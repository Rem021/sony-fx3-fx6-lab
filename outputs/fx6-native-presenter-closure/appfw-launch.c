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

    /* Q1/Q2 closure: initialize genuine libMWF.so before loading/entering appFw.so */
    fx6_mwf_lifecycle();

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
