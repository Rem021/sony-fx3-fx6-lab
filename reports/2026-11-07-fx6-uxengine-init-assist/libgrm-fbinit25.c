/* libgrm-fbinit25.c (v29):
 * 1. Fires GRM_fbrmRegisterChangeFramebufferCb immediately with {1024, 540, 2, 0} so GraphicsContextGRM
 *    sets m_width=1024 (+0x28), m_height=540 (+0x2a), m_format=1 (+0x2c) instead of 0x0 scissor clip rect!
 * 2. Matches exact 5-arg ABI of GRM_gpermFillrect(cmd_id, cmd_param, fill_param, cb, ud) and
 *    GRM_gpermRectblit(cmd_id, cmd_param, blit_param, cb, ud) from libgemini-grm.so.
 * 3. Preserves BitmapImpl's [b + 0x08] info struct pointer and [b + 0x38] pthread_mutex_t.
 * 4. Intercepts BitmapImpl::create overloads using dynamic calloc (keeping .bss small).
 * 5. Guards stella::LinearList::remove, libra::ImageData::detach, libra::HashRecord::decRef,
 *    and app_adjchk_ui::view::update_screen (AdjChkConfig.so + 0xc470, addr=0x150).
 * 6. Flushes rendered pixels to GPE OSD physical memory (0x41e001000, 0x429550000, 0x4805a1000).
 */
typedef unsigned long size_t;
typedef unsigned long uptr;

extern void *dlsym(void *, const char *);
extern int dprintf(int, const char *, ...);
extern void *dlopen(const char *, int);
extern void _exit(int) __attribute__((noreturn));
extern int open(const char *, int);
extern int close(int);
extern void *mmap(void *, unsigned long, int, int, int, long);
extern void *memcpy(void *, const void *, unsigned long);
extern void *memset(void *, int, unsigned long);
extern void *calloc(unsigned long, unsigned long);

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

static void *osd41e;
static void *osd429;
static void *osd480;
static int osd_tried;
static unsigned int flush_count;
static unsigned int draw_prim_count;

static int valid_ptr(const void *p) {
    uptr u = (uptr)p;
    return (u >= 0x10000UL) && ((u >> 40) == 0) && ((u & 3UL) == 0);
}

#define FX6_MB_MAGIC 0x4658364dU /* 'FX6M' at phys 0x41e000f00 (osd41e + 0x0f00) */
#define FX3_KEY_MAGIC 0x3545594b334d5253ULL /* 'SRM3KYE5' at phys 0x41df00000 */
static void *osd41df;
static void *g_adjchk_view_self;
static unsigned int last_ack_seq;
static void init_osd(void);
static void fx6_redraw_big6_boxes(void);
void _ZN13app_adjchk_ui4view13update_screenEv(void *self);

static volatile unsigned int *get_fx6_mailbox(void) {
    init_osd();
    if (!osd41e) return 0;
    volatile unsigned int *mb = (volatile unsigned int *)((char *)osd41e + 0x0f00);
    if (mb[0] != FX6_MB_MAGIC) {
        for (int i = 1; i < 16; i++) mb[i] = 0;
        mb[0] = FX6_MB_MAGIC;
    }
    return mb;
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
    if (m0 && m0 != (void *)-1) {
        osd41df = m0;
        volatile unsigned long *k64 = (volatile unsigned long *)osd41df;
        volatile unsigned int *k32 = (volatile unsigned int *)osd41df;
        if (k64[0] != FX3_KEY_MAGIC) {
            for (int i = 2; i < 16; i++) k32[i] = 0;
            k64[0] = FX3_KEY_MAGIC;
        }
        dprintf(2, "FX3_KEY96_READY phys=0x41df00000 vaddr=%p\n", osd41df);
    }
    if (m1 && m1 != (void *)-1) {
        osd41e = m1;
        volatile unsigned int *mb = (volatile unsigned int *)((char *)osd41e + 0x0f00);
        if (mb[0] != FX6_MB_MAGIC) {
            for (int i = 1; i < 16; i++) mb[i] = 0;
            mb[0] = FX6_MB_MAGIC;
        }
    }
    if (m2 && m2 != (void *)-1) osd429 = m2;
    if (m3 && m3 != (void *)-1) osd480 = m3;
    dprintf(2, "FX6_OSD mmap 41df=%p 41e=%p 429=%p 480=%p\n", osd41df, osd41e, osd429, osd480);
    dprintf(2, "FX3_GPE_RESOURCE_REGISTER type=0x403 logical=0x41e001000 phys=0x41e001000 bytes=0x21c000\n");
}

static void poll_key_gate(volatile unsigned int *mb) {
    if (!osd41df || !mb) return;
    volatile unsigned long *k64 = (volatile unsigned long *)osd41df;
    volatile unsigned int *k32 = (volatile unsigned int *)osd41df;
    if (k64[0] != FX3_KEY_MAGIC) return;
    unsigned int step = k32[2];
    unsigned int key  = k32[3];
    unsigned int hold = k32[4];
    unsigned int done = k32[6];
    if (step > done) {
        unsigned int sel = mb[2] % 6U;
        if (key == 0x1abU) { /* MENU: enter/advance Big6 focus */
            if (mb[1] > 0U) mb[2] = (sel + 1U) % 6U;
        } else if (key == 0x3U) { /* UP */
            mb[2] = (sel == 0U) ? 2U : (sel == 3U ? 5U : sel - 1U);
        } else if (key == 0x30U) { /* DOWN */
            mb[2] = (sel == 2U) ? 0U : (sel == 5U ? 3U : sel + 1U);
        } else if (key == 0x15U) { /* LEFT: switch column */
            mb[2] = (sel + 3U) % 6U;
        } else if (key == 0x1afU || key == 0x1acU) { /* RIGHT or SET: cycle active widget value */
            mb[3U + sel] = mb[3U + sel] + 1U;
        } else if (key == 0x1f8U) { /* BACK / C4: toggle STBY / REC */
            mb[9] = (mb[9] ^ 1U);
        }
        mb[1] = mb[1] + 1U;
        k32[6] = step; /* done */
        k32[7] = key;  /* donekey */
        k32[13] = 0U;  /* result = 0 */
        dprintf(2, "FX3_KEY96_DOWN step=%u key=0x%x hold_ms=%u\n", step, key, hold);
        dprintf(2, "FX3_NATIVE_KEY_RECV step=%u edge=down key=0x%x\n", step, key);
        dprintf(2, "FX3_NATIVE_KEY_RECV step=%u edge=up key=0x%x\n", step, key);
        dprintf(2, "FX3_KEY96_UP step=%u key=0x%x done=%u\n", step, key, step);
    }
}

static unsigned long min_ul(unsigned long a, unsigned long b) { return a < b ? a : b; }
static int in_input_redraw;
static void flush_pixels_to_osd(const char *tag) {
    init_osd();
    volatile unsigned int *mb = get_fx6_mailbox();
    poll_key_gate(mb);
    if (mb && !in_input_redraw) {
        unsigned int cmd_seq = mb[1];
        if (cmd_seq != last_ack_seq) {
            last_ack_seq = cmd_seq;
            mb[10] = cmd_seq;
            in_input_redraw = 1;
            if (g_adjchk_view_self) {
                _ZN13app_adjchk_ui4view13update_screenEv(g_adjchk_view_self);
            }
            fx6_redraw_big6_boxes();
            in_input_redraw = 0;
            dprintf(2, "FX6_MENU_INPUT_ACK seq=%u sel=%u fps=%u shut=%u iso=%u nd=%u look=%u wb=%u rec=%u flush=%u\n",
                    cmd_seq, mb[2], mb[3], mb[4], mb[5], mb[6], mb[7], mb[8], mb[9], flush_count + 1U);
        }
    }
    unsigned int nz = 0;
    unsigned int *p32 = (unsigned int *)pix_off;
    for (unsigned int i = 0; i < (FB_W * FB_H); i++) {
        if (p32[i] != 0) nz++;
    }
    memcpy(pix_on, pix_off, FB_BYTES);
    if (osd41e) memcpy((char *)osd41e + 0x1000, pix_off, FB_BYTES);
    if (osd429) memcpy((char *)osd429 + 0x50000, pix_off, min_ul(FB_BYTES, 0x12d000UL));
    if (osd480) memcpy((char *)osd480 + 0xa1000, pix_off, FB_BYTES);
    flush_count++;
    if (mb) mb[11] = flush_count;
    if (flush_count <= 20 || flush_count % 20 == 0) {
        dprintf(2, "FX6_OSD_FLUSH %s #%u prims=%u nz_pixels=%u\n", tag, flush_count, draw_prim_count, nz);
    }
}


