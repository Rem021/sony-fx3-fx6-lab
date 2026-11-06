/* An owner-process MSC dispatcher. No pointer/credential/endpoint importer,
 * launcher, device close/reset, filesystem, payload or firmware command. */
#include "native_session.h"
#include <string.h>

static uint32_t get32(const uint8_t *p) {uint32_t n=0;for(unsigned i=0;i<4;++i)n|=(uint32_t)p[i]<<(8*i);return n;}
static uint64_t get64(const uint8_t *p) {return get32(p)|((uint64_t)get32(p+4)<<32);}
static void put32(uint8_t *p,uint32_t n) {for(unsigned i=0;i<4;++i)p[i]=(uint8_t)(n>>(8*i));}
static void put64(uint8_t *p,uint64_t n) {put32(p,(uint32_t)n);put32(p+4,(uint32_t)(n>>32));}
static int zeros(const uint8_t *p,uint32_t n) {uint8_t v=0;for(uint32_t i=0;i<n;++i)v|=p[i];return !v;}
static void native_result(uint8_t *p,const fx3_io_result *r) {
    uint32_t fields[12]={r->abi,r->status,r->operation,r->requested,r->actual_known,r->reported_count,
        r->timeout_ms,r->native_returned,(uint32_t)r->raw_return,r->buffer_ok,r->owner_ok,r->body_effect_proven};
    for(unsigned i=0;i<12;++i)put32(p+4*i,fields[i]);
}
static int answer(fx3_native_session *s,uint8_t *out,uint64_t id,int status,
                  const fx3_io_result *a,const fx3_io_result *b,const uint8_t *reply,uint32_t n) {
    memset(out,0,FX3_RESPONSE_BYTES);put32(out,FX3_RESPONSE_MAGIC);put32(out+4,1);put64(out+8,id);put32(out+16,(uint32_t)status);
    put32(out+20,s->started|s->stopped<<1|s->failed<<2|s->hard<<3|s->ended<<4|s->complete<<5);
    put32(out+24,s->exchanges);put32(out+28,s->requests);put32(out+32,s->wire?fx3_io_pending(s->wire):0);put32(out+36,n);
    /* offset40: body/worker completion proof always false. */
    put32(out+44,(a?a->native_returned:0)+(b?b->native_returned:0));memcpy(out+48,s->nonce,16);
    if(a)native_result(out+64,a);if(b)native_result(out+112,b);if(reply && n==516)memcpy(out+160,reply,n);
    atomic_store_explicit(&s->busy,0,memory_order_release);return status;
}
static int hard(int n) {return n==IO_DENIED || n==IO_TIMEOUT || n==IO_GONE || n==IO_ERROR || n==IO_BAD_COUNT ||
    n==IO_BUFFER || n==IO_LATE || n==IO_CLOCK || n==IO_OWNER || n==IO_TOKEN;}
