/* Candidate collector and formatter, actual host pthread/fork. No native firmware.
 * Foreign-TGID shared-BSS cases are injected models, not guest raw clone tests. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <sys/syscall.h>
#include <sys/wait.h>
#include <pthread.h>
#include <time.h>
#include <stdint.h>
#include <stdarg.h>
#include <assert.h>
typedef unsigned long U;
static _Thread_local unsigned fake_pid,pid_queries;
static unsigned resolutions,clock_calls;static U test_magic=0x32474e495244534fUL;
static long host_tgid(long n,...){assert(n==172);pid_queries++;errno=909;return fake_pid?fake_pid:syscall(SYS_getpid);}
static U timing_ns(void){struct timespec t;clock_calls++;clock_gettime(CLOCK_MONOTONIC,&t);return (U)t.tv_sec*1000000000UL+t.tv_nsec;}
static U now(void){return timing_ns();}
static int *host_errno(void){return &errno;}
struct r35_packet;static void *host_resolve(void*,const char*);
#define syscall host_tgid
#define __errno_location host_errno
#define dlsym host_resolve
#define R35_HOST_MANUAL_INIT 1
#include "r35-collector.inc"
#include "r35-log.inc"
#undef syscall
static void *host_resolve(void*h,const char*n){assert(!strcmp(n,"fx3_r35_snapshot_v1"));resolutions++;return (void*)fx3_r35_snapshot_v1;}
static void reset(void){fake_pid=0;r35_lock=r35_owner=r35_loss=0;memset(&r35_record,0,sizeof r35_record);r35_log_lock=r35_ui_pid=r35_seen=r35_logs=r35_bytes=0;r35_ui_instance=0;r35_exporter=0;errno=37;r35_init();r35_ui_init();assert(errno==37);}
struct state {struct r35_packet record;U ui_instance;uintptr_t exporter;unsigned lock,owner,loss,log_lock,pid,seen,logs,bytes;};
static struct state state(void){struct state s={0};s.record=r35_record;s.ui_instance=r35_ui_instance;s.exporter=(uintptr_t)r35_exporter;s.lock=r35_lock;s.owner=r35_owner;s.loss=r35_loss;s.log_lock=r35_log_lock;s.pid=r35_ui_pid;s.seen=r35_seen;s.logs=r35_logs;s.bytes=r35_bytes;return s;}
static void reject_all(void){struct state a=state(),b;struct r35_packet p,q;memset(&p,0xa5,sizeof p);q=p;char text[185];errno=37;
 assert(r35_pub_begin(0x1003)==0);r35_pub_end(1,-12);assert(r35_bind_begin()==0);r35_bind_end(1,0,3,&test_magic);assert(fx3_r35_snapshot_v1(R35_ABI,&p)==3);assert(!memcmp(&p,&q,sizeof p));r35_suffix(text);assert(!text[0]);assert(errno==37);b=state();assert(!memcmp(&a,&b,sizeof a));
}
static void *foreign_thread(void*x){fake_pid=(unsigned)(uintptr_t)x;reject_all();return 0;}
static void *own_thread(void*x){assert((unsigned)host_tgid(172)==r35_owner);unsigned t=r35_pub_begin(0x1003);r35_pub_end(t,-7);struct r35_packet p;int rc=fx3_r35_snapshot_v1(R35_ABI,&p);assert(rc==1||rc==2);return 0;}
static void emit(void){char out[185];unsigned n=pid_queries,cl=clock_calls,ds=resolutions;errno=37;r35_suffix(out);assert(errno==37&&pid_queries-n<=2&&clock_calls==cl&&resolutions==ds);assert(strlen(out)==184);printf("FX3_UI_GATE_SAMPLE id=9 n=1 tid=%u pc=0x16f1a74 object=0x1 a18=3 a12=0 a13=0 r0=0 decision_a18=0 elapsed=0 old_time=0 new_time=0 message=0 type=0 source=0 observed_only=1%s\n",r35_ui_pid,out);}
int main(int argc,char**argv){
 reset();struct r35_packet p;unsigned initpid=r35_owner;assert(initpid==(unsigned)getpid());
 /* All entry points reject a different real/injected TGID before any state write. */
 struct state initial=state();fake_pid=initpid+999;reject_all();fake_pid=0;
 r35_lock=r35_log_lock=1;fake_pid=initpid+999;reject_all();fake_pid=0;r35_lock=r35_log_lock=0;
 pthread_t t;pthread_create(&t,0,foreign_thread,(void*)(uintptr_t)(initpid+777));pthread_join(t,0);
 struct state after=state();assert(!memcmp(&initial,&after,sizeof initial));
 pid_t child=fork();assert(child>=0);if(!child){reject_all();_exit(0);}int status;waitpid(child,&status,0);assert(WIFEXITED(status)&&!WEXITSTATUS(status));after=state();assert(!memcmp(&initial,&after,sizeof initial));
 fprintf(stderr,"PASS injected_shared_BSS_foreign_TGID_all_points_and_actual_host_fork\n");
 /* Pre-constructor coverage unknown: no pretend early-event zero or loss record. */
 reset();r35_owner=0;initial=state();assert(!r35_pub_begin(0x1003));r35_pub_end(1,3);assert(!r35_bind_begin());r35_bind_end(1,0,3,&test_magic);assert(!fx3_r35_snapshot_v1(R35_ABI,&p));after=state();assert(!memcmp(&initial,&after,sizeof initial));
 fprintf(stderr,"PASS early_uninitialized_unknown_no_mutation\n");
 reset();unsigned token=r35_pub_begin(0x1003);assert(token==1);assert(!r35_pub_begin(0x1005));r35_pub_end(0,8);assert(r35_record.w[6]==1);r35_pub_end(token,-5);assert((int)r35_record.w[8]==-5);assert(!r35_pub_begin(0x1005));assert(r35_record.w[7]==0x1003);r35_pub_end(token,0);assert(r35_loss);
 reset();token=r35_pub_begin(0x1003);r35_lock=1;r35_pub_end(token,0);assert(r35_loss&&r35_record.w[6]==1);assert(fx3_r35_snapshot_v1(R35_ABI,&p)==2);r35_lock=0;assert(fx3_r35_snapshot_v1(R35_ABI,&p)==1&&p.w[6]==1);assert(fx3_r35_snapshot_v1(R35_ABI+1,&p)==-1);
 fprintf(stderr,"PASS first_capture_not_all_events_recursion_return_loss_contention_ABI\n");
 reset();pthread_t threads[16];for(unsigned i=0;i<16;i++)pthread_create(&threads[i],0,own_thread,0);for(unsigned i=0;i<16;i++)pthread_join(threads[i],0);assert(r35_record.w[6]&&(r35_record.w[6]==1||r35_record.w[8]==(unsigned)-7));
 fprintf(stderr,"PASS actual_host_same_TGID_multithread_bounded_claim\n");
 /* Actual suffix: all seven distinct categories, never consume all quota before events. */
 reset();r35_owner=0;emit();r35_init();emit();token=r35_pub_begin(0x1003);emit();r35_pub_end(token,0);emit();token=r35_bind_begin();emit();r35_bind_end(token,0,3,&test_magic);emit();r35_lost();emit();assert(r35_logs==7&&r35_bytes==1288);
 initial=state();for(unsigned i=0;i<10000;i++){char out[185];r35_suffix(out);assert(!out[0]);}after=state();assert(!memcmp(&initial,&after,sizeof initial));r35_init();r35_ui_init();after=state();assert(!memcmp(&initial,&after,sizeof initial));
 fake_pid=initpid+1;reject_all();fake_pid=0;
 fprintf(stderr,"PASS seven_suffixes_184_each_1288_total_no_reset_no_more_export\n");
 /* All six order-preserving interleavings of publication entry/return and
  * bind entry/return: every independent advance remains exportable. */
 const unsigned orders[6][4]={{0,1,2,3},{0,2,1,3},{0,2,3,1},{2,3,0,1},{2,0,3,1},{2,0,1,3}};
 for(unsigned order=0;order<6;order++){
  reset();unsigned pt=0,bt=0;char text[185];
  for(unsigned step=0;step<4;step++){
   switch(orders[order][step]){case 0:pt=r35_pub_begin(0x1003);break;case 1:r35_pub_end(pt,0);break;case 2:bt=r35_bind_begin();break;case 3:r35_bind_end(bt,0,3,&test_magic);break;}
   r35_suffix(text);assert(strlen(text)==184&&r35_logs==step+1);
  }
  assert(r35_record.w[6]==2&&r35_record.w[9]==2&&r35_bytes==736);r35_suffix(text);assert(!text[0]);
 }
 fprintf(stderr,"PASS all_six_phase_interleavings_bind_first_publication_not_masked\n");
 /* Missing exporter stays unknown and consumes only one early diagnostic category. */
 reset();r35_exporter=0;emit();for(unsigned i=0;i<100;i++){char out[185];r35_suffix(out);assert(!out[0]);}assert(r35_logs==1&&r35_bytes==184);
 fprintf(stderr,"PASS unbound_exporter_no_fallback_IO\n");
 reset();r35_bytes=~0U;char out[185];r35_suffix(out);assert(!out[0]&&!r35_logs&&r35_bytes==~0U);r35_bytes=0;r35_logs=~0U;r35_suffix(out);assert(!out[0]&&r35_logs==~0U);fprintf(stderr,"PASS corrupt_budget_counter_no_wrap_no_export\n");
 return 0;
}
