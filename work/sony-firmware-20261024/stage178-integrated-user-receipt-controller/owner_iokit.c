/* Explicit IOKit owner trial. No USB transfer, filesystem, firmware, reset,
 * configuration selection, suspend, or automatic retry API is used. */
#include "owner_trial.h"
#include <IOKit/IOKitLib.h>
#include <IOKit/IOCFPlugIn.h>
#include <IOKit/usb/IOUSBLib.h>
#include <DiskArbitration/DiskArbitration.h>
#include <CommonCrypto/CommonHMAC.h>
#include <stdatomic.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

typedef struct {
    fx3_owner_result *report;
    const fx3_owner_config *config;
    io_service_t service;
    IOUSBDeviceInterface650 **device;
    IOUSBInterfaceInterface650 **interface;
    int device_open, interface_open;
} native_owner;

_Static_assert(sizeof(IOReturn)==sizeof(int32_t),"IOReturn trace width");
_Static_assert(sizeof(HRESULT)==sizeof(int32_t),"HRESULT trace width");

static int32_t trace_claim_result(native_owner *p,uint32_t step,int32_t code) {
    /* Claim has at most ten API results. Together with eleven major phases
     * and forty post-snapshots this remains below the existing 64-event cap.
     * Pure bounded result-memory writes; no extra device or file operation. */
    fx3_owner_result *r=p->report;
    if(r && r->event_count<FX3_OWNER_EVENTS)
        r->events[r->event_count++]=(fx3_owner_event){step,code};
    return code;
}

