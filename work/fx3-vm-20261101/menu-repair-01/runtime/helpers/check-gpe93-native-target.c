#include <assert.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <pthread.h>
#include <sched.h>
#include <setjmp.h>
static int proc90_mode;static unsigned long early_base;static unsigned char fake_map[64];
static void *stub_dlsym(void*,const char*);static long stub_syscall(long,...);
static void stub_exit(int) __attribute__((noreturn));
#define dlsym stub_dlsym
#define syscall stub_syscall
#define _exit stub_exit
static long stub_pread(int,void*,unsigned long,long);
static int stub_open(const char*,int,...);
static long stub_read(int,void*,unsigned long);
static int stub_close(int);
static void *stub_mmap(void*,unsigned long,int,int,int,long);
static int stub_munmap(void*,unsigned long);
static int stub_printf(int,const char*,...);
#define pread stub_pread
#define open stub_open
#define read stub_read
#define close stub_close
#define mmap stub_mmap
#define munmap stub_munmap
#define dprintf stub_printf
#define __errno_location stub_errno
static int *stub_errno(void){static int e;return &e;}
static int bad_handle;int dlinfo(void *h,int r,void *p){assert(r==2);if(h!=(void*)17||bad_handle)return -1;memcpy(fake_map,&early_base,8);*(void**)p=fake_map;return 0;}
#define FX3_GPE_HOST_TEST 1
#include "fx3-gpe-observe-v17-native-target.c"
static unsigned char memory[EXT_BYTES],before[EXT_BYTES],private_memory[EXT_BYTES],private_before[EXT_BYTES];
#define PRIVATE_BASE 0x512340000UL
static unsigned maps,unmaps,cmd_lines,summary_lines,statuses,callbacks,order,laststatus;
static int live=1,badread=0,mapfail=0,sendfail=0;
static struct gpe_callback_param lastcb;
static void callback(const void *p){memcpy(&lastcb,p,16);assert(order==0);order=1;callbacks++;assert(memory[0x100]==0x44);}
static int complete(unsigned src,const void *p,size_t n){assert(src==0x123);assert(n==4);memcpy(&laststatus,p,4);assert(laststatus==0||laststatus==5);assert(order<=1);order=2;statuses++;return !sendfail;}
static int stub_printf(int fd,const char *fmt,...){(void)fd;va_list ap;va_start(ap,fmt);char buf[2048];int n=vsnprintf(buf,sizeof(buf),fmt,ap);va_end(ap);assert(n>0&&n<(int)sizeof(buf));
 if(strstr(buf,"FX3_GPE_CMD op=")){cmd_lines++;const char *fields[]={" op="," seq="," async="," fmt="," w="," h="," dst_phys="," src_phys="," flags="," result="};for(unsigned i=0;i<10;i++)assert(strstr(buf,fields[i]));}
 if(strstr(buf,"FX3_GPE_CMD_SUMMARY"))summary_lines++;
 fputs(buf,stdout);return n;}
static long stub_pread(int fd,void *p,unsigned long n,long a){(void)fd;if(badread)return -1;memcpy(p,(void*)a,n);return n;}
static int stub_open(const char *p,int f,...){(void)f;if(!strcmp(p,"/proc/udm/dmm_extents"))return 81;if(!strcmp(p,"/proc/self/maps"))return 82;if(!strcmp(p,"/proc/udm/dmm_units"))return 83;return 80;}
static long stub_read(int fd,void *p,unsigned long n){static int last,used;if(last!=fd){last=fd;used=0;}if(used){used=0;return 0;}used=1;char buf[1024];if(fd==81)snprintf(buf,sizeof(buf),"0081 0003 00000001 %08x 00000000 00000000 00000003 0000008c 43feb5000 (430400000+fab5000) 00140000\n",live?0x545:0x546);else if(fd==83)snprintf(buf,sizeof(buf),"0402 00000403 0002 01 01 00 01 00000003 43feb5000 00140000 0081 < 0003\n");else snprintf(buf,sizeof(buf),"%lx-%lx r-xp 0 0:0 0\n",(unsigned long)callback&~4095UL,((unsigned long)callback&~4095UL)+4096);if(fd==81&&proc90_mode==1)buf[strlen(buf)-1]=0;
 if(fd==81&&proc90_mode==2){char duplicate[512];strcpy(duplicate,buf);strcat(buf,duplicate);}
 if(fd==81&&proc90_mode==3){char*q=strstr(buf,"fab5000");assert(q);q[6]='1';}
 if(fd==83&&proc90_mode==4){char*q=strstr(buf,"0081 <");assert(q);q[3]='2';}
 if(fd==81&&proc90_mode==5){buf[strlen(buf)-1]=0;strcat(buf," garbage\n");}
 size_t z=strlen(buf);assert(z<n);memcpy(p,buf,z);return z;}
