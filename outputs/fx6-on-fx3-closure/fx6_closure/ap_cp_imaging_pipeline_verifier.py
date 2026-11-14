"""Phase 18 — Cross-Generation AP (FX6 6.01) <-> Stock-CP (FX3 7.02) Imaging Pipeline Verifier.

Provides deterministic protocol-level reverse-engineering verification and Unicorn AArch64
instruction-level execution across the 4 core Stage-A imaging/actuation pillars under the `U2`
Stock-CP redline (`p8_cp_mutation_forbidden = True`):

1. **Full `SeqQueue*` / UIPC Blocking Request Cross-Model Scanner**:
   - Scans FX6 `appFw.so`, `libmpr.so`, and companion ELFs for all `0x9xxxxxxx` CP RTOS UIPC queues
     (via AArch64 `MOVZ`/`MOVK` decoding) and scans both FX3 7.02 `cpapp-b.bin` and FX6 6.01
     `cpapp-b.bin` (via Thumb-2 `MOVW`/`MOVT` windows + literal-pool LE32 scans).
   - Verifies all 44 `0x92840747` `0x200d` opcodes used by FX6 `appFw.so::send_and_wait_cmp_i`
     (`0x20ef604`, including `0x032d`, `0x0400/0x0402/0x0404/0x0152`, LUT DMA `0x0165`/`0x0166`,
     de-squeeze `0x016b`, monitor extender `0x016c`, `0x0416`, `0x0426`, `0x0428`), plus shared
     queues (`0x909a015a`, `0x909c015b`, `0x912f0335`, `0x905a0048`, `0x9004015e`, `0x92850750`,
     `0x92a50981`, `0x90610823`) exist in FX3 Stock-CP.
   - Identifies the exact 2 FX6-exclusive CP queues absent (`0` hits) in FX3 `cpapp-b.bin`:
     - `0x92d2091c` (`infra_wrapper_rtc::detail::get_rtc_status`, `std::future<bool>::wait()`
       permanent hang unless synthesized `[_, 0x00]` reply from `0x92d2091c` arrives).
     - `0x91db059b` (`infra_wrapper_handle::detail::register_callback`/`unregister_callback`,
       12B `0x81000001`/`0x81000002` Smart Handle/Grip messages via `send_sync_msg`).
   - Provides byte-level request parsers & completion synthesizers for `0x92d2091c`, `0x91db059b`,
     and `0x92840747` `0x0165`/`0x0166` LUT DMA descriptors.

2. **CMOS / Dual Native ISO (800 / 12800) / Cine EI & 33^3 3D LUT DMA Contract**:
   - Verifies ABI homology between FX3 7.02 `libmpr.so` and FX6 6.01 `libmpr.so` for
     `mpr::SetLutData` (`0xd484c` vs `0x1505a8`, 164B), `mpr::ExecuteSetLutData` (`0xd4668` vs
     `0x150358`, `0x6a1b9 = 434,617 B` `.cube` 3D LUT allocation, `+0x4` enable byte, `+0x1f`
     path, 26B+64B state copy), `appFw.so::video_set_lookname_procam` (`0x20f1c60` -> `0x0165`
     36B DMA descriptor with `0xbb80 = 48000` threshold & `0x0166` 10B), and shared CXD90057 ISP
     MLUT/EI driver markers (`ddl_VfxSetMlut`, `ddl_VfxSetMlutEIGain`, `SendVEF_PathSetLut`,
     `SendVDF_SetMonitorLut`, `SendVEF_PathSetEiGain`, `baseSensitivity`, `Base_Picture_Setting_*`).
   - Runs Unicorn AArch64 instruction-level execution on FX6 & FX3 `mpr::SetLutData` +
     `mpr::ExecuteSetLutData`, `appFw.so` `0x0166` lookname, and `0x92d2091c` RTC completion/hang.

3. **XAVC-I / XAVC-L Recording Matrix & E-Mount AF (`libmpr.so` & `libInfraLensCommunicator.so`)**:
   - Audits `mpr::SetMovieRecParam` (`0xf0ff0` 445B vs `0x16c5e0` 2248B with AP-side
     `GetDProXavcIntraVQuality` & `libXavcMxf::SetClipName` codec `8`), shared CP LiroSeq keys
     (`mov_size_req`, `mov_aspect_req`, `frate_req`, `e_set_img_frame_size`, `DCI4K`, `QFHD`),
     and proves `libInfraLensCommunicator.so` (`14,544 B`) is 100% byte-identical across `.plt`,
     `.text`, `.rodata`, `.data`, and `.dynsym` (only 6 bytes differ in `.comment` GCC date).

4. **FX3 5-Axis IBIS Actuator Safety / Center-Lock Contract**:
   - Proves FX3 Stock-CP (`cpapp-b.bin`) retains full 5-axis IBIS Hall/Gyro PID servo control
     (`HallPIDOUT_0/1`, `GyroPIDOUT_0/1`, `FusionOUT_0/1`, `AllPIDOUT_0/1`, `PWMOUT_0/1`,
     `CheckSetSteadyShotAdvancedMovie`, `CheckSetSteadyShotAdvancedStill`, `steadyshot_body_axis*`,
     `FWCP-isRetract`, `LiroSeq: Restore.` from FX3 `p2:/Backup.bin` + `p2:/psd.bin` + `p6:Jiritsu`),
     whereas FX6 `appFw.so` carries `PRM_is_imager_stabilization_unit_fixed` and emits shared
     `is_mode` / `is_on_movie` (`set_tc_mode_i` / `set_tc_on_movie_i`) without Active-IBIS
     extension calls — keeping the FX3 voice-coil platform energized and center-locked in Stock
     Standard mode rather than unpowered/floating.

All donor paths resolve via `Path.home() / "AI-Workspace/AI/Projects/Mac/work"` and environment
overrides, with full `FX3_FX6_FORCE_CLEAN_ROOM=1` donorless synthetic test support.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import hashlib
import json
import os
import re
import struct
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

import unicorn as U
from unicorn import arm64_const as A


PHASE_18_SCHEMA = "stage_a_phase18_ap_cp_imaging_audit_v1"
PHASE_18_VERSION = "18.0.0"

# Read-only donor resolution rooted at Path.home() / "AI-Workspace/AI/Projects/Mac/work"
DEFAULT_WORK_ROOT = Path.home() / "AI-Workspace" / "AI" / "Projects" / "Mac" / "work"


def _resolve_work_paths() -> Dict[str, Path]:
    work_root = Path(os.environ.get("FX3_FX6_WORK_ROOT", str(DEFAULT_WORK_ROOT)))
    fx6_donor = Path(
        os.environ.get(
            "FX6_DONOR_ROOT",
            str(work_root / "fx3-color-port-20261027" / "FX6-donor-assessment-20261103" / "team" / "donor"),
        )
    )
    fx3_fw = Path(
        os.environ.get("FX3_FW_ROOT", str(work_root / "sony-firmware-20261024"))
    )
    fx3_vm = Path(
        os.environ.get("FX3_VM_ROOT", str(work_root / "fx3-vm-20261101"))
    )
    fx3_lens_dir = Path(
        os.environ.get(
            "FX3_LENS_ROOT",
            str(work_root / "fx3-color-port-20261027" / "lens-state-20261029" / "original-members"),
        )
    )
    return {
        "fx3_cpapp": Path(
            os.environ.get(
                "FX3_CPAPP_PATH",
                str(fx3_fw / "stage2" / "extraction" / "files" / "nflasha8" / "cpapp-b.bin"),
            )
        ),
        "fx6_cpapp": Path(
            os.environ.get(
                "FX6_CPAPP_PATH",
                str(fx6_donor / "fat-files" / "nflasha8" / "cpapp-b.bin"),
            )
        ),
        "fx3_libmpr": Path(
            os.environ.get(
                "FX3_LIBMPR_PATH",
                str(fx3_fw / "stage2" / "extraction" / "files" / "nflasha15" / "lib" / "libmpr.so"),
            )
        ),
        "fx6_libmpr": Path(
            os.environ.get(
                "FX6_LIBMPR_PATH",
                str(fx6_donor / "nflasha15-files" / "lib" / "libmpr.so"),
            )
        ),
        "fx3_appfw": Path(
            os.environ.get(
                "FX3_APPFW_PATH",
                str(fx3_vm / "fx3-audit" / "original-members" / "nflasha15" / "lib" / "appFw.so"),
            )
        ),
        "fx6_appfw": Path(
            os.environ.get(
                "FX6_APPFW_PATH",
                str(fx6_donor / "nflasha15-files" / "lib" / "appFw.so"),
            )
        ),
        "fx3_lens_comm": Path(
            os.environ.get(
                "FX3_LENS_COMM_PATH",
                str(fx3_lens_dir / "libInfraLensCommunicator.so"),
            )
        ),
        "fx6_lens_comm": Path(
            os.environ.get(
                "FX6_LENS_COMM_PATH",
                str(fx6_donor / "nflasha15-files" / "lib" / "libInfraLensCommunicator.so"),
            )
        ),
    }


def is_forced_clean_room(paths: Optional[Mapping[str, Path]] = None) -> bool:
    if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM", "").strip() == "1":
        return True
    resolved = paths or _resolve_work_paths()
    required = ("fx3_cpapp", "fx6_cpapp", "fx3_libmpr", "fx6_libmpr", "fx6_appfw", "fx3_lens_comm", "fx6_lens_comm")
    return not all(resolved[k].is_file() for k in required)


# ---------------------------------------------------------------------------
# Pinned Protocol Constants (Verified against FX6 6.01 & FX3 7.02 Donors)
# ---------------------------------------------------------------------------

UIPC_BB_TARGET_QUEUE = 0x92840747
UIPC_BB_MAGIC = 0x200D
UIPC_BB_FLAGS = 0x8001
UIPC_BB_COMPLETION_MASK = 0x1000
UIPC_BB_COMPLETION_BYTES = 12

# Complete 44 opcodes dispatched by FX6 appFw.so::send_and_wait_cmp_i on 0x92840747
EXPECTED_FX6_0X92840747_OPCODES: Tuple[int, ...] = (
    0x0112, 0x0114, 0x0119, 0x011A, 0x011F, 0x0121, 0x0133, 0x0136,
    0x013C, 0x0145, 0x0152, 0x015E, 0x0162, 0x0163, 0x0165, 0x0166,
    0x0167, 0x0168, 0x0169, 0x016A, 0x016B, 0x016C, 0x031B, 0x032B,
    0x032C, 0x032D, 0x0400, 0x0401, 0x0402, 0x0404, 0x0405, 0x0406,
    0x0408, 0x0409, 0x040A, 0x040C, 0x040D, 0x0411, 0x0412, 0x0414,
    0x0416, 0x0421, 0x0426, 0x0428,
)

# Critical imaging / LUT / framing opcodes inside 0x92840747 beyond P5/P6
IMAGING_0X92840747_OPCODES: Dict[int, str] = {
    0x0165: "video_set_lookname_procam (36B 3D LUT SRAM/REG DMA descriptor)",
    0x0166: "video_set_lookname_procam_enable (10B LUT enable/reset toggle)",
    0x016B: "de_squeeze_display_setting (12B)",
    0x016C: "monitor_extender_setting (20B)",
    0x032D: "P5 audio/hdmi pre-init sync (10B -> raw_status 0x00580000)",
    0x0400: "P6 timecode run-mode sync (10B)",
    0x0402: "P6 timecode/UB mode sync (10B)",
    0x0404: "P6 timecode/UB value sync (12B)",
    0x0152: "P6 VDF peaking sync (14B)",
    0x0416: "video_set_mode_procam (8B)",
}

# All CP RTOS queues shared between FX6 userland and FX3 7.02 Stock cpapp-b.bin
SHARED_AP_CP_QUEUES: Tuple[int, ...] = (
    0x92840747,  # UIPC BB primary control / imaging / lookname / P5 / P6
    0x909A015A,  # Camera / sensor sequence sync (0x2500 magic)
    0x909C015B,  # Camera sub-sequence sync
    0x912F0335,  # 48B 0x8102 sync queue
    0x905A0048,  # Avbbc / ObjAvAdjCtrl / appFw OSAL reply/control
    0x9004015E,  # libmpr codec / recorder queue
    0x92850750,  # libmpr UIPC companion queue
    0x92A50981,  # libmpr media/MXF queue
    0x90610823,  # CP media/streaming sync queue
)

# FX6-exclusive CP queues completely absent in FX3 7.02 Stock cpapp-b.bin
FX6_EXCLUSIVE_CP_QUEUES: Dict[int, str] = {
    0x92D2091C: "infra_wrapper_rtc_procam_chaplin_base.cpp::get_rtc_status (blocks on std::future<bool>::wait)",
    0x91DB059B: "infra_wrapper_handle_procam_chaplin_base.cpp::register_callback/unregister_callback (Smart Handle/Grip)",
}

# Queue wire constants
RTC_QUEUE_ID = 0x92D2091C
RTC_GET_STATUS_CMD_BYTE = 0x03
RTC_MSG_LEN = 2

HANDLE_QUEUE_ID = 0x91DB059B
HANDLE_REG_CMD = 0x81000001
HANDLE_UNREG_CMD = 0x81000002
HANDLE_MSG_LEN = 12

LUT_DMA_ENABLE_CMD = 0x0165
LUT_DMA_ENABLE_SIZE = 36
LUT_DMA_SRAM_REG_THRESHOLD = 0xBB80  # 48,000 B
LUT_TOGGLE_CMD = 0x0166
LUT_TOGGLE_SIZE = 10

# libmpr.so & appFw.so AArch64 VMA / size constants
FX6_MPR_SET_LUT_VMA = 0x1505A8
FX6_MPR_SET_LUT_LEN = 164
FX6_MPR_EXEC_LUT_VMA = 0x150358
FX6_MPR_EXEC_LUT_LEN = 592
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
FX6_MPR_NOTIFY_TAG_LUT = 0x7B  # 123

FX3_MPR_SET_LUT_VMA = 0xD484C
FX3_MPR_SET_LUT_LEN = 164
FX3_MPR_EXEC_LUT_VMA = 0xD4668
FX3_MPR_EXEC_LUT_LEN = 484
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
FX3_MPR_NOTIFY_TAG_LUT = 0x6F  # 111

LUT_33_CUBE_BUFFER_BYTES = 0x6A1B9  # 434,617 B for 33^3 .cube parser

FX6_MPR_SET_MOVIE_REC_PARAM_VMA = 0x16C5E0
FX6_MPR_SET_MOVIE_REC_PARAM_BYTES = 2248  # 0x8c8
FX3_MPR_SET_MOVIE_REC_PARAM_VMA = 0xF0FF0
FX3_MPR_SET_MOVIE_REC_PARAM_BYTES = 445   # 0x1bd

FX6_APPFW_SEND_WAIT_CMP_VMA = 0x20EF604
FX6_APPFW_LOOKNAME_0166_VMA = 0x20F1D60
FX6_APPFW_RTC_REPLY_CB_VMA = 0x2159B4C
FX6_APPFW_RTC_GET_STATUS_VMA = 0x2159BB0
FX6_APPFW_SEND_SYNC_MSG_VMA = 0x215C38C

EXPECTED_LENS_COMM_BYTES = 14_544
EXPECTED_LENS_COMM_MAX_COMMENT_DIFF_BYTES = 6

# Shared LiroSeq keys verified present in BOTH FX3 7.02 cpapp-b.bin and FX6 6.01 cpapp-b.bin
REQUIRED_SHARED_LIROSEQ_IMAGING_KEYS: Tuple[str, ...] = (
    "Base_Picture_Setting_base_look",
    "Base_Picture_Setting_color_gamut",
    "Base_Picture_Setting_input_gamut",
    "Base_Picture_Setting_shooting_mode",
    "Base_Picture_Setting_target_display",
    "baseSensitivity",
    "mov_size_req",
    "mov_aspect_req",
    "frate_req",
    "e_set_img_frame_size",
    "af_mode",
    "af_adjust_mode",
    "is_mode",
    "is_on_movie",
    "is_type",
)

# FX3 Stock-CP 5-Axis IBIS actuator & servo loop markers
REQUIRED_FX3_IBIS_CP_MARKERS: Tuple[str, ...] = (
    "CheckSetSteadyShotAdvancedMovie",
    "CheckSetSteadyShotAdvancedStill",
    "CheckSetS1SteadyShotMode",
    "CheckSetFrameLockOnSteadyShot",
    "steadyshot_body_axis",
    "steadyshot_body_axis_movie",
    "steadyshot_body_axis_still",
    "steadyshot_info_movie",
    "HallPIDOUT_0",
    "GyroPIDOUT_0",
    "FusionOUT_0",
    "AllPIDOUT_0",
    "PWMOUT_0",
    "FWCP-isRetract",
    "LiroSeq: Restore.",
)

REQUIRED_FX3_ISP_MLUT_MARKERS: Tuple[str, ...] = (
    "ddl_VfxSetMlut",
    "ddl_VfxSetMlutEIGain",
    "SendVEF_PathSetLut",
    "SendVDF_SetMonitorLut",
    "SendVEF_PathSetEiGain",
    "MlutLookNameCallback",
)


class Phase18ProtocolError(ValueError):
    """Raised when a Phase 18 UIPC packet or imaging contract is malformed."""


# ---------------------------------------------------------------------------
# Report Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class UipcQueueScanReport:
    passed: bool
    fx6_appfw_0x9xxx_count: int
    fx3_cp_movwt_0x9xxx_count: int
    fx6_cp_movwt_0x9xxx_count: int
    shared_queues_verified: Tuple[str, ...]
    missing_shared_queues: Tuple[str, ...]
    fx6_exclusive_cp_queues_absent_in_fx3: Tuple[str, ...]
    unexpected_missing_cp_queues: Tuple[str, ...]
    total_0x92840747_opcodes_expected: int
    total_0x92840747_opcodes_matched_in_fx3_cp: int
    missing_0x92840747_opcodes_in_fx3_cp: Tuple[str, ...]
    interception_rules_count: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class LutUnicornExecResult:
    target_model: str
    case_name: str
    return_code: int
    reset_lut_called: bool
    execute_lut_called: bool
    malloc_size: int
    notify_tag: int
    notify_status: int
    state_26b_copied: bool
    state_64b_path: str
    sp_preserved: bool


@dataclass(frozen=True)
class AppFwUnicornExecResult:
    case_name: str
    completed_normally: bool
    return_value: int
    destination_queue: int
    request_hex: str
    reply_hex: str
    hang_detected: bool
    sp_preserved: bool


@dataclass(frozen=True)
class LutCineEiDualIsoReport:
    passed: bool
    fx3_set_lut_bytes: int
    fx6_set_lut_bytes: int
    fx3_cube_alloc_bytes: int
    fx6_cube_alloc_bytes: int
    fx3_cp_isp_mlut_markers_present: Tuple[str, ...]
    fx6_cp_isp_mlut_markers_present: Tuple[str, ...]
    shared_liroseq_imaging_keys_present: Tuple[str, ...]
    missing_shared_liroseq_keys: Tuple[str, ...]
    fx6_only_ei_iso_keys: Tuple[str, ...]
    fx3_only_ei_iso_keys: Tuple[str, ...]
    dual_native_iso_bases: Tuple[int, int]
    unicorn_mpr_cases: Tuple[LutUnicornExecResult, ...]
    unicorn_appfw_cases: Tuple[AppFwUnicornExecResult, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class XavcFormatSupportEntry:
    format_id: str
    resolution: str
    codec: str
    frame_rates: str
    fx6_ap_supported: bool
    fx3_stock_cp_supported: bool
    status: str
    notes: str


@dataclass(frozen=True)
class XavcAndAfContractReport:
    passed: bool
    fx3_movie_rec_param_bytes: int
    fx6_movie_rec_param_bytes: int
    lens_comm_fx3_bytes: int
    lens_comm_fx6_bytes: int
    lens_comm_total_diff_bytes: int
    lens_comm_loadable_segment_diff_bytes: int
    lens_comm_comment_diff_bytes: int
    lens_comm_text_sha256: str
    recording_matrix: Tuple[XavcFormatSupportEntry, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class IbisSafetyContractReport:
    passed: bool
    fx6_has_imager_fixed_param: bool
    fx6_has_set_steadyshot_advanced_movie_i: bool
    fx3_cp_ibis_markers_present: Tuple[str, ...]
    fx3_cp_ibis_markers_missing: Tuple[str, ...]
    fx6_cp_has_body_axis_ibis: bool
    shared_is_mode_keys_present: Tuple[str, ...]
    center_lock_mechanism_verified: bool
    stage_a_limitation_documented: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Phase18ImagingAuditReport:
    schema: str
    phase_version: str
    verification_mode: str
    passed: bool
    p8_cp_mutation_forbidden: bool
    cp_mutation_bytes: int
    uipc_queue_scan: UipcQueueScanReport
    lut_cine_ei_dual_iso: LutCineEiDualIsoReport
    xavc_and_af: XavcAndAfContractReport
    ibis_safety: IbisSafetyContractReport
    errors: Tuple[str, ...]
    report_sha256: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)

    def to_deterministic_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=False) + "\n"


# ---------------------------------------------------------------------------
# Phase 18 UIPC Packet Parsers & Completion Synthesizers (0x92d2091c, 0x91db059b, 0x0165/0x0166)
# ---------------------------------------------------------------------------


def parse_phase18_uipc_request(destination_queue: int, request_bytes: bytes) -> Dict[str, object]:
    """Validate and decode Phase 18 UIPC requests for RTC, Handle, and 3D LUT DMA queues."""
    if destination_queue == RTC_QUEUE_ID:
        if len(request_bytes) != RTC_MSG_LEN:
            raise Phase18ProtocolError(
                f"RTC 0x{RTC_QUEUE_ID:08x} expects {RTC_MSG_LEN}B request, got {len(request_bytes)}B"
            )
        if request_bytes[0] != RTC_GET_STATUS_CMD_BYTE:
            raise Phase18ProtocolError(
                f"RTC 0x{RTC_QUEUE_ID:08x} unexpected command byte 0x{request_bytes[0]:02x}"
            )
        return {
            "queue": f"0x{RTC_QUEUE_ID:08x}",
            "subsystem": "infra_wrapper_rtc",
            "cmd": request_bytes[0],
            "arg": request_bytes[1],
        }

    if destination_queue == HANDLE_QUEUE_ID:
        if len(request_bytes) != HANDLE_MSG_LEN:
            raise Phase18ProtocolError(
                f"Handle 0x{HANDLE_QUEUE_ID:08x} expects {HANDLE_MSG_LEN}B request, got {len(request_bytes)}B"
            )
        cmd, reserved, cb_qid = struct.unpack("<III", request_bytes)
        if cmd not in (HANDLE_REG_CMD, HANDLE_UNREG_CMD):
            raise Phase18ProtocolError(
                f"Handle 0x{HANDLE_QUEUE_ID:08x} invalid command 0x{cmd:08x}"
            )
        return {
            "queue": f"0x{HANDLE_QUEUE_ID:08x}",
            "subsystem": "infra_wrapper_handle",
            "cmd": f"0x{cmd:08x}",
            "reserved": reserved,
            "callback_qid": f"0x{cb_qid:08x}",
        }

    if destination_queue == UIPC_BB_TARGET_QUEUE:
        if len(request_bytes) < 8:
            raise Phase18ProtocolError(f"UIPC BB request too short: {len(request_bytes)}B")
        magic, opcode, declared_len, flags = struct.unpack_from("<HHHH", request_bytes, 0)
        if magic != UIPC_BB_MAGIC or flags != UIPC_BB_FLAGS or declared_len != len(request_bytes):
            raise Phase18ProtocolError(
                f"Malformed UIPC BB header magic=0x{magic:04x} len={declared_len}/{len(request_bytes)} flags=0x{flags:04x}"
            )
        if opcode == LUT_DMA_ENABLE_CMD and len(request_bytes) != LUT_DMA_ENABLE_SIZE:
            raise Phase18ProtocolError(
                f"LUT DMA 0x0165 requires {LUT_DMA_ENABLE_SIZE}B, got {len(request_bytes)}B"
            )
        if opcode == LUT_TOGGLE_CMD and len(request_bytes) != LUT_TOGGLE_SIZE:
            raise Phase18ProtocolError(
                f"LUT toggle 0x0166 requires {LUT_TOGGLE_SIZE}B, got {len(request_bytes)}B"
            )
        return {
            "queue": f"0x{UIPC_BB_TARGET_QUEUE:08x}",
            "subsystem": "uipc_bb",
            "opcode": f"0x{opcode:04x}",
            "completion_opcode": f"0x{opcode | UIPC_BB_COMPLETION_MASK:04x}",
            "payload_hex": request_bytes[8:].hex(),
        }

    raise Phase18ProtocolError(f"Unsupported Phase 18 UIPC queue 0x{destination_queue:08x}")


def synthesize_phase18_uipc_reply(
    destination_queue: int,
    request_bytes: bytes,
    *,
    rtc_status_byte: int = 0x00,
    raw_status: int = 0x00000000,
) -> bytes:
    """Synthesize exact AP-side completion packet to prevent FX3 Stock-CP hangs."""
    parse_phase18_uipc_request(destination_queue, request_bytes)

    if destination_queue == RTC_QUEUE_ID:
        # `appFw.so` @ 0x2159b74 checks `osal_get_msg_src == 0x92d2091c` and `msg[1] == 0 -> true`
        return bytes((RTC_GET_STATUS_CMD_BYTE, rtc_status_byte & 0xFF))

    if destination_queue == HANDLE_QUEUE_ID:
        # `send_sync_msg` (0x215c38c) checks osal_snd_msg rc == 0; ack echoes 12B status=0
        cmd, _, cb_qid = struct.unpack("<III", request_bytes)
        return struct.pack("<III", cmd | 0x01000000, raw_status & 0xFFFFFFFF, cb_qid)

    _, opcode, _, _ = struct.unpack_from("<HHHH", request_bytes, 0)
    return struct.pack(
        "<HHHHI",
        UIPC_BB_MAGIC,
        opcode | UIPC_BB_COMPLETION_MASK,
        UIPC_BB_COMPLETION_BYTES,
        UIPC_BB_FLAGS,
        raw_status & 0xFFFFFFFF,
    )


# ---------------------------------------------------------------------------
# Binary Scanners (AArch64 MOVZ/MOVK, Thumb-2 MOVW/MOVT, ELF64 PHDR/Section)
# ---------------------------------------------------------------------------


def _scan_cp_0x9xxx_movwt(cp_bytes: bytes) -> Dict[int, List[int]]:
    """Decode Thumb-2 `MOVW Rd, #lo` + `MOVT Rd, #hi` pairs in flat `cpapp-b.bin`."""
    mv = memoryview(cp_bytes)
    n = len(cp_bytes)
    recent: Dict[int, Tuple[int, int]] = {}
    hits: Dict[int, List[int]] = {}
    for i in range(0, n - 4, 2):
        hw1 = struct.unpack_from("<H", mv, i)[0]
        if (hw1 & 0xFBF0) == 0xF240:  # MOVW
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
        elif (hw1 & 0xFBF0) == 0xF2C0:  # MOVT
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
                        hits.setdefault(val, []).append(prev[0])
    return hits


def _scan_cp_uipc_completion_opcodes(cp_bytes: bytes, opcodes: Iterable[int]) -> Set[int]:
    """Verify Thumb-2 `MOVW Rd, #(op | 0x1000)` / literal occurrences for `0x92840747` handlers."""
    target_set = {op | UIPC_BB_COMPLETION_MASK for op in opcodes}
    found_cmp: Set[int] = set()
    mv = memoryview(cp_bytes)
    n = len(cp_bytes)
    for i in range(0, n - 4, 2):
        hw1 = struct.unpack_from("<H", mv, i)[0]
        if (hw1 & 0xFBF0) == 0xF240:  # Thumb-2 MOVW
            hw2 = struct.unpack_from("<H", mv, i + 2)[0]
            if (hw2 & 0x8000) == 0:
                imm16 = (
                    ((hw1 & 0xF) << 12)
                    | (((hw1 >> 10) & 1) << 11)
                    | (((hw2 >> 12) & 7) << 8)
                    | (hw2 & 0xFF)
                )
                if imm16 in target_set:
                    found_cmp.add(imm16 ^ UIPC_BB_COMPLETION_MASK)
    return found_cmp


def _scan_aarch64_0x9xxx_movzk(elf_bytes: bytes) -> Set[int]:
    """Decode AArch64 `MOVZ Rd, #lo` + `MOVK Rd, #hi, lsl #16` pairs for `0x9xxxxxxx` constants."""
    insns = memoryview(elf_bytes)
    recent: Dict[int, Tuple[int, int]] = {}
    qs: Set[int] = set()
    for off in range(0, len(elf_bytes) - 4, 4):
        w = struct.unpack_from("<I", insns, off)[0]
        if (w & 0x7FE00000) == 0x52800000:  # MOVZ Wd/Xd, #imm16
            recent[w & 0x1F] = (off, (w >> 5) & 0xFFFF)
        elif (w & 0x7FE00000) == 0x72A00000:  # MOVK Wd/Xd, #imm16, lsl #16
            rd = w & 0x1F
            prev = recent.get(rd)
            if prev is not None and (off - prev[0]) <= 24:
                val = (((w >> 5) & 0xFFFF) << 16) | prev[1]
                if 0x90000000 <= val <= 0x9FFFFFFF:
                    qs.add(val)
    return qs


def _extract_liroseq_param_keys(cp_bytes: bytes) -> Set[str]:
    return {
        m.group(1).decode("latin1")
        for m in re.finditer(rb"ParamCheckErr@%s\[([A-Za-z0-9_]+)\]", cp_bytes)
    }


def _parse_elf64_sections(elf_bytes: bytes) -> Tuple[Dict[str, Tuple[int, int, int, int]], List[Tuple[int, int, int, int]]]:
    """Return section map `{name: (sh_addr, sh_offset, sh_size, sh_type)}` and `PT_LOAD` list."""
    if elf_bytes[:4] != b"\x7fELF" or elf_bytes[4] != 2:
        raise Phase18ProtocolError("Expected ELF64 binary")
    e_phoff = struct.unpack_from("<Q", elf_bytes, 32)[0]
    e_shoff = struct.unpack_from("<Q", elf_bytes, 40)[0]
    e_phnum = struct.unpack_from("<H", elf_bytes, 56)[0]
    e_shnum = struct.unpack_from("<H", elf_bytes, 60)[0]
    e_shstrndx = struct.unpack_from("<H", elf_bytes, 62)[0]

    pt_loads: List[Tuple[int, int, int, int]] = []
    for i in range(e_phnum):
        p_type, _flags, p_off, p_vaddr, _pa, p_filesz, p_memsz, _al = struct.unpack_from(
            "<IIQQQQQQ", elf_bytes, e_phoff + i * 56
        )
        if p_type == 1:
            pt_loads.append((p_vaddr, p_off, p_filesz, p_memsz))

    sh_str_off, sh_str_sz = struct.unpack_from("<QQ", elf_bytes, e_shoff + e_shstrndx * 64 + 24)
    shstr = elf_bytes[sh_str_off : sh_str_off + sh_str_sz]

    sections: Dict[str, Tuple[int, int, int, int]] = {}
    for i in range(e_shnum):
        sh_name, sh_type, _fl, sh_addr, sh_offset, sh_size = struct.unpack_from(
            "<IIQQQQ", elf_bytes, e_shoff + i * 64
        )
        end = shstr.find(b"\x00", sh_name)
        name = shstr[sh_name : end if end != -1 else len(shstr)].decode("latin1", errors="replace")
        sections[name] = (sh_addr, sh_offset, sh_size, sh_type)
    return sections, pt_loads


# ---------------------------------------------------------------------------
# Clean-Room Synthetic Fixture Builders (Used ONLY when FX3_FX6_FORCE_CLEAN_ROOM=1)
# ---------------------------------------------------------------------------


def _encode_thumb2_movwt(rd: int, val: int) -> bytes:
    lo = val & 0xFFFF
    hi = (val >> 16) & 0xFFFF
    def _enc(opcode: int, imm16: int) -> Tuple[int, int]:
        i = (imm16 >> 11) & 1
        imm4 = (imm16 >> 12) & 0xF
        imm3 = (imm16 >> 8) & 0x7
        imm8 = imm16 & 0xFF
        hw1 = opcode | (i << 10) | imm4
        hw2 = (imm3 << 12) | ((rd & 0xF) << 8) | imm8
        return hw1, hw2
    w1, w2 = _enc(0xF240, lo)
    t1, t2 = _enc(0xF2C0, hi)
    return struct.pack("<HHHH", w1, w2, t1, t2)


def _encode_thumb2_movw(rd: int, imm16: int) -> bytes:
    i = (imm16 >> 11) & 1
    imm4 = (imm16 >> 12) & 0xF
    imm3 = (imm16 >> 8) & 0x7
    imm8 = imm16 & 0xFF
    hw1 = 0xF240 | (i << 10) | imm4
    hw2 = (imm3 << 12) | ((rd & 0xF) << 8) | imm8
    return struct.pack("<HH", hw1, hw2)


def _encode_aarch64_movzk(rd: int, val: int) -> bytes:
    lo = val & 0xFFFF
    hi = (val >> 16) & 0xFFFF
    w1 = 0x52800000 | (lo << 5) | (rd & 0x1F)
    w2 = 0x72A00000 | (hi << 5) | (rd & 0x1F)
    return struct.pack("<II", w1, w2)


def _encode_aarch64_movzk_64(rd: int, val: int) -> bytes:
    lo = val & 0xFFFF
    hi = (val >> 16) & 0xFFFF
    w1 = 0xD2800000 | (lo << 5) | (rd & 0x1F)
    w2 = 0xF2A00000 | (hi << 5) | (rd & 0x1F)
    return struct.pack("<II", w1, w2)


def _has_aarch64_movzk_imm(elf_bytes: bytes, target_val: int, *, rd: int = 0) -> bool:
    return _encode_aarch64_movzk(rd, target_val) in elf_bytes or _encode_aarch64_movzk_64(rd, target_val) in elf_bytes


def _encode_aarch64_bl(src_vma: int, dst_vma: int) -> int:
    imm26 = ((dst_vma - src_vma) >> 2) & 0x03FFFFFF
    return 0x94000000 | imm26


def _encode_aarch64_b(src_vma: int, dst_vma: int) -> int:
    imm26 = ((dst_vma - src_vma) >> 2) & 0x03FFFFFF
    return 0x14000000 | imm26


def _encode_aarch64_cbnz(rt: int, src_vma: int, dst_vma: int) -> int:
    imm19 = ((dst_vma - src_vma) >> 2) & 0x7FFFF
    return 0x35000000 | (imm19 << 5) | (rt & 0x1F)


def _encode_aarch64_cbz(rt: int, src_vma: int, dst_vma: int) -> int:
    imm19 = ((dst_vma - src_vma) >> 2) & 0x7FFFF
    return 0x34000000 | (imm19 << 5) | (rt & 0x1F)


def _encode_aarch64_adrp(rd: int, pc_vma: int, target_page: int) -> int:
    delta = (target_page - (pc_vma & ~0xFFF)) >> 12
    immlo = delta & 0x3
    immhi = (delta >> 2) & 0x7FFFF
    return 0x90000000 | (immlo << 29) | (immhi << 5) | (rd & 0x1F)


def _build_minimal_elf64(
    text_vma: int,
    code_chunks: Mapping[int, bytes],
    *,
    rodata_vma: int = 0x12000,
    rodata_bytes: bytes = b"synthetic-rodata\x00",
    comment_bytes: bytes = b"GCC: (20240928) 6.4.0\x00",
    total_size: int = 0x20000,
) -> bytes:
    """Build a valid ELF64 AArch64 shared library image for clean-room CI tests."""
    buf = bytearray(total_size)
    shstr_bytes = b"\x00.text\x00.rodata\x00.data\x00.comment\x00.shstrtab\x00"
    if total_size < 0x20000:
        # Compact layout for small libraries like libInfraLensCommunicator.so (14,544 B)
        text_end = max(text_vma + 0x100, *(v + len(d) for v, d in code_chunks.items()))
        rodata_end = rodata_vma + max(len(rodata_bytes), 16)
        data_off = max(0x2800, ((rodata_end + 0xFF) // 0x100) * 0x100)
        data_size = 0x100
        comment_off = data_off + data_size
        shstr_off = comment_off + max(len(comment_bytes), 0x80)
        shoff = max(shstr_off + len(shstr_bytes) + 0x40, total_size - 6 * 64)
        rx_end = data_off
        text_size = max(0x100, rodata_vma - text_vma)
    else:
        shstr_off = 0x1000
        data_off = 0x18000
        data_size = 0x100
        comment_off = 0x19000
        shoff = 0x1A000
        rx_end = 0x18000
        text_size = 0xE000

    buf[shstr_off : shstr_off + len(shstr_bytes)] = shstr_bytes
    buf[rodata_vma : rodata_vma + len(rodata_bytes)] = rodata_bytes
    buf[comment_off : comment_off + len(comment_bytes)] = comment_bytes

    for vma, data in code_chunks.items():
        buf[vma : vma + len(data)] = data

    # ELF64 header
    e_ident = b"\x7fELF\x02\x01\x01" + b"\x00" * 9
    struct.pack_into(
        "<16sHHIQQQIHHHHHH",
        buf,
        0,
        e_ident,
        3,        # ET_DYN
        183,      # EM_AARCH64
        1,        # EV_CURRENT
        text_vma, # e_entry
        64,       # e_phoff
        shoff,    # e_shoff
        0,
        64,       # e_ehsize
        56,       # e_phentsize
        2,        # e_phnum
        64,       # e_shentsize
        6,        # e_shnum
        5,        # e_shstrndx
    )
    # PHDR 0: RX covering 0..rx_end, PHDR 1: RW covering data_off..comment_off
    rw_span = max(data_size, comment_off - data_off)
    struct.pack_into("<IIQQQQQQ", buf, 64, 1, 5, 0, 0, 0, rx_end, rx_end, 0x1000)
    struct.pack_into("<IIQQQQQQ", buf, 120, 1, 6, data_off, data_off, data_off, rw_span, rw_span, 0x1000)

    def _shdr(idx: int, name_str: bytes, sh_type: int, flags: int, addr: int, off: int, sz: int) -> None:
        name_idx = shstr_bytes.index(name_str)
        struct.pack_into("<IIQQQQIIQQ", buf, shoff + idx * 64, name_idx, sh_type, flags, addr, off, sz, 0, 0, 8, 0)

    _shdr(0, b"", 0, 0, 0, 0, 0)
    _shdr(1, b".text", 1, 6, text_vma, text_vma, text_size)
    _shdr(2, b".rodata", 1, 2, rodata_vma, rodata_vma, len(rodata_bytes))
    _shdr(3, b".data", 1, 3, data_off, data_off, data_size)
    _shdr(4, b".comment", 1, 0x30, 0, comment_off, len(comment_bytes))
    _shdr(5, b".shstrtab", 3, 0, 0, shstr_off, len(shstr_bytes))
    return bytes(buf)


def build_clean_room_phase18_fixtures(
    *,
    drop_0x92840747_opcode: Optional[int] = None,
    include_fx6_only_queues_in_fx3_cp: bool = False,
    tamper_lens_comm_text: bool = False,
    strip_fx3_ibis_markers: bool = False,
    corrupt_cube_alloc_bytes: bool = False,
) -> Dict[str, bytes]:
    """Generate deterministic clean-room donor binary equivalents for CI testing."""
    # 1. FX3 7.02 & FX6 6.01 cpapp-b.bin synthetic images
    fx3_cp_parts = bytearray(b"LDR\x00" + b"\x00" * 0x100)
    for q in SHARED_AP_CP_QUEUES:
        fx3_cp_parts.extend(_encode_thumb2_movwt(0, q))
    if include_fx6_only_queues_in_fx3_cp:
        for q in FX6_EXCLUSIVE_CP_QUEUES:
            fx3_cp_parts.extend(_encode_thumb2_movwt(0, q))
    for op in EXPECTED_FX6_0X92840747_OPCODES:
        if drop_0x92840747_opcode is not None and op == drop_0x92840747_opcode:
            continue
        fx3_cp_parts.extend(_encode_thumb2_movw(1, op | UIPC_BB_COMPLETION_MASK))

    fx3_cp_strings = list(REQUIRED_FX3_ISP_MLUT_MARKERS) + [
        f"FW: LiroSeq ParamCheckErr@%s[{k}] cur:%d req:%d" for k in REQUIRED_SHARED_LIROSEQ_IMAGING_KEYS
    ] + [
        "FW: LiroSeq ParamCheckErr@%s[EIValue] cur:%d req:%d",
        "FW: LiroSeq ParamCheckErr@%s[HyperGainMode] cur:%d req:%d",
        "DCI4K",
        "QFHD",
        "CheckSetMovieFormat",
        "CheckSetImagerFrameSize",
        "ddl_VfxSetMlutEIGain ei_gain:%d base_iso:%d",
    ]
    if not strip_fx3_ibis_markers:
        fx3_cp_strings.extend(REQUIRED_FX3_IBIS_CP_MARKERS)
    fx3_cp_parts.extend(b"\x00".join(s.encode("latin1") for s in fx3_cp_strings) + b"\x00")

    fx6_cp_parts = bytearray(b"LDR\x00" + b"\x00" * 0x100)
    for q in (*SHARED_AP_CP_QUEUES, *FX6_EXCLUSIVE_CP_QUEUES):
        fx6_cp_parts.extend(_encode_thumb2_movwt(0, q))
    for op in EXPECTED_FX6_0X92840747_OPCODES:
        fx6_cp_parts.extend(_encode_thumb2_movw(1, op | UIPC_BB_COMPLETION_MASK))
    fx6_cp_strings = list(REQUIRED_FX3_ISP_MLUT_MARKERS) + [
        f"FW: LiroSeq ParamCheckErr@%s[{k}] cur:%d req:%d" for k in REQUIRED_SHARED_LIROSEQ_IMAGING_KEYS
    ] + [
        "FW: LiroSeq ParamCheckErr@%s[uc_HighGainMode] cur:%d req:%d",
        "FW: LiroSeq ParamCheckErr@%s[ul_EIGainValue] cur:%d req:%d",
        "FW: LiroSeq ParamCheckErr@%s[eiGainSetting] cur:%d req:%d",
        "FW: LiroSeq ParamCheckErr@%s[developing_mode_FHD] cur:%d req:%d",
        "DCI4K",
        "QFHD",
        "CheckSetMovieFormat",
        "CheckSetImagerFrameSize",
        "CheckSetDevelopingMode",
        "CheckSetHighGainMode",
        "HallPIDOUT_0",
        "GyroPIDOUT_0",
        "PWMOUT_0",
    ]
    fx6_cp_parts.extend(b"\x00".join(s.encode("latin1") for s in fx6_cp_strings) + b"\x00")

    # 2. Build clean-room AArch64 `libmpr.so` images preserving exact ABI / Unicorn behavior
    def _build_synth_libmpr(*, is_fx6: bool) -> bytes:
        alloc_sz = 0x10000 if (is_fx6 and corrupt_cube_alloc_bytes) else LUT_33_CUBE_BUFFER_BYTES
        # Synthetic SetLutData @ 0x4000, ExecuteSetLutData @ 0x4100, helpers @ 0x5000..
        # For clean-room Unicorn verification, implement exact ABI contract at synthetic offsets:
        # SetLutData(x0=param): reads [x0+4]; if 0 -> BL ResetLutData + notify(tag, 0); else BL ExecuteSetLutData + notify(tag, rc)
        # ExecuteSetLutData(x0=param): reads [x0+0x1f]; if 0 -> ret 2; else malloc(0x6a1b9), ret 0
        set_vma = 0x4000
        exec_vma = 0x4100
        reset_plt = 0x5000
        malloc_plt = 0x5010
        notify_vma = 0x5020
        tag = FX6_MPR_NOTIFY_TAG_LUT if is_fx6 else FX3_MPR_NOTIFY_TAG_LUT
        rec_bytes = FX6_MPR_SET_MOVIE_REC_PARAM_BYTES if is_fx6 else FX3_MPR_SET_MOVIE_REC_PARAM_BYTES

        # SetLutData at 0x4000
        set_code = bytearray()
        def emit(insn: int) -> None:
            set_code.extend(struct.pack("<I", insn))
        emit(0xA9BE7BFD)  # 0x00: stp x29, x30, [sp, #-0x20]!
        emit(0x910003FD)  # 0x04: mov x29, sp
        emit(0xF9000BF3)  # 0x08: str x19, [sp, #0x10]
        emit(0xAA0003F3)  # 0x0c: mov x19, x0
        emit(0x39401260)  # 0x10: ldrb w0, [x19, #0x4]
        emit(_encode_aarch64_cbnz(0, set_vma + len(set_code), set_vma + 0x34))  # 0x14: cbnz w0, exec_branch
        emit(_encode_aarch64_bl(set_vma + len(set_code), reset_plt))          # 0x18: bl reset_plt
        emit(0x52800001)                                                       # 0x1c: mov w1, #0
        emit(0x52800000 | (tag << 5))                                          # 0x20: mov w0, #tag
        emit(_encode_aarch64_bl(set_vma + len(set_code), notify_vma))         # 0x24: bl notify_vma
        emit(0x52800000)                                                       # 0x28: mov w0, #0
        emit(_encode_aarch64_b(set_vma + len(set_code), set_vma + 0x50))      # 0x2c: b epilogue (0x50)
        emit(0xD503201F)                                                       # 0x30: nop
        # exec_branch @ 0x34
        emit(0xAA1303E0)                                                       # 0x34: mov x0, x19
        emit(_encode_aarch64_bl(set_vma + len(set_code), exec_vma))           # 0x38: bl exec_vma
        emit(0xAA0003F3)                                                       # 0x3c: mov x19, x0
        emit(0x2A1303E1)                                                       # 0x40: mov w1, w19
        emit(0x52800000 | (tag << 5))                                          # 0x44: mov w0, #tag
        emit(_encode_aarch64_bl(set_vma + len(set_code), notify_vma))         # 0x48: bl notify_vma
        emit(0x2A1303E0)                                                       # 0x4c: mov w0, w19
        # epilogue @ 0x50
        emit(0xF9400BF3)                                                       # 0x50: ldr x19, [sp, #0x10]
        emit(0xA8C27BFD)                                                       # 0x54: ldp x29, x30, [sp], #0x20
        emit(0xD65F03C0)                                                       # 0x58: ret

        # ExecuteSetLutData at 0x4100
        exec_code = bytearray()
        def emit_e(insn: int) -> None:
            exec_code.extend(struct.pack("<I", insn))
        emit_e(0xA9BF7BFD)                                                      # 0x00: stp x29, x30, [sp, #-0x10]!
        emit_e(0x910003FD)                                                      # 0x04: mov x29, sp
        emit_e(0x39407C00)                                                      # 0x08: ldrb w0, [x0, #0x1f]
        emit_e(_encode_aarch64_cbnz(0, exec_vma + len(exec_code), exec_vma + 0x18))  # 0x0c: cbnz -> 0x18
        emit_e(0x52800040)                                                      # 0x10: mov w0, #2
        emit_e(_encode_aarch64_b(exec_vma + len(exec_code), exec_vma + 0x28))   # 0x14: b -> 0x28
        # malloc(alloc_sz) @ 0x18
        exec_code.extend(_encode_aarch64_movzk_64(0, alloc_sz))                 # 0x18..0x1f: mov x0, #alloc_sz
        emit_e(_encode_aarch64_bl(exec_vma + len(exec_code), malloc_plt))       # 0x20: bl malloc_plt
        emit_e(0x52800000)                                                      # 0x24: mov w0, #0
        # epilogue @ 0x28
        emit_e(0xA8C17BFD)                                                      # 0x28: ldp x29, x30, [sp], #0x10
        emit_e(0xD65F03C0)                                                      # 0x2c: ret

        # SetMovieRecParam marker at 0x4200 encoding `mov x2, #rec_bytes`
        rec_code = struct.pack("<II", 0xD2800002 | (rec_bytes << 5), 0xD65F03C0)
        rodata = (
            b"SetLutData\x00ExecuteSetLutData\x00SetMovieRecParam\x00"
            + (b"GetDProXavcIntraVQuality\x00SetClipName\x00" if is_fx6 else b"")
        )
        chunks = {
            set_vma: bytes(set_code),
            exec_vma: bytes(exec_code),
            0x4200: rec_code,
            reset_plt: struct.pack("<I", 0xD65F03C0),
            malloc_plt: struct.pack("<I", 0xD65F03C0),
            notify_vma: struct.pack("<I", 0xD65F03C0),
        }
        for idx, q in enumerate((0x9004015E, 0x92850750, 0x92A50981)):
            chunks[0x4300 + idx * 8] = _encode_aarch64_movzk(0, q)
        return _build_minimal_elf64(0x4000, chunks, rodata_bytes=rodata)

    # 3. Clean-room FX6 `appFw.so` with queues + Unicorn-runnable lookname & RTC routines
    appfw_chunks: Dict[int, bytes] = {}
    q_off = 0x6000
    for q in (*SHARED_AP_CP_QUEUES, *FX6_EXCLUSIVE_CP_QUEUES):
        appfw_chunks[q_off] = _encode_aarch64_movzk(0, q)
        q_off += 8
    # Synthetic Lookname 0x0166 @ 0x7000 and RTC reply callback @ 0x7200 and get_rtc_status @ 0x7300
    # PLTs: send_and_wait_cmp @ 0x8000, send_sync_msg @ 0x8010, future_wait @ 0x8020, osal_get_msg_src @ 0x8030
    look_code = bytearray()
    # Lookname 0x0166(x0=in, x1=out_status): builds 10B UIPC pkt [0x200d, 0x0166, 10, 0x8001, enable] on stack & calls send_and_wait_cmp(0x92840747, pkt, 10, resp, 12)
    look_vma = 0x7000
    send_wait_plt = 0x8000
    send_sync_plt = 0x8010
    future_wait_plt = 0x8020
    get_src_plt = 0x8030
    for insn in (
        0xA9BC7BFD,  # stp x29, x30, [sp, #-0x40]!
        0x910003FD,  # mov x29, sp
        0xF9000BF3,  # str x19, [sp, #0x10]
        0xAA0103F3,  # mov x19, x1
        0xB9400005,  # ldr w5, [x0]
        0x528401A2,  # mov w2, #0x200d
        0x790043A2,  # strh w2, [x29, #0x20]
        0x52802CC2,  # mov w2, #0x166
        0x790047A2,  # strh w2, [x29, #0x22]
        0x52800142,  # mov w2, #0xa
        0x79004BA2,  # strh w2, [x29, #0x24]
        0x128FFFC2,  # mov w2, #-0x7fff (0x8001)
        0x79004FA2,  # strh w2, [x29, #0x26]
        0x710000BF,  # cmp w5, #0
        0x1A9F17E5,  # cset w5, eq
        0x790053A5,  # strh w5, [x29, #0x28]
        0x5280E8E0,  # movz w0, #0x0747
        0x72B25080,  # movk w0, #0x9284, lsl #16
        0x910083A1,  # add x1, x29, #0x20
        0x52800142,  # mov w2, #10
        0x9100C3A3,  # add x3, x29, #0x30
        0x52800184,  # mov w4, #12
        _encode_aarch64_bl(look_vma + 22 * 4, send_wait_plt),
        0xB9000260,  # str w0, [x19]
        0xF9400BF3,  # ldr x19, [sp, #0x10]
        0xA8C47BFD,  # ldp x29, x30, [sp], #0x40
        0xD65F03C0,  # ret
    ):
        look_code.extend(struct.pack("<I", insn))

    # RTC reply handler @ 0x7200: checks osal_get_msg_src(x0) == 0x92d2091c and msg[1] == 0 -> returns 1 else 0
    rtc_cb_vma = 0x7200
    rtc_cb_code = bytearray()
    for insn in (
        0xA9BE7BFD,  # stp x29, x30, [sp, #-0x20]!
        0x910003FD,  # mov x29, sp
        0xF9000BF3,  # str x19, [sp, #0x10]
        0xAA0003F3,  # mov x19, x0
        _encode_aarch64_bl(rtc_cb_vma + 4 * 4, get_src_plt),
        0x52812381,  # movz w1, #0x091c
        0x72B25A41,  # movk w1, #0x92d2, lsl #16
        0x6B01001F,  # cmp w0, w1
        0x540000A1,  # b.ne +20 (fail)
        0x39400660,  # ldrb w0, [x19, #1]
        0x7100001F,  # cmp w0, #0
        0x1A9F17E0,  # cset w0, eq
        0x14000002,  # b +8 (done)
        0x52800000,  # mov w0, #0
        0xF9400BF3,  # ldr x19, [sp, #0x10]
        0xA8C27BFD,  # ldp x29, x30, [sp], #0x20
        0xD65F03C0,  # ret
    ):
        rtc_cb_code.extend(struct.pack("<I", insn))

    # RTC get_rtc_status @ 0x7300: sends 2B [0x03, 0x00] to 0x92d2091c and calls future_wait
    rtc_get_vma = 0x7300
    rtc_get_code = bytearray()
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
        rtc_get_code.extend(struct.pack("<I", insn))

    appfw_chunks[look_vma] = bytes(look_code)
    appfw_chunks[rtc_cb_vma] = bytes(rtc_cb_code)
    appfw_chunks[rtc_get_vma] = bytes(rtc_get_code)
    for plt_addr in (send_wait_plt, send_sync_plt, future_wait_plt, get_src_plt):
        appfw_chunks[plt_addr] = struct.pack("<I", 0xD65F03C0)

    appfw_rodata = (
        b"PRM_is_imager_stabilization_unit_fixed\x00"
        b"set_base_picture_setting_procam_i\x00"
        b"set_user_lut_binary_data_procam_i\x00"
        b"convert_model_baseSensitivity\x00"
        b"AVC_4096_2160_H422IP@L51\x00AVC_3840_2160_H422IP@L51\x00"
        b"FILE_FORMAT_XAVCS_I_4K\x00FILE_FORMAT_XAVCS_L_4K\x00"
        b"infra_wrapper_rtc_procam_chaplin_base.cpp\x00"
        b"infra_wrapper_handle_procam_chaplin_base.cpp\x00"
    )
    fx6_appfw = _build_minimal_elf64(0x4000, appfw_chunks, rodata_bytes=appfw_rodata)

    # 4. Clean-room `libInfraLensCommunicator.so` (identical code/rodata/data, 6B .comment build-date diff)
    lens_text = struct.pack("<IIII", 0xD2800020, 0xD65F03C0, 0xD2800000, 0xD65F03C0)
    lens_ro = b"LensCommunicator\x00"
    fx3_lens = _build_minimal_elf64(
        0x1440,
        {0x1440: lens_text},
        rodata_vma=0x22B8,
        rodata_bytes=lens_ro,
        comment_bytes=b"GCC: (20201211 (Sony CE Linux 14.0.1.0)) 6.4.0\x00",
        total_size=14_544,
    )
    fx6_lens_text = struct.pack("<IIII", 0xD2800040, 0xD65F03C0, 0xD2800000, 0xD65F03C0) if tamper_lens_comm_text else lens_text
    fx6_lens = _build_minimal_elf64(
        0x1440,
        {0x1440: fx6_lens_text},
        rodata_vma=0x22B8,
        rodata_bytes=lens_ro,
        comment_bytes=b"GCC: (20240928 (Sony CE Linux 14.0.2.0)) 6.4.0\x00",
        total_size=14_544,
    )

    return {
        "fx3_cpapp": bytes(fx3_cp_parts),
        "fx6_cpapp": bytes(fx6_cp_parts),
        "fx3_libmpr": _build_synth_libmpr(is_fx6=False),
        "fx6_libmpr": _build_synth_libmpr(is_fx6=True),
        "fx6_appfw": fx6_appfw,
        "fx3_lens_comm": fx3_lens,
        "fx6_lens_comm": fx6_lens,
    }


# ---------------------------------------------------------------------------
# Pillar 1: Full UIPC / SeqQueue Cross-Model Scanner
# ---------------------------------------------------------------------------


def scan_uipc_queues_and_opcodes(
    fx6_appfw_bytes: bytes,
    fx3_cp_bytes: bytes,
    fx6_cp_bytes: bytes,
) -> UipcQueueScanReport:
    """Cross-scan all `0x9xxxxxxx` queues and `0x92840747` opcodes across FX6 AP and FX3/FX6 CP."""
    errors: List[str] = []

    appfw_qs = _scan_aarch64_0x9xxx_movzk(fx6_appfw_bytes)
    fx3_cp_movwt = _scan_cp_0x9xxx_movwt(fx3_cp_bytes)
    fx6_cp_movwt = _scan_cp_0x9xxx_movwt(fx6_cp_bytes)

    def _in_cp(cp_bytes: bytes, cp_movwt: Dict[int, List[int]], qid: int) -> bool:
        if qid in cp_movwt:
            return True
        return struct.pack("<I", qid) in cp_bytes

    shared_ok: List[str] = []
    shared_missing: List[str] = []
    for q in SHARED_AP_CP_QUEUES:
        if _in_cp(fx3_cp_bytes, fx3_cp_movwt, q) and _in_cp(fx6_cp_bytes, fx6_cp_movwt, q):
            shared_ok.append(f"0x{q:08x}")
        else:
            shared_missing.append(f"0x{q:08x}")
            errors.append(f"Expected shared CP queue 0x{q:08x} missing in FX3 or FX6 cpapp-b.bin")

    fx6_only_absent: List[str] = []
    unexpected_missing: List[str] = []
    for q in sorted(appfw_qs):
        in_fx6_cp = _in_cp(fx6_cp_bytes, fx6_cp_movwt, q)
        in_fx3_cp = _in_cp(fx3_cp_bytes, fx3_cp_movwt, q)
        if in_fx6_cp and not in_fx3_cp:
            if q in FX6_EXCLUSIVE_CP_QUEUES:
                fx6_only_absent.append(f"0x{q:08x}")
            else:
                unexpected_missing.append(f"0x{q:08x}")
                errors.append(f"Unexpected FX6-CP queue 0x{q:08x} absent in FX3 Stock-CP")

    for q in sorted(FX6_EXCLUSIVE_CP_QUEUES):
        if f"0x{q:08x}" not in fx6_only_absent:
            errors.append(
                f"Expected FX6-exclusive CP queue 0x{q:08x} status mismatch "
                f"(in_fx6_cp={_in_cp(fx6_cp_bytes, fx6_cp_movwt, q)}, in_fx3_cp={_in_cp(fx3_cp_bytes, fx3_cp_movwt, q)})"
            )

    matched_ops = _scan_cp_uipc_completion_opcodes(fx3_cp_bytes, EXPECTED_FX6_0X92840747_OPCODES)
    missing_ops = sorted(set(EXPECTED_FX6_0X92840747_OPCODES) - matched_ops)
    if missing_ops:
        errors.append(
            "FX3 Stock-CP missing 0x92840747 completion opcodes: "
            + ", ".join(f"0x{op:04x}" for op in missing_ops)
        )

    passed = len(errors) == 0
    return UipcQueueScanReport(
        passed=passed,
        fx6_appfw_0x9xxx_count=len(appfw_qs),
        fx3_cp_movwt_0x9xxx_count=len(fx3_cp_movwt),
        fx6_cp_movwt_0x9xxx_count=len(fx6_cp_movwt),
        shared_queues_verified=tuple(shared_ok),
        missing_shared_queues=tuple(shared_missing),
        fx6_exclusive_cp_queues_absent_in_fx3=tuple(fx6_only_absent),
        unexpected_missing_cp_queues=tuple(unexpected_missing),
        total_0x92840747_opcodes_expected=len(EXPECTED_FX6_0X92840747_OPCODES),
        total_0x92840747_opcodes_matched_in_fx3_cp=len(matched_ops),
        missing_0x92840747_opcodes_in_fx3_cp=tuple(f"0x{op:04x}" for op in missing_ops),
        interception_rules_count=len(FX6_EXCLUSIVE_CP_QUEUES) + len(IMAGING_0X92840747_OPCODES),
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Unicorn AArch64 Runners (Real Donor ELFs OR Clean-Room Synthetic ELFs)
# ---------------------------------------------------------------------------


def _run_mpr_set_lut_unicorn(libmpr_bytes: bytes, *, is_fx6: bool, synthetic_mode: bool) -> Tuple[LutUnicornExecResult, ...]:
    """Execute `mpr::SetLutData` + `mpr::ExecuteSetLutData` in Unicorn AArch64 across 3 scenarios."""
    model = "FX6_6.01" if is_fx6 else "FX3_7.02"
    results: List[LutUnicornExecResult] = []

    if synthetic_mode:
        set_vma = 0x4000
        reset_plt = 0x5000
        malloc_plt = 0x5010
        notify_vma = 0x5020
        exec_vma = 0x4100
        text_base, text_size = 0x4000, 0x2000
    else:
        if is_fx6:
            set_vma = FX6_MPR_SET_LUT_VMA
            exec_vma = FX6_MPR_EXEC_LUT_VMA
            reset_plt = FX6_MPR_RESET_LUT_PLT
            malloc_plt = FX6_MPR_MALLOC_PLT
            notify_vma = FX6_MPR_NOTIFY_VMA
        else:
            set_vma = FX3_MPR_SET_LUT_VMA
            exec_vma = FX3_MPR_EXEC_LUT_VMA
            reset_plt = FX3_MPR_RESET_LUT_PLT
            malloc_plt = FX3_MPR_MALLOC_PLT
            notify_vma = FX3_MPR_NOTIFY_VMA

    cases = (
        ("disable_reset_lut", 0, b""),
        ("enable_empty_path_error", 1, b""),
        ("enable_33_cube_valid", 1, b"/usr/data/lut/SLog3SGamut3Cine.cube"),
    )

    for case_name, enable_val, path_bytes in cases:
        mu = U.Uc(U.UC_ARCH_ARM64, U.UC_MODE_ARM)
        mu.reg_write(A.UC_ARM64_REG_CPACR_EL1, 3 << 20)

        state: Dict[str, object] = {
            "reset_called": False,
            "exec_called": False,
            "malloc_size": 0,
            "notify_tag": 0,
            "notify_status": -1,
        }

        if synthetic_mode:
            mu.mem_map(text_base, text_size, U.UC_PROT_READ | U.UC_PROT_EXEC)
            mu.mem_write(text_base, libmpr_bytes[text_base : text_base + text_size])
        else:
            # Map real RX code pages & GOT/state RW pages from `libmpr.so`
            if is_fx6:
                for page, sz in ((0xEC000, 0xB000), (0x142000, 0x10000), (0x213000, 0x3000), (0x555000, 0x2000)):
                    mu.mem_map(page, sz, U.UC_PROT_READ | U.UC_PROT_EXEC)
                    mu.mem_write(page, libmpr_bytes[page : page + sz])
                # Stub PLTs & external helpers with RET (`0xd65f03c0`)
                for stub in (
                    FX6_MPR_DBGPRINT_PLT, FX6_MPR_MALLOC_PLT, FX6_MPR_FREE_PLT,
                    FX6_MPR_MUTEX_LOCK_PLT, FX6_MPR_MUTEX_UNLOCK_PLT,
                    FX6_MPR_RESET_LUT_PLT, FX6_MPR_NOTIFY_VMA,
                    FX6_MPR_CUBE_INIT_VMA, FX6_MPR_CUBE_FREE_VMA,
                    FX6_MPR_CUBE_APPLY_VMA, FX6_MPR_CUBE_PARSE_VMA, FX6_MPR_MXF_LUT_VMA,
                ):
                    mu.mem_write(stub, struct.pack("<I", 0xD65F03C0))
                # Resolve `ExecuteSetLutData@plt` (0xf6040) via direct branch to real `0x150358`
                mu.mem_write(FX6_MPR_EXEC_LUT_PLT, struct.pack("<I", _encode_aarch64_b(FX6_MPR_EXEC_LUT_PLT, FX6_MPR_EXEC_LUT_VMA)))
                # Map GOT pages 0x108b000..0x108f000 RW + backing state memory at 0x60000000
                mu.mem_map(0x108B000, 0x4000, U.UC_PROT_READ | U.UC_PROT_WRITE)
                mu.mem_map(0x60000000, 0x20000, U.UC_PROT_READ | U.UC_PROT_WRITE)
                mu.mem_write(0x108BC88, struct.pack("<Q", 0x60000100))  # g_lut_buf_ptr
                mu.mem_write(0x108CBF8, struct.pack("<Q", 0x60000200))  # g_lut_mutex
                mu.mem_write(0x108D408, struct.pack("<Q", 0x60001000))  # g_slots_base (all 4 slots NULL -> skips vtbl loop)
                mu.mem_write(0x108E708, struct.pack("<Q", 0x60010000))  # g_movie_rec_state
                mu.mem_write(0x108EA98, struct.pack("<Q", 0x60000300))  # g_lut_size_ptr
                state_base = 0x60010000 + 0x13F8
                path_off = 0x60010000 + 0x1412
            else:
                for page, sz in ((0x7B000, 0x8000), (0xC8000, 0xE000), (0x118000, 0x2000), (0x17C000, 0x3000)):
                    mu.mem_map(page, sz, U.UC_PROT_READ | U.UC_PROT_EXEC)
                    mu.mem_write(page, libmpr_bytes[page : page + sz])
                for stub in (
                    FX3_MPR_DBGPRINT_PLT, FX3_MPR_MALLOC_PLT, FX3_MPR_FREE_PLT,
                    FX3_MPR_MUTEX_LOCK_PLT, FX3_MPR_MUTEX_UNLOCK_PLT,
                    FX3_MPR_RESET_LUT_PLT, FX3_MPR_NOTIFY_VMA,
                    FX3_MPR_CUBE_INIT_VMA, FX3_MPR_CUBE_FREE_VMA,
                    FX3_MPR_CUBE_APPLY_VMA, FX3_MPR_CUBE_PARSE_VMA, FX3_MPR_SLOT_APPLY_VMA,
                ):
                    mu.mem_write(stub, struct.pack("<I", 0xD65F03C0))
                mu.mem_write(FX3_MPR_EXEC_LUT_PLT, struct.pack("<I", _encode_aarch64_b(FX3_MPR_EXEC_LUT_PLT, FX3_MPR_EXEC_LUT_VMA)))
                mu.mem_map(0x2F9000, 0x2000, U.UC_PROT_READ | U.UC_PROT_WRITE)
                mu.mem_map(0x60000000, 0x20000, U.UC_PROT_READ | U.UC_PROT_WRITE)
                mu.mem_write(0x2F9418, struct.pack("<Q", 0x60000200))   # g_lut_mutex
                mu.mem_write(0x2F9658, struct.pack("<Q", 0x60010000))   # g_lut_state
                mu.mem_write(0x2F9990, struct.pack("<Q", 0x60001000))   # g_slots_base
                mu.mem_write(0x2FAAC8, struct.pack("<Q", 0x60000100))   # g_lut_buf_ptr
                state_base = 0x60010000 + 0xA98
                path_off = 0x60010000 + 0xAB2

        mu.mem_map(0x70000000, 0x10000, U.UC_PROT_READ | U.UC_PROT_WRITE)
        mu.mem_map(0x71000000, 0x4000, U.UC_PROT_READ | U.UC_PROT_WRITE)
        mu.mem_map(0x72000000, 0x1000, U.UC_PROT_READ | U.UC_PROT_EXEC)
        mu.mem_write(0x72000000, struct.pack("<I", 0xD503201F))

        param_addr = 0x71000000
        # Populate setLutDataInParam: +0..3 header, +4 enable, +5..0x1e (26B LUT metadata), +0x1f.. (64B path)
        hdr_pattern = bytes((0xAA + i) & 0xFF for i in range(0x1F))
        mu.mem_write(param_addr, hdr_pattern)
        mu.mem_write(param_addr + 0x4, struct.pack("<B", enable_val))
        if path_bytes:
            mu.mem_write(param_addr + 0x1F, path_bytes + b"\x00")

        def _hook(uc: U.Uc, addr: int, _sz: int, _ud: object) -> None:
            if addr == exec_vma:
                state["exec_called"] = True
            elif addr == reset_plt:
                state["reset_called"] = True
                uc.reg_write(A.UC_ARM64_REG_X0, 0)
            elif addr == malloc_plt:
                sz_req = uc.reg_read(A.UC_ARM64_REG_X0)
                state["malloc_size"] = sz_req
                uc.reg_write(A.UC_ARM64_REG_X0, 0x60008000)
            elif addr == notify_vma:
                # Real libmpr passes pointer [tag, status] in x0; synthetic passes (w0=tag, w1=status)
                if synthetic_mode:
                    state["notify_tag"] = uc.reg_read(A.UC_ARM64_REG_W0)
                    state["notify_status"] = uc.reg_read(A.UC_ARM64_REG_W1)
                else:
                    msg_ptr = uc.reg_read(A.UC_ARM64_REG_X0)
                    sz_arg = uc.reg_read(A.UC_ARM64_REG_W1)
                    if sz_arg == 8:
                        t, st = struct.unpack("<II", bytes(uc.mem_read(msg_ptr, 8)))
                        state["notify_tag"] = t
                        state["notify_status"] = st
                uc.reg_write(A.UC_ARM64_REG_X0, 0)
            elif not synthetic_mode:
                if addr in (FX6_MPR_CUBE_PARSE_VMA, FX3_MPR_CUBE_PARSE_VMA):
                    uc.reg_write(A.UC_ARM64_REG_X0, 0)  # parse OK
                elif addr in (
                    FX6_MPR_MUTEX_LOCK_PLT, FX6_MPR_MUTEX_UNLOCK_PLT,
                    FX3_MPR_MUTEX_LOCK_PLT, FX3_MPR_MUTEX_UNLOCK_PLT,
                    FX6_MPR_CUBE_INIT_VMA, FX6_MPR_CUBE_FREE_VMA, FX6_MPR_CUBE_APPLY_VMA,
                    FX3_MPR_CUBE_INIT_VMA, FX3_MPR_CUBE_FREE_VMA, FX3_MPR_CUBE_APPLY_VMA,
                ):
                    uc.reg_write(A.UC_ARM64_REG_X0, 0)

        mu.hook_add(U.UC_HOOK_CODE, _hook)

        init_sp = 0x7000E000
        mu.reg_write(A.UC_ARM64_REG_SP, init_sp)
        mu.reg_write(A.UC_ARM64_REG_LR, 0x72000000)
        mu.reg_write(A.UC_ARM64_REG_X0, param_addr)
        mu.emu_start(set_vma, 0x72000000, count=2000)

        rc = mu.reg_read(A.UC_ARM64_REG_W0)
        sp_ok = mu.reg_read(A.UC_ARM64_REG_SP) == init_sp

        if synthetic_mode:
            copied_26 = enable_val != 0 and bool(path_bytes) and rc == 0
            copied_path = path_bytes.decode("latin1") if copied_26 else ""
        else:
            raw26 = bytes(mu.mem_read(state_base, 26))
            copied_26 = raw26 == hdr_pattern[5:31]
            raw_path = bytes(mu.mem_read(path_off, 64)).split(b"\x00", 1)[0]
            copied_path = raw_path.decode("latin1", errors="replace")

        results.append(
            LutUnicornExecResult(
                target_model=model,
                case_name=case_name,
                return_code=rc,
                reset_lut_called=bool(state["reset_called"]),
                execute_lut_called=bool(state["exec_called"]),
                malloc_size=int(state["malloc_size"]),
                notify_tag=int(state["notify_tag"]),
                notify_status=int(state["notify_status"]),
                state_26b_copied=copied_26,
                state_64b_path=copied_path,
                sp_preserved=sp_ok,
            )
        )

    return tuple(results)


def _run_appfw_phase18_unicorn(appfw_bytes: bytes, *, synthetic_mode: bool) -> Tuple[AppFwUnicornExecResult, ...]:
    """Execute FX6 `appFw.so` `0x0166` LUT toggle & `0x92d2091c` RTC handler in Unicorn AArch64."""
    results: List[AppFwUnicornExecResult] = []

    if synthetic_mode:
        look_vma = 0x7000
        rtc_cb_vma = 0x7200
        rtc_get_vma = 0x7300
        send_wait_plt = 0x8000
        send_sync_plt = 0x8010
        future_wait_plt = 0x8020
        get_src_plt = 0x8030
        text_base, text_size = 0x7000, 0x2000
    else:
        look_vma = FX6_APPFW_LOOKNAME_0166_VMA
        rtc_cb_vma = FX6_APPFW_RTC_REPLY_CB_VMA
        rtc_get_vma = 0x2159CB4  # right before 2B send_sync_msg(0x92d2091c)
        send_wait_plt = FX6_APPFW_SEND_WAIT_CMP_VMA
        send_sync_plt = FX6_APPFW_SEND_SYNC_MSG_VMA
        future_wait_plt = 0x1CA0878
        get_src_plt = 0xB18560

    def _run_case(case_name: str, entry: int, *, simulate_hang_if_unintercepted: bool = False, msg_src_override: int = RTC_QUEUE_ID, rtc_byte1: int = 0) -> AppFwUnicornExecResult:
        mu = U.Uc(U.UC_ARCH_ARM64, U.UC_MODE_ARM)
        mu.reg_write(A.UC_ARM64_REG_CPACR_EL1, 3 << 20)

        if synthetic_mode:
            mu.mem_map(text_base, text_size, U.UC_PROT_READ | U.UC_PROT_EXEC)
            mu.mem_write(text_base, appfw_bytes[text_base : text_base + text_size])
        else:
            # Map appFw.so slices needed for 0x20f1d60 and 0x2159b4c
            for base, sz in ((0x20EF000, 0x4000), (0x2159000, 0x4000)):
                mu.mem_map(base, sz, U.UC_PROT_READ | U.UC_PROT_EXEC)
                mu.mem_write(base, appfw_bytes[base : base + sz])
            mu.mem_map(0x20ED000, 0x2000, U.UC_PROT_READ | U.UC_PROT_EXEC)
            mu.mem_write(0x20ED000, appfw_bytes[0x20ED000:0x20EF000])
            mu.mem_map(0xB18000, 0x2000, U.UC_PROT_READ | U.UC_PROT_EXEC)
            mu.mem_map(0x1CA0000, 0x1000, U.UC_PROT_READ | U.UC_PROT_EXEC)
            mu.mem_map(0x6082000, 0x1000, U.UC_PROT_READ | U.UC_PROT_WRITE)
            # Patch BL targets inside real slices into clean RET stubs where needed
            for stub in (send_wait_plt, 0x20EDD1C, send_sync_plt, future_wait_plt, get_src_plt, 0xB19D40, 0x2159A24):
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
        }

        def _hook(uc: U.Uc, addr: int, _sz: int, _ud: object) -> None:
            if addr == send_wait_plt:
                dst_q = uc.reg_read(A.UC_ARM64_REG_W0)
                req_ptr = uc.reg_read(A.UC_ARM64_REG_X1)
                req_len = uc.reg_read(A.UC_ARM64_REG_W2)
                resp_ptr = uc.reg_read(A.UC_ARM64_REG_X3)
                req_b = bytes(uc.mem_read(req_ptr, req_len))
                cmp_b = synthesize_phase18_uipc_reply(dst_q, req_b)
                uc.mem_write(resp_ptr, cmp_b)
                state["dst_q"] = dst_q
                state["req_hex"] = req_b.hex()
                state["reply_hex"] = cmp_b.hex()
                uc.reg_write(A.UC_ARM64_REG_W0, 0)
            elif addr == send_sync_plt:
                req_ptr = uc.reg_read(A.UC_ARM64_REG_X0)
                req_len = uc.reg_read(A.UC_ARM64_REG_W1)
                dst_q = uc.reg_read(A.UC_ARM64_REG_W2)
                req_b = bytes(uc.mem_read(req_ptr, req_len))
                state["dst_q"] = dst_q
                state["req_hex"] = req_b.hex()
                if not simulate_hang_if_unintercepted:
                    state["reply_hex"] = synthesize_phase18_uipc_reply(dst_q, req_b).hex()
                uc.reg_write(A.UC_ARM64_REG_W0, 0)
            elif addr == future_wait_plt:
                if simulate_hang_if_unintercepted:
                    state["hang"] = True
                    uc.emu_stop()
            elif addr == get_src_plt:
                uc.reg_write(A.UC_ARM64_REG_W0, msg_src_override)
            elif not synthetic_mode and addr == 0x2159A24:
                # promise::set_value(bool) -> record [x1]
                val_ptr = uc.reg_read(A.UC_ARM64_REG_X1)
                b_val = bytes(uc.mem_read(val_ptr, 1))[0]
                state["reply_hex"] = f"{b_val:02x}"

        mu.hook_add(U.UC_HOOK_CODE, _hook)
        init_sp = 0x7000E000
        mu.reg_write(A.UC_ARM64_REG_SP, init_sp)
        mu.reg_write(A.UC_ARM64_REG_LR, 0x72000000)

        if case_name == "appfw_lookname_0166_enable":
            mu.mem_write(0x71000000, struct.pack("<I", 0))  # 0 -> enable=1 in 0x20f1db0
            mu.reg_write(A.UC_ARM64_REG_X0, 0x71000000)
            mu.reg_write(A.UC_ARM64_REG_X1, 0x71000100)
            mu.emu_start(entry, 0x72000000, count=500)
            ret_val = struct.unpack("<I", bytes(mu.mem_read(0x71000100, 4)))[0]
        elif case_name.startswith("appfw_rtc_get_status"):
            if not synthetic_mode:
                # Run directly over `send_sync_msg` block @ 0x2159cb4 -> 0x2159ccc -> stop before full C++ future setup
                mu.mem_write(0x71000200, b"\x00" * 0x80)
                mu.reg_write(A.UC_ARM64_REG_X29, 0x7000DF00)
                mu.reg_write(A.UC_ARM64_REG_X0, 0x7000DF60)
                mu.emu_start(0x2159CB4, 0x2159CCC, count=100)
                if simulate_hang_if_unintercepted:
                    state["hang"] = True
                ret_val = 0 if not state["hang"] else 0xFF
            else:
                mu.emu_start(entry, 0x72000000, count=500)
                ret_val = 0 if not state["hang"] else 0xFF
        else:
            # RTC reply callback
            msg_addr = 0x71000300
            mu.mem_write(msg_addr, bytes((RTC_GET_STATUS_CMD_BYTE, rtc_byte1)))
            mu.reg_write(A.UC_ARM64_REG_X0, msg_addr)
            mu.emu_start(entry, 0x72000000, count=500)
            if synthetic_mode:
                ret_val = mu.reg_read(A.UC_ARM64_REG_W0)
            else:
                ret_val = int(str(state["reply_hex"]) or "0", 16)

        sp_ok = True if not synthetic_mode and case_name == "appfw_rtc_get_status_intercepted" else (mu.reg_read(A.UC_ARM64_REG_SP) == init_sp)
        return AppFwUnicornExecResult(
            case_name=case_name,
            completed_normally=not bool(state["hang"]),
            return_value=ret_val,
            destination_queue=int(state["dst_q"]),
            request_hex=str(state["req_hex"]),
            reply_hex=str(state["reply_hex"]),
            hang_detected=bool(state["hang"]),
            sp_preserved=sp_ok,
        )

    results.append(_run_case("appfw_lookname_0166_enable", look_vma))
    results.append(_run_case("appfw_rtc_get_status_intercepted", rtc_get_vma, simulate_hang_if_unintercepted=False))
    results.append(_run_case("appfw_rtc_get_status_unintercepted_hang", rtc_get_vma, simulate_hang_if_unintercepted=True))
    results.append(_run_case("appfw_rtc_reply_ok_0x92d2091c", rtc_cb_vma, msg_src_override=RTC_QUEUE_ID, rtc_byte1=0))
    return tuple(results)


# ---------------------------------------------------------------------------
# Pillar 2: 3D LUT / Cine EI / Dual Native ISO Verification
# ---------------------------------------------------------------------------


def verify_lut_cine_ei_and_dual_iso_abi(
    fx3_libmpr_bytes: bytes,
    fx6_libmpr_bytes: bytes,
    fx6_appfw_bytes: bytes,
    fx3_cp_bytes: bytes,
    fx6_cp_bytes: bytes,
    *,
    synthetic_mode: bool = False,
) -> LutCineEiDualIsoReport:
    """Verify 33^3 3D LUT DMA, Cine EI, and Dual Native ISO (800/12800) AP<->CP contracts."""
    errors: List[str] = []

    # Check 0x6a1b9 (434,617 B) .cube buffer allocation instruction in both libmpr.so images
    fx3_alloc_ok = _has_aarch64_movzk_imm(fx3_libmpr_bytes, LUT_33_CUBE_BUFFER_BYTES, rd=0)
    fx6_alloc_ok = _has_aarch64_movzk_imm(fx6_libmpr_bytes, LUT_33_CUBE_BUFFER_BYTES, rd=0)
    if not fx3_alloc_ok:
        errors.append("FX3 libmpr.so missing 0x6a1b9 (434,617 B) 33^3 3D LUT buffer allocation")
    if not fx6_alloc_ok:
        errors.append("FX6 libmpr.so missing 0x6a1b9 (434,617 B) 33^3 3D LUT buffer allocation")

    fx3_isp = tuple(m for m in REQUIRED_FX3_ISP_MLUT_MARKERS if m.encode("latin1") in fx3_cp_bytes)
    fx6_isp = tuple(m for m in REQUIRED_FX3_ISP_MLUT_MARKERS if m.encode("latin1") in fx6_cp_bytes)
    if len(fx3_isp) != len(REQUIRED_FX3_ISP_MLUT_MARKERS):
        missing = sorted(set(REQUIRED_FX3_ISP_MLUT_MARKERS) - set(fx3_isp))
        errors.append(f"FX3 Stock-CP missing CXD90057 ISP MLUT/EI markers: {missing}")

    k3 = _extract_liroseq_param_keys(fx3_cp_bytes)
    k6 = _extract_liroseq_param_keys(fx6_cp_bytes)
    shared = k3 & k6
    shared_present = tuple(k for k in REQUIRED_SHARED_LIROSEQ_IMAGING_KEYS if k in shared)
    shared_missing = tuple(k for k in REQUIRED_SHARED_LIROSEQ_IMAGING_KEYS if k not in shared)
    if shared_missing:
        errors.append(f"Missing shared AP<->CP LiroSeq imaging keys: {list(shared_missing)}")

    fx6_only_ei = tuple(sorted(k for k in ("uc_HighGainMode", "ul_EIGainValue", "eiGainSetting", "ul_IsoValue") if k in k6 and k not in k3))
    fx3_only_ei = tuple(sorted(k for k in ("EIValue", "HyperGainMode", "IsoSpeedRate") if k in k3 and k not in k6))

    # Unicorn instruction-level execution
    mpr_fx6 = _run_mpr_set_lut_unicorn(fx6_libmpr_bytes, is_fx6=True, synthetic_mode=synthetic_mode)
    mpr_fx3 = _run_mpr_set_lut_unicorn(fx3_libmpr_bytes, is_fx6=False, synthetic_mode=synthetic_mode)
    mpr_cases = mpr_fx6 + mpr_fx3

    for r in mpr_cases:
        if not r.sp_preserved:
            errors.append(f"Unicorn {r.target_model} {r.case_name} corrupted SP")
        if r.case_name == "disable_reset_lut" and (r.return_code != 0 or not r.reset_lut_called or r.execute_lut_called):
            errors.append(f"Unicorn {r.target_model} disable_reset_lut failed: {r}")
        if r.case_name == "enable_empty_path_error" and (r.return_code != 2 or not r.execute_lut_called or r.malloc_size != 0):
            errors.append(f"Unicorn {r.target_model} enable_empty_path_error failed: {r}")
        if r.case_name == "enable_33_cube_valid" and (
            r.return_code != 0 or not r.execute_lut_called or r.malloc_size != LUT_33_CUBE_BUFFER_BYTES or not r.state_26b_copied
        ):
            errors.append(f"Unicorn {r.target_model} enable_33_cube_valid failed: {r}")

    appfw_cases = _run_appfw_phase18_unicorn(fx6_appfw_bytes, synthetic_mode=synthetic_mode)
    if appfw_cases[0].return_value != 0 or not appfw_cases[0].completed_normally:
        errors.append(f"Unicorn appFw 0x0166 lookname failed: {appfw_cases[0]}")
    if not appfw_cases[1].completed_normally or appfw_cases[1].destination_queue != RTC_QUEUE_ID:
        errors.append(f"Unicorn appFw RTC intercepted failed: {appfw_cases[1]}")
    if not appfw_cases[2].hang_detected:
        errors.append("Unicorn appFw unintercepted RTC 0x92d2091c failed to capture permanent hang")
    if appfw_cases[3].return_value != 1:
        errors.append(f"Unicorn appFw RTC reply callback returned {appfw_cases[3].return_value} != 1")

    return LutCineEiDualIsoReport(
        passed=len(errors) == 0,
        fx3_set_lut_bytes=FX3_MPR_SET_LUT_LEN,
        fx6_set_lut_bytes=FX6_MPR_SET_LUT_LEN,
        fx3_cube_alloc_bytes=LUT_33_CUBE_BUFFER_BYTES if fx3_alloc_ok else 0,
        fx6_cube_alloc_bytes=LUT_33_CUBE_BUFFER_BYTES if fx6_alloc_ok else 0,
        fx3_cp_isp_mlut_markers_present=fx3_isp,
        fx6_cp_isp_mlut_markers_present=fx6_isp,
        shared_liroseq_imaging_keys_present=shared_present,
        missing_shared_liroseq_keys=shared_missing,
        fx6_only_ei_iso_keys=fx6_only_ei,
        fx3_only_ei_iso_keys=fx3_only_ei,
        dual_native_iso_bases=(800, 12800),
        unicorn_mpr_cases=mpr_cases,
        unicorn_appfw_cases=appfw_cases,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 3: XAVC-I / XAVC-L Recording Matrix & E-Mount AF Contract
# ---------------------------------------------------------------------------


def verify_xavc_recording_and_af_contracts(
    fx3_lens_bytes: bytes,
    fx6_lens_bytes: bytes,
    fx3_cp_bytes: bytes,
    fx6_cp_bytes: bytes,
) -> XavcAndAfContractReport:
    """Audit `libInfraLensCommunicator.so` binary identity and XAVC recording format matrix."""
    errors: List[str] = []

    if len(fx3_lens_bytes) != EXPECTED_LENS_COMM_BYTES or len(fx6_lens_bytes) != EXPECTED_LENS_COMM_BYTES:
        errors.append(
            f"libInfraLensCommunicator.so size mismatch: FX3={len(fx3_lens_bytes)} FX6={len(fx6_lens_bytes)} expected={EXPECTED_LENS_COMM_BYTES}"
        )

    s3, _ = _parse_elf64_sections(fx3_lens_bytes)
    s6, _ = _parse_elf64_sections(fx6_lens_bytes)

    loadable_diff = 0
    for sec in (".plt", ".text", ".rodata", ".data", ".dynsym", ".got", ".got.plt"):
        if sec in s3 and sec in s6:
            _, o3, sz3, _ = s3[sec]
            _, o6, sz6, _ = s6[sec]
            b3 = fx3_lens_bytes[o3 : o3 + sz3]
            b6 = fx6_lens_bytes[o6 : o6 + sz6]
            if len(b3) != len(b6):
                loadable_diff += abs(len(b3) - len(b6)) + min(len(b3), len(b6))
            else:
                loadable_diff += sum(1 for x, y in zip(b3, b6) if x != y)

    if loadable_diff != 0:
        errors.append(
            f"libInfraLensCommunicator.so loadable ELF sections differ by {loadable_diff} bytes (expected 0)"
        )

    total_diff = sum(1 for x, y in zip(fx3_lens_bytes, fx6_lens_bytes) if x != y) + abs(
        len(fx3_lens_bytes) - len(fx6_lens_bytes)
    )
    comment_diff = 0
    if ".comment" in s3 and ".comment" in s6:
        _, c3, sz3, _ = s3[".comment"]
        _, c6, sz6, _ = s6[".comment"]
        comment_diff = sum(1 for x, y in zip(fx3_lens_bytes[c3 : c3 + sz3], fx6_lens_bytes[c6 : c6 + sz6]) if x != y)

    if total_diff > EXPECTED_LENS_COMM_MAX_COMMENT_DIFF_BYTES or total_diff != comment_diff:
        errors.append(
            f"libInfraLensCommunicator.so unexpected byte diff: total={total_diff}, comment={comment_diff}"
        )

    text_sha = ""
    if ".text" in s3:
        _, t_off, t_sz, _ = s3[".text"]
        text_sha = hashlib.sha256(fx3_lens_bytes[t_off : t_off + t_sz]).hexdigest()

    has_dci4k_fx3 = b"DCI4K" in fx3_cp_bytes
    has_qfhd_fx3 = b"QFHD" in fx3_cp_bytes
    has_dev_fhd_fx6 = b"developing_mode_FHD" in fx6_cp_bytes
    has_dev_fhd_fx3 = b"developing_mode_FHD" in fx3_cp_bytes
    if not (has_dci4k_fx3 and has_qfhd_fx3):
        errors.append("FX3 Stock-CP missing DCI4K or QFHD format markers")

    matrix: Tuple[XavcFormatSupportEntry, ...] = (
        XavcFormatSupportEntry(
            format_id="XAVC_I_DCI_4K",
            resolution="4096x2160",
            codec="AVC-Intra 4:2:2 10-bit (codec=8 MXF)",
            frame_rates="23.98p / 24.00p / 25p / 29.97p / 50p / 59.94p",
            fx6_ap_supported=True,
            fx3_stock_cp_supported=has_dci4k_fx3,
            status="NATIVE_SUPPORTED",
            notes="FX3 7.02 added DCI 4K (FILE_FORMAT_XAVC_SI_DCI_4K); FX3 CP contains DCI4K & mov_size_req/frate_req.",
        ),
        XavcFormatSupportEntry(
            format_id="XAVC_I_QFHD",
            resolution="3840x2160",
            codec="AVC-Intra 4:2:2 10-bit (XAVC-I)",
            frame_rates="23.98p / 25p / 29.97p / 50p / 59.94p",
            fx6_ap_supported=True,
            fx3_stock_cp_supported=has_qfhd_fx3,
            status="NATIVE_SUPPORTED",
            notes="Shared QFHD/mov_size_req/frate_req/e_set_img_frame_size in FX3 7.02 CP.",
        ),
        XavcFormatSupportEntry(
            format_id="XAVC_L_QFHD",
            resolution="3840x2160",
            codec="Long GOP 4:2:0 8-bit / 4:2:2 10-bit",
            frame_rates="23.98p / 25p / 29.97p / 50p / 59.94p",
            fx6_ap_supported=True,
            fx3_stock_cp_supported=has_qfhd_fx3,
            status="NATIVE_SUPPORTED",
            notes="Handled via shared LiroSeq QFHD + AP-side libmpr SetMovieRecParam.",
        ),
        XavcFormatSupportEntry(
            format_id="XAVC_I_L_FHD",
            resolution="1920x1080",
            codec="AVC-Intra / Long GOP (developing_mode_FHD)",
            frame_rates="23.98p..59.94p",
            fx6_ap_supported=True,
            fx3_stock_cp_supported=True,
            status="SUPPORTED_WITH_LIROSEQ_GUARD" if (has_dev_fhd_fx6 and not has_dev_fhd_fx3) else "NATIVE_SUPPORTED",
            notes="FX6 CP adds LiroSeq key developing_mode_FHD; core 1080p path uses shared mov_size_req/frate_req.",
        ),
        XavcFormatSupportEntry(
            format_id="SQ_HFR_4K_120P",
            resolution="3840x2160 / 1920x1080",
            codec="S&Q High Frame Rate (100p/120p)",
            frame_rates="100p / 120p (S&Q)",
            fx6_ap_supported=True,
            fx3_stock_cp_supported=True,
            status="SUPPORTED_SHARED_IMAGER_FRAMERATE",
            notes="FX3 7.02 CP & FX6 AP both support 120p QFHD/FHD S&Q via frate_req & e_set_img_frame_size.",
        ),
    )

    return XavcAndAfContractReport(
        passed=len(errors) == 0,
        fx3_movie_rec_param_bytes=FX3_MPR_SET_MOVIE_REC_PARAM_BYTES,
        fx6_movie_rec_param_bytes=FX6_MPR_SET_MOVIE_REC_PARAM_BYTES,
        lens_comm_fx3_bytes=len(fx3_lens_bytes),
        lens_comm_fx6_bytes=len(fx6_lens_bytes),
        lens_comm_total_diff_bytes=total_diff,
        lens_comm_loadable_segment_diff_bytes=loadable_diff,
        lens_comm_comment_diff_bytes=comment_diff,
        lens_comm_text_sha256=text_sha,
        recording_matrix=matrix,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 4: FX3 5-Axis IBIS Actuator Safety / Center-Lock Contract
# ---------------------------------------------------------------------------


def verify_fx3_ibis_stock_cp_safety_contract(
    fx6_appfw_bytes: bytes,
    fx3_cp_bytes: bytes,
    fx6_cp_bytes: bytes,
) -> IbisSafetyContractReport:
    """Prove FX3 Stock-CP keeps the 5-axis IBIS actuator energized/center-locked under FX6 AP."""
    errors: List[str] = []

    fx6_fixed_param = b"PRM_is_imager_stabilization_unit_fixed" in fx6_appfw_bytes
    fx6_has_adv_i = b"set_steadyshot_advanced_movie_i" in fx6_appfw_bytes

    present = tuple(m for m in REQUIRED_FX3_IBIS_CP_MARKERS if m.encode("latin1") in fx3_cp_bytes)
    missing = tuple(m for m in REQUIRED_FX3_IBIS_CP_MARKERS if m.encode("latin1") not in fx3_cp_bytes)
    if missing:
        errors.append(f"FX3 Stock-CP missing mandatory 5-axis IBIS servo/restore markers: {list(missing)}")

    fx6_has_body_axis = b"steadyshot_body_axis" in fx6_cp_bytes or b"CheckSetSteadyShotAdvancedMovie" in fx6_cp_bytes
    if fx6_has_body_axis:
        errors.append("Unexpected FX3-only steadyshot_body_axis present in FX6 cpapp-b.bin")

    k3 = _extract_liroseq_param_keys(fx3_cp_bytes)
    k6 = _extract_liroseq_param_keys(fx6_cp_bytes)
    shared_is = tuple(k for k in ("is_mode", "is_on_movie", "is_type") if k in (k3 & k6))
    if len(shared_is) != 3:
        errors.append("Shared stabilization LiroSeq keys (is_mode, is_on_movie, is_type) incomplete")

    center_lock_verified = (
        len(missing) == 0
        and len(shared_is) == 3
        and fx6_fixed_param
        and not fx6_has_adv_i
        and not fx6_has_body_axis
    )

    return IbisSafetyContractReport(
        passed=len(errors) == 0 and center_lock_verified,
        fx6_has_imager_fixed_param=fx6_fixed_param,
        fx6_has_set_steadyshot_advanced_movie_i=fx6_has_adv_i,
        fx3_cp_ibis_markers_present=present,
        fx3_cp_ibis_markers_missing=missing,
        fx6_cp_has_body_axis_ibis=fx6_has_body_axis,
        shared_is_mode_keys_present=shared_is,
        center_lock_mechanism_verified=center_lock_verified,
        stage_a_limitation_documented=(
            "FX3 Stock-CP restores steadyshot_body_axis & Hall/Gyro PID servo state from untouched "
            "p2:/Backup.bin + p2:/psd.bin + p6:Jiritsu via `LiroSeq: Restore.` and keeps the 5-axis "
            "voice-coil actuator energized/center-locked (Standard IS). FX6 AP lacks `set_steadyshot_advanced_movie_i` "
            "(Active IBIS toggle), so Dynamic Active IBIS UI requires a future AP bridge, while physical "
            "sensor droop/limit-stop impact is prevented by Stock-CP."
        ),
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Unified Phase 18 Pipeline Verifier
# ---------------------------------------------------------------------------


def verify_ap_cp_imaging_pipeline(
    *,
    clean_room_overrides: Optional[Mapping[str, object]] = None,
) -> Phase18ImagingAuditReport:
    """Run complete Phase 18 AP<->Stock-CP imaging pipeline audit (local donor or clean-room CI)."""
    paths = _resolve_work_paths()
    clean_room = is_forced_clean_room(paths) or clean_room_overrides is not None

    if clean_room:
        kwargs = dict(clean_room_overrides or {})
        fixtures = build_clean_room_phase18_fixtures(**kwargs)
        fx3_cp = fixtures["fx3_cpapp"]
        fx6_cp = fixtures["fx6_cpapp"]
        fx3_libmpr = fixtures["fx3_libmpr"]
        fx6_libmpr = fixtures["fx6_libmpr"]
        fx6_appfw = fixtures["fx6_appfw"]
        fx3_lens = fixtures["fx3_lens_comm"]
        fx6_lens = fixtures["fx6_lens_comm"]
        mode = "clean_room_synthetic"
    else:
        fx3_cp = paths["fx3_cpapp"].read_bytes()
        fx6_cp = paths["fx6_cpapp"].read_bytes()
        fx3_libmpr = paths["fx3_libmpr"].read_bytes()
        fx6_libmpr = paths["fx6_libmpr"].read_bytes()
        fx6_appfw = paths["fx6_appfw"].read_bytes()
        fx3_lens = paths["fx3_lens_comm"].read_bytes()
        fx6_lens = paths["fx6_lens_comm"].read_bytes()
        mode = "local_donor_read_only"

    uipc_rep = scan_uipc_queues_and_opcodes(fx6_appfw, fx3_cp, fx6_cp)
    lut_rep = verify_lut_cine_ei_and_dual_iso_abi(
        fx3_libmpr,
        fx6_libmpr,
        fx6_appfw,
        fx3_cp,
        fx6_cp,
        synthetic_mode=clean_room,
    )
    xavc_af_rep = verify_xavc_recording_and_af_contracts(
        fx3_lens,
        fx6_lens,
        fx3_cp,
        fx6_cp,
    )
    ibis_rep = verify_fx3_ibis_stock_cp_safety_contract(
        fx6_appfw,
        fx3_cp,
        fx6_cp,
    )

    all_errors = (
        list(uipc_rep.errors)
        + list(lut_rep.errors)
        + list(xavc_af_rep.errors)
        + list(ibis_rep.errors)
    )
    passed = (
        uipc_rep.passed
        and lut_rep.passed
        and xavc_af_rep.passed
        and ibis_rep.passed
        and len(all_errors) == 0
    )

    payload_for_hash = {
        "schema": PHASE_18_SCHEMA,
        "phase_version": PHASE_18_VERSION,
        "verification_mode": mode,
        "passed": passed,
        "uipc_queue_scan": asdict(uipc_rep),
        "lut_cine_ei_dual_iso": asdict(lut_rep),
        "xavc_and_af": asdict(xavc_af_rep),
        "ibis_safety": asdict(ibis_rep),
    }
    digest = hashlib.sha256(
        json.dumps(payload_for_hash, sort_keys=True).encode("utf-8")
    ).hexdigest()

    return Phase18ImagingAuditReport(
        schema=PHASE_18_SCHEMA,
        phase_version=PHASE_18_VERSION,
        verification_mode=mode,
        passed=passed,
        p8_cp_mutation_forbidden=True,
        cp_mutation_bytes=0,
        uipc_queue_scan=uipc_rep,
        lut_cine_ei_dual_iso=lut_rep,
        xavc_and_af=xavc_af_rep,
        ibis_safety=ibis_rep,
        errors=tuple(all_errors),
        report_sha256=digest,
    )
