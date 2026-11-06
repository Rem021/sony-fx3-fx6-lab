from pathlib import Path
from elftools.elf.elffile import ELFFile
from capstone import *
import struct,json
R=Path(__file__).resolve().parent;p=R.parent/'original-uipc/ap-projection/regular-files/usr/lib/appFw.so'
with p.open('rb') as f:
 e=ELFFile(f);t=e.get_section_by_name('.text');data=t.data();base=t['sh_addr'];cs=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN);out=[]
 for ident in [0x6db,0x6dc,0x6e3,0x6e4,0x708,0x709,0x1203,0x1204,0x13e,0x13f]:
  hits=[]
  for reg in range(8):
   b=struct.pack('<I',0x52800000|(ident<<5)|reg);at=-1
   while True:
    at=data.find(b,at+1)
    if at<0:break
    if at%4:continue
    va=base+at;ins=[{'va':hex(i.address),'asm':i.mnemonic+' '+i.op_str,'bytes':i.bytes.hex()} for i in cs.disasm(data[max(0,at-64):at+48],max(base,va-64))];hits.append({'va':hex(va),'reg':reg,'window':ins})
  out.append({'id':hex(ident),'hits':hits});print(hex(ident),len(hits),[(x['va'],x['reg']) for x in hits][:25])
 (R/'ap92-parameter-xrefs.json').write_text(json.dumps(out,indent=2)+'\n')
