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

static uint64_t fnv1a(const unsigned char *p, size_t n) {
    uint64_t h = 1469598103934665603ULL;
    for (size_t i=0;i<n;i++) { h ^= p[i]; h *= 1099511628211ULL; }
    return h;
}
static const unsigned char b64tab[]="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
static void b64(const unsigned char *in,size_t n) {
    size_t i=0;
    for (i=0;i<n;i+=3) {
        unsigned v=in[i]<<16;
        if (i+1<n) v|=in[i+1]<<8;
        if (i+2<n) v|=in[i+2];
        putchar(b64tab[(v>>18)&63]); putchar(b64tab[(v>>12)&63]);
        putchar(i+1<n?b64tab[(v>>6)&63]:'=');
        putchar(i+2<n?b64tab[v&63]:'=');
    }
}
static int read_once(const char *path, unsigned char *buf, size_t cap) {
    int fd=open(path,O_RDONLY|O_CLOEXEC);
    if(fd<0) return -1;
    ssize_t n=read(fd,buf,cap); /* deliberately one read; never stitch repeated maps reads */
    int saved=errno; close(fd); errno=saved;
    if(n<0) return -1;
    return (int)n;
}
static int starttime_of(pid_t pid, unsigned long long *out) {
    char path[64],buf[1024]; snprintf(path,sizeof path,"/proc/%d/stat",(int)pid);
    int fd=open(path,O_RDONLY|O_CLOEXEC); if(fd<0) return -1;
    ssize_t n=read(fd,buf,sizeof(buf)-1); close(fd); if(n<=0) return -1; buf[n]=0;
    char *p=strrchr(buf,')'); if(!p) return -1; p++;
    int field=3; char *save=NULL; for(char *t=strtok_r(p," ",&save);t;t=strtok_r(NULL," ",&save),field++) {
        if(field==22){*out=strtoull(t,NULL,10);return 0;}
    }
    return -1;
}
int main(int argc,char **argv) {
    if(argc<3){fprintf(stderr,"usage: %s PID SEQ [--fixture PATH] [--starttime TICKS] [--cap BYTES]\n",argv[0]);return 2;}
    char *end=NULL; long pid_l=strtol(argv[1],&end,10); if(*end||pid_l<=0||pid_l>INT32_MAX)return 2;
    long seq_l=strtol(argv[2],&end,10); if(*end||seq_l<0)return 2;
    const char *fixture=NULL; unsigned long long starttime=0; int have_start=0; size_t cap=DEFAULT_CAP;
    for(int i=3;i<argc;i++){
        if(!strcmp(argv[i],"--cap")&&i+1<argc){long c=strtol(argv[++i],&end,10);if(*end||c<4096||c>MAX_CAP)return 2;cap=(size_t)c;}
        else if(!strcmp(argv[i],"--fixture")&&i+1<argc)fixture=argv[++i];
        else if(!strcmp(argv[i],"--starttime")&&i+1<argc){starttime=strtoull(argv[++i],&end,10);if(*end)return 2;have_start=1;}
        else {fprintf(stderr,"bad argument\n");return 2;}
    }
    char procmap[64]; const char *path;
    if(fixture){ if(!have_start){fprintf(stderr,"fixture requires --starttime\n");return 2;} path=fixture; }
    else { snprintf(procmap,sizeof procmap,"/proc/%ld/maps",pid_l); path=procmap; if(!have_start&&starttime_of((pid_t)pid_l,&starttime)!=0){fprintf(stderr,"cannot read starttime\n");return 3;} }
    unsigned char *buf=malloc(cap); if(!buf){fprintf(stderr,"oom\n");return 3;}
    int n=read_once(path,buf,cap); if(n<0){fprintf(stderr,"read failed: %s\n",strerror(errno));free(buf);return 3;}
    if(n==0){fprintf(stderr,"empty maps\n");free(buf);return 4;}
    if((size_t)n==cap){printf("FX3MS1 ERROR pid=%ld starttime=%llu seq=%ld reason=cap_exceeded cap=%zu read=%d\n",pid_l,starttime,seq_l,cap,n);free(buf);return 4;}
    uint64_t digest=fnv1a(buf,(size_t)n); size_t lines=0; for(int i=0;i<n;i++) if(buf[i]=='\n')lines++;
    int term=n>0&&buf[n-1]=='\n';
    printf("FX3MS1 BEGIN pid=%ld starttime=%llu seq=%ld cap=%zu single_read=1 capture=bounded_single_read\n",pid_l,starttime,seq_l,cap);
    for(int off=0;off<n;off+=B64_CHUNK){printf("FX3MS1 DATA %d ",off/B64_CHUNK);b64(buf+off,(size_t)((n-off>B64_CHUNK)?B64_CHUNK:n-off));putchar('\n');}
    printf("FX3MS1 END pid=%ld starttime=%llu seq=%ld bytes=%d lines=%zu digest=fnv1a64:%016llx line_terminated=%d complete=%d snapshot_atomic=0\n",pid_l,starttime,seq_l,n,lines,(unsigned long long)digest,term,term);
    free(buf);return term?0:4;
}
