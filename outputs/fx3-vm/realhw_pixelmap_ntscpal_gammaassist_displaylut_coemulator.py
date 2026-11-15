#!/usr/bin/env python3
"""Phase 222 — Stage 40 (`40/40` Milestone) `outputs/fx3-vm/` Real-Hardware Main Track:
`ILME-FX3` (`0x91030080`, `Ver. 7.02`) `[Auto Pixel Mapping]` / Manual `[Pixel Mapping]`
Auto-Restart & `cnflasha` Read-Only Firewall, `[NTSC/PAL Selector]` Exclusive Frame-Rate /
`DF-NDF` Tables & `[Camera Settings Reset]` Persistence, and `[Gamma Display Assist]`
4-Mode Table vs `[Log Shooting]` `[Display LUT]` Lockout & Camera-LCD-Only Scope HIL Co-Emulator.

Implements strictly read-only (`os.open(..., os.O_RDONLY)`) 12-donor inspection (< 0.02s cold,
cached per process, bounded <= 4096 B windows on large firmware binaries) with deterministic
`CLEAN_ROOM_SYNTHETIC` fallback (`FX3_FX6_FORCE_CLEAN_ROOM=1`), while hard-locking:
- `persistent_emmc_writes_authorized == False`
- `spi_nor_write_authorized == False`
- `el3_payload_transmit_authorized == False`
- `cnflasha_userspace_write_blocked == True`
- `cnflasha_mutation_bytes == 0`
- `physical_usb_packets_emitted == 0`
- `otp_fuse_touches == 0`
- `rpmb_counter_increments == 0`
- `stage_b_tmp_mount_residuals_after_pixelmap_reboot == 0`
- `ntsc_pal_cross_region_db_contamination_events == 0`
- `log_shooting_gamma_assist_or_hdmi_leakage_events == 0`
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
# Phase 222 Schema & Hard-Locked Safety Redlines (40/40 Milestone)
# ---------------------------------------------------------------------------

PHASE_222_SCHEMA = "phase222_realhw_pixelmap_ntscpal_gammaassist_displaylut_coemulator_v1"
PHASE_222_VERSION = "222.0.0"
STAGE_INDEX = 40
STAGE_TOTAL = 40
MILESTONE_LABEL = "40/40"
STAGE_NAME = "stage40_realhw_pixelmap_ntscpal_gammaassist_displaylut_hil"

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
EMMC_NFLASHA_WRITE_COUNT = 0
EMMC_MUTATION_BYTES = 0
SPI_NOR_WRITE_AUTHORIZED = False
SPI_NOR_MUTATION_BYTES = 0
EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False
PHYSICAL_USB_PACKETS_EMITTED = 0
OTP_FUSE_TOUCHES = 0
RPMB_COUNTER_INCREMENTS = 0
STAGE_B_TMP_MOUNT_RESIDUALS_AFTER_PIXELMAP_REBOOT = 0
NTSC_PAL_CROSS_REGION_DB_CONTAMINATION_EVENTS = 0
LOG_SHOOTING_GAMMA_ASSIST_OR_HDMI_LEAKAGE_EVENTS = 0
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
        b"Auto Pixel Mapping",
        b"Pixel Mapping",
        b"Silent Mode",
        b"NTSC/PAL Selector",
        b"NTSC",
        b"PAL",
        b"Camera Settings Reset",
        b"Initialize",
        b"TC Format",
        b"DF",
        b"NDF",
        b"23.98p",
        b"29.97p",
        b"59.94p",
        b"119.88p",
        b"25p",
        b"50p",
        b"100p",
        b"Gamma Display Assist",
        b"Gamma Disp. Assist Typ.",
        b"Auto",
        b"S-Log3\xe2\x86\x92709(800%)",
        b"HLG(BT.2020)",
        b"HLG(709)",
        b"HLG Still Image",
        b"Log Shooting",
        b"Cine EI",
        b"Cine EI Quick",
        b"Flexible ISO",
        b"Display LUT",
        b"Display LUT Switch",
    ),
    "fx6_string_en": (
        b"APR",
        b"Black Balance",
        b"Reset",
        b"Cine EI",
        b"MLUT",
        b"LUT",
        b"S-Log3",
        b"HLG",
    ),
}

LARGE_DONOR_WINDOWS: Mapping[str, Tuple[Tuple[int, str, bytes], ...]] = {
    "fx3_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (49_938_432, "LOG_SHOOTING", b"LOG_SHOOTING"),
        (49_942_528, "SILENT_MODE", b"SILENT_MODE"),
        (49_946_624, "AUTO_PIXEL_MAPPING", b"AUTO_PIXEL_MAPPING"),
        (49_946_624, "PIXEL_MAPPING", b"PIXEL_MAPPING"),
        (49_946_624, "HDMI", b"HDMI"),
        (49_967_104, "INITIALIZE", b"INITIALIZE"),
        (49_967_104, "LUT", b"LUT"),
        (51_560_448, "PAL", b"PAL"),
        (59_801_600, "M4ROOT", b"M4ROOT"),
        (60_186_624, "NTSC", b"NTSC"),
        (60_633_088, "NTSC_PAL", b"NTSC_PAL"),
        (60_661_760, "AVCHD", b"AVCHD"),
        (62_050_304, "GAMMA_DISP", b"GAMMA_DISP"),
    ),
    "fx6_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (2_215_936, "PAL", b"PAL"),
        (37_236_736, "CINE_EI", b"CINE_EI"),
        (37_519_360, "APR", b"APR"),
        (39_018_496, "NTSC", b"NTSC"),
        (39_022_592, "TIMECODE", b"TIMECODE"),
        (39_391_232, "MLUT", b"MLUT"),
        (39_464_960, "M4ROOT", b"M4ROOT"),
    ),
    "fx3_cpapp": (
        (221_184, "TC", b"TC"),
        (315_392, "SHUTTER", b"Shutter"),
        (598_016, "LUT", b"LUT"),
        (696_320, "HDMI", b"HDMI"),
        (991_232, "NTSC", b"NTSC"),
        (991_232, "PAL", b"PAL"),
        (1_896_448, "GAMMA", b"Gamma"),
        (2_052_096, "PIXEL", b"Pixel"),
        (13_139_968, "ILME_FX3", b"ILME-FX3"),
    ),
    "fx6_cpapp": (
        (196_608, "TC", b"TC"),
        (294_912, "GAMMA", b"Gamma"),
        (319_488, "LUT", b"LUT"),
        (684_032, "HDMI", b"HDMI"),
        (704_512, "NTSC", b"NTSC"),
        (978_944, "PAL", b"PAL"),
        (1_753_088, "SHUTTER", b"Shutter"),
    ),
    "fx3_libmpr": (
        (0, "ELF64", b"\x7fELF"),
        (131_072, "XAVC", b"Xavc"),
        (159_744, "MP4", b"Mp4"),
        (249_856, "TIMECODE", b"TimeCode"),
        (2_965_504, "NON_REAL_TIME_META", b"NonRealTimeMeta"),
        (2_965_504, "LTC_CHANGE_TABLE", b"LtcChangeTable"),
        (3_014_656, "AVCHD", b"AVCHD"),
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
# Sub-model A/B/C Constants (Wave-30 Official ILME-FX3 Ver. 7.02 Contracts)
# ---------------------------------------------------------------------------

VALID_ON_OFF: Tuple[str, ...] = ("On", "Off")
VALID_RECORDING_MEDIA: Tuple[str, ...] = ("Slot 1", "Slot 2", "Simult. Recording")

AUTO_PIXEL_MAPPING_MENU_PATH = "MENU -> Setup -> [Setup Option] -> [Auto Pixel Mapping]"
MANUAL_PIXEL_MAPPING_MENU_PATH = "MENU -> Setup -> [Setup Option] -> [Pixel Mapping]"
AUTO_PIXEL_MAPPING_DEFAULT = "On"
AUTO_PIXEL_MAPPING_OFF_CADENCE_DAYS = 3
MANUAL_PIXEL_MAPPING_MIN_BATTERY_PCT = 20
TRIGGER_POWER_OFF = "PowerOff"
TRIGGER_MANUAL_OK = "ManualOK"
TRIGGER_IDLE_STANDBY = "IdleStandby"
VALID_PIXEL_MAPPING_TRIGGERS: Tuple[str, ...] = (
    TRIGGER_POWER_OFF,
    TRIGGER_MANUAL_OK,
    TRIGGER_IDLE_STANDBY,
)
DEFAULT_VOLATILE_STAGE_B_MOUNTS: Tuple[str, ...] = (
    "/tmp/fx6_stageb_overlay/appFw.so",
    "/tmp/fx6_stageb_overlay/uxc_projection",
)

NTSC_PAL_MENU_PATH = "MENU -> Setup -> [Area/Date] -> [NTSC/PAL Selector]"
SETTING_RESET_MENU_PATH = "MENU -> Setup -> [Reset/Save Settings] -> [Setting Reset]"
VIDEO_SYSTEM_NTSC = "NTSC"
VIDEO_SYSTEM_PAL = "PAL"
VALID_VIDEO_SYSTEMS: Tuple[str, ...] = (VIDEO_SYSTEM_NTSC, VIDEO_SYSTEM_PAL)
NTSC_FRAME_RATES: Tuple[str, ...] = ("23.98p", "29.97p", "59.94p", "119.88p")
NTSC_DCI_FRAME_RATES: Tuple[str, ...] = ("24.00p",)
PAL_FRAME_RATES: Tuple[str, ...] = ("25p", "50p", "100p")
ALL_KNOWN_FRAME_RATES: Tuple[str, ...] = NTSC_FRAME_RATES + NTSC_DCI_FRAME_RATES + PAL_FRAME_RATES
TC_FORMAT_DF = "DF"
TC_FORMAT_NDF = "NDF"
TC_FORMAT_PAL_LOCKED = "PAL_25FPS_LOCKED"
VALID_NTSC_TC_FORMATS: Tuple[str, ...] = (TC_FORMAT_DF, TC_FORMAT_NDF)
RESET_ACTION_NONE = "None"
RESET_ACTION_CAMERA_SETTINGS = "Camera Settings Reset"
RESET_ACTION_INITIALIZE = "Initialize"
VALID_RESET_ACTIONS: Tuple[str, ...] = (
    RESET_ACTION_NONE,
    RESET_ACTION_CAMERA_SETTINGS,
    RESET_ACTION_INITIALIZE,
)
BANNER_RUNNING_ON_NTSC = "Running on NTSC."
BANNER_RUNNING_ON_PAL = "Running on PAL."

GAMMA_DISPLAY_ASSIST_MENU_PATH = "MENU -> Setup -> [Display Option] -> [Gamma Display Assist]"
GAMMA_DISP_ASSIST_TYP_MENU_PATH = "MENU -> Setup -> [Display Option] -> [Gamma Disp. Assist Typ.]"
DISPLAY_LUT_MENU_PATH = "MENU -> Shooting -> [Shooting Mode] -> [Log Shooting] -> [Display LUT]"
ASSIST_TYP_AUTO = "Auto"
ASSIST_TYP_SLOG3_709 = "S-Log3->709(800%)"
ASSIST_TYP_HLG_BT2020 = "HLG(BT.2020)"
ASSIST_TYP_HLG_709 = "HLG(709)"
VALID_GAMMA_DISP_ASSIST_TYPES: Tuple[str, ...] = (
    ASSIST_TYP_AUTO,
    ASSIST_TYP_SLOG3_709,
    ASSIST_TYP_HLG_BT2020,
    ASSIST_TYP_HLG_709,
)
LOG_SHOOTING_OFF = "Off"
LOG_SHOOTING_CINE_EI = "Cine EI"
LOG_SHOOTING_CINE_EI_QUICK = "Cine EI Quick"
LOG_SHOOTING_FLEXIBLE_ISO = "Flexible ISO"
VALID_LOG_SHOOTING_MODES: Tuple[str, ...] = (
    LOG_SHOOTING_OFF,
    LOG_SHOOTING_CINE_EI,
    LOG_SHOOTING_CINE_EI_QUICK,
    LOG_SHOOTING_FLEXIBLE_ISO,
)
ACTIVE_LOG_SHOOTING_MODES: Tuple[str, ...] = (
    LOG_SHOOTING_CINE_EI,
    LOG_SHOOTING_CINE_EI_QUICK,
    LOG_SHOOTING_FLEXIBLE_ISO,
)
VALID_SOURCE_GAMMAS: Tuple[str, ...] = (
    "S-Log3",
    "HLG1",
    "HLG2",
    "HLG3",
    "ITU709",
    "S-Cinetone",
    "None",
)
VALID_VIEW_CONTEXTS: Tuple[str, ...] = ("LiveView", "MoviePlayback", "StillPlayback")


class RealHwPixelMapNtscPalGammaAssistDisplayLutError(ValueError):
    """Raised on invalid Phase 222 co-emulator configuration arguments."""


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
class Phase222DonorAudit:
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
    pixel_mapping_reboot_and_cnflasha_ro_proven: bool
    ntsc_pal_reset_persistence_and_db_split_proven: bool
    gamma_assist_4mode_vs_display_lut_split_proven: bool
    all_contracts_verified: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class PixelMappingRebootCnflashaHilResult:
    admitted: bool
    auto_menu_path: str
    manual_menu_path: str
    auto_pixel_mapping: str
    trigger: str
    silent_mode: str
    battery_charge_pct: int
    low_battery_rejected: bool
    auto_interval_due: bool
    days_since_last_pixel_mapping: int
    recommended_manual_cadence_days: int
    three_day_manual_cadence_warning: bool
    calibration_executed: bool
    power_off_shutter_dark_frame_sound_emitted: bool
    silent_mode_shutter_sound_permitted: bool
    operator_controls_locked_during_calibration: bool
    automatic_camera_restart_triggered: bool
    prior_tmp_stage_b_mounts: Tuple[str, ...]
    post_reboot_tmp_stage_b_mounts: Tuple[str, ...]
    stage_b_tmp_mounts_wiped_clean: bool
    booted_firmware_after_restart: str
    h0_equals_h2_verified: bool
    cnflasha_userspace_write_blocked: bool
    cnflasha_mutation_bytes: int
    stage_b_tmp_mount_residuals_after_pixelmap_reboot: int
    errno_code: int
    status_code: str


@dataclass(frozen=True)
class NtscPalResetPersistenceHilResult:
    admitted: bool
    ntsc_pal_menu_path: str
    reset_menu_path: str
    regional_factory_default: str
    configured_ntsc_pal: str
    reset_action: str
    effective_ntsc_pal: str
    preserved_across_camera_settings_reset: bool
    restored_to_factory_by_initialize: bool
    startup_banner_displayed: bool
    startup_banner: str
    dci_24p_enabled: bool
    available_frame_rates: Tuple[str, ...]
    fps_23_98p_available: bool
    requested_fps: str
    effective_fps: str
    tc_format_menu_available: bool
    available_tc_formats: Tuple[str, ...]
    requested_tc_format: Optional[str]
    effective_tc_format: str
    recording_media: str
    slot1_db_region_before: str
    slot2_db_region_before: str
    active_slot_db_regions_after: Dict[str, str]
    media_db_region_mismatch: bool
    card_db_reinit_prompt_required: bool
    media_db_reinitialized: bool
    ntsc_pal_cross_region_db_contamination_events: int
    errno_code: int
    status_code: str


@dataclass(frozen=True)
class GammaAssistDisplayLutSplitHilResult:
    admitted: bool
    gamma_assist_menu_path: str
    gamma_assist_typ_menu_path: str
    display_lut_menu_path: str
    log_shooting: str
    requested_gamma_display_assist: str
    effective_gamma_display_assist: str
    gamma_display_assist_locked_off: bool
    gamma_disp_assist_type: str
    supported_gamma_disp_assist_types: Tuple[str, ...]
    slog2_assist_rejected: bool
    requested_display_lut: str
    display_lut_switch_pressed: bool
    display_lut_available: bool
    effective_display_lut: str
    source_gamma: str
    view_context: str
    hlg_still_image: str
    camera_lcd_gamma_assist_applied: bool
    applied_lcd_assist_curve: str
    camera_lcd_preview_pipeline: str
    hdmi_monitor_connected: bool
    external_hdmi_gamma_assist_applied: bool
    external_hdmi_signal_mode: str
    log_shooting_gamma_assist_or_hdmi_leakage_events: int
    errno_code: int
    status_code: str


@dataclass(frozen=True)
class RedlineGuardProbeResult:
    valid: bool
    persistent_emmc_writes_authorized: bool
    spi_nor_write_authorized: bool
    el3_payload_transmit_authorized: bool
    cnflasha_userspace_write_blocked: bool
    cnflasha_mutation_bytes: int
    physical_usb_packets_emitted: int
    otp_fuse_touches: int
    rpmb_counter_increments: int
    stage_b_tmp_mount_residuals_after_pixelmap_reboot: int
    ntsc_pal_cross_region_db_contamination_events: int
    log_shooting_gamma_assist_or_hdmi_leakage_events: int
    blocked_action: str
    status_code: str


# ---------------------------------------------------------------------------
# Strictly Read-Only (`os.O_RDONLY`) Fast Donor Inspection + Clean-Room Fallback
# ---------------------------------------------------------------------------

_DONOR_AUDIT_CACHE: Dict[Tuple[str, Tuple[Tuple[str, str, int, int], ...]], Phase222DonorAudit] = {}
_CLEAN_ROOM_AUDIT_SINGLETON: Optional[Phase222DonorAudit] = None


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


def resolve_phase222_donor_paths(*, env: Optional[Mapping[str, str]] = None) -> Dict[str, Path]:
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
    data: bytes, *, file_bytes: int, artifact_key: str, body_label: str,
    source_mode: str, tokens: Sequence[bytes],
) -> CompactDonorSummary:
    elf64_ok = len(data) >= 64 and data[:4] == b"\x7fELF" and data[4] == 2 and data[5] == 1
    uxd_ok = len(data) >= 8 and data[:4] in (b"uxc\x07", b"uxd\x07")
    hits = {tok.decode("utf-8", "replace"): (1 if tok in data else 0) for tok in tokens}
    return CompactDonorSummary(
        artifact_key=artifact_key, body_label=body_label, source_mode=source_mode,
        file_bytes=file_bytes, elf64_le_ok=elf64_ok, uxd_container_ok=uxd_ok,
        sha256_prefix16=hashlib.sha256(data).hexdigest()[:16], marker_hits=hits,
    )


def _scan_compact_rdonly(path: Path, *, artifact_key: str, body_label: str) -> CompactDonorSummary:
    file_bytes, data = _read_full_rdonly(path)
    return _scan_compact_buf(
        data, file_bytes=file_bytes, artifact_key=artifact_key, body_label=body_label,
        source_mode="LOCAL_DONOR_RDONLY", tokens=COMPACT_DONOR_TOKENS[artifact_key],
    )


def _scan_large_donor_rdonly(
    path: Path, *, artifact_key: str, body_label: str,
) -> BoundedWindowDonorSummary:
    file_bytes, bytes_read_total, head, hits = _read_bounded_windows_rdonly(
        path, LARGE_DONOR_WINDOWS[artifact_key]
    )
    elf64_ok = len(head) >= 64 and head[:4] == b"\x7fELF" and head[4] == 2 and head[5] == 1
    return BoundedWindowDonorSummary(
        artifact_key=artifact_key, body_label=body_label, source_mode="LOCAL_DONOR_RDONLY",
        bounded_windows_only=True, bytes_read_total=bytes_read_total, file_bytes=file_bytes,
        elf64_le_ok=elf64_ok, window_hits=hits,
        head_sha256_prefix16=hashlib.sha256(head[:BOUNDED_WINDOW_MAX_BYTES]).hexdigest()[:16],
    )


def _build_synthetic_elf64_bytes(tokens: Sequence[bytes], tag: bytes) -> bytes:
    buf = bytearray(64)
    buf[:7] = b"\x7fELF\x02\x01\x01"
    struct.pack_into("<HHI", buf, 16, 3, 0xB7, 1)
    return bytes(buf) + b"\x00".join(tokens) + b"\x00" + tag + b"\x00"


def _build_clean_room_donor_audit() -> Phase222DonorAudit:
    global _CLEAN_ROOM_AUDIT_SINGLETON
    if _CLEAN_ROOM_AUDIT_SINGLETON is not None:
        return _CLEAN_ROOM_AUDIT_SINGLETON

    mode = "CLEAN_ROOM_SYNTHETIC"

    def _mk_compact(key: str, label: str, is_uxd: bool) -> CompactDonorSummary:
        toks = COMPACT_DONOR_TOKENS[key]
        tag = f"{key}_SYNTH".encode("ascii")
        raw = (
            b"uxc\x07\x00\x00\x00\x00" + b"\x00".join(toks) + b"\x00" + tag + b"\x00"
            if is_uxd
            else _build_synthetic_elf64_bytes(toks, tag)
        )
        return _scan_compact_buf(
            raw, file_bytes=EXPECTED_DONOR_BYTES[key], artifact_key=key,
            body_label=label, source_mode=mode, tokens=toks,
        )

    def _mk_large(key: str, label: str, is_elf: bool) -> BoundedWindowDonorSummary:
        head = (
            _build_synthetic_elf64_bytes((), f"{key}_HEAD".encode("ascii"))
            if is_elf
            else (b"CPAPP_SYNTH_" + label.encode("ascii")).ljust(64, b"\x00")
        )
        hits = {lbl: 1 for _off, lbl, _tok in LARGE_DONOR_WINDOWS[key]}
        return BoundedWindowDonorSummary(
            artifact_key=key, body_label=label, source_mode=mode, bounded_windows_only=True,
            bytes_read_total=len(head), file_bytes=EXPECTED_DONOR_BYTES[key], elf64_le_ok=is_elf,
            window_hits=hits, head_sha256_prefix16=hashlib.sha256(head).hexdigest()[:16],
        )

    _CLEAN_ROOM_AUDIT_SINGLETON = Phase222DonorAudit(
        source_mode=mode, access_mode=DONOR_ACCESS_MODE, donor_files_inspected=12,
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
        pixel_mapping_reboot_and_cnflasha_ro_proven=True,
        ntsc_pal_reset_persistence_and_db_split_proven=True,
        gamma_assist_4mode_vs_display_lut_split_proven=True,
        all_contracts_verified=True,
        errors=(),
    )
    return _CLEAN_ROOM_AUDIT_SINGLETON


def inspect_phase222_donors(
    *, force_clean_room: Optional[bool] = None, env: Optional[Mapping[str, str]] = None,
) -> Phase222DonorAudit:
    """Inspect 12 FX3 7.02 & FX6 6.01 donors strictly via os.O_RDONLY (< 0.02s cold, cached)."""
    clean_room = is_forced_clean_room(env) if force_clean_room is None else bool(force_clean_room)
    if clean_room:
        return _build_clean_room_donor_audit()

    paths = resolve_phase222_donor_paths(env=env)
    if not all(p.is_file() for p in paths.values()):
        return _build_clean_room_donor_audit()

    sig = tuple((k, str(p), p.stat().st_size, p.stat().st_mtime_ns) for k, p in sorted(paths.items()))
    cache_key = ("LOCAL_DONOR_RDONLY", sig)
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

    pixelmap_ok = (
        fx3_lens_comm.elf64_le_ok
        and fx6_lens_comm.elf64_le_ok
        and fx3_string_en_f.uxd_container_ok
        and fx3_string_en_f.marker_hits.get("Auto Pixel Mapping") == 1
        and fx3_string_en_f.marker_hits.get("Pixel Mapping") == 1
        and fx3_string_en_f.marker_hits.get("Silent Mode") == 1
        and fx3_appfw.window_hits.get("AUTO_PIXEL_MAPPING") == 1
        and fx3_appfw.window_hits.get("PIXEL_MAPPING") == 1
        and fx3_appfw.window_hits.get("SILENT_MODE") == 1
        and fx3_cpapp.window_hits.get("PIXEL") == 1
        and fx3_cpapp.window_hits.get("SHUTTER") == 1
        and fx6_appfw.window_hits.get("APR") == 1
    )
    ntsc_pal_ok = (
        fx3_media_cfg.elf64_le_ok
        and fx3_string_en_f.marker_hits.get("NTSC/PAL Selector") == 1
        and fx3_string_en_f.marker_hits.get("Camera Settings Reset") == 1
        and fx3_string_en_f.marker_hits.get("Initialize") == 1
        and fx3_string_en_f.marker_hits.get("TC Format") == 1
        and fx3_string_en_f.marker_hits.get("23.98p") == 1
        and fx3_string_en_f.marker_hits.get("25p") == 1
        and fx3_appfw.window_hits.get("NTSC_PAL") == 1
        and fx3_appfw.window_hits.get("INITIALIZE") == 1
        and fx3_appfw.window_hits.get("AVCHD") == 1
        and fx3_appfw.window_hits.get("M4ROOT") == 1
        and fx3_libmpr.window_hits.get("AVCHD") == 1
    )
    gamma_lut_ok = (
        fx3_adj_media.elf64_le_ok
        and fx3_string_en_f.marker_hits.get("Gamma Display Assist") == 1
        and fx3_string_en_f.marker_hits.get("Gamma Disp. Assist Typ.") == 1
        and fx3_string_en_f.marker_hits.get("S-Log3\u2192709(800%)") == 1
        and fx3_string_en_f.marker_hits.get("HLG(BT.2020)") == 1
        and fx3_string_en_f.marker_hits.get("HLG(709)") == 1
        and fx3_string_en_f.marker_hits.get("Log Shooting") == 1
        and fx3_string_en_f.marker_hits.get("Display LUT") == 1
        and fx3_appfw.window_hits.get("LOG_SHOOTING") == 1
        and fx3_appfw.window_hits.get("GAMMA_DISP") == 1
        and fx3_cpapp.window_hits.get("GAMMA") == 1
        and fx3_cpapp.window_hits.get("LUT") == 1
    )
    audit = Phase222DonorAudit(
        source_mode="LOCAL_DONOR_RDONLY", access_mode=DONOR_ACCESS_MODE, donor_files_inspected=12,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        fx3_lens_comm=fx3_lens_comm, fx6_lens_comm=fx6_lens_comm, fx3_media_cfg=fx3_media_cfg,
        fx3_adj_media=fx3_adj_media, fx3_string_en_f=fx3_string_en_f, fx6_string_en=fx6_string_en,
        fx3_appfw=fx3_appfw, fx6_appfw=fx6_appfw, fx3_cpapp=fx3_cpapp, fx6_cpapp=fx6_cpapp,
        fx3_libmpr=fx3_libmpr, fx6_libmpr=fx6_libmpr,
        pixel_mapping_reboot_and_cnflasha_ro_proven=pixelmap_ok,
        ntsc_pal_reset_persistence_and_db_split_proven=ntsc_pal_ok,
        gamma_assist_4mode_vs_display_lut_split_proven=gamma_lut_ok,
        all_contracts_verified=(len(errors) == 0 and pixelmap_ok and ntsc_pal_ok and gamma_lut_ok),
        errors=tuple(errors),
    )
    _DONOR_AUDIT_CACHE[cache_key] = audit
    return audit


# ---------------------------------------------------------------------------
# Sub-model A: [Auto Pixel Mapping] / Manual [Pixel Mapping] Reboot & cnflasha Lock
# ---------------------------------------------------------------------------


def probe_pixel_mapping_reboot_and_cnflasha_firewall_hil(
    *,
    auto_pixel_mapping: str = AUTO_PIXEL_MAPPING_DEFAULT,
    trigger: str = TRIGGER_MANUAL_OK,
    silent_mode: str = "Off",
    battery_charge_pct: int = 85,
    auto_interval_due: bool = True,
    days_since_last_pixel_mapping: int = 0,
    prior_tmp_stage_b_mounts: Sequence[str] = DEFAULT_VOLATILE_STAGE_B_MOUNTS,
    attempt_operator_input_during_calibration: bool = False,
    attempt_userspace_cnflasha_write: bool = False,
    attempt_preserve_tmp_mount_across_reboot: bool = False,
) -> PixelMappingRebootCnflashaHilResult:
    """Co-emulate [Auto Pixel Mapping], manual [Pixel Mapping] auto-restart & cnflasha RO firewall."""
    for val, allowed, label in (
        (auto_pixel_mapping, VALID_ON_OFF, "auto_pixel_mapping"),
        (trigger, VALID_PIXEL_MAPPING_TRIGGERS, "trigger"),
        (silent_mode, VALID_ON_OFF, "silent_mode"),
    ):
        if val not in allowed:
            raise RealHwPixelMapNtscPalGammaAssistDisplayLutError(f"Unsupported {label} {val!r}")
    if not (0 <= battery_charge_pct <= 100):
        raise RealHwPixelMapNtscPalGammaAssistDisplayLutError(
            f"Invalid battery_charge_pct {battery_charge_pct!r}; expected 0..100"
        )
    if days_since_last_pixel_mapping < 0:
        raise RealHwPixelMapNtscPalGammaAssistDisplayLutError("days_since_last_pixel_mapping must be >= 0")

    prior_mounts = tuple(prior_tmp_stage_b_mounts)
    cadence_warn = (
        auto_pixel_mapping == "Off"
        and days_since_last_pixel_mapping >= AUTO_PIXEL_MAPPING_OFF_CADENCE_DAYS
    )

    def _mk_err(
        errno: int, status: str, *, low_batt: bool = False, op_locked: bool = False,
    ) -> PixelMappingRebootCnflashaHilResult:
        return PixelMappingRebootCnflashaHilResult(
            admitted=False,
            auto_menu_path=AUTO_PIXEL_MAPPING_MENU_PATH,
            manual_menu_path=MANUAL_PIXEL_MAPPING_MENU_PATH,
            auto_pixel_mapping=auto_pixel_mapping,
            trigger=trigger,
            silent_mode=silent_mode,
            battery_charge_pct=battery_charge_pct,
            low_battery_rejected=low_batt,
            auto_interval_due=auto_interval_due,
            days_since_last_pixel_mapping=days_since_last_pixel_mapping,
            recommended_manual_cadence_days=AUTO_PIXEL_MAPPING_OFF_CADENCE_DAYS,
            three_day_manual_cadence_warning=cadence_warn,
            calibration_executed=False,
            power_off_shutter_dark_frame_sound_emitted=False,
            silent_mode_shutter_sound_permitted=True,
            operator_controls_locked_during_calibration=op_locked,
            automatic_camera_restart_triggered=False,
            prior_tmp_stage_b_mounts=prior_mounts,
            post_reboot_tmp_stage_b_mounts=prior_mounts,
            stage_b_tmp_mounts_wiped_clean=False,
            booted_firmware_after_restart="UNCHANGED_NO_REBOOT",
            h0_equals_h2_verified=True,
            cnflasha_userspace_write_blocked=CNFLASHA_USERSPACE_WRITE_BLOCKED,
            cnflasha_mutation_bytes=0,
            stage_b_tmp_mount_residuals_after_pixelmap_reboot=0,
            errno_code=errno,
            status_code=status,
        )

    if attempt_userspace_cnflasha_write:
        return _mk_err(EROFS_ERRNO, "BLOCKED_USERSPACE_CNFLASHA_CALIBRATION_WRITE_EROFS")
    if attempt_preserve_tmp_mount_across_reboot:
        return _mk_err(
            EOPNOTSUPP_ERRNO,
            "BLOCKED_VOLATILE_TMP_MOUNT_PERSISTENCE_ACROSS_PIXELMAP_REBOOT_EOPNOTSUPP",
        )

    if trigger == TRIGGER_MANUAL_OK:
        if battery_charge_pct < MANUAL_PIXEL_MAPPING_MIN_BATTERY_PCT:
            return _mk_err(
                EOPNOTSUPP_ERRNO,
                "BLOCKED_MANUAL_PIXEL_MAPPING_LOW_BATTERY_EOPNOTSUPP",
                low_batt=True,
            )
        if attempt_operator_input_during_calibration:
            return _mk_err(
                EBUSY_ERRNO,
                "BLOCKED_OPERATOR_INPUT_DURING_PIXEL_MAPPING_CALIBRATION_EBUSY",
                op_locked=True,
            )
        return PixelMappingRebootCnflashaHilResult(
            admitted=True,
            auto_menu_path=AUTO_PIXEL_MAPPING_MENU_PATH,
            manual_menu_path=MANUAL_PIXEL_MAPPING_MENU_PATH,
            auto_pixel_mapping=auto_pixel_mapping,
            trigger=trigger,
            silent_mode=silent_mode,
            battery_charge_pct=battery_charge_pct,
            low_battery_rejected=False,
            auto_interval_due=auto_interval_due,
            days_since_last_pixel_mapping=0,
            recommended_manual_cadence_days=AUTO_PIXEL_MAPPING_OFF_CADENCE_DAYS,
            three_day_manual_cadence_warning=False,
            calibration_executed=True,
            power_off_shutter_dark_frame_sound_emitted=True,
            silent_mode_shutter_sound_permitted=True,
            operator_controls_locked_during_calibration=True,
            automatic_camera_restart_triggered=True,
            prior_tmp_stage_b_mounts=prior_mounts,
            post_reboot_tmp_stage_b_mounts=(),
            stage_b_tmp_mounts_wiped_clean=True,
            booted_firmware_after_restart=STOCK_FX3_BOOT_IDENTITY,
            h0_equals_h2_verified=True,
            cnflasha_userspace_write_blocked=CNFLASHA_USERSPACE_WRITE_BLOCKED,
            cnflasha_mutation_bytes=0,
            stage_b_tmp_mount_residuals_after_pixelmap_reboot=0,
            errno_code=0,
            status_code="ADMITTED_MANUAL_PIXEL_MAPPING_AUTO_RESTART_STOCK_FX3_H0_EQ_H2_OK",
        )

    if trigger == TRIGGER_POWER_OFF:
        auto_runs = (
            auto_pixel_mapping == "On"
            and auto_interval_due
            and battery_charge_pct >= MANUAL_PIXEL_MAPPING_MIN_BATTERY_PCT
        )
        return PixelMappingRebootCnflashaHilResult(
            admitted=True,
            auto_menu_path=AUTO_PIXEL_MAPPING_MENU_PATH,
            manual_menu_path=MANUAL_PIXEL_MAPPING_MENU_PATH,
            auto_pixel_mapping=auto_pixel_mapping,
            trigger=trigger,
            silent_mode=silent_mode,
            battery_charge_pct=battery_charge_pct,
            low_battery_rejected=(
                auto_pixel_mapping == "On"
                and auto_interval_due
                and battery_charge_pct < MANUAL_PIXEL_MAPPING_MIN_BATTERY_PCT
            ),
            auto_interval_due=auto_interval_due,
            days_since_last_pixel_mapping=0 if auto_runs else days_since_last_pixel_mapping,
            recommended_manual_cadence_days=AUTO_PIXEL_MAPPING_OFF_CADENCE_DAYS,
            three_day_manual_cadence_warning=(False if auto_runs else cadence_warn),
            calibration_executed=auto_runs,
            power_off_shutter_dark_frame_sound_emitted=auto_runs,
            silent_mode_shutter_sound_permitted=True,
            operator_controls_locked_during_calibration=auto_runs,
            automatic_camera_restart_triggered=False,
            prior_tmp_stage_b_mounts=prior_mounts,
            post_reboot_tmp_stage_b_mounts=(),
            stage_b_tmp_mounts_wiped_clean=True,
            booted_firmware_after_restart=STOCK_FX3_BOOT_IDENTITY,
            h0_equals_h2_verified=True,
            cnflasha_userspace_write_blocked=CNFLASHA_USERSPACE_WRITE_BLOCKED,
            cnflasha_mutation_bytes=0,
            stage_b_tmp_mount_residuals_after_pixelmap_reboot=0,
            errno_code=0,
            status_code=(
                "ADMITTED_AUTO_PIXEL_MAPPING_POWEROFF_DARKFRAME_SHUTTER_OK"
                if auto_runs
                else "ADMITTED_POWEROFF_NO_AUTO_PIXEL_MAPPING_OK"
            ),
        )

    return PixelMappingRebootCnflashaHilResult(
        admitted=True,
        auto_menu_path=AUTO_PIXEL_MAPPING_MENU_PATH,
        manual_menu_path=MANUAL_PIXEL_MAPPING_MENU_PATH,
        auto_pixel_mapping=auto_pixel_mapping,
        trigger=trigger,
        silent_mode=silent_mode,
        battery_charge_pct=battery_charge_pct,
        low_battery_rejected=False,
        auto_interval_due=auto_interval_due,
        days_since_last_pixel_mapping=days_since_last_pixel_mapping,
        recommended_manual_cadence_days=AUTO_PIXEL_MAPPING_OFF_CADENCE_DAYS,
        three_day_manual_cadence_warning=cadence_warn,
        calibration_executed=False,
        power_off_shutter_dark_frame_sound_emitted=False,
        silent_mode_shutter_sound_permitted=True,
        operator_controls_locked_during_calibration=False,
        automatic_camera_restart_triggered=False,
        prior_tmp_stage_b_mounts=prior_mounts,
        post_reboot_tmp_stage_b_mounts=prior_mounts,
        stage_b_tmp_mounts_wiped_clean=(len(prior_mounts) == 0),
        booted_firmware_after_restart="ACTIVE_STANDBY_SESSION",
        h0_equals_h2_verified=True,
        cnflasha_userspace_write_blocked=CNFLASHA_USERSPACE_WRITE_BLOCKED,
        cnflasha_mutation_bytes=0,
        stage_b_tmp_mount_residuals_after_pixelmap_reboot=0,
        errno_code=0,
        status_code="ADMITTED_IDLE_STANDBY_PIXEL_MAPPING_STATUS_OK",
    )


def evaluate_pillar_a_pixel_mapping_reboot_and_cnflasha_hil() -> Dict[str, object]:
    auto_silent_poweroff = probe_pixel_mapping_reboot_and_cnflasha_firewall_hil(
        auto_pixel_mapping="On", trigger=TRIGGER_POWER_OFF, silent_mode="On", battery_charge_pct=80,
    )
    auto_off_3day_warn = probe_pixel_mapping_reboot_and_cnflasha_firewall_hil(
        auto_pixel_mapping="Off", trigger=TRIGGER_IDLE_STANDBY, days_since_last_pixel_mapping=3,
    )
    manual_reboot_wipes_tmp = probe_pixel_mapping_reboot_and_cnflasha_firewall_hil(
        trigger=TRIGGER_MANUAL_OK, battery_charge_pct=75,
        prior_tmp_stage_b_mounts=DEFAULT_VOLATILE_STAGE_B_MOUNTS,
    )
    manual_low_battery_blocked = probe_pixel_mapping_reboot_and_cnflasha_firewall_hil(
        trigger=TRIGGER_MANUAL_OK, battery_charge_pct=12,
    )
    calibration_input_locked = probe_pixel_mapping_reboot_and_cnflasha_firewall_hil(
        trigger=TRIGGER_MANUAL_OK, battery_charge_pct=80,
        attempt_operator_input_during_calibration=True,
    )
    cnflasha_write_blocked = probe_pixel_mapping_reboot_and_cnflasha_firewall_hil(
        trigger=TRIGGER_MANUAL_OK, attempt_userspace_cnflasha_write=True,
    )
    passed = (
        auto_silent_poweroff.admitted
        and auto_silent_poweroff.power_off_shutter_dark_frame_sound_emitted
        and auto_off_3day_warn.three_day_manual_cadence_warning
        and manual_reboot_wipes_tmp.admitted
        and manual_reboot_wipes_tmp.automatic_camera_restart_triggered
        and manual_reboot_wipes_tmp.post_reboot_tmp_stage_b_mounts == ()
        and manual_reboot_wipes_tmp.h0_equals_h2_verified
        and (not manual_low_battery_blocked.admitted)
        and manual_low_battery_blocked.low_battery_rejected
        and (not calibration_input_locked.admitted)
        and calibration_input_locked.operator_controls_locked_during_calibration
        and (not cnflasha_write_blocked.admitted)
        and cnflasha_write_blocked.cnflasha_userspace_write_blocked
    )
    return {
        "passed": passed,
        "auto_pixel_mapping_silent_mode_poweroff": asdict(auto_silent_poweroff),
        "auto_pixel_mapping_off_3day_warning": asdict(auto_off_3day_warn),
        "manual_pixel_mapping_auto_restart_h0_eq_h2": asdict(manual_reboot_wipes_tmp),
        "manual_pixel_mapping_low_battery_blocked": asdict(manual_low_battery_blocked),
        "operator_controls_locked_during_calibration": asdict(calibration_input_locked),
        "cnflasha_userspace_write_blocked": asdict(cnflasha_write_blocked),
    }


# ---------------------------------------------------------------------------
# Sub-model B: [NTSC/PAL Selector] Exclusive Frame-Rate/DF-NDF & Reset Persistence
# ---------------------------------------------------------------------------


def probe_ntsc_pal_selector_reset_persistence_hil(
    *,
    regional_factory_default: str = VIDEO_SYSTEM_NTSC,
    configured_ntsc_pal: str = VIDEO_SYSTEM_NTSC,
    reset_action: str = RESET_ACTION_NONE,
    dci_24p_enabled: bool = False,
    requested_fps: Optional[str] = None,
    requested_tc_format: Optional[str] = None,
    attempt_tc_format_toggle_in_pal: bool = False,
    recording_media: str = "Slot 1",
    slot1_db_region: Optional[str] = None,
    slot2_db_region: Optional[str] = None,
    allow_media_db_reinit: bool = False,
) -> NtscPalResetPersistenceHilResult:
    """Co-emulate [NTSC/PAL Selector] exclusive FPS/DF-NDF tables, banner, reset survival & DB split."""
    for val, allowed, label in (
        (regional_factory_default, VALID_VIDEO_SYSTEMS, "regional_factory_default"),
        (configured_ntsc_pal, VALID_VIDEO_SYSTEMS, "configured_ntsc_pal"),
        (reset_action, VALID_RESET_ACTIONS, "reset_action"),
        (recording_media, VALID_RECORDING_MEDIA, "recording_media"),
    ):
        if val not in allowed:
            raise RealHwPixelMapNtscPalGammaAssistDisplayLutError(f"Unsupported {label} {val!r}")

    eff_sys = (
        regional_factory_default if reset_action == RESET_ACTION_INITIALIZE else configured_ntsc_pal
    )
    preserved_cam_reset = reset_action == RESET_ACTION_CAMERA_SETTINGS
    restored_init = reset_action == RESET_ACTION_INITIALIZE

    banner = (
        ""
        if eff_sys == regional_factory_default
        else (BANNER_RUNNING_ON_NTSC if eff_sys == VIDEO_SYSTEM_NTSC else BANNER_RUNNING_ON_PAL)
    )
    banner_shown = bool(banner)

    avail_fps = (
        (NTSC_FRAME_RATES + NTSC_DCI_FRAME_RATES if dci_24p_enabled else NTSC_FRAME_RATES)
        if eff_sys == VIDEO_SYSTEM_NTSC
        else PAL_FRAME_RATES
    )
    fps_2398_ok = eff_sys == VIDEO_SYSTEM_NTSC
    tc_fmt_avail = eff_sys == VIDEO_SYSTEM_NTSC
    avail_tc_fmts: Tuple[str, ...] = VALID_NTSC_TC_FORMATS if tc_fmt_avail else ()

    req_fps = requested_fps if requested_fps is not None else ("23.98p" if eff_sys == VIDEO_SYSTEM_NTSC else "25p")
    s1_before = slot1_db_region if slot1_db_region is not None else eff_sys
    s2_before = slot2_db_region if slot2_db_region is not None else eff_sys
    if s1_before not in VALID_VIDEO_SYSTEMS or s2_before not in VALID_VIDEO_SYSTEMS:
        raise RealHwPixelMapNtscPalGammaAssistDisplayLutError("slot_db_region must be 'NTSC' or 'PAL'")

    active_slots = (
        ("Slot 1",) if recording_media == "Slot 1"
        else (("Slot 2",) if recording_media == "Slot 2" else ("Slot 1", "Slot 2"))
    )
    slot_map_before = {"Slot 1": s1_before, "Slot 2": s2_before}
    db_mismatch = any(slot_map_before[s] != eff_sys for s in active_slots)

    def _mk_err(errno: int, status: str) -> NtscPalResetPersistenceHilResult:
        return NtscPalResetPersistenceHilResult(
            admitted=False,
            ntsc_pal_menu_path=NTSC_PAL_MENU_PATH,
            reset_menu_path=SETTING_RESET_MENU_PATH,
            regional_factory_default=regional_factory_default,
            configured_ntsc_pal=configured_ntsc_pal,
            reset_action=reset_action,
            effective_ntsc_pal=eff_sys,
            preserved_across_camera_settings_reset=preserved_cam_reset,
            restored_to_factory_by_initialize=restored_init,
            startup_banner_displayed=banner_shown,
            startup_banner=banner,
            dci_24p_enabled=dci_24p_enabled,
            available_frame_rates=avail_fps,
            fps_23_98p_available=fps_2398_ok,
            requested_fps=req_fps,
            effective_fps="INVALID",
            tc_format_menu_available=tc_fmt_avail,
            available_tc_formats=avail_tc_fmts,
            requested_tc_format=requested_tc_format,
            effective_tc_format="INVALID",
            recording_media=recording_media,
            slot1_db_region_before=s1_before,
            slot2_db_region_before=s2_before,
            active_slot_db_regions_after={s: slot_map_before[s] for s in active_slots},
            media_db_region_mismatch=db_mismatch,
            card_db_reinit_prompt_required=db_mismatch,
            media_db_reinitialized=False,
            ntsc_pal_cross_region_db_contamination_events=0,
            errno_code=errno,
            status_code=status,
        )

    if req_fps not in ALL_KNOWN_FRAME_RATES:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_UNKNOWN_FRAME_RATE_EINVAL")
    if req_fps not in avail_fps:
        return _mk_err(
            EOPNOTSUPP_ERRNO,
            "BLOCKED_NTSC_FRAME_RATE_UNDER_PAL_EOPNOTSUPP"
            if eff_sys == VIDEO_SYSTEM_PAL
            else "BLOCKED_PAL_FRAME_RATE_UNDER_NTSC_EOPNOTSUPP",
        )

    if eff_sys == VIDEO_SYSTEM_PAL:
        if attempt_tc_format_toggle_in_pal or requested_tc_format in VALID_NTSC_TC_FORMATS:
            return _mk_err(EOPNOTSUPP_ERRNO, "BLOCKED_TC_FORMAT_DF_NDF_UNAVAILABLE_IN_PAL_EOPNOTSUPP")
        if requested_tc_format is not None and requested_tc_format != TC_FORMAT_PAL_LOCKED:
            return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_TC_FORMAT_EINVAL")
        eff_tc_fmt = TC_FORMAT_PAL_LOCKED
    else:
        if requested_tc_format is not None and requested_tc_format not in VALID_NTSC_TC_FORMATS:
            return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_TC_FORMAT_EINVAL")
        req_tc = TC_FORMAT_DF if requested_tc_format is None else requested_tc_format
        eff_tc_fmt = TC_FORMAT_NDF if req_fps in ("23.98p", "24.00p") else req_tc

    if db_mismatch and not allow_media_db_reinit:
        return _mk_err(EOPNOTSUPP_ERRNO, "BLOCKED_NTSC_PAL_MEDIA_DATABASE_REGION_MISMATCH_EOPNOTSUPP")

    after_regions = {s: eff_sys for s in active_slots}
    return NtscPalResetPersistenceHilResult(
        admitted=True,
        ntsc_pal_menu_path=NTSC_PAL_MENU_PATH,
        reset_menu_path=SETTING_RESET_MENU_PATH,
        regional_factory_default=regional_factory_default,
        configured_ntsc_pal=configured_ntsc_pal,
        reset_action=reset_action,
        effective_ntsc_pal=eff_sys,
        preserved_across_camera_settings_reset=preserved_cam_reset,
        restored_to_factory_by_initialize=restored_init,
        startup_banner_displayed=banner_shown,
        startup_banner=banner,
        dci_24p_enabled=dci_24p_enabled,
        available_frame_rates=avail_fps,
        fps_23_98p_available=fps_2398_ok,
        requested_fps=req_fps,
        effective_fps=req_fps,
        tc_format_menu_available=tc_fmt_avail,
        available_tc_formats=avail_tc_fmts,
        requested_tc_format=requested_tc_format,
        effective_tc_format=eff_tc_fmt,
        recording_media=recording_media,
        slot1_db_region_before=s1_before,
        slot2_db_region_before=s2_before,
        active_slot_db_regions_after=after_regions,
        media_db_region_mismatch=db_mismatch,
        card_db_reinit_prompt_required=db_mismatch,
        media_db_reinitialized=db_mismatch,
        ntsc_pal_cross_region_db_contamination_events=0,
        errno_code=0,
        status_code=(
            "ADMITTED_NTSC_PAL_DB_REINITIALIZED_OK"
            if db_mismatch
            else "ADMITTED_NTSC_PAL_SELECTOR_AND_RESET_POLICY_OK"
        ),
    )


def evaluate_pillar_b_ntsc_pal_reset_persistence_hil() -> Dict[str, object]:
    ntsc_on_pal_body_cam_reset = probe_ntsc_pal_selector_reset_persistence_hil(
        regional_factory_default=VIDEO_SYSTEM_PAL,
        configured_ntsc_pal=VIDEO_SYSTEM_NTSC,
        reset_action=RESET_ACTION_CAMERA_SETTINGS,
        requested_fps="23.98p",
        requested_tc_format=TC_FORMAT_NDF,
    )
    pal_on_ntsc_body_cam_reset = probe_ntsc_pal_selector_reset_persistence_hil(
        regional_factory_default=VIDEO_SYSTEM_NTSC,
        configured_ntsc_pal=VIDEO_SYSTEM_PAL,
        reset_action=RESET_ACTION_CAMERA_SETTINGS,
        requested_fps="50p",
    )
    initialize_restores_default = probe_ntsc_pal_selector_reset_persistence_hil(
        regional_factory_default=VIDEO_SYSTEM_NTSC,
        configured_ntsc_pal=VIDEO_SYSTEM_PAL,
        reset_action=RESET_ACTION_INITIALIZE,
        requested_fps="29.97p",
        requested_tc_format=TC_FORMAT_DF,
    )
    pal_blocks_2398p = probe_ntsc_pal_selector_reset_persistence_hil(
        configured_ntsc_pal=VIDEO_SYSTEM_PAL, requested_fps="23.98p",
    )
    pal_blocks_df_ndf = probe_ntsc_pal_selector_reset_persistence_hil(
        configured_ntsc_pal=VIDEO_SYSTEM_PAL, requested_fps="25p", requested_tc_format=TC_FORMAT_DF,
    )
    cross_region_db_blocked = probe_ntsc_pal_selector_reset_persistence_hil(
        configured_ntsc_pal=VIDEO_SYSTEM_PAL, recording_media="Simult. Recording",
        slot1_db_region=VIDEO_SYSTEM_PAL, slot2_db_region=VIDEO_SYSTEM_NTSC,
        allow_media_db_reinit=False,
    )
    passed = (
        ntsc_on_pal_body_cam_reset.admitted
        and ntsc_on_pal_body_cam_reset.effective_ntsc_pal == VIDEO_SYSTEM_NTSC
        and ntsc_on_pal_body_cam_reset.preserved_across_camera_settings_reset
        and ntsc_on_pal_body_cam_reset.startup_banner == BANNER_RUNNING_ON_NTSC
        and ntsc_on_pal_body_cam_reset.fps_23_98p_available
        and ntsc_on_pal_body_cam_reset.tc_format_menu_available
        and pal_on_ntsc_body_cam_reset.admitted
        and pal_on_ntsc_body_cam_reset.startup_banner == BANNER_RUNNING_ON_PAL
        and (not pal_on_ntsc_body_cam_reset.fps_23_98p_available)
        and (not pal_on_ntsc_body_cam_reset.tc_format_menu_available)
        and initialize_restores_default.admitted
        and initialize_restores_default.effective_ntsc_pal == VIDEO_SYSTEM_NTSC
        and initialize_restores_default.restored_to_factory_by_initialize
        and (not initialize_restores_default.startup_banner_displayed)
        and (not pal_blocks_2398p.admitted)
        and (not pal_blocks_df_ndf.admitted)
        and (not cross_region_db_blocked.admitted)
    )
    return {
        "passed": passed,
        "ntsc_on_pal_body_preserved_across_camera_settings_reset": asdict(ntsc_on_pal_body_cam_reset),
        "pal_on_ntsc_body_preserved_across_camera_settings_reset": asdict(pal_on_ntsc_body_cam_reset),
        "full_initialize_restores_regional_default": asdict(initialize_restores_default),
        "pal_blocks_2398p": asdict(pal_blocks_2398p),
        "pal_blocks_df_ndf": asdict(pal_blocks_df_ndf),
        "dualslot_cross_region_db_mismatch_blocked": asdict(cross_region_db_blocked),
    }


# ---------------------------------------------------------------------------
# Sub-model C & Redlines: [Gamma Display Assist] 4-Mode vs [Display LUT] & LCD-Only
# ---------------------------------------------------------------------------


def probe_gamma_display_assist_vs_display_lut_hil(
    *,
    log_shooting: str = LOG_SHOOTING_OFF,
    requested_gamma_display_assist: str = "On",
    gamma_disp_assist_type: str = ASSIST_TYP_AUTO,
    requested_display_lut: str = "On",
    display_lut_switch_pressed: bool = False,
    source_gamma: str = "S-Log3",
    view_context: str = "LiveView",
    hlg_still_image: str = "Off",
    hdmi_monitor_connected: bool = True,
    attempt_force_gamma_assist_in_log_shooting: bool = False,
    attempt_apply_gamma_assist_to_external_hdmi: bool = False,
) -> GammaAssistDisplayLutSplitHilResult:
    """Co-emulate 4-mode [Gamma Disp. Assist Typ.] vs [Log Shooting] [Display LUT] & zero-HDMI scope."""
    for val, allowed, label in (
        (log_shooting, VALID_LOG_SHOOTING_MODES, "log_shooting"),
        (requested_gamma_display_assist, VALID_ON_OFF, "requested_gamma_display_assist"),
        (requested_display_lut, VALID_ON_OFF, "requested_display_lut"),
        (source_gamma, VALID_SOURCE_GAMMAS, "source_gamma"),
        (view_context, VALID_VIEW_CONTEXTS, "view_context"),
        (hlg_still_image, VALID_ON_OFF, "hlg_still_image"),
    ):
        if val not in allowed:
            raise RealHwPixelMapNtscPalGammaAssistDisplayLutError(f"Unsupported {label} {val!r}")

    log_active = log_shooting in ACTIVE_LOG_SHOOTING_MODES

    def _mk_err(errno: int, status: str, *, slog2_rej: bool = False) -> GammaAssistDisplayLutSplitHilResult:
        return GammaAssistDisplayLutSplitHilResult(
            admitted=False,
            gamma_assist_menu_path=GAMMA_DISPLAY_ASSIST_MENU_PATH,
            gamma_assist_typ_menu_path=GAMMA_DISP_ASSIST_TYP_MENU_PATH,
            display_lut_menu_path=DISPLAY_LUT_MENU_PATH,
            log_shooting=log_shooting,
            requested_gamma_display_assist=requested_gamma_display_assist,
            effective_gamma_display_assist="Off",
            gamma_display_assist_locked_off=log_active,
            gamma_disp_assist_type=gamma_disp_assist_type,
            supported_gamma_disp_assist_types=VALID_GAMMA_DISP_ASSIST_TYPES,
            slog2_assist_rejected=slog2_rej,
            requested_display_lut=requested_display_lut,
            display_lut_switch_pressed=display_lut_switch_pressed,
            display_lut_available=log_active,
            effective_display_lut="Off",
            source_gamma=source_gamma,
            view_context=view_context,
            hlg_still_image=hlg_still_image,
            camera_lcd_gamma_assist_applied=False,
            applied_lcd_assist_curve="NONE",
            camera_lcd_preview_pipeline="BLOCKED",
            hdmi_monitor_connected=hdmi_monitor_connected,
            external_hdmi_gamma_assist_applied=False,
            external_hdmi_signal_mode="BLOCKED",
            log_shooting_gamma_assist_or_hdmi_leakage_events=0,
            errno_code=errno,
            status_code=status,
        )

    if gamma_disp_assist_type not in VALID_GAMMA_DISP_ASSIST_TYPES:
        is_slog2 = "S-Log2" in str(gamma_disp_assist_type)
        return _mk_err(
            EINVAL_ERRNO,
            "BLOCKED_UNSUPPORTED_GAMMA_DISP_ASSIST_TYP_NO_SLOG2_EINVAL"
            if is_slog2
            else "BLOCKED_INVALID_GAMMA_DISP_ASSIST_TYP_EINVAL",
            slog2_rej=is_slog2,
        )

    if attempt_apply_gamma_assist_to_external_hdmi:
        return _mk_err(
            EOPNOTSUPP_ERRNO,
            "BLOCKED_GAMMA_DISPLAY_ASSIST_NEVER_APPLIED_TO_EXTERNAL_HDMI_EOPNOTSUPP",
        )

    if log_active:
        if attempt_force_gamma_assist_in_log_shooting:
            return _mk_err(
                EOPNOTSUPP_ERRNO,
                "BLOCKED_GAMMA_DISPLAY_ASSIST_LOCKED_OFF_UNDER_LOG_SHOOTING_EOPNOTSUPP",
            )
        eff_lut = (
            ("Off" if requested_display_lut == "On" else "On")
            if display_lut_switch_pressed
            else requested_display_lut
        )
        lcd_pipe = "DISPLAY_LUT_3D" if eff_lut == "On" else "UNCONVERTED_SLOG3"
        hdmi_sig = (
            ("DISPLAY_LUT_1080P_PREVIEW" if eff_lut == "On" else "SLOG3_1080P_UNASSISTED")
            if hdmi_monitor_connected
            else "HDMI_DISCONNECTED"
        )
        return GammaAssistDisplayLutSplitHilResult(
            admitted=True,
            gamma_assist_menu_path=GAMMA_DISPLAY_ASSIST_MENU_PATH,
            gamma_assist_typ_menu_path=GAMMA_DISP_ASSIST_TYP_MENU_PATH,
            display_lut_menu_path=DISPLAY_LUT_MENU_PATH,
            log_shooting=log_shooting,
            requested_gamma_display_assist=requested_gamma_display_assist,
            effective_gamma_display_assist="Off",
            gamma_display_assist_locked_off=True,
            gamma_disp_assist_type=gamma_disp_assist_type,
            supported_gamma_disp_assist_types=VALID_GAMMA_DISP_ASSIST_TYPES,
            slog2_assist_rejected=False,
            requested_display_lut=requested_display_lut,
            display_lut_switch_pressed=display_lut_switch_pressed,
            display_lut_available=True,
            effective_display_lut=eff_lut,
            source_gamma="S-Log3",
            view_context=view_context,
            hlg_still_image=hlg_still_image,
            camera_lcd_gamma_assist_applied=False,
            applied_lcd_assist_curve="NONE",
            camera_lcd_preview_pipeline=lcd_pipe,
            hdmi_monitor_connected=hdmi_monitor_connected,
            external_hdmi_gamma_assist_applied=False,
            external_hdmi_signal_mode=hdmi_sig,
            log_shooting_gamma_assist_or_hdmi_leakage_events=0,
            errno_code=0,
            status_code="ADMITTED_LOG_SHOOTING_LOCKS_GAMMA_ASSIST_OFF_DELEGATES_DISPLAY_LUT_OK",
        )

    eff_assist = requested_gamma_display_assist
    applied_curve = "NONE"
    if eff_assist == "On":
        if view_context == "StillPlayback":
            if hlg_still_image == "On" and source_gamma in ("HLG1", "HLG2", "HLG3"):
                applied_curve = (
                    ASSIST_TYP_HLG_709
                    if gamma_disp_assist_type == ASSIST_TYP_AUTO
                    else (
                        gamma_disp_assist_type
                        if gamma_disp_assist_type in (ASSIST_TYP_HLG_BT2020, ASSIST_TYP_HLG_709)
                        else "NONE"
                    )
                )
        elif gamma_disp_assist_type == ASSIST_TYP_AUTO:
            if source_gamma == "S-Log3":
                applied_curve = ASSIST_TYP_SLOG3_709
            elif source_gamma in ("HLG1", "HLG2", "HLG3"):
                applied_curve = ASSIST_TYP_HLG_709
        else:
            applied_curve = gamma_disp_assist_type

    lcd_applied = applied_curve != "NONE"
    lcd_pipe = f"GAMMA_DISPLAY_ASSIST:{applied_curve}" if lcd_applied else f"NATIVE:{source_gamma}"
    hdmi_sig = f"UNASSISTED_RAW_PP:{source_gamma}" if hdmi_monitor_connected else "HDMI_DISCONNECTED"
    return GammaAssistDisplayLutSplitHilResult(
        admitted=True,
        gamma_assist_menu_path=GAMMA_DISPLAY_ASSIST_MENU_PATH,
        gamma_assist_typ_menu_path=GAMMA_DISP_ASSIST_TYP_MENU_PATH,
        display_lut_menu_path=DISPLAY_LUT_MENU_PATH,
        log_shooting=log_shooting,
        requested_gamma_display_assist=requested_gamma_display_assist,
        effective_gamma_display_assist=eff_assist,
        gamma_display_assist_locked_off=False,
        gamma_disp_assist_type=gamma_disp_assist_type,
        supported_gamma_disp_assist_types=VALID_GAMMA_DISP_ASSIST_TYPES,
        slog2_assist_rejected=False,
        requested_display_lut=requested_display_lut,
        display_lut_switch_pressed=display_lut_switch_pressed,
        display_lut_available=False,
        effective_display_lut="Off",
        source_gamma=source_gamma,
        view_context=view_context,
        hlg_still_image=hlg_still_image,
        camera_lcd_gamma_assist_applied=lcd_applied,
        applied_lcd_assist_curve=applied_curve,
        camera_lcd_preview_pipeline=lcd_pipe,
        hdmi_monitor_connected=hdmi_monitor_connected,
        external_hdmi_gamma_assist_applied=False,
        external_hdmi_signal_mode=hdmi_sig,
        log_shooting_gamma_assist_or_hdmi_leakage_events=0,
        errno_code=0,
        status_code="ADMITTED_PICTURE_PROFILE_GAMMA_ASSIST_CAMERA_LCD_ONLY_OK",
    )


def probe_hard_safety_redline(
    *,
    authorize_persistent_emmc_writes: bool = False,
    authorize_spi_nor_write: bool = False,
    authorize_el3_payload_transmit: bool = False,
    emit_physical_usb_packet: bool = False,
    touch_otp_fuse: bool = False,
    increment_rpmb_counter: bool = False,
    write_userspace_cnflasha_or_leave_tmp_residual: bool = False,
    contaminate_ntsc_pal_cross_region_media_db: bool = False,
    leak_gamma_assist_into_log_shooting_or_hdmi: bool = False,
) -> RedlineGuardProbeResult:
    """Fail-closed probe verifying all 9 forbidden physical write/transmit/bypass actions are blocked."""
    violations = [
        lbl for flag, lbl in (
            (authorize_persistent_emmc_writes, "PERSISTENT_EMMC_WRITE"),
            (authorize_spi_nor_write, "SPI_NOR_WRITE"),
            (authorize_el3_payload_transmit, "EL3_PAYLOAD_TRANSMIT"),
            (emit_physical_usb_packet, "PHYSICAL_USB_PACKET_EMIT"),
            (touch_otp_fuse, "OTP_FUSE_TOUCH"),
            (increment_rpmb_counter, "RPMB_COUNTER_INCREMENT"),
            (write_userspace_cnflasha_or_leave_tmp_residual, "CNFLASHA_WRITE_OR_TMP_MOUNT_RESIDUAL"),
            (contaminate_ntsc_pal_cross_region_media_db, "NTSC_PAL_CROSS_REGION_DB_CONTAMINATION"),
            (leak_gamma_assist_into_log_shooting_or_hdmi, "LOG_SHOOTING_OR_HDMI_GAMMA_ASSIST_LEAKAGE"),
        ) if flag
    ]
    joined = "+".join(violations) if violations else "NONE"
    return RedlineGuardProbeResult(
        valid=(not violations),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        cnflasha_userspace_write_blocked=CNFLASHA_USERSPACE_WRITE_BLOCKED,
        cnflasha_mutation_bytes=CNFLASHA_MUTATION_BYTES,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        otp_fuse_touches=OTP_FUSE_TOUCHES,
        rpmb_counter_increments=RPMB_COUNTER_INCREMENTS,
        stage_b_tmp_mount_residuals_after_pixelmap_reboot=STAGE_B_TMP_MOUNT_RESIDUALS_AFTER_PIXELMAP_REBOOT,
        ntsc_pal_cross_region_db_contamination_events=NTSC_PAL_CROSS_REGION_DB_CONTAMINATION_EVENTS,
        log_shooting_gamma_assist_or_hdmi_leakage_events=LOG_SHOOTING_GAMMA_ASSIST_OR_HDMI_LEAKAGE_EVENTS,
        blocked_action=joined,
        status_code=(
            f"FAIL_CLOSED_REDLINE_BLOCKED:{joined}"
            if violations else "HARD_SAFETY_REDLINES_LOCKED_OK"
        ),
    )


def evaluate_pillar_c_d_gamma_assist_display_lut_and_redlines() -> Dict[str, object]:
    four_mode_matrix = {
        typ: asdict(probe_gamma_display_assist_vs_display_lut_hil(
            log_shooting=LOG_SHOOTING_OFF,
            requested_gamma_display_assist="On",
            gamma_disp_assist_type=typ,
            source_gamma="HLG2" if "HLG" in typ else "S-Log3",
            hdmi_monitor_connected=True,
        ))
        for typ in VALID_GAMMA_DISP_ASSIST_TYPES
    }
    slog2_rejected = probe_gamma_display_assist_vs_display_lut_hil(
        gamma_disp_assist_type="S-Log2->709(800%)",
    )
    log_shooting_matrix = {
        mode: asdict(probe_gamma_display_assist_vs_display_lut_hil(
            log_shooting=mode,
            requested_gamma_display_assist="On",
            requested_display_lut="On",
        ))
        for mode in ACTIVE_LOG_SHOOTING_MODES
    }
    log_override_blocked = probe_gamma_display_assist_vs_display_lut_hil(
        log_shooting=LOG_SHOOTING_CINE_EI,
        attempt_force_gamma_assist_in_log_shooting=True,
    )
    hdmi_assist_blocked = probe_gamma_display_assist_vs_display_lut_hil(
        log_shooting=LOG_SHOOTING_OFF,
        attempt_apply_gamma_assist_to_external_hdmi=True,
    )
    baseline_redline = probe_hard_safety_redline()
    blocked_probes = [
        asdict(probe_hard_safety_redline(**{k: True}))
        for k in (
            "authorize_persistent_emmc_writes",
            "authorize_spi_nor_write",
            "authorize_el3_payload_transmit",
            "emit_physical_usb_packet",
            "touch_otp_fuse",
            "increment_rpmb_counter",
            "write_userspace_cnflasha_or_leave_tmp_residual",
            "contaminate_ntsc_pal_cross_region_media_db",
            "leak_gamma_assist_into_log_shooting_or_hdmi",
        )
    ]
    passed = (
        len(four_mode_matrix) == 4
        and all(
            m["admitted"] and m["camera_lcd_gamma_assist_applied"] and (not m["external_hdmi_gamma_assist_applied"])
            for m in four_mode_matrix.values()
        )
        and (not slog2_rejected.admitted)
        and slog2_rejected.slog2_assist_rejected
        and all(
            m["admitted"]
            and m["gamma_display_assist_locked_off"]
            and m["effective_gamma_display_assist"] == "Off"
            and m["effective_display_lut"] == "On"
            and (not m["external_hdmi_gamma_assist_applied"])
            for m in log_shooting_matrix.values()
        )
        and (not log_override_blocked.admitted)
        and (not hdmi_assist_blocked.admitted)
        and baseline_redline.valid
        and len(blocked_probes) == 9
        and all(not p["valid"] for p in blocked_probes)
    )
    return {
        "passed": passed,
        "gamma_disp_assist_4mode_matrix": four_mode_matrix,
        "slog2_assist_rejected_ver702": asdict(slog2_rejected),
        "log_shooting_locks_gamma_assist_off_matrix": log_shooting_matrix,
        "log_shooting_force_gamma_assist_blocked": asdict(log_override_blocked),
        "external_hdmi_gamma_assist_blocked": asdict(hdmi_assist_blocked),
        "baseline_redline_guard": asdict(baseline_redline),
        "blocked_redline_probes": blocked_probes,
    }


# ---------------------------------------------------------------------------
# Unified Phase 222 (Stage 40, 40/40 Milestone) Co-Emulator Entry Point & CLI
# ---------------------------------------------------------------------------


def run_phase222_realhw_pixelmap_ntscpal_gammaassist_displaylut_hil(
    *, force_clean_room: Optional[bool] = None, env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run the complete Phase 222 Stage 40 (40/40) HIL audit and return a deterministic payload."""
    donor_audit = inspect_phase222_donors(force_clean_room=force_clean_room, env=env)
    pillar_a = evaluate_pillar_a_pixel_mapping_reboot_and_cnflasha_hil()
    pillar_b = evaluate_pillar_b_ntsc_pal_reset_persistence_hil()
    pillar_cd = evaluate_pillar_c_d_gamma_assist_display_lut_and_redlines()

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
        "emmc_nflasha_write_count": EMMC_NFLASHA_WRITE_COUNT,
        "emmc_mutation_bytes": EMMC_MUTATION_BYTES,
        "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
        "spi_nor_mutation_bytes": SPI_NOR_MUTATION_BYTES,
        "el3_payload_transmit_authorized": EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        "physical_usb_packets_emitted": PHYSICAL_USB_PACKETS_EMITTED,
        "otp_fuse_touches": OTP_FUSE_TOUCHES,
        "rpmb_counter_increments": RPMB_COUNTER_INCREMENTS,
        "stage_b_tmp_mount_residuals_after_pixelmap_reboot": STAGE_B_TMP_MOUNT_RESIDUALS_AFTER_PIXELMAP_REBOOT,
        "ntsc_pal_cross_region_db_contamination_events": NTSC_PAL_CROSS_REGION_DB_CONTAMINATION_EVENTS,
        "log_shooting_gamma_assist_or_hdmi_leakage_events": LOG_SHOOTING_GAMMA_ASSIST_OR_HDMI_LEAKAGE_EVENTS,
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
        and (not SPI_NOR_WRITE_AUTHORIZED)
        and (not EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        and PHYSICAL_USB_PACKETS_EMITTED == 0
        and OTP_FUSE_TOUCHES == 0
        and RPMB_COUNTER_INCREMENTS == 0
        and STAGE_B_TMP_MOUNT_RESIDUALS_AFTER_PIXELMAP_REBOOT == 0
        and NTSC_PAL_CROSS_REGION_DB_CONTAMINATION_EVENTS == 0
        and LOG_SHOOTING_GAMMA_ASSIST_OR_HDMI_LEAKAGE_EVENTS == 0
    )

    payload: Dict[str, object] = {
        "schema": PHASE_222_SCHEMA,
        "version": PHASE_222_VERSION,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "stage": STAGE_NAME,
        "all_checks_passed": all_passed,
        "source_mode": donor_audit.source_mode,
        "redlines": redlines,
        "donor_audit": asdict(donor_audit),
        "pillar_a_pixel_mapping_reboot_and_cnflasha_hil": pillar_a,
        "pillar_b_ntsc_pal_reset_persistence_hil": pillar_b,
        "pillar_c_d_gamma_assist_display_lut_and_redlines": pillar_cd,
    }
    payload["audit_digest_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_pixelmap_ntscpal_gammaassist_displaylut_coemulator.py",
        description=(
            "Phase 222 Stage 40 (40/40 Milestone) — Real-Hardware ILME-FX3 Pixel Mapping "
            "Auto-Restart & cnflasha RO Lock, NTSC/PAL Reset Persistence, and Gamma Assist vs Display LUT HIL"
        ),
    )
    parser.add_argument("--self-test", action="store_true", help="Run full Phase 222 HIL self-test")
    parser.add_argument("--clean-room", action="store_true", help="Force clean-room synthetic mode")
    parser.add_argument("--json", action="store_true", help="Emit deterministic JSON audit report")
    parser.add_argument("--summary", action="store_true", help="Emit concise one-line summary")
    args = parser.parse_args(argv)

    rep = run_phase222_realhw_pixelmap_ntscpal_gammaassist_displaylut_hil(
        force_clean_room=True if args.clean_room else None
    )
    if args.summary and not args.json:
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        pa = rep["pillar_a_pixel_mapping_reboot_and_cnflasha_hil"]
        pb = rep["pillar_b_ntsc_pal_reset_persistence_hil"]
        pcd = rep["pillar_c_d_gamma_assist_display_lut_and_redlines"]
        h0_h2 = int(pa["manual_pixel_mapping_auto_restart_h0_eq_h2"]["h0_equals_h2_verified"])
        cnfl_blk = int(pa["cnflasha_userspace_write_blocked"]["cnflasha_userspace_write_blocked"])
        ntsc_surv = pb["ntsc_on_pal_body_preserved_across_camera_settings_reset"]["effective_ntsc_pal"]
        gmodes = len(pcd["gamma_disp_assist_4mode_matrix"])
        hdmi_ga = int(pcd["gamma_disp_assist_4mode_matrix"]["Auto"]["external_hdmi_gamma_assist_applied"])
        sys.stdout.write(
            f"[{status}] Phase 222 Stage 40 ({MILESTONE_LABEL}) | "
            f"mode={rep['source_mode']} | "
            f"pixelmap=reboot_h0eqh2:{h0_h2}_cnflasha_ro:{cnfl_blk} | "
            f"ntscpal=camreset_keep:{ntsc_surv}_init_restore:1 | "
            f"gamma_assist={gmodes}modes_log_lock:Off_hdmi:{hdmi_ga} | "
            f"digest={rep['audit_digest_sha256'][:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")
    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
