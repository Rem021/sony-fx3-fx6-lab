#define _GNU_SOURCE
#include <dlfcn.h>
#include <elf.h>
#include <errno.h>
#include <link.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <ucontext.h>
#include <unistd.h>

#include "got_table_fx6.inc"

#ifndef FX6_NATIVE_FAITHFUL
#define FX6_NATIVE_FAITHFUL 1
#endif

#ifndef FX6_ROUND
#define FX6_ROUND (FX6_NATIVE_FAITHFUL ? 7 : 3)
#endif

typedef void (*init_fn)(const char *);
typedef void (*mwf_init_fn)(void);

static int ptr_readable(uintptr_t p) {
    return (p >= 0x10000UL) && ((p >> 40) == 0UL) && ((p & 0x7UL) == 0UL);
}

static void log_addr_module(const char *tag, uintptr_t addr) {
    Dl_info di;
    memset(&di, 0, sizeof(di));
    if (addr && dladdr((void *)addr, &di) && di.dli_fbase) {
        uintptr_t off = addr - (uintptr_t)di.dli_fbase;
        fprintf(stderr, "%s addr=0x%llx module=%s+0x%lx base=%p sym=%s\n",
                tag,
                (unsigned long long)addr,
                di.dli_fname ? di.dli_fname : "?",
                (unsigned long)off,
                di.dli_fbase,
                di.dli_sname ? di.dli_sname : "?");
    } else {
        fprintf(stderr, "%s addr=0x%llx module=unknown\n", tag, (unsigned long long)addr);
    }
}

static void segv_handler(int sig, siginfo_t *si, void *ctx) {
    ucontext_t *uc = (ucontext_t *)ctx;
    uintptr_t pc = (uintptr_t)uc->uc_mcontext.pc;
    uintptr_t lr = (uintptr_t)uc->uc_mcontext.regs[30];
    uintptr_t fp = (uintptr_t)uc->uc_mcontext.regs[29];
    fprintf(stderr, "APPFW_SEGV sig=%d code=%d addr=%p pc=0x%llx lr=0x%llx sp=0x%llx\n",
            sig,
            si ? si->si_code : 0,
            si ? si->si_addr : NULL,
            (unsigned long long)pc,
            (unsigned long long)lr,
            (unsigned long long)uc->uc_mcontext.sp);
    for (int i = 0; i < 31; i++) {
        fprintf(stderr, "APPFW_X%d=0x%llx\n", i, (unsigned long long)uc->uc_mcontext.regs[i]);
    }
    log_addr_module("APPFW_PC_MODULE", pc);
    log_addr_module("APPFW_LR_MODULE", lr);
    for (int depth = 0; depth < 12 && ptr_readable(fp); depth++) {
        uintptr_t next_fp = ((const uintptr_t *)fp)[0];
        uintptr_t ret_pc = ((const uintptr_t *)fp)[1];
        char tag[32];
        snprintf(tag, sizeof(tag), "APPFW_FP_BT_%d", depth);
        log_addr_module(tag, ret_pc);
        if (next_fp <= fp || (next_fp - fp) > 0x100000UL) break;
        fp = next_fp;
    }
    FILE *mf = fopen("/proc/self/maps", "r");
    if (mf) {
        char line[512];
        while (fgets(line, sizeof(line), mf)) {
            unsigned long a = 0, b = 0;
            if (sscanf(line, "%lx-%lx", &a, &b) == 2 && pc >= a && pc < b) {
                fprintf(stderr, "APPFW_PC_MAP %s", line);
                break;
            }
        }
        fclose(mf);
    }
    fflush(stderr);
    _exit(128 + (sig & 0x7f));
}

