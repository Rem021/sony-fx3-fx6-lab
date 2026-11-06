"""Original fixed-loader prefix, stopped BEFORE mount or any file/device I/O.

Selected defined PLT functions resolve to their original code. Only errno,
strncmp and memset use explicit guest fixtures. No mount success is fabricated.
"""
from pathlib import Path
from hashlib import sha256
import io, json, struct
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm64_const import *
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / 'stage184-community-recovery-and-standalone-service/evidence/standalone-commands/originals/lib/libJiritsu.so'
raw = SOURCE.read_bytes()
assert sha256(raw).hexdigest() == 'bdef58b24a3b67b4d14d4f0214b89aae0fcad19f114b4188c328f9d2c092f1d9'
elf = ELFFile(io.BytesIO(raw))
symbols = {s.name: s for s in elf.get_section_by_name('.dynsym').iter_symbols()}
B, REQ, DMM, ERRNO, STACK, DONE = 0x1000000, 0x2000000, 0x2010000, 0x2020000, 0x2100000, 0x2200000
bindings = {0x5b70: 0x771c, 0x5ee0: 0xf8b4, 0x67b0: 0xf460, 0x5ca0: 0x6d28}
expected_symbols = {
    0x771c: 'sys_mount', 0xf8b4: '_ZN11CFileAccess5mountEPKcS1_S1_mPKv',
    0xf460: '_ZN11CFileAccess15selection_mountEPKcS1_S1_S1_mPKv',
    0x6d28: '_ZN11CFileAccessC1Ev',
}
for va, name in expected_symbols.items():
    assert symbols[name]['st_value'] == va

def original(va, size):
    seg = next(s for s in elf.iter_segments() if s['p_type'] == 'PT_LOAD'
               and s['p_vaddr'] <= va and va + size <= s['p_vaddr'] + s['p_filesz'])
    off = seg['p_offset'] + va - seg['p_vaddr']
    return raw[off:off + size]

def run(entry, operation, area):
    u = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
    u.mem_map(B, 0x80000)
    for seg in elf.iter_segments():
        if seg['p_type'] == 'PT_LOAD':
            u.mem_write(B + seg['p_vaddr'], seg.data())
    for at, size in [(REQ, 0x1000), (DMM, 0x1000), (ERRNO, 0x1000), (STACK, 0x10000), (DONE, 0x1000)]:
        u.mem_map(at, size)
    u.mem_write(REQ + 0x28, bytes([operation, area, 0]))
    for reg, value in [(UC_ARM64_REG_X0, REQ), (UC_ARM64_REG_X1, DMM),
                        (UC_ARM64_REG_SP, STACK + 0xff00), (UC_ARM64_REG_X30, DONE)]:
        u.reg_write(reg, value)
    state = {'entry': hex(entry), 'operation': operation, 'area': area, 'instructions': 0,
             'bindings': [], 'fixtures': [], 'stop': None}
    def cstring(at):
        value = bytes(u.mem_read(at, 128))
        assert b'\0' in value
        return value.split(b'\0')[0].decode('ascii')
    def ret(value):
        u.reg_write(UC_ARM64_REG_X0, value)
        u.reg_write(UC_ARM64_REG_PC, u.reg_read(UC_ARM64_REG_X30))
    def hook(uc, address, size, _):
        state['instructions'] += 1
        assert state['instructions'] < 10000
        if address == DONE:
            state['stop'] = 'original_return'
            uc.emu_stop(); return
        va = address - B
        if va in bindings:
            state['bindings'].append({'PLT': hex(va), 'original_defined_VA': hex(bindings[va])})
            uc.reg_write(UC_ARM64_REG_PC, B + bindings[va]); return
        if not 0x5a00 <= va < 0x6960:
            return
        args = [uc.reg_read(r) for r in (UC_ARM64_REG_X0, UC_ARM64_REG_X1, UC_ARM64_REG_X2, UC_ARM64_REG_X3, UC_ARM64_REG_X4)]
        if va == 0x6540:
            state['fixtures'].append('__errno_location -> private guest cell')
            ret(ERRNO)
        elif va == 0x62d0:
            assert args[2] == 4 and cstring(args[0]) == '/tmp/jiritsu' and cstring(args[1]) == '/mnt'
            state['fixtures'].append('strncmp of original fixed strings')
            ret(1)
        elif va == 0x5e60:
            assert STACK <= args[0] < STACK + 0x10000 and args[1] == 0 and args[2] in (0x40e, 0x202)
            state['fixtures'].append('memset of guest CFileAccess/filename buffer')
            uc.mem_write(args[0], bytes(args[2])); ret(args[0])
        else:
            state['stop'] = 'before_external_call'
            state['boundary'] = hex(va)
            if va == 0x61a0:
                state['pending_mount_args'] = {'source': cstring(args[0]), 'target': cstring(args[1]),
                                               'filesystem': cstring(args[2]), 'flags': hex(args[3]), 'data': args[4]}
                state['pending_mount_is_readonly'] = bool(args[3] & 1)
            uc.emu_stop()
    u.hook_add(UC_HOOK_CODE, hook)
    u.emu_start(B + entry, DONE + 4, count=10000)
    assert state['stop'] is not None
    state['request_status_field'] = hex(struct.unpack('<I', bytes(u.mem_read(REQ + 0x1c, 4)))[0])
    if state['stop'] == 'original_return':
        state['return_w0'] = u.reg_read(UC_ARM64_REG_X0) & 0xffffffff
    for seg in elf.iter_segments():
        if seg['p_type'] == 'PT_LOAD' and seg['p_flags'] & 1:
            assert bytes(u.mem_read(B + seg['p_vaddr'], seg['p_filesz'])) == seg.data()
    return state

