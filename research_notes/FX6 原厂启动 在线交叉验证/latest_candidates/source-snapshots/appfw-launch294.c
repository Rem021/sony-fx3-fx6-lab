#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <signal.h>
#include <ucontext.h>
#include <unistd.h>
#include <sys/mman.h>
#include <link.h>
#include <elf.h>
#include <stdint.h>
#include <string.h>
#include <errno.h>

#include "/tmp/got_table_fx6.inc"

typedef void (*init_fn)(void *);

static void segv_handler(int sig, siginfo_t *si, void *ctx) {
    ucontext_t *uc = (ucontext_t *)ctx;
    fprintf(stderr, "APPFW_SEGV sig=%d addr=%p pc=%llx sp=%llx\n",
            sig, si->si_addr,
            (unsigned long long)uc->uc_mcontext.pc,
            (unsigned long long)uc->uc_mcontext.sp);
    for (int i = 0; i < 31; i++)
        fprintf(stderr, "APPFW_X%d=%llx\n", i, (unsigned long long)uc->uc_mcontext.regs[i]);
    {
        Dl_info di;
        if (dladdr((void *)uc->uc_mcontext.pc, &di))
            fprintf(stderr, "APPFW_PC_MODULE %s base=%p\n", di.dli_fname, di.dli_fbase);
        if (dladdr((void *)uc->uc_mcontext.regs[30], &di))
            fprintf(stderr, "APPFW_LR_MODULE %s base=%p\n", di.dli_fname, di.dli_fbase);
        {
            FILE *mf = fopen("/proc/self/maps", "r");
            if (mf) {
                char line[512];
                unsigned long pc = (unsigned long)uc->uc_mcontext.pc;
                while (fgets(line, sizeof(line), mf)) {
                    unsigned long a = 0, b = 0;
                    if (sscanf(line, "%lx-%lx", &a, &b) == 2 && pc >= a && pc < b) {
                        fprintf(stderr, "APPFW_PC_MAP %s", line);
                        break;
                    }
                }
                fclose(mf);
            }
        }
    }
    _exit(139);
}

static void fix_got_table(void *init, void *sh) {
    Dl_info info;
    if (!dladdr(init, &info) || !info.dli_fbase) {
        fprintf(stderr, "fix_got_table: dladdr failed\n");
        return;
    }
    uintptr_t base = (uintptr_t)info.dli_fbase;
    int fixed = 0, missing = 0, shown = 0;
    size_t n = sizeof(got_tab) / sizeof(got_tab[0]);
    for (size_t i = 0; i < n; i++) {
        void *addr = sh ? dlsym(sh, got_tab[i].name) : NULL;
        if (!addr) addr = dlsym(RTLD_DEFAULT, got_tab[i].name);
        if (!addr) {
            missing++;
            if (shown < 15) { fprintf(stderr, "fix_got_table: missing %s\n", got_tab[i].name); shown++; }
            continue;
        }
        uintptr_t *slot = (uintptr_t *)(base + got_tab[i].off);
        uintptr_t page = (uintptr_t)slot & ~0xfffUL;
        int mr = mprotect((void *)page, 0x4000, PROT_READ | PROT_WRITE | PROT_EXEC);
        uintptr_t before = *slot;
        *slot = (uintptr_t)addr;
        if (got_tab[i].off == 0x47cd430UL || got_tab[i].off == 0x47cc620UL) {
            fprintf(stderr, "fix_got_detail: off=%lx slot=%p before=%lx after=%lx target=%p mprotect=%d errno=%d\n",
                    got_tab[i].off, (void*)slot, (unsigned long)before, (unsigned long)*slot, addr, mr, errno);
        }
        fixed++;
    }
    fprintf(stderr, "fix_got_table: base=%p entries=%zu fixed=%d missing=%d\n",
            (void *)base, n, fixed, missing);
}

static unsigned char app_ctx[0x10000];
static void *ge_instance = NULL;

static void pre(const char *p) {
    void *h = dlopen(p, RTLD_NOW | RTLD_GLOBAL);
    if (!h) fprintf(stderr, "appfw-launch: preload %s failed: %s\n", p, dlerror());
    else fprintf(stderr, "appfw-launch: preload %s=%p\n", p, h);
}

