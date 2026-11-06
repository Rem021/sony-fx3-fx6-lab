/* Read-only observation interposer. Every operation calls the original libc. */
typedef __SIZE_TYPE__ size_t;
extern void *dlsym(void *, const char *);
extern int dprintf(int, const char *, ...);
extern int snprintf(char *, size_t, const char *, ...);
extern long readlink(const char *, char *, size_t);
extern int getpid(void);
struct trace_iovec { void *base; size_t length; };
extern long process_vm_readv(int, const struct trace_iovec *, unsigned long,
                            const struct trace_iovec *, unsigned long, unsigned long);
extern int open(const char *, int, ...);
extern long pread(int, void *, size_t, long);
extern int close(int);
extern int *__errno_location(void);
extern void _exit(int) __attribute__((noreturn));
static unsigned int ioctl_count;
static unsigned int mmap_count;
static unsigned char uipc_map_lock;
static unsigned long uipc_base, uipc_length, uipc_epoch;

static void map_lock(void)
{
    while (__atomic_test_and_set(&uipc_map_lock, __ATOMIC_ACQUIRE)) { }
}

static void map_unlock(void)
{
    __atomic_clear(&uipc_map_lock, __ATOMIC_RELEASE);
}

/* Invalidate before a real mapping-lifetime operation. A failed operation still
 * conservatively discards the observational capability; it never fakes success. */
static void invalidate_mapping(void *address, size_t length)
{
    unsigned long start = (unsigned long)address;
    map_lock();
    int overlaps = uipc_length && length &&
        (start >= uipc_base ? start - uipc_base < uipc_length : uipc_base - start < length);
    if (overlaps) { uipc_base = 0; uipc_length = 0; ++uipc_epoch; }
    map_unlock();
}

static long bounded_live_uipc_read(void *destination, const void *source, size_t count,
                                   unsigned long *base, unsigned long *length, unsigned long *epoch)
{
    /* A nested observer skips rather than waiting for an interrupted reader. */
    if (__atomic_test_and_set(&uipc_map_lock, __ATOMIC_ACQUIRE)) return -1;
    unsigned long pointer = (unsigned long)source;
    int permitted = count <= 16 && uipc_base && uipc_length == 0x200000 &&
        pointer >= uipc_base && pointer - uipc_base <= uipc_length &&
        count <= uipc_length - (pointer - uipc_base);
    if (permitted) {
        *base = uipc_base; *length = uipc_length; *epoch = uipc_epoch;
        const volatile unsigned char *input = (const volatile unsigned char *)source;
        unsigned char *output = destination;
        for (size_t i = 0; i < count; i++) output[i] = input[i];
    }
    map_unlock();
    return permitted ? (long)count : -1;
}

static long safe_read(void *destination, const void *source, size_t count, int *read_errno)
{
    int fd = open("/proc/self/mem", 0);
    if (fd < 0) {
        *read_errno = *__errno_location();
        return -1;
    }
    long result = pread(fd, destination, count, (long)source);
    int saved_errno = *__errno_location();
    close(fd);
    *read_errno = result < 0 ? saved_errno : 0;
    *__errno_location() = saved_errno;
    return result;
}

static void hex_bytes(char *out, const unsigned char *bytes, long count)
{
    static const char alphabet[] = "0123456789abcdef";
    if (count < 0) count = 0;
    if (count > 32) count = 32;
    for (long i = 0; i < count; i++) {
        out[2 * i] = alphabet[bytes[i] >> 4];
        out[2 * i + 1] = alphabet[bytes[i] & 15];
    }
    out[2 * count] = 0;
}

