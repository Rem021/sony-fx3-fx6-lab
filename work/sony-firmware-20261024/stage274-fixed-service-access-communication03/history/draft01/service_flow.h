#ifndef FX3_ROOT_SERVICE_FLOW_H
#define FX3_ROOT_SERVICE_FLOW_H
#include "stream.h"
#include "owner_trial.h"
#include "host_transport.h"
typedef struct fx3_service_flow fx3_service_flow;
typedef struct {
    int (*take_msc)(void *,fx3_service_flow *);
    int (*observe)(void *,fx3_service_flow *,uint32_t,fx3_identity *);
    int (*open_service)(void *,fx3_service_flow *,const fx3_identity *);
    fx3_call (*driver_return)(void *,fx3_service_flow *,const fx3_identity *);
    uint64_t (*now)(void *);
    void (*pause)(void *,uint32_t);
} fx3_flow_ops;
typedef struct {
    int fd,failed;
    uint32_t sequence,uid,pid;
    uint64_t sec,usec;
    uint8_t nonce[16],grant_hash[32],previous[32];
    const fx3_channel_config *peer;
} fx3_flow_journal;
struct fx3_service_flow {
    fx3_route route;
    fx3_stream msc,service;
    fx3_identity current;
    fx3_read_receipt read;
    fx3_flow_journal *journal;
    fx3_owner_result *owner;
    fx3_owner_control *control;
    uint64_t deadline;
    uint8_t key[32];
    uint32_t taken,retained,objects_disposed,normal_seen,driver_returned,finished;
};
int fx3_flow_journal_open(fx3_flow_journal *,const fx3_channel_config *,const fx3_receipt_meta *,const char *);
int fx3_flow_emit(fx3_service_flow *,uint32_t,uint32_t,const fx3_call *);
int fx3_flow_journal_close(fx3_flow_journal *);
void fx3_flow_install_journal(fx3_flow_journal *);
fx3_flow_journal *fx3_flow_current_journal(void);
int fx3_flow_run(fx3_service_flow *,const fx3_flow_ops *,void *);
#endif
