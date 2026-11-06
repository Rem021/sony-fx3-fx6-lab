/* Minimal pthread wait diagnostics: log condition/mutex address and caller. */
extern void *dlsym(void *, const char *);
extern int dprintf(int, const char *, ...);
typedef void *pthread_cond_t;
typedef void *pthread_mutex_t;
typedef void *pthread_mutexattr_t;
typedef void *pthread_condattr_t;
typedef void *timespec_t;
int pthread_cond_wait(pthread_cond_t *c, pthread_mutex_t *m) {
    typedef int (*fn)(pthread_cond_t *, pthread_mutex_t *);
    static fn real;
    if (!real) real = (fn)dlsym((void *)-1, "pthread_cond_wait");
    dprintf(2, "DIAG_COND_WAIT cond=%p mutex=%p caller=%p\n", (void *)c, (void *)m, __builtin_return_address(0));
    return real ? real(c, m) : -1;
}
int pthread_cond_timedwait(pthread_cond_t *c, pthread_mutex_t *m, const timespec_t *t) {
    typedef int (*fn)(pthread_cond_t *, pthread_mutex_t *, const timespec_t *);
    static fn real;
    if (!real) real = (fn)dlsym((void *)-1, "pthread_cond_timedwait");
    dprintf(2, "DIAG_COND_TIMEDWAIT cond=%p mutex=%p caller=%p\n", (void *)c, (void *)m, __builtin_return_address(0));
    return real ? real(c, m, t) : -1;
}
int pthread_mutex_lock(pthread_mutex_t *m) {
    typedef int (*fn)(pthread_mutex_t *);
    static fn real_lock, real_try;
    if (!real_lock) real_lock = (fn)dlsym((void *)-1, "pthread_mutex_lock");
    if (!real_try) real_try = (fn)dlsym((void *)-1, "pthread_mutex_trylock");
    if (real_try && real_try(m) == 0) return 0;
    dprintf(2, "DIAG_MUTEX_CONTENDED mutex=%p caller=%p\n", (void *)m, __builtin_return_address(0));
    return real_lock ? real_lock(m) : -1;
}
