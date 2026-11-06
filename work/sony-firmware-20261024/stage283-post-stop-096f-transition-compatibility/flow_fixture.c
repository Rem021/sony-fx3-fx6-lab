/* Own fake native pipes for the real C orchestration; no IOKit linkage. */
#include "service_flow.h"
#include "entry_shared.h"
#include "descriptor_policy.h"
#include "transition_identity.h"
#include "derived_profile_fixture.h"
#include "device_access.h"
#include <CommonCrypto/CommonDigest.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
typedef struct{uint32_t kind,command,mode,offset,fail,stop_on_write,header_variant;uint64_t deadline;fx3_owner_control *control;int device_owned,interface_owned,shared_ready;} pipe_state;
typedef struct{pipe_state msc,service;fx3_identity initial;uint32_t option,return_samples;} fake_flow;
static uint64_t now(void *unused){(void)unused;return fx3_entry_clock_ns();}
static fx3_call control(void *p,const uint8_t setup[8],uint32_t ms){(void)ms;pipe_state *s=p;if(!fx3_fixed_control_allowed(1,s->device_owned,s->interface_owned,s->shared_ready,setup))return(fx3_call){FX3T_DENIED,0,1,0,0};return(fx3_call){FX3T_OK,0,1,1,0};}
static fx3_call put(void *p,const uint8_t *data,uint32_t n,uint32_t ms){
    (void)ms;pipe_state *s=p;if(s->fail && s->mode==2)return(fx3_call){FX3T_STALL,-99,1,0,0};
    if(n==17){s->kind=1;s->offset=0;}else if(n==516){s->kind=0;s->command=(uint16_t)~((uint16_t)data[0]<<8|data[1]);}else return(fx3_call){FX3T_SHAPE,0,1,0,0};
    if(s->stop_on_write && s->mode==1)atomic_store(&s->control->stop_requested,1);
    return(fx3_call){FX3T_OK,0,1,0,0};
}
static fx3_call get(void *p,uint8_t *data,uint32_t n,uint32_t ms){
    (void)ms;pipe_state *s=p;memset(data,0,n);
    if(!s->kind){
        if(n!=516)return(fx3_call){FX3T_SHAPE,0,1,1,0};
        unsigned code=s->command==1?8:s->command==3?4:6;uint16_t wire=(uint16_t)~code;data[0]=(uint8_t)(wire>>8);data[1]=(uint8_t)wire;
        if(code==8)for(unsigned i=4;i<n;i++)data[i]=(uint8_t)i;
        if(code==6)data[4]=1;
    }else if(s->kind==1){
        if(n!=12)return(fx3_call){FX3T_SHAPE,0,1,1,0};
        if(s->header_variant==10)return(fx3_call){FX3T_IO,-536870199,1,0,0};
        uint8_t header[12]={88,0,0,0,16,0,1,0,3,0,0,1};
        switch(s->header_variant){
            case 2:header[0]=89;break;case 3:header[4]=0x11;break;case 4:header[6]=2;break;
            case 5:header[8]=0;break;case 6:header[9]=1;break;case 7:header[10]=1;break;
            case 8:header[11]=0;break;case 9:header[0]=0;header[8]=0;header[11]=0;break;default:break;
        }
        memcpy(data,header,12);s->kind=2;
        if(s->header_variant==1)return(fx3_call){FX3T_OK,0,1,1,11};
    }else{for(unsigned i=0;i<n;i++)data[i]=(uint8_t)(s->offset+i);s->offset+=n;}
    return(fx3_call){FX3T_OK,0,1,1,n};
}
static fx3_call dispose(void *p){(void)p;return(fx3_call){FX3T_GONE,-2,1,0,0};}
static const fx3_stream_ops stream_ops={now,control,put,get,dispose};
static int take(void *p,fx3_service_flow *f){
    fake_flow *b=p;f->current=b->initial;if(fx3_route_init(&f->route,&b->initial))return FX3T_DENIED;
    if(fx3_witness_init(&f->route.witness,&b->initial,f->journal->nonce))return FX3T_DENIED;
    int rc=fx3_stream_bind(&f->route,&f->msc,&b->initial,1,f->deadline,&stream_ops,&b->msc);if(!rc)f->taken=1;return rc;
}
static int observe(void *p,fx3_service_flow *f,uint32_t mode,fx3_identity *out){
    (void)f;fake_flow *b=p;*out=b->initial;
    if(mode==2 && (b->option&16384))return FX3T_GONE;
    out->registry_id=mode==2?200:300;out->pid=mode==2?0x0336:0x0da1;
    if(mode==2){out->identity_kind=FX3_ID_CONTROLLED_PORT;memset(out->serial_tag,0,32);out->location=0x01200000;out->logical_port=502;
        if(b->option&268435456)out->physical_port++;
        if(b->option&1073741824){out->identity_kind=FX3_ID_SERIAL;memset(out->serial_tag,'B',32);}
    }else{
        b->return_samples++;
        if((b->option&(1u<<31)) || ((b->option&(1u<<23)) && b->return_samples<=2)){
            out->registry_id=250;out->pid=0x096f;
        }
        if(b->option&536870912)memset(out->serial_tag,'B',32);
    }
    return FX3T_OK;
}
static int open_service(void *p,fx3_service_flow *f,const fx3_identity *id){
    fake_flow *b=p;int rc=fx3_stream_bind(&f->route,&f->service,id,2,f->deadline,&stream_ops,&b->service);if(rc)return rc;
    f->service.acquire_device_open_raw=(b->option&131072u)?FX3_DEVICE_EXCLUSIVE_ERROR:0;
    f->service.acquire_device_open_disposition=fx3_device_open_disposition(f->service.acquire_device_open_raw);
    b->service.device_owned=f->service.acquire_device_open_disposition==FX3_DEVICE_OWNED;
    if(b->option&(32768u|65536u)){
        f->service.acquire_step=(b->option&32768u)?203u:210u;
        f->service.acquire_raw_return=(b->option&32768u)?-536870210:FX3_DEVICE_EXCLUSIVE_ERROR;
        if(b->option&32768u){f->service.acquire_device_open_raw=f->service.acquire_raw_return;f->service.acquire_device_open_disposition=FX3_DEVICE_NONE;b->service.device_owned=0;}
        f->service.failed=f->route.failed=1;return FX3T_UNKNOWN;
    }
    uint8_t raw[128]={9,2,32,0,1,1,0,0x80,50, 9,4,0,0,2,255,255,255,0, 7,5,6,2,0,2,0, 7,5,0x85,2,0,2,0};uint32_t n=32;
    if(b->option&67108864){n=sizeof(fx3_derived_ss);memcpy(raw,fx3_derived_ss,n);}
    else if(b->option&134217728){n=sizeof(fx3_derived_lsfs);memcpy(raw,fx3_derived_lsfs,n);}
    if(b->option&33554432)raw[23]=4; /* Artificial1024B mismatch, not device data. */
    f->service.configurations=f->service.active_configuration=1;f->service.descriptor_length=f->service.descriptor_copied=n;
    memcpy(f->service.descriptor,raw,n);CC_SHA256(raw,n,f->service.descriptor_hash);
    rc=fx3_parse_service_config(raw,n,1,1,&f->service.observed_profile);
    if(!rc){f->service.observed_profile.pipe_in=n==32?2:1;f->service.observed_profile.pipe_out=n==32?1:2;}
    f->service.acquire_policy_return=rc;f->service.control_only=rc!=FX3T_OK;
    f->service.acquire_step=rc?206u:110u+f->service.observed_profile.endpoints;
    f->service.acquire_raw_return=0;
    if(rc && !b->service.device_owned){f->service.acquire_policy_return=FX3T_DENIED;f->service.failed=f->route.failed=1;return FX3T_DENIED;}
    b->service.interface_owned=rc==0;
    b->service.shared_ready=!b->service.device_owned && b->service.interface_owned;
    return FX3T_OK;
}
static fx3_call driver_return(void *p,fx3_service_flow *f,const fx3_identity *id){(void)p;int rc=fx3_route_observe_return(&f->route,id);return(fx3_call){rc,0,1,0,0};}
static void pause(void *p,uint32_t ms){
    fake_flow *b=p;
    if(b->option&16384){struct timespec t={ms/1000,(long)(ms%1000)*1000000L};nanosleep(&t,NULL);}
}
static const fx3_flow_ops flow_ops={take,observe,open_service,driver_return,now,pause};
int fx3_fixture_service_run(fx3_service_flow *f,fx3_owner_result *report,fx3_owner_control *control_,const fx3_owner_config *cfg,uint32_t option){
    fake_flow *b=calloc(1,sizeof(*b));if(!b)return -1;
    b->initial.registry_id=100;b->initial.location=cfg->location;b->initial.vid=0x054c;b->initial.pid=0x0da1;
    b->initial.identity_kind=FX3_ID_SERIAL;b->initial.physical_port=500;b->initial.logical_port=501;memcpy(b->initial.serial_tag,cfg->expected_body_tag,32);
    b->option=option;b->msc.mode=1;b->msc.device_owned=1;b->service.mode=2;b->service.fail=(option&4194304)!=0;
    b->service.header_variant=((option>>18)&3u)|(((option>>10)&3u)<<2);
    b->msc.stop_on_write=(option&16777216)!=0;b->msc.control=control_;
    f->journal=fx3_flow_current_journal();f->owner=report;f->control=control_;f->deadline=cfg->work_deadline_ns;memcpy(f->key,cfg->privacy_key,32);
    int rc=fx3_flow_run(f,&flow_ops,b);if(!f->retained)free(b);return rc;
}
