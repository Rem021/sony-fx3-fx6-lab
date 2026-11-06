from pathlib import Path
import json,hashlib,subprocess
R=Path(__file__).resolve().parent;H=R/'helpers';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
s=(H/'fx3-gpe-observe-v22-tile101.c').read_text();s=s.replace('static unsigned long seen;','static unsigned long seen;static U last_command102;\nU fx3_gpe_observation_sequence102(void){return __atomic_load_n(&last_command102,__ATOMIC_ACQUIRE);}')
s=s.replace(' struct gpe_plan checked_plan;unsigned valid_plan=', ' __atomic_store_n(&last_command102,seq,__ATOMIC_RELEASE);\n struct gpe_plan checked_plan;unsigned valid_plan=',1)
s=s.replace('if(n<=200||approx||result||offscreen_observation(op,p,readable)){','if(1){',1)
s=s.replace('static int command(unsigned op,', '#include "fx3-texture-observe102-v1.h"\nstatic int command(unsigned op,',1)
needle='  stage="backend_submit";reason=gpe_submit(&ctx,op,seq,0,execution,len,dst_ref,src_ref);if(reason)goto done;'
assert needle in s
replacement='''  struct tex102_sample texture102={0};const unsigned char *texture_source102=0;unsigned char *texture_destination102=0;
  if(op==1&&!plan.empty_clip_noop){texture_destination102=(unsigned char*)area+leading+(plan.dst-destination_base);texture_source102=(!(destination_screen&&source_screen)&&!same_parent)?(const unsigned char*)source_area+plan.src-source_page:(const unsigned char*)area+leading+(plan.src-destination_base);tex102_before(&texture102,raw,&plan,texture_source102,texture_destination102,seq,sr.object,dr.object);}else if(op==1)tex102_before(&texture102,raw,&plan,0,0,seq,sr.object,dr.object);
  stage="backend_submit";reason=gpe_submit(&ctx,op,seq,0,execution,len,dst_ref,src_ref);if(op==1)tex102_after(&texture102,&plan,texture_destination102,reason);if(reason)goto done;'''
s=s.replace(needle,replacement);(H/'fx3-gpe-observe-v23-capture102.c').write_text(s)
s=(H/'fx3-osd-headless-v6-live-frame.c').read_text()
s=s.replace('static int pmem=-1;', 'extern U fx3_gpe_observation_sequence102(void) __attribute__((weak));static __thread U copied_gpe102;\nstatic int pmem=-1;',1)
needle='memcpy(output,bits,f->span);';assert s.count(needle)==1;s=s.replace(needle,'copied_gpe102=fx3_gpe_observation_sequence102?fx3_gpe_observation_sequence102():0;'+needle)
needle='if(old)((U *)ring)[10]++;}'
assert needle in s;s=s.replace(needle,'''if(old)((U *)ring)[10]++;char desc[73];const char*hex="0123456789abcdef";for(unsigned i=0;i<36;i++){desc[2*i]=hex[job->descriptor[i]>>4];desc[2*i+1]=hex[job->descriptor[i]&15];}desc[72]=0;dprintf(2,"FX3_OSD102_COMMIT frame=%lu op=%#x pixel_source_seq=%lu copied_GPE_last=%lu FB=%#lx bitmap=%#lx entry=%#lx allocation=%#lx token=%#lx physical=%#lx FBformat=%lu bitmapformat=%lu descriptor36=%s native_plane_role_unproven=1 read_only_observation=1\\n",seq,job->pending,w[4],copied_gpe102,f->fb,f->bitmap,f->entry,f->allocation,f->token,f->physical,f->fbformat,f->bitmapformat,desc);}''',1)
for condition in ['seq<=30||seq%30==0','seq<=30||seq%30==0||rc','seq<=30||seq%30==0||rc||!consume']:
 s=s.replace('if('+condition+')dprintf','if(1)dprintf')
(H/'fx3-osd-headless-v7-observe102.c').write_text(s)
for old,new in [('fx3-gpe-observe-v22-tile101','fx3-gpe-observe-v23-capture102'),('fx3-osd-headless-v6-live-frame','fx3-osd-headless-v7-observe102')]:
 b=json.loads((H/(old+'-build.json')).read_text());args=[x.replace(old,new) for x in b['args']];p=subprocess.run(args,capture_output=True,text=True);(H/(new+'-build.log')).write_text(p.stdout+p.stderr);assert p.returncode==0,p.stderr;(H/(new+'-build.json')).write_text(json.dumps({'args':args,'exit':p.returncode,'source_sha256':sha(H/(new+'.c')),'output_sha256':sha(H/(new+'.so')),'base_source':str(H/(old+'.c')),'base_sha256':sha(H/(old+'.c')),'authority':['msg_7eb2cdbf663a','msg_2c7707dd92c8'],'observation_only':True,'backend_v8_source_unchanged':sha(H/'fx3-gpe-backend-v8.c'),'backend_v8_header_unchanged':sha(H/'fx3-gpe-backend-v8.h')},indent=2)+'\n')
print('Passive graphics observer libraries built; original backend v8 and protocol code retained')
