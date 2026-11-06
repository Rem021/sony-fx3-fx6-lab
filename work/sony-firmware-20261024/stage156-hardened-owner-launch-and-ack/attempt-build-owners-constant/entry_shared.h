#ifndef FX3_ENTRY_SHARED_H
#define FX3_ENTRY_SHARED_H
#include "owner_trial.h"
#define FX3_ENTRY_SCHEMA 2u
#define FX3_ENTRY_SCOPE 0x55534231u
#define FX3_ENTRY_BLOCK_BYTES 4096u
typedef struct {
    uint32_t schema,mode,owner_uid,scope;
    uint8_t nonce[16],privacy_key[32],expected_body_tag[32];
    _Atomic uint32_t attempt_claimed,native_started,native_completed;
    uint32_t native_pid;
    uint64_t birth_sec,birth_usec,started_ns,work_deadline_ns,final_deadline_ns;
    int32_t native_return;
    uint32_t fixture_fail,fixture_option,fixture_block;
    uint8_t fixture_observed_tag[32],result_sha256[32];
    uint32_t observer_pid;
    uint64_t observer_birth_sec,observer_birth_usec;
    _Atomic uint32_t helper_ready,parent_ack;
} fx3_entry_grant;
typedef struct {
    fx3_owner_control control;
    fx3_owner_result result;
    fx3_fixture_gate gate;
    fx3_entry_grant grant;
} fx3_entry_frame;
uint32_t fx3_entry_layout(uint32_t);
int fx3_entry_init(void *,size_t,uint32_t,uint32_t,const uint8_t *,const uint8_t *,const uint8_t *);
int fx3_entry_claim(void *,const uint8_t *);
int fx3_entry_pid_info(uint32_t,uint32_t *,uint64_t *,uint64_t *);
uint64_t fx3_entry_clock_ns(void);
uint32_t fx3_entry_ready(void *);
void fx3_entry_ack(void *);
int fx3_entry_pid_path(uint32_t,char *,uint32_t);
int fx3_ipc_init(void *,size_t);
int fx3_ipc_install_handlers(void *);
int fx3_owner_run(const fx3_owner_config *,fx3_owner_result *,fx3_owner_control *);
#endif
