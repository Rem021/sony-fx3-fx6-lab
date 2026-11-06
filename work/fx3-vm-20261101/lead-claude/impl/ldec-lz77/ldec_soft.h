#ifndef LDEC_SOFT_H
#define LDEC_SOFT_H
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif

enum ldec_status {
    LDEC_OK = 0, LDEC_E_ARGUMENT = 1, LDEC_E_LIMIT = 2,
    LDEC_E_TRUNCATED = 3, LDEC_E_TYPE = 4, LDEC_E_DISTANCE = 5,
    LDEC_E_OUTPUT = 6, LDEC_E_OVERLAP = 7
};

typedef struct ldec_soft_info {
    size_t input_bytes, output_bytes, blocks, raw_blocks;
    size_t literals, matches, max_distance;
} ldec_soft_info;

/* Exact src_len and dst_len, no framing/size header outside the supplied data.
 * dst == NULL validates without writing. Immutable input required throughout.
 * Validation pass precedes any output write: failure leaves dst unchanged.
 * src/dst must not overlap; info must not alias either range.
 * No allocation, OS calls, physical-address mapping, or completion messages.
 * 16 MiB per source/target is an implementation safety cap, not a hardware limit.
 * On failure info describes the validation progress (not committed output).
 */
int ldec_soft_decode(const uint8_t *src, size_t src_len,
                     uint8_t *dst, size_t dst_len, ldec_soft_info *info);
const char *ldec_soft_strerror(int status);
#ifdef __cplusplus
}
#endif
#endif
