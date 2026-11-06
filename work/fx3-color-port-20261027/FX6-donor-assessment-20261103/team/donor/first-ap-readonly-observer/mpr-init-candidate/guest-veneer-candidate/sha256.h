#pragma once
#include <stddef.h>
#include <stdint.h>
typedef struct { uint32_t state[8]; uint64_t count; uint8_t block[64]; size_t used; } fx6_sha256_ctx;
void fx6_sha256_init(fx6_sha256_ctx* c);
void fx6_sha256_update(fx6_sha256_ctx* c, const uint8_t* data, size_t size);
void fx6_sha256_final(fx6_sha256_ctx* c, uint8_t out[32]);
