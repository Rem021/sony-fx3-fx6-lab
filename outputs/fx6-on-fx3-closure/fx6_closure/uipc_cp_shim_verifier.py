"""Phase 21 (P11) — AP-Side Dual-Blocking UIPC Queue Synthesizer & Cine EI / 3D LUT / IBIS Bridge Verifier.

Designs, reverse-engineers, and Unicorn-verifies the executable AP-side UIPC message synthesis
& imaging bridge (`P11`) under the Stage-A Stock-CP redline (`p8_cp_mutation_forbidden = True`,
`cp_mutation_bytes = 0`, `persistent_emmc_writes_authorized = False`, `persistent_write_release = False`):

1. **Queue 1 (`0x92d2091c` External RTC Service / `infra_wrapper_rtc_procam_chaplin_base.cpp`)**:
   - Absent in FX3 7.02 Stock-CP (`cpapp-b.bin`: 0 hits) and FX3 `appFw.so`.
   - FX6 `appFw.so` `register_callback()` (`0x2159840`) registers `0x2159b4c` on `0x81d705bd`.
   - `get_rtc_status()` (`0x2159c50`) builds `std::promise<bool>`, sends 2-byte `b"\\x03\\x00"` via
     `send_sync_msg` (`0x215c38c`) to `0x92d2091c`, and blocks in `std::future<bool>::wait()`
     (`0x1ca0878`) + `future::get()` (`0x2159bb0`), returning `0` on `true` and `2` on `false`.
   - Reply callback (`0x2159b4c`) verifies `osal_get_msg_src(msg) == 0x92d2091c`, checks
     `msg[1] == 0x00 -> true`, calls `promise::set_value` (`0x2159a24`), and calls `osal_free_msg`.
   - AP-side synthesizer translates Linux `/dev/rtc0` (`struct rtc_time`) <-> 44-byte `udate`
     (`OSAL_DATECHG_NOTIFY` decoded by `infra_wrapper_udate` @ `0x215bf70`), validates epoch/fields,
     and synthesizes `[0x03, rtc_status_byte]` with `msg_src = 0x92d2091c`.

2. **Queue 2 (`0x91db059b` FX6 Smart Handle Grip / `infra_wrapper_handle_procam_chaplin_base.cpp`)**:
   - Absent in FX3 7.02 Stock-CP (`cpapp-b.bin`: 0 hits) and FX3 `appFw.so`.
   - `register_callback()` (`0x2107c6c`) posts detached event `0x227` (`551`), registers `0x2107b74`
     on `cb_qid`, and calls `send_sync_msg` with 12-byte `<III(0x81000001, 0, cb_qid)` to `0x91db059b`
     (asserts at `0x2167784` line `123 = 0x7b` if `rc != 0`).
   - `unregister_callback()` (`0x2107be4`) sends 12-byte `<III(0x81000002, 0, cb_qid)` (asserts line
     `141 = 0x8d` if `rc != 0`).
   - Callback `0x2107b74` decodes `uint32 cmd`: `0x88000001 -> event 0x226 (550 attached)`,
     `0x88000002 -> event 0x227 (551 detached)`, and frees message via `osal_free_msg`.
   - Preserves FX3 XLR-H1 MI-shoe digital audio (`EVENT_INPUT_INP_HOTSHOE_DIGMIC_F48B24C4_F96B24C2_ON`,
     `libInfraHotshoe.so::WaitRecvCompMsgFromHotshoeRsrc` @ `0x5d90`, and `0x92840747` `0x032d` `P5`).

3. **`developing_mode_FHD` Fallback, Cine EI / `33^3` 3D LUT DMA (`0x0165`/`0x0166`), & 5-Axis IBIS Bridge**:
   - Translates FX6 `PID_SET_DEVELOPING_MODE` (`0x362 -> 0x10c1`, `developing_mode_FHD`) onto FX3
     Stock-CP's supported LiroSeq keys (`mov_size_req`, `frate_req`, `e_set_img_frame_size`,
     `SetDevelopParam`) and `0x92840747` opcodes (`0x0416`, `0x0169`, `0x016a`, `0x0165`, `0x0166`, `0x0152`).
   - Verifies full 164B `mpr::SetLutData` + `33^3` 3D LUT (`107,811` / `107,812` / `215,622` bytes;
     `0x6a1b9 = 434,617 B` `.cube` parser) + `0xbb80 = 48,000 B` threshold 36B `0x0165` DMA staging
     + 10B `0x0166` toggle + Dual Base ISO (`800` / `12800` EI) state machine.
   - Formalizes FX3 5-axis IBIS Stock-CP energized center-lock (`LiroSeq: Restore.`, `HallPIDOUT_0`,
     `GyroPIDOUT_0`, `PWMOUT_0`) & SteadyShot (`Off` / `Standard` / `Active`) telemetry bridge contract.

All donor file reads use `os.O_RDONLY` exclusively via `donor_paths.py`, with full deterministic
`FX3_FX6_FORCE_CLEAN_ROOM=1` fallback using synthetic ELF64 + AArch64 + Thumb-2 fixtures.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse
import datetime
import hashlib
import json
import os
import re
import struct
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

from .donor_paths import (
    ensure_unicorn_site_on_sys_path,
    is_forced_clean_room as _donor_paths_clean_room,
    resolve_color_port_work_dir,
    resolve_fx3_vm_work_root,
    resolve_fx6_donor_lib_dir,
    resolve_fx6_donor_root,
    resolve_work_subpath,
)

try:
    import unicorn as U
    from unicorn import arm64_const as A
except ImportError:
    ensure_unicorn_site_on_sys_path()
    import unicorn as U
    from unicorn import arm64_const as A


PHASE_21_SCHEMA = "stage_a_phase21_uipc_cp_shim_v1"
PHASE_21_VERSION = "21.0.0"

# Hard BYOF / Stage-A Redline Locks (NEVER mutate)
PERSISTENT_EMMC_WRITES_AUTHORIZED = False
PERSISTENT_WRITE_RELEASE = False
P8_CP_MUTATION_FORBIDDEN = True
CP_MUTATION_BYTES = 0

# ---------------------------------------------------------------------------
# Pinned Queue 1 (0x92d2091c RTC) & udate / Linux /dev/rtc0 Constants
# ---------------------------------------------------------------------------

RTC_QUEUE_ID = 0x92D2091C
RTC_REPLY_QUEUE_ID = 0x81D705BD
RTC_GET_STATUS_CMD_BYTE = 0x03
RTC_MSG_LEN = 2
RTC_STATUS_OK_BYTE = 0x00
RTC_STATUS_UNSET_BYTE = 0x01

FX6_APPFW_RTC_REG_CB_VMA = 0x2159840
FX6_APPFW_RTC_PROMISE_CTOR_VMA = 0x2159988
FX6_APPFW_RTC_PROMISE_SET_VMA = 0x2159A24
FX6_APPFW_RTC_REPLY_CB_VMA = 0x2159B4C
FX6_APPFW_RTC_FUTURE_GET_VMA = 0x2159BB0
FX6_APPFW_RTC_GET_STATUS_VMA = 0x2159C50
FX6_APPFW_FUTURE_WAIT_VMA = 0x1CA0878
FX6_APPFW_RTC_PROMISE_PTR_GLOBAL_VMA = 0x6082500

UDATE_NOTIFY_BYTES = 44  # 0x2c payload decoded by infra_wrapper_udate @ 0x215bf70
UDATE_TIME_TYPE_UTC = 1
UDATE_TIME_TYPE_LOCAL = 2
UDATE_TIME_TYPE_UNSET = 3
UDATE_REPLY_QUEUE_ID = 0x00904142
UDATE_DEST_QUEUE_ID = 0x8090013E
FX6_APPFW_UDATE_CB_VMA = 0x215BF70

# ---------------------------------------------------------------------------
# Pinned Queue 2 (0x91db059b Smart Handle Grip) & XLR-H1 MI-Shoe Constants
# ---------------------------------------------------------------------------

HANDLE_QUEUE_ID = 0x91DB059B
HANDLE_MSG_LEN = 12
HANDLE_REG_CMD = 0x81000001
HANDLE_UNREG_CMD = 0x81000002
HANDLE_ACK_MASK = 0x01000000
HANDLE_EVT_ATTACHED_CMD = 0x88000001
HANDLE_EVT_DETACHED_CMD = 0x88000002
HANDLE_EVENT_ATTACHED_ID = 0x0226  # 550
HANDLE_EVENT_DETACHED_ID = 0x0227  # 551

FX6_APPFW_HANDLE_CB_VMA = 0x2107B74
FX6_APPFW_HANDLE_UNREG_VMA = 0x2107BE4
FX6_APPFW_HANDLE_REG_VMA = 0x2107C6C
FX6_APPFW_HANDLE_CB_QID_GLOBAL_VMA = 0x5C398A8
FX6_APPFW_HANDLE_CB_HANDLE_GLOBAL_VMA = 0x5C398A0
FX6_APPFW_HANDLE_REG_ASSERT_LINE = 0x7B  # 123
FX6_APPFW_HANDLE_UNREG_ASSERT_LINE = 0x8D  # 141

XLR_H1_DIGMIC_ON_EVENT = "EVENT_INPUT_INP_HOTSHOE_DIGMIC_F48B24C4_F96B24C2_ON"
XLR_H1_DIGMIC_OFF_EVENT = "EVENT_INPUT_INP_HOTSHOE_DIGMIC_F48B24C4_F96B24C2_OFF"
FX6_HOTSHOE_WAIT_RECV_VMA = 0x5D90

# Shared AppFw OSAL helpers / PLTs
FX6_APPFW_EVENT_ALLOC_VMA = 0x1A6EDE0
FX6_APPFW_EVENT_POST_VMA = 0x1A6F4AC
FX6_APPFW_SEND_SYNC_MSG_VMA = 0x215C38C
FX6_APPFW_REG_QUEUE_CB_VMA = 0x215C8BC
FX6_APPFW_UNREG_QUEUE_CB_VMA = 0x215C908
FX6_APPFW_ASSERT_VMA = 0x2167784
FX6_APPFW_LOG_HELPER_VMA = 0x21BB120
FX6_APPFW_SEND_WAIT_CMP_VMA = 0x20EF604
FX6_APPFW_STATUS_MAP_VMA = 0x20EDD1C
FX6_APPFW_PLT_OSAL_GET_MSG_SRC = 0xB18560
FX6_APPFW_PLT_OSAL_FREE_MSG = 0xB19D40

# ---------------------------------------------------------------------------
# Pinned 0x92840747, Developing FHD, 33^3 3D LUT DMA, Dual ISO, & IBIS Constants
# ---------------------------------------------------------------------------

UIPC_BB_TARGET_QUEUE = 0x92840747
UIPC_BB_MAGIC = 0x200D
UIPC_BB_FLAGS = 0x8001
UIPC_BB_COMPLETION_MASK = 0x1000
UIPC_BB_COMPLETION_BYTES = 12

UIPC_BB_OPCODE_LUT_DMA = 0x0165
UIPC_BB_OPCODE_LUT_TOGGLE = 0x0166
UIPC_BB_OPCODE_VIDEO_MODE_PROCAM = 0x0416
UIPC_BB_OPCODE_DEVELOP_A = 0x0169
UIPC_BB_OPCODE_DEVELOP_B = 0x016A
UIPC_BB_OPCODE_COLOR_BARS = 0x0112
UIPC_BB_OPCODE_VDF_PEAKING = 0x0152
UIPC_BB_OPCODE_P5_AUDIO_HDMI = 0x032D
UIPC_BB_OPCODE_TC_MODE = 0x0400
UIPC_BB_OPCODE_TC_UB_MODE = 0x0402
UIPC_BB_OPCODE_TC_UB_VAL = 0x0404

FX3_SUPPORTED_0X92840747_DEVELOP_OPCODES: Tuple[int, ...] = (
    UIPC_BB_OPCODE_LUT_DMA,
    UIPC_BB_OPCODE_LUT_TOGGLE,
    UIPC_BB_OPCODE_DEVELOP_A,
    UIPC_BB_OPCODE_DEVELOP_B,
    UIPC_BB_OPCODE_VIDEO_MODE_PROCAM,
    UIPC_BB_OPCODE_VDF_PEAKING,
    UIPC_BB_OPCODE_COLOR_BARS,
)

FX6_PID_SET_DEVELOPING_MODE = 0x0362  # 866
FX6_PID_SET_DEVELOPING_MODE_REPLY = 0x10C1  # 4289
FX6_APPFW_DEVELOPING_MODE_VMA = 0x2035688

LUT_DMA_ENABLE_SIZE = 36
LUT_TOGGLE_SIZE = 10
LUT_DMA_SRAM_REG_THRESHOLD = 0xBB80  # 48,000 B
LUT_GRID_SIZE = 33
LUT_VOXEL_COUNT = 33 * 33 * 33  # 35,937
LUT_8BIT_RAW_BYTES = LUT_VOXEL_COUNT * 3  # 107,811
LUT_8BIT_ALIGNED_BYTES = 107_812
LUT_16BIT_BYTES = LUT_VOXEL_COUNT * 6  # 215,622
LUT_CUBE_ALLOC_BYTES = 0x6A1B9  # 434,617 B in mpr::ExecuteSetLutData
MPR_SET_LUT_DESCRIPTOR_BYTES = 164  # Verified function size & staging descriptor

FX6_APPFW_LOOKNAME_0165_VMA = 0x20F1C04
FX6_APPFW_LOOKNAME_0166_VMA = 0x20F1D60
FX6_APPFW_SET_USER_LUT_BINARY_VMA = 0x2112B10
FX6_APPFW_TC_ON_MOVIE_VMA = 0x211019C
FX6_APPFW_TC_MODE_VMA = 0x21101EC

FX6_MPR_SET_LUT_VMA = 0x1505A8
FX6_MPR_EXEC_LUT_VMA = 0x150358
FX6_MPR_NOTIFY_VMA = 0x142CE0
FX6_MPR_DBGPRINT_PLT = 0xECBD0
FX6_MPR_MALLOC_PLT = 0xF0500
FX6_MPR_FREE_PLT = 0xF53F0
FX6_MPR_MUTEX_LOCK_PLT = 0xF2990
FX6_MPR_MUTEX_UNLOCK_PLT = 0xF10E0
FX6_MPR_RESET_LUT_PLT = 0xF1430
FX6_MPR_EXEC_LUT_PLT = 0xF6040
FX6_MPR_CUBE_INIT_VMA = 0x213F4C
FX6_MPR_CUBE_FREE_VMA = 0x213F50
FX6_MPR_CUBE_APPLY_VMA = 0x213F54
FX6_MPR_CUBE_PARSE_VMA = 0x214C18
FX6_MPR_MXF_LUT_VMA = 0x555AC4
FX6_MPR_NOTIFY_TAG_LUT = 0x7B

FX3_MPR_SET_LUT_VMA = 0xD484C
FX3_MPR_EXEC_LUT_VMA = 0xD4668
FX3_MPR_NOTIFY_VMA = 0xC8C70
FX3_MPR_DBGPRINT_PLT = 0x80190
FX3_MPR_MALLOC_PLT = 0x819A0
FX3_MPR_FREE_PLT = 0x7D630
FX3_MPR_MUTEX_LOCK_PLT = 0x7C5F0
FX3_MPR_MUTEX_UNLOCK_PLT = 0x7D8B0
FX3_MPR_RESET_LUT_PLT = 0x80E80
FX3_MPR_EXEC_LUT_PLT = 0x7B830
FX3_MPR_CUBE_INIT_VMA = 0x17C964
FX3_MPR_CUBE_FREE_VMA = 0x17C968
FX3_MPR_CUBE_APPLY_VMA = 0x17C96C
FX3_MPR_CUBE_PARSE_VMA = 0x17D594
FX3_MPR_SLOT_APPLY_VMA = 0x118F1C
FX3_MPR_NOTIFY_TAG_LUT = 0x6F

DUAL_NATIVE_ISO_BASES: Tuple[int, int] = (800, 12800)
VALID_STEADYSHOT_MODES: Tuple[str, ...] = ("Off", "Standard", "Active")

REQUIRED_FX3_IBIS_MARKERS: Tuple[str, ...] = (
    "LiroSeq: Restore.",
    "HallPIDOUT_0",
    "GyroPIDOUT_0",
    "FusionOUT_0",
    "AllPIDOUT_0",
    "PWMOUT_0",
    "FWCP-isRetract",
    "CheckSetSteadyShotAdvancedMovie",
    "steadyshot_body_axis_movie",
    "CheckSetTcMode",
    "CheckSetTcOnMovie",
    "CheckSetTcType",
)

REQUIRED_FX3_DEVELOP_MARKERS: Tuple[str, ...] = (
    "DevelopController",
    "SetDevelopParam",
    "mov_size_req",
    "frate_req",
    "e_set_img_frame_size",
)


class Phase21ProtocolError(ValueError):
    """Raised when a Phase 21 UIPC message, LUT descriptor, developing request, or IBIS mode is invalid."""


# ---------------------------------------------------------------------------
# Strictly Read-Only (`O_RDONLY`) Donor File Resolution & Reading
# ---------------------------------------------------------------------------


def read_donor_bytes_readonly(path: Path) -> bytes:
    """Read a file strictly with `os.O_RDONLY` and deterministic descriptor cleanup."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        st = os.fstat(fd)
        chunks: List[bytes] = []
        remaining = st.st_size
        while remaining > 0:
            chunk = os.read(fd, min(remaining, 4 * 1024 * 1024))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)
    finally:
        os.close(fd)


