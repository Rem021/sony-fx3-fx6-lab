from pathlib import Path
import hashlib
ROOT=Path(__file__).resolve().parent
H=ROOT.parents[2]/'menu-repair-01/runtime/helpers'
def replace(s,a,b):
 assert s.count(a)==1,(a[:80],s.count(a));return s.replace(a,b)
def make():
 source=(H/'fx3-gpe-observe-v25-complete104.c').read_text()
 assert hashlib.sha256(source.encode()).hexdigest()=='54b0bde37888376f372eb26d4241054277cbda6af5636a3a17def0ff86f63e70'
 (ROOT/'fx3-gpe-observe-v25-reference.c').write_text(source)
 s=source.replace('fx3-gpe-backend-v8.h','fx3-gpe-backend-v9.h')
 s=replace(s,'#include "fx3-gpe-resource-v5-authority.inc"','#include "cache-v26.inc"\n#include "resource-v26.inc"')
 a=s.index('static int screen_live(struct screen_identity*out)');b=s.index('\nstatic int within(U,U,U,unsigned);',a)
 s=s[:a]+'''static int screen_live(struct screen_identity*out){
 int saved=*__errno_location();
 if(screen_anchor_object){struct resource_record r={0};
  if(!screen_object_anchor(&r)){map26_retire(screen_anchor_object);*__errno_location()=saved;return 0;}
  if(out)out->serial=r.epoch;*__errno_location()=saved;return 1;
 }
 /* No registered native owner: retain the complete strict proc fallback. */
 struct screen_identity proc={0};int first=screen_proc_live(&proc),second=first;
 if(!first){syscall(124);second=screen_proc_live(&proc);}
 if(second&&out)*out=proc;*__errno_location()=saved;return second;
}
''' + s[b:]
 s=replace(s,' if(!fn)return 1;',' if(!fn)return 1;\n if(callback26_hit(fn))return 1;')
 s=replace(s,"perms[2]=='x'&&!(fn&3))return 1;","perms[2]=='x'&&!(fn&3)){callback26_add(fn);return 1;}")
 s=s.replace('#include "fx3-texture-observe102-v2.h"','#include "texture-v26.inc"')
 s=replace(s,'struct gpe_plan plan;\n if(gpe102_take','struct gpe_plan plan;unsigned source_cached26=0,destination_cached26=0;\n if(gpe102_take')
 a=s.index('   U page=plan.src&~4095UL,tail=');b=s.index('\n  stage="screen_recheck";',a)
 s=s[:a]+'''   U source_base26=source_screen?EXT_BASE:sr.phys,source_size26=source_screen?EXT_BYTES:sr.bytes;
   U source_object26=source_screen?screen_anchor_object:sr.object,source_epoch26=source_screen?screen_anchor_epoch:sr.epoch;
   stage="source_mmap";source_area=map26_get(source_object26,source_epoch26,source_base26,source_size26,1,&source_cached26,&source_page,&source_bytes);
   if(source_area==(void*)-1){reason=GPE_STALE;goto done;}
  }
  U destination_base=destination_screen?EXT_BASE:dr.phys,destination_size=destination_screen?EXT_BYTES:dr.bytes;
  U destination_page=0,leading=destination_base&4095UL;
  U destination_object26=destination_screen?screen_anchor_object:dr.object,destination_epoch26=destination_screen?screen_anchor_epoch:dr.epoch;
  stage="destination_mmap";area=map26_get(destination_object26,destination_epoch26,destination_base,destination_size,3,&destination_cached26,&destination_page,&destination_map_bytes);
  if(area==(void*)-1){reason=GPE_STALE;goto done;}
''' + s[b:]
 s=s.replace('if(munmap(area,destination_map_bytes))','if(!destination_cached26&&munmap(area,destination_map_bytes))')
 s=s.replace('if(munmap(source_area,source_bytes))','if(!source_cached26&&munmap(source_area,source_bytes))')
 s=s.replace('if(area!=(void *)-1)(void)munmap','if(area!=(void *)-1&&!destination_cached26)(void)munmap')
 s=s.replace('if(source_area!=(void*)-1)(void)munmap','if(source_area!=(void*)-1&&!source_cached26)(void)munmap')
 s=s.replace('adapter=v18_frame_target early_thread_bind=1','adapter=v26_perf backend=v9 object_authoritative_no_draw_proc=1 mapping_cache=object_epoch texture_observe_default=0 callback_cache_default=0 early_thread_bind=1')
 s=replace(s,'void *dlopen(const char *name,int flags) {','void *dlopen(const char *name,int flags) {\n fx3_gpe_callback_cache_invalidate26();')
 (ROOT/'fx3-gpe-observe-v26-perf.c').write_text(s)
 r=(H/'fx3-gpe-resource-v5-authority.inc').read_text()
 r=replace(r,'static void resource_retire(void *o,const char *event){','static void resource_retire(void *o,const char *event){\n map26_retire((U)o);')
 r=replace(r,'child_retire(r->object,0,"parent_identity_changed");r->active=0;','map26_retire(r->object);child_retire(r->object,0,"parent_identity_changed");r->active=0;')
 a='screen_anchor_object=r.object;screen_anchor_epoch=r.epoch;'
 r=replace(r,a,a+'struct screen_identity auxiliary26={0};(void)screen_proc_live(&auxiliary26);')
 (ROOT/'resource-v26.inc').write_text(r)
if __name__=='__main__':make()
