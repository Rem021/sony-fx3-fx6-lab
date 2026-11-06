/* Own no-argument factory bridge. No Sony execution, loader installation,
 * authentication or upload backend. Only explicit step() performs work.
 * Fixed RAM tasks and fingerprints are association, NOT user approval. */
#include "core_support.inc"
enum {G_TIME=45,G_BIND=49,G_EXPIRED=50};
#include "parent_ipc.inc"
static const char im_sha[]="5171f576d8b76cfbf15581389183b390c445bd6ff9dd97fd6668c5f64e77dc91";
static const char keeper_sha[]="93bcd77751550c7079a38dfe532272ecf71d849f906c4b05d5515267fa888581";
static const char worker_sha[]="349115672da2bc494e073472446004ee476c77ecc716756351cfe50a395b66e7";
static const char boot_profile[]="057dc79d9fe94348e2eb4cc7135db1824c8f97c65046dffe307b3b8568ce72c6";
enum {B_IDLE=0,B_RUNNING=1,B_HELD=2,B_DONE=3,B_DENIED=4,B_UNINITIALIZED=5};
static volatile u64 initialized;static int transition;
static struct {
 int state,started,phase,received,reaped,exit_ok,channel_owned,reason;
 long creator,child,channel,owner_fd;u32 count,completed;u64 deadline;
 struct kstat im_identity,owner_identity;
 u8 task[1536],task_sha[32],job[512];
} boot;
static int regular_root(const struct kstat *s){return (s->mode&0170000)==0100000&&!s->uid&&s->nlink==1&&!(s->mode&022);}
static int nonzero(const u8 *p,u32 n){u8 x=0;for(u32 i=0;i<n;++i)x|=p[i];return x!=0;}
static int identity(void){long p=sc(172,0,0,0,0);return p>1&&p<=2147483647L&&sc(178,0,0,0,0)==p&&!sc(174,0,0,0,0)&&!sc(175,0,0,0,0)&&(!boot.started||boot.creator==p);}
static int im_profile(int initial){
 long fd=sc(56,AT_FDCWD,(long)"/proc/self/exe",0x80000,0);if(fd<0)return 0;
 struct kstat a,z;int ok=0;if(!stat_(fd,&a)||!regular_root(&a)||a.size!=40920)goto done;
 if(!initial){ok=stable(&a,&boot.im_identity);goto done;}
 struct sha state;u8 buffer[4096],digest[32],extra=0;sha_init(&state);
 for(u32 left=40920;left;){u32 n=left>sizeof(buffer)?sizeof(buffer):left;if(sc(63,fd,(long)buffer,n,0)!=(long)n)goto done;sha_update(&state,buffer,n);left-=n;}
 sha_final(&state,digest);if(sc(63,fd,(long)&extra,1,0)||!hex_matches(digest,im_sha)||!stat_(fd,&z)||!stable(&a,&z))goto done;
 boot.im_identity=a;ok=1;
done:if(sc(57,fd,0,0,0))ok=0;return ok;
}
static int task_valid(void){
 static const u8 magic[16]="FX3BOOTPLANv1",req_magic[16]="FX3BOOTREQv1";
 const u8 *p=boot.task;u32 count=get32(p+20);u64 now=0,created=get64(p+184),deadline=get64(p+192);
 if(!equal(p,magic,16)||get32(p+16)!=1||count>8||get32(p+24)||get32(p+28)||!nonzero(p+32,16)||!nonzero(p+48,32)||!nonzero(p+80,32)||!hex_matches(p+112,keeper_sha)||!hex_matches(p+144,worker_sha)||get32(p+176)!=262144||get32(p+180)!=262144||get32(p+1532)!=(crc(0xffffffffu,p,1532)^0xffffffffu))return 0;
 if(!created||deadline<=created||deadline-created>900000000000ULL||!tick(&now)||now<created||now>=deadline)return 0;
 for(u32 i=200;i<256;++i)if(p[i])return 0;for(u32 i=256+count*128;i<1532;++i)if(p[i])return 0;
 for(u32 i=0;i<count;++i){
  const u8 *q=p+256+i*128;u32 role=get32(q+36),window=get32(q+40);u64 total=get64(q+48);
  if(!equal(q,req_magic,16)||!equal(q+16,p+32,16)||get32(q+32)!=1||role>1||window>3||get32(q+44)!=BLOCK||!hex_matches(q+56,boot_profile)||get32(q+88)!=3||get32(q+92)!=252||get32(q+96)!=126+role||get32(q+100)!=1||get32(q+124)!=(crc(0xffffffffu,q,124)^0xffffffffu))return 0;
  for(u32 j=104;j<124;++j)if(q[j])return 0;
  if((!total&&window)||(total&&(total<UNIT||total>MAX_TOTAL||total%UNIT||window*WINDOW>=total/BLOCK)))return 0;
  for(u32 j=0;j<i;++j){const u8 *old=p+256+j*128;if(get32(old+36)==role&&get32(old+40)==window)return 0;}
 }
 boot.count=count;boot.deadline=deadline;return 1;
}
static int load_task(long root){
 long fd=sc(56,root,(long)"fx3-bootstrap-plan-v1.bin",RD,0);if(fd<0)return 0;
 struct kstat a,z;u8 extra=0;int ok=0;
 if(!ram(fd,0)||!stat_(fd,&a)||!regular_root(&a)||(a.mode&07777)!=0600||a.size!=1536)goto done;
 if(sc(63,fd,(long)boot.task,1536,0)!=1536||sc(63,fd,(long)&extra,1,0)||!stat_(fd,&z)||!stable(&a,&z)||!task_valid())goto done;
 hash(boot.task,1536,boot.task_sha);ok=1;
done:if(sc(57,fd,0,0,0))ok=0;return ok;
}
static int pin_image(long root,const char *name,const char *digest,long *out,struct kstat *saved){
 long fd=sc(56,root,(long)name,RD,0);if(fd<0)return 0;
 struct kstat a,z;struct sha state;u8 buffer[4096],actual[32],extra=0;int ok=0;
 if(!ram(fd,0)||!stat_(fd,&a)||!regular_root(&a)||(a.mode&07777)!=0500||a.size!=262144)goto done;
 long flags=sc(25,fd,3,0,0);if(flags<0||(flags&3)||(flags&0x200000))goto done;
 sha_init(&state);for(u32 left=262144;left;left-=4096){if(sc(63,fd,(long)buffer,4096,0)!=4096)goto done;sha_update(&state,buffer,4096);}sha_final(&state,actual);
 if(sc(63,fd,(long)&extra,1,0)||!hex_matches(actual,digest)||!stat_(fd,&z)||!stable(&a,&z))goto done;
 *out=fd;*saved=a;ok=1;
done:if(!ok&&sc(57,fd,0,0,0))return 0;return ok;
}
static int held(int reason){boot.state=B_HELD;boot.reason=reason;return B_HELD;}
static int reserve_session(long root){
 if(sc(34,root,(long)"fx3-bootstrap-owner-v1",0700,0))return 0;
 boot.owner_fd=sc(56,root,(long)"fx3-bootstrap-owner-v1",DIR,0);boot.started=1;boot.creator=sc(172,0,0,0,0);
 if(boot.owner_fd<0||!ram(boot.owner_fd,0)||!stat_(boot.owner_fd,&boot.owner_identity)||(boot.owner_identity.mode&0170000)!=0040000||(boot.owner_identity.mode&07777)!=0700||boot.owner_identity.uid)return 0;
 long fd=sc(56,boot.owner_fd,(long)"bootstrap.pending",NEW,0600);if(fd<0)return 0;
 struct kstat a;u8 record[256];int ok=0;zero(record,sizeof(record));copy(record,(const u8 *)"FX3BOOTPENDv1",13);put32(record+16,1);put32(record+20,(u32)boot.creator);copy(record+32,boot.task_sha,32);copy(record+64,boot.task+48,32);put64(record+96,boot.deadline);put32(record+252,crc(0xffffffffu,record,252)^0xffffffffu);
 if(!ram(fd,0)||!stat_(fd,&a)||!regular_root(&a)||(a.mode&07777)!=0600||a.size)goto done;
 if(sc(64,fd,(long)record,256,0)!=256||sc(82,fd,0,0,0))goto done;ok=1;
done:if(sc(57,fd,0,0,0))ok=0;if(sc(82,boot.owner_fd,0,0,0)||!stat_(boot.owner_fd,&boot.owner_identity))ok=0;return ok;
}
#include "child_exec.inc"
static int channel(void){
 u32 type=0,len=4,peer[3]={0,0,0};u8 address[110];zero(address,sizeof(address));u32 size=sizeof(address);
 if(ipc_sc(209,boot.channel,1,3,(long)&type,(long)&len,0)||len!=4||type!=2)return 0;
 if(ipc_sc(204,boot.channel,(long)address,(long)&size,0,0,0)||size!=2||address[0]!=1||address[1])return 0;
 len=12;if(ipc_sc(209,boot.channel,1,17,(long)peer,(long)&len,0)||len!=12||peer[0]!=(u32)boot.creator||peer[1]||peer[2])return 0;
 u32 enabled=1;return !ipc_sc(208,boot.channel,1,16,(long)&enabled,4,0);
}
static int begin(void){
 long root=-1,image=-1,worker=-1;int pair[2]={-1,-1};struct kstat image_stat,worker_stat,s;int ok=0;
 if(!identity()||!im_profile(1))return B_DENIED;
 root=sc(56,AT_FDCWD,(long)"/tmp_wbshd",DIR,0);
 if(root<0||!ram(root,2097152)||!stat_(root,&s)||(s.mode&0170000)!=0040000||s.uid||((s.mode&022)&&!(s.mode&01000))||!load_task(root))goto done;
 if(!pin_image(root,"fx3-boot-keeper-226.elf",keeper_sha,&image,&image_stat)||!pin_image(root,"fx3-boot-worker-226.elf",worker_sha,&worker,&worker_stat))goto done;
 if(!reserve_session(root)){held(90);goto done;}
 if(ipc_sc(199,1,0x80002,0,(long)pair,0,0)){held(91);goto done;}
 long child=ipc_sc(220,17,0,0,0,0,0);if(!child)child_exec(image,root,pair[1],&image_stat);
 if(child<=1||child>2147483647L){held(92);goto done;}
 boot.child=child;boot.channel=pair[0];boot.channel_owned=1;boot.phase=0;boot.completed=0;boot.received=boot.reaped=boot.exit_ok=0;boot.state=B_RUNNING;
 if(!channel()){held(93);goto done;}ok=1;
done:
 if(pair[1]>=0&&sc(57,pair[1],0,0,0))ok=0;
 if(image>=0&&sc(57,image,0,0,0))ok=0;if(worker>=0&&sc(57,worker,0,0,0))ok=0;if(root>=0&&sc(57,root,0,0,0))ok=0;
 if(!ok&&boot.started)return held(94);return ok?B_RUNNING:B_DENIED;
}
static int make_job(void){
 u8 *p=boot.job;zero(p,512);copy(p,(const u8 *)"FX3KEEPJOBv1",12);put32(p+16,1);put32(p+20,boot.completed==boot.count?2:1);put32(p+28,boot.completed+1);copy(p+416,boot.task+112,32);copy(p+448,boot.task+144,32);
 if(boot.completed<boot.count){
  const u8 *req=boot.task+256+boot.completed*128;u8 *hand=p+32;u8 nonce_input[36];copy(nonce_input,boot.task+48,32);put32(nonce_input+32,boot.completed);hash(nonce_input,36,hand+32);
  copy(hand,(const u8 *)"FX3HANDOFFv2",12);copy(hand+16,boot.task+32,16);copy(hand+64,boot.task+80,32);hash(req,128,hand+96);put32(hand+132,(u32)boot.child);put32(hand+136,get32(req+36));put32(hand+140,get32(req+40));put32(hand+144,1);put32(hand+148,3);
  u64 now=0;if(!tick(&now)||now>=boot.deadline)return 0;u64 end=now+120000000000ULL;if(end>boot.deadline)end=boot.deadline;
  put64(hand+152,now);put64(hand+160,end);put64(hand+168,get64(req+48));put32(hand+176,get32(req+124));put32(hand+180,1);put32(hand+184,1);copy(hand+188,boot.task+112,32);put32(hand+220,262144);put32(hand+252,crc(0xffffffffu,hand,252)^0xffffffffu);copy(p+288,req,128);
 }
 put32(p+508,crc(0xffffffffu,p,508)^0xffffffffu);return 1;
}
static int send_job(void){
 if(!make_job())return 0;struct ipc_iov iov={boot.job,512};struct ipc_msg msg;zero((u8 *)&msg,sizeof(msg));msg.iov=&iov;msg.iovlen=1;
 if(ipc_sc(211,boot.channel,(long)&msg,0x4040,0,0,0)!=512)return 0;boot.phase=1;return 1;
}
#include "receive_result.inc"
static int result_valid(const u8 p[512]){
 static const u8 magic[16]="FX3KEEPRESv1";u8 digest[32];hash(boot.job,512,digest);
 if(!equal(p,magic,16)||get32(p+16)!=1||get32(p+20)!=get32(boot.job+20)||get32(p+24)||get32(p+28)!=boot.completed+1||get32(p+32)!=(u32)boot.child||get32(p+40)||get32(p+44)||!equal(p+96,digest,32)||!equal(p+128,boot.task+112,32)||get32(p+508)!=(crc(0xffffffffu,p,508)^0xffffffffu))return 0;
 for(u32 i=416;i<508;++i)if(p[i])return 0;
 if(boot.completed<boot.count){
  u8 expected[256];copy(expected,boot.job+32,256);if(get32(p+36)<=1)return 0;put32(expected+128,get32(p+36));put32(expected+252,crc(0xffffffffu,expected,252)^0xffffffffu);
  return equal(p+160,expected,256)&&equal(p+48,boot.task+32,16)&&equal(p+64,boot.job+64,32);
 }
 if(get32(p+36)||nonzero(p+48,48)||nonzero(p+160,256))return 0;return 1;
}
static int observe_exit(void){
 if(boot.reaped||boot.child<=1)return 1;int status=-1;long got=sc(260,boot.child,(long)&status,1,0);
 if(!got)return 1;if(got!=boot.child){held(97);return 0;}boot.reaped=1;boot.exit_ok=status==0;if(!boot.exit_ok)held(98);return 1;
}
static int poll(void){
 u64 now=0;struct kstat owner_now;
 if(!identity()||!im_profile(0)||!ram(boot.owner_fd,0)||!stat_(boot.owner_fd,&owner_now)||!stable(&owner_now,&boot.owner_identity)||!tick(&now)||now>=boot.deadline)held(95);
 if(boot.state==B_RUNNING&&boot.phase==0&&!send_job())held(96);
 if(boot.channel_owned){
  u8 packet[512];int rc=receive_result(packet);
  if(!rc){if(boot.state!=B_RUNNING||boot.phase!=1||!result_valid(packet))held(99);else if(boot.completed<boot.count){++boot.completed;boot.phase=0;}else{boot.received=1;boot.phase=2;}}
  else if(rc!=G_AGAIN&&!(rc==G_CHANNEL_CLOSED&&boot.received))held(100);
 }
 observe_exit();
 if(boot.state==B_RUNNING&&boot.received&&boot.reaped&&boot.exit_ok){
  u8 extra[512];int rc=receive_result(extra);if(rc!=G_AGAIN&&rc!=G_CHANNEL_CLOSED)return held(101);
  if(sc(57,boot.channel,0,0,0)){boot.channel_owned=0;return held(102);}boot.channel_owned=0;
  if(sc(57,boot.owner_fd,0,0,0))return held(103);boot.state=B_DONE;
 }
 return boot.state;
}
__attribute__((constructor)) static void fx3_module_init(void){initialized=0x465833424f4f5431ULL;}
__attribute__((visibility("default"))) int fx3_bootstrap_step(void){
 if(__atomic_exchange_n(&transition,1,__ATOMIC_ACQ_REL))return B_RUNNING;int result;
 if(initialized!=0x465833424f4f5431ULL)result=B_UNINITIALIZED;
 else if(boot.state==B_IDLE)result=begin();
 else if(boot.state==B_RUNNING||boot.state==B_HELD)result=poll();else result=boot.state;
 __atomic_store_n(&transition,0,__ATOMIC_RELEASE);return result;
}
__attribute__((visibility("default"))) int fx3_bootstrap_status(void){return initialized==0x465833424f4f5431ULL?boot.state:B_UNINITIALIZED;}
