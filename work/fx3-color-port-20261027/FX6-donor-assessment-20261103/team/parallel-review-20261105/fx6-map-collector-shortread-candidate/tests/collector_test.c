/* Native offline fixture tests for the shared collector state machine.
 * This binary runs on the host only; it does not execute the AArch64 target.
 */
#include <stdio.h>
#include <string.h>
#include "collector_core.h"

struct fake {
    const unsigned char *data;
    unsigned long len;
    unsigned long off;
    const unsigned long *chunks;
    unsigned int chunk_count;
    unsigned int chunk_i;
    unsigned int eintr_left;
    unsigned int reads;
    unsigned long long clock;
    long before_pid;
    long after_pid;
    unsigned long long before_st;
    unsigned long long after_st;
    int stat_calls;
    int fail_open_dir;
    int fail_open_maps;
    int fail_stat_before;
    int fail_stat_after;
    int read_error;
    int clock_error;
    int clock_backwards;
    unsigned long long clock_after_bump;
    unsigned long long first_now;
    unsigned int now_calls;
};

static int f_open_dir(void *ctx, long pid, void **dir)
{
    struct fake *f = (struct fake *)ctx;
    (void)pid;
    if (f->fail_open_dir) {
        return -1;
    }
    *dir = f;
    return 0;
}

static int f_stat(void *ctx, void *dir, long *pid, unsigned long long *st)
{
    struct fake *f = (struct fake *)ctx;
    (void)dir;
    f->stat_calls++;
    if (f->stat_calls == 1) {
        if (f->fail_stat_before) {
            return -1;
        }
        *pid = f->before_pid;
        *st = f->before_st;
    } else {
        if (f->fail_stat_after) {
            return -1;
        }
        *pid = f->after_pid;
        *st = f->after_st;
        f->clock += f->clock_after_bump;
    }
    return 0;
}

static int f_open_maps(void *ctx, void *dir, void **maps)
{
    struct fake *f = (struct fake *)ctx;
    (void)dir;
    if (f->fail_open_maps) {
        return -1;
    }
    *maps = f;
    return 0;
}

static long f_read(void *ctx, void *maps, unsigned char *buf, unsigned long len)
{
    struct fake *f = (struct fake *)ctx;
    unsigned long n;
    (void)maps;
    f->reads++;
    if (f->eintr_left) {
        f->eintr_left--;
        return FX3_READ_EINTR;
    }
    if (f->read_error) {
        return FX3_READ_ERROR;
    }
    if (f->off >= f->len) {
        return 0;
    }
    n = f->len - f->off;
    if (f->chunk_i < f->chunk_count) {
        if (f->chunks[f->chunk_i] < n) {
            n = f->chunks[f->chunk_i];
        }
        f->chunk_i++;
    }
    if (n > len) {
        n = len;
    }
    memcpy(buf, f->data + f->off, n);
    f->off += n;
    f->clock += 100;
    return (long)n;
}

static int f_close(void *ctx, void *h)
{
    (void)ctx;
    (void)h;
    return 0;
}

static int f_now(void *ctx, unsigned long long *out)
{
    struct fake *f = (struct fake *)ctx;
    if (f->clock_error) {
        return -1;
    }
    f->now_calls++;
    if (f->clock_backwards && f->now_calls > 1) {
        *out = f->first_now - 1;
        return 0;
    }
    if (f->now_calls == 1) {
        f->first_now = f->clock;
    }
    *out = f->clock;
    return 0;
}