static int number(io_registry_entry_t service, CFStringRef key, uint32_t *out) {
    CFTypeRef value=IORegistryEntryCreateCFProperty(service,key,kCFAllocatorDefault,0);
    int64_t n=0;
    int ok=value && CFGetTypeID(value)==CFNumberGetTypeID() && CFNumberGetValue(value,kCFNumberSInt64Type,&n) && n>=0 && n<=UINT32_MAX;
    if (value) CFRelease(value);
    if (ok) *out=(uint32_t)n;
    return ok;
}
static int serial_tag(native_owner *p, io_service_t service, uint8_t tag[32]) {
    char buffer[256]={0};
    CFTypeRef value=IORegistryEntryCreateCFProperty(service,CFSTR("USB Serial Number"),kCFAllocatorDefault,0);
    int ok=value && CFGetTypeID(value)==CFStringGetTypeID() && CFStringGetCString(value,buffer,sizeof(buffer),kCFStringEncodingUTF8) && buffer[0];
    if (value) CFRelease(value);
    if (ok) CCHmac(kCCHmacAlgSHA256,p->config->privacy_key,32,buffer,strlen(buffer),tag);
    memset(buffer,0,sizeof(buffer));
    return ok;
}
static int storage(io_service_t service, fx3_owner_snapshot *out) {
    io_iterator_t iterator=IO_OBJECT_NULL;
    kern_return_t rc=IORegistryEntryCreateIterator(service,kIOServicePlane,kIORegistryIterateRecursively,&iterator);
    if (rc) return (int)rc;
    DASessionRef session=DASessionCreate(kCFAllocatorDefault);
    io_registry_entry_t child;
    while ((child=IOIteratorNext(iterator))) {
        io_name_t class_name={0};
        if (IOObjectGetClass(child,class_name)==KERN_SUCCESS && strstr(class_name,"IOUSBMassStorage")) ++out->storage_driver_count;
        if (IOObjectConformsTo(child,"IOMedia")) {
            ++out->media_count;
            DADiskRef disk=session?DADiskCreateFromIOMedia(kCFAllocatorDefault,session,child):NULL;
            CFDictionaryRef description=disk?DADiskCopyDescription(disk):NULL;
            if (!description) ++out->media_unknown;
            else if (CFDictionaryGetValue(description,kDADiskDescriptionVolumePathKey)) ++out->mounted_count;
            if (description) CFRelease(description);
            if (disk) CFRelease(disk);
        }
        IOObjectRelease(child);
    }
    if (session) CFRelease(session);
    IOObjectRelease(iterator);
    return 0;
}
static int32_t snapshot(void *opaque, fx3_owner_snapshot *out) {
    native_owner *p=opaque;
    memset(out,0,sizeof(*out));
    io_iterator_t iterator=IO_OBJECT_NULL;
    kern_return_t rc=IOServiceGetMatchingServices(kIOMainPortDefault,IOServiceMatching("IOUSBHostDevice"),&iterator);
    if (rc) return (int32_t)rc;
    io_service_t candidate=IO_OBJECT_NULL, service;
    unsigned matches=0;
    while ((service=IOIteratorNext(iterator))) {
        uint32_t vid=0,pid=0,location=0;
        int selected=number(service,CFSTR("idVendor"),&vid) && number(service,CFSTR("idProduct"),&pid) &&
            number(service,CFSTR("locationID"),&location) && vid==p->config->vid && pid==p->config->pid && location==p->config->location;
        if (selected) {
            CFTypeRef product=IORegistryEntryCreateCFProperty(service,CFSTR("USB Product Name"),kCFAllocatorDefault,0);
            selected=product && CFGetTypeID(product)==CFStringGetTypeID() && CFEqual(product,CFSTR("ILME-FX3"));
            if (product) CFRelease(product);
        }
        if (selected) {
            ++matches;
            if (!candidate) { candidate=service; service=IO_OBJECT_NULL; }
        }
        if (service) IOObjectRelease(service);
    }
    IOObjectRelease(iterator);
    if (matches!=1) { if (candidate) IOObjectRelease(candidate); return (int32_t)kIOReturnNotFound; }
    out->vid=p->config->vid; out->pid=p->config->pid; out->location=p->config->location;
    rc=IORegistryEntryGetRegistryEntryID(candidate,&out->registry_id);
    if (!rc && !serial_tag(p,candidate,out->body_tag)) rc=kIOReturnNotFound;
    if (!rc) rc=(kern_return_t)storage(candidate,out);
    if (!rc && !p->service) { p->service=candidate; candidate=IO_OBJECT_NULL; }
    if (candidate) IOObjectRelease(candidate);
    return (int32_t)rc;
}
static int32_t prepare_device(void *opaque) {
    native_owner *p=opaque;
    IOCFPlugInInterface **plugin=NULL;
    SInt32 score=0;
    if (!p->service) return (int32_t)kIOReturnNotFound;
    IOReturn rc=IOCreatePlugInInterfaceForService(p->service,kIOUSBDeviceUserClientTypeID,kIOCFPlugInInterfaceID,&plugin,&score);
    if (rc || !plugin) return rc?(int32_t)rc:(int32_t)kIOReturnNoResources;
    HRESULT hr=(*plugin)->QueryInterface(plugin,CFUUIDGetUUIDBytes(kIOUSBDeviceInterfaceID650),(LPVOID *)&p->device);
    (*plugin)->Release(plugin);
    return hr || !p->device?(int32_t)kIOReturnUnsupported:0;
}
static int32_t capture(void *opaque) {
    native_owner *p=opaque;
    if (geteuid()!=0 || !p->config->capture_permitted) return (int32_t)kIOReturnNotPrivileged;
    /* Explicitly approved seizure, not a fallback after another open attempt.
     * Capture alone is documented to exclude mass-storage interface drivers. */
    IOReturn rc=(*p->device)->USBDeviceOpenSeize(p->device);
    if (rc) return (int32_t)rc;
    p->device_open=1;
    return (int32_t)(*p->device)->USBDeviceReEnumerate(p->device,kUSBReEnumerateCaptureDeviceMask);
}
static int32_t reopen_device(void *opaque) {
    native_owner *p=opaque;
    if (p->device_open) {
        p->device_open=0; /* Failed close is not retried automatically. */
        IOReturn rc=(*p->device)->USBDeviceClose(p->device);
        if (rc) return (int32_t)rc;
    }
    IOReturn rc=(*p->device)->USBDeviceOpen(p->device);
    if (!rc) p->device_open=1;
    return (int32_t)rc;
}
static int32_t claim(void *opaque, fx3_owner_profile *out) {
    native_owner *p=opaque;
    if (!p->device_open) { IOReturn rc=trace_claim_result(p,101,(int32_t)((*p->device)->USBDeviceOpen(p->device))); if (rc) return (int32_t)rc; p->device_open=1; }
    IOUSBFindInterfaceRequest request={8,6,80,kIOUSBFindInterfaceDontCare};
    io_iterator_t iterator=IO_OBJECT_NULL;
    IOReturn rc=trace_claim_result(p,102,(int32_t)((*p->device)->CreateInterfaceIterator(p->device,&request,&iterator)));
    if (rc) return (int32_t)rc;
    io_service_t first=IOIteratorNext(iterator), extra=IOIteratorNext(iterator);
    IOObjectRelease(iterator);
    if (!first || extra) { if (first) IOObjectRelease(first); if (extra) IOObjectRelease(extra); return (int32_t)kIOReturnUnsupported; }
    IOCFPlugInInterface **plugin=NULL; SInt32 score=0;
    rc=trace_claim_result(p,103,(int32_t)(IOCreatePlugInInterfaceForService(first,kIOUSBInterfaceUserClientTypeID,kIOCFPlugInInterfaceID,&plugin,&score)));
    IOObjectRelease(first);
    if (rc || !plugin) return rc?(int32_t)rc:(int32_t)kIOReturnNoResources;
    HRESULT hr=trace_claim_result(p,104,(int32_t)((*plugin)->QueryInterface(plugin,CFUUIDGetUUIDBytes(kIOUSBInterfaceInterfaceID650),(LPVOID *)&p->interface)));
    (*plugin)->Release(plugin);
    if (hr || !p->interface) return (int32_t)kIOReturnUnsupported;
    UInt8 number=255,alternate=255,endpoints=0;
    rc=trace_claim_result(p,105,(int32_t)((*p->interface)->GetInterfaceNumber(p->interface,&number))); if (rc) return (int32_t)rc;
    rc=trace_claim_result(p,106,(int32_t)((*p->interface)->GetAlternateSetting(p->interface,&alternate))); if (rc) return (int32_t)rc;
    rc=trace_claim_result(p,107,(int32_t)((*p->interface)->GetNumEndpoints(p->interface,&endpoints))); if (rc) return (int32_t)rc;
    if (number || alternate || endpoints!=2) return (int32_t)kIOReturnUnsupported;
    rc=trace_claim_result(p,108,(int32_t)((*p->interface)->USBInterfaceOpen(p->interface))); if (rc) return (int32_t)rc;
    p->interface_open=1;
    out->interface_number=number; out->alternate=alternate; out->endpoints=endpoints;
    for (UInt8 pipe=1; pipe<=endpoints; ++pipe) {
        UInt8 direction=255,endpoint=0,type=0,interval=0; UInt16 packet=0;
        rc=trace_claim_result(p,109,(int32_t)((*p->interface)->GetPipeProperties(p->interface,pipe,&direction,&endpoint,&type,&packet,&interval)));
        if (rc) return (int32_t)rc;
        if (type!=kUSBBulk || packet!=512 || endpoint>15) return (int32_t)kIOReturnUnsupported;
        if (direction==kUSBIn) { if (out->in_address) return (int32_t)kIOReturnUnsupported; out->in_address=0x80u|endpoint; }
        else if (direction==kUSBOut) { if (out->out_address) return (int32_t)kIOReturnUnsupported; out->out_address=endpoint; }
        else return (int32_t)kIOReturnUnsupported;
        out->max_packet=packet;
    }
    return 0;
}
static int32_t release_interface(void *opaque) {
    native_owner *p=opaque; IOReturn rc=0;
    if (p->interface) {
        if (p->interface_open) { p->interface_open=0; rc=(*p->interface)->USBInterfaceClose(p->interface); }
        (*p->interface)->Release(p->interface); p->interface=NULL;
    }
    return (int32_t)rc;
}
static int32_t return_driver(void *opaque) {
    native_owner *p=opaque;
    /* SDK release option is valid without an open device for a root client.
     * No zero-option bus re-enumeration or fallback reset is attempted. */
    return p->device?(int32_t)(*p->device)->USBDeviceReEnumerate(p->device,kUSBReEnumerateReleaseDeviceMask):(int32_t)kIOReturnNotFound;
}
static int32_t close_device(void *opaque) {
    native_owner *p=opaque; IOReturn rc=0;
    if (p->device) {
        if (p->device_open) { p->device_open=0; rc=(*p->device)->USBDeviceClose(p->device); }
        (*p->device)->Release(p->device); p->device=NULL;
    }
    return (int32_t)rc;
}
static uint64_t now_ns(void *unused) { (void)unused; struct timespec t; clock_gettime(CLOCK_MONOTONIC,&t); return (uint64_t)t.tv_sec*1000000000u+(uint64_t)t.tv_nsec; }
static void pause_ms(void *unused,uint32_t ms) { (void)unused; struct timespec t={ms/1000,(long)(ms%1000)*1000000L}; nanosleep(&t,NULL); }
static const fx3_owner_ops ops={snapshot,prepare_device,capture,reopen_device,claim,release_interface,return_driver,close_device,now_ns,pause_ms};
static atomic_flag once=ATOMIC_FLAG_INIT;
__attribute__((visibility("default"))) int fx3_owner_run(const fx3_owner_config *c,fx3_owner_result *r,fx3_owner_control *control) {
    if (!c || !r || geteuid()!=0 || atomic_flag_test_and_set(&once)) {
        if (r) {
            size_t pending=offsetof(fx3_owner_result,active_call_pending);
            memset(r,0,pending);
            memset((uint8_t *)r+pending+sizeof(r->active_call_pending),0,sizeof(*r)-pending-sizeof(r->active_call_pending));
            atomic_store_explicit(&r->active_call_pending,0,memory_order_release);
            r->abi=FX3_OWNER_ABI; r->status=FX3_DENIED;
        }
        return FX3_DENIED;
    }
    native_owner owner={.report=r,.config=c};
    int result=fx3_owner_core(c,r,control,&ops,&owner);
    if (owner.service) IOObjectRelease(owner.service);
    return result;
}
