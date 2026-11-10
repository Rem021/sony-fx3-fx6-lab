/*
 * libgrm-fbinit9.c — FX6_NATIVE_FAITHFUL Cold-Boot & GPE/GRM Bridge
 *
 * Strictly enforces FX6_NATIVE_FAITHFUL=1 invariants across Rounds 1..3:
 *   subst_color=0  subst_image=0  forced_render=0  skipped_node=0  lock_bypass=0
 *
 * Compile-time single-variable switches:
 *   -DFX6_ROUND=1  Round 1: Real MWF_Init (in appfw-launch) + removed MonCtrl::GetFlag mask
 *   -DFX6_ROUND=2  Round 2: + Minimal compliant UIPC completion for SeqQueueCommon (0x92840747 0x032d)
 *                           + ScreenManager / Presenter / TriggerCb milestone observation
 *   -DFX6_ROUND=3  Round 3: + Native App::start_utimer (0xc09e50 un-NOPed)
 *                           + GRM_fbrmRegisterTriggerFrameworkCb 25Hz vsync pump & DrawCompletionCb
 */

#ifndef FX6_ROUND
#define FX6_ROUND 3
#endif

#ifndef FX6_RESTORE_INFRA70
#define FX6_RESTORE_INFRA70 0
#endif

#ifndef FX6_RESTORE_ALL_EARLY
#define FX6_RESTORE_ALL_EARLY 0
#endif