cases = [run(0x8cf4, 0, 2), run(0x8cf4, 1, 2), run(0x9528, 0, 0), run(0x9528, 0, 2)]
for c in (cases[0], cases[2]):
    assert c['stop'] == 'before_external_call' and c['boundary'] == '0x61a0'
    assert c['pending_mount_args'] == {'source': '/dev/nflasha6', 'target': '/tmp/jiritsu', 'filesystem': 'vfat', 'flags': '0xc0ed0490', 'data': 0}
    assert c['pending_mount_is_readonly'] is False
assert cases[1]['stop'] == 'original_return' and cases[1]['request_status_field'] == '0x10000201'
assert cases[3]['stop'] == 'before_external_call' and cases[3]['boundary'] == '0x6090'
assert cases[3]['request_status_field'] == '0x10000201'

md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
pins = []
for va, size, meaning in [(0x771c, 24, 'fixed mount wrapper'), (0xf8b4, 24, 'mount argument adapter'),
                           (0xf460, 1108, 'filesystem selection and native mount'),
                           (0x8cf4, 748, 'set_file'), (0x9528, 1120, 'set_file2')]:
    code = original(va, size)
    pins.append({'VA': hex(va), 'bytes': size, 'meaning': meaning, 'sha256': sha256(code).hexdigest(),
                 'disassembly': [f'{i.address:08x} {i.mnemonic} {i.op_str}' for i in md.disasm(code, va)]})
report = {'status': 'FIXED_LIBRARY_LOADER_PREFIX_REQUIRES_FLASH_MOUNT_ATTEMPT',
          'source': str(SOURCE), 'source_sha256': sha256(raw).hexdigest(),
          'cases': cases, 'function_pins': pins, 'all_4_cases_met_expected_result': True,
          'finding': 'The normal set_file path reaches mount(/dev/nflasha6, /tmp/jiritsu, vfat, non-readonly flags) BEFORE writing or dlopen. The /tmp prefix is not proof of volatile storage. set_file2 operation0 area2 refuses before mount; this does not cover its other modes.',
          'normal_write_flags_observed_statically': 'open flags0x241 = WRONLY|CREAT|TRUNC; no EXCL/NOFOLLOW',
          'dlopen_return_not_worker_success': True,
          'actual_mount_return_or_current_mount_state_fabricated': False,
          'actual_mount_file_write_dlopen_or_camera_operations': 0,
          'scope': 'Original AP local prefix with predecoded requests and explicit libc fixtures only. No whole firmware, Linux, USB, current device mount, loader or recovery validation.'}
with (HERE / 'fixed-loader-prefix-results.json').open('x') as f:
    json.dump(report, f, indent=2); f.write('\n')
print(json.dumps({'cases': len(cases), 'mount_stops': 2, 'source': '/dev/nflasha6',
                  'target': '/tmp/jiritsu', 'readonly_flag': False, 'actual_camera_operations': 0}))
