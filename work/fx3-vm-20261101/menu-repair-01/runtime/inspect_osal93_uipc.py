from pathlib import Path
from elftools.elf.elffile import ELFFile
from capstone import *
P=Path('../original-uipc/ap-projection/regular-files/usr/lib/libosal_uipc.so');cs=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN)
with P.open('rb') as f:
 e=ELFFile(f);syms={s.name:s for s in e.get_section_by_name('.dynsym').iter_symbols()};print([(n,hex(s['st_value']),s['st_size']) for n,s in syms.items() if any(k in n for k in ['msg_queue','stat_msgq','msg_src'])])
 for name in ['osal_reg_msg_queue','osal_reg_msg_queue_cb','osal_stat_msgq','u_osal_reg_msg_queue_cb','u_osal_stat_msgq','osal_unreg_msg_queue']:
  s=syms.get(name)
  if not s:continue
  start=s['st_value'];size=s['st_size'];seg=next(s for s in e.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=start< s['p_vaddr']+s['p_filesz']);b=seg.data()[start-seg['p_vaddr']:start-seg['p_vaddr']+size];print(name)
  for i in cs.disasm(b,start):print(hex(i.address),i.mnemonic,i.op_str)
