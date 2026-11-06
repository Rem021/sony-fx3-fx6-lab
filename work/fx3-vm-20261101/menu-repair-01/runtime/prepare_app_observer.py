from pathlib import Path
import json,hashlib,subprocess,os
R=Path(__file__).resolve().parent
s=(R/'helpers/fx3-gpe-observe-v4.c').read_text()
a='static unsigned char binding_lock;'
extra='''extern void *mmap(void *,size_t,int,int,int,long);
extern long syscall(long,...);
struct app_dl_info {const char *file;void *base;const char *symbol;void *address;};
extern int dladdr(const void *,struct app_dl_info *);
static void *(*app_original)(void *);
static unsigned char app_lock;
static int app_bound;
static void sync_instructions(unsigned char *p,U n){
 U ctr;__asm__ volatile("mrs %0, ctr_el0":"=r"(ctr));U dc=4UL<<((ctr>>16)&15),ic=4UL<<(ctr&15);
 for(U a=(U)p&~(dc-1);a<(U)p+n;a+=dc)__asm__ volatile("dc cvau, %0"::"r"(a):"memory");
 __asm__ volatile("dsb ish":::"memory");
 for(U a=(U)p&~(ic-1);a<(U)p+n;a+=ic)__asm__ volatile("ic ivau, %0"::"r"(a):"memory");
 __asm__ volatile("dsb ish; isb":::"memory");
}
static void *app_observe(void *arg){
 int before=*__errno_location();long tid=syscall(178);
 dprintf(2,"FX3_APP_INIT_ENTER tid=%ld argument=%p original_delegated=1\\n",tid,arg);
 *__errno_location()=before;void *(*fn)(void *)=__atomic_load_n(&app_original,__ATOMIC_ACQUIRE);
 if(!fn)_exit(126);void *result=fn(arg);int after=*__errno_location();
 dprintf(2,"FX3_APP_INIT_RETURN tid=%ld result=%p errno=%d original_delegated=1\\n",tid,result,after);
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
 dprintf(2,"FX3_APP_INIT_BIND relative=0x16efb90 prefix_verified=16 relocated_adrp=2 result_unchanged=1\\n");
 done: __atomic_clear(&app_lock,__ATOMIC_RELEASE);
}
'''
assert a in s;s=s.replace(a,extra+'\n'+a)
a=' *__errno_location()=result_errno;return h;'
s=s.replace(a,' if(h&&name&&(!strcmp(name,"appFw.so")||!strcmp(name,"/usr/lib/appFw.so")))bind_app(h);\n'+a)
(R/'helpers/fx3-gpe-observe-v5.c').write_text(s)
v=json.loads((R/'helpers/fx3-gpe-observe-v4-build.json').read_text());args=[a.replace('fx3-gpe-observe-v4.c','fx3-gpe-observe-v5.c').replace('fx3-gpe-observe-v4.so','fx3-gpe-observe-v5.so') for a in v['args']];env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(R/'toolchains/zig-cache');env['ZIG_LOCAL_CACHE_DIR']=str(R/'toolchains/zig-local-cache');p=subprocess.run(args,env=env,capture_output=True,text=True);assert p.returncode==0,p.stderr;(R/'helpers/fx3-gpe-observe-v5-build.json').write_text(json.dumps({'args':args,'exit':p.returncode,'stderr':p.stderr,'source_sha256':hashlib.sha256((R/'helpers/fx3-gpe-observe-v5.c').read_bytes()).hexdigest(),'scope':'original FX3 app init entry/return observer, exact16bytes and 2 ADRP relocations'},indent=2)+'\n')
print('compiled app observer')
