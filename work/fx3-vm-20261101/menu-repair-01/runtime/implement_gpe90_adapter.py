from pathlib import Path
R=Path(__file__).resolve().parent;H=R/'helpers'
s=(H/'fx3-gpe-observe-v15-earlybind.c').read_text().replace('"fx3-gpe-backend-v2.h"','"fx3-gpe-backend-v3.h"')
a=s.index('static int extent_live(');b=s.index('static unsigned char command_lock;',a)
s=s[:a]+'''#define EXT_BASE 0x43feb5000UL
#define EXT_BYTES 0x140000UL
#define PAYLOAD_BASE (EXT_BASE+0x100UL)
#include "fx3-gpe-screen-v1.inc"
''' + s[b:]
pos=s.index('static int approximate_command(')
s=s[:pos]+'#include "fx3-gpe-resource-v1.inc"\n'+s[pos:]
s=s.replace(' if(result){\n  char hex[289];',' if(op==1||result){\n  char hex[289];')
s=s.replace('FX3_GPE_REJECT_PARAMS op=%s seq=%u read=%d len=%u raw_hex=%s','FX3_GPE_RAW_PARAMS op=%s seq=%u read=%d len=%u raw_hex=%s')
needle='  if(!within(plan.dst,plan.dst_step,plan.line,plan.rows)||(op==1&&!within(plan.src,plan.src_step,plan.line,plan.rows))||!extent_live())goto done;'
a=s.index(needle);b=s.index('  fills_done++;',a)+len('  fills_done++;')
s=s[:a]+'''  if(!within(plan.dst,plan.dst_step,plan.line,plan.rows))goto done;
  life_enter();life_held=1;U event_before=__atomic_load_n(&allocation_events,__ATOMIC_RELAXED);
  struct screen_identity si={0},after_si={0};struct resource_record sr={0};unsigned count_before=0,count_after=0;
  if(!screen_live(&si)){reason=GPE_STALE;goto done;}
  int source_screen=op==1&&within(plan.src,plan.src_step,plan.src_line,plan.src_rows);
  if(op==1&&!source_screen){
   if(!obj_bound||!resource_lookup(plan.src,plan.src_step,plan.src_line,plan.src_rows,&sr)){reason=GPE_STALE;goto done;}
   (void)pread(process_mem,&count_before,4,(long)sr.object+0x24);
   U page=plan.src&~4095UL,tail=plan.src+(U)(plan.src_rows-1)*plan.src_step+plan.src_line;
   U requested=tail-page;if(requested>~0UL-4095){reason=GPE_BOUNDS;goto done;}
   source_bytes=(requested+4095)&~4095UL;source_page=page;
   source_area=mmap(0,source_bytes,1,1,physical,page);if(source_area==(void*)-1){reason=GPE_STALE;goto done;}
  }
  area=mmap(0,EXT_BYTES,3,1,physical,EXT_BASE);if(area==(void*)-1){reason=GPE_STALE;goto done;}
  if(!screen_live(&after_si)||si.serial!=after_si.serial){reason=GPE_STALE;goto done;}
  struct gpe_context ctx;struct gpe_ref dst_ref={0x81,si.serial},src_ref=dst_ref;
  gpe_init(&ctx,(struct gpe_hooks){0});reason=gpe_register(&ctx,dst_ref,EXT_BASE,area,EXT_BYTES);if(reason)goto done;
  if(op==1&&!source_screen){
   src_ref=(struct gpe_ref){sr.object,sr.epoch};
   /* Only the sampled source envelope is mapped read-only. The extra page
    * padding is never registered; no resource receives screen +0x100 rule. */
   U envelope=(U)(plan.src_rows-1)*plan.src_step+plan.src_line;
   reason=gpe_register(&ctx,src_ref,plan.src,(unsigned char*)source_area+plan.src-source_page,envelope);if(reason)goto done;
  }
  reason=gpe_begin_batch(&ctx,1);if(reason)goto done;
  unsigned char execution[144];__builtin_memcpy(execution,raw,len);execution[ao]=1;__builtin_memset(execution+fo,0,16);
  reason=gpe_submit(&ctx,op,seq,0,execution,len,dst_ref,src_ref);if(reason)goto done;
  __atomic_thread_fence(__ATOMIC_SEQ_CST);
  if(sr.object)(void)pread(process_mem,&count_after,4,(long)sr.object+0x24);
  U event_after=__atomic_load_n(&allocation_events,__ATOMIC_RELAXED);
  dprintf(2,"FX3_GPE_SCOPE seq=%u screen_extent_id=0x81 screen_type=0x545 screen_serial=%#lx source_object=%#lx source_uhdl=%#x source_epoch=%lu source_type=%#lx source_phys=%#lx source_bytes=%#lx interval_lease=1 subblock_lifetime_unproven=1 queued_ABA_uncovered=1 compaction_uncovered=1 compaction_or_subblock_change_during_draw=%u allocation_event_scope=all_heaps_conservative native_count_before=%u native_count_after=%u approx_fmt2=%u formula=%s original_fmt2_semantics_unproven=%u approx_stretch=%s\\n",seq,si.serial,sr.object,sr.uhdl,sr.epoch,sr.type,sr.phys,sr.bytes,event_before!=event_after||count_before!=count_after,count_before,count_after,plan.approx_fmt2,plan.approx_fmt2?"a8_color_straight_over_v1_candidate":plan.approx_blend?"straight_over_v1":"none",plan.approx_fmt2,plan.approx_stretch?"nearest_v1":"none");
  if(!screen_live(&after_si)||si.serial!=after_si.serial){reason=GPE_STALE;goto done;}
  if(munmap(area,EXT_BYTES)){area=(void*)-1;reason=GPE_DELIVERY;goto done;}area=(void*)-1;
  if(source_area!=(void*)-1){if(munmap(source_area,source_bytes)){source_area=(void*)-1;reason=GPE_DELIVERY;goto done;}source_area=(void*)-1;}
  life_leave();life_held=0;fills_done++;''' + s[b:]
