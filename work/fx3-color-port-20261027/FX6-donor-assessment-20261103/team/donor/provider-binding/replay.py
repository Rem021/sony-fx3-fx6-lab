#!/usr/bin/env python3
"""Bounded original AArch64 mode-update and event-dispatch replay.

The provider table, callback and event are explicit host fixtures.  No DMA
builder, kernel, unknown program entry or device code is executed.
"""
import hashlib
import json
import struct

from unicorn import UC_ARCH_ARM64, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_MODE_ARM, Uc
from unicorn import arm64_const as R

from analyze import BASE, FX3_AV, FX6_AV, MODELS, PINS, ROOT, source

STACK = 0x50000000
EVENT = 0x51001000
STOP = 0x60000000
STUB = 0x61000000
PROVIDER = 0x62000000
MAX_INSTRUCTIONS = 1200

EXTRA = {
    'FX6_6.01': {'getter': (0x29b308, 0x29b334), 'lookup': (0x2a650c, 0x2a659c),
                 'logger': 0x2a65f8, 'output': 0xb533d8, 'alt': (84, 0xa822b8)},
    'FX3_7.02': {'getter': (0x2b8130, 0x2b815c), 'lookup': (0x2c3334, 0x2c33c4),
                'logger': 0x2c3420, 'output': 0xbb5d40, 'alt': None},
}


def reg(u, name):
    return u.reg_read(getattr(R, 'UC_ARM64_REG_' + name))


def run(name, data, status, word):
    cfg = MODELS[name]
    extra = EXTRA[name]
    u = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
    u.mem_map(BASE, (len(data) + 0xfff) & ~0xfff)
    u.mem_write(BASE, data)
    u.mem_map(STACK, 0x10000)
    u.mem_write(STACK, b'\xc7' * 0x10000)
    u.mem_map(EVENT & ~0xfff, 0x1000)
    u.mem_write(EVENT & ~0xfff, b'\x5a' * 0x1000)
    u.mem_write(EVENT, struct.pack('<III', 0, 22, 0))
    u.mem_map(PROVIDER, 0x1000)
    u.mem_write(PROVIDER, b'\xa5' * 0x1000)
    u.mem_write(PROVIDER + 0x4c0, struct.pack('<Q', STUB))
    u.mem_write(BASE + 0x20, struct.pack('<Q', PROVIDER))
    u.mem_map(STUB, 0x1000)
    u.mem_write(STUB, bytes.fromhex('c0035fd6'))  # ret
    u.reg_write(R.UC_ARM64_REG_SP, STACK + 0xf000)
    u.reg_write(R.UC_ARM64_REG_LR, STOP)
    for i in range(19, 29):
        u.reg_write(getattr(R, f'UC_ARM64_REG_X{i}'), 0x11110000 + i)
    saved = {f'X{i}': reg(u, f'X{i}') for i in range(19, 29)}
    state = {'name': name, 'fixture_status': status, 'fixture_word': hex(word),
             'patched_original_header_qword': hex(BASE + 0x1a4),
             'patched_guest_header_qword': hex(PROVIDER),
             'provider_slot_offset': '0x4c0', 'provider_slot_guest_va': hex(PROVIDER + 0x4c0),
             'stub_guest_va': hex(STUB), 'event_guest_va': hex(EVENT),
             'event_kind': 0, 'event_look_index': 22, 'event_ip': 0,
             'stage': 'mode', 'pcs': [], 'writes': [], 'violations': [], 'stub_calls': [],
             'stop': None, 'builder': None}
    mode_lo, mode_hi = cfg['update']
    dispatch_lo, _ = cfg['dispatch']
    mode_allowed = [(mode_lo, mode_hi), (cfg['thunk_word'], cfg['thunk_word'] + 20)]
    dispatch_allowed = [(dispatch_lo, cfg['builder_call']), extra['getter'], extra['lookup']]

    def code(uc, pc, size, _):
        off = pc - BASE
        if pc == STUB:
            args = {'w0': hex(reg(uc, 'W0')), 'x1': hex(reg(uc, 'X1')),
                    'w2': reg(uc, 'W2'), 'lr': hex(reg(uc, 'LR'))}
            state['stub_calls'].append(args)
            if args['w0'] != '0x2ae0000' or args['w2'] != 4:
                state['violations'].append({'kind': 'unexpected_provider_abi', 'args': args})
                uc.emu_stop()
                return
            if status > 0:
                uc.mem_write(reg(uc, 'X1'), struct.pack('<I', word))
                state['writes'].append({'stage': 'host_provider_stub', 'address': args['x1'],
                                        'size': 4, 'value': hex(word)})
            uc.reg_write(R.UC_ARM64_REG_X0, status)
            return
        if state['stage'] == 'dispatch' and off in (cfg['builder_call'], extra['logger']):
            state['stop'] = hex(off)
            if off == cfg['builder_call']:
                arg = reg(uc, 'X0')
                blob = bytes(uc.mem_read(arg, 16))
                ip, count, descriptor = struct.unpack('<IIQ', blob)
                state['builder'] = {'call_offset': hex(off), 'ip': ip, 'count': count,
                                    'descriptor_va': hex(descriptor), 'arg_bytes_hex': blob.hex(),
                                    'x19': hex(reg(uc, 'X19')), 'x20': reg(uc, 'W20'),
                                    'x21': hex(reg(uc, 'X21')), 'sp': hex(reg(uc, 'SP'))}
            uc.emu_stop()
            return
        if pc != STUB and not any(a <= off < z for a, z in
                                  (mode_allowed if state['stage'] == 'mode' else dispatch_allowed)):
            state['violations'].append({'kind': 'outside_allowed_code', 'pc': hex(pc),
                                        'stage': state['stage']})
            uc.emu_stop()
            return
        state['pcs'].append({'stage': state['stage'], 'offset': hex(off) if pc != STUB else 'stub'})

    def write(uc, access, addr, size, value, _):
        allowed = STACK <= addr and addr + size <= STACK + 0x10000
        if state['stage'] == 'mode':
            allowed |= addr == BASE + cfg['flag'] and size == 1
            allowed |= addr == BASE + cfg['mode'] and size == 4
        if not allowed:
            state['violations'].append({'kind': 'unexpected_original_write',
                                        'address': hex(addr), 'size': size,
                                        'pc': hex(reg(uc, 'PC'))})
            uc.emu_stop()
        state['writes'].append({'stage': state['stage'], 'address': hex(addr), 'size': size,
                                'value': hex(value), 'pc': hex(reg(uc, 'PC'))})

    u.hook_add(UC_HOOK_CODE, code)
    u.hook_add(UC_HOOK_MEM_WRITE, write)
    u.emu_start(BASE + mode_lo, STOP, count=MAX_INSTRUCTIONS)
    state['mode_instructions'] = len(state['pcs'])
    state['mode_result'] = {
        'pc': hex(reg(u, 'PC')), 'sp': hex(reg(u, 'SP')),
        'flag': bytes(u.mem_read(BASE + cfg['flag'], 1))[0],
        'mode': struct.unpack('<I', bytes(u.mem_read(BASE + cfg['mode'], 4)))[0],
        'callee_saved_preserved': {k: reg(u, k) == v for k, v in saved.items()},
    }
    assert state['mode_result']['pc'] == hex(STOP)
    assert all(state['mode_result']['callee_saved_preserved'].values())
    assert state['mode_result']['sp'] == hex(STACK + 0xf000)
    assert len(state['stub_calls']) == 1 and not state['violations']
    assert state['mode_result']['flag'] == (1 if status > 0 and word & 0xf == 1 else 0)
    expected_mode = (3 if ((word >> 4) & 0xf) == 3 else 2) if status > 0 else 2
    assert state['mode_result']['mode'] == expected_mode
    u.reg_write(R.UC_ARM64_REG_SP, STACK + 0xf000)
    u.reg_write(R.UC_ARM64_REG_X0, EVENT)
    u.reg_write(R.UC_ARM64_REG_LR, STOP)
    state['stage'] = 'dispatch'
    u.emu_start(BASE + dispatch_lo, STOP, count=MAX_INSTRUCTIONS)
    state['dispatch_instructions'] = len(state['pcs']) - state['mode_instructions']
    assert not state['violations'] and state['dispatch_instructions'] < MAX_INSTRUCTIONS
    assert state['stop'] == hex(cfg['builder_call'] if expected_mode == 3 else extra['logger'])
    if state['builder']:
        assert state['builder']['ip'] == 0
        assert state['builder']['x19'] == hex(EVENT)
        assert state['builder']['x21'] == hex(BASE + extra['output'])
        assert state['builder']['x20'] == (31 if state['mode_result']['flag'] else 22)
        if not state['mode_result']['flag']:
            assert (state['builder']['count'], state['builder']['descriptor_va']) == (
                70, hex(BASE + cfg['descriptors']))
        elif extra['alt']:
            assert (state['builder']['count'], state['builder']['descriptor_va']) == (
                extra['alt'][0], hex(BASE + extra['alt'][1]))
    state['stack_canaries_preserved'] = [
        bytes(u.mem_read(STACK + 0xef00, 16)) == b'\xc7' * 16,
        bytes(u.mem_read(STACK + 0xf000, 16)) == b'\xc7' * 16]
    state['event_unchanged'] = bytes(u.mem_read(EVENT, 12)) == struct.pack('<III', 0, 22, 0)
    assert all(state['stack_canaries_preserved']) and state['event_unchanged']
    return state


