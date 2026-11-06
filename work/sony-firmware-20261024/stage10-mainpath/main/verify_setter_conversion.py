"""Bounded original FX3 main-setter conversion BLOCK, not whole setter/Start.
No device/host syscalls/MMIO, source modifications or payload output. One optional
Unicorn-memory MOV constant override is diagnostic only and deliberately broad.
"""
from pathlib import Path
import struct,json,hashlib,subprocess,plistlib
from unicorn import Uc,UcError,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_INVALID,UC_HOOK_MEM_WRITE,UC_PROT_READ,UC_PROT_WRITE,UC_PROT_EXEC
from unicorn.arm64_const import UC_ARM64_REG_X0,UC_ARM64_REG_X19,UC_ARM64_REG_X24,UC_ARM64_REG_X29,UC_ARM64_REG_SP,UC_ARM64_REG_PC
from audit_main_path import Image,OUT,EXPECTED,INPUT
START,END=0x2e6ea58,0x2e6f040
RANGES=[(START,END),(0x2e6f45c,0x2e6f494)]
STACK=0x10000000;INPUT_BASE=0x11000000;FRAME=STACK+0x10000
PATCH=0x2e6ed04

def invoke(im,fmt,quality,frame,color,override):
 u=Uc(UC_ARCH_ARM64,UC_MODE_ARM)
 pages=set()
 for s in im.segments: pages.update(range(s['p_vaddr']&~4095,(s['p_vaddr']+s['p_memsz']+4095)&~4095,4096))
 assert len(pages)*4096<256*1024*1024
 runs=[]
 for a in sorted(pages):
  if runs and runs[-1][1]==a:runs[-1][1]=a+4096
  else:runs.append([a,a+4096])
 for a,z in runs:u.mem_map(a,z-a)
 for s in im.segments:u.mem_write(s['p_vaddr'],s.data())
 assert im.read(PATCH,4)==bytes.fromhex('a0008052')
 if override:u.mem_write(PATCH,bytes.fromhex('c0008052'))
 for a,z in runs:u.mem_protect(a,z-a,UC_PROT_READ|UC_PROT_EXEC)
 u.mem_map(STACK,0x20000,UC_PROT_READ|UC_PROT_WRITE)
 u.mem_map(INPUT_BASE,0x1000,UC_PROT_READ|UC_PROT_WRITE)
 for off,val in [(0x10,frame),(0x14,fmt),(0x18,quality),(0x1c,color)]:u.mem_write(INPUT_BASE+off,struct.pack('<I',val))
 for reg,val in [(UC_ARM64_REG_X24,INPUT_BASE),(UC_ARM64_REG_X29,FRAME),(UC_ARM64_REG_X19,FRAME+0x310),(UC_ARM64_REG_SP,STACK+0x8000)]:u.reg_write(reg,val)
 state={'reason':None,'steps':0,'stores':[],'pcs':[]}
 def stop(reason):state['reason']=reason;u.emu_stop()
 def code(uc,a,n,d):
  state['steps']+=1;state['pcs'].append(hex(a))
  if a==END:stop('conversion block complete');return
  if not any(b<=a and a+n<=z for b,z in RANGES):stop('unapproved execution '+hex(a));return
  w=struct.unpack('<I',bytes(u.mem_read(a,4)))[0]
  if w&0xffe0001f in (0xd4000001,0xd4000002,0xd4000003):stop('SVC/HVC/SMC forbidden')
 def invalid(uc,access,a,n,v,d):state['reason']='unmapped/protected '+hex(a);return False
 def write(uc,access,a,n,v,d):
  if not (STACK<=a and a+n<=STACK+0x20000):stop('guest write outside synthetic stack');return
  if FRAME+0x480<=a<FRAME+0x48c:state['stores'].append({'pc':hex(u.reg_read(UC_ARM64_REG_PC)),'movieRecParam_offset':hex(a-(FRAME+0x310)),'value':v,'size':n})
 hooks=[u.hook_add(UC_HOOK_CODE,code),u.hook_add(UC_HOOK_MEM_INVALID,invalid),u.hook_add(UC_HOOK_MEM_WRITE,write)]
 try:u.emu_start(START,END,timeout=100000,count=2000)
 except UcError as e:
  if state['reason'] is None:state['reason']='emulator error '+str(e)
 if state['reason'] is None:state['reason']='conversion block complete' if u.reg_read(UC_ARM64_REG_PC)==END else 'budget exhausted'
 for h in hooks:u.hook_del(h)
 state['start_pc']=hex(START);state['stop_pc']=hex(u.reg_read(UC_ARM64_REG_PC))
 state['output_vpc_quality_frame']=list(struct.unpack('<III',bytes(u.mem_read(FRAME+0x480,12))))
 state.update(input={'format':fmt,'quality':quality,'frame':frame,'color':color},diagnostic_memory_override=override)
 return state

def main():
 v=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
 assert v['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
 im=Image();cases=[]
 controls=[('HS420 target tuple',6,2,15,0,[5,6,3]),('HD AVC control',8,2,15,0,[1,6,3]),('UHD AVC control',7,13,15,0,[0,12,3]),('HS422 control',6,2,15,1,[7,6,3]),('HS420 59.94 100M',6,13,13,0,[5,12,2])]
 for label,f,q,fr,c,expected in controls:
  for override in [False,True]:
   x=invoke(im,f,q,fr,c,override);x['label']=label
   want=[6 if override and f==6 and c==0 else expected[0],*expected[1:]]
   assert x['reason']=='conversion block complete',(label,x)
   assert x['output_vpc_quality_frame']==want,(label,x,want)
   x['expected']=want;cases.append(x)
 for label,f,q,fr,c in [('bad format',13,2,15,0),('bad quality',6,0,15,0),('bad frame',6,2,0,0),('bad color',6,2,15,2)]:
  x=invoke(im,f,q,fr,c,False);x['label']=label
  assert x['reason'].startswith('unapproved execution'),x
  cases.append(x)
 assert hashlib.sha256(INPUT.read_bytes()).hexdigest()==EXPECTED
 report={'source_sha256':EXPECTED,'scope':'real main-setter conversion block only; model builder, complete setter and MPR call not executed','entry':hex(START),'stop':hex(END),'allowed_ranges':[[hex(a),hex(z)] for a,z in RANGES],'stubs':[],'synthetic_context':{'x24':'input structure at 0x11000000','x29':'synthetic frame at 0x10010000','x19':'movieRecParam base x29+0x310','input_offsets':{'frame':'0x10','format':'0x14','quality':'0x18','color':'0x1c'},'output_offsets':{'VPC':'0x170','VQuality':'0x174','Frame':'0x178'},'all_other_synthetic_bytes':'zero; not a real model snapshot'},'instruction_limit':2000,'timeout_us':100000,'no_syscalls_devices_network_MMIO':True,'source_unchanged':True,'diagnostic_override':{'va':hex(PATCH),'original':'a0008052','memory_only':'c0008052','meaning':'MOV W0,#5 -> MOV W0,#6; changes ALL HS420 format6 inputs, not a usable patch or coherent menu/model solution'},'cases':cases,'assertions':14,'status':'PASS'}
 (OUT/'setter-conversion-results.json').write_text(json.dumps(report,indent=2))
 print('PASS',len(cases),'cases; source unchanged; no full setter or hardware')
 for x in cases:print(x['label'],x['diagnostic_memory_override'],x['reason'],x['output_vpc_quality_frame'])
if __name__=='__main__':main()
