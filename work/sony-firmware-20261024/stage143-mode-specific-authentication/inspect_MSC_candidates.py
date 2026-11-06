#!/usr/bin/env python3
"""Extract three original FX3 candidates as data and inspect symbol names only."""
from pathlib import Path
from hashlib import sha256
import importlib.util
import io
import json
import re
from elftools.elf.elffile import ELFFile

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
ROOT=BASE.parents[1]


def main():
    source=BASE/'stage2/extraction/read_filesystems.py'
    assert sha256(source.read_bytes()).hexdigest()=='eecbe9b099f9fbc8f8e06759c5e8a2ce9910e0f365ae9891fe0887353edc31ad'
    spec=importlib.util.spec_from_file_location('pinned_local_ext2_reader',source)
    reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
    image=BASE/'stage2/extraction/nflasha15.img'
    fs=reader.Ext2(image)
    image_hash=sha256(fs.b).hexdigest()
    assert image_hash=='df0a2cf2ebb0d884605d041a6dcb701092bd36848956855b8d3d7a7164a3a1c5'
    wanted={'/kmod/usbg_storage.ko','/lib/libUsbControl.so','/lib/libusbcmd.so'}
    records=[]
    for entry in fs.walk():
        if entry['path'] not in wanted:continue
        assert entry['type']==32768
        raw=fs.data(entry['inode']);assert len(raw)==entry['size']
        dest=HERE/'work/original-candidates'/entry['path'].lstrip('/')
        dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open('xb') as f:f.write(raw)
        elf=ELFFile(io.BytesIO(raw));table=elf.get_section_by_name('.symtab') or elf.get_section_by_name('.dynsym')
        symbols=[{'name':s.name,'value':hex(s['st_value']),'size':s['st_size'],'section':s['st_shndx']}
                 for s in table.iter_symbols() if re.search('nin|auth|sense|senser|digest|sha|xxhop|xxstep|crypto',s.name,re.I)]
        records.append({'image_entry':entry,'path':dest.relative_to(ROOT).as_posix(),'bytes':len(raw),
                        'sha256':sha256(raw).hexdigest(),'elf_type':elf['e_type'],'machine':elf['e_machine'],
                        'candidate_symbols':symbols,'original_native_code_loaded_or_executed':False})
    assert len(records)==3
    result={'status':'THREE_ORIGINAL_MSC_CANDIDATES_EXTRACTED_AS_DATA_NOT_AUTH_VERIFIED',
            'source_image_sha256':image_hash,'reader_sha256':sha256(source.read_bytes()).hexdigest(),
            'records':records,'camera_or_Windows_operations':0,'initial_MSC_verifier_proven':False}
    with (HERE/'MSC-original-candidates.json').open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps({'status':result['status'],'records':records}))


if __name__=='__main__':main()
