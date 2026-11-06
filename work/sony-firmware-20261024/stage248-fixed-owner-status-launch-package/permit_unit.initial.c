/* Own ordinary-user permit-file and registry-gate checks; no IOKit linked. */
#include "status_permit.h"
#include "target_binding.h"
#include <CommonCrypto/CommonDigest.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
int main(int argc,char **argv){
    if(argc!=3 || getuid()!=geteuid() || !getuid())return 64;
    FILE *f=fopen(argv[1],"rb");if(!f)return 65;unsigned char p[97]={0};size_t n=fread(p,1,sizeof(p),f);fclose(f);
    unsigned char nonce[16];memcpy(nonce,FX3_FIXED_NONCE,16);
    if(n!=96 || !fx3_status_permit_bytes(p,n,nonce))return 66;
    unsigned checks=1;
    unsigned offsets[]={0,16,20,24,40,44,48,56,64};
    for(unsigned i=0;i<sizeof(offsets)/sizeof(offsets[0]);++i){
        unsigned char q[96];memcpy(q,p,96);q[offsets[i]]^=1;
        if(offsets[i]!=64)CC_SHA256(q,64,q+64);
        if(fx3_status_permit_bytes(q,96,nonce))return 67;++checks;
    }
    nonce[0]^=1;if(fx3_status_permit_bytes(p,96,nonce))return 68;++checks;
    memcpy(nonce,FX3_FIXED_NONCE,16);
    if(fx3_status_permit_bytes(p,95,nonce) || fx3_status_permit_bytes(p,97,nonce))return 69;checks+=2;
    if(!fx3_target_registry_permitted(FX3_CACHED_REGISTRY_ID,0) || fx3_target_registry_permitted(FX3_CACHED_REGISTRY_ID+1,0) ||
       !fx3_target_registry_permitted(FX3_CACHED_REGISTRY_ID+1,1))return 70;checks+=3;
    if(fx3_status_permit_test_file(argv[2],getuid(),nonce)!=(getenv("EXPECT_PERMIT_FILE_DENY")?0:1))return 71;++checks;
    printf("{\"permit_and_registry_checks\":%u,\"root_or_USB_operations\":0}\n",checks);return 0;
}
