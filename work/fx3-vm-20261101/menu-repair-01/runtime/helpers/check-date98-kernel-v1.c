
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#include "fx3-cp-backup-reset-v2-date98.c"
static _Alignas(64) B trace_test_page[DATE98_SPAN];static B *bank;static void *enqueued;static int alloc_fail,send_fail,reg_result;static W alloc_owner,last_free_owner,last_send_Q;static unsigned request_frees,reply_frees;static W request_Q=0x803e61c2;
int printk(const char*f,...){(void)f;return 0;}int osal_reg_public(const void*p){assert(p==&owner);return reg_result;}int osal_unreg_public(void){return 0;}
W osal_msg_size(const void*p){return rd32((const B*)p-8);}W osal_get_msg_src(const void*p){return rd32((const B*)p-12);}void osal_set_msg_src(void*p,W v){wr32((B*)p-12,v);}
static B*msg(W n,W src){B *b=calloc(1,n+80);assert(b);B*p=b+64;p[-16]=(B)(((n+131)&~63U)/64);p[-15]=65;p[-14]=1;wr32(p-12,src);wr32(p-8,n);wr32(p-4,0x55555555);wr32(p+n,0x77777777);return p;}
int osal_valloc_msg_wait(W id,void**p,W n,W wait){assert(n==4096&&!wait);alloc_owner=id;if(alloc_fail){*p=0;return -1023;}*p=msg(n,id);return 0;}
int osal_snd_msg(W q,void*p){assert(q==request_Q&&osal_msg_size(p)==4096&&osal_get_msg_src(p)==0x003e0811);assert(rd32(p)==0x33&&!rd32((B*)p+4)&&rd32((B*)p+12)==q);for(unsigned i=40;i<4096;i++)assert(!((B*)p)[i]);last_send_Q=q;if(send_fail)return -1021;assert(!enqueued);enqueued=p;return 0;}
int osal_free_msg(W id,void*p){W n=osal_msg_size(p);if(n==40){assert(id==0x903e0811);request_frees++;}else{assert(n==4096&&id==request_Q);reply_frees++;}last_free_owner=id;free((B*)p-64);return 0;}
void*arch_phys_to_va(U p){if(p==DATE98_PHYS)return trace_test_page;assert(p==CP_BANK_PHYS);return bank;}void*vmalloc(U n){return malloc(n);}void vfree(void*p){free(p);}
static B*request(W f){B*p=msg(40,request_Q);W w[10]={0x33,0,0x903e0811,request_Q,1,1,2,0,2,f};for(unsigned i=0;i<10;i++)wr32(p+4*i,w[i]);return p;}
static void consume(void){assert(enqueued);assert(!rd32((B*)enqueued+4));assert(!osal_free_msg(last_send_Q,enqueued));enqueued=0;}
int main(int argc,char**argv){assert(argc==2);FILE*f=fopen(argv[1],"rb");assert(f);bank=malloc(CP_BANK_BYTES);assert(fread(bank,1,CP_BANK_BYTES,f)==CP_BANK_BYTES);fclose(f);assert(!cp_validate(bank,1)&&cp_digest(bank,CP_BANK_BYTES)==CP_SEED_FNV64);
 /* Core applies actual differences, repeat allcopies forF1, and every default. */
 B *test=malloc(CP_BANK_BYTES);cp_copy(test,bank,CP_BANK_BYTES);struct cp_stats st;test[0x2f24c]^=1;assert(!cp_reset(test,1,&st)&&st.selected==317&&st.repeat_items==2&&st.changed==1&&cp_equal(test,bank,CP_BANK_BYTES));assert(!cp_reset(test,4,&st)&&st.selected==2&&!st.changed);
 cp_copy(test,bank,CP_BANK_BYTES);wr32(test+258,31198);assert(cp_validate(test,0)==-7);cp_copy(test,bank,CP_BANK_BYTES);test[16]=0;assert(cp_reset(test,1,&st)==-7);cp_copy(test,bank,CP_BANK_BYTES);test[32]^=1;assert(cp_validate(test,1)==-7);assert(cp_reset(bank,2,&st)==-7);free(test);
 reg_result=-1018;assert(init_module()==-1018&&!registered);reg_result=0;assert(!init_module()&&registered&&owner.send==cp_reset_send&&!owner.sync);
 B*p=request(4);assert(cp_reset_send(0x903e0811,p)==-7&&!stage);free(p-64);p=request(1);wr32(p-8,39);assert(cp_reset_send(0x903e0811,p)==-7&&!stage);free(p-64);
 p=request(1);alloc_fail=1;assert(cp_reset_send(0x903e0811,p)==-7&&!stage&&pending_valid&&cp_digest(bank,CP_BANK_BYTES)==CP_SEED_FNV64&&!request_frees);alloc_fail=0;send_fail=1;assert(cp_reset_send(0x903e0811,p)==-1021&&!stage&&reply_frees==1&&!request_frees&&cp_digest(bank,CP_BANK_BYTES)==CP_SEED_FNV64);
 B*wrong=request(1);wr32(wrong+12,request_Q+1);wr32(wrong-12,request_Q+1);assert(cp_reset_send(0x903e0811,wrong)==-7&&!stage);free(wrong-64);
 send_fail=0;assert(!cp_reset_send(0x903e0811,p)&&stage==1&&request_frees==1&&!pending_valid&&alloc_owner==request_Q&&enqueued);consume();
 p=request(1);assert(cp_reset_send(0x903e0811,p)==-7&&stage==1);free(p-64);p=request(2);assert(cp_reset_send(0x903e0811,p)==-7&&stage==1);free(p-64);
 p=request(4);assert(!cp_reset_send(0x903e0811,p)&&stage==2&&request_frees==2&&enqueued);consume();assert(cp_digest(bank,CP_BANK_BYTES)==CP_SEED_FNV64);
 p=request(4);assert(cp_reset_send(0x903e0811,p)==-7&&stage==2);free(p-64);p=request(1);wr32(p,0x34);assert(!cp_reset_send(0x903e0811,p)&&stage==2);free(p-64);
 B*date=msg(44,0x809061c5);for(W i=0;i<44;i++)date[i]=(B)(i+3);B original44[44];cp_copy(original44,date,44);unsigned old_request_frees=request_frees,old_reply_frees=reply_frees;assert(!cp_reset_send(0x909005c5,date));assert(cp_equal(date,original44,44)&&request_frees==old_request_frees&&reply_frees==old_reply_frees&&!enqueued&&stage==2&&cp_digest(bank,CP_BANK_BYTES)==CP_SEED_FNV64);B*record=trace_test_page+64;assert(rd32(record+24)==0x909005c5&&rd32(record+28)==44&&rd32(record+48)==2&&rd32(record+52)==0&&rd32(record+60)==1&&rd32(record+64)==0&&rd32(record+76)==2&&cp_equal(record+192,original44,44));free(date-64);
 cleanup_module();assert(!registered&&!backing&&!work&&!rollback&&!enqueued&&reply_frees==3);free(bank);puts("DATE98_KERNEL44_PASS no_reply/no_free/no_mutation/unchanged_return0/source_full44/own_trace_lease; CP88_REGRESSION_PASS nativeheader/schema/wholeindex/defaultbounds/checksum/repeat4/realchangedcopy/F1thenF4/wrongflags/duplicate/retryidentity/allocationfailure/sendfailure_rollback/separate4096reply_zero_tail/sourceQ/original_request_destination_free/onlyreply_native_queue_ownership");}
