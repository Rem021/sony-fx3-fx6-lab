#!/usr/bin/env python3
"""Bounded AArch64 static xrefs. Candidate references must be reviewed."""
from pathlib import Path
import json
import re
import struct
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
from extract_color_tables import read_image, descriptors, BASE, HERE


def sx(v, width):
    return v - (1 << width) if v & (1 << (width - 1)) else v


def main():
    data = read_image()
    records = descriptors(data)
    wanted = {r['descriptor_offset']: r['name'] for r in records.values()}
    wanted.update({r['data_offset']: r['name'] + ':data' for r in records.values()})
    ranges = [(0xbde000, 0xbf8fb4), (0xc148bc, 0xc1b134), (0xcab4e4, 0xcb70e0)]
    selected = lambda x: x in wanted or any(a <= x < z for a, z in ranges)
    absolute = []
    for m in re.finditer(b'\xc0\xff\xff\xff', data):
        off = m.start() - 4
        if off < 0 or off % 4:
            continue
        value = struct.unpack_from('<Q', data, off)[0] - BASE
        if selected(value):
            absolute.append(dict(offset=hex(off), target=hex(value), name=wanted.get(value)))
    adrp = []
    for pc in range(0, len(data) - 24, 4):
        word = struct.unpack_from('<I', data, pc)[0]
        if word & 0x9f000000 != 0x90000000:
            continue
        rd = word & 31
        imm = (((word >> 5) & 0x7ffff) << 2) | ((word >> 29) & 3)
        page = ((BASE + pc) & ~4095) + (sx(imm, 21) << 12)
        if not any((BASE + a - 4096) <= page <= (BASE + z) for a, z in ranges):
            continue
        for delta in range(4, 24, 4):
            add = struct.unpack_from('<I', data, pc + delta)[0]
            if add & 0xff800000 != 0x91000000 or (add >> 5) & 31 != rd:
                continue
            value = page + (((add >> 10) & 4095) << (12 if add & 0x400000 else 0)) - BASE
            if selected(value):
                adrp.append(dict(adrp=hex(pc), add=hex(pc + delta), target=hex(value), name=wanted.get(value)))
    md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
    out = HERE / 'xref-disassembly'
    out.mkdir(exist_ok=True)
    for ref in adrp:
        pc = int(ref['adrp'], 16)
        begin, end = max(0, pc - 96), min(len(data), pc + 160)
        listing = '\n'.join(f'{i.address - BASE:08x}: {i.mnemonic} {i.op_str}'
                            for i in md.disasm(data[begin:end], BASE + begin))
        (out / f'{pc:08x}.txt').write_text(json.dumps(ref) + '\n' + listing + '\n')
    (HERE / 'color-xrefs.json').write_text(json.dumps(dict(absolute=absolute, adrp_add_candidates=adrp,
        limits='ADRP/ADD within 5 instructions is candidate-only until intervening definitions and control flow are checked.'), indent=2) + '\n')
    print('absolute', len(absolute), 'adrp/add', len(adrp))
    print(json.dumps([r for r in adrp if 'VENICE' in str(r.get('name'))][:6], indent=2))
    # Diagnostic command/source strings help identify whether table consumers are production or test routes.
    strings = [(m.start(), m.group().decode()) for m in re.finditer(rb'[\x20-\x7e]{5,300}', data)]
    matches = [{'offset': hex(o), 'text': s} for o, s in strings
               if re.search(r'mlut|monitor.?lut|vfx.*(?:lut|matrix)|dsp.*(?:reg|data)', s, re.I) and not s.startswith('MLUT_')]
    (HERE / 'color-command-strings.json').write_text(json.dumps(matches, indent=2) + '\n')
    print('non-descriptor color strings', len(matches))
    print(json.dumps(matches[:30], indent=2))


if __name__ == '__main__':
    main()
