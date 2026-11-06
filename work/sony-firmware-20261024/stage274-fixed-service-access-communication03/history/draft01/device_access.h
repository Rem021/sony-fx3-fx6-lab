#ifndef FX3_BOUNDED_DEVICE_ACCESS_H
#define FX3_BOUNDED_DEVICE_ACCESS_H
#include <stdint.h>
#include <string.h>
#define FX3_DEVICE_EXCLUSIVE_ERROR (-536870203)
enum {FX3_DEVICE_NONE=0,FX3_DEVICE_OWNED=1,FX3_DEVICE_NO_EXCLUSIVE_OPEN=2};
static inline unsigned fx3_device_open_disposition(int32_t result){
    if(!result)return FX3_DEVICE_OWNED;
    return result==FX3_DEVICE_EXCLUSIVE_ERROR?FX3_DEVICE_NO_EXCLUSIVE_OPEN:FX3_DEVICE_NONE;
}
static inline int fx3_fixed_control_allowed(int device_present,int device_owned,int interface_owned,
                                           int matched_shared_service,const uint8_t setup[8]){
    static const uint8_t start[8]={0x43,1,0xff,0x37,0xaa,0xd7,0,0};
    static const uint8_t stop[8]={0x43,1,0,0xc8,0x55,0x28,0,0};
    if(!setup || device_present!=1 || (device_owned!=0 && device_owned!=1) ||
       (interface_owned!=0 && interface_owned!=1) || (matched_shared_service!=0 && matched_shared_service!=1))return 0;
    if(memcmp(setup,start,8) && memcmp(setup,stop,8))return 0;
    return device_owned || (interface_owned && matched_shared_service);
}
#endif
