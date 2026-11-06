/* Shared by the native IOKit candidate and an own, IOKit-free fixture DSO. */
#include "owner_trial.h"
#include <string.h>

static int record(fx3_owner_result *r, uint32_t phase, int32_t code) {
    if (r->event_count >= FX3_OWNER_EVENTS) return 0;
    r->events[r->event_count++] = (fx3_owner_event){phase, code};
    return 1;
}
static int tag_present(const uint8_t tag[32]) {
    uint8_t value = 0;
    for (unsigned i=0; i<32; ++i) value |= tag[i];
    return value != 0;
}
static int identity(const fx3_owner_config *c, const fx3_owner_snapshot *s) {
    return s->registry_id && s->vid==c->vid && s->pid==c->pid && s->location==c->location && tag_present(s->body_tag);
}
static int baseline(const fx3_owner_snapshot *a, const fx3_owner_snapshot *b, int same_incarnation) {
    return !memcmp(a->body_tag,b->body_tag,32) && (!same_incarnation || a->registry_id==b->registry_id);
}
static int ready(const fx3_owner_config *c, fx3_owner_result *r, fx3_owner_control *control, const fx3_owner_ops *o, void *p, uint64_t *last) {
    uint64_t now=o->now_ns(p);
    if (now < *last) r->clock_invalid=1;
    *last=now;
    return !r->clock_invalid && !atomic_load_explicit(&control->stop_requested,memory_order_acquire) && now < c->work_deadline_ns;
}

