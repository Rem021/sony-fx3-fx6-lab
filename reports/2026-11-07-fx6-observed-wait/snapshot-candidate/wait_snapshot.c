#define _GNU_SOURCE
#include "snapshot_core.h"
#include <dirent.h>
#include <errno.h>
#include <inttypes.h>
#include <limits.h>
#include <signal.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ptrace.h>
#include <sys/uio.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#if !defined(__aarch64__) || !defined(__linux__)
#error "guest helper must be Linux AArch64"
#endif
_Static_assert(sizeof(long)==8,"PEEKDATA LP64 word");
_Static_assert(PTRACE_SEIZE==FX6_SEIZE && PTRACE_INTERRUPT==FX6_INTERRUPT && PTRACE_GETREGSET==FX6_GETREGSET && PTRACE_DETACH==FX6_DETACH && PTRACE_PEEKDATA==FX6_PEEKDATA,"ptrace request ABI");
static volatile sig_atomic_t cancelled;
static struct fx6_active active;
static struct fx6_ops ops;
static int target_pid;

static void stop_handler(int sig) {
 if (cancelled) {
  const char m[]="FX6_WAIT_SNAPSHOT_HARD_EXIT cleanup_deadline=1 kernel_tracer_exit_unlinks=1\n";
  (void)write(2,m,sizeof(m)-1);_exit(124);
 }
 cancelled=sig;alarm(1);
}
static int is_cancelled(void) { return cancelled!=0; }
static uint64_t monotonic_ms(void) {
 struct timespec t;
 if (clock_gettime(CLOCK_MONOTONIC,&t)<0) { cancelled=SIGALRM;return UINT64_MAX/2; }
 return (uint64_t)t.tv_sec*1000+(uint64_t)t.tv_nsec/1000000;
}
static void short_pause(void) { struct timespec t={0,1000000};(void)nanosleep(&t,0); }
static long trace_request(int request,int tid,uintptr_t address,uintptr_t data,int *error) {
 errno=0;long result=ptrace((enum __ptrace_request)request,tid,(void *)address,(void *)data);*error=errno;return result;
}
static int wait_request(int tid,int *status,int *error) {
 errno=0;int result=waitpid(tid,status,__WALL|WNOHANG);*error=errno;return result;
}
static void cleanup(void) {
 if (active.seized)(void)fx6_cleanup_thread(&ops,&active);
}
static void cleanup_on_exit(int status,void *arg) { (void)status;(void)arg;cleanup(); }
static int belongs_to_target(int tid) {
 char path[96],line[128];snprintf(path,sizeof path,"/proc/%d/task/%d/status",target_pid,tid);
 FILE *f=fopen(path,"r");if (!f)return 0;
 int found=0,tgid=0;
 while (fgets(line,sizeof line,f))if (sscanf(line,"Tgid:%d",&tgid)==1) { found=tgid==target_pid;break; }
 fclose(f);return found;
}
static int read_stack(int tid,uint64_t sp,struct fx6_stack *stack) {
 char path[96],line[1024];snprintf(path,sizeof path,"/proc/%d/task/%d/maps",target_pid,tid);
 FILE *f=fopen(path,"r");if (!f) {
  fprintf(stdout,"FX6_WAIT_SNAPSHOT_STACK_FAIL tid=%d errno=%d\n",tid,errno);return 0;
 }
 int found=0;unsigned count=0;
 while (!cancelled && count++<4096 && fgets(line,sizeof line,f)) {
  unsigned long long low,high;char perms[5]={0};int used=0;
  if (sscanf(line,"%llx-%llx %4s %*s %*s %*s %n",&low,&high,perms,&used)!=3)continue;
  char *name=line+used;name[strcspn(name,"\r\n")]=0;
  /* Only the readable+writable anonymous/explicit stack VMA holding this
     thread's live SP qualifies. File-backed mappings are never peeked. */
  if (low<=sp && sp<high && perms[0]=='r' && perms[1]=='w' &&
      (!*name || !strncmp(name,"[stack",6))) {
   stack->low=low;stack->high=high;found=1;break;
  }
 }
 fclose(f);return found;
}
static int dump_proc_file(const char *path,const char *label,int tid,size_t limit) {
 FILE *f=fopen(path,"r");if (!f) {
  fprintf(stdout,"FX6_WAIT_SNAPSHOT_%s_FAIL tid=%d errno=%d\n",label,tid,errno);return 1;
 }
 fprintf(stdout,"FX6_WAIT_SNAPSHOT_%s_BEGIN tid=%d\n",label,tid);
 char line[1024];size_t bytes=0;int failed=0;
 while (!cancelled && fgets(line,sizeof line,f)) {
  size_t n=strlen(line);if (n>limit-bytes) { failed=1;break; }
  fputs(line,stdout);bytes+=n;
 }
 if (ferror(f)) { fprintf(stdout,"FX6_WAIT_SNAPSHOT_%s_READ_FAIL tid=%d errno=%d\n",label,tid,errno);failed=1; }
 fprintf(stdout,"FX6_WAIT_SNAPSHOT_%s_END tid=%d bytes=%zu truncated=%d cancelled=%d\n",label,tid,bytes,failed,!!cancelled);
 fclose(f);return failed;
}
static int compare_pid(const void *a,const void *b) { int x=*(const int*)a,y=*(const int*)b;return (x>y)-(x<y); }
int main(int argc,char **argv) {
 setvbuf(stdout,0,_IONBF,0);setvbuf(stderr,0,_IONBF,0);
 if (argc!=2) { fprintf(stderr,"FX6_WAIT_SNAPSHOT_USAGE expected=appfw_pid\n");return 64; }
 errno=0;char *end=0;long parsed=strtol(argv[1],&end,10);
 if (errno || !end || *end || parsed<=1 || parsed>INT_MAX || parsed==getpid())return 64;
 target_pid=(int)parsed;
 long page=sysconf(_SC_PAGESIZE);if (page<16 || (page&(page-1)) || page>65536)return 65;
 ops=(struct fx6_ops){trace_request,wait_request,monotonic_ms,short_pause,is_cancelled,belongs_to_target,read_stack,stdout,(uint64_t)page};
 struct sigaction sa={0};sa.sa_handler=stop_handler;sigemptyset(&sa.sa_mask);
 if (sigaction(SIGALRM,&sa,0) || sigaction(SIGINT,&sa,0) || sigaction(SIGTERM,&sa,0) || on_exit(cleanup_on_exit,0))return 66;
 alarm(6);uint64_t begin=monotonic_ms();
 fprintf(stdout,"FX6_WAIT_SNAPSHOT_BEGIN pid=%d monotonic_ms=%" PRIu64 " page=%ld thread_pause=1 sequential=1 no_exitkill=1\n",target_pid,begin,page);
 char path[96];snprintf(path,sizeof path,"/proc/%d/maps",target_pid);(void)dump_proc_file(path,"MAPS",target_pid,512*1024);
 snprintf(path,sizeof path,"/proc/%d/task",target_pid);DIR *d=opendir(path);
 if (!d) { fprintf(stdout,"FX6_WAIT_SNAPSHOT_ENUM_FAIL errno=%d\n",errno);return 67; }
 int tids[512];unsigned count=0;struct dirent *entry;int overflow=0;
 while (!cancelled && (entry=readdir(d))) {
  char *last=0;errno=0;long n=strtol(entry->d_name,&last,10);
  if (errno || !last || *last || n<=0 || n>INT_MAX)continue;
  if (count==512) { overflow=1;break; }tids[count++]=(int)n;
 }
 closedir(d);qsort(tids,count,sizeof *tids,compare_pid);
 fprintf(stdout,"FX6_WAIT_SNAPSHOT_ENUM pid=%d tids=%u overflow=%d scope=existing_at_enumeration\n",target_pid,count,overflow);
 unsigned done=0,failures=0;int detach_failed=0;
 for (unsigned i=0;i<count && !cancelled;i++) {
  snprintf(path,sizeof path,"/proc/%d/task/%d/comm",target_pid,tids[i]);(void)dump_proc_file(path,"COMM",tids[i],4096);
  snprintf(path,sizeof path,"/proc/%d/task/%d/syscall",target_pid,tids[i]);(void)dump_proc_file(path,"SYSCALL",tids[i],4096);
  if (cancelled)break;
  int result=fx6_capture_thread(&ops,&active,tids[i]);done++;
  if (result)failures++;
  if (result<0) { detach_failed=1;break; }
 }
 cleanup();
 fprintf(stdout,"FX6_WAIT_SNAPSHOT_END pid=%d processed=%u enumerated=%u failures=%u cancelled=%d overflow=%d detach_failed=%d elapsed_ms=%" PRIu64 "\n",target_pid,done,count,failures,!!cancelled,overflow,detach_failed,monotonic_ms()-begin);
 if (active.seized) {
  fprintf(stdout,"FX6_WAIT_SNAPSHOT_UNRESOLVED_EXIT tid=%d kernel_tracer_exit_unlinks=1\n",active.tid);_exit(70);
 }
 alarm(0);return cancelled?124:(detach_failed?70:(overflow || failures || done!=count?1:0));
}
