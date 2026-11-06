/* Own provider fixture: no IOKit headers/framework, USB library or device API. */
#include "owner_trial.h"
#include "target_binding.h"
#include "owner_channel.h"
#include "entry_shared.h"
#include <string.h>
#include <stdatomic.h>
#include <time.h>
#include <unistd.h>
typedef struct { uint32_t fail, option, late_phase, calls[14], snapshots, captured, closed; uint64_t now; fx3_owner_result *result;
    fx3_owner_control *control;fx3_channel_config channel;fx3_channel_runtime runtime;void *io;uint32_t wire_counts[3],fault_op,fault; } fixture;
static fixture f;
static uint8_t fixture_body_tag[32];
static atomic_flag running=ATOMIC_FLAG_INIT;
static fx3_fixture_gate *block_gate;
static uint32_t block_phase;
void *fx3_iokit_fixture_create(uint32_t,uint64_t,int);
int fx3_iokit_fixture_dispose(void *);
int fx3_iokit_fixture_borrow_owner(void *,fx3_io_owner *);
void fx3_iokit_fixture_gate(void *,_Atomic uint32_t *,_Atomic uint32_t *);
int fx3_iokit_fixture_clock(void *,uint64_t);
int fx3_iokit_fixture_reply(void *,const uint8_t *,uint32_t);
int fx3_iokit_fixture_fault(void *,uint32_t,uint32_t);
uint64_t fx3_iokit_fixture_stat(void *,uint32_t);
enum { MOUNTED=1, NULL_TAG=2, BAD_PROFILE=4, BODY_CHANGED=8, MOUNT_RACE=16,
       INCARNATION_RACE=32, DRIVER_REMAINS=64, NO_DRIVER=128, CLOCK_BACKWARD=256 };
