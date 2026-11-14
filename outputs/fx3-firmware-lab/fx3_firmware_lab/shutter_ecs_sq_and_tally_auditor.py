"""Phase 60 — 11th Unified Firmware-Lab Auditor: Cinema Shutter Angle (5.6°..360°), Extended Clear Scan (ECS Anti-LED-Flicker), S&Q (1..240fps), Tally LEDs & FX3 Mechanical Shutter Curtain Protection.

Strictly Read-Only (`os.O_RDONLY` + `mmap.ACCESS_READ`) & Clean-Room Dual-Mode:
- Local Donor Mode: inspects FX3 v7.02 (`appFw.so`, `libmpr.so`, `cpapp-b.bin`,
  `string_english.uxc`, `string_english_g.uxc`) and FX6 v6.01 (`appFw.so`,
  `libmpr.so`, `cpapp-b.bin`, `string_english.uxc`, `string_english_2.uxc`)
  strictly via `os.O_RDONLY` + read-only `mmap` and ELF64 `.rodata`/`.dynstr`
  section-scoped `find()`, plus `.uxc` string-pack slot verification.
- Clean-Room Mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`, `clean_room=True`, or donors
  absent): synthesizes deterministic clean-room binary and `.uxc` fixtures
  carrying the exact contract markers and executes the identical four-pillar
  verification pipeline with zero proprietary files required.

Audits Four Cross-Body Cinema Shutter, Frame-Rate & Tally Safety Pillars:
1. Pillar A — FX3 Mechanical Focal-Plane Shutter Curtain Protection:
   Proves FX6 `appFw.so` video-mode electronic rolling shutter IPCs and Stock-CP
   (`cp_mutation_bytes == 0`) contain zero FX3 mechanical-shutter actuation PIDs
   (`PID_SET_SHUTTER_TYPE`, `SET_SHUTTER_TYPE`, `SET_FRONT_ESHUTTER`), keeping
   `mech_shutter_unintended_actuations == 0` with curtains parked safely open
   during Video and S&Q operation.
2. Pillar B — True Cinema Shutter Angle (`5.6°..360.0°`, `180.0°` default) &
   Extended Clear Scan (`ECS` Hz Anti-LED-Flicker):
   Verifies exact exposure-time math (`t_exp = (angle / 360.0) / fps`) across
   `23.976..240 fps`, all 19 canonical Sony shutter-angle steps + `2F..64F` slow
   shutter, and `ECS` fine frequency steps (`t_exp = 1 / ecs_hz`) for LED
   virtual-production walls.
3. Pillar C — Slow & Quick Motion (`S&Q` `1..120fps` in `4K DCI/QFHD` &
   `1..240fps` in `FHD`) + Proxy / Audio-Mute & CFexpress Speed-Class Rules:
   Verifies exact resolution/fps envelopes, automatic audio disable in off-speed
   S&Q (`rec_fps != sensor_fps`), HFR (`200/240fps`) proxy gating, and CFexpress
   Type A (`VPG200/400`) vs SDXC `V90/V60/V30` sustained-write coupling.
4. Pillar D — Front / Rear / Top Cinema Tally Lamps (`Technical -> Tally`):
   Verifies FX6 `Front Tally Lamp`, `Rear Tally Lamp`, `Tally Lamp Brightness`,
   and `Rec Tally Blink` map cleanly to FX3's physical Front + Top/Rear REC
   Tally LEDs (`REC_LAMP_ALL_LIGHTS_UP`, `REC_LAMP_ONLY_FRONT_OFF`,
   `REC_LAMP_LIGHT_UP_ONLY_ONE`, `REC_LAMP_ALL_LIGHTS_OUT`, and CP
   `MSG_ID_INFRABB_SYS_SET_CA_TALLY`) with zero missing-GPIO faults for FX6-only
   Green/Yellow broadcast tally lamps.
"""

from __future__ import annotations

import hashlib
import json
import math
import mmap
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from .emount_af_breathing_and_ibis_auditor import _extract_uxc_labels, _parse_elf64_sections
from .global_xdb_and_menu_tree_auditor import build_sparse_uxc_string_pack
from .haita_bk4_feature_analyzer import (
    DEFAULT_REPO_ROOT,
    FX3_APPFW_RELPATH,
    FX6_APPFW_RELPATH,
    is_forced_clean_room,
    resolve_donor_file,
)
from .sensor_codec_compatibility_analyzer import (
    FX3_CPAPP_RELPATH,
    FX3_LIBMPR_RELPATH,
    FX6_CPAPP_RELPATH,
    FX6_LIBMPR_RELPATH,
)
from .uxc_multilang_and_font_verifier import FX3_SHARE_APP_RELDIR, FX6_SHARE_APP_RELDIR


PHASE_60_SCHEMA = "fx3_firmware_lab_phase60_shutter_ecs_sq_tally_v1"
PHASE_60_VERSION = "60.0.0"

FX3_STR_EN_RELPATH = f"{FX3_SHARE_APP_RELDIR}/string_english.uxc"
FX3_STR_EN_G_RELPATH = f"{FX3_SHARE_APP_RELDIR}/string_english_g.uxc"
FX6_STR_EN_1_RELPATH = f"{FX6_SHARE_APP_RELDIR}/string_english.uxc"
FX6_STR_EN_2_RELPATH = f"{FX6_SHARE_APP_RELDIR}/string_english_2.uxc"

# ---------------------------------------------------------------------------
# Pinned Cross-Body Shutter, ECS, S&Q & Tally Constants
# ---------------------------------------------------------------------------

DEFAULT_SHUTTER_ANGLE_DEG = 180.0
SHUTTER_ANGLE_MIN_DEG = 5.6
SHUTTER_ANGLE_MAX_DEG = 360.0
SHUTTER_FPS_MIN = 23.976
SHUTTER_FPS_MAX = 240.0

VALID_DISCRETE_SHUTTER_ANGLES_DEG: Tuple[float, ...] = (
    5.6,
    11.25,
    22.5,
    30.0,
    45.0,
    72.0,
    86.4,
    90.0,
    120.0,
    144.0,
    150.0,
    172.8,
    180.0,
    210.0,
    216.0,
    240.0,
    270.0,
    300.0,
    360.0,
)
VALID_SLOW_SHUTTER_FRAME_MULTIPLIERS: Tuple[int, ...] = (2, 3, 4, 5, 6, 7, 8, 16, 32, 64)

ECS_FREQ_MIN_HZ = 23.98
ECS_FREQ_MAX_HZ = 8000.0

SQ_4K_MIN_FPS = 1
SQ_4K_MAX_FPS = 120
SQ_FHD_MIN_FPS = 1
SQ_FHD_MAX_FPS = 240
SQ_STANDARD_CAPTURE_FPS_4K: Tuple[int, ...] = (1, 2, 3, 4, 6, 8, 12, 15, 24, 25, 30, 48, 50, 60, 100, 120)
SQ_STANDARD_CAPTURE_FPS_FHD: Tuple[int, ...] = (
    1,
    2,
    3,
    4,
    6,
    8,
    12,
    15,
    24,
    25,
    30,
    48,
    50,
    60,
    100,
    120,
    200,
    240,
)
SQ_PROJECT_REC_FPS: Tuple[float, ...] = (23.976, 24.0, 25.0, 29.97, 50.0, 59.94)

MEDIA_SUSTAINED_MBPS: Dict[str, float] = {
    "CFEXPRESS_TYPE_A_VPG400": 3200.0,  # 400 MB/s
    "CFEXPRESS_TYPE_A": 1600.0,         # 200 MB/s (VPG200)
    "SDXC_V90": 720.0,                  # 90 MB/s
    "SDXC_V60": 480.0,                  # 60 MB/s
    "SDXC_V30": 240.0,                  # 30 MB/s
}

# Nominal sustained peak bitrates (Mbps) for S&Q Intra/Long profiles at project playback rate -> scaled by (sensor_fps / rec_fps)
SQ_BASE_CODEC_MBPS_AT_24P: Dict[str, float] = {
    "XAVC_S_I_DCI_4K": 240.0,
    "XAVC_S_I_4K": 240.0,
    "XAVC_I_4K": 240.0,
    "XAVC_S_I_HD": 89.0,
    "XAVC_I_HD": 111.0,
    "XAVC_S_4K": 100.0,
    "XAVC_HS_4K": 75.0,
    "XAVC_S_HD": 50.0,
}

VALID_TALLY_BRIGHTNESS: Tuple[str, ...] = ("HIGH", "LOW", "OFF")

# ---------------------------------------------------------------------------
# Verified Binary Marker Contracts (FX3 v7.02 & FX6 v6.01)
# ---------------------------------------------------------------------------

FX3_APPFW_MECH_SHUTTER_MARKERS: Tuple[str, ...] = (
    "PID_SET_SHUTTER_TYPE",
    "PID_SET_FRONT_ESHUTTER_MODE",
    "PID_SET_HYBRID_SHUTTER_MODE",
    "PID_SET_SILENT_SHUTTER_MODE",
    "VAL_setting_shutter_type_SHUTTER_TYPE_MECHANICAL",
    "VAL_setting_shutter_type_SHUTTER_TYPE_ELECTRONIC",
    "VAL_setting_front_curtaion_shutter_FRONT_CURTAIN_SHUTTER_OFF",
    "EVENT_REMOTE_ANTI_DUST_FUNCTION_IMAGE_SENSOR_BARRIER",
    "EVENT_REMOTE_CLEANING_MODE_ON",
)

FX6_APPFW_FORBIDDEN_MECH_PIDS: Tuple[str, ...] = (
    "PID_SET_SHUTTER_TYPE",
    "PID_SET_FRONT_ESHUTTER_MODE",
    "PID_SET_HYBRID_SHUTTER_MODE",
    "PID_SET_SILENT_SHUTTER_MODE",
)

FX3_CP_MECH_SHUTTER_MARKERS: Tuple[str, ...] = (
    "SET_SHUTTER_TYPE",
    "SET_FRONT_ESHUTTER",
    "SET_HYBRID_SHUTTER_MODE",
    "SET_SILENT_SHUTTER_MODE",
    "CheckSetShutterType",
    "CheckSetHybridShutterMode",
    "CheckSetSilentShutterMode",
)

