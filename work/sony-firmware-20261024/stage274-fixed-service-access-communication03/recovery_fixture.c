/* Never linked into the native helper. Only own unprivileged fake caches. */
#include "recovery_fixture.h"
#include "entry_shared.h"
#include "entry_target.h"
#include <CommonCrypto/CommonDigest.h>
#include <fcntl.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
static uint32_t g32(const uint8_t *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static uint64_t g64(const uint8_t *p){return g32(p)|((uint64_t)g32(p+4)<<32);}
static fx3_guard_actor actor(const uint8_t *p){return (fx3_guard_actor){g32(p),g32(p+4),g64(p+8),g64(p+16)};}
int fx3_fixture_recovery_load(const char *path,uint32_t uid,fx3_fixture_recovery_context *out){
    if(getuid()!=geteuid() || getuid()!=uid || !uid || !out || strncmp(path,FX3_FIXTURE_JOB_ROOT,strlen(FX3_FIXTURE_JOB_ROOT)))return -1;
    int fd=open(path,O_RDONLY|O_NOFOLLOW|O_CLOEXEC|O_NONBLOCK);if(fd<0)return -1;
    struct stat s;uint8_t b[256],digest[32];
    int ok=!fstat(fd,&s) && S_ISREG(s.st_mode) && s.st_uid==uid && s.st_nlink==1 &&
        (s.st_mode&07777)==0400 && s.st_size==256 && pread(fd,b,256,0)==256;close(fd);if(!ok)return -1;
    CC_SHA256(b,224,digest);
    if(memcmp(b,"FX3RCV01",8) || g32(b+8)!=1 || g32(b+12)!=256 || memcmp(digest,b+224,32))return -1;
    for(unsigned i=208;i<224;i++)if(b[i])return -1;
    memset(out,0,sizeof(*out));fx3_recovery_policy *p=&out->policy;
    p->previous_owner=actor(b+16);p->previous_observer=actor(b+40);
    if(p->previous_owner.uid!=uid || p->previous_observer.uid!=uid)return -1;
    memcpy(p->previous_nonce,b+64,16);memcpy(p->previous_grant_hash,b+80,32);
    memcpy(p->prior_body_tag,b+112,32);memcpy(p->fixed_evidence_digest,b+144,32);
    p->prior_source_node=g64(b+176);p->new_source_node=g64(b+184);p->physical_port=g64(b+192);
    p->location=g32(b+200);out->variant=g32(b+204);return 0;
}
int fx3_fixture_verify_recovery(void *opaque,fx3_recovery_cache *c){
    fx3_fixture_recovery_context *ctx=opaque;if(!ctx || !c)return -1;
    *c=(fx3_recovery_cache){.registry_id=100,.physical_port=500,.observed_ns=fx3_entry_clock_ns(),
        .location=0x01100000,.unique_count=1,.storage_driver_count=3,.vid=0x54c,.pid=0x0da1};
    memset(c->body_tag,'A',32);
    switch(ctx->variant){case 0:case 100:break;case 2:c->physical_port++;break;
        case 4:c->observed_ns-=FX3_RECOVERY_FRESH_NS+1;break;case 6:c->mounted_count=1;break;default:return -1;}
    return 0;
}
