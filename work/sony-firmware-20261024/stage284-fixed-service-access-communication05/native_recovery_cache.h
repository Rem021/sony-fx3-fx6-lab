#ifndef FX3_NATIVE_RECOVERY_CACHE_H
#define FX3_NATIVE_RECOVERY_CACHE_H
#include "global_guard.h"
typedef struct {
    const fx3_recovery_policy *policy;
    const uint8_t *prior_privacy_key; /*32B fixed private material, never output*/
} fx3_native_recovery_context;
/* A root-only callback for the recovery journal. IORegistry/mount metadata
 * only; no USB user-client/interface, device request, media/file/card open. */
int fx3_native_verify_recovery_cache(void *,fx3_recovery_cache *);
#endif
