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
static char effects[8192];static unsigned effect_n;static void effect(char c){assert(effect_n+1<sizeof effects);effects[effect_n++]=c;effects[effect_n]=0;}
static char log_lines[64][2048];static unsigned log_n;static unsigned clocks;static unsigned long ns_value=1000000100UL;static int test_case,first_read_errno=-1;
static int seam_clock(int clock_id,struct timespec*t){assert(clock_id==CLOCK_MONOTONIC);effect('C');clocks++;errno=233;
 if(TEST_CANDIDATE&&clocks==1){if(test_case==3)return -1;t->tv_sec=test_case==4?0:1;t->tv_nsec=0;return 0;}
 unsigned long n=ns_value;ns_value+=test_case==2?1000000000UL:100UL;t->tv_sec=(long)(n/1000000000UL);t->tv_nsec=(long)(n%1000000000UL);return 0;}
static int seam_sleep(const struct timespec*a,struct timespec*b){(void)a;(void)b;effect('N');return 0;}
#define clock_gettime seam_clock
#define nanosleep seam_sleep
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
#define FX3_GPE104_HOST_TEST 1
#include ADAPTER_SOURCE
static unsigned char screen[EXT_BYTES],source[0x340000],screen_object[0x70],source_object[0x70];
static char extents_text[60000];static unsigned read_at[8];
static U proc_opens,maps_opens,physical_maps,physical_unmaps,physical_bytes,process_reads,log_calls,status_calls,observer_maps;
static int proc_bad,map_failure;static unsigned trace_pos;static char trace_order[16];static U callback_calls;
static int mock_printf(int fd,const char*fmt,...){(void)fd;log_calls++;effect('L');assert(log_n<64);va_list a;va_start(a,fmt);int n=vsnprintf(log_lines[log_n],2048,fmt,a);va_end(a);assert(n>=0&&n<2048);log_n++;errno=234;return n;}
static int mock_open(const char*path,int flags,...){effect('O');(void)flags;if(!strcmp(path,"/proc/udm/dmm_extents")){proc_opens++;read_at[1]=0;return 81;}if(!strcmp(path,"/proc/udm/dmm_units")){proc_opens++;read_at[2]=0;return 82;}if(!strcmp(path,"/proc/self/maps")){maps_opens++;read_at[3]=0;return 83;}return 80;}
static long mock_read(int fd,void*out,unsigned long n){effect('R');char maps[128];snprintf(maps,sizeof maps,"%lx-%lx r-xp 0 0:0 0\n",(U)callback&~4095UL,((U)callback&~4095UL)+4096);const char*str=fd==81?extents_text:fd==82?"0402 00000403 0002 01 01 00 01 00000003 43feb5000 00140000 0081 < 0003\n":maps;if(proc_bad&&(fd==81||fd==82))str="corrupt\n";unsigned idx=(unsigned)fd-80;size_t len=strlen(str),at=read_at[idx];if(at>=len)return 0;size_t bytes=len-at;if(bytes>n)bytes=n;memcpy(out,str+at,bytes);read_at[idx]+=(unsigned)bytes;return (long)bytes;}
static long mock_pread(int fd,void*out,unsigned long n,long p){effect('P');if(first_read_errno<0)first_read_errno=errno;(void)fd;process_reads++;if(!p)return -1;memcpy(out,(void*)p,n);return(long)n;}
static int mock_close(int fd){effect('X');(void)fd;return 0;}
static void *mock_mmap(void*p,unsigned long n,int prot,int flags,int fd,long offset){effect('M');(void)p;(void)prot;(void)fd;if(flags==0x22){observer_maps++;return calloc(1,n);}physical_maps++;physical_bytes+=n;if(map_failure)return(void*)-1;if((U)offset==EXT_BASE){assert(n<=sizeof screen);return screen;}if((U)offset>=0x410924000UL&&(U)offset+n<=0x410c64000UL)return source+((U)offset-0x410924000UL);assert(0);return(void*)-1;}
static int mock_munmap(void*p,unsigned long n){effect('U');(void)n;if((uintptr_t)p>=(uintptr_t)screen&&(uintptr_t)p<(uintptr_t)screen+sizeof screen){physical_unmaps++;return 0;}if((uintptr_t)p>=(uintptr_t)source&&(uintptr_t)p<(uintptr_t)source+sizeof source){physical_unmaps++;return 0;}free(p);return 0;}
static long mock_syscall(long number,...){effect('S');return number==178?7301:0;}
static void *mock_dlsym(void*h,const char*n){(void)h;(void)n;return NULL;}
static int mock_mprotect(void*p,unsigned long n,int prot){(void)p;(void)n;(void)prot;return 0;}
int dlinfo(void*h,int n,void*p){(void)h;(void)n;(void)p;return -1;}
int dladdr(const void*p,struct app_dl_info*out){(void)p;(void)out;return 0;}
static void p32(unsigned char*p,unsigned v){memcpy(p,&v,4);}static void p64(unsigned char*p,U v){memcpy(p,&v,8);}
static void callback(const void*p){const struct gpe_callback_param*c=p;assert(c->sequence==71&&c->argument==0xabc);callback_calls++;effect('c');errno=25;trace_order[trace_pos++]='c';}
static int complete(unsigned src,const void*p,size_t n){assert(src==0x123&&n==4&&!load32(p));status_calls++;effect('s');errno=30;trace_order[trace_pos++]='s';return 1;}
static void init_object(unsigned char*p,U token,U type,U logical,U phys,U bytes){memset(p,0,0x70);p64(p,0x90001000);p64(p+0x10,token);p32(p+0x20,0x10);p64(p+0x38,type);p32(p+0x40,(unsigned)token);p64(p+0x58,logical);p64(p+0x60,phys);p64(p+0x68,bytes);}
static void setup(void){
 physical=80;process_mem=80;obj_bound=1;resource_class_vptr=0x90001000;draw_complete=complete;
 size_t used=0;for(unsigned i=1;i<350;i++)if(i!=0x81)used+=(size_t)snprintf(extents_text+used,sizeof extents_text-used,"%04x 0003 00000001 00000546 00000000 00000000 00000003 0000008c 430500000 (430400000+100000) 00001000\n",i);
 snprintf(extents_text+used,sizeof extents_text-used,"0081 0003 00000001 00000545 00000000 00000000 00000003 0000008c 43feb5000 (430400000+fab5000) 00140000\n");
 init_object(screen_object,0x402,0x403,0x10000000,EXT_BASE,EXT_BYTES);init_object(source_object,0x501,0,0x20000000,0x410924000UL,sizeof source);
 life_enter();resource_add(screen_object,"native_open_return_v1");resource_add(source_object,"malloc_parent_v1");life_leave();
 memset(source,0x3a,sizeof source);
}
static void fill_param(unsigned char*p){memset(p,0,144);p64(p,PAYLOAD_BASE);p32(p+16,16);p32(p+20,2);p32(p+24,640);p[32]=0x20;p[33]=0x40;p[34]=0x60;p[35]=255;p[37]=255;p[38]=1;}
static void blit_param(unsigned char*p,unsigned sw,unsigned sh,unsigned dw,unsigned dh){memset(p,0,144);p64(p,PAYLOAD_BASE);p32(p+16,dw);p32(p+20,dh);p32(p+32,640);p32(p+36,480);p32(p+48,640);p64(p+56,0x410924000UL);p32(p+72,sw);p32(p+76,sh);p32(p+88,640);p[112]=1;p[114]=255;p[115]=1;p[121]=1;}

