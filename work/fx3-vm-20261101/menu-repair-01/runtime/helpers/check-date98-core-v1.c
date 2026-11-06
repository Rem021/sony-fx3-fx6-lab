#include <assert.h>
#include <pthread.h>
#include <stdio.h>
#include <string.h>
typedef unsigned long U;typedef unsigned W;
#include "fx3-date98-trace-core-v1.h"
static _Alignas(64) unsigned char page[65536];
static void*worker(void*x){U k=(U)x;unsigned char raw[64];for(unsigned i=0;i<64;i++)raw[i]=i+k;for(U j=0;j<20;j++){unsigned char*r=d98_begin(page+4096,k,228,427,0x80900141,32,0x1234,0x5678,raw,1,2,7,0);d98_end(r,-1021,5,raw,32,1,2,8,0);}return 0;}
static U getu(unsigned char*p){U x;memcpy(&x,p,8);return x;}static W getword(unsigned char*p){W x;memcpy(&x,p,4);return x;}
int main(void){memset(page,0x5a,sizeof page);memset(page+4096,0,DATE98_SPAN);assert(!d98_init(page+4096,64)&&getu(page+4096)==0);assert(d98_init(page+4096,DATE98_SPAN));pthread_t ts[4];for(U i=0;i<4;i++)assert(!pthread_create(ts+i,0,worker,(void*)(i+1)));for(U i=0;i<4;i++)assert(!pthread_join(ts[i],0));unsigned char*p=page+4096;assert(getu(p+32)==80&&getu(p+40)==16);for(U i=0;i<64;i++){unsigned char*r=p+64+i*DATE98_REC;assert(getu(r)==4&&getu(r+8)==i+1&&getword(r+48)==2&&(int)getword(r+52)==-1021&&getword(r+60)==1&&getword(r+64)==1&&r[192]==getword(r+76)&&!memcmp(r+192,r+256,32));}assert(d98_init(p,DATE98_SPAN)&&getu(p+32)==80);for(unsigned i=0;i<4096;i++)assert(page[i]==0x5a);for(unsigned i=4096+DATE98_SPAN;i<sizeof page;i++)assert(page[i]==0x5a);puts("DATE98_CORE_PASS 4producers80events/64slots16drops/odd_even_publish/full32_before_after/no_reinit/input4K_and_tail_guards");}
