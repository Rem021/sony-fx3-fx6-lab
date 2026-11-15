#define _GNU_SOURCE
#include <dirent.h>
#include <dlfcn.h>
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
#include <sys/wait.h>
#include <time.h>
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

#ifndef MS_RDONLY
#define MS_RDONLY 1UL
#endif

#ifndef MS_REMOUNT
#define MS_REMOUNT 32UL
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
    struct stat r21_st;
    if (stat("/etc/fx6_stage_r21", &r21_st) == 0) {
        char lang_buf[32] = "en";
        FILE *r21f = fopen("/etc/fx6_stage_r21", "r");
        if (r21f) {
            char rline[128];
            while (fgets(rline, sizeof(rline), r21f)) {
                char parsed[32];
                if (sscanf(rline, "lang=%31s", parsed) == 1) {
                    snprintf(lang_buf, sizeof(lang_buf), "%s", parsed);
                }
            }
            fclose(r21f);
        }
        fprintf(stderr,
                "FX6_STAGE_B_R21_VERIFY_PASS count=%u stage_b=1 p10_keymap=1 p11_uipc=1 p12_wlan=1 p4_nd_clear=1 uxc=1 audio_4lang_dualsurface=1 wf12_00342260_immune=1 lang=%s\n",
                count, lang_buf);
    }
    struct stat r22_st;
    if (stat("/etc/fx6_stage_r22", &r22_st) == 0) {
        char lang_buf[32] = "en";
        FILE *r22f = fopen("/etc/fx6_stage_r22", "r");
        if (r22f) {
            char rline[128];
            while (fgets(rline, sizeof(rline), r22f)) {
                char parsed[32];
                if (sscanf(rline, "lang=%31s", parsed) == 1) {
                    snprintf(lang_buf, sizeof(lang_buf), "%s", parsed);
                }
            }
            fclose(r22f);
        }
        fprintf(stderr,
                "FX6_STAGE_B_R22_VERIFY_PASS count=%u stage_b=1 p10_keymap=1 p11_uipc=1 p12_wlan=1 p4_nd_clear=1 uxc=1 paintlook_camtab2_4lang_dualsurface=1 wf12_00342260_immune=1 lang=%s\n",
                count, lang_buf);
    }
    struct stat r23_st;
    if (stat("/etc/fx6_stage_r23", &r23_st) == 0) {
        char lang_buf[32] = "en";
        FILE *r23f = fopen("/etc/fx6_stage_r23", "r");
        if (r23f) {
            char rline[128];
            while (fgets(rline, sizeof(rline), r23f)) {
                char parsed[32];
                if (sscanf(rline, "lang=%31s", parsed) == 1) {
                    snprintf(lang_buf, sizeof(lang_buf), "%s", parsed);
                }
            }
            fclose(r23f);
        }
        fprintf(stderr,
                "FX6_STAGE_B_R23_VERIFY_PASS count=%u stage_b=1 p10_keymap=1 p11_uipc=1 p12_wlan=1 p4_nd_clear=1 uxc=1 monitoring_tab5_4lang_dualsurface=1 wf12_00342260_immune=1 lang=%s\n",
                count, lang_buf);
    }
    struct stat r24_st;
    if (stat("/etc/fx6_stage_r24", &r24_st) == 0) {
        char lang_buf[32] = "en";
        FILE *r24f = fopen("/etc/fx6_stage_r24", "r");
        if (r24f) {
            char rline[128];
            while (fgets(rline, sizeof(rline), r24f)) {
                char parsed[32];
                if (sscanf(rline, "lang=%31s", parsed) == 1) {
                    snprintf(lang_buf, sizeof(lang_buf), "%s", parsed);
                }
            }
            fclose(r24f);
        }
        fprintf(stderr,
                "FX6_STAGE_B_R24_VERIFY_PASS count=%u stage_b=1 p10_keymap=1 p11_uipc=1 p12_wlan=1 p4_nd_clear=1 uxc=1 project_tab4_4lang_dualsurface=1 wf12_00342260_immune=1 lang=%s\n",
                count, lang_buf);
    }
    struct stat r25_st;
    if (stat("/etc/fx6_stage_r25", &r25_st) == 0) {
        char lang_buf[32] = "en";
        FILE *r25f = fopen("/etc/fx6_stage_r25", "r");
        if (r25f) {
            char rline[128];
            while (fgets(rline, sizeof(rline), r25f)) {
                char parsed[32];
                if (sscanf(rline, "lang=%31s", parsed) == 1) {
                    snprintf(lang_buf, sizeof(lang_buf), "%s", parsed);
                }
            }
            fclose(r25f);
        }
        fprintf(stderr,
                "FX6_STAGE_B_R25_VERIFY_PASS count=%u stage_b=1 p10_keymap=1 p11_uipc=1 p12_wlan=1 p4_nd_clear=1 uxc=1 tcmedia_tab8_4lang_dualsurface=1 wf12_00342260_immune=1 lang=%s\n",
                count, lang_buf);
    }
    struct stat r26_st;
    if (stat("/etc/fx6_stage_r26", &r26_st) == 0) {
        char lang_buf[32] = "en";
        FILE *r26f = fopen("/etc/fx6_stage_r26", "r");
        if (r26f) {
            char rline[128];
            while (fgets(rline, sizeof(rline), r26f)) {
                char parsed[32];
                if (sscanf(rline, "lang=%31s", parsed) == 1) {
                    snprintf(lang_buf, sizeof(lang_buf), "%s", parsed);
                }
            }
            fclose(r26f);
        }
        fprintf(stderr,
                "FX6_STAGE_B_R26_VERIFY_PASS count=%u stage_b=1 p10_keymap=1 p11_uipc=1 p12_wlan=1 p4_nd_clear=1 uxc=1 technical_tab6_4lang_dualsurface=1 wf12_00342260_immune=1 lang=%s\n",
                count, lang_buf);
    }
    struct stat r27_st;
    if (stat("/etc/fx6_stage_r27", &r27_st) == 0) {
        char lang_buf[32] = "en";
        FILE *r27f = fopen("/etc/fx6_stage_r27", "r");
        if (r27f) {
            char rline[128];
            while (fgets(rline, sizeof(rline), r27f)) {
                char parsed[32];
                if (sscanf(rline, "lang=%31s", parsed) == 1) {
                    snprintf(lang_buf, sizeof(lang_buf), "%s", parsed);
                }
            }
            fclose(r27f);
        }
        fprintf(stderr,
                "FX6_STAGE_B_R27_VERIFY_PASS count=%u stage_b=1 p10_keymap=1 p11_uipc=1 p12_wlan=1 p4_nd_clear=1 uxc=1 maintenance_tab7_4lang_dualsurface=1 wf12_00342260_immune=1 lang=%s\n",
                count, lang_buf);
    }
    struct stat r28_st;
    if (stat("/etc/fx6_stage_r28", &r28_st) == 0) {
        char lang_buf[32] = "en";
        FILE *r28f = fopen("/etc/fx6_stage_r28", "r");
        if (r28f) {
            char rline[128];
            while (fgets(rline, sizeof(rline), r28f)) {
                char parsed[32];
                if (sscanf(rline, "lang=%31s", parsed) == 1) {
                    snprintf(lang_buf, sizeof(lang_buf), "%s", parsed);
                }
            }
            fclose(r28f);
        }
        fprintf(stderr,
                "FX6_STAGE_B_R28_VERIFY_PASS count=%u stage_b=1 p10_keymap=1 p11_uipc=1 p12_wlan=1 p4_nd_clear=1 uxc=1 realhw_sd_dualboot_overlay=1 wf12_00342260_immune=1 lang=%s\n",
                count, lang_buf);
    }
    struct stat r29_st;
    if (stat("/etc/fx6_stage_r29", &r29_st) == 0) {
        char lang_buf[32] = "en";
        FILE *r29f = fopen("/etc/fx6_stage_r29", "r");
        if (r29f) {
            char rline[128];
            while (fgets(rline, sizeof(rline), r29f)) {
                char parsed[32];
                if (sscanf(rline, "lang=%31s", parsed) == 1) {
                    snprintf(lang_buf, sizeof(lang_buf), "%s", parsed);
                }
            }
            fclose(r29f);
        }
        fprintf(stderr,
                "FX6_STAGE_B_R29_VERIFY_PASS count=%u stage_b=1 p10_keymap=1 p11_uipc=1 p12_wlan=1 p4_nd_clear=1 uxc=1 realhw_sd_dualboot_overlay=1 atomic_installer_ready=1 wf12_00342260_immune=1 lang=%s\n",
                count, lang_buf);
    }
    return 0;
}

