/* Sony LDEC block grammar, independently bounded implementation.
 * See lz77_format.md and results/public_sources.json for public corroboration.
 */
#include "ldec_soft.h"
#include <stdint.h>

#define LDEC_MAX_BYTES ((size_t)16 * 1024 * 1024)

static int walk(const uint8_t *s, size_t n, uint8_t *d, size_t cap,
                ldec_soft_info *st) {
    static const uint8_t lengths[16] = {3,4,5,6,7,8,9,10,11,12,13,14,15,16,32,64};
    size_t p = 0, o = 0;
    ldec_soft_info z = {0};
    int status = LDEC_OK;
#define FAIL(e) do { status = (e); goto end; } while (0)
    while (p < n) {
        size_t base = o;
        unsigned kind = s[p++];
        ++z.blocks;
        if (kind == 0x0f) {
            if (n - p < 3) FAIL(LDEC_E_TRUNCATED);
            size_t count = (size_t)s[p + 1] | (size_t)s[p + 2] << 8;
            p += 3; /* reserved byte ignored, as in public decoder */
            if (count > n - p) FAIL(LDEC_E_TRUNCATED);
            if (count > cap - o) FAIL(LDEC_E_OUTPUT);
            if (d) for (size_t j = 0; j < count; ++j) d[o + j] = s[p + j];
            p += count; o += count; ++z.raw_blocks;
        } else if (kind == 0xf0) {
            int ended = 0;
            while (!ended) {
                if (p == n) FAIL(LDEC_E_TRUNCATED);
                unsigned flags = s[p++];
                for (unsigned bit = 0; bit < 8; ++bit) {
                    if (flags & (1u << bit)) {
                        if (n - p < 2) FAIL(LDEC_E_TRUNCATED);
                        unsigned a = s[p++], b = s[p++];
                        size_t distance = (a & 15u) << 8 | b;
                        if (!distance) { ended = 1; break; }
                        size_t count = lengths[a >> 4];
                        if (distance > o - base) FAIL(LDEC_E_DISTANCE);
                        if (count > cap - o) FAIL(LDEC_E_OUTPUT);
                        if (d) for (size_t j = 0; j < count; ++j) d[o + j] = d[o + j - distance];
                        o += count; ++z.matches;
                        if (distance > z.max_distance) z.max_distance = distance;
                    } else {
                        if (p == n) FAIL(LDEC_E_TRUNCATED);
                        if (o == cap) FAIL(LDEC_E_OUTPUT);
                        if (d) d[o] = s[p];
                        ++p; ++o; ++z.literals;
                    }
                }
            }
        } else FAIL(LDEC_E_TYPE);
    }
    if (o != cap) FAIL(LDEC_E_OUTPUT);
end:
    z.input_bytes = p; z.output_bytes = o;
    if (st) *st = z;
    return status;
#undef FAIL
}

int ldec_soft_decode(const uint8_t *src, size_t src_len,
                     uint8_t *dst, size_t dst_len, ldec_soft_info *info) {
    if (info) { ldec_soft_info z = {0}; *info = z; }
    if (!src || !src_len || !dst_len) return LDEC_E_ARGUMENT;
    if (src_len > LDEC_MAX_BYTES || dst_len > LDEC_MAX_BYTES) return LDEC_E_LIMIT;
    uintptr_t s = (uintptr_t)src, d = (uintptr_t)dst;
    if (s > UINTPTR_MAX - src_len || (dst && d > UINTPTR_MAX - dst_len))
        return LDEC_E_ARGUMENT;
    if (dst && s < d + dst_len && d < s + src_len) return LDEC_E_OVERLAP;
    int result = walk(src, src_len, NULL, dst_len, info);
    if (result != LDEC_OK || !dst) return result;
    return walk(src, src_len, dst, dst_len, info);
}

const char *ldec_soft_strerror(int status) {
    switch (status) {
    case LDEC_OK: return "success";
    case LDEC_E_ARGUMENT: return "invalid argument";
    case LDEC_E_LIMIT: return "implementation size limit";
    case LDEC_E_TRUNCATED: return "truncated block/token or missing terminator";
    case LDEC_E_TYPE: return "unknown block type";
    case LDEC_E_DISTANCE: return "distance outside current block history";
    case LDEC_E_OUTPUT: return "output overflow or exact size mismatch";
    case LDEC_E_OVERLAP: return "source/destination overlap";
    default: return "unknown status";
    }
}
