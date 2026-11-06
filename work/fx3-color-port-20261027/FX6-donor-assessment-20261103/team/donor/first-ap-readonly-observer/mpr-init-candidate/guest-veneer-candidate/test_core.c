#include "bridge_core.h"
#include "callback_offsets.h"
#include "sha256.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static uint16_t rd16(const uint8_t* p){return (uint16_t)(p[0]|(p[1]<<8));}
static uint32_t rd32(const uint8_t* p){return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static uint64_t rd64(const uint8_t* p){return (uint64_t)rd32(p)|((uint64_t)rd32(p+4)<<32);}
static void put32(uint8_t* p,uint32_t v){for(unsigned i=0;i<4;i++)p[i]=(uint8_t)(v>>(8*i));}
static void digest(const uint8_t* b,size_t n,char out[65]){
    static const char hex[]="0123456789abcdef";uint8_t d[32];fx6_sha256_ctx c;
    fx6_sha256_init(&c);fx6_sha256_update(&c,b,n);fx6_sha256_final(&c,d);
    for(unsigned i=0;i<32;i++){out[2*i]=hex[d[i]>>4];out[2*i+1]=hex[d[i]&15];}out[64]=0;
}
int main(int argc,char** argv){
    assert(argc==3);
    char hex[65];digest((const uint8_t*)"abc",3,hex);
    assert(strcmp(hex,"ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")==0);
    FILE* f=fopen(argv[1],"rb");assert(f);uint8_t raw[0x290];
    assert(fread(raw,1,sizeof(raw),f)==sizeof(raw));assert(fgetc(f)==EOF);assert(fclose(f)==0);
    digest(raw,sizeof(raw),hex);
    assert(strcmp(hex,"585d8918da368cec6ef689aa3c14dc3306311ab6661c0bffc9a02e1685430cf1")==0);
    f=fopen(argv[2],"rb");assert(f);fx6_sha256_ctx c;fx6_sha256_init(&c);
    uint8_t block[8192];size_t n;
    while((n=fread(block,1,sizeof(block),f))!=0)fx6_sha256_update(&c,block,n);
    assert(feof(f));assert(fclose(f)==0);
    uint8_t d[32];fx6_sha256_final(&c,d);
    static const char hexd[]="0123456789abcdef";
    for(unsigned i=0;i<32;i++){hex[2*i]=hexd[d[i]>>4];hex[2*i+1]=hexd[d[i]&15];}hex[64]=0;
    assert(strcmp(hex,"c31bc293816db5d63cc5acf6b019bd69c9dd7b940ae0ece1ea6977ff9b944db1")==0);
    uintptr_t thunks[57];for(unsigned i=0;i<57;i++)thunks[i]=0x70000000u+8u*i;
    fx6diag_plan p;
    assert(fx6diag_map(raw,sizeof(raw),thunks,&p)==FX6DIAG_MAP_OK);
    assert(p.count==2&&p.slots[0]==0x1000&&p.slots[1]==0x1010&&p.slots[2]==0&&p.slots[3]==0);
    assert(p.source_u16==1440&&rd16(p.mapped+0x1f2)==780&&p.extra_nonnull==10);
    assert(rd32(p.mapped+0x1d0)==2&&rd32(p.mapped+0x1d4)==0x1000&&rd32(p.mapped+0x1d8)==0x1010);
    unsigned nonnull=0;
    for(unsigned i=0;i<57;i++){
        uint64_t orig=rd64(raw+fx6diag_src_offsets[i]);
        assert(p.original_callbacks[i]==orig);
        assert(rd64(p.mapped+fx6diag_dst_offsets[i])==(orig?(uint64_t)thunks[i]:0));
        if(orig)nonnull++;
    }
    assert(nonnull==46);
    assert(fx6diag_map(raw,sizeof(raw)-1,thunks,&p)==FX6DIAG_MAP_LENGTH);
    assert(p.count==0&&p.original_callbacks[0]==0); /* failure clears stale output */
    uint8_t changed[0x290];memcpy(changed,raw,sizeof(raw));put32(changed+0x268,5);
    assert(fx6diag_map(changed,sizeof(changed),thunks,&p)==FX6DIAG_MAP_COUNT);
    memcpy(changed,raw,sizeof(raw));put32(changed+0x26c,0xffff);
    assert(fx6diag_map(changed,sizeof(changed),thunks,&p)==FX6DIAG_MAP_SENTINEL);
    memcpy(changed,raw,sizeof(raw));put32(changed+0x270,0x1000);
    assert(fx6diag_map(changed,sizeof(changed),thunks,&p)==FX6DIAG_MAP_DUPLICATE);
    memcpy(changed,raw,sizeof(raw));changed[0x28a]=0;
    assert(fx6diag_map(changed,sizeof(changed),thunks,&p)==FX6DIAG_MAP_U16);
    thunks[0]=0;assert(fx6diag_map(raw,sizeof(raw),thunks,&p)==FX6DIAG_MAP_THUNK);
    thunks[0]=(uintptr_t)rd64(raw+fx6diag_src_offsets[0]);
    assert(fx6diag_map(raw,sizeof(raw),thunks,&p)==FX6DIAG_MAP_THUNK);
    puts("host SHA vectors, original snapshot, 57 slot projection, 10 extras and rejection cases: PASS");
    return 0;
}
