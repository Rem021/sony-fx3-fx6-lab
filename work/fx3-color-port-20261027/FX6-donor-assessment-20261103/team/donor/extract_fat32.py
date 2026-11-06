#!/usr/bin/env python3
"""Read-only extraction of nflasha23 FAT32 at MBR sector 1."""
import hashlib,json,pathlib
from pyfatfs.PyFatFS import PyFatFS
ROOT=pathlib.Path(__file__).resolve().parent
SOURCE=ROOT/'tree/0700_part_image/dev/nflasha23'
DEST=ROOT/'fat-files/nflasha23'
def main():
 DEST.mkdir(parents=True,exist_ok=True);entries=[]
 with PyFatFS(str(SOURCE),offset=512,read_only=True) as fs:
  for name in fs.walk.files():
   rel=pathlib.PurePosixPath(name.lstrip('/'))
   assert '..' not in rel.parts and not rel.is_absolute()
   dest=DEST.joinpath(*rel.parts);dest.parent.mkdir(parents=True,exist_ok=True)
   with fs.openbin(name) as src,dest.open('wb') as dst:
    h=hashlib.sha256();n=0
    while b:=src.read(1024*1024):dst.write(b);h.update(b);n+=len(b)
   entries.append({'partition':'nflasha23','path':name,'bytes':n,'sha256':h.hexdigest()})
 (ROOT/'fat32-manifest.json').write_text(json.dumps({'filesystem':'FAT32','mbr_partition_offset':512,'entries':entries},indent=2)+'\n')
 print('files',len(entries))
if __name__=='__main__':main()