static uint64_t token(uint64_t id,int second) {return id*2+(uint64_t)second;}
static uint32_t timeout_ms(fx3_native_session *s,uint64_t deadline) {
    uint64_t now=s->clock_ns(s->environment);if(!now || now>=deadline)return 0;
    uint64_t ms=(deadline-now+999999ull)/1000000ull;return ms>1000?1000:(uint32_t)ms;
}
int fx3_session_init(fx3_native_session *s,fx3_io_context *wire,const uint8_t *nonce,uint64_t deadline,
                     int (*peer)(void *),uint64_t (*clock)(void *),void *env) {
    if(!s || s->magic || !wire || wire->start_sent || wire->last_token || !nonce || zeros(nonce,16) || !peer || !clock || !deadline ||
       wire->owner.mode!=1 || !wire->valid || fx3_io_pending(wire))return FX3S_DENIED;
    memset(s,0,sizeof(*s));s->magic=0x53455331u;s->wire=wire;s->generation=wire->generation;s->deadline_ns=deadline;
    memcpy(s->nonce,nonce,16);s->peer_ok=peer;s->clock_ns=clock;s->environment=env;s->next_command=1;atomic_init(&s->busy,0);
    return FX3S_OK;
}
int fx3_session_finish_host(fx3_native_session *s) {
    /* Exclusively invalidate/detach the local context. No device close, normal
     * mode, worker completion or device cleanup is authorized by this result. */
    if(!s || s->magic!=0x53455331u)return FX3S_DENIED;
    uint32_t zero=0;
    if(!atomic_compare_exchange_strong_explicit(&s->busy,&zero,1,memory_order_acq_rel,memory_order_acquire))return FX3S_PENDING;
    int result=FX3S_CLOSED;
    if(s->wire) {
        if(fx3_io_pending(s->wire))result=FX3S_PENDING;
        else if(fx3_io_invalidate(s->wire,s->generation))result=FX3S_DENIED;
        else{s->wire=NULL;s->ended=1;result=FX3S_OK;}
    }
    atomic_store_explicit(&s->busy,0,memory_order_release);return result;
}
int fx3_session_dispatch(fx3_native_session *s,const uint8_t *request,uint32_t n,uint8_t *out) {
    if(!s || s->magic!=0x53455331u || !request || !out)return FX3S_DENIED;
    uint32_t zero=0;if(!atomic_compare_exchange_strong_explicit(&s->busy,&zero,1,memory_order_acq_rel,memory_order_acquire)) {
        memset(out,0,FX3_RESPONSE_BYTES);put32(out,FX3_RESPONSE_MAGIC);put32(out+4,1);
        if(n>=16)put64(out+8,get64(request+8));put32(out+16,FX3S_PENDING);memcpy(out+48,s->nonce,16);
        put32(out+32,255);return FX3S_PENDING; /* Busy owner: do not race a context detach. */
    }
    uint64_t id=n>=16?get64(request+8):0;
    if(n!=FX3_REQUEST_BYTES || get32(request)!=FX3_REQUEST_MAGIC || get32(request+4)!=1)
        return answer(s,out,id,FX3S_BAD_FRAME,NULL,NULL,NULL,0);
    /* Private copy from one kernel datagram, never a mutable shared request. */
    uint8_t copy[FX3_REQUEST_BYTES];memcpy(copy,request,sizeof(copy));
    uint64_t generation=get64(copy+16),deadline=get64(copy+24);uint32_t op=get32(copy+32),size=get32(copy+36);
    uint8_t *payload=copy+56;
    if(memcmp(copy+40,s->nonce,16) || generation!=s->generation || !id || id>1000 || id!=s->last_id+1 || s->requests>=64)
        return answer(s,out,id,FX3S_DENIED,NULL,NULL,NULL,0);
    s->last_id=id;++s->requests;
    if(!s->peer_ok(s->environment)){s->failed=s->hard=1;return answer(s,out,id,FX3S_PEER_LOST,NULL,NULL,NULL,0);}
    if(s->ended)return answer(s,out,id,FX3S_CLOSED,NULL,NULL,NULL,0);
    uint32_t expected=op==FX3S_START || op==FX3S_STOP?8:op==FX3S_AUTH?516:0;
    if(op<FX3S_OBSERVE || op>FX3S_STATUS || size!=expected || !zeros(payload+size,516-size))
        return answer(s,out,id,FX3S_BAD_FRAME,NULL,NULL,NULL,0);
    if(op==FX3S_STATUS)return answer(s,out,id,FX3S_OK,NULL,NULL,NULL,0);
    if(op==FX3S_END) {
        if(fx3_io_pending(s->wire))return answer(s,out,id,FX3S_PENDING,NULL,NULL,NULL,0);
        s->ended=1;return answer(s,out,id,s->started?FX3S_INCOMPLETE:FX3S_OK,NULL,NULL,NULL,0);
    }
    if(!deadline || deadline>s->deadline_ns || !timeout_ms(s,deadline))
        return answer(s,out,id,FX3S_DENIED,NULL,NULL,NULL,0);
    if(op==FX3S_OBSERVE) {
        int rc=fx3_io_refresh(s->wire,s->generation);
        return answer(s,out,id,rc?FX3S_DENIED:FX3S_OK,NULL,NULL,NULL,0);
    }
    if(s->hard || s->stopped || (s->failed && op!=FX3S_STOP))return answer(s,out,id,FX3S_DENIED,NULL,NULL,NULL,0);
    fx3_io_result a={0},b={0};int rc=IO_DENIED;
    if(op==FX3S_START || op==FX3S_STOP) {
        static const uint8_t start[8]={0x43,1,0xff,0x37,0xaa,0xd7,0,0};
        static const uint8_t stop[8]={0x43,1,0,0xc8,0x55,0x28,0,0};
        if(memcmp(payload,op==FX3S_START?start:stop,8) || (op==FX3S_START && s->started) || (op==FX3S_STOP && !s->started))
            return answer(s,out,id,FX3S_DENIED,NULL,NULL,NULL,0);
        if(op==FX3S_START)s->started=1;else s->stopped=1;
        rc=fx3_io_control(s->wire,s->generation,token(id,0),payload,deadline,timeout_ms(s,deadline),&a);
    }else {
        if(!s->started || s->complete || s->exchanges>=7 || !s->next_command)
            return answer(s,out,id,FX3S_DENIED,NULL,NULL,NULL,0);
        uint16_t command=(uint16_t)~((uint16_t)payload[0]<<8|payload[1]);
        uint32_t digest_size=s->family==2?20:32;
        if(payload[2] || payload[3] || command!=s->next_command ||
           ((command==1 || command==5) && !zeros(payload+4,512)) ||
           (command==3 && (payload[4]!=1 || !zeros(payload+5+digest_size,511-digest_size))))
            return answer(s,out,id,FX3S_DENIED,NULL,NULL,NULL,0);
        ++s->exchanges;
        rc=fx3_io_out(s->wire,s->generation,token(id,0),payload,516,deadline,timeout_ms(s,deadline),&a);
        uint8_t reply[516]={0};
        if(!rc) {
            if(!s->peer_ok(s->environment)) {
                s->failed=s->hard=1;return answer(s,out,id,FX3S_PEER_LOST,&a,NULL,NULL,0);
            }
            rc=fx3_io_in(s->wire,s->generation,token(id,1),reply,516,deadline,timeout_ms(s,deadline),&b);
        }
        if(!rc) {
            int code=(int)((uint16_t)~((uint16_t)reply[0]<<8|reply[1]))-((int)reply[2]<<8|reply[3]);
            int valid=(command==1?(code==2 || code==8):command==3?code==4:code==6 && reply[4]==1);
            if(!valid) {s->failed=1;return answer(s,out,id,FX3S_PROTOCOL_ERROR,&a,&b,NULL,0);}
            if(command==1){s->family=(uint32_t)code;s->next_command=3;}
            else if(command==3){++s->round;s->next_command=s->round==3?5:1;}
            else{s->complete=1;s->next_command=0;}
            return answer(s,out,id,FX3S_OK,&a,&b,reply,516);
        }
    }
    if(rc && !(op==FX3S_START && rc==IO_STALL)){s->failed=1;s->hard|=(uint32_t)hard(rc);}
    return answer(s,out,id,rc?FX3S_NATIVE_ERROR:FX3S_OK,&a,&b,NULL,0);
}
