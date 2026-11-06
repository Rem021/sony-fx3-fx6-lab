typedef unsigned long U;typedef unsigned int W;typedef unsigned long size_t;
extern void *dlsym(void *,const char *);extern int dlinfo(void *,int,void *);extern int dprintf(int,const char *,...);extern int *__errno_location(void);extern int open(const char *,int,...);extern long read(int,void *,size_t);extern int close(int);extern long syscall(long,...);extern void *mmap(void *,size_t,int,int,int,long);extern int munmap(void *,size_t);extern int mprotect(void *,size_t,int);extern void *memcpy(void *,const void *,size_t);extern void *memset(void *,int,size_t);extern char *strstr(const char *,const char *);
struct ts{long s,n;};extern int clock_gettime(int,struct ts *);
struct lm{U base;char *name;void *dynamic;struct lm *next,*prev;};
struct ctx{U pc,continuation,id,objreg;};
extern long pread(int,void *,size_t,long);extern char *getenv(const char *);extern int strcmp(const char *,const char *);
extern void fx3_media_probe_core(void);extern int fx3_media_test(void),fx3_media_branch_test(int),fx3_media_bl_test(int);extern char fx3_media_test_point[],fx3_media_test_cb[],fx3_media_test_bl[];
__attribute__((visibility("hidden"))) int fx3_media_test_compare(U *p){for(int i=0;i<31;i++)if(p[i]!=(U)(0x100+i))return i+1;unsigned char *q=(void *)(p+32);for(int i=0;i<32;i++)for(int j=0;j<16;j++)if(q[i*16+j]!=i+1)return 100+i;if(p[96]!=0xa0000000)return 200;if(p[97]||p[98])return 202;if(p[124]!=(U)p)return 201;return 0;}

struct di {const char *file;void *base;const char *symbol;void *symaddr;};extern int dladdr(void *,struct di *);
extern int pthread_create(U *,const void *,void *(*)(void *),void *);extern int pthread_detach(U);extern int usleep(unsigned);
#include "fx3-media-params-v1.inc"
#include "fx3-media-points-v1.inc"
static int pmem=-1,active,binding,selftest_done;static U app_base,dbase,mbase,sequence;static int bound_D,bound_M,param_started;
static int peek(U p,void *out,U n){return pmem>=0&&p>=4096&&p<0x8000000000UL&&n<=0x8000000000UL-p&&pread(pmem,out,n,p)==(long)n;}
static W word(U p){W v=0xffffffffU;peek(p,&v,4);return v;}static U pointer(U p){U v=0;peek(p,&v,8);return v;}
static U stamp(void){struct ts t={0};clock_gettime(1,&t);return (U)t.s*1000000000UL+t.n;}
static __thread U eid;static __thread int inside;
static void raw(const char *tag,U p,U n){int saved=*__errno_location();char hex[8193];unsigned char b[4096];if(n>4096||!peek(p,b,n)){dprintf(2,"FX3_MEDIA_RAW eid=%lu tid=%ld tag=%s pointer=%#lx bytes=%lu readable=0 limit=4096 passive=1\n",eid,syscall(178),tag,p,n);*__errno_location()=saved;return;}const char *h="0123456789abcdef";for(U i=0;i<n;i++){hex[2*i]=h[b[i]>>4];hex[2*i+1]=h[b[i]&15];}hex[2*n]=0;dprintf(2,"FX3_MEDIA_RAW eid=%lu tid=%ld tag=%s pointer=%#lx bytes=%lu readable=1 raw=%s passive=1\n",eid,syscall(178),tag,p,n,hex);*__errno_location()=saved;}
static void frame(U pc,unsigned depth){struct di d={0};dladdr((void*)pc,&d);dprintf(2,"FX3_MEDIA_STACK eid=%lu tid=%ld depth=%u pc=%#lx module=%s relative=%#lx passive=1\n",eid,syscall(178),depth,pc,d.file?d.file:"unknown",d.base?pc-(U)d.base:0);}
static void stack(U pc,U fp){frame(pc,0);for(unsigned j=1;j<=12;j++){U v[2];if((fp&15)||!peek(fp,v,16))break;if(!v[1])break;frame(v[1],j);if(v[0]<=fp||v[0]-fp>0x100000||(v[0]&15))break;fp=v[0];}}
static void ports(const char *tag,U self){raw(tag,self+0x268,72);}
static void record(const char *tag,U p){raw(tag,p,0x3c);dprintf(2,"FX3_MEDIA_RECORD eid=%lu tid=%ld tag=%s record=%#lx mediaID=%#x state=%u mask=%#x notify_destination=%#x passive=1\n",eid,syscall(178),tag,p,word(p+0xc),word(p+0x38),word(p+0x14),word(p+0x1c));}
static W last_cur[10],last_shadow[10];static unsigned last_valid[10];static int param_lock;
static void sample(const char *why){if(!app_base||__atomic_test_and_set(&param_lock,__ATOMIC_ACQUIRE))return;for(unsigned i=0;i<10;i++){W a=0,b=0;unsigned ok=peek(app_base+params[i].offset,&a,params[i].size)&&peek(app_base+params[i].shadow_offset,&b,params[i].size);if(!last_valid[i]||ok!=last_valid[i]||a!=last_cur[i]||b!=last_shadow[i]){dprintf(2,"FX3_MEDIA_PARAM eid=%lu tid=%ld ns=%lu reason=%s id=%#lx current=%#x shadow=%#x bytes=%u readable=%u offset=%#lx read_only=1\n",eid,syscall(178),stamp(),why,params[i].id,a,b,params[i].size,ok,params[i].offset);last_cur[i]=a;last_shadow[i]=b;last_valid[i]=ok;}}__atomic_clear(&param_lock,__ATOMIC_RELEASE);}
static void *sampler(void *unused){(void)unused;for(;;){sample("period100ms_target");usleep(100000);}return 0;}
struct call {U self,payload,sp,caller,token;};static __thread struct call rm,status_call,mount_call;

extern long pwrite(int,const void *,U,long);extern int fsync(int);extern void abort(void);
long fx3_host_tid(long n,...){(void)n;return 7;}
#define CHECK(c) do{if(!(c))abort();}while(0)
int main(int argc,char **argv){CHECK(argc==2);pmem=open(argv[1],0x602,0600);CHECK(pmem>=0);unsigned char b[4096];for(unsigned i=0;i<4096;i++)b[i]=(unsigned char)i;CHECK(pwrite(pmem,b,4096,4096)==4096);fsync(pmem);unsigned char out[4096];CHECK(peek(4096,out,4096));CHECK(!__builtin_memcmp(b,out,4096));CHECK(!peek(4095,out,1));CHECK(!peek(0x8000000000UL,out,0));CHECK(!peek(0x7fffffffffUL,out,2));CHECK(!peek(4096,out,~0UL));CHECK(!peek(12288,out,1));
 *__errno_location()=73;raw("host_valid",4096,32);CHECK(*__errno_location()==73);raw("host_oversize",4096,4097);CHECK(*__errno_location()==73);raw("host_unmapped",12288,32);CHECK(*__errno_location()==73);
 U f[2]={0x1001,0};CHECK(pwrite(pmem,f,16,6144)==16);stack((U)main,6144);CHECK(*__errno_location()==73);CHECK(peek(4096,out,4096));CHECK(!__builtin_memcmp(b,out,2048));CHECK(!__builtin_memcmp(b+2064,out+2064,4096-2064));close(pmem);return 0;}
