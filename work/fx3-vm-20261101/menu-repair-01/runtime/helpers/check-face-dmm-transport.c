#define FF_HOST_DIRECT 1
#define syscall fake_syscall
#define dladdr fake_dladdr
#define open fake_face_open
#define close fake_face_close
#define mmap fake_face_mmap
#define munmap fake_face_munmap
#include "fx3-capid-v38.c"
#undef open
#undef close
#undef mmap
#undef munmap
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

static const unsigned char golden[3][3][40]={{{0x20,0x80,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x8,0x84,0x0,0x0,0xd9,0x1,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0},{0x2a,0x80,0x0,0x0,0x0,0x0,0x0,0x0,0x1,0x0,0x0,0x0,0x8,0x84,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0xd0,0x1d,0x0,0x0,0x0,0x0,0x0,0x40,0x6,0x0,0x0,0x0,0x0,0x0},{0x23,0x80,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x8,0x84,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0}},{{0x20,0x80,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x9,0x84,0x0,0x0,0xda,0x1,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0},{0x2a,0x80,0x0,0x0,0x0,0x0,0x0,0x0,0x1,0x0,0x0,0x0,0x9,0x84,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0xd7,0x1d,0x0,0x0,0x0,0x0,0x0,0xc8,0x0,0x0,0x0,0x0,0x0,0x0},{0x23,0x80,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x9,0x84,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0}},{{0x20,0x80,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0xa,0x84,0x0,0x0,0xdb,0x1,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0},{0x2a,0x80,0x0,0x0,0x0,0x0,0x0,0x0,0x1,0x0,0x0,0x0,0xa,0x84,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0xd8,0x1d,0x0,0x0,0x0,0x0,0x0,0xd1,0x0,0x0,0x0,0x0,0x0,0x0},{0x23,0x80,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0xa,0x84,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0}}};

