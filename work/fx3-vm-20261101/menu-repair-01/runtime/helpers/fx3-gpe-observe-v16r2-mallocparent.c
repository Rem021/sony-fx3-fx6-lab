/* v14: original v12 binding/FIFO retained; bounded backend adapter. */
#include "fx3-gpe-backend-v3.h"
#include <string.h>
typedef unsigned long size_t;
typedef unsigned long U;
extern void *dlsym(void *,const char *);
extern int dlinfo(void *,int,void *);
extern int dprintf(int,const char *,...);
extern int open(const char *,int,...);
extern long pread(int,void *,size_t,long);
extern int close(int);
extern int mprotect(void *,size_t,int);
extern int strcmp(const char *,const char *);
extern int *__errno_location(void);
extern void _exit(int) __attribute__((noreturn));
struct dyn {long tag; U val;};
struct lm { U base; const char *name; struct dyn *dynamic; struct lm *next,*prev;};
struct sym {unsigned int name; unsigned char info,other; unsigned short shndx;U value,size;};
struct rela { U offset,info; long addend;};
extern void *mmap(void *,size_t,int,int,int,long);
extern long syscall(long,...);
struct app_dl_info {const char *file;void *base;const char *symbol;void *address;};
extern int dladdr(const void *,struct app_dl_info *);
static void *(*app_original)(void *);
static unsigned char app_lock;
static int app_bound;
static void sync_instructions(unsigned char *p,U n){

#ifndef FX3_GPE_HOST_TEST
 U ctr;__asm__ volatile("mrs %0, ctr_el0":"=r"(ctr));U dc=4UL<<((ctr>>16)&15),ic=4UL<<(ctr&15);
 for(U a=(U)p&~(dc-1);a<(U)p+n;a+=dc)__asm__ volatile("dc cvau, %0"::"r"(a):"memory");
 __asm__ volatile("dsb ish":::"memory");
 for(U a=(U)p&~(ic-1);a<(U)p+n;a+=ic)__asm__ volatile("ic ivau, %0"::"r"(a):"memory");
 __asm__ volatile("dsb ish; isb":::"memory");
#else
 (void)p;(void)n;
#endif
}
static void *app_observe(void *arg){
 int before=*__errno_location();long tid=syscall(178);
 dprintf(2,"FX3_APP_INIT_ENTER tid=%ld argument=%p original_delegated=1\n",tid,arg);
 *__errno_location()=before;void *(*fn)(void *)=__atomic_load_n(&app_original,__ATOMIC_ACQUIRE);
 if(!fn)_exit(126);void *result=fn(arg);int after=*__errno_location();
 dprintf(2,"FX3_APP_INIT_RETURN tid=%ld result=%p errno=%d original_delegated=1\n",tid,result,after);
 *__errno_location()=after;return result;
}
static void bind_app(void *h){
 if(__atomic_test_and_set(&app_lock,__ATOMIC_ACQUIRE))return;
 if(__atomic_load_n(&app_bound,__ATOMIC_ACQUIRE))goto done;
 unsigned char *p=dlsym(h,"Application_System_Init");struct app_dl_info info={0};
 if(!p||!dladdr(p,&info)||(U)p-(U)info.base!=0x16efb90)goto done;
 const unsigned char prefix[16]={0xfd,0x7b,0xba,0xa9,0x03,0x82,0x01,0x90,0x42,0xc5,0x00,0xd0,0x01,0x04,0x80,0xd2};
 for(unsigned int i=0;i<16;i++)if(p[i]!=prefix[i])goto done;
 unsigned char *tr=mmap(0,4096,3,0x22,-1,0);if(tr==(void *)-1)goto done;
 /* Replay STP/MOV and relocate two original ADRPs to exact literal page values. */
 unsigned int code[6]={0xa9ba7bfd,0x580000a3,0x580000c2,0xd2800401,0x580000d0,0xd61f0200};
 __builtin_memcpy(tr,code,24);U targets[3]={(U)info.base+0x472f000,(U)info.base+0x2f99000,(U)p+16};__builtin_memcpy(tr+24,targets,24);
 sync_instructions(tr,48);if(mprotect(tr,4096,5))goto done;
 __atomic_store_n(&app_original,(void *(*)(void *))tr,__ATOMIC_RELEASE);
 if(mprotect((void *)((U)p&~4095UL),4096,7))goto done;
 unsigned int branch[2]={0x58000050,0xd61f0200};U dest=(U)app_observe;
 __builtin_memcpy(p,branch,8);__builtin_memcpy(p+8,&dest,8);sync_instructions(p,16);
 if(mprotect((void *)((U)p&~4095UL),4096,5))_exit(126);
 __atomic_store_n(&app_bound,1,__ATOMIC_RELEASE);
 dprintf(2,"FX3_APP_INIT_BIND relative=0x16efb90 prefix_verified=16 relocated_adrp=2 result_unchanged=1\n");
 done: __atomic_clear(&app_lock,__ATOMIC_RELEASE);
}

