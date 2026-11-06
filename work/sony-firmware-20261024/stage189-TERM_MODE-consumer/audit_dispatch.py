"""Bounded original ARM64 dispatch experiment, with explicit host-only fixtures.

No device API, firmware loading on the host, or original instructions replaced.
Only memset/Serialize/logging PLT boundaries are fixture functions. Stop before
IPC, allocation, testcmd or any other unmodelled external call. Not a full USB,
authentication, Linux, Sony loader or camera execution experiment.
"""
from pathlib import Path
from hashlib import sha256
import io, json, struct
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm64_const import (
    UC_ARM64_REG_X0, UC_ARM64_REG_X1, UC_ARM64_REG_X2,
    UC_ARM64_REG_X3, UC_ARM64_REG_X30, UC_ARM64_REG_SP, UC_ARM64_REG_PC,
)

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
SOURCE = BASE / 'stage183-request-consumer-and-early-entry/evidence/usb-main-dependency/originals/lib/libsencore.so'
RAW = SOURCE.read_bytes()
assert sha256(RAW).hexdigest() == 'a2907111c4a22314dcb12c25889e0e3142764c6a4a910a746e43908f76e7c410'
ELF = ELFFile(io.BytesIO(RAW))
B = 0x1000000
OBJECT, PACKET, COMMAND, STACK, DONE = 0x2000000, 0x2010000, 0x2020000, 0x2100000, 0x2200000

def original(va, length):
    seg = next(s for s in ELF.iter_segments() if s['p_type'] == 'PT_LOAD'
               and s['p_vaddr'] <= va and va + length <= s['p_vaddr'] + s['p_filesz'])
    off = seg['p_offset'] + va - seg['p_vaddr']
    return RAW[off:off + length]

assert original(0x265a4, 17).hex() == '5f023d0001061f805445524d5f4d4f4445'
symbols = {s.name: s for s in ELF.get_section_by_name('.dynsym').iter_symbols()}
entry = symbols['_ZN29SubsystemCommunicationCommand16TransactionStartEPK12SenserPacketPKvS4_']
assert (entry['st_value'], entry['st_size']) == (0xfb0c, 2080)
assert symbols['adjCodeLevel']['st_value'] == 0x6bf98

