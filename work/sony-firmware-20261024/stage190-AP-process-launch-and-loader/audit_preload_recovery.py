"""Original Sony root-loader preload error consumer and startup-file audit.

Guest fixtures inject _dl_catch_error results and collect diagnostics. The real
file lookup, full loader, constructor, kernel and camera are not executed.
"""
from pathlib import Path
from hashlib import sha256
import importlib.util, io, json, re, struct, urllib.request
from elftools.elf.elffile import ELFFile
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_INTR
from unicorn.arm64_const import *
HERE = Path(__file__).resolve().parent
BASE = HERE.parent
inventory = json.loads((HERE / 'launch-inventory-v2.json').read_text())
reader = BASE / 'stage2/extraction/read_filesystems.py'
assert sha256(reader.read_bytes()).hexdigest() == 'eecbe9b099f9fbc8f8e06759c5e8a2ce9910e0f365ae9891fe0887353edc31ad'
spec = importlib.util.spec_from_file_location('fixed_read_only_ext2', reader)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
root = m.Ext2(BASE / 'stage2/extraction/nflasha7.img')
assert sha256(root.b).hexdigest() == inventory['root_image_sha256']
rows = {r['path']: r for r in root.walk()}
def root_data(name):
    assert rows[name]['type'] == 0x8000
    return root.data(rows[name]['inode'])
script_names = ('/sbin/initrc/fstab.root', '/sbin/initrc/fstab.ext', '/sbin/init2')
scripts = [{'path': p, 'inode': rows[p]['inode'], 'sha256': sha256(root_data(p)).hexdigest(),
            'text': root_data(p).decode()} for p in script_names]
ext = root_data('/sbin/initrc/fstab.ext').decode().splitlines()
assert [line.split()[:4] for line in ext] == [
    ['/dev/nflasha10', '/etc', 'vfat', 'rw,nodiratime,noatime,sync,posix_attr'],
    ['/dev/nflasha10', '/var', 'vfat', 'rw,nodiratime,noatime,sync,posix_attr']]
init2 = root_data('/sbin/init2')
assert b'[ -r $FSTAB_EXT ] && busybox mount -a -T $FSTAB_EXT' in init2
assert b'mount -t tmpfs none /tmp_wbshd' in init2
assert init2.index(b'mount -t tmpfs none /tmp_wbshd') < init2.index(b'/usr/bin/bootin.elf &')
raw = root_data('/lib/ld-2.25.so')
assert sha256(raw).hexdigest() == '90b4fe734ba7faa08d4591b1363bff478e7bde399a821fc0b2d021c062a58a9a'
elf = ELFFile(io.BytesIO(raw))
def original(va, size):
    s = next(s for s in elf.iter_segments() if s['p_type'] == 'PT_LOAD'
             and s['p_vaddr'] <= va and va + size <= s['p_vaddr'] + s['p_filesz'])
    at = s['p_offset'] + va - s['p_vaddr']
    return raw[at:at + size]
def literal(va):
    return original(va, 128).split(b'\0')[0].decode()
assert literal(0x18be8) == '/etc/ld.so.preload'
assert literal(0x17bd0) == "ERROR: ld.so: object '%s' from %s cannot be preloaded (%s): ignored.\n"
symtab = elf.get_section_by_name('.dynsym')
plt = {elf.get_section_by_name('.plt')['sh_addr'] + 32 + i * 16: symtab.get_symbol(r['r_info_sym']).name
       for i, r in enumerate(elf.get_section_by_name('.rela.plt').iter_relocations())}
assert plt[0xad0] == '_dl_catch_error'
md = Cs(CS_ARCH_ARM64, CS_MODE_ARM); md.skipdata = True
function = original(0xb00, 0x94)
instructions = list(md.disasm(function, 0xb00))
assert len(instructions) == 37 and instructions[-1].mnemonic == 'ret'
assert [(i.address, i.op_str) for i in instructions if i.mnemonic == 'bl'] == [(0xb4c, '#0xad0'), (0xb6c, '#0xe530')]
all_text = list(md.disasm(elf.get_section_by_name('.text').data(), elf.get_section_by_name('.text')['sh_addr']))
callers = [i.address for i in all_text if i.mnemonic == 'bl' and i.op_str == '#0xb00']
assert callers, 'preload helper has no identified original caller'