static unsigned char binding_lock;
static int armed,physical=-1,process_mem=-1;
static unsigned int requests;
static void *(*loader)(const char *,int);
static int init(int gpe) {
 if(gpe || physical<0 || process_mem<0) return 5;
 dprintf(2,"FX3_GPE_MODEL_INIT gpe=%d resources_ready=1 mode=request_capture physical_engine=0\n",gpe);
 return 0;
}
static int gperm_init(const void *p) {
 int gpe=-1;
 if(!p || pread(process_mem,&gpe,4,(long)p+8)!=4) return 5;
 return init(gpe);
}
extern long read(int,void *,size_t);
extern char *strstr(const char *,const char *);
extern int sscanf(const char *,const char *,...);
extern int munmap(void *,size_t);

static int raster_failed;
static unsigned int fills_done;
static int (*draw_complete)(unsigned int,const void *,size_t);
#define EXT_BASE 0x43feb5000UL
#define EXT_BYTES 0x140000UL
#define PAYLOAD_BASE (EXT_BASE+0x100UL)
#include "fx3-gpe-screen-v1.inc"
static unsigned char command_lock;
/* Same guard as every v14 CPU raster command. Consumer only holds it for memcpy. */
static __thread unsigned snapshot_owned;
int fx3_gpe_snapshot_trylock(void){if(snapshot_owned||__atomic_test_and_set(&command_lock,__ATOMIC_ACQUIRE))return -1;snapshot_owned=1;return 0;}
int fx3_gpe_snapshot_unlock(void){if(!snapshot_owned)return -1;snapshot_owned=0;__atomic_clear(&command_lock,__ATOMIC_RELEASE);return 0;}

