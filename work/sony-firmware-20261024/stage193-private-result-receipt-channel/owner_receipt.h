#ifndef FX3_OWNER_RECEIPT_H
#define FX3_OWNER_RECEIPT_H
#include "owner_channel.h"
#define FX3_RECEIPT_BYTES 1024u
enum { FX3_RECEIPT_COMPLETE=1, FX3_RECEIPT_HELD=2 };
typedef struct {
    uint32_t phase,uid,pid;
    uint64_t sec,usec;
    const uint8_t *nonce;
    const char *grant;
    int32_t native_return,guard_return;
    uint32_t frame_failed,ran;
} fx3_receipt_meta;
/* Only private entry state is accepted. No frame/file flag authorizes cleanup. */
int fx3_receipt_send(const fx3_channel_config *,const fx3_receipt_meta *,const fx3_owner_result *,uint64_t);
int fx3_receipt_peer_ack(const fx3_channel_config *,uint64_t);
#endif
