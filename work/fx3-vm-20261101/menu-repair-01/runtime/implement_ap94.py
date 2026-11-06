from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parent;H=R/'helpers'
def put(n,s):
 p=H/n;assert not p.exists(),n;p.write_text(s)
# Narrow audited flags0 reg760=0 4x overwrite, raw parameter bytes remain unchanged.
s=(H/'fx3-gpe-backend-v3.h').read_text().replace('BACKEND_V3_H','BACKEND_V4_H');put('fx3-gpe-backend-v4.h',s)
s=(H/'fx3-gpe-backend-v3.c').read_text().replace('fx3-gpe-backend-v3.h','fx3-gpe-backend-v4.h')
needle=' if(!q[115]) {'
new=r''' if(!q[115]&&(u32(q+16)!=u32(q+72)||u32(q+20)!=u32(q+76))) {
  uint32_t dw=u32(q+16),dh=u32(q+20),sw=u32(q+72),sh=u32(q+76);
  if(u32(q+52)||u32(q+92)||u32(q+104)||q[112]||q[113]||q[114]!=255)return GPE_UNSUPPORTED;
  for(unsigned i=115;i<=120;i++)if(q[i])return GPE_UNSUPPORTED;
  for(unsigned i=108;i<112;i++)if(q[i])return GPE_UNSUPPORTED;
  if(!sw||!sh||sw>INT32_MAX/4||sh>GPE_MAX_ROWS/4||dw!=sw*4||dh!=sh*4)return GPE_UNSUPPORTED;
  /* Audited subset: all coordinate/adjust and float slots zero, exact full clip. */
  const unsigned zero_slots[]={8,12,24,28,40,44,64,68,80,84,96,100};
  for(unsigned i=0;i<sizeof(zero_slots)/sizeof(zero_slots[0]);i++)if(u32(q+zero_slots[i]))return GPE_UNSUPPORTED;
  if(u32(q+32)!=dw||u32(q+36)!=dh)return GPE_UNSUPPORTED;
  memset(p,0,sizeof(*p));p->blit=1;p->bpp=p->src_bpp=2;p->rows=dh;p->line=(uint64_t)dw*2;
  p->src_rows=sh;p->src_line=(uint64_t)sw*2;p->source_width=sw;p->target_width=p->write_width=dw;p->target_height=dh;
  p->approx_stretch=1;p->approx_blend=0;p->constant_alpha=255;
  int r=address(u64(q),0,0,u32(q+48),dw,dh,2,&p->dst,&p->dst_step);if(r)return r;
  return address(u64(q+56),0,0,u32(q+88),sw,sh,2,&p->src,&p->src_step);
 }
'''+needle
assert s.count(needle)==1;s=s.replace(needle,new);put('fx3-gpe-backend-v4.c',s)
# Actual allocation event ledger. This is interval/lifetime tracking, NOT bitmap pinning.
s=(H/'fx3-gpe-resource-v3-target.inc').read_text()
s=s.replace('static U resource_epoch,allocation_events,resource_class_vptr;',r'''static U resource_epoch,allocation_events,resource_class_vptr;
#define CHILD_LIMIT 8192
struct child_record {U parent,parent_epoch,logical,phys,bytes,align,epoch;unsigned active;};
static struct child_record children[CHILD_LIMIT];static U child_epoch;
static U compaction_events;static unsigned draw_active;
static void child_retire(U parent,U logical,const char*why){for(unsigned i=0;i<CHILD_LIMIT;i++)if(children[i].active&&children[i].parent==parent&&(!logical||children[i].logical==logical)){children[i].active=0;dprintf(2,"FX3_GPE_CHILD_RETIRE parent=%#lx logical=%#lx child_epoch=%lu reason=%s before_native_release=1\n",parent,children[i].logical,children[i].epoch,why);}}
static void child_add(const struct resource_record*p,U logical,U phys,U bytes,U align){
 if(!bytes||logical<p->logical||logical-p->logical>p->bytes||bytes>p->bytes-(logical-p->logical)||phys!=p->phys+logical-p->logical||!align||(align&(align-1))||logical%align||phys%align)return;
 /* Overlap/reuse invalidates previous records conservatively, even on failed replacement admission. */
 for(unsigned i=0;i<CHILD_LIMIT;i++)if(children[i].active&&children[i].parent==p->object&&logical<children[i].logical+children[i].bytes&&children[i].logical<logical+bytes)children[i].active=0;
 unsigned slot=CHILD_LIMIT;for(unsigned i=0;i<CHILD_LIMIT;i++)if(!children[i].active){slot=i;break;}
 if(slot==CHILD_LIMIT||child_epoch==~0UL){child_retire(p->object,0,"capacity_or_epoch");return;}
 struct child_record c={p->object,p->epoch,logical,phys,bytes,align,++child_epoch,1};children[slot]=c;
 dprintf(2,"FX3_GPE_CHILD_REGISTER parent=%#lx parent_epoch=%lu logical=%#lx phys=%#lx bytes=%#lx align=%#lx child_epoch=%lu malloc_success_return=1 bitmap_binding_unproven=1 compaction_uncovered=1 queued_ABA_uncovered=1\n",c.parent,c.parent_epoch,c.logical,c.phys,c.bytes,c.align,c.epoch);
}
static int child_lookup(const struct resource_record*p,U a,U step,U line,unsigned rows,struct child_record*out){
 if(!rows||!line)return 0;unsigned count=0;struct child_record selected={0};
 for(unsigned i=0;i<CHILD_LIMIT;i++){struct child_record*c=&children[i];if(!c->active||c->parent!=p->object||c->parent_epoch!=p->epoch)continue;int valid=1;
  for(unsigned y=0;y<rows;y++){if(step&&y>(~0UL-a)/step){valid=0;break;}U at=a+(U)y*step;if(at<c->phys||at-c->phys>c->bytes||line>c->bytes-(at-c->phys)){valid=0;break;}}
  if(valid){selected=*c;count++;}}
 if(count!=1)return 0;*out=selected;return 1;
}
''')
s=s.replace('resources[i].active=0;dprintf','child_retire((U)o,0,event);resources[i].active=0;dprintf')
s=s.replace('if(!rc){life_enter();resource_add(o,"native_open_return_v1");life_leave();}', 'life_enter();resource_retire(o,"open_or_replace_attempt");if(!rc)resource_add(o,"native_open_return_v1");life_leave();')
# only register child if native result success + native field identity and matching parent current epoch.
s=s.replace('malloc_parent_register(o,&r,ptr,bytes);}', 'malloc_parent_register(o,&r,ptr,bytes);for(unsigned i=0;i<RESOURCE_LIMIT;i++)if(resources[i].active&&resources[i].object==(U)o&&resource_same(&resources[i],&r)){child_add(&resources[i],ptr,phys,bytes,align);break;}}else if(!rc){child_retire((U)o,0,"malloc_success_unverifiable");}')
a=s.index(' /* Allocation interval remains live;');b=s.index(' *__errno_location()=before;int rc=native_resource_free',a)
s=s[:a]+''' child_retire((U)o,(U)ptr,"free_entry");
 dprintf(2,"FX3_GPE_RESOURCE_SUBFREE object=%p logical=%p child_free_observed=1 child_epoch_tracked=1 before_native_release=1 bitmap_binding_unproven=1 compaction_uncovered=1 queued_ABA_uncovered=1\\n",o,ptr);
'''+s[b:]
# Avoid external lifecycle lock while waiting native free: invalidation committed first.
s=s.replace('child_epoch_tracked=1 before_native_release=1 bitmap_binding_unproven=1 compaction_uncovered=1 queued_ABA_uncovered=1\\n",o,ptr);\n *__errno_location()', 'child_epoch_tracked=1 before_native_release=1 bitmap_binding_unproven=1 compaction_uncovered=1 queued_ABA_uncovered=1\\n",o,ptr);life_leave();\n *__errno_location()')
s=s.replace('int after=*__errno_location();life_leave();\n __atomic_add_fetch', 'int after=*__errno_location();\n __atomic_add_fetch')
s=s.replace('if(!object_fields((void*)r->object,&now)||!resource_same(r,&now)){r->active=0;continue;}', 'if(!object_fields((void*)r->object,&now)||!resource_same(r,&now)){child_retire(r->object,0,"parent_identity_changed");r->active=0;continue;}')
s=s.replace('if(install_resource_hooks(m->base))', 'if(install_resource_hooks(m->base)&&install_compaction_hooks(m->base))')
# Compaction entry probes: no native call interception, no lock, no blocking.
a=s.index('static void bind_resources(')
comp=r'''
__attribute__((visibility("hidden"))) void fx3_compaction_event(U point,U*regs){int saved=*__errno_location();U e=__atomic_add_fetch(&compaction_events,1,__ATOMIC_RELAXED);dprintf(2,"FX3_GPE_COMPACTION point=%#lx event=%lu x0=%#lx x1=%#lx x2=%#lx observed_during_draw=%u entry_only=1 observe_only=1 original_args_unchanged=1 compaction_uncovered=1 queued_ABA_uncovered=1\n",point,e,regs[0],regs[1],regs[2],__atomic_load_n(&draw_active,__ATOMIC_RELAXED));*__errno_location()=saved;}
'''
off=[0x150b9c,0x103a40,0x103760,0x103804,0x1039a8,0xefd0c,0xefde8]
pref=['fd7bbba9fd030091f35301a9f40300aa','fd7bb7a9fd030091f35301a9f40300aa','fd7bbba9fd030091f35301a9b4c30091','fd7bb8a9fd030091f55b02a9b6830191','fd7bbba9fd030091f35301a9b3c30091','fd7bbba9fd030091f35301a9b4430191','fd7bbca9fd030091f35301a9b4030191']
asm=['.text']
for i,o in enumerate(off):
 comp+=f'__attribute__((visibility("hidden"))) U fx3_compaction_tramp_{i};\n'
 comp+=f'#ifndef FX3_GPE_HOST_TEST\nextern void fx3_compaction_probe_{i}(void);\n#else\nstatic void fx3_compaction_probe_{i}(void){{}}\n#endif\n'
 asm += [f'.global fx3_compaction_probe_{i}',f'.hidden fx3_compaction_probe_{i}',f'fx3_compaction_probe_{i}:',' sub sp,sp,#800']
 for r in range(0,30,2):asm.append(f' stp x{r},x{r+1},[sp,#{r*8}]')
 asm+=[' str x30,[sp,#240]']
 for r in range(0,32,2):asm.append(f' stp q{r},q{r+1},[sp,#{256+r*16}]')
 asm+=[' mrs x0,nzcv',' mrs x1,fpcr',' mrs x2,fpsr',' stp x0,x1,[sp,#768]',' str x2,[sp,#784]',f' mov x0,#{o&65535}',f' movk x0,#{o>>16},lsl #16',' mov x1,sp',' bl fx3_compaction_event',' ldp x0,x1,[sp,#768]',' ldr x2,[sp,#784]',' msr nzcv,x0',' msr fpcr,x1',' msr fpsr,x2']
 for r in range(0,32,2):asm.append(f' ldp q{r},q{r+1},[sp,#{256+r*16}]')
 for r in range(0,30,2):asm.append(f' ldp x{r},x{r+1},[sp,#{r*8}]')
 asm+=[' ldr x30,[sp,#240]',' add sp,sp,#800',f' adrp x16,fx3_compaction_tramp_{i}',f' ldr x16,[x16,:lo12:fx3_compaction_tramp_{i}]',' br x16']