static void fx6_mwf_lifecycle(void) {
    void *mwf = dlopen("/usr/lib/libMWF.so", RTLD_NOW | RTLD_GLOBAL);
    if (!mwf) {
        fprintf(stderr, "FX6_MWF_OPEN_FAILED error=%s\n", dlerror());
        _exit(123);
    }
    mwf_init_fn mwf_init = (mwf_init_fn)dlsym(mwf, "MWF_Init");
    void **mon_err = (void **)dlsym(mwf, "_ZN3MWF6RsrcDP10smp_monErrE");
    void **lock_mgr = (void **)dlsym(mwf, "_ZN3MWF12RsrcRelation15mp_objShLockMgrE");
    void **lock_acsr = (void **)dlsym(mwf, "_ZN3MWF12RsrcRelation16mp_objShLockAcsrE");
    void **lock_glob = (void **)dlsym(mwf, "_ZN3MWF12RsrcRelation18mp_objShLockGlobalE");
    if (!mwf_init || !mon_err || !lock_mgr || !lock_acsr || !lock_glob) {
        fprintf(stderr,
                "FX6_MWF_SYM_FAILED fn=%p mon_err=%p mgr=%p acsr=%p glob=%p err=%s\n",
                (void *)mwf_init, (void *)mon_err, (void *)lock_mgr,
                (void *)lock_acsr, (void *)lock_glob, dlerror());
        _exit(123);
    }
    fprintf(stderr,
            "FX6_MWF_PRE fn=%p smp_monErr=%p shLockMgr=%p shLockAcsr=%p shLockGlobal=%p\n",
            (void *)mwf_init, *mon_err, *lock_mgr, *lock_acsr, *lock_glob);
    fflush(stderr);

    mwf_init();

    fprintf(stderr,
            "FX6_MWF_POST smp_monErr=%p shLockMgr=%p shLockAcsr=%p shLockGlobal=%p lock_bypass=0\n",
            *mon_err, *lock_mgr, *lock_acsr, *lock_glob);
    fflush(stderr);

    if (!*mon_err || !*lock_mgr || !*lock_acsr || !*lock_glob) {
        fprintf(stderr, "FX6_MWF_POST_INVARIANT_FAILED\n");
        _exit(124);
    }
}

#if defined(FX6_ROUND) && (FX6_ROUND >= 4)
static void fx6_media_config_lifecycle(void) {
    void *imcfg = dlopen("/usr/lib/libInfraMediaConfig.so", RTLD_NOW | RTLD_GLOBAL);
    if (!imcfg) {
        fprintf(stderr, "FX6_IMCFG_OPEN_FAILED error=%s\n", dlerror());
        _exit(123);
    }
    mwf_init_fn imcfg_init = (mwf_init_fn)dlsym(imcfg, "InfraMediaConfig_Init");
    Dl_info di;
    memset(&di, 0, sizeof(di));
    if (!imcfg_init || !dladdr((void *)imcfg_init, &di) || !di.dli_fbase) {
        fprintf(stderr, "FX6_IMCFG_SYM_FAILED fn=%p err=%s\n", (void *)imcfg_init, dlerror());
        _exit(123);
    }
    uintptr_t base = (uintptr_t)di.dli_fbase;
    /* libInfraMediaConfig.so +0x6770 stores InfraMediaConfig* singleton at +0x1c470 */
    void **singleton_slot = (void **)(base + 0x1c470UL);
    fprintf(stderr, "FX6_IMCFG_PRE fn=%p base=%p singleton=%p\n",
            (void *)imcfg_init, di.dli_fbase, *singleton_slot);
    fflush(stderr);

    imcfg_init();

    void *inst = *singleton_slot;
    unsigned int slot_cnt = 0, s0_id = 0, s0_dev = 0, s1_id = 0, s1_dev = 0;
    if (ptr_readable((uintptr_t)inst)) {
        slot_cnt = *((const uint8_t *)inst + 0x20);
        const uint8_t *tbl = *(const uint8_t * const *)((const char *)inst + 0x18);
        if (ptr_readable((uintptr_t)tbl) && slot_cnt >= 1U) {
            s0_id = *(const uint32_t *)(tbl + 0x00);
            s0_dev = *(const uint16_t *)(tbl + 0x06);
        }
        if (ptr_readable((uintptr_t)tbl) && slot_cnt >= 2U) {
            s1_id = *(const uint32_t *)(tbl + 0x110);
            s1_dev = *(const uint16_t *)(tbl + 0x110 + 0x06);
        }
    }
    fprintf(stderr,
            "FX6_IMCFG_POST singleton=%p slot_count=%u slot0_id=0x%x slot0_dev=0x%x slot1_id=0x%x slot1_dev=0x%x\n",
            inst, slot_cnt, s0_id, s0_dev, s1_id, s1_dev);
    fflush(stderr);
}