struct cmd_stats {unsigned long total,ok,rejected;};
static struct cmd_stats stats[3];
static unsigned long seen;
static unsigned int load32(const unsigned char *p){unsigned int v;__builtin_memcpy(&v,p,4);return v;}
static U load64(const unsigned char *p){U v;__builtin_memcpy(&v,p,8);return v;}
#include "fx3-gpe-resource-v2.inc"
static int approximate_command(unsigned op,const unsigned char *p,int readable){
 if(!readable||op==4)return 0;
 return op==0?(p[36]==1||p[36]==2):(p[112]<=1&&(p[112]||p[114]!=255));
}
static void marker(unsigned op,unsigned seq,const unsigned char *p,int readable,int result,int reason){
 unsigned k=op==4?2:op;U n=__atomic_add_fetch(&seen,1,__ATOMIC_RELAXED);
 U total=__atomic_add_fetch(&stats[k].total,1,__ATOMIC_RELAXED);
 __atomic_add_fetch(result?&stats[k].rejected:&stats[k].ok,1,__ATOMIC_RELAXED);
 int approx=approximate_command(op,p,readable);
 /* Every blend and every rejection remains observable after the v13 cap. */
 if(n<=200||approx||result){
  unsigned fmt=0,w=0,h=0,async=0;U dst=0,src=0,flags=0;
  if(readable){async=p[op==0?38:op==1?121:0];if(op!=4){dst=load64(p);fmt=load32(p+(op?52:28));w=load32(p+(op?72:16));h=load32(p+(op?76:20));if(op){src=load64(p+56);for(unsigned i=115;i<=120;i++)flags|=(U)p[i]<<(8*(i-115));flags|=(U)p[112]<<48|(U)p[113]<<56;}else flags=(U)p[36]<<8|p[37];}}
  dprintf(2,"FX3_GPE_CMD op=%s seq=%u async=%u fmt=%u w=%u h=%u dst_phys=%#lx src_phys=%#lx flags=%#lx result=%d reason=%d read=%d approx_blend=%d formula=%s selector=%u K=%u rotation=%u src_fmt=%u\n",op==0?"FillRect":op==1?"BitBlit":"Flush",seq,async,fmt,w,h,dst,src,flags,result,reason,readable,approx,approx?"straight_over_v1":"none",readable&&op!=4?p[op?112:36]:0,readable&&op!=4?p[op?114:37]:0,readable&&op==1?load32(p+104):0,readable&&op==1?load32(p+92):0);
 }
 if(n>200&&(total==1||(total&(total-1))==0)){
  dprintf(2,"FX3_GPE_CMD_SUMMARY op=%s total=%lu ok=%lu unsupported=%lu seen=%lu\n",op==0?"FillRect":op==1?"BitBlit":"Flush",total,__atomic_load_n(&stats[k].ok,__ATOMIC_RELAXED),__atomic_load_n(&stats[k].rejected,__ATOMIC_RELAXED),n);
 }
 if(op==1||result){
  char hex[289];unsigned len=op==0?56:op==1?144:24;
  const char *digits="0123456789abcdef";
  if(readable){for(unsigned i=0;i<len;i++){hex[2*i]=digits[p[i]>>4];hex[2*i+1]=digits[p[i]&15];}hex[2*len]=0;}
  else hex[0]=0;
  dprintf(2,"FX3_GPE_RAW_PARAMS op=%s seq=%u read=%d len=%u raw_hex=%s\n",op==0?"FillRect":op==1?"BitBlit":"Flush",seq,readable,readable?len:0,readable?hex:"unavailable");
 }
}
/* Callback is a process-local guest pointer, never a physical/DMM address.
 * Require an executable mapping before writes. This is not allocator pinning. */
