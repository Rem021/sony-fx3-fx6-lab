/* FX3MS2 bounded sequential /proc/<pid>/maps collector (AArch64 Linux).
 *
 * Freestanding: no libc, no malloc, no printf.  Raw Linux syscalls only.
 * The collector reads until EOF, under an explicit total-byte cap, read
 * count, wall-clock limit and EINTR limits, and rechecks the same /proc/<pid>
 * directory + starttime before and after.  The payload is a complete byte
 * stream, not an atomic kernel snapshot; the protocol always says
 * snapshot_atomic=0.
 *
 * This file is an offline candidate.  It has not been executed on the target
 * in this task; the native test harness exercises the shared collector core.
 */
#include "collector_core.h"

#define AT_FDCWD (-100L)
#define O_RDONLY 0L
#define O_DIRECTORY 040000L
#define O_CLOEXEC 02000000L
#define CLOCK_MONOTONIC 1L
#define EINTR_NR 4L
#define SYS_OPENAT 56L
#define SYS_CLOSE 57L
#define SYS_READ 63L
#define SYS_WRITE 64L
#define SYS_EXIT 93L
#define SYS_CLOCK_GETTIME 113L
#define MAX_WRITE_BYTES 1500000UL
#define MAX_WRITE_EINTR 8U
#define BASE64_CHUNK 192U

static long sys2(long nr, long a0, long a1)
{
    register long x8 __asm__("x8") = nr;
    register long x0 __asm__("x0") = a0;
    register long x1 __asm__("x1") = a1;
    __asm__ __volatile__("svc #0" : "+r"(x0) : "r"(x8), "r"(x1) : "memory");
    return x0;
}

static long sys3(long nr, long a0, long a1, long a2)
{
    register long x8 __asm__("x8") = nr;
    register long x0 __asm__("x0") = a0;
    register long x1 __asm__("x1") = a1;
    register long x2 __asm__("x2") = a2;
    __asm__ __volatile__("svc #0" : "+r"(x0) : "r"(x8), "r"(x1), "r"(x2) : "memory");
    return x0;
}

static long sys_openat(long dirfd, const char *path, long flags)
{
    return sys3(SYS_OPENAT, dirfd, (long)path, flags);
}

static long sys_read(long fd, void *buf, unsigned long n)
{
    return sys3(SYS_READ, fd, (long)buf, (long)n);
}

static long sys_write(long fd, const void *buf, unsigned long n)
{
    return sys3(SYS_WRITE, fd, (long)buf, (long)n);
}

static long sys_close(long fd)
{
    return sys2(SYS_CLOSE, fd, 0);
}

static void sys_exit(long code) __attribute__((noreturn));
static void sys_exit(long code)
{
    (void)sys2(SYS_EXIT, code, 0);
    for (;;) {
    }
}

struct fx3_timespec {
    long tv_sec;
    long tv_nsec;
};

static int mono_ms(unsigned long long *out_ms)
{
    struct fx3_timespec ts = {0, 0};
    long r = sys2(SYS_CLOCK_GETTIME, CLOCK_MONOTONIC, (long)&ts);
    if (r < 0) {
        return -1;
    }
    if (ts.tv_sec < 0 || ts.tv_nsec < 0 || ts.tv_nsec >= 1000000000L) {
        return -1;
    }
    *out_ms = (unsigned long long)ts.tv_sec * 1000ULL + (unsigned long long)ts.tv_nsec / 1000000ULL;
    return 0;
}

static int append_char(char *b, unsigned long cap, unsigned long *n, char c)
{
    if (*n + 1 >= cap) {
        return -1;
    }
    b[*n] = c;
    (*n)++;
    return 0;
}

static int append_str(char *b, unsigned long cap, unsigned long *n, const char *s)
{
    if (!s) {
        s = "(null)";
    }
    while (*s) {
        if (append_char(b, cap, n, *s++) != 0) {
            return -1;
        }
    }
    return 0;
}

static int append_dec(char *b, unsigned long cap, unsigned long *n, unsigned long long v)
{
    char tmp[24];
    int k = 0;
    if (v == 0) {
        return append_char(b, cap, n, '0');
    }
    while (v && k < (int)sizeof(tmp)) {
        tmp[k++] = (char)('0' + (v % 10));
        v /= 10;
    }
    while (k > 0) {
        if (append_char(b, cap, n, tmp[--k]) != 0) {
            return -1;
        }
    }
    return 0;
}

