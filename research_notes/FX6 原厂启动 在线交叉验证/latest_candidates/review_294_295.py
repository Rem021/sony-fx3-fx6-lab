#!/usr/bin/env python3
"""Offline review of completed 293/294/295 and source/ELF contract differences."""
import argparse
import difflib
import importlib.util
import io
import json
from pathlib import Path
import re
import struct
from elftools.elf.elffile import ELFFile
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def vma(e, raw, address, size):
    for s in e.iter_segments():
        if s['p_type'] == 'PT_LOAD' and s['p_vaddr'] <= address < address + size <= s['p_vaddr'] + s['p_filesz']:
            off = s['p_offset'] + address - s['p_vaddr']
            return raw[off:off + size]
    raise ValueError('VMA outside file-backed PT_LOAD')


def inspect_elf(raw, names, lr=None):
    e = ELFFile(io.BytesIO(raw))
    symbols = {}
    for sec in e.iter_sections():
        if sec['sh_type'] in ('SHT_SYMTAB', 'SHT_DYNSYM'):
            for s in sec.iter_symbols():
                if s['st_shndx'] != 'SHN_UNDEF' and (s.name in names or lr is not None and s['st_value'] <= lr < s['st_value'] + s['st_size']):
                    symbols[s.name] = {'vma': hex(s['st_value']), 'bytes': s['st_size']}
    dis = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
    # Only short ABI-relevant entry summaries, never a firmware disassembly export.
    for n in ('Backup_read', 'Backup_nread'):
        if n in symbols:
            a = int(symbols[n]['vma'], 16)
            symbols[n]['first_instructions'] = [f'{x.mnemonic} {x.op_str}' for x in dis.disasm(vma(e, raw, a, min(24, symbols[n]['bytes'])), a)]
    return symbols


