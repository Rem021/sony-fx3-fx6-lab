#!/usr/bin/env python3
"""Inventory shipped AP symbols for bounded-read primitives, not wire access."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import importlib.util
import io
import json
import re
from elftools.elf.elffile import ELFFile

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
ROOT=BASE.parents[1]
PATTERN=re.compile(r'^(?:pread(?:64)?|lseek(?:64)?|open(?:64)?|close|read|fstat(?:64)?|mmap(?:64)?|ioctl)$|FileAccess.*(?:seek|read)|DeviceIo.*(?:seek|read|open)|DmmMgr.*file2dmm|(?:ReadFile|read_file|readFile|ReadBlock|readBlock|FlashRead|flash_read|FileControl)')
SPECIAL=re.compile(r'^pread(?:64)?$|FileAccess.*seek|DeviceIo.*(?:seek|read)|FileControl|(?:ReadBlock|readBlock|FlashRead|flash_read)')


def main():
    reader=BASE/'stage2/extraction/read_filesystems.py'
    assert sha256(reader.read_bytes()).hexdigest()=='eecbe9b099f9fbc8f8e06759c5e8a2ce9910e0f365ae9891fe0887353edc31ad'
    spec=importlib.util.spec_from_file_location('pinned_original_ext2_reader',reader)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    fs=module.Ext2(BASE/'stage2/extraction/nflasha15.img')
    assert sha256(fs.b).hexdigest()=='df0a2cf2ebb0d884605d041a6dcb701092bd36848956855b8d3d7a7164a3a1c5'
    prior=json.loads((BASE/'stage148-initial-MSC-handler-inventory/AP-handler-inventory.json').read_text())
    expected={r['inode']:r for r in prior['ELF_records']}
    records=[];seen={};other=0
    for entry in fs.walk():
        if entry['type']!=32768:continue
        inode=entry['inode']
        if inode in seen:seen[inode]['image_paths'].append(entry['path']);continue
        raw=fs.data(inode)
        if not raw.startswith(b'\x7fELF'):other+=1;continue
        assert inode in expected and len(raw)==expected[inode]['bytes'] and sha256(raw).hexdigest()==expected[inode]['sha256']
        elf=ELFFile(io.BytesIO(raw));symbols=[];tables=[]
        for name in ['.dynsym','.symtab']:
            table=elf.get_section_by_name(name)
            if table is None:continue
            tables.append(name)
            for symbol in table.iter_symbols():
                if PATTERN.search(symbol.name):
                    symbols.append({'name':symbol.name,'VA':hex(symbol['st_value']),'bytes':symbol['st_size'],
                        'section':symbol['st_shndx'],'defined':symbol['st_shndx']!='SHN_UNDEF','type':symbol['st_info']['type'],'table':name})
        dynamic=elf.get_section_by_name('.dynamic')
        needed=[t.needed for t in dynamic.iter_tags() if t.entry.d_tag=='DT_NEEDED'] if dynamic is not None else []
        record={'image_paths':[entry['path']],'inode':inode,'bytes':len(raw),'sha256':sha256(raw).hexdigest(),
            'machine':elf['e_machine'],'elf_type':elf['e_type'],'symbol_tables':tables,'needed':needed,'symbols':symbols}
        records.append(record);seen[inode]=record
    assert len(records)==len(expected)==532
    matches=[r for r in records if r['symbols']]
    preferred=[{'image_paths':r['image_paths'],'inode':r['inode'],'sha256':r['sha256'],'machine':r['machine'],
        'symbols':[s for s in r['symbols'] if SPECIAL.search(s['name'])]} for r in matches]
    preferred=[r for r in preferred if r['symbols']]
    result={'status':'PASS_STATIC_AP_RANGE_READ_PRIMITIVE_INVENTORY_NOT_REACHABLE_BACKUP_API',
        'created_utc':datetime.now(timezone.utc).isoformat(),'source_image_sha256':sha256(fs.b).hexdigest(),
        'source_image':str((BASE/'stage2/extraction/nflasha15.img').relative_to(ROOT)),
        'reader_sha256':sha256(reader.read_bytes()).hexdigest(),'ELF_count':len(records),'non_ELF_count':other,
        'pattern':PATTERN.pattern,'matching_ELF_count':len(matches),'preferred':preferred,'ELF_records':records,
        'scope':'Named symbols/imports in the fixed AP filesystem only. Presence is not a Senser route, read-only behavior or physical range guarantee; absence does not exclude inline/syscall/RTOS/other partition/ROM/dynamic code.',
        'original_Sony_code_or_libraries_executed':False,'new_USB_root_camera_or_file_service_operations':0}
    with (HERE/'AP-range-read-inventory.json').open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    (HERE/'inventory-executed.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({'ELFs':len(records),'matched':len(matches),'preferred':preferred}))


if __name__=='__main__':main()