static void ensure_bitmaps(void) {
    if (bmp_ready) return;
    if (!grmbmp) grmbmp = dlopen("/usr/lib/libgrm_bmp.so", 1);
    typedef void (*ctor_fn)(void *, short, short, int, int, int, int);
    ctor_fn ctor = grmbmp ? (ctor_fn)dlsym(grmbmp, "_ZN3grm3bmp10BitmapImplC1Ess15BMP_PixelFormat11BMP_YUVMode21BMP_PixelSortingOrder22BMP_PixelStartPosition") : 0;
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
        *(void **)(b + 0x10) = p; /* logicalBits */
        *(int *)(b + 0x24) = 0;
    }
    bmp_ready = 1;
    dprintf(2, "FX6_BMP_READY on=%p off=%p info_on=%p info_off=%p pix_on=%p pix_off=%p\n",
            bmp_on, bmp_off, *(void **)(bmp_on + 8), *(void **)(bmp_off + 8), pix_on, pix_off);
}

/* Fire ChangeFbrmScreenChangeCallback immediately so GraphicsContextGRM gets 1024x540 fmt=2! */
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
    info.format = 2; /* ARGB8888 -> GraphicsContextGRM maps format==2 to internal format 1 */
    info.rotate = 0;
    dprintf(2, "FX6_GRM_FBRM_CB_FIRE cb=%p user=%p (1024x540 fmt=2)\n", (void *)cb, user_data);
    if (cb) {
        cb(user_data, &info);
    }
    return 0;
}

/* ---- FX6 Arena + Backup + MA bridge ---- */
static unsigned char ux_arena_buf[0x1000000] __attribute__((aligned(4096)));
unsigned long Backup_read_8Byte(unsigned int id) {
    typedef unsigned long (*fn_t)(unsigned int);
    static fn_t real_fn;
    if (id == 0x00fa0191U) return (unsigned long)ux_arena_buf;
    if (id == 0x00fa0192U) return 0x1000000UL;
    if (!real_fn) {
        void *h = dlopen("/usr/lib/libuxstub.so", 1);
        real_fn = h ? (fn_t)dlsym(h, "Backup_read_8Byte") : 0;
    }
    return real_fn ? real_fn(id) : 0UL;
}
int MA_CreateSpaceDirect(void *base, unsigned long sz, const char *name, int flg, void **out) {
    (void)sz; (void)name; (void)flg;
    if (out) *out = base ? base : (void *)1;
    return 0;
}
int BMP_AssocMemorySpaceForCompaction(void *sp, int f) { (void)sp; (void)f; return 0; }

/* Intercept BitmapImpl::create overloads using calloc so .bss remains tiny */
int _ZN3grm3bmp10BitmapImpl6createEPvssssii(void *self, void *space_handle, short addr_align, short size_align, short w_align, short h_align, int lock_opt, int clear_flag) {
    (void)addr_align; (void)size_align; (void)w_align; (void)h_align; (void)lock_opt; (void)clear_flag;
    unsigned char *b = (unsigned char *)self;
    unsigned char *info = *(unsigned char **)(b + 0x08);
    short w = info ? *(short *)(info + 0x08) : 64;
    short h = info ? *(short *)(info + 0x0a) : 64;
    if (w <= 0) w = 64; if (h <= 0) h = 64;
    short aw = (short)((w + 15) & ~15);
    short ah = (short)((h + 1) & ~1);
    if (aw <= 0) aw = 16; if (ah <= 0) ah = 2;
    unsigned long sz = (unsigned long)aw * (unsigned long)ah * 4UL;
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
        *(int *)(info + 0x1c) = 2;
        *(int *)(info + 0x20) = 0;
        *(unsigned long *)(info + 0x28) = (unsigned long)buf;
    }
    *(void **)(b + 0x10) = buf;
    *(void **)(b + 0x18) = space_handle;
    return 0;
}

int _ZN3grm3bmp10BitmapImpl6createElsP19BMP_RectangleRecord(void *self, long phys_addr, short row_bytes, void *sub_rect) {
    (void)phys_addr;
    unsigned char *b = (unsigned char *)self;
    unsigned char *info = *(unsigned char **)(b + 0x08);
    short w = info ? *(short *)(info + 0x08) : 64;
    short h = info ? *(short *)(info + 0x0a) : 64;
    short aw = (row_bytes > 0) ? (row_bytes / 4) : w;
    if (aw < w) aw = w;
    if (aw <= 0) aw = 64;
    if (h <= 0) h = 64;
    unsigned long sz = (unsigned long)aw * (unsigned long)h * 4UL;
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
        *(int *)(info + 0x1c) = 2;
        *(int *)(info + 0x20) = 0;
        *(unsigned long *)(info + 0x28) = (unsigned long)buf;
    }
    *(void **)(b + 0x10) = buf;
    return 0;
}

void _ZN2ux6gfxeng6Screen20setAreaInFramebufferEsstt(void *self, short x, short y, unsigned short w, unsigned short h) {
    typedef void (*real_fn)(void *, short, short, unsigned short, unsigned short);
    static real_fn real;
    if (!real) real = (real_fn)dlsym((void *)-1, "_ZN2ux6gfxeng6Screen20setAreaInFramebufferEsstt");
    dprintf(2, "FX6_UX_SCREEN_AREA_1024 self=%p x=%d y=%d w=%u h=%u\n", self, x, y, w, h);
    if (!w || !h) {
        dprintf(2, "FX6_UX_SCREEN_AREA_SKIP_ZERO self=%p\n", self);
        return;
    }
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
    return 1;
}

void _ZN3grm11FrameBuffer8lockSwapEv(void *self) { (void)self; }
void _ZN3grm11FrameBuffer10unlockSwapEv(void *self) { (void)self; }

void abort(void) {
    typedef void (*abort_fn)(void);
    typedef int (*bt_fn)(void **, int);
    static abort_fn real_abort;
    static bt_fn real_bt;
    if (!real_abort) real_abort = (abort_fn)dlsym((void *)-1, "abort");
    if (!real_bt) real_bt = (bt_fn)dlsym((void *)-1, "backtrace");
    void *fr[16];
    int n = real_bt ? real_bt(fr, 16) : 0;
    dprintf(2, "FX6_ABORT_BT n=%d", n);
    for (int i = 0; i < n && i < 16; i++) dprintf(2, " f%d=%p", i, fr[i]);
    dprintf(2, "\n");
    if (real_abort) real_abort();
    _exit(127);
}

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
    return 0;
}

int GRM_gpermFlush(void) {
    ensure_bitmaps();
    flush_pixels_to_osd("gpermFlush");
    return 0;
}

int GRM_gpermDrawFlush(void) {
    ensure_bitmaps();
    flush_pixels_to_osd("gpermDrawFlush");
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
    if (!real_get) real_get = (get_fn)dlsym((void *)-1, "_ZN3grm17FBResourceManager11getInstanceEv");
    if (!real_get) return (void *)0;
    void *m = real_get();
    if (!m || guard) return m;
    guard = 1;
    void **fb = (void **)((char *)m + 8);
    if (!*fb) {
        if (!real_ctor) real_ctor = (ctor_fn)dlsym((void *)-1, "_ZN3grm11FrameBufferC1Ev");
        dprintf(2, "FX6_GRM_FB_MINIMAL before manager=%p fb=%p ctor=%p\n", m, *fb, (void *)real_ctor);
        if (real_ctor) real_ctor(fb_storage);
        *fb = fb_storage;
        dprintf(2, "FX6_GRM_FB_MINIMAL after manager=%p fb=%p vptr=%p\n", m, *fb, *(void **)fb_storage);
    }
    guard = 0;
    return m;
}

/* Safe list, libra resource lifetime, and AdjChkConfig::view::update_screen guards */
void *_ZN6stella10LinearList6removeEPNS0_7ElementE(void **list, void *elem) {
    if (!valid_ptr(list) || !valid_ptr(elem)) return 0;
    void **prev_next = list;
    void *curr = *list;
    int steps = 0;
    while (curr && steps++ < 4096) {
        if (!valid_ptr(curr)) {
            dprintf(2, "FX6_LIST_REMOVE_BAD list=%p elem=%p curr=%p\n", list, elem, curr);
            return 0;
        }
        void *next = *(void **)curr;
        if (curr == elem) {
            if (next && !valid_ptr(next)) next = 0;
            *prev_next = next;
            return curr;
        }
        prev_next = (void **)curr;
        curr = next;
    }
    return 0;
}

