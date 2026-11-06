#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
typedef unsigned long size_t;
struct cap_dl_info {const char*file;void*base;const char*symbol;void*address;};
static int error91,alloc_result,send_result,return_alloc_on_failure;
static unsigned alloc_count,release_count,send_count,start_count;
static unsigned char messages91[32][20],*allocation91;static unsigned alloc_index;
static unsigned long times91[32],now91=500000000,opened91=1000000000;
static unsigned char *obj_image91,*instance91,*config91,*states91;
static unsigned keys91[4]={0x1ac,0x1ab,0x30,0x1af};
static void p32(void*p,unsigned v){memcpy(p,&v,4);}static void p64(void*p,unsigned long v){memcpy(p,&v,8);}
static int alloc91(unsigned dst,void**out,unsigned n,unsigned wait){assert(dst==0x807a0020&&n==20&&wait==1);alloc_count++;*out=alloc_result&&!return_alloc_on_failure?0:messages91[alloc_index++];allocation91=*out;return alloc_result;}
static int free91(unsigned dst,void*p){assert(dst==0x807a0020&&p==allocation91);release_count++;return 0;}
static void setsrc91(void*p,unsigned src){assert(p==allocation91&&src==0x00410025);}
static int send91(unsigned dst,void*p){assert(dst==0x807a0020&&p==allocation91);unsigned w[5];memcpy(w,p,20);assert(w[1]==0&&w[3]==0&&w[4]==1);times91[send_count]=now91;send_count++;if(!send_result)for(unsigned i=0;i<4;i++)if(keys91[i]==w[0])p32(states91+i*44+8,w[2]);return send_result;}
static unsigned size_result91=20;static unsigned size91(void*p){assert(p);return size_result91;}static unsigned source91(void*p){assert(p);return 0x00410025;}
static int (*allocate)(unsigned,void**,unsigned,unsigned)=alloc91;static int(*release)(unsigned,void*)=free91;static void(*set_source)(void*,unsigned)=setsrc91;static int(*send_msg)(unsigned,void*)=send91;static unsigned(*msg_size)(void*)=size91,*(*unused91)(void*);static unsigned(*source)(void*)=source91;
static int*errno91(void){return &error91;}
static int printf91(int fd,const char*f,...){assert(fd==2);va_list ap;va_start(ap,f);int n=vprintf(f,ap);va_end(ap);return n;}
static unsigned long screen91(unsigned*last){*last=0x2c7;return opened91;}
static int receive_rc91;static int receive91(unsigned dst,void**out,long timeout){assert(dst==0x807a0020&&timeout==-1);*out=messages91[11];error91=9;return receive_rc91;}
static void*load91(const char*n,int flags){assert(!strcmp(n,"libObj.so")&&flags==5);return(void*)17;}
static void*dlsym91(void*h,const char*n){(void)h;if(!strcmp(n,"osal_rcv_msg_tmo"))return(void*)receive91;if(!strcmp(n,"dlopen"))return(void*)load91;if(!strcmp(n,"fx3_native_screen_open_snapshot"))return(void*)screen91;return 0;}
static int open91(const char*p,int flags,...){assert(!strcmp(p,"/proc/self/mem")&&flags==0);return 1;}
static long pread91(int fd,void*p,unsigned long n,long at){assert(fd==1);unsigned long a=(unsigned long)at;void*src=0;
 if(a>=0x1000000&&a+n<=0x1300000)src=obj_image91+a-0x1000000;
 else if(a>=0x2000000&&a+n<=0x2000080)src=instance91+a-0x2000000;
 else if(a>=0x3000000&&a+n<=0x30000c0)src=config91+a-0x3000000;
 else if(a>=0x4000000&&a+n<=0x40000b0)src=states91+a-0x4000000;
 assert(src);memcpy(p,src,n);return n;}
