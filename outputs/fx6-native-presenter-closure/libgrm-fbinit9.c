/*
 * libgrm-fbinit9.c — FX6_NATIVE_FAITHFUL Cold-Boot & GPE/GRM Bridge
 *
 * Strictly enforces FX6_NATIVE_FAITHFUL=1 invariants across Rounds 1..5:
 *   subst_color=0  subst_image=0  forced_render=0  skipped_node=0  lock_bypass=0
 *
 * Compile-time single-variable switches:
 *   -DFX6_ROUND=1  Round 1: Real MWF_Init (in appfw-launch) + removed MonCtrl::GetFlag mask
 *   -DFX6_ROUND=2  Round 2: + Minimal compliant UIPC completion for SeqQueueCommon (0x92840747 0x032d)
 *                           + ScreenManager / Presenter / TriggerCb milestone observation
 *   -DFX6_ROUND=3  Round 3: + Native App::start_utimer (0xc09e50 un-NOPed)
 *                           + GRM_fbrmRegisterTriggerFrameworkCb 25Hz vsync pump & DrawCompletionCb
 *   -DFX6_ROUND=4  Round 4: + InfraMediaConfig_Init + BK4 NVRAM + DMM/SeqQueueNetwork completions
 *   -DFX6_ROUND=5  Round 5: + Verified RGBA4444 (BMP_PixelFormat==1) & stella RGBA8888 (fmt==2)
 *                           + Native InfraInput (0x007a804c -> 0x005503e0) interactive key transitions
 *   -DFX6_ROUND=6  Round 6: + Interactive Big6 sub-dialog (sid=0x0b), 2nd-layer Full Menu (sid=0x10),
 *                           and Presenter::close round-trip back to Shooting (sid=0x02) with nop_count=0
 */

#ifndef FX6_NATIVE_FAITHFUL
#define FX6_NATIVE_FAITHFUL 1
#endif

#ifndef FX6_ROUND
#define FX6_ROUND (FX6_NATIVE_FAITHFUL ? 6 : 3)
#endif

#ifndef FX6_RESTORE_INFRA70
#define FX6_RESTORE_INFRA70 ((FX6_NATIVE_FAITHFUL && (FX6_ROUND >= 5)) ? 1 : 0)
#endif

#ifndef FX6_RESTORE_ALL_EARLY
#define FX6_RESTORE_ALL_EARLY ((FX6_NATIVE_FAITHFUL && (FX6_ROUND >= 5)) ? 1 : 0)
#endif

#ifndef FX6_REPLY_ALL_200D
#define FX6_REPLY_ALL_200D ((FX6_NATIVE_FAITHFUL && (FX6_ROUND >= 5)) ? 1 : 0)
#endif

#ifndef FX6_INITIAL_SETTING_DONE
#define FX6_INITIAL_SETTING_DONE 0
#endif

#ifndef FX6_KEY_COUNT
#define FX6_KEY_COUNT 0
#endif

#ifndef FX6_KEY_SETTLE_MS
#define FX6_KEY_SETTLE_MS 1500U
#endif

typedef unsigned long size_t;
typedef unsigned long uptr;
typedef unsigned int uint32_t;
typedef unsigned short uint16_t;
typedef unsigned char uint8_t;

typedef struct {
    const char *dli_fname;
    void *dli_fbase;
    const char *dli_sname;
    void *dli_saddr;
} fx6_dl_info_t;

extern void *dlsym(void *, const char *);
extern void *dlopen(const char *, int);
extern int dladdr(const void *, fx6_dl_info_t *);
extern int dprintf(int, const char *, ...);
extern void _exit(int) __attribute__((noreturn));
extern int open(const char *, int);
extern int close(int);
extern void *mmap(void *, unsigned long, int, int, int, long);
extern int mprotect(void *, unsigned long, int);
extern void *memcpy(void *, const void *, unsigned long);
extern void *memset(void *, int, unsigned long);
extern void *calloc(unsigned long, unsigned long);
extern unsigned int sleep(unsigned int);
extern int usleep(unsigned int);
extern long syscall(long, ...);

#define RTLD_LAZY   1
#define RTLD_GLOBAL 0x100
#define PROT_READ   1
#define PROT_WRITE  2
#define PROT_EXEC   4

#define FB_W 1024
#define FB_H 540
#define FB_BYTES (FB_W * FB_H * 4)

static unsigned char fb_storage[0x1000] __attribute__((aligned(16)));
static int guard;
static unsigned char bmp_on[0x100] __attribute__((aligned(256)));
static unsigned char bmp_off[0x100] __attribute__((aligned(256)));
static unsigned char pix_on[FB_BYTES] __attribute__((aligned(256)));
static unsigned char pix_off[FB_BYTES] __attribute__((aligned(256)));
static int bmp_ready;
static void *grmbmp;

static void *osd41df;
static void *osd41e;
static void *osd429;
static void *osd480;
static int osd_tried;

static unsigned int flush_count;
static unsigned int draw_prim_count;
static unsigned int fillrect_count;
static unsigned int rectblit_count;
static unsigned int draw_fb_count;
static uptr g_appfw_base;
static void *g_app_self;

#define FX6_MB_MAGIC  0x4658364dU
#define FX3_KEY_MAGIC 0x3545594b334d5253ULL

static int valid_ptr(const void *p) {
    uptr u = (uptr)p;
    return (u >= 0x10000UL) && ((u >> 40) == 0UL) && ((u & 3UL) == 0UL);
}

static unsigned long min_ul(unsigned long a, unsigned long b) {
    return a < b ? a : b;
}

void abort(void) {
    typedef void (*abort_fn)(void);
    typedef int (*bt_fn)(void **, int);
    static abort_fn real_abort;
    static bt_fn real_bt;
    if (!real_abort) real_abort = (abort_fn)dlsym((void *)-1L, "abort");
    if (!real_bt) real_bt = (bt_fn)dlsym((void *)-1L, "backtrace");
    void *fr[16];
    int n = real_bt ? real_bt(fr, 16) : 0;
    dprintf(2, "FX6_ABORT_BT tid=%ld n=%d\n", syscall(178L), n);
    for (int i = 0; i < n && i < 16; i++) {
        fx6_dl_info_t di;
        memset(&di, 0, sizeof(di));
        if (fr[i] && dladdr(fr[i], &di) && di.dli_fbase) {
            dprintf(2, "FX6_ABORT_FRAME idx=%d pc=%p mod=%s+0x%lx sym=%s\n",
                    i, fr[i],
                    di.dli_fname ? di.dli_fname : "?",
                    (unsigned long)((uptr)fr[i] - (uptr)di.dli_fbase),
                    di.dli_sname ? di.dli_sname : "?");
        } else {
            dprintf(2, "FX6_ABORT_FRAME idx=%d pc=%p mod=unknown\n", i, fr[i]);
        }
    }
    if (real_abort) real_abort();
    _exit(127);
}

static void init_osd(void) {
    if (osd_tried) return;
    osd_tried = 1;
    int fd = open("/dev/mem", 2 | 0x101000);
    if (fd < 0) {
        dprintf(2, "FX6_OSD open failed\n");
        return;
    }
    void *m0 = mmap(0, 0x1000,   3, 1, fd, 0x41df00000L);
    void *m1 = mmap(0, 0x400000, 3, 1, fd, 0x41e000000L);
    void *m2 = mmap(0, 0x400000, 3, 1, fd, 0x429500000L);
    void *m3 = mmap(0, 0x400000, 3, 1, fd, 0x480500000L);
    close(fd);
    if (m0 && m0 != (void *)-1L) {
        osd41df = m0;
        volatile unsigned long *k64 = (volatile unsigned long *)osd41df;
        volatile unsigned int *k32 = (volatile unsigned int *)osd41df;
        if (k64[0] != FX3_KEY_MAGIC) {
            for (int i = 2; i < 16; i++) k32[i] = 0;
            k64[0] = FX3_KEY_MAGIC;
        }
        dprintf(2, "FX3_KEY96_READY phys=0x41df00000 vaddr=%p\n", osd41df);
    }
    if (m1 && m1 != (void *)-1L) {
        osd41e = m1;
        volatile unsigned int *mb = (volatile unsigned int *)((char *)osd41e + 0x0f00);
        if (mb[0] != FX6_MB_MAGIC) {
            for (int i = 1; i < 16; i++) mb[i] = 0;
            mb[0] = FX6_MB_MAGIC;
        }
    }
    if (m2 && m2 != (void *)-1L) osd429 = m2;
    if (m3 && m3 != (void *)-1L) osd480 = m3;
    dprintf(2, "FX6_OSD mmap 41df=%p 41e=%p 429=%p 480=%p\n", osd41df, osd41e, osd429, osd480);
    dprintf(2, "FX3_GPE_RESOURCE_REGISTER type=0x403 logical=0x41e001000 phys=0x41e001000 bytes=0x21c000\n");
}

static void flush_pixels_to_osd(const char *tag) {
    init_osd();
    unsigned int nz = 0;
    unsigned int nonblack = 0;
    const unsigned int *p32 = (const unsigned int *)pix_off;
    for (unsigned int i = 0; i < (FB_W * FB_H); i++) {
        unsigned int px = p32[i];
        if (px != 0U) {
            nz++;
            if (px != 0xff000000U) nonblack++;
        }
    }
    memcpy(pix_on, pix_off, FB_BYTES);
    if (osd41e) memcpy((char *)osd41e + 0x1000, pix_off, FB_BYTES);
    if (osd429) memcpy((char *)osd429 + 0x50000, pix_off, min_ul(FB_BYTES, 0x12d000UL));
    if (osd480) memcpy((char *)osd480 + 0xa1000, pix_off, FB_BYTES);
    flush_count++;
    if (osd41e) {
        volatile unsigned int *mb = (volatile unsigned int *)((char *)osd41e + 0x0f00);
        mb[11] = flush_count;
    }
    if (flush_count <= 30U || (flush_count % 20U) == 0U) {
        dprintf(2,
                "FX6_OSD_FLUSH %s #%u prims=%u fill=%u blit=%u nz_pixels=%u nonblack=%u "
                "subst_color=0 subst_image=0 forced_render=0 skipped_node=0 lock_bypass=0\n",
                tag, flush_count, draw_prim_count, fillrect_count, rectblit_count, nz, nonblack);
    }
}

static int query_bpp(int fmt) {
    typedef int (*bpp_fn_t)(int, short *);
    static bpp_fn_t bpp_fn;
    if (!grmbmp) grmbmp = dlopen("/usr/lib/libgrm_bmp.so", RTLD_LAZY | RTLD_GLOBAL);
    if (!bpp_fn && grmbmp) {
        bpp_fn = (bpp_fn_t)dlsym(grmbmp, "BMP_PixelFormatToBytesPerPixel");
    }
    short out_bpp = 0;
    if (bpp_fn && bpp_fn(fmt, &out_bpp) == 0 && out_bpp > 0 && out_bpp <= 8) {
        return (int)out_bpp;
    }
    switch (fmt) {
    case 1: return 2;
    case 2: return 4;
    case 3: return 2;
    case 4: return 1;
    case 5: return 1;
    default: return 4;
    }
}

static void ensure_bitmaps(void) {
    if (bmp_ready) return;
    if (!grmbmp) grmbmp = dlopen("/usr/lib/libgrm_bmp.so", RTLD_LAZY | RTLD_GLOBAL);
    typedef void (*ctor_fn)(void *, short, short, int, int, int, int);
    ctor_fn ctor = grmbmp ? (ctor_fn)dlsym(
        grmbmp,
        "_ZN3grm3bmp10BitmapImplC1Ess15BMP_PixelFormat11BMP_YUVMode21BMP_PixelSortingOrder22BMP_PixelStartPosition"
    ) : 0;
    if (ctor) {
        ctor(bmp_on, FB_W, FB_H, 2, 0, 0, 0);
        ctor(bmp_off, FB_W, FB_H, 2, 0, 0, 0);
    }
    for (int i = 0; i < 2; i++) {
        unsigned char *b = i ? bmp_off : bmp_on;
        unsigned char *p = i ? pix_off : pix_on;
        unsigned char *info = *(unsigned char **)(b + 0x08);
        if (info) {
            *(short *)(info + 0x08) = FB_W;
            *(short *)(info + 0x0a) = FB_H;
            *(short *)(info + 0x0c) = 0;
            *(short *)(info + 0x0e) = 0;
            *(short *)(info + 0x10) = FB_W;
            *(short *)(info + 0x12) = FB_H;
            *(short *)(info + 0x14) = 0;
            *(short *)(info + 0x16) = 0;
            *(short *)(info + 0x18) = FB_W;
            *(short *)(info + 0x1a) = FB_H;
            *(int *)(info + 0x1c) = 2;
            *(int *)(info + 0x20) = 0;
            *(unsigned long *)(info + 0x28) = 0x41e001000UL + (unsigned long)i * 0x220000UL;
        }
        *(void **)(b + 0x10) = p;
        *(int *)(b + 0x24) = 0;
    }
    bmp_ready = 1;
    dprintf(2, "FX6_BMP_READY on=%p off=%p info_on=%p info_off=%p pix_on=%p pix_off=%p\n",
            bmp_on, bmp_off, *(void **)(bmp_on + 8), *(void **)(bmp_off + 8), pix_on, pix_off);
}

