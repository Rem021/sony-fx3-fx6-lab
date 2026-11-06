#define dlsym fake_dlsym
#define FF_HOST_DIRECT 1
#define syscall fake_syscall
#define dladdr fake_dladdr
#include "fx3-capid-v44.c"
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
static long test_pid=3;static long test_tid=7;
long fake_syscall(long n,...){if(n!=98)return n==172?test_pid:test_tid;
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
static void setsrc(void *p,unsigned int id){assert(p==reply&&(id==0x9061003c||id==0x02820746||id==0x9004015e||id==0x92850750||id==0x00930101||id==0x92840747||id==0x909a015a||id==0x909c015b||id==0x90040193||id==0x9059000e||pg_owner(id)));}
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


static unsigned long context[7]={0x10000,7,1,0,0,0,0};static int context_valid=1;
static int ctx(unsigned long *out,unsigned n){if(!context_valid||n<7)return 0;memcpy(out,context,sizeof context);return 7;}
void *fake_dlsym(void *h,const char *name){(void)h;if(!strcmp(name,"fx3_timecode_preset_context"))return (void *)ctx;return 0;}
static const unsigned char run_wire[10]={13,32,2,4,10,0,1,128,0,0},run_gold[12]={13,32,2,20,12,0,1,128,0,0,0,0},preset_wire[12]={13,32,4,4,12,0,1,128,0,0,0,0},preset_gold[12]={13,32,4,20,12,0,1,128,0,0,0,0};
static void setup(int preset){reset();model.initialized=1;in_size=preset?12:10;memcpy(request,preset?preset_wire:run_wire,in_size);memset(sys_uud,0,sizeof sys_uud);memset(sys_uud_request,0,sizeof sys_uud_request);memset(sys_uud_kind,0,sizeof sys_uud_kind);memset(sys_uud_source,0,sizeof sys_uud_source);memset(context,0,sizeof context);context[0]=0x10000;context[1]=7;context[2]=1;context_valid=1;setenv("FX3_SYS_UUD","audited-run-preset-v1",1);}
int main(void){setup(0);assert(!osal_snd_msg(0x92840747,request)&&!memcmp(reply,run_gold,12)&&!memcmp(request,run_wire,10)&&!free_count&&sys_uud[0].accepted&&sys_uud[0].pending_counter_backend&&sys_uud[0].generation==1);assert(sys_uud_dispatch(request,0x402)==-1021&&send_count==1);assert(!osal_free_msg(src,reply)&&free_count==1&&!sys_uud_request[0]);for(unsigned j=0;j<10;j++){setup(0);request[j]^=1;assert(sys_uud_dispatch(request,0x402)==-1024&&!send_count&&!sys_uud[0].accepted);}setup(0);in_size=9;assert(sys_uud_dispatch(request,0x402)==-1024);in_size=11;assert(sys_uud_dispatch(request,0x402)==-1024);
 setup(1);assert(!sys_uud_dispatch(request,0x404)&&!memcmp(reply,preset_gold,12)&&!memcmp(request,preset_wire,12)&&!free_count&&sys_uud[1].accepted);assert(!osal_free_msg(src,reply));for(unsigned j=0;j<8;j++){setup(1);request[j]^=1;assert(sys_uud_dispatch(request,0x404)==-1024&&!send_count);}for(unsigned j=0;j<4;j++){setup(1);request[8+j]=1;assert(sys_uud_dispatch(request,0x404)==-1024&&!send_count);}
 setup(1);context[3]=0x1ff;context[4]=128;context[5]=0x103;request[8]=255;request[9]=128;request[10]=3;unsigned char before[12];memcpy(before,request,12);assert(!sys_uud_dispatch(request,0x404)&&!memcmp(reply,preset_gold,12)&&!memcmp(request,before,12)&&sys_uud[1].desired[0]==255&&sys_uud[1].desired[1]==128&&sys_uud[1].desired[2]==3);assert(!osal_free_msg(src,reply));setup(1);context_valid=0;assert(sys_uud_dispatch(request,0x404)==-1024&&!send_count);setup(1);context[1]=8;assert(sys_uud_dispatch(request,0x404)==-1024&&!send_count);setup(1);context[2]=0;assert(sys_uud_dispatch(request,0x404)==-1024&&!send_count);setup(1);in_size=13;assert(sys_uud_dispatch(request,0x404)==-1024&&!send_count);
 for(unsigned k=0;k<2;k++){setup(k);unsigned command=k?0x404:0x402;src=0;assert(sys_uud_dispatch(request,command)==-1024&&!send_count);setup(k);send_rc=-1020;assert(sys_uud_dispatch(request,command)==-1020&&!sys_uud[k].accepted&&!sys_uud[k].generation&&!sys_uud_request[0]&&last_free==reply);setup(k);alloc_rc=-1021;assert(sys_uud_dispatch(request,command)==-1021&&!send_count&&!sys_uud[k].accepted);}
 puts("SYS_UUD_PASS actual_capid44/exact402/complete404_header_and_all4_task_low8_fields/thread_epoch_rejection/no_range_invention/independent12B_bare0/source_duplicate/nativefree/allocation_send_rollback/original_caller_owned");}
