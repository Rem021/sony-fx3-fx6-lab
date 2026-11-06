#ifndef FX3_GLOBAL_GUARD_H
#define FX3_GLOBAL_GUARD_H
#include <stdint.h>
#include <sys/types.h>
#include <sys/stat.h>
enum {G_OK=0,G_BUSY,G_INVALID,G_STALE,G_IO,G_FULL};
enum {G_OWNED=1,G_CLEAN=2,G_UNKNOWN=3,G_MANUALLY_RECOVERED=4};
#define FX3_GUARD_RECORD 256u
#define FX3_GUARD_LIMIT 2048u
#define FX3_RECOVERY_FRESH_NS 2000000000ull
typedef struct {
    int fd;struct stat identity;
    uint8_t last[FX3_GUARD_RECORD];
    uint32_t count,started;
    uint32_t uid,pid;uint64_t sec,usec;
    uint8_t nonce[16],grant[32];
} fx3_global_guard;
typedef struct {uint32_t pid,uid;uint64_t sec,usec;} fx3_guard_actor;
typedef struct {
    fx3_guard_actor previous_owner,previous_observer;
    uint8_t previous_nonce[16],previous_grant_hash[32];
    uint8_t prior_body_tag[32],fixed_evidence_digest[32];
    uint64_t prior_source_node,new_source_node,physical_port;
    uint32_t location;
} fx3_recovery_policy;
typedef struct {
    uint64_t registry_id,physical_port,observed_ns;
    uint32_t location,unique_count,storage_driver_count,mounted_count,media_unknown,media_count;
    uint16_t vid,pid;
    uint8_t body_tag[32];
} fx3_recovery_cache;
/* The callback must be a reviewed private root implementation which queries
 * fresh host caches itself. User files/booleans are not a substitute. */
typedef int (*fx3_recovery_verify)(void *,fx3_recovery_cache *);
int fx3_global_begin(fx3_global_guard *,const char *,uint32_t,const uint8_t *,const char *);
int fx3_global_begin_recovered(fx3_global_guard *,const char *,uint32_t,const uint8_t *,const char *,
    const fx3_recovery_policy *,fx3_recovery_verify,void *);
int fx3_global_finish(fx3_global_guard *,int);
#ifdef FX3_ENTRY_FIXTURE
void fx3_guard_fixture_stop_after_recovered(int);
#endif
#endif
