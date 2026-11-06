"""Static AP process launch inventory and original rootfs loader identities.
No firmware execution, symlink creation/following, external client or device I/O.
"""
from pathlib import Path
from hashlib import sha256
import importlib.util, io, json, re
from elftools.elf.elffile import ELFFile
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
HERE = Path(__file__).resolve().parent
BASE = HERE.parent
reader = BASE / 'stage2/extraction/read_filesystems.py'
assert sha256(reader.read_bytes()).hexdigest() == 'eecbe9b099f9fbc8f8e06759c5e8a2ce9910e0f365ae9891fe0887353edc31ad'
spec = importlib.util.spec_from_file_location('fixed_read_only_fs', reader)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
fs = m.Ext2(BASE / 'stage2/extraction/nflasha15.img')
assert sha256(fs.b).hexdigest() == 'df0a2cf2ebb0d884605d041a6dcb701092bd36848956855b8d3d7a7164a3a1c5'
old = json.loads((BASE / 'stage148-initial-MSC-handler-inventory/AP-handler-inventory.json').read_text())
launch = {'execve', 'execv', 'execvp', 'execl', 'execlp', 'execle', 'fexecve',
          'system', 'popen', 'posix_spawn', 'posix_spawnp', 'vfork', 'fork', 'clone'}
md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
md.skipdata = True  # AArch64 skips undecodable aligned 4-byte words; record gaps.
records = []
for rec in old['ELF_records']:
    raw = fs.data(rec['inode'])
    assert sha256(raw).hexdigest() == rec['sha256']
    e = ELFFile(io.BytesIO(raw)); table = e.get_section_by_name('.dynsym')
    if table is None:
        continue
    symbols = list(table.iter_symbols())
    found = [s for s in symbols if s.name in launch]
    if not found:
        continue
    dynamic = e.get_section_by_name('.dynamic')
    needs = [t.needed for t in dynamic.iter_tags() if t.entry.d_tag == 'DT_NEEDED'] if dynamic else []
    targets = {s['st_value']: s.name for s in found if s['st_shndx'] != 'SHN_UNDEF'}
    plt, rela = e.get_section_by_name('.plt'), e.get_section_by_name('.rela.plt')
    if plt and rela:
        for i, r in enumerate(rela.iter_relocations()):
            name = table.get_symbol(r['r_info_sym']).name
            if name in launch:
                targets[plt['sh_addr'] + 32 + i * 16] = name
    funcs = [s for s in symbols if s['st_info']['type'] == 'STT_FUNC' and s['st_size']]
    calls = []
    coverage = {'section_bytes': 0, 'decoded_instruction_bytes': 0, 'skipped_data_bytes': 0, 'skipped_data_offsets': []}
    text = e.get_section_by_name('.text')
    if text:
        coverage['section_bytes'] = text['sh_size']
        for ins in md.disasm_lite(text.data(), text['sh_addr']):
            at, size, op, args = ins
            assert at % 4 == 0 and size == 4
            if op.startswith('.'):
                coverage['skipped_data_bytes'] += size
                coverage['skipped_data_offsets'].append(hex(at))
            else:
                coverage['decoded_instruction_bytes'] += size
            if op not in ('b', 'bl') or not args.startswith('#0x'):
                continue
            dest = int(args[1:], 16)
            if dest in targets:
                owners = [{'name': s.name, 'VA': hex(s['st_value']), 'bytes': s['st_size']} for s in funcs
                          if s['st_value'] <= at < s['st_value'] + s['st_size']]
                calls.append({'VA': hex(at), 'instruction': op + ' ' + args, 'destination': hex(dest),
                              'target': targets[dest], 'containing_dynamic_symbols': owners})
        assert coverage['section_bytes'] == coverage['decoded_instruction_bytes'] + coverage['skipped_data_bytes']
    strings = [s.decode('ascii') for s in re.findall(rb'[\x20-\x7e]{5,}', raw)
               if any(v in s for v in (b'/tmp_wbshd', b'/etc/ld.so.preload', b'/bin/sh', b'/bin/date'))]
    records.append({'paths': rec['image_paths'], 'inode': rec['inode'], 'bytes': len(raw),
                    'sha256': rec['sha256'], 'needed': needs,
                    'launch_symbols': [{'name': s.name, 'VA': hex(s['st_value']), 'bytes': s['st_size'], 'section': s['st_shndx']} for s in found],
                    'direct_calls': calls, 'selected_strings': strings, 'text_scan_coverage': coverage})

root = m.Ext2(BASE / 'stage2/extraction/nflasha7.img')
root_records = []
for rec in root.walk():
    if rec['path'] not in ('/bin/sh', '/bin/date', '/bin/busybox', '/lib/ld-linux-aarch64.so.1', '/lib/ld-2.25.so', '/lib/libc.so.6', '/lib/libc-2.25.so'):
        continue
    raw = root.data(rec['inode'])
    d = {'path': rec['path'], 'inode': rec['inode'], 'inode_type': rec['type'],
         'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}
    if rec['type'] == 0xa000:
        d['symlink_text_only'] = raw.decode()
    elif raw.startswith(b'\x7fELF'):
        e = ELFFile(io.BytesIO(raw))
        d.update(elf_type=e['e_type'], machine=e['e_machine'], entry=hex(e['e_entry']),
                 interp=[s.data().split(b'\0')[0].decode() for s in e.iter_segments() if s['p_type'] == 'PT_INTERP'])
        dynamic = e.get_section_by_name('.dynamic')
        d['needed'] = [t.needed for t in dynamic.iter_tags() if t.entry.d_tag == 'DT_NEEDED'] if dynamic else []
        d['preload_literal_offsets'] = [x.start() for x in re.finditer(re.escape(b'/etc/ld.so.preload'), raw)]
    root_records.append(d)
report = {'status': 'STATIC_AP_PROCESS_LAUNCH_AND_ROOT_LOADER_INVENTORY',
          'AP_image_sha256': sha256(fs.b).hexdigest(), 'root_image_sha256': sha256(root.b).hexdigest(),
          'ELFs_reverified': len(old['ELF_records']), 'launch_files': records, 'root_files': root_records,
          'scope': 'Only exact dynamic launch names and direct branches. Raw syscalls, indirect branches, constructed command names, other partitions and runtime modifications are not ruled out.',
          'original_Sony_or_public_client_execution': False, 'new_camera_operations': 0}
with (HERE / 'launch-inventory-v2.json').open('x') as f:
    json.dump(report, f, indent=2); f.write('\n')
print(json.dumps({'ELFs_reverified': len(old['ELF_records']), 'launch_files': len(records),
                  'candidates': [{'paths': r['paths'], 'launch_symbols': [s['name'] for s in r['launch_symbols']],
                                  'direct_call_count': len(r['direct_calls'])} for r in records],
                  'root_loader_files': root_records, 'new_camera_operations': 0}))
