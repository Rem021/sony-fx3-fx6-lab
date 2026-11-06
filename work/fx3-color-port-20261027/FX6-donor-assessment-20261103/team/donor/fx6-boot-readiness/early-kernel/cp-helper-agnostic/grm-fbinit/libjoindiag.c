/* Log pthread_join and std::thread::join targets/callers. */
extern void *dlsym(void *, const char *);
extern int dprintf(int, const char *, ...);
int pthread_join(unsigned long th, void **ret) {
    typedef int (*fn)(unsigned long, void **); static fn real;
    if (!real) real=(fn)dlsym((void *)-1,"pthread_join");
    dprintf(2,"JOINDIAG_PTHREAD th=%#lx c0=%p c1=%p\n", th, __builtin_return_address(0), __builtin_return_address(1));
    return real?real(th,ret):-1;
}
void _ZNSt6thread4joinEv(void *self) {
    typedef void (*fn)(void *); static fn real;
    if (!real) real=(fn)dlsym((void *)-1,"_ZNSt6thread4joinEv");
    dprintf(2,"JOINDIAG_STDTHREAD self=%p c0=%p c1=%p\n", self, __builtin_return_address(0), __builtin_return_address(1));
    if (real) real(self);
}
