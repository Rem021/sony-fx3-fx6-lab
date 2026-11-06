/* AP100 software CP Backup lock/snapshot/DMA/unlock. Single public owner. */
extern U kallsyms_lookup_name(const char*);
extern int probe_kernel_read(void*,const void*,U);
static B *sync100_dma_rollback;static W sync100_gate;static unsigned sync100_enabled,sync100_hooked,sync100_active,sync100_copied,sync100_callback,sync100_failed;static U sync100_epoch,sync100_payload;static unsigned sync100_suspend;
static int (*sync100_patch)(void**,W*,int);static void *sync100_api;static W sync100_original[4];
#ifndef SYNC100_HOST_TEST
extern int sync100_native_fallback(void*);
/* Exactly relocate the pinned first16B, including its sole PC-relative CBZ.
 * Non-target calls execute all original code with original x0 and LR. */
__asm__(".text\n.balign 16\n.global sync100_native_fallback\n.type sync100_native_fallback,%function\nsync100_native_fallback:\ncbnz x0,1f\nldr x16,2f\nbr x16\n1: stp x29,x30,[sp,#-0x50]!\nmov x29,sp\nstp x19,x20,[sp,#0x10]\nldr x16,3f\nbr x16\n.balign 8\n2: .quad 0xffffff8008322228\n3: .quad 0xffffff80083220d8\n.size sync100_native_fallback,.-sync100_native_fallback\n");
#else
extern int sync100_native_fallback(void*);
#endif
static U sync100_rd64(const B*p){return (U)rd32(p)|((U)rd32(p+4)<<32);}
static U sync100_fingerprint(const B*p){U h=14695981039346656037UL;for(U i=0;i<CP_BANK_BYTES;i++)if(i!=9&&(i<32||i>=36)){h^=p[i];h*=1099511628211UL;}return h;}
static int sync100_enter(void){int r;do{r=osal_wai_sem_tmo(sync100_gate,-1);}while(r==-1021);return r;}
static void sync100_leave(void){if(osal_sig_sem(sync100_gate))poisoned=1;}
static int sync100_storage(void){
 if(cp_setup()||poisoned||cp_validate(backing,0))return -7;
 if(!sync100_payload)sync100_payload=sync100_fingerprint(backing);
 if(sync100_payload!=sync100_fingerprint(backing)||backing[9]!=sync100_suspend)return -7;
 U d=cp_digest(backing,CP_BANK_BYTES);
 /* Native backupfile_save may recompute the checksum. Payload is immutable
    outside the existing audited reset transaction. Never reseed from AP. */
 if(d!=expected_digest){if(cp_validate(backing,1))return -7;expected_digest=d;printk("FX3_SYNC100_NATIVE_CHECKSUM_REFRESH epoch=%lu checksum=%#x unchanged_payload=1\n",sync100_epoch,rd32(backing+32));}
 return 0;
}
static int sync100_schema(W dst,void*p,W*q,W*mode){
 if(dst!=0x903e0811||!p||osal_msg_size(p)!=40)return -7;B*b=p;W Q=rd32(b+12),m=rd32(b+32);
 if(rd32(b)!=0x30||rd32(b+4)||rd32(b+8)!=dst||(Q&0xffff0000U)!=0x803e0000U||!(Q&0x7fffU)||(Q&0x8000U)||osal_get_msg_src(p)!=Q||rd32(b+16)!=1||rd32(b+20)!=1||rd32(b+24)!=1||rd32(b+28)!=1||(m!=3&&m!=0)||rd32(b+36))return -7;
 const B*h=b-24;if(h[8]!=2||(h[9]&64)==0||rd16(h+10)!=1||rd32(h+12)!=Q||rd32(h+16)!=40||rd32(h+20)!=0x55555555||rd32(b+40)!=0x77777777)return -7;*q=Q;*mode=m;return 0;
}
static int sync100_reply(W dst,void*p){
 W Q=0,mode=0;if(!sync100_enabled||sync100_schema(dst,p,&Q,&mode)){printk("FX3_SYNC100_REJECT reason=schema no_reply=1 no_free=1\n");return -7;}
 if(sync100_enter())return -7;int rc=-7;void*reply=0;int locked=0;cp_raw("SYNC100_NATIVE_REQUEST",dst,p,40);
 if(sync100_storage())goto reject;
 if(mode==3){if(sync100_active||sync100_epoch==~0UL)goto reject;cp_copy(rollback,backing,CP_BANK_BYTES);backing[9]=1;sync100_suspend=1;cp_copy(work,backing,CP_BANK_BYTES);if(!cp_equal(work,backing,CP_BANK_BYTES))goto undo_lock;locked=1;sync100_active=1;sync100_copied=sync100_callback=sync100_failed=0;sync100_epoch++;expected_digest=cp_digest(backing,CP_BANK_BYTES);}
 else if(!sync100_active)goto reject;
 else if(sync100_failed||!sync100_copied||!sync100_callback){/* Native AP still unlocks after DMA failure: expose failure, never mask it. */sync100_active=0;sync100_failed=1;printk("FX3_SYNC100_REJECT reason=unlock_without_verified_copy epoch=%lu no_success=1\n",sync100_epoch);goto out;}
 rc=osal_valloc_msg_wait(Q,&reply,4096,0);if(rc||!reply||osal_msg_size(reply)!=4096){rc=-7;goto failed;}
 for(W i=0;i<4096;i++)((B*)reply)[i]=0;cp_copy(reply,p,40);wr32((B*)reply+4,0);wr32((B*)reply+32,mode==3?1:0);osal_set_msg_src(reply,0x003e0811);
 rc=osal_snd_msg(Q,reply);if(rc)goto failed;reply=0;
 if(mode==0)sync100_active=0;
 int fr=osal_free_msg(dst,p);if(fr)poisoned=1;
 printk("FX3_SYNC100_COMMIT op=0x30 mode=%u reply_mode=%u Q=%#x source=0x003e0811 epoch=%lu SuspendComp=%u reply_bytes=4096 initialized_copy=40 tail_zeroed=4056 tail_software_difference=1 native_send=0 native_request_free=%d data_in_reply=0 synthetic_cp_backup_sync=1 original_CP=0 source_alias_destination=1\n",mode,mode==3?1:0,Q,sync100_epoch,backing[9],fr);rc=0;goto out;
 failed:if(reply){if(osal_free_msg(Q,reply))poisoned=1;reply=0;}if(locked){
 undo_lock:cp_copy(backing,rollback,CP_BANK_BYTES);sync100_suspend=backing[9];sync100_active=0;sync100_copied=sync100_callback=sync100_failed=0;expected_digest=cp_digest(backing,CP_BANK_BYTES);if(!cp_equal(backing,rollback,CP_BANK_BYTES))poisoned=1;printk("FX3_SYNC100_ROLLBACK mode=3 epoch=%lu verified=%u no_request_free=1\n",sync100_epoch,!poisoned);}
 if(!rc)rc=-7;goto out;
 reject:printk("FX3_SYNC100_REJECT reason=order_or_storage mode=%u active=%u epoch=%lu no_reply=1 no_free=1\n",mode,sync100_active,sync100_epoch);
 out:sync100_leave();return rc;
}
#ifndef SYNC100_AFTER_COPY
#define SYNC100_AFTER_COPY(p,n) ((void)0)
#endif
static int sync100_dma_at(void*descriptor,U caller){
 U cb=kallsyms_lookup_name("backupfile_cb_getcp"),get=kallsyms_lookup_name("backupfile_get_cp_data");
 /* Non-target behavior stays in the original API, including invalid-input
    -EINVAL and all original uninitialized-channel semantics. */
 if(!get||caller!=get+(0x70c0-0x7030)){printk("FX3_SYNC100_DMA_NON_TARGET caller=%#lx original_API_forward=1 synthetic_success=0\n",caller);return sync100_native_fallback(descriptor);}
 B d[40];int rc=-22;if(!sync100_enabled||!cb||!descriptor||probe_kernel_read(d,descriptor,40))goto bad;
 if(d[0]||d[1]!=4||d[2]||d[3]||rd32(d+4)!=CP_BANK_BYTES||sync100_rd64(d+8)!=0x404000000UL||sync100_rd64(d+16)!=CP_BANK_PHYS||sync100_rd64(d+24)!=cb||sync100_rd64(d+32))goto bad;
 if(sync100_enter())goto bad;
 if(!sync100_active||sync100_failed||sync100_copied||sync100_callback||poisoned||cp_validate(work,0)||sync100_fingerprint(work)!=sync100_payload||work[9]!=1||cp_digest(work,CP_BANK_BYTES)!=expected_digest)goto bad_locked;
 B*dest=arch_phys_to_va(CP_BANK_PHYS);if(!dest||!sync100_dma_rollback)goto bad_locked;cp_copy(sync100_dma_rollback,dest,CP_BANK_BYTES);
 /* Frozen work is a real full-bank snapshot made before lock reply. It is not
    fabricated defaults, nor a read of AP primary at remote CP address. */
 cp_copy(dest,work,CP_BANK_BYTES);SYNC100_AFTER_COPY(dest,CP_BANK_BYTES);__atomic_thread_fence(__ATOMIC_SEQ_CST);
 if(!cp_equal(dest,work,CP_BANK_BYTES)){cp_copy(dest,sync100_dma_rollback,CP_BANK_BYTES);if(!cp_equal(dest,sync100_dma_rollback,CP_BANK_BYTES))poisoned=1;sync100_failed=1;goto bad_locked;}
 sync100_copied=sync100_callback=1;expected_digest=cp_digest(dest,CP_BANK_BYTES);
 printk("FX3_SYNC100_DMA_COPY epoch=%lu caller=%#lx descriptor=%p remote_source=0x404000000 modeled_CP_backing=%#lx AP_destination=%#lx bytes=%u before_snapshot_fnv64=%#lx destination_fnv64=%#lx all_bytes_equal=1 source_alias_destination=1 synthetic_cp_backup_sync=1 original_CP=0 callback=%#lx context=0 count=1\n",sync100_epoch,caller,descriptor,CP_BANK_PHYS,CP_BANK_PHYS,CP_BANK_BYTES,cp_digest(work,CP_BANK_BYTES),expected_digest,cb);
 /* The original callback itself signals 803e090b. Do not signal it here. */
 ((void(*)(int,void*))cb)(0,0);
 printk("FX3_SYNC100_NATIVE_CALLBACK_RETURN epoch=%lu count=1 original_callback=1 result_argument=0 context=0\n",sync100_epoch);sync100_leave();return 0;
 bad_locked:sync100_failed=1;sync100_leave();
 bad:printk("FX3_SYNC100_REJECT reason=DMA_target_schema_or_state caller=%#lx descriptor=%p no_copy=1 no_callback=1 result=%d\n",caller,descriptor,rc);return rc;
}
__attribute__((noinline)) static int sync100_dma(void*p){return sync100_dma_at(p,(U)__builtin_return_address(0));}
static int sync100_route(W dst,void*p){
 if(dst==0x903e0811&&p&&osal_msg_size(p)>=4&&rd32(p)==0x30)return sync100_reply(dst,p);
 if(dst!=0x903e0811||!p||osal_msg_size(p)<4||rd32(p)!=0x33)return cp_reset_send_backup100_prior(dst,p);
 if(sync100_enter())return -7;int rc;
 if(sync100_active){printk("FX3_SYNC100_REJECT reason=reset_during_lock no_reply=1\n");rc=-7;}
 else {rc=cp_reset_send_backup100_prior(dst,p);if(!rc&&initialized){sync100_payload=sync100_fingerprint(backing);sync100_suspend=backing[9];}}
 sync100_leave();return rc;
}
static void sync100_log_patch(const char*phase,const W*p,int rc){printk("FX3_SYNC100_API_BIND phase=%s result=%d api=%p words=%08x,%08x,%08x,%08x original_disk_bytes_unchanged=1\n",phase,rc,sync100_api,p[0],p[1],p[2],p[3]);}
static int sync100_restore(void){if(!sync100_hooked)return 0;void*a[4];for(W i=0;i<4;i++)a[i]=(B*)sync100_api+4*i;int rc=sync100_patch(a,sync100_original,4);W check[4]={0};if(probe_kernel_read(check,sync100_api,16)||!cp_equal((B*)check,(B*)sync100_original,16))rc=-7;sync100_log_patch("restored",check,rc);if(!rc)sync100_hooked=0;return rc;}
static int sync100_start(void){
 if(osal_dynamic_id(0x32,0x90,&sync100_gate)||!sync100_gate)return -7;sync100_dma_rollback=vmalloc(CP_BANK_BYTES);if(!sync100_dma_rollback)goto fail;
 sync100_api=(void*)kallsyms_lookup_name("pcidma_transfer_async");sync100_patch=(void*)kallsyms_lookup_name("aarch64_insn_patch_text");
 const W pinned[4]={0xb4000b00,0xa9bb7bfd,0x910003fd,0xa90153f3};
 if((U)sync100_api!=0xffffff80083220c8UL||!sync100_patch||probe_kernel_read(sync100_original,sync100_api,16)||!cp_equal((B*)pinned,(B*)sync100_original,16))goto fail;
 sync100_log_patch("original",sync100_original,0);void*a[4];W target[4]={0x58000050,0xd61f0200,(W)(U)sync100_dma,(W)((U)sync100_dma>>32)};for(W i=0;i<4;i++)a[i]=(B*)sync100_api+4*i;
 int rc=sync100_patch(a,target,4);sync100_hooked=1;W check[4]={0};if(probe_kernel_read(check,sync100_api,16)||!cp_equal((B*)check,(B*)target,16))rc=-7;sync100_log_patch("bound",check,rc);
 if(rc){sync100_restore();goto fail;}sync100_enabled=1;printk("FX3_SYNC100_BACKEND_BOUND exact_op30=1 exact_DMA=1 native_callback_once=1 non_target_original_API=1 synthetic_cp_backup_sync=1 original_CP=0\n");return 0;
 fail:sync100_enabled=0;printk("FX3_SYNC100_DISABLED reason=binding_failure no_success_fallback=1\n");if(!sync100_hooked){osal_dynamic_id(0x52,0,(void*)(U)sync100_gate);sync100_gate=0;if(sync100_dma_rollback)vfree(sync100_dma_rollback);sync100_dma_rollback=0;return -7;}return -7;
}
__attribute__((noinline,used)) int fx3_sync100_shutdown(void){if(sync100_enter())return -7;sync100_enabled=0;int rc=sync100_restore();sync100_leave();printk("FX3_SYNC100_SHUTDOWN original16_verified=%u resident_module_preserved=1 active=%u\n",!rc,sync100_active);return rc;}
static void sync100_stop(void){sync100_enabled=0;if(sync100_dma_rollback)vfree(sync100_dma_rollback);sync100_dma_rollback=0;int rc=sync100_restore();if(sync100_gate){osal_dynamic_id(0x52,0,(void*)(U)sync100_gate);sync100_gate=0;}printk("FX3_SYNC100_BACKEND_STOP restored=%u active=%u epoch=%lu\n",!rc,sync100_active,sync100_epoch);}
