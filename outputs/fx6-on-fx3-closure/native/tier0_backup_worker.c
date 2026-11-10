/*
 * Hardened Read-Only Two-Pass Tier-0 Per-Body Calibration Backup Worker (ARM64 Freestanding)
 *
 * Zero libc imports — invokes Linux AArch64 syscalls directly via `svc #0`.
 * Security & Safety Invariants:
 *  1. One-shot atomic reentrancy guard + FIRST kernel syscall is unconditionally
 *     `unlinkat(AT_FDCWD, "/tmp/jiritsu/libJit.so", 0)` to prevent crash/reboot loops and
 *     eliminate persistent footprint on `p6` (`/dev/nflasha6`).
 *  2. All 11 `TIER0_REQUIRED_BACKUPS` sources are opened strictly `O_RDONLY | O_NOFOLLOW`
 *     (zero write/create/truncate flags ever touch `/dev/...` or source paths).
 *  3. Chunked `pread64` with header magic verification (`"82462.00"` + count==30 on `sector0`,
 *     `0xaaaaaaaa` + `"BK4\0"` on `p2_backup_bin`) BEFORE opening any output file.
 *  4. All backup files and `manifest.json` are opened strictly under `/mnt/fx3_tier0_backup/`
 *     with `O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW` (never overwrites or truncates).
 *  5. Independent Pass-1 and Pass-2 `openat` + `pread64` + FIPS 180-4 SHA-256 verification;
 *     any single-bit flip between Pass-1 and Pass-2 aborts with a non-zero error code and
 *     refuses to emit `manifest.json`.
 */

typedef unsigned long uword;
typedef unsigned long long u64;
typedef unsigned int u32;
typedef unsigned char u8;

_Static_assert(sizeof(long) == 8 && sizeof(u64) == 8 && sizeof(u32) == 4, "LP64 ABI required");

#if !defined(__aarch64__)
#error "tier0_backup_worker.c targets Linux AArch64 only"
#endif

static long sc6(long nr, long a0, long a1, long a2, long a3, long a4, long a5) {
    register long x8 __asm__("x8") = nr;
    register long x0 __asm__("x0") = a0;
    register long x1 __asm__("x1") = a1;
    register long x2 __asm__("x2") = a2;
    register long x3 __asm__("x3") = a3;
    register long x4 __asm__("x4") = a4;
    register long x5 __asm__("x5") = a5;
    __asm__ volatile(
        "svc #0"
        : "+r"(x0)
        : "r"(x8), "r"(x1), "r"(x2), "r"(x3), "r"(x4), "r"(x5)
        : "memory", "cc"
    );
    return x0;
}

/* Linux AArch64 syscall numbers */
enum {
    SYS_ioctl    = 29,
    SYS_mkdirat  = 34,
    SYS_unlinkat = 35,
    SYS_openat   = 56,
    SYS_close    = 57,
    SYS_write    = 64,
    SYS_pread64  = 67,
    SYS_fstat    = 80,
    SYS_sync     = 81,
    SYS_fsync    = 82
};

/* Linux openat flags (sets both arm64 O_NOFOLLOW 0100000=0x8000 and generic 0400000=0x20000 + O_CLOEXEC 0x80000) */
enum {
    AT_FDCWD       = -100,
    O_RDONLY_SAFE  = 0xA8000,             /* O_RDONLY(0) | O_NOFOLLOW_ARM64(0x8000) | O_LARGEFILE/GENERIC_NOFOLLOW(0x20000) | O_CLOEXEC(0x80000) */
    O_WRONLY_EXCL  = 0xA80C1,             /* O_WRONLY(1) | O_CREAT(0x40) | O_EXCL(0x80) | O_NOFOLLOW | O_CLOEXEC */
    EEXIST_NEG     = -17,
    BLKGETSIZE64   = (int)0x80081272u,
    CHUNK_BYTES    = 65536
};

