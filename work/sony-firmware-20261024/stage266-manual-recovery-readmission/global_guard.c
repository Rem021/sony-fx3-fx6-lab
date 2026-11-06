/* Append-only host journal. No device, signal, stale deletion, new lock path,
 * or auto-recovery. An explicit recovery transaction never labels old CLEAN. */
#include "global_guard.h"
#include "entry_shared.h"
#include <CommonCrypto/CommonDigest.h>
#include <fcntl.h>
#include <string.h>
#include <sys/file.h>
#include <sys/mount.h>
#include <unistd.h>
static uint32_t get32(const uint8_t *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static uint64_t get64(const uint8_t *p){return get32(p)|((uint64_t)get32(p+4)<<32);}
static void put32(uint8_t *p,uint32_t v){for(unsigned i=0;i<4;i++)p[i]=(uint8_t)(v>>(8*i));}
static void put64(uint8_t *p,uint64_t v){put32(p,(uint32_t)v);put32(p+4,(uint32_t)(v>>32));}
static int nonzero(const uint8_t *p,size_t n){uint8_t v=0;while(n--)v|=*p++;return v!=0;}
static int close_guard(fx3_global_guard *g,int rc){if(g->fd>=0)close(g->fd);g->fd=-1;return rc;}
static int identity(fx3_global_guard *g){
    struct stat s;return g->fd>=0 && !fstat(g->fd,&s) && S_ISREG(s.st_mode) && s.st_uid==g->uid &&
        s.st_nlink==1 && (s.st_mode&07777)==0600 && s.st_dev==g->identity.st_dev &&
        s.st_ino==g->identity.st_ino && s.st_size==(off_t)g->count*FX3_GUARD_RECORD;
}
static int append(fx3_global_guard *g,uint32_t state,const uint8_t *extra){
    if(g->count>=FX3_GUARD_LIMIT)return G_FULL;if(!identity(g))return G_INVALID;
    uint8_t r[256]={0};int recovered=state==G_MANUALLY_RECOVERED;
    memcpy(r,recovered?"FX3-GUARD-v2":"FX3-GUARD-v1",12);put32(r+16,recovered?2:1);
    put32(r+20,state);put32(r+24,g->count+1);put32(r+28,g->pid);put32(r+32,g->uid);
    put64(r+40,g->sec);put64(r+48,g->usec);memcpy(r+56,g->nonce,16);memcpy(r+72,g->grant,32);
    if(g->count)memcpy(r+104,g->last+224,32);if(recovered && extra)memcpy(r+136,extra,88);
    CC_SHA256(r,224,r+224);
    /* A partial write is left as a blocking damaged tail; never filled/retried. */
    if(pwrite(g->fd,r,sizeof(r),(off_t)g->count*256)!=sizeof(r) || fsync(g->fd))return G_IO;
    memcpy(g->last,r,sizeof(r));g->count++;return identity(g)?G_OK:G_INVALID;
}
static int fresh_scope(fx3_global_guard *g){
    for(uint32_t i=0;i<g->count;i++){
        uint8_t r[256];if(pread(g->fd,r,sizeof(r),(off_t)i*256)!=sizeof(r))return G_IO;
        if(!memcmp(r+56,g->nonce,16) || !memcmp(r+72,g->grant,32))return G_STALE;
    }return G_OK;
}
static int load(fx3_global_guard *g,const char *path,uint32_t uid,const uint8_t *nonce,const char *grant,int create){
    if(!g || g->fd!=-1 || !path || !nonce || !grant || !nonzero(nonce,16) || !grant[0])return G_INVALID;
    g->uid=uid;g->pid=(uint32_t)getpid();uint32_t actual=0;
    if(fx3_entry_pid_info(g->pid,&actual,&g->sec,&g->usec) || actual!=uid)return G_INVALID;
    memcpy(g->nonce,nonce,16);CC_SHA256(grant,(CC_LONG)strlen(grant),g->grant);
    g->fd=open(path,O_RDWR|O_NOFOLLOW|O_CLOEXEC|O_NONBLOCK|(create?O_CREAT:0),0600);if(g->fd<0)return G_INVALID;
    struct stat s;struct statfs fs;
    if(fstat(g->fd,&s) || !S_ISREG(s.st_mode) || s.st_uid!=uid || s.st_nlink!=1 ||
       (s.st_mode&07777)!=0600 || s.st_size<0 || s.st_size>2048*256 || s.st_size%256 || fstatfs(g->fd,&fs))return close_guard(g,G_INVALID);
#ifndef FX3_ENTRY_FIXTURE
    if(uid!=0 || (fs.f_flags&MNT_IGNORE_OWNERSHIP))return close_guard(g,G_INVALID);
#endif
    if(flock(g->fd,LOCK_EX|LOCK_NB))return close_guard(g,G_BUSY);
    if(fstat(g->fd,&s) || !S_ISREG(s.st_mode) || s.st_uid!=uid || s.st_nlink!=1 ||
       (s.st_mode&07777)!=0600 || s.st_size<0 || s.st_size>2048*256 || s.st_size%256)return close_guard(g,G_INVALID);
    g->identity=s;g->count=(uint32_t)(s.st_size/256);uint8_t prev[256]={0};
    for(uint32_t i=0;i<g->count;i++){
        uint8_t r[256],hash[32];if(pread(g->fd,r,256,(off_t)i*256)!=256)return close_guard(g,G_IO);
        CC_SHA256(r,224,hash);uint32_t state=get32(r+20),before=get32(prev+20),version=get32(r+16);
        if(get32(r+24)!=i+1 || get32(r+32)!=uid || memcmp(r+224,hash,32) || memcmp(r+104,prev+224,32) ||
           nonzero(r+12,4) || nonzero(r+36,4))return close_guard(g,G_INVALID);
        if(version==1){
            if(memcmp(r,"FX3-GUARD-v1",12) || state<1 || state>3 || nonzero(r+136,88))return close_guard(g,G_INVALID);
            if(!i && state!=G_OWNED)return close_guard(g,G_INVALID);
            if(i && state==G_OWNED && before!=G_CLEAN &&
               !(before==G_MANUALLY_RECOVERED && !memcmp(r+28,prev+28,76)))return close_guard(g,G_INVALID);
            if(i && state!=G_OWNED && (before!=G_OWNED || memcmp(r+28,prev+28,76)))return close_guard(g,G_INVALID);
        }else if(version==2){
            if(memcmp(r,"FX3-GUARD-v2",12) || state!=G_MANUALLY_RECOVERED || !i ||
               (before!=G_OWNED && before!=G_UNKNOWN) || !nonzero(r+136,32) || !nonzero(r+168,32) ||
               !get64(r+200) || !get64(r+208) || !get32(r+216) || get32(r+220)!=1 ||
               !memcmp(r+56,prev+56,16) || !memcmp(r+72,prev+72,32))return close_guard(g,G_INVALID);
        }else return close_guard(g,G_INVALID);
        memcpy(prev,r,256);
    }
    memcpy(g->last,prev,256);return G_OK;
}
int fx3_global_begin(fx3_global_guard *g,const char *path,uint32_t uid,const uint8_t *nonce,const char *grant){
    int rc=load(g,path,uid,nonce,grant,1);if(rc)return rc;
    if(g->count && get32(g->last+20)!=G_CLEAN)return close_guard(g,G_STALE);
    if(g->count>FX3_GUARD_LIMIT-2)return close_guard(g,G_FULL);
    rc=fresh_scope(g);if(rc)return close_guard(g,rc);
    rc=append(g,G_OWNED,NULL);if(rc)return close_guard(g,rc);g->started=1;return G_OK;
}
static int gone(const fx3_guard_actor *a){
    uint32_t uid=0;uint64_t sec=0,usec=0;
    if(!a || a->pid<=1 || !a->sec || a->usec>=1000000)return 0;
    if(!fx3_entry_pid_info(a->pid,&uid,&sec,&usec))return uid!=a->uid || sec!=a->sec || usec!=a->usec;
    return fx3_entry_pid_exists(a->pid)==0;
}
#ifdef FX3_ENTRY_FIXTURE
static int stop_after_recovered;
void fx3_guard_fixture_stop_after_recovered(int on){stop_after_recovered=on;}
#endif
int fx3_global_begin_recovered(fx3_global_guard *g,const char *path,uint32_t uid,const uint8_t *nonce,const char *grant,
    const fx3_recovery_policy *p,fx3_recovery_verify verify,void *opaque){
    if(!p || !verify || !p->prior_source_node || !p->new_source_node || p->new_source_node==p->prior_source_node ||
       !p->physical_port || !p->location || !nonzero(p->prior_body_tag,32) || !nonzero(p->fixed_evidence_digest,32))return G_INVALID;
    int rc=load(g,path,uid,nonce,grant,0);if(rc)return rc;
    uint8_t *last=g->last;uint32_t state=get32(last+20);const fx3_guard_actor *old=&p->previous_owner;
    if(!g->count || (state!=G_OWNED && state!=G_UNKNOWN) || get32(last+28)!=old->pid || get32(last+32)!=old->uid ||
       get64(last+40)!=old->sec || get64(last+48)!=old->usec || memcmp(last+56,p->previous_nonce,16) ||
       memcmp(last+72,p->previous_grant_hash,32) || !memcmp(g->nonce,p->previous_nonce,16) ||
       !memcmp(g->grant,p->previous_grant_hash,32) || !gone(old) || !gone(&p->previous_observer))return close_guard(g,G_STALE);
    if(g->count>FX3_GUARD_LIMIT-3)return close_guard(g,G_FULL);
    rc=fresh_scope(g);if(rc)return close_guard(g,rc);
    fx3_recovery_cache c={0};if(verify(opaque,&c))return close_guard(g,G_STALE);
    uint64_t now=fx3_entry_clock_ns();
    if(!now || !c.observed_ns || c.observed_ns>now || now-c.observed_ns>FX3_RECOVERY_FRESH_NS || c.unique_count!=1 ||
       c.registry_id!=p->new_source_node || c.physical_port!=p->physical_port || c.location!=p->location ||
       c.vid!=0x054c || c.pid!=0x0da1 || !c.storage_driver_count || c.mounted_count || c.media_unknown ||
       memcmp(c.body_tag,p->prior_body_tag,32))return close_guard(g,G_STALE);
    uint8_t binding[128]={0},extra[88]={0};memcpy(binding,p->fixed_evidence_digest,32);memcpy(binding+32,c.body_tag,32);
    put64(binding+64,c.registry_id);put64(binding+72,c.physical_port);put32(binding+80,c.location);
    put32(binding+84,c.storage_driver_count);put32(binding+88,c.media_count);put32(binding+92,c.unique_count);put64(binding+96,c.observed_ns);
    put32(binding+104,p->previous_observer.pid);put32(binding+108,p->previous_observer.uid);
    put64(binding+112,p->previous_observer.sec);put64(binding+120,p->previous_observer.usec);
    CC_SHA256(binding,sizeof(binding),extra);memcpy(extra+32,c.body_tag,32);put64(extra+64,c.registry_id);
    put64(extra+72,c.physical_port);put32(extra+80,c.location);put32(extra+84,1); /* diagnostic eligibility only */
    rc=append(g,G_MANUALLY_RECOVERED,extra);if(rc)return close_guard(g,rc);
#ifdef FX3_ENTRY_FIXTURE
    if(stop_after_recovered)return close_guard(g,G_IO);
#endif
    rc=append(g,G_OWNED,NULL);if(rc)return close_guard(g,rc);g->started=1;return G_OK;
}
int fx3_global_finish(fx3_global_guard *g,int clean){
    if(!g || g->fd<0 || !g->started)return G_INVALID;
    int rc=append(g,clean?G_CLEAN:G_UNKNOWN,NULL);int fd=g->fd;g->fd=-1;
    if(close(fd) && !rc)rc=G_IO;return rc;
}
