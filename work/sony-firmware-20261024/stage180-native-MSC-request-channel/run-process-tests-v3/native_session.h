#ifndef FX3_NATIVE_MSC_SESSION_H
#define FX3_NATIVE_MSC_SESSION_H
#include "../stage179-bounded-IOKit-wire/iokit_wire.h"
#define FX3_REQUEST_BYTES 572u
#define FX3_RESPONSE_BYTES 676u
#define FX3_REQUEST_MAGIC 0x31385146u
#define FX3_RESPONSE_MAGIC 0x52385146u
enum { FX3S_OK,FX3S_DENIED,FX3S_BAD_FRAME,FX3S_PEER_LOST,FX3S_INCOMPLETE,FX3S_NATIVE_ERROR,FX3S_PROTOCOL_ERROR,FX3S_CLOSED,FX3S_PENDING };
enum { FX3S_OBSERVE=1,FX3S_START,FX3S_AUTH,FX3S_STOP,FX3S_END,FX3S_STATUS };
typedef struct {
    uint32_t magic;
    fx3_io_context *wire;
    uint64_t generation,deadline_ns,last_id;
    uint8_t nonce[16];
    uint32_t started,stopped,failed,hard,ended,exchanges,next_command,family,round,complete,requests;
    _Atomic uint32_t busy;
    int (*peer_ok)(void *);
    uint64_t (*clock_ns)(void *);
    void *environment;
} fx3_native_session;
int fx3_session_init(fx3_native_session *,fx3_io_context *,const uint8_t *,uint64_t,
                     int (*)(void *),uint64_t (*)(void *),void *);
int fx3_session_dispatch(fx3_native_session *,const uint8_t *,uint32_t,uint8_t *);
int fx3_session_finish_host(fx3_native_session *);
#endif
