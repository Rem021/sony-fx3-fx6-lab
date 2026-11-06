#!/usr/bin/env python3
"""Extract verified FAT12/FAT16 partition members using pinned fwtool."""
import hashlib,json,pathlib,stat,sys
ROOT=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(next(ROOT.glob('fwtool.py-*'))))
from fwtool.archive import fat
from inventory import elf_header

def main():
 all_entries=[]
 for part in ['nflasha1','nflasha3','nflasha8']:
  folder='0400_updater/dev' if part=='nflasha1' else '0700_part_image/dev'
  source=ROOT/'tree'/folder/part
  destroot=ROOT/'fat-files'/part;destroot.mkdir(parents=True,exist_ok=True)
  with source.open('rb') as src:
   assert fat.isFat(src)
   for item in fat.readFat(src):
    rel=pathlib.PurePosixPath(item.path.lstrip('/'))
    assert '..' not in rel.parts and not rel.is_absolute()
    if stat.S_ISDIR(item.mode):continue
    if stat.S_ISLNK(item.mode):continue
    dest=destroot.joinpath(*rel.parts);dest.parent.mkdir(parents=True,exist_ok=True)
    h=hashlib.sha256();n=0
    with dest.open('wb') as out:
     while n<item.size:
      b=item.contents.read(min(1024*1024,item.size-n))
      if not b:break
      out.write(b);h.update(b);n+=len(b)
    assert n==item.size,(part,item.path,n,item.size)
    all_entries.append({'partition':part,'path':item.path,'bytes':n,'sha256':h.hexdigest(),'elf':elf_header(dest)})
 (ROOT/'fat-manifest.json').write_text(json.dumps({'source':'firmware.tar partition images','entries':all_entries},indent=2)+'\n')
 print('files',len(all_entries),flush=True)
if __name__=='__main__':main()
