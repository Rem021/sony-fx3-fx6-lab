/* fx6_static_assist.h — static-derived patches for FX6 522+ (terminal B)
 * No drawing. Only native control-state initialization.
 *
 * Assumptions:
 *   appfw   = load base of /usr/lib/appFw.so
 *   uxengine= load base of /usr/lib/libuxengine.so
 *   all offsets are module-relative, aarch64 LP64.
 */
#ifndef FX6_STATIC_ASSIST_H
#define FX6_STATIC_ASSIST_H

#include <stdint.h>

extern int mprotect(void *addr, unsigned long len, int prot);
extern int dprintf(int fd, const char *fmt, ...);
extern void *dlopen(const char *file, int mode);
extern void *dlsym(void *handle, const char *name);
typedef struct { const char *dli_fname; void *dli_fbase; const char *dli_sname; void *dli_saddr; } fx6_dl_info;
extern int dladdr(const void *addr, fx6_dl_info *info);

/* ---------------------------------------------------------------- model */
/* appFw+0x2127750 is a request dispatcher:
 *   out[0] = id; out[1] = -1; out[2..5] = 0; then osal request.
 * Callers 0x2127b04 / 0x2127d60 read the same out and then store the
 * 0x215ca08 result at out+0x18.  A success spoof only needs:
 *   out[0]=id, out[1]=0, out[2..7]=0, return 0.
 */
static inline long fx6_model_spoof(unsigned id, unsigned mode,
                                   unsigned param, void *out)
{
    (void)mode; (void)param;
    if (out) {
        uint32_t *p = (uint32_t *)out;
        for (int i = 0; i < 8; i++) p[i] = 0;
        p[0] = id;   /* request/object id */
        p[1] = 0;    /* 0 = success, original writes -1 before I/O */
    }
    return 0;
}

static inline void fx6_install_model_spoof(uint64_t appfw);
static inline void fx6_model_ready(uint64_t appfw);

/* Resolve appFw base without relying on g_appfw_base (521 observed base=0). */
typedef struct {
    uint64_t dlpi_addr;
    const char *dlpi_name;
    const void *dlpi_phdr;
    uint16_t dlpi_phnum;
} fx6_dl_phdr_info;
extern int dl_iterate_phdr(int (*cb)(fx6_dl_phdr_info *, unsigned long, void *), void *data);

static inline int fx6_appfw_base_cb(fx6_dl_phdr_info *info, unsigned long size, void *data)
{
    (void)size;
    const char *n = info ? info->dlpi_name : 0;
    if (!n || !info->dlpi_addr) return 0;
    const char *p = n;
    while (*p) p++;
    /* suffix match ".../appFw.so" */
    if (p - n >= 9) {
        const char *q = p - 9;
        if (q[0]=='a'&&q[1]=='p'&&q[2]=='p'&&q[3]=='F'&&q[4]=='w'&&q[5]=='.'&&q[6]=='s'&&q[7]=='o'&&q[8]=='\0') {
            *(uint64_t *)data = info->dlpi_addr;
            return 1;
        }
    }
    return 0;
}

static inline uint64_t fx6_appfw_base_auto(void)
{
    uint64_t base = 0;
    dl_iterate_phdr(fx6_appfw_base_cb, &base);
    if (base) return base;
    /* fallback: appFw is already loaded; resolve its own entry symbol. */
    void *h = dlopen("/usr/lib/appFw.so", 4 /* RTLD_NOLOAD */);
    if (!h) h = dlopen("/usr/lib/appFw.so", 1);
    if (!h) return 0;
    void *sym = dlsym(h, "Application_System_Init");
    if (!sym) return 0;
    fx6_dl_info di;
    for (unsigned i = 0; i < sizeof(di); i++) ((char *)&di)[i] = 0;
    if (!dladdr(sym, &di) || !di.dli_fbase) return 0;
    return (uint64_t)(uintptr_t)di.dli_fbase;
}

static inline void fx6_install_model_spoof_auto(void)
{
    fx6_install_model_spoof(fx6_appfw_base_auto());
}

static inline void fx6_model_ready_auto(void)
{
    fx6_model_ready(fx6_appfw_base_auto());
}

/* Install BL fx6_model_spoof at appFw+0x2127750. */
static inline void fx6_install_model_spoof(uint64_t appfw)
{
    if (!appfw) return;
    uint64_t pc = appfw + 0x2127750ULL;
    int64_t imm = ((int64_t)(uintptr_t)&fx6_model_spoof - (int64_t)pc) >> 2;
    if (imm < -(1 << 25) || imm >= (1 << 25)) {
        dprintf(2, "FX6_MODEL_SPOOF range fail\n");
        return;
    }
    uint64_t page = pc & ~0xfffULL;
    mprotect((void *)page, 0x1000, 7);
    uint32_t old = *(uint32_t *)pc;
    *(uint32_t *)pc = 0x94000000U | ((uint32_t)imm & 0x03ffffffU);
    __builtin___clear_cache((char *)pc, (char *)pc + 4);
    dprintf(2, "FX6_MODEL_SPOOF pc=%llx old=%x new=%x\n",
            (unsigned long long)pc, old, *(uint32_t *)pc);
}

