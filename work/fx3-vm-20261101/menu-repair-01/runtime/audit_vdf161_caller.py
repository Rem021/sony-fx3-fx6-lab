from pathlib import Path
from elftools.elf.elffile import ELFFile
from capstone import *
import hashlib,json,re
R=Path(__file__).resolve().parent;A=R.parent/'original-uipc/ap-projection/regular-files/usr/lib';p=A/'appFw.so';b=p.read_bytes();e=ELFFile(p.open('rb'));sec=e.get_section_by_name('.text');cs=Cs(CS_ARCH_ARM64,CS_MODE_ARM);blocks=[(0x2debdb0,0xc4),(0x2dd0794,0x40),(0x2d8aa28,0xc8)];out={'appFw_sha256':hashlib.sha256(b).hexdigest(),'blocks':{hex(a):[{'va':hex(i.address),'bytes':i.bytes.hex(),'instruction':i.mnemonic+' '+i.op_str} for i in cs.disasm(sec.data()[a-sec['sh_addr']:a-sec['sh_addr']+n],a)] for a,n in blocks},'strings':{}}
for a in [0x3951631,0x3951658,0x39516ac,0x39516d8]:
 seg=next(s for s in e.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=a<s['p_vaddr']+s['p_filesz']);off=seg['p_offset']+a-seg['p_vaddr'];out['strings'][hex(a)]=b[off:b.index(b'\0',off)].decode()
d=next((R/'runs').glob('ap65vdf161-*'));s=(d/'serial.log').read_text(errors='replace');ls=s.splitlines();i=next(i for i,l in enumerate(ls) if 'FX3_PROFILE_STACK_BEGIN' in l and 'header=0x161200d' in l);out.update(run=d.name,serial_sha256=hashlib.sha256((d/'serial.log').read_bytes()).hexdigest(),native_stack=ls[i:i+11],request='0d2061010a0001800000',completion_binding='Unclosed AP0161 to legacyVDF011d/111d and back to AP reply; no completion added',interpretation='Original sequence_set_gamma_disp_assist sends vdf_disp_set_monitor_lut; native payload mode0. Not generic CameraProfile or CEC. Legacy VDF class name located but bridge semantics still pending.')
(R/'vdf161-caller-proof.json').write_text(json.dumps(out,indent=2)+'\n')
