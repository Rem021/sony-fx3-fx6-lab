#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stdarg.h>
typedef unsigned long U;static int error;static U ticks=100000;static unsigned maps,unmaps;static unsigned char guarded[0x80000+32],other[4096];
static int*stub_errno(void){return &error;}static U gpe102_now(void){ticks+=100;error=999;return ticks;}
static long stub_syscall(long n,...){assert(n==172||n==178);error=998;return n==172?42:43;}
static int stub_printf(int fd,const char*fmt,...){assert(fd==2&&fmt);error=997;return 0;}
static void*stub_mmap(void*p,U n,int prot,int flags,int fd,long off){assert(!p&&prot==3&&flags==1);maps++;error=13;if(n==0x80000){assert(fd==9&&off==0x41d640000UL);return guarded+16;}assert(n==4096&&fd==7&&off==0x1000);return other;}
static int stub_munmap(void*p,U n){assert(p==other&&n==4096);unmaps++;error=17;return 0;}
#define __errno_location stub_errno
#define syscall stub_syscall
#define dprintf stub_printf
#define mmap stub_mmap
#define munmap stub_munmap
#include "fx3-gpe-profile104-v1.h"
int main(void){memset(guarded,0xa5,sizeof guarded);memset(guarded+16,0,0x80000);error=41;pr104_init(9);assert(error==41&&pr104_ring&&pr104_ring[0]==PR104_MAGIC&&maps==1);struct pr104_context a,b;error=51;pr104_begin(&a,42,1,0x808261c0);assert(error==51&&pr104_current==&a);U t=pr104_start();error=52;pr104_end(P104_BACKEND,t);assert(error==52);assert(pr104_mmap(0,4096,3,1,7,0x1000)==other&&error==13&&maps==2);assert(!pr104_munmap(other,4096)&&error==17&&unmaps==1);pr104_begin(&b,43,4,0x808261c0);assert(pr104_current==&b&&pr104_ring[6]==2);pr104_finish(&b,5,0,24);assert(pr104_current==&a&&pr104_ring[6]==1);unsigned char raw[144]={0};raw[114]=255;pr104_finish(&a,0,raw,144);assert(!pr104_current&&!pr104_ring[6]&&pr104_ring[5]==2&&pr104_ring[7]==2);U*row=(U*)((unsigned char*)pr104_ring+4096);assert(row[0]==1&&row[1]==1&&row[2]==43&&row[3]==42&&row[4]==1&&row[32+P104_BACKEND]==1&&row[32+P104_MMAP]==1&&row[32+P104_MUNMAP]==1&&row[54]==~0UL&&row[55]==~0UL);
 for(unsigned i=0;i<PR104_CAP+5;i++){pr104_begin(&a,100+i,0,0);pr104_finish(&a,0,raw,56);}assert(pr104_ring[4]==PR104_CAP+7&&pr104_ring[5]==PR104_CAP+7&&!pr104_ring[6]);for(unsigned i=0;i<16;i++)assert(guarded[i]==0xa5&&guarded[sizeof guarded-16+i]==0xa5);for(unsigned i=0;i<PR104_CAP;i++){U*w=(U*)((unsigned char*)pr104_ring+4096+i*512);assert(w[0]&&w[0]==w[1]&&w[7]>=w[6]);}puts("AP104_PROFILE_RING_BOUNDS_WRAP_NESTED_ERRNO_EXACT_MAP_ARGS_UNKNOWN_FIFO_ASAN_UBSAN_PASS");}
