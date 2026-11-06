"""Own bounded guest selection experiment. No native execution, camera, USB or stubs.
Runs original builder code against explicit synthetic global model slots, then
checks ONLY its stock HS4K output aliases through fixed original conversion code.
"""
from pathlib import Path
import sys,json,struct,hashlib,subprocess,plistlib
from unicorn import Uc,UcError,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_INVALID,UC_HOOK_MEM_WRITE,UC_PROT_READ,UC_PROT_WRITE,UC_PROT_EXEC
from unicorn.arm64_const import UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_LR,UC_ARM64_REG_SP,UC_ARM64_REG_PC
from audit_typed_builder import Image,OUT,ROOT,EXPECTED,INPUT
sys.path.insert(0,str(ROOT/'work/sony-firmware-20261024/stage10-mainpath/main'))
from verify_setter_conversion import invoke as setter_block
sys.path.insert(0,str(ROOT/'work/sony-firmware-20261024/stage4-windows-collab/mac-verification'))
from offline_verify import Native,Micro,SCRATCH,read32
START=0x2beae8c;STOP=0x12000000;STACK=0x10000000;BUILDER=0x11000000
FRAMEGET=0x2934d14;Q60=0x2934e54;Q24=0x2934e7c;Q120=0x2934ea4

def invoke(im,fr,q60=12,q24=17,q120=9):
 u=Uc(UC_ARCH_ARM64,UC_MODE_ARM);pages=set()
 for s in im.segments:pages.update(range(s['p_vaddr']&~4095,(s['p_vaddr']+s['p_memsz']+4095)&~4095,4096))
 assert len(pages)*4096<256*1024*1024
 runs=[]
 for a in sorted(pages):
  if runs and runs[-1][1]==a:runs[-1][1]=a+4096
  else:runs.append([a,a+4096])
 for a,z in runs:u.mem_map(a,z-a)
 for s in im.segments:u.mem_write(s['p_vaddr'],s.data())
 leaves=json.loads((OUT/'model-leaf-accessors.json').read_text())['accessors']
 leafaddrs={int(x['accessor'],16) for x in leaves}|{0x2934c9c,0x29353a4,0x293d90c}
 # All global model slots are synthetic zero unless explicitly listed here.
 values={0x2934c9c:6,0x293d90c:5,FRAMEGET:fr,Q60:q60,Q24:q24,Q120:q120}
 for a in leafaddrs:
  addr=im.leaf(a);assert addr is not None
  u.mem_write(addr,struct.pack('<I',values.get(a,0)))
 for a,z in runs:u.mem_protect(a,z-a,UC_PROT_READ|UC_PROT_EXEC)
 u.mem_map(STACK,0x20000,UC_PROT_READ|UC_PROT_WRITE);u.mem_map(BUILDER,0x1000,UC_PROT_READ|UC_PROT_WRITE)
 # Known ctor defaults only, not its other initialization/model behavior.
 for off,val in [(0x40,15),(0x44,6),(0x48,24),(0x4c,0)]:u.mem_write(BUILDER+off,struct.pack('<I',val))
 for reg,val in [(UC_ARM64_REG_X0,BUILDER),(UC_ARM64_REG_X1,0),(UC_ARM64_REG_LR,STOP),(UC_ARM64_REG_SP,STACK+0x10000)]:u.reg_write(reg,val)
 ranges=[(START,0x2beea04),(0x2bd0fb0,0x2bd0ff8),(0x2a4e5e0,0x2a4e600),(0x2a4e6b0,0x2a4e6e4),(0x2a4e794,0x2a4e7cc),(0x2a4e87c,0x2a4e880)]+[(a,a+20) for a in leafaddrs]
 state={'reason':None,'steps':0,'pcs':[],'writes':[],'synthetic_model_values':[{'getter':hex(a),'global':hex(im.leaf(a)),'value':v} for a,v in values.items()]}
 def stop(msg):state['reason']=msg;u.emu_stop()
 def code(uc,a,n,d):
  state['steps']+=1;state['pcs'].append(hex(a))
  if a==STOP:stop('returned');return
  if not any(b<=a and a+n<=z for b,z in ranges):stop('unapproved execution '+hex(a));return
  w=struct.unpack('<I',bytes(u.mem_read(a,4)))[0]
  if w&0xffe0001f in (0xd4000001,0xd4000002,0xd4000003):stop('SVC/HVC/SMC forbidden')
 def invalid(uc,access,a,n,v,d):state['reason']='unmapped/protected '+hex(a);return False
 def write(uc,access,a,n,v,d):
  if not ((STACK<=a and a+n<=STACK+0x20000) or (BUILDER<=a and a+n<=BUILDER+0x1000)):stop('write outside synthetic stack/builder');return
  if BUILDER+0x40<=a<BUILDER+0x50:state['writes'].append({'pc':hex(u.reg_read(UC_ARM64_REG_PC)),'builder_offset':hex(a-BUILDER),'size':n,'value':v})
 hooks=[u.hook_add(UC_HOOK_CODE,code),u.hook_add(UC_HOOK_MEM_INVALID,invalid),u.hook_add(UC_HOOK_MEM_WRITE,write)]
 try:u.emu_start(START,STOP,timeout=100000,count=2000)
 except UcError as e:
  if state['reason'] is None:state['reason']='emulator error '+str(e)
 if state['reason'] is None:state['reason']='returned' if u.reg_read(UC_ARM64_REG_PC)==STOP else 'budget exhausted'
 for h in hooks:u.hook_del(h)
 state.update(start_pc=hex(START),stop_pc=hex(u.reg_read(UC_ARM64_REG_PC)),builder_frame_format_quality_color=list(struct.unpack('<IIII',bytes(u.mem_read(BUILDER+0x40,16)))))
 return state