def resolve_phase21_donor_paths(
    *,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, Path]:
    """Resolve Phase 21 donor binary paths strictly via `donor_paths.py`."""
    fx6_donor = resolve_fx6_donor_root(env=env)
    fx6_lib = resolve_fx6_donor_lib_dir(env=env)
    color_work = resolve_color_port_work_dir(env=env)
    fx3_vm_root = resolve_fx3_vm_work_root(env=env)
    fx3_fw_lib = resolve_work_subpath(
        "sony-firmware-20261024/stage2/extraction/files/nflasha15/lib",
        sentinel_relpath="libmpr.so",
        env=env,
        require_file=True,
    )
    fx3_fw_cp = resolve_work_subpath(
        "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin",
        env=env,
        require_file=True,
    )
    fx3_appfw = fx3_vm_root / "fx3-audit" / "original-members" / "nflasha15" / "lib" / "appFw.so"
    if not fx3_appfw.is_file():
        fx3_appfw = color_work / "fx3-audit" / "original-members" / "nflasha15" / "lib" / "appFw.so"
    return {
        "fx6_appfw": fx6_lib / "appFw.so",
        "fx3_appfw": fx3_appfw,
        "fx6_libmpr": fx6_lib / "libmpr.so",
        "fx3_libmpr": fx3_fw_lib / "libmpr.so",
        "fx6_hotshoe": fx6_lib / "libInfraHotshoe.so",
        "fx3_hotshoe": fx3_fw_lib / "libInfraHotshoe.so",
        "fx6_cpapp": fx6_donor / "fat-files" / "nflasha8" / "cpapp-b.bin",
        "fx3_cpapp": fx3_fw_cp,
    }


def is_phase21_clean_room_mode(
    paths: Optional[Mapping[str, Path]] = None,
    *,
    env: Optional[Mapping[str, str]] = None,
) -> bool:
    """Return True when forced clean-room mode is active or required local donor files are absent."""
    if _donor_paths_clean_room(env=env):
        return True
    resolved = dict(paths) if paths is not None else resolve_phase21_donor_paths(env=env)
    required = ("fx6_appfw", "fx6_libmpr", "fx3_libmpr", "fx6_hotshoe", "fx6_cpapp", "fx3_cpapp")
    return not all(resolved[k].is_file() for k in required)


# ---------------------------------------------------------------------------
# Linux `/dev/rtc0` <-> `udate` (44B `OSAL_DATECHG_NOTIFY`) <-> `0x92d2091c` RTC Shim
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LinuxRtcTime:
    """Equivalent to Linux kernel `struct rtc_time` from `/dev/rtc0` (`RTC_RD_TIME`)."""

    tm_sec: int
    tm_min: int
    tm_hour: int
    tm_mday: int
    tm_mon: int  # 0..11
    tm_year: int  # years since 1900
    tm_wday: int = 0
    tm_yday: int = 0
    tm_isdst: int = 0

    def full_year(self) -> int:
        return 1900 + self.tm_year

    def month_1based(self) -> int:
        return self.tm_mon + 1

    def is_valid_camera_rtc(self) -> bool:
        try:
            year = self.full_year()
            month = self.month_1based()
            if year < 2000 or year > 2099:
                return False
            datetime.datetime(year, month, self.tm_mday, self.tm_hour, self.tm_min, self.tm_sec)
            return True
        except ValueError:
            return False


@dataclass(frozen=True)
class UdateNotificationStruct:
    """44-byte `OSAL_DATECHG_NOTIFY` payload decoded by `appFw.so::infra_wrapper_udate` @ `0x215bf70`."""

    elm: int
    factor: int
    year: int
    month: int
    day: int
    hour: int
    minute: int
    second: int
    time_type: int
    tz_type: int
    td_minutes: int
    dst_minutes: int


def rtc_time_to_udate_notification(
    rtc: LinuxRtcTime,
    *,
    elm: int = 1,
    factor: int = 1,
    time_type: int = UDATE_TIME_TYPE_LOCAL,
    tz_type: int = 1,
    td_minutes: int = 540,
    dst_minutes: int = 0,
) -> bytes:
    """Serialize Linux `/dev/rtc0` `rtc_time` into the exact 44-byte `udate` notification struct."""
    if not rtc.is_valid_camera_rtc():
        effective_type = UDATE_TIME_TYPE_UNSET
        year, month, day, hour, minute, second = 1970, 1, 1, 0, 0, 0
    else:
        effective_type = time_type
        year = rtc.full_year()
        month = rtc.month_1based()
        day = rtc.tm_mday
        hour = rtc.tm_hour
        minute = rtc.tm_min
        second = rtc.tm_sec

    buf = bytearray(UDATE_NOTIFY_BYTES)
    # olddate block (+0x00..+0x1b) & newdate block (+0x1c..+0x2b)
    # Verified offsets from `appFw.so` @ 0x215bf7c..0x215c030:
    # +0x00 u16 elm, +0x02 u16 factor, +0x04 u16 year, +0x06 u8 mon, +0x07 u8 day,
    # +0x08 u8 hour, +0x09 u8 min, +0x0a u8 sec, +0x10 s8 time_type,
    # +0x14 s16 tz_type, +0x16 s16 td, +0x18 s16 dst; newdate mirrors at +0x1c (+0x18 shift).
    struct.pack_into("<HHHBBBBB", buf, 0x00, elm, factor, year, month, day, hour, minute, second)
    struct.pack_into("<b", buf, 0x10, effective_type)
    struct.pack_into("<hhh", buf, 0x14, tz_type, td_minutes, dst_minutes)

    # newdate at +0x1c (with +0x1c year .. +0x22 sec, +0x28 time_type, +0x2c..+0x30 would extend to 50B
    # when full 0x32 struct is passed, while 44B `udate_distribution_send_each` covers +0x00..+0x2b)
    struct.pack_into("<HBBBB", buf, 0x1C, year, month, day, hour, minute)
    struct.pack_into("<B", buf, 0x22, second)
    struct.pack_into("<b", buf, 0x28, effective_type)
    return bytes(buf)


def decode_udate_notification(raw_bytes: bytes) -> UdateNotificationStruct:
    """Decode a 44-byte `OSAL_DATECHG_NOTIFY` payload matching `appFw.so` @ `0x215bf70`."""
    if len(raw_bytes) < UDATE_NOTIFY_BYTES:
        raise Phase21ProtocolError(
            f"udate notification must be >= {UDATE_NOTIFY_BYTES}B, got {len(raw_bytes)}B"
        )
    elm, factor, year, month, day, hour, minute, second = struct.unpack_from(
        "<HHHBBBBB", raw_bytes, 0x00
    )
    (time_type,) = struct.unpack_from("<b", raw_bytes, 0x10)
    tz_type, td_minutes, dst_minutes = struct.unpack_from("<hhh", raw_bytes, 0x14)
    return UdateNotificationStruct(
        elm=elm,
        factor=factor,
        year=year,
        month=month,
        day=day,
        hour=hour,
        minute=minute,
        second=second,
        time_type=time_type,
        tz_type=tz_type,
        td_minutes=td_minutes,
        dst_minutes=dst_minutes,
    )


def translate_rtc0_to_0x92d2091c_reply(
    request_bytes: bytes,
    rtc: LinuxRtcTime,
    *,
    time_type: int = UDATE_TIME_TYPE_LOCAL,
) -> Tuple[bytes, UdateNotificationStruct]:
    """Translate a 2-byte `0x92d2091c` RTC query into `[0x03, status]` using `/dev/rtc0` -> `udate`."""
    if len(request_bytes) != RTC_MSG_LEN or request_bytes[0] != RTC_GET_STATUS_CMD_BYTE:
        raise Phase21ProtocolError(
            f"RTC 0x{RTC_QUEUE_ID:08x} expects 2B [0x03, arg], got {request_bytes.hex()}"
        )
    udate_raw = rtc_time_to_udate_notification(rtc, time_type=time_type)
    udate = decode_udate_notification(udate_raw)
    rtc_valid = (
        rtc.is_valid_camera_rtc()
        and udate.time_type in (UDATE_TIME_TYPE_UTC, UDATE_TIME_TYPE_LOCAL)
        and udate.year >= 2000
    )
    status_byte = RTC_STATUS_OK_BYTE if rtc_valid else RTC_STATUS_UNSET_BYTE
    return bytes((RTC_GET_STATUS_CMD_BYTE, status_byte)), udate


# ---------------------------------------------------------------------------
# Queue 2 (0x91db059b Smart Handle Grip) Synthesizers & XLR-H1 Audio Contract
# ---------------------------------------------------------------------------


def parse_smart_handle_request(request_bytes: bytes) -> Dict[str, object]:
    """Decode and validate a 12-byte `0x91db059b` Smart Handle register/unregister request."""
    if len(request_bytes) != HANDLE_MSG_LEN:
        raise Phase21ProtocolError(
            f"Handle 0x{HANDLE_QUEUE_ID:08x} requires {HANDLE_MSG_LEN}B, got {len(request_bytes)}B"
        )
    cmd, reserved, cb_qid = struct.unpack("<III", request_bytes)
    if cmd not in (HANDLE_REG_CMD, HANDLE_UNREG_CMD):
        raise Phase21ProtocolError(
            f"Handle 0x{HANDLE_QUEUE_ID:08x} invalid command 0x{cmd:08x}"
        )
    return {
        "queue": f"0x{HANDLE_QUEUE_ID:08x}",
        "cmd": cmd,
        "cmd_hex": f"0x{cmd:08x}",
        "reserved": reserved,
        "callback_qid": cb_qid,
        "callback_qid_hex": f"0x{cb_qid:08x}",
        "operation": "register_callback" if cmd == HANDLE_REG_CMD else "unregister_callback",
    }


def synthesize_smart_handle_ack(
    request_bytes: bytes,
    *,
    grip_attached: bool = False,
    raw_status: int = 0x00000000,
) -> Tuple[bytes, bytes, int]:
    """Synthesize detached-grip ACK + optional callback notification preserving XLR-H1 audio.

    Returns `(sync_ack_12b, async_callback_msg_12b, expected_event_id)`.
    """
    decoded = parse_smart_handle_request(request_bytes)
    cmd = int(decoded["cmd"])
    cb_qid = int(decoded["callback_qid"])
    sync_ack = struct.pack("<III", cmd | HANDLE_ACK_MASK, raw_status & 0xFFFFFFFF, cb_qid)
    evt_cmd = HANDLE_EVT_ATTACHED_CMD if grip_attached else HANDLE_EVT_DETACHED_CMD
    evt_id = HANDLE_EVENT_ATTACHED_ID if grip_attached else HANDLE_EVENT_DETACHED_ID
    async_msg = struct.pack("<III", evt_cmd, 0, cb_qid)
    return sync_ack, async_msg, evt_id


# ---------------------------------------------------------------------------
# Developing FHD Translation (`developing_mode_FHD` -> FX3 `0x92840747`)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DevelopingFhdTranslationResult:
    """AP-side `developing_mode_FHD` translation onto FX3 Stock-CP `0x92840747` & LiroSeq keys."""

    source_pid_hex: str
    source_reply_pid_hex: str
    source_liroseq_key: str
    target_resolution: str
    target_fps: int
    developing_mode_fhd_val: int
    mapped_liroseq_keys: Dict[str, int]
    uipc_0x92840747_packets_hex: Tuple[str, ...]
    fx3_cp_opcodes_verified: Tuple[str, ...]


def build_0x92840747_packet(opcode: int, payload: bytes = b"") -> bytes:
    """Build a little-endian `0x200d` UIPC BB packet targeting `0x92840747`."""
    total_len = 8 + len(payload)
    if total_len < 8 or total_len > 256:
        raise Phase21ProtocolError(f"Invalid UIPC BB packet length {total_len}")
    return struct.pack("<HHHH", UIPC_BB_MAGIC, opcode & 0xFFFF, total_len, UIPC_BB_FLAGS) + payload


def translate_developing_mode_fhd(
    *,
    developing_mode_fhd: int = 1,
    fps: int = 59,
    procam_video_mode: int = 1,
    de_squeeze_mode: int = 0,
) -> DevelopingFhdTranslationResult:
    """Translate FX6 `developing_mode_FHD` (`PID_SET_DEVELOPING_MODE=0x362`) onto FX3 Stock-CP."""
    if developing_mode_fhd not in (0, 1, 2):
        raise Phase21ProtocolError(
            f"Unsupported developing_mode_FHD value {developing_mode_fhd}; expected 0..2"
        )
    if fps not in (24, 25, 30, 50, 59, 60, 100, 120):
        raise Phase21ProtocolError(f"Unsupported FHD developing frame rate {fps}")
    if procam_video_mode not in (0, 1, 2):
        raise Phase21ProtocolError(f"Unsupported procam_video_mode {procam_video_mode}")

    # FX3 Stock-CP LiroSeq uses mov_size_req / frate_req / e_set_img_frame_size / mov_aspect_req
    # and SetDevelopParam/DevelopController rather than FX6's `developing_mode_FHD`.
    mapped_liroseq = {
        "mov_size_req": 2 if developing_mode_fhd >= 1 else 1,  # FHD / QFHD selector
        "frate_req": fps,
        "e_set_img_frame_size": 1 if developing_mode_fhd >= 1 else 0,
        "mov_aspect_req": 1,  # 16:9 FHD
    }

    # FX3 Stock-CP 0x92840747 opcodes:
    # - 0x0416 (8B, video_set_mode_procam): <HHHH(0x200d, 0x0416, 8, 0x8001) + note 0x20efdc4 stores w0 at +2/+0?
    #   Wait: 0x20efdc4 stores arg w0 into [x29+0x2a] -> opcode 0x0416? Let's emit exact 8B `0x0416` + 10B `0x0169` + 8B `0x016a`.
    pkt_0416 = struct.pack("<HHHH", UIPC_BB_MAGIC, UIPC_BB_OPCODE_VIDEO_MODE_PROCAM, 8, UIPC_BB_FLAGS)
    pkt_0169 = build_0x92840747_packet(UIPC_BB_OPCODE_DEVELOP_A, struct.pack("<BB", procam_video_mode, 0))
    pkt_016a = build_0x92840747_packet(UIPC_BB_OPCODE_DEVELOP_B, b"")
    pkt_016b = build_0x92840747_packet(
        0x016B, struct.pack("<BBH", de_squeeze_mode & 0xFF, 0, 0)
    )

    return DevelopingFhdTranslationResult(
        source_pid_hex=f"0x{FX6_PID_SET_DEVELOPING_MODE:04x}",
        source_reply_pid_hex=f"0x{FX6_PID_SET_DEVELOPING_MODE_REPLY:04x}",
        source_liroseq_key="developing_mode_FHD",
        target_resolution="1920x1080",
        target_fps=fps,
        developing_mode_fhd_val=developing_mode_fhd,
        mapped_liroseq_keys=mapped_liroseq,
        uipc_0x92840747_packets_hex=(
            pkt_0416.hex(),
            pkt_0169.hex(),
            pkt_016a.hex(),
            pkt_016b.hex(),
        ),
        fx3_cp_opcodes_verified=tuple(f"0x{op:04x}" for op in FX3_SUPPORTED_0X92840747_DEVELOP_OPCODES),
    )


