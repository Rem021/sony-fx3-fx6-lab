from pathlib import Path
import json,hashlib,re,struct
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM
from elftools.elf.elffile import ELFFile
R=Path(__file__).resolve().parent;AP=R.parent/'original-uipc/ap-projection/regular-files/usr/lib/appFw.so';a=AP.read_bytes()
with AP.open('rb') as f:
 e=ELFFile(f);loads=[(s['p_vaddr'],s['p_offset'],s['p_filesz']) for s in e.iter_segments() if s['p_type']=='PT_LOAD']
def off(v):
 for va,o,n in loads:
  if va<=v<va+n:return o+v-va
 raise ValueError(hex(v))
cs=Cs(CS_ARCH_ARM64,CS_MODE_ARM)
blocks={}
for v,n in [(0x2de6600,0x600),(0x2df2cf0,0x130),(0x2dd2080,0xb0),(0x2dca980,0x160),(0x2b8b300,0x480),(0x2b8c650,0x100),(0x2dcac20,0x80),(0x2d8c664,0x30)]:
 blocks[hex(v)]=[dict(va=hex(i.address),bytes=i.bytes.hex(),instruction=i.mnemonic+' '+i.op_str) for i in cs.disasm(a[off(v):off(v)+n],v)]
strings={}
for v in (0x3960859,0x396087c,0x39608c8,0x39608ee,0x3960940,0x39226c6,0x391c6c9,0x3922a98,0x391c71f,0x3960a78):
 o=off(v);strings[hex(v)]=a[o:a.index(b'\0',o)].decode(errors='replace')
print(strings)
proof={'strings':strings,'AP_sha256':hashlib.sha256(a).hexdigest(),'blocks':blocks}
(R/'ap70-passive-callers-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
for v,ins in blocks.items():
 print(v)
 for i in ins:
  if i['instruction'].startswith(('bl ','adrp ','add x','mov w')):print(i)
