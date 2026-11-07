#include "typed_backup_reader.h"
#include <stdlib.h>
#include <string.h>
#ifdef FX6_READER_TEST_ALLOC
extern void *fx6_test_calloc(size_t, size_t);
#define FX6_CALLOC fx6_test_calloc
#else
#define FX6_CALLOC calloc
#endif

static int key_known(uint32_t id) {
    return id == 0x00fa0191U || id == 0x00fa0192U ||
           id == 0x00fa01a3U || id == 0x00fa01a4U;
}
static enum fx6_read_status check_output(void *out, size_t n) {
    if (n != 8) return FX6_READ_BAD_SIZE;
    if (!out) return FX6_READ_BAD_ARGUMENT;
    return FX6_READ_OK;
}
enum fx6_read_status fx6_template_read_u64(const struct fx6_backup_record *r,
    uint32_t id, void *out, size_t n) {
    if (!key_known(id)) return FX6_READ_NOT_HANDLED;
    enum fx6_read_status rc = check_output(out, n);
    if (rc != FX6_READ_OK) return rc;
    if (!r || r->record_index > 1 || r->item_count != 4)
        return FX6_READ_BAD_RECORD;
    /* Validate the whole small table before doing any write. */
    const struct fx6_backup_item *found = NULL;
    for (size_t i = 0; i < r->item_count; ++i) {
        if (!key_known(r->items[i].id) || r->items[i].length != 8)
            return FX6_READ_BAD_RECORD;
        for (size_t j = 0; j < i; ++j)
            if (r->items[i].id == r->items[j].id) return FX6_READ_BAD_RECORD;
        if (r->items[i].id == id) found = &r->items[i];
    }
    if (!found) return FX6_READ_BAD_RECORD;
    /* Decode little endian then copy a host scalar, permitting unaligned out. */
    uint64_t value = 0;
    for (size_t i = 0; i < 8; ++i) value |= (uint64_t)found->bytes[i] << (8*i);
    memcpy(out, &value, 8);
    return FX6_READ_OK;
}
struct fx6_owned_arena { unsigned char *base; size_t capacity, required; };
struct fx6_owned_arena *fx6_arena_create(size_t capacity, size_t required) {
    if (!capacity || !required || required > capacity || capacity > PTRDIFF_MAX)
        return NULL;
    struct fx6_owned_arena *a = FX6_CALLOC(1, sizeof *a);
    if (!a) return NULL;
    a->base = FX6_CALLOC(1, capacity);
    if (!a->base) { free(a); return NULL; }
    if ((uintptr_t)a->base > UINTPTR_MAX - capacity) {
        free(a->base); free(a); return NULL;
    }
    a->capacity = capacity; a->required = required;
    return a;
}
void fx6_arena_destroy(struct fx6_owned_arena *a) {
    if (a) { free(a->base); free(a); }
}
enum fx6_read_status fx6_arena_read_u64(const struct fx6_owned_arena *a,
    uint32_t id, void *out, size_t n) {
    if (!key_known(id)) return FX6_READ_NOT_HANDLED;
    enum fx6_read_status rc = check_output(out, n);
    if (rc != FX6_READ_OK) return rc;
    if (id == 0x00fa01a3U || id == 0x00fa01a4U)
        return FX6_READ_NO_CAPABILITY;
    if (!a || !a->base || !a->required || a->required > a->capacity)
        return FX6_READ_NO_CAPABILITY;
    uint64_t value = id == 0x00fa0191U ? (uint64_t)(uintptr_t)a->base : a->capacity;
    memcpy(out, &value, 8);
    return FX6_READ_OK;
}
