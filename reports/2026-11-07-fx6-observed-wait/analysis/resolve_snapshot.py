#!/usr/bin/env python3
"""Resolve recorded user addresses using their exact CPIO ELF PT_LOAD mappings.

No guest connection, writes, unwinding guesses, or VA=file-offset assumption.
Input JSON is a recorded /proc/maps text plus explicitly labelled addresses.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
from elftools.elf.elffile import ELFFile


def member(archive, wanted):
    """Read exact newc member; preserve traversal beyond intermediate trailers."""
    found = None
    with Path(archive).open('rb') as f:
        while True:
            h = f.read(110)
            if not h:
                break
            if h == b'\0'*len(h):
                if any(f.read()):
                    raise ValueError('nonzero data after archive padding')
                break
            if len(h) != 110 or h[:6] not in (b'070701', b'070702'):
                raise ValueError('invalid newc header at '+str(f.tell()-len(h)))
            fields = [int(h[6+8*i:14+8*i], 16) for i in range(13)]
            size, namesize = fields[6], fields[11]
            raw = f.read(namesize)
            if len(raw) != namesize or not raw.endswith(b'\0'):
                raise ValueError('invalid member name')
            name = raw[:-1].decode()
            f.seek((-f.tell()) % 4, 1)
            if name.lstrip('./') == wanted.lstrip('./'):
                if found is not None:
                    raise ValueError('duplicate target member: '+wanted)
                found = f.read(size)
                if len(found) != size:
                    raise ValueError('short member')
            else:
                f.seek(size, 1)
            f.seek((-f.tell()) % 4, 1)
            # This project's archives can contain records after TRAILER!!!.
    if found is None:
        raise ValueError('member absent: '+wanted)
    return found


def parse_maps(text):
    result = []
    for line in text.splitlines():
        m = re.search(r'(?<![0-9a-f])([0-9a-f]+)-([0-9a-f]+) ([rwxps-]{4}) ([0-9a-f]+) [0-9a-f:]+ \d+\s*(.*)', line)
        if m:
            a, b, perms, offset, path = m.groups()
            result.append(dict(start=int(a,16), end=int(b,16), perms=perms,
                               offset=int(offset,16), path=path))
    return result


def resolve(archive, maps, address):
    address = int(address, 0) if isinstance(address, str) else address
    out = {'address':hex(address)}
    matches = [m for m in maps if m['start'] <= address < m['end']]
    if len(matches) != 1:
        return dict(out, status='no_unique_mapping')
    mapping = matches[0]
    out['mapping'] = {k:hex(v) if isinstance(v,int) else v for k,v in mapping.items()}
    if not mapping['path'].startswith('/') or ' (deleted)' in mapping['path']:
        return dict(out, status='not_file_backed')
    try:
        data = member(archive, mapping['path'])
    except ValueError as exc:
        return dict(out, status='member_unresolved', error=str(exc))
    out['elf_sha256'] = hashlib.sha256(data).hexdigest()
    out['elf_bytes'] = len(data)
    elf = ELFFile(io.BytesIO(data))
    if elf['e_machine'] != 'EM_AARCH64' or elf.elfclass != 64:
        return dict(out, status='not_aarch64_elf')
    # Linux mapping offsets are page aligned; confirm load bias by every
    # segment compatible with the selected file mapping.
    biases = set()
    for s in elf.iter_segments():
        if s['p_type'] != 'PT_LOAD':
            continue
        if ('x' in mapping['perms']) != bool(s['p_flags'] & 1):
            continue
        # This harness temporarily makes patched code pages writable; W in
        # /proc/maps therefore need not equal the original ELF PF_W flag.
        off = s['p_offset'] & ~4095
        va = s['p_vaddr'] & ~4095
        extent = ((s['p_offset']+s['p_filesz']+4095) & ~4095)-off
        if off <= mapping['offset'] < off+extent:
            biases.add(mapping['start']-(va+mapping['offset']-off))
    if len(biases) != 1:
        return dict(out, status='ambiguous_PT_LOAD_bias' if biases else 'no_PT_LOAD_bias',
                    biases=[hex(x) for x in sorted(biases)])
    bias = biases.pop()
    va = address-bias
    segments = [s for s in elf.iter_segments() if s['p_type']=='PT_LOAD'
                and s['p_vaddr'] <= va < s['p_vaddr']+s['p_filesz']]
    if len(segments) != 1:
        return dict(out, status='not_unique_file_backed_PT_LOAD', elf_va=hex(va))
    s = segments[0]
    file_offset = s['p_offset']+va-s['p_vaddr']
    out.update(status='resolved', load_bias=hex(bias), elf_va=hex(va), file_offset=hex(file_offset),
               executable=bool(s['p_flags'] & 1))
    symbols = []
    for table in (elf.get_section_by_name('.dynsym'), elf.get_section_by_name('.symtab')):
        if table:
            for sym in table.iter_symbols():
                if sym['st_info']['type'] == 'STT_FUNC' and sym['st_size'] > 0 and sym['st_value'] <= va < sym['st_value']+sym['st_size']:
                    symbols.append({'name':sym.name,'start':hex(sym['st_value']),
                                    'bytes':sym['st_size'],'offset':hex(va-sym['st_value'])})
    out['covering_function_symbols'] = list({json.dumps(x,sort_keys=True):x for x in symbols}.values())
    if s['p_flags'] & 1:
        start = max(s['p_vaddr'], (va-16)&~3)
        end = min(s['p_vaddr']+s['p_filesz'], va+16)
        begin = s['p_offset']+start-s['p_vaddr']
        cs = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
        out['instructions'] = [{'va':hex(i.address),'assembly':i.mnemonic+' '+i.op_str}
                               for i in cs.disasm(data[begin:begin+end-start], start)]
        out['preceding_instruction'] = next((i for i in out['instructions'] if int(i['va'],16)==va-4), None)
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive', type=Path, required=True)
    p.add_argument('--archive-sha256', required=True)
    p.add_argument('--input', type=Path, required=True)
    args = p.parse_args()
    h=hashlib.sha256()
    with args.archive.open('rb') as f:
        for block in iter(lambda:f.read(4*1024*1024), b''):h.update(block)
    if h.hexdigest() != args.archive_sha256:
        raise ValueError('snapshot CPIO identity mismatch')
    request = json.loads(args.input.read_text())
    maps = parse_maps(request['maps'])
    results = []
    for item in request['addresses']:
        results.append(dict(item, resolution=resolve(args.archive, maps, item['address'])))
    print(json.dumps({'archive_sha256':h.hexdigest(),'maps_sha256':hashlib.sha256(request['maps'].encode()).hexdigest(),
                      'scope':'Recorded registers/frame records only; an FP chain is not a complete unwind',
                      'addresses':results},indent=2))


if __name__ == '__main__':
    main()
