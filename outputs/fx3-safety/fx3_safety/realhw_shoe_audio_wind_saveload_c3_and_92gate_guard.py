"""Phase 241 (`92/92` Wave-36) Sony `ILME-FX3` (`Ver. 7.02`) Safety Gates `G91`
(`[Shoe Audio Set.]` `48kHz/24bit 4ch` Meter/Routing Guard & `[Wind Noise Reduct.]`
Built-In-Mic-Only Boundary) & `G92` (`[Save/Load Settings]` `CAMSET01..10.DAT` /
`C3 Portal` Excluded-Items Privacy/Calibration Firewall & Slot-1 Tier-0 Vault
Write Guard) + Unified 92-Gate Master Safety Preflight (`G01..G92`).

Operationalizes Wave-36 official Sony `ILME-FX3` (`Ver. 7.02`) intelligence
(`reports/2026-11-15-global-sony-wave36-shoe-audio-4ch-wind-noise-builtin-only-saveload-c3-exclusions-intel/README.md`)
as deterministic offline preflight verifiers (`G91` and `G92`) and delegates
`G01..G90` directly to `evaluate_90gate_preflight()`.
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
from .realhw_dualmedia_bench_interlock_and_58gate_guard import (
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
)
from .realhw_emphasized_rec_grid_hdmi_touch_sunny_and_90gate_guard import (
    Master90GateReport,
    evaluate_90gate_preflight,
)
from .realhw_filesettings_shotmark_tcregen_reclamp_and_78gate_guard import (
    _DONOR_BLOB_CACHE,
)
from .realhw_pnflasha_mtdro_rfnvs_and_48gate_guard import SPI_NOR_WRITE_AUTHORIZED
from .thermal_pwm_and_power_guard import resolve_donor_thermal_power_paths

# ---------------------------------------------------------------------------
# Schema, Gate Identifiers & Hard-Locked Safety Redline Constants
# ---------------------------------------------------------------------------

REALHW_SHOE_AUDIO_WIND_SAVELOAD_C3_92GATE_SCHEMA: str = (
    "realhw_shoe_audio_wind_saveload_c3_and_92gate_guard_v1"
)
REALHW_SHOE_AUDIO_WIND_SAVELOAD_C3_92GATE_VERSION: str = "1.0.0"

G91_GATE_ID: str = "G91_shoe_audio_4ch_meter_routing_and_wind_noise_builtin_only_guard"
G91_GATE_CODE: str = (
    "SHOE_AUDIO_48KHZ_24BIT_4CH_METER_ROUTING_AND_WIND_NOISE_BUILTIN_ONLY_GUARD"
)

G92_GATE_ID: str = (
    "G92_saveload_camset_c3_excluded_items_and_slot1_tier0_vault_guard"
)
G92_GATE_CODE: str = (
    "SAVELOAD_CAMSET_C3_PORTAL_EXCLUDED_ITEMS_FIREWALL_AND_SLOT1_TIER0_VAULT_WRITE_GUARD"
)

G91: str = G91_GATE_ID
G92: str = G92_GATE_ID
GATE_G91_SHOE_AUDIO_48KHZ_24BIT_4CH_METER_ROUTING_AND_WIND_NOISE_BUILTIN_ONLY_GUARD: str = (
    G91_GATE_CODE
)
GATE_G92_SAVELOAD_CAMSET_C3_PORTAL_EXCLUDED_ITEMS_FIREWALL_AND_SLOT1_TIER0_VAULT_WRITE_GUARD: str = (
    G92_GATE_CODE
)

HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
HUMAN_HARDWARE_ATTACH_TOKEN: bool = False
USB_PACKETS_TRANSMITTED: int = 0
PHYSICAL_USB_PACKETS_EMITTED: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0
DONOR_CHECK_MAX_SECONDS_PHASE241: float = 0.10
DONOR_CHECK_MAX_SECONDS: float = DONOR_CHECK_MAX_SECONDS_PHASE241

FX3_MODEL_NAME: str = "ILME-FX3"
FX3_MODEL_ID: int = 0x91030080
FX3_DEFAULT_FW_VERSION_PHASE241: str = "7.02"
FX3_MIN_SUPPORTED_FW_TUPLE_PHASE241: Tuple[int, int] = (1, 0)
SAVELOAD_CLOUD_C3_MIN_FW_TUPLE: Tuple[int, int] = (4, 0)

RESET_ACTION_NONE: str = "NONE"
RESET_ACTION_CAMERA_SETTINGS_RESET: str = "Camera Settings Reset"
RESET_ACTION_INITIALIZE: str = "Initialize"
ALLOWED_RESET_ACTIONS_PHASE241: Tuple[str, ...] = (
    RESET_ACTION_NONE,
    RESET_ACTION_CAMERA_SETTINGS_RESET,
    RESET_ACTION_INITIALIZE,
)

# Status & Violation Codes
STATUS_VERIFIED_G91: str = (
    "VERIFIED_G91_SHOE_AUDIO_4CH_METER_ROUTING_AND_WIND_NOISE_BUILTIN_ONLY_SAFE"
)
STATUS_VERIFIED_G92: str = (
    "VERIFIED_G92_SAVELOAD_CAMSET_C3_EXCLUDED_ITEMS_AND_SLOT1_TIER0_VAULT_SAFE"
)
STATUS_BLOCKED_PHASE241_DONOR_INTEGRITY: str = (
    "BLOCKED_PHASE241_DONOR_CONTRACT_INTEGRITY"
)

STATUS_BLOCKED_G91_SHOE_AUDIO_SET_ENUM_OR_RESET_VIOLATION: str = (
    "BLOCKED_G91_SHOE_AUDIO_SET_ENUM_OR_RESET_VIOLATION"
)
STATUS_BLOCKED_G91_FOUR_CH_LOCKOUT_OR_ROUTING_OVERRIDE_VIOLATION: str = (
    "BLOCKED_G91_FOUR_CH_LOCKOUT_OR_ROUTING_OVERRIDE_VIOLATION"
)
STATUS_BLOCKED_G91_AUDIO_LEVEL_METER_EXPANSION_MISMATCH: str = (
    "BLOCKED_G91_AUDIO_LEVEL_METER_EXPANSION_MISMATCH"
)
STATUS_BLOCKED_G91_WIND_NOISE_REDUCT_ENUM_OR_RESET_VIOLATION: str = (
    "BLOCKED_G91_WIND_NOISE_REDUCT_ENUM_OR_RESET_VIOLATION"
)
STATUS_BLOCKED_G91_EXTERNAL_MIC_WIND_NOISE_REDUCT_FALSE_CLAIM: str = (
    "BLOCKED_G91_EXTERNAL_MIC_WIND_NOISE_REDUCT_FALSE_CLAIM"
)
STATUS_BLOCKED_G91_INDOOR_LOW_WIND_BENCH_ATTENUATION_HAZARD: str = (
    "BLOCKED_G91_INDOOR_LOW_WIND_BENCH_ATTENUATION_HAZARD"
)
STATUS_BLOCKED_G91_TELEMETRY_INVALID: str = (
    "BLOCKED_G91_SHOE_AUDIO_WIND_TELEMETRY_INVALID"
)

STATUS_BLOCKED_G92_SAVELOAD_TARGET_FILE_OR_COUNT_INVALID: str = (
    "BLOCKED_G92_SAVELOAD_TARGET_FILE_OR_COUNT_INVALID"
)
STATUS_BLOCKED_G92_CAMSET_OR_CLOUD_CROSS_MODEL_REJECTED: str = (
    "BLOCKED_G92_CAMSET_OR_CLOUD_CROSS_MODEL_REJECTED"
)
STATUS_BLOCKED_G92_CLOUD_C3_FIRMWARE_FLOOR_VIOLATION: str = (
    "BLOCKED_G92_CLOUD_C3_FIRMWARE_FLOOR_VIOLATION"
)
STATUS_BLOCKED_G92_EXCLUDED_PRIVACY_CALIBRATION_OR_CREDENTIAL_LEAK: str = (
    "BLOCKED_G92_EXCLUDED_PRIVACY_CALIBRATION_OR_CREDENTIAL_LEAK"
)
STATUS_BLOCKED_G92_SLOT1_TIER0_VAULT_CAMSET_SAVE_FORBIDDEN: str = (
    "BLOCKED_G92_SLOT1_TIER0_VAULT_CAMSET_SAVE_FORBIDDEN"
)
STATUS_BLOCKED_G92_LOAD_CARD_NON_RDONLY_MUTATION: str = (
    "BLOCKED_G92_LOAD_CARD_NON_RDONLY_MUTATION"
)
STATUS_BLOCKED_G92_TELEMETRY_INVALID: str = (
    "BLOCKED_G92_SAVELOAD_C3_EXCLUSIONS_TELEMETRY_INVALID"
)

# ---------------------------------------------------------------------------
# Gate G91 Canonical Constants: [Shoe Audio Set.] & [Wind Noise Reduct.]
# ---------------------------------------------------------------------------

SHOE_AUDIO_SET_MENU_PATH: str = (
    "MENU -> Shooting -> [Audio Recording] -> [Shoe Audio Set.]"
)
SHOE_AUDIO_48K_16BIT_2CH: str = "48kHz/16bit 2ch"
SHOE_AUDIO_48K_24BIT_2CH: str = "48kHz/24bit 2ch"
SHOE_AUDIO_48K_24BIT_4CH: str = "48kHz/24bit 4ch"
ALLOWED_SHOE_AUDIO_SET_MODES: Tuple[str, ...] = (
    SHOE_AUDIO_48K_16BIT_2CH,
    SHOE_AUDIO_48K_24BIT_2CH,
    SHOE_AUDIO_48K_24BIT_4CH,
)
SHOE_AUDIO_SET_FACTORY_DEFAULT: str = SHOE_AUDIO_48K_16BIT_2CH

WIND_NOISE_REDUCT_MENU_PATH: str = (
    "MENU -> Shooting -> [Audio Recording] -> [Wind Noise Reduct.]"
)
WIND_NOISE_REDUCT_OFF: str = "Off"
WIND_NOISE_REDUCT_ON: str = "On"
ALLOWED_WIND_NOISE_REDUCT_MODES: Tuple[str, ...] = (
    WIND_NOISE_REDUCT_OFF,
    WIND_NOISE_REDUCT_ON,
)
WIND_NOISE_REDUCT_FACTORY_DEFAULT: str = WIND_NOISE_REDUCT_OFF

AUDIO_LEVEL_DISPLAY_MENU_PATH: str = (
    "MENU -> Shooting -> [Audio Recording] -> [Audio Level Display]"
)
AUDIO_RECORDING_MENU_PATH_G91: str = (
    "MENU -> Shooting -> [Audio Recording] -> [Audio Recording]"
)

SHOOT_MODE_MOVIE_G91: str = "Movie"
SHOOT_MODE_SQ_MOTION_G91: str = "S&Q Motion"
SHOOT_MODE_STILL_G91: str = "Still"
ALLOWED_SHOOT_MODES_G91: Tuple[str, ...] = (
    SHOOT_MODE_MOVIE_G91,
    SHOOT_MODE_SQ_MOTION_G91,
    SHOOT_MODE_STILL_G91,
)

MISHOE_ACCESSORY_NONE_G91: str = "NONE"
MISHOE_ACCESSORY_XLR_H1_G91: str = "XLR-H1"
MISHOE_ACCESSORY_ECM_M1_G91: str = "ECM-M1"
MISHOE_ACCESSORY_ECM_B1M_G91: str = "ECM-B1M"
MISHOE_ACCESSORY_ANALOG_MIC_G91: str = "ANALOG_MISHOE_MIC"
ALLOWED_MISHOE_AUDIO_ACCESSORIES_G91: Tuple[str, ...] = (
    MISHOE_ACCESSORY_NONE_G91,
    MISHOE_ACCESSORY_XLR_H1_G91,
    MISHOE_ACCESSORY_ECM_M1_G91,
    MISHOE_ACCESSORY_ECM_B1M_G91,
    MISHOE_ACCESSORY_ANALOG_MIC_G91,
)
DIGITAL_4CH_MISHOE_ACCESSORIES_G91: Tuple[str, ...] = (
    MISHOE_ACCESSORY_XLR_H1_G91,
    MISHOE_ACCESSORY_ECM_M1_G91,
)
DIGITAL_2CH_MISHOE_ACCESSORIES_G91: Tuple[str, ...] = (
    MISHOE_ACCESSORY_XLR_H1_G91,
    MISHOE_ACCESSORY_ECM_M1_G91,
    MISHOE_ACCESSORY_ECM_B1M_G91,
)

XLRH1_SWITCH_DIGITAL_G91: str = "DIGITAL"
XLRH1_SWITCH_ANALOG_G91: str = "ANALOG"
ALLOWED_XLRH1_SWITCH_MODES_G91: Tuple[str, ...] = (
    XLRH1_SWITCH_DIGITAL_G91,
    XLRH1_SWITCH_ANALOG_G91,
)
XLRH1_HARDWARE_LOW_CUT_MODES_G91: Tuple[str, ...] = ("Off", "100Hz", "300Hz")

AUDIO_INPUT_SOURCE_DISABLED_G91: str = "AUDIO_DISABLED"
AUDIO_INPUT_SOURCE_BODY_35MM_ANALOG_G91: str = "BODY_35MM_ANALOG_ADC_2CH"
AUDIO_INPUT_SOURCE_MISHOE_ANALOG_2CH_G91: str = "MISHOE_ANALOG_2CH"
AUDIO_INPUT_SOURCE_MISHOE_DIGITAL_G91: str = "MISHOE_DIGITAL_I2S"
AUDIO_INPUT_SOURCE_BUILTIN_STEREO_MIC_G91: str = "BUILTIN_STEREO_MIC"

SHOE_AUDIO_3_DISQUALIFYING_CONDITIONS: Tuple[str, ...] = (
    "AUDIO_RECORDING_OFF_OR_SQ_MOTION",
    "BODY_35MM_MIC_JACK_PLUGIN_OVERRIDE",
    "XLR_H1_OR_MISHOE_ANALOG_SWITCH_FALLBACK",
)

# ---------------------------------------------------------------------------
# Gate G92 Canonical Constants: [Save/Load Settings] CAMSET & C3 Portal Guard
# ---------------------------------------------------------------------------

SAVE_LOAD_SETTINGS_MENU_PATH: str = (
    "MENU -> Setup -> [Reset/Save Settings] -> [Save/Load Settings]"
)

SAVELOAD_OP_NONE: str = "NONE"
SAVELOAD_OP_LOAD: str = "LOAD"
SAVELOAD_OP_SAVE: str = "SAVE"
ALLOWED_SAVELOAD_OPERATIONS: Tuple[str, ...] = (
    SAVELOAD_OP_NONE,
    SAVELOAD_OP_LOAD,
    SAVELOAD_OP_SAVE,
)

SAVELOAD_TARGET_MEDIA_SLOT_1: str = "Media(Slot 1)"
SAVELOAD_TARGET_MEDIA_SLOT_2: str = "Media(Slot 2)"
SAVELOAD_TARGET_CLOUD_PRIVATE: str = "Cloud(Private)"
SAVELOAD_TARGET_CLOUD_SHARE: str = "Cloud(Share)"
ALLOWED_SAVELOAD_TARGETS: Tuple[str, ...] = (
    SAVELOAD_TARGET_MEDIA_SLOT_1,
    SAVELOAD_TARGET_MEDIA_SLOT_2,
    SAVELOAD_TARGET_CLOUD_PRIVATE,
    SAVELOAD_TARGET_CLOUD_SHARE,
)
SAVELOAD_MEDIA_TARGETS: Tuple[str, ...] = (
    SAVELOAD_TARGET_MEDIA_SLOT_1,
    SAVELOAD_TARGET_MEDIA_SLOT_2,
)
SAVELOAD_CLOUD_C3_TARGETS: Tuple[str, ...] = (
    SAVELOAD_TARGET_CLOUD_PRIVATE,
    SAVELOAD_TARGET_CLOUD_SHARE,
)

SAVELOAD_MAX_CAMSET_FILES_PER_CARD: int = 10
SAVELOAD_ALLOWED_CAMSET_FILENAMES: Tuple[str, ...] = tuple(
    f"CAMSET{i:02d}.DAT" for i in range(1, SAVELOAD_MAX_CAMSET_FILES_PER_CARD + 1)
)
SAVELOAD_FX3_CAMSET_CARD_DIR: str = "/PRIVATE/SONY/PRO/CAMERA/ILME-FX3"

SAVELOAD_REJECTED_CROSS_MODELS: Tuple[str, ...] = (
    "ILME-FX6",
    "ILME-FX30",
    "ILME-FX3A",
    "ILCE-7SM3",
    "ILME-FR7",
    "MPC-2610",
)

SAVELOAD_EXCLUDED_ITEM_CATEGORIES: Tuple[str, ...] = (
    "IPTC Information",
    "Copyright Info",
    "Custom White Balance (Custom 1..3)",
    "Face Memory",
    "Network Credentials (FTP / RTMP-SRT Streaming / Wi-Fi / Static IP / TLS Certs)",
)

SAVELOAD_EXCLUDED_ITEM_TOKENS: Dict[str, Tuple[str, ...]] = {
    "IPTC Information": ("IPTC", "IPTC INFORMATION", "IPTC METADATA"),
    "Copyright Info": (
        "COPYRIGHT",
        "COPYRIGHT INFO",
        "WRITE COPYRIGHT INFO",
        "PHOTOGRAPHER NAME",
        "COPYRIGHT HOLDER",
    ),
    "Custom White Balance (Custom 1..3)": (
        "CUSTOM WHITE BALANCE",
        "CUSTOM WB",
        "CUSTOM 1",
        "CUSTOM 2",
        "CUSTOM 3",
        "CAPTURED WB",
    ),
    "Face Memory": ("FACE MEMORY", "REGISTERED FACE", "FACE TEMPLATE"),
    "Network Credentials (FTP / RTMP-SRT Streaming / Wi-Fi / Static IP / TLS Certs)": (
        "FTP",
        "RTMP",
        "RTMPS",
        "SRT",
        "STREAM KEY",
        "STREAMING",
        "WI-FI",
        "WIFI",
        "SSID",
        "PASSPHRASE",
        "WPA",
        "STATIC IP",
        "STATIC DNS",
        "TLS CERT",
        "ROOT CERT",
        "CLIENT CERT",
    ),
}

TIER0_VAULT_GUARDED_ARTIFACTS_G92: Tuple[str, ...] = (
    "pnflasha",
    "cnflasha",
    "CAMSET01.DAT",
)

# ---------------------------------------------------------------------------
# Pinned Local Donor Contracts (O_RDONLY, <0.10s, Clean-Room Fallback)
# ---------------------------------------------------------------------------

PINNED_PHASE241_DONOR_SPECS: Dict[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_cpapp_bin": (
        "FX3",
        "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin",
        15_980_568,
        "c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba",
        (
            b"ILME-FX3",
            b"Audio",
            b"Shoe",
            b"Wind",
            b"48kHz",
            b"24bit",
            b"4ch",
            b"Hotshoe",
            b"Reset",
            b"Initialize",
        ),
        "FX3_CPAPP_SHOE_AUDIO_4CH_AND_WIND_NOISE_STRINGS",
    ),
    "fx3_saveload_so": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libSaveLoadSettings.so",
        18_760,
        "07819f42bdad381ecdd41c3765c117c33b0c44c25be36279b26f83906d244cb7",
        (b"\x7fELF", b"SaveLoadSettings", b"Settings", b"Save", b"Backup"),
        "FX3_SAVELOAD_SETTINGS_CAMSET_EXCLUSIONS_ELF",
    ),
    "fx3_bk4_bin": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin",
        2_229_740,
        "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2",
        (b"BK4", b"ILME-FX3", b"FTP", b"TC", b"/setting"),
        "FX3_BK4_RESET_AND_CREDENTIAL_EXCLUSION_SEED",
    ),
    "fx6_bk4_bin": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0110_backup/SYSIPSX-DSLR/CHAPLIN/CX95898_NTSC.bin",
        2_253_333,
        "e2eafd4e950ead94fdba64722b225b9ccf4cf294ce4c1cf956b9e62926bbf89e",
        (b"BK4", b"NTSC", b"TC", b"Settings", b"/setting"),
        "FX6_CHAPLIN_BK4_CROSS_MODEL_CAMSET_REJECTION_REF",
    ),
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase241DonorAuditResult:
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
class ShoeAudio4chAndWindNoiseGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    body_model_name: str
    body_model_id_hex: str
    firmware_version: str
    shoe_audio_set_menu_path: str
    wind_noise_reduct_menu_path: str
    audio_level_display_menu_path: str
    pre_reset_shoe_audio_set: str
    pre_reset_wind_noise_reduct: str
    reset_action: str
    expected_post_reset_shoe_audio_set: str
    effective_post_reset_shoe_audio_set: str
    shoe_audio_set_reset_by_camera_settings_reset: bool
    expected_post_reset_wind_noise_reduct: str
    effective_post_reset_wind_noise_reduct: str
    wind_noise_reduct_reset_by_camera_settings_reset: bool
    shoot_mode: str
    audio_recording: str
    audio_level_display: str
    mishoe_accessory: str
    xlrh1_digital_analog_switch: str
    xlrh1_low_cut_switch: str
    body_35mm_mic_jack_plugged: bool
    disqualified_by_audio_off_or_sq: bool
    disqualified_by_35mm_jack_override: bool
    disqualified_by_analog_shoe_switch: bool
    active_disqualifying_conditions: Tuple[str, ...]
    shoe_audio_set_available: bool
    active_audio_input_source: str
    expected_effective_audio_format: str
    effective_audio_format: str
    expected_recorded_audio_channels: int
    effective_recorded_audio_channels: int
    expected_audio_level_meter_channels: int
    audio_level_meter_channels: int
    four_ch_audio_level_meter_expanded: bool
    wind_noise_reduct_available: bool
    builtin_mic_wind_reduct_effective: bool
    external_mic_wind_reduct_effective: bool
    indoor_low_wind_bench: bool
    indoor_low_wind_attenuation_blocked: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SaveLoadCamsetC3ExclusionsAndSlot1VaultResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    body_model_name: str
    body_model_id_hex: str
    firmware_version: str
    saveload_menu_path: str
    saveload_operation: str
    saveload_target: str
    is_media_target: bool
    is_cloud_c3_target: bool
    c3_portal_firmware_floor_met: bool
    camset_filename: str
    camset_card_path: str
    card_camset_file_count: int
    profile_model_header: str
    same_model_ilme_fx3_locked: bool
    action_item_not_reset_parameter: bool
    excluded_categories_enforced: Tuple[str, ...]
    leaked_excluded_categories: Tuple[str, ...]
    excluded_items_leaked_count: int
    iptc_info_excluded: bool
    copyright_info_excluded: bool
    custom_wb_1_to_3_excluded: bool
    face_memory_excluded: bool
    network_credentials_excluded: bool
    excluded_items_firewall_enforced: bool
    load_card_access_mode: str
    load_is_card_o_rdonly_safe: bool
    slot1_tier0_vault_active: bool
    slot1_present_artifacts: Tuple[str, ...]
    slot1_off_camera_sha256_verified: bool
    slot1_sdxc_wp_locked: bool
    slot1_unverified_camset_save_blocked: bool
    slot1_card_sector_writes: int
    slot1_vault_write_firewall_enforced: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G91ShoeAudioAndWindNoiseGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    shoe_audio_wind_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G92SaveLoadC3ExclusionsAndSlot1VaultGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    saveload_c3_exclusions_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master92GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    offline_89_gates_verified: bool
    all_92_gates_verified: bool
    g13_to_g92_all_passed: bool
    g91_to_g92_all_passed: bool
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
    master_90_report: Dict[str, Any]
    g91_result: Dict[str, Any]
    g92_result: Dict[str, Any]
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


def _norm_on_off(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = raw.strip().strip("[]").upper()
    if s == "ON":
        return "On"
    if s == "OFF":
        return "Off"
    return None


def _norm_reset_action(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if u in ("NONE", "NO RESET", ""):
        return RESET_ACTION_NONE
    if u == "CAMERA SETTINGS RESET":
        return RESET_ACTION_CAMERA_SETTINGS_RESET
    if u == "INITIALIZE":
        return RESET_ACTION_INITIALIZE
    return None


def _norm_shoe_audio_set(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    if s in ("48KHZ/16BIT 2CH", "48KHZ_16BIT_2CH"):
        return SHOE_AUDIO_48K_16BIT_2CH
    if s in ("48KHZ/24BIT 2CH", "48KHZ_24BIT_2CH"):
        return SHOE_AUDIO_48K_24BIT_2CH
    if s in ("48KHZ/24BIT 4CH", "48KHZ_24BIT_4CH"):
        return SHOE_AUDIO_48K_24BIT_4CH
    return None


def _norm_shoot_mode_g91(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if s in ("MOVIE", "MOVIE RECORDING", "MOVIE REC"):
        return SHOOT_MODE_MOVIE_G91
    if s in ("S&Q MOTION", "S&Q", "SQ MOTION", "SQ", "S&Q RECORDING"):
        return SHOOT_MODE_SQ_MOTION_G91
    if s in ("STILL", "STILL SHOOTING", "PHOTO"):
        return SHOOT_MODE_STILL_G91
    return None


def _norm_mishoe_accessory_g91(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    if s in ("NONE", "DETACHED", "EMPTY", ""):
        return MISHOE_ACCESSORY_NONE_G91
    if s in ("XLR-H1", "XLR_H1", "XLR-K3M", "XLR_K3M"):
        return MISHOE_ACCESSORY_XLR_H1_G91
    if s in ("ECM-M1", "ECM_M1"):
        return MISHOE_ACCESSORY_ECM_M1_G91
    if s in ("ECM-B1M", "ECM_B1M", "ECM-B10", "ECM_B10"):
        return MISHOE_ACCESSORY_ECM_B1M_G91
    if s in ("ANALOG_MISHOE_MIC", "ANALOG MISHOE MIC", "ECM-W2BT_ANALOG", "ANALOG_SHOE"):
        return MISHOE_ACCESSORY_ANALOG_MIC_G91
    return None


def _norm_xlrh1_switch_g91(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = raw.strip().strip("[]").upper()
    if s == "DIGITAL":
        return XLRH1_SWITCH_DIGITAL_G91
    if s == "ANALOG":
        return XLRH1_SWITCH_ANALOG_G91
    return None


def _norm_low_cut_g91(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = raw.strip().strip("[]").upper()
    if s == "OFF":
        return "Off"
    if s in ("100HZ", "100 HZ"):
        return "100Hz"
    if s in ("300HZ", "300 HZ"):
        return "300Hz"
    return None


# ---------------------------------------------------------------------------
# 1. Bounded `< 0.10s` O_RDONLY Donor Contract Audit (`Phase 241`)
# ---------------------------------------------------------------------------


def audit_phase241_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    max_budget_seconds: float = DONOR_CHECK_MAX_SECONDS_PHASE241,
) -> Phase241DonorAuditResult:
    """Inspect local FX3 Ver. 7.02 / FX6 Ver. 6.01 donor artifacts strictly
    `os.O_RDONLY` within `<0.10s`, with automatic `CLEAN_ROOM_SYNTHETIC`
    fallback when `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor paths are absent.
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
        for key, (_body, rel_path, *_rest) in PINNED_PHASE241_DONOR_SPECS.items():
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
            spec[5] for spec in PINNED_PHASE241_DONOR_SPECS.values()
        )
        synthetic_shas = {
            k: f"synthetic:{v[3][:16]}" for k, v in PINNED_PHASE241_DONOR_SPECS.items()
        }
        synthetic_sizes = {k: v[2] for k, v in PINNED_PHASE241_DONOR_SPECS.items()}
        return Phase241DonorAuditResult(
            valid=within_budget,
            status=(
                STATUS_VERIFIED_SAFE
                if within_budget
                else STATUS_BLOCKED_PHASE241_DONOR_INTEGRITY
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
    ) in PINNED_PHASE241_DONOR_SPECS.items():
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
            f"Local O_RDONLY donor audit exceeded {max_budget_seconds:.3f}s budget ({elapsed:.4f}s)."
        )

    fx3_ok = all(
        k in passed_keys
        for k, s in PINNED_PHASE241_DONOR_SPECS.items()
        if s[0] == "FX3"
    )
    fx6_ok = all(
        k in passed_keys
        for k, s in PINNED_PHASE241_DONOR_SPECS.items()
        if s[0] == "FX6"
    )
    valid = fx3_ok and fx6_ok and within_budget and (not errors)
    return Phase241DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_PHASE241_DONOR_INTEGRITY,
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="O_RDONLY",
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
# 2. Gate `G91`: `[Shoe Audio Set.]` `48kHz/24bit 4ch` Meter/Routing Guard &
#    `[Wind Noise Reduct.]` Built-In-Mic-Only Boundary
# ---------------------------------------------------------------------------


def resolve_fx3_shoe_audio_and_wind_noise_state(
    *,
    pre_reset_shoe_audio_set: str = SHOE_AUDIO_48K_24BIT_4CH,
    pre_reset_wind_noise_reduct: str = WIND_NOISE_REDUCT_OFF,
    reset_action: str = RESET_ACTION_NONE,
    shoot_mode: str = SHOOT_MODE_MOVIE_G91,
    audio_recording: str = "On",
    audio_level_display: str = "On",
    mishoe_accessory: str = MISHOE_ACCESSORY_XLR_H1_G91,
    xlrh1_digital_analog_switch: str = XLRH1_SWITCH_DIGITAL_G91,
    body_35mm_mic_jack_plugged: bool = False,
    indoor_low_wind_bench: bool = True,
) -> Dict[str, Any]:
    """Deterministically resolve `[Shoe Audio Set.]` (`48kHz/16bit 2ch` default,
    `24bit 2ch`, `24bit 4ch`, resettable via `[Camera Settings Reset]`), 4-channel
    `[Audio Level Display]` expansion, the 3 hardware lockout/override conditions,
    and `[Wind Noise Reduct.]` built-in-mic-only scope.
    """
    c_shoe = _norm_shoe_audio_set(pre_reset_shoe_audio_set)
    c_wind = _norm_on_off(pre_reset_wind_noise_reduct)
    c_rst = _norm_reset_action(reset_action)
    c_shoot = _norm_shoot_mode_g91(shoot_mode)
    c_arec = _norm_on_off(audio_recording)
    c_alvl = _norm_on_off(audio_level_display)
    c_acc = _norm_mishoe_accessory_g91(mishoe_accessory)
    c_sw = _norm_xlrh1_switch_g91(xlrh1_digital_analog_switch)

    if c_rst in (RESET_ACTION_CAMERA_SETTINGS_RESET, RESET_ACTION_INITIALIZE):
        exp_post_shoe = SHOE_AUDIO_SET_FACTORY_DEFAULT
        exp_post_wind = WIND_NOISE_REDUCT_FACTORY_DEFAULT
    else:
        exp_post_shoe = c_shoe or SHOE_AUDIO_SET_FACTORY_DEFAULT
        exp_post_wind = c_wind or WIND_NOISE_REDUCT_FACTORY_DEFAULT

    disq_audio_or_sq = (
        c_arec == "Off"
        or c_shoot in (SHOOT_MODE_SQ_MOTION_G91, SHOOT_MODE_STILL_G91)
    )
    disq_35mm = bool(body_35mm_mic_jack_plugged) and (not disq_audio_or_sq)
    disq_analog_shoe = (
        (not disq_audio_or_sq)
        and (not disq_35mm)
        and (
            (
                c_acc == MISHOE_ACCESSORY_XLR_H1_G91
                and c_sw == XLRH1_SWITCH_ANALOG_G91
            )
            or c_acc == MISHOE_ACCESSORY_ANALOG_MIC_G91
        )
    )

    disq_list: List[str] = []
    if c_arec == "Off" or c_shoot == SHOOT_MODE_SQ_MOTION_G91:
        disq_list.append("AUDIO_RECORDING_OFF_OR_SQ_MOTION")
    if bool(body_35mm_mic_jack_plugged):
        disq_list.append("BODY_35MM_MIC_JACK_PLUGIN_OVERRIDE")
    if (
        c_acc == MISHOE_ACCESSORY_XLR_H1_G91 and c_sw == XLRH1_SWITCH_ANALOG_G91
    ) or c_acc == MISHOE_ACCESSORY_ANALOG_MIC_G91:
        disq_list.append("XLR_H1_OR_MISHOE_ANALOG_SWITCH_FALLBACK")

    digital_shoe_active = (
        (not disq_audio_or_sq)
        and (not disq_35mm)
        and (not disq_analog_shoe)
        and c_acc in DIGITAL_2CH_MISHOE_ACCESSORIES_G91
        and (
            c_acc != MISHOE_ACCESSORY_XLR_H1_G91
            or c_sw == XLRH1_SWITCH_DIGITAL_G91
        )
    )
    digital_4ch_shoe_capable = (
        digital_shoe_active and c_acc in DIGITAL_4CH_MISHOE_ACCESSORIES_G91
    )

    if disq_audio_or_sq:
        input_src = AUDIO_INPUT_SOURCE_DISABLED_G91
        eff_fmt = "0ch_muted"
        rec_ch = 0
        shoe_avail = False
    elif disq_35mm:
        input_src = AUDIO_INPUT_SOURCE_BODY_35MM_ANALOG_G91
        eff_fmt = SHOE_AUDIO_48K_16BIT_2CH
        rec_ch = 2
        shoe_avail = False
    elif disq_analog_shoe:
        input_src = AUDIO_INPUT_SOURCE_MISHOE_ANALOG_2CH_G91
        eff_fmt = SHOE_AUDIO_48K_16BIT_2CH
        rec_ch = 2
        shoe_avail = False
    elif digital_shoe_active:
        input_src = AUDIO_INPUT_SOURCE_MISHOE_DIGITAL_G91
        shoe_avail = True
        if exp_post_shoe == SHOE_AUDIO_48K_24BIT_4CH:
            if digital_4ch_shoe_capable:
                eff_fmt = SHOE_AUDIO_48K_24BIT_4CH
                rec_ch = 4
            else:
                eff_fmt = SHOE_AUDIO_48K_24BIT_2CH
                rec_ch = 2
        else:
            eff_fmt = exp_post_shoe
            rec_ch = 2
    else:
        input_src = AUDIO_INPUT_SOURCE_BUILTIN_STEREO_MIC_G91
        eff_fmt = SHOE_AUDIO_48K_16BIT_2CH
        rec_ch = 2
        shoe_avail = False

    meter_ch = rec_ch if (c_alvl == "On" and rec_ch > 0) else 0
    meter_4ch_expanded = meter_ch == 4

    wind_avail = not disq_audio_or_sq
    builtin_wind_eff = (
        wind_avail
        and input_src == AUDIO_INPUT_SOURCE_BUILTIN_STEREO_MIC_G91
        and exp_post_wind == WIND_NOISE_REDUCT_ON
    )
    indoor_attenuation_violation = bool(indoor_low_wind_bench) and builtin_wind_eff

    return {
        "canonical_pre_shoe_audio_set": c_shoe,
        "canonical_pre_wind_noise_reduct": c_wind,
        "canonical_reset_action": c_rst,
        "canonical_shoot_mode": c_shoot,
        "canonical_audio_recording": c_arec,
        "canonical_audio_level_display": c_alvl,
        "canonical_mishoe_accessory": c_acc,
        "canonical_xlrh1_switch": c_sw,
        "expected_post_shoe_audio_set": exp_post_shoe,
        "expected_post_wind_noise_reduct": exp_post_wind,
        "disqualified_by_audio_off_or_sq": (
            c_arec == "Off" or c_shoot == SHOOT_MODE_SQ_MOTION_G91
        ),
        "disqualified_by_35mm_jack_override": bool(body_35mm_mic_jack_plugged),
        "disqualified_by_analog_shoe_switch": (
            (c_acc == MISHOE_ACCESSORY_XLR_H1_G91 and c_sw == XLRH1_SWITCH_ANALOG_G91)
            or c_acc == MISHOE_ACCESSORY_ANALOG_MIC_G91
        ),
        "active_disqualifying_conditions": tuple(disq_list),
        "digital_4ch_shoe_capable": digital_4ch_shoe_capable,
        "shoe_audio_set_available": shoe_avail,
        "active_audio_input_source": input_src,
        "expected_effective_audio_format": eff_fmt,
        "expected_recorded_audio_channels": rec_ch,
        "expected_audio_level_meter_channels": meter_ch,
        "four_ch_audio_level_meter_expanded": meter_4ch_expanded,
        "wind_noise_reduct_available": wind_avail,
        "builtin_mic_wind_reduct_effective": builtin_wind_eff,
        "external_mic_wind_reduct_effective": False,
        "indoor_low_wind_attenuation_violation": indoor_attenuation_violation,
    }


def verify_shoe_audio_4ch_and_wind_noise_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: int = FX3_MODEL_ID,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE241,
    pre_reset_shoe_audio_set: str = SHOE_AUDIO_48K_24BIT_4CH,
    pre_reset_wind_noise_reduct: str = WIND_NOISE_REDUCT_OFF,
    reset_action: str = RESET_ACTION_NONE,
    observed_post_reset_shoe_audio_set: Optional[str] = None,
    observed_post_reset_wind_noise_reduct: Optional[str] = None,
    claimed_shoe_audio_factory_default: str = SHOE_AUDIO_SET_FACTORY_DEFAULT,
    claimed_wind_noise_factory_default: str = WIND_NOISE_REDUCT_FACTORY_DEFAULT,
    shoot_mode: str = SHOOT_MODE_MOVIE_G91,
    audio_recording: str = "On",
    audio_level_display: str = "On",
    mishoe_accessory: str = MISHOE_ACCESSORY_XLR_H1_G91,
    xlrh1_digital_analog_switch: str = XLRH1_SWITCH_DIGITAL_G91,
    xlrh1_low_cut_switch: str = "Off",
    body_35mm_mic_jack_plugged: bool = False,
    observed_shoe_audio_set_available: Optional[bool] = None,
    observed_effective_audio_format: Optional[str] = None,
    observed_recorded_audio_channels: Optional[int] = None,
    observed_audio_level_meter_channels: Optional[int] = None,
    observed_wind_noise_reduct_available: Optional[bool] = None,
    observed_builtin_mic_wind_reduct_effective: Optional[bool] = None,
    observed_external_mic_wind_reduct_effective: bool = False,
    indoor_low_wind_bench: bool = True,
) -> ShoeAudio4chAndWindNoiseGuardResult:
    """Verify Gate `G91` invariants across `[Shoe Audio Set.]` (`48kHz/16bit 2ch`
    default, `24bit 2ch`, `24bit 4ch`), automatic `4ch` `[Audio Level Display]`
    meter expansion, the 3 hardware lockout/override rules (`[Audio Recording]=Off`
    or `S&Q Motion`, `3.5mm` `MIC` jack plug-in priority, and `XLR-H1` `ANALOG`
    slide switch), and `[Wind Noise Reduct.]` built-in-mic-only boundary.
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    fw_tuple = _parse_fw_tuple(firmware_version)
    if (
        body_model_name.strip().upper() != FX3_MODEL_NAME
        or int(body_model_id) != FX3_MODEL_ID
    ):
        _add_code(codes, STATUS_BLOCKED_G91_TELEMETRY_INVALID)
        errors.append(
            f"Gate G91 requires ILME-FX3 (0x{FX3_MODEL_ID:08X}); got {body_model_name!r} (0x{int(body_model_id):08X})."
        )
    if fw_tuple is None or fw_tuple < FX3_MIN_SUPPORTED_FW_TUPLE_PHASE241:
        _add_code(codes, STATUS_BLOCKED_G91_TELEMETRY_INVALID)
        errors.append(
            f"Gate G91 requires valid ILME-FX3 firmware version (>= 1.00); got {firmware_version!r}."
        )

    c_low_cut = _norm_low_cut_g91(xlrh1_low_cut_switch)
    if c_low_cut is None:
        _add_code(codes, STATUS_BLOCKED_G91_TELEMETRY_INVALID)
        errors.append(
            f"Invalid xlrh1_low_cut_switch={xlrh1_low_cut_switch!r}; expected {XLRH1_HARDWARE_LOW_CUT_MODES_G91}."
        )

    for label, val in (
        ("observed_recorded_audio_channels", observed_recorded_audio_channels),
        ("observed_audio_level_meter_channels", observed_audio_level_meter_channels),
    ):
        if val is not None and (
            isinstance(val, bool) or not isinstance(val, int) or val < 0
        ):
            _add_code(codes, STATUS_BLOCKED_G91_TELEMETRY_INVALID)
            errors.append(f"Invalid {label}={val!r}; expected non-negative int.")

    st = resolve_fx3_shoe_audio_and_wind_noise_state(
        pre_reset_shoe_audio_set=pre_reset_shoe_audio_set,
        pre_reset_wind_noise_reduct=pre_reset_wind_noise_reduct,
        reset_action=reset_action,
        shoot_mode=shoot_mode,
        audio_recording=audio_recording,
        audio_level_display=audio_level_display,
        mishoe_accessory=mishoe_accessory,
        xlrh1_digital_analog_switch=xlrh1_digital_analog_switch,
        body_35mm_mic_jack_plugged=body_35mm_mic_jack_plugged,
        indoor_low_wind_bench=indoor_low_wind_bench,
    )

    c_shoe = st["canonical_pre_shoe_audio_set"]
    c_wind = st["canonical_pre_wind_noise_reduct"]
    c_rst = st["canonical_reset_action"]
    c_shoot = st["canonical_shoot_mode"]
    c_arec = st["canonical_audio_recording"]
    c_alvl = st["canonical_audio_level_display"]
    c_acc = st["canonical_mishoe_accessory"]
    c_sw = st["canonical_xlrh1_switch"]

    if c_rst is None:
        _add_code(codes, STATUS_BLOCKED_G91_TELEMETRY_INVALID)
        errors.append(
            f"Invalid reset_action={reset_action!r}; expected {ALLOWED_RESET_ACTIONS_PHASE241}."
        )
    if c_shoot is None:
        _add_code(codes, STATUS_BLOCKED_G91_TELEMETRY_INVALID)
        errors.append(
            f"Invalid shoot_mode={shoot_mode!r}; expected {ALLOWED_SHOOT_MODES_G91}."
        )
    if c_arec is None:
        _add_code(codes, STATUS_BLOCKED_G91_TELEMETRY_INVALID)
        errors.append(f"Invalid audio_recording={audio_recording!r}; expected ('On', 'Off').")
    if c_alvl is None:
        _add_code(codes, STATUS_BLOCKED_G91_TELEMETRY_INVALID)
        errors.append(
            f"Invalid audio_level_display={audio_level_display!r}; expected ('On', 'Off')."
        )
    if c_acc is None:
        _add_code(codes, STATUS_BLOCKED_G91_TELEMETRY_INVALID)
        errors.append(
            f"Invalid mishoe_accessory={mishoe_accessory!r}; expected {ALLOWED_MISHOE_AUDIO_ACCESSORIES_G91}."
        )
    if c_sw is None:
        _add_code(codes, STATUS_BLOCKED_G91_TELEMETRY_INVALID)
        errors.append(
            f"Invalid xlrh1_digital_analog_switch={xlrh1_digital_analog_switch!r}; expected {ALLOWED_XLRH1_SWITCH_MODES_G91}."
        )

    # 1. [Shoe Audio Set.] Enum & Reset Validation
    shoe_reset_ok = True
    if _norm_shoe_audio_set(claimed_shoe_audio_factory_default) != SHOE_AUDIO_SET_FACTORY_DEFAULT:
        shoe_reset_ok = False
        _add_code(codes, STATUS_BLOCKED_G91_SHOE_AUDIO_SET_ENUM_OR_RESET_VIOLATION)
        errors.append(
            f"[Shoe Audio Set.] factory default is {SHOE_AUDIO_SET_FACTORY_DEFAULT!r}; "
            f"got {claimed_shoe_audio_factory_default!r}."
        )
    if c_shoe is None:
        shoe_reset_ok = False
        _add_code(codes, STATUS_BLOCKED_G91_SHOE_AUDIO_SET_ENUM_OR_RESET_VIOLATION)
        errors.append(
            f"Invalid [Shoe Audio Set.]={pre_reset_shoe_audio_set!r}; expected {ALLOWED_SHOE_AUDIO_SET_MODES}."
        )

    exp_post_shoe = st["expected_post_shoe_audio_set"]
    if observed_post_reset_shoe_audio_set is None:
        eff_post_shoe = exp_post_shoe
    else:
        n_obs_shoe = _norm_shoe_audio_set(observed_post_reset_shoe_audio_set)
        eff_post_shoe = (
            n_obs_shoe if n_obs_shoe is not None else observed_post_reset_shoe_audio_set
        )
        if n_obs_shoe is None or eff_post_shoe != exp_post_shoe:
            shoe_reset_ok = False
            _add_code(codes, STATUS_BLOCKED_G91_SHOE_AUDIO_SET_ENUM_OR_RESET_VIOLATION)
            errors.append(
                f"[Shoe Audio Set.] post-reset mismatch under {c_rst!r}: "
                f"got {eff_post_shoe!r}, expected {exp_post_shoe!r}."
            )

    # 2. [Wind Noise Reduct.] Enum & Reset Validation
    wind_reset_ok = True
    if _norm_on_off(claimed_wind_noise_factory_default) != WIND_NOISE_REDUCT_FACTORY_DEFAULT:
        wind_reset_ok = False
        _add_code(codes, STATUS_BLOCKED_G91_WIND_NOISE_REDUCT_ENUM_OR_RESET_VIOLATION)
        errors.append(
            f"[Wind Noise Reduct.] factory default is {WIND_NOISE_REDUCT_FACTORY_DEFAULT!r}; "
            f"got {claimed_wind_noise_factory_default!r}."
        )
    if c_wind is None:
        wind_reset_ok = False
        _add_code(codes, STATUS_BLOCKED_G91_WIND_NOISE_REDUCT_ENUM_OR_RESET_VIOLATION)
        errors.append(
            f"Invalid [Wind Noise Reduct.]={pre_reset_wind_noise_reduct!r}; expected {ALLOWED_WIND_NOISE_REDUCT_MODES}."
        )

    exp_post_wind = st["expected_post_wind_noise_reduct"]
    if observed_post_reset_wind_noise_reduct is None:
        eff_post_wind = exp_post_wind
    else:
        n_obs_wind = _norm_on_off(observed_post_reset_wind_noise_reduct)
        eff_post_wind = (
            n_obs_wind if n_obs_wind is not None else observed_post_reset_wind_noise_reduct
        )
        if n_obs_wind is None or eff_post_wind != exp_post_wind:
            wind_reset_ok = False
            _add_code(codes, STATUS_BLOCKED_G91_WIND_NOISE_REDUCT_ENUM_OR_RESET_VIOLATION)
            errors.append(
                f"[Wind Noise Reduct.] post-reset mismatch under {c_rst!r}: "
                f"got {eff_post_wind!r}, expected {exp_post_wind!r}."
            )

    # 3. 4ch Routing, 3 Hardware Lockouts & [Audio Level Display] Expansion
    exp_shoe_avail = bool(st["shoe_audio_set_available"])
    exp_fmt = str(st["expected_effective_audio_format"])
    exp_rec_ch = int(st["expected_recorded_audio_channels"])
    exp_meter_ch = int(st["expected_audio_level_meter_channels"])

    eff_shoe_avail = (
        exp_shoe_avail
        if observed_shoe_audio_set_available is None
        else bool(observed_shoe_audio_set_available)
    )
    if observed_effective_audio_format is None:
        eff_fmt = exp_fmt
    else:
        n_ef = _norm_shoe_audio_set(observed_effective_audio_format)
        eff_fmt = (
            n_ef
            if n_ef is not None
            else observed_effective_audio_format.strip()
        )
    eff_rec_ch = (
        exp_rec_ch
        if observed_recorded_audio_channels is None
        else int(observed_recorded_audio_channels)
    )
    eff_meter_ch = (
        exp_meter_ch
        if observed_audio_level_meter_channels is None
        else int(observed_audio_level_meter_channels)
    )

    if (
        eff_shoe_avail != exp_shoe_avail
        or eff_fmt != exp_fmt
        or eff_rec_ch != exp_rec_ch
        or (
            c_acc == MISHOE_ACCESSORY_ECM_B1M_G91
            and eff_post_shoe == SHOE_AUDIO_48K_24BIT_4CH
            and c_rst == RESET_ACTION_NONE
            and not st["active_disqualifying_conditions"]
        )
    ):
        _add_code(codes, STATUS_BLOCKED_G91_FOUR_CH_LOCKOUT_OR_ROUTING_OVERRIDE_VIOLATION)
        errors.append(
            "Shoe Audio 4ch routing / hardware lockout mismatch: "
            f"shoe_avail={eff_shoe_avail} (exp {exp_shoe_avail}), "
            f"format={eff_fmt!r} (exp {exp_fmt!r}), "
            f"rec_ch={eff_rec_ch} (exp {exp_rec_ch}), "
            f"accessory={c_acc!r}, disq={st['active_disqualifying_conditions']}."
        )

    if eff_meter_ch != exp_meter_ch:
        _add_code(codes, STATUS_BLOCKED_G91_AUDIO_LEVEL_METER_EXPANSION_MISMATCH)
        errors.append(
            f"[Audio Level Display] meter channel mismatch: got {eff_meter_ch}ch, "
            f"expected {exp_meter_ch}ch (4ch CH1..CH4 meter expansion active={exp_meter_ch == 4})."
        )

    # 4. [Wind Noise Reduct.] Built-In-Mic-Only Scope, S&Q Lockout & Indoor Bench Guard
    exp_wind_avail = bool(st["wind_noise_reduct_available"])
    exp_builtin_wind = bool(st["builtin_mic_wind_reduct_effective"])
    eff_wind_avail = (
        exp_wind_avail
        if observed_wind_noise_reduct_available is None
        else bool(observed_wind_noise_reduct_available)
    )
    eff_builtin_wind = (
        exp_builtin_wind
        if observed_builtin_mic_wind_reduct_effective is None
        else bool(observed_builtin_mic_wind_reduct_effective)
    )
    eff_ext_wind = bool(observed_external_mic_wind_reduct_effective)

    if eff_ext_wind:
        _add_code(codes, STATUS_BLOCKED_G91_EXTERNAL_MIC_WIND_NOISE_REDUCT_FALSE_CLAIM)
        errors.append(
            "[Wind Noise Reduct.] applies exclusively to the built-in stereo microphone; "
            "external microphones (3.5mm MIC jack and MI Shoe XLR-H1/ECM-M1) never receive "
            "body [Wind Noise Reduct.] filtering (use physical XLR-H1 LOW CUT Off/100Hz/300Hz)."
        )
    if eff_wind_avail != exp_wind_avail or eff_builtin_wind != exp_builtin_wind:
        _add_code(codes, STATUS_BLOCKED_G91_WIND_NOISE_REDUCT_ENUM_OR_RESET_VIOLATION)
        errors.append(
            f"[Wind Noise Reduct.] availability/effect mismatch: avail={eff_wind_avail} "
            f"(exp {exp_wind_avail}), builtin_effective={eff_builtin_wind} (exp {exp_builtin_wind})."
        )

    indoor_attenuation_blocked = True
    if bool(indoor_low_wind_bench) and eff_post_wind == WIND_NOISE_REDUCT_ON:
        if st["active_audio_input_source"] == AUDIO_INPUT_SOURCE_BUILTIN_STEREO_MIC_G91 and exp_wind_avail:
            indoor_attenuation_blocked = False
            _add_code(codes, STATUS_BLOCKED_G91_INDOOR_LOW_WIND_BENCH_ATTENUATION_HAZARD)
            errors.append(
                "[Wind Noise Reduct.]=On on indoor low-wind bench with built-in stereo mic "
                "attenuates normal low-frequency audio volume and alters timbre; set to Off."
            )
        elif exp_wind_avail:
            warnings.append(
                "[Wind Noise Reduct.]=On has no effect while external mic is active, but will "
                "attenuate low-frequency audio on indoor bench if external mic is detached."
            )

    shoe_reset_by_cam_rst = (
        c_rst in (RESET_ACTION_CAMERA_SETTINGS_RESET, RESET_ACTION_INITIALIZE)
        and shoe_reset_ok
    )
    wind_reset_by_cam_rst = (
        c_rst in (RESET_ACTION_CAMERA_SETTINGS_RESET, RESET_ACTION_INITIALIZE)
        and wind_reset_ok
    )

    valid = not codes
    status = STATUS_VERIFIED_G91 if valid else codes[0]
    return ShoeAudio4chAndWindNoiseGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=body_model_name,
        body_model_id_hex=f"0x{int(body_model_id):08X}",
        firmware_version=firmware_version,
        shoe_audio_set_menu_path=SHOE_AUDIO_SET_MENU_PATH,
        wind_noise_reduct_menu_path=WIND_NOISE_REDUCT_MENU_PATH,
        audio_level_display_menu_path=AUDIO_LEVEL_DISPLAY_MENU_PATH,
        pre_reset_shoe_audio_set=c_shoe or pre_reset_shoe_audio_set,
        pre_reset_wind_noise_reduct=c_wind or pre_reset_wind_noise_reduct,
        reset_action=c_rst or reset_action,
        expected_post_reset_shoe_audio_set=exp_post_shoe,
        effective_post_reset_shoe_audio_set=eff_post_shoe,
        shoe_audio_set_reset_by_camera_settings_reset=shoe_reset_by_cam_rst,
        expected_post_reset_wind_noise_reduct=exp_post_wind,
        effective_post_reset_wind_noise_reduct=eff_post_wind,
        wind_noise_reduct_reset_by_camera_settings_reset=wind_reset_by_cam_rst,
        shoot_mode=c_shoot or shoot_mode,
        audio_recording=c_arec or audio_recording,
        audio_level_display=c_alvl or audio_level_display,
        mishoe_accessory=c_acc or mishoe_accessory,
        xlrh1_digital_analog_switch=c_sw or xlrh1_digital_analog_switch,
        xlrh1_low_cut_switch=c_low_cut or xlrh1_low_cut_switch,
        body_35mm_mic_jack_plugged=bool(body_35mm_mic_jack_plugged),
        disqualified_by_audio_off_or_sq=bool(st["disqualified_by_audio_off_or_sq"]),
        disqualified_by_35mm_jack_override=bool(st["disqualified_by_35mm_jack_override"]),
        disqualified_by_analog_shoe_switch=bool(st["disqualified_by_analog_shoe_switch"]),
        active_disqualifying_conditions=st["active_disqualifying_conditions"],
        shoe_audio_set_available=eff_shoe_avail,
        active_audio_input_source=str(st["active_audio_input_source"]),
        expected_effective_audio_format=exp_fmt,
        effective_audio_format=eff_fmt,
        expected_recorded_audio_channels=exp_rec_ch,
        effective_recorded_audio_channels=eff_rec_ch,
        expected_audio_level_meter_channels=exp_meter_ch,
        audio_level_meter_channels=eff_meter_ch,
        four_ch_audio_level_meter_expanded=eff_meter_ch == 4,
        wind_noise_reduct_available=eff_wind_avail,
        builtin_mic_wind_reduct_effective=eff_builtin_wind,
        external_mic_wind_reduct_effective=eff_ext_wind,
        indoor_low_wind_bench=bool(indoor_low_wind_bench),
        indoor_low_wind_attenuation_blocked=indoor_attenuation_blocked,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g91_shoe_audio_and_wind_noise_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    shoe_audio_wind_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase241DonorAuditResult] = None,
) -> Tuple[GateVerdict, G91ShoeAudioAndWindNoiseGuardResult]:
    """Evaluate Gate `G91` combining bounded `<0.10s` donor check with
    `[Shoe Audio Set.]` `48kHz/24bit 4ch` meter/routing guard & `[Wind Noise Reduct.]`
    built-in-mic-only boundary.
    """
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase241_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_shoe_audio_4ch_and_wind_noise_guard(
        **dict(shoe_audio_wind_kwargs or {})
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
        errors.append("Gate G91 blocked persistent eMMC write authorization request.")

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G91 if valid else codes[0]

    res = G91ShoeAudioAndWindNoiseGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        shoe_audio_wind_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, shoe_audio={guard.effective_post_reset_shoe_audio_set}"
        f"->{guard.effective_audio_format}(rec={guard.effective_recorded_audio_channels}ch,"
        f"meter={guard.audio_level_meter_channels}ch,acc={guard.mishoe_accessory}/{guard.xlrh1_digital_analog_switch}), "
        f"wind={guard.effective_post_reset_wind_noise_reduct}(ext_eff={guard.external_mic_wind_reduct_effective})"
    )
    verdict = GateVerdict(
        gate_id=G91_GATE_ID,
        gate_code=G91_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 3. Gate `G92`: `[Save/Load Settings]` `CAMSET01..10.DAT` / `C3 Portal`
#    Excluded-Items Privacy/Calibration Firewall & Slot-1 Tier-0 Vault Guard
# ---------------------------------------------------------------------------


def _norm_saveload_op(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = raw.strip().strip("[]").upper()
    if s in ("NONE", "IDLE", ""):
        return SAVELOAD_OP_NONE
    if s in ("LOAD", "IMPORT"):
        return SAVELOAD_OP_LOAD
    if s in ("SAVE", "EXPORT"):
        return SAVELOAD_OP_SAVE
    return None


def _norm_saveload_target(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    if s in ("MEDIA(SLOT 1)", "MEDIA (SLOT 1)", "MEDIA_SLOT_1", "SLOT 1", "SLOT_1"):
        return SAVELOAD_TARGET_MEDIA_SLOT_1
    if s in (
        "MEDIA(SLOT 2)",
        "MEDIA (SLOT 2)",
        "MEDIA_SLOT_2",
        "SLOT 2",
        "SLOT_2",
        "MEDIA",
    ):
        return SAVELOAD_TARGET_MEDIA_SLOT_2
    if s in ("CLOUD(PRIVATE)", "CLOUD (PRIVATE)", "CLOUD_PRIVATE", "C3_PRIVATE"):
        return SAVELOAD_TARGET_CLOUD_PRIVATE
    if s in ("CLOUD(SHARE)", "CLOUD (SHARE)", "CLOUD_SHARE", "C3_SHARE"):
        return SAVELOAD_TARGET_CLOUD_SHARE
    return None


def _norm_camset_filename(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = raw.strip().upper()
    return s if s in SAVELOAD_ALLOWED_CAMSET_FILENAMES else None


def classify_saveload_excluded_items(
    items: Sequence[str],
) -> Dict[str, Tuple[str, ...]]:
    """Classify any items in `items` that fall under Sony's 5 excluded
    `[Save/Load Settings]` privacy, calibration, or network-credential categories.
    """
    matched_by_cat: Dict[str, List[str]] = {
        cat: [] for cat in SAVELOAD_EXCLUDED_ITEM_CATEGORIES
    }
    for raw_item in items:
        if not isinstance(raw_item, str):
            continue
        norm = re.sub(r"\s+", " ", raw_item.strip().strip("[]")).upper()
        if not norm:
            continue
        for cat, tokens in SAVELOAD_EXCLUDED_ITEM_TOKENS.items():
            if any(tok in norm for tok in tokens):
                if raw_item not in matched_by_cat[cat]:
                    matched_by_cat[cat].append(raw_item)
    return {
        cat: tuple(vals)
        for cat, vals in matched_by_cat.items()
        if vals
    }


def resolve_fx3_saveload_c3_and_slot1_vault_state(
    *,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE241,
    saveload_operation: str = SAVELOAD_OP_LOAD,
    saveload_target: str = SAVELOAD_TARGET_MEDIA_SLOT_1,
    camset_filename: str = "CAMSET01.DAT",
    card_camset_file_count: int = 1,
    profile_model_header: str = FX3_MODEL_NAME,
    slot1_tier0_vault_active: bool = True,
    slot1_present_artifacts: Sequence[str] = TIER0_VAULT_GUARDED_ARTIFACTS_G92,
    slot1_off_camera_sha256_verified: bool = False,
    slot1_sdxc_wp_locked: bool = False,
) -> Dict[str, Any]:
    """Deterministically resolve `[Save/Load Settings]` target routing (`Media`
    `CAMSET01..10.DAT` vs `Cloud(Private)` / `Cloud(Share)` `C3 Portal` `Ver. 4.00+`),
    same-model `ILME-FX3` lock, and Slot-1 Tier-0 forensic card write protection.
    """
    fw_tuple = _parse_fw_tuple(firmware_version)
    c_op = _norm_saveload_op(saveload_operation)
    c_tgt = _norm_saveload_target(saveload_target)
    c_fname = _norm_camset_filename(camset_filename)
    c_hdr = profile_model_header.strip().upper() if isinstance(profile_model_header, str) else ""

    is_media = c_tgt in SAVELOAD_MEDIA_TARGETS
    is_cloud = c_tgt in SAVELOAD_CLOUD_C3_TARGETS
    c3_fw_ok = fw_tuple is not None and fw_tuple >= SAVELOAD_CLOUD_C3_MIN_FW_TUPLE

    norm_artifacts = tuple(
        str(a).strip() for a in slot1_present_artifacts if str(a).strip()
    )
    guarded_lower = {g.lower() for g in TIER0_VAULT_GUARDED_ARTIFACTS_G92}
    has_guarded = any(
        any(g in a.lower() for g in guarded_lower) for a in norm_artifacts
    )

    # Unverified OR non-WP-locked OR guarded-artifact Slot-1 Tier-0 vault card
    # blocks [Save] targeting Media(Slot 1), while [Load] stays O_RDONLY safe.
    slot1_unverified_save_blocked = bool(
        slot1_tier0_vault_active or has_guarded
    ) and (
        (not bool(slot1_off_camera_sha256_verified))
        or (not bool(slot1_sdxc_wp_locked))
        or has_guarded
    )

    camset_path = (
        f"{SAVELOAD_FX3_CAMSET_CARD_DIR}/{c_fname or str(camset_filename).strip()}"
        if is_media
        else f"c3portal://{c_tgt or saveload_target}/{c_hdr or 'UNKNOWN'}"
    )

    return {
        "fw_tuple": fw_tuple,
        "canonical_op": c_op,
        "canonical_target": c_tgt,
        "canonical_camset_filename": c_fname,
        "canonical_profile_header": c_hdr,
        "is_media_target": is_media,
        "is_cloud_c3_target": is_cloud,
        "c3_portal_firmware_floor_met": c3_fw_ok,
        "same_model_ilme_fx3_locked": c_hdr == FX3_MODEL_NAME,
        "camset_card_path": camset_path,
        "normalized_slot1_artifacts": norm_artifacts,
        "slot1_has_guarded_artifacts": has_guarded,
        "slot1_unverified_camset_save_blocked": slot1_unverified_save_blocked,
        "load_card_access_mode": "O_RDONLY",
    }


def verify_saveload_camset_c3_exclusions_and_slot1_vault_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: int = FX3_MODEL_ID,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE241,
    saveload_operation: str = SAVELOAD_OP_LOAD,
    saveload_target: str = SAVELOAD_TARGET_MEDIA_SLOT_1,
    camset_filename: str = "CAMSET01.DAT",
    card_camset_file_count: int = 1,
    profile_model_header: str = FX3_MODEL_NAME,
    claimed_saveload_is_stateful_reset_parameter: bool = False,
    exported_or_overwritten_items: Sequence[str] = (
        "Shoe Audio Set.",
        "Picture Profile",
        "Focus Area",
    ),
    iptc_info_exported_or_overwritten: bool = False,
    copyright_info_exported_or_overwritten: bool = False,
    custom_wb_1_to_3_exported_or_overwritten: bool = False,
    face_memory_exported_or_overwritten: bool = False,
    ftp_credentials_exported_or_overwritten: bool = False,
    streaming_rtmp_srt_keys_exported_or_overwritten: bool = False,
    wifi_ssid_passphrase_exported_or_overwritten: bool = False,
    static_ip_or_tls_cert_exported_or_overwritten: bool = False,
    observed_load_card_access_mode: str = "O_RDONLY",
    slot1_tier0_vault_active: bool = True,
    slot1_present_artifacts: Sequence[str] = TIER0_VAULT_GUARDED_ARTIFACTS_G92,
    slot1_off_camera_sha256_verified: bool = False,
    slot1_sdxc_wp_locked: bool = False,
    slot1_card_sector_writes: int = 0,
    observed_slot1_save_executed: Optional[bool] = None,
) -> SaveLoadCamsetC3ExclusionsAndSlot1VaultResult:
    """Verify Gate `G92` invariants across `[Save/Load Settings]` (`Media`
    `CAMSET01..10.DAT` up to `10`/card + `Cloud(Private)`/`Cloud(Share)` `C3 Portal`
    `Ver. 4.00+`), strict `ILME-FX3` same-model firewall, Sony Help Guide 5-category
    excluded-items privacy/calibration firewall, and Slot-1 Tier-0 vault write guard.
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    fw_tuple = _parse_fw_tuple(firmware_version)
    if (
        body_model_name.strip().upper() != FX3_MODEL_NAME
        or int(body_model_id) != FX3_MODEL_ID
    ):
        _add_code(codes, STATUS_BLOCKED_G92_TELEMETRY_INVALID)
        errors.append(
            f"Gate G92 requires ILME-FX3 (0x{FX3_MODEL_ID:08X}); got {body_model_name!r} (0x{int(body_model_id):08X})."
        )
    if fw_tuple is None or fw_tuple < FX3_MIN_SUPPORTED_FW_TUPLE_PHASE241:
        _add_code(codes, STATUS_BLOCKED_G92_TELEMETRY_INVALID)
        errors.append(
            f"Gate G92 requires valid ILME-FX3 firmware version (>= 1.00); got {firmware_version!r}."
        )

    if (
        isinstance(card_camset_file_count, bool)
        or not isinstance(card_camset_file_count, int)
        or card_camset_file_count < 0
    ):
        _add_code(codes, STATUS_BLOCKED_G92_TELEMETRY_INVALID)
        errors.append(
            f"Invalid card_camset_file_count={card_camset_file_count!r}; expected non-negative int."
        )
    if (
        isinstance(slot1_card_sector_writes, bool)
        or not isinstance(slot1_card_sector_writes, int)
        or slot1_card_sector_writes < 0
    ):
        _add_code(codes, STATUS_BLOCKED_G92_TELEMETRY_INVALID)
        errors.append(
            f"Invalid slot1_card_sector_writes={slot1_card_sector_writes!r}; expected non-negative int."
        )

    st = resolve_fx3_saveload_c3_and_slot1_vault_state(
        firmware_version=firmware_version,
        saveload_operation=saveload_operation,
        saveload_target=saveload_target,
        camset_filename=camset_filename,
        card_camset_file_count=card_camset_file_count
        if isinstance(card_camset_file_count, int)
        else 0,
        profile_model_header=profile_model_header,
        slot1_tier0_vault_active=slot1_tier0_vault_active,
        slot1_present_artifacts=slot1_present_artifacts,
        slot1_off_camera_sha256_verified=slot1_off_camera_sha256_verified,
        slot1_sdxc_wp_locked=slot1_sdxc_wp_locked,
    )

    c_op = st["canonical_op"]
    c_tgt = st["canonical_target"]
    c_fname = st["canonical_camset_filename"]
    c_hdr = st["canonical_profile_header"]
    is_media = bool(st["is_media_target"])
    is_cloud = bool(st["is_cloud_c3_target"])
    c3_fw_ok = bool(st["c3_portal_firmware_floor_met"])

    if c_op is None:
        _add_code(codes, STATUS_BLOCKED_G92_TELEMETRY_INVALID)
        errors.append(
            f"Invalid saveload_operation={saveload_operation!r}; expected {ALLOWED_SAVELOAD_OPERATIONS}."
        )
    if c_tgt is None:
        _add_code(codes, STATUS_BLOCKED_G92_SAVELOAD_TARGET_FILE_OR_COUNT_INVALID)
        errors.append(
            f"Invalid saveload_target={saveload_target!r}; expected {ALLOWED_SAVELOAD_TARGETS}."
        )
    if bool(claimed_saveload_is_stateful_reset_parameter):
        _add_code(codes, STATUS_BLOCKED_G92_TELEMETRY_INVALID)
        errors.append(
            "[Save/Load Settings] is an executable action item, not a stateful parameter reset by [Camera Settings Reset]."
        )

    # 1. Media CAMSET01..10.DAT (max 10/card) & Cloud(Private)/Cloud(Share) Ver. 4.00+ Floor
    if is_media:
        if c_fname is None:
            _add_code(codes, STATUS_BLOCKED_G92_SAVELOAD_TARGET_FILE_OR_COUNT_INVALID)
            errors.append(
                f"Invalid CAMSET filename={camset_filename!r}; expected CAMSET01.DAT..CAMSET10.DAT."
            )
        if (
            isinstance(card_camset_file_count, int)
            and not isinstance(card_camset_file_count, bool)
            and card_camset_file_count > SAVELOAD_MAX_CAMSET_FILES_PER_CARD
        ):
            _add_code(codes, STATUS_BLOCKED_G92_SAVELOAD_TARGET_FILE_OR_COUNT_INVALID)
            errors.append(
                f"Card CAMSET file count={card_camset_file_count} exceeds Sony ceiling ({SAVELOAD_MAX_CAMSET_FILES_PER_CARD})."
            )

    if is_cloud and not c3_fw_ok:
        _add_code(codes, STATUS_BLOCKED_G92_CLOUD_C3_FIRMWARE_FLOOR_VIOLATION)
        errors.append(
            f"[Save/Load Settings] {c_tgt!r} via Creators' Cloud / C3 Portal requires ILME-FX3 Ver. 4.00+; got {firmware_version!r}."
        )

    # 2. Strict ILME-FX3 Same-Model Firewall (rejecting ILME-FX6 / cross-model .DAT & cloud profiles)
    same_model_ok = c_hdr == FX3_MODEL_NAME
    if not same_model_ok:
        _add_code(codes, STATUS_BLOCKED_G92_CAMSET_OR_CLOUD_CROSS_MODEL_REJECTED)
        errors.append(
            f"[Save/Load Settings] rejected cross-model profile header {profile_model_header!r}; "
            f"strictly locked to {FX3_MODEL_NAME!r}."
        )

    # 3. Official Excluded-Items Privacy, Calibration & Network-Credentials Firewall
    classified_leaks = classify_saveload_excluded_items(exported_or_overwritten_items)
    net_flag_leak = any(
        (
            bool(ftp_credentials_exported_or_overwritten),
            bool(streaming_rtmp_srt_keys_exported_or_overwritten),
            bool(wifi_ssid_passphrase_exported_or_overwritten),
            bool(static_ip_or_tls_cert_exported_or_overwritten),
        )
    )
    iptc_leaked = (
        bool(iptc_info_exported_or_overwritten)
        or "IPTC Information" in classified_leaks
    )
    copyright_leaked = (
        bool(copyright_info_exported_or_overwritten)
        or "Copyright Info" in classified_leaks
    )
    cwb_leaked = (
        bool(custom_wb_1_to_3_exported_or_overwritten)
        or "Custom White Balance (Custom 1..3)" in classified_leaks
    )
    face_leaked = (
        bool(face_memory_exported_or_overwritten)
        or "Face Memory" in classified_leaks
    )
    net_cat = (
        "Network Credentials (FTP / RTMP-SRT Streaming / Wi-Fi / Static IP / TLS Certs)"
    )
    net_leaked = net_flag_leak or (net_cat in classified_leaks)

    leaked_cats: List[str] = []
    if iptc_leaked:
        leaked_cats.append("IPTC Information")
    if copyright_leaked:
        leaked_cats.append("Copyright Info")
    if cwb_leaked:
        leaked_cats.append("Custom White Balance (Custom 1..3)")
    if face_leaked:
        leaked_cats.append("Face Memory")
    if net_leaked:
        leaked_cats.append(net_cat)

    leaked_item_count = sum(len(v) for v in classified_leaks.values()) + sum(
        1
        for flag in (
            iptc_info_exported_or_overwritten,
            copyright_info_exported_or_overwritten,
            custom_wb_1_to_3_exported_or_overwritten,
            face_memory_exported_or_overwritten,
            ftp_credentials_exported_or_overwritten,
            streaming_rtmp_srt_keys_exported_or_overwritten,
            wifi_ssid_passphrase_exported_or_overwritten,
            static_ip_or_tls_cert_exported_or_overwritten,
        )
        if flag
    )

    exclusions_ok = len(leaked_cats) == 0
    if not exclusions_ok:
        _add_code(
            codes,
            STATUS_BLOCKED_G92_EXCLUDED_PRIVACY_CALIBRATION_OR_CREDENTIAL_LEAK,
        )
        errors.append(
            "[Save/Load Settings] Excluded-Items Firewall blocked export/overwrite of machine-bound "
            f"or secret registers: categories={tuple(leaked_cats)}."
        )

    # 4. [Load] O_RDONLY Card Safety & Slot-1 Tier-0 Vault Write Firewall
    norm_access = (
        observed_load_card_access_mode.strip().upper()
        if isinstance(observed_load_card_access_mode, str)
        else ""
    )
    writes_int = (
        slot1_card_sector_writes
        if isinstance(slot1_card_sector_writes, int)
        and not isinstance(slot1_card_sector_writes, bool)
        else -1
    )
    load_rdonly_safe = norm_access == "O_RDONLY" and (
        c_op != SAVELOAD_OP_LOAD or writes_int == 0
    )
    if not load_rdonly_safe:
        _add_code(codes, STATUS_BLOCKED_G92_LOAD_CARD_NON_RDONLY_MUTATION)
        errors.append(
            f"[Save/Load Settings] [Load] must remain strictly O_RDONLY on card with 0 sector writes: "
            f"access_mode={observed_load_card_access_mode!r}, slot1_writes={slot1_card_sector_writes!r}."
        )

    slot1_save_blocked = bool(st["slot1_unverified_camset_save_blocked"])
    slot1_save_attempted = (
        c_op == SAVELOAD_OP_SAVE and c_tgt == SAVELOAD_TARGET_MEDIA_SLOT_1
    )
    slot1_vault_ok = True
    if slot1_save_blocked and (
        slot1_save_attempted
        or bool(observed_slot1_save_executed)
        or writes_int > 0
    ):
        slot1_vault_ok = False
        _add_code(codes, STATUS_BLOCKED_G92_SLOT1_TIER0_VAULT_CAMSET_SAVE_FORBIDDEN)
        errors.append(
            "Slot-1 Tier-0 Vault Write Firewall blocked [Save/Load Settings] -> [Save] targeting "
            f"Slot 1 forensic card (vault_active={slot1_tier0_vault_active}, "
            f"sha256_verified={slot1_off_camera_sha256_verified}, wp_locked={slot1_sdxc_wp_locked}, "
            f"artifacts={st['normalized_slot1_artifacts']}, writes={slot1_card_sector_writes})."
        )
    elif (
        bool(slot1_sdxc_wp_locked)
        and slot1_save_attempted
        and (bool(observed_slot1_save_executed) or writes_int > 0)
    ):
        slot1_vault_ok = False
        _add_code(codes, STATUS_BLOCKED_G92_SLOT1_TIER0_VAULT_CAMSET_SAVE_FORBIDDEN)
        errors.append(
            "Physical SDXC WP switch on Slot 1 prevents [Save] sector writes."
        )

    valid = not codes
    status = STATUS_VERIFIED_G92 if valid else codes[0]
    return SaveLoadCamsetC3ExclusionsAndSlot1VaultResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=body_model_name,
        body_model_id_hex=f"0x{int(body_model_id):08X}",
        firmware_version=firmware_version,
        saveload_menu_path=SAVE_LOAD_SETTINGS_MENU_PATH,
        saveload_operation=c_op or saveload_operation,
        saveload_target=c_tgt or saveload_target,
        is_media_target=is_media,
        is_cloud_c3_target=is_cloud,
        c3_portal_firmware_floor_met=c3_fw_ok,
        camset_filename=c_fname or str(camset_filename),
        camset_card_path=str(st["camset_card_path"]),
        card_camset_file_count=card_camset_file_count
        if isinstance(card_camset_file_count, int)
        and not isinstance(card_camset_file_count, bool)
        else -1,
        profile_model_header=c_hdr or str(profile_model_header),
        same_model_ilme_fx3_locked=same_model_ok,
        action_item_not_reset_parameter=not bool(
            claimed_saveload_is_stateful_reset_parameter
        ),
        excluded_categories_enforced=SAVELOAD_EXCLUDED_ITEM_CATEGORIES,
        leaked_excluded_categories=tuple(leaked_cats),
        excluded_items_leaked_count=leaked_item_count,
        iptc_info_excluded=not iptc_leaked,
        copyright_info_excluded=not copyright_leaked,
        custom_wb_1_to_3_excluded=not cwb_leaked,
        face_memory_excluded=not face_leaked,
        network_credentials_excluded=not net_leaked,
        excluded_items_firewall_enforced=exclusions_ok,
        load_card_access_mode=norm_access or str(observed_load_card_access_mode),
        load_is_card_o_rdonly_safe=load_rdonly_safe,
        slot1_tier0_vault_active=bool(slot1_tier0_vault_active),
        slot1_present_artifacts=st["normalized_slot1_artifacts"],
        slot1_off_camera_sha256_verified=bool(slot1_off_camera_sha256_verified),
        slot1_sdxc_wp_locked=bool(slot1_sdxc_wp_locked),
        slot1_unverified_camset_save_blocked=slot1_save_blocked,
        slot1_card_sector_writes=writes_int,
        slot1_vault_write_firewall_enforced=slot1_vault_ok and load_rdonly_safe,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g92_saveload_c3_exclusions_and_slot1_vault_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    saveload_c3_exclusions_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase241DonorAuditResult] = None,
) -> Tuple[GateVerdict, G92SaveLoadC3ExclusionsAndSlot1VaultGuardResult]:
    """Evaluate Gate `G92` combining bounded `<0.10s` donor check with
    `[Save/Load Settings]` `CAMSET01..10.DAT` / `C3 Portal` excluded-items
    firewall & Slot-1 Tier-0 vault write guard.
    """
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase241_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_saveload_camset_c3_exclusions_and_slot1_vault_guard(
        **dict(saveload_c3_exclusions_kwargs or {})
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
        errors.append("Gate G92 blocked persistent eMMC write authorization request.")

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G92 if valid else codes[0]

    res = G92SaveLoadC3ExclusionsAndSlot1VaultGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        saveload_c3_exclusions_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, op={guard.saveload_operation}@{guard.saveload_target}"
        f"({guard.camset_filename},hdr={guard.profile_model_header},"
        f"exclusions_ok={guard.excluded_items_firewall_enforced},"
        f"slot1_save_blocked={guard.slot1_unverified_camset_save_blocked})"
    )
    verdict = GateVerdict(
        gate_id=G92_GATE_ID,
        gate_code=G92_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 4. Unified `92`-Gate Master Safety Preflight (`G01..G92`)
# ---------------------------------------------------------------------------


def evaluate_92gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    dry_run_simulated_backup: Optional[bool] = None,
    simulate_bench_dry_run: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    request_persistent_emmc_writes: bool = False,
    shoe_audio_wind_kwargs: Optional[Mapping[str, Any]] = None,
    saveload_c3_exclusions_kwargs: Optional[Mapping[str, Any]] = None,
    master_90_override: Optional[Master90GateReport] = None,
    **m90_passthrough_kwargs: Any,
) -> Master92GateReport:
    """Evaluate all 92 Master Safety Gates (`G01..G92`) deterministically by
    delegating `G01..G90` directly to `evaluate_90gate_preflight()`.
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

    m90_report: Master90GateReport = (
        master_90_override
        if master_90_override is not None
        else evaluate_90gate_preflight(
            resolved_root,
            force_clean_room=clean_forced,
            dry_run_simulated=effective_dry_run,
            include_large_binaries=include_large_binaries,
            work_root=work_root,
            request_persistent_emmc_writes=request_persistent_emmc_writes,
            **m90_passthrough_kwargs,
        )
    )

    phase241_audit = audit_phase241_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
    )

    g91_verdict, g91_res = evaluate_g91_shoe_audio_and_wind_noise_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        shoe_audio_wind_kwargs=shoe_audio_wind_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase241_audit,
    )

    g92_verdict, g92_res = evaluate_g92_saveload_c3_exclusions_and_slot1_vault_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        saveload_c3_exclusions_kwargs=saveload_c3_exclusions_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase241_audit,
    )

    gates_91_to_92 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g91_verdict, g92_verdict)
    ]
    all_gates = tuple(list(m90_report.gates) + gates_91_to_92)

    g01_to_g12_verified = int(m90_report.summary["g01_to_g12_verified"])
    g13_to_g90_verified = (
        int(m90_report.summary["g13_to_g88_verified"])
        + int(m90_report.summary["g89_to_g90_verified"])
    )
    g91_to_g92_verified = sum(1 for v in (g91_verdict, g92_verdict) if v.passed)
    total_verified = g01_to_g12_verified + g13_to_g90_verified + g91_to_g92_verified

    g91_to_g92_all_passed = g91_to_g92_verified == 2
    g13_to_g92_all_passed = m90_report.g13_to_g90_all_passed and g91_to_g92_all_passed
    g01_to_g09_ok = all(bool(g["passed"]) for g in m90_report.gates[:9])

    offline_89_verified = (
        g01_to_g09_ok
        and m90_report.offline_87_gates_verified
        and g91_to_g92_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_92_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g92_all_passed
        and (not request_persistent_emmc_writes)
    )

    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m90_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_89_verified
        and m90_report.h0_h1_trial_entry_allowed
        and g91_to_g92_all_passed
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
        list(m90_report.errors) + list(g91_verdict.errors) + list(g92_verdict.errors)
    )
    warnings: List[str] = (
        list(m90_report.warnings)
        + list(g91_verdict.warnings)
        + list(g92_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m90_report.g13_to_g90_all_passed:
        overall_status = m90_report.status
    elif not g91_verdict.passed:
        overall_status = g91_verdict.status
    elif not g92_verdict.passed:
        overall_status = g92_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_92_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_92_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_92_verified:
        overall_status = "VERIFIED_ALL_92_GATES"
    else:
        overall_status = "VERIFIED_89_OF_92_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m90_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g91_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g92_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 92,
        "verified_gates": total_verified,
        "technical_gates_passed": total_verified,
        "blocked_or_pending_gates": 92 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g90_verified": g13_to_g90_verified,
        "g91_to_g92_verified": g91_to_g92_verified,
        "g13_to_g92_all_passed": g13_to_g92_all_passed,
        "g91_to_g92_all_passed": g91_to_g92_all_passed,
        "offline_89_gates_verified": offline_89_verified,
        "all_92_gates_verified": all_92_verified,
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

    return Master92GateReport(
        schema=REALHW_SHOE_AUDIO_WIND_SAVELOAD_C3_92GATE_SCHEMA,
        version=REALHW_SHOE_AUDIO_WIND_SAVELOAD_C3_92GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        offline_89_gates_verified=offline_89_verified,
        all_92_gates_verified=all_92_verified,
        g13_to_g92_all_passed=g13_to_g92_all_passed,
        g91_to_g92_all_passed=g91_to_g92_all_passed,
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
        master_90_report=m90_report.to_dict(),
        g91_result=g91_res.to_dict(),
        g92_result=g92_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_92_master_safety_gates = evaluate_92gate_preflight
run_92_gate_preflight = evaluate_92gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_shoe_audio_wind_saveload_c3_and_92gate_guard",
        description=(
            "Phase 241 Safety Gates G91 (Shoe Audio Set. 48kHz/24bit 4ch Meter/Routing "
            "Guard & Wind Noise Reduct. Built-In-Mic-Only Boundary) + G92 (Save/Load "
            "Settings CAMSET01..10.DAT / C3 Portal Excluded-Items Firewall & Slot-1 "
            "Tier-0 Vault Write Guard) + Unified 92-Gate Master Safety Preflight"
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

    report = evaluate_92gate_preflight(
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
            f"verified={report.summary['verified_gates']}/92 "
            f"g91_to_g92_all_passed={report.g91_to_g92_all_passed} "
            f"all_92_gates_verified={report.all_92_gates_verified} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
            f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
            f"usb_packets_transmitted={report.usb_packets_transmitted} "
            f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
        )
    ok = (
        report.all_92_gates_verified
        if args.dry_run_simulated
        else report.offline_89_gates_verified
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
