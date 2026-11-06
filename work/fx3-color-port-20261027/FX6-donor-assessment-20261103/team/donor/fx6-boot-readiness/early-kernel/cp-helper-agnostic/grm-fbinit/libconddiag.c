/* Direct pthread condition variable diagnostics with caller1. */
extern void *dlsym(void *, const char *);
extern int dprintf(int, const char *, ...);
int pthread_cond_wait(void *c, void *m) {
    typedef int (*fn)(void *, void *); static fn real;
    if (!real) real=(fn)dlsym((void *)-1,"pthread_cond_wait");
    dprintf(2,"CONDDIAG_WAIT c=%p m=%p c0=%p c1=%p\n", c, m, __builtin_return_address(0), __builtin_return_address(1));
    return real?real(c,m):-1;
}
int pthread_cond_timedwait(void *c, void *m, const void *t) {
    typedef int (*fn)(void *, void *, const void *); static fn real;
    if (!real) real=(fn)dlsym((void *)-1,"pthread_cond_timedwait");
    dprintf(2,"CONDDIAG_TIMEDWAIT c=%p m=%p c0=%p c1=%p\n", c, m, __builtin_return_address(0), __builtin_return_address(1));
    return real?real(c,m,t):-1;
}
int pthread_cond_signal(void *c) {
    typedef int (*fn)(void *); static fn real;
    if (!real) real=(fn)dlsym((void *)-1,"pthread_cond_signal");
    dprintf(2,"CONDDIAG_SIGNAL c=%p c0=%p c1=%p\n", c, __builtin_return_address(0), __builtin_return_address(1));
    return real?real(c):-1;
}
int pthread_cond_broadcast(void *c) {
    typedef int (*fn)(void *); static fn real;
    if (!real) real=(fn)dlsym((void *)-1,"pthread_cond_broadcast");
    dprintf(2,"CONDDIAG_BROADCAST c=%p c0=%p c1=%p\n", c, __builtin_return_address(0), __builtin_return_address(1));
    return real?real(c):-1;
}
