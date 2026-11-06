#!/usr/bin/env python3
"""Guarded positive/negative CPU controls for original FX6 initializer."""
import hashlib,json,pathlib,struct
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn import arm64_const as R
from trace_init import AV,PIN,BASE,ENTRY,CODE_END,MEMCPY,TARGET,SOURCE,STACK,STOP

ROOT=pathlib.Path(__file__).resolve().parent
LOW=0xa88bd0
HIGH=0xab4020
CANARIES=[LOW-16,HIGH]
PATTERN=b'\xc7'*16

def run(image,mutate=False,budget=500000):
 u=Uc(UC_ARCH_ARM64,UC_MODE_ARM)
 u.mem_map(BASE,(len(image)+4095)&~4095);u.mem_write(BASE,image)
 u.mem_map(STACK,0x10000);u.mem_map(STOP,0x1000)
 u.mem_write(STACK,b'\xa7'*0x10000)
 patches=[]
 for off in CANARIES:
  u.mem_write(BASE+off,PATTERN)
  patches.append({'kind':'guard','offset':hex(off),'bytes_hex':PATTERN.hex()})
 if mutate:
  assert image[SOURCE+20:SOURCE+21]==b'M'
  u.mem_write(BASE+SOURCE+20,b'N')
  patches.append({'kind':'negative_source_mutation','offset':hex(SOURCE+20),'before':'4d','after':'4e'})
 u.reg_write(R.UC_ARM64_REG_SP,STACK+0xf000)
 u.reg_write(R.UC_ARM64_REG_LR,STOP)
 violations=[];pcs=[];writes=[];calls=[]
 def code(uc,pc,size,_):
  if pc==STOP:uc.emu_stop();return
  off=pc-BASE
  if not (ENTRY<=off<CODE_END or MEMCPY[0]<=off<MEMCPY[1]):
   violations.append({'kind':'outside_code','pc':hex(pc)});uc.emu_stop();return
  pcs.append(off)
  if off==MEMCPY[0]:
   dst,src,n=[uc.reg_read(x) for x in (R.UC_ARM64_REG_X0,R.UC_ARM64_REG_X1,R.UC_ARM64_REG_X2)]
   calls.append((dst-BASE,src-BASE,n))
 def write(uc,access,addr,size,value,_):
  if not (BASE+LOW<=addr and addr+size<=BASE+HIGH or STACK<=addr and addr+size<=STACK+0x10000):
   violations.append({'kind':'outside_measured_write_domain','address':hex(addr),'size':size,'pc':hex(uc.reg_read(R.UC_ARM64_REG_PC))})
   uc.emu_stop();return
  writes.append((addr,size))
 u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
 error=None
 try:u.emu_start(BASE+ENTRY,STOP+4,count=budget)
 except Exception as ex:error=repr(ex)
 returned=u.reg_read(R.UC_ARM64_REG_PC)==STOP
 guards=[bytes(u.mem_read(BASE+off,16))==PATTERN for off in CANARIES]
 target=bytes(u.mem_read(BASE+TARGET,152))
 guest_source=bytes(u.mem_read(BASE+SOURCE,152))
 return {'patches_guest_ram_only':patches,'stubs':[],'budget':budget,'returned_to_stop':returned,
         'stop_pc':hex(u.reg_read(R.UC_ARM64_REG_PC)),'error':error,'violations':violations,
         'instruction_count':len(pcs),'original_memcpy_calls':len(calls),
         'target_copy_calls':sum(x==(TARGET,SOURCE,152) for x in calls),
         'image_write_events':sum(BASE<=a<BASE+len(image) for a,s in writes),
         'canary_preserved':guards,'stack_pointer_preserved':u.reg_read(R.UC_ARM64_REG_SP)==STACK+0xf000,
         'target_equals_guest_source':target==guest_source,
         'target_equals_unpatched_original_source':target==image[SOURCE:SOURCE+152],
         'target_sha256':hashlib.sha256(target).hexdigest()}

def main():
 image=AV.read_bytes();assert hashlib.sha256(image).hexdigest()==PIN
 trace=json.loads((ROOT/'init-trace.json').read_text())
 assert trace['image_write_min']==hex(LOW) and trace['image_write_max_exclusive']==hex(HIGH)
 assert image[CANARIES[0]:CANARIES[0]+16]!=PATTERN
 assert image[CANARIES[1]:CANARIES[1]+16]!=PATTERN
 positive=run(image)
 assert positive['returned_to_stop'] and positive['error'] is None and not positive['violations']
 assert positive['canary_preserved']==[True,True] and positive['target_equals_unpatched_original_source']
 assert positive['target_copy_calls']==1 and positive['original_memcpy_calls']==1166
 mutation=run(image,mutate=True)
 assert mutation['returned_to_stop'] and mutation['error'] is None and not mutation['violations']
 assert mutation['canary_preserved']==[True,True] and mutation['target_equals_guest_source']
 assert not mutation['target_equals_unpatched_original_source'] and mutation['target_copy_calls']==1
 budget=run(image,budget=1000)
 assert not budget['returned_to_stop'] and budget['instruction_count']==1000
 assert budget['error'] is None and not budget['violations'] and budget['canary_preserved']==[True,True]
 result={'source_sha256':PIN,'allowed_image_write_interval':[hex(LOW),hex(HIGH)],
         'original_code_ranges':[[hex(ENTRY),hex(CODE_END)],[hex(x) for x in MEMCPY]],
         'positive':positive,'negative_source_mutation':mutation,'negative_budget_exhaustion':budget,
         'scope':'all execution in Unicorn CPU RAM; guest canary/source mutations listed, no on-disk patch, no stub, no hardware/VM'}
 (ROOT/'controls.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'positive_returned':positive['returned_to_stop'],'positive_canaries':positive['canary_preserved'],
                   'negative_source_changed_target':not mutation['target_equals_unpatched_original_source'],
                   'negative_budget_rejected':not budget['returned_to_stop']}))
if __name__=='__main__':main()