comp+='static int install_compaction_hooks(U base){\n const U offsets[7]={'+','.join(hex(x) for x in off)+'};\n'
comp+=' const unsigned char expected[7][16]={'+','.join('{'+','.join('0x'+p[k:k+2] for k in range(0,32,2))+'}' for p in pref)+'};\n'
comp+=' void*targets[7]={'+','.join(f'(void*)fx3_compaction_probe_{i}' for i in range(7))+'};U*slots[7]={'+','.join(f'&fx3_compaction_tramp_{i}' for i in range(7))+'};\n'
comp+=r''' for(unsigned k=0;k<7;k++)if(__builtin_memcmp((void*)(base+offsets[k]),expected[k],16)){dprintf(2,"FX3_GPE_RESOURCE_BIND_REJECT reason=compaction_prefix point=%#lx\n",offsets[k]);return 0;}
 unsigned char*tr=mmap(0,4096,3,0x22,-1,0);if(tr==(void*)-1)return 0;const unsigned jump[2]={0x58000050,0xd61f0200};
 for(unsigned k=0;k<7;k++){unsigned char*t=tr+64*k;__builtin_memcpy(t,expected[k],16);__builtin_memcpy(t+16,jump,8);U back=base+offsets[k]+16;__builtin_memcpy(t+24,&back,8);*slots[k]=(U)t;}
 sync_instructions(tr,448);if(mprotect(tr,4096,5))return 0;
 for(unsigned k=0;k<7;k++){void*p=(void*)(base+offsets[k]);if(mprotect((void*)((U)p&~4095UL),4096,7))_exit(126);__builtin_memcpy(p,jump,8);U fn=(U)targets[k];__builtin_memcpy((char*)p+8,&fn,8);sync_instructions(p,16);if(mprotect((void*)((U)p&~4095UL),4096,5))_exit(126);}
 dprintf(2,"FX3_GPE_COMPACTION_BOUND count=7 original_prefix_verified=16 GPR_and_SIMD_flags_preserved=1 entry_only=1 observe_only=1 no_lifecycle_lock=1 compaction_uncovered=1\n");return 1;
}
'''
s=s[:a]+comp+s[a:];put('fx3-gpe-resource-v4-child.inc',s);put('fx3-gpe-compaction-v1.S','\n'.join(asm)+'\n')
# Adapter destination resolver. Keep OSD frame_target resolver unchanged.
s=(H/'fx3-gpe-observe-v18-frame-target.c').read_text().replace('fx3-gpe-backend-v3.h','fx3-gpe-backend-v4.h').replace('fx3-gpe-resource-v3-target.inc','fx3-gpe-resource-v4-child.inc')
s=s.replace('struct resource_record sr={0},dr={0};','struct resource_record sr={0},dr={0};struct child_record dc={0},sc={0};unsigned offscreen_child=0;')
s=s.replace('if(!obj_bound||!resource_lookup(plan.dst,plan.dst_step,plan.line,plan.rows,&dr)||!dr.native_open||dr.type!=0x403||!resource_class_vptr||dr.vptr!=resource_class_vptr){reason=GPE_STALE;goto done;}', 'if(!obj_bound||!resource_lookup(plan.dst,plan.dst_step,plan.line,plan.rows,&dr)||!resource_class_vptr||dr.vptr!=resource_class_vptr){reason=GPE_STALE;goto done;}\n   if(!(dr.native_open&&dr.type==0x403)){if(!child_lookup(&dr,plan.dst,plan.dst_step,plan.line,plan.rows,&dc)){reason=GPE_STALE;goto done;}offscreen_child=1;}')
s=s.replace('(void)pread(process_mem,&count_before', 'if(offscreen_child&&!child_lookup(&sr,plan.src,plan.src_step,plan.src_line,plan.src_rows,&sc)){reason=GPE_STALE;goto done;}\n   (void)pread(process_mem,&count_before')
s=s.replace('life_enter();life_held=1;U event_before=', 'life_enter();life_held=1;__atomic_store_n(&draw_active,1,__ATOMIC_RELAXED);U compact_before=__atomic_load_n(&compaction_events,__ATOMIC_RELAXED);U event_before=')
needle='  if(!destination_screen){\n   dprintf(2,"FX3_GPE_NATIVE_TARGET'
replace='''  dprintf(2,"FX3_GPE_DRAW_INTERVAL seq=%u offscreen_child=%u destination_parent=%#lx destination_parent_epoch=%lu destination_uhdl=%#x destination_child_epoch=%lu destination_child_phys=%#lx destination_child_bytes=%#lx source_parent=%#lx source_parent_epoch=%lu source_uhdl=%#x source_child_epoch=%lu source_child_phys=%#lx source_child_bytes=%#lx dst_span=%#lx src_span=%#lx same_parent=%u raster_mode=%s approx_stretch=%s approx_blend=%u compaction_entry_during_draw=%u bitmap_binding_unproven=1 compaction_uncovered=1 queued_ABA_uncovered=1\\n",seq,offscreen_child,dr.object,dr.epoch,dr.uhdl,dc.epoch,dc.phys,dc.bytes,sr.object,sr.epoch,sr.uhdl,sc.epoch,sc.phys,sc.bytes,(U)(plan.rows-1)*plan.dst_step+plan.line,op==1?(U)(plan.src_rows-1)*plan.src_step+plan.src_line:0,same_parent,plan.approx_blend?"straight_over_v1":"replace",plan.approx_stretch?"nearest_v1":"none",plan.approx_blend,compact_before!=__atomic_load_n(&compaction_events,__ATOMIC_RELAXED));
  if(!destination_screen&&!offscreen_child){
   dprintf(2,"FX3_GPE_NATIVE_TARGET'''
