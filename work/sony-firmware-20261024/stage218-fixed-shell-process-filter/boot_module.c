/* Own offline candidate. Constructor remains memory-only. Explicit dispatch
 * filters the first /bin/sh -c child; these are accidental-process checks,
 * not authorisation, live body/loaded-code attestation or a secure root boundary.
 * No preload installation, worker auto-dispatch or process-exit syscall.
 */
#include "inner_boot_reader.c"
static volatile u64 module_initialized;
static int guard_used;
static const u8 shell_command[]="/bin/sh\0-c\0/bin/date -s 070421422017.26";
static const char self_sha[]="c3297a7086efe9a001c39fa98d74d125992cf3225cf353ab6ff2238d827c7799";
static const char parent_sha[]="5171f576d8b76cfbf15581389183b390c445bd6ff9dd97fd6668c5f64e77dc91";
enum { G_REPLAY=40,G_ID=41,G_CMD=42,G_SELF=43,G_PARENT=44,G_TIME=45,G_CLOSE=46,G_INIT=47 };
static int g_close(long fd,int result){return sc(57,fd,0,0,0)?G_CLOSE:result;}
static int g_regular(const struct kstat *s){return (s->mode&0170000)==0100000&&!s->uid&&s->nlink==1&&!(s->mode&022);}
static int g_command(void){
    long fd=sc(56,AT_FDCWD,(long)"/proc/self/cmdline",RD,0);if(fd<0)return G_CMD;
    struct kstat a,b;u8 text[256],extra=0;u64 fs[32];zero((u8 *)fs,sizeof(fs));int result=G_CMD;
    if(!stat_(fd,&a)||!g_regular(&a)||a.size!=0||sc(44,fd,(long)fs,0,0)||fs[0]!=0x9fa0)goto done;
    long n=sc(63,fd,(long)text,sizeof(text),0);
    if(n!=(long)sizeof(shell_command)||!equal(text,shell_command,sizeof(shell_command))||sc(63,fd,(long)&extra,1,0)||!stat_(fd,&b)||!stable(&a,&b))goto done;
    result=0;
done:return g_close(fd,result);
}
/* /proc/<pid>/exe magic links are deliberately followed to the executable
 * backing file. This does not read or attest all mapped process memory.
 */
static int g_hash_exe(const char *path,u32 size,const char *digest,struct kstat *saved,int failure){
    long fd=sc(56,AT_FDCWD,(long)path,0x80000,0);if(fd<0)return failure;
    struct kstat a,b;struct sha state;u8 out[32],extra=0;int result=failure;
    if(!stat_(fd,&a)||!g_regular(&a)||a.size!=(long)size)goto done;
    sha_init(&state);u32 left=size;
    while(left){u32 want=left>sizeof(hashbuf)?sizeof(hashbuf):left;long n=sc(63,fd,(long)hashbuf,want,0);if(n!=(long)want)goto done;sha_update(&state,hashbuf,want);left-=want;}
    sha_final(&state,out);
    if(sc(63,fd,(long)&extra,1,0)||!hex_matches(out,digest)||!stat_(fd,&b)||!stable(&a,&b))goto done;
    *saved=a;result=0;
done:return g_close(fd,result);
}
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
static int g_filter(void){
    long pid=sc(172,0,0,0,0),parent=sc(173,0,0,0,0),tid=sc(178,0,0,0,0);
    if(sc(174,0,0,0,0)||sc(175,0,0,0,0)||pid<=1||pid>2147483647L||tid!=pid||parent<=1||parent==pid)return G_ID;
    char parent_path[32];if(!g_parent_path(parent_path,parent))return G_ID;
    u64 now=0;if(!tick(&now))return G_TIME;u64 deadline=now+10000000000ULL;
    int result=g_command();if(result)return result;
    if(!tick(&now)||now>=deadline)return G_TIME;
    struct kstat self,parent_stat;
    result=g_hash_exe("/proc/self/exe",423000,self_sha,&self,G_SELF);if(result)return result;
    if(!tick(&now)||now>=deadline)return G_TIME;
    result=g_hash_exe(parent_path,40920,parent_sha,&parent_stat,G_PARENT);if(result)return result;
    if(!tick(&now)||now>=deadline)return G_TIME;
    if(sc(172,0,0,0,0)!=pid||sc(178,0,0,0,0)!=pid||sc(173,0,0,0,0)!=parent||sc(174,0,0,0,0)||sc(175,0,0,0,0))return G_ID;
    result=g_recheck("/proc/self/exe",&self,G_SELF);if(result)return result;
    result=g_recheck(parent_path,&parent_stat,G_PARENT);if(result)return result;
    if(!tick(&now)||now>=deadline)return G_TIME;
    return 0;
}
__attribute__((constructor)) static void fx3_module_init(void){module_initialized=0x4658334d4f443031ULL;}
__attribute__((visibility("default"))) u64 fx3_module_status(void){return module_initialized;}
__attribute__((visibility("default"))) int fx3_boot_read_window(void){
    if(__atomic_exchange_n(&guard_used,1,__ATOMIC_ACQ_REL))return G_REPLAY;
    if(module_initialized!=0x4658334d4f443031ULL)return G_INIT;
    int result=g_filter();if(result)return result;
    return fx3_inner_boot_read_window();
}