# ---------------------------------------------------------------------------
# Cine EI / 33^3 3D LUT DMA (`0x0165`/`0x0166`) + Dual Base ISO State Machine
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LutStageSnapshot:
    state: str
    lut_path: str
    lut_payload_bytes: int
    mpr_descriptor_bytes: int
    dma_packet_0165_hex: str
    toggle_packet_0166_hex: str
    uses_dma_dram_path: bool
    base_iso: int
    ei_index: int
    high_gain_mode: int
    liroseq_params: Dict[str, int]


def build_mpr_set_lut_descriptor(
    *,
    enable: bool,
    cube_path: str,
    lut_payload_bytes: int,
    base_iso: int = 800,
    ei_index: int = 800,
    category: int = 3,
    look_slot: int = 1,
) -> bytes:
    """Build deterministic 164-byte `mpr::SetLutData` staging descriptor matching `libmpr.so` offsets."""
    if base_iso not in DUAL_NATIVE_ISO_BASES:
        raise Phase21ProtocolError(
            f"Invalid Dual Native ISO base {base_iso}; expected one of {DUAL_NATIVE_ISO_BASES}"
        )
    encoded_path = cube_path.encode("latin1", errors="strict")
    if len(encoded_path) >= 64:
        raise Phase21ProtocolError(f"LUT .cube path must be < 64 bytes, got {len(encoded_path)}")
    if enable and not encoded_path:
        raise Phase21ProtocolError("Enabled 3D LUT requires a non-empty .cube path")
    if enable and lut_payload_bytes not in (
        LUT_8BIT_RAW_BYTES,
        LUT_8BIT_ALIGNED_BYTES,
        LUT_16BIT_BYTES,
    ):
        raise Phase21ProtocolError(
            f"Unsupported 33^3 3D LUT byte length {lut_payload_bytes}; expected "
            f"{LUT_8BIT_RAW_BYTES}/{LUT_8BIT_ALIGNED_BYTES}/{LUT_16BIT_BYTES}"
        )

    buf = bytearray(MPR_SET_LUT_DESCRIPTOR_BYTES)
    # `+0x04`: enable byte; `+0x05..+0x1e`: 26B LUT metadata; `+0x1f..+0x5e`: 64B NUL-terminated path
    struct.pack_into("<I", buf, 0x00, MPR_SET_LUT_DESCRIPTOR_BYTES)
    struct.pack_into("<B", buf, 0x04, 1 if enable else 0)
    struct.pack_into(
        "<BBHIIIIII",
        buf,
        0x05,
        category & 0xFF,
        look_slot & 0xFF,
        LUT_GRID_SIZE,
        lut_payload_bytes,
        base_iso,
        ei_index,
        LUT_VOXEL_COUNT,
        LUT_CUBE_ALLOC_BYTES,
        LUT_DMA_SRAM_REG_THRESHOLD,
    )
    buf[0x1F : 0x1F + len(encoded_path)] = encoded_path
    return bytes(buf)


def build_0x0165_lut_dma_packet(
    *,
    category: int,
    look_name: int,
    exist_user_lut: int,
    data_size: int,
    data_offset_sram: int,
    data_size_sram: int,
    data_offset_reg: int,
    data_size_reg: int,
) -> bytes:
    """Build exact 36-byte `0x92840747` `0x0165` (`video_set_lookname_procam`) descriptor."""
    if data_size > LUT_DMA_SRAM_REG_THRESHOLD:
        inline_sz = 0
        sram_off = data_offset_sram
        sram_sz = data_size_sram if data_size_sram > 0 else data_size
        reg_off = data_offset_reg
        reg_sz = data_size_reg
    else:
        inline_sz = data_size
        sram_off = 0
        sram_sz = 0
        reg_off = 0
        reg_sz = 0

    return struct.pack(
        "<HHHHBBHIIIIII",
        UIPC_BB_MAGIC,
        UIPC_BB_OPCODE_LUT_DMA,
        LUT_DMA_ENABLE_SIZE,
        UIPC_BB_FLAGS,
        category & 0xFF,
        look_name & 0xFF,
        0,
        exist_user_lut & 0xFFFFFFFF,
        inline_sz & 0xFFFFFFFF,
        sram_off & 0xFFFFFFFF,
        sram_sz & 0xFFFFFFFF,
        reg_off & 0xFFFFFFFF,
        reg_sz & 0xFFFFFFFF,
    )


def build_0x0166_lut_toggle_packet(*, enable: bool) -> bytes:
    """Build exact 10-byte `0x92840747` `0x0166` LUT enable/reset packet matching `0x20f1d60`."""
    # Note: FX6 `0x20f1db0` maps input 0 -> wire byte 1 (enable LUT), non-zero -> 0 (disable).
    wire_val = 1 if enable else 0
    return struct.pack(
        "<HHHHH",
        UIPC_BB_MAGIC,
        UIPC_BB_OPCODE_LUT_TOGGLE,
        LUT_TOGGLE_SIZE,
        UIPC_BB_FLAGS,
        wire_val,
    )


class CineEiLutDmaStateMachine:
    """Deterministic round-trip state machine for Cine EI Dual Base ISO + `33^3` 3D LUT DMA."""

    def __init__(self) -> None:
        self.state: str = "IDLE"
        self.lut_path: str = ""
        self.lut_payload_bytes: int = 0
        self.mpr_descriptor: bytes = b""
        self.dma_packet_0165: bytes = b""
        self.toggle_packet_0166: bytes = b""
        self.base_iso: int = 800
        self.ei_index: int = 800
        self.high_gain_mode: int = 0
        self.uses_dma_dram_path: bool = False

    def stage_cube_lut(
        self,
        cube_path: str,
        lut_payload_bytes: int = LUT_8BIT_ALIGNED_BYTES,
        *,
        base_iso: int = 800,
        ei_index: int = 800,
    ) -> LutStageSnapshot:
        desc = build_mpr_set_lut_descriptor(
            enable=True,
            cube_path=cube_path,
            lut_payload_bytes=lut_payload_bytes,
            base_iso=base_iso,
            ei_index=ei_index,
        )
        self.lut_path = cube_path
        self.lut_payload_bytes = lut_payload_bytes
        self.mpr_descriptor = desc
        self.base_iso = base_iso
        self.ei_index = ei_index
        self.high_gain_mode = 1 if base_iso == 12800 else 0
        self.uses_dma_dram_path = lut_payload_bytes > LUT_DMA_SRAM_REG_THRESHOLD
        self.state = "CUBE_STAGED"
        return self.snapshot()

    def arm_dma_0165(
        self,
        *,
        sram_offset: int = 0x1000,
        reg_offset: int = 0x20000,
        reg_size: int = 0x400,
    ) -> LutStageSnapshot:
        if self.state not in ("CUBE_STAGED", "LOOKNAME_0166_ENABLED", "RESET_DISABLED"):
            raise Phase21ProtocolError(f"Cannot arm 0x0165 DMA from state {self.state}")
        self.dma_packet_0165 = build_0x0165_lut_dma_packet(
            category=3,
            look_name=0,
            exist_user_lut=1,
            data_size=self.lut_payload_bytes,
            data_offset_sram=sram_offset,
            data_size_sram=self.lut_payload_bytes,
            data_offset_reg=reg_offset,
            data_size_reg=reg_size,
        )
        self.state = "DMA_0165_ARMED"
        return self.snapshot()

    def enable_look_0166(self) -> LutStageSnapshot:
        if self.state != "DMA_0165_ARMED":
            raise Phase21ProtocolError(f"Cannot enable 0x0166 LUT from state {self.state}")
        self.toggle_packet_0166 = build_0x0166_lut_toggle_packet(enable=True)
        self.state = "LOOKNAME_0166_ENABLED"
        return self.snapshot()

    def set_cine_ei(self, *, base_iso: int, ei_index: int) -> LutStageSnapshot:
        if base_iso not in DUAL_NATIVE_ISO_BASES:
            raise Phase21ProtocolError(
                f"Dual Native ISO must be in {DUAL_NATIVE_ISO_BASES}, got {base_iso}"
            )
        if ei_index < 200 or ei_index > 102400:
            raise Phase21ProtocolError(f"Cine EI index {ei_index} out of valid range [200..102400]")
        self.base_iso = base_iso
        self.ei_index = ei_index
        self.high_gain_mode = 1 if base_iso == 12800 else 0
        return self.snapshot()

    def disable_look_0166(self) -> LutStageSnapshot:
        self.toggle_packet_0166 = build_0x0166_lut_toggle_packet(enable=False)
        self.mpr_descriptor = build_mpr_set_lut_descriptor(
            enable=False,
            cube_path="",
            lut_payload_bytes=0,
            base_iso=self.base_iso,
            ei_index=self.ei_index,
        )
        self.state = "RESET_DISABLED"
        return self.snapshot()

    def snapshot(self) -> LutStageSnapshot:
        # AP->CP Dual ISO bridge aligns FX6 (`uc_HighGainMode`/`ul_EIGainValue`) with
        # FX3 Stock-CP (`HyperGainMode`/`EIValue`) and shared `baseSensitivity`.
        ei_gain_db_x10 = 0
        if self.ei_index > 0 and self.base_iso > 0:
            import math

            ei_gain_db_x10 = int(round(200.0 * math.log10(self.ei_index / float(self.base_iso))))
        liroseq_params = {
            "baseSensitivity": 1 if self.high_gain_mode else 0,
            "HyperGainMode": self.high_gain_mode,
            "EIValue": self.ei_index,
            "uc_HighGainMode": self.high_gain_mode,
            "ul_EIGainValue": ei_gain_db_x10,
        }
        return LutStageSnapshot(
            state=self.state,
            lut_path=self.lut_path,
            lut_payload_bytes=self.lut_payload_bytes,
            mpr_descriptor_bytes=len(self.mpr_descriptor),
            dma_packet_0165_hex=self.dma_packet_0165.hex(),
            toggle_packet_0166_hex=self.toggle_packet_0166.hex(),
            uses_dma_dram_path=self.uses_dma_dram_path,
            base_iso=self.base_iso,
            ei_index=self.ei_index,
            high_gain_mode=self.high_gain_mode,
            liroseq_params=liroseq_params,
        )


# ---------------------------------------------------------------------------
# FX3 5-Axis IBIS SteadyShot (Off / Standard / Active) Telemetry Bridge Contract
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IbisTelemetryBridgeState:
    requested_mode: str
    effective_cp_mode: str
    is_on_movie: int
    is_mode: int
    is_type: int
    center_lock_energized: bool
    floating_sensor_hazard: bool
    active_electronic_crop_bridged: bool
    servo_restore_source: str
    notes: str


def evaluate_ibis_steadyshot_bridge(
    requested_mode: str,
    *,
    ap_active_extension_enabled: bool = False,
) -> IbisTelemetryBridgeState:
    """Formalize FX3 5-axis IBIS SteadyShot (`Off`/`Standard`/`Active`) telemetry bridge contract."""
    if requested_mode not in VALID_STEADYSHOT_MODES:
        raise Phase21ProtocolError(
            f"Unsupported SteadyShot mode {requested_mode!r}; expected one of {VALID_STEADYSHOT_MODES}"
        )
    servo_src = "LiroSeq: Restore. (p2:/Backup.bin + p2:/psd.bin + p6:Jiritsu)"
    if requested_mode == "Off":
        # FX3 Stock-CP keeps Hall/Gyro PID voice-coil center-lock energized even when IS is Off.
        return IbisTelemetryBridgeState(
            requested_mode="Off",
            effective_cp_mode="CenterLock_Energized_IS_Off",
            is_on_movie=0,
            is_mode=0,
            is_type=0,
            center_lock_energized=True,
            floating_sensor_hazard=False,
            active_electronic_crop_bridged=False,
            servo_restore_source=servo_src,
            notes="FX3 Stock-CP energizes HallPIDOUT/GyroPIDOUT center-lock with IS stabilization disabled.",
        )
    if requested_mode == "Standard":
        return IbisTelemetryBridgeState(
            requested_mode="Standard",
            effective_cp_mode="Standard_5Axis_IBIS",
            is_on_movie=1,
            is_mode=1,
            is_type=1,
            center_lock_energized=True,
            floating_sensor_hazard=False,
            active_electronic_crop_bridged=False,
            servo_restore_source=servo_src,
            notes="Matches FX6 appFw set_tc_on_movie_i/set_tc_mode_i -> FX3 CheckSetTcOnMovie/CheckSetTcMode.",
        )
    # Active mode
    if ap_active_extension_enabled:
        return IbisTelemetryBridgeState(
            requested_mode="Active",
            effective_cp_mode="Active_5Axis_IBIS_Bridged",
            is_on_movie=1,
            is_mode=2,
            is_type=1,
            center_lock_energized=True,
            floating_sensor_hazard=False,
            active_electronic_crop_bridged=True,
            servo_restore_source=servo_src,
            notes="Bridged onto FX3 CheckSetSteadyShotAdvancedMovie / steadyshot_body_axis_movie.",
        )
    return IbisTelemetryBridgeState(
        requested_mode="Active",
        effective_cp_mode="Standard_5Axis_CenterLock_Fallback",
        is_on_movie=1,
        is_mode=1,
        is_type=1,
        center_lock_energized=True,
        floating_sensor_hazard=False,
        active_electronic_crop_bridged=False,
        servo_restore_source=servo_src,
        notes="FX6 AP omits set_steadyshot_advanced_movie_i; Stock-CP maintains Standard energized 5-axis IBIS.",
    )


# ---------------------------------------------------------------------------
# Executable AP-Side `P11` UIPC Shim Runtime Dispatcher
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ShimDispatchReceipt:
    destination_queue: str
    intercepted_by_shim: bool
    request_bytes: int
    reply_bytes: int
    reply_hex: str
    raw_status: int
    action: str


