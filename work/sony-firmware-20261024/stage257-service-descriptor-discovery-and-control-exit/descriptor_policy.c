#include "descriptor_policy.h"
#include <string.h>
static uint16_t le16(const uint8_t *p){return(uint16_t)(p[0]|(uint16_t)p[1]<<8);}
int fx3_parse_service_config(const uint8_t *raw,uint32_t bytes,uint8_t configurations,uint8_t active,fx3_profile *out){
    if(!out)return FX3T_DENIED;
    memset(out,0,sizeof(*out));
    if(!raw || bytes<9 || bytes>FX3_CONFIG_MAX || configurations!=1 || !active || raw[0]!=9 || raw[1]!=2 || le16(raw+2)!=bytes || raw[4]!=1 || raw[5]!=active || !(raw[7]&0x80))return FX3T_SHAPE;
    fx3_profile p={0};uint32_t at=9,interfaces=0,endpoints=0,ins=0,outs=0;uint32_t seen=0;
    while(at<bytes){
        if(bytes-at<2 || raw[at]<2 || raw[at]>bytes-at)return FX3T_SHAPE;
        const uint8_t *d=raw+at;uint32_t length=d[0];
        if(d[1]==4){
            if(length!=9 || interfaces++ || d[3]!=0 || d[5]!=255 || (d[4]!=2 && d[4]!=4))return FX3T_SHAPE;
            p.number=d[2];p.alternate=d[3];p.endpoints=d[4];p.cls=d[5];p.subclass=d[6];p.protocol=d[7];
        }else if(d[1]==5){
            if(length!=7 || interfaces!=1 || endpoints>=p.endpoints || d[2]&0x70 || !(d[2]&15) || d[3]!=2 || le16(d+4)!=512)return FX3T_SHAPE;
            uint32_t bit=(d[2]&15)+(d[2]&0x80?16:0);if(seen&(1u<<bit))return FX3T_SHAPE;seen|=1u<<bit;
            if(d[2]&0x80){if(!ins)p.in_address=d[2];ins++;}
            else{if(!outs)p.out_address=d[2];outs++;}
            endpoints++;
        }else return FX3T_SHAPE;
        at+=length;
    }
    if(interfaces!=1 || endpoints!=p.endpoints || ins!=p.endpoints/2 || outs!=p.endpoints/2)return FX3T_SHAPE;
    p.max_packet=512;*out=p;return FX3T_OK;
}
