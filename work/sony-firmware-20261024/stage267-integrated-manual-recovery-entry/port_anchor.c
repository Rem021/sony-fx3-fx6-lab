#include "port_anchor.h"
#include <CoreFoundation/CoreFoundation.h>
#include <string.h>
int fx3_cached_port_anchor(io_registry_entry_t device,uint64_t *physical,uint64_t *logical){
    if(!device || !physical || !logical)return -1;
    *physical=*logical=0;io_registry_entry_t parent=0,anchor=0;CFTypeRef property=NULL;
    int ok=!IORegistryEntryGetParentEntry(device,kIOServicePlane,&parent) &&
        IOObjectConformsTo(parent,"AppleUSBHostPort") && !IORegistryEntryGetRegistryEntryID(parent,logical);
    char path[1024]={0};
    if(ok){
        property=IORegistryEntryCreateCFProperty(parent,CFSTR("UsbIOPort"),kCFAllocatorDefault,0);
        ok=property && CFGetTypeID(property)==CFStringGetTypeID() &&
            CFStringGetCString(property,path,sizeof(path),kCFStringEncodingUTF8) && !strncmp(path,"IOService:/",11);
    }
    if(ok){anchor=IORegistryEntryFromPath(kIOMainPortDefault,path);ok=anchor && !IORegistryEntryGetRegistryEntryID(anchor,physical) && *physical && *logical && *physical!=*logical;}
    if(property)CFRelease(property);if(anchor)IOObjectRelease(anchor);if(parent)IOObjectRelease(parent);
    if(!ok)*physical=*logical=0;return ok?0:-1;
}