static int stub_close(int fd){(void)fd;return 0;}
static void *stub_mmap(void *p,unsigned long n,int a,int b,int fd,long off){(void)p;(void)a;(void)b;(void)fd;assert(n&&n<=EXT_BYTES);assert(a==1||a==3);maps++;if(mapfail)return (void*)-1;if(off==EXT_BASE)return memory;if(off==PRIVATE_BASE)return private_memory;assert(0);return (void*)-1;}
static int stub_munmap(void *p,unsigned long n){assert((p==memory||p==private_memory)&&n&&n<=EXT_BYTES);unmaps++;return 0;}
static void p32(unsigned char *p,unsigned v){memcpy(p,&v,4);}
static void p64(unsigned char *p,U v){memcpy(p,&v,8);}
static void mkfill(unsigned char *p,unsigned fmt){memset(p,0,56);p64(p,PAYLOAD_BASE);p32(p+16,3);p32(p+20,2);p32(p+24,5);p32(p+28,fmt);p[32]=0x11;p[33]=0x22;p[34]=0x33;p[35]=0x44;p[37]=255;p[38]=1;}
static void reset(void){raster_failed=0;fills_done=0;order=0;live=1;badread=mapfail=sendfail=0;memset(memory,0xa5,sizeof(memory));}
int fx3_original_test_main(void){physical=80;process_mem=80;draw_complete=complete;unsigned char p[144],f[24]={0};
 for(unsigned fmt=0;fmt<2;fmt++){reset();mkfill(p,fmt);assert(fill(0,0,10,0,p)==0);unsigned bpp=fmt?4:2;for(unsigned y=0;y<2;y++)for(unsigned x=0;x<3;x++){unsigned char *q=memory+0x100+(y*5+x)*bpp;if(fmt)assert(!memcmp(q,"\x44\x33\x22\x11",4));else assert(!memcmp(q,"\x34\x12",2));}assert(memory[0xff]==0xa5&&memory[0x100+3*bpp]==0xa5);assert(flush(0,0,11,0x123,f)==0);}
 reset();mkfill(p,1);p[38]=0;p64(p+40,(U)callback);p64(p+48,0xabc);assert(fill(0,0,12,0x123,p)==0);assert(order==2&&lastcb.sequence==12&&!lastcb.zero&&lastcb.argument==0xabc);
 order=0;p[38]=1;unsigned old=statuses;assert(fill(0,0,13,0x123,p)==0&&statuses==old&&order==1);
 memset(f,0,24);f[0]=1;p64(f+8,(U)callback);p64(f+16,0xdef);order=0;assert(flush(0,0,14,0x123,f)==0&&order==1&&lastcb.argument==0xdef);
 for(unsigned fmt=0;fmt<2;fmt++){reset();for(unsigned i=0;i<64;i++)memory[0x100+i]=(unsigned char)i;
 memset(p,0,144);p64(p,PAYLOAD_BASE+0x400);p64(p+56,PAYLOAD_BASE);p32(p+16,3);p32(p+20,2);p32(p+32,3);p32(p+36,2);p32(p+48,5);p32(p+52,fmt);p32(p+72,3);p32(p+76,2);p32(p+88,5);p32(p+92,fmt);p[114]=255;p[121]=1;memcpy(before,memory,sizeof(memory));assert(blit(0,0,15,0,p)==0);unsigned bpp=fmt?4:2;for(unsigned y=0;y<2;y++){memcpy(before+0x500+y*5*bpp,before+0x100+y*5*bpp,3*bpp);}assert(!memcmp(memory,before,sizeof(memory)));}
 for(unsigned t=0;t<8;t++){reset();mkfill(p,1);if(t==0)p64(p,EXT_BASE+EXT_BYTES);if(t==1)p64(p,EXT_BASE);if(t==2)p64(p,EXT_BASE+EXT_BYTES-16);if(t==3)live=0;if(t==4)p32(p+28,2);if(t==5)badread=1;if(t==6)p64(p+40,3);if(t==7)mapfail=1;memcpy(before,memory,sizeof(memory));old=statuses;assert(fill(0,0,20+t,0x123,p)==5);assert(statuses==old);assert(!memcmp(before,memory,sizeof(memory)));}

 /* Native Main stub: adapter returns failure, Main sends the sole 4B5. */
 reset();mkfill(p,1);p64(p,1);p[38]=0;old=statuses;int rc=fill(0,0,29,0x123,p);assert(rc==5&&statuses==old);assert(complete(0x123,&rc,4)&&statuses==old+1&&laststatus==5);
 /* Source outside 545, overlap and unsupported flags: reject before writes. */
 for(unsigned t=0;t<3;t++){reset();memset(p,0,144);p64(p,PAYLOAD_BASE+0x400);p64(p+56,t==0?1:t==1?PAYLOAD_BASE+0x400:PAYLOAD_BASE);p32(p+16,2);p32(p+20,2);p32(p+32,2);p32(p+36,2);p32(p+48,4);p32(p+52,1);p32(p+72,2);p32(p+76,2);p32(p+88,4);p32(p+92,1);p[114]=255;p[121]=1;if(t==2)p[115]=1;memcpy(before,memory,sizeof(memory));assert(blit(0,0,40+t,0,p)==5&&!memcmp(memory,before,sizeof(memory)));}
 reset();memset(f,0,24);assert(flush(0,0,30,0x123,f)==5);mkfill(p,1);assert(fill(0,0,31,0,p)==0);p64(p,1);assert(fill(0,0,32,0,p)==5);assert(flush(0,0,33,0x123,f)==5);
 reset();mkfill(p,1);sendfail=1;p[38]=0;assert(fill(0,0,34,0x123,p)==5&&raster_failed);sendfail=0;
 reset();seen=0;memset(stats,0,sizeof(stats));cmd_lines=summary_lines=0;mkfill(p,1);for(unsigned i=0;i<1100;i++)assert(fill(0,0,i,0,p)==0);assert(cmd_lines==200&&summary_lines==3&&stats[0].total==1100&&stats[0].ok==1100);assert(maps>=unmaps);
 puts("PASS adapter: pixels, extent rejection zero writes, completion ordering, sticky flush, marker fields and throttling; ASan/UBSan enabled");return 0;}