static int executable_callback(U fn){
 if(!fn)return 1;
 char data[65536];int fd=open("/proc/self/maps",0);if(fd<0)return 0;long n=0,r;
 while(n<(long)sizeof(data)-1&&(r=read(fd,data+n,sizeof(data)-1-n))>0)n+=r;close(fd);
 if(n<=0||n>=(long)sizeof(data)-1)return 0;data[n]=0;char *line=data;
 while(*line){U lo,hi;char perms[5]={0};if(sscanf(line,"%lx-%lx %4s",&lo,&hi,perms)==3&&fn>=lo&&fn<hi&&perms[2]=='x'&&!(fn&3))return 1;while(*line&&*line!='\n')line++;if(*line)line++;}return 0;
}
static int within(U a,U step,U line,unsigned rows){
 if(a<PAYLOAD_BASE||a>=EXT_BASE+EXT_BYTES||!rows)return 0;
 for(unsigned y=0;y<rows;y++){U pos=a+(U)y*step;if(pos<a||pos>=EXT_BASE+EXT_BYTES||line>EXT_BASE+EXT_BYTES-pos)return 0;}return 1;
}
static int command(unsigned op,int g,int c,unsigned seq,unsigned src,const void *p){
 unsigned char raw[144]={0};unsigned len=op==0?56:op==1?144:24;
 int readable=p&&pread(process_mem,raw,len,(long)p)==len;
 int reason=GPE_INVALID,result=5,locked=0,life_held=0;void *area=(void *)-1,*source_area=(void*)-1;U source_bytes=0,source_page=0;struct gpe_plan plan;
 if(__atomic_test_and_set(&command_lock,__ATOMIC_ACQUIRE)){marker(op,seq,raw,readable,5,GPE_BUSY);return 5;}locked=1;
 if(!readable||g||c)goto done;
 unsigned ao=op==0?38:op==1?121:0,fo=op==0?40:op==1?128:8;
 U cb=load64(raw+fo),arg=load64(raw+fo+8);
 if(!executable_callback(cb))goto done;
 if(!raw[ao]&&src&&!draw_complete)goto done;
 if(op==4){
  /* Retain v12's successful-prior-draw and sticky failure gate. */
  if(raster_failed||!fills_done){reason=GPE_UNSUPPORTED;goto done;}
  for(unsigned i=1;i<8;i++)if(raw[i])goto done;
  reason=GPE_OK;
 }else{
  reason=op==0?gpe_plan_fill(raw,len,&plan):gpe_plan_blit(raw,len,&plan);if(reason)goto done;
  reason=GPE_UNSUPPORTED;
  if(!within(plan.dst,plan.dst_step,plan.line,plan.rows))goto done;
  life_enter();life_held=1;U event_before=__atomic_load_n(&allocation_events,__ATOMIC_RELAXED);
  struct screen_identity si={0},after_si={0};struct resource_record sr={0};unsigned count_before=0,count_after=0;
  if(!screen_live(&si)){reason=GPE_STALE;goto done;}
  int source_screen=op==1&&within(plan.src,plan.src_step,plan.src_line,plan.src_rows);
  if(op==1&&!source_screen){
   if(!obj_bound||!resource_lookup(plan.src,plan.src_step,plan.src_line,plan.src_rows,&sr)){reason=GPE_STALE;goto done;}
   (void)pread(process_mem,&count_before,4,(long)sr.object+0x24);
   U page=plan.src&~4095UL,tail=plan.src+(U)(plan.src_rows-1)*plan.src_step+plan.src_line;
   U requested=tail-page;if(requested>~0UL-4095){reason=GPE_BOUNDS;goto done;}
   source_bytes=(requested+4095)&~4095UL;source_page=page;
   source_area=mmap(0,source_bytes,1,1,physical,page);if(source_area==(void*)-1){reason=GPE_STALE;goto done;}
  }
  area=mmap(0,EXT_BYTES,3,1,physical,EXT_BASE);if(area==(void*)-1){reason=GPE_STALE;goto done;}
  if(!screen_live(&after_si)||si.serial!=after_si.serial){reason=GPE_STALE;goto done;}
  struct gpe_context ctx;struct gpe_ref dst_ref={0x81,si.serial},src_ref=dst_ref;
  gpe_init(&ctx,(struct gpe_hooks){0});reason=gpe_register(&ctx,dst_ref,EXT_BASE,area,EXT_BYTES);if(reason)goto done;
  if(op==1&&!source_screen){
   src_ref=(struct gpe_ref){sr.object,sr.epoch};
   /* Only the sampled source envelope is mapped read-only. The extra page
    * padding is never registered; no resource receives screen +0x100 rule. */
   U envelope=(U)(plan.src_rows-1)*plan.src_step+plan.src_line;
   reason=gpe_register(&ctx,src_ref,plan.src,(unsigned char*)source_area+plan.src-source_page,envelope);if(reason)goto done;
  }
  reason=gpe_begin_batch(&ctx,1);if(reason)goto done;
  unsigned char execution[144];__builtin_memcpy(execution,raw,len);execution[ao]=1;__builtin_memset(execution+fo,0,16);
  reason=gpe_submit(&ctx,op,seq,0,execution,len,dst_ref,src_ref);if(reason)goto done;
  __atomic_thread_fence(__ATOMIC_SEQ_CST);
  if(sr.object)(void)pread(process_mem,&count_after,4,(long)sr.object+0x24);
  U event_after=__atomic_load_n(&allocation_events,__ATOMIC_RELAXED);
  dprintf(2,"FX3_GPE_SCOPE seq=%u screen_extent_id=0x81 screen_type=0x545 screen_serial=%#lx source_object=%#lx source_uhdl=%#x source_epoch=%lu source_type=%#lx source_phys=%#lx source_bytes=%#lx interval_lease=1 subblock_lifetime_unproven=1 queued_ABA_uncovered=1 compaction_uncovered=1 compaction_or_subblock_change_during_draw=%u allocation_event_scope=all_heaps_conservative native_count_before=%u native_count_after=%u approx_fmt2=%u formula=%s original_fmt2_semantics_unproven=%u approx_stretch=%s\n",seq,si.serial,sr.object,sr.uhdl,sr.epoch,sr.type,sr.phys,sr.bytes,event_before!=event_after||count_before!=count_after,count_before,count_after,plan.approx_fmt2,plan.approx_fmt2?"a8_color_straight_over_v1_candidate":plan.approx_blend?"straight_over_v1":"none",plan.approx_fmt2,plan.approx_stretch?"nearest_v1":"none");
  if(!screen_live(&after_si)||si.serial!=after_si.serial){reason=GPE_STALE;goto done;}
  if(munmap(area,EXT_BYTES)){area=(void*)-1;reason=GPE_DELIVERY;goto done;}area=(void*)-1;
  if(source_area!=(void*)-1){if(munmap(source_area,source_bytes)){source_area=(void*)-1;reason=GPE_DELIVERY;goto done;}source_area=(void*)-1;}
  life_leave();life_held=0;fills_done++;
 }
 /* Matches callback parameter ABI and callback-before-status ordering. The
  * software callback runs inline on the existing FIFO worker (see README). */
 if(cb){struct gpe_callback_param cp={seq,0,arg};((void (*)(const void *))cb)(&cp);}
 if(!raw[ao]&&src){unsigned int status=0;if(!draw_complete(src,&status,4)){reason=GPE_DELIVERY;goto done;}}
 result=0;
 done:
 if(area!=(void *)-1)(void)munmap(area,EXT_BYTES);
 if(source_area!=(void*)-1)(void)munmap(source_area,source_bytes);
 if(life_held)life_leave();
 if(result&&op!=4)raster_failed=1;
 if(result&&reason==GPE_DELIVERY)raster_failed=1;
 marker(op,seq,raw,readable,result,reason);
 if(locked)__atomic_clear(&command_lock,__ATOMIC_RELEASE);
 /* Nonzero is returned to original Main, which alone sends failure status. */
 return result;
}
static int fill(int g,int c,unsigned seq,unsigned src,const void *p){return command(0,g,c,seq,src,p);}
static int blit(int g,int c,unsigned seq,unsigned src,const void *p){return command(1,g,c,seq,src,p);}
static int flush(int g,int c,unsigned seq,unsigned src,const void *p){return command(4,g,c,seq,src,p);}
static const char *names[]={
 "_ZN5mpgpe14InitializeDrawENS_3GpeE",
 "_ZNK5mpgpe5Gperm4InitEv",
 "_ZN5mpgpe8FillRectENS_3GpeENS_7IntCoreEjjRKNS_13FillRectParamE",
 "_ZN5mpgpe7BitBlitENS_3GpeENS_7IntCoreEjjRKNS_12BitBlitParamE",
 "_ZN5mpgpe5FlushENS_3GpeENS_7IntCoreEjjRKNS_10FlushParamE"};
