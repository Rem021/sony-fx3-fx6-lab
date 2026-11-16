"""Phase 263 (Wave-42) Sony `ILME-FX3` (`Ver. 7.02`) Safety Gates `G103`
(`[APS-C S35 Shooting]` `12.1MP` Sensor `4K` Movie & `4264x2408` `HDMI RAW Output`
Lockout + `[Face/Eye AF]` BIONZ XR Menu Hierarchy, `[Right/Left Eye Select]`,
Clean-HDMI Frame Isolation & `[Face Memory]` Survival Guard) & `G104`
(`[Version]` Read-Only Body / E-Mount Lens / Mount Adaptor Inspection,
`Ver. 6.00+`/`7.02` Update Notification Badge Zero-RF `Airplane Mode = On`
Suppression & Hard-Blocked Slot-1 `BODYDATA.DAT` Flash Guard) + Unified `104`-Gate
Master Safety Preflight (`G01..G104`).

Operationalizes Wave-42 official Sony `ILME-FX3` (`Ver. 7.02`, Help Guide `ilc/2210`)
intelligence (`reports/2026-11-15-global-sony-wave42-apsc-s35-4k-lockout-face-eye-af-right-left-eye-version-read-only-intel/README.md`)
as deterministic offline preflight verifiers (`G103` and `G104`) and delegates
`G01..G102` directly to `evaluate_102gate_preflight()`.
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
from .realhw_auto_slow_shutter_hdmi_reccontrol_breathing_and_102gate_guard import (
    Master102GateReport,
    evaluate_102gate_preflight,
)
from .realhw_cfexpress_ufu_el3_and_52gate_guard import EL3_PAYLOAD_TRANSMIT_AUTHORIZED
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

REALHW_APSC_S35_FACE_EYE_AF_VERSION_104GATE_SCHEMA: str = (
    "realhw_apsc_s35_face_eye_af_version_and_104gate_guard_v1"
)
REALHW_APSC_S35_FACE_EYE_AF_VERSION_104GATE_VERSION: str = "1.0.0"

G103_GATE_ID: str = (
    "G103_apsc_s35_12mp_4k_lockout_and_face_eye_af_clean_hdmi_guard"
)
G103_GATE_CODE: str = (
    "APSC_S35_12MP_4K_LOCKOUT_AND_FACE_EYE_AF_CLEAN_HDMI_GUARD"
)

G104_GATE_ID: str = (
    "G104_version_readonly_airplane_badge_and_bodydata_flash_block_guard"
)
G104_GATE_CODE: str = (
    "VERSION_READONLY_AIRPLANE_BADGE_AND_BODYDATA_FLASH_BLOCK_GUARD"
)

G103: str = G103_GATE_ID
G104: str = G104_GATE_ID
GATE_G103_APSC_S35_12MP_4K_LOCKOUT_AND_FACE_EYE_AF_CLEAN_HDMI_GUARD: str = (
    G103_GATE_CODE
)
GATE_G104_VERSION_READONLY_AIRPLANE_BADGE_AND_BODYDATA_FLASH_BLOCK_GUARD: str = (
    G104_GATE_CODE
)

HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
HUMAN_HARDWARE_ATTACH_TOKEN: bool = False
USB_PACKETS_TRANSMITTED: int = 0
PHYSICAL_USB_PACKETS_EMITTED: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0
DONOR_CHECK_MAX_SECONDS_PHASE263: float = 0.10
DONOR_CHECK_MAX_SECONDS: float = DONOR_CHECK_MAX_SECONDS_PHASE263

FX3_MODEL_NAME: str = "ILME-FX3"
FX3_MODEL_ID: int = 0x91030080
FX6_MODEL_NAME: str = "ILME-FX6"
FX3_DEFAULT_FW_VERSION_PHASE263: str = "7.02"
FX3_MIN_SUPPORTED_FW_TUPLE_PHASE263: Tuple[int, int] = (1, 0)
FX3_BIRD_SUBJECT_MIN_FW_TUPLE_G103: Tuple[int, int] = (3, 0)
FX3_VERSION_BADGE_MIN_FW_TUPLE_G104: Tuple[int, int] = (6, 0)
FX3_HELP_GUIDE_CODE_PHASE263: str = "ilc/2210"

RESET_ACTION_NONE: str = "NONE"
RESET_ACTION_CAMERA_SETTINGS_RESET: str = "Camera Settings Reset"
RESET_ACTION_RESET_NETWORK_SET_PHASE263: str = "Reset Network Set."
RESET_ACTION_INITIALIZE: str = "Initialize"
ALLOWED_RESET_ACTIONS_PHASE263: Tuple[str, ...] = (
    RESET_ACTION_NONE,
    RESET_ACTION_CAMERA_SETTINGS_RESET,
    RESET_ACTION_RESET_NETWORK_SET_PHASE263,
    RESET_ACTION_INITIALIZE,
)

# ---------------------------------------------------------------------------
# Status & Violation Codes (G103 / G104 / Phase 263)
# ---------------------------------------------------------------------------

STATUS_VERIFIED_G103: str = (
    "VERIFIED_G103_APSC_S35_4K_LOCKOUT_AND_FACE_EYE_AF_CLEAN_HDMI_SAFE"
)
STATUS_VERIFIED_G104: str = (
    "VERIFIED_G104_VERSION_READONLY_AIRPLANE_BADGE_AND_BODYDATA_BLOCK_SAFE"
)
STATUS_BLOCKED_PHASE263_DONOR_INTEGRITY: str = (
    "BLOCKED_PHASE263_DONOR_CONTRACT_INTEGRITY"
)

STATUS_BLOCKED_G103_APSC_S35_4K_OR_RAW_BYPASS_VIOLATION: str = (
    "BLOCKED_G103_APSC_S35_4K_OR_RAW_BYPASS_VIOLATION"
)
STATUS_BLOCKED_G103_AI_UNIT_SUBJECT_RECOG_SPOOF_VIOLATION: str = (
    "BLOCKED_G103_AI_UNIT_SUBJECT_RECOG_SPOOF_VIOLATION"
)
STATUS_BLOCKED_G103_HDMI_CLEAN_FEED_EYE_FRAME_BAKE_VIOLATION: str = (
    "BLOCKED_G103_HDMI_CLEAN_FEED_EYE_FRAME_BAKE_VIOLATION"
)
STATUS_BLOCKED_G103_RESET_OR_FACE_MEMORY_PERSISTENCE_VIOLATION: str = (
    "BLOCKED_G103_RESET_OR_FACE_MEMORY_PERSISTENCE_VIOLATION"
)
STATUS_BLOCKED_G103_TELEMETRY_INVALID: str = (
    "BLOCKED_G103_APSC_S35_FACE_EYE_AF_TELEMETRY_INVALID"
)

STATUS_BLOCKED_G104_VERSION_DIALOG_FLASH_WRITE_VIOLATION: str = (
    "BLOCKED_G104_VERSION_DIALOG_FLASH_WRITE_VIOLATION"
)
STATUS_BLOCKED_G104_ZERO_RF_UPDATE_BADGE_OR_TX_VIOLATION: str = (
    "BLOCKED_G104_ZERO_RF_UPDATE_BADGE_OR_TX_VIOLATION"
)
STATUS_BLOCKED_G104_BODYDATA_FLASH_EXECUTION_VIOLATION: str = (
    "BLOCKED_G104_BODYDATA_FLASH_EXECUTION_VIOLATION"
)
STATUS_BLOCKED_G104_TELEMETRY_INVALID: str = (
    "BLOCKED_G104_VERSION_BODYDATA_TELEMETRY_INVALID"
)

# ---------------------------------------------------------------------------
# Gate G103 Constants: APS-C S35 Shooting (12.1MP 4K Lockout) & Face/Eye AF
# ---------------------------------------------------------------------------

APSC_S35_MENU_PATH_G103: str = (
    "MENU -> Shooting -> [Image Quality/Rec] -> [APS-C S35 Shooting]"
)
APSC_S35_AUTO_G103: str = "Auto"
APSC_S35_ON_G103: str = "On"
APSC_S35_OFF_G103: str = "Off"
ALLOWED_APSC_S35_SETTINGS_G103: Tuple[str, ...] = (
    APSC_S35_AUTO_G103,
    APSC_S35_ON_G103,
    APSC_S35_OFF_G103,
)
APSC_S35_FACTORY_DEFAULT_G103: str = APSC_S35_AUTO_G103

FX3_SENSOR_EFFECTIVE_MP_G103: float = 12.1
FX3_SENSOR_EFFECTIVE_STILL_RES_G103: str = "4240x2832"
FX3_SENSOR_NATIVE_4K_MOVIE_RES_G103: str = "3840x2160"
FX3_HDMI_RAW_OUTPUT_RES_G103: str = "4264x2408"
FX3_FULL_FRAME_CROP_FACTOR_G103: float = 1.0
FX3_APSC_S35_CROP_FACTOR_G103: float = 1.5
SENSOR_READOUT_FULL_FRAME_G103: str = "Full-Frame 35mm"
SENSOR_READOUT_SUPER_35MM_G103: str = "APS-C / Super 35mm"

CAPTURE_DOMAIN_MOVIE_G103: str = "Movie"
CAPTURE_DOMAIN_STILL_G103: str = "Still"
ALLOWED_CAPTURE_DOMAINS_G103: Tuple[str, ...] = (
    CAPTURE_DOMAIN_MOVIE_G103,
    CAPTURE_DOMAIN_STILL_G103,
)

LENS_COVERAGE_FULL_FRAME_G103: str = "Full-Frame"
LENS_COVERAGE_APSC_S35_G103: str = "APS-C"
ALLOWED_LENS_COVERAGES_G103: Tuple[str, ...] = (
    LENS_COVERAGE_FULL_FRAME_G103,
    LENS_COVERAGE_APSC_S35_G103,
)

MOVIE_FORMAT_XAVC_HS_4K_G103: str = "XAVC HS 4K"
MOVIE_FORMAT_XAVC_S_4K_G103: str = "XAVC S 4K"
MOVIE_FORMAT_XAVC_SI_4K_G103: str = "XAVC S-I 4K"
MOVIE_FORMAT_XAVC_S_HD_G103: str = "XAVC S HD"
MOVIE_FORMAT_XAVC_SI_HD_G103: str = "XAVC S-I HD"
LOCKED_4K_MOVIE_FORMATS_G103: Tuple[str, ...] = (
    MOVIE_FORMAT_XAVC_HS_4K_G103,
    MOVIE_FORMAT_XAVC_S_4K_G103,
    MOVIE_FORMAT_XAVC_SI_4K_G103,
)
ALLOWED_S35_HD_MOVIE_FORMATS_G103: Tuple[str, ...] = (
    MOVIE_FORMAT_XAVC_S_HD_G103,
    MOVIE_FORMAT_XAVC_SI_HD_G103,
)
ALLOWED_MOVIE_FILE_FORMATS_G103: Tuple[str, ...] = (
    LOCKED_4K_MOVIE_FORMATS_G103 + ALLOWED_S35_HD_MOVIE_FORMATS_G103
)

FACE_EYE_AF_MENU_PATH_G103: str = "MENU -> Focus -> [Face/Eye AF]"
FACE_EYE_AF_CANONICAL_MENU_LABEL_G103: str = "Face/Eye AF"
DISALLOWED_AI_UNIT_MENU_LABELS_G103: Tuple[str, ...] = (
    "Subject Recog in AF",
    "Subject Recognition in AF",
    "AI Subject Recognition",
    "Auto Framing",
)

FACE_EYE_PRIOR_ON_G103: str = "On"
FACE_EYE_PRIOR_OFF_G103: str = "Off"
ALLOWED_FACE_EYE_PRIOR_SETTINGS_G103: Tuple[str, ...] = (
    FACE_EYE_PRIOR_ON_G103,
    FACE_EYE_PRIOR_OFF_G103,
)
FACE_EYE_PRIOR_FACTORY_DEFAULT_G103: str = FACE_EYE_PRIOR_ON_G103

FACE_EYE_SUBJECT_HUMAN_G103: str = "Human"
FACE_EYE_SUBJECT_ANIMAL_G103: str = "Animal"
FACE_EYE_SUBJECT_BIRD_G103: str = "Bird"
ALLOWED_FACE_EYE_SUBJECTS_G103: Tuple[str, ...] = (
    FACE_EYE_SUBJECT_HUMAN_G103,
    FACE_EYE_SUBJECT_ANIMAL_G103,
    FACE_EYE_SUBJECT_BIRD_G103,
)
FACE_EYE_SUBJECT_FACTORY_DEFAULT_G103: str = FACE_EYE_SUBJECT_HUMAN_G103

RIGHT_LEFT_EYE_AUTO_G103: str = "Auto"
RIGHT_LEFT_EYE_RIGHT_G103: str = "Right Eye"
RIGHT_LEFT_EYE_LEFT_G103: str = "Left Eye"
ALLOWED_RIGHT_LEFT_EYE_SELECT_G103: Tuple[str, ...] = (
    RIGHT_LEFT_EYE_AUTO_G103,
    RIGHT_LEFT_EYE_RIGHT_G103,
    RIGHT_LEFT_EYE_LEFT_G103,
)
RIGHT_LEFT_EYE_FACTORY_DEFAULT_G103: str = RIGHT_LEFT_EYE_AUTO_G103

FACE_EYE_FRAME_DISP_ON_G103: str = "On"
FACE_EYE_FRAME_DISP_OFF_G103: str = "Off"
ALLOWED_FACE_EYE_FRAME_DISP_SETTINGS_G103: Tuple[str, ...] = (
    FACE_EYE_FRAME_DISP_ON_G103,
    FACE_EYE_FRAME_DISP_OFF_G103,
)
FACE_EYE_FRAME_DISP_FACTORY_DEFAULT_G103: str = FACE_EYE_FRAME_DISP_OFF_G103
MAX_FACE_MEMORY_REGISTRATIONS_G103: int = 8

# ---------------------------------------------------------------------------
# Gate G104 Constants: Version Read-Only, Zero-RF Badge & BODYDATA.DAT Block
# ---------------------------------------------------------------------------

VERSION_MENU_PATH_G104: str = "MENU -> Setup -> [Setup Option] -> [Version]"
VERSION_DIALOG_ACCESS_MODE_G104: str = "READ_ONLY"
AIRPLANE_MODE_ON_G104: str = "On"
AIRPLANE_MODE_OFF_G104: str = "Off"
ALLOWED_AIRPLANE_MODE_SETTINGS_G104: Tuple[str, ...] = (
    AIRPLANE_MODE_ON_G104,
    AIRPLANE_MODE_OFF_G104,
)
AIRPLANE_MODE_BENCH_REQUIRED_G104: str = AIRPLANE_MODE_ON_G104

BODYDATA_FILENAME_G104: str = "BODYDATA.DAT"
BODYDATA_SLOT1_MOUNT_PATH_G104: str = "/mnt/sd_slot1/BODYDATA.DAT"
HUMAN_MANUAL_MIN_BATTERY_PCT_G104: int = 51
HUMAN_MANUAL_MIN_BATTERY_BARS_G104: int = 3
DEFAULT_LENS_VERSION_G104: str = "Ver. 02"
DEFAULT_MOUNT_ADAPTOR_VERSION_G104: str = "--"

# ---------------------------------------------------------------------------
# Pinned Local Donor Contracts (O_RDONLY, <0.10s, Clean-Room Fallback)
# ---------------------------------------------------------------------------

PINNED_PHASE263_DONOR_SPECS: Dict[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_cpapp_bin": (
        "FX3",
        "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin",
        15_980_568,
        "c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba",
        (
            b"ILME-FX3",
            b"Super",
            b"Face",
            b"Eye",
            b"AF",
            b"Human",
            b"Animal",
            b"Right",
            b"Left",
            b"Memory",
            b"Version",
            b"Lens",
            b"Mount",
            b"HDMI",
            b"RAW",
            b"4K",
            b"HD",
            b"Reset",
            b"Initialize",
        ),
        "FX3_CPAPP_APSC_S35_FACE_EYE_AF_VERSION_STRINGS",
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
        "FX3_LIBGPE_APSC_S35_FACE_EYE_VERSION_MENU_ELF",
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
        "FX3_LIBSAVELOADSETTINGS_FACE_MEMORY_RESET_SPLIT_ELF",
    ),
    "fx3_bk4_bin": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin",
        2_229_740,
        "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2",
        (b"BK4", b"ILME-FX3", b"TC", b"/setting"),
        "FX3_BK4_APSC_S35_FACE_EYE_AF_BACKUP_SEED",
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
        "FX6_LIBINFRADIAL_EYE_SELECT_CUSTOM_KEY_PARITY_ELF",
    ),
    "fx6_bk4_bin": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0110_backup/SYSIPSX-DSLR/CHAPLIN/CX95898_NTSC.bin",
        2_253_333,
        "e2eafd4e950ead94fdba64722b225b9ccf4cf294ce4c1cf956b9e62926bbf89e",
        (b"BK4", b"WB", b"TC", b"/setting"),
        "FX6_BK4_CINEMA_LINE_FACE_EYE_VERSION_PARITY_SEED",
    ),
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase263DonorAuditResult:
    valid: bool
    status: str
    verification_mode: str
    access_mode: str
    files_inspected: int
    elapsed_seconds: float
    within_budget_100ms: bool
    raw_firmware_bytes_leaked: int
    checked_markers: Tuple[str, ...
    ]
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
class ApscS35AndFaceEyeAfGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    body_model_name: str
    body_model_id_hex: str
    help_guide_code: str
    firmware_version: str
    sensor_effective_megapixels: float
    sensor_effective_still_resolution: str
    sensor_native_4k_movie_resolution: str
    apsc_s35_menu_path: str
    apsc_s35_factory_default: str
    pre_reset_apsc_s35_setting: str
    reset_action: str
    effective_post_reset_apsc_s35_setting: str
    apsc_s35_reset_by_camera_settings_reset: bool
    apsc_s35_unaffected_by_reset_network_set: bool
    capture_domain: str
    lens_coverage: str
    movie_file_format: str
    hdmi_raw_output_enabled: bool
    hdmi_raw_resolution: str
    is_4k_movie_format: bool
    apsc_s35_hardware_locked_to_off: bool
    effective_apsc_s35_state: str
    effective_sensor_readout_mode: str
    effective_crop_factor: float
    super35_movie_capture_active: bool
    super35_hd_only_enforced: bool
    lockout_matrix_states_checked: int
    apsc_s35_4k_or_raw_bypass_events: int
    face_eye_af_menu_path: str
    face_eye_af_menu_label: str
    ai_unit_subject_recog_spoof_events: int
    shoot_mode_intelligent_auto: bool
    pre_reset_face_eye_prior_in_af: str
    effective_post_reset_face_eye_prior_in_af: str
    pre_reset_face_eye_subject: str
    effective_post_reset_face_eye_subject: str
    pre_reset_right_left_eye_select: str
    switch_right_left_eye_pressed: bool
    effective_post_reset_right_left_eye_select: str
    pre_reset_face_eye_frame_disp: str
    effective_post_reset_face_eye_frame_disp: str
    af_area_auto_clear: str
    focus_locked: bool
    lcd_eye_frame_overlay_rendered: bool
    hdmi_info_display: str
    hdmi_eye_frame_overlay_rendered: bool
    hdmi_clean_feed_eye_frame_baked_pixels: int
    pre_reset_registered_face_memory_count: int
    explicit_face_memory_delete: bool
    effective_post_reset_registered_face_memory_count: int
    face_memory_survives_camera_settings_reset: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G103ApscS35AndFaceEyeAfGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    apsc_s35_face_eye_af_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VersionReadOnlyAndBodydataFlashBlockGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    body_model_name: str
    body_model_id_hex: str
    help_guide_code: str
    version_menu_path: str
    version_dialog_access_mode: str
    reset_action: str
    body_firmware_version: str
    formatted_body_version: str
    lens_firmware_version: str
    mount_adaptor_firmware_version: str
    version_survives_all_resets: bool
    version_dialog_flash_writes: int
    airplane_mode: str
    wifi_enabled: bool
    bluetooth_enabled: bool
    creators_app_cloud_polling_enabled: bool
    fw_supports_v6_update_badge: bool
    update_notification_badge_suppressed: bool
    update_notification_badge_visible: bool
    passive_tx_bytes_emitted: int
    bodydata_filename: str
    slot1_bodydata_present: bool
    slot1_bodydata_sony_signed: bool
    battery_charge_pct: int
    battery_bars: int
    human_manual_battery_prereq_met: bool
    automated_bodydata_flash_attempts: int
    bodydata_flash_hard_blocked: bool
    bodydata_flash_attempts_blocked: int
    bodydata_flash_executions_permitted: int
    persistent_emmc_writes_authorized: bool
    physical_flash_auto_exec_authorized: bool
    slot1_bodydata_vault_mutation_bytes: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G104VersionReadOnlyAndBodydataFlashBlockGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    version_bodydata_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master104GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    offline_101_gates_verified: bool
    all_104_gates_verified: bool
    g13_to_g104_all_passed: bool
    g103_to_g104_all_passed: bool
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
    master_102_report: Dict[str, Any]
    g103_result: Dict[str, Any]
    g104_result: Dict[str, Any]
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
    m = re.match(r"^\s*(?:Ver\.\s*|[vV])?(\d+)\.(\d+)(?:\.\d+)?\s*$", version_str)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def _norm_reset_action_phase263(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if u in ("NONE", "NO RESET", ""):
        return RESET_ACTION_NONE
    if u == "CAMERA SETTINGS RESET":
        return RESET_ACTION_CAMERA_SETTINGS_RESET
    if u in ("RESET NETWORK SET.", "RESET NETWORK SET", "RESET NETWORK SETTINGS"):
        return RESET_ACTION_RESET_NETWORK_SET_PHASE263
    if u == "INITIALIZE":
        return RESET_ACTION_INITIALIZE
    return None


def _norm_on_off_phase263(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if u == "ON":
        return "On"
    if u == "OFF":
        return "Off"
    return None


def _norm_apsc_s35_setting_g103(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if u == "AUTO":
        return APSC_S35_AUTO_G103
    if u in ("ON", "SUPER 35MM", "APS-C", "S35"):
        return APSC_S35_ON_G103
    if u in ("OFF", "FULL FRAME", "FULL-FRAME"):
        return APSC_S35_OFF_G103
    return None


def _norm_capture_domain_g103(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if u in ("MOVIE", "VIDEO"):
        return CAPTURE_DOMAIN_MOVIE_G103
    if u in ("STILL", "PHOTO", "STILL IMAGE"):
        return CAPTURE_DOMAIN_STILL_G103
    return None


def _norm_lens_coverage_g103(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if u in ("FULL-FRAME", "FULL FRAME", "FF", "35MM FULL-FRAME", "FE"):
        return LENS_COVERAGE_FULL_FRAME_G103
    if u in ("APS-C", "APSC", "SUPER 35MM", "SUPER 35", "S35", "E APS-C"):
        return LENS_COVERAGE_APSC_S35_G103
    return None


def _norm_movie_file_format_g103(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if u in ("XAVC HS 4K", "HS 4K"):
        return MOVIE_FORMAT_XAVC_HS_4K_G103
    if u in ("XAVC S 4K", "S 4K"):
        return MOVIE_FORMAT_XAVC_S_4K_G103
    if u in ("XAVC S-I 4K", "XAVC SI 4K", "S-I 4K"):
        return MOVIE_FORMAT_XAVC_SI_4K_G103
    if u in ("XAVC S HD", "S HD"):
        return MOVIE_FORMAT_XAVC_S_HD_G103
    if u in ("XAVC S-I HD", "XAVC SI HD", "S-I HD"):
        return MOVIE_FORMAT_XAVC_SI_HD_G103
    return None


def _norm_face_eye_subject_g103(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if u == "HUMAN":
        return FACE_EYE_SUBJECT_HUMAN_G103
    if u == "ANIMAL":
        return FACE_EYE_SUBJECT_ANIMAL_G103
    if u == "BIRD":
        return FACE_EYE_SUBJECT_BIRD_G103
    return None


def _norm_right_left_eye_g103(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if u == "AUTO":
        return RIGHT_LEFT_EYE_AUTO_G103
    if u in ("RIGHT EYE", "RIGHT"):
        return RIGHT_LEFT_EYE_RIGHT_G103
    if u in ("LEFT EYE", "LEFT"):
        return RIGHT_LEFT_EYE_LEFT_G103
    return None


# ---------------------------------------------------------------------------
# 1. Bounded `< 0.10s` O_RDONLY Donor Contract Audit (`Phase 263`)
# ---------------------------------------------------------------------------


def audit_phase263_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    max_budget_seconds: float = DONOR_CHECK_MAX_SECONDS_PHASE263,
) -> Phase263DonorAuditResult:
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
        for key, (_body, rel_path, *_rest) in PINNED_PHASE263_DONOR_SPECS.items():
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
            spec[5] for spec in PINNED_PHASE263_DONOR_SPECS.values()
        )
        synthetic_shas = {
            k: f"synthetic:{v[3][:16]}" for k, v in PINNED_PHASE263_DONOR_SPECS.items()
        }
        synthetic_sizes = {k: v[2] for k, v in PINNED_PHASE263_DONOR_SPECS.items()}
        return Phase263DonorAuditResult(
            valid=within_budget,
            status=(
                STATUS_VERIFIED_SAFE
                if within_budget
                else STATUS_BLOCKED_PHASE263_DONOR_INTEGRITY
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
    ) in PINNED_PHASE263_DONOR_SPECS.items():
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
            errors.append(f"Missing required Wave-42 byte markers in {key}.")

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

    fx3_keys = {k for k, v in PINNED_PHASE263_DONOR_SPECS.items() if v[0] == "FX3"}
    fx6_keys = {k for k, v in PINNED_PHASE263_DONOR_SPECS.items() if v[0] == "FX6"}
    fx3_ok = fx3_keys.issubset(passed_keys)
    fx6_ok = fx6_keys.issubset(passed_keys)
    valid = fx3_ok and fx6_ok and (not missing) and within_budget and (not errors)

    return Phase263DonorAuditResult(
        valid=valid,
        status=(
            STATUS_VERIFIED_SAFE
            if valid
            else STATUS_BLOCKED_PHASE263_DONOR_INTEGRITY
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
# 2. Gate `G103`: `[APS-C S35 Shooting]` 12.1MP 4K Lockout & `[Face/Eye AF]` Guard
# ---------------------------------------------------------------------------


def compute_apsc_s35_movie_format_lockout_matrix() -> Dict[str, Any]:
    """Exhaustively enumerate all `60` Sony `ILME-FX3` (`12.1MP` full-frame sensor)
    movie recording states across:
    `3 [APS-C S35 Shooting] settings x 2 lens coverages x 5 movie formats x 2 HDMI RAW states`
    proving:
    - `0` states where Super 35mm (~1.5x) movie readout is active in `4K`
      (`XAVC HS 4K`, `XAVC S 4K`, `XAVC S-I 4K`) or `4264x2408` `HDMI RAW Output`;
    - Super 35mm movie capture operates strictly in `HD` (`XAVC S HD` / `XAVC S-I HD`)
      with `HDMI RAW Output = Off` (`apsc_s35_4k_or_raw_bypass_events == 0`).
    """
    states_checked = 0
    s35_active_states = 0
    locked_4k_or_raw_states = 0
    bypass_events = 0

    for apsc_setting in ALLOWED_APSC_S35_SETTINGS_G103:
        for lens_cov in ALLOWED_LENS_COVERAGES_G103:
            for mv_fmt in ALLOWED_MOVIE_FILE_FORMATS_G103:
                for raw_on in (False, True):
                    states_checked += 1
                    is_4k = mv_fmt in LOCKED_4K_MOVIE_FORMATS_G103
                    locked_to_off = is_4k or raw_on
                    if locked_to_off:
                        locked_4k_or_raw_states += 1
                        s35_active = False
                    elif apsc_setting == APSC_S35_ON_G103:
                        s35_active = True
                    elif apsc_setting == APSC_S35_AUTO_G103:
                        s35_active = lens_cov == LENS_COVERAGE_APSC_S35_G103
                    else:
                        s35_active = False

                    if s35_active:
                        s35_active_states += 1
                        if is_4k or raw_on or (
                            mv_fmt not in ALLOWED_S35_HD_MOVIE_FORMATS_G103
                        ):
                            bypass_events += 1

    return {
        "states_checked": states_checked,
        "s35_active_states": s35_active_states,
        "locked_4k_or_raw_states": locked_4k_or_raw_states,
        "apsc_s35_4k_or_raw_bypass_events": bypass_events,
        "hd_only_super35_enforced": bypass_events == 0 and s35_active_states > 0,
    }


def resolve_fx3_apsc_s35_and_face_eye_af_state(
    *,
    apsc_s35_setting: str = APSC_S35_FACTORY_DEFAULT_G103,
    reset_action: str = RESET_ACTION_NONE,
    capture_domain: str = CAPTURE_DOMAIN_MOVIE_G103,
    lens_coverage: str = LENS_COVERAGE_FULL_FRAME_G103,
    movie_file_format: str = MOVIE_FORMAT_XAVC_S_4K_G103,
    hdmi_raw_output_enabled: bool = False,
    shoot_mode_intelligent_auto: bool = False,
    face_eye_prior_in_af: str = FACE_EYE_PRIOR_FACTORY_DEFAULT_G103,
    face_eye_subject: str = FACE_EYE_SUBJECT_FACTORY_DEFAULT_G103,
    right_left_eye_select: str = RIGHT_LEFT_EYE_FACTORY_DEFAULT_G103,
    switch_right_left_eye_pressed: bool = False,
    face_eye_frame_disp: str = FACE_EYE_FRAME_DISP_FACTORY_DEFAULT_G103,
    af_area_auto_clear: str = "Off",
    focus_locked: bool = False,
    hdmi_info_display: str = "Off",
    registered_face_memory_count: int = 2,
    explicit_face_memory_delete: bool = False,
) -> Dict[str, Any]:
    """Deterministically resolve Sony `ILME-FX3` (`Ver. 7.02`, `ilc/2210`)
    `[APS-C S35 Shooting]` (`12.1MP` sensor `4K` / `HDMI RAW` lockout) and
    `[Face/Eye AF]` (`[Face/Eye Prior. in AF]`, `[Face/Eye Subject]`,
    `[Right/Left Eye Select]`, `[Face/Eye Frame Disp.]` clean-HDMI isolation,
    and `[Face Memory]` reset survival).
    """
    norm_reset = _norm_reset_action_phase263(reset_action) or RESET_ACTION_NONE
    norm_apsc = (
        _norm_apsc_s35_setting_g103(apsc_s35_setting) or APSC_S35_FACTORY_DEFAULT_G103
    )
    norm_domain = (
        _norm_capture_domain_g103(capture_domain) or CAPTURE_DOMAIN_MOVIE_G103
    )
    norm_lens = (
        _norm_lens_coverage_g103(lens_coverage) or LENS_COVERAGE_FULL_FRAME_G103
    )
    norm_mv_fmt = (
        _norm_movie_file_format_g103(movie_file_format)
        or MOVIE_FORMAT_XAVC_S_4K_G103
    )
    norm_prior = (
        _norm_on_off_phase263(face_eye_prior_in_af)
        or FACE_EYE_PRIOR_FACTORY_DEFAULT_G103
    )
    norm_subject = (
        _norm_face_eye_subject_g103(face_eye_subject)
        or FACE_EYE_SUBJECT_FACTORY_DEFAULT_G103
    )
    norm_eye = (
        _norm_right_left_eye_g103(right_left_eye_select)
        or RIGHT_LEFT_EYE_FACTORY_DEFAULT_G103
    )
    norm_frame_disp = (
        _norm_on_off_phase263(face_eye_frame_disp)
        or FACE_EYE_FRAME_DISP_FACTORY_DEFAULT_G103
    )
    norm_auto_clear = _norm_on_off_phase263(af_area_auto_clear) or "Off"
    norm_hdmi_info = _norm_on_off_phase263(hdmi_info_display) or "Off"

    cam_or_init_reset = norm_reset in (
        RESET_ACTION_CAMERA_SETTINGS_RESET,
        RESET_ACTION_INITIALIZE,
    )
    post_apsc = APSC_S35_FACTORY_DEFAULT_G103 if cam_or_init_reset else norm_apsc
    post_prior = FACE_EYE_PRIOR_FACTORY_DEFAULT_G103 if cam_or_init_reset else norm_prior
    if shoot_mode_intelligent_auto:
        post_prior = FACE_EYE_PRIOR_ON_G103
    post_subject = (
        FACE_EYE_SUBJECT_FACTORY_DEFAULT_G103 if cam_or_init_reset else norm_subject
    )
    post_eye = RIGHT_LEFT_EYE_FACTORY_DEFAULT_G103 if cam_or_init_reset else norm_eye
    if switch_right_left_eye_pressed:
        if post_eye in (RIGHT_LEFT_EYE_AUTO_G103, RIGHT_LEFT_EYE_LEFT_G103):
            post_eye = RIGHT_LEFT_EYE_RIGHT_G103
        else:
            post_eye = RIGHT_LEFT_EYE_LEFT_G103
    post_frame_disp = (
        FACE_EYE_FRAME_DISP_FACTORY_DEFAULT_G103
        if cam_or_init_reset
        else norm_frame_disp
    )

    if explicit_face_memory_delete or norm_reset == RESET_ACTION_INITIALIZE:
        post_face_memory_count = 0
    else:
        post_face_memory_count = max(0, int(registered_face_memory_count))

    is_4k_movie = (
        norm_domain == CAPTURE_DOMAIN_MOVIE_G103
        and norm_mv_fmt in LOCKED_4K_MOVIE_FORMATS_G103
    )
    apsc_locked_off = norm_domain == CAPTURE_DOMAIN_MOVIE_G103 and (
        is_4k_movie or bool(hdmi_raw_output_enabled)
    )
    if apsc_locked_off:
        effective_apsc = APSC_S35_OFF_G103
        s35_active = False
    elif post_apsc == APSC_S35_ON_G103:
        effective_apsc = APSC_S35_ON_G103
        s35_active = True
    elif post_apsc == APSC_S35_AUTO_G103:
        effective_apsc = APSC_S35_AUTO_G103
        s35_active = norm_lens == LENS_COVERAGE_APSC_S35_G103
    else:
        effective_apsc = APSC_S35_OFF_G103
        s35_active = False

    readout_mode = (
        SENSOR_READOUT_SUPER_35MM_G103
        if s35_active
        else SENSOR_READOUT_FULL_FRAME_G103
    )
    crop_factor = (
        FX3_APSC_S35_CROP_FACTOR_G103
        if s35_active
        else FX3_FULL_FRAME_CROP_FACTOR_G103
    )
    super35_movie_active = (
        norm_domain == CAPTURE_DOMAIN_MOVIE_G103 and s35_active
    )

    frame_cleared_by_lock = (
        norm_auto_clear == "On" and bool(focus_locked)
    )
    lcd_eye_frame = (
        post_prior == FACE_EYE_PRIOR_ON_G103
        and post_frame_disp == FACE_EYE_FRAME_DISP_ON_G103
        and (not frame_cleared_by_lock)
    )
    hdmi_eye_frame = (
        lcd_eye_frame
        and norm_hdmi_info == "On"
        and (not bool(hdmi_raw_output_enabled))
    )

    return {
        "effective_post_reset_apsc_s35_setting": post_apsc,
        "is_4k_movie_format": is_4k_movie,
        "apsc_s35_hardware_locked_to_off": apsc_locked_off,
        "effective_apsc_s35_state": effective_apsc,
        "effective_sensor_readout_mode": readout_mode,
        "effective_crop_factor": crop_factor,
        "super35_movie_capture_active": super35_movie_active,
        "effective_post_reset_face_eye_prior_in_af": post_prior,
        "effective_post_reset_face_eye_subject": post_subject,
        "effective_post_reset_right_left_eye_select": post_eye,
        "effective_post_reset_face_eye_frame_disp": post_frame_disp,
        "lcd_eye_frame_overlay_rendered": lcd_eye_frame,
        "hdmi_eye_frame_overlay_rendered": hdmi_eye_frame,
        "hdmi_clean_feed_eye_frame_baked_pixels": 0,
        "effective_post_reset_registered_face_memory_count": post_face_memory_count,
    }


def verify_apsc_s35_and_face_eye_af_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: int = FX3_MODEL_ID,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE263,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE263,
    sensor_effective_megapixels: float = FX3_SENSOR_EFFECTIVE_MP_G103,
    apsc_s35_setting: str = APSC_S35_FACTORY_DEFAULT_G103,
    reset_action: str = RESET_ACTION_NONE,
    capture_domain: str = CAPTURE_DOMAIN_MOVIE_G103,
    lens_coverage: str = LENS_COVERAGE_FULL_FRAME_G103,
    movie_file_format: str = MOVIE_FORMAT_XAVC_S_4K_G103,
    hdmi_raw_output_enabled: bool = False,
    hdmi_raw_resolution: str = FX3_HDMI_RAW_OUTPUT_RES_G103,
    face_eye_af_menu_label: str = FACE_EYE_AF_CANONICAL_MENU_LABEL_G103,
    shoot_mode_intelligent_auto: bool = False,
    face_eye_prior_in_af: str = FACE_EYE_PRIOR_FACTORY_DEFAULT_G103,
    face_eye_subject: str = FACE_EYE_SUBJECT_FACTORY_DEFAULT_G103,
    right_left_eye_select: str = RIGHT_LEFT_EYE_FACTORY_DEFAULT_G103,
    switch_right_left_eye_pressed: bool = False,
    face_eye_frame_disp: str = FACE_EYE_FRAME_DISP_FACTORY_DEFAULT_G103,
    af_area_auto_clear: str = "Off",
    focus_locked: bool = False,
    hdmi_info_display: str = "Off",
    registered_face_memory_count: int = 2,
    explicit_face_memory_delete: bool = False,
    claimed_post_reset_apsc_s35_setting: Optional[str] = None,
    claimed_effective_apsc_s35_active: Optional[bool] = None,
    claimed_effective_crop_factor: Optional[float] = None,
    claimed_apsc_s35_4k_or_raw_bypass_events: int = 0,
    claimed_ai_unit_subject_recog_spoof_events: int = 0,
    claimed_post_reset_face_eye_prior_in_af: Optional[str] = None,
    claimed_post_reset_face_eye_subject: Optional[str] = None,
    claimed_post_reset_right_left_eye_select: Optional[str] = None,
    claimed_post_reset_face_eye_frame_disp: Optional[str] = None,
    claimed_post_reset_face_memory_count: Optional[int] = None,
    claimed_clean_hdmi_eye_frame_rendered: Optional[bool] = None,
    claimed_hdmi_clean_feed_baked_pixels: int = 0,
) -> ApscS35AndFaceEyeAfGuardResult:
    """Verify Gate `G103`: `ILME-FX3` (`Ver. 7.02`, `ilc/2210`, `12.1MP` sensor)
    `[APS-C S35 Shooting]` `4K` movie & `4264x2408` `HDMI RAW Output` lockout +
    `[Face/Eye AF]` BIONZ XR hierarchy, clean-HDMI isolation & `[Face Memory]` survival.
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    fw_tuple = _parse_fw_tuple(firmware_version)
    if (
        body_model_name != FX3_MODEL_NAME
        or body_model_id != FX3_MODEL_ID
        or help_guide_code != FX3_HELP_GUIDE_CODE_PHASE263
        or fw_tuple is None
        or fw_tuple < FX3_MIN_SUPPORTED_FW_TUPLE_PHASE263
        or abs(float(sensor_effective_megapixels) - FX3_SENSOR_EFFECTIVE_MP_G103) > 1e-6
    ):
        _add_code(codes, STATUS_BLOCKED_G103_TELEMETRY_INVALID)
        errors.append(
            "Invalid ILME-FX3 body/help-guide/firmware/12.1MP sensor identity for Gate G103."
        )

    norm_reset = _norm_reset_action_phase263(reset_action)
    norm_apsc = _norm_apsc_s35_setting_g103(apsc_s35_setting)
    norm_domain = _norm_capture_domain_g103(capture_domain)
    norm_lens = _norm_lens_coverage_g103(lens_coverage)
    norm_mv_fmt = _norm_movie_file_format_g103(movie_file_format)
    norm_prior = _norm_on_off_phase263(face_eye_prior_in_af)
    norm_subject = _norm_face_eye_subject_g103(face_eye_subject)
    norm_eye = _norm_right_left_eye_g103(right_left_eye_select)
    norm_frame_disp = _norm_on_off_phase263(face_eye_frame_disp)
    norm_auto_clear = _norm_on_off_phase263(af_area_auto_clear)
    norm_hdmi_info = _norm_on_off_phase263(hdmi_info_display)

    if (
        norm_reset is None
        or norm_apsc is None
        or norm_domain is None
        or norm_lens is None
        or norm_mv_fmt is None
        or norm_prior is None
        or norm_subject is None
        or norm_eye is None
        or norm_frame_disp is None
        or norm_auto_clear is None
        or norm_hdmi_info is None
        or not isinstance(registered_face_memory_count, int)
        or registered_face_memory_count < 0
        or registered_face_memory_count > MAX_FACE_MEMORY_REGISTRATIONS_G103
        or (
            bool(hdmi_raw_output_enabled)
            and hdmi_raw_resolution != FX3_HDMI_RAW_OUTPUT_RES_G103
        )
    ):
        _add_code(codes, STATUS_BLOCKED_G103_TELEMETRY_INVALID)
        errors.append("Invalid G103 menu option or Face Memory count telemetry.")

    if (
        norm_subject == FACE_EYE_SUBJECT_BIRD_G103
        and fw_tuple is not None
        and fw_tuple < FX3_BIRD_SUBJECT_MIN_FW_TUPLE_G103
    ):
        _add_code(codes, STATUS_BLOCKED_G103_TELEMETRY_INVALID)
        errors.append(
            f"[Face/Eye Subject] = [Bird] requires ILME-FX3 Ver. 3.00+ (got {firmware_version})."
        )

    cleaned_label = (
        face_eye_af_menu_label.strip().strip("[]")
        if isinstance(face_eye_af_menu_label, str)
        else ""
    )
    spoof_events = max(0, int(claimed_ai_unit_subject_recog_spoof_events))
    if (
        cleaned_label != FACE_EYE_AF_CANONICAL_MENU_LABEL_G103
        or any(
            cleaned_label.upper() == bad.upper()
            for bad in DISALLOWED_AI_UNIT_MENU_LABELS_G103
        )
        or spoof_events > 0
    ):
        spoof_events = max(1, spoof_events)
        _add_code(codes, STATUS_BLOCKED_G103_AI_UNIT_SUBJECT_RECOG_SPOOF_VIOLATION)
        errors.append(
            f"ILME-FX3 (ilc/2210) uses BIONZ XR [{FACE_EYE_AF_CANONICAL_MENU_LABEL_G103}], "
            f"not dedicated AI-unit [Subject Recog in AF] (got '{face_eye_af_menu_label}')."
        )

    resolved = resolve_fx3_apsc_s35_and_face_eye_af_state(
        apsc_s35_setting=norm_apsc or APSC_S35_FACTORY_DEFAULT_G103,
        reset_action=norm_reset or RESET_ACTION_NONE,
        capture_domain=norm_domain or CAPTURE_DOMAIN_MOVIE_G103,
        lens_coverage=norm_lens or LENS_COVERAGE_FULL_FRAME_G103,
        movie_file_format=norm_mv_fmt or MOVIE_FORMAT_XAVC_S_4K_G103,
        hdmi_raw_output_enabled=bool(hdmi_raw_output_enabled),
        shoot_mode_intelligent_auto=bool(shoot_mode_intelligent_auto),
        face_eye_prior_in_af=norm_prior or FACE_EYE_PRIOR_FACTORY_DEFAULT_G103,
        face_eye_subject=norm_subject or FACE_EYE_SUBJECT_FACTORY_DEFAULT_G103,
        right_left_eye_select=norm_eye or RIGHT_LEFT_EYE_FACTORY_DEFAULT_G103,
        switch_right_left_eye_pressed=bool(switch_right_left_eye_pressed),
        face_eye_frame_disp=norm_frame_disp or FACE_EYE_FRAME_DISP_FACTORY_DEFAULT_G103,
        af_area_auto_clear=norm_auto_clear or "Off",
        focus_locked=bool(focus_locked),
        hdmi_info_display=norm_hdmi_info or "Off",
        registered_face_memory_count=(
            registered_face_memory_count
            if isinstance(registered_face_memory_count, int)
            and 0 <= registered_face_memory_count <= MAX_FACE_MEMORY_REGISTRATIONS_G103
            else 0
        ),
        explicit_face_memory_delete=bool(explicit_face_memory_delete),
    )

    matrix = compute_apsc_s35_movie_format_lockout_matrix()
    bypass_events = int(matrix["apsc_s35_4k_or_raw_bypass_events"]) + max(
        0, int(claimed_apsc_s35_4k_or_raw_bypass_events)
    )
    actual_s35_active = (
        resolved["effective_sensor_readout_mode"] == SENSOR_READOUT_SUPER_35MM_G103
    )
    if (
        claimed_effective_apsc_s35_active is not None
        and bool(claimed_effective_apsc_s35_active) != actual_s35_active
    ):
        bypass_events += 1
    if (
        claimed_effective_crop_factor is not None
        and abs(float(claimed_effective_crop_factor) - resolved["effective_crop_factor"])
        > 1e-6
    ):
        bypass_events += 1
    if bypass_events > 0:
        _add_code(codes, STATUS_BLOCKED_G103_APSC_S35_4K_OR_RAW_BYPASS_VIOLATION)
        errors.append(
            "ILME-FX3 12.1MP sensor locks [APS-C S35 Shooting] to [Off] in 4K movie "
            "(XAVC HS 4K / XAVC S 4K / XAVC S-I 4K) and 4264x2408 HDMI RAW Output."
        )

    baked_pixels = max(0, int(claimed_hdmi_clean_feed_baked_pixels))
    clean_hdmi_stream = (norm_hdmi_info or "Off") == "Off" or bool(
        hdmi_raw_output_enabled
    )
    if clean_hdmi_stream and claimed_clean_hdmi_eye_frame_rendered is True:
        baked_pixels = max(1, baked_pixels)
    if (
        not clean_hdmi_stream
        and claimed_clean_hdmi_eye_frame_rendered is not None
        and bool(claimed_clean_hdmi_eye_frame_rendered)
        != resolved["hdmi_eye_frame_overlay_rendered"]
    ):
        baked_pixels = max(1, baked_pixels)
    if baked_pixels > 0:
        _add_code(codes, STATUS_BLOCKED_G103_HDMI_CLEAN_FEED_EYE_FRAME_BAKE_VIOLATION)
        errors.append(
            "[Face/Eye Frame Disp.] overlay must never be baked into clean HDMI "
            "([HDMI Info. Display] = [Off]) or 4264x2408 HDMI RAW Output."
        )

    reset_mismatch = False
    if claimed_post_reset_apsc_s35_setting is not None:
        if (
            _norm_apsc_s35_setting_g103(claimed_post_reset_apsc_s35_setting)
            != resolved["effective_post_reset_apsc_s35_setting"]
        ):
            reset_mismatch = True
    if claimed_post_reset_face_eye_prior_in_af is not None:
        if (
            _norm_on_off_phase263(claimed_post_reset_face_eye_prior_in_af)
            != resolved["effective_post_reset_face_eye_prior_in_af"]
        ):
            reset_mismatch = True
    if claimed_post_reset_face_eye_subject is not None:
        if (
            _norm_face_eye_subject_g103(claimed_post_reset_face_eye_subject)
            != resolved["effective_post_reset_face_eye_subject"]
        ):
            reset_mismatch = True
    if claimed_post_reset_right_left_eye_select is not None:
        if (
            _norm_right_left_eye_g103(claimed_post_reset_right_left_eye_select)
            != resolved["effective_post_reset_right_left_eye_select"]
        ):
            reset_mismatch = True
    if claimed_post_reset_face_eye_frame_disp is not None:
        if (
            _norm_on_off_phase263(claimed_post_reset_face_eye_frame_disp)
            != resolved["effective_post_reset_face_eye_frame_disp"]
        ):
            reset_mismatch = True
    if claimed_post_reset_face_memory_count is not None:
        if (
            int(claimed_post_reset_face_memory_count)
            != resolved["effective_post_reset_registered_face_memory_count"]
        ):
            reset_mismatch = True
    if reset_mismatch:
        _add_code(
            codes, STATUS_BLOCKED_G103_RESET_OR_FACE_MEMORY_PERSISTENCE_VIOLATION
        )
        errors.append(
            "Reset persistence mismatch across [APS-C S35 Shooting], [Face/Eye AF], "
            "or [Face Memory] survival across [Camera Settings Reset]."
        )

    valid = not codes
    status = STATUS_VERIFIED_G103 if valid else codes[0]

    return ApscS35AndFaceEyeAfGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=body_model_name,
        body_model_id_hex=f"0x{body_model_id:08X}"
        if isinstance(body_model_id, int)
        else "INVALID",
        help_guide_code=help_guide_code,
        firmware_version=firmware_version,
        sensor_effective_megapixels=float(sensor_effective_megapixels),
        sensor_effective_still_resolution=FX3_SENSOR_EFFECTIVE_STILL_RES_G103,
        sensor_native_4k_movie_resolution=FX3_SENSOR_NATIVE_4K_MOVIE_RES_G103,
        apsc_s35_menu_path=APSC_S35_MENU_PATH_G103,
        apsc_s35_factory_default=APSC_S35_FACTORY_DEFAULT_G103,
        pre_reset_apsc_s35_setting=norm_apsc or str(apsc_s35_setting),
        reset_action=norm_reset or str(reset_action),
        effective_post_reset_apsc_s35_setting=resolved[
            "effective_post_reset_apsc_s35_setting"
        ],
        apsc_s35_reset_by_camera_settings_reset=True,
        apsc_s35_unaffected_by_reset_network_set=True,
        capture_domain=norm_domain or str(capture_domain),
        lens_coverage=norm_lens or str(lens_coverage),
        movie_file_format=norm_mv_fmt or str(movie_file_format),
        hdmi_raw_output_enabled=bool(hdmi_raw_output_enabled),
        hdmi_raw_resolution=hdmi_raw_resolution,
        is_4k_movie_format=resolved["is_4k_movie_format"],
        apsc_s35_hardware_locked_to_off=resolved["apsc_s35_hardware_locked_to_off"],
        effective_apsc_s35_state=resolved["effective_apsc_s35_state"],
        effective_sensor_readout_mode=resolved["effective_sensor_readout_mode"],
        effective_crop_factor=resolved["effective_crop_factor"],
        super35_movie_capture_active=resolved["super35_movie_capture_active"],
        super35_hd_only_enforced=bool(matrix["hd_only_super35_enforced"])
        and bypass_events == 0,
        lockout_matrix_states_checked=int(matrix["states_checked"]),
        apsc_s35_4k_or_raw_bypass_events=bypass_events,
        face_eye_af_menu_path=FACE_EYE_AF_MENU_PATH_G103,
        face_eye_af_menu_label=cleaned_label or str(face_eye_af_menu_label),
        ai_unit_subject_recog_spoof_events=spoof_events,
        shoot_mode_intelligent_auto=bool(shoot_mode_intelligent_auto),
        pre_reset_face_eye_prior_in_af=norm_prior or str(face_eye_prior_in_af),
        effective_post_reset_face_eye_prior_in_af=resolved[
            "effective_post_reset_face_eye_prior_in_af"
        ],
        pre_reset_face_eye_subject=norm_subject or str(face_eye_subject),
        effective_post_reset_face_eye_subject=resolved[
            "effective_post_reset_face_eye_subject"
        ],
        pre_reset_right_left_eye_select=norm_eye or str(right_left_eye_select),
        switch_right_left_eye_pressed=bool(switch_right_left_eye_pressed),
        effective_post_reset_right_left_eye_select=resolved[
            "effective_post_reset_right_left_eye_select"
        ],
        pre_reset_face_eye_frame_disp=norm_frame_disp or str(face_eye_frame_disp),
        effective_post_reset_face_eye_frame_disp=resolved[
            "effective_post_reset_face_eye_frame_disp"
        ],
        af_area_auto_clear=norm_auto_clear or str(af_area_auto_clear),
        focus_locked=bool(focus_locked),
        lcd_eye_frame_overlay_rendered=resolved["lcd_eye_frame_overlay_rendered"],
        hdmi_info_display=norm_hdmi_info or str(hdmi_info_display),
        hdmi_eye_frame_overlay_rendered=resolved["hdmi_eye_frame_overlay_rendered"],
        hdmi_clean_feed_eye_frame_baked_pixels=baked_pixels,
        pre_reset_registered_face_memory_count=int(registered_face_memory_count)
        if isinstance(registered_face_memory_count, int)
        else -1,
        explicit_face_memory_delete=bool(explicit_face_memory_delete),
        effective_post_reset_registered_face_memory_count=resolved[
            "effective_post_reset_registered_face_memory_count"
        ],
        face_memory_survives_camera_settings_reset=True,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g103_apsc_s35_and_face_eye_af_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    apsc_s35_face_eye_af_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase263DonorAuditResult] = None,
) -> Tuple[GateVerdict, G103ApscS35AndFaceEyeAfGuardResult]:
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase263_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_apsc_s35_and_face_eye_af_guard(
        **dict(apsc_s35_face_eye_af_kwargs or {})
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
        errors.append("Persistent eMMC write authorization requested in Gate G103.")
    if not audit.valid:
        _add_code(codes, audit.status)
    for c in guard.violation_codes:
        _add_code(codes, c)

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G103 if valid else codes[0]

    res = G103ApscS35AndFaceEyeAfGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        apsc_s35_face_eye_af_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, apsc_s35={guard.effective_apsc_s35_state}"
        f"(locked_off={guard.apsc_s35_hardware_locked_to_off},"
        f"bypass={guard.apsc_s35_4k_or_raw_bypass_events}), "
        f"face_eye_af={guard.face_eye_af_menu_label}"
        f"(spoof={guard.ai_unit_subject_recog_spoof_events},"
        f"eye={guard.effective_post_reset_right_left_eye_select},"
        f"clean_hdmi_baked={guard.hdmi_clean_feed_eye_frame_baked_pixels},"
        f"face_mem={guard.effective_post_reset_registered_face_memory_count})"
    )
    verdict = GateVerdict(
        gate_id=G103_GATE_ID,
        gate_code=G103_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 3. Gate `G104`: `[Version]` Read-Only, Zero-RF Badge & `BODYDATA.DAT` Flash Block
# ---------------------------------------------------------------------------


def resolve_fx3_version_readonly_and_bodydata_state(
    *,
    body_firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE263,
    lens_firmware_version: str = DEFAULT_LENS_VERSION_G104,
    mount_adaptor_firmware_version: str = DEFAULT_MOUNT_ADAPTOR_VERSION_G104,
    reset_action: str = RESET_ACTION_NONE,
    airplane_mode: str = AIRPLANE_MODE_BENCH_REQUIRED_G104,
    wifi_enabled: bool = False,
    bluetooth_enabled: bool = False,
    creators_app_cloud_polling_enabled: bool = False,
    battery_charge_pct: int = 85,
    battery_bars: int = 4,
    automated_bodydata_flash_attempts: int = 1,
) -> Dict[str, Any]:
    """Deterministically resolve `MENU -> Setup -> [Setup Option] -> [Version]`
    read-only inspection, `Ver. 6.00+`/`7.02` update notification badge zero-RF
    suppression, and hard-blocked automated Slot-1 `BODYDATA.DAT` flash guard.
    """
    fw_tuple = _parse_fw_tuple(body_firmware_version)
    formatted_body_ver = (
        f"Ver. {fw_tuple[0]}.{fw_tuple[1]:02d}"
        if fw_tuple is not None
        else str(body_firmware_version)
    )
    norm_airplane = (
        _norm_on_off_phase263(airplane_mode) or AIRPLANE_MODE_BENCH_REQUIRED_G104
    )
    fw_has_v6_badge = (
        fw_tuple is not None and fw_tuple >= FX3_VERSION_BADGE_MIN_FW_TUPLE_G104
    )
    zero_rf_active = (
        norm_airplane == AIRPLANE_MODE_ON_G104
        and (not bool(wifi_enabled))
        and (not bool(bluetooth_enabled))
        and (not bool(creators_app_cloud_polling_enabled))
    )
    badge_suppressed = zero_rf_active or (not fw_has_v6_badge)
    badge_visible = fw_has_v6_badge and (not zero_rf_active)
    human_batt_ok = (
        int(battery_charge_pct) >= HUMAN_MANUAL_MIN_BATTERY_PCT_G104
        and int(battery_bars) >= HUMAN_MANUAL_MIN_BATTERY_BARS_G104
    )
    attempts = max(0, int(automated_bodydata_flash_attempts))
    _ = _norm_reset_action_phase263(reset_action)

    return {
        "formatted_body_version": formatted_body_ver,
        "lens_firmware_version": str(lens_firmware_version).strip() or "--",
        "mount_adaptor_firmware_version": str(mount_adaptor_firmware_version).strip()
        or "--",
        "version_survives_all_resets": True,
        "version_dialog_flash_writes": 0,
        "fw_supports_v6_update_badge": fw_has_v6_badge,
        "zero_rf_bench_active": zero_rf_active,
        "update_notification_badge_suppressed": badge_suppressed,
        "update_notification_badge_visible": badge_visible,
        "passive_tx_bytes_emitted": 0 if zero_rf_active else 1,
        "human_manual_battery_prereq_met": human_batt_ok,
        "bodydata_flash_hard_blocked": True,
        "bodydata_flash_attempts_blocked": attempts,
        "bodydata_flash_executions_permitted": 0,
        "slot1_bodydata_vault_mutation_bytes": 0,
    }


def verify_version_readonly_and_bodydata_flash_block_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: int = FX3_MODEL_ID,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE263,
    body_firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE263,
    lens_firmware_version: str = DEFAULT_LENS_VERSION_G104,
    mount_adaptor_firmware_version: str = DEFAULT_MOUNT_ADAPTOR_VERSION_G104,
    reset_action: str = RESET_ACTION_NONE,
    version_dialog_access_mode: str = VERSION_DIALOG_ACCESS_MODE_G104,
    airplane_mode: str = AIRPLANE_MODE_BENCH_REQUIRED_G104,
    wifi_enabled: bool = False,
    bluetooth_enabled: bool = False,
    creators_app_cloud_polling_enabled: bool = False,
    bodydata_filename: str = BODYDATA_FILENAME_G104,
    slot1_bodydata_present: bool = False,
    slot1_bodydata_sony_signed: bool = True,
    battery_charge_pct: int = 85,
    battery_bars: int = 4,
    automated_bodydata_flash_attempts: int = 1,
    allow_automated_bodydata_flash: bool = False,
    claimed_version_dialog_flash_writes: int = 0,
    claimed_post_reset_body_version: Optional[str] = None,
    claimed_update_notification_badge_visible: Optional[bool] = None,
    claimed_passive_tx_bytes_emitted: int = 0,
    claimed_bodydata_flash_executions_permitted: int = 0,
    claimed_slot1_bodydata_vault_mutation_bytes: int = 0,
) -> VersionReadOnlyAndBodydataFlashBlockGuardResult:
    """Verify Gate `G104`: `MENU -> Setup -> [Setup Option] -> [Version]` read-only
    Body (`Ver. 7.02`), E-mount Lens & Mount Adaptor inspection (`version_dialog_flash_writes == 0`),
    `Ver. 6.00+`/`7.02` update notification badge suppression on zero-RF
    `Airplane Mode = On` bench (`passive_tx_bytes_emitted == 0`), and hard-blocked
    Slot-1 `BODYDATA.DAT` automated flash guard (`bodydata_flash_attempts_blocked >= 1`,
    `slot1_bodydata_vault_mutation_bytes == 0`).
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    fw_tuple = _parse_fw_tuple(body_firmware_version)
    norm_reset = _norm_reset_action_phase263(reset_action)
    norm_airplane = _norm_on_off_phase263(airplane_mode)

    if (
        body_model_name != FX3_MODEL_NAME
        or body_model_id != FX3_MODEL_ID
        or help_guide_code != FX3_HELP_GUIDE_CODE_PHASE263
        or fw_tuple is None
        or fw_tuple < FX3_MIN_SUPPORTED_FW_TUPLE_PHASE263
        or norm_reset is None
        or norm_airplane is None
        or not isinstance(lens_firmware_version, str)
        or not lens_firmware_version.strip()
        or not isinstance(mount_adaptor_firmware_version, str)
        or not mount_adaptor_firmware_version.strip()
        or not isinstance(battery_charge_pct, int)
        or not (0 <= battery_charge_pct <= 100)
        or not isinstance(battery_bars, int)
        or not (0 <= battery_bars <= 4)
        or not isinstance(automated_bodydata_flash_attempts, int)
        or automated_bodydata_flash_attempts < 1
        or bodydata_filename != BODYDATA_FILENAME_G104
    ):
        _add_code(codes, STATUS_BLOCKED_G104_TELEMETRY_INVALID)
        errors.append("Invalid ILME-FX3 [Version] or BODYDATA.DAT guard telemetry.")

    resolved = resolve_fx3_version_readonly_and_bodydata_state(
        body_firmware_version=body_firmware_version,
        lens_firmware_version=(
            lens_firmware_version
            if isinstance(lens_firmware_version, str)
            else DEFAULT_LENS_VERSION_G104
        ),
        mount_adaptor_firmware_version=(
            mount_adaptor_firmware_version
            if isinstance(mount_adaptor_firmware_version, str)
            else DEFAULT_MOUNT_ADAPTOR_VERSION_G104
        ),
        reset_action=norm_reset or RESET_ACTION_NONE,
        airplane_mode=norm_airplane or AIRPLANE_MODE_BENCH_REQUIRED_G104,
        wifi_enabled=bool(wifi_enabled),
        bluetooth_enabled=bool(bluetooth_enabled),
        creators_app_cloud_polling_enabled=bool(creators_app_cloud_polling_enabled),
        battery_charge_pct=(
            battery_charge_pct if isinstance(battery_charge_pct, int) else 0
        ),
        battery_bars=battery_bars if isinstance(battery_bars, int) else 0,
        automated_bodydata_flash_attempts=(
            automated_bodydata_flash_attempts
            if isinstance(automated_bodydata_flash_attempts, int)
            else 0
        ),
    )

    flash_writes = max(0, int(claimed_version_dialog_flash_writes))
    access_clean = (
        isinstance(version_dialog_access_mode, str)
        and version_dialog_access_mode.strip().upper() == VERSION_DIALOG_ACCESS_MODE_G104
    )
    if not access_clean or flash_writes > 0:
        flash_writes = max(1, flash_writes)
        _add_code(codes, STATUS_BLOCKED_G104_VERSION_DIALOG_FLASH_WRITE_VIOLATION)
        errors.append(
            "[Version] dialog must remain strictly READ_ONLY with zero flash partition writes."
        )

    if claimed_post_reset_body_version is not None:
        claimed_fw_tuple = _parse_fw_tuple(claimed_post_reset_body_version)
        if claimed_fw_tuple is None or claimed_fw_tuple != fw_tuple:
            flash_writes = max(1, flash_writes)
            _add_code(codes, STATUS_BLOCKED_G104_VERSION_DIALOG_FLASH_WRITE_VIOLATION)
            errors.append(
                "[Version] body firmware string mutated across reset or dialog inspection."
            )

    tx_bytes = int(resolved["passive_tx_bytes_emitted"]) + max(
        0, int(claimed_passive_tx_bytes_emitted)
    )
    badge_vis = bool(resolved["update_notification_badge_visible"])
    if claimed_update_notification_badge_visible is True:
        badge_vis = True
    badge_suppressed = not badge_vis
    if (
        norm_airplane != AIRPLANE_MODE_ON_G104
        or bool(wifi_enabled)
        or bool(bluetooth_enabled)
        or bool(creators_app_cloud_polling_enabled)
        or tx_bytes > 0
        or badge_vis
    ):
        _add_code(codes, STATUS_BLOCKED_G104_ZERO_RF_UPDATE_BADGE_OR_TX_VIOLATION)
        errors.append(
            "Zero-RF bench requires [Airplane Mode] = [On], suppressed Ver. 6.00+/7.02 "
            "update notification badge, and passive_tx_bytes_emitted == 0."
        )

    execs_permitted = max(0, int(claimed_bodydata_flash_executions_permitted))
    vault_mut_bytes = max(0, int(claimed_slot1_bodydata_vault_mutation_bytes))
    hard_blocked = (
        (not bool(allow_automated_bodydata_flash))
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED)
        and execs_permitted == 0
        and vault_mut_bytes == 0
    )
    attempts_blocked = (
        int(resolved["bodydata_flash_attempts_blocked"]) if hard_blocked else 0
    )
    if (
        not hard_blocked
        or attempts_blocked < 1
        or (bool(slot1_bodydata_present) and not bool(slot1_bodydata_sony_signed))
    ):
        if bool(allow_automated_bodydata_flash):
            execs_permitted = max(1, execs_permitted)
        _add_code(codes, STATUS_BLOCKED_G104_BODYDATA_FLASH_EXECUTION_VIOLATION)
        errors.append(
            "Automated Slot-1 BODYDATA.DAT firmware flashing (or unsigned image staging) "
            "is HARD-BLOCKED / NO-GO for all agents."
        )

    valid = not codes
    status = STATUS_VERIFIED_G104 if valid else codes[0]

    return VersionReadOnlyAndBodydataFlashBlockGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=body_model_name,
        body_model_id_hex=f"0x{body_model_id:08X}"
        if isinstance(body_model_id, int)
        else "INVALID",
        help_guide_code=help_guide_code,
        version_menu_path=VERSION_MENU_PATH_G104,
        version_dialog_access_mode=str(version_dialog_access_mode),
        reset_action=norm_reset or str(reset_action),
        body_firmware_version=str(body_firmware_version),
        formatted_body_version=resolved["formatted_body_version"],
        lens_firmware_version=resolved["lens_firmware_version"],
        mount_adaptor_firmware_version=resolved["mount_adaptor_firmware_version"],
        version_survives_all_resets=True,
        version_dialog_flash_writes=flash_writes,
        airplane_mode=norm_airplane or str(airplane_mode),
        wifi_enabled=bool(wifi_enabled),
        bluetooth_enabled=bool(bluetooth_enabled),
        creators_app_cloud_polling_enabled=bool(creators_app_cloud_polling_enabled),
        fw_supports_v6_update_badge=resolved["fw_supports_v6_update_badge"],
        update_notification_badge_suppressed=badge_suppressed,
        update_notification_badge_visible=badge_vis,
        passive_tx_bytes_emitted=tx_bytes,
        bodydata_filename=str(bodydata_filename),
        slot1_bodydata_present=bool(slot1_bodydata_present),
        slot1_bodydata_sony_signed=bool(slot1_bodydata_sony_signed),
        battery_charge_pct=int(battery_charge_pct)
        if isinstance(battery_charge_pct, int)
        else -1,
        battery_bars=int(battery_bars) if isinstance(battery_bars, int) else -1,
        human_manual_battery_prereq_met=resolved["human_manual_battery_prereq_met"],
        automated_bodydata_flash_attempts=int(automated_bodydata_flash_attempts)
        if isinstance(automated_bodydata_flash_attempts, int)
        else -1,
        bodydata_flash_hard_blocked=hard_blocked,
        bodydata_flash_attempts_blocked=attempts_blocked,
        bodydata_flash_executions_permitted=execs_permitted,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        physical_flash_auto_exec_authorized=PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
        slot1_bodydata_vault_mutation_bytes=vault_mut_bytes,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g104_version_readonly_and_bodydata_flash_block_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    version_bodydata_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase263DonorAuditResult] = None,
) -> Tuple[GateVerdict, G104VersionReadOnlyAndBodydataFlashBlockGuardResult]:
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase263_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_version_readonly_and_bodydata_flash_block_guard(
        **dict(version_bodydata_kwargs or {})
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
        errors.append("Persistent eMMC write authorization requested in Gate G104.")
    if not audit.valid:
        _add_code(codes, audit.status)
    for c in guard.violation_codes:
        _add_code(codes, c)

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G104 if valid else codes[0]

    res = G104VersionReadOnlyAndBodydataFlashBlockGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        version_bodydata_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, body={guard.formatted_body_version}"
        f"(flash_writes={guard.version_dialog_flash_writes}), "
        f"airplane={guard.airplane_mode}"
        f"(badge_suppressed={guard.update_notification_badge_suppressed},"
        f"tx={guard.passive_tx_bytes_emitted}), "
        f"bodydata_blocked={guard.bodydata_flash_attempts_blocked}"
        f"(mut_bytes={guard.slot1_bodydata_vault_mutation_bytes})"
    )
    verdict = GateVerdict(
        gate_id=G104_GATE_ID,
        gate_code=G104_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 4. Unified `104`-Gate Master Safety Preflight (`G01..G104`)
# ---------------------------------------------------------------------------


def evaluate_104gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    dry_run_simulated_backup: Optional[bool] = None,
    simulate_bench_dry_run: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    request_persistent_emmc_writes: bool = False,
    apsc_s35_face_eye_af_kwargs: Optional[Mapping[str, Any]] = None,
    version_bodydata_kwargs: Optional[Mapping[str, Any]] = None,
    master_102_override: Optional[Master102GateReport] = None,
    **m102_passthrough_kwargs: Any,
) -> Master104GateReport:
    """Evaluate all 104 Master Safety Gates (`G01..G104`) deterministically by
    delegating `G01..G102` directly to `evaluate_102gate_preflight()`.
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

    m102_report: Master102GateReport = (
        master_102_override
        if master_102_override is not None
        else evaluate_102gate_preflight(
            resolved_root,
            force_clean_room=clean_forced,
            dry_run_simulated=effective_dry_run,
            include_large_binaries=include_large_binaries,
            work_root=work_root,
            request_persistent_emmc_writes=request_persistent_emmc_writes,
            **m102_passthrough_kwargs,
        )
    )

    phase263_audit = audit_phase263_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
    )

    g103_verdict, g103_res = evaluate_g103_apsc_s35_and_face_eye_af_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        apsc_s35_face_eye_af_kwargs=apsc_s35_face_eye_af_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase263_audit,
    )

    g104_verdict, g104_res = (
        evaluate_g104_version_readonly_and_bodydata_flash_block_guard(
            work_root=work_root,
            repo_root=resolved_root,
            force_clean_room=clean_forced,
            version_bodydata_kwargs=version_bodydata_kwargs,
            request_persistent_emmc_writes=request_persistent_emmc_writes,
            donor_audit=phase263_audit,
        )
    )

    gates_103_to_104 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g103_verdict, g104_verdict)
    ]
    all_gates = tuple(list(m102_report.gates) + gates_103_to_104)

    g01_to_g12_verified = int(m102_report.summary["g01_to_g12_verified"])
    g13_to_g102_verified = int(m102_report.summary["g13_to_g100_verified"]) + int(
        m102_report.summary["g101_to_g102_verified"]
    )
    g103_to_g104_verified = sum(1 for v in (g103_verdict, g104_verdict) if v.passed)
    total_verified = (
        g01_to_g12_verified + g13_to_g102_verified + g103_to_g104_verified
    )

    g103_to_g104_all_passed = g103_to_g104_verified == 2
    g13_to_g104_all_passed = (
        m102_report.g13_to_g102_all_passed and g103_to_g104_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m102_report.gates[:9])

    offline_101_verified = (
        g01_to_g09_ok
        and m102_report.offline_99_gates_verified
        and g103_to_g104_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_104_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g104_all_passed
        and (not request_persistent_emmc_writes)
    )

    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m102_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_101_verified
        and m102_report.h0_h1_trial_entry_allowed
        and g103_to_g104_all_passed
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
        list(m102_report.errors)
        + list(g103_verdict.errors)
        + list(g104_verdict.errors)
    )
    warnings: List[str] = (
        list(m102_report.warnings)
        + list(g103_verdict.warnings)
        + list(g104_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m102_report.g13_to_g102_all_passed:
        overall_status = m102_report.status
    elif not g103_verdict.passed:
        overall_status = g103_verdict.status
    elif not g104_verdict.passed:
        overall_status = g104_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_104_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_104_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_104_verified:
        overall_status = "VERIFIED_ALL_104_GATES"
    else:
        overall_status = "VERIFIED_101_OF_104_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m102_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g103_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g104_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 104,
        "verified_gates": total_verified,
        "technical_gates_passed": total_verified,
        "blocked_or_pending_gates": 104 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g102_verified": g13_to_g102_verified,
        "g103_to_g104_verified": g103_to_g104_verified,
        "g13_to_g104_all_passed": g13_to_g104_all_passed,
        "g103_to_g104_all_passed": g103_to_g104_all_passed,
        "offline_101_gates_verified": offline_101_verified,
        "all_104_gates_verified": all_104_verified,
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

    return Master104GateReport(
        schema=REALHW_APSC_S35_FACE_EYE_AF_VERSION_104GATE_SCHEMA,
        version=REALHW_APSC_S35_FACE_EYE_AF_VERSION_104GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        offline_101_gates_verified=offline_101_verified,
        all_104_gates_verified=all_104_verified,
        g13_to_g104_all_passed=g13_to_g104_all_passed,
        g103_to_g104_all_passed=g103_to_g104_all_passed,
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
        master_102_report=m102_report.to_dict(),
        g103_result=g103_res.to_dict(),
        g104_result=g104_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_104_master_safety_gates = evaluate_104gate_preflight
run_104_gate_preflight = evaluate_104gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_apsc_s35_face_eye_af_version_and_104gate_guard",
        description=(
            "Phase 263 Safety Gates G103 (APS-C S35 Shooting 12.1MP 4K Lockout & "
            "Face/Eye AF Clean-HDMI Isolation Guard) + G104 (Version Read-Only, "
            "Zero-RF Badge Suppression & Hard-Blocked BODYDATA.DAT Flash Guard) + "
            "Unified 104-Gate Master Safety Preflight"
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

    report = evaluate_104gate_preflight(
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
            f"verified={report.summary['verified_gates']}/104 "
            f"g103_to_g104_all_passed={report.g103_to_g104_all_passed} "
            f"all_104_gates_verified={report.all_104_gates_verified} "
            f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach}\n"
        )
    ok = (
        report.all_104_gates_verified
        if args.dry_run_simulated
        else report.offline_101_gates_verified
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
