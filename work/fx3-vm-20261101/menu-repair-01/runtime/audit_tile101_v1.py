from pathlib import Path
import json,re,runpy,struct,hashlib,plistlib,subprocess
from unicorn import arm64_const as ar
R=Path(__file__).resolve().parent;assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B';provider=R.parents[1]/'lead-claude/audits/gpe-blend-p3/audit_gpe_blend.py';assert hashlib.sha256(provider.read_bytes()).hexdigest()=='88effc3d0cf05c7027d30e1b7a505e88cad96ba001e55815c9300a422dff0bc1';m=runpy.run_path(str(provider),run_name='tile101_original_provider');image=m['Image']('libgpe.so');Base=m['Replay'];run=R/'runs/ap101r3emptyclip600-49610a67';lines=(run/'serial.log').read_text(errors='replace').split('\n');line,ma=next((i+1,x) for i,l in enumerate(lines) if (x:=re.search(r'FX3_GPE_RAW_PARAMS op=BitBlit seq=712 read=1 len=144 raw_hex=([0-9a-f]{288})',l)));raw=bytes.fromhex(ma[1])
class Replay(Base):
 def hook(self,uc,address,size,arg):
  self.trace.append(address);name=self.image.plt.get(address,'')
  if 'StretchRotateBlit' in name:uc.reg_write(ar.UC_ARM64_REG_PC,0xc878);return
  if name in ('cslMakeZoomSprite','cslMakeZoomRotateSprite'):
   self.other.append({'kind':name,'caller_va':hex(self.reg(30)-4),'dst_x':self.reg(1)&0xffffffff,'dst_y':self.reg(2)&0xffffffff,'src_struct40':bytes(uc.mem_read(self.reg(0),40)).hex(),'scale_float':[struct.unpack('<f',struct.pack('<I',uc.reg_read(r)&0xffffffff))[0] for r in (ar.UC_ARM64_REG_S0,ar.UC_ARM64_REG_S1)]});self.ret();return
  if address==0xaf30:self.submissions.append({'call_va':hex(self.reg(30)-4),'accepted_transport_mock':0});self.ret(0);return
  super().hook(uc,address,size,arg)
 def execute(self,p):
  self.trace=[];self.submissions=[];v=self.run(0xcf2c,p);v['submission_calls']=self.submissions;v['source_mask_registers']=[x for x in v['register_writes'] if int(x['reg'],16) in [0x460,0x461,0x462,0x463,0x464,0x465,0x466,0x467,0x470,0x471,0x472,0x473,0x474]];v['source_sprites']=[x for x in v['other_descriptors'] if x['kind']=='cslMakeSimpleSprite'];return v
r=Replay(image);cases=[]
for label,edits in [('native712',{}),('source_origin0',{64:0,68:0}),('source_origin17_1',{64:17,68:1}),('dest_equal_source',{16:32,20:2}),('repeat_both_axes',{16:458,20:5,36:5}),('source_width16',{72:16}),('source_width31_nonpow2',{72:31}),('source_height3_nonpow2',{76:3}),('scale2',{96:0x40000000})]:
 p=bytearray(raw)
 for off,n in edits.items():struct.pack_into('<I',p,off,n)
 q=r.execute(bytes(p));assert q['status']=='returned' and q['return_x0']==0 and len(q['submission_calls'])==1,(label,q);cases.append({'label':label,'raw144':p.hex(),'original_descriptor_path':q})
native=cases[0]['original_descriptor_path'];assert native['route']==['0xbbcc'];out={'scope':'Pinned original descriptor generation only; csl/hardware are hooked, no pixel oracle. Candidate repeat_mask_v1 interpretation kept explicit.','authority':'msg_a13ef691c862','libgpe_original':{'path':str(image.path),'sha256':image.sha},'source_run':str(run),'serial_LF_line':line,'native144':raw.hex(),'vectors':cases,'original_blocks':{'BitBlit_dispatch':image.block(0xcf2c,0xd148),'general_blit_source_and_masks':image.block(0xbc90,0xc150)},'candidate_sampling':'P74=1 folds original src x/y into texture physical base, texture coords zero; dimensions differing with power-of-two source program size-1 mask. Equivalent candidate samples from folded base with dest-relative coords AND source-size-1. Same-axis dimensions program1fff but no coordinate exceeds that axis source size. Nonpower source axes adjust sprite size and are excluded.','native_hardware_repeat_pixel_evidence':False};p=R/'ap101-P74-original-proof-v1.json';assert not p.exists();p.write_text(json.dumps(out,indent=2)+'\n');print(p)
for x in cases:
 q=x['original_descriptor_path'];print(x['label'],q['route'],q['source_mask_registers'],q['source_sprites'])