static const U values[]={0xc1d0,0x9ae8,0xc30c,0xcf2c,0xc760};
static void *wrappers[]={init,gperm_init,fill,blit,flush};

static void *(*get_instance)(int,int);
static void software_setup(int gpe) {
 void *object=(gpe>=0&&gpe<2&&get_instance)?get_instance(gpe,0):0;
 dprintf(2,"FX3_GPE_SOFTWARE_SETUP gpe=%d object=%p original_get_instance=1 hardware_register_setup=0 supported_draw_gpe0_only=1\n",gpe,object);
 if(object)gperm_init(object);
}
static int install_setup(U base) {
 const unsigned char expected[16]={0xfd,0x7b,0xbb,0xa9,0xfd,0x03,0x00,0x91,0xf3,0x53,0x01,0xa9,0x14,0x7c,0x40,0x93};unsigned char *p=(void *)(base+0xdb74);
 for(unsigned int i=0;i<16;i++)if(p[i]!=expected[i])return 5;
 if(mprotect((void *)((U)p&~4095UL),4096,7))return 5;
 unsigned int words[2]={0x58000050,0xd61f0200};
 __builtin_memcpy(p,words,8);U fn=(U)software_setup;__builtin_memcpy(p+8,&fn,8);
 sync_instructions(p,16);
 if(mprotect((void *)((U)p&~4095UL),4096,5))_exit(126);
 dprintf(2,"FX3_GPE_SETUP_BIND relative=0xdb74 original_prefix_verified=16 original_fifo_main_unchanged=1\n");return 0;
}

