/* AArch64 Linux diagnostic bridge. No guest helper, kernel, or Sony binary is executed by the build. */
#include <stddef.h>
#include <stdint.h>
#include "bridge_core.h"
#include "bridge_pins.h"
#include "sha256.h"

typedef struct { const char* dli_fname; void* dli_fbase; const char* dli_sname; void* dli_saddr; } fx6diag_dl_info;
extern void* dlopen(const char*, int);
extern void* dlsym(void*, const char*);
extern int dladdr(const void*, fx6diag_dl_info*);
extern int open(const char*, int, ...);
extern long read(int, void*, unsigned long);
extern int close(int);
extern void fx6diag_failstop(void) __attribute__((noreturn));
extern int32_t fx6diag_call_original(const uint8_t*, void*);
extern void* const fx6diag_slot_table[57];
extern void fx6diag_mpr_enterrec(void);

/* Public for read-only debugger inspection; storage remains process-lifetime. */
volatile uint32_t fx6diag_state; /* 0 new, 1 building, 2 published, 3 calling, 4 returned */
volatile uint32_t fx6diag_fail_reason;
volatile int32_t fx6diag_original_return;
uint64_t fx6diag_original_callbacks[57];
uint64_t fx6diag_bound_thunks[57];
uint64_t fx6diag_extra_callbacks[18];
uint8_t fx6diag_mapped_record[FX6DIAG_TARGET_BYTES];
uint32_t fx6diag_extra_nonnull;
uint64_t fx6diag_verified_ap_base;
uint64_t fx6diag_verified_mpr_base;
uint64_t fx6diag_verified_original_init;

enum {
    FAIL_REENTRY=1, FAIL_AP_IDENTITY=2, FAIL_ORIGINAL_MPR=3,
    FAIL_THUNK_IDENTITY=4, FAIL_SOURCE_FIELD=5, FAIL_CALLBACK_ADDRESS=6,
    FAIL_PUBLISH_STATE=7
};
static __attribute__((noreturn)) void fail(uint32_t reason) {
    fx6diag_fail_reason=reason;
    __atomic_thread_fence(__ATOMIC_RELEASE);
    fx6diag_failstop();
}
static int equal32(const uint8_t a[32],const uint8_t b[32]) {
    uint8_t d=0;for(unsigned i=0;i<32;i++)d|=a[i]^b[i];return d==0;
}
static int hash_file(const char* path,const uint8_t expected[32],uint64_t size) {
    if(!path||!path[0])return 0;
    int fd=open(path,0);
    if(fd<0)return 0;
    fx6_sha256_ctx c;fx6_sha256_init(&c);
    uint8_t block[4096];uint64_t total=0;
    for(;;) {
        long n=read(fd,block,sizeof(block));
        if(n<0){close(fd);return 0;}
        if(n==0)break;
        total+=(uint64_t)n;
        if(total>size){close(fd);return 0;}
        fx6_sha256_update(&c,block,(size_t)n);
    }
    if(close(fd)!=0||total!=size)return 0;
    uint8_t digest[32];fx6_sha256_final(&c,digest);
    return equal32(digest,expected);
}
static uint32_t rd32(const void* address) {
    const uint8_t* p=(const uint8_t*)address;
    return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);
}
static uintptr_t verify_ap(void* return_pc) {
    fx6diag_dl_info info;
    if(!dladdr(return_pc,&info)||!info.dli_fbase)return 0;
    uintptr_t base=(uintptr_t)info.dli_fbase;
    if((uintptr_t)return_pc-base!=0x212f7bc) return 0;
    if(!hash_file(info.dli_fname,fx6diag_expected_ap_sha,50520424))return 0;
    if(rd32((void*)(base+0x212f7b8))!=0x97a79f42)return 0;
    return base;
}
static uintptr_t verify_mpr(void** original) {
    /* NOLOAD: never bring in a substitute MPR as a side effect of this bridge. */
    void* handle=dlopen("libmpr.so",2|4);
    if(!handle)handle=dlopen("/usr/lib/libmpr.so",2|4);
    if(!handle)return 0;
    void* p=dlsym(handle,"_ZN3mpr4InitERKNS_11initInParamE");
    fx6diag_dl_info info;
    if(!p||!dladdr(p,&info)||!info.dli_fbase)return 0;
    uintptr_t base=(uintptr_t)info.dli_fbase;
    if((uintptr_t)p-base!=0xb6844)return 0;
    if(!hash_file(info.dli_fname,fx6diag_expected_mpr_sha,3517008))return 0;
    if(rd32(p)!=0xa9b27bfd)return 0;
    *original=p;
    return base;
}
static int verify_thunks(uintptr_t out[57]) {
    fx6diag_dl_info own;
    if(!dladdr((void*)&fx6diag_mpr_enterrec,&own)||!own.dli_fbase)return 0;
    uintptr_t base=(uintptr_t)own.dli_fbase;
    if(rd32((void*)&fx6diag_mpr_enterrec)!=(0xd4200000u|(0x7f0u<<5)))return 0;
    for(unsigned i=0;i<57;i++) {
        uintptr_t p=(uintptr_t)fx6diag_slot_table[i];
        fx6diag_dl_info info;
        if(!p||!dladdr((void*)p,&info)||info.dli_fbase!=(void*)base||info.dli_saddr!=(void*)p)
            return 0;
        if(rd32((void*)p)!=(0xd4200000u|((0x600u+i)<<5)))return 0;
        for(unsigned j=0;j<i;j++)if(out[j]==p)return 0;
        out[i]=p;
    }
    return 1;
}
static int all_callbacks_in_ap(const fx6diag_plan* plan,uintptr_t base) {
    const uintptr_t end=base+0x2900a17u; /* executable PT_LOAD filesz from pinned AP */
    for(unsigned i=0;i<57;i++) {
        uintptr_t p=(uintptr_t)plan->original_callbacks[i];
        if(p&&(p<base||p>=end||(p&3)))return 0;
    }
    for(unsigned i=0;i<18;i++) {
        uintptr_t p=(uintptr_t)plan->original_extra[i];
        if(p&&(p<base||p>=end||(p&3)))return 0;
    }
    return 1;
}

