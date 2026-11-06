#ifndef FX3_RECOVERY_FIXTURE_H
#define FX3_RECOVERY_FIXTURE_H
#include "global_guard.h"
typedef struct {fx3_recovery_policy policy;uint32_t variant;} fx3_fixture_recovery_context;
int fx3_fixture_recovery_load(const char *,uint32_t,fx3_fixture_recovery_context *);
int fx3_fixture_verify_recovery(void *,fx3_recovery_cache *);
#endif
