#ifndef FX3_BOUNDED_IOKIT_WIRE_H
#define FX3_BOUNDED_IOKIT_WIRE_H
#include <IOKit/usb/IOUSBLib.h>
#include <stdatomic.h>
#include <stdint.h>

#define FX3_IO_ABI 1u
#define FX3_IO_MAGIC 0x494f3635u
#define FX3_IO_N 516u
#define FX3_IO_API __attribute__((visibility("default")))
enum { IO_OK,IO_DENIED,IO_BUSY,IO_STALL,IO_TIMEOUT,IO_GONE,IO_ERROR,IO_SHORT,
       IO_BAD_COUNT,IO_BUFFER,IO_LATE,IO_CLOCK,IO_OWNER,IO_LIMIT,IO_DEADLINE,IO_SHAPE,IO_TOKEN,IO_CANCEL };
typedef struct {
    uint32_t abi,status,operation,requested,actual_known,reported_count,timeout_ms,native_returned;
    int32_t raw_return;
    uint32_t buffer_ok,owner_ok,body_effect_proven;
} fx3_io_result;
typedef struct {
    IOUSBDeviceInterface650 **device;
    IOUSBInterfaceInterface650 **interface;
    _Atomic uint32_t *owner_active,*stop_requested;
    _Atomic uint64_t *owner_generation;
    uint64_t generation,session_deadline_ns;
    uint32_t pipe_in,pipe_out,ep_in,ep_out,max_packet,mode,map_reviewed,protocol_scope_reviewed;
    uint64_t (*fixture_clock)(void *);
    void *fixture_clock_context;
} fx3_io_owner;
typedef struct {
    uint32_t magic,creator_pid,valid,failed,hard_unknown,start_sent,stop_sent,outs,ins,awaiting_in;
    uint64_t generation,last_token,last_now,observed_ns,observation_version,start_version,fault_version,operation_deadline_ns;
    _Atomic uint32_t pending;
    fx3_io_owner owner;
} fx3_io_context;

int fx3_io_bind(fx3_io_context *,const fx3_io_owner *);
FX3_IO_API int fx3_io_refresh(fx3_io_context *,uint64_t);
FX3_IO_API int fx3_io_invalidate(fx3_io_context *,uint64_t);
FX3_IO_API uint32_t fx3_io_pending(fx3_io_context *);
FX3_IO_API int fx3_io_control(fx3_io_context *,uint64_t,uint64_t,const uint8_t *,uint64_t,uint32_t,fx3_io_result *);
FX3_IO_API int fx3_io_out(fx3_io_context *,uint64_t,uint64_t,const uint8_t *,uint32_t,uint64_t,uint32_t,fx3_io_result *);
FX3_IO_API int fx3_io_in(fx3_io_context *,uint64_t,uint64_t,uint8_t *,uint32_t,uint64_t,uint32_t,fx3_io_result *);
#endif
