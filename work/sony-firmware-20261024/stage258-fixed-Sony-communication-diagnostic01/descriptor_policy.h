#ifndef FX3_BOUNDED_SERVICE_DESCRIPTOR_POLICY_H
#define FX3_BOUNDED_SERVICE_DESCRIPTOR_POLICY_H
#include "stream.h"
#define FX3_CONFIG_MAX 128u
/* One configuration, one vendor interface, alt0, exactly2 or4 bulk512
 * endpoints. Primary endpoints are the first IN/OUT in descriptor order,
 * matching the pinned public driver's direction-filtered order. */
int fx3_parse_service_config(const uint8_t *,uint32_t,uint8_t,uint8_t,fx3_profile *);
#endif
