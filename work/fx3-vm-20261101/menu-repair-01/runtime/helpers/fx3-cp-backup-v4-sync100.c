/* AP88 software-only CP Backup endpoint: exact audited reset33/F1,F4. */
typedef unsigned long size_t;
extern int printk(const char*,...);
struct cp_entry;static void cp_item_trace(const struct cp_entry*,unsigned,int);
#define CP_ITEM_TRACE(e,f,c) cp_item_trace(e,f,c)
#include "fx3-cp-backup-reset-core-v2-sync100.h"
#include "fx3-cp-backup-profile-v1.h"
extern int osal_reg_public(const void*),osal_unreg_public(void);
extern W osal_msg_size(const void*),osal_get_msg_src(const void*);
extern int osal_valloc_msg_wait(W,void**,W,W),osal_snd_msg(W,void*),osal_free_msg(W,void*);
extern void osal_set_msg_src(void*,W);
extern void *arch_phys_to_va(U),*vmalloc(U);extern void vfree(void*);
#include "fx3-date98-trace-core-v1.h"
static B *backing,*work,*rollback;static unsigned registered,stage,unknowns,postunknowns,attempts,initialized,poisoned;static unsigned char busy;static U expected_digest;static B pending[40];static W pending_Q;static unsigned pending_valid;
static void cp_item_trace(const struct cp_entry*e,W flag,int changed){printk("FX3_BACKUP_CP_RESET_ITEM flag=%u key=%#x attr=%#x offset=%#x size=%u unit=%u repeat=%u copies=%u default_offset=%#x changed=%u copied_and_readback=1 software_CP_profile=1\n",flag,e->key,e->attribute,e->offset,e->size,e->unit,e->repeat,e->copies,e->default_offset,changed);}
static int cp_setup(void){if(initialized)return 0;backing=arch_phys_to_va(CP_BANK_PHYS);if(!backing||cp_validate(backing,1)||cp_digest(backing,CP_BANK_BYTES)!=CP_SEED_FNV64)return -7;work=vmalloc(CP_BANK_BYTES);rollback=vmalloc(CP_BANK_BYTES);if(!work||!rollback){if(work)vfree(work);if(rollback)vfree(rollback);work=rollback=0;return -7;}expected_digest=CP_SEED_FNV64;initialized=1;printk("FX3_BACKUP_CP_STORAGE physical=%#lx bytes=%u bank_offset=0xd2000 separate_CP_profile=1 native_CP_address_binding_unproven=1 first_AP_bank_untouched=1 initial_sha256=%s checksum_verified=1 index_all_validated=1 repeat=4 epoch=1 save_to_disk=0\n",CP_BANK_PHYS,CP_BANK_BYTES,CP_SEED_SHA256);return 0;}
static void cp_raw(const char*kind,W dst,const void*message,W n){const B*b=message;char raw[81];const char*hex="0123456789abcdef";W len=n<40?n:40;for(W i=0;i<len;i++){raw[2*i]=hex[b[i]>>4];raw[2*i+1]=hex[b[i]&15];}raw[2*len]=0;printk("FX3_BACKUP_CP_%s destination=%#x logical_bytes=%u captured=%u raw=%s epoch=1\n",kind,dst,n,len,raw);}
static int cp_schema(W dst,const void*message,W*Q,W*F){if(dst!=0x903e0811U||!message||osal_msg_size(message)!=40)return -7;const B*p=message;W q=rd32(p+12);if(rd32(p)!=0x33||rd32(p+4)||rd32(p+8)!=dst||(q&0xffff0000U)!=0x803e0000U||!(q&0x7fffU)||(q&0x8000U)||osal_get_msg_src(message)!=q||rd32(p+16)!=1||rd32(p+20)!=1||rd32(p+24)!=2||rd32(p+28)||rd32(p+32)!=2)return -7;
 const B*h=p-24;if(h[8]!=2||(h[9]&64)==0||rd16(h+10)!=1||rd32(h+12)!=q||rd32(h+16)!=40||rd32(h+20)!=0x55555555||rd32(p+40)!=0x77777777)return -7;*Q=q;*F=rd32(p+36);return 0;}
