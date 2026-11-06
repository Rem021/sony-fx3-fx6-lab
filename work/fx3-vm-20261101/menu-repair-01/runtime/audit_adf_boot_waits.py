from pathlib import Path
from elftools.elf.elffile import ELFFile
from capstone import *
import json,hashlib
R=Path(__file__).resolve().parent;p=R.parent/'original-uipc/ap-projection/regular-files/usr/lib/appFw.so';b=p.read_bytes();e=ELFFile(p.open('rb'));sec=e.get_section_by_name('.text');cs=Cs(CS_ARCH_ARM64,CS_MODE_ARM);blocks=[(0x2ded154,0xc4),(0x2deea08,0x78),(0x2b5fae4,0x80),(0x2b61d6c,0x80)];out={'source_sha256':hashlib.sha256(b).hexdigest(),'blocks':{hex(a):[{'va':hex(i.address),'bytes':i.bytes.hex(),'instruction':i.mnemonic+' '+i.op_str} for i in cs.disasm(sec.data()[a-sec['sh_addr']:a-sec['sh_addr']+n],a)] for a,n in blocks},'strings':{}}
for a in [0x39677b8,0x391a5f0,0x3917e31,0x39184f4,0x3918523,0x39184bf]:
 seg=next(s for s in e.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=a<s['p_vaddr']+s['p_filesz']);o=seg['p_offset']+a-seg['p_vaddr'];out['strings'][hex(a)]=b[o:b.index(b'\0',o)].decode()
d=next((R/'runs').glob('ap69audio-*'));ls=(d/'serial.log').read_text(errors='replace').splitlines();out['run']=d.name;out['stacks']={}
for header in ['0x32e200d','0x33d200d']:
 i=next(i for i,l in enumerate(ls) if 'FX3_PROFILE_STACK_BEGIN' in l and 'header='+header in l);j=next(j for j in range(i,len(ls)) if 'FX3_PROFILE_STACK_END' in ls[j]);out['stacks'][header]=ls[i:j+1]
out['requests']=['0d202e030a0001800800','0d203d0308000180'];out['facts']=['032e AP adf_set_volume_i, wirebyte8=8, expected12Bcompletion/status+8; currentlyunhandled','033d AP adf_sys_get_system_sound_address, expected24Breply, status+8, physical64address+16 copiedtoout+8; no arbitrary0address replyadded','CPsystemsound buffer address/extent/native ownership andloading oforiginalsoundassets notbound; 0118panel output stillpending; no menuacceptance'];(R/'adf-boot-waits-proof.json').write_text(json.dumps(out,indent=2)+'\n')
