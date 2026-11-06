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
static void put32(uint8_t *p,uint32_t x) {for(unsigned i=0;i<4;++i)p[i]=(uint8_t)(x>>(i*8));}
static void put64(uint8_t *p,uint64_t x) {for(unsigned i=0;i<8;++i)p[i]=(uint8_t)(x>>(i*8));}
int fx3_receipt_peer_ack(const fx3_channel_config *peer,uint64_t deadline) {
    if(!peer)return -1;
    uint8_t data[24]={0};size_t at=0;
    while(at<sizeof(data)) {
        uint64_t now=fx3_entry_clock_ns();if(!now || now>=deadline || !fx3_channel_peer(peer))return -1;
        union {struct cmsghdr align;uint8_t bytes[CMSG_SPACE(512*sizeof(int))];} control={0};
        struct iovec io={data+at,1};
        struct msghdr msg={.msg_iov=&io,.msg_iovlen=1,.msg_control=control.bytes,.msg_controllen=sizeof(control.bytes)};
        ssize_t n=recvmsg(peer->fd,&msg,MSG_DONTWAIT);
        if(n<0 && (errno==EAGAIN || errno==EINTR)) {
            struct pollfd ready={.fd=peer->fd,.events=POLLIN};
            int rc=poll(&ready,1,10);
            if(rc<0 && errno!=EINTR)return -1;
            continue;
        }
        int reject=msg.msg_controllen!=0 || (msg.msg_flags&(MSG_TRUNC|MSG_CTRUNC));
        for(struct cmsghdr *c=CMSG_FIRSTHDR(&msg);c;c=CMSG_NXTHDR(&msg,c)) {
            size_t available=(size_t)((uint8_t *)msg.msg_control+msg.msg_controllen-(uint8_t *)c);
            if(available<sizeof(*c) || c->cmsg_len<CMSG_LEN(0))return -1;
            size_t total=c->cmsg_len<available?c->cmsg_len:available;
            if(c->cmsg_level==SOL_SOCKET && c->cmsg_type==SCM_RIGHTS && total>=CMSG_LEN(0)) {
                size_t bytes=total-CMSG_LEN(0);
                for(size_t k=0;k+sizeof(int)<=bytes;k+=sizeof(int)) {
                    int fd=-1;memcpy(&fd,(uint8_t *)CMSG_DATA(c)+k,sizeof(fd));if(fd>=0)close(fd);
                }
            }
            if(c->cmsg_len>available)return -1;
        }
        if(reject || n!=1)return -1;
        at+=(size_t)n;
    }
    return memcmp(data,"FX3ACK01",8) || memcmp(data+8,peer->nonce,16)?-1:0;
}
int fx3_receipt_send(const fx3_channel_config *peer,const fx3_receipt_meta *m,const fx3_owner_result *r,uint64_t deadline) {
    if(!peer || !m || !r || !m->nonce || !m->grant || !m->pid || !m->sec || m->usec>=1000000 ||
       m->phase<FX3_RECEIPT_COMPLETE || m->phase>FX3_RECEIPT_HELD || m->frame_failed>1 || m->ran>1 ||
       r->abi!=FX3_OWNER_ABI || r->event_count>FX3_OWNER_EVENTS)return -1;
    uint8_t frame[FX3_RECEIPT_BYTES+4]={0},*p=frame+4;
    put32(frame,FX3_RECEIPT_BYTES);memcpy(p,"FX3RCPT1",8);
    put32(p+8,1);put32(p+12,m->phase);put32(p+16,FX3_RECEIPT_BYTES);put32(p+20,FX3_OWNER_ABI);
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
    CC_SHA256(p+160,sizeof(*r),p+120);CC_SHA256(p,992,p+992);
    return fx3_receipt_send_bytes(peer,frame,sizeof(frame),deadline);
}
int fx3_receipt_send_bytes(const fx3_channel_config *peer,const uint8_t *frame,size_t bytes,uint64_t deadline) {
    if(!peer || !frame || !bytes || bytes>1028)return -1;
    size_t at=0;
    while(at<bytes) {
        uint64_t now=fx3_entry_clock_ns();
        if(!now || now>=deadline || !fx3_channel_peer(peer))return -1;
        struct pollfd ready={.fd=peer->fd,.events=POLLOUT};
        uint64_t remain=(deadline-now+999999)/1000000;
        int n=poll(&ready,1,remain>20?20:(int)remain);
        if(n<0 && errno==EINTR)continue;
        if(n<0 || ready.revents&(POLLHUP|POLLERR|POLLNVAL))return -1;
        if(!n || !(ready.revents&POLLOUT))continue;
        ssize_t sent=send(peer->fd,frame+at,bytes-at,MSG_DONTWAIT);
        if(sent<0 && (errno==EAGAIN || errno==EINTR))continue;
        if(sent<=0)return -1;
        at+=(size_t)sent;
    }
    return 0; /* Delivery is not a camera completion or a release permission. */
}