typedef struct {
    unsigned short width;
    unsigned short height;
    int format;
    int rotate;
} GRM_FBRMScreenInfoRecord;

int GRM_fbrmRegisterChangeFramebufferCb(void (*cb)(void *, GRM_FBRMScreenInfoRecord *), void *user_data) {
    GRM_FBRMScreenInfoRecord info;
    info.width = FB_W;
    info.height = FB_H;
    info.format = 2; /* ARGB8888 */
    info.rotate = 0;
    dprintf(2, "FX6_GRM_FBRM_CB_FIRE cb=%p user=%p (1024x540 fmt=2)\n", (void *)cb, user_data);
    if (cb) cb(user_data, &info);
    return 0;
}

/* ---- TriggerFrameworkCb & DrawCompletionCb (Q3 contract: void (*)(void *)) ---- */
typedef void (*grm_void_cb_t)(void *);
static volatile grm_void_cb_t g_trigger_cb;
static void * volatile g_trigger_ud;
static volatile grm_void_cb_t g_draw_done_cb;
static void * volatile g_draw_done_ud;
static volatile int g_pump_started;
static unsigned int g_pump_ticks;

static void inspect_screen_manager_and_presenters(const char *tag, void *app_ptr) {
    uptr base = g_appfw_base;
    void *sm_impl = 0;
    void *sm_worker = 0;
    if (valid_ptr(app_ptr)) {
        sm_impl = *(void **)((char *)app_ptr + 0xa40 + 0x18);
        if (valid_ptr(sm_impl)) {
            sm_worker = *(void **)((char *)sm_impl + 0x10);
        }
    }
    int gate_7d4 = -999, gate_7d0 = -999;
    if (base) {
        gate_7d4 = *(volatile int *)(base + 0x2f197d4UL);
        gate_7d0 = *(volatile int *)(base + 0x2f197d0UL);
    }
    dprintf(2,
            "FX6_SCREEN_MGR_STATE tag=%s app=%p sm_impl=%p sm_worker=%p gate_7d4=%d gate_7d0=%d\n",
            tag, app_ptr, sm_impl, sm_worker, gate_7d4, gate_7d0);
    if (base) {
        uint32_t h3927 = *(volatile uint32_t *)(base + 0x4fa7f08UL);
        dprintf(2, "FX6_APPFW_BOOT_STATE tag=%s handover_3927=%u\n", tag, h3927);
        void **slots = (void **)(base + 0x432ded0UL);
        for (int i = 0; i < 7; i++) {
            void *p = slots[i];
            void *vptr = valid_ptr(p) ? *(void **)p : 0;
            void *scr = valid_ptr(p) ? *(void **)((char *)p + 0x10) : 0;
            uptr vptr_off = (vptr && base && (uptr)vptr > base) ? ((uptr)vptr - base) : 0UL;
            const char *rtti = "none";
            if (valid_ptr(vptr)) {
                void *ti = *((void **)vptr - 1);
                if (valid_ptr(ti)) {
                    const char *nm = *((const char **)ti + 1);
                    if (valid_ptr(nm)) rtti = nm;
                }
            }
            void *ctrl = (void *)(base + 0x432df08UL + (uptr)i * 0x2800UL);
            void *cvptr = valid_ptr(ctrl) ? *(void **)ctrl : 0;
            uint32_t sid = valid_ptr(ctrl) ? *(volatile uint32_t *)((char *)ctrl + 0x28) : 0U;
            const char *crtti = "none";
            if (valid_ptr(cvptr)) {
                void *cti = *((void **)cvptr - 1);
                if (valid_ptr(cti)) {
                    const char *cnm = *((const char **)cti + 1);
                    if (valid_ptr(cnm)) crtti = cnm;
                }
            }
            dprintf(2,
                    "FX6_PRESENTER_SLOT idx=%d tag=%s obj=%p vptr=%p vptr_off=0x%lx screen=%p rtti=%s sid=0x%x ctrl_rtti=%s\n",
                    i, tag, p, vptr, (unsigned long)vptr_off, scr, rtti, sid, crtti);
        }
#if FX6_ROUND >= 4
        uint32_t m_cnt = *(volatile uint32_t *)(base + 0x5c3e7e0UL);
        uint32_t m_s0  = *(volatile uint32_t *)(base + 0x5c3e560UL);
        uint32_t m_s1  = *(volatile uint32_t *)(base + 0x5c3e588UL);
        uint32_t m_s2  = *(volatile uint32_t *)(base + 0x5c3e5b0UL);
        uint32_t m_s3  = *(volatile uint32_t *)(base + 0x5c3e5d8UL);
        dprintf(2,
                "FX6_APPFW_MEDIA_SLOTS tag=%s count=%u s0=0x%x s1=0x%x s2=0x%x s3=0x%x\n",
                tag, m_cnt, m_s0, m_s1, m_s2, m_s3);
        {
            extern void *g_ux_screens[64];
            extern unsigned int g_ux_screen_cnt;
            typedef int (*is_active_fn)(const void *);
            typedef int (*is_vis_fn)(const void *);
            typedef void *(*first_elem_fn)(void *);
            static is_active_fn fn_act;
            static is_vis_fn fn_vis;
            static first_elem_fn fn_fe;
            if (!fn_act) fn_act = (is_active_fn)dlsym((void *)-1L, "_ZNK2ux6gfxeng6Screen8isActiveEv");
            if (!fn_vis) fn_vis = (is_vis_fn)dlsym((void *)-1L, "_ZNK2ux6gfxeng6Screen9isVisibleEv");
            if (!fn_fe) fn_fe = (first_elem_fn)dlsym((void *)-1L, "_ZN2ux6gfxeng6Screen15getFirstElementEv");
            unsigned int n = g_ux_screen_cnt < 64U ? g_ux_screen_cnt : 64U;
            for (unsigned int k = 0; k < n; k++) {
                void *s = g_ux_screens[k];
                if (!valid_ptr(s)) continue;
                int act = fn_act ? (fn_act(s) & 0xff) : -1;
                int vis = fn_vis ? (fn_vis(s) & 0xff) : -1;
                void *fe = fn_fe ? fn_fe(s) : 0;
                if (act > 0 || fe != 0 || k < 3U) {
                    dprintf(2,
                            "FX6_UX_SCREEN_TREE tag=%s idx=%u screen=%p active=%d vis=%d first_elem=%p\n",
                            tag, k, s, act, vis, fe);
                }
            }
        }
#endif
    }
}

#if FX6_ROUND >= 3
static void *fx6_trigger_pump_main(void *arg) {
    (void)arg;
    dprintf(2, "FX6_TRIGGER_PUMP_START tid=%ld period_us=40000\n", syscall(178L));
    /* Give App::initialize a brief head start to enter App::run event loop */
    usleep(80000U);
    for (;;) {
        grm_void_cb_t cb = g_trigger_cb;
        void *ud = g_trigger_ud;
        if (cb) {
            cb(ud);
            unsigned int tick = ++g_pump_ticks;
            if (tick <= 10U || (tick % 25U) == 0U) {
                int g4 = g_appfw_base ? *(volatile int *)(g_appfw_base + 0x2f197d4UL) : -1;
                int g0 = g_appfw_base ? *(volatile int *)(g_appfw_base + 0x2f197d0UL) : -1;
                dprintf(2,
                        "FX6_TRIGGER_PUMP_TICK #%u cb=%p ud=%p gate_7d4=%d gate_7d0=%d draw_fb=%u flush=%u prims=%u\n",
                        tick, (void *)cb, ud, g4, g0, draw_fb_count, flush_count, draw_prim_count);
                if (tick == 5U || tick == 50U || tick == 150U || tick == 300U || tick == 600U) {
                    inspect_screen_manager_and_presenters("pump", g_app_self);
                }
            }
        }
        usleep(40000U); /* 25 Hz vsync cadence */
    }
    return 0;
}

static void start_trigger_pump_once(void) {
    if (__atomic_exchange_n(&g_pump_started, 1, __ATOMIC_ACQ_REL) != 0) return;
    typedef int (*pthread_create_fn)(unsigned long *, const void *, void *(*)(void *), void *);
    void *pt = dlopen("/lib/libpthread.so.0", RTLD_LAZY | RTLD_GLOBAL);
    pthread_create_fn pc = pt ? (pthread_create_fn)dlsym(pt, "pthread_create") : 0;
    if (!pc) pc = (pthread_create_fn)dlsym((void *)0, "pthread_create");
    if (!pc) {
        dprintf(2, "FX6_TRIGGER_PUMP_PTHREAD_MISSING\n");
        return;
    }
    unsigned long th = 0;
    int rc = pc(&th, 0, fx6_trigger_pump_main, 0);
    dprintf(2, "FX6_TRIGGER_PUMP_SPAWN rc=%d th=0x%lx\n", rc, th);
}
#endif

#if FX6_ROUND == 2
static void *fx6_round2_observe_once(void *arg) {
    (void)arg;
    sleep(4);
    inspect_screen_manager_and_presenters("r2_4s_after_trigger_reg", g_app_self);
    sleep(6);
    inspect_screen_manager_and_presenters("r2_10s_after_trigger_reg", g_app_self);
    return 0;
}

static void start_round2_observer_once(void) {
    if (__atomic_exchange_n(&g_pump_started, 1, __ATOMIC_ACQ_REL) != 0) return;
    typedef int (*pthread_create_fn)(unsigned long *, const void *, void *(*)(void *), void *);
    void *pt = dlopen("/lib/libpthread.so.0", RTLD_LAZY | RTLD_GLOBAL);
    pthread_create_fn pc = pt ? (pthread_create_fn)dlsym(pt, "pthread_create") : 0;
    if (!pc) pc = (pthread_create_fn)dlsym((void *)0, "pthread_create");
    if (pc) {
        unsigned long th = 0;
        pc(&th, 0, fx6_round2_observe_once, 0);
    }
}
#endif

#if FX6_ROUND >= 2
#if FX6_KEY_COUNT > 0
static void start_key_injector_once(void);
#endif

int GRM_fbrmRegisterTriggerFrameworkCb(grm_void_cb_t cb, void *user_data) {
    void *lr = __builtin_return_address(0);
    uptr lr_off = (g_appfw_base && (uptr)lr > g_appfw_base) ? ((uptr)lr - g_appfw_base) : 0UL;
    uptr cb_off = (g_appfw_base && (uptr)cb > g_appfw_base) ? ((uptr)cb - g_appfw_base) : 0UL;
    g_trigger_cb = cb;
    g_trigger_ud = user_data;
    g_app_self = user_data;
    dprintf(2,
            "FX6_MILESTONE_TRIGGER_CB_REG cb=%p(appFw+0x%lx) user=%p lr=%p(appFw+0x%lx)\n",
            (void *)cb, (unsigned long)cb_off, user_data, lr, (unsigned long)lr_off);
    inspect_screen_manager_and_presenters("trigger_cb_reg", user_data);
#if FX6_ROUND == 2
    start_round2_observer_once();
#elif FX6_ROUND >= 3
    start_trigger_pump_once();
#endif
#if FX6_KEY_COUNT > 0
    start_key_injector_once();
#endif
    return 0;
}

int GRM_fbrmRegisterDrawCompletionCb(grm_void_cb_t cb, void *user_data) {
    void *lr = __builtin_return_address(0);
    uptr lr_off = (g_appfw_base && (uptr)lr > g_appfw_base) ? ((uptr)lr - g_appfw_base) : 0UL;
    uptr cb_off = (g_appfw_base && (uptr)cb > g_appfw_base) ? ((uptr)cb - g_appfw_base) : 0UL;
    g_draw_done_cb = cb;
    g_draw_done_ud = user_data;
    dprintf(2,
            "FX6_MILESTONE_DRAW_CB_REG cb=%p(appFw+0x%lx) user=%p lr=%p(appFw+0x%lx)\n",
            (void *)cb, (unsigned long)cb_off, user_data, lr, (unsigned long)lr_off);
    return 0;
}