int main(int argc,char**argv){assert(argc==2);test_case=atoi(argv[1]);assert(test_case>=0&&test_case<=4);setup();
 unsigned char raw[144];fill_param(raw);raw[38]=0;p64(raw+40,(U)callback);p64(raw+48,0xabc);
 if(test_case==2)command_lock=1;
 effect_n=log_n=clocks=0;first_read_errno=-1;log_calls=status_calls=callback_calls=0;trace_pos=0;memset(trace_order,0,sizeof trace_order);errno=17;
 int result=command(0,test_case==1?1:0,0,71,0x123,raw);int after=errno;
 unsigned pixels=0;for(unsigned y=0;y<2;y++)for(unsigned x=0;x<16;x++){unsigned char*p=screen+0x100+((unsigned long)y*640+x)*2;uint16_t value;memcpy(&value,p,2);if(value==0x246f)pixels++;}
 if(test_case==1||test_case==2){assert(result==5&&callback_calls==0&&status_calls==0&&pixels==0);}else{assert(result==0&&callback_calls==1&&status_calls==1&&trace_pos==2&&trace_order[0]=='c'&&trace_order[1]=='s');assert(pixels==32);}
 assert(first_read_errno==17);
 printf("SUMMARY {\"case\":%d,\"candidate\":%d,\"result\":%d,\"errno\":%d,\"first_read_errno\":%d,\"clock_calls\":%u,\"log_calls\":%lu,\"callback_calls\":%lu,\"SendDrawComp_calls\":%lu,\"pixels\":%u,\"effects\":\"%s\",\"callback_order\":\"%s\"}\n",test_case,TEST_CANDIDATE,result,after,first_read_errno,clocks,log_calls,callback_calls,status_calls,pixels,effects,trace_order);
 for(unsigned i=0;i<log_n;i++)printf("LOG %s",log_lines[i]);return 0;}
