from pathlib import Path
from io import BytesIO
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
import json,hashlib,struct
R=Path(__file__).resolve().parent;O=R/'scu-model';p=R.parent/'original-uipc/original-modules/upm.ko';b=p.read_bytes();assert hashlib.sha256(b).hexdigest()=='ba0cca76ec8e19836697d69d0851c5a0bd2c2eea98ee2aa54d1eff3408f1ec8e';e=ELFFile(BytesIO(b));sec=e.get_section_by_name('.text');t=sec.data();sy=e.get_section_by_name('.symtab');rs=e.get_section_by_name('.rela.text');refs={rel['r_offset']:sy.get_symbol(rel['r_info_sym']).name for rel in rs.iter_relocations()};cs=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN);cs.skipdata=True
ins=[]
for i in cs.disasm(t[0xab9c:0xae20],0xab9c):
 r={'va':hex(i.address),'bytes':i.bytes.hex(),'instruction':i.mnemonic+' '+i.op_str,'reloc_symbol':refs.get(i.address)}
 if i.mnemonic=='ldr' and ', #' in i.op_str and '[' not in i.op_str:
  a=int(i.op_str.split(', #')[1],16)
  if a+8<=len(t):r['literal_u64']=hex(struct.unpack_from('<Q',t,a)[0])
 ins.append(r)
addresses={}
for s in e.iter_sections():
 if s['sh_type']=='SHT_PROGBITS':
  for off in range(0,len(s.data())-7,4):
   v=struct.unpack_from('<Q',s.data(),off)[0]
   if 0xfffffffff1388000<=v<0xfffffffff1389000:addresses.setdefault(hex(v),[]).append({'section':s.name,'offset':hex(off)})
out={'upm_sha256':hashlib.sha256(b).hexdigest(),'observed_fault_pc_text':'0xabd8','SCU_native_literals':addresses,'consumer':ins,'sony_header':{'path':str(O/'regs-scu.h'),'sha256':hashlib.sha256((O/'regs-scu.h').read_bytes()).hexdigest(),'DATA':0,'SET':4,'CLR':8},'boundary':'Restricted virtual AP request bank INFERRED from native consumer; generic SCU DATA/SET/CLR header does not prove f50/f54/f58/f5c/f60 handshake layout. No physical effects/CP ACK/firmware replies.'};(O/'upm-scu-proof.json').write_text(json.dumps(out,indent=2)+'\n');print(addresses)
for i in ins[:65]:print(i['va'],i['instruction'],i.get('literal_u64',''),i['reloc_symbol'] or '')

registers={};computed=[]
import re
for i in ins:
 text=i['instruction'];m=re.fullmatch(r'mov (x[0-9]+), #(-?0x[0-9a-f]+|-?[0-9]+)',text)
 if m:registers[m[1]]=int(m[2],0)&((1<<64)-1)
 m=re.fullmatch(r'movk (x[0-9]+), #(0x[0-9a-f]+), lsl #16',text)
 if m and m[1] in registers:
  registers[m[1]]=(registers[m[1]]&~(0xffff<<16))|(int(m[2],16)<<16)
  if 0xfffffffff1388000<=registers[m[1]]<0xfffffffff1389000:computed.append({'instruction_va':i['va'],'register':m[1],'computed_value':hex(registers[m[1]])})
out['native_computed_addresses']=computed
(O/'upm-scu-proof.json').write_text(json.dumps(out,indent=2)+'\n')
