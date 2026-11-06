import sys,struct
sys.dont_write_bytecode=True
from extract import *
def rels(k,targets):
 e=E[k];out={}
 for s in e.sections:
  if s[1]!=4:continue
  for off in range(s[4],s[4]+s[5],24):
   va,info,ad=struct.unpack_from('<QQq',e.b,off)
   if va not in targets:continue
   ds=e.sections[s[6]];ss=e.sections[ds[6]];idx=info>>32;no=struct.unpack_from('<I',e.b,ds[4]+idx*24)[0];sv=struct.unpack_from('<Q',e.b,ds[4]+idx*24+8)[0];at=ss[4]+no
   out[va]={'va':hex(va),'fileoff':hex(off),'rela_bytes':e.b[off:off+24].hex(),'target':hex(sv+ad),'symbol':e.b[at:e.b.index(b'\0',at)].decode()}
 return out
out={}
for k,gots in [('fx3_ap',[0x474b450,0x4735f68,0x4702a70]),('fx6_ap',[0x2eef5d0,0x2eeb3b0,0x2ee37e0])]:
 roots=rels(k,gots);slots=rels(k,{int(r['target'],16)+i for r in roots.values() for i in range(0,0x38,8)})
 out[k]={'gots':list(roots.values()),'slots':list(slots.values())}
 for r in slots.values():
  target=int(r['target'],16)
  if target and target< (0x3800000 if k=='fx3_ap' else 0x2500000):dis(k,target,target+32)
(H/'vtables.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
