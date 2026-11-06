#include "collector_core.h"

static void fail(struct fx3_collector_result *o, const char *reason)
{
    o->ok = 0;
    o->reason = reason;
}

static int read_now(struct fx3_collector_ops *ops, struct fx3_collector_result *o,
                    unsigned long long *now)
{
    if (!ops->now_ms) {
        o->clock_missing = 1;
        fail(o, "clock_missing");
        return -1;
    }
    if (ops->now_ms(ops->ctx, now) != 0) {
        o->clock_error = 1;
        fail(o, "clock_error");
        return -1;
    }
    return 0;
}

static int check_clock(struct fx3_collector_ops *ops,
                       const struct fx3_collector_limits *lim,
                       struct fx3_collector_result *o,
                       unsigned long long *last,
                       unsigned long long t0)
{
    unsigned long long now = 0;
    if (read_now(ops, o, &now) != 0) {
        return -1;
    }
    if (now < *last) {
        o->clock_backwards = 1;
        fail(o, "clock_backwards");
        return -1;
    }
    *last = now;
    o->elapsed_ms = now - t0;
    if (o->elapsed_ms > (unsigned long long)lim->max_ms) {
        o->time_limit_hit = 1;
        fail(o, "time_limit");
        return -1;
    }
    return 0;
}

int fx3_collect(struct fx3_collector_ops *ops,
                const struct fx3_collector_limits *lim,
                long pid,
                unsigned char *buf,
                struct fx3_collector_result *out)
{
    void *dir = 0;
    void *maps = 0;
    int dir_open = 0;
    int maps_open = 0;
    unsigned long long t0 = 0;
    unsigned long long last_now = 0;
    unsigned int eintr_this_read = 0;
    long before_pid = 0;
    long after_pid = 0;
    unsigned long long before_st = 0;
    unsigned long long after_st = 0;

    *out = (struct fx3_collector_result){0};
    out->pid = pid;
    out->reason = "init";

    if (!ops || !lim || !buf || pid <= 0 || lim->cap == 0 || lim->max_reads == 0 ||
        lim->max_ms == 0 || lim->max_eintr_per_read == 0 || lim->max_eintr_total == 0) {
        fail(out, "bad_args");
        return 0;
    }
    if (!ops->open_dir || !ops->stat_identity || !ops->open_maps || !ops->read_maps) {
        fail(out, "missing_ops");
        return 0;
    }
    if (!ops->now_ms) {
        out->clock_missing = 1;
        fail(out, "clock_missing");
        return 0;
    }
    if (ops->now_ms(ops->ctx, &t0) != 0) {
        out->clock_error = 1;
        fail(out, "clock_error");
        return 0;
    }
    last_now = t0;

    if (ops->open_dir(ops->ctx, pid, &dir) != 0) {
        fail(out, "open_proc_pid");
        goto done;
    }
    dir_open = 1;
    if (check_clock(ops, lim, out, &last_now, t0) != 0) {
        goto done;
    }

    if (ops->stat_identity(ops->ctx, dir, &before_pid, &before_st) != 0) {
        fail(out, "stat_before_error");
        goto done;
    }
    if (check_clock(ops, lim, out, &last_now, t0) != 0) {
        goto done;
    }
    out->starttime_before = before_st;
    if (before_pid != pid) {
        fail(out, "pid_mismatch_before");
        goto done;
    }

    if (ops->open_maps(ops->ctx, dir, &maps) != 0) {
        fail(out, "open_maps");
        goto done;
    }
    maps_open = 1;
    if (check_clock(ops, lim, out, &last_now, t0) != 0) {
        goto done;
    }

    for (;;) {
        unsigned long rem;
        unsigned long want;
        long r;

        if (check_clock(ops, lim, out, &last_now, t0) != 0) {
            goto done;
        }

        rem = lim->cap - out->bytes;
        if (rem == 0) {
            out->cap_hit = 1;
            fail(out, "cap_exceeded");
            goto done;
        }
        want = (rem > (unsigned long)FX3_COLLECTOR_READ_CHUNK) ? (unsigned long)FX3_COLLECTOR_READ_CHUNK : rem;

        r = ops->read_maps(ops->ctx, maps, buf + out->bytes, want);
        out->read_attempts++;

        /* A blocking read cannot be interrupted by this check; this is a
         * post-syscall deadline check, not a preemption mechanism. */
        if (check_clock(ops, lim, out, &last_now, t0) != 0) {
            goto done;
        }

        if (r > 0) {
            if ((unsigned long)r > rem) {
                fail(out, "read_overflow");
                goto done;
            }
            if (out->read_count >= lim->max_reads) {
                out->read_limit_hit = 1;
                fail(out, "read_limit");
                goto done;
            }
            out->bytes += (unsigned long)r;
            out->read_count++;
            eintr_this_read = 0;
            if (out->bytes >= lim->cap) {
                out->cap_hit = 1;
                fail(out, "cap_exceeded");
                goto done;
            }
            continue;
        }

        if (r == 0) {
            out->eof_observed = 1;
            break;
        }

        if (r == FX3_READ_EINTR) {
            out->eintr_count++;
            eintr_this_read++;
            if (eintr_this_read > lim->max_eintr_per_read ||
                out->eintr_count > lim->max_eintr_total) {
                out->eintr_limit_hit = 1;
                fail(out, "eintr_limit");
                goto done;
            }
            continue;
        }

        fail(out, "read_error");
        goto done;
    }

    if (check_clock(ops, lim, out, &last_now, t0) != 0) {
        goto done;
    }
    if (ops->stat_identity(ops->ctx, dir, &after_pid, &after_st) != 0) {
        fail(out, "stat_after_error");
        goto done;
    }
    /* Recheck the deadline after the post-read identity operation. */
    if (check_clock(ops, lim, out, &last_now, t0) != 0) {
        goto done;
    }
    out->starttime_after = after_st;
    if (after_pid != pid) {
        fail(out, "pid_mismatch_after");
        goto done;
    }
    if (before_pid != after_pid || before_st != after_st) {
        fail(out, "identity_changed");
        goto done;
    }
    if (out->bytes == 0) {
        fail(out, "empty_maps");
        goto done;
    }
    if (buf[out->bytes - 1] != (unsigned char)'\n') {
        fail(out, "unterminated_maps");
        goto done;
    }
    if (check_clock(ops, lim, out, &last_now, t0) != 0) {
        goto done;
    }

    out->identity_stable = 1;
    out->line_terminated = 1;
    out->ok = 1;
    out->reason = "ok";

done:
    if (maps_open && ops->close_maps) {
        (void)ops->close_maps(ops->ctx, maps);
    }
    if (dir_open && ops->close_dir) {
        (void)ops->close_dir(ops->ctx, dir);
    }
    return out->ok;
}
