/* Decision policy used by the production adapter and artificial pipes. */
#include "device_access.h"
#include <IOKit/IOReturn.h>
#include <assert.h>
#include <stdio.h>
int main(void){
    _Static_assert((int32_t)kIOReturnExclusiveAccess==FX3_DEVICE_EXCLUSIVE_ERROR,"SDK error value");
    const uint8_t start[8]={0x43,1,0xff,0x37,0xaa,0xd7,0,0};
    const uint8_t stop[8]={0x43,1,0,0xc8,0x55,0x28,0,0};
    const uint8_t set_config[8]={0,9,1,0,0,0,0,0};
    const uint8_t other_vendor[8]={0x43,2,0,0,0,0,0,0};
    assert(fx3_device_open_disposition(0)==FX3_DEVICE_OWNED);
    assert(fx3_device_open_disposition(FX3_DEVICE_EXCLUSIVE_ERROR)==FX3_DEVICE_NO_EXCLUSIVE_OPEN);
    int32_t other_errors[]={-536870210,-536870212,-536870195,1,-1};
    for(unsigned i=0;i<5;i++)assert(fx3_device_open_disposition(other_errors[i])==FX3_DEVICE_NONE);
    assert(fx3_fixed_control_allowed(1,1,0,0,start));
    assert(fx3_fixed_control_allowed(1,1,0,0,stop));
    assert(fx3_fixed_control_allowed(1,0,1,1,start));
    assert(fx3_fixed_control_allowed(1,0,1,1,stop));
    assert(!fx3_fixed_control_allowed(1,0,0,1,start));
    assert(!fx3_fixed_control_allowed(1,0,1,0,start));
    assert(!fx3_fixed_control_allowed(0,1,1,1,start));
    assert(!fx3_fixed_control_allowed(1,0,1,1,set_config));
    assert(!fx3_fixed_control_allowed(1,1,1,1,other_vendor));
    assert(!fx3_fixed_control_allowed(1,2,1,1,start));
    assert(!fx3_fixed_control_allowed(1,0,2,1,start));
    assert(!fx3_fixed_control_allowed(1,0,1,2,start));
    assert(!fx3_fixed_control_allowed(1,1,1,1,NULL));
    puts("{\"status\":\"BOUNDED_DEVICE_CONTROL_POLICY_PASS\",\"IOKit_calls\":0}");return 0;
}
