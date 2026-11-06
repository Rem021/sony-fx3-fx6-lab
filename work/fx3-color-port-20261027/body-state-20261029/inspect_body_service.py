#!/usr/bin/env python3
"""Read-only original UPM service references, section-aware ET_REL symbols."""
import hashlib, io, json, struct, sys
from pathlib import Path
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN
from elftools.elf.elffile import ELFFile

HERE = Path(__file__).resolve().parent
TASK = HERE.parent
FS = TASK.parents[1] / 'work/sony-firmware-20261024/stage2/extraction'
PARENT_PIN = '40181b37d8d89158e2eda8da7cb92c6bcddba29504c2472a17a3fd7aa33abbb4'

def sha(raw): return hashlib.sha256(raw).hexdigest()

def main():
    parent = TASK / 'lens-state-20261029'
    receipt = parent / 'final-receipt.json'
    assert sha(receipt.read_bytes()) == PARENT_PIN
    manifest = json.loads(receipt.read_text())
    for item in manifest['files']:
        raw = (parent / item['path']).read_bytes()
        assert len(raw) == item['bytes'] and sha(raw) == item['sha256']
    image = FS / 'nflasha15.img'
    with image.open('rb') as f:
        assert hashlib.file_digest(f, 'sha256').hexdigest() == 'df0a2cf2ebb0d884605d041a6dcb701092bd36848956855b8d3d7a7164a3a1c5'
    sys.path.insert(0, str(FS))
    from read_filesystems import Ext2
    fs = Ext2(image)
    entry = next(r for r in fs.walk() if r['path'] == '/kmod/upm.ko')
    raw = fs.data(entry['inode'])
    expected = next(r['source_sha256'] for r in json.loads((parent / 'service-location-results.json').read_text())['ap_mov_wide_matches'] if r['path'] == '/kmod/upm.ko')
    assert len(raw) == entry['size'] and sha(raw) == expected
    out = HERE / 'original-members'; out.mkdir(exist_ok=True)
    dest = out / 'upm.ko'
    if dest.exists(): assert dest.read_bytes() == raw
    else: dest.write_bytes(raw)
    elf = ELFFile(io.BytesIO(raw)); assert elf['e_type'] == 'ET_REL'
    symbols = list(elf.get_section_by_name('.symtab').iter_symbols())
    text = elf.get_section_by_name('.text'); index = next(i for i, s in enumerate(elf.iter_sections()) if s.name == '.text')
    functions = [s for s in symbols if s['st_info']['type'] == 'STT_FUNC' and s['st_shndx'] == index and s['st_size']]
    relocations = {}
    for sec in elf.iter_sections():
        if sec['sh_type'] != 'SHT_RELA' or sec['sh_info'] != index: continue
        for rel in sec.iter_relocations():
            sym = symbols[rel['r_info_sym']]
            relocations.setdefault(rel['r_offset'], []).append(dict(symbol=sym.name, addend=rel['r_addend'], type=rel['r_info_type'], section=sym['st_shndx']))
    data = text.data(); md = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
    matches = json.loads((parent / 'service-location-results.json').read_text())['ap_mov_wide_matches']
    selected = [r for r in matches if r['path'] == '/kmod/upm.ko']
    ranges = {}
    for row in selected:
        at = int(row['address'], 16)
        owners = [s for s in functions if s['st_value'] <= at < s['st_value'] + s['st_size']]
        for sym in owners:
            ranges[sym.name] = sym
        row['symtab_owners'] = [s.name for s in owners]
    fragments = HERE / 'source-fragments'; fragments.mkdir(exist_ok=True)
    records = []
    for name, sym in sorted(ranges.items(), key=lambda pair: pair[1]['st_value']):
        lo, n = sym['st_value'], sym['st_size']; body = data[lo:lo+n]
        path = fragments / (name.replace('/', '_') + '.txt')
        lines = []
        for ins in md.disasm(body, lo):
            line = f'{ins.address:08x} {ins.mnemonic:10} {ins.op_str}'
            if ins.address in relocations: line += ' ; ' + json.dumps(relocations[ins.address])
            lines.append(line)
        path.write_text('\n'.join(lines) + '\n')
        records.append(dict(name=name, section='.text', section_offset=hex(lo), bytes=n, file_offset=hex(text['sh_offset']+lo), sha256=sha(body), listing=str(path.relative_to(HERE))))
    private = []
    windows = [(0x13a68, 0x13bc0, 'reply-wrapper'), (0x13cf8, 0x13de8, 'command3-handler'),
               (0x13de8, 0x13ef0, 'receiver'), (0x14360, 0x14428, 'thread-start'),
               (0x1ba18, 0x1ba40, 'factor7-copy'), (0x1a248, 0x1a27c, 'power-status-log'),
               (0x144f8, 0x14728, 'power-status-enum-log')]
    for lo, hi, label in windows:
        body = data[lo:hi]; path = fragments / f'private-{label}.txt'
        lines = []
        for ins in md.disasm(body, lo):
            line = f'{ins.address:08x} {ins.mnemonic:10} {ins.op_str}'
            if ins.address in relocations: line += ' ; ' + json.dumps(relocations[ins.address])
            lines.append(line)
        path.write_text('\n'.join(lines)+'\n')
        private.append(dict(label=label, section='.text', offset=hex(lo), bytes=len(body), sha256=sha(body), listing=str(path.relative_to(HERE)), bounds='explicit window; zero-valued ABS64 relocation slots are data, never executed'))
    table_relocations = []
    for sec in elf.iter_sections():
        if sec['sh_type'] != 'SHT_RELA': continue
        for rel in sec.iter_relocations():
            at = rel['r_offset']
            if not (sec['sh_info'] == 12 and 0x9d0 <= at < 0xa08 or sec['sh_info'] == 23 and 0x3f0 <= at < 0x420): continue
            sym = symbols[rel['r_info_sym']]
            table_relocations.append(dict(section=elf.get_section(sec['sh_info']).name, offset=hex(at), type=rel['r_info_type'], target_symbol=sym.name, target_section=sym['st_shndx'], target_value=hex(sym['st_value']), addend=hex(rel['r_addend'])))
    strsec = elf.get_section(14)
    strings = []
    for off in [0x1918,0x1930,0x1940,0x1958,0x1968,0x1980,0x1998,0x1b48,0x1b60]:
        strings.append(dict(section=strsec.name, offset=hex(off), value=strsec.data()[off:].split(b'\0',1)[0].decode(errors='replace')))
    result = dict(parent_files_verified=len(manifest['files']), parent_receipt_sha256=PARENT_PIN,
                  source=dict(original_path='/kmod/upm.ko', inode=entry['inode'], bytes=len(raw), sha256=sha(raw), output=str(dest.relative_to(HERE))),
                  references=selected, functions=records, private_windows=private, table_relocations=table_relocations, strings=strings,
                  symbols=[dict(name=s.name, section=s['st_shndx'], value=hex(s['st_value']), bytes=s['st_size']) for s in symbols if any(w in s.name.lower() for w in ['message', 'msg', 'rcv', 'recv', 'backup', 'battery', 'power'])],
                  scope='ET_REL .text offsets and original relocations, not runtime kernel addresses. All extraction is read-only; no module loading, target-native code, IPC, USB or device action.')
    (HERE / 'service-inspection-results.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(parent_files_verified=len(manifest['files']), source_bytes=len(raw), selected_reference_functions=[r['name'] for r in records])))

if __name__ == '__main__': main()
