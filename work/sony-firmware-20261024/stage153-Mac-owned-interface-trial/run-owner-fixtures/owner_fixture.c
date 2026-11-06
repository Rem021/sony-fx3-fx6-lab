/* Own provider fixture: no IOKit headers/framework, USB library or device API. */
#include "owner_trial.h"
#include <string.h>
#include <stdatomic.h>
typedef struct { uint32_t fail, option, late_phase, calls[13], snapshots, captured, closed; uint64_t now; fx3_owner_result *result; } fixture;
static fixture f;
static atomic_flag running=ATOMIC_FLAG_INIT;
enum { MOUNTED=1, NULL_TAG=2, BAD_PROFILE=4, BODY_CHANGED=8, MOUNT_RACE=16,
       INCARNATION_RACE=32, DRIVER_REMAINS=64, NO_DRIVER=128, CLOCK_BACKWARD=256 };
static int32_t hit(unsigned phase) {
    ++f.calls[phase];
    if (f.late_phase==phase) f.now+=21000000000ull;
    return f.fail==phase?17:0;
}
static int32_t snap(void *p,fx3_owner_snapshot *s) {
    (void)p;
    unsigned phase=f.result->active_call_pending;
    ++f.snapshots;
    memset(s,0,sizeof(*s));
    s->registry_id=phase==P_AFTER?101:100; s->media_count=2; s->vid=0x054c; s->pid=0x0da1; s->location=0x02100000;
    s->storage_driver_count=(f.option&NO_DRIVER)?0:(f.captured?0:3);
    memset(s->body_tag,0x41,32);
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
    (void)p; *profile=(fx3_owner_profile){0,0,(f.option&BAD_PROFILE)?0x82:0x81,2,512,2}; return hit(P_CLAIM);
}
static int32_t release_(void *p) { (void)p; return hit(P_RELEASE); }
static int32_t return_(void *p) { (void)p; f.captured=0; return hit(P_RETURN); }
static int32_t close_(void *p) { (void)p; f.closed=1; return hit(P_CLOSE); }
static uint64_t now_(void *p) {
    (void)p;
    if ((f.option&CLOCK_BACKWARD) && f.calls[P_CAPTURE]) { f.option&=~CLOCK_BACKWARD; f.now=1; }
    else f.now+=1000;
    return f.now;
}
static void pause_(void *p,uint32_t ms) { (void)p; f.now+=(uint64_t)ms*1000000ull; }
static const fx3_owner_ops ops={snap,open_,capture_,reopen_,claim_,release_,return_,close_,now_,pause_};
__attribute__((visibility("default"))) uint32_t fx3_owner_fixture_marker(void) { return 0x46495833; }
__attribute__((visibility("default"))) void fx3_owner_fixture_reset(uint32_t fail,uint32_t option,uint32_t late) {
    memset(&f,0,sizeof(f)); f.fail=fail; f.option=option; f.late_phase=late; f.now=1000000000ull;
}
__attribute__((visibility("default"))) uint32_t fx3_owner_fixture_calls(uint32_t phase) { return phase<=12?f.calls[phase]:0; }
__attribute__((visibility("default"))) uint32_t fx3_owner_fixture_size(uint32_t which) {
    const uint32_t sizes[]={sizeof(fx3_owner_config),sizeof(fx3_owner_result),sizeof(fx3_owner_snapshot),sizeof(fx3_owner_profile),sizeof(fx3_owner_event)};
    return which<5?sizes[which]:0;
}
__attribute__((visibility("default"))) int fx3_owner_run(const fx3_owner_config *c,fx3_owner_result *r) {
    if (atomic_flag_test_and_set(&running)) return FX3_DENIED;
    f.result=r;
    int rc=fx3_owner_core(c,r,&ops,&f);
    atomic_flag_clear(&running);
    return rc;
}
