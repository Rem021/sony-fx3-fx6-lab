/* Fixed grant, root-owned executable, descriptor-based frame, verified-parent
 * ACK and cooperative watchdog. No Sony transfer, file or firmware operation. */
#include "entry_shared.h"
#include "entry_target.h"
#include <CommonCrypto/CommonDigest.h>
#include <fcntl.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>
#ifndef FX3_ENTRY_FIXTURE
#include "host_login.h"
#endif
#ifdef FX3_ENTRY_FIXTURE
void fx3_owner_fixture_reset(uint32_t,uint32_t,uint32_t);
void fx3_owner_fixture_block(uint32_t,fx3_fixture_gate *);
void fx3_owner_fixture_body_tag(const uint8_t *);
uint32_t fx3_owner_fixture_calls(uint32_t);
#endif

typedef struct {
    fx3_entry_frame *frame;
    uint32_t observer_pid,owner_uid;
    uint64_t observer_sec,observer_usec,work_deadline;
    _Atomic uint32_t finished;
} watch_context;
static int denied(const char *reason,int code) { fprintf(stderr,"FX3_OWNER_ENTRY_DENIED:%s\n",reason);return code; }
static int nonzero(const uint8_t *p,size_t n) {uint8_t sum=0;for(size_t i=0;i<n;++i)sum|=p[i];return sum!=0;}
static void pause_short(void) {struct timespec t={0,10000000};nanosleep(&t,NULL);}
static int hex_nonce(const char *text,uint8_t out[16]) {
    if (strlen(text)!=32) return -1;
    for(unsigned i=0;i<16;++i) {
        char pair[3]={text[2*i],text[2*i+1],0};
        for(unsigned j=0;j<2;++j)if(!((pair[j]>='0'&&pair[j]<='9')||(pair[j]>='a'&&pair[j]<='f')))return -1;
        out[i]=(uint8_t)strtoul(pair,NULL,16);
    }return 0;
}
static int observer_alive(const watch_context *w) {
    uint32_t uid=0;uint64_t sec=0,usec=0;
    return !fx3_entry_pid_info(w->observer_pid,&uid,&sec,&usec) && uid==w->owner_uid && sec==w->observer_sec && usec==w->observer_usec;
}
static void *watch(void *opaque) {
    watch_context *w=opaque;
    while(!atomic_load_explicit(&w->finished,memory_order_acquire)) {
        if(!observer_alive(w) || fx3_entry_clock_ns()>=w->work_deadline)
            atomic_store_explicit(&w->frame->control.stop_requested,1,memory_order_release);
        pause_short();
    }return NULL;
}
static int fixed_entry_lease(const char *path,uint32_t pid) {
    int fd=open(path,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0400);
    if(fd<0)return -1;
    char text[80];int n=snprintf(text,sizeof(text),"grant=%s pid=%u\n",FX3_GRANT_ID,pid);
    int ok=n>0 && (size_t)n<sizeof(text) && write(fd,text,(size_t)n)==n && !fsync(fd);
    close(fd);return ok?0:-1; /* Never erase the consumed lease, even on failure. */
}

