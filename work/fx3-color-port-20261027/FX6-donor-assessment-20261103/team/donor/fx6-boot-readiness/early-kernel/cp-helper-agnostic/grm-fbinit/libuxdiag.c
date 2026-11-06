/* Read-only UXEngine init/draw probes. */
extern void *dlsym(void *, const char *);
extern int dprintf(int, const char *, ...);
int _ZN8UXEngine10initializeEPKcttN2ux6wgtsys7FPSTypeEjmm(void *s, const char *p, unsigned short w, unsigned short h, int fps, unsigned f, unsigned long a, unsigned long b) {
    typedef int (*fn)(void *, const char *, unsigned short, unsigned short, int, unsigned, unsigned long, unsigned long);
    static fn real; if (!real) real=(fn)dlsym((void *)-1,"_ZN8UXEngine10initializeEPKcttN2ux6wgtsys7FPSTypeEjmm");
    dprintf(2,"UXDIAG_ENGINE_INIT_ENTER self=%p p=%s w=%u h=%u fps=%d f=%u a=%lu b=%lu\n",s,p?p:"?",w,h,fps,f,a,b);
    int r=real?real(s,p,w,h,fps,f,a,b):-1;
    dprintf(2,"UXDIAG_ENGINE_INIT_RET self=%p ret=%d\n",s,r); return r;
}
int _ZN2ux6resmgr15ResourceManager14sys_initializeEj(void *s, unsigned v) {
    typedef int (*fn)(void *, unsigned); static fn real;
    if (!real) real=(fn)dlsym((void *)-1,"_ZN2ux6resmgr15ResourceManager14sys_initializeEj");
    dprintf(2,"UXDIAG_RESMGR_INIT_ENTER self=%p v=%u\n",s,v); int r=real?real(s,v):-1;
    dprintf(2,"UXDIAG_RESMGR_INIT_RET self=%p ret=%d\n",s,r); return r;
}
int _ZN2ux6wgtsys12WidgetSystem14sys_initializeENS0_7FPSTypeE(void *s, int fps) {
    typedef int (*fn)(void *, int); static fn real;
    if (!real) real=(fn)dlsym((void *)-1,"_ZN2ux6wgtsys12WidgetSystem14sys_initializeENS0_7FPSTypeE");
    dprintf(2,"UXDIAG_WGT_INIT_ENTER self=%p fps=%d\n",s,fps); int r=real?real(s,fps):-1;
    dprintf(2,"UXDIAG_WGT_INIT_RET self=%p ret=%d\n",s,r); return r;
}
int _ZN2ux6gfxeng14GraphicsEngine14sys_initializeEPKcttt(void *s, const char *p, unsigned short w, unsigned short h, unsigned short x) {
    typedef int (*fn)(void *, const char *, unsigned short, unsigned short, unsigned short); static fn real;
    if (!real) real=(fn)dlsym((void *)-1,"_ZN2ux6gfxeng14GraphicsEngine14sys_initializeEPKcttt");
    dprintf(2,"UXDIAG_GFX_INIT_ENTER self=%p p=%s w=%u h=%u x=%u\n",s,p?p:"?",w,h,x); int r=real?real(s,p,w,h,x):-1;
    dprintf(2,"UXDIAG_GFX_INIT_RET self=%p ret=%d\n",s,r); return r;
}
int _ZN8UXEngine19beginDrawOnMultiTskEv(void *s) {
    typedef int (*fn)(void *); static fn real;
    if (!real) real=(fn)dlsym((void *)-1,"_ZN8UXEngine19beginDrawOnMultiTskEv");
    dprintf(2,"UXDIAG_BEGIN_DRAW_ENTER self=%p\n",s); int r=real?real(s):-1;
    dprintf(2,"UXDIAG_BEGIN_DRAW_RET self=%p ret=%d\n",s,r); return r;
}
void _ZN8UXEngine18execDrawOnMultiTskEv(void *s) {
    typedef void (*fn)(void *); static fn real;
    if (!real) real=(fn)dlsym((void *)-1,"_ZN8UXEngine18execDrawOnMultiTskEv");
    dprintf(2,"UXDIAG_EXEC_DRAW_ENTER self=%p\n",s); if (real) real(s); dprintf(2,"UXDIAG_EXEC_DRAW_RET self=%p\n",s);
}
int _ZN2ux6resmgr15ResourceManager21sys_invokeWorkerEventEv(void *s) {
    typedef int (*fn)(void *); static fn real;
    if (!real) real=(fn)dlsym((void *)-1,"_ZN2ux6resmgr15ResourceManager21sys_invokeWorkerEventEv");
    dprintf(2,"UXDIAG_WORKER_EVENT_ENTER self=%p\n",s); int r=real?real(s):-1;
    dprintf(2,"UXDIAG_WORKER_EVENT_RET self=%p ret=%d\n",s,r); return r;
}
