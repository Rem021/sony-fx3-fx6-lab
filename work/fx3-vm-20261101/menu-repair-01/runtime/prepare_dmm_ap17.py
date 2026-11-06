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
text = text.replace("DEST = ROOT / 'ap10-full-v4'", "DEST = ROOT / 'ap17-dmm-b'")
anchor = '    # The source proof binds these exact argv and documents fork/execve inheritance.'
assert text.count(anchor) == 1
injection = '''    signal_helper = ROOT / 'helpers/signal-observe-v2.so'
    entries['simulation/signal-observe-v2.so'] = {'name': 'simulation/signal-observe-v2.so', 'mode': 0o100755, 'file': signal_helper, 'size': signal_helper.stat().st_size, 'sha256': sha(signal_helper)}
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
text = text.replace('candidate10.json', 'candidate17.json')
text = text.replace('LD_PRELOAD=/simulation/ioctl-trace.so /usr/bin/bootin.elf', 'LD_LIBRARY_PATH=/simulation:/usr/lib:/lib LD_PRELOAD=/simulation/ioctl-trace.so /usr/bin/bootin.elf')
text = text.replace('Five original service modules only preloaded.', 'Five original service modules only preloaded; explicit derived IMDB upstream ten-service filter plus FX3-only ResourceBluetooth exclusion after observed GPIO fault.')
text = text.replace(' echo FX3_AP_NATURAL_BOOTIN_BEGIN', ' echo FX3_GRM_MA_BEGIN\n /bin/busybox insmod /usr/kmod/grm_ma.ko\n grm_rc=$?\n echo FX3_GRM_MA_RC=$grm_rc\n if [ \"$grm_rc\" != 0 ]; then while true; do /bin/busybox sleep 1; done; fi\n echo FX3_AP_NATURAL_BOOTIN_BEGIN')
text = text.replace("    entries['init']['data'] = init.encode()", "    init = init.replace('LD_PRELOAD=/simulation/ioctl-trace.so', 'LD_PRELOAD=/simulation/signal-observe-v2.so:/simulation/ioctl-trace.so')\n    entries['init']['data'] = init.encode()")
text = text.replace('    /bin/busybox cat \"$procdir/status\" \"$procdir/maps\" \"$procdir/wchan\"', '    /bin/busybox cat "$procdir/status" "$procdir/maps" "$procdir/wchan"\n    /bin/busybox ls -l "$procdir/fd"\n    for taskdir in "$procdir"/task/*; do\n     echo FX3_TASK_SNAPSHOT_${taskdir##*/}_BEGIN\n     /bin/busybox cat "$taskdir/status" "$taskdir/syscall" "$taskdir/stack"\n     echo FX3_TASK_SNAPSHOT_${taskdir##*/}_END\n    done')

text = text.replace('0x408000000', '0x440000000').replace('< 0x480000000', '< 0x540000000')
text = text.replace(' echo FX3_GRM_MA_BEGIN', ' echo FX3_DMM_BEGIN\n /bin/busybox insmod /usr/kmod/dmm.ko DmmConfig=/setting/DmmCfg.bin\n dmm_rc=$?\n echo FX3_DMM_RC=$dmm_rc\n if [ \"$dmm_rc\" != 0 ]; then while true; do /bin/busybox sleep 1; done; fi\n echo FX3_GRM_MA_BEGIN')
text = text.replace("    candidate = {'dtb':", "    candidate = {'memory_mib': 5120, 'initrd_load_address': '0x440000000', 'dtb':")
layout = '''    import importlib.util
    parser_path = ROOT.parents[1] / 'fx3-audit/prepare_virt_dtb.py'
    spec = importlib.util.spec_from_file_location('fx3fdt', parser_path)
    fdt = importlib.util.module_from_spec(spec); spec.loader.exec_module(fdt)
    tree, before, reserve, meta = fdt.parse(bytes(dtb_bytes))
    kemco_row = next(m for m in manifest['members'] if m['guest_path'] == '/setting/kemco.txt')
    kemco_path = Path(kemco_row['local_file'])
    assert sha(kemco_path) == kemco_row['sha256']
    reservations = [line.split()[0] for line in kemco_path.read_text().splitlines() if line.startswith('memrsv=') and 'tmonitor.' not in line]
    memory = next(n for kind,n in tree['items'] if kind == 'node' and n['name'] == 'memory@400000000')
    memory['items'] = [(k,(v[0],struct.pack('>QQ',0x400000000,0x140000000)) if k=='prop' and v[0]=='reg' else v) for k,v in memory['items']]
    chosen = next(n for kind,n in tree['items'] if kind=='node' and n['name']=='chosen')
    chosen['items'] = [(k,(v[0],struct.pack('>Q',0x440000000)) if k=='prop' and v[0]=='linux,initrd-start' else v) for k,v in chosen['items']]
    chosen['items'] = [(k,(v[0],v[1].rstrip(b'\\0')+b' '+(' '.join(reservations)).encode()+b'\\0') if k=='prop' and v[0]=='bootargs' else v) for k,v in chosen['items']]
    dtb_bytes = bytearray(fdt.encode(tree,reserve,meta))
    _, after, reserve_after, _ = fdt.parse(bytes(dtb_bytes))
    assert reserve == reserve_after
    assert struct.unpack('>Q',after[('/chosen','linux,initrd-start')])[0] == 0x440000000
    assert struct.unpack('>Q',after[('/chosen','linux,initrd-end')])[0] == 0x440000000+archive.stat().st_size
    (DEST/'layout-receipt.json').write_text(json.dumps({'initrd_start':'0x440000000','initrd_bytes':archive.stat().st_size,'memory_base':'0x400000000','memory_bytes':'0x140000000','same_model_kemco_sha256':sha(kemco_path),'exact_original_memrsv':reservations,'reserve_map_preserved':True,'rationale':'original GRM needs DMM; high initrd avoids same-model firmware carveouts; sparse guest RAM only'},indent=2)+'\\n')
'''
text = text.replace("    dtb = DEST / 'virt-original-ap10.dtb';", layout + "    dtb = DEST / 'virt-original-ap10.dtb';")

exec(compile(text, str(source), 'exec'), {'__file__': str(source), '__name__': '__main__'})