static int install_worker_entries(U base){
 const U offsets[3]={0xc30c,0xcf2c,0xc760};void *targets[3]={(void *)fill,(void *)blit,(void *)flush};
 const unsigned char prefix[3][16]={{0xfd,0x7b,0xba,0xa9,0xfd,0x3,0x0,0x91,0xf5,0x5b,0x2,0xa9,0xf5,0x3,0x0,0x2a},{0xfd,0x7b,0xbc,0xa9,0xfd,0x3,0x0,0x91,0xf3,0x53,0x1,0xa9,0xf3,0x3,0x4,0xaa},{0x85,0x0,0x40,0x39,0x65,0x0,0x0,0x34,0x85,0x4,0x40,0xf9,0x65,0x4,0x0,0xb4}};
 for(unsigned int k=0;k<3;k++){const unsigned char *p=(void *)(base+offsets[k]);for(unsigned int i=0;i<16;i++)if(p[i]!=prefix[k][i])return 5;}
 for(unsigned int k=0;k<3;k++){unsigned char *p=(void *)(base+offsets[k]);if(mprotect((void *)((U)p&~4095UL),4096,7))return 5;
 unsigned int branch[2]={0x58000050,0xd61f0200};U dest=(U)targets[k];__builtin_memcpy(p,branch,8);__builtin_memcpy(p+8,&dest,8);sync_instructions(p,16);if(mprotect((void *)((U)p&~4095UL),4096,5))_exit(126);}
 dprintf(2,"FX3_GPE_WORKER_ENTRIES count=3 prefix_verified=16 direct_and_PLT_calls=1 originalFIFO=1\n");return 0;
}
static void bind_impl(void *h) {
 struct lm *map=0;if(__atomic_load_n(&armed,__ATOMIC_ACQUIRE) || dlinfo(h,2,&map) || !map) return;
 U base=map->base; const unsigned char *header=(void *)base;
 if(header[0]!=0x7f || header[1]!='E' || header[2]!='L' || header[3]!='F' || header[4]!=2) return;
 struct sym *syms=0;const char *strings=0;struct rela *relas=0;U bytes=0,stringsz=0,kind=0;
 for(unsigned int i=0;i<512;i++) {
  struct dyn d=map->dynamic[i];if(!d.tag)break;
  U v=d.val;if((d.tag==5||d.tag==6||d.tag==23) && v<base)v+=base;
  if(d.tag==5)strings=(void *)v;else if(d.tag==6)syms=(void *)v;else if(d.tag==23)relas=(void *)v;
  else if(d.tag==2)bytes=v;else if(d.tag==10)stringsz=v;else if(d.tag==20)kind=v;
 }
 if(!syms||!strings||!relas||!bytes||bytes%24||bytes>4096*24||!stringsz||stringsz>1048576||kind!=7)return;
 U *slots[5]={0};unsigned int seen[5]={0};
 for(U i=0;i<bytes/24;i++) {
  struct rela r=relas[i];if((unsigned int)r.info!=1026)continue;
  struct sym sym=syms[r.info>>32];if(sym.name>=stringsz)continue;
  for(unsigned int k=0;k<5;k++) if(!strcmp(strings+sym.name,names[k])) {
   if(sym.value!=values[k] || sym.shndx==0 || r.offset>0x30000) return;
   slots[k]=(void *)(base+r.offset);seen[k]++;
  }
 }
 for(unsigned int k=0;k<5;k++) {
  dprintf(2,"FX3_GPE_SLOT k=%u seen=%u current=%#lx expected=%#lx\n",k,seen[k],slots[k]?*slots[k]-base:0,values[k]);
  if(seen[k]!=1 || dlsym(h,names[k])!=(void *)(base+values[k]))return;
  if(*slots[k]!=base+values[k] && !(*slots[k]>=base+0x8700 && *slots[k]<base+0x9200))return;
 }
 physical=open("/dev/mem",2);if(process_mem<0)process_mem=open("/proc/self/mem",0);
 if(physical<0||process_mem<0)return;
 /* FX3 .got.plt page is RW in the audited original PT_LOAD, outside RELRO.
  * Reject different page placement; no A7C2 GOT offsets are used. */
 U page=(U)slots[0]&~4095UL;
 for(unsigned int k=0;k<5;k++)if(((U)slots[k]&~4095UL)!=page)return;
 draw_complete=dlsym(h,"_ZN5mpgpe7message12SendDrawCompEjPKvm");
 get_instance=dlsym(h,"_ZN5mpgpe5Gperm11GetInstanceENS_3GpeENS_7IntCoreE");
 if(!get_instance||install_setup(base)||install_worker_entries(base))return;
 for(unsigned int k=0;k<5;k++) {
  dprintf(2,"FX3_GPE_BIND name=%s slot_relative=%#lx original_relative=%#lx\n",names[k],(U)slots[k]-base,*slots[k]-base);
  __atomic_store_n(slots[k],(U)wrappers[k],__ATOMIC_RELEASE);
 }
 __atomic_store_n(&armed,1,__ATOMIC_RELEASE);dprintf(2,"FX3_GPE_BOUND count=5 symbol_relocations=1 original_fifo=1 completion_added=1 adapter=v16r2 early_thread_bind=1 resource_interval_registry=1 fmt2_candidate=1 nearest_candidate=1 approx_model=straight_over_v1 snapshot_guard=1\n");
}
static int bind(void *h) {
 if(__atomic_test_and_set(&binding_lock,__ATOMIC_ACQUIRE))return -2;
 bind_impl(h);int result=__atomic_load_n(&armed,__ATOMIC_ACQUIRE)?0:-1;
 __atomic_clear(&binding_lock,__ATOMIC_RELEASE);return result;
}

