#pragma once
#include <stddef.h>
#include <stdint.h>
#define FX6DIAG_SOURCE_BYTES 0x290u
#define FX6DIAG_TARGET_BYTES 0x1f8u
typedef struct {
    uint8_t mapped[FX6DIAG_TARGET_BYTES];
    uint64_t original_callbacks[57];
    uint64_t target_thunks[57];
    uint64_t original_extra[18];
    uint32_t count;
    uint32_t slots[4];
    uint16_t source_u16;
    uint32_t extra_nonnull;
} fx6diag_plan;
enum {
    FX6DIAG_MAP_OK=0, FX6DIAG_MAP_LENGTH=1, FX6DIAG_MAP_COUNT=2,
    FX6DIAG_MAP_SENTINEL=3, FX6DIAG_MAP_DUPLICATE=4,
    FX6DIAG_MAP_U16=5, FX6DIAG_MAP_THUNK=6
};
int fx6diag_map(const uint8_t* source, size_t length,
                 const uintptr_t thunks[57], fx6diag_plan* result);