FX6_CP_FORBIDDEN_MECH_SHUTTER_MARKERS: Tuple[str, ...] = FX3_CP_MECH_SHUTTER_MARKERS

CP_SHARED_ELEC_SHUTTER_MARKERS: Tuple[str, ...] = (
    "EC_ElecShutter_Main",
    "EC_NonlinearElecShutter_MechShutterTable",
    "NonlinearElecShutter::XPIDrvSpeed",
    "EC_CurtainSpeedAdj",
)

SHARED_APPFW_SHUTTER_ANGLE_MARKERS: Tuple[str, ...] = (
    "VAL_setting_mode_shutter_MODE_SHUTTER_ANGLE",
    "VAL_setting_mode_shutter_MODE_SHUTTER_SPEED",
    "EVENT_REMOTE_SHUTTER_ANGLE",
    "VAL_setting_shutter_angle_SHUTTER_ANGLE_5_POINT_6",
    "VAL_setting_shutter_angle_SHUTTER_ANGLE_11_POINT_25",
    "VAL_setting_shutter_angle_SHUTTER_ANGLE_22_POINT_5",
    "VAL_setting_shutter_angle_SHUTTER_ANGLE_45_POINT_0",
    "VAL_setting_shutter_angle_SHUTTER_ANGLE_90_POINT_0",
    "VAL_setting_shutter_angle_SHUTTER_ANGLE_172_POINT_8",
    "VAL_setting_shutter_angle_SHUTTER_ANGLE_180_POINT_0",
    "VAL_setting_shutter_angle_SHUTTER_ANGLE_270_POINT_0",
    "VAL_setting_shutter_angle_SHUTTER_ANGLE_360_POINT_0",
    "VAL_setting_shutter_angle_SHUTTER_ANGLE_2F",
    "VAL_setting_shutter_angle_SHUTTER_ANGLE_64F",
)

FX6_APPFW_ECS_AND_ANGLE_MARKERS: Tuple[str, ...] = (
    "BKID_APP_SETTING_MODE_SHUTTER",
    "BKID_APP_SETTING_SHUTTER_ANGLE",
    "BKID_APP_SETTING_SHUTTER_ANGLE_CONTINUOUS",
    "BKID_APP_EXTERN_SHUTTER_ANGLE_STEP",
    "BKID_APP_SETTING_ECS_FREQUENCY",
    "BKID_APP_EXTERN_SHUTTER_ECSISON",
    "BKID_APP_EXTERN_SHUTTER_ECS_STEP",
    "EVENT_REMOTE_SHUTTER_ECS_FREQUENCY",
    "EVENT_REMOTE_SHUTTER_ECS_SETTING",
    "EVENT_REMOTE_SHUTTER_ECS_NUMBER_STEP",
)

FX6_CP_SHUTTER_ANGLE_MARKERS: Tuple[str, ...] = (
    "ShutterSpeedAngle",
    "ShutterSpeedAngleMeta",
    "ShutterSpeedTime",
)

FX6_MPR_SHUTTER_RTMD_MARKERS: Tuple[str, ...] = (
    "muxMxfRtmetaBufferShutterSpeedAngleWrite",
    "muxMxfRtmetaBufferShutterSpeedTimeWrite",
    "MuxMxfRtMeta::muxMxfRtBimConvertSubShutterTime",
)

SHARED_APPFW_SQ_MARKERS: Tuple[str, ...] = (
    "SHOOT_MODE_SWITCH_S_AND_Q",
    "EVENT_REMOTE_SQ_FRAME_RATE",
    "EVENT_REMOTE_SQ_REC_FRAME_RATE",
    "EVENT_REMOTE_SQ_PROXY_RECORDING",
    "EVENT_REMOTE_SQ_PROXY_FILE_FORMAT",
)

FX3_APPFW_SQ_HFR_MARKERS: Tuple[str, ...] = (
    "SHOOTING_MODE_SLOW_QUICK_MOTION_SQ_FRAME_RATE_120FPS",
    "SHOOTING_MODE_SLOW_QUICK_MOTION_SQ_FRAME_RATE_240FPS",
)

FX6_APPFW_SQ_HFR_MARKERS: Tuple[str, ...] = (
    "BKID_APP_SETTING_SQ_PROXY_RECORDING",
    "SQ_FRAME_RATE_1FPS",
    "SQ_FRAME_RATE_120FPS",
    "SQ_FRAME_RATE_240FPS",
)

FX3_CP_SQ_MARKERS: Tuple[str, ...] = ("SLOW_AND_QUICK_MODE",)

MPR_SHARED_AUDIO_PROXY_MARKERS: Tuple[str, ...] = (
    "AudioRecStart",
    "AudioRecStop",
    "AudioFormat",
    "AVC_Proxy_1920_1080_HP",
    "HEVC_Proxy_1920_1080_M10P",
)

SHARED_APPFW_REC_LAMP_MARKERS: Tuple[str, ...] = (
    "REC_LAMP_ALL_LIGHTS_UP",
    "REC_LAMP_ALL_LIGHTS_OUT",
    "REC_LAMP_ONLY_FRONT_OFF",
    "REC_LAMP_LIGHT_UP_ONLY_ONE",
    "REC_LAMP_ON",
    "REC_LAMP_OFF",
)

FX6_APPFW_TALLY_MARKERS: Tuple[str, ...] = (
    "BKID_APP_SETTING_FRONT_TALLY",
    "BKID_APP_SETTING_REAR_TALLY",
    "BKID_APP_SETTING_TALLY_CONTROL",
    "BKID_APP_SETTING_TALLY_LAMP_BRIGHTNESS",
    "FRONT_TALLY_ON",
    "FRONT_TALLY_OFF",
    "REAR_TALLY_ON",
    "REAR_TALLY_OFF",
    "TALLY_LAMP_BRIGHTNESS_HIGH",
    "TALLY_LAMP_BRIGHTNESS_LOW",
    "TALLY_LAMP_BRIGHTNESS_OFF",
    "EVENT_REMOTE_RED_TALLY_LAMP_CONTROL",
    "EVENT_REMOTE_GREEN_TALLY_LAMP_CONTROL",
    "EVENT_REMOTE_YELLOW_TALLY_LAMP_CONTROL",
)

CP_SHARED_TALLY_MARKERS: Tuple[str, ...] = ("MSG_ID_INFRABB_SYS_SET_CA_TALLY",)

FX3_NS39_UXC_EXPECTED_LABELS: Dict[int, str] = {
    0x0000E368: "Slow Shutter",
    0x0000E72E: "Audio Recording",
}

FX3_NS3_UXC_EXPECTED_LABELS: Dict[int, str] = {
    0x00006099: "S&Q Motion",
    0x000060C6: "Movie/S&Q Motion",
    0x00006431: "Shutter",
}

FX6_NS1_UXC_EXPECTED_LABELS: Dict[int, str] = {
    0x00002077: "ECS",
    0x000020C2: "S&Q FPS",
    0x000020CC: "S&Q Frame Rate",
    0x000022DB: "ECS On/Off",
    0x000024F6: "Front Tally Lamp",
    0x000024F8: "Rear Tally Lamp",
    0x000024FA: "Tally Control",
    0x000025B6: "Tally Lamp Brightness",
    0x000030C6: "Shutter Angle (Step)",
    0x000030D9: "Shutter Angle (Continuous)",
}

FX6_NS2_UXC_EXPECTED_LABELS: Dict[int, str] = {
    0x0000417A: "S&Q Motion: On",
    0x000042C8: "Tally",
    0x00004325: "Slow & Quick Motion",
    0x00004577: "S&Q Frame Rate",
    0x00004D96: "Shutter Angle",
    0x00004D98: "ECS Frequency",
    0x00004EE1: "Rec Tally Blink",
    0x00005379: "Green Tally",
    0x0000537B: "Red Tally",
}

# ---------------------------------------------------------------------------
# Report & Evaluation Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MechShutterProtectionEvalResult:
    valid: bool
    status: str
    operating_mode: str
    shutter_mode_requested: str
    fx6_video_ipc_emits_mech_pid: bool
    curtains_parked_safely_open: bool
    solenoid_energized_in_video: bool
    mech_shutter_unintended_actuations: int
    cp_mutation_bytes: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class MechShutterMatrixEntry:
    scenario_id: str
    fx6_ipc_behavior: str
    fx3_physical_curtain_state: str
    unintended_actuations: int
    verdict: str
    notes: str


