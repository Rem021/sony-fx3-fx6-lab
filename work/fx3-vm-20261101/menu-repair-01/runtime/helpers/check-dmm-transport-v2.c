#define syscall fake_syscall
#define dladdr fake_dladdr
#include "fx3-capid-v9.c"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
static int test_errno;int *__errno_location(void){return &test_errno;}
static unsigned char q[40],r[40],memory[DMM_TEST_SIZE];static struct cap_table table;
static unsigned int src=0x81cf6186,sends,frees;static void *last_free;static int alloc_rc,send_rc;static long test_pid=3;
long fake_syscall(long n,...){return n==172?test_pid:7;}
int fake_dladdr(const void *p,struct cap_dl_info *i){(void)p;(void)i;return 0;}
static int alloc(unsigned int id,void **p,unsigned int n,unsigned int w){assert(id==src&&n==40&&w==1);*p=alloc_rc?0:r;return alloc_rc;}
static int freemsg(unsigned int id,void *p){(void)id;frees++;last_free=p;return 0;}
static int sendmsg(unsigned int id,void *p){assert(id==src&&p==r);sends++;return send_rc;}
static void setsrc(void *p,unsigned int id){assert(p==r&&id==0x9061003c);}
static unsigned int msize(void *p){assert(p==q);return 40;}
static unsigned int msource(void *p){assert(p==q);return src;}
static void op(unsigned int x,unsigned int h,unsigned int option){memset(q,0,40);put(q,x,2);put(q+4,0x63a,4);put(q+8,h,4);put(q+12,0xffffffff,4);put(q+22,option,2);}
int main(void){initialized=enabled=1;process_owner=3;model=(struct cap_service){.table=&table,.address=0x41d800000ULL,.initialized=1};allocate=alloc;release=freemsg;send_msg=sendmsg;set_source=setsrc;msg_size=msize;source=msource;remote_dmm=(struct dmm_service){.memory=memory,.physical=DMM_TEST_PHYSICAL};setenv("FX3_REMOTE_DMM","two-slot-storage-v1",1);
 op(0x20,0,1);assert(!osal_snd_msg(0x9061003c,q)&&get(r+12,4)==0x8400&&get(r+24,4)==0x1d900000&&get(r+32,4)==0x80000&&last_free==q);assert(!osal_free_msg(src,r));
 memory[0]=0x44;struct dmm_service before=remote_dmm;send_rc=-1020;assert(dmm_dispatch(q)==-1020&&!memcmp(&before,&remote_dmm,sizeof before)&&memory[0]==0x44&&last_free==r&&!live[0].p);send_rc=0;alloc_rc=-1022;unsigned int free_before=frees;assert(dmm_dispatch(q)==-1022&&frees==free_before&&!memcmp(&before,&remote_dmm,sizeof before));alloc_rc=0;
 assert(!dmm_dispatch(q)&&get(r+12,4)==0x8401);assert(!osal_free_msg(src,r));assert(!dmm_dispatch(q)&&(short)get(r+2,2)==-1);assert(!osal_free_msg(src,r));
 op(0x2a,0x8400,0);assert(!dmm_dispatch(q)&&get(r+8,2)==1&&get(r+24,4)==0x1d900000);assert(!osal_free_msg(src,r));
 op(0x21,0x8400,0);assert(!dmm_dispatch(q)&&remote_dmm.slots[0].open_count==2);assert(!osal_free_msg(src,r));op(0x22,0x8400,0);assert(!dmm_dispatch(q)&&remote_dmm.slots[0].open_count==1);assert(!osal_free_msg(src,r));op(0x23,0x8400,2);assert(!dmm_dispatch(q)&&!remote_dmm.slots[0].allocated);assert(!osal_free_msg(src,r));op(0x20,0,1);assert(!dmm_dispatch(q)&&get(r+12,4)==0x8800&&!memory[0]);assert(!osal_free_msg(src,r));
 op(0x21,0x8400,0);assert(!dmm_dispatch(q)&&(short)get(r+2,2)==-5);assert(!osal_free_msg(src,r));test_pid=4;free_before=frees;assert(dmm_dispatch(q)==-1021&&frees==free_before);test_pid=3;src=1;assert(dmm_dispatch(q)==-1024);src=0x81cf6186;op(0x28,0,0);assert(dmm_dispatch(q)==-1024);
 puts("FX3_DMM_TRANSPORT_TEST_PASS: storage, generations, stalehandles, open/close/free, exhaustion, rollback, allocationfailure, originalownership, PID");}
