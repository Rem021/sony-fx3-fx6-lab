"""Build AP11 with the upstream ten-service filter at audited FX3 rows.
Execute the existing pinned AP10 builder with a narrow reviewed injection; leave
all historical builders, source payloads, DTB placement and init behavior intact.
"""
from pathlib import Path
import hashlib
import json
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
source = ROOT / 'build_ap10_full_v4.py'
text = source.read_text()
assert hashlib.sha256(source.read_bytes()).hexdigest() == '6ccb599331a0dfb82434864692b03988194c3af471a474be77b190befcfa0617'
text = text.replace("DEST = ROOT / 'ap10-full-v4'", "DEST = ROOT / 'ap14-signal'")
anchor = '    # The source proof binds these exact argv and documents fork/execve inheritance.'
assert text.count(anchor) == 1
injection = '''    signal_helper = ROOT / 'helpers/signal-observe.so'
    entries['simulation/signal-observe.so'] = {'name': 'simulation/signal-observe.so', 'mode': 0o100755, 'file': signal_helper, 'size': signal_helper.stat().st_size, 'sha256': sha(signal_helper)}
    # FX3-only table positions; same named filter policy as pinned upstream.
    table = json.loads((SOURCE / 'ap-projection/projection-manifest-v3.json').read_text())['imdb']
    names = set(json.loads((ROOT.parent / 'success-cases/imdb-entry-filter-contract-v2.json').read_text())['actual_upstream_IMDB_filter']['names'])
    names.add('libResourceBluetooth.so')
    original_entry = entries['usr/lib/libIMDB.so']
    original = original_entry['file'].read_bytes() if 'file' in original_entry else original_entry['data']
    assert hashlib.sha256(original).hexdigest() == table['sha256']
    derived = bytearray(original)
    phoff = struct.unpack_from('<Q', original, 32)[0]
    phsize, phnum = struct.unpack_from('<HH', original, 54)
    def offset(va, length):
        for i in range(phnum):
            typ, flags, off, vaddr, paddr, size, memsz, align = struct.unpack_from('<II6Q', original, phoff + i * phsize)
            if typ == 1 and vaddr <= va and va + length <= vaddr + size:
                return off + va - vaddr
        raise ValueError(hex(va))
    changes = []
    for row in table['rows']:
        name = row['strings_by_pointer_slot'].get('2')
        if name not in names:
            continue
        va = int(row['original_va'], 16)
        off = offset(va, 72)
        assert original[off:off+72].hex() == row['raw_hex']
        mask = struct.unpack_from('<I', original, off + 8)[0]
        assert mask == int(row['target_mask'], 16) and mask & 7
        struct.pack_into('<I', derived, off + 8, mask & ~7)
        changes.append({'name': name, 'row_va': hex(va), 'file_offset': off+8, 'before_mask': hex(mask), 'after_mask': hex(mask & ~7)})
    assert len(changes) == 11 and {r['name'] for r in changes} == names
    allowed = {r['file_offset']+i for r in changes for i in range(4)}
    assert all(a == b or i in allowed for i, (a,b) in enumerate(zip(original, derived)))
    derived_path = DEST / 'libIMDB-filtered.so'
    derived_path.write_bytes(derived)
    entries['simulation/libIMDB.so'] = {'name': 'simulation/libIMDB.so', 'mode': 0o100755}
    entries['simulation/libIMDB.so'].update({'file': derived_path, 'size': len(derived), 'sha256': sha(derived_path), 'source': 'explicit FX3 derived ten-service IMDB filter'})
    (DEST / 'imdb-filter-receipt.json').write_text(json.dumps({'input_sha256': table['sha256'], 'output_sha256': sha(derived_path), 'changes': changes, 'changed_bytes': sum(a!=b for a,b in zip(original,derived)), 'policy_source': 'upstream ten services plus explicit FX3-only ResourceBluetooth: AP12 user stack libResourceBluetooth+1454 issuing c0104702 faults in kernel; no Bluetooth hardware model' , 'scope': 'virtual platform service filter, not original firmware or physical-camera patch'}, indent=2)+'\\n')
'''
text = text.replace(anchor, injection + anchor)
text = text.replace('candidate10.json', 'candidate14.json')
text = text.replace('LD_PRELOAD=/simulation/ioctl-trace.so /usr/bin/bootin.elf', 'LD_LIBRARY_PATH=/simulation:/usr/lib:/lib LD_PRELOAD=/simulation/ioctl-trace.so /usr/bin/bootin.elf')
text = text.replace('Five original service modules only preloaded.', 'Five original service modules only preloaded; explicit derived IMDB upstream ten-service filter plus FX3-only ResourceBluetooth exclusion after observed GPIO fault.')
text = text.replace(' echo FX3_AP_NATURAL_BOOTIN_BEGIN', ' echo FX3_GRM_MA_BEGIN\n /bin/busybox insmod /usr/kmod/grm_ma.ko\n grm_rc=$?\n echo FX3_GRM_MA_RC=$grm_rc\n if [ \"$grm_rc\" != 0 ]; then while true; do /bin/busybox sleep 1; done; fi\n echo FX3_AP_NATURAL_BOOTIN_BEGIN')
text = text.replace("    entries['init']['data'] = init.encode()", "    init = init.replace('LD_PRELOAD=/simulation/ioctl-trace.so', 'LD_PRELOAD=/simulation/signal-observe.so:/simulation/ioctl-trace.so')\n    entries['init']['data'] = init.encode()")
exec(compile(text, str(source), 'exec'), {'__file__': str(source), '__name__': '__main__'})