static void fx6_infra_input_lifecycle(void) {
    void *in_lib = dlopen("/usr/lib/libInfraInput.so", RTLD_NOW | RTLD_GLOBAL);
    if (!in_lib) {
        fprintf(stderr, "FX6_INFRA_INPUT_OPEN_FAILED error=%s\n", dlerror());
        return;
    }
    typedef void (*in_init_fn)(void);
    typedef void *(*in_get_fn)(void);
    in_init_fn fn_init = (in_init_fn)dlsym(in_lib, "infra_input_init");
    in_get_fn fn_get = (in_get_fn)dlsym(in_lib, "_ZN10InfraInput11GetInstanceEv");
    if (fn_init) fn_init();
    void *inst = fn_get ? fn_get() : NULL;
    int key_cnt = 0;
    int pw_sw_found = 0;
    unsigned int pw_sw_status = 0U;
    if (ptr_readable((uintptr_t)inst)) {
        key_cnt = *(const int *)((const char *)inst + 0x2c);
        const uint8_t *cfg = *(const uint8_t * const *)((const char *)inst + 0x20);
        uint8_t *cache = *(uint8_t * const *)((const char *)inst + 0x38);
        if (key_cnt > 0 && key_cnt <= 4096 && ptr_readable((uintptr_t)cfg) && ptr_readable((uintptr_t)cache)) {
            for (int i = 0; i < key_cnt; i++) {
                uint32_t dev = *(const uint32_t *)(cfg + (size_t)i * 0x30UL + 0x00UL);
                uint32_t phy_id = *(const uint32_t *)(cfg + (size_t)i * 0x30UL + 0x08UL);
                uint8_t *ce = cache + (size_t)i * 0x2cUL;
                uint32_t st = (phy_id == 1U) ? 1U : 0U; /* phy_key_id 1 == PW_SW (Power Switch ON) */
                *(uint32_t *)(ce + 0x00UL) = dev;
                *(uint32_t *)(ce + 0x04UL) = phy_id;
                *(uint32_t *)(ce + 0x08UL) = st;
                *(uint32_t *)(ce + 0x0cUL) = 0U;
                *(uint32_t *)(ce + 0x10UL) = 0U;
                if (phy_id == 1U) {
                    pw_sw_found = 1;
                    pw_sw_status = st;
                }
            }
        }
    }
    fprintf(stderr,
            "FX6_INFRA_INPUT_POST inst=%p key_cnt=%d pw_sw_found=%d pw_sw_status=%u\n",
            inst, key_cnt, pw_sw_found, pw_sw_status);
    fflush(stderr);
}
#endif

