#include "idle_held.h"
unsigned fx3_idle_held_flow_reasons(const fx3_service_flow *f) {
    if(!f || !f->owner || !f->journal)return FX3_IDLE_MISSING;
    unsigned r=0;
    if(!f->taken || !f->retained || f->finished || f->normal_seen || f->driver_returned)
        r|=FX3_IDLE_NOT_HELD;
    if(atomic_load(&f->owner->active_call_pending) || atomic_load(&f->owner->wire_pending) ||
       atomic_load(&f->msc.busy) || atomic_load(&f->service.busy) ||
       atomic_load(&f->route.return_pending))r|=FX3_IDLE_PENDING;
    if(!f->route.initialized || f->route.active || f->route.phase!=1 || f->route.failed ||
       f->route.witness.service_node ||
       (f->route.witness.state!=FX3_W_ENTER_ARMED && f->route.witness.state!=FX3_W_FAILED))
        r|=FX3_IDLE_ROUTE;
    if(f->msc.route || f->msc.backend || !f->msc.dispose_attempted || f->msc.unreturned ||
       f->msc.failed || !f->msc.exchange_finished || !f->msc.last_call.returned ||
       (f->msc.last_call.status!=FX3T_OK && f->msc.last_call.status!=FX3T_GONE))
        r|=FX3_IDLE_MSC;
    if(f->service.route || f->service.backend || f->service.mode || f->service.generation ||
       f->service.started || f->service.native_calls || f->service.acquire_step ||
       f->service.descriptor_length || f->service.unreturned)r|=FX3_IDLE_SERVICE;
    if(f->journal->failed || f->journal->fd<0)r|=FX3_IDLE_JOURNAL;
    if(!atomic_load(&f->owner->owner_retained) || f->owner->clock_invalid ||
       f->owner->cleanup_error)r|=FX3_IDLE_OWNER;
    return r;
}