static int run_case(const char *name, const unsigned char *data, unsigned long len,
                    const unsigned long *chunks, unsigned int chunk_count,
                    struct fx3_collector_limits lim, unsigned int eintr_left,
                    long before_pid, long after_pid, unsigned long long before_st,
                    unsigned long long after_st, int fail_open_dir, int fail_open_maps,
                    int fail_stat_before, int fail_stat_after, int read_error,
                    int expect_ok, const char *expect_reason)
{
    struct fake f;
    struct fx3_collector_ops ops;
    struct fx3_collector_result r;
    unsigned char buf[65536];
    int ok;
    memset(&f, 0, sizeof(f));
    f.data = data;
    f.len = len;
    f.chunks = chunks;
    f.chunk_count = chunk_count;
    f.eintr_left = eintr_left;
    f.before_pid = before_pid;
    f.after_pid = after_pid;
    f.before_st = before_st;
    f.after_st = after_st;
    f.fail_open_dir = fail_open_dir;
    f.fail_open_maps = fail_open_maps;
    f.fail_stat_before = fail_stat_before;
    f.fail_stat_after = fail_stat_after;
    f.read_error = read_error;
    ops.ctx = &f;
    ops.open_dir = f_open_dir;
    ops.stat_identity = f_stat;
    ops.open_maps = f_open_maps;
    ops.read_maps = f_read;
    ops.close_maps = f_close;
    ops.close_dir = f_close;
    ops.now_ms = f_now;
    ok = fx3_collect(&ops, &lim, 237, buf, &r);
    if (ok != expect_ok) {
        printf("FAIL %s ok=%d expect=%d reason=%s\n", name, ok, expect_ok, r.reason);
        return 1;
    }
    if (!expect_ok && strcmp(r.reason, expect_reason) != 0) {
        printf("FAIL %s reason=%s expect=%s\n", name, r.reason, expect_reason);
        return 1;
    }
    if (expect_ok) {
        if (r.bytes != len || memcmp(buf, data, len) != 0 || !r.eof_observed ||
            !r.line_terminated || !r.identity_stable ||
            r.read_attempts != r.read_count + r.eintr_count + 1) {
            printf("FAIL %s success invariants bytes=%lu/%lu rc=%u ea=%u ra=%u eof=%d lt=%d id=%d\n",
                   name, r.bytes, len, r.read_count, r.eintr_count, r.read_attempts,
                   r.eof_observed, r.line_terminated, r.identity_stable);
            return 1;
        }
    }
    printf("PASS %s ok=%d reason=%s bytes=%lu reads=%u eintr=%u attempts=%u\n",
           name, ok, r.reason, r.bytes, r.read_count, r.eintr_count, r.read_attempts);
    return 0;
}

static int run_clock_case(const char *name, const unsigned char *data, unsigned long len,
                         int missing, int error, int backwards, unsigned long long bump,
                         const char *expect_reason)
{
    struct fake f;
    struct fx3_collector_ops ops;
    struct fx3_collector_result r;
    struct fx3_collector_limits lim;
    unsigned char buf[8192];
    int ok;
    memset(&f, 0, sizeof(f));
    f.data = data;
    f.len = len;
    f.before_pid = 237;
    f.after_pid = 237;
    f.before_st = 100;
    f.after_st = 100;
    f.clock = 100;
    f.clock_error = error;
    f.clock_backwards = backwards;
    f.clock_after_bump = bump;
    lim.cap = 4096;
    lim.max_reads = 64;
    lim.max_ms = 1000;
    lim.max_eintr_per_read = 8;
    lim.max_eintr_total = 32;
    ops.ctx = &f;
    ops.open_dir = f_open_dir;
    ops.stat_identity = f_stat;
    ops.open_maps = f_open_maps;
    ops.read_maps = f_read;
    ops.close_maps = f_close;
    ops.close_dir = f_close;
    ops.now_ms = missing ? NULL : f_now;
    ok = fx3_collect(&ops, &lim, 237, buf, &r);
    if (ok != 0 || !r.reason || strcmp(r.reason, expect_reason) != 0) {
        printf("FAIL %s ok=%d reason=%s expect=%s\n", name, ok, r.reason ? r.reason : "(null)", expect_reason);
        return 1;
    }
    printf("PASS %s reason=%s elapsed=%llu\n", name, r.reason, r.elapsed_ms);
    return 0;
}