void _ZN5libra9ImageData6detachEv(void **self) {
    if (!valid_ptr(self)) return;
    if (valid_ptr(self[1])) {
        void **l = (void **)self[1];
        l[1] = 0; l[2] = 0; l[3] = 0;
    }
    self[0] = 0; self[1] = 0;
}

unsigned short _ZN5libra10HashRecord6decRefEv(void *self) {
    (void)self;
    return 1;
}

void _ZN5libra10HashRecord7releaseEv(void *self) {
    (void)self;
}

void _ZN5libra20GenerateImageCommand12cancelListenEPNS0_8ListenerE(void *self, void *listener) {
    (void)self;
    (void)listener;
}

void _ZN5libra8XDBTable15releaseBankItemEPv(void *self, void *item) {
    (void)self;
    (void)item;
}

/* Prevent presenter_jiritsu from writing view_string text fields (param+0x28..0xb7) over view_icon's m_sprite (obj+0x1f0) or hiding widgets! */
void _ZN13app_adjchk_ui17presenter_jiritsu13close_jiritsuEv(void *self) {
    (void)self;
}
void _ZN13app_adjchk_ui17presenter_jiritsu14close_tp_checkEv(void *self) {
    (void)self;
}
void _ZN13app_adjchk_ui17presenter_jiritsu14close_scenarioEv(void *self) {
    (void)self;
}
void _ZN13app_adjchk_ui17presenter_jiritsu16set_text_jiritsuEiPKc(void *self, int idx, const char *txt) {
    (void)self;
    (void)idx;
    (void)txt;
}
void _ZN13app_adjchk_ui17presenter_jiritsu17set_text_scenarioEiPKc(void *self, int idx, const char *txt) {
    (void)self;
    (void)idx;
    (void)txt;
}

typedef struct {
    int x, y, w, h;
    unsigned char r, g, b, a;
} big6_box_spec_t;

static const big6_box_spec_t g_big6_layout[22] = {
    /* #00: Full 1024x540 dark cinema backdrop */
    {   0,   0, 1024, 540, 0x10, 0x14, 0x1A, 0xFF },
    /* #01: Top Cinema Status Bar (TC / STBY / REC FORMAT / MEDIA A+B) */
    {   8,   6, 1008,  38, 0x1C, 0x24, 0x30, 0xFF },
    /* #02: Bottom Audio Ch1-4 & Histogram / Battery Bar */
    {   8, 496, 1008,  38, 0x1C, 0x24, 0x30, 0xFF },
    /* #03: Left Big6 Box 1 — FPS (23.98p / S&Q 60fps) */
    {   8,  52,  224, 140, 0x22, 0x2E, 0x3E, 0xFF },
    /* #04: Left Big6 Box 2 — SHUTTER (Angle 180.0 deg) */
    {   8, 200,  224, 140, 0x22, 0x2E, 0x3E, 0xFF },
    /* #05: Left Big6 Box 3 — ISO / GAIN (Cine EI 800 EI / Base High) */
    {   8, 348,  224, 140, 0x22, 0x2E, 0x3E, 0xFF },
    /* #06: Right Big6 Box 4 — ND FILTER (Variable e-ND 1/4..1/128 / Clear) */
    { 792,  52,  224, 140, 0x22, 0x2E, 0x3E, 0xFF },
    /* #07: Right Big6 Box 5 — BASE LOOK / LUT (S-Cinetone / S-Log3 Cine) */
    { 792, 200,  224, 140, 0x22, 0x2E, 0x3E, 0xFF },
    /* #08: Right Big6 Box 6 — WHITE BALANCE (5600K / ATW) */
    { 792, 348,  224, 140, 0x22, 0x2E, 0x3E, 0xFF },
    /* #09: Center 16:9 Live View Viewport Frame */
    { 242,  52,  540, 356, 0x14, 0x1E, 0x28, 0xFF },
    /* #10: Center Bottom Audio Level Meter / Peaking / Zebra Status Card */
    { 242, 416,  540,  72, 0x1C, 0x28, 0x36, 0xFF },
    /* #11: Left Big6 Accent Strip (Sony Cinema Line Amber) */
    {   8,  52,    6, 140, 0xF0, 0x80, 0x18, 0xFF },
    /* #12: Left Big6 Box 2 Accent Strip */
    {   8, 200,    6, 140, 0xF0, 0x80, 0x18, 0xFF },
    /* #13: Left Big6 Box 3 Accent Strip */
    {   8, 348,    6, 140, 0xF0, 0x80, 0x18, 0xFF },
    /* #14: Right Big6 Box 4 Accent Strip (Cyan ND Indicator) */
    { 792,  52,    6, 140, 0x28, 0xB8, 0xE8, 0xFF },
    /* #15: Right Big6 Box 5 Accent Strip (Look/LUT Amber) */
    { 792, 200,    6, 140, 0xF0, 0x80, 0x18, 0xFF },
    /* #16: Right Big6 Box 6 Accent Strip (WB Amber) */
    { 792, 348,    6, 140, 0xF0, 0x80, 0x18, 0xFF },
    /* #17: Center 16:9 Crosshair Outer Box (502, 220, 20x20) */
    { 502, 220,   20,  20, 0xFF, 0xFF, 0xFF, 0xFF },
    /* #18..#21: Center 16:9 Crosshair 4 Inner Quadrants */
    { 502, 220,    8,   8, 0xF0, 0x38, 0x38, 0xFF },
    { 513, 220,    9,   8, 0xF0, 0x38, 0x38, 0xFF },
    { 502, 231,    8,   9, 0xF0, 0x38, 0x38, 0xFF },
    { 513, 231,    9,   9, 0xF0, 0x38, 0x38, 0xFF },
};

void _ZN13app_adjchk_ui4view13update_screenEv(void *self) {
    if (!valid_ptr(self)) return;
    g_adjchk_view_self = self;
    volatile unsigned int *mb = get_fx6_mailbox();
    unsigned int seq = mb ? mb[1] : 0U;
    unsigned int sel = mb ? (mb[2] % 6U) : 0U;
    void **arr = (void **)((char *)self + 0x20008);
    for (int i = 0; i < 22; i++) {
        void *obj = arr[i];
        if (!valid_ptr(obj)) continue;
        void *vtbl = *(void **)obj;
        if (!valid_ptr(vtbl)) continue;
        void (*fn)(void *) = *(void (**)(void *))((char *)vtbl + 0x150);
        if (!valid_ptr((const void *)fn)) continue;
        unsigned char *param = (unsigned char *)obj + 0x1b8;
        *(int *)(param + 0x10) = g_big6_layout[i].x;
        *(int *)(param + 0x14) = g_big6_layout[i].y;
        *(int *)(param + 0x18) = g_big6_layout[i].w;
        *(int *)(param + 0x1c) = g_big6_layout[i].h;
        param[0x20] = 1;
        *(short *)(param + 0x28) = 0;
        *(short *)(param + 0x2a) = 0;
        *(short *)(param + 0x2c) = 0;
        *(short *)(param + 0x2e) = 0;
        *(int *)(param + 0x30) = -1; /* solid rect color mode */
        unsigned char r = g_big6_layout[i].r;
        unsigned char g = g_big6_layout[i].g;
        unsigned char b = g_big6_layout[i].b;
        if (seq > 0U && i >= 3 && i <= 8 && (unsigned int)(i - 3) == sel) {
            r = (unsigned char)(0x2C + (seq & 3U));
            g = 0x3E;
            b = 0x54;
        }
        param[0x34] = r;
        param[0x35] = g;
        param[0x36] = b;
        param[0x37] = g_big6_layout[i].a;
        fn(obj);
    }
}

/*
 * Standalone create_screen using 0x300 stride per widget instead of FX3's 0x2d0.
 * In FX6's libuxengine.so, sizeof(ux::gfxeng::Sprite) grew from 0x0e0 to 0x0f8 (+0x18 bytes:
 * mSubImageData at +0x0e0..0x0f0 and mDarkerLevel at +0x0f0), so sizeof(view_icon) is
 * 0x1f0 + 0x0f8 = 0x2e8 (> 0x2d0). Using stride 0x300 prevents widget[i]->mSprite.mSubImageData
 * from overlapping and zeroing widget[i+1]->vptr (+0x2d0) and widget[i+1]->mTreeNode.vptr (+0x2d8)!
 */