static long readlink91(const char*p,char*out,unsigned long n){assert(!strcmp(p,"/proc/self/exe"));const char*s="/usr/bin/im.elf";assert(strlen(s)<n);memcpy(out,s,strlen(s));return strlen(s);}
static char*getenv91(const char*n){assert(!strcmp(n,"FX3_SYNTH_KEYS"));return "ap91-script-v1";}
static int create91(void*p,const void*a,void*(*fn)(void*),void*b){(void)a;(void)fn;(void)b;start_count++;*(unsigned long*)p=3;return 0;}static int detach91(unsigned long p){assert(p==3);return 0;}
static int sleep91(unsigned us){now91+=(unsigned long)us*1000;return 0;}
static long syscall91(long n,...){(void)n;return 1;}
static void exit91(int n){(void)n;assert(0);abort();}
static int addr91(const void*p,struct cap_dl_info*i){(void)p;(void)i;return 0;}
#define __errno_location errno91
#define dprintf printf91
#define dlsym dlsym91
#define open open91
#define pread pread91
#define readlink readlink91
#define getenv getenv91
#define pthread_create create91
#define pthread_detach detach91
#define usleep sleep91
#define syscall syscall91
#define _exit exit91
#define dladdr addr91
#define clock_gettime clock91
#define dlinfo info91
struct sk_timespec;static int clock91(int,struct sk_timespec*);static int info91(void*,int,void*);
#include "fx3-synth-key-script-v1.inc"
static int clock91(int id,struct sk_timespec*t){assert(id==1);t->sec=now91/1000000000;t->nsec=now91%1000000000;return 0;}
static int info91(void*h,int req,void*out){assert(h==(void*)17&&req==2);static struct sk_link_map m;m.base=0x1000000;*(void**)out=&m;return 0;}
int main(void){
 unsigned char body[20];assert(!sk_pack(0x1ab,1,body));const unsigned char expected[20]={0xab,1,0,0,0,0,0,0,1,0,0,0,0,0,0,0,1,0,0,0};assert(!memcmp(body,expected,20));assert(sk_pack(0x99,1,body)&&sk_pack(0x1ab,2,body));
 obj_image91=calloc(1,0x300000);instance91=calloc(1,128);config91=calloc(4,48);states91=calloc(4,44);assert(obj_image91&&instance91&&config91&&states91);p64(obj_image91+0x2cde48,0x2000000);p64(instance91+0x20,0x3000000);p32(instance91+0x2c,4);p64(instance91+0x38,0x4000000);for(unsigned i=0;i<4;i++){p32(config91+i*48+8,keys91[i]);p32(states91+i*44+8,0x7fffffff);}
 error91=77;sk_start_once();sk_start_once();assert(start_count==1&&error91==77);sk_receiver_seen=1;sk_worker(0);assert(send_count==12&&alloc_count==12&&!release_count);for(unsigned i=0;i<12;i++){unsigned w[5];memcpy(w,messages91[i],20);assert(w[0]==sk_keys[i/2]&&w[2]==(i%2?0:1));if(i%2)assert(times91[i]-times91[i-1]>=100000000UL);else if(i)assert(times91[i]-times91[i-1]>=4000000000UL);}assert(times91[0]>=opened91+5000000000UL);
 unsigned val;assert(sk_cache(0x1ab,&val)&&val==0);p64(instance91+0x20,~0UL);assert(!sk_cache(0x1ab,&val));p64(instance91+0x20,0x3000000);
 send_result=-5;unsigned freed=release_count;assert(sk_native_send(1,0x1ab,1)==-5&&release_count==freed+1);send_result=0;alloc_result=-6;freed=release_count;assert(sk_native_send(1,0x1ab,1)==-1&&release_count==freed);return_alloc_on_failure=1;assert(sk_native_send(1,0x1ab,1)==-1&&release_count==freed+1);
 struct sk_script bad={0};assert(sk_arm(&bad,0));assert(sk_arm(&bad,~0UL-1));struct sk_script good={0};assert(!sk_arm(&good,1));unsigned step,key,status;assert(!sk_ready(&good,5000000000UL,&step,&key,&status));assert(sk_ready(&good,5000000001UL,&step,&key,&status)&&step==1&&key==0x1ac&&status==1);assert(sk_commit(&good,1));
 void*received=0;error91=77;receive_rc91=0;assert(!osal_rcv_msg_tmo(0x807a0020,&received,-1)&&received==messages91[11]&&error91==9);receive_rc91=-9;error91=77;assert(osal_rcv_msg_tmo(0x807a0020,&received,-1)==-9&&error91==9);
 unsigned internal[7]={0x1ab,0,1,0,1,17,0};size_result91=28;unsigned count_before=send_count;sk_observe_internal(0x007a804c,internal);assert(send_count==count_before);size_result91=20;
 free(obj_image91);free(instance91);free(config91);free(states91);puts("SYNTH_KEY91_PASS exact20B/6steps12events/5s_after_dialog/100ms_hold/4s_gap/allowedkeys/readonly_cache_bounds/no_GetInstance/original_allocownership/sendfailure_free/clock_overflow/startonce_sameim");return 0;
}