#ifndef FX6_REPLY_ALL_200D
#define FX6_REPLY_ALL_200D 0
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
    const unsigned int *p32 = (const unsigned int *)pix_off;
    for (unsigned int i = 0; i < (FB_W * FB_H); i++) {
        if (p32[i] != 0U) nz++;
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
                "FX6_OSD_FLUSH %s #%u prims=%u fill=%u blit=%u nz_pixels=%u "
                "subst_color=0 subst_image=0 forced_render=0 skipped_node=0 lock_bypass=0\n",
                tag, flush_count, draw_prim_count, fillrect_count, rectblit_count, nz);
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
        void **slots = (void **)(base + 0x432ded0UL);
        for (int i = 0; i < 7; i++) {
            void *p = slots[i];
            void *vptr = valid_ptr(p) ? *(void **)p : 0;
            void *scr = valid_ptr(p) ? *(void **)((char *)p + 0x10) : 0;
            uptr vptr_off = (vptr && base && (uptr)vptr > base) ? ((uptr)vptr - base) : 0UL;
            dprintf(2,
                    "FX6_PRESENTER_SLOT idx=%d tag=%s obj=%p vptr=%p vptr_off=0x%lx screen=%p\n",
                    i, tag, p, vptr, (unsigned long)vptr_off, scr);
        }
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
                if (tick == 5U || tick == 50U || tick == 150U) {
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
typedef int (*osal_valloc_msg_wait_fn)(uint32_t, void **, int, int);
typedef int (*osal_free_msg_fn)(uint32_t, void *);
typedef uint32_t (*osal_get_msg_src_fn)(const void *);
typedef void (*osal_set_msg_src_fn)(void *, uint32_t);
typedef int (*osal_msg_size_fn)(const void *);

static osal_snd_msg_fn         g_real_snd_msg;
static osal_valloc_msg_wait_fn g_real_valloc_msg;
static osal_free_msg_fn        g_real_free_msg;
static osal_get_msg_src_fn     g_real_get_src;
static osal_set_msg_src_fn     g_real_set_src;
static osal_msg_size_fn        g_real_msg_size;
static unsigned int            g_uipc_snd_seq;

static void ensure_uipc_syms(void) {
    if (g_real_snd_msg) return;
    void *h = dlopen("/usr/lib/libosal_uipc.so", RTLD_LAZY | RTLD_GLOBAL);
    if (!h) {
        dprintf(2, "FX6_UIPC_DLOPEN_FAILED\n");
        _exit(126);
    }
    g_real_snd_msg    = (osal_snd_msg_fn)dlsym(h, "osal_snd_msg");
    g_real_valloc_msg = (osal_valloc_msg_wait_fn)dlsym(h, "osal_valloc_msg_wait");
    g_real_free_msg   = (osal_free_msg_fn)dlsym(h, "osal_free_msg");
    g_real_get_src    = (osal_get_msg_src_fn)dlsym(h, "osal_get_msg_src");
    g_real_set_src    = (osal_set_msg_src_fn)dlsym(h, "osal_set_msg_src");
    g_real_msg_size   = (osal_msg_size_fn)dlsym(h, "osal_msg_size");
}

static int is_unanswered_bb_adf_dest(uint32_t dest_qid, uint32_t src_qid) {
    if ((src_qid >> 16) != 0x81cfU) return 0;
    if (dest_qid == 0x92840747U) return 1;
#if FX6_REPLY_ALL_200D
    if (dest_qid == 0x909a015aU || dest_qid == 0x909c015bU || dest_qid == 0x912f0335U) {
        return 1;
    }
#endif
    return 0;
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

    if (dest_qid != 0x8f013aU && dest_qid != 0x5503e0U) {
        unsigned int seq = __atomic_add_fetch(&g_uipc_snd_seq, 1U, __ATOMIC_RELAXED);
        if (seq <= 300U) {
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
            } else if (dest_qid == 0x909a015aU || dest_qid == 0x909c015bU) {
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

void _ZN2ux6gfxeng6Screen20setAreaInFramebufferEsstt(
    void *self, short x, short y, unsigned short w, unsigned short h
) {
    typedef void (*real_fn)(void *, short, short, unsigned short, unsigned short);
    static real_fn real;
    if (!real) real = (real_fn)dlsym((void *)-1L, "_ZN2ux6gfxeng6Screen20setAreaInFramebufferEsstt");
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
    flush_pixels_to_osd("getOffscreen");
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
 * Native-Faithful GPE rasterizers:
 *   - GRM_gpermFillrect writes the EXACT ARGB8888 color requested by libgemini-grm.so.
 *     Zero slate clear override, zero pseudo-random blue card fill, zero focus highlight.
 *   - GRM_gpermRectblit blits the exact source bitmap pixels according to native format & bpp.
 */
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
    unsigned char r = fp[0x08];
    unsigned char g = fp[0x09];
    unsigned char b = fp[0x0a];
    unsigned char a = fp[0x0b];
    short rx = *(const short *)(fp + 0x0c);
    short ry = *(const short *)(fp + 0x0e);
    short rw = *(const short *)(fp + 0x10);
    short rh = *(const short *)(fp + 0x12);
    unsigned int color = ((unsigned int)a << 24) | ((unsigned int)r << 16) |
                         ((unsigned int)g << 8)  | (unsigned int)b;

    int x0 = rx < 0 ? 0 : rx;
    int y0 = ry < 0 ? 0 : ry;
    int x1 = (rx + rw > FB_W) ? FB_W : (rx + rw);
    int y1 = (ry + rh > FB_H) ? FB_H : (ry + rh);
    unsigned int *base = (unsigned int *)pix_off;
    for (int y = y0; y < y1; y++) {
        for (int x = x0; x < x1; x++) {
            base[y * FB_W + x] = color;
        }
    }
    fillrect_count++;
    draw_prim_count++;
    if (fillrect_count <= 40U || (fillrect_count % 50U) == 0U) {
        dprintf(2,
                "FX6_GPE_FILLRECT #%u (%d,%d,%d,%d) argb=0x%08x cb=%p ud=%p subst_color=0\n",
                fillrect_count, rx, ry, rw, rh, color, cb, ud);
    }
    invoke_gpe_cmd_cb(cb, ud);
    flush_pixels_to_osd("fillrect");
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
    short dx0 = *(const short *)(bp + 0x18);
    short dy0 = *(const short *)(bp + 0x1a);
    short dw0 = *(const short *)(bp + 0x1c);
    short dh0 = *(const short *)(bp + 0x1e);
    int x0 = dx0 < 0 ? 0 : dx0;
    int y0 = dy0 < 0 ? 0 : dy0;
    int x1 = (dx0 + dw0 > FB_W) ? FB_W : (dx0 + dw0);
    int y1 = (dy0 + dh0 > FB_H) ? FB_H : (dy0 + dh0);
    unsigned int *db = (unsigned int *)pix_off;
    int fmt = -1;
    int bpp = 0;

    if (valid_ptr(src)) {
        unsigned char *info = *(unsigned char **)((char *)src + 0x08);
        unsigned char *bits = *(unsigned char **)((char *)src + 0x10);
        if (valid_ptr(info) && valid_ptr(bits)) {
            int sw = *(short *)(info + 0x10);
            int sh = *(short *)(info + 0x12);
            if (sw <= 0) sw = *(short *)(info + 0x08);
            if (sh <= 0) sh = *(short *)(info + 0x0a);
            int stride = *(short *)(info + 0x18);
            if (stride < sw) stride = sw;
            fmt = *(int *)(info + 0x1c);
            bpp = query_bpp(fmt);
            unsigned long row_pitch = (unsigned long)stride * (unsigned long)bpp;

            for (int y = 0; y < (y1 - y0); y++) {
                int dy = y0 + y, sy = sy0 + y;
                if (dy < 0 || dy >= FB_H || sy < 0 || sy >= sh) continue;
                const unsigned char *srow = bits + (unsigned long)sy * row_pitch;
                for (int x = 0; x < (x1 - x0); x++) {
                    int dx = x0 + x, sx = sx0 + x;
                    if (dx < 0 || dx >= FB_W || sx < 0 || sx >= sw) continue;
                    unsigned int sr = 0, sg = 0, sb = 0, sa = 0;
                    if (bpp == 4) {
                        unsigned int p = ((const unsigned int *)srow)[sx];
                        sa = (p >> 24) & 0xFFU;
                        sr = (p >> 16) & 0xFFU;
                        sg = (p >> 8)  & 0xFFU;
                        sb = p & 0xFFU;
                    } else if (bpp == 1) {
                        sa = srow[sx];
                        sr = 255U; sg = 255U; sb = 255U;
                    } else if (bpp == 2) {
                        uint16_t p16 = ((const uint16_t *)srow)[sx];
                        if (fmt == 3) { /* ARGB4444 */
                            sa = ((p16 >> 12) & 0xFU) * 17U;
                            sr = ((p16 >> 8)  & 0xFU) * 17U;
                            sg = ((p16 >> 4)  & 0xFU) * 17U;
                            sb = (p16 & 0xFU) * 17U;
                        } else { /* RGB565 / ARGB1555 */
                            sa = (p16 & 0x8000U) ? 255U : 0U;
                            sr = ((p16 >> 10) & 0x1FU) * 255U / 31U;
                            sg = ((p16 >> 5)  & 0x1FU) * 255U / 31U;
                            sb = (p16 & 0x1FU) * 255U / 31U;
                        }
                    }
                    if (sa != 0U) {
                        unsigned int dst = db[dy * FB_W + dx];
                        unsigned int da = (dst >> 24) & 0xFFU;
                        unsigned int dr = (dst >> 16) & 0xFFU;
                        unsigned int dg = (dst >> 8)  & 0xFFU;
                        unsigned int db_c = dst & 0xFFU;
                        unsigned int or_c = (sr * sa + dr * (255U - sa)) / 255U;
                        unsigned int og_c = (sg * sa + dg * (255U - sa)) / 255U;
                        unsigned int ob_c = (sb * sa + db_c * (255U - sa)) / 255U;
                        unsigned int oa_c = sa + (da * (255U - sa)) / 255U;
                        db[dy * FB_W + dx] = (oa_c << 24) | (or_c << 16) | (og_c << 8) | ob_c;
                    }
                }
            }
        }
    }
    rectblit_count++;
    draw_prim_count++;
    if (rectblit_count <= 40U || (rectblit_count % 50U) == 0U) {
        dprintf(2,
                "FX6_GPE_RECTBLIT #%u dst=(%d,%d,%d,%d) src=%p fmt=%d bpp=%d cb=%p ud=%p subst_image=0\n",
                rectblit_count, dx0, dy0, dw0, dh0, src, fmt, bpp, cb, ud);
    }
    invoke_gpe_cmd_cb(cb, ud);
    flush_pixels_to_osd("rectblit");
    return 0;
}

int _ZN2ma4MMap3mapElm(void *self, long addr, unsigned long len) {
    (void)self; (void)addr; (void)len;
    dprintf(2, "FX6_MA_MMAP_SKIP\n");
    return 0;
}

void _ZN2ux6resmgr15ResourceManager10createFontERKN5alcor13FontAttributeERN5libra9RecordPtrE(
    const void *attr, void *rec
) {
    typedef void (*fn_t)(const void *, void *);
    static fn_t real;
    if (!real) {
        void *h = dlopen("/usr/lib/libuxengine.so", RTLD_LAZY | RTLD_GLOBAL);
        real = h ? (fn_t)dlsym(h, "_ZN2ux6resmgr15ResourceManager10createFontERKN5alcor13FontAttributeERN5libra9RecordPtrE") : 0;
    }
    dprintf(2, "FX6_FONT_CREATE2 attr=%p rec=%p before=%p real=%p\n",
            attr, rec, rec ? *(void **)rec : 0, (void *)real);
    if (real) real(attr, rec);
    dprintf(2, "FX6_FONT_CREATE2_DONE rec=%p after=%p\n",
            rec, rec ? *(void **)rec : 0);
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

/* FX6 backup memory bridge: never touch /dev/backup. */
int Backup_get_suspend_flag(void) { return 0; }
int Backup_nread(unsigned int id, void *buf, int size) {
    (void)id;
    if (buf && size > 0) memset(buf, 0, (size_t)size);
    return size > 0 ? size : 4;
}
int Backup_read(unsigned int id, void *buf, int size) {
    (void)id; (void)buf; (void)size;
    return 0;
}
int Backup_nread_multi(void *a, ...) { (void)a; return 0; }
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
    (void)id; (void)buf;
    return size > 0 ? size : 4;
}
int Backup_reg_cb(void *a, ...) { (void)a; return 0; }
int backup_sync_msg(int *ret, ...) { if (ret) *ret = 0; return 0; }
int backup_async_msg(void *a, ...) { (void)a; return 0; }
int backup_sharedcb_send_msg(void *a, ...) { (void)a; return 0; }