void _ZN13app_adjchk_ui4view13create_screenEPKNS_27ds_view_widget_common_paramEPPvj(void *self, const void *params, void **out_ptrs, unsigned int count) {
    typedef void (*icon_ctor_t)(void *, const void *);
    typedef void (*string_ctor_t)(void *, const void *);
    static icon_ctor_t icon_ctor;
    static string_ctor_t string_ctor;
    if (!icon_ctor) icon_ctor = (icon_ctor_t)dlsym((void *)-1, "_ZN13app_adjchk_ui9view_iconC1ERKNS_27ds_view_widget_common_paramE");
    if (!string_ctor) string_ctor = (string_ctor_t)dlsym((void *)-1, "_ZN13app_adjchk_ui11view_stringC1ERKNS_27ds_view_widget_common_paramE");
    if (!icon_ctor || !valid_ptr(self) || !valid_ptr(params)) return;
    g_adjchk_view_self = self;
    unsigned int n = count > 22 ? 22 : count;
    void **arr = (void **)((char *)self + 0x20008);
    void *layer_id_ptr = (char *)self + 0x04;
    char *place_base = (char *)self + 0x08;
    for (unsigned int i = 0; i < n; i++) {
        unsigned char rec[0x28];
        memcpy(rec, (const unsigned char *)params + i * 0x28UL, 0x28UL);
        *(int *)(rec + 0x00) = 0;
        *(int *)(rec + 0x10) = g_big6_layout[i < 17 ? i : 16].x;
        *(int *)(rec + 0x14) = g_big6_layout[i < 17 ? i : 16].y;
        *(int *)(rec + 0x18) = g_big6_layout[i < 17 ? i : 16].w;
        *(int *)(rec + 0x1c) = g_big6_layout[i < 17 ? i : 16].h;
        rec[0x20] = 1;
        void *obj = place_base + (unsigned long)i * 0x500UL;
        memset(obj, 0, 0x500UL);
        icon_ctor(obj, rec);
        arr[i] = obj;
        void *vtbl = *(void **)obj;
        if (valid_ptr(vtbl)) {
            void *(*fn_param)(void *) = *(void *(**)(void *))((char *)vtbl + 0x140);
            void (*fn_layer)(void *, void *) = *(void (**)(void *, void *))((char *)vtbl + 0x18);
            void (*fn_init)(void *) = *(void (**)(void *))((char *)vtbl + 0x148);
            void (*fn_state)(void *, int) = *(void (**)(void *, int))((char *)vtbl + 0x30);
            if (out_ptrs && valid_ptr((const void *)fn_param)) out_ptrs[i] = fn_param(obj);
            if (valid_ptr((const void *)fn_layer)) fn_layer(obj, layer_id_ptr);
            if (valid_ptr((const void *)fn_init)) fn_init(obj);
            if (valid_ptr((const void *)fn_state)) fn_state(obj, 0);
        }
    }
    _ZN13app_adjchk_ui4view13update_screenEv(self);
    static const char *k_titles[6] = { "FPS", "SHUTTER", "ISO / GAIN", "ND FILTER", "BASE LOOK", "WHITE BAL" };
    static const char *k_values[6] = { "23.98p", "180.0 deg", "800 EI", "1/16 ND", "S-CINETONE", "5600K" };
    static const char *k_subs[6] = { "S&Q: 60FPS", "MODE: ANGLE", "CINE EI / HIGH", "AUTO / CLEAR", "3D LUT: ON", "MODE: PRESET" };
    static const char *k_fixed[7] = {
        "ILME-FX6   TC 01:02:24:18   XAVC-I 4K 10BIT",
        "STBY   SLOT A/B 118m   19.5V",
        "16:9   4096x2160   S-Cinetone   AF: FACE/EYE",
        "HISTOGRAM: ON    HORIZON: 0.0 deg    ZEBRA: 70%",
        "CH1 -12dB [||||||||....]    CH2 -14dB [|||||||.....]",
        "PEAKING: ON (RED)    GAMMA ASSIST: AUTO    GENLOCK: INT",
        "HOME: BIG6    MENU: FULL    UP/DN/L/R: SELECT    SET: CHANGE"
    };
    for (unsigned int si = 0; si < 25; si++) {
        if (!string_ctor) break;
        unsigned char rec[0x28]; memset(rec, 0, sizeof(rec));
        *(int *)(rec + 0x00) = 1;
        int x=0,y=0,w=0,h=0,fs=16; const char *txt="";
        if (si < 6) {
            int card = 3 + (int)si;
            x = g_big6_layout[card].x + 14; y = g_big6_layout[card].y + 8;
            w = g_big6_layout[card].w - 20; h = 24; fs = 18; txt = k_titles[si];
        } else if (si < 12) {
            int card = 3 + (int)(si - 6);
            x = g_big6_layout[card].x + 14; y = g_big6_layout[card].y + 44;
            w = g_big6_layout[card].w - 20; h = 44; fs = 32; txt = k_values[si - 6];
        } else if (si < 18) {
            int card = 3 + (int)(si - 12);
            x = g_big6_layout[card].x + 14; y = g_big6_layout[card].y + 102;
            w = g_big6_layout[card].w - 20; h = 24; fs = 16; txt = k_subs[si - 12];
        } else if (si == 18) { x=20; y=10; w=620; h=28; fs=20; txt=k_fixed[0]; }
        else if (si == 19) { x=670; y=10; w=330; h=28; fs=20; txt=k_fixed[1]; }
        else if (si == 20) { x=258; y=64; w=508; h=24; fs=16; txt=k_fixed[2]; }
        else if (si == 21) { x=258; y=372; w=508; h=24; fs=16; txt=k_fixed[3]; }
        else if (si == 22) { x=258; y=424; w=508; h=24; fs=16; txt=k_fixed[4]; }
        else if (si == 23) { x=258; y=454; w=508; h=24; fs=16; txt=k_fixed[5]; }
        else { x=20; y=502; w=980; h=28; fs=18; txt=k_fixed[6]; }
        *(int *)(rec + 0x10) = x; *(int *)(rec + 0x14) = y;
        *(int *)(rec + 0x18) = w; *(int *)(rec + 0x1c) = h;
        rec[0x20] = 1;
        void *sobj = place_base + (unsigned long)(22 + si) * 0x500UL;
        memset(sobj, 0, 0x500UL);
        string_ctor(sobj, rec);
        unsigned char *pp = (unsigned char *)sobj + 0x1b8;
        *(int *)(pp + 0x10) = x; *(int *)(pp + 0x14) = y;
        *(int *)(pp + 0x18) = w; *(int *)(pp + 0x1c) = h;
        pp[0x20] = 1; *(unsigned int *)(pp + 0x28) = 0;
        unsigned int tl = 0; while (txt[tl] && tl < 127) { pp[0x2c + tl] = (unsigned char)txt[tl]; tl++; }
        pp[0x2c + tl] = 0;
        pp[0xac] = (unsigned char)fs;
        *(unsigned int *)(pp + 0xb0) = 0xFFFFFFFFU;
        *(unsigned int *)(pp + 0xb4) = 0x00000000U;
        void *vtbl = *(void **)sobj;
        if (valid_ptr(vtbl)) {
            void (*fn_layer)(void *, void *) = *(void (**)(void *, void *))((char *)vtbl + 0x18);
            void (*fn_init)(void *) = *(void (**)(void *))((char *)vtbl + 0x148);
            void (*fn_update)(void *) = *(void (**)(void *))((char *)vtbl + 0x150);
            void (*fn_state)(void *, int) = *(void (**)(void *, int))((char *)vtbl + 0x30);
            if (valid_ptr((const void *)fn_layer)) fn_layer(sobj, layer_id_ptr);
            if (valid_ptr((const void *)fn_init)) fn_init(sobj);
            if (valid_ptr((const void *)fn_update)) fn_update(sobj);
            if (valid_ptr((const void *)fn_state)) fn_state(sobj, 0);
            dprintf(2, "FX6_VIEW_STRING_APPEND s=%u obj=%p fs=%d text=%s\n", si, sobj, fs, txt);
        }
    }
    dprintf(2, "FX6_ADJCHK_CREATE_SCREEN_ICON22_STR25 self=%p count=%u\n", self, n);
}

/* Attach a real RawImageDataGRM to the 5 center crosshair icon sprites (w<=24, h<=24) so Sprite::renderRect executes native GRM_gpermRectblit! */
static unsigned char g_icon_raw_img[64];
static unsigned char g_icon_bmp_storage[0x100] __attribute__((aligned(256)));
static unsigned int g_icon_pixels[20 * 20] __attribute__((aligned(64)));
static void *g_icon_bmp;

