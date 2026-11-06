/* Own static ELF child; explicit _start, no Sony code or loader. */
struct child_roles {long image,job,socket,parent_image;};
static struct child_roles roles;
#include "inner_boot_reader.c"
static int guard_used;
static struct kstat parent_identity;
enum { G_REPLAY=40,G_ID=41,G_CMD=42,G_SELF=43,G_PARENT=44,G_TIME=45,G_CLOSE=46,G_INIT=47 };
static int g_close(long fd,int result){return sc(57,fd,0,0,0)?G_CLOSE:result;}
static int g_regular(const struct kstat *s){return (s->mode&0170000)==0100000&&!s->uid&&s->nlink==1&&!(s->mode&022);}
#include "roles_and_image.inc"
/* /proc/<pid>/exe magic links are deliberately followed to the executable
 * backing file. This does not read or attest all mapped process memory.
 */
static int g_recheck(const char *path,const struct kstat *saved,int failure){
    long fd=sc(56,AT_FDCWD,(long)path,0x80000,0);if(fd<0)return failure;
    struct kstat now;int result=stat_(fd,&now)&&g_regular(&now)&&stable(saved,&now)?0:failure;
    return g_close(fd,result);
}
static int g_parent_path(char out[32],long parent){
    if(parent<=1||parent>2147483647L)return 0;
    const char prefix[]="/proc/";u32 at=0;while(prefix[at]){out[at]=prefix[at];++at;}
    char number[10];u32 count=0;while(parent){number[count++]=(char)('0'+parent%10);parent/=10;}
    while(count)out[at++]=number[--count];const char tail[]="/exe";for(u32 i=0;i<sizeof(tail);++i)out[at++]=tail[i];return 1;
}
#include "parent_image.inc"
static int g_filter(void){
    long pid=sc(172,0,0,0,0),parent=sc(173,0,0,0,0),tid=sc(178,0,0,0,0);
    if(sc(174,0,0,0,0)||sc(175,0,0,0,0)||pid<=1||pid>2147483647L||tid!=pid||parent<=1||parent==pid)return G_ID;
    char parent_path[32];if(!g_parent_path(parent_path,parent))return G_ID;
    u64 now=0;if(!tick(&now))return G_TIME;u64 deadline=now+10000000000ULL;
    int result=g_arguments();if(result)return result;
    if(!tick(&now)||now>=deadline)return G_TIME;
    struct kstat self;
    result=g_self_image(&self);if(result)return result;
    if(!tick(&now)||now>=deadline)return G_TIME;
    result=g_parent_selected(parent_path);if(result)return result;
    if(!tick(&now)||now>=deadline)return G_TIME;
    if(sc(172,0,0,0,0)!=pid||sc(178,0,0,0,0)!=pid||sc(173,0,0,0,0)!=parent||sc(174,0,0,0,0)||sc(175,0,0,0,0))return G_ID;
    result=g_recheck("/proc/self/exe",&self,G_SELF);if(result)return result;
    result=g_recheck(parent_path,&parent_identity,G_PARENT);if(result)return result;
    if(!tick(&now)||now>=deadline)return G_TIME;
    return 0;
}
#include "handoff_impl.inc"
#include "ipc_gate.inc"
__attribute__((visibility("default"))) int fx3_boot_read_window(void){
    if(__atomic_exchange_n(&guard_used,1,__ATOMIC_ACQ_REL))return G_REPLAY;
    int result=g_filter();if(result)return result;
    struct ipc_context gate;zero((u8 *)&gate,sizeof(gate));gate.fd=roles.socket;int permitted=0;
    result=ipc_begin(&gate);if(result)goto done;
    result=g_parent_bound(gate.hand);if(result)goto done;
    u8 bound_request[128];u64 deadline=0;
    result=h_bind_and_claim(bound_request,&deadline,gate.hand);if(result)goto done;
    result=ipc_permission(&gate);if(result)goto done;permitted=1;
    result=fx3_inner_boot_read_window(bound_request,deadline);
    if(!result){u64 now=0;if(!tick(&now)||now>=deadline)result=G_EXPIRED;}
done:
    if(permitted){if(sc(57,roles.image,0,0,0))result=G_CLOSE;if(sc(57,roles.job,0,0,0))result=G_CLOSE;if(sc(57,roles.parent_image,0,0,0))result=G_CLOSE;}
    return ipc_finish(&gate,result,permitted);
}
