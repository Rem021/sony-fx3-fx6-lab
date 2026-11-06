/* Actual bounded C orchestration used by native and fake providers alike.
 * Peer/single-use approval and original ownership are supplied by the entry. */
#include "service_flow.h"
#include "transition_identity.h"
#include "transition_limits.h"
#include <string.h>
static int healthy(fx3_service_flow *f,const fx3_flow_ops *o,void *p){uint64_t n=o->now(p);return n && n<f->deadline && !atomic_load(&f->control->stop_requested) && f->journal && !f->journal->failed;}
static int audit(void *p,uint32_t op,uint32_t point,const fx3_call *call){return fx3_flow_emit(p,op,point,call);}
static void attach(fx3_service_flow *f,fx3_stream *s){s->audit=audit;s->audit_context=f;}
static int observe(fx3_service_flow *f,const fx3_flow_ops *o,void *p,uint32_t mode){
    for(unsigned n=0;n<FX3_TRANSITION_MAX_SAMPLES && healthy(f,o,p);n++){
        fx3_identity id={0};int raw=o->observe(p,f,mode,&id);
        int rc=fx3_witness_sample(&f->route.witness,mode,raw,&id,o->now(p));
        f->current=id;fx3_call sampled={.status=rc,.raw_return=raw,.returned=1};
        if(fx3_flow_emit(f,mode==2?61:63,2,&sampled))return FX3T_UNKNOWN;
        if(rc==FX3T_OK){
            if(mode==2 && fx3_route_candidate(&f->route,&id,2))return FX3T_DENIED;
            f->current=id;return fx3_flow_emit(f,40+mode,2,NULL)?FX3T_UNKNOWN:FX3T_OK;
        }
        if(rc!=FX3T_GONE && rc!=FX3T_BUSY)return rc;
        o->pause(p,FX3_TRANSITION_SAMPLE_MS);
    }
    return FX3T_UNKNOWN;
}
int fx3_flow_run(fx3_service_flow *f,const fx3_flow_ops *o,void *p){
    if(!f || !o || !o->take_msc || !o->observe || !o->open_service || !o->driver_return || !o->now || !o->pause || !healthy(f,o,p))return -1;
    f->retained=1;
    if(fx3_flow_emit(f,30,2,NULL))return -1;
    int rc=o->take_msc(p,f);if(rc || !f->taken)goto held;
    if(fx3_flow_emit(f,31,2,NULL))goto held;
    attach(f,&f->msc);
    if(!healthy(f,o,p))goto held;
    rc=fx3_stream_start(&f->msc);if(rc!=FX3T_OK && rc!=FX3T_STALL)goto held;
    if(fx3_stream_exchange_fixed(&f->msc))goto held;
    if(fx3_stream_retire(&f->msc))goto held;
    if(fx3_witness_arm(&f->route.witness,2,o->now(p),f->deadline) || fx3_flow_emit(f,60,2,NULL))goto held;
    if(observe(f,o,p,2))goto held;
    if(!healthy(f,o,p))goto held;
    if(fx3_flow_emit(f,11,0,NULL))goto held;
    rc=o->open_service(p,f,&f->current);
    fx3_call acquired={.status=rc,.raw_return=f->service.acquire_raw_return,.returned=1};
    if(fx3_flow_emit(f,11,1,&acquired) || rc)goto held;
    attach(f,&f->service);
    if(!healthy(f,o,p))goto held;
    if(f->service.control_only){
        rc=fx3_stream_control_end(&f->service);if(rc!=FX3T_OK && rc!=FX3T_STALL)goto held;
    }else{
        rc=fx3_stream_start(&f->service);if(rc!=FX3T_OK && rc!=FX3T_STALL)goto held;
        if(fx3_stream_exchange_fixed(&f->service))goto held;
        if(fx3_stream_read0(&f->service,f->key,&f->read))goto held;
        if(!healthy(f,o,p))goto held;
        rc=fx3_stream_stop(&f->service);if(rc!=FX3T_OK && rc!=FX3T_STALL)goto held;
    }
    if(fx3_stream_retire(&f->service))goto held;
    f->objects_disposed=1;
    if(fx3_witness_arm(&f->route.witness,1,o->now(p),f->deadline) || fx3_flow_emit(f,62,2,NULL))goto held;
    if(observe(f,o,p,1))goto held;
    f->normal_seen=1;
    if(!healthy(f,o,p))goto held;
    if(fx3_flow_emit(f,9,0,NULL))goto held;
    fx3_call returned=o->driver_return(p,f,&f->current);
    if(fx3_flow_emit(f,9,1,&returned) || returned.status!=FX3T_OK || !returned.returned)goto held;
    f->driver_returned=1;f->finished=1;f->retained=0;
    if(fx3_flow_emit(f,f->service.control_only?52:50,3,NULL)){f->retained=1;return -1;}return 0;
held:
    f->retained=f->taken?1:0;
    (void)fx3_flow_emit(f,51,3,NULL);return -1;
}