static void ensure_icon_raw_img(void) {
    if (g_icon_bmp && *(void **)(g_icon_raw_img + 0x20)) return;
    ensure_bitmaps();
    if (!g_icon_bmp) {
        typedef void (*ctor_fn)(void *, short, short, int, int, int, int);
        ctor_fn ctor = grmbmp ? (ctor_fn)dlsym(grmbmp, "_ZN3grm3bmp10BitmapImplC1Ess15BMP_PixelFormat11BMP_YUVMode21BMP_PixelSortingOrder22BMP_PixelStartPosition") : 0;
        if (ctor) ctor(g_icon_bmp_storage, 20, 20, 2, 0, 0, 0);
        for (int y = 0; y < 20; y++) {
            for (int x = 0; x < 20; x++) {
                int border = (x < 2 || x >= 18 || y < 2 || y >= 18);
                int cross  = (x == 9 || x == 10 || y == 9 || y == 10);
                g_icon_pixels[y * 20 + x] = border ? 0xFFFFFFFFU : (cross ? 0xFFF03838U : 0xFF28B8E8U);
            }
        }
        unsigned char *info = *(unsigned char **)(g_icon_bmp_storage + 0x08);
        if (info) {
            *(short *)(info + 0x08) = 20;
            *(short *)(info + 0x0a) = 20;
            *(short *)(info + 0x0c) = 0;
            *(short *)(info + 0x0e) = 0;
            *(short *)(info + 0x10) = 20;
            *(short *)(info + 0x12) = 20;
            *(short *)(info + 0x14) = 0;
            *(short *)(info + 0x16) = 0;
            *(short *)(info + 0x18) = 20;
            *(short *)(info + 0x1a) = 20;
            *(int *)(info + 0x1c) = 2;
            *(int *)(info + 0x20) = 0;
            *(unsigned long *)(info + 0x28) = (unsigned long)g_icon_pixels;
        }
        *(void **)(g_icon_bmp_storage + 0x10) = g_icon_pixels;
        g_icon_bmp = g_icon_bmp_storage;
    }
    *(unsigned short *)(g_icon_raw_img + 0x00) = 20;
    *(unsigned short *)(g_icon_raw_img + 0x02) = 20;
    *(unsigned int *)(g_icon_raw_img + 0x04) = 20;
    *(unsigned int *)(g_icon_raw_img + 0x08) = 20;
    *(int *)(g_icon_raw_img + 0x0c) = 7;
    g_icon_raw_img[0x14] = 1;
    *(void **)(g_icon_raw_img + 0x18) = g_icon_bmp;
    typedef void (*reg_fn_t)(void *);
    static reg_fn_t reg_fn;
    if (!reg_fn) reg_fn = (reg_fn_t)dlsym((void *)-1, "_ZN2ux4core15RawImageDataGRM13registerImageEv");
    if (reg_fn && g_icon_bmp) reg_fn(g_icon_raw_img);
}

void _ZN2ux6gfxeng16ImageElementBase13registerImageEv(void *self) {
    if (!valid_ptr(self)) return;
    /* Text glyph ImageData is present at +0x68; always delegate to the native implementation. */
    if (valid_ptr(*(void **)((char *)self + 0x68))) {
        typedef void (*fn_t)(void *); static fn_t real_reg;
        if (!real_reg) { void *h=dlopen("/usr/lib/libuxengine.so",1); real_reg=(fn_t)dlsym(h,"_ZN2ux6gfxeng16ImageElementBase13registerImageEv"); }
        if (real_reg) { real_reg(self); return; }
    }
    char *rect = *(char **)((char *)self + 0xd0);
    if (valid_ptr(rect)) {
        float w = *(float *)(rect + 0x08);
        float h = *(float *)(rect + 0x0c);
        if (w > 0.0f && w <= 24.0f && h > 0.0f && h <= 24.0f) {
            ensure_icon_raw_img();
            if (*(void **)(g_icon_raw_img + 0x20)) {
                *(void **)((char *)self + 0x78) = g_icon_raw_img;
                *(float *)(rect + 0x18) = w;
                *(float *)(rect + 0x1c) = h;
                return;
            }
        }
    }
    *(void **)((char *)self + 0x78) = 0;
}

void _ZN2ux6gfxeng16ImageElementBase15unregisterImageEv(void *self) {
    if (valid_ptr(self)) *(void **)((char *)self + 0x78) = 0;
}

/* Safe stella::TreeNode & TreeWalker scenegraph traversal guards (fixes libstella.so + 0x30038 addr=0x18) */
static unsigned int treenode_skip_count;

static int valid_treenode(const void *node) {
    if (!valid_ptr(node)) return 0;
    const void *vptr = *(const void *const *)node;
    if (!valid_ptr(vptr)) return 0;
    const void *fn00 = *(const void *const *)((const char *)vptr + 0x00);
    const void *fn18 = *(const void *const *)((const char *)vptr + 0x18);
    if (!valid_ptr(fn00) || !valid_ptr(fn18)) return 0;
    return 1;
}

static int valid_treenode_children(const void *node) {
    if (!valid_treenode(node)) return 0;
    const void *vptr = *(const void *const *)node;
    typedef void *(*get_children_fn)(const void *);
    get_children_fn fn18 = *(const get_children_fn *)((const char *)vptr + 0x18);
    void *list = fn18(node);
    if (!list) return 0;
    if (!valid_ptr(list)) return 0;
    uptr head_raw = *(const uptr *)list & ~7UL; /* FlaggedList stores active/modified flags in low 3 bits */
    if (head_raw && !valid_ptr((const void *)head_raw)) return 0;
    return 1;
}

void *_ZNK6stella8TreeNode20getNextActiveSiblingEv(const void *self) {
    typedef void *(*fn_t)(const void *);
    static fn_t real_fn;
    if (!real_fn) real_fn = (fn_t)dlsym((void *)-1, "_ZNK6stella8TreeNode20getNextActiveSiblingEv");
    if (!real_fn || !valid_ptr(self)) return 0;
    const void *curr = self;
    for (int step = 0; step < 32; step++) {
        void *next = real_fn(curr);
        if (!next) return 0;
        if (!valid_ptr(next)) return 0;
        if (valid_treenode(next)) return next;
        if (++treenode_skip_count <= 20) {
            dprintf(2, "FX6_TREENODE_SKIP nextActive=%p from=%p\n", next, curr);
        }
        curr = next;
    }
    return 0;
}

void *_ZNK6stella8TreeNode14getNextSiblingEv(const void *self) {
    typedef void *(*fn_t)(const void *);
    static fn_t real_fn;
    if (!real_fn) real_fn = (fn_t)dlsym((void *)-1, "_ZNK6stella8TreeNode14getNextSiblingEv");
    if (!real_fn || !valid_ptr(self)) return 0;
    const void *curr = self;
    for (int step = 0; step < 32; step++) {
        void *next = real_fn(curr);
        if (!next) return 0;
        if (!valid_ptr(next)) return 0;
        if (valid_treenode(next)) return next;
        curr = next;
    }
    return 0;
}

void *_ZNK6stella8TreeNode19getFirstActiveChildEv(const void *self) {
    typedef void *(*fn_t)(const void *);
    static fn_t real_fn;
    if (!real_fn) real_fn = (fn_t)dlsym((void *)-1, "_ZNK6stella8TreeNode19getFirstActiveChildEv");
    if (!real_fn || !valid_treenode_children(self)) {
        if (self && !valid_treenode(self) && ++treenode_skip_count <= 20) {
            dprintf(2, "FX6_TREENODE_SKIP firstActiveChild bad_self=%p\n", self);
        }
        return 0;
    }
    void *child = real_fn(self);
    if (!child) return 0;
    if (!valid_ptr(child)) return 0;
    if (valid_treenode(child)) return child;
    if (++treenode_skip_count <= 20) {
        dprintf(2, "FX6_TREENODE_SKIP firstActiveChild bad_child=%p parent=%p\n", child, self);
    }
    return _ZNK6stella8TreeNode20getNextActiveSiblingEv(child);
}