/* Distinct fail-closed return codes */
enum {
    WORKER_OK                  = 0,
    ERR_REENTRANT_LOCK         = 10,
    ERR_UNLINK_LIBJIT_FAILED   = 11,
    ERR_MKDIR_BACKUP_FAILED    = 12,
    ERR_SRC_OPEN_FAILED        = 13,
    ERR_SRC_STAT_FAILED        = 14,
    ERR_SRC_SIZE_CONTRACT      = 15,
    ERR_BOOT_SYMMETRY          = 16,
    ERR_PREAD_SHORT_OR_IO      = 17,
    ERR_SECTOR0_MAGIC          = 18,
    ERR_BK4_MAGIC              = 19,
    ERR_DST_OPEN_EXCL_FAILED   = 20,
    ERR_DST_WRITE_FAILED       = 21,
    ERR_DST_FSYNC_CLOSE_FAILED = 22,
    ERR_PASS2_OPEN_FAILED      = 23,
    ERR_PASS2_PREAD_FAILED     = 24,
    ERR_TWOPASS_SHA256_MISMATCH = 25,
    ERR_MANIFEST_WRITE_FAILED  = 26
};

enum {
    MAGIC_NONE        = 0,
    MAGIC_SECTOR0     = 1,
    MAGIC_BK4_BACKUP  = 2
};

/* Linux AArch64 asm-generic struct stat (128 bytes) */
struct kstat {
    u64 dev;
    u64 ino;
    u32 mode;
    u32 nlink;
    u32 uid;
    u32 gid;
    u64 rdev;
    u64 pad1;
    long size;
    int blksize;
    int pad2;
    long blocks;
    long atime;
    u64 atime_ns;
    long mtime;
    u64 mtime_ns;
    long ctime;
    u64 ctime_ns;
    u32 pad3;
    u32 pad4;
};
_Static_assert(sizeof(struct kstat) == 128, "AArch64 kstat must be 128 bytes");
_Static_assert(__builtin_offsetof(struct kstat, size) == 48, "AArch64 kstat.size offset must be 48");

/* Pointer-free item descriptor (zero runtime relocations required in .rodata) */
struct tier0_item_spec {
    char key[24];
    char src_path[32];
    char dst_path[56];
    u64 exact_bytes;
    u64 min_bytes;
    u64 max_bytes;
    u64 multiple_of;
    u32 magic_kind;
    u32 reserved;
};

static const struct tier0_item_spec TIER0_ITEMS[11] = {
    {
        "sector0",
        "/dev/nflasha",
        "/mnt/fx3_tier0_backup/sector0.bin",
        512ULL, 512ULL, 512ULL, 512ULL, MAGIC_SECTOR0, 0
    },
    {
        "boot0",
        "/dev/nflashaB0",
        "/mnt/fx3_tier0_backup/boot0.bin",
        0ULL, 131072ULL, 33423360ULL, 131072ULL, MAGIC_NONE, 0
    },
    {
        "boot1",
        "/dev/nflashaB1",
        "/mnt/fx3_tier0_backup/boot1.bin",
        0ULL, 131072ULL, 33423360ULL, 131072ULL, MAGIC_NONE, 0
    },
    {
        "p1_updater",
        "/dev/nflasha1",
        "/mnt/fx3_tier0_backup/p1_updater.bin",
        25100288ULL, 25100288ULL, 25100288ULL, 512ULL, MAGIC_NONE, 0
    },
    {
        "p2_backup_bin",
        "/setting/Backup.bin",
        "/mnt/fx3_tier0_backup/p2_backup_bin.bin",
        0ULL, 262144ULL, 67108864ULL, 1ULL, MAGIC_BK4_BACKUP, 0
    },
    {
        "p2_psd_bin",
        "/setting/psd.bin",
        "/mnt/fx3_tier0_backup/p2_psd_bin.bin",
        0ULL, 1024ULL, 67108864ULL, 1ULL, MAGIC_NONE, 0
    },
    {
        "p2_defdet_bin",
        "/setting/defdet.bin",
        "/mnt/fx3_tier0_backup/p2_defdet_bin.bin",
        0ULL, 1024ULL, 67108864ULL, 1ULL, MAGIC_NONE, 0
    },
    {
        "p6_jiritsu",
        "/dev/nflasha6",
        "/mnt/fx3_tier0_backup/p6_jiritsu.bin",
        26214400ULL, 26214400ULL, 26214400ULL, 512ULL, MAGIC_NONE, 0
    },
    {
        "p12_cert",
        "/dev/nflasha12",
        "/mnt/fx3_tier0_backup/p12_cert.bin",
        0ULL, 20971520ULL, 67108864ULL, 512ULL, MAGIC_NONE, 0
    },
    {
        "p18_lensfile",
        "/dev/nflasha18",
        "/mnt/fx3_tier0_backup/p18_lensfile.bin",
        0ULL, 1024ULL, 67108864ULL, 1ULL, MAGIC_NONE, 0
    },
    {
        "spi_nor_ddrtraining",
        "/dev/mtd0",
        "/mnt/fx3_tier0_backup/spi_nor_ddrtraining.bin",
        0ULL, 2048ULL, 134217728ULL, 1ULL, MAGIC_NONE, 0
    }
};