B, DATA, STACK, DONE = 0x1000000, 0x2000000, 0x2100000, 0x2200000
def run(scenario):
    u = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
    u.mem_map(B, 0x40000)
    for seg in elf.iter_segments():
        if seg['p_type'] == 'PT_LOAD':
            u.mem_write(B + seg['p_vaddr'], seg.data())
    for address, length in ((DATA, 0x1000), (STACK, 0x10000), (DONE, 0x1000)):
        u.mem_map(address, length)
    fname = b'/tmp_wbshd/fx3-p1-worker-candidate.so\0'
    u.mem_write(DATA, fname)
    errors = {'ENOENT': b'fixture: No such file or directory\0',
              'ENOEXEC': b'fixture: invalid ELF header\0',
              'EACCES': b'fixture: Permission denied\0'}
    err = errors.get(scenario)
    if err:
        u.mem_write(DATA + 0x100, err)
    u.mem_write(B + 0x2c040, struct.pack('<I', 3))
    for register, value in ((UC_ARM64_REG_X0, DATA), (UC_ARM64_REG_X1, DATA + 0x500),
                            (UC_ARM64_REG_X2, B + 0x18be8), (UC_ARM64_REG_SP, STACK + 0xff00),
                            (UC_ARM64_REG_X30, DONE)):
        u.reg_write(register, value)
    state = {'scenario': scenario, 'instructions': 0, 'diagnostics': [], 'catch_fixture_calls': 0, 'normal_return': False}
    def cstring(at):
        data = bytes(u.mem_read(at, 256)); assert b'\0' in data
        return data.split(b'\0')[0].decode()
    def ret(value):
        u.reg_write(UC_ARM64_REG_X0, value)
        u.reg_write(UC_ARM64_REG_PC, u.reg_read(UC_ARM64_REG_X30))
    def hook(uc, address, size, _):
        state['instructions'] += 1
        assert state['instructions'] < 1000
        if address == DONE:
            state['normal_return'] = True; uc.emu_stop(); return
        va = address - B
        if va == 0xad0:
            state['catch_fixture_calls'] += 1
            x0, x1, x2, x3, x4 = [uc.reg_read(r) for r in (UC_ARM64_REG_X0, UC_ARM64_REG_X1, UC_ARM64_REG_X2, UC_ARM64_REG_X3, UC_ARM64_REG_X4)]
            assert STACK <= x0 < x1 < STACK + 0x10000
            assert x3 == B + 0xee8 and cstring(struct.unpack('<Q', bytes(uc.mem_read(x4, 8)))[0]) == fname[:-1].decode()
            uc.mem_write(x0, struct.pack('<Q', DATA))
            uc.mem_write(x1, struct.pack('<Q', DATA + 0x100 if err else 0))
            uc.mem_write(x2, b'\0')
            if scenario == 'success_new':
                uc.mem_write(B + 0x2c040, struct.pack('<I', 4))
            ret({'ENOENT': 2, 'ENOEXEC': 8, 'EACCES': 13}.get(scenario, 0))
        elif va == 0xe530:
            x0, x1, x2, x3, x4 = [uc.reg_read(r) for r in (UC_ARM64_REG_X0, UC_ARM64_REG_X1, UC_ARM64_REG_X2, UC_ARM64_REG_X3, UC_ARM64_REG_X4)]
            assert x0 == 2 and x1 == B + 0x17bd0 and x2 == DATA and x3 == B + 0x18be8
            assert err and cstring(x4) == err[:-1].decode()
            state['diagnostics'].append({'format_VA': '0x17bd0', 'from': cstring(x3), 'fixture_error': cstring(x4)})
            ret(0)
        else:
            assert 0xb00 <= va < 0xb94, ('unexpected original path', hex(va))
    def no_syscall(uc, number, _):
        raise AssertionError(('unexpected guest SVC', number))
    u.hook_add(UC_HOOK_CODE, hook)
    u.hook_add(UC_HOOK_INTR, no_syscall)
    u.emu_start(B + 0xb00, DONE + 4, count=1000)
    assert state['normal_return'] and state['catch_fixture_calls'] == 1
    state['return_w0'] = u.reg_read(UC_ARM64_REG_X0) & 0xffffffff
    assert state['return_w0'] == (1 if scenario == 'success_new' else 0)
    assert len(state['diagnostics']) == (1 if err else 0)
    for seg in elf.iter_segments():
        if seg['p_type'] == 'PT_LOAD' and seg['p_flags'] & 1:
            assert bytes(u.mem_read(B + seg['p_vaddr'], seg['p_filesz'])) == seg.data()
    return state
cases = [run(s) for s in ('ENOENT', 'ENOEXEC', 'EACCES', 'success_new', 'success_duplicate')]

url = 'https://raw.githubusercontent.com/bminor/glibc/glibc-2.25/elf/rtld.c'
with urllib.request.urlopen(url, timeout=30) as response:
    upstream = response.read(200001)
assert len(upstream) < 200001 and b'do_preload (const char *fname' in upstream
with (HERE / 'glibc-2.25-rtld-source.txt').open('xb') as out:
    out.write(upstream)
report = {'status': 'ORIGINAL_LOADER_PRELOAD_ERROR_CONSUMER_RETURNS_NORMALLY_IN_BOUNDED_FIXTURES',
          'root_image_sha256': inventory['root_image_sha256'],
          'loader_sha256': sha256(raw).hexdigest(),
          'original_do_preload': {'VA': '0xb00', 'bytes': len(function), 'sha256': sha256(function).hexdigest(),
                                  'original_instructions': [f'{i.address:08x} {i.mnemonic} {i.op_str}' for i in instructions],
                                  'direct_caller_VAs': [hex(x) for x in callers]},
          'startup_files': scripts, 'cases': cases,
          'upstream_reference': {'url': url, 'sha256': sha256(upstream).hexdigest(),
                                 'use': 'Source comparison only; original Sony loader bytes, not upstream rebuild, were emulated.'},
          'proven_local_behavior': 'Given a caught missing/invalid/permission-error result, original helper emits a warning and returns0 rather than terminating. Newly loaded returns1; duplicate returns0.',
          'recovery_inference': 'If actual boot follows these files, tmp_wbshd is recreated as tmpfs while etc preload may persist. A missing volatile library then has a nonfatal caught-error consumer. This supports designing a fallback, but is NOT a cold-boot, constructor-failure or brick-recovery test.',
          'not_proven': ['actual rootfs/mount/boot path on current body', 'real missing-file lookup and exception catch',
                         'complete ld.so startup', 'module ELF acceptance or constructor execution',
                         'crashing/hanging constructor recovery', 'p1 writeback or independent rescue'],
          'original_instructions_replaced': False,
          'real_filesystem_kernel_loader_or_camera_operations': 0}
with (HERE / 'preload-recovery-review.json').open('x') as out:
    json.dump(report, out, indent=2); out.write('\n')
print(json.dumps({'cases': len(cases), 'original_loader_helper': '0xb00',
                  'preload_error_result_nonfatal': True, 'etc_is_declared_persistent': True,
                  'tmp_wbshd_is_declared_tmpfs': True, 'physical_boot_or_recovery_proven': False,
                  'new_camera_operations': 0}))
