#ifndef FX3_NATIVE_TRANSITION_STREAM_H
#define FX3_NATIVE_TRANSITION_STREAM_H
#include <stdint.h>
#include <stdatomic.h>
#define FX3_MODE_MSC 1u
#define FX3_MODE_SERVICE 2u
enum { FX3T_OK=0,FX3T_DENIED,FX3T_BUSY,FX3T_STALL,FX3T_TIMEOUT,FX3T_GONE,FX3T_IO,FX3T_SHAPE,FX3T_UNKNOWN };
typedef struct {
    uint64_t registry_id;
    uint32_t location;
    uint16_t vid,pid;
    uint8_t body_tag[32];
} fx3_identity;
typedef struct {
    uint8_t number,alternate,cls,subclass,protocol,endpoints,in_address,out_address;
    uint16_t max_packet;
    uint8_t pipe_in,pipe_out;
} fx3_profile;
typedef struct {
    int status;
    int32_t raw_return;
    uint32_t returned,count_known,count;
} fx3_call;
typedef struct {
    uint64_t (*now_ns)(void *);
    fx3_call (*control)(void *,const uint8_t [8],uint32_t);
    fx3_call (*write)(void *,const uint8_t *,uint32_t,uint32_t);
    fx3_call (*read)(void *,uint8_t *,uint32_t,uint32_t);
    fx3_call (*dispose)(void *);
} fx3_stream_ops;
typedef struct {
    uint32_t initialized,phase,active,failed,return_attempted,return_api_attempted;
    _Atomic uint32_t return_pending;
    uint64_t generation,used_registry[3];
    fx3_identity initial;
} fx3_route;
typedef struct {
    fx3_route *route;
    fx3_stream_ops ops;
    void *backend;
    fx3_identity identity;
    uint64_t generation,deadline_ns,last_now;
    uint32_t mode,started,stop_attempted,exchange_finished,read_attempted;
    uint32_t next_command,round,family,failed,native_calls,dispose_attempted,unreturned;
    _Atomic uint32_t busy;
    fx3_call last_call;
    uint32_t acquire_step;
    int32_t acquire_raw_return;
    int acquire_policy_return;
    int (*audit)(void *,uint32_t,uint32_t,const fx3_call *);
    void *audit_context;
    uint32_t control_only,descriptor_length,descriptor_copied;
    uint8_t descriptor[128],descriptor_hash[32],configurations,active_configuration;
    fx3_profile observed_profile;
} fx3_stream;
typedef struct {
    uint32_t bytes,reply_valid,table_AB_capability,authentication_proven,camera_threads_proven;
    uint8_t opaque_hmac[32];
} fx3_read_receipt;
int fx3_route_init(fx3_route *,const fx3_identity *);
int fx3_route_candidate(const fx3_route *,const fx3_identity *,uint32_t);
int fx3_stream_bind(fx3_route *,fx3_stream *,const fx3_identity *,uint32_t,uint64_t,const fx3_stream_ops *,void *);
/* Native acquisition holds the ordinary I/O/disposal lock until it returns. */
int fx3_stream_bind_acquiring(fx3_route *,fx3_stream *,const fx3_identity *,uint32_t,uint64_t,const fx3_stream_ops *,void *);
int fx3_stream_start(fx3_stream *);
int fx3_stream_auth(fx3_stream *,const uint8_t [516],uint8_t [516]);
/* Native, mode-specific fixed7-exchange driver. FX3T_OK means observed exchange
 * finished, not verified authorization, thread exit or package admission. */
int fx3_stream_exchange_fixed(fx3_stream *);
int fx3_stream_read0(fx3_stream *,const uint8_t [32],fx3_read_receipt *);
int fx3_stream_stop(fx3_stream *);
/* Only a matched SERVICE control lease with no SERVICE START or auth.
 * This separate call does not fabricate a completed service exchange. */
int fx3_stream_control_end(fx3_stream *);
/* Dispose native objects under the same lock used for I/O. Disposal is a
 * host-object statement, never camera-thread proof. One attempt only. */
int fx3_stream_retire(fx3_stream *);
int fx3_route_observe_return(fx3_route *,const fx3_identity *);
#endif