class UipcCpShimRuntime:
    """Executable AP-side `P11` UIPC message synthesizer for FX6 AP <-> FX3 7.02 Stock-CP."""

    def __init__(
        self,
        *,
        rtc_time: Optional[LinuxRtcTime] = None,
        smart_handle_attached: bool = False,
    ) -> None:
        self.rtc_time: LinuxRtcTime = rtc_time or LinuxRtcTime(
            tm_sec=45,
            tm_min=30,
            tm_hour=11,
            tm_mday=14,
            tm_mon=10,  # November (0-based)
            tm_year=126,  # 2026 (1900 + 126)
            tm_wday=6,
            tm_yday=317,
            tm_isdst=0,
        )
        self.smart_handle_attached: bool = smart_handle_attached
        self.xlr_h1_audio_preserved: bool = True
        self.dispatch_counts: Dict[str, int] = {
            f"0x{RTC_QUEUE_ID:08x}": 0,
            f"0x{HANDLE_QUEUE_ID:08x}": 0,
            f"0x{UIPC_BB_TARGET_QUEUE:08x}": 0,
        }
        self.last_handle_event_id: int = HANDLE_EVENT_DETACHED_ID
        self.last_udate: Optional[UdateNotificationStruct] = None

    def dispatch(self, destination_queue: int, request_bytes: bytes) -> ShimDispatchReceipt:
        if destination_queue == RTC_QUEUE_ID:
            reply, udate = translate_rtc0_to_0x92d2091c_reply(request_bytes, self.rtc_time)
            self.last_udate = udate
            q_hex = f"0x{RTC_QUEUE_ID:08x}"
            self.dispatch_counts[q_hex] += 1
            return ShimDispatchReceipt(
                destination_queue=q_hex,
                intercepted_by_shim=True,
                request_bytes=len(request_bytes),
                reply_bytes=len(reply),
                reply_hex=reply.hex(),
                raw_status=reply[1],
                action="synthesized_rtc0_to_0x92d2091c_reply",
            )

        if destination_queue == HANDLE_QUEUE_ID:
            sync_ack, _async_evt, evt_id = synthesize_smart_handle_ack(
                request_bytes, grip_attached=self.smart_handle_attached
            )
            self.last_handle_event_id = evt_id
            q_hex = f"0x{HANDLE_QUEUE_ID:08x}"
            self.dispatch_counts[q_hex] += 1
            return ShimDispatchReceipt(
                destination_queue=q_hex,
                intercepted_by_shim=True,
                request_bytes=len(request_bytes),
                reply_bytes=len(sync_ack),
                reply_hex=sync_ack.hex(),
                raw_status=0,
                action="synthesized_smart_handle_detached_ack",
            )

        if destination_queue == UIPC_BB_TARGET_QUEUE:
            if len(request_bytes) < 8:
                raise Phase21ProtocolError(
                    f"UIPC BB 0x{UIPC_BB_TARGET_QUEUE:08x} packet < 8B: {len(request_bytes)}B"
                )
            magic, opcode, decl_len, flags = struct.unpack_from("<HHHH", request_bytes, 0)
            if magic != UIPC_BB_MAGIC or flags != UIPC_BB_FLAGS or decl_len != len(request_bytes):
                raise Phase21ProtocolError(
                    f"Malformed UIPC BB header magic=0x{magic:04x} len={decl_len}/{len(request_bytes)} flags=0x{flags:04x}"
                )
            if opcode == UIPC_BB_OPCODE_LUT_DMA and len(request_bytes) != LUT_DMA_ENABLE_SIZE:
                raise Phase21ProtocolError(
                    f"0x0165 LUT DMA expects {LUT_DMA_ENABLE_SIZE}B, got {len(request_bytes)}B"
                )
            if opcode == UIPC_BB_OPCODE_LUT_TOGGLE and len(request_bytes) != LUT_TOGGLE_SIZE:
                raise Phase21ProtocolError(
                    f"0x0166 LUT toggle expects {LUT_TOGGLE_SIZE}B, got {len(request_bytes)}B"
                )
            raw_status = 0x00580000 if opcode == UIPC_BB_OPCODE_P5_AUDIO_HDMI else 0x00000000
            reply = struct.pack(
                "<HHHHI",
                UIPC_BB_MAGIC,
                opcode | UIPC_BB_COMPLETION_MASK,
                UIPC_BB_COMPLETION_BYTES,
                UIPC_BB_FLAGS,
                raw_status,
            )
            q_hex = f"0x{UIPC_BB_TARGET_QUEUE:08x}"
            self.dispatch_counts[q_hex] += 1
            passthrough = opcode in (
                UIPC_BB_OPCODE_LUT_DMA,
                UIPC_BB_OPCODE_LUT_TOGGLE,
                UIPC_BB_OPCODE_VIDEO_MODE_PROCAM,
                UIPC_BB_OPCODE_DEVELOP_A,
                UIPC_BB_OPCODE_DEVELOP_B,
            )
            return ShimDispatchReceipt(
                destination_queue=q_hex,
                intercepted_by_shim=not passthrough,
                request_bytes=len(request_bytes),
                reply_bytes=len(reply),
                reply_hex=reply.hex(),
                raw_status=raw_status,
                action="stock_cp_passthrough_verified" if passthrough else "uipc_bb_completion_synth",
            )

        raise Phase21ProtocolError(f"Unsupported Phase 21 queue 0x{destination_queue:08x}")


# ---------------------------------------------------------------------------
# Binary Scanners & Clean-Room Synthetic ELF64/ARM64/Thumb-2 Fixtures
# ---------------------------------------------------------------------------


def _scan_cp_0x9xxx_movwt(cp_bytes: bytes) -> Set[int]:
    mv = memoryview(cp_bytes)
    n = len(cp_bytes)
    recent: Dict[int, Tuple[int, int]] = {}
    found: Set[int] = set()
    for i in range(0, n - 4, 2):
        hw1 = struct.unpack_from("<H", mv, i)[0]
        if (hw1 & 0xFBF0) == 0xF240:
            hw2 = struct.unpack_from("<H", mv, i + 2)[0]
            if (hw2 & 0x8000) == 0:
                rd = (hw2 >> 8) & 0xF
                imm16 = (
                    ((hw1 & 0xF) << 12)
                    | (((hw1 >> 10) & 1) << 11)
                    | (((hw2 >> 12) & 7) << 8)
                    | (hw2 & 0xFF)
                )
                recent[rd] = (i, imm16)
        elif (hw1 & 0xFBF0) == 0xF2C0:
            hw2 = struct.unpack_from("<H", mv, i + 2)[0]
            if (hw2 & 0x8000) == 0:
                rd = (hw2 >> 8) & 0xF
                prev = recent.get(rd)
                if prev is not None and (i - prev[0]) <= 24:
                    imm16_hi = (
                        ((hw1 & 0xF) << 12)
                        | (((hw1 >> 10) & 1) << 11)
                        | (((hw2 >> 12) & 7) << 8)
                        | (hw2 & 0xFF)
                    )
                    val = (imm16_hi << 16) | prev[1]
                    if 0x90000000 <= val <= 0x9FFFFFFF:
                        found.add(val)
    return found


def _scan_cp_uipc_completion_opcodes(cp_bytes: bytes, opcodes: Iterable[int]) -> Set[int]:
    target_set = {op | UIPC_BB_COMPLETION_MASK for op in opcodes}
    found: Set[int] = set()
    mv = memoryview(cp_bytes)
    n = len(cp_bytes)
    for i in range(0, n - 4, 2):
        hw1 = struct.unpack_from("<H", mv, i)[0]
        if (hw1 & 0xFBF0) == 0xF240:
            hw2 = struct.unpack_from("<H", mv, i + 2)[0]
            if (hw2 & 0x8000) == 0:
                imm16 = (
                    ((hw1 & 0xF) << 12)
                    | (((hw1 >> 10) & 1) << 11)
                    | (((hw2 >> 12) & 7) << 8)
                    | (hw2 & 0xFF)
                )
                if imm16 in target_set:
                    found.add(imm16 ^ UIPC_BB_COMPLETION_MASK)
    return found


def _scan_aarch64_0x9xxx_movzk(elf_bytes: bytes) -> Set[int]:
    insns = memoryview(elf_bytes)
    recent: Dict[int, Tuple[int, int]] = {}
    found: Set[int] = set()
    for off in range(0, len(elf_bytes) - 4, 4):
        w = struct.unpack_from("<I", insns, off)[0]
        if (w & 0x7FE00000) == 0x52800000:
            recent[w & 0x1F] = (off, (w >> 5) & 0xFFFF)
        elif (w & 0x7FE00000) == 0x72A00000:
            rd = w & 0x1F
            prev = recent.get(rd)
            if prev is not None and (off - prev[0]) <= 24:
                val = (((w >> 5) & 0xFFFF) << 16) | prev[1]
                if 0x90000000 <= val <= 0x9FFFFFFF:
                    found.add(val)
    return found


def _encode_thumb2_movwt(rd: int, val: int) -> bytes:
    lo = val & 0xFFFF
    hi = (val >> 16) & 0xFFFF

    def _enc(opcode: int, imm16: int) -> Tuple[int, int]:
        i = (imm16 >> 11) & 1
        imm4 = (imm16 >> 12) & 0xF
        imm3 = (imm16 >> 8) & 0x7
        imm8 = imm16 & 0xFF
        return opcode | (i << 10) | imm4, (imm3 << 12) | ((rd & 0xF) << 8) | imm8

    w1, w2 = _enc(0xF240, lo)
    t1, t2 = _enc(0xF2C0, hi)
    return struct.pack("<HHHH", w1, w2, t1, t2)


def _encode_thumb2_movw(rd: int, imm16: int) -> bytes:
    i = (imm16 >> 11) & 1
    imm4 = (imm16 >> 12) & 0xF
    imm3 = (imm16 >> 8) & 0x7
    imm8 = imm16 & 0xFF
    return struct.pack("<HH", 0xF240 | (i << 10) | imm4, (imm3 << 12) | ((rd & 0xF) << 8) | imm8)


def _encode_aarch64_movzk(rd: int, val: int) -> bytes:
    lo = val & 0xFFFF
    hi = (val >> 16) & 0xFFFF
    return struct.pack("<II", 0x52800000 | (lo << 5) | (rd & 0x1F), 0x72A00000 | (hi << 5) | (rd & 0x1F))


def _encode_aarch64_movzk_64(rd: int, val: int) -> bytes:
    lo = val & 0xFFFF
    hi = (val >> 16) & 0xFFFF
    return struct.pack("<II", 0xD2800000 | (lo << 5) | (rd & 0x1F), 0xF2A00000 | (hi << 5) | (rd & 0x1F))


def _encode_aarch64_bl(src_vma: int, dst_vma: int) -> int:
    return 0x94000000 | (((dst_vma - src_vma) >> 2) & 0x03FFFFFF)


def _encode_aarch64_b(src_vma: int, dst_vma: int) -> int:
    return 0x14000000 | (((dst_vma - src_vma) >> 2) & 0x03FFFFFF)


def _encode_aarch64_cbnz(rt: int, src_vma: int, dst_vma: int) -> int:
    return 0x35000000 | ((((dst_vma - src_vma) >> 2) & 0x7FFFF) << 5) | (rt & 0x1F)


def _encode_aarch64_cbz(rt: int, src_vma: int, dst_vma: int) -> int:
    return 0x34000000 | ((((dst_vma - src_vma) >> 2) & 0x7FFFF) << 5) | (rt & 0x1F)


def _build_minimal_elf64(
    text_vma: int,
    code_chunks: Mapping[int, bytes],
    *,
    rodata_vma: int = 0x12000,
    rodata_bytes: bytes = b"synthetic-rodata\x00",
    total_size: int = 0x20000,
) -> bytes:
    buf = bytearray(total_size)
    shstr_bytes = b"\x00.text\x00.rodata\x00.data\x00.shstrtab\x00"
    shstr_off = 0x1000
    data_off = 0x18000
    shoff = 0x1A000
    buf[shstr_off : shstr_off + len(shstr_bytes)] = shstr_bytes
    buf[rodata_vma : rodata_vma + len(rodata_bytes)] = rodata_bytes
    for vma, data in code_chunks.items():
        buf[vma : vma + len(data)] = data
    e_ident = b"\x7fELF\x02\x01\x01" + b"\x00" * 9
    struct.pack_into("<16sHHIQQQIHHHHHH", buf, 0, e_ident, 3, 183, 1, text_vma, 64, shoff, 0, 64, 56, 2, 64, 5, 4)
    struct.pack_into("<IIQQQQQQ", buf, 64, 1, 5, 0, 0, 0, data_off, data_off, 0x1000)
    struct.pack_into("<IIQQQQQQ", buf, 120, 1, 6, data_off, data_off, data_off, 0x1000, 0x1000, 0x1000)
    return bytes(buf)


