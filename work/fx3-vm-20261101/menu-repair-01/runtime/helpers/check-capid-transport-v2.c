#define syscall fake_syscall
#include "fx3-capid-v2.c"
#include <assert.h>
#include <stdio.h>
static int test_errno;int *__errno_location(void){return &test_errno;}
static unsigned char request[40],reply[32];static struct cap_table table;
static unsigned int in_size=24,src=0x803061c0,free_count,send_count;static int alloc_rc,send_rc;static void *last_free;
static long test_pid=3;long fake_syscall(long n,...){return n==172?test_pid:7;}
static int alloc(unsigned int id,void **p,unsigned int n,unsigned int wait){assert(id==src&&n<=24&&wait==1);*p=alloc_rc?0:reply;return alloc_rc;}
static int freemsg(unsigned int id,void *p){(void)id;free_count++;last_free=p;return 0;}
static int sendmsg(unsigned int id,void *p){assert(id==src&&p==reply);send_count++;return send_rc;}
static void setsrc(void *p,unsigned int id){assert(p==reply&&(id==0x9004015e||id==0x92850750));}
static unsigned int msize(void *p){assert(p==request);return in_size;}
static unsigned int msource(void *p){assert(p==request);return src;}
static void reset(void){memset(request,0,sizeof request);memset(&table,0,sizeof table);memset(live,0,sizeof live);model=(struct cap_service){&table,0x41d800000ULL,0,0};initialized=enabled=1;process_owner=3;fault=0;in_size=24;src=0x803061c0;free_count=send_count=0;alloc_rc=send_rc=0;allocate=alloc;release=freemsg;send_msg=sendmsg;set_source=setsrc;msg_size=msize;source=msource;}
static void op(unsigned int x){memcpy(request+4,&x,4);}
int main(void){
 reset();op(0x1000);assert(osal_snd_msg(0x9004015e,request)==0&&last_free==request&&live[0].p==reply);assert(reply[0]==1&&reply[5]==0x10);assert(osal_free_msg(src,reply)==0&&!live[0].p);
 reset();op(0x1001);send_rc=-1020;assert(osal_snd_msg(0x9004015e,request)==-1020&&!model.access_owner&&!live[0].p&&last_free==reply&&free_count==1);
 reset();op(0x1001);alloc_rc=-1022;assert(osal_snd_msg(0x9004015e,request)==-1022&&!send_count&&!free_count&&!model.access_owner);
 reset();op(0x1001);assert(!osal_snd_msg(0x9004015e,request)&&model.access_owner==7);assert(!osal_free_msg(src,reply));op(0x1002);assert(!osal_snd_msg(0x9004015e,request)&&!model.access_owner);assert(!osal_free_msg(src,reply));
 reset();op(0x1003);table.header[0]=1024;assert(!osal_snd_msg(0x9004015e,request)&&model.initialized&&!send_count&&free_count==1);
 reset();op(0x1003);assert(osal_snd_msg(0x9004015e,request)==-1024&&!free_count&&!send_count);
 reset();op(0x1000);request[8]=1;assert(osal_snd_msg(0x9004015e,request)==-1024&&!free_count&&!send_count);
 reset();in_size=36;unsigned long long addr=model.address;memcpy(request,&addr,8);unsigned int x=1;memcpy(request+8,&x,4);x=1024;memcpy(request+16,&x,4);send_rc=-1020;assert(osal_snd_msg(0x92850750,request)==-1020&&table.header[0]==0&&last_free==reply);send_rc=0;assert(!osal_snd_msg(0x92850750,request)&&table.header[0]==1024);assert(!osal_free_msg(src,reply));
 reset();op(0x1000);assert(!osal_snd_msg(0x9004015e,request));unsigned int before_free=free_count;test_pid=4;assert(osal_free_msg(src,reply)==-1021&&free_count==before_free&&live[0].p==reply);test_pid=3;assert(!osal_free_msg(src,reply));
 puts("CAPID_TRANSPORT_TEST_PASS: original request ownership, lease free, state rollback, no-reply, envelope and allocation failure");
}
