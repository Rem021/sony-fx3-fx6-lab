#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#define DEFAULT_CAP 262144
#define MAX_CAP 1048576
#define B64_CHUNK 192
#define MAX_RETRY 3
static const unsigned char b64tab[]="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
static uint64_t fnv1a(const unsigned char *p,size_t n){uint64_t h=14695981039346656037ULL;for(size_t i=0;i<n;i++){h^=p[i];h*=1099511628211ULL;}return h;}
static void b64(const unsigned char *in,size_t n){for(size_t i=0;i<n;i+=3){unsigned v=in[i]<<16;if(i+1<n)v|=in[i+1]<<8;if(i+2<n)v|=in[i+2];putchar(b64tab[(v>>18)&63]);putchar(b64tab[(v>>12)&63]);putchar(i+1<n?b64tab[(v>>6)&63]:'=');putchar(i+2<n?b64tab[v&63]:'=');}}
static ssize_t retry_read(int fd,void *buf,size_t n,int *attempts){*attempts=0;while(*attempts<MAX_RETRY){(*attempts)++;ssize_t r=read(fd,buf,n);if(r>=0)return r;if(errno!=EINTR)return -1;}return -1;}
static int parse_stat(const char *buf,long *pid,unsigned long long *start){const char *p=strrchr(buf,')');if(!p)return -1;char *end=NULL;errno=0;long q=strtol(buf,&end,10);if(end==buf||( *end!=' ' && *end!='\0')||errno||q<=0)return -1;*pid=q; /* caller checks */
 char *copy=strdup(p+1);if(!copy)return -1;char *save=NULL;int field=3;int ok=-1;for(char *t=strtok_r(copy," ",&save);t;t=strtok_r(NULL," ",&save),field++){if(field==22){errno=0;unsigned long long v=strtoull(t,&end,10);if(end==t||*end||errno)break;*start=v;ok=0;break;}}free(copy);if(ok==0){*pid=q;return 0;}return -1;}