def build_clean_room_phase21_fixtures(
    *,
    inject_blocking_queue_into_fx3_cp: bool = False,
    drop_develop_opcode: Optional[int] = None,
    strip_fx3_ibis_markers: bool = False,
    corrupt_cube_alloc_bytes: bool = False,
) -> Dict[str, bytes]:
    """Generate clean-room synthetic ELF64+ARM64+Thumb-2 fixtures matching live donor contracts."""
    # 1. FX3 & FX6 cpapp-b.bin
    fx3_cp = bytearray(b"LDR\x00" + b"\x00" * 0x80)
    fx3_cp.extend(_encode_thumb2_movwt(0, UIPC_BB_TARGET_QUEUE))
    if inject_blocking_queue_into_fx3_cp:
        fx3_cp.extend(_encode_thumb2_movwt(0, RTC_QUEUE_ID))
    for op in FX3_SUPPORTED_0X92840747_DEVELOP_OPCODES:
        if drop_develop_opcode is not None and op == drop_develop_opcode:
            continue
        fx3_cp.extend(_encode_thumb2_movw(1, op | UIPC_BB_COMPLETION_MASK))
    fx3_strs = list(REQUIRED_FX3_DEVELOP_MARKERS) + ["DCI4K", "QFHD", "is_mode", "is_on_movie", "is_type"]
    if not strip_fx3_ibis_markers:
        fx3_strs.extend(REQUIRED_FX3_IBIS_MARKERS)
    fx3_cp.extend(b"\x00".join(s.encode("latin1") for s in fx3_strs) + b"\x00")

    fx6_cp = bytearray(b"LDR\x00" + b"\x00" * 0x80)
    for q in (UIPC_BB_TARGET_QUEUE, RTC_QUEUE_ID, HANDLE_QUEUE_ID):
        fx6_cp.extend(_encode_thumb2_movwt(0, q))
    for op in FX3_SUPPORTED_0X92840747_DEVELOP_OPCODES:
        fx6_cp.extend(_encode_thumb2_movw(1, op | UIPC_BB_COMPLETION_MASK))
    fx6_cp.extend(
        b"\x00".join(
            s.encode("latin1")
            for s in (
                "developing_mode_FHD",
                "CheckSetDevelopingMode",
                "uc_HighGainMode",
                "ul_EIGainValue",
                "is_mode",
                "is_on_movie",
                "is_type",
            )
        )
        + b"\x00"
    )

    # 2. Synthetic FX6 appFw.so with Unicorn-runnable Queue 1, Queue 2, 0x0165/0x0166 LUT DMA, and IBIS TC mappers
    chunks: Dict[int, bytes] = {}
    chunks[0x4000] = _encode_aarch64_movzk(0, RTC_QUEUE_ID) + _encode_aarch64_movzk(0, HANDLE_QUEUE_ID) + _encode_aarch64_movzk(0, UIPC_BB_TARGET_QUEUE)

    send_sync_plt = 0x8000
    future_wait_plt = 0x8010
    get_src_plt = 0x8020
    promise_set_plt = 0x8030
    free_msg_plt = 0x8040
    ev_alloc_plt = 0x8050
    ev_post_plt = 0x8060
    reg_cb_plt = 0x8070
    unreg_cb_plt = 0x8080
    assert_plt = 0x8090
    send_wait_plt = 0x80A0

    for stub in (
        send_sync_plt, future_wait_plt, get_src_plt, promise_set_plt, free_msg_plt,
        ev_alloc_plt, ev_post_plt, reg_cb_plt, unreg_cb_plt, assert_plt, send_wait_plt,
    ):
        chunks[stub] = struct.pack("<I", 0xD65F03C0)

    # Queue 1: get_rtc_status @ 0x7000
    rtc_get_vma = 0x7000
    rtc_get = bytearray()
    for insn in (
        0xA9BE7BFD,  # stp x29, x30, [sp, #-0x20]!
        0x910003FD,  # mov x29, sp
        0x52800060,  # mov w0, #3
        0x390063A0,  # strb w0, [x29, #0x18]
        0x390067BF,  # strb wzr, [x29, #0x19]
        0x910063A0,  # add x0, x29, #0x18
        0xD2800041,  # mov x1, #2
        0x52812382,  # movz w2, #0x091c
        0x72B25A42,  # movk w2, #0x92d2, lsl #16
        _encode_aarch64_bl(rtc_get_vma + 9 * 4, send_sync_plt),
        _encode_aarch64_bl(rtc_get_vma + 10 * 4, future_wait_plt),
        0xA8C27BFD,  # ldp x29, x30, [sp], #0x20
        0xD65F03C0,  # ret
    ):
        rtc_get.extend(struct.pack("<I", insn))
    chunks[rtc_get_vma] = bytes(rtc_get)

    # Queue 1: reply callback @ 0x7100: checks msg_src == 0x92d2091c, calls promise_set_plt(msg[1]==0), then free_msg_plt(0x81d705bd, msg)
    rtc_cb_vma = 0x7100
    rtc_cb = bytearray()
    for insn in (
        0xA9BE7BFD,  # 0x00: stp x29, x30, [sp, #-0x20]!
        0x910003FD,  # 0x04: mov x29, sp
        0xF9000BF3,  # 0x08: str x19, [sp, #0x10]
        0xAA0003F3,  # 0x0c: mov x19, x0
        _encode_aarch64_bl(rtc_cb_vma + 0x10, get_src_plt),        # 0x10
        0x52812381,  # 0x14: movz w1, #0x091c
        0x72B25A41,  # 0x18: movk w1, #0x92d2, lsl #16
        0x6B01001F,  # 0x1c: cmp w0, w1
        0x540000E1,  # 0x20: b.ne 0x3c (skip promise_set)
        0x39400660,  # 0x24: ldrb w0, [x19, #1]
        0x7100001F,  # 0x28: cmp w0, #0
        0x1A9F17E0,  # 0x2c: cset w0, eq
        0x39007FA0,  # 0x30: strb w0, [x29, #0x1f]
        0x91007FA1,  # 0x34: add x1, x29, #0x1f
        _encode_aarch64_bl(rtc_cb_vma + 0x38, promise_set_plt),    # 0x38
        0x5280B7A0,  # 0x3c: movz w0, #0x05bd
        0x72B03AE0,  # 0x40: movk w0, #0x81d7, lsl #16
        0xAA1303E1,  # 0x44: mov x1, x19
        _encode_aarch64_bl(rtc_cb_vma + 0x48, free_msg_plt),       # 0x48
        0xF9400BF3,  # 0x4c: ldr x19, [sp, #0x10]
        0xA8C27BFD,  # 0x50: ldp x29, x30, [sp], #0x20
        0xD65F03C0,  # 0x54: ret
    ):
        rtc_cb.extend(struct.pack("<I", insn))
    chunks[rtc_cb_vma] = bytes(rtc_cb)

    # Queue 2: register_callback @ 0x7200: posts 551, calls reg_cb_plt, sends 12B <III(0x81000001, 0, cb_qid) to 0x91db059b; if rc!=0 calls assert_plt(w1=123)
    h_reg_vma = 0x7200
    h_reg = bytearray()
    for insn in (
        0xA9BD7BFD,  # 0x00: stp x29, x30, [sp, #-0x30]!
        0x910003FD,  # 0x04: mov x29, sp
        0xD2800080,  # 0x08: mov x0, #4
        _encode_aarch64_bl(h_reg_vma + 0x0C, ev_alloc_plt),        # 0x0c
        0x528044E1,  # 0x10: mov w1, #551 (0x227)
        0xB9000001,  # 0x14: str w1, [x0]
        _encode_aarch64_bl(h_reg_vma + 0x18, ev_post_plt),         # 0x18
        0x5280A020,  # 0x1c: movz w0, #0x0501
        0x72B03980,  # 0x20: movk w0, #0x81cc, lsl #16
        _encode_aarch64_bl(h_reg_vma + 0x24, reg_cb_plt),          # 0x24
        0x52800020,  # 0x28: movz w0, #1
        0x72B02000,  # 0x2c: movk w0, #0x8100, lsl #16
        0xF90013BF,  # 0x30: str xzr, [x29, #0x20]
        0xB90023A0,  # 0x34: str w0, [x29, #0x20]
        0x5280A023,  # 0x38: movz w3, #0x0501
        0x72B03983,  # 0x3c: movk w3, #0x81cc, lsl #16
        0xB9002BA3,  # 0x40: str w3, [x29, #0x28]
        0x910083A0,  # 0x44: add x0, x29, #0x20
        0xD2800181,  # 0x48: mov x1, #12
        0x5280B362,  # 0x4c: movz w2, #0x059b
        0x72B23B62,  # 0x50: movk w2, #0x91db, lsl #16
        _encode_aarch64_bl(h_reg_vma + 0x54, send_sync_plt),       # 0x54
        _encode_aarch64_cbz(0, h_reg_vma + 0x58, h_reg_vma + 0x64),# 0x58
        0x52800F61,  # 0x5c: mov w1, #123 (0x7b)
        _encode_aarch64_bl(h_reg_vma + 0x60, assert_plt),          # 0x60
        0xA8C37BFD,  # 0x64: ldp x29, x30, [sp], #0x30
        0xD65F03C0,  # 0x68: ret
    ):
        h_reg.extend(struct.pack("<I", insn))
    chunks[h_reg_vma] = bytes(h_reg)

    # Queue 2: callback @ 0x7300: decodes 0x88000001 -> 550, 0x88000002 -> 551, frees msg
    h_cb_vma = 0x7300
    h_cb = bytearray()
    for insn in (
        0xA9BE7BFD,  # 0x00: stp x29, x30, [sp, #-0x20]!
        0x910003FD,  # 0x04: mov x29, sp
        0xF9000BF3,  # 0x08: str x19, [sp, #0x10]
        0xAA0003F3,  # 0x0c: mov x19, x0
        0xB9400004,  # 0x10: ldr w4, [x0]
        0x52800021,  # 0x14: movz w1, #1
        0x72B10001,  # 0x18: movk w1, #0x8800, lsl #16
        0x6B01009F,  # 0x1c: cmp w4, w1
        0x54000140,  # 0x20: b.eq 0x48 (attached 550)
        0x11000421,  # 0x24: add w1, w1, #1 (0x88000002)
        0x6B01009F,  # 0x28: cmp w4, w1
        0x54000180,  # 0x2c: b.eq 0x58 (detached 551)
        # free_msg @ 0x30
        0x5280A020,  # 0x30: movz w0, #0x0501
        0x72B03980,  # 0x34: movk w0, #0x81cc, lsl #16
        0xAA1303E1,  # 0x38: mov x1, x19
        _encode_aarch64_bl(h_cb_vma + 0x3C, free_msg_plt),         # 0x3c
        0xF9400BF3,  # 0x40: ldr x19, [sp, #0x10]
        0xA8C27BFD,  # 0x44: ldp x29, x30, [sp], #0x20; wait - ret next
        0xD65F03C0,  # 0x48: ret (offset adjust below!)
    ):
        h_cb.extend(struct.pack("<I", insn))
    # Let's rebuild h_cb cleanly with exact branch offsets
    h_cb = bytearray()
    h_cb_insns = [
        0xA9BE7BFD,  # 0x00: stp x29, x30, [sp, #-0x20]!
        0x910003FD,  # 0x04: mov x29, sp
        0xF9000BF3,  # 0x08: str x19, [sp, #0x10]
        0xAA0003F3,  # 0x0c: mov x19, x0
        0xB9400004,  # 0x10: ldr w4, [x0]
        0x52800021,  # 0x14: movz w1, #1
        0x72B10001,  # 0x18: movk w1, #0x8800, lsl #16
        0x6B01009F,  # 0x1c: cmp w4, w1
        0x54000140,  # 0x20: b.eq -> 0x48 (attached 550)
        0x11000421,  # 0x24: add w1, w1, #1
        0x6B01009F,  # 0x28: cmp w4, w1
        0x540001A0,  # 0x2c: b.eq -> 0x60 (detached 551)
        0x5280A020,  # 0x30: movz w0, #0x0501
        0x72B03980,  # 0x34: movk w0, #0x81cc, lsl #16
        0xAA1303E1,  # 0x38: mov x1, x19
        _encode_aarch64_bl(h_cb_vma + 0x3C, free_msg_plt),         # 0x3c
        0xF9400BF3,  # 0x40: ldr x19, [sp, #0x10]
        0xA8C27BFD,  # 0x44: ldp x29, x30, [sp], #0x20
        0xD65F03C0,  # 0x48 -> wait: 0x48 is slot 18! Let's shift branch targets!
    ]
    # Recompute exact targets:
    # 0x00..0x2c = 12 insns; free_msg block at 0x30 (7 insns: 0x30..0x48); attached at 0x4c (5 insns); detached at 0x60 (5 insns)
    h_cb_insns = [
        0xA9BE7BFD,  # 0x00
        0x910003FD,  # 0x04
        0xF9000BF3,  # 0x08
        0xAA0003F3,  # 0x0c
        0xB9400004,  # 0x10
        0x52800021,  # 0x14
        0x72B10001,  # 0x18
        0x6B01009F,  # 0x1c
        0x54000160,  # 0x20: b.eq +0x2c -> 0x4c (attached)
        0x11000421,  # 0x24
        0x6B01009F,  # 0x28
        0x540001C0,  # 0x2c: b.eq +0x38 -> 0x64 (detached)
        # 0x30: free & return
        0x5280A020,  # 0x30
        0x72B03980,  # 0x34
        0xAA1303E1,  # 0x38
        _encode_aarch64_bl(h_cb_vma + 0x3C, free_msg_plt),         # 0x3c
        0xF9400BF3,  # 0x40
        0xA8C27BFD,  # 0x44
        0xD65F03C0,  # 0x48
        # 0x4c: attached 550
        0xD2800080,  # 0x4c
        _encode_aarch64_bl(h_cb_vma + 0x50, ev_alloc_plt),         # 0x50
        0x528044C1,  # 0x54: mov w1, #550
        0xB9000001,  # 0x58
        _encode_aarch64_bl(h_cb_vma + 0x5C, ev_post_plt),          # 0x5c
        _encode_aarch64_b(h_cb_vma + 0x60, h_cb_vma + 0x30),       # 0x60 -> free
        # 0x64: detached 551
        0xD2800080,  # 0x64
        _encode_aarch64_bl(h_cb_vma + 0x68, ev_alloc_plt),         # 0x68
        0x528044E1,  # 0x6c: mov w1, #551
        0xB9000001,  # 0x70
        _encode_aarch64_bl(h_cb_vma + 0x74, ev_post_plt),          # 0x74
        _encode_aarch64_b(h_cb_vma + 0x78, h_cb_vma + 0x30),       # 0x78 -> free
    ]
    for insn in h_cb_insns:
        h_cb.extend(struct.pack("<I", insn))
    chunks[h_cb_vma] = bytes(h_cb)

    # Queue 2: unregister @ 0x7400
    h_unreg_vma = 0x7400
    h_unreg = bytearray()
    for insn in (
        0xA9BD7BFD,  # 0x00
        0x910003FD,  # 0x04
        0x52800040,  # 0x08: movz w0, #2
        0x72B02000,  # 0x0c: movk w0, #0x8100, lsl #16
        0xF90013BF,  # 0x10
        0xB90023A0,  # 0x14
        0x5280A023,  # 0x18
        0x72B03983,  # 0x1c
        0xB9002BA3,  # 0x20
        0x910083A0,  # 0x24
        0xD2800181,  # 0x28
        0x5280B362,  # 0x2c
        0x72B23B62,  # 0x30
        _encode_aarch64_bl(h_unreg_vma + 0x34, send_sync_plt),     # 0x34
        _encode_aarch64_cbz(0, h_unreg_vma + 0x38, h_unreg_vma + 0x44),  # 0x38
        0x528011A1,  # 0x3c: mov w1, #141 (0x8d)
        _encode_aarch64_bl(h_unreg_vma + 0x40, assert_plt),        # 0x40
        0x5280A020,  # 0x44
        0x72B03980,  # 0x48
        _encode_aarch64_bl(h_unreg_vma + 0x4C, unreg_cb_plt),      # 0x4c
        0xA8C37BFD,  # 0x50
        0xD65F03C0,  # 0x54
    ):
        h_unreg.extend(struct.pack("<I", insn))
    chunks[h_unreg_vma] = bytes(h_unreg)

    # Lookname 0x0165 (36B DMA > 0xbb80) @ 0x7500 & 0x0166 (10B toggle) @ 0x7600
    look65_vma = 0x7500
    look65 = bytearray()
    for insn in (
        0xA9BA7BFD,  # stp x29, x30, [sp, #-0x60]!
        0x910003FD,  # mov x29, sp
        0xF9000BF3,  # str x19, [sp, #0x10]
        0xAA0103F3,  # mov x19, x1
        0xA9037FBF,  # stp xzr, xzr, [x29, #0x38]
        0xA9047FBF,  # stp xzr, xzr, [x29, #0x48]
        0xB9005BBF,  # str wzr, [x29, #0x58]
        0x528401A1,  # mov w1, #0x200d
        0x790073A1,  # strh w1, [x29, #0x38]
        0x52802CA1,  # mov w1, #0x165
        0x790077A1,  # strh w1, [x29, #0x3a]
        0x52800481,  # mov w1, #36
        0x79007BA1,  # strh w1, [x29, #0x3c]
        0x128FFFC1,  # mov w1, #0x8001
        0x79007FA1,  # strh w1, [x29, #0x3e]
        0x52800061,  # mov w1, #3 (user LUT category)
        0x390103A1,  # strb w1, [x29, #0x40]
        0xB9400802,  # ldr w2, [x0, #8] (exist_user_lut)
        0xB90047A2,  # str w2, [x29, #0x44]
        0xB9400C01,  # ldr w1, [x0, #0xc] (data_size)
        0x52977004,  # mov w4, #0xbb80
        0x6B04003F,  # cmp w1, w4
        0x540000C9,  # b.ls +0x18 (inline SRAM)
        0x29420C01,  # ldp w1, w3, [x0, #0x10]
        0x29098FA1,  # stp w1, w3, [x29, #0x4c]
        0x29430001,  # ldp w1, w0, [x0, #0x18]
        0x290A83A1,  # stp w1, w0, [x29, #0x54]
        0x14000002,  # b +8
        0xB9004BA1,  # str w1, [x29, #0x48]
        0x5280E8E0,  # movz w0, #0x0747
        0x72B25080,  # movk w0, #0x9284, lsl #16
        0x9100E3A1,  # add x1, x29, #0x38
        0x52800482,  # mov w2, #36
        0x9100A3A3,  # add x3, x29, #0x28
        0x52800184,  # mov w4, #12
        _encode_aarch64_bl(look65_vma + 35 * 4, send_wait_plt),
        0xB9000260,  # str w0, [x19]
        0xF9400BF3,  # ldr x19, [sp, #0x10]
        0xA8C67BFD,  # ldp x29, x30, [sp], #0x60
        0xD65F03C0,  # ret
    ):
        look65.extend(struct.pack("<I", insn))
    chunks[look65_vma] = bytes(look65)

    look66_vma = 0x7600
    look66 = bytearray()
    for insn in (
        0xA9BC7BFD, 0x910003FD, 0xF9000BF3, 0xAA0103F3,
        0xB9400005, 0x528401A2, 0x790043A2, 0x52802CC2,
        0x790047A2, 0x52800142, 0x79004BA2, 0x128FFFC2,
        0x79004FA2, 0x710000BF, 0x1A9F17E5, 0x790053A5,
        0x5280E8E0, 0x72B25080, 0x910083A1, 0x52800142,
        0x9100C3A3, 0x52800184,
        _encode_aarch64_bl(look66_vma + 22 * 4, send_wait_plt),
        0xB9000260, 0xF9400BF3, 0xA8C47BFD, 0xD65F03C0,
    ):
        look66.extend(struct.pack("<I", insn))
    chunks[look66_vma] = bytes(look66)

    # IBIS set_tc_on_movie_i @ 0x7700: mode in {1,2,3} -> 1, {4,5} -> 0
    tc_on_vma = 0x7700
    tc_on = bytearray()
    for insn in (
        0x71000C1F,  # cmp w0, #3
        0x1A9F87E0,  # cset w0, ls
        0x39000020,  # strb w0, [x1]
        0xD65F03C0,  # ret
    ):
        tc_on.extend(struct.pack("<I", insn))
    chunks[tc_on_vma] = bytes(tc_on)

    appfw_ro = (
        b"infra_wrapper_rtc_procam_chaplin_base.cpp\x00"
        b"infra_wrapper_handle_procam_chaplin_base.cpp\x00"
        b"PRM_is_imager_stabilization_unit_fixed\x00"
        b"PID_SET_DEVELOPING_MODE\x00"
        + XLR_H1_DIGMIC_ON_EVENT.encode("latin1") + b"\x00"
        + XLR_H1_DIGMIC_OFF_EVENT.encode("latin1") + b"\x00"
    )
    fx6_appfw = _build_minimal_elf64(0x4000, chunks, rodata_bytes=appfw_ro)

    # 3. Synthetic libInfraHotshoe.so (WaitRecvCompMsgFromHotshoeRsrc @ 0x5d90)
    hs_rcv_plt = 0x2B30
    hs_free_plt = 0x2ED0
    hs_entry = FX6_HOTSHOE_WAIT_RECV_VMA
    hs_code = bytearray()
    for insn in (
        0xA9BD7BFD, 0x910003FD, 0xF9000BF3,
        0x2A0203F3,  # mov w19, w2 (qid)
        0x9100A3A1,  # add x1, x29, #0x28
        0x2A1303E0,  # mov w0, w19
        0x52803E82,  # mov w2, #500
        _encode_aarch64_bl(hs_entry + 7 * 4, hs_rcv_plt),
        0xF94017A1,  # ldr x1, [x29, #0x28]
        0x2A1303E0,  # mov w0, w19
        _encode_aarch64_bl(hs_entry + 10 * 4, hs_free_plt),
        0x52800000,  # mov w0, #0
        0xF9400BF3, 0xA8C37BFD, 0xD65F03C0,
    ):
        hs_code.extend(struct.pack("<I", insn))
    fx6_hotshoe = _build_minimal_elf64(
        0x2000,
        {
            hs_rcv_plt: struct.pack("<I", 0xD65F03C0),
            hs_free_plt: struct.pack("<I", 0xD65F03C0),
            hs_entry: bytes(hs_code),
        },
        rodata_bytes=b"WaitRecvCompMsgFromHotshoeRsrc\x00",
    )

    # 4. Synthetic libmpr.so (with 0x6a1b9 .cube alloc & SetLutData)
    def _build_mpr(*, is_fx6: bool) -> bytes:
        alloc_sz = 0x10000 if (is_fx6 and corrupt_cube_alloc_bytes) else LUT_CUBE_ALLOC_BYTES
        m_chunks = {
            0x4000: _encode_aarch64_movzk_64(0, alloc_sz) + struct.pack("<I", 0xD65F03C0),
        }
        return _build_minimal_elf64(0x4000, m_chunks, rodata_bytes=b"SetLutData\x00ExecuteSetLutData\x00")

    return {
        "fx3_cpapp": bytes(fx3_cp),
        "fx6_cpapp": bytes(fx6_cp),
        "fx6_appfw": fx6_appfw,
        "fx6_hotshoe": fx6_hotshoe,
        "fx3_libmpr": _build_mpr(is_fx6=False),
        "fx6_libmpr": _build_mpr(is_fx6=True),
    }


