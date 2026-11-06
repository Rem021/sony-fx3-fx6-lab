#!/usr/bin/env python3
"""Stop at original DMA builder call, after original dispatch and look lookup.

The mode=3 RAM fixture bypasses an unrelated logging call; it is not claimed
as the natural camera state. No builder, handoff, VM or device is executed.
"""
import hashlib
import json
import pathlib
import struct

from unicorn import UC_ARCH_ARM64, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_MODE_ARM, Uc
from unicorn import arm64_const as R

ROOT = pathlib.Path(__file__).resolve().parent
AV = ROOT.parents[2] / 'fat-files/nflasha3/av-cam.bin'
PIN = '56684d830eab1e304868548746d8275188a925f9e4ab9354560180c31b4a93cf'
BASE = 0xffffffc001000000
STACK = 0x50000000
EVENT = 0x51001000
ENTRY = 0x2a7374
BUILDER_CALL = 0x2a74e4
OTHER_HANDLER = 0x2a7574
LOGGER = 0x2a65f8
MAX_COUNT = 1000


def run(data, name, *, kind, index, ip, override, mode):
    u = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
    u.mem_map(BASE, (len(data)+4095)&~4095)
    u.mem_write(BASE, data)
    u.mem_map(STACK, 0x10000)
    u.mem_write(STACK, b'\xc7'*0x10000)
    u.mem_map(EVENT & ~0xfff, 0x1000)
    u.mem_write(EVENT & ~0xfff, b'\x5a'*0x1000)
    u.mem_write(EVENT, struct.pack('<III', kind, index, ip))
    u.mem_write(BASE+0xb45884, bytes([override]))
    u.mem_write(BASE+0xbb0bfc, struct.pack('<I', mode))
    u.reg_write(R.UC_ARM64_REG_SP, STACK+0xf000)
    u.reg_write(R.UC_ARM64_REG_X0, EVENT)
    u.reg_write(R.UC_ARM64_REG_X21, 0x2121212121212121)
    u.reg_write(R.UC_ARM64_REG_LR, 0x60000000)
    state = {'stop': None, 'flag_before': None, 'flag_after': None,
             'lookup_before': None, 'lookup_after': None,
             'calls': [], 'writes': [], 'violations': []}
    allowed = [(0x2a7374, 0x2a74e8), (0x29b308, 0x29b334), (0x2a650c, 0x2a659c)]

    def code(uc, pc, size, _):
        off = pc-BASE
        if off in (BUILDER_CALL, OTHER_HANDLER, LOGGER):
            state['stop'] = hex(off)
            if off == BUILDER_CALL:
                arg = uc.reg_read(R.UC_ARM64_REG_X0)
                out = uc.reg_read(R.UC_ARM64_REG_X1)
                state['builder_arguments'] = {
                    'x0': hex(arg), 'x1': hex(out),
                    'arg_bytes_hex': bytes(uc.mem_read(arg, 16)).hex(),
                    'ip': struct.unpack('<I', bytes(uc.mem_read(arg, 4)))[0],
                    'count': struct.unpack('<I', bytes(uc.mem_read(arg+4, 4)))[0],
                    'descriptor_va': hex(struct.unpack('<Q', bytes(uc.mem_read(arg+8, 8)))[0]),
                    'x19': hex(uc.reg_read(R.UC_ARM64_REG_X19)),
                    'x20': hex(uc.reg_read(R.UC_ARM64_REG_X20)),
                    'x21': hex(uc.reg_read(R.UC_ARM64_REG_X21)),
                    'sp': hex(uc.reg_read(R.UC_ARM64_REG_SP)),
                }
            uc.emu_stop()
            return
        if not any(a <= off < z for a, z in allowed):
            state['violations'].append({'kind': 'outside_original_code', 'pc': hex(pc)})
            uc.emu_stop()
            return
        state['calls'].append(hex(off))
        if off in (0x2a7470, 0x2a7474, 0x2a748c, 0x2a7490):
            snap = {k: hex(uc.reg_read(getattr(R, 'UC_ARM64_REG_'+k)))
                    for k in ('X19', 'X20', 'X21', 'SP')}
            if off == 0x2a7470:
                state['flag_before'] = snap
            elif off == 0x2a7474:
                state['flag_after'] = {**snap, 'w0': uc.reg_read(R.UC_ARM64_REG_W0)}
            else:
                state['lookup_before' if off == 0x2a748c else 'lookup_after'] = snap

    def write(uc, access, addr, size, value, _):
        if not (STACK <= addr and addr+size <= STACK+0x10000):
            state['violations'].append({'kind': 'outside_stack_write', 'address': hex(addr),
                                        'size': size, 'pc': hex(uc.reg_read(R.UC_ARM64_REG_PC))})
            uc.emu_stop()
        state['writes'].append({'address': hex(addr), 'size': size,
                                'pc_offset': hex(uc.reg_read(R.UC_ARM64_REG_PC)-BASE)})

    u.hook_add(UC_HOOK_CODE, code)
    u.hook_add(UC_HOOK_MEM_WRITE, write)
    error = None
    try:
        u.emu_start(BASE+ENTRY, 0x60000000, count=MAX_COUNT)
    except Exception as ex:
        error = repr(ex)
    state['name'] = name
    state['fixture'] = {'event_va': hex(EVENT), 'event_kind': kind, 'event_look_index': index,
                        'event_ip': ip, 'guest_override_flag': override, 'guest_mode_word': mode,
                        'mode_original_in_file': 2, 'override_original_in_file': 0}
    state['instruction_count'] = len(state['calls'])
    state['error'] = error
    state['stack_canaries_preserved'] = [
        bytes(u.mem_read(STACK+0xef00, 16)) == b'\xc7'*16,
        bytes(u.mem_read(STACK+0xf000, 16)) == b'\xc7'*16,
    ]
    state['event_unchanged'] = bytes(u.mem_read(EVENT, 12)) == struct.pack('<III', kind,index,ip)
    # Retain the full code/write trace for reproducible bounded-call evidence.
    assert not state['violations'] and not error and all(state['stack_canaries_preserved'])
    assert state['event_unchanged'] and state['instruction_count'] < MAX_COUNT
    return state