def run(command, payload, level):
    u = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
    u.mem_map(B, 0x80000)
    for seg in ELF.iter_segments():
        if seg['p_type'] == 'PT_LOAD':
            u.mem_write(B + seg['p_vaddr'], seg.data())
    # These data relocations are the two GOT entries consumed in this fixture.
    # No original instruction, command table, or branch condition is modified.
    u.mem_write(B + 0x6aee0, struct.pack('<Q', B + 0x6bf98))
    u.mem_write(B + 0x6ae80, struct.pack('<Q', B + 0xcff0))
    u.mem_write(B + 0x6bf98, bytes([level]))
    for address, length in [(OBJECT, 0x1000), (PACKET, 0x1000), (COMMAND, 0x1000), (STACK, 0x10000), (DONE, 0x1000)]:
        u.mem_map(address, length)
    # Already decoded SenserPacket and 4-byte command header, synthetic payload.
    u.mem_write(PACKET, struct.pack('<IHHB', 5, 0x6000, 0, 1))
    u.mem_write(COMMAND, struct.pack('<HH', 0x601, command))
    for register, value in [(UC_ARM64_REG_X0, OBJECT), (UC_ARM64_REG_X1, PACKET),
                            (UC_ARM64_REG_X2, 0), (UC_ARM64_REG_X3, COMMAND),
                            (UC_ARM64_REG_SP, STACK + 0xff00), (UC_ARM64_REG_X30, DONE)]:
        u.reg_write(register, value)
    events, path, state = [], [], {'instructions': 0, 'stop': None}
    points = {0xfb0c, 0xfbb0, 0xfbc4, 0xfbc8, 0xfbd0, 0xfbd4, 0xfbd8, 0xfbe0,
              0xfd9c, 0xfdf4, 0xfe04, 0xfe10, 0xfe14, 0xfe44, 0xfe5c,
              0xff58, 0xfff8, 0x100b8, 0x1016c, 0x10174}

    def ret(value):
        u.reg_write(UC_ARM64_REG_X0, value)
        u.reg_write(UC_ARM64_REG_PC, u.reg_read(UC_ARM64_REG_X30))

    def hook(uc, address, size, _):
        state['instructions'] += 1
        assert state['instructions'] < 100000, 'instruction budget'
        if address == DONE:
            state['stop'] = 'original_return'
            uc.emu_stop()
            return
        va = address - B
        if va in points:
            path.append(hex(va))
        if 0x9d00 <= va < 0xad20:
            x0, x1, x2 = [uc.reg_read(r) for r in (UC_ARM64_REG_X0, UC_ARM64_REG_X1, UC_ARM64_REG_X2)]
            if va == 0xa260:
                assert x0 == OBJECT + 0x40 and x1 == 0 and x2 == 0x124
                uc.mem_write(x0, bytes(x2))
                events.append({'fixture': 'memset', 'bytes': x2})
                ret(x0)
            elif va == 0xa580:
                assert x0 == B + 0xcff0 and x1 == OBJECT + 0x40 and x2 == 1
                uc.mem_write(x1, bytes([payload]))
                events.append({'fixture': 'Serialize synthetic payload', 'bytes': 1})
                ret(1)
            elif va == 0xa450:
                events.append({'fixture': 'cpp_logrec', 'level': x0})
                ret(0)
            else:
                state['stop'] = 'before_unmodelled_external_call'
                state['boundary'] = hex(va)
                uc.emu_stop()

    u.hook_add(UC_HOOK_CODE, hook)
    u.emu_start(B + 0xfb0c, DONE + 4, count=100000)
    assert state['stop'] is not None, 'guest failed to reach a checked stop'
    for seg in ELF.iter_segments():
        if seg['p_type'] == 'PT_LOAD' and seg['p_flags'] & 1:
            assert bytes(u.mem_read(B + seg['p_vaddr'], seg['p_filesz'])) == seg.data(), 'original code changed'
    result = {'command': hex(command), 'payload': payload, 'adjCodeLevel': level,
              'path': path, 'events': events, **state}
    if state['stop'] == 'original_return':
        result['return_w0'] = u.reg_read(UC_ARM64_REG_X0) & 0xffffffff
    return result

results = [run(command, payload, level) for command in (0x1f, 0x801f)
           for payload in (0, 1, 2) for level in range(4)]
for r in results:
    assert r['stop'] == 'original_return' and r['return_w0'] == 0x80
    assert '0xfbc8' in r['path'] and '0x10174' in r['path']
    assert [x['fixture'] for x in r['events']] == ['memset', 'Serialize synthetic payload']

controls = [run(0x12, 2, 3), run(0x1012, 2, 3)]
assert controls[0]['boundary'] == '0xa440', controls[0]  # stop before OSAL allocation
assert controls[1]['boundary'] == '0x9f10', controls[1]  # stop before testcmd_init
assert all(r['stop'] == 'before_unmodelled_external_call' for r in controls)

report = {
    'status': 'ORIGINAL_ARM64_TERM_MODE_REJECTED_BEFORE_IPC_IN_BOUNDED_FIXTURES',
    'source': str(SOURCE), 'source_sha256': sha256(RAW).hexdigest(),
    'function_VA': hex(entry['st_value']), 'function_bytes': entry['st_size'],
    'function_sha256': sha256(original(entry['st_value'], entry['st_size'])).hexdigest(),
    'term_cases': results, 'positive_route_controls_stopped_before_external_call': controls,
    'original_instructions_or_table_replaced': False,
    'fixture_boundaries': ['already decoded command and packet', 'one-byte payload serializer', 'memset', 'logging'],
    'other_external_calls_automatically_succeeded': False,
    'all_26_cases_met_expected_result': True,
    'scope': 'This original AP dispatch and table only; no complete protocol/auth/Linux/CP/USB/loader or physical camera validation.',
    'new_camera_operations': 0,
}
with (HERE / 'dispatch-guest-results.json').open('x') as f:
    json.dump(report, f, indent=2)
    f.write('\n')
print(json.dumps({'term_cases': len(results), 'control_cases': len(controls),
                  'term_return': '0x80', 'no_IPC_or_testcmd_called': True, 'new_camera_operations': 0}))
