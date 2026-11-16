"""Phase 256 (`100/100` GRAND MILESTONE, Wave-40) Sony `ILME-FX3` (`Ver. 7.02`) Safety
Gates `G99` (`[Different Set for Still/Mv]` 8-Item Asymmetric State Transitions,
`Camera Settings Reset` + `Reset Network Set.` Survival & `Ver. 7.02` `[Shutter Mode]`
= `[Angle]` Common-Mode Independence Override Guard) & `G100` (`100th` Safety Gate:
`[Custom Key/Dial Set.]` 3-Domain Keymaps, Cinema-Line `Front dial=Aperture` /
`Rear dial=ISO/EI` / `Control Wheel=Shutter Speed` Auto-Adaptation, `[Follow Custom]`,
`[My Dial 1..3]`, Slot-1 Tier-0 `CAMSET01.DAT` `O_RDONLY` Load-Only Firewall &
`[Remain Shoot Display]` Still-Buffer Scope + EVF-Less `ILME-FX3` `ilc/2210` Topology
Guard) + Unified `100`-Gate Master Safety Preflight (`G01..G100`).

Operationalizes Wave-40 official Sony `ILME-FX3` (`Ver. 7.02`, Help Guide `ilc/2210`)
intelligence (`reports/2026-11-15-global-sony-wave40-milestone-diff-set-still-mv-8items-shutter-angle-custom-key-dial-remain-shoot-intel/README.md`)
as deterministic offline preflight verifiers (`G99` and `G100`) and delegates
`G01..G98` directly to `evaluate_98gate_preflight()`.
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
from .realhw_display_quality_bt_rmt_mymenu_and_98gate_guard import (
    Master98GateReport,
    evaluate_98gate_preflight,
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

REALHW_DIFF_SET_STILL_MV_CUSTOM_KEY_REMAIN_SHOOT_100GATE_SCHEMA: str = (
    "realhw_diff_set_still_mv_custom_key_remain_shoot_and_100gate_guard_v1"
)
REALHW_DIFF_SET_STILL_MV_CUSTOM_KEY_REMAIN_SHOOT_100GATE_VERSION: str = "1.0.0"

G99_GATE_ID: str = (
    "G99_diff_set_still_mv_8item_transitions_and_shutter_angle_override_guard"
)
G99_GATE_CODE: str = (
    "DIFF_SET_STILL_MV_8ITEM_TRANSITIONS_AND_SHUTTER_ANGLE_OVERRIDE_GUARD"
)

G100_GATE_ID: str = (
    "G100_custom_key_dial_iso_ei_firewall_and_remain_shoot_evf_less_guard"
)
G100_GATE_CODE: str = (
    "CUSTOM_KEY_DIAL_ISO_EI_FIREWALL_AND_REMAIN_SHOOT_EVF_LESS_GUARD"
)

G99: str = G99_GATE_ID
G100: str = G100_GATE_ID
GATE_G99_DIFF_SET_STILL_MV_8ITEM_TRANSITIONS_AND_SHUTTER_ANGLE_OVERRIDE_GUARD: str = (
    G99_GATE_CODE
)
GATE_G100_CUSTOM_KEY_DIAL_ISO_EI_FIREWALL_AND_REMAIN_SHOOT_EVF_LESS_GUARD: str = (
    G100_GATE_CODE
)

HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
HUMAN_HARDWARE_ATTACH_TOKEN: bool = False
USB_PACKETS_TRANSMITTED: int = 0
PHYSICAL_USB_PACKETS_EMITTED: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0
DONOR_CHECK_MAX_SECONDS_PHASE256: float = 0.10
DONOR_CHECK_MAX_SECONDS: float = DONOR_CHECK_MAX_SECONDS_PHASE256

FX3_MODEL_NAME: str = "ILME-FX3"
FX3_MODEL_ID: int = 0x91030080
FX6_MODEL_NAME: str = "ILME-FX6"
FX3_DEFAULT_FW_VERSION_PHASE256: str = "7.02"
FX3_MIN_SUPPORTED_FW_TUPLE_PHASE256: Tuple[int, int] = (1, 0)
FX3_SHUTTER_ANGLE_MIN_FW_TUPLE_G99: Tuple[int, int] = (6, 0)
FX3_HELP_GUIDE_CODE_PHASE256: str = "ilc/2210"
FX3_HAS_BUILTIN_EVF_G100: bool = False
FX3_ACTIVE_DISPLAY_SURFACE_LCD_G100: str = "VARI_ANGLE_LCD_MONITOR"

RESET_ACTION_NONE: str = "NONE"
RESET_ACTION_CAMERA_SETTINGS_RESET: str = "Camera Settings Reset"
RESET_ACTION_RESET_NETWORK_SET_PHASE256: str = "Reset Network Set."
RESET_ACTION_INITIALIZE: str = "Initialize"
ALLOWED_RESET_ACTIONS_PHASE256: Tuple[str, ...] = (
    RESET_ACTION_NONE,
    RESET_ACTION_CAMERA_SETTINGS_RESET,
    RESET_ACTION_RESET_NETWORK_SET_PHASE256,
    RESET_ACTION_INITIALIZE,
)

# Status & Violation Codes
STATUS_VERIFIED_G99: str = (
    "VERIFIED_G99_DIFF_SET_STILL_MV_8ITEM_TRANSITIONS_AND_SHUTTER_ANGLE_SAFE"
)
STATUS_VERIFIED_G100: str = (
    "VERIFIED_G100_CUSTOM_KEY_DIAL_ISO_EI_FIREWALL_AND_REMAIN_SHOOT_SAFE"
)
STATUS_BLOCKED_PHASE256_DONOR_INTEGRITY: str = (
    "BLOCKED_PHASE256_DONOR_CONTRACT_INTEGRITY"
)

STATUS_BLOCKED_G99_DIFF_SET_ITEM_CATALOG_OR_RESET_PERSISTENCE_VIOLATION: str = (
    "BLOCKED_G99_DIFF_SET_ITEM_CATALOG_OR_RESET_PERSISTENCE_VIOLATION"
)
STATUS_BLOCKED_G99_COMMON_TO_SEPARATE_CUSTOM_WB_STILL_ONLY_VIOLATION: str = (
    "BLOCKED_G99_COMMON_TO_SEPARATE_CUSTOM_WB_STILL_ONLY_VIOLATION"
)
STATUS_BLOCKED_G99_SEPARATE_TO_COMMON_ASYMMETRIC_RETENTION_VIOLATION: str = (
    "BLOCKED_G99_SEPARATE_TO_COMMON_ASYMMETRIC_RETENTION_VIOLATION"
)
STATUS_BLOCKED_G99_SHUTTER_ANGLE_COMMON_BLEED_VIOLATION: str = (
    "BLOCKED_G99_SHUTTER_ANGLE_COMMON_BLEED_VIOLATION"
)
STATUS_BLOCKED_G99_TELEMETRY_INVALID: str = (
    "BLOCKED_G99_DIFF_SET_STILL_MV_TELEMETRY_INVALID"
)

STATUS_BLOCKED_G100_CUSTOM_KEY_DIAL_DOMAIN_OR_ISO_EI_MISMATCH: str = (
    "BLOCKED_G100_CUSTOM_KEY_DIAL_DOMAIN_OR_ISO_EI_MISMATCH"
)
STATUS_BLOCKED_G100_CUSTOM_KEY_RESET_PERSISTENCE_VIOLATION: str = (
    "BLOCKED_G100_CUSTOM_KEY_RESET_PERSISTENCE_VIOLATION"
)
STATUS_BLOCKED_G100_SLOT1_CUSTOM_KEY_CAMSET01_FIREWALL_VIOLATION: str = (
    "BLOCKED_G100_SLOT1_CUSTOM_KEY_CAMSET01_FIREWALL_VIOLATION"
)
STATUS_BLOCKED_G100_REMAIN_SHOOT_SCOPE_OR_RESET_PERSISTENCE_VIOLATION: str = (
    "BLOCKED_G100_REMAIN_SHOOT_SCOPE_OR_RESET_PERSISTENCE_VIOLATION"
)
STATUS_BLOCKED_G100_EVF_FINDER_MONITOR_TOPOLOGY_SPOOF_VIOLATION: str = (
    "BLOCKED_G100_EVF_FINDER_MONITOR_TOPOLOGY_SPOOF_VIOLATION"
)
STATUS_BLOCKED_G100_TELEMETRY_INVALID: str = (
    "BLOCKED_G100_CUSTOM_KEY_REMAIN_SHOOT_TELEMETRY_INVALID"
)

# ---------------------------------------------------------------------------
# Gate G99 Domain Constants (`[Different Set for Still/Mv]` & `[Shutter Mode]`)
# ---------------------------------------------------------------------------

DIFF_SET_STILL_MV_MENU_PATH_G99: str = (
    "MENU -> Setup -> [Operation Customize] -> [Different Set for Still/Mv]"
)
DIFF_SET_ITEM_APERTURE_G99: str = "Aperture"
DIFF_SET_ITEM_SHUTTER_SPEED_G99: str = "Shutter Speed"
DIFF_SET_ITEM_ISO_G99: str = "ISO"
DIFF_SET_ITEM_EXPOSURE_COMP_G99: str = "Exposure Comp."
DIFF_SET_ITEM_METERING_MODE_G99: str = "Metering Mode"
DIFF_SET_ITEM_WHITE_BALANCE_G99: str = "White Balance"
DIFF_SET_ITEM_PICTURE_PROFILE_G99: str = "Picture Profile"
DIFF_SET_ITEM_FOCUS_MODE_G99: str = "Focus Mode"

DIFF_SET_STILL_MV_EIGHT_ITEMS_G99: Tuple[str, ...] = (
    DIFF_SET_ITEM_APERTURE_G99,
    DIFF_SET_ITEM_SHUTTER_SPEED_G99,
    DIFF_SET_ITEM_ISO_G99,
    DIFF_SET_ITEM_EXPOSURE_COMP_G99,
    DIFF_SET_ITEM_METERING_MODE_G99,
    DIFF_SET_ITEM_WHITE_BALANCE_G99,
    DIFF_SET_ITEM_PICTURE_PROFILE_G99,
    DIFF_SET_ITEM_FOCUS_MODE_G99,
)

DIFF_SET_FACTORY_CHECKED_ITEMS_G99: Tuple[str, ...] = ()

DIFF_SET_INITIAL_FACTORY_PARAM_DEFAULTS_G99: Dict[str, str] = {
    DIFF_SET_ITEM_APERTURE_G99: "F4.0",
    DIFF_SET_ITEM_SHUTTER_SPEED_G99: "1/125",
    DIFF_SET_ITEM_ISO_G99: "ISO AUTO",
    DIFF_SET_ITEM_EXPOSURE_COMP_G99: "0.0EV",
    DIFF_SET_ITEM_METERING_MODE_G99: "Multi",
    DIFF_SET_ITEM_WHITE_BALANCE_G99: "Auto",
    DIFF_SET_ITEM_PICTURE_PROFILE_G99: "Off",
    DIFF_SET_ITEM_FOCUS_MODE_G99: "AF-C",
}

DIFF_SET_SEPARATE_TO_COMMON_STILL_RETAINED_ITEMS_G99: Tuple[str, ...] = (
    DIFF_SET_ITEM_APERTURE_G99,
    DIFF_SET_ITEM_SHUTTER_SPEED_G99,
)

CUSTOM_WHITE_BALANCE_VALUES_G99: Tuple[str, ...] = (
    "Custom White Balance",
    "Custom 1",
    "Custom 2",
    "Custom 3",
)

DIFF_SET_TRANSITION_NONE_G99: str = "NONE"
DIFF_SET_TRANSITION_COMMON_TO_SEPARATE_G99: str = "COMMON_TO_SEPARATE"
DIFF_SET_TRANSITION_SEPARATE_TO_COMMON_G99: str = "SEPARATE_TO_COMMON"
ALLOWED_DIFF_SET_TRANSITIONS_G99: Tuple[str, ...] = (
    DIFF_SET_TRANSITION_NONE_G99,
    DIFF_SET_TRANSITION_COMMON_TO_SEPARATE_G99,
    DIFF_SET_TRANSITION_SEPARATE_TO_COMMON_G99,
)

SHUTTER_MODE_MENU_PATH_G99: str = (
    "MENU -> Exposure/Color -> [Shutter/Silent] -> [Shutter Mode]"
)
SHUTTER_MODE_SPEED_G99: str = "Speed"
SHUTTER_MODE_ANGLE_G99: str = "Angle"
ALLOWED_MOVIE_SHUTTER_MODES_G99: Tuple[str, ...] = (
    SHUTTER_MODE_SPEED_G99,
    SHUTTER_MODE_ANGLE_G99,
)

# ---------------------------------------------------------------------------
# Gate G100 Domain Constants (`[Custom Key/Dial Set.]` & `[Remain Shoot Display]`)
# ---------------------------------------------------------------------------

CUSTOM_KEY_DIAL_MENU_PATH_G100: str = (
    "MENU -> Setup -> [Operation Customize] -> [Custom Key/Dial Set.]"
)
ALLOWED_CUSTOM_KEY_DOMAINS_G100: Tuple[str, ...] = ("Still", "Movie", "Playback")
ALLOWED_CUSTOM_KEY_CONTROLS_G100: Tuple[str, ...] = (
    "Custom Button 1",
    "Custom Button 2",
    "Custom Button 3",
    "Custom Button 4",
    "Custom Button 5",
    "Custom Button 6",
    "Multi-Selector",
    "Lens Focus Hold",
    "Front dial",
    "Rear dial",
    "Control Wheel",
)
CINEMA_LINE_FACTORY_DIAL_DEFAULTS_G100: Dict[str, str] = {
    "Front dial": "Aperture",
    "Rear dial": "ISO/EI",
    "Control Wheel": "Shutter Speed",
}
CUSTOM_KEY_FOLLOW_CUSTOM_TOKEN_G100: str = "Follow Custom"
ALLOWED_LOG_SHOOTING_MODES_G100: Tuple[str, ...] = (
    "Off",
    "Flexible ISO",
    "Cine EI Quick",
    "Cine EI",
)
ALLOWED_MY_DIAL_SLOTS_G100: Tuple[str, ...] = (
    "NONE",
    "My Dial 1",
    "My Dial 2",
    "My Dial 3",
)
ALLOWED_RECALL_CUSTOM_HOLD_SLOTS_G100: Tuple[str, ...] = (
    "NONE",
    "Recall Custom hold 1",
    "Recall Custom hold 2",
    "Recall Custom hold 3",
)

CAMSET_DEFAULT_SLOT1_FILENAME_G100: str = "CAMSET01.DAT"
CAMSET_OP_NONE_G100: str = "NONE"
CAMSET_OP_LOAD_O_RDONLY_G100: str = "LOAD_O_RDONLY"
CAMSET_OP_SAVE_OVERWRITE_G100: str = "SAVE_OVERWRITE"
ALLOWED_CAMSET_OPERATIONS_G100: Tuple[str, ...] = (
    CAMSET_OP_NONE_G100,
    CAMSET_OP_LOAD_O_RDONLY_G100,
    CAMSET_OP_SAVE_OVERWRITE_G100,
)

REMAIN_SHOOT_DISPLAY_MENU_PATH_G100: str = (
    "MENU -> Setup -> [Display Option] -> [Remain Shoot Display]"
)
REMAIN_SHOOT_NOT_DISPLAYED_G100: str = "Not Displayed"
REMAIN_SHOOT_ALWAYS_DISPLAY_G100: str = "Always Display"
REMAIN_SHOOT_SHOOT_ONLY_DISPLAY_G100: str = "Shoot-Only Display"
ALLOWED_REMAIN_SHOOT_DISPLAY_MODES_G100: Tuple[str, ...] = (
    REMAIN_SHOOT_NOT_DISPLAYED_G100,
    REMAIN_SHOOT_ALWAYS_DISPLAY_G100,
    REMAIN_SHOOT_SHOOT_ONLY_DISPLAY_G100,
)
REMAIN_SHOOT_FACTORY_DEFAULT_G100: str = REMAIN_SHOOT_NOT_DISPLAYED_G100
REMAIN_SHOOT_SCOPE_STILL_BUFFER_ONLY_G100: str = "STILL_CONTINUOUS_BUFFER_ONLY"

# ---------------------------------------------------------------------------
# Pinned Local Donor Contracts (O_RDONLY, <0.10s, Clean-Room Fallback)
# ---------------------------------------------------------------------------

PINNED_PHASE256_DONOR_SPECS: Dict[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_cpapp_bin": (
        "FX3",
        "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin",
        15_980_568,
        "c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba",
        (
            b"ILME-FX3",
            b"Aperture",
            b"Shutter",
            b"Angle",
            b"ISO",
            b"Exposure",
            b"Metering",
            b"White",
            b"Balance",
            b"Profile",
            b"Focus",
            b"Custom",
            b"Dial",
            b"Wheel",
            b"Remain",
            b"Display",
            b"Monitor",
            b"Reset",
            b"Initialize",
        ),
        "FX3_CPAPP_DIFF_SET_STILL_MV_CUSTOM_KEY_DIAL_REMAIN_SHOOT_STRINGS",
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
        "FX3_LIBGPE_MENU_REMAIN_SHOOT_EVF_LESS_OSD_ELF",
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
        "FX3_LIBSAVELOADSETTINGS_CAMSET01_CUSTOM_KEY_FIREWALL_ELF",
    ),
    "fx3_bk4_bin": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin",
        2_229_740,
        "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2",
        (b"BK4", b"ILME-FX3", b"/setting"),
        "FX3_BK4_SETUP_OP_CUSTOMIZE_PERSISTENCE_SEED",
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
        "FX6_LIBINFRADIAL_DIAL_WHEEL_DISPATCH_PARITY_ELF",
    ),
    "fx6_libinfrainput_so": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libInfraInput.so",
        93_448,
        "1851e2dc8515d2240b9ecaffd58591207336c5f061b1af0d3585d7b082a41f02",
        (
            b"\x7fELF",
            b"_ZN14InfraInputBase14KeyConfigAllocEi",
            b"_ZN14InfraInputBase13KeyConfigFreeEv",
            b"_ZN14InfraInputBase7SuspendEv",
        ),
        "FX6_LIBINFRAINPUT_CUSTOM_KEYMAP_ALLOC_PARITY_ELF",
    ),
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase256DonorAuditResult:
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
class DiffSetStillMvAndShutterAngleGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    body_model_name: str
    body_model_id_hex: str
    help_guide_code: str
    firmware_version: str
    diff_set_menu_path: str
    diff_set_eight_items: Tuple[str, ...]
    diff_set_factory_checked_items: Tuple[str, ...]
    pre_reset_checked_items: Tuple[str, ...]
    reset_action: str
    effective_post_reset_checked_items: Tuple[str, ...]
    diff_set_survives_camera_settings_reset: bool
    diff_set_survives_reset_network_set: bool
    diff_set_reset_only_by_initialize: bool
    transition_mode: str
    expected_post_transition_still_values: Dict[str, str]
    expected_post_transition_movie_values: Dict[str, str]
    expected_post_transition_common_values: Dict[str, str]
    custom_wb_still_only_enforced: bool
    separate_to_common_asymmetric_retention_enforced: bool
    diff_set_transition_corruption_events: int
    shutter_mode_menu_path: str
    movie_shutter_mode: str
    shutter_speed_checked_separate: bool
    still_shutter_speed: str
    movie_shutter_angle_deg: float
    shutter_angle_override_active: bool
    effective_shutter_still_movie_independent: bool
    shutter_angle_common_bleed_events: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G99DiffSetStillMvAndShutterAngleGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    diff_set_still_mv_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CustomKeyDialAndRemainShootGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    body_model_name: str
    body_model_id_hex: str
    help_guide_code: str
    firmware_version: str
    custom_key_dial_menu_path: str
    supported_domains: Tuple[str, ...]
    factory_dial_defaults: Dict[str, str]
    pre_reset_dial_assignments: Dict[str, str]
    reset_action: str
    effective_post_reset_dial_assignments: Dict[str, str]
    log_shooting_mode: str
    effective_rear_dial_target: str
    still_custom_keymap: Dict[str, str]
    movie_custom_keymap: Dict[str, str]
    resolved_movie_custom_keymap: Dict[str, str]
    playback_custom_keymap: Dict[str, str]
    follow_custom_inherited_controls: Tuple[str, ...]
    active_my_dial_slot: str
    active_recall_custom_hold_slot: str
    custom_key_survives_camera_settings_reset: bool
    custom_key_survives_reset_network_set: bool
    custom_key_reset_only_by_initialize: bool
    tier0_vault_protection_active: bool
    slot1_camset_filename: str
    slot1_camset_operation: str
    slot1_open_flags_o_rdonly: bool
    camset_source_body_model: str
    slot1_custom_key_vault_mutation_bytes: int
    remain_shoot_display_menu_path: str
    remain_shoot_factory_default: str
    pre_reset_remain_shoot_display: str
    effective_post_reset_remain_shoot_display: str
    remain_shoot_scope: str
    displays_movie_card_remaining_time: bool
    remain_shoot_survives_camera_settings_reset: bool
    remain_shoot_survives_reset_network_set: bool
    remain_shoot_reset_only_by_initialize: bool
    fx3_has_builtin_evf: bool
    finder_monitor_switch_present: bool
    evf_eye_sensor_present: bool
    active_display_surface: str
    evf_finder_monitor_spoof_events: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G100CustomKeyDialAndRemainShootGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    custom_key_remain_shoot_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master100GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    offline_97_gates_verified: bool
    all_100_gates_verified: bool
    g13_to_g100_all_passed: bool
    g99_to_g100_all_passed: bool
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
    master_98_report: Dict[str, Any]
    g99_result: Dict[str, Any]
    g100_result: Dict[str, Any]
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


def _norm_reset_action_phase256(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if u in ("NONE", "NO RESET", ""):
        return RESET_ACTION_NONE
    if u == "CAMERA SETTINGS RESET":
        return RESET_ACTION_CAMERA_SETTINGS_RESET
    if u in ("RESET NETWORK SET.", "RESET NETWORK SET", "RESET NETWORK SETTINGS"):
        return RESET_ACTION_RESET_NETWORK_SET_PHASE256
    if u == "INITIALIZE":
        return RESET_ACTION_INITIALIZE
    return None


def _norm_diff_set_item_g99(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    mapping = {
        "APERTURE": DIFF_SET_ITEM_APERTURE_G99,
        "SHUTTER SPEED": DIFF_SET_ITEM_SHUTTER_SPEED_G99,
        "ISO": DIFF_SET_ITEM_ISO_G99,
        "EXPOSURE COMP.": DIFF_SET_ITEM_EXPOSURE_COMP_G99,
        "EXPOSURE COMP": DIFF_SET_ITEM_EXPOSURE_COMP_G99,
        "METERING MODE": DIFF_SET_ITEM_METERING_MODE_G99,
        "WHITE BALANCE": DIFF_SET_ITEM_WHITE_BALANCE_G99,
        "PICTURE PROFILE": DIFF_SET_ITEM_PICTURE_PROFILE_G99,
        "FOCUS MODE": DIFF_SET_ITEM_FOCUS_MODE_G99,
    }
    return mapping.get(s)


def _norm_diff_set_transition_g99(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = (
        re.sub(r"\s+", "_", raw.strip().strip("[]"))
        .replace("->", "_TO_")
        .replace("__", "_")
        .upper()
    )
    s = re.sub(r"_+", "_", s)
    if s in ("NONE", "NO_OP", "STEADY", ""):
        return DIFF_SET_TRANSITION_NONE_G99
    if s in ("COMMON_TO_SEPARATE", "CHECK", "UNCHECKED_TO_CHECKED"):
        return DIFF_SET_TRANSITION_COMMON_TO_SEPARATE_G99
    if s in ("SEPARATE_TO_COMMON", "UNCHECK", "CHECKED_TO_UNCHECKED"):
        return DIFF_SET_TRANSITION_SEPARATE_TO_COMMON_G99
    return None


def _norm_movie_shutter_mode_g99(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if s in ("SPEED", "SHUTTER SPEED"):
        return SHUTTER_MODE_SPEED_G99
    if s in ("ANGLE", "SHUTTER ANGLE"):
        return SHUTTER_MODE_ANGLE_G99
    return None


def _is_custom_wb_value_g99(raw: Any) -> bool:
    if not isinstance(raw, str):
        return False
    s = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    return s in (
        "CUSTOM WHITE BALANCE",
        "CUSTOM WB",
        "CUSTOM 1",
        "CUSTOM 2",
        "CUSTOM 3",
        "CUSTOM1",
        "CUSTOM2",
        "CUSTOM3",
    )


def _norm_log_shooting_mode_g100(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if s == "OFF":
        return "Off"
    if s == "FLEXIBLE ISO":
        return "Flexible ISO"
    if s == "CINE EI QUICK":
        return "Cine EI Quick"
    if s == "CINE EI":
        return "Cine EI"
    return None


def _norm_rear_dial_target_g100(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if s == "ISO":
        return "ISO"
    if s in ("EI", "EXPOSURE INDEX", "EXPOSURE INDEX (EI)"):
        return "Exposure Index (EI)"
    return raw.strip()


def _norm_follow_custom_token_g100(raw: Any) -> Optional[str]:
    if not isinstance(raw, str) or not raw.strip():
        return None
    s = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " "))
    if s.upper() == "FOLLOW CUSTOM":
        return CUSTOM_KEY_FOLLOW_CUSTOM_TOKEN_G100
    return s


def _norm_my_dial_slot_g100(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if s in ("NONE", "OFF", ""):
        return "NONE"
    if s == "MY DIAL 1":
        return "My Dial 1"
    if s == "MY DIAL 2":
        return "My Dial 2"
    if s == "MY DIAL 3":
        return "My Dial 3"
    return None


def _norm_recall_custom_hold_slot_g100(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if s in ("NONE", "OFF", ""):
        return "NONE"
    if s == "RECALL CUSTOM HOLD 1":
        return "Recall Custom hold 1"
    if s == "RECALL CUSTOM HOLD 2":
        return "Recall Custom hold 2"
    if s == "RECALL CUSTOM HOLD 3":
        return "Recall Custom hold 3"
    return None


def _norm_camset_op_g100(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = re.sub(r"\s+", "_", raw.strip().strip("[]")).upper()
    if s in ("NONE", "NO_OP", ""):
        return CAMSET_OP_NONE_G100
    if s in ("LOAD_O_RDONLY", "LOAD", "READ_ONLY_LOAD"):
        return CAMSET_OP_LOAD_O_RDONLY_G100
    if s in ("SAVE_OVERWRITE", "SAVE", "WRITE", "OVERWRITE"):
        return CAMSET_OP_SAVE_OVERWRITE_G100
    return None


def _norm_camset_filename_g100(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = raw.strip().upper()
    if re.match(r"^CAMSET(?:0[1-9]|10)\.DAT$", s):
        return s
    return None


def _norm_remain_shoot_display_g100(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if s == "NOT DISPLAYED":
        return REMAIN_SHOOT_NOT_DISPLAYED_G100
    if s == "ALWAYS DISPLAY":
        return REMAIN_SHOOT_ALWAYS_DISPLAY_G100
    if s in ("SHOOT-ONLY DISPLAY", "SHOOT ONLY DISPLAY"):
        return REMAIN_SHOOT_SHOOT_ONLY_DISPLAY_G100
    return None


# ---------------------------------------------------------------------------
# 1. Bounded `< 0.10s` O_RDONLY Donor Contract Audit (`Phase 256`)
# ---------------------------------------------------------------------------


def audit_phase256_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    max_budget_seconds: float = DONOR_CHECK_MAX_SECONDS_PHASE256,
) -> Phase256DonorAuditResult:
    """Inspect local FX3 Ver. 7.02 / FX6 Ver. 6.01 donor artifacts strictly
    `os.O_RDONLY` within `<0.10s`, verifying bounded symbols across
    `cpapp-b.bin`, `libgpe.so`, `libSaveLoadSettings.so`, `FX3-CX95900_ALLLANG-Backup.bin`,
    `libInfraDial.so`, and `libInfraInput.so` with deterministic
    `FX3_FX6_FORCE_CLEAN_ROOM=1` parity.
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
        for key, (_body, rel_path, *_rest) in PINNED_PHASE256_DONOR_SPECS.items():
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
            spec[5] for spec in PINNED_PHASE256_DONOR_SPECS.values()
        )
        synthetic_shas = {
            k: f"synthetic:{v[3][:16]}" for k, v in PINNED_PHASE256_DONOR_SPECS.items()
        }
        synthetic_sizes = {k: v[2] for k, v in PINNED_PHASE256_DONOR_SPECS.items()}
        return Phase256DonorAuditResult(
            valid=within_budget,
            status=(
                STATUS_VERIFIED_SAFE
                if within_budget
                else STATUS_BLOCKED_PHASE256_DONOR_INTEGRITY
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
    ) in PINNED_PHASE256_DONOR_SPECS.items():
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
        if (not missing_for_file) and integrity_ok:
            passed_keys.add(key)

    elapsed = time.perf_counter() - t0
    within_budget = elapsed < max_budget_seconds
    if not within_budget:
        errors.append(
            f"Local O_RDONLY donor check exceeded budget ({elapsed:.4f}s >= {max_budget_seconds:.4f}s)."
        )

    fx3_keys = {k for k, v in PINNED_PHASE256_DONOR_SPECS.items() if v[0] == "FX3"}
    fx6_keys = {k for k, v in PINNED_PHASE256_DONOR_SPECS.items() if v[0] == "FX6"}
    fx3_ok = fx3_keys.issubset(passed_keys)
    fx6_ok = fx6_keys.issubset(passed_keys)
    valid = fx3_ok and fx6_ok and (not missing) and within_budget and (not errors)

    return Phase256DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_PHASE256_DONOR_INTEGRITY,
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
# 2. Gate `G99`: `[Different Set for Still/Mv]` 8-Item Asymmetric Transitions,
#    Reset Survival & `Ver. 7.02` `[Shutter Mode] = [Angle]` Override Guard
# ---------------------------------------------------------------------------


def resolve_fx3_diff_set_still_mv_and_shutter_angle_state(
    *,
    pre_reset_checked_items: Sequence[str] = (
        DIFF_SET_ITEM_APERTURE_G99,
        DIFF_SET_ITEM_ISO_G99,
        DIFF_SET_ITEM_WHITE_BALANCE_G99,
        DIFF_SET_ITEM_PICTURE_PROFILE_G99,
    ),
    reset_action: str = RESET_ACTION_NONE,
    transition_mode: str = DIFF_SET_TRANSITION_NONE_G99,
    common_values: Optional[Mapping[str, str]] = None,
    movie_fallback_white_balance: str = "Auto",
    separate_still_values: Optional[Mapping[str, str]] = None,
    separate_movie_values: Optional[Mapping[str, str]] = None,
    movie_shutter_mode: str = SHUTTER_MODE_ANGLE_G99,
    still_shutter_speed: str = "1/250",
    movie_shutter_angle_deg: float = 180.0,
) -> Dict[str, Any]:
    """Deterministically resolve Sony `ILME-FX3` (`Ver. 7.02`) `[Different Set for
    Still/Mv]` post-reset survival, `Common -> Separate` / `Separate -> Common`
    asymmetric parameter transitions, and `[Shutter Mode] = [Angle]` override.
    """
    norm_reset = _norm_reset_action_phase256(reset_action) or RESET_ACTION_NONE
    norm_trans = (
        _norm_diff_set_transition_g99(transition_mode) or DIFF_SET_TRANSITION_NONE_G99
    )
    norm_shutter_mode = (
        _norm_movie_shutter_mode_g99(movie_shutter_mode) or SHUTTER_MODE_ANGLE_G99
    )

    normalized_pre: List[str] = []
    for raw_item in pre_reset_checked_items:
        canon = _norm_diff_set_item_g99(raw_item)
        if canon is not None and canon not in normalized_pre:
            normalized_pre.append(canon)
    ordered_pre = tuple(
        item for item in DIFF_SET_STILL_MV_EIGHT_ITEMS_G99 if item in normalized_pre
    )

    if norm_reset == RESET_ACTION_INITIALIZE:
        expected_post_reset_checked = DIFF_SET_FACTORY_CHECKED_ITEMS_G99
    else:
        expected_post_reset_checked = ordered_pre

    merged_common: Dict[str, str] = dict(DIFF_SET_INITIAL_FACTORY_PARAM_DEFAULTS_G99)
    if common_values is not None:
        for k, v in common_values.items():
            ck = _norm_diff_set_item_g99(k) or str(k)
            merged_common[ck] = str(v)

    default_sep_still: Dict[str, str] = {
        DIFF_SET_ITEM_APERTURE_G99: "F2.8",
        DIFF_SET_ITEM_SHUTTER_SPEED_G99: still_shutter_speed,
        DIFF_SET_ITEM_ISO_G99: "ISO 800",
        DIFF_SET_ITEM_EXPOSURE_COMP_G99: "+0.7EV",
        DIFF_SET_ITEM_METERING_MODE_G99: "Spot: Standard",
        DIFF_SET_ITEM_WHITE_BALANCE_G99: "Custom White Balance",
        DIFF_SET_ITEM_PICTURE_PROFILE_G99: "PP11",
        DIFF_SET_ITEM_FOCUS_MODE_G99: "AF-S",
    }
    if separate_still_values is not None:
        for k, v in separate_still_values.items():
            ck = _norm_diff_set_item_g99(k) or str(k)
            default_sep_still[ck] = str(v)

    default_sep_movie: Dict[str, str] = {
        DIFF_SET_ITEM_APERTURE_G99: "F5.6",
        DIFF_SET_ITEM_SHUTTER_SPEED_G99: "1/50",
        DIFF_SET_ITEM_ISO_G99: "ISO 12800",
        DIFF_SET_ITEM_EXPOSURE_COMP_G99: "-0.3EV",
        DIFF_SET_ITEM_METERING_MODE_G99: "Center",
        DIFF_SET_ITEM_WHITE_BALANCE_G99: "5500K",
        DIFF_SET_ITEM_PICTURE_PROFILE_G99: "PP8",
        DIFF_SET_ITEM_FOCUS_MODE_G99: "AF-C",
    }
    if separate_movie_values is not None:
        for k, v in separate_movie_values.items():
            ck = _norm_diff_set_item_g99(k) or str(k)
            default_sep_movie[ck] = str(v)

    # Rule 1: Common -> Separate copies current common values to Still & Movie,
    # EXCEPT Custom White Balance which applies ONLY to still-image shooting.
    expected_c2s_still: Dict[str, str] = {}
    expected_c2s_movie: Dict[str, str] = {}
    for item in DIFF_SET_STILL_MV_EIGHT_ITEMS_G99:
        val = merged_common[item]
        expected_c2s_still[item] = val
        if item == DIFF_SET_ITEM_WHITE_BALANCE_G99 and _is_custom_wb_value_g99(val):
            expected_c2s_movie[item] = movie_fallback_white_balance
        else:
            expected_c2s_movie[item] = val

    # Rule 2: Separate -> Common resets parameters to initial factory defaults,
    # EXCEPT Aperture, Shutter Speed, and Custom White Balance (retain Still).
    expected_s2c_common: Dict[str, str] = {}
    for item in DIFF_SET_STILL_MV_EIGHT_ITEMS_G99:
        still_val = default_sep_still[item]
        if item in DIFF_SET_SEPARATE_TO_COMMON_STILL_RETAINED_ITEMS_G99:
            expected_s2c_common[item] = still_val
        elif item == DIFF_SET_ITEM_WHITE_BALANCE_G99 and _is_custom_wb_value_g99(
            still_val
        ):
            expected_s2c_common[item] = still_val
        else:
            expected_s2c_common[item] = DIFF_SET_INITIAL_FACTORY_PARAM_DEFAULTS_G99[
                item
            ]

    if norm_trans == DIFF_SET_TRANSITION_COMMON_TO_SEPARATE_G99:
        active_still = expected_c2s_still
        active_movie = expected_c2s_movie
        active_common = dict(merged_common)
    elif norm_trans == DIFF_SET_TRANSITION_SEPARATE_TO_COMMON_G99:
        active_still = dict(default_sep_still)
        active_movie = dict(default_sep_movie)
        active_common = expected_s2c_common
    else:
        active_still = expected_c2s_still
        active_movie = expected_c2s_movie
        active_common = expected_s2c_common

    shutter_checked_separate = (
        DIFF_SET_ITEM_SHUTTER_SPEED_G99 in expected_post_reset_checked
    )
    shutter_angle_override = norm_shutter_mode == SHUTTER_MODE_ANGLE_G99
    effective_independent = shutter_angle_override or shutter_checked_separate

    return {
        "normalized_pre_reset_checked_items": ordered_pre,
        "reset_action": norm_reset,
        "expected_post_reset_checked_items": expected_post_reset_checked,
        "transition_mode": norm_trans,
        "expected_post_transition_still_values": active_still,
        "expected_post_transition_movie_values": active_movie,
        "expected_post_transition_common_values": active_common,
        "movie_shutter_mode": norm_shutter_mode,
        "shutter_speed_checked_separate": shutter_checked_separate,
        "shutter_angle_override_active": shutter_angle_override,
        "effective_shutter_still_movie_independent": effective_independent,
        "still_shutter_speed": still_shutter_speed,
        "movie_shutter_angle_deg": float(movie_shutter_angle_deg),
    }


def verify_diff_set_still_mv_and_shutter_angle_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: int = FX3_MODEL_ID,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE256,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE256,
    diff_set_menu_path: str = DIFF_SET_STILL_MV_MENU_PATH_G99,
    pre_reset_checked_items: Sequence[str] = (
        DIFF_SET_ITEM_APERTURE_G99,
        DIFF_SET_ITEM_ISO_G99,
        DIFF_SET_ITEM_WHITE_BALANCE_G99,
        DIFF_SET_ITEM_PICTURE_PROFILE_G99,
    ),
    reset_action: str = RESET_ACTION_NONE,
    observed_post_reset_checked_items: Optional[Sequence[str]] = None,
    transition_mode: str = DIFF_SET_TRANSITION_NONE_G99,
    common_values: Optional[Mapping[str, str]] = None,
    movie_fallback_white_balance: str = "Auto",
    separate_still_values: Optional[Mapping[str, str]] = None,
    separate_movie_values: Optional[Mapping[str, str]] = None,
    observed_post_transition_still_values: Optional[Mapping[str, str]] = None,
    observed_post_transition_movie_values: Optional[Mapping[str, str]] = None,
    observed_post_transition_common_values: Optional[Mapping[str, str]] = None,
    diff_set_transition_corruption_events: int = 0,
    shutter_mode_menu_path: str = SHUTTER_MODE_MENU_PATH_G99,
    movie_shutter_mode: str = SHUTTER_MODE_ANGLE_G99,
    still_shutter_speed: str = "1/250",
    movie_shutter_angle_deg: float = 180.0,
    observed_still_shutter_speed: Optional[str] = None,
    observed_movie_shutter_angle_deg: Optional[float] = None,
    observed_shutter_still_movie_independent: Optional[bool] = None,
    shutter_angle_common_bleed_events: int = 0,
) -> DiffSetStillMvAndShutterAngleGuardResult:
    """Verify Gate `G99`: `[Different Set for Still/Mv]` exact 8-item catalog,
    `Camera Settings Reset` + `Reset Network Set.` survival, asymmetric
    `Common -> Separate` & `Separate -> Common` transitions, and `Ver. 7.02`
    `[Shutter Mode] = [Angle]` independence override.
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
        or help_guide_code != FX3_HELP_GUIDE_CODE_PHASE256
        or fw_tuple is None
        or fw_tuple < FX3_MIN_SUPPORTED_FW_TUPLE_PHASE256
        or not isinstance(diff_set_transition_corruption_events, int)
        or isinstance(diff_set_transition_corruption_events, bool)
        or diff_set_transition_corruption_events < 0
        or not isinstance(shutter_angle_common_bleed_events, int)
        or isinstance(shutter_angle_common_bleed_events, bool)
        or shutter_angle_common_bleed_events < 0
    ):
        _add_code(codes, STATUS_BLOCKED_G99_TELEMETRY_INVALID)
        errors.append(
            "Invalid ILME-FX3 telemetry, firmware version, or negative event counters in Gate G99."
        )

    norm_reset = _norm_reset_action_phase256(reset_action)
    if norm_reset is None or diff_set_menu_path != DIFF_SET_STILL_MV_MENU_PATH_G99:
        _add_code(
            codes,
            STATUS_BLOCKED_G99_DIFF_SET_ITEM_CATALOG_OR_RESET_PERSISTENCE_VIOLATION,
        )
        errors.append(
            f"Unsupported reset_action={reset_action!r} or menu path={diff_set_menu_path!r} in Gate G99."
        )

    invalid_pre_items: List[str] = []
    if isinstance(pre_reset_checked_items, (str, bytes)) or not isinstance(
        pre_reset_checked_items, Sequence
    ):
        invalid_pre_items.append(repr(pre_reset_checked_items))
    else:
        for item in pre_reset_checked_items:
            if _norm_diff_set_item_g99(item) is None:
                invalid_pre_items.append(repr(item))
    if invalid_pre_items:
        _add_code(
            codes,
            STATUS_BLOCKED_G99_DIFF_SET_ITEM_CATALOG_OR_RESET_PERSISTENCE_VIOLATION,
        )
        errors.append(
            f"Unsupported [Different Set for Still/Mv] item(s) outside exact 8-item catalog: {invalid_pre_items}."
        )

    norm_trans = _norm_diff_set_transition_g99(transition_mode)
    if norm_trans is None:
        _add_code(codes, STATUS_BLOCKED_G99_TELEMETRY_INVALID)
        errors.append(f"Unsupported transition_mode={transition_mode!r} in Gate G99.")

    norm_shutter_mode = _norm_movie_shutter_mode_g99(movie_shutter_mode)
    if (
        norm_shutter_mode is None
        or shutter_mode_menu_path != SHUTTER_MODE_MENU_PATH_G99
    ):
        _add_code(codes, STATUS_BLOCKED_G99_SHUTTER_ANGLE_COMMON_BLEED_VIOLATION)
        errors.append(
            f"Unsupported movie_shutter_mode={movie_shutter_mode!r} or menu path={shutter_mode_menu_path!r}."
        )

    state = resolve_fx3_diff_set_still_mv_and_shutter_angle_state(
        pre_reset_checked_items=() if invalid_pre_items else pre_reset_checked_items,
        reset_action=norm_reset or RESET_ACTION_NONE,
        transition_mode=norm_trans or DIFF_SET_TRANSITION_NONE_G99,
        common_values=common_values,
        movie_fallback_white_balance=movie_fallback_white_balance,
        separate_still_values=separate_still_values,
        separate_movie_values=separate_movie_values,
        movie_shutter_mode=norm_shutter_mode or SHUTTER_MODE_ANGLE_G99,
        still_shutter_speed=still_shutter_speed,
        movie_shutter_angle_deg=movie_shutter_angle_deg,
    )

    expected_checked: Tuple[str, ...] = state["expected_post_reset_checked_items"]
    effective_checked = expected_checked
    if observed_post_reset_checked_items is not None:
        obs_norm: List[str] = []
        obs_invalid = False
        if isinstance(
            observed_post_reset_checked_items, (str, bytes)
        ) or not isinstance(observed_post_reset_checked_items, Sequence):
            obs_invalid = True
        else:
            for item in observed_post_reset_checked_items:
                c = _norm_diff_set_item_g99(item)
                if c is None:
                    obs_invalid = True
                elif c not in obs_norm:
                    obs_norm.append(c)
        effective_checked = tuple(
            it for it in DIFF_SET_STILL_MV_EIGHT_ITEMS_G99 if it in obs_norm
        )
        if obs_invalid or effective_checked != expected_checked:
            _add_code(
                codes,
                STATUS_BLOCKED_G99_DIFF_SET_ITEM_CATALOG_OR_RESET_PERSISTENCE_VIOLATION,
            )
            errors.append(
                f"Post-reset [Different Set for Still/Mv] mismatch under {norm_reset}: "
                f"observed={observed_post_reset_checked_items!r}, expected={expected_checked!r}."
            )

    corruption_count = max(0, int(diff_set_transition_corruption_events))
    c2s_still: Dict[str, str] = state["expected_post_transition_still_values"]
    c2s_movie: Dict[str, str] = state["expected_post_transition_movie_values"]
    s2c_common: Dict[str, str] = state["expected_post_transition_common_values"]

    custom_wb_still_only_ok = True
    if _is_custom_wb_value_g99(movie_fallback_white_balance):
        custom_wb_still_only_ok = False
        corruption_count += 1
        _add_code(
            codes, STATUS_BLOCKED_G99_COMMON_TO_SEPARATE_CUSTOM_WB_STILL_ONLY_VIOLATION
        )
        errors.append(
            "movie_fallback_white_balance cannot be Custom White Balance in Common -> Separate."
        )

    if observed_post_transition_still_values is not None:
        for item in DIFF_SET_STILL_MV_EIGHT_ITEMS_G99:
            obs_v = observed_post_transition_still_values.get(item)
            if obs_v is not None and str(obs_v) != c2s_still[item]:
                custom_wb_still_only_ok = False
                corruption_count += 1
                _add_code(
                    codes,
                    STATUS_BLOCKED_G99_COMMON_TO_SEPARATE_CUSTOM_WB_STILL_ONLY_VIOLATION,
                )
                errors.append(
                    f"Common -> Separate Still register mismatch for {item}: "
                    f"observed={obs_v!r}, expected={c2s_still[item]!r}."
                )

    if observed_post_transition_movie_values is not None:
        for item in DIFF_SET_STILL_MV_EIGHT_ITEMS_G99:
            obs_v = observed_post_transition_movie_values.get(item)
            if obs_v is not None and str(obs_v) != c2s_movie[item]:
                custom_wb_still_only_ok = False
                corruption_count += 1
                _add_code(
                    codes,
                    STATUS_BLOCKED_G99_COMMON_TO_SEPARATE_CUSTOM_WB_STILL_ONLY_VIOLATION,
                )
                errors.append(
                    f"Common -> Separate Movie register mismatch for {item}: "
                    f"observed={obs_v!r}, expected={c2s_movie[item]!r}."
                )

    s2c_retention_ok = True
    if observed_post_transition_common_values is not None:
        for item in DIFF_SET_STILL_MV_EIGHT_ITEMS_G99:
            obs_v = observed_post_transition_common_values.get(item)
            if obs_v is not None and str(obs_v) != s2c_common[item]:
                s2c_retention_ok = False
                corruption_count += 1
                _add_code(
                    codes,
                    STATUS_BLOCKED_G99_SEPARATE_TO_COMMON_ASYMMETRIC_RETENTION_VIOLATION,
                )
                errors.append(
                    f"Separate -> Common asymmetric retention mismatch for {item}: "
                    f"observed={obs_v!r}, expected={s2c_common[item]!r}."
                )

    if diff_set_transition_corruption_events > 0 and (
        STATUS_BLOCKED_G99_COMMON_TO_SEPARATE_CUSTOM_WB_STILL_ONLY_VIOLATION
        not in codes
        and STATUS_BLOCKED_G99_SEPARATE_TO_COMMON_ASYMMETRIC_RETENTION_VIOLATION
        not in codes
    ):
        if norm_trans == DIFF_SET_TRANSITION_COMMON_TO_SEPARATE_G99:
            custom_wb_still_only_ok = False
            _add_code(
                codes,
                STATUS_BLOCKED_G99_COMMON_TO_SEPARATE_CUSTOM_WB_STILL_ONLY_VIOLATION,
            )
        else:
            s2c_retention_ok = False
            _add_code(
                codes,
                STATUS_BLOCKED_G99_SEPARATE_TO_COMMON_ASYMMETRIC_RETENTION_VIOLATION,
            )
        errors.append(
            f"Non-zero diff_set_transition_corruption_events={diff_set_transition_corruption_events} reported."
        )

    # Rule 3: Ver. 6.00+ / Ver. 7.02 [Shutter Mode] = [Angle] override
    bleed_count = max(0, int(shutter_angle_common_bleed_events))
    if (
        not isinstance(still_shutter_speed, str)
        or not still_shutter_speed.strip()
        or not isinstance(movie_shutter_angle_deg, (int, float))
        or isinstance(movie_shutter_angle_deg, bool)
        or float(movie_shutter_angle_deg) <= 0.0
        or float(movie_shutter_angle_deg) > 360.0
    ):
        bleed_count += 1
        _add_code(codes, STATUS_BLOCKED_G99_SHUTTER_ANGLE_COMMON_BLEED_VIOLATION)
        errors.append(
            f"Invalid still_shutter_speed={still_shutter_speed!r} or movie_shutter_angle_deg={movie_shutter_angle_deg!r}."
        )

    if (
        norm_shutter_mode == SHUTTER_MODE_ANGLE_G99
        and fw_tuple is not None
        and fw_tuple < FX3_SHUTTER_ANGLE_MIN_FW_TUPLE_G99
    ):
        bleed_count += 1
        _add_code(codes, STATUS_BLOCKED_G99_SHUTTER_ANGLE_COMMON_BLEED_VIOLATION)
        errors.append(
            f"[Shutter Mode] = [Angle] requires ILME-FX3 Ver. 6.00+ (got {firmware_version!r})."
        )

    if norm_shutter_mode == SHUTTER_MODE_ANGLE_G99:
        if observed_shutter_still_movie_independent is False:
            bleed_count += 1
            _add_code(codes, STATUS_BLOCKED_G99_SHUTTER_ANGLE_COMMON_BLEED_VIOLATION)
            errors.append(
                "[Shutter Mode] = [Angle] MUST keep Still Shutter Speed and Movie Shutter Angle independent even when Shutter Speed is Common."
            )
        if (
            observed_still_shutter_speed is not None
            and str(observed_still_shutter_speed) != still_shutter_speed
        ):
            bleed_count += 1
            _add_code(codes, STATUS_BLOCKED_G99_SHUTTER_ANGLE_COMMON_BLEED_VIOLATION)
            errors.append(
                f"Movie Shutter Angle bled into Still Shutter Speed: observed={observed_still_shutter_speed!r} != {still_shutter_speed!r}."
            )
        if observed_movie_shutter_angle_deg is not None and abs(
            float(observed_movie_shutter_angle_deg) - float(movie_shutter_angle_deg)
        ) > 1e-6:
            bleed_count += 1
            _add_code(codes, STATUS_BLOCKED_G99_SHUTTER_ANGLE_COMMON_BLEED_VIOLATION)
            errors.append(
                f"Still Shutter Speed bled into Movie Shutter Angle: observed={observed_movie_shutter_angle_deg!r} != {movie_shutter_angle_deg!r}."
            )
    elif norm_shutter_mode == SHUTTER_MODE_SPEED_G99:
        exp_indep = bool(state["effective_shutter_still_movie_independent"])
        if (
            observed_shutter_still_movie_independent is not None
            and bool(observed_shutter_still_movie_independent) != exp_indep
        ):
            bleed_count += 1
            _add_code(codes, STATUS_BLOCKED_G99_SHUTTER_ANGLE_COMMON_BLEED_VIOLATION)
            errors.append(
                f"[Shutter Mode] = [Speed] independence mismatch: observed={observed_shutter_still_movie_independent!r}, expected={exp_indep!r}."
            )

    if (
        bleed_count > 0
        and STATUS_BLOCKED_G99_SHUTTER_ANGLE_COMMON_BLEED_VIOLATION not in codes
    ):
        _add_code(codes, STATUS_BLOCKED_G99_SHUTTER_ANGLE_COMMON_BLEED_VIOLATION)
        errors.append(
            f"Non-zero shutter_angle_common_bleed_events={bleed_count} reported."
        )

    valid = len(codes) == 0
    status = STATUS_VERIFIED_G99 if valid else codes[0]

    return DiffSetStillMvAndShutterAngleGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=body_model_name,
        body_model_id_hex=(
            f"0x{body_model_id:08x}"
            if isinstance(body_model_id, int) and not isinstance(body_model_id, bool)
            else "INVALID"
        ),
        help_guide_code=help_guide_code,
        firmware_version=str(firmware_version),
        diff_set_menu_path=diff_set_menu_path,
        diff_set_eight_items=DIFF_SET_STILL_MV_EIGHT_ITEMS_G99,
        diff_set_factory_checked_items=DIFF_SET_FACTORY_CHECKED_ITEMS_G99,
        pre_reset_checked_items=state["normalized_pre_reset_checked_items"],
        reset_action=norm_reset or str(reset_action),
        effective_post_reset_checked_items=effective_checked,
        diff_set_survives_camera_settings_reset=True,
        diff_set_survives_reset_network_set=True,
        diff_set_reset_only_by_initialize=True,
        transition_mode=norm_trans or str(transition_mode),
        expected_post_transition_still_values=c2s_still,
        expected_post_transition_movie_values=c2s_movie,
        expected_post_transition_common_values=s2c_common,
        custom_wb_still_only_enforced=custom_wb_still_only_ok,
        separate_to_common_asymmetric_retention_enforced=s2c_retention_ok,
        diff_set_transition_corruption_events=corruption_count,
        shutter_mode_menu_path=shutter_mode_menu_path,
        movie_shutter_mode=norm_shutter_mode or str(movie_shutter_mode),
        shutter_speed_checked_separate=bool(state["shutter_speed_checked_separate"]),
        still_shutter_speed=str(still_shutter_speed),
        movie_shutter_angle_deg=(
            float(movie_shutter_angle_deg)
            if isinstance(movie_shutter_angle_deg, (int, float))
            and not isinstance(movie_shutter_angle_deg, bool)
            else -1.0
        ),
        shutter_angle_override_active=bool(state["shutter_angle_override_active"]),
        effective_shutter_still_movie_independent=bool(
            state["effective_shutter_still_movie_independent"]
        ),
        shutter_angle_common_bleed_events=bleed_count,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g99_diff_set_still_mv_and_shutter_angle_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    diff_set_still_mv_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase256DonorAuditResult] = None,
) -> Tuple[GateVerdict, G99DiffSetStillMvAndShutterAngleGuardResult]:
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase256_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_diff_set_still_mv_and_shutter_angle_guard(
        **dict(diff_set_still_mv_kwargs or {})
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
        errors.append("Persistent eMMC write authorization requested in Gate G99.")
    if not audit.valid:
        _add_code(codes, audit.status)
    for c in guard.violation_codes:
        _add_code(codes, c)

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G99 if valid else codes[0]

    res = G99DiffSetStillMvAndShutterAngleGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        diff_set_still_mv_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, checked={len(guard.effective_post_reset_checked_items)}/8"
        f"(transition={guard.transition_mode},corrupt={guard.diff_set_transition_corruption_events}), "
        f"shutter_mode={guard.movie_shutter_mode}(indep={guard.effective_shutter_still_movie_independent},"
        f"bleed={guard.shutter_angle_common_bleed_events})"
    )
    verdict = GateVerdict(
        gate_id=G99_GATE_ID,
        gate_code=G99_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 3. Gate `G100` (`100th` Milestone Gate): `[Custom Key/Dial Set.]` 3-Domain
#    Keymaps / `ISO/EI` Auto-Adapt / Slot-1 `CAMSET01.DAT` Firewall &
#    `[Remain Shoot Display]` Still-Buffer Scope + EVF-Less Topology Guard
# ---------------------------------------------------------------------------

_DEFAULT_FACTORY_STILL_KEYMAP_G100: Dict[str, str] = {
    "Custom Button 1": "White Balance",
    "Custom Button 2": "Focus Standard",
    "Custom Button 3": "Focus Mode",
    "Custom Button 4": "Touch Operation Select",
    "Custom Button 5": "Shot Mark1",
    "Custom Button 6": "Zebra Display Select",
    "Multi-Selector": "Focus Standard",
    "Lens Focus Hold": "Focus Hold",
}

_DEFAULT_FACTORY_MOVIE_KEYMAP_G100: Dict[str, str] = {
    "Custom Button 1": CUSTOM_KEY_FOLLOW_CUSTOM_TOKEN_G100,
    "Custom Button 2": "Peaking Display Select",
    "Custom Button 3": CUSTOM_KEY_FOLLOW_CUSTOM_TOKEN_G100,
    "Custom Button 4": CUSTOM_KEY_FOLLOW_CUSTOM_TOKEN_G100,
    "Custom Button 5": "Shot Mark1",
    "Custom Button 6": "Zebra Display Select",
    "Multi-Selector": CUSTOM_KEY_FOLLOW_CUSTOM_TOKEN_G100,
    "Lens Focus Hold": CUSTOM_KEY_FOLLOW_CUSTOM_TOKEN_G100,
}

_DEFAULT_FACTORY_PLAYBACK_KEYMAP_G100: Dict[str, str] = {
    "Custom Button 2": "Send to Smartphone",
    "Custom Button 3": "Protect",
    "Fn/Delete Button": "Delete",
}


def resolve_fx3_custom_key_dial_and_remain_shoot_state(
    *,
    pre_reset_dial_assignments: Optional[Mapping[str, str]] = None,
    still_custom_keymap: Optional[Mapping[str, str]] = None,
    movie_custom_keymap: Optional[Mapping[str, str]] = None,
    playback_custom_keymap: Optional[Mapping[str, str]] = None,
    log_shooting_mode: str = "Cine EI",
    pre_reset_remain_shoot_display: str = REMAIN_SHOOT_NOT_DISPLAYED_G100,
    reset_action: str = RESET_ACTION_NONE,
) -> Dict[str, Any]:
    """Deterministically resolve Sony `ILME-FX3` (`Ver. 7.02`) `[Custom Key/Dial Set.]`
    3-domain mappings, `Rear dial = ISO/EI` exposure-mode adaptation, `[Follow Custom]`
    movie inheritance, `[Remain Shoot Display]` reset survival, and factory `[Initialize]`.
    """
    norm_reset = _norm_reset_action_phase256(reset_action) or RESET_ACTION_NONE
    norm_log = _norm_log_shooting_mode_g100(log_shooting_mode) or "Cine EI"
    norm_remain_pre = (
        _norm_remain_shoot_display_g100(pre_reset_remain_shoot_display)
        or REMAIN_SHOOT_NOT_DISPLAYED_G100
    )

    pre_dials: Dict[str, str] = dict(CINEMA_LINE_FACTORY_DIAL_DEFAULTS_G100)
    if pre_reset_dial_assignments is not None:
        for k, v in pre_reset_dial_assignments.items():
            pre_dials[str(k)] = str(v)

    still_map: Dict[str, str] = dict(_DEFAULT_FACTORY_STILL_KEYMAP_G100)
    if still_custom_keymap is not None:
        for k, v in still_custom_keymap.items():
            still_map[str(k)] = _norm_follow_custom_token_g100(v) or str(v)

    movie_map: Dict[str, str] = dict(_DEFAULT_FACTORY_MOVIE_KEYMAP_G100)
    if movie_custom_keymap is not None:
        for k, v in movie_custom_keymap.items():
            movie_map[str(k)] = _norm_follow_custom_token_g100(v) or str(v)

    playback_map: Dict[str, str] = dict(_DEFAULT_FACTORY_PLAYBACK_KEYMAP_G100)
    if playback_custom_keymap is not None:
        for k, v in playback_custom_keymap.items():
            playback_map[str(k)] = _norm_follow_custom_token_g100(v) or str(v)

    if norm_reset == RESET_ACTION_INITIALIZE:
        post_dials = dict(CINEMA_LINE_FACTORY_DIAL_DEFAULTS_G100)
        post_still = dict(_DEFAULT_FACTORY_STILL_KEYMAP_G100)
        post_movie = dict(_DEFAULT_FACTORY_MOVIE_KEYMAP_G100)
        post_playback = dict(_DEFAULT_FACTORY_PLAYBACK_KEYMAP_G100)
        post_remain = REMAIN_SHOOT_FACTORY_DEFAULT_G100
    else:
        post_dials = dict(pre_dials)
        post_still = dict(still_map)
        post_movie = dict(movie_map)
        post_playback = dict(playback_map)
        post_remain = norm_remain_pre

    resolved_movie: Dict[str, str] = {}
    inherited_controls: List[str] = []
    for ctrl, assigned in post_movie.items():
        if assigned == CUSTOM_KEY_FOLLOW_CUSTOM_TOKEN_G100:
            resolved_movie[ctrl] = post_still.get(ctrl, "Not set")
            inherited_controls.append(ctrl)
        else:
            resolved_movie[ctrl] = assigned

    rear_dial_fn = post_dials.get("Rear dial", "ISO/EI")
    if rear_dial_fn == "ISO/EI":
        if norm_log in ("Cine EI", "Cine EI Quick"):
            effective_rear_target = "Exposure Index (EI)"
        else:
            effective_rear_target = "ISO"
    else:
        effective_rear_target = rear_dial_fn

    return {
        "reset_action": norm_reset,
        "log_shooting_mode": norm_log,
        "pre_reset_dial_assignments": pre_dials,
        "expected_post_reset_dial_assignments": post_dials,
        "effective_rear_dial_target": effective_rear_target,
        "expected_post_reset_still_keymap": post_still,
        "expected_post_reset_movie_keymap": post_movie,
        "resolved_movie_custom_keymap": resolved_movie,
        "expected_post_reset_playback_keymap": post_playback,
        "follow_custom_inherited_controls": tuple(inherited_controls),
        "pre_reset_remain_shoot_display": norm_remain_pre,
        "expected_post_reset_remain_shoot_display": post_remain,
    }


def verify_custom_key_dial_iso_ei_and_remain_shoot_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: int = FX3_MODEL_ID,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE256,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE256,
    custom_key_dial_menu_path: str = CUSTOM_KEY_DIAL_MENU_PATH_G100,
    supported_domains: Sequence[str] = ALLOWED_CUSTOM_KEY_DOMAINS_G100,
    pre_reset_dial_assignments: Optional[Mapping[str, str]] = None,
    still_custom_keymap: Optional[Mapping[str, str]] = None,
    movie_custom_keymap: Optional[Mapping[str, str]] = None,
    playback_custom_keymap: Optional[Mapping[str, str]] = None,
    log_shooting_mode: str = "Cine EI",
    observed_rear_dial_target: Optional[str] = None,
    observed_resolved_movie_keymap: Optional[Mapping[str, str]] = None,
    active_my_dial_slot: str = "NONE",
    active_recall_custom_hold_slot: str = "NONE",
    reset_action: str = RESET_ACTION_NONE,
    observed_post_reset_dial_assignments: Optional[Mapping[str, str]] = None,
    observed_post_reset_custom_keys_preserved: Optional[bool] = None,
    tier0_vault_protection_active: bool = True,
    slot1_camset_filename: str = CAMSET_DEFAULT_SLOT1_FILENAME_G100,
    slot1_camset_operation: str = CAMSET_OP_LOAD_O_RDONLY_G100,
    slot1_open_flags: int = os.O_RDONLY,
    camset_source_body_model: str = FX3_MODEL_NAME,
    slot1_custom_key_vault_mutation_bytes: int = 0,
    remain_shoot_display_menu_path: str = REMAIN_SHOOT_DISPLAY_MENU_PATH_G100,
    pre_reset_remain_shoot_display: str = REMAIN_SHOOT_NOT_DISPLAYED_G100,
    observed_post_reset_remain_shoot_display: Optional[str] = None,
    remain_shoot_scope: str = REMAIN_SHOOT_SCOPE_STILL_BUFFER_ONLY_G100,
    displays_movie_card_remaining_time: bool = False,
    claimed_builtin_evf: bool = False,
    finder_monitor_switch_present: bool = False,
    evf_eye_sensor_present: bool = False,
    active_display_surface: str = FX3_ACTIVE_DISPLAY_SURFACE_LCD_G100,
    evf_finder_monitor_spoof_events: int = 0,
) -> CustomKeyDialAndRemainShootGuardResult:
    """Verify Gate `G100` (`100th` Safety Gate): `[Custom Key/Dial Set.]` 3-domain
    mappings, Cinema-Line `Front dial=Aperture` / `Rear dial=ISO/EI` /
    `Control Wheel=Shutter Speed`, `[Follow Custom]`, `[My Dial 1..3]`, Slot-1
    Tier-0 `CAMSET01.DAT` `O_RDONLY` load-only firewall, AND `[Remain Shoot Display]`
    still-buffer scope + EVF-less `ILME-FX3` (`ilc/2210`) topology guard.
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
        or help_guide_code != FX3_HELP_GUIDE_CODE_PHASE256
        or fw_tuple is None
        or fw_tuple < FX3_MIN_SUPPORTED_FW_TUPLE_PHASE256
        or not isinstance(slot1_custom_key_vault_mutation_bytes, int)
        or isinstance(slot1_custom_key_vault_mutation_bytes, bool)
        or slot1_custom_key_vault_mutation_bytes < 0
        or not isinstance(evf_finder_monitor_spoof_events, int)
        or isinstance(evf_finder_monitor_spoof_events, bool)
        or evf_finder_monitor_spoof_events < 0
    ):
        _add_code(codes, STATUS_BLOCKED_G100_TELEMETRY_INVALID)
        errors.append(
            "Invalid ILME-FX3 telemetry, firmware version, or negative counters in Gate G100."
        )

    norm_reset = _norm_reset_action_phase256(reset_action)
    if norm_reset is None:
        _add_code(codes, STATUS_BLOCKED_G100_CUSTOM_KEY_RESET_PERSISTENCE_VIOLATION)
        errors.append(f"Unsupported reset_action={reset_action!r} in Gate G100.")

    norm_log = _norm_log_shooting_mode_g100(log_shooting_mode)
    norm_my_dial = _norm_my_dial_slot_g100(active_my_dial_slot)
    norm_recall_hold = _norm_recall_custom_hold_slot_g100(
        active_recall_custom_hold_slot
    )

    if (
        custom_key_dial_menu_path != CUSTOM_KEY_DIAL_MENU_PATH_G100
        or tuple(supported_domains) != ALLOWED_CUSTOM_KEY_DOMAINS_G100
        or norm_log is None
        or norm_my_dial is None
        or norm_recall_hold is None
    ):
        _add_code(codes, STATUS_BLOCKED_G100_CUSTOM_KEY_DIAL_DOMAIN_OR_ISO_EI_MISMATCH)
        errors.append(
            "Invalid [Custom Key/Dial Set.] menu path, 3-domain catalog, log mode, or My Dial/Recall Hold slot."
        )

    state = resolve_fx3_custom_key_dial_and_remain_shoot_state(
        pre_reset_dial_assignments=pre_reset_dial_assignments,
        still_custom_keymap=still_custom_keymap,
        movie_custom_keymap=movie_custom_keymap,
        playback_custom_keymap=playback_custom_keymap,
        log_shooting_mode=norm_log or "Cine EI",
        pre_reset_remain_shoot_display=pre_reset_remain_shoot_display,
        reset_action=norm_reset or RESET_ACTION_NONE,
    )

    # Validate dial keys & forbid [Follow Custom] in Still or Playback domains
    allowed_dial_keys = set(CINEMA_LINE_FACTORY_DIAL_DEFAULTS_G100.keys())
    if set(state["pre_reset_dial_assignments"].keys()) != allowed_dial_keys or any(
        not str(v).strip() for v in state["pre_reset_dial_assignments"].values()
    ):
        _add_code(codes, STATUS_BLOCKED_G100_CUSTOM_KEY_DIAL_DOMAIN_OR_ISO_EI_MISMATCH)
        errors.append(
            f"Dial assignments must cover exact Cinema-Line dials {sorted(allowed_dial_keys)}."
        )

    if any(
        v == CUSTOM_KEY_FOLLOW_CUSTOM_TOKEN_G100
        for v in state["expected_post_reset_still_keymap"].values()
    ) or any(
        v == CUSTOM_KEY_FOLLOW_CUSTOM_TOKEN_G100
        for v in state["expected_post_reset_playback_keymap"].values()
    ):
        _add_code(codes, STATUS_BLOCKED_G100_CUSTOM_KEY_DIAL_DOMAIN_OR_ISO_EI_MISMATCH)
        errors.append(
            "[Follow Custom] is valid only in Movie domain (inheriting Still), not Still/Playback."
        )

    exp_rear_target = state["effective_rear_dial_target"]
    if observed_rear_dial_target is not None:
        norm_obs_rear = _norm_rear_dial_target_g100(observed_rear_dial_target)
        if norm_obs_rear != exp_rear_target:
            _add_code(
                codes, STATUS_BLOCKED_G100_CUSTOM_KEY_DIAL_DOMAIN_OR_ISO_EI_MISMATCH
            )
            errors.append(
                f"Rear dial ISO/EI auto-adaptation mismatch under {norm_log}: "
                f"observed={observed_rear_dial_target!r}, expected={exp_rear_target!r}."
            )

    if observed_resolved_movie_keymap is not None:
        for ctrl, obs_fn in observed_resolved_movie_keymap.items():
            exp_fn = state["resolved_movie_custom_keymap"].get(ctrl)
            if exp_fn != obs_fn:
                _add_code(
                    codes, STATUS_BLOCKED_G100_CUSTOM_KEY_DIAL_DOMAIN_OR_ISO_EI_MISMATCH
                )
                errors.append(
                    f"[Follow Custom] Movie inheritance mismatch for {ctrl}: "
                    f"observed={obs_fn!r}, expected={exp_fn!r}."
                )

    # Custom Key/Dial Reset Survival
    expected_dials: Dict[str, str] = state["expected_post_reset_dial_assignments"]
    effective_dials = dict(expected_dials)
    if observed_post_reset_dial_assignments is not None:
        effective_dials = {
            str(k): str(v) for k, v in observed_post_reset_dial_assignments.items()
        }
        if effective_dials != expected_dials:
            _add_code(codes, STATUS_BLOCKED_G100_CUSTOM_KEY_RESET_PERSISTENCE_VIOLATION)
            errors.append(
                f"Post-reset [Custom Key/Dial Set.] dial drift under {norm_reset}: "
                f"observed={effective_dials!r}, expected={expected_dials!r}."
            )

    if observed_post_reset_custom_keys_preserved is not None:
        expected_preserved = norm_reset != RESET_ACTION_INITIALIZE
        if bool(observed_post_reset_custom_keys_preserved) != expected_preserved:
            _add_code(codes, STATUS_BLOCKED_G100_CUSTOM_KEY_RESET_PERSISTENCE_VIOLATION)
            errors.append(
                f"Post-reset custom key persistence flag mismatch under {norm_reset}: "
                f"observed={observed_post_reset_custom_keys_preserved!r}, expected={expected_preserved!r}."
            )

    # Slot-1 Tier-0 CAMSET01.DAT O_RDONLY Load-Only Firewall
    norm_camset_fn = _norm_camset_filename_g100(slot1_camset_filename)
    norm_camset_op = _norm_camset_op_g100(slot1_camset_operation)
    write_flag_mask = (
        getattr(os, "O_WRONLY", 1)
        | getattr(os, "O_RDWR", 2)
        | getattr(os, "O_CREAT", 0)
        | getattr(os, "O_TRUNC", 0)
        | getattr(os, "O_APPEND", 0)
    )
    open_is_rdonly = (
        isinstance(slot1_open_flags, int)
        and not isinstance(slot1_open_flags, bool)
        and (slot1_open_flags & write_flag_mask) == 0
    )

    if (
        norm_camset_fn is None
        or norm_camset_op is None
        or camset_source_body_model != FX3_MODEL_NAME
        or not open_is_rdonly
        or slot1_custom_key_vault_mutation_bytes > 0
        or (
            tier0_vault_protection_active
            and norm_camset_op == CAMSET_OP_SAVE_OVERWRITE_G100
        )
    ):
        _add_code(
            codes, STATUS_BLOCKED_G100_SLOT1_CUSTOM_KEY_CAMSET01_FIREWALL_VIOLATION
        )
        errors.append(
            "Slot-1 Tier-0 CAMSET01.DAT O_RDONLY load-only firewall violated in Gate G100."
        )

    # [Remain Shoot Display] Scope & Reset Survival
    norm_remain_pre = _norm_remain_shoot_display_g100(pre_reset_remain_shoot_display)
    expected_remain = state["expected_post_reset_remain_shoot_display"]
    effective_remain = expected_remain
    if (
        remain_shoot_display_menu_path != REMAIN_SHOOT_DISPLAY_MENU_PATH_G100
        or norm_remain_pre is None
        or remain_shoot_scope != REMAIN_SHOOT_SCOPE_STILL_BUFFER_ONLY_G100
        or bool(displays_movie_card_remaining_time)
    ):
        _add_code(
            codes,
            STATUS_BLOCKED_G100_REMAIN_SHOOT_SCOPE_OR_RESET_PERSISTENCE_VIOLATION,
        )
        errors.append(
            "[Remain Shoot Display] violated menu path, option enum, or still-buffer-only scope."
        )

    if observed_post_reset_remain_shoot_display is not None:
        obs_rem = _norm_remain_shoot_display_g100(
            observed_post_reset_remain_shoot_display
        )
        effective_remain = obs_rem or str(observed_post_reset_remain_shoot_display)
        if obs_rem is None or obs_rem != expected_remain:
            _add_code(
                codes,
                STATUS_BLOCKED_G100_REMAIN_SHOOT_SCOPE_OR_RESET_PERSISTENCE_VIOLATION,
            )
            errors.append(
                f"Post-reset [Remain Shoot Display] mismatch under {norm_reset}: "
                f"observed={observed_post_reset_remain_shoot_display!r}, expected={expected_remain!r}."
            )

    # EVF-Less ILME-FX3 (ilc/2210) Monitor Topology Guard
    spoof_count = max(0, int(evf_finder_monitor_spoof_events))
    if (
        bool(claimed_builtin_evf)
        or bool(finder_monitor_switch_present)
        or bool(evf_eye_sensor_present)
        or active_display_surface != FX3_ACTIVE_DISPLAY_SURFACE_LCD_G100
    ):
        spoof_count += 1
        _add_code(
            codes, STATUS_BLOCKED_G100_EVF_FINDER_MONITOR_TOPOLOGY_SPOOF_VIOLATION
        )
        errors.append(
            "EVF-less ILME-FX3 (ilc/2210) monitor topology spoofed (built-in EVF / Finder-Monitor / eye sensor claimed)."
        )
    elif spoof_count > 0:
        _add_code(
            codes, STATUS_BLOCKED_G100_EVF_FINDER_MONITOR_TOPOLOGY_SPOOF_VIOLATION
        )
        errors.append(
            f"Non-zero evf_finder_monitor_spoof_events={spoof_count} reported in Gate G100."
        )

    valid = len(codes) == 0
    status = STATUS_VERIFIED_G100 if valid else codes[0]

    return CustomKeyDialAndRemainShootGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=body_model_name,
        body_model_id_hex=(
            f"0x{body_model_id:08x}"
            if isinstance(body_model_id, int) and not isinstance(body_model_id, bool)
            else "INVALID"
        ),
        help_guide_code=help_guide_code,
        firmware_version=str(firmware_version),
        custom_key_dial_menu_path=custom_key_dial_menu_path,
        supported_domains=tuple(supported_domains),
        factory_dial_defaults=dict(CINEMA_LINE_FACTORY_DIAL_DEFAULTS_G100),
        pre_reset_dial_assignments=state["pre_reset_dial_assignments"],
        reset_action=norm_reset or str(reset_action),
        effective_post_reset_dial_assignments=effective_dials,
        log_shooting_mode=norm_log or str(log_shooting_mode),
        effective_rear_dial_target=exp_rear_target,
        still_custom_keymap=state["expected_post_reset_still_keymap"],
        movie_custom_keymap=state["expected_post_reset_movie_keymap"],
        resolved_movie_custom_keymap=state["resolved_movie_custom_keymap"],
        playback_custom_keymap=state["expected_post_reset_playback_keymap"],
        follow_custom_inherited_controls=state["follow_custom_inherited_controls"],
        active_my_dial_slot=norm_my_dial or str(active_my_dial_slot),
        active_recall_custom_hold_slot=(
            norm_recall_hold or str(active_recall_custom_hold_slot)
        ),
        custom_key_survives_camera_settings_reset=True,
        custom_key_survives_reset_network_set=True,
        custom_key_reset_only_by_initialize=True,
        tier0_vault_protection_active=bool(tier0_vault_protection_active),
        slot1_camset_filename=norm_camset_fn or str(slot1_camset_filename),
        slot1_camset_operation=norm_camset_op or str(slot1_camset_operation),
        slot1_open_flags_o_rdonly=open_is_rdonly,
        camset_source_body_model=camset_source_body_model,
        slot1_custom_key_vault_mutation_bytes=max(
            0, int(slot1_custom_key_vault_mutation_bytes)
        )
        if isinstance(slot1_custom_key_vault_mutation_bytes, int)
        and not isinstance(slot1_custom_key_vault_mutation_bytes, bool)
        else -1,
        remain_shoot_display_menu_path=remain_shoot_display_menu_path,
        remain_shoot_factory_default=REMAIN_SHOOT_FACTORY_DEFAULT_G100,
        pre_reset_remain_shoot_display=(
            norm_remain_pre or str(pre_reset_remain_shoot_display)
        ),
        effective_post_reset_remain_shoot_display=effective_remain,
        remain_shoot_scope=remain_shoot_scope,
        displays_movie_card_remaining_time=bool(displays_movie_card_remaining_time),
        remain_shoot_survives_camera_settings_reset=True,
        remain_shoot_survives_reset_network_set=True,
        remain_shoot_reset_only_by_initialize=True,
        fx3_has_builtin_evf=FX3_HAS_BUILTIN_EVF_G100,
        finder_monitor_switch_present=bool(finder_monitor_switch_present),
        evf_eye_sensor_present=bool(evf_eye_sensor_present),
        active_display_surface=active_display_surface,
        evf_finder_monitor_spoof_events=spoof_count,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g100_custom_key_dial_and_remain_shoot_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    custom_key_remain_shoot_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase256DonorAuditResult] = None,
) -> Tuple[GateVerdict, G100CustomKeyDialAndRemainShootGuardResult]:
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase256_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_custom_key_dial_iso_ei_and_remain_shoot_guard(
        **dict(custom_key_remain_shoot_kwargs or {})
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
        errors.append("Persistent eMMC write authorization requested in Gate G100.")
    if not audit.valid:
        _add_code(codes, audit.status)
    for c in guard.violation_codes:
        _add_code(codes, c)

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G100 if valid else codes[0]

    res = G100CustomKeyDialAndRemainShootGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        custom_key_remain_shoot_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, rear_dial={guard.effective_rear_dial_target}"
        f"(log={guard.log_shooting_mode},mut_bytes={guard.slot1_custom_key_vault_mutation_bytes}), "
        f"remain_shoot={guard.effective_post_reset_remain_shoot_display}"
        f"(evf={guard.fx3_has_builtin_evf},spoof={guard.evf_finder_monitor_spoof_events})"
    )
    verdict = GateVerdict(
        gate_id=G100_GATE_ID,
        gate_code=G100_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 4. Unified `100`-Gate Grand Milestone Safety Preflight (`G01..G100`)
# ---------------------------------------------------------------------------


def evaluate_100gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    dry_run_simulated_backup: Optional[bool] = None,
    simulate_bench_dry_run: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    request_persistent_emmc_writes: bool = False,
    diff_set_still_mv_kwargs: Optional[Mapping[str, Any]] = None,
    custom_key_remain_shoot_kwargs: Optional[Mapping[str, Any]] = None,
    master_98_override: Optional[Master98GateReport] = None,
    **m98_passthrough_kwargs: Any,
) -> Master100GateReport:
    """Evaluate all 100 Master Safety Gates (`G01..G100`) deterministically by
    delegating `G01..G98` directly to `evaluate_98gate_preflight()`.
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

    m98_report: Master98GateReport = (
        master_98_override
        if master_98_override is not None
        else evaluate_98gate_preflight(
            resolved_root,
            force_clean_room=clean_forced,
            dry_run_simulated=effective_dry_run,
            include_large_binaries=include_large_binaries,
            work_root=work_root,
            request_persistent_emmc_writes=request_persistent_emmc_writes,
            **m98_passthrough_kwargs,
        )
    )

    phase256_audit = audit_phase256_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
    )

    g99_verdict, g99_res = evaluate_g99_diff_set_still_mv_and_shutter_angle_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        diff_set_still_mv_kwargs=diff_set_still_mv_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase256_audit,
    )

    g100_verdict, g100_res = evaluate_g100_custom_key_dial_and_remain_shoot_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        custom_key_remain_shoot_kwargs=custom_key_remain_shoot_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase256_audit,
    )

    gates_99_to_100 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g99_verdict, g100_verdict)
    ]
    all_gates = tuple(list(m98_report.gates) + gates_99_to_100)

    g01_to_g12_verified = int(m98_report.summary["g01_to_g12_verified"])
    g13_to_g98_verified = int(m98_report.summary["g13_to_g96_verified"]) + int(
        m98_report.summary["g97_to_g98_verified"]
    )
    g99_to_g100_verified = sum(1 for v in (g99_verdict, g100_verdict) if v.passed)
    total_verified = g01_to_g12_verified + g13_to_g98_verified + g99_to_g100_verified

    g99_to_g100_all_passed = g99_to_g100_verified == 2
    g13_to_g100_all_passed = m98_report.g13_to_g98_all_passed and g99_to_g100_all_passed
    g01_to_g09_ok = all(bool(g["passed"]) for g in m98_report.gates[:9])

    offline_97_verified = (
        g01_to_g09_ok
        and m98_report.offline_95_gates_verified
        and g99_to_g100_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_100_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g100_all_passed
        and (not request_persistent_emmc_writes)
    )

    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m98_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_97_verified
        and m98_report.h0_h1_trial_entry_allowed
        and g99_to_g100_all_passed
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
        list(m98_report.errors) + list(g99_verdict.errors) + list(g100_verdict.errors)
    )
    warnings: List[str] = (
        list(m98_report.warnings)
        + list(g99_verdict.warnings)
        + list(g100_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m98_report.g13_to_g98_all_passed:
        overall_status = m98_report.status
    elif not g99_verdict.passed:
        overall_status = g99_verdict.status
    elif not g100_verdict.passed:
        overall_status = g100_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_100_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_100_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_100_verified:
        overall_status = "VERIFIED_ALL_100_GATES"
    else:
        overall_status = "VERIFIED_97_OF_100_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m98_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g99_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g100_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 100,
        "verified_gates": total_verified,
        "technical_gates_passed": total_verified,
        "blocked_or_pending_gates": 100 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g98_verified": g13_to_g98_verified,
        "g99_to_g100_verified": g99_to_g100_verified,
        "g13_to_g100_all_passed": g13_to_g100_all_passed,
        "g99_to_g100_all_passed": g99_to_g100_all_passed,
        "offline_97_gates_verified": offline_97_verified,
        "all_100_gates_verified": all_100_verified,
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

    return Master100GateReport(
        schema=REALHW_DIFF_SET_STILL_MV_CUSTOM_KEY_REMAIN_SHOOT_100GATE_SCHEMA,
        version=REALHW_DIFF_SET_STILL_MV_CUSTOM_KEY_REMAIN_SHOOT_100GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        offline_97_gates_verified=offline_97_verified,
        all_100_gates_verified=all_100_verified,
        g13_to_g100_all_passed=g13_to_g100_all_passed,
        g99_to_g100_all_passed=g99_to_g100_all_passed,
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
        master_98_report=m98_report.to_dict(),
        g99_result=g99_res.to_dict(),
        g100_result=g100_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_100_master_safety_gates = evaluate_100gate_preflight
run_100_gate_preflight = evaluate_100gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_diff_set_still_mv_custom_key_remain_shoot_and_100gate_guard",
        description=(
            "Phase 256 Grand Milestone Safety Gates G99 (Different Set for Still/Mv "
            "8-Item Transitions & Shutter Angle Override Guard) + G100 (100th Gate: "
            "Custom Key/Dial Set. ISO/EI Firewall & Remain Shoot EVF-Less Guard) "
            "+ Unified 100-Gate Master Safety Preflight"
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

    report = evaluate_100gate_preflight(
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
            f"verified={report.summary['verified_gates']}/100 "
            f"g99_to_g100_all_passed={report.g99_to_g100_all_passed} "
            f"all_100_gates_verified={report.all_100_gates_verified} "
            f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach}\n"
        )
    ok = (
        report.all_100_gates_verified
        if args.dry_run_simulated
        else report.offline_97_gates_verified
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