/* ============================================================================
 * Pure-C FIPS 180-4 SHA-256 Implementation (Zero external dependencies)
 * ============================================================================ */

static const u32 SHA256_K[64] = {
    0x428a2f98u, 0x71374491u, 0xb5c0fbcfu, 0xe9b5dba5u,
    0x3956c25bu, 0x59f111f1u, 0x923f82a4u, 0xab1c5ed5u,
    0xd807aa98u, 0x12835b01u, 0x243185beu, 0x550c7dc3u,
    0x72be5d74u, 0x80deb1feu, 0x9bdc06a7u, 0xc19bf174u,
    0xe49b69c1u, 0xefbe4786u, 0x0fc19dc6u, 0x240ca1ccu,
    0x2de92c6fu, 0x4a7484aau, 0x5cb0a9dcu, 0x76f988dau,
    0x983e5152u, 0xa831c66du, 0xb00327c8u, 0xbf597fc7u,
    0xc6e00bf3u, 0xd5a79147u, 0x06ca6351u, 0x14292967u,
    0x27b70a85u, 0x2e1b2138u, 0x4d2c6dfcu, 0x53380d13u,
    0x650a7354u, 0x766a0abbu, 0x81c2c92eu, 0x92722c85u,
    0xa2bfe8a1u, 0xa81a664bu, 0xc24b8b70u, 0xc76c51a3u,
    0xd192e819u, 0xd6990624u, 0xf40e3585u, 0x106aa070u,
    0x19a4c116u, 0x1e376c08u, 0x2748774cu, 0x34b0bcb5u,
    0x391c0cb3u, 0x4ed8aa4au, 0x5b9cca4fu, 0x682e6ff3u,
    0x748f82eeu, 0x78a5636fu, 0x84c87814u, 0x8cc70208u,
    0x90befffau, 0xa4506cebu, 0xbef9a3f7u, 0xc67178f2u
};

struct sha256_ctx {
    u32 state[8];
    u64 bitlen;
    u32 buflen;
    u8 buf[64];
};

static inline u32 rotr32(u32 x, u32 n) {
    return (x >> n) | (x << (32u - n));
}

