#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#define SYNC100_HOST_TEST 1
#define DATE99_NOW sync100_test_now
static unsigned long sync100_test_now(void){return 1000000000UL;}
static int copy_fault;static void corrupt_copy(unsigned char*p,unsigned long n){(void)n;if(copy_fault){p[0x30000]^=1;copy_fault=0;}}
#define SYNC100_AFTER_COPY corrupt_copy
#include "fx3-cp-backup-v5-native101.c"
static B*bank;static void*enqueued;static int alloc_fail,send_fail,patch_fail,cb_calls,fallback_calls;static W request_Q=0x803e61c2;static unsigned request_frees,reply_frees;static W apiwords[4]={0xb4000b00,0xa9bb7bfd,0x910003fd,0xa90153f3};
int printk(const char*f,...){(void)f;return 0;}
static B*msg(W n,W q){B*b=calloc(1,n+80);B*p=b+64;p[-16]=(B)(((n+131)&~63U)/64);p[-15]=65;p[-14]=1;wr32(p-12,q);wr32(p-8,n);wr32(p-4,0x55555555);wr32(p+n,0x77777777);return p;}
W osal_msg_size(const void*p){return rd32((B*)p-8);}W osal_get_msg_src(const void*p){return rd32((B*)p-12);}void osal_set_msg_src(void*p,W q){wr32((B*)p-12,q);}
int osal_valloc_msg_wait(W q,void**p,W n,W wait){assert(q==request_Q&&n==4096&&!wait);if(alloc_fail){*p=0;return -1023;}*p=msg(n,q);return 0;}
int osal_snd_msg(W q,void*p){assert(q==request_Q&&osal_msg_size(p)==4096&&osal_get_msg_src(p)==0x003e0811);assert(!rd32((B*)p+4));for(W i=40;i<4096;i++)assert(!((B*)p)[i]);if(send_fail)return -1021;assert(!enqueued);enqueued=p;return 0;}
int osal_free_msg(W q,void*p){if(osal_msg_size(p)==40){assert(q==0x903e0811);request_frees++;}else{assert(q==request_Q);reply_frees++;}free((B*)p-64);return 0;}
void*arch_phys_to_va(U p){assert(p==CP_BANK_PHYS);return bank;}void*vmalloc(U n){return malloc(n);}void vfree(void*p){free(p);}
int osal_reg_public(const void*p){assert(p==&owner);return 0;}int osal_unreg_public(void){return 0;}
int osal_dynamic_id(W op,W module,void*p){(void)module;static W i=1;if(op==0x32){*(W*)p=i++;return 0;}if(op==0x52)return 0;assert(0);return -1;}
int osal_wai_sem_tmo(W q,int t){(void)q;assert(t==-1);return 0;}int osal_sig_sem(W q){(void)q;return 0;}
int osal_create_waitable_thread(const void*i,void**p){assert(i==&date99_thread_info);*p=(void*)1;return 1;}int osal_wait_thread_exit(void*p){assert(p==(void*)1);return 0;}int osal_rcv_msg_tmo(W q,void**p,int t){(void)q;(void)p;(void)t;assert(0);return -1;}
static void callback(int status,void*context){assert(!status&&!context);assert(sync100_copied&&sync100_callback&&cp_equal(bank,work,CP_BANK_BYTES));cb_calls++;}
static int patch(void**a,W*words,int n){assert(n==4);for(int i=0;i<4;i++)assert((U)a[i]==0xffffff80083220c8UL+4*i);if(patch_fail){patch_fail=0;return -5;}memcpy(apiwords,words,16);return 0;}
U kallsyms_lookup_name(const char*n){if(!strcmp(n,"pcidma_transfer_async"))return 0xffffff80083220c8UL;if(!strcmp(n,"aarch64_insn_patch_text"))return (U)patch;if(!strcmp(n,"backupfile_cb_getcp"))return (U)callback;if(!strcmp(n,"backupfile_get_cp_data"))return 0x1000;return 0;}
int probe_kernel_read(void*d,const void*s,U n){if((U)s==0xffffff80083220c8UL)memcpy(d,apiwords,n);else memcpy(d,s,n);return 0;}
int sync100_native_fallback(void*p){fallback_calls++;return p?-13:-22;}
static B*request(W mode){W a[10]={0x30,0,0x903e0811,request_Q,1,1,1,1,mode,0};B*p=msg(40,request_Q);memcpy(p,a,40);return p;}
static void consume(W mode){assert(enqueued&&rd32((B*)enqueued+32)==mode);osal_free_msg(request_Q,enqueued);enqueued=0;}
static void wr64(B*p,U n){wr32(p,n);wr32(p+4,n>>32);}
static void descriptor(B*d){memset(d,0,40);d[1]=4;wr32(d+4,CP_BANK_BYTES);wr64(d+8,0x404000000UL);wr64(d+16,CP_BANK_PHYS);wr64(d+24,(U)callback);}
int main(int argc,char**argv){assert(argc==2);FILE*f=fopen(argv[1],"rb");assert(f);bank=malloc(CP_BANK_BYTES);assert(fread(bank,1,CP_BANK_BYTES,f)==CP_BANK_BYTES);fclose(f);assert(!cp_validate(bank,1));
 /* Binding failure never enables model; original bytes restored. */
 patch_fail=1;assert(sync100_start()==-7&&!sync100_enabled&&!sync100_hooked&&!sync100_gate);assert(apiwords[0]==0xb4000b00);
 assert(!init_module()&&registered&&sync100_enabled&&sync100_hooked);assert(apiwords[0]==0x58000050);
 B*reset=msg(40,request_Q);W rw[10]={0x33,0,0x903e0811,request_Q,1,1,2,0,2,1};memcpy(reset,rw,40);assert(!sync100_route(0x903e0811,reset)&&stage==1);consume(2);reset=msg(40,request_Q);rw[9]=4;memcpy(reset,rw,40);assert(!sync100_route(0x903e0811,reset)&&stage==2);consume(2);request_frees=reply_frees=0;
 B*p=request(0);assert(sync100_reply(0x903e0811,p)==-7&&!request_frees);free(p-64);
 for(unsigned i=0;i<10;i++){p=request(3);p[4*i]^=1;assert(sync100_reply(0x903e0811,p)==-7&&!sync100_active);free(p-64);}
 p=request(3);alloc_fail=1;assert(sync100_reply(0x903e0811,p)==-7&&!sync100_active&&bank[9]==1&&!request_frees);alloc_fail=0;send_fail=1;assert(sync100_reply(0x903e0811,p)==-1021&&!sync100_active&&bank[9]==1&&!request_frees);send_fail=0;
 assert(!sync100_reply(0x903e0811,p)&&sync100_active&&bank[9]==1&&request_frees==1);consume(1);B*d=calloc(1,64);descriptor(d);
 B*dup=request(3);assert(sync100_reply(0x903e0811,dup)==-7);free(dup-64);
 bank[0x30000]^=1;assert(bank[0x30000]!=work[0x30000]);assert(!sync100_dma_at(d,0x1090)&&bank[0x30000]==work[0x30000]&&cb_calls==1&&sync100_copied&&cp_equal(work,bank,CP_BANK_BYTES));assert(sync100_dma_at(d,0x1090)==-22&&cb_calls==1);
 /* A repeated descriptor is rejected, poisoning this epoch; unlock must not
    mask the failed copy path. Fresh next lock is still an independent epoch. */
 p=request(0);assert(sync100_reply(0x903e0811,p)==-7&&!sync100_active);free(p-64);
 p=request(3);assert(!sync100_reply(0x903e0811,p));consume(1);descriptor(d);assert(!sync100_dma_at(d,0x1090)&&cb_calls==2);p=request(0);send_fail=1;assert(sync100_reply(0x903e0811,p)==-1021&&sync100_active);send_fail=0;assert(!sync100_reply(0x903e0811,p)&&!sync100_active);consume(0);assert(bank[9]==1);
 /* Native checksum-only save is accepted, payload corruption is rejected. */
 W sum=0;for(U i=0;i<CP_BANK_BYTES;i++)if(i<32||i>=36)sum+=bank[i];wr32(bank+32,sum);assert(!sync100_storage());bank[0x30000]^=1;assert(sync100_storage()==-7);bank[0x30000]^=1;
 assert(sync100_dma_at(0,0x1234)==-22&&sync100_dma_at(d,0x1234)==-13&&fallback_calls==2);
 p=request(3);assert(!sync100_reply(0x903e0811,p));consume(1);descriptor(d);copy_fault=1;U before_copy_failure=cp_digest(bank,CP_BANK_BYTES);int callbacks_before_fault=cb_calls;assert(sync100_dma_at(d,0x1090)==-22&&cp_digest(bank,CP_BANK_BYTES)==before_copy_failure&&cb_calls==callbacks_before_fault);p=request(0);assert(sync100_reply(0x903e0811,p)==-7&&!sync100_active);free(p-64);
 /* Every descriptor field rejects without callback or memory overwrite. */
 for(unsigned i=0;i<40;i++){p=request(3);assert(!sync100_reply(0x903e0811,p));consume(1);descriptor(d);d[i]^=1;int before=cb_calls;U hash=cp_digest(bank,CP_BANK_BYTES);assert(sync100_dma_at(d,0x1090)==-22&&cb_calls==before&&cp_digest(bank,CP_BANK_BYTES)==hash);p=request(0);assert(sync100_reply(0x903e0811,p)==-7&&!sync100_active);free(p-64);}
 cleanup_module();assert(!registered&&!sync100_hooked&&!sync100_gate&&apiwords[0]==0xb4000b00&&!work&&!rollback);free(d);free(bank);puts("AP101_NATIVE_CONSTRUCTOR_PASS exact40B/schema/order/native4096/sourceQ/tailzero/lockSuspend1/unlockSuspend1/wholebank_snapshot_realcopy_readback/nativecallbackonce/duplicate_no_callback/unlock_does_not_mask_DMAfailure/alloc_send_rollback/retry/same_numeric_Q_allowed/checksum_refresh/payload_integrity/40_descriptor_mutations/native_non_target_forward/binding_failure_restore/cleanup_restore");}
