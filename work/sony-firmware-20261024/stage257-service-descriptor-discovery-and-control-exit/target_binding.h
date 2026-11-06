#ifndef FX3_STATUS_TARGET_BINDING_H
#define FX3_STATUS_TARGET_BINDING_H
#include <stdint.h>
#define FX3_FIXED_LOCATION 0x01100000u
#define FX3_CACHED_REGISTRY_ID 0ull
static const unsigned char FX3_FIXED_NONCE[16]={0};
static const unsigned char FX3_FIXED_PRIVACY_KEY[32]={0};
static inline int fx3_target_registry_permitted(uint64_t id,unsigned captured){return captured || id==FX3_CACHED_REGISTRY_ID;}
#endif
