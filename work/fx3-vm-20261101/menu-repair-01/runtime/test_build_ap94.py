from pathlib import Path
import subprocess,json,hashlib
R=Path(__file__).resolve().parent;H=R/'helpers';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
s=(H/'check-gpe93-frame-target.c').read_text().replace('fx3-gpe-observe-v18-frame-target.c','fx3-gpe-observe-v19-child-stretch.c').replace('flag==1&&lifecycle_lock','flag==1&&!lifecycle_lock').replace('int main(void){assert(!legacy_native_target93_main());','int retained_frame94_main(void){assert(!legacy_native_target93_main());')
s+=r'''
static void child_setup94(void){reset();private_register(0,0);memset(children,0,sizeof children);life_enter();child_add(&resources[0],0x12340100,PRIVATE_BASE+0x100,0x780,0x40);child_add(&resources[0],0x12340900,PRIVATE_BASE+0x900,0x7400,0x40);life_leave();}
static void stretch94(unsigned char*p){memset(p,0,144);p64(p,PRIVATE_BASE+0x900);p64(p+56,PRIVATE_BASE+0x100);p32(p+16,116);p32(p+20,116);p32(p+32,116);p32(p+36,116);p32(p+48,128);p32(p+72,29);p32(p+76,29);p32(p+88,32);p[114]=255;p[121]=1;}
static void raster_vectors94(void){unsigned char p[144],raw[144];for(unsigned pattern=0;pattern<2;pattern++){
 child_setup94();memset(private_memory,0xa5,sizeof private_memory);memset(private_memory+0x100,0x3d,0x780);
 if(!pattern){mkfill(p,0);p64(p,PRIVATE_BASE+0x100);p32(p+16,32);p32(p+20,29);p32(p+24,32);memset(p+32,255,4);assert(!fill(0,0,2000,0,p));}
 else for(unsigned y=0;y<29;y++)for(unsigned x=0;x<29;x++){unsigned short v=((x*37+y*53)^0xa530)&65535;memcpy(private_memory+0x100+(y*32+x)*2,&v,2);}
 memcpy(private_before,private_memory,sizeof private_memory);stretch94(p);memcpy(raw,p,144);struct gpe_plan plan;assert(!gpe_plan_blit(p,144,&plan)&&plan.approx_stretch&&!plan.approx_blend&&!plan.approx_fmt2);assert(!blit(0,0,2001+pattern,0,p));assert(!memcmp(p,raw,144));
 for(unsigned y=0;y<116;y++)for(unsigned x=0;x<116;x++){unsigned short v=pattern?(((x/4*37+y/4*53)^0xa530)&65535):65535;memcpy(private_before+0x900+(y*128+x)*2,&v,2);}
 assert(!memcmp(private_before,private_memory,sizeof private_memory));printf("VECTOR94 pixel_%s PASS pixels=13456 padding_bytes=2784 source_and_neighbors_unchanged=1 alpha0_RGB_overwritten=1\n",pattern?"pattern":"white");}}
static void admission_vectors94(void){struct child_record c={0};struct resource_record r={0};
 for(unsigned v=0;v<10;v++){child_setup94();U a=PRIVATE_BASE+0x900,bytes=0x73e8;unsigned expected=1;
 if(v==1){resource_retire(object90,"test_close");expected=0;}
 if(v==2){child_retire((U)object90,0x12340900,"test_free");expected=0;}
 if(v==3){resources[0].epoch++;expected=0;}
 if(v==4){child_retire((U)object90,0x12340900,"reuse");U old=children[1].epoch;child_add(&resources[0],0x12340900,a,0x7400,0x40);assert(children[1].epoch>old);/* queued raw params have no epoch: uncovered, not falsely rejected */}
 if(v==5)bytes=0x7400;
 if(v==6){bytes=0x7401;expected=0;}
 if(v==7){a--;expected=0;}
 if(v==8){children[2]=children[1];expected=0;}
 if(v==9){p64(object90+0x10,0xdead);expected=0;}
 life_enter();int parent=resource_lookup(a,bytes,bytes,1,&r);int got=parent&&child_lookup(&r,a,bytes,bytes,1,&c);life_leave();assert((unsigned)got==expected);printf("VECTOR94 admission_%u PASS accepted=%u queued_ABA_uncovered=1 bitmap_binding_unproven=1 compaction_uncovered=1\n",v,got);
 }
 /* Native free/close revoke before original calls; invalid child zero-write. */
 child_setup94();unsigned char p[144];stretch94(p);child_retire((U)object90,0x12340900,"host_free");memcpy(private_before,private_memory,sizeof private_memory);assert(blit(0,0,2100,0,p)==5&&!memcmp(private_before,private_memory,sizeof private_memory));
 /* Unknown operations, partial clip, rotation, flags, zero, overflow and stride all reject zero-write. */
 for(unsigned v=0;v<9;v++){child_setup94();stretch94(p);if(v==0)p32(p+104,90);if(v==1)p[115]=1;if(v==2)p32(p+52,2);if(v==3)p32(p+32,115);if(v==4)p32(p+48,115);if(v==5)p32(p+72,0);if(v==6)p64(p,~0UL-5);if(v==7)p32(p+8,0xffffffff);if(v==8)p64(p+56,PRIVATE_BASE+0x900);memcpy(private_before,private_memory,sizeof private_memory);assert(blit(0,0,2200+v,0,p)==5&&!memcmp(private_before,private_memory,sizeof private_memory));}
 /* Compaction is observed, never blocked; marker notes concurrent draw. */
 U regs[31]={0},old=compaction_events;draw_active=1;fx3_compaction_event(0xefd0c,regs);draw_active=0;assert(compaction_events==old+1);puts("CHILD94_PASS active_epoch/free_close_revoke/full_rows/no_parent_only_permission/unknown_zero_write/compaction_observe_only");
}
int main(void){assert(!retained_frame94_main());raster_vectors94();admission_vectors94();return 0;}
'''
p=H/'check-gpe94-child.c';assert not p.exists();p.write_text(s)
p=H/'check-gpe94-regression.c';assert not p.exists();p.write_text((H/'check-gpe90-backend.c').read_text().replace('fx3-gpe-backend-v3.c','fx3-gpe-backend-v4.c'))
checks=[]
for name,sources in [('check-gpe94-child',['check-gpe94-child.c','fx3-gpe-backend-v4.c']),('check-gpe94-regression',['check-gpe94-regression.c'])]:
 args=['clang','-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all','-pthread','-I',str(H),*[str(H/x) for x in sources],'-o',str(H/name)]
 p=subprocess.run(args,capture_output=True,text=True);(H/(name+'-compile.log')).write_text(p.stdout+p.stderr);assert p.returncode==0,p.stderr
 p=subprocess.run([str(H/name)],capture_output=True,text=True);log=H/(name+'.log');log.write_text(p.stdout+p.stderr);print(name,p.returncode,p.stdout[-650:],p.stderr[-1500:]);checks.append({'name':name,'args':args,'exit':p.returncode,'log':str(log),'log_sha256':sha(log)});assert p.returncode==0