def main():
    data = AV.read_bytes()
    assert hashlib.sha256(data).hexdigest() == PIN
    assert data[0xb45884] == 0 and struct.unpack_from('<I', data, 0xbb0bfc)[0] == 2
    cases = [
        run(data, 'look22_ip0', kind=0,index=22,ip=0,override=0,mode=3),
        run(data, 'look22_ip1', kind=0,index=22,ip=1,override=0,mode=3),
        run(data, 'override_forces_31', kind=0,index=22,ip=0,override=1,mode=3),
        run(data, 'other_event_kind', kind=1,index=22,ip=0,override=0,mode=3),
        run(data, 'original_mode_reaches_logger', kind=0,index=22,ip=0,override=0,mode=2),
    ]
    by = {c['name']:c for c in cases}
    for key, ip in [('look22_ip0',0),('look22_ip1',1)]:
        c=by[key]
        assert c['stop']==hex(BUILDER_CALL)
        assert (c['builder_arguments']['ip'],c['builder_arguments']['count'],c['builder_arguments']['descriptor_va']) == (ip,70,hex(BASE+0xaa2ca0))
        assert c['lookup_before'] == c['lookup_after']
        assert all(c['flag_before'][k]==c['flag_after'][k] for k in ('X19','X20','X21','SP'))
        assert c['flag_after']['w0']==0
        assert c['builder_arguments']['x19']==hex(EVENT) and c['builder_arguments']['x20']==hex(22)
        assert c['builder_arguments']['x21']==hex(BASE+0xb533d8)
    c=by['override_forces_31']
    assert c['stop']==hex(BUILDER_CALL) and c['builder_arguments']['x20']==hex(31)
    assert c['flag_after']['w0']==1 and c['lookup_before']==c['lookup_after']
    assert c['builder_arguments']['count']==84 and c['builder_arguments']['descriptor_va']==hex(BASE+0xa822b8)
    assert by['other_event_kind']['stop']==hex(OTHER_HANDLER)
    assert by['original_mode_reaches_logger']['stop']==hex(LOGGER)
    result={'source_sha256':PIN,'base':hex(BASE),'entry_offset':hex(ENTRY),
            'stop_before_dma_builder_or_other_handler':True,'budget_each':MAX_COUNT,
            'guest_patches':'mode word at image+0xbb0bfc changed 2->3 in four cases to bypass logging; flag byte 0->1 in one case; event fixture and stack are host-created RAM; no code patch or stub',
            'cases':cases,'hardware_submitted':False,
            'scope':'Original dispatch and lookup CPU bytes only; selection state is synthetic; no DMA builder or submit executed'}
    (ROOT/'caller-replay.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'source_sha256':PIN,'cases':[{'name':c['name'],'stop':c['stop'],
                  'instructions':c['instruction_count'],
                  'builder_arguments':c.get('builder_arguments')} for c in cases]}))


if __name__=='__main__':main()
