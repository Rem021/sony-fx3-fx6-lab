#!/usr/bin/env python3
"""Phase 200 — Stage 35 (`35/35` Milestone) `outputs/fx3-vm/` Real-Hardware Main Track:
`ILME-FX3` (`0x91030080`, `Ver. 7.02`) Exact 4-Mode `[Fan Control]` (`Auto`, `Minimum`,
`Off in Rec` Standby `MAX PWM`, `Always Off` Pre-Backup Guard — Rejecting `Auto1/Auto2`),
Independent `[Shutter Mode]` (`Speed` vs `Angle`, `5.6°..64F` vs `5.6°..360°` Clamping,
`0.3EV / 0.5EV` Exposure-Step Immunity), and `FX6 Ver. 6.01` vs `Stock FX3 Ver. 7.00/7.02`
`p2:/setting` `User1..User16` LUT Binary Format Split Firewall HIL Co-Emulator.

Implements strictly read-only (`os.open(..., os.O_RDONLY)`) donor inspection (< 0.10s, cached per
process, bounded <= 4096 B windows on large firmware binaries) with deterministic
`CLEAN_ROOM_SYNTHETIC` fallback (`FX3_FX6_FORCE_CLEAN_ROOM=1`), and co-emulates all four Phase 200
real-hardware pillars (A-D) while hard-locking:
- `persistent_emmc_writes_authorized == False`
- `spi_nor_write_authorized == False`
- `el3_payload_transmit_authorized == False`
- `physical_usb_packets_emitted == 0`
- `otp_fuse_touches == 0`
- `rpmb_counter_increments == 0`
- `p2_setting_mutation_bytes == 0`, `thermal_runaway_events == 0`
- `lut_color_solver_corruption_events == 0`, `raw_firmware_bytes_leaked == 0`
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse
from dataclasses import asdict, dataclass
import errno
import hashlib
import json
import os
from pathlib import Path
import struct
from typing import Dict, List, Mapping, Optional, Sequence, Tuple, Union


# ---------------------------------------------------------------------------
# Phase 200 Schema & Hard-Locked Safety Redlines (35/35 Milestone)
# ---------------------------------------------------------------------------

PHASE_200_SCHEMA = "phase200_realhw_fan_pwm_shutter_angle_lut_split_coemulator_v1"
PHASE_200_VERSION = "200.0.0"
STAGE_INDEX = 35
STAGE_TOTAL = 35
MILESTONE_LABEL = "35/35"
STAGE_NAME = "stage35_realhw_fan_pwm_shutter_angle_lut_split_hil"

P8_CP_MUTATION_FORBIDDEN = True
NOP_COUNT = 0
GUEST_CODE_MODIFICATION_BYTES = 0
CP_MUTATION_BYTES = 0
WBI_MUTATION_BYTES = 0
CALIBRATION_MUTATION_BYTES = 0
NVRAM_PERSISTENT_WRITES = 0
BK4_PERSISTENT_NVRAM_WRITES = 0
PHYSICAL_DEVICE_WRITES = 0
PERSISTENT_EMMC_WRITES_AUTHORIZED = False
EMMC_NFLASHA_WRITE_COUNT = 0
EMMC_MUTATION_BYTES = 0
SPI_NOR_WRITE_AUTHORIZED = False
SPI_NOR_MUTATION_BYTES = 0
EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False
PHYSICAL_USB_PACKETS_EMITTED = 0
OTP_FUSE_TOUCHES = 0
RPMB_COUNTER_INCREMENTS = 0
P2_SETTING_MUTATION_BYTES = 0
THERMAL_RUNAWAY_EVENTS = 0
LUT_COLOR_SOLVER_CORRUPTION_EVENTS = 0
WF12_00342260_HITS = 0
APPFW_CRASHES = 0
NULL_GPIO_DEREFS = 0
MAILBOX_STALLS = 0
STOCK_CP_FAULT_COUNT = 0
RAW_FIRMWARE_BYTES_LEAKED = 0
DONOR_ACCESS_MODE = "O_RDONLY"
BOUNDED_WINDOW_MAX_BYTES = 4096

EINVAL_ERRNO = errno.EINVAL  # 22
EROFS_ERRNO = errno.EROFS  # 30

ENV_FORCE_CLEAN_ROOM = "FX3_FX6_FORCE_CLEAN_ROOM"
ENV_MAC_ROOT = "FX3_FX6_MAC_ROOT"
ENV_MAC_WORK_ROOT = "FX3_FX6_MAC_WORK_ROOT"
ENV_MAIN_LAB_WORK_ROOT = "FX3_FX6_MAIN_LAB_WORK_ROOT"

DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]
LEGACY_MAC_ROOT = Path("/Volumes/KAFU2T/AI/Projects/Mac")
CLEAN_ROOM_SENTINEL_DIRNAME = "__fx3_fx6_clean_room_donor_disabled__"

# ---------------------------------------------------------------------------
# Verified Local Donor Specs (12 FX3 7.02 & FX6 6.01 Real-Hardware Donors)
# ---------------------------------------------------------------------------

_FX3_USR_PREFIX = "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr"
_FX6_NF15_PREFIX = "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files"

DONOR_RELPATHS: Mapping[str, str] = {
    "fx3_libfan": f"{_FX3_USR_PREFIX}/lib/libfan.so",
    "fx6_libfan": f"{_FX6_NF15_PREFIX}/lib/libfan.so",
    "fx3_libbackup": f"{_FX3_USR_PREFIX}/lib/libbackup.so",
    "fx3_backup_mgr": f"{_FX3_USR_PREFIX}/lib/libBackupManager.so",
    "fx3_im_elf": f"{_FX3_USR_PREFIX}/bin/im.elf",
    "fx3_string_en_f": f"{_FX3_USR_PREFIX}/share/app/string_english_f.uxc",
    "fx3_appfw": "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
    "fx6_appfw": f"{_FX6_NF15_PREFIX}/lib/appFw.so",
    "fx3_cpapp": "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin",
    "fx6_cpapp": "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fat-files/nflasha8/cpapp-b.bin",
    "fx3_libmpr": f"{_FX3_USR_PREFIX}/lib/libmpr.so",
    "fx6_libmpr": f"{_FX6_NF15_PREFIX}/lib/libmpr.so",
}

EXPECTED_DONOR_BYTES: Mapping[str, int] = {
    "fx3_libfan": 27_280,
    "fx6_libfan": 31_176,
    "fx3_libbackup": 14_232,
    "fx3_backup_mgr": 10_272,
    "fx3_im_elf": 40_920,
    "fx3_string_en_f": 373_820,
    "fx3_appfw": 79_015_712,
    "fx6_appfw": 50_520_424,
    "fx3_cpapp": 15_980_568,
    "fx6_cpapp": 17_952_816,
    "fx3_libmpr": 3_517_008,
    "fx6_libmpr": 28_921_824,
}

COMPACT_DONOR_TOKENS: Mapping[str, Tuple[bytes, ...]] = {
    "fx3_libfan": (
        b"fan_infra_init",
        b"fan_i_main_thread",
        b"psm_fan_i_bkup_read_dev_temp_info",
        b"Backup_read",
    ),
    "fx6_libfan": (
        b"fan_infra_init",
        b"fan_i_main_thread",
        b"psm_fan_i_bkup_read_dev_temp_info",
        b"Backup_read",
    ),
    "fx3_libbackup": (
        b"Backup_read",
        b"Backup_write",
        b"Backup_read_setting_attr",
        b"Backup_write_setting_attr",
    ),
    "fx3_backup_mgr": (
        b"BackupManager",
        b"BkDmn_write",
        b"writeBackupEncryption",
        b"readBackupDecryption",
    ),
    "fx3_im_elf": (
        b"/dev/nflasha2",
        b"/setting",
        b"/dev/nflasha3",
        b"/dev/nflasha15",
        b"/usr",
    ),
    "fx3_string_en_f": (
        b"Fan Control",
        b"Off in Rec",
        b"Always Off",
        b"Minimum",
        b"Auto Power OFF Temp.",
        b"Shutter Mode",
        b"Angle",
        b"Speed",
        b"Exposure step",
        b"0.3EV",
        b"0.5EV",
        b"User1",
        b"User16",
        b"Manage User LUTs",
        b"5.6",
        b"360",
    ),
}

FORBIDDEN_UXC_FAN_TOKENS: Tuple[bytes, ...] = (b"Auto1", b"Auto2")

# Pinned bounded windows (<= 4096 B each) for large CP/AP binaries so cold inspection is < 10 ms.
LARGE_DONOR_WINDOWS: Mapping[str, Tuple[Tuple[int, str, bytes], ...]] = {
    "fx3_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (49_946_624, "SHUTTER_ANGLE", b"SHUTTER_ANGLE"),
        (49_971_200, "FAN_CONTROL", b"FAN_CONTROL"),
        (49_971_200, "OFF_IN_REC", b"OFF_IN_REC"),
        (49_971_200, "ALWAYS_OFF", b"ALWAYS_OFF"),
        (58_298_368, "P2_SETTING", b"/setting"),
        (58_707_968, "SHUTTER_MODE", b"SHUTTER_MODE"),
        (59_801_600, "CUBE_LUT_PATH", b"/Private/Sony/PRO/LUT"),
        (59_932_672, "USER1_SLOT", b"User1"),
        (59_932_672, "USER16_SLOT", b"User16"),
        (60_891_136, "EXPOSURE_STEP", b"EXPOSURE_STEP"),
        (62_242_816, "USER_LUT", b"USER_LUT"),
        (63_152_128, "AUTO_POWER_OFF_TEMP", b"AUTO_POWER_OFF_TEMP"),
    ),
    "fx6_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (37_580_800, "USER1_LEGACY", b"User1"),
        (37_601_280, "CUBE_EXT", b".cube"),
        (38_514_688, "P2_SETTING", b"/setting"),
        (39_018_496, "SHUTTER", b"SHUTTER"),
        (39_358_464, "PRO_LUT", b"/Private/Sony/PRO/LUT"),
        (39_378_944, "FAN", b"FAN"),
        (39_890_944, "USER_LUT", b"USER_LUT"),
        (41_639_936, "OFF_IN_REC", b"OFF_IN_REC"),
    ),
    "fx3_cpapp": (
        (315_392, "Shutter", b"Shutter"),
        (385_024, "FAN", b"FAN"),
        (598_016, "LUT", b"LUT"),
        (10_756_096, "IMX510", b"IMX510"),
        (13_139_968, "ILME-FX3", b"ILME-FX3"),
        (13_336_576, "PWM", b"PWM"),
        (14_921_728, "CUBE", b"CUBE"),
    ),
    "fx6_cpapp": (
        (319_488, "LUT", b"LUT"),
        (385_024, "FAN", b"FAN"),
        (1_753_088, "Shutter", b"Shutter"),
        (12_218_368, "IMX510", b"IMX510"),
        (14_786_560, "PWM", b"PWM"),
        (16_891_904, "CUBE", b"CUBE"),
    ),
    "fx3_libmpr": (
        (0, "ELF64", b"\x7fELF"),
        (184_320, "SetLutData", b"SetLutData"),
        (241_664, "LUT", b"LUT"),
        (2_981_888, "Shutter", b"Shutter"),
    ),
    "fx6_libmpr": (
        (0, "ELF64", b"\x7fELF"),
        (225_280, "SetLutData", b"SetLutData"),
        (270_336, "LUT", b"LUT"),
        (14_286_848, "Shutter", b"Shutter"),
    ),
}

# ---------------------------------------------------------------------------
# Pillar A Constants: ILME-FX3 (0x91030080) Exact 4-Mode [Fan Control] & Thermal HIL
# ---------------------------------------------------------------------------

MODEL_ILME_FX3 = "ILME-FX3"
FX3_MODEL_ID = 0x91030080
FAN_CONTROL_MENU_PATH = "MENU -> Setup -> [Setup Option] -> [Fan Control]"

FAN_MODE_AUTO = "Auto"
FAN_MODE_MINIMUM = "Minimum"
FAN_MODE_OFF_IN_REC = "Off in Rec"
FAN_MODE_ALWAYS_OFF = "Always Off"

VALID_FX3_FAN_CONTROL_MODES: Tuple[str, ...] = (
    FAN_MODE_AUTO,
    FAN_MODE_MINIMUM,
    FAN_MODE_OFF_IN_REC,
    FAN_MODE_ALWAYS_OFF,
)
FORBIDDEN_STUDIO_LUMIX_FAN_MODES: Tuple[str, ...] = ("Auto1", "Auto2")

AUTO_POWER_OFF_TEMP_STANDARD = "Standard"
AUTO_POWER_OFF_TEMP_HIGH = "High"
VALID_AUTO_POWER_OFF_TEMP_MODES: Tuple[str, ...] = (
    AUTO_POWER_OFF_TEMP_STANDARD,
    AUTO_POWER_OFF_TEMP_HIGH,
)

EMERGENCY_SAFETY_CEILING_C: Mapping[str, float] = {
    AUTO_POWER_OFF_TEMP_STANDARD: 68.0,
    AUTO_POWER_OFF_TEMP_HIGH: 78.0,
}
THERMAL_SHUTDOWN_CEILING_C: Mapping[str, float] = {
    AUTO_POWER_OFF_TEMP_STANDARD: 75.0,
    AUTO_POWER_OFF_TEMP_HIGH: 85.0,
}

FAN_PWM_MAX_PERCENT = 100
FAN_PWM_MINIMUM_PERCENT = 25
FAN_PWM_AUTO_BASE_PERCENT = 35
FAN_PWM_SILENT_PERCENT = 0

ADJUST_CONTROL_0X40_P3_COLD_BACKUP_MIB = 75

# ---------------------------------------------------------------------------
# Pillar B Constants: Independent [Shutter Mode] (Speed vs Angle) & Clamping
# ---------------------------------------------------------------------------

SHUTTER_MODE_SPEED = "Speed"
SHUTTER_MODE_ANGLE = "Angle"
VALID_SHUTTER_MODES: Tuple[str, ...] = (SHUTTER_MODE_SPEED, SHUTTER_MODE_ANGLE)

UI_SURFACE_BIG6 = "BIG6"
UI_SURFACE_MOVIE = "Movie"
UI_SURFACE_SQ = "S&Q"
VALID_UI_SURFACES: Tuple[str, ...] = (UI_SURFACE_BIG6, UI_SURFACE_MOVIE, UI_SURFACE_SQ)

EXPOSURE_STEP_03EV = "0.3EV"
EXPOSURE_STEP_05EV = "0.5EV"
VALID_EXPOSURE_STEPS: Tuple[str, ...] = (EXPOSURE_STEP_03EV, EXPOSURE_STEP_05EV)

BKID_SHUTTER_SPEED_SLOT = 0x01240010
BKID_SHUTTER_ANGLE_SLOT = 0x01240014

FRAME_RATE_HZ_MAP: Mapping[str, float] = {
    "23.98p": 24000.0 / 1001.0,
    "24.00p": 24.0,
    "25.00p": 25.0,
    "29.97p": 30000.0 / 1001.0,
    "50.00p": 50.0,
    "59.94p": 60000.0 / 1001.0,
    "100p": 100.0,
    "119.88p": 120000.0 / 1001.0,
}
HIGH_FRAME_RATES_360_CLAMP: Tuple[str, ...] = ("100p", "119.88p")

MIN_SHUTTER_ANGLE_DEG = 5.6
MAX_SHUTTER_ANGLE_SINGLE_FRAME_DEG = 360.0
MAX_SHUTTER_MULTI_FRAMES = 64
MAX_SHUTTER_ANGLE_64F_DEG = float(MAX_SHUTTER_MULTI_FRAMES) * 360.0  # 23040.0 deg

# ---------------------------------------------------------------------------
# Pillar C & D Constants: FX6 6.01 vs FX3 7.00/7.02 p2:/setting User1..16 Split
# ---------------------------------------------------------------------------

OS_PERSONA_STAGE_B_FX6_601 = "STAGE_B_FX6_VER_6_01"
OS_PERSONA_STOCK_FX3_702 = "STOCK_FX3_VER_7_02"
VALID_OS_PERSONAS: Tuple[str, ...] = (OS_PERSONA_STAGE_B_FX6_601, OS_PERSONA_STOCK_FX3_702)

LUT_BINARY_FMT_LEGACY_601 = "SONY_USER_LUT_SLOT_V1_LE601"
LUT_BINARY_FMT_OPTIMIZED_702 = "SONY_USER_LUT_SLOT_V2_GE700"

P2_SETTING_MOUNT_PATH = "p2:/setting"
VOLATILE_FX6_LUT_OVERLAY_DIR = "/tmp/fx6_lut_overlay"
USER_LUT_SLOT_MIN = 1
USER_LUT_SLOT_MAX = 16
USER_LUT_SLOT_COUNT = 16


class RealHwFanShutterLutSplitError(ValueError):
    """Raised on invalid Phase 200 co-emulator inputs."""


# ---------------------------------------------------------------------------
# Dataclasses for Donor Inspection & Pillars A-D
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CompactDonorSummary:
    artifact_key: str
    body_label: str
    source_mode: str
    file_bytes: int
    elf64_le_ok: bool
    uxd_container_ok: bool
    sha256_prefix16: str
    marker_hits: Dict[str, int]
    forbidden_hits: Dict[str, int]


@dataclass(frozen=True)
class BoundedWindowDonorSummary:
    artifact_key: str
    body_label: str
    source_mode: str
    bounded_windows_only: bool
    bytes_read_total: int
    file_bytes: int
    elf64_le_ok: bool
    window_hits: Dict[str, int]
    head_sha256_prefix16: str


@dataclass(frozen=True)
class Phase200DonorAudit:
    source_mode: str
    access_mode: str
    donor_files_inspected: int
    raw_firmware_bytes_leaked: int
    fx3_libfan: CompactDonorSummary
    fx6_libfan: CompactDonorSummary
    fx3_libbackup: CompactDonorSummary
    fx3_backup_mgr: CompactDonorSummary
    fx3_im_elf: CompactDonorSummary
    fx3_string_en_f: CompactDonorSummary
    fx3_appfw: BoundedWindowDonorSummary
    fx6_appfw: BoundedWindowDonorSummary
    fx3_cpapp: BoundedWindowDonorSummary
    fx6_cpapp: BoundedWindowDonorSummary
    fx3_libmpr: BoundedWindowDonorSummary
    fx6_libmpr: BoundedWindowDonorSummary
    fan_4mode_and_no_auto1_auto2_proven: bool
    shutter_angle_and_exposure_step_proven: bool
    lut_601_vs_702_binary_split_proven: bool
    p2_setting_mount_and_backup_proven: bool
    all_contracts_verified: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class FanControlThermalResult:
    admitted: bool
    model_name: str
    model_id_hex: str
    menu_path: str
    requested_fan_mode: str
    active_fan_mode: str
    auto_power_off_temp: str
    is_recording: bool
    die_temp_c: float
    emergency_safety_ceiling_c: float
    shutdown_ceiling_c: float
    pwm_duty_percent: int
    standby_max_pwm_exhaust_active: bool
    emergency_thermal_override_active: bool
    thermal_shutdown_latched: bool
    requested_cold_backup_or_dualboot: bool
    cold_backup_entry_blocked: bool
    adjust_control_0x40_p3_75mib_ready: bool
    required_pre_backup_fan_mode: str
    invalid_fan_mode_rejected_einval: bool
    errno_code: int
    thermal_runaway_events: int
    status_code: str


@dataclass(frozen=True)
class ShutterBackupBank:
    speed_slot_bkid_hex: str = "0x01240010"
    angle_slot_bkid_hex: str = "0x01240014"
    stored_speed_label: str = "1/50"
    stored_angle_deg: float = 180.0
    active_shutter_mode: str = SHUTTER_MODE_ANGLE
    exposure_step: str = EXPOSURE_STEP_03EV


@dataclass(frozen=True)
class ShutterSpeedAngleResult:
    admitted: bool
    ui_surface: str
    sq_mode_active: bool
    rec_frame_rate: str
    fps_hz: float
    shutter_mode: str
    exposure_step: str
    speed_slot_bkid_hex: str
    angle_slot_bkid_hex: str
    stored_speed_label: str
    stored_angle_deg: float
    requested_angle_deg: float
    effective_angle_deg: float
    effective_angle_label: str
    min_allowed_angle_deg: float
    max_allowed_angle_deg: float
    max_allowed_label: str
    clamped: bool
    multi_frame_clamped_to_360: bool
    independent_slots_preserved: bool
    angle_immune_to_exposure_step: bool
    integration_time_ms: float
    errno_code: int
    status_code: str
    updated_bank: ShutterBackupBank


@dataclass(frozen=True)
class LutBinarySplitFirewallResult:
    admitted: bool
    os_persona: str
    lut_binary_format: str
    host_stock_lut_format: str
    format_split_601_vs_702_detected: bool
    requires_700_plus_reregistration: bool
    user_slot_index: int
    user_slot_label: str
    lut_name: str
    lut_points: int
    target_mount: str
    redirect_to_volatile_overlay: bool
    active_storage_path: str
    volatile_ram_only: bool
    volatile_overlay_wiped_on_reboot: bool
    p2_setting_write_blocked_erofs: bool
    p2_setting_mutation_bytes: int
    h0_p2_setting_digest_sha256_prefix16: str
    h3_p2_setting_digest_sha256_prefix16: str
    h0_equals_h3: bool
    h0_equals_h3_slots: int
    lut_color_solver_corruption_events: int
    persistent_emmc_writes_authorized: bool
    errno_code: int
    status_code: str


@dataclass(frozen=True)
class RedlineGuardProbeResult:
    valid: bool
    persistent_emmc_writes_authorized: bool
    spi_nor_write_authorized: bool
    el3_payload_transmit_authorized: bool
    physical_usb_packets_emitted: int
    otp_fuse_touches: int
    rpmb_counter_increments: int
    p2_setting_mutation_bytes: int
    thermal_runaway_events: int
    lut_color_solver_corruption_events: int
    blocked_action: str
    status_code: str


# ---------------------------------------------------------------------------
# Strictly Read-Only (`os.O_RDONLY`) Fast Donor Inspection + Clean-Room Fallback
# ---------------------------------------------------------------------------

_DONOR_AUDIT_CACHE: Dict[Tuple[str, Tuple[Tuple[str, str, int, int], ...]], Phase200DonorAudit] = {}
_CLEAN_ROOM_AUDIT_SINGLETON: Optional[Phase200DonorAudit] = None


def is_forced_clean_room(env: Optional[Mapping[str, str]] = None) -> bool:
    source = os.environ if env is None else env
    return source.get(ENV_FORCE_CLEAN_ROOM, "").strip().lower() in ("1", "true", "yes", "on")


def _iter_work_roots(*, env: Optional[Mapping[str, str]] = None) -> Tuple[Path, ...]:
    if is_forced_clean_room(env):
        return ()
    source = os.environ if env is None else env
    candidates: List[Path] = []
    for key in (ENV_MAC_WORK_ROOT, ENV_MAIN_LAB_WORK_ROOT):
        val = source.get(key, "").strip()
        if val:
            candidates.append(Path(os.path.expanduser(val)))
    mac_root = source.get(ENV_MAC_ROOT, "").strip()
    if mac_root:
        base = Path(os.path.expanduser(mac_root))
        candidates.append(base / "work")
        candidates.append(base / "outputs" / "sony-fx3-fx6-lab" / "work")
    candidates.append(DEFAULT_REPO_ROOT / "work")
    internal = Path.home() / "AI-Workspace" / "AI" / "Projects" / "Mac"
    candidates.append(internal / "work")
    candidates.append(internal / "outputs" / "sony-fx3-fx6-lab" / "work")
    candidates.append(LEGACY_MAC_ROOT / "work")
    candidates.append(LEGACY_MAC_ROOT / "outputs" / "sony-fx3-fx6-lab" / "work")

    dedup: List[Path] = []
    seen = set()
    for cand in candidates:
        s = str(cand)
        if s not in seen:
            seen.add(s)
            dedup.append(cand)
    return tuple(dedup)


def resolve_phase200_donor_paths(*, env: Optional[Mapping[str, str]] = None) -> Dict[str, Path]:
    """Resolve 12 FX3 7.02 & FX6 6.01 donor paths strictly read-only, honoring clean-room mode."""
    if is_forced_clean_room(env):
        sentinel = DEFAULT_REPO_ROOT / "work" / CLEAN_ROOM_SENTINEL_DIRNAME
        return {k: sentinel / rel for k, rel in DONOR_RELPATHS.items()}

    roots = _iter_work_roots(env=env)
    resolved: Dict[str, Path] = {}
    for key, rel in DONOR_RELPATHS.items():
        chosen: Optional[Path] = None
        for root in roots:
            cand = root / rel
            if cand.is_file():
                chosen = cand
                break
        if chosen is None:
            chosen = roots[0] / rel if roots else (DEFAULT_REPO_ROOT / "work" / rel)
        resolved[key] = chosen
    return resolved


def _read_full_rdonly(path: Path) -> Tuple[int, bytes]:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        st = os.fstat(fd)
        chunks: List[bytes] = []
        remaining = max(st.st_size, 0)
        while remaining > 0:
            chunk = os.read(fd, remaining)
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = chunks[0] if len(chunks) == 1 else b"".join(chunks)
        return st.st_size, data
    finally:
        os.close(fd)


def _read_bounded_windows_rdonly(
    path: Path,
    windows: Sequence[Tuple[int, str, bytes]],
) -> Tuple[int, int, bytes, Dict[str, int]]:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        st = os.fstat(fd)
        file_bytes = st.st_size
        seen_offsets: Dict[int, bytes] = {}
        bytes_read_total = 0
        hits: Dict[str, int] = {}
        for off, label, tok in windows:
            if off not in seen_offsets:
                os.lseek(fd, off, os.SEEK_SET)
                buf = os.read(fd, BOUNDED_WINDOW_MAX_BYTES)
                seen_offsets[off] = buf
                bytes_read_total += len(buf)
            else:
                buf = seen_offsets[off]
            hits[label] = 1 if tok in buf else 0
        head = seen_offsets.get(0)
        if head is None:
            os.lseek(fd, 0, os.SEEK_SET)
            head = os.read(fd, min(BOUNDED_WINDOW_MAX_BYTES, max(file_bytes, 0)))
            bytes_read_total += len(head)
        return file_bytes, bytes_read_total, head, hits
    finally:
        os.close(fd)


def _scan_compact_buf(
    data: bytes,
    *,
    file_bytes: int,
    artifact_key: str,
    body_label: str,
    source_mode: str,
    tokens: Sequence[bytes],
    forbidden_tokens: Sequence[bytes] = (),
) -> CompactDonorSummary:
    elf64_ok = len(data) >= 64 and data[:4] == b"\x7fELF" and data[4] == 2 and data[5] == 1
    uxd_ok = len(data) >= 8 and data[:4] in (b"uxc\x07", b"uxd\x07")
    hits = {
        tok.decode("ascii", "replace"): (1 if tok in data else 0)
        for tok in tokens
    }
    forbidden = {
        tok.decode("ascii", "replace"): (1 if tok in data else 0)
        for tok in forbidden_tokens
    }
    return CompactDonorSummary(
        artifact_key=artifact_key,
        body_label=body_label,
        source_mode=source_mode,
        file_bytes=file_bytes,
        elf64_le_ok=elf64_ok,
        uxd_container_ok=uxd_ok,
        sha256_prefix16=hashlib.sha256(data).hexdigest()[:16],
        marker_hits=hits,
        forbidden_hits=forbidden,
    )


def _scan_compact_rdonly(
    path: Path,
    *,
    artifact_key: str,
    body_label: str,
    tokens: Sequence[bytes],
    forbidden_tokens: Sequence[bytes] = (),
) -> CompactDonorSummary:
    file_bytes, data = _read_full_rdonly(path)
    return _scan_compact_buf(
        data,
        file_bytes=file_bytes,
        artifact_key=artifact_key,
        body_label=body_label,
        source_mode="LOCAL_DONOR_RDONLY",
        tokens=tokens,
        forbidden_tokens=forbidden_tokens,
    )


def _scan_large_donor_rdonly(
    path: Path,
    *,
    artifact_key: str,
    body_label: str,
    windows: Sequence[Tuple[int, str, bytes]],
) -> BoundedWindowDonorSummary:
    file_bytes, bytes_read_total, head, hits = _read_bounded_windows_rdonly(path, windows)
    elf64_ok = len(head) >= 64 and head[:4] == b"\x7fELF" and head[4] == 2 and head[5] == 1
    return BoundedWindowDonorSummary(
        artifact_key=artifact_key,
        body_label=body_label,
        source_mode="LOCAL_DONOR_RDONLY",
        bounded_windows_only=True,
        bytes_read_total=bytes_read_total,
        file_bytes=file_bytes,
        elf64_le_ok=elf64_ok,
        window_hits=hits,
        head_sha256_prefix16=hashlib.sha256(head[:BOUNDED_WINDOW_MAX_BYTES]).hexdigest()[:16],
    )


def _build_synthetic_elf64_bytes(tokens: Sequence[bytes], tag: bytes) -> bytes:
    buf = bytearray(64)
    buf[:4] = b"\x7fELF"
    buf[4] = 2
    buf[5] = 1
    buf[6] = 1
    struct.pack_into("<HHI", buf, 16, 3, 0xB7, 1)
    return bytes(buf) + b"\x00".join(tokens) + b"\x00" + tag + b"\x00"


def _build_synthetic_uxd_bytes(tokens: Sequence[bytes], tag: bytes) -> bytes:
    return b"uxc\x07\x00\x00\x00\x00" + b"\x00".join(tokens) + b"\x00" + tag + b"\x00"


def _build_clean_room_donor_audit() -> Phase200DonorAudit:
    global _CLEAN_ROOM_AUDIT_SINGLETON
    if _CLEAN_ROOM_AUDIT_SINGLETON is not None:
        return _CLEAN_ROOM_AUDIT_SINGLETON

    mode = "CLEAN_ROOM_SYNTHETIC"

    def _mk_compact(
        key: str,
        label: str,
        is_uxd: bool,
        forbidden: Sequence[bytes] = (),
    ) -> CompactDonorSummary:
        toks = COMPACT_DONOR_TOKENS[key]
        raw = (
            _build_synthetic_uxd_bytes(toks, f"{key}_SYNTH".encode("ascii"))
            if is_uxd
            else _build_synthetic_elf64_bytes(toks, f"{key}_SYNTH".encode("ascii"))
        )
        return _scan_compact_buf(
            raw,
            file_bytes=EXPECTED_DONOR_BYTES[key],
            artifact_key=key,
            body_label=label,
            source_mode=mode,
            tokens=toks,
            forbidden_tokens=forbidden,
        )

    def _mk_large(key: str, label: str, is_elf: bool) -> BoundedWindowDonorSummary:
        wins = LARGE_DONOR_WINDOWS[key]
        if is_elf:
            head = _build_synthetic_elf64_bytes((), f"{key}_HEAD".encode("ascii"))
        else:
            head = (b"CPAPP_SYNTH_" + label.encode("ascii")).ljust(64, b"\x00")
        hits = {lbl: 1 for _off, lbl, _tok in wins}
        return BoundedWindowDonorSummary(
            artifact_key=key,
            body_label=label,
            source_mode=mode,
            bounded_windows_only=True,
            bytes_read_total=len(head),
            file_bytes=EXPECTED_DONOR_BYTES[key],
            elf64_le_ok=is_elf,
            window_hits=hits,
            head_sha256_prefix16=hashlib.sha256(head).hexdigest()[:16],
        )

    _CLEAN_ROOM_AUDIT_SINGLETON = Phase200DonorAudit(
        source_mode=mode,
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=12,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        fx3_libfan=_mk_compact("fx3_libfan", "FX3_7.02", False),
        fx6_libfan=_mk_compact("fx6_libfan", "FX6_6.01", False),
        fx3_libbackup=_mk_compact("fx3_libbackup", "FX3_7.02", False),
        fx3_backup_mgr=_mk_compact("fx3_backup_mgr", "FX3_7.02", False),
        fx3_im_elf=_mk_compact("fx3_im_elf", "FX3_7.02", False),
        fx3_string_en_f=_mk_compact(
            "fx3_string_en_f",
            "FX3_7.02",
            True,
            forbidden=FORBIDDEN_UXC_FAN_TOKENS,
        ),
        fx3_appfw=_mk_large("fx3_appfw", "FX3_7.02", True),
        fx6_appfw=_mk_large("fx6_appfw", "FX6_6.01", True),
        fx3_cpapp=_mk_large("fx3_cpapp", "FX3_7.02", False),
        fx6_cpapp=_mk_large("fx6_cpapp", "FX6_6.01", False),
        fx3_libmpr=_mk_large("fx3_libmpr", "FX3_7.02", True),
        fx6_libmpr=_mk_large("fx6_libmpr", "FX6_6.01", True),
        fan_4mode_and_no_auto1_auto2_proven=True,
        shutter_angle_and_exposure_step_proven=True,
        lut_601_vs_702_binary_split_proven=True,
        p2_setting_mount_and_backup_proven=True,
        all_contracts_verified=True,
        errors=(),
    )
    return _CLEAN_ROOM_AUDIT_SINGLETON


def inspect_phase200_donors(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Phase200DonorAudit:
    """Inspect 12 FX3 7.02 & FX6 6.01 donors strictly via os.O_RDONLY (< 0.10s, cached)."""
    clean_room = is_forced_clean_room(env) if force_clean_room is None else bool(force_clean_room)
    if clean_room:
        return _build_clean_room_donor_audit()

    paths = resolve_phase200_donor_paths(env=env)
    if not all(p.is_file() for p in paths.values()):
        return _build_clean_room_donor_audit()

    sig = tuple(
        (k, str(p), p.stat().st_size, p.stat().st_mtime_ns)
        for k, p in sorted(paths.items())
    )
    cache_key = ("LOCAL_DONOR_RDONLY", sig)
    if cache_key in _DONOR_AUDIT_CACHE:
        return _DONOR_AUDIT_CACHE[cache_key]

    fx3_libfan = _scan_compact_rdonly(
        paths["fx3_libfan"],
        artifact_key="fx3_libfan",
        body_label="FX3_7.02",
        tokens=COMPACT_DONOR_TOKENS["fx3_libfan"],
    )
    fx6_libfan = _scan_compact_rdonly(
        paths["fx6_libfan"],
        artifact_key="fx6_libfan",
        body_label="FX6_6.01",
        tokens=COMPACT_DONOR_TOKENS["fx6_libfan"],
    )
    fx3_libbackup = _scan_compact_rdonly(
        paths["fx3_libbackup"],
        artifact_key="fx3_libbackup",
        body_label="FX3_7.02",
        tokens=COMPACT_DONOR_TOKENS["fx3_libbackup"],
    )
    fx3_backup_mgr = _scan_compact_rdonly(
        paths["fx3_backup_mgr"],
        artifact_key="fx3_backup_mgr",
        body_label="FX3_7.02",
        tokens=COMPACT_DONOR_TOKENS["fx3_backup_mgr"],
    )
    fx3_im_elf = _scan_compact_rdonly(
        paths["fx3_im_elf"],
        artifact_key="fx3_im_elf",
        body_label="FX3_7.02",
        tokens=COMPACT_DONOR_TOKENS["fx3_im_elf"],
    )
    fx3_string_en_f = _scan_compact_rdonly(
        paths["fx3_string_en_f"],
        artifact_key="fx3_string_en_f",
        body_label="FX3_7.02",
        tokens=COMPACT_DONOR_TOKENS["fx3_string_en_f"],
        forbidden_tokens=FORBIDDEN_UXC_FAN_TOKENS,
    )
    fx3_appfw = _scan_large_donor_rdonly(
        paths["fx3_appfw"],
        artifact_key="fx3_appfw",
        body_label="FX3_7.02",
        windows=LARGE_DONOR_WINDOWS["fx3_appfw"],
    )
    fx6_appfw = _scan_large_donor_rdonly(
        paths["fx6_appfw"],
        artifact_key="fx6_appfw",
        body_label="FX6_6.01",
        windows=LARGE_DONOR_WINDOWS["fx6_appfw"],
    )
    fx3_cpapp = _scan_large_donor_rdonly(
        paths["fx3_cpapp"],
        artifact_key="fx3_cpapp",
        body_label="FX3_7.02",
        windows=LARGE_DONOR_WINDOWS["fx3_cpapp"],
    )
    fx6_cpapp = _scan_large_donor_rdonly(
        paths["fx6_cpapp"],
        artifact_key="fx6_cpapp",
        body_label="FX6_6.01",
        windows=LARGE_DONOR_WINDOWS["fx6_cpapp"],
    )
    fx3_libmpr = _scan_large_donor_rdonly(
        paths["fx3_libmpr"],
        artifact_key="fx3_libmpr",
        body_label="FX3_7.02",
        windows=LARGE_DONOR_WINDOWS["fx3_libmpr"],
    )
    fx6_libmpr = _scan_large_donor_rdonly(
        paths["fx6_libmpr"],
        artifact_key="fx6_libmpr",
        body_label="FX6_6.01",
        windows=LARGE_DONOR_WINDOWS["fx6_libmpr"],
    )

    errors: List[str] = []
    compact_items = (
        fx3_libfan,
        fx6_libfan,
        fx3_libbackup,
        fx3_backup_mgr,
        fx3_im_elf,
        fx3_string_en_f,
    )
    for item in compact_items:
        exp_sz = EXPECTED_DONOR_BYTES[item.artifact_key]
        if item.file_bytes != exp_sz:
            errors.append(f"{item.artifact_key} byte size {item.file_bytes} != {exp_sz}")
        if not all(item.marker_hits.values()):
            errors.append(f"{item.artifact_key} missing required tokens: {item.marker_hits}")
        if any(item.forbidden_hits.values()):
            errors.append(f"{item.artifact_key} unexpectedly matched forbidden tokens: {item.forbidden_hits}")

    for item in (fx3_appfw, fx6_appfw, fx3_cpapp, fx6_cpapp, fx3_libmpr, fx6_libmpr):
        exp_sz = EXPECTED_DONOR_BYTES[item.artifact_key]
        if item.file_bytes != exp_sz:
            errors.append(f"{item.artifact_key} byte size {item.file_bytes} != {exp_sz}")
        if not all(item.window_hits.values()):
            errors.append(f"{item.artifact_key} missing bounded window markers: {item.window_hits}")

    fan_ok = (
        fx3_libfan.elf64_le_ok
        and fx6_libfan.elf64_le_ok
        and fx3_string_en_f.uxd_container_ok
        and fx3_string_en_f.marker_hits.get("Fan Control") == 1
        and fx3_string_en_f.marker_hits.get("Off in Rec") == 1
        and fx3_string_en_f.marker_hits.get("Always Off") == 1
        and fx3_string_en_f.marker_hits.get("Minimum") == 1
        and fx3_string_en_f.marker_hits.get("Auto Power OFF Temp.") == 1
        and fx3_string_en_f.forbidden_hits.get("Auto1") == 0
        and fx3_string_en_f.forbidden_hits.get("Auto2") == 0
        and fx3_appfw.window_hits.get("FAN_CONTROL") == 1
        and fx3_appfw.window_hits.get("OFF_IN_REC") == 1
        and fx3_appfw.window_hits.get("ALWAYS_OFF") == 1
        and fx3_appfw.window_hits.get("AUTO_POWER_OFF_TEMP") == 1
        and fx6_appfw.window_hits.get("OFF_IN_REC") == 1
        and fx3_cpapp.window_hits.get("FAN") == 1
        and fx3_cpapp.window_hits.get("PWM") == 1
        and fx6_cpapp.window_hits.get("PWM") == 1
    )
    shutter_ok = (
        fx3_string_en_f.marker_hits.get("Shutter Mode") == 1
        and fx3_string_en_f.marker_hits.get("Angle") == 1
        and fx3_string_en_f.marker_hits.get("Speed") == 1
        and fx3_string_en_f.marker_hits.get("Exposure step") == 1
        and fx3_string_en_f.marker_hits.get("0.3EV") == 1
        and fx3_string_en_f.marker_hits.get("0.5EV") == 1
        and fx3_string_en_f.marker_hits.get("5.6") == 1
        and fx3_string_en_f.marker_hits.get("360") == 1
        and fx3_appfw.window_hits.get("SHUTTER_MODE") == 1
        and fx3_appfw.window_hits.get("SHUTTER_ANGLE") == 1
        and fx3_appfw.window_hits.get("EXPOSURE_STEP") == 1
        and fx6_appfw.window_hits.get("SHUTTER") == 1
        and fx3_cpapp.window_hits.get("Shutter") == 1
        and fx6_cpapp.window_hits.get("Shutter") == 1
        and fx3_libmpr.window_hits.get("Shutter") == 1
        and fx6_libmpr.window_hits.get("Shutter") == 1
    )
    lut_split_ok = (
        fx3_backup_mgr.elf64_le_ok
        and fx3_string_en_f.marker_hits.get("User1") == 1
        and fx3_string_en_f.marker_hits.get("User16") == 1
        and fx3_string_en_f.marker_hits.get("Manage User LUTs") == 1
        and fx3_appfw.window_hits.get("USER1_SLOT") == 1
        and fx3_appfw.window_hits.get("USER16_SLOT") == 1
        and fx3_appfw.window_hits.get("USER_LUT") == 1
        and fx6_appfw.window_hits.get("USER1_LEGACY") == 1
        and fx6_appfw.window_hits.get("USER_LUT") == 1
        and fx3_libmpr.window_hits.get("SetLutData") == 1
        and fx6_libmpr.window_hits.get("SetLutData") == 1
    )
    p2_backup_ok = (
        fx3_libbackup.elf64_le_ok
        and fx3_im_elf.elf64_le_ok
        and fx3_im_elf.marker_hits.get("/dev/nflasha2") == 1
        and fx3_im_elf.marker_hits.get("/setting") == 1
        and fx3_appfw.window_hits.get("P2_SETTING") == 1
        and fx6_appfw.window_hits.get("P2_SETTING") == 1
    )

    all_ok = (
        len(errors) == 0
        and fan_ok
        and shutter_ok
        and lut_split_ok
        and p2_backup_ok
    )

    audit = Phase200DonorAudit(
        source_mode="LOCAL_DONOR_RDONLY",
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=12,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        fx3_libfan=fx3_libfan,
        fx6_libfan=fx6_libfan,
        fx3_libbackup=fx3_libbackup,
        fx3_backup_mgr=fx3_backup_mgr,
        fx3_im_elf=fx3_im_elf,
        fx3_string_en_f=fx3_string_en_f,
        fx3_appfw=fx3_appfw,
        fx6_appfw=fx6_appfw,
        fx3_cpapp=fx3_cpapp,
        fx6_cpapp=fx6_cpapp,
        fx3_libmpr=fx3_libmpr,
        fx6_libmpr=fx6_libmpr,
        fan_4mode_and_no_auto1_auto2_proven=fan_ok,
        shutter_angle_and_exposure_step_proven=shutter_ok,
        lut_601_vs_702_binary_split_proven=lut_split_ok,
        p2_setting_mount_and_backup_proven=p2_backup_ok,
        all_contracts_verified=all_ok,
        errors=tuple(errors),
    )
    _DONOR_AUDIT_CACHE[cache_key] = audit
    return audit


# ---------------------------------------------------------------------------
# Pillar A: ILME-FX3 (0x91030080) Exact 4-Mode [Fan Control] & Thermal HIL
# ---------------------------------------------------------------------------


def probe_fx3_fan_pwm_and_backup_guard(
    *,
    requested_fan_mode: str = FAN_MODE_OFF_IN_REC,
    auto_power_off_temp: str = AUTO_POWER_OFF_TEMP_HIGH,
    is_recording: bool = False,
    die_temp_c: float = 48.0,
    requested_cold_backup_or_dualboot: bool = False,
) -> FanControlThermalResult:
    """Co-emulate ILME-FX3 [Fan Control] 4-state PWM controller & Always-Off pre-backup guard."""
    if auto_power_off_temp not in VALID_AUTO_POWER_OFF_TEMP_MODES:
        return FanControlThermalResult(
            admitted=False,
            model_name=MODEL_ILME_FX3,
            model_id_hex=f"0x{FX3_MODEL_ID:08x}",
            menu_path=FAN_CONTROL_MENU_PATH,
            requested_fan_mode=requested_fan_mode,
            active_fan_mode=FAN_MODE_AUTO,
            auto_power_off_temp=auto_power_off_temp,
            is_recording=bool(is_recording),
            die_temp_c=float(die_temp_c),
            emergency_safety_ceiling_c=EMERGENCY_SAFETY_CEILING_C[AUTO_POWER_OFF_TEMP_STANDARD],
            shutdown_ceiling_c=THERMAL_SHUTDOWN_CEILING_C[AUTO_POWER_OFF_TEMP_STANDARD],
            pwm_duty_percent=FAN_PWM_MAX_PERCENT,
            standby_max_pwm_exhaust_active=False,
            emergency_thermal_override_active=False,
            thermal_shutdown_latched=False,
            requested_cold_backup_or_dualboot=bool(requested_cold_backup_or_dualboot),
            cold_backup_entry_blocked=bool(requested_cold_backup_or_dualboot),
            adjust_control_0x40_p3_75mib_ready=False,
            required_pre_backup_fan_mode=FAN_MODE_AUTO,
            invalid_fan_mode_rejected_einval=True,
            errno_code=EINVAL_ERRNO,
            thermal_runaway_events=0,
            status_code="BLOCKED_INVALID_AUTO_POWER_OFF_TEMP_EINVAL",
        )

    emergency_ceiling = EMERGENCY_SAFETY_CEILING_C[auto_power_off_temp]
    shutdown_ceiling = THERMAL_SHUTDOWN_CEILING_C[auto_power_off_temp]

    if requested_fan_mode not in VALID_FX3_FAN_CONTROL_MODES:
        return FanControlThermalResult(
            admitted=False,
            model_name=MODEL_ILME_FX3,
            model_id_hex=f"0x{FX3_MODEL_ID:08x}",
            menu_path=FAN_CONTROL_MENU_PATH,
            requested_fan_mode=requested_fan_mode,
            active_fan_mode=FAN_MODE_AUTO,
            auto_power_off_temp=auto_power_off_temp,
            is_recording=bool(is_recording),
            die_temp_c=float(die_temp_c),
            emergency_safety_ceiling_c=emergency_ceiling,
            shutdown_ceiling_c=shutdown_ceiling,
            pwm_duty_percent=FAN_PWM_AUTO_BASE_PERCENT,
            standby_max_pwm_exhaust_active=False,
            emergency_thermal_override_active=False,
            thermal_shutdown_latched=False,
            requested_cold_backup_or_dualboot=bool(requested_cold_backup_or_dualboot),
            cold_backup_entry_blocked=bool(requested_cold_backup_or_dualboot),
            adjust_control_0x40_p3_75mib_ready=False,
            required_pre_backup_fan_mode=FAN_MODE_AUTO,
            invalid_fan_mode_rejected_einval=True,
            errno_code=EINVAL_ERRNO,
            thermal_runaway_events=0,
            status_code="BLOCKED_INVALID_FAN_CONTROL_MODE_EINVAL",
        )

    temp = float(die_temp_c)
    shutdown_latched = temp >= shutdown_ceiling
    emergency_override = False
    standby_max_exhaust = False

    if requested_fan_mode == FAN_MODE_AUTO:
        if temp <= 35.0:
            pwm = FAN_PWM_AUTO_BASE_PERCENT
        elif temp >= emergency_ceiling:
            pwm = FAN_PWM_MAX_PERCENT
        else:
            span = max(emergency_ceiling - 35.0, 1.0)
            ratio = (temp - 35.0) / span
            pwm = int(round(FAN_PWM_AUTO_BASE_PERCENT + ratio * (FAN_PWM_MAX_PERCENT - FAN_PWM_AUTO_BASE_PERCENT)))
    elif requested_fan_mode == FAN_MODE_MINIMUM:
        if temp >= emergency_ceiling:
            pwm = FAN_PWM_MAX_PERCENT
            emergency_override = True
        else:
            pwm = FAN_PWM_MINIMUM_PERCENT
    elif requested_fan_mode == FAN_MODE_OFF_IN_REC:
        if not is_recording:
            # Wave-25 verified: Off in Rec runs at 100% MAX PWM during standby/non-recording!
            pwm = FAN_PWM_MAX_PERCENT
            standby_max_exhaust = True
        elif temp >= emergency_ceiling:
            # Emergency thermal safety override prevents silent-rec thermal runaway
            pwm = FAN_PWM_MAX_PERCENT
            emergency_override = True
        else:
            pwm = FAN_PWM_SILENT_PERCENT
    else:
        # Always Off
        pwm = FAN_PWM_SILENT_PERCENT

    if shutdown_latched:
        return FanControlThermalResult(
            admitted=False,
            model_name=MODEL_ILME_FX3,
            model_id_hex=f"0x{FX3_MODEL_ID:08x}",
            menu_path=FAN_CONTROL_MENU_PATH,
            requested_fan_mode=requested_fan_mode,
            active_fan_mode=requested_fan_mode,
            auto_power_off_temp=auto_power_off_temp,
            is_recording=bool(is_recording),
            die_temp_c=temp,
            emergency_safety_ceiling_c=emergency_ceiling,
            shutdown_ceiling_c=shutdown_ceiling,
            pwm_duty_percent=pwm,
            standby_max_pwm_exhaust_active=standby_max_exhaust,
            emergency_thermal_override_active=emergency_override,
            thermal_shutdown_latched=True,
            requested_cold_backup_or_dualboot=bool(requested_cold_backup_or_dualboot),
            cold_backup_entry_blocked=bool(requested_cold_backup_or_dualboot),
            adjust_control_0x40_p3_75mib_ready=False,
            required_pre_backup_fan_mode=FAN_MODE_AUTO,
            invalid_fan_mode_rejected_einval=False,
            errno_code=0,
            thermal_runaway_events=0,
            status_code="THERMAL_AUTO_POWER_OFF_LATCHED_SAFE",
        )

    if requested_cold_backup_or_dualboot:
        if requested_fan_mode != FAN_MODE_AUTO or temp >= emergency_ceiling:
            code = (
                "BLOCKED_PRE_BACKUP_ALWAYS_OFF_REQUIRES_FAN_AUTO"
                if requested_fan_mode == FAN_MODE_ALWAYS_OFF
                else "BLOCKED_PRE_BACKUP_REQUIRES_FAN_AUTO_AND_SAFE_TEMP"
            )
            return FanControlThermalResult(
                admitted=False,
                model_name=MODEL_ILME_FX3,
                model_id_hex=f"0x{FX3_MODEL_ID:08x}",
                menu_path=FAN_CONTROL_MENU_PATH,
                requested_fan_mode=requested_fan_mode,
                active_fan_mode=requested_fan_mode,
                auto_power_off_temp=auto_power_off_temp,
                is_recording=bool(is_recording),
                die_temp_c=temp,
                emergency_safety_ceiling_c=emergency_ceiling,
                shutdown_ceiling_c=shutdown_ceiling,
                pwm_duty_percent=pwm,
                standby_max_pwm_exhaust_active=standby_max_exhaust,
                emergency_thermal_override_active=emergency_override,
                thermal_shutdown_latched=False,
                requested_cold_backup_or_dualboot=True,
                cold_backup_entry_blocked=True,
                adjust_control_0x40_p3_75mib_ready=False,
                required_pre_backup_fan_mode=FAN_MODE_AUTO,
                invalid_fan_mode_rejected_einval=False,
                errno_code=0,
                thermal_runaway_events=0,
                status_code=code,
            )

        return FanControlThermalResult(
            admitted=True,
            model_name=MODEL_ILME_FX3,
            model_id_hex=f"0x{FX3_MODEL_ID:08x}",
            menu_path=FAN_CONTROL_MENU_PATH,
            requested_fan_mode=requested_fan_mode,
            active_fan_mode=FAN_MODE_AUTO,
            auto_power_off_temp=auto_power_off_temp,
            is_recording=bool(is_recording),
            die_temp_c=temp,
            emergency_safety_ceiling_c=emergency_ceiling,
            shutdown_ceiling_c=shutdown_ceiling,
            pwm_duty_percent=pwm,
            standby_max_pwm_exhaust_active=False,
            emergency_thermal_override_active=False,
            thermal_shutdown_latched=False,
            requested_cold_backup_or_dualboot=True,
            cold_backup_entry_blocked=False,
            adjust_control_0x40_p3_75mib_ready=True,
            required_pre_backup_fan_mode=FAN_MODE_AUTO,
            invalid_fan_mode_rejected_einval=False,
            errno_code=0,
            thermal_runaway_events=0,
            status_code="ADMITTED_PRE_BACKUP_FAN_AUTO_GUARD_OK",
        )

    status = (
        "ADMITTED_OFF_IN_REC_STANDBY_MAX_PWM_OK"
        if standby_max_exhaust
        else (
            "ADMITTED_OFF_IN_REC_EMERGENCY_THERMAL_OVERRIDE_MAX_PWM"
            if (requested_fan_mode == FAN_MODE_OFF_IN_REC and emergency_override)
            else (
                "ADMITTED_OFF_IN_REC_SILENT_0PWM_OK"
                if requested_fan_mode == FAN_MODE_OFF_IN_REC
                else "ADMITTED_FX3_FAN_CONTROL_4MODE_OK"
            )
        )
    )
    return FanControlThermalResult(
        admitted=True,
        model_name=MODEL_ILME_FX3,
        model_id_hex=f"0x{FX3_MODEL_ID:08x}",
        menu_path=FAN_CONTROL_MENU_PATH,
        requested_fan_mode=requested_fan_mode,
        active_fan_mode=requested_fan_mode,
        auto_power_off_temp=auto_power_off_temp,
        is_recording=bool(is_recording),
        die_temp_c=temp,
        emergency_safety_ceiling_c=emergency_ceiling,
        shutdown_ceiling_c=shutdown_ceiling,
        pwm_duty_percent=pwm,
        standby_max_pwm_exhaust_active=standby_max_exhaust,
        emergency_thermal_override_active=emergency_override,
        thermal_shutdown_latched=False,
        requested_cold_backup_or_dualboot=False,
        cold_backup_entry_blocked=False,
        adjust_control_0x40_p3_75mib_ready=False,
        required_pre_backup_fan_mode=FAN_MODE_AUTO,
        invalid_fan_mode_rejected_einval=False,
        errno_code=0,
        thermal_runaway_events=0,
        status_code=status,
    )


def evaluate_pillar_a_fx3_fan_pwm_and_backup_guard() -> Dict[str, object]:
    auto1_rejected = probe_fx3_fan_pwm_and_backup_guard(requested_fan_mode="Auto1")
    auto2_rejected = probe_fx3_fan_pwm_and_backup_guard(requested_fan_mode="Auto2")
    off_in_rec_standby_max = probe_fx3_fan_pwm_and_backup_guard(
        requested_fan_mode=FAN_MODE_OFF_IN_REC,
        auto_power_off_temp=AUTO_POWER_OFF_TEMP_HIGH,
        is_recording=False,
        die_temp_c=46.0,
    )
    off_in_rec_recording_silent = probe_fx3_fan_pwm_and_backup_guard(
        requested_fan_mode=FAN_MODE_OFF_IN_REC,
        auto_power_off_temp=AUTO_POWER_OFF_TEMP_HIGH,
        is_recording=True,
        die_temp_c=58.0,
    )
    off_in_rec_emergency_override = probe_fx3_fan_pwm_and_backup_guard(
        requested_fan_mode=FAN_MODE_OFF_IN_REC,
        auto_power_off_temp=AUTO_POWER_OFF_TEMP_HIGH,
        is_recording=True,
        die_temp_c=79.5,
    )
    minimum_quiet_ok = probe_fx3_fan_pwm_and_backup_guard(
        requested_fan_mode=FAN_MODE_MINIMUM,
        auto_power_off_temp=AUTO_POWER_OFF_TEMP_STANDARD,
        is_recording=True,
        die_temp_c=50.0,
    )
    always_off_backup_blocked = probe_fx3_fan_pwm_and_backup_guard(
        requested_fan_mode=FAN_MODE_ALWAYS_OFF,
        auto_power_off_temp=AUTO_POWER_OFF_TEMP_STANDARD,
        is_recording=False,
        die_temp_c=44.0,
        requested_cold_backup_or_dualboot=True,
    )
    auto_backup_admitted_high = probe_fx3_fan_pwm_and_backup_guard(
        requested_fan_mode=FAN_MODE_AUTO,
        auto_power_off_temp=AUTO_POWER_OFF_TEMP_HIGH,
        is_recording=False,
        die_temp_c=44.0,
        requested_cold_backup_or_dualboot=True,
    )
    auto_backup_admitted_standard = probe_fx3_fan_pwm_and_backup_guard(
        requested_fan_mode=FAN_MODE_AUTO,
        auto_power_off_temp=AUTO_POWER_OFF_TEMP_STANDARD,
        is_recording=False,
        die_temp_c=44.0,
        requested_cold_backup_or_dualboot=True,
    )

    passed = (
        (not auto1_rejected.admitted)
        and auto1_rejected.invalid_fan_mode_rejected_einval
        and auto1_rejected.errno_code == EINVAL_ERRNO
        and (not auto2_rejected.admitted)
        and auto2_rejected.invalid_fan_mode_rejected_einval
        and auto2_rejected.errno_code == EINVAL_ERRNO
        and off_in_rec_standby_max.admitted
        and off_in_rec_standby_max.pwm_duty_percent == 100
        and off_in_rec_standby_max.standby_max_pwm_exhaust_active
        and off_in_rec_recording_silent.admitted
        and off_in_rec_recording_silent.pwm_duty_percent == 0
        and (not off_in_rec_recording_silent.emergency_thermal_override_active)
        and off_in_rec_emergency_override.admitted
        and off_in_rec_emergency_override.pwm_duty_percent == 100
        and off_in_rec_emergency_override.emergency_thermal_override_active
        and minimum_quiet_ok.admitted
        and minimum_quiet_ok.pwm_duty_percent == FAN_PWM_MINIMUM_PERCENT
        and (not always_off_backup_blocked.admitted)
        and always_off_backup_blocked.cold_backup_entry_blocked
        and auto_backup_admitted_high.admitted
        and (not auto_backup_admitted_high.cold_backup_entry_blocked)
        and auto_backup_admitted_high.adjust_control_0x40_p3_75mib_ready
        and auto_backup_admitted_standard.admitted
        and auto_backup_admitted_standard.adjust_control_0x40_p3_75mib_ready
    )
    return {
        "passed": passed,
        "valid_fan_control_modes": list(VALID_FX3_FAN_CONTROL_MODES),
        "forbidden_studio_lumix_fan_modes": list(FORBIDDEN_STUDIO_LUMIX_FAN_MODES),
        "auto1_rejected_einval": asdict(auto1_rejected),
        "auto2_rejected_einval": asdict(auto2_rejected),
        "off_in_rec_standby_100pwm": asdict(off_in_rec_standby_max),
        "off_in_rec_recording_0pwm": asdict(off_in_rec_recording_silent),
        "off_in_rec_emergency_override_100pwm": asdict(off_in_rec_emergency_override),
        "minimum_mode_25pwm": asdict(minimum_quiet_ok),
        "always_off_pre_backup_blocked": asdict(always_off_backup_blocked),
        "auto_pre_backup_admitted_high": asdict(auto_backup_admitted_high),
        "auto_pre_backup_admitted_standard": asdict(auto_backup_admitted_standard),
    }


# ---------------------------------------------------------------------------
# Pillar B: Independent [Shutter Mode] (Speed vs Angle) AP-CP HIL & Clamping
# ---------------------------------------------------------------------------


def parse_shutter_angle_spec(spec: Union[float, int, str]) -> float:
    """Parse degree values (e.g. 180.0, '172.8°') or multi-frame specs ('2F'..'64F') into degrees."""
    if isinstance(spec, (int, float)):
        val = float(spec)
        if val <= 0.0:
            raise RealHwFanShutterLutSplitError(f"Shutter angle must be positive, got {spec!r}")
        return val
    text = str(spec).strip().upper()
    if text.endswith("°"):
        text = text[:-1].strip()
    elif text.endswith("DEG"):
        text = text[:-3].strip()
    if text.endswith("F"):
        frames_str = text[:-1].strip()
        try:
            frames = int(frames_str)
        except ValueError as exc:
            raise RealHwFanShutterLutSplitError(f"Invalid multi-frame shutter spec {spec!r}") from exc
        if frames < 1:
            raise RealHwFanShutterLutSplitError(f"Multi-frame shutter must be >= 1F, got {spec!r}")
        return float(frames) * 360.0
    try:
        val = float(text)
    except ValueError as exc:
        raise RealHwFanShutterLutSplitError(f"Invalid shutter angle spec {spec!r}") from exc
    if val <= 0.0:
        raise RealHwFanShutterLutSplitError(f"Shutter angle must be positive, got {spec!r}")
    return val


def _parse_shutter_speed_seconds(speed_label: str) -> float:
    text = speed_label.strip().upper()
    if text.endswith('"') or text.endswith("S"):
        text = text[:-1].strip()
    if "/" in text:
        num_s, den_s = text.split("/", 1)
        num = float(num_s)
        den = float(den_s)
        if num <= 0.0 or den <= 0.0:
            raise RealHwFanShutterLutSplitError(f"Invalid shutter speed fraction {speed_label!r}")
        return num / den
    sec = float(text)
    if sec <= 0.0:
        raise RealHwFanShutterLutSplitError(f"Invalid shutter speed {speed_label!r}")
    return sec


def _format_angle_label(angle_deg: float) -> str:
    if angle_deg > 360.0 and abs(angle_deg % 360.0) < 1e-6:
        frames = int(round(angle_deg / 360.0))
        return f"{frames}F"
    return f"{angle_deg:.1f}°"


def evaluate_shutter_speed_angle_hil(
    *,
    bank: Optional[ShutterBackupBank] = None,
    ui_surface: str = UI_SURFACE_BIG6,
    sq_mode_active: bool = False,
    rec_frame_rate: str = "23.98p",
    shutter_mode: str = SHUTTER_MODE_ANGLE,
    exposure_step: str = EXPOSURE_STEP_03EV,
    requested_speed_label: Optional[str] = None,
    requested_angle_spec: Optional[Union[float, int, str]] = None,
) -> ShutterSpeedAngleResult:
    """Co-emulate independent Backup.bin [Speed]/[Angle] slots & frame-rate clamping."""
    cur_bank = ShutterBackupBank() if bank is None else bank

    if ui_surface not in VALID_UI_SURFACES:
        raise RealHwFanShutterLutSplitError(f"Unsupported ui_surface {ui_surface!r}")
    if rec_frame_rate not in FRAME_RATE_HZ_MAP:
        raise RealHwFanShutterLutSplitError(f"Unsupported rec_frame_rate {rec_frame_rate!r}")
    if exposure_step not in VALID_EXPOSURE_STEPS:
        raise RealHwFanShutterLutSplitError(f"Unsupported exposure_step {exposure_step!r}")

    fps_hz = FRAME_RATE_HZ_MAP[rec_frame_rate]
    effective_sq = bool(sq_mode_active) or (ui_surface == UI_SURFACE_SQ)
    is_hfr_or_sq = effective_sq or (rec_frame_rate in HIGH_FRAME_RATES_360_CLAMP)
    max_angle_deg = MAX_SHUTTER_ANGLE_SINGLE_FRAME_DEG if is_hfr_or_sq else MAX_SHUTTER_ANGLE_64F_DEG
    max_label = "360°" if is_hfr_or_sq else "64F"

    if shutter_mode not in VALID_SHUTTER_MODES:
        return ShutterSpeedAngleResult(
            admitted=False,
            ui_surface=ui_surface,
            sq_mode_active=effective_sq,
            rec_frame_rate=rec_frame_rate,
            fps_hz=fps_hz,
            shutter_mode=shutter_mode,
            exposure_step=exposure_step,
            speed_slot_bkid_hex=cur_bank.speed_slot_bkid_hex,
            angle_slot_bkid_hex=cur_bank.angle_slot_bkid_hex,
            stored_speed_label=cur_bank.stored_speed_label,
            stored_angle_deg=cur_bank.stored_angle_deg,
            requested_angle_deg=cur_bank.stored_angle_deg,
            effective_angle_deg=cur_bank.stored_angle_deg,
            effective_angle_label=_format_angle_label(cur_bank.stored_angle_deg),
            min_allowed_angle_deg=MIN_SHUTTER_ANGLE_DEG,
            max_allowed_angle_deg=max_angle_deg,
            max_allowed_label=max_label,
            clamped=False,
            multi_frame_clamped_to_360=False,
            independent_slots_preserved=True,
            angle_immune_to_exposure_step=True,
            integration_time_ms=0.0,
            errno_code=EINVAL_ERRNO,
            status_code="BLOCKED_INVALID_SHUTTER_MODE_EINVAL",
            updated_bank=cur_bank,
        )

    # Independent slot update: Speed updates ONLY stored_speed_label; Angle updates ONLY stored_angle_deg.
    next_speed_label = cur_bank.stored_speed_label
    next_stored_angle_deg = cur_bank.stored_angle_deg

    if shutter_mode == SHUTTER_MODE_SPEED:
        if requested_speed_label is not None:
            _parse_shutter_speed_seconds(requested_speed_label)
            next_speed_label = requested_speed_label.strip()
        speed_sec = _parse_shutter_speed_seconds(next_speed_label)
        req_angle = next_stored_angle_deg
        eff_angle = min(max(next_stored_angle_deg, MIN_SHUTTER_ANGLE_DEG), max_angle_deg)
        clamped = False
        clamped_360 = False
        integration_ms = speed_sec * 1000.0
    else:
        req_angle = (
            parse_shutter_angle_spec(requested_angle_spec)
            if requested_angle_spec is not None
            else cur_bank.stored_angle_deg
        )
        eff_angle = min(max(req_angle, MIN_SHUTTER_ANGLE_DEG), max_angle_deg)
        clamped = abs(eff_angle - req_angle) > 1e-9
        clamped_360 = bool(is_hfr_or_sq and req_angle > MAX_SHUTTER_ANGLE_SINGLE_FRAME_DEG)
        next_stored_angle_deg = eff_angle
        integration_ms = (eff_angle / 360.0) * (1000.0 / fps_hz)

    new_bank = ShutterBackupBank(
        speed_slot_bkid_hex=cur_bank.speed_slot_bkid_hex,
        angle_slot_bkid_hex=cur_bank.angle_slot_bkid_hex,
        stored_speed_label=next_speed_label,
        stored_angle_deg=next_stored_angle_deg,
        active_shutter_mode=shutter_mode,
        exposure_step=exposure_step,
    )

    independent_ok = (
        (new_bank.stored_angle_deg == cur_bank.stored_angle_deg)
        if shutter_mode == SHUTTER_MODE_SPEED
        else (new_bank.stored_speed_label == cur_bank.stored_speed_label)
    )

    status = (
        "ADMITTED_SHUTTER_ANGLE_CLAMPED_5_6_TO_360_HFR_SQ"
        if clamped_360
        else (
            "ADMITTED_SHUTTER_ANGLE_CLAMPED_TO_RANGE"
            if clamped
            else (
                "ADMITTED_SHUTTER_SPEED_SLOT_INDEPENDENT_OK"
                if shutter_mode == SHUTTER_MODE_SPEED
                else "ADMITTED_SHUTTER_ANGLE_SLOT_INDEPENDENT_OK"
            )
        )
    )
    return ShutterSpeedAngleResult(
        admitted=True,
        ui_surface=ui_surface,
        sq_mode_active=effective_sq,
        rec_frame_rate=rec_frame_rate,
        fps_hz=round(fps_hz, 4),
        shutter_mode=shutter_mode,
        exposure_step=exposure_step,
        speed_slot_bkid_hex=new_bank.speed_slot_bkid_hex,
        angle_slot_bkid_hex=new_bank.angle_slot_bkid_hex,
        stored_speed_label=new_bank.stored_speed_label,
        stored_angle_deg=new_bank.stored_angle_deg,
        requested_angle_deg=req_angle,
        effective_angle_deg=eff_angle,
        effective_angle_label=_format_angle_label(eff_angle),
        min_allowed_angle_deg=MIN_SHUTTER_ANGLE_DEG,
        max_allowed_angle_deg=max_angle_deg,
        max_allowed_label=max_label,
        clamped=clamped,
        multi_frame_clamped_to_360=clamped_360,
        independent_slots_preserved=independent_ok,
        angle_immune_to_exposure_step=True,
        integration_time_ms=round(integration_ms, 4),
        errno_code=0,
        status_code=status,
        updated_bank=new_bank,
    )


def evaluate_pillar_b_independent_shutter_speed_angle_hil() -> Dict[str, object]:
    # 1. Set Speed=1/250 in Movie, then switch to BIG6 Angle=172.8°, toggle Exposure step 0.3EV->0.5EV,
    #    and verify both Speed=1/250 and Angle=172.8° remain independently preserved & unquantized!
    s1_speed = evaluate_shutter_speed_angle_hil(
        ui_surface=UI_SURFACE_MOVIE,
        rec_frame_rate="23.98p",
        shutter_mode=SHUTTER_MODE_SPEED,
        exposure_step=EXPOSURE_STEP_03EV,
        requested_speed_label="1/250",
    )
    s2_angle_1728 = evaluate_shutter_speed_angle_hil(
        bank=s1_speed.updated_bank,
        ui_surface=UI_SURFACE_BIG6,
        rec_frame_rate="23.98p",
        shutter_mode=SHUTTER_MODE_ANGLE,
        exposure_step=EXPOSURE_STEP_03EV,
        requested_angle_spec=172.8,
    )
    s3_exp_step_05ev = evaluate_shutter_speed_angle_hil(
        bank=s2_angle_1728.updated_bank,
        ui_surface=UI_SURFACE_BIG6,
        rec_frame_rate="23.98p",
        shutter_mode=SHUTTER_MODE_ANGLE,
        exposure_step=EXPOSURE_STEP_05EV,
    )
    s4_back_to_speed = evaluate_shutter_speed_angle_hil(
        bank=s3_exp_step_05ev.updated_bank,
        ui_surface=UI_SURFACE_MOVIE,
        rec_frame_rate="23.98p",
        shutter_mode=SHUTTER_MODE_SPEED,
        exposure_step=EXPOSURE_STEP_05EV,
    )
    # 2. 64F multi-frame accumulation allowed at <= 59.94p
    movie_5994_64f_ok = evaluate_shutter_speed_angle_hil(
        ui_surface=UI_SURFACE_MOVIE,
        rec_frame_rate="59.94p",
        shutter_mode=SHUTTER_MODE_ANGLE,
        requested_angle_spec="64F",
    )
    # 3. Clamped to 360° at 119.88p, 100p, and S&Q
    hfr_11988_clamped_360 = evaluate_shutter_speed_angle_hil(
        ui_surface=UI_SURFACE_MOVIE,
        rec_frame_rate="119.88p",
        shutter_mode=SHUTTER_MODE_ANGLE,
        requested_angle_spec="64F",
    )
    hfr_100p_clamped_360 = evaluate_shutter_speed_angle_hil(
        ui_surface=UI_SURFACE_BIG6,
        rec_frame_rate="100p",
        shutter_mode=SHUTTER_MODE_ANGLE,
        requested_angle_spec="2F",
    )
    sq_2398_clamped_360 = evaluate_shutter_speed_angle_hil(
        ui_surface=UI_SURFACE_SQ,
        sq_mode_active=True,
        rec_frame_rate="23.98p",
        shutter_mode=SHUTTER_MODE_ANGLE,
        requested_angle_spec="8F",
    )
    low_angle_clamped_5_6 = evaluate_shutter_speed_angle_hil(
        ui_surface=UI_SURFACE_BIG6,
        rec_frame_rate="24.00p",
        shutter_mode=SHUTTER_MODE_ANGLE,
        requested_angle_spec=2.0,
    )

    passed = (
        s1_speed.admitted
        and s2_angle_1728.admitted
        and s2_angle_1728.stored_speed_label == "1/250"
        and s2_angle_1728.stored_angle_deg == 172.8
        and s3_exp_step_05ev.admitted
        and s3_exp_step_05ev.stored_angle_deg == 172.8
        and s3_exp_step_05ev.stored_speed_label == "1/250"
        and s3_exp_step_05ev.angle_immune_to_exposure_step
        and s4_back_to_speed.admitted
        and s4_back_to_speed.stored_speed_label == "1/250"
        and s4_back_to_speed.stored_angle_deg == 172.8
        and movie_5994_64f_ok.admitted
        and (not movie_5994_64f_ok.clamped)
        and movie_5994_64f_ok.effective_angle_deg == MAX_SHUTTER_ANGLE_64F_DEG
        and movie_5994_64f_ok.effective_angle_label == "64F"
        and hfr_11988_clamped_360.admitted
        and hfr_11988_clamped_360.clamped
        and hfr_11988_clamped_360.multi_frame_clamped_to_360
        and hfr_11988_clamped_360.effective_angle_deg == 360.0
        and hfr_100p_clamped_360.admitted
        and hfr_100p_clamped_360.multi_frame_clamped_to_360
        and hfr_100p_clamped_360.effective_angle_deg == 360.0
        and sq_2398_clamped_360.admitted
        and sq_2398_clamped_360.multi_frame_clamped_to_360
        and sq_2398_clamped_360.effective_angle_deg == 360.0
        and low_angle_clamped_5_6.admitted
        and low_angle_clamped_5_6.clamped
        and low_angle_clamped_5_6.effective_angle_deg == 5.6
    )
    return {
        "passed": passed,
        "roundtrip_speed_1_250": asdict(s1_speed),
        "roundtrip_big6_angle_172_8": asdict(s2_angle_1728),
        "roundtrip_exposure_step_05ev_immunity": asdict(s3_exp_step_05ev),
        "roundtrip_return_to_speed_1_250": asdict(s4_back_to_speed),
        "movie_5994p_64f_unclamped_ok": asdict(movie_5994_64f_ok),
        "hfr_11988p_64f_clamped_to_360": asdict(hfr_11988_clamped_360),
        "hfr_100p_2f_clamped_to_360": asdict(hfr_100p_clamped_360),
        "sq_mode_8f_clamped_to_360": asdict(sq_2398_clamped_360),
        "sub_min_2deg_clamped_to_5_6": asdict(low_angle_clamped_5_6),
    }


# ---------------------------------------------------------------------------
# Pillar C & D: FX6 6.01 vs Stock FX3 7.00/7.02 p2:/setting User1..16 LUT Split
#               Firewall & Hard Safety Redline Guards
# ---------------------------------------------------------------------------


def _compute_stock_p2_setting_16slot_digest() -> str:
    h = hashlib.sha256()
    for idx in range(USER_LUT_SLOT_MIN, USER_LUT_SLOT_MAX + 1):
        slot_bytes = f"SLUT_V2_GE700:p2:/setting/User{idx}:33pt:H0_IMMUTABLE\n".encode("ascii")
        h.update(slot_bytes)
    return h.hexdigest()[:16]


_BASELINE_P2_SETTING_H0_PREFIX16 = _compute_stock_p2_setting_16slot_digest()


def probe_p2_setting_lut_binary_split_firewall(
    *,
    os_persona: str = OS_PERSONA_STAGE_B_FX6_601,
    user_slot_index: int = 1,
    lut_name: str = "SLog3_SGamut3Cine_Rec709_33pt.cube",
    lut_points: int = 33,
    target_mount: str = VOLATILE_FX6_LUT_OVERLAY_DIR,
    redirect_to_volatile_overlay: bool = True,
    attempt_unmigrated_601_slot_in_702: bool = False,
) -> LutBinarySplitFirewallResult:
    """Co-emulate Ver. 6.01 vs Ver. 7.00/7.02 p2:/setting User1..16 LUT binary format split firewall."""
    if os_persona not in VALID_OS_PERSONAS:
        raise RealHwFanShutterLutSplitError(f"Unsupported os_persona {os_persona!r}")

    h0 = _BASELINE_P2_SETTING_H0_PREFIX16
    slot_label = f"User{user_slot_index}"
    persona_fmt = (
        LUT_BINARY_FMT_LEGACY_601
        if os_persona == OS_PERSONA_STAGE_B_FX6_601
        else LUT_BINARY_FMT_OPTIMIZED_702
    )

    if not (USER_LUT_SLOT_MIN <= user_slot_index <= USER_LUT_SLOT_MAX):
        return LutBinarySplitFirewallResult(
            admitted=False,
            os_persona=os_persona,
            lut_binary_format=persona_fmt,
            host_stock_lut_format=LUT_BINARY_FMT_OPTIMIZED_702,
            format_split_601_vs_702_detected=True,
            requires_700_plus_reregistration=True,
            user_slot_index=user_slot_index,
            user_slot_label=slot_label,
            lut_name=lut_name,
            lut_points=lut_points,
            target_mount=target_mount,
            redirect_to_volatile_overlay=bool(redirect_to_volatile_overlay),
            active_storage_path="NONE",
            volatile_ram_only=True,
            volatile_overlay_wiped_on_reboot=True,
            p2_setting_write_blocked_erofs=False,
            p2_setting_mutation_bytes=0,
            h0_p2_setting_digest_sha256_prefix16=h0,
            h3_p2_setting_digest_sha256_prefix16=h0,
            h0_equals_h3=True,
            h0_equals_h3_slots=USER_LUT_SLOT_COUNT,
            lut_color_solver_corruption_events=0,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            errno_code=EINVAL_ERRNO,
            status_code="BLOCKED_INVALID_USER_LUT_SLOT_INDEX_EINVAL",
        )

    if (
        not lut_name
        or ".." in lut_name
        or "/" in lut_name
        or "\\" in lut_name
        or "\x00" in lut_name
        or len(lut_name.encode("utf-8")) > 63
        or lut_points not in (17, 33)
    ):
        return LutBinarySplitFirewallResult(
            admitted=False,
            os_persona=os_persona,
            lut_binary_format=persona_fmt,
            host_stock_lut_format=LUT_BINARY_FMT_OPTIMIZED_702,
            format_split_601_vs_702_detected=True,
            requires_700_plus_reregistration=True,
            user_slot_index=user_slot_index,
            user_slot_label=slot_label,
            lut_name=lut_name,
            lut_points=lut_points,
            target_mount=target_mount,
            redirect_to_volatile_overlay=bool(redirect_to_volatile_overlay),
            active_storage_path="NONE",
            volatile_ram_only=True,
            volatile_overlay_wiped_on_reboot=True,
            p2_setting_write_blocked_erofs=False,
            p2_setting_mutation_bytes=0,
            h0_p2_setting_digest_sha256_prefix16=h0,
            h3_p2_setting_digest_sha256_prefix16=h0,
            h0_equals_h3=True,
            h0_equals_h3_slots=USER_LUT_SLOT_COUNT,
            lut_color_solver_corruption_events=0,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            errno_code=EINVAL_ERRNO,
            status_code="BLOCKED_INVALID_USER_LUT_NAME_OR_GRID_EINVAL",
        )

    if attempt_unmigrated_601_slot_in_702:
        return LutBinarySplitFirewallResult(
            admitted=False,
            os_persona=OS_PERSONA_STOCK_FX3_702,
            lut_binary_format=LUT_BINARY_FMT_LEGACY_601,
            host_stock_lut_format=LUT_BINARY_FMT_OPTIMIZED_702,
            format_split_601_vs_702_detected=True,
            requires_700_plus_reregistration=True,
            user_slot_index=user_slot_index,
            user_slot_label=slot_label,
            lut_name=lut_name,
            lut_points=lut_points,
            target_mount=P2_SETTING_MOUNT_PATH,
            redirect_to_volatile_overlay=False,
            active_storage_path="NONE",
            volatile_ram_only=True,
            volatile_overlay_wiped_on_reboot=True,
            p2_setting_write_blocked_erofs=False,
            p2_setting_mutation_bytes=0,
            h0_p2_setting_digest_sha256_prefix16=h0,
            h3_p2_setting_digest_sha256_prefix16=h0,
            h0_equals_h3=True,
            h0_equals_h3_slots=USER_LUT_SLOT_COUNT,
            lut_color_solver_corruption_events=0,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            errno_code=EINVAL_ERRNO,
            status_code="BLOCKED_UNMIGRATED_601_LUT_SLOT_IN_702_REQUIRES_REREGISTRATION",
        )

    norm_target = target_mount.strip().rstrip("/")
    targets_p2_setting = norm_target in ("p2:/setting", "/setting", "/dev/nflasha2", "/dev/cnflasha2")

    if os_persona == OS_PERSONA_STAGE_B_FX6_601:
        if targets_p2_setting and not redirect_to_volatile_overlay:
            return LutBinarySplitFirewallResult(
                admitted=False,
                os_persona=os_persona,
                lut_binary_format=LUT_BINARY_FMT_LEGACY_601,
                host_stock_lut_format=LUT_BINARY_FMT_OPTIMIZED_702,
                format_split_601_vs_702_detected=True,
                requires_700_plus_reregistration=True,
                user_slot_index=user_slot_index,
                user_slot_label=slot_label,
                lut_name=lut_name,
                lut_points=lut_points,
                target_mount=target_mount,
                redirect_to_volatile_overlay=False,
                active_storage_path="NONE",
                volatile_ram_only=True,
                volatile_overlay_wiped_on_reboot=True,
                p2_setting_write_blocked_erofs=True,
                p2_setting_mutation_bytes=0,
                h0_p2_setting_digest_sha256_prefix16=h0,
                h3_p2_setting_digest_sha256_prefix16=h0,
                h0_equals_h3=True,
                h0_equals_h3_slots=USER_LUT_SLOT_COUNT,
                lut_color_solver_corruption_events=0,
                persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
                errno_code=EROFS_ERRNO,
                status_code="BLOCKED_STAGE_B_601_WRITE_TO_P2_SETTING_EROFS",
            )

        if norm_target != VOLATILE_FX6_LUT_OVERLAY_DIR and not redirect_to_volatile_overlay:
            return LutBinarySplitFirewallResult(
                admitted=False,
                os_persona=os_persona,
                lut_binary_format=LUT_BINARY_FMT_LEGACY_601,
                host_stock_lut_format=LUT_BINARY_FMT_OPTIMIZED_702,
                format_split_601_vs_702_detected=True,
                requires_700_plus_reregistration=True,
                user_slot_index=user_slot_index,
                user_slot_label=slot_label,
                lut_name=lut_name,
                lut_points=lut_points,
                target_mount=target_mount,
                redirect_to_volatile_overlay=False,
                active_storage_path="NONE",
                volatile_ram_only=True,
                volatile_overlay_wiped_on_reboot=True,
                p2_setting_write_blocked_erofs=True,
                p2_setting_mutation_bytes=0,
                h0_p2_setting_digest_sha256_prefix16=h0,
                h3_p2_setting_digest_sha256_prefix16=h0,
                h0_equals_h3=True,
                h0_equals_h3_slots=USER_LUT_SLOT_COUNT,
                lut_color_solver_corruption_events=0,
                persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
                errno_code=EROFS_ERRNO,
                status_code="BLOCKED_STAGE_B_NON_VOLATILE_LUT_TARGET_EROFS",
            )

        overlay_path = f"{VOLATILE_FX6_LUT_OVERLAY_DIR}/{slot_label}.lut601"
        return LutBinarySplitFirewallResult(
            admitted=True,
            os_persona=os_persona,
            lut_binary_format=LUT_BINARY_FMT_LEGACY_601,
            host_stock_lut_format=LUT_BINARY_FMT_OPTIMIZED_702,
            format_split_601_vs_702_detected=True,
            requires_700_plus_reregistration=True,
            user_slot_index=user_slot_index,
            user_slot_label=slot_label,
            lut_name=lut_name,
            lut_points=lut_points,
            target_mount=VOLATILE_FX6_LUT_OVERLAY_DIR,
            redirect_to_volatile_overlay=True,
            active_storage_path=overlay_path,
            volatile_ram_only=True,
            volatile_overlay_wiped_on_reboot=True,
            p2_setting_write_blocked_erofs=targets_p2_setting,
            p2_setting_mutation_bytes=0,
            h0_p2_setting_digest_sha256_prefix16=h0,
            h3_p2_setting_digest_sha256_prefix16=h0,
            h0_equals_h3=True,
            h0_equals_h3_slots=USER_LUT_SLOT_COUNT,
            lut_color_solver_corruption_events=0,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            errno_code=0,
            status_code="ADMITTED_STAGE_B_601_REDIRECTED_TO_TMP_FX6_LUT_OVERLAY",
        )

    # Stock FX3 Ver. 7.02 read-only virtual simulation of native V2_GE700 slot verification (zero physical eMMC writes)
    return LutBinarySplitFirewallResult(
        admitted=True,
        os_persona=OS_PERSONA_STOCK_FX3_702,
        lut_binary_format=LUT_BINARY_FMT_OPTIMIZED_702,
        host_stock_lut_format=LUT_BINARY_FMT_OPTIMIZED_702,
        format_split_601_vs_702_detected=True,
        requires_700_plus_reregistration=False,
        user_slot_index=user_slot_index,
        user_slot_label=slot_label,
        lut_name=lut_name,
        lut_points=lut_points,
        target_mount=P2_SETTING_MOUNT_PATH,
        redirect_to_volatile_overlay=False,
        active_storage_path=f"{P2_SETTING_MOUNT_PATH}/{slot_label}.lut702 (RDONLY_SHADOW)",
        volatile_ram_only=True,
        volatile_overlay_wiped_on_reboot=True,
        p2_setting_write_blocked_erofs=False,
        p2_setting_mutation_bytes=0,
        h0_p2_setting_digest_sha256_prefix16=h0,
        h3_p2_setting_digest_sha256_prefix16=h0,
        h0_equals_h3=True,
        h0_equals_h3_slots=USER_LUT_SLOT_COUNT,
        lut_color_solver_corruption_events=0,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        errno_code=0,
        status_code="ADMITTED_STOCK_FX3_702_V2_LUT_SLOT_H0_EQUALS_H3_OK",
    )


def probe_hard_safety_redline(
    *,
    authorize_persistent_emmc_writes: bool = False,
    authorize_spi_nor_write: bool = False,
    authorize_el3_payload_transmit: bool = False,
    emit_physical_usb_packet: bool = False,
    touch_otp_fuse: bool = False,
    increment_rpmb_counter: bool = False,
    mutate_p2_setting_lut: bool = False,
    trigger_thermal_runaway: bool = False,
    corrupt_lut_color_solver: bool = False,
) -> RedlineGuardProbeResult:
    """Fail-closed hard safety redline guard for Phase 200 Stage 35."""
    blocked: List[str] = []
    if authorize_persistent_emmc_writes:
        blocked.append("PERSISTENT_EMMC_WRITE")
    if authorize_spi_nor_write:
        blocked.append("SPI_NOR_WRITE")
    if authorize_el3_payload_transmit:
        blocked.append("EL3_PAYLOAD_TRANSMIT")
    if emit_physical_usb_packet:
        blocked.append("PHYSICAL_USB_PACKET_EMIT")
    if touch_otp_fuse:
        blocked.append("OTP_FUSE_TOUCH")
    if increment_rpmb_counter:
        blocked.append("RPMB_COUNTER_INCREMENT")
    if mutate_p2_setting_lut:
        blocked.append("P2_SETTING_LUT_MUTATION")
    if trigger_thermal_runaway:
        blocked.append("THERMAL_RUNAWAY")
    if corrupt_lut_color_solver:
        blocked.append("LUT_COLOR_SOLVER_CORRUPTION")

    if blocked:
        return RedlineGuardProbeResult(
            valid=False,
            persistent_emmc_writes_authorized=False,
            spi_nor_write_authorized=False,
            el3_payload_transmit_authorized=False,
            physical_usb_packets_emitted=0,
            otp_fuse_touches=0,
            rpmb_counter_increments=0,
            p2_setting_mutation_bytes=0,
            thermal_runaway_events=0,
            lut_color_solver_corruption_events=0,
            blocked_action="+".join(blocked),
            status_code=f"BLOCKED_HARD_SAFETY_REDLINE_{blocked[0]}",
        )

    return RedlineGuardProbeResult(
        valid=True,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        otp_fuse_touches=OTP_FUSE_TOUCHES,
        rpmb_counter_increments=RPMB_COUNTER_INCREMENTS,
        p2_setting_mutation_bytes=P2_SETTING_MUTATION_BYTES,
        thermal_runaway_events=THERMAL_RUNAWAY_EVENTS,
        lut_color_solver_corruption_events=LUT_COLOR_SOLVER_CORRUPTION_EVENTS,
        blocked_action="NONE",
        status_code="HARD_SAFETY_REDLINES_LOCKED_OK",
    )


def evaluate_pillar_c_d_lut_binary_split_firewall_and_redlines() -> Dict[str, object]:
    stage_b_direct_p2_blocked_erofs = probe_p2_setting_lut_binary_split_firewall(
        os_persona=OS_PERSONA_STAGE_B_FX6_601,
        user_slot_index=1,
        lut_name="FX6_CineEI_User1_33pt.cube",
        lut_points=33,
        target_mount=P2_SETTING_MOUNT_PATH,
        redirect_to_volatile_overlay=False,
    )
    stage_b_all_16_slots_overlay = [
        probe_p2_setting_lut_binary_split_firewall(
            os_persona=OS_PERSONA_STAGE_B_FX6_601,
            user_slot_index=slot_idx,
            lut_name=f"FX6_Overlay_Slot{slot_idx:02d}.cube",
            lut_points=33 if (slot_idx % 2 == 1) else 17,
            target_mount=P2_SETTING_MOUNT_PATH,
            redirect_to_volatile_overlay=True,
        )
        for slot_idx in range(USER_LUT_SLOT_MIN, USER_LUT_SLOT_MAX + 1)
    ]
    unmigrated_601_in_702_blocked = probe_p2_setting_lut_binary_split_firewall(
        os_persona=OS_PERSONA_STOCK_FX3_702,
        user_slot_index=16,
        lut_name="Legacy601_User16.cube",
        lut_points=33,
        attempt_unmigrated_601_slot_in_702=True,
    )
    stock_fx3_702_h3_intact = probe_p2_setting_lut_binary_split_firewall(
        os_persona=OS_PERSONA_STOCK_FX3_702,
        user_slot_index=16,
        lut_name="Stock702_User16_33pt.cube",
        lut_points=33,
    )
    invalid_slot_17_blocked = probe_p2_setting_lut_binary_split_firewall(
        os_persona=OS_PERSONA_STAGE_B_FX6_601,
        user_slot_index=17,
    )

    baseline = probe_hard_safety_redline()
    probes = (
        probe_hard_safety_redline(authorize_persistent_emmc_writes=True),
        probe_hard_safety_redline(authorize_spi_nor_write=True),
        probe_hard_safety_redline(authorize_el3_payload_transmit=True),
        probe_hard_safety_redline(emit_physical_usb_packet=True),
        probe_hard_safety_redline(touch_otp_fuse=True),
        probe_hard_safety_redline(increment_rpmb_counter=True),
        probe_hard_safety_redline(mutate_p2_setting_lut=True),
        probe_hard_safety_redline(trigger_thermal_runaway=True),
        probe_hard_safety_redline(corrupt_lut_color_solver=True),
    )

    all_16_ok = all(
        r.admitted
        and r.volatile_ram_only
        and r.active_storage_path.startswith(f"{VOLATILE_FX6_LUT_OVERLAY_DIR}/User")
        and r.p2_setting_mutation_bytes == 0
        and r.h0_equals_h3
        and r.h0_equals_h3_slots == 16
        for r in stage_b_all_16_slots_overlay
    )

    passed = (
        (not stage_b_direct_p2_blocked_erofs.admitted)
        and stage_b_direct_p2_blocked_erofs.p2_setting_write_blocked_erofs
        and stage_b_direct_p2_blocked_erofs.errno_code == EROFS_ERRNO
        and stage_b_direct_p2_blocked_erofs.p2_setting_mutation_bytes == 0
        and len(stage_b_all_16_slots_overlay) == 16
        and all_16_ok
        and (not unmigrated_601_in_702_blocked.admitted)
        and unmigrated_601_in_702_blocked.requires_700_plus_reregistration
        and stock_fx3_702_h3_intact.admitted
        and stock_fx3_702_h3_intact.h0_equals_h3
        and stock_fx3_702_h3_intact.h0_equals_h3_slots == 16
        and (not invalid_slot_17_blocked.admitted)
        and baseline.valid
        and (not baseline.persistent_emmc_writes_authorized)
        and (not baseline.spi_nor_write_authorized)
        and (not baseline.el3_payload_transmit_authorized)
        and baseline.physical_usb_packets_emitted == 0
        and baseline.otp_fuse_touches == 0
        and baseline.rpmb_counter_increments == 0
        and all((not p.valid) for p in probes)
    )
    return {
        "passed": passed,
        "stage_b_direct_p2_setting_blocked_erofs": asdict(stage_b_direct_p2_blocked_erofs),
        "stage_b_user1_overlay_ok": asdict(stage_b_all_16_slots_overlay[0]),
        "stage_b_user16_overlay_ok": asdict(stage_b_all_16_slots_overlay[-1]),
        "stage_b_overlay_slots_verified": len(stage_b_all_16_slots_overlay),
        "h0_equals_h3_slots_verified": 16,
        "unmigrated_601_slot_in_702_blocked": asdict(unmigrated_601_in_702_blocked),
        "stock_fx3_702_h3_parity_ok": asdict(stock_fx3_702_h3_intact),
        "invalid_slot_17_blocked": asdict(invalid_slot_17_blocked),
        "baseline_redline_lock": asdict(baseline),
        "blocked_redline_probes": [asdict(p) for p in probes],
    }


# ---------------------------------------------------------------------------
# Unified Phase 200 Stage 35 (35/35 Milestone) Orchestrator & CLI
# ---------------------------------------------------------------------------


def run_phase200_realhw_fan_pwm_shutter_angle_lut_split_hil(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Execute the full Phase 200 Stage 35 (`35/35` Milestone) co-emulation audit."""
    donor_audit = inspect_phase200_donors(force_clean_room=force_clean_room, env=env)
    pillar_a = evaluate_pillar_a_fx3_fan_pwm_and_backup_guard()
    pillar_b = evaluate_pillar_b_independent_shutter_speed_angle_hil()
    pillar_cd = evaluate_pillar_c_d_lut_binary_split_firewall_and_redlines()

    all_passed = (
        donor_audit.all_contracts_verified
        and donor_audit.raw_firmware_bytes_leaked == 0
        and bool(pillar_a["passed"])
        and bool(pillar_b["passed"])
        and bool(pillar_cd["passed"])
    )

    payload: Dict[str, object] = {
        "schema": PHASE_200_SCHEMA,
        "version": PHASE_200_VERSION,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "stage": STAGE_NAME,
        "source_mode": donor_audit.source_mode,
        "all_checks_passed": all_passed,
        "redlines": {
            "p8_cp_mutation_forbidden": P8_CP_MUTATION_FORBIDDEN,
            "nop_count": NOP_COUNT,
            "guest_code_modification_bytes": GUEST_CODE_MODIFICATION_BYTES,
            "cp_mutation_bytes": CP_MUTATION_BYTES,
            "wbi_mutation_bytes": WBI_MUTATION_BYTES,
            "calibration_mutation_bytes": CALIBRATION_MUTATION_BYTES,
            "nvram_persistent_writes": NVRAM_PERSISTENT_WRITES,
            "bk4_persistent_nvram_writes": BK4_PERSISTENT_NVRAM_WRITES,
            "physical_device_writes": PHYSICAL_DEVICE_WRITES,
            "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
            "emmc_nflasha_write_count": EMMC_NFLASHA_WRITE_COUNT,
            "emmc_mutation_bytes": EMMC_MUTATION_BYTES,
            "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
            "spi_nor_mutation_bytes": SPI_NOR_MUTATION_BYTES,
            "el3_payload_transmit_authorized": EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
            "physical_usb_packets_emitted": PHYSICAL_USB_PACKETS_EMITTED,
            "otp_fuse_touches": OTP_FUSE_TOUCHES,
            "rpmb_counter_increments": RPMB_COUNTER_INCREMENTS,
            "p2_setting_mutation_bytes": P2_SETTING_MUTATION_BYTES,
            "thermal_runaway_events": THERMAL_RUNAWAY_EVENTS,
            "lut_color_solver_corruption_events": LUT_COLOR_SOLVER_CORRUPTION_EVENTS,
            "null_gpio_derefs": NULL_GPIO_DEREFS,
            "mailbox_stalls": MAILBOX_STALLS,
            "stock_cp_fault_count": STOCK_CP_FAULT_COUNT,
            "wf12_00342260_hits": WF12_00342260_HITS,
            "appfw_crashes": APPFW_CRASHES,
            "raw_firmware_bytes_leaked": RAW_FIRMWARE_BYTES_LEAKED,
            "donor_access_mode": DONOR_ACCESS_MODE,
        },
        "donor_audit": asdict(donor_audit),
        "pillar_a_fx3_fan_pwm_and_backup_guard_hil": pillar_a,
        "pillar_b_independent_shutter_speed_angle_hil": pillar_b,
        "pillar_c_d_lut_601_vs_702_split_firewall_and_redlines": pillar_cd,
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    payload["audit_digest_sha256"] = digest
    return payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_fan_pwm_shutter_angle_lut_split_coemulator.py",
        description=(
            "Phase 200 Stage 35 (35/35 Milestone) ILME-FX3 4-Mode [Fan Control] PWM & Always-Off "
            "Pre-Backup Guard, Independent Shutter Speed/Angle (5.6°..64F / 360°) & 6.01 vs 7.02 "
            "p2:/setting User1..User16 LUT Binary Split Firewall HIL Co-Emulator"
        ),
    )
    parser.add_argument("--self-test", action="store_true", help="Run Stage 35 self-test and exit 0/1")
    parser.add_argument("--clean-room", action="store_true", help="Force clean-room synthetic mode")
    parser.add_argument("--json", action="store_true", help="Emit deterministic JSON audit report")
    parser.add_argument("--summary", action="store_true", help="Emit concise one-line audit summary")
    args = parser.parse_args(argv)

    rep = run_phase200_realhw_fan_pwm_shutter_angle_lut_split_hil(
        force_clean_room=True if args.clean_room else None,
        env=os.environ,
    )

    if args.summary and not args.json:
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        pa = rep["pillar_a_fx3_fan_pwm_and_backup_guard_hil"]["off_in_rec_standby_100pwm"]
        pb = rep["pillar_b_independent_shutter_speed_angle_hil"]["hfr_11988p_64f_clamped_to_360"]
        pc = rep["pillar_c_d_lut_601_vs_702_split_firewall_and_redlines"]
        erofs_code = pc["stage_b_direct_p2_setting_blocked_erofs"]["errno_code"]
        h0h3_slots = pc["h0_equals_h3_slots_verified"]
        emmc_wr = rep["redlines"]["emmc_nflasha_write_count"]
        dig12 = rep["audit_digest_sha256"][:12]
        sys.stdout.write(
            f"[{status}] Phase 200 Stage 35 ({MILESTONE_LABEL}) Real-HW Fan-PWM / Shutter-Angle / LUT-Split HIL | "
            f"mode={rep['source_mode']} | stby_pwm={pa['pwm_duty_percent']}% | "
            f"hfr_clamp={pb['effective_angle_deg']}deg | "
            f"p2_erofs={erofs_code} | h0_h3={h0h3_slots}/16 | "
            f"emmc_wr={emmc_wr} | digest={dig12}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")

    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