static void fix_got_table(void *init_sym, void *sh) {
    Dl_info info;
    if (!dladdr(init_sym, &info) || !info.dli_fbase) {
        fprintf(stderr, "fix_got_table: dladdr failed\n");
        return;
    }
    uintptr_t base = (uintptr_t)info.dli_fbase;
    void *observer_handle = dlopen("/usr/lib/libfx6-queue-observer.so", RTLD_NOW | RTLD_GLOBAL);
    void *observer_receive = observer_handle ? dlsym(observer_handle, "osal_rcv_msg_tmo") : NULL;
    Dl_info observer_info = {0};
    if (!observer_receive || !dladdr(observer_receive, &observer_info) || !observer_info.dli_fname ||
        !strstr(observer_info.dli_fname, "libfx6-queue-observer.so")) {
        fprintf(stderr, "FX6_QUEUE_OBS_BIND_FAILED handle=%p function=%p error=%s\n",
                observer_handle, observer_receive, dlerror());
        _exit(125);
    }
    fprintf(stderr, "FX6_QUEUE_OBS_LIBRARY base=%p function=%p owner=%s\n",
            observer_info.dli_fbase, observer_receive, observer_info.dli_fname);

    int fixed = 0, missing = 0, shown = 0, skipped_tlsdesc = 0;
    size_t n = sizeof(got_tab) / sizeof(got_tab[0]);
    for (size_t i = 0; i < n; i++) {
        /* 0x2ef29f0 (_ZSt11__once_call) and 0x2ef2a00 (_ZSt15__once_callable) are
           16-byte R_AARCH64_TLSDESC descriptors resolved by ld-linux; overwriting word 0
           with dlsym() corrupts the TLS resolver function pointer into rw-p data! */
        if (got_tab[i].off == 0x2ef29f0UL || got_tab[i].off == 0x2ef2a00UL) {
            skipped_tlsdesc++;
            continue;
        }
        int observe_receive = strcmp(got_tab[i].name, "osal_rcv_msg_tmo") == 0;
        void *addr = observe_receive ? observer_receive : (sh ? dlsym(sh, got_tab[i].name) : NULL);
        if (!addr) addr = dlsym(RTLD_DEFAULT, got_tab[i].name);
        if (!addr) {
            missing++;
            if (shown < 15) {
                fprintf(stderr, "fix_got_table: missing %s\n", got_tab[i].name);
                shown++;
            }
            continue;
        }
        uintptr_t *slot = (uintptr_t *)(base + got_tab[i].off);
        uintptr_t page = (uintptr_t)slot & ~0xfffUL;
        int mr = mprotect((void *)page, 0x4000, PROT_READ | PROT_WRITE | PROT_EXEC);
        uintptr_t before = *slot;
        *slot = (uintptr_t)addr;
        if (observe_receive) {
            int saved_errno = errno;
            uintptr_t readback = *(volatile uintptr_t *)slot;
            Dl_info previous_owner = {0}, readback_owner = {0};
            dladdr((void *)before, &previous_owner);
            dladdr((void *)readback, &readback_owner);
            fprintf(stderr,
                    "FX6_QUEUE_OBS_GOT off=0x%lx slot=%p before=%p previous_owner=%s requested=%p readback=%p owner=%s mprotect=%d\n",
                    got_tab[i].off, (void *)slot, (void *)before,
                    previous_owner.dli_fname ? previous_owner.dli_fname : "?",
                    addr, (void *)readback,
                    readback_owner.dli_fname ? readback_owner.dli_fname : "?", mr);
            errno = saved_errno;
        }
        fixed++;
    }
    fprintf(stderr, "fix_got_table: base=%p entries=%zu fixed=%d skipped_tlsdesc=%d missing=%d\n",
            (void *)base, n, fixed, skipped_tlsdesc, missing);
}

static void pre(const char *p) {
    void *h = dlopen(p, RTLD_NOW | RTLD_GLOBAL);
    if (!h) fprintf(stderr, "appfw-launch: preload %s failed: %s\n", p, dlerror());
    else fprintf(stderr, "appfw-launch: preload %s=%p\n", p, h);
}

