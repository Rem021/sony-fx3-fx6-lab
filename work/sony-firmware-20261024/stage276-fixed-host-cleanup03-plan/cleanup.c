/* Fixed host-only cleanup. No USB, IOKit, camera, driver or firmware API.
 * Executes only after distinct approval and user-confirmed physical removal. */
#include "cleanup_target.h"
#include <CommonCrypto/CommonDigest.h>
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>
static uint32_t u32(const unsigned char *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static uint64_t u64(const unsigned char *p){return u32(p)|((uint64_t)u32(p+4)<<32);}
static int unchanged(const struct stat *a,const struct stat *b){
    return a->st_dev==b->st_dev && a->st_ino==b->st_ino && a->st_size==b->st_size &&
        a->st_mtimespec.tv_sec==b->st_mtimespec.tv_sec && a->st_mtimespec.tv_nsec==b->st_mtimespec.tv_nsec &&
        a->st_ctimespec.tv_sec==b->st_ctimespec.tv_sec && a->st_ctimespec.tv_nsec==b->st_ctimespec.tv_nsec;
}
static int hash_file(const char *path,unsigned char digest[32],struct stat *identity,unsigned char *tail){
    int fd=open(path,O_RDONLY|O_NOFOLLOW|O_CLOEXEC|O_NONBLOCK);if(fd<0)return -1;
    struct stat before,after;struct statfs fs;int ok=0;
    if(fstat(fd,&before) || !S_ISREG(before.st_mode) || before.st_nlink!=1 ||
       before.st_uid!=0 || before.st_size<=0 || before.st_size>8*1024*1024 ||
       fstatfs(fd,&fs) || (fs.f_flags&MNT_IGNORE_OWNERSHIP))goto end;
    CC_SHA256_CTX ctx;CC_SHA256_Init(&ctx);unsigned char block[4096];off_t at=0;
    while(at<before.st_size){
        size_t n=(size_t)(before.st_size-at);if(n>sizeof(block))n=sizeof(block);
        if(pread(fd,block,n,at)!=(ssize_t)n)goto end;
        CC_SHA256_Update(&ctx,block,(CC_LONG)n);at+=(off_t)n;
    }
    if(tail && (before.st_size%256 || before.st_size>2048*256 ||
       pread(fd,tail,256,before.st_size-256)!=256))goto end;
    if(fstat(fd,&after) || !unchanged(&before,&after))goto end;
    CC_SHA256_Final(digest,&ctx);*identity=before;ok=1;
end:close(fd);return ok?0:-1;
}
static int image(const fx3_host_identity *e,const unsigned char expected[32]){
    unsigned char digest[32];struct stat identity;
    return !hash_file(e->path,digest,&identity,NULL) && !memcmp(digest,expected,32);
}
static int gone(const fx3_host_identity *e){
    for(unsigned i=0;i<200;i++){
        int state=fx3_host_same_process(e);if(state==0)return 1;if(state<0)return -1;
        struct timespec wait={0,10000000};nanosleep(&wait,NULL);
    }return 0;
}
static int record(int directory,const char *text){
    int fd=openat(directory,"result.json",O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0400);
    if(fd<0)return -1;size_t n=strlen(text);
    int ok=write(fd,text,n)==(ssize_t)n && !fsync(fd);if(close(fd))ok=0;return ok?0:-1;
}
int main(int argc,char **argv){
    if(geteuid()!=0){fputs("FX3_HOST_CLEANUP_DENIED:root_required\n",stderr);return 77;}
    if(argc!=2 || strcmp(argv[1],"--confirmed-camera-USB-physically-disconnected"))return 64;
    char self[PROC_PIDPATHINFO_MAXSIZE]={0};struct stat directory_stat,self_stat;
    if(proc_pidpath(getpid(),self,sizeof(self))<=0 || strcmp(self,FX3_CLEANUP_SELF) ||
       lstat(self,&self_stat) || !S_ISREG(self_stat.st_mode) || self_stat.st_uid ||
       self_stat.st_nlink!=1 || (self_stat.st_mode&07777)!=0500)return 65;
    int directory=open(FX3_CLEANUP_ROOT,O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);if(directory<0)return 65;
    struct statfs fs;
    if(fstat(directory,&directory_stat) || directory_stat.st_uid || (directory_stat.st_mode&07777)!=0700 ||
       fstatfs(directory,&fs) || (fs.f_flags&MNT_IGNORE_OWNERSHIP)){close(directory);return 65;}
    int once=openat(directory,"entry.once",O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0400);
    if(once<0){close(directory);return 67;}
    const char mark[]="host-only cleanup; fixed PIDs; no camera actions; no retry\n";
    int consumed=write(once,mark,sizeof(mark)-1)==sizeof(mark)-1 && !fsync(once);close(once);
    if(!consumed){close(directory);return 68;}
    audit_token_t helper={0},observer={0};
    unsigned char guard_before[32]={0},guard_after[32]={0},tail[256]={0};struct stat gb,ga;
    int helper_signal=0,helper_absent=0,observer_signal=0,observer_absent=0,guard_same=0,error=0;
    const char *status="DENIED_BEFORE_SIGNALS";
    if(!image(&helper_identity,helper_image_hash) || !image(&observer_identity,observer_image_hash) ||
       fx3_host_capture_token(&helper_identity,&helper) || fx3_host_capture_token(&observer_identity,&observer)){
        error=errno;goto finish;
    }
    if(hash_file(FX3_OLD_GUARD,guard_before,&gb,tail) || (gb.st_mode&07777)!=0600 ||
       memcmp(tail,"FX3-GUARD-v1",12) || u32(tail+20)!=1 || u32(tail+28)!=(uint32_t)helper_identity.pid ||
       u32(tail+32)!=helper_identity.uid || u64(tail+40)!=helper_identity.sec || u64(tail+48)!=helper_identity.usec){
        error=EINVAL;goto finish;
    }
    /* This explicit forced host termination is a distinct exception to274's
     * no-kill policy. It is never issued to a PID without its audit version. */
    if(fx3_host_same_process(&helper_identity)!=1 || fx3_host_signal_token(&helper,SIGKILL)){
        error=errno;goto finish;
    }
    helper_signal=SIGKILL;helper_absent=gone(&helper_identity);
    if(helper_absent!=1){status="UNKNOWN_HELPER_EXIT";error=errno;goto finish;}
    status="HELPER_GONE_OBSERVER_UNRESOLVED";
    int observed=fx3_host_same_process(&observer_identity);
    if(observed==1){
        if(fx3_host_signal_token(&observer,SIGTERM)){error=errno;goto finish;}
        observer_signal=SIGTERM;observer_absent=gone(&observer_identity);
    }else observer_absent=observed==0?1:-1;
    if(observer_absent!=1){error=errno;goto finish;}
    if(hash_file(FX3_OLD_GUARD,guard_after,&ga,NULL) || !unchanged(&gb,&ga) || memcmp(guard_before,guard_after,32)){
        status="HOST_PROCESSES_GONE_GUARD_CHECK_UNKNOWN";error=errno;goto finish;
    }
    guard_same=1;status="HOST_CLEANUP_ONLY_OLD_TRIAL_STILL_UNKNOWN";
finish:;
    char text[1200];int n=snprintf(text,sizeof(text),
        "{\"status\":\"%s\",\"helper_PID\":%d,\"helper_signal\":%d,\"helper_absent\":%d,\"observer_PID\":%d,\"observer_signal\":%d,\"observer_absent\":%d,\"old_guard_bytes_unchanged\":%s,\"old_trial_COMPLETE\":false,\"new_trial_authorized\":false,\"USB_requests\":0,\"firmware_writes\":0,\"automatic_retry\":false,\"error\":%d}\n",
        status,helper_identity.pid,helper_signal,helper_absent,observer_identity.pid,observer_signal,observer_absent,guard_same?"true":"false",error);
    int logged=n>0 && (size_t)n<sizeof(text) && !record(directory,text);
    if(n>0 && (size_t)n<sizeof(text)){fputs(text,stdout);fflush(stdout);}close(directory);
    return helper_absent==1 && observer_absent==1 && guard_same && logged?0:69;
}
