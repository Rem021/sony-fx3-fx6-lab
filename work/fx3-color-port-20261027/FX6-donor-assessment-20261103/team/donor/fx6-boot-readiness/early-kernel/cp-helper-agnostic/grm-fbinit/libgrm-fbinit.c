/* Lazy GRM framebuffer initialization shim.
 * libgrm's FBResourceManager::initialize() creates the FrameBuffer at +0x8.
 * The FX6 appFw can call initializeFrameBuffer() before any initialize();
 * this interposer calls the real initialize() once, then returns the manager.
 */
typedef unsigned long size_t;
extern void *dlsym(void *, const char *);
extern int dprintf(int, const char *, ...);
static int guard;
void *_ZN3grm17FBResourceManager11getInstanceEv(void) {
    typedef void *(*get_fn)(void);
    typedef void (*init_fn)(void *);
    static get_fn real_get;
    static init_fn real_init;
    if (!real_get) real_get = (get_fn)dlsym((void *)-1, "_ZN3grm17FBResourceManager11getInstanceEv");
    if (!real_get) return (void *)0;
    void *m = real_get();
    if (!m || guard) return m;
    guard = 1;
    void **fb = (void **)((char *)m + 8);
    if (!*fb) {
        if (!real_init) real_init = (init_fn)dlsym((void *)-1, "_ZN3grm17FBResourceManager10initializeEv");
        dprintf(2, "FX6_GRM_FB_LAZY_INIT before manager=%p fb=%p real_init=%p\n", m, *fb, (void *)real_init);
        if (real_init) real_init(m);
        dprintf(2, "FX6_GRM_FB_LAZY_INIT after manager=%p fb=%p\n", m, *fb);
    }
    guard = 0;
    return m;
}
