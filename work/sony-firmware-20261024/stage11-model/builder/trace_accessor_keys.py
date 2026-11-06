"""Own static direct-call scan for typed model wrappers and selected immutable tables."""
import json,struct
from audit_typed_builder import Image,OUT,EXPECTED
im=Image(); leaves=json.loads((OUT/'model-leaf-accessors.json').read_text())['accessors']
targets={int(x['accessor'],16) for x in leaves}|{0x2934c9c,0x293d90c}
refs=[]
sec=im.elf.get_section_by_name('.text');d=sec.data();base=sec['sh_addr']
for k in range(0,len(d)-3,4):
 w=struct.unpack_from('<I',d,k)[0]
 if w>>26 not in (0b100101,0b000101):continue
 off=w&0x3ffffff;off-=1<<26 if off&(1<<25) else 0
 t=base+k+off*4
 if t not in targets:continue
 a=base+k;ctx=im.dump(a-8,a+20)
 # A key-like immediate in another routine is not a typed wrapper identity.
 # Restrict to known small builder wrappers and the immediate after this BL.
 key=ctx[3]['asm'] if 0x2bd0000<=a<0x2bd2000 and ctx[3]['asm'].startswith('mov x1, #') else None
 if key:refs.append({'accessor':hex(t),'call':hex(a),'key':int(key.split('#')[1],16),'context':ctx})
(OUT/'accessor-key-wrappers.json').write_text(json.dumps({'source_sha256':EXPECTED,'records':refs},indent=2))
for x in refs:print(x['accessor'],'call',x['call'],'key',hex(x['key']))
tables=[]
for a,n,base in [(0x392f9ac,8,0x2bee8c4),(0x392f8a0,7,0x2beb414),(0x392f9bc,7,0x2bee95c),(0x392f978,12,0x2bec5c4)]:
 width=1 if a in (0x392f8a0,0x392f978) else 2;d=im.read(a,n*width);vals=struct.unpack('<'+str(n)+('b' if width==1 else 'h'),d)
 tables.append({'va':hex(a),'raw':d.hex(),'entry_width':width,'base':hex(base),'signed_values':vals,'targets':[hex(base+x*4) for x in vals]})
(OUT/'selection-tables.json').write_text(json.dumps({'sha256':EXPECTED,'tables':tables},indent=2))