typedef struct {long pid;size_t cap;unsigned char *buf;int dirfd;int mapsfd;int attempts_data;int attempts_probe;} Ctx;
#ifndef FX3_MAP_SNAPSHOT_TEST
static int io_open_dir(Ctx*c,long pid){char p[64];snprintf(p,sizeof p,"/proc/%ld",pid);c->dirfd=open(p,O_RDONLY|O_DIRECTORY|O_CLOEXEC);return c->dirfd<0?-1:0;}
static int io_stat(Ctx*c,int phase,long*pid,unsigned long long*st){(void)phase;int fd=openat(c->dirfd,"stat",O_RDONLY|O_CLOEXEC);if(fd<0)return -1;char b[1024];int a=0;ssize_t n=retry_read(fd,b,sizeof(b)-1,&a);close(fd);if(n<=0)return -1;b[n]=0;return parse_stat(b,pid,st);}
static int io_open_maps(Ctx*c){c->mapsfd=openat(c->dirfd,"maps",O_RDONLY|O_CLOEXEC);return c->mapsfd<0?-1:0;}
static ssize_t io_data(Ctx*c,unsigned char*buf,size_t cap){return retry_read(c->mapsfd,buf,cap,&c->attempts_data);}
static ssize_t io_probe(Ctx*c){unsigned char b;return retry_read(c->mapsfd,&b,1,&c->attempts_probe);}
static void io_close(Ctx*c){if(c->mapsfd>=0)close(c->mapsfd);if(c->dirfd>=0)close(c->dirfd);}
#else
static int test_trace(const char*p){const char*f=getenv("FX3_TEST_TRACE");if(!f)return 0;int fd=open(f,O_WRONLY|O_CREAT|O_APPEND|O_CLOEXEC,0600);if(fd<0)return -1;ssize_t n=write(fd,p,strlen(p));close(fd);return n==(ssize_t)strlen(p)?0:-1;}
static int read_path(const char*path,char*b,size_t cap){int fd=open(path,O_RDONLY|O_CLOEXEC);if(fd<0)return -1;int a=0;ssize_t n=retry_read(fd,b,cap,&a);close(fd);return n<0?-1:(int)n;}
static int io_open_dir(Ctx*c,long pid){(void)c;(void)pid;test_trace("open\n");return 0;}
static int io_stat(Ctx*c,int phase,long*pid,unsigned long long*st){(void)c;test_trace(phase==0?"stat_before\n":"stat_after\n");const char*k=phase==0?"FX3_TEST_STAT_BEFORE":"FX3_TEST_STAT_AFTER";const char*f=getenv(k);if(!f)return -1;char b[1024];int n=read_path(f,b,sizeof(b)-1);if(n<=0)return -1;b[n]=0;return parse_stat(b,pid,st);}
static int io_open_maps(Ctx*c){(void)c;test_trace("maps_open\n");return 0;}
static ssize_t io_data(Ctx*c,unsigned char*buf,size_t cap){int a=0;const char*e=getenv("FX3_TEST_EINTR");if(e&&*e){c->attempts_data=1;test_trace("data_eintr\n");return -1;}const char*f=getenv("FX3_TEST_MAPS");int fd=open(f,O_RDONLY|O_CLOEXEC);if(fd<0)return -1;ssize_t n=retry_read(fd,buf,cap,&a);c->attempts_data=a;close(fd);test_trace("data\n");return n;}
static ssize_t io_probe(Ctx*c){c->attempts_probe=1;const char*e=getenv("FX3_TEST_EOF_FAIL");if(e&&*e){test_trace("probe_error\n");return -1;}const char*x=getenv("FX3_TEST_EXTRA");test_trace("probe\n");return (x&&*x)?1:0;}
static void io_close(Ctx*c){(void)c;test_trace("close\n");}
#endif
static int emit(long pid,unsigned long long st,long seq,const unsigned char*buf,size_t n,int term,size_t cap,int da,int pa){
 uint64_t d=fnv1a(buf,n);size_t lines=0;for(size_t i=0;i<n;i++)if(buf[i]=='\n')lines++;
 printf("FX3MS1 BEGIN pid=%ld starttime=%llu seq=%ld cap=%zu data_reads=1 eof_probe=1 data_attempts=%d eof_attempts=%d capture=bounded_single_read\n",pid,st,seq,cap,da,pa);
 for(size_t off=0;off<n;off+=B64_CHUNK){printf("FX3MS1 DATA %zu %ld %llu %ld ",off/B64_CHUNK,pid,st,seq);b64(buf+off,((n-off>B64_CHUNK)?B64_CHUNK:(n-off)));putchar('\n');}
 printf("FX3MS1 END pid=%ld starttime=%llu seq=%ld bytes=%zu lines=%zu digest=fnv1a64:%016llx line_terminated=%d complete=%d snapshot_atomic=0 data_reads=1 eof_probe=1 eof_observed=1 data_attempts=%d eof_attempts=%d\n",pid,st,seq,n,lines,(unsigned long long)d,term,term,da,pa);return term?0:4;
}
static int fail(const char*w,long pid,unsigned long long st,long seq){printf("FX3MS1 ERROR pid=%ld starttime=%llu seq=%ld reason=%s\n",pid,st,seq,w);return 4;}
static int run_capture(long pid,long seq){
 Ctx c={.pid=pid,.cap=DEFAULT_CAP,.buf=NULL,.dirfd=-1,.mapsfd=-1,.attempts_data=0,.attempts_probe=0};
#ifdef FX3_MAP_SNAPSHOT_TEST
 const char*cs=getenv("FX3_TEST_CAP");if(cs){char*e=NULL;errno=0;long x=strtol(cs,&e,10);if(errno||*e||x<4096||x>MAX_CAP)return fail("test_cap",pid,0,seq);c.cap=(size_t)x;}
#endif
 c.buf=malloc(c.cap);if(!c.buf)return fail("oom",pid,0,seq);
 long p1=0,p2=0;unsigned long long s1=0,s2=0;int rc;
 if(io_open_dir(&c,pid)!=0){free(c.buf);return fail("open_proc_pid",pid,0,seq);}
 if(io_stat(&c,0,&p1,&s1)!=0){io_close(&c);free(c.buf);return fail("stat_before_error",pid,0,seq);} if(p1!=pid){io_close(&c);free(c.buf);return fail("pid_mismatch_before",pid,s1,seq);}
 if(io_open_maps(&c)!=0){io_close(&c);free(c.buf);return fail("open_maps",pid,s1,seq);}
 ssize_t n=io_data(&c,c.buf,c.cap);
 if(n<0){io_close(&c);free(c.buf);return fail("data_read_error",pid,s1,seq);} if(n==0){io_close(&c);free(c.buf);return fail("empty_maps",pid,s1,seq);} if((size_t)n>=c.cap){io_close(&c);free(c.buf);return fail("cap_exceeded",pid,s1,seq);}
 ssize_t pr=io_probe(&c);
 if(pr<0){io_close(&c);free(c.buf);return fail("eof_probe_error",pid,s1,seq);} if(pr>0){io_close(&c);free(c.buf);return fail("short_read_more_data",pid,s1,seq);}
 io_close(&c);
 if(io_stat(&c,1,&p2,&s2)!=0){free(c.buf);return fail("stat_after_error",pid,s1,seq);} if(p2!=pid){free(c.buf);return fail("pid_mismatch_after",pid,s2,seq);} if(s2!=s1){free(c.buf);return fail("identity_changed",pid,s1,seq);}
 int term=n>0&&c.buf[n-1]=='\n';rc=emit(pid,s1,seq,c.buf,(size_t)n,term,c.cap,c.attempts_data,c.attempts_probe);free(c.buf);return rc;
}
int main(int argc,char**argv){if(argc!=3){fprintf(stderr,"usage: %s PID SEQ\n",argv[0]);return 2;}char*e=NULL;errno=0;long pid=strtol(argv[1],&e,10);if(errno||*e||pid<=0||pid>2147483647)return 2;errno=0;long seq=strtol(argv[2],&e,10);if(errno||*e||seq<0)return 2;return run_capture(pid,seq);}
