#ifndef FX3_OWNER_TRIAL_H
#define FX3_OWNER_TRIAL_H
#include <stdint.h>
#include <stddef.h>
#include <stdatomic.h>
#define FX3_OWNER_ABI 3u
#define FX3_OWNER_ARM 0x4f574e33u
#define FX3_OWNER_EVENTS 64u
enum { FX3_OBSERVED=0, FX3_ABORTED_RETURN_OBSERVED=1, FX3_RETURN_UNKNOWN=2, FX3_DENIED=3 };
enum { P_BEFORE=1, P_OPEN=2, P_PRE_CAPTURE=3, P_CAPTURE=4, P_REOPEN=5, P_PRE_CLAIM=6,
       P_CLAIM=7, P_PROFILE=8, P_RELEASE=9, P_RETURN=10, P_CLOSE=11, P_AFTER=12 };
typedef struct {
    uint32_t abi, arm, location, capture_permitted;
    uint16_t vid, pid;
    uint32_t reserved;
    uint64_t work_deadline_ns, final_deadline_ns;
    uint8_t privacy_key[32];
    uint8_t expected_body_tag[32];
} fx3_owner_config;
typedef struct {
    uint64_t registry_id;
    uint32_t media_count, mounted_count, media_unknown, storage_driver_count;
    uint16_t vid, pid;
    uint32_t location;
    uint8_t body_tag[32];
} fx3_owner_snapshot;
typedef struct { uint32_t interface_number, alternate, in_address, out_address, max_packet, endpoints; } fx3_owner_profile;
typedef struct { uint32_t phase; int32_t raw_return; } fx3_owner_event;
typedef struct {
    uint32_t abi, status, event_count, capture_attempted;
    uint32_t claim_attempted, interface_claimed, clock_invalid, cleanup_error;
    _Atomic uint32_t active_call_pending;
    uint32_t persistent_camera_or_vendor_commands;
    fx3_owner_snapshot before, after;
    fx3_owner_profile profile;
    fx3_owner_event events[FX3_OWNER_EVENTS];
} fx3_owner_result;
typedef struct { uint32_t abi; _Atomic uint32_t stop_requested; uint32_t reserved[2]; } fx3_owner_control;
typedef struct { _Atomic uint32_t released, entered; } fx3_fixture_gate;
typedef struct {
    int32_t (*snapshot)(void *, fx3_owner_snapshot *);
    int32_t (*open)(void *);
    int32_t (*capture)(void *);
    int32_t (*reopen)(void *);
    int32_t (*claim)(void *, fx3_owner_profile *);
    int32_t (*release_interface)(void *);
    int32_t (*return_driver)(void *);
    int32_t (*close)(void *);
    uint64_t (*now_ns)(void *);
    void (*pause_ms)(void *, uint32_t);
} fx3_owner_ops;
int fx3_owner_core(const fx3_owner_config *, fx3_owner_result *, fx3_owner_control *, const fx3_owner_ops *, void *);
#endif
