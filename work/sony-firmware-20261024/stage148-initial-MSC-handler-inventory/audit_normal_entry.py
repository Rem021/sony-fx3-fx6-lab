#!/usr/bin/env python3
"""Extract one original object library as data; trace named normal-mode entry."""
from pathlib import Path
from hashlib import sha256
import importlib.util
import json
import re

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
ROOT=BASE.parents[1]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


def main():
    p=BASE/'stage2/extraction/read_filesystems.py'
    assert sha256(p.read_bytes()).hexdigest()=='eecbe9b099f9fbc8f8e06759c5e8a2ce9910e0f365ae9891fe0887353edc31ad'
    reader=load('pinned_fs_for_object',p);fs=reader.Ext2(BASE/'stage2/extraction/nflasha15.img')
    assert sha256(fs.b).hexdigest()=='df0a2cf2ebb0d884605d041a6dcb701092bd36848956855b8d3d7a7164a3a1c5'
    entry=next(x for x in fs.walk() if x['path']=='/lib/libObj.so')
    raw=fs.data(entry['inode']);want='c4681d209a7fe2ed63752be3b0be89ab7b7ce400679c00068c8c6e47d39f83ae'
    assert sha256(raw).hexdigest()==want
    original=HERE/'work/originals/libObj.so';original.parent.mkdir(parents=True,exist_ok=True)
    with original.open('xb') as f:f.write(raw)
    prior=BASE/'stage134-backup-reader-scope-and-service-extension'
    manifest=(prior/'final-receipt.json').read_bytes()
    assert sha256(manifest).hexdigest()=='5ece0e5dea69b1c88e812ae42e46a07abf95316a2a6f02c34a5784b7ff6eec1d'
    source=prior/'audit_readers.py';pin=next(x for x in json.loads(manifest)['files'] if x['path']==source.relative_to(ROOT).as_posix())
    assert sha256(source.read_bytes()).hexdigest()==pin['sha256']
    elf=load('pinned_image_for_object',source);elf.LIB=original.parent
    obj=elf.Image('libObj.so',want)
    names=[n for n,s in obj.symbols.items() if s['st_shndx']!='SHN_UNDEF' and s['st_info']['type']=='STT_FUNC' and
           re.search(r'^senser_(?:init|res|sus)$|udtr_senser_init|Nin|[Cc]oreModule|normal_mode',n)]
    functions=[obj.function(n) for n in names]
    calls=[{'in_function':f['name'],**i} for f in functions for i in f['instructions'] if i.get('PLT_symbol')]
    report={'status':'STATIC_ORIGINAL_LIBOBJ_NORMAL_ENTRY_NOT_INITIAL_MSC_AUTH_PROOF',
        'original':{'path':original.relative_to(ROOT).as_posix(),'bytes':len(raw),'sha256':want},
        'fixed_reader':pin,'functions':functions,'calls':calls,
        'new_camera_or_USB_operations':0,'original_Sony_code_loaded_or_executed':False}
    with (HERE/'normal-entry-review.json').open('x') as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
    (HERE/'normal-entry-executed.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({'status':report['status'],'functions':[(f['name'],f['VA'],f['bytes']) for f in functions],
        'PLT_targets':sorted(set(x['PLT_symbol'] for x in calls))}))


if __name__=='__main__':main()