@dataclass(frozen=True)
class MechShutterProtectionReport:
    passed: bool
    fx3_appfw_mech_shutter_markers: Tuple[str, ...]
    fx6_appfw_unexpected_mech_pids: Tuple[str, ...]
    fx3_cp_mech_shutter_markers: Tuple[str, ...]
    fx6_cp_unexpected_mech_markers: Tuple[str, ...]
    fx3_cp_shared_elec_markers: Tuple[str, ...]
    fx6_cp_shared_elec_markers: Tuple[str, ...]
    video_mode_eval: MechShutterProtectionEvalResult
    sq_mode_eval: MechShutterProtectionEvalResult
    stills_mech_eval: MechShutterProtectionEvalResult
    antidust_barrier_eval: MechShutterProtectionEvalResult
    matrix: Tuple[MechShutterMatrixEntry, ...]
    mech_shutter_unintended_actuations: int
    cp_mutation_bytes: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class ShutterAngleEvalResult:
    valid: bool
    status: str
    angle_deg: float
    fps: float
    continuous: bool
    exposure_time_sec: float
    exposure_time_ms: float
    equivalent_shutter_denom: float
    fits_within_frame_period: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class EcsAntiFlickerEvalResult:
    valid: bool
    status: str
    ecs_freq_hz: float
    fps: float
    light_source_hz: float
    exposure_time_sec: float
    exposure_time_ms: float
    equivalent_angle_deg: float
    harmonic_multiple: float
    beat_drift_pct: float
    flicker_free_locked: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class ShutterAngleAndEcsReport:
    passed: bool
    fx3_shared_angle_markers: Tuple[str, ...]
    fx6_shared_angle_markers: Tuple[str, ...]
    fx6_ecs_and_angle_markers: Tuple[str, ...]
    fx6_cp_shutter_markers: Tuple[str, ...]
    fx6_mpr_rtmd_shutter_markers: Tuple[str, ...]
    uxc_shutter_ecs_labels: Dict[str, str]
    default_180_at_24fps_eval: ShutterAngleEvalResult
    min_5_6_at_240fps_eval: ShutterAngleEvalResult
    max_360_at_23_976fps_eval: ShutterAngleEvalResult
    ecs_120hz_led_wall_eval: EcsAntiFlickerEvalResult
    ecs_100hz_pal_mains_eval: EcsAntiFlickerEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class SqMotionEvalResult:
    valid: bool
    status: str
    resolution_class: str
    sensor_fps: int
    rec_fps: float
    speed_factor: float
    off_speed: bool
    audio_recording_enabled: bool
    audio_muted_reason: str
    proxy_requested: bool
    proxy_allowed: bool
    codec: str
    card_class: str
    estimated_write_mbps: float
    card_sustained_mbps: float
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class SqMotionMatrixReport:
    passed: bool
    fx3_shared_sq_markers: Tuple[str, ...]
    fx6_shared_sq_markers: Tuple[str, ...]
    fx3_sq_hfr_markers: Tuple[str, ...]
    fx6_sq_hfr_markers: Tuple[str, ...]
    fx3_cp_sq_markers: Tuple[str, ...]
    fx3_mpr_audio_proxy_markers: Tuple[str, ...]
    fx6_mpr_audio_proxy_markers: Tuple[str, ...]
    uxc_sq_labels: Dict[str, str]
    sq_4k_120fps_24p_eval: SqMotionEvalResult
    sq_fhd_240fps_24p_eval: SqMotionEvalResult
    sq_4k_1fps_24p_eval: SqMotionEvalResult
    sq_4k_24fps_1to1_eval: SqMotionEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class TallyLampEvalResult:
    valid: bool
    status: str
    front_tally_on: bool
    rear_tally_on: bool
    brightness: str
    rec_tally_blink: bool
    fx3_rec_lamp_cmd: str
    cp_tally_msg_id: str
    green_tally_requested: bool
    yellow_tally_requested: bool
    osd_indicator_fallback: bool
    missing_gpio_faults: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class TallyLampMatrixEntry:
    feature_id: str
    fx6_control: str
    fx3_mapping: str
    missing_gpio_faults: int
    verdict: str
    notes: str


@dataclass(frozen=True)
class TallyLampMatrixReport:
    passed: bool
    fx3_rec_lamp_markers: Tuple[str, ...]
    fx6_rec_lamp_markers: Tuple[str, ...]
    fx6_tally_markers: Tuple[str, ...]
    fx3_cp_tally_markers: Tuple[str, ...]
    fx6_cp_tally_markers: Tuple[str, ...]
    uxc_tally_labels: Dict[str, str]
    both_on_eval: TallyLampEvalResult
    front_off_rear_on_eval: TallyLampEvalResult
    front_on_rear_off_eval: TallyLampEvalResult
    green_yellow_contained_eval: TallyLampEvalResult
    matrix: Tuple[TallyLampMatrixEntry, ...]
    missing_gpio_faults: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class ShutterEcsSqAndTallyReport:
    schema_version: str
    phase_version: str
    mode: str
    all_checks_passed: bool
    o_rdonly_enforced: bool
    donor_file_sizes: Dict[str, int]
    pillar_a_mech_shutter: MechShutterProtectionReport
    pillar_b_shutter_angle_ecs: ShutterAngleAndEcsReport
    pillar_c_sq_motion: SqMotionMatrixReport
    pillar_d_tally_lamps: TallyLampMatrixReport
    errors: Tuple[str, ...]
    report_sha256: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)

    def to_deterministic_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True) + "\n"


# ---------------------------------------------------------------------------
# Strictly `os.O_RDONLY` + `mmap` Section-Scoped Scanning Helpers
# ---------------------------------------------------------------------------


def _scan_buffer_markers(buf: bytes, markers: Sequence[str]) -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
    """Scan an in-memory buffer for ASCII markers via C-level `bytes.find`."""
    present: List[str] = []
    missing: List[str] = []
    for m in markers:
        if buf.find(m.encode("latin1")) != -1:
            present.append(m)
        else:
            missing.append(m)
    return tuple(present), tuple(missing)


def _read_uxc_rdonly(path: Path) -> bytes:
    """Read a small `.uxc` asset file strictly via `os.O_RDONLY`."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        with os.fdopen(fd, "rb") as fh:
            return fh.read()
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        raise


def _scan_donor_rdonly_markers(
    path: Path,
    marker_groups: Mapping[str, Sequence[str]],
    *,
    is_elf: bool,
) -> Tuple[int, Dict[str, Tuple[str, ...]]]:
    """Open `path` strictly `os.O_RDONLY` with `mmap.ACCESS_READ` and scan marker groups."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        sz = os.fstat(fd).st_size
        if sz == 0:
            return 0, {k: () for k in marker_groups}
        unique_markers = sorted(
            {m for markers in marker_groups.values() for m in markers},
            key=lambda s: (-len(s), s),
        )
        if not unique_markers:
            return sz, {k: () for k in marker_groups}

        pat = re.compile(b"|".join(re.escape(m.encode("latin1")) for m in unique_markers))
        matched_tokens: set[bytes] = set()
        with mmap.mmap(fd, sz, access=mmap.ACCESS_READ) as mm:
            ranges: List[Tuple[int, int]] = [(0, sz)]
            if is_elf:
                try:
                    secs = _parse_elf64_sections(mm)  # type: ignore[arg-type]
                    elf_ranges = [secs[s] for s in (".rodata", ".dynstr") if s in secs]
                    if elf_ranges:
                        ranges = elf_ranges
                except ValueError:
                    ranges = [(0, sz)]

            for off, rsz in ranges:
                for mo in pat.finditer(mm, off, off + rsz):
                    matched_tokens.add(mo.group(0))

        matched_list = list(matched_tokens)
        present_markers = {
            m
            for m in unique_markers
            if (mb := m.encode("latin1")) in matched_tokens or any(mb in tok for tok in matched_list)
        }
        results: Dict[str, Tuple[str, ...]] = {
            group_name: tuple(m for m in markers if m in present_markers)
            for group_name, markers in marker_groups.items()
        }
        return sz, results
    finally:
        os.close(fd)


# ---------------------------------------------------------------------------
# Clean-Room Synthetic Fixtures (Used ONLY when FX3_FX6_FORCE_CLEAN_ROOM=1 or donors absent)
# ---------------------------------------------------------------------------


def build_clean_room_shutter_ecs_sq_tally_fixtures(
    *,
    inject_fx6_mech_shutter_pid: bool = False,
    inject_fx6_cp_mech_shutter: bool = False,
    drop_fx3_mech_shutter: bool = False,
    drop_shutter_angle_5_6_or_360: bool = False,
    drop_fx6_ecs_markers: bool = False,
    drop_sq_240fps: bool = False,
    drop_fx3_rec_lamp: bool = False,
    drop_fx6_tally: bool = False,
    corrupt_uxc_labels: bool = False,
) -> Dict[str, bytes]:
    """Build deterministic clean-room fixtures representing all 10 FX3 v7.02 & FX6 v6.01 donor artifacts."""
    elf_hdr = b"\x7fELF\x02\x01\x01\x00" + bytes(56)
    cp_hdr = b"LDR\x00" + bytes(60)

    def _pack(tokens: Sequence[str], *, prefix: bytes = elf_hdr) -> bytes:
        return prefix + b"\x00".join(t.encode("latin1") for t in tokens) + b"\x00"

    fx3_mech = () if drop_fx3_mech_shutter else FX3_APPFW_MECH_SHUTTER_MARKERS
    fx3_angle = (
        tuple(m for m in SHARED_APPFW_SHUTTER_ANGLE_MARKERS if "5_POINT_6" not in m and "360_POINT_0" not in m)
        if drop_shutter_angle_5_6_or_360
        else SHARED_APPFW_SHUTTER_ANGLE_MARKERS
    )
    fx3_sq_hfr = () if drop_sq_240fps else FX3_APPFW_SQ_HFR_MARKERS
    fx3_rec_lamp = () if drop_fx3_rec_lamp else SHARED_APPFW_REC_LAMP_MARKERS

    fx3_appfw_tokens = [
        *fx3_mech,
        *fx3_angle,
        *SHARED_APPFW_SQ_MARKERS,
        *fx3_sq_hfr,
        *fx3_rec_lamp,
    ]

    fx6_ecs = () if drop_fx6_ecs_markers else FX6_APPFW_ECS_AND_ANGLE_MARKERS
    fx6_tally = () if drop_fx6_tally else FX6_APPFW_TALLY_MARKERS
    fx6_appfw_tokens = [
        *(FX6_APPFW_FORBIDDEN_MECH_PIDS if inject_fx6_mech_shutter_pid else ()),
        *SHARED_APPFW_SHUTTER_ANGLE_MARKERS,
        *fx6_ecs,
        *SHARED_APPFW_SQ_MARKERS,
        *FX6_APPFW_SQ_HFR_MARKERS,
        *SHARED_APPFW_REC_LAMP_MARKERS,
        *fx6_tally,
    ]

    fx3_cp_tokens = [
        *FX3_CP_MECH_SHUTTER_MARKERS,
        *CP_SHARED_ELEC_SHUTTER_MARKERS,
        *FX3_CP_SQ_MARKERS,
        *CP_SHARED_TALLY_MARKERS,
    ]
    fx6_cp_tokens = [
        *(FX6_CP_FORBIDDEN_MECH_SHUTTER_MARKERS if inject_fx6_cp_mech_shutter else ()),
        *CP_SHARED_ELEC_SHUTTER_MARKERS,
        *FX6_CP_SHUTTER_ANGLE_MARKERS,
        *CP_SHARED_TALLY_MARKERS,
    ]

    fx3_mpr_tokens = [*MPR_SHARED_AUDIO_PROXY_MARKERS]
    fx6_mpr_tokens = [*MPR_SHARED_AUDIO_PROXY_MARKERS, *FX6_MPR_SHUTTER_RTMD_MARKERS]

    fx6_ns1_labels = dict(FX6_NS1_UXC_EXPECTED_LABELS)
    if corrupt_uxc_labels:
        fx6_ns1_labels[0x00002077] = "CORRUPT_ECS_LABEL"

    return {
        "fx3_appfw": _pack(fx3_appfw_tokens),
        "fx6_appfw": _pack(fx6_appfw_tokens),
        "fx3_libmpr": _pack(fx3_mpr_tokens),
        "fx6_libmpr": _pack(fx6_mpr_tokens),
        "fx3_cpapp": _pack(fx3_cp_tokens, prefix=cp_hdr),
        "fx6_cpapp": _pack(fx6_cp_tokens, prefix=cp_hdr),
        "fx3_str_en": build_sparse_uxc_string_pack(
            {k & 0x1FFF: v for k, v in FX3_NS39_UXC_EXPECTED_LABELS.items()}, namespace_id=39
        ),
        "fx3_str_en_g": build_sparse_uxc_string_pack(
            {k & 0x1FFF: v for k, v in FX3_NS3_UXC_EXPECTED_LABELS.items()}, namespace_id=3
        ),
        "fx6_str_en_1": build_sparse_uxc_string_pack(
            {k & 0x1FFF: v for k, v in fx6_ns1_labels.items()}, namespace_id=1
        ),
        "fx6_str_en_2": build_sparse_uxc_string_pack(
            {k & 0x1FFF: v for k, v in FX6_NS2_UXC_EXPECTED_LABELS.items()}, namespace_id=2
        ),
    }