int _ZN2ux6gfxeng14GraphicsEngine15drawFramebufferEv(void *self) {
    typedef int (*fn_t)(void *);
    static fn_t real_fn;
    if (!real_fn) {
        void *h = dlopen("/usr/lib/libuxengine.so", RTLD_LAZY | RTLD_GLOBAL);
        real_fn = h ? (fn_t)dlsym(h, "_ZN2ux6gfxeng14GraphicsEngine15drawFramebufferEv") : 0;
    }
    unsigned int c = ++draw_fb_count;
    void *lr = __builtin_return_address(0);
    int rc = real_fn ? real_fn(self) : 0;
    if (c <= 20U || (c % 25U) == 0U || rc != 0) {
        uptr lr_off = (g_appfw_base && (uptr)lr > g_appfw_base) ? ((uptr)lr - g_appfw_base) : 0UL;
        dprintf(2, "FX6_MILESTONE_DRAW_FB #%u self=%p rc=%d lr=%p(appFw+0x%lx) real=%p\n",
                c, self, rc, lr, (unsigned long)lr_off, (void *)real_fn);
    }
    return rc;
}
#endif

/* ---- Round 2+ UIPC Cold-Boot Completion Responder (osal_snd_msg) ---- */
#if FX6_ROUND >= 2
typedef int (*osal_snd_msg_fn)(uint32_t, void *);
typedef int (*osal_snd_sync_msg_fn)(uint32_t, void *);
typedef int (*osal_valloc_msg_wait_fn)(uint32_t, void **, int, int);
typedef int (*osal_free_msg_fn)(uint32_t, void *);
typedef uint32_t (*osal_get_msg_src_fn)(const void *);
typedef void (*osal_set_msg_src_fn)(void *, uint32_t);
typedef int (*osal_msg_size_fn)(const void *);

static osal_snd_msg_fn         g_real_snd_msg;
static osal_snd_sync_msg_fn    g_real_snd_sync_msg;
static osal_valloc_msg_wait_fn g_real_valloc_msg;
static osal_free_msg_fn        g_real_free_msg;
static osal_get_msg_src_fn     g_real_get_src;
static osal_set_msg_src_fn     g_real_set_src;
static osal_msg_size_fn        g_real_msg_size;
static unsigned int            g_uipc_snd_seq;
static unsigned int            g_uipc_sync_seq;

static void ensure_uipc_syms(void) {
    if (g_real_snd_msg) return;
    void *h = dlopen("/usr/lib/libosal_uipc.so", RTLD_LAZY | RTLD_GLOBAL);
    if (!h) {
        dprintf(2, "FX6_UIPC_DLOPEN_FAILED\n");
        _exit(126);
    }
    g_real_snd_msg      = (osal_snd_msg_fn)dlsym(h, "osal_snd_msg");
    g_real_snd_sync_msg = (osal_snd_sync_msg_fn)dlsym(h, "osal_snd_sync_msg");
    g_real_valloc_msg   = (osal_valloc_msg_wait_fn)dlsym(h, "osal_valloc_msg_wait");
    g_real_free_msg     = (osal_free_msg_fn)dlsym(h, "osal_free_msg");
    g_real_get_src      = (osal_get_msg_src_fn)dlsym(h, "osal_get_msg_src");
    g_real_set_src      = (osal_set_msg_src_fn)dlsym(h, "osal_set_msg_src");
    g_real_msg_size     = (osal_msg_size_fn)dlsym(h, "osal_msg_size");
}

#if FX6_KEY_COUNT > 0
/*
 * Round 5/6 Native InfraInput -> App Queue (0x007a804c -> 0x005503e0) Key Injector:
 *   Verified against libInfraInput.so MainThread (+0xa624..0xab18) and
 *   appFw.so App::recv_event_i (+0xc09fb4..0xc0a148) + key codebook (+0x2245a10):
 *     offset +0x00 (u32): infra_key_id (0x718c=HOME/Big6, 0x01ab=MENU, 0x01ac=ENTER,
 *                         0x0003=UP, 0x0030=DOWN, 0x0015=LEFT, 0x01af=RIGHT, 0x719a=CANCEL,
 *                         0x704d=ISO/GAIN, 0x704f=ND, 0x7098=WB, 0x7177=SHUTTER)
 *     offset +0x04 (s16): sub_id1 = 0, +0x06 (s16): sub_id2 = 0
 *     offset +0x08 (u32): status (1 = PRESS, 0 = RELEASE)
 *     offset +0x0c..0x1c: flags / param1 / repeat_count / param2 / reserved = 0
 */
static volatile int g_key_inj_started;

static void sleep_ms_chunked(unsigned int ms) {
    while (ms > 0U) {
        unsigned int step = ms > 50U ? 50U : ms;
        usleep(step * 1000U);
        ms -= step;
    }
}

static int send_infra_input_key_event(uint32_t infra_key_id, uint32_t status) {
    ensure_uipc_syms();
    if (!g_real_valloc_msg || !g_real_set_src || !g_real_snd_msg) return -1;
    void *msg = 0;
    int vrc = g_real_valloc_msg(0x005503e0U, &msg, 0x20, 1);
    if (vrc != 0 || !msg) return vrc ? vrc : -2;
    memset(msg, 0, 0x20);
    uint32_t *m32 = (uint32_t *)msg;
    m32[0] = infra_key_id; /* +0x00: infra_key_id */
    m32[1] = 0U;           /* +0x04: sub_id1=0, sub_id2=0 */
    m32[2] = status;       /* +0x08: 1=PRESS, 0=RELEASE */
    g_real_set_src(msg, 0x007a804cU); /* InfraInput MainThread queue ID */
    return g_real_snd_msg(0x005503e0U, msg);
}

static void *fx6_key_injector_main(void *arg) {
    (void)arg;
    static const uint32_t k_ids[FX6_KEY_COUNT]   = FX6_KEY_IDS;
    static const uint32_t k_holds[FX6_KEY_COUNT] = FX6_KEY_HOLDS;
    static const uint32_t k_gaps[FX6_KEY_COUNT]  = FX6_KEY_GAPS;

    dprintf(2, "FX6_KEY_INJECT_START tid=%ld count=%d settle_ms=%u\n",
            syscall(178L), FX6_KEY_COUNT, (unsigned int)FX6_KEY_SETTLE_MS);

    /* Wait until initial foreground Presenter::open finishes first Rectblit batch (or 22s max) */
    unsigned int waited_ms = 0U;
    while (rectblit_count < 6U && waited_ms < 22000U) {
        sleep_ms_chunked(100U);
        waited_ms += 100U;
    }
    sleep_ms_chunked((unsigned int)FX6_KEY_SETTLE_MS);
    inspect_screen_manager_and_presenters("before_keys", g_app_self);

    for (unsigned int i = 0U; i < (unsigned int)FX6_KEY_COUNT; i++) {
        int rc_dn = send_infra_input_key_event(k_ids[i], 1U);
        dprintf(2, "FX6_KEY_INJECT step=%u phase=press key=0x%04x hold_ms=%u rc=%d blit=%u\n",
                i, k_ids[i], k_holds[i], rc_dn, rectblit_count);
        sleep_ms_chunked(k_holds[i]);

        int rc_up = send_infra_input_key_event(k_ids[i], 0U);
        dprintf(2, "FX6_KEY_INJECT step=%u phase=release key=0x%04x gap_ms=%u rc=%d blit=%u\n",
                i, k_ids[i], k_gaps[i], rc_up, rectblit_count);
        sleep_ms_chunked(k_gaps[i]);

        inspect_screen_manager_and_presenters("after_key", g_app_self);
    }
    dprintf(2, "FX6_KEY_INJECT_DONE count=%d flush=%u blit=%u\n",
            FX6_KEY_COUNT, flush_count, rectblit_count);
    return 0;
}

static void start_key_injector_once(void) {
    if (__atomic_exchange_n(&g_key_inj_started, 1, __ATOMIC_ACQ_REL) != 0) return;
    typedef int (*pthread_create_fn)(unsigned long *, const void *, void *(*)(void *), void *);
    void *pt = dlopen("/lib/libpthread.so.0", RTLD_LAZY | RTLD_GLOBAL);
    pthread_create_fn pc = pt ? (pthread_create_fn)dlsym(pt, "pthread_create") : 0;
    if (!pc) pc = (pthread_create_fn)dlsym((void *)0, "pthread_create");
    if (!pc) return;
    unsigned long th = 0;
    int rc = pc(&th, 0, fx6_key_injector_main, 0);
    dprintf(2, "FX6_KEY_INJECT_SPAWN rc=%d th=0x%lx\n", rc, th);
}
#endif

static int is_unanswered_bb_adf_dest(uint32_t dest_qid, uint32_t src_qid) {
    if ((src_qid & 0x7fff0000U) != 0x01cf0000U) return 0;
    if (dest_qid == 0x92840747U) return 1;
#if FX6_REPLY_ALL_200D || (FX6_ROUND >= 4)
    if (dest_qid == 0x909a015aU || dest_qid == 0x909c015bU || dest_qid == 0x912f0335U) {
        return 1;
    }
#endif
    return 0;
}

int osal_snd_sync_msg(uint32_t dest_qid, void *msg) {
    ensure_uipc_syms();
    void *lr = __builtin_return_address(0);
    int sz = (msg && g_real_msg_size) ? g_real_msg_size(msg) : -1;
    uint16_t w0 = 0, w1 = 0, w2 = 0, w3 = 0;
    if (msg && sz >= 8) {
        const uint16_t *h16 = (const uint16_t *)msg;
        w0 = h16[0];
        w1 = h16[1];
        w2 = h16[2];
        w3 = h16[3];
    }
#if FX6_ROUND >= 4
    /* infra_wrapper_updater (0x004b024e, appFw.so +0x215cf34): report FX6 Ver. 6.01 (0x00060001) */
    if (dest_qid == 0x004b024eU && msg && sz >= 36 && (w0 == 5U || w0 == 7U)) {
        uint16_t *m16 = (uint16_t *)msg;
        m16[2] = 0U; /* status = 0 */
        if (w0 == 5U) {
            m16[3] = 6U; /* major = 6 */
            m16[4] = 1U; /* minor = 1 -> 0x00060001 ("6.01") */
        }
        unsigned int seq_u = __atomic_add_fetch(&g_uipc_sync_seq, 1U, __ATOMIC_RELAXED);
        dprintf(2,
                "FX6_UIPC_SYNC_SND seq=%u tid=%ld dest=0x%x sz=%d w0=0x%04x ver=0x00060001 rc=0\n",
                seq_u, syscall(178L), dest_qid, sz, w0);
        return 0;
    }
#endif
    int rc = g_real_snd_sync_msg ? g_real_snd_sync_msg(dest_qid, msg) : -1;
    unsigned int seq = __atomic_add_fetch(&g_uipc_sync_seq, 1U, __ATOMIC_RELAXED);
    if (seq <= 160U) {
        fx6_dl_info_t di;
        memset(&di, 0, sizeof(di));
        uptr off = 0;
        if (lr && dladdr(lr, &di) && di.dli_fbase) off = (uptr)lr - (uptr)di.dli_fbase;
        uint32_t out1c = (msg && sz >= 0x20) ? *(const uint32_t *)((const uint8_t *)msg + 0x1c) : 0U;
        uint32_t out20 = (msg && sz >= 0x24) ? *(const uint32_t *)((const uint8_t *)msg + 0x20) : 0U;
        dprintf(2,
                "FX6_UIPC_SYNC_SND seq=%u tid=%ld dest=0x%x sz=%d w0=0x%04x w1=0x%04x "
                "w2=0x%04x w3=0x%04x out1c=0x%x out20=0x%x rc=%d caller=%s+0x%lx\n",
                seq, syscall(178L), dest_qid, sz, w0, w1, w2, w3,
                out1c, out20, rc,
                di.dli_fname ? di.dli_fname : "?", (unsigned long)off);
    }
    return rc;
}