int main(void) {
    struct sigaction sa;
    memset(&sa, 0, sizeof(sa));
    sa.sa_sigaction = segv_handler;
    sa.sa_flags = SA_SIGINFO;
    sigemptyset(&sa.sa_mask);
    sigaction(SIGSEGV, &sa, NULL);
    sigaction(SIGBUS, &sa, NULL);
    sigaction(SIGILL, &sa, NULL);
    sigaction(SIGABRT, &sa, NULL);

    void *sh0 = dlopen("/usr/lib/libgrm-fbinit9.so", RTLD_NOW | RTLD_GLOBAL);
    if (!sh0) {
        fprintf(stderr, "appfw-launch: stub preload failed: %s\n", dlerror());
        return 3;
    }
    fprintf(stderr, "appfw-launch: stub first=%p\n", sh0);
    pre("/usr/lib/libosal_utm.so");
    pre("/usr/lib/libosal_uipc.so");
    pre("/usr/lib/libbackup.so");
    pre("/usr/lib/libMWF.so");
    pre("/usr/lib/libInfraMediaCommon.so");
    pre("/usr/lib/libInfraFsys.so");
    pre("/usr/lib/libInfraInput.so");
    pre("/usr/lib/libUsbControl.so");
    pre("/usr/lib/libarchstub.so");
    pre("/usr/lib/libutil_date.so");
    pre("/usr/lib/libInfraLanc.so");
    pre("/usr/lib/libObj.so");
    pre("/usr/lib/libgrm_bmp.so");
    pre("/usr/lib/libux_core.so");
    pre("/usr/lib/libgrm.so");
    pre("/usr/lib/libuxengine.so");
    pre("/usr/lib/libgrm-fbinit9.so");
    pre("/usr/lib/libInfraTp.so");
    pre("/usr/lib/libcrypto.so.3");
    pre("/usr/lib/libssl.so.3");
    pre("/usr/lib/libmpr.so");
    pre("/usr/lib/libicryptstub.so");
    pre("/usr/lib/libuxstub.so");
    pre("/usr/lib/libInfraDial.so");
    pre("/usr/lib/libInfraKikiLogGenerator.so");
    pre("/usr/lib/libInfraRemote.so");
    pre("/usr/lib/libInfraAccessLog.so");
    pre("/usr/lib/libInfraInterchipDatatrans.so");
#if defined(FX6_ROUND) && (FX6_ROUND >= 4)
    {
        static const char * const k_r4_libs[] = {
            "/lib/libSTMcmdexecute.so",
            "/usr/lib/libSysDef.so",
            "/usr/lib/libcurl.so.4",
            "/usr/lib/libCertificateManager.so",
            "/usr/lib/dataflowInfraFramework.so",
            "/usr/lib/libInfraIndctr.so",
            "/usr/lib/libEMG.so",
            "/usr/lib/libGetLog.so",
            "/usr/lib/libpng.so.16",
            "/usr/lib/libexpat.so.1",
            "/usr/lib/libopus.so.0",
            "/usr/lib/libSoundTouch.so.1",
            "/usr/lib/libtestcmd.so",
        };
        for (size_t i = 0; i < sizeof(k_r4_libs) / sizeof(k_r4_libs[0]); i++) {
            void *lh = dlopen(k_r4_libs[i], RTLD_LAZY | RTLD_GLOBAL);
            fprintf(stderr, "appfw-launch: r4_preload %s=%p err=%s\n",
                    k_r4_libs[i], lh, lh ? "ok" : dlerror());
        }
    }
#endif

    /* Q1/Q2 closure: initialize genuine libMWF.so before loading/entering appFw.so */
    fx6_mwf_lifecycle();
#if defined(FX6_ROUND) && (FX6_ROUND >= 4)
    /* Round 4 media-slot & physical switch contracts: initialize libInfraMediaConfig.so + libInfraInput.so */
    fx6_media_config_lifecycle();
    fx6_infra_input_lifecycle();
#endif

    void *h = dlopen("/usr/lib/appFw.so", RTLD_LAZY | RTLD_GLOBAL);
    if (!h) {
        fprintf(stderr, "appfw-launch: dlopen appFw failed: %s\n", dlerror());
        return 1;
    }
    init_fn init = sh0 ? (init_fn)dlsym(sh0, "Application_System_Init") : NULL;
    if (!init) {
        fprintf(stderr, "appfw-launch: stub dlsym failed: %s\n", dlerror());
        return 2;
    }
    void *real_entry = dlsym(h, "Application_System_Init");
    fix_got_table(real_entry ? real_entry : (void *)init, sh0);
    fprintf(stderr, "appfw-launch: stub_entry=%p real_entry=%p\n", (void *)init, real_entry);
    fflush(stderr);
    sleep(1);
    init("AppConfig.so");
    fprintf(stderr, "appfw-launch: Application_System_Init returned unexpectedly; holding\n");
    for (;;) sleep(3600);
}