static int append_hex64(char *b, unsigned long cap, unsigned long *n, unsigned long long v)
{
    static const char hex[] = "0123456789abcdef";
    int i;
    for (i = 15; i >= 0; i--) {
        if (append_char(b, cap, n, hex[(v >> (i * 4)) & 15]) != 0) {
            return -1;
        }
    }
    return 0;
}

static unsigned long long fnv1a64(const unsigned char *p, unsigned long n)
{
    unsigned long long h = 14695981039346656037ULL;
    unsigned long i;
    for (i = 0; i < n; i++) {
        h ^= (unsigned long long)p[i];
        h *= 1099511628211ULL;
    }
    return h;
}

static int write_all(long fd, const char *b, unsigned long n)
{
    static unsigned long total;
    unsigned long off = 0;
    unsigned int eintr = 0;
    if (total + n > MAX_WRITE_BYTES) {
        return -1;
    }
    while (off < n) {
        long r = sys_write(fd, b + off, n - off);
        if (r > 0) {
            off += (unsigned long)r;
            total += (unsigned long)r;
            continue;
        }
        if (r == -EINTR_NR) {
            if (++eintr > MAX_WRITE_EINTR) {
                return -1;
            }
            continue;
        }
        return -1;
    }
    return 0;
}

static int emit_line(const char *b, unsigned long n)
{
    return write_all(1, b, n);
}

