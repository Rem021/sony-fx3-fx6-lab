#include "transition_identity.h"
#include <string.h>
static int nonzero(const uint8_t *p,unsigned n){uint8_t sum=0;while(n--)sum|=*p++;return sum!=0;}
static int basic(const fx3_identity *id){return id && id->registry_id && id->physical_port && id->logical_port && id->location && id->vid==0x54c;}
static int serial(const fx3_port_witness *w,const fx3_identity *id){return id->identity_kind==FX3_ID_SERIAL && !memcmp(id->serial_tag,w->origin_serial_tag,32);}
static int fail(fx3_port_witness *w,int rc){w->state=FX3_W_FAILED;return rc;}
int fx3_witness_init(fx3_port_witness *w,const fx3_identity *id,const uint8_t nonce[16]){
    if(!w || w->state || !basic(id) || id->pid!=0x0da1 || id->identity_kind!=FX3_ID_SERIAL || !nonzero(id->serial_tag,32) || !nonce || !nonzero(nonce,16))return FX3T_DENIED;
    memset(w,0,sizeof(*w));w->source_node=id->registry_id;w->physical_port=id->physical_port;w->initial_location=id->location;
    memcpy(w->origin_serial_tag,id->serial_tag,32);memcpy(w->nonce,nonce,16);w->state=FX3_W_SOURCE;w->flags=1;return FX3T_OK;
}
int fx3_witness_arm(fx3_port_witness *w,uint32_t mode,uint64_t now,uint64_t overall){
    if(!w || !((mode==2 && w->state==FX3_W_SOURCE)||(mode==1 && w->state==FX3_W_SERVICE)))return FX3T_DENIED;
    if(!now || now<w->last_ns || now>=overall || now>UINT64_MAX-2000000000ull)return fail(w,FX3T_TIMEOUT);
    w->armed_ns=w->last_ns=now;w->deadline_ns=now+2000000000ull;
    if(w->deadline_ns>overall)w->deadline_ns=overall;
    w->observations=0;w->state=mode==2?FX3_W_ENTER_ARMED:FX3_W_RETURN_ARMED;w->flags|=mode==2?2:8;return FX3T_OK;
}
int fx3_witness_matches(const fx3_port_witness *w,const fx3_identity *id,uint32_t mode){
    if(!w || !basic(id) || id->physical_port!=w->physical_port)return 0;
    if(mode==2 && w->state==FX3_W_SERVICE && id->pid==0x0336 && id->registry_id==w->service_node && id->identity_kind==w->service_kind)
        return id->identity_kind==FX3_ID_CONTROLLED_PORT?!nonzero(id->serial_tag,32):serial(w,id);
    return mode==1 && w->state==FX3_W_RETURNED && id->pid==0x0da1 && id->registry_id==w->return_node && id->location==w->initial_location && serial(w,id);
}
int fx3_witness_sample(fx3_port_witness *w,uint32_t mode,int status,const fx3_identity *id,uint64_t now){
    if(!w || !((mode==2 && w->state==FX3_W_ENTER_ARMED)||(mode==1 && w->state==FX3_W_RETURN_ARMED)))return FX3T_DENIED;
    if(!now || now<w->last_ns || now>=w->deadline_ns || w->observations>=20)return fail(w,FX3T_TIMEOUT);
    w->last_ns=now;w->observations++;
    if(status==FX3T_GONE)return FX3T_GONE;
    if(status!=FX3T_OK)return fail(w,status);
    if(!basic(id) || id->physical_port!=w->physical_port)return fail(w,FX3T_DENIED);
    if(mode==2){
        if(id->pid==0x0da1 && id->registry_id==w->source_node && id->location==w->initial_location && serial(w,id))return FX3T_BUSY;
        if(id->pid!=0x0336 || id->registry_id==w->source_node)return fail(w,FX3T_DENIED);
        if(id->identity_kind==FX3_ID_CONTROLLED_PORT){if(nonzero(id->serial_tag,32))return fail(w,FX3T_DENIED);}
        else if(!serial(w,id))return fail(w,FX3T_DENIED);
        w->service_node=id->registry_id;w->service_kind=id->identity_kind;w->service_ns=now;w->state=FX3_W_SERVICE;w->flags|=4;return FX3T_OK;
    }
    if(id->pid==0x0336 && id->registry_id==w->service_node && id->identity_kind==w->service_kind){
        if(id->identity_kind==FX3_ID_CONTROLLED_PORT?!nonzero(id->serial_tag,32):serial(w,id))return FX3T_BUSY;
        return fail(w,FX3T_DENIED);
    }
    if(id->pid!=0x0da1 || id->registry_id==w->source_node || id->registry_id==w->service_node || id->location!=w->initial_location || !serial(w,id))return fail(w,FX3T_DENIED);
    w->return_node=id->registry_id;w->return_ns=now;w->state=FX3_W_RETURNED;w->flags|=16;return FX3T_OK;
}