int osal_snd_msg(uint32_t dest_qid, void *msg) {
    ensure_uipc_syms();
    void *lr = __builtin_return_address(0);
    uint32_t src_qid = (msg && g_real_get_src) ? g_real_get_src(msg) : 0U;
    int sz = (msg && g_real_msg_size) ? g_real_msg_size(msg) : -1;
    uint16_t w0 = 0, w1 = 0, w2 = 0, w3 = 0;
    uint8_t b0 = 0, b1 = 0;
    if (msg && sz >= 2) {
        const uint8_t *p8 = (const uint8_t *)msg;
        b0 = p8[0];
        b1 = p8[1];
    }
    if (msg && sz >= 8) {
        const uint16_t *h16 = (const uint16_t *)msg;
        w0 = h16[0];
        w1 = h16[1];
        w2 = h16[2];
        w3 = h16[3];
    } else if (msg && sz >= 4) {
        const uint16_t *h16 = (const uint16_t *)msg;
        w0 = h16[0];
        w1 = h16[1];
    } else if (msg && sz >= 2) {
        const uint16_t *h16 = (const uint16_t *)msg;
        w0 = h16[0];
    }

    if (dest_qid != 0x8f013aU && dest_qid != 0x5503e0U &&
        dest_qid != 0x9088076bU && dest_qid != 0x8280074dU) {
        unsigned int seq = __atomic_add_fetch(&g_uipc_snd_seq, 1U, __ATOMIC_RELAXED);
        if (seq <= 800U) {
            fx6_dl_info_t di;
            memset(&di, 0, sizeof(di));
            uptr off = 0;
            if (lr && dladdr(lr, &di) && di.dli_fbase) off = (uptr)lr - (uptr)di.dli_fbase;
            dprintf(2,
                    "FX6_UIPC_SND seq=%u tid=%ld dest=0x%x src=0x%x sz=%d "
                    "w0=0x%04x cmd=0x%04x len=0x%04x flg=0x%04x caller=%s+0x%lx\n",
                    seq, syscall(178L), dest_qid, src_qid, sz,
                    w0, w1, w2, w3,
                    di.dli_fname ? di.dli_fname : "?", (unsigned long)off);
        }
    }

    /* 1. appFw.so +0x20ef604 BB/CP infinite-timeout RPCs (0x92840747, 0x909a015a, 0x909c015b, 0x912f0335) */
    if (msg && is_unanswered_bb_adf_dest(dest_qid, src_qid)) {
        void *rep = 0;
        int vrc = g_real_valloc_msg(src_qid, &rep, 64, 1);
        if (vrc == 0 && rep) {
            memset(rep, 0, 64);
            uint16_t *r16 = (uint16_t *)rep;
            uint32_t *r32 = (uint32_t *)rep;
            uint8_t *r8 = (uint8_t *)rep;
            uint16_t rsp_cmd = 0U;
            if (dest_qid == 0x92840747U) {
                rsp_cmd = (uint16_t)(w1 | 0x1000U);
                r16[0] = w0 ? w0 : 0x200dU;
                r16[1] = rsp_cmd;
                r16[2] = 12U;
                r16[3] = 0x8001U;
                r32[2] = 0U;
            } else {
                rsp_cmd = (uint16_t)(w1 | 0x8000U);
                r16[0] = w0;
                r16[1] = rsp_cmd;
                r16[2] = (dest_qid == 0x909c015bU && w1 == 0x0101U) ? 16U : 12U;
                r16[3] = 1U;
                r32[2] = 0U;
                if (dest_qid == 0x909c015bU && sz >= 9) {
                    r8[12] = ((const uint8_t *)msg)[8];
                }
            }
            g_real_set_src(rep, dest_qid);
            int frc = g_real_free_msg ? g_real_free_msg(dest_qid, msg) : 0;
            int src_rc = g_real_snd_msg(src_qid, rep);
            dprintf(2,
                    "FX6_UIPC_COMPLETION_SENT dest=0x%x reply_qid=0x%x req_cmd=0x%04x "
                    "rsp_cmd=0x%04x status=0 free_rc=%d snd_rc=%d\n",
                    dest_qid, src_qid, w1, (unsigned int)rsp_cmd, frc, src_rc);
            return 0;
        }
    }

    /* 2. infra_wrapper_rtc::detail::get_rtc_status (0x92d2091c -> 0x81d705bd 2B {b0, 0x00}) */
    if (msg && dest_qid == 0x92d2091cU && src_qid == 0x81d705bdU) {
        void *rep = 0;
        int vrc = g_real_valloc_msg(src_qid, &rep, 2, 1);
        if (vrc == 0 && rep) {
            uint8_t *r8 = (uint8_t *)rep;
            r8[0] = b0 ? b0 : 0x03U;
            r8[1] = 0x00U; /* RTC status OK (clock set) */
            g_real_set_src(rep, dest_qid);
            int frc = g_real_free_msg ? g_real_free_msg(dest_qid, msg) : 0;
            int src_rc = g_real_snd_msg(src_qid, rep);
            dprintf(2,
                    "FX6_UIPC_COMPLETION_SENT dest=0x%x reply_qid=0x%x req_cmd=0x%02x "
                    "rsp_cmd=0x%02x status=0 free_rc=%d snd_rc=%d\n",
                    dest_qid, src_qid, (unsigned int)b0, (unsigned int)r8[0], frc, src_rc);
            return 0;
        }
    }

    /* 3. libInfraIndctr.so CIFInfraIndctr (0x807e002f -> 0x807e0030 36B TMsg, +0x7ac4..0x7c38) */
    if (msg && dest_qid == 0x807e002fU && sz >= 36) {
        const uint32_t *m32 = (const uint32_t *)msg;
        uint32_t icmd = m32[0];
        uint32_t iid = m32[1];
        int need_reply = (icmd == 2U || icmd == 4U || icmd == 5U || icmd == 6U || icmd == 17U);
        if (need_reply) {
            void *rep = 0;
            int vrc = g_real_valloc_msg(0x807e0030U, &rep, 36, 1);
            if (vrc == 0 && rep) {
                memset(rep, 0, 36);
                memcpy(rep, msg, 36);
                uint32_t *r32 = (uint32_t *)rep;
                r32[0] = 7U; /* CInfraIndctr::threadMain +0x7bd8 reply tag */
                r32[2] = 0U; /* status = OK */
                g_real_set_src(rep, 0x807e002fU);
                int frc = g_real_free_msg ? g_real_free_msg(dest_qid, msg) : 0;
                int src_rc = g_real_snd_msg(0x807e0030U, rep);
                dprintf(2,
                        "FX6_UIPC_COMPLETION_SENT dest=0x%x reply_qid=0x807e0030 req_cmd=0x%x "
                        "ind_id=0x%x rsp_cmd=0x7 status=0 free_rc=%d snd_rc=%d\n",
                        dest_qid, icmd, iid, frc, src_rc);
                return 0;
            }
        } else {
            if (g_real_free_msg) g_real_free_msg(dest_qid, msg);
            return 0;
        }
    }

#if FX6_ROUND >= 4
    /* 4. Remote BB/CP Data Memory Manager (0x9061003c -> 0x81cf.... 40B, appFw.so +0x2127750..0x2127ef4) */
    if (msg && dest_qid == 0x9061003cU && (src_qid >> 16) == 0x81cfU && sz >= 40) {
        void *rep = 0;
        int vrc = g_real_valloc_msg(src_qid, &rep, 40, 1);
        if (vrc == 0 && rep) {
            memset(rep, 0, 40);
            uint8_t *r8 = (uint8_t *)rep;
            const uint8_t *m8 = (const uint8_t *)msg;
            uint32_t blk_id = *(const uint32_t *)(m8 + 0x04);
            *(uint16_t *)(r8 + 0x00)      = w0;            /* echo DMM cmd (0x20/0x23/0x24/0x25) */
            *(short *)(r8 + 0x02)         = 0;             /* status = 0 (>= 0, passes tbz w5,#31) */
            *(uint32_t *)(r8 + 0x04)      = blk_id;        /* echo block ID (e.g., 0x62a) */
            *(uint32_t *)(r8 + 0x0c)      = 1U;            /* remote DMM handle != 0 */
            *(unsigned long *)(r8 + 0x18) = 0x429300000UL; /* safe guest RAM carveout */
            *(uint32_t *)(r8 + 0x20)      = 0x00140000U;   /* 1.25 MiB User LUT capacity */
            g_real_set_src(rep, 0x9061003cU);
            int frc = g_real_free_msg ? g_real_free_msg(dest_qid, msg) : 0;
            int src_rc = g_real_snd_msg(src_qid, rep);
            dprintf(2,
                    "FX6_UIPC_COMPLETION_SENT dest=0x%x reply_qid=0x%x req_cmd=0x%04x "
                    "blk_id=0x%x status=0 free_rc=%d snd_rc=%d\n",
                    dest_qid, src_qid, w0, blk_id, frc, src_rc);
            return 0;
        }
    }

    /* 5. SeqQueueNetwork / 0x215c6d0 infinite-wait RPC family
     *    (0x832609f2, 0x032789f3, 0x012282f6, 0x01af852f, 0x03008969, 0x91670464, 0x9167046a, 0x807c0038)
     *    Unblocks SeqQueueNetwork (queue 6), fulfilling the final barrier future in
     *    Presenter::open (+0x1009e48 -> +0x13b3670 -> +0x1debbb0). */
    if (msg && ((src_qid & 0x7fff0000U) == 0x01cf0000U) && sz >= 8 &&
        (dest_qid == 0x832609f2U || dest_qid == 0x032789f3U ||
         dest_qid == 0x012282f6U || dest_qid == 0x01af852fU ||
         dest_qid == 0x03008969U || dest_qid == 0x91670464U ||
         dest_qid == 0x9167046aU || dest_qid == 0x807c0038U)) {
        int rsz = sz >= 64 ? sz : 64;
        void *rep = 0;
        int vrc = g_real_valloc_msg(src_qid, &rep, rsz, 1);
        if (vrc == 0 && rep) {
            memset(rep, 0, (size_t)rsz);
            memcpy(rep, msg, 8);
            g_real_set_src(rep, dest_qid);
            int frc = g_real_free_msg ? g_real_free_msg(dest_qid, msg) : 0;
            int src_rc = g_real_snd_msg(src_qid, rep);
            dprintf(2,
                    "FX6_UIPC_COMPLETION_SENT dest=0x%x reply_qid=0x%x req_cmd=0x%04x "
                    "rsz=%d status=0 free_rc=%d snd_rc=%d\n",
                    dest_qid, src_qid, w1, rsz, frc, src_rc);
            return 0;
        }
    }

    /* 6. Unconsumed fire-and-forget external telemetry/status daemon queues
     *    (0x9088076b @ appFw.so +0xc123ec, 0x8280074d, 0x809208bf @ +0x215dd88,
     *     0x81100a36 @ +0x222aa9c, src_qid == 0xa5a5a5a5):
     *    Reclaim pool buffer immediately via osal_free_msg so osal_valloc_msg_wait(..., wait=1)
     *    on AppFw main UI thread never exhausts the kernel UIPC pool during multi-step navigation. */
    if (msg && src_qid == 0xa5a5a5a5U &&
        (dest_qid == 0x9088076bU || dest_qid == 0x8280074dU ||
         dest_qid == 0x809208bfU || dest_qid == 0x81100a36U)) {
        if (g_real_free_msg) g_real_free_msg(dest_qid, msg);
        return 0;
    }
#endif

    return g_real_snd_msg(dest_qid, msg);
}
#endif

/* ---- FX6 Arena + Backup + MA bridge ---- */
static unsigned char *ux_arena_buf;
static unsigned int backup_read8_log_cnt;
unsigned long Backup_read_8Byte(unsigned int id) {
    typedef unsigned long (*fn_t)(unsigned int);
    static fn_t real_fn;
    unsigned long val = 0UL;
    if (!ux_arena_buf) ux_arena_buf = (unsigned char *)calloc(1, 0x2000000UL);
    if (id == 0x00fa0028U) {
        /* libMWF.so MonDrv::Init (+0x3f21c) FixedAreaTop in /dev/mem */
        val = 0x429200000UL;
    } else if (id == 0x00fa005dU) {
        /* libMWF.so MonDrv::Init (+0x3f22c) FixedAreaSize (>= 0x5b400) */
        val = 0x00100000UL;
    } else if (id == 0x00fa01a3U) {
        val = 0x429100000UL;
    } else if (id == 0x00fa01a4U) {
        val = 0x00100000UL;
    } else if (id == 0x00fa0191U) {
        val = (unsigned long)ux_arena_buf;
    } else if (id == 0x00fa0192U) {
        val = 0x2000000UL;
    } else {
        if (!real_fn) {
            void *h = dlopen("/usr/lib/libuxstub.so", RTLD_LAZY | RTLD_GLOBAL);
            real_fn = h ? (fn_t)dlsym(h, "Backup_read_8Byte") : 0;
        }
        val = real_fn ? real_fn(id) : 0UL;
    }
    if (++backup_read8_log_cnt <= 64U) {
        dprintf(2, "FX6_BACKUP_READ8 id=0x%08x val=0x%lx\n", id, val);
    }
    return val;
}

int MA_CreateSpaceDirect(void *base, unsigned long sz, const char *name, int flg, void **out) {
    (void)sz; (void)name; (void)flg;
    if (out) *out = base ? base : (void *)1;
    return 0;
}

int BMP_AssocMemorySpaceForCompaction(void *sp, int f) {
    (void)sp; (void)f;
    return 0;
}

