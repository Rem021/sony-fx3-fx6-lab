from pathlib import Path
import struct,json,hashlib
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB
R=Path(__file__).resolve().parent;p=R.parents[2]/'sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin';b=p.read_bytes();assert hashlib.sha256(b).hexdigest()=='c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba';base=0x108000;cs=Cs(CS_ARCH_ARM,CS_MODE_THUMB);blocks={}
for a,n in [(0x1ab910,0x28),(0x5cb9ca,0xb8),(0x1abab4,0x28),(0x1b4a50,0x2f0),(0x5f5f6c,0x154),(0x5f3096,0x10e),(0x60f364,0x18),(0x60ed16,0x7a),(0x1adbd4,0x114),(0x5c9962,0x52),(0x5c9aaa,0x52)]:
 blocks[hex(a)]=[{'va':hex(i.address),'bytes':i.bytes.hex(),'instruction':i.mnemonic+' '+i.op_str} for i in cs.disasm(b[a-base:a-base+n],a)]
classes={}
for name in ['N3VDF23VdfInputCmdSetYuvLayoutE','N3VDF36VdfDisplayCmdSetPanelBrightnessSlopeE','N3VDF17SubsystemAccessorE','N3VDF11MsgAccessorE']:
 off=b.find(name.encode()+b'\0');assert off>=0;refs=[i for i in range(0,len(b)-4,4) if b[i:i+4]==struct.pack('<I',off+base)];assert len(refs)==1;ti=base+refs[0]-4;vrefs=[i for i in range(0,len(b)-4,4) if b[i:i+4]==struct.pack('<I',ti)];assert len(vrefs)==1;vt=vrefs[0]+4
 slots=[0xc,0x10,0x14] if 'Cmd' in name else [0x1ec] if 'Subsystem' in name else [8,0x88]
 classes[name]={'name_va':hex(off+base),'typeinfo':hex(ti),'vtable_address_point':hex(vt+base),'slots':{hex(i):hex(struct.unpack_from('<I',b,vt+i)[0]) for i in slots}}
x={'source':str(p),'sha256':hashlib.sha256(b).hexdigest(),'classes':classes,'blocks':blocks,'facts':['014c internal98 calls1b4a50 ->legacy2001/0305; classvtable ID5f5f6c matches0305','5f5f7c validates enabled1/type<4 then sends1305/status0 at5f5fb8 BEFORE5f6044 internallysends f023 copiedlayout32B at5f60ac; acceptance is not outputcompletion','013d internal8b calls5cb9ca ->legacy2001/010d; class ID5f3096 matches010d','5f30fc usesselectorbits1/2 andsubsystemvtable+1ec; 60f364 savesu32slope tostate+144/+148, zero also queues originaltrigger30;110d/status0 afterupdates','60ed16 createslegacyreply;1adbd4 routes2001/110d,1305 tostatusat+8 andOR590000;5c9962/5c9aaa create113d/114c12Bcompletion'],'model_scope':'Finite explicit acceptancequeue8 retaining40B AP layouts for software640x480; brightnessshadow+pendingreset. No pixel/backend/activeoutput completion. Queue not draineduntil validated softwareconsumer exists. Unsupportedrequestscannotreceive success.'}
(R/'fx3-vdf-config-proof.json').write_text(json.dumps(x,indent=2)+'\n')