def main():
 assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
 im=Image();mpr=Native('libmpr.so');cases=[];rational=[];qualities=[]
 for fr in range(7):
  r=invoke(im,fr);r['case']='HS4K typed frame '+str(fr)
  if fr in (2,3):assert r['reason']=='unapproved execution 0x2f6fe3c'
  else:
   assert r['reason']=='returned';f,fmt,q,c=r['builder_frame_format_quality_color']
   r['setter_conversion']=setter_block(im,fmt,q,f,c,False);assert r['setter_conversion']['reason']=='conversion block complete'
  cases.append(r)
 for fr,kwargs in [(0,{'q60':2}),(4,{'q24':2})]:
  r=invoke(im,fr,**kwargs);r['case']='HS4K invalid typed quality2, frame '+str(fr)
  assert r['reason']=='unapproved execution 0x2f6fe3c';cases.append(r)
 for model,mprfr in [(20,7),(18,5),(10,0),(22,9),(21,8),(13,2),(15,3)]:
  s=setter_block(im,6,13,model,0,False);assert s['reason']=='conversion block complete' and s['output_vpc_quality_frame'][2]==mprfr
  m=Micro(mpr,[(0x2c0de8,0x2c0e98)]);r=m.run(0x2c0de8,[mprfr,SCRATCH,SCRATCH+4]);assert r['reason']=='returned'
  rational.append({'model_frame':model,'mpr_frame':mprfr,'numerator':read32(m.uc,SCRATCH),'denominator':read32(m.uc,SCRATCH+4),'setter':s,'mpr_function':r})
 for q in [18,16,13,10,7,8,5,22]:
  s=setter_block(im,6,q,20,0,False);assert s['reason']=='conversion block complete';vq=s['output_vpc_quality_frame'][1]
  m=Micro(mpr,[(0x2c0ce0,0x2c0d04)]);r=m.run(0x2c0ce0,[vq]);assert r['reason']=='returned'
  qualities.append({'model_quality':q,'mpr_vquality':vq,'GetVideoBitrate_raw':r['return_u32'],'setter':s,'mpr_function':r})
 assert hashlib.sha256(INPUT.read_bytes()).hexdigest()==EXPECTED
 report={'source_sha256':EXPECTED,'libmpr_sha256':hashlib.sha256(mpr.blob).hexdigest(),'scope':'original typed-builder selection with explicit synthetic global model cells; output alias conversion only; no whole app or camera execution','bounded_guest_function_emulation':True,'stubs':[],'source_modified':False,'native_execution':False,'USB_GUI_camera_devices':False,'persistent_camera_write':False,'constructor_executed':False,'constructor_defaults_supplied':{'builder+0x40_frame':15,'builder+0x44_format':6,'builder+0x48_quality':24,'builder+0x4c_color':0},'all_unlisted_model_slots':'synthetic zero; not a camera snapshot','instruction_limit_each':2000,'builder_timeout_us_each':100000,'cases':cases,'model_frame_to_mpr_rational':rational,'model_quality_to_mpr_bitrate':qualities,'bitrate_raw_unit_note':'preserve helper return without relabeling as bps; target VQuality6 returns16000 in prior verified chain','status':'PASS'}
 (OUT/'typed-selection-results.json').write_text(json.dumps(report,indent=2))
 print('PASS nine builder cases; seven frame alias checks; eight quality aliases')
 for r in cases:print(r['case'],r['reason'],r['builder_frame_format_quality_color'])
 print('rational',[(r['model_frame'],r['mpr_frame'],r['numerator'],r['denominator']) for r in rational])
 print('quality',[(r['model_quality'],r['mpr_vquality'],r['GetVideoBitrate_raw']) for r in qualities])
if __name__=='__main__':main()