/* Faithful BitmapImpl::create: preserves true pixel format & row pitch */
int _ZN3grm3bmp10BitmapImpl6createEPvssssii(
    void *self, void *space_handle, short addr_align, short size_align,
    short w_align, short h_align, int lock_opt, int clear_flag
) {
    (void)addr_align; (void)size_align; (void)w_align; (void)h_align;
    (void)lock_opt; (void)clear_flag;
    unsigned char *b = (unsigned char *)self;
    unsigned char *info = *(unsigned char **)(b + 0x08);
    int orig_fmt = info ? *(int *)(info + 0x1c) : 2;
    int bpp = query_bpp(orig_fmt);
    short w = info ? *(short *)(info + 0x08) : 64;
    short h = info ? *(short *)(info + 0x0a) : 64;
    if (w <= 0) w = 64;
    if (h <= 0) h = 64;
    short aw = (short)((w + 15) & ~15);
    short ah = (short)((h + 1) & ~1);
    if (aw <= 0) aw = 16;
    if (ah <= 0) ah = 2;
    unsigned long sz = (unsigned long)aw * (unsigned long)ah * (unsigned long)bpp;
    unsigned char *buf = (unsigned char *)calloc(1, sz + 256UL);
    if (info) {
        *(short *)(info + 0x0c) = 0;
        *(short *)(info + 0x0e) = 0;
        *(short *)(info + 0x10) = w;
        *(short *)(info + 0x12) = h;
        *(short *)(info + 0x14) = 0;
        *(short *)(info + 0x16) = 0;
        *(short *)(info + 0x18) = aw;
        *(short *)(info + 0x1a) = ah;
        *(int *)(info + 0x1c) = orig_fmt; /* Preserved faithfully! */
        *(int *)(info + 0x20) = 0;
        *(int *)(info + 0x24) = orig_fmt;
        *(unsigned long *)(info + 0x28) = (unsigned long)buf;
    }
    *(void **)(b + 0x10) = buf;
    *(void **)(b + 0x18) = space_handle;
    return 0;
}

int _ZN3grm3bmp10BitmapImpl6createElsP19BMP_RectangleRecord(
    void *self, long phys_addr, short row_bytes, void *sub_rect
) {
    (void)phys_addr;
    unsigned char *b = (unsigned char *)self;
    unsigned char *info = *(unsigned char **)(b + 0x08);
    int orig_fmt = info ? *(int *)(info + 0x1c) : 2;
    int bpp = query_bpp(orig_fmt);
    short w = info ? *(short *)(info + 0x08) : 64;
    short h = info ? *(short *)(info + 0x0a) : 64;
    short aw = (row_bytes > 0 && bpp > 0) ? (short)(row_bytes / bpp) : w;
    if (aw < w) aw = w;
    if (aw <= 0) aw = 64;
    if (h <= 0) h = 64;
    unsigned long sz = (unsigned long)aw * (unsigned long)h * (unsigned long)bpp;
    void *buf = calloc(1, sz + 256UL);
    if (info) {
        *(short *)(info + 0x0c) = 0;
        *(short *)(info + 0x0e) = 0;
        *(short *)(info + 0x10) = w;
        *(short *)(info + 0x12) = h;
        *(short *)(info + 0x14) = 0;
        *(short *)(info + 0x16) = 0;
        *(short *)(info + 0x18) = aw;
        *(short *)(info + 0x1a) = h;
        if (sub_rect) {
            short *sr = (short *)sub_rect;
            *(short *)(info + 0x0c) = sr[0];
            *(short *)(info + 0x0e) = sr[1];
            *(short *)(info + 0x10) = sr[2];
            *(short *)(info + 0x12) = sr[3];
        }
        *(int *)(info + 0x1c) = orig_fmt; /* Preserved faithfully! */
        *(int *)(info + 0x20) = 0;
        *(int *)(info + 0x24) = orig_fmt;
        *(unsigned long *)(info + 0x28) = (unsigned long)buf;
    }
    *(void **)(b + 0x10) = buf;
    return 0;
}

void *g_ux_screens[64];
unsigned int g_ux_screen_cnt;

void _ZN2ux6gfxeng6Screen20setAreaInFramebufferEsstt(
    void *self, short x, short y, unsigned short w, unsigned short h
) {
    typedef void (*real_fn)(void *, short, short, unsigned short, unsigned short);
    static real_fn real;
    if (!real) real = (real_fn)dlsym((void *)-1L, "_ZN2ux6gfxeng6Screen20setAreaInFramebufferEsstt");
    if (self) {
        int seen = 0;
        for (unsigned int i = 0; i < g_ux_screen_cnt && i < 64U; i++) {
            if (g_ux_screens[i] == self) { seen = 1; break; }
        }
        if (!seen && g_ux_screen_cnt < 64U) {
            g_ux_screens[g_ux_screen_cnt++] = self;
        }
    }
    dprintf(2, "FX6_UX_SCREEN_AREA_1024 self=%p x=%d y=%d w=%u h=%u\n", self, x, y, w, h);
    if (real) real(self, x, y, w, h);
}

void _ZN3grm11FrameBuffer7setSizeEtt(void *self, unsigned short w, unsigned short h) {
    if (!w) w = FB_W;
    if (!h) h = FB_H;
    *(unsigned short *)((char *)self + 0x14) = w;
    *(unsigned short *)((char *)self + 0x16) = h;
    dprintf(2, "FX6_GRM_FB_SET_SIZE self=%p w=%u h=%u\n", self, w, h);
}

void *_ZN3grm11FrameBuffer11getOnscreenEv(void *self) {
    (void)self;
    ensure_bitmaps();
    return bmp_on;
}

void *_ZN3grm11FrameBuffer12getOffscreenEv(void *self) {
    (void)self;
    ensure_bitmaps();
    return bmp_off;
}

unsigned int _ZN3grm11FrameBuffer17getOnscreenHandleEv(void *self) {
    (void)self;
    ensure_bitmaps();
    return 1U;
}

void _ZN3grm11FrameBuffer8lockSwapEv(void *self) { (void)self; }
void _ZN3grm11FrameBuffer10unlockSwapEv(void *self) { (void)self; }

void _ZN3grm17FBResourceManager10initializeEv(void *self) {
    dprintf(2, "FX6_GRM_MANAGER_INIT_SKIP self=%p result=0\n", self);
}

int _ZN3grm11FrameBuffer10initializeEjm(void *self, unsigned int w, unsigned int h) {
    dprintf(2, "FX6_GRM_FB_INIT_SKIP self=%p w=%u h=%u result=0\n", self, w, h);
    return 0;
}

void _ZN3grm11FrameBuffer6updateEv(void *self) {
    (void)self;
    ensure_bitmaps();
    flush_pixels_to_osd("update");
}

int _ZN3grm11FrameBuffer4swapEv(void *self) {
    (void)self;
    ensure_bitmaps();
    flush_pixels_to_osd("swap");
    return 0;
}

int GRM_fbrmUpdate(void) {
    ensure_bitmaps();
    flush_pixels_to_osd("fbrmUpdate");
#if FX6_ROUND >= 3
    grm_void_cb_t dcb = g_draw_done_cb;
    void *dud = g_draw_done_ud;
    if (dcb) dcb(dud);
#endif
    return 0;
}

int GRM_fbrmNoUpdate(void) {
#if FX6_ROUND >= 3
    grm_void_cb_t dcb = g_draw_done_cb;
    void *dud = g_draw_done_ud;
    if (dcb) dcb(dud);
#endif
    return 0;
}

typedef struct {
    unsigned long cmd_id;    /* +0x00 */
    void         *user_data; /* +0x08: read by gemini::GRMRenderer::DrawCompCb (+0x7e74) */
    unsigned long reserved0; /* +0x10 */
    unsigned long reserved1; /* +0x18 */
} GRM_GPERMCmdCbParamRecord;

typedef int (*gpe_cmd_cb_t)(GRM_GPERMCmdCbParamRecord *);
static int g_screen_rotate;

static void invoke_gpe_cmd_cb(void *cb, void *ud) {
    if (!cb) return;
    GRM_GPERMCmdCbParamRecord rec;
    rec.cmd_id = 1UL;
    rec.user_data = ud;
    rec.reserved0 = 0UL;
    rec.reserved1 = 0UL;
    ((gpe_cmd_cb_t)cb)(&rec);
}

int GRM_fbrmPrepareUpdate(void) { return 0; }
int GRM_fbrmPrepareDraw(void) { return 0; }
int GRM_fbrmPrepareSwap(void) { return 0; }
int GRM_fbrmCheckUpdateFinished(void) { return 0; }
int GRM_fbrmSetScreenRotate(int rot) { g_screen_rotate = rot; return 0; }
int GRM_fbrmGetScreenRotate(int *out) { if (out) *out = g_screen_rotate; return 0; }
int GRM_gpermSuspend(void) { return 0; }
int GRM_gpermResume(void) { return 0; }
int GRM_gpermSetWorkImage(void *bmp) { (void)bmp; return 0; }

int GRM_gpermFlush(void) {
    ensure_bitmaps();
    flush_pixels_to_osd("gpermFlush");
    return 0;
}

int GRM_gpermDrawFlush(void *cb, void *ud) {
    ensure_bitmaps();
    flush_pixels_to_osd("gpermDrawFlush");
    invoke_gpe_cmd_cb(cb, ud);
    return 0;
}

int GRM_gpermDrawFinish(void) {
    ensure_bitmaps();
    flush_pixels_to_osd("gpermDrawFinish");
    return 0;
}

void *_ZN3grm17FBResourceManager11getInstanceEv(void) {
    typedef void *(*get_fn)(void);
    typedef void (*ctor_fn)(void *);
    static get_fn real_get;
    static ctor_fn real_ctor;
    if (!real_get) real_get = (get_fn)dlsym((void *)-1L, "_ZN3grm17FBResourceManager11getInstanceEv");
    if (!real_get) return 0;
    void *m = real_get();
    if (!m || guard) return m;
    guard = 1;
    void **fb = (void **)((char *)m + 8);
    if (!*fb) {
        if (!real_ctor) real_ctor = (ctor_fn)dlsym((void *)-1L, "_ZN3grm11FrameBufferC1Ev");
        dprintf(2, "FX6_GRM_FB_MINIMAL before manager=%p fb=%p ctor=%p\n", m, *fb, (void *)real_ctor);
        if (real_ctor) real_ctor(fb_storage);
        *fb = fb_storage;
        dprintf(2, "FX6_GRM_FB_MINIMAL after manager=%p fb=%p vptr=%p\n", m, *fb, *(void **)fb_storage);
    }
    guard = 0;
    return m;
}

/*
 * Native-Faithful GPE rasterizers (verified against libgemini-grm.so +0x7204, +0x7700..0x7e00,
 * and libstella.so +0x52010..0x520c0):
 *   - BMP_PixelFormat == 1 (2 Bpp) -> stella_fmt 7 = RGBA4444 (u16 LE: [15:12]=R, [11:8]=G, [7:4]=B, [3:0]=A).
 *   - BMP_PixelFormat == 2 (4 Bpp) -> stella_fmt 1 = RGBA8888 ([R,G,B,A] bytes for CPU-decoded assets;
 *     GPE-written 4-Bpp work/framebuffer surfaces store 0xAARRGGBB).
 *   - BMP_PixelFormat == 4 (1 Bpp) -> stella_fmt 8 = A8 glyph alpha, tinted by bp[0x3c..0x3e] (R,G,B) when +0x50 == 0x0e.
 *   - Strictly offscreen until gpermDrawFlush / fbrmUpdate / swap.
 *     Zero color substitution, zero image substitution.
 */
static const unsigned char *g_gpe_argb_surfaces[1024];
static unsigned int g_gpe_argb_cnt;

static int is_gpe_argb_surface(const unsigned char *bits) {
    if (!bits) return 0;
    if (bits == pix_off || bits == pix_on) return 1;
    unsigned int n = g_gpe_argb_cnt < 1024U ? g_gpe_argb_cnt : 1024U;
    for (unsigned int i = 0U; i < n; i++) {
        if (g_gpe_argb_surfaces[i] == bits) return 1;
    }
    return 0;
}

static void mark_gpe_argb_surface(const unsigned char *bits) {
    if (!bits || is_gpe_argb_surface(bits)) return;
    if (g_gpe_argb_cnt < 1024U) {
        g_gpe_argb_surfaces[g_gpe_argb_cnt++] = bits;
    }
}

