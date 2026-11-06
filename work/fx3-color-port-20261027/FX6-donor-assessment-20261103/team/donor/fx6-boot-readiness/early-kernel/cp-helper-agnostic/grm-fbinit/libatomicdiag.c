/* Log libstdc++ atomic futex wait target/caller. */
extern void *dlsym(void *, const char *);
extern int dprintf(int, const char *, ...);
_Bool _ZNSt28__atomic_futex_unsigned_base19_M_futex_wait_untilEPjjbNSt6chrono8durationIlSt5ratioILl1ELl1EEEENS2_IlS3_ILl1ELl1000000000EEEE(void *self, unsigned *futex, unsigned val, _Bool has_timeout, long s, long ns) {
    typedef _Bool (*fn)(void *, unsigned *, unsigned, _Bool, long, long); static fn real;
    if (!real) real=(fn)dlsym((void *)-1,"_ZNSt28__atomic_futex_unsigned_base19_M_futex_wait_untilEPjjbNSt6chrono8durationIlSt5ratioILl1ELl1EEEENS2_IlS3_ILl1ELl1000000000EEEE");
    dprintf(2,"ATOMICDIAG_WAIT self=%p futex=%p val=%u to=%d c0=%p c1=%p\n", self, futex, val, (int)has_timeout, __builtin_return_address(0), __builtin_return_address(1));
    return real?real(self,futex,val,has_timeout,s,ns):0;
}
