#ifndef FX6_TYPED_BACKUP_READER_H
#define FX6_TYPED_BACKUP_READER_H
#include <stddef.h>
#include <stdint.h>

/* These are THIS helper's statuses, never Sony Backup_* status values. */
enum fx6_read_status {
    FX6_READ_OK, FX6_READ_NOT_HANDLED, FX6_READ_BAD_SIZE,
    FX6_READ_BAD_ARGUMENT, FX6_READ_BAD_RECORD, FX6_READ_NO_CAPABILITY
};
struct fx6_backup_item { uint32_t id; size_t length; unsigned char bytes[8]; };
struct fx6_backup_record { size_t record_index; size_t item_count;
                          struct fx6_backup_item items[4]; };

/* Raw metadata reader: no address dereference, allocation, or native API claim.
 * The caller must supply a checksum/hash-validated record from the BYOF parser.
 * A returned UINT64_MAX is an observed template sentinel, not a usable mapping.
 * Every failure leaves the output unchanged; exactly 8 bytes are written on OK.
 */
enum fx6_read_status fx6_template_read_u64(const struct fx6_backup_record *,
    uint32_t id, void *output, size_t output_bytes);

struct fx6_owned_arena;
/* Allocates zeroed backing storage owned by this object. required_bytes must
 * come from the caller's verified consumer descriptors, not from Backup w2.
 * Context is immutable; no resizing/replacement while consumers retain base.
 * Destroy only after ALL consumer threads and retained references have ended.
 */
struct fx6_owned_arena *fx6_arena_create(size_t capacity, size_t required_bytes);
void fx6_arena_destroy(struct fx6_owned_arena *);
/* Only fa0191/fa0192 are supplied from the same owned allocation. The physical
 * fa01a3/fa01a4 pair has no mapping capability here and is explicitly refused.
 * Unknown ID is NOT_HANDLED: the adapter must call original or fail explicitly.
 */
enum fx6_read_status fx6_arena_read_u64(const struct fx6_owned_arena *,
    uint32_t id, void *output, size_t output_bytes);
#endif