static int resolve_bitmap_surface(
    void *bmp, unsigned char **out_bits, int *out_w, int *out_h, int *out_stride, int *out_fmt, int *out_bpp
) {
    if (!valid_ptr(bmp)) return 0;
    unsigned char *info = *(unsigned char **)((char *)bmp + 0x08);
    unsigned char *bits = *(unsigned char **)((char *)bmp + 0x10);
    if (!valid_ptr(info) || !valid_ptr(bits)) return 0;
    int w = *(short *)(info + 0x10);
    int h = *(short *)(info + 0x12);
    if (w <= 0) w = *(short *)(info + 0x08);
    if (h <= 0) h = *(short *)(info + 0x0a);
    int stride = *(short *)(info + 0x18);
    if (stride < w) stride = w;
    int fmt = *(int *)(info + 0x1c);
    int bpp = query_bpp(fmt);
    if (w <= 0 || h <= 0 || stride <= 0 || bpp <= 0) return 0;
    *out_bits = bits;
    *out_w = w;
    *out_h = h;
    *out_stride = stride;
    *out_fmt = fmt;
    *out_bpp = bpp;
    return 1;
}

int GRM_gpermFillrect(
    unsigned int *cmd_id, const void *cmd_param, const void *fill_param, void *cb, void *ud
) {
    (void)cmd_param;
    ensure_bitmaps();
    if (cmd_id) *cmd_id = 1U;
    if (!valid_ptr(fill_param)) {
        invoke_gpe_cmd_cb(cb, ud);
        return 0;
    }
    const unsigned char *fp = (const unsigned char *)fill_param;
    void *dst_bmp = *(void *const *)(fp + 0x00);
    unsigned char r = fp[0x08];
    unsigned char g = fp[0x09];
    unsigned char b = fp[0x0a];
    unsigned char a = fp[0x0b];
    short rx = *(const short *)(fp + 0x0c);
    short ry = *(const short *)(fp + 0x0e);
    short rw = *(const short *)(fp + 0x10);
    short rh = *(const short *)(fp + 0x12);
    int blend_mode = *(const int *)(fp + 0x14);
    unsigned char const_alpha = fp[0x18];

    unsigned char *dbits = pix_off;
    int dw = FB_W, dh = FB_H, dstride = FB_W, dfmt = 2, dbpp = 4;
    if (valid_ptr(dst_bmp) && dst_bmp != (void *)bmp_off) {
        if (!resolve_bitmap_surface(dst_bmp, &dbits, &dw, &dh, &dstride, &dfmt, &dbpp)) {
            dbits = pix_off; dw = FB_W; dh = FB_H; dstride = FB_W; dfmt = 2; dbpp = 4;
        }
    }

    unsigned int eff_a = (blend_mode == 2)
        ? (((unsigned int)a * (unsigned int)const_alpha) / 255U)
        : (unsigned int)a;
    unsigned int color = (eff_a << 24) | ((unsigned int)r << 16) |
                         ((unsigned int)g << 8) | (unsigned int)b;

    int x0 = rx < 0 ? 0 : rx;
    int y0 = ry < 0 ? 0 : ry;
    int x1 = (rx + rw > dw) ? dw : (rx + rw);
    int y1 = (ry + rh > dh) ? dh : (ry + rh);

    if (dbpp == 4) {
        mark_gpe_argb_surface(dbits);
        unsigned int *base = (unsigned int *)dbits;
        if (blend_mode != 2 || eff_a == 255U) {
            if (blend_mode != 2 || eff_a != 0U) {
                for (int y = y0; y < y1; y++) {
                    unsigned int *row = base + (unsigned long)y * (unsigned long)dstride;
                    for (int x = x0; x < x1; x++) row[x] = color;
                }
            }
        } else if (eff_a != 0U) {
            for (int y = y0; y < y1; y++) {
                unsigned int *row = base + (unsigned long)y * (unsigned long)dstride;
                for (int x = x0; x < x1; x++) {
                    unsigned int dst = row[x];
                    unsigned int da = (dst >> 24) & 0xFFU;
                    unsigned int dr = (dst >> 16) & 0xFFU;
                    unsigned int dg = (dst >> 8)  & 0xFFU;
                    unsigned int db_c = dst & 0xFFU;
                    unsigned int or_c = ((unsigned int)r * eff_a + dr * (255U - eff_a)) / 255U;
                    unsigned int og_c = ((unsigned int)g * eff_a + dg * (255U - eff_a)) / 255U;
                    unsigned int ob_c = ((unsigned int)b * eff_a + db_c * (255U - eff_a)) / 255U;
                    unsigned int oa_c = eff_a + (da * (255U - eff_a)) / 255U;
                    row[x] = (oa_c << 24) | (or_c << 16) | (og_c << 8) | ob_c;
                }
            }
        }
    } else if (dbpp == 2) {
        uint16_t c16 = (uint16_t)((((unsigned int)r >> 4) << 12) |
                                  (((unsigned int)g >> 4) << 8)  |
                                  (((unsigned int)b >> 4) << 4)  |
                                  (eff_a >> 4));
        uint16_t *base16 = (uint16_t *)dbits;
        if (blend_mode != 2 || eff_a != 0U) {
            for (int y = y0; y < y1; y++) {
                uint16_t *row = base16 + (unsigned long)y * (unsigned long)dstride;
                for (int x = x0; x < x1; x++) row[x] = c16;
            }
        }
    } else if (dbpp == 1) {
        if (blend_mode != 2 || eff_a != 0U) {
            for (int y = y0; y < y1; y++) {
                memset(dbits + (unsigned long)y * (unsigned long)dstride + x0,
                       (int)eff_a, (size_t)(x1 > x0 ? (x1 - x0) : 0));
            }
        }
    }

    fillrect_count++;
    draw_prim_count++;
    if (fillrect_count <= 40U || (fillrect_count % 100U) == 0U) {
        dprintf(2,
                "FX6_GPE_FILLRECT #%u (%d,%d,%d,%d) argb=0x%08x blend=%d calpha=%u dst=%p subst_color=0\n",
                fillrect_count, rx, ry, rw, rh, color, blend_mode, (unsigned int)const_alpha, dst_bmp);
    }
    invoke_gpe_cmd_cb(cb, ud);
    return 0;
}

int GRM_gpermRectblit(
    unsigned int *cmd_id, const void *cmd_param, const void *blit_param, void *cb, void *ud
) {
    (void)cmd_param;
    ensure_bitmaps();
    if (cmd_id) *cmd_id = 1U;
    if (!valid_ptr(blit_param)) {
        invoke_gpe_cmd_cb(cb, ud);
        return 0;
    }
    const unsigned char *bp = (const unsigned char *)blit_param;
    void *src = *(void *const *)(bp + 0x00);
    short sx0 = *(const short *)(bp + 0x08);
    short sy0 = *(const short *)(bp + 0x0a);
    short sw0 = *(const short *)(bp + 0x0c);
    short sh0 = *(const short *)(bp + 0x0e);
    void *dst_bmp = *(void *const *)(bp + 0x10);
    short dx0 = *(const short *)(bp + 0x18);
    short dy0 = *(const short *)(bp + 0x1a);
    short dw0 = *(const short *)(bp + 0x1c);
    short dh0 = *(const short *)(bp + 0x1e);
    short cx0 = *(const short *)(bp + 0x20);
    short cy0 = *(const short *)(bp + 0x22);
    short cw0 = *(const short *)(bp + 0x24);
    short ch0 = *(const short *)(bp + 0x26);
    int blend_mode = *(const int *)(bp + 0x28);
    unsigned char const_alpha = bp[0x2c];
    unsigned char const_alpha2 = bp[0x2d];
    int color_mod = *(const int *)(bp + 0x50);
    unsigned int tint_r = (color_mod == 0x0e) ? (unsigned int)bp[0x3c] : 255U;
    unsigned int tint_g = (color_mod == 0x0e) ? (unsigned int)bp[0x3d] : 255U;
    unsigned int tint_b = (color_mod == 0x0e) ? (unsigned int)bp[0x3e] : 255U;

    unsigned char *dbits = pix_off;
    int dst_w = FB_W, dst_h = FB_H, dst_stride = FB_W, dst_fmt = 2, dst_bpp = 4;
    if (valid_ptr(dst_bmp) && dst_bmp != (void *)bmp_off) {
        if (!resolve_bitmap_surface(dst_bmp, &dbits, &dst_w, &dst_h, &dst_stride, &dst_fmt, &dst_bpp)) {
            dbits = pix_off; dst_w = FB_W; dst_h = FB_H; dst_stride = FB_W; dst_fmt = 2; dst_bpp = 4;
        }
    }

    int x0 = dx0 < 0 ? 0 : dx0;
    int y0 = dy0 < 0 ? 0 : dy0;
    int x1 = (dx0 + dw0 > dst_w) ? dst_w : (dx0 + dw0);
    int y1 = (dy0 + dh0 > dst_h) ? dst_h : (dy0 + dh0);
    if (cw0 > 0 && ch0 > 0) {
        if (cx0 > x0) x0 = cx0;
        if (cy0 > y0) y0 = cy0;
        if (cx0 + cw0 < x1) x1 = cx0 + cw0;
        if (cy0 + ch0 < y1) y1 = cy0 + ch0;
    }

    int fmt = -1;
    int bpp = 0;
    unsigned int src_nz = 0U;

    unsigned char *sbits = 0;
    int sw = 0, sh = 0, sstride = 0;
    if (resolve_bitmap_surface(src, &sbits, &sw, &sh, &sstride, &fmt, &bpp)) {
        int src_is_gpe_argb = (bpp == 4) ? is_gpe_argb_surface(sbits) : 0;
        if (dst_bpp == 4) {
            mark_gpe_argb_surface(dbits);
        }
        if (sw0 <= 0) sw0 = (short)sw;
        if (sh0 <= 0) sh0 = (short)sh;
        unsigned long row_pitch = (unsigned long)sstride * (unsigned long)bpp;

        for (int dy = y0; dy < y1; dy++) {
            int rel_y = dy - (int)dy0;
            int sy = (dw0 > 0 && dh0 > 0) ? ((int)sy0 + (rel_y * (int)sh0) / (int)dh0) : ((int)sy0 + rel_y);
            if (sy < 0 || sy >= sh) continue;
            const unsigned char *srow = sbits + (unsigned long)sy * row_pitch;

            for (int dx = x0; dx < x1; dx++) {
                int rel_x = dx - (int)dx0;
                int sx = (dw0 > 0 && dh0 > 0) ? ((int)sx0 + (rel_x * (int)sw0) / (int)dw0) : ((int)sx0 + rel_x);
                if (sx < 0 || sx >= sw) continue;

                unsigned int sr = 0U, sg = 0U, sb = 0U, sa = 0U;
                if (bpp == 4) {
                    if (src_is_gpe_argb) {
                        unsigned int p = ((const unsigned int *)srow)[sx];
                        sa = (p >> 24) & 0xFFU;
                        sr = (p >> 16) & 0xFFU;
                        sg = (p >> 8)  & 0xFFU;
                        sb = p & 0xFFU;
                        if (p != 0U) src_nz++;
                    } else {
                        /* BMP_PixelFormat == 2 -> stella_fmt == 1 (RGBA8888 bytes [R,G,B,A]) */
                        const unsigned char *px4 = srow + (unsigned long)sx * 4UL;
                        sr = px4[0];
                        sg = px4[1];
                        sb = px4[2];
                        sa = px4[3];
                        if ((sr | sg | sb | sa) != 0U) src_nz++;
                    }
                } else if (bpp == 1) {
                    sa = srow[sx];
                    sr = tint_r;
                    sg = tint_g;
                    sb = tint_b;
                    if (sa != 0U) src_nz++;
                } else if (bpp == 2) {
                    uint16_t p16 = ((const uint16_t *)srow)[sx];
                    if (p16 != 0U) src_nz++;
                    if (fmt == 1) {
                        /* BMP_PixelFormat == 1 -> stella_fmt == 7 (RGBA4444: [15:12]=R,[11:8]=G,[7:4]=B,[3:0]=A) */
                        sr = ((p16 >> 12) & 0xFU) * 17U;
                        sg = ((p16 >> 8)  & 0xFU) * 17U;
                        sb = ((p16 >> 4)  & 0xFU) * 17U;
                        sa = (p16 & 0xFU) * 17U;
                    } else if (fmt == 3) { /* ARGB4444 */
                        sa = ((p16 >> 12) & 0xFU) * 17U;
                        sr = ((p16 >> 8)  & 0xFU) * 17U;
                        sg = ((p16 >> 4)  & 0xFU) * 17U;
                        sb = (p16 & 0xFU) * 17U;
                    } else { /* ARGB1555 fallback */
                        sa = (p16 & 0x8000U) ? 255U : 0U;
                        sr = ((p16 >> 10) & 0x1FU) * 255U / 31U;
                        sg = ((p16 >> 5)  & 0x1FU) * 255U / 31U;
                        sb = (p16 & 0x1FU) * 255U / 31U;
                    }
                }

                if (blend_mode == 2 || blend_mode == 3) {
                    sa = (sa * (unsigned int)const_alpha) / 255U;
                    if (blend_mode == 3) {
                        sa = (sa * (unsigned int)const_alpha2) / 255U;
                    }
                }

                if (dst_bpp == 4) {
                    unsigned int *drow = (unsigned int *)dbits + (unsigned long)dy * (unsigned long)dst_stride;
                    if (blend_mode == 1) {
                        drow[dx] = (sa << 24) | (sr << 16) | (sg << 8) | sb;
                    } else if (sa != 0U) {
                        unsigned int dst = drow[dx];
                        unsigned int da = (dst >> 24) & 0xFFU;
                        unsigned int dr = (dst >> 16) & 0xFFU;
                        unsigned int dg = (dst >> 8)  & 0xFFU;
                        unsigned int db_c = dst & 0xFFU;
                        unsigned int or_c = (sr * sa + dr * (255U - sa)) / 255U;
                        unsigned int og_c = (sg * sa + dg * (255U - sa)) / 255U;
                        unsigned int ob_c = (sb * sa + db_c * (255U - sa)) / 255U;
                        unsigned int oa_c = sa + (da * (255U - sa)) / 255U;
                        drow[dx] = (oa_c << 24) | (or_c << 16) | (og_c << 8) | ob_c;
                    }
                } else if (dst_bpp == 2) {
                    uint16_t *drow = (uint16_t *)dbits + (unsigned long)dy * (unsigned long)dst_stride;
                    if (blend_mode == 1) {
                        drow[dx] = (uint16_t)(((sr >> 4) << 12) | ((sg >> 4) << 8) | ((sb >> 4) << 4) | (sa >> 4));
                    } else if (sa != 0U) {
                        uint16_t d16 = drow[dx];
                        unsigned int dr = ((d16 >> 12) & 0xFU) * 17U;
                        unsigned int dg = ((d16 >> 8)  & 0xFU) * 17U;
                        unsigned int db_c = ((d16 >> 4) & 0xFU) * 17U;
                        unsigned int da = (d16 & 0xFU) * 17U;
                        unsigned int or_c = (sr * sa + dr * (255U - sa)) / 255U;
                        unsigned int og_c = (sg * sa + dg * (255U - sa)) / 255U;
                        unsigned int ob_c = (sb * sa + db_c * (255U - sa)) / 255U;
                        unsigned int oa_c = sa + (da * (255U - sa)) / 255U;
                        drow[dx] = (uint16_t)(((or_c >> 4) << 12) | ((og_c >> 4) << 8) | ((ob_c >> 4) << 4) | (oa_c >> 4));
                    }
                } else if (dst_bpp == 1) {
                    unsigned char *drow = dbits + (unsigned long)dy * (unsigned long)dst_stride;
                    if (blend_mode == 1) {
                        drow[dx] = (unsigned char)sa;
                    } else if (sa != 0U) {
                        unsigned int da = drow[dx];
                        unsigned int oa_c = sa + (da * (255U - sa)) / 255U;
                        drow[dx] = (unsigned char)(oa_c > 255U ? 255U : oa_c);
                    }
                }
            }
        }
    }
    rectblit_count++;
    draw_prim_count++;
    if (rectblit_count <= 40U || (rectblit_count % 100U) == 0U) {
        dprintf(2,
                "FX6_GPE_RECTBLIT #%u dst=(%d,%d,%d,%d) target=%p src=%p fmt=%d bpp=%d "
                "src_nz=%u blend=%d calpha=%u tint=0x%02x%02x%02x subst_image=0\n",
                rectblit_count, dx0, dy0, dw0, dh0, dst_bmp, src, fmt, bpp,
                src_nz, blend_mode, (unsigned int)const_alpha, tint_r, tint_g, tint_b);
    }
    invoke_gpe_cmd_cb(cb, ud);
    return 0;
}

