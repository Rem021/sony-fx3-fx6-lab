#!/usr/bin/env python3
"""Extract original middleware as data, inventory its resource accessor methods."""
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
    reader_path=BASE/'stage2/extraction/read_filesystems.py'
    assert sha256(reader_path.read_bytes()).hexdigest()=='eecbe9b099f9fbc8f8e06759c5e8a2ce9910e0f365ae9891fe0887353edc31ad'
    reader=load('fixed_resource_fs',reader_path);fs=reader.Ext2(BASE/'stage2/extraction/nflasha15.img')
    assert sha256(fs.b).hexdigest()=='df0a2cf2ebb0d884605d041a6dcb701092bd36848956855b8d3d7a7164a3a1c5'
    entry=next(x for x in fs.walk() if x['path']=='/lib/libMWF.so');raw=fs.data(entry['inode'])
    want='06a80e89d1bba839bf4ea83492fb1fe0490037a8c8c46bf21d7ac46657d47a26';assert sha256(raw).hexdigest()==want
    path=HERE/'work/originals/libMWF.so';path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f:f.write(raw)
    ref=BASE/'stage134-backup-reader-scope-and-service-extension';receipt=(ref/'final-receipt.json').read_bytes()
    assert sha256(receipt).hexdigest()=='5ece0e5dea69b1c88e812ae42e46a07abf95316a2a6f02c34a5784b7ff6eec1d'
    source=ref/'audit_readers.py';pin=next(x for x in json.loads(receipt)['files'] if x['path']==source.relative_to(ROOT).as_posix())
    assert sha256(source.read_bytes()).hexdigest()==pin['sha256']
    elf=load('fixed_resource_image',source);elf.LIB=path.parent;image=elf.Image('libMWF.so',want)
    methods=[{'name':n,'VA':hex(s['st_value']),'bytes':s['st_size']} for n,s in image.symbols.items()
             if 'RsrcAcsr' in n and s['st_shndx']!='SHN_UNDEF' and s['st_info']['type']=='STT_FUNC']
    report={'original':{'path':path.relative_to(ROOT).as_posix(),'bytes':len(raw),'sha256':want},
        'source_image_SHA256':sha256(fs.b).hexdigest(),'fixed_reader':pin,'methods':methods,
        'original_code_loaded_or_executed':False,'new_camera_or_USB_operations':0}
    with (HERE/'middleware-original.json').open('x') as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
    (HERE/'prepare-executed.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({'bytes':len(raw),'method_count':len(methods),'methods':methods}))


if __name__=='__main__':main()
