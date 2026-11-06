#!/usr/bin/env python3
"""All regular AP/initrd/AV/CP filesystem files, exact ASCII and UTF-16 markers."""
import hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
FSROOT=HERE.parents[1]/'sony-firmware-20261024/stage2/extraction'
sys.path.insert(0,str(FSROOT))
from read_filesystems import Ext2,FAT16
PINS={
15:'df0a2cf2ebb0d884605d041a6dcb701092bd36848956855b8d3d7a7164a3a1c5',
7:'ceca23d253350e65df9c7c976f06e545ad41a2d8f272d28fc1e73fcc576ddba7',
3:'ca5a8c80a1883c4a72c2f40018e3d40ab43e28ff0bf6a1d89f17d0680c607568',
8:'3c751e784fe6790a4b455990d7c6e144c33cf51c643cf3bf9523f8a3bd5a6a2b',
}
TOKENS=['BinaryPackProperty','ProductCodeVersion','DATA23213','PackageType','multiversion']
def main():
    dest=HERE/'fx3-whole-filesystem-markers.json';assert not dest.exists()
    tokens=[(s,e,s.encode(e)) for s in TOKENS for e in ['ascii','utf-16-le','utf-16-be']]
    images=[]
    for part,pin in PINS.items():
        p=FSROOT/f'nflasha{part}.img';assert hashlib.sha256(p.read_bytes()).hexdigest()==pin
        fs=Ext2(p) if part in [15,7] else FAT16(p)
        rows=[];hits=[];total=0
        for e in fs.walk():
            if e['type']!=0x8000:continue
            b=fs.data(e['inode']) if part in [15,7] else fs.data(e['cluster'],e['size'])
            assert len(b)==e['size'];total+=len(b)
            rows.append(dict(path=e['path'],bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
            for s,enc,needle in tokens:
                pos=b.find(needle)
                if pos>=0:hits.append(dict(path=e['path'],token=s,encoding=enc,first_file_offset=pos))
        images.append(dict(image=str(p),sha256=pin,filesystem=fs.meta,regular_files=len(rows),scanned_bytes=total,hits=hits,files=rows))
    result=dict(tokens=TOKENS,encodings=['ascii','utf-16-le','utf-16-be'],images=images,
        scope='Exact marker search over every regular file in four pinned filesystems, excluding symlinks, slack, unallocated regions and WBI. A no-hit result does not prove absence of a stripped or string-free parser. Read-only host parsing, no original native program or device execution.')
    dest.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps([{k:r[k] for k in ['image','regular_files','scanned_bytes','hits']} for r in images],ensure_ascii=False))
if __name__=='__main__':main()