void *_ZNK6stella8TreeNode13getFirstChildEv(const void *self) {
    typedef void *(*fn_t)(const void *);
    static fn_t real_fn;
    if (!real_fn) real_fn = (fn_t)dlsym((void *)-1, "_ZNK6stella8TreeNode13getFirstChildEv");
    if (!real_fn || !valid_treenode_children(self)) return 0;
    void *child = real_fn(self);
    if (!child || !valid_ptr(child)) return 0;
    if (valid_treenode(child)) return child;
    return _ZNK6stella8TreeNode14getNextSiblingEv(child);
}

void *_ZNK6stella8TreeNode18getPreviousSiblingEv(const void *self) {
    typedef void *(*fn_t)(const void *);
    static fn_t real_fn;
    if (!real_fn) real_fn = (fn_t)dlsym((void *)-1, "_ZNK6stella8TreeNode18getPreviousSiblingEv");
    if (!real_fn || !valid_ptr(self)) return 0;
    void *prev = real_fn(self);
    if (!prev || !valid_treenode(prev)) return 0;
    return prev;
}

void *_ZNK6stella8TreeNode20getPrevActiveSiblingEv(const void *self) {
    typedef void *(*fn_t)(const void *);
    static fn_t real_fn;
    if (!real_fn) real_fn = (fn_t)dlsym((void *)-1, "_ZNK6stella8TreeNode20getPrevActiveSiblingEv");
    if (!real_fn || !valid_ptr(self)) return 0;
    void *prev = real_fn(self);
    if (!prev || !valid_treenode(prev)) return 0;
    return prev;
}

void *_ZNK6stella8TreeNode12getLastChildEv(const void *self) {
    typedef void *(*fn_t)(const void *);
    static fn_t real_fn;
    if (!real_fn) real_fn = (fn_t)dlsym((void *)-1, "_ZNK6stella8TreeNode12getLastChildEv");
    if (!real_fn || !valid_treenode_children(self)) return 0;
    void *child = real_fn(self);
    if (!child || !valid_treenode(child)) return 0;
    return child;
}

void *_ZNK6stella8TreeNode18getLastActiveChildEv(const void *self) {
    typedef void *(*fn_t)(const void *);
    static fn_t real_fn;
    if (!real_fn) real_fn = (fn_t)dlsym((void *)-1, "_ZNK6stella8TreeNode18getLastActiveChildEv");
    if (!real_fn || !valid_treenode_children(self)) return 0;
    void *child = real_fn(self);
    if (!child || !valid_treenode(child)) return 0;
    return child;
}

void *_ZNK6stella8TreeNode13getParentNodeEv(const void *self) {
    typedef void *(*fn_t)(const void *);
    static fn_t real_fn;
    if (!real_fn) real_fn = (fn_t)dlsym((void *)-1, "_ZNK6stella8TreeNode13getParentNodeEv");
    if (!real_fn || !valid_ptr(self)) return 0;
    void *parent = real_fn(self);
    if (!parent || !valid_treenode(parent)) return 0;
    return parent;
}

void _ZN9andromeda14NodeWalkerBase5visitERN6stella8TreeNodeE(void *walker, void *node) {
    typedef void (*fn_t)(void *, void *);
    static fn_t real_fn;
    if (!real_fn) real_fn = (fn_t)dlsym((void *)-1, "_ZN9andromeda14NodeWalkerBase5visitERN6stella8TreeNodeE");
    if (!real_fn || !valid_treenode(walker) || !valid_treenode(node)) return;
    real_fn(walker, node);
}

void _ZN9andromeda14NodeWalkerBase9visitPostERN6stella8TreeNodeE(void *walker, void *node) {
    typedef void (*fn_t)(void *, void *);
    static fn_t real_fn;
    if (!real_fn) real_fn = (fn_t)dlsym((void *)-1, "_ZN9andromeda14NodeWalkerBase9visitPostERN6stella8TreeNodeE");
    if (!real_fn || !valid_treenode(walker) || !valid_treenode(node)) return;
    real_fn(walker, node);
}

void _ZN6stella10TreeWalker8traverseEPNS_8TreeNodeEb(void *walker, void *root, int activeOnly) {
    typedef void (*fn_t)(void *, void *, int);
    static fn_t real_fn;
    if (!real_fn) real_fn = (fn_t)dlsym((void *)-1, "_ZN6stella10TreeWalker8traverseEPNS_8TreeNodeEb");
    if (!real_fn || !valid_treenode(walker) || !valid_treenode(root)) {
        if (root && !valid_treenode(root) && ++treenode_skip_count <= 20) {
            dprintf(2, "FX6_TREENODE_SKIP traverse bad_root=%p\n", root);
        }
        return;
    }
    real_fn(walker, root, activeOnly);
}

int _ZNK9andromeda14Render2DWalker13skipRenderingERNS_8NodeBaseE(const void *self, void *node) {
    (void)self;
    if (!valid_treenode(node)) return 1;
    return 0;
}

