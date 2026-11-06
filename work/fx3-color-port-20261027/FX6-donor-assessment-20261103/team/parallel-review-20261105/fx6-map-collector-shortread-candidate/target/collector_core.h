#ifndef FX3_COLLECTOR_CORE_H
#define FX3_COLLECTOR_CORE_H

/* Explicit, reviewed bounds.  The 262144-byte cap is unchanged from the
 * previous diagnostic package: the observed im.elf maps block is far smaller
 * (~43.5 KiB in the accepted r6 serial), and the failure was a short seq_file
 * read followed by more data, not cap exhaustion. */
#define FX3_COLLECTOR_CAP 262144UL
#define FX3_COLLECTOR_MAX_READS 64U
#define FX3_COLLECTOR_MAX_MS 1000U
#define FX3_COLLECTOR_READ_CHUNK 65536U
#define FX3_COLLECTOR_MAX_EINTR_PER_READ 8U
#define FX3_COLLECTOR_MAX_EINTR_TOTAL 32U

#define FX3_READ_EINTR (-1L)
#define FX3_READ_ERROR (-2L)

struct fx3_collector_ops {
    void *ctx;
    int (*open_dir)(void *ctx, long pid, void **dir_out);
    int (*stat_identity)(void *ctx, void *dir, long *pid_out, unsigned long long *start_out);
    int (*open_maps)(void *ctx, void *dir, void **maps_out);
    /* >0 bytes read, 0 EOF, FX3_READ_EINTR, FX3_READ_ERROR */
    long (*read_maps)(void *ctx, void *maps, unsigned char *buf, unsigned long len);
    int (*close_maps)(void *ctx, void *maps);
    int (*close_dir)(void *ctx, void *dir);
    /* Returns 0 and stores monotonic milliseconds, or -1 on error.  A missing
     * callback is a hard failure, never an implicit zero clock. */
    int (*now_ms)(void *ctx, unsigned long long *out_ms);
};

struct fx3_collector_limits {
    unsigned long cap;
    unsigned int max_reads;
    unsigned int max_ms;
    unsigned int max_eintr_per_read;
    unsigned int max_eintr_total;
};

struct fx3_collector_result {
    int ok;
    const char *reason;              /* static string; no allocation */
    long pid;
    unsigned long long starttime_before;
    unsigned long long starttime_after;
    unsigned long bytes;
    unsigned int read_count;         /* reads that returned data */
    unsigned int eintr_count;
    unsigned int read_attempts;      /* every read() call incl. EOF/EINTR */
    unsigned long long elapsed_ms;
    int eof_observed;
    int line_terminated;
    int identity_stable;
    int cap_hit;
    int read_limit_hit;
    int time_limit_hit;
    int eintr_limit_hit;
    int clock_missing;
    int clock_error;
    int clock_backwards;
};

/* Reads /proc/<pid>/maps from one /proc/<pid> directory, one read at a time,
 * until EOF, under the explicit byte/read/time/EINTR bounds.  The returned
 * buffer is a complete byte stream, not an atomic kernel snapshot.
 *
 * Clock policy: missing/error/backwards clocks fail closed.  Deadline checks
 * run before a read and after each syscall/identity operation.  A blocking
 * read/open/stat syscall cannot be interrupted by polling the deadline; the
 * max_ms bound is therefore checked around the calls, not enforced during a
 * blocked call.  The host observation deadline remains the outer bound. */
int fx3_collect(struct fx3_collector_ops *ops,
                const struct fx3_collector_limits *lim,
                long pid,
                unsigned char *buf,
                struct fx3_collector_result *out);

#endif