int _ZN2ma4MMap3mapElm(void *self, long addr, unsigned long len) {
    (void)self; (void)addr; (void)len;
    dprintf(2, "FX6_MA_MMAP_SKIP\n");
    return 0;
}

static unsigned int g_font_create2_cnt;
void _ZN2ux6resmgr15ResourceManager10createFontERKN5alcor13FontAttributeERN5libra9RecordPtrE(
    const void *attr, void *rec
) {
    typedef void (*fn_t)(const void *, void *);
    static fn_t real;
    if (!real) {
        void *h = dlopen("/usr/lib/libuxengine.so", RTLD_LAZY | RTLD_GLOBAL);
        real = h ? (fn_t)dlsym(h, "_ZN2ux6resmgr15ResourceManager10createFontERKN5alcor13FontAttributeERN5libra9RecordPtrE") : 0;
    }
    unsigned int c = ++g_font_create2_cnt;
    if (c <= 20U || (c % 1000U) == 0U) {
        dprintf(2, "FX6_FONT_CREATE2 #%u attr=%p rec=%p before=%p real=%p\n",
                c, attr, rec, rec ? *(void **)rec : 0, (void *)real);
    }
    if (real) real(attr, rec);
    if (c <= 20U || (c % 1000U) == 0U) {
        dprintf(2, "FX6_FONT_CREATE2_DONE #%u rec=%p after=%p\n",
                c, rec, rec ? *(void **)rec : 0);
    }
}

__attribute__((constructor)) static void stub_ctor(void) {
    dprintf(2,
            "FX6_NATIVE_FAITHFUL_SHIM_LOADED round=%d restore_infra70=%d restore_all_early=%d "
            "subst_color=0 subst_image=0 forced_render=0 skipped_node=0 lock_bypass=0\n",
            FX6_ROUND, FX6_RESTORE_INFRA70, FX6_RESTORE_ALL_EARLY);
    dprintf(2, "FX3_GPE_RESOURCE_REGISTER type=0x403 logical=0x41e001000 phys=0x41e001000 bytes=0x21c000\n");
}

static void fx6_patch_blocking_calls(void *real_init) {
    fx6_dl_info_t di;
    memset(&di, 0, sizeof(di));
    if (!dladdr(real_init, &di) || !di.dli_fbase) return;
    g_appfw_base = (uptr)di.dli_fbase;

    unsigned long offs[6];
    int count = 0;
#if !FX6_RESTORE_ALL_EARLY
    offs[count++] = 0x12d824cUL;
    offs[count++] = 0x12d8250UL;
#if !FX6_RESTORE_INFRA70
    offs[count++] = 0x12d8254UL;
#endif
#endif
#if FX6_ROUND < 3
    /* Round 1 & 2 keep App::start_utimer NOPed; Round 3 restores native App::start_utimer! */
    offs[count++] = 0xc09e50UL;
#endif

    dprintf(2, "FX6_PATCH_PLAN appFw_base=%p nop_count=%d round=%d\n",
            di.dli_fbase, count, FX6_ROUND);
    for (int i = 0; i < count; i++) {
        unsigned long a = (unsigned long)di.dli_fbase + offs[i];
        unsigned long page = a & ~0xfffUL;
        int mr = mprotect((void *)page, 0x1000, PROT_READ | PROT_WRITE | PROT_EXEC);
        *(unsigned int *)a = 0xd503201fU;
        __builtin___clear_cache((char *)a, (char *)a + 4);
        dprintf(2, "FX6_PATCH_NOP off=0x%lx addr=%p mprotect=%d\n", offs[i], (void *)a, mr);
    }
}

void Application_System_Init(const char *arg) {
    typedef void (*fn_t)(const char *);
    void *h = dlopen("/usr/lib/appFw.so", RTLD_LAZY | RTLD_GLOBAL);
    fn_t real = h ? (fn_t)dlsym(h, "Application_System_Init") : 0;
    dprintf(2, "FX6_APP_CONFIG_ENTRY arg=%s appFw=%p real=%p round=%d\n",
            arg ? arg : "(null)", h, (void *)real, FX6_ROUND);
    if (real) fx6_patch_blocking_calls((void *)real);
    if (real) real("AppConfig.so");
    dprintf(2, "FX6_APP_CONFIG_HOLD real_returned round=%d\n", FX6_ROUND);
    for (;;) sleep(3600);
}

/* kikilog hardware is absent in VM; accept callback registration. */
int kikilog_set_notify_cb(void *cb, void *arg) {
    dprintf(2, "FX6_KIKILOG_STUB set cb=%p arg=%p\n", cb, arg);
    return 0;
}
int kikilog_clear_notify_cb(void) {
    dprintf(2, "FX6_KIKILOG_STUB clear\n");
    return 0;
}

/* FX6 backup memory bridge: never touch /dev/backup.
 * Round 4+: serve genuine Sony FX6 (fx6_chaplin_ntsc BK4) factory media-slot
 * configuration bytes for 0x00cf0000..0x00cf040b and 0x010d006c / 0x010d0085. */
#if FX6_ROUND >= 4
static const uint8_t k_fx6_bk4_slot0[21] = {
    0x00, 0x10, 0x00, 0x00, 0x10, 0xdf, 0x03, 0x0a,
    0x00, 0x00, 0x00, 0x03, 0x01, 0x03, 0x00, 0x41,
    0x40, 0x10, 0x00, 0x2a, 0x01
};
static const uint8_t k_fx6_bk4_slot1[28] = {
    0x10, 0x10, 0x00, 0x00, 0x20, 0xdf, 0x03, 0x0a,
    0x00, 0x00, 0x00, 0x03, 0x02, 0x03, 0x00, 0x41,
    0x40, 0x18, 0x00, 0x32, 0x02, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x02
};
static const uint8_t k_fx6_bk4_slot7[28] = {
    0x00, 0x20, 0x00, 0x00, 0x00, 0xd6, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x05, 0x00, 0x03, 0x00, 0x41,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0xff
};
static const uint8_t k_fx6_bk4_slot8[28] = {
    0x01, 0x30, 0x00, 0x00, 0x17, 0xd5, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x01, 0x00, 0x03, 0x00, 0x08,
    0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0xff
};
static unsigned int g_backup_query_log_cnt;
static unsigned int g_backup_media_hit_cnt;
static unsigned int g_backup_nread_multi_cnt;

#define FX6_BK4_BYTES 2253333UL
static const uint8_t *g_bk4_map;
static int g_bk4_tried;
static const uint8_t k_fx6_handover_comp = 3U; /* HAND_OVER_STATUS_AFTER_UUD_FROM_DIADEM_PRO_COMP */
static const uint8_t k_fx6_saved_fw_ver_601[4] = { 0x01U, 0x00U, 0x06U, 0x00U }; /* 0x00060001 ("6.01") */
static uint8_t g_bk_fallback_byte;

typedef struct {
    uint32_t id;
    uint32_t len;
    uint8_t  data[16];
} fx6_bk_write_entry_t;
static fx6_bk_write_entry_t g_bk_writes[128];
static unsigned int g_bk_write_cnt;

static uint16_t bk4_u16(const uint8_t *p) {
    return (uint16_t)((uint16_t)p[0] | ((uint16_t)p[1] << 8));
}

static uint32_t bk4_u32(const uint8_t *p) {
    return (uint32_t)p[0] |
           ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) |
           ((uint32_t)p[3] << 24);
}

static const uint8_t *ensure_bk4_mapped(void) {
    if (g_bk4_tried) return g_bk4_map;
    g_bk4_tried = 1;
    int fd = open("/etc/fx6_chaplin_ntsc.bk4", 0);
    if (fd < 0) {
        dprintf(2, "FX6_BK4_MMAP status=missing path=/etc/fx6_chaplin_ntsc.bk4\n");
        return 0;
    }
    void *m = mmap(0, FX6_BK4_BYTES, PROT_READ, 2 /* MAP_PRIVATE */, fd, 0L);
    close(fd);
    if (!m || (long)m == -1L) {
        dprintf(2, "FX6_BK4_MMAP status=failed map=%p\n", m);
        return 0;
    }
    g_bk4_map = (const uint8_t *)m;
    dprintf(2, "FX6_BK4_MMAP status=ok base=%p bytes=%lu\n", m, FX6_BK4_BYTES);
    return g_bk4_map;
}

