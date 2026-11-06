from pathlib import Path
import json,hashlib
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM
R=Path(__file__).resolve().parent;out={'scope':'Read-only original allocator/send/static kernel pool fields; runtime causality pending','images':{}}
for name,path,windows in [('libosal_uipc.so',R.parent/'original-uipc/ap-projection/regular-files/usr/lib/libosal_uipc.so',[(0x67b0,0x1c0),(0x5e60,0x2ac),(0x6e08,0x4c)]),('osal_uipc.ko',R.parent/'original-uipc/original-modules/osal_uipc.ko',[(0x44c0,360),(0x3248,0x300),(0x3bf8,520),(0x6998,544),(0x6bb8,288),(0x6cd8,228),(0x4d08,84),(0x3160,0xe8),(0x2ee8,0x270)]),('libObj.so',R.parent/'original-uipc/ap-projection/regular-files/usr/lib/libObj.so',[(0xf1d04,0x1a0)])]:
 b=path.read_bytes();im={'path':str(path),'sha256':hashlib.sha256(b).hexdigest(),'blocks':{}};out['images'][name]=im
 with path.open('rb') as f:
  e=ELFFile(f);cs=Cs(CS_ARCH_ARM64,CS_MODE_ARM);rels={}
  if name.endswith('.ko'):
   text=e.get_section_by_name('.text').data();r=e.get_section_by_name('.rela.text');sy=e.get_section(r['sh_link']);rels={q['r_offset']:sy.get_symbol(q['r_info_sym']).name+'+'+hex(q['r_addend']) for q in r.iter_relocations()};im['pool_symbols']={s.name:{'section':e.get_section(s['st_shndx']).name,'offset':hex(s['st_value']),'bytes':s['st_size']} for s in e.get_section_by_name('.symtab').iter_symbols() if s.name in ['vpool','rtpool']}
  for v,n in windows:
   if name.endswith('.ko'):q=text[v:v+n]
   else:
    off=next(s['p_offset']+v-s['p_vaddr'] for s in e.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=v and v+n<=s['p_vaddr']+s['p_filesz']);q=b[off:off+n]
   im['blocks'][hex(v)]={'bytes':q.hex(),'instructions':[{'va':hex(i.address),'bytes':i.bytes.hex(),'asm':i.mnemonic+' '+i.op_str,**({'relocation':rels[i.address]} if i.address in rels else {})} for i in cs.disasm(q,v)]}
out['interpretation']={'constructors':{'1002':'f1db4 allocator(dst74d,12,wait1), returnf1db8','1003':'f1e40 allocator(dst84d,36,wait1), returnf1e44','1005':'f1d28 allocator(dst84e,8,wait1), returnf1d2c'},'kernel_vpool_fields':{'symbol':'.bss+3740','bytes':56,'free_list_head':'+10 u64','maximum_bytes':'+20 u32','waiter_head':'+28 u64','current_free_bytes':'+30 u32','minimum_free_bytes':'+34 u32'},'CAUTION':'No user free alone does not prove absence of kernel free; pointer reuse recorded separately. Actual selected queue pool/remaining and blocked original caller need runtime evidence.'};(R/'ap86-lifetime-original-proof.json').write_text(json.dumps(out,indent=2)+'\n');print('AP86_ORIGINAL_ALLOCATOR_PROOF_SAVED')
