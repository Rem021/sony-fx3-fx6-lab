#ifndef FX3_OWNER_CHANNEL_H
#define FX3_OWNER_CHANNEL_H
#include "owner_trial.h"
#include "native_session.h"
/* Private root-side config; never serialized or imported from a request. */
typedef struct {
    const char *path;
    uint32_t peer_uid,peer_pid;
    uint64_t peer_sec,peer_usec,deadline_ns,generation;
    uint8_t nonce[16];
    uint32_t scope; /* 1=observe/status/end only; 2=bounded MSC (fixture only). */
    int fd;
#ifdef FX3_OWNER_CHANNEL_FIXTURE
    void (*before_request)(void *);
    void *fixture;
#endif
} fx3_channel_config;
typedef struct {
    fx3_io_context wire;
    fx3_native_session session;
    fx3_channel_config config;
    fx3_owner_result *report;
    uint32_t initialized;
} fx3_channel_runtime;
int fx3_channel_peer(const fx3_channel_config *);
int fx3_channel_connect(fx3_channel_config *);
int fx3_channel_run(fx3_channel_runtime *,const fx3_channel_config *,const fx3_io_owner *,fx3_owner_result *);
int fx3_channel_cleanup_allowed(fx3_channel_runtime *);
int fx3_owner_run_with_channel(const fx3_owner_config *,fx3_owner_result *,fx3_owner_control *,const fx3_channel_config *);
#endif
