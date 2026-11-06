from pathlib import Path
from elftools.elf.elffile import ELFFile
from capstone import *
import json,hashlib
R=Path(__file__).resolve().parent;P=R.parent/'original-uipc/ap-projection/regular-files/usr/lib';cs=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN)
for name,start,end in [('libInfraMediaDetect.so',0xe8f4,0xecfc),('libInfraMediaDetect.so',0x1091c,0x10a30),('libInfraMediaDetect.so',0x10c98,0x10d3c),('libInfraMediaMount.so',0x9c98,0x9f78)]:
 with (P/name).open('rb') as f:
  e=ELFFile(f);s=next(s for s in e.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=start and end<=s['p_vaddr']+s['p_filesz']);d=s.data()[start-s['p_vaddr']:end-s['p_vaddr']]
  print(name)
  for i in cs.disasm(d,start):print(hex(i.address),i.bytes.hex(),i.mnemonic,i.op_str)
