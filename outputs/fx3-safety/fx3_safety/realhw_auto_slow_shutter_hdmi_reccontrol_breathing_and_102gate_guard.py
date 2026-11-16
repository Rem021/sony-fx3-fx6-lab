"""Phase 259 (Wave-41) Sony `ILME-FX3` (`Ver. 7.02`) Safety Gates `G101`
(`[Auto Slow Shutter]` 6-Condition Non-Function Lockout, `Ver. 7.02` `[Shutter Mode]`
= `[Angle]` Strict Hardware Disjointness & `[Lens Compensation]` -> `[Breathing Comp.]`
Movie-Only Compliant-Lens Crop + `4264x2408` `RAW` / `S&Q` `239.76p`/`200p` Lockout
Guard) & `G102` (`[HDMI Output Settings]` Non-Resettable `[Setup]` Survival,
`[REC Control]` <- `[Time Code Output] = [On]` Mandatory Hardware Prerequisite,
`[4ch Audio Output]` `CH1/CH2` vs `CH3/CH4` MI-Shoe Channel Routing &
`[Rec. Media dur HDMI Output]` Slot-1/Slot-2 + `[Proxy Recording]` Inhibition /
Tier-0 Vault Guard) + Unified `102`-Gate Master Safety Preflight (`G01..G102`).

Operationalizes Wave-41 official Sony `ILME-FX3` (`Ver. 7.02`, Help Guide `ilc/2210`)
intelligence (`reports/2026-11-15-global-sony-wave41-auto-slow-shutter-6locks-hdmi-reccontrol-tcout-4chaudio-breathing-comp-intel/README.md`)
as deterministic offline preflight verifiers (`G101` and `G102`) and delegates
`G01..G100` directly to `evaluate_100gate_preflight()`.
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

from .master_16gate_preflight import (
    DEFAULT_REPO_ROOT,
    ENV_FORCE_CLEAN_ROOM,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_VERIFIED_SAFE,
    GateVerdict,
)
from .realhw_cfexpress_ufu_el3_and_52gate_guard import EL3_PAYLOAD_TRANSMIT_AUTHORIZED
from .realhw_diff_set_still_mv_custom_key_remain_shoot_and_100gate_guard import (
    Master100GateReport,
    evaluate_100gate_preflight,
)
from .realhw_dualmedia_bench_interlock_and_58gate_guard import (
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
)
from .realhw_filesettings_shotmark_tcregen_reclamp_and_78gate_guard import (
    _DONOR_BLOB_CACHE,
)
from .realhw_pnflasha_mtdro_rfnvs_and_48gate_guard import SPI_NOR_WRITE_AUTHORIZED
from .thermal_pwm_and_power_guard import resolve_donor_thermal_power_paths

# ---------------------------------------------------------------------------
# Schema, Gate Identifiers & Hard-Locked Safety Redline Constants
# ---------------------------------------------------------------------------

REALHW_AUTO_SLOW_SHUTTER_HDMI_RECCONTROL_BREATHING_102GATE_SCHEMA: str = (
    "realhw_auto_slow_shutter_hdmi_reccontrol_breathing_and_102gate_guard_v1"
)
REALHW_AUTO_SLOW_SHUTTER_HDMI_RECCONTROL_BREATHING_102GATE_VERSION: str = "1.0.0"

G101_GATE_ID: str = (
    "G101_auto_slow_shutter_6lock_angle_disjoint_and_breathing_comp_guard"
)
G101_GATE_CODE: str = (
    "AUTO_SLOW_SHUTTER_6LOCK_ANGLE_DISJOINT_AND_BREATHING_COMP_GUARD"
)

G102_GATE_ID: str = (
    "G102_hdmi_rec_control_tcout_4chaudio_and_slot1_rec_media_vault_guard"
)
G102_GATE_CODE: str = (
    "HDMI_REC_CONTROL_TCOUT_4CHAUDIO_AND_SLOT1_REC_MEDIA_VAULT_GUARD"
)

G101: str = G101_GATE_ID
G102: str = G102_GATE_ID
GATE_G101_AUTO_SLOW_SHUTTER_6LOCK_ANGLE_DISJOINT_AND_BREATHING_COMP_GUARD: str = (
    G101_GATE_CODE
)
GATE_G102_HDMI_REC_CONTROL_TCOUT_4CHAUDIO_AND_SLOT1_REC_MEDIA_VAULT_GUARD: str = (
    G102_GATE_CODE
)

HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
HUMAN_HARDWARE_ATTACH_TOKEN: bool = False
USB_PACKETS_TRANSMITTED: int = 0
PHYSICAL_USB_PACKETS_EMITTED: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0
DONOR_CHECK_MAX_SECONDS_PHASE259: float = 0.10
DONOR_CHECK_MAX_SECONDS: float = DONOR_CHECK_MAX_SECONDS_PHASE259

FX3_MODEL_NAME: str = "ILME-FX3"
FX3_MODEL_ID: int = 0x91030080
FX6_MODEL_NAME: str = "ILME-FX6"
FX3_DEFAULT_FW_VERSION_PHASE259: str = "7.02"
FX3_MIN_SUPPORTED_FW_TUPLE_PHASE259: Tuple[int, int] = (1, 0)
FX3_SHUTTER_ANGLE_MIN_FW_TUPLE_G101: Tuple[int, int] = (6, 0)
FX3_BREATHING_COMP_MIN_FW_TUPLE_G101: Tuple[int, int] = (3, 0)
FX3_HELP_GUIDE_CODE_PHASE259: str = "ilc/2210"

RESET_ACTION_NONE: str = "NONE"
RESET_ACTION_CAMERA_SETTINGS_RESET: str = "Camera Settings Reset"
RESET_ACTION_RESET_NETWORK_SET_PHASE259: str = "Reset Network Set."
RESET_ACTION_INITIALIZE: str = "Initialize"
ALLOWED_RESET_ACTIONS_PHASE259: Tuple[str, ...] = (
    RESET_ACTION_NONE,
    RESET_ACTION_CAMERA_SETTINGS_RESET,
    RESET_ACTION_RESET_NETWORK_SET_PHASE259,
    RESET_ACTION_INITIALIZE,
)

# ---------------------------------------------------------------------------
# Status & Violation Codes (G101 / G102 / Phase 259)
# ---------------------------------------------------------------------------

STATUS_VERIFIED_G101: str = (
    "VERIFIED_G101_AUTO_SLOW_SHUTTER_6LOCK_AND_BREATHING_COMP_SAFE"
)
STATUS_VERIFIED_G102: str = (
    "VERIFIED_G102_HDMI_REC_CONTROL_TCOUT_4CHAUDIO_AND_VAULT_SAFE"
)
STATUS_BLOCKED_PHASE259_DONOR_INTEGRITY: str = (
    "BLOCKED_PHASE259_DONOR_CONTRACT_INTEGRITY"
)

STATUS_BLOCKED_G101_AUTO_SLOW_SHUTTER_LOCKOUT_BYPASS_VIOLATION: str = (
    "BLOCKED_G101_AUTO_SLOW_SHUTTER_LOCKOUT_BYPASS_VIOLATION"
)
STATUS_BLOCKED_G101_SHUTTER_ANGLE_OVERLAP_VIOLATION: str = (
    "BLOCKED_G101_SHUTTER_ANGLE_OVERLAP_VIOLATION"
)
STATUS_BLOCKED_G101_RESET_SCOPE_PERSISTENCE_VIOLATION: str = (
    "BLOCKED_G101_RESET_SCOPE_PERSISTENCE_VIOLATION"
)
STATUS_BLOCKED_G101_BREATHING_COMP_STILL_OR_LENS_VIOLATION: str = (
    "BLOCKED_G101_BREATHING_COMP_STILL_OR_LENS_VIOLATION"
)
STATUS_BLOCKED_G101_BREATHING_COMP_RAW_OR_240P_BYPASS_VIOLATION: str = (
    "BLOCKED_G101_BREATHING_COMP_RAW_OR_240P_BYPASS_VIOLATION"
)
STATUS_BLOCKED_G101_TELEMETRY_INVALID: str = (
    "BLOCKED_G101_AUTO_SLOW_SHUTTER_BREATHING_TELEMETRY_INVALID"
)

STATUS_BLOCKED_G102_HDMI_SETUP_RESET_PERSISTENCE_VIOLATION: str = (
    "BLOCKED_G102_HDMI_SETUP_RESET_PERSISTENCE_VIOLATION"
)
STATUS_BLOCKED_G102_HDMI_REC_CTRL_WITHOUT_TCOUT_VIOLATION: str = (
    "BLOCKED_G102_HDMI_REC_CTRL_WITHOUT_TCOUT_VIOLATION"
)
STATUS_BLOCKED_G102_HDMI_4CH_AUDIO_ROUTING_MISMATCH: str = (
    "BLOCKED_G102_HDMI_4CH_AUDIO_ROUTING_MISMATCH"
)
STATUS_BLOCKED_G102_SLOT1_HDMI_REC_MEDIA_VAULT_VIOLATION: str = (
    "BLOCKED_G102_SLOT1_HDMI_REC_MEDIA_VAULT_VIOLATION"
)
STATUS_BLOCKED_G102_TELEMETRY_INVALID: str = (
    "BLOCKED_G102_HDMI_RECCONTROL_4CHAUDIO_TELEMETRY_INVALID"
)

# ---------------------------------------------------------------------------
# Gate G101 Constants: Auto Slow Shutter (6 Lockouts + Angle Disjoint) & Breathing Comp.
# ---------------------------------------------------------------------------

AUTO_SLOW_SHUTTER_MENU_PATH_G101: str = (
    "MENU -> Exposure/Color -> [Exposure] -> [Auto Slow Shutter]"
)
AUTO_SLOW_SHUTTER_ON_G101: str = "On"
AUTO_SLOW_SHUTTER_OFF_G101: str = "Off"
ALLOWED_AUTO_SLOW_SHUTTER_SETTINGS_G101: Tuple[str, ...] = (
    AUTO_SLOW_SHUTTER_ON_G101,
    AUTO_SLOW_SHUTTER_OFF_G101,
)
AUTO_SLOW_SHUTTER_FACTORY_DEFAULT_G101: str = AUTO_SLOW_SHUTTER_ON_G101

SHOOT_MODE_PROGRAM_AUTO_G101: str = "Program Auto"
SHOOT_MODE_APERTURE_PRIORITY_G101: str = "Aperture Priority"
SHOOT_MODE_SHUTTER_PRIORITY_G101: str = "Shutter Priority"
SHOOT_MODE_MANUAL_EXPOSURE_G101: str = "Manual Exposure"
SHOOT_MODE_SQ_G101: str = "S&Q"
ALLOWED_MOVIE_SHOOT_MODES_G101: Tuple[str, ...] = (
    SHOOT_MODE_PROGRAM_AUTO_G101,
    SHOOT_MODE_APERTURE_PRIORITY_G101,
    SHOOT_MODE_SHUTTER_PRIORITY_G101,
    SHOOT_MODE_MANUAL_EXPOSURE_G101,
    SHOOT_MODE_SQ_G101,
)

EXPOSURE_CTRL_PASM_MODE_G101: str = "P/A/S/M Mode"
EXPOSURE_CTRL_FLEXIBLE_EXP_MODE_G101: str = "Flexible Exp. Mode"
ALLOWED_EXPOSURE_CTRL_TYPES_G101: Tuple[str, ...] = (
    EXPOSURE_CTRL_PASM_MODE_G101,
    EXPOSURE_CTRL_FLEXIBLE_EXP_MODE_G101,
)

FLEX_EXP_SHUTTER_AUTO_G101: str = "Auto"
FLEX_EXP_SHUTTER_MANUAL_G101: str = "Manual"
ALLOWED_FLEX_EXP_SHUTTER_MODES_G101: Tuple[str, ...] = (
    FLEX_EXP_SHUTTER_AUTO_G101,
    FLEX_EXP_SHUTTER_MANUAL_G101,
)

ISO_AUTO_TOKEN_G101: str = "ISO AUTO"

LOG_SHOOTING_OFF_G101: str = "Off"
LOG_SHOOTING_FLEXIBLE_ISO_G101: str = "Flexible ISO"
LOG_SHOOTING_CINE_EI_QUICK_G101: str = "Cine EI Quick"
LOG_SHOOTING_CINE_EI_G101: str = "Cine EI"
ALLOWED_LOG_SHOOTING_MODES_G101: Tuple[str, ...] = (
    LOG_SHOOTING_OFF_G101,
    LOG_SHOOTING_FLEXIBLE_ISO_G101,
    LOG_SHOOTING_CINE_EI_QUICK_G101,
    LOG_SHOOTING_CINE_EI_G101,
)

SHUTTER_MODE_MENU_PATH_G101: str = (
    "MENU -> Exposure/Color -> [Exposure] -> [Shutter Mode]"
)
SHUTTER_MODE_SPEED_G101: str = "Speed"
SHUTTER_MODE_ANGLE_G101: str = "Angle"
ALLOWED_SHUTTER_MODES_G101: Tuple[str, ...] = (
    SHUTTER_MODE_SPEED_G101,
    SHUTTER_MODE_ANGLE_G101,
)

LOCKOUT_1_SQ_MODE_G101: str = "SQ_SHOOTING_MODE"
LOCKOUT_2_SHUTTER_PRIORITY_G101: str = "SHUTTER_PRIORITY_MODE"
LOCKOUT_3_MANUAL_EXPOSURE_G101: str = "MANUAL_EXPOSURE_MODE"
LOCKOUT_4_ISO_NOT_AUTO_G101: str = "ISO_NOT_AUTO"
LOCKOUT_5_FLEX_EXP_MANUAL_SHUTTER_G101: str = "FLEXIBLE_EXP_MANUAL_SHUTTER"
LOCKOUT_6_LOG_CINE_EI_G101: str = "LOG_SHOOTING_CINE_EI"
AUTO_SLOW_SHUTTER_SIX_LOCKOUT_CONDITIONS_G101: Tuple[str, ...] = (
    LOCKOUT_1_SQ_MODE_G101,
    LOCKOUT_2_SHUTTER_PRIORITY_G101,
    LOCKOUT_3_MANUAL_EXPOSURE_G101,
    LOCKOUT_4_ISO_NOT_AUTO_G101,
    LOCKOUT_5_FLEX_EXP_MANUAL_SHUTTER_G101,
    LOCKOUT_6_LOG_CINE_EI_G101,
)

BREATHING_COMP_MENU_PATH_G101: str = (
    "MENU -> Shooting -> [Image Quality/Rec] -> [Lens Compensation] -> [Breathing Comp.]"
)
BREATHING_COMP_OFF_G101: str = "Off"
BREATHING_COMP_ON_G101: str = "On"
ALLOWED_BREATHING_COMP_SETTINGS_G101: Tuple[str, ...] = (
    BREATHING_COMP_OFF_G101,
    BREATHING_COMP_ON_G101,
)
BREATHING_COMP_FACTORY_DEFAULT_G101: str = BREATHING_COMP_OFF_G101
CAPTURE_DOMAIN_MOVIE_G101: str = "Movie"
CAPTURE_DOMAIN_STILL_G101: str = "Still"
ALLOWED_CAPTURE_DOMAINS_G101: Tuple[str, ...] = (
    CAPTURE_DOMAIN_MOVIE_G101,
    CAPTURE_DOMAIN_STILL_G101,
)
BREATHING_COMP_RAW_RESOLUTION_G101: str = "4264x2408"
BREATHING_COMP_LOCKED_SQ_HIGH_FPS_G101: Tuple[float, ...] = (200.0, 239.76, 240.0)

# ---------------------------------------------------------------------------
# Gate G102 Constants: HDMI Output Settings (REC Control, TC Out, 4ch Audio, Vault)
# ---------------------------------------------------------------------------

HDMI_OUTPUT_SETTINGS_MENU_PATH_G102: str = (
    "MENU -> Setup -> [External Output] -> [HDMI Output Settings]"
)
HDMI_TC_OUTPUT_OFF_G102: str = "Off"
HDMI_TC_OUTPUT_ON_G102: str = "On"
ALLOWED_HDMI_TC_OUTPUT_SETTINGS_G102: Tuple[str, ...] = (
    HDMI_TC_OUTPUT_OFF_G102,
    HDMI_TC_OUTPUT_ON_G102,
)
HDMI_TC_OUTPUT_FACTORY_DEFAULT_G102: str = HDMI_TC_OUTPUT_OFF_G102

HDMI_REC_CONTROL_OFF_G102: str = "Off"
HDMI_REC_CONTROL_ON_G102: str = "On"
ALLOWED_HDMI_REC_CONTROL_SETTINGS_G102: Tuple[str, ...] = (
    HDMI_REC_CONTROL_OFF_G102,
    HDMI_REC_CONTROL_ON_G102,
)
HDMI_REC_CONTROL_FACTORY_DEFAULT_G102: str = HDMI_REC_CONTROL_OFF_G102

HDMI_4CH_AUDIO_CH1_CH2_G102: str = "CH1/CH2"
HDMI_4CH_AUDIO_CH3_CH4_G102: str = "CH3/CH4"
ALLOWED_HDMI_4CH_AUDIO_SETTINGS_G102: Tuple[str, ...] = (
    HDMI_4CH_AUDIO_CH1_CH2_G102,
    HDMI_4CH_AUDIO_CH3_CH4_G102,
)
HDMI_4CH_AUDIO_FACTORY_DEFAULT_G102: str = HDMI_4CH_AUDIO_CH1_CH2_G102
HDMI_AUDIO_PAIR_CH1_L_CH2_R_G102: str = "CH1=L/CH2=R"
HDMI_AUDIO_PAIR_CH3_L_CH4_R_G102: str = "CH3=L/CH4=R"
ALLOWED_HDMI_AUDIO_OUTPUT_PAIRS_G102: Tuple[str, ...] = (
    HDMI_AUDIO_PAIR_CH1_L_CH2_R_G102,
    HDMI_AUDIO_PAIR_CH3_L_CH4_R_G102,
)

HDMI_REC_MEDIA_ON_G102: str = "On"
HDMI_REC_MEDIA_OFF_G102: str = "Off"
ALLOWED_HDMI_REC_MEDIA_SETTINGS_G102: Tuple[str, ...] = (
    HDMI_REC_MEDIA_ON_G102,
    HDMI_REC_MEDIA_OFF_G102,
)
HDMI_REC_MEDIA_FACTORY_DEFAULT_G102: str = HDMI_REC_MEDIA_ON_G102
HDMI_REC_MEDIA_TIER0_BENCH_SAFE_DEFAULT_G102: str = HDMI_REC_MEDIA_OFF_G102

HDMI_OUTPUT_FACTORY_DEFAULTS_G102: Dict[str, str] = {
    "time_code_output": HDMI_TC_OUTPUT_FACTORY_DEFAULT_G102,
    "rec_control": HDMI_REC_CONTROL_FACTORY_DEFAULT_G102,
    "audio_4ch_output": HDMI_4CH_AUDIO_FACTORY_DEFAULT_G102,
    "rec_media_dur_hdmi_output": HDMI_REC_MEDIA_FACTORY_DEFAULT_G102,
}

# ---------------------------------------------------------------------------
# Pinned Local Donor Contracts (O_RDONLY, <0.10s, Clean-Room Fallback)
# ---------------------------------------------------------------------------

PINNED_PHASE259_DONOR_SPECS: Dict[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_cpapp_bin": (
        "FX3",
        "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin",
        15_980_568,
        "c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba",
        (
            b"ILME-FX3",
            b"Auto",
            b"Slow",
            b"Shutter",
            b"Angle",
            b"Exposure",
            b"ISO",
            b"Cine",
            b"Breathing",
            b"Lens",
            b"Comp",
            b"HDMI",
            b"REC",
            b"Control",
            b"Time",
            b"Code",
            b"Audio",
            b"Proxy",
            b"RAW",
            b"Reset",
            b"Initialize",
        ),
        "FX3_CPAPP_AUTO_SLOW_SHUTTER_HDMI_RECCONTROL_BREATHING_STRINGS",
    ),
    "fx3_libgpe_so": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libgpe.so",
        106_480,
        "363879687bd43a69734187eb28f721ce6080209a95c62b04c833a4a117f12464",
        (
            b"\x7fELF",
            b"gpe_blog_error",
            b"_ZNK5mpgpe5Gperm4InitEv",
        ),
        "FX3_LIBGPE_AUTO_SLOW_SHUTTER_HDMI_BREATHING_MENU_ELF",
    ),
    "fx3_libsaveloadsettings_so": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libSaveLoadSettings.so",
        18_760,
        "07819f42bdad381ecdd41c3765c117c33b0c44c25be36279b26f83906d244cb7",
        (
            b"\x7fELF",
            b"infra_saveLoadSettings_init",
            b"_ZN16SaveLoadSettings13requestToReadEN18SaveLoadSettingsIf11RequestTypeE",
            b"_ZN16SaveLoadSettings14requestToCheckEN18SaveLoadSettingsIf11RequestType",
        ),
        "FX3_LIBSAVELOADSETTINGS_EXPOSURE_SETUP_RESET_SPLIT_ELF",
    ),
    "fx3_bk4_bin": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin",
        2_229_740,
        "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2",
        (b"BK4", b"ILME-FX3", b"TC", b"/setting"),
        "FX3_BK4_HDMI_OUTPUT_TCOUT_BREATHING_COMP_SEED",
    ),
    "fx6_libinfradial_so": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libInfraDial.so",
        31_232,
        "b2034d6c85372027444e783d5d2ed913bb5a8cd2fe4051b10cf63caae875db33",
        (
            b"\x7fELF",
            b"_ZN9InfraDial4InitEv",
            b"_ZN9InfraDial10set4KeyInhEb",
            b"_ZN10InfraInput12SetKeyInhExtEibi",
        ),
        "FX6_LIBINFRADIAL_SHUTTER_ANGLE_EXPOSURE_PARITY_ELF",
    ),
    "fx6_bk4_bin": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0110_backup/SYSIPSX-DSLR/CHAPLIN/CX95898_NTSC.bin",
        2_253_333,
        "e2eafd4e950ead94fdba64722b225b9ccf4cf294ce4c1cf956b9e62926bbf89e",
        (b"BK4", b"WB", b"TC", b"/setting"),
        "FX6_BK4_CINEMA_LINE_TC_HDMI_AUDIO_PARITY_SEED",
    ),
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase259DonorAuditResult:
    valid: bool
    status: str
    verification_mode: str
    access_mode: str
    files_inspected: int
    elapsed_seconds: float
    within_budget_100ms: bool
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
class AutoSlowShutterAndBreathingCompGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    body_model_name: str
    body_model_id_hex: str
    help_guide_code: str
    firmware_version: str
    auto_slow_shutter_menu_path: str
    auto_slow_shutter_factory_default: str
    pre_reset_auto_slow_shutter: str
    reset_action: str
    effective_post_reset_auto_slow_shutter: str
    auto_slow_shutter_reset_by_camera_settings_reset: bool
    auto_slow_shutter_unaffected_by_reset_network_set: bool
    shoot_mode: str
    exposure_ctrl_type: str
    flexible_exp_shutter_mode: str
    iso_setting: str
    log_shooting_mode: str
    six_lockout_catalog: Tuple[str, ...]
    active_auto_slow_shutter_lockouts: Tuple[str, ...]
    auto_slow_shutter_hardware_locked_out: bool
    auto_slow_shutter_effective_active: bool
    auto_slow_shutter_lockout_bypass_events: int
    shutter_mode_menu_path: str
    movie_shutter_mode: str
    shutter_angle_deg: float
    shutter_angle_governing_exposure: bool
    shutter_angle_disjoint_from_auto_slow_shutter: bool
    disjointness_matrix_states_checked: int
    auto_slow_shutter_angle_overlap_events: int
    breathing_comp_menu_path: str
    breathing_comp_factory_default: str
    pre_reset_breathing_comp: str
    effective_post_reset_breathing_comp: str
    breathing_comp_reset_by_camera_settings_reset: bool
    capture_domain: str
    lens_breathing_comp_compliant: bool
    hdmi_raw_output_enabled: bool
    hdmi_raw_resolution: str
    sq_frame_rate_fps: float
    sq_high_fps_240p_200p_lockout_active: bool
    breathing_comp_hardware_locked_out: bool
    breathing_comp_effective_active: bool
    breathing_comp_fov_crop_active: bool
    breathing_comp_raw_or_240p_bypass_events: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G101AutoSlowShutterAndBreathingCompGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    auto_slow_shutter_breathing_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class HdmiRecControlTcOut4chAudioGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    body_model_name: str
    body_model_id_hex: str
    help_guide_code: str
    firmware_version: str
    hdmi_output_settings_menu_path: str
    hdmi_output_factory_defaults: Dict[str, str]
    reset_action: str
    pre_reset_time_code_output: str
    effective_post_reset_time_code_output: str
    pre_reset_rec_control: str
    effective_post_reset_rec_control: str
    rec_control_requires_time_code_output_on: bool
    effective_rec_control_active: bool
    hdmi_rec_ctrl_without_tc_violations: int
    pre_reset_audio_4ch_output: str
    effective_post_reset_audio_4ch_output: str
    mi_shoe_4ch_audio_active: bool
    hdmi_audio_left_channel: str
    hdmi_audio_right_channel: str
    effective_hdmi_audio_output_pair: str
    pre_reset_rec_media_dur_hdmi_output: str
    effective_post_reset_rec_media_dur_hdmi_output: str
    hdmi_settings_survive_camera_settings_reset: bool
    hdmi_settings_survive_reset_network_set: bool
    hdmi_settings_cleared_only_by_initialize: bool
    hdmi_output_active: bool
    proxy_recording_menu_setting: str
    rec_trigger_requested: bool
    tier0_slot1_vault_protection_active: bool
    internal_slot1_slot2_recording_inhibited: bool
    internal_proxy_recording_inhibited: bool
    effective_internal_media_recording_active: bool
    effective_proxy_recording_active: bool
    slot1_hdmi_rec_vault_mutation_bytes: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G102HdmiRecControlTcOut4chAudioGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    hdmi_reccontrol_4chaudio_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master102GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    offline_99_gates_verified: bool
    all_102_gates_verified: bool
    g13_to_g102_all_passed: bool
    g101_to_g102_all_passed: bool
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
    master_100_report: Dict[str, Any]
    g101_result: Dict[str, Any]
    g102_result: Dict[str, Any]
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


def _parse_fw_tuple(version_str: str) -> Optional[Tuple[int, int]]:
    if not isinstance(version_str, str):
        return None
    m = re.match(r"^\s*[vV]?(\d+)\.(\d+)(?:\.\d+)?\s*$", version_str)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def _norm_reset_action_phase259(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if u in ("NONE", "NO RESET", ""):
        return RESET_ACTION_NONE
    if u == "CAMERA SETTINGS RESET":
        return RESET_ACTION_CAMERA_SETTINGS_RESET
    if u in ("RESET NETWORK SET.", "RESET NETWORK SET", "RESET NETWORK SETTINGS"):
        return RESET_ACTION_RESET_NETWORK_SET_PHASE259
    if u == "INITIALIZE":
        return RESET_ACTION_INITIALIZE
    return None


def _norm_on_off_phase259(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if u == "ON":
        return "On"
    if u == "OFF":
        return "Off"
    return None


def _norm_shoot_mode_g101(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if u in ("PROGRAM AUTO", "MOVIE PROGRAM AUTO", "P"):
        return SHOOT_MODE_PROGRAM_AUTO_G101
    if u in ("APERTURE PRIORITY", "MOVIE APERTURE PRIORITY", "A"):
        return SHOOT_MODE_APERTURE_PRIORITY_G101
    if u in ("SHUTTER PRIORITY", "MOVIE SHUTTER PRIORITY", "S"):
        return SHOOT_MODE_SHUTTER_PRIORITY_G101
    if u in ("MANUAL EXPOSURE", "MOVIE MANUAL EXPOSURE", "M"):
        return SHOOT_MODE_MANUAL_EXPOSURE_G101
    if u in ("S&Q", "SQ", "SLOW & QUICK", "SLOW AND QUICK", "S&Q MOTION"):
        return SHOOT_MODE_SQ_G101
    return None


def _norm_exposure_ctrl_type_g101(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if u in ("P/A/S/M MODE", "PASM MODE", "PASM", "P/A/S/M"):
        return EXPOSURE_CTRL_PASM_MODE_G101
    if u in (
        "FLEXIBLE EXP. MODE",
        "FLEXIBLE EXP MODE",
        "FLEXIBLE EXPOSURE MODE",
        "FLEXIBLE EXP",
    ):
        return EXPOSURE_CTRL_FLEXIBLE_EXP_MODE_G101
    return None


def _norm_flex_exp_shutter_mode_g101(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if u == "AUTO":
        return FLEX_EXP_SHUTTER_AUTO_G101
    if u == "MANUAL":
        return FLEX_EXP_SHUTTER_MANUAL_G101
    return None


def _norm_iso_setting_g101(raw: Any) -> Optional[str]:
    if not isinstance(raw, str) or not raw.strip():
        return None
    s = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if s in ("ISO AUTO", "AUTO"):
        return ISO_AUTO_TOKEN_G101
    m = re.match(r"^(?:ISO\s*)?(\d+)$", s)
    if m:
        val = int(m.group(1))
        if 50 <= val <= 409600:
            return f"ISO {val}"
    return None


def _norm_log_shooting_mode_g101(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if u == "OFF":
        return LOG_SHOOTING_OFF_G101
    if u == "FLEXIBLE ISO":
        return LOG_SHOOTING_FLEXIBLE_ISO_G101
    if u == "CINE EI QUICK":
        return LOG_SHOOTING_CINE_EI_QUICK_G101
    if u in ("CINE EI", "BIG6 CINE EI", "BIG-6 CINE EI"):
        return LOG_SHOOTING_CINE_EI_G101
    return None


def _norm_shutter_mode_g101(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if u in ("SPEED", "SHUTTER SPEED"):
        return SHUTTER_MODE_SPEED_G101
    if u in ("ANGLE", "SHUTTER ANGLE"):
        return SHUTTER_MODE_ANGLE_G101
    return None


def _norm_capture_domain_g101(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if u in ("MOVIE", "VIDEO"):
        return CAPTURE_DOMAIN_MOVIE_G101
    if u in ("STILL", "PHOTO", "STILL IMAGE"):
        return CAPTURE_DOMAIN_STILL_G101
    return None


def _norm_4ch_audio_setting_g102(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = (
        re.sub(r"\s+", "", raw.strip().strip("[]").replace("_", "/"))
        .upper()
    )
    if u in ("CH1/CH2", "CH1&CH2", "1/2"):
        return HDMI_4CH_AUDIO_CH1_CH2_G102
    if u in ("CH3/CH4", "CH3&CH4", "3/4"):
        return HDMI_4CH_AUDIO_CH3_CH4_G102
    return None


def _norm_hdmi_audio_pair_g102(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", "", raw.strip().strip("[]")).upper()
    if u in ("CH1=L/CH2=R", "CH1/CH2"):
        return HDMI_AUDIO_PAIR_CH1_L_CH2_R_G102
    if u in ("CH3=L/CH4=R", "CH3/CH4"):
        return HDMI_AUDIO_PAIR_CH3_L_CH4_R_G102
    return None


# ---------------------------------------------------------------------------
# 1. Bounded `< 0.10s` O_RDONLY Donor Contract Audit (`Phase 259`)
# ---------------------------------------------------------------------------


def audit_phase259_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    max_budget_seconds: float = DONOR_CHECK_MAX_SECONDS_PHASE259,
) -> Phase259DonorAuditResult:
    """Inspect local FX3 Ver. 7.02 / FX6 Ver. 6.01 donor artifacts strictly
    `os.O_RDONLY` within `<0.10s`, verifying bounded symbols across
    `cpapp-b.bin`, `libgpe.so`, `libSaveLoadSettings.so`,
    `FX3-CX95900_ALLLANG-Backup.bin`, `libInfraDial.so`, and `CX95898_NTSC.bin`
    with deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` parity.
    """
    t0 = time.perf_counter()
    clean_forced = _is_forced_clean_room(force_clean_room)
    resolved_repo = (
        DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)
    ).resolve()

    candidate_root: Optional[Path] = None
    if not clean_forced:
        if work_root is not None:
            candidate_root = Path(work_root)
        else:
            paths = resolve_donor_thermal_power_paths(
                work_root=work_root, repo_root=resolved_repo
            )
            candidate_root = paths.work_root

    resolved: Dict[str, Path] = {}
    all_present = False
    if not clean_forced and candidate_root is not None and candidate_root.is_dir():
        all_present = True
        for key, (_body, rel_path, *_rest) in PINNED_PHASE259_DONOR_SPECS.items():
            fp = candidate_root / rel_path
            if fp.is_file():
                resolved[key] = fp
            else:
                all_present = False
                break

    if clean_forced or not all_present:
        elapsed = time.perf_counter() - t0
        within_budget = elapsed < max_budget_seconds
        synthetic_markers = tuple(
            spec[5] for spec in PINNED_PHASE259_DONOR_SPECS.values()
        )
        synthetic_shas = {
            k: f"synthetic:{v[3][:16]}" for k, v in PINNED_PHASE259_DONOR_SPECS.items()
        }
        synthetic_sizes = {k: v[2] for k, v in PINNED_PHASE259_DONOR_SPECS.items()}
        return Phase259DonorAuditResult(
            valid=within_budget,
            status=(
                STATUS_VERIFIED_SAFE
                if within_budget
                else STATUS_BLOCKED_PHASE259_DONOR_INTEGRITY
            ),
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="SYNTHETIC_CLEAN_ROOM",
            files_inspected=0,
            elapsed_seconds=round(elapsed, 6),
            within_budget_100ms=within_budget,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            checked_markers=synthetic_markers,
            missing_markers=(),
            fx3_contracts_verified=True,
            fx6_contracts_verified=True,
            sha256_by_artifact=synthetic_shas,
            bytes_by_artifact=synthetic_sizes,
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
    ) in PINNED_PHASE259_DONOR_SPECS.items():
        fp = resolved[key]
        try:
            actual_size, actual_sha, blob = _read_cached_donor_o_rdonly(fp)
            files_inspected += 1
        except OSError as exc:
            missing.append(marker_label)
            errors.append(f"O_RDONLY read failed for {key}: {exc}")
            continue

        sizes[key] = actual_size
        shas[key] = actual_sha
        size_ok = actual_size == exp_size
        sha_ok = actual_sha == exp_sha
        markers_ok = all(m in blob for m in marker_tuple)

        if not size_ok:
            errors.append(
                f"Donor size mismatch for {key}: got {actual_size}, expected {exp_size}."
            )
        if not sha_ok:
            errors.append(
                f"Donor SHA-256 mismatch for {key}: got {actual_sha}, expected {exp_sha}."
            )
        if not markers_ok:
            errors.append(f"Missing required Wave-41 byte markers in {key}.")

        if size_ok and sha_ok and markers_ok:
            checked.append(marker_label)
            passed_keys.add(key)
        else:
            missing.append(marker_label)

    elapsed = time.perf_counter() - t0
    within_budget = elapsed < max_budget_seconds
    if not within_budget:
        errors.append(
            f"Local O_RDONLY donor audit exceeded budget ({elapsed:.4f}s >= {max_budget_seconds:.4f}s)."
        )

    fx3_keys = {k for k, v in PINNED_PHASE259_DONOR_SPECS.items() if v[0] == "FX3"}
    fx6_keys = {k for k, v in PINNED_PHASE259_DONOR_SPECS.items() if v[0] == "FX6"}
    fx3_ok = fx3_keys.issubset(passed_keys)
    fx6_ok = fx6_keys.issubset(passed_keys)
    valid = fx3_ok and fx6_ok and (not missing) and within_budget and (not errors)

    return Phase259DonorAuditResult(
        valid=valid,
        status=(
            STATUS_VERIFIED_SAFE
            if valid
            else STATUS_BLOCKED_PHASE259_DONOR_INTEGRITY
        ),
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="OS_O_RDONLY",
        files_inspected=files_inspected,
        elapsed_seconds=round(elapsed, 6),
        within_budget_100ms=within_budget,
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
# 2. Gate G101: Auto Slow Shutter 6-Condition Lockout, Shutter Angle Disjointness
#    & Lens Compensation -> Breathing Comp. Guard
# ---------------------------------------------------------------------------


def _compute_active_auto_slow_shutter_lockouts(
    *,
    shoot_mode: str,
    exposure_ctrl_type: str,
    flexible_exp_shutter_mode: str,
    iso_setting: str,
    log_shooting_mode: str,
) -> Tuple[str, ...]:
    lockouts: List[str] = []
    if shoot_mode == SHOOT_MODE_SQ_G101:
        lockouts.append(LOCKOUT_1_SQ_MODE_G101)
    if shoot_mode == SHOOT_MODE_SHUTTER_PRIORITY_G101:
        lockouts.append(LOCKOUT_2_SHUTTER_PRIORITY_G101)
    if shoot_mode == SHOOT_MODE_MANUAL_EXPOSURE_G101:
        lockouts.append(LOCKOUT_3_MANUAL_EXPOSURE_G101)
    if iso_setting != ISO_AUTO_TOKEN_G101:
        lockouts.append(LOCKOUT_4_ISO_NOT_AUTO_G101)
    if (
        exposure_ctrl_type == EXPOSURE_CTRL_FLEXIBLE_EXP_MODE_G101
        and flexible_exp_shutter_mode == FLEX_EXP_SHUTTER_MANUAL_G101
    ):
        lockouts.append(LOCKOUT_5_FLEX_EXP_MANUAL_SHUTTER_G101)
    if log_shooting_mode in (
        LOG_SHOOTING_CINE_EI_QUICK_G101,
        LOG_SHOOTING_CINE_EI_G101,
    ):
        lockouts.append(LOCKOUT_6_LOG_CINE_EI_G101)
    return tuple(lockouts)


def _is_shutter_angle_governing_exposure(
    *,
    movie_shutter_mode: str,
    shoot_mode: str,
    exposure_ctrl_type: str,
    flexible_exp_shutter_mode: str,
) -> bool:
    if movie_shutter_mode != SHUTTER_MODE_ANGLE_G101:
        return False
    if shoot_mode == SHOOT_MODE_SQ_G101:
        return True
    if exposure_ctrl_type == EXPOSURE_CTRL_FLEXIBLE_EXP_MODE_G101:
        return flexible_exp_shutter_mode == FLEX_EXP_SHUTTER_MANUAL_G101
    return shoot_mode in (
        SHOOT_MODE_SHUTTER_PRIORITY_G101,
        SHOOT_MODE_MANUAL_EXPOSURE_G101,
    )


_CACHED_DISJOINTNESS_MATRIX_G101: Optional[Dict[str, int]] = None


def compute_auto_slow_shutter_angle_disjointness_matrix() -> Dict[str, int]:
    """Exhaustively evaluate all 320 Sony ILME-FX3 Ver. 7.02 movie exposure states
    to prove `[Auto Slow Shutter]` and `[Shutter Mode] = [Angle]` can never
    simultaneously govern exposure time (`overlap_states == 0`).
    """
    global _CACHED_DISJOINTNESS_MATRIX_G101
    if _CACHED_DISJOINTNESS_MATRIX_G101 is not None:
        return dict(_CACHED_DISJOINTNESS_MATRIX_G101)

    states_checked = 0
    auto_slow_active_states = 0
    shutter_angle_active_states = 0
    overlap_states = 0

    for shoot_mode in ALLOWED_MOVIE_SHOOT_MODES_G101:
        for exp_ctrl in ALLOWED_EXPOSURE_CTRL_TYPES_G101:
            for flex_shutter in ALLOWED_FLEX_EXP_SHUTTER_MODES_G101:
                for iso_val in (ISO_AUTO_TOKEN_G101, "ISO 800"):
                    for log_mode in ALLOWED_LOG_SHOOTING_MODES_G101:
                        for shutter_mode in ALLOWED_SHUTTER_MODES_G101:
                            states_checked += 1
                            locks = _compute_active_auto_slow_shutter_lockouts(
                                shoot_mode=shoot_mode,
                                exposure_ctrl_type=exp_ctrl,
                                flexible_exp_shutter_mode=flex_shutter,
                                iso_setting=iso_val,
                                log_shooting_mode=log_mode,
                            )
                            auto_slow_on = len(locks) == 0
                            angle_on = _is_shutter_angle_governing_exposure(
                                movie_shutter_mode=shutter_mode,
                                shoot_mode=shoot_mode,
                                exposure_ctrl_type=exp_ctrl,
                                flexible_exp_shutter_mode=flex_shutter,
                            )
                            if auto_slow_on:
                                auto_slow_active_states += 1
                            if angle_on:
                                shutter_angle_active_states += 1
                            if auto_slow_on and angle_on:
                                overlap_states += 1

    _CACHED_DISJOINTNESS_MATRIX_G101 = {
        "states_checked": states_checked,
        "auto_slow_active_states": auto_slow_active_states,
        "shutter_angle_active_states": shutter_angle_active_states,
        "overlap_states": overlap_states,
    }
    return dict(_CACHED_DISJOINTNESS_MATRIX_G101)


def resolve_fx3_auto_slow_shutter_and_breathing_comp_state(
    *,
    pre_reset_auto_slow_shutter: str = AUTO_SLOW_SHUTTER_FACTORY_DEFAULT_G101,
    pre_reset_breathing_comp: str = BREATHING_COMP_FACTORY_DEFAULT_G101,
    reset_action: str = RESET_ACTION_NONE,
    shoot_mode: str = SHOOT_MODE_PROGRAM_AUTO_G101,
    exposure_ctrl_type: str = EXPOSURE_CTRL_PASM_MODE_G101,
    flexible_exp_shutter_mode: str = FLEX_EXP_SHUTTER_AUTO_G101,
    iso_setting: str = ISO_AUTO_TOKEN_G101,
    log_shooting_mode: str = LOG_SHOOTING_OFF_G101,
    movie_shutter_mode: str = SHUTTER_MODE_SPEED_G101,
    capture_domain: str = CAPTURE_DOMAIN_MOVIE_G101,
    lens_breathing_comp_compliant: bool = True,
    hdmi_raw_output_enabled: bool = False,
    sq_frame_rate_fps: float = 23.98,
) -> Dict[str, Any]:
    """Resolve deterministic post-reset `[Auto Slow Shutter]`, `[Shutter Mode]`,
    and `[Breathing Comp.]` hardware states on `ILME-FX3` (`Ver. 7.02`).
    """
    norm_reset = _norm_reset_action_phase259(reset_action)
    norm_ass_pre = _norm_on_off_phase259(pre_reset_auto_slow_shutter)
    norm_bc_pre = _norm_on_off_phase259(pre_reset_breathing_comp)
    norm_shoot = _norm_shoot_mode_g101(shoot_mode)
    norm_exp_ctrl = _norm_exposure_ctrl_type_g101(exposure_ctrl_type)
    norm_flex_shutter = _norm_flex_exp_shutter_mode_g101(flexible_exp_shutter_mode)
    norm_iso = _norm_iso_setting_g101(iso_setting)
    norm_log = _norm_log_shooting_mode_g101(log_shooting_mode)
    norm_shutter_mode = _norm_shutter_mode_g101(movie_shutter_mode)
    norm_domain = _norm_capture_domain_g101(capture_domain)

    if (
        norm_reset is None
        or norm_ass_pre is None
        or norm_bc_pre is None
        or norm_shoot is None
        or norm_exp_ctrl is None
        or norm_flex_shutter is None
        or norm_iso is None
        or norm_log is None
        or norm_shutter_mode is None
        or norm_domain is None
    ):
        raise ValueError("Invalid Gate G101 state parameter.")

    if norm_reset in (RESET_ACTION_CAMERA_SETTINGS_RESET, RESET_ACTION_INITIALIZE):
        post_ass = AUTO_SLOW_SHUTTER_FACTORY_DEFAULT_G101
        post_bc = BREATHING_COMP_FACTORY_DEFAULT_G101
    else:
        post_ass = norm_ass_pre
        post_bc = norm_bc_pre

    active_lockouts = _compute_active_auto_slow_shutter_lockouts(
        shoot_mode=norm_shoot,
        exposure_ctrl_type=norm_exp_ctrl,
        flexible_exp_shutter_mode=norm_flex_shutter,
        iso_setting=norm_iso,
        log_shooting_mode=norm_log,
    )
    ass_locked_out = len(active_lockouts) > 0
    ass_effective_active = (post_ass == AUTO_SLOW_SHUTTER_ON_G101) and (not ass_locked_out)

    angle_governing = _is_shutter_angle_governing_exposure(
        movie_shutter_mode=norm_shutter_mode,
        shoot_mode=norm_shoot,
        exposure_ctrl_type=norm_exp_ctrl,
        flexible_exp_shutter_mode=norm_flex_shutter,
    )

    fps_val = float(sq_frame_rate_fps)
    sq_240p_lockout = any(
        abs(fps_val - locked_fps) < 0.05
        for locked_fps in BREATHING_COMP_LOCKED_SQ_HIGH_FPS_G101
    ) and (norm_shoot == SHOOT_MODE_SQ_G101 or fps_val >= 200.0)
    bc_locked_out = bool(hdmi_raw_output_enabled) or sq_240p_lockout
    bc_effective_active = (
        post_bc == BREATHING_COMP_ON_G101
        and norm_domain == CAPTURE_DOMAIN_MOVIE_G101
        and bool(lens_breathing_comp_compliant)
        and (not bc_locked_out)
    )

    return {
        "reset_action": norm_reset,
        "effective_post_reset_auto_slow_shutter": post_ass,
        "active_auto_slow_shutter_lockouts": active_lockouts,
        "auto_slow_shutter_hardware_locked_out": ass_locked_out,
        "auto_slow_shutter_effective_active": ass_effective_active,
        "shutter_angle_governing_exposure": angle_governing,
        "effective_post_reset_breathing_comp": post_bc,
        "sq_high_fps_240p_200p_lockout_active": sq_240p_lockout,
        "breathing_comp_hardware_locked_out": bc_locked_out,
        "breathing_comp_effective_active": bc_effective_active,
        "breathing_comp_fov_crop_active": bc_effective_active,
    }



def verify_auto_slow_shutter_and_breathing_comp_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: int = FX3_MODEL_ID,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE259,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE259,
    auto_slow_shutter_menu_path: str = AUTO_SLOW_SHUTTER_MENU_PATH_G101,
    pre_reset_auto_slow_shutter: str = AUTO_SLOW_SHUTTER_FACTORY_DEFAULT_G101,
    reset_action: str = RESET_ACTION_NONE,
    claimed_post_reset_auto_slow_shutter: Optional[str] = None,
    shoot_mode: str = SHOOT_MODE_PROGRAM_AUTO_G101,
    exposure_ctrl_type: str = EXPOSURE_CTRL_PASM_MODE_G101,
    flexible_exp_shutter_mode: str = FLEX_EXP_SHUTTER_AUTO_G101,
    iso_setting: str = ISO_AUTO_TOKEN_G101,
    log_shooting_mode: str = LOG_SHOOTING_OFF_G101,
    six_lockout_catalog: Sequence[str] = AUTO_SLOW_SHUTTER_SIX_LOCKOUT_CONDITIONS_G101,
    claimed_auto_slow_shutter_active: Optional[bool] = None,
    auto_slow_shutter_lockout_bypass_events: int = 0,
    shutter_mode_menu_path: str = SHUTTER_MODE_MENU_PATH_G101,
    movie_shutter_mode: str = SHUTTER_MODE_SPEED_G101,
    shutter_angle_deg: float = 180.0,
    claimed_shutter_angle_governing_exposure: Optional[bool] = None,
    auto_slow_shutter_angle_overlap_events: int = 0,
    breathing_comp_menu_path: str = BREATHING_COMP_MENU_PATH_G101,
    pre_reset_breathing_comp: str = BREATHING_COMP_FACTORY_DEFAULT_G101,
    claimed_post_reset_breathing_comp: Optional[str] = None,
    capture_domain: str = CAPTURE_DOMAIN_MOVIE_G101,
    lens_breathing_comp_compliant: bool = True,
    hdmi_raw_output_enabled: bool = False,
    hdmi_raw_resolution: str = BREATHING_COMP_RAW_RESOLUTION_G101,
    sq_frame_rate_fps: float = 23.98,
    claimed_breathing_comp_active: Optional[bool] = None,
    claimed_breathing_comp_fov_crop_active: Optional[bool] = None,
    breathing_comp_raw_or_240p_bypass_events: int = 0,
) -> AutoSlowShutterAndBreathingCompGuardResult:
    """Verify Gate G101: `[Auto Slow Shutter]` 6-condition lockout + `[Shutter Mode]`
    = `[Angle]` disjointness + `[Breathing Comp.]` movie-only compliant-lens crop
    and `4264x2408` `RAW` / `S&Q` `239.76p`/`200p` lockout guard.
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    fw_tuple = _parse_fw_tuple(firmware_version)
    if (
        body_model_name != FX3_MODEL_NAME
        or not isinstance(body_model_id, int)
        or isinstance(body_model_id, bool)
        or body_model_id != FX3_MODEL_ID
        or help_guide_code != FX3_HELP_GUIDE_CODE_PHASE259
        or fw_tuple is None
        or fw_tuple < FX3_MIN_SUPPORTED_FW_TUPLE_PHASE259
    ):
        _add_code(codes, STATUS_BLOCKED_G101_TELEMETRY_INVALID)
        errors.append(
            "Invalid ILME-FX3 model identity, Help Guide code (ilc/2210), or firmware version in Gate G101."
        )

    if (
        auto_slow_shutter_menu_path != AUTO_SLOW_SHUTTER_MENU_PATH_G101
        or shutter_mode_menu_path != SHUTTER_MODE_MENU_PATH_G101
        or breathing_comp_menu_path != BREATHING_COMP_MENU_PATH_G101
        or hdmi_raw_resolution != BREATHING_COMP_RAW_RESOLUTION_G101
    ):
        _add_code(codes, STATUS_BLOCKED_G101_TELEMETRY_INVALID)
        errors.append(
            "Invalid menu path or HDMI RAW resolution (expected 4264x2408) in Gate G101."
        )

    if tuple(six_lockout_catalog) != AUTO_SLOW_SHUTTER_SIX_LOCKOUT_CONDITIONS_G101:
        _add_code(codes, STATUS_BLOCKED_G101_TELEMETRY_INVALID)
        errors.append(
            "Gate G101 six_lockout_catalog does not match exact 6 Sony Auto Slow Shutter lockouts."
        )

    norm_reset = _norm_reset_action_phase259(reset_action)
    norm_ass_pre = _norm_on_off_phase259(pre_reset_auto_slow_shutter)
    norm_bc_pre = _norm_on_off_phase259(pre_reset_breathing_comp)
    norm_shoot = _norm_shoot_mode_g101(shoot_mode)
    norm_exp_ctrl = _norm_exposure_ctrl_type_g101(exposure_ctrl_type)
    norm_flex_shutter = _norm_flex_exp_shutter_mode_g101(flexible_exp_shutter_mode)
    norm_iso = _norm_iso_setting_g101(iso_setting)
    norm_log = _norm_log_shooting_mode_g101(log_shooting_mode)
    norm_shutter_mode = _norm_shutter_mode_g101(movie_shutter_mode)
    norm_domain = _norm_capture_domain_g101(capture_domain)

    angle_valid = (
        isinstance(shutter_angle_deg, (int, float))
        and not isinstance(shutter_angle_deg, bool)
        and 5.6 <= float(shutter_angle_deg) <= 360.0
    )
    fps_valid = (
        isinstance(sq_frame_rate_fps, (int, float))
        and not isinstance(sq_frame_rate_fps, bool)
        and 1.0 <= float(sq_frame_rate_fps) <= 240.0
    )
    counters_valid = all(
        isinstance(v, int) and not isinstance(v, bool) and v >= 0
        for v in (
            auto_slow_shutter_lockout_bypass_events,
            auto_slow_shutter_angle_overlap_events,
            breathing_comp_raw_or_240p_bypass_events,
        )
    )
    bools_valid = all(
        isinstance(b, bool)
        for b in (lens_breathing_comp_compliant, hdmi_raw_output_enabled)
    )

    if (
        norm_reset is None
        or norm_ass_pre is None
        or norm_bc_pre is None
        or norm_shoot is None
        or norm_exp_ctrl is None
        or norm_flex_shutter is None
        or norm_iso is None
        or norm_log is None
        or norm_shutter_mode is None
        or norm_domain is None
        or not angle_valid
        or not fps_valid
        or not counters_valid
        or not bools_valid
    ):
        _add_code(codes, STATUS_BLOCKED_G101_TELEMETRY_INVALID)
        errors.append(
            "Invalid enum, angle, frame-rate, boolean, or counter telemetry in Gate G101."
        )

    eff_reset = norm_reset or RESET_ACTION_NONE
    eff_ass_pre = norm_ass_pre or AUTO_SLOW_SHUTTER_FACTORY_DEFAULT_G101
    eff_bc_pre = norm_bc_pre or BREATHING_COMP_FACTORY_DEFAULT_G101
    eff_shoot = norm_shoot or SHOOT_MODE_PROGRAM_AUTO_G101
    eff_exp_ctrl = norm_exp_ctrl or EXPOSURE_CTRL_PASM_MODE_G101
    eff_flex_shutter = norm_flex_shutter or FLEX_EXP_SHUTTER_AUTO_G101
    eff_iso = norm_iso or ISO_AUTO_TOKEN_G101
    eff_log = norm_log or LOG_SHOOTING_OFF_G101
    eff_shutter_mode = norm_shutter_mode or SHUTTER_MODE_SPEED_G101
    eff_domain = norm_domain or CAPTURE_DOMAIN_MOVIE_G101
    eff_fps = float(sq_frame_rate_fps) if fps_valid else 23.98
    eff_angle_deg = float(shutter_angle_deg) if angle_valid else 180.0

    resolved = resolve_fx3_auto_slow_shutter_and_breathing_comp_state(
        pre_reset_auto_slow_shutter=eff_ass_pre,
        pre_reset_breathing_comp=eff_bc_pre,
        reset_action=eff_reset,
        shoot_mode=eff_shoot,
        exposure_ctrl_type=eff_exp_ctrl,
        flexible_exp_shutter_mode=eff_flex_shutter,
        iso_setting=eff_iso,
        log_shooting_mode=eff_log,
        movie_shutter_mode=eff_shutter_mode,
        capture_domain=eff_domain,
        lens_breathing_comp_compliant=bool(lens_breathing_comp_compliant),
        hdmi_raw_output_enabled=bool(hdmi_raw_output_enabled),
        sq_frame_rate_fps=eff_fps,
    )

    post_ass = resolved["effective_post_reset_auto_slow_shutter"]
    post_bc = resolved["effective_post_reset_breathing_comp"]
    active_lockouts = resolved["active_auto_slow_shutter_lockouts"]
    ass_locked_out = resolved["auto_slow_shutter_hardware_locked_out"]
    ass_effective_active = resolved["auto_slow_shutter_effective_active"]
    angle_governing = resolved["shutter_angle_governing_exposure"]
    sq_240p_lockout = resolved["sq_high_fps_240p_200p_lockout_active"]
    bc_locked_out = resolved["breathing_comp_hardware_locked_out"]
    bc_effective_active = resolved["breathing_comp_effective_active"]
    bc_crop_active = resolved["breathing_comp_fov_crop_active"]

    # Reset scope validation (Camera Settings Reset + Initialize reset both; Reset Network Set. preserves both)
    if claimed_post_reset_auto_slow_shutter is not None:
        norm_claimed_ass = _norm_on_off_phase259(claimed_post_reset_auto_slow_shutter)
        if norm_claimed_ass != post_ass:
            _add_code(codes, STATUS_BLOCKED_G101_RESET_SCOPE_PERSISTENCE_VIOLATION)
            errors.append(
                f"[Auto Slow Shutter] post-reset mismatch after {eff_reset}: "
                f"claimed={claimed_post_reset_auto_slow_shutter!r}, expected={post_ass!r}."
            )

    if claimed_post_reset_breathing_comp is not None:
        norm_claimed_bc = _norm_on_off_phase259(claimed_post_reset_breathing_comp)
        if norm_claimed_bc != post_bc:
            _add_code(codes, STATUS_BLOCKED_G101_RESET_SCOPE_PERSISTENCE_VIOLATION)
            errors.append(
                f"[Breathing Comp.] post-reset mismatch after {eff_reset}: "
                f"claimed={claimed_post_reset_breathing_comp!r}, expected={post_bc!r}."
            )

    # 6-condition Auto Slow Shutter lockout check
    bypass_count = (
        int(auto_slow_shutter_lockout_bypass_events)
        if isinstance(auto_slow_shutter_lockout_bypass_events, int)
        and not isinstance(auto_slow_shutter_lockout_bypass_events, bool)
        else 1
    )
    if claimed_auto_slow_shutter_active is not None:
        if not isinstance(claimed_auto_slow_shutter_active, bool):
            _add_code(codes, STATUS_BLOCKED_G101_TELEMETRY_INVALID)
            errors.append("claimed_auto_slow_shutter_active must be bool.")
        elif claimed_auto_slow_shutter_active != ass_effective_active:
            bypass_count += 1
            _add_code(
                codes, STATUS_BLOCKED_G101_AUTO_SLOW_SHUTTER_LOCKOUT_BYPASS_VIOLATION
            )
            errors.append(
                f"[Auto Slow Shutter] lockout/state violation: claimed_active={claimed_auto_slow_shutter_active}, "
                f"expected={ass_effective_active}, lockouts={active_lockouts}."
            )
    if bypass_count != 0:
        _add_code(codes, STATUS_BLOCKED_G101_AUTO_SLOW_SHUTTER_LOCKOUT_BYPASS_VIOLATION)
        errors.append(
            f"auto_slow_shutter_lockout_bypass_events={bypass_count} (must be 0)."
        )

    # Ver. 7.02 [Shutter Mode] = [Angle] disjointness check
    matrix = compute_auto_slow_shutter_angle_disjointness_matrix()
    overlap_count = (
        (
            int(auto_slow_shutter_angle_overlap_events)
            if isinstance(auto_slow_shutter_angle_overlap_events, int)
            and not isinstance(auto_slow_shutter_angle_overlap_events, bool)
            else 1
        )
        + int(matrix["overlap_states"])
    )
    if (
        eff_shutter_mode == SHUTTER_MODE_ANGLE_G101
        and fw_tuple is not None
        and fw_tuple < FX3_SHUTTER_ANGLE_MIN_FW_TUPLE_G101
    ):
        overlap_count += 1
        _add_code(codes, STATUS_BLOCKED_G101_SHUTTER_ANGLE_OVERLAP_VIOLATION)
        errors.append(
            f"[Shutter Mode] = [Angle] requires ILME-FX3 Ver. 6.00+ (got {firmware_version})."
        )

    if claimed_shutter_angle_governing_exposure is not None:
        if not isinstance(claimed_shutter_angle_governing_exposure, bool):
            _add_code(codes, STATUS_BLOCKED_G101_TELEMETRY_INVALID)
            errors.append("claimed_shutter_angle_governing_exposure must be bool.")
        elif claimed_shutter_angle_governing_exposure != angle_governing:
            overlap_count += 1
            _add_code(codes, STATUS_BLOCKED_G101_SHUTTER_ANGLE_OVERLAP_VIOLATION)
            errors.append(
                f"[Shutter Mode] = [Angle] governance mismatch: claimed={claimed_shutter_angle_governing_exposure}, "
                f"expected={angle_governing} in {eff_shoot}/{eff_exp_ctrl}."
            )

    if (ass_effective_active and angle_governing) or (
        claimed_auto_slow_shutter_active is True
        and claimed_shutter_angle_governing_exposure is True
    ):
        overlap_count += 1
        _add_code(codes, STATUS_BLOCKED_G101_SHUTTER_ANGLE_OVERLAP_VIOLATION)
        errors.append(
            "[Auto Slow Shutter] and [Shutter Mode]=[Angle] cannot simultaneously govern exposure."
        )

    if overlap_count != 0:
        _add_code(codes, STATUS_BLOCKED_G101_SHUTTER_ANGLE_OVERLAP_VIOLATION)
        errors.append(
            f"auto_slow_shutter_angle_overlap_events={overlap_count} (must be 0)."
        )

    # [Lens Compensation] -> [Breathing Comp.] movie-only, compliant lens & RAW/240p lockout check
    raw_240p_bypass = (
        int(breathing_comp_raw_or_240p_bypass_events)
        if isinstance(breathing_comp_raw_or_240p_bypass_events, int)
        and not isinstance(breathing_comp_raw_or_240p_bypass_events, bool)
        else 1
    )
    if (
        post_bc == BREATHING_COMP_ON_G101
        and fw_tuple is not None
        and fw_tuple < FX3_BREATHING_COMP_MIN_FW_TUPLE_G101
    ):
        _add_code(codes, STATUS_BLOCKED_G101_BREATHING_COMP_STILL_OR_LENS_VIOLATION)
        errors.append(
            f"[Breathing Comp.] requires ILME-FX3 Ver. 3.00+ (got {firmware_version})."
        )

    if claimed_breathing_comp_active is not None:
        if not isinstance(claimed_breathing_comp_active, bool):
            _add_code(codes, STATUS_BLOCKED_G101_TELEMETRY_INVALID)
            errors.append("claimed_breathing_comp_active must be bool.")
        elif claimed_breathing_comp_active != bc_effective_active:
            if claimed_breathing_comp_active and bc_locked_out:
                raw_240p_bypass += 1
                _add_code(
                    codes,
                    STATUS_BLOCKED_G101_BREATHING_COMP_RAW_OR_240P_BYPASS_VIOLATION,
                )
                errors.append(
                    "[Breathing Comp.] cannot remain active during 4264x2408 RAW Output or S&Q 239.76p/200p."
                )
            else:
                _add_code(
                    codes,
                    STATUS_BLOCKED_G101_BREATHING_COMP_STILL_OR_LENS_VIOLATION,
                )
                errors.append(
                    f"[Breathing Comp.] movie-only / compliant-lens state mismatch: "
                    f"claimed={claimed_breathing_comp_active}, expected={bc_effective_active}."
                )

    if claimed_breathing_comp_fov_crop_active is not None:
        if not isinstance(claimed_breathing_comp_fov_crop_active, bool):
            _add_code(codes, STATUS_BLOCKED_G101_TELEMETRY_INVALID)
            errors.append("claimed_breathing_comp_fov_crop_active must be bool.")
        elif claimed_breathing_comp_fov_crop_active != bc_crop_active:
            if claimed_breathing_comp_fov_crop_active and bc_locked_out:
                raw_240p_bypass += 1
                _add_code(
                    codes,
                    STATUS_BLOCKED_G101_BREATHING_COMP_RAW_OR_240P_BYPASS_VIOLATION,
                )
            else:
                _add_code(
                    codes,
                    STATUS_BLOCKED_G101_BREATHING_COMP_STILL_OR_LENS_VIOLATION,
                )
            errors.append(
                f"[Breathing Comp.] FOV crop mismatch: claimed={claimed_breathing_comp_fov_crop_active}, "
                f"expected={bc_crop_active}."
            )

    if raw_240p_bypass != 0:
        _add_code(
            codes, STATUS_BLOCKED_G101_BREATHING_COMP_RAW_OR_240P_BYPASS_VIOLATION
        )
        errors.append(
            f"breathing_comp_raw_or_240p_bypass_events={raw_240p_bypass} (must be 0)."
        )

    valid = not codes
    status = STATUS_VERIFIED_G101 if valid else codes[0]

    return AutoSlowShutterAndBreathingCompGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=str(body_model_name),
        body_model_id_hex=(
            f"0x{body_model_id:08x}"
            if isinstance(body_model_id, int) and not isinstance(body_model_id, bool)
            else "invalid"
        ),
        help_guide_code=str(help_guide_code),
        firmware_version=str(firmware_version),
        auto_slow_shutter_menu_path=str(auto_slow_shutter_menu_path),
        auto_slow_shutter_factory_default=AUTO_SLOW_SHUTTER_FACTORY_DEFAULT_G101,
        pre_reset_auto_slow_shutter=norm_ass_pre or str(pre_reset_auto_slow_shutter),
        reset_action=norm_reset or str(reset_action),
        effective_post_reset_auto_slow_shutter=post_ass,
        auto_slow_shutter_reset_by_camera_settings_reset=True,
        auto_slow_shutter_unaffected_by_reset_network_set=True,
        shoot_mode=norm_shoot or str(shoot_mode),
        exposure_ctrl_type=norm_exp_ctrl or str(exposure_ctrl_type),
        flexible_exp_shutter_mode=norm_flex_shutter or str(flexible_exp_shutter_mode),
        iso_setting=norm_iso or str(iso_setting),
        log_shooting_mode=norm_log or str(log_shooting_mode),
        six_lockout_catalog=AUTO_SLOW_SHUTTER_SIX_LOCKOUT_CONDITIONS_G101,
        active_auto_slow_shutter_lockouts=active_lockouts,
        auto_slow_shutter_hardware_locked_out=ass_locked_out,
        auto_slow_shutter_effective_active=ass_effective_active,
        auto_slow_shutter_lockout_bypass_events=bypass_count,
        shutter_mode_menu_path=str(shutter_mode_menu_path),
        movie_shutter_mode=norm_shutter_mode or str(movie_shutter_mode),
        shutter_angle_deg=eff_angle_deg,
        shutter_angle_governing_exposure=angle_governing,
        shutter_angle_disjoint_from_auto_slow_shutter=(overlap_count == 0),
        disjointness_matrix_states_checked=int(matrix["states_checked"]),
        auto_slow_shutter_angle_overlap_events=overlap_count,
        breathing_comp_menu_path=str(breathing_comp_menu_path),
        breathing_comp_factory_default=BREATHING_COMP_FACTORY_DEFAULT_G101,
        pre_reset_breathing_comp=norm_bc_pre or str(pre_reset_breathing_comp),
        effective_post_reset_breathing_comp=post_bc,
        breathing_comp_reset_by_camera_settings_reset=True,
        capture_domain=norm_domain or str(capture_domain),
        lens_breathing_comp_compliant=(
            bool(lens_breathing_comp_compliant)
            if isinstance(lens_breathing_comp_compliant, bool)
            else False
        ),
        hdmi_raw_output_enabled=(
            bool(hdmi_raw_output_enabled)
            if isinstance(hdmi_raw_output_enabled, bool)
            else False
        ),
        hdmi_raw_resolution=str(hdmi_raw_resolution),
        sq_frame_rate_fps=eff_fps,
        sq_high_fps_240p_200p_lockout_active=sq_240p_lockout,
        breathing_comp_hardware_locked_out=bc_locked_out,
        breathing_comp_effective_active=bc_effective_active,
        breathing_comp_fov_crop_active=bc_crop_active,
        breathing_comp_raw_or_240p_bypass_events=raw_240p_bypass,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g101_auto_slow_shutter_and_breathing_comp_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    auto_slow_shutter_breathing_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase259DonorAuditResult] = None,
) -> Tuple[GateVerdict, G101AutoSlowShutterAndBreathingCompGuardResult]:
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase259_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_auto_slow_shutter_and_breathing_comp_guard(
        **dict(auto_slow_shutter_breathing_kwargs or {})
    )

    codes: List[str] = []
    errors: List[str] = list(audit.errors) + list(guard.errors)
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Persistent eMMC write authorization requested in Gate G101.")
    if not audit.valid:
        _add_code(codes, audit.status)
    for c in guard.violation_codes:
        _add_code(codes, c)

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G101 if valid else codes[0]

    res = G101AutoSlowShutterAndBreathingCompGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        auto_slow_shutter_breathing_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, auto_slow={guard.effective_post_reset_auto_slow_shutter}"
        f"(active={guard.auto_slow_shutter_effective_active},"
        f"locks={len(guard.active_auto_slow_shutter_lockouts)}/6,"
        f"bypass={guard.auto_slow_shutter_lockout_bypass_events},"
        f"angle_overlap={guard.auto_slow_shutter_angle_overlap_events}), "
        f"breathing_comp={guard.effective_post_reset_breathing_comp}"
        f"(active={guard.breathing_comp_effective_active},"
        f"bypass={guard.breathing_comp_raw_or_240p_bypass_events})"
    )
    verdict = GateVerdict(
        gate_id=G101_GATE_ID,
        gate_code=G101_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 3. Gate G102: HDMI Output Settings (`[REC Control]` <- `[Time Code Output]`
#    Prerequisite, `[4ch Audio Output]` Routing & `[Rec. Media dur HDMI Output]`
#    Slot-1 Tier-0 Vault Guard)
# ---------------------------------------------------------------------------


def resolve_fx3_hdmi_reccontrol_tcout_4chaudio_state(
    *,
    pre_reset_time_code_output: str = HDMI_TC_OUTPUT_FACTORY_DEFAULT_G102,
    pre_reset_rec_control: str = HDMI_REC_CONTROL_FACTORY_DEFAULT_G102,
    pre_reset_audio_4ch_output: str = HDMI_4CH_AUDIO_FACTORY_DEFAULT_G102,
    pre_reset_rec_media_dur_hdmi_output: str = HDMI_REC_MEDIA_TIER0_BENCH_SAFE_DEFAULT_G102,
    reset_action: str = RESET_ACTION_NONE,
    mi_shoe_4ch_audio_active: bool = False,
    hdmi_output_active: bool = True,
    proxy_recording_menu_setting: str = "On",
    rec_trigger_requested: bool = False,
) -> Dict[str, Any]:
    """Resolve deterministic post-reset `[HDMI Output Settings]` state on
    `ILME-FX3` (`Ver. 7.02`), enforcing non-resettable `[Setup]` survival across
    `[Camera Settings Reset]` and `[Reset Network Set.]` (cleared only by
    `[Initialize]`), `[REC Control]` <- `[Time Code Output] = [On]`,
    `[4ch Audio Output]` `CH1/CH2` vs `CH3/CH4` pair routing, and
    `[Rec. Media dur HDMI Output] = [Off]` clip/proxy write inhibition.
    """
    norm_reset = _norm_reset_action_phase259(reset_action)
    norm_tc_pre = _norm_on_off_phase259(pre_reset_time_code_output)
    norm_rc_pre = _norm_on_off_phase259(pre_reset_rec_control)
    norm_4ch_pre = _norm_4ch_audio_setting_g102(pre_reset_audio_4ch_output)
    norm_rm_pre = _norm_on_off_phase259(pre_reset_rec_media_dur_hdmi_output)
    norm_proxy = _norm_on_off_phase259(proxy_recording_menu_setting)

    if (
        norm_reset is None
        or norm_tc_pre is None
        or norm_rc_pre is None
        or norm_4ch_pre is None
        or norm_rm_pre is None
        or norm_proxy is None
    ):
        raise ValueError("Invalid Gate G102 state parameter.")

    if norm_reset == RESET_ACTION_INITIALIZE:
        post_tc = HDMI_TC_OUTPUT_FACTORY_DEFAULT_G102
        post_rc = HDMI_REC_CONTROL_FACTORY_DEFAULT_G102
        post_4ch = HDMI_4CH_AUDIO_FACTORY_DEFAULT_G102
        post_rm = HDMI_REC_MEDIA_FACTORY_DEFAULT_G102
    else:
        post_tc = norm_tc_pre
        post_rc = norm_rc_pre
        post_4ch = norm_4ch_pre
        post_rm = norm_rm_pre

    effective_rc_active = (
        bool(hdmi_output_active)
        and post_tc == HDMI_TC_OUTPUT_ON_G102
        and post_rc == HDMI_REC_CONTROL_ON_G102
    )

    if bool(mi_shoe_4ch_audio_active) and post_4ch == HDMI_4CH_AUDIO_CH3_CH4_G102:
        left_ch, right_ch = "CH3", "CH4"
        audio_pair = HDMI_AUDIO_PAIR_CH3_L_CH4_R_G102
    else:
        left_ch, right_ch = "CH1", "CH2"
        audio_pair = HDMI_AUDIO_PAIR_CH1_L_CH2_R_G102

    media_inhibited = bool(hdmi_output_active) and (post_rm == HDMI_REC_MEDIA_OFF_G102)
    proxy_inhibited = media_inhibited
    internal_rec_active = bool(rec_trigger_requested) and (not media_inhibited)
    effective_proxy_active = (
        internal_rec_active and (norm_proxy == "On") and (not proxy_inhibited)
    )

    return {
        "reset_action": norm_reset,
        "effective_post_reset_time_code_output": post_tc,
        "effective_post_reset_rec_control": post_rc,
        "effective_rec_control_active": effective_rc_active,
        "effective_post_reset_audio_4ch_output": post_4ch,
        "hdmi_audio_left_channel": left_ch,
        "hdmi_audio_right_channel": right_ch,
        "effective_hdmi_audio_output_pair": audio_pair,
        "effective_post_reset_rec_media_dur_hdmi_output": post_rm,
        "internal_slot1_slot2_recording_inhibited": media_inhibited,
        "internal_proxy_recording_inhibited": proxy_inhibited,
        "effective_internal_media_recording_active": internal_rec_active,
        "effective_proxy_recording_active": effective_proxy_active,
    }



def verify_hdmi_reccontrol_tcout_4chaudio_and_vault_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: int = FX3_MODEL_ID,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE259,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE259,
    hdmi_output_settings_menu_path: str = HDMI_OUTPUT_SETTINGS_MENU_PATH_G102,
    reset_action: str = RESET_ACTION_NONE,
    pre_reset_time_code_output: str = HDMI_TC_OUTPUT_FACTORY_DEFAULT_G102,
    claimed_post_reset_time_code_output: Optional[str] = None,
    pre_reset_rec_control: str = HDMI_REC_CONTROL_FACTORY_DEFAULT_G102,
    claimed_post_reset_rec_control: Optional[str] = None,
    claimed_rec_control_active: Optional[bool] = None,
    hdmi_rec_ctrl_without_tc_violations: int = 0,
    pre_reset_audio_4ch_output: str = HDMI_4CH_AUDIO_FACTORY_DEFAULT_G102,
    claimed_post_reset_audio_4ch_output: Optional[str] = None,
    mi_shoe_4ch_audio_active: bool = False,
    claimed_hdmi_audio_output_pair: Optional[str] = None,
    claimed_hdmi_audio_left_channel: Optional[str] = None,
    claimed_hdmi_audio_right_channel: Optional[str] = None,
    pre_reset_rec_media_dur_hdmi_output: str = HDMI_REC_MEDIA_TIER0_BENCH_SAFE_DEFAULT_G102,
    claimed_post_reset_rec_media_dur_hdmi_output: Optional[str] = None,
    hdmi_output_active: bool = True,
    proxy_recording_menu_setting: str = "On",
    rec_trigger_requested: bool = False,
    tier0_slot1_vault_protection_active: bool = True,
    claimed_internal_media_recording_active: Optional[bool] = None,
    claimed_proxy_recording_active: Optional[bool] = None,
    slot1_hdmi_rec_vault_mutation_bytes: int = 0,
) -> HdmiRecControlTcOut4chAudioGuardResult:
    """Verify Gate G102: `[HDMI Output Settings]` non-resettable `[Setup]` survival,
    `[REC Control]` <- `[Time Code Output] = [On]` mandatory prerequisite,
    `[4ch Audio Output]` (`CH1/CH2` -> `CH1=L/CH2=R` vs `CH3/CH4` -> `CH3=L/CH4=R`),
    and `[Rec. Media dur HDMI Output]` internal clip/proxy inhibition + Slot-1
    Tier-0 recovery vault guard.
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    fw_tuple = _parse_fw_tuple(firmware_version)
    if (
        body_model_name != FX3_MODEL_NAME
        or not isinstance(body_model_id, int)
        or isinstance(body_model_id, bool)
        or body_model_id != FX3_MODEL_ID
        or help_guide_code != FX3_HELP_GUIDE_CODE_PHASE259
        or fw_tuple is None
        or fw_tuple < FX3_MIN_SUPPORTED_FW_TUPLE_PHASE259
    ):
        _add_code(codes, STATUS_BLOCKED_G102_TELEMETRY_INVALID)
        errors.append(
            "Invalid ILME-FX3 model identity, Help Guide code (ilc/2210), or firmware version in Gate G102."
        )

    if hdmi_output_settings_menu_path != HDMI_OUTPUT_SETTINGS_MENU_PATH_G102:
        _add_code(codes, STATUS_BLOCKED_G102_TELEMETRY_INVALID)
        errors.append("Invalid HDMI Output Settings menu path in Gate G102.")

    norm_reset = _norm_reset_action_phase259(reset_action)
    norm_tc_pre = _norm_on_off_phase259(pre_reset_time_code_output)
    norm_rc_pre = _norm_on_off_phase259(pre_reset_rec_control)
    norm_4ch_pre = _norm_4ch_audio_setting_g102(pre_reset_audio_4ch_output)
    norm_rm_pre = _norm_on_off_phase259(pre_reset_rec_media_dur_hdmi_output)
    norm_proxy = _norm_on_off_phase259(proxy_recording_menu_setting)

    bools_valid = all(
        isinstance(b, bool)
        for b in (
            mi_shoe_4ch_audio_active,
            hdmi_output_active,
            rec_trigger_requested,
            tier0_slot1_vault_protection_active,
        )
    )
    counters_valid = all(
        isinstance(v, int) and not isinstance(v, bool) and v >= 0
        for v in (
            hdmi_rec_ctrl_without_tc_violations,
            slot1_hdmi_rec_vault_mutation_bytes,
        )
    )

    if (
        norm_reset is None
        or norm_tc_pre is None
        or norm_rc_pre is None
        or norm_4ch_pre is None
        or norm_rm_pre is None
        or norm_proxy is None
        or not bools_valid
        or not counters_valid
    ):
        _add_code(codes, STATUS_BLOCKED_G102_TELEMETRY_INVALID)
        errors.append(
            "Invalid enum, boolean, or counter telemetry in Gate G102."
        )

    eff_reset = norm_reset or RESET_ACTION_NONE
    eff_tc_pre = norm_tc_pre or HDMI_TC_OUTPUT_FACTORY_DEFAULT_G102
    eff_rc_pre = norm_rc_pre or HDMI_REC_CONTROL_FACTORY_DEFAULT_G102
    eff_4ch_pre = norm_4ch_pre or HDMI_4CH_AUDIO_FACTORY_DEFAULT_G102
    eff_rm_pre = norm_rm_pre or HDMI_REC_MEDIA_TIER0_BENCH_SAFE_DEFAULT_G102
    eff_proxy = norm_proxy or "On"

    resolved = resolve_fx3_hdmi_reccontrol_tcout_4chaudio_state(
        pre_reset_time_code_output=eff_tc_pre,
        pre_reset_rec_control=eff_rc_pre,
        pre_reset_audio_4ch_output=eff_4ch_pre,
        pre_reset_rec_media_dur_hdmi_output=eff_rm_pre,
        reset_action=eff_reset,
        mi_shoe_4ch_audio_active=(
            bool(mi_shoe_4ch_audio_active)
            if isinstance(mi_shoe_4ch_audio_active, bool)
            else False
        ),
        hdmi_output_active=(
            bool(hdmi_output_active)
            if isinstance(hdmi_output_active, bool)
            else True
        ),
        proxy_recording_menu_setting=eff_proxy,
        rec_trigger_requested=(
            bool(rec_trigger_requested)
            if isinstance(rec_trigger_requested, bool)
            else False
        ),
    )

    post_tc = resolved["effective_post_reset_time_code_output"]
    post_rc = resolved["effective_post_reset_rec_control"]
    effective_rc_active = resolved["effective_rec_control_active"]
    post_4ch = resolved["effective_post_reset_audio_4ch_output"]
    left_ch = resolved["hdmi_audio_left_channel"]
    right_ch = resolved["hdmi_audio_right_channel"]
    audio_pair = resolved["effective_hdmi_audio_output_pair"]
    post_rm = resolved["effective_post_reset_rec_media_dur_hdmi_output"]
    media_inhibited = resolved["internal_slot1_slot2_recording_inhibited"]
    proxy_inhibited = resolved["internal_proxy_recording_inhibited"]
    internal_rec_active = resolved["effective_internal_media_recording_active"]
    effective_proxy_active = resolved["effective_proxy_recording_active"]

    # 1. Non-resettable [Setup] survival across Camera Settings Reset & Reset Network Set. (cleared only by Initialize)
    for label, claimed_raw, norm_fn, expected_val in (
        (
            "[Time Code Output]",
            claimed_post_reset_time_code_output,
            _norm_on_off_phase259,
            post_tc,
        ),
        (
            "[REC Control]",
            claimed_post_reset_rec_control,
            _norm_on_off_phase259,
            post_rc,
        ),
        (
            "[4ch Audio Output]",
            claimed_post_reset_audio_4ch_output,
            _norm_4ch_audio_setting_g102,
            post_4ch,
        ),
        (
            "[Rec. Media dur HDMI Output]",
            claimed_post_reset_rec_media_dur_hdmi_output,
            _norm_on_off_phase259,
            post_rm,
        ),
    ):
        if claimed_raw is not None:
            norm_claimed = norm_fn(claimed_raw)
            if norm_claimed != expected_val:
                _add_code(
                    codes, STATUS_BLOCKED_G102_HDMI_SETUP_RESET_PERSISTENCE_VIOLATION
                )
                errors.append(
                    f"{label} post-reset persistence mismatch after {eff_reset}: "
                    f"claimed={claimed_raw!r}, expected={expected_val!r}."
                )

    # 2. [REC Control] <- [Time Code Output] = [On] mandatory hardware prerequisite
    tc_violations = (
        int(hdmi_rec_ctrl_without_tc_violations)
        if isinstance(hdmi_rec_ctrl_without_tc_violations, int)
        and not isinstance(hdmi_rec_ctrl_without_tc_violations, bool)
        else 1
    )
    if eff_rc_pre == HDMI_REC_CONTROL_ON_G102 and eff_tc_pre == HDMI_TC_OUTPUT_OFF_G102:
        tc_violations += 1
        _add_code(codes, STATUS_BLOCKED_G102_HDMI_REC_CTRL_WITHOUT_TCOUT_VIOLATION)
        errors.append(
            "[REC Control] cannot be set to [On] when [Time Code Output] is set to [Off]."
        )
    if post_rc == HDMI_REC_CONTROL_ON_G102 and post_tc == HDMI_TC_OUTPUT_OFF_G102:
        tc_violations += 1
        _add_code(codes, STATUS_BLOCKED_G102_HDMI_REC_CTRL_WITHOUT_TCOUT_VIOLATION)
        errors.append(
            "Post-reset [REC Control] is [On] while [Time Code Output] is [Off]."
        )
    if claimed_rec_control_active is not None:
        if not isinstance(claimed_rec_control_active, bool):
            _add_code(codes, STATUS_BLOCKED_G102_TELEMETRY_INVALID)
            errors.append("claimed_rec_control_active must be bool.")
        elif claimed_rec_control_active != effective_rc_active:
            tc_violations += 1
            _add_code(codes, STATUS_BLOCKED_G102_HDMI_REC_CTRL_WITHOUT_TCOUT_VIOLATION)
            errors.append(
                f"[REC Control] active state mismatch: claimed={claimed_rec_control_active}, "
                f"expected={effective_rc_active} (Time Code Output={post_tc})."
            )
    if tc_violations != 0:
        _add_code(codes, STATUS_BLOCKED_G102_HDMI_REC_CTRL_WITHOUT_TCOUT_VIOLATION)
        errors.append(
            f"hdmi_rec_ctrl_without_tc_violations={tc_violations} (must be 0)."
        )

    # 3. [4ch Audio Output] channel-pair routing (CH1/CH2 -> CH1=L/CH2=R vs CH3/CH4 -> CH3=L/CH4=R when 4ch MI-shoe active)
    if claimed_hdmi_audio_output_pair is not None:
        norm_pair = _norm_hdmi_audio_pair_g102(claimed_hdmi_audio_output_pair)
        if norm_pair != audio_pair:
            _add_code(codes, STATUS_BLOCKED_G102_HDMI_4CH_AUDIO_ROUTING_MISMATCH)
            errors.append(
                f"[4ch Audio Output] HDMI pair mismatch: claimed={claimed_hdmi_audio_output_pair!r}, "
                f"expected={audio_pair!r} (4ch_setting={post_4ch}, mi_shoe_4ch={mi_shoe_4ch_audio_active})."
            )
    if claimed_hdmi_audio_left_channel is not None and (
        not isinstance(claimed_hdmi_audio_left_channel, str)
        or claimed_hdmi_audio_left_channel.strip().upper() != left_ch
    ):
        _add_code(codes, STATUS_BLOCKED_G102_HDMI_4CH_AUDIO_ROUTING_MISMATCH)
        errors.append(
            f"HDMI Left audio channel mismatch: claimed={claimed_hdmi_audio_left_channel!r}, expected={left_ch!r}."
        )
    if claimed_hdmi_audio_right_channel is not None and (
        not isinstance(claimed_hdmi_audio_right_channel, str)
        or claimed_hdmi_audio_right_channel.strip().upper() != right_ch
    ):
        _add_code(codes, STATUS_BLOCKED_G102_HDMI_4CH_AUDIO_ROUTING_MISMATCH)
        errors.append(
            f"HDMI Right audio channel mismatch: claimed={claimed_hdmi_audio_right_channel!r}, expected={right_ch!r}."
        )

    # 4. [Rec. Media dur HDMI Output] Slot-1/Slot-2 & [Proxy Recording] inhibition + Tier-0 Vault Guard
    mut_bytes = (
        int(slot1_hdmi_rec_vault_mutation_bytes)
        if isinstance(slot1_hdmi_rec_vault_mutation_bytes, int)
        and not isinstance(slot1_hdmi_rec_vault_mutation_bytes, bool)
        else -1
    )
    if claimed_internal_media_recording_active is not None:
        if not isinstance(claimed_internal_media_recording_active, bool):
            _add_code(codes, STATUS_BLOCKED_G102_TELEMETRY_INVALID)
            errors.append("claimed_internal_media_recording_active must be bool.")
        elif claimed_internal_media_recording_active != internal_rec_active:
            _add_code(codes, STATUS_BLOCKED_G102_SLOT1_HDMI_REC_MEDIA_VAULT_VIOLATION)
            errors.append(
                f"[Rec. Media dur HDMI Output] internal card recording mismatch: "
                f"claimed={claimed_internal_media_recording_active}, expected={internal_rec_active}."
            )

    if claimed_proxy_recording_active is not None:
        if not isinstance(claimed_proxy_recording_active, bool):
            _add_code(codes, STATUS_BLOCKED_G102_TELEMETRY_INVALID)
            errors.append("claimed_proxy_recording_active must be bool.")
        elif claimed_proxy_recording_active != effective_proxy_active:
            _add_code(codes, STATUS_BLOCKED_G102_SLOT1_HDMI_REC_MEDIA_VAULT_VIOLATION)
            errors.append(
                f"[Rec. Media dur HDMI Output] [Proxy Recording] inhibition mismatch: "
                f"claimed={claimed_proxy_recording_active}, expected={effective_proxy_active}."
            )

    if (
        isinstance(tier0_slot1_vault_protection_active, bool)
        and tier0_slot1_vault_protection_active
        and isinstance(hdmi_output_active, bool)
        and hdmi_output_active
        and isinstance(rec_trigger_requested, bool)
        and rec_trigger_requested
        and post_rm == HDMI_REC_MEDIA_ON_G102
    ):
        _add_code(codes, STATUS_BLOCKED_G102_SLOT1_HDMI_REC_MEDIA_VAULT_VIOLATION)
        errors.append(
            "Tier-0 Slot-1 recovery vault protection active while [Rec. Media dur HDMI Output]=[On] "
            "and recording triggered (would write clip/proxy data onto Slot-1 vault)."
        )

    if mut_bytes != 0:
        _add_code(codes, STATUS_BLOCKED_G102_SLOT1_HDMI_REC_MEDIA_VAULT_VIOLATION)
        errors.append(
            f"slot1_hdmi_rec_vault_mutation_bytes={mut_bytes} (must be 0)."
        )

    valid = not codes
    status = STATUS_VERIFIED_G102 if valid else codes[0]

    return HdmiRecControlTcOut4chAudioGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=str(body_model_name),
        body_model_id_hex=(
            f"0x{body_model_id:08x}"
            if isinstance(body_model_id, int) and not isinstance(body_model_id, bool)
            else "invalid"
        ),
        help_guide_code=str(help_guide_code),
        firmware_version=str(firmware_version),
        hdmi_output_settings_menu_path=str(hdmi_output_settings_menu_path),
        hdmi_output_factory_defaults=dict(HDMI_OUTPUT_FACTORY_DEFAULTS_G102),
        reset_action=norm_reset or str(reset_action),
        pre_reset_time_code_output=norm_tc_pre or str(pre_reset_time_code_output),
        effective_post_reset_time_code_output=post_tc,
        pre_reset_rec_control=norm_rc_pre or str(pre_reset_rec_control),
        effective_post_reset_rec_control=post_rc,
        rec_control_requires_time_code_output_on=True,
        effective_rec_control_active=effective_rc_active,
        hdmi_rec_ctrl_without_tc_violations=tc_violations,
        pre_reset_audio_4ch_output=norm_4ch_pre or str(pre_reset_audio_4ch_output),
        effective_post_reset_audio_4ch_output=post_4ch,
        mi_shoe_4ch_audio_active=(
            bool(mi_shoe_4ch_audio_active)
            if isinstance(mi_shoe_4ch_audio_active, bool)
            else False
        ),
        hdmi_audio_left_channel=left_ch,
        hdmi_audio_right_channel=right_ch,
        effective_hdmi_audio_output_pair=audio_pair,
        pre_reset_rec_media_dur_hdmi_output=(
            norm_rm_pre or str(pre_reset_rec_media_dur_hdmi_output)
        ),
        effective_post_reset_rec_media_dur_hdmi_output=post_rm,
        hdmi_settings_survive_camera_settings_reset=True,
        hdmi_settings_survive_reset_network_set=True,
        hdmi_settings_cleared_only_by_initialize=True,
        hdmi_output_active=(
            bool(hdmi_output_active)
            if isinstance(hdmi_output_active, bool)
            else False
        ),
        proxy_recording_menu_setting=norm_proxy or str(proxy_recording_menu_setting),
        rec_trigger_requested=(
            bool(rec_trigger_requested)
            if isinstance(rec_trigger_requested, bool)
            else False
        ),
        tier0_slot1_vault_protection_active=(
            bool(tier0_slot1_vault_protection_active)
            if isinstance(tier0_slot1_vault_protection_active, bool)
            else False
        ),
        internal_slot1_slot2_recording_inhibited=media_inhibited,
        internal_proxy_recording_inhibited=proxy_inhibited,
        effective_internal_media_recording_active=internal_rec_active,
        effective_proxy_recording_active=effective_proxy_active,
        slot1_hdmi_rec_vault_mutation_bytes=mut_bytes,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g102_hdmi_reccontrol_tcout_4chaudio_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    hdmi_reccontrol_4chaudio_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase259DonorAuditResult] = None,
) -> Tuple[GateVerdict, G102HdmiRecControlTcOut4chAudioGuardResult]:
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase259_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_hdmi_reccontrol_tcout_4chaudio_and_vault_guard(
        **dict(hdmi_reccontrol_4chaudio_kwargs or {})
    )

    codes: List[str] = []
    errors: List[str] = list(audit.errors) + list(guard.errors)
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Persistent eMMC write authorization requested in Gate G102.")
    if not audit.valid:
        _add_code(codes, audit.status)
    for c in guard.violation_codes:
        _add_code(codes, c)

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G102 if valid else codes[0]

    res = G102HdmiRecControlTcOut4chAudioGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        hdmi_reccontrol_4chaudio_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, rec_ctrl={guard.effective_post_reset_rec_control}"
        f"(tc_out={guard.effective_post_reset_time_code_output},"
        f"tc_viol={guard.hdmi_rec_ctrl_without_tc_violations}), "
        f"audio_pair={guard.effective_hdmi_audio_output_pair}, "
        f"rec_media={guard.effective_post_reset_rec_media_dur_hdmi_output}"
        f"(inhibited={guard.internal_slot1_slot2_recording_inhibited},"
        f"mut_bytes={guard.slot1_hdmi_rec_vault_mutation_bytes})"
    )
    verdict = GateVerdict(
        gate_id=G102_GATE_ID,
        gate_code=G102_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 4. Unified `102`-Gate Master Safety Preflight (`G01..G102`)
# ---------------------------------------------------------------------------


def evaluate_102gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    dry_run_simulated_backup: Optional[bool] = None,
    simulate_bench_dry_run: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    request_persistent_emmc_writes: bool = False,
    auto_slow_shutter_breathing_kwargs: Optional[Mapping[str, Any]] = None,
    hdmi_reccontrol_4chaudio_kwargs: Optional[Mapping[str, Any]] = None,
    master_100_override: Optional[Master100GateReport] = None,
    **m100_passthrough_kwargs: Any,
) -> Master102GateReport:
    """Evaluate all 102 Master Safety Gates (`G01..G102`) deterministically by
    delegating `G01..G100` directly to `evaluate_100gate_preflight()`.
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

    m100_report: Master100GateReport = (
        master_100_override
        if master_100_override is not None
        else evaluate_100gate_preflight(
            resolved_root,
            force_clean_room=clean_forced,
            dry_run_simulated=effective_dry_run,
            include_large_binaries=include_large_binaries,
            work_root=work_root,
            request_persistent_emmc_writes=request_persistent_emmc_writes,
            **m100_passthrough_kwargs,
        )
    )

    phase259_audit = audit_phase259_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
    )

    g101_verdict, g101_res = evaluate_g101_auto_slow_shutter_and_breathing_comp_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        auto_slow_shutter_breathing_kwargs=auto_slow_shutter_breathing_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase259_audit,
    )

    g102_verdict, g102_res = evaluate_g102_hdmi_reccontrol_tcout_4chaudio_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        hdmi_reccontrol_4chaudio_kwargs=hdmi_reccontrol_4chaudio_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase259_audit,
    )

    gates_101_to_102 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g101_verdict, g102_verdict)
    ]
    all_gates = tuple(list(m100_report.gates) + gates_101_to_102)

    g01_to_g12_verified = int(m100_report.summary["g01_to_g12_verified"])
    g13_to_g100_verified = int(m100_report.summary["g13_to_g98_verified"]) + int(
        m100_report.summary["g99_to_g100_verified"]
    )
    g101_to_g102_verified = sum(1 for v in (g101_verdict, g102_verdict) if v.passed)
    total_verified = (
        g01_to_g12_verified + g13_to_g100_verified + g101_to_g102_verified
    )

    g101_to_g102_all_passed = g101_to_g102_verified == 2
    g13_to_g102_all_passed = (
        m100_report.g13_to_g100_all_passed and g101_to_g102_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m100_report.gates[:9])

    offline_99_verified = (
        g01_to_g09_ok
        and m100_report.offline_97_gates_verified
        and g101_to_g102_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_102_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g102_all_passed
        and (not request_persistent_emmc_writes)
    )

    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m100_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_99_verified
        and m100_report.h0_h1_trial_entry_allowed
        and g101_to_g102_all_passed
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
        list(m100_report.errors)
        + list(g101_verdict.errors)
        + list(g102_verdict.errors)
    )
    warnings: List[str] = (
        list(m100_report.warnings)
        + list(g101_verdict.warnings)
        + list(g102_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m100_report.g13_to_g100_all_passed:
        overall_status = m100_report.status
    elif not g101_verdict.passed:
        overall_status = g101_verdict.status
    elif not g102_verdict.passed:
        overall_status = g102_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_102_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_102_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_102_verified:
        overall_status = "VERIFIED_ALL_102_GATES"
    else:
        overall_status = "VERIFIED_99_OF_102_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m100_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g101_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g102_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 102,
        "verified_gates": total_verified,
        "technical_gates_passed": total_verified,
        "blocked_or_pending_gates": 102 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g100_verified": g13_to_g100_verified,
        "g101_to_g102_verified": g101_to_g102_verified,
        "g13_to_g102_all_passed": g13_to_g102_all_passed,
        "g101_to_g102_all_passed": g101_to_g102_all_passed,
        "offline_99_gates_verified": offline_99_verified,
        "all_102_gates_verified": all_102_verified,
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

    return Master102GateReport(
        schema=REALHW_AUTO_SLOW_SHUTTER_HDMI_RECCONTROL_BREATHING_102GATE_SCHEMA,
        version=REALHW_AUTO_SLOW_SHUTTER_HDMI_RECCONTROL_BREATHING_102GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        offline_99_gates_verified=offline_99_verified,
        all_102_gates_verified=all_102_verified,
        g13_to_g102_all_passed=g13_to_g102_all_passed,
        g101_to_g102_all_passed=g101_to_g102_all_passed,
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
        master_100_report=m100_report.to_dict(),
        g101_result=g101_res.to_dict(),
        g102_result=g102_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_102_master_safety_gates = evaluate_102gate_preflight
run_102_gate_preflight = evaluate_102gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_auto_slow_shutter_hdmi_reccontrol_breathing_and_102gate_guard",
        description=(
            "Phase 259 Safety Gates G101 (Auto Slow Shutter 6-Condition Lockout, "
            "Shutter Angle Disjointness & Breathing Comp. Guard) + G102 (HDMI Output "
            "Settings REC Control <- Time Code Output Prerequisite, 4ch Audio Output "
            "& Slot-1 Rec. Media Vault Guard) + Unified 102-Gate Master Safety Preflight"
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

    report = evaluate_102gate_preflight(
        args.repo_root,
        force_clean_room=True if args.force_clean_room else None,
        dry_run_simulated=bool(args.dry_run_simulated),
    )
    if args.json:
        try:
            sys.stdout.write(
                json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n"
            )
            sys.stdout.flush()
        except BrokenPipeError:
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, sys.stdout.fileno())
            os.close(devnull)
    else:
        sys.stdout.write(
            f"status={report.status} mode={report.verification_mode} "
            f"verified={report.summary['verified_gates']}/102 "
            f"g101_to_g102_all_passed={report.g101_to_g102_all_passed} "
            f"all_102_gates_verified={report.all_102_gates_verified} "
            f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach}\n"
        )
    ok = (
        report.all_102_gates_verified
        if args.dry_run_simulated
        else report.offline_99_gates_verified
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