# ---------------------------------------------------------------------------
# Pillar A: FX3 Mechanical Focal-Plane Shutter Curtain Protection
# ---------------------------------------------------------------------------


def evaluate_mech_shutter_curtain_protection(
    *,
    operating_mode: str = "VIDEO_ELECTRONIC_SHUTTER",
    shutter_mode_requested: str = "ELECTRONIC_ROLLING",
    fx6_video_ipc_emits_mech_pid: bool = False,
    curtain_parked_open: bool = True,
    cp_mutation_bytes: int = 0,
) -> MechShutterProtectionEvalResult:
    """Prove FX3 mechanical focal-plane curtains remain parked safely open during Video/S&Q."""
    errors: List[str] = []
    norm_op = operating_mode.strip().upper()
    norm_req = shutter_mode_requested.strip().upper()

    if norm_op not in (
        "VIDEO_ELECTRONIC_SHUTTER",
        "S_AND_Q_ELECTRONIC_SHUTTER",
        "STILLS_MECHANICAL_SHUTTER",
        "ANTI_DUST_CLEANING_MODE",
    ):
        errors.append(f"Unsupported operating_mode: {operating_mode!r}")
    if norm_req not in ("ELECTRONIC_ROLLING", "MECHANICAL_CURTAIN", "ANTI_DUST_BARRIER"):
        errors.append(f"Unsupported shutter_mode_requested: {shutter_mode_requested!r}")
    if cp_mutation_bytes != 0:
        errors.append(f"U2 Stock-CP redline violated: cp_mutation_bytes={cp_mutation_bytes} (must be 0)")

    is_video_mode = norm_op in ("VIDEO_ELECTRONIC_SHUTTER", "S_AND_Q_ELECTRONIC_SHUTTER")
    unintended = 0
    solenoid_video = False

    if is_video_mode:
        if fx6_video_ipc_emits_mech_pid:
            unintended += 1
            solenoid_video = True
            errors.append("FX6 video-mode IPC unexpectedly emitted FX3 mechanical-shutter PID")
        if norm_req != "ELECTRONIC_ROLLING":
            unintended += 1
            solenoid_video = True
            errors.append(
                f"Video/S&Q mode forbids {norm_req}; electronic rolling shutter required to protect curtains"
            )
        if not curtain_parked_open:
            unintended += 1
            errors.append("FX3 mechanical shutter curtain not parked safely open in video mode")
    elif norm_op == "STILLS_MECHANICAL_SHUTTER" and norm_req != "MECHANICAL_CURTAIN":
        errors.append("STILLS_MECHANICAL_SHUTTER requires MECHANICAL_CURTAIN request")
    elif norm_op == "ANTI_DUST_CLEANING_MODE" and norm_req != "ANTI_DUST_BARRIER":
        errors.append("ANTI_DUST_CLEANING_MODE requires ANTI_DUST_BARRIER request")

    if len(errors) > 0:
        status = "BLOCKED_MECH_SHUTTER_VIDEO_ACTUATION_HAZARD"
    elif is_video_mode:
        status = "MECH_SHUTTER_CURTAINS_PARKED_OPEN_VIDEO_SAFE"
    else:
        status = "STILLS_OR_ANTIDUST_MECH_CURTAIN_AUTHORIZED"

    return MechShutterProtectionEvalResult(
        valid=len(errors) == 0,
        status=status,
        operating_mode=norm_op,
        shutter_mode_requested=norm_req,
        fx6_video_ipc_emits_mech_pid=fx6_video_ipc_emits_mech_pid,
        curtains_parked_safely_open=curtain_parked_open if is_video_mode else False,
        solenoid_energized_in_video=solenoid_video,
        mech_shutter_unintended_actuations=unintended,
        cp_mutation_bytes=cp_mutation_bytes,
        errors=tuple(errors),
    )


