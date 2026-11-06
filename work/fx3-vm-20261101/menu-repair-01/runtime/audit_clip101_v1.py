from pathlib import Path
import json,re,runpy,struct,hashlib,plistlib,subprocess
from unicorn import arm64_const as ar
R=Path(__file__).resolve().parent;assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B';provider=R.parents[1]/'lead-claude/audits/gpe-blend-p3/audit_gpe_blend.py';assert hashlib.sha256(provider.read_bytes()).hexdigest()=='88effc3d0cf05c7027d30e1b7a505e88cad96ba001e55815c9300a422dff0bc1';m=runpy.run_path(str(provider),run_name='clip101_readonly_provider');image=m['Image']('libgpe.so');Base=m['Replay'];run=R/'runs/ap101r2nativefile600-425d4d97';lines=(run/'serial.log').read_text(errors='replace').split('\n');matches=[(i+1,re.search(r'FX3_GPE_RAW_PARAMS op=BitBlit seq=712 read=1 len=144 raw_hex=([0-9a-f]{288})',l)) for i,l in enumerate(lines)];line,match=next((i,x) for i,x in matches if x);raw=bytes.fromhex(match[1])
class Replay(Base):
 def hook(self,uc,address,size,arg):
  self.trace.append(address)
  name=self.image.plt.get(address,'')
  if 'StretchRotateBlit' in name:uc.reg_write(ar.UC_ARM64_REG_PC,0xc878);return
  if name in ('cslMakeZoomSprite','cslMakeZoomRotateSprite'):
   self.other.append({'kind':name,'caller_va':hex(self.reg(30)-4),'dst_x':self.reg(1)&0xffffffff,'dst_y':self.reg(2)&0xffffffff,'src_struct40':bytes(uc.mem_read(self.reg(0),40)).hex(),'scale_float':[struct.unpack('<f',struct.pack('<I',uc.reg_read(r)&0xffffffff))[0] for r in (ar.UC_ARM64_REG_S0,ar.UC_ARM64_REG_S1)]});self.ret();return
  if address==0xaf30:
   self.submissions.append({'call_va':hex(self.reg(30)-4),'args_x0_x7':[hex(self.reg(i)) for i in range(8)],'scope':'submission reached; no hardware call; accepted transport simulated0'});self.ret(0);return
  super().hook(uc,address,size,arg)
 def execute(self,p):
  self.trace=[];self.submissions=[];v=self.run(0xcf2c,p);v['submission_calls']=self.submissions;v['executed_original_VAs']=[hex(x) for x in sorted(set(self.trace)) if 0x9000<=x<=0xd148];return v
r=Replay(image)
def set32(p,o,n):struct.pack_into('<I',p,o,n&0xffffffff)
def geometry(p):
 vals={n:struct.unpack_from('<I',p,o)[0] for n,o in [('dx',8),('dy',12),('dw',16),('dh',20),('cx',24),('cy',28),('cw',32),('ch',36),('ax',40),('ay',44),('sx',64),('sy',68),('sw',72),('sh',76),('asx',80),('asy',84)]};dx=vals['dx']+vals['ax']-vals['asx'];dy=vals['dy']+vals['ay']-vals['asy'];l=max(dx,vals['cx']);t=max(dy,vals['cy']);right=min(dx+vals['dw'],vals['cx']+vals['cw']);bottom=min(dy+vals['dh'],vals['cy']+vals['ch']);return {'raw_fields':vals,'adjusted_destination':[dx,dy,vals['dw'],vals['dh']],'intersection':[l,t,right,bottom],'empty':right<=l or bottom<=t}
cases=[]
for label,edits in [('seq712_native',{}),('same_size_empty',{16:6,20:32}),('inside_one_row',{28:432,36:1}),('touching_below_empty',{28:474,36:1}),('one_row_at_bottom',{28:473,36:1}),('touching_right_empty',{24:597,32:1,28:432,36:1}),('one_column_at_right',{24:596,32:1,28:432,36:1}),('outside_left_empty',{24:500,32:1,28:432,36:1}),('one_column_at_left',{24:501,32:1,28:432,36:1})]:
 p=bytearray(raw)
 for o,n in edits.items():set32(p,o,n)
 q=r.execute(bytes(p));assert q['status']=='returned' and q['return_x0']==0 and len(q['submission_calls'])==1,(label,q);cases.append({'label':label,'raw144':p.hex(),'geometry':geometry(p),'original_descriptor_path':q})
# Prove original error paths remain meaningful in this harness.
p=bytearray(raw);p[112]=2;bad=r.execute(bytes(p));assert bad['status']=='returned' and bad['return_x0']!=0 and not bad['submission_calls'],bad
blocks={n:image.block(a,z) for n,a,z in [('BitBlit_dispatch',0xcf2c,0xd148),('general_primitive',0xbbcc,0xc154),('StretchRotateBlit',0xc878,0xcf2c)]}
out={'scope':'Static pinned original bytes plus bounded isolated original AArch64 descriptor planning via Unicorn. External csl/transport are intercepted, no hardware or pixel execution.','authority':'msg_b4d68a13192e','libgpe_original':{'path':str(image.path),'sha256':image.sha},'provider_sha256':hashlib.sha256(provider.read_bytes()).hexdigest(),'source_run':str(run),'serial_LF_line_native144':line,'native_geometry':geometry(raw),'vectors':cases,'selector2_negative_control':bad,'original_blocks':blocks,'conclusion':'Both original stretched and same-size paths submit even when software dst/clip intersection is empty; no local bounds error or empty-intersection branch. With accepted mocked transport, native entry returns0. Descriptor generation acceptance is proven, hardware no-write semantics is the approved bounded software clip model, not hardware execution evidence.'}
p=R/'ap101-empty-clip-original-proof-v1.json';assert not p.exists();p.write_text(json.dumps(out,indent=2)+'\n');print('AP101_ORIGINAL_CLIP_PASS',len(cases),'original vectors submitted/returned0; selector2 rejected; no hardware pixels executed');print(p)
for q in cases[:2]:print(q['label'],q['original_descriptor_path']['route'],q['geometry']['intersection'],q['original_descriptor_path']['register_writes'][-4:])