s=s.replace('int reason=GPE_INVALID,result=5,locked=0;void *area=(void *)-1;struct gpe_plan plan;','int reason=GPE_INVALID,result=5,locked=0,life_held=0;void *area=(void *)-1,*source_area=(void*)-1;U source_bytes=0,source_page=0;struct gpe_plan plan;')
s=s.replace(' if(area!=(void *)-1)(void)munmap(area,EXT_BYTES);',' if(area!=(void *)-1)(void)munmap(area,EXT_BYTES);\n if(source_area!=(void*)-1)(void)munmap(source_area,source_bytes);\n if(life_held)life_leave();')
s=s.replace('physical=open("/dev/mem",2);process_mem=open("/proc/self/mem",0);','physical=open("/dev/mem",2);if(process_mem<0)process_mem=open("/proc/self/mem",0);')
s=s.replace('adapter=v15 early_thread_bind=1','adapter=v16 early_thread_bind=1 resource_interval_registry=1 fmt2_candidate=1 nearest_candidate=1')
needle=' if(h&&name&&(!strcmp(name,"appFw.so")'
s=s.replace(needle,' if(h&&!__atomic_load_n(&obj_bound,__ATOMIC_ACQUIRE)){void*obj=fn("libObj.so",5);if(obj)bind_resources(obj);}\n'+needle)
(H/'fx3-gpe-observe-v16-resources.c').write_text(s)
p=H/'fx3-gpe-resource-v1.inc';x=p.read_text().replace('child_epoch_invalidated=1','child_free_observed=1 child_epoch_untracked=1')
x=x.replace('before_native_release=1\\n",o,ptr);life_leave();','before_native_release=1\\n",o,ptr);')
x=x.replace('int rc=native_resource_free(o,ptr,flag);int after=*__errno_location();','int rc=native_resource_free(o,ptr,flag);int after=*__errno_location();life_leave();')
p.write_text(x)
print('v16 resources adapter written; v15 source unchanged')
