/* 391 post-walk trace stub: preserves x0..x9 and x17 across logging, so calls
 * that pass a struct-return buffer in x8 (e.g. 0x113e8f4) see the real x8. */
typedef unsigned long u64;
extern int dprintf(int, const char *, ...);

__attribute__((visibility("hidden")))
void *(*g_post_real[512])(void *, void *, void *, void *, void *, void *, void *, void *);

__attribute__((visibility("hidden")))
void fx6_post_log_call(u64 id, void *a0, void *a1) {
    dprintf(2, "FX6_POST%lu_CALL a0=%p a1=%p\n", id, a0, a1);
}

__attribute__((visibility("hidden")))
void fx6_post_log_ret(u64 id, void *r) {
    dprintf(2, "FX6_POST%lu_RET r0=%p\n", id, r);
}

__attribute__((naked)) void *fx6_stub_post(void) {
    __asm__ volatile(
        "stp x29, x30, [sp, #-0x70]!\n"
        "mov x29, sp\n"
        "stp x0, x1, [sp, #0x10]\n"
        "stp x2, x3, [sp, #0x20]\n"
        "stp x4, x5, [sp, #0x30]\n"
        "stp x6, x7, [sp, #0x40]\n"
        "stp x8, x9, [sp, #0x50]\n"
        "str x17, [sp, #0x60]\n"
        "mov x0, x17\n"
        "ldr x1, [sp, #0x10]\n"
        "ldr x2, [sp, #0x18]\n"
        "bl fx6_post_log_call\n"
        "ldp x0, x1, [sp, #0x10]\n"
        "ldp x2, x3, [sp, #0x20]\n"
        "ldp x4, x5, [sp, #0x30]\n"
        "ldp x6, x7, [sp, #0x40]\n"
        "ldr x8, [sp, #0x50]\n"
        "ldr x9, [sp, #0x60]\n"
        "adrp x10, g_post_real\n"
        "add x10, x10, :lo12:g_post_real\n"
        "ldr x10, [x10, x9, lsl #3]\n"
        "blr x10\n"
        "str x0, [sp, #0x68]\n"
        "ldr x0, [sp, #0x60]\n"
        "ldr x1, [sp, #0x68]\n"
        "bl fx6_post_log_ret\n"
        "ldr x0, [sp, #0x68]\n"
        "ldp x29, x30, [sp], #0x70\n"
        "ret\n"
    );
}