static int32_t hit(unsigned phase) {
    ++f.calls[phase];
    if (block_gate && phase==block_phase) {
        atomic_store_explicit(&block_gate->entered,phase,memory_order_release);
        while (!atomic_load_explicit(&block_gate->released,memory_order_acquire)) { struct timespec t={0,1000000}; nanosleep(&t,NULL); }
    }
    if (f.late_phase==phase) f.now+=21000000000ull;
    return f.fail==phase?17:0;
}
static int32_t snap(void *p,fx3_owner_snapshot *s) {
    (void)p;
    unsigned phase=f.result->active_call_pending;
    ++f.snapshots;
    memset(s,0,sizeof(*s));
    s->registry_id=phase==P_AFTER?101:100; s->media_count=2; s->vid=0x054c; s->pid=0x0da1; s->location=FX3_FIXED_LOCATION;
    s->storage_driver_count=(f.option&NO_DRIVER)?0:(f.captured?0:3);
    memcpy(s->body_tag,fixture_body_tag,32);
    if (f.option&NULL_TAG) memset(s->body_tag,0,32);
    if (phase==P_BEFORE && f.option&MOUNTED) s->mounted_count=1;
    if (phase==P_AFTER && f.option&BODY_CHANGED) s->body_tag[0]^=1;
    if (phase==P_PRE_CAPTURE && f.option&MOUNT_RACE) s->mounted_count=1;
    if (phase==P_PRE_CAPTURE && f.option&INCARNATION_RACE) s->registry_id=102;
    if (phase==P_PRE_CLAIM && f.option&DRIVER_REMAINS) s->storage_driver_count=3;
    return hit(phase);
}
static int32_t open_(void *p) { (void)p; return hit(P_OPEN); }
static int32_t capture_(void *p) { (void)p; f.captured=1; return hit(P_CAPTURE); }
static int32_t reopen_(void *p) { (void)p; return hit(P_REOPEN); }
static int32_t claim_(void *p,fx3_owner_profile *profile) {
    /* Synthetic native claim trace; no USB calls in this fixture. */
    const uint32_t trace[]={102,103,104,105,106,107,108,109,109};
    for(unsigned i=0;i<sizeof(trace)/sizeof(trace[0]);++i) {
        if(f.result->event_count>=FX3_OWNER_EVENTS)return -1;
        f.result->events[f.result->event_count++]=(fx3_owner_event){trace[i],0};
    }
    (void)p; *profile=(fx3_owner_profile){0,0,(f.option&BAD_PROFILE)?0x82:0x81,2,512,2,(f.option&8192)?2:1,(f.option&8192)?1:2}; return hit(P_CLAIM);
}
static int32_t release_(void *p) { (void)p; return hit(P_RELEASE); }
static int32_t return_(void *p) { (void)p; f.captured=0; return hit(P_RETURN); }
static int32_t close_(void *p) { (void)p; f.closed=1; return hit(P_CLOSE); }
static uint64_t now_(void *p) {
    (void)p;
    if (f.option&512) { struct timespec t; clock_gettime(CLOCK_MONOTONIC,&t); return (uint64_t)t.tv_sec*1000000000ull+(uint64_t)t.tv_nsec; }
    if ((f.option&CLOCK_BACKWARD) && f.calls[P_CAPTURE]) { f.option&=~CLOCK_BACKWARD; f.now=1; }
    else f.now+=1000;
    return f.now;
}
static void pause_(void *p,uint32_t ms) { (void)p; if (f.option&512) { struct timespec t={ms/1000,(long)(ms%1000)*1000000L}; nanosleep(&t,NULL); } else f.now+=(uint64_t)ms*1000000ull; }
static void prepare_reply(void *unused) {
    (void)unused;uint8_t data[516]={0};unsigned command=f.runtime.session.next_command;
    unsigned reply=command==1?8:command==3?4:6;
    data[0]=(uint8_t)((~reply)>>8);data[1]=(uint8_t)~reply;if(reply==6)data[4]=1;
    (void)fx3_iokit_fixture_clock(f.io,fx3_entry_clock_ns());
    (void)fx3_iokit_fixture_reply(f.io,data,516);
    (void)fx3_iokit_fixture_fault(f.io,f.fault_op,f.fault);
}
static int32_t session_(void *unused) {
    (void)unused;(void)hit(P_SESSION);
    f.io=fx3_iokit_fixture_create(1,f.channel.generation,(f.option&8192)!=0);if(!f.io)return -1;
    if(fx3_iokit_fixture_clock(f.io,fx3_entry_clock_ns()))return -1;
    fx3_io_owner owner;if(fx3_iokit_fixture_borrow_owner(f.io,&owner))return -1;
    owner.session_deadline_ns=f.channel.deadline_ns;
    owner.stop_requested=&f.control->stop_requested;
    owner.published_pending=&f.result->wire_pending;owner.published_vendor=&f.result->vendor_attempted;
    if(block_gate)fx3_iokit_fixture_gate(f.io,&block_gate->entered,&block_gate->released);
    f.channel.before_request=prepare_reply;
    return fx3_channel_run(&f.runtime,&f.channel,&owner,f.result);
}
static int clean_(void *unused) {(void)unused;return fx3_channel_cleanup_allowed(&f.runtime);}
static const fx3_owner_ops ops={snap,open_,capture_,reopen_,claim_,release_,return_,close_,now_,pause_,session_,clean_};
__attribute__((visibility("default"))) uint32_t fx3_owner_fixture_marker(void) { return 0x46495835; }
__attribute__((visibility("default"))) void fx3_owner_fixture_reset(uint32_t fail,uint32_t option,uint32_t late) {
    memset(&f,0,sizeof(f)); memset(fixture_body_tag,0x41,32); block_gate=NULL; block_phase=0; f.fail=fail; f.option=option; f.late_phase=late; f.now=1000000000ull;
}
__attribute__((visibility("default"))) uint32_t fx3_owner_fixture_calls(uint32_t phase) { return phase<=13?f.calls[phase]:0; }
__attribute__((visibility("default"))) uint32_t fx3_owner_fixture_size(uint32_t which) {
    const uint32_t sizes[]={sizeof(fx3_owner_config),sizeof(fx3_owner_result),sizeof(fx3_owner_snapshot),sizeof(fx3_owner_profile),sizeof(fx3_owner_event)};
    return which<5?sizes[which]:0;
}
int fx3_owner_run_with_channel(const fx3_owner_config *c,fx3_owner_result *r,fx3_owner_control *control,const fx3_channel_config *channel) {
    if (atomic_flag_test_and_set(&running)) return FX3_DENIED;
    if(c->protocol_scope && (!channel || !fx3_channel_peer(channel)))return FX3_DENIED;
    f.result=r;f.control=control;if(channel)f.channel=*channel;
    int rc=fx3_owner_core(c,r,control,&ops,&f);
    if(f.io && rc!=FX3_RETAINED) {
        for(unsigned i=0;i<3;++i)f.wire_counts[i]=(uint32_t)fx3_iokit_fixture_stat(f.io,i);
        if(fx3_iokit_fixture_dispose(f.io))return FX3_RETURN_UNKNOWN;f.io=NULL;
    }
    atomic_flag_clear(&running);
    return rc;
}
__attribute__((visibility("default"))) int fx3_owner_run(const fx3_owner_config *c,fx3_owner_result *r,fx3_owner_control *control) {
    return fx3_owner_run_with_channel(c,r,control,NULL);
}

__attribute__((visibility("default"))) void fx3_owner_fixture_block(uint32_t phase,fx3_fixture_gate *gate) { block_phase=phase; block_gate=gate; }
__attribute__((visibility("default"))) void fx3_owner_fixture_body_tag(const uint8_t *tag) { memcpy(fixture_body_tag,tag,32); }
void fx3_owner_fixture_set_gate(fx3_fixture_gate *gate) {block_gate=gate;}
void fx3_owner_fixture_io_fault(uint32_t op,uint32_t fault) {f.fault_op=op;f.fault=fault;}
uint32_t fx3_owner_fixture_wire_calls(uint32_t i) {return f.io?(uint32_t)fx3_iokit_fixture_stat(f.io,i):(i<3?f.wire_counts[i]:0);}
