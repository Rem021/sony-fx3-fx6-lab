/* Raw frame is fsynced privately before it is sent on the verified peer.
 * No payload, challenge, digest material or raw serial enters this record. */
#include "service_flow.h"
#include "entry_shared.h"
#include <CommonCrypto/CommonDigest.h>
#include <fcntl.h>
#include <string.h>
#include <unistd.h>
static fx3_flow_journal *current;
_Static_assert(sizeof(fx3_profile)==12,"descriptor receipt profile ABI");
void fx3_flow_install_journal(fx3_flow_journal *j){current=j;}
fx3_flow_journal *fx3_flow_current_journal(void){return current;}
static void p32(uint8_t *p,uint32_t n){for(unsigned i=0;i<4;i++)p[i]=(uint8_t)(n>>(i*8));}
static void p64(uint8_t *p,uint64_t n){p32(p,(uint32_t)n);p32(p+4,(uint32_t)(n>>32));}
int fx3_flow_journal_open(fx3_flow_journal *j,const fx3_channel_config *peer,const fx3_receipt_meta *m,const char *path){
    if(!j || !m || !m->nonce || !m->grant || !path || !fx3_channel_peer(peer))return -1;
    memset(j,0,sizeof(*j));j->fd=-1;j->peer=peer;j->uid=m->uid;j->pid=m->pid;j->sec=m->sec;j->usec=m->usec;
    memcpy(j->nonce,m->nonce,16);CC_SHA256(m->grant,(CC_LONG)strlen(m->grant),j->grant_hash);
    j->fd=open(path,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0400);return j->fd<0?-1:0;
}
int fx3_flow_emit(fx3_service_flow *f,uint32_t op,uint32_t point,const fx3_call *call){
    fx3_flow_journal *j=f->journal;
    if(!j || j->fd<0 || j->failed || j->sequence>=512 || !fx3_channel_peer(j->peer))return -1;
    /* Check cancellation before every native call, including OUT->IN. */
    if(point==0 && atomic_load(&f->control->stop_requested))return -1;
    if(point==0){atomic_store(&f->owner->wire_pending,op);if(op==1){atomic_store(&f->owner->vendor_attempted,1);f->owner->persistent_camera_or_vendor_commands=1;}}
    else if(point==1 && call && call->returned)atomic_store(&f->owner->wire_pending,0);
    uint8_t wire[516]={0},*p=wire+4;p32(wire,512);memcpy(p,"FX3FLOW2",8);p32(p+8,2);p32(p+12,point);
    p64(p+16,++j->sequence);p32(p+24,op);p32(p+28,call?(uint32_t)call->status:0);
    p32(p+32,j->uid);p32(p+36,j->pid);p64(p+40,j->sec);p64(p+48,j->usec);memcpy(p+56,j->nonce,16);memcpy(p+72,j->grant_hash,32);
    if(call){p32(p+104,call->returned);p32(p+108,call->count_known);p32(p+112,call->count);p32(p+116,(uint32_t)call->raw_return);}
    p32(p+120,atomic_load(&f->owner->wire_pending));p32(p+124,atomic_load(&f->owner->vendor_attempted));
    p32(p+128,f->route.phase);p32(p+132,f->taken);p32(p+136,f->normal_seen);p32(p+140,f->objects_disposed);p32(p+144,f->retained);p32(p+148,f->finished);p32(p+248,f->driver_returned);
    p64(p+152,f->route.generation);p64(p+160,f->current.registry_id);p32(p+168,f->current.location);p32(p+172,f->current.vid|((uint32_t)f->current.pid<<16));memcpy(p+176,f->current.body_tag,32);
    p32(p+208,f->read.bytes);p32(p+212,f->read.reply_valid);memcpy(p+216,f->read.opaque_hmac,32);
    p32(p+252,f->service.control_only);p32(p+256,f->service.descriptor_length);p32(p+260,f->service.descriptor_copied);
    memcpy(p+264,f->service.descriptor_hash,32);memcpy(p+296,&f->service.observed_profile,sizeof(fx3_profile));
    p32(p+308,(uint32_t)f->service.acquire_policy_return);p32(p+312,f->service.configurations|((uint32_t)f->service.active_configuration<<8));
    memcpy(p+320,f->service.descriptor,128);
    memcpy(p+448,j->previous,32);CC_SHA256(p,480,p+480);
    size_t at=0;while(at<512){ssize_t n=write(j->fd,p+at,512-at);if(n<=0){j->failed=1;return -1;}at+=(size_t)n;}
    if(fsync(j->fd)){j->failed=1;return -1;}
    memcpy(j->previous,p+480,32);
    if(fx3_receipt_send_bytes(j->peer,wire,sizeof(wire),j->peer->deadline_ns)){j->failed=1;return -1;}
    return 0;
}
int fx3_flow_journal_close(fx3_flow_journal *j){
    if(!j || j->fd<0)return -1;int rc=fsync(j->fd);if(close(j->fd))rc=-1;j->fd=-1;return rc || j->failed?-1:0;
}
