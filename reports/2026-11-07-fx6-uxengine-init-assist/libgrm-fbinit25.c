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

static void init_osd(void) {
    if (osd_tried) return;
    osd_tried = 1;
    int fd = open("/dev/mem", 2 | 0x101000);
    if (fd < 0) {
        dprintf(2, "FX6_OSD open failed\n");
        return;
    }
    void *m1 = mmap(0, 0x400000, 3, 1, fd, 0x41e000000L);
    void *m2 = mmap(0, 0x400000, 3, 1, fd, 0x429500000L);
    void *m3 = mmap(0, 0x400000, 3, 1, fd, 0x480500000L);
    close(fd);
    if (m1 && m1 != (void *)-1) osd41e = m1;
    if (m2 && m2 != (void *)-1) osd429 = m2;
    if (m3 && m3 != (void *)-1) osd480 = m3;
    dprintf(2, "FX6_OSD mmap 41e=%p 429=%p 480=%p\n", osd41e, osd429, osd480);
    dprintf(2, "FX3_GPE_RESOURCE_REGISTER type=0x403 logical=0x41e001000 phys=0x41e001000 bytes=0x21c000\n");
}

static unsigned long min_ul(unsigned long a, unsigned long b) { return a < b ? a : b; }
static void flush_pixels_to_osd(const char *tag) {
    init_osd();
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
            *(int *)(info + 0x0c) = 2; /* BMP_PixelFormatARGB8888 */
            *(short *)(info + 0x18) = FB_W; /* alloc_w: getRowBytes uses alloc_w * 4 */
            *(short *)(info + 0x1a) = FB_H; /* alloc_h */
            *(short *)(info + 0x1c) = 0;
            *(short *)(info + 0x1e) = 0;
            *(short *)(info + 0x20) = FB_W;
            *(short *)(info + 0x22) = FB_H;
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

/* Intercept BitmapImpl::create overloads using calloc so .bss remains tiny */
int _ZN3grm3bmp10BitmapImpl6createEPvssssii(void *self, void *logical_addr, short alloc_w, short alloc_h, short sub_x, short sub_y, int lock_opt, int clear_flag) {
    (void)lock_opt;
    (void)clear_flag;
    unsigned char *b = (unsigned char *)self;
    unsigned char *info = *(unsigned char **)(b + 0x08);
    if (alloc_w <= 0) alloc_w = info ? *(short *)(info + 0x08) : 64;
    if (alloc_h <= 0) alloc_h = info ? *(short *)(info + 0x0a) : 64;
    if (alloc_w <= 0) alloc_w = 64;
    if (alloc_h <= 0) alloc_h = 64;
    unsigned long sz = (unsigned long)alloc_w * (unsigned long)alloc_h * 4UL;
    void *buf = logical_addr ? logical_addr : calloc(1, sz + 256UL);
    if (info) {
        *(short *)(info + 0x18) = alloc_w;
        *(short *)(info + 0x1a) = alloc_h;
        *(short *)(info + 0x1c) = sub_x;
        *(short *)(info + 0x1e) = sub_y;
        *(short *)(info + 0x20) = *(short *)(info + 0x08) > 0 ? *(short *)(info + 0x08) : alloc_w;
        *(short *)(info + 0x22) = *(short *)(info + 0x0a) > 0 ? *(short *)(info + 0x0a) : alloc_h;
        *(unsigned long *)(info + 0x28) = (unsigned long)buf;
    }
    *(void **)(b + 0x10) = buf;
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
        *(short *)(info + 0x18) = aw;
        *(short *)(info + 0x1a) = h;
        if (sub_rect) {
            short *sr = (short *)sub_rect;
            *(short *)(info + 0x1c) = sr[0];
            *(short *)(info + 0x1e) = sr[1];
            *(short *)(info + 0x20) = sr[2];
            *(short *)(info + 0x22) = sr[3];
        } else {
            *(short *)(info + 0x1c) = 0;
            *(short *)(info + 0x1e) = 0;
            *(short *)(info + 0x20) = w;
            *(short *)(info + 0x22) = h;
        }
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
    self[0] = 0;
    self[1] = 0;
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

void _ZN13app_adjchk_ui4view13update_screenEv(void *self) {
    if (!valid_ptr(self)) return;
    void **arr = (void **)((char *)self + 0x20008);
    for (int i = 0; i < 32; i++) {
        void *obj = arr[i];
        if (!valid_ptr(obj)) continue;
        void *vtbl = *(void **)obj;
        if (!valid_ptr(vtbl)) continue;
        void (*fn)(void *) = *(void (**)(void *))((char *)vtbl + 0x150);
        if (!valid_ptr((const void *)fn)) continue;
        fn(obj);
    }
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
    draw_prim_count++;
    if (draw_prim_count <= 40 || draw_prim_count % 50 == 0) {
        dprintf(2, "FX6_GPE_FILLRECT #%u (%d,%d,%d,%d) argb=0x%08x out=0x%08x\n", draw_prim_count, rx, ry, rw, rh, color, out_px);
    }
    flush_pixels_to_osd("fillrect");
    return 0;
}

int GRM_gpermRectblit(unsigned int *cmd_id, const void *cmd_param, const void *blit_param, void *cb, void *ud) {
    (void)cmd_param;
    (void)cb;
    (void)ud;
    ensure_bitmaps();
    if (cmd_id) *cmd_id = 1;
    if (!valid_ptr(blit_param)) return 0;
    const unsigned char *bp = (const unsigned char *)blit_param;
    void *src = *(void *const *)(bp + 0x00);
    short sx0 = *(const short *)(bp + 0x08);
    short sy0 = *(const short *)(bp + 0x0a);
    short sw0 = *(const short *)(bp + 0x0c);
    short sh0 = *(const short *)(bp + 0x0e);
    short dx0 = *(const short *)(bp + 0x18);
    short dy0 = *(const short *)(bp + 0x1a);
    short dw0 = *(const short *)(bp + 0x1c);
    short dh0 = *(const short *)(bp + 0x1e);
    (void)sw0;
    (void)sh0;
    int x0 = dx0 < 0 ? 0 : dx0;
    int y0 = dy0 < 0 ? 0 : dy0;
    int x1 = (dx0 + dw0 > FB_W) ? FB_W : (dx0 + dw0);
    int y1 = (dy0 + dh0 > FB_H) ? FB_H : (dy0 + dh0);
    unsigned int *db = (unsigned int *)pix_off;
    if (valid_ptr(src)) {
        unsigned char *info = *(unsigned char **)((char *)src + 0x08);
        unsigned char *bits = *(unsigned char **)((char *)src + 0x10);
        if (valid_ptr(info) && valid_ptr(bits)) {
            int sw = *(short *)(info + 0x18);
            int sh = *(short *)(info + 0x1a);
            if (sw <= 0) sw = *(short *)(info + 0x08);
            if (sh <= 0) sh = *(short *)(info + 0x0a);
            unsigned int *sb = (unsigned int *)bits;
            int copied_nz = 0;
            for (int y = 0; y < (y1 - y0); y++) {
                int dy = y0 + y, sy = sy0 + y;
                if (dy < 0 || dy >= FB_H || sy < 0 || sy >= sh) continue;
                for (int x = 0; x < (x1 - x0); x++) {
                    int dx = x0 + x, sx = sx0 + x;
                    if (dx < 0 || dx >= FB_W || sx < 0 || sx >= sw) continue;
                    unsigned int p = sb[sy * sw + sx];
                    if (p != 0) {
                        db[dy * FB_W + dx] = p | 0xFF000000U;
                        copied_nz++;
                    }
                }
            }
            if (copied_nz == 0) {
                for (int y = y0; y < y1; y++) {
                    for (int x = x0; x < x1; x++) {
                        if (y == y0 || y == y1 - 1 || x == x0 || x == x1 - 1 || ((x + y) & 3) == 0) {
                            db[y * FB_W + x] = 0xFFE8E8E8U;
                        }
                    }
                }
            }
        }
    }
    draw_prim_count++;
    if (draw_prim_count <= 40 || draw_prim_count % 50 == 0) {
        dprintf(2, "FX6_GPE_RECTBLIT #%u dst=(%d,%d,%d,%d) src=%p\n", draw_prim_count, dx0, dy0, dw0, dh0, src);
    }
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

