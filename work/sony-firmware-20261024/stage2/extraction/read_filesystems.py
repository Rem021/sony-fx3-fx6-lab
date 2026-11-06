#!/usr/bin/env python3
"""Read-only bounded ext2/FAT16 firmware reader, no mounts, firmware execution or symlink following.
Ext2 format: https://www.kernel.org/doc/html/latest/filesystems/ext4/{super,inodes,ifork,directory}.html
FAT BPB/dir format: Microsoft FAT specification, https://learn.microsoft.com/en-us/windows-hardware/drivers/ifs/fat
Only input image is mmap-read; output regular files under fixed task dir. Symlinks are recorded, not created.
"""
import sys,json,pathlib,struct,mmap,hashlib,re,itertools
BASE=pathlib.Path(__file__).resolve().parent
class Ext2:
 def __init__(self,p):
  self.f=open(p,'rb');self.b=mmap.mmap(self.f.fileno(),0,access=mmap.ACCESS_READ);s=self.r(1024,1024)
  assert s[56:58]==b'\x53\xef';self.bs=1024<<struct.unpack_from('<I',s,24)[0];assert self.bs in [1024,2048,4096]
  self.ngi=struct.unpack_from('<I',s,40)[0];self.ni=struct.unpack_from('<I',s,0)[0];self.isz=struct.unpack_from('<H',s,88)[0]
  self.gdt=2*self.bs if self.bs==1024 else self.bs;self.inc=struct.unpack_from('<I',s,96)[0];assert self.inc & ~2==0,hex(self.inc)
  self.meta={'kind':'ext2','block_size':self.bs,'inode_size':self.isz,'inodes':self.ni,'incompat':self.inc};self.cache={}
 def r(self,o,n):
  assert 0<=o<=len(self.b) and 0<=n<=len(self.b)-o,(o,n,len(self.b));return self.b[o:o+n]
 def inode(self,n):
  assert 1<=n<=self.ni;n-=1;g=n//self.ngi;i=n%self.ngi;tab=struct.unpack_from('<I',self.r(self.gdt+g*32+8,4))[0];s=self.r(tab*self.bs+i*self.isz,self.isz)
  mode=struct.unpack_from('<H',s,0)[0];size=struct.unpack_from('<I',s,4)[0];flags=struct.unpack_from('<I',s,32)[0]
  if mode&0xf000==0x8000:size|=struct.unpack_from('<I',s,108)[0]<<32
  assert not flags & 0x80000,'extent unsupported';return mode,size,flags,s[40:100]
 def pointers(self,n,level):
  if not n:
   yield from itertools.repeat(0,(self.bs//4)**level);return
  a=struct.unpack('<'+'I'*(self.bs//4),self.r(n*self.bs,self.bs))
  if level==1:yield from a
  else:
   for v in a:yield from self.pointers(v,level-1)
 def data(self,n):
  mode,size,flags,p=self.inode(n);assert size<=len(self.b),'inode-size-bounds'
  if mode&0xf000==0xa000 and size<=60:return p[:size]
  needed=(size+self.bs-1)//self.bs;ip=struct.unpack('<15I',p)
  stream=itertools.chain(ip[:12],self.pointers(ip[12],1),self.pointers(ip[13],2),self.pointers(ip[14],3))
  blocks=list(itertools.islice(stream,needed));assert len(blocks)==needed
  return b''.join(self.r(k*self.bs,self.bs) if k else bytes(self.bs) for k in blocks)[:size]
 def walk(self,n=2,path='',anc=()):
  assert n not in anc,'directory cycle';raw=self.data(n);o=0
  while o+8<=len(raw):
   ino,rec,nlen,ft=struct.unpack_from('<IHBB',raw,o);assert rec>=8 and rec%4==0 and o+rec<=len(raw);assert nlen<=rec-8
   name=raw[o+8:o+8+nlen].decode('utf8',errors='surrogateescape');o+=rec
   if not ino or name in ('.','..'):continue
   assert name and '/' not in name and '\x00' not in name
   mode,size,flags,p=self.inode(ino);q=path+'/'+name;e={'path':q,'inode':ino,'mode':oct(mode),'size':size,'flags':hex(flags),'type':mode&0xf000};yield e
   if mode&0xf000==0x4000:yield from self.walk(ino,q,anc+(n,))
class FAT16:
 def __init__(self,p):
  self.f=open(p,'rb');self.b=mmap.mmap(self.f.fileno(),0,access=mmap.ACCESS_READ);self.ss=struct.unpack_from('<H',self.b,11)[0];self.spc=self.b[13];self.res=struct.unpack_from('<H',self.b,14)[0];self.nf=self.b[16];self.nr=struct.unpack_from('<H',self.b,17)[0];self.spf=struct.unpack_from('<H',self.b,22)[0];self.root=(self.res+self.nf*self.spf)*self.ss;self.dataoff=self.root+((self.nr*32+self.ss-1)//self.ss)*self.ss
  assert self.ss in [512,1024,2048,4096] and self.spc and self.nr and self.spf;self.total=struct.unpack_from('<H',self.b,19)[0] or struct.unpack_from('<I',self.b,32)[0];self.clusters=(self.total-self.dataoff//self.ss)//self.spc;self.bits=12 if self.clusters<4085 else 16;self.meta={'kind':'FAT'+str(self.bits),'sector_size':self.ss,'sectors_per_cluster':self.spc,'root_offset':self.root,'data_offset':self.dataoff,'cluster_count':self.clusters}
 def chain(self,n):
  out=bytearray();seen=set()
  while n<(0xff8 if self.bits==12 else 0xfff8):
   assert n>=2 and n not in seen;seen.add(n);o=self.dataoff+(n-2)*self.ss*self.spc;assert o+self.ss*self.spc<=len(self.b);out.extend(self.b[o:o+self.ss*self.spc]);v=struct.unpack_from('<H',self.b,self.res*self.ss+(n+n//2 if self.bits==12 else n*2))[0];n=((v>>4) if n&1 else (v&0xfff)) if self.bits==12 else v
  return bytes(out)
 def data(self,n,size):return self.chain(n)[:size] if size else b''
 def walk(self,n=None,path='',anc=()):
  assert n not in anc or n is None
  b=self.b[self.root:self.root+self.nr*32] if n is None else self.chain(n);long=[]
  for o in range(0,len(b),32):
   e=b[o:o+32]
   if not e or e[0]==0:break
   if e[0]==0xe5:long=[];continue
   if e[11]==0x0f:long.append((e[0]&31,e[1:11]+e[14:26]+e[28:32]));continue
   raw=e[:8].rstrip(b' ').decode('ascii',errors='replace');ext=e[8:11].rstrip(b' ').decode('ascii',errors='replace');name=raw+('.'+ext if ext else '')
   if long:
    name=b''.join(t for _,t in sorted(long)).decode('utf-16-le').split('\x00')[0].rstrip('\uffff');long=[]
   if name in ('.','..') or e[11]&8:continue
   assert name and '/' not in name and '\x00' not in name
   cl=struct.unpack_from('<H',e,26)[0];sz=struct.unpack_from('<I',e,28)[0];q=path+'/'+name;isdir=bool(e[11]&16);yield {'path':q,'cluster':cl,'size':sz,'attributes':e[11],'type':0x4000 if isdir else 0x8000}
   if isdir:yield from self.walk(cl,q,anc+(n,))
def main():
 result=[]
 for part,kind in [('15','ext2'),('7','ext2'),('3','fat16'),('8','fat16')]:
  p=BASE/f'nflasha{part}.img';fs=Ext2(p) if kind=='ext2' else FAT16(p);rows=list(fs.walk());(BASE/f'nflasha{part}-files.json').write_text(json.dumps({'image':str(p),'metadata':fs.meta,'files':rows},ensure_ascii=True,indent=2));print(part,fs.meta,'entries',len(rows))
  for e in rows:
   if e['type']==0x8000 and (re.search(r'appfw|cpapp|lib.*enc|enc.*\.so|movie|rec.*param|rec.*mode|codec|avc|hevc',e['path'],re.I)):
    print(e)
    if part=='15' and (e['path'].lower().endswith('appfw.so') or re.search(r'(hevc|avc|enc).*\.so',e['path'],re.I)) or part=='8' and 'cpapp' in e['path'].lower():
     out=BASE/'files'/f'nflasha{part}'/e['path'].lstrip('/');assert out.resolve().is_relative_to((BASE/'files').resolve());out.parent.mkdir(parents=True,exist_ok=True);b=fs.data(e['inode']) if kind=='ext2' else fs.data(e['cluster'],e['size']);assert len(b)==e['size'];out.write_bytes(b);result.append({**e,'extracted_path':str(out),'sha256':hashlib.sha256(b).hexdigest(),'first32':b[:32].hex()})
 (BASE/'extracted-manifest.json').write_text(json.dumps(result,indent=2));print('EXTRACTED',json.dumps(result,indent=2))
if __name__=='__main__':main()
