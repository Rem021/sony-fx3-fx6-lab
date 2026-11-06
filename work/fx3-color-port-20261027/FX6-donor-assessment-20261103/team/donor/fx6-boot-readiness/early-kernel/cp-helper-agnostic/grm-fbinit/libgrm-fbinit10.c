/* Minimal FrameBuffer construction for FX6 libgrm.
 * Calls the real FrameBuffer constructor and stores it at manager+0x8,
 * but does NOT run the full FBResourceManager::initialize (threads/semaphores),
 * which aborts on this FX3 VM. */
typedef unsigned long size_t;
extern void *dlsym(void *, const char *);
extern int dprintf(int, const char *, ...);
static unsigned char fb_storage[0x1000] __attribute__((aligned(16)));
static int guard;
/* AppFw reports 1024x540 via FrameBuffer::setSize; use the same size for the
 * UX screen area when the screen object still carries 0x0. */
void _ZN2ux6gfxeng6Screen20setAreaInFramebufferEsstt(void *self, short x, short y, unsigned short w, unsigned short h) {
    typedef void (*real_fn)(void *, short, short, unsigned short, unsigned short);
    static real_fn real;
    if (!real) real = (real_fn)dlsym((void *)-1, "_ZN2ux6gfxeng6Screen20setAreaInFramebufferEsstt");
    dprintf(2, "FX6_UX_SCREEN_AREA_1024 self=%p x=%d y=%d w=%u h=%u\n", self, x, y, w, h);
    if (!w || !h) { dprintf(2, "FX6_UX_SCREEN_AREA_SKIP_ZERO self=%p\n", self); return; }
    if (real) real(self, x, y, w, h);
}

/* Initialize the fake framebuffer's size before UXEngine reads it. */
void _ZN3grm11FrameBuffer7setSizeEtt(void *self, unsigned short w, unsigned short h) {
    if (!w) w = 1024; if (!h) h = 540;
    *(unsigned short *)((char *)self + 0x14) = w;
    *(unsigned short *)((char *)self + 0x16) = h;
    dprintf(2, "FX6_GRM_FB_SET_SIZE self=%p w=%u h=%u\n", self, w, h);
}

/* Safe getters: the fake FrameBuffer has no BMP at +0x68/+0x70. */
void *_ZN3grm11FrameBuffer11getOnscreenEv(void *self) {
    dprintf(2, "FX6_GRM_FB_GET_ONSCREEN_SKIP self=%p result=NULL\n", self); return (void *)0;
}
void *_ZN3grm11FrameBuffer12getOffscreenEv(void *self) {
    dprintf(2, "FX6_GRM_FB_GET_OFFSCREEN_SKIP self=%p result=NULL\n", self); return (void *)0;
}
unsigned int _ZN3grm11FrameBuffer17getOnscreenHandleEv(void *self) {
    dprintf(2, "FX6_GRM_FB_GET_ONSCREEN_HANDLE_SKIP self=%p result=0\n", self); return 0;
}
void _ZN3grm11FrameBuffer8lockSwapEv(void *self) { dprintf(2, "FX6_GRM_FB_LOCK_SKIP self=%p\n", self); }
void _ZN3grm11FrameBuffer10unlockSwapEv(void *self) { dprintf(2, "FX6_GRM_FB_UNLOCK_SKIP self=%p\n", self); }
/* Abort backtrace diagnostic. */
extern void _exit(int) __attribute__((noreturn));
void abort(void) {
    typedef void (*abort_fn)(void);
    typedef int (*bt_fn)(void **, int);
    static abort_fn real_abort; static bt_fn real_bt;
    if (!real_abort) real_abort = (abort_fn)dlsym((void *)-1, "abort");
    if (!real_bt) real_bt = (bt_fn)dlsym((void *)-1, "backtrace");
    void *fr[16]; int n = real_bt ? real_bt(fr, 16) : 0;
    dprintf(2, "FX6_ABORT_BT n=%d", n);
    for (int i = 0; i < n && i < 16; i++) dprintf(2, " f%d=%p", i, fr[i]);
    dprintf(2, "\n");
    if (real_abort) real_abort();
    _exit(127);
}

/* Full manager/framebuffer initialization needs GRM/GPE/threads; skip it. */
void _ZN3grm17FBResourceManager10initializeEv(void *self) {
    dprintf(2, "FX6_GRM_MANAGER_INIT_SKIP self=%p result=0\n", self);
}
int _ZN3grm11FrameBuffer10initializeEjm(void *self, unsigned int w, unsigned int h) {
    dprintf(2, "FX6_GRM_FB_INIT_SKIP self=%p w=%u h=%u result=0\n", self, w, h);
    return 0;
}

void _ZN3grm11FrameBuffer6updateEv(void *self) {
    typedef void (*fn)(void *); static fn real;
    if (!real) real = (fn)dlsym((void *)-1, "_ZN3grm11FrameBuffer6updateEv");
    dprintf(2, "FX6_GRM_FB_UPDATE_REAL self=%p real=%p\n", self, (void *)real);
    if (real) real(self);
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
