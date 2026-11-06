/* Result delivery on the already kernel-identified stream. No new connection,
 * device operation, cleanup, signal, retry of a trial, or privilege change. */
#include "owner_receipt.h"
#include "entry_shared.h"
#include <CommonCrypto/CommonDigest.h>
#include <errno.h>
#include <poll.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>
_Static_assert(__BYTE_ORDER__==__ORDER_LITTLE_ENDIAN__,"receipt v1 is little endian");
_Static_assert(sizeof(fx3_owner_result)==728,"receipt v1 result ABI");
_Static_assert(offsetof(fx3_owner_result,before)==56,"receipt v1 result offsets");
_Static_assert(sizeof(fx3_guard_recovery_stamp)==104,"recovery stamp wire capacity");
static void put32(uint8_t *p,uint32_t x) {for(unsigned i=0;i<4;++i)p[i]=(uint8_t)(x>>(i*8));}
static void put64(uint8_t *p,uint64_t x) {for(unsigned i=0;i<8;++i)p[i]=(uint8_t)(x>>(i*8));}
int fx3_receipt_send(const fx3_channel_config *peer,const fx3_receipt_meta *m,const fx3_owner_result *r,uint64_t deadline) {
    if(!peer || !m || !r || !m->nonce || !m->grant || !m->pid || !m->sec || m->usec>=1000000 ||
       m->phase<FX3_RECEIPT_COMPLETE || m->phase>FX3_RECEIPT_IDLE_HELD_EXIT || m->frame_failed>1 || m->ran>1 ||
       r->abi!=FX3_OWNER_ABI || r->event_count>FX3_OWNER_EVENTS)return -1;
    uint8_t frame[FX3_RECEIPT_BYTES+4]={0},*p=frame+4;
    put32(frame,FX3_RECEIPT_BYTES);memcpy(p,"FX3RCPT5",8);
    put32(p+8,5);put32(p+12,m->phase);put32(p+16,FX3_RECEIPT_BYTES);put32(p+20,FX3_OWNER_ABI);
    put32(p+24,m->uid);put32(p+28,m->pid);put64(p+32,m->sec);put64(p+40,m->usec);
    memcpy(p+48,m->nonce,16);CC_SHA256(m->grant,(CC_LONG)strlen(m->grant),p+64);
    put32(p+96,sizeof(*r));put32(p+100,(uint32_t)m->native_return);put32(p+104,(uint32_t)m->guard_return);
    put32(p+108,m->frame_failed);put32(p+112,m->ran);
    memcpy(p+160,r,sizeof(*r));
    /* All non-atomic fields are stable after core returned; atomic publication
     * fields are loaded explicitly, never interpreted through user storage. */
#define ATOMIC_FIELD(name) put32(p+160+offsetof(fx3_owner_result,name),atomic_load(&r->name))
    ATOMIC_FIELD(active_call_pending);ATOMIC_FIELD(owner_retained);ATOMIC_FIELD(session_state);
    ATOMIC_FIELD(wire_pending);ATOMIC_FIELD(vendor_attempted);
#undef ATOMIC_FIELD
    if(m->recovery && m->recovery->stage){
        const fx3_guard_recovery_stamp *s=m->recovery;
        if(s->schema!=1 || s->stage>2 || s->reserved)return -1;
        put32(p+888,s->schema);put32(p+892,s->stage);
        memcpy(p+896,s->prior_tail_hash,32);memcpy(p+928,s->recovered_hash,32);
        put64(p+960,s->source_node);put64(p+968,s->physical_port);put32(p+976,s->location);
        put64(p+984,s->before_count);
    }
    CC_SHA256(p+160,sizeof(*r),p+120);CC_SHA256(p,992,p+992);
    return fx3_receipt_send_bytes(peer,frame,sizeof(frame),deadline);
}
