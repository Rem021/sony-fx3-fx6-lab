from pathlib import Path
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM
import struct,json
R=Path(__file__).resolve().parent;P=R.parent/'original-uipc/ap-projection/regular-files/usr/lib/appFw.so';b=P.read_bytes();cs=Cs(CS_ARCH_ARM64,CS_MODE_ARM);out=[]
with P.open('rb') as f:
 e=ELFFile(f)
 def raw(v,n):
  p=next(s['p_offset']+v-s['p_vaddr'] for s in e.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=v and v+n<=s['p_vaddr']+s['p_filesz']);return b[p:p+n]
 for v in [0x2dca7fc,0x2dca610,0x2b7f8cc,0x2d9ac90,0x237fe28,0x2380320,0x2380468,0x23803f4,0x21916b0,0x218fd0c,0x2b8037c,0x1cdcf28,0x2bd76f4,0x2dca6a0,0x2dca6e0]:
  q=raw(v,4);i=next(cs.disasm(q,v));print(hex(v),i.mnemonic,i.op_str);out.append({'va':hex(v),'raw':q.hex(),'word':struct.unpack('<I',q)[0],'asm':i.mnemonic+' '+i.op_str})
 for v,n in [(0x2dca860,0x64),(0x293019c,0x70),(0x21916b0,0xa0),(0x23803e8,0x24),(0x218fd0c,0x38)]:
  print('WINDOW',hex(v));print('\n'.join(hex(i.address)+' '+i.mnemonic+' '+i.op_str for i in cs.disasm(raw(v,n),v)))
(R/'ap87-probes-proof.json').write_text(json.dumps(out,indent=2)+'\n')
