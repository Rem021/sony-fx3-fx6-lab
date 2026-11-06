"""Assemble only reviewed OWN C fragments, with fixed-input manifest pins."""
from pathlib import Path
from hashlib import sha256
import json
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2]
P=B/'stage234-fixed-RAM-plan-preparer';W=B/'stage231-constructor-noexec-child-and-reload-observer'
for p,digest in [(P,'76d6babd27647379a883a7bb6af3e24f4451c1cd65560d3294c5262381aaa5c3'),(W,'85326100f4abf29a0310efc76d48c5f1007582238d7af4494200552d8fd8e311')]:
 assert sha256((p/'final-receipt.json').read_bytes()).hexdigest()==digest
 m=json.loads((p/'final-receipt.json').read_text())
 for name in ['prepare.c','entry.c','core_support.inc','parent_ipc.inc']:
  if (p/name).exists():assert sha256((p/name).read_bytes()).hexdigest()==next(x['sha256'] for x in m['files'] if x['path']==str((p/name).relative_to(R)))
prep=(P/'prepare.c').read_text();worker=(W/'entry.c').read_text()
head,body=prep.split('__attribute__((constructor)) static void fx3_module_init(void){',1);body=body.split('__attribute__((visibility("default")))',1)[0]
head=head.replace('static int state,reason;','enum {E_START=1,E_HELD=2,E_OBSERVED=3,E_DENIED=4};\nstatic int state,reason;\nstatic u8 plan[256],record[256],common[32],own_image_sha[32];\nstatic struct kstat prepared_identity;')
head=head.replace('FX3PREPCONFIGv1','FX3SINGLECFGv1')
head+='static int crc_ok(const u8 *p){return get32(p+252)==(crc(0xffffffffu,p,252)^0xffffffffu);}\n'
body=body.replace('copy(plan+32,cfg+32,112);','copy(plan+32,cfg+32,112);copy(plan+112,own_sha,32);')
body=body.replace('copy(report+112,cfg+112,32);','copy(report+112,own_sha,32);')
old='if(!tick(&now)||now>=begun+ttl)error(21);else state=1;';new='if(!tick(&now)||now>=begun+ttl)error(21);else{copy(own_image_sha,own_sha,32);copy((u8 *)&prepared_identity,(u8 *)&pending,sizeof(pending));state=1;}'
assert body.count(old)==1;body=body.replace(old,new)
parts=worker[worker.index('static int write256('):worker.index('static int image_profile(')]
parts=parts.replace('(get32(plan+20)!=1&&get32(plan+20)!=2)','get32(plan+20)!=1')
parts+=worker[worker.index('static int proc_directory('):worker.index('static void launch(')]
source=head+'static void prepare_fixed(void){'+body+'\n'+parts
tail=r'''
/* Full preparation -> exact source object -> same-constructor launch.
 * No later-load observer or mode2 path exists in this component. */
static int read_prepared_plan(long root){
 long fd=sc(56,root,(long)"fx3-entry-plan-v1.bin",RD,0);if(fd<0)return 0;
 struct kstat a,z;u8 extra=0;int ok=0;
 if(!ram(fd,0)||!stat_(fd,&a)||!regular(&a,0600)||a.size!=256||a.dev!=prepared_identity.dev||a.ino!=prepared_identity.ino)goto end;
 if(sc(63,fd,(long)plan,256,0)!=256||sc(63,fd,(long)&extra,1,0)||!stat_(fd,&z)||!stable(&a,&z)||!equal(plan+112,own_image_sha,32))goto end;ok=1;
end:if(sc(57,fd,0,0,0))ok=0;return ok;
}
static int close_once(long *fd,int why){
 if(*fd<0)return 1;long value=*fd;*fd=-1;if(sc(57,value,0,0,0))return error(why);return 1;
}
static int collect_same_call(long fd,long child,u8 done[256],int *exit_status){
 u64 begun=0,now=0;int got=0,reaped=0;if(!tick(&begun))return error(61);
 for(u32 attempt=0;attempt<100;++attempt){
  if(!within()||!tick(&now)||now<begun||now-begun>=2000000000ULL)return error(65);
  if(!got){int r=recv_packet(fd,child,2,done,1);if(r==1)got=1;else if(r!=2)return error(62);}
  if(!reaped){long r=sc(260,child,(long)exit_status,0xa0000001UL,0);if(r==child){reaped=1;if(*exit_status)return error(64);}else if(r<0)return error(63);}
  if(got&&reaped)return 1;
  struct {long sec,nsec;} pause={0,10000000};if(sc(101,(long)&pause,0,0,0))return error(66);
 }return error(65);
}
static void launch_and_collect(long root,long owner,const struct kstat *directory){
 int pair[2]={-1,-1};struct kstat sock,thread_stat;u64 oldmask=0,blocked=~((1ULL<<8)|(1ULL<<18)),allocation_span=0;int mask_set=0,observed=0,status=-1;long child=-1,thread=-1,allocation=-1,control=-1;u8 done[256];zero(done,256);
 state=E_HELD;reason=0;
 if(!write256(owner,"entry.pending",plan)){error(41);goto end;}
 thread=thread_anchor(&thread_stat);if(thread<0){error(42);goto end;}
 if(ipc_sc(199,1,0x80002,0,(long)pair,0,0)||!stat_(pair[0],&sock)||!socket_profile(pair[0],sc(172,0,0,0,0),0)){error(43);goto end;}
 control=pair[0];zero(record,256);copy(record,(const u8 *)"FX3ENTRYOWNv1",13);put32(record+16,1);put32(record+20,(u32)sc(172,0,0,0,0));put32(record+24,(u32)sc(178,0,0,0,0));put32(record+32,(u32)control);put32(record+36,1);put64(record+40,sock.dev);put64(record+48,sock.ino);copy(record+56,common,32);copy(record+88,plan+32,16);copy(record+104,plan+112,32);put64(record+136,directory->dev);put64(record+144,directory->ino);put64(record+152,get64(plan+144));put64(record+160,get64(plan+152));put32(record+168,(u32)thread);put64(record+176,thread_stat.dev);put64(record+184,thread_stat.ino);
 long entry=detached_image(&allocation,&allocation_span);if(!entry){error(44);goto end;}
 if(!within()||sc(135,2,(long)&blocked,(long)&oldmask,8)){error(45);goto end;}mask_set=1;
 child=((long (*)(long))entry)(pair[1]);
 /* Keep this creator thread's signal mask blocked continuously through
  * clone, GO and collection. No callback-return gap precedes wait4. */
 if(sc(215,allocation,allocation_span,0,0)){allocation=-1;error(47);goto end;}allocation=-1;
 if(child<=1||child>2147483647L){error(46);goto end;}put32(record+28,(u32)child);finish_crc(record);
 if(!write256(owner,"entry.owner",record)){error(48);goto end;}
 long other=pair[1];pair[1]=-1;if(sc(57,other,0,0,0)){error(49);goto end;}
 u8 go[256];packet(go,1,0);if(!within()||!send_packet(control,go)){error(50);goto end;}
 if(collect_same_call(control,child,done,&status)){
  if(close_once(&control,67)&&close_once(&thread,68))observed=1;
 }
end:
 if(allocation>=0){long value=allocation;allocation=-1;if(sc(215,value,allocation_span,0,0))error(73);}
 if(pair[1]>=0){long value=pair[1];pair[1]=-1;if(sc(57,value,0,0,0))error(74);}
 if(child<0){close_once(&control,75);close_once(&thread,76);}
 if(mask_set){if(sc(135,2,(long)&oldmask,0,8))error(69);mask_set=0;}
 if(observed&&reason==0){
  u8 result[256];zero(result,256);copy(result,(const u8 *)"FX3SINGLEOUTv1",14);put32(result+16,1);put32(result+20,1);put32(result+24,get32(record+20));put32(result+28,(u32)child);put32(result+32,(u32)status);hash(record,256,result+48);hash(done,256,result+80);copy(result+112,plan+32,16);copy(result+128,own_image_sha,32);put32(result+160,1);finish_crc(result);
  /* CHILD_EXIT_OBSERVED only. Final RAM-directory close/clock and USB
   * return are deliberately NOT certified by this stored record. */
  if(!write256(owner,"entry.single-result",result))error(70);
 }
 close_once(&owner,71);close_once(&root,72);
 if(observed&&reason==0){u64 now=0;if(!tick(&now)||now>=get64(plan+152))error(77);else state=E_OBSERVED;}
 /* An unfinished child/close remains HELD with sticky claims; no later
  * load is allowed to convert it into success, and no reset/retry exists. */
}
__attribute__((constructor)) static void fx3_module_init(void){
 prepare_fixed();if(state!=1)return;state=E_DENIED;reason=0;
 long root=-1,owner=-1;struct kstat s;
 root=sc(56,AT_FDCWD,(long)"/tmp_wbshd",DIR,0);
 if(root<0||!ram(root,65536)||!stat_(root,&s)||(s.mode&0170000)!=0040000||s.uid||((s.mode&022)&&!(s.mode&01000))||!read_prepared_plan(root)||!plan_valid())goto end;
 if(sc(34,root,(long)"fx3-singleload-owner-v1",0700,0)){error(31);goto end;}
 owner=sc(56,root,(long)"fx3-singleload-owner-v1",DIR,0);
 if(owner<0||!ram(owner,0)||!stat_(owner,&s)||(s.mode&0170000)!=0040000||s.uid||(s.mode&07777)!=0700){error(32);goto end;}
 launch_and_collect(root,owner,&s);root=owner=-1;
end:close_once(&owner,33);close_once(&root,34);
}
__attribute__((visibility("default"))) int fx3_single_state(void){return state;}
__attribute__((visibility("default"))) int fx3_single_reason(void){return reason;}
'''
source+=tail
source='/* Own single-load synthetic diagnostic: integrated preparation and\n * continuous creator-mask clone/exit collection, purpose1 NOOP only. */\n'+source
(H/'combined.c').open('x').write(source)
for name in ['core_support.inc','parent_ipc.inc']:(H/name).open('xb').write((P/name).read_bytes())
builder=(P/'prepare_build.py').read_text().replace("EXPORTS=('fx3_prepare_state','fx3_prepare_reason')","EXPORTS=('fx3_single_state','fx3_single_reason')")
builder=builder.replace("H/'prepare.c'","H/'combined.c'").replace("'prepare.c': '"+sha256((P/'prepare.c').read_bytes()).hexdigest()+"'","'combined.c': '"+sha256(source.encode()).hexdigest()+"'")
builder=builder.replace("MODULE_SHA='"+sha256((P/'prepare.c').read_bytes()).hexdigest()+"'","MODULE_SHA='"+sha256(source.encode()).hexdigest()+"'")
builder=builder.replace('FX3PREPCONFIGv1','FX3SINGLECFGv1').replace('expected_worker_sha256=WORKER_SHA,expected_worker_bytes=131864','reference_component_sha256=WORKER_SHA,reference_component_bytes=131864')
builder=builder.replace('child_identity_guard_implemented=False,no_child_lifecycle_in_this_component=True','child_identity_guard_implemented=True,no_child_lifecycle_in_this_component=False')
builder=builder.replace('prepare_only_no_child_source_USB_or_firmware_backend=True','single_constructor_own_NOOP_child_only=True,boot_source_USB_or_firmware_backend=False')
builder=builder.replace("role='own fixed synthetic RAM-plan preparation constructor'","role='own fixed synthetic single-load preparation and NOOP child/exit collector'")
builder=builder.replace('source_or_worker_execution_backend=False','source_execution_backend=False,own_NOOP_child_execution_implemented=True,same_constructor_continuous_creator_mask_implemented=True')
(H/'combined_build.py').open('x').write(builder)
(H/'source-assembly.json').open('x').write(json.dumps(dict(own_inputs=[dict(path=str((p/name).relative_to(R)),sha256=sha256((p/name).read_bytes()).hexdigest()) for p,name in [(P,'prepare.c'),(W,'entry.c'),(P,'prepare_build.py')]],combined_c_sha256=sha256(source.encode()).hexdigest(),builder_sha256=sha256(builder.encode()).hexdigest(),original_Sony_code_included=False,source_or_firmware_backend=False,actual_execution=False),indent=2)+'\n')
print(json.dumps(dict(status='OWN_SINGLE_LOAD_SOURCE_ASSEMBLED',C_bytes=len(source.encode()),source_sha256=sha256(source.encode()).hexdigest())))
