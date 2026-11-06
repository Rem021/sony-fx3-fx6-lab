#ifndef FX3_CACHED_PHYSICAL_PORT_ANCHOR_H
#define FX3_CACHED_PHYSICAL_PORT_ANCHOR_H
#include <stdint.h>
#include <IOKit/IOKitLib.h>
/* IORegistry properties only. No plug-in, USB user client or device request. */
int fx3_cached_port_anchor(io_registry_entry_t,uint64_t *,uint64_t *);
#endif
