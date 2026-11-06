/* Production IOKit implementation. Compiled only; never executed by tests.
 * No reset, seize, configuration/alternate setter, launcher,
 * authorization prompt, card interface or automatic retry. */
#include "iokit_adapter.h"
#include <IOKit/IOKitLib.h>
#include <IOKit/IOCFPlugIn.h>
#include <CoreFoundation/CoreFoundation.h>
#include <CommonCrypto/CommonHMAC.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
struct fx3_native_usb{
    io_service_t service;
    IOUSBDeviceInterface650 **device;
    IOUSBInterfaceInterface650 **interface;
    fx3_profile profile;
    int device_open,interface_open;
};
static int equal_identity(const fx3_identity *a,const fx3_identity *b){return a->registry_id==b->registry_id && a->location==b->location && a->vid==b->vid && a->pid==b->pid && !memcmp(a->body_tag,b->body_tag,32);}
static uint64_t clock_ns(void *unused){(void)unused;struct timespec t;if(clock_gettime(CLOCK_MONOTONIC,&t))return 0;return (uint64_t)t.tv_sec*1000000000ull+(uint64_t)t.tv_nsec;}
static int scalar(io_registry_entry_t entry,CFStringRef name,uint32_t *out){
    CFTypeRef value=IORegistryEntryCreateCFProperty(entry,name,kCFAllocatorDefault,0);int64_t n=0;
    int ok=value && CFGetTypeID(value)==CFNumberGetTypeID() && CFNumberGetValue(value,kCFNumberSInt64Type,&n) && n>=0 && n<=UINT32_MAX;
    if(value)CFRelease(value);if(ok)*out=(uint32_t)n;return ok;
}
static int identity(io_service_t entry,const uint8_t key[32],fx3_identity *out){
    uint32_t vid=0,pid=0,loc=0;char serial[256]={0};memset(out,0,sizeof(*out));
    if(!scalar(entry,CFSTR("idVendor"),&vid) || !scalar(entry,CFSTR("idProduct"),&pid) || !scalar(entry,CFSTR("locationID"),&loc) || vid>65535 || pid>65535)return F_SHAPE;
    CFTypeRef value=IORegistryEntryCreateCFProperty(entry,CFSTR("USB Serial Number"),kCFAllocatorDefault,0);
    int ok=value && CFGetTypeID(value)==CFStringGetTypeID() && CFStringGetCString(value,serial,sizeof(serial),kCFStringEncodingUTF8) && serial[0];
    if(value)CFRelease(value);
    if(ok && pid==0x0da1){
        value=IORegistryEntryCreateCFProperty(entry,CFSTR("USB Product Name"),kCFAllocatorDefault,0);
        ok=value && CFGetTypeID(value)==CFStringGetTypeID() && CFEqual(value,CFSTR("ILME-FX3"));if(value)CFRelease(value);
    }
    if(ok){out->vid=(uint16_t)vid;out->pid=(uint16_t)pid;out->location=loc;CCHmac(kCCHmacAlgSHA256,key,32,serial,strlen(serial),out->body_tag);}
    volatile char *wipe=serial;for(unsigned i=0;i<sizeof(serial);i++)wipe[i]=0;
    if(!ok || IORegistryEntryGetRegistryEntryID(entry,&out->registry_id))return F_SHAPE;
    return F_OK;
}
static int find(uint32_t location,uint16_t pid,const uint8_t key[32],fx3_identity *out,io_service_t *selected){
    if(geteuid()!=0 || !key || !out || !selected || (pid!=0x0da1 && pid!=0x0336))return F_DENIED;
    *selected=IO_OBJECT_NULL;io_iterator_t it=IO_OBJECT_NULL;
    if(IOServiceGetMatchingServices(kIOMainPortDefault,IOServiceMatching("IOUSBHostDevice"),&it))return F_IO;
    unsigned count=0;io_service_t entry;int rc=F_GONE;
    while((entry=IOIteratorNext(it))){
        uint32_t actual_location=0,vid=0,product=0;
        if(scalar(entry,CFSTR("locationID"),&actual_location) && actual_location==location){
            count++;
            if(count==1 && scalar(entry,CFSTR("idVendor"),&vid) && scalar(entry,CFSTR("idProduct"),&product) && vid==0x054c && product==pid){
                rc=identity(entry,key,out);if(!rc){*selected=entry;entry=IO_OBJECT_NULL;}
            }else rc=F_DENIED;
        }
        if(entry)IOObjectRelease(entry);
    }
    IOObjectRelease(it);
    if(count!=1 || rc){if(*selected)IOObjectRelease(*selected);*selected=IO_OBJECT_NULL;return count>1?F_DENIED:rc;}
    return F_OK;
}
int fx3_usb_cached_identity(uint32_t location,uint16_t pid,const uint8_t key[32],fx3_identity *out){
    io_service_t entry=IO_OBJECT_NULL;int rc=find(location,pid,key,out,&entry);if(entry)IOObjectRelease(entry);return rc;
}
static fx3_call result(IOReturn rc,uint32_t known,uint32_t n){
    int status=rc==0?F_OK:rc==kIOUSBPipeStalled?F_STALL:
        (rc==kIOReturnTimeout || rc==kIOUSBTransactionTimeout)?F_TIMEOUT:
        (rc==kIOReturnNoDevice || rc==kIOReturnNotResponding)?F_GONE:F_IO;
    return(fx3_call){status,(int32_t)rc,1,known,n};
}
static fx3_call control(void *opaque,const uint8_t setup[8],uint32_t ms){
    fx3_native_usb *p=opaque;if(geteuid()!=0 || !p || !p->device || !p->device_open)return(fx3_call){F_DENIED,0,1,0,0};
    IOUSBDevRequestTO q={0};q.bmRequestType=setup[0];q.bRequest=setup[1];q.wValue=(uint16_t)(setup[2]|setup[3]<<8);q.wIndex=(uint16_t)(setup[4]|setup[5]<<8);
    q.noDataTimeout=q.completionTimeout=ms;
    IOReturn raw=(*p->device)->DeviceRequestTO(p->device,&q);fx3_call c=result(raw,raw==0,q.wLenDone);if(q.wLenDone)c.status=F_SHAPE;return c;
}
static int guards(const uint8_t *b,uint32_t n){for(unsigned i=0;i<32;i++)if(b[i]!=0xc7 || b[n+32+i]!=0xc7)return 0;return 1;}
static fx3_call write_pipe(void *opaque,const uint8_t *data,uint32_t n,uint32_t ms){
    fx3_native_usb *p=opaque;if(geteuid()!=0 || !p || !p->interface_open || !n || n>516)return(fx3_call){F_DENIED,0,1,0,0};
    uint8_t b[580];memset(b,0xc7,sizeof(b));memcpy(b+32,data,n);
    IOReturn raw=(*p->interface)->WritePipeTO(p->interface,p->profile.pipe_out,b+32,n,ms,ms);
    fx3_call c=result(raw,0,0);if(!guards(b,n) || memcmp(b+32,data,n))c.status=F_SHAPE;
    volatile uint8_t *wipe=b;for(unsigned i=0;i<sizeof(b);i++)wipe[i]=0;return c;
}
static fx3_call read_pipe(void *opaque,uint8_t *data,uint32_t capacity,uint32_t ms){
    fx3_native_usb *p=opaque;if(geteuid()!=0 || !p || !p->interface_open || !capacity || capacity>516)return(fx3_call){F_DENIED,0,1,0,0};
    uint8_t b[580];memset(b,0xc7,sizeof(b));memset(b+32,0,capacity);UInt32 count=capacity;
    IOReturn raw=(*p->interface)->ReadPipeTO(p->interface,p->profile.pipe_in,b+32,&count,ms,ms);
    fx3_call c=result(raw,raw==0,count);
    if(!guards(b,capacity) || count>capacity)c.status=F_SHAPE;
    if(c.status==F_OK)memcpy(data,b+32,count);
    volatile uint8_t *wipe=b;for(unsigned i=0;i<sizeof(b);i++)wipe[i]=0;return c;
}
static fx3_call dispose(void *opaque){
    fx3_native_usb *p=opaque;if(geteuid()!=0 || !p)return(fx3_call){F_DENIED,0,1,0,0};
    int gone=0;IOReturn rc=0;
    if(p->interface){
        if(p->interface_open){rc=(*p->interface)->USBInterfaceClose(p->interface);if(rc && rc!=kIOReturnNoDevice)return result(rc,0,0);gone|=rc!=0;p->interface_open=0;}
        (*p->interface)->Release(p->interface);p->interface=NULL;
    }
    if(p->device){
        if(p->device_open){rc=(*p->device)->USBDeviceClose(p->device);if(rc && rc!=kIOReturnNoDevice)return result(rc,0,0);gone|=rc!=0;p->device_open=0;}
        (*p->device)->Release(p->device);p->device=NULL;
    }
    if(p->service)IOObjectRelease(p->service);
    free(p);return result(gone?kIOReturnNoDevice:0,1,0);
}
static const fx3_stream_ops ops={clock_ns,control,write_pipe,read_pipe,dispose};
static int inspect(fx3_native_usb *p,const fx3_profile *expected,fx3_stream *stream){
    fx3_profile actual={0};IOReturn rc;
    stream->acquire_step=100;
#define GET(method,field) do{stream->acquire_step++;rc=(*p->interface)->method(p->interface,&actual.field);stream->acquire_raw_return=(int32_t)rc;if(rc)return F_IO;}while(0)
    GET(GetInterfaceNumber,number);GET(GetAlternateSetting,alternate);GET(GetInterfaceClass,cls);
    GET(GetInterfaceSubClass,subclass);GET(GetInterfaceProtocol,protocol);GET(GetNumEndpoints,endpoints);
#undef GET
    if(actual.number!=expected->number || actual.alternate!=0 || actual.cls!=expected->cls || actual.subclass!=expected->subclass || actual.protocol!=expected->protocol || actual.endpoints!=expected->endpoints)return F_SHAPE;
    for(UInt8 pipe=1;pipe<=actual.endpoints;pipe++){
        UInt8 dir=0,ep=0,type=0,interval=0;UInt16 packet=0;
        stream->acquire_step=110+pipe;rc=(*p->interface)->GetPipeProperties(p->interface,pipe,&dir,&ep,&type,&packet,&interval);stream->acquire_raw_return=(int32_t)rc;if(rc)return F_IO;
        if(!ep || ep>15 || type!=kUSBBulk || packet!=expected->max_packet)return F_SHAPE;
        uint8_t address=(uint8_t)(ep|(dir==kUSBIn?0x80:0));
        if(dir!=kUSBIn && dir!=kUSBOut)return F_SHAPE;
        if(address==expected->in_address){if(actual.pipe_in)return F_SHAPE;actual.pipe_in=pipe;actual.in_address=address;}
        if(address==expected->out_address){if(actual.pipe_out)return F_SHAPE;actual.pipe_out=pipe;actual.out_address=address;}
    }
    if(!actual.pipe_in || !actual.pipe_out || actual.pipe_in==actual.pipe_out)return F_SHAPE;
    actual.max_packet=expected->max_packet;p->profile=actual;return F_OK;
}
static int expected_ok(const fx3_profile *p,uint32_t mode){
    return p && !p->alternate && p->max_packet==512 && (p->endpoints==2 || (mode==2 && p->endpoints==4)) &&
        p->in_address>=0x81 && p->in_address<=0x8f && p->out_address>=1 && p->out_address<=15 &&
        (mode==1?(p->cls==8 && p->subclass==6 && p->protocol==80 && p->number==0 && p->in_address==0x81 && p->out_address==2):mode==2 && p->cls==255);
}
int fx3_usb_open(fx3_route *route,fx3_stream *stream,const fx3_identity *expected_identity,uint32_t mode,const uint8_t key[32],const fx3_profile *expected_profile,uint64_t deadline){
    /* Initial MSC comes only from the established owner transfer, which
     * performs its own ejection/capture checks. Never claim a mounted MSC. */
    if(geteuid()!=0 || mode!=FX3_MODE_SERVICE || !stream || stream->route || fx3_route_candidate(route,expected_identity,mode) || !expected_ok(expected_profile,mode))return F_DENIED;
    fx3_identity actual;io_service_t service=IO_OBJECT_NULL;int rc=find(expected_identity->location,expected_identity->pid,key,&actual,&service);
    if(rc)return rc;
    if(!equal_identity(&actual,expected_identity)){IOObjectRelease(service);return F_DENIED;}
    fx3_native_usb *p=calloc(1,sizeof(*p));if(!p){IOObjectRelease(service);return F_IO;}p->service=service;
    /* Bind before acquiring any USB objects so all partial acquisition state
     * is reachable for one explicit retirement, with no automatic cleanup. */
    rc=fx3_stream_bind_acquiring(route,stream,&actual,mode,deadline,&ops,p);if(rc){IOObjectRelease(service);free(p);return rc;}
    IOCFPlugInInterface **plugin=NULL;SInt32 score=0;HRESULT hr=0;io_iterator_t it=IO_OBJECT_NULL;
    stream->acquire_step=1;IOReturn raw=IOCreatePlugInInterfaceForService(service,kIOUSBDeviceUserClientTypeID,kIOCFPlugInInterfaceID,&plugin,&score);stream->acquire_raw_return=(int32_t)raw;
    if(raw || !plugin)goto failed;
    stream->acquire_step=2;hr=(*plugin)->QueryInterface(plugin,CFUUIDGetUUIDBytes(kIOUSBDeviceInterfaceID650),(LPVOID *)&p->device);stream->acquire_raw_return=(int32_t)hr;(*plugin)->Release(plugin);plugin=NULL;
    if(hr || !p->device)goto failed;
    stream->acquire_step=3;raw=(*p->device)->USBDeviceOpen(p->device);stream->acquire_raw_return=(int32_t)raw;if(raw)goto failed;p->device_open=1;
    IOUSBFindInterfaceRequest q={expected_profile->cls,expected_profile->subclass,expected_profile->protocol,kIOUSBFindInterfaceDontCare};
    stream->acquire_step=4;raw=(*p->device)->CreateInterfaceIterator(p->device,&q,&it);stream->acquire_raw_return=(int32_t)raw;if(raw)goto failed;
    io_service_t first=IOIteratorNext(it),extra=IOIteratorNext(it);IOObjectRelease(it);it=IO_OBJECT_NULL;
    stream->acquire_step=5;
    if(!first || extra){stream->acquire_policy_return=F_SHAPE;if(first)IOObjectRelease(first);if(extra)IOObjectRelease(extra);goto failed;}
    stream->acquire_step=6;raw=IOCreatePlugInInterfaceForService(first,kIOUSBInterfaceUserClientTypeID,kIOCFPlugInInterfaceID,&plugin,&score);stream->acquire_raw_return=(int32_t)raw;IOObjectRelease(first);
    if(raw || !plugin)goto failed;
    stream->acquire_step=7;hr=(*plugin)->QueryInterface(plugin,CFUUIDGetUUIDBytes(kIOUSBInterfaceInterfaceID650),(LPVOID *)&p->interface);stream->acquire_raw_return=(int32_t)hr;(*plugin)->Release(plugin);plugin=NULL;
    if(hr || !p->interface)goto failed;
    stream->acquire_step=8;raw=(*p->interface)->USBInterfaceOpen(p->interface);stream->acquire_raw_return=(int32_t)raw;if(raw)goto failed;p->interface_open=1;
    rc=inspect(p,expected_profile,stream);stream->acquire_policy_return=rc;if(rc)goto failed;
    if(clock_ns(NULL)>=deadline){raw=kIOReturnTimeout;goto failed;}
    atomic_store(&stream->busy,0);return F_OK;
failed:
    if(plugin)(*plugin)->Release(plugin);
    if(it)IOObjectRelease(it);
    stream->failed=route->failed=1;stream->last_call=result(raw?raw:hr?(IOReturn)hr:kIOReturnUnsupported,0,0);atomic_store(&stream->busy,0);return F_UNKNOWN;
}
int fx3_usb_take_msc(fx3_route *route,fx3_stream *stream,const fx3_identity *expected,const uint8_t key[32],IOUSBDeviceInterface650 ***device,IOUSBInterfaceInterface650 ***interface,uint64_t deadline){
    if(geteuid()!=0 || !device || !*device || !interface || !*interface || !stream || stream->route || fx3_route_candidate(route,expected,1))return F_DENIED;
    fx3_identity actual;int rc=fx3_usb_cached_identity(expected->location,expected->pid,key,&actual);if(rc || !equal_identity(&actual,expected))return F_DENIED;
    fx3_native_usb *p=calloc(1,sizeof(*p));if(!p)return F_IO;
    rc=fx3_stream_bind_acquiring(route,stream,&actual,1,deadline,&ops,p);if(rc){free(p);return rc;}
    p->device=*device;p->interface=*interface;p->device_open=p->interface_open=1;*device=NULL;*interface=NULL;
    const fx3_profile profile={.number=0,.alternate=0,.cls=8,.subclass=6,.protocol=80,.endpoints=2,.in_address=0x81,.out_address=2,.max_packet=512};
    rc=inspect(p,&profile,stream);stream->acquire_policy_return=rc;if(rc || clock_ns(NULL)>=deadline){stream->failed=route->failed=1;atomic_store(&stream->busy,0);return F_UNKNOWN;}atomic_store(&stream->busy,0);return F_OK;
}
fx3_call fx3_usb_request_driver_return(fx3_route *route,const fx3_identity *expected,const uint8_t key[32]){
    fx3_call denied={F_DENIED,0,1,0,0};
    if(geteuid()!=0 || !route || route->return_attempted || route->active || route->failed || route->phase!=2 || !expected || expected->pid!=0x0da1)return denied;
    route->return_attempted=1;
    uint32_t empty=0;if(!atomic_compare_exchange_strong(&route->return_pending,&empty,1))return denied;
    fx3_identity actual;io_service_t entry=IO_OBJECT_NULL;
    int rc=find(expected->location,expected->pid,key,&actual,&entry);
    if(rc || !equal_identity(&actual,expected) || fx3_route_observe_return(route,&actual)){
        if(entry)IOObjectRelease(entry);atomic_store(&route->return_pending,0);route->failed=1;return denied;
    }
    IOCFPlugInInterface **plugin=NULL;IOUSBDeviceInterface650 **device=NULL;SInt32 score=0;
    IOReturn raw=IOCreatePlugInInterfaceForService(entry,kIOUSBDeviceUserClientTypeID,kIOCFPlugInInterfaceID,&plugin,&score);IOObjectRelease(entry);
    if(raw || !plugin){if(plugin)(*plugin)->Release(plugin);atomic_store(&route->return_pending,0);route->failed=1;return result(raw?raw:kIOReturnNoResources,0,0);}
    HRESULT hr=(*plugin)->QueryInterface(plugin,CFUUIDGetUUIDBytes(kIOUSBDeviceInterfaceID650),(LPVOID *)&device);(*plugin)->Release(plugin);
    if(hr || !device){if(device)(*device)->Release(device);atomic_store(&route->return_pending,0);route->failed=1;return(fx3_call){F_IO,(int32_t)hr,1,0,0};}
    /* The only re-enumeration option in this component is explicit RELEASE.
     * SDK permits it without opening the device when the caller is root. */
    route->return_api_attempted=1;raw=(*device)->USBDeviceReEnumerate(device,kUSBReEnumerateReleaseDeviceMask);
    (*device)->Release(device);atomic_store(&route->return_pending,0);
    fx3_call call=result(raw,0,0);if(call.status!=F_OK)route->failed=1;return call;
}