# native cross builds
for old,new,backend in [('fx3-gpe-observe-v18-frame-target','fx3-gpe-observe-v19-child-stretch',True),('fx3-rm-empty-provider-v3-setup','fx3-rm-empty-provider-v4-up-enter',False)]:
 args=json.loads((H/(old+'-build.json')).read_text())['args'];args=[x.replace(old,new).replace('fx3-gpe-backend-v3.c','fx3-gpe-backend-v4.c') for x in args]
 if backend:args.insert(args.index('-o'),str(H/'fx3-gpe-compaction-v1.S'))
 p=subprocess.run(args,capture_output=True,text=True);print(new,p.returncode,p.stderr);assert p.returncode==0
 (H/(new+'-build.json')).write_text(json.dumps({'args':args,'exit':p.returncode,'source_sha256':sha(H/(new+'.c')),'output_sha256':sha(H/(new+'.so')),'authority':'msg_fd22adc6ac57'},indent=2)+'\n')
(R/'ap94-host-check.json').write_text(json.dumps({'checks':checks,'proof_replay_sha256':'331cd0acab44d79634d297d7662cf0f46af0304add1f4071c2ee31455febb4a6','audit_12_python_guard_model_vectors_replayed':True,'C_vectors':{'pixel':2,'admission_actual_contract':10,'additional_prewrite_reject':9},'limitations':['bitmap command binding unproven','queued ABA uncovered; reuse new epoch observed but raw FIFO lacks epoch sidecar','compaction observation only, never blocked'],'authority':'msg_fd22adc6ac57'},indent=2)+'\n')
