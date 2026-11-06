/* Own parser tests, no IOKit or Sony code. */
#include "descriptor_policy.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static const uint8_t two[32]={9,2,32,0,1,1,0,0x80,50,9,4,3,0,2,255,255,255,0,7,5,6,2,0,2,0,7,5,0x85,2,0,2,0};
int main(void){
    fx3_profile p={0};assert(fx3_parse_service_config(two,32,1,1,&p)==FX3T_OK);
    assert(p.number==3 && p.in_address==0x85 && p.out_address==6 && p.max_packet==512);
    uint8_t four[46];memcpy(four,two,32);four[2]=46;four[13]=4;
    const uint8_t extras[14]={7,5,8,2,0,2,0,7,5,0x87,2,0,2,0};memcpy(four+32,extras,14);
    assert(fx3_parse_service_config(four,46,1,1,&p)==FX3T_OK && p.in_address==0x85 && p.out_address==6 && p.endpoints==4);
    for(unsigned n=0;n<32;n++){memset(&p,0x77,sizeof(p));assert(fx3_parse_service_config(two,n,1,1,&p)==FX3T_SHAPE);assert(!memcmp(&p,(fx3_profile[1]){{0}},sizeof(p)));}
    const unsigned offsets[]={0,1,2,4,5,7,9,10,12,13,14,18,19,20,21,23};
    for(unsigned i=0;i<sizeof(offsets)/sizeof(offsets[0]);i++){
        uint8_t b[32];memcpy(b,two,32);b[offsets[i]]=0;
        if(offsets[i]==12)b[12]=1; /* alternate setting */
        assert(fx3_parse_service_config(b,32,1,1,&p)==FX3T_SHAPE);
    }
    uint8_t duplicate[46];memcpy(duplicate,four,46);duplicate[34]=6;
    assert(fx3_parse_service_config(duplicate,46,1,1,&p)==FX3T_SHAPE);
    assert(fx3_parse_service_config(two,32,2,1,&p)==FX3T_SHAPE);
    assert(fx3_parse_service_config(two,32,1,0,&p)==FX3T_SHAPE);
    assert(fx3_parse_service_config(NULL,32,1,1,&p)==FX3T_SHAPE);
    assert(fx3_parse_service_config(two,32,1,1,NULL)==FX3T_DENIED);
    puts("PASS descriptor policy:2/4 endpoints,32 truncated prefixes,16 field mutations,duplicate endpoint,configuration and null bounds");return 0;
}
