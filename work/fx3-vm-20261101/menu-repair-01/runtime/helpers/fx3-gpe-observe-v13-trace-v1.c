/* v13: original v12 binding/FIFO retained; bounded backend adapter. */
#include "fx3-gpe-backend.h"
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
static int extent_live(void){
 char data[65536];int fd=open("/proc/udm/dmm_extents",0);if(fd<0)return 0;long n=0,part;while(n<(long)sizeof(data)-1&&(part=read(fd,data+n,sizeof(data)-1-n))>0)n+=part;close(fd);if(n<=0||n>=(long)sizeof(data)-1)return 0;data[n]=0;
 char *line=data;while(line&&*line){unsigned int a,b,c,d,e,f,g,h;unsigned long start,parent,offset,bytes;
 if(sscanf(line,"%x %x %x %x %x %x %x %x %lx (%lx+%lx) %lx",&a,&b,&c,&d,&e,&f,&g,&h,&start,&parent,&offset,&bytes)==12&&d==0x545&&c==1&&g==3&&start==0x43feb5000UL&&bytes==0x140000UL)return 1;
 while(*line&&*line!='\n')line++;if(*line)line++;else break;}return 0;
}
#define EXT_BASE 0x43feb5000UL
#define EXT_BYTES 0x140000UL
#define PAYLOAD_BASE (EXT_BASE+0x100UL)
static unsigned char command_lock;
struct cmd_stats {unsigned long total,ok,rejected;};
static struct cmd_stats stats[3];
static unsigned long seen;
static unsigned int load32(const unsigned char *p){unsigned int v;__builtin_memcpy(&v,p,4);return v;}
static U load64(const unsigned char *p){U v;__builtin_memcpy(&v,p,8);return v;}
static void marker(unsigned op,unsigned seq,const unsigned char *p,int readable,int result,int reason){
 if(readable){unsigned len=op==0?56:op==1?144:24;char hex[289];const char *digits="0123456789abcdef";for(unsigned i=0;i<len;i++){hex[i*2]=digits[p[i]>>4];hex[i*2+1]=digits[p[i]&15];}hex[len*2]=0;dprintf(2,"FX3_GPE_RAW op=%s seq=%u bytes=%u selector=%u alpha=%u src_fmt=%u conversion=%u rotation=%u result=%d reason=%d raw=%s v13_behavior_unchanged=1\n",op==0?"FillRect":op==1?"BitBlit":"Flush",seq,len,op==0?p[36]:op==1?p[112]:0,op==0?p[37]:op==1?p[114]:0,op==1?load32(p+92):0,op==1?p[113]:0,op==1?load32(p+104):0,result,reason,hex);}

 unsigned k=op==4?2:op;U n=__atomic_add_fetch(&seen,1,__ATOMIC_RELAXED);
 U total=__atomic_add_fetch(&stats[k].total,1,__ATOMIC_RELAXED);
 __atomic_add_fetch(result?&stats[k].rejected:&stats[k].ok,1,__ATOMIC_RELAXED);
 if(n<=200){
  unsigned fmt=0,w=0,h=0,async=0;U dst=0,src=0,flags=0;
  if(readable){async=p[op==0?38:op==1?121:0];if(op!=4){dst=load64(p);fmt=load32(p+(op?52:28));w=load32(p+(op?72:16));h=load32(p+(op?76:20));if(op){src=load64(p+56);for(unsigned i=115;i<=120;i++)flags|=(U)p[i]<<(8*(i-115));flags|=(U)p[112]<<48|(U)p[113]<<56;}else flags=(U)p[36]<<8|p[37];}}
  dprintf(2,"FX3_GPE_CMD op=%s seq=%u async=%u fmt=%u w=%u h=%u dst_phys=%#lx src_phys=%#lx flags=%#lx result=%d reason=%d read=%d\n",op==0?"FillRect":op==1?"BitBlit":"Flush",seq,async,fmt,w,h,dst,src,flags,result,reason,readable);
 }else if(total==1||(total&(total-1))==0){
  dprintf(2,"FX3_GPE_CMD_SUMMARY op=%s total=%lu ok=%lu unsupported=%lu seen=%lu\n",op==0?"FillRect":op==1?"BitBlit":"Flush",total,__atomic_load_n(&stats[k].ok,__ATOMIC_RELAXED),__atomic_load_n(&stats[k].rejected,__ATOMIC_RELAXED),n);
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
 int reason=GPE_INVALID,result=5,locked=0;void *area=(void *)-1;struct gpe_plan plan;
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
  if(!within(plan.dst,plan.dst_step,plan.line,plan.rows)||(op==1&&!within(plan.src,plan.src_step,plan.line,plan.rows))||!extent_live())goto done;
  area=mmap(0,EXT_BYTES,3,1,physical,EXT_BASE);if(area==(void *)-1){reason=GPE_STALE;goto done;}
  if(!extent_live()){reason=GPE_STALE;goto done;}
  struct gpe_context ctx;struct gpe_ref ref={0x545,1};
  gpe_init(&ctx,(struct gpe_hooks){0});reason=gpe_register(&ctx,ref,EXT_BASE,area,EXT_BYTES);
  if(reason)goto done;reason=gpe_begin_batch(&ctx,1);if(reason)goto done;
  unsigned char execution[144];__builtin_memcpy(execution,raw,len);execution[ao]=1;__builtin_memset(execution+fo,0,16);
  reason=gpe_submit(&ctx,op,seq,0,execution,len,ref,ref);if(reason)goto done;
  __atomic_thread_fence(__ATOMIC_SEQ_CST);
  if(!extent_live()){reason=GPE_STALE;goto done;}
  if(munmap(area,EXT_BYTES)){area=(void *)-1;reason=GPE_DELIVERY;goto done;}area=(void *)-1;
  fills_done++;
 }
 /* Matches callback parameter ABI and callback-before-status ordering. The
  * software callback runs inline on the existing FIFO worker (see README). */
 if(cb){struct gpe_callback_param cp={seq,0,arg};((void (*)(const void *))cb)(&cp);}
 if(!raw[ao]&&src){unsigned int status=0;if(!draw_complete(src,&status,4)){reason=GPE_DELIVERY;goto done;}}
 result=0;
 done:
 if(area!=(void *)-1)(void)munmap(area,EXT_BYTES);
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
 physical=open("/dev/mem",2);process_mem=open("/proc/self/mem",0);
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
 __atomic_store_n(&armed,1,__ATOMIC_RELEASE);dprintf(2,"FX3_GPE_BOUND count=5 symbol_relocations=1 original_fifo=1 completion_added=1 adapter=v13\n");
}
static void bind(void *h) {
 if(__atomic_test_and_set(&binding_lock,__ATOMIC_ACQUIRE))return;
 bind_impl(h);
 __atomic_clear(&binding_lock,__ATOMIC_RELEASE);
}
#ifdef FX3_GPE_HOST_TEST
#define dlopen host_interposer_dlopen
#endif
void *dlopen(const char *name,int flags) {
 int saved=*__errno_location();void *(*fn)(const char *,int)=__atomic_load_n(&loader,__ATOMIC_ACQUIRE);if(!fn){fn=dlsym((void *)-1,"dlopen");__atomic_store_n(&loader,fn,__ATOMIC_RELEASE);}if(!fn)_exit(126);
 *__errno_location()=saved;void *h=fn(name,flags);int result_errno=*__errno_location();
 if(h&&!__atomic_load_n(&armed,__ATOMIC_ACQUIRE)){dprintf(2,"FX3_GPE_LOAD name=%s flags=%#x\n",name?name:"NULL",flags);void *gpe=fn("libgpe.so",6);if(gpe)bind(gpe);}
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
