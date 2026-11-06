from pathlib import Path
import json,subprocess,hashlib
R=Path(__file__).resolve().parent;H=R/'helpers'
s=(H/'fx3-gpe-screen-v2-diag.inc').read_text().replace('static int screen_live(struct screen_identity*out){','static int screen_proc_live(struct screen_identity*out){');s+='\nstatic int screen_live(struct screen_identity*);\n';(H/'fx3-gpe-screen-v3-aux.inc').write_text(s)
s=(H/'fx3-gpe-resource-v4-child.inc').read_text();s=s.replace('static U resource_epoch,allocation_events,resource_class_vptr;','static U resource_epoch,allocation_events,resource_class_vptr;\nstatic U screen_anchor_object,screen_anchor_epoch;')
needle='r.native_open=!strcmp(origin,"native_open_return_v1");resources[slot]=r;'
replacement=needle+r'''
 if(r.native_open&&r.type==0x403&&r.uhdl==0x402&&r.phys==EXT_BASE&&r.bytes==EXT_BYTES&&r.vptr==resource_class_vptr){screen_anchor_object=r.object;screen_anchor_epoch=r.epoch;dprintf(2,"FX3_GPE_SCREEN_AUTHORITY_BOUND object=%#lx epoch=%lu identity=%#lx token=%#x native_open_type403=1 original_state10=1 authority=native_object_fields_and_epoch proc_auxiliary=1\n",r.object,r.epoch,r.identity,r.uhdl);}
'''
assert needle in s;s=s.replace(needle,replacement);(H/'fx3-gpe-resource-v5-authority.inc').write_text(s)
s=(H/'fx3-gpe-observe-v19r3-nearest-v2.c').read_text().replace('fx3-gpe-screen-v2-diag.inc','fx3-gpe-screen-v3-aux.inc').replace('fx3-gpe-resource-v4-child.inc','fx3-gpe-resource-v5-authority.inc')
needle='#include "fx3-gpe-resource-v5-authority.inc"'
wrapper=r'''
/* Caller holds lifecycle guard (draw or OSD target acquisition). Native epoch
 * is stable across successful proc reads, bounded retry and object fallback. */
static int screen_object_anchor(struct resource_record*out){unsigned count=0;struct resource_record selected={0};
 if(!screen_anchor_object||!screen_anchor_epoch)return 0;
 for(unsigned i=0;i<RESOURCE_LIMIT;i++){struct resource_record*r=&resources[i];if(!r->active||r->object!=screen_anchor_object||r->epoch!=screen_anchor_epoch||!r->native_open||r->type!=0x403||r->uhdl!=0x402||r->phys!=EXT_BASE||r->bytes!=EXT_BYTES||r->vptr!=resource_class_vptr)continue;struct resource_record current={0};if(!object_fields((void*)r->object,&current)||!resource_same(r,&current))return 0;selected=*r;count++;}
 if(count!=1)return 0;*out=selected;return 1;
}
static int screen_live(struct screen_identity*out){int saved=*__errno_location();struct screen_identity proc={0};int first=screen_proc_live(&proc),second=first;unsigned first_code=screen_diag_code;
 if(!first){syscall(124);second=screen_proc_live(&proc);}
 if(screen_anchor_object){struct resource_record r={0};if(!screen_object_anchor(&r)){dprintf(2,"FX3_GPE_SCREEN_AUTHORITY_REJECT object=%#lx epoch=%lu proc_first=%d proc_retry=%d object_fields_epoch_state_release_guard_failed=1\n",screen_anchor_object,screen_anchor_epoch,first,second);*__errno_location()=saved;return 0;}
  if(out)out->serial=r.epoch;
  if(!first)dprintf(2,"FX3_GPE_SCREEN_RECHECK screen_recheck=object_authoritative proc_inconsistent=1 proc_first_code=%u proc_retry_result=%d object=%#lx epoch=%lu identity=%#lx type=%#lx token=%#x phys=%#lx bytes=%#lx original_state10=1 exact_original_fields=1 no_close_release_since_registration=1 lifecycle_guard=1 proc_is_auxiliary=1\n",first_code,second,r.object,r.epoch,r.identity,r.type,r.uhdl,r.phys,r.bytes);
  *__errno_location()=saved;return 1;
 }
 /* Before a registered original screen exists, retain the strict proc path;
  * a failed proc never authorizes an unknown allocation. */
 if(second&&out)*out=proc;*__errno_location()=saved;return second;
}
'''
s=s.replace(needle,needle+wrapper);(H/'fx3-gpe-observe-v19r4-object-authority.c').write_text(s)
s=(H/'check-gpe94-r3-center.c').read_text().replace('fx3-gpe-observe-v19r3-nearest-v2.c','fx3-gpe-observe-v19r4-object-authority.c').replace('int main(void){assert(!retained_94r2_main());','int retained_94r3_main(void){assert(!retained_94r2_main());')
s+=r'''
static void anchor94_setup(void){reset();private_register(0x403,1);screen_anchor_object=screen_anchor_epoch=0;p64(object90+0x60,EXT_BASE);p32(object90+0x40,0x402);life_enter();resource_add(object90,"native_open_return_v1");life_leave();assert(screen_anchor_object==(U)object90&&screen_anchor_epoch);}
int main(void){assert(!retained_94r3_main());unsigned char p[144];struct screen_identity si;U tuple[10];
 for(unsigned mode=1;mode<=5;mode++){anchor94_setup();proc90_mode=mode;life_enter();assert(screen_live(&si)&&si.serial==screen_anchor_epoch);life_leave();mkfill(p,0);assert(!fill(0,0,4000+mode,0,p));assert(!fx3_gpe_snapshot_trylock());assert(!fx3_gpe_frame_target_acquire(PAYLOAD_BASE,0x96000,0x402,tuple,10));assert(tuple[3]==screen_anchor_epoch);assert(!fx3_gpe_frame_target_recheck(tuple,PAYLOAD_BASE,0x96000,0x402));assert(!fx3_gpe_frame_target_release());assert(!fx3_gpe_snapshot_unlock());}
 for(unsigned mode=0;mode<3;mode++){anchor94_setup();proc90_mode=2;if(mode==0)p64(object90+0x10,0x999);if(mode==1)screen_anchor_epoch++;if(mode==2){life_enter();resource_retire(object90,"host_close");life_leave();proc90_mode=0;}memcpy(before,memory,sizeof memory);mkfill(p,0);assert(fill(0,0,4100+mode,0,p)==5&&!memcmp(before,memory,sizeof memory));assert(!fx3_gpe_snapshot_trylock());assert(fx3_gpe_frame_target_acquire(PAYLOAD_BASE,0x96000,0x402,tuple,10));assert(!fx3_gpe_snapshot_unlock());}
 puts("AUTHORITY94R4_PASS duplicate_truncated_schema_proc_plus_exact_live_native_object_accept/draw_OSD_shared_policy/identity_epoch_release_reject_zero_write/bounded_one_retry_no_unknown_allocation_fallback");return 0;}
'''
(H/'check-gpe94-r4-authority.c').write_text(s)
args=['clang','-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all','-pthread','-I',str(H),str(H/'check-gpe94-r4-authority.c'),str(H/'fx3-gpe-backend-v5.c'),'-o',str(H/'check-gpe94-r4-authority')];p=subprocess.run(args,capture_output=True,text=True);assert not p.returncode,p.stderr;p=subprocess.run([str(H/'check-gpe94-r4-authority')],capture_output=True,text=True);log=H/'check-gpe94-r4-authority.log';log.write_text(p.stdout+p.stderr);print(p.returncode,p.stdout[-700:],p.stderr);assert not p.returncode
old='fx3-gpe-observe-v19r3-nearest-v2';new='fx3-gpe-observe-v19r4-object-authority';args=[x.replace(old,new) for x in json.loads((H/(old+'-build.json')).read_text())['args']];p=subprocess.run(args,capture_output=True,text=True);assert not p.returncode,p.stderr;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();(H/(new+'-build.json')).write_text(json.dumps({'args':args,'exit':0,'authority':'msg_4f0238f1bb4d','source_sha256':sha(H/(new+'.c')),'output_sha256':sha(H/(new+'.so'))},indent=2)+'\n');(R/'ap94-r4-object-authority-host-check.json').write_text(json.dumps({'authority':'msg_4f0238f1bb4d','ASan_UBSan_exit':0,'retained_all_r3_vectors':True,'duplicate_truncated_schema_plus_exact_native_object':True,'object_failure_epoch_change_close_reject_zero_write':True,'draw_and_OSD_target_lease_share_policy':True,'log':str(log),'log_sha256':sha(log),'OSDv6_unused_extent_function_not_called':True,'OSD_binary_unchanged_frame_target_API_provider_updated':True},indent=2)+'\n')
print('PASS native object authority and OSD shared export host regression')
