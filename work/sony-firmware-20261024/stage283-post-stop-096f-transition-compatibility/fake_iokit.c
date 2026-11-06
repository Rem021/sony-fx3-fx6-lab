/* SDK-typed fake IOKit vtables. No actual USB object or IOKit library is used. */
#include "iokit_wire.h"
#include <stdlib.h>
#include <stddef.h>
#include <string.h>
#include <unistd.h>

typedef struct fixture fixture;
typedef struct {IOUSBDeviceInterface650 *table;fixture *f;} fake_device;
typedef struct {IOUSBInterfaceInterface650 *table;fixture *f;} fake_interface;
struct fixture {
    fx3_io_context context;
    fake_device device;fake_interface interface;
    _Atomic uint32_t active,stop,block,entered,release;
    _Atomic uint64_t generation;
    uint64_t clock;
    uint32_t fault_op,fault,stats[16];
    uint8_t reply[FX3_IO_N],sent[FX3_IO_N];
    _Atomic uint32_t *shared_entered,*shared_release;
};
_Static_assert(offsetof(fixture,context)==0,"fixture context prefix");
static uint64_t tick(void *opaque) {return ((fixture *)opaque)->clock;}
static IOReturn effect(fixture *f,uint32_t op,void *buffer) {
    if(f->fault_op!=op)return 0;
    switch(f->fault) {
        case 1:return kIOUSBPipeStalled;
        case 2:return kIOUSBTransactionTimeout;
        case 3:return kIOReturnNoDevice;
        case 4:if(buffer)((uint8_t *)buffer)[0]^=1;return 0;
        case 7:if(buffer)((uint8_t *)buffer)[FX3_IO_N]=0;return 0;
        case 8:f->clock+=70000000000ull;return 0;
        case 9:f->clock=1;return 0;
        case 10:atomic_store(&f->active,0);return 0;
        case 11:atomic_fetch_add(&f->generation,1);return 0;
        case 12:
            atomic_store(&f->entered,1);
            if(f->shared_entered)atomic_store(f->shared_entered,op);
            while(!atomic_load(&f->release) && !(f->shared_release && atomic_load(f->shared_release)==1))usleep(1000);
            return 0;
        case 15:return kIOReturnError;
        case 16:atomic_store(&f->stop,1);return 0;
        case 17:f->clock+=4000000000ull;return 0;
        default:return 0;
    }
}
static IOReturn control(void *self,IOUSBDevRequestTO *req) {
    fixture *f=((fake_device *)self)->f;++f->stats[0];
    f->stats[3]=req->noDataTimeout;f->stats[4]=req->completionTimeout;
    f->stats[7]=req->bmRequestType;f->stats[8]=req->bRequest;
    f->stats[9]=req->wValue;f->stats[10]=req->wIndex;f->stats[11]=req->wLength;
    if(req->pData || req->wLength || !req->noDataTimeout || !req->completionTimeout)++f->stats[15];
    if(f->fault_op==1 && f->fault==13)req->wLenDone=1;
    return effect(f,1,NULL);
}
static IOReturn write_pipe(void *self,UInt8 pipe,void *buffer,UInt32 n,UInt32 idle,UInt32 total) {
    fixture *f=((fake_interface *)self)->f;++f->stats[1];
    f->stats[3]=idle;f->stats[4]=total;f->stats[5]=pipe;f->stats[12]=n;
    if(n!=FX3_IO_N || !idle || !total)++f->stats[15];
    if(n==FX3_IO_N)memcpy(f->sent,buffer,n);
    return effect(f,2,buffer);
}
static IOReturn read_pipe(void *self,UInt8 pipe,void *buffer,UInt32 *n,UInt32 idle,UInt32 total) {
    fixture *f=((fake_interface *)self)->f;++f->stats[2];
    f->stats[3]=idle;f->stats[4]=total;f->stats[6]=pipe;f->stats[13]=*n;
    if(*n!=FX3_IO_N || !idle || !total)++f->stats[15];
    memcpy(buffer,f->reply,FX3_IO_N);
    if(f->fault_op==3 && f->fault==5)*n=FX3_IO_N-1;
    if(f->fault_op==3 && f->fault==6)*n=FX3_IO_N+1;
    return effect(f,3,buffer);
}
static IOUSBDeviceInterface650 dv={.DeviceRequestTO=control};
static IOUSBInterfaceInterface650 iv={.ReadPipeTO=read_pipe,.WritePipeTO=write_pipe};
FX3_IO_API uint32_t fx3_iokit_fixture_marker(void) {return 0x494f4649u;}
FX3_IO_API fixture *fx3_iokit_fixture_create(uint32_t mode,uint64_t generation,int reverse) {
    fixture *f=calloc(1,sizeof(*f));if(!f)return NULL;
    f->device=(fake_device){&dv,f};f->interface=(fake_interface){&iv,f};
    atomic_init(&f->active,1);atomic_init(&f->stop,0);atomic_init(&f->generation,generation);
    atomic_init(&f->block,0);atomic_init(&f->entered,0);atomic_init(&f->release,0);
    f->clock=1000000000ull;
    fx3_io_owner o={.device=(IOUSBDeviceInterface650 **)&f->device,
        .interface=(IOUSBInterfaceInterface650 **)&f->interface,.owner_active=&f->active,
        .owner_generation=&f->generation,.stop_requested=&f->stop,.generation=generation,
        .session_deadline_ns=61000000000ull,.pipe_in=reverse?2:1,.pipe_out=reverse?1:2,
        .ep_in=mode==1?0x81:0x83,.ep_out=mode==1?2:4,.max_packet=512,.mode=mode,
        .map_reviewed=1,.protocol_scope_reviewed=1,.fixture_clock=tick,.fixture_clock_context=f};
    if(fx3_io_bind(&f->context,&o)){free(f);return NULL;}return f;
}
FX3_IO_API int fx3_iokit_fixture_dispose(fixture *f) {
    if(!f || fx3_io_pending(&f->context))return IO_BUSY;
    free(f);return 0;
}
FX3_IO_API int fx3_iokit_fixture_fault(fixture *f,uint32_t op,uint32_t fault) {
    if(!f || fx3_io_pending(&f->context))return IO_BUSY;
    f->fault_op=op;f->fault=fault;return 0;
}
FX3_IO_API int fx3_iokit_fixture_reply(fixture *f,const uint8_t *data,uint32_t n) {
    if(!f || fx3_io_pending(&f->context) || !data || n!=FX3_IO_N)return IO_DENIED;
    memcpy(f->reply,data,n);return 0;
}
FX3_IO_API int fx3_iokit_fixture_sent(fixture *f,uint8_t *data,uint32_t n) {
    if(!f || fx3_io_pending(&f->context) || !data || n!=FX3_IO_N)return IO_DENIED;
    memcpy(data,f->sent,n);return 0;
}
FX3_IO_API uint64_t fx3_iokit_fixture_stat(fixture *f,uint32_t index) {
    if(!f)return 0;
    if(index<16)return f->stats[index];
    if(index==16)return f->clock;
    if(index==17)return atomic_load(&f->entered);
    if(index==18)return f->context.generation;
    return 0;
}
FX3_IO_API void fx3_iokit_fixture_release(fixture *f) {if(f)atomic_store(&f->release,1);}
FX3_IO_API int fx3_iokit_fixture_clock(fixture *f,uint64_t value) {
    if(!f || fx3_io_pending(&f->context))return IO_BUSY;
    f->clock=value;return 0;
}
FX3_IO_API int fx3_iokit_fixture_owner(fixture *f,uint32_t active,uint64_t generation) {
    if(!f || fx3_io_pending(&f->context))return IO_BUSY;
    atomic_store(&f->active,active);atomic_store(&f->generation,generation);return 0;
}
int fx3_iokit_fixture_borrow_owner(fixture *f,fx3_io_owner *out) {
    if(!f || !out)return -1;*out=f->context.owner;return 0;
}
void fx3_iokit_fixture_gate(fixture *f,_Atomic uint32_t *entered,_Atomic uint32_t *released) {
    if(f){f->shared_entered=entered;f->shared_release=released;}
}
