/* FX3 original FIFO retained; symbol-derived binding and bounded request capture.
 * No raster/ACK is fabricated: workers reject pending ownership/layout validation.
 */
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
static int capture(const char *name,int gpe,int core,unsigned int sequence,unsigned int source,const void *p,unsigned int length) {
 unsigned char raw[144];char hex[289];static const char digits[]="0123456789abcdef";
 unsigned int n=__atomic_fetch_add(&requests,1,__ATOMIC_RELAXED);
 long rc=p?pread(process_mem,raw,length,(long)p):-1;
 if(n<64) {
  unsigned int count=rc>0?(unsigned int)rc:0;
  for(unsigned int i=0;i<count;i++){hex[2*i]=digits[raw[i]>>4];hex[2*i+1]=digits[raw[i]&15];} hex[2*count]=0;
  dprintf(2,"FX3_GPE_REQUEST op=%s n=%u gpe=%d core=%d sequence=%u source=%#x read=%ld raw=%s result=5 completed=0 pixels_written=0 reason=allocation_lease_and_FX3_layout_pending\n",name,n,gpe,core,sequence,source,rc,hex);
 }
 return 5;
}
static int fill(int g,int c,unsigned int seq,unsigned int src,const void *p){return capture("fill",g,c,seq,src,p,56);}
static int blit(int g,int c,unsigned int seq,unsigned int src,const void *p){return capture("blit",g,c,seq,src,p,144);}
static int flush(int g,int c,unsigned int seq,unsigned int src,const void *p){return capture("flush",g,c,seq,src,p,24);}
static const char *names[]={
 "_ZN5mpgpe14InitializeDrawENS_3GpeE",
 "_ZNK5mpgpe5Gperm4InitEv",
 "_ZN5mpgpe8FillRectENS_3GpeENS_7IntCoreEjjRKNS_13FillRectParamE",
 "_ZN5mpgpe7BitBlitENS_3GpeENS_7IntCoreEjjRKNS_12BitBlitParamE",
 "_ZN5mpgpe5FlushENS_3GpeENS_7IntCoreEjjRKNS_10FlushParamE"};
static const U values[]={0xc1d0,0x9ae8,0xc30c,0xcf2c,0xc760};
static void *wrappers[]={init,gperm_init,fill,blit,flush};
static void bind(void *h) {
 struct lm *map=0;if(armed || dlinfo(h,2,&map) || !map) return;
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
 for(unsigned int k=0;k<5;k++) {
  dprintf(2,"FX3_GPE_BIND name=%s slot_relative=%#lx original_relative=%#lx\n",names[k],(U)slots[k]-base,*slots[k]-base);
  __atomic_store_n(slots[k],(U)wrappers[k],__ATOMIC_RELEASE);
 }
 armed=1;dprintf(2,"FX3_GPE_BOUND count=5 symbol_relocations=1 original_fifo=1 completion_added=0\n");
}
void *dlopen(const char *name,int flags) {
 int saved=*__errno_location();if(!loader)loader=dlsym((void *)-1,"dlopen");if(!loader)_exit(126);
 *__errno_location()=saved;void *h=loader(name,flags);int result_errno=*__errno_location();
 if(h&&!armed){dprintf(2,"FX3_GPE_LOAD name=%s flags=%#x\n",name?name:"NULL",flags);void *gpe=loader("libgpe.so",6);if(gpe)bind(gpe);}
 *__errno_location()=result_errno;return h;
}
