import struct

import os
HERE = os.path.dirname(os.path.abspath(__file__))
obj = open(os.path.join(HERE, 'jit_payload.o'), 'rb').read()
e_shoff = struct.unpack_from('<Q', obj, 0x28)[0]
e_shentsize = struct.unpack_from('<H', obj, 0x3a)[0]
e_shnum = struct.unpack_from('<H', obj, 0x3c)[0]
e_shstrndx = struct.unpack_from('<H', obj, 0x3e)[0]
secs=[]
for i in range(e_shnum):
    off=e_shoff+i*e_shentsize
    name,typ,flags,addr,offset,size,link,info,align,entsize=struct.unpack_from('<IIQQQQIIQQ',obj,off)
    secs.append(dict(name=name,typ=typ,offset=offset,size=size))
shstr=secs[e_shstrndx]
shstrtab=obj[shstr['offset']:shstr['offset']+shstr['size']]
def sname(n):
    end=shstrtab.find(b'\0',n); return shstrtab[n:end].decode()
text=rodata=None
for s in secs:
    nm=sname(s['name'])
    if nm=='.text': text=bytearray(obj[s['offset']:s['offset']+s['size']])
    if nm=='.rodata.str1.1': rodata=obj[s['offset']:s['offset']+s['size']]
assert text is not None and rodata is not None
def patch_add(buf, off, imm12):
    ins=struct.unpack_from('<I',buf,off)[0]
    ins=(ins & ~(0xfff<<10)) | ((imm12 & 0xfff)<<10)
    struct.pack_into('<I',buf,off,ins)
patch_add(text,0x10,0x100)   # .rodata base 0x1100
patch_add(text,0x78,0x10d)   # .rodata+0xd

TEXT_VA=0x1000; RODATA_VA=0x1100
DYN_VA=0x2000; SYM_VA=0x2070; STR_VA=0x2088; HASH_VA=0x2089
dyn=[(5,STR_VA),(6,SYM_VA),(10,1),(11,24),(4,HASH_VA),(12,TEXT_VA),(0,0)]
dynbytes=b''.join(struct.pack('<QQ',t,v) for t,v in dyn)
dynsym=b'\0'*24
dynstr=b'\0'
hashb=struct.pack('<IIII',1,1,0,0)
rdata=dynbytes+dynsym+dynstr+hashb

EH=64; PH=56; phnum=3; phoff=EH
textoff=0x1000; rdoff=0x1100; dynoff=0x2000
total=dynoff+len(rdata)
out=bytearray(total)
e_ident=b'\x7fELF'+bytes([2,1,1,0])+b'\0'*8
struct.pack_into('<16sHHIQQQIHHHHHH',out,0,e_ident,3,183,1,0,phoff,0,0,EH,PH,phnum,0,0,0)
def ph(idx,typ,flags,off,vaddr,filesz,memsz,align):
    struct.pack_into('<IIQQQQQQ',out,phoff+idx*PH,typ,flags,off,vaddr,vaddr,filesz,memsz,align)
ph(0,1,5,textoff,TEXT_VA,rdoff+len(rodata)-textoff,rdoff+len(rodata)-textoff,0x1000)
ph(1,1,4,dynoff,DYN_VA,len(rdata),len(rdata),0x1000)
ph(2,2,4,dynoff,DYN_VA,len(dynbytes),len(dynbytes),8)
out[textoff:textoff+len(text)] = text
out[rdoff:rdoff+len(rodata)] = rodata
out[dynoff:dynoff+len(rdata)] = rdata
open(os.path.join(HERE, 'libJit_test.so'), 'wb').write(out)
print('built', len(out), 'bytes; text', len(text), 'rodata', len(rodata), 'dyn', len(dynbytes))
