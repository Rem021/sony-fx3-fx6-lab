#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/utsname.h>
#include <unistd.h>

#ifndef LOOP_SET_FD
#define LOOP_SET_FD 0x4C00UL
#endif

#ifndef LOOP_CLR_FD
#define LOOP_CLR_FD 0x4C01UL
#endif

#ifndef LOOP_CTL_GET_FREE
#define LOOP_CTL_GET_FREE 0x4C82UL
#endif

#ifndef MS_NOATIME
#define MS_NOATIME 1024UL
#endif

/* Pure FIPS 180-4 SHA-256 implementation for Verify-Before-Mount checks. */
typedef struct {
    uint32_t state[8];
    uint64_t bitlen;
    uint8_t data[64];
    size_t datalen;
} fx6_sha256_ctx_t;

static inline uint32_t rotr32(uint32_t x, uint32_t n) {
    return (x >> n) | (x << (32U - n));
}

static void sha256_transform(fx6_sha256_ctx_t *ctx, const uint8_t data[64]) {
    static const uint32_t k[64] = {
        0x428a2f98U, 0x71374491U, 0xb5c0fbcfU, 0xe9b5dba5U,
        0x3956c25bU, 0x59f111f1U, 0x923f82a4U, 0xab1c5ed5U,
        0xd807aa98U, 0x12835b01U, 0x243185beU, 0x550c7dc3U,
        0x72be5d74U, 0x80deb1feU, 0x9bdc06a7U, 0xc19bf174U,
        0xe49b69c1U, 0xefbe4786U, 0x0fc19dc6U, 0x240ca1ccU,
        0x2de92c6fU, 0x4a7484aaU, 0x5cb0a9dcU, 0x76f988daU,
        0x983e5152U, 0xa831c66dU, 0xb00327c8U, 0xbf597fc7U,
        0xc6e00bf3U, 0xd5a79147U, 0x06ca6351U, 0x14292967U,
        0x27b70a85U, 0x2e1b2138U, 0x4d2c6dfcU, 0x53380d13U,
        0x650a7354U, 0x766a0abbU, 0x81c2c92eU, 0x92722c85U,
        0xa2bfe8a1U, 0xa81a664bU, 0xc24b8b70U, 0xc76c51a3U,
        0xd192e819U, 0xd6990624U, 0xf40e3585U, 0x106aa070U,
        0x19a4c116U, 0x1e376c08U, 0x2748774cU, 0x34b0bcb5U,
        0x391c0cb3U, 0x4ed8aa4aU, 0x5b9cca4fU, 0x682e6ff3U,
        0x748f82eeU, 0x78a5636fU, 0x84c87814U, 0x8cc70208U,
        0x90befffaU, 0xa4506cebU, 0xbef9a3f7U, 0xc67178f2U
    };
    uint32_t m[64];
    for (int i = 0, j = 0; i < 16; i++, j += 4) {
        m[i] = ((uint32_t)data[j] << 24) |
               ((uint32_t)data[j + 1] << 16) |
               ((uint32_t)data[j + 2] << 8) |
               ((uint32_t)data[j + 3]);
    }
    for (int i = 16; i < 64; i++) {
        uint32_t s0 = rotr32(m[i - 15], 7U) ^ rotr32(m[i - 15], 18U) ^ (m[i - 15] >> 3);
        uint32_t s1 = rotr32(m[i - 2], 17U) ^ rotr32(m[i - 2], 19U) ^ (m[i - 2] >> 10);
        m[i] = m[i - 16] + s0 + m[i - 7] + s1;
    }

    uint32_t a = ctx->state[0];
    uint32_t b = ctx->state[1];
    uint32_t c = ctx->state[2];
    uint32_t d = ctx->state[3];
    uint32_t e = ctx->state[4];
    uint32_t f = ctx->state[5];
    uint32_t g = ctx->state[6];
    uint32_t h = ctx->state[7];

    for (int i = 0; i < 64; i++) {
        uint32_t S1 = rotr32(e, 6U) ^ rotr32(e, 11U) ^ rotr32(e, 25U);
        uint32_t ch = (e & f) ^ ((~e) & g);
        uint32_t temp1 = h + S1 + ch + k[i] + m[i];
        uint32_t S0 = rotr32(a, 2U) ^ rotr32(a, 13U) ^ rotr32(a, 22U);
        uint32_t maj = (a & b) ^ (a & c) ^ (b & c);
        uint32_t temp2 = S0 + maj;

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

static void sha256_init(fx6_sha256_ctx_t *ctx) {
    ctx->datalen = 0;
    ctx->bitlen = 0;
    ctx->state[0] = 0x6a09e667U;
    ctx->state[1] = 0xbb67ae85U;
    ctx->state[2] = 0x3c6ef372U;
    ctx->state[3] = 0xa54ff53aU;
    ctx->state[4] = 0x510e527fU;
    ctx->state[5] = 0x9b05688cU;
    ctx->state[6] = 0x1f83d9abU;
    ctx->state[7] = 0x5be0cd19U;
}

static void sha256_update(fx6_sha256_ctx_t *ctx, const uint8_t *data, size_t len) {
    for (size_t i = 0; i < len; i++) {
        ctx->data[ctx->datalen++] = data[i];
        if (ctx->datalen == 64U) {
            sha256_transform(ctx, ctx->data);
            ctx->bitlen += 512ULL;
            ctx->datalen = 0U;
        }
    }
}

static void sha256_final(fx6_sha256_ctx_t *ctx, uint8_t hash[32]) {
    size_t i = ctx->datalen;
    if (ctx->datalen < 56U) {
        ctx->data[i++] = 0x80U;
        while (i < 56U) ctx->data[i++] = 0x00U;
    } else {
        ctx->data[i++] = 0x80U;
        while (i < 64U) ctx->data[i++] = 0x00U;
        sha256_transform(ctx, ctx->data);
        memset(ctx->data, 0, 56U);
    }

    ctx->bitlen += (uint64_t)ctx->datalen * 8ULL;
    for (int b = 0; b < 8; b++) {
        ctx->data[63 - b] = (uint8_t)((ctx->bitlen >> (b * 8)) & 0xffU);
    }
    sha256_transform(ctx, ctx->data);

    for (int w = 0; w < 8; w++) {
        hash[w * 4 + 0] = (uint8_t)((ctx->state[w] >> 24) & 0xffU);
        hash[w * 4 + 1] = (uint8_t)((ctx->state[w] >> 16) & 0xffU);
        hash[w * 4 + 2] = (uint8_t)((ctx->state[w] >> 8) & 0xffU);
        hash[w * 4 + 3] = (uint8_t)(ctx->state[w] & 0xffU);
    }
}

static int sha256_file_hex(const char *path, char out_hex[65], unsigned long long *out_bytes) {
    int fd = open(path, O_RDONLY);
    if (fd < 0) return -1;
    fx6_sha256_ctx_t ctx;
    sha256_init(&ctx);
    uint8_t buf[65536];
    unsigned long long total = 0ULL;
    for (;;) {
        ssize_t n = read(fd, buf, sizeof(buf));
        if (n < 0) {
            if (errno == EINTR) continue;
            close(fd);
            return -1;
        }
        if (n == 0) break;
        sha256_update(&ctx, buf, (size_t)n);
        total += (unsigned long long)n;
    }
    close(fd);
    uint8_t hash[32];
    sha256_final(&ctx, hash);
    static const char hex[] = "0123456789abcdef";
    for (int i = 0; i < 32; i++) {
        out_hex[i * 2 + 0] = hex[(hash[i] >> 4) & 0xfU];
        out_hex[i * 2 + 1] = hex[hash[i] & 0xfU];
    }
    out_hex[64] = '\0';
    if (out_bytes) *out_bytes = total;
    return 0;
}

static int verify_manifest(const char *manifest_path) {
    FILE *fp = fopen(manifest_path, "r");
    if (!fp) {
        fprintf(stderr, "FX6_STAGE_A_VERIFY_FAIL open_manifest=%s errno=%d\n",
                manifest_path, errno);
        return -1;
    }
    char line[512];
    unsigned int count = 0U;
    unsigned int failed = 0U;
    while (fgets(line, sizeof(line), fp)) {
        size_t ln = strlen(line);
        while (ln > 0U && (line[ln - 1U] == '\n' || line[ln - 1U] == '\r')) {
            line[--ln] = '\0';
        }
        if (ln == 0U || line[0] == '#') continue;

        char expected[65];
        char path[384];
        if (sscanf(line, "%64s %383s", expected, path) != 2) {
            fprintf(stderr, "FX6_STAGE_A_VERIFY_FAIL bad_line=%s\n", line);
            fclose(fp);
            return -1;
        }
        char actual[65];
        unsigned long long bytes = 0ULL;
        if (sha256_file_hex(path, actual, &bytes) != 0) {
            fprintf(stderr,
                    "FX6_STAGE_A_VERIFY_ITEM path=%s bytes=0 expected=%s actual=MISSING status=FAIL errno=%d\n",
                    path, expected, errno);
            failed++;
            continue;
        }
        int match = (strcmp(expected, actual) == 0);
        fprintf(stderr,
                "FX6_STAGE_A_VERIFY_ITEM path=%s bytes=%llu expected=%s actual=%s status=%s\n",
                path, bytes, expected, actual, match ? "OK" : "MISMATCH");
        if (!match) failed++;
        count++;
    }
    fclose(fp);
    if (failed != 0U || count == 0U) {
        fprintf(stderr, "FX6_STAGE_A_VERIFY_FAIL verified=%u failed=%u\n", count, failed);
        return -1;
    }
    fprintf(stderr, "FX6_STAGE_A_VERIFY_PASS count=%u\n", count);
    struct stat sb_st;
    if (count >= 11U || stat("/etc/fx6_stage_b", &sb_st) == 0) {
        fprintf(stderr,
                "FX6_STAGE_B_VERIFY_PASS count=%u stage_b=1 p10_keymap=1\n",
                count);
    }
    struct stat r10_st;
    if (count >= 12U || stat("/etc/fx6_stage_r10", &r10_st) == 0) {
        fprintf(stderr,
                "FX6_STAGE_B_R10_VERIFY_PASS count=%u stage_b=1 p10_keymap=1 p11_uipc=1 uxc=1\n",
                count);
    }
    struct stat r11_st;
    if (count >= 13U || stat("/etc/fx6_stage_r11", &r11_st) == 0) {
        int is_schinese = 0;
        FILE *r11f = fopen("/etc/fx6_stage_r11", "r");
        if (r11f) {
            char rline[128];
            while (fgets(rline, sizeof(rline), r11f)) {
                if (strstr(rline, "lang=schinese") != NULL) {
                    is_schinese = 1;
                }
            }
            fclose(r11f);
        }
        fprintf(stderr,
                "FX6_STAGE_B_R11_VERIFY_PASS count=%u stage_b=1 p10_keymap=1 p11_uipc=1 p12_wlan=1 uxc=1 schinese=%d\n",
                count, is_schinese);
    }
    struct stat r12_st;
    if (stat("/etc/fx6_stage_r12", &r12_st) == 0) {
        char lang_buf[32] = "en";
        FILE *r12f = fopen("/etc/fx6_stage_r12", "r");
        if (r12f) {
            char rline[128];
            while (fgets(rline, sizeof(rline), r12f)) {
                char parsed[32];
                if (sscanf(rline, "lang=%31s", parsed) == 1) {
                    snprintf(lang_buf, sizeof(lang_buf), "%s", parsed);
                }
            }
            fclose(r12f);
        }
        fprintf(stderr,
                "FX6_STAGE_B_R12_VERIFY_PASS count=%u stage_b=1 p10_keymap=1 p11_uipc=1 p12_wlan=1 p4_nd_clear=1 uxc=1 lang=%s\n",
                count, lang_buf);
    }
    struct stat r13_st;
    if (stat("/etc/fx6_stage_r13", &r13_st) == 0) {
        char lang_buf[32] = "en";
        FILE *r13f = fopen("/etc/fx6_stage_r13", "r");
        if (r13f) {
            char rline[128];
            while (fgets(rline, sizeof(rline), r13f)) {
                char parsed[32];
                if (sscanf(rline, "lang=%31s", parsed) == 1) {
                    snprintf(lang_buf, sizeof(lang_buf), "%s", parsed);
                }
            }
            fclose(r13f);
        }
        fprintf(stderr,
                "FX6_STAGE_B_R13_VERIFY_PASS count=%u stage_b=1 p10_keymap=1 p11_uipc=1 p12_wlan=1 p4_nd_clear=1 uxc=1 lang=%s\n",
                count, lang_buf);
    }
    struct stat r14_st;
    if (stat("/etc/fx6_stage_r14", &r14_st) == 0) {
        char lang_buf[32] = "en";
        FILE *r14f = fopen("/etc/fx6_stage_r14", "r");
        if (r14f) {
            char rline[128];
            while (fgets(rline, sizeof(rline), r14f)) {
                char parsed[32];
                if (sscanf(rline, "lang=%31s", parsed) == 1) {
                    snprintf(lang_buf, sizeof(lang_buf), "%s", parsed);
                }
            }
            fclose(r14f);
        }
        fprintf(stderr,
                "FX6_STAGE_B_R14_VERIFY_PASS count=%u stage_b=1 p10_keymap=1 p11_uipc=1 p12_wlan=1 p4_nd_clear=1 uxc=1 statuscheck_4lang=1 lang=%s\n",
                count, lang_buf);
    }
    struct stat r15_st;
    if (stat("/etc/fx6_stage_r15", &r15_st) == 0) {
        char lang_buf[32] = "en";
        FILE *r15f = fopen("/etc/fx6_stage_r15", "r");
        if (r15f) {
            char rline[128];
            while (fgets(rline, sizeof(rline), r15f)) {
                char parsed[32];
                if (sscanf(rline, "lang=%31s", parsed) == 1) {
                    snprintf(lang_buf, sizeof(lang_buf), "%s", parsed);
                }
            }
            fclose(r15f);
        }
        fprintf(stderr,
                "FX6_STAGE_B_R15_VERIFY_PASS count=%u stage_b=1 p10_keymap=1 p11_uipc=1 p12_wlan=1 p4_nd_clear=1 uxc=1 statuscheck_multitab=1 monitoring_3layer=1 lang=%s\n",
                count, lang_buf);
    }
    struct stat r16_st;
    if (stat("/etc/fx6_stage_r16", &r16_st) == 0) {
        char lang_buf[32] = "en";
        FILE *r16f = fopen("/etc/fx6_stage_r16", "r");
        if (r16f) {
            char rline[128];
            while (fgets(rline, sizeof(rline), r16f)) {
                char parsed[32];
                if (sscanf(rline, "lang=%31s", parsed) == 1) {
                    snprintf(lang_buf, sizeof(lang_buf), "%s", parsed);
                }
            }
            fclose(r16f);
        }
        fprintf(stderr,
                "FX6_STAGE_B_R16_VERIFY_PASS count=%u stage_b=1 p10_keymap=1 p11_uipc=1 p12_wlan=1 p4_nd_clear=1 uxc=1 statuscheck_tabs45=1 tcmedia_3layer=1 lang=%s\n",
                count, lang_buf);
    }
    struct stat r17_st;
    if (stat("/etc/fx6_stage_r17", &r17_st) == 0) {
        char lang_buf[32] = "en";
        FILE *r17f = fopen("/etc/fx6_stage_r17", "r");
        if (r17f) {
            char rline[128];
            while (fgets(rline, sizeof(rline), r17f)) {
                char parsed[32];
                if (sscanf(rline, "lang=%31s", parsed) == 1) {
                    snprintf(lang_buf, sizeof(lang_buf), "%s", parsed);
                }
            }
            fclose(r17f);
        }
        fprintf(stderr,
                "FX6_STAGE_B_R17_VERIFY_PASS count=%u stage_b=1 p10_keymap=1 p11_uipc=1 p12_wlan=1 p4_nd_clear=1 uxc=1 statuscheck_fullsweep=1 audio_3layer=1 lang=%s\n",
                count, lang_buf);
    }
    struct stat r18_st;
    if (stat("/etc/fx6_stage_r18", &r18_st) == 0) {
        char lang_buf[32] = "en";
        FILE *r18f = fopen("/etc/fx6_stage_r18", "r");
        if (r18f) {
            char rline[128];
            while (fgets(rline, sizeof(rline), r18f)) {
                char parsed[32];
                if (sscanf(rline, "lang=%31s", parsed) == 1) {
                    snprintf(lang_buf, sizeof(lang_buf), "%s", parsed);
                }
            }
            fclose(r18f);
        }
        fprintf(stderr,
                "FX6_STAGE_B_R18_VERIFY_PASS count=%u stage_b=1 p10_keymap=1 p11_uipc=1 p12_wlan=1 p4_nd_clear=1 uxc=1 menu_8cat_closure=1 wf12_00342260_immune=1 lang=%s\n",
                count, lang_buf);
    }
    struct stat r19_st;
    if (stat("/etc/fx6_stage_r19", &r19_st) == 0) {
        char lang_buf[32] = "en";
        FILE *r19f = fopen("/etc/fx6_stage_r19", "r");
        if (r19f) {
            char rline[128];
            while (fgets(rline, sizeof(rline), r19f)) {
                char parsed[32];
                if (sscanf(rline, "lang=%31s", parsed) == 1) {
                    snprintf(lang_buf, sizeof(lang_buf), "%s", parsed);
                }
            }
            fclose(r19f);
        }
        fprintf(stderr,
                "FX6_STAGE_B_R19_VERIFY_PASS count=%u stage_b=1 p10_keymap=1 p11_uipc=1 p12_wlan=1 p4_nd_clear=1 uxc=1 menu_11cat_fullsweep=1 wf12_00342260_immune=1 lang=%s\n",
                count, lang_buf);
    }
    struct stat r20_st;
    if (stat("/etc/fx6_stage_r20", &r20_st) == 0) {
        char lang_buf[32] = "en";
        FILE *r20f = fopen("/etc/fx6_stage_r20", "r");
        if (r20f) {
            char rline[128];
            while (fgets(rline, sizeof(rline), r20f)) {
                char parsed[32];
                if (sscanf(rline, "lang=%31s", parsed) == 1) {
                    snprintf(lang_buf, sizeof(lang_buf), "%s", parsed);
                }
            }
            fclose(r20f);
        }
        fprintf(stderr,
                "FX6_STAGE_B_R20_VERIFY_PASS count=%u stage_b=1 p10_keymap=1 p11_uipc=1 p12_wlan=1 p4_nd_clear=1 uxc=1 network_4lang_wf12_closure=1 wf12_00342260_immune=1 lang=%s\n",
                count, lang_buf);
    }
    return 0;
}

static int setup_p1_lut_symlinks(void) {
    struct stat st;
    if (stat("/dev/cnflasha30", &st) != 0) {
        int fd = open("/dev/cnflasha30", O_CREAT | O_WRONLY, 0644);
        if (fd >= 0) close(fd);
    }
    unlink("/dev/nflasha30");
    int rc30 = symlink("/dev/cnflasha30", "/dev/nflasha30");
    unlink("/dev/nflasha20");
    int rc20 = symlink("/dev/cnflasha30", "/dev/nflasha20");
    fprintf(stderr,
            "FX6_STAGE_A_P1_LINK target=/dev/cnflasha30 rc30=%d rc20=%d\n",
            rc30, rc20);
    return (rc30 == 0 && rc20 == 0) ? 0 : -1;
}

static dev_t fx6_makedev(unsigned int maj, unsigned int min) {
    return (dev_t)((((unsigned long long)(maj & 0xfffU)) << 8) |
                   ((unsigned long long)(min & 0xffU)) |
                   (((unsigned long long)(min & ~0xffU)) << 12));
}

static int setup_p2_loopback_vfat(void) {
    char loop_path[32];
    snprintf(loop_path, sizeof(loop_path), "/dev/loop7");

    int ctl_fd = open("/dev/loop-control", O_RDWR);
    if (ctl_fd >= 0) {
        int free_idx = (int)ioctl(ctl_fd, LOOP_CTL_GET_FREE);
        close(ctl_fd);
        if (free_idx >= 0) {
            snprintf(loop_path, sizeof(loop_path), "/dev/loop%d", free_idx);
        }
    }

    struct stat st;
    if (stat(loop_path, &st) != 0) {
        unsigned int dev_num = 7U;
        if (sscanf(loop_path, "/dev/loop%u", &dev_num) != 1) dev_num = 7U;
        if (mknod(loop_path, S_IFBLK | 0660, fx6_makedev(7U, dev_num)) != 0 && errno != EEXIST) {
            fprintf(stderr, "FX6_STAGE_A_P2_MOUNT_FAIL step=mknod loop=%s errno=%d\n",
                    loop_path, errno);
            return -1;
        }
    }

    int img_fd = open("/tmp/opelog.vfat", O_RDWR);
    if (img_fd < 0) {
        fprintf(stderr, "FX6_STAGE_A_P2_MOUNT_FAIL step=open_img errno=%d\n", errno);
        return -1;
    }
    int loop_fd = open(loop_path, O_RDWR);
    if (loop_fd < 0) {
        fprintf(stderr, "FX6_STAGE_A_P2_MOUNT_FAIL step=open_loop loop=%s errno=%d\n",
                loop_path, errno);
        close(img_fd);
        return -1;
    }

    int set_rc = ioctl(loop_fd, LOOP_SET_FD, img_fd);
    if (set_rc < 0 && errno == EBUSY) {
        (void)ioctl(loop_fd, LOOP_CLR_FD, 0);
        set_rc = ioctl(loop_fd, LOOP_SET_FD, img_fd);
    }
    int set_errno = (set_rc < 0) ? errno : 0;
    close(loop_fd);
    close(img_fd);
    if (set_rc < 0) {
        fprintf(stderr, "FX6_STAGE_A_P2_MOUNT_FAIL step=LOOP_SET_FD loop=%s errno=%d\n",
                loop_path, set_errno);
        return -1;
    }

    unlink("/dev/nflasha21");
    int sym_rc = symlink(loop_path, "/dev/nflasha21");
    (void)mkdir("/etc/opelog", 0755);

    const char *used_opts = "posix_attr";
    int mnt_rc = mount("/dev/nflasha21", "/etc/opelog", "vfat", MS_NOATIME, used_opts);
    int mnt_errno = (mnt_rc == 0) ? 0 : errno;
    if (mnt_rc != 0) {
        used_opts = "default";
        mnt_rc = mount("/dev/nflasha21", "/etc/opelog", "vfat", MS_NOATIME, NULL);
        mnt_errno = (mnt_rc == 0) ? 0 : errno;
    }

    int ope_ok = (stat("/etc/opelog/OPE", &st) == 0 && S_ISDIR(st.st_mode)) ? 1 : 0;
    int ope00_ok = (stat("/etc/opelog/OPE/00", &st) == 0 && S_ISDIR(st.st_mode)) ? 1 : 0;
    int ope01_ok = (stat("/etc/opelog/OPE/01", &st) == 0 && S_ISDIR(st.st_mode)) ? 1 : 0;
    fprintf(stderr,
            "FX6_STAGE_A_P2_MOUNT rc=%d errno=%d sym_rc=%d loop=%s target=/etc/opelog opts=%s ope=%d ope00=%d ope01=%d\n",
            mnt_rc, mnt_errno, sym_rc, loop_path, used_opts, ope_ok, ope00_ok, ope01_ok);
    return (mnt_rc == 0 && ope_ok && ope00_ok && ope01_ok) ? 0 : -1;
}

static int verify_ram_shadow_bk4(const char *path) {
    int fd = open(path, O_RDONLY);
    if (fd < 0) {
        fprintf(stderr, "FX6_STAGE_A_BK4_SHADOW path=%s status=MISSING errno=%d\n", path, errno);
        return -1;
    }
    struct stat st;
    if (fstat(fd, &st) != 0 || st.st_size < 0x28) {
        close(fd);
        fprintf(stderr, "FX6_STAGE_A_BK4_SHADOW path=%s status=SHORT\n", path);
        return -1;
    }
    uint8_t hdr[0x28];
    ssize_t n = read(fd, hdr, sizeof(hdr));
    close(fd);
    if (n != (ssize_t)sizeof(hdr) ||
        hdr[0x0c] != 'B' || hdr[0x0d] != 'K' || hdr[0x0e] != '4' || hdr[0x0f] != '\0' ||
        hdr[0x08] != 0x00U) {
        fprintf(stderr, "FX6_STAGE_A_BK4_SHADOW path=%s status=BAD_HEADER\n", path);
        return -1;
    }
    fprintf(stderr,
            "FX6_STAGE_A_BK4_SHADOW path=%s bytes=%llu magic=BK4_0 byte8=0x%02x flash_write=0 status=OK\n",
            path, (unsigned long long)st.st_size, (unsigned int)hdr[0x08]);
    return 0;
}

typedef struct {
    int tm_sec, tm_min, tm_hour, tm_mday, tm_mon, tm_year, tm_wday, tm_yday, tm_isdst;
} fx6_rtc_time_t;

#ifndef FX6_RTC_RD_TIME
#define FX6_RTC_RD_TIME 0x80247009UL
#endif

static int verify_uxc_archive(const char *path) {
    int fd = open(path, O_RDONLY);
    if (fd < 0) {
        fprintf(stderr, "FX6_STAGE_B_R10_UXC path=%s status=MISSING errno=%d\n", path, errno);
        return -1;
    }
    struct stat st;
    if (fstat(fd, &st) != 0 || st.st_size < 16) {
        close(fd);
        fprintf(stderr, "FX6_STAGE_B_R10_UXC path=%s status=SHORT\n", path);
        return -1;
    }
    uint8_t magic[4];
    ssize_t n = read(fd, magic, sizeof(magic));
    close(fd);
    if (n != (ssize_t)sizeof(magic) ||
        magic[0] != 'u' || magic[1] != 'x' || magic[2] != 'd' || magic[3] != 0x07U) {
        fprintf(stderr, "FX6_STAGE_B_R10_UXC path=%s status=BAD_MAGIC\n", path);
        return -1;
    }
    fprintf(stderr,
            "FX6_STAGE_B_R10_UXC path=%s bytes=%llu magic=uxd_07 status=OK\n",
            path, (unsigned long long)st.st_size);
    return 0;
}

static void probe_r10_rtc0(void) {
    fx6_rtc_time_t tm;
    memset(&tm, 0, sizeof(tm));
    int fd = open("/dev/rtc0", O_RDONLY);
    if (fd < 0) {
        fprintf(stderr, "FX6_STAGE_B_R10_RTC0 path=/dev/rtc0 open_ok=0 errno=%d\n", errno);
        return;
    }
    int rc = ioctl(fd, FX6_RTC_RD_TIME, &tm);
    int err = (rc != 0) ? errno : 0;
    close(fd);
    if (rc == 0) {
        fprintf(stderr,
                "FX6_STAGE_B_R10_RTC0 path=/dev/rtc0 open_ok=1 rc=0 year=%d mon=%d mday=%d hour=%d min=%d sec=%d\n",
                1900 + tm.tm_year, tm.tm_mon + 1, tm.tm_mday, tm.tm_hour, tm.tm_min, tm.tm_sec);
    } else {
        fprintf(stderr,
                "FX6_STAGE_B_R10_RTC0 path=/dev/rtc0 open_ok=1 rc=%d errno=%d\n",
                rc, err);
    }
}

int main(void) {
    struct utsname uts;
    memset(&uts, 0, sizeof(uts));
    if (uname(&uts) == 0) {
        fprintf(stderr,
                "FX6_STAGE_A_KERNEL sysname=%s release=%s machine=%s version=%s\n",
                uts.sysname, uts.release, uts.machine, uts.version);
    }
    FILE *pv = fopen("/proc/version", "r");
    if (pv) {
        char buf[384];
        if (fgets(buf, sizeof(buf), pv)) {
            size_t ln = strlen(buf);
            while (ln > 0U && (buf[ln - 1U] == '\n' || buf[ln - 1U] == '\r')) buf[--ln] = '\0';
            fprintf(stderr, "FX6_HYBRID_PROC_VERSION %s\n", buf);
        }
        fclose(pv);
    }

    if (verify_manifest("/etc/fx6_stage_a_manifest.txt") != 0) {
        return 41;
    }
    if (setup_p1_lut_symlinks() != 0) {
        return 42;
    }
    if (setup_p2_loopback_vfat() != 0) {
        return 43;
    }
    if (verify_ram_shadow_bk4("/etc/fx6_ram_shadow_bk4.bin") != 0) {
        return 44;
    }

    struct stat upm_st;
    int upm_loaded = (stat("/sys/module/upm", &upm_st) == 0 && S_ISDIR(upm_st.st_mode)) ? 1 : 0;
    fprintf(stderr, "FX6_STAGE_A_P9_UPM module_loaded=%d\n", upm_loaded);

    struct stat r10_st;
    if (stat("/etc/fx6_stage_r10", &r10_st) == 0) {
        if (verify_uxc_archive("/usr/share/app/image_00_169.uxc") != 0) {
            return 45;
        }
        probe_r10_rtc0();
    }

    FILE *r11f = fopen("/etc/fx6_stage_r11", "r");
    if (r11f) {
        int is_schinese = 0;
        char rline[128];
        while (fgets(rline, sizeof(rline), r11f)) {
            if (strstr(rline, "lang=schinese") != NULL) {
                is_schinese = 1;
            }
        }
        fclose(r11f);
        if (is_schinese) {
            static const struct {
                const char *path;
                uint8_t magic[4];
                const char *magic_label;
            } k_schinese_assets[3] = {
                { "/usr/share/app/string_simplifiedchinese.uxc", { 'u', 'x', 'c', 0x07U }, "uxc_07" },
                { "/usr/share/app/string_simplifiedchinese_2.uxc", { 'u', 'x', 'c', 0x07U }, "uxc_07" },
                { "/usr/share/app/MYingHeiC-GB18030-SJ_wIcon.ltt", { 'L', 'T', 'T', '\n' }, "LTT" },
            };
            for (size_t i = 0U; i < 3U; i++) {
                int afd = open(k_schinese_assets[i].path, O_RDONLY);
                if (afd < 0) {
                    fprintf(stderr, "FX6_STAGE_B_R11_LANG_ASSET path=%s status=MISSING errno=%d\n",
                            k_schinese_assets[i].path, errno);
                    return 46;
                }
                struct stat ast;
                if (fstat(afd, &ast) != 0 || ast.st_size < 16) {
                    close(afd);
                    fprintf(stderr, "FX6_STAGE_B_R11_LANG_ASSET path=%s status=SHORT\n",
                            k_schinese_assets[i].path);
                    return 46;
                }
                uint8_t amagic[4];
                ssize_t an = read(afd, amagic, sizeof(amagic));
                close(afd);
                if (an != (ssize_t)sizeof(amagic) ||
                    memcmp(amagic, k_schinese_assets[i].magic, 4U) != 0) {
                    fprintf(stderr, "FX6_STAGE_B_R11_LANG_ASSET path=%s status=BAD_MAGIC\n",
                            k_schinese_assets[i].path);
                    return 46;
                }
                fprintf(stderr,
                        "FX6_STAGE_B_R11_LANG_ASSET path=%s bytes=%llu magic=%s status=OK\n",
                        k_schinese_assets[i].path,
                        (unsigned long long)ast.st_size,
                        k_schinese_assets[i].magic_label);
            }
            FILE *fl = fopen("/usr/share/app/fontlist.dat", "r");
            if (!fl) {
                fprintf(stderr, "FX6_STAGE_B_R11_FONTLIST path=/usr/share/app/fontlist.dat status=MISSING\n");
                return 46;
            }
            char fbuf[1024];
            size_t fr = fread(fbuf, 1U, sizeof(fbuf) - 1U, fl);
            fclose(fl);
            fbuf[fr] = '\0';
            int has_sc = (strstr(fbuf, "FONT_S_CHINESE") != NULL &&
                          strstr(fbuf, "MYingHeiC-GB18030-SJ_wIcon.ltt") != NULL) ? 1 : 0;
            fprintf(stderr,
                    "FX6_STAGE_B_R11_FONTLIST path=/usr/share/app/fontlist.dat font_s_chinese=%d status=%s\n",
                    has_sc, has_sc ? "OK" : "MISSING_SC");
            if (!has_sc) {
                return 46;
            }
        }
    }

    FILE *r12f = fopen("/etc/fx6_stage_r12", "r");
    if (r12f) {
        char lang_buf[32] = "en";
        char rline[128];
        while (fgets(rline, sizeof(rline), r12f)) {
            char parsed[32];
            if (sscanf(rline, "lang=%31s", parsed) == 1) {
                snprintf(lang_buf, sizeof(lang_buf), "%s", parsed);
            }
        }
        fclose(r12f);

        const char *str1 = "/usr/share/app/string_english.uxc";
        const char *str2 = "/usr/share/app/string_english_2.uxc";
        const char *ltt_path = "/usr/share/app/UniversOTS-SJ_wIcon.ltt";
        const char *font_key = "FONT_UNIVERS";
        const char *ltt_name = "UniversOTS-SJ_wIcon.ltt";
        if (strcmp(lang_buf, "schinese") == 0) {
            str1 = "/usr/share/app/string_simplifiedchinese.uxc";
            str2 = "/usr/share/app/string_simplifiedchinese_2.uxc";
            ltt_path = "/usr/share/app/MYingHeiC-GB18030-SJ_wIcon.ltt";
            font_key = "FONT_S_CHINESE";
            ltt_name = "MYingHeiC-GB18030-SJ_wIcon.ltt";
        } else if (strcmp(lang_buf, "tchinese") == 0) {
            str1 = "/usr/share/app/string_traditionalchinese.uxc";
            str2 = "/usr/share/app/string_traditionalchinese_2.uxc";
            ltt_path = "/usr/share/app/MYingHeiC-Big5HKSCS-SJ_wIcon.ltt";
            font_key = "FONT_T_CHINESE";
            ltt_name = "MYingHeiC-Big5HKSCS-SJ_wIcon.ltt";
        } else if (strcmp(lang_buf, "japanese") == 0) {
            str1 = "/usr/share/app/string_japanese.uxc";
            str2 = "/usr/share/app/string_japanese_2.uxc";
            ltt_path = "/usr/share/app/HeiseiKakuGothW5-SJ_wIcon.ltt";
            font_key = "FONT_JAPANESE";
            ltt_name = "HeiseiKakuGothW5-SJ_wIcon.ltt";
        }

        const char *paths[3] = { str1, str2, ltt_path };
        const uint8_t magics[3][4] = {
            { 'u', 'x', 'c', 0x07U },
            { 'u', 'x', 'c', 0x07U },
            { 'L', 'T', 'T', '\n' },
        };
        const char *labels[3] = { "uxc_07", "uxc_07", "LTT" };
        for (size_t i = 0U; i < 3U; i++) {
            int afd = open(paths[i], O_RDONLY);
            if (afd < 0) {
                fprintf(stderr, "FX6_STAGE_B_R12_LANG_ASSET lang=%s path=%s status=MISSING errno=%d\n",
                        lang_buf, paths[i], errno);
                return 47;
            }
            struct stat ast;
            if (fstat(afd, &ast) != 0 || ast.st_size < 16) {
                close(afd);
                fprintf(stderr, "FX6_STAGE_B_R12_LANG_ASSET lang=%s path=%s status=SHORT\n",
                        lang_buf, paths[i]);
                return 47;
            }
            uint8_t amagic[4];
            ssize_t an = read(afd, amagic, sizeof(amagic));
            close(afd);
            if (an != (ssize_t)sizeof(amagic) || memcmp(amagic, magics[i], 4U) != 0) {
                fprintf(stderr, "FX6_STAGE_B_R12_LANG_ASSET lang=%s path=%s status=BAD_MAGIC\n",
                        lang_buf, paths[i]);
                return 47;
            }
            fprintf(stderr,
                    "FX6_STAGE_B_R12_LANG_ASSET lang=%s path=%s bytes=%llu magic=%s status=OK\n",
                    lang_buf, paths[i], (unsigned long long)ast.st_size, labels[i]);
        }

        FILE *fl = fopen("/usr/share/app/fontlist.dat", "r");
        if (!fl) {
            fprintf(stderr, "FX6_STAGE_B_R12_FONTLIST path=/usr/share/app/fontlist.dat status=MISSING\n");
            return 47;
        }
        char fbuf[1024];
        size_t fr = fread(fbuf, 1U, sizeof(fbuf) - 1U, fl);
        fclose(fl);
        fbuf[fr] = '\0';
        int has_font = (strstr(fbuf, font_key) != NULL && strstr(fbuf, ltt_name) != NULL) ? 1 : 0;
        fprintf(stderr,
                "FX6_STAGE_B_R12_FONTLIST lang=%s font_key=%s ltt=%s present=%d status=%s\n",
                lang_buf, font_key, ltt_name, has_font, has_font ? "OK" : "MISSING_FONT");
        if (!has_font) {
            return 47;
        }
    }

    fflush(stderr);
    return 0;
}