static void sha256_transform(struct sha256_ctx *ctx, const u8 block[64]) {
    u32 w[64];
    for (u32 i = 0; i < 16; ++i) {
        u32 j = i * 4;
        w[i] = ((u32)block[j] << 24) | ((u32)block[j + 1] << 16) |
               ((u32)block[j + 2] << 8) | (u32)block[j + 3];
    }
    for (u32 i = 16; i < 64; ++i) {
        u32 s0 = rotr32(w[i - 15], 7) ^ rotr32(w[i - 15], 18) ^ (w[i - 15] >> 3);
        u32 s1 = rotr32(w[i - 2], 17) ^ rotr32(w[i - 2], 19) ^ (w[i - 2] >> 10);
        w[i] = w[i - 16] + s0 + w[i - 7] + s1;
    }

    u32 a = ctx->state[0];
    u32 b = ctx->state[1];
    u32 c = ctx->state[2];
    u32 d = ctx->state[3];
    u32 e = ctx->state[4];
    u32 f = ctx->state[5];
    u32 g = ctx->state[6];
    u32 h = ctx->state[7];

    for (u32 i = 0; i < 64; ++i) {
        u32 S1 = rotr32(e, 6) ^ rotr32(e, 11) ^ rotr32(e, 25);
        u32 ch = (e & f) ^ ((~e) & g);
        u32 temp1 = h + S1 + ch + SHA256_K[i] + w[i];
        u32 S0 = rotr32(a, 2) ^ rotr32(a, 13) ^ rotr32(a, 22);
        u32 maj = (a & b) ^ (a & c) ^ (b & c);
        u32 temp2 = S0 + maj;

        h = g;
        g = f;
        f = e;
        e = d + temp1;
        d = c;
        c = b;
        b = a;
        a = temp1 + temp2;
    }

    ctx->state[0] += a;
    ctx->state[1] += b;
    ctx->state[2] += c;
    ctx->state[3] += d;
    ctx->state[4] += e;
    ctx->state[5] += f;
    ctx->state[6] += g;
    ctx->state[7] += h;
}

static void sha256_init(struct sha256_ctx *ctx) {
    ctx->state[0] = 0x6a09e667u;
    ctx->state[1] = 0xbb67ae85u;
    ctx->state[2] = 0x3c6ef372u;
    ctx->state[3] = 0xa54ff53au;
    ctx->state[4] = 0x510e527fu;
    ctx->state[5] = 0x9b05688cu;
    ctx->state[6] = 0x1f83d9abu;
    ctx->state[7] = 0x5be0cd19u;
    ctx->bitlen = 0;
    ctx->buflen = 0;
}

static void sha256_update(struct sha256_ctx *ctx, const u8 *data, u64 len) {
    u64 i = 0;
    if (ctx->buflen > 0) {
        while (i < len && ctx->buflen < 64) {
            ctx->buf[ctx->buflen++] = data[i++];
        }
        if (ctx->buflen == 64) {
            sha256_transform(ctx, ctx->buf);
            ctx->bitlen += 512ULL;
            ctx->buflen = 0;
        }
    }
    while (i + 64 <= len) {
        sha256_transform(ctx, data + i);
        ctx->bitlen += 512ULL;
        i += 64;
    }
    while (i < len) {
        ctx->buf[ctx->buflen++] = data[i++];
    }
}

static void sha256_final(struct sha256_ctx *ctx, u8 out[32]) {
    u64 total_bits = ctx->bitlen + ((u64)ctx->buflen * 8ULL);
    ctx->buf[ctx->buflen++] = 0x80u;
    if (ctx->buflen > 56) {
        while (ctx->buflen < 64) {
            ((volatile u8 *)ctx->buf)[ctx->buflen++] = 0;
        }
        sha256_transform(ctx, ctx->buf);
        ctx->buflen = 0;
    }
    while (ctx->buflen < 56) {
        ((volatile u8 *)ctx->buf)[ctx->buflen++] = 0;
    }
    for (int j = 7; j >= 0; --j) {
        ctx->buf[56 + (7 - j)] = (u8)(total_bits >> (j * 8));
    }
    sha256_transform(ctx, ctx->buf);

    for (u32 i = 0; i < 8; ++i) {
        out[i * 4 + 0] = (u8)(ctx->state[i] >> 24);
        out[i * 4 + 1] = (u8)(ctx->state[i] >> 16);
        out[i * 4 + 2] = (u8)(ctx->state[i] >> 8);
        out[i * 4 + 3] = (u8)(ctx->state[i]);
    }
}

/* ============================================================================
 * Worker State & Helpers
 * ============================================================================ */

static int g_worker_entered;
static int g_worker_last_rc;
static u8 g_io_buf[CHUNK_BYTES];
static char g_manifest_buf[8192];

static int digest_equal_ct(const u8 a[32], const u8 b[32]) {
    u8 diff = 0;
    for (u32 i = 0; i < 32; ++i) {
        diff |= (a[i] ^ b[i]);
    }
    return diff == 0;
}