int retained_raster_main(void){int result=fx3_original_test_main();assert(fx3_gpe_snapshot_unlock()==-1);assert(!fx3_gpe_snapshot_trylock());assert(fx3_gpe_snapshot_trylock()==-1);assert(command_lock);assert(command(0,0,0,0,0,0)==5);assert(!fx3_gpe_snapshot_unlock());assert(!command_lock);assert(fx3_gpe_snapshot_unlock()==-1);return result;}

static unsigned native_creates,bind_calls,yields,waiting;static int native_result=-3;static const void*last_info;static unsigned char info_before[40];static jmp_buf rejection;static int expected_exit;
static void stub_exit(int code){assert(code==expected_exit);longjmp(rejection,1);}
static int original_create(const void*info){assert(stub_errno()[0]==77);assert(!memcmp(info,info_before,40));native_creates++;last_info=info;stub_errno()[0]=9;return native_result;}
static void*original_noload(const char*n,int flags){assert(!strcmp(n,"libgpe.so")&&flags==5);return (void*)17;}
static void*stub_dlsym(void*h,const char*n){assert(h==(void*)-1);if(!strcmp(n,"osal_create_thread"))return (void*)original_create;if(!strcmp(n,"dlopen"))return (void*)original_noload;assert(0);return 0;}
int dladdr(const void*p,struct app_dl_info*out){if((U)p<early_base||(U)p>=early_base+0x30000)return 0;out->base=(void*)early_base;out->file="/usr/lib/libgpe.so";return 1;}
static long stub_syscall(long n,...){assert(n==124);__atomic_add_fetch(&yields,1,__ATOMIC_RELAXED);sched_yield();return 0;}
static int simulated_binder(void*h){assert(h==(void*)17);__atomic_add_fetch(&bind_calls,1,__ATOMIC_RELAXED);if(__atomic_load_n(&binding_lock,__ATOMIC_ACQUIRE)){__atomic_store_n(&waiting,1,__ATOMIC_RELEASE);return -2;}__atomic_store_n(&armed,1,__ATOMIC_RELEASE);return 0;}
static void setinfo(unsigned g){U*p=(void*)(early_base+(g?0x297e8:0x297c0));p[0]=early_base+(g?0x1574e:0x15759);p[1]=4;p[2]=early_base+(g?0xdce4:0xdcb0);p[3]=0;p[4]=0x288;memcpy(info_before,p,40);}
static void*creator(void*arg){stub_errno()[0]=77;assert(osal_create_thread(arg)==native_result&&stub_errno()[0]==9);return 0;}
int early90_main(void){assert(!retained_raster_main());early_base=(U)calloc(1,0x30000);assert(early_base);host_early_bind_override=simulated_binder;setinfo(0);U*p=(void*)(early_base+0x297c0);
 assert(match_gpe_thread(p,early_base)==0);armed=0;stub_errno()[0]=77;assert(osal_create_thread(p)==-3&&armed&&native_creates==1&&last_info==p&&stub_errno()[0]==9);
 setinfo(1);p=(void*)(early_base+0x297e8);assert(match_gpe_thread(p,early_base)==1);armed=0;binding_lock=1;native_creates=0;waiting=0;pthread_t t;assert(!pthread_create(&t,0,creator,p));while(!__atomic_load_n(&waiting,__ATOMIC_ACQUIRE))sched_yield();assert(!native_creates&&!armed);__atomic_clear(&binding_lock,__ATOMIC_RELEASE);assert(!pthread_join(t,0));assert(native_creates==1&&armed&&yields);
 setinfo(0);p=(void*)(early_base+0x297c0);p[2]++;memcpy(info_before,p,40);assert(match_gpe_thread(p,early_base)==-1);armed=0;unsigned prior=bind_calls;stub_errno()[0]=77;assert(osal_create_thread(p)==-3&&bind_calls==prior&&!armed&&stub_errno()[0]==9);
 setinfo(0);p=(void*)(early_base+0x297c0);unsigned before=native_creates;bad_handle=1;expected_exit=126;if(!setjmp(rejection)){stub_errno()[0]=77;osal_create_thread(p);assert(0);}assert(native_creates==before);bad_handle=0;free((void*)early_base);puts("GPE_EARLY88_PASS exactGPE0and1_descriptor/entry/no_binding_passthrough/create_before_bind/racing_bind_barrier/nativeargs_result_errno_preserved/bind_failure_never_starts_hardware/retainedraster_extent_completion_guard");return 0;}

