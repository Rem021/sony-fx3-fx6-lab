/* Transparent signal observation; no signal is suppressed or invented. */
extern void *dlsym(void *, const char *);
extern int dprintf(int, const char *, ...);
extern int *__errno_location(void);
extern void _exit(int) __attribute__((noreturn));
extern int getpid(void);
struct di { const char *file; void *base; const char *symbol; void *address; };
extern int dladdr(const void *, struct di *);
static void report(const char *api, int pid, int sig, void *caller) {
 int saved=*__errno_location(); struct di info={0}; dladdr(caller,&info);
 dprintf(2,"FX3_SIGNAL_OBSERVE api=%s self=%d target=%d signal=%d caller=%p library=%s offset=%#lx\n",api,getpid(),pid,sig,caller,info.file?info.file:"?",(unsigned long)caller-(unsigned long)info.base);
 *__errno_location()=saved;
}
int kill(int pid,int sig) { int saved=*__errno_location(); int (*fn)(int,int)=dlsym((void *)-1,"kill"); if(!fn)_exit(126); report("kill",pid,sig,__builtin_return_address(0)); *__errno_location()=saved; return fn(pid,sig); }
int raise(int sig) { int saved=*__errno_location(); int (*fn)(int)=dlsym((void *)-1,"raise"); if(!fn)_exit(126); report("raise",getpid(),sig,__builtin_return_address(0)); *__errno_location()=saved; return fn(sig); }
int pthread_kill(unsigned long thread,int sig) { int saved=*__errno_location(); int (*fn)(unsigned long,int)=dlsym((void *)-1,"pthread_kill"); if(!fn)_exit(126); report("pthread_kill",-1,sig,__builtin_return_address(0)); *__errno_location()=saved; return fn(thread,sig); }
