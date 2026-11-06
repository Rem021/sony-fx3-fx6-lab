/* Log contended pthread mutex, pthread_once and __cxa_guard acquisitions with caller1. */
extern void *dlsym(void *, const char *);
extern int dprintf(int, const char *, ...);
int pthread_mutex_lock(void *m) {
    typedef int (*fn)(void *); static fn real, real_try;
    if (!real) real=(fn)dlsym((void *)-1,"pthread_mutex_lock");
    if (!real_try) real_try=(fn)dlsym((void *)-1,"pthread_mutex_trylock");
    if (real_try && real_try(m)==0) return 0;
    dprintf(2,"MUTEXDIAG_LOCK m=%p c0=%p c1=%p\n", m, __builtin_return_address(0), __builtin_return_address(1));
    return real?real(m):-1;
}
int pthread_once(void *once, void (*init)(void)) {
    typedef int (*fn)(void *, void (*)(void)); static fn real;
    if (!real) real=(fn)dlsym((void *)-1,"pthread_once");
    dprintf(2,"MUTEXDIAG_ONCE once=%p init=%p c0=%p c1=%p\n", once, (void*)init, __builtin_return_address(0), __builtin_return_address(1));
    return real?real(once,init):-1;
}
int __cxa_guard_acquire(void *g) {
    typedef int (*fn)(void *); static fn real;
    if (!real) real=(fn)dlsym((void *)-1,"__cxa_guard_acquire");
    dprintf(2,"MUTEXDIAG_GUARD g=%p c0=%p c1=%p\n", g, __builtin_return_address(0), __builtin_return_address(1));
    return real?real(g):1;
}
