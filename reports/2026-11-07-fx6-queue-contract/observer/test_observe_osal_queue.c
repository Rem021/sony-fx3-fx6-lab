/* Host fixture for argument/return/errno preservation; never controls a VM. */
#include <assert.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct { const char *fname; void *base; const char *sname; void *saddr; } obs_dl_info;
typedef struct { long sec; long nsec; } obs_timespec;
extern int osal_rcv_msg_tmo(unsigned int, void **, int);
static int fake_errno, expected_errno, next_errno, next_result, calls, missing, self;
static unsigned int expected_qid;
static int expected_timeout;
static void **expected_out;
static unsigned long caller_offset = 0xc0a20cUL;
static char logs[16000];

static int real_receive(unsigned int qid, void **out, int timeout) {
    assert(qid == expected_qid && out == expected_out && timeout == expected_timeout);
    assert(fake_errno == expected_errno);
    ++calls;
    if (next_result == 0 && out) *out = (void *)0xabcdUL;
    fake_errno = next_errno;
    return next_result;
}
int *fx6_test_errno_location(void) { return &fake_errno; }
char *fx6_test_dlerror(void) { fake_errno = 999; return NULL; }
void *fx6_test_dlsym(void *handle, const char *name) {
    assert(handle == (void *)-1L && strcmp(name, "osal_rcv_msg_tmo") == 0);
    fake_errno = 999;
    return missing ? NULL : self ? (void *)&osal_rcv_msg_tmo : (void *)&real_receive;
}
int fx6_test_dladdr(const void *addr, obs_dl_info *info) {
    fake_errno = 999;
    if (addr == (void *)&real_receive) {
        info->fname = "/usr/lib/libosal_uipc.so";
        info->base = (void *)addr;
    } else {
        info->fname = "/usr/lib/appFw.so";
        info->base = (void *)((unsigned long)addr - caller_offset);
    }
    return 1;
}
long fx6_test_syscall(long number, ...) { assert(number == 178); fake_errno = 999; return 225; }
int fx6_test_clock_gettime(int clock, obs_timespec *t) {
    assert(clock == 1); t->sec = 10; t->nsec = 20; fake_errno = 999; return 0;
}
int fx6_test_dprintf(int fd, const char *format, ...) {
    assert(fd == 2); va_list ap; va_start(ap, format);
    size_t used = strlen(logs); int n = vsnprintf(logs + used, sizeof logs - used, format, ap);
    va_end(ap); fake_errno = 999; return n;
}
void fx6_test_exit(int code) { _Exit(code); }

int main(int argc, char **argv) {
    if (argc > 1) { missing = strcmp(argv[1], "missing") == 0; self = !missing; }
    void *slot = (void *)0xdeadUL;
    expected_qid = 0x5503e0; expected_timeout = -1; expected_out = &slot;
    expected_errno = fake_errno = 777; next_errno = 123; next_result = 0;
    assert(osal_rcv_msg_tmo(expected_qid, &slot, -1) == 0 && slot == (void *)0xabcdUL && fake_errno == 123);
    assert(strstr(logs, "site=app_event_loop") && strstr(logs, "qid=0x5503e0 timeout=-1"));
    slot = (void *)0xdeadUL; expected_qid = 0x123; expected_timeout = 0;
    expected_errno = fake_errno = 345; next_errno = 456; next_result = -1020; caller_offset = 0x20efbbcUL;
    assert(osal_rcv_msg_tmo(expected_qid, &slot, 0) == -1020 && slot == (void *)0xdeadUL && fake_errno == 456);
    assert(strstr(logs, "site=bb_finalize") && strstr(logs, "rc=-1020 errno=456"));
    expected_out = NULL; expected_timeout = 37; expected_errno = fake_errno = 91;
    next_errno = 92; next_result = 42;
    assert(osal_rcv_msg_tmo(expected_qid, NULL, 37) == 42 && fake_errno == 92);
    assert(calls == 3 && strstr(logs, "seq=3") && strstr(logs, "target=/usr/lib/libosal_uipc.so"));
    puts("observer host fixture passed: arguments, output ownership, return values, errno, caller classification");
    return 0;
}