static unsigned char object90[0x120];static unsigned nr_open,nr_close,nr_malloc,nr_free;static int native90_result;
static int stub_resource_open(void*o,const void*c){assert(o==object90&&c==(void*)19);assert(*stub_errno()==77);nr_open++;*stub_errno()=13;return native90_result;}
static int stub_resource_close(void*o){assert(o==object90&&!lifecycle_lock);assert(*stub_errno()==77);nr_close++;*stub_errno()=14;return native90_result;}
static int stub_resource_malloc(void*o,U bytes,U align,void**out){assert(o==object90&&bytes==32&&align==16);assert(*stub_errno()==77);nr_malloc++;*out=(void*)0x12340100;*stub_errno()=15;return native90_result;}
static int stub_resource_free(void*o,void*p,unsigned flag){assert(o==object90&&p==(void*)0x12340100&&flag==1&&lifecycle_lock);assert(*stub_errno()==77);nr_free++;*stub_errno()=16;return native90_result;}
static void*free90_thread(void*unused){(void)unused;*stub_errno()=77;assert(observe_resource_free(object90,(void*)0x12340100,1)==native90_result);assert(*stub_errno()==16);return 0;}
static void check_resources90(void){
 native_resource_open=stub_resource_open;native_resource_close=stub_resource_close;native_resource_malloc=stub_resource_malloc;native_resource_free=stub_resource_free;
 memset(resources,0,sizeof(resources));resource_epoch=0;memset(object90,0,sizeof(object90));p64(object90,0x90001000);p64(object90+0x10,0x123);p32(object90+0x20,0x10);p64(object90+0x38,0x55);p32(object90+0x40,0x77);p64(object90+0x58,0x12340000);p64(object90+0x60,0x512340000);p64(object90+0x68,4096);
 native90_result=0;*stub_errno()=77;assert(!observe_resource_open(object90,(void*)19)&&*stub_errno()==13&&nr_open==1&&resources[0].active);
 struct resource_record r={0};life_enter();assert(resource_lookup(0x512340100,16,8,2,&r));assert(r.uhdl==0x77&&r.epoch==1);assert(!resource_lookup(0x512340fff,16,2,1,&r));assert(!resource_lookup(0x410524000,16,8,1,&r));life_leave();
 void*out=0;*stub_errno()=77;assert(!observe_resource_malloc(object90,32,16,&out)&&*stub_errno()==15&&nr_malloc==1);
 life_enter();U events=allocation_events;unsigned prior=nr_free;pthread_t t;assert(!pthread_create(&t,0,free90_thread,0));while(__atomic_load_n(&allocation_events,__ATOMIC_RELAXED)==events)sched_yield();assert(nr_free==prior);life_leave();assert(!pthread_join(t,0));assert(nr_free==prior+1);
 *stub_errno()=77;assert(!observe_resource_close(object90)&&*stub_errno()==14&&nr_close==1&&!resources[0].active);
 *stub_errno()=77;assert(!observe_resource_open(object90,(void*)19)&&resources[0].epoch==2);life_enter();assert(resource_lookup(0x512340100,16,8,1,&r)&&r.epoch==2);p32(object90+0x40,0x78);assert(!resource_lookup(0x512340100,16,8,1,&r)&&!resources[0].active);life_leave();
 native90_result=-9;*stub_errno()=77;assert(observe_resource_open(object90,(void*)19)==-9&&*stub_errno()==13&&!resources[0].active);puts("GPE90_RESOURCE_PASS original_once/errno/result/shared_free_lock/retire_before_close/unknown_extent_reject/reuse_epoch/native_identity_change; compaction/queuedABA untested and uncovered");
}
static void check_malloc_parent90(void){
 unsigned char pool[0x120];memcpy(pool,object90,sizeof(pool));p64(pool+0x10,0x124);p32(pool+0x40,0x81);p64(pool+0x58,0x22220000);p64(pool+0x60,0x410524000);p64(pool+0x68,0x400000);struct resource_record r={0};
 memset(resources,0,sizeof(resources));p32(object90+0x40,0x77);life_enter();resource_add(object90,"native_open_return_v1");assert(object_fields(pool,&r));malloc_parent_register(pool,&r,r.logical+0x100,32);assert(resources[1].active&&resources[1].object==(U)pool);U epoch=resources[1].epoch;resource_retire(pool,"test");
 r.vptr++;malloc_parent_register(pool,&r,r.logical+0x100,32);assert(!resources[1].active);r.vptr--;
 r.bytes--;malloc_parent_register(pool,&r,r.logical+0x100,32);assert(!resources[1].active);r.bytes++;
 malloc_parent_register(pool,&r,r.logical+r.bytes-1,32);assert(!resources[1].active);
 struct resource_record saved=resources[0];resources[0].phys=r.phys;resources[0].bytes=r.bytes;malloc_parent_register(pool,&r,r.logical+0x100,32);assert(!resources[1].active);resources[0]=saved;
 malloc_parent_register(pool,&r,r.logical+0x100,32);assert(resources[1].active&&resources[1].epoch>epoch);resource_retire(pool,"test_cleanup");life_leave();puts("GPE90_R2_SUPPLEMENT_PASS same_native_vptr/exact_log_tuple/selfconsistent/nonoverlap/returned_span/all_required; unknowns_failclosed");
}
int legacy_target_checks_main(void){assert(!early90_main());check_resources90();check_malloc_parent90();live=1;struct screen_identity si;
 assert(screen_live(&si)&&si.serial==0x8c);for(proc90_mode=1;proc90_mode<=5;proc90_mode++)assert(!screen_live(&si));proc90_mode=0;assert(screen_live(&si));puts("GPE90_PROC_PASS trueid81/unit402/completeEOF/duplicate/truncated/wrongbase/wrongunit/trailinggarbage failclosed");return 0;}

