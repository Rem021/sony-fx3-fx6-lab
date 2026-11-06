/* Own virtual USB provider. Real stream, journal, witness and flow C are linked.
 * No IOKit, camera, actual topology event, root, or real peer proof is involved. */
#include "service_flow.h"
#include "transition_identity.h"
#include "transition_limits.h"
#include "descriptor_policy.h"
#include "idle_held.h"
#include <CommonCrypto/CommonDigest.h>
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
typedef struct world world;
typedef struct {world *w;unsigned mode,cmd,kind,offset;} fake_pipe;
struct world {
    uint64_t tick;
    unsigned enter_ms,return_ms,wrong_port,opens,controls,stops;
    fake_pipe msc,service;
    fx3_identity initial;
};
static int peer_marker;
int fx3_channel_peer(const fx3_channel_config *p){return p && p->fd==peer_marker;}
int fx3_receipt_send_bytes(const fx3_channel_config *p,const uint8_t *bytes,size_t n,uint64_t deadline){
    (void)deadline;assert(fx3_channel_peer(p) && n==676 && bytes[0]==0xa0 && bytes[1]==2);return 0;
}
static uint64_t clock_now(void *p){return ((world *)p)->tick;}
static uint64_t pipe_now(void *p){return ((fake_pipe *)p)->w->tick;}
static fx3_call ctl(void *p,const uint8_t request[8],uint32_t ms){
    fake_pipe *s=p;assert(ms && ms<=1000);s->w->controls++;
    if(request[2]==0 && request[3]==0xc8)s->w->stops++;
    return (fx3_call){FX3T_OK,0,1,1,0};
}
static fx3_call put(void *p,const uint8_t *data,uint32_t n,uint32_t ms){
    fake_pipe *s=p;assert(ms && ms<=1000);
    if(n==17){s->kind=1;s->offset=0;}
    else {assert(n==516);s->kind=0;s->cmd=(uint16_t)~((uint16_t)data[0]<<8|data[1]);}
    return (fx3_call){FX3T_OK,0,1,0,0};
}
static fx3_call get(void *p,uint8_t *data,uint32_t n,uint32_t ms){
    fake_pipe *s=p;assert(ms && ms<=1000);memset(data,0,n);
    if(!s->kind){
        assert(n==516);unsigned code=s->cmd==1?8:s->cmd==3?4:6;uint16_t wire=(uint16_t)~code;
        data[0]=(uint8_t)(wire>>8);data[1]=(uint8_t)wire;if(code==6)data[4]=1;
    }else if(s->kind==1){
        assert(n==12);const uint8_t header[12]={88,0,0,0,16,0,1,0,0,0,0,1};
        memcpy(data,header,12);s->kind=2;
    }else {for(unsigned i=0;i<n;i++)data[i]=(uint8_t)(s->offset+i);s->offset+=n;}
    return (fx3_call){FX3T_OK,0,1,1,n};
}
static fx3_call dispose(void *p){(void)p;return (fx3_call){FX3T_OK,0,1,0,0};}
static const fx3_stream_ops pipes={pipe_now,ctl,put,get,dispose};
static int take(void *p,fx3_service_flow *f){
    world *w=p;f->current=w->initial;
    assert(!fx3_route_init(&f->route,&w->initial));
    assert(!fx3_witness_init(&f->route.witness,&w->initial,f->journal->nonce));
    int rc=fx3_stream_bind(&f->route,&f->msc,&w->initial,1,f->deadline,&pipes,&w->msc);
    if(!rc)f->taken=1;return rc;
}
static fx3_identity service(world *w){
    fx3_identity x=w->initial;x.registry_id=200;x.pid=0x0336;x.location=0x01200000;
    x.logical_port=502;x.identity_kind=FX3_ID_CONTROLLED_PORT;memset(x.serial_tag,0,32);return x;
}
static int observe(void *p,fx3_service_flow *f,uint32_t mode,fx3_identity *out){
    world *w=p;uint64_t elapsed=w->tick-f->route.witness.armed_ns;
    if(mode==2){
        if(elapsed<(uint64_t)w->enter_ms*1000000ull){
            if(elapsed<200000000ull){*out=w->initial;return FX3T_OK;}
            return FX3T_GONE;
        }
        *out=service(w);if(w->wrong_port)out->physical_port++;return FX3T_OK;
    }
    if(elapsed<(uint64_t)w->return_ms*1000000ull){*out=service(w);return FX3T_OK;}
    *out=w->initial;out->registry_id=300;return FX3T_OK;
}
static int open_service(void *p,fx3_service_flow *f,const fx3_identity *id){
    world *w=p;w->opens++;
    int rc=fx3_stream_bind(&f->route,&f->service,id,2,f->deadline,&pipes,&w->service);
    if(rc)return rc;
    const uint8_t raw[32]={9,2,32,0,1,1,0,0x80,50,9,4,0,0,2,255,255,255,0,7,5,6,2,0,2,0,7,5,0x85,2,0,2,0};
    f->service.configurations=f->service.active_configuration=1;
    f->service.descriptor_length=f->service.descriptor_copied=sizeof(raw);
    memcpy(f->service.descriptor,raw,sizeof(raw));CC_SHA256(raw,sizeof(raw),f->service.descriptor_hash);
    rc=fx3_parse_service_config(raw,sizeof(raw),1,1,&f->service.observed_profile);
    assert(!rc);f->service.observed_profile.pipe_in=2;f->service.observed_profile.pipe_out=1;
    return FX3T_OK;
}
static fx3_call driver_return(void *p,fx3_service_flow *f,const fx3_identity *id){
    (void)p;int rc=fx3_route_observe_return(&f->route,id);return (fx3_call){rc,0,1,0,0};
}
static void pause_clock(void *p,uint32_t ms){world *w=p;assert(ms==100);w->tick+=(uint64_t)ms*1000000ull;}
static const fx3_flow_ops ops={take,observe,open_service,driver_return,clock_now,pause_clock};
int main(int argc,char **argv){
    assert(argc==3 && geteuid()!=0);unsigned scenario=(unsigned)strtoul(argv[1],NULL,10);
    world w={.tick=1000000000ull,.enter_ms=3200,.return_ms=3600};
    if(scenario==1)w.enter_ms=6000;
    if(scenario==2){w.enter_ms=300;w.wrong_port=1;}
    if(scenario==3)w.enter_ms=6000;
    w.msc.w=w.service.w=&w;w.msc.mode=1;w.service.mode=2;
    w.initial=(fx3_identity){.registry_id=100,.location=0x01100000,.vid=0x054c,.pid=0x0da1,
        .physical_port=500,.logical_port=501,.identity_kind=FX3_ID_SERIAL};
    memset(w.initial.serial_tag,'A',32);
    fx3_owner_result owner={0};fx3_owner_control control={.abi=FX3_OWNER_ABI};
    fx3_channel_config peer={.fd=12345,.deadline_ns=30000000000ull};peer_marker=peer.fd;
    uint8_t nonce[16];memset(nonce,'N',sizeof(nonce));
    fx3_receipt_meta meta={.uid=(uint32_t)geteuid(),.pid=1234,.sec=100,.usec=200,.nonce=nonce,.grant="offline-timing-263"};
    fx3_flow_journal journal={.fd=-1};assert(!fx3_flow_journal_open(&journal,&peer,&meta,argv[2]));
    fx3_service_flow f={.owner=&owner,.control=&control,.journal=&journal,.deadline=21000000000ull};
    if(scenario==3)f.deadline=w.tick+3000000000ull;
    memset(f.key,'K',sizeof(f.key));
    int rc=fx3_flow_run(&f,&ops,&w);unsigned idle=~0u;
    if(scenario==0){assert(!rc && f.finished && !f.retained && w.opens==1 && w.stops==1);}
    else {
        assert(rc && f.retained && !f.finished && w.opens==0 && w.stops==0);
        atomic_store(&owner.owner_retained,1);idle=fx3_idle_held_flow_reasons(&f);assert(!idle);
        if(scenario==1)assert(w.tick==6000000000ull && f.route.witness.observations==50);
        if(scenario==3)assert(w.tick==4000000000ull && f.route.witness.deadline_ns==f.deadline);
        atomic_store(&owner.wire_pending,2);assert(fx3_idle_held_flow_reasons(&f)&FX3_IDLE_PENDING);atomic_store(&owner.wire_pending,0);
        f.service.backend=&w;assert(fx3_idle_held_flow_reasons(&f)&FX3_IDLE_SERVICE);f.service.backend=NULL;
        f.msc.unreturned=1;assert(fx3_idle_held_flow_reasons(&f)&FX3_IDLE_MSC);f.msc.unreturned=0;
        f.route.active=1;assert(fx3_idle_held_flow_reasons(&f)&FX3_IDLE_ROUTE);f.route.active=0;
        assert(!fx3_idle_held_flow_reasons(&f));
    }
    printf("{\"scenario\":%u,\"flow_return\":%d,\"frames\":%u,\"virtual_elapsed_ms\":%llu,\"opens\":%u,\"STOPs\":%u,\"flow_object_classifier\":%u,\"actual_camera\":false}\n",
        scenario,rc,journal.sequence,(unsigned long long)((w.tick-1000000000ull)/1000000ull),w.opens,w.stops,idle);
    assert(!fx3_flow_journal_close(&journal));return 0;
}
