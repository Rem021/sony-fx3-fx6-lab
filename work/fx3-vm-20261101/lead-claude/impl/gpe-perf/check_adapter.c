#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <errno.h>
static void callback(const void*);
static int *stub_errno(void){return &errno;}
static int mock_printf(int,const char*,...);static int mock_open(const char*,int,...);
static long mock_read(int,void*,unsigned long);static long mock_pread(int,void*,unsigned long,long);
static int mock_close(int);static void *mock_mmap(void*,unsigned long,int,int,int,long);
static int mock_munmap(void*,unsigned long);static long mock_syscall(long,...);
static void *mock_dlsym(void*,const char*);static int mock_mprotect(void*,unsigned long,int);
#undef snprintf
#define dprintf mock_printf
#define open mock_open
#define read mock_read
#define pread mock_pread
#define close mock_close
#define mmap mock_mmap
#define munmap mock_munmap
#define syscall mock_syscall
#define mprotect mock_mprotect
#define dlsym mock_dlsym
#define __errno_location stub_errno
#define FX3_GPE_HOST_TEST 1
#define FX3_GPE102_HOST_TEST 1
#if CANDIDATE
#include "fx3-gpe-observe-v26-perf.c"
#else
#include "fx3-gpe-observe-v25-reference.c"
#endif
static unsigned char screen[EXT_BYTES],source[0x340000],screen_object[0x70],source_object[0x70];
static char extents_text[60000];static unsigned read_at[8];
static U proc_opens,maps_opens,physical_maps,physical_unmaps,physical_bytes,process_reads,log_calls,status_calls,observer_maps;
static int proc_bad,map_failure;static unsigned trace_pos;static char trace_order[16];static U callback_calls;
static int mock_printf(int fd,const char*fmt,...){(void)fd;(void)fmt;log_calls++;return 1;}
static int mock_open(const char*path,int flags,...){(void)flags;if(!strcmp(path,"/proc/udm/dmm_extents")){proc_opens++;read_at[1]=0;return 81;}if(!strcmp(path,"/proc/udm/dmm_units")){proc_opens++;read_at[2]=0;return 82;}if(!strcmp(path,"/proc/self/maps")){maps_opens++;read_at[3]=0;return 83;}return 80;}
static long mock_read(int fd,void*out,unsigned long n){char maps[128];snprintf(maps,sizeof maps,"%lx-%lx r-xp 0 0:0 0\n",(U)callback&~4095UL,((U)callback&~4095UL)+4096);const char*str=fd==81?extents_text:fd==82?"0402 00000403 0002 01 01 00 01 00000003 43feb5000 00140000 0081 < 0003\n":maps;if(proc_bad&&(fd==81||fd==82))str="corrupt\n";unsigned idx=(unsigned)fd-80;size_t len=strlen(str),at=read_at[idx];if(at>=len)return 0;size_t bytes=len-at;if(bytes>n)bytes=n;memcpy(out,str+at,bytes);read_at[idx]+=(unsigned)bytes;return (long)bytes;}
static long mock_pread(int fd,void*out,unsigned long n,long p){(void)fd;process_reads++;if(!p)return -1;memcpy(out,(void*)p,n);return(long)n;}
static int mock_close(int fd){(void)fd;return 0;}
static void *mock_mmap(void*p,unsigned long n,int prot,int flags,int fd,long offset){(void)p;(void)prot;(void)fd;if(flags==0x22){observer_maps++;return calloc(1,n);}physical_maps++;physical_bytes+=n;if(map_failure)return(void*)-1;if((U)offset==EXT_BASE){assert(n<=sizeof screen);return screen;}if((U)offset>=0x410924000UL&&(U)offset+n<=0x410c64000UL)return source+((U)offset-0x410924000UL);assert(0);return(void*)-1;}
static int mock_munmap(void*p,unsigned long n){(void)n;if((uintptr_t)p>=(uintptr_t)screen&&(uintptr_t)p<(uintptr_t)screen+sizeof screen){physical_unmaps++;return 0;}if((uintptr_t)p>=(uintptr_t)source&&(uintptr_t)p<(uintptr_t)source+sizeof source){physical_unmaps++;return 0;}free(p);return 0;}
static long mock_syscall(long number,...){(void)number;return 0;}
static void *mock_dlsym(void*h,const char*n){(void)h;(void)n;return NULL;}
static int mock_mprotect(void*p,unsigned long n,int prot){(void)p;(void)n;(void)prot;return 0;}
int dlinfo(void*h,int n,void*p){(void)h;(void)n;(void)p;return -1;}
int dladdr(const void*p,struct app_dl_info*out){(void)p;(void)out;return 0;}
static void p32(unsigned char*p,unsigned v){memcpy(p,&v,4);}static void p64(unsigned char*p,U v){memcpy(p,&v,8);}
static void callback(const void*p){const struct gpe_callback_param*c=p;assert(c->sequence==71&&c->argument==0xabc);callback_calls++;trace_order[trace_pos++]='c';}
static int complete(unsigned src,const void*p,size_t n){assert(src==0x123&&n==4&&!load32(p));status_calls++;trace_order[trace_pos++]='s';return 1;}
static void init_object(unsigned char*p,U token,U type,U logical,U phys,U bytes){memset(p,0,0x70);p64(p,0x90001000);p64(p+0x10,token);p32(p+0x20,0x10);p64(p+0x38,type);p32(p+0x40,(unsigned)token);p64(p+0x58,logical);p64(p+0x60,phys);p64(p+0x68,bytes);}
static void setup(void){
 physical=80;process_mem=80;obj_bound=1;resource_class_vptr=0x90001000;draw_complete=complete;
 size_t used=0;for(unsigned i=1;i<350;i++)if(i!=0x81)used+=(size_t)snprintf(extents_text+used,sizeof extents_text-used,"%04x 0003 00000001 00000546 00000000 00000000 00000003 0000008c 430500000 (430400000+100000) 00001000\n",i);
 snprintf(extents_text+used,sizeof extents_text-used,"0081 0003 00000001 00000545 00000000 00000000 00000003 0000008c 43feb5000 (430400000+fab5000) 00140000\n");
 init_object(screen_object,0x402,0x403,0x10000000,EXT_BASE,EXT_BYTES);init_object(source_object,0x501,0,0x20000000,0x410924000UL,sizeof source);
 life_enter();resource_add(screen_object,"native_open_return_v1");resource_add(source_object,"malloc_parent_v1");life_leave();
 FILE*f=fopen("build/textures.bin","rb");assert(f);size_t n=fread(source,1,sizeof source,f);assert(n);fclose(f);for(size_t i=n;i<sizeof source;i++)source[i]=source[i%n];
}
static void fill_param(unsigned char*p){memset(p,0,144);p64(p,PAYLOAD_BASE);p32(p+16,16);p32(p+20,2);p32(p+24,640);p[32]=0x20;p[33]=0x40;p[34]=0x60;p[35]=255;p[37]=255;p[38]=1;}
static void blit_param(unsigned char*p,unsigned sw,unsigned sh,unsigned dw,unsigned dh){memset(p,0,144);p64(p,PAYLOAD_BASE);p32(p+16,dw);p32(p+20,dh);p32(p+32,640);p32(p+36,480);p32(p+48,640);p64(p+56,0x410924000UL);p32(p+72,sw);p32(p+76,sh);p32(p+88,640);p[112]=1;p[114]=255;p[115]=1;p[121]=1;}
static double now(void){struct timespec t;assert(!clock_gettime(CLOCK_MONOTONIC,&t));return t.tv_sec+t.tv_nsec/1e9;}
static void reset_counts(void){proc_opens=maps_opens=physical_maps=physical_unmaps=physical_bytes=process_reads=log_calls=observer_maps=0;}
int main(void){setup();unsigned char raw[144];fill_param(raw);assert(!fill(0,0,1,0,raw));raw[38]=0;assert(!fill(0,0,71,0x123,raw)&&trace_order[0]=='s');
 trace_pos=0;p64(raw+40,(U)callback);p64(raw+48,0xabc);assert(!fill(0,0,71,0x123,raw));assert(callback_calls==1&&trace_pos==2&&trace_order[0]=='c'&&trace_order[1]=='s');
 unsigned char unchanged[EXT_BYTES];memcpy(unchanged,screen,sizeof unchanged);p64(raw+40,3);assert(fill(0,0,72,0x123,raw)==5&&!memcmp(unchanged,screen,sizeof unchanged));raster_failed=0;
 for(unsigned scenario=0;scenario<4;scenario++){
  if(scenario==0)fill_param(raw);else if(scenario==1)blit_param(raw,16,2,16,2);else if(scenario==2)blit_param(raw,1,2,441,2);else blit_param(raw,640,384,640,384);
  reset_counts();double start=now();for(unsigned j=0;j<60;j++)assert(!command(scenario?1:0,0,0,j,0,raw));double elapsed=(now()-start)*1e6/60;
  printf("ADAPTER,%d,%u,%.3f,%lu,%lu,%lu,%lu,%lu,%lu,%lu,%lu\n",CANDIDATE,scenario,elapsed,proc_opens,maps_opens,physical_maps,physical_unmaps,physical_bytes,process_reads,log_calls,observer_maps);
  U digest=14695981039346656037UL;for(unsigned z=0;z<sizeof screen;z++)digest=(digest^screen[z])*1099511628211UL;printf("ADAPTER_HASH,%u,%016lx\n",scenario,digest);
 }
 unsigned char before[EXT_BYTES];memcpy(before,screen,sizeof before);fill_param(raw);p32(screen_object+0x20,2);assert(fill(0,0,80,0,raw)==5&&!memcmp(before,screen,sizeof before));p32(screen_object+0x20,0x10);raster_failed=0;
#if CANDIDATE
 assert(map26_hits>50);U old=map26_revokes;life_enter();resource_retire(source_object,"host_close");life_leave();assert(map26_revokes>old);
 blit_param(raw,16,2,16,2);assert(blit(0,0,81,0,raw)==5&&!memcmp(before,screen,sizeof before));raster_failed=0;
 life_enter();resource_add(source_object,"malloc_parent_v1");life_leave();assert(!blit(0,0,82,0,raw));assert(!GPE26_CALLBACK_CACHE);assert(!GPE26_TEXTURE_OBSERVE);
 U misses=map26_misses;life_enter();resource_retire(source_object,"host_reopen");resource_add(source_object,"malloc_parent_v1");life_leave();assert(!blit(0,0,83,0,raw));assert(map26_misses>misses);
 proc_bad=1;fill_param(raw);assert(!fill(0,0,84,0,raw));proc_bad=0;
 life_enter();for(unsigned i=0;i<RESOURCE_LIMIT;i++)if(resources[i].active)map26_retire(resources[i].object);life_leave();
#else
 if(tex102_workspace){free(tex102_workspace);tex102_workspace=NULL;tex102_workspace_capacity=0;}
#endif
 puts("ADAPTER_PASS object_authority/epoch/revoke/stale-zero-write/strict-exec-fallback/diagnostic-off");return 0;}
