#!/usr/bin/env python3
"""FX6 original initializer -> DMA-list builder in bounded CPU RAM; no submit."""
import hashlib,json,pathlib,struct
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE,UC_HOOK_MEM_READ
from unicorn import arm64_const as R
from trace_init import AV,PIN,BASE,ENTRY,CODE_END,MEMCPY,TARGET,SOURCE,STACK,STOP

ROOT=pathlib.Path(__file__).resolve().parent
DMA_ENTRY=0x2a7978
DMA_END=0x2a7ba4
LOOK22=0xaa2ca0
COUNT=70
GUEST=BASE+0xc60000
ARG=GUEST+0x1000
OUTPUT=GUEST+0x2000
PROVIDERS=GUEST+0x8000
STUB=0x61000000
VIRT=0xffffffc000000000
PHYS=0x400000000

def main():
 b=AV.read_bytes();assert hashlib.sha256(b).hexdigest()==PIN
 look=json.loads((ROOT.parent/'descriptor-diff.json').read_text())['looks'][21]
 assert look['descriptor_array_offset']==hex(LOOK22) and look['descriptor_count']==COUNT
 prior=json.loads((ROOT/'init-trace.json').read_text());assert prior['target_equals_original_source']
 u=Uc(UC_ARCH_ARM64,UC_MODE_ARM)
 u.mem_map(BASE,(len(b)+4095)&~4095);u.mem_write(BASE,b)
 u.mem_map(STACK,0x10000);u.mem_write(STACK,b'\xa7'*0x10000)
 u.mem_map(STOP,0x1000);u.mem_map(GUEST,0x10000);u.mem_map(STUB,0x1000)
 u.reg_write(R.UC_ARM64_REG_SP,STACK+0xf000);u.reg_write(R.UC_ARM64_REG_LR,STOP)
 state={'phase':'init'};pcs=[];init_count=0;violations=[];reads=[];writes=[];callback=[];flush=[]
 allowed_dma=[(DMA_ENTRY,DMA_END),(0x297460,0x297474),(0x2f330,0x2f344),(0x2f2e0,0x2f2f4),(0x2f5d0,0x2f5e4)]
 def code(uc,pc,size,_):
  nonlocal init_count
  if pc==STOP:uc.emu_stop();return
  if state['phase']=='dma' and pc in (STUB,STUB+0x100):
   x0=uc.reg_read(R.UC_ARM64_REG_X0)
   if pc==STUB:
    flush.append({'address':hex(x0),'length':uc.reg_read(R.UC_ARM64_REG_X1)})
   else:
    assert VIRT<=x0<VIRT+0x100000000
    physical=PHYS+x0-VIRT
    callback.append({'virtual':hex(x0),'declared_physical':hex(physical)})
    uc.reg_write(R.UC_ARM64_REG_X0,physical)
   uc.reg_write(R.UC_ARM64_REG_PC,uc.reg_read(R.UC_ARM64_REG_LR));return
  off=pc-BASE
  if state['phase']=='init':
   if not(ENTRY<=off<CODE_END or MEMCPY[0]<=off<MEMCPY[1]):
    violations.append({'phase':'init','kind':'outside_code','pc':hex(pc)});uc.emu_stop();return
   init_count+=1
  else:
   if not any(lo<=off<hi for lo,hi in allowed_dma):
    violations.append({'phase':'dma','kind':'outside_code','pc':hex(pc)});uc.emu_stop();return
   pcs.append(off)
 def memwrite(uc,access,addr,size,value,_):
  if state['phase']=='init':
   ok=(BASE+0xa88bd0<=addr and addr+size<=BASE+0xab4020) or STACK<=addr and addr+size<=STACK+0x10000
  else:
   ok=(OUTPUT<=addr and addr+size<=OUTPUT+COUNT*16) or (ARG<=addr and addr+size<=ARG+16) or STACK<=addr and addr+size<=STACK+0x10000
  if not ok:
   violations.append({'phase':state['phase'],'kind':'outside_write','address':hex(addr),'size':size,'pc':hex(uc.reg_read(R.UC_ARM64_REG_PC))})
   uc.emu_stop();return
  if state['phase']=='dma':writes.append({'address':hex(addr),'size':size,'pc':hex(uc.reg_read(R.UC_ARM64_REG_PC))})
 def memread(uc,access,addr,size,value,_):
  if state['phase']!='dma':return
  if addr<TARGET+BASE+152 and addr+size>BASE+TARGET:
   reads.append({'pc_offset':hex(uc.reg_read(R.UC_ARM64_REG_PC)-BASE),'address_offset':hex(addr-BASE),'size':size})
 u.hook_add(UC_HOOK_CODE,code)
 u.hook_add(UC_HOOK_MEM_WRITE,memwrite)
 u.hook_add(UC_HOOK_MEM_READ,memread)
 u.emu_start(BASE+ENTRY,STOP+4,count=500000)
 assert u.reg_read(R.UC_ARM64_REG_PC)==STOP and init_count==55395 and not violations
 assert bytes(u.mem_read(BASE+TARGET,152))==b[SOURCE:SOURCE+152]
 state['phase']='dma'
 patches=[]
 original_provider=bytes(u.mem_read(BASE+0x20,8))
 u.mem_write(BASE+0x20,struct.pack('<Q',PROVIDERS))
 patches.append({'kind':'provider_table_pointer','address_offset':'0x20','before_hex':original_provider.hex(),'after_value':hex(PROVIDERS)})
 u.mem_write(PROVIDERS+0x610,struct.pack('<Q',STUB))
 u.mem_write(PROVIDERS+0x630,struct.pack('<Q',STUB+0x100))
 patches.append({'kind':'provider_callbacks','table':hex(PROVIDERS),'cache_flush_slot':hex(PROVIDERS+0x610),'cache_flush_stub':hex(STUB),
                 'virtual_to_physical_slot':hex(PROVIDERS+0x630),'virtual_to_physical_stub':hex(STUB+0x100)})
 u.mem_write(ARG,struct.pack('<IIQ',0,COUNT,BASE+LOOK22))
 patches.append({'kind':'DMA_builder_input_fixture','address':hex(ARG),'ip':0,'count':COUNT,'first_descriptor':hex(BASE+LOOK22)})
 u.mem_write(OUTPUT-16,b'\x5a'*(COUNT*16+32))
 patches.append({'kind':'output_canary_fixture','address':hex(OUTPUT-16),'bytes':COUNT*16+32,'pattern':'5a'})
 u.reg_write(R.UC_ARM64_REG_X0,ARG);u.reg_write(R.UC_ARM64_REG_X1,OUTPUT);u.reg_write(R.UC_ARM64_REG_LR,STOP)
 error=None
 try:u.emu_start(BASE+DMA_ENTRY,STOP+4,count=50000)
 except Exception as ex:error=repr(ex)
 pc=u.reg_read(R.UC_ARM64_REG_PC)
 output=bytes(u.mem_read(OUTPUT-16,COUNT*16+32))
 rows=[list(struct.unpack_from('<4I',output,16+i*16)) for i in range(COUNT)]
 selected=rows[63]
 src_ptr,reg,n=struct.unpack_from('<QQI',bytes(u.mem_read(BASE+TARGET,20)))
 register_bases=[]
 for index,row in enumerate(rows):
  ptr_i,reg_i,count_i=struct.unpack_from('<QQI',bytes(u.mem_read(BASE+LOOK22+index*152,20)))
  expected_source=(PHYS+ptr_i-VIRT)&0xffffffff
  expected_next=0 if index==COUNT-1 else (PHYS+OUTPUT+(index+1)*16-VIRT)&0xfffffffe
  expected_control=0x0e489000|(count_i&0xfff)|(0x80000000 if index==COUNT-1 else 0)
  assert row[0]==expected_source and row[2]==expected_next and row[3]==expected_control,(index,row)
  register_bases.append((row[1]-reg_i)&0xffffffff)
 assert len(set(register_bases))==1 and register_bases[0]==0xf3019000
 assert selected==[(PHYS+src_ptr-VIRT)&0xffffffff,(register_bases[0]+reg)&0xffffffff,
                   (PHYS+OUTPUT+64*16-VIRT)&0xfffffffe,0x0e489000|(n&0xfff)]
 result={'source_sha256':PIN,'initializer_entry_offset':hex(ENTRY),'initializer_instructions':init_count,
         'dma_entry_offset':hex(DMA_ENTRY),'dma_instruction_count':len(pcs),'dma_stop_pc':hex(pc),'error':error,
         'violations':violations,'stubs_and_guest_patches':patches,
         'stub_semantics':{'cache_flush':'record x0 address and x1 length; return to LR, no cache operation',
                           'virtual_to_physical':'declared PHYS + virtual - VIRT; return to LR, no OS mapping proof'},
         'callback_count':len(callback),'flush_count':len(flush),'callbacks':callback,'flushes':flush,
         'target_slot_read_events':reads,'target_slot_original_descriptor':{'pointer':hex(src_ptr),'register_offset':hex(reg),'word_count':n},
         'all_70_rows_match_original_descriptor_fields':True,'register_base_low32':hex(register_bases[0]),
         'output_layout':'70 linked rows, each <I source_physical_low32, I register_destination_low32, I next_physical_low32, I control>; last has null next and end bit',
         'output_canaries_preserved':output[:16]==output[-16:]==b'\x5a'*16,
         'input_after':bytes(u.mem_read(ARG,16)).hex(),'dma_rows':rows,'slot63_dma_row':selected,
         'slot63_output_offset':hex(OUTPUT+63*16),'write_event_count':len(writes),
         'hardware_submitted':False,
         'scope':'original FX6 CPU DMA-list construction only; provider stubs declared, no cache operation, OS mapping, DMA submission, DSP or camera'}
 (ROOT/'dma-trace.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:result[k] for k in ['dma_stop_pc','error','violations','dma_instruction_count','callback_count','flush_count','target_slot_read_events','slot63_dma_row','output_canaries_preserved']}))
 if error or violations or pc!=STOP:raise RuntimeError('bounded DMA-list construction did not complete')
 assert reads and len(rows)==COUNT and result['output_canaries_preserved']
if __name__=='__main__':main()
