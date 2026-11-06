#!/usr/bin/env python3
"""Read-only full AP/initrd search for literal configuration-loading references."""
import hashlib,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
FSROOT=HERE.parents[1]/'sony-firmware-20261024/stage2/extraction'
sys.path.insert(0,str(FSROOT))
from read_filesystems import Ext2
PINS={15:'df0a2cf2ebb0d884605d041a6dcb701092bd36848956855b8d3d7a7164a3a1c5',
7:'ceca23d253350e65df9c7c976f06e545ad41a2d8f272d28fc1e73fcc576ddba7'}
TOKENS=[b'DmmCfg',b'DMMCFG',b'cpapp-b',b'cpImg.dat',b'fa0182']
def main():
    out=HERE/'AP-initrd-config-marker-scan.json';assert not out.exists()
    result=[]
    for part,pin in PINS.items():
        image=FSROOT/f'nflasha{part}.img';assert hashlib.sha256(image.read_bytes()).hexdigest()==pin
        fs=Ext2(image);files=[];hits=[]
        for e in fs.walk():
            if e['type']!=0x8000:continue
            data=fs.data(e['inode']);assert len(data)==e['size']
            files.append(dict(path=e['path'],bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
            for token in TOKENS:
                offsets=[];start=0
                while (at:=data.find(token,start))>=0:offsets.append(at);start=at+len(token)
                if offsets:hits.append(dict(path=e['path'],token=token.decode(),file_offsets=list(map(hex,offsets))))
        result.append(dict(image=str(image),image_sha256=pin,regular_files=len(files),scanned_bytes=sum(x['bytes'] for x in files),files=files,hits=hits))
    out.write_text(json.dumps(dict(images=result,tokens=[x.decode() for x in TOKENS],
        scope='Exact ASCII literals over all regular AP/initrd files, excluding symlinks/slack. A hit is only a candidate reference, not proof of a load path; missing strings do not rule out a stripped implementation. No native Sony or device execution.'),indent=2)+'\n')
    print(json.dumps([dict(image=x['image'],regular_files=x['regular_files'],hits=x['hits']) for x in result]))
if __name__=='__main__':main()