/* This symbol is the only patched Init import. AAPCS x0 points to the 0x290 record. */
int32_t fx6diag_mpr_init(const uint8_t* source) {
    uint32_t expected=0;
    if(!__atomic_compare_exchange_n(&fx6diag_state,&expected,1,0,
                                    __ATOMIC_ACQ_REL,__ATOMIC_ACQUIRE))fail(FAIL_REENTRY);
    uintptr_t ap=verify_ap(__builtin_return_address(0));
    if(!ap)fail(FAIL_AP_IDENTITY);
    void* original=0;uintptr_t mpr=verify_mpr(&original);
    if(!mpr)fail(FAIL_ORIGINAL_MPR);
    uintptr_t thunk_addresses[57];
    if(!verify_thunks(thunk_addresses))fail(FAIL_THUNK_IDENTITY);
    fx6diag_plan plan;
    if(fx6diag_map(source,FX6DIAG_SOURCE_BYTES,thunk_addresses,&plan)!=FX6DIAG_MAP_OK)
        fail(FAIL_SOURCE_FIELD);
    if(!all_callbacks_in_ap(&plan,ap))fail(FAIL_CALLBACK_ADDRESS);
    for(unsigned i=0;i<57;i++) {
        fx6diag_original_callbacks[i]=plan.original_callbacks[i];
        fx6diag_bound_thunks[i]=plan.target_thunks[i];
    }
    for(unsigned i=0;i<18;i++)fx6diag_extra_callbacks[i]=plan.original_extra[i];
    for(unsigned i=0;i<FX6DIAG_TARGET_BYTES;i++)fx6diag_mapped_record[i]=plan.mapped[i];
    fx6diag_extra_nonnull=plan.extra_nonnull;
    fx6diag_verified_ap_base=ap;
    fx6diag_verified_mpr_base=mpr;
    fx6diag_verified_original_init=(uint64_t)(uintptr_t)original;
    __atomic_store_n(&fx6diag_state,2,__ATOMIC_RELEASE); /* callbacks published before Sony Init */
    expected=2;
    if(!__atomic_compare_exchange_n(&fx6diag_state,&expected,3,0,
                                    __ATOMIC_ACQ_REL,__ATOMIC_ACQUIRE))fail(FAIL_PUBLISH_STATE);
    int32_t rc=fx6diag_call_original(fx6diag_mapped_record,original);
    fx6diag_original_return=rc;
    __atomic_store_n(&fx6diag_state,4,__ATOMIC_RELEASE);
    return rc; /* Preserve every real return code, including nonzero. */
}
