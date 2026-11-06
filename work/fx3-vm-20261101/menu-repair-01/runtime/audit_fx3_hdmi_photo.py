from pathlib import Path
import struct,json,hashlib
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB
R=Path(__file__).resolve().parent;p=R.parents[2]/'sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin';b=p.read_bytes();sha=hashlib.sha256(b).hexdigest();assert sha=='c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba';base=0x108000;cs=Cs(CS_ARCH_ARM,CS_MODE_THUMB);blocks={}
for a,n in [(0x659a20,0x1e),(0x21799c,0x28),(0x659fc2,0x16),(0x65b764,0x64),(0x65b0be,6),(0x656c5a,6),(0x213a48,0x16),(0x213a8c,6),(0x213ac0,0x2e)]:
 blocks[hex(a)]=[{'va':hex(i.address),'bytes':i.bytes.hex(),'instruction':i.mnemonic+' '+i.op_str} for i in cs.disasm(b[a-base:a-base+n],a)]
vt=[]
for a in [0xba5e60,0xba5f18,0xba5fd0,0xba6088,0xba6140,0xba61f8,0xba62b0,0xba6368,0xba6420]:
 target=struct.unpack_from('<I',b,a-base+0x4c)[0];assert target==0x65b765;vt.append({'address_point':hex(a),'slot':hex(a+0x4c),'thumb_handler':hex(target)})
target=0x213a5e+b[0x213a5e-base+6]*2;assert target==0x213a8c
x={'source':str(p),'sha256':sha,'blocks':blocks,'state_vtables':vt,'selector6_branch':hex(target),'facts':['0102 registration659a20 points21799d; wrapperreads request+8 byte andforwards659fc2','Every originalHDMI statevtable slot4c points65b765','65b764 storesrawbyte atHDMIsingleton+97, clamped>=3 to0 desiredpreset6','65b0be readsprofileat+8c;656c5a forwards to213a48;selector6 writesu32 toprofile+60','213ac0 writesdesired beforecheckingprofile+28 activecondition; inactivebranch returns1. Full active profile recomputation remains unsupported.','65b796..65b7ba always constructs2500/8102/12/1/status0; handler returns0 (no state transition).'],'model_scope':'Explicit absent-output configuration: supportrequestbyte0..2,paddingzero; retainraw/desiredpreset6 andcount; noHDMIconnection/hardware/pixels/activeprofile.'}
(R/'fx3-hdmi-photo-proof.json').write_text(json.dumps(x,indent=2)+'\n')
