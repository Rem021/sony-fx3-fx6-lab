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
extern int *__errno_location(void);
extern void _exit(int) __attribute__((noreturn));
static unsigned int ioctl_count;
static unsigned int mmap_count;

static long safe_read(void *destination, const void *source, size_t count)
{
    struct trace_iovec local = {destination, count};
    struct trace_iovec remote = {(void *)source, count};
    return process_vm_readv(getpid(), &local, 1, &remote, 1, 0);
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
    unsigned int argument0 = 0;
    unsigned long argument1 = 0;
    unsigned long message_pointer = 0;
    if (is_uipc && command <= 16 && argument) {
        outer_read = safe_read(outer, argument, 16);
        if (outer_read == 16) {
            __builtin_memcpy(&argument0, outer, 4);
            __builtin_memcpy(&argument1, outer + 8, 8);
            if (command >= 4 && command <= 6 && argument1) {
                argument1_read = safe_read(argument1_raw, (void *)argument1, command == 5 ? 24 : 16);
                if (command == 4) message_pointer = argument1;
                if (command == 5 && argument1_read == 24)
                    __builtin_memcpy(&message_pointer, argument1_raw, 8);
                if (command == 6 && argument1_read == 16) {
                    unsigned int total_length = 0;
                    __builtin_memcpy(&total_length, argument1_raw, 4);
                    if (total_length >= 32 && argument1 <= ~0UL - 16)
                        message_pointer = argument1 + 16;
                }
                if (message_pointer) message_read = safe_read(message, (void *)message_pointer, 16);
            }
        }
    }
    *__errno_location() = entry_errno;
    int result = function(fd, request, argument);
    int saved_errno = *__errno_location();
    unsigned int sequence = __atomic_fetch_add(&ioctl_count, 1, __ATOMIC_RELAXED);
    if (sequence < 256)
        dprintf(2, "FX3_IOCTL_PASS seq=%u fd=%d request=0x%lx argument=%p result=%d errno=%d\n",
                sequence, fd, request, argument, result, saved_errno);
    if (sequence < 256 && is_uipc) {
        char outer_hex[33], argument1_hex[49], message_hex[33];
        hex_bytes(outer_hex, outer, outer_read);
        hex_bytes(argument1_hex, argument1_raw, argument1_read);
        hex_bytes(message_hex, message, message_read);
        dprintf(2, "FX3_UIPC_PASS seq=%u op=%u arg0=0x%x arg1=0x%lx outer_read=%ld outer=%s arg1_read=%ld arg1_raw=%s body_pointer=0x%lx body_read=%ld body_head=%s result=%d errno=%d\n",
                sequence, command, argument0, argument1, outer_read, outer_hex,
                argument1_read, argument1_hex, message_pointer, message_read, message_hex, result, saved_errno);
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
    *__errno_location() = entry_errno;
    void *result = function(address, length, protection, flags, fd, offset);
    int saved_errno = *__errno_location();
    unsigned int sequence = __atomic_fetch_add(&mmap_count, 1, __ATOMIC_RELAXED);
    if (sequence < 32)
        dprintf(2, "FX3_MMAP_PASS seq=%u address=%p length=0x%lx protection=0x%x flags=0x%x fd=%d offset=0x%lx result=%p errno=%d\n",
                sequence, address, (unsigned long)length, protection, flags, fd,
                (unsigned long)offset, result, saved_errno);
    *__errno_location() = saved_errno;
    return result;
}
