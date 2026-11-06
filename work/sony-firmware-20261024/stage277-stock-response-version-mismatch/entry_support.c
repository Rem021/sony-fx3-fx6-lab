/* Shared-data and process identity only; this file contains no device API. */
#include "entry_shared.h"
#include <libproc.h>
#include <errno.h>
#include <limits.h>
#include <string.h>
#include <time.h>
#include <sys/types.h>
#include <sys/sysctl.h>
#define PUB __attribute__((visibility("default")))
_Static_assert(sizeof(fx3_entry_frame)<=FX3_ENTRY_BLOCK_BYTES,"entry frame exceeds fixed mapping");
PUB uint32_t fx3_entry_layout(uint32_t field) {
    const uint32_t values[]={sizeof(fx3_entry_frame),offsetof(fx3_entry_frame,grant),sizeof(fx3_entry_grant),
        sizeof(fx3_owner_config),sizeof(fx3_owner_result),sizeof(fx3_owner_control)};
    return field<6?values[field]:0;
}
PUB int fx3_entry_init(void *memory,size_t bytes,uint32_t mode,uint32_t owner,const uint8_t *nonce,const uint8_t *key,const uint8_t *tag) {
    if (!memory || bytes!=FX3_ENTRY_BLOCK_BYTES || mode>1 || !owner || !nonce || !key || !tag) return -1;
    if (fx3_ipc_init(memory,bytes)) return -1;
    fx3_entry_frame *f=memory;
    f->grant.schema=FX3_ENTRY_SCHEMA;f->grant.mode=mode;f->grant.owner_uid=owner;f->grant.scope=FX3_ENTRY_SCOPE;
    memcpy(f->grant.nonce,nonce,16);memcpy(f->grant.privacy_key,key,32);memcpy(f->grant.expected_body_tag,tag,32);
    atomic_init(&f->grant.attempt_claimed,0);atomic_init(&f->grant.native_started,0);atomic_init(&f->grant.native_completed,0);
    atomic_init(&f->grant.helper_ready,0);atomic_init(&f->grant.parent_ack,0);
    return 0;
}
PUB int fx3_entry_claim(void *memory,const uint8_t *nonce) {
    fx3_entry_frame *f=memory;
    if (!f || !nonce || f->grant.schema!=FX3_ENTRY_SCHEMA || f->grant.scope!=FX3_ENTRY_SCOPE || memcmp(nonce,f->grant.nonce,16)) return -1;
    uint32_t expected=0;
    return atomic_compare_exchange_strong_explicit(&f->grant.attempt_claimed,&expected,1,memory_order_acq_rel,memory_order_acquire)?0:-2;
}
PUB int fx3_entry_pid_info(uint32_t pid,uint32_t *uid,uint64_t *sec,uint64_t *usec) {
    /* Public kernel metadata, not full same-UID-only PROC_PIDTBSDINFO.
     * Keep the exact effective UID and microsecond process start identity. */
    if(!pid || pid>INT_MAX) {errno=EINVAL;return -1;}
    int name[4]={CTL_KERN,KERN_PROC,KERN_PROC_PID,(int)pid};
    struct kinfo_proc info;size_t size=sizeof(info);memset(&info,0,sizeof(info));
    if(sysctl(name,4,&info,&size,NULL,0))return -1;
    if(!size) {errno=ESRCH;return -1;}
    if(size!=sizeof(info) || info.kp_proc.p_pid!=(pid_t)pid ||
       info.kp_proc.p_starttime.tv_sec<=0 || info.kp_proc.p_starttime.tv_usec<0 ||
       info.kp_proc.p_starttime.tv_usec>=1000000) {errno=EIO;return -1;}
    if (uid) *uid=info.kp_eproc.e_ucred.cr_uid;
    if (sec) *sec=(uint64_t)info.kp_proc.p_starttime.tv_sec;
    if (usec) *usec=(uint64_t)info.kp_proc.p_starttime.tv_usec;
    return 0;
}
PUB uint64_t fx3_entry_clock_ns(void) {
    struct timespec now;clock_gettime(CLOCK_MONOTONIC,&now);
    return (uint64_t)now.tv_sec*1000000000ull+(uint64_t)now.tv_nsec;
}
PUB uint32_t fx3_entry_ready(void *memory) {
    return atomic_load_explicit(&((fx3_entry_frame *)memory)->grant.helper_ready,memory_order_acquire);
}
PUB void fx3_entry_ack(void *memory) {
    atomic_store_explicit(&((fx3_entry_frame *)memory)->grant.parent_ack,1,memory_order_release);
}
PUB uint32_t fx3_entry_completed(void *memory) {
    return atomic_load_explicit(&((fx3_entry_frame *)memory)->grant.native_completed,memory_order_acquire);
}
PUB int fx3_entry_pid_path(uint32_t pid,char *path,uint32_t capacity) {
    return proc_pidpath((int)pid,path,capacity)>0?0:-1;
}
PUB int fx3_entry_pid_exists(uint32_t pid) {
    int name[4]={CTL_KERN,KERN_PROC,KERN_PROC_PID,(int)pid};
    struct kinfo_proc info;size_t size=sizeof(info);
    if(sysctl(name,4,&info,&size,NULL,0))return -1;
    return size?1:0;
}
/* Native ABI getters for a read-only observer; no layout guessed in Python. */
PUB uint64_t fx3_entry_value(void *memory,uint32_t item) {
    fx3_entry_frame *f=memory;
    switch(item) {
        case 0:return f->grant.native_pid;
        case 1:return atomic_load(&f->grant.native_started);
        case 2:return atomic_load(&f->result.owner_retained);
        case 3:return atomic_load(&f->result.session_state);
        case 4:return atomic_load(&f->result.wire_pending);
        case 5:return atomic_load(&f->result.vendor_attempted);
        case 6:return atomic_load(&f->result.active_call_pending);
        case 7:return f->result.status;
        case 8:return atomic_load(&f->gate.entered);
        default:return 0;
    }
}
PUB int fx3_entry_fixture_fields(void *memory,uint32_t fail,uint32_t option,uint32_t block,const uint8_t *observed,
    uint32_t observer,uint64_t sec,uint64_t usec) {
    fx3_entry_frame *f=memory;
    if(f->grant.mode!=1 || atomic_load(&f->grant.attempt_claimed) || !observed)return -1;
    f->grant.fixture_fail=fail;f->grant.fixture_option=option;f->grant.fixture_block=block;
    memcpy(f->grant.fixture_observed_tag,observed,32);
    f->grant.observer_pid=observer;f->grant.observer_birth_sec=sec;f->grant.observer_birth_usec=usec;return 0;
}
PUB void fx3_entry_fixture_gate(void *memory,uint32_t value) {
    fx3_entry_frame *f=memory;if(f->grant.mode==1)atomic_store(&f->gate.released,value);
}
