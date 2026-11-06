/* Host-only append-only fence. No device, reset, credentials or stale cleanup.
 * A dead PID is NOT a clean device receipt. flock alone is not sufficient. */
#include "global_guard.h"
#include "entry_shared.h"
#include <CommonCrypto/CommonDigest.h>
#include <fcntl.h>
#include <string.h>
#include <sys/file.h>
#include <sys/mount.h>
#include <unistd.h>
static uint32_t get32(const uint8_t *p) {return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static void put32(uint8_t *p,uint32_t n) {for(unsigned i=0;i<4;++i)p[i]=(uint8_t)(n>>(8*i));}
static void put64(uint8_t *p,uint64_t n) {for(unsigned i=0;i<8;++i)p[i]=(uint8_t)(n>>(8*i));}
static int identity(fx3_global_guard *g) {
    struct stat s;
    return g->fd>=0 && !fstat(g->fd,&s) && S_ISREG(s.st_mode) && s.st_uid==g->uid &&
        s.st_nlink==1 && (s.st_mode&07777)==0600 && s.st_dev==g->identity.st_dev && s.st_ino==g->identity.st_ino &&
        s.st_size==(off_t)g->count*FX3_GUARD_RECORD;
}
static int append(fx3_global_guard *g,uint32_t state) {
    if(g->count>=FX3_GUARD_LIMIT)return G_FULL;
    if(!identity(g))return G_INVALID;
    uint8_t record[FX3_GUARD_RECORD]={0};
    memcpy(record,"FX3-GUARD-v1",12);put32(record+16,1);put32(record+20,state);put32(record+24,g->count+1);
    put32(record+28,g->pid);put32(record+32,g->uid);put64(record+40,g->sec);put64(record+48,g->usec);
    memcpy(record+56,g->nonce,16);memcpy(record+72,g->grant,32);
    if(g->count)memcpy(record+104,g->last+224,32);
    CC_SHA256(record,224,record+224);
    /* One write, no partial-write filling or retry. A torn record blocks. */
    if(pwrite(g->fd,record,sizeof(record),(off_t)g->count*FX3_GUARD_RECORD)!=(ssize_t)sizeof(record) || fsync(g->fd))return G_IO;
    memcpy(g->last,record,sizeof(record));++g->count;return identity(g)?G_OK:G_INVALID;
}
int fx3_global_begin(fx3_global_guard *g,const char *path,uint32_t uid,const uint8_t *nonce,const char *grant) {
    if(!g || g->fd!=-1 || !path || !nonce || !grant)return G_INVALID;
    g->uid=uid;g->pid=(uint32_t)getpid();
    uint32_t actual=0;
    if(fx3_entry_pid_info(g->pid,&actual,&g->sec,&g->usec) || actual!=uid)return G_INVALID;
    memcpy(g->nonce,nonce,16);CC_SHA256(grant,(CC_LONG)strlen(grant),g->grant);
    int fd=open(path,O_RDWR|O_CREAT|O_NOFOLLOW|O_CLOEXEC|O_NONBLOCK,0600);if(fd<0)return G_INVALID;
    struct stat s;struct statfs fs;
    if(fstat(fd,&s) || !S_ISREG(s.st_mode) || s.st_uid!=uid || s.st_nlink!=1 || (s.st_mode&07777)!=0600 ||
       s.st_size<0 || s.st_size>(off_t)FX3_GUARD_RECORD*FX3_GUARD_LIMIT || s.st_size%FX3_GUARD_RECORD || fstatfs(fd,&fs)) {close(fd);return G_INVALID;}
#ifndef FX3_ENTRY_FIXTURE
    if(uid!=0 || fs.f_flags&MNT_IGNORE_OWNERSHIP) {close(fd);return G_INVALID;}
#endif
    if(flock(fd,LOCK_EX|LOCK_NB)) {close(fd);return G_BUSY;}
    if(fstat(fd,&s) || !S_ISREG(s.st_mode) || s.st_uid!=uid || s.st_nlink!=1 || (s.st_mode&07777)!=0600 ||
       s.st_size<0 || s.st_size>(off_t)FX3_GUARD_RECORD*FX3_GUARD_LIMIT || s.st_size%FX3_GUARD_RECORD) {close(fd);return G_INVALID;}
    g->fd=fd;g->identity=s;g->count=(uint32_t)(s.st_size/FX3_GUARD_RECORD);
    uint8_t previous[FX3_GUARD_RECORD]={0};
    for(uint32_t i=0;i<g->count;++i) {
        uint8_t r[FX3_GUARD_RECORD],hash[32];
        if(pread(fd,r,sizeof(r),(off_t)i*FX3_GUARD_RECORD)!=(ssize_t)sizeof(r))goto invalid;
        CC_SHA256(r,224,hash);uint32_t state=get32(r+20),before=get32(previous+20);
        if(memcmp(r,"FX3-GUARD-v1",12) || get32(r+16)!=1 || get32(r+24)!=i+1 ||
           state<1 || state>3 || memcmp(r+224,hash,32) || memcmp(r+104,previous+224,32))goto invalid;
        if((i==0 && state!=G_OWNED) || (i && before!=G_CLEAN && state==G_OWNED) ||
           (i && state!=G_OWNED && (before!=G_OWNED || memcmp(r+28,previous+28,76))))goto invalid;
        memcpy(previous,r,sizeof(r));
    }
    memcpy(g->last,previous,sizeof(previous));
    if(g->count && get32(g->last+20)!=G_CLEAN) {close(fd);g->fd=-1;return G_STALE;}
    if(g->count>FX3_GUARD_LIMIT-2) {close(fd);g->fd=-1;return G_FULL;}
    int rc=append(g,G_OWNED);
    if(rc) {close(fd);g->fd=-1;return rc;}
    g->started=1;return G_OK;
invalid:
    close(fd);g->fd=-1;return G_INVALID;
}
int fx3_global_finish(fx3_global_guard *g,int clean) {
    if(!g || g->fd<0 || !g->started)return G_INVALID;
    int rc=append(g,clean?G_CLEAN:G_UNKNOWN);
    int fd=g->fd;g->fd=-1;
    /* close releases kernel lock; durable UNKNOWN/OWNED still denies reuse. */
    if(close(fd) && !rc)rc=G_IO;
    return rc;
}
