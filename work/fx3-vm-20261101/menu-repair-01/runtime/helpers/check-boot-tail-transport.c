#define FF_HOST_DIRECT 1
#define syscall fake_syscall
#define dladdr fake_dladdr
#include "fx3-capid-v32.c"
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

static unsigned int backup_value;static int backup_known=1;static int fake_backup(unsigned int *out){*out=backup_value;return backup_known;}
static void setup_tail(void){setup_tc();memset(&panel165,0,sizeof panel165);memset(&hdmi_boot,0,sizeof hdmi_boot);memset(tail_live,0,sizeof tail_live);hdmi_tc.known=1;hdmi_tc.tc_output=0;backup_value=0;backup_known=1;backup_observed=fake_backup;setenv("FX3_DISPLAY_INFO","software-640x480-v1",1);setenv("FX3_HDMI_BOOT","disconnected-inactive-v1",1);}
static const unsigned char panq[10]={13,32,101,1,10,0,1,128,2,0},defq[12]={0,37,10,1,12,0,1,0,0,0,0,0},resq[16]={0,37,1,1,16,0,1,0,0,0,0,0,6,5,0,0};
static void prep(const unsigned char *q,unsigned int n){memcpy(request,q,n);in_size=n;}
static void rateq(unsigned int port,unsigned int rate){const unsigned char q[12]={0,37,23,1,12,0,1,0,port,rate,port,rate};prep(q,12);}
int main(void){
 setup_tail();prep(panq,10);assert(!tail_dispatch(0x92840747,request,0x165)&&panel165.shadow_valid&&panel165.pending_hardware&&panel165.selector==2&&!panel165.enumeration&&panel165.cache_valid&&!panel165.cache_enum&&last_free==request);const unsigned char expected[12]={13,32,101,17,12,0,1,128,0,0,89,0};assert(!memcmp(reply,expected,12));assert(tail_dispatch(0x92840747,request,0x165)==-1021&&send_count==1);assert(!osal_free_msg(src,reply)&&!tail_live[0].request);
 for(int i=0;i<10;i++){setup_tail();prep(panq,10);request[i]^=1;assert(tail_dispatch(0x92840747,request,0x165)==-1024&&!send_count&&!free_count&&!panel165.shadow_valid);}
 setup_tail();prep(panq,10);struct tail_panel before=panel165;send_rc=-1020;assert(tail_dispatch(0x92840747,request,0x165)==-1020&&!memcmp(&before,&panel165,sizeof before)&&last_free==reply&&!live[0].p&&!tail_live[0].request);setup_tail();prep(panq,10);alloc_rc=-1022;assert(tail_dispatch(0x92840747,request,0x165)==-1022&&!panel165.shadow_valid&&!send_count&&!free_count);setup_tail();prep(panq,10);setenv("FX3_DISPLAY_INFO","other",1);assert(tail_dispatch(0x92840747,request,0x165)==-1024);
 setup_tail();prep(defq,12);assert(!tail_dispatch(0x909a015a,request,0x10a)&&hdmi_boot.definition_known&&!hdmi_boot.definition&&reply[8]==1&&reply[3]==0x81&&reply[2]==10);assert(!osal_free_msg(src,reply));prep(resq,16);assert(!tail_dispatch(0x909a015a,request,0x101)&&hdmi_boot.resolution_known&&!memcmp(hdmi_boot.parameters,resq+8,8)&&reply[8]==0&&reply[2]==1);assert(!osal_free_msg(src,reply));
 for(unsigned int i=0;i<5;i++){const unsigned int rates[5]={0,0,17,17,0};rateq(i,rates[i]);assert(!tail_dispatch(0x909a015a,request,0x117)&&hdmi_boot.next_port==i+1&&hdmi_boot.rate_known[i]&&hdmi_boot.rate[i]==rates[i]&&reply[2]==23&&!reply[8]);unsigned int n=send_count;assert(tail_dispatch(0x909a015a,request,0x117)<0&&send_count==n);assert(!osal_free_msg(src,reply));}
 rateq(4,0);assert(tail_dispatch(0x909a015a,request,0x117)==-1024);
 setup_tail();backup_value=7;for(unsigned int i=0;i<5;i++){rateq(i,7);assert(!tail_dispatch(0x909a015a,request,0x117)&&hdmi_boot.rate[i]==7);assert(!osal_free_msg(src,reply));}
 setup_tail();rateq(1,0);assert(tail_dispatch(0x909a015a,request,0x117)==-1024);setup_tail();rateq(0,17);assert(tail_dispatch(0x909a015a,request,0x117)==-1024);setup_tail();rateq(0,7);assert(tail_dispatch(0x909a015a,request,0x117)==-1024);backup_value=7;rateq(0,0);assert(tail_dispatch(0x909a015a,request,0x117)==-1024);setup_tail();backup_known=0;rateq(0,0);assert(tail_dispatch(0x909a015a,request,0x117)==-1024);setup_tail();rateq(0,0);request[10]=1;assert(tail_dispatch(0x909a015a,request,0x117)==-1024);
 for(int kind=0;kind<3;kind++){const unsigned char *q=kind==0?defq:kind==1?resq:0;unsigned int size=kind==0?12:kind==1?16:12,cmd=kind==0?0x10a:kind==1?0x101:0x117;for(unsigned int i=0;i<size;i++){setup_tail();if(q)prep(q,size);else rateq(0,0);request[i]^=0x80;assert(tail_dispatch(0x909a015a,request,cmd)==-1024&&!send_count&&!free_count);}setup_tail();if(q)prep(q,size);else rateq(0,0);struct tail_hdmi prior=hdmi_boot;send_rc=-1020;assert(tail_dispatch(0x909a015a,request,cmd)==-1020&&!memcmp(&prior,&hdmi_boot,sizeof prior)&&last_free==reply&&!tail_live[0].request);send_rc=0;assert(!tail_dispatch(0x909a015a,request,cmd));assert(!osal_free_msg(src,reply));}
 setup_tail();prep(defq,12);hdmi_tc.tc_output=1;assert(tail_dispatch(0x909a015a,request,0x10a)==-1024);setup_tail();prep(defq,12);src=0x90000001;assert(tail_dispatch(0x909a015a,request,0x10a)==-1024);setup_tail();prep(defq,12);test_pid=4;assert(tail_dispatch(0x909a015a,request,0x10a)==-1021);test_pid=3;
 setup_gf();assert(!get_func_dispatch(request)&&reply[12]==128&&reply[27]==128);assert(!osal_free_msg(src,reply));setup_tc();assert(!timecode_dispatch(request,7));assert(!osal_free_msg(src,reply));
 pthread_t threads[8];protected_counter=0;for(int i=0;i<8;i++)assert(!pthread_create(threads+i,0,contend,0));for(int i=0;i<8;i++)assert(!pthread_join(threads[i],0));assert(protected_counter==24000);puts("AP79_TAIL_PASS panel590000/shadow-cache/rollback/lease, HDMI010a_status1/0101_exact/0117_ordered5/static_and_backup7, rejectbytes/backupunknown/rate/reorder/replay/source/PID/active, prior325_and_timecode,8threads24000");return 0;}