# ---------------------------------------------------------------------------
# Unicorn AArch64 Proofs (Real Donor ELFs OR Clean-Room Synthetic ELFs)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Queue1RtcUnicornResult:
    case_name: str
    hang_detected: bool
    completed_normally: bool
    destination_queue: int
    request_hex: str
    reply_hex: str
    promise_bool_value: Optional[int]
    expected_get_rtc_status_rc: int
    free_msg_called: bool
    sp_preserved: bool


@dataclass(frozen=True)
class Queue2HandleUnicornResult:
    case_name: str
    completed_normally: bool
    assert_hit: bool
    assert_line: int
    destination_queue: int
    request_hex: str
    reply_hex: str
    posted_events: Tuple[int, ...]
    free_msg_called: bool
    xlr_h1_hotshoe_rc: int
    sp_preserved: bool


@dataclass(frozen=True)
class ImagingBridgeUnicornResult:
    case_name: str
    destination_queue: int
    packet_hex: str
    packet_bytes: int
    return_code: int
    sp_preserved: bool


def verify_queue1_rtc_unicorn(
    fx6_appfw_bytes: bytes,
    rtc_time: LinuxRtcTime,
    *,
    synthetic_mode: bool,
) -> Tuple[Queue1RtcUnicornResult, ...]:
    """Prove Queue 1 (`0x92d2091c`) hang vs /dev/rtc0->udate wakeup on FX6 `appFw.so`."""
    if synthetic_mode:
        rtc_get_vma = 0x7000
        rtc_cb_vma = 0x7100
        send_sync_vma = 0x8000
        future_wait_vma = 0x8010
        get_src_vma = 0x8020
        promise_set_vma = 0x8030
        free_msg_vma = 0x8040
    else:
        rtc_get_vma = 0x2159CB4  # setup of 2B [0x03, 0x00] -> send_sync_msg -> future::wait
        rtc_cb_vma = FX6_APPFW_RTC_REPLY_CB_VMA
        send_sync_vma = FX6_APPFW_SEND_SYNC_MSG_VMA
        future_wait_vma = FX6_APPFW_FUTURE_WAIT_VMA
        get_src_vma = FX6_APPFW_PLT_OSAL_GET_MSG_SRC
        promise_set_vma = FX6_APPFW_RTC_PROMISE_SET_VMA
        free_msg_vma = FX6_APPFW_PLT_OSAL_FREE_MSG

    def _run(
        case_name: str,
        *,
        entry_mode: str,
        intercept_shim: bool,
        msg_src: int = RTC_QUEUE_ID,
        test_rtc: LinuxRtcTime = rtc_time,
    ) -> Queue1RtcUnicornResult:
        mu = U.Uc(U.UC_ARCH_ARM64, U.UC_MODE_ARM)
        mu.reg_write(A.UC_ARM64_REG_CPACR_EL1, 3 << 20)
        if synthetic_mode:
            mu.mem_map(0x7000, 0x2000, U.UC_PROT_READ | U.UC_PROT_EXEC)
            mu.mem_write(0x7000, fx6_appfw_bytes[0x7000:0x9000])
        else:
            mu.mem_map(0x2159000, 0x4000, U.UC_PROT_READ | U.UC_PROT_EXEC)
            mu.mem_write(0x2159000, fx6_appfw_bytes[0x2159000:0x215D000])
            mu.mem_map(0xB18000, 0x2000, U.UC_PROT_READ | U.UC_PROT_EXEC)
            mu.mem_map(0x1CA0000, 0x1000, U.UC_PROT_READ | U.UC_PROT_EXEC)
            mu.mem_map(0x6082000, 0x1000, U.UC_PROT_READ | U.UC_PROT_WRITE)
            for stub in (send_sync_vma, future_wait_vma, get_src_vma, promise_set_vma, free_msg_vma):
                mu.mem_write(stub, struct.pack("<I", 0xD65F03C0))

        mu.mem_map(0x70000000, 0x10000, U.UC_PROT_READ | U.UC_PROT_WRITE)
        mu.mem_map(0x71000000, 0x4000, U.UC_PROT_READ | U.UC_PROT_WRITE)
        mu.mem_map(0x72000000, 0x1000, U.UC_PROT_READ | U.UC_PROT_EXEC)
        mu.mem_write(0x72000000, struct.pack("<I", 0xD503201F))

        state: Dict[str, object] = {
            "dst_q": 0,
            "req_hex": "",
            "reply_hex": "",
            "hang": False,
            "promise_val": None,
            "freed": False,
        }

        def _hook(uc: U.Uc, addr: int, _sz: int, _ud: object) -> None:
            if addr == send_sync_vma:
                p = uc.reg_read(A.UC_ARM64_REG_X0)
                l = uc.reg_read(A.UC_ARM64_REG_W1)
                q = uc.reg_read(A.UC_ARM64_REG_W2)
                req_b = bytes(uc.mem_read(p, l))
                state["dst_q"] = q
                state["req_hex"] = req_b.hex()
                if intercept_shim:
                    reply_b, _udate = translate_rtc0_to_0x92d2091c_reply(req_b, test_rtc)
                    state["reply_hex"] = reply_b.hex()
                uc.reg_write(A.UC_ARM64_REG_W0, 0)
            elif addr == future_wait_vma:
                if not intercept_shim:
                    state["hang"] = True
                    uc.emu_stop()
            elif addr == get_src_vma:
                uc.reg_write(A.UC_ARM64_REG_W0, msg_src)
            elif addr == promise_set_vma:
                val_ptr = uc.reg_read(A.UC_ARM64_REG_X1)
                state["promise_val"] = bytes(uc.mem_read(val_ptr, 1))[0]
            elif addr == free_msg_vma:
                q_free = uc.reg_read(A.UC_ARM64_REG_W0)
                if q_free == RTC_REPLY_QUEUE_ID:
                    state["freed"] = True
                uc.reg_write(A.UC_ARM64_REG_W0, 0)

        mu.hook_add(U.UC_HOOK_CODE, _hook)
        sp0 = 0x7000E000
        mu.reg_write(A.UC_ARM64_REG_SP, sp0)
        mu.reg_write(A.UC_ARM64_REG_LR, 0x72000000)

        if entry_mode == "get_rtc_status":
            if synthetic_mode:
                mu.emu_start(rtc_get_vma, 0x72000000, count=300)
                cur_sp = mu.reg_read(A.UC_ARM64_REG_SP)
                sp_ok = (cur_sp == sp0 - 0x20) if state["hang"] else (cur_sp == sp0)
            else:
                mu.reg_write(A.UC_ARM64_REG_X29, 0x7000DF00)
                mu.reg_write(A.UC_ARM64_REG_X0, 0x7000DF60)
                mu.emu_start(rtc_get_vma, 0x2159CCC, count=100)
                if not intercept_shim:
                    # Unintercepted path falls through directly to std::future<bool>::wait() @ 0x1ca0878
                    state["hang"] = True
                sp_ok = True
            return Queue1RtcUnicornResult(
                case_name=case_name,
                hang_detected=bool(state["hang"]),
                completed_normally=not bool(state["hang"]),
                destination_queue=int(state["dst_q"]),
                request_hex=str(state["req_hex"]),
                reply_hex=str(state["reply_hex"]),
                promise_bool_value=None,
                expected_get_rtc_status_rc=2 if state["hang"] else 0,
                free_msg_called=bool(state["freed"]),
                sp_preserved=sp_ok,
            )

        # Feed synthesized reply into real FX6 callback `0x2159b4c`
        req_b = bytes((RTC_GET_STATUS_CMD_BYTE, 0x00))
        reply_b, _ = translate_rtc0_to_0x92d2091c_reply(req_b, test_rtc)
        msg_addr = 0x71000200
        mu.mem_write(msg_addr, reply_b)
        mu.reg_write(A.UC_ARM64_REG_X0, msg_addr)
        mu.emu_start(rtc_cb_vma, 0x72000000, count=300)
        p_val = state["promise_val"]
        # `appFw.so::get_rtc_status` @ 0x2159dd0 returns `csinc w0, w0, wzr, ne` -> 0 if true(1), 2 if false(0)
        rc_mapped = 0 if p_val == 1 else 2
        return Queue1RtcUnicornResult(
            case_name=case_name,
            hang_detected=False,
            completed_normally=True,
            destination_queue=RTC_QUEUE_ID,
            request_hex=req_b.hex(),
            reply_hex=reply_b.hex(),
            promise_bool_value=int(p_val) if p_val is not None else None,
            expected_get_rtc_status_rc=rc_mapped,
            free_msg_called=bool(state["freed"]),
            sp_preserved=mu.reg_read(A.UC_ARM64_REG_SP) == sp0,
        )

    unset_rtc = LinuxRtcTime(0, 0, 0, 1, 0, 70)  # 1970-01-01 unset RTC
    return (
        _run("q1_unintercepted_future_wait_hang", entry_mode="get_rtc_status", intercept_shim=False),
        _run("q1_intercepted_send_sync_rtc0", entry_mode="get_rtc_status", intercept_shim=True),
        _run("q1_reply_cb_valid_rtc0_unblocks", entry_mode="reply_cb", intercept_shim=True, msg_src=RTC_QUEUE_ID, test_rtc=rtc_time),
        _run("q1_reply_cb_unset_rtc0_false", entry_mode="reply_cb", intercept_shim=True, msg_src=RTC_QUEUE_ID, test_rtc=unset_rtc),
        _run("q1_reply_cb_wrong_src_ignored", entry_mode="reply_cb", intercept_shim=True, msg_src=0x905A0048, test_rtc=rtc_time),
    )


