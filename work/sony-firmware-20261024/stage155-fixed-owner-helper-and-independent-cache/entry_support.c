/* Shared-data and process identity only; this file contains no device API. */
#include "entry_shared.h"
#include <libproc.h>
#include <string.h>
#include <time.h>
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
    return 0;
}
PUB int fx3_entry_claim(void *memory,const uint8_t *nonce) {
    fx3_entry_frame *f=memory;
    if (!f || !nonce || f->grant.schema!=FX3_ENTRY_SCHEMA || f->grant.scope!=FX3_ENTRY_SCOPE || memcmp(nonce,f->grant.nonce,16)) return -1;
    uint32_t expected=0;
    return atomic_compare_exchange_strong_explicit(&f->grant.attempt_claimed,&expected,1,memory_order_acq_rel,memory_order_acquire)?0:-2;
}
PUB int fx3_entry_pid_info(uint32_t pid,uint32_t *uid,uint64_t *sec,uint64_t *usec) {
    struct proc_bsdinfo info;
    int bytes=proc_pidinfo((int)pid,PROC_PIDTBSDINFO,0,&info,sizeof(info));
    if (bytes!=(int)sizeof(info)) return -1;
    if (uid) *uid=info.pbi_uid;
    if (sec) *sec=info.pbi_start_tvsec;
    if (usec) *usec=info.pbi_start_tvusec;
    return 0;
}
PUB uint64_t fx3_entry_clock_ns(void) {
    struct timespec now;clock_gettime(CLOCK_MONOTONIC,&now);
    return (uint64_t)now.tv_sec*1000000000ull+(uint64_t)now.tv_nsec;
}
