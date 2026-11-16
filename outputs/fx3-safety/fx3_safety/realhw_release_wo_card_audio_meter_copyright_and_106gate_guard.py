"""Phase 266 (Task H300 Milestone, Wave-43) Sony `ILME-FX3` (`Ver. 7.02`, `ilc/2210`)
Safety Gates `G105` (`[Release w/o Card]` Still-Only Scope vs Movie Internal Media
Gate & `[Release w/o Lens]` Zero-`E-ND` / Zero-E-Mount-UART Body-Only Bench Guard +
`Ver. 2.00+`/`7.02` Exact 5-Item `[Audio Recording]` Menu vs `Ver. 1.x` `ilc/2035`
Standalone `[Audio Level Display]` Removal & `[DISP (Screen Disp) Set]` 2ch/4ch/`S&Q`
Audio Meter Guard) & `G106` (`[Copyright Info]` `<= 46`-Char Printable ASCII Bounds,
Still-JPEG/HEIF EXIF-Only Scope, `[Camera Settings Reset]` Survival vs `[Initialize]`
Wipe & Clean-Room Bench PII Hygiene Guard) + Unified `106`-Gate Master Safety
Preflight (`G01..G106`).

Operationalizes Wave-43 official Sony `ILME-FX3` (`Ver. 7.02`, Help Guide `ilc/2210`)
intelligence (`reports/2026-11-15-global-sony-wave43-release-wo-card-lens-disp-audio-meter-v2-vs-v1-copyright-info-46char-intel/README.md`)
as deterministic offline preflight verifiers (`G105` and `G106`) and delegates
`G01..G104` directly to `evaluate_104gate_preflight()`.
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
from .realhw_apsc_s35_face_eye_af_version_and_104gate_guard import (
    Master104GateReport,
    evaluate_104gate_preflight,
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

REALHW_RELEASE_WO_CARD_AUDIO_METER_COPYRIGHT_106GATE_SCHEMA: str = (
    "realhw_release_wo_card_audio_meter_copyright_and_106gate_guard_v1"
)
REALHW_RELEASE_WO_CARD_AUDIO_METER_COPYRIGHT_106GATE_VERSION: str = "1.0.0"

G105_GATE_ID: str = (
    "G105_release_wo_card_lens_and_v702_audio_disp_meter_guard"
)
G105_GATE_CODE: str = (
    "RELEASE_WO_CARD_LENS_AND_V702_AUDIO_DISP_METER_GUARD"
)

G106_GATE_ID: str = (
    "G106_copyright_info_46char_still_exif_and_pii_hygiene_guard"
)
G106_GATE_CODE: str = (
    "COPYRIGHT_INFO_46CHAR_STILL_EXIF_AND_PII_HYGIENE_GUARD"
)

G105: str = G105_GATE_ID
G106: str = G106_GATE_ID
GATE_G105_RELEASE_WO_CARD_LENS_AND_V702_AUDIO_DISP_METER_GUARD: str = G105_GATE_CODE
GATE_G106_COPYRIGHT_INFO_46CHAR_STILL_EXIF_AND_PII_HYGIENE_GUARD: str = G106_GATE_CODE

ENV_CLEAN_ROOM_TEST_PHASE266: str = "FX3_CLEAN_ROOM_TEST"

HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
HUMAN_HARDWARE_ATTACH_TOKEN: bool = False
USB_PACKETS_TRANSMITTED: int = 0
PHYSICAL_USB_PACKETS_EMITTED: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0
DONOR_CHECK_MAX_SECONDS_PHASE266: float = 0.10
DONOR_CHECK_MAX_SECONDS: float = DONOR_CHECK_MAX_SECONDS_PHASE266

FX3_MODEL_NAME: str = "ILME-FX3"
FX3_MODEL_ID: int = 0x91030080
FX6_MODEL_NAME: str = "ILME-FX6"
FX3_DEFAULT_FW_VERSION_PHASE266: str = "7.02"
FX3_V2_AUDIO_DISP_MIN_FW_TUPLE_G105: Tuple[int, int] = (2, 0)
FX3_HELP_GUIDE_CODE_PHASE266: str = "ilc/2210"
FX3_LEGACY_V1_HELP_GUIDE_CODE_G105: str = "ilc/2035"

RESET_ACTION_NONE: str = "NONE"
RESET_ACTION_CAMERA_SETTINGS_RESET: str = "Camera Settings Reset"
RESET_ACTION_RESET_NETWORK_SET_PHASE266: str = "Reset Network Set."
RESET_ACTION_INITIALIZE: str = "Initialize"
ALLOWED_RESET_ACTIONS_PHASE266: Tuple[str, ...] = (
    RESET_ACTION_NONE,
    RESET_ACTION_CAMERA_SETTINGS_RESET,
    RESET_ACTION_RESET_NETWORK_SET_PHASE266,
    RESET_ACTION_INITIALIZE,
)

# ---------------------------------------------------------------------------
# Status & Violation Codes (G105 / G106 / Phase 266)
# ---------------------------------------------------------------------------

STATUS_VERIFIED_G105: str = (
    "VERIFIED_G105_RELEASE_WO_CARD_LENS_AND_V702_AUDIO_DISP_METER_SAFE"
)
STATUS_VERIFIED_G106: str = (
    "VERIFIED_G106_COPYRIGHT_INFO_46CHAR_STILL_EXIF_AND_PII_HYGIENE_SAFE"
)
STATUS_BLOCKED_PHASE266_DONOR_INTEGRITY: str = (
    "BLOCKED_PHASE266_DONOR_CONTRACT_INTEGRITY"
)

STATUS_BLOCKED_G105_RELEASE_WO_CARD_SCOPE_OR_PRODUCTION_VIOLATION: str = (
    "BLOCKED_G105_RELEASE_WO_CARD_SCOPE_OR_PRODUCTION_VIOLATION"
)
STATUS_BLOCKED_G105_MOVIE_CARDLESS_INTERNAL_REC_BYPASS_VIOLATION: str = (
    "BLOCKED_G105_MOVIE_CARDLESS_INTERNAL_REC_BYPASS_VIOLATION"
)
STATUS_BLOCKED_G105_RELEASE_WO_LENS_OR_END_UART_VIOLATION: str = (
    "BLOCKED_G105_RELEASE_WO_LENS_OR_END_UART_VIOLATION"
)
STATUS_BLOCKED_G105_LEGACY_V1_AUDIO_LEVEL_MENU_SPOOF_VIOLATION: str = (
    "BLOCKED_G105_LEGACY_V1_AUDIO_LEVEL_MENU_SPOOF_VIOLATION"
)
STATUS_BLOCKED_G105_DISP_AUDIO_METER_OR_SQ_SUPPRESSION_VIOLATION: str = (
    "BLOCKED_G105_DISP_AUDIO_METER_OR_SQ_SUPPRESSION_VIOLATION"
)
STATUS_BLOCKED_G105_RESET_PERSISTENCE_VIOLATION: str = (
    "BLOCKED_G105_RESET_PERSISTENCE_VIOLATION"
)
STATUS_BLOCKED_G105_TELEMETRY_INVALID: str = (
    "BLOCKED_G105_RELEASE_AUDIO_DISP_TELEMETRY_INVALID"
)

STATUS_BLOCKED_G106_COPYRIGHT_46CHAR_OR_ASCII_BOUND_VIOLATION: str = (
    "BLOCKED_G106_COPYRIGHT_46CHAR_OR_ASCII_BOUND_VIOLATION"
)
STATUS_BLOCKED_G106_MOVIE_STREAM_OR_SLOT1_VAULT_MUTATION_VIOLATION: str = (
    "BLOCKED_G106_MOVIE_STREAM_OR_SLOT1_VAULT_MUTATION_VIOLATION"
)
STATUS_BLOCKED_G106_RESET_SURVIVAL_OR_INITIALIZE_WIPE_VIOLATION: str = (
    "BLOCKED_G106_RESET_SURVIVAL_OR_INITIALIZE_WIPE_VIOLATION"
)
STATUS_BLOCKED_G106_BENCH_PII_HYGIENE_LEAK_VIOLATION: str = (
    "BLOCKED_G106_BENCH_PII_HYGIENE_LEAK_VIOLATION"
)
STATUS_BLOCKED_G106_TELEMETRY_INVALID: str = (
    "BLOCKED_G106_COPYRIGHT_INFO_TELEMETRY_INVALID"
)

# ---------------------------------------------------------------------------
# Gate G105 Constants: Release w/o Card & w/o Lens + Ver. 7.02 Audio/DISP Meter
# ---------------------------------------------------------------------------

RELEASE_WO_CARD_MENU_PATH_G105: str = (
    "MENU -> Shooting -> [Shutter/Silent] -> [Release w/o Card]"
)
RELEASE_WO_LENS_MENU_PATH_G105: str = (
    "MENU -> Shooting -> [Shutter/Silent] -> [Release w/o Lens]"
)

RELEASE_ENABLE_G105: str = "Enable"
RELEASE_DISABLE_G105: str = "Disable"
ALLOWED_RELEASE_ENABLE_DISABLE_G105: Tuple[str, ...] = (
    RELEASE_ENABLE_G105,
    RELEASE_DISABLE_G105,
)
RELEASE_WO_CARD_FACTORY_DEFAULT_G105: str = RELEASE_ENABLE_G105
RELEASE_WO_LENS_FACTORY_DEFAULT_G105: str = RELEASE_ENABLE_G105

BENCH_POSTURE_CARDLESS_DIAGNOSTIC_G105: str = "CARDLESS_DIAGNOSTIC_BENCH"
BENCH_POSTURE_PRODUCTION_SHOOT_G105: str = "PRODUCTION_SHOOT"
ALLOWED_BENCH_POSTURES_G105: Tuple[str, ...] = (
    BENCH_POSTURE_CARDLESS_DIAGNOSTIC_G105,
    BENCH_POSTURE_PRODUCTION_SHOOT_G105,
)

CAPTURE_MODE_STILL_G105: str = "Still"
CAPTURE_MODE_MOVIE_G105: str = "Movie"
CAPTURE_MODE_SQ_G105: str = "S&Q"
ALLOWED_CAPTURE_MODES_G105: Tuple[str, ...] = (
    CAPTURE_MODE_STILL_G105,
    CAPTURE_MODE_MOVIE_G105,
    CAPTURE_MODE_SQ_G105,
)

LENS_MOUNT_BODY_ONLY_BENCH_G105: str = "BODY_ONLY_BENCH"
LENS_MOUNT_PL_MECHANICAL_ADAPTER_G105: str = "PL_MECHANICAL_ADAPTER"
LENS_MOUNT_ELECTRONIC_EMOUNT_G105: str = "ELECTRONIC_E_MOUNT"
ALLOWED_LENS_MOUNT_STATES_G105: Tuple[str, ...] = (
    LENS_MOUNT_BODY_ONLY_BENCH_G105,
    LENS_MOUNT_PL_MECHANICAL_ADAPTER_G105,
    LENS_MOUNT_ELECTRONIC_EMOUNT_G105,
)

HDMI_REC_MEDIA_ON_G105: str = "On"
HDMI_REC_MEDIA_OFF_G105: str = "Off"
ALLOWED_HDMI_REC_MEDIA_SETTINGS_G105: Tuple[str, ...] = (
    HDMI_REC_MEDIA_ON_G105,
    HDMI_REC_MEDIA_OFF_G105,
)

AUDIO_RECORDING_MENU_PATH_G105: str = "MENU -> Shooting -> [Audio Recording]"
DISP_SCREEN_DISP_SET_MENU_PATH_G105: str = (
    "MENU -> Setup -> [Operation Customize] -> [DISP (Screen Disp) Set]"
)
V702_AUDIO_RECORDING_EXACT_5_ITEMS_G105: Tuple[str, ...] = (
    "Audio Recording",
    "Audio Rec Level",
    "Audio Out Timing",
    "Wind Noise Reduct.",
    "Shoe Audio Set.",
)
DISALLOWED_V1_AUDIO_MENU_ITEMS_G105: Tuple[str, ...] = (
    "Audio Level Display",
    "[Audio Level Display]",
    "Audio Level Meter",
)

AUDIO_RECORDING_ON_G105: str = "On"
AUDIO_RECORDING_OFF_G105: str = "Off"
AUDIO_RECORDING_FACTORY_DEFAULT_G105: str = AUDIO_RECORDING_ON_G105

AUDIO_REC_LEVEL_MIN_G105: int = 0
AUDIO_REC_LEVEL_MAX_G105: int = 31
AUDIO_REC_LEVEL_FACTORY_DEFAULT_G105: int = 26

AUDIO_OUT_TIMING_LIVE_G105: str = "Live"
AUDIO_OUT_TIMING_LIP_SYNC_G105: str = "Lip Sync"
ALLOWED_AUDIO_OUT_TIMING_G105: Tuple[str, ...] = (
    AUDIO_OUT_TIMING_LIVE_G105,
    AUDIO_OUT_TIMING_LIP_SYNC_G105,
)
AUDIO_OUT_TIMING_FACTORY_DEFAULT_G105: str = AUDIO_OUT_TIMING_LIVE_G105

WIND_NOISE_REDUCT_OFF_G105: str = "Off"
WIND_NOISE_REDUCT_ON_G105: str = "On"
WIND_NOISE_REDUCT_FACTORY_DEFAULT_G105: str = WIND_NOISE_REDUCT_OFF_G105

SHOE_AUDIO_48K_16B_2CH_G105: str = "48kHz/16bit 2ch"
SHOE_AUDIO_48K_24B_2CH_G105: str = "48kHz/24bit 2ch"
SHOE_AUDIO_48K_24B_4CH_G105: str = "48kHz/24bit 4ch"
ALLOWED_SHOE_AUDIO_SETTINGS_G105: Tuple[str, ...] = (
    SHOE_AUDIO_48K_16B_2CH_G105,
    SHOE_AUDIO_48K_24B_2CH_G105,
    SHOE_AUDIO_48K_24B_4CH_G105,
)
SHOE_AUDIO_FACTORY_DEFAULT_G105: str = SHOE_AUDIO_48K_16B_2CH_G105

# ---------------------------------------------------------------------------
# Gate G106 Constants: Copyright Info 46-Char Still EXIF & PII Hygiene Guard
# ---------------------------------------------------------------------------

COPYRIGHT_INFO_MENU_PATH_G106: str = (
    "MENU -> Shooting -> [File] -> [Copyright Info]"
)
COPYRIGHT_INFO_EXACT_4_SUBITEMS_G106: Tuple[str, ...] = (
    "Write Copyright Info",
    "Set Photographer",
    "Set Copyright",
    "Disp. Copyright Info",
)
WRITE_COPYRIGHT_INFO_OFF_G106: str = "Off"
WRITE_COPYRIGHT_INFO_ON_G106: str = "On"
ALLOWED_WRITE_COPYRIGHT_SETTINGS_G106: Tuple[str, ...] = (
    WRITE_COPYRIGHT_INFO_OFF_G106,
    WRITE_COPYRIGHT_INFO_ON_G106,
)
WRITE_COPYRIGHT_INFO_FACTORY_DEFAULT_G106: str = WRITE_COPYRIGHT_INFO_OFF_G106
WRITE_COPYRIGHT_INFO_BENCH_DEFAULT_G106: str = WRITE_COPYRIGHT_INFO_OFF_G106

COPYRIGHT_INFO_MAX_CHARS_G106: int = 46
MAX_PHOTOGRAPHER_CHARS_G106: int = COPYRIGHT_INFO_MAX_CHARS_G106
MAX_COPYRIGHT_CHARS_G106: int = COPYRIGHT_INFO_MAX_CHARS_G106
ASCII_PRINTABLE_MIN_CODEPOINT_G106: int = 0x20
ASCII_PRINTABLE_MAX_CODEPOINT_G106: int = 0x7E
EXIF_TAG_ARTIST_HEX_G106: str = "0x013B"
EXIF_TAG_COPYRIGHT_HEX_G106: str = "0x8298"

CONTAINER_STILL_JPEG_G106: str = "STILL_JPEG"
CONTAINER_STILL_HEIF_G106: str = "STILL_HEIF"
CONTAINER_STILL_ARW_G106: str = "STILL_ARW"
CONTAINER_MOVIE_XAVC_HS_MP4_G106: str = "MOVIE_XAVC_HS_MP4"
CONTAINER_MOVIE_XAVC_S_MP4_G106: str = "MOVIE_XAVC_S_MP4"
CONTAINER_MOVIE_XAVC_SI_MP4_G106: str = "MOVIE_XAVC_SI_MP4"
CONTAINER_HDMI_RAW_STREAM_G106: str = "HDMI_RAW_STREAM"

STILL_EXIF_ELIGIBLE_CONTAINERS_G106: Tuple[str, ...] = (
    CONTAINER_STILL_JPEG_G106,
    CONTAINER_STILL_HEIF_G106,
    CONTAINER_STILL_ARW_G106,
)
MOVIE_AND_RAW_CONTAINERS_G106: Tuple[str, ...] = (
    CONTAINER_MOVIE_XAVC_HS_MP4_G106,
    CONTAINER_MOVIE_XAVC_S_MP4_G106,
    CONTAINER_MOVIE_XAVC_SI_MP4_G106,
    CONTAINER_HDMI_RAW_STREAM_G106,
)
ALLOWED_TARGET_CONTAINERS_G106: Tuple[str, ...] = (
    STILL_EXIF_ELIGIBLE_CONTAINERS_G106 + MOVIE_AND_RAW_CONTAINERS_G106
)

# ---------------------------------------------------------------------------
# Pinned Local Donor Contracts (O_RDONLY, <0.10s, Clean-Room Fallback)
# ---------------------------------------------------------------------------

PINNED_PHASE266_DONOR_SPECS: Dict[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_cpapp_bin": (
        "FX3",
        "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin",
        15_980_568,
        "c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba",
        (
            b"ILME-FX3",
            b"Release",
            b"Lens",
            b"Shutter",
            b"Audio",
            b"Recording",
            b"Level",
            b"Timing",
            b"Wind",
            b"Shoe",
            b"DISP",
            b"Display",
            b"EXIF",
            b"Exif",
            b"HDMI",
            b"File",
            b"Reset",
            b"Initialize",
        ),
        "FX3_CPAPP_RELEASE_WO_CARD_LENS_AUDIO_DISP_EXIF_STRINGS",
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
        "FX3_LIBGPE_RELEASE_AUDIO_DISP_COPYRIGHT_MENU_ELF",
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
        "FX3_LIBSAVELOADSETTINGS_COPYRIGHT_EXCLUSION_RESET_SPLIT_ELF",
    ),
    "fx3_bk4_bin": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin",
        2_229_740,
        "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2",
        (b"BK4", b"ILME-FX3", b"TC", b"/setting"),
        "FX3_BK4_RELEASE_AUDIO_COPYRIGHT_BACKUP_SEED",
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
        "FX6_LIBINFRADIAL_DISP_AUDIO_METER_PARITY_ELF",
    ),
    "fx6_bk4_bin": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0110_backup/SYSIPSX-DSLR/CHAPLIN/CX95898_NTSC.bin",
        2_253_333,
        "e2eafd4e950ead94fdba64722b225b9ccf4cf294ce4c1cf956b9e62926bbf89e",
        (b"BK4", b"WB", b"TC", b"/setting"),
        "FX6_BK4_CINEMA_LINE_AUDIO_COPYRIGHT_PARITY_SEED",
    ),
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase266DonorAuditResult:
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
class ReleaseWoCardLensAndV702AudioDispGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    body_model_name: str
    body_model_id_hex: str
    help_guide_code: str
    firmware_version: str
    bench_posture: str
    reset_action: str
    capture_mode: str
    release_wo_card_menu_path: str
    release_wo_card_factory_default: str
    pre_reset_release_wo_card: str
    effective_post_reset_release_wo_card: str
    release_wo_card_survives_camera_settings_reset: bool
    slot1_card_inserted: bool
    slot2_card_inserted: bool
    cardless_bench_active: bool
    still_shutter_release_allowed: bool
    still_image_saved_to_card: bool
    cardless_media_sector_writes: int
    movie_internal_rec_allowed: bool
    movie_cardless_internal_rec_bypass_events: int
    hdmi_external_capture_connected: bool
    rec_media_dur_hdmi_output: str
    external_hdmi_capture_governed_by_rec_media: bool
    external_hdmi_rec_allowed: bool
    release_wo_lens_menu_path: str
    release_wo_lens_factory_default: str
    pre_reset_release_wo_lens: str
    effective_post_reset_release_wo_lens: str
    release_wo_lens_survives_camera_settings_reset: bool
    lens_mount_state: str
    electronic_emount_lens_attached: bool
    lens_gate_permits_release: bool
    effective_release_permitted: bool
    e_nd_actuator_tx_count: int
    emount_lens_uart_tx_bytes: int
    release_scope_matrix_states_checked: int
    audio_recording_menu_path: str
    disp_screen_disp_set_menu_path: str
    v702_audio_recording_menu_items: Tuple[str, ...]
    v702_audio_menu_exact_5_items_verified: bool
    legacy_v1_audio_level_menu_spoof_events: int
    pre_reset_audio_recording: str
    effective_post_reset_audio_recording: str
    pre_reset_audio_rec_level: int
    effective_post_reset_audio_rec_level: int
    pre_reset_audio_out_timing: str
    effective_post_reset_audio_out_timing: str
    pre_reset_wind_noise_reduct: str
    effective_post_reset_wind_noise_reduct: str
    pre_reset_shoe_audio_set: str
    effective_post_reset_shoe_audio_set: str
    digital_mi_shoe_4ch_attached: bool
    pre_reset_disp_audio_level_checked: bool
    effective_post_reset_disp_audio_level_checked: bool
    disp_set_survives_camera_settings_reset: bool
    sq_audio_meter_suppressed: bool
    effective_audio_meter_visible: bool
    effective_audio_meter_channels: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G105ReleaseWoCardLensAndV702AudioDispGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    release_audio_disp_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CopyrightInfo46CharStillExifGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    body_model_name: str
    body_model_id_hex: str
    help_guide_code: str
    firmware_version: str
    copyright_info_menu_path: str
    copyright_info_subitems: Tuple[str, ...]
    copyright_max_chars: int
    reset_action: str
    clean_room_bench_hygiene_required: bool
    pre_reset_write_copyright_info: str
    effective_post_reset_write_copyright_info: str
    pre_reset_photographer: str
    effective_post_reset_photographer: str
    photographer_char_length: int
    photographer_within_46char_ascii: bool
    pre_reset_copyright: str
    effective_post_reset_copyright: str
    copyright_char_length: int
    copyright_within_46char_ascii: bool
    strings_survive_camera_settings_reset: bool
    strings_wiped_by_initialize: bool
    disp_copyright_info_readonly: bool
    disp_copyright_info_media_writes: int
    target_container: str
    is_still_exif_container: bool
    still_exif_tags_written: bool
    exif_artist_tag_hex: str
    exif_copyright_tag_hex: str
    movie_or_raw_exif_mutation_bytes: int
    slot1_recovery_vault_mutation_bytes: int
    excluded_from_camset_saveload: bool
    camset_copyright_export_bytes: int
    photographer_copyright_pii_leaked_bytes: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G106CopyrightInfo46CharStillExifGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    copyright_info_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master106GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    offline_103_gates_verified: bool
    all_106_gates_verified: bool
    g13_to_g106_all_passed: bool
    g105_to_g106_all_passed: bool
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
    master_104_report: Dict[str, Any]
    g105_result: Dict[str, Any]
    g106_result: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Internal Helpers & Normalization
# ---------------------------------------------------------------------------

_TRUTHY_CLEAN_ROOM_TOKENS: Tuple[str, ...] = ("1", "true", "TRUE", "yes", "YES")


def _is_forced_clean_room(force_clean_room: Optional[bool] = None) -> bool:
    if force_clean_room is not None:
        return bool(force_clean_room)
    for env_key in (ENV_FORCE_CLEAN_ROOM, ENV_CLEAN_ROOM_TEST_PHASE266):
        if os.environ.get(env_key, "").strip() in _TRUTHY_CLEAN_ROOM_TOKENS:
            return True
    return False


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


def _norm_reset_action_phase266(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if u in ("NONE", "NO RESET", ""):
        return RESET_ACTION_NONE
    if u == "CAMERA SETTINGS RESET":
        return RESET_ACTION_CAMERA_SETTINGS_RESET
    if u in ("RESET NETWORK SET.", "RESET NETWORK SET", "RESET NETWORK SETTINGS"):
        return RESET_ACTION_RESET_NETWORK_SET_PHASE266
    if u == "INITIALIZE":
        return RESET_ACTION_INITIALIZE
    return None


def _norm_on_off_phase266(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if u == "ON":
        return "On"
    if u == "OFF":
        return "Off"
    return None


def _norm_enable_disable_g105(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if u == "ENABLE":
        return RELEASE_ENABLE_G105
    if u == "DISABLE":
        return RELEASE_DISABLE_G105
    return None


def _norm_capture_mode_g105(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if u in ("STILL", "STILL IMAGE", "PHOTO"):
        return CAPTURE_MODE_STILL_G105
    if u in ("MOVIE", "VIDEO"):
        return CAPTURE_MODE_MOVIE_G105
    if u in ("S&Q", "SQ", "S&Q MOTION", "SLOW & QUICK"):
        return CAPTURE_MODE_SQ_G105
    return None


def _norm_bench_posture_g105(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", "_", raw.strip().strip("[]").upper())
    if u in ("CARDLESS_DIAGNOSTIC_BENCH", "DIAGNOSTIC_BENCH", "BENCH"):
        return BENCH_POSTURE_CARDLESS_DIAGNOSTIC_G105
    if u in ("PRODUCTION_SHOOT", "PRODUCTION"):
        return BENCH_POSTURE_PRODUCTION_SHOOT_G105
    return None


def _norm_lens_mount_state_g105(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", "_", raw.strip().strip("[]").replace("-", "_").upper())
    if u in ("BODY_ONLY_BENCH", "BODY_ONLY", "NO_LENS"):
        return LENS_MOUNT_BODY_ONLY_BENCH_G105
    if u in ("PL_MECHANICAL_ADAPTER", "PL_ADAPTER", "MECHANICAL_ADAPTER", "TELESCOPE"):
        return LENS_MOUNT_PL_MECHANICAL_ADAPTER_G105
    if u in ("ELECTRONIC_E_MOUNT", "E_MOUNT", "FE_LENS", "ELECTRONIC_LENS"):
        return LENS_MOUNT_ELECTRONIC_EMOUNT_G105
    return None


def _norm_audio_out_timing_g105(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if u == "LIVE":
        return AUDIO_OUT_TIMING_LIVE_G105
    if u in ("LIP SYNC", "LIPSYNC"):
        return AUDIO_OUT_TIMING_LIP_SYNC_G105
    return None


def _norm_shoe_audio_set_g105(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).lower()
    if u == "48khz/16bit 2ch":
        return SHOE_AUDIO_48K_16B_2CH_G105
    if u == "48khz/24bit 2ch":
        return SHOE_AUDIO_48K_24B_2CH_G105
    if u == "48khz/24bit 4ch":
        return SHOE_AUDIO_48K_24B_4CH_G105
    return None


def _norm_target_container_g106(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", "_", raw.strip().strip("[]").replace("-", "_").upper())
    mapping = {
        "STILL_JPEG": CONTAINER_STILL_JPEG_G106,
        "JPEG": CONTAINER_STILL_JPEG_G106,
        "JPG": CONTAINER_STILL_JPEG_G106,
        "STILL_HEIF": CONTAINER_STILL_HEIF_G106,
        "HEIF": CONTAINER_STILL_HEIF_G106,
        "HIF": CONTAINER_STILL_HEIF_G106,
        "STILL_ARW": CONTAINER_STILL_ARW_G106,
        "ARW": CONTAINER_STILL_ARW_G106,
        "MOVIE_XAVC_HS_MP4": CONTAINER_MOVIE_XAVC_HS_MP4_G106,
        "XAVC_HS_4K": CONTAINER_MOVIE_XAVC_HS_MP4_G106,
        "MOVIE_XAVC_S_MP4": CONTAINER_MOVIE_XAVC_S_MP4_G106,
        "XAVC_S_4K": CONTAINER_MOVIE_XAVC_S_MP4_G106,
        "MOVIE_XAVC_SI_MP4": CONTAINER_MOVIE_XAVC_SI_MP4_G106,
        "XAVC_SI_4K": CONTAINER_MOVIE_XAVC_SI_MP4_G106,
        "HDMI_RAW_STREAM": CONTAINER_HDMI_RAW_STREAM_G106,
        "HDMI_RAW": CONTAINER_HDMI_RAW_STREAM_G106,
    }
    return mapping.get(u)


def _is_valid_46char_printable_ascii_g106(val: Any) -> bool:
    if not isinstance(val, str):
        return False
    if len(val) > COPYRIGHT_INFO_MAX_CHARS_G106:
        return False
    return all(
        ASCII_PRINTABLE_MIN_CODEPOINT_G106
        <= ord(ch)
        <= ASCII_PRINTABLE_MAX_CODEPOINT_G106
        for ch in val
    )


# ---------------------------------------------------------------------------
# 1. Bounded `< 0.10s` O_RDONLY Donor Contract Audit (`Phase 266`)
# ---------------------------------------------------------------------------


def audit_phase266_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    max_budget_seconds: float = DONOR_CHECK_MAX_SECONDS_PHASE266,
) -> Phase266DonorAuditResult:
    """Inspect local FX3 Ver. 7.02 / FX6 Ver. 6.01 donor artifacts strictly
    `os.O_RDONLY` within `<0.10s`, verifying bounded Wave-43 symbols across
    `cpapp-b.bin`, `libgpe.so`, `libSaveLoadSettings.so`,
    `FX3-CX95900_ALLLANG-Backup.bin`, `libInfraDial.so`, and `CX95898_NTSC.bin`
    with deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` / `FX3_CLEAN_ROOM_TEST=1` parity.
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
        for key, (_body, rel_path, *_rest) in PINNED_PHASE266_DONOR_SPECS.items():
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
            spec[5] for spec in PINNED_PHASE266_DONOR_SPECS.values()
        )
        synthetic_shas = {
            k: f"synthetic:{v[3][:16]}" for k, v in PINNED_PHASE266_DONOR_SPECS.items()
        }
        synthetic_sizes = {k: v[2] for k, v in PINNED_PHASE266_DONOR_SPECS.items()}
        return Phase266DonorAuditResult(
            valid=within_budget,
            status=(
                STATUS_VERIFIED_SAFE
                if within_budget
                else STATUS_BLOCKED_PHASE266_DONOR_INTEGRITY
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
    ) in PINNED_PHASE266_DONOR_SPECS.items():
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
            errors.append(f"Missing required Wave-43 byte markers in {key}.")

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

    fx3_keys = {k for k, v in PINNED_PHASE266_DONOR_SPECS.items() if v[0] == "FX3"}
    fx6_keys = {k for k, v in PINNED_PHASE266_DONOR_SPECS.items() if v[0] == "FX6"}
    fx3_ok = fx3_keys.issubset(passed_keys)
    fx6_ok = fx6_keys.issubset(passed_keys)
    valid = fx3_ok and fx6_ok and (not missing) and within_budget and (not errors)

    return Phase266DonorAuditResult(
        valid=valid,
        status=(
            STATUS_VERIFIED_SAFE
            if valid
            else STATUS_BLOCKED_PHASE266_DONOR_INTEGRITY
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
# 2. Gate `G105`: `[Release w/o Card]` & `[Release w/o Lens]` + `Ver. 7.02`
#    5-Item `[Audio Recording]` vs `[DISP (Screen Disp) Set]` Audio Meter Guard
# ---------------------------------------------------------------------------


def compute_release_wo_card_and_lens_scope_matrix() -> Dict[str, Any]:
    """Exhaustively evaluate all `2 x 2 x 2 x 2 x 3 x 2 = 96` combinations of
    `(any_card_inserted, release_wo_card, electronic_lens_attached, release_wo_lens,
    capture_mode, rec_media_dur_hdmi_output)` on `ILME-FX3` (`Ver. 7.02`, `ilc/2210`),
    proving:
    - `[Release w/o Card]` governs Still shutter release without card ONLY;
    - Movie / `S&Q` internal media recording is ALWAYS blocked (`False`) when
      both slots are empty (`movie_cardless_internal_rec_bypass_events == 0`);
    - `[Release w/o Lens]` governs Still + Movie + `S&Q` uniformly;
    - Body-only / mechanical-adapter states emit `0` E-mount `E-ND` / lens UART bytes.
    """
    states_checked = 0
    cardless_still_enabled_count = 0
    cardless_still_blocked_count = 0
    movie_cardless_bypass_events = 0
    lensless_blocked_across_all_modes_count = 0

    for any_card in (False, True):
        for rel_card in ALLOWED_RELEASE_ENABLE_DISABLE_G105:
            for has_elec_lens in (False, True):
                for rel_lens in ALLOWED_RELEASE_ENABLE_DISABLE_G105:
                    for mode in ALLOWED_CAPTURE_MODES_G105:
                        for hdmi_rec_media in ALLOWED_HDMI_REC_MEDIA_SETTINGS_G105:
                            states_checked += 1
                            lens_ok = has_elec_lens or (rel_lens == RELEASE_ENABLE_G105)
                            if not lens_ok:
                                lensless_blocked_across_all_modes_count += 1

                            if mode == CAPTURE_MODE_STILL_G105:
                                card_ok = any_card or (rel_card == RELEASE_ENABLE_G105)
                                still_allowed = lens_ok and card_ok
                                if (not any_card) and lens_ok:
                                    if rel_card == RELEASE_ENABLE_G105 and still_allowed:
                                        cardless_still_enabled_count += 1
                                    elif rel_card == RELEASE_DISABLE_G105 and (not still_allowed):
                                        cardless_still_blocked_count += 1
                            else:
                                internal_rec = (
                                    lens_ok
                                    and any_card
                                    and (hdmi_rec_media == HDMI_REC_MEDIA_ON_G105)
                                )
                                if (not any_card) and internal_rec:
                                    movie_cardless_bypass_events += 1

    return {
        "states_checked": states_checked,
        "cardless_still_enabled_count": cardless_still_enabled_count,
        "cardless_still_blocked_count": cardless_still_blocked_count,
        "lensless_blocked_across_all_modes_count": lensless_blocked_across_all_modes_count,
        "movie_cardless_internal_rec_bypass_events": movie_cardless_bypass_events,
    }


def resolve_fx3_release_wo_card_lens_and_v702_audio_disp_state(
    *,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE266,
    bench_posture: str = BENCH_POSTURE_CARDLESS_DIAGNOSTIC_G105,
    reset_action: str = RESET_ACTION_NONE,
    capture_mode: str = CAPTURE_MODE_STILL_G105,
    pre_reset_release_wo_card: str = RELEASE_WO_CARD_FACTORY_DEFAULT_G105,
    slot1_card_inserted: bool = False,
    slot2_card_inserted: bool = False,
    hdmi_external_capture_connected: bool = False,
    rec_media_dur_hdmi_output: str = HDMI_REC_MEDIA_OFF_G105,
    pre_reset_release_wo_lens: str = RELEASE_WO_LENS_FACTORY_DEFAULT_G105,
    lens_mount_state: str = LENS_MOUNT_BODY_ONLY_BENCH_G105,
    pre_reset_audio_recording: str = AUDIO_RECORDING_FACTORY_DEFAULT_G105,
    pre_reset_audio_rec_level: int = AUDIO_REC_LEVEL_FACTORY_DEFAULT_G105,
    pre_reset_audio_out_timing: str = AUDIO_OUT_TIMING_FACTORY_DEFAULT_G105,
    pre_reset_wind_noise_reduct: str = WIND_NOISE_REDUCT_FACTORY_DEFAULT_G105,
    pre_reset_shoe_audio_set: str = SHOE_AUDIO_FACTORY_DEFAULT_G105,
    digital_mi_shoe_4ch_attached: bool = False,
    pre_reset_disp_audio_level_checked: bool = True,
) -> Dict[str, Any]:
    """Deterministic state resolver for Wave-43 Gate `G105`."""
    norm_reset = _norm_reset_action_phase266(reset_action) or RESET_ACTION_NONE
    norm_mode = _norm_capture_mode_g105(capture_mode) or CAPTURE_MODE_STILL_G105
    norm_posture = (
        _norm_bench_posture_g105(bench_posture)
        or BENCH_POSTURE_CARDLESS_DIAGNOSTIC_G105
    )
    norm_rel_card = (
        _norm_enable_disable_g105(pre_reset_release_wo_card)
        or RELEASE_WO_CARD_FACTORY_DEFAULT_G105
    )
    norm_rel_lens = (
        _norm_enable_disable_g105(pre_reset_release_wo_lens)
        or RELEASE_WO_LENS_FACTORY_DEFAULT_G105
    )
    norm_lens_mount = (
        _norm_lens_mount_state_g105(lens_mount_state)
        or LENS_MOUNT_BODY_ONLY_BENCH_G105
    )
    norm_hdmi_rec_media = (
        _norm_on_off_phase266(rec_media_dur_hdmi_output) or HDMI_REC_MEDIA_OFF_G105
    )

    norm_audio_rec = (
        _norm_on_off_phase266(pre_reset_audio_recording)
        or AUDIO_RECORDING_FACTORY_DEFAULT_G105
    )
    norm_audio_timing = (
        _norm_audio_out_timing_g105(pre_reset_audio_out_timing)
        or AUDIO_OUT_TIMING_FACTORY_DEFAULT_G105
    )
    norm_wind = (
        _norm_on_off_phase266(pre_reset_wind_noise_reduct)
        or WIND_NOISE_REDUCT_FACTORY_DEFAULT_G105
    )
    norm_shoe = (
        _norm_shoe_audio_set_g105(pre_reset_shoe_audio_set)
        or SHOE_AUDIO_FACTORY_DEFAULT_G105
    )

    # Persistence rules:
    # - [Release w/o Card], [Release w/o Lens], and [DISP (Screen Disp) Set]
    #   survive [Camera Settings Reset] & [Reset Network Set.], reset on [Initialize].
    # - Shooting -> [Audio Recording] 5 items reset on [Camera Settings Reset] & [Initialize].
    if norm_reset == RESET_ACTION_INITIALIZE:
        eff_rel_card = RELEASE_WO_CARD_FACTORY_DEFAULT_G105
        eff_rel_lens = RELEASE_WO_LENS_FACTORY_DEFAULT_G105
        eff_disp_audio = True
        eff_audio_rec = AUDIO_RECORDING_FACTORY_DEFAULT_G105
        eff_audio_level = AUDIO_REC_LEVEL_FACTORY_DEFAULT_G105
        eff_audio_timing = AUDIO_OUT_TIMING_FACTORY_DEFAULT_G105
        eff_wind = WIND_NOISE_REDUCT_FACTORY_DEFAULT_G105
        eff_shoe = SHOE_AUDIO_FACTORY_DEFAULT_G105
    elif norm_reset == RESET_ACTION_CAMERA_SETTINGS_RESET:
        eff_rel_card = norm_rel_card
        eff_rel_lens = norm_rel_lens
        eff_disp_audio = bool(pre_reset_disp_audio_level_checked)
        eff_audio_rec = AUDIO_RECORDING_FACTORY_DEFAULT_G105
        eff_audio_level = AUDIO_REC_LEVEL_FACTORY_DEFAULT_G105
        eff_audio_timing = AUDIO_OUT_TIMING_FACTORY_DEFAULT_G105
        eff_wind = WIND_NOISE_REDUCT_FACTORY_DEFAULT_G105
        eff_shoe = SHOE_AUDIO_FACTORY_DEFAULT_G105
    else:
        eff_rel_card = norm_rel_card
        eff_rel_lens = norm_rel_lens
        eff_disp_audio = bool(pre_reset_disp_audio_level_checked)
        eff_audio_rec = norm_audio_rec
        eff_audio_level = int(pre_reset_audio_rec_level)
        eff_audio_timing = norm_audio_timing
        eff_wind = norm_wind
        eff_shoe = norm_shoe

    any_card = bool(slot1_card_inserted) or bool(slot2_card_inserted)
    cardless_bench = not any_card
    elec_lens = norm_lens_mount == LENS_MOUNT_ELECTRONIC_EMOUNT_G105
    lens_permits = elec_lens or (eff_rel_lens == RELEASE_ENABLE_G105)

    still_card_permits = any_card or (eff_rel_card == RELEASE_ENABLE_G105)
    still_shutter_allowed = (
        (lens_permits and still_card_permits)
        if norm_mode == CAPTURE_MODE_STILL_G105
        else False
    )
    still_saved = bool(still_shutter_allowed and any_card)

    if norm_mode in (CAPTURE_MODE_MOVIE_G105, CAPTURE_MODE_SQ_G105):
        hdmi_inhibits_internal = bool(hdmi_external_capture_connected) and (
            norm_hdmi_rec_media == HDMI_REC_MEDIA_OFF_G105
        )
        movie_internal_allowed = bool(
            lens_permits and any_card and (not hdmi_inhibits_internal)
        )
        ext_hdmi_rec_allowed = bool(lens_permits and hdmi_external_capture_connected)
        effective_release_permitted = bool(
            movie_internal_allowed or ext_hdmi_rec_allowed
        )
    else:
        movie_internal_allowed = False
        ext_hdmi_rec_allowed = False
        effective_release_permitted = still_shutter_allowed

    sq_suppressed = norm_mode == CAPTURE_MODE_SQ_G105
    if sq_suppressed or eff_audio_rec == AUDIO_RECORDING_OFF_G105:
        meter_visible = False
        meter_channels = 0
    else:
        meter_visible = bool(eff_disp_audio)
        if not meter_visible:
            meter_channels = 0
        elif (
            eff_shoe == SHOE_AUDIO_48K_24B_4CH_G105
            and bool(digital_mi_shoe_4ch_attached)
        ):
            meter_channels = 4
        else:
            meter_channels = 2

    return {
        "bench_posture": norm_posture,
        "reset_action": norm_reset,
        "capture_mode": norm_mode,
        "effective_post_reset_release_wo_card": eff_rel_card,
        "effective_post_reset_release_wo_lens": eff_rel_lens,
        "any_card_inserted": any_card,
        "cardless_bench_active": cardless_bench,
        "lens_mount_state": norm_lens_mount,
        "electronic_emount_lens_attached": elec_lens,
        "lens_gate_permits_release": lens_permits,
        "still_shutter_release_allowed": still_shutter_allowed,
        "still_image_saved_to_card": still_saved,
        "movie_internal_rec_allowed": movie_internal_allowed,
        "rec_media_dur_hdmi_output": norm_hdmi_rec_media,
        "external_hdmi_rec_allowed": ext_hdmi_rec_allowed,
        "effective_release_permitted": effective_release_permitted,
        "effective_post_reset_audio_recording": eff_audio_rec,
        "effective_post_reset_audio_rec_level": eff_audio_level,
        "effective_post_reset_audio_out_timing": eff_audio_timing,
        "effective_post_reset_wind_noise_reduct": eff_wind,
        "effective_post_reset_shoe_audio_set": eff_shoe,
        "effective_post_reset_disp_audio_level_checked": eff_disp_audio,
        "sq_audio_meter_suppressed": sq_suppressed,
        "effective_audio_meter_visible": meter_visible,
        "effective_audio_meter_channels": meter_channels,
        "fw_is_v2_or_later": (
            (_parse_fw_tuple(firmware_version) or (0, 0))
            >= FX3_V2_AUDIO_DISP_MIN_FW_TUPLE_G105
        ),
    }


def verify_release_wo_card_lens_and_v702_audio_disp_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: int = FX3_MODEL_ID,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE266,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE266,
    bench_posture: str = BENCH_POSTURE_CARDLESS_DIAGNOSTIC_G105,
    reset_action: str = RESET_ACTION_NONE,
    capture_mode: str = CAPTURE_MODE_STILL_G105,
    pre_reset_release_wo_card: str = RELEASE_WO_CARD_FACTORY_DEFAULT_G105,
    slot1_card_inserted: bool = False,
    slot2_card_inserted: bool = False,
    hdmi_external_capture_connected: bool = False,
    rec_media_dur_hdmi_output: str = HDMI_REC_MEDIA_OFF_G105,
    pre_reset_release_wo_lens: str = RELEASE_WO_LENS_FACTORY_DEFAULT_G105,
    lens_mount_state: str = LENS_MOUNT_BODY_ONLY_BENCH_G105,
    audio_recording_menu_items: Sequence[str] = V702_AUDIO_RECORDING_EXACT_5_ITEMS_G105,
    pre_reset_audio_recording: str = AUDIO_RECORDING_FACTORY_DEFAULT_G105,
    pre_reset_audio_rec_level: int = AUDIO_REC_LEVEL_FACTORY_DEFAULT_G105,
    pre_reset_audio_out_timing: str = AUDIO_OUT_TIMING_FACTORY_DEFAULT_G105,
    pre_reset_wind_noise_reduct: str = WIND_NOISE_REDUCT_FACTORY_DEFAULT_G105,
    pre_reset_shoe_audio_set: str = SHOE_AUDIO_FACTORY_DEFAULT_G105,
    digital_mi_shoe_4ch_attached: bool = False,
    pre_reset_disp_audio_level_checked: bool = True,
    claimed_cardless_media_sector_writes: int = 0,
    claimed_still_shutter_release_allowed: Optional[bool] = None,
    claimed_movie_internal_rec_allowed: Optional[bool] = None,
    claimed_lens_gate_permits_release: Optional[bool] = None,
    claimed_e_nd_actuator_tx_count: int = 0,
    claimed_emount_lens_uart_tx_bytes: int = 0,
    claimed_legacy_v1_audio_level_menu_spoof_events: int = 0,
    claimed_audio_meter_visible: Optional[bool] = None,
    claimed_audio_meter_channels: Optional[int] = None,
    claimed_post_reset_release_wo_card: Optional[str] = None,
    claimed_post_reset_release_wo_lens: Optional[str] = None,
    claimed_post_reset_audio_rec_level: Optional[int] = None,
    claimed_post_reset_disp_audio_level_checked: Optional[bool] = None,
) -> ReleaseWoCardLensAndV702AudioDispGuardResult:
    """Verify Gate `G105` across `[Release w/o Card]`, `[Release w/o Lens]`,
    and `Ver. 2.00+`/`7.02` (`ilc/2210`) 5-item `[Audio Recording]` vs
    `[DISP (Screen Disp) Set]` audio level meter governance.
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    fw_tuple = _parse_fw_tuple(firmware_version)
    norm_reset = _norm_reset_action_phase266(reset_action)
    norm_mode = _norm_capture_mode_g105(capture_mode)
    norm_posture = _norm_bench_posture_g105(bench_posture)
    norm_rel_card = _norm_enable_disable_g105(pre_reset_release_wo_card)
    norm_rel_lens = _norm_enable_disable_g105(pre_reset_release_wo_lens)
    norm_lens_mount = _norm_lens_mount_state_g105(lens_mount_state)
    norm_hdmi_rec = _norm_on_off_phase266(rec_media_dur_hdmi_output)
    norm_audio_rec = _norm_on_off_phase266(pre_reset_audio_recording)
    norm_audio_timing = _norm_audio_out_timing_g105(pre_reset_audio_out_timing)
    norm_wind = _norm_on_off_phase266(pre_reset_wind_noise_reduct)
    norm_shoe = _norm_shoe_audio_set_g105(pre_reset_shoe_audio_set)

    level_ok = (
        isinstance(pre_reset_audio_rec_level, int)
        and not isinstance(pre_reset_audio_rec_level, bool)
        and (
            AUDIO_REC_LEVEL_MIN_G105
            <= pre_reset_audio_rec_level
            <= AUDIO_REC_LEVEL_MAX_G105
        )
    )

    if help_guide_code == FX3_LEGACY_V1_HELP_GUIDE_CODE_G105 or (
        fw_tuple is not None and fw_tuple < FX3_V2_AUDIO_DISP_MIN_FW_TUPLE_G105
    ):
        _add_code(codes, STATUS_BLOCKED_G105_LEGACY_V1_AUDIO_LEVEL_MENU_SPOOF_VIOLATION)
        errors.append(
            "Legacy Ver. 1.x (ilc/2035) firmware/help-guide baseline rejected on Ver. 7.02 (ilc/2210) bench."
        )
    elif (
        body_model_name != FX3_MODEL_NAME
        or body_model_id != FX3_MODEL_ID
        or help_guide_code != FX3_HELP_GUIDE_CODE_PHASE266
        or fw_tuple is None
        or norm_reset is None
        or norm_mode is None
        or norm_posture is None
        or norm_rel_card is None
        or norm_rel_lens is None
        or norm_lens_mount is None
        or norm_hdmi_rec is None
        or norm_audio_rec is None
        or not level_ok
        or norm_audio_timing is None
        or norm_wind is None
        or norm_shoe is None
        or not isinstance(audio_recording_menu_items, (list, tuple))
    ):
        _add_code(codes, STATUS_BLOCKED_G105_TELEMETRY_INVALID)
        errors.append("Invalid ILME-FX3 Gate G105 release/audio/DISP telemetry.")

    resolved = resolve_fx3_release_wo_card_lens_and_v702_audio_disp_state(
        firmware_version=firmware_version,
        bench_posture=norm_posture or BENCH_POSTURE_CARDLESS_DIAGNOSTIC_G105,
        reset_action=norm_reset or RESET_ACTION_NONE,
        capture_mode=norm_mode or CAPTURE_MODE_STILL_G105,
        pre_reset_release_wo_card=norm_rel_card or RELEASE_WO_CARD_FACTORY_DEFAULT_G105,
        slot1_card_inserted=bool(slot1_card_inserted),
        slot2_card_inserted=bool(slot2_card_inserted),
        hdmi_external_capture_connected=bool(hdmi_external_capture_connected),
        rec_media_dur_hdmi_output=norm_hdmi_rec or HDMI_REC_MEDIA_OFF_G105,
        pre_reset_release_wo_lens=norm_rel_lens or RELEASE_WO_LENS_FACTORY_DEFAULT_G105,
        lens_mount_state=norm_lens_mount or LENS_MOUNT_BODY_ONLY_BENCH_G105,
        pre_reset_audio_recording=norm_audio_rec or AUDIO_RECORDING_FACTORY_DEFAULT_G105,
        pre_reset_audio_rec_level=(
            pre_reset_audio_rec_level
            if level_ok
            else AUDIO_REC_LEVEL_FACTORY_DEFAULT_G105
        ),
        pre_reset_audio_out_timing=(
            norm_audio_timing or AUDIO_OUT_TIMING_FACTORY_DEFAULT_G105
        ),
        pre_reset_wind_noise_reduct=norm_wind or WIND_NOISE_REDUCT_FACTORY_DEFAULT_G105,
        pre_reset_shoe_audio_set=norm_shoe or SHOE_AUDIO_FACTORY_DEFAULT_G105,
        digital_mi_shoe_4ch_attached=bool(digital_mi_shoe_4ch_attached),
        pre_reset_disp_audio_level_checked=bool(pre_reset_disp_audio_level_checked),
    )
    matrix = compute_release_wo_card_and_lens_scope_matrix()

    eff_rel_card = str(resolved["effective_post_reset_release_wo_card"])
    eff_rel_lens = str(resolved["effective_post_reset_release_wo_lens"])
    cardless = bool(resolved["cardless_bench_active"])
    cardless_writes = max(0, int(claimed_cardless_media_sector_writes))

    # 1. [Release w/o Card] production anti-unrecorded-shoot & still scope checks
    if (
        norm_posture == BENCH_POSTURE_PRODUCTION_SHOOT_G105
        and eff_rel_card != RELEASE_DISABLE_G105
    ):
        _add_code(
            codes, STATUS_BLOCKED_G105_RELEASE_WO_CARD_SCOPE_OR_PRODUCTION_VIOLATION
        )
        errors.append(
            "Production shoot posture requires [Release w/o Card] = [Disable] to block accidental unrecorded shoots."
        )
    if (
        norm_posture == BENCH_POSTURE_CARDLESS_DIAGNOSTIC_G105
        and not cardless
    ):
        _add_code(
            codes, STATUS_BLOCKED_G105_RELEASE_WO_CARD_SCOPE_OR_PRODUCTION_VIOLATION
        )
        errors.append(
            "Cardless diagnostic bench posture requires both Slot-1 and Slot-2 to be empty."
        )
    if cardless and cardless_writes > 0:
        _add_code(
            codes, STATUS_BLOCKED_G105_RELEASE_WO_CARD_SCOPE_OR_PRODUCTION_VIOLATION
        )
        errors.append("Cardless bench reported non-zero media sector writes.")
    if (
        claimed_still_shutter_release_allowed is not None
        and bool(claimed_still_shutter_release_allowed)
        != bool(resolved["still_shutter_release_allowed"])
    ):
        _add_code(
            codes, STATUS_BLOCKED_G105_RELEASE_WO_CARD_SCOPE_OR_PRODUCTION_VIOLATION
        )
        errors.append(
            "Claimed Still shutter release state contradicts [Release w/o Card] / [Release w/o Lens] gate."
        )

    # 2. Movie internal media gate vs [Release w/o Card] Still-only scope
    movie_bypass_events = int(matrix["movie_cardless_internal_rec_bypass_events"])
    if claimed_movie_internal_rec_allowed is not None and bool(
        claimed_movie_internal_rec_allowed
    ) != bool(resolved["movie_internal_rec_allowed"]):
        movie_bypass_events += 1
        _add_code(
            codes, STATUS_BLOCKED_G105_MOVIE_CARDLESS_INTERNAL_REC_BYPASS_VIOLATION
        )
        errors.append(
            "Movie / S&Q internal recording bypass detected (internal movie capture is strictly blocked when slots are empty or inhibited by [Rec. Media dur HDMI Output]=Off)."
        )

    # 3. [Release w/o Lens] Still + Movie + S&Q scope & zero E-ND / zero lens UART on body-only bench
    e_nd_tx = max(0, int(claimed_e_nd_actuator_tx_count))
    lens_uart_tx = max(0, int(claimed_emount_lens_uart_tx_bytes))
    elec_lens = bool(resolved["electronic_emount_lens_attached"])
    if (
        e_nd_tx > 0
        or ((not elec_lens) and lens_uart_tx > 0)
        or (
            claimed_lens_gate_permits_release is not None
            and bool(claimed_lens_gate_permits_release)
            != bool(resolved["lens_gate_permits_release"])
        )
    ):
        _add_code(codes, STATUS_BLOCKED_G105_RELEASE_WO_LENS_OR_END_UART_VIOLATION)
        errors.append(
            "ILME-FX3 has zero internal E-ND actuator (e_nd_actuator_tx_count == 0) and emits zero E-mount lens UART bytes on body-only/PL-mount bench."
        )

    # 4. Ver. 2.00+/7.02 (ilc/2210) exact 5-item [Audio Recording] menu vs Ver. 1.x [Audio Level Display] removal
    menu_tuple = (
        tuple(str(x).strip() for x in audio_recording_menu_items)
        if isinstance(audio_recording_menu_items, (list, tuple))
        else ()
    )
    has_disallowed_v1 = any(
        item in DISALLOWED_V1_AUDIO_MENU_ITEMS_G105
        or item.strip("[]").lower() == "audio level display"
        for item in menu_tuple
    )
    exact_5_ok = (menu_tuple == V702_AUDIO_RECORDING_EXACT_5_ITEMS_G105) and (
        not has_disallowed_v1
    )
    spoof_events = max(0, int(claimed_legacy_v1_audio_level_menu_spoof_events))
    if not exact_5_ok:
        spoof_events = max(1, spoof_events)
    if spoof_events > 0:
        _add_code(codes, STATUS_BLOCKED_G105_LEGACY_V1_AUDIO_LEVEL_MENU_SPOOF_VIOLATION)
        errors.append(
            "Ver. 2.00+/7.02 (ilc/2210) [Audio Recording] must expose the exact 5 items without Ver. 1.x standalone [Audio Level Display]."
        )

    # 5. [DISP (Screen Disp) Set] 2ch/4ch audio meter visibility & S&Q suppression
    if (
        claimed_audio_meter_visible is not None
        and bool(claimed_audio_meter_visible)
        != bool(resolved["effective_audio_meter_visible"])
    ) or (
        claimed_audio_meter_channels is not None
        and int(claimed_audio_meter_channels)
        != int(resolved["effective_audio_meter_channels"])
    ):
        _add_code(
            codes, STATUS_BLOCKED_G105_DISP_AUDIO_METER_OR_SQ_SUPPRESSION_VIOLATION
        )
        errors.append(
            "Audio level meter visibility/channel count contradicts [DISP (Screen Disp) Set], 4ch MI-shoe state, or S&Q suppression."
        )

    # 6. Reset persistence split check
    if (
        (
            claimed_post_reset_release_wo_card is not None
            and _norm_enable_disable_g105(claimed_post_reset_release_wo_card)
            != eff_rel_card
        )
        or (
            claimed_post_reset_release_wo_lens is not None
            and _norm_enable_disable_g105(claimed_post_reset_release_wo_lens)
            != eff_rel_lens
        )
        or (
            claimed_post_reset_audio_rec_level is not None
            and int(claimed_post_reset_audio_rec_level)
            != int(resolved["effective_post_reset_audio_rec_level"])
        )
        or (
            claimed_post_reset_disp_audio_level_checked is not None
            and bool(claimed_post_reset_disp_audio_level_checked)
            != bool(resolved["effective_post_reset_disp_audio_level_checked"])
        )
    ):
        _add_code(codes, STATUS_BLOCKED_G105_RESET_PERSISTENCE_VIOLATION)
        errors.append(
            "Post-reset persistence drift across [Release w/o Card], [Release w/o Lens], [Audio Recording], or [DISP (Screen Disp) Set]."
        )

    valid = not codes
    status = STATUS_VERIFIED_G105 if valid else codes[0]

    return ReleaseWoCardLensAndV702AudioDispGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=str(body_model_name),
        body_model_id_hex=f"0x{body_model_id:08X}"
        if isinstance(body_model_id, int)
        else "INVALID",
        help_guide_code=str(help_guide_code),
        firmware_version=str(firmware_version),
        bench_posture=norm_posture or str(bench_posture),
        reset_action=norm_reset or str(reset_action),
        capture_mode=norm_mode or str(capture_mode),
        release_wo_card_menu_path=RELEASE_WO_CARD_MENU_PATH_G105,
        release_wo_card_factory_default=RELEASE_WO_CARD_FACTORY_DEFAULT_G105,
        pre_reset_release_wo_card=norm_rel_card or str(pre_reset_release_wo_card),
        effective_post_reset_release_wo_card=eff_rel_card,
        release_wo_card_survives_camera_settings_reset=True,
        slot1_card_inserted=bool(slot1_card_inserted),
        slot2_card_inserted=bool(slot2_card_inserted),
        cardless_bench_active=cardless,
        still_shutter_release_allowed=bool(resolved["still_shutter_release_allowed"]),
        still_image_saved_to_card=bool(resolved["still_image_saved_to_card"]),
        cardless_media_sector_writes=cardless_writes,
        movie_internal_rec_allowed=bool(resolved["movie_internal_rec_allowed"]),
        movie_cardless_internal_rec_bypass_events=movie_bypass_events,
        hdmi_external_capture_connected=bool(hdmi_external_capture_connected),
        rec_media_dur_hdmi_output=str(resolved["rec_media_dur_hdmi_output"]),
        external_hdmi_capture_governed_by_rec_media=True,
        external_hdmi_rec_allowed=bool(resolved["external_hdmi_rec_allowed"]),
        release_wo_lens_menu_path=RELEASE_WO_LENS_MENU_PATH_G105,
        release_wo_lens_factory_default=RELEASE_WO_LENS_FACTORY_DEFAULT_G105,
        pre_reset_release_wo_lens=norm_rel_lens or str(pre_reset_release_wo_lens),
        effective_post_reset_release_wo_lens=eff_rel_lens,
        release_wo_lens_survives_camera_settings_reset=True,
        lens_mount_state=norm_lens_mount or str(lens_mount_state),
        electronic_emount_lens_attached=elec_lens,
        lens_gate_permits_release=bool(resolved["lens_gate_permits_release"]),
        effective_release_permitted=bool(resolved["effective_release_permitted"]),
        e_nd_actuator_tx_count=e_nd_tx,
        emount_lens_uart_tx_bytes=lens_uart_tx,
        release_scope_matrix_states_checked=int(matrix["states_checked"]),
        audio_recording_menu_path=AUDIO_RECORDING_MENU_PATH_G105,
        disp_screen_disp_set_menu_path=DISP_SCREEN_DISP_SET_MENU_PATH_G105,
        v702_audio_recording_menu_items=menu_tuple,
        v702_audio_menu_exact_5_items_verified=exact_5_ok,
        legacy_v1_audio_level_menu_spoof_events=spoof_events,
        pre_reset_audio_recording=norm_audio_rec or str(pre_reset_audio_recording),
        effective_post_reset_audio_recording=str(
            resolved["effective_post_reset_audio_recording"]
        ),
        pre_reset_audio_rec_level=(
            int(pre_reset_audio_rec_level)
            if isinstance(pre_reset_audio_rec_level, int)
            else -1
        ),
        effective_post_reset_audio_rec_level=int(
            resolved["effective_post_reset_audio_rec_level"]
        ),
        pre_reset_audio_out_timing=norm_audio_timing or str(pre_reset_audio_out_timing),
        effective_post_reset_audio_out_timing=str(
            resolved["effective_post_reset_audio_out_timing"]
        ),
        pre_reset_wind_noise_reduct=norm_wind or str(pre_reset_wind_noise_reduct),
        effective_post_reset_wind_noise_reduct=str(
            resolved["effective_post_reset_wind_noise_reduct"]
        ),
        pre_reset_shoe_audio_set=norm_shoe or str(pre_reset_shoe_audio_set),
        effective_post_reset_shoe_audio_set=str(
            resolved["effective_post_reset_shoe_audio_set"]
        ),
        digital_mi_shoe_4ch_attached=bool(digital_mi_shoe_4ch_attached),
        pre_reset_disp_audio_level_checked=bool(pre_reset_disp_audio_level_checked),
        effective_post_reset_disp_audio_level_checked=bool(
            resolved["effective_post_reset_disp_audio_level_checked"]
        ),
        disp_set_survives_camera_settings_reset=True,
        sq_audio_meter_suppressed=bool(resolved["sq_audio_meter_suppressed"]),
        effective_audio_meter_visible=bool(resolved["effective_audio_meter_visible"]),
        effective_audio_meter_channels=int(resolved["effective_audio_meter_channels"]),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g105_release_wo_card_lens_and_v702_audio_disp_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    release_audio_disp_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase266DonorAuditResult] = None,
) -> Tuple[GateVerdict, G105ReleaseWoCardLensAndV702AudioDispGuardResult]:
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase266_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_release_wo_card_lens_and_v702_audio_disp_guard(
        **dict(release_audio_disp_kwargs or {})
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
        errors.append("Persistent eMMC write authorization requested in Gate G105.")
    if not audit.valid:
        _add_code(codes, audit.status)
    for c in guard.violation_codes:
        _add_code(codes, c)

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G105 if valid else codes[0]

    res = G105ReleaseWoCardLensAndV702AudioDispGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        release_audio_disp_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, rel_wo_card={guard.effective_post_reset_release_wo_card}"
        f"(cardless={guard.cardless_bench_active},mv_bypass={guard.movie_cardless_internal_rec_bypass_events}), "
        f"rel_wo_lens={guard.effective_post_reset_release_wo_lens}"
        f"(e_nd_tx={guard.e_nd_actuator_tx_count},lens_uart={guard.emount_lens_uart_tx_bytes}), "
        f"audio_5items={guard.v702_audio_menu_exact_5_items_verified}"
        f"(v1_spoof={guard.legacy_v1_audio_level_menu_spoof_events},"
        f"disp_meter={guard.effective_audio_meter_channels}ch)"
    )
    verdict = GateVerdict(
        gate_id=G105_GATE_ID,
        gate_code=G105_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 3. Gate `G106`: `[Copyright Info]` `<= 46`-Char Printable ASCII Bounds,
#    Still-EXIF-Only Scope, Reset Survival & Clean-Room Bench PII Hygiene Guard
# ---------------------------------------------------------------------------


def resolve_fx3_copyright_info_46char_still_exif_state(
    *,
    reset_action: str = RESET_ACTION_NONE,
    pre_reset_write_copyright_info: str = WRITE_COPYRIGHT_INFO_BENCH_DEFAULT_G106,
    pre_reset_photographer: str = "",
    pre_reset_copyright: str = "",
    target_container: str = CONTAINER_STILL_JPEG_G106,
    clean_room_bench_hygiene_required: bool = True,
) -> Dict[str, Any]:
    """Deterministic state resolver for Wave-43 Gate `G106`."""
    norm_reset = _norm_reset_action_phase266(reset_action) or RESET_ACTION_NONE
    norm_write = (
        _norm_on_off_phase266(pre_reset_write_copyright_info)
        or WRITE_COPYRIGHT_INFO_FACTORY_DEFAULT_G106
    )
    norm_container = (
        _norm_target_container_g106(target_container) or CONTAINER_STILL_JPEG_G106
    )
    raw_photo = pre_reset_photographer if isinstance(pre_reset_photographer, str) else ""
    raw_copy = pre_reset_copyright if isinstance(pre_reset_copyright, str) else ""

    # Official Sony ILME-FX3 Help Guide (ilc/2210) persistence:
    # - [Write Copyright Info] returns to [Off] on [Camera Settings Reset] & [Initialize].
    # - [Set Photographer] & [Set Copyright] SURVIVE [Camera Settings Reset] &
    #   [Reset Network Set.], and are wiped ("") ONLY by [Initialize].
    if norm_reset == RESET_ACTION_INITIALIZE:
        eff_write = WRITE_COPYRIGHT_INFO_FACTORY_DEFAULT_G106
        eff_photo = ""
        eff_copy = ""
    elif norm_reset == RESET_ACTION_CAMERA_SETTINGS_RESET:
        eff_write = WRITE_COPYRIGHT_INFO_FACTORY_DEFAULT_G106
        eff_photo = raw_photo
        eff_copy = raw_copy
    else:
        eff_write = norm_write
        eff_photo = raw_photo
        eff_copy = raw_copy

    is_still = norm_container in STILL_EXIF_ELIGIBLE_CONTAINERS_G106
    still_exif_written = bool(is_still and (eff_write == WRITE_COPYRIGHT_INFO_ON_G106))

    pii_bytes_if_written = len(eff_photo.encode("utf-8")) + len(
        eff_copy.encode("utf-8")
    )
    if clean_room_bench_hygiene_required and eff_write == WRITE_COPYRIGHT_INFO_ON_G106:
        bench_pii_leaked = max(1, pii_bytes_if_written)
    else:
        bench_pii_leaked = 0

    return {
        "reset_action": norm_reset,
        "effective_post_reset_write_copyright_info": eff_write,
        "effective_post_reset_photographer": eff_photo,
        "effective_post_reset_copyright": eff_copy,
        "target_container": norm_container,
        "is_still_exif_container": is_still,
        "still_exif_tags_written": still_exif_written,
        "bench_pii_leaked_bytes": bench_pii_leaked,
    }


def verify_copyright_info_46char_still_exif_and_pii_hygiene_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: int = FX3_MODEL_ID,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE266,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE266,
    copyright_info_subitems: Sequence[str] = COPYRIGHT_INFO_EXACT_4_SUBITEMS_G106,
    reset_action: str = RESET_ACTION_NONE,
    clean_room_bench_hygiene_required: bool = True,
    pre_reset_write_copyright_info: str = WRITE_COPYRIGHT_INFO_BENCH_DEFAULT_G106,
    pre_reset_photographer: str = "",
    pre_reset_copyright: str = "",
    target_container: str = CONTAINER_STILL_JPEG_G106,
    disp_copyright_info_readonly: bool = True,
    claimed_disp_copyright_info_media_writes: int = 0,
    claimed_post_reset_write_copyright_info: Optional[str] = None,
    claimed_post_reset_photographer: Optional[str] = None,
    claimed_post_reset_copyright: Optional[str] = None,
    claimed_movie_or_raw_exif_mutation_bytes: int = 0,
    claimed_slot1_recovery_vault_mutation_bytes: int = 0,
    claimed_camset_copyright_export_bytes: int = 0,
    claimed_photographer_copyright_pii_leaked_bytes: int = 0,
) -> CopyrightInfo46CharStillExifGuardResult:
    """Verify Gate `G106`: `[Copyright Info]` (`Write Copyright Info` `Off` default,
    `Set Photographer` `<= 46` ASCII chars, `Set Copyright` `<= 46` ASCII chars,
    `Disp. Copyright Info`), enforcing Still-EXIF-only scope, zero movie/Slot-1
    mutation, `[Camera Settings Reset]` survival vs `[Initialize]` wipe,
    `[Save/Load Settings]` exclusion, and clean-room bench PII hygiene.
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    fw_tuple = _parse_fw_tuple(firmware_version)
    norm_reset = _norm_reset_action_phase266(reset_action)
    norm_write = _norm_on_off_phase266(pre_reset_write_copyright_info)
    norm_container = _norm_target_container_g106(target_container)
    subitems_tuple = (
        tuple(str(x).strip() for x in copyright_info_subitems)
        if isinstance(copyright_info_subitems, (list, tuple))
        else ()
    )

    if (
        body_model_name != FX3_MODEL_NAME
        or body_model_id != FX3_MODEL_ID
        or help_guide_code != FX3_HELP_GUIDE_CODE_PHASE266
        or fw_tuple is None
        or norm_reset is None
        or norm_write is None
        or norm_container is None
        or not isinstance(pre_reset_photographer, str)
        or not isinstance(pre_reset_copyright, str)
        or subitems_tuple != COPYRIGHT_INFO_EXACT_4_SUBITEMS_G106
    ):
        _add_code(codes, STATUS_BLOCKED_G106_TELEMETRY_INVALID)
        errors.append("Invalid ILME-FX3 Gate G106 [Copyright Info] telemetry.")

    photo_ok = _is_valid_46char_printable_ascii_g106(pre_reset_photographer)
    copy_ok = _is_valid_46char_printable_ascii_g106(pre_reset_copyright)
    if not photo_ok or not copy_ok:
        _add_code(codes, STATUS_BLOCKED_G106_COPYRIGHT_46CHAR_OR_ASCII_BOUND_VIOLATION)
        errors.append(
            f"[Set Photographer] and [Set Copyright] must be printable ASCII <= {COPYRIGHT_INFO_MAX_CHARS_G106} characters."
        )

    resolved = resolve_fx3_copyright_info_46char_still_exif_state(
        reset_action=norm_reset or RESET_ACTION_NONE,
        pre_reset_write_copyright_info=(
            norm_write or WRITE_COPYRIGHT_INFO_BENCH_DEFAULT_G106
        ),
        pre_reset_photographer=(
            pre_reset_photographer if isinstance(pre_reset_photographer, str) else ""
        ),
        pre_reset_copyright=(
            pre_reset_copyright if isinstance(pre_reset_copyright, str) else ""
        ),
        target_container=norm_container or CONTAINER_STILL_JPEG_G106,
        clean_room_bench_hygiene_required=bool(clean_room_bench_hygiene_required),
    )

    eff_write = str(resolved["effective_post_reset_write_copyright_info"])
    eff_photo = str(resolved["effective_post_reset_photographer"])
    eff_copy = str(resolved["effective_post_reset_copyright"])

    # Still-EXIF-only scope vs Movie/RAW stream & Slot-1 recovery vault isolation
    disp_writes = max(0, int(claimed_disp_copyright_info_media_writes))
    movie_mut_bytes = max(0, int(claimed_movie_or_raw_exif_mutation_bytes))
    slot1_mut_bytes = max(0, int(claimed_slot1_recovery_vault_mutation_bytes))
    if (
        (not bool(disp_copyright_info_readonly))
        or disp_writes > 0
        or movie_mut_bytes > 0
        or slot1_mut_bytes > 0
    ):
        _add_code(
            codes, STATUS_BLOCKED_G106_MOVIE_STREAM_OR_SLOT1_VAULT_MUTATION_VIOLATION
        )
        errors.append(
            "[Copyright Info] applies strictly to Still EXIF headers; Movie/RAW streams, [Disp. Copyright Info], and Slot-1 vault must incur 0 mutation bytes."
        )

    # Reset survival ([Camera Settings Reset]) vs [Initialize] wipe + CAMSET exclusion
    camset_export_bytes = max(0, int(claimed_camset_copyright_export_bytes))
    if (
        (
            claimed_post_reset_write_copyright_info is not None
            and _norm_on_off_phase266(claimed_post_reset_write_copyright_info)
            != eff_write
        )
        or (
            claimed_post_reset_photographer is not None
            and str(claimed_post_reset_photographer) != eff_photo
        )
        or (
            claimed_post_reset_copyright is not None
            and str(claimed_post_reset_copyright) != eff_copy
        )
        or camset_export_bytes > 0
    ):
        _add_code(
            codes, STATUS_BLOCKED_G106_RESET_SURVIVAL_OR_INITIALIZE_WIPE_VIOLATION
        )
        errors.append(
            "[Set Photographer]/[Set Copyright] must survive [Camera Settings Reset], clear on [Initialize], and remain excluded from [Save/Load Settings] CAMSET exports."
        )

    # Clean-room bench PII hygiene check
    pii_leaked = int(resolved["bench_pii_leaked_bytes"]) + max(
        0, int(claimed_photographer_copyright_pii_leaked_bytes)
    )
    if bool(clean_room_bench_hygiene_required) and (
        eff_write != WRITE_COPYRIGHT_INFO_OFF_G106
        or pii_leaked > 0
        or len(eff_photo) > 0
        or len(eff_copy) > 0
    ):
        if len(eff_photo) > 0 or len(eff_copy) > 0:
            pii_leaked = max(
                pii_leaked,
                len(eff_photo.encode("utf-8")) + len(eff_copy.encode("utf-8")),
            )
        _add_code(codes, STATUS_BLOCKED_G106_BENCH_PII_HYGIENE_LEAK_VIOLATION)
        errors.append(
            "Clean-room bench PII hygiene requires [Write Copyright Info] = [Off] and cleared operator Photographer/Copyright strings (photographer_copyright_pii_leaked_bytes == 0)."
        )

    valid = not codes
    status = STATUS_VERIFIED_G106 if valid else codes[0]

    return CopyrightInfo46CharStillExifGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=str(body_model_name),
        body_model_id_hex=f"0x{body_model_id:08X}"
        if isinstance(body_model_id, int)
        else "INVALID",
        help_guide_code=str(help_guide_code),
        firmware_version=str(firmware_version),
        copyright_info_menu_path=COPYRIGHT_INFO_MENU_PATH_G106,
        copyright_info_subitems=subitems_tuple,
        copyright_max_chars=COPYRIGHT_INFO_MAX_CHARS_G106,
        reset_action=norm_reset or str(reset_action),
        clean_room_bench_hygiene_required=bool(clean_room_bench_hygiene_required),
        pre_reset_write_copyright_info=norm_write or str(pre_reset_write_copyright_info),
        effective_post_reset_write_copyright_info=eff_write,
        pre_reset_photographer=(
            pre_reset_photographer if isinstance(pre_reset_photographer, str) else ""
        ),
        effective_post_reset_photographer=eff_photo,
        photographer_char_length=len(eff_photo),
        photographer_within_46char_ascii=photo_ok,
        pre_reset_copyright=(
            pre_reset_copyright if isinstance(pre_reset_copyright, str) else ""
        ),
        effective_post_reset_copyright=eff_copy,
        copyright_char_length=len(eff_copy),
        copyright_within_46char_ascii=copy_ok,
        strings_survive_camera_settings_reset=True,
        strings_wiped_by_initialize=True,
        disp_copyright_info_readonly=bool(disp_copyright_info_readonly)
        and disp_writes == 0,
        disp_copyright_info_media_writes=disp_writes,
        target_container=norm_container or str(target_container),
        is_still_exif_container=bool(resolved["is_still_exif_container"]),
        still_exif_tags_written=bool(resolved["still_exif_tags_written"]),
        exif_artist_tag_hex=EXIF_TAG_ARTIST_HEX_G106,
        exif_copyright_tag_hex=EXIF_TAG_COPYRIGHT_HEX_G106,
        movie_or_raw_exif_mutation_bytes=movie_mut_bytes,
        slot1_recovery_vault_mutation_bytes=slot1_mut_bytes,
        excluded_from_camset_saveload=(camset_export_bytes == 0),
        camset_copyright_export_bytes=camset_export_bytes,
        photographer_copyright_pii_leaked_bytes=pii_leaked,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g106_copyright_info_46char_still_exif_and_pii_hygiene_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    copyright_info_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase266DonorAuditResult] = None,
) -> Tuple[GateVerdict, G106CopyrightInfo46CharStillExifGuardResult]:
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase266_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_copyright_info_46char_still_exif_and_pii_hygiene_guard(
        **dict(copyright_info_kwargs or {})
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
        errors.append("Persistent eMMC write authorization requested in Gate G106.")
    if not audit.valid:
        _add_code(codes, audit.status)
    for c in guard.violation_codes:
        _add_code(codes, c)

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G106 if valid else codes[0]

    res = G106CopyrightInfo46CharStillExifGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        copyright_info_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, write_copyright={guard.effective_post_reset_write_copyright_info}"
        f"(max_chars={guard.copyright_max_chars},pii_leaked={guard.photographer_copyright_pii_leaked_bytes}), "
        f"container={guard.target_container}(still_exif={guard.still_exif_tags_written},"
        f"mv_mut={guard.movie_or_raw_exif_mutation_bytes},"
        f"slot1_mut={guard.slot1_recovery_vault_mutation_bytes})"
    )
    verdict = GateVerdict(
        gate_id=G106_GATE_ID,
        gate_code=G106_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 4. Unified `106`-Gate Master Safety Preflight (`G01..G106`)
# ---------------------------------------------------------------------------


def evaluate_106gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    dry_run_simulated_backup: Optional[bool] = None,
    simulate_bench_dry_run: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    request_persistent_emmc_writes: bool = False,
    release_audio_disp_kwargs: Optional[Mapping[str, Any]] = None,
    copyright_info_kwargs: Optional[Mapping[str, Any]] = None,
    master_104_override: Optional[Master104GateReport] = None,
    **m104_passthrough_kwargs: Any,
) -> Master106GateReport:
    """Evaluate all 106 Master Safety Gates (`G01..G106`) deterministically by
    delegating `G01..G104` directly to `evaluate_104gate_preflight()`.
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

    m104_report: Master104GateReport = (
        master_104_override
        if master_104_override is not None
        else evaluate_104gate_preflight(
            resolved_root,
            force_clean_room=clean_forced,
            dry_run_simulated=effective_dry_run,
            include_large_binaries=include_large_binaries,
            work_root=work_root,
            request_persistent_emmc_writes=request_persistent_emmc_writes,
            **m104_passthrough_kwargs,
        )
    )

    phase266_audit = audit_phase266_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
    )

    g105_verdict, g105_res = (
        evaluate_g105_release_wo_card_lens_and_v702_audio_disp_guard(
            work_root=work_root,
            repo_root=resolved_root,
            force_clean_room=clean_forced,
            release_audio_disp_kwargs=release_audio_disp_kwargs,
            request_persistent_emmc_writes=request_persistent_emmc_writes,
            donor_audit=phase266_audit,
        )
    )

    g106_verdict, g106_res = (
        evaluate_g106_copyright_info_46char_still_exif_and_pii_hygiene_guard(
            work_root=work_root,
            repo_root=resolved_root,
            force_clean_room=clean_forced,
            copyright_info_kwargs=copyright_info_kwargs,
            request_persistent_emmc_writes=request_persistent_emmc_writes,
            donor_audit=phase266_audit,
        )
    )

    gates_105_to_106 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g105_verdict, g106_verdict)
    ]
    all_gates = tuple(list(m104_report.gates) + gates_105_to_106)

    g01_to_g12_verified = int(m104_report.summary["g01_to_g12_verified"])
    g13_to_g104_verified = int(m104_report.summary["g13_to_g102_verified"]) + int(
        m104_report.summary["g103_to_g104_verified"]
    )
    g105_to_g106_verified = sum(1 for v in (g105_verdict, g106_verdict) if v.passed)
    total_verified = (
        g01_to_g12_verified + g13_to_g104_verified + g105_to_g106_verified
    )

    g105_to_g106_all_passed = g105_to_g106_verified == 2
    g13_to_g106_all_passed = (
        m104_report.g13_to_g104_all_passed and g105_to_g106_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m104_report.gates[:9])

    offline_103_verified = (
        g01_to_g09_ok
        and m104_report.offline_101_gates_verified
        and g105_to_g106_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_106_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g106_all_passed
        and (not request_persistent_emmc_writes)
    )

    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m104_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_103_verified
        and m104_report.h0_h1_trial_entry_allowed
        and g105_to_g106_all_passed
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
        list(m104_report.errors)
        + list(g105_verdict.errors)
        + list(g106_verdict.errors)
    )
    warnings: List[str] = (
        list(m104_report.warnings)
        + list(g105_verdict.warnings)
        + list(g106_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m104_report.g13_to_g104_all_passed:
        overall_status = m104_report.status
    elif not g105_verdict.passed:
        overall_status = g105_verdict.status
    elif not g106_verdict.passed:
        overall_status = g106_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_106_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_106_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_106_verified:
        overall_status = "VERIFIED_ALL_106_GATES"
    else:
        overall_status = "VERIFIED_103_OF_106_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m104_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g105_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g106_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 106,
        "verified_gates": total_verified,
        "technical_gates_passed": total_verified,
        "blocked_or_pending_gates": 106 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g104_verified": g13_to_g104_verified,
        "g105_to_g106_verified": g105_to_g106_verified,
        "g13_to_g106_all_passed": g13_to_g106_all_passed,
        "g105_to_g106_all_passed": g105_to_g106_all_passed,
        "offline_103_gates_verified": offline_103_verified,
        "all_106_gates_verified": all_106_verified,
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

    return Master106GateReport(
        schema=REALHW_RELEASE_WO_CARD_AUDIO_METER_COPYRIGHT_106GATE_SCHEMA,
        version=REALHW_RELEASE_WO_CARD_AUDIO_METER_COPYRIGHT_106GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        offline_103_gates_verified=offline_103_verified,
        all_106_gates_verified=all_106_verified,
        g13_to_g106_all_passed=g13_to_g106_all_passed,
        g105_to_g106_all_passed=g105_to_g106_all_passed,
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
        master_104_report=m104_report.to_dict(),
        g105_result=g105_res.to_dict(),
        g106_result=g106_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_106_master_safety_gates = evaluate_106gate_preflight
run_106_gate_preflight = evaluate_106gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_release_wo_card_audio_meter_copyright_and_106gate_guard",
        description=(
            "Phase 266 Safety Gates G105 (Release w/o Card & w/o Lens + Ver. 7.02 "
            "5-Item Audio Recording vs DISP Audio Meter Guard) + G106 (Copyright Info "
            "46-Char Still EXIF & Bench PII Hygiene Guard) + Unified 106-Gate Master "
            "Safety Preflight"
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

    report = evaluate_106gate_preflight(
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
            f"verified={report.summary['verified_gates']}/106 "
            f"g105_to_g106_all_passed={report.g105_to_g106_all_passed} "
            f"all_106_gates_verified={report.all_106_gates_verified} "
            f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach}\n"
        )
    ok = (
        report.all_106_gates_verified
        if args.dry_run_simulated
        else report.offline_103_gates_verified
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
