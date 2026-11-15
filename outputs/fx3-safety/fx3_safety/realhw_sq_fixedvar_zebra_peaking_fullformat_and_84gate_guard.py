"""Phase 228 Real-Hardware Safety Gates (`G83..G84`) & Unified 84-Gate Master
Safety Preflight (`verify-84-gates`) for Sony `ILME-FX3` (`Ver. 7.02`).

Implements Wave-32 official Sony `ILME-FX3` (`Ver. 7.02`) hardware rules while delegating
Gates `G01..G82` directly to `evaluate_82gate_preflight()` from
`realhw_steadyshot_ciz_powersave_autotemp_and_82gate_guard.py`:

1. **Gate G83 (`G83_SQ_FIXED_VARIABLE_6LOCK_MATRIX_AND_ZEBRA_PEAKING_HDMI_CLEANFEED_GUARD`)**:
   - Enforces `Ver. 7.00+` / `7.02` `[Mode Settings]` = `[Fixed/Variable]` (`MENU -> Shooting ->
     [Shooting Mode] -> [Shoot Mode] -> [S&Q(Slow&Quick Motion)] -> [Mode Settings]`), locking
     legacy `MENU -> Shooting -> [Image Quality/Rec] -> [S&Q Settings]` in favor of direct `[FPS]`
     (`Home (FPS)`) frame-rate control while codec/bit-rate follow `[Movie Settings]` & `[File Format]`.
   - Enforces all 6 official Sony `ILME-FX3` S&Q disqualifications:
     (1) `0ch` zero audio recorded (`sound_recorded_in_sq == False`),
     (2) `[Audio Out Timing]` (`Live` default zero-delay vs `Lip Sync` video-aligned) disabled in S&Q,
     (3) `[Time Code Run]` & HDMI `[Time Code Output]` unavailable in S&Q,
     (4) `240fps` (NTSC) / `200fps` (PAL) blocked on `XAVC HS 4K`, `XAVC S 4K`, `XAVC S-I 4K`,
         and `XAVC S-I DCI 4K` (requires `XAVC S HD` or `XAVC S-I HD`),
     (5) `120fps` (NTSC) / `100fps` (PAL) blocked on `XAVC S-I DCI 4K` (`4096x2160`), and
     (6) `[Proxy Recording]` blocked in S&Q whenever `Rec Frame Rate` is `119.88p`/`100p` OR
         S&Q capture `Frame Rate >= 120fps`/`100fps`.
   - Enforces hardware HDMI assist-overlay suppression: neither `[Zebra Display]` stripes nor
     `[Peaking Display]` (`On`/`Off`, `High`/`Mid`/`Low`, `Red`/`Yellow`/`Blue`/`White`) outlines
     are ever output over HDMI even when `[HDMI Info. Display] = [On]`.
   - Bounded `< 0.15s` `O_RDONLY` local donor check (`raw_firmware_bytes_leaked == 0`) with
     deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` synthetic fallback.

2. **Gate G84 (`G84_ZEBRA_CAMERA_SETTINGS_RESET_SURVIVAL_AND_FULL_FORMAT_CHORD_VAULT_GUARD`)**:
   - Verifies `[Zebra Display]` (`Off`/`On`, Control Wheel Left default `[Zebra Display Select]`)
     and `[Zebra Level]` (`70..100+`, `Custom 1` Standard+Range exposure band, `Custom 2`
     Minimum/Lower-Limit overexposure threshold) survive `[Camera Settings Reset]` and are cleared
     back to factory `Off` / `70` exclusively by `[Initialize]`.
   - Enforces hard-lock on Slot 1 `[Format]` — covering `[Enter]` **Quick Format** (metadata-only),
     `(Delete)`-toggled **Full Format** (all data blocks + metadata, plus mid-cancel
     data-already-erased / card-remains-usable semantics), and the physical **`MENU + (Delete)`
     (`~2s`) shooting-screen chord** — whenever Slot 1 holds an unverified or active Tier-0
     recovery vault (`pnflasha` / `cnflasha` / `CAMSET01.DAT`).

3. **Unified `verify-84-gates` Master Safety Preflight**:
   - Combines `G01..G82` + `G83` + `G84` (`81/84` offline pass with the 3 physical-bench
     Tier-0 gates `G10..G12` awaiting receipt; `84/84` in `--simulate-bench-dry-run`).

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
)
from .realhw_fx3a_firewall_xlrh1_mishoe_and_64gate_guard import (
    FX3_MODEL_ID,
    FX3_MODEL_NAME,
)
from .realhw_pixelmap_ntscpal_gammaassist_displaylut_and_80gate_guard import (
    RESET_ACTION_CAMERA_SETTINGS_RESET,
    RESET_ACTION_INITIALIZE,
    RESET_ACTION_NONE,
    VIDEO_SYSTEM_NTSC,
    VIDEO_SYSTEM_PAL,
)
from .realhw_steadyshot_ciz_powersave_autotemp_and_82gate_guard import (
    Master82GateReport,
    SHOOT_MODE_MOVIE,
    SHOOT_MODE_SQ,
    SHOOT_MODE_STILL,
    evaluate_82gate_preflight,
)
from .thermal_pwm_and_power_guard import (
    ENV_FORCE_CLEAN_ROOM,
    resolve_donor_thermal_power_paths,
)


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

REALHW_SQ_FIXEDVAR_ZEBRA_PEAKING_FULLFORMAT_84GATE_SCHEMA: str = (
    "fx3-realhw-sq-fixedvar-zebra-peaking-fullformat-84gate-preflight-v1"
)
REALHW_SQ_FIXEDVAR_ZEBRA_PEAKING_FULLFORMAT_84GATE_VERSION: str = "1.0.0"

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
FX3_DEFAULT_FW_VERSION_G83: str = "7.02"
FX3_SQ_FIXEDVAR_MIN_FW_TUPLE: Tuple[int, int] = (7, 0)

# Gate IDs & Canonical Codes for G83..G84
G83_GATE_ID: str = (
    "G83_sq_fixed_variable_6lock_matrix_and_zebra_peaking_hdmi_cleanfeed_guard"
)
G83_GATE_CODE: str = (
    "G83_SQ_FIXED_VARIABLE_6LOCK_MATRIX_AND_ZEBRA_PEAKING_HDMI_CLEANFEED_GUARD"
)
GATE_G83_SQ_FIXED_VARIABLE_6LOCK_MATRIX_AND_ZEBRA_PEAKING_HDMI_CLEANFEED_GUARD: str = (
    G83_GATE_CODE
)
G83: str = G83_GATE_CODE

G84_GATE_ID: str = (
    "G84_zebra_camera_settings_reset_survival_and_full_format_chord_vault_guard"
)
G84_GATE_CODE: str = (
    "G84_ZEBRA_CAMERA_SETTINGS_RESET_SURVIVAL_AND_FULL_FORMAT_CHORD_VAULT_GUARD"
)
GATE_G84_ZEBRA_CAMERA_SETTINGS_RESET_SURVIVAL_AND_FULL_FORMAT_CHORD_VAULT_GUARD: str = (
    G84_GATE_CODE
)
G84: str = G84_GATE_CODE

# Status & Violation Codes
STATUS_VERIFIED_SAFE: str = "VERIFIED_SAFE"
STATUS_VERIFIED_G83: str = (
    "VERIFIED_SQ_FIXED_VARIABLE_6LOCK_MATRIX_AND_ZEBRA_PEAKING_HDMI_CLEANFEED_GUARD"
)
STATUS_VERIFIED_G84: str = (
    "VERIFIED_ZEBRA_CAMERA_SETTINGS_RESET_SURVIVAL_AND_FULL_FORMAT_CHORD_VAULT_GUARD"
)

STATUS_BLOCKED_G83_MODE_SETTINGS_FIXED_VARIABLE_OR_SQ_SETTINGS_LOCK_VIOLATION: str = (
    "BLOCKED_G83_MODE_SETTINGS_FIXED_VARIABLE_OR_SQ_SETTINGS_LOCK_VIOLATION"
)
STATUS_BLOCKED_G83_SQ_6LOCK_AUDIO_TC_CODEC_OR_PROXY_VIOLATION: str = (
    "BLOCKED_G83_SQ_6LOCK_AUDIO_TC_CODEC_OR_PROXY_VIOLATION"
)
STATUS_BLOCKED_G83_HDMI_ZEBRA_OR_PEAKING_ASSIST_OVERLAY_LEAK: str = (
    "BLOCKED_G83_HDMI_ZEBRA_OR_PEAKING_ASSIST_OVERLAY_LEAK"
)
STATUS_BLOCKED_G83_TELEMETRY_INVALID: str = (
    "BLOCKED_G83_SQ_FIXEDVAR_ZEBRA_PEAKING_TELEMETRY_INVALID"
)

STATUS_BLOCKED_G84_ZEBRA_LEVEL_OR_CUSTOM_THRESHOLD_INVALID: str = (
    "BLOCKED_G84_ZEBRA_LEVEL_OR_CUSTOM_THRESHOLD_INVALID"
)
STATUS_BLOCKED_G84_ZEBRA_CAMERA_SETTINGS_RESET_PERSISTENCE_VIOLATION: str = (
    "BLOCKED_G84_ZEBRA_CAMERA_SETTINGS_RESET_PERSISTENCE_VIOLATION"
)
STATUS_BLOCKED_G84_SLOT1_TIER0_VAULT_FORMAT_OR_CHORD_LOCKOUT: str = (
    "BLOCKED_G84_SLOT1_TIER0_VAULT_FORMAT_OR_CHORD_LOCKOUT"
)
STATUS_BLOCKED_G84_FULL_FORMAT_CANCEL_SEMANTICS_MISMATCH: str = (
    "BLOCKED_G84_FULL_FORMAT_CANCEL_SEMANTICS_MISMATCH"
)
STATUS_BLOCKED_G84_TELEMETRY_INVALID: str = (
    "BLOCKED_G84_ZEBRA_RESET_FULLFORMAT_TELEMETRY_INVALID"
)

STATUS_BLOCKED_PHASE228_DONOR_INTEGRITY: str = (
    "BLOCKED_PHASE228_84GATE_DONOR_INTEGRITY_OR_BUDGET_EXCEEDED"
)
STATUS_BLOCKED_PERSISTENT_EMMC_WRITE: str = (
    "BLOCKED_BY_PERSISTENT_EMMC_WRITE_REDLINE"
)

# Gate G83 Constants — [Mode Settings] ([Fixed/Variable]), S&Q 6-Lock Matrix,
# [Audio Out Timing], and Zebra/Peaking Local-LCD-Only HDMI Clean-Feed Isolation
SQ_MODE_SETTINGS_MENU_PATH: str = (
    "MENU -> Shooting -> [Shooting Mode] -> [Shoot Mode] -> "
    "[S&Q(Slow&Quick Motion)] -> [Mode Settings]"
)
LEGACY_SQ_SETTINGS_MENU_PATH: str = (
    "MENU -> Shooting -> [Image Quality/Rec] -> [S&Q Settings]"
)
AUDIO_OUT_TIMING_MENU_PATH: str = (
    "MENU -> Shooting -> [Audio Recording] -> [Audio Out Timing]"
)
PEAKING_DISPLAY_MENU_PATH: str = "MENU -> Focus -> [Peaking Display]"

MODE_SETTINGS_FIXED_VARIABLE: str = "Fixed/Variable"
MODE_SETTINGS_VARIABLE: str = "Variable"
ALLOWED_SQ_MODE_SETTINGS: Tuple[str, ...] = (
    MODE_SETTINGS_FIXED_VARIABLE,
    MODE_SETTINGS_VARIABLE,
)

ALLOWED_SHOOT_MODES_G83: Tuple[str, ...] = (
    SHOOT_MODE_MOVIE,
    SHOOT_MODE_SQ,
    SHOOT_MODE_STILL,
)

FILE_FORMAT_XAVC_HS_4K: str = "XAVC HS 4K"
FILE_FORMAT_XAVC_S_4K: str = "XAVC S 4K"
FILE_FORMAT_XAVC_S_HD: str = "XAVC S HD"
FILE_FORMAT_XAVC_SI_4K: str = "XAVC S-I 4K"
FILE_FORMAT_XAVC_SI_DCI_4K: str = "XAVC S-I DCI 4K"
FILE_FORMAT_XAVC_SI_HD: str = "XAVC S-I HD"
ALLOWED_MOVIE_FILE_FORMATS_G83: Tuple[str, ...] = (
    FILE_FORMAT_XAVC_HS_4K,
    FILE_FORMAT_XAVC_S_4K,
    FILE_FORMAT_XAVC_S_HD,
    FILE_FORMAT_XAVC_SI_4K,
    FILE_FORMAT_XAVC_SI_DCI_4K,
    FILE_FORMAT_XAVC_SI_HD,
)
SQ_240_200FPS_BLOCKED_4K_FORMATS: Tuple[str, ...] = (
    FILE_FORMAT_XAVC_HS_4K,
    FILE_FORMAT_XAVC_S_4K,
    FILE_FORMAT_XAVC_SI_4K,
    FILE_FORMAT_XAVC_SI_DCI_4K,
)
SQ_120_100FPS_BLOCKED_DCI4K_FORMATS: Tuple[str, ...] = (
    FILE_FORMAT_XAVC_SI_DCI_4K,
)

NTSC_SQ_ALLOWED_REC_RATES: Tuple[str, ...] = (
    "23.98p",
    "24.00p",
    "29.97p",
    "59.94p",
    "119.88p",
)
PAL_SQ_ALLOWED_REC_RATES: Tuple[str, ...] = (
    "25p",
    "50p",
    "100p",
)
NTSC_SQ_MAX_CAPTURE_FPS: int = 240
PAL_SQ_MAX_CAPTURE_FPS: int = 200
SQ_MIN_CAPTURE_FPS: int = 1
SQ_PROXY_BLOCKED_REC_RATES: Tuple[str, ...] = ("119.88p", "100p")
SQ_PROXY_BLOCKED_CAPTURE_FPS_FLOOR: float = 100.0

AUDIO_OUT_TIMING_LIVE: str = "Live"
AUDIO_OUT_TIMING_LIP_SYNC: str = "Lip Sync"
AUDIO_OUT_TIMING_FACTORY_DEFAULT: str = AUDIO_OUT_TIMING_LIVE
ALLOWED_AUDIO_OUT_TIMING_MODES: Tuple[str, ...] = (
    AUDIO_OUT_TIMING_LIVE,
    AUDIO_OUT_TIMING_LIP_SYNC,
)

SQ_6_DISQUALIFICATIONS: Tuple[str, ...] = (
    "sq_0ch_no_sound_recorded",
    "sq_audio_out_timing_disabled",
    "sq_time_code_run_and_output_unavailable",
    "sq_240_200fps_blocked_on_4k_formats",
    "sq_120_100fps_blocked_on_xavc_si_dci_4k",
    "sq_proxy_blocked_at_hfr_119_88p_100p_or_ge_100fps",
)

PEAKING_DISPLAY_OFF: str = "Off"
PEAKING_DISPLAY_ON: str = "On"
PEAKING_FACTORY_DEFAULT_DISPLAY: str = PEAKING_DISPLAY_OFF
ALLOWED_PEAKING_DISPLAY_MODES: Tuple[str, ...] = (
    PEAKING_DISPLAY_OFF,
    PEAKING_DISPLAY_ON,
)
PEAKING_LEVEL_HIGH: str = "High"
PEAKING_LEVEL_MID: str = "Mid"
PEAKING_LEVEL_LOW: str = "Low"
PEAKING_FACTORY_DEFAULT_LEVEL: str = PEAKING_LEVEL_MID
ALLOWED_PEAKING_LEVELS: Tuple[str, ...] = (
    PEAKING_LEVEL_HIGH,
    PEAKING_LEVEL_MID,
    PEAKING_LEVEL_LOW,
)
PEAKING_COLOR_RED: str = "Red"
PEAKING_COLOR_YELLOW: str = "Yellow"
PEAKING_COLOR_BLUE: str = "Blue"
PEAKING_COLOR_WHITE: str = "White"
PEAKING_FACTORY_DEFAULT_COLOR: str = PEAKING_COLOR_WHITE
ALLOWED_PEAKING_COLORS: Tuple[str, ...] = (
    PEAKING_COLOR_RED,
    PEAKING_COLOR_YELLOW,
    PEAKING_COLOR_BLUE,
    PEAKING_COLOR_WHITE,
)
CONTROL_WHEEL_RIGHT_DEFAULT_PEAKING_SELECT: str = "Peaking Display Select"

# Gate G84 Constants — [Zebra Display] / [Zebra Level] Reset Survival &
# Slot-1 [Format] (Quick / Full / MENU+Delete 2s Chord) Tier-0 Vault Guard
ZEBRA_DISPLAY_MENU_PATH: str = "MENU -> Exposure/Color -> [Zebra Display]"
MEDIA_FORMAT_MENU_PATH: str = "MENU -> Shooting -> [Media] -> [Format]"
CONTROL_WHEEL_LEFT_DEFAULT_ZEBRA_SELECT: str = "Zebra Display Select"

ZEBRA_DISPLAY_OFF: str = "Off"
ZEBRA_DISPLAY_ON: str = "On"
ZEBRA_FACTORY_DEFAULT_DISPLAY: str = ZEBRA_DISPLAY_OFF
ALLOWED_ZEBRA_DISPLAY_MODES: Tuple[str, ...] = (
    ZEBRA_DISPLAY_OFF,
    ZEBRA_DISPLAY_ON,
)

ZEBRA_FACTORY_DEFAULT_LEVEL: str = "70"
ZEBRA_LEVEL_CUSTOM_1: str = "Custom 1"
ZEBRA_LEVEL_CUSTOM_2: str = "Custom 2"
ALLOWED_ZEBRA_PRESET_LEVELS: Tuple[str, ...] = (
    "70",
    "75",
    "80",
    "85",
    "90",
    "95",
    "100",
    "100+",
)
ALLOWED_ZEBRA_CUSTOM_MODES: Tuple[str, ...] = (
    ZEBRA_LEVEL_CUSTOM_1,
    ZEBRA_LEVEL_CUSTOM_2,
)
ALLOWED_ZEBRA_LEVELS: Tuple[str, ...] = (
    ALLOWED_ZEBRA_PRESET_LEVELS + ALLOWED_ZEBRA_CUSTOM_MODES
)
ZEBRA_CUSTOM_IRE_MIN: int = 0
ZEBRA_CUSTOM_IRE_MAX: int = 109
ZEBRA_CUSTOM1_RANGE_MIN: int = 1
ZEBRA_CUSTOM1_RANGE_MAX: int = 30

ALLOWED_RESET_ACTIONS_G84: Tuple[str, ...] = (
    RESET_ACTION_NONE,
    RESET_ACTION_CAMERA_SETTINGS_RESET,
    RESET_ACTION_INITIALIZE,
)

FORMAT_SLOT_NONE: str = "NONE"
FORMAT_SLOT_1: str = "SLOT_1"
FORMAT_SLOT_2: str = "SLOT_2"
ALLOWED_FORMAT_TARGET_SLOTS: Tuple[str, ...] = (
    FORMAT_SLOT_NONE,
    FORMAT_SLOT_1,
    FORMAT_SLOT_2,
)

FORMAT_MODE_NONE: str = "NONE"
FORMAT_MODE_QUICK: str = "QUICK_FORMAT"
FORMAT_MODE_FULL: str = "FULL_FORMAT"
ALLOWED_FORMAT_MODES: Tuple[str, ...] = (
    FORMAT_MODE_NONE,
    FORMAT_MODE_QUICK,
    FORMAT_MODE_FULL,
)

FORMAT_TRIGGER_NONE: str = "NONE"
FORMAT_TRIGGER_MENU_ENTER: str = "MENU_ENTER_QUICK"
FORMAT_TRIGGER_CONFIRM_DELETE_TOGGLE: str = "CONFIRM_DELETE_TOGGLE_FULL"
FORMAT_TRIGGER_MENU_DELETE_2S_CHORD: str = "MENU_PLUS_DELETE_2S_CHORD"
ALLOWED_FORMAT_TRIGGERS: Tuple[str, ...] = (
    FORMAT_TRIGGER_NONE,
    FORMAT_TRIGGER_MENU_ENTER,
    FORMAT_TRIGGER_CONFIRM_DELETE_TOGGLE,
    FORMAT_TRIGGER_MENU_DELETE_2S_CHORD,
)
MENU_DELETE_CHORD_MIN_HOLD_SECONDS: float = 2.0
TIER0_VAULT_REQUIRED_ARTIFACTS: Tuple[str, ...] = (
    "pnflasha",
    "cnflasha",
    "CAMSET01.DAT",
)

# Pinned FX3 v7.02 & FX6 v6.01 Donor Specs (bounded <0.15s O_RDONLY verification)
PINNED_PHASE228_DONOR_SPECS: Mapping[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_cpapp_b": (
        "fx3",
        "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin",
        15_980_568,
        "c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba",
        (
            b"ILME-FX3",
            b"Zebra",
            b"Peaking",
            b"Format",
            b"Audio",
            b"Proxy",
            b"Time",
            b"HDMI",
            b"FPS",
            b"Reset",
            b"Delete",
            b"Live",
            b"Custom",
            b"BK4",
            b"/setting",
        ),
        "fx3/cpapp-b.bin::{15980568B,ILME-FX3,Zebra,Peaking,Format,Audio,Proxy,Time,HDMI,FPS,Reset,Delete,Live,Custom}",
    ),
    "fx3_saveload_so": (
        "fx3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libSaveLoadSettings.so",
        18_760,
        "07819f42bdad381ecdd41c3765c117c33b0c44c25be36279b26f83906d244cb7",
        (b"\x7fELF", b"SaveLoadSettings", b"Settings", b"Save", b"Backup"),
        "fx3/libSaveLoadSettings.so::{18760B,ELF,SaveLoadSettings,Settings,Save,Backup}",
    ),
    "fx3_bk4_bin": (
        "fx3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin",
        2_229_740,
        "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2",
        (b"BK4", b"ILME-FX3", b"FTP", b"TC", b"/setting"),
        "fx3/FX3-CX95900_ALLLANG-Backup.bin::{2229740B,BK4,ILME-FX3,FTP,TC,/setting}",
    ),
    "fx6_bk4_bin": (
        "fx6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0110_backup/SYSIPSX-DSLR/CHAPLIN/CX95898_NTSC.bin",
        2_253_333,
        "e2eafd4e950ead94fdba64722b225b9ccf4cf294ce4c1cf956b9e62926bbf89e",
        (b"BK4", b"NTSC", b"TC", b"Settings", b"/setting"),
        "fx6/CX95898_NTSC.bin::{2253333B,BK4,NTSC,TC,Settings,/setting}",
    ),
}


# ---------------------------------------------------------------------------
# Data Models (Zero raw bytes reprs; hex strings / ASCII markers only)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase228DonorAuditResult:
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
class SqFixedVar6LockAndZebraPeakingHdmiResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    body_model_name: str
    body_model_id_hex: str
    firmware_version: str
    video_system: str
    shoot_mode: str
    sq_mode_settings: str
    legacy_sq_settings_menu_locked: bool
    direct_fps_control_active: bool
    legacy_sq_settings_mutation_attempted: bool
    movie_file_format: str
    rec_frame_rate: str
    sq_capture_fps: int
    sq_playback_speed_ratio: float
    sq_audio_channels_recorded: int
    sound_recorded_in_sq: bool
    audio_out_timing_mode: str
    audio_out_timing_available: bool
    time_code_run_available: bool
    hdmi_time_code_output_available: bool
    proxy_recording_on: bool
    sq_6_locks_evaluated: Tuple[str, ...]
    all_6_sq_locks_enforced: bool
    zebra_display_mode: str
    peaking_display_mode: str
    peaking_level: str
    peaking_color: str
    wheel_right_default_function: str
    hdmi_info_display_on: bool
    camera_lcd_blanked_by_hdmi_info: bool
    local_lcd_zebra_rendered: bool
    local_lcd_peaking_rendered: bool
    hdmi_zebra_overlay_rendered: bool
    hdmi_peaking_overlay_rendered: bool
    hdmi_assist_clean_feed_enforced: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ZebraResetSurvivalAndFullFormatVaultResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    wheel_left_default_function: str
    pre_reset_zebra_display: str
    pre_reset_zebra_level: str
    custom1_std_level: int
    custom1_exposure_range: int
    custom1_band_min_ire: int
    custom1_band_max_ire: int
    custom2_lower_limit_ire: int
    reset_action: str
    expected_post_reset_zebra_display: str
    expected_post_reset_zebra_level: str
    effective_post_reset_zebra_display: str
    effective_post_reset_zebra_level: str
    zebra_survived_camera_settings_reset: bool
    slot1_tier0_vault_present: bool
    slot1_tier0_vault_active: bool
    slot1_vault_artifacts: Tuple[str, ...]
    off_camera_sha256_verified: bool
    slot1_vault_card_removed_or_wp_locked: bool
    slot1_format_hard_locked: bool
    target_slot: str
    format_trigger: str
    format_mode: str
    menu_delete_chord_hold_seconds: float
    menu_delete_chord_dialog_invoked: bool
    full_format_wipes_all_data_blocks: bool
    full_format_canceled_midway: bool
    mid_cancel_prior_data_erased: bool
    mid_cancel_card_usable: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G83SqFixedVarZebraPeakingGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    sq_fixedvar_zebra_peaking_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G84ZebraResetFullFormatVaultGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    zebra_reset_fullformat_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master84GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    offline_81_gates_verified: bool
    all_84_gates_verified: bool
    g13_to_g84_all_passed: bool
    g83_to_g84_all_passed: bool
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
    master_82_report: Dict[str, Any]
    g83_result: Dict[str, Any]
    g84_result: Dict[str, Any]
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


def _norm_token(val: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", (val or "").strip().upper()).strip("_")


def _parse_fw_tuple(fw_str: str) -> Optional[Tuple[int, int]]:
    m = re.match(r"^\s*[vV]?(\d+)\.(\d+)(?:\.\d+)?\s*$", (fw_str or "").strip())
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def _norm_shoot_mode(val: str) -> str:
    s = (val or "").strip().upper().replace(" ", "")
    if s in ("MOVIE", "NORMAL_MOVIE", "VIDEO"):
        return SHOOT_MODE_MOVIE
    if s in ("S&Q", "SQ", "S_Q", "SLOW_AND_QUICK"):
        return SHOOT_MODE_SQ
    if s in ("STILL", "PHOTO"):
        return SHOOT_MODE_STILL
    return s


def _norm_video_system(val: str) -> Optional[str]:
    t = _norm_token(val)
    if t == "NTSC":
        return VIDEO_SYSTEM_NTSC
    if t == "PAL":
        return VIDEO_SYSTEM_PAL
    return None


def _norm_sq_mode_settings(val: str) -> Optional[str]:
    s = re.sub(r"\s+", "", (val or "").strip().lower())
    if s in ("fixed/variable", "fixed_variable", "fixedvariable"):
        return MODE_SETTINGS_FIXED_VARIABLE
    if s in ("variable", "legacy_variable"):
        return MODE_SETTINGS_VARIABLE
    return None


def _norm_movie_file_format(val: str) -> Optional[str]:
    s = re.sub(r"\s+", " ", (val or "").strip().upper())
    mapping = {
        "XAVC HS 4K": FILE_FORMAT_XAVC_HS_4K,
        "XAVC_HS_4K": FILE_FORMAT_XAVC_HS_4K,
        "XAVC S 4K": FILE_FORMAT_XAVC_S_4K,
        "XAVC_S_4K": FILE_FORMAT_XAVC_S_4K,
        "XAVC S HD": FILE_FORMAT_XAVC_S_HD,
        "XAVC_S_HD": FILE_FORMAT_XAVC_S_HD,
        "XAVC S-I 4K": FILE_FORMAT_XAVC_SI_4K,
        "XAVC_SI_4K": FILE_FORMAT_XAVC_SI_4K,
        "XAVC S-I DCI 4K": FILE_FORMAT_XAVC_SI_DCI_4K,
        "XAVC_SI_DCI_4K": FILE_FORMAT_XAVC_SI_DCI_4K,
        "XAVC S-I HD": FILE_FORMAT_XAVC_SI_HD,
        "XAVC_SI_HD": FILE_FORMAT_XAVC_SI_HD,
    }
    return mapping.get(s)


def _norm_movie_rate(val: str) -> str:
    s = (val or "").strip().lower().replace("fps", "p").replace(" ", "")
    aliases = {
        "23.98p": "23.98p",
        "23.976p": "23.98p",
        "24.00p": "24.00p",
        "24p": "24.00p",
        "25p": "25p",
        "29.97p": "29.97p",
        "30p": "29.97p",
        "50p": "50p",
        "59.94p": "59.94p",
        "60p": "59.94p",
        "100p": "100p",
        "100.00p": "100p",
        "119.88p": "119.88p",
        "120p": "119.88p",
    }
    return aliases.get(s, (val or "").strip())


def _parse_fps_value(rate_str: Any) -> Optional[float]:
    if isinstance(rate_str, (int, float)) and not isinstance(rate_str, bool):
        return float(rate_str) if _is_finite_num(rate_str) else None
    m = re.match(r"^\s*(\d+(?:\.\d+)?)\s*(?:p|fps)?\s*$", str(rate_str or "").lower())
    return float(m.group(1)) if m else None


def _norm_audio_out_timing(val: str) -> Optional[str]:
    t = _norm_token(val)
    if t == "LIVE":
        return AUDIO_OUT_TIMING_LIVE
    if t == "LIP_SYNC" or t == "LIPSYNC":
        return AUDIO_OUT_TIMING_LIP_SYNC
    return None


def _norm_on_off(val: str) -> Optional[str]:
    t = _norm_token(val)
    if t == "ON":
        return "On"
    if t == "OFF":
        return "Off"
    return None


def _norm_peaking_level(val: str) -> Optional[str]:
    t = _norm_token(val)
    mapping = {"HIGH": PEAKING_LEVEL_HIGH, "MID": PEAKING_LEVEL_MID, "LOW": PEAKING_LEVEL_LOW}
    return mapping.get(t)


def _norm_peaking_color(val: str) -> Optional[str]:
    t = _norm_token(val)
    mapping = {
        "RED": PEAKING_COLOR_RED,
        "YELLOW": PEAKING_COLOR_YELLOW,
        "BLUE": PEAKING_COLOR_BLUE,
        "WHITE": PEAKING_COLOR_WHITE,
    }
    return mapping.get(t)


def _norm_zebra_level(val: Any) -> Optional[str]:
    if isinstance(val, int) and not isinstance(val, bool):
        s = str(val)
    else:
        s = re.sub(r"\s+", " ", str(val or "").strip())
    if s in ALLOWED_ZEBRA_PRESET_LEVELS:
        return s
    t = _norm_token(s)
    if t in ("100_PLUS", "100P"):
        return "100+"
    if t in ("CUSTOM_1", "CUSTOM1"):
        return ZEBRA_LEVEL_CUSTOM_1
    if t in ("CUSTOM_2", "CUSTOM2"):
        return ZEBRA_LEVEL_CUSTOM_2
    return None


def _norm_reset_action(val: str) -> Optional[str]:
    t = _norm_token(val)
    if t in ("NONE", "NO_RESET"):
        return RESET_ACTION_NONE
    if t in ("CAMERA_SETTINGS_RESET", "CAM_SETTINGS_RESET"):
        return RESET_ACTION_CAMERA_SETTINGS_RESET
    if t in ("INITIALIZE", "FACTORY_INITIALIZE"):
        return RESET_ACTION_INITIALIZE
    return None


def _norm_format_slot(val: str) -> Optional[str]:
    t = _norm_token(val)
    if t in ("NONE", "NO_SLOT"):
        return FORMAT_SLOT_NONE
    if t in ("SLOT_1", "SLOT1", "1", "SLOT_A"):
        return FORMAT_SLOT_1
    if t in ("SLOT_2", "SLOT2", "2", "SLOT_B"):
        return FORMAT_SLOT_2
    return None


def _norm_format_mode(val: str) -> Optional[str]:
    t = _norm_token(val)
    if t in ("NONE", "NO_FORMAT"):
        return FORMAT_MODE_NONE
    if t in ("QUICK", "QUICK_FORMAT"):
        return FORMAT_MODE_QUICK
    if t in ("FULL", "FULL_FORMAT"):
        return FORMAT_MODE_FULL
    return None


def _norm_format_trigger(val: str) -> Optional[str]:
    t = _norm_token(val)
    if t in ("NONE", "NO_TRIGGER"):
        return FORMAT_TRIGGER_NONE
    if t in ("MENU_ENTER", "MENU_ENTER_QUICK", "ENTER_QUICK"):
        return FORMAT_TRIGGER_MENU_ENTER
    if t in (
        "CONFIRM_DELETE_TOGGLE_FULL",
        "DELETE_TOGGLE_FULL",
        "CONFIRM_DELETE_FULL",
    ):
        return FORMAT_TRIGGER_CONFIRM_DELETE_TOGGLE
    if t in (
        "MENU_PLUS_DELETE_2S_CHORD",
        "MENU_DELETE_2S_CHORD",
        "MENU_DELETE_CHORD",
    ):
        return FORMAT_TRIGGER_MENU_DELETE_2S_CHORD
    return None


# ---------------------------------------------------------------------------
# 1. Bounded `<0.15s` O_RDONLY Local Donor Audit (`FX3_FX6_FORCE_CLEAN_ROOM=1`)
# ---------------------------------------------------------------------------


def audit_phase228_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    max_budget_seconds: float = DONOR_CHECK_MAX_SECONDS,
) -> Phase228DonorAuditResult:
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
        for key, (_body, rel_path, *_rest) in PINNED_PHASE228_DONOR_SPECS.items():
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
        return Phase228DonorAuditResult(
            valid=within_budget,
            status=(
                STATUS_VERIFIED_SAFE
                if within_budget
                else STATUS_BLOCKED_PHASE228_DONOR_INTEGRITY
            ),
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="O_RDONLY",
            files_inspected=0,
            elapsed_seconds=round(elapsed, 6),
            within_budget_150ms=within_budget,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            checked_markers=tuple(
                spec[5] for spec in PINNED_PHASE228_DONOR_SPECS.values()
            ),
            missing_markers=(),
            fx3_contracts_verified=within_budget,
            fx6_contracts_verified=within_budget,
            sha256_by_artifact={
                k: spec[3] for k, spec in PINNED_PHASE228_DONOR_SPECS.items()
            },
            bytes_by_artifact={
                k: spec[2] for k, spec in PINNED_PHASE228_DONOR_SPECS.items()
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
    ) in PINNED_PHASE228_DONOR_SPECS.items():
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
            f"Local donor O_RDONLY check exceeded budget ({elapsed:.4f}s >= {max_budget_seconds:.4f}s)."
        )

    fx3_keys = {k for k, s in PINNED_PHASE228_DONOR_SPECS.items() if s[0] == "fx3"}
    fx6_keys = {k for k, s in PINNED_PHASE228_DONOR_SPECS.items() if s[0] == "fx6"}
    fx3_ok = fx3_keys.issubset(passed_keys)
    fx6_ok = fx6_keys.issubset(passed_keys)
    valid = fx3_ok and fx6_ok and within_budget and (not errors)

    return Phase228DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE
        if valid
        else STATUS_BLOCKED_PHASE228_DONOR_INTEGRITY,
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="O_RDONLY",
        files_inspected=files_inspected,
        elapsed_seconds=round(elapsed, 6),
        within_budget_150ms=within_budget,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        checked_markers=tuple(checked),
        missing_markers=tuple(missing),
        fx3_contracts_verified=fx3_ok,
        fx6_contracts_verified=fx6_ok,
        sha256_by_artifact=shas,
        bytes_by_artifact=sizes,
        errors=tuple(errors),
        warnings=(),
    )


# ---------------------------------------------------------------------------
# 2. Gate G83: Ver. 7.02 [Mode Settings] = [Fixed/Variable] S&Q 6-Lock Matrix
#    & [Zebra Display] / [Peaking Display] Local-LCD-Only HDMI Clean-Feed Guard
# ---------------------------------------------------------------------------


def resolve_fx3_mode_settings_and_sq_6locks(
    *,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_G83,
    video_system: str = VIDEO_SYSTEM_NTSC,
    shoot_mode: str = SHOOT_MODE_SQ,
    sq_mode_settings: str = MODE_SETTINGS_FIXED_VARIABLE,
    movie_file_format: str = FILE_FORMAT_XAVC_S_4K,
    rec_frame_rate: str = "23.98p",
    sq_capture_fps: int = 60,
    proxy_recording_on: bool = False,
) -> Dict[str, Any]:
    """Resolve `ILME-FX3` (`Ver. 7.02`) `[Mode Settings]` (`[Fixed/Variable]` vs
    `[Variable]`) and compute the 6 official S&Q hardware disqualifications.
    """
    fw_tuple = _parse_fw_tuple(firmware_version)
    canon_mode_settings = _norm_sq_mode_settings(sq_mode_settings)
    canon_shoot = _norm_shoot_mode(shoot_mode)
    canon_fmt = _norm_movie_file_format(movie_file_format)
    canon_rec = _norm_movie_rate(rec_frame_rate)
    canon_sys = _norm_video_system(video_system)

    fixed_var_active = canon_mode_settings == MODE_SETTINGS_FIXED_VARIABLE
    fw_supports_fixed_var = (
        fw_tuple is not None and fw_tuple >= FX3_SQ_FIXEDVAR_MIN_FW_TUPLE
    )

    rec_fps = _parse_fps_value(canon_rec) or 23.98
    cap_fps = int(sq_capture_fps) if not isinstance(sq_capture_fps, bool) else 0
    speed_ratio = round(rec_fps / float(cap_fps), 4) if cap_fps > 0 else 0.0

    is_sq = canon_shoot == SHOOT_MODE_SQ
    lock4_240_200_on_4k = (
        is_sq
        and cap_fps >= 200
        and canon_fmt in SQ_240_200FPS_BLOCKED_4K_FORMATS
    )
    lock5_120_100_on_dci4k = (
        is_sq
        and cap_fps >= 100
        and canon_fmt in SQ_120_100FPS_BLOCKED_DCI4K_FORMATS
    )
    lock6_proxy_hfr_blocked = (
        is_sq
        and bool(proxy_recording_on)
        and (
            canon_rec in SQ_PROXY_BLOCKED_REC_RATES
            or rec_fps >= 100.0
            or float(cap_fps) >= SQ_PROXY_BLOCKED_CAPTURE_FPS_FLOOR
        )
    )

    return {
        "firmware_supports_fixed_variable": fw_supports_fixed_var,
        "canonical_sq_mode_settings": canon_mode_settings,
        "expected_legacy_sq_settings_locked": fixed_var_active,
        "expected_direct_fps_control_active": fixed_var_active,
        "canonical_video_system": canon_sys,
        "canonical_shoot_mode": canon_shoot,
        "canonical_movie_file_format": canon_fmt,
        "canonical_rec_frame_rate": canon_rec,
        "sq_playback_speed_ratio": speed_ratio,
        "expected_sq_audio_channels": 0 if is_sq else 2,
        "expected_sound_recorded_in_sq": False,
        "expected_audio_out_timing_available": not is_sq,
        "expected_time_code_run_available": not is_sq,
        "expected_hdmi_time_code_output_available": not is_sq,
        "lock4_240_200fps_4k_blocked": lock4_240_200_on_4k,
        "lock5_120_100fps_dci4k_blocked": lock5_120_100_on_dci4k,
        "lock6_proxy_hfr_blocked": lock6_proxy_hfr_blocked,
    }


def resolve_fx3_zebra_peaking_hdmi_cleanfeed(
    *,
    zebra_display_mode: str = ZEBRA_DISPLAY_ON,
    peaking_display_mode: str = PEAKING_DISPLAY_ON,
    hdmi_info_display_on: bool = False,
) -> Dict[str, bool]:
    """Resolve local-LCD vs Type-A HDMI assist-overlay rendering on `ILME-FX3`.

    Official Sony hardware rule: neither `[Zebra Display]` stripes nor `[Peaking Display]`
    outlines are EVER output over HDMI (`hdmi_zebra_overlay_rendered == False`,
    `hdmi_peaking_overlay_rendered == False`), even when `[HDMI Info. Display] = [On]`.
    When `[HDMI Info. Display] = [On]`, the camera's built-in LCD panel is blanked.
    """
    z_on = _norm_on_off(zebra_display_mode) == "On"
    p_on = _norm_on_off(peaking_display_mode) == "On"
    lcd_blanked = bool(hdmi_info_display_on)
    return {
        "camera_lcd_blanked_by_hdmi_info": lcd_blanked,
        "expected_local_lcd_zebra_rendered": z_on and (not lcd_blanked),
        "expected_local_lcd_peaking_rendered": p_on and (not lcd_blanked),
        "expected_hdmi_zebra_overlay_rendered": False,
        "expected_hdmi_peaking_overlay_rendered": False,
    }


def verify_sq_fixedvar_6lock_and_zebra_peaking_hdmi_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: int = FX3_MODEL_ID,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_G83,
    video_system: str = VIDEO_SYSTEM_NTSC,
    shoot_mode: str = SHOOT_MODE_SQ,
    sq_mode_settings: str = MODE_SETTINGS_FIXED_VARIABLE,
    legacy_sq_settings_menu_locked: Optional[bool] = None,
    direct_fps_control_active: Optional[bool] = None,
    legacy_sq_settings_mutation_attempted: bool = False,
    movie_file_format: str = FILE_FORMAT_XAVC_S_4K,
    rec_frame_rate: str = "23.98p",
    sq_capture_fps: int = 60,
    sq_audio_channels_recorded: Optional[int] = None,
    sound_recorded_in_sq: Optional[bool] = None,
    audio_out_timing_mode: str = AUDIO_OUT_TIMING_LIVE,
    audio_out_timing_available: Optional[bool] = None,
    time_code_run_available: Optional[bool] = None,
    hdmi_time_code_output_available: Optional[bool] = None,
    proxy_recording_on: bool = False,
    zebra_display_mode: str = ZEBRA_DISPLAY_ON,
    peaking_display_mode: str = PEAKING_DISPLAY_ON,
    peaking_level: str = PEAKING_LEVEL_MID,
    peaking_color: str = PEAKING_COLOR_WHITE,
    wheel_right_default_function: str = CONTROL_WHEEL_RIGHT_DEFAULT_PEAKING_SELECT,
    hdmi_info_display_on: bool = False,
    local_lcd_zebra_rendered: Optional[bool] = None,
    local_lcd_peaking_rendered: Optional[bool] = None,
    hdmi_zebra_overlay_rendered: bool = False,
    hdmi_peaking_overlay_rendered: bool = False,
) -> SqFixedVar6LockAndZebraPeakingHdmiResult:
    """Verify Gate `G83`: `ILME-FX3` (`Ver. 7.02`) `[Mode Settings] = [Fixed/Variable]`
    legacy `[S&Q Settings]` lockout + all 6 official S&Q disqualifications +
    `[Zebra Display]` / `[Peaking Display]` local-LCD-only HDMI clean-feed isolation.
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if (
        body_model_name.strip().upper() != FX3_MODEL_NAME
        or int(body_model_id) != FX3_MODEL_ID
    ):
        _add_code(codes, STATUS_BLOCKED_G83_TELEMETRY_INVALID)
        errors.append(
            f"Body mismatch for G83: name={body_model_name!r}, id=0x{int(body_model_id):08X}."
        )

    fw_tuple = _parse_fw_tuple(firmware_version)
    if fw_tuple is None:
        _add_code(codes, STATUS_BLOCKED_G83_TELEMETRY_INVALID)
        errors.append(f"Malformed firmware_version={firmware_version!r} for Gate G83.")

    canon_sys = _norm_video_system(video_system)
    if canon_sys is None:
        _add_code(codes, STATUS_BLOCKED_G83_TELEMETRY_INVALID)
        errors.append(f"Unsupported video_system={video_system!r}; expected NTSC or PAL.")

    canon_shoot = _norm_shoot_mode(shoot_mode)
    if canon_shoot not in ALLOWED_SHOOT_MODES_G83:
        _add_code(codes, STATUS_BLOCKED_G83_TELEMETRY_INVALID)
        errors.append(f"Unsupported shoot_mode={shoot_mode!r} for Gate G83.")

    canon_mode_set = _norm_sq_mode_settings(sq_mode_settings)
    if canon_mode_set is None:
        _add_code(codes, STATUS_BLOCKED_G83_TELEMETRY_INVALID)
        errors.append(
            f"Unsupported [Mode Settings]={sq_mode_settings!r}; allowed={ALLOWED_SQ_MODE_SETTINGS}."
        )

    canon_fmt = _norm_movie_file_format(movie_file_format)
    if canon_fmt is None:
        _add_code(codes, STATUS_BLOCKED_G83_TELEMETRY_INVALID)
        errors.append(
            f"Unsupported [File Format]={movie_file_format!r}; allowed={ALLOWED_MOVIE_FILE_FORMATS_G83}."
        )

    canon_rec = _norm_movie_rate(rec_frame_rate)
    if canon_sys == VIDEO_SYSTEM_NTSC and canon_rec not in NTSC_SQ_ALLOWED_REC_RATES:
        _add_code(codes, STATUS_BLOCKED_G83_TELEMETRY_INVALID)
        errors.append(
            f"[Rec Frame Rate]={rec_frame_rate!r} incompatible with NTSC ({NTSC_SQ_ALLOWED_REC_RATES})."
        )
    elif canon_sys == VIDEO_SYSTEM_PAL and canon_rec not in PAL_SQ_ALLOWED_REC_RATES:
        _add_code(codes, STATUS_BLOCKED_G83_TELEMETRY_INVALID)
        errors.append(
            f"[Rec Frame Rate]={rec_frame_rate!r} incompatible with PAL ({PAL_SQ_ALLOWED_REC_RATES})."
        )

    max_sq_fps = (
        PAL_SQ_MAX_CAPTURE_FPS
        if canon_sys == VIDEO_SYSTEM_PAL
        else NTSC_SQ_MAX_CAPTURE_FPS
    )
    if (
        isinstance(sq_capture_fps, bool)
        or not isinstance(sq_capture_fps, int)
        or not (SQ_MIN_CAPTURE_FPS <= sq_capture_fps <= max_sq_fps)
    ):
        _add_code(codes, STATUS_BLOCKED_G83_TELEMETRY_INVALID)
        errors.append(
            f"S&Q capture [FPS]={sq_capture_fps!r} must be an integer in [{SQ_MIN_CAPTURE_FPS}, {max_sq_fps}] for {canon_sys or video_system}."
        )
        cap_fps_i = 60
    else:
        cap_fps_i = int(sq_capture_fps)

    canon_aot = _norm_audio_out_timing(audio_out_timing_mode)
    if canon_aot is None:
        _add_code(codes, STATUS_BLOCKED_G83_TELEMETRY_INVALID)
        errors.append(
            f"Unsupported [Audio Out Timing]={audio_out_timing_mode!r}; allowed={ALLOWED_AUDIO_OUT_TIMING_MODES}."
        )

    canon_zebra_disp = _norm_on_off(zebra_display_mode)
    canon_peaking_disp = _norm_on_off(peaking_display_mode)
    canon_peaking_lvl = _norm_peaking_level(peaking_level)
    canon_peaking_col = _norm_peaking_color(peaking_color)
    if (
        canon_zebra_disp is None
        or canon_peaking_disp is None
        or canon_peaking_lvl is None
        or canon_peaking_col is None
    ):
        _add_code(codes, STATUS_BLOCKED_G83_TELEMETRY_INVALID)
        errors.append(
            "Invalid Zebra/Peaking enum in Gate G83: "
            f"zebra={zebra_display_mode!r}, peaking={peaking_display_mode!r}, "
            f"level={peaking_level!r}, color={peaking_color!r}."
        )
    if (wheel_right_default_function or "").strip() != CONTROL_WHEEL_RIGHT_DEFAULT_PEAKING_SELECT:
        _add_code(codes, STATUS_BLOCKED_G83_TELEMETRY_INVALID)
        errors.append(
            f"Control Wheel Right default function {wheel_right_default_function!r} must match {CONTROL_WHEEL_RIGHT_DEFAULT_PEAKING_SELECT!r}."
        )

    # 1. Ver. 7.00+/7.02 [Mode Settings] = [Fixed/Variable] & legacy [S&Q Settings] lock
    sq_state = resolve_fx3_mode_settings_and_sq_6locks(
        firmware_version=firmware_version,
        video_system=canon_sys or VIDEO_SYSTEM_NTSC,
        shoot_mode=canon_shoot,
        sq_mode_settings=canon_mode_set or MODE_SETTINGS_FIXED_VARIABLE,
        movie_file_format=canon_fmt or FILE_FORMAT_XAVC_S_4K,
        rec_frame_rate=canon_rec,
        sq_capture_fps=cap_fps_i,
        proxy_recording_on=bool(proxy_recording_on),
    )

    fixed_var_active = canon_mode_set == MODE_SETTINGS_FIXED_VARIABLE
    eff_sq_locked = (
        fixed_var_active
        if legacy_sq_settings_menu_locked is None
        else bool(legacy_sq_settings_menu_locked)
    )
    eff_direct_fps = (
        fixed_var_active
        if direct_fps_control_active is None
        else bool(direct_fps_control_active)
    )

    if fixed_var_active and fw_tuple is not None and fw_tuple < FX3_SQ_FIXEDVAR_MIN_FW_TUPLE:
        _add_code(
            codes,
            STATUS_BLOCKED_G83_MODE_SETTINGS_FIXED_VARIABLE_OR_SQ_SETTINGS_LOCK_VIOLATION,
        )
        errors.append(
            f"[Mode Settings]=[Fixed/Variable] requires ILME-FX3 Ver. 7.00+, got {firmware_version!r}."
        )

    if fixed_var_active and (
        (not eff_sq_locked)
        or (not eff_direct_fps)
        or bool(legacy_sq_settings_mutation_attempted)
    ):
        _add_code(
            codes,
            STATUS_BLOCKED_G83_MODE_SETTINGS_FIXED_VARIABLE_OR_SQ_SETTINGS_LOCK_VIOLATION,
        )
        errors.append(
            "[Mode Settings]=[Fixed/Variable] locks legacy [S&Q Settings] in favor of direct [FPS] control: "
            f"sq_locked={eff_sq_locked}, direct_fps={eff_direct_fps}, "
            f"legacy_mutation={legacy_sq_settings_mutation_attempted}."
        )
    elif (not fixed_var_active) and (canon_mode_set == MODE_SETTINGS_VARIABLE) and eff_sq_locked:
        _add_code(
            codes,
            STATUS_BLOCKED_G83_MODE_SETTINGS_FIXED_VARIABLE_OR_SQ_SETTINGS_LOCK_VIOLATION,
        )
        errors.append(
            "Legacy [Mode Settings]=[Variable] cannot report [S&Q Settings] locked unless [Fixed/Variable] is active."
        )

    # 2. All 6 official S&Q disqualifications
    is_sq = canon_shoot == SHOOT_MODE_SQ
    eff_audio_ch = (
        (0 if is_sq else 2)
        if sq_audio_channels_recorded is None
        else int(sq_audio_channels_recorded)
    )
    eff_sound_in_sq = (
        False if sound_recorded_in_sq is None else bool(sound_recorded_in_sq)
    )
    eff_aot_avail = (
        (not is_sq)
        if audio_out_timing_available is None
        else bool(audio_out_timing_available)
    )
    eff_tc_run_avail = (
        (not is_sq)
        if time_code_run_available is None
        else bool(time_code_run_available)
    )
    eff_hdmi_tcout_avail = (
        (not is_sq)
        if hdmi_time_code_output_available is None
        else bool(hdmi_time_code_output_available)
    )

    lock1_ok = (not is_sq) or (eff_audio_ch == 0 and (not eff_sound_in_sq))
    lock2_ok = (eff_aot_avail is False) if is_sq else (eff_aot_avail is True)
    lock3_ok = (not is_sq) or ((not eff_tc_run_avail) and (not eff_hdmi_tcout_avail))
    lock4_ok = not bool(sq_state["lock4_240_200fps_4k_blocked"])
    lock5_ok = not bool(sq_state["lock5_120_100fps_dci4k_blocked"])
    lock6_ok = not bool(sq_state["lock6_proxy_hfr_blocked"])

    all_6_locks_ok = (
        lock1_ok and lock2_ok and lock3_ok and lock4_ok and lock5_ok and lock6_ok
    )
    if not all_6_locks_ok:
        _add_code(codes, STATUS_BLOCKED_G83_SQ_6LOCK_AUDIO_TC_CODEC_OR_PROXY_VIOLATION)
        if not lock1_ok:
            errors.append(
                f"S&Q Lock 1 violated: S&Q records 0ch audio (got channels={eff_audio_ch}, sound={eff_sound_in_sq})."
            )
        if not lock2_ok:
            errors.append(
                f"S&Q Lock 2 violated: [Audio Out Timing] availability={eff_aot_avail} invalid for shoot_mode={canon_shoot}."
            )
        if not lock3_ok:
            errors.append(
                f"S&Q Lock 3 violated: [Time Code Run] ({eff_tc_run_avail}) and [Time Code Output] ({eff_hdmi_tcout_avail}) are unavailable in S&Q."
            )
        if not lock4_ok:
            errors.append(
                f"S&Q Lock 4 violated: {cap_fps_i}fps is unavailable when [File Format]={canon_fmt!r} (4K formats block 240fps/200fps)."
            )
        if not lock5_ok:
            errors.append(
                f"S&Q Lock 5 violated: {cap_fps_i}fps is unavailable when [File Format]={canon_fmt!r} (4096x2160 DCI 4K blocks 120fps/100fps)."
            )
        if not lock6_ok:
            errors.append(
                f"S&Q Lock 6 violated: [Proxy Recording] is unavailable in S&Q at Rec={canon_rec} / FPS={cap_fps_i}fps."
            )

    # 3. Hardware HDMI Assist-Overlay Suppression (Zebra & Peaking Local-LCD-Only Clean-Feed)
    cleanfeed = resolve_fx3_zebra_peaking_hdmi_cleanfeed(
        zebra_display_mode=canon_zebra_disp or ZEBRA_DISPLAY_OFF,
        peaking_display_mode=canon_peaking_disp or PEAKING_DISPLAY_OFF,
        hdmi_info_display_on=bool(hdmi_info_display_on),
    )
    eff_lcd_zebra = (
        cleanfeed["expected_local_lcd_zebra_rendered"]
        if local_lcd_zebra_rendered is None
        else bool(local_lcd_zebra_rendered)
    )
    eff_lcd_peaking = (
        cleanfeed["expected_local_lcd_peaking_rendered"]
        if local_lcd_peaking_rendered is None
        else bool(local_lcd_peaking_rendered)
    )
    eff_hdmi_zebra = bool(hdmi_zebra_overlay_rendered)
    eff_hdmi_peaking = bool(hdmi_peaking_overlay_rendered)

    hdmi_clean_ok = (
        (not eff_hdmi_zebra)
        and (not eff_hdmi_peaking)
        and (eff_lcd_zebra == cleanfeed["expected_local_lcd_zebra_rendered"])
        and (eff_lcd_peaking == cleanfeed["expected_local_lcd_peaking_rendered"])
    )
    if not hdmi_clean_ok:
        _add_code(codes, STATUS_BLOCKED_G83_HDMI_ZEBRA_OR_PEAKING_ASSIST_OVERLAY_LEAK)
        errors.append(
            "ILME-FX3 Zebra/Peaking HDMI clean-feed isolation violated: "
            f"hdmi_zebra={eff_hdmi_zebra}, hdmi_peaking={eff_hdmi_peaking}, "
            f"lcd_zebra={eff_lcd_zebra} (expected {cleanfeed['expected_local_lcd_zebra_rendered']}), "
            f"lcd_peaking={eff_lcd_peaking} (expected {cleanfeed['expected_local_lcd_peaking_rendered']}), "
            f"hdmi_info_display_on={bool(hdmi_info_display_on)}."
        )

    valid = not codes
    status = STATUS_VERIFIED_G83 if valid else codes[0]
    return SqFixedVar6LockAndZebraPeakingHdmiResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=body_model_name,
        body_model_id_hex=f"0x{int(body_model_id):08X}",
        firmware_version=firmware_version,
        video_system=canon_sys or video_system,
        shoot_mode=canon_shoot,
        sq_mode_settings=canon_mode_set or sq_mode_settings,
        legacy_sq_settings_menu_locked=eff_sq_locked,
        direct_fps_control_active=eff_direct_fps,
        legacy_sq_settings_mutation_attempted=bool(
            legacy_sq_settings_mutation_attempted
        ),
        movie_file_format=canon_fmt or movie_file_format,
        rec_frame_rate=canon_rec,
        sq_capture_fps=cap_fps_i,
        sq_playback_speed_ratio=float(sq_state["sq_playback_speed_ratio"]),
        sq_audio_channels_recorded=eff_audio_ch,
        sound_recorded_in_sq=eff_sound_in_sq,
        audio_out_timing_mode=canon_aot or audio_out_timing_mode,
        audio_out_timing_available=eff_aot_avail,
        time_code_run_available=eff_tc_run_avail,
        hdmi_time_code_output_available=eff_hdmi_tcout_avail,
        proxy_recording_on=bool(proxy_recording_on),
        sq_6_locks_evaluated=SQ_6_DISQUALIFICATIONS,
        all_6_sq_locks_enforced=all_6_locks_ok,
        zebra_display_mode=canon_zebra_disp or zebra_display_mode,
        peaking_display_mode=canon_peaking_disp or peaking_display_mode,
        peaking_level=canon_peaking_lvl or peaking_level,
        peaking_color=canon_peaking_col or peaking_color,
        wheel_right_default_function=wheel_right_default_function,
        hdmi_info_display_on=bool(hdmi_info_display_on),
        camera_lcd_blanked_by_hdmi_info=cleanfeed["camera_lcd_blanked_by_hdmi_info"],
        local_lcd_zebra_rendered=eff_lcd_zebra,
        local_lcd_peaking_rendered=eff_lcd_peaking,
        hdmi_zebra_overlay_rendered=eff_hdmi_zebra,
        hdmi_peaking_overlay_rendered=eff_hdmi_peaking,
        hdmi_assist_clean_feed_enforced=hdmi_clean_ok,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g83_sq_fixedvar_zebra_peaking_hdmi_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    sq_fixedvar_zebra_peaking_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase228DonorAuditResult] = None,
) -> Tuple[GateVerdict, G83SqFixedVarZebraPeakingGuardResult]:
    """Evaluate Gate `G83` combining bounded `<0.15s` donor check with `[Mode Settings]`
    `[Fixed/Variable]` S&Q 6-lock matrix and `Zebra`/`Peaking` HDMI clean-feed guard.
    """
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase228_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_sq_fixedvar_6lock_and_zebra_peaking_hdmi_guard(
        **dict(sq_fixedvar_zebra_peaking_kwargs or {})
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
        errors.append("Gate G83 blocked persistent eMMC write authorization request.")

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G83 if valid else codes[0]

    res = G83SqFixedVarZebraPeakingGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        sq_fixedvar_zebra_peaking_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, sq_mode={guard.sq_mode_settings}"
        f"(sq_locked={guard.legacy_sq_settings_menu_locked},"
        f"fps={guard.sq_capture_fps}fps@{guard.movie_file_format},"
        f"6locks={guard.all_6_sq_locks_enforced}), "
        f"cleanfeed={guard.hdmi_assist_clean_feed_enforced}"
        f"(hdmi_zebra={guard.hdmi_zebra_overlay_rendered},"
        f"hdmi_peaking={guard.hdmi_peaking_overlay_rendered})"
    )
    verdict = GateVerdict(
        gate_id=G83_GATE_ID,
        gate_code=G83_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 3. Gate G84: [Zebra Display] Camera Settings Reset Survival & Slot-1 [Format]
#    (Quick / Full / MENU+Delete 2s Chord) Tier-0 Vault Lockout Guard
# ---------------------------------------------------------------------------


def resolve_fx3_zebra_reset_survival(
    *,
    pre_reset_zebra_display: str = ZEBRA_DISPLAY_ON,
    pre_reset_zebra_level: str = ZEBRA_LEVEL_CUSTOM_1,
    reset_action: str = RESET_ACTION_CAMERA_SETTINGS_RESET,
) -> Tuple[Optional[str], Optional[str], Optional[str], str, str]:
    """Resolve `ILME-FX3` (`Ver. 7.02`) `[Zebra Display]` and `[Zebra Level]`
    reset persistence asymmetry:
    - `[Camera Settings Reset]` preserves `[Zebra Display]` & `[Zebra Level]`.
    - `[Initialize]` resets `[Zebra Display] -> Off` & `[Zebra Level] -> 70`.
    """
    canon_disp = _norm_on_off(pre_reset_zebra_display)
    canon_lvl = _norm_zebra_level(pre_reset_zebra_level)
    canon_rst = _norm_reset_action(reset_action)

    if canon_rst == RESET_ACTION_INITIALIZE:
        exp_disp = ZEBRA_FACTORY_DEFAULT_DISPLAY
        exp_lvl = ZEBRA_FACTORY_DEFAULT_LEVEL
    else:
        exp_disp = canon_disp or pre_reset_zebra_display
        exp_lvl = canon_lvl or str(pre_reset_zebra_level)
    return canon_disp, canon_lvl, canon_rst, exp_disp, exp_lvl


def resolve_fx3_slot1_format_and_chord_vault_lock(
    *,
    slot1_tier0_vault_present: bool = True,
    slot1_tier0_vault_active: bool = True,
    off_camera_sha256_verified: bool = False,
    slot1_vault_card_removed_or_wp_locked: bool = False,
    target_slot: str = FORMAT_SLOT_NONE,
    format_trigger: str = FORMAT_TRIGGER_NONE,
    format_mode: str = FORMAT_MODE_NONE,
    menu_delete_chord_hold_seconds: float = 0.0,
) -> Dict[str, Any]:
    """Evaluate Slot-1 Tier-0 recovery vault hard-lock across Quick Format (`[Enter]`),
    `(Delete)`-toggled Full Format, and `MENU + (Delete)` (`~2s`) shooting-screen chord.
    """
    canon_slot = _norm_format_slot(target_slot)
    canon_trig = _norm_format_trigger(format_trigger)
    canon_mode = _norm_format_mode(format_mode)

    vault_protected = bool(slot1_tier0_vault_present) and (
        bool(slot1_tier0_vault_active)
        or (not bool(off_camera_sha256_verified))
        or (not bool(slot1_vault_card_removed_or_wp_locked))
    )
    chord_invoked = (
        canon_trig == FORMAT_TRIGGER_MENU_DELETE_2S_CHORD
        and float(menu_delete_chord_hold_seconds) >= MENU_DELETE_CHORD_MIN_HOLD_SECONDS
    )
    any_format_action = (
        canon_mode != FORMAT_MODE_NONE
        or canon_trig != FORMAT_TRIGGER_NONE
        or chord_invoked
    )
    slot1_targeted = canon_slot == FORMAT_SLOT_1
    blocked_by_vault = vault_protected and slot1_targeted and any_format_action

    return {
        "canonical_slot": canon_slot,
        "canonical_trigger": canon_trig,
        "canonical_mode": canon_mode,
        "slot1_format_hard_locked": vault_protected,
        "chord_dialog_invoked": chord_invoked,
        "any_format_action": any_format_action,
        "slot1_vault_violation": blocked_by_vault,
    }


def verify_zebra_reset_survival_and_fullformat_chord_vault_guard(
    *,
    wheel_left_default_function: str = CONTROL_WHEEL_LEFT_DEFAULT_ZEBRA_SELECT,
    pre_reset_zebra_display: str = ZEBRA_DISPLAY_ON,
    pre_reset_zebra_level: str = ZEBRA_LEVEL_CUSTOM_1,
    custom1_std_level: int = 70,
    custom1_exposure_range: int = 5,
    custom2_lower_limit_ire: int = 100,
    reset_action: str = RESET_ACTION_CAMERA_SETTINGS_RESET,
    post_reset_zebra_display: Optional[str] = None,
    post_reset_zebra_level: Optional[str] = None,
    slot1_tier0_vault_present: bool = True,
    slot1_tier0_vault_active: bool = True,
    slot1_vault_artifacts: Sequence[str] = TIER0_VAULT_REQUIRED_ARTIFACTS,
    off_camera_sha256_verified: bool = False,
    slot1_vault_card_removed_or_wp_locked: bool = False,
    slot1_format_hard_locked_enforced: Optional[bool] = None,
    target_slot: str = FORMAT_SLOT_NONE,
    format_trigger: str = FORMAT_TRIGGER_NONE,
    format_mode: str = FORMAT_MODE_NONE,
    menu_delete_chord_hold_seconds: float = 0.0,
    menu_delete_chord_dialog_invoked: Optional[bool] = None,
    full_format_canceled_midway: bool = False,
    mid_cancel_prior_data_erased: Optional[bool] = None,
    mid_cancel_card_usable: Optional[bool] = None,
) -> ZebraResetSurvivalAndFullFormatVaultResult:
    """Verify Gate `G84`: `[Zebra Display]` / `[Zebra Level]` (`70..100+`, `Custom 1`,
    `Custom 2`) survival across `[Camera Settings Reset]` vs `[Initialize]`, plus
    Slot-1 `[Format]` (Quick / `(Delete)` Full Format / `MENU + (Delete)` 2s chord)
    Tier-0 recovery vault hard-lock and Full Format mid-cancel semantics.
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if (
        wheel_left_default_function or ""
    ).strip() != CONTROL_WHEEL_LEFT_DEFAULT_ZEBRA_SELECT:
        _add_code(codes, STATUS_BLOCKED_G84_TELEMETRY_INVALID)
        errors.append(
            f"Control Wheel Left default {wheel_left_default_function!r} must match {CONTROL_WHEEL_LEFT_DEFAULT_ZEBRA_SELECT!r}."
        )

    canon_disp, canon_lvl, canon_rst, exp_post_disp, exp_post_lvl = (
        resolve_fx3_zebra_reset_survival(
            pre_reset_zebra_display=pre_reset_zebra_display,
            pre_reset_zebra_level=pre_reset_zebra_level,
            reset_action=reset_action,
        )
    )

    if canon_disp is None:
        _add_code(codes, STATUS_BLOCKED_G84_ZEBRA_LEVEL_OR_CUSTOM_THRESHOLD_INVALID)
        errors.append(
            f"Unsupported [Zebra Display]={pre_reset_zebra_display!r}; allowed={ALLOWED_ZEBRA_DISPLAY_MODES}."
        )

    if canon_lvl is None:
        _add_code(codes, STATUS_BLOCKED_G84_ZEBRA_LEVEL_OR_CUSTOM_THRESHOLD_INVALID)
        errors.append(
            f"Unsupported [Zebra Level]={pre_reset_zebra_level!r}; allowed={ALLOWED_ZEBRA_LEVELS}."
        )

    if canon_rst is None:
        _add_code(codes, STATUS_BLOCKED_G84_TELEMETRY_INVALID)
        errors.append(
            f"Unsupported reset_action={reset_action!r}; allowed={ALLOWED_RESET_ACTIONS_G84}."
        )

    if (
        isinstance(custom1_std_level, bool)
        or not isinstance(custom1_std_level, int)
        or not (ZEBRA_CUSTOM_IRE_MIN <= custom1_std_level <= ZEBRA_CUSTOM_IRE_MAX)
    ):
        _add_code(codes, STATUS_BLOCKED_G84_ZEBRA_LEVEL_OR_CUSTOM_THRESHOLD_INVALID)
        errors.append(
            f"Zebra Custom 1 [Standard]={custom1_std_level!r} must be an int in [{ZEBRA_CUSTOM_IRE_MIN}, {ZEBRA_CUSTOM_IRE_MAX}]."
        )
        c1_std = 70
    else:
        c1_std = int(custom1_std_level)

    if (
        isinstance(custom1_exposure_range, bool)
        or not isinstance(custom1_exposure_range, int)
        or not (ZEBRA_CUSTOM1_RANGE_MIN <= custom1_exposure_range <= ZEBRA_CUSTOM1_RANGE_MAX)
    ):
        _add_code(codes, STATUS_BLOCKED_G84_ZEBRA_LEVEL_OR_CUSTOM_THRESHOLD_INVALID)
        errors.append(
            f"Zebra Custom 1 [Exposure Range]={custom1_exposure_range!r} must be an int in [{ZEBRA_CUSTOM1_RANGE_MIN}, {ZEBRA_CUSTOM1_RANGE_MAX}]."
        )
        c1_rng = 5
    else:
        c1_rng = int(custom1_exposure_range)

    if (
        isinstance(custom2_lower_limit_ire, bool)
        or not isinstance(custom2_lower_limit_ire, int)
        or not (ZEBRA_CUSTOM_IRE_MIN <= custom2_lower_limit_ire <= ZEBRA_CUSTOM_IRE_MAX)
    ):
        _add_code(codes, STATUS_BLOCKED_G84_ZEBRA_LEVEL_OR_CUSTOM_THRESHOLD_INVALID)
        errors.append(
            f"Zebra Custom 2 [Minimum]={custom2_lower_limit_ire!r} must be an int in [{ZEBRA_CUSTOM_IRE_MIN}, {ZEBRA_CUSTOM_IRE_MAX}]."
        )
        c2_lim = 100
    else:
        c2_lim = int(custom2_lower_limit_ire)

    # 1. [Camera Settings Reset] survival vs [Initialize] factory wipe
    eff_post_disp = (
        exp_post_disp
        if post_reset_zebra_display is None
        else (_norm_on_off(post_reset_zebra_display) or post_reset_zebra_display)
    )
    eff_post_lvl = (
        exp_post_lvl
        if post_reset_zebra_level is None
        else (_norm_zebra_level(post_reset_zebra_level) or str(post_reset_zebra_level))
    )

    reset_persistence_ok = (eff_post_disp == exp_post_disp) and (
        eff_post_lvl == exp_post_lvl
    )
    if not reset_persistence_ok:
        _add_code(
            codes,
            STATUS_BLOCKED_G84_ZEBRA_CAMERA_SETTINGS_RESET_PERSISTENCE_VIOLATION,
        )
        errors.append(
            f"[Zebra Display]/[Zebra Level] post-reset mismatch under {canon_rst}: "
            f"got ({eff_post_disp!r}, {eff_post_lvl!r}), expected ({exp_post_disp!r}, {exp_post_lvl!r})."
        )

    # 2. Slot-1 [Format] (Quick / (Delete) Full / MENU+Delete 2s Chord) Tier-0 Vault Guard
    if not _is_finite_num(menu_delete_chord_hold_seconds) or float(
        menu_delete_chord_hold_seconds
    ) < 0.0:
        _add_code(codes, STATUS_BLOCKED_G84_TELEMETRY_INVALID)
        errors.append(
            f"menu_delete_chord_hold_seconds={menu_delete_chord_hold_seconds!r} must be a finite float >= 0.0."
        )
        hold_s = 0.0
    else:
        hold_s = float(menu_delete_chord_hold_seconds)

    vault_eval = resolve_fx3_slot1_format_and_chord_vault_lock(
        slot1_tier0_vault_present=bool(slot1_tier0_vault_present),
        slot1_tier0_vault_active=bool(slot1_tier0_vault_active),
        off_camera_sha256_verified=bool(off_camera_sha256_verified),
        slot1_vault_card_removed_or_wp_locked=bool(
            slot1_vault_card_removed_or_wp_locked
        ),
        target_slot=target_slot,
        format_trigger=format_trigger,
        format_mode=format_mode,
        menu_delete_chord_hold_seconds=hold_s,
    )
    canon_slot = vault_eval["canonical_slot"]
    canon_trig = vault_eval["canonical_trigger"]
    canon_mode = vault_eval["canonical_mode"]

    if canon_slot is None or canon_trig is None or canon_mode is None:
        _add_code(codes, STATUS_BLOCKED_G84_TELEMETRY_INVALID)
        errors.append(
            f"Invalid format telemetry: target_slot={target_slot!r}, "
            f"format_trigger={format_trigger!r}, format_mode={format_mode!r}."
        )

    if canon_trig == FORMAT_TRIGGER_MENU_ENTER and canon_mode == FORMAT_MODE_FULL:
        _add_code(codes, STATUS_BLOCKED_G84_TELEMETRY_INVALID)
        errors.append(
            "[Enter] alone executes Quick Format; Full Format requires pressing (Delete) on the confirmation dialog."
        )
    if (
        canon_trig == FORMAT_TRIGGER_CONFIRM_DELETE_TOGGLE
        and canon_mode not in (FORMAT_MODE_FULL,)
    ):
        _add_code(codes, STATUS_BLOCKED_G84_TELEMETRY_INVALID)
        errors.append(
            "(Delete) toggle on [Format] confirmation dialog selects Full Format."
        )
    if (
        canon_trig == FORMAT_TRIGGER_MENU_DELETE_2S_CHORD
        and hold_s < MENU_DELETE_CHORD_MIN_HOLD_SECONDS
    ):
        _add_code(codes, STATUS_BLOCKED_G84_TELEMETRY_INVALID)
        errors.append(
            f"Physical MENU + (Delete) format shortcut requires >={MENU_DELETE_CHORD_MIN_HOLD_SECONDS:.1f}s hold, got {hold_s:.2f}s."
        )

    eff_chord_dialog = (
        bool(vault_eval["chord_dialog_invoked"])
        if menu_delete_chord_dialog_invoked is None
        else bool(menu_delete_chord_dialog_invoked)
    )
    if eff_chord_dialog != bool(vault_eval["chord_dialog_invoked"]):
        _add_code(codes, STATUS_BLOCKED_G84_TELEMETRY_INVALID)
        errors.append(
            f"menu_delete_chord_dialog_invoked={eff_chord_dialog} contradicts trigger={canon_trig} & hold={hold_s:.2f}s."
        )

    hard_locked = bool(vault_eval["slot1_format_hard_locked"])
    eff_hard_lock_enforced = (
        hard_locked
        if slot1_format_hard_locked_enforced is None
        else bool(slot1_format_hard_locked_enforced)
    )

    if bool(vault_eval["slot1_vault_violation"]) or (
        hard_locked and not eff_hard_lock_enforced
    ):
        _add_code(codes, STATUS_BLOCKED_G84_SLOT1_TIER0_VAULT_FORMAT_OR_CHORD_LOCKOUT)
        errors.append(
            "Slot 1 [Format] (Quick Format, (Delete) Full Format, or MENU+Delete ~2s chord) "
            "is HARD-LOCKED while Slot 1 holds an active or unverified Tier-0 recovery vault "
            f"(artifacts={tuple(slot1_vault_artifacts)}, slot={canon_slot}, "
            f"trigger={canon_trig}, mode={canon_mode}, lock_enforced={eff_hard_lock_enforced})."
        )

    # 3. Full Format data-block wipe & mid-cancel semantics
    is_full = canon_mode == FORMAT_MODE_FULL
    canceled_mid = bool(full_format_canceled_midway)
    if canceled_mid and not is_full:
        _add_code(codes, STATUS_BLOCKED_G84_FULL_FORMAT_CANCEL_SEMANTICS_MISMATCH)
        errors.append(
            f"full_format_canceled_midway=True invalid when format_mode={canon_mode!r}."
        )

    eff_erased = (
        canceled_mid
        if mid_cancel_prior_data_erased is None
        else bool(mid_cancel_prior_data_erased)
    )
    eff_usable = (
        True if mid_cancel_card_usable is None else bool(mid_cancel_card_usable)
    )
    if canceled_mid and ((not eff_erased) or (not eff_usable)):
        _add_code(codes, STATUS_BLOCKED_G84_FULL_FORMAT_CANCEL_SEMANTICS_MISMATCH)
        errors.append(
            "Canceling ILME-FX3 Full Format mid-process leaves previously stored data ALREADY ERASED "
            f"while the card remains formatted and usable (got erased={eff_erased}, usable={eff_usable})."
        )

    band_min = max(ZEBRA_CUSTOM_IRE_MIN, c1_std - c1_rng)
    band_max = min(ZEBRA_CUSTOM_IRE_MAX, c1_std + c1_rng)
    survived_cam_reset = (
        (canon_rst != RESET_ACTION_INITIALIZE) and reset_persistence_ok
    )

    valid = not codes
    status = STATUS_VERIFIED_G84 if valid else codes[0]
    return ZebraResetSurvivalAndFullFormatVaultResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        wheel_left_default_function=wheel_left_default_function,
        pre_reset_zebra_display=canon_disp or pre_reset_zebra_display,
        pre_reset_zebra_level=canon_lvl or str(pre_reset_zebra_level),
        custom1_std_level=c1_std,
        custom1_exposure_range=c1_rng,
        custom1_band_min_ire=band_min,
        custom1_band_max_ire=band_max,
        custom2_lower_limit_ire=c2_lim,
        reset_action=canon_rst or reset_action,
        expected_post_reset_zebra_display=exp_post_disp,
        expected_post_reset_zebra_level=exp_post_lvl,
        effective_post_reset_zebra_display=eff_post_disp,
        effective_post_reset_zebra_level=eff_post_lvl,
        zebra_survived_camera_settings_reset=survived_cam_reset,
        slot1_tier0_vault_present=bool(slot1_tier0_vault_present),
        slot1_tier0_vault_active=bool(slot1_tier0_vault_active),
        slot1_vault_artifacts=tuple(slot1_vault_artifacts),
        off_camera_sha256_verified=bool(off_camera_sha256_verified),
        slot1_vault_card_removed_or_wp_locked=bool(
            slot1_vault_card_removed_or_wp_locked
        ),
        slot1_format_hard_locked=eff_hard_lock_enforced,
        target_slot=canon_slot or target_slot,
        format_trigger=canon_trig or format_trigger,
        format_mode=canon_mode or format_mode,
        menu_delete_chord_hold_seconds=round(hold_s, 3),
        menu_delete_chord_dialog_invoked=eff_chord_dialog,
        full_format_wipes_all_data_blocks=is_full,
        full_format_canceled_midway=canceled_mid,
        mid_cancel_prior_data_erased=eff_erased,
        mid_cancel_card_usable=eff_usable,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g84_zebra_reset_and_fullformat_chord_vault_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    zebra_reset_fullformat_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase228DonorAuditResult] = None,
) -> Tuple[GateVerdict, G84ZebraResetFullFormatVaultGuardResult]:
    """Evaluate Gate `G84` combining bounded `<0.15s` donor check with `[Zebra Display]`
    reset survival and Slot-1 `[Format]` / `MENU+Delete` 2s chord Tier-0 vault guard.
    """
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase228_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_zebra_reset_survival_and_fullformat_chord_vault_guard(
        **dict(zebra_reset_fullformat_kwargs or {})
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
        errors.append("Gate G84 blocked persistent eMMC write authorization request.")

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G84 if valid else codes[0]

    res = G84ZebraResetFullFormatVaultGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        zebra_reset_fullformat_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, zebra={guard.effective_post_reset_zebra_display}/"
        f"{guard.effective_post_reset_zebra_level}(rst={guard.reset_action}), "
        f"slot1_vault_lock={guard.slot1_format_hard_locked}"
        f"(slot={guard.target_slot},trig={guard.format_trigger},fmt={guard.format_mode})"
    )
    verdict = GateVerdict(
        gate_id=G84_GATE_ID,
        gate_code=G84_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 4. Unified 84-Gate Master Safety Preflight (`G01..G84`)
# ---------------------------------------------------------------------------


def evaluate_84gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    dry_run_simulated_backup: Optional[bool] = None,
    simulate_bench_dry_run: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    request_persistent_emmc_writes: bool = False,
    sq_fixedvar_zebra_peaking_kwargs: Optional[Mapping[str, Any]] = None,
    zebra_reset_fullformat_kwargs: Optional[Mapping[str, Any]] = None,
    master_82_override: Optional[Master82GateReport] = None,
    **m82_passthrough_kwargs: Any,
) -> Master84GateReport:
    """Evaluate all 84 Master Safety Gates (`G01..G84`) deterministically by
    delegating `G01..G82` directly to `evaluate_82gate_preflight()`.
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

    m82_report: Master82GateReport = (
        master_82_override
        if master_82_override is not None
        else evaluate_82gate_preflight(
            resolved_root,
            force_clean_room=clean_forced,
            dry_run_simulated=effective_dry_run,
            include_large_binaries=include_large_binaries,
            work_root=work_root,
            request_persistent_emmc_writes=request_persistent_emmc_writes,
            **m82_passthrough_kwargs,
        )
    )

    phase228_audit = audit_phase228_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
    )

    g83_verdict, g83_res = evaluate_g83_sq_fixedvar_zebra_peaking_hdmi_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        sq_fixedvar_zebra_peaking_kwargs=sq_fixedvar_zebra_peaking_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase228_audit,
    )

    g84_verdict, g84_res = evaluate_g84_zebra_reset_and_fullformat_chord_vault_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        zebra_reset_fullformat_kwargs=zebra_reset_fullformat_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase228_audit,
    )

    gates_83_to_84 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g83_verdict, g84_verdict)
    ]
    all_gates = tuple(list(m82_report.gates) + gates_83_to_84)

    g01_to_g12_verified = int(m82_report.summary["g01_to_g12_verified"])
    g13_to_g82_verified = (
        int(m82_report.summary["g13_to_g80_verified"])
        + int(m82_report.summary["g81_to_g82_verified"])
    )
    g83_to_g84_verified = sum(1 for v in (g83_verdict, g84_verdict) if v.passed)
    total_verified = g01_to_g12_verified + g13_to_g82_verified + g83_to_g84_verified

    g83_to_g84_all_passed = g83_to_g84_verified == 2
    g13_to_g84_all_passed = m82_report.g13_to_g82_all_passed and g83_to_g84_all_passed
    g01_to_g09_ok = all(bool(g["passed"]) for g in m82_report.gates[:9])

    offline_81_verified = (
        g01_to_g09_ok
        and m82_report.offline_79_gates_verified
        and g83_to_g84_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_84_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g84_all_passed
        and (not request_persistent_emmc_writes)
    )

    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m82_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_81_verified
        and m82_report.h0_h1_trial_entry_allowed
        and g83_to_g84_all_passed
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
        list(m82_report.errors) + list(g83_verdict.errors) + list(g84_verdict.errors)
    )
    warnings: List[str] = (
        list(m82_report.warnings)
        + list(g83_verdict.warnings)
        + list(g84_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m82_report.g13_to_g82_all_passed:
        overall_status = m82_report.status
    elif not g83_verdict.passed:
        overall_status = g83_verdict.status
    elif not g84_verdict.passed:
        overall_status = g84_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_84_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_84_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_84_verified:
        overall_status = "VERIFIED_ALL_84_GATES"
    else:
        overall_status = "VERIFIED_81_OF_84_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m82_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g83_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g84_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 84,
        "verified_gates": total_verified,
        "technical_gates_passed": total_verified,
        "blocked_or_pending_gates": 84 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g82_verified": g13_to_g82_verified,
        "g83_to_g84_verified": g83_to_g84_verified,
        "g13_to_g84_all_passed": g13_to_g84_all_passed,
        "g83_to_g84_all_passed": g83_to_g84_all_passed,
        "offline_81_gates_verified": offline_81_verified,
        "all_84_gates_verified": all_84_verified,
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

    return Master84GateReport(
        schema=REALHW_SQ_FIXEDVAR_ZEBRA_PEAKING_FULLFORMAT_84GATE_SCHEMA,
        version=REALHW_SQ_FIXEDVAR_ZEBRA_PEAKING_FULLFORMAT_84GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        offline_81_gates_verified=offline_81_verified,
        all_84_gates_verified=all_84_verified,
        g13_to_g84_all_passed=g13_to_g84_all_passed,
        g83_to_g84_all_passed=g83_to_g84_all_passed,
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
        master_82_report=m82_report.to_dict(),
        g83_result=g83_res.to_dict(),
        g84_result=g84_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_84_master_safety_gates = evaluate_84gate_preflight
run_84_gate_preflight = evaluate_84gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_sq_fixedvar_zebra_peaking_fullformat_and_84gate_guard",
        description=(
            "Phase 228 Safety Gates G83 (Mode Settings Fixed/Variable S&Q 6-Lock Matrix "
            "& Zebra/Peaking Local-LCD-Only HDMI Clean-Feed Guard) + G84 (Zebra Display "
            "Camera Settings Reset Survival & Full Format / MENU+Delete 2s Chord Vault "
            "Guard) + Unified 84-Gate Master Safety Preflight"
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

    report = evaluate_84gate_preflight(
        args.repo_root,
        force_clean_room=True if args.force_clean_room else None,
        dry_run_simulated=bool(args.dry_run_simulated),
    )
    if args.json:
        sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
    else:
        sys.stdout.write(
            f"status={report.status} mode={report.verification_mode} "
            f"verified={report.summary['verified_gates']}/84 "
            f"g83_to_g84_all_passed={report.g83_to_g84_all_passed} "
            f"all_84_gates_verified={report.all_84_gates_verified} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach}\n"
        )
    ok = report.all_84_gates_verified if args.dry_run_simulated else report.offline_81_gates_verified
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
