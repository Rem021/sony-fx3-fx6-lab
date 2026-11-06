/* Fixed grant, root-owned executable, descriptor-based frame, verified-parent
 * ACK and cooperative watchdog. No Sony transfer, file or firmware operation. */
#include "entry_shared.h"
#include "owner_channel.h"
#include "entry_target.h"
#include "frame_io.h"
#include "global_guard.h"
#include "owner_receipt.h"
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
void fx3_owner_fixture_io_fault(uint32_t,uint32_t);
uint32_t fx3_owner_fixture_wire_calls(uint32_t);
void fx3_owner_fixture_set_gate(fx3_fixture_gate *);
void fx3_owner_fixture_block(uint32_t,fx3_fixture_gate *);
void fx3_owner_fixture_body_tag(const uint8_t *);
uint32_t fx3_owner_fixture_calls(uint32_t);
#endif

typedef struct {
    fx3_entry_frame *frame;
    fx3_frame_io *frame_io;
    uint32_t observer_pid,owner_uid;
    uint64_t observer_sec,observer_usec,work_deadline;
    fx3_owner_result *private_result;
    _Atomic uint32_t finished;
} watch_context;
static int denied(const char *reason,int code) { fprintf(stderr,"FX3_OWNER_ENTRY_DENIED:%s\n",reason);return code; }
static int nonzero(const uint8_t *p,size_t n) {uint8_t sum=0;for(size_t i=0;i<n;++i)sum|=p[i];return sum!=0;}
static unsigned fd_count(void) {unsigned n=0;for(int fd=0;fd<4096;++fd)if(fcntl(fd,F_GETFD)>=0)++n;return n;}
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
static int pre_owner_ready(watch_context *w) {
    /* A host-only handshake may take time. Honor any intervening stop or
     * invalid report before acquiring an owner, independent of thread timing. */
    fx3_frame_control(w->frame_io,w->frame);
    uint64_t now=fx3_entry_clock_ns();
    return now && now<w->work_deadline && !atomic_load(&w->frame_io->failed) &&
        !atomic_load(&w->frame->control.stop_requested) && observer_alive(w);
}
static void *watch(void *opaque) {
    watch_context *w=opaque;
    while(!atomic_load_explicit(&w->finished,memory_order_acquire)) {
        fx3_owner_result *p=w->private_result,*out=&w->frame->result;
        if(p) {
            atomic_store(&out->active_call_pending,atomic_load(&p->active_call_pending));
            atomic_store(&out->owner_retained,atomic_load(&p->owner_retained));
            atomic_store(&out->session_state,atomic_load(&p->session_state));
            atomic_store(&out->wire_pending,atomic_load(&p->wire_pending));
            atomic_store(&out->vendor_attempted,atomic_load(&p->vendor_attempted));
        }
        fx3_frame_control(w->frame_io,w->frame);
        fx3_frame_progress(w->frame_io,w->frame);
        if(atomic_load(&w->frame_io->failed) || !observer_alive(w) || fx3_entry_clock_ns()>=w->work_deadline)
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
    unsigned fds_before=fd_count();
#ifdef FX3_ENTRY_FIXTURE
    if(argc!=6)return denied("fixture_frame_nonce_lease_socket_guard_required",64);
    if(strncmp(argv[5],FX3_FIXTURE_JOB_ROOT,strlen(FX3_FIXTURE_JOB_ROOT)))return denied("fixture_guard_path",65);
    if(strncmp(argv[4],FX3_FIXTURE_SOCKET_ROOT,strlen(FX3_FIXTURE_SOCKET_ROOT)))return denied("fixture_socket_path",65);
#else
    if(!FX3_NATIVE_RELEASED)return denied("candidate_not_released",77);
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
    void *memory=calloc(1,4096);
    if(!memory || pread(fd,memory,4096,0)!=4096) {close(fd);return denied("private_frame_read",65);}
    fx3_frame_io frame_io={.fd=fd,.identity=st};atomic_init(&frame_io.failed,0);
    fx3_entry_frame *f=memory;fx3_entry_grant *g=&f->grant;
    /* Snapshot untrusted grant inputs once. No later shared mutation can
     * retarget the private native config or watchdog observer identity. */
    uint8_t privacy_key[32],expected_tag[32],observed_tag[32];
    memcpy(privacy_key,g->privacy_key,32);memcpy(expected_tag,g->expected_body_tag,32);
    memcpy(observed_tag,g->fixture_observed_tag,32);
    uint32_t fail=g->fixture_fail,option=g->fixture_option,block=g->fixture_block;
    watch_context context={.frame=f,.frame_io=&frame_io,.observer_pid=g->observer_pid,.owner_uid=owner_uid,
        .observer_sec=g->observer_birth_sec,.observer_usec=g->observer_birth_usec};
    atomic_init(&context.finished,0);
#ifdef FX3_ENTRY_FIXTURE
    if(g->mode!=1)return denied("fixture_mode",65);
#else
    if(g->mode || fail || option || block || nonzero(observed_tag,32))return denied("live_mode",65);
#endif
    if(g->schema!=FX3_ENTRY_SCHEMA || g->owner_uid!=owner_uid || f->control.abi!=FX3_OWNER_ABI ||
       !nonzero(privacy_key,32) || !nonzero(expected_tag,32) || !observer_alive(&context))return denied("grant_or_observer",65);
#ifdef FX3_ENTRY_FIXTURE
    const char *lease=argv[3];
#else
    const char *lease=FX3_ROOT_ENTRY_LEASE;
#endif
    if(fixed_entry_lease(lease,(uint32_t)getpid()))return denied("fixed_grant_consumed",67);
    if(fx3_entry_claim(f,nonce) || fx3_frame_write(&frame_io,f))return denied("frame_claim",66);
    if(fx3_ipc_install_handlers(memory))return denied("signal_setup",65);
    uint32_t uid=0;uint64_t sec=0,usec=0;
    if(fx3_entry_pid_info((uint32_t)getpid(),&uid,&sec,&usec))return denied("self_identity",65);
    g->native_pid=(uint32_t)getpid();g->birth_sec=sec;g->birth_usec=usec;
    uint64_t ack_deadline=fx3_entry_clock_ns()+2000000000ull;
    atomic_store_explicit(&g->helper_ready,1,memory_order_release);
    if(fx3_frame_write(&frame_io,f))return denied("ready_delivery",65);
    while(!atomic_load_explicit(&g->parent_ack,memory_order_acquire) &&
          !atomic_load_explicit(&f->control.stop_requested,memory_order_acquire) &&
          observer_alive(&context) && fx3_entry_clock_ns()<ack_deadline) {fx3_frame_control(&frame_io,f);pause_short();}
    int acknowledged=atomic_load_explicit(&g->parent_ack,memory_order_acquire) && observer_alive(&context) &&
        !atomic_load_explicit(&f->control.stop_requested,memory_order_acquire) && fx3_entry_clock_ns()<ack_deadline;
    uint64_t started_ns=fx3_entry_clock_ns(),work_deadline,final_deadline;
    g->started_ns=started_ns;
#ifdef FX3_ENTRY_FIXTURE
    work_deadline=started_ns+2000000000ull;final_deadline=started_ns+3000000000ull;
    fx3_owner_fixture_reset(fail,option|512u,0);fx3_owner_fixture_body_tag(observed_tag);
    fx3_owner_fixture_set_gate(&f->gate);
    if(block && block<=13)fx3_owner_fixture_block(block,&f->gate);
    else if(block)fx3_owner_fixture_io_fault((block>>8)&255,block&255);
#else
    work_deadline=started_ns+20000000000ull;final_deadline=started_ns+30000000000ull;
#endif
    g->work_deadline_ns=work_deadline;g->final_deadline_ns=final_deadline;
    context.work_deadline=work_deadline;
    fx3_owner_config config={.abi=FX3_OWNER_ABI,.arm=FX3_OWNER_ARM,.location=0x02100000,.capture_permitted=1,.vid=0x054c,.pid=0x0da1,
        .work_deadline_ns=work_deadline,.final_deadline_ns=final_deadline};
    memcpy(config.privacy_key,privacy_key,32);memcpy(config.expected_body_tag,expected_tag,32);
    g->native_return=FX3_DENIED;f->result.abi=FX3_OWNER_ABI;f->result.status=FX3_DENIED;
    fx3_channel_config channel={.peer_uid=owner_uid,.peer_pid=context.observer_pid,
        .peer_sec=context.observer_sec,.peer_usec=context.observer_usec,.deadline_ns=work_deadline,
        .generation=17,.scope=1,.fd=-1};
    memcpy(channel.nonce,nonce,16);
#ifdef FX3_ENTRY_FIXTURE
    channel.path=argv[4];channel.scope=(option&4096)?2:1;
    if(option&1048576)channel.peer_pid=(uint32_t)getpid();
    if(option&2097152)++channel.peer_sec;
#else
    channel.path=FX3_FIXED_PEER_PATH;
#endif
    config.protocol_scope=channel.scope;
    fx3_owner_result private_result;
    memset(&private_result,0,sizeof(private_result));
    atomic_init(&private_result.active_call_pending,0);atomic_init(&private_result.owner_retained,0);
    atomic_init(&private_result.session_state,0);atomic_init(&private_result.wire_pending,0);atomic_init(&private_result.vendor_attempted,0);
    private_result.abi=FX3_OWNER_ABI;private_result.status=FX3_DENIED;
    context.private_result=&private_result;
    int ran=0,private_return=FX3_DENIED;
    fx3_global_guard global={.fd=-1};int global_result=G_INVALID;
#ifdef FX3_ENTRY_FIXTURE
    const char *global_path=argv[5];uint32_t guard_uid=(uint32_t)getuid();
#else
    const char *global_path=FX3_GLOBAL_GUARD;uint32_t guard_uid=0;
#endif
    if(fx3_frame_write(&frame_io,f))acknowledged=0;
    pthread_t watchdog;
    uint64_t peer_ack_deadline=fx3_entry_clock_ns()+1000000000ull;
    if(peer_ack_deadline>work_deadline)peer_ack_deadline=work_deadline;
    if(acknowledged && !fx3_channel_connect(&channel) && !fx3_receipt_peer_ack(&channel,peer_ack_deadline) && pre_owner_ready(&context) &&
       !(global_result=fx3_global_begin(&global,global_path,guard_uid,nonce,FX3_GRANT_ID)) &&
       !pthread_create(&watchdog,NULL,watch,&context)) {
        atomic_store_explicit(&g->native_started,1,memory_order_release);
        ran=1;private_return=fx3_owner_run_with_channel(&config,&private_result,&f->control,&channel);
        g->native_return=private_return;
        if(private_return==FX3_RETAINED) {
            fx3_frame_progress(&frame_io,f); /* publication failure cannot release an owner */
            fx3_receipt_meta held={.phase=FX3_RECEIPT_HELD,.uid=uid,.pid=(uint32_t)getpid(),.sec=sec,.usec=usec,
                .nonce=nonce,.grant=FX3_GRANT_ID,.native_return=private_return,.guard_return=global_result,
                .frame_failed=atomic_load(&frame_io.failed)!=0,.ran=1};
            (void)fx3_receipt_send(&channel,&held,&private_result,final_deadline);
            /* Do not publish native_completed, join/kill, release USB or exit.
             * Only the own fake-object fixture has a local termination gate. */
#ifdef FX3_ENTRY_FIXTURE
            while(atomic_load(&f->gate.released)!=2)pause_short();
            printf("{\"fixture_retained_exit\":true,\"cleanup_calls\":[%u,%u,%u],\"wire_calls\":[%u,%u,%u],\"last_pipes\":[%u,%u],\"body_completion_proven\":false}\n",
                fx3_owner_fixture_calls(P_RELEASE),fx3_owner_fixture_calls(P_RETURN),fx3_owner_fixture_calls(P_CLOSE),
                fx3_owner_fixture_wire_calls(0),fx3_owner_fixture_wire_calls(1),fx3_owner_fixture_wire_calls(2),
                fx3_owner_fixture_wire_calls(5),fx3_owner_fixture_wire_calls(6));
            fflush(stdout);_exit(90);
#else
            for(;;)pause_short();
#endif
        }
        atomic_store_explicit(&context.finished,1,memory_order_release);
        if(pthread_join(watchdog,NULL))return denied("watchdog_join_unknown",65);
    }
    if(global.started && global.fd>=0) {
        int clean=!ran || (private_return==FX3_DENIED && !private_result.event_count) ||
            ((private_return==FX3_OBSERVED || private_return==FX3_ABORTED_RETURN_OBSERVED) &&
            !private_result.cleanup_error && !private_result.clock_invalid && !atomic_load(&private_result.vendor_attempted) &&
            !atomic_load(&private_result.active_call_pending));
        global_result=fx3_global_finish(&global,clean);
    }
    if(ran) {
        /* Copy only after the real call returned and watchdog joined. Public
         * writes cannot alter private ownership, snapshots or deadlines. */
        size_t a=offsetof(fx3_owner_result,active_call_pending),b=offsetof(fx3_owner_result,before);
        memcpy(&f->result,&private_result,a);
        f->result.persistent_camera_or_vendor_commands=private_result.persistent_camera_or_vendor_commands;
        memcpy((uint8_t *)&f->result+b,(uint8_t *)&private_result+b,sizeof(private_result)-b);
        atomic_store(&f->result.active_call_pending,atomic_load(&private_result.active_call_pending));
        atomic_store(&f->result.owner_retained,atomic_load(&private_result.owner_retained));
        atomic_store(&f->result.session_state,atomic_load(&private_result.session_state));
        atomic_store(&f->result.wire_pending,atomic_load(&private_result.wire_pending));
        atomic_store(&f->result.vendor_attempted,atomic_load(&private_result.vendor_attempted));
    }
    uint8_t private_digest[32];CC_SHA256(&private_result,sizeof(private_result),private_digest);
    memcpy(g->result_sha256,private_digest,32);
    atomic_store_explicit(&g->native_completed,1,memory_order_release);
    int frame_failed=fx3_frame_write(&frame_io,f)!=0;
    close(frame_io.fd);frame_io.fd=-1;
    fx3_receipt_meta final={.phase=FX3_RECEIPT_COMPLETE,.uid=uid,.pid=(uint32_t)getpid(),.sec=sec,.usec=usec,
        .nonce=nonce,.grant=FX3_GRANT_ID,.native_return=private_return,.guard_return=global_result,
        .frame_failed=frame_failed,.ran=(uint32_t)ran};
    int receipt_delivered=fx3_receipt_send(&channel,&final,&private_result,final_deadline)==0;
    if(channel.fd>=0)close(channel.fd);
    printf("{\"schema\":2,\"grant_id\":\"%s\",\"mode\":\"%s\",\"nonce\":\"%s\",\"pid\":%u,\"birth_sec\":%llu,\"birth_usec\":%llu,\"native_return\":%d,\"result_sha256\":\"",
        FX3_GRANT_ID,
#ifdef FX3_ENTRY_FIXTURE
        "fixture",
#else
        "live",
#endif
        argv[2],(uint32_t)getpid(),(unsigned long long)sec,(unsigned long long)usec,private_return);
    for(unsigned i=0;i<32;++i)printf("%02x",private_digest[i]);
    printf("\",\"physical_camera_acceptance\":false");
#ifdef FX3_ENTRY_FIXTURE
    printf(",\"fixture_calls\":[");for(unsigned i=1;i<=12;++i)printf("%s%u",i==1?"":",",fx3_owner_fixture_calls(i));printf("]");
    printf(",\"wire_calls\":[%u,%u,%u]",fx3_owner_fixture_wire_calls(0),fx3_owner_fixture_wire_calls(1),fx3_owner_fixture_wire_calls(2));
#endif
#ifndef FX3_ENTRY_FIXTURE
    fx3_host_login_print_json(&host_login);
#endif
    printf(",\"global_guard_result\":%d,\"frame_io_failed\":%s,\"receipt_delivered\":%s,\"fd_count_before\":%u,\"fd_count_after\":%u}\n",global_result,frame_failed?"true":"false",receipt_delivered?"true":"false",fds_before,fd_count());fflush(stdout);_exit(0);
}