static unsigned char fr_backing[FR_SIZE],local_bytes[FR_MAX];static int map_fail,unmap_fail;
int fake_face_open(const char *name,int flags,...){(void)flags;return !strcmp(name,"/dev/mem")?99:-1;}int fake_face_close(int fd){assert(fd==99);return 0;}
void *fake_face_mmap(void *a,size_t n,int prot,int flags,int fd,long off){assert(!a&&n<=FR_MAX&&prot==1&&flags==1&&fd==99&&off==0x410000000UL);return map_fail?(void *)-1:local_bytes;}int fake_face_munmap(void *p,size_t n){assert(p==local_bytes&&n<=FR_MAX);return unmap_fail;}
static void face_setup(void){reset();model.initialized=1;memset(&face_model,0,sizeof face_model);face_model.memory=fr_backing;memset(fr_backing,0xaa,sizeof fr_backing);memset(fr_dmm_lease,0,sizeof fr_dmm_lease);memset(fr_icdt_pending,0,sizeof fr_icdt_pending);memset(face_locals,0,sizeof face_locals);memset(local_bytes,0,sizeof local_bytes);map_fail=unmap_fail=0;in_size=40;}
static void allocq(unsigned unit,unsigned option){memset(request,0,40);ff_put(request,0x20,2);ff_put(request+4,unit,4);ff_put(request+12,0xffffffff,4);ff_put(request+22,option,2);in_size=40;}
static void handleq(unsigned op,unsigned handle,unsigned option){memset(request,0,40);ff_put(request,op,2);ff_put(request+8,handle,4);ff_put(request+22,option,2);in_size=40;}
static unsigned long pairs[2],cbctx[2];static unsigned source_pair[2],dest_pair[2];
static void transferq(unsigned h,unsigned length){memset(request,0,48);source_pair[0]=0x0401;source_pair[1]=0;dest_pair[0]=h;dest_pair[1]=0;pairs[0]=(unsigned long)source_pair;pairs[1]=(unsigned long)dest_pair;memcpy(request,pairs,16);ff_put(request+16,length,4);ff_put(request+20,1,4);unsigned long cb=0x12342e1574cULL,context=(unsigned long)cbctx;memcpy(request+24,&cb,8);memcpy(request+32,&context,8);ff_put(request+40,17,4);in_size=48;}
int main(void){face_setup();for(unsigned i=0;i<3;i++){allocq(fr_units[i],0);assert(!fr_dispatch(request)&&face_model.slots[i].allocated&&!face_model.slots[i].opens&&!memcmp(reply,golden[i][0],40)&&face_model.slots[i].handle==(0x8408U+i)&&!ff_get(reply+8,2)&&!ff_get(reply+32,4));assert(!osal_free_msg(src,reply));handleq(0x2a,0x8408+i,0);assert(!fr_dispatch(request)&&ff_get(reply+8,2)==1&&ff_get(reply+32,4)==fr_cap[i]&&!memcmp(reply,golden[i][1],40));unsigned long long cp;memcpy(&cp,reply+24,8);assert(cp==fr_cp(i));assert(!osal_free_msg(src,reply));}
 for(unsigned i=0;i<3;i++){handleq(0x23,0x8408+i,0);assert(!fr_dispatch(request)&&!face_model.slots[i].allocated&&!memcmp(reply,golden[i][2],40));assert(!osal_free_msg(src,reply));assert(fr_reply(request,reply)==-1024);allocq(fr_units[i],0);assert(!fr_reply(request,reply)&&face_model.slots[i].handle==(0x8808U+i));handleq(0x2a,0x8408+i,0);assert(fr_reply(request,reply)==-1024);}
 face_setup();allocq(0x1d9,0);struct fr_model before=face_model;unsigned char mem_before[FR_SIZE];memcpy(mem_before,fr_backing,FR_SIZE);send_rc=-1020;assert(fr_dispatch(request)==-1020&&!memcmp(&face_model,&before,sizeof before)&&!memcmp(fr_backing,mem_before,FR_SIZE)&&last_free==reply);send_rc=0;assert(!fr_dispatch(request));assert(!osal_free_msg(src,reply));handleq(0x21,0x8408,0);assert(!fr_reply(request,reply)&&face_model.slots[0].opens==1);handleq(0x23,0x8408,0);assert(fr_reply(request,reply)==-1024&&face_model.slots[0].allocated);handleq(0x22,0x8408,0);assert(!fr_reply(request,reply)&&!face_model.slots[0].opens);handleq(0x23,0x8408,2);assert(fr_reply(request,reply)==-1024);handleq(0x23,0x8408,0);assert(!fr_reply(request,reply));
 for(unsigned unit_i=0;unit_i<3;unit_i++){face_setup();allocq(fr_units[unit_i],0);assert(!fr_reply(request,reply));face_locals[0]=(struct fr_local){0x0401,fr_units[unit_i],fr_cap[unit_i],1,0x410000000ULL};for(unsigned n=0;n<fr_cap[unit_i];n++)local_bytes[n]=(unsigned char)(n*73+unit_i+19);transferq(0x8408+unit_i,fr_cap[unit_i]);setenv("FX3_ADF_FILE","muted-user-v1",1);assert(!osal_snd_sync_msg(0x02820746,request)&&face_model.slots[unit_i].pending&&!memcmp(fr_backing+fr_offset[unit_i],local_bytes,fr_cap[unit_i]));assert(fr_icdt(request)==-1024&&send_count==1);assert(!osal_free_msg(0x0282078f,reply)&&!face_model.slots[unit_i].pending);source_pair[0]=0x0801;assert(fr_icdt(request)==-1024);source_pair[0]=0x0401;dest_pair[1]=fr_cap[unit_i];assert(fr_icdt(request)==-1024);dest_pair[1]=0;source_pair[1]=1;assert(fr_icdt(request)==-1024);source_pair[1]=0;ff_put(request+16,fr_cap[unit_i]+1,4);assert(fr_icdt(request)==-1024);ff_put(request+16,fr_cap[unit_i],4);ff_put(request+40,17,4);send_rc=-1020;memset(fr_backing+fr_offset[unit_i],0x67,fr_cap[unit_i]);assert(fr_icdt(request)==-1020&&!face_model.slots[unit_i].pending&&ff_get(request+40,4)==17);for(unsigned n=0;n<fr_cap[unit_i];n++)assert(fr_backing[fr_offset[unit_i]+n]==0x67);send_rc=0;map_fail=1;assert(fr_icdt(request)==-1021);map_fail=0;unmap_fail=1;assert(fr_icdt(request)==-1021);unmap_fail=0;}
 face_setup();unsigned char native[40]={0};ff_put(native,0x8020,2);ff_put(native+12,0x401,4);ff_put(native+16,0x1d9,4);fr_capture_local(native);assert(face_locals[0].live&&!face_locals[0].physical);ff_put(native,0x802a,2);ff_put(native+8,1,2);unsigned long long phys=0x410000000ULL;memcpy(native+24,&phys,8);ff_put(native+32,0x64000,4);fr_capture_local(native);assert(face_locals[0].physical==phys&&face_locals[0].capacity==0x64000);ff_put(native,0x8023,2);fr_capture_local(native);assert(!face_locals[0].live);
 puts("AP83_FACE_PASS three_exact_alloc_only/geometry/handle_generation/stale/wrongdomain/doublefree/open_close/free0/send_rollback/native_local_capture/ICDT_each_byte_equal/all3_units/bounds/mapfail/sendfail_restore/no_muted_substitution");}
