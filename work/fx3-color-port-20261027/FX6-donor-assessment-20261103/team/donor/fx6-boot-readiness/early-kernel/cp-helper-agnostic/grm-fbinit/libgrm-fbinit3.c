/* Minimal FrameBuffer construction for FX6 libgrm.
 * Calls the real FrameBuffer constructor and stores it at manager+0x8,
 * but does NOT run the full FBResourceManager::initialize (threads/semaphores),
 * which aborts on this FX3 VM. */
typedef unsigned long size_t;
extern void *dlsym(void *, const char *);
extern int dprintf(int, const char *, ...);
static unsigned char fb_storage[0x1000] __attribute__((aligned(16)));
static int guard;
/* The FX3 VM has no GRM/GPE backing for FrameBuffer::update; accept it. */
void _ZN3grm11FrameBuffer6updateEv(void *self) {
    dprintf(2, "FX6_GRM_FB_UPDATE_SKIP self=%p result=0\n", self);
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
