#include "native_recovery_cache.h"
#include "iokit_adapter.h"
#include "entry_shared.h"
#include <IOKit/IOKitLib.h>
#include <CoreFoundation/CoreFoundation.h>
#include <stdio.h>
#include <string.h>
#include <sys/mount.h>
#include <unistd.h>
static int same(const fx3_identity *a,const fx3_identity *b){
    return a->registry_id==b->registry_id && a->physical_port==b->physical_port &&
        a->logical_port==b->logical_port && a->location==b->location && a->vid==b->vid &&
        a->pid==b->pid && a->identity_kind==b->identity_kind && !memcmp(a->serial_tag,b->serial_tag,32);
}
static int storage(uint64_t registry,fx3_recovery_cache *out){
    io_service_t service=IOServiceGetMatchingService(kIOMainPortDefault,IORegistryEntryIDMatching(registry));
    if(!service)return -1;
    io_iterator_t it=IO_OBJECT_NULL;
    if(IORegistryEntryCreateIterator(service,kIOServicePlane,kIORegistryIterateRecursively,&it)){
        IOObjectRelease(service);return -1;
    }
    struct statfs *mounts=NULL;int count=getmntinfo(&mounts,MNT_NOWAIT);
    if(count<=0 || !mounts){IOObjectRelease(it);IOObjectRelease(service);return -1;}
    io_registry_entry_t child;
    while((child=IOIteratorNext(it))){
        io_name_t name={0};
        if(IOObjectGetClass(child,name)==KERN_SUCCESS){
            if(strstr(name,"IOUSBMassStorage"))out->storage_driver_count++;
        }else out->media_unknown++;
        if(IOObjectConformsTo(child,"IOMedia")){
            out->media_count++;char bsd[128]={0},device[140]={0};
            CFTypeRef value=IORegistryEntryCreateCFProperty(child,CFSTR("BSD Name"),kCFAllocatorDefault,0);
            int ok=value && CFGetTypeID(value)==CFStringGetTypeID() &&
                CFStringGetCString(value,bsd,sizeof(bsd),kCFStringEncodingUTF8) && bsd[0];
            if(value)CFRelease(value);
            if(!ok)out->media_unknown++;
            else {
                int n=snprintf(device,sizeof(device),"/dev/%s",bsd);
                if(n<=0 || (size_t)n>=sizeof(device))out->media_unknown++;
                else for(int i=0;i<count;i++)if(!strcmp(mounts[i].f_mntfromname,device))out->mounted_count++;
            }
        }
        IOObjectRelease(child);
    }
    int ok=IOIteratorIsValid(it);IOObjectRelease(it);IOObjectRelease(service);
    return ok?0:-1;
}
int fx3_native_verify_recovery_cache(void *opaque,fx3_recovery_cache *out){
    fx3_native_recovery_context *c=opaque;
    if(geteuid()!=0 || !c || !c->policy || !c->prior_privacy_key || !out)return -1;
    const fx3_recovery_policy *p=c->policy;fx3_identity before={0},after={0};
    uint64_t start=fx3_entry_clock_ns();if(!start)return -1;
    if(fx3_usb_unique_msc_source(p->location,c->prior_privacy_key,&before) ||
       before.registry_id!=p->new_source_node || before.physical_port!=p->physical_port ||
       before.location!=p->location || before.vid!=0x54c || before.pid!=0x0da1 ||
       memcmp(before.serial_tag,p->prior_body_tag,32))return -1;
    fx3_recovery_cache witness={0};
    if(storage(before.registry_id,&witness) ||
       fx3_usb_unique_msc_source(p->location,c->prior_privacy_key,&after) || !same(&before,&after))return -1;
    uint64_t end=fx3_entry_clock_ns();if(!end || end<start || end-start>FX3_RECOVERY_FRESH_NS)return -1;
    witness.registry_id=after.registry_id;witness.physical_port=after.physical_port;
    witness.location=after.location;witness.vid=after.vid;witness.pid=after.pid;
    witness.unique_count=1;witness.observed_ns=end;memcpy(witness.body_tag,after.serial_tag,32);
    *out=witness;return 0;
}
