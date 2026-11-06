#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <errno.h>
#include <assert.h>
#include "fx3-gpe-backend-v8.h"
typedef unsigned long U;int*__errno_location(void){return &errno;}
static unsigned load32(const unsigned char*p){unsigned x;memcpy(&x,p,4);return x;}static U load64(const unsigned char*p){U x;memcpy(&x,p,8);return x;}
#include "fx3-texture-observe102-v1.h"
int main(void){struct tex102_sha s;char out[65];tex102_init(&s);tex102_update(&s,(const unsigned char*)"abc",3);tex102_final(&s,out);assert(!strcmp(out,"ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"));unsigned char src[16]={0x23,0x01,0x67,0x45,0xaa,0xbb,0xcc,0xdd,0xab,0x89,0xef,0xcd,0x11,0x22,0x33,0x44},dst[16]={0},raw[144]={0},copy[16];memcpy(copy,src,16);raw[112]=1;raw[114]=255;raw[115]=1;struct gpe_plan p={.src_rows=2,.src_line=4,.src_step=8,.src_bpp=2,.rows=2,.line=4,.dst_step=8};struct tex102_sample t={0};errno=73;tex102_before(&t,raw,&p,src,dst,7,1,2);assert(errno==73&&t.enabled&&!strcmp(t.source,"5b04152862e327dd78c3768ec10140e01452d4f3230f49af8bb09ac84b3bc6bb"));assert(!memcmp(copy,src,16));for(unsigned c=0;c<4;c++){unsigned count=0;for(unsigned i=0;i<16;i++)count+=t.hist[c][i];assert(count==4);}dst[0]=0x99;tex102_after(&t,&p,dst,0);assert(dst[0]==0x99&&errno==73);p.empty_clip_noop=1;memset(&t,0,sizeof t);tex102_before(&t,raw,&p,0,0,8,1,2);assert(!t.enabled);puts("AP102_TEXTURE_SHA_ROWS_HIST_EMPTY_ERRNO_PASS");return 0;}
