/* Own ordinary-user cache probe. No USB headers, request or interface calls. */
#include "port_anchor.h"
#include <CoreFoundation/CoreFoundation.h>
#include <stdio.h>
#include <unistd.h>
static int number(io_registry_entry_t e,CFStringRef key,uint32_t *out){
    CFTypeRef v=IORegistryEntryCreateCFProperty(e,key,kCFAllocatorDefault,0);int64_t n=0;
    int ok=v && CFGetTypeID(v)==CFNumberGetTypeID() && CFNumberGetValue(v,kCFNumberSInt64Type,&n) && n>=0 && n<=UINT32_MAX;
    if(v)CFRelease(v);if(ok)*out=(uint32_t)n;return ok;
}
int main(void){
    if(!getuid() || getuid()!=geteuid())return 77;
    io_iterator_t it=0;io_registry_entry_t e=0;unsigned count=0;uint64_t reg=0,physical=0,logical=0;int result=-1;
    if(IOServiceGetMatchingServices(kIOMainPortDefault,IOServiceMatching("IOUSBHostDevice"),&it))return 65;
    while((e=IOIteratorNext(it))){
        uint32_t vid=0,pid=0,loc=0;
        if(number(e,CFSTR("idVendor"),&vid)&&number(e,CFSTR("idProduct"),&pid)&&number(e,CFSTR("locationID"),&loc)&&vid==0x54c&&pid==0x0da1&&loc==0x01100000){
            CFTypeRef name=IORegistryEntryCreateCFProperty(e,CFSTR("USB Product Name"),kCFAllocatorDefault,0);
            if(name&&CFGetTypeID(name)==CFStringGetTypeID()&&CFEqual(name,CFSTR("ILME-FX3"))){count++;result=IORegistryEntryGetRegistryEntryID(e,&reg)?-1:fx3_cached_port_anchor(e,&physical,&logical);}
            if(name)CFRelease(name);
        }
        IOObjectRelease(e);
    }
    IOObjectRelease(it);
    printf("{\"uid\":%u,\"candidate_count\":%u,\"registryID\":%llu,\"physical_port_registryID\":%llu,\"logical_port_registryID\":%llu,\"anchor_available\":%s,\"USB_interface_opened\":false,\"serial_selected\":false}\n",(unsigned)getuid(),count,(unsigned long long)reg,(unsigned long long)physical,(unsigned long long)logical,count==1&&!result?"true":"false");
    return count==1&&!result?0:2;
}