static void hex_encode_32(const u8 digest[32], char out_hex[65]) {
    static const char HEX[16] = {
        '0', '1', '2', '3', '4', '5', '6', '7',
        '8', '9', 'a', 'b', 'c', 'd', 'e', 'f'
    };
    for (u32 i = 0; i < 32; ++i) {
        out_hex[i * 2 + 0] = HEX[(digest[i] >> 4) & 0xFu];
        out_hex[i * 2 + 1] = HEX[digest[i] & 0xFu];
    }
    out_hex[64] = '\0';
}

static u32 append_str(char *dst, u32 pos, u32 cap, const char *s) {
    while (*s && pos + 1 < cap) {
        dst[pos++] = *s++;
    }
    return pos;
}

static u32 append_u64_dec(char *dst, u32 pos, u32 cap, u64 val) {
    char tmp[24];
    u32 n = 0;
    if (val == 0) {
        tmp[n++] = '0';
    } else {
        while (val > 0) {
            tmp[n++] = (char)('0' + (val % 10ULL));
            val /= 10ULL;
        }
    }
    while (n > 0 && pos + 1 < cap) {
        dst[pos++] = tmp[--n];
    }
    return pos;
}

static int write_all(long fd, const u8 *buf, u64 len) {
    u64 off = 0;
    while (off < len) {
        long w = sc6(SYS_write, fd, (long)(buf + off), (long)(len - off), 0, 0, 0);
        if (w <= 0) {
            return -1;
        }
        off += (u64)w;
    }
    return 0;
}

static int check_header_magic(u32 magic_kind, const u8 *buf, u64 nread) {
    if (magic_kind == MAGIC_SECTOR0) {
        /* Offset 0: "8246" "2.00", Offset 8: LE u32 count == 30 */
        if (nread < 32) {
            return ERR_SECTOR0_MAGIC;
        }
        if (buf[0] != '8' || buf[1] != '2' || buf[2] != '4' || buf[3] != '6' ||
            buf[4] != '2' || buf[5] != '.' || buf[6] != '0' || buf[7] != '0') {
            return ERR_SECTOR0_MAGIC;
        }
        u32 count = (u32)buf[8] | ((u32)buf[9] << 8) | ((u32)buf[10] << 16) | ((u32)buf[11] << 24);
        if (count != 30u) {
            return ERR_SECTOR0_MAGIC;
        }
    } else if (magic_kind == MAGIC_BK4_BACKUP) {
        /* Offset 4: 0xaaaaaaaa, Offset 12: "BK4\0" */
        if (nread < 64) {
            return ERR_BK4_MAGIC;
        }
        u32 sync_word = (u32)buf[4] | ((u32)buf[5] << 8) | ((u32)buf[6] << 16) | ((u32)buf[7] << 24);
        if (sync_word != 0xaaaaaaaau ||
            buf[12] != 'B' || buf[13] != 'K' || buf[14] != '4' || buf[15] != '\0') {
            return ERR_BK4_MAGIC;
        }
    }
    return WORKER_OK;
}

static int query_source_size(long src_fd, u64 *out_size) {
    struct kstat st;
    for (u32 i = 0; i < sizeof(st); ++i) {
        ((volatile u8 *)&st)[i] = 0;
    }
    if (sc6(SYS_fstat, src_fd, (long)&st, 0, 0, 0, 0) != 0) {
        return ERR_SRC_STAT_FAILED;
    }
    if (st.size > 0) {
        *out_size = (u64)st.size;
        return WORKER_OK;
    }
    u64 blk_bytes = 0;
    if (sc6(SYS_ioctl, src_fd, BLKGETSIZE64, (long)&blk_bytes, 0, 0, 0) == 0 && blk_bytes > 0) {
        *out_size = blk_bytes;
        return WORKER_OK;
    }
    return ERR_SRC_STAT_FAILED;
}