def verify_queue2_handle_and_hotshoe_unicorn(
    fx6_appfw_bytes: bytes,
    fx6_hotshoe_bytes: bytes,
    *,
    synthetic_mode: bool,
) -> Tuple[Queue2HandleUnicornResult, ...]:
    """Prove Queue 2 (`0x91db059b`) detached-grip ACK + XLR-H1 `libInfraHotshoe.so` coexistence."""
    if synthetic_mode:
        h_reg_vma = 0x7200
        h_cb_vma = 0x7300
        h_unreg_vma = 0x7400
        send_sync_vma = 0x8000
        free_msg_vma = 0x8040
        ev_alloc_vma = 0x8050
        ev_post_vma = 0x8060
        reg_cb_vma = 0x8070
        unreg_cb_vma = 0x8080
        assert_vma = 0x8090
    else:
        h_reg_vma = FX6_APPFW_HANDLE_REG_VMA
        h_cb_vma = FX6_APPFW_HANDLE_CB_VMA
        h_unreg_vma = FX6_APPFW_HANDLE_UNREG_VMA
        send_sync_vma = FX6_APPFW_SEND_SYNC_MSG_VMA
        free_msg_vma = FX6_APPFW_PLT_OSAL_FREE_MSG
        ev_alloc_vma = FX6_APPFW_EVENT_ALLOC_VMA
        ev_post_vma = FX6_APPFW_EVENT_POST_VMA
        reg_cb_vma = FX6_APPFW_REG_QUEUE_CB_VMA
        unreg_cb_vma = FX6_APPFW_UNREG_QUEUE_CB_VMA
        assert_vma = FX6_APPFW_ASSERT_VMA

    def _run_xlr_h1_hotshoe() -> int:
        mu = U.Uc(U.UC_ARCH_ARM64, U.UC_MODE_ARM)
        mu.reg_write(A.UC_ARM64_REG_CPACR_EL1, 3 << 20)
        mu.mem_map(0x2000, 0x6000, U.UC_PROT_READ | U.UC_PROT_EXEC)
        mu.mem_write(0x2000, fx6_hotshoe_bytes[0x2000:0x8000])
        if not synthetic_mode:
            mu.mem_map(0x8000, 0x1000, U.UC_PROT_READ)
            mu.mem_write(0x8000, fx6_hotshoe_bytes[0x8000:0x9000])
            for stub in (0x2B30, 0x2B70, 0x2ED0):
                mu.mem_write(stub, struct.pack("<I", 0xD65F03C0))
        mu.mem_map(0x70000000, 0x10000, U.UC_PROT_READ | U.UC_PROT_WRITE)
        mu.mem_map(0x71000000, 0x4000, U.UC_PROT_READ | U.UC_PROT_WRITE)
        mu.mem_map(0x72000000, 0x1000, U.UC_PROT_READ | U.UC_PROT_EXEC)
        mu.mem_write(0x72000000, struct.pack("<I", 0xD503201F))

        def _h_hook(uc: U.Uc, addr: int, _sz: int, _ud: object) -> None:
            if addr == 0x2B30:  # osal_rcv_msg_tmo(qid, &msg, 500)
                ptr_out = uc.reg_read(A.UC_ARM64_REG_X1)
                uc.mem_write(0x71000500, struct.pack("<IIII", 0, 0x1234, 0, 0))
                uc.mem_write(ptr_out, struct.pack("<Q", 0x71000500))
                uc.reg_write(A.UC_ARM64_REG_W0, 0)
            elif addr == 0x2ED0:
                uc.reg_write(A.UC_ARM64_REG_W0, 0)

        mu.hook_add(U.UC_HOOK_CODE, _h_hook)
        mu.reg_write(A.UC_ARM64_REG_SP, 0x7000E000)
        mu.reg_write(A.UC_ARM64_REG_LR, 0x72000000)
        mu.reg_write(A.UC_ARM64_REG_X0, 0x71000000)
        mu.reg_write(A.UC_ARM64_REG_W2, 0x81CC0600)
        mu.reg_write(A.UC_ARM64_REG_W3, 0x1234)
        mu.emu_start(FX6_HOTSHOE_WAIT_RECV_VMA, 0x72000000, count=400)
        return mu.reg_read(A.UC_ARM64_REG_W0)

    def _run_q2(
        case_name: str,
        *,
        action: str,
        snd_rc: int = 0,
        cb_cmd: int = HANDLE_EVT_DETACHED_CMD,
        pre_registered: bool = False,
    ) -> Queue2HandleUnicornResult:
        mu = U.Uc(U.UC_ARCH_ARM64, U.UC_MODE_ARM)
        mu.reg_write(A.UC_ARM64_REG_CPACR_EL1, 3 << 20)
        if synthetic_mode:
            mu.mem_map(0x7000, 0x2000, U.UC_PROT_READ | U.UC_PROT_EXEC)
            mu.mem_write(0x7000, fx6_appfw_bytes[0x7000:0x9000])
        else:
            mu.mem_map(0x2107000, 0x2000, U.UC_PROT_READ | U.UC_PROT_EXEC)
            mu.mem_write(0x2107000, fx6_appfw_bytes[0x2107000:0x2109000])
            for page, sz in ((0x1A6E000, 0x2000), (0x215C000, 0x1000), (0x2167000, 0x1000), (0xB19000, 0x1000)):
                mu.mem_map(page, sz, U.UC_PROT_READ | U.UC_PROT_EXEC)
            mu.mem_map(0x2608000, 0x1000, U.UC_PROT_READ)
            mu.mem_write(0x2608000, fx6_appfw_bytes[0x2608000:0x2609000])
            mu.mem_map(0x5C39000, 0x1000, U.UC_PROT_READ | U.UC_PROT_WRITE)
            mu.mem_write(FX6_APPFW_HANDLE_CB_QID_GLOBAL_VMA, struct.pack("<I", 0x81CC0501))
            if pre_registered:
                mu.mem_write(FX6_APPFW_HANDLE_CB_HANDLE_GLOBAL_VMA, struct.pack("<Q", 0xCAFEF00D))
            for stub in (ev_alloc_vma, ev_post_vma, reg_cb_vma, send_sync_vma, unreg_cb_vma, assert_vma, free_msg_vma):
                mu.mem_write(stub, struct.pack("<I", 0xD65F03C0))

        mu.mem_map(0x70000000, 0x10000, U.UC_PROT_READ | U.UC_PROT_WRITE)
        mu.mem_map(0x71000000, 0x4000, U.UC_PROT_READ | U.UC_PROT_WRITE)
        mu.mem_map(0x72000000, 0x1000, U.UC_PROT_READ | U.UC_PROT_EXEC)
        mu.mem_write(0x72000000, struct.pack("<I", 0xD503201F))

        state: Dict[str, object] = {
            "assert_hit": False,
            "assert_line": 0,
            "dst_q": 0,
            "req_hex": "",
            "reply_hex": "",
            "events": [],
            "freed": False,
        }

        def _hook(uc: U.Uc, addr: int, _sz: int, _ud: object) -> None:
            if addr == ev_alloc_vma:
                uc.reg_write(A.UC_ARM64_REG_X0, 0x71000800)
            elif addr == ev_post_vma:
                ev = struct.unpack("<I", bytes(uc.mem_read(0x71000800, 4)))[0]
                state["events"].append(ev)  # type: ignore[attr-defined]
                uc.reg_write(A.UC_ARM64_REG_W0, 0)
            elif addr == reg_cb_vma:
                if not synthetic_mode:
                    ptr = uc.reg_read(A.UC_ARM64_REG_X1)
                    uc.mem_write(ptr, struct.pack("<Q", 0xCAFEF00D))
                uc.reg_write(A.UC_ARM64_REG_W0, 0)
            elif addr == send_sync_vma:
                p = uc.reg_read(A.UC_ARM64_REG_X0)
                l = uc.reg_read(A.UC_ARM64_REG_W1)
                q = uc.reg_read(A.UC_ARM64_REG_W2)
                req_b = bytes(uc.mem_read(p, l))
                state["dst_q"] = q
                state["req_hex"] = req_b.hex()
                if snd_rc == 0:
                    ack_b, _, _ = synthesize_smart_handle_ack(req_b, grip_attached=False)
                    state["reply_hex"] = ack_b.hex()
                uc.reg_write(A.UC_ARM64_REG_W0, snd_rc)
            elif addr == assert_vma:
                state["assert_hit"] = True
                state["assert_line"] = uc.reg_read(A.UC_ARM64_REG_W1)
            elif addr == free_msg_vma:
                state["freed"] = True
                uc.reg_write(A.UC_ARM64_REG_W0, 0)

        mu.hook_add(U.UC_HOOK_CODE, _hook)
        sp0 = 0x7000E000
        mu.reg_write(A.UC_ARM64_REG_SP, sp0)
        mu.reg_write(A.UC_ARM64_REG_LR, 0x72000000)

        if action == "register":
            mu.emu_start(h_reg_vma, 0x72000000, count=400)
        elif action == "unregister":
            mu.emu_start(h_unreg_vma, 0x72000000, count=400)
        else:
            msg_addr = 0x71000100
            mu.mem_write(msg_addr, struct.pack("<III", cb_cmd, 0, 0x81CC0501))
            mu.reg_write(A.UC_ARM64_REG_X0, msg_addr)
            mu.emu_start(h_cb_vma, 0x72000000, count=400)

        hs_rc = _run_xlr_h1_hotshoe()
        return Queue2HandleUnicornResult(
            case_name=case_name,
            completed_normally=not bool(state["assert_hit"]),
            assert_hit=bool(state["assert_hit"]),
            assert_line=int(state["assert_line"]),
            destination_queue=int(state["dst_q"]) if state["dst_q"] else HANDLE_QUEUE_ID,
            request_hex=str(state["req_hex"]),
            reply_hex=str(state["reply_hex"]),
            posted_events=tuple(state["events"]),  # type: ignore[arg-type]
            free_msg_called=bool(state["freed"]),
            xlr_h1_hotshoe_rc=hs_rc,
            sp_preserved=mu.reg_read(A.UC_ARM64_REG_SP) == sp0,
        )

    return (
        _run_q2("q2_unintercepted_register_asserts", action="register", snd_rc=0xFFFFFFFF),
        _run_q2("q2_intercepted_register_detached_ack", action="register", snd_rc=0),
        _run_q2("q2_callback_detached_0x88000002", action="callback", cb_cmd=HANDLE_EVT_DETACHED_CMD),
        _run_q2("q2_callback_attached_0x88000001", action="callback", cb_cmd=HANDLE_EVT_ATTACHED_CMD),
        _run_q2("q2_intercepted_unregister_ack", action="unregister", snd_rc=0, pre_registered=True),
    )


def verify_imaging_bridge_unicorn(
    fx6_appfw_bytes: bytes,
    *,
    synthetic_mode: bool,
) -> Tuple[ImagingBridgeUnicornResult, ...]:
    """Prove FX6 `0x0165` 36B 3D LUT DMA (>48KB), `0x0166` toggle, and IBIS `set_tc_on_movie_i`."""
    results: List[ImagingBridgeUnicornResult] = []
    if synthetic_mode:
        look65_vma = 0x7500
        look66_vma = 0x7600
        tc_on_vma = 0x7700
        send_wait_vma = 0x80A0
    else:
        look65_vma = FX6_APPFW_LOOKNAME_0165_VMA
        look66_vma = FX6_APPFW_LOOKNAME_0166_VMA
        tc_on_vma = FX6_APPFW_TC_ON_MOVIE_VMA
        send_wait_vma = FX6_APPFW_SEND_WAIT_CMP_VMA

    def _run_look(case_name: str, entry: int, data_sz: int) -> ImagingBridgeUnicornResult:
        mu = U.Uc(U.UC_ARCH_ARM64, U.UC_MODE_ARM)
        mu.reg_write(A.UC_ARM64_REG_CPACR_EL1, 3 << 20)
        if synthetic_mode:
            mu.mem_map(0x7000, 0x2000, U.UC_PROT_READ | U.UC_PROT_EXEC)
            mu.mem_write(0x7000, fx6_appfw_bytes[0x7000:0x9000])
        else:
            mu.mem_map(0x20ED000, 0x6000, U.UC_PROT_READ | U.UC_PROT_EXEC)
            mu.mem_write(0x20ED000, fx6_appfw_bytes[0x20ED000:0x20F3000])
            mu.mem_map(0x21BB000, 0x1000, U.UC_PROT_READ | U.UC_PROT_EXEC)
            mu.mem_map(0x25FF000, 0x1000, U.UC_PROT_READ)
            mu.mem_write(0x25FF000, fx6_appfw_bytes[0x25FF000:0x2600000])
            for stub in (send_wait_vma, FX6_APPFW_STATUS_MAP_VMA, FX6_APPFW_LOG_HELPER_VMA):
                mu.mem_write(stub, struct.pack("<I", 0xD65F03C0))

        mu.mem_map(0x70000000, 0x10000, U.UC_PROT_READ | U.UC_PROT_WRITE)
        mu.mem_map(0x71000000, 0x4000, U.UC_PROT_READ | U.UC_PROT_WRITE)
        mu.mem_map(0x72000000, 0x1000, U.UC_PROT_READ | U.UC_PROT_EXEC)
        mu.mem_write(0x72000000, struct.pack("<I", 0xD503201F))

        cap = {"dst_q": 0, "pkt_hex": "", "pkt_len": 0}

        def _hook(uc: U.Uc, addr: int, _sz: int, _ud: object) -> None:
            if addr == send_wait_vma:
                cap["dst_q"] = uc.reg_read(A.UC_ARM64_REG_W0)
                p = uc.reg_read(A.UC_ARM64_REG_X1)
                l = uc.reg_read(A.UC_ARM64_REG_W2)
                pkt = bytes(uc.mem_read(p, l))
                cap["pkt_hex"] = pkt.hex()
                cap["pkt_len"] = len(pkt)
                uc.reg_write(A.UC_ARM64_REG_W0, 0)
            elif not synthetic_mode and addr == FX6_APPFW_STATUS_MAP_VMA:
                uc.reg_write(A.UC_ARM64_REG_W0, 0)

        mu.hook_add(U.UC_HOOK_CODE, _hook)
        sp0 = 0x7000E000
        mu.reg_write(A.UC_ARM64_REG_SP, sp0)
        mu.reg_write(A.UC_ARM64_REG_LR, 0x72000000)

        if entry == look65_vma:
            mu.mem_write(
                0x71000000,
                struct.pack("<IIIIIIIIII", 3, 1, 1, data_sz, 0x1000, data_sz, 0x20000, 0x400, 1, 3),
            )
        else:
            mu.mem_write(0x71000000, struct.pack("<I", 0))  # 0 -> enable=1

        mu.reg_write(A.UC_ARM64_REG_X0, 0x71000000)
        mu.reg_write(A.UC_ARM64_REG_X1, 0x71000100)
        mu.emu_start(entry, 0x72000000, count=400)
        rc = struct.unpack("<I", bytes(mu.mem_read(0x71000100, 4)))[0]
        return ImagingBridgeUnicornResult(
            case_name=case_name,
            destination_queue=int(cap["dst_q"]),
            packet_hex=str(cap["pkt_hex"]),
            packet_bytes=int(cap["pkt_len"]),
            return_code=rc,
            sp_preserved=mu.reg_read(A.UC_ARM64_REG_SP) == sp0,
        )

    results.append(_run_look("lut_0x0165_33cube_8bit_dma_107812", look65_vma, LUT_8BIT_ALIGNED_BYTES))
    results.append(_run_look("lut_0x0165_33cube_16bit_dma_215622", look65_vma, LUT_16BIT_BYTES))
    results.append(_run_look("lut_0x0166_enable_10b", look66_vma, 0))

    # IBIS `set_tc_on_movie_i` mapping verification (modes 2=Standard -> 1, 4=Off -> 0)
    mu_ibis = U.Uc(U.UC_ARCH_ARM64, U.UC_MODE_ARM)
    mu_ibis.reg_write(A.UC_ARM64_REG_CPACR_EL1, 3 << 20)
    if synthetic_mode:
        mu_ibis.mem_map(0x7000, 0x2000, U.UC_PROT_READ | U.UC_PROT_EXEC)
        mu_ibis.mem_write(0x7000, fx6_appfw_bytes[0x7000:0x9000])
    else:
        mu_ibis.mem_map(0x2110000, 0x1000, U.UC_PROT_READ | U.UC_PROT_EXEC)
        mu_ibis.mem_write(0x2110000, fx6_appfw_bytes[0x2110000:0x2111000])
        mu_ibis.mem_map(0x260C000, 0x1000, U.UC_PROT_READ)
        mu_ibis.mem_write(0x260C000, fx6_appfw_bytes[0x260C000:0x260D000])
    mu_ibis.mem_map(0x70000000, 0x10000, U.UC_PROT_READ | U.UC_PROT_WRITE)
    mu_ibis.mem_map(0x71000000, 0x1000, U.UC_PROT_READ | U.UC_PROT_WRITE)
    mu_ibis.mem_map(0x72000000, 0x1000, U.UC_PROT_READ | U.UC_PROT_EXEC)
    mu_ibis.mem_write(0x72000000, struct.pack("<I", 0xD503201F))

    sp0 = 0x7000E000
    for mode_arg, label in ((2, "ibis_set_tc_on_movie_standard"), (4, "ibis_set_tc_on_movie_off")):
        mu_ibis.mem_write(0x71000000, b"\xff")
        mu_ibis.reg_write(A.UC_ARM64_REG_SP, sp0)
        mu_ibis.reg_write(A.UC_ARM64_REG_LR, 0x72000000)
        mu_ibis.reg_write(A.UC_ARM64_REG_W0, mode_arg)
        mu_ibis.reg_write(A.UC_ARM64_REG_X1, 0x71000000)
        mu_ibis.emu_start(tc_on_vma, 0x72000000, count=100)
        out_b = bytes(mu_ibis.mem_read(0x71000000, 1))[0]
        results.append(
            ImagingBridgeUnicornResult(
                case_name=label,
                destination_queue=0,
                packet_hex=f"{out_b:02x}",
                packet_bytes=1,
                return_code=out_b,
                sp_preserved=mu_ibis.reg_read(A.UC_ARM64_REG_SP) == sp0,
            )
        )
    return tuple(results)