static void date98_kernel_capture(W dst,void *message,W n){B raw[44];cp_copy(raw,message,44);char text[89];const char *h="0123456789abcdef";for(W i=0;i<44;i++){text[i*2]=h[raw[i]>>4];text[i*2+1]=h[raw[i]&15];}text[88]=0;B *page=arch_phys_to_va(DATE98_PHYS);B *r=page&&d98_init(page,DATE98_SPAN)?d98_begin(page,2,0,0,dst,n,(U)message,(U)__builtin_return_address(0),raw,1,3,0,0):0;printk("FX3_DATE98_CP_DISPATCH destination=%#x source=%#x pointer=%p bytes=44 raw=%s no_reply=1 no_free=1 original_absent_route_return=0 unchanged=1\n",dst,osal_get_msg_src(message),message,text);d98_end(r,0,0,0,0,0,0,0,0);}
static int cp_reset_send_backup100_prior(W dst,void*message){W n=message?osal_msg_size(message):0;if(dst==0x909005c5U&&message&&n==44)date98_kernel_capture(dst,message,n);if(dst!=0x903e0811U||!message||n<4||rd32(message)!=0x33){if(message&&__atomic_add_fetch(stage>=2?&postunknowns:&unknowns,1,__ATOMIC_RELAXED)<=(stage>=2?128U:16U)){cp_raw("UNHANDLED",dst,message,n);if(stage>=2&&n<=4096){const B*b=message;const char*hx="0123456789abcdef";for(W at=0;at<n;at+=64){W k=n-at<64?n-at:64;char raw[129];for(W j=0;j<k;j++){raw[j*2]=hx[b[at+j]>>4];raw[j*2+1]=hx[b[at+j]&15];}raw[k*2]=0;printk("FX3_BACKUP_CP_POST_RESET_RAW index=%u destination=%#x source=%#x bytes=%u offset=%u captured=%u raw=%s stage=%u no_reply=1\n",postunknowns,dst,osal_get_msg_src(message),n,at,k,raw,stage);}}printk("FX3_BACKUP_CP_UNHANDLED_SOURCE destination=%#x source=%#x no_reply=1 no_free=1 prior_absent_route_return=0 stage=%u terminal_unproven=1\n",dst,osal_get_msg_src(message),stage);}return 0;}
 W Q=0,F=0;cp_raw("REQUEST",dst,message,n);if(cp_schema(dst,message,&Q,&F)){printk("FX3_BACKUP_CP_REJECT reason=schema no_success=1 no_free=1\n");return -7;}
 if(__atomic_test_and_set(&busy,__ATOMIC_ACQUIRE)){printk("FX3_BACKUP_CP_REJECT reason=concurrent no_success=1 no_free=1\n");return -7;}
 int rc=-7;void*reply=0;struct cp_stats st={0};attempts++;
 if(poisoned||stage>1||F!=(stage==0?1U:4U)){printk("FX3_BACKUP_CP_REJECT reason=order flag=%u stage=%u no_success=1 no_free=1\n",F,stage);goto out;}
 if(pending_valid&&(pending_Q!=Q||!cp_equal(pending,message,40))){printk("FX3_BACKUP_CP_REJECT reason=retry_identity no_success=1 no_free=1\n");goto out;}
 if(!pending_valid){cp_copy(pending,message,40);pending_Q=Q;pending_valid=1;}
 if(cp_setup()||cp_digest(backing,CP_BANK_BYTES)!=expected_digest){printk("FX3_BACKUP_CP_REJECT reason=storage_identity no_success=1 no_free=1\n");goto out;}
 cp_copy(rollback,backing,CP_BANK_BYTES);cp_copy(work,backing,CP_BANK_BYTES);
 if(cp_reset(work,F,&st)){printk("FX3_BACKUP_CP_REJECT reason=reset_validation no_success=1 storage_unchanged=1\n");goto out;}
 /* AP pool accounting uses the actual originating native Q. Source identifies
    the modeled CP; there is no running CP allocator/address space. */
 rc=osal_valloc_msg_wait(Q,&reply,4096,0);if(rc||!reply){printk("FX3_BACKUP_CP_RETRY flag=%u reason=reply_alloc result=%d stage=%u rollback=unchanged\n",F,rc,stage);rc=-7;goto out;}
 if(osal_msg_size(reply)!=4096){osal_free_msg(Q,reply);reply=0;rc=-7;goto out;}
 for(W i=0;i<4096;i++)((B*)reply)[i]=0;cp_copy(reply,message,40);wr32((B*)reply+4,0);osal_set_msg_src(reply,0x003e0811);
 cp_copy(backing,work,CP_BANK_BYTES);if(!cp_equal(backing,work,CP_BANK_BYTES)){cp_copy(backing,rollback,CP_BANK_BYTES);rc=-7;goto fail_reply;}
 __atomic_thread_fence(__ATOMIC_SEQ_CST);rc=osal_snd_msg(Q,reply);
 if(rc){cp_copy(backing,rollback,CP_BANK_BYTES);if(!cp_equal(backing,rollback,CP_BANK_BYTES))poisoned=1;printk("FX3_BACKUP_CP_RETRY flag=%u reason=reply_send result=%d stage=%u rollback_verified=%u\n",F,rc,stage,!poisoned);goto fail_reply;}
 /* Reply is native queue owned after successful send; never read/free it here. */
 reply=0;expected_digest=st.after;stage++;pending_valid=0;int freed=osal_free_msg(dst,message);if(freed)poisoned=1;
 printk("FX3_BACKUP_CP_COMMIT flag=%u stage=%u Q=%#x reply_source=0x003e0811 request_metadata=40 request_allocation=128 request_capacity=60 reply_metadata=4096 initialized_copy=40 tail_zeroed=4056 opaque_tail_software_difference=1 reply_allocator_accounting=actual_AP_Q request_free_accounting=original_destination selected=%u repeat_items=%u copies=%u changed=%u before_fnv64=%#lx after_fnv64=%#lx actual_copy_and_readback=1 reply_send_result=0 request_free_result=%d software_CP_profile=1 original_CP_executed=0 epoch=1\n",F,stage,Q,st.selected,st.repeat_items,st.copies,st.changed,st.before,st.after,freed);
 rc=0;goto out;
 fail_reply:if(reply){int fr=osal_free_msg(Q,reply);if(fr)poisoned=1;reply=0;}if(!rc)rc=-7;
 out:__atomic_clear(&busy,__ATOMIC_RELEASE);return rc;
}
#include "fx3-date99-consumer-v1.h"
static int sync100_route(W,void*);
static int cp_reset_send99(W dst,void*p){return dst==DATE99_DEST?date99_accept(dst,p):sync100_route(dst,p);}
#include "fx3-backup-sync100-v1.h"
static const struct{int(*send)(W,void*);void*sync;}owner={cp_reset_send99,0};
int init_module(void){int rc=sync100_start();if(rc)return rc;rc=date99_start();if(rc){sync100_stop();return rc;}rc=osal_reg_public(&owner);if(!rc){registered=1;printk("FX3_DATE99_CONSUMER_BOUND only_ready44=1 synthetic_cp_clock=1 original_CP=0 original_AP_clock_and_Backup_unchanged=1 dynamic_replyQ=1 source_chip1=1 reason4_no_done=1\n");printk("FX3_DATE98_KERNEL_OBSERVE_READY consumer99_replaces_passive_target=0x909005c5 original_other_destinations_unchanged=1\n");}else {date99_stop();sync100_stop();}printk("FX3_BACKUP_CP_PUBLIC_OWNER exact_reset33=1 F1_then_F4_once=1 result=%d standard_native_registration=1 sync_null_preserves_prior_route=1 software_CP_executed=0\n",rc);return rc;}
void cleanup_module(void){if(registered){osal_unreg_public();registered=0;}date99_stop();sync100_stop();if(work)vfree(work);if(rollback)vfree(rollback);work=rollback=backing=0;}
