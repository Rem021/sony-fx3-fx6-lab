#!/usr/bin/env python3
"""Extract only regular files from verified nflasha15 ext2, with per-file SHA256."""
import collections,hashlib,json,pathlib,stat,sys
ROOT=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(next(ROOT.glob('fwtool.py-*'))))
from fwtool.archive import ext2
from inventory import elf_header

def main():
 image=ROOT/'tree/0700_part_image/dev/nflasha15'
 out=ROOT/'nflasha15-files';out.mkdir(exist_ok=True)
 entries=[]
 # The host volume is case-insensitive. Precompute names that would collide.
 with image.open('rb') as src:
  names=[x.path for x in ext2.readExt2(src) if stat.S_ISREG(x.mode)]
 folded=collections.Counter(x.casefold() for x in names)
 with image.open('rb') as src:
  assert ext2.isExt2(src)
  for item in ext2.readExt2(src):
   rel=pathlib.PurePosixPath(item.path.lstrip('/'))
   assert not rel.is_absolute() and '..' not in rel.parts
   if not rel.parts:continue
   if stat.S_ISDIR(item.mode):continue
   if stat.S_ISLNK(item.mode):
    entries.append({'path':item.path,'kind':'symlink','extracted':False});continue
   if not stat.S_ISREG(item.mode):
    entries.append({'path':item.path,'kind':'other','mode':oct(item.mode),'extracted':False});continue
   if folded[item.path.casefold()]>1:
    suffix=hashlib.sha256(item.path.encode()).hexdigest()[:12]
    stored=pathlib.PurePosixPath('case-collisions')/(suffix+'-'+rel.name)
   else:stored=rel
   dest=out.joinpath(*stored.parts);dest.parent.mkdir(parents=True,exist_ok=True)
   h=hashlib.sha256();count=0
   with dest.open('wb') as f:
    while b:=item.contents.read(min(1024*1024,item.size-count)):
     f.write(b);h.update(b);count+=len(b)
     if count>=item.size:break
   assert count==item.size,(item.path,count,item.size)
   entries.append({'path':item.path,'stored_path':str(stored),'kind':'file','bytes':count,'sha256':h.hexdigest(),'elf':elf_header(dest)})
   if len(entries)%250==0:print('entries',len(entries),flush=True)
 (ROOT/'nflasha15-manifest.json').write_text(json.dumps({'source':'0700_part_image/dev/nflasha15','filesystem':'ext2','entries':entries},indent=2)+'\n')
 print('done',len(entries),'files',sum(x['kind']=='file' for x in entries),flush=True)
if __name__=='__main__':main()
