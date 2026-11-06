import sys
sys.dont_write_bytecode=True
from extract import *
import struct
R={}
for k in ['fx3_ap','fx6_ap','fx3_mpr','fx6_mpr']:
 e=E[k];rr={}
 for s in e.sections:
  if s[1]!=4:continue
  ds=e.sections[s[6]];ss=e.sections[ds[6]];st=e.b[ss[4]:ss[4]+ss[5]]
  for off in range(s[4],s[4]+s[5],24):
   va,info,ad=struct.unpack_from('<QQq',e.b,off);idx=info>>32
   no=struct.unpack_from('<I',e.b,ds[4]+idx*24)[0];sv=struct.unpack_from('<Q',e.b,ds[4]+idx*24+8)[0]
   rr[va]={'va':hex(va),'relocation_fileoff':hex(off),'raw_rela':e.b[off:off+24].hex(),'symbol':st[no:].split(b'\0')[0].decode(),'resolved_link_va':hex(sv+ad),'type':info&0xffffffff}
 R[k]=rr
if __name__=='__main__':
 out={}
 for k,vas in [('fx6_ap',[0x2ee6960,0x2ee9c50,0x2eeab68,0x2eecb38,0x2ee1950,0x2ee6908,0x2eef5d0,0x2eeb3b0,0x2ee37e0]),('fx3_mpr',[0x2fade0]),('fx6_mpr',[0x108ee08])]:
  out[k]=[]
  for va in vas:
   r=R[k][va].copy();t=int(r['resolved_link_va'],16)
   if t and k=='fx6_ap' and va in [0x2eef5d0,0x2eeb3b0,0x2ee37e0]:r['vtable_slots']=[R[k].get(a,{'va':hex(a),'raw':E[k].mapping(a,8)}) for a in range(t,t+0x38,8)]
   out[k].append(r)
 (H/'resolved-relocations.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
