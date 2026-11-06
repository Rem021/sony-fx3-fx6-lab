"""Own targeted static direct callers of three HS4K quality model accessors."""
from audit_typed_builder import Image,OUT,EXPECTED
import struct,json
im=Image();sec=im.elf.get_section_by_name('.text');d=sec.data();base=sec['sh_addr'];rows=[]
for k in range(0,len(d)-3,4):
 w=struct.unpack_from('<I',d,k)[0]
 if w>>26 not in (0b100101,0b000101):continue
 off=w&0x3ffffff;off-=1<<26 if off&(1<<25) else 0;t=base+k+off*4
 if t not in (0x2934e54,0x2934e68,0x2934e7c,0x2934e90,0x2934ea4,0x2934eb8):continue
 a=base+k
 if not 0x2700000<=a<=0x2800000:continue
 rows.append({'call':hex(a),'target':hex(t),'context':im.dump(a-0x70,a+0x90)})
(OUT/'quality-dispatch-callers.json').write_text(json.dumps({'sha256':EXPECTED,'callers':rows},indent=2))
for r in rows:
 print(r['call'],r['target'])
 for x in r['context']:
  if x['asm'].startswith(('mov w','mov x','bl #0x293','str w')):print(' ',x['va'],x['asm'])