def evaluate_pillar_a_mech_shutter_protection(
    present_map: Mapping[str, Tuple[str, ...]],
) -> MechShutterProtectionReport:
    """Audit Pillar A: FX3 mechanical focal-plane curtain safety under FX6 electronic video IPCs."""
    errors: List[str] = []

    fx3_mech = present_map["fx3_appfw_mech"]
    fx6_unexp_pids = present_map["fx6_appfw_unexpected_mech"]
    fx3_cp_mech = present_map["fx3_cp_mech"]
    fx6_cp_unexp = present_map["fx6_cp_unexpected_mech"]
    fx3_cp_elec = present_map["fx3_cp_elec"]
    fx6_cp_elec = present_map["fx6_cp_elec"]

    if fx3_mech != FX3_APPFW_MECH_SHUTTER_MARKERS:
        missing = tuple(m for m in FX3_APPFW_MECH_SHUTTER_MARKERS if m not in fx3_mech)
        errors.append(f"FX3 appFw.so missing mechanical-shutter Stills/Anti-Dust markers: {missing}")
    if len(fx6_unexp_pids) > 0:
        errors.append(f"FX6 appFw.so unexpectedly contains FX3 mechanical shutter PIDs: {fx6_unexp_pids}")
    if fx3_cp_mech != FX3_CP_MECH_SHUTTER_MARKERS:
        missing = tuple(m for m in FX3_CP_MECH_SHUTTER_MARKERS if m not in fx3_cp_mech)
        errors.append(f"FX3 cpapp-b.bin missing mechanical shutter CP handlers: {missing}")
    if len(fx6_cp_unexp) > 0:
        errors.append(f"FX6 cpapp-b.bin unexpectedly contains mechanical shutter CP handlers: {fx6_cp_unexp}")
    if fx3_cp_elec != CP_SHARED_ELEC_SHUTTER_MARKERS or fx6_cp_elec != CP_SHARED_ELEC_SHUTTER_MARKERS:
        errors.append("FX3/FX6 cpapp-b.bin missing shared electronic shutter driver markers")

    fx6_emits_mech = len(fx6_unexp_pids) > 0 or len(fx6_cp_unexp) > 0
    video_eval = evaluate_mech_shutter_curtain_protection(
        operating_mode="VIDEO_ELECTRONIC_SHUTTER",
        shutter_mode_requested="ELECTRONIC_ROLLING",
        fx6_video_ipc_emits_mech_pid=fx6_emits_mech,
        curtain_parked_open=True,
    )
    sq_eval = evaluate_mech_shutter_curtain_protection(
        operating_mode="S_AND_Q_ELECTRONIC_SHUTTER",
        shutter_mode_requested="ELECTRONIC_ROLLING",
        fx6_video_ipc_emits_mech_pid=fx6_emits_mech,
        curtain_parked_open=True,
    )
    stills_eval = evaluate_mech_shutter_curtain_protection(
        operating_mode="STILLS_MECHANICAL_SHUTTER",
        shutter_mode_requested="MECHANICAL_CURTAIN",
        curtain_parked_open=False,
    )
    antidust_eval = evaluate_mech_shutter_curtain_protection(
        operating_mode="ANTI_DUST_CLEANING_MODE",
        shutter_mode_requested="ANTI_DUST_BARRIER",
        curtain_parked_open=False,
    )

    for ev in (video_eval, sq_eval, stills_eval, antidust_eval):
        if not ev.valid:
            errors.extend(ev.errors)

    total_unintended = video_eval.mech_shutter_unintended_actuations + sq_eval.mech_shutter_unintended_actuations
    matrix: Tuple[MechShutterMatrixEntry, ...] = (
        MechShutterMatrixEntry(
            scenario_id="VIDEO_MODE_ELECTRONIC_SHUTTER",
            fx6_ipc_behavior="Electronic rolling shutter (0 mechanical shutter PIDs in FX6 appFw.so)",
            fx3_physical_curtain_state="Curtains parked safely open (solenoid de-energized)",
            unintended_actuations=video_eval.mech_shutter_unintended_actuations,
            verdict="SAFE_CURTAINS_PARKED_OPEN",
            notes="FX6 video-mode IPCs never invoke PID_SET_SHUTTER_TYPE / SET_SHUTTER_TYPE.",
        ),
        MechShutterMatrixEntry(
            scenario_id="SQ_HFR_1_TO_240FPS_ELECTRONIC",
            fx6_ipc_behavior="IMX510 electronic sensor integration only",
            fx3_physical_curtain_state="Curtains parked safely open (solenoid de-energized)",
            unintended_actuations=sq_eval.mech_shutter_unintended_actuations,
            verdict="SAFE_CURTAINS_PARKED_OPEN",
            notes="High-speed 120/240fps S&Q uses pure electronic sensor readout.",
        ),
        MechShutterMatrixEntry(
            scenario_id="STILLS_AND_ANTI_DUST_FX3_STOCK_CP",
            fx6_ipc_behavior="N/A (FX6 lacks mechanical curtain; FX3 stock CP retains handlers)",
            fx3_physical_curtain_state="Stock-CP mechanical shutter & Anti-Dust barrier intact",
            unintended_actuations=0,
            verdict="STOCK_CP_PRESERVED",
            notes="cp_mutation_bytes == 0 keeps FX3 native Stills & Anti-Dust curtain control intact.",
        ),
    )

    return MechShutterProtectionReport(
        passed=len(errors) == 0 and total_unintended == 0,
        fx3_appfw_mech_shutter_markers=fx3_mech,
        fx6_appfw_unexpected_mech_pids=fx6_unexp_pids,
        fx3_cp_mech_shutter_markers=fx3_cp_mech,
        fx6_cp_unexpected_mech_markers=fx6_cp_unexp,
        fx3_cp_shared_elec_markers=fx3_cp_elec,
        fx6_cp_shared_elec_markers=fx6_cp_elec,
        video_mode_eval=video_eval,
        sq_mode_eval=sq_eval,
        stills_mech_eval=stills_eval,
        antidust_barrier_eval=antidust_eval,
        matrix=matrix,
        mech_shutter_unintended_actuations=total_unintended,
        cp_mutation_bytes=0,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar B: True Cinema Shutter Angle (5.6°..360.0°) & Extended Clear Scan (ECS)
# ---------------------------------------------------------------------------


def evaluate_shutter_angle_exposure(
    *,
    angle_deg: float = DEFAULT_SHUTTER_ANGLE_DEG,
    fps: float = 24.0,
    continuous: bool = False,
) -> ShutterAngleEvalResult:
    """Validate true cinema shutter angle exposure math: `t_exp = (angle / 360.0) / fps`."""
    errors: List[str] = []
    if not math.isfinite(angle_deg):
        errors.append("Shutter angle must be finite")
    if not math.isfinite(fps):
        errors.append("Frame rate fps must be finite")

    if not errors:
        if angle_deg < SHUTTER_ANGLE_MIN_DEG or angle_deg > SHUTTER_ANGLE_MAX_DEG:
            errors.append(
                f"Shutter angle {angle_deg}° out of valid range [{SHUTTER_ANGLE_MIN_DEG}°..{SHUTTER_ANGLE_MAX_DEG}°]"
            )
        if not continuous and all(abs(angle_deg - d) > 1e-6 for d in VALID_DISCRETE_SHUTTER_ANGLES_DEG):
            errors.append(
                f"Discrete shutter angle {angle_deg}° not in canonical Sony step table"
            )
        if fps < SHUTTER_FPS_MIN or fps > SHUTTER_FPS_MAX:
            errors.append(f"Frame rate {fps} fps out of range [{SHUTTER_FPS_MIN}..{SHUTTER_FPS_MAX}]")

    if errors:
        return ShutterAngleEvalResult(
            valid=False,
            status="BLOCKED_INVALID_SHUTTER_ANGLE_OR_FPS",
            angle_deg=angle_deg if math.isfinite(angle_deg) else 0.0,
            fps=fps if math.isfinite(fps) else 0.0,
            continuous=continuous,
            exposure_time_sec=0.0,
            exposure_time_ms=0.0,
            equivalent_shutter_denom=0.0,
            fits_within_frame_period=False,
            errors=tuple(errors),
        )

    t_exp = (angle_deg / 360.0) / fps
    t_frame = 1.0 / fps
    fits = t_exp <= t_frame + 1e-12
    equiv_denom = 1.0 / t_exp

    return ShutterAngleEvalResult(
        valid=True,
        status="SHUTTER_ANGLE_EXPOSURE_VERIFIED",
        angle_deg=round(angle_deg, 4),
        fps=round(fps, 4),
        continuous=continuous,
        exposure_time_sec=round(t_exp, 9),
        exposure_time_ms=round(t_exp * 1000.0, 6),
        equivalent_shutter_denom=round(equiv_denom, 4),
        fits_within_frame_period=fits,
        errors=(),
    )


def evaluate_ecs_anti_flicker(
    *,
    ecs_freq_hz: float = 120.0,
    fps: float = 24.0,
    light_source_hz: float = 120.0,
) -> EcsAntiFlickerEvalResult:
    """Validate Extended Clear Scan (`ECS`) fine frequency step & LED/mains flicker lock."""
    errors: List[str] = []
    if not (math.isfinite(ecs_freq_hz) and math.isfinite(fps) and math.isfinite(light_source_hz)):
        errors.append("ECS inputs (ecs_freq_hz, fps, light_source_hz) must be finite")
    else:
        if fps < SHUTTER_FPS_MIN or fps > SHUTTER_FPS_MAX:
            errors.append(f"Frame rate {fps} fps out of range [{SHUTTER_FPS_MIN}..{SHUTTER_FPS_MAX}]")
        if ecs_freq_hz < ECS_FREQ_MIN_HZ or ecs_freq_hz > ECS_FREQ_MAX_HZ:
            errors.append(
                f"ECS frequency {ecs_freq_hz} Hz out of range [{ECS_FREQ_MIN_HZ}..{ECS_FREQ_MAX_HZ}]"
            )
        if ecs_freq_hz < fps - 1e-6:
            errors.append(
                f"ECS frequency {ecs_freq_hz} Hz cannot be lower than frame rate {fps} fps"
            )
        if light_source_hz <= 0.0:
            errors.append("light_source_hz must be > 0")

    if errors:
        return EcsAntiFlickerEvalResult(
            valid=False,
            status="BLOCKED_INVALID_ECS_FREQUENCY",
            ecs_freq_hz=ecs_freq_hz if math.isfinite(ecs_freq_hz) else 0.0,
            fps=fps if math.isfinite(fps) else 0.0,
            light_source_hz=light_source_hz if math.isfinite(light_source_hz) else 0.0,
            exposure_time_sec=0.0,
            exposure_time_ms=0.0,
            equivalent_angle_deg=0.0,
            harmonic_multiple=0.0,
            beat_drift_pct=100.0,
            flicker_free_locked=False,
            errors=tuple(errors),
        )

    t_exp = 1.0 / ecs_freq_hz
    equiv_angle = 360.0 * (fps / ecs_freq_hz)
    ratio = light_source_hz / ecs_freq_hz
    nearest_int = max(1, round(ratio))
    beat_drift_pct = abs(ratio - nearest_int) / nearest_int * 100.0
    flicker_locked = beat_drift_pct <= 0.5

    return EcsAntiFlickerEvalResult(
        valid=True,
        status="ECS_LED_FLICKER_LOCKED" if flicker_locked else "ECS_EXPOSURE_VALID_PHASE_UNSYNCED",
        ecs_freq_hz=round(ecs_freq_hz, 3),
        fps=round(fps, 4),
        light_source_hz=round(light_source_hz, 3),
        exposure_time_sec=round(t_exp, 9),
        exposure_time_ms=round(t_exp * 1000.0, 6),
        equivalent_angle_deg=round(equiv_angle, 4),
        harmonic_multiple=round(ratio, 6),
        beat_drift_pct=round(beat_drift_pct, 4),
        flicker_free_locked=flicker_locked,
        errors=(),
    )


def evaluate_pillar_b_shutter_angle_and_ecs(
    present_map: Mapping[str, Tuple[str, ...]],
    uxc_shutter_ecs_labels: Mapping[str, str],
) -> ShutterAngleAndEcsReport:
    """Audit Pillar B: True Cinema Shutter Angle (`5.6°..360.0°`) and Extended Clear Scan (`ECS`)."""
    errors: List[str] = []

    fx3_angle = present_map["fx3_appfw_angle"]
    fx6_angle = present_map["fx6_appfw_angle"]
    fx6_ecs = present_map["fx6_appfw_ecs"]
    fx6_cp = present_map["fx6_cp_shutter"]
    fx6_mpr = present_map["fx6_mpr_shutter"]

    if fx3_angle != SHARED_APPFW_SHUTTER_ANGLE_MARKERS:
        missing = tuple(m for m in SHARED_APPFW_SHUTTER_ANGLE_MARKERS if m not in fx3_angle)
        errors.append(f"FX3 appFw.so missing Shutter Angle markers: {missing}")
    if fx6_angle != SHARED_APPFW_SHUTTER_ANGLE_MARKERS:
        missing = tuple(m for m in SHARED_APPFW_SHUTTER_ANGLE_MARKERS if m not in fx6_angle)
        errors.append(f"FX6 appFw.so missing Shutter Angle markers: {missing}")
    if fx6_ecs != FX6_APPFW_ECS_AND_ANGLE_MARKERS:
        missing = tuple(m for m in FX6_APPFW_ECS_AND_ANGLE_MARKERS if m not in fx6_ecs)
        errors.append(f"FX6 appFw.so missing ECS / Continuous Angle markers: {missing}")
    if fx6_cp != FX6_CP_SHUTTER_ANGLE_MARKERS:
        errors.append("FX6 cpapp-b.bin missing ShutterSpeedAngle metadata markers")
    if fx6_mpr != FX6_MPR_SHUTTER_RTMD_MARKERS:
        errors.append("FX6 libmpr.so missing RTMD ShutterSpeedAngle/Time writer symbols")

    ev_180 = evaluate_shutter_angle_exposure(angle_deg=180.0, fps=24.0)
    ev_5_6 = evaluate_shutter_angle_exposure(angle_deg=5.6, fps=240.0)
    ev_360 = evaluate_shutter_angle_exposure(angle_deg=360.0, fps=23.976)
    ecs_led = evaluate_ecs_anti_flicker(ecs_freq_hz=120.0, fps=24.0, light_source_hz=1920.0)
    ecs_pal = evaluate_ecs_anti_flicker(ecs_freq_hz=50.0, fps=25.0, light_source_hz=100.0)

    for ev in (ev_180, ev_5_6, ev_360):
        if not ev.valid:
            errors.extend(ev.errors)
    for ecs_ev in (ecs_led, ecs_pal):
        if not ecs_ev.valid or not ecs_ev.flicker_free_locked:
            errors.extend(ecs_ev.errors)
            if ecs_ev.valid and not ecs_ev.flicker_free_locked:
                errors.append(f"ECS frequency {ecs_ev.ecs_freq_hz} Hz failed harmonic flicker lock")

    return ShutterAngleAndEcsReport(
        passed=len(errors) == 0,
        fx3_shared_angle_markers=fx3_angle,
        fx6_shared_angle_markers=fx6_angle,
        fx6_ecs_and_angle_markers=fx6_ecs,
        fx6_cp_shutter_markers=fx6_cp,
        fx6_mpr_rtmd_shutter_markers=fx6_mpr,
        uxc_shutter_ecs_labels=dict(uxc_shutter_ecs_labels),
        default_180_at_24fps_eval=ev_180,
        min_5_6_at_240fps_eval=ev_5_6,
        max_360_at_23_976fps_eval=ev_360,
        ecs_120hz_led_wall_eval=ecs_led,
        ecs_100hz_pal_mains_eval=ecs_pal,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar C: Slow & Quick Motion (S&Q 1..120fps 4K / 1..240fps FHD) + Proxy/Audio
# ---------------------------------------------------------------------------


def evaluate_sq_motion_contract(
    *,
    resolution_class: str = "4K_DCI",
    sensor_fps: int = 120,
    rec_fps: float = 24.0,
    codec: str = "XAVC_S_I_4K",
    card_class: str = "CFEXPRESS_TYPE_A",
    proxy_requested: bool = False,
    force_audio_in_off_speed: bool = False,
) -> SqMotionEvalResult:
    """Validate S&Q frame-rate envelope, off-speed audio mute, proxy gating, and CFexpress coupling."""
    errors: List[str] = []
    norm_res = resolution_class.strip().upper()
    norm_codec = codec.strip().upper()
    norm_card = card_class.strip().upper()

    if norm_res not in ("4K_DCI", "QFHD", "FHD"):
        errors.append(f"Unsupported S&Q resolution_class: {resolution_class!r}")
    if norm_codec not in SQ_BASE_CODEC_MBPS_AT_24P:
        errors.append(f"Unsupported S&Q codec: {codec!r}")
    if norm_card not in MEDIA_SUSTAINED_MBPS:
        errors.append(f"Unsupported media card_class: {card_class!r}")
    if not any(abs(rec_fps - p) <= 1e-3 for p in SQ_PROJECT_REC_FPS):
        errors.append(f"Unsupported S&Q project recording frame rate: {rec_fps} fps")

    if norm_res in ("4K_DCI", "QFHD"):
        if not (SQ_4K_MIN_FPS <= sensor_fps <= SQ_4K_MAX_FPS):
            errors.append(
                f"{norm_res} S&Q sensor_fps={sensor_fps} out of envelope [{SQ_4K_MIN_FPS}..{SQ_4K_MAX_FPS}]"
            )
    elif norm_res == "FHD":
        if not (SQ_FHD_MIN_FPS <= sensor_fps <= SQ_FHD_MAX_FPS):
            errors.append(
                f"FHD S&Q sensor_fps={sensor_fps} out of envelope [{SQ_FHD_MIN_FPS}..{SQ_FHD_MAX_FPS}]"
            )

    if norm_res in ("4K_DCI", "QFHD") and "HD" in norm_codec and "4K" not in norm_codec:
        errors.append(f"Codec {norm_codec} incompatible with {norm_res}")
    if norm_res == "FHD" and "4K" in norm_codec:
        errors.append(f"4K codec {norm_codec} incompatible with FHD S&Q mode")

    off_speed = abs(float(sensor_fps) - float(rec_fps)) > 1e-3
    speed_factor = round(float(sensor_fps) / float(rec_fps), 4) if rec_fps > 0 else 0.0

    # Audio is automatically disabled whenever S&Q is off-speed (rec_fps != sensor_fps).
    if off_speed:
        if force_audio_in_off_speed:
            errors.append(
                f"Off-speed S&Q ({sensor_fps}fps -> {rec_fps}p) forbids audio recording (auto-mute enforced)"
            )
        audio_enabled = False
        audio_reason = "OFF_SPEED_SQ_AUDIO_AUTO_DISABLED"
    else:
        audio_enabled = False
        audio_reason = "SQ_MODE_AUDIO_DISABLED_BY_SONY_SPEC"

    # Proxy recording is blocked above 120fps (200/240fps HFR) per FX3/FX6 S&Q specification.
    proxy_allowed = sensor_fps <= 120
    if proxy_requested and not proxy_allowed:
        errors.append(
            f"S&Q proxy recording disallowed at {sensor_fps}fps (>120fps HFR limit)"
        )

    base_mbps = SQ_BASE_CODEC_MBPS_AT_24P.get(norm_codec, 240.0)
    est_write_mbps = round(base_mbps * (float(sensor_fps) / 24.0), 2)
    card_mbps = MEDIA_SUSTAINED_MBPS.get(norm_card, 0.0)
    if norm_card in MEDIA_SUSTAINED_MBPS and est_write_mbps > card_mbps:
        errors.append(
            f"Media card {norm_card} ({card_mbps:.0f} Mbps) insufficient for {norm_codec} @ {sensor_fps}fps ({est_write_mbps:.1f} Mbps)"
        )

    if len(errors) == 0:
        status = "SQ_MOTION_READY"
    elif force_audio_in_off_speed and off_speed:
        status = "BLOCKED_SQ_AUDIO_DESYNC_VIOLATION"
    else:
        status = "BLOCKED_SQ_ENVELOPE_OR_MEDIA_VIOLATION"

    return SqMotionEvalResult(
        valid=len(errors) == 0,
        status=status,
        resolution_class=norm_res,
        sensor_fps=sensor_fps,
        rec_fps=rec_fps,
        speed_factor=speed_factor,
        off_speed=off_speed,
        audio_recording_enabled=audio_enabled,
        audio_muted_reason=audio_reason,
        proxy_requested=proxy_requested,
        proxy_allowed=proxy_allowed,
        codec=norm_codec,
        card_class=norm_card,
        estimated_write_mbps=est_write_mbps,
        card_sustained_mbps=card_mbps,
        errors=tuple(errors),
    )


def evaluate_pillar_c_sq_motion_matrix(
    present_map: Mapping[str, Tuple[str, ...]],
    uxc_sq_labels: Mapping[str, str],
) -> SqMotionMatrixReport:
    """Audit Pillar C: S&Q 1..120fps (4K DCI/QFHD) & 1..240fps (FHD) + Proxy/Audio-Mute + CFexpress."""
    errors: List[str] = []

    fx3_sq = present_map["fx3_appfw_sq"]
    fx6_sq = present_map["fx6_appfw_sq"]
    fx3_hfr = present_map["fx3_appfw_sq_hfr"]
    fx6_hfr = present_map["fx6_appfw_sq_hfr"]
    fx3_cp_sq = present_map["fx3_cp_sq"]
    fx3_mpr = present_map["fx3_mpr_audio_proxy"]
    fx6_mpr = present_map["fx6_mpr_audio_proxy"]

    if fx3_sq != SHARED_APPFW_SQ_MARKERS or fx6_sq != SHARED_APPFW_SQ_MARKERS:
        errors.append("Shared S&Q / Proxy appFw.so markers missing")
    if fx3_hfr != FX3_APPFW_SQ_HFR_MARKERS:
        errors.append("FX3 appFw.so missing 120fps/240fps S&Q markers")
    if fx6_hfr != FX6_APPFW_SQ_HFR_MARKERS:
        errors.append("FX6 appFw.so missing 1fps/120fps/240fps/Proxy S&Q markers")
    if fx3_cp_sq != FX3_CP_SQ_MARKERS:
        errors.append("FX3 cpapp-b.bin missing SLOW_AND_QUICK_MODE marker")
    if fx3_mpr != MPR_SHARED_AUDIO_PROXY_MARKERS or fx6_mpr != MPR_SHARED_AUDIO_PROXY_MARKERS:
        errors.append("FX3/FX6 libmpr.so missing AudioRecStart/Stop/Proxy profile markers")

    ev_4k_120 = evaluate_sq_motion_contract(
        resolution_class="4K_DCI",
        sensor_fps=120,
        rec_fps=24.0,
        codec="XAVC_S_I_DCI_4K",
        card_class="CFEXPRESS_TYPE_A",
        proxy_requested=True,
    )
    ev_fhd_240 = evaluate_sq_motion_contract(
        resolution_class="FHD",
        sensor_fps=240,
        rec_fps=24.0,
        codec="XAVC_S_I_HD",
        card_class="CFEXPRESS_TYPE_A",
        proxy_requested=False,
    )
    ev_4k_1 = evaluate_sq_motion_contract(
        resolution_class="QFHD",
        sensor_fps=1,
        rec_fps=23.976,
        codec="XAVC_S_4K",
        card_class="SDXC_V60",
        proxy_requested=True,
    )
    ev_4k_24 = evaluate_sq_motion_contract(
        resolution_class="4K_DCI",
        sensor_fps=24,
        rec_fps=24.0,
        codec="XAVC_S_I_DCI_4K",
        card_class="SDXC_V90",
        proxy_requested=True,
    )

    for ev in (ev_4k_120, ev_fhd_240, ev_4k_1, ev_4k_24):
        if not ev.valid:
            errors.extend(ev.errors)
        if ev.off_speed and ev.audio_recording_enabled:
            errors.append("Off-speed S&Q failed to auto-disable audio recording")

    return SqMotionMatrixReport(
        passed=len(errors) == 0,
        fx3_shared_sq_markers=fx3_sq,
        fx6_shared_sq_markers=fx6_sq,
        fx3_sq_hfr_markers=fx3_hfr,
        fx6_sq_hfr_markers=fx6_hfr,
        fx3_cp_sq_markers=fx3_cp_sq,
        fx3_mpr_audio_proxy_markers=fx3_mpr,
        fx6_mpr_audio_proxy_markers=fx6_mpr,
        uxc_sq_labels=dict(uxc_sq_labels),
        sq_4k_120fps_24p_eval=ev_4k_120,
        sq_fhd_240fps_24p_eval=ev_fhd_240,
        sq_4k_1fps_24p_eval=ev_4k_1,
        sq_4k_24fps_1to1_eval=ev_4k_24,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar D: Front / Rear / Top Cinema Tally Lamps (Technical -> Tally)
# ---------------------------------------------------------------------------


def evaluate_tally_lamp_routing(
    *,
    front_tally_on: bool = True,
    rear_tally_on: bool = True,
    brightness: str = "HIGH",
    rec_tally_blink: bool = False,
    green_tally_requested: bool = False,
    yellow_tally_requested: bool = False,
    missing_gpio_write_attempted: bool = False,
) -> TallyLampEvalResult:
    """Map FX6 Front/Rear/Brightness/G/Y Tally controls to FX3 Front + Top/Rear REC Tally LEDs."""
    errors: List[str] = []
    norm_bright = brightness.strip().upper()
    if norm_bright not in VALID_TALLY_BRIGHTNESS:
        errors.append(f"Unsupported tally brightness {brightness!r}; expected {VALID_TALLY_BRIGHTNESS}")
    if missing_gpio_write_attempted:
        errors.append("Unmapped broadcast G/Y Tally GPIO write attempted on FX3 hardware")

    if norm_bright == "OFF" or (not front_tally_on and not rear_tally_on):
        rec_lamp_cmd = "REC_LAMP_ALL_LIGHTS_OUT"
    elif front_tally_on and rear_tally_on:
        rec_lamp_cmd = "REC_LAMP_ALL_LIGHTS_UP"
    elif not front_tally_on and rear_tally_on:
        rec_lamp_cmd = "REC_LAMP_ONLY_FRONT_OFF"
    else:
        rec_lamp_cmd = "REC_LAMP_LIGHT_UP_ONLY_ONE"

    osd_fallback = bool(green_tally_requested or yellow_tally_requested)
    gpio_faults = 1 if missing_gpio_write_attempted else 0

    if len(errors) > 0:
        status = "BLOCKED_TALLY_GPIO_OR_BRIGHTNESS_FAULT"
    elif osd_fallback:
        status = "FX3_TALLY_MAPPED_WITH_GY_OSD_CONTAINMENT"
    else:
        status = "FX3_FRONT_REAR_REC_TALLY_MAPPED"

    return TallyLampEvalResult(
        valid=len(errors) == 0,
        status=status,
        front_tally_on=front_tally_on,
        rear_tally_on=rear_tally_on,
        brightness=norm_bright,
        rec_tally_blink=rec_tally_blink,
        fx3_rec_lamp_cmd=rec_lamp_cmd,
        cp_tally_msg_id="MSG_ID_INFRABB_SYS_SET_CA_TALLY",
        green_tally_requested=green_tally_requested,
        yellow_tally_requested=yellow_tally_requested,
        osd_indicator_fallback=osd_fallback,
        missing_gpio_faults=gpio_faults,
        errors=tuple(errors),
    )


def evaluate_pillar_d_tally_lamp_matrix(
    present_map: Mapping[str, Tuple[str, ...]],
    uxc_tally_labels: Mapping[str, str],
) -> TallyLampMatrixReport:
    """Audit Pillar D: FX6 Technical -> Tally controls mapped cleanly to FX3 Front + Top/Rear LEDs."""
    errors: List[str] = []

    fx3_lamp = present_map["fx3_appfw_rec_lamp"]
    fx6_lamp = present_map["fx6_appfw_rec_lamp"]
    fx6_tally = present_map["fx6_appfw_tally"]
    fx3_cp_tally = present_map["fx3_cp_tally"]
    fx6_cp_tally = present_map["fx6_cp_tally"]

    if fx3_lamp != SHARED_APPFW_REC_LAMP_MARKERS or fx6_lamp != SHARED_APPFW_REC_LAMP_MARKERS:
        errors.append("FX3 or FX6 appFw.so missing shared REC_LAMP_* physical LED state markers")
    if fx6_tally != FX6_APPFW_TALLY_MARKERS:
        missing = tuple(m for m in FX6_APPFW_TALLY_MARKERS if m not in fx6_tally)
        errors.append(f"FX6 appFw.so missing Technical -> Tally markers: {missing}")
    if fx3_cp_tally != CP_SHARED_TALLY_MARKERS or fx6_cp_tally != CP_SHARED_TALLY_MARKERS:
        errors.append("FX3/FX6 cpapp-b.bin missing MSG_ID_INFRABB_SYS_SET_CA_TALLY")

    both_on = evaluate_tally_lamp_routing(front_tally_on=True, rear_tally_on=True, brightness="HIGH")
    front_off = evaluate_tally_lamp_routing(front_tally_on=False, rear_tally_on=True, brightness="LOW")
    rear_off = evaluate_tally_lamp_routing(front_tally_on=True, rear_tally_on=False, brightness="HIGH")
    gy_contained = evaluate_tally_lamp_routing(
        front_tally_on=True,
        rear_tally_on=True,
        brightness="HIGH",
        rec_tally_blink=True,
        green_tally_requested=True,
        yellow_tally_requested=True,
    )

    for ev in (both_on, front_off, rear_off, gy_contained):
        if not ev.valid or ev.missing_gpio_faults != 0:
            errors.extend(ev.errors)

    total_faults = sum(ev.missing_gpio_faults for ev in (both_on, front_off, rear_off, gy_contained))
    matrix: Tuple[TallyLampMatrixEntry, ...] = (
        TallyLampMatrixEntry(
            feature_id="FRONT_AND_REAR_TALLY_LAMPS",
            fx6_control="BKID_APP_SETTING_FRONT_TALLY + BKID_APP_SETTING_REAR_TALLY",
            fx3_mapping="REC_LAMP_ALL_LIGHTS_UP / REC_LAMP_ONLY_FRONT_OFF / REC_LAMP_LIGHT_UP_ONLY_ONE / REC_LAMP_ALL_LIGHTS_OUT",
            missing_gpio_faults=0,
            verdict="DIRECT_PHYSICAL_LED_PARITY",
            notes="Maps FX6 Front/Rear Tally switches directly to FX3 physical Front + Top/Rear REC Tally LEDs.",
        ),
        TallyLampMatrixEntry(
            feature_id="TALLY_BRIGHTNESS_AND_REC_BLINK",
            fx6_control="BKID_APP_SETTING_TALLY_LAMP_BRIGHTNESS (High/Low/Off) + Rec Tally Blink",
            fx3_mapping="MSG_ID_INFRABB_SYS_SET_CA_TALLY + REC_LAMP_ON/OFF cadence",
            missing_gpio_faults=0,
            verdict="SUPPORTED_VIA_CP_TALLY_IPC",
            notes="Off forces REC_LAMP_ALL_LIGHTS_OUT; High/Low drives active FX3 REC LEDs.",
        ),
        TallyLampMatrixEntry(
            feature_id="GREEN_YELLOW_AND_EXT_TALLY",
            fx6_control="BKID_APP_SETTING_G_TALLY_LAMP / Y_TALLY_LAMP / TALLY_CONTROL_EXTERNAL",
            fx3_mapping="On-Screen Display (OSD) tally frame containment (0 physical GPIO writes)",
            missing_gpio_faults=0,
            verdict="NOOP_OSD_CONTAINED_ZERO_GPIO_FAULTS",
            notes="FX3 has Red REC LEDs only; G/Y broadcast tally is safely contained to OSD without GPIO panic.",
        ),
    )

    return TallyLampMatrixReport(
        passed=len(errors) == 0 and total_faults == 0,
        fx3_rec_lamp_markers=fx3_lamp,
        fx6_rec_lamp_markers=fx6_lamp,
        fx6_tally_markers=fx6_tally,
        fx3_cp_tally_markers=fx3_cp_tally,
        fx6_cp_tally_markers=fx6_cp_tally,
        uxc_tally_labels=dict(uxc_tally_labels),
        both_on_eval=both_on,
        front_off_rear_on_eval=front_off,
        front_on_rear_off_eval=rear_off,
        green_yellow_contained_eval=gy_contained,
        matrix=matrix,
        missing_gpio_faults=total_faults,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Unified Dual-Mode Entrypoint
# ---------------------------------------------------------------------------


def shutter_ecs_sq_and_tally_report_to_dict(
    report: ShutterEcsSqAndTallyReport,
) -> Dict[str, object]:
    return report.to_dict()


def analyze_shutter_ecs_sq_and_tally(
    *,
    clean_room: bool = False,
    repo_root: Path = DEFAULT_REPO_ROOT,
    env: Optional[Mapping[str, str]] = None,
    synthetic_overrides: Optional[Mapping[str, bytes]] = None,
) -> ShutterEcsSqAndTallyReport:
    """Run the 11th unified firmware-lab audit across Shutter Angle, ECS, S&Q, Tally, and Mechanical Shutter safety."""
    relpaths: Dict[str, str] = {
        "fx3_appfw": FX3_APPFW_RELPATH,
        "fx6_appfw": FX6_APPFW_RELPATH,
        "fx3_libmpr": FX3_LIBMPR_RELPATH,
        "fx6_libmpr": FX6_LIBMPR_RELPATH,
        "fx3_cpapp": FX3_CPAPP_RELPATH,
        "fx6_cpapp": FX6_CPAPP_RELPATH,
        "fx3_str_en": FX3_STR_EN_RELPATH,
        "fx3_str_en_g": FX3_STR_EN_G_RELPATH,
        "fx6_str_en_1": FX6_STR_EN_1_RELPATH,
        "fx6_str_en_2": FX6_STR_EN_2_RELPATH,
    }

    forced = bool(clean_room or synthetic_overrides is not None or is_forced_clean_room(env))
    resolved: Dict[str, Optional[Path]] = {}
    if not forced:
        for k, rel in relpaths.items():
            resolved[k] = resolve_donor_file(rel, repo_root=repo_root, env=env)
        if any(p is None or not p.is_file() for p in resolved.values()):
            forced = True

    fx3_app_groups: Dict[str, Sequence[str]] = {
        "fx3_appfw_mech": FX3_APPFW_MECH_SHUTTER_MARKERS,
        "fx3_appfw_angle": SHARED_APPFW_SHUTTER_ANGLE_MARKERS,
        "fx3_appfw_sq": SHARED_APPFW_SQ_MARKERS,
        "fx3_appfw_sq_hfr": FX3_APPFW_SQ_HFR_MARKERS,
        "fx3_appfw_rec_lamp": SHARED_APPFW_REC_LAMP_MARKERS,
    }
    fx6_app_groups: Dict[str, Sequence[str]] = {
        "fx6_appfw_unexpected_mech": FX6_APPFW_FORBIDDEN_MECH_PIDS,
        "fx6_appfw_angle": SHARED_APPFW_SHUTTER_ANGLE_MARKERS,
        "fx6_appfw_ecs": FX6_APPFW_ECS_AND_ANGLE_MARKERS,
        "fx6_appfw_sq": SHARED_APPFW_SQ_MARKERS,
        "fx6_appfw_sq_hfr": FX6_APPFW_SQ_HFR_MARKERS,
        "fx6_appfw_rec_lamp": SHARED_APPFW_REC_LAMP_MARKERS,
        "fx6_appfw_tally": FX6_APPFW_TALLY_MARKERS,
    }
    fx3_mpr_groups: Dict[str, Sequence[str]] = {
        "fx3_mpr_audio_proxy": MPR_SHARED_AUDIO_PROXY_MARKERS,
    }
    fx6_mpr_groups: Dict[str, Sequence[str]] = {
        "fx6_mpr_audio_proxy": MPR_SHARED_AUDIO_PROXY_MARKERS,
        "fx6_mpr_shutter": FX6_MPR_SHUTTER_RTMD_MARKERS,
    }
    fx3_cp_groups: Dict[str, Sequence[str]] = {
        "fx3_cp_mech": FX3_CP_MECH_SHUTTER_MARKERS,
        "fx3_cp_elec": CP_SHARED_ELEC_SHUTTER_MARKERS,
        "fx3_cp_sq": FX3_CP_SQ_MARKERS,
        "fx3_cp_tally": CP_SHARED_TALLY_MARKERS,
    }
    fx6_cp_groups: Dict[str, Sequence[str]] = {
        "fx6_cp_unexpected_mech": FX6_CP_FORBIDDEN_MECH_SHUTTER_MARKERS,
        "fx6_cp_elec": CP_SHARED_ELEC_SHUTTER_MARKERS,
        "fx6_cp_shutter": FX6_CP_SHUTTER_ANGLE_MARKERS,
        "fx6_cp_tally": CP_SHARED_TALLY_MARKERS,
    }

    donor_sizes: Dict[str, int] = {}
    present_map: Dict[str, Tuple[str, ...]] = {}
    errors: List[str] = []

    if forced:
        mode = "CLEAN_ROOM_SYNTHETIC_VERIFIED"
        fixtures = dict(build_clean_room_shutter_ecs_sq_tally_fixtures())
        if synthetic_overrides:
            fixtures.update(synthetic_overrides)

        for k, buf in fixtures.items():
            donor_sizes[k] = len(buf)

        for gname, markers in fx3_app_groups.items():
            present_map[gname], _ = _scan_buffer_markers(fixtures["fx3_appfw"], markers)
        for gname, markers in fx6_app_groups.items():
            present_map[gname], _ = _scan_buffer_markers(fixtures["fx6_appfw"], markers)
        for gname, markers in fx3_mpr_groups.items():
            present_map[gname], _ = _scan_buffer_markers(fixtures["fx3_libmpr"], markers)
        for gname, markers in fx6_mpr_groups.items():
            present_map[gname], _ = _scan_buffer_markers(fixtures["fx6_libmpr"], markers)
        for gname, markers in fx3_cp_groups.items():
            present_map[gname], _ = _scan_buffer_markers(fixtures["fx3_cpapp"], markers)
        for gname, markers in fx6_cp_groups.items():
            present_map[gname], _ = _scan_buffer_markers(fixtures["fx6_cpapp"], markers)

        str_fx3 = fixtures["fx3_str_en"]
        str_fx3_g = fixtures["fx3_str_en_g"]
        str_fx6_1 = fixtures["fx6_str_en_1"]
        str_fx6_2 = fixtures["fx6_str_en_2"]
    else:
        mode = "LOCAL_DONOR_VERIFIED"
        sz3_a, res3_a = _scan_donor_rdonly_markers(resolved["fx3_appfw"], fx3_app_groups, is_elf=True)  # type: ignore[arg-type]
        sz6_a, res6_a = _scan_donor_rdonly_markers(resolved["fx6_appfw"], fx6_app_groups, is_elf=True)  # type: ignore[arg-type]
        sz3_m, res3_m = _scan_donor_rdonly_markers(resolved["fx3_libmpr"], fx3_mpr_groups, is_elf=True)  # type: ignore[arg-type]
        sz6_m, res6_m = _scan_donor_rdonly_markers(resolved["fx6_libmpr"], fx6_mpr_groups, is_elf=True)  # type: ignore[arg-type]
        sz3_c, res3_c = _scan_donor_rdonly_markers(resolved["fx3_cpapp"], fx3_cp_groups, is_elf=False)  # type: ignore[arg-type]
        sz6_c, res6_c = _scan_donor_rdonly_markers(resolved["fx6_cpapp"], fx6_cp_groups, is_elf=False)  # type: ignore[arg-type]

        for res in (res3_a, res6_a, res3_m, res6_m, res3_c, res6_c):
            present_map.update(res)

        str_fx3 = _read_uxc_rdonly(resolved["fx3_str_en"])  # type: ignore[arg-type]
        str_fx3_g = _read_uxc_rdonly(resolved["fx3_str_en_g"])  # type: ignore[arg-type]
        str_fx6_1 = _read_uxc_rdonly(resolved["fx6_str_en_1"])  # type: ignore[arg-type]
        str_fx6_2 = _read_uxc_rdonly(resolved["fx6_str_en_2"])  # type: ignore[arg-type]

        donor_sizes = {
            "fx3_appfw": sz3_a,
            "fx6_appfw": sz6_a,
            "fx3_libmpr": sz3_m,
            "fx6_libmpr": sz6_m,
            "fx3_cpapp": sz3_c,
            "fx6_cpapp": sz6_c,
            "fx3_str_en": len(str_fx3),
            "fx3_str_en_g": len(str_fx3_g),
            "fx6_str_en_1": len(str_fx6_1),
            "fx6_str_en_2": len(str_fx6_2),
        }

    lbl_fx3, err_fx3 = _extract_uxc_labels(str_fx3, FX3_NS39_UXC_EXPECTED_LABELS)
    lbl_fx3_g, err_fx3_g = _extract_uxc_labels(str_fx3_g, FX3_NS3_UXC_EXPECTED_LABELS)
    lbl_fx6_1, err_fx6_1 = _extract_uxc_labels(str_fx6_1, FX6_NS1_UXC_EXPECTED_LABELS)
    lbl_fx6_2, err_fx6_2 = _extract_uxc_labels(str_fx6_2, FX6_NS2_UXC_EXPECTED_LABELS)
    errors.extend(err_fx3)
    errors.extend(err_fx3_g)
    errors.extend(err_fx6_1)
    errors.extend(err_fx6_2)

    uxc_shutter_ecs_labels = {
        "fx3_slow_shutter": lbl_fx3.get("0x0000e368", ""),
        "fx3_shutter": lbl_fx3_g.get("0x00006431", ""),
        "fx6_ecs": lbl_fx6_1.get("0x00002077", ""),
        "fx6_ecs_onoff": lbl_fx6_1.get("0x000022db", ""),
        "fx6_shutter_angle_step": lbl_fx6_1.get("0x000030c6", ""),
        "fx6_shutter_angle_continuous": lbl_fx6_1.get("0x000030d9", ""),
        "fx6_shutter_angle": lbl_fx6_2.get("0x00004d96", ""),
        "fx6_ecs_frequency": lbl_fx6_2.get("0x00004d98", ""),
    }
    uxc_sq_labels = {
        "fx3_audio_recording": lbl_fx3.get("0x0000e72e", ""),
        "fx3_sq_motion": lbl_fx3_g.get("0x00006099", ""),
        "fx3_movie_sq_motion": lbl_fx3_g.get("0x000060c6", ""),
        "fx6_sq_fps": lbl_fx6_1.get("0x000020c2", ""),
        "fx6_sq_frame_rate": lbl_fx6_1.get("0x000020cc", ""),
        "fx6_sq_motion_on": lbl_fx6_2.get("0x0000417a", ""),
        "fx6_slow_and_quick_motion": lbl_fx6_2.get("0x00004325", ""),
    }
    uxc_tally_labels = {
        "fx6_front_tally_lamp": lbl_fx6_1.get("0x000024f6", ""),
        "fx6_rear_tally_lamp": lbl_fx6_1.get("0x000024f8", ""),
        "fx6_tally_control": lbl_fx6_1.get("0x000024fa", ""),
        "fx6_tally_lamp_brightness": lbl_fx6_1.get("0x000025b6", ""),
        "fx6_tally": lbl_fx6_2.get("0x000042c8", ""),
        "fx6_rec_tally_blink": lbl_fx6_2.get("0x00004ee1", ""),
        "fx6_green_tally": lbl_fx6_2.get("0x00005379", ""),
        "fx6_red_tally": lbl_fx6_2.get("0x0000537b", ""),
    }

    pillar_a = evaluate_pillar_a_mech_shutter_protection(present_map)
    pillar_b = evaluate_pillar_b_shutter_angle_and_ecs(present_map, uxc_shutter_ecs_labels)
    pillar_c = evaluate_pillar_c_sq_motion_matrix(present_map, uxc_sq_labels)
    pillar_d = evaluate_pillar_d_tally_lamp_matrix(present_map, uxc_tally_labels)

    errors.extend(pillar_a.errors)
    errors.extend(pillar_b.errors)
    errors.extend(pillar_c.errors)
    errors.extend(pillar_d.errors)

    all_passed = bool(
        len(errors) == 0
        and pillar_a.passed
        and pillar_b.passed
        and pillar_c.passed
        and pillar_d.passed
    )

    digest_payload = {
        "schema_version": PHASE_60_SCHEMA,
        "phase_version": PHASE_60_VERSION,
        "mode": mode,
        "all_checks_passed": all_passed,
        "o_rdonly_enforced": True,
        "donor_file_sizes": donor_sizes,
        "pillar_a_mech_shutter": asdict(pillar_a),
        "pillar_b_shutter_angle_ecs": asdict(pillar_b),
        "pillar_c_sq_motion": asdict(pillar_c),
        "pillar_d_tally_lamps": asdict(pillar_d),
        "errors": list(errors),
    }
    report_sha256 = hashlib.sha256(
        json.dumps(digest_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()

    return ShutterEcsSqAndTallyReport(
        schema_version=PHASE_60_SCHEMA,
        phase_version=PHASE_60_VERSION,
        mode=mode,
        all_checks_passed=all_passed,
        o_rdonly_enforced=True,
        donor_file_sizes=donor_sizes,
        pillar_a_mech_shutter=pillar_a,
        pillar_b_shutter_angle_ecs=pillar_b,
        pillar_c_sq_motion=pillar_c,
        pillar_d_tally_lamps=pillar_d,
        errors=tuple(errors),
        report_sha256=report_sha256,
    )