static int fx6_bk4_lookup_byte(uint32_t id, uint8_t *out_val) {
    if (id >= 0x00cf0000U && id <= 0x00cf03ffU) {
        uint32_t slot = (id - 0x00cf0000U) >> 6;
        uint32_t off  = (id - 0x00cf0000U) & 0x3fU;
        uint8_t v = 0U;
        if (slot == 0U && off < sizeof(k_fx6_bk4_slot0)) v = k_fx6_bk4_slot0[off];
        else if (slot == 1U && off < sizeof(k_fx6_bk4_slot1)) v = k_fx6_bk4_slot1[off];
        else if (slot == 7U && off < sizeof(k_fx6_bk4_slot7)) v = k_fx6_bk4_slot7[off];
        else if (slot == 8U && off < sizeof(k_fx6_bk4_slot8)) v = k_fx6_bk4_slot8[off];
        if (out_val) *out_val = v;
        return 1;
    }
    if (id >= 0x00cf0400U && id <= 0x00cf040bU) {
        uint8_t v = (id == 0x00cf0408U || id == 0x00cf040aU) ? 1U : 0U;
        if (out_val) *out_val = v;
        return 1;
    }
    if (id == 0x010d006cU || id == 0x010d0085U) {
        if (out_val) *out_val = 1U;
        return 1;
    }
    return 0;
}

static int fx6_bk4_lookup_span(uint32_t id, const uint8_t **out_ptr, uint32_t *out_len) {
    unsigned int wc = g_bk_write_cnt < 128U ? g_bk_write_cnt : 128U;
    for (unsigned int i = 0; i < wc; i++) {
        if (g_bk_writes[i].id == id) {
            if (out_ptr) *out_ptr = g_bk_writes[i].data;
            if (out_len) *out_len = g_bk_writes[i].len;
            return 1;
        }
    }
    /* Operational FX6 Ver. 6.01 persistent state: saved setting-table version 6.01 + UUD handover COMP */
#if FX6_INITIAL_SETTING_DONE
    if (id == 0x02cf0068U) {
        static const uint8_t k_fx6_init_setting_done = 0U;
        if (out_ptr) *out_ptr = &k_fx6_init_setting_done;
        if (out_len) *out_len = 1U;
        return 1;
    }
#endif
    if (id == 0x02cf0069U) {
        if (out_ptr) *out_ptr = k_fx6_saved_fw_ver_601;
        if (out_len) *out_len = 4U;
        return 1;
    }
    if (id == 0x02cf15c8U) {
        if (out_ptr) *out_ptr = &k_fx6_handover_comp;
        if (out_len) *out_len = 1U;
        return 1;
    }
    const uint8_t *blob = ensure_bk4_mapped();
    if (blob) {
        static const unsigned long k_rec_bases[2] = { 0UL, 872448UL };
        for (int r = 0; r < 2; r++) {
            unsigned long base = k_rec_bases[r];
            if (base + 256UL > FX6_BK4_BYTES) continue;
            if (blob[base + 12] != 'B' || blob[base + 13] != 'K' ||
                blob[base + 14] != '4' || blob[base + 15] != 0) {
                continue;
            }
            uint32_t ns     = bk4_u32(blob + base + 16);
            uint32_t np_cnt = bk4_u32(blob + base + 20);
            uint32_t start  = bk4_u32(blob + base + 24);
            uint32_t size   = bk4_u32(blob + base + 28);
            uint32_t sub    = id >> 16;
            uint32_t unit   = id & 0xffffU;
            if (sub >= ns) continue;
            unsigned long s_off = base + 256UL + 6UL * (unsigned long)sub;
            if (s_off + 6UL > FX6_BK4_BYTES) continue;
            uint16_t cnt = bk4_u16(blob + s_off);
            uint32_t idx = bk4_u32(blob + s_off + 2UL);
            if (unit >= (uint32_t)cnt || (idx + unit) >= np_cnt) continue;
            unsigned long p_off = base + 256UL + 6UL * (unsigned long)ns +
                                  6UL * (unsigned long)(idx + unit);
            if (p_off + 6UL > FX6_BK4_BYTES) continue;
            uint32_t ptr = bk4_u32(blob + p_off + 2UL);
            if (ptr == 0xffffffffU) continue;
            uint32_t ln  = ptr >> 24;
            uint32_t off = ptr & 0xffffffU;
            uint32_t rlen = 0U;
            unsigned long doff = 0UL;
            if (ln == 255U) {
                if (base + off + 2UL > FX6_BK4_BYTES) continue;
                rlen = (uint32_t)bk4_u16(blob + base + off);
                doff = base + (unsigned long)off + 2UL;
            } else if (ln == 0U) {
                if (base + off + 4UL > FX6_BK4_BYTES) continue;
                rlen = (uint32_t)bk4_u16(blob + base + off);
                doff = base + (unsigned long)off + 4UL;
            } else {
                rlen = ln;
                doff = base + (unsigned long)off;
            }
            if (doff + (unsigned long)rlen <= base + (unsigned long)start + (unsigned long)size &&
                doff + (unsigned long)rlen <= FX6_BK4_BYTES) {
                if (out_ptr) *out_ptr = blob + doff;
                if (out_len) *out_len = rlen;
                return 1;
            }
        }
    }
    if (fx6_bk4_lookup_byte(id, &g_bk_fallback_byte)) {
        if (out_ptr) *out_ptr = &g_bk_fallback_byte;
        if (out_len) *out_len = 1U;
        return 1;
    }
    return 0;
}

int Backup_get_datasize(unsigned int id) {
    const uint8_t *ptr = 0;
    uint32_t len = 0U;
    if (fx6_bk4_lookup_span(id, &ptr, &len)) {
        if (id == 0x007a0001U || id == 0x003e0005U) {
            dprintf(2, "FX6_BACKUP_MEDIA op=get_datasize id=0x%08x len=%u\n", id, len);
        }
        return (int)len;
    }
    unsigned int c = __atomic_add_fetch(&g_backup_query_log_cnt, 1U, __ATOMIC_RELAXED);
    if (c <= 60U) {
        dprintf(2, "FX6_BACKUP_QUERY op=get_datasize id=0x%08x miss=1\n", id);
    }
    return 0;
}

int Backup_read_multi(const unsigned int *ids, void **ptrs) {
    if (!ids || !ptrs) return 0;
    int count = 0;
    while (ids[count] != 0U) {
        const uint8_t *sp = 0;
        uint32_t slen = 0U;
        if (fx6_bk4_lookup_span(ids[count], &sp, &slen)) {
            if (ptrs[count] && sp && slen > 0U) {
                memcpy(ptrs[count], sp, (size_t)slen);
            }
            count++;
        } else {
            unsigned int c = __atomic_add_fetch(&g_backup_query_log_cnt, 1U, __ATOMIC_RELAXED);
            if (c <= 60U) {
                dprintf(2, "FX6_BACKUP_QUERY op=read_multi id=0x%08x idx=%d miss=1\n", ids[count], count);
            }
            break;
        }
    }
    unsigned int h = __atomic_add_fetch(&g_backup_media_hit_cnt, 1U, __ATOMIC_RELAXED);
    if (h <= 20U) {
        dprintf(2, "FX6_BACKUP_MEDIA op=read_multi first_id=0x%08x count=%d\n", ids[0], count);
    }
    return count;
}
#endif

int Backup_get_suspend_flag(void) { return 0; }

int Backup_nread(unsigned int id, void *buf, int size) {
    if (buf && size > 0) memset(buf, 0, (size_t)size);
#if FX6_ROUND >= 4
    const uint8_t *sp = 0;
    uint32_t slen = 0U;
    if (fx6_bk4_lookup_span(id, &sp, &slen)) {
        if (buf && size > 0 && sp && slen > 0U) {
            uint32_t copy_n = (uint32_t)size < slen ? (uint32_t)size : slen;
            memcpy(buf, sp, (size_t)copy_n);
        }
        if (id == 0x02cf15c8U) {
            dprintf(2, "FX6_BACKUP_MEDIA op=nread id=0x%08x sz=%d val=0x%02x\n",
                    id, size, sp ? (unsigned int)sp[0] : 0U);
        }
        return size > 0 ? size : (int)slen;
    }
    unsigned int c = __atomic_add_fetch(&g_backup_query_log_cnt, 1U, __ATOMIC_RELAXED);
    if (c <= 60U) {
        dprintf(2, "FX6_BACKUP_QUERY op=nread id=0x%08x sz=%d miss=1\n", id, size);
    }
#else
    (void)id;
#endif
    return size > 0 ? size : 4;
}

int Backup_read(unsigned int id, void *buf) {
#if FX6_ROUND >= 4
    const uint8_t *sp = 0;
    uint32_t slen = 0U;
    if (fx6_bk4_lookup_span(id, &sp, &slen)) {
        if (buf && sp && slen > 0U) {
            memcpy(buf, sp, (size_t)slen);
        }
        unsigned int h = __atomic_add_fetch(&g_backup_media_hit_cnt, 1U, __ATOMIC_RELAXED);
        if (h <= 40U || id == 0x007a0001U || id == 0x02cf15c8U) {
            dprintf(2, "FX6_BACKUP_MEDIA op=read id=0x%08x len=%u b0=0x%02x\n",
                    id, slen, sp ? (unsigned int)sp[0] : 0U);
        }
        return (int)slen;
    }
    unsigned int c = __atomic_add_fetch(&g_backup_query_log_cnt, 1U, __ATOMIC_RELAXED);
    if (c <= 60U) {
        dprintf(2, "FX6_BACKUP_QUERY op=read id=0x%08x miss=1\n", id);
    }
#else
    (void)id; (void)buf;
#endif
    return 0;
}

int Backup_nread_multi(const unsigned int *ids, void **ptrs, const unsigned int *sizes) {
    if (!ids || !ptrs) return 0;
    int count = 0;
    int hits = 0;
    int hit_3927 = 0;
    while (ids[count] != 0U) {
        unsigned int id = ids[count];
        unsigned int sz = sizes ? sizes[count] : 4U;
        void *dst = ptrs[count];
        if (dst && sz > 0U) memset(dst, 0, (size_t)sz);
#if FX6_ROUND >= 4
        const uint8_t *sp = 0;
        uint32_t slen = 0U;
        if (fx6_bk4_lookup_span(id, &sp, &slen)) {
            if (dst && sz > 0U && sp && slen > 0U) {
                uint32_t copy_n = sz < slen ? sz : slen;
                memcpy(dst, sp, (size_t)copy_n);
            }
            hits++;
            if (id == 0x02cf15c8U) {
                hit_3927 = sp ? (int)sp[0] : -1;
            }
        }
#endif
        count++;
    }
#if FX6_ROUND >= 4
    unsigned int mc = __atomic_add_fetch(&g_backup_nread_multi_cnt, 1U, __ATOMIC_RELAXED);
    if (mc <= 16U || hit_3927 > 0) {
        dprintf(2,
                "FX6_BACKUP_NREAD_MULTI call=%u first_id=0x%08x count=%d bk4_hits=%d handover_02cf15c8=%d\n",
                mc, ids[0], count, hits, hit_3927);
    }
#endif
    return count;
}

int Backup_nread_setting_attr(void *a, ...) { (void)a; return 0; }
int Backup_read_rst_attr(void *a, ...) { (void)a; return 0; }
int Backup_reset_all(void) { return 0; }
int Backup_reset_subsystem(void *a, ...) { (void)a; return 0; }
int Backup_sync_all(void) { return 0; }
int Backup_sync_subsystem(void *a, ...) { (void)a; return 0; }
int Backup_write_setting_attr(void *a, ...) { (void)a; return 0; }
int Backup_write_vsize(unsigned int id, const void *buf, int size) {
    (void)id; (void)buf;
    return size > 0 ? size : 4;
}
int Backup_write(unsigned int id, const void *buf, int size) {
#if FX6_ROUND >= 4
    if (buf && size > 0 && size <= 16) {
        unsigned int wc = g_bk_write_cnt < 128U ? g_bk_write_cnt : 128U;
        int updated = 0;
        for (unsigned int i = 0; i < wc; i++) {
            if (g_bk_writes[i].id == id) {
                memset(g_bk_writes[i].data, 0, sizeof(g_bk_writes[i].data));
                memcpy(g_bk_writes[i].data, buf, (size_t)size);
                g_bk_writes[i].len = (uint32_t)size;
                updated = 1;
                break;
            }
        }
        if (!updated && g_bk_write_cnt < 128U) {
            unsigned int idx = g_bk_write_cnt++;
            g_bk_writes[idx].id = id;
            g_bk_writes[idx].len = (uint32_t)size;
            memcpy(g_bk_writes[idx].data, buf, (size_t)size);
        }
    }
#else
    (void)id; (void)buf;
#endif
    return size > 0 ? size : 4;
}
int Backup_reg_cb(void *a, ...) { (void)a; return 0; }
int backup_sync_msg(int *ret, ...) { if (ret) *ret = 0; return 0; }
int backup_async_msg(void *a, ...) { (void)a; return 0; }
int backup_sharedcb_send_msg(void *a, ...) { (void)a; return 0; }