/* GpeInit ddcc creates exact gpe0_info/1_info before lazy dlopen binding
 * can finish on another thread. Do not let these original worker entries
 * run until the existing software setup/GOT binding is completely armed. */
static int (*native_create_thread)(const void *);
#ifdef FX3_GPE_HOST_TEST
static int (*host_early_bind_override)(void *);
#endif
static int match_gpe_thread(const void *info,U base){
 if(!base||((U)info!=base+0x297c0&&(U)info!=base+0x297e8))return -1;
 const U *w=info;int g=(U)info==base+0x297c0?0:1;
 if(w[0]!=base+(g?0x1574e:0x15759)||w[1]!=4||w[2]!=base+(g?0xdce4:0xdcb0)||w[3]||w[4]!=0x288)return -1;
 return g;
}
int osal_create_thread(const void *info){
 int saved=*__errno_location();int(*fn)(const void *)=__atomic_load_n(&native_create_thread,__ATOMIC_ACQUIRE);
 if(!fn){fn=dlsym((void *)-1,"osal_create_thread");if(!fn)_exit(126);__atomic_store_n(&native_create_thread,fn,__ATOMIC_RELEASE);}
 struct app_dl_info location={0};int g=-1;
 if(info&&dladdr(info,&location))g=match_gpe_thread(info,(U)location.base);
 if(g>=0){
  void *(*open_next)(const char *,int)=__atomic_load_n(&loader,__ATOMIC_ACQUIRE);
  if(!open_next){open_next=dlsym((void *)-1,"dlopen");if(open_next)__atomic_store_n(&loader,open_next,__ATOMIC_RELEASE);}
  void*h=open_next?open_next("libgpe.so",5):0;struct lm*map=0;
  if(!h||dlinfo(h,2,&map)||!map||map->base!=(U)location.base){dprintf(2,"FX3_GPE_EARLY_BIND_REJECT gpe=%d reason=original_NOLOAD_identity native_thread_not_created=1\n",g);_exit(126);}
  unsigned yielded=0;int rc;
  for(;;){
#ifdef FX3_GPE_HOST_TEST
   rc=host_early_bind_override?host_early_bind_override(h):bind(h);
#else
   rc=bind(h);
#endif
   if(rc!=-2)break;yielded++;syscall(124);
  }
  if(rc||!__atomic_load_n(&armed,__ATOMIC_ACQUIRE)){dprintf(2,"FX3_GPE_EARLY_BIND_REJECT gpe=%d reason=existing_bind_failed native_thread_not_created=1 result=%d\n",g,rc);_exit(126);}
  dprintf(2,"FX3_GPE_EARLY_THREAD_GATE gpe=%d info_relative=%#lx entry_relative=%#lx armed=1 wait_yields=%u original_thread_create_follows=1 original_args_unchanged=1 no_register_model=1\n",g,(U)info-(U)location.base,((const U*)info)[2]-(U)location.base,yielded);
 }
 *__errno_location()=saved;int result=fn(info);int after=*__errno_location();
 if(g>=0)dprintf(2,"FX3_GPE_EARLY_THREAD_RETURN gpe=%d result=%d errno=%d native_return=1\n",g,result,after);
 *__errno_location()=after;return result;
}
#ifdef FX3_GPE_HOST_TEST
#define dlopen host_interposer_dlopen
#endif
void *dlopen(const char *name,int flags) {
 int saved=*__errno_location();void *(*fn)(const char *,int)=__atomic_load_n(&loader,__ATOMIC_ACQUIRE);if(!fn){fn=dlsym((void *)-1,"dlopen");__atomic_store_n(&loader,fn,__ATOMIC_RELEASE);}if(!fn)_exit(126);
 *__errno_location()=saved;void *h=fn(name,flags);int result_errno=*__errno_location();
 if(h&&!__atomic_load_n(&armed,__ATOMIC_ACQUIRE)){dprintf(2,"FX3_GPE_LOAD name=%s flags=%#x\n",name?name:"NULL",flags);void *gpe=fn("libgpe.so",6);if(gpe)bind(gpe);}
 if(h&&!__atomic_load_n(&obj_bound,__ATOMIC_ACQUIRE)){void*obj=fn("libObj.so",5);if(obj)bind_resources(obj);}
 if(h&&name&&(!strcmp(name,"appFw.so")||!strcmp(name,"/usr/lib/appFw.so")))bind_app(h);
 *__errno_location()=result_errno;return h;
}

void bt_error_place(void *,unsigned short,unsigned int)
#ifndef FX3_GPE_HOST_TEST
 __asm__("_ZN8BTUtils_6BTBlog10errorPlaceEtj")
#endif
;
void bt_error_place(void *self,unsigned short group,unsigned int line){
 int before=*__errno_location();struct app_dl_info info={0};void *caller=__builtin_return_address(0);dladdr(caller,&info);
 dprintf(2,"FX3_BT_ERROR self=%p group=%u line=%u caller=%s+%#lx original_delegated=1\n",self,group,line,info.file?info.file:"?",info.base?(U)caller-(U)info.base:0);
 void (*fn)(void *,unsigned short,unsigned int)=dlsym((void *)-1,"_ZN8BTUtils_6BTBlog10errorPlaceEtj");if(!fn||fn==bt_error_place)_exit(126);
 *__errno_location()=before;fn(self,group,line);
}
