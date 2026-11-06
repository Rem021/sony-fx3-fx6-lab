#!/usr/bin/env python3
"""Safely extract verified firmware.tar and emit byte hashes and ELF metadata."""
import hashlib, json, pathlib, struct, subprocess, tarfile

ROOT=pathlib.Path(__file__).resolve().parent
SRC=ROOT/'firmware.tar'
DEST=ROOT/'tree'

def digest(f):
 h=hashlib.sha256()
 while b:=f.read(4*1024*1024):h.update(b)
 return h.hexdigest()

def elf_header(p):
 with p.open('rb') as f:b=f.read(64)
 if b[:4]!=b'\x7fELF':return None
 le=b[5]==1; order='<' if le else '>'
 et,em=struct.unpack_from(order+'HH',b,16)
 return {'class':32 if b[4]==1 else 64,'endian':'little' if le else 'big',
         'type':et,'machine':em,'machine_name':{3:'x86',40:'ARM',183:'AArch64',8:'MIPS'}.get(em,'unknown')}

def main():
 DEST.mkdir(exist_ok=True)
 entries=[]
 with tarfile.open(SRC) as t:
  for m in t:
   rel=pathlib.PurePosixPath(m.name)
   assert not rel.is_absolute() and '..' not in rel.parts
   dest=DEST.joinpath(*rel.parts)
   if m.isdir():dest.mkdir(parents=True,exist_ok=True);continue
   if m.issym():
    entries.append({'path':m.name,'kind':'symlink','target':m.linkname,'extracted':False});continue
   assert m.isfile()
   dest.parent.mkdir(parents=True,exist_ok=True)
   with t.extractfile(m) as src, dest.open('wb') as out:
    h=hashlib.sha256();n=0
    while b:=src.read(4*1024*1024):out.write(b);h.update(b);n+=len(b)
   assert n==m.size
   entry={'path':m.name,'kind':'file','bytes':n,'sha256':h.hexdigest(),'elf':elf_header(dest)}
   if n>0:
    q=subprocess.run(['file','-b',str(dest)],capture_output=True,text=True)
    entry['file_type']=q.stdout.strip()
   entries.append(entry)
 (ROOT/'manifest.json').write_text(json.dumps({'source':'firmware.tar','entries':entries},indent=2)+'\n')
 print('files',sum(e['kind']=='file' for e in entries),'ELF',sum(bool(e.get('elf')) for e in entries),flush=True)

if __name__=='__main__':main()
