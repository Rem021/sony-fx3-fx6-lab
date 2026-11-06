/* Own ARM64 parent-side arbiter core, explicitly called from a reference im
 * process context. Does not fork, exec, install, authenticate or upload.
 * Kernel metadata, wait4 and all sockets remain unverified on actual FX3. */
#include "core_support.inc"
enum { G_TIME=45,G_BIND=49,G_EXPIRED=50 };
#include "parent_ipc.inc"
enum { A_IDLE=0,A_RUNNING=1,A_HELD=2,A_DENIED=3,A_UNINITIALIZED=4 };
static const u8 hand_magic[16]="FX3HANDOFFv1",req_magic[16]="FX3BOOTREQv1";
static const char im_sha[]="5171f576d8b76cfbf15581389183b390c445bd6ff9dd97fd6668c5f64e77dc91";
static const char boot_profile[]="057dc79d9fe94348e2eb4cc7135db1824c8f97c65046dffe307b3b8568ce72c6";
static volatile u64 initialized;
static int transition;
static struct {
    int state,owner_started,phase,done,reaped,exit_ok,reason,close_attempted;
    long creator,owner_fd;
    u32 jobs;
    struct kstat directory;
    struct ipc_context gate;
} owner;
static int regular_root(const struct kstat *s){return (s->mode&0170000)==0100000&&!s->uid&&s->nlink==1&&!(s->mode&022);}
static int nonzero(const u8 *p,u32 n){u8 x=0;for(u32 i=0;i<n;++i)x|=p[i];return x!=0;}
static int identity(void){
    long pid=sc(172,0,0,0,0);
    return pid>1&&pid<=2147483647L&&sc(178,0,0,0,0)==pid&&!sc(174,0,0,0,0)&&!sc(175,0,0,0,0)&&(!owner.owner_started||owner.creator==pid);
}
static int im_profile(void){
    long fd=sc(56,AT_FDCWD,(long)"/proc/self/exe",0x80000,0);if(fd<0)return 0;
    int ok=0;struct kstat a,z;struct sha state;u8 digest[32],buffer[4096],extra=0;sha_init(&state);
    if(!stat_(fd,&a)||!regular_root(&a)||a.size!=40920)goto done;
    for(u32 left=40920;left;){u32 n=left>sizeof(buffer)?sizeof(buffer):left;if(sc(63,fd,(long)buffer,n,0)!=(long)n)goto done;sha_update(&state,buffer,n);left-=n;}
    sha_final(&state,digest);
    if(sc(63,fd,(long)&extra,1,0)||!stat_(fd,&z)||!stable(&a,&z)||!hex_matches(digest,im_sha))goto done;ok=1;
done:if(sc(57,fd,0,0,0))ok=0;return ok;
}
static int held(int reason){owner.state=A_HELD;owner.reason=reason;return A_HELD;}
static int namespace_stable(void){
    struct kstat s;
    return owner.owner_started&&ram(owner.owner_fd,0)&&stat_(owner.owner_fd,&s)&&stable(&s,&owner.directory);
}
static int reserve_session(const u8 hand[256]){
    if(owner.owner_started)return namespace_stable();
    long root=-1,file=-1;int ok=0;struct kstat s;
    root=sc(56,AT_FDCWD,(long)"/tmp_wbshd",DIR,0);
    if(root<0||!ram(root,2097152)||!stat_(root,&s)||(s.mode&0170000)!=0040000||s.uid||((s.mode&022)&&!(s.mode&01000)))goto done;
    /* Existing directory always blocks a new owner, regardless of any file
     * contents, PID disappearance or a previous owner's apparent success. */
    if(sc(34,root,(long)"fx3-boot-owner-session-v1",0700,0))goto done;
    owner.owner_fd=sc(56,root,(long)"fx3-boot-owner-session-v1",DIR,0);owner.owner_started=1;owner.creator=sc(172,0,0,0,0);
    if(owner.owner_fd<0||!ram(owner.owner_fd,0)||!stat_(owner.owner_fd,&s)||(s.mode&0170000)!=0040000||(s.mode&07777)!=0700||s.uid)goto done;
    file=sc(56,owner.owner_fd,(long)"owner-session.pending",NEW,0600);if(file<0)goto done;
    if(!ram(file,0)||!stat_(file,&s)||!regular_root(&s)||(s.mode&07777)!=0600||s.size)goto done;
    u8 record[256];zero(record,sizeof(record));copy(record,(const u8 *)"FX3OWNERPENDv1",14);put32(record+16,1);put32(record+20,(u32)owner.creator);copy(record+32,hand+32,32);hash(hand,256,record+64);put64(record+96,get64(hand+160));put32(record+252,crc(0xffffffffu,record,252)^0xffffffffu);
    if(sc(64,file,(long)record,sizeof(record),0)!=(long)sizeof(record)||sc(82,file,0,0,0))goto done;
    if(sc(57,file,0,0,0)){file=-1;goto done;}file=-1;
    if(sc(82,owner.owner_fd,0,0,0)||!stat_(owner.owner_fd,&owner.directory))goto done;ok=1;
done:
    if(file>=0&&sc(57,file,0,0,0))ok=0;
    if(root>=0&&sc(57,root,0,0,0))ok=0;
    return ok;
}
static int binding(const u8 hand[256],const u8 req[128],long child){
    if(!hand||!req||child<=1||child>2147483647L||child==sc(172,0,0,0,0))return 0;
    if(!equal(hand,hand_magic,16)||get32(hand+252)!=(crc(0xffffffffu,hand,252)^0xffffffffu)||!nonzero(hand+16,16)||!nonzero(hand+32,32)||!nonzero(hand+64,32))return 0;
    if(get32(hand+128)!=(u32)child||get32(hand+132)!=(u32)sc(172,0,0,0,0)||get32(hand+136)>1||get32(hand+140)>3||get32(hand+144)!=1||get32(hand+148)!=3||get32(hand+180)!=1||get32(hand+184)!=1)return 0;
    for(u32 i=188;i<252;++i)if(hand[i])return 0;
    u32 role=get32(req+36),window=get32(req+40);u64 total=get64(req+48);u8 digest[32];hash(req,128,digest);
    if(!equal(req,req_magic,16)||!equal(req+16,hand+16,16)||get32(req+32)!=1||role>1||window>3||get32(req+44)!=BLOCK||!hex_matches(req+56,boot_profile)||get32(req+88)!=3||get32(req+92)!=252||get32(req+96)!=126+role||get32(req+100)!=1||get32(req+124)!=(crc(0xffffffffu,req,124)^0xffffffffu))return 0;
    for(u32 i=104;i<124;++i)if(req[i])return 0;
    if((!total&&window)||(total&&(total<UNIT||total>MAX_TOTAL||total%UNIT||window*WINDOW>=total/BLOCK)))return 0;
    if(!equal(digest,hand+96,32)||role!=get32(hand+136)||window!=get32(hand+140)||total!=get64(hand+168)||get32(req+124)!=get32(hand+176))return 0;
    u64 now=0;return ipc_clock(hand,&now);
}
static int channel(void){
    struct ipc_context *gate=&owner.gate;struct kstat s;u32 type=0,len=4,peer[3]={0,0,0};u8 address[110];zero(address,sizeof(address));u32 size=sizeof(address);
    if(!stat_(gate->fd,&s)||(s.mode&0170000)!=0140000||s.uid)return 0;
    if(ipc_sc(209,gate->fd,1,3,(long)&type,(long)&len,0)||len!=4||type!=2)return 0;
    if(ipc_sc(204,gate->fd,(long)address,(long)&size,0,0,0)||size!=2||address[0]!=1||address[1])return 0;
    /* socketpair was created by this reference-parent process. Per-message
     * credentials, not SO_PEERCRED, must identify the subsequently forked child. */
    len=12;if(ipc_sc(209,gate->fd,1,17,(long)peer,(long)&len,0)||len!=12||peer[0]!=(u32)owner.creator||peer[1]||peer[2])return 0;
    gate->owned=1;u32 enabled=1;return !ipc_sc(208,gate->fd,1,16,(long)&enabled,4,0);
}
static void observe_child(void){
    if(owner.reaped||owner.gate.child<=1)return;
    int status=-1;long pid=sc(260,owner.gate.child,(long)&status,1,0);
    if(pid==0)return;
    if(pid!=owner.gate.child){held(70);return;}
    owner.reaped=1;owner.exit_ok=status==0;
    if(!owner.exit_ok)held(71);
}
__attribute__((constructor)) static void fx3_module_init(void){initialized=0x4658335041523031ULL;}
__attribute__((visibility("default"))) int fx3_arbiter_submit(const u8 hand[256],const u8 req[128],long child,long fd){
    if(__atomic_exchange_n(&transition,1,__ATOMIC_ACQ_REL))return A_RUNNING;
    int result=A_HELD;
    if(initialized!=0x4658335041523031ULL){result=A_UNINITIALIZED;goto done;}
    if(owner.state==A_HELD)goto done;
    if(owner.state==A_RUNNING){result=A_RUNNING;goto done;}
    u8 bound_hand[256],bound_req[128];
    if(!hand||!req){held(72);goto done;}copy(bound_hand,hand,256);copy(bound_req,req,128);hand=bound_hand;req=bound_req;
    if(fd!=199||!identity()||!im_profile()||!binding(hand,req,child)||owner.jobs>=1024){held(72);goto done;}
    if(!reserve_session(hand)){held(73);goto done;}
    copy(owner.gate.hand,hand,256);owner.gate.fd=fd;owner.gate.child=child;owner.gate.owned=0;
    owner.phase=1;owner.done=owner.reaped=owner.exit_ok=owner.close_attempted=0;
    if(!channel()){held(74);goto done;}
    observe_child();if(owner.state==A_HELD||owner.reaped){held(75);goto done;}
    if(ipc_send(&owner.gate,1,0)){held(76);goto done;}
    ++owner.jobs;owner.state=A_RUNNING;result=A_RUNNING;
done:__atomic_store_n(&transition,0,__ATOMIC_RELEASE);return result;
}
__attribute__((visibility("default"))) int fx3_arbiter_poll(void){
    if(__atomic_exchange_n(&transition,1,__ATOMIC_ACQ_REL))return A_RUNNING;
    int result=A_HELD;
    if(initialized!=0x4658335041523031ULL){result=A_UNINITIALIZED;goto done;}
    if(owner.state==A_IDLE){result=A_IDLE;goto done;}
    u64 now=0;
    if(!identity()||!namespace_stable()||!ipc_clock(owner.gate.hand,&now))held(77);
    /* Held owners still observe the ORIGINAL child/channel, but never send GO
     * or turn an eventual exit into IDLE. No reset or stale-owner deletion. */
    if(owner.gate.owned){
        u8 packet[320];int rc=ipc_recv(&owner.gate,packet,owner.phase==1?2:4);
        if(!rc){
            if(owner.state==A_RUNNING&&owner.phase==1){
                if(ipc_send(&owner.gate,3,0))held(78);else owner.phase=2;
            }else if(owner.phase==2&&!owner.done){
                if(get32(packet+24))held(79);else owner.done=1;
            }else held(80);
        }else if(rc!=G_AGAIN&&!(rc==G_CHANNEL_CLOSED&&owner.done))held(81);
    }
    observe_child();
    if(owner.state==A_RUNNING&&owner.done&&owner.reaped&&owner.exit_ok){
        /* No duplicate/extra datagram may hide behind a successful DONE. */
        u8 extra[320];int rc=ipc_recv(&owner.gate,extra,4);
        if(rc!=G_AGAIN&&rc!=G_CHANNEL_CLOSED){held(82);goto finish;}
        now=0;if(!ipc_clock(owner.gate.hand,&now)||!namespace_stable()){held(83);goto finish;}
        owner.close_attempted=1;
        if(sc(57,owner.gate.fd,0,0,0)){owner.gate.owned=0;held(84);goto finish;}
        owner.gate.owned=0;owner.phase=0;owner.state=A_IDLE;
    }
finish:result=owner.state;
done:__atomic_store_n(&transition,0,__ATOMIC_RELEASE);return result;
}
