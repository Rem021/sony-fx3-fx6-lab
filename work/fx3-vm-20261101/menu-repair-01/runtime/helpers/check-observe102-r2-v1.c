#define _DARWIN_C_SOURCE
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <errno.h>
#include <assert.h>
#include <sys/mman.h>
#include <pthread.h>
#include <unistd.h>
#include "fx3-gpe-backend-v8.h"
typedef unsigned long U;int*__errno_location(void){return &errno;}
static unsigned load32(const unsigned char*p){unsigned x;memcpy(&x,p,4);return x;}static U load64(const unsigned char*p){U x;memcpy(&x,p,8);return x;}
#define TEX102_MAP_FLAGS (MAP_PRIVATE|MAP_ANON)
#include "fx3-texture-observe102-v2.h"
#define FX3_GPE102_HOST_TEST 1
#include "fx3-gpe-command-wait102-v1.h"
static unsigned char lock102;
static void*release_lock(void*unused){(void)unused;usleep(20000);__atomic_clear(&lock102,__ATOMIC_RELEASE);return 0;}
int main(void){
 unsigned char*src=mmap(0,4096,3,MAP_PRIVATE|MAP_ANON,-1,0),*dst=mmap(0,4096,3,MAP_PRIVATE|MAP_ANON,-1,0);assert(src!=MAP_FAILED&&dst!=MAP_FAILED);unsigned char bytes[16]={0x23,0x01,0x67,0x45,0xaa,0xbb,0xcc,0xdd,0xab,0x89,0xef,0xcd,0x11,0x22,0x33,0x44};memcpy(src,bytes,16);unsigned char raw[144]={0};raw[112]=1;raw[114]=255;raw[115]=1;struct gpe_plan p={.src_rows=2,.src_line=4,.src_step=8,.src_bpp=2,.rows=2,.line=4,.dst_step=8};struct tex102_sample t={0};errno=73;tex102_before(&t,raw,&p,src,dst,7,1,2);assert(errno==73&&t.enabled&&!memcmp(src,bytes,16));assert(!memcmp(t.source_copy,bytes,4)&&!memcmp(t.source_copy+4,bytes+8,4));dst[0]=0x99;tex102_after(&t,&p,dst,0);assert(dst[0]==0x99&&errno==73);assert(!mprotect(src,4096,PROT_NONE)&&!mprotect(dst,4096,PROT_NONE));tex102_emit(&t);assert(errno==73);munmap(src,4096);munmap(dst,4096);p.empty_clip_noop=1;memset(&t,0,sizeof t);tex102_before(&t,raw,&p,0,0,8,1,2);tex102_emit(&t);assert(!t.enabled);
 assert(!gpe102_take(&lock102,10,1));__atomic_clear(&lock102,__ATOMIC_RELEASE);__atomic_test_and_set(&lock102,__ATOMIC_ACQUIRE);pthread_t thread;assert(!pthread_create(&thread,0,release_lock,0));errno=41;U start=gpe102_now();assert(!gpe102_take(&lock102,11,1));U elapsed=gpe102_now()-start;assert(elapsed>=10000000&&elapsed<500000000&&errno==41);pthread_join(thread,0);__atomic_clear(&lock102,__ATOMIC_RELEASE);__atomic_test_and_set(&lock102,__ATOMIC_ACQUIRE);start=gpe102_now();assert(gpe102_take(&lock102,12,1)==-1);elapsed=gpe102_now()-start;assert(elapsed>=450000000&&elapsed<900000000&&lock102&&errno==41);__atomic_clear(&lock102,__ATOMIC_RELEASE);puts("AP102_R2_OFFLOCK_PROT_NONE_COPY_SHA_HIST_ERRNO_BOUNDED_WAIT_PASS");return 0;
}
