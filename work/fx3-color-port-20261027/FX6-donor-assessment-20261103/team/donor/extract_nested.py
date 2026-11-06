#!/usr/bin/env python3
"""Extract recognized ext2 and zlib SquashFS nested images without mounting."""
import hashlib,json,pathlib,stat,sys
ROOT=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(next(ROOT.glob('fwtool.py-*'))))
from fwtool.archive import ext2,squashfs
from inventory import elf_header
IMAGES=[('updater.img',ROOT/'updater.img',squashfs),
        ('nflasha1-initrd',ROOT/'fat-files/nflasha1/boot/initrd.img',squashfs),
        ('nflasha3-initrd',ROOT/'fat-files/nflasha3/initrd.img',ext2)]
def main():
 entries=[]
 for label,source,lib in IMAGES:
  destroot=ROOT/'nested-files'/label;destroot.mkdir(parents=True,exist_ok=True)
  with source.open('rb') as f:
   assert (lib.isSquashfs(f) if lib is squashfs else lib.isExt2(f))
   iterator=lib.readSquashfs(f) if lib is squashfs else lib.readExt2(f)
   for item in iterator:
    if stat.S_ISDIR(item.mode):continue
    if stat.S_ISLNK(item.mode):
     entries.append({'image':label,'path':item.path,'kind':'symlink','extracted':False});continue
    if not stat.S_ISREG(item.mode):continue
    rel=pathlib.PurePosixPath(item.path.lstrip('/'))
    assert not rel.is_absolute() and '..' not in rel.parts
    dest=destroot.joinpath(*rel.parts);dest.parent.mkdir(parents=True,exist_ok=True)
    h=hashlib.sha256();n=0
    with dest.open('wb') as out:
     while n<item.size:
      b=item.contents.read(min(1024*1024,item.size-n))
      if not b:break
      out.write(b);h.update(b);n+=len(b)
    assert n==item.size,(label,item.path,n,item.size)
    entries.append({'image':label,'path':item.path,'kind':'file','bytes':n,'sha256':h.hexdigest(),'elf':elf_header(dest)})
  print(label,'done',flush=True)
 (ROOT/'nested-manifest.json').write_text(json.dumps({'entries':entries},indent=2)+'\n')
 print('files',sum(x['kind']=='file' for x in entries),flush=True)
if __name__=='__main__':main()
