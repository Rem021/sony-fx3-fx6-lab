#!/usr/bin/env python3
"""Bounded exact searches for original handoff names and marker constants."""
import hashlib,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;FSROOT=HERE.parents[1]/'sony-firmware-20261024/stage2/extraction'
sys.path.insert(0,str(FSROOT));from read_filesystems import Ext2,FAT16
PINS={15:'df0a2cf2ebb0d884605d041a6dcb701092bd36848956855b8d3d7a7164a3a1c5',
7:'ceca23d253350e65df9c7c976f06e545ad41a2d8f272d28fc1e73fcc576ddba7',
8:'3c751e784fe6790a4b455990d7c6e144c33cf51c643cf3bf9523f8a3bd5a6a2b'}
TOKENS=[b'cetus',b'CETUS',b'Cetus',b'CP_ESCAPE',b'cpapp',b'CPAPP',b'KRNE',b'ESCP']
def main():
    out=HERE/'handoff-marker-scan.json';assert not out.exists();images=[]
    for part,pin in PINS.items():
        image=FSROOT/f'nflasha{part}.img';assert hashlib.sha256(image.read_bytes()).hexdigest()==pin
        fs=Ext2(image) if part in [15,7] else FAT16(image);rows=[];hits=[]
        for e in fs.walk():
            if e['type']!=0x8000:continue
            data=fs.data(e['inode']) if part in [15,7] else fs.data(e['cluster'],e['size'])
            assert len(data)==e['size'];rows.append(dict(path=e['path'],bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
            for token in TOKENS:
                offsets=[];start=0
                while (at:=data.find(token,start))>=0:offsets.append(at);start=at+len(token)
                if offsets:hits.append(dict(path=e['path'],token=token.decode(),occurrences=len(offsets),first_offsets=list(map(hex,offsets[:12]))))
        images.append(dict(image=str(image),image_sha256=pin,regular_files=len(rows),scanned_bytes=sum(x['bytes'] for x in rows),files=rows,hits=hits))
    out.write_text(json.dumps(dict(tokens=[x.decode() for x in TOKENS],images=images,
        scope='Exact regular-file names/markers, not source reachability or a complete sender inventory. A missing literal does not exclude instructions constructing a constant or stripped code. No execution/mount/device action.'),indent=2)+'\n')
    print(json.dumps([dict(image=x['image'],files=x['regular_files'],hits=x['hits']) for x in images]))
if __name__=='__main__':main()
