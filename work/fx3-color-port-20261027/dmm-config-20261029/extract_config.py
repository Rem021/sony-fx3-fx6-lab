#!/usr/bin/env python3
"""Read two original FAT files from the pinned FX3 partition; no mounts."""
import hashlib,json,struct,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;TASK=HERE.parent
SOURCE=TASK.parent/'sony-firmware-20261024/stage2/extraction'
PIN='3c751e784fe6790a4b455990d7c6e144c33cf51c643cf3bf9523f8a3bd5a6a2b'
sys.path.insert(0,str(SOURCE))
from read_filesystems import FAT16

def main():
    assert not (HERE/'original-files.json').exists()
    image=SOURCE/'nflasha8.img';raw=image.read_bytes()
    assert len(raw)==22450176 and hashlib.sha256(raw).hexdigest()==PIN
    fs=FAT16(image);files={r['path']:r for r in fs.walk()};rows=[]
    out=HERE/'original-files';out.mkdir(exist_ok=True)
    for name in ['/DmmCfg.bin','/cpImg.dat']:
        row=files[name];assert row['type']==0x8000
        b=fs.data(row['cluster'],row['size']);assert len(b)==row['size']
        file=out/name.lstrip('/')
        if file.exists():assert file.read_bytes()==b
        else:file.write_bytes(b)
        # Retain every original cluster/physical slice, independently reading
        # the FAT entry instead of treating a found byte string as a file.
        cluster=row['cluster'];chain=[];pieces=[]
        while cluster<(0xff8 if fs.bits==12 else 0xfff8):
            assert cluster>=2 and cluster not in [r['cluster'] for r in chain]
            at=fs.dataoff+(cluster-2)*fs.ss*fs.spc;n=fs.ss*fs.spc
            assert at+n<=len(raw)
            chain.append(dict(cluster=cluster,partition_offset=hex(at),bytes=n))
            pieces.append(raw[at:at+n])
            if fs.bits==12:
                fat_at=fs.res*fs.ss+cluster+cluster//2
                pair=int.from_bytes(raw[fat_at:fat_at+2],'little')
                cluster=(pair>>4) if cluster&1 else pair&0xfff
            else:cluster=int.from_bytes(raw[fs.res*fs.ss+cluster*2:fs.res*fs.ss+cluster*2+2],'little')
        assert b==b''.join(pieces)[:row['size']]
        rows.append(dict(**row,output=str(file.relative_to(HERE)),sha256=hashlib.sha256(b).hexdigest(),
                         first96_hex=b[:96].hex(),cluster_chain=chain))
    record=dict(partition=str(image),partition_sha256=PIN,partition_bytes=len(raw),metadata=fs.meta,files=rows,
                scope='Original bounded FAT reads with independent cluster-slice oracle. No file content interpreted as sensor/ISP or runtime state solely from its filename.')
    (HERE/'original-files.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps([{k:r[k] for k in ('path','size','sha256','first96_hex')} for r in rows]))

if __name__=='__main__':main()
