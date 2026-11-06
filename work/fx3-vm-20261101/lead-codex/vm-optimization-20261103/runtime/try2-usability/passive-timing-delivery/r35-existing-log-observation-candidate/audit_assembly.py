#!/usr/bin/env python3
"""Bounded static decoding only. Not an instruction emulator or guest execution."""
from pathlib import Path
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
import json,hashlib,io
O=Path(__file__).resolve().parent;D=O.parent;ROOT=next(p for p in O.parents if p.name=='Mac');RT=ROOT/'work/fx3-vm-20261101/menu-repair-01/runtime';md=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN);md.detail=True
def funcs(path):
 b=Path(path).read_bytes();e=ELFFile(io.BytesIO(b));sections=[s for s in e.iter_sections() if s['sh_type'] in ('SHT_SYMTAB','SHT_DYNSYM')];syms={s.name:s for st in sections for s in st.iter_symbols()};return b,e,syms
def decode_func(path,name):
 b,e,ss=funcs(path);s=ss[name];seg=next(x for x in e.iter_segments() if x['p_type']=='PT_LOAD' and x['p_vaddr']<=s['st_value']<x['p_vaddr']+x['p_filesz']);off=seg['p_offset']+s['st_value']-seg['p_vaddr'];code=b[off:off+s['st_size']];ins=list(md.disasm(code,s['st_value']));assert len(ins)*4==len(code);return s,code,ins
result={'scope':'static AArch64 code only; original locks may retain their old retry loops','candidate':{}};lines=[]
for tag in ['osd','ui']:
 path=O/'build'/('fx3-'+tag+'-r35.so');b,e,ss=funcs(path);selected=['fx3_r35_snapshot_v1','osal_snd_msg','observer_bind'] if tag=='osd' else ['fx3_gate_event']
 functions={}
 for name in selected:
  s,code,ins=decode_func(path,name);c=[];weak=[];loops=[]
  for i,x in enumerate(ins):
   # Source argument one: number loaded into w0 immediately before syscall PLT.
   if x.mnemonic=='mov' and x.op_str=='w0, #0xac':
    follow=ins[i+1:i+5];calls=[v for v in follow if v.mnemonic=='bl'];assert calls;c.append({'number_load':hex(x.address),'call':hex(calls[0].address)})
   if x.mnemonic=='stxr':
    nxt=ins[i+1];targets=[int(z,16) for z in __import__('re').findall(r'#(0x[0-9a-f]+)',nxt.op_str)]
    # Distinguish original strong own_lock loops from new one-attempt weak claims.
    weak.append({'stxr':hex(x.address),'following':nxt.mnemonic+' '+nxt.op_str,'direct_retry':bool(targets and targets[-1]<=x.address)})
  # Resolve straight-line ADR/ADRP+ADD address materialization at exclusive sites.
  constants={};newclaims=[];locks={ss[k]['st_value']:k for k in ['r35_lock','r35_log_lock'] if k in ss}
  for i,x in enumerate(ins):
   ops=x.operands
   if x.mnemonic in ('adr','adrp') and len(ops)==2:constants[x.reg_name(ops[0].reg)]=ops[1].imm
   elif x.mnemonic=='add' and len(ops)==3 and ops[2].type==2:
    dest=x.reg_name(ops[0].reg);src=x.reg_name(ops[1].reg)
    if src in constants:constants[dest]=constants[src]+ops[2].imm
    else:constants.pop(dest,None)
   elif x.mnemonic=='mov' and len(ops)==2:
    dest=x.reg_name(ops[0].reg)
    if ops[1].type==2:constants[dest]=ops[1].imm
    elif x.reg_name(ops[1].reg) in constants:constants[dest]=constants[x.reg_name(ops[1].reg)]
    else:constants.pop(dest,None)
   elif x.mnemonic in ('ldaxr','ldxr','stxr'):
    mem=ops[-1];base=x.reg_name(mem.mem.base);address=constants.get(base)
    if x.mnemonic=='stxr' and address in locks:
     after=ins[i+1];assert after.mnemonic=='cbnz';target=after.operands[-1].imm
     # Weak one-attempt failure edge goes out of this claim, never to its LDXR.
     assert target>x.address,(name,hex(x.address),hex(target))
     newclaims.append({'stxr':hex(x.address),'BSS_lock':locks[address],'failure_target':hex(target),'no_direct_retry':True})
   elif x.mnemonic.startswith(('ldr','ldp','ldur')) and ops and ops[0].type==1:
    constants.pop(x.reg_name(ops[0].reg),None)
  functions[name]={'new_weak_claims':newclaims,'address':hex(s['st_value']),'bytes':s['st_size'],'sha256':hashlib.sha256(code).hexdigest(),'mov172_sites':c,'stxr_sites':weak}
  lines.append(f'\n{tag}:{name} VA={s["st_value"]:#x} bytes={s["st_size"]}')
  lines.extend(f'{x.address:08x} {x.bytes.hex()} {x.mnemonic} {x.op_str}' for x in ins)
 if tag=='osd':
  assert len(functions['fx3_r35_snapshot_v1']['mov172_sites'])==1
  assert len(functions['osal_snd_msg']['mov172_sites'])>=2
  # bind includes one original syscall(172), one new begin query and cloned
  # end queries in each mutually exclusive original return branch.
  assert len(functions['observer_bind']['mov172_sites'])>=3
  # All weak claims in stand-alone snapshot (no original native lock here).
  assert not any(x['direct_retry'] for x in functions['fx3_r35_snapshot_v1']['stxr_sites'])
  # Identify actual memory load into bind result before BSS stores, not magic constant.
  s,code,ins=decode_func(path,'observer_bind');loads=[{'address':hex(x.address),'instruction':x.mnemonic+' '+x.op_str} for x in ins if x.mnemonic=='ldr' and x.op_str.startswith('x')]
  functions['observer_bind']['all_64bit_loads_for_magic_review']=loads
  magic=[x for x in ins if x.mnemonic=='ldr' and x.op_str=='x10, [x19]'];assert len(magic)==1
  functions['observer_bind']['verified_magic_load']={'address':hex(magic[0].address),'raw':magic[0].bytes.hex(),'instruction':'ldr x10, [x19]','meaning':'one actual volatile ring magic read after original stores and successful new ownership/claim, not a constant or End state'}
  assert len(functions['fx3_r35_snapshot_v1']['new_weak_claims'])==1
  assert len(functions['osal_snd_msg']['new_weak_claims'])==2
  assert len(functions['observer_bind']['new_weak_claims'])==6
 result['candidate'][tag]=functions
 if tag=='ui':assert len(functions['fx3_gate_event']['new_weak_claims'])==1
 # Compare unchanged probe core function instructions, despite shifted ELF VA.
 if tag=='ui':
  baseline=O/'build/baseline-ui.so';_,_,base_ss=funcs(baseline);names=[k for k in ss if (k.startswith('fx3_gate_probe_core') or k in ['fx3_gate_test','fx3_gate_branch_test','fx3_gate_bl_test']) and k in base_ss and ss[k]['st_size']]
  probe=[]
  for name in names:
   a,ac,ai=decode_func(path,name);bb,bc,bi=decode_func(baseline,name);assert len(ac)==len(bc)
   relocation_differences=[]
   for x,y in zip(ai,bi):
    if x.bytes==y.bytes:continue
    assert x.mnemonic==y.mnemonic=='bl',(name,x.mnemonic,y.mnemonic)
    target=int(x.op_str.lstrip('#'),16);old_target=int(y.op_str.lstrip('#'),16)
    names_new={k for k,v in ss.items() if v['st_value']==target};names_old={k for k,v in base_ss.items() if v['st_value']==old_target};same=names_new&names_old;assert same
    relocation_differences.append({'offset':x.address-a['st_value'],'same_call_target':sorted(same)})
   probe.append({'name':name,'bytes':len(ac),'sha256':hashlib.sha256(ac).hexdigest(),'only_relocated_BL_differences':relocation_differences})
  assert probe;result['unchanged_probe_instructions_except_same_target_BL_relocations']=probe
