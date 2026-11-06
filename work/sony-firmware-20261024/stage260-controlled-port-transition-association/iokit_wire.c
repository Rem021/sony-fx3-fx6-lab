/* Borrowed same-process IOKit650 objects only. No loader/open/claim/close/reset,
 * halt-clear, configuration/mode fallback, file access or automatic retry. */
#include "iokit_wire.h"
#include <string.h>
#include <time.h>
#include <unistd.h>

static const uint8_t start[8]={0x43,1,0xff,0x37,0xaa,0xd7,0,0};
static const uint8_t stop[8]={0x43,1,0,0xc8,0x55,0x28,0,0};
static uint64_t now(fx3_io_context *c) {
    (void)c;
#ifdef FX3_IOKIT_WIRE_FIXTURE
    if(c->owner.fixture_clock)return c->owner.fixture_clock(c->owner.fixture_clock_context);
#endif
    struct timespec t;if(clock_gettime(CLOCK_MONOTONIC,&t))return 0;
    return (uint64_t)t.tv_sec*1000000000ull+(uint64_t)t.tv_nsec;
}
static int shape(fx3_io_context *c) {
    return c && c->magic==FX3_IO_MAGIC && c->creator_pid==(uint32_t)getpid();
}
static int owned(fx3_io_context *c,uint64_t generation) {
    return shape(c) && c->valid && generation==c->generation && c->owner.owner_active &&
        c->owner.owner_generation && atomic_load_explicit(c->owner.owner_active,memory_order_acquire)==1 &&
        atomic_load_explicit(c->owner.owner_generation,memory_order_acquire)==generation;
}
static int lock(fx3_io_context *c) {
    uint32_t zero=0;return atomic_compare_exchange_strong_explicit(&c->pending,&zero,255,memory_order_acq_rel,memory_order_acquire);
}
int fx3_io_bind(fx3_io_context *c,const fx3_io_owner *o) {
#ifndef FX3_IOKIT_WIRE_FIXTURE
    if(geteuid()!=0)return IO_DENIED;
#endif
    if(!c || c->magic || !o || !o->device || !*o->device || !o->interface || !*o->interface ||
       !(*o->device)->DeviceRequestTO || !(*o->interface)->ReadPipeTO || !(*o->interface)->WritePipeTO ||
       !o->owner_active || !o->owner_generation || !o->stop_requested || !o->generation ||
       !o->session_deadline_ns || o->map_reviewed!=1 || o->protocol_scope_reviewed!=1 ||
       o->max_packet!=512 || o->pipe_in<1 || o->pipe_in>2 || o->pipe_out<1 || o->pipe_out>2 || o->pipe_in==o->pipe_out)
        return IO_DENIED;
    if(o->mode==1) {if(o->ep_in!=0x81 || o->ep_out!=2)return IO_DENIED;}
    else {
#ifdef FX3_IOKIT_WIRE_FIXTURE
        if(o->mode!=2 || o->ep_in!=0x83 || o->ep_out!=4)return IO_DENIED;
#else
        return IO_DENIED; /* Actual SERVICE profile has not been observed. */
#endif
    }
    memset(c,0,sizeof(*c));c->magic=FX3_IO_MAGIC;c->creator_pid=(uint32_t)getpid();
    c->generation=o->generation;c->owner=*o;c->valid=1;atomic_init(&c->pending,0);
    if(!owned(c,o->generation)){c->valid=0;return IO_OWNER;}
    c->last_now=now(c);
    if(!c->last_now || c->last_now>=o->session_deadline_ns){c->valid=0;return IO_CLOCK;}
    return IO_OK;
}
uint32_t fx3_io_pending(fx3_io_context *c) {return shape(c)?atomic_load_explicit(&c->pending,memory_order_acquire):255;}
int fx3_io_refresh(fx3_io_context *c,uint64_t generation) {
    if(!shape(c))return IO_DENIED;
    if(!lock(c))return IO_BUSY;
    int result=IO_OWNER;
    if(owned(c,generation)) {
        uint64_t t=now(c);
        if(t && t>=c->last_now && t<c->owner.session_deadline_ns) {
            c->last_now=t;c->observed_ns=t;++c->observation_version;result=IO_OK;
        }else {c->hard_unknown=1;result=IO_CLOCK;}
    }
    atomic_store_explicit(&c->pending,0,memory_order_release);return result;
}
int fx3_io_invalidate(fx3_io_context *c,uint64_t generation) {
    if(!shape(c) || generation!=c->generation)return IO_DENIED;
    if(!lock(c))return IO_BUSY;
    c->valid=0;atomic_store_explicit(&c->pending,0,memory_order_release);return IO_OK;
}
static int done(fx3_io_context *c,fx3_io_result *r,int status,int hard) {
    r->status=(uint32_t)status;
    if(status!=IO_OK && !(status==IO_STALL && r->operation==1)) {c->failed=1;c->fault_version=c->observation_version;}
    if(hard)c->hard_unknown=1;
    if(c->owner.published_pending)atomic_store_explicit(c->owner.published_pending,0,memory_order_release);
    atomic_store_explicit(&c->pending,0,memory_order_release);return status;
}
static int begin(fx3_io_context *c,uint64_t gen,uint64_t token,uint64_t deadline,uint32_t ms,uint32_t op,fx3_io_result *r) {
    if(!r)return IO_DENIED;
    memset(r,0,sizeof(*r));r->abi=FX3_IO_ABI;r->operation=op;r->status=IO_DENIED;r->buffer_ok=1;
    if(!shape(c))return IO_DENIED;
    if(!lock(c)){r->status=IO_BUSY;return IO_BUSY;}
#ifndef FX3_IOKIT_WIRE_FIXTURE
    if(geteuid()!=0)return done(c,r,IO_DENIED,1);
#endif
    if(!owned(c,gen))return done(c,r,IO_OWNER,1);
    r->owner_ok=1;
    if(c->hard_unknown)return done(c,r,IO_DENIED,1);
    if(!token || token<=c->last_token)return done(c,r,IO_TOKEN,1);
    if(!ms || ms>1000)return done(c,r,IO_SHAPE,0);
    uint64_t t=now(c);
    if(!t || t<c->last_now)return done(c,r,IO_CLOCK,1);
    c->last_now=t;
    c->operation_deadline_ns=deadline<c->owner.session_deadline_ns?deadline:c->owner.session_deadline_ns;
    if(t>=c->operation_deadline_ns)return done(c,r,IO_DEADLINE,0);
    if(!c->observed_ns || t<c->observed_ns || t-c->observed_ns>2000000000ull)return done(c,r,IO_OWNER,1);
    uint64_t remaining=(c->operation_deadline_ns-t+999999ull)/1000000ull;
    r->timeout_ms=(uint32_t)(remaining<ms?remaining:ms);c->last_token=token;
    return IO_OK; /* pending remains reserved until actual operation return. */
}
static int returned(fx3_io_context *c,fx3_io_result *r,IOReturn rc) {
    r->native_returned=1;r->raw_return=(int32_t)rc;
    uint64_t t=now(c);
    if(!t || t<c->last_now)return IO_CLOCK;
    c->last_now=t;
    if(t>c->operation_deadline_ns)return IO_LATE;
    if(!owned(c,c->generation)){r->owner_ok=0;return IO_OWNER;}
    if(atomic_load(c->owner.stop_requested) && !c->stop_sent)return IO_CANCEL;
    if(rc==kIOUSBPipeStalled)return IO_STALL;
    if(rc==kIOUSBTransactionTimeout || rc==kIOReturnTimeout)return IO_TIMEOUT;
    if(rc==kIOReturnNoDevice || rc==kIOReturnNotResponding)return IO_GONE;
    return rc?IO_ERROR:IO_OK;
}
int fx3_io_control(fx3_io_context *c,uint64_t gen,uint64_t token,const uint8_t *packet,uint64_t deadline,uint32_t ms,fx3_io_result *r) {
    int status=begin(c,gen,token,deadline,ms,1,r);if(status)return status;
    if(!packet)return done(c,r,IO_SHAPE,0);
    uint8_t bytes[8];memcpy(bytes,packet,8);
    int is_start=!memcmp(bytes,start,8),is_stop=!memcmp(bytes,stop,8);
    if(!is_start && !is_stop)return done(c,r,IO_SHAPE,0);
    if(is_start && (c->start_sent || c->stop_sent || c->failed || atomic_load(c->owner.stop_requested)))return done(c,r,IO_LIMIT,0);
    if(is_stop && (!c->start_sent || c->stop_sent || (c->failed && c->observation_version<=c->fault_version)))return done(c,r,IO_LIMIT,0);
    if(is_start){c->start_sent=1;c->start_version=c->observation_version;}else c->stop_sent=1;
    IOUSBDevRequestTO req={0};req.bmRequestType=bytes[0];req.bRequest=bytes[1];
    req.wValue=(uint16_t)(bytes[2]|bytes[3]<<8);req.wIndex=(uint16_t)(bytes[4]|bytes[5]<<8);
    req.noDataTimeout=req.completionTimeout=r->timeout_ms;
    atomic_store_explicit(&c->pending,1,memory_order_release);
    if(c->owner.published_vendor)atomic_store_explicit(c->owner.published_vendor,1,memory_order_release);
    if(c->owner.published_pending)atomic_store_explicit(c->owner.published_pending,1,memory_order_release);
    IOReturn raw=(*c->owner.device)->DeviceRequestTO(c->owner.device,&req);
    status=returned(c,r,raw);r->reported_count=req.wLenDone;r->actual_known=raw==0;
    if(req.wLenDone)status=IO_BAD_COUNT;
    return done(c,r,status,status==IO_BAD_COUNT || status==IO_CLOCK || status==IO_LATE || status==IO_OWNER);
}
static int guarded(const uint8_t *b) {
    for(unsigned i=0;i<32;++i)if(b[i]!=0xc7 || b[32+FX3_IO_N+i]!=0xc7)return 0;
    return 1;
}
static int auth_ready(fx3_io_context *c,fx3_io_result *r) {
    if(!c->start_sent || c->stop_sent || c->failed || c->observation_version<=c->start_version ||
       atomic_load(c->owner.stop_requested))return done(c,r,IO_LIMIT,0);
    return IO_OK;
}
int fx3_io_out(fx3_io_context *c,uint64_t gen,uint64_t token,const uint8_t *data,uint32_t n,uint64_t deadline,uint32_t ms,fx3_io_result *r) {
    int status=begin(c,gen,token,deadline,ms,2,r);if(status)return status;
    if(!data || n!=FX3_IO_N)return done(c,r,IO_SHAPE,0);
    if((status=auth_ready(c,r)))return status;
    if(c->awaiting_in || c->outs>=7)return done(c,r,IO_LIMIT,0);
    uint8_t copy[FX3_IO_N],buffer[FX3_IO_N+64];memcpy(copy,data,FX3_IO_N);
    uint16_t command=(uint16_t)~((uint16_t)copy[0]<<8|copy[1]);
    if(copy[2] || copy[3] || (command!=1 && command!=3 && command!=5))return done(c,r,IO_SHAPE,0);
    if(command==1 || command==5) {for(unsigned i=4;i<FX3_IO_N;++i)if(copy[i])return done(c,r,IO_SHAPE,0);}
    else {if(copy[4]!=1)return done(c,r,IO_SHAPE,0);for(unsigned i=37;i<FX3_IO_N;++i)if(copy[i])return done(c,r,IO_SHAPE,0);}
    memset(buffer,0xc7,sizeof(buffer));memcpy(buffer+32,copy,FX3_IO_N);++c->outs;r->requested=FX3_IO_N;
    atomic_store_explicit(&c->pending,2,memory_order_release);
    if(c->owner.published_pending)atomic_store_explicit(c->owner.published_pending,2,memory_order_release);
    IOReturn raw=(*c->owner.interface)->WritePipeTO(c->owner.interface,(UInt8)c->owner.pipe_out,buffer+32,FX3_IO_N,r->timeout_ms,r->timeout_ms);
    status=returned(c,r,raw);r->buffer_ok=guarded(buffer) && !memcmp(buffer+32,copy,FX3_IO_N);
    /* WritePipeTO exposes no transferred-byte output, even for rc0. */
    r->actual_known=0;
    if(!r->buffer_ok)status=IO_BUFFER;
    if(!status)c->awaiting_in=1;
    return done(c,r,status,status==IO_BUFFER || status==IO_CLOCK || status==IO_LATE || status==IO_OWNER);
}
int fx3_io_in(fx3_io_context *c,uint64_t gen,uint64_t token,uint8_t *out,uint32_t capacity,uint64_t deadline,uint32_t ms,fx3_io_result *r) {
    int status=begin(c,gen,token,deadline,ms,3,r);if(status)return status;
    if(!out || capacity!=FX3_IO_N)return done(c,r,IO_SHAPE,0);
    memset(out,0,FX3_IO_N);
    if((status=auth_ready(c,r)))return status;
    if(!c->awaiting_in || c->ins>=7)return done(c,r,IO_LIMIT,0);
    uint8_t buffer[FX3_IO_N+64];memset(buffer,0xc7,sizeof(buffer));memset(buffer+32,0,FX3_IO_N);
    UInt32 n=FX3_IO_N;++c->ins;c->awaiting_in=0;r->requested=FX3_IO_N;
    atomic_store_explicit(&c->pending,3,memory_order_release);
    if(c->owner.published_pending)atomic_store_explicit(c->owner.published_pending,3,memory_order_release);
    IOReturn raw=(*c->owner.interface)->ReadPipeTO(c->owner.interface,(UInt8)c->owner.pipe_in,buffer+32,&n,r->timeout_ms,r->timeout_ms);
    status=returned(c,r,raw);r->reported_count=n;r->actual_known=raw==0;r->buffer_ok=guarded(buffer);
    if(!r->buffer_ok)status=IO_BUFFER;
    else if(n>FX3_IO_N)status=IO_BAD_COUNT;
    else if(status==IO_OK && n!=FX3_IO_N)status=IO_SHORT;
    if(status==IO_OK)memcpy(out,buffer+32,FX3_IO_N);
    return done(c,r,status,status==IO_BUFFER || status==IO_BAD_COUNT || status==IO_CLOCK || status==IO_LATE || status==IO_OWNER);
}
