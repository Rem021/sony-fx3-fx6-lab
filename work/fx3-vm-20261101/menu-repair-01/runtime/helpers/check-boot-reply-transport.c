#define FF_HOST_DIRECT 1
#define syscall fake_syscall
#define dladdr fake_dladdr
#include "fx3-capid-v31.c"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
static int test_errno;int *__errno_location(void){return &test_errno;}
static unsigned char request[1024],reply[1024];static struct cap_table table;
static unsigned int in_size=24,src=0x803061c0,free_count,send_count;static int alloc_rc,send_rc;static void *last_free;
#include <pthread.h>
#include <stdarg.h>
static pthread_mutex_t wait_mutex=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t wait_cond=PTHREAD_COND_INITIALIZER;
static unsigned int wait_calls,wake_calls;
static long test_pid=3;
long fake_syscall(long n,...){if(n!=98)return n==172?test_pid:7;
 va_list args;va_start(args,n);unsigned int *p=va_arg(args,unsigned int *);int op=va_arg(args,int);int val=va_arg(args,int);va_end(args);
 assert(op==128||op==129);assert(val==1);pthread_mutex_lock(&wait_mutex);
 if(op==128){wait_calls++;while(__atomic_load_n(p,__ATOMIC_ACQUIRE)==1)pthread_cond_wait(&wait_cond,&wait_mutex);}
 else{wake_calls++;pthread_cond_signal(&wait_cond);}
 pthread_mutex_unlock(&wait_mutex);return 0;}
static unsigned int protected_counter;
static void *contend(void *arg){(void)arg;for(int i=0;i<3000;i++){enter();unsigned int v=protected_counter;sched_yield();protected_counter=v+1;leave();}return 0;}

static int alloc(unsigned int id,void **p,unsigned int n,unsigned int wait){assert((id==src||id==0x0282078f)&&n<=80&&wait==1);*p=alloc_rc?0:reply;return alloc_rc;}
static int freemsg(unsigned int id,void *p){(void)id;free_count++;last_free=p;return 0;}
static int delegated_cp;static int sendmsg(unsigned int id,void *p){if(id==0x912503d0){assert(p==request);delegated_cp++;return 77;}assert((id==src||id==0x0282078f)&&p==reply);send_count++;return send_rc;}
static void setsrc(void *p,unsigned int id){assert(p==reply&&(id==0x9061003c||id==0x02820746||id==0x9004015e||id==0x92850750||id==0x00930101||id==0x92840747||id==0x909a015a||id==0x909c015b||id==0x90040193||id==0x9059000e));}
static unsigned int msize(void *p){assert(p==request||p==reply);return in_size;}
static unsigned int msource(void *p){assert(p==request);return src;}
static void reset(void){memset(request,0,sizeof request);memset(&table,0,sizeof table);memset(live,0,sizeof live);model=(struct cap_service){&table,0x41d800000ULL,0,0};initialized=enabled=1;process_owner=3;fault=0;in_size=24;src=0x803061c0;free_count=send_count=0;alloc_rc=send_rc=0;allocate=alloc;release=freemsg;send_msg=sendmsg;set_source=setsrc;msg_size=msize;source=msource;}
static void op(unsigned int x){memcpy(request+4,&x,4);}
static const char *caller_module="/usr/lib/libupdaterufp.so";
int fake_dladdr(const void *p,struct cap_dl_info *i){if(p==(void *)0x12342e1574cULL){i->file="/usr/lib/appFw.so";i->base=(void *)0x12340000000ULL;return 1;}i->file=caller_module;i->base=(void *)((unsigned long)p-0x1984);return 1;}

