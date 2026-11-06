/* Log std::condition_variable wait/notify object, caller0 (wrapper call site) and caller1 (producer/user). */
extern void *dlsym(void *, const char *);
extern int dprintf(int, const char *, ...);
void _ZNSt18condition_variable4waitERSt11unique_lockISt5mutexE(void *self, void *lock) {
    typedef void (*fn)(void *, void *); static fn real;
    if (!real) real=(fn)dlsym((void *)-1,"_ZNSt18condition_variable4waitERSt11unique_lockISt5mutexE");
    dprintf(2,"CVDIAG2_WAIT self=%p lock=%p c0=%p c1=%p\n", self, lock, __builtin_return_address(0), __builtin_return_address(1));
    if (real) real(self, lock);
}
void _ZNSt18condition_variable10notify_oneEv(void *self) {
    typedef void (*fn)(void *); static fn real;
    if (!real) real=(fn)dlsym((void *)-1,"_ZNSt18condition_variable10notify_oneEv");
    dprintf(2,"CVDIAG2_NOTIFY_ONE self=%p c0=%p c1=%p\n", self, __builtin_return_address(0), __builtin_return_address(1));
    if (real) real(self);
}
void _ZNSt18condition_variable10notify_allEv(void *self) {
    typedef void (*fn)(void *); static fn real;
    if (!real) real=(fn)dlsym((void *)-1,"_ZNSt18condition_variable10notify_allEv");
    dprintf(2,"CVDIAG2_NOTIFY_ALL self=%p c0=%p c1=%p\n", self, __builtin_return_address(0), __builtin_return_address(1));
    if (real) real(self);
}
