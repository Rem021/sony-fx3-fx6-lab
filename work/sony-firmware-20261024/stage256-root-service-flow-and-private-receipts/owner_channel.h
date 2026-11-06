#ifndef FX3_OWNER_CHANNEL_H
#define FX3_OWNER_CHANNEL_H
#include "owner_trial.h"
#include "native_session.h"
/* Shared base protocol is the HOST_ONLY transport validated in246. */
#include "host_transport.h"
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