static void setup_tc(void){reset();model.initialized=1;in_size=52;memset(tc_live_request,0,sizeof tc_live_request);memset(tc_live_padding,0,sizeof tc_live_padding);memset(gf_live_request,0,sizeof gf_live_request);memcpy(request,tc_frozen,52);memcpy(request,&src,4);}
static void setup_gf(void){setup_tc();in_size=8;const unsigned char q[8]={13,32,37,3,8,0,1,128};memcpy(request,q,8);}
int main(void){
 setup_tc();assert(!timecode_dispatch(request,7)&&send_count==1&&free_count==1&&last_free==request&&live[0].p==reply&&tc_live_request[0]==request);const unsigned char expected[36]={0,0,0,0,160,160,160,160,1,0,36,0,24,0,0,0,36,0,0,0,0,0,0,0,1,32,5,18,12,0,1,0,0,0,0,0};assert(!memcmp(reply,expected,36));assert(timecode_dispatch(request,7)==-1021&&send_count==1&&free_count==1);assert(!osal_free_msg(src,reply)&&!live[0].p&&!tc_live_request[0]);
 for(int i=4;i<52;i++){if(i>=20&&i<24)continue;setup_tc();request[i]^=1;assert(timecode_dispatch(request,7)==-1024&&!send_count&&!free_count);}
 for(int i=0;i<60;i++){if(i==52)continue;setup_tc();in_size=i;assert(timecode_dispatch(request,7)==-1024&&!send_count&&!free_count);}
 for(int i=0;i<7;i++){setup_tc();assert(timecode_dispatch(request,i)==-1024&&!send_count&&!free_count);}
 setup_tc();src=0x81aa8123;memcpy(request,&src,4);memset(request+20,0xff,4);assert(!timecode_dispatch(request,7)&&tc_live_padding[0]==0xffffffffU&&!memcmp(reply,expected,36));assert(!osal_free_msg(src,reply));
 setup_tc();request[0]^=1;assert(timecode_dispatch(request,7)==-1024&&!send_count&&!free_count);setup_tc();src=0;memset(request,0,4);assert(timecode_dispatch(request,7)==-1024);setup_tc();src=0x90000001;memcpy(request,&src,4);assert(timecode_dispatch(request,7)==-1024);
 setup_tc();alloc_rc=-1022;assert(timecode_dispatch(request,7)==-1022&&!send_count&&!free_count&&!live[0].p);setup_tc();send_rc=-1020;assert(timecode_dispatch(request,7)==-1020&&send_count==1&&free_count==1&&last_free==reply&&!live[0].p&&!tc_live_request[0]);send_rc=0;assert(!timecode_dispatch(request,7)&&last_free==request);assert(!osal_free_msg(src,reply));
 setup_tc();for(int i=0;i<8;i++)live[i].p=(void *)(unsigned long)(i+1);assert(timecode_dispatch(request,7)==-1021&&!send_count&&!free_count);setup_tc();test_pid=4;assert(timecode_dispatch(request,7)==-1021);test_pid=3;
 setup_gf();assert(!get_func_dispatch(request)&&send_count==1&&free_count==1&&last_free==request&&gf_live_request[0]==request);unsigned char gf[28]={13,32,37,19,28,0,1,128,0,0,0,0};memset(gf+12,128,16);assert(!memcmp(reply,gf,28));assert(get_func_dispatch(request)==-1021&&send_count==1);assert(!osal_free_msg(src,reply)&&!live[0].p&&!gf_live_request[0]);
 for(int i=0;i<8;i++){setup_gf();request[i]^=1;assert(get_func_dispatch(request)==-1024&&!send_count&&!free_count);}setup_gf();in_size=9;assert(get_func_dispatch(request)==-1024);setup_gf();in_size=7;assert(get_func_dispatch(request)==-1024);
 setup_gf();send_rc=-1020;assert(get_func_dispatch(request)==-1020&&last_free==reply&&!live[0].p&&!gf_live_request[0]);setup_gf();alloc_rc=-1022;assert(get_func_dispatch(request)==-1022&&!send_count&&!free_count);setup_gf();src=0x90000001;assert(get_func_dispatch(request)==-1024);setup_gf();test_pid=4;assert(get_func_dispatch(request)==-1021);test_pid=3;
 pthread_t threads[8];protected_counter=0;for(int i=0;i<8;i++)assert(!pthread_create(threads+i,0,contend,0));for(int i=0;i<8;i++)assert(!pthread_join(threads[i],0));assert(protected_counter==24000);puts("AP78_BOOT_REPLY_PASS exact44B/replyid-source/padding/dynamicqueue/stackmask/replybytes/ownership/lease/dedup/rollback/allocfail/length/source/PID/325_80capabilities/8threads24000");return 0;
}