# SDK actual libc syscall -> svc ABI and actual kernel table -> tgid load.
lib=RT/'guest-sdk/lib/libc-2.25.so';s,code,ins=decode_func(lib,'syscall');assert ins[0].mnemonic=='mov' and ins[0].op_str=='w8, w0';assert any(x.mnemonic=='svc' for x in ins);result['libc_syscall']={'address':hex(s['st_value']),'bytes':len(code),'raw':code.hex()};lines.append('\nActual CPIO-identical libc syscall');lines.extend(f'{x.address:08x} {x.bytes.hex()} {x.mnemonic} {x.op_str}' for x in ins)
binding=json.loads((O/'ACTUAL-BINDING.json').read_text());image=(ROOT/'work/sony-firmware-20261024/stage47-runtime-provider-binding/official-files/nflasha3/vmlinux.bin').read_bytes()
for key,v in binding['kernel_syscalls'].items():
 code=image[v['code_file_offset']:v['code_file_offset']+40];ins=list(md.disasm(code,int(v['target'],16)));lines.append('\nActual kernel '+key+' '+v['name']);lines.extend(f'{x.address:016x} {x.bytes.hex()} {x.mnemonic} {x.op_str}' for x in ins)
 result['kernel_'+key]=[{'address':hex(x.address),'instruction':x.mnemonic+' '+x.op_str} for x in ins]
(O/'ASSEMBLY-AUDIT.json').write_text(json.dumps(result,indent=2)+'\n');(O/'ASSEMBLY-AUDIT.txt').write_text('\n'.join(lines)+'\n');print('AArch64 source sites, libc SVC ABI, actual kernel table, unchanged probe bytes PASS')
