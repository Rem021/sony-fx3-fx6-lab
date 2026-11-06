from pathlib import Path
import hashlib,json,plistlib,subprocess
R=Path(__file__).resolve().parent;H=R/'helpers';assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
def save(n,s):p=H/n;assert not p.exists(),p;p.write_text(s)
def wrap(s,signature,name,wrapper):
 assert s.count(signature)==1,(name,s.count(signature));start=s.index(signature);opening=s.index('{',start);depth=0;string=None;escape=False;i=opening
 while i<len(s):
  c=s[i]
  if string:
   if escape:escape=False
   elif c=='\\':escape=True
   elif c==string:string=None
  else:
   if c in ['"',"'"]:string=c
   elif c=='{':depth+=1
   elif c=='}':
    depth-=1
    if depth==0:break
  i+=1
 assert depth==0
 original=s[start:i+1];changed=original.replace(name+'(',name+'_profile_impl(',1);return s[:start]+changed+'\n'+wrapper+'\n'+s[i+1:]
s=(H/'fx3-gpe-screen-v3-aux.inc').read_text()
s=wrap(s,'static int read_proc_complete(', 'read_proc_complete','static int read_proc_complete(const char*p,char*d,U n){U t=pr104_start();int r=read_proc_complete_profile_impl(p,d,n);pr104_end(P104_PROC_READ,t);return r;}')
s=wrap(s,'static int screen_proc_live(', 'screen_proc_live','static int screen_proc_live(struct screen_identity*out){struct pr104_context*c=pr104_current;U before=c?c->w[16+P104_PROC_READ]:0,t=pr104_start();int r=screen_proc_live_profile_impl(out);if(c){U now=pr104_now(),reads=c->w[16+P104_PROC_READ]-before;if(t&&now>=t&&now-t>=reads){c->w[16+P104_PROC_PARSE]+=now-t-reads;c->w[32+P104_PROC_PARSE]++;}else c->w[58]++;}return r;}')
save('fx3-gpe-screen-v4-profile104.inc',s)
s=(H/'fx3-gpe-resource-v5-authority.inc').read_text()
s=wrap(s,'static void life_enter(', 'life_enter','static void life_enter(void){U t=pr104_start();life_enter_profile_impl();U end=pr104_end(P104_LIFE_WAIT,t);if(pr104_current)pr104_current->life_since=end;}')
s=wrap(s,'static void life_leave(', 'life_leave','static void life_leave(void){U held=pr104_current?pr104_current->life_since:0;life_leave_profile_impl();if(held){pr104_end(P104_LIFE_HOLD,held);pr104_current->life_since=0;}}')
s=wrap(s,'static int object_fields(', 'object_fields','static int object_fields(void*o,struct resource_record*r){U t=pr104_start();int result=object_fields_profile_impl(o,r);pr104_end(P104_OBJECT,t);return result;}')
save('fx3-gpe-resource-v6-profile104.inc',s)
s=(H/'fx3-texture-observe102-v2.h').read_text()
s=wrap(s,'static void tex102_before(', 'tex102_before','static void tex102_before(struct tex102_sample*s,const unsigned char*raw,const struct gpe_plan*p,const unsigned char*src,const unsigned char*dst,unsigned seq,U so,U dob){U t=pr104_start();tex102_before_profile_impl(s,raw,p,src,dst,seq,so,dob);pr104_end(P104_TEX_COPY,t);if(pr104_current&&s->enabled){pr104_current->w[59]=s->source_bytes+2*s->destination_bytes;pr104_current->w[60]=s->source_bytes;}}')
s=wrap(s,'static void tex102_after(', 'tex102_after','static void tex102_after(struct tex102_sample*s,const struct gpe_plan*p,const unsigned char*dst,int result){U t=pr104_start();tex102_after_profile_impl(s,p,dst,result);pr104_end(P104_TEX_COPY,t);}')
s=wrap(s,'static void tex102_emit(', 'tex102_emit','static void tex102_emit(struct tex102_sample*s){U t=pr104_start();tex102_emit_profile_impl(s);pr104_end(P104_TEX_EMIT,t);}')
save('fx3-texture-observe102-v3-profile104.h',s)
s=(H/'fx3-complete104-observe-v1.h').read_text()
s=wrap(s,'static void gpe104_callback(', 'gpe104_callback','static void gpe104_callback(void(*fn)(const void*),const void*p,unsigned seq,unsigned op,unsigned async,unsigned source,U opaque){U t=pr104_start();gpe104_callback_profile_impl(fn,p,seq,op,async,source,opaque);pr104_end(P104_CALLBACK,t);}')
s=wrap(s,'static int gpe104_complete(', 'gpe104_complete','static int gpe104_complete(int(*fn)(unsigned,const void*,size_t),unsigned target,const void*p,size_t n,unsigned seq,unsigned op,unsigned async){U t=pr104_start();int r=gpe104_complete_profile_impl(fn,target,p,n,seq,op,async);pr104_end(P104_COMPLETE,t);return r;}')
save('fx3-complete104-observe-v2-profile104.h',s)
s=(H/'fx3-gpe-observe-v25-complete104.c').read_text();old='#include "fx3-gpe-command-wait102-v1.h"\n';assert s.count(old)==1;s=s.replace(old,'')
needle='static void *(*app_original)(void *);';assert s.count(needle)==1;s=s.replace(needle,'extern int munmap(void *,size_t);\n#include "fx3-gpe-command-wait102-v1.h"\n#include "fx3-gpe-profile104-v1.h"\n#define mmap pr104_mmap\n#define munmap pr104_munmap\n'+needle)
s=s.replace('fx3-gpe-screen-v3-aux.inc','fx3-gpe-screen-v4-profile104.inc').replace('fx3-gpe-resource-v5-authority.inc','fx3-gpe-resource-v6-profile104.inc').replace('fx3-texture-observe102-v2.h','fx3-texture-observe102-v3-profile104.h').replace('fx3-complete104-observe-v1.h','fx3-complete104-observe-v2-profile104.h')
s=wrap(s,'static int executable_callback(', 'executable_callback','static int executable_callback(U fn){U t=pr104_start();int r=executable_callback_profile_impl(fn);pr104_end(P104_CALLBACK_CHECK,t);return r;}')
s=wrap(s,'static void marker(', 'marker','static void marker(unsigned op,unsigned seq,const unsigned char*p,int readable,int result,int reason){U t=pr104_start();marker_profile_impl(op,seq,p,readable,result,reason);pr104_end(P104_MARKER,t);}')
needle='static int command(unsigned op,int g,int c,unsigned seq,unsigned src,const void *p){\n';assert s.count(needle)==1;s=s.replace(needle,needle+' struct pr104_context profile104;pr104_begin(&profile104,seq,op,src);\n')
old='if(gpe102_take(&command_lock,seq,op)){marker(op,seq,raw,readable,5,GPE_BUSY);gpe104_command_return(seq,op,src,5);return 5;}locked=1;';new='U lock104=pr104_start();int lock104_result=gpe102_take(&command_lock,seq,op);pr104_end(P104_COMMAND_LOCK,lock104);if(lock104_result){marker(op,seq,raw,readable,5,GPE_BUSY);gpe104_command_return(seq,op,src,5);pr104_finish(&profile104,5,readable?raw:0,len);return 5;}locked=1;';assert s.count(old)==1;s=s.replace(old,new)
old='stage="plan";reason=op==0?gpe_plan_fill(raw,len,&plan):gpe_plan_blit(raw,len,&plan);if(reason)goto done;';new='stage="plan";U plan104=pr104_start();reason=op==0?gpe_plan_fill(raw,len,&plan):gpe_plan_blit(raw,len,&plan);pr104_end(P104_PLAN,plan104);if(reason)goto done;';assert s.count(old)==1;s=s.replace(old,new)
old='stage="backend_submit";reason=gpe_submit(&ctx,op,seq,0,execution,len,dst_ref,src_ref);';new='stage="backend_submit";U backend104=pr104_start();reason=gpe_submit(&ctx,op,seq,0,execution,len,dst_ref,src_ref);pr104_end(P104_BACKEND,backend104);';assert s.count(old)==1;s=s.replace(old,new)
needle=' gpe104_command_return(seq,op,src,result);\n';assert s.count(needle)==1;s=s.replace(needle,needle+' pr104_finish(&profile104,result,readable?raw:0,len);\n')
needle=' if(physical<0||process_mem<0)return;';assert s.count(needle)==1;s=s.replace(needle,needle+'\n pr104_init(physical);')
save('fx3-gpe-observe-v26-profile104.c',s);print('PROFILE104_OBSERVATION_ONLY_SOURCES_CREATED')