/* appFw+0x14d4654 returns appFw+0x4dc56c8 (model status object).
 * df91e8 reads +0x4 and +0x10; ready condition is:
 *   (status == 0 || status == 3) && valid == 1
 */
static inline void *fx6_model_status(uint64_t appfw)
{
    return (void *)(uintptr_t)(appfw + 0x4dc56c8ULL);
}

static inline void fx6_model_ready(uint64_t appfw)
{
    if (!appfw) return;
    volatile uint32_t *m = (volatile uint32_t *)(uintptr_t)(appfw + 0x4dc56c8ULL);
    m[1] = 0;   /* +0x04: ready/status 0 or 3 */
    m[4] = 1;   /* +0x10: valid/ready */
}

/* -------------------------------------------------------------- engine gate */
/* GraphicsEngine::sys_getInstance() = libuxengine+0x8265c
 * engine+0x318 = before-render callback (non-null)
 * engine+0x328 = enable before-render callback
 * ScenegraphWindow at engine+0xb0:
 *   +0x234 = 8-byte dirty rect {s16 x,y,w,h}
 *   +0x23c = 2D drawing enabled byte
 *   +0x23d = clear color
 */
static inline void fx6_set_window_dirty(void *window,
                                        int16_t x, int16_t y,
                                        uint16_t w, uint16_t h)
{
    if (!window) return;
    volatile uint16_t *r = (volatile uint16_t *)((char *)window + 0x234);
    r[0] = (uint16_t)x; r[1] = (uint16_t)y;
    r[2] = w;           r[3] = h;
}


static inline void *fx6_engine_gate(uint64_t uxengine);

/* Resolve libuxengine base from its own sys_getInstance symbol. */
static inline uint64_t fx6_uxengine_base(void)
{
    /* Do NOT dlopen here: at preload time libra may not be ready yet. */
    void *sym = dlsym((void *)-1, "_ZN2ux6gfxeng14GraphicsEngine15sys_getInstanceEv");
    if (!sym) return 0;
    fx6_dl_info di;
    for (unsigned i = 0; i < sizeof(di); i++) ((char *)&di)[i] = 0;
    if (!dladdr(sym, &di) || !di.dli_fbase) return 0;
    return (uint64_t)(uintptr_t)di.dli_fbase;
}

static inline void *fx6_engine_gate_auto(void)
{
    return fx6_engine_gate(fx6_uxengine_base());
}

static inline void *fx6_engine_gate(uint64_t uxengine)
{
    if (!uxengine) return 0;
    void *(*get)(void) = (void *(*)(void))(uintptr_t)(uxengine + 0x8265cULL);
    void *ge = get ? get() : 0;
    if (!ge) return 0;

    /* no-op before-render callback: libuxengine+0xa3240 (single ret) */
    *(volatile uint64_t *)((char *)ge + 0x318) = uxengine + 0xa3240ULL;
    *(volatile uint8_t  *)((char *)ge + 0x328) = 1;

    /* full-screen dirty rect expected by ScenegraphWindow::setDirtyRect */
    void *win = (char *)ge + 0xb0;
    fx6_set_window_dirty(win, 0, 0, 1024, 540);
    *(volatile uint8_t *)((char *)win + 0x23c) = 1;

    dprintf(2, "FX6_GATE ge=%p cb=%llx dirty=0,0,1024,540 flag=1\n",
            ge, (unsigned long long)(uxengine + 0xa3240ULL));
    return ge;
}

/* optional explicit call instead of direct +0x23c write:
 * libuxengine+0x7b618: ScenegraphWindow::stopClearScreen(bool)
 */
static inline void fx6_stop_clear(uint64_t uxengine, void *window, int enable)
{
    if (!uxengine || !window) return;
    void (*fn)(void *, int) =
        (void (*)(void *, int))(uintptr_t)(uxengine + 0x7b618ULL);
    fn(window, enable);
}


/* 522 link fix: 520/517 call this symbol but model_spoof2.c does not define it.
 * Weak so a strong model_spoof.c definition still wins.
 */
#ifndef FX6_STATIC_ASSIST_NO_INJECT
extern void fx6_model_done(void) __attribute__((weak));

__attribute__((weak)) void fx6_inject_set_presenter_done(void)
{
    if (fx6_model_done) fx6_model_done();
    fx6_install_model_spoof_auto();
    fx6_model_ready_auto();
    fx6_engine_gate_auto();
}

#endif /* FX6_STATIC_ASSIST_NO_INJECT */

#endif /* FX6_STATIC_ASSIST_H */