# ---------------------------------------------------------------------------
# Phase 21 Report & End-to-End Verifier Entrypoint
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase21UipcCpShimReport:
    schema: str
    phase_version: str
    verification_mode: str
    passed: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    p8_cp_mutation_forbidden: bool
    cp_mutation_bytes: int
    donor_access_mode: str
    fx6_exclusive_blocking_queues: Tuple[str, ...]
    queue1_rtc_cases: Tuple[Queue1RtcUnicornResult, ...]
    queue2_handle_cases: Tuple[Queue2HandleUnicornResult, ...]
    imaging_bridge_cases: Tuple[ImagingBridgeUnicornResult, ...]
    developing_fhd_translation: DevelopingFhdTranslationResult
    lut_state_machine_trace: Tuple[LutStageSnapshot, ...]
    ibis_telemetry_bridge: Tuple[IbisTelemetryBridgeState, ...]
    xlr_h1_digmic_markers_present: Tuple[str, ...]
    fx3_cp_ibis_markers_present: Tuple[str, ...]
    fx3_cp_develop_markers_present: Tuple[str, ...]
    libmpr_cube_alloc_verified: bool
    errors: Tuple[str, ...]
    report_sha256: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)

    def to_deterministic_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=False) + "\n"


def _has_movzk_imm64_or_32(elf_bytes: bytes, val: int, rd: int = 0) -> bool:
    return _encode_aarch64_movzk(rd, val) in elf_bytes or _encode_aarch64_movzk_64(rd, val) in elf_bytes


def run_phase21_uipc_cp_shim_verification(
    *,
    donor_blobs: Optional[Mapping[str, bytes]] = None,
    synthetic_mode: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Phase21UipcCpShimReport:
    """Run full Phase 21 (`P11`) verification across real FX6/FX3 donors or clean-room fixtures."""
    errors: List[str] = []
    paths = resolve_phase21_donor_paths(env=env)

    if donor_blobs is not None:
        blobs = dict(donor_blobs)
        clean_room = True if synthetic_mode is None else bool(synthetic_mode)
    else:
        clean_room = is_phase21_clean_room_mode(paths, env=env) if synthetic_mode is None else bool(synthetic_mode)
        if clean_room:
            blobs = build_clean_room_phase21_fixtures()
        else:
            blobs = {
                k: read_donor_bytes_readonly(paths[k])
                for k in ("fx6_appfw", "fx6_libmpr", "fx3_libmpr", "fx6_hotshoe", "fx6_cpapp", "fx3_cpapp")
            }

    verification_mode = "CLEAN_ROOM_SYNTHETIC_VERIFIED" if clean_room else "LOCAL_DONOR_VERIFIED"

    # 1. Verify exact 2 FX6-exclusive blocking queues absent in FX3 Stock-CP
    fx6_appfw_qs = _scan_aarch64_0x9xxx_movzk(blobs["fx6_appfw"])
    fx3_cp_qs = _scan_cp_0x9xxx_movwt(blobs["fx3_cpapp"])
    fx6_cp_qs = _scan_cp_0x9xxx_movwt(blobs["fx6_cpapp"])

    exclusive_blocking: List[str] = []
    for qid in (RTC_QUEUE_ID, HANDLE_QUEUE_ID):
        if qid not in fx6_appfw_qs:
            errors.append(f"FX6 appFw.so missing expected blocking queue 0x{qid:08x}")
        if qid not in fx6_cp_qs and struct.pack("<I", qid) not in blobs["fx6_cpapp"]:
            errors.append(f"FX6 cpapp-b.bin missing expected queue 0x{qid:08x}")
        if qid in fx3_cp_qs or struct.pack("<I", qid) in blobs["fx3_cpapp"]:
            errors.append(f"FX3 Stock-CP unexpectedly contains FX6-exclusive queue 0x{qid:08x}")
        else:
            exclusive_blocking.append(f"0x{qid:08x}")

    # Verify FX3 Stock-CP has all developing/LUT 0x92840747 completion handlers
    matched_dev_ops = _scan_cp_uipc_completion_opcodes(
        blobs["fx3_cpapp"], FX3_SUPPORTED_0X92840747_DEVELOP_OPCODES
    )
    missing_dev_ops = set(FX3_SUPPORTED_0X92840747_DEVELOP_OPCODES) - matched_dev_ops
    if missing_dev_ops:
        errors.append(
            "FX3 Stock-CP missing developing/LUT 0x92840747 opcodes: "
            + ", ".join(f"0x{op:04x}" for op in sorted(missing_dev_ops))
        )

    # 2. Verify Queue 1 (RTC 0x92d2091c) in Unicorn AArch64 + /dev/rtc0 -> udate translation
    nominal_rtc = LinuxRtcTime(
        tm_sec=45, tm_min=30, tm_hour=11, tm_mday=14, tm_mon=10, tm_year=126, tm_wday=6, tm_yday=317
    )
    q1_cases = verify_queue1_rtc_unicorn(blobs["fx6_appfw"], nominal_rtc, synthetic_mode=clean_room)
    if not q1_cases[0].hang_detected:
        errors.append("Queue 1 unintercepted case failed to prove std::future::wait hang")
    if not q1_cases[1].completed_normally or q1_cases[1].reply_hex != "0300":
        errors.append(f"Queue 1 intercepted send_sync failed: {q1_cases[1]}")
    if q1_cases[2].promise_bool_value != 1 or q1_cases[2].expected_get_rtc_status_rc != 0 or not q1_cases[2].free_msg_called:
        errors.append(f"Queue 1 valid RTC0 callback failed: {q1_cases[2]}")
    if q1_cases[3].promise_bool_value != 0 or q1_cases[3].expected_get_rtc_status_rc != 2:
        errors.append(f"Queue 1 unset RTC0 callback failed: {q1_cases[3]}")
    if q1_cases[4].promise_bool_value is not None or not q1_cases[4].free_msg_called:
        errors.append(f"Queue 1 wrong-src message was not ignored safely: {q1_cases[4]}")

    # 3. Verify Queue 2 (Smart Handle 0x91db059b) + XLR-H1 MI-shoe coexistence in Unicorn AArch64
    q2_cases = verify_queue2_handle_and_hotshoe_unicorn(
        blobs["fx6_appfw"], blobs["fx6_hotshoe"], synthetic_mode=clean_room
    )
    if not q2_cases[0].assert_hit or q2_cases[0].assert_line != FX6_APPFW_HANDLE_REG_ASSERT_LINE:
        errors.append(f"Queue 2 unintercepted register failed to trigger expected line 123 assert: {q2_cases[0]}")
    if q2_cases[1].assert_hit or HANDLE_EVENT_DETACHED_ID not in q2_cases[1].posted_events:
        errors.append(f"Queue 2 intercepted register failed: {q2_cases[1]}")
    if q2_cases[2].posted_events != (HANDLE_EVENT_DETACHED_ID,) or not q2_cases[2].free_msg_called:
        errors.append(f"Queue 2 detached callback failed: {q2_cases[2]}")
    if q2_cases[3].posted_events != (HANDLE_EVENT_ATTACHED_ID,) or not q2_cases[3].free_msg_called:
        errors.append(f"Queue 2 attached callback failed: {q2_cases[3]}")
    if q2_cases[4].assert_hit:
        errors.append(f"Queue 2 unregister failed: {q2_cases[4]}")
    if any(c.xlr_h1_hotshoe_rc != 0 for c in q2_cases):
        errors.append("XLR-H1 libInfraHotshoe WaitRecvCompMsgFromHotshoeRsrc returned non-zero")

    xlr_markers = tuple(
        m for m in (XLR_H1_DIGMIC_ON_EVENT, XLR_H1_DIGMIC_OFF_EVENT) if m.encode("latin1") in blobs["fx6_appfw"]
    )
    if len(xlr_markers) != 2:
        errors.append("FX6 appFw.so missing XLR-H1 MI-shoe DIGMIC event markers")

    # 4. Verify Imaging Bridge in Unicorn + `libmpr.so` 0x6a1b9 .cube alloc
    img_cases = verify_imaging_bridge_unicorn(blobs["fx6_appfw"], synthetic_mode=clean_room)
    for c in img_cases:
        if not c.sp_preserved:
            errors.append(f"Imaging bridge Unicorn SP corrupted in {c.case_name}")
    if img_cases[0].packet_bytes != LUT_DMA_ENABLE_SIZE or img_cases[1].packet_bytes != LUT_DMA_ENABLE_SIZE:
        errors.append("0x0165 LUT DMA packet length != 36B in Unicorn execution")
    if img_cases[2].packet_bytes != LUT_TOGGLE_SIZE or img_cases[2].packet_hex != "0d2066010a0001800100":
        errors.append(f"0x0166 LUT toggle unexpected packet {img_cases[2].packet_hex}")
    if img_cases[3].return_code != 1 or img_cases[4].return_code != 0:
        errors.append("IBIS set_tc_on_movie_i Unicorn return values mismatch (expected 1 for Standard, 0 for Off)")

    mpr_alloc_ok = _has_movzk_imm64_or_32(blobs["fx3_libmpr"], LUT_CUBE_ALLOC_BYTES, rd=0) and _has_movzk_imm64_or_32(
        blobs["fx6_libmpr"], LUT_CUBE_ALLOC_BYTES, rd=0
    )
    if not mpr_alloc_ok:
        errors.append("libmpr.so missing 0x6a1b9 (434,617 B) 33^3 3D LUT buffer allocation")

    # 5. Verify `developing_mode_FHD`, Cine EI / LUT State Machine, & IBIS Telemetry Bridge
    dev_fhd = translate_developing_mode_fhd(developing_mode_fhd=1, fps=59)

    fsm = CineEiLutDmaStateMachine()
    trace = [
        fsm.stage_cube_lut("/usr/data/lut/SLog3SGamut3Cine.cube", LUT_8BIT_ALIGNED_BYTES, base_iso=800, ei_index=800),
        fsm.arm_dma_0165(),
        fsm.enable_look_0166(),
        fsm.set_cine_ei(base_iso=12800, ei_index=12800),
        fsm.disable_look_0166(),
    ]
    if trace[0].mpr_descriptor_bytes != MPR_SET_LUT_DESCRIPTOR_BYTES or trace[1].dma_packet_0165_hex != img_cases[0].packet_hex:
        errors.append("Cine EI / 3D LUT DMA state machine 0x0165 packet diverged from real appFw.so Unicorn output")

    ibis_bridge = tuple(evaluate_ibis_steadyshot_bridge(m) for m in VALID_STEADYSHOT_MODES)
    if any(not b.center_lock_energized or b.floating_sensor_hazard for b in ibis_bridge):
        errors.append("FX3 5-axis IBIS telemetry bridge reported unpowered floating sensor hazard")

    # 6. Check FX3 Stock-CP IBIS & Developing markers
    fx3_ibis_present = tuple(m for m in REQUIRED_FX3_IBIS_MARKERS if m.encode("latin1") in blobs["fx3_cpapp"])
    if len(fx3_ibis_present) != len(REQUIRED_FX3_IBIS_MARKERS):
        missing = set(REQUIRED_FX3_IBIS_MARKERS) - set(fx3_ibis_present)
        errors.append(f"FX3 cpapp-b.bin missing IBIS markers: {sorted(missing)}")

    fx3_dev_present = tuple(m for m in REQUIRED_FX3_DEVELOP_MARKERS if m.encode("latin1") in blobs["fx3_cpapp"])
    if len(fx3_dev_present) != len(REQUIRED_FX3_DEVELOP_MARKERS):
        missing = set(REQUIRED_FX3_DEVELOP_MARKERS) - set(fx3_dev_present)
        errors.append(f"FX3 cpapp-b.bin missing developing markers: {sorted(missing)}")

    # 7. Exercise live `UipcCpShimRuntime` dispatcher
    runtime = UipcCpShimRuntime(rtc_time=nominal_rtc, smart_handle_attached=False)
    r_rtc = runtime.dispatch(RTC_QUEUE_ID, b"\x03\x00")
    r_hdl = runtime.dispatch(HANDLE_QUEUE_ID, struct.pack("<III", HANDLE_REG_CMD, 0, 0x81CC0501))
    r_lut = runtime.dispatch(UIPC_BB_TARGET_QUEUE, bytes.fromhex(trace[1].dma_packet_0165_hex))
    if r_rtc.reply_hex != "0300" or r_hdl.raw_status != 0 or r_lut.intercepted_by_shim:
        errors.append("UipcCpShimRuntime end-to-end dispatch sanity check failed")

    passed = len(errors) == 0
    payload_for_hash = {
        "schema": PHASE_21_SCHEMA,
        "phase_version": PHASE_21_VERSION,
        "verification_mode": verification_mode,
        "passed": passed,
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "persistent_write_release": PERSISTENT_WRITE_RELEASE,
        "p8_cp_mutation_forbidden": P8_CP_MUTATION_FORBIDDEN,
        "cp_mutation_bytes": CP_MUTATION_BYTES,
        "donor_access_mode": "O_RDONLY",
        "fx6_exclusive_blocking_queues": list(exclusive_blocking),
        "queue1_rtc_cases": [asdict(c) for c in q1_cases],
        "queue2_handle_cases": [asdict(c) for c in q2_cases],
        "imaging_bridge_cases": [asdict(c) for c in img_cases],
        "developing_fhd_translation": asdict(dev_fhd),
        "lut_state_machine_trace": [asdict(s) for s in trace],
        "ibis_telemetry_bridge": [asdict(b) for b in ibis_bridge],
        "xlr_h1_digmic_markers_present": list(xlr_markers),
        "fx3_cp_ibis_markers_present": list(fx3_ibis_present),
        "fx3_cp_develop_markers_present": list(fx3_dev_present),
        "libmpr_cube_alloc_verified": mpr_alloc_ok,
        "errors": errors,
    }
    report_sha256 = hashlib.sha256(
        json.dumps(payload_for_hash, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    return Phase21UipcCpShimReport(
        schema=PHASE_21_SCHEMA,
        phase_version=PHASE_21_VERSION,
        verification_mode=verification_mode,
        passed=passed,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        p8_cp_mutation_forbidden=P8_CP_MUTATION_FORBIDDEN,
        cp_mutation_bytes=CP_MUTATION_BYTES,
        donor_access_mode="O_RDONLY",
        fx6_exclusive_blocking_queues=tuple(exclusive_blocking),
        queue1_rtc_cases=q1_cases,
        queue2_handle_cases=q2_cases,
        imaging_bridge_cases=img_cases,
        developing_fhd_translation=dev_fhd,
        lut_state_machine_trace=tuple(trace),
        ibis_telemetry_bridge=ibis_bridge,
        xlr_h1_digmic_markers_present=xlr_markers,
        fx3_cp_ibis_markers_present=fx3_ibis_present,
        fx3_cp_develop_markers_present=fx3_dev_present,
        libmpr_cube_alloc_verified=mpr_alloc_ok,
        errors=tuple(errors),
        report_sha256=report_sha256,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="uipc_cp_shim_verifier",
        description="Phase 21 (P11) AP-Side UIPC Dual-Blocking Queue & Cine EI / LUT / IBIS Bridge Verifier.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="emit_json",
        help="Emit deterministic JSON report to stdout",
    )
    args = parser.parse_args(argv)
    report = run_phase21_uipc_cp_shim_verification()
    if args.emit_json:
        sys.stdout.write(report.to_deterministic_json())
    else:
        status = "PASS" if report.passed else "FAIL"
        sys.stdout.write(
            f"[Phase 21 P11 UIPC-CP Shim] {status} ({report.verification_mode}) | "
            f"queues={','.join(report.fx6_exclusive_blocking_queues)} | "
            f"sha256={report.report_sha256[:16]}...\n"
        )
        for err in report.errors:
            sys.stdout.write(f"  ! {err}\n")
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
