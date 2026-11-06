/* Real ordinary-user processes/files/flock; all camera/cache data artificial. */
#include "global_guard.h"
#include "entry_shared.h"
#include <CommonCrypto/CommonDigest.h>
#include <assert.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>
typedef struct {pid_t pid;int release;fx3_guard_actor actor;} child;
typedef struct {char path[4096];child owner,observer;fx3_recovery_policy policy;} seed;
static void actor(fx3_guard_actor *a){a->pid=(uint32_t)getpid();assert(!fx3_entry_pid_info(a->pid,&a->uid,&a->sec,&a->usec));}
static child spawn(const char *path,int unknown){
    int ready[2],release[2];assert(!pipe(ready) && !pipe(release));pid_t pid=fork();assert(pid>=0);
    if(!pid){
        close(ready[0]);close(release[1]);fx3_guard_actor a;actor(&a);
        fx3_global_guard g={.fd=-1};uint8_t nonce[16];memset(nonce,'A',16);
        if(path)assert(fx3_global_begin(&g,path,(uint32_t)getuid(),nonce,"old-fixture-grant")==G_OK);
        assert(write(ready[1],&a,sizeof(a))==sizeof(a));close(ready[1]);char c;
        assert(read(release[0],&c,1)==1);if(path && unknown)assert(fx3_global_finish(&g,0)==G_OK);
        close(release[0]);_exit(0); /* OWNED intentionally survives ordinary exit. */
    }
    close(ready[1]);close(release[0]);child c={.pid=pid,.release=release[1]};
    assert(read(ready[0],&c.actor,sizeof(c.actor))==sizeof(c.actor));close(ready[0]);return c;
}
static void release_child(child *c){char yes='x';assert(write(c->release,&yes,1)==1);close(c->release);int status=0;assert(waitpid(c->pid,&status,0)==c->pid && WIFEXITED(status) && !WEXITSTATUS(status));}
static seed make_seed(const char *dir,const char *name,int unknown){
    seed s={0};assert(snprintf(s.path,sizeof(s.path),"%s/%s.journal",dir,name)>0);
    s.owner=spawn(s.path,unknown);s.observer=spawn(NULL,0);
    s.policy.previous_owner=s.owner.actor;s.policy.previous_observer=s.observer.actor;
    memset(s.policy.previous_nonce,'A',16);CC_SHA256("old-fixture-grant",17,s.policy.previous_grant_hash);
    memset(s.policy.prior_body_tag,'T',32);memset(s.policy.fixed_evidence_digest,'E',32);
    s.policy.prior_source_node=100;s.policy.new_source_node=200;s.policy.physical_port=500;s.policy.location=0x01100000;
    return s;
}
static size_t read_file(const char *path,uint8_t *out,size_t cap){int fd=open(path,O_RDONLY);assert(fd>=0);ssize_t n=read(fd,out,cap);assert(n>=0);close(fd);return (size_t)n;}
static uint32_t u32(const uint8_t *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
typedef struct {unsigned variant,calls;} cache_context;
static int verify(void *p,fx3_recovery_cache *c){
    cache_context *x=p;x->calls++;
    *c=(fx3_recovery_cache){.registry_id=200,.physical_port=500,.observed_ns=fx3_entry_clock_ns(),
        .location=0x01100000,.unique_count=1,.storage_driver_count=3,.vid=0x54c,.pid=0x0da1};
    memset(c->body_tag,'T',32);
    switch(x->variant){
    case 1:c->body_tag[0]^=1;break;case 2:c->physical_port++;break;case 3:c->registry_id++;break;
    case 4:c->observed_ns-=FX3_RECOVERY_FRESH_NS+1;break;case 5:c->observed_ns+=FX3_RECOVERY_FRESH_NS;break;
    case 6:c->mounted_count=1;break;case 7:c->media_unknown=1;break;case 8:c->storage_driver_count=0;break;
    case 9:c->unique_count=2;break;case 10:c->pid=0x0336;break;case 11:c->location++;break;
    case 12:return -1;default:break;
    }return 0;
}
static int recover(seed *s,fx3_global_guard *g,cache_context *c,const uint8_t nonce[16],const char *grant){
    return fx3_global_begin_recovered(g,s->path,(uint32_t)getuid(),nonce,grant,&s->policy,verify,c);
}
int main(int argc,char **argv){
    assert(argc==2 && getuid()==geteuid() && getuid()!=0);uint8_t nonce[16];memset(nonce,'B',16);
    uint8_t before[2048],after[2048];unsigned groups=0;
    for(unsigned unknown=0;unknown<2;unknown++){
        seed s=make_seed(argv[1],unknown?"migrate-UNKNOWN":"migrate-OWNED",unknown);
        release_child(&s.owner);release_child(&s.observer);size_t n=read_file(s.path,before,sizeof(before));
        fx3_global_guard ordinary={.fd=-1};assert(fx3_global_begin(&ordinary,s.path,(uint32_t)getuid(),nonce,"new-fixture-grant")==G_STALE);
        fx3_global_guard g={.fd=-1};cache_context c={0};assert(recover(&s,&g,&c,nonce,"new-fixture-grant")==G_OK && c.calls==1);
        assert(fx3_global_finish(&g,0)==G_OK);size_t m=read_file(s.path,after,sizeof(after));
        assert(m==n+3*256 && !memcmp(before,after,n));
        assert(u32(after+n+16)==2 && u32(after+n+20)==G_MANUALLY_RECOVERED);
        assert(u32(after+n+256+20)==G_OWNED && u32(after+n+512+20)==G_UNKNOWN);
        assert(memcmp(after+n+136,(uint8_t[32]){0},32));
        fx3_global_guard next={.fd=-1};assert(fx3_global_begin(&next,s.path,(uint32_t)getuid(),nonce,"another-grant")==G_STALE);
        groups++;
    }
    seed bad=make_seed(argv[1],"invalid-witness",0);release_child(&bad.owner);release_child(&bad.observer);
    size_t n=read_file(bad.path,before,sizeof(before));
    for(unsigned i=1;i<=12;i++){
        fx3_global_guard g={.fd=-1};cache_context c={.variant=i};assert(recover(&bad,&g,&c,nonce,"new-fixture-grant")==G_STALE && c.calls==1);
        assert(read_file(bad.path,after,sizeof(after))==n && !memcmp(before,after,n));
    }
    fx3_global_guard reuse={.fd=-1};cache_context c={0};
    assert(recover(&bad,&reuse,&c,bad.policy.previous_nonce,"new-fixture-grant")==G_STALE && !c.calls);
    reuse=(fx3_global_guard){.fd=-1};assert(recover(&bad,&reuse,&c,nonce,"old-fixture-grant")==G_STALE && !c.calls);
    groups++;
    seed live=make_seed(argv[1],"live-old-owner",0);fx3_global_guard busy={.fd=-1};c=(cache_context){0};
    assert(recover(&live,&busy,&c,nonce,"new-fixture-grant")==G_BUSY && !c.calls);
    release_child(&live.owner);busy=(fx3_global_guard){.fd=-1};
    assert(recover(&live,&busy,&c,nonce,"new-fixture-grant")==G_STALE && !c.calls);
    release_child(&live.observer);groups++;
    seed crash=make_seed(argv[1],"crash-after-recovery-record",0);release_child(&crash.owner);release_child(&crash.observer);
    n=read_file(crash.path,before,sizeof(before));fx3_guard_fixture_stop_after_recovered(1);
    fx3_global_guard g={.fd=-1};c=(cache_context){0};assert(recover(&crash,&g,&c,nonce,"new-fixture-grant")==G_IO);
    fx3_guard_fixture_stop_after_recovered(0);assert(read_file(crash.path,after,sizeof(after))==n+256 && !memcmp(before,after,n));
    g=(fx3_global_guard){.fd=-1};assert(fx3_global_begin(&g,crash.path,(uint32_t)getuid(),nonce,"next")==G_STALE);
    g=(fx3_global_guard){.fd=-1};c=(cache_context){0};assert(recover(&crash,&g,&c,nonce,"next")==G_STALE && !c.calls);groups++;
    seed torn=make_seed(argv[1],"torn-tail",0);release_child(&torn.owner);release_child(&torn.observer);
    int fd=open(torn.path,O_WRONLY|O_APPEND);assert(fd>=0 && write(fd,"x",1)==1);close(fd);
    g=(fx3_global_guard){.fd=-1};assert(fx3_global_begin(&g,torn.path,(uint32_t)getuid(),nonce,"next")==G_INVALID);
    g=(fx3_global_guard){.fd=-1};c=(cache_context){0};assert(recover(&torn,&g,&c,nonce,"next")==G_INVALID && !c.calls);groups++;
    char historical_path[4096];assert(snprintf(historical_path,sizeof(historical_path),"%s/historical-scope-reuse.journal",argv[1])>0);
    g=(fx3_global_guard){.fd=-1};assert(fx3_global_begin(&g,historical_path,(uint32_t)getuid(),nonce,"new-fixture-grant")==G_OK);
    assert(fx3_global_finish(&g,1)==G_OK);
    seed historical=make_seed(argv[1],"historical-scope-reuse",0);release_child(&historical.owner);release_child(&historical.observer);
    n=read_file(historical.path,before,sizeof(before));uint8_t other_nonce[16];memset(other_nonce,'C',16);
    g=(fx3_global_guard){.fd=-1};c=(cache_context){0};assert(recover(&historical,&g,&c,other_nonce,"new-fixture-grant")==G_STALE && !c.calls);
    g=(fx3_global_guard){.fd=-1};assert(recover(&historical,&g,&c,nonce,"unused-next-grant")==G_STALE && !c.calls);
    assert(read_file(historical.path,after,sizeof(after))==n && !memcmp(before,after,n));groups++;
    printf("{\"groups\":%u,\"bad_cache_variants\":12,\"old_prefix_unchanged\":true,\"camera_and_root_operations\":0}\n",groups);
    return 0;
}