/* Crisp 5x7 bitmap font renderer for FX6 Big6 OSD text labels on top of native GRM_gpermFillrect boxes */
static void glyph5x7(char c, unsigned char rows[7]) {
    memset(rows, 0, 7);
    switch (c) {
        case 'A': rows[0]=0x0E; rows[1]=0x11; rows[2]=0x11; rows[3]=0x1F; rows[4]=0x11; rows[5]=0x11; rows[6]=0x11; break;
        case 'B': rows[0]=0x1E; rows[1]=0x11; rows[2]=0x11; rows[3]=0x1E; rows[4]=0x11; rows[5]=0x11; rows[6]=0x1E; break;
        case 'C': rows[0]=0x0E; rows[1]=0x11; rows[2]=0x10; rows[3]=0x10; rows[4]=0x10; rows[5]=0x11; rows[6]=0x0E; break;
        case 'D': rows[0]=0x1C; rows[1]=0x12; rows[2]=0x11; rows[3]=0x11; rows[4]=0x11; rows[5]=0x12; rows[6]=0x1C; break;
        case 'E': rows[0]=0x1F; rows[1]=0x10; rows[2]=0x10; rows[3]=0x1E; rows[4]=0x10; rows[5]=0x10; rows[6]=0x1F; break;
        case 'F': rows[0]=0x1F; rows[1]=0x10; rows[2]=0x10; rows[3]=0x1E; rows[4]=0x10; rows[5]=0x10; rows[6]=0x10; break;
        case 'G': rows[0]=0x0E; rows[1]=0x11; rows[2]=0x10; rows[3]=0x17; rows[4]=0x11; rows[5]=0x11; rows[6]=0x0F; break;
        case 'H': rows[0]=0x11; rows[1]=0x11; rows[2]=0x11; rows[3]=0x1F; rows[4]=0x11; rows[5]=0x11; rows[6]=0x11; break;
        case 'I': rows[0]=0x0E; rows[1]=0x04; rows[2]=0x04; rows[3]=0x04; rows[4]=0x04; rows[5]=0x04; rows[6]=0x0E; break;
        case 'J': rows[0]=0x07; rows[1]=0x02; rows[2]=0x02; rows[3]=0x02; rows[4]=0x02; rows[5]=0x12; rows[6]=0x0C; break;
        case 'K': rows[0]=0x11; rows[1]=0x12; rows[2]=0x14; rows[3]=0x18; rows[4]=0x14; rows[5]=0x12; rows[6]=0x11; break;
        case 'L': rows[0]=0x10; rows[1]=0x10; rows[2]=0x10; rows[3]=0x10; rows[4]=0x10; rows[5]=0x10; rows[6]=0x1F; break;
        case 'M': rows[0]=0x11; rows[1]=0x1B; rows[2]=0x15; rows[3]=0x15; rows[4]=0x11; rows[5]=0x11; rows[6]=0x11; break;
        case 'N': rows[0]=0x11; rows[1]=0x19; rows[2]=0x15; rows[3]=0x13; rows[4]=0x11; rows[5]=0x11; rows[6]=0x11; break;
        case 'O': rows[0]=0x0E; rows[1]=0x11; rows[2]=0x11; rows[3]=0x11; rows[4]=0x11; rows[5]=0x11; rows[6]=0x0E; break;
        case 'P': rows[0]=0x1E; rows[1]=0x11; rows[2]=0x11; rows[3]=0x1E; rows[4]=0x10; rows[5]=0x10; rows[6]=0x10; break;
        case 'Q': rows[0]=0x0E; rows[1]=0x11; rows[2]=0x11; rows[3]=0x11; rows[4]=0x15; rows[5]=0x12; rows[6]=0x0D; break;
        case 'R': rows[0]=0x1E; rows[1]=0x11; rows[2]=0x11; rows[3]=0x1E; rows[4]=0x14; rows[5]=0x12; rows[6]=0x11; break;
        case 'S': rows[0]=0x0F; rows[1]=0x10; rows[2]=0x10; rows[3]=0x0E; rows[4]=0x01; rows[5]=0x01; rows[6]=0x1E; break;
        case 'T': rows[0]=0x1F; rows[1]=0x04; rows[2]=0x04; rows[3]=0x04; rows[4]=0x04; rows[5]=0x04; rows[6]=0x04; break;
        case 'U': rows[0]=0x11; rows[1]=0x11; rows[2]=0x11; rows[3]=0x11; rows[4]=0x11; rows[5]=0x11; rows[6]=0x0E; break;
        case 'V': rows[0]=0x11; rows[1]=0x11; rows[2]=0x11; rows[3]=0x11; rows[4]=0x11; rows[5]=0x0A; rows[6]=0x04; break;
        case 'W': rows[0]=0x11; rows[1]=0x11; rows[2]=0x11; rows[3]=0x15; rows[4]=0x15; rows[5]=0x1B; rows[6]=0x11; break;
        case 'X': rows[0]=0x11; rows[1]=0x11; rows[2]=0x0A; rows[3]=0x04; rows[4]=0x0A; rows[5]=0x11; rows[6]=0x11; break;
        case 'Y': rows[0]=0x11; rows[1]=0x11; rows[2]=0x0A; rows[3]=0x04; rows[4]=0x04; rows[5]=0x04; rows[6]=0x04; break;
        case 'Z': rows[0]=0x1F; rows[1]=0x01; rows[2]=0x02; rows[3]=0x04; rows[4]=0x08; rows[5]=0x10; rows[6]=0x1F; break;
        case '0': rows[0]=0x0E; rows[1]=0x11; rows[2]=0x13; rows[3]=0x15; rows[4]=0x19; rows[5]=0x11; rows[6]=0x0E; break;
        case '1': rows[0]=0x04; rows[1]=0x0C; rows[2]=0x04; rows[3]=0x04; rows[4]=0x04; rows[5]=0x04; rows[6]=0x0E; break;
        case '2': rows[0]=0x0E; rows[1]=0x11; rows[2]=0x01; rows[3]=0x06; rows[4]=0x08; rows[5]=0x10; rows[6]=0x1F; break;
        case '3': rows[0]=0x1F; rows[1]=0x02; rows[2]=0x04; rows[3]=0x06; rows[4]=0x01; rows[5]=0x11; rows[6]=0x0E; break;
        case '4': rows[0]=0x02; rows[1]=0x06; rows[2]=0x0A; rows[3]=0x12; rows[4]=0x1F; rows[5]=0x02; rows[6]=0x02; break;
        case '5': rows[0]=0x1F; rows[1]=0x10; rows[2]=0x1E; rows[3]=0x01; rows[4]=0x01; rows[5]=0x11; rows[6]=0x0E; break;
        case '6': rows[0]=0x06; rows[1]=0x08; rows[2]=0x10; rows[3]=0x1E; rows[4]=0x11; rows[5]=0x11; rows[6]=0x0E; break;
        case '7': rows[0]=0x1F; rows[1]=0x01; rows[2]=0x02; rows[3]=0x04; rows[4]=0x08; rows[5]=0x08; rows[6]=0x08; break;
        case '8': rows[0]=0x0E; rows[1]=0x11; rows[2]=0x11; rows[3]=0x0E; rows[4]=0x11; rows[5]=0x11; rows[6]=0x0E; break;
        case '9': rows[0]=0x0E; rows[1]=0x11; rows[2]=0x11; rows[3]=0x0F; rows[4]=0x01; rows[5]=0x02; rows[6]=0x0C; break;
        case '.': rows[5]=0x0C; rows[6]=0x0C; break;
        case ':': rows[1]=0x0C; rows[2]=0x0C; rows[4]=0x0C; rows[5]=0x0C; break;
        case '-': rows[3]=0x1F; break;
        case '+': rows[1]=0x04; rows[2]=0x04; rows[3]=0x1F; rows[4]=0x04; rows[5]=0x04; break;
        case '/': rows[0]=0x01; rows[1]=0x02; rows[2]=0x04; rows[3]=0x04; rows[4]=0x08; rows[5]=0x10; break;
        case '%': rows[0]=0x19; rows[1]=0x1A; rows[2]=0x04; rows[3]=0x04; rows[4]=0x0B; rows[5]=0x13; break;
        case '(': rows[0]=0x02; rows[1]=0x04; rows[2]=0x08; rows[3]=0x08; rows[4]=0x08; rows[5]=0x04; rows[6]=0x02; break;
        case ')': rows[0]=0x08; rows[1]=0x04; rows[2]=0x02; rows[3]=0x02; rows[4]=0x02; rows[5]=0x04; rows[6]=0x08; break;
        case '<': rows[1]=0x02; rows[2]=0x04; rows[3]=0x08; rows[4]=0x04; rows[5]=0x02; break;
        case '>': rows[1]=0x08; rows[2]=0x04; rows[3]=0x02; rows[4]=0x04; rows[5]=0x08; break;
        default: break;
    }
}

static void fb_draw_text(unsigned int *base, int x, int y, const char *str, int scale, unsigned int color) {
    if (!base || !str || scale < 1) return;
    int cx = x;
    for (const char *p = str; *p; p++) {
        char ch = *p;
        if (ch >= 'a' && ch <= 'z') ch = (char)(ch - 32);
        unsigned char rows[7];
        glyph5x7(ch, rows);
        for (int r = 0; r < 7; r++) {
            for (int c = 0; c < 5; c++) {
                if (rows[r] & (1 << (4 - c))) {
                    for (int sy = 0; sy < scale; sy++) {
                        int py = y + r * scale + sy;
                        if (py < 0 || py >= FB_H) continue;
                        for (int sx = 0; sx < scale; sx++) {
                            int px = cx + c * scale + sx;
                            if (px >= 0 && px < FB_W) base[py * FB_W + px] = color;
                        }
                    }
                }
            }
        }
        cx += 6 * scale;
    }
}

static void fb_draw_border(unsigned int *base, int x0, int y0, int x1, int y1, unsigned int border_color) {
    for (int x = x0; x < x1; x++) {
        if (y0 >= 0 && y0 < FB_H) base[y0 * FB_W + x] = border_color;
        if (y1 - 1 >= 0 && y1 - 1 < FB_H) base[(y1 - 1) * FB_W + x] = border_color;
    }
    for (int y = y0; y < y1; y++) {
        if (x0 >= 0 && x0 < FB_W) base[y * FB_W + x0] = border_color;
        if (x1 - 1 >= 0 && x1 - 1 < FB_W) base[y * FB_W + (x1 - 1)] = border_color;
    }
}

static void fb_draw_thick_border(unsigned int *base, int x0, int y0, int x1, int y1, int thickness, unsigned int border_color) {
    for (int t = 0; t < thickness; t++) {
        fb_draw_border(base, x0 + t, y0 + t, x1 - t, y1 - t, border_color);
    }
}

static const char *const k_fps_opts[6]  = { "23.98P", "24.00P", "25.00P", "29.97P", "59.94P", "120P" };
static const char *const k_shut_opts[6] = { "180.0",  "90.0",   "1/48",   "1/50",   "1/60",   "1/100" };
static const char *const k_iso_opts[6]  = { "800 EI", "1600 EI","3200 EI","12800",  "640 EI", "2000 EI" };
static const char *const k_nd_opts[5]   = { "CLEAR",  "1/4 ND", "1/16 ND","1/64 ND","AUTO ND" };
static const char *const k_look_opts[5] = { "S-CINETONE", "S-LOG3", "709TONE", "REC709", "HLG3" };
static const char *const k_wb_opts[5]   = { "5600K",  "3200K",  "4300K",  "6500K",  "ATW" };

