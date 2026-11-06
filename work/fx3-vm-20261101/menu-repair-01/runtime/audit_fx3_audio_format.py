from pathlib import Path
import struct,json,hashlib
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB
R=Path(__file__).resolve().parent;p=R.parents[2]/'sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin';b=p.read_bytes();assert hashlib.sha256(b).hexdigest()=='c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba';base=0x108000;cs=Cs(CS_ARCH_ARM,CS_MODE_THUMB);blocks={}
for a,n in [(0x1ac088,0x26),(0x1b2494,0xa2),(0x161004,0xae),(0x59818c,0x7c),(0x1adbd4,0x76),(0x1adc7a,0x16),(0x1adcde,8),(0x1ac86c,0xc),(0x5ca3b2,0x52)]:
 blocks[hex(a)]=[{'va':hex(i.address),'bytes':i.bytes.hex(),'instruction':i.mnemonic+' '+i.op_str} for i in cs.disasm(b[a-base:a-base+n],a)]
entries=[]
for cmd in [0xbf,0xc0,0xc1,0xc2]:
 v=struct.unpack_from('<H',b,0x1ab6a6-base+(cmd-0x1f)*2)[0];entries.append({'internal_command':hex(cmd),'table_u16':hex(v),'branch':hex(0x1ab6a6+v*2)})
print(entries)
x={'source_sha256':hashlib.sha256(b).hexdigest(),'blocks':blocks,'internal_request_dispatch_table':entries,'format_state':{'singleton':'ee5bcc','setter':'5981c6 writes four bytes tosingleton+8','getter':'5981ee reads same four bytes','original_accepted_format':'0or1; larger yields e002','legacy_payload':'handler1b2494 zero-initializes4B thenwritesbyteformat at+8 of12B frame2004/0304','legacy_response':'16103e constructs2004/8304/12/1/status0 fromsetter; audio-domain tag1adc88/1adcdeOR580000','AP_completion':'5ca3b2 constructs200d/132d/12/8001/u32status','scope':'Explicit inactive virtual audio config only. No originalCP, hardware signal, PCM/audio frames or clock/output model.'},'native_request':'AP45 observed0d202d030a0001800000 destination92840747 source81cf6186'}
(R/'fx3-audio-format-proof.json').write_text(json.dumps(x,indent=2)+'\n')
