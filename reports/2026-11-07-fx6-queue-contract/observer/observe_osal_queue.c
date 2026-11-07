/* Observation candidate, not integrated into any VM.
 * Verified ABI: libosal_uipc.so fe248d226863722b2ab911ca70195c616566b8cb96a2ab13b920ee25202a7b9a.
 * Records LR/qid/TID before the real wait; never reads or changes *out.
 * No timeout conversion, fake completion, queue deletion or memory patches.
 */
#if !defined(FX6_QUEUE_OBSERVER_TEST) && (!defined(__linux__) || !defined(__aarch64__))
#error "Production observer is for AArch64 Linux only"
#endif

#ifdef FX6_QUEUE_OBSERVER_TEST
#define dlsym fx6_test_dlsym
#define dlerror fx6_test_dlerror
#define dladdr fx6_test_dladdr
#define dprintf fx6_test_dprintf
#define syscall fx6_test_syscall
#define clock_gettime fx6_test_clock_gettime
#define __errno_location fx6_test_errno_location
#define _exit fx6_test_exit
#endif

typedef unsigned long uptr;
typedef struct { const char *fname; void *base; const char *sname; void *saddr; } obs_dl_info;
typedef struct { long sec; long nsec; } obs_timespec;
typedef int (*receive_fn)(unsigned int, void **, int);
extern void *dlsym(void *, const char *);
extern char *dlerror(void);
extern int dladdr(const void *, obs_dl_info *);
extern int dprintf(int, const char *, ...);
extern long syscall(long, ...);
extern int clock_gettime(int, obs_timespec *);
extern int *__errno_location(void);
extern void _exit(int) __attribute__((noreturn));

static void *resolved_receive;
static unsigned int serial_sequence;

int osal_rcv_msg_tmo(unsigned int qid, void **out, int timeout);

static int equal(const char *a, const char *b) {
    if (!a || !b) return 0;
    while (*a && *a == *b) { ++a; ++b; }
    return *a == *b;
}

static const char *basename_of(const char *p) {
    const char *base = p;
    if (!p) return "?";
    while (*p) { if (*p == '/') base = p + 1; ++p; }
    return base;
}

static const char *classify(const obs_dl_info *info, uptr offset) {
    if (!equal(basename_of(info->fname), "appFw.so")) return "other_dso";
    switch (offset) {
    case 0x20efbbcUL: return "bb_finalize";
    case 0x20f80f8UL: return "bb_worker";
    case 0x20ef7ccUL: return "bb_request_reply";
    case 0x20ef554UL: return "bb_temp_queue_drain";
    case 0xc0a20cUL: return "app_event_loop";
    default: return "other_appfw";
    }
}

static receive_fn resolve_receive(void) {
    void *p = __atomic_load_n(&resolved_receive, __ATOMIC_ACQUIRE);
    if (!p) {
        (void)dlerror();
        p = dlsym((void *)-1L, "osal_rcv_msg_tmo"); /* Linux RTLD_NEXT */
        const char *error = dlerror();
        if (error || !p || p == (void *)&osal_rcv_msg_tmo) {
            dprintf(2, "FX6_QUEUE_OBS_RESOLVE_FAILED error=%s\n", error ? error : "null_or_self");
            _exit(126); /* Never manufacture a successful receive. */
        }
        __atomic_store_n(&resolved_receive, p, __ATOMIC_RELEASE);
    }
    return (receive_fn)p;
}

int osal_rcv_msg_tmo(unsigned int qid, void **out, int timeout) {
    int *errno_slot = __errno_location();
    int incoming_errno = *errno_slot;
    receive_fn real = resolve_receive();
    unsigned int sequence = __atomic_add_fetch(&serial_sequence, 1U, __ATOMIC_RELAXED);
    int capture = sequence <= 1024U;
    obs_dl_info caller_info = {0}, target_info = {0};
    obs_timespec when = {0};
    void *caller = __builtin_return_address(0);
    uptr offset = 0;
    long tid = 0;
    if (capture) {
        dladdr(caller, &caller_info);
        dladdr((void *)real, &target_info);
        if (caller_info.base) offset = (uptr)caller - (uptr)caller_info.base;
        tid = syscall(178L); /* AArch64 Linux __NR_gettid */
        clock_gettime(1, &when); /* CLOCK_MONOTONIC */
        dprintf(2, "FX6_QUEUE_OBS_ENTER seq=%u tid=%ld t=%ld.%09ld lr=%p caller=%s+0x%lx site=%s qid=0x%x timeout=%d outslot=%p target=%s@%p\n",
                sequence, tid, when.sec, when.nsec, caller,
                caller_info.fname ? caller_info.fname : "?", offset,
                classify(&caller_info, offset), qid, timeout, (void *)out,
                target_info.fname ? target_info.fname : "?", (void *)real);
    } else if (sequence == 1025U) {
        dprintf(2, "FX6_QUEUE_OBS_LIMIT entries=1024 forwarding_continues=1\n");
    }
    *errno_slot = incoming_errno;
    int result = real(qid, out, timeout);
    int returned_errno = *errno_slot;
    if (capture) {
        clock_gettime(1, &when);
        dprintf(2, "FX6_QUEUE_OBS_EXIT seq=%u tid=%ld t=%ld.%09ld rc=%d errno=%d\n",
                sequence, tid, when.sec, when.nsec, result, returned_errno);
    }
    *errno_slot = returned_errno;
    return result;
}
