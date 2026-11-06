#ifndef FX3_HOST_TRANSPORT_H
#define FX3_HOST_TRANSPORT_H
#include <stdint.h>
#include <stddef.h>
#include <stdatomic.h>
/* Private local stream configuration only. No hardware pointers or handles. */
typedef struct {
    const char *path;
    uint32_t peer_uid,peer_pid;
    uint64_t peer_sec,peer_usec,deadline_ns,generation;
    uint8_t nonce[16];
    uint32_t scope;
    int fd;
#ifdef FX3_OWNER_CHANNEL_FIXTURE
    void (*before_request)(void *);
    void *fixture;
#endif
} fx3_channel_config;
typedef struct {
    uint32_t phase,uid,pid;
    uint64_t sec,usec;
    const uint8_t *nonce;
    const char *grant;
    int32_t native_return,guard_return;
    uint32_t frame_failed,ran;
} fx3_receipt_meta;
int fx3_channel_peer(const fx3_channel_config *);
int fx3_channel_connect(fx3_channel_config *);
int fx3_receipt_peer_ack(const fx3_channel_config *,uint64_t);
int fx3_receipt_send_bytes(const fx3_channel_config *,const uint8_t *,size_t,uint64_t);
#endif
