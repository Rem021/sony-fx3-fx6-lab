from pathlib import Path
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB
import struct,json,hashlib
R=Path(__file__).resolve().parent;p=R.parents[2]/'sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin';b=p.read_bytes();base=0x108000
cs=Cs(CS_ARCH_ARM,CS_MODE_THUMB)
blocks={}
for name,a,n in [('dispatch_registration',0x659d64,0x20),('request_handler',0x21825c,0x60),('state_dispatch',0x65a460,0x38),('shared_registration',0x65ca7e,0xbe),('observer_store',0x6598ea,6),('reply_constructor',0x65cb3c,0x42),('original_transport',0x218e8c,0x6e)]:
 raw=b[a-base:a-base+n];blocks[name]={'va':hex(a),'bytes':raw.hex(),'instructions':[{'va':hex(i.address),'bytes':i.bytes.hex(),'instruction':i.mnemonic+' '+i.op_str} for i in cs.disasm(raw,a)]}
# Exact RTTI name pointer -> typeinfo -> vtable -> registration virtual slot.
states=[]
for a in [0xba659c,0xba65a8,0xba65b4,0xba65c0,0xba65cc,0xba65d8,0xba65e4,0xba65f0,0xba65fc]:
 nameptr=struct.unpack_from('<I',b,a-base+4)[0];name=b[nameptr-base:].split(b'\0',1)[0].decode();needle=struct.pack('<I',a);refs=[o+base for o in range(0,len(b)-4,4) if b[o:o+4]==needle];vt=[h+4 for h in refs if 0xba5000<h<0xba6500];assert len(vt)==1,(name,vt);target=struct.unpack_from('<I',b,vt[0]+0x98-base)[0];assert target==0x65ca7f
 states.append({'name':name,'typeinfo':hex(a),'vtable':hex(vt[0]),'slot98':hex(target)})
out={'source':str(p),'source_sha256':hashlib.sha256(b).hexdigest(),'cpva':'raw offset+108000, same-package pformat configuration','blocks':blocks,'concrete_state_vtables':states,'verified_contract':{'destination':'909a015a','frame':'2500','command':'0127','minimum_original_request_bytes':12,'payload_u32_at8':'observer ID, distinct from reply source','state_effect':'Store supplied observer ID in thirteen existing condition objects at singleton offsets ec..11c, through6598ea. No condition value changed or notification sent by registration.','reply':'12bytes frame2500 cmd8127 length12 flags1 statusu32=0','transition':'all nine concrete HDMI state vtables use same65ca7e slot98, returning0/no transition'},'model_scope':'Explicit software registration state only, no original CP execution, no hotplug or output frames','native_request_observed':'AP32 AppFw tid276 target909a015a tag01272500 envelope0001000c then receive81cf6187'}
(R/'hdmi-registration-proof.json').write_text(json.dumps(out,indent=2)+'\n');print(out['source_sha256']);print(states)