int fx3_owner_core(const fx3_owner_config *c, fx3_owner_result *r, fx3_owner_control *control, const fx3_owner_ops *o, void *p) {
    if (!r) return FX3_DENIED;
    size_t pending=offsetof(fx3_owner_result,active_call_pending);
    memset(r,0,pending);
    r->persistent_camera_or_vendor_commands=0;
    memset((uint8_t *)r+offsetof(fx3_owner_result,before),0,sizeof(*r)-offsetof(fx3_owner_result,before));
    atomic_store_explicit(&r->active_call_pending,0,memory_order_release);
    atomic_store(&r->owner_retained,0); atomic_store(&r->session_state,0);
    atomic_store(&r->wire_pending,0); atomic_store(&r->vendor_attempted,0);
    r->abi=FX3_OWNER_ABI; r->status=FX3_DENIED;
    if (!c || !o || !control || control->abi!=FX3_OWNER_ABI || control->reserved[0] || control->reserved[1] || c->abi!=FX3_OWNER_ABI || c->arm!=FX3_OWNER_ARM || c->vid!=0x054c || c->pid!=0x0da1 ||
        !c->location || c->capture_permitted>1 || c->protocol_scope>2 || c->work_deadline_ns>=c->final_deadline_ns ||
        !tag_present(c->privacy_key) || !tag_present(c->expected_body_tag)) return FX3_DENIED;
    if (!o->snapshot || !o->open || !o->capture || !o->reopen || !o->claim || !o->release_interface ||
        !o->return_driver || !o->close || !o->now_ns || !o->pause_ms ||
        (c->protocol_scope && (!o->session || !o->cleanup_allowed))) return FX3_DENIED;
    uint64_t last=0;
    int opened=0, work_ok=0, observed=0, rc=0, baseline_valid=0;
    fx3_owner_snapshot current={0};
    r->status=FX3_RETURN_UNKNOWN;
    if (!ready(c,r,control,o,p,&last)) goto cleanup;
    r->active_call_pending=P_BEFORE; rc=o->snapshot(p,&r->before); r->active_call_pending=0; record(r,P_BEFORE,rc);
    if (rc || !identity(c,&r->before) || memcmp(c->expected_body_tag,r->before.body_tag,32)) goto cleanup;
    baseline_valid=1;
    if (r->before.mounted_count || r->before.media_unknown) goto cleanup;
    if (r->before.storage_driver_count && !c->capture_permitted) goto cleanup;
    if (!ready(c,r,control,o,p,&last)) goto cleanup;
    opened=1;
    r->active_call_pending=P_OPEN; rc=o->open(p); r->active_call_pending=0; record(r,P_OPEN,rc);
    if (rc) goto cleanup;
    if (r->before.storage_driver_count) {
        if (!ready(c,r,control,o,p,&last)) goto cleanup;
        r->active_call_pending=P_PRE_CAPTURE; rc=o->snapshot(p,&current); r->active_call_pending=0; record(r,P_PRE_CAPTURE,rc);
        if (rc || !identity(c,&current) || !baseline(&r->before,&current,1) || current.mounted_count || current.media_unknown) goto cleanup;
        if (!ready(c,r,control,o,p,&last)) goto cleanup;
        r->capture_attempted=1;
        r->active_call_pending=P_CAPTURE; rc=o->capture(p); r->active_call_pending=0; record(r,P_CAPTURE,rc);
        if (rc || !ready(c,r,control,o,p,&last)) goto cleanup;
        r->active_call_pending=P_REOPEN; rc=o->reopen(p); r->active_call_pending=0; record(r,P_REOPEN,rc);
        if (rc) goto cleanup;
    }
    if (!ready(c,r,control,o,p,&last)) goto cleanup;
    r->active_call_pending=P_PRE_CLAIM; rc=o->snapshot(p,&current); r->active_call_pending=0; record(r,P_PRE_CLAIM,rc);
    if (rc || !identity(c,&current) || !baseline(&r->before,&current,1) || current.mounted_count || current.media_unknown || current.storage_driver_count) goto cleanup;
    if (!ready(c,r,control,o,p,&last)) goto cleanup;
    r->claim_attempted=1;
    r->active_call_pending=P_CLAIM; rc=o->claim(p,&r->profile); r->active_call_pending=0; record(r,P_CLAIM,rc);
    if (rc) goto cleanup;
    r->interface_claimed=1;
    rc=!(r->profile.interface_number==0 && r->profile.alternate==0 && r->profile.in_address==0x81 &&
        r->profile.out_address==0x02 && r->profile.max_packet==512 && r->profile.endpoints==2 &&
        r->profile.pipe_in>=1 && r->profile.pipe_in<=2 && r->profile.pipe_out>=1 && r->profile.pipe_out<=2 &&
        r->profile.pipe_in!=r->profile.pipe_out);
    record(r,P_PROFILE,rc);
    if (rc || !ready(c,r,control,o,p,&last)) goto cleanup;
    work_ok=1;
    if(c->protocol_scope) {
        r->active_call_pending=P_SESSION; rc=o->session(p); r->active_call_pending=0; record(r,P_SESSION,rc);
        if(rc)work_ok=0;
    }
cleanup:
    /* Ownership must outlive an outstanding native call or uncertain vendor
     * session. The caller retains the heap provider AND process in this case.
     * No release/driver return/close/cache-success inference is allowed. */
    if(c->protocol_scope && o->cleanup_allowed && !o->cleanup_allowed(p)) {
        atomic_store_explicit(&r->owner_retained,1,memory_order_release);
        r->status=FX3_RETURN_UNKNOWN; return FX3_RETAINED;
    }
    /* Cleanup is explicit and single-use; a passed work deadline does not skip it. */
    if (r->claim_attempted) {
        r->active_call_pending=P_RELEASE; rc=o->release_interface(p); r->active_call_pending=0; record(r,P_RELEASE,rc);
        if (rc) r->cleanup_error=1;
    }
    if (r->capture_attempted) {
        r->active_call_pending=P_RETURN; rc=o->return_driver(p); r->active_call_pending=0; record(r,P_RETURN,rc);
        if (rc) r->cleanup_error=1;
    }
    if (opened) {
        r->active_call_pending=P_CLOSE; rc=o->close(p); r->active_call_pending=0; record(r,P_CLOSE,rc);
        if (rc) r->cleanup_error=1;
    }
    if (!baseline_valid) return r->status;
    /* Cached observations only. Re-enumeration may give a new registry ID. */
    for (unsigned n=0; n<40 && r->event_count<FX3_OWNER_EVENTS; ++n) {
        uint64_t now=o->now_ns(p);
        if (now<last) r->clock_invalid=1;
        last=now;
        if (r->clock_invalid || now>=c->final_deadline_ns) break;
        r->active_call_pending=P_AFTER; rc=o->snapshot(p,&r->after); r->active_call_pending=0; record(r,P_AFTER,rc);
        if (!rc && identity(c,&r->after) && baseline(&r->before,&r->after,0) && !r->after.media_unknown &&
            r->after.media_count>=r->before.media_count && r->after.storage_driver_count>=r->before.storage_driver_count) {
            observed=1; break;
        }
        o->pause_ms(p,100);
    }
    if (observed && !r->cleanup_error && !r->clock_invalid) r->status=work_ok?FX3_OBSERVED:FX3_ABORTED_RETURN_OBSERVED;
    return r->status;
}
