from pathlib import Path
from elftools.elf.elffile import ELFFile
from capstone import *
import json,hashlib
R=Path(__file__).resolve().parent;P=R.parent/'original-uipc/ap-projection/regular-files/usr/lib';cs=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN)
for name,start,end in [('libInfraMediaDetect.so',0xf1e4,0xf338),('libInfraMediaDetect.so',0xf380,0xf484),('libInfraMediaDetect.so',0xf8d8,0xfa54),('libInfraMediaDetect.so',0xd40c,0xd590)]:
 with (P/name).open('rb') as f:
  e=ELFFile(f);s=next(s for s in e.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=start and end<=s['p_vaddr']+s['p_filesz']);d=s.data()[start-s['p_vaddr']:end-s['p_vaddr']]
  print(name)
  for i in cs.disasm(d,start):print(hex(i.address),i.bytes.hex(),i.mnemonic,i.op_str)
