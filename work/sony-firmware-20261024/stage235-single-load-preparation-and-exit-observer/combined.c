/* Own single-load synthetic diagnostic: integrated preparation and
 * continuous creator-mask clone/exit collection, purpose1 NOOP only. */
/* Own fixed RAM-plan preparation component, no worker/source/USB backend.
 * Embedded associations and normalized-image checks are NOT authorization
 * or live-body attestation. This build is an offline synthetic candidate. */
#include "core_support.inc"
#include "parent_ipc.inc"
extern const u8 __fx3_elf_base[] __attribute__((visibility("hidden")));
enum {E_START=1,E_HELD=2,E_OBSERVED=3,E_DENIED=4};
static int state,reason;
static u8 plan[256],record[256],common[32],own_image_sha[32],prepared_plan_sha[32];
static struct kstat prepared_identity;
static const char im_sha[]="5171f576d8b76cfbf15581389183b390c445bd6ff9dd97fd6668c5f64e77dc91";
static const char worker_sha[]="c711f6ab13666c45249cc255d2ab09ec283496214d8941d11b9f1569124c47ec";
static int error(int code){state=2;reason=code;return 0;}
static int nonzero(const u8 *p,u32 n){u8 v=0;for(u32 i=0;i<n;++i)v|=p[i];return v!=0;}
static int regular(const struct kstat *s,u32 mode){return (s->mode&0170000)==0100000&&!s->uid&&s->nlink==1&&(s->mode&07777)==mode;}
static void finish_crc(u8 *p){put32(p+252,crc(0xffffffffu,p,252)^0xffffffffu);}
static int config_valid(void){
 const u8 *p=__fx3_elf_base+4096;static const u8 magic[16]="FX3SINGLECFGv1";
 if(!equal(p,magic,16)||get32(p+16)!=1||get32(p+20)!=1||get32(p+24)!=1||get32(p+28)!=1||!nonzero(p+32,16)||!nonzero(p+48,32)||!nonzero(p+80,32)||!hex_matches(p+112,worker_sha)||get64(p+152)!=131864||get32(p+160)!=1)return 0;
 if(!get64(p+144)||get64(p+144)>900000000000ULL||get32(p+252)!=(crc(0xffffffffu,p,252)^0xffffffffu))return 0;
 for(u32 i=164;i<252;++i)if(p[i])return 0;return nonzero(__fx3_elf_base+4352,32);
}
static int parent_identity(void){
 long pid=sc(172,0,0,0,0),tid=sc(178,0,0,0,0);if(pid<=1||pid>2147483647L||tid<=1||tid>2147483647L||sc(174,0,0,0,0)||sc(175,0,0,0,0))return 0;
 long fd=sc(56,AT_FDCWD,(long)"/proc/self/exe",0x80000,0);if(fd<0)return 0;struct kstat a,z;struct sha s;u8 buf[4096],out[32],extra=0;int ok=0;
 if(!stat_(fd,&a)||(a.mode&0170000)!=0100000||a.uid||a.nlink!=1||a.size!=40920)goto end;
 sha_init(&s);for(u32 left=40920;left;){u32 n=left>4096?4096:left;if(sc(63,fd,(long)buf,n,0)!=(long)n)goto end;sha_update(&s,buf,n);left-=n;}
 sha_final(&s,out);if(sc(63,fd,(long)&extra,1,0)||!hex_matches(out,im_sha)||!stat_(fd,&z)||!stable(&a,&z))goto end;ok=1;
end:if(sc(57,fd,0,0,0))ok=0;return ok;
}
static int image_profile(u8 full_sha[32]){
 const u8 *base=__fx3_elf_base;long fd=sc(56,AT_FDCWD,(long)"/tmp/jiritsu/libJit.so",RD,0);if(fd<0)return 0;
 struct kstat a,z;struct sha full,norm;u8 buf[4096],out[32],extra=0;int ok=0;
 if(!stat_(fd,&a)||(a.mode&0170000)!=0100000||a.uid||a.nlink!=1||a.size<32768||a.size>262144)goto end;
 if(get32(base)!=0x464c457f||get64(base+32)!=64||base[54]!=56||base[55]||base[56]!=8||base[57])goto end;
 sha_init(&full);sha_init(&norm);
 for(u32 at=0;at<(u32)a.size;){u32 n=(u32)a.size-at;if(n>4096)n=4096;if(sc(63,fd,(long)buf,n,0)!=(long)n)goto end;sha_update(&full,buf,n);
  for(u32 i=0;i<3;++i){const u8 *p=base+64+56*i;u64 off=get64(p+8),va=get64(p+16),size=get64(p+32);u32 flags=get32(p+4);
   if(get32(p)!=1||flags!=(i==1?5u:4u)||off!=(u64)i*32768||va!=off||!size||size>32768)goto end;
   for(u32 j=0;j<n;++j)if((u64)at+j>=off&&(u64)at+j<off+size&&buf[j]!=base[va+(u64)at+j-off])goto end;
  }
  for(u32 j=0;j<n;++j)if(at+j>=4352&&at+j<4384)buf[j]=0;
  sha_update(&norm,buf,n);at+=n;
 }
 sha_final(&full,full_sha);sha_final(&norm,out);if(!equal(out,base+4352,32)||sc(63,fd,(long)&extra,1,0)||!stat_(fd,&z)||!stable(&a,&z))goto end;ok=1;
end:if(sc(57,fd,0,0,0))ok=0;return ok;
}
static int store(long directory,const char *name,const u8 data[256],struct kstat *saved){
 long fd=sc(56,directory,(long)name,(NEW&~3)|2,0600);if(fd<0)return 0;struct kstat a,z;u8 got[256],extra=0;int ok=0;
 if(!ram(fd,0)||!stat_(fd,&a)||!regular(&a,0600)||a.size)goto end;
 if(sc(64,fd,(long)data,256,0)!=256||sc(82,fd,0,0,0)||!stat_(fd,&a)||!regular(&a,0600)||a.size!=256)goto end;
 if(sc(62,fd,0,0,0)!=0||sc(63,fd,(long)got,256,0)!=256||sc(63,fd,(long)&extra,1,0)||!equal(got,data,256)||!stat_(fd,&z)||!stable(&a,&z))goto end;if(saved)copy((u8 *)saved,(u8 *)&z,sizeof(z));ok=1;
end:if(sc(57,fd,0,0,0))ok=0;return ok;
}
static int verify_plan(long root,const u8 plan[256],const struct kstat *saved){
 long fd=sc(56,root,(long)"fx3-entry-plan-v1.bin",RD,0);if(fd<0)return 0;struct kstat a,z;u8 got[256],extra=0;int ok=0;
 if(!ram(fd,0)||!stat_(fd,&a)||!regular(&a,0600)||a.size!=256||a.dev!=saved->dev||a.ino!=saved->ino)goto end;
 if(sc(63,fd,(long)got,256,0)!=256||sc(63,fd,(long)&extra,1,0)||!equal(got,plan,256)||!stat_(fd,&z)||!stable(&a,&z))goto end;ok=1;
end:if(sc(57,fd,0,0,0))ok=0;return ok;
}
static int crc_ok(const u8 *p){return get32(p+252)==(crc(0xffffffffu,p,252)^0xffffffffu);}
static void prepare_fixed(void){
 state=4;reason=0;int published_checked=0;long root=-1,claim=-1;struct kstat s,pending;u8 own_sha[32],plan[256],report[256];u64 begun=0,now=0;
 if(!parent_identity()||!config_valid()||!image_profile(own_sha))return;
 root=sc(56,AT_FDCWD,(long)"/tmp_wbshd",DIR,0);
 if(root<0||!ram(root,65536)||!stat_(root,&s)||(s.mode&0170000)!=0040000||s.uid||((s.mode&022)&&!(s.mode&01000))){error(10);goto end;}
 if(sc(34,root,(long)"fx3-plan-preparation-v1",0700,0)){error(11);goto end;}
 claim=sc(56,root,(long)"fx3-plan-preparation-v1",DIR,0);
 if(claim<0||!ram(claim,0)||!stat_(claim,&s)||(s.mode&0170000)!=0040000||s.uid||(s.mode&07777)!=0700){error(12);goto end;}
 if(!tick(&begun)){error(13);goto end;}
 const u8 *cfg=__fx3_elf_base+4096;u64 ttl=get64(cfg+144);if(begun>~0ULL-ttl){error(13);goto end;}
 zero(plan,256);copy(plan,(const u8 *)"FX3ENTRYPLANv1",14);put32(plan+16,1);put32(plan+20,1);put32(plan+24,1);copy(plan+32,cfg+32,112);copy(plan+112,own_sha,32);put64(plan+144,begun);put64(plan+152,begun+ttl);put32(plan+160,1);finish_crc(plan);
 if(!store(claim,"plan.pending",plan,&pending)){error(14);goto end;}
 /* STAGED receipt is written BEFORE publish. It is never a release/cleanup,
  * camera identity, execution approval, worker completion or USB receipt. */
 zero(report,256);copy(report,(const u8 *)"FX3PREPSTAGED1",14);put32(report+16,1);put32(report+20,1);put32(report+24,(u32)sc(172,0,0,0,0));put32(report+28,(u32)sc(178,0,0,0,0));copy(report+32,cfg+32,16);copy(report+48,own_sha,32);hash(plan,256,report+80);copy(report+112,own_sha,32);put64(report+144,begun);put64(report+152,begun+ttl);hash(cfg,256,report+160);put32(report+192,1);put64(report+200,pending.dev);put64(report+208,pending.ino);finish_crc(report);
 if(!store(claim,"prepare.staged",report,0)){error(15);goto end;}
 now=begun;if(!tick(&now)||now>=begun+ttl){error(16);goto end;}
 /* renameat2 RENAME_NOREPLACE, never plain rename or overwrite fallback. */
 if(ipc_sc(276,claim,(long)"plan.pending",root,(long)"fx3-entry-plan-v1.bin",1,0)){error(17);goto end;}
 if(!verify_plan(root,plan,&pending)){error(18);goto end;}published_checked=1;
end:
 if(claim>=0&&sc(57,claim,0,0,0))error(19);
 if(root>=0&&sc(57,root,0,0,0))error(20);
 if(published_checked&&state!=2){if(!tick(&now)||now>=begun+ttl)error(21);else{copy(own_image_sha,own_sha,32);hash(plan,256,prepared_plan_sha);copy((u8 *)&prepared_identity,(u8 *)&pending,sizeof(pending));state=1;}}
 /* Keep claims, partial staging and any published plan on error. No unlink,
  * chmod, retry, child launch, device access or replacement is permitted. */
}