int main(int argc,char **argv) {
#ifdef FX3_ENTRY_FIXTURE
    if(argc!=4)return denied("fixture_frame_nonce_and_lease_required",64);
#else
    if(argc!=3)return denied("fixed_frame_and_nonce_required",64);
    if(geteuid()!=0)return denied("administrator_required",77);
    fx3_host_login host_login;
    char self[4096]={0};struct stat executable,grant_dir,root_base;
    if(fx3_entry_pid_path((uint32_t)getpid(),self,sizeof(self)) || strcmp(self,FX3_INSTALLED_HELPER) ||
       lstat(self,&executable) || !S_ISREG(executable.st_mode) || executable.st_uid || executable.st_nlink!=1 ||
       (executable.st_mode&0777)!=0500 || lstat(FX3_ROOT_GRANT_DIR,&grant_dir) || !S_ISDIR(grant_dir.st_mode) ||
       grant_dir.st_uid || (grant_dir.st_mode&0777)!=0700 || lstat(FX3_ROOT_BASE,&root_base) ||
       !S_ISDIR(root_base.st_mode) || root_base.st_uid || (root_base.st_mode&0777)!=0700)return denied("root_executable_identity",65);
#endif
    uint8_t nonce[16];if(hex_nonce(argv[2],nonce))return denied("nonce_shape",64);
    char path[4096];struct stat original;
    if(lstat(argv[1],&original) || S_ISLNK(original.st_mode) || !realpath(argv[1],path))return denied("frame_path",65);
#ifdef FX3_ENTRY_FIXTURE
    if(strncmp(path,FX3_FIXTURE_JOB_ROOT,strlen(FX3_FIXTURE_JOB_ROOT)) ||
       strncmp(argv[3],FX3_FIXTURE_JOB_ROOT,strlen(FX3_FIXTURE_JOB_ROOT)))return denied("fixture_path",65);
    uint32_t owner_uid=(uint32_t)getuid();
    int fd=open(path,O_RDWR|O_NOFOLLOW);
#else
    if(strcmp(path,FX3_FIXED_FRAME))return denied("fixed_frame_only",65);
    struct stat console,dir;struct statfs filesystem;
    if(stat("/dev/console",&console) || !console.st_uid)return denied("console_owner",65);
    uint32_t owner_uid=console.st_uid;
    fx3_host_login_read(&host_login);
    if(owner_uid!=501 || !fx3_host_login_valid(&host_login,owner_uid))
        return denied("current_console_GUI_audit_login_required",65);
    int directory=open(FX3_FIXED_JOB_DIR,O_RDONLY|O_DIRECTORY|O_NOFOLLOW);
    if(directory<0)return denied("job_directory",65);
    if(fstat(directory,&dir) || !S_ISDIR(dir.st_mode) || dir.st_uid!=owner_uid || (dir.st_mode&0777)!=0700 ||
       fstatfs(directory,&filesystem) || (filesystem.f_flags&MNT_IGNORE_OWNERSHIP)) {
        close(directory);return denied("job_directory_identity_or_owners_disabled",65);
    }
    int fd=openat(directory,"shared.bin",O_RDWR|O_NOFOLLOW);close(directory);
#endif
    struct stat st;
    if(fd<0)return denied("frame_open",65);
    if(fstat(fd,&st) || !S_ISREG(st.st_mode) || st.st_uid!=owner_uid || st.st_nlink!=1 ||
       (st.st_mode&0777)!=0600 || st.st_size!=4096) {close(fd);return denied("frame_identity",65);}
    void *memory=mmap(NULL,4096,PROT_READ|PROT_WRITE,MAP_SHARED,fd,0);close(fd);
    if(memory==MAP_FAILED)return denied("mapping",65);
    fx3_entry_frame *f=memory;fx3_entry_grant *g=&f->grant;
    /* Snapshot untrusted grant inputs once. No later shared mutation can
     * retarget the private native config or watchdog observer identity. */
    uint8_t privacy_key[32],expected_tag[32],observed_tag[32];
    memcpy(privacy_key,g->privacy_key,32);memcpy(expected_tag,g->expected_body_tag,32);
    memcpy(observed_tag,g->fixture_observed_tag,32);
    uint32_t fail=g->fixture_fail,option=g->fixture_option,block=g->fixture_block;
    watch_context context={.frame=f,.observer_pid=g->observer_pid,.owner_uid=owner_uid,
        .observer_sec=g->observer_birth_sec,.observer_usec=g->observer_birth_usec};
    atomic_init(&context.finished,0);
#ifdef FX3_ENTRY_FIXTURE
    if(g->mode!=1)return denied("fixture_mode",65);
#else
    if(g->mode || fail || option || block || nonzero(observed_tag,32))return denied("live_mode",65);
#endif
    if(g->schema!=2 || g->owner_uid!=owner_uid || f->control.abi!=3 ||
       !nonzero(privacy_key,32) || !nonzero(expected_tag,32) || !observer_alive(&context))return denied("grant_or_observer",65);
#ifdef FX3_ENTRY_FIXTURE
    const char *lease=argv[3];
#else
    const char *lease=FX3_ROOT_ENTRY_LEASE;
#endif
    if(fixed_entry_lease(lease,(uint32_t)getpid()))return denied("fixed_grant_consumed",67);
    if(fx3_entry_claim(f,nonce) || msync(memory,4096,MS_SYNC))return denied("frame_claim",66);
    if(fx3_ipc_install_handlers(memory))return denied("signal_setup",65);
    uint32_t uid=0;uint64_t sec=0,usec=0;
    if(fx3_entry_pid_info((uint32_t)getpid(),&uid,&sec,&usec))return denied("self_identity",65);
    g->native_pid=(uint32_t)getpid();g->birth_sec=sec;g->birth_usec=usec;
    uint64_t ack_deadline=fx3_entry_clock_ns()+2000000000ull;
    atomic_store_explicit(&g->helper_ready,1,memory_order_release);
    while(!atomic_load_explicit(&g->parent_ack,memory_order_acquire) &&
          !atomic_load_explicit(&f->control.stop_requested,memory_order_acquire) &&
          observer_alive(&context) && fx3_entry_clock_ns()<ack_deadline)pause_short();
    int acknowledged=atomic_load_explicit(&g->parent_ack,memory_order_acquire) && observer_alive(&context) &&
        !atomic_load_explicit(&f->control.stop_requested,memory_order_acquire) && fx3_entry_clock_ns()<ack_deadline;
    g->started_ns=fx3_entry_clock_ns();
#ifdef FX3_ENTRY_FIXTURE
    g->work_deadline_ns=g->started_ns+500000000ull;g->final_deadline_ns=g->started_ns+1500000000ull;
    fx3_owner_fixture_reset(fail,option|512u,0);fx3_owner_fixture_body_tag(observed_tag);
    if(block)fx3_owner_fixture_block(block,&f->gate);
#else
    g->work_deadline_ns=g->started_ns+20000000000ull;g->final_deadline_ns=g->started_ns+30000000000ull;
#endif
    context.work_deadline=g->work_deadline_ns;
    fx3_owner_config config={.abi=3,.arm=FX3_OWNER_ARM,.location=0x02100000,.capture_permitted=1,.vid=0x054c,.pid=0x0da1,
        .work_deadline_ns=g->work_deadline_ns,.final_deadline_ns=g->final_deadline_ns};
    memcpy(config.privacy_key,privacy_key,32);memcpy(config.expected_body_tag,expected_tag,32);
    g->native_return=FX3_DENIED;f->result.abi=3;f->result.status=FX3_DENIED;
    pthread_t watchdog;
    if(acknowledged && !pthread_create(&watchdog,NULL,watch,&context)) {
        atomic_store_explicit(&g->native_started,1,memory_order_release);
        g->native_return=fx3_owner_run(&config,&f->result,&f->control);
        atomic_store_explicit(&context.finished,1,memory_order_release);
        if(pthread_join(watchdog,NULL))return denied("watchdog_join_unknown",65);
    }
    CC_SHA256(&f->result,sizeof(f->result),g->result_sha256);
    atomic_store_explicit(&g->native_completed,1,memory_order_release);
    if(msync(memory,4096,MS_SYNC))return denied("result_sync",65);
    printf("{\"schema\":2,\"grant_id\":\"%s\",\"mode\":\"%s\",\"nonce\":\"%s\",\"pid\":%u,\"birth_sec\":%llu,\"birth_usec\":%llu,\"native_return\":%d,\"result_sha256\":\"",
        FX3_GRANT_ID,
#ifdef FX3_ENTRY_FIXTURE
        "fixture",
#else
        "live",
#endif
        argv[2],g->native_pid,(unsigned long long)sec,(unsigned long long)usec,g->native_return);
    for(unsigned i=0;i<32;++i)printf("%02x",g->result_sha256[i]);
    printf("\",\"physical_camera_acceptance\":false");
#ifdef FX3_ENTRY_FIXTURE
    printf(",\"fixture_calls\":[");for(unsigned i=1;i<=12;++i)printf("%s%u",i==1?"":",",fx3_owner_fixture_calls(i));printf("]");
#endif
#ifndef FX3_ENTRY_FIXTURE
    fx3_host_login_print_json(&host_login);
#endif
    printf("}\n");fflush(stdout);_exit(0);
}