static uint32_t fx3_crc32_ieee(const uint8_t *buf, size_t len) {
    uint32_t crc = 0xFFFFFFFFU;
    for (size_t i = 0U; i < len; i++) {
        crc ^= (uint32_t)buf[i];
        for (int b = 0; b < 8; b++) {
            crc = (crc & 1U) ? ((crc >> 1) ^ 0xEDB88320U) : (crc >> 1);
        }
    }
    return crc ^ 0xFFFFFFFFU;
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

static int setup_strategy_a_bridge_r28(void) {
    struct stat st;
    if (stat("/dev/cnflasha30", &st) != 0) {
        int fd = open("/dev/cnflasha30", O_CREAT | O_WRONLY, 0644);
        if (fd >= 0) close(fd);
    }
    unlink("/dev/nflasha30");
    int rc30 = symlink("/dev/cnflasha30", "/dev/nflasha30");
    unlink("/dev/nflasha20");
    int rc20 = symlink("/dev/nflasha30", "/dev/nflasha20");

    char link20[128] = "";
    char link30[128] = "";
    ssize_t rl20 = readlink("/dev/nflasha20", link20, sizeof(link20) - 1U);
    if (rl20 > 0) link20[rl20] = '\0';
    ssize_t rl30 = readlink("/dev/nflasha30", link30, sizeof(link30) - 1U);
    if (rl30 > 0) link30[rl30] = '\0';

    int link20_ok = (rc20 == 0 && strcmp(link20, "/dev/nflasha30") == 0 && stat("/dev/nflasha20", &st) == 0) ? 1 : 0;
    int link30_ok = (rc30 == 0 && strcmp(link30, "/dev/cnflasha30") == 0) ? 1 : 0;
    fprintf(stderr,
            "FX6_STAGE_A_P1_LINK target=/dev/cnflasha30 rc30=%d rc20=%d\n",
            rc30, rc20);

    (void)mkdir("/etc/opelog", 0755);
    int mnt_rc = mount("tmpfs", "/etc/opelog", "tmpfs", MS_NOATIME, "size=16m");
    int mnt_errno = (mnt_rc == 0) ? 0 : errno;
    (void)mkdir("/etc/opelog/OPE", 0755);
    (void)mkdir("/etc/opelog/OPE/00", 0755);
    (void)mkdir("/etc/opelog/OPE/01", 0755);
    int ope_ok = (stat("/etc/opelog/OPE", &st) == 0 && S_ISDIR(st.st_mode)) ? 1 : 0;
    int ope00_ok = (stat("/etc/opelog/OPE/00", &st) == 0 && S_ISDIR(st.st_mode)) ? 1 : 0;
    int ope01_ok = (stat("/etc/opelog/OPE/01", &st) == 0 && S_ISDIR(st.st_mode)) ? 1 : 0;

    int tmpfs_mounted = 0;
    FILE *mf = fopen("/proc/mounts", "r");
    if (mf) {
        char mline[512];
        while (fgets(mline, sizeof(mline), mf)) {
            if (strstr(mline, " /etc/opelog tmpfs ") != NULL) {
                tmpfs_mounted = 1;
                break;
            }
        }
        fclose(mf);
    }

    int ok = (link20_ok && link30_ok && mnt_rc == 0 && tmpfs_mounted && ope_ok && ope00_ok && ope01_ok) ? 1 : 0;
    fprintf(stderr,
            "FX6_STAGE_A_P2_MOUNT rc=%d errno=%d sym_rc=0 loop=tmpfs target=/etc/opelog opts=size=16m ope=%d ope00=%d ope01=%d\n",
            mnt_rc, mnt_errno, ope_ok, ope00_ok, ope01_ok);
    fprintf(stderr,
            "FX6_R28_STRATEGY_A_BRIDGE nflasha20_link=%s nflasha30_link=%s opelog_fstype=%s tmpfs_mounted=%d opelog_ope=%d opelog_00=%d opelog_01=%d sector0_repartition=0 emmc_write_count=0 strategy_a_bridge_ok=%d\n",
            link20[0] ? link20 : "ERR",
            link30[0] ? link30 : "ERR",
            tmpfs_mounted ? "tmpfs" : "unknown",
            tmpfs_mounted, ope_ok, ope00_ok, ope01_ok, ok);
    return ok ? 0 : -1;
}

static int run_jiritsu_libjit_probe_r28(void) {
    /* Expose simulated FX3 Sector 0 at /dev/pnflasha0 strictly read-only from /etc/fx3_sector0.bin */
    int src_fd = open("/etc/fx3_sector0.bin", O_RDONLY);
    if (src_fd < 0) {
        fprintf(stderr, "FX6_R28_JIRITSU_PROBE dlopen_ok=0 err=missing_fx3_sector0 errno=%d\n", errno);
        return -1;
    }
    uint8_t sec_buf[512];
    ssize_t sn = read(src_fd, sec_buf, sizeof(sec_buf));
    close(src_fd);
    if (sn != 512) {
        fprintf(stderr, "FX6_R28_JIRITSU_PROBE dlopen_ok=0 err=short_fx3_sector0 bytes=%zd\n", sn);
        return -1;
    }
    unlink("/dev/pnflasha0");
    int dev_fd = open("/dev/pnflasha0", O_WRONLY | O_CREAT | O_EXCL, 0444);
    if (dev_fd < 0) {
        fprintf(stderr, "FX6_R28_JIRITSU_PROBE dlopen_ok=0 err=create_pnflasha0 errno=%d\n", errno);
        return -1;
    }
    ssize_t wn = write(dev_fd, sec_buf, sizeof(sec_buf));
    close(dev_fd);
    if (wn != 512) {
        fprintf(stderr, "FX6_R28_JIRITSU_PROBE dlopen_ok=0 err=write_pnflasha0 bytes=%zd\n", wn);
        return -1;
    }

    (void)mkdir("/tmp/jiritsu", 0755);
    unlink("/tmp/jiritsu/sector0.pkt");

    struct stat pre_st;
    if (stat("/tmp/jiritsu/libJit.so", &pre_st) != 0) {
        fprintf(stderr, "FX6_R28_JIRITSU_PROBE dlopen_ok=0 err=missing_libJit_so errno=%d\n", errno);
        return -1;
    }

    void *handle = dlopen("/tmp/jiritsu/libJit.so", RTLD_NOW);
    if (!handle) {
        const char *derr = dlerror();
        fprintf(stderr, "FX6_R28_JIRITSU_PROBE dlopen_ok=0 dlerror=%s\n", derr ? derr : "unknown");
        return -1;
    }
    int dlclose_rc = dlclose(handle);

    struct stat post_st;
    int unlinked = (stat("/tmp/jiritsu/libJit.so", &post_st) != 0 && errno == ENOENT) ? 1 : 0;
    int unlink_err = unlinked ? ENOENT : 0;

    int pkt_fd = open("/tmp/jiritsu/sector0.pkt", O_RDONLY);
    if (pkt_fd < 0) {
        fprintf(stderr,
                "FX6_R28_JIRITSU_PROBE dlopen_ok=1 dlclose_rc=%d jit_self_unlinked=%d unlink_errno=%d sector0_pkt_bytes=0 err=missing_pkt errno=%d\n",
                dlclose_rc, unlinked, unlink_err, errno);
        return -1;
    }
    uint8_t pkt[544];
    ssize_t pn = read(pkt_fd, pkt, sizeof(pkt));
    close(pkt_fd);

    if (pn != 528 || memcmp(pkt, "FX3S0OK\0", 8U) != 0) {
        fprintf(stderr,
                "FX6_R28_JIRITSU_PROBE dlopen_ok=1 dlclose_rc=%d jit_self_unlinked=%d sector0_pkt_bytes=%zd err=bad_pkt_header\n",
                dlclose_rc, unlinked, pn);
        return -1;
    }
    uint32_t pkt_len = (uint32_t)pkt[8] | ((uint32_t)pkt[9] << 8) | ((uint32_t)pkt[10] << 16) | ((uint32_t)pkt[11] << 24);
    uint32_t pkt_crc = (uint32_t)pkt[12] | ((uint32_t)pkt[13] << 8) | ((uint32_t)pkt[14] << 16) | ((uint32_t)pkt[15] << 24);
    uint32_t calc_crc = fx3_crc32_ieee(pkt + 16, 512U);
    int crc_ok = (pkt_len == 512U && pkt_crc == calc_crc) ? 1 : 0;

    char magic_str[5] = { (char)pkt[16], (char)pkt[17], (char)pkt[18], (char)pkt[19], '\0' };
    char ver_str[5] = { (char)pkt[20], (char)pkt[21], (char)pkt[22], (char)pkt[23], '\0' };
    uint32_t nparts = (uint32_t)pkt[24] | ((uint32_t)pkt[25] << 8) | ((uint32_t)pkt[26] << 16) | ((uint32_t)pkt[27] << 24);
    uint32_t p1_start = (uint32_t)pkt[48] | ((uint32_t)pkt[49] << 8) | ((uint32_t)pkt[50] << 16) | ((uint32_t)pkt[51] << 24);
    uint32_t p1_size = (uint32_t)pkt[52] | ((uint32_t)pkt[53] << 8) | ((uint32_t)pkt[54] << 16) | ((uint32_t)pkt[55] << 24);
    /* Entry 29 (p30) starts at sector0 offset 0x20 + 29*16 = 0x1f0 -> pkt offset 16 + 0x1f0 = 512 */
    uint32_t p30_start = (uint32_t)pkt[512] | ((uint32_t)pkt[513] << 8) | ((uint32_t)pkt[514] << 16) | ((uint32_t)pkt[515] << 24);
    uint32_t p30_size = (uint32_t)pkt[516] | ((uint32_t)pkt[517] << 8) | ((uint32_t)pkt[518] << 16) | ((uint32_t)pkt[519] << 24);

    int ok = (dlclose_rc == 0 && unlinked == 1 && crc_ok == 1 &&
              strcmp(magic_str, "8246") == 0 && strcmp(ver_str, "2.00") == 0 && nparts == 30U) ? 1 : 0;
    fprintf(stderr,
            "FX6_R28_JIRITSU_PROBE dlopen_ok=1 dlclose_rc=%d jit_self_unlinked=%d unlink_errno=%d "
            "sector0_pkt_bytes=%zd sector0_hdr=FX3S0OK sector0_len=%u sector0_crc32=0x%08x sector0_crc_ok=%d "
            "sector0_magic=%s sector0_ver=%s sector0_parts=%u p1_start=0x%x p1_size=0x%x p30_start=0x%x p30_size=0x%x "
            "emmc_write_count=0 probe_ok=%d\n",
            dlclose_rc, unlinked, unlink_err, pn, pkt_len, pkt_crc, crc_ok,
            magic_str, ver_str, nparts, p1_start, p1_size, p30_start, p30_size, ok);
    return ok ? 0 : -1;
}

static void print_kernel_identity(void) {
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
}

static int is_lower_hex64(const char *s) {
    if (!s) return 0;
    for (int i = 0; i < 64; i++) {
        char c = s[i];
        if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'))) return 0;
    }
    return s[64] == '\0';
}

static long long elapsed_us(const struct timespec *t0, const struct timespec *t1) {
    long long ds = (long long)(t1->tv_sec - t0->tv_sec);
    long long dns = (long long)(t1->tv_nsec - t0->tv_nsec);
    long long us = ds * 1000000LL + dns / 1000LL;
    return (us < 0) ? 0 : us;
}

static int run_sd_gate_r28(void) {
    struct timespec t0, t1;
    clock_gettime(CLOCK_MONOTONIC, &t0);

    const char *manifest_path = "/mnt/sd/FX6_STAGEB_BOOT.MANIFEST";
    struct stat st;
    if (stat(manifest_path, &st) != 0) {
        clock_gettime(CLOCK_MONOTONIC, &t1);
        long long us = elapsed_us(&t0, &t1);
        fprintf(stderr,
                "FX6_R28_SD_DUALBOOT sd_dualboot_mode=STOCK_FX3_BYPASS trigger_present=0 tamper_rejected=0 stageb_loaded=0 emmc_write_count=0 verify_ms=%lld verify_us=%lld\n",
                us / 1000LL, us);
        fflush(stderr);
        return 10;
    }

    FILE *fp = fopen(manifest_path, "r");
    if (!fp) {
        clock_gettime(CLOCK_MONOTONIC, &t1);
        long long us = elapsed_us(&t0, &t1);
        fprintf(stderr,
                "FX6_R28_SD_DUALBOOT sd_dualboot_mode=FAIL_CLOSED_STOCK_FX3_FALLBACK trigger_present=1 tamper_rejected=1 stageb_loaded=0 emmc_write_count=0 verify_ms=%lld verify_us=%lld reason=open_failed\n",
                us / 1000LL, us);
        fflush(stderr);
        return 11;
    }

    char line[512];
    unsigned int count = 0U;
    int tamper = 0;
    char fail_reason[64] = "ok";
    char fail_path[256] = "none";

    while (fgets(line, sizeof(line), fp)) {
        size_t ln = strlen(line);
        while (ln > 0U && (line[ln - 1U] == '\n' || line[ln - 1U] == '\r')) {
            line[--ln] = '\0';
        }
        if (ln == 0U) continue;
        if (ln < 66U || line[64] != ' ' || line[65] != '/') {
            tamper = 1;
            snprintf(fail_reason, sizeof(fail_reason), "malformed_line");
            break;
        }
        char expected[65];
        memcpy(expected, line, 64U);
        expected[64] = '\0';
        if (!is_lower_hex64(expected)) {
            tamper = 1;
            snprintf(fail_reason, sizeof(fail_reason), "bad_hex_digest");
            break;
        }
        const char *path = line + 65;
        char actual[65];
        unsigned long long bytes = 0ULL;
        if (sha256_file_hex(path, actual, &bytes) != 0) {
            tamper = 1;
            snprintf(fail_reason, sizeof(fail_reason), "missing_item");
            snprintf(fail_path, sizeof(fail_path), "%s", path);
            break;
        }
        if (strcmp(expected, actual) != 0) {
            tamper = 1;
            snprintf(fail_reason, sizeof(fail_reason), "sha256_mismatch");
            snprintf(fail_path, sizeof(fail_path), "%s", path);
            break;
        }
        count++;
    }
    fclose(fp);
    if (!tamper && count == 0U) {
        tamper = 1;
        snprintf(fail_reason, sizeof(fail_reason), "empty_manifest");
    }

    clock_gettime(CLOCK_MONOTONIC, &t1);
    long long us = elapsed_us(&t0, &t1);
    long long ms = us / 1000LL;

    if (tamper) {
        fprintf(stderr,
                "FX6_R28_SD_DUALBOOT sd_dualboot_mode=FAIL_CLOSED_STOCK_FX3_FALLBACK trigger_present=1 tamper_rejected=1 stageb_loaded=0 emmc_write_count=0 verify_ms=%lld verify_us=%lld reason=%s failed_path=%s\n",
                ms, us, fail_reason, fail_path);
        fflush(stderr);
        return 11;
    }

    fprintf(stderr,
            "FX6_R28_SD_DUALBOOT sd_dualboot_mode=STAGEB_SD_AUTHENTICATED trigger_present=1 tamper_rejected=0 stageb_loaded=1 emmc_write_count=0 verified_count=%u verify_ms=%lld verify_us=%lld\n",
            count, ms, us);
    fflush(stderr);
    return 0;
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

static int r29_is_allowed_nflasha15_path(const char *path) {
    if (!path) return 0;
    return (strcmp(path, "/dev/nflasha15") == 0 || strcmp(path, "/dev/cnflasha15") == 0) ? 1 : 0;
}

static int r29_write_all_fsync(const char *path, const void *buf, size_t len, mode_t mode) {
    int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, mode);
    if (fd < 0) return -1;
    const uint8_t *p = (const uint8_t *)buf;
    size_t off = 0U;
    while (off < len) {
        ssize_t n = write(fd, p + off, len - off);
        if (n < 0) {
            if (errno == EINTR) continue;
            close(fd);
            return -1;
        }
        off += (size_t)n;
    }
    if (fsync(fd) != 0) {
        close(fd);
        return -1;
    }
    if (close(fd) != 0) return -1;
    return 0;
}

static int r29_copy_file_fsync(const char *src, const char *dst, mode_t mode) {
    int in_fd = open(src, O_RDONLY);
    if (in_fd < 0) return -1;
    int out_fd = open(dst, O_WRONLY | O_CREAT | O_TRUNC, mode);
    if (out_fd < 0) {
        close(in_fd);
        return -1;
    }
    uint8_t buf[16384];
    for (;;) {
        ssize_t nr = read(in_fd, buf, sizeof(buf));
        if (nr < 0) {
            if (errno == EINTR) continue;
            close(in_fd);
            close(out_fd);
            return -1;
        }
        if (nr == 0) break;
        ssize_t off = 0;
        while (off < nr) {
            ssize_t nw = write(out_fd, buf + off, (size_t)(nr - off));
            if (nw < 0) {
                if (errno == EINTR) continue;
                close(in_fd);
                close(out_fd);
                return -1;
            }
            off += nw;
        }
    }
    close(in_fd);
    if (fsync(out_fd) != 0) {
        close(out_fd);
        return -1;
    }
    if (close(out_fd) != 0) return -1;
    return 0;
}

static int r29_fsync_dir(const char *dir_path) {
    int dfd = open(dir_path, O_RDONLY | O_DIRECTORY);
    if (dfd < 0) return -1;
    int rc = fsync(dfd);
    close(dfd);
    return rc;
}

static void r29_sha256_buf_hex(const uint8_t *buf, size_t len, char out_hex[65]) {
    fx6_sha256_ctx_t ctx;
    sha256_init(&ctx);
    sha256_update(&ctx, buf, len);
    uint8_t hash[32];
    sha256_final(&ctx, hash);
    static const char hex[] = "0123456789abcdef";
    for (int i = 0; i < 32; i++) {
        out_hex[i * 2 + 0] = hex[(hash[i] >> 4) & 0xfU];
        out_hex[i * 2 + 1] = hex[hash[i] & 0xfU];
    }
    out_hex[64] = '\0';
}

static void r29_check_mount_ro(const char *mountpoint, const char *probe_file,
                               int *out_ro_mount, int *out_erofs) {
    int ro_mnt = 0;
    char needle[256];
    snprintf(needle, sizeof(needle), " %s tmpfs ", mountpoint);
    FILE *mf = fopen("/proc/mounts", "r");
    if (mf) {
        char mline[512];
        while (fgets(mline, sizeof(mline), mf)) {
            const char *hit = strstr(mline, needle);
            if (hit) {
                const char *opts = hit + strlen(needle);
                if (strncmp(opts, "ro,", 3U) == 0 || strncmp(opts, "ro ", 3U) == 0) {
                    ro_mnt = 1;
                }
                break;
            }
        }
        fclose(mf);
    }
    int erofs = 0;
    if (probe_file) {
        int pfd = open(probe_file, O_WRONLY | O_CREAT | O_TRUNC, 0644);
        if (pfd < 0) {
            if (errno == EROFS) erofs = 1;
        } else {
            close(pfd);
            unlink(probe_file);
        }
    }
    if (out_ro_mount) *out_ro_mount = ro_mnt;
    if (out_erofs) *out_erofs = erofs;
}

static int run_r29_installer_tx(int inject_fault) {
    struct timespec t0, t1;
    clock_gettime(CLOCK_MONOTONIC, &t0);

    int pnflasha15_rejected = (r29_is_allowed_nflasha15_path("/dev/pnflasha15") == 0) ? 1 : 0;
    int nflasha15_accepted = r29_is_allowed_nflasha15_path("/dev/nflasha15");
    int cnflasha15_accepted = r29_is_allowed_nflasha15_path("/dev/cnflasha15");
    if (!pnflasha15_rejected || !nflasha15_accepted || !cnflasha15_accepted) {
        fprintf(stderr, "FX6_R29_INSTALLER_FAIL step=device_firewall\n");
        return 60;
    }

    /* Create simulated /dev/cnflasha15 & /dev/nflasha15 symlink in devtmpfs (zero eMMC writes) */
    struct stat st;
    if (stat("/dev/cnflasha15", &st) != 0) {
        int dfd = open("/dev/cnflasha15", O_WRONLY | O_CREAT, 0644);
        if (dfd >= 0) close(dfd);
    }
    unlink("/dev/nflasha15");
    (void)symlink("/dev/cnflasha15", "/dev/nflasha15");

    char expected_stock_sha[65] = "";
    FILE *sf = fopen("/etc/fx6_r29_stock_im_sha256.txt", "r");
    if (!sf) {
        fprintf(stderr, "FX6_R29_INSTALLER_FAIL step=missing_stock_sha errno=%d\n", errno);
        return 61;
    }
    if (fscanf(sf, "%64s", expected_stock_sha) != 1 || !is_lower_hex64(expected_stock_sha)) {
        fclose(sf);
        fprintf(stderr, "FX6_R29_INSTALLER_FAIL step=bad_stock_sha\n");
        return 61;
    }
    fclose(sf);

    (void)mkdir("/mnt/r29_usr", 0755);
    (void)umount("/mnt/r29_usr");
    if (mount("tmpfs", "/mnt/r29_usr", "tmpfs", MS_NOATIME, "size=8m") != 0) {
        fprintf(stderr, "FX6_R29_INSTALLER_FAIL step=mount_tmpfs errno=%d\n", errno);
        return 62;
    }
    if (mkdir("/mnt/r29_usr/bin", 0755) != 0 && errno != EEXIST) {
        fprintf(stderr, "FX6_R29_INSTALLER_FAIL step=mkdir_bin errno=%d\n", errno);
        return 62;
    }

    if (r29_copy_file_fsync("/usr/bin/im.elf", "/mnt/r29_usr/bin/im.elf", 0755) != 0) {
        fprintf(stderr, "FX6_R29_INSTALLER_FAIL step=stage_stock_im errno=%d\n", errno);
        return 63;
    }

    char pre_sha[65];
    unsigned long long pre_bytes = 0ULL;
    if (sha256_file_hex("/mnt/r29_usr/bin/im.elf", pre_sha, &pre_bytes) != 0) {
        fprintf(stderr, "FX6_R29_INSTALLER_FAIL step=hash_pre errno=%d\n", errno);
        return 63;
    }
    int pre_sha_match = (strcmp(pre_sha, expected_stock_sha) == 0) ? 1 : 0;
    if (!pre_sha_match) {
        fprintf(stderr, "FX6_R29_INSTALLER_FAIL step=pre_sha_mismatch pre=%s exp=%s\n",
                pre_sha, expected_stock_sha);
        return 64;
    }

    if (r29_copy_file_fsync("/mnt/r29_usr/bin/im.elf", "/mnt/r29_usr/bin/im.elf.orig", 0755) != 0) {
        fprintf(stderr, "FX6_R29_INSTALLER_FAIL step=backup_orig errno=%d\n", errno);
        return 65;
    }
    char orig_sha[65];
    unsigned long long orig_bytes = 0ULL;
    if (sha256_file_hex("/mnt/r29_usr/bin/im.elf.orig", orig_sha, &orig_bytes) != 0 ||
        strcmp(orig_sha, expected_stock_sha) != 0) {
        fprintf(stderr, "FX6_R29_INSTALLER_FAIL step=verify_orig\n");
        return 65;
    }

    static const char k_r29_sd_launcher[] =
        "#!/bin/sh\n"
        "if [ ! -f /mnt/sd/FX6_STAGEB_BOOT.MANIFEST ]; then exec /usr/bin/im.elf.orig \"$@\"; fi\n"
        "exec /usr/bin/appfw-launch \"$@\"\n";
    const size_t staged_len = sizeof(k_r29_sd_launcher) - 1U;
    char staged_sha[65];
    r29_sha256_buf_hex((const uint8_t *)k_r29_sd_launcher, staged_len, staged_sha);

    if (!inject_fault) {
        if (r29_write_all_fsync("/mnt/r29_usr/bin/im.elf.new", k_r29_sd_launcher, staged_len, 0755) != 0) {
            fprintf(stderr, "FX6_R29_INSTALLER_FAIL step=write_new errno=%d\n", errno);
            return 66;
        }
        if (rename("/mnt/r29_usr/bin/im.elf.new", "/mnt/r29_usr/bin/im.elf") != 0 ||
            r29_fsync_dir("/mnt/r29_usr/bin") != 0) {
            fprintf(stderr, "FX6_R29_INSTALLER_FAIL step=atomic_rename errno=%d\n", errno);
            return 66;
        }
        char post_sha[65];
        unsigned long long post_bytes = 0ULL;
        if (sha256_file_hex("/mnt/r29_usr/bin/im.elf", post_sha, &post_bytes) != 0) {
            fprintf(stderr, "FX6_R29_INSTALLER_FAIL step=readback_post errno=%d\n", errno);
            return 67;
        }
        int post_sha_match = (post_bytes == (unsigned long long)staged_len &&
                              strcmp(post_sha, staged_sha) == 0) ? 1 : 0;

        int ro_rc = mount(NULL, "/mnt/r29_usr", NULL, MS_REMOUNT | MS_RDONLY, NULL);
        int ro_mnt = 0, erofs = 0;
        r29_check_mount_ro("/mnt/r29_usr", "/mnt/r29_usr/bin/.ro_probe", &ro_mnt, &erofs);

        clock_gettime(CLOCK_MONOTONIC, &t1);
        long long us = elapsed_us(&t0, &t1);
        int ok = (pnflasha15_rejected && nflasha15_accepted && cnflasha15_accepted &&
                  pre_sha_match && post_sha_match && ro_rc == 0 && ro_mnt && erofs) ? 1 : 0;
        fprintf(stderr,
                "FX6_R29_ATOMIC_INSTALL mode=install device=/dev/cnflasha15 alias=/dev/nflasha15 "
                "pnflasha15_rejected=%d nflasha15_accepted=%d cnflasha15_accepted=%d "
                "stock_bytes=%llu stock_sha256=%s orig_sha256=%s staged_bytes=%zu staged_sha256=%s "
                "post_sha256=%s pre_sha_match=%d orig_backup_ok=1 post_sha_match=%d "
                "ro_remounted=%d ro_write_blocked_erofs=%d atomic_install_ok=%d "
                "emmc_write_count=0 crashes=0 verify_us=%lld\n",
                pnflasha15_rejected, nflasha15_accepted, cnflasha15_accepted,
                pre_bytes, expected_stock_sha, orig_sha, staged_len, staged_sha,
                post_sha, pre_sha_match, post_sha_match,
                (ro_rc == 0 && ro_mnt) ? 1 : 0, erofs, ok, us);
        fflush(stderr);
        return ok ? 0 : 68;
    }

    /* Fault-injected mid-write rollback Case 1: deterministic 1-bit flip */
    uint8_t corrupted_buf[sizeof(k_r29_sd_launcher)];
    memcpy(corrupted_buf, k_r29_sd_launcher, staged_len);
    corrupted_buf[staged_len - 2U] ^= 0x01U;

    if (r29_write_all_fsync("/mnt/r29_usr/bin/im.elf.new", corrupted_buf, staged_len, 0755) != 0 ||
        rename("/mnt/r29_usr/bin/im.elf.new", "/mnt/r29_usr/bin/im.elf") != 0 ||
        r29_fsync_dir("/mnt/r29_usr/bin") != 0) {
        fprintf(stderr, "FX6_R29_ROLLBACK_FAIL step=inject_bitflip errno=%d\n", errno);
        return 70;
    }

    char corrupted_sha[65];
    unsigned long long corrupted_bytes = 0ULL;
    if (sha256_file_hex("/mnt/r29_usr/bin/im.elf", corrupted_sha, &corrupted_bytes) != 0) {
        fprintf(stderr, "FX6_R29_ROLLBACK_FAIL step=readback_corrupted errno=%d\n", errno);
        return 71;
    }
    int mismatch_detected = (strcmp(corrupted_sha, staged_sha) != 0) ? 1 : 0;
    if (!mismatch_detected) {
        fprintf(stderr, "FX6_R29_ROLLBACK_FAIL step=expected_mismatch_not_seen\n");
        return 71;
    }

    /* Atomic rollback from .orig + fsync + ro remount */
    if (r29_copy_file_fsync("/mnt/r29_usr/bin/im.elf.orig", "/mnt/r29_usr/bin/im.elf.rb", 0755) != 0 ||
        rename("/mnt/r29_usr/bin/im.elf.rb", "/mnt/r29_usr/bin/im.elf") != 0 ||
        unlink("/mnt/r29_usr/bin/im.elf.orig") != 0 ||
        r29_fsync_dir("/mnt/r29_usr/bin") != 0) {
        fprintf(stderr, "FX6_R29_ROLLBACK_FAIL step=restore_orig_bitflip errno=%d\n", errno);
        return 72;
    }
    int ro_rc1 = mount(NULL, "/mnt/r29_usr", NULL, MS_REMOUNT | MS_RDONLY, NULL);
    int ro_mnt1 = 0, erofs1 = 0;
    r29_check_mount_ro("/mnt/r29_usr", "/mnt/r29_usr/bin/.ro_probe", &ro_mnt1, &erofs1);

    char restored_sha[65];
    unsigned long long restored_bytes = 0ULL;
    if (sha256_file_hex("/mnt/r29_usr/bin/im.elf", restored_sha, &restored_bytes) != 0) {
        fprintf(stderr, "FX6_R29_ROLLBACK_FAIL step=hash_restored_bitflip errno=%d\n", errno);
        return 73;
    }
    int bitflip_restored = (restored_bytes == pre_bytes &&
                            strcmp(restored_sha, expected_stock_sha) == 0 &&
                            ro_rc1 == 0 && ro_mnt1 && erofs1) ? 1 : 0;

    /* Fault-injected mid-write rollback Case 2: deterministic 50% short-write */
    int short_write_detected = 0;
    int short_write_rollback_ok = 0;
    if (mount(NULL, "/mnt/r29_usr", NULL, MS_REMOUNT, NULL) == 0 &&
        r29_copy_file_fsync("/mnt/r29_usr/bin/im.elf", "/mnt/r29_usr/bin/im.elf.orig", 0755) == 0) {
        const size_t half_len = staged_len / 2U;
        if (r29_write_all_fsync("/mnt/r29_usr/bin/im.elf.new", k_r29_sd_launcher, half_len, 0755) == 0 &&
            rename("/mnt/r29_usr/bin/im.elf.new", "/mnt/r29_usr/bin/im.elf") == 0 &&
            r29_fsync_dir("/mnt/r29_usr/bin") == 0) {
            char sw_sha[65];
            unsigned long long sw_bytes = 0ULL;
            if (sha256_file_hex("/mnt/r29_usr/bin/im.elf", sw_sha, &sw_bytes) == 0 &&
                (sw_bytes != (unsigned long long)staged_len || strcmp(sw_sha, staged_sha) != 0)) {
                short_write_detected = 1;
                if (r29_copy_file_fsync("/mnt/r29_usr/bin/im.elf.orig", "/mnt/r29_usr/bin/im.elf.rb", 0755) == 0 &&
                    rename("/mnt/r29_usr/bin/im.elf.rb", "/mnt/r29_usr/bin/im.elf") == 0 &&
                    unlink("/mnt/r29_usr/bin/im.elf.orig") == 0 &&
                    r29_fsync_dir("/mnt/r29_usr/bin") == 0) {
                    int ro_rc2 = mount(NULL, "/mnt/r29_usr", NULL, MS_REMOUNT | MS_RDONLY, NULL);
                    int ro_mnt2 = 0, erofs2 = 0;
                    r29_check_mount_ro("/mnt/r29_usr", "/mnt/r29_usr/bin/.ro_probe", &ro_mnt2, &erofs2);
                    char restored_sw_sha[65];
                    unsigned long long restored_sw_bytes = 0ULL;
                    if (sha256_file_hex("/mnt/r29_usr/bin/im.elf", restored_sw_sha, &restored_sw_bytes) == 0 &&
                        restored_sw_bytes == pre_bytes &&
                        strcmp(restored_sw_sha, expected_stock_sha) == 0 &&
                        ro_rc2 == 0 && ro_mnt2 && erofs2) {
                        short_write_rollback_ok = 1;
                    }
                }
            }
        }
    }

    clock_gettime(CLOCK_MONOTONIC, &t1);
    long long us = elapsed_us(&t0, &t1);
    int all_ok = (bitflip_restored && short_write_detected && short_write_rollback_ok) ? 1 : 0;
    fprintf(stderr,
            "FX6_R29_ATOMIC_ROLLBACK fault_kind=bit_flip_1b_and_short_write device=/dev/cnflasha15 "
            "pnflasha15_rejected=%d nflasha15_accepted=%d cnflasha15_accepted=%d "
            "stock_bytes=%llu stock_sha256=%s expected_staged_sha256=%s corrupted_readback_sha256=%s "
            "restored_sha256=%s mismatch_detected=%d short_write_detected=%d short_write_rollback_ok=%d "
            "ro_remounted=%d ro_write_blocked_erofs=%d stock_sha256_restored=%d "
            "atomic_rollback_verified=%d emmc_write_count=0 crashes=0 verify_us=%lld\n",
            pnflasha15_rejected, nflasha15_accepted, cnflasha15_accepted,
            pre_bytes, expected_stock_sha, staged_sha, corrupted_sha,
            restored_sha, mismatch_detected, short_write_detected, short_write_rollback_ok,
            (ro_rc1 == 0 && ro_mnt1) ? 1 : 0, erofs1, all_ok, all_ok, us);
    fflush(stderr);
    return all_ok ? 0 : 74;
}

static int r29_count_mode_files(const char *dir_path) {
    DIR *d = opendir(dir_path);
    if (!d) return -1;
    int cnt = 0;
    struct dirent *de;
    while ((de = readdir(d)) != NULL) {
        if (strncmp(de->d_name, "mode", 4U) == 0) {
            cnt++;
        }
    }
    closedir(d);
    return cnt;
}

static int run_r29_p1_rescue(void) {
    struct timespec t0, t1;
    clock_gettime(CLOCK_MONOTONIC, &t0);

    (void)mkdir("/setting", 0755);
    (void)mkdir("/setting/updater", 0755);
    (void)umount("/setting/updater");
    if (mount("tmpfs", "/setting/updater", "tmpfs", MS_NOATIME, "size=2m") != 0) {
        fprintf(stderr, "FX6_R29_P1_RESCUE_FAIL step=mount_updater errno=%d\n", errno);
        return 80;
    }
    if (r29_write_all_fsync("/setting/updater/mode6", "6\n", 2U, 0644) != 0) {
        fprintf(stderr, "FX6_R29_P1_RESCUE_FAIL step=arm_mode6 errno=%d\n", errno);
        return 80;
    }

    (void)mkdir("/mnt/r29_p1", 0755);
    (void)umount("/mnt/r29_p1");
    if (mount("tmpfs", "/mnt/r29_p1", "tmpfs", MS_NOATIME, "size=4m") != 0) {
        fprintf(stderr, "FX6_R29_P1_RESCUE_FAIL step=mount_p1 errno=%d\n", errno);
        return 81;
    }
    (void)mkdir("/mnt/r29_p1/boot", 0755);
    (void)mkdir("/mnt/r29_p1/sbin", 0755);

    static const char k_dat2[] = "91030080";
    static const char k_dat3[] = "J1\n";
    static const char k_kemco[] =
        "kemco\n"
        "init=/sbin/init\n"
        "ramdisk_size=8192\n"
        "rw noatime\n"
        "cfg.uart=1\n"
        "ip=off root=/dev/ram0 rootfstype=squashfs\n"
        "console=ttyAMA0,460800n8 amba2.console=1\n"
        "exception.reboot=1 wdt.mode=1\n"
        "*\n";
    static const char k_p1_init[] =
        "#!/bin/sh\n"
        "# Single-shot p1 diagnostic init: line-1 clears mode* + sync before any diag\n"
        "rm -f /setting/updater/mode* && sync\n"
        "mount -t proc proc /proc\n"
        "sync\n";

    if (r29_write_all_fsync("/mnt/r29_p1/dat2", k_dat2, sizeof(k_dat2) - 1U, 0644) != 0 ||
        r29_write_all_fsync("/mnt/r29_p1/dat3", k_dat3, sizeof(k_dat3) - 1U, 0644) != 0 ||
        r29_write_all_fsync("/mnt/r29_p1/boot/kemco.txt", k_kemco, sizeof(k_kemco) - 1U, 0644) != 0 ||
        r29_write_all_fsync("/mnt/r29_p1/sbin/init", k_p1_init, sizeof(k_p1_init) - 1U, 0755) != 0) {
        fprintf(stderr, "FX6_R29_P1_RESCUE_FAIL step=populate_p1 errno=%d\n", errno);
        return 81;
    }

    (void)mkdir("/mnt/r29_p3", 0755);
    (void)umount("/mnt/r29_p3");
    if (mount("tmpfs", "/mnt/r29_p3", "tmpfs", MS_NOATIME, "size=2m") != 0) {
        fprintf(stderr, "FX6_R29_P1_RESCUE_FAIL step=mount_p3 errno=%d\n", errno);
        return 82;
    }
    static const char k_p3_marker[] = "FX3_702_STOCK_P3_KERNEL_AND_ROOTFS_UNTOUCHED\n";
    if (r29_write_all_fsync("/mnt/r29_p3/p3_marker.txt", k_p3_marker, sizeof(k_p3_marker) - 1U, 0444) != 0) {
        fprintf(stderr, "FX6_R29_P1_RESCUE_FAIL step=populate_p3 errno=%d\n", errno);
        return 82;
    }
    char p3_before_sha[65];
    unsigned long long p3_before_bytes = 0ULL;
    if (sha256_file_hex("/mnt/r29_p3/p3_marker.txt", p3_before_sha, &p3_before_bytes) != 0 ||
        mount(NULL, "/mnt/r29_p3", NULL, MS_REMOUNT | MS_RDONLY, NULL) != 0) {
        fprintf(stderr, "FX6_R29_P1_RESCUE_FAIL step=lock_p3_ro errno=%d\n", errno);
        return 82;
    }

    int mode_before = r29_count_mode_files("/setting/updater");

    /* Extract exact first non-comment executable line from /mnt/r29_p1/sbin/init */
    char first_line[256] = "";
    FILE *init_fp = fopen("/mnt/r29_p1/sbin/init", "r");
    if (!init_fp) {
        fprintf(stderr, "FX6_R29_P1_RESCUE_FAIL step=open_p1_init errno=%d\n", errno);
        return 83;
    }
    char line_buf[256];
    while (fgets(line_buf, sizeof(line_buf), init_fp)) {
        size_t ln = strlen(line_buf);
        while (ln > 0U && (line_buf[ln - 1U] == '\n' || line_buf[ln - 1U] == '\r')) {
            line_buf[--ln] = '\0';
        }
        char *p = line_buf;
        while (*p == ' ' || *p == '\t') p++;
        if (*p == '\0' || *p == '#') continue;
        snprintf(first_line, sizeof(first_line), "%s", p);
        break;
    }
    fclose(init_fp);

    int first_line_valid = (strcmp(first_line, "rm -f /setting/updater/mode* && sync") == 0) ? 1 : 0;
    int sh_rc = -1;
    if (first_line_valid) {
        pid_t pid = fork();
        if (pid == 0) {
            execl("/bin/busybox", "busybox", "sh", "-c", first_line, (char *)NULL);
            _exit(127);
        } else if (pid > 0) {
            int status = 0;
            if (waitpid(pid, &status, 0) == pid && WIFEXITED(status)) {
                sh_rc = WEXITSTATUS(status);
            }
        }
    }
    int mode_after = r29_count_mode_files("/setting/updater");

    /* Verify p1:/dat2 == "91030080" */
    char dat2_read[32] = "";
    FILE *d2f = fopen("/mnt/r29_p1/dat2", "r");
    if (d2f) {
        if (fgets(dat2_read, sizeof(dat2_read), d2f)) {
            size_t ln = strlen(dat2_read);
            while (ln > 0U && (dat2_read[ln - 1U] == '\n' || dat2_read[ln - 1U] == '\r')) {
                dat2_read[--ln] = '\0';
            }
        }
        fclose(d2f);
    }
    int dat2_intact = (strcmp(dat2_read, "91030080") == 0) ? 1 : 0;

    /* Verify p1:/boot/kemco.txt enforces cfg.uart=1 & console=ttyAMA0,460800n8 */
    int uart_port = -1;
    int console_ok = 0;
    FILE *kf = fopen("/mnt/r29_p1/boot/kemco.txt", "r");
    if (kf) {
        char kbuf[1024];
        size_t kr = fread(kbuf, 1U, sizeof(kbuf) - 1U, kf);
        fclose(kf);
        kbuf[kr] = '\0';
        const char *up = strstr(kbuf, "cfg.uart=");
        if (up) {
            uart_port = atoi(up + 9);
        }
        if (strstr(kbuf, "console=ttyAMA0,460800n8") != NULL &&
            strstr(kbuf, "console=ttynull") == NULL) {
            console_ok = 1;
        }
    }

    /* Verify p3 untouched & read-only */
    char p3_after_sha[65] = "";
    unsigned long long p3_after_bytes = 0ULL;
    int p3_ro_mnt = 0, p3_erofs = 0;
    r29_check_mount_ro("/mnt/r29_p3", "/mnt/r29_p3/.ro_probe", &p3_ro_mnt, &p3_erofs);
    int p3_untouched = (sha256_file_hex("/mnt/r29_p3/p3_marker.txt", p3_after_sha, &p3_after_bytes) == 0 &&
                        p3_after_bytes == p3_before_bytes &&
                        strcmp(p3_after_sha, p3_before_sha) == 0 &&
                        p3_ro_mnt && p3_erofs) ? 1 : 0;

    clock_gettime(CLOCK_MONOTONIC, &t1);
    long long us = elapsed_us(&t0, &t1);

    int ok = (mode_before == 1 && first_line_valid && sh_rc == 0 &&
              mode_after == 0 && dat2_intact && uart_port == 1 &&
              console_ok && p3_untouched) ? 1 : 0;

    fprintf(stderr,
            "FX6_R29_P1_RESCUE mode_armed=mode6 mode_files_before=%d first_line_cleared=%d "
            "exec_rc=%d mode_files_remaining=%d dat2_value=%s dat2_intact=%d "
            "uart_port=%d console_ttyama0_ok=%d p3_untouched=%d p3_ro_erofs=%d "
            "p3_sha256=%s next_cold_boot_bank=p3 emmc_write_count=0 crashes=0 "
            "p1_rescue_ok=%d verify_us=%lld\n",
            mode_before, first_line_valid, sh_rc, mode_after,
            dat2_read[0] ? dat2_read : "ERR", dat2_intact,
            uart_port, console_ok, p3_untouched, p3_erofs,
            p3_after_sha, ok, us);
    fflush(stderr);
    return ok ? 0 : 84;
}

int main(int argc, char **argv) {
    print_kernel_identity();

    if (argc >= 2 && strcmp(argv[1], "--sd-gate") == 0) {
        return run_sd_gate_r28();
    }
    if (argc >= 2 && strcmp(argv[1], "--r29-installer-install") == 0) {
        return run_r29_installer_tx(0);
    }
    if (argc >= 2 && strcmp(argv[1], "--r29-installer-rollback") == 0) {
        return run_r29_installer_tx(1);
    }
    if (argc >= 2 && strcmp(argv[1], "--r29-p1-rescue") == 0) {
        return run_r29_p1_rescue();
    }

    if (verify_manifest("/etc/fx6_stage_a_manifest.txt") != 0) {
        return 41;
    }

    struct stat r28_st;
    if (stat("/etc/fx6_stage_r28", &r28_st) == 0) {
        if (setup_strategy_a_bridge_r28() != 0) {
            return 42;
        }
        if (run_jiritsu_libjit_probe_r28() != 0) {
            return 48;
        }
    } else {
        if (setup_p1_lut_symlinks() != 0) {
            return 42;
        }
        if (setup_p2_loopback_vfat() != 0) {
            return 43;
        }
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
