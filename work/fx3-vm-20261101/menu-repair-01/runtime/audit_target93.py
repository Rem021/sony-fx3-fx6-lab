from pathlib import Path
from elftools.elf.elffile import ELFFile
from capstone import *
import json,hashlib,re
R=Path(__file__).resolve().parent;P=R.parent/'original-uipc/ap-projection/regular-files/usr/lib/libObj.so';cs=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN)
with P.open('rb') as f:
 e=ELFFile(f)
 def read(va,n):
  s=next(s for s in e.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=va and va+n<=s['p_vaddr']+s['p_filesz']);return s.data()[va-s['p_vaddr']:va-s['p_vaddr']+n]
 blocks=[]
 for start,end in [(0x1031b0,0x1032cc),(0x103454,0x103520),(0x103550,0x103600),(0xf96f4,0xf97ec)]:
  b=read(start,end-start);blocks.append({'start':hex(start),'end':hex(end),'SHA256':hashlib.sha256(b).hexdigest(),'instructions':[{'va':hex(i.address),'bytes':i.bytes.hex(),'asm':i.mnemonic+' '+i.op_str} for i in cs.disasm(b,start)]})
 vt=read(0x253a38,0x50);symbols=[{'name':s.name,'value':hex(s['st_value'])} for s in e.get_section_by_name('.dynsym').iter_symbols() if s['st_value'] and abs(s['st_value']-0x253a48)<64]
ls=(R/'runs/ap93r3setup-d8c86a95/serial.log').read_bytes().decode(errors='replace').split('\n');reg=next({'LF_line':i+1,'text':x} for i,x in enumerate(ls) if 'FX3_GPE_RESOURCE_REGISTER' in x and 'phys=0x43ae96000' in x);first=next({'LF_line':i+1,'text':x,'raw_next':ls[i+1]} for i,x in enumerate(ls) if 'FX3_GPE_CMD op=FillRect seq=72 ' in x);maps=next(x for x in ls if '7f58508000-7f58648000 rw-s 43ae96000' in x)
v={'source':str(P),'SHA256':hashlib.sha256(P.read_bytes()).hexdigest(),'native_open_observation':reg,'source_vptr_relative':'0x253a48','vtable_bytes_from_minus16':vt.hex(),'near_vtable_symbols':symbols,'original_blocks':blocks,'native_mapping':maps,'first_original_new_target_request':first,'cause':'Existing resource registry owns the target interval, but command dst within() rejects all non545 before resource_lookup.','current_proc_snapshot':'No full dmm_extents text snapshot saved in this run; do not invent it. Existing screen_live in original adapter independently reads proc each successful545draw, does not prove the newtarget unit.','role':'Native open type403 allocation, exact screen/doublebuffer role not proven; need not infer to apply original object lifecycle/rowbounds to a private software render target.','next_model_contract':'Only successful original native-open type403 / original253a48vptr / live fullfields+epoch / each-row nonoverflowspan / lifecycle lock+rechecks / originalclose revokes. Source mappings stayRO. No physical allowlist. Existing bitmap/subblock/compaction/queuedABA limitations remain explicit.'};(R/'ap93-new-target-original-proof.json').write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'reg':reg,'first':first,'symbols':symbols,'source_SHA256':v['SHA256']},ensure_ascii=False,indent=2))