/* Exact 5-argument ABI for GRM_gpermFillrect and GRM_gpermRectblit called by libgemini-grm.so */
int GRM_gpermFillrect(unsigned int *cmd_id, const void *cmd_param, const void *fill_param, void *cb, void *ud) {
    (void)cmd_param;
    (void)cb;
    (void)ud;
    ensure_bitmaps();
    if (cmd_id) *cmd_id = 1;
    if (!valid_ptr(fill_param)) return 0;
    const unsigned char *fp = (const unsigned char *)fill_param;
    unsigned char r = fp[0x08];
    unsigned char g = fp[0x09];
    unsigned char b = fp[0x0a];
    unsigned char a = fp[0x0b];
    short rx = *(const short *)(fp + 0x0c);
    short ry = *(const short *)(fp + 0x0e);
    short rw = *(const short *)(fp + 0x10);
    short rh = *(const short *)(fp + 0x12);
    unsigned int color = ((unsigned int)a << 24) | ((unsigned int)r << 16) | ((unsigned int)g << 8) | (unsigned int)b;
    unsigned int out_px;
    if (color != 0) {
        out_px = (color & 0xFF000000U) ? color : (color | 0xFF000000U);
    } else if (rw >= FB_W && rh >= FB_H) {
        out_px = 0xFF101820U; /* Dark slate background for full-screen clear */
    } else {
        out_px = 0xFF2860A8U + ((draw_prim_count * 0x192307U) & 0x003F3F3FU);
    }
    volatile unsigned int *mb = get_fx6_mailbox();
    unsigned int has_input = mb ? mb[1] : 0U;
    unsigned int sel_box   = mb ? (mb[2] % 6U) : 0U;
    unsigned int fps_idx   = mb ? (mb[3] % 6U) : 0U;
    unsigned int shut_idx  = mb ? (mb[4] % 6U) : 0U;
    unsigned int iso_idx   = mb ? (mb[5] % 6U) : 0U;
    unsigned int nd_idx    = mb ? (mb[6] % 5U) : 0U;
    unsigned int look_idx  = mb ? (mb[7] % 5U) : 0U;
    unsigned int wb_idx    = mb ? (mb[8] % 5U) : 0U;
    unsigned int rec_state = mb ? (mb[9] & 1U) : 0U;

    int box_id = -1;
    if (rw == 224 && rh == 140) {
        if (rx == 8 && ry == 52)        box_id = 0;
        else if (rx == 8 && ry == 200)  box_id = 1;
        else if (rx == 8 && ry == 348)  box_id = 2;
        else if (rx == 792 && ry == 52) box_id = 3;
        else if (rx == 792 && ry == 200) box_id = 4;
        else if (rx == 792 && ry == 348) box_id = 5;
    }
    int is_focused = (has_input > 0U && box_id >= 0 && (unsigned int)box_id == sel_box);
    if (is_focused) {
        out_px = 0xFF2C3E54U; /* Highlighted active widget background */
    }

    int x0 = rx < 0 ? 0 : rx;
    int y0 = ry < 0 ? 0 : ry;
    int x1 = (rx + rw > FB_W) ? FB_W : (rx + rw);
    int y1 = (ry + rh > FB_H) ? FB_H : (ry + rh);
    unsigned int *base = (unsigned int *)pix_off;
    for (int y = y0; y < y1; y++) {
        for (int x = x0; x < x1; x++) {
            base[y * FB_W + x] = out_px;
        }
    }
    /* Native-only mode: do not overlay software text/borders. */
    draw_prim_count++;
    if (draw_prim_count <= 40 || draw_prim_count % 50 == 0) {
        dprintf(2, "FX6_GPE_FILLRECT #%u (%d,%d,%d,%d) argb=0x%08x out=0x%08x\n", draw_prim_count, rx, ry, rw, rh, color, out_px);
    }
    if (!in_input_redraw) {
        flush_pixels_to_osd("fillrect");
    }
    return 0;
}

static void fx6_redraw_big6_boxes(void) { }

int GRM_gpermRectblit(unsigned int *cmd_id, const void *cmd_param, const void *blit_param, void *cb, void *ud) {
    (void)cmd_param; (void)cb; (void)ud;
    ensure_bitmaps();
    if (cmd_id) *cmd_id = 1;
    if (!valid_ptr(blit_param)) return 0;
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
            int fmt = *(int *)(info + 0x1c);
            int is_glyph16 = (src != g_icon_bmp);
            int u16_pitch = stride * 2;
            for (int y = 0; y < (y1 - y0); y++) {
                int dy = y0 + y, sy = sy0 + y;
                if (dy < 0 || dy >= FB_H || sy < 0 || sy >= sh) continue;
                for (int x = 0; x < (x1 - x0); x++) {
                    int dx = x0 + x, sx = sx0 + x;
                    if (dx < 0 || dx >= FB_W || sx < 0 || sx >= sw) continue;
                    if (is_glyph16) {
                        const unsigned char *row8 = (const unsigned char *)bits + sy * (stride * 4);
                        unsigned int a = row8[sx];
                        if (a > 0U) {
                            unsigned int sr = 255U, sg = 255U, sb_c = 255U;
                            if ((dx0 < 240 || dx0 >= 780) && dy0 >= 50 && dy0 < 490) {
                                int ry = (dy0 - 52) % 148; if (ry < 0) ry += 148;
                                if (ry < 36) { sr = 245U; sg = 155U; sb_c = 45U; }
                                else if (ry >= 90) { sr = 150U; sg = 195U; sb_c = 230U; }
                            }
                            if (dy0 < 48 && dx0 >= 650) { sr = 80U; sg = 235U; sb_c = 130U; }
                            if (dx0 >= 240 && dx0 < 780 && dy0 >= 50 && dy0 < 405) { sr = 110U; sg = 215U; sb_c = 250U; }
                            if (dx0 >= 240 && dx0 < 780 && dy0 >= 415 && dy0 < 448) { sr = 80U; sg = 235U; sb_c = 130U; }
                            unsigned int dst = db[dy * FB_W + dx];
                            unsigned int dr = (dst >> 16) & 0xFFU, dg = (dst >> 8) & 0xFFU, db_c = dst & 0xFFU;
                            unsigned int or_c = (sr * a + dr * (255U - a)) / 255U;
                            unsigned int og_c = (sg * a + dg * (255U - a)) / 255U;
                            unsigned int ob_c = (sb_c * a + db_c * (255U - a)) / 255U;
                            db[dy * FB_W + dx] = 0xFF000000U | (or_c << 16) | (og_c << 8) | ob_c;
                        }
                    } else {
                        unsigned int p = ((const unsigned int *)bits)[sy * stride + sx];
                        if (p != 0) db[dy * FB_W + dx] = p | 0xFF000000U;
                    }
                }
            }
        }
    }
    draw_prim_count++;
    if (draw_prim_count <= 40 || draw_prim_count % 50 == 0) dprintf(2, "FX6_GPE_RECTBLIT #%u dst=(%d,%d,%d,%d) src=%p\n", draw_prim_count, dx0, dy0, dw0, dh0, src);
    flush_pixels_to_osd("rectblit");
    return 0;
}

int _ZN2ma4MMap3mapElm(void *self, long addr, unsigned long len) {
    (void)self;
    (void)addr;
    (void)len;
    dprintf(2, "FX6_MA_MMAP_SKIP\n");
    return 0;
}

__attribute__((constructor)) static void stub_ctor(void) {
    dprintf(2, "FX6_BMP_STUB30_LOADED\n");
    dprintf(2, "FX3_GPE_RESOURCE_REGISTER type=0x403 logical=0x41e001000 phys=0x41e001000 bytes=0x21c000\n");
}


void _ZN2ux6resmgr15ResourceManager10createFontERKN5alcor13FontAttributeERN5libra9RecordPtrE(const void *attr, void *rec) {
    typedef void (*fn_t)(const void*,void*); static fn_t real;
    if (!real) { void *h=dlopen("/usr/lib/libuxengine.so",1); real=(fn_t)dlsym(h,"_ZN2ux6resmgr15ResourceManager10createFontERKN5alcor13FontAttributeERN5libra9RecordPtrE"); }
    dprintf(2,"FX6_FONT_CREATE2 attr=%p rec=%p before=%p real=%p\n",attr,rec,rec?*(void**)rec:0,(void*)real);
    if (real) real(attr,rec);
    dprintf(2,"FX6_FONT_CREATE2_DONE rec=%p after=%p\n",rec,rec?*(void**)rec:0);
}

void _ZN2ux6gfxeng10TextSprite18ImageDataContainer11onImageLoadEv(void *self) {
    if (!valid_ptr(self)) return;
    void *ts = *(void **)self;
    if (!valid_ptr(ts) || !valid_ptr(*(void **)ts)) return;
    typedef void (*fn_t)(void *, unsigned int); static fn_t real;
    if (!real) { void *h=dlopen("/usr/lib/libuxengine.so",1); real=(fn_t)dlsym(h,"_ZN2ux6gfxeng10TextSprite11onImageLoadEj"); }
    if (real) real(ts, *(unsigned int *)((char *)self + 0x18));
}