int main(void) {
    struct sigaction sa;
    sa.sa_sigaction = segv_handler;
    sa.sa_flags = SA_SIGINFO;
    sigemptyset(&sa.sa_mask);
    sigaction(SIGSEGV, &sa, NULL);
    sigaction(SIGBUS, &sa, NULL);
    void *sh0 = dlopen("/usr/lib/libgrm-fbinit9.so", RTLD_NOW | RTLD_GLOBAL);
    if (!sh0) { fprintf(stderr, "appfw-launch: stub preload failed: %s\n", dlerror()); return 3; }
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
    void *h = dlopen("/usr/lib/appFw.so", RTLD_LAZY | RTLD_GLOBAL);
    if (!h) { fprintf(stderr, "appfw-launch: dlopen appFw failed: %s\n", dlerror()); return 1; }
    init_fn init = sh0 ? (init_fn)dlsym(sh0, "Application_System_Init") : 0;
    if (!init) { fprintf(stderr, "appfw-launch: stub dlsym failed: %s\n", dlerror()); return 2; }
    void *real_entry = dlsym(h, "Application_System_Init");
    fix_got_table(real_entry ? real_entry : (void *)init, sh0);
    fprintf(stderr, "appfw-launch: stub_entry=%p real_entry=%p\n", (void*)init, real_entry);
    fprintf(stderr, "appfw-launch: sleeping 30s before init()\n");
    sleep(1);
    init("AppConfig.so");
    fprintf(stderr, "appfw-launch: Application_System_Init returned\n");
    {
        void (*uinit)(void) = (void (*)(void))dlsym(RTLD_DEFAULT, "uxengine_init2");
        fprintf(stderr, "appfw-launch: uxengine_init2=%p\n", (void*)uinit);
        if (uinit) {
            Dl_info di;
            if (dladdr((void*)uinit, &di) && di.dli_fbase) {
                uintptr_t *slot = (uintptr_t *)((uintptr_t)di.dli_fbase + 0x48800UL);
                uintptr_t page = (uintptr_t)slot & ~0xfffUL;
                mprotect((void*)page, 0x4000, PROT_READ | PROT_WRITE | PROT_EXEC);
                *slot = (uintptr_t)app_ctx;
                fprintf(stderr, "appfw-launch: patched 0x48800 base=%p slot=%p -> %p\n",
                        di.dli_fbase, (void*)slot, (void*)app_ctx);
                uintptr_t *slot2 = (uintptr_t *)((uintptr_t)di.dli_fbase + 0x48810UL);
                uintptr_t page2 = (uintptr_t)slot2 & ~0xfffUL;
                mprotect((void*)page2, 0x4000, PROT_READ | PROT_WRITE | PROT_EXEC);
                *slot2 = (uintptr_t)app_ctx;
                fprintf(stderr, "appfw-launch: patched 0x48810 base=%p slot=%p -> %p\n",
                        di.dli_fbase, (void*)slot2, (void*)app_ctx);
            }
            {
                void *s = dlsym(RTLD_DEFAULT, "_ZN2ux6gfxeng14GraphicsEngine15drawFramebufferEv");
                Dl_info di;
                if (s && dladdr(s, &di) && di.dli_fbase) {
                    uint32_t *p = (uint32_t *)((uintptr_t)di.dli_fbase + 0x82c74UL);
                    uintptr_t page = (uintptr_t)p & ~0xfffUL;
                    mprotect((void*)page, 0x4000, PROT_READ | PROT_WRITE | PROT_EXEC);
                    p[0] = 0xd2800000u; /* mov x0, #0 */
                    p[1] = 0xd65f03c0u; /* ret */
                    for (uintptr_t off = 0x82c74UL; off < 0x82ce0UL; off += 8) {
                        uint32_t *q = (uint32_t *)((uintptr_t)di.dli_fbase + off);
                        uintptr_t pageq = (uintptr_t)q & ~0xfffUL;
                        mprotect((void*)pageq, 0x4000, PROT_READ | PROT_WRITE | PROT_EXEC);
                        q[0] = 0x52800000u; /* mov w0, #0 */
                        q[1] = 0xd65f03c0u; /* ret */
                    }
                    fprintf(stderr, "appfw-launch: patched getter range %p..%p\n",
                            (void*)((uintptr_t)di.dli_fbase + 0x82c74UL),
                            (void*)((uintptr_t)di.dli_fbase + 0x82ce0UL));
                }
            }
            uinit();
            fprintf(stderr, "appfw-launch: uxengine_init2 returned\n");
            {
                void *(*gfx)(void) = (void *(*)(void))dlsym(RTLD_DEFAULT, "_ZN8UXEngine6gfxengEv");
                void *(*create)(void *, const void *) = (void *(*)(void *, const void *))dlsym(RTLD_DEFAULT, "_ZN2ux6gfxeng14GraphicsEngine14createScreen3DERKNS_4core2IDE");
                void (*draw)(void *) = (void (*)(void *))dlsym(RTLD_DEFAULT, "_ZN2ux6gfxeng14GraphicsEngine15drawFramebufferEv");
                {
                    void *s2 = dlsym(RTLD_DEFAULT, "_ZN2ux6gfxeng14GraphicsEngine15drawFramebufferEv");
                    Dl_info di2;
                    if (s2 && dladdr(s2, &di2) && di2.dli_fbase) {
                        {
                            void *uc = dlsym(RTLD_DEFAULT, "uxengine_init2");
                            Dl_info diu;
                            if (uc && dladdr(uc, &diu) && diu.dli_fbase) {
                                uint32_t *pg = (uint32_t *)((uintptr_t)diu.dli_fbase + 0x30e50UL);
                                uintptr_t pageg = (uintptr_t)pg & ~0xfffUL;
                                mprotect((void*)pageg, 0x4000, PROT_READ | PROT_WRITE | PROT_EXEC);
                                pg[0] = 0x52800000u; /* mov w0, #0 */
                                pg[1] = 0xd65f03c0u; /* ret */
                                uint32_t *pg2 = (uint32_t *)((uintptr_t)diu.dli_fbase + 0x30e68UL);
                                uintptr_t pageg2 = (uintptr_t)pg2 & ~0xfffUL;
                                mprotect((void*)pageg2, 0x4000, PROT_READ | PROT_WRITE | PROT_EXEC);
                                pg2[0] = 0x52800000u; /* mov w0, #0 */
                                pg2[1] = 0xd65f03c0u; /* ret */
                                fprintf(stderr, "appfw-launch: patched 0x30e50/0x30e68 base=%p slot=%p/%p\n",
                                        diu.dli_fbase, (void*)pg, (void*)pg2);
                            }
                        }
                        {
                            void *gs = dlsym(RTLD_DEFAULT, "_ZN6gemini10AngleStackD0Ev");
                            Dl_info dg;
                            if (gs && dladdr(gs, &dg) && dg.dli_fbase) {
                                uint32_t *pg = (uint32_t *)((uintptr_t)dg.dli_fbase + 0x8cc0UL);
                                uintptr_t pageg = (uintptr_t)pg & ~0xfffUL;
                                mprotect((void*)pageg, 0x4000, PROT_READ | PROT_WRITE | PROT_EXEC);
                                pg[0] = 0xd503201fu; /* nop */
                                fprintf(stderr, "appfw-launch: patched gemini 0x8cc0 base=%p slot=%p\n",
                                        dg.dli_fbase, (void*)pg);
                            }
                        }
                        unsigned char *ge_buf = (unsigned char *)malloc(0x10000);
                        if (ge_buf) memset(ge_buf, 0, 0x10000);
                        void (*ge_ctor)(void *) = (void (*)(void *))dlsym(RTLD_DEFAULT, "_ZN2ux6gfxeng14GraphicsEngineC1Ev");
                        fprintf(stderr, "appfw-launch: GraphicsEngine ctor=%p ge_buf=%p\n", (void*)ge_ctor, (void*)ge_buf);
                        if (ge_ctor && ge_buf) { ge_ctor(ge_buf); fprintf(stderr, "appfw-launch: GraphicsEngine ctor returned\n"); }
                        ge_instance = ge_buf;
                        void **slot = (void **)((uintptr_t)di2.dli_fbase + 0xc1f78UL);
                        uintptr_t page = (uintptr_t)slot & ~0xfffUL;
                        mprotect((void*)page, 0x4000, PROT_READ | PROT_WRITE | PROT_EXEC);
                        *slot = &ge_instance;
                        fprintf(stderr, "appfw-launch: patched 0xc1f78 base=%p slot=%p -> &ge_instance(%p)\n",
                                di2.dli_fbase, (void*)slot, (void*)&ge_instance);
                    }
                }
                void *ge = gfx ? gfx() : NULL;
                fprintf(stderr, "appfw-launch: gfxeng=%p createScreen3D=%p drawFramebuffer=%p ge=%p\n",
                        (void*)gfx, (void*)create, (void*)draw, ge);
                if (0 && ge && create) {
                    unsigned char id[16] = {0};
                    void *scr = create(ge, id);
                    fprintf(stderr, "appfw-launch: createScreen3D returned %p\n", scr);
                }
                if (ge && draw) { draw(ge); fprintf(stderr, "appfw-launch: drawFramebuffer returned\n"); }
            }
        }
    }
    fprintf(stderr, "appfw-launch: keeping process alive\n");
    sleep(300);
    return 0;
}
