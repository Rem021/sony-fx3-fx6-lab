from pathlib import Path
import json,hashlib,struct
from elftools.elf.elffile import ELFFile
from capstone import *
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM
from unicorn.arm64_const import UC_ARM64_REG_X0
R=Path(__file__).resolve().parent;H=R/'helpers';P=R.parent/'original-uipc/ap-projection/regular-files/usr/lib';cs=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN)
def read(n,va,count):
 with (P/n).open('rb') as f:
  e=ELFFile(f)
  s=next(s for s in e.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=va and va+count<=s['p_vaddr']+s['p_filesz'])
  return s.data()[va-s['p_vaddr']:va-s['p_vaddr']+count]
params=[(0x6db,0x293c010,0x293c024,4),(0x6dc,0x293c038,0x293c04c,4),(0x6e3,0x293c150,0x293c164,4),(0x6e4,0x293c178,0x293c18c,4),(0x708,0x293c718,0x293c72c,4),(0x709,0x293c740,0x293c754,4),(0x1203,0x294c014,0x294c028,4),(0x1204,0x294c03c,0x294c050,4),(0x13e,0x29300fc,0x2930110,1),(0x13f,0x2930124,0x2930138,1)]
out=[];hdr=['struct param {U id,getter,shadow_getter,offset,shadow_offset; unsigned size; unsigned char code[20],shadow_code[20];};','static struct param params[]={']
for ident,va,sh,size in params:
 entry={'id':hex(ident),'size':size};row=[]
 for label,addr in [('current',va),('shadow',sh)]:
  code=read('appFw.so',addr,20);ins=list(cs.disasm(code,addr));assert [i.mnemonic for i in ins] in (['adrp','add','add','add','ret'], ['adrp','mov','add','add','ret']), (hex(ident),label,hex(addr),[(i.mnemonic,i.op_str) for i in ins])
  vals=[]
  for base in [0,0x7f12345000]:
   u=Uc(UC_ARCH_ARM64,UC_MODE_ARM);u.mem_map((base+addr)&~4095,4096);u.mem_write(base+addr,code);u.emu_start(base+addr,base+addr+16,count=4);vals.append(u.reg_read(UC_ARM64_REG_X0)-base)
  assert vals[0]==vals[1];entry[label]={'getter':hex(addr),'address_relative':hex(vals[0]),'code':code.hex(),'asm':[i.mnemonic+' '+i.op_str for i in ins],'Unicorn_ASLR_two_bases_equal':True};row.append((vals[0],code))
 out.append(entry);hdr.append('{%#x,%#x,%#x,%#x,%#x,%d,{%s},{%s}},'%(ident,va,sh,row[0][0],row[1][0],size,','.join(hex(b) for b in row[0][1]),','.join(hex(b) for b in row[1][1])))
hdr.append('};');(H/'fx3-media-params-v1.inc').write_text('\n'.join(hdr)+'\n')
points={'D':[0xe6dc,0xe750,0xf1e4,0xf274,0xf278,0xf2b8,0xf31c,0xf380,0xf39c,0xf468,0xf8d8,0xd40c,0xd534,0xf92c,0xf978,0xf9a0,0xfa00,0xfa24,0xfa3c,0xfa50,0xe8f4,0xe9d4,0xe9e0,0xec34,0x1091c,0x109e0,0x10d38], 'M':[0x9c98,0x9d6c,0x9dc4,0x9dc8,0x9e40,0x9e14,0x9e18,0x9eac,0x9ef8]}
proof={'parameters':out,'points':{},'source_SHA256':{n:hashlib.sha256((P/n).read_bytes()).hexdigest() for n in ['appFw.so','libInfraMediaDetect.so','libInfraMediaMount.so']},'scope':'Only guarded passive original instructions and read-only sampled references; no getter invocation/state write/protocol reply'};ph=['struct point {U off;W word;};']
for tag,n in [('D','libInfraMediaDetect.so'),('M','libInfraMediaMount.so')]:
 ph.append('static struct point points_%s[]={'%tag);proof['points'][tag]=[]
 for va in points[tag]:
  b=read(n,va,4);i=next(cs.disasm(b,va));assert i.mnemonic not in ['adrp','adr','b','b.eq','b.ne','tbz','tbnz','ldr_literal'];proof['points'][tag].append({'va':hex(va),'bytes':b.hex(),'asm':i.mnemonic+' '+i.op_str});ph.append('{%#x,%#x},'%(va,int.from_bytes(b,'little')))
 ph.append('};')
(H/'fx3-media-points-v1.inc').write_text('\n'.join(ph)+'\n');(R/'ap92-passive-original-proof.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(out,indent=1));print('points', {k:len(v) for k,v in points.items()})
