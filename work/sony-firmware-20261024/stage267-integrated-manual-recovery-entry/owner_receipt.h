#ifndef FX3_OWNER_RECEIPT_H
#define FX3_OWNER_RECEIPT_H
#include "owner_channel.h"
#define FX3_RECEIPT_BYTES 1024u
enum { FX3_RECEIPT_COMPLETE=1, FX3_RECEIPT_HELD=2, FX3_RECEIPT_IDLE_HELD_EXIT=3 };
/* Only private entry state is accepted. No frame/file flag authorizes cleanup. */
int fx3_receipt_send(const fx3_channel_config *,const fx3_receipt_meta *,const fx3_owner_result *,uint64_t);
int fx3_receipt_peer_ack(const fx3_channel_config *,uint64_t);
int fx3_receipt_send_bytes(const fx3_channel_config *,const uint8_t *,size_t,uint64_t);
#endif