def got_table(raw):
    e = ELFFile(io.BytesIO(raw))
    found = None
    for s in e.get_section_by_name('.symtab').iter_symbols():
        if s.name == 'got_tab': found = s; break
    if found is None: return []
    table = vma(e, raw, found['st_value'], found['st_size'])
    selected = []
    for i in range(0, len(table), 16):
        off, nameptr = struct.unpack('<QQ', table[i:i+16])
        name = vma(e, raw, nameptr, 96).split(b'\0', 1)[0].decode(errors='replace')
        if name.startswith('Backup_') or name == 'osal_rcv_msg_tmo':
            selected.append({'name': name, 'appfw_slot_vma': hex(off)})
    return selected


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--scanner', type=Path, required=True)
    p.add_argument('--base-review', type=Path, required=True)
    p.add_argument('--source-dir', type=Path, required=True)
    a = p.parse_args()
    review = load(a.base_review, 'runtime_review')
    scanner = load(a.scanner, 'cpio_scan')
    review.WANTED = (*review.WANTED, 'usr/lib/libbackup.so')
    runs, inits = [], []
    for n in (293, 294, 295):
        r, init = review.run_review(a.root, n, scanner)
        if r['status'] != 'completed': raise ValueError('no completed receipt')
        run = a.root / 'runs' / r['run']
        text = (run / 'serial.log').read_text(errors='replace')
        lines = text.splitlines()
        r['line_count'] = len(lines)
        r['exact_diagnostics'] = [{'line': i+1, 'text': l[:700]} for i, l in enumerate(lines)
            if re.search(r'FX6_PATCH_NOP|fix_got|stub first=|APPFW_(?:SEGV|PC_MODULE|LR_MODULE)|Backup_|BACKUP_|qid=|caller=|caller_lr=|lr=', l)]
        r['fault_scan'] = {k: [{'line': i+1, 'text': l[:700]} for i, l in enumerate(lines) if re.search(pat, l, re.I)]
            for k, pat in {'assert':r'\bassert at |Assertion .*failed', 'segv':r'APPFW_SEGV|SEGV \(PC=', 'oops':r'\bOops:|Internal error:|Kernel panic|\bBUG:'}.items()}
        r['real_receive_argument_records'] = [l for l in lines if re.search(r'osal_rcv_msg_tmo.*(?:qid=|caller=|lr=)', l)]
        r['receive_wchan_count'] = sum(l.strip() == 'osal_rcv_msg_tmo' for l in lines)
        thread_samples = {}
        for i, line in enumerate(lines):
            match = re.search(r'FX6_NATIVE_THREAD_BEGIN_(\d+)', line)
            if match and i+2 < len(lines) and f'FX6_NATIVE_THREAD_END_{match[1]}' in lines[i+2]:
                tid = match[1]
                row = thread_samples.setdefault(tid, {'count':0,'wchan_values':[],'first_line':i+1})
                row['count'] += 1
                value = lines[i+1].strip()
                if value not in row['wchan_values']: row['wchan_values'].append(value)
                row['last_line'] = i+1
        r['thread_wchan_summary'] = thread_samples
        binding = r['full_container_binding']; members = binding['selected_actual_members']; cpio = Path(binding['initrd']['path'])
        shim = review.payload(cpio, members['usr/lib/libgrm-fbinit9.so'])
        launcher = review.payload(cpio, members['usr/bin/appfw-launch'])
        backup = review.payload(cpio, members['usr/lib/libbackup.so'])
        lr = int(r['explicit_appfw_exception']['lr_offset'],16) if r['explicit_appfw_exception'] and 'lr_offset' in r['explicit_appfw_exception'] else None
        r['actual_backup_abi'] = inspect_elf(backup, {'Backup_read', 'Backup_nread'})
        r['actual_shim_exports'] = inspect_elf(shim, {'Backup_read', 'Backup_nread', 'Backup_read_8Byte', 'Backup_get_suspend_flag'}, lr)
        r['actual_launcher_got_subset'] = got_table(launcher)
        r['tmp_binary_bindings'] = []
        for temp, name in ((Path(f'/tmp/libgrm-fbinit25-{n}.so'), 'usr/lib/libgrm-fbinit9.so'),
                           (Path('/tmp/appfw/appfw-launch294'), 'usr/bin/appfw-launch')):
            if temp.exists(): r['tmp_binary_bindings'].append({**review.fp(temp), 'matches_cpio_member': review.digest(temp)==members[name]['sha256'], 'member':name})
        r['source_runtime_evidence_limit'] = 'No readback of runtime GOT slots or patched code bytes, and no Backup shim entry/exit records were found by this review.'
        runs.append(r); inits.append(init)
    differences = []
    for i in (1,2):
        old,new = runs[i-1],runs[i]
        oldmembers=old['full_container_binding']['selected_actual_members']; newmembers=new['full_container_binding']['selected_actual_members']
        differences.append({'from':old['candidate'],'to':new['candidate'],
            'changed_selected_member_payloads':[name for name in oldmembers if
                (oldmembers.get(name) or {}).get('sha256') != (newmembers.get(name) or {}).get('sha256') or
                (oldmembers.get(name) or {}).get('bytes') != (newmembers.get(name) or {}).get('bytes')],
            'changed_library_payloads':[name for name in old['all_effective_library_entries'] if old['all_effective_library_entries'].get(name)!=new['all_effective_library_entries'].get(name)],
            'init_diff':list(difflib.unified_diff(inits[i-1].splitlines(),inits[i].splitlines(),lineterm=''))})
    sources = {p.name:review.fp(p) for p in a.source_dir.glob('*.c')}
    source_diff={}
    for before,after in (('libgrm-fbinit25-293.c','libgrm-fbinit25-294.c'),('libgrm-fbinit25-294.c','libgrm-fbinit25-295.c'),('appfw-launch288.c','appfw-launch294.c')):
        source_diff[before+' -> '+after]=list(difflib.unified_diff((a.source_dir/before).read_text().splitlines(),(a.source_dir/after).read_text().splitlines(),lineterm=''))
    print(json.dumps({'schema':'fx6-latest-candidates-offline-v1','runs':runs,'differences':differences,'source_fingerprints':sources,'source_diff':source_diff,
        'tools':[review.fp(a.scanner),review.fp(a.base_review)],'method':'offline completed artifacts only; no sockets/process control'},ensure_ascii=False,indent=2))


if __name__ == '__main__':main()
