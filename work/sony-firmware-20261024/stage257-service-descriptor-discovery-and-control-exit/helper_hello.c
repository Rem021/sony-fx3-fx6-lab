/* Self-image attestation on an already kernel-identified local connection.
 * Not a signature against an administrator; no hardware or new connection. */
#include "helper_hello.h"
#include "entry_shared.h"
#include <CommonCrypto/CommonDigest.h>
#include <fcntl.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
static void put32(uint8_t *p,uint32_t x){for(unsigned i=0;i<4;++i)p[i]=(uint8_t)(x>>(8*i));}
static void put64(uint8_t *p,uint64_t x){for(unsigned i=0;i<8;++i)p[i]=(uint8_t)(x>>(8*i));}
static int same(const struct stat *a,const struct stat *b) {
    return a->st_dev==b->st_dev && a->st_ino==b->st_ino && a->st_size==b->st_size && a->st_uid==b->st_uid &&
        a->st_mode==b->st_mode && a->st_nlink==b->st_nlink && a->st_mtimespec.tv_sec==b->st_mtimespec.tv_sec &&
        a->st_mtimespec.tv_nsec==b->st_mtimespec.tv_nsec && a->st_ctimespec.tv_sec==b->st_ctimespec.tv_sec &&
        a->st_ctimespec.tv_nsec==b->st_ctimespec.tv_nsec;
}
int fx3_helper_hello(const fx3_channel_config *peer,const fx3_receipt_meta *m,uint64_t deadline) {
    if(!peer || !m || !m->nonce || !m->grant || m->pid!=(uint32_t)getpid() || m->uid!=(uint32_t)geteuid())return -1;
    char path[4096];struct stat before,after;
    if(fx3_entry_pid_path(m->pid,path,sizeof(path)))return -1;
    int fd=open(path,O_RDONLY|O_NOFOLLOW|O_NONBLOCK|O_CLOEXEC);if(fd<0)return -1;
    int valid=!fstat(fd,&before) && S_ISREG(before.st_mode) && before.st_nlink==1 && before.st_uid==m->uid &&
        before.st_size>0 && before.st_size<=8*1024*1024;
#ifdef FX3_ENTRY_FIXTURE
    valid=valid && ((before.st_mode&07777)==0500 || (before.st_mode&07777)==0755);
#else
    valid=valid && (before.st_mode&07777)==0500;
#endif
    if(!valid){close(fd);return -1;}
    uint8_t record[164]={0},*p=record+4,buffer[4096];CC_SHA256_CTX hash;CC_SHA256_Init(&hash);
    off_t at=0;
    while(at<before.st_size) {
        size_t count=(size_t)(before.st_size-at);if(count>sizeof(buffer))count=sizeof(buffer);
        ssize_t n=pread(fd,buffer,count,at);
        if(n!=(ssize_t)count){close(fd);return -1;}
        CC_SHA256_Update(&hash,buffer,(CC_LONG)n);at+=n;
    }
    int ok=!fstat(fd,&after) && same(&before,&after);if(close(fd))ok=0;if(!ok)return -1;
    put32(record,160);memcpy(p,"FX3HEL01",8);put32(p+8,1);put32(p+12,160);put32(p+16,m->uid);put32(p+20,m->pid);
    put64(p+24,m->sec);put64(p+32,m->usec);memcpy(p+40,m->nonce,16);
    CC_SHA256(m->grant,(CC_LONG)strlen(m->grant),p+56);CC_SHA256_Final(p+88,&hash);CC_SHA256(p,128,p+128);
    return fx3_receipt_send_bytes(peer,record,sizeof(record),deadline);
}