def main():
    binaries = {'FX6_6.01': source(FX6_AV, PINS['fx6_av']),
                'FX3_7.02': source(FX3_AV, PINS['fx3_av'])}
    cases = [run(name, data, status, word)
             for name, data in binaries.items()
             for status, word in [(4, 0x30), (4, 0x31), (0, 0x30)]]
    output = {'source_sha256': {'FX6_6.01': PINS['fx6_av'], 'FX3_7.02': PINS['fx3_av']},
              'va_rule': 'AV VA = 0xffffffc001000000 + file offset',
              'instruction_budget_per_stage': MAX_INSTRUCTIONS,
              'patches': ['guest RAM ORIL header+0x20 -> synthetic provider 0x62000000',
                          'guest RAM provider+0x4c0 -> synthetic ret stub 0x61000000'],
              'stubs': ['ret at 0x61000000 supplies status and optional four-byte word; checks original arguments'],
              'fixtures': ['event kind=0, look=22, ip=0 at 0x51001000; synthetic status/word cases'],
              'executed_scope': 'original mode update, provider import thunk, dispatch, mode/flag getters and look lookup; stop before builder or logger',
              'hardware_submitted': False, 'natural_provider_identified': False,
              'cases': cases}
    (ROOT / 'provider-replay.json').write_text(json.dumps(output, indent=2) + '\n')
    print(json.dumps([{'model': c['name'], 'status': c['fixture_status'],
                       'word': c['fixture_word'], 'mode': c['mode_result']['mode'],
                       'flag': c['mode_result']['flag'], 'stop': c['stop'],
                       'builder': c['builder']} for c in cases]))


if __name__ == '__main__':
    main()
