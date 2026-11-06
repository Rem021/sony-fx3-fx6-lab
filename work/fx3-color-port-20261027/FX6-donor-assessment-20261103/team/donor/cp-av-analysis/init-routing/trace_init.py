#!/usr/bin/env python3
"""Bounded original FX6 initializer CPU replay; no device or memcpy substitute."""
import collections,hashlib,json,pathlib,struct
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn import arm64_const as R

ROOT=pathlib.Path(__file__).resolve().parent
AV=ROOT.parents[1]/'fat-files/nflasha3/av-cam.bin'
PIN='56684d830eab1e304868548746d8275188a925f9e4ab9354560180c31b4a93cf'
BASE=0xffffffc001000000
ENTRY=0x29f508
CODE_END=0x2a5964
MEMCPY=(0xd80,0x1060)
TARGET=0xaa5208
SOURCE=0xb83218
STACK=0x50000000
STOP=0x60000000
BUDGET=500000

def main():
 image=AV.read_bytes()
 assert hashlib.sha256(image).hexdigest()==PIN
 assert struct.unpack_from('<Q',image)[0]-0x58==BASE
 uc=Uc(UC_ARCH_ARM64,UC_MODE_ARM)
 uc.mem_map(BASE,(len(image)+4095)&~4095)
 uc.mem_write(BASE,image)
 uc.mem_map(STACK,0x10000);uc.mem_write(STACK,b'\xa7'*0x10000)
 uc.mem_map(STOP,0x1000)
 uc.reg_write(R.UC_ARM64_REG_SP,STACK+0xf000)
 uc.reg_write(R.UC_ARM64_REG_LR,STOP)
 saved={getattr(R,f'UC_ARM64_REG_X{i}'):0x7777000000000000+i for i in range(19,30)}
 for reg,val in saved.items():uc.reg_write(reg,val)
 pcs=[];writes=[];copies=[];violations=[]
 def code(u,pc,size,_):
  if pc==STOP:u.emu_stop();return
  off=pc-BASE
  if not (ENTRY<=off<CODE_END or MEMCPY[0]<=off<MEMCPY[1]):
   violations.append({'kind':'outside_code','pc':hex(pc)});u.emu_stop();return
  pcs.append(off)
  if off==MEMCPY[0]:
   dst,src,n=[u.reg_read(x) for x in (R.UC_ARM64_REG_X0,R.UC_ARM64_REG_X1,R.UC_ARM64_REG_X2)]
   copies.append({'caller_offset':hex(u.reg_read(R.UC_ARM64_REG_LR)-BASE-4),
                  'dst_offset':hex(dst-BASE),'src_offset':hex(src-BASE),'bytes':n})
 def write(u,access,addr,size,value,_):
  pc=u.reg_read(R.UC_ARM64_REG_PC)
  if not (BASE<=addr and addr+size<=BASE+len(image) or STACK<=addr and addr+size<=STACK+0x10000):
   violations.append({'kind':'outside_memory_write','pc':hex(pc),'address':hex(addr),'size':size})
   u.emu_stop();return
  writes.append((addr,size,pc))
 uc.hook_add(UC_HOOK_CODE,code)
 uc.hook_add(UC_HOOK_MEM_WRITE,write)
 error=None
 try:uc.emu_start(BASE+ENTRY,STOP+4,count=BUDGET)
 except Exception as ex:error=repr(ex)
 pc=uc.reg_read(R.UC_ARM64_REG_PC)
 image_writes=[(a,s,p) for a,s,p in writes if BASE<=a<BASE+len(image)]
 stack_writes=[(a,s,p) for a,s,p in writes if STACK<=a<STACK+0x10000]
 merged=[]
 for a,end in sorted((a-BASE,a+s-BASE) for a,s,p in image_writes):
  if merged and a<=merged[-1][1]:merged[-1][1]=max(merged[-1][1],end)
  else:merged.append([a,end])
 ranges={}
 for a,s,p in image_writes:
  page=(a-BASE)//4096
  z=ranges.setdefault(page,{'min':a-BASE,'max':a+s-BASE,'events':0})
  z['min']=min(z['min'],a-BASE);z['max']=max(z['max'],a+s-BASE);z['events']+=1
 source_bytes=image[SOURCE:SOURCE+152]
 target_bytes=bytes(uc.mem_read(BASE+TARGET,152))
 result={'source_sha256':PIN,'entry_offset':hex(ENTRY),'original_memcpy_offset':hex(MEMCPY[0]),
         'budget':BUDGET,'stop_pc':hex(pc),'error':error,'violations':violations,
         'instruction_count':len(pcs),'unique_code_offsets':len(set(pcs)),
         'code_ranges':{'initializer':[hex(ENTRY),hex(CODE_END)],'memcpy':[hex(x) for x in MEMCPY]},
         'calls_to_original_memcpy':len(copies),'copies':copies,
         'image_write_events':len(image_writes),'stack_write_events':len(stack_writes),
         'image_write_intervals':[{'start':hex(a),'end_exclusive':hex(z)} for a,z in merged],
         'image_write_unique_bytes':sum(z-a for a,z in merged),
         'image_write_instruction_offsets':sorted({hex(p-BASE) for a,s,p in image_writes}),
         'image_write_pages':[{'page':hex(p*4096),'min':hex(z['min']),'max_exclusive':hex(z['max']),'events':z['events']} for p,z in sorted(ranges.items())],
         'image_write_min':hex(min((a-BASE for a,s,p in image_writes),default=0)),
         'image_write_max_exclusive':hex(max((a+s-BASE for a,s,p in image_writes),default=0)),
         'target_offset':hex(TARGET),'target_sha256':hashlib.sha256(target_bytes).hexdigest(),
         'source_descriptor_offset':hex(SOURCE),'source_sha256_152':hashlib.sha256(source_bytes).hexdigest(),
         'target_equals_original_source':target_bytes==source_bytes,
         'source_unchanged':bytes(uc.mem_read(BASE+SOURCE,152))==source_bytes,
         'stack_pointer_preserved':uc.reg_read(R.UC_ARM64_REG_SP)==STACK+0xf000,
         'callee_saved_preserved':all(uc.reg_read(reg)==v for reg,v in saved.items()),
         'scope':'fixed-input CPU trace; no stubs, no patches, no VM/OS/ISP/DMA or camera'}
 (ROOT/'init-trace.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:result[k] for k in ['stop_pc','error','violations','instruction_count','calls_to_original_memcpy','image_write_events','image_write_min','image_write_max_exclusive','target_equals_original_source','source_unchanged','stack_pointer_preserved','callee_saved_preserved']}))
 if error or violations or pc!=STOP or len(pcs)>=BUDGET:raise RuntimeError('bounded initializer did not complete')
if __name__=='__main__':main()