static int write256(long dir,const char *name,const u8 *p){
 long fd=sc(56,dir,(long)name,NEW,0600);if(fd<0)return 0;struct kstat s;int ok=0;
 if(ram(fd,0)&&stat_(fd,&s)&&regular(&s,0600)&&!s.size&&sc(64,fd,(long)p,256,0)==256&&!sc(82,fd,0,0,0))ok=1;
 if(sc(57,fd,0,0,0))ok=0;return ok;
}
static int within(void){u64 now=0;return tick(&now)&&now>=get64(plan+144)&&now<get64(plan+152);}
static int plan_valid(void){
 static const u8 magic[16]="FX3ENTRYPLANv1";u64 now=0;
 if(!equal(plan,magic,16)||get32(plan+16)!=1||get32(plan+20)!=1||get32(plan+24)!=1||get32(plan+28)||!crc_ok(plan))return 0;
 if(!nonzero(plan+32,16)||!nonzero(plan+48,32)||!nonzero(plan+80,32)||!nonzero(plan+112,32)||get32(plan+160)!=1)return 0;
 for(u32 i=164;i<252;++i)if(plan[i])return 0;
 u64 a=get64(plan+144),z=get64(plan+152);if(!a||z<=a||z-a>900000000000ULL||!tick(&now)||now<a||(get32(plan+20)==1&&now>=z))return 0;
 hash(plan+24,228,common);return 1;
}
static int proc_directory(long fd,struct kstat *s){
 u64 fs[32];zero((u8 *)fs,sizeof(fs));return !sc(44,fd,(long)fs,0,0)&&fs[0]==0x9fa0&&stat_(fd,s)&&(s->mode&0170000)==0040000&&!s->uid;
}
static long thread_anchor(struct kstat *s){
 u8 name[64],digits[16];zero(name,sizeof(name));copy(name,(const u8 *)"/proc/self/task/",16);u32 n=0;long tid=sc(178,0,0,0,0);if(tid<=1||tid>2147483647L)return -1;
 for(u32 v=(u32)tid;v;v/=10)digits[n++]=(u8)('0'+v%10);for(u32 i=0;i<n;++i)name[16+i]=digits[n-i-1];
 long fd=sc(56,AT_FDCWD,(long)name,DIR,0);if(fd<0)return -1;if(proc_directory(fd,s))return fd;sc(57,fd,0,0,0);return -1;
}
static int socket_profile(long fd,long creator,const struct kstat *expected){
 struct kstat s;u32 type=0,size=4,peer[3]={0,0,0};u8 addr[110];u32 len=110;zero(addr,sizeof(addr));
 if(!stat_(fd,&s)||(s.mode&0170000)!=0140000||s.uid||(expected&&(s.dev!=expected->dev||s.ino!=expected->ino)))return 0;
 if(ipc_sc(209,fd,1,3,(long)&type,(long)&size,0)||size!=4||type!=2)return 0;
 if(ipc_sc(204,fd,(long)addr,(long)&len,0,0,0)||len!=2||addr[0]!=1||addr[1])return 0;
 size=12;if(ipc_sc(209,fd,1,17,(long)peer,(long)&size,0)||size!=12||peer[0]!=(u32)creator||peer[1]||peer[2])return 0;
 u32 enabled=1;return !ipc_sc(208,fd,1,16,(long)&enabled,4,0);
}
static void packet(u8 *p,u32 type,u32 result){
 zero(p,256);copy(p,(const u8 *)"FX3ENTRYIPC1",12);put32(p+16,1);put32(p+20,type);put32(p+24,get32(record+20));put32(p+28,get32(record+28));copy(p+32,plan+32,16);copy(p+48,common,32);copy(p+80,plan+112,32);put32(p+112,get32(record+252));put32(p+116,result);finish_crc(p);
}
static int send_packet(long fd,const u8 *p){
 volatile struct ipc_iov v;v.base=(void *)p;v.size=256;struct ipc_msg m;zero((u8 *)&m,sizeof(m));m.iov=(struct ipc_iov *)&v;m.iovlen=1;return ipc_sc(211,fd,(long)&m,0x4000,0,0,0)==256;
}
static int recv_packet(long fd,long sender,u32 type,u8 *out,int nonblock){
 volatile struct ipc_iov v;v.base=out;v.size=256;u8 control[128];zero(control,sizeof(control));struct ipc_msg m;zero((u8 *)&m,sizeof(m));m.iov=(struct ipc_iov *)&v;m.iovlen=1;m.control=control;m.controllen=sizeof(control);
 long n=ipc_sc(212,fd,(long)&m,0x40000000|(nonblock?64:0),0,0,0);if(n==-11)return 2;if(n<0||m.controllen>sizeof(control))return 0;
 u32 creds=0;int bad=n!=256||(m.flags&0x28);for(u64 at=0;at<m.controllen;){if(m.controllen-at<16)return 0;u64 len=get64(control+at);u32 level=get32(control+at+8),kind=get32(control+at+12);if(len<16||len>m.controllen-at)return 0;
  if(level==1&&kind==2&&len==28){if(++creds!=1||get32(control+at+16)!=(u32)sender||get32(control+at+20)||get32(control+at+24))bad=1;}
  else{bad=1;if(level==1&&kind==1&&len>=20&&(len-16)%4==0)for(u64 j=16;j<len;j+=4)if(sc(57,get32(control+at+j),0,0,0))bad=1;}
  u64 next=(len+7)&~7ULL;if(next>m.controllen-at)return 0;at+=next;
 }
 u8 wanted[256];packet(wanted,type,0);return !bad&&creds==1&&equal(out,wanted,256);
}
static int close_inherited(long keep){
 long scan=sc(56,AT_FDCWD,(long)"/proc/self/fd",DIR,0);if(scan<0||scan==keep)return 0;u8 buf[1024];int ok=1;
 for(u32 round=0;round<1024;++round){long n=sc(61,scan,(long)buf,sizeof(buf),0);if(n<0){ok=0;break;}if(!n)break;
  for(long at=0;at<n;){if(n-at<20){ok=0;break;}u32 len=(u32)buf[at+16]|(u32)buf[at+17]<<8;if(len<20||len>(u32)(n-at)){ok=0;break;}u32 j=19;u64 value=0;int digit=0,valid=1;
   if(buf[at+j]=='.'){at+=len;continue;}
   while(j<len&&buf[at+j]){u8 c=buf[at+j++];if(c<'0'||c>'9'||value>214748364ULL){valid=0;break;}value=value*10+c-'0';digit=1;}
   if(!valid||!digit||j==len||value>2147483647ULL){ok=0;break;}
   if((long)value!=scan&&(long)value!=keep&&sc(57,(long)value,0,0,0)){ok=0;break;}at+=len;
  }if(!ok)break;if(round==1023)ok=0;
 }if(sc(57,scan,0,0,0))ok=0;return ok;
}
static int await_grant(long fd,u8 *p){
 u64 begun=0,now=0;if(!tick(&begun))return 0;
 for(u32 attempt=0;attempt<100;++attempt){
  if(!within()||!tick(&now)||now<begun||now-begun>=2000000000ULL)return 0;
  int got=recv_packet(fd,get32(record+20),1,p,1);if(got==1)return 1;if(got!=2)return 0;
  struct {long sec,nsec;} pause={0,10000000};if(sc(101,(long)&pause,0,0,0))return 0;
 }return 0;
}
static void child_exit(int code){sc(93,code,0,0,0);for(;;){}}
static void child_run(long fd){
 long pid=sc(172,0,0,0,0);if(pid<=1||sc(178,0,0,0,0)!=pid||sc(173,0,0,0,0)!=(long)get32(record+20)||sc(174,0,0,0,0)||sc(175,0,0,0,0))child_exit(61);
 put32(record+28,(u32)pid);finish_crc(record);
 if(!close_inherited(fd))child_exit(62);
 /* All blockable signals were blocked in the launching thread before clone.
  * Change dispositions ONLY in this new, non-CLONE_SIGHAND process. */
 for(long sig=1;sig<=64;++sig){if(sig==9||sig==19)continue;u64 action[4]={0,0,0,0},seen[4]={1,1,1,1};if(sc(134,sig,(long)action,0,8)||sc(134,sig,0,(long)seen,8)||!equal((u8 *)action,(u8 *)seen,32))child_exit(63);}
 u64 mask=0;if(sc(135,2,(long)&mask,0,8))child_exit(64);
 if(!socket_profile(fd,get32(record+20),0))child_exit(65);
 u8 p[256];if(!await_grant(fd,p))child_exit(70);if(!within())child_exit(69);
 /* Purpose1 is deliberately only the lifecycle diagnostic. No source read. */
 packet(p,2,0);if(!send_packet(fd,p))child_exit(67);
 if(sc(57,fd,0,0,0))child_exit(68);child_exit(0);
}
static long clone_dispatch(long fd){
 long child=ipc_sc(220,0,0,0,0,0,0);if(!child)child_run(fd);return child;
}
static long detached_image(long *allocation,u64 *span){
 /* Enter clone itself from anonymous code: even a child that has never been
  * scheduled must not resume in the file-backed caller after the next write
  * truncates libJit.so. Only this fixed own PIC image can be copied here. */
 const u8 *old=__fx3_elf_base;u64 size=6*32768ULL;long raw=ipc_sc(222,0,size,3,0x22,-1,0);if(raw<0)return 0;
 *allocation=raw;*span=size;u8 *base=(u8 *)(((u64)raw+32767)&~32767ULL);
 for(u32 i=0;i<5;++i){const u8 *p=old+64+i*56;u64 va=get64(p+16),n=get64(p+40);if(get32(p)!=1||va!=(u64)i*32768||!n||n>32768)return 0;copy(base+va,old+va,(u32)n);}
 u64 init=get64(old+3*32768);if(init<(u64)old+32768||init>=(u64)old+2*32768)return 0;put64(base+3*32768,(u64)base+init-(u64)old);
 if(sc(226,raw,size,0,0))return 0;
 for(u32 i=0;i<5;++i){u32 flags=get32(old+64+i*56+4);u32 prot=(flags&4?1:0)|(flags&2?2:0)|(flags&1?4:0);if((prot&6)==6||sc(226,(long)(base+i*32768),32768,prot,0))return 0;}
 u64 offset=(u64)(long)&clone_dispatch-(u64)old;if(offset<32768||offset>=65536)return 0;
 /* Fresh anonymous pages receive executable permission once. Actual Sony
  * cache/coherency behavior is an explicit unresolved on-device condition. */
 return (long)(base+offset);
}