static int validate_size_contract(const struct tier0_item_spec *spec, u64 sz) {
    if (sz == 0) {
        return ERR_SRC_SIZE_CONTRACT;
    }
    if (spec->exact_bytes != 0 && sz != spec->exact_bytes) {
        return ERR_SRC_SIZE_CONTRACT;
    }
    if (sz < spec->min_bytes || sz > spec->max_bytes) {
        return ERR_SRC_SIZE_CONTRACT;
    }
    if (spec->multiple_of > 1 && (sz % spec->multiple_of) != 0) {
        return ERR_SRC_SIZE_CONTRACT;
    }
    return WORKER_OK;
}

static int tier0_backup_worker_run_impl(void) {
    /* Step 0: Atomic in-process one-shot lock */
    if (__atomic_exchange_n(&g_worker_entered, 1, __ATOMIC_ACQ_REL) != 0) {
        return ERR_REENTRANT_LOCK;
    }

    /* Step 1: MANDATORY FIRST SYSCALL — unlinkat(AT_FDCWD, "/tmp/jiritsu/libJit.so", 0) */
    long ul_rc = sc6(SYS_unlinkat, AT_FDCWD, (long)"/tmp/jiritsu/libJit.so", 0, 0, 0, 0);
    if (ul_rc != 0) {
        g_worker_last_rc = ERR_UNLINK_LIBJIT_FAILED;
        return ERR_UNLINK_LIBJIT_FAILED;
    }

    /* Step 2: Create SD/CFexpress output directory /mnt/fx3_tier0_backup */
    long mk_rc = sc6(SYS_mkdirat, AT_FDCWD, (long)"/mnt/fx3_tier0_backup", 0700, 0, 0, 0);
    if (mk_rc != 0 && mk_rc != EEXIST_NEG) {
        g_worker_last_rc = ERR_MKDIR_BACKUP_FAILED;
        return ERR_MKDIR_BACKUP_FAILED;
    }

    u64 item_sizes[11];
    char pass1_hex[11][65];
    char pass2_hex[11][65];

    for (u32 idx = 0; idx < 11; ++idx) {
        const struct tier0_item_spec *spec = &TIER0_ITEMS[idx];

        /* ---- PASS 1: Strict O_RDONLY | O_NOFOLLOW open + magic check + exclusive dump ---- */
        long src_fd1 = sc6(SYS_openat, AT_FDCWD, (long)spec->src_path, O_RDONLY_SAFE, 0, 0, 0);
        if (src_fd1 < 0) {
            g_worker_last_rc = ERR_SRC_OPEN_FAILED;
            return ERR_SRC_OPEN_FAILED;
        }

        u64 total_size = 0;
        int sz_rc = query_source_size(src_fd1, &total_size);
        if (sz_rc != WORKER_OK) {
            sc6(SYS_close, src_fd1, 0, 0, 0, 0, 0);
            g_worker_last_rc = sz_rc;
            return sz_rc;
        }
        int ctr_rc = validate_size_contract(spec, total_size);
        if (ctr_rc != WORKER_OK) {
            sc6(SYS_close, src_fd1, 0, 0, 0, 0, 0);
            g_worker_last_rc = ctr_rc;
            return ctr_rc;
        }
        /* Enforce boot0 == boot1 size symmetry immediately on boot1 */
        if (idx == 2 && total_size != item_sizes[1]) {
            sc6(SYS_close, src_fd1, 0, 0, 0, 0, 0);
            g_worker_last_rc = ERR_BOOT_SYMMETRY;
            return ERR_BOOT_SYMMETRY;
        }
        item_sizes[idx] = total_size;

        /* Pre-read first chunk & verify header magic BEFORE opening output file */
        u64 first_chunk = total_size < CHUNK_BYTES ? total_size : CHUNK_BYTES;
        long r0 = sc6(SYS_pread64, src_fd1, (long)g_io_buf, (long)first_chunk, 0, 0, 0);
        if (r0 != (long)first_chunk) {
            sc6(SYS_close, src_fd1, 0, 0, 0, 0, 0);
            g_worker_last_rc = ERR_PREAD_SHORT_OR_IO;
            return ERR_PREAD_SHORT_OR_IO;
        }
        int mg_rc = check_header_magic(spec->magic_kind, g_io_buf, first_chunk);
        if (mg_rc != WORKER_OK) {
            sc6(SYS_close, src_fd1, 0, 0, 0, 0, 0);
            g_worker_last_rc = mg_rc;
            return mg_rc;
        }

        /* Open destination exclusively (O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW) */
        long out_fd = sc6(SYS_openat, AT_FDCWD, (long)spec->dst_path, O_WRONLY_EXCL, 0600, 0, 0);
        if (out_fd < 0) {
            sc6(SYS_close, src_fd1, 0, 0, 0, 0, 0);
            g_worker_last_rc = ERR_DST_OPEN_EXCL_FAILED;
            return ERR_DST_OPEN_EXCL_FAILED;
        }

        struct sha256_ctx ctx1;
        sha256_init(&ctx1);

        u64 offset = 0;
        while (offset < total_size) {
            u64 want = (total_size - offset) < CHUNK_BYTES ? (total_size - offset) : CHUNK_BYTES;
            if (offset > 0) {
                long rn = sc6(SYS_pread64, src_fd1, (long)g_io_buf, (long)want, (long)offset, 0, 0);
                if (rn != (long)want) {
                    sc6(SYS_close, out_fd, 0, 0, 0, 0, 0);
                    sc6(SYS_unlinkat, AT_FDCWD, (long)spec->dst_path, 0, 0, 0, 0);
                    sc6(SYS_close, src_fd1, 0, 0, 0, 0, 0);
                    g_worker_last_rc = ERR_PREAD_SHORT_OR_IO;
                    return ERR_PREAD_SHORT_OR_IO;
                }
            }
            sha256_update(&ctx1, g_io_buf, want);
            if (write_all(out_fd, g_io_buf, want) != 0) {
                sc6(SYS_close, out_fd, 0, 0, 0, 0, 0);
                sc6(SYS_unlinkat, AT_FDCWD, (long)spec->dst_path, 0, 0, 0, 0);
                sc6(SYS_close, src_fd1, 0, 0, 0, 0, 0);
                g_worker_last_rc = ERR_DST_WRITE_FAILED;
                return ERR_DST_WRITE_FAILED;
            }
            offset += want;
        }

        long fs_rc = sc6(SYS_fsync, out_fd, 0, 0, 0, 0, 0);
        long co_rc = sc6(SYS_close, out_fd, 0, 0, 0, 0, 0);
        long ci_rc = sc6(SYS_close, src_fd1, 0, 0, 0, 0, 0);
        if (fs_rc != 0 || co_rc != 0 || ci_rc != 0) {
            g_worker_last_rc = ERR_DST_FSYNC_CLOSE_FAILED;
            return ERR_DST_FSYNC_CLOSE_FAILED;
        }

        u8 digest1[32];
        sha256_final(&ctx1, digest1);
        hex_encode_32(digest1, pass1_hex[idx]);

        /* ---- PASS 2: Independent re-open & full pread64 re-verification ---- */
        long src_fd2 = sc6(SYS_openat, AT_FDCWD, (long)spec->src_path, O_RDONLY_SAFE, 0, 0, 0);
        if (src_fd2 < 0) {
            g_worker_last_rc = ERR_PASS2_OPEN_FAILED;
            return ERR_PASS2_OPEN_FAILED;
        }

        struct sha256_ctx ctx2;
        sha256_init(&ctx2);

        u64 off2 = 0;
        while (off2 < total_size) {
            u64 want2 = (total_size - off2) < CHUNK_BYTES ? (total_size - off2) : CHUNK_BYTES;
            long r2 = sc6(SYS_pread64, src_fd2, (long)g_io_buf, (long)want2, (long)off2, 0, 0);
            if (r2 != (long)want2) {
                sc6(SYS_close, src_fd2, 0, 0, 0, 0, 0);
                g_worker_last_rc = ERR_PASS2_PREAD_FAILED;
                return ERR_PASS2_PREAD_FAILED;
            }
            if (off2 == 0) {
                int mg2 = check_header_magic(spec->magic_kind, g_io_buf, want2);
                if (mg2 != WORKER_OK) {
                    sc6(SYS_close, src_fd2, 0, 0, 0, 0, 0);
                    g_worker_last_rc = mg2;
                    return mg2;
                }
            }
            sha256_update(&ctx2, g_io_buf, want2);
            off2 += want2;
        }

        if (sc6(SYS_close, src_fd2, 0, 0, 0, 0, 0) != 0) {
            g_worker_last_rc = ERR_PASS2_PREAD_FAILED;
            return ERR_PASS2_PREAD_FAILED;
        }

        u8 digest2[32];
        sha256_final(&ctx2, digest2);
        hex_encode_32(digest2, pass2_hex[idx]);

        if (!digest_equal_ct(digest1, digest2)) {
            g_worker_last_rc = ERR_TWOPASS_SHA256_MISMATCH;
            return ERR_TWOPASS_SHA256_MISMATCH;
        }
    }

    /* Step 3: Derive camera_body_tag (SHA-256 of sector0 Pass-1, 64 lowercase hex chars)
     * and emit JSON manifest strictly matching fx3_safety.preflight.verify_tier0_backup_manifest */
    u32 pos = 0;
    const u32 cap = sizeof(g_manifest_buf);
    pos = append_str(g_manifest_buf, pos, cap, "{\n  \"schema\": \"fx3-tier0-backup-manifest-v1\",\n  \"camera_body_tag\": \"");
    pos = append_str(g_manifest_buf, pos, cap, pass1_hex[0]);
    pos = append_str(g_manifest_buf, pos, cap, "\",\n  \"model_id\": \"0x91030080\",\n  \"items\": {\n");

    for (u32 idx = 0; idx < 11; ++idx) {
        pos = append_str(g_manifest_buf, pos, cap, "    \"");
        pos = append_str(g_manifest_buf, pos, cap, TIER0_ITEMS[idx].key);
        pos = append_str(g_manifest_buf, pos, cap, "\": {\"bytes\": ");
        pos = append_u64_dec(g_manifest_buf, pos, cap, item_sizes[idx]);
        pos = append_str(g_manifest_buf, pos, cap, ", \"pass1_sha256\": \"");
        pos = append_str(g_manifest_buf, pos, cap, pass1_hex[idx]);
        pos = append_str(g_manifest_buf, pos, cap, "\", \"pass2_sha256\": \"");
        pos = append_str(g_manifest_buf, pos, cap, pass2_hex[idx]);
        pos = append_str(g_manifest_buf, pos, cap, idx < 10 ? "\"},\n" : "\"}\n");
    }
    pos = append_str(g_manifest_buf, pos, cap, "  }\n}\n");

    long man_fd = sc6(
        SYS_openat,
        AT_FDCWD,
        (long)"/mnt/fx3_tier0_backup/manifest.json",
        O_WRONLY_EXCL,
        0600,
        0,
        0
    );
    if (man_fd < 0) {
        g_worker_last_rc = ERR_MANIFEST_WRITE_FAILED;
        return ERR_MANIFEST_WRITE_FAILED;
    }
    if (write_all(man_fd, (const u8 *)g_manifest_buf, (u64)pos) != 0 ||
        sc6(SYS_fsync, man_fd, 0, 0, 0, 0, 0) != 0 ||
        sc6(SYS_close, man_fd, 0, 0, 0, 0, 0) != 0) {
        sc6(SYS_close, man_fd, 0, 0, 0, 0, 0);
        g_worker_last_rc = ERR_MANIFEST_WRITE_FAILED;
        return ERR_MANIFEST_WRITE_FAILED;
    }

    sc6(SYS_sync, 0, 0, 0, 0, 0, 0);
    g_worker_last_rc = WORKER_OK;
    return WORKER_OK;
}

__attribute__((visibility("default"))) int tier0_backup_worker_run(void) {
    return tier0_backup_worker_run_impl();
}

/* DT_INIT shared-object constructor entrypoint invoked on dlopen("/tmp/jiritsu/libJit.so", RTLD_LAZY) */
__attribute__((visibility("default"))) void tier0_backup_worker_init(void) {
    (void)tier0_backup_worker_run_impl();
}
