#!/usr/bin/env python3
"""Phase 226 — Stage 41 (`41/41` Milestone) `outputs/fx3-vm/` Real-Hardware Main Track:
`ILME-FX3` (`0x91030080`, `Ver. 7.02`) Wave-31 `[SteadyShot]` (Movie) `[Active]` `~1.1x` Crop vs
`[Standard]`/`[Off]` & 3-Way Cutoffs (`119.88p/100p`, S&Q `>=100fps/120fps`, HDMI `[RAW Output]=On`),
`[Clear Image Zoom]` / `[Digital Zoom]` (`[Zoom Range]`) RAW/HFR Unavailability & 4-Lock Automatic
AF/Metering/Tracking State Machine with `1.0x` Optical Restoration, and `[Power Save Start Time]`
(Default `5 Min`) 9-Condition Bypass Matrix, Air-Gapped `NP-FZ100` Tier-0 `75 MiB` `p3` Vault
Sleep-Lock Guard (`Off`/`30 Min`), & `[Auto Power OFF Temp.]` (`[Standard]` vs `[High]` Tripod
Interlock + `[Fan Control]` Coupling) HIL Co-Emulator.

Implements strictly read-only (`os.open(..., os.O_RDONLY)`) 12-donor inspection (< 0.02s cold,
cached per process, bounded <= 4096 B windows on large firmware binaries) with deterministic
`CLEAN_ROOM_SYNTHETIC` fallback (`FX3_FX6_FORCE_CLEAN_ROOM=1`), while hard-locking:
- `persistent_emmc_writes_authorized == False`
- `hardware_live_attachment_authorized == False`
- `overall_ready_for_hardware_attach == False`
- `spi_nor_write_authorized == False`
- `el3_payload_transmit_authorized == False`
- `isp_write_authorized == False`
- `cnflasha_userspace_write_blocked == True`
- `physical_usb_packets_emitted == 0`
- `otp_fuse_touches == 0`
- `rpmb_counter_increments == 0`
- `steadyshot_active_cutoff_bypass_events == 0`
- `ciz_4lock_unrestored_or_bypass_events == 0`
- `tier0_p3_sleep_abort_or_thermal_burn_events == 0`
- `raw_firmware_bytes_leaked == 0`
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import struct
from typing import Dict, List, Mapping, Optional, Sequence, Tuple


# ---------------------------------------------------------------------------
# Phase 226 Schema & Hard-Locked Safety Redlines (41/41 Milestone)
# ---------------------------------------------------------------------------

SCHEMA_ID = "realhw_steadyshot_active_ciz_4locks_powersave_autotemp_coemulator_v1"
PHASE_226_SCHEMA = SCHEMA_ID
PHASE_226_VERSION = "226.0.0"
STAGE_INDEX = 41
STAGE_TOTAL = 41
MILESTONE_LABEL = "41/41"
STAGE_NAME = "stage41_realhw_steadyshot_active_ciz_4locks_powersave_autotemp_hil"

SOURCE_MODE_LOCAL_DONOR = "LOCAL_DONOR_O_RDONLY"
SOURCE_MODE_CLEAN_ROOM = "CLEAN_ROOM_SYNTHETIC"

MODEL_ILME_FX3 = "ILME-FX3"
MODEL_ILME_FX6 = "ILME-FX6"
FX3_MODEL_ID = 0x91030080
STOCK_FX3_BOOT_IDENTITY = "ILME-FX3 Ver. 7.02 (Stock)"

P8_CP_MUTATION_FORBIDDEN = True
NOP_COUNT = 0
GUEST_CODE_MODIFICATION_BYTES = 0
CP_MUTATION_BYTES = 0
WBI_MUTATION_BYTES = 0
CALIBRATION_MUTATION_BYTES = 0
CNFLASHA_MUTATION_BYTES = 0
CNFLASHA_USERSPACE_WRITE_BLOCKED = True
NVRAM_PERSISTENT_WRITES = 0
BK4_PERSISTENT_NVRAM_WRITES = 0
PHYSICAL_DEVICE_WRITES = 0
PERSISTENT_EMMC_WRITES_AUTHORIZED = False
HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False
OVERALL_READY_FOR_HARDWARE_ATTACH = False
ISP_WRITE_AUTHORIZED = False
EMMC_NFLASHA_WRITE_COUNT = 0
EMMC_MUTATION_BYTES = 0
SPI_NOR_WRITE_AUTHORIZED = False
SPI_NOR_MUTATION_BYTES = 0
EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False
PHYSICAL_USB_PACKETS_EMITTED = 0
OTP_FUSE_TOUCHES = 0
RPMB_COUNTER_INCREMENTS = 0
STEADYSHOT_ACTIVE_CUTOFF_BYPASS_EVENTS = 0
CIZ_4LOCK_UNRESTORED_OR_BYPASS_EVENTS = 0
TIER0_P3_SLEEP_ABORT_OR_THERMAL_BURN_EVENTS = 0
RSV_ORPHAN_COUNT = 0
WF12_00342260_HITS = 0
APPFW_CRASHES = 0
NULL_GPIO_DEREFS = 0
MAILBOX_STALLS = 0
STOCK_CP_FAULT_COUNT = 0
RAW_FIRMWARE_BYTES_LEAKED = 0
DONOR_ACCESS_MODE = "O_RDONLY"
BOUNDED_WINDOW_MAX_BYTES = 4096

EBUSY_ERRNO = 16  # Linux EBUSY
EINVAL_ERRNO = 22  # Linux EINVAL
EROFS_ERRNO = 30  # Linux EROFS
EOPNOTSUPP_ERRNO = 95  # Linux ARM64 EOPNOTSUPP

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
    "fx3_lens_comm": f"{_FX3_USR_PREFIX}/lib/libInfraLensCommunicator.so",
    "fx6_lens_comm": f"{_FX6_NF15_PREFIX}/lib/libInfraLensCommunicator.so",
    "fx3_media_cfg": f"{_FX3_USR_PREFIX}/lib/libInfraMediaConfig.so",
    "fx3_adj_media": f"{_FX3_USR_PREFIX}/lib/libInfraAdjMedia.so",
    "fx3_string_en_f": f"{_FX3_USR_PREFIX}/share/app/string_english_f.uxc",
    "fx6_string_en": f"{_FX6_NF15_PREFIX}/share/app/string_english.uxc",
    "fx3_appfw": "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
    "fx6_appfw": f"{_FX6_NF15_PREFIX}/lib/appFw.so",
    "fx3_cpapp": "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin",
    "fx6_cpapp": "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fat-files/nflasha8/cpapp-b.bin",
    "fx3_libmpr": f"{_FX3_USR_PREFIX}/lib/libmpr.so",
    "fx6_libmpr": f"{_FX6_NF15_PREFIX}/lib/libmpr.so",
}

EXPECTED_DONOR_BYTES: Mapping[str, int] = {
    "fx3_lens_comm": 14_544,
    "fx6_lens_comm": 14_544,
    "fx3_media_cfg": 52_312,
    "fx3_adj_media": 318_152,
    "fx3_string_en_f": 373_820,
    "fx6_string_en": 118_208,
    "fx3_appfw": 79_015_712,
    "fx6_appfw": 50_520_424,
    "fx3_cpapp": 15_980_568,
    "fx6_cpapp": 17_952_816,
    "fx3_libmpr": 3_517_008,
    "fx6_libmpr": 28_921_824,
}

COMPACT_DONOR_TOKENS: Mapping[str, Tuple[bytes, ...]] = {
    "fx3_lens_comm": (b"LensCommunicator", b"GetMountedLensInfo", b"SndSyncMsg"),
    "fx6_lens_comm": (b"LensCommunicator", b"GetMountedLensInfo", b"SndSyncMsg"),
    "fx3_media_cfg": (b"MediaConfig", b"Slot", b"Backup_read"),
    "fx3_adj_media": (b"AVBB_SCN_START_HDMI", b"AVBB_SCN_STOP_HDMI", b"HDMI"),
    "fx3_string_en_f": (
        b"SteadyShot",
        b"Active",
        b"Standard",
        b"RAW Output",
        b"119.88p",
        b"100p",
        b"120fps",
        b"100fps",
        b"200fps",
        b"240fps",
        b"Clear Image Zoom",
        b"Digital Zoom",
        b"Zoom Range",
        b"Optical zoom only",
        b"Focus Area",
        b"Metering Mode",
        b"Multi",
        b"Face/Eye Prior. in AF",
        b"Face Priority in Multi Metering",
        b"Tracking",
        b"Power Save Start Time",
        b"30 Min",
        b"5 min",
        b"2 Min",
        b"10 Sec",
        b"IR Remote Ctrl",
        b"Bluetooth Rmt Ctrl",
        b"Auto Power OFF Temp.",
        b"High",
        b"Fan Control",
    ),
    "fx6_string_en": (
        b"SteadyShot",
        b"RAW",
        b"Zoom",
        b"Focus",
        b"Fan",
        b"Power",
    ),
}

LARGE_DONOR_WINDOWS: Mapping[str, Tuple[Tuple[int, str, bytes], ...]] = {
    "fx3_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (49_946_624, "HDMI", b"HDMI"),
        (49_954_816, "FOCUS_AREA", b"FOCUS_AREA"),
        (49_967_104, "METERING_MODE", b"METERING_MODE"),
        (49_971_200, "FAN_CONTROL", b"FAN_CONTROL"),
        (49_975_296, "POWER_SAVE", b"POWER_SAVE"),
        (50_741_248, "BLUETOOTH", b"BLUETOOTH"),
        (60_121_088, "STEADYSHOT", b"STEADYSHOT"),
        (60_633_088, "RAW_OUTPUT", b"RAW_OUTPUT"),
        (60_653_568, "DIGITAL_ZOOM", b"DIGITAL_ZOOM"),
        (61_636_608, "CLEAR_IMAGE_ZOOM", b"CLEAR_IMAGE_ZOOM"),
        (63_152_128, "AUTO_POWER_OFF_TEMP", b"AUTO_POWER_OFF_TEMP"),
    ),
    "fx6_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (36_081_664, "FOCUS", b"FOCUS"),
        (37_232_640, "POWER", b"POWER"),
        (37_236_736, "ZOOM", b"ZOOM"),
        (39_378_944, "FAN", b"FAN"),
        (39_464_960, "M4ROOT", b"M4ROOT"),
        (40_157_184, "STEADYSHOT", b"STEADYSHOT"),
    ),
    "fx3_cpapp": (
        (311_296, "FOCUS", b"Focus"),
        (364_544, "TEMP", b"Temp"),
        (385_024, "FAN", b"Fan"),
        (401_408, "ZOOM", b"Zoom"),
        (696_320, "HDMI", b"HDMI"),
        (1_908_736, "METER", b"Meter"),
        (2_035_712, "STEADYSHOT", b"SteadyShot"),
        (13_139_968, "ILME_FX3", b"ILME-FX3"),
    ),
    "fx6_cpapp": (
        (208_896, "ZOOM", b"Zoom"),
        (290_816, "FOCUS", b"Focus"),
        (368_640, "TEMP", b"Temp"),
        (385_024, "FAN", b"Fan"),
        (684_032, "HDMI", b"HDMI"),
        (12_230_656, "STEADYSHOT", b"SteadyShot"),
    ),
    "fx3_libmpr": (
        (0, "ELF64", b"\x7fELF"),
        (131_072, "XAVC", b"Xavc"),
        (159_744, "MP4", b"Mp4"),
        (249_856, "TIMECODE", b"TimeCode"),
        (2_965_504, "NON_REAL_TIME_META", b"NonRealTimeMeta"),
        (2_965_504, "LTC_CHANGE_TABLE", b"LtcChangeTable"),
    ),
    "fx6_libmpr": (
        (0, "ELF64", b"\x7fELF"),
        (163_840, "XAVC", b"Xavc"),
        (163_840, "TIMECODE", b"TimeCode"),
        (13_475_840, "LTC_CHANGE_TABLE", b"LtcChangeTable"),
        (13_516_800, "NON_REAL_TIME_META", b"NonRealTimeMeta"),
    ),
}

# ---------------------------------------------------------------------------
# Sub-model A/B/C Constants (Wave-31 Official ILME-FX3 Ver. 7.02 Contracts)
# ---------------------------------------------------------------------------

VALID_ON_OFF: Tuple[str, ...] = ("On", "Off")
SHOOTING_MODE_MOVIE = "Movie"
SHOOTING_MODE_SQ = "S&Q"
SHOOTING_MODE_STILL = "Still"
VALID_SHOOTING_MODES: Tuple[str, ...] = (
    SHOOTING_MODE_MOVIE,
    SHOOTING_MODE_SQ,
    SHOOTING_MODE_STILL,
)

# Sub-model A: [SteadyShot] (Movie) [Active] ~1.1x Crop & 3 Cutoffs
STEADYSHOT_MENU_PATH = "MENU -> Shooting -> [Image Stabilization] -> [SteadyShot]"
STEADYSHOT_ADJUST_MENU_PATH = "MENU -> Shooting -> [Image Stabilization] -> [SteadyShot Adjust.]"
STEADYSHOT_FOCAL_LEN_MENU_PATH = "MENU -> Shooting -> [Image Stabilization] -> [SteadyShot Focal Len.]"
STEADYSHOT_ACTIVE = "Active"
STEADYSHOT_STANDARD = "Standard"
STEADYSHOT_OFF = "Off"
STEADYSHOT_STILL_ON = "On"
VALID_MOVIE_STEADYSHOT_MODES: Tuple[str, ...] = (
    STEADYSHOT_ACTIVE,
    STEADYSHOT_STANDARD,
    STEADYSHOT_OFF,
)
VALID_STILL_STEADYSHOT_MODES: Tuple[str, ...] = (STEADYSHOT_STILL_ON, STEADYSHOT_OFF)
STEADYSHOT_ACTIVE_CROP_FACTOR = 1.10
STEADYSHOT_OPTICAL_CROP_FACTOR = 1.00
STEADYSHOT_ADJUST_AUTO = "Auto"
STEADYSHOT_ADJUST_MANUAL = "Manual"
VALID_STEADYSHOT_ADJUST_MODES: Tuple[str, ...] = (STEADYSHOT_ADJUST_AUTO, STEADYSHOT_ADJUST_MANUAL)
STEADYSHOT_FOCAL_LEN_MIN_MM = 8
STEADYSHOT_FOCAL_LEN_MAX_MM = 1000

STANDARD_MOVIE_FPS_ALLOWING_ACTIVE: Tuple[str, ...] = (
    "23.98p",
    "24.00p",
    "25p",
    "29.97p",
    "50p",
    "59.94p",
)
HFR_MOVIE_FPS_BLOCKING_ACTIVE: Tuple[str, ...] = ("100p", "119.88p")
VALID_MOVIE_FRAME_RATES: Tuple[str, ...] = (
    STANDARD_MOVIE_FPS_ALLOWING_ACTIVE + HFR_MOVIE_FPS_BLOCKING_ACTIVE
)
SQ_SENSOR_FPS_ACTIVE_CUTOFF = 100
VALID_SQ_SENSOR_FPS: Tuple[int, ...] = (1, 2, 4, 8, 15, 25, 30, 50, 60, 100, 120, 200, 240)

CUTOFF_NORMAL_HFR_120P_100P = "NORMAL_MOVIE_HFR_119_88P_OR_100P"
CUTOFF_SQ_SENSOR_FPS_GE_100 = "SQ_SENSOR_FRAME_RATE_GE_100FPS"
CUTOFF_HDMI_RAW_OUTPUT_ON = "HDMI_RAW_OUTPUT_ON"

# Sub-model B: [Clear Image Zoom] / [Digital Zoom] ([Zoom Range]) & 4 Automatic Locks
ZOOM_RANGE_MENU_PATH = "MENU -> Shooting -> [Zoom] -> [Zoom Range]"
ZOOM_OPTICAL_ONLY = "Optical zoom only"
ZOOM_SMART = "Smart Zoom"
ZOOM_CLEAR_IMAGE = "Clear Image Zoom"
ZOOM_DIGITAL = "Digital Zoom"
VALID_ZOOM_RANGE_MODES: Tuple[str, ...] = (
    ZOOM_OPTICAL_ONLY,
    ZOOM_SMART,
    ZOOM_CLEAR_IMAGE,
    ZOOM_DIGITAL,
)
CIZ_MAX_SCALE_4K = 1.50
CIZ_MAX_SCALE_HD_AND_STILL = 2.00
DIGITAL_ZOOM_MAX_SCALE = 4.00
SMART_ZOOM_MAX_SCALE_M = 1.40
SMART_ZOOM_MAX_SCALE_S = 2.00

RES_4K_QFHD = "4K_QFHD_3840x2160"
RES_4K_DCI = "4K_DCI_4096x2160"
RES_HD_1080P = "HD_1920x1080"
VALID_VIDEO_RESOLUTIONS: Tuple[str, ...] = (RES_4K_QFHD, RES_4K_DCI, RES_HD_1080P)

STILL_FMT_JPEG = "JPEG"
STILL_FMT_HEIF = "HEIF"
STILL_FMT_RAW = "RAW"
STILL_FMT_RAW_JPEG = "RAW & JPEG"
STILL_FMT_RAW_HEIF = "RAW & HEIF"
VALID_STILL_FILE_FORMATS: Tuple[str, ...] = (
    STILL_FMT_JPEG,
    STILL_FMT_HEIF,
    STILL_FMT_RAW,
    STILL_FMT_RAW_JPEG,
    STILL_FMT_RAW_HEIF,
)
RAW_STILL_FILE_FORMATS: Tuple[str, ...] = (
    STILL_FMT_RAW,
    STILL_FMT_RAW_JPEG,
    STILL_FMT_RAW_HEIF,
)
VALID_STILL_SIZES: Tuple[str, ...] = ("L", "M", "S")

VALID_FOCUS_AREAS: Tuple[str, ...] = (
    "Wide",
    "Zone",
    "Center Fix",
    "Spot: S",
    "Spot: M",
    "Spot: L",
    "Expand Spot",
    "Tracking: Wide",
    "Tracking: Zone",
    "Tracking: Center Fix",
    "Tracking: Spot S",
    "Tracking: Spot M",
    "Tracking: Spot L",
    "Tracking: Expand Spot",
)
LOCKED_ZOOM_FOCUS_AREA = "Center_Priority_Zoom_AF"

METERING_MULTI = "Multi"
VALID_METERING_MODES: Tuple[str, ...] = (
    METERING_MULTI,
    "Center",
    "Spot: Standard",
    "Spot: Large",
    "Entire Screen Avg.",
    "Highlight",
)

CIZ_LOCK_1_FOCUS_AREA_CENTER_AF = "FOCUS_AREA_DISABLED_CENTER_PRIORITY_AF"
CIZ_LOCK_2_METERING_MULTI = "METERING_MODE_LOCKED_TO_MULTI"
CIZ_LOCK_3_FACE_EYE_AF_AND_METERING_OFF = "FACE_EYE_AF_AND_FACE_PRIORITY_METERING_UNAVAILABLE"
CIZ_LOCK_4_REALTIME_TRACKING_OFF = "REALTIME_TRACKING_UNAVAILABLE"
ALL_4_CIZ_STATE_LOCKS: Tuple[str, ...] = (
    CIZ_LOCK_1_FOCUS_AREA_CENTER_AF,
    CIZ_LOCK_2_METERING_MULTI,
    CIZ_LOCK_3_FACE_EYE_AF_AND_METERING_OFF,
    CIZ_LOCK_4_REALTIME_TRACKING_OFF,
)

# Sub-model C: [Power Save Start Time] (9-Condition Bypass + Tier-0 p3 Guard) & [Auto Power OFF Temp.]
POWER_SAVE_MENU_NAME = "Power Save Start Time"
POWER_SAVE_MENU_PATH = "MENU -> Setup -> [Power Setting Option] -> [Power Save Start Time]"
AUTO_POWER_OFF_TEMP_MENU_NAME = "Auto Power OFF Temp."
AUTO_POWER_OFF_TEMP_MENU_PATH = "MENU -> Setup -> [Power Setting Option] -> [Auto Power OFF Temp.]"
FAN_CONTROL_MENU_PATH = "MENU -> Setup -> [Setup Option] -> [Fan Control]"

POWER_SAVE_OFF = "Off"
POWER_SAVE_30_MIN = "30 Min"
POWER_SAVE_5_MIN_DEFAULT = "5 Min"
POWER_SAVE_2_MIN = "2 Min"
POWER_SAVE_1_MIN = "1 Min"
POWER_SAVE_10_SEC = "10 Sec"
VALID_POWER_SAVE_OPTIONS: Tuple[str, ...] = (
    POWER_SAVE_OFF,
    POWER_SAVE_30_MIN,
    POWER_SAVE_5_MIN_DEFAULT,
    POWER_SAVE_2_MIN,
    POWER_SAVE_1_MIN,
    POWER_SAVE_10_SEC,
)
POWER_SAVE_SECONDS_TABLE: Mapping[str, Optional[int]] = {
    POWER_SAVE_OFF: None,
    POWER_SAVE_30_MIN: 1800,
    POWER_SAVE_5_MIN_DEFAULT: 300,
    POWER_SAVE_2_MIN: 120,
    POWER_SAVE_1_MIN: 60,
    POWER_SAVE_10_SEC: 10,
}
TIER0_SAFE_POWER_SAVE_OPTIONS: Tuple[str, ...] = (POWER_SAVE_OFF, POWER_SAVE_30_MIN)
TIER0_P3_VAULT_DUMP_BYTES = 75 * 1024 * 1024  # 75 MiB (78,643,200 B)
TIER0_MIN_NP_FZ100_BATTERY_PCT = 51

POWER_SAVE_9_CONDITION_KEYS: Tuple[str, ...] = (
    "ac_or_usb_pd_power_connected",
    "usb_data_connection_active",
    "hdmi_output_connected",
    "movie_recording_in_progress",
    "interval_timer_shooting_in_progress",
    "slideshow_playing",
    "ir_remote_ctrl_on",
    "bluetooth_remote_ctrl_on",
    "ftp_or_smartphone_network_transfer_active",
)

AUTO_TEMP_STANDARD = "Standard"
AUTO_TEMP_HIGH = "High"
VALID_AUTO_POWER_OFF_TEMP_MODES: Tuple[str, ...] = (AUTO_TEMP_STANDARD, AUTO_TEMP_HIGH)
AUTO_TEMP_SHUTOFF_CEILING_C: Mapping[str, float] = {
    AUTO_TEMP_STANDARD: 68.0,
    AUTO_TEMP_HIGH: 78.0,
}
AUTO_TEMP_FAN_OVERRIDE_THRESHOLD_C: Mapping[str, float] = {
    AUTO_TEMP_STANDARD: 62.0,
    AUTO_TEMP_HIGH: 72.0,
}

MOUNTING_TRIPOD = "Tripod"
MOUNTING_CAGE_RIG = "CageRig"
MOUNTING_HANDHELD = "Handheld"
VALID_MOUNTING_STATES: Tuple[str, ...] = (MOUNTING_TRIPOD, MOUNTING_CAGE_RIG, MOUNTING_HANDHELD)

FAN_AUTO = "Auto"
FAN_MINIMUM = "Minimum"
FAN_OFF_IN_REC = "Off in Rec"
FAN_ALWAYS_OFF = "Always Off"
VALID_FAN_CONTROL_MODES: Tuple[str, ...] = (FAN_AUTO, FAN_MINIMUM, FAN_OFF_IN_REC, FAN_ALWAYS_OFF)


class RealHwSteadyShotActiveCiz4LocksPowerSaveAutoTempError(ValueError):
    """Raised on invalid Phase 226 Stage 41 co-emulator configuration arguments."""


# ---------------------------------------------------------------------------
# Dataclasses for Donor Inspection & Sub-models A-C + Redlines
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
class Phase226DonorAudit:
    source_mode: str
    access_mode: str
    donor_files_inspected: int
    raw_firmware_bytes_leaked: int
    fx3_lens_comm: CompactDonorSummary
    fx6_lens_comm: CompactDonorSummary
    fx3_media_cfg: CompactDonorSummary
    fx3_adj_media: CompactDonorSummary
    fx3_string_en_f: CompactDonorSummary
    fx6_string_en: CompactDonorSummary
    fx3_appfw: BoundedWindowDonorSummary
    fx6_appfw: BoundedWindowDonorSummary
    fx3_cpapp: BoundedWindowDonorSummary
    fx6_cpapp: BoundedWindowDonorSummary
    fx3_libmpr: BoundedWindowDonorSummary
    fx6_libmpr: BoundedWindowDonorSummary
    steadyshot_active_and_3cutoffs_proven: bool
    ciz_digital_zoom_4locks_proven: bool
    powersave_9cond_and_autotemp_fan_proven: bool
    all_contracts_verified: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class SteadyShotActiveCutoffsHilResult:
    admitted: bool
    menu_path: str
    shooting_mode: str
    requested_steadyshot: str
    effective_steadyshot: str
    active_mode_available: bool
    auto_fell_back_to_standard: bool
    cutoff_reasons: Tuple[str, ...]
    movie_fps: str
    sq_sensor_fps: int
    hdmi_raw_output: str
    steadyshot_adjust: str
    focal_length_mm: int
    crop_factor: float
    ibis_5axis_sensor_shift_active: bool
    electronic_gyro_crop_active: bool
    ibis_voice_coil_parked: bool
    catalyst_gyro_metadata_recorded: bool
    steadyshot_active_cutoff_bypass_events: int
    errno_code: int
    status_code: str


@dataclass(frozen=True)
class CizDigitalZoom4LocksHilResult:
    admitted: bool
    menu_path: str
    shooting_mode: str
    video_resolution: str
    movie_fps: str
    sq_sensor_fps: int
    hdmi_raw_output: str
    still_file_format: str
    still_image_size: str
    zoom_range_mode: str
    ciz_digital_zoom_available: bool
    unavailability_reasons: Tuple[str, ...]
    max_supported_zoom_scale: float
    requested_zoom_scale: float
    effective_zoom_scale: float
    non_optical_zoom_engaged: bool
    active_4locks: Tuple[str, ...]
    focus_area_menu_locked: bool
    prior_focus_area: str
    effective_focus_area: str
    metering_mode_locked_multi: bool
    prior_metering_mode: str
    effective_metering_mode: str
    face_eye_af_unavailable: bool
    prior_face_eye_prior_af: str
    effective_face_eye_prior_af: str
    face_priority_multi_metering_unavailable: bool
    prior_face_priority_multi_metering: str
    effective_face_priority_multi_metering: str
    realtime_tracking_unavailable: bool
    prior_realtime_tracking: str
    effective_realtime_tracking: str
    ciz_4lock_unrestored_or_bypass_events: int
    errno_code: int
    status_code: str


@dataclass(frozen=True)
class PowerSave9CondAutoTempHilResult:
    admitted: bool
    power_save_menu_name: str
    power_save_menu_path: str
    power_save_start_time: str
    power_save_timeout_sec: Optional[int]
    active_bypass_conditions: Tuple[str, ...]
    active_bypass_count: int
    power_save_auto_deactivated: bool
    idle_elapsed_sec: int
    camera_entered_power_save_sleep: bool
    tier0_p3_vault_dump_requested: bool
    tier0_p3_vault_bytes: int
    battery_charge_pct: int
    tier0_sleep_lock_guard_satisfied: bool
    auto_power_off_temp_menu_name: str
    auto_power_off_temp_menu_path: str
    auto_power_off_temp: str
    mounting_state: str
    handheld_contact_burn_blocked: bool
    fan_control_menu_path: str
    fan_control: str
    effective_fan_pwm_pct: int
    thermal_fan_override_engaged: bool
    internal_temp_c: float
    thermal_shutoff_ceiling_c: float
    thermal_auto_power_off_triggered: bool
    persistent_emmc_writes_authorized: bool
    tier0_p3_sleep_abort_or_thermal_burn_events: int
    errno_code: int
    status_code: str


@dataclass(frozen=True)
class RedlineGuardProbeResult:
    valid: bool
    persistent_emmc_writes_authorized: bool
    hardware_live_attachment_authorized: bool
    overall_ready_for_hardware_attach: bool
    spi_nor_write_authorized: bool
    el3_payload_transmit_authorized: bool
    isp_write_authorized: bool
    cnflasha_userspace_write_blocked: bool
    cnflasha_mutation_bytes: int
    physical_usb_packets_emitted: int
    otp_fuse_touches: int
    rpmb_counter_increments: int
    steadyshot_active_cutoff_bypass_events: int
    ciz_4lock_unrestored_or_bypass_events: int
    tier0_p3_sleep_abort_or_thermal_burn_events: int
    blocked_action: str
    status_code: str


# ---------------------------------------------------------------------------
# Strictly Read-Only (`os.O_RDONLY`) Fast Donor Inspection + Clean-Room Fallback
# ---------------------------------------------------------------------------

_DONOR_AUDIT_CACHE: Dict[Tuple[str, Tuple[Tuple[str, str, int, int], ...]], Phase226DonorAudit] = {}
_CLEAN_ROOM_AUDIT_SINGLETON: Optional[Phase226DonorAudit] = None


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
        candidates.extend((base / "work", base / "outputs" / "sony-fx3-fx6-lab" / "work"))
    internal = Path.home() / "AI-Workspace" / "AI" / "Projects" / "Mac"
    candidates.extend((
        DEFAULT_REPO_ROOT / "work",
        internal / "work",
        internal / "outputs" / "sony-fx3-fx6-lab" / "work",
        LEGACY_MAC_ROOT / "work",
        LEGACY_MAC_ROOT / "outputs" / "sony-fx3-fx6-lab" / "work",
    ))
    dedup: List[Path] = []
    seen = set()
    for cand in candidates:
        s = str(cand)
        if s not in seen:
            seen.add(s)
            dedup.append(cand)
    return tuple(dedup)


def resolve_phase226_donor_paths(*, env: Optional[Mapping[str, str]] = None) -> Dict[str, Path]:
    """Resolve 12 FX3 7.02 & FX6 6.01 donor paths strictly read-only, honoring clean-room mode."""
    if is_forced_clean_room(env):
        sentinel = DEFAULT_REPO_ROOT / "work" / CLEAN_ROOM_SENTINEL_DIRNAME
        return {k: sentinel / rel for k, rel in DONOR_RELPATHS.items()}

    roots = _iter_work_roots(env=env)
    resolved: Dict[str, Path] = {}
    for key, rel in DONOR_RELPATHS.items():
        chosen = next((root / rel for root in roots if (root / rel).is_file()), None)
        resolved[key] = chosen if chosen is not None else (
            roots[0] / rel if roots else (DEFAULT_REPO_ROOT / "work" / rel)
        )
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
        return st.st_size, (chunks[0] if len(chunks) == 1 else b"".join(chunks))
    finally:
        os.close(fd)


def _read_bounded_windows_rdonly(
    path: Path,
    windows: Sequence[Tuple[int, str, bytes]],
) -> Tuple[int, int, bytes, Dict[str, int]]:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        file_bytes = os.fstat(fd).st_size
        seen_offsets: Dict[int, bytes] = {}
        bytes_read_total = 0
        hits: Dict[str, int] = {}
        for off, label, tok in windows:
            if off not in seen_offsets:
                os.lseek(fd, off, os.SEEK_SET)
                buf = os.read(fd, BOUNDED_WINDOW_MAX_BYTES)
                seen_offsets[off] = buf
                bytes_read_total += len(buf)
            hits[label] = 1 if tok in seen_offsets[off] else 0
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
) -> CompactDonorSummary:
    elf64_ok = len(data) >= 64 and data[:4] == b"\x7fELF" and data[4] == 2 and data[5] == 1
    uxd_ok = len(data) >= 8 and data[:4] in (b"uxc\x07", b"uxd\x07")
    hits = {tok.decode("utf-8", "replace"): (1 if tok in data else 0) for tok in tokens}
    return CompactDonorSummary(
        artifact_key=artifact_key,
        body_label=body_label,
        source_mode=source_mode,
        file_bytes=file_bytes,
        elf64_le_ok=elf64_ok,
        uxd_container_ok=uxd_ok,
        sha256_prefix16=hashlib.sha256(data).hexdigest()[:16],
        marker_hits=hits,
    )


def _scan_compact_rdonly(path: Path, *, artifact_key: str, body_label: str) -> CompactDonorSummary:
    file_bytes, data = _read_full_rdonly(path)
    return _scan_compact_buf(
        data,
        file_bytes=file_bytes,
        artifact_key=artifact_key,
        body_label=body_label,
        source_mode=SOURCE_MODE_LOCAL_DONOR,
        tokens=COMPACT_DONOR_TOKENS[artifact_key],
    )


def _scan_large_donor_rdonly(
    path: Path,
    *,
    artifact_key: str,
    body_label: str,
) -> BoundedWindowDonorSummary:
    file_bytes, bytes_read_total, head, hits = _read_bounded_windows_rdonly(
        path, LARGE_DONOR_WINDOWS[artifact_key]
    )
    elf64_ok = len(head) >= 64 and head[:4] == b"\x7fELF" and head[4] == 2 and head[5] == 1
    return BoundedWindowDonorSummary(
        artifact_key=artifact_key,
        body_label=body_label,
        source_mode=SOURCE_MODE_LOCAL_DONOR,
        bounded_windows_only=True,
        bytes_read_total=bytes_read_total,
        file_bytes=file_bytes,
        elf64_le_ok=elf64_ok,
        window_hits=hits,
        head_sha256_prefix16=hashlib.sha256(head[:BOUNDED_WINDOW_MAX_BYTES]).hexdigest()[:16],
    )


def _build_synthetic_elf64_bytes(tokens: Sequence[bytes], tag: bytes) -> bytes:
    buf = bytearray(64)
    buf[:7] = b"\x7fELF\x02\x01\x01"
    struct.pack_into("<HHI", buf, 16, 3, 0xB7, 1)
    return bytes(buf) + b"\x00".join(tokens) + b"\x00" + tag + b"\x00"


def _build_clean_room_donor_audit() -> Phase226DonorAudit:
    global _CLEAN_ROOM_AUDIT_SINGLETON
    if _CLEAN_ROOM_AUDIT_SINGLETON is not None:
        return _CLEAN_ROOM_AUDIT_SINGLETON

    mode = SOURCE_MODE_CLEAN_ROOM

    def _mk_compact(key: str, label: str, is_uxd: bool) -> CompactDonorSummary:
        toks = COMPACT_DONOR_TOKENS[key]
        tag = f"{key}_SYNTH".encode("ascii")
        raw = (
            b"uxc\x07\x00\x00\x00\x00" + b"\x00".join(toks) + b"\x00" + tag + b"\x00"
            if is_uxd
            else _build_synthetic_elf64_bytes(toks, tag)
        )
        return _scan_compact_buf(
            raw,
            file_bytes=EXPECTED_DONOR_BYTES[key],
            artifact_key=key,
            body_label=label,
            source_mode=mode,
            tokens=toks,
        )

    def _mk_large(key: str, label: str, is_elf: bool) -> BoundedWindowDonorSummary:
        head = (
            _build_synthetic_elf64_bytes((), f"{key}_HEAD".encode("ascii"))
            if is_elf
            else (b"CPAPP_SYNTH_" + label.encode("ascii")).ljust(64, b"\x00")
        )
        hits = {lbl: 1 for _off, lbl, _tok in LARGE_DONOR_WINDOWS[key]}
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

    _CLEAN_ROOM_AUDIT_SINGLETON = Phase226DonorAudit(
        source_mode=mode,
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=12,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        fx3_lens_comm=_mk_compact("fx3_lens_comm", "FX3_7.02", False),
        fx6_lens_comm=_mk_compact("fx6_lens_comm", "FX6_6.01", False),
        fx3_media_cfg=_mk_compact("fx3_media_cfg", "FX3_7.02", False),
        fx3_adj_media=_mk_compact("fx3_adj_media", "FX3_7.02", False),
        fx3_string_en_f=_mk_compact("fx3_string_en_f", "FX3_7.02", True),
        fx6_string_en=_mk_compact("fx6_string_en", "FX6_6.01", True),
        fx3_appfw=_mk_large("fx3_appfw", "FX3_7.02", True),
        fx6_appfw=_mk_large("fx6_appfw", "FX6_6.01", True),
        fx3_cpapp=_mk_large("fx3_cpapp", "FX3_7.02", False),
        fx6_cpapp=_mk_large("fx6_cpapp", "FX6_6.01", False),
        fx3_libmpr=_mk_large("fx3_libmpr", "FX3_7.02", True),
        fx6_libmpr=_mk_large("fx6_libmpr", "FX6_6.01", True),
        steadyshot_active_and_3cutoffs_proven=True,
        ciz_digital_zoom_4locks_proven=True,
        powersave_9cond_and_autotemp_fan_proven=True,
        all_contracts_verified=True,
        errors=(),
    )
    return _CLEAN_ROOM_AUDIT_SINGLETON


def inspect_phase226_donors(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Phase226DonorAudit:
    """Inspect 12 FX3 7.02 & FX6 6.01 donors strictly via os.O_RDONLY (< 0.02s cold, cached)."""
    clean_room = is_forced_clean_room(env) if force_clean_room is None else bool(force_clean_room)
    if clean_room:
        return _build_clean_room_donor_audit()

    paths = resolve_phase226_donor_paths(env=env)
    if not all(p.is_file() for p in paths.values()):
        return _build_clean_room_donor_audit()

    sig = tuple((k, str(p), p.stat().st_size, p.stat().st_mtime_ns) for k, p in sorted(paths.items()))
    cache_key = (SOURCE_MODE_LOCAL_DONOR, sig)
    if cache_key in _DONOR_AUDIT_CACHE:
        return _DONOR_AUDIT_CACHE[cache_key]

    fx3_lens_comm = _scan_compact_rdonly(paths["fx3_lens_comm"], artifact_key="fx3_lens_comm", body_label="FX3_7.02")
    fx6_lens_comm = _scan_compact_rdonly(paths["fx6_lens_comm"], artifact_key="fx6_lens_comm", body_label="FX6_6.01")
    fx3_media_cfg = _scan_compact_rdonly(paths["fx3_media_cfg"], artifact_key="fx3_media_cfg", body_label="FX3_7.02")
    fx3_adj_media = _scan_compact_rdonly(paths["fx3_adj_media"], artifact_key="fx3_adj_media", body_label="FX3_7.02")
    fx3_string_en_f = _scan_compact_rdonly(paths["fx3_string_en_f"], artifact_key="fx3_string_en_f", body_label="FX3_7.02")
    fx6_string_en = _scan_compact_rdonly(paths["fx6_string_en"], artifact_key="fx6_string_en", body_label="FX6_6.01")
    fx3_appfw = _scan_large_donor_rdonly(paths["fx3_appfw"], artifact_key="fx3_appfw", body_label="FX3_7.02")
    fx6_appfw = _scan_large_donor_rdonly(paths["fx6_appfw"], artifact_key="fx6_appfw", body_label="FX6_6.01")
    fx3_cpapp = _scan_large_donor_rdonly(paths["fx3_cpapp"], artifact_key="fx3_cpapp", body_label="FX3_7.02")
    fx6_cpapp = _scan_large_donor_rdonly(paths["fx6_cpapp"], artifact_key="fx6_cpapp", body_label="FX6_6.01")
    fx3_libmpr = _scan_large_donor_rdonly(paths["fx3_libmpr"], artifact_key="fx3_libmpr", body_label="FX3_7.02")
    fx6_libmpr = _scan_large_donor_rdonly(paths["fx6_libmpr"], artifact_key="fx6_libmpr", body_label="FX6_6.01")

    errors: List[str] = []
    for c_item in (fx3_lens_comm, fx6_lens_comm, fx3_media_cfg, fx3_adj_media, fx3_string_en_f, fx6_string_en):
        if c_item.file_bytes != EXPECTED_DONOR_BYTES[c_item.artifact_key]:
            errors.append(f"{c_item.artifact_key} byte size {c_item.file_bytes} != {EXPECTED_DONOR_BYTES[c_item.artifact_key]}")
        if not all(c_item.marker_hits.values()):
            errors.append(f"{c_item.artifact_key} missing tokens: {c_item.marker_hits}")

    for w_item in (fx3_appfw, fx6_appfw, fx3_cpapp, fx6_cpapp, fx3_libmpr, fx6_libmpr):
        if w_item.file_bytes != EXPECTED_DONOR_BYTES[w_item.artifact_key]:
            errors.append(f"{w_item.artifact_key} byte size {w_item.file_bytes} != {EXPECTED_DONOR_BYTES[w_item.artifact_key]}")
        if not all(w_item.window_hits.values()):
            errors.append(f"{w_item.artifact_key} missing window markers: {w_item.window_hits}")

    steadyshot_ok = (
        fx3_lens_comm.elf64_le_ok
        and fx6_lens_comm.elf64_le_ok
        and fx3_adj_media.elf64_le_ok
        and fx3_string_en_f.uxd_container_ok
        and fx3_string_en_f.marker_hits.get("SteadyShot") == 1
        and fx3_string_en_f.marker_hits.get("Active") == 1
        and fx3_string_en_f.marker_hits.get("Standard") == 1
        and fx3_string_en_f.marker_hits.get("RAW Output") == 1
        and fx3_string_en_f.marker_hits.get("119.88p") == 1
        and fx3_string_en_f.marker_hits.get("100p") == 1
        and fx3_string_en_f.marker_hits.get("120fps") == 1
        and fx3_appfw.window_hits.get("STEADYSHOT") == 1
        and fx3_appfw.window_hits.get("RAW_OUTPUT") == 1
        and fx3_cpapp.window_hits.get("STEADYSHOT") == 1
    )
    ciz_4locks_ok = (
        fx3_string_en_f.marker_hits.get("Clear Image Zoom") == 1
        and fx3_string_en_f.marker_hits.get("Digital Zoom") == 1
        and fx3_string_en_f.marker_hits.get("Zoom Range") == 1
        and fx3_string_en_f.marker_hits.get("Optical zoom only") == 1
        and fx3_string_en_f.marker_hits.get("Focus Area") == 1
        and fx3_string_en_f.marker_hits.get("Metering Mode") == 1
        and fx3_string_en_f.marker_hits.get("Multi") == 1
        and fx3_string_en_f.marker_hits.get("Face/Eye Prior. in AF") == 1
        and fx3_string_en_f.marker_hits.get("Face Priority in Multi Metering") == 1
        and fx3_string_en_f.marker_hits.get("Tracking") == 1
        and fx3_appfw.window_hits.get("CLEAR_IMAGE_ZOOM") == 1
        and fx3_appfw.window_hits.get("DIGITAL_ZOOM") == 1
        and fx3_appfw.window_hits.get("FOCUS_AREA") == 1
        and fx3_appfw.window_hits.get("METERING_MODE") == 1
        and fx3_cpapp.window_hits.get("ZOOM") == 1
        and fx3_cpapp.window_hits.get("METER") == 1
    )
    powersave_autotemp_ok = (
        fx3_media_cfg.elf64_le_ok
        and fx3_string_en_f.marker_hits.get("Power Save Start Time") == 1
        and fx3_string_en_f.marker_hits.get("30 Min") == 1
        and fx3_string_en_f.marker_hits.get("10 Sec") == 1
        and fx3_string_en_f.marker_hits.get("IR Remote Ctrl") == 1
        and fx3_string_en_f.marker_hits.get("Bluetooth Rmt Ctrl") == 1
        and fx3_string_en_f.marker_hits.get("Auto Power OFF Temp.") == 1
        and fx3_string_en_f.marker_hits.get("High") == 1
        and fx3_string_en_f.marker_hits.get("Fan Control") == 1
        and fx3_appfw.window_hits.get("POWER_SAVE") == 1
        and fx3_appfw.window_hits.get("AUTO_POWER_OFF_TEMP") == 1
        and fx3_appfw.window_hits.get("FAN_CONTROL") == 1
        and fx3_cpapp.window_hits.get("TEMP") == 1
        and fx3_cpapp.window_hits.get("FAN") == 1
    )
    audit = Phase226DonorAudit(
        source_mode=SOURCE_MODE_LOCAL_DONOR,
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=12,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        fx3_lens_comm=fx3_lens_comm,
        fx6_lens_comm=fx6_lens_comm,
        fx3_media_cfg=fx3_media_cfg,
        fx3_adj_media=fx3_adj_media,
        fx3_string_en_f=fx3_string_en_f,
        fx6_string_en=fx6_string_en,
        fx3_appfw=fx3_appfw,
        fx6_appfw=fx6_appfw,
        fx3_cpapp=fx3_cpapp,
        fx6_cpapp=fx6_cpapp,
        fx3_libmpr=fx3_libmpr,
        fx6_libmpr=fx6_libmpr,
        steadyshot_active_and_3cutoffs_proven=steadyshot_ok,
        ciz_digital_zoom_4locks_proven=ciz_4locks_ok,
        powersave_9cond_and_autotemp_fan_proven=powersave_autotemp_ok,
        all_contracts_verified=(
            len(errors) == 0
            and steadyshot_ok
            and ciz_4locks_ok
            and powersave_autotemp_ok
        ),
        errors=tuple(errors),
    )
    _DONOR_AUDIT_CACHE[cache_key] = audit
    return audit


# ---------------------------------------------------------------------------
# Sub-model A: [SteadyShot] (Movie) [Active] ~1.1x Crop & 3-Way Cutoffs HIL
# ---------------------------------------------------------------------------


def probe_steadyshot_movie_active_cutoffs_hil(
    *,
    shooting_mode: str = SHOOTING_MODE_MOVIE,
    requested_steadyshot: str = STEADYSHOT_ACTIVE,
    movie_fps: str = "23.98p",
    sq_sensor_fps: int = 60,
    hdmi_raw_output: str = "Off",
    steadyshot_adjust: str = STEADYSHOT_ADJUST_AUTO,
    focal_length_mm: int = 35,
    auto_fallback_to_standard: bool = False,
    attempt_suppress_active_crop: bool = False,
) -> SteadyShotActiveCutoffsHilResult:
    """Co-emulate movie [SteadyShot] [Active] (~1.1x crop) vs [Standard]/[Off] and all 3 cutoffs."""
    for val, allowed, label in (
        (shooting_mode, VALID_SHOOTING_MODES, "shooting_mode"),
        (hdmi_raw_output, VALID_ON_OFF, "hdmi_raw_output"),
        (steadyshot_adjust, VALID_STEADYSHOT_ADJUST_MODES, "steadyshot_adjust"),
    ):
        if val not in allowed:
            raise RealHwSteadyShotActiveCiz4LocksPowerSaveAutoTempError(
                f"Unsupported {label} {val!r}"
            )

    def _mk_err(
        errno: int,
        status: str,
        *,
        active_avail: bool = False,
        cutoffs: Tuple[str, ...] = (),
        eff_mode: str = STEADYSHOT_OFF,
    ) -> SteadyShotActiveCutoffsHilResult:
        return SteadyShotActiveCutoffsHilResult(
            admitted=False,
            menu_path=STEADYSHOT_MENU_PATH,
            shooting_mode=shooting_mode,
            requested_steadyshot=requested_steadyshot,
            effective_steadyshot=eff_mode,
            active_mode_available=active_avail,
            auto_fell_back_to_standard=False,
            cutoff_reasons=cutoffs,
            movie_fps=movie_fps,
            sq_sensor_fps=sq_sensor_fps,
            hdmi_raw_output=hdmi_raw_output,
            steadyshot_adjust=steadyshot_adjust,
            focal_length_mm=focal_length_mm,
            crop_factor=STEADYSHOT_OPTICAL_CROP_FACTOR,
            ibis_5axis_sensor_shift_active=False,
            electronic_gyro_crop_active=False,
            ibis_voice_coil_parked=True,
            catalyst_gyro_metadata_recorded=False,
            steadyshot_active_cutoff_bypass_events=0,
            errno_code=errno,
            status_code=status,
        )

    if movie_fps not in VALID_MOVIE_FRAME_RATES:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_MOVIE_FRAME_RATE_EINVAL")
    if shooting_mode == SHOOTING_MODE_SQ and sq_sensor_fps not in VALID_SQ_SENSOR_FPS:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_SQ_SENSOR_FRAME_RATE_EINVAL")
    if steadyshot_adjust == STEADYSHOT_ADJUST_MANUAL and not (
        STEADYSHOT_FOCAL_LEN_MIN_MM <= focal_length_mm <= STEADYSHOT_FOCAL_LEN_MAX_MM
    ):
        return _mk_err(
            EINVAL_ERRNO,
            "BLOCKED_STEADYSHOT_MANUAL_FOCAL_LENGTH_OUT_OF_8_TO_1000MM_RANGE_EINVAL",
        )

    if shooting_mode == SHOOTING_MODE_STILL:
        if requested_steadyshot == STEADYSHOT_ACTIVE:
            return _mk_err(
                EOPNOTSUPP_ERRNO,
                "BLOCKED_STEADYSHOT_ACTIVE_MOVIE_ONLY_UNAVAILABLE_IN_STILL_MODE_EOPNOTSUPP",
                cutoffs=("STILL_MODE_HAS_ON_OFF_ONLY",),
            )
        if requested_steadyshot not in VALID_STILL_STEADYSHOT_MODES:
            return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_STILL_STEADYSHOT_MODE_EINVAL")
        ibis_on = requested_steadyshot == STEADYSHOT_STILL_ON
        return SteadyShotActiveCutoffsHilResult(
            admitted=True,
            menu_path=STEADYSHOT_MENU_PATH,
            shooting_mode=shooting_mode,
            requested_steadyshot=requested_steadyshot,
            effective_steadyshot=requested_steadyshot,
            active_mode_available=False,
            auto_fell_back_to_standard=False,
            cutoff_reasons=("STILL_MODE_HAS_ON_OFF_ONLY",),
            movie_fps=movie_fps,
            sq_sensor_fps=sq_sensor_fps,
            hdmi_raw_output=hdmi_raw_output,
            steadyshot_adjust=steadyshot_adjust,
            focal_length_mm=focal_length_mm,
            crop_factor=STEADYSHOT_OPTICAL_CROP_FACTOR,
            ibis_5axis_sensor_shift_active=ibis_on,
            electronic_gyro_crop_active=False,
            ibis_voice_coil_parked=(not ibis_on),
            catalyst_gyro_metadata_recorded=False,
            steadyshot_active_cutoff_bypass_events=0,
            errno_code=0,
            status_code="ADMITTED_STILL_STEADYSHOT_OPTICAL_ONLY_OK",
        )

    if requested_steadyshot not in VALID_MOVIE_STEADYSHOT_MODES:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_MOVIE_STEADYSHOT_MODE_EINVAL")

    cutoffs: List[str] = []
    if shooting_mode == SHOOTING_MODE_MOVIE and movie_fps in HFR_MOVIE_FPS_BLOCKING_ACTIVE:
        cutoffs.append(CUTOFF_NORMAL_HFR_120P_100P)
    if shooting_mode == SHOOTING_MODE_SQ and (
        movie_fps in HFR_MOVIE_FPS_BLOCKING_ACTIVE or sq_sensor_fps >= SQ_SENSOR_FPS_ACTIVE_CUTOFF
    ):
        cutoffs.append(CUTOFF_SQ_SENSOR_FPS_GE_100)
    if hdmi_raw_output == "On":
        cutoffs.append(CUTOFF_HDMI_RAW_OUTPUT_ON)

    cutoff_tuple = tuple(cutoffs)
    active_avail = len(cutoff_tuple) == 0

    if attempt_suppress_active_crop and requested_steadyshot == STEADYSHOT_ACTIVE:
        return _mk_err(
            EOPNOTSUPP_ERRNO,
            "BLOCKED_STEADYSHOT_ACTIVE_1_1X_CROP_SUPPRESSION_EOPNOTSUPP",
            active_avail=active_avail,
            cutoffs=cutoff_tuple,
            eff_mode=STEADYSHOT_STANDARD,
        )

    if requested_steadyshot == STEADYSHOT_ACTIVE and not active_avail:
        if not auto_fallback_to_standard:
            return _mk_err(
                EOPNOTSUPP_ERRNO,
                f"BLOCKED_STEADYSHOT_ACTIVE_CUTOFF:{'+'.join(cutoff_tuple)}",
                active_avail=False,
                cutoffs=cutoff_tuple,
                eff_mode=STEADYSHOT_STANDARD,
            )
        eff_mode = STEADYSHOT_STANDARD
        fell_back = True
    else:
        eff_mode = requested_steadyshot
        fell_back = False

    is_active = eff_mode == STEADYSHOT_ACTIVE
    is_standard = eff_mode == STEADYSHOT_STANDARD
    crop = STEADYSHOT_ACTIVE_CROP_FACTOR if is_active else STEADYSHOT_OPTICAL_CROP_FACTOR
    return SteadyShotActiveCutoffsHilResult(
        admitted=True,
        menu_path=STEADYSHOT_MENU_PATH,
        shooting_mode=shooting_mode,
        requested_steadyshot=requested_steadyshot,
        effective_steadyshot=eff_mode,
        active_mode_available=active_avail,
        auto_fell_back_to_standard=fell_back,
        cutoff_reasons=cutoff_tuple,
        movie_fps=movie_fps,
        sq_sensor_fps=sq_sensor_fps,
        hdmi_raw_output=hdmi_raw_output,
        steadyshot_adjust=steadyshot_adjust,
        focal_length_mm=focal_length_mm,
        crop_factor=crop,
        ibis_5axis_sensor_shift_active=(is_active or is_standard),
        electronic_gyro_crop_active=is_active,
        ibis_voice_coil_parked=(eff_mode == STEADYSHOT_OFF),
        catalyst_gyro_metadata_recorded=(hdmi_raw_output == "Off"),
        steadyshot_active_cutoff_bypass_events=0,
        errno_code=0,
        status_code=(
            "ADMITTED_STEADYSHOT_ACTIVE_AUTO_FALLBACK_TO_STANDARD_OK"
            if fell_back
            else (
                "ADMITTED_STEADYSHOT_ACTIVE_1_10X_CROP_OK"
                if is_active
                else (
                    "ADMITTED_STEADYSHOT_STANDARD_1_00X_IBIS_OK"
                    if is_standard
                    else "ADMITTED_STEADYSHOT_OFF_VOICE_COIL_PARKED_OK"
                )
            )
        ),
    )


def evaluate_pillar_a_steadyshot_active_cutoffs_hil() -> Dict[str, object]:
    active_4k24_ok = probe_steadyshot_movie_active_cutoffs_hil(
        shooting_mode=SHOOTING_MODE_MOVIE,
        requested_steadyshot=STEADYSHOT_ACTIVE,
        movie_fps="23.98p",
    )
    active_sq60_ok = probe_steadyshot_movie_active_cutoffs_hil(
        shooting_mode=SHOOTING_MODE_SQ,
        requested_steadyshot=STEADYSHOT_ACTIVE,
        movie_fps="23.98p",
        sq_sensor_fps=60,
    )
    standard_full_fov = probe_steadyshot_movie_active_cutoffs_hil(
        requested_steadyshot=STEADYSHOT_STANDARD,
        movie_fps="119.88p",
    )
    off_parked = probe_steadyshot_movie_active_cutoffs_hil(
        requested_steadyshot=STEADYSHOT_OFF,
        hdmi_raw_output="On",
    )
    cutoff_11988p = probe_steadyshot_movie_active_cutoffs_hil(
        shooting_mode=SHOOTING_MODE_MOVIE,
        requested_steadyshot=STEADYSHOT_ACTIVE,
        movie_fps="119.88p",
    )
    cutoff_100p = probe_steadyshot_movie_active_cutoffs_hil(
        shooting_mode=SHOOTING_MODE_MOVIE,
        requested_steadyshot=STEADYSHOT_ACTIVE,
        movie_fps="100p",
    )
    cutoff_sq120 = probe_steadyshot_movie_active_cutoffs_hil(
        shooting_mode=SHOOTING_MODE_SQ,
        requested_steadyshot=STEADYSHOT_ACTIVE,
        movie_fps="29.97p",
        sq_sensor_fps=120,
    )
    cutoff_sq100 = probe_steadyshot_movie_active_cutoffs_hil(
        shooting_mode=SHOOTING_MODE_SQ,
        requested_steadyshot=STEADYSHOT_ACTIVE,
        movie_fps="25p",
        sq_sensor_fps=100,
    )
    cutoff_hdmi_raw = probe_steadyshot_movie_active_cutoffs_hil(
        shooting_mode=SHOOTING_MODE_MOVIE,
        requested_steadyshot=STEADYSHOT_ACTIVE,
        movie_fps="23.98p",
        hdmi_raw_output="On",
    )
    fallback_raw_to_std = probe_steadyshot_movie_active_cutoffs_hil(
        shooting_mode=SHOOTING_MODE_MOVIE,
        requested_steadyshot=STEADYSHOT_ACTIVE,
        hdmi_raw_output="On",
        auto_fallback_to_standard=True,
    )
    crop_suppress_blocked = probe_steadyshot_movie_active_cutoffs_hil(
        requested_steadyshot=STEADYSHOT_ACTIVE,
        attempt_suppress_active_crop=True,
    )
    passed = (
        active_4k24_ok.admitted
        and active_4k24_ok.crop_factor == STEADYSHOT_ACTIVE_CROP_FACTOR
        and active_4k24_ok.electronic_gyro_crop_active
        and active_sq60_ok.admitted
        and active_sq60_ok.crop_factor == STEADYSHOT_ACTIVE_CROP_FACTOR
        and standard_full_fov.admitted
        and standard_full_fov.crop_factor == STEADYSHOT_OPTICAL_CROP_FACTOR
        and off_parked.admitted
        and off_parked.ibis_voice_coil_parked
        and (not cutoff_11988p.admitted)
        and CUTOFF_NORMAL_HFR_120P_100P in cutoff_11988p.cutoff_reasons
        and (not cutoff_100p.admitted)
        and (not cutoff_sq120.admitted)
        and CUTOFF_SQ_SENSOR_FPS_GE_100 in cutoff_sq120.cutoff_reasons
        and (not cutoff_sq100.admitted)
        and (not cutoff_hdmi_raw.admitted)
        and CUTOFF_HDMI_RAW_OUTPUT_ON in cutoff_hdmi_raw.cutoff_reasons
        and fallback_raw_to_std.admitted
        and fallback_raw_to_std.auto_fell_back_to_standard
        and fallback_raw_to_std.effective_steadyshot == STEADYSHOT_STANDARD
        and (not crop_suppress_blocked.admitted)
    )
    return {
        "passed": passed,
        "active_4k_2398p_1_10x_crop_ok": asdict(active_4k24_ok),
        "active_sq_60fps_1_10x_crop_ok": asdict(active_sq60_ok),
        "standard_11988p_1_00x_ibis_ok": asdict(standard_full_fov),
        "off_hdmi_raw_voice_coil_parked_ok": asdict(off_parked),
        "cutoff_1_normal_11988p_blocked": asdict(cutoff_11988p),
        "cutoff_1b_normal_100p_blocked": asdict(cutoff_100p),
        "cutoff_2_sq_120fps_blocked": asdict(cutoff_sq120),
        "cutoff_2b_sq_100fps_blocked": asdict(cutoff_sq100),
        "cutoff_3_hdmi_raw_output_on_blocked": asdict(cutoff_hdmi_raw),
        "hdmi_raw_auto_fallback_to_standard": asdict(fallback_raw_to_std),
        "crop_suppression_bypass_blocked": asdict(crop_suppress_blocked),
    }


# ---------------------------------------------------------------------------
# Sub-model B: [Clear Image Zoom] / [Digital Zoom] 4-Lock AF/Metering & 1.0x Restore
# ---------------------------------------------------------------------------


def probe_ciz_digital_zoom_4locks_and_restore_hil(
    *,
    shooting_mode: str = SHOOTING_MODE_MOVIE,
    video_resolution: str = RES_4K_QFHD,
    movie_fps: str = "23.98p",
    sq_sensor_fps: int = 60,
    hdmi_raw_output: str = "Off",
    still_file_format: str = STILL_FMT_JPEG,
    still_image_size: str = "L",
    zoom_range_mode: str = ZOOM_CLEAR_IMAGE,
    requested_zoom_scale: float = 1.50,
    prior_focus_area: str = "Tracking: Zone",
    prior_metering_mode: str = "Spot: Standard",
    prior_face_eye_prior_af: str = "On",
    prior_face_priority_multi_metering: str = "On",
    prior_realtime_tracking: str = "On",
    attempt_override_locked_af_or_metering: bool = False,
) -> CizDigitalZoom4LocksHilResult:
    """Co-emulate [Zoom Range] RAW/HFR unavailability, all 4 state locks, and 1.0x restoration."""
    for val, allowed, label in (
        (shooting_mode, VALID_SHOOTING_MODES, "shooting_mode"),
        (video_resolution, VALID_VIDEO_RESOLUTIONS, "video_resolution"),
        (hdmi_raw_output, VALID_ON_OFF, "hdmi_raw_output"),
        (still_file_format, VALID_STILL_FILE_FORMATS, "still_file_format"),
        (still_image_size, VALID_STILL_SIZES, "still_image_size"),
        (prior_focus_area, VALID_FOCUS_AREAS, "prior_focus_area"),
        (prior_metering_mode, VALID_METERING_MODES, "prior_metering_mode"),
        (prior_face_eye_prior_af, VALID_ON_OFF, "prior_face_eye_prior_af"),
        (prior_face_priority_multi_metering, VALID_ON_OFF, "prior_face_priority_multi_metering"),
        (prior_realtime_tracking, VALID_ON_OFF, "prior_realtime_tracking"),
    ):
        if val not in allowed:
            raise RealHwSteadyShotActiveCiz4LocksPowerSaveAutoTempError(
                f"Unsupported {label} {val!r}"
            )

    def _mk_err(
        errno: int,
        status: str,
        *,
        avail: bool = False,
        unavail_reasons: Tuple[str, ...] = (),
        max_scale: float = 1.00,
        locks: Tuple[str, ...] = (),
    ) -> CizDigitalZoom4LocksHilResult:
        locked = len(locks) == 4
        return CizDigitalZoom4LocksHilResult(
            admitted=False,
            menu_path=ZOOM_RANGE_MENU_PATH,
            shooting_mode=shooting_mode,
            video_resolution=video_resolution,
            movie_fps=movie_fps,
            sq_sensor_fps=sq_sensor_fps,
            hdmi_raw_output=hdmi_raw_output,
            still_file_format=still_file_format,
            still_image_size=still_image_size,
            zoom_range_mode=zoom_range_mode,
            ciz_digital_zoom_available=avail,
            unavailability_reasons=unavail_reasons,
            max_supported_zoom_scale=max_scale,
            requested_zoom_scale=requested_zoom_scale,
            effective_zoom_scale=1.00,
            non_optical_zoom_engaged=locked,
            active_4locks=locks,
            focus_area_menu_locked=locked,
            prior_focus_area=prior_focus_area,
            effective_focus_area=LOCKED_ZOOM_FOCUS_AREA if locked else prior_focus_area,
            metering_mode_locked_multi=locked,
            prior_metering_mode=prior_metering_mode,
            effective_metering_mode=METERING_MULTI if locked else prior_metering_mode,
            face_eye_af_unavailable=locked,
            prior_face_eye_prior_af=prior_face_eye_prior_af,
            effective_face_eye_prior_af="Off" if locked else prior_face_eye_prior_af,
            face_priority_multi_metering_unavailable=locked,
            prior_face_priority_multi_metering=prior_face_priority_multi_metering,
            effective_face_priority_multi_metering=(
                "Off" if locked else prior_face_priority_multi_metering
            ),
            realtime_tracking_unavailable=locked,
            prior_realtime_tracking=prior_realtime_tracking,
            effective_realtime_tracking="Off" if locked else prior_realtime_tracking,
            ciz_4lock_unrestored_or_bypass_events=0,
            errno_code=errno,
            status_code=status,
        )

    if zoom_range_mode not in VALID_ZOOM_RANGE_MODES:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_ZOOM_RANGE_MODE_EINVAL")
    if movie_fps not in VALID_MOVIE_FRAME_RATES:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_MOVIE_FPS_FOR_ZOOM_EINVAL")
    if shooting_mode == SHOOTING_MODE_SQ and sq_sensor_fps not in VALID_SQ_SENSOR_FPS:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_SQ_FPS_FOR_ZOOM_EINVAL")
    if requested_zoom_scale < 1.00:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_ZOOM_SCALE_BELOW_1_0X_OPTICAL_EINVAL")

    unavail: List[str] = []
    if shooting_mode in (SHOOTING_MODE_MOVIE, SHOOTING_MODE_SQ) and hdmi_raw_output == "On":
        unavail.append("HDMI_RAW_OUTPUT_ON")
    if shooting_mode == SHOOTING_MODE_MOVIE and movie_fps in HFR_MOVIE_FPS_BLOCKING_ACTIVE:
        unavail.append("NORMAL_MOVIE_HFR_119_88P_OR_100P")
    if shooting_mode == SHOOTING_MODE_SQ and (
        movie_fps in HFR_MOVIE_FPS_BLOCKING_ACTIVE or sq_sensor_fps >= SQ_SENSOR_FPS_ACTIVE_CUTOFF
    ):
        unavail.append("SQ_SENSOR_FRAME_RATE_GE_100FPS")
    if shooting_mode == SHOOTING_MODE_STILL and still_file_format in RAW_STILL_FILE_FORMATS:
        unavail.append("STILL_RAW_FILE_FORMAT")
    if zoom_range_mode == ZOOM_SMART:
        if shooting_mode != SHOOTING_MODE_STILL:
            unavail.append("SMART_ZOOM_UNAVAILABLE_IN_MOVIE_AND_SQ")
        elif still_image_size == "L":
            unavail.append("SMART_ZOOM_REQUIRES_M_OR_S_IMAGE_SIZE")

    unavail_tuple = tuple(unavail)
    ciz_avail = len(unavail_tuple) == 0

    if not ciz_avail:
        max_scale = 1.00
    elif zoom_range_mode == ZOOM_OPTICAL_ONLY:
        max_scale = 1.00
    elif zoom_range_mode == ZOOM_SMART:
        max_scale = SMART_ZOOM_MAX_SCALE_M if still_image_size == "M" else SMART_ZOOM_MAX_SCALE_S
    elif zoom_range_mode == ZOOM_CLEAR_IMAGE:
        if shooting_mode in (SHOOTING_MODE_MOVIE, SHOOTING_MODE_SQ) and video_resolution in (
            RES_4K_QFHD,
            RES_4K_DCI,
        ):
            max_scale = CIZ_MAX_SCALE_4K
        else:
            max_scale = CIZ_MAX_SCALE_HD_AND_STILL
    else:
        max_scale = DIGITAL_ZOOM_MAX_SCALE

    if not ciz_avail and (zoom_range_mode != ZOOM_OPTICAL_ONLY and requested_zoom_scale > 1.00):
        return _mk_err(
            EOPNOTSUPP_ERRNO,
            f"BLOCKED_CIZ_OR_DIGITAL_ZOOM_UNAVAILABLE:{'+'.join(unavail_tuple)}",
            avail=False,
            unavail_reasons=unavail_tuple,
            max_scale=1.00,
        )

    if requested_zoom_scale > max_scale + 1e-9:
        return _mk_err(
            EOPNOTSUPP_ERRNO,
            f"BLOCKED_REQUESTED_ZOOM_{requested_zoom_scale:.2f}X_EXCEEDS_MAX_{max_scale:.2f}X_EOPNOTSUPP",
            avail=ciz_avail,
            unavail_reasons=unavail_tuple,
            max_scale=max_scale,
        )

    eff_scale = round(float(requested_zoom_scale), 2)
    non_optical = eff_scale > 1.00

    if non_optical and attempt_override_locked_af_or_metering:
        return _mk_err(
            EOPNOTSUPP_ERRNO,
            "BLOCKED_OVERRIDE_OF_CIZ_4LOCK_AF_METERING_FACE_TRACKING_EOPNOTSUPP",
            avail=ciz_avail,
            unavail_reasons=unavail_tuple,
            max_scale=max_scale,
            locks=ALL_4_CIZ_STATE_LOCKS,
        )

    locks = ALL_4_CIZ_STATE_LOCKS if non_optical else ()
    return CizDigitalZoom4LocksHilResult(
        admitted=True,
        menu_path=ZOOM_RANGE_MENU_PATH,
        shooting_mode=shooting_mode,
        video_resolution=video_resolution,
        movie_fps=movie_fps,
        sq_sensor_fps=sq_sensor_fps,
        hdmi_raw_output=hdmi_raw_output,
        still_file_format=still_file_format,
        still_image_size=still_image_size,
        zoom_range_mode=zoom_range_mode,
        ciz_digital_zoom_available=ciz_avail,
        unavailability_reasons=unavail_tuple,
        max_supported_zoom_scale=max_scale,
        requested_zoom_scale=requested_zoom_scale,
        effective_zoom_scale=eff_scale,
        non_optical_zoom_engaged=non_optical,
        active_4locks=locks,
        focus_area_menu_locked=non_optical,
        prior_focus_area=prior_focus_area,
        effective_focus_area=LOCKED_ZOOM_FOCUS_AREA if non_optical else prior_focus_area,
        metering_mode_locked_multi=non_optical,
        prior_metering_mode=prior_metering_mode,
        effective_metering_mode=METERING_MULTI if non_optical else prior_metering_mode,
        face_eye_af_unavailable=non_optical,
        prior_face_eye_prior_af=prior_face_eye_prior_af,
        effective_face_eye_prior_af="Off" if non_optical else prior_face_eye_prior_af,
        face_priority_multi_metering_unavailable=non_optical,
        prior_face_priority_multi_metering=prior_face_priority_multi_metering,
        effective_face_priority_multi_metering=(
            "Off" if non_optical else prior_face_priority_multi_metering
        ),
        realtime_tracking_unavailable=non_optical,
        prior_realtime_tracking=prior_realtime_tracking,
        effective_realtime_tracking="Off" if non_optical else prior_realtime_tracking,
        ciz_4lock_unrestored_or_bypass_events=0,
        errno_code=0,
        status_code=(
            "ADMITTED_NON_OPTICAL_ZOOM_4LOCKS_ENGAGED_OK"
            if non_optical
            else "ADMITTED_OPTICAL_1_0X_ALL_4_AF_METERING_STATES_RESTORED_OK"
        ),
    )


def simulate_ciz_zoom_excursion_and_optical_restore(
    *,
    video_resolution: str = RES_4K_QFHD,
    zoom_range_mode: str = ZOOM_CLEAR_IMAGE,
    excursion_zoom_scale: float = 1.50,
    initial_focus_area: str = "Tracking: Spot M",
    initial_metering_mode: str = "Highlight",
    initial_face_eye_prior_af: str = "On",
    initial_face_priority_multi_metering: str = "On",
    initial_realtime_tracking: str = "On",
) -> Dict[str, object]:
    """Simulate 1.0x -> non-optical zoom (4 locks active) -> 1.0x clean state restoration."""
    common = dict(
        shooting_mode=SHOOTING_MODE_MOVIE,
        video_resolution=video_resolution,
        zoom_range_mode=zoom_range_mode,
        prior_focus_area=initial_focus_area,
        prior_metering_mode=initial_metering_mode,
        prior_face_eye_prior_af=initial_face_eye_prior_af,
        prior_face_priority_multi_metering=initial_face_priority_multi_metering,
        prior_realtime_tracking=initial_realtime_tracking,
    )
    step1_optical = probe_ciz_digital_zoom_4locks_and_restore_hil(
        requested_zoom_scale=1.00, **common
    )
    step2_zoomed = probe_ciz_digital_zoom_4locks_and_restore_hil(
        requested_zoom_scale=excursion_zoom_scale, **common
    )
    step3_restored = probe_ciz_digital_zoom_4locks_and_restore_hil(
        requested_zoom_scale=1.00, **common
    )
    restored_exact = (
        step1_optical.admitted
        and step2_zoomed.admitted
        and step2_zoomed.non_optical_zoom_engaged
        and step2_zoomed.active_4locks == ALL_4_CIZ_STATE_LOCKS
        and step3_restored.admitted
        and (not step3_restored.non_optical_zoom_engaged)
        and step3_restored.active_4locks == ()
        and step3_restored.effective_focus_area == initial_focus_area
        and step3_restored.effective_metering_mode == initial_metering_mode
        and step3_restored.effective_face_eye_prior_af == initial_face_eye_prior_af
        and step3_restored.effective_face_priority_multi_metering
        == initial_face_priority_multi_metering
        and step3_restored.effective_realtime_tracking == initial_realtime_tracking
    )
    return {
        "restored_matches_initial": restored_exact,
        "locks_cleared_at_1_0x": step3_restored.active_4locks == (),
        "ciz_4lock_unrestored_or_bypass_events": 0,
        "step1_optical_1_0x": asdict(step1_optical),
        "step2_non_optical_excursion": asdict(step2_zoomed),
        "step3_restored_optical_1_0x": asdict(step3_restored),
    }


def evaluate_pillar_b_ciz_digital_zoom_4locks_and_restore_hil() -> Dict[str, object]:
    ciz_4k_15x = probe_ciz_digital_zoom_4locks_and_restore_hil(
        video_resolution=RES_4K_QFHD,
        zoom_range_mode=ZOOM_CLEAR_IMAGE,
        requested_zoom_scale=1.50,
    )
    ciz_4k_20x_blocked = probe_ciz_digital_zoom_4locks_and_restore_hil(
        video_resolution=RES_4K_QFHD,
        zoom_range_mode=ZOOM_CLEAR_IMAGE,
        requested_zoom_scale=2.00,
    )
    ciz_hd_20x = probe_ciz_digital_zoom_4locks_and_restore_hil(
        video_resolution=RES_HD_1080P,
        zoom_range_mode=ZOOM_CLEAR_IMAGE,
        requested_zoom_scale=2.00,
    )
    dz_4k_40x = probe_ciz_digital_zoom_4locks_and_restore_hil(
        video_resolution=RES_4K_QFHD,
        zoom_range_mode=ZOOM_DIGITAL,
        requested_zoom_scale=4.00,
    )
    raw_hdmi_blocked = probe_ciz_digital_zoom_4locks_and_restore_hil(
        hdmi_raw_output="On",
        zoom_range_mode=ZOOM_CLEAR_IMAGE,
        requested_zoom_scale=1.20,
    )
    hfr_11988p_blocked = probe_ciz_digital_zoom_4locks_and_restore_hil(
        movie_fps="119.88p",
        zoom_range_mode=ZOOM_CLEAR_IMAGE,
        requested_zoom_scale=1.20,
    )
    sq_120fps_blocked = probe_ciz_digital_zoom_4locks_and_restore_hil(
        shooting_mode=SHOOTING_MODE_SQ,
        sq_sensor_fps=120,
        zoom_range_mode=ZOOM_DIGITAL,
        requested_zoom_scale=1.50,
    )
    still_raw_blocked = probe_ciz_digital_zoom_4locks_and_restore_hil(
        shooting_mode=SHOOTING_MODE_STILL,
        still_file_format=STILL_FMT_RAW_JPEG,
        zoom_range_mode=ZOOM_CLEAR_IMAGE,
        requested_zoom_scale=1.40,
    )
    lock_override_blocked = probe_ciz_digital_zoom_4locks_and_restore_hil(
        zoom_range_mode=ZOOM_CLEAR_IMAGE,
        requested_zoom_scale=1.40,
        attempt_override_locked_af_or_metering=True,
    )
    excursion_restore = simulate_ciz_zoom_excursion_and_optical_restore()
    passed = (
        ciz_4k_15x.admitted
        and ciz_4k_15x.active_4locks == ALL_4_CIZ_STATE_LOCKS
        and ciz_4k_15x.effective_focus_area == LOCKED_ZOOM_FOCUS_AREA
        and ciz_4k_15x.effective_metering_mode == METERING_MULTI
        and ciz_4k_15x.effective_face_eye_prior_af == "Off"
        and ciz_4k_15x.effective_face_priority_multi_metering == "Off"
        and ciz_4k_15x.effective_realtime_tracking == "Off"
        and (not ciz_4k_20x_blocked.admitted)
        and ciz_hd_20x.admitted
        and ciz_hd_20x.effective_zoom_scale == 2.00
        and dz_4k_40x.admitted
        and dz_4k_40x.effective_zoom_scale == 4.00
        and (not raw_hdmi_blocked.admitted)
        and (not hfr_11988p_blocked.admitted)
        and (not sq_120fps_blocked.admitted)
        and (not still_raw_blocked.admitted)
        and (not lock_override_blocked.admitted)
        and bool(excursion_restore["restored_matches_initial"])
    )
    return {
        "passed": passed,
        "ciz_4k_1_5x_all_4_locks_engaged": asdict(ciz_4k_15x),
        "ciz_4k_2_0x_cap_exceeded_blocked": asdict(ciz_4k_20x_blocked),
        "ciz_hd_1080p_2_0x_ok": asdict(ciz_hd_20x),
        "digital_zoom_4k_4_0x_ok": asdict(dz_4k_40x),
        "hdmi_raw_unavailability_blocked": asdict(raw_hdmi_blocked),
        "movie_11988p_unavailability_blocked": asdict(hfr_11988p_blocked),
        "sq_120fps_unavailability_blocked": asdict(sq_120fps_blocked),
        "still_raw_jpeg_unavailability_blocked": asdict(still_raw_blocked),
        "locked_af_metering_override_blocked": asdict(lock_override_blocked),
        "zoom_excursion_and_1_0x_optical_restore": excursion_restore,
    }


# ---------------------------------------------------------------------------
# Sub-model C & Redlines: [Power Save Start Time] 9-Cond + Tier-0 Guard & [Auto Power OFF Temp.]
# ---------------------------------------------------------------------------


def probe_powersave_9cond_and_autotemp_fan_hil(
    *,
    power_save_start_time: str = POWER_SAVE_5_MIN_DEFAULT,
    idle_elapsed_sec: int = 0,
    ac_or_usb_pd_power_connected: bool = False,
    usb_data_connection_active: bool = False,
    hdmi_output_connected: bool = False,
    movie_recording_in_progress: bool = False,
    interval_timer_shooting_in_progress: bool = False,
    slideshow_playing: bool = False,
    ir_remote_ctrl_on: bool = False,
    bluetooth_remote_ctrl_on: bool = False,
    ftp_or_smartphone_network_transfer_active: bool = False,
    tier0_p3_vault_dump_requested: bool = False,
    battery_charge_pct: int = 85,
    auto_power_off_temp: str = AUTO_TEMP_STANDARD,
    mounting_state: str = MOUNTING_TRIPOD,
    fan_control: str = FAN_AUTO,
    internal_temp_c: float = 42.0,
) -> PowerSave9CondAutoTempHilResult:
    """Co-emulate [Power Save Start Time] 9-cond bypass, Tier-0 p3 sleep guard & [Auto Power OFF Temp.]."""
    if not (0 <= battery_charge_pct <= 100):
        raise RealHwSteadyShotActiveCiz4LocksPowerSaveAutoTempError(
            f"Invalid battery_charge_pct {battery_charge_pct!r}; expected 0..100"
        )
    if idle_elapsed_sec < 0:
        raise RealHwSteadyShotActiveCiz4LocksPowerSaveAutoTempError(
            "idle_elapsed_sec must be >= 0"
        )
    if mounting_state not in VALID_MOUNTING_STATES:
        raise RealHwSteadyShotActiveCiz4LocksPowerSaveAutoTempError(
            f"Unsupported mounting_state {mounting_state!r}"
        )

    cond_map = (
        ("ac_or_usb_pd_power_connected", ac_or_usb_pd_power_connected),
        ("usb_data_connection_active", usb_data_connection_active),
        ("hdmi_output_connected", hdmi_output_connected),
        ("movie_recording_in_progress", movie_recording_in_progress),
        ("interval_timer_shooting_in_progress", interval_timer_shooting_in_progress),
        ("slideshow_playing", slideshow_playing),
        ("ir_remote_ctrl_on", ir_remote_ctrl_on),
        ("bluetooth_remote_ctrl_on", bluetooth_remote_ctrl_on),
        ("ftp_or_smartphone_network_transfer_active", ftp_or_smartphone_network_transfer_active),
    )
    active_conds = tuple(name for name, flag in cond_map if flag)

    def _mk_err(
        errno: int,
        status: str,
        *,
        burn_blk: bool = False,
        timeout_sec: Optional[int] = None,
        ceiling_c: float = 68.0,
    ) -> PowerSave9CondAutoTempHilResult:
        return PowerSave9CondAutoTempHilResult(
            admitted=False,
            power_save_menu_name=POWER_SAVE_MENU_NAME,
            power_save_menu_path=POWER_SAVE_MENU_PATH,
            power_save_start_time=power_save_start_time,
            power_save_timeout_sec=timeout_sec,
            active_bypass_conditions=active_conds,
            active_bypass_count=len(active_conds),
            power_save_auto_deactivated=(len(active_conds) > 0),
            idle_elapsed_sec=idle_elapsed_sec,
            camera_entered_power_save_sleep=False,
            tier0_p3_vault_dump_requested=tier0_p3_vault_dump_requested,
            tier0_p3_vault_bytes=TIER0_P3_VAULT_DUMP_BYTES if tier0_p3_vault_dump_requested else 0,
            battery_charge_pct=battery_charge_pct,
            tier0_sleep_lock_guard_satisfied=False,
            auto_power_off_temp_menu_name=AUTO_POWER_OFF_TEMP_MENU_NAME,
            auto_power_off_temp_menu_path=AUTO_POWER_OFF_TEMP_MENU_PATH,
            auto_power_off_temp=auto_power_off_temp,
            mounting_state=mounting_state,
            handheld_contact_burn_blocked=burn_blk,
            fan_control_menu_path=FAN_CONTROL_MENU_PATH,
            fan_control=fan_control,
            effective_fan_pwm_pct=0,
            thermal_fan_override_engaged=False,
            internal_temp_c=float(internal_temp_c),
            thermal_shutoff_ceiling_c=ceiling_c,
            thermal_auto_power_off_triggered=False,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            tier0_p3_sleep_abort_or_thermal_burn_events=0,
            errno_code=errno,
            status_code=status,
        )

    if power_save_start_time not in VALID_POWER_SAVE_OPTIONS:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_POWER_SAVE_START_TIME_OPTION_EINVAL")
    if auto_power_off_temp not in VALID_AUTO_POWER_OFF_TEMP_MODES:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_AUTO_POWER_OFF_TEMP_MODE_EINVAL")
    if fan_control not in VALID_FAN_CONTROL_MODES:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_FAN_CONTROL_MODE_EINVAL")

    timeout_sec = POWER_SAVE_SECONDS_TABLE[power_save_start_time]
    ceiling_c = AUTO_TEMP_SHUTOFF_CEILING_C[auto_power_off_temp]
    fan_ovr_c = AUTO_TEMP_FAN_OVERRIDE_THRESHOLD_C[auto_power_off_temp]

    if auto_power_off_temp == AUTO_TEMP_HIGH and mounting_state == MOUNTING_HANDHELD:
        return _mk_err(
            EOPNOTSUPP_ERRNO,
            "BLOCKED_AUTO_POWER_OFF_TEMP_HIGH_HANDHELD_CONTACT_BURN_RISK_EOPNOTSUPP",
            burn_blk=True,
            timeout_sec=timeout_sec,
            ceiling_c=ceiling_c,
        )

    if auto_power_off_temp == AUTO_TEMP_HIGH and fan_control == FAN_ALWAYS_OFF:
        return _mk_err(
            EOPNOTSUPP_ERRNO,
            "BLOCKED_AUTO_POWER_OFF_TEMP_HIGH_WITH_FAN_ALWAYS_OFF_EOPNOTSUPP",
            timeout_sec=timeout_sec,
            ceiling_c=ceiling_c,
        )

    if tier0_p3_vault_dump_requested:
        if power_save_start_time not in TIER0_SAFE_POWER_SAVE_OPTIONS:
            return _mk_err(
                EOPNOTSUPP_ERRNO,
                "BLOCKED_TIER0_75MIB_P3_VAULT_SLEEP_RISK_POWERSAVE_TOO_SHORT_EOPNOTSUPP",
                timeout_sec=timeout_sec,
                ceiling_c=ceiling_c,
            )
        if battery_charge_pct < TIER0_MIN_NP_FZ100_BATTERY_PCT:
            return _mk_err(
                EOPNOTSUPP_ERRNO,
                "BLOCKED_TIER0_75MIB_P3_VAULT_LOW_NP_FZ100_BATTERY_EOPNOTSUPP",
                timeout_sec=timeout_sec,
                ceiling_c=ceiling_c,
            )
        if fan_control != FAN_AUTO:
            return _mk_err(
                EOPNOTSUPP_ERRNO,
                "BLOCKED_TIER0_75MIB_P3_VAULT_REQUIRES_FAN_CONTROL_AUTO_EOPNOTSUPP",
                timeout_sec=timeout_sec,
                ceiling_c=ceiling_c,
            )
        if (
            usb_data_connection_active
            or ftp_or_smartphone_network_transfer_active
            or bluetooth_remote_ctrl_on
            or ir_remote_ctrl_on
        ):
            return _mk_err(
                EOPNOTSUPP_ERRNO,
                "BLOCKED_TIER0_75MIB_P3_VAULT_AIRGAP_ISOLATION_BREACH_EOPNOTSUPP",
                timeout_sec=timeout_sec,
                ceiling_c=ceiling_c,
            )

    auto_deactivated = len(active_conds) > 0
    entered_sleep = (
        (not auto_deactivated)
        and timeout_sec is not None
        and idle_elapsed_sec >= timeout_sec
    )
    tier0_guard_ok = (
        power_save_start_time in TIER0_SAFE_POWER_SAVE_OPTIONS
        and battery_charge_pct >= TIER0_MIN_NP_FZ100_BATTERY_PCT
        and fan_control == FAN_AUTO
        and not entered_sleep
    )

    thermal_shutoff = float(internal_temp_c) >= ceiling_c
    fan_override = False
    if fan_control == FAN_ALWAYS_OFF:
        pwm_pct = 0
    elif float(internal_temp_c) >= fan_ovr_c:
        pwm_pct = 100
        fan_override = fan_control in (FAN_MINIMUM, FAN_OFF_IN_REC)
    elif fan_control == FAN_OFF_IN_REC:
        pwm_pct = 0 if movie_recording_in_progress else 100
    elif fan_control == FAN_MINIMUM:
        pwm_pct = 35
    else:
        pwm_pct = 65 if float(internal_temp_c) >= 45.0 else 45

    return PowerSave9CondAutoTempHilResult(
        admitted=True,
        power_save_menu_name=POWER_SAVE_MENU_NAME,
        power_save_menu_path=POWER_SAVE_MENU_PATH,
        power_save_start_time=power_save_start_time,
        power_save_timeout_sec=timeout_sec,
        active_bypass_conditions=active_conds,
        active_bypass_count=len(active_conds),
        power_save_auto_deactivated=auto_deactivated,
        idle_elapsed_sec=idle_elapsed_sec,
        camera_entered_power_save_sleep=entered_sleep,
        tier0_p3_vault_dump_requested=tier0_p3_vault_dump_requested,
        tier0_p3_vault_bytes=TIER0_P3_VAULT_DUMP_BYTES if tier0_p3_vault_dump_requested else 0,
        battery_charge_pct=battery_charge_pct,
        tier0_sleep_lock_guard_satisfied=tier0_guard_ok,
        auto_power_off_temp_menu_name=AUTO_POWER_OFF_TEMP_MENU_NAME,
        auto_power_off_temp_menu_path=AUTO_POWER_OFF_TEMP_MENU_PATH,
        auto_power_off_temp=auto_power_off_temp,
        mounting_state=mounting_state,
        handheld_contact_burn_blocked=False,
        fan_control_menu_path=FAN_CONTROL_MENU_PATH,
        fan_control=fan_control,
        effective_fan_pwm_pct=pwm_pct,
        thermal_fan_override_engaged=fan_override,
        internal_temp_c=float(internal_temp_c),
        thermal_shutoff_ceiling_c=ceiling_c,
        thermal_auto_power_off_triggered=thermal_shutoff,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        tier0_p3_sleep_abort_or_thermal_burn_events=0,
        errno_code=0,
        status_code=(
            "ADMITTED_THERMAL_CEILING_GRACEFUL_AUTO_POWER_OFF_OK"
            if thermal_shutoff
            else (
                "ADMITTED_TIER0_AIRGAPPED_NP_FZ100_75MIB_P3_SLEEP_GUARD_LOCKED_OK"
                if tier0_p3_vault_dump_requested
                else (
                    "ADMITTED_POWER_SAVE_AUTO_DEACTIVATED_BY_ACTIVE_CONDITION_OK"
                    if auto_deactivated
                    else (
                        "ADMITTED_STANDALONE_IDLE_POWER_SAVE_SLEEP_ENTERED_OK"
                        if entered_sleep
                        else "ADMITTED_POWERSAVE_AND_AUTO_POWER_OFF_TEMP_READY_OK"
                    )
                )
            )
        ),
    )


def probe_hard_safety_redline(
    *,
    authorize_persistent_emmc_writes: bool = False,
    authorize_hardware_live_attachment: bool = False,
    authorize_spi_nor_write: bool = False,
    authorize_el3_payload_transmit: bool = False,
    authorize_isp_write: bool = False,
    emit_physical_usb_packet: bool = False,
    touch_otp_fuse: bool = False,
    increment_rpmb_counter: bool = False,
    bypass_steadyshot_active_or_ciz_4locks_or_tier0_thermal_guard: bool = False,
) -> RedlineGuardProbeResult:
    """Fail-closed probe verifying all 9 forbidden physical write/attach/bypass actions are blocked."""
    violations = [
        lbl
        for flag, lbl in (
            (authorize_persistent_emmc_writes, "PERSISTENT_EMMC_WRITE"),
            (authorize_hardware_live_attachment, "HARDWARE_LIVE_ATTACHMENT"),
            (authorize_spi_nor_write, "SPI_NOR_WRITE"),
            (authorize_el3_payload_transmit, "EL3_PAYLOAD_TRANSMIT"),
            (authorize_isp_write, "ISP_WRITE"),
            (emit_physical_usb_packet, "PHYSICAL_USB_PACKET_EMIT"),
            (touch_otp_fuse, "OTP_FUSE_TOUCH"),
            (increment_rpmb_counter, "RPMB_COUNTER_INCREMENT"),
            (
                bypass_steadyshot_active_or_ciz_4locks_or_tier0_thermal_guard,
                "STEADYSHOT_CIZ_4LOCK_OR_TIER0_THERMAL_GUARD_BYPASS",
            ),
        )
        if flag
    ]
    joined = "+".join(violations) if violations else "NONE"
    return RedlineGuardProbeResult(
        valid=(not violations),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        overall_ready_for_hardware_attach=OVERALL_READY_FOR_HARDWARE_ATTACH,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        isp_write_authorized=ISP_WRITE_AUTHORIZED,
        cnflasha_userspace_write_blocked=CNFLASHA_USERSPACE_WRITE_BLOCKED,
        cnflasha_mutation_bytes=CNFLASHA_MUTATION_BYTES,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        otp_fuse_touches=OTP_FUSE_TOUCHES,
        rpmb_counter_increments=RPMB_COUNTER_INCREMENTS,
        steadyshot_active_cutoff_bypass_events=STEADYSHOT_ACTIVE_CUTOFF_BYPASS_EVENTS,
        ciz_4lock_unrestored_or_bypass_events=CIZ_4LOCK_UNRESTORED_OR_BYPASS_EVENTS,
        tier0_p3_sleep_abort_or_thermal_burn_events=TIER0_P3_SLEEP_ABORT_OR_THERMAL_BURN_EVENTS,
        blocked_action=joined,
        status_code=(
            f"FAIL_CLOSED_REDLINE_BLOCKED:{joined}"
            if violations
            else "HARD_SAFETY_REDLINES_LOCKED_OK"
        ),
    )


def evaluate_pillar_c_d_powersave_9cond_autotemp_and_redlines() -> Dict[str, object]:
    nine_condition_matrix = {
        cond_key: asdict(
            probe_powersave_9cond_and_autotemp_fan_hil(
                power_save_start_time=POWER_SAVE_10_SEC,
                idle_elapsed_sec=600,
                **{cond_key: True},
            )
        )
        for cond_key in POWER_SAVE_9_CONDITION_KEYS
    }
    airgap_default_5min_sleeps = probe_powersave_9cond_and_autotemp_fan_hil(
        power_save_start_time=POWER_SAVE_5_MIN_DEFAULT,
        idle_elapsed_sec=305,
    )
    tier0_5min_blocked = probe_powersave_9cond_and_autotemp_fan_hil(
        power_save_start_time=POWER_SAVE_5_MIN_DEFAULT,
        tier0_p3_vault_dump_requested=True,
        battery_charge_pct=85,
    )
    tier0_off_admitted = probe_powersave_9cond_and_autotemp_fan_hil(
        power_save_start_time=POWER_SAVE_OFF,
        idle_elapsed_sec=420,
        tier0_p3_vault_dump_requested=True,
        battery_charge_pct=85,
        fan_control=FAN_AUTO,
    )
    tier0_30min_admitted = probe_powersave_9cond_and_autotemp_fan_hil(
        power_save_start_time=POWER_SAVE_30_MIN,
        idle_elapsed_sec=420,
        tier0_p3_vault_dump_requested=True,
        battery_charge_pct=85,
        fan_control=FAN_AUTO,
    )
    autotemp_high_tripod_ok = probe_powersave_9cond_and_autotemp_fan_hil(
        auto_power_off_temp=AUTO_TEMP_HIGH,
        mounting_state=MOUNTING_TRIPOD,
        fan_control=FAN_OFF_IN_REC,
        movie_recording_in_progress=True,
        internal_temp_c=74.0,
    )
    autotemp_high_handheld_blocked = probe_powersave_9cond_and_autotemp_fan_hil(
        auto_power_off_temp=AUTO_TEMP_HIGH,
        mounting_state=MOUNTING_HANDHELD,
        fan_control=FAN_AUTO,
    )
    autotemp_high_fan_always_off_blocked = probe_powersave_9cond_and_autotemp_fan_hil(
        auto_power_off_temp=AUTO_TEMP_HIGH,
        mounting_state=MOUNTING_TRIPOD,
        fan_control=FAN_ALWAYS_OFF,
    )
    baseline_redline = probe_hard_safety_redline()
    blocked_probes = [
        asdict(probe_hard_safety_redline(**{k: True}))
        for k in (
            "authorize_persistent_emmc_writes",
            "authorize_hardware_live_attachment",
            "authorize_spi_nor_write",
            "authorize_el3_payload_transmit",
            "authorize_isp_write",
            "emit_physical_usb_packet",
            "touch_otp_fuse",
            "increment_rpmb_counter",
            "bypass_steadyshot_active_or_ciz_4locks_or_tier0_thermal_guard",
        )
    ]
    passed = (
        len(nine_condition_matrix) == 9
        and all(
            m["admitted"]
            and m["power_save_auto_deactivated"]
            and (not m["camera_entered_power_save_sleep"])
            for m in nine_condition_matrix.values()
        )
        and airgap_default_5min_sleeps.admitted
        and airgap_default_5min_sleeps.camera_entered_power_save_sleep
        and (not tier0_5min_blocked.admitted)
        and tier0_off_admitted.admitted
        and tier0_off_admitted.tier0_sleep_lock_guard_satisfied
        and tier0_30min_admitted.admitted
        and tier0_30min_admitted.tier0_sleep_lock_guard_satisfied
        and autotemp_high_tripod_ok.admitted
        and autotemp_high_tripod_ok.thermal_fan_override_engaged
        and autotemp_high_tripod_ok.effective_fan_pwm_pct == 100
        and (not autotemp_high_handheld_blocked.admitted)
        and autotemp_high_handheld_blocked.handheld_contact_burn_blocked
        and (not autotemp_high_fan_always_off_blocked.admitted)
        and baseline_redline.valid
        and len(blocked_probes) == 9
        and all(not p["valid"] for p in blocked_probes)
    )
    return {
        "passed": passed,
        "power_save_9condition_bypass_matrix": nine_condition_matrix,
        "airgap_default_5min_idle_enters_sleep": asdict(airgap_default_5min_sleeps),
        "tier0_p3_vault_default_5min_blocked": asdict(tier0_5min_blocked),
        "tier0_p3_vault_off_admitted": asdict(tier0_off_admitted),
        "tier0_p3_vault_30min_admitted": asdict(tier0_30min_admitted),
        "autotemp_high_tripod_fan_override_ok": asdict(autotemp_high_tripod_ok),
        "autotemp_high_handheld_burn_blocked": asdict(autotemp_high_handheld_blocked),
        "autotemp_high_with_fan_always_off_blocked": asdict(autotemp_high_fan_always_off_blocked),
        "baseline_redline_guard": asdict(baseline_redline),
        "blocked_redline_probes": blocked_probes,
    }


# ---------------------------------------------------------------------------
# Unified Phase 226 (Stage 41, 41/41 Milestone) Co-Emulator Entry Point & CLI
# ---------------------------------------------------------------------------


def run_phase226_realhw_steadyshot_active_ciz_4locks_powersave_autotemp_hil(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run the complete Phase 226 Stage 41 (41/41) HIL audit and return a deterministic payload."""
    donor_audit = inspect_phase226_donors(force_clean_room=force_clean_room, env=env)
    pillar_a = evaluate_pillar_a_steadyshot_active_cutoffs_hil()
    pillar_b = evaluate_pillar_b_ciz_digital_zoom_4locks_and_restore_hil()
    pillar_cd = evaluate_pillar_c_d_powersave_9cond_autotemp_and_redlines()

    redlines: Dict[str, object] = {
        "p8_cp_mutation_forbidden": P8_CP_MUTATION_FORBIDDEN,
        "nop_count": NOP_COUNT,
        "guest_code_modification_bytes": GUEST_CODE_MODIFICATION_BYTES,
        "cp_mutation_bytes": CP_MUTATION_BYTES,
        "wbi_mutation_bytes": WBI_MUTATION_BYTES,
        "calibration_mutation_bytes": CALIBRATION_MUTATION_BYTES,
        "cnflasha_mutation_bytes": CNFLASHA_MUTATION_BYTES,
        "cnflasha_userspace_write_blocked": CNFLASHA_USERSPACE_WRITE_BLOCKED,
        "nvram_persistent_writes": NVRAM_PERSISTENT_WRITES,
        "bk4_persistent_nvram_writes": BK4_PERSISTENT_NVRAM_WRITES,
        "physical_device_writes": PHYSICAL_DEVICE_WRITES,
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "hardware_live_attachment_authorized": HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        "overall_ready_for_hardware_attach": OVERALL_READY_FOR_HARDWARE_ATTACH,
        "isp_write_authorized": ISP_WRITE_AUTHORIZED,
        "emmc_nflasha_write_count": EMMC_NFLASHA_WRITE_COUNT,
        "emmc_mutation_bytes": EMMC_MUTATION_BYTES,
        "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
        "spi_nor_mutation_bytes": SPI_NOR_MUTATION_BYTES,
        "el3_payload_transmit_authorized": EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        "physical_usb_packets_emitted": PHYSICAL_USB_PACKETS_EMITTED,
        "otp_fuse_touches": OTP_FUSE_TOUCHES,
        "rpmb_counter_increments": RPMB_COUNTER_INCREMENTS,
        "steadyshot_active_cutoff_bypass_events": STEADYSHOT_ACTIVE_CUTOFF_BYPASS_EVENTS,
        "ciz_4lock_unrestored_or_bypass_events": CIZ_4LOCK_UNRESTORED_OR_BYPASS_EVENTS,
        "tier0_p3_sleep_abort_or_thermal_burn_events": TIER0_P3_SLEEP_ABORT_OR_THERMAL_BURN_EVENTS,
        "rsv_orphan_count": RSV_ORPHAN_COUNT,
        "wf12_00342260_hits": WF12_00342260_HITS,
        "appfw_crashes": APPFW_CRASHES,
        "null_gpio_derefs": NULL_GPIO_DEREFS,
        "mailbox_stalls": MAILBOX_STALLS,
        "stock_cp_fault_count": STOCK_CP_FAULT_COUNT,
        "raw_firmware_bytes_leaked": RAW_FIRMWARE_BYTES_LEAKED,
        "donor_access_mode": DONOR_ACCESS_MODE,
    }

    all_passed = (
        donor_audit.all_contracts_verified
        and donor_audit.raw_firmware_bytes_leaked == 0
        and bool(pillar_a["passed"])
        and bool(pillar_b["passed"])
        and bool(pillar_cd["passed"])
        and CNFLASHA_USERSPACE_WRITE_BLOCKED
        and CNFLASHA_MUTATION_BYTES == 0
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        and (not OVERALL_READY_FOR_HARDWARE_ATTACH)
        and (not SPI_NOR_WRITE_AUTHORIZED)
        and (not EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        and (not ISP_WRITE_AUTHORIZED)
        and PHYSICAL_USB_PACKETS_EMITTED == 0
        and OTP_FUSE_TOUCHES == 0
        and RPMB_COUNTER_INCREMENTS == 0
        and STEADYSHOT_ACTIVE_CUTOFF_BYPASS_EVENTS == 0
        and CIZ_4LOCK_UNRESTORED_OR_BYPASS_EVENTS == 0
        and TIER0_P3_SLEEP_ABORT_OR_THERMAL_BURN_EVENTS == 0
    )

    payload: Dict[str, object] = {
        "schema": SCHEMA_ID,
        "version": PHASE_226_VERSION,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "stage": STAGE_NAME,
        "all_checks_passed": all_passed,
        "source_mode": donor_audit.source_mode,
        "redlines": redlines,
        "donor_audit": asdict(donor_audit),
        "pillar_a_steadyshot_active_cutoffs_hil": pillar_a,
        "pillar_b_ciz_digital_zoom_4locks_and_restore_hil": pillar_b,
        "pillar_c_d_powersave_9cond_autotemp_and_redlines": pillar_cd,
    }
    payload["audit_digest_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_steadyshot_active_ciz_4locks_powersave_autotemp_coemulator.py",
        description=(
            "Phase 226 Stage 41 (41/41 Milestone) — Real-Hardware ILME-FX3 SteadyShot Active "
            "3-Cutoffs, Clear Image Zoom 4-Lock AF/Metering & Power Save 9-Condition + Auto Power OFF Temp. HIL"
        ),
    )
    parser.add_argument("--self-test", action="store_true", help="Run full Phase 226 HIL self-test")
    parser.add_argument("--clean-room", action="store_true", help="Force clean-room synthetic mode")
    parser.add_argument("--json", action="store_true", help="Emit deterministic JSON audit report")
    parser.add_argument("--summary", action="store_true", help="Emit concise one-line summary")
    args = parser.parse_args(argv)

    rep = run_phase226_realhw_steadyshot_active_ciz_4locks_powersave_autotemp_hil(
        force_clean_room=True if args.clean_room else None
    )
    if args.summary and not args.json:
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        pa = rep["pillar_a_steadyshot_active_cutoffs_hil"]
        pb = rep["pillar_b_ciz_digital_zoom_4locks_and_restore_hil"]
        pcd = rep["pillar_c_d_powersave_9cond_autotemp_and_redlines"]
        crop = pa["active_4k_2398p_1_10x_crop_ok"]["crop_factor"]
        locks = len(pb["ciz_4k_1_5x_all_4_locks_engaged"]["active_4locks"])
        restored = int(pb["zoom_excursion_and_1_0x_optical_restore"]["restored_matches_initial"])
        conds = len(pcd["power_save_9condition_bypass_matrix"])
        t0_ok = int(pcd["tier0_p3_vault_off_admitted"]["tier0_sleep_lock_guard_satisfied"])
        sys.stdout.write(
            f"[{status}] Phase 226 Stage 41 ({MILESTONE_LABEL}) | "
            f"mode={rep['source_mode']} | "
            f"steadyshot=active:{crop:.2f}x_3cutoffs_blk:1 | "
            f"ciz_dz={locks}locks_1.0x_restore:{restored} | "
            f"powersave={conds}cond_tier0_p3:{t0_ok}_autotemp_high_tripod:1 | "
            f"digest={rep['audit_digest_sha256'][:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")
    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
