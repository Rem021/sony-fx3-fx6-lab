#!/usr/bin/env python3
"""Static symbol/import inventory of shipped AP ELFs. No Sony code execution."""
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
PATTERN=re.compile(r'NinThread|xx(?:hop|step|jump|kick)|senser|senif|authenticate|authentication|SHA(?:1|224|256|384|512)(?:_|$)|EVP_Digest|SEN_SSL',re.I)


def main():
    reader=BASE/'stage2/extraction/read_filesystems.py'
    assert sha256(reader.read_bytes()).hexdigest()=='eecbe9b099f9fbc8f8e06759c5e8a2ce9910e0f365ae9891fe0887353edc31ad'
    spec=importlib.util.spec_from_file_location('pinned_filesystem_reader',reader)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    image=BASE/'stage2/extraction/nflasha15.img';fs=module.Ext2(image)
    assert sha256(fs.b).hexdigest()=='df0a2cf2ebb0d884605d041a6dcb701092bd36848956855b8d3d7a7164a3a1c5'
    entries=list(fs.walk());regular=[x for x in entries if x['type']==32768]
    records=[];by_inode={};matched=[];nonelf=0
    for entry in regular:
        inode=entry['inode']
        if inode in by_inode:
            by_inode[inode]['image_paths'].append(entry['path']);continue
        raw=fs.data(inode)
        assert len(raw)==entry['size']
        if raw[:4]!=b'\x7fELF':nonelf+=1;continue
        elf=ELFFile(io.BytesIO(raw));tables=[];symbols=[]
        for name in ('.dynsym','.symtab'):
            table=elf.get_section_by_name(name)
            if table is None:continue
            tables.append(name)
            for symbol in table.iter_symbols():
                if PATTERN.search(symbol.name):
                    symbols.append({'name':symbol.name,'value':symbol['st_value'],'bytes':symbol['st_size'],
                        'section':symbol['st_shndx'],'type':symbol['st_info']['type'],'table':name})
        dynamic=elf.get_section_by_name('.dynamic')
        needed=[x.needed for x in dynamic.iter_tags() if x.entry.d_tag=='DT_NEEDED'] if dynamic is not None else []
        rec={'image_paths':[entry['path']],'inode':inode,'bytes':len(raw),'sha256':sha256(raw).hexdigest(),
            'elf_type':elf['e_type'],'machine':elf['e_machine'],'symbol_tables':tables,'needed':needed,'matching_symbols':symbols}
        records.append(rec);by_inode[inode]=rec
        if symbols:matched.append(rec)
    report={'status':'STATIC_SHIPPED_AP_ELF_SYMBOL_AND_IMPORT_INVENTORY_NOT_AUTHENTICATION_PROOF',
        'created_utc':datetime.now(timezone.utc).isoformat(),'source_image':image.relative_to(ROOT).as_posix(),
        'source_image_sha256':sha256(fs.b).hexdigest(),'reader_sha256':sha256(reader.read_bytes()).hexdigest(),
        'regular_entries':len(regular),'unique_ELF_inodes':len(records),'unique_non_ELF_regular_files':nonelf,
        'matched_ELF_files':len(matched),'pattern':PATTERN.pattern,'ELF_records':records,
        'scope_limit':'Named symbols/imports only; no assertion that absent names exclude inlined, local, RTOS, ROM or dynamically selected code.',
        'new_USB_camera_or_Windows_operations':0,'original_Sony_code_loaded_or_executed':False}
    with (HERE/'AP-handler-inventory.json').open('x') as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
    (HERE/'inventory-executed.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({'status':report['status'],'regular_entries':len(regular),'unique_ELF_inodes':len(records),
        'matched_files':len(matched),'candidate_paths':[x['image_paths'] for x in matched
             if any(re.search(r'NinThread|xxhop|xxstep',s['name']) for s in x['matching_symbols'])]}))


if __name__=='__main__':main()
