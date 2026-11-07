/* Offline observation candidate only. Not built into a CPIO or run.
 * Forward every native call; do not create MonCtrl objects or suppress NULL.
 * ABI: FX6 native libMWF.so sha256 3c9666c49bde90076cf69af13295dc07e585d87c51a27ecaf7f1926df87d1782.
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const char *basename_of(const char *path) {
    const char *p = path ? strrchr(path, '/') : NULL;
    return p ? p + 1 : path;
}

static void *must_resolve(const char *symbol) {
    void *p = dlsym(RTLD_NEXT, symbol);
    if (!p) {
        dprintf(2, "FX6_MWF_OBSERVER_RESOLVE_FAILED symbol=%s\n", symbol);
        abort(); /* Never synthesize success if the expected ABI is absent. */
    }
    return p;
}

static void report_state(const char *phase, void *caller, const void *self) {
    int saved_errno = errno;
    Dl_info di = {0};
    dladdr(caller, &di);
    static const char *const symbols[] = {
        "_ZN3MWF6RsrcDP10smp_monErrE", "_ZN3MWF6RsrcDP10smp_monWrnE",
        "_ZN3MWF6RsrcDP10smp_monMsgE", "_ZN3MWF6RsrcDP10smp_monSeqE",
        "_ZN3MWF6RsrcDP10smp_monDbgE"
    };
    void *values[5] = {0};
    for (unsigned int i = 0; i < 5; ++i) {
        void **slot = (void **)dlsym(RTLD_DEFAULT, symbols[i]);
        if (slot) values[i] = *slot;
    }
    dprintf(2, "FX6_MWF_OBSERVER phase=%s caller=%s+0x%lx self=%p err=%p wrn=%p msg=%p seq=%p dbg=%p\n",
            phase, di.dli_fname ? di.dli_fname : "?",
            (unsigned long)((uintptr_t)caller - (uintptr_t)di.dli_fbase),
            self, values[0], values[1], values[2], values[3], values[4]);
    errno = saved_errno;
}

void MWF_Init(void) {
    int saved_errno = errno;
    void (*real)(void) = (void (*)(void))must_resolve("MWF_Init");
    void *caller = __builtin_return_address(0);
    report_state("MWF_Init_enter", caller, NULL);
    errno = saved_errno;
    real();
    saved_errno = errno;
    report_state("MWF_Init_exit", caller, NULL);
    errno = saved_errno;
}

void _ZN3MWF6RsrcDP10InitializeEv(void) {
    int saved_errno = errno;
    void (*real)(void) = (void (*)(void))must_resolve("_ZN3MWF6RsrcDP10InitializeEv");
    void *caller = __builtin_return_address(0);
    report_state("RsrcDP_Initialize_enter", caller, NULL);
    errno = saved_errno;
    real();
    saved_errno = errno;
    report_state("RsrcDP_Initialize_exit", caller, NULL);
    errno = saved_errno;
}

bool _ZNK7MonCtrl7GetFlagEv(const void *self) {
    int saved_errno = errno;
    bool (*real)(const void *) = (bool (*)(const void *))must_resolve("_ZNK7MonCtrl7GetFlagEv");
    void *caller = __builtin_return_address(0);
    Dl_info di = {0};
    if (dladdr(caller, &di) && di.dli_fbase && di.dli_fname &&
        strcmp(basename_of(di.dli_fname), "libMWF.so") == 0 &&
        (uintptr_t)caller - (uintptr_t)di.dli_fbase == 0x38f14UL) {
        report_state("RsrcDP_error_GetFlag", caller, self);
    }
    errno = saved_errno;
    return real(self); /* Preserve the original NULL fault when self is NULL. */
}
