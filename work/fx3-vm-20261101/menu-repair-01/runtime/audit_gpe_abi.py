from pathlib import Path
from io import BytesIO
import json,hashlib
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
R=Path(__file__).resolve().parent; m=json.loads((R.parent/'original-uipc/ap-projection/full-v4/projection-manifest-full-v4.json').read_text());row=next(x for x in m['members'] if x['guest_path']=='/usr/lib/libgpe.so');b=Path(row['local_file']).read_bytes();assert hashlib.sha256(b).hexdigest()==row['sha256'];e=ELFFile(BytesIO(b));ds=e.get_section_by_name('.dynsym');r=e.get_section_by_name('.rela.plt');plt=e.get_section_by_name('.plt');mp={plt['sh_addr']+32+i*16:ds.get_symbol(v['r_info_sym']).name for i,v in enumerate(r.iter_relocations())};cs=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN)
names=['_ZN5mpgpe14InitializeDrawENS_3GpeE','_ZNK5mpgpe5Gperm4InitEv','_ZN5mpgpe8FillRectENS_3GpeENS_7IntCoreEjjRKNS_13FillRectParamE','_ZN5mpgpe7BitBlitENS_3GpeENS_7IntCoreEjjRKNS_12BitBlitParamE','_ZN5mpgpe5FlushENS_3GpeENS_7IntCoreEjjRKNS_10FlushParamE','_ZN5mpgpe7message12SendDrawCompEjPKvm']
funcs={}
for sym in ds.iter_symbols():
 if sym.name not in names:continue
 a=sym['st_value'];n=sym['st_size']
 for seg in e.iter_segments():
  if seg['p_type']=='PT_LOAD' and seg['p_vaddr']<=a<a+n<=seg['p_vaddr']+seg['p_filesz']:off=seg['p_offset']+a-seg['p_vaddr'];break
 ins=[]
 for i in cs.disasm(b[off:off+n],a):
  ins.append({'va':hex(i.address),'instruction':i.mnemonic+' '+i.op_str,'bytes':i.bytes.hex(),'plt_symbol':mp.get(int(i.op_str[1:],16)) if i.mnemonic=='bl' and i.op_str.startswith('#') else None})
 funcs[sym.name]=ins
out={'source_sha256':row['sha256'],'functions':funcs,'relocations':[{'name':ds.get_symbol(v['r_info_sym']).name,'offset':hex(v['r_offset'])} for v in r.iter_relocations() if ds.get_symbol(v['r_info_sym']).name in names]};(R/'gpe-abi-proof.json').write_text(json.dumps(out,indent=2)+'\n')
for name,ins in funcs.items():
 print('\n',name)
 print('\n'.join(i['va']+' '+i['instruction']+' '+str(i['plt_symbol'] or '') for i in ins[:140]))

a=0xdb74;n=0x160
for seg in e.iter_segments():
 if seg['p_type']=='PT_LOAD' and seg['p_vaddr']<=a and a+n<=seg['p_vaddr']+seg['p_filesz']:
  off=seg['p_offset']+a-seg['p_vaddr'];break
out['private_hardware_setup']={'va':hex(a),'prefix16':b[off:off+16].hex(),'instructions':[{'va':hex(i.address),'bytes':i.bytes.hex(),'instruction':i.mnemonic+' '+i.op_str} for i in cs.disasm(b[off:off+n],a)],'original_fifo_entry':'GPE0 thread dcb0 calls private setup then original GetInstance/Main; only setup is replaced, Main/FIFO/queue APIs unchanged'}
(R/'gpe-abi-proof.json').write_text(json.dumps(out,indent=2)+'\n')
