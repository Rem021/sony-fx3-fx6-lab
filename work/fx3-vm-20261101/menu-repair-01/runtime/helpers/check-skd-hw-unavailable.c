#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#define mmap skd_guard_mmap
#define dladdr fake_dladdr
#define readlink fake_readlink
#include "fx3-skd-hw-unavailable-v1.c"
#undef readlink
#undef dladdr
#undef mmap
static int error;int *__errno_location(void){return &error;}
static const char *module="/usr/lib/libInfraSKD.so",*fd_target="/dev/mem";static int readable_fd=6;static unsigned calls;static void *last_address;static unsigned long last_size;static int last_prot,last_flags,last_fd;static long last_offset;
int fake_dladdr(const void *p,struct skd_dl_info *i){(void)p;i->file=module;i->base=(void *)0x12340000000UL;return 1;}
long fake_readlink(const char *p,char *out,size_t capacity){char exact[64];snprintf(exact,sizeof exact,"/proc/self/fd/%d",readable_fd);if(strcmp(p,exact))return -1;size_t n=strlen(fd_target);if(n>capacity)n=capacity;memcpy(out,fd_target,n);error=77;return n;}
static void *original(void *a,size_t n,int p,int f,int fd,long off){calls++;last_address=a;last_size=n;last_prot=p;last_flags=f;last_fd=fd;last_offset=off;assert(error==42);error=91;return (void *)0xabc000;}
static void reset(void){error=42;calls=0;module="/usr/lib/libInfraSKD.so";fd_target="/dev/mem";readable_fd=6;skd_next_mmap=original;setenv("FX3_SKD_HW","unavailable-rom-v1",1);}
static void forward(void *a,size_t n,int p,int f,int fd,long off,void *caller){assert(skd_mmap_dispatch(a,n,p,f,fd,off,caller)==(void *)0xabc000&&calls==1&&error==91);assert(a==last_address&&n==last_size&&p==last_prot&&f==last_flags&&fd==last_fd&&off==last_offset);}
int main(void){void *caller=(void *)0x123400645ecUL;reset();assert(skd_mmap_dispatch(0,0x1000,1,1,6,0xffffb000,caller)==(void *)-1&&error==19&&!calls);for(unsigned i=0;i<2;i++){reset();forward(0,0x1000,1,1,6,0xffffb000+(i?0x1000:-0x1000),caller);reset();forward(0,i?0x2000:0xfff,1,1,6,0xffffb000,caller);reset();forward(0,0x1000,i?3:0,1,6,0xffffb000,caller);reset();forward(0,0x1000,1,i?2:0x11,6,0xffffb000,caller);}reset();forward(0,0x1000,1,1,7,0xffffb000,caller);reset();fd_target="/dev/zero";forward(0,0x1000,1,1,6,0xffffb000,caller);reset();module="/usr/lib/appFw.so";forward(0,0x1000,1,1,6,0xffffb000,caller);reset();forward(0,0x1000,1,1,6,0xffffb000,(void *)((unsigned long)caller+4));reset();forward((void *)0x1000,0x1000,1,1,6,0xffffb000,caller);reset();forward(0,0x1000,1,1,6,0xf340f000,caller);reset();forward(0,0x1000,1,1,6,0xf13b8000,caller);reset();setenv("FX3_SKD_HW","off",1);forward(0,0x1000,1,1,6,0xffffb000,caller);puts("SKD_HW_UNAVAILABLE_PASS exact_tuple_caller_fd_only/MAP_FAILED_ENODEV/no_ROM_key/adjacent_tuple_fd_caller_regions_forward/errno_preserved");}