static int b64_append(char *b, unsigned long cap, unsigned long *n,
                      const unsigned char *in, unsigned long len)
{
    static const char t[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    unsigned long i;
    for (i = 0; i < len; i += 3) {
        unsigned long v = (unsigned long)in[i] << 16;
        if (i + 1 < len) {
            v |= (unsigned long)in[i + 1] << 8;
        }
        if (i + 2 < len) {
            v |= (unsigned long)in[i + 2];
        }
        if (append_char(b, cap, n, t[(v >> 18) & 63]) != 0 ||
            append_char(b, cap, n, t[(v >> 12) & 63]) != 0 ||
            append_char(b, cap, n, (i + 1 < len) ? t[(v >> 6) & 63] : '=') != 0 ||
            append_char(b, cap, n, (i + 2 < len) ? t[v & 63] : '=') != 0) {
            return -1;
        }
    }
    return 0;
}

static int emit_begin(long pid, unsigned long long starttime, long seq,
                      const struct fx3_collector_limits *lim)
{
    char b[320];
    unsigned long n = 0;
    if (append_str(b, sizeof(b), &n, "FX3MS2 BEGIN pid=") != 0 ||
        append_dec(b, sizeof(b), &n, (unsigned long long)pid) != 0 ||
        append_str(b, sizeof(b), &n, " starttime=") != 0 ||
        append_dec(b, sizeof(b), &n, starttime) != 0 ||
        append_str(b, sizeof(b), &n, " seq=") != 0 ||
        append_dec(b, sizeof(b), &n, (unsigned long long)seq) != 0 ||
        append_str(b, sizeof(b), &n, " cap=") != 0 ||
        append_dec(b, sizeof(b), &n, (unsigned long long)lim->cap) != 0 ||
        append_str(b, sizeof(b), &n, " max_reads=") != 0 ||
        append_dec(b, sizeof(b), &n, (unsigned long long)lim->max_reads) != 0 ||
        append_str(b, sizeof(b), &n, " max_ms=") != 0 ||
        append_dec(b, sizeof(b), &n, (unsigned long long)lim->max_ms) != 0 ||
        append_str(b, sizeof(b), &n, " capture=bounded_sequential_read\n") != 0) {
        return -1;
    }
    return emit_line(b, n);
}

static int emit_data(long pid, unsigned long long starttime, long seq,
                     unsigned long index, const unsigned char *data, unsigned long len)
{
    char b[640];
    unsigned long n = 0;
    if (append_str(b, sizeof(b), &n, "FX3MS2 DATA ") != 0 ||
        append_dec(b, sizeof(b), &n, (unsigned long long)index) != 0 ||
        append_str(b, sizeof(b), &n, " ") != 0 ||
        append_dec(b, sizeof(b), &n, (unsigned long long)pid) != 0 ||
        append_str(b, sizeof(b), &n, " ") != 0 ||
        append_dec(b, sizeof(b), &n, starttime) != 0 ||
        append_str(b, sizeof(b), &n, " ") != 0 ||
        append_dec(b, sizeof(b), &n, (unsigned long long)seq) != 0 ||
        append_str(b, sizeof(b), &n, " ") != 0 ||
        b64_append(b, sizeof(b), &n, data, len) != 0 ||
        append_char(b, sizeof(b), &n, '\n') != 0) {
        return -1;
    }
    return emit_line(b, n);
}

static int emit_end(long pid, unsigned long long starttime, long seq,
                    const unsigned char *buf, const struct fx3_collector_result *r,
                    const struct fx3_collector_limits *lim)
{
    char b[640];
    unsigned long n = 0;
    unsigned long lines = 0;
    unsigned long i;
    for (i = 0; i < r->bytes; i++) {
        if (buf[i] == (unsigned char)'\n') {
            lines++;
        }
    }
    if (append_str(b, sizeof(b), &n, "FX3MS2 END pid=") != 0 ||
        append_dec(b, sizeof(b), &n, (unsigned long long)pid) != 0 ||
        append_str(b, sizeof(b), &n, " starttime=") != 0 ||
        append_dec(b, sizeof(b), &n, starttime) != 0 ||
        append_str(b, sizeof(b), &n, " seq=") != 0 ||
        append_dec(b, sizeof(b), &n, (unsigned long long)seq) != 0 ||
        append_str(b, sizeof(b), &n, " bytes=") != 0 ||
        append_dec(b, sizeof(b), &n, (unsigned long long)r->bytes) != 0 ||
        append_str(b, sizeof(b), &n, " lines=") != 0 ||
        append_dec(b, sizeof(b), &n, (unsigned long long)lines) != 0 ||
        append_str(b, sizeof(b), &n, " digest=fnv1a64:") != 0 ||
        append_hex64(b, sizeof(b), &n, fnv1a64(buf, r->bytes)) != 0 ||
        append_str(b, sizeof(b), &n, " read_count=") != 0 ||
        append_dec(b, sizeof(b), &n, (unsigned long long)r->read_count) != 0 ||
        append_str(b, sizeof(b), &n, " eintr_count=") != 0 ||
        append_dec(b, sizeof(b), &n, (unsigned long long)r->eintr_count) != 0 ||
        append_str(b, sizeof(b), &n, " read_attempts=") != 0 ||
        append_dec(b, sizeof(b), &n, (unsigned long long)r->read_attempts) != 0 ||
        append_str(b, sizeof(b), &n, " eof_observed=1 identity_before=") != 0 ||
        append_dec(b, sizeof(b), &n, (unsigned long long)pid) != 0 ||
        append_str(b, sizeof(b), &n, ":") != 0 ||
        append_dec(b, sizeof(b), &n, r->starttime_before) != 0 ||
        append_str(b, sizeof(b), &n, " identity_after=") != 0 ||
        append_dec(b, sizeof(b), &n, (unsigned long long)pid) != 0 ||
        append_str(b, sizeof(b), &n, ":") != 0 ||
        append_dec(b, sizeof(b), &n, r->starttime_after) != 0 ||
        append_str(b, sizeof(b), &n, " snapshot_atomic=0 line_terminated=1 complete=1 cap_hit=0 read_limit_hit=0 time_limit_hit=0\n") != 0) {
        return -1;
    }
    (void)lim;
    return emit_line(b, n);
}

static int emit_error(long pid, long seq, const struct fx3_collector_result *r)
{
    char b[480];
    unsigned long n = 0;
    if (append_str(b, sizeof(b), &n, "FX3MS2 ERROR pid=") != 0 ||
        append_dec(b, sizeof(b), &n, (unsigned long long)(pid > 0 ? pid : 0)) != 0 ||
        append_str(b, sizeof(b), &n, " starttime=") != 0 ||
        append_dec(b, sizeof(b), &n, r->starttime_before) != 0 ||
        append_str(b, sizeof(b), &n, " seq=") != 0 ||
        append_dec(b, sizeof(b), &n, (unsigned long long)(seq > 0 ? seq : 0)) != 0 ||
        append_str(b, sizeof(b), &n, " reason=") != 0 ||
        append_str(b, sizeof(b), &n, r->reason ? r->reason : "unknown") != 0 ||
        append_str(b, sizeof(b), &n, " read_count=") != 0 ||
        append_dec(b, sizeof(b), &n, (unsigned long long)r->read_count) != 0 ||
        append_str(b, sizeof(b), &n, " bytes=") != 0 ||
        append_dec(b, sizeof(b), &n, (unsigned long long)r->bytes) != 0 ||
        append_str(b, sizeof(b), &n, " eintr_count=") != 0 ||
        append_dec(b, sizeof(b), &n, (unsigned long long)r->eintr_count) != 0 ||
        append_str(b, sizeof(b), &n, " read_attempts=") != 0 ||
        append_dec(b, sizeof(b), &n, (unsigned long long)r->read_attempts) != 0 ||
        append_str(b, sizeof(b), &n, " elapsed_ms=") != 0 ||
        append_dec(b, sizeof(b), &n, r->elapsed_ms) != 0 ||
        append_char(b, sizeof(b), &n, '\n') != 0) {
        return -1;
    }
    return emit_line(b, n);
}

/* ---- production IO ops ---- */
static int prod_open_dir(void *ctx, long pid, void **dir_out)
{
    char path[64];
    unsigned long n = 0;
    long fd;
    (void)ctx;
    if (pid <= 0) {
        return -1;
    }
    if (append_str(path, sizeof(path), &n, "/proc/") != 0 ||
        append_dec(path, sizeof(path), &n, (unsigned long long)pid) != 0) {
        return -1;
    }
    path[n] = 0;
    fd = sys_openat(AT_FDCWD, path, O_RDONLY | O_DIRECTORY | O_CLOEXEC);
    if (fd < 0) {
        return -1;
    }
    *dir_out = (void *)(long)fd;
    return 0;
}

static int parse_long_token(const char *s, unsigned long len, long *out)
{
    unsigned long i;
    long v = 0;
    if (len == 0 || len > 18) {
        return -1;
    }
    for (i = 0; i < len; i++) {
        if (s[i] < '0' || s[i] > '9') {
            return -1;
        }
        v = v * 10 + (s[i] - '0');
    }
    *out = v;
    return 0;
}

static int parse_stat_identity(const char *buf, unsigned long n, long *pid_out,
                               unsigned long long *start_out)
{
    unsigned long i;
    const char *p;
    const char *end;
    long pid = 0;
    long start = 0;
    int field = 3;
    if (!buf || n == 0) {
        return -1;
    }
    for (i = 0; i < n && buf[i] != ' '; i++) {
        if (buf[i] < '0' || buf[i] > '9') {
            return -1;
        }
        pid = pid * 10 + (buf[i] - '0');
    }
    if (i == 0 || i >= n) {
        return -1;
    }
    end = 0;
    for (i = 0; i < n; i++) {
        if (buf[i] == ')') {
            end = buf + i;
        }
    }
    if (!end) {
        return -1;
    }
    p = end + 1;
    while (p < buf + n) {
        const char *tok;
        unsigned long len;
        while (p < buf + n && *p == ' ') {
            p++;
        }
        if (p >= buf + n) {
            break;
        }
        tok = p;
        while (p < buf + n && *p != ' ') {
            p++;
        }
        len = (unsigned long)(p - tok);
        if (field == 22) {
            if (parse_long_token(tok, len, &start) != 0) {
                return -1;
            }
            *pid_out = pid;
            *start_out = (unsigned long long)(start < 0 ? 0 : start);
            return 0;
        }
        field++;
        if (field > 22) {
            break;
        }
    }
    return -1;
}

static int prod_stat_identity(void *ctx, void *dir, long *pid_out, unsigned long long *start_out)
{
    long dirfd = (long)dir;
    long fd;
    char b[1024];
    long n;
    (void)ctx;
    fd = sys_openat(dirfd, "stat", O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        return -1;
    }
    n = sys_read(fd, b, sizeof(b) - 1);
    (void)sys_close(fd);
    if (n <= 0 || n >= (long)sizeof(b) - 1) {
        return -1;
    }
    b[n] = 0;
    return parse_stat_identity(b, (unsigned long)n, pid_out, start_out);
}

static int prod_open_maps(void *ctx, void *dir, void **maps_out)
{
    long dirfd = (long)dir;
    long fd;
    (void)ctx;
    fd = sys_openat(dirfd, "maps", O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        return -1;
    }
    *maps_out = (void *)(long)fd;
    return 0;
}

static long prod_read_maps(void *ctx, void *maps, unsigned char *buf, unsigned long len)
{
    long fd = (long)maps;
    long r;
    (void)ctx;
    r = sys_read(fd, buf, len);
    if (r == -EINTR_NR) {
        return FX3_READ_EINTR;
    }
    if (r < 0) {
        return FX3_READ_ERROR;
    }
    return r;
}

static int prod_close_maps(void *ctx, void *maps)
{
    (void)ctx;
    return (int)sys_close((long)maps);
}

static int prod_close_dir(void *ctx, void *dir)
{
    (void)ctx;
    return (int)sys_close((long)dir);
}

static int prod_now_ms(void *ctx, unsigned long long *out_ms)
{
    (void)ctx;
    return mono_ms(out_ms);
}

static unsigned char maps_buf[FX3_COLLECTOR_CAP];

static int parse_arg(const char *s, long *out, long lo, long hi)
{
    long v = 0;
    int any = 0;
    if (!s) {
        return -1;
    }
    while (*s) {
        if (*s < '0' || *s > '9') {
            return -1;
        }
        v = v * 10 + (*s - '0');
        if (v > hi) {
            return -1;
        }
        any = 1;
        s++;
    }
    if (!any || v < lo || v > hi) {
        return -1;
    }
    *out = v;
    return 0;
}

__attribute__((noreturn)) static void start_exit(long code)
{
    sys_exit(code);
}

__attribute__((naked, noreturn, used)) void _start(void)
{
    __asm__ __volatile__(
        "mov x3, sp\n"
        "ldr x0, [x3]\n"
        "add x1, x3, #8\n"
        "bl main\n"
        "mov x8, #93\n"
        "svc #0\n");
}

int main(long argc, char **argv)
{
    struct fx3_collector_limits lim;
    struct fx3_collector_result r;
    struct fx3_collector_ops ops;
    long pid = 0;
    long seq = 0;
    unsigned long off;
    unsigned long index = 0;

    if (argc != 3) {
        return 2;
    }
    if (parse_arg(argv[1], &pid, 1, 2147483647L) != 0 ||
        parse_arg(argv[2], &seq, 0, 2147483647L) != 0) {
        return 2;
    }

    lim.cap = FX3_COLLECTOR_CAP;
    lim.max_reads = FX3_COLLECTOR_MAX_READS;
    lim.max_ms = FX3_COLLECTOR_MAX_MS;
    lim.max_eintr_per_read = FX3_COLLECTOR_MAX_EINTR_PER_READ;
    lim.max_eintr_total = FX3_COLLECTOR_MAX_EINTR_TOTAL;

    ops.ctx = 0;
    ops.open_dir = prod_open_dir;
    ops.stat_identity = prod_stat_identity;
    ops.open_maps = prod_open_maps;
    ops.read_maps = prod_read_maps;
    ops.close_maps = prod_close_maps;
    ops.close_dir = prod_close_dir;
    ops.now_ms = prod_now_ms;

    if (!fx3_collect(&ops, &lim, pid, maps_buf, &r)) {
        if (emit_error(pid, seq, &r) != 0) {
            start_exit(6);
        }
        start_exit(4);
    }

    if (emit_begin(pid, r.starttime_before, seq, &lim) != 0) {
        start_exit(6);
    }
    for (off = 0; off < r.bytes; off += BASE64_CHUNK) {
        unsigned long n = r.bytes - off;
        if (n > BASE64_CHUNK) {
            n = BASE64_CHUNK;
        }
        if (emit_data(pid, r.starttime_before, seq, index++, maps_buf + off, n) != 0) {
            start_exit(6);
        }
    }
    if (emit_end(pid, r.starttime_before, seq, maps_buf, &r, &lim) != 0) {
        start_exit(6);
    }
    start_exit(0);
}