int ioctl(int fd, unsigned long request, ...)
{
    int entry_errno = *__errno_location();
    void *caller = __builtin_return_address(0);
    static int (*original)(int, unsigned long, void *);
    __builtin_va_list args;
    __builtin_va_start(args, request);
    void *argument = __builtin_va_arg(args, void *);
    __builtin_va_end(args);
    int (*function)(int, unsigned long, void *) = __atomic_load_n(&original, __ATOMIC_ACQUIRE);
    if (!function) {
        function = (void *)dlsym((void *)-1, "ioctl");
        __atomic_store_n(&original, function, __ATOMIC_RELEASE);
    }
    if (!function) {
        dprintf(2, "FX3_TRACE_FATAL: original ioctl unresolved\n");
        _exit(126);
    }
    unsigned int command = (unsigned int)request & 0x7fffffffU;
    char fd_path[64], target[64];
    snprintf(fd_path, sizeof fd_path, "/proc/self/fd/%d", fd);
    long target_length = readlink(fd_path, target, sizeof target - 1);
    if (target_length >= 0) target[target_length] = 0;
    int is_uipc = target_length == 9 && __builtin_memcmp(target, "/dev/uipc", 9) == 0;
    unsigned char outer[16] = {0}, argument1_raw[24] = {0}, message[16] = {0};
    long outer_read = -1, argument1_read = -1, message_read = -1;
    int outer_errno = 0, argument1_errno = 0, message_errno = 0;
    int body_direct_snapshot = 0, body_proc_errno = 0;
    unsigned long body_map_base = 0, body_map_length = 0, body_map_epoch = 0;
    unsigned int argument0 = 0;
    unsigned long argument1 = 0;
    unsigned long message_pointer = 0;
    if (is_uipc && command <= 16 && argument) {
        outer_read = safe_read(outer, argument, 16, &outer_errno);
        if (outer_read == 16) {
            __builtin_memcpy(&argument0, outer, 4);
            __builtin_memcpy(&argument1, outer + 8, 8);
            if (command >= 4 && command <= 6 && argument1) {
                argument1_read = safe_read(argument1_raw, (void *)argument1, command == 5 ? 24 : 16, &argument1_errno);
                if (command == 4) message_pointer = argument1;
                if (command == 5 && argument1_read == 24)
                    __builtin_memcpy(&message_pointer, argument1_raw, 8);
                if (command == 6 && argument1_read == 16) {
                    unsigned int total_length = 0;
                    __builtin_memcpy(&total_length, argument1_raw, 4);
                    if (total_length >= 32 && argument1 <= ~0UL - 16)
                        message_pointer = argument1 + 16;
                }
                if (message_pointer) {
                    message_read = safe_read(message, (void *)message_pointer, 16, &message_errno);
                    body_proc_errno = message_errno;
                    /* PFNMAP ranges are CPU-readable even when /proc mem GUP
                     * rejects them. Only the current successful original UIPC
                     * mmap is eligible; unknown pointers remain unread. */
                    if (message_read < 0 && message_errno == 5) {
                        long direct = bounded_live_uipc_read(message, (void *)message_pointer, 16,
                            &body_map_base, &body_map_length, &body_map_epoch);
                        if (direct == 16) { message_read = direct; message_errno = 0; body_direct_snapshot = 1; }
                    }
                }
            }
        }
    }
    *__errno_location() = entry_errno;
    int result = function(fd, request, argument);
    int saved_errno = *__errno_location();
    unsigned int sequence = __atomic_fetch_add(&ioctl_count, 1, __ATOMIC_RELAXED);
    if (sequence < 256 || (sequence < 8192 && is_uipc && argument0 != 0x8f013a && command >= 4 && command <= 6))
        dprintf(2, "FX3_IOCTL_PASS seq=%u fd=%d request=0x%lx argument=%p result=%d errno=%d caller=%p\n",
                sequence, fd, request, argument, result, saved_errno, caller);
    if ((sequence < 256 || (sequence < 8192 && is_uipc && argument0 != 0x8f013a && command >= 4 && command <= 6)) && is_uipc) {
        char outer_hex[33], argument1_hex[49], message_hex[33];
        hex_bytes(outer_hex, outer, outer_read);
        hex_bytes(argument1_hex, argument1_raw, argument1_read);
        hex_bytes(message_hex, message, message_read);
        dprintf(2, "FX3_UIPC_PASS seq=%u op=%u arg0=0x%x arg1=0x%lx outer_read=%ld outer_errno=%d outer=%s arg1_read=%ld arg1_errno=%d arg1_raw=%s body_pointer=0x%lx body_read=%ld body_errno=%d body_head=%s result=%d errno=%d body_proc_errno=%d body_direct=%d body_map=0x%lx body_map_length=0x%lx body_epoch=%lu\n",
                sequence, command, argument0, argument1, outer_read, outer_errno, outer_hex,
                argument1_read, argument1_errno, argument1_hex, message_pointer, message_read, message_errno, message_hex, result, saved_errno,
                body_proc_errno, body_direct_snapshot, body_map_base, body_map_length, body_map_epoch);
    }
    *__errno_location() = saved_errno;
    return result;
}

