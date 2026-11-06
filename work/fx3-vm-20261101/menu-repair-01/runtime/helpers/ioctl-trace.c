/* Read-only observation interposer. Every operation calls the original libc. */
typedef __SIZE_TYPE__ size_t;
extern void *dlsym(void *, const char *);
extern int dprintf(int, const char *, ...);
extern int *__errno_location(void);
extern void _exit(int) __attribute__((noreturn));
static unsigned int ioctl_count;
static unsigned int mmap_count;

int ioctl(int fd, unsigned long request, ...)
{
    static int (*original)(int, unsigned long, void *);
    __builtin_va_list args;
    __builtin_va_start(args, request);
    void *argument = __builtin_va_arg(args, void *);
    __builtin_va_end(args);
    if (!original) original = (void *)dlsym((void *)-1, "ioctl");
    if (!original) {
        dprintf(2, "FX3_TRACE_FATAL: original ioctl unresolved\n");
        _exit(126);
    }
    int result = original(fd, request, argument);
    int saved_errno = *__errno_location();
    unsigned int sequence = __atomic_fetch_add(&ioctl_count, 1, __ATOMIC_RELAXED);
    if (sequence < 256)
        dprintf(2, "FX3_IOCTL_PASS seq=%u fd=%d request=0x%lx argument=%p result=%d errno=%d\n",
                sequence, fd, request, argument, result, saved_errno);
    *__errno_location() = saved_errno;
    return result;
}

void *mmap(void *address, size_t length, int protection, int flags, int fd, long offset)
{
    static void *(*original)(void *, size_t, int, int, int, long);
    if (!original) original = (void *)dlsym((void *)-1, "mmap");
    if (!original) {
        dprintf(2, "FX3_TRACE_FATAL: original mmap unresolved\n");
        _exit(126);
    }
    void *result = original(address, length, protection, flags, fd, offset);
    int saved_errno = *__errno_location();
    unsigned int sequence = __atomic_fetch_add(&mmap_count, 1, __ATOMIC_RELAXED);
    if (sequence < 32)
        dprintf(2, "FX3_MMAP_PASS seq=%u address=%p length=0x%lx protection=0x%x flags=0x%x fd=%d offset=0x%lx result=%p errno=%d\n",
                sequence, address, (unsigned long)length, protection, flags, fd,
                (unsigned long)offset, result, saved_errno);
    *__errno_location() = saved_errno;
    return result;
}