static void private_register(unsigned type,unsigned native){memset(resources,0,sizeof(resources));memset(object90,0,sizeof(object90));p64(object90,0x90001000);p64(object90+0x10,0x123);p32(object90+0x20,0x10);p64(object90+0x38,type);p32(object90+0x40,0x401);p64(object90+0x58,0x12340000);p64(object90+0x60,PRIVATE_BASE);p64(object90+0x68,EXT_BYTES);obj_bound=1;resource_class_vptr=0x90001000;life_enter();resource_add(object90,native?"native_open_return_v1":"malloc_parent_v1");life_leave();}
static void private_fill(unsigned char*p){mkfill(p,0);p64(p,PRIVATE_BASE+0x100);}
static void private_blit(unsigned char*p,U dst,U src){memset(p,0,144);p64(p,dst);p64(p+56,src);p32(p+16,2);p32(p+20,2);p32(p+32,2);p32(p+36,2);p32(p+48,4);p32(p+72,2);p32(p+76,2);p32(p+88,4);p[114]=255;p[121]=1;}
int main(void){assert(!legacy_target_checks_main());unsigned char p[144];
 reset();private_register(0x403,1);memset(private_memory,0xa5,sizeof(private_memory));private_fill(p);assert(!fill(0,0,1200,0,p));assert(private_memory[0x100]==0x34&&private_memory[0x101]==0x12&&private_memory[0xff]==0xa5);assert(memory[0x100]==0xa5);
 for(unsigned t=0;t<6;t++){reset();private_register(t==2?0x404:0x403,t!=1);memset(private_memory,0xa5,sizeof(private_memory));private_fill(p);if(t==0)resources[0].active=0;if(t==3)resource_class_vptr++;if(t==4)p64(p,PRIVATE_BASE+EXT_BYTES-1);if(t==5)p64(object90+0x10,0x999);memcpy(private_before,private_memory,sizeof(private_memory));assert(fill(0,0,1201+t,0,p)==5);assert(!memcmp(private_memory,private_before,sizeof(private_memory)));}
 for(unsigned mode=0;mode<3;mode++){reset();private_register(0x403,1);memset(private_memory,0x11,sizeof(private_memory));for(unsigned i=0;i<64;i++){private_memory[0x100+i]=(unsigned char)(i+1);memory[0x100+i]=(unsigned char)(i+51);}U dst=mode==0?PAYLOAD_BASE+0x400:PRIVATE_BASE+0x500,src=mode==1?PAYLOAD_BASE:PRIVATE_BASE+0x100;private_blit(p,dst,src);unsigned char expected[12];memcpy(expected,mode==1?memory+0x100:private_memory+0x100,12);assert(!blit(0,0,1300+mode,0,p));unsigned char*out=mode==0?memory+0x500:private_memory+0x500;assert(!memcmp(out,expected,4)&&!memcmp(out+8,expected+8,4));}
 puts("NATIVE_TARGET93_PASS nativeOpen_type403_class_epoch_fields_perrow/prewrite_reject/RO_distinct_source/545toprivate/privateto545/sameparentalias/legacy_callback_FIFO_Flush_proc_lifetime_retained");return 0;}
