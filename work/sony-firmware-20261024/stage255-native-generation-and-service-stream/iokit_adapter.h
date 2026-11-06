#ifndef FX3_GENERATION_IOKIT_ADAPTER_H
#define FX3_GENERATION_IOKIT_ADAPTER_H
#include "stream.h"
#include <IOKit/usb/IOUSBLib.h>
typedef struct fx3_native_usb fx3_native_usb;
/* No launch/authorization/capture policy is supplied by this library.
 * All functions below require a separately approved fixed root caller. */
int fx3_usb_cached_identity(uint32_t,uint16_t,const uint8_t [32],fx3_identity *);
/* expected is required, including the SERVICE endpoint pair. This component
 * has no default0336 profile and does not promote a fixture profile. */
int fx3_usb_open(fx3_route *,fx3_stream *,const fx3_identity *,uint32_t,
                 const uint8_t [32],const fx3_profile *,uint64_t);
/* Transfer exclusively owned, already-open MSC650 objects from the existing
 * owner. Pointers are cleared on acceptance to prevent outer double-close.
 * Ownership is transferred even when later profile validation fails; a
 * bound failed stream is retained for its single explicit retirement. */
int fx3_usb_take_msc(fx3_route *,fx3_stream *,const fx3_identity *,const uint8_t [32],
                    IOUSBDeviceInterface650 ***,IOUSBInterfaceInterface650 ***,uint64_t);
/* Request the SDK ReleaseDeviceMask exactly once on the fresh same-body MSC
 * node. No open, capture, zero-option re-enumeration or reset. The fixed
 * caller must own the corresponding capture lease. F_OK is API return only;
 * independently observe post-return node/drivers and physical camera state. */
fx3_call fx3_usb_request_driver_return(fx3_route *,const fx3_identity *,const uint8_t [32]);
#endif