int main(void)
{
    static const unsigned char payload[] =
        "00400000-00401000 r-xp 00000000 00:01 42 /usr/lib/appFw.so\n"
        "00401000-00402000 rw-p 00001000 00:01 42 /usr/lib/appFw.so\n"
        "7f000000-7f001000 r-xp 00000000 00:01 43 /usr/bin/im.elf\n"
        "7f001000-7f002000 rw-p 00001000 00:01 43 /usr/bin/im.elf\n";
    static const unsigned long chunks1[] = {3, 7, 1000};
    static const unsigned long chunks_split[] = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12};
    static const unsigned long chunks_limit[] = {1, 1, 1};
    struct fx3_collector_limits lim;
    int fails = 0;
    int total = 18;
    unsigned long len = sizeof(payload) - 1;

    lim.cap = 4096;
    lim.max_reads = 64;
    lim.max_ms = 1000;
    lim.max_eintr_per_read = 8;
    lim.max_eintr_total = 32;
    {
        struct fx3_collector_limits lim_split = lim;
        lim_split.max_ms = 10000;
        fails += run_case("split_lines_arbitrary", payload, len, chunks_split, 12, lim_split, 0, 237, 237, 100, 100, 0, 0, 0, 0, 0, 1, NULL);
    }

    fails += run_case("shortread_moredata", payload, len, chunks1, 3, lim, 0, 237, 237, 100, 100, 0, 0, 0, 0, 0, 1, NULL);
    fails += run_case("eintr_8_then_data", payload, len, NULL, 0, lim, 8, 237, 237, 100, 100, 0, 0, 0, 0, 0, 1, NULL);
    fails += run_case("eintr_limit_9", payload, len, NULL, 0, lim, 9, 237, 237, 100, 100, 0, 0, 0, 0, 0, 0, "eintr_limit");
    fails += run_case("eintr_total_limit", payload, len, NULL, 0, lim, 33, 237, 237, 100, 100, 0, 0, 0, 0, 0, 0, "eintr_limit");
    lim.max_eintr_per_read = 100;
    lim.max_eintr_total = 3;
    fails += run_case("eintr_total_limit_small", payload, len, NULL, 0, lim, 4, 237, 237, 100, 100, 0, 0, 0, 0, 0, 0, "eintr_limit");
    lim.max_eintr_per_read = 8;
    lim.max_eintr_total = 32;
    lim.cap = 16;
    fails += run_case("cap_exceeded", payload, len, NULL, 0, lim, 0, 237, 237, 100, 100, 0, 0, 0, 0, 0, 0, "cap_exceeded");
    lim.cap = 4096;
    lim.max_reads = 2;
    fails += run_case("read_limit", payload, len, chunks_limit, 3, lim, 0, 237, 237, 100, 100, 0, 0, 0, 0, 0, 0, "read_limit");
    lim.max_reads = 64;
    lim.max_ms = 50;
    fails += run_case("time_limit", payload, len, NULL, 0, lim, 0, 237, 237, 100, 100, 0, 0, 0, 0, 0, 0, "time_limit");
    lim.max_ms = 1000;
    fails += run_case("pid_change_after", payload, len, NULL, 0, lim, 0, 237, 238, 100, 100, 0, 0, 0, 0, 0, 0, "pid_mismatch_after");
    fails += run_case("starttime_change_after", payload, len, NULL, 0, lim, 0, 237, 237, 100, 101, 0, 0, 0, 0, 0, 0, "identity_changed");
    fails += run_case("read_error", payload, len, NULL, 0, lim, 0, 237, 237, 100, 100, 0, 0, 0, 0, 1, 0, "read_error");
    fails += run_case("empty_maps", payload, 0, NULL, 0, lim, 0, 237, 237, 100, 100, 0, 0, 0, 0, 0, 0, "empty_maps");
    fails += run_case("unterminated", payload, 5, NULL, 0, lim, 0, 237, 237, 100, 100, 0, 0, 0, 0, 0, 0, "unterminated_maps");
    fails += run_case("open_proc_fail", payload, len, NULL, 0, lim, 0, 237, 237, 100, 100, 1, 0, 0, 0, 0, 0, "open_proc_pid");
    fails += run_case("open_maps_fail", payload, len, NULL, 0, lim, 0, 237, 237, 100, 100, 0, 1, 0, 0, 0, 0, "open_maps");
    fails += run_case("stat_before_fail", payload, len, NULL, 0, lim, 0, 237, 237, 100, 100, 0, 0, 1, 0, 0, 0, "stat_before_error");
    fails += run_case("stat_after_fail", payload, len, NULL, 0, lim, 0, 237, 237, 100, 100, 0, 0, 0, 1, 0, 0, "stat_after_error");

    {
        FILE *fp = fopen("fixtures/native-target-frame-v2.maps", "rb");
        if (fp) {
            static unsigned char actual[131072];
            static const unsigned long chunks_actual[] = {
                1024, 1024, 1024, 1024, 1024, 1024, 1024, 1024,
                1024, 1024, 1024, 1024, 1024, 1024, 1024, 1024
            };
            size_t got = fread(actual, 1, sizeof(actual), fp);
            fclose(fp);
            if (got > 0) {
                struct fx3_collector_limits lim_actual = lim;
                lim_actual.cap = 262144;
                lim_actual.max_reads = 64;
                lim_actual.max_ms = 10000;
                fails += run_case("actual_maps_payload_split1024_eintr8", actual, (unsigned long)got,
                                  chunks_actual, 16, lim_actual, 8, 237, 237, 100, 100,
                                  0, 0, 0, 0, 0, 1, NULL);
                total++;
            }
        }
    }

    fails += run_clock_case("clock_missing", (const unsigned char *)"line\n", 5, 1, 0, 0, 0, "clock_missing");
    fails += run_clock_case("clock_error", (const unsigned char *)"line\n", 5, 0, 1, 0, 0, "clock_error");
    fails += run_clock_case("clock_backwards", (const unsigned char *)"line\n", 5, 0, 0, 1, 0, "clock_backwards");
    fails += run_clock_case("identity_after_timeout", (const unsigned char *)"line\n", 5, 0, 0, 0, 2000, "time_limit");
    total += 4;

    printf("CASES_TOTAL=%d FAILS=%d\n", total, fails);
    return fails ? 1 : 0;
}