assert s.count(needle)==1;s=s.replace(needle,replace)
s=s.replace('if(life_held)life_leave();','if(life_held)life_leave();\n __atomic_store_n(&draw_active,0,__ATOMIC_RELAXED);')
s=s.replace('life_leave();life_held=0;fills_done++;','__atomic_store_n(&draw_active,0,__ATOMIC_RELAXED);life_leave();life_held=0;fills_done++;')
# all draws full56/144B and all CMD records incl scaled overwrite beyond cap
s=s.replace('if(n<=200||approx||result){','if(n<=200||approx||result||offscreen_observation(op,p,readable)){')
s=s.replace('static void marker(', 'static int offscreen_observation(unsigned op,const unsigned char*p,int readable){return readable&&op!=4&&(op==1||load64(p)<EXT_BASE);}\nstatic void marker(')
s=s.replace('if(op==1||result){','if(op!=4||result){')
put('fx3-gpe-observe-v19-child-stretch.c',s)
# Input plan sole behavioural change to RM provider (core v2 untouched).
s=(H/'fx3-input93-plan-v1.h').read_text().replace('INPUT93_PLAN_V1','INPUT94_PLAN_V1').replace('first[3]={0x30,3,0x1ac}','first[2]={3,0x1ac}').replace('step>20','step>19').replace('step<=3','step<=2');put('fx3-input94-plan-v1.h',s)
s=(H/'fx3-rm-key-gate-v2-setup.inc').read_text().replace('fx3-input93-plan-v1.h','fx3-input94-plan-v1.h');put('fx3-rm-key-gate-v3-up-enter.inc',s)
s=(H/'fx3-rm-empty-provider-v3-setup.c').read_text().replace('fx3-rm-key-gate-v2-setup.inc','fx3-rm-key-gate-v3-up-enter.inc');put('fx3-rm-empty-provider-v4-up-enter.c',s)
s=(R/'gate_input93_v2.py').read_text().replace('KEYS=[0x30,3,0x1ac]','KEYS=[3,0x1ac]').replace('len(keys)>20','len(keys)>19').replace('if i<3:','if i<2:');(R/'gate_input94.py').write_text(s)
s=(R/'run_candidate93_r5.py').read_text().replace('gate_input93_v2','gate_input94').replace('input_gate.command(1,0x30)','input_gate.command(1,3)').replace('host_step<20','host_step<19').replace("if host_step in [1,2]:key=[3,0x1ac][host_step-1]",'if host_step==1:key=0x1ac').replace('ap93-next-key.json','ap94-next-key.json').replace('msg_f063a6eaccba','msg_fd22adc6ac57')
# No automatic ENTER before first UP PNG is actually inspected. All subsequent actions manual.
s=s.replace('if host_step==1:key=0x1ac\n                    elif (run/', 'if (run/')
s=s.replace('ap93-step-readbacks.json','ap94-step-readbacks.json').replace("'ap93-phaseA.json'","'ap94-phaseA.json'")
(R/'run_candidate94.py').write_text(s);compile(s,'run_candidate94.py','exec')
print('created v19/backend4/child4/compaction probes/RMprovider4/input94/driver94')