void *mmap(void *address, size_t length, int protection, int flags, int fd, long offset)
{
    int entry_errno = *__errno_location();
    static void *(*original)(void *, size_t, int, int, int, long);
    void *(*function)(void *, size_t, int, int, int, long) = __atomic_load_n(&original, __ATOMIC_ACQUIRE);
    if (!function) {
        function = (void *)dlsym((void *)-1, "mmap");
        __atomic_store_n(&original, function, __ATOMIC_RELEASE);
    }
    if (!function) {
        dprintf(2, "FX3_TRACE_FATAL: original mmap unresolved\n");
        _exit(126);
    }
    /* MAP_FIXED can replace an existing VMA without a munmap call. */
    if (flags & 0x10) invalidate_mapping(address, length);
    *__errno_location() = entry_errno;
    void *result = function(address, length, protection, flags, fd, offset);
    int saved_errno = *__errno_location();
    if (result != (void *)-1 && address == (void *)0 && length == 0x200000 &&
        protection == 3 && flags == 1 && offset == 0 && (unsigned long)result <= ~0UL - length) {
        char path[64], target[64];
        snprintf(path, sizeof path, "/proc/self/fd/%d", fd);
        long n = readlink(path, target, sizeof target - 1);
        if (n == 9 && __builtin_memcmp(target, "/dev/uipc", 9) == 0) {
            map_lock();
            uipc_base = (unsigned long)result; uipc_length = length; ++uipc_epoch;
            unsigned long epoch = uipc_epoch;
            map_unlock();
            dprintf(2, "FX3_UIPC_LIVE_MAP base=%p length=0x%lx protection=0x%x flags=0x%x fd=%d epoch=%lu\n",
                    result, (unsigned long)length, protection, flags, fd, epoch);
        }
    }
    unsigned int sequence = __atomic_fetch_add(&mmap_count, 1, __ATOMIC_RELAXED);
    if (sequence < 32)
        dprintf(2, "FX3_MMAP_PASS seq=%u address=%p length=0x%lx protection=0x%x flags=0x%x fd=%d offset=0x%lx result=%p errno=%d\n",
                sequence, address, (unsigned long)length, protection, flags, fd,
                (unsigned long)offset, result, saved_errno);
    *__errno_location() = saved_errno;
    return result;
}

int munmap(void *address, size_t length)
{
    int entry_errno = *__errno_location();
    static int (*original)(void *, size_t);
    int (*function)(void *, size_t) = __atomic_load_n(&original, __ATOMIC_ACQUIRE);
    if (!function) { function = (void *)dlsym((void *)-1, "munmap"); __atomic_store_n(&original, function, __ATOMIC_RELEASE); }
    if (!function) _exit(126);
    invalidate_mapping(address, length);
    *__errno_location() = entry_errno;
    return function(address, length);
}

int mprotect(void *address, size_t length, int protection)
{
    int entry_errno = *__errno_location();
    static int (*original)(void *, size_t, int);
    int (*function)(void *, size_t, int) = __atomic_load_n(&original, __ATOMIC_ACQUIRE);
    if (!function) { function = (void *)dlsym((void *)-1, "mprotect"); __atomic_store_n(&original, function, __ATOMIC_RELEASE); }
    if (!function) _exit(126);
    invalidate_mapping(address, length);
    *__errno_location() = entry_errno;
    return function(address, length, protection);
}

void *mremap(void *address, size_t old_length, size_t new_length, int flags, ...)
{
    int entry_errno = *__errno_location();
    static void *(*original)(void *, size_t, size_t, int, ...);
    void *(*function)(void *, size_t, size_t, int, ...) = __atomic_load_n(&original, __ATOMIC_ACQUIRE);
    if (!function) { function = (void *)dlsym((void *)-1, "mremap"); __atomic_store_n(&original, function, __ATOMIC_RELEASE); }
    if (!function) _exit(126);
    void *new_address = (void *)0;
    if (flags & 2) {
        __builtin_va_list arguments;
        __builtin_va_start(arguments, flags);
        new_address = __builtin_va_arg(arguments, void *);
        __builtin_va_end(arguments);
    }
    invalidate_mapping(address, old_length);
    if (flags & 2) invalidate_mapping(new_address, new_length);
    *__errno_location() = entry_errno;
    return function(address, old_length, new_length, flags, new_address);
}
