/* Fixed authentication exchanges and read0 only. No file, mode fallback,
 * firmware writer, loader, retry, reset or thread-completion assertion. */
#include "stream.h"
#include <CommonCrypto/CommonHMAC.h>
#include <CommonCrypto/CommonDigest.h>
#include <string.h>
#include "public_material.h"
static const uint8_t start_packet[8]={0x43,1,0xff,0x37,0xaa,0xd7,0,0};
static const uint8_t stop_packet[8]={0x43,1,0,0xc8,0x55,0x28,0,0};
static const uint8_t read0_packet[17]={5,0,0,0,0x10,0,1,0,0,0,0,0,0,0,0x1f,0,0};
static int zero(const uint8_t *p,unsigned n){uint8_t x=0;while(n--)x|=*p++;return !x;}
static void wipe(void *p,unsigned n){volatile uint8_t *v=p;while(n--)*v++=0;}
static int same(const fx3_identity *a,const fx3_identity *b){return a->location==b->location && a->vid==0x054c && b->vid==0x054c && !memcmp(a->body_tag,b->body_tag,32);}
static int identity_ok(const fx3_identity *a){return a && a->registry_id && a->location && a->vid==0x054c && !zero(a->body_tag,32);}
int fx3_route_init(fx3_route *r,const fx3_identity *a){
    if(!r || r->initialized || !identity_ok(a) || a->pid!=0x0da1)return FX3T_DENIED;
    memset(r,0,sizeof(*r));r->initial=*a;r->initialized=1;atomic_init(&r->return_pending,0);return FX3T_OK;
}
int fx3_route_candidate(const fx3_route *r,const fx3_identity *a,uint32_t mode){
    if(!r || !r->initialized || r->failed || r->active || !identity_ok(a) || !same(a,&r->initial))return FX3T_DENIED;
    if(!((r->phase==0 && mode==1 && a->pid==0x0da1 && a->registry_id==r->initial.registry_id) ||
         (r->phase==1 && mode==2 && a->pid==0x0336)))return FX3T_DENIED;
    for(unsigned i=0;i<r->phase;i++)if(a->registry_id==r->used_registry[i])return FX3T_DENIED;
    return FX3T_OK;
}
static int bind(fx3_route *r,fx3_stream *s,const fx3_identity *a,uint32_t mode,uint64_t deadline,const fx3_stream_ops *ops,void *backend,uint32_t busy){
    if(!s || s->route || fx3_route_candidate(r,a,mode) || !ops || !ops->now_ns || !ops->control || !ops->write || !ops->read || !ops->dispose)return FX3T_DENIED;
    uint64_t now=ops->now_ns(backend);if(!now || deadline<=now)return FX3T_DENIED;
    memset(s,0,sizeof(*s));s->route=r;s->identity=*a;s->mode=mode;s->ops=*ops;s->backend=backend;
    s->generation=++r->generation;s->deadline_ns=deadline;s->last_now=now;s->next_command=1;
    r->used_registry[r->phase]=a->registry_id;r->active=1;atomic_init(&s->busy,busy);return FX3T_OK;
}
int fx3_stream_bind(fx3_route *r,fx3_stream *s,const fx3_identity *a,uint32_t mode,uint64_t deadline,const fx3_stream_ops *ops,void *backend){return bind(r,s,a,mode,deadline,ops,backend,0);}
int fx3_stream_bind_acquiring(fx3_route *r,fx3_stream *s,const fx3_identity *a,uint32_t mode,uint64_t deadline,const fx3_stream_ops *ops,void *backend){return bind(r,s,a,mode,deadline,ops,backend,1);}
static int lock(fx3_stream *s){
    if(!s || !s->route || !s->route->active || s->route->failed || s->generation!=s->route->generation || s->failed)return FX3T_DENIED;
    uint32_t n=0;return atomic_compare_exchange_strong(&s->busy,&n,1)?FX3T_OK:FX3T_BUSY;
}
static int leave(fx3_stream *s,int rc){if(rc!=FX3T_OK && rc!=FX3T_STALL){s->failed=1;s->route->failed=1;}atomic_store(&s->busy,0);return rc;}
static uint32_t timeout(fx3_stream *s){
    uint64_t now=s->ops.now_ns(s->backend);if(!now || now<s->last_now || now>=s->deadline_ns)return 0;
    s->last_now=now;uint64_t ms=(s->deadline_ns-now+999999)/1000000;return ms>1000?1000:(uint32_t)ms;
}
static int audit(fx3_stream *s,uint32_t op,uint32_t point,const fx3_call *call){return s->audit?s->audit(s->audit_context,op,point,call):0;}
static int returned(fx3_stream *s,fx3_call call,uint32_t op){
    s->last_call=call;++s->native_calls;
    if(audit(s,op,1,&call))return FX3T_UNKNOWN;
    if(!call.returned){s->unreturned=1;return FX3T_UNKNOWN;}
    if(!timeout(s))return FX3T_UNKNOWN;
    return call.status;
}
static int put(fx3_stream *s,const uint8_t *p,uint32_t n){
    uint32_t ms=timeout(s);if(!ms)return FX3T_TIMEOUT;
    uint32_t op=n==17?4:2;if(audit(s,op,0,NULL))return FX3T_UNKNOWN;
    return returned(s,s->ops.write(s->backend,p,n,ms),op);
}
static int get(fx3_stream *s,uint8_t *p,uint32_t n,uint32_t *received,uint32_t op){
    uint32_t ms=timeout(s);if(!ms)return FX3T_TIMEOUT;
    if(audit(s,op,0,NULL))return FX3T_UNKNOWN;
    fx3_call call=s->ops.read(s->backend,p,n,ms);int rc=returned(s,call,op);
    if(rc)return rc;
    if(!call.count_known || !call.count || call.count>n)return FX3T_SHAPE;
    *received=call.count;return FX3T_OK;
}
int fx3_stream_start(fx3_stream *s){
    int rc=lock(s);if(rc)return rc;
    if(s->started || s->stop_attempted)return leave(s,FX3T_DENIED);
    uint32_t ms=timeout(s);if(!ms)return leave(s,FX3T_TIMEOUT);
    s->started=1;if(audit(s,1,0,NULL))return leave(s,FX3T_UNKNOWN);rc=returned(s,s->ops.control(s->backend,start_packet,ms),1);
    return leave(s,rc); /* Returned STALL is retained, not success or no effect. */
}
static int auth_piece(fx3_stream *s,const uint8_t request[516],uint8_t reply[516]){
    int rc=FX3T_OK;
    if(!request || !reply || !s->started || s->stop_attempted || s->exchange_finished || s->round>3)return FX3T_DENIED;
    uint8_t copy[516];memcpy(copy,request,516);memset(reply,0,516);
    unsigned cmd=(uint16_t)~((uint16_t)copy[0]<<8|copy[1]);unsigned digest=s->family==2?20:32;
    if(copy[2] || copy[3] || cmd!=s->next_command ||
       ((cmd==1 || cmd==5) && !zero(copy+4,512)) ||
       (cmd==3 && (copy[4]!=1 || !zero(copy+5+digest,511-digest)))){wipe(copy,516);return FX3T_SHAPE;}
    rc=put(s,copy,516);wipe(copy,516);uint32_t count=0;
    if(!rc)rc=get(s,reply,516,&count,3);
    if(!rc && count!=516)rc=FX3T_SHAPE;
    if(!rc){
        int code=(int)(uint16_t)~((uint16_t)reply[0]<<8|reply[1])-((int)reply[2]<<8|reply[3]);
        if(cmd==1){
            if((code!=2 && code!=8) || (s->mode==2 && code!=8) || (s->family && s->family!=(unsigned)code))rc=FX3T_SHAPE;
            else{s->family=(uint32_t)code;s->next_command=3;}
        }else if(cmd==3){if(code!=4)rc=FX3T_SHAPE;else{s->round++;s->next_command=s->round==3?5:1;}}
        else if(code!=6 || reply[4]!=1)rc=FX3T_SHAPE;
        else{s->exchange_finished=1;s->next_command=0;}
    }
    if(rc){wipe(reply,516);s->failed=s->route->failed=1;}
    return rc;
}
int fx3_stream_auth(fx3_stream *s,const uint8_t request[516],uint8_t reply[516]){
    int rc=lock(s);if(rc)return rc;return leave(s,auth_piece(s,request,reply));
}
static void auth_request(uint8_t request[516],unsigned command){
    memset(request,0,516);uint16_t encoded=(uint16_t)~command;request[0]=(uint8_t)(encoded>>8);request[1]=(uint8_t)encoded;
}
int fx3_stream_exchange_fixed(fx3_stream *s){
    int rc=lock(s);if(rc)return rc;
    if(!s->started || s->next_command!=1 || s->round || s->exchange_finished || s->stop_attempted)return leave(s,FX3T_DENIED);
    uint8_t request[516]={0},reply[516]={0},digest_input[1024]={0};
    for(unsigned round=0;round<3 && !rc;round++){
        auth_request(request,1);rc=auth_piece(s,request,reply);if(rc)break;
        auth_request(request,3);request[4]=1;
        if(s->mode==FX3_MODE_SERVICE){
            memcpy(digest_input,reply+4,512);memcpy(digest_input+512,fx3_sha256_material[round],512);
            if(!CC_SHA256(digest_input,1024,request+5))rc=FX3T_UNKNOWN;
        }else if(s->family==2){if(!CC_SHA1(reply+4,4,request+5))rc=FX3T_UNKNOWN;}
        else if(s->family==8){if(!CC_SHA256(reply+4,4,request+5))rc=FX3T_UNKNOWN;}
        else rc=FX3T_SHAPE;
        wipe(digest_input,sizeof(digest_input));wipe(reply,sizeof(reply));
        if(!rc)rc=auth_piece(s,request,reply);
    }
    if(!rc){auth_request(request,5);rc=auth_piece(s,request,reply);}
    wipe(request,sizeof(request));wipe(reply,sizeof(reply));wipe(digest_input,sizeof(digest_input));
    return leave(s,rc);
}
static int header_ok(const uint8_t h[12]){
    static const uint8_t expected[12]={88,0,0,0,0x10,0,1,0,0,0,0,1};return !memcmp(h,expected,12);
}
int fx3_stream_read0(fx3_stream *s,const uint8_t key[32],fx3_read_receipt *out){
    int rc=lock(s);if(rc)return rc;
    if(!out || !key || zero(key,32) || s->mode!=2 || !s->exchange_finished || s->read_attempted || s->stop_attempted)return leave(s,FX3T_DENIED);
    memset(out,0,sizeof(*out));s->read_attempted=1;
    uint8_t header[12]={0},body[88]={0};uint32_t count=0,at=0;
    rc=put(s,read0_packet,sizeof(read0_packet));
    /* SERVICE has no 512B minimum. Header and payload are separate native
     * reads; asking for100 bytes can stop at the12B header short packet. */
    if(!rc)rc=get(s,header,12,&count,5);
    if(!rc && (count!=12 || !header_ok(header)))rc=FX3T_SHAPE;
    while(!rc && at<88){rc=get(s,body+at,88-at,&count,6);if(!rc)at+=count;}
    if(!rc){
        CCHmac(kCCHmacAlgSHA256,key,32,body,88,out->opaque_hmac);
        out->bytes=88;out->reply_valid=1;out->table_AB_capability=1;
        /* No raw body, authentication, thread, firmware or backup verdict. */
    }
    if(rc)s->failed=s->route->failed=1;
    wipe(header,sizeof(header));wipe(body,sizeof(body));return leave(s,rc);
}
int fx3_stream_stop(fx3_stream *s){
    int rc=lock(s);if(rc)return rc;
    if(!s->started || s->stop_attempted)return leave(s,FX3T_DENIED);
    uint32_t ms=timeout(s);if(!ms)return leave(s,FX3T_TIMEOUT);
    s->stop_attempted=1;if(audit(s,7,0,NULL))return leave(s,FX3T_UNKNOWN);rc=returned(s,s->ops.control(s->backend,stop_packet,ms),7);return leave(s,rc);
}
int fx3_stream_retire(fx3_stream *s){
    if(!s || !s->route)return FX3T_DENIED;
    uint32_t n=0;if(!atomic_compare_exchange_strong(&s->busy,&n,1))return FX3T_BUSY;
    if(s->unreturned){atomic_store(&s->busy,0);return FX3T_UNKNOWN;}
    int rc=FX3T_DENIED;fx3_route *r=s->route;
    if(!s->dispose_attempted && r->active && s->generation==r->generation){
        s->dispose_attempted=1;
        if(audit(s,8,0,NULL)){s->failed=r->failed=1;atomic_store(&s->busy,0);return FX3T_UNKNOWN;}
        fx3_call done=s->ops.dispose(s->backend);s->last_call=done;
        if(audit(s,8,1,&done)){s->failed=r->failed=1;atomic_store(&s->busy,0);return FX3T_UNKNOWN;}
        if(!done.returned || (done.status!=FX3T_OK && done.status!=FX3T_GONE)){
            s->failed=r->failed=1;atomic_store(&s->busy,0);return FX3T_UNKNOWN;
        }
        r->active=0;
        if(!s->failed && !r->failed && ((s->mode==1 && s->exchange_finished) || (s->mode==2 && s->stop_attempted))){r->phase++;rc=FX3T_OK;}
        else{r->failed=1;rc=FX3T_UNKNOWN;}
        s->route=NULL;s->backend=NULL;
    }
    atomic_store(&s->busy,0);return rc;
}
int fx3_route_observe_return(fx3_route *r,const fx3_identity *a){
    if(!r || r->failed || r->active || r->phase!=2 || !identity_ok(a) || a->pid!=0x0da1 || !same(a,&r->initial))return FX3T_DENIED;
    if(a->registry_id==r->used_registry[0] || a->registry_id==r->used_registry[1])return FX3T_DENIED;
    r->used_registry[2]=a->registry_id;r->phase=3;return FX3T_OK;
}
