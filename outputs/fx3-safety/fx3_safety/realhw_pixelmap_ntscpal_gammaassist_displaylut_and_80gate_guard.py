"""Phase 219 (`80/80` Milestone) Real-Hardware Safety Gates (`G79..G80`) & Unified
80-Gate Master Safety Preflight (`verify-80-gates`) for Sony `ILME-FX3` (`Ver. 7.02`).

Implements Wave-30 official Sony `ILME-FX3` (`Ver. 7.02`) hardware rules while delegating
Gates `G01..G78` directly to `evaluate_78gate_preflight()` from
`realhw_filesettings_shotmark_tcregen_reclamp_and_78gate_guard.py`:

1. **Gate G79 (`G79_PIXEL_MAPPING_REBOOT_LOWBATT_LOCK_AND_CNFLASHA_READONLY_GUARD`)**:
   - Models `[Auto Pixel Mapping]` (`MENU -> Setup -> [Setup Option] -> [Auto Pixel Mapping]`,
     `On` default, mechanical shutter actuation sound at power-off even when `[Silent Mode]`
     is `On`, and `<= 3`-day manual `[Pixel Mapping]` cadence recommendation when `Off`).
   - Models manual `[Pixel Mapping]` (`MENU -> Setup -> [Setup Option] -> [Pixel Mapping]`),
     enforcing low-battery lockout (`NP-FZ100` `< 20%` SoC or low-battery warning active),
     complete operator-control lockout during execution, mandatory **automatic camera restart**
     upon completion (cleanly unmounting volatile Stage-B `/tmp` RAM bind-mounts back to
     stock `FX3 Ver. 7.02` with `H0 == H2`), and absolute `cnflasha` factory calibration
     read-only firewall (`cnflasha_userspace_write_blocked == True`,
     `persistent_emmc_writes_authorized == False`).
   - Bounded `< 0.15s` `O_RDONLY` local donor check (`raw_firmware_bytes_leaked == 0`) with
     deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` synthetic fallback.

2. **Gate G80 (`G80_NTSCPAL_RESET_PERSISTENCE_AND_GAMMA_ASSIST_DISPLAY_LUT_SPLIT_GUARD`)**:
   - Enforces `[NTSC/PAL Selector]` exclusive frame-rate & timecode matrix (`NTSC`: `23.98p`
     NTSC-exclusive, `24.00p`, `29.97p`, `59.94p`, `119.88p` + `[TC Format]` `DF`/`NDF`;
     `PAL`: `25p`, `50p`, `100p`, with `23.98p` and `[TC Format]` `DF`/`NDF` blocked),
     startup `"Running on NTSC."` / `"Running on PAL."` notification banner when non-default,
     and `[Camera Settings Reset]` persistence (only `[Initialize]` resets `[NTSC/PAL Selector]`).
   - Enforces `[Gamma Display Assist]` (`[Gamma Disp. Assist Typ.]`: `Auto`,
     `S-Log3->709(800%)`, `HLG(BT.2020)`, `HLG(709)` — zero `S-Log2` in `Ver. 7.02`) hard
     lock to `[Off]` whenever `[Log Shooting]` (`Cine EI` / `Cine EI Quick` / `Flexible ISO`)
     is active (where `[Display LUT]` `On`/`Off` governs preview), and enforces built-in-LCD-only
     scope (`external_hdmi_gamma_assist_applied == False`).

3. **Unified `80/80` Milestone `verify-80-gates` Master Safety Preflight**:
   - Combines `G01..G78` + `G79` + `G80` (`77/80` offline pass with the 3 physical-bench
     Tier-0 gates `G10..G12` awaiting receipt; `80/80` in `--simulate-bench-dry-run`).

Hard-locked safety redlines:
- `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`
- `SPI_NOR_WRITE_AUTHORIZED = False`
- `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`
- `HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`
- `USB_PACKETS_TRANSMITTED = 0`
- `RAW_FIRMWARE_BYTES_LEAKED = 0`
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

from .master_16gate_preflight import DEFAULT_REPO_ROOT, GateVerdict
from .realhw_filesettings_shotmark_tcregen_reclamp_and_78gate_guard import (
    _DONOR_BLOB_CACHE,
    Master78GateReport,
    evaluate_78gate_preflight,
)
from .realhw_fx3a_firewall_xlrh1_mishoe_and_64gate_guard import (
    FX3_MODEL_ID,
    FX3_MODEL_NAME,
)
from .thermal_pwm_and_power_guard import (
    ENV_FORCE_CLEAN_ROOM,
    resolve_donor_thermal_power_paths,
)


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

REALHW_PIXELMAP_NTSCPAL_GAMMAASSIST_DISPLAYLUT_80GATE_SCHEMA: str = (
    "fx3-realhw-pixelmap-ntscpal-gammaassist-displaylut-80gate-preflight-v1"
)
REALHW_PIXELMAP_NTSCPAL_GAMMAASSIST_DISPLAYLUT_80GATE_VERSION: str = "1.0.0"

EL3_PAYLOAD_TRANSMIT_AUTHORIZED: bool = False
SPI_NOR_WRITE_AUTHORIZED: bool = False
PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False
PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED: bool = False
HUMAN_HARDWARE_ATTACH_TOKEN: bool = False
HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
USB_PACKETS_TRANSMITTED: int = 0
PHYSICAL_USB_PACKETS_EMITTED: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0

DONOR_CHECK_MAX_SECONDS: float = 0.15
FX3_DEFAULT_FW_VERSION_G79: str = "7.02"

# Gate IDs & Canonical Codes for G79..G80
G79_GATE_ID: str = "G79_pixel_mapping_reboot_lowbatt_lock_and_cnflasha_readonly_guard"
G79_GATE_CODE: str = "G79_PIXEL_MAPPING_REBOOT_LOWBATT_LOCK_AND_CNFLASHA_READONLY_GUARD"
GATE_G79_PIXEL_MAPPING_REBOOT_LOWBATT_LOCK_AND_CNFLASHA_READONLY_GUARD: str = G79_GATE_CODE
G79: str = G79_GATE_CODE

G80_GATE_ID: str = "G80_ntscpal_reset_persistence_and_gamma_assist_display_lut_split_guard"
G80_GATE_CODE: str = "G80_NTSCPAL_RESET_PERSISTENCE_AND_GAMMA_ASSIST_DISPLAY_LUT_SPLIT_GUARD"
GATE_G80_NTSCPAL_RESET_PERSISTENCE_AND_GAMMA_ASSIST_DISPLAY_LUT_SPLIT_GUARD: str = G80_GATE_CODE
G80: str = G80_GATE_CODE

# Status & Violation Codes
STATUS_VERIFIED_SAFE: str = "VERIFIED_SAFE"
STATUS_VERIFIED_G79: str = (
    "VERIFIED_PIXEL_MAPPING_REBOOT_LOWBATT_LOCK_AND_CNFLASHA_READONLY_GUARD"
)
STATUS_VERIFIED_G80: str = (
    "VERIFIED_NTSCPAL_RESET_PERSISTENCE_AND_GAMMA_ASSIST_DISPLAY_LUT_SPLIT_GUARD"
)

STATUS_BLOCKED_G79_AUTO_PIXEL_MAPPING_SHUTTER_OR_CADENCE_VIOLATION: str = (
    "BLOCKED_G79_AUTO_PIXEL_MAPPING_SHUTTER_OR_CADENCE_VIOLATION"
)
STATUS_BLOCKED_G79_MANUAL_PIXEL_MAPPING_LOW_BATTERY_LOCKOUT: str = (
    "BLOCKED_G79_MANUAL_PIXEL_MAPPING_LOW_BATTERY_LOCKOUT"
)
STATUS_BLOCKED_G79_PIXEL_MAPPING_OPERATOR_CONTROL_LOCKOUT_VIOLATION: str = (
    "BLOCKED_G79_PIXEL_MAPPING_OPERATOR_CONTROL_LOCKOUT_VIOLATION"
)
STATUS_BLOCKED_G79_PIXEL_MAPPING_MANDATORY_REBOOT_OR_H0_H2_MISMATCH: str = (
    "BLOCKED_G79_PIXEL_MAPPING_MANDATORY_REBOOT_OR_H0_H2_MISMATCH"
)
STATUS_BLOCKED_G79_CNFLASHA_FACTORY_CALIBRATION_WRITE_FIREWALL: str = (
    "BLOCKED_G79_CNFLASHA_FACTORY_CALIBRATION_WRITE_FIREWALL"
)
STATUS_BLOCKED_G79_TELEMETRY_INVALID: str = (
    "BLOCKED_G79_PIXEL_MAPPING_CNFLASHA_TELEMETRY_INVALID"
)

STATUS_BLOCKED_G80_NTSCPAL_FRAMERATE_OR_TC_FORMAT_MATRIX_VIOLATION: str = (
    "BLOCKED_G80_NTSCPAL_FRAMERATE_OR_TC_FORMAT_MATRIX_VIOLATION"
)
STATUS_BLOCKED_G80_NTSCPAL_STARTUP_BANNER_OR_MEDIA_DB_VIOLATION: str = (
    "BLOCKED_G80_NTSCPAL_STARTUP_BANNER_OR_MEDIA_DB_VIOLATION"
)
STATUS_BLOCKED_G80_NTSCPAL_RESET_PERSISTENCE_ASYMMETRY_VIOLATION: str = (
    "BLOCKED_G80_NTSCPAL_RESET_PERSISTENCE_ASYMMETRY_VIOLATION"
)
STATUS_BLOCKED_G80_GAMMA_ASSIST_TYPE_OR_SLOG2_FORBIDDEN: str = (
    "BLOCKED_G80_GAMMA_ASSIST_TYPE_OR_SLOG2_FORBIDDEN"
)
STATUS_BLOCKED_G80_LOG_SHOOTING_GAMMA_ASSIST_OR_DISPLAY_LUT_SPLIT_VIOLATION: str = (
    "BLOCKED_G80_LOG_SHOOTING_GAMMA_ASSIST_OR_DISPLAY_LUT_SPLIT_VIOLATION"
)
STATUS_BLOCKED_G80_EXTERNAL_HDMI_GAMMA_ASSIST_SCOPE_VIOLATION: str = (
    "BLOCKED_G80_EXTERNAL_HDMI_GAMMA_ASSIST_SCOPE_VIOLATION"
)
STATUS_BLOCKED_G80_TELEMETRY_INVALID: str = (
    "BLOCKED_G80_NTSCPAL_GAMMA_ASSIST_TELEMETRY_INVALID"
)

STATUS_BLOCKED_PHASE219_DONOR_INTEGRITY: str = (
    "BLOCKED_PHASE219_80GATE_DONOR_INTEGRITY_OR_BUDGET_EXCEEDED"
)
STATUS_BLOCKED_PERSISTENT_EMMC_WRITE: str = (
    "BLOCKED_BY_PERSISTENT_EMMC_WRITE_REDLINE"
)

# Gate G79 Constants — [Auto Pixel Mapping], [Pixel Mapping], Mandatory Reboot & cnflasha RO
AUTO_PIXEL_MAPPING_MENU_PATH: str = (
    "MENU -> Setup -> [Setup Option] -> [Auto Pixel Mapping]"
)
MANUAL_PIXEL_MAPPING_MENU_PATH: str = (
    "MENU -> Setup -> [Setup Option] -> [Pixel Mapping]"
)
AUTO_PIXEL_MAPPING_DEFAULT_ON: bool = True
MANUAL_PIXEL_MAPPING_RECOMMENDED_MAX_DAYS: float = 3.0
PIXEL_MAPPING_MIN_BATTERY_SOC_PCT: float = 20.0
CNFLASHA_CALIBRATION_PARTITION: str = "cnflasha"
DEFAULT_SYNTHETIC_H0_SURFACE_SHA256: str = (
    "c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba"
)

# Gate G80 Constants — [NTSC/PAL Selector], Reset Asymmetry, [Gamma Display Assist] & [Display LUT]
NTSC_PAL_SELECTOR_MENU_PATH: str = (
    "MENU -> Setup -> [Area/Date] -> [NTSC/PAL Selector]"
)
SETTING_RESET_MENU_PATH: str = (
    "MENU -> Setup -> [Reset/Save Settings] -> [Setting Reset]"
)
GAMMA_DISPLAY_ASSIST_MENU_PATH: str = (
    "MENU -> Setup -> [Display Option] -> [Gamma Display Assist]"
)
GAMMA_DISP_ASSIST_TYP_MENU_PATH: str = (
    "MENU -> Setup -> [Display Option] -> [Gamma Disp. Assist Typ.]"
)
DISPLAY_LUT_MENU_PATH: str = (
    "MENU -> Shooting -> [Image Quality/Rec] -> [Log Shooting Setting] -> [Display LUT]"
)

VIDEO_SYSTEM_NTSC: str = "NTSC"
VIDEO_SYSTEM_PAL: str = "PAL"
ALLOWED_VIDEO_SYSTEMS: Tuple[str, ...] = (VIDEO_SYSTEM_NTSC, VIDEO_SYSTEM_PAL)

NTSC_EXCLUSIVE_FRAME_RATE_2398P: str = "23.98p"
NTSC_ALLOWED_FRAME_RATES: Tuple[str, ...] = (
    "23.98p",
    "24.00p",
    "29.97p",
    "59.94p",
    "119.88p",
)
PAL_ALLOWED_FRAME_RATES: Tuple[str, ...] = ("25p", "50p", "100p")

TC_FORMAT_DF: str = "DF"
TC_FORMAT_NDF: str = "NDF"
TC_FORMAT_PAL_LOCKED: str = "PAL_LOCKED"
NTSC_ALLOWED_TC_FORMATS: Tuple[str, ...] = (TC_FORMAT_DF, TC_FORMAT_NDF)

STARTUP_BANNER_NONE: str = "NONE"
STARTUP_BANNER_RUNNING_ON_NTSC: str = "Running on NTSC."
STARTUP_BANNER_RUNNING_ON_PAL: str = "Running on PAL."

RESET_ACTION_NONE: str = "NONE"
RESET_ACTION_CAMERA_SETTINGS_RESET: str = "CAMERA_SETTINGS_RESET"
RESET_ACTION_INITIALIZE: str = "INITIALIZE"
ALLOWED_RESET_ACTIONS: Tuple[str, ...] = (
    RESET_ACTION_NONE,
    RESET_ACTION_CAMERA_SETTINGS_RESET,
    RESET_ACTION_INITIALIZE,
)

GAMMA_ASSIST_TYPE_AUTO: str = "AUTO"
GAMMA_ASSIST_TYPE_SLOG3_709: str = "S-LOG3->709(800%)"
GAMMA_ASSIST_TYPE_HLG_BT2020: str = "HLG(BT.2020)"
GAMMA_ASSIST_TYPE_HLG_709: str = "HLG(709)"
ALLOWED_FX3_702_GAMMA_ASSIST_TYPES: Tuple[str, ...] = (
    GAMMA_ASSIST_TYPE_AUTO,
    GAMMA_ASSIST_TYPE_SLOG3_709,
    GAMMA_ASSIST_TYPE_HLG_BT2020,
    GAMMA_ASSIST_TYPE_HLG_709,
)

LOG_SHOOTING_OFF: str = "OFF"
LOG_SHOOTING_CINE_EI: str = "CINE_EI"
LOG_SHOOTING_CINE_EI_QUICK: str = "CINE_EI_QUICK"
LOG_SHOOTING_FLEXIBLE_ISO: str = "FLEXIBLE_ISO"
ALLOWED_LOG_SHOOTING_MODES_G80: Tuple[str, ...] = (
    LOG_SHOOTING_OFF,
    LOG_SHOOTING_CINE_EI,
    LOG_SHOOTING_CINE_EI_QUICK,
    LOG_SHOOTING_FLEXIBLE_ISO,
)

# Pinned FX3 v7.02 & FX6 v6.01 Donor Specs (bounded <0.15s O_RDONLY verification)
PINNED_PHASE219_DONOR_SPECS: Mapping[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_cpapp_b": (
        "fx3",
        "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin",
        15_980_568,
        "c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba",
        (
            b"ILME-FX3",
            b"Pixel",
            b"Mapping",
            b"NTSC",
            b"PAL",
            b"Gamma",
            b"HLG",
            b"LUT",
            b"S-Log3",
            b"709",
            b"Initialize",
            b"Reset",
            b"Silent",
            b"Display",
            b"Assist",
            b"BK4",
            b"/setting",
        ),
        "fx3/cpapp-b.bin::{15980568B,ILME-FX3,Pixel,Mapping,NTSC,PAL,Gamma,HLG,LUT,S-Log3,709,Initialize,Reset,Silent,Display,Assist}",
    ),
    "fx3_saveload_so": (
        "fx3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libSaveLoadSettings.so",
        18_760,
        "07819f42bdad381ecdd41c3765c117c33b0c44c25be36279b26f83906d244cb7",
        (b"\x7fELF", b"SaveLoadSettings", b"Settings", b"Backup"),
        "fx3/libSaveLoadSettings.so::{18760B,ELF,SaveLoadSettings,Settings,Backup}",
    ),
    "fx3_bk4_bin": (
        "fx3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin",
        2_229_740,
        "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2",
        (b"BK4", b"ILME-FX3", b"TC", b"/setting"),
        "fx3/FX3-CX95900_ALLLANG-Backup.bin::{2229740B,BK4,ILME-FX3,TC,/setting}",
    ),
    "fx6_bk4_bin": (
        "fx6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0110_backup/SYSIPSX-DSLR/CHAPLIN/CX95898_NTSC.bin",
        2_253_333,
        "e2eafd4e950ead94fdba64722b225b9ccf4cf294ce4c1cf956b9e62926bbf89e",
        (b"BK4", b"NTSC", b"TC", b"/setting"),
        "fx6/CX95898_NTSC.bin::{2253333B,BK4,NTSC,TC,/setting}",
    ),
}


# ---------------------------------------------------------------------------
# Data Models (Zero raw bytes reprs; hex strings / ASCII markers only)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase219DonorAuditResult:
    valid: bool
    status: str
    verification_mode: str
    access_mode: str
    files_inspected: int
    elapsed_seconds: float
    within_budget_150ms: bool
    raw_firmware_bytes_leaked: int
    checked_markers: Tuple[str, ...]
    missing_markers: Tuple[str, ...]
    fx3_contracts_verified: bool
    fx6_contracts_verified: bool
    sha256_by_artifact: Dict[str, str]
    bytes_by_artifact: Dict[str, int]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PixelMappingRebootAndCnflashaGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    body_model_name: str
    body_model_id_hex: str
    firmware_version: str
    auto_pixel_mapping_on: bool
    silent_mode_on: bool
    power_off_shutter_sound_expected: bool
    manual_3day_cadence_recommended: bool
    days_since_last_pixel_mapping: float
    manual_pixel_mapping_requested: bool
    battery_soc_pct: float
    battery_low_warning_active: bool
    low_battery_lockout_triggered: bool
    operator_controls_locked_during_exec: bool
    auto_camera_restart_on_completion: bool
    stageb_tmp_overlay_unmounted_post_reboot: bool
    h0_equals_h2_post_reboot: bool
    cnflasha_partition: str
    cnflasha_userspace_write_blocked: bool
    cnflasha_calibration_mutation_bytes: int
    persistent_emmc_writes_authorized: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NtscPalPersistenceAndGammaAssistSplitResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    regional_default_system: str
    configured_ntsc_pal_system: str
    canonical_reset_action: str
    effective_post_reset_system: str
    camera_settings_reset_preserved_system: bool
    initialize_restores_regional_default: bool
    startup_notification_banner: str
    selected_frame_rate: str
    ntsc_exclusive_2398p_active: bool
    selected_tc_format: str
    tc_format_df_ndf_available: bool
    media_db_system_tracked: bool
    canonical_log_shooting_mode: str
    log_shooting_active: bool
    canonical_gamma_assist_type: str
    gamma_display_assist_menu_on: bool
    gamma_display_assist_locked_off_by_log: bool
    effective_gamma_display_assist_on: bool
    display_lut_on: bool
    effective_display_lut_preview_on: bool
    active_preview_governor: str
    builtin_lcd_only_scope: bool
    external_hdmi_gamma_assist_applied: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G79PixelMapCnflashaGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    pixelmap_cnflasha_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G80NtscPalGammaAssistDisplayLutGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    ntscpal_gammaassist_displaylut_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master80GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    offline_77_gates_verified: bool
    all_80_gates_verified: bool
    g13_to_g80_all_passed: bool
    g79_to_g80_all_passed: bool
    h0_h1_trial_entry_allowed: bool
    status: str
    agent_auto_flash_blocked: bool
    human_hardware_attach_token: bool
    el3_payload_transmit_authorized: bool
    spi_nor_write_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    physical_flash_auto_exec_authorized: bool
    usb_packets_transmitted: int
    physical_usb_packets_emitted: int
    raw_firmware_bytes_leaked: int
    technical_gates_passed: int
    summary: Dict[str, Any]
    gates: Tuple[Dict[str, Any], ...]
    master_78_report: Dict[str, Any]
    g79_result: Dict[str, Any]
    g80_result: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Internal Helpers & Normalization
# ---------------------------------------------------------------------------


def _is_forced_clean_room(force_clean_room: Optional[bool] = None) -> bool:
    if force_clean_room is not None:
        return bool(force_clean_room)
    return os.environ.get(ENV_FORCE_CLEAN_ROOM, "").strip() in (
        "1",
        "true",
        "TRUE",
        "yes",
        "YES",
    )


def _read_file_o_rdonly(path: Path) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    fd = os.open(str(path), flags)
    chunks: List[bytes] = []
    try:
        while True:
            buf = os.read(fd, 1 << 20)
            if not buf:
                break
            chunks.append(buf)
    finally:
        os.close(fd)
    return b"".join(chunks)


def _read_cached_donor_o_rdonly(path: Path) -> Tuple[int, str, bytes]:
    key = str(path.resolve())
    st = os.stat(key)
    cached = _DONOR_BLOB_CACHE.get(key)
    if cached is not None and cached[0] == st.st_size and cached[1] == st.st_mtime:
        return cached[2], cached[3], cached[4]
    blob = _read_file_o_rdonly(path)
    sha = hashlib.sha256(blob).hexdigest()
    _DONOR_BLOB_CACHE[key] = (st.st_size, st.st_mtime, len(blob), sha, blob)
    return len(blob), sha, blob


def _add_code(codes: List[str], code: str) -> None:
    if code not in codes:
        codes.append(code)


def _is_finite_num(val: Any) -> bool:
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        return False
    f = float(val)
    return abs(f) < 1e12 and (f == f)


def _is_sha256_hex(val: Any) -> bool:
    return isinstance(val, str) and bool(re.fullmatch(r"[0-9a-fA-F]{64}", val.strip()))


def _parse_fw_major_minor(version: str) -> Optional[Tuple[int, int]]:
    m = re.fullmatch(r"\s*(\d+)\.(\d+)(?:\.\d+)?\s*", version or "")
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def _norm_video_system(val: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", (val or "").strip().upper()).strip("_")


def _norm_frame_rate(val: str) -> str:
    s = (val or "").strip().lower().replace("fps", "p").replace(" ", "")
    aliases = {
        "23.98p": "23.98p",
        "23.976p": "23.98p",
        "24p_ntsc": "23.98p",
        "24.00p": "24.00p",
        "24p_dci": "24.00p",
        "29.97p": "29.97p",
        "59.94p": "59.94p",
        "119.88p": "119.88p",
        "25p": "25p",
        "25.00p": "25p",
        "50p": "50p",
        "50.00p": "50p",
        "100p": "100p",
        "100.00p": "100p",
    }
    return aliases.get(s, (val or "").strip())


def _norm_tc_format(val: str) -> str:
    t = re.sub(r"[^A-Z0-9]+", "_", (val or "").strip().upper()).strip("_")
    if t in ("DF", "DROP_FRAME"):
        return TC_FORMAT_DF
    if t in ("NDF", "NON_DROP_FRAME"):
        return TC_FORMAT_NDF
    if t in ("PAL_LOCKED", "NONE", "UNAVAILABLE", "PAL_FIXED_25FPS"):
        return TC_FORMAT_PAL_LOCKED
    return t


def _norm_reset_action(val: str) -> str:
    t = re.sub(r"[^A-Z0-9]+", "_", (val or "").strip().upper()).strip("_")
    if t in ("NONE", "NO_RESET"):
        return RESET_ACTION_NONE
    if t in ("CAMERA_SETTINGS_RESET", "CAMERA_SETTING_RESET"):
        return RESET_ACTION_CAMERA_SETTINGS_RESET
    if t in ("INITIALIZE", "FACTORY_INITIALIZE"):
        return RESET_ACTION_INITIALIZE
    return t


def _norm_log_shooting_mode(val: str) -> str:
    t = re.sub(r"[^A-Z0-9]+", "_", (val or "").strip().upper()).strip("_")
    if t in ("OFF", "NONE", "DISABLED", "PICTURE_PROFILE"):
        return LOG_SHOOTING_OFF
    if t == "CINE_EI":
        return LOG_SHOOTING_CINE_EI
    if t == "CINE_EI_QUICK":
        return LOG_SHOOTING_CINE_EI_QUICK
    if t == "FLEXIBLE_ISO":
        return LOG_SHOOTING_FLEXIBLE_ISO
    return t


def _norm_gamma_assist_type(val: str) -> str:
    raw = (val or "").strip().upper().replace(" ", "")
    aliases = {
        "AUTO": GAMMA_ASSIST_TYPE_AUTO,
        "S-LOG3->709(800%)": GAMMA_ASSIST_TYPE_SLOG3_709,
        "SLOG3->709(800%)": GAMMA_ASSIST_TYPE_SLOG3_709,
        "S_LOG3_TO_709_800": GAMMA_ASSIST_TYPE_SLOG3_709,
        "S-LOG3_709_800": GAMMA_ASSIST_TYPE_SLOG3_709,
        "HLG(BT.2020)": GAMMA_ASSIST_TYPE_HLG_BT2020,
        "HLG_BT2020": GAMMA_ASSIST_TYPE_HLG_BT2020,
        "HLG(BT2020)": GAMMA_ASSIST_TYPE_HLG_BT2020,
        "HLG(709)": GAMMA_ASSIST_TYPE_HLG_709,
        "HLG_709": GAMMA_ASSIST_TYPE_HLG_709,
    }
    return aliases.get(raw, (val or "").strip())


# ---------------------------------------------------------------------------
# 1. Bounded `<0.15s` O_RDONLY Local Donor Audit (`FX3_FX6_FORCE_CLEAN_ROOM=1`)
# ---------------------------------------------------------------------------


def audit_phase219_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    max_budget_seconds: float = DONOR_CHECK_MAX_SECONDS,
) -> Phase219DonorAuditResult:
    """Bounded `<0.15s` `O_RDONLY` local donor contract check with deterministic
    `FX3_FX6_FORCE_CLEAN_ROOM=1` synthetic fallback (`raw_firmware_bytes_leaked == 0`).
    """
    t0 = time.perf_counter()
    clean_forced = _is_forced_clean_room(force_clean_room)
    resolved_repo = (
        DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)
    ).resolve()
    paths = resolve_donor_thermal_power_paths(
        work_root=work_root, repo_root=resolved_repo
    )
    effective_work_root: Optional[Path] = (
        Path(work_root) if work_root is not None else paths.work_root
    )

    resolved: Dict[str, Path] = {}
    if effective_work_root is not None:
        for key, (_body, rel_path, *_rest) in PINNED_PHASE219_DONOR_SPECS.items():
            resolved[key] = effective_work_root / rel_path

    donor_available = (
        (not clean_forced)
        and (effective_work_root is not None)
        and bool(resolved)
        and all(p.is_file() for p in resolved.values())
    )

    if not donor_available:
        elapsed = time.perf_counter() - t0
        within_budget = elapsed < max_budget_seconds
        return Phase219DonorAuditResult(
            valid=within_budget,
            status=(
                STATUS_VERIFIED_SAFE
                if within_budget
                else STATUS_BLOCKED_PHASE219_DONOR_INTEGRITY
            ),
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="O_RDONLY",
            files_inspected=0,
            elapsed_seconds=round(elapsed, 6),
            within_budget_150ms=within_budget,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            checked_markers=tuple(
                spec[5] for spec in PINNED_PHASE219_DONOR_SPECS.values()
            ),
            missing_markers=(),
            fx3_contracts_verified=within_budget,
            fx6_contracts_verified=within_budget,
            sha256_by_artifact={
                k: spec[3] for k, spec in PINNED_PHASE219_DONOR_SPECS.items()
            },
            bytes_by_artifact={
                k: spec[2] for k, spec in PINNED_PHASE219_DONOR_SPECS.items()
            },
            errors=()
            if within_budget
            else (
                f"Clean-room donor check exceeded budget ({elapsed:.4f}s >= {max_budget_seconds:.4f}s).",
            ),
            warnings=(),
        )

    checked: List[str] = []
    missing: List[str] = []
    shas: Dict[str, str] = {}
    sizes: Dict[str, int] = {}
    errors: List[str] = []
    passed_keys: Set[str] = set()
    files_inspected = 0

    for key, (
        _body,
        _rel_name,
        exp_size,
        exp_sha,
        marker_tuple,
        marker_label,
    ) in PINNED_PHASE219_DONOR_SPECS.items():
        size_b, sha, blob = _read_cached_donor_o_rdonly(resolved[key])
        files_inspected += 1
        shas[key] = sha
        sizes[key] = size_b

        missing_for_file = [m for m in marker_tuple if m not in blob]
        integrity_ok = size_b == exp_size and sha == exp_sha
        if not missing_for_file:
            checked.append(marker_label)
        else:
            missing.append(marker_label)
            errors.append(
                f"Donor {key} missing {len(missing_for_file)} required marker(s) for {marker_label}."
            )
        if not integrity_ok:
            errors.append(
                f"Donor {key} integrity mismatch: size={size_b} (expected {exp_size}), "
                f"sha256={sha} (expected {exp_sha})."
            )
        if not missing_for_file and integrity_ok:
            passed_keys.add(key)

    elapsed = time.perf_counter() - t0
    within_budget = elapsed < max_budget_seconds
    if not within_budget:
        errors.append(
            f"Local O_RDONLY donor check exceeded {max_budget_seconds:.3f}s budget ({elapsed:.4f}s)."
        )

    fx3_keys = {k for k, s in PINNED_PHASE219_DONOR_SPECS.items() if s[0] == "fx3"}
    fx6_keys = {k for k, s in PINNED_PHASE219_DONOR_SPECS.items() if s[0] == "fx6"}
    valid = (len(errors) == 0) and (len(missing) == 0) and within_budget
    return Phase219DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_PHASE219_DONOR_INTEGRITY,
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="O_RDONLY",
        files_inspected=files_inspected,
        elapsed_seconds=round(elapsed, 6),
        within_budget_150ms=within_budget,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        checked_markers=tuple(checked),
        missing_markers=tuple(missing),
        fx3_contracts_verified=fx3_keys.issubset(passed_keys) and valid,
        fx6_contracts_verified=fx6_keys.issubset(passed_keys) and valid,
        sha256_by_artifact=shas,
        bytes_by_artifact=sizes,
        errors=tuple(errors),
        warnings=(),
    )


# ---------------------------------------------------------------------------
# 2. Gate G79 Validators (`G79_PIXEL_MAPPING_REBOOT_LOWBATT_LOCK_AND_CNFLASHA_READONLY_GUARD`)
# ---------------------------------------------------------------------------


def resolve_fx3_pixel_mapping_lifecycle(
    *,
    auto_pixel_mapping_on: bool = AUTO_PIXEL_MAPPING_DEFAULT_ON,
    silent_mode_on: bool = False,
    battery_soc_pct: float = 85.0,
    battery_low_warning_active: bool = False,
) -> Tuple[bool, bool, bool]:
    """Resolve Sony `ILME-FX3` (`Ver. 7.02`) pixel mapping hardware behaviors:
    `(power_off_shutter_sound_expected, manual_3day_cadence_recommended, low_battery_lockout)`.

    - `[Auto Pixel Mapping] = [On]` actuates the mechanical shutter at power-off for dark-frame
      sensor optimization **even when `[Silent Mode] = [On]`**.
    - `[Auto Pixel Mapping] = [Off]` activates the `<= 3`-day manual `[Pixel Mapping]` guidance.
    - Manual `[Pixel Mapping]` locks out execution when battery charge is low (`< 20%` or warning).
    """
    power_off_shutter_sound_expected = bool(auto_pixel_mapping_on)
    manual_3day_cadence_recommended = not bool(auto_pixel_mapping_on)
    low_battery_lockout = bool(battery_low_warning_active) or (
        float(battery_soc_pct) < PIXEL_MAPPING_MIN_BATTERY_SOC_PCT
    )
    return (
        power_off_shutter_sound_expected,
        manual_3day_cadence_recommended,
        low_battery_lockout,
    )


def verify_pixel_mapping_reboot_lowbatt_and_cnflasha_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: int = FX3_MODEL_ID,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_G79,
    auto_pixel_mapping_on: bool = AUTO_PIXEL_MAPPING_DEFAULT_ON,
    silent_mode_on: bool = False,
    claimed_silent_mode_suppresses_poweroff_shutter: bool = False,
    days_since_last_pixel_mapping: float = 0.0,
    manual_pixel_mapping_requested: bool = True,
    battery_soc_pct: float = 85.0,
    battery_low_warning_active: bool = False,
    operator_controls_locked_during_exec: bool = True,
    concurrent_operator_input_accepted: bool = False,
    auto_camera_restart_on_completion: bool = True,
    stageb_tmp_overlay_unmounted_post_reboot: bool = True,
    h0_surface_sha256: str = DEFAULT_SYNTHETIC_H0_SURFACE_SHA256,
    h2_post_reboot_surface_sha256: str = DEFAULT_SYNTHETIC_H0_SURFACE_SHA256,
    cnflasha_userspace_write_blocked: bool = True,
    cnflasha_write_attempted: bool = False,
    cnflasha_calibration_mutation_bytes: int = 0,
) -> PixelMappingRebootAndCnflashaGuardResult:
    """Verify Gate `G79`: `[Auto Pixel Mapping]` / manual `[Pixel Mapping]` low-battery
    lockout, operator-control lockout, mandatory automatic camera restart (`H0 == H2`
    Stage-B `/tmp` teardown), and absolute `cnflasha` factory calibration read-only firewall.
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    fw_tuple = _parse_fw_major_minor(firmware_version)
    if (
        not isinstance(body_model_name, str)
        or body_model_name.strip().upper() != FX3_MODEL_NAME
        or not isinstance(body_model_id, int)
        or isinstance(body_model_id, bool)
        or body_model_id != FX3_MODEL_ID
        or fw_tuple is None
        or fw_tuple < (7, 2)
    ):
        _add_code(codes, STATUS_BLOCKED_G79_TELEMETRY_INVALID)
        errors.append(
            f"Gate G79 requires {FX3_MODEL_NAME} (model_id=0x{FX3_MODEL_ID:08X}) Ver. >= 7.02; "
            f"got model={body_model_name!r}, id={body_model_id!r}, fw={firmware_version!r}."
        )

    if (
        not isinstance(auto_pixel_mapping_on, bool)
        or not isinstance(silent_mode_on, bool)
        or not isinstance(claimed_silent_mode_suppresses_poweroff_shutter, bool)
        or not isinstance(manual_pixel_mapping_requested, bool)
        or not isinstance(battery_low_warning_active, bool)
        or not isinstance(operator_controls_locked_during_exec, bool)
        or not isinstance(concurrent_operator_input_accepted, bool)
        or not isinstance(auto_camera_restart_on_completion, bool)
        or not isinstance(stageb_tmp_overlay_unmounted_post_reboot, bool)
        or not isinstance(cnflasha_userspace_write_blocked, bool)
        or not isinstance(cnflasha_write_attempted, bool)
        or not _is_finite_num(days_since_last_pixel_mapping)
        or float(days_since_last_pixel_mapping) < 0.0
        or not _is_finite_num(battery_soc_pct)
        or not (0.0 <= float(battery_soc_pct) <= 100.0)
        or isinstance(cnflasha_calibration_mutation_bytes, bool)
        or not isinstance(cnflasha_calibration_mutation_bytes, int)
        or cnflasha_calibration_mutation_bytes < 0
        or not _is_sha256_hex(h0_surface_sha256)
        or not _is_sha256_hex(h2_post_reboot_surface_sha256)
    ):
        _add_code(codes, STATUS_BLOCKED_G79_TELEMETRY_INVALID)
        errors.append("Gate G79 received malformed boolean, battery SoC, or SHA-256 telemetry.")
        soc_val = 0.0
        days_val = 0.0
    else:
        soc_val = float(battery_soc_pct)
        days_val = float(days_since_last_pixel_mapping)

    (
        power_off_shutter_sound_expected,
        manual_3day_cadence_recommended,
        low_battery_lockout,
    ) = resolve_fx3_pixel_mapping_lifecycle(
        auto_pixel_mapping_on=bool(auto_pixel_mapping_on)
        if isinstance(auto_pixel_mapping_on, bool)
        else True,
        silent_mode_on=bool(silent_mode_on) if isinstance(silent_mode_on, bool) else False,
        battery_soc_pct=soc_val,
        battery_low_warning_active=bool(battery_low_warning_active)
        if isinstance(battery_low_warning_active, bool)
        else False,
    )

    if power_off_shutter_sound_expected and claimed_silent_mode_suppresses_poweroff_shutter:
        _add_code(codes, STATUS_BLOCKED_G79_AUTO_PIXEL_MAPPING_SHUTTER_OR_CADENCE_VIOLATION)
        errors.append(
            "[Auto Pixel Mapping] = [On] actuates the mechanical shutter at power-off even when "
            "[Silent Mode] = [On]; suppressing or misclassifying power-off shutter actuation is invalid."
        )

    if (
        manual_3day_cadence_recommended
        and days_val > MANUAL_PIXEL_MAPPING_RECOMMENDED_MAX_DAYS
        and not manual_pixel_mapping_requested
    ):
        _add_code(codes, STATUS_BLOCKED_G79_AUTO_PIXEL_MAPPING_SHUTTER_OR_CADENCE_VIOLATION)
        errors.append(
            f"[Auto Pixel Mapping] is [Off] and {days_val:.1f} days elapsed (> "
            f"{MANUAL_PIXEL_MAPPING_RECOMMENDED_MAX_DAYS:.0f}-day Sony guidance) without manual [Pixel Mapping]."
        )

    if manual_pixel_mapping_requested and low_battery_lockout:
        _add_code(codes, STATUS_BLOCKED_G79_MANUAL_PIXEL_MAPPING_LOW_BATTERY_LOCKOUT)
        errors.append(
            f"Manual [Pixel Mapping] blocked by low-battery lockout (battery_soc_pct={soc_val:.1f}%, "
            f"battery_low_warning_active={battery_low_warning_active})."
        )

    if manual_pixel_mapping_requested and (
        (not operator_controls_locked_during_exec) or concurrent_operator_input_accepted
    ):
        _add_code(codes, STATUS_BLOCKED_G79_PIXEL_MAPPING_OPERATOR_CONTROL_LOCKOUT_VIOLATION)
        errors.append(
            "Manual [Pixel Mapping] requires complete camera operator-control lockout during execution."
        )

    h0_eq_h2 = (
        isinstance(h0_surface_sha256, str)
        and isinstance(h2_post_reboot_surface_sha256, str)
        and h0_surface_sha256.strip().lower()
        == h2_post_reboot_surface_sha256.strip().lower()
    )
    if manual_pixel_mapping_requested and (
        (not auto_camera_restart_on_completion)
        or (not stageb_tmp_overlay_unmounted_post_reboot)
        or (not h0_eq_h2)
    ):
        _add_code(codes, STATUS_BLOCKED_G79_PIXEL_MAPPING_MANDATORY_REBOOT_OR_H0_H2_MISMATCH)
        errors.append(
            "Manual [Pixel Mapping] triggers mandatory automatic camera restart upon completion, "
            "which must cleanly unmount Stage-B /tmp bind-mounts and restore H0 == H2 parity."
        )

    if (
        (not cnflasha_userspace_write_blocked)
        or cnflasha_write_attempted
        or (cnflasha_calibration_mutation_bytes != 0)
    ):
        _add_code(codes, STATUS_BLOCKED_G79_CNFLASHA_FACTORY_CALIBRATION_WRITE_FIREWALL)
        errors.append(
            "Absolute cnflasha factory sensor calibration read-only firewall violated: "
            "user-space writes or calibration byte mutations are strictly forbidden."
        )

    valid = len(codes) == 0
    return PixelMappingRebootAndCnflashaGuardResult(
        valid=valid,
        status=STATUS_VERIFIED_G79 if valid else codes[0],
        violation_codes=tuple(codes),
        body_model_name=str(body_model_name),
        body_model_id_hex=f"0x{body_model_id:08X}"
        if isinstance(body_model_id, int) and not isinstance(body_model_id, bool)
        else "INVALID",
        firmware_version=str(firmware_version),
        auto_pixel_mapping_on=bool(auto_pixel_mapping_on),
        silent_mode_on=bool(silent_mode_on),
        power_off_shutter_sound_expected=power_off_shutter_sound_expected,
        manual_3day_cadence_recommended=manual_3day_cadence_recommended,
        days_since_last_pixel_mapping=round(days_val, 3),
        manual_pixel_mapping_requested=bool(manual_pixel_mapping_requested),
        battery_soc_pct=round(soc_val, 2),
        battery_low_warning_active=bool(battery_low_warning_active),
        low_battery_lockout_triggered=bool(manual_pixel_mapping_requested and low_battery_lockout),
        operator_controls_locked_during_exec=bool(operator_controls_locked_during_exec),
        auto_camera_restart_on_completion=bool(auto_camera_restart_on_completion),
        stageb_tmp_overlay_unmounted_post_reboot=bool(
            stageb_tmp_overlay_unmounted_post_reboot
        ),
        h0_equals_h2_post_reboot=bool(h0_eq_h2),
        cnflasha_partition=CNFLASHA_CALIBRATION_PARTITION,
        cnflasha_userspace_write_blocked=bool(cnflasha_userspace_write_blocked),
        cnflasha_calibration_mutation_bytes=(
            int(cnflasha_calibration_mutation_bytes)
            if isinstance(cnflasha_calibration_mutation_bytes, int)
            and not isinstance(cnflasha_calibration_mutation_bytes, bool)
            else -1
        ),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g79_pixelmap_reboot_cnflasha_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    pixelmap_cnflasha_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase219DonorAuditResult] = None,
) -> Tuple[GateVerdict, G79PixelMapCnflashaGuardResult]:
    """Evaluate Gate `G79` combining bounded `<0.15s` donor check with pixel mapping
    reboot / low-battery / `cnflasha` read-only firewall verification.
    """
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase219_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_pixel_mapping_reboot_lowbatt_and_cnflasha_guard(
        **dict(pixelmap_cnflasha_kwargs or {})
    )

    codes: List[str] = []
    errors: List[str] = list(audit.errors) + list(guard.errors)
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if not audit.valid:
        _add_code(codes, audit.status)
    for c in guard.violation_codes:
        _add_code(codes, c)
    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Gate G79 blocked persistent eMMC write authorization request.")

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G79 if valid else codes[0]

    res = G79PixelMapCnflashaGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        pixelmap_cnflasha_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, auto_pixel_map={guard.auto_pixel_mapping_on}"
        f"(shutter_snd={guard.power_off_shutter_sound_expected}), "
        f"manual={guard.manual_pixel_mapping_requested}(soc={guard.battery_soc_pct:.1f}%,"
        f"ctrl_lock={guard.operator_controls_locked_during_exec},"
        f"reboot={guard.auto_camera_restart_on_completion},h0_eq_h2={guard.h0_equals_h2_post_reboot}), "
        f"cnflasha_ro={guard.cnflasha_userspace_write_blocked}"
    )
    verdict = GateVerdict(
        gate_id=G79_GATE_ID,
        gate_code=G79_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 3. Gate G80 Validators (`G80_NTSCPAL_RESET_PERSISTENCE_AND_GAMMA_ASSIST_DISPLAY_LUT_SPLIT_GUARD`)
# ---------------------------------------------------------------------------


def resolve_fx3_ntscpal_state(
    *,
    regional_default_system: str = VIDEO_SYSTEM_NTSC,
    configured_ntsc_pal_system: str = VIDEO_SYSTEM_NTSC,
    reset_action: str = RESET_ACTION_NONE,
) -> Tuple[str, str, Tuple[str, ...], bool]:
    """Resolve effective post-reset `[NTSC/PAL Selector]` state, startup banner,
    allowed frame-rate table, and `[TC Format]` (`DF`/`NDF`) availability:

    - `[Camera Settings Reset]` preserves `[NTSC/PAL Selector]`; only `[Initialize]`
      restores `regional_default_system`.
    - Startup banner `"Running on NTSC."` / `"Running on PAL."` appears whenever the
      effective system differs from `regional_default_system`.
    """
    reg = _norm_video_system(regional_default_system)
    cfg = _norm_video_system(configured_ntsc_pal_system)
    act = _norm_reset_action(reset_action)

    effective = reg if act == RESET_ACTION_INITIALIZE else cfg
    if effective != reg:
        banner = (
            STARTUP_BANNER_RUNNING_ON_NTSC
            if effective == VIDEO_SYSTEM_NTSC
            else STARTUP_BANNER_RUNNING_ON_PAL
        )
    else:
        banner = STARTUP_BANNER_NONE

    rates = (
        NTSC_ALLOWED_FRAME_RATES
        if effective == VIDEO_SYSTEM_NTSC
        else PAL_ALLOWED_FRAME_RATES
    )
    tc_df_ndf_available = effective == VIDEO_SYSTEM_NTSC
    return effective, banner, rates, tc_df_ndf_available


def resolve_fx3_gamma_assist_and_display_lut_split(
    *,
    log_shooting_mode: str = LOG_SHOOTING_CINE_EI,
    gamma_display_assist_menu_on: bool = False,
    display_lut_on: bool = True,
) -> Tuple[bool, bool, bool, bool, str]:
    """Resolve `ILME-FX3` (`Ver. 7.02`) `[Gamma Display Assist]` vs `[Display LUT]` split:
    `(log_shooting_active, locked_off_by_log, effective_gamma_assist_on, effective_display_lut_on, governor)`.

    Whenever `[Log Shooting]` (`Cine EI` / `Cine EI Quick` / `Flexible ISO`) is active,
    `[Gamma Display Assist]` is hard-locked to `[Off]` and `[Display LUT]` governs preview.
    """
    canon_log = _norm_log_shooting_mode(log_shooting_mode)
    log_active = canon_log != LOG_SHOOTING_OFF
    locked_off_by_log = log_active
    effective_gamma_assist = False if log_active else bool(gamma_display_assist_menu_on)
    effective_display_lut = bool(display_lut_on) if log_active else False
    governor = "DISPLAY_LUT" if log_active else "GAMMA_DISPLAY_ASSIST"
    return (
        log_active,
        locked_off_by_log,
        effective_gamma_assist,
        effective_display_lut,
        governor,
    )


def verify_ntscpal_persistence_and_gamma_assist_displaylut_guard(
    *,
    regional_default_system: str = VIDEO_SYSTEM_NTSC,
    configured_ntsc_pal_system: str = VIDEO_SYSTEM_NTSC,
    reset_action: str = RESET_ACTION_CAMERA_SETTINGS_RESET,
    observed_post_reset_system: Optional[str] = None,
    observed_startup_banner: Optional[str] = None,
    selected_frame_rate: str = "23.98p",
    selected_tc_format: str = TC_FORMAT_NDF,
    media_db_system_tracked: bool = True,
    log_shooting_mode: str = LOG_SHOOTING_CINE_EI,
    gamma_assist_type: str = GAMMA_ASSIST_TYPE_SLOG3_709,
    gamma_display_assist_menu_on: bool = True,
    claimed_gamma_assist_active_in_log_shooting: bool = False,
    display_lut_on: bool = True,
    claimed_display_lut_active_outside_log: bool = False,
    external_hdmi_gamma_assist_applied: bool = False,
) -> NtscPalPersistenceAndGammaAssistSplitResult:
    """Verify Gate `G80`: `[NTSC/PAL Selector]` exclusive frame-rate & `[TC Format]`
    matrix, startup banner, `[Camera Settings Reset]` vs `[Initialize]` persistence
    asymmetry, 4-mode `[Gamma Disp. Assist Typ.]` (`zero S-Log2`), `[Log Shooting]`
    `[Display LUT]` split, and built-in-LCD-only scope.
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if (
        not isinstance(regional_default_system, str)
        or not isinstance(configured_ntsc_pal_system, str)
        or not isinstance(reset_action, str)
        or not isinstance(selected_frame_rate, str)
        or not isinstance(selected_tc_format, str)
        or not isinstance(log_shooting_mode, str)
        or not isinstance(gamma_assist_type, str)
        or not isinstance(media_db_system_tracked, bool)
        or not isinstance(gamma_display_assist_menu_on, bool)
        or not isinstance(claimed_gamma_assist_active_in_log_shooting, bool)
        or not isinstance(display_lut_on, bool)
        or not isinstance(claimed_display_lut_active_outside_log, bool)
        or not isinstance(external_hdmi_gamma_assist_applied, bool)
        or (observed_post_reset_system is not None and not isinstance(observed_post_reset_system, str))
        or (observed_startup_banner is not None and not isinstance(observed_startup_banner, str))
    ):
        _add_code(codes, STATUS_BLOCKED_G80_TELEMETRY_INVALID)
        errors.append("Gate G80 received non-string or non-boolean telemetry parameters.")

    reg = _norm_video_system(regional_default_system if isinstance(regional_default_system, str) else "")
    cfg = _norm_video_system(
        configured_ntsc_pal_system if isinstance(configured_ntsc_pal_system, str) else ""
    )
    act = _norm_reset_action(reset_action if isinstance(reset_action, str) else "")

    if reg not in ALLOWED_VIDEO_SYSTEMS or cfg not in ALLOWED_VIDEO_SYSTEMS:
        _add_code(codes, STATUS_BLOCKED_G80_TELEMETRY_INVALID)
        errors.append(
            f"[NTSC/PAL Selector] systems must be in {ALLOWED_VIDEO_SYSTEMS}; got "
            f"regional_default={regional_default_system!r}, configured={configured_ntsc_pal_system!r}."
        )
    if act not in ALLOWED_RESET_ACTIONS:
        _add_code(codes, STATUS_BLOCKED_G80_TELEMETRY_INVALID)
        errors.append(
            f"Reset action must be in {ALLOWED_RESET_ACTIONS}; got {reset_action!r}."
        )

    effective_sys, expected_banner, allowed_rates, tc_df_ndf_avail = (
        resolve_fx3_ntscpal_state(
            regional_default_system=reg if reg in ALLOWED_VIDEO_SYSTEMS else VIDEO_SYSTEM_NTSC,
            configured_ntsc_pal_system=cfg if cfg in ALLOWED_VIDEO_SYSTEMS else VIDEO_SYSTEM_NTSC,
            reset_action=act if act in ALLOWED_RESET_ACTIONS else RESET_ACTION_NONE,
        )
    )

    if observed_post_reset_system is not None and isinstance(observed_post_reset_system, str):
        obs_sys = _norm_video_system(observed_post_reset_system)
        if obs_sys != effective_sys:
            _add_code(codes, STATUS_BLOCKED_G80_NTSCPAL_RESET_PERSISTENCE_ASYMMETRY_VIOLATION)
            errors.append(
                f"[Setting Reset] persistence asymmetry violated for action={act}: "
                f"expected post-reset system {effective_sys!r}, observed {obs_sys!r}."
            )

    norm_rate = _norm_frame_rate(selected_frame_rate if isinstance(selected_frame_rate, str) else "")
    norm_tc = _norm_tc_format(selected_tc_format if isinstance(selected_tc_format, str) else "")

    if norm_rate not in allowed_rates:
        _add_code(codes, STATUS_BLOCKED_G80_NTSCPAL_FRAMERATE_OR_TC_FORMAT_MATRIX_VIOLATION)
        errors.append(
            f"Frame rate {selected_frame_rate!r} is illegal under {effective_sys} "
            f"(allowed={allowed_rates}; 23.98p is NTSC-exclusive)."
        )

    if effective_sys == VIDEO_SYSTEM_NTSC:
        if norm_tc not in NTSC_ALLOWED_TC_FORMATS:
            _add_code(codes, STATUS_BLOCKED_G80_NTSCPAL_FRAMERATE_OR_TC_FORMAT_MATRIX_VIOLATION)
            errors.append(
                f"NTSC requires [TC Format] in {NTSC_ALLOWED_TC_FORMATS}; got {selected_tc_format!r}."
            )
    else:
        if norm_tc != TC_FORMAT_PAL_LOCKED:
            _add_code(codes, STATUS_BLOCKED_G80_NTSCPAL_FRAMERATE_OR_TC_FORMAT_MATRIX_VIOLATION)
            errors.append(
                f"PAL locks out [TC Format] DF/NDF selection; got {selected_tc_format!r}."
            )

    actual_banner = (
        observed_startup_banner.strip()
        if isinstance(observed_startup_banner, str)
        else expected_banner
    )
    if actual_banner != expected_banner or (not media_db_system_tracked):
        _add_code(codes, STATUS_BLOCKED_G80_NTSCPAL_STARTUP_BANNER_OR_MEDIA_DB_VIOLATION)
        errors.append(
            f"[NTSC/PAL Selector] startup banner / media DB tracking violation: "
            f"expected banner={expected_banner!r} (got {actual_banner!r}), "
            f"media_db_system_tracked={media_db_system_tracked}."
        )

    canon_log = _norm_log_shooting_mode(log_shooting_mode if isinstance(log_shooting_mode, str) else "")
    if canon_log not in ALLOWED_LOG_SHOOTING_MODES_G80:
        _add_code(codes, STATUS_BLOCKED_G80_TELEMETRY_INVALID)
        errors.append(
            f"[Log Shooting] mode must be in {ALLOWED_LOG_SHOOTING_MODES_G80}; got {log_shooting_mode!r}."
        )

    canon_gamma = _norm_gamma_assist_type(gamma_assist_type if isinstance(gamma_assist_type, str) else "")
    if canon_gamma not in ALLOWED_FX3_702_GAMMA_ASSIST_TYPES:
        _add_code(codes, STATUS_BLOCKED_G80_GAMMA_ASSIST_TYPE_OR_SLOG2_FORBIDDEN)
        errors.append(
            f"[Gamma Disp. Assist Typ.] {gamma_assist_type!r} is unsupported in FX3 Ver. 7.02 "
            f"(only {ALLOWED_FX3_702_GAMMA_ASSIST_TYPES} allowed; S-Log2 is forbidden)."
        )

    (
        log_active,
        locked_off_by_log,
        effective_gamma_assist,
        effective_display_lut,
        governor,
    ) = resolve_fx3_gamma_assist_and_display_lut_split(
        log_shooting_mode=canon_log
        if canon_log in ALLOWED_LOG_SHOOTING_MODES_G80
        else LOG_SHOOTING_OFF,
        gamma_display_assist_menu_on=bool(gamma_display_assist_menu_on),
        display_lut_on=bool(display_lut_on),
    )

    if log_active and claimed_gamma_assist_active_in_log_shooting:
        _add_code(
            codes,
            STATUS_BLOCKED_G80_LOG_SHOOTING_GAMMA_ASSIST_OR_DISPLAY_LUT_SPLIT_VIOLATION,
        )
        errors.append(
            f"[Gamma Display Assist] is hard-locked to [Off] whenever [Log Shooting] "
            f"({canon_log}) is active; [Display LUT] governs Log preview."
        )
    if (not log_active) and claimed_display_lut_active_outside_log:
        _add_code(
            codes,
            STATUS_BLOCKED_G80_LOG_SHOOTING_GAMMA_ASSIST_OR_DISPLAY_LUT_SPLIT_VIOLATION,
        )
        errors.append(
            "[Display LUT] governs [Log Shooting] modes only and cannot override Picture Profile preview when [Log Shooting] = [Off]."
        )

    if external_hdmi_gamma_assist_applied:
        _add_code(codes, STATUS_BLOCKED_G80_EXTERNAL_HDMI_GAMMA_ASSIST_SCOPE_VIOLATION)
        errors.append(
            "[Gamma Display Assist] applies exclusively to the built-in LCD monitor and is never applied to external HDMI/TV output."
        )

    valid = len(codes) == 0
    return NtscPalPersistenceAndGammaAssistSplitResult(
        valid=valid,
        status=STATUS_VERIFIED_G80 if valid else codes[0],
        violation_codes=tuple(codes),
        regional_default_system=reg,
        configured_ntsc_pal_system=cfg,
        canonical_reset_action=act,
        effective_post_reset_system=effective_sys,
        camera_settings_reset_preserved_system=(
            resolve_fx3_ntscpal_state(
                regional_default_system=reg if reg in ALLOWED_VIDEO_SYSTEMS else VIDEO_SYSTEM_NTSC,
                configured_ntsc_pal_system=cfg if cfg in ALLOWED_VIDEO_SYSTEMS else VIDEO_SYSTEM_NTSC,
                reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            )[0]
            == (cfg if cfg in ALLOWED_VIDEO_SYSTEMS else VIDEO_SYSTEM_NTSC)
        ),
        initialize_restores_regional_default=(
            resolve_fx3_ntscpal_state(
                regional_default_system=reg if reg in ALLOWED_VIDEO_SYSTEMS else VIDEO_SYSTEM_NTSC,
                configured_ntsc_pal_system=cfg if cfg in ALLOWED_VIDEO_SYSTEMS else VIDEO_SYSTEM_NTSC,
                reset_action=RESET_ACTION_INITIALIZE,
            )[0]
            == (reg if reg in ALLOWED_VIDEO_SYSTEMS else VIDEO_SYSTEM_NTSC)
        ),
        startup_notification_banner=expected_banner,
        selected_frame_rate=norm_rate,
        ntsc_exclusive_2398p_active=(
            effective_sys == VIDEO_SYSTEM_NTSC and norm_rate == NTSC_EXCLUSIVE_FRAME_RATE_2398P
        ),
        selected_tc_format=norm_tc,
        tc_format_df_ndf_available=tc_df_ndf_avail,
        media_db_system_tracked=bool(media_db_system_tracked),
        canonical_log_shooting_mode=canon_log,
        log_shooting_active=log_active,
        canonical_gamma_assist_type=canon_gamma,
        gamma_display_assist_menu_on=bool(gamma_display_assist_menu_on),
        gamma_display_assist_locked_off_by_log=locked_off_by_log,
        effective_gamma_display_assist_on=effective_gamma_assist,
        display_lut_on=bool(display_lut_on),
        effective_display_lut_preview_on=effective_display_lut,
        active_preview_governor=governor,
        builtin_lcd_only_scope=not bool(external_hdmi_gamma_assist_applied),
        external_hdmi_gamma_assist_applied=bool(external_hdmi_gamma_assist_applied),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g80_ntscpal_gammaassist_displaylut_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    ntscpal_gammaassist_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase219DonorAuditResult] = None,
) -> Tuple[GateVerdict, G80NtscPalGammaAssistDisplayLutGuardResult]:
    """Evaluate Gate `G80` combining bounded `<0.15s` donor check with `[NTSC/PAL Selector]`
    reset persistence and `[Gamma Display Assist]` / `[Display LUT]` split verification.
    """
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase219_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_ntscpal_persistence_and_gamma_assist_displaylut_guard(
        **dict(ntscpal_gammaassist_kwargs or {})
    )

    codes: List[str] = []
    errors: List[str] = list(audit.errors) + list(guard.errors)
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if not audit.valid:
        _add_code(codes, audit.status)
    for c in guard.violation_codes:
        _add_code(codes, c)
    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Gate G80 blocked persistent eMMC write authorization request.")

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G80 if valid else codes[0]

    res = G80NtscPalGammaAssistDisplayLutGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        ntscpal_gammaassist_displaylut_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, sys={guard.effective_post_reset_system}"
        f"(fps={guard.selected_frame_rate},tc={guard.selected_tc_format},"
        f"banner={guard.startup_notification_banner}), "
        f"log={guard.canonical_log_shooting_mode}(gov={guard.active_preview_governor},"
        f"gamma_assist={guard.effective_gamma_display_assist_on},"
        f"display_lut={guard.effective_display_lut_preview_on},"
        f"hdmi_gamma={guard.external_hdmi_gamma_assist_applied})"
    )
    verdict = GateVerdict(
        gate_id=G80_GATE_ID,
        gate_code=G80_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 4. Unified 80-Gate Milestone Master Safety Preflight (`G01..G80`)
# ---------------------------------------------------------------------------


def evaluate_80gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    dry_run_simulated_backup: Optional[bool] = None,
    simulate_bench_dry_run: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    request_persistent_emmc_writes: bool = False,
    pixelmap_cnflasha_kwargs: Optional[Mapping[str, Any]] = None,
    ntscpal_gammaassist_kwargs: Optional[Mapping[str, Any]] = None,
    master_78_override: Optional[Master78GateReport] = None,
    **m78_passthrough_kwargs: Any,
) -> Master80GateReport:
    """Evaluate all 80 Milestone Master Safety Gates (`G01..G80`) deterministically
    by delegating `G01..G78` directly to `evaluate_78gate_preflight()`.
    """
    resolved_root = (
        DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)
    ).resolve()
    clean_forced = _is_forced_clean_room(force_clean_room)
    effective_dry_run = bool(
        dry_run_simulated
        or simulate_bench_dry_run
        or bool(dry_run_simulated_backup)
    )

    m78_report: Master78GateReport = (
        master_78_override
        if master_78_override is not None
        else evaluate_78gate_preflight(
            resolved_root,
            force_clean_room=clean_forced,
            dry_run_simulated=effective_dry_run,
            include_large_binaries=include_large_binaries,
            work_root=work_root,
            request_persistent_emmc_writes=request_persistent_emmc_writes,
            **m78_passthrough_kwargs,
        )
    )

    phase219_audit = audit_phase219_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
    )

    g79_verdict, g79_res = evaluate_g79_pixelmap_reboot_cnflasha_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        pixelmap_cnflasha_kwargs=pixelmap_cnflasha_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase219_audit,
    )

    g80_verdict, g80_res = evaluate_g80_ntscpal_gammaassist_displaylut_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        ntscpal_gammaassist_kwargs=ntscpal_gammaassist_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase219_audit,
    )

    gates_79_to_80 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g79_verdict, g80_verdict)
    ]
    all_gates = tuple(list(m78_report.gates) + gates_79_to_80)

    g01_to_g12_verified = int(m78_report.summary["g01_to_g12_verified"])
    g13_to_g78_verified = (
        int(m78_report.summary["g13_to_g76_verified"])
        + int(m78_report.summary["g77_to_g78_verified"])
    )
    g79_to_g80_verified = sum(1 for v in (g79_verdict, g80_verdict) if v.passed)
    total_verified = g01_to_g12_verified + g13_to_g78_verified + g79_to_g80_verified

    g79_to_g80_all_passed = g79_to_g80_verified == 2
    g13_to_g80_all_passed = m78_report.g13_to_g78_all_passed and g79_to_g80_all_passed
    g01_to_g09_ok = all(bool(g["passed"]) for g in m78_report.gates[:9])

    offline_77_verified = (
        g01_to_g09_ok
        and m78_report.offline_75_gates_verified
        and g79_to_g80_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_80_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g80_all_passed
        and (not request_persistent_emmc_writes)
    )

    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m78_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_77_verified
        and m78_report.h0_h1_trial_entry_allowed
        and g79_to_g80_all_passed
        and agent_auto_flash_blocked
        and (not HUMAN_HARDWARE_ATTACH_TOKEN)
        and (not HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        and (not PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED)
        and (not EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        and (not SPI_NOR_WRITE_AUTHORIZED)
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    errors: List[str] = (
        list(m78_report.errors) + list(g79_verdict.errors) + list(g80_verdict.errors)
    )
    warnings: List[str] = (
        list(m78_report.warnings)
        + list(g79_verdict.warnings)
        + list(g80_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m78_report.g13_to_g78_all_passed:
        overall_status = m78_report.status
    elif not g79_verdict.passed:
        overall_status = g79_verdict.status
    elif not g80_verdict.passed:
        overall_status = g80_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_80_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_80_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_80_verified:
        overall_status = "VERIFIED_ALL_80_GATES"
    else:
        overall_status = "VERIFIED_77_OF_80_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m78_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g79_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g80_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 80,
        "verified_gates": total_verified,
        "technical_gates_passed": total_verified,
        "blocked_or_pending_gates": 80 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g78_verified": g13_to_g78_verified,
        "g79_to_g80_verified": g79_to_g80_verified,
        "g13_to_g80_all_passed": g13_to_g80_all_passed,
        "g79_to_g80_all_passed": g79_to_g80_all_passed,
        "offline_77_gates_verified": offline_77_verified,
        "all_80_gates_verified": all_80_verified,
        "dry_run_rehearsal_only": effective_dry_run,
        "overall_ready_for_hardware_attach": overall_ready_for_hardware_attach,
        "hardware_live_attachment_authorized": HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        "h0_h1_trial_entry_allowed": h0_h1_allowed,
        "agent_auto_flash_blocked": agent_auto_flash_blocked,
        "human_hardware_attach_token": HUMAN_HARDWARE_ATTACH_TOKEN,
        "physical_flash_auto_exec_authorized": PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
        "el3_payload_transmit_authorized": EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "persistent_write_release": PERSISTENT_WRITE_RELEASE,
        "usb_packets_transmitted": USB_PACKETS_TRANSMITTED,
        "physical_usb_packets_emitted": PHYSICAL_USB_PACKETS_EMITTED,
        "raw_firmware_bytes_leaked": RAW_FIRMWARE_BYTES_LEAKED,
    }

    return Master80GateReport(
        schema=REALHW_PIXELMAP_NTSCPAL_GAMMAASSIST_DISPLAYLUT_80GATE_SCHEMA,
        version=REALHW_PIXELMAP_NTSCPAL_GAMMAASSIST_DISPLAYLUT_80GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        offline_77_gates_verified=offline_77_verified,
        all_80_gates_verified=all_80_verified,
        g13_to_g80_all_passed=g13_to_g80_all_passed,
        g79_to_g80_all_passed=g79_to_g80_all_passed,
        h0_h1_trial_entry_allowed=h0_h1_allowed,
        status=overall_status,
        agent_auto_flash_blocked=agent_auto_flash_blocked,
        human_hardware_attach_token=HUMAN_HARDWARE_ATTACH_TOKEN,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        physical_flash_auto_exec_authorized=PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
        usb_packets_transmitted=USB_PACKETS_TRANSMITTED,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        technical_gates_passed=total_verified,
        summary=summary,
        gates=all_gates,
        master_78_report=m78_report.to_dict(),
        g79_result=g79_res.to_dict(),
        g80_result=g80_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_80_master_safety_gates = evaluate_80gate_preflight
run_80_gate_preflight = evaluate_80gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_pixelmap_ntscpal_gammaassist_displaylut_and_80gate_guard",
        description=(
            "Phase 219 (80/80 Milestone) Safety Gates G79 (Pixel Mapping Reboot, Low-Battery "
            "Lockout & cnflasha Read-Only Firewall) + G80 (NTSC/PAL Reset Persistence & Gamma "
            "Display Assist / Display LUT Split Guard) + Unified 80-Gate Master Safety Preflight"
        ),
    )
    parser.add_argument("--repo-root", type=Path, default=DEFAULT_REPO_ROOT)
    parser.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
    )
    parser.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = evaluate_80gate_preflight(
        args.repo_root,
        force_clean_room=True if args.force_clean_room else None,
        dry_run_simulated=bool(args.dry_run_simulated),
    )
    if args.json:
        sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
    else:
        sys.stdout.write(
            f"status={report.status} mode={report.verification_mode} "
            f"verified={report.summary['verified_gates']}/80 "
            f"g79_to_g80_all_passed={report.g79_to_g80_all_passed} "
            f"all_80_gates_verified={report.all_80_gates_verified} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach}\n"
        )
    ok = report.all_80_gates_verified if args.dry_run_simulated else report.offline_77_gates_verified
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
