/* Exact selected original/candidate UI logging block. No guest probe execution. */
#include <stdio.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/syscall.h>
#include <errno.h>
#include <time.h>
#include <assert.h>
#include <stdarg.h>
#include <string.h>
#include <stdlib.h>
typedef unsigned long U;typedef unsigned W;
static unsigned pid_calls,tid_calls,log_calls,clock_calls,resolve_calls;
static U timing_ns(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return (U)t.tv_sec*1000000000UL+t.tv_nsec;}
static U now(void){clock_calls++;return 43;}
static void save(U*p,U v){*p=v;}
static long host_syscall(long n,...){if(n==172){pid_calls++;return syscall(SYS_getpid);}assert(n==178);tid_calls++;return 42;}
static int *host_errno(void){return &errno;}
struct r35_packet;static void *host_resolve(void*,const char*);
#define syscall host_syscall
#define __errno_location host_errno
#define dlsym host_resolve
#define R35_HOST_MANUAL_INIT 1
#ifdef CANDIDATE
#include "r35-collector.inc"
#include "r35-log.inc"
#endif
#undef dlsym
static void *host_resolve(void*h,const char*n){resolve_calls++;
#ifdef CANDIDATE
 return (void*)fx3_r35_snapshot_v1;
#else
 return 0;
#endif
}
static int stream=0,io_sink=-1;static U total_chars;static char text[1024];
static int host_dprintf(int fd,const char*format,...){va_list a;va_start(a,format);int n=io_sink>=0?vdprintf(io_sink,format,a):vsnprintf(text,sizeof text,format,a);va_end(a);assert(n>0&&n<(int)sizeof text);total_chars+=n;log_calls++;if(stream)fputs(text,stdout);return n;}
#define dprintf host_dprintf
static struct {U last_ns;} st;
static void event(U n){U id=9,app_base=0x10000000,obj=0x30000000,a18=3,a12=0,a13=1,elapsed=5,msg=0,type=0,src=0;W decision_a18=2;U r[31]={7};r[22]=19;struct {U pc;} context={0x116f1a74},*c=&context;
#include BLOCK_FILE
}
int main(int argc,char**argv){
#ifdef CANDIDATE
 r35_init();r35_ui_init();
#endif
 unsigned initial_clock=clock_calls,initial_resolve=resolve_calls;pid_calls=tid_calls=log_calls=0;stream=1;
 for(unsigned n=1;n<=1001;n++)event(n);
 assert(log_calls==51&&tid_calls==51&&clock_calls-initial_clock==51&&resolve_calls==initial_resolve);
#ifdef CANDIDATE
 assert(pid_calls==102&&r35_logs==1&&r35_bytes==184);
#else
 assert(pid_calls==0);
#endif
 fprintf(stderr,"SELECTED count=%u tid_calls=%u diagnostic_getpid=%u original_clock=%u chars=%lu\n",log_calls,tid_calls,pid_calls,clock_calls-initial_clock,total_chars);
 stream=0;U begin=timing_ns();unsigned iterations=100000;
 for(unsigned i=0;i<iterations;i++)event(1);
 U end=timing_ns();fprintf(stderr,"BENCH steady_suppressed_ns_per_callback=%.2f iterations=%u\n",(double)(end-begin)/iterations,iterations);
#ifdef CANDIDATE
 begin=timing_ns();
 for(unsigned i=0;i<iterations;i++){r35_seen=0;r35_logs=r35_bytes=0;event(1);}
 end=timing_ns();fprintf(stderr,"BENCH forced_fixture_export_ns_per_callback=%.2f iterations=%u fixture_resets_not_runtime_API=1\n",(double)(end-begin)/iterations,iterations);
#endif
 begin=timing_ns();volatile long result=0;for(unsigned i=0;i<iterations;i++)result=syscall(172);end=timing_ns();fprintf(stderr,"BENCH actual_host_getpid_syscall_ns=%.2f iterations=%u last=%ld\n",(double)(end-begin)/iterations,iterations,result);
 io_sink=open("/dev/null",O_WRONLY);assert(io_sink>=0);begin=timing_ns();
 for(unsigned i=0;i<iterations;i++)event(1);
 end=timing_ns();fprintf(stderr,"BENCH actual_host_vdprintf_devnull_ns_per_callback=%.2f iterations=%u underlying_write_syscall_count_not_inferred=1\n",(double)(end-begin)/iterations,iterations);
#ifdef CANDIDATE
 begin=timing_ns();for(unsigned i=0;i<iterations;i++){r35_seen=0;r35_logs=r35_bytes=0;event(1);}end=timing_ns();fprintf(stderr,"BENCH actual_host_vdprintf_devnull_forced_export_ns_per_callback=%.2f iterations=%u fixture_resets_only=1\n",(double)(end-begin)/iterations,iterations);
#endif
 #ifdef CANDIDATE
 r35_seen=127;r35_logs=7;r35_bytes=1288;unsigned before_pids=pid_calls;begin=timing_ns();for(unsigned i=0;i<iterations;i++)event(1);end=timing_ns();assert(r35_logs==7&&r35_bytes==1288&&pid_calls-before_pids==2*iterations);fprintf(stderr,"BENCH exhausted_budget_actual_host_vdprintf_ns_per_callback=%.2f iterations=%u diagnostic_getpid_per_callback=2 no_collector_or_budget_reset=1\n",(double)(end-begin)/iterations,iterations);
#endif
 close(io_sink);return 0;
}
