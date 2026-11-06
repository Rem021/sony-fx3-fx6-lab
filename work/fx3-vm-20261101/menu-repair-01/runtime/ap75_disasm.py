from pathlib import Path
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM
R=Path(__file__).resolve().parent;P=R.parent/'original-uipc/ap-projection/regular-files/usr/lib';cs=Cs(CS_ARCH_ARM64,CS_MODE_ARM)
for name,va,size in [('appFw.so',0x176fb4c,0xc0),('appFw.so',0x2191db0,0x80),('libObj.so',0x176ab0,0xc0),('libObj.so',0x100c48,0x90)]:
 p=P/name;b=p.read_bytes()
 with p.open('rb') as f:
  e=ELFFile(f);seg=next(s for s in e.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=va<s['p_vaddr']+s['p_filesz']);off=va-seg['p_vaddr']+seg['p_offset']
 print(name,hex(va))
 for i in cs.disasm(b[off:off+size],va):print(hex(i.address),i.bytes.hex(),i.mnemonic,i.op_str)