/* Full preparation -> exact source object -> same-constructor launch.
 * No later-load observer or mode2 path exists in this component. */
static int read_prepared_plan(long root){
 long fd=sc(56,root,(long)"fx3-entry-plan-v1.bin",RD,0);if(fd<0)return 0;
 struct kstat a,z;u8 extra=0;int ok=0;
 if(!ram(fd,0)||!stat_(fd,&a)||!regular(&a,0600)||a.size!=256||a.dev!=prepared_identity.dev||a.ino!=prepared_identity.ino)goto end;
 if(sc(63,fd,(long)plan,256,0)!=256||sc(63,fd,(long)&extra,1,0)||!stat_(fd,&z)||!stable(&a,&z)||!equal(plan+112,own_image_sha,32))goto end;
 u8 digest[32];hash(plan,256,digest);if(!equal(digest,prepared_plan_sha,32))goto end;ok=1;
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
 if(ipc_sc(199,1,0x80002,0,(long)pair,0,0)){error(43);goto end;}control=pair[0];
 if(!stat_(control,&sock)||!socket_profile(control,sc(172,0,0,0,0),0)){error(43);goto end;}
 zero(record,256);copy(record,(const u8 *)"FX3ENTRYOWNv1",13);put32(record+16,1);put32(record+20,(u32)sc(172,0,0,0,0));put32(record+24,(u32)sc(178,0,0,0,0));put32(record+28,0);put32(record+32,(u32)control);put32(record+36,1);put64(record+40,sock.dev);put64(record+48,sock.ino);copy(record+56,common,32);copy(record+88,plan+32,16);copy(record+104,plan+112,32);put64(record+136,directory->dev);put64(record+144,directory->ino);put64(record+152,get64(plan+144));put64(record+160,get64(plan+152));put32(record+168,(u32)thread);put64(record+176,thread_stat.dev);put64(record+184,thread_stat.ino);
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
