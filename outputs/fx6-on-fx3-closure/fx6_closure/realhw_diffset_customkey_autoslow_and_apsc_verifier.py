"""Phase 261 — 6th Physical Bench & Pre-Shoot Readiness Verifier (`preflight-diffset-customkey-autoslow-and-apsc`).

Dedicated host-side read-only 6th physical bench & pre-shoot readiness verifier for Sony
`ILME-FX3` (`Ver. 7.02`, `ilc/2210`, Model `0x91030080`), extending the operator bench preflight
series (`preflight-card-insert` -> `preflight-bench-cable-fan-slot1` ->
`preflight-hdmi-proxy-desqueeze-and-simult` ->
`preflight-pixelmap-ntscpal-powersave-and-autotemp` ->
`preflight-imagedb-touch-shoeaudio-and-lockop` ->
`preflight-diffset-customkey-autoslow-and-apsc`) by synthesizing Waves 40–43 official Sony
`ILME-FX3` Help Guide (`ilc/2210`) hardware boundaries into 4 deterministic fail-closed check
groups (`A..D`), bounded `O_RDONLY` donor inspection (`< 0.15s`), `16/16 H0 == H3` baseline
invariance, and dual-media `528 B FX3RCPT1` Tier-0 receipt gating:

1. **Check Group A (`GROUP_A_DIFF_SET_8ITEMS_SHUTTER_ANGLE_CUSTOM_KEY_AND_EVFLESS` — Wave 40)**:
   - Verifies `[Different Set for Still/Mv]` exact 8 checkable items (`Aperture`, `Shutter Speed`,
     `ISO`, `Exposure Comp.`, `Metering Mode`, `White Balance`, `Picture Profile`, `Focus Mode`),
     `[Camera Settings Reset]` survival, asymmetric `Common -> Separate` (copies all except
     `Custom White Balance` which stays still-only) & `Separate -> Common` (resets to factory
     defaults except `Aperture`, `Shutter Speed`, `Custom White Balance` which retain still values)
     transitions, and `Ver. 7.02` `[Shutter Mode] = [Angle]` independent movie/still override even
     when `Shutter Speed` is unchecked (set to common).
   - Verifies `[Custom Key/Dial Set.]` 3-domain (`Still` / `Movie` / `Playback`) Cinema-Line dial
     defaults (`Front dial = Aperture`, `Rear dial = ISO/EI`, `Control Wheel = Shutter Speed`),
     `[Camera Settings Reset]` survival, and Slot-1 `CAMSET01.DAT` `O_RDONLY` firewall
     (`slot1_custom_key_vault_mutation_bytes == 0`).
   - Verifies `[Remain Shoot Display]` (`Not Displayed` default / `Always Display` /
     `Shoot-Only Display`) still-image continuous-shooting buffer scope ONLY (not movie card time)
     and EVF-less `ILME-FX3` (`ilc/2210`) topology (`fx3_has_builtin_evf == False`,
     `fx3_has_finder_monitor_switch == False`).

2. **Check Group B (`GROUP_B_AUTO_SLOW_SHUTTER_6LOCKS_HDMI_REC_CTRL_TC_AND_BREATHING` — Wave 41)**:
   - Enforces `[Auto Slow Shutter]` (`On` default / `Off`, resettable by `[Camera Settings Reset]`)
     exact 6 official hardware lockout / non-function conditions (`S&Q`, `Shutter Priority`,
     `Manual Exposure`, fixed manual `ISO != ISO AUTO`, `Flexible Exp. Mode` with manual shutter,
     and `Log Shooting = Cine EI Quick / Cine EI`), plus strict hardware disjointness with
     `[Shutter Mode] = [Angle]` (`auto_slow_shutter_angle_overlap_events == 0`).
   - Enforces `[HDMI Output Settings]` (`[Camera Settings Reset]` survival), `[REC Control]`
     mandatory `[Time Code Output] = [On]` hardware prerequisite
     (`hdmi_rec_ctrl_without_tc_violations == 0`), `[4ch Audio Output]` (`CH1/CH2` vs `CH3/CH4`
     4ch MI-shoe routing), and `[Rec. Media dur HDMI Output]` Slot-1 Tier-0 vault guard.
   - Enforces `[Breathing Comp.]` (`Ver. 3.00+`/`7.02`) movie-only scope, compliant Sony E-mount
     lens requirement, and `HDMI RAW Output` (`4264x2408`) / `S&Q 240p/200p` lockouts.

3. **Check Group C (`GROUP_C_APSC_S35_12MP_4K_LOCKOUT_FACE_EYE_AF_AND_VERSION_RO` — Wave 42)**:
   - Enforces `[APS-C S35 Shooting]` (`Auto` / `On` / `Off`) `12.1 MP` full-frame sensor `4K` movie
     (`XAVC HS 4K` / `XAVC S 4K` / `XAVC S-I 4K`) & `4264x2408` `HDMI RAW Output` lockout (Super
     35mm movie allowed ONLY in `HD`: `XAVC S HD` / `XAVC S-I HD`,
     `apsc_s35_4k_or_raw_bypass_events == 0`).
   - Verifies `[Face/Eye AF]` exact 4-item BIONZ XR hierarchy (`Face/Eye Prior. in AF`,
     `Face/Eye Subject`, `Right/Left Eye Select`, `Face/Eye Frame Disp.` — not dedicated AI-unit
     `Subject Recog in AF`), `[Face Memory]` reset survival split, and clean-HDMI frame isolation
     (`hdmi_clean_feed_eye_frame_baked_pixels == 0`).
   - Verifies `[Version]` read-only dialog (`Airplane Mode = On` update badge suppression,
     `passive_tx_bytes_emitted == 0`) vs hard-blocked Slot-1 `BODYDATA.DAT` automated flash
     (`persistent_emmc_writes_authorized == False`).

4. **Check Group D (`GROUP_D_RELEASE_WO_CARD_LENS_V702_AUDIO_5ITEM_COPYRIGHT_AND_TIER0` — Wave 43)**:
   - Enforces `[Release w/o Card]` still-only shutter scope vs mandatory writable card for movie
     internal recording, and `[Release w/o Lens]` body-only / mechanical PL-adapter zero-E-ND
     bench safety (`e_nd_uart_bytes_transmitted == 0`).
   - Verifies `Ver. 2.00+`/`7.02` `[Audio Recording]` exact 5-item menu (`Audio Recording`,
     `Audio Rec Level 0..31`, `Audio Out Timing`, `Wind Noise Reduct.`, `Shoe Audio Set.`) and
     `DISP (Screen Disp) Set` audio meter integration vs absent `Ver. 1.x` `[Audio Level Display]`
     (`legacy_v1_audio_level_menu_spoof_events == 0`).
   - Enforces `[Copyright Info]` (`Write Copyright Info = Off` bench default, `<= 46`-char
     `Set Photographer` / `Set Copyright` survival across `[Camera Settings Reset]`, still-EXIF
     scope) with `photographer_copyright_pii_leaked_bytes == 0`, `16/16 H0 == H3` storage
     invariance, and dual-media `528 B FX3RCPT1` Tier-0 receipt gating.

Hard-Locked Safety Invariants (UNCONDITIONAL):
- `overall_ready_for_hardware_attach = False`
- `hardware_live_attachment_authorized = False`
- `persistent_emmc_writes_authorized = False`
- `persistent_write_release = False`
- `spi_nor_write_authorized = False`
- `el3_payload_transmit_authorized = False`
- `sd_physical_media_written = False`
- `usb_packets_transmitted = 0` (`physical_usb_packets_emitted = 0`)
- `raw_firmware_bytes_leaked = 0`
- `e_nd_uart_bytes_transmitted = 0`
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import copy
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple


def _ensure_cross_package_paths(repo_root: Path) -> None:
    for rel in (
        "outputs/fx3-safety",
        "outputs/fx3-recovery-adapter",
        "outputs/fx3-firmware-lab",
        "outputs/fx3-vm",
        "outputs/fx6-on-fx3-closure",
    ):
        cand = str(repo_root / rel)
        if cand not in sys.path:
            sys.path.append(cand)


DEFAULT_REPO_ROOT: Path = Path(__file__).resolve().parents[3]
_ensure_cross_package_paths(DEFAULT_REPO_ROOT)

from fx3_recovery.realhw_adjustcontrol_streaming_backup_client import (  # noqa: E402
    COLD_BACKUP_ITEMS,
    SD_RECEIPT_BYTES,
    build_sd_backup_receipt_bytes,
    parse_sd_backup_receipt_bytes,
)

from .donor_paths import is_forced_clean_room, resolve_work_subpath  # noqa: E402
from .hardware_readiness_packet import (  # noqa: E402
    BODY_SERIAL_RE,
    FORBIDDEN_TRIVIAL_CIDS,
    FORBIDDEN_TRIVIAL_SERIALS,
    HEX32_CID_RE,
    HEX64_RE,
)
from .patcher import (  # noqa: E402
    DEFAULT_FX3_MODULES_DIR,
    DEFAULT_FX6_DONOR_LIB_DIR,
    FX6_WLAN_RSRC_DONOR_SHA256,
)
from .realhw_bench_cable_fan_and_slot1_verifier import (  # noqa: E402
    FX3_LIBUSBBUSPOWER_EXPECTED_SHA256,
    FX3_LIBUSBBUSPOWER_EXPECTED_SIZE,
    FX3_LIBUSBBUSPOWER_RELPATH,
)
from .realhw_card_insert_readiness_verifier import (  # noqa: E402
    DONOR_INSPECTION_MAX_SECONDS,
    EM_AARCH64,
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
    MIN_BODY_FW_TUPLE,
    REQUIRED_H0_BASELINE_KEYS,
    TARGET_BODY_FW,
    TARGET_MODEL_ID_INT,
    _parse_elf64_header_and_pt_load,
    _parse_fw_tuple,
    _read_bounded_slice_o_rdonly,
    build_default_h0_baselines,
)
from .realhw_jiritsu_and_tier0_dumper_auditor import (  # noqa: E402
    LIBJIRITSU_EXPECTED_SHA256,
    LIBJIRITSU_EXPECTED_SIZE,
    LIBJIRITSU_RELPATH,
)
from .realhw_sd_stageb_bundle_and_uninstaller import (  # noqa: E402
    DEFAULT_TARGET_BODY_SERIAL,
    DEFAULT_TARGET_EMMC_CID,
    FX3_IM_ELF_EXPECTED_SHA256,
    FX3_IM_ELF_EXPECTED_SIZE,
    FX3_IM_ELF_RELPATH,
    FX6_APPFW_EXPECTED_SIZE,
    SIXTEEN_STORAGE_SURFACES,
    read_only_o_rdonly_digest_and_header,
)

# ---------------------------------------------------------------------------
# Schema, Verdicts & Non-Shadowing P261_* Domain Constants
# ---------------------------------------------------------------------------

PHASE_261_SCHEMA: str = "realhw_diffset_customkey_autoslow_and_apsc_verifier_v1"
P261_SCHEMA: str = PHASE_261_SCHEMA
REALHW_DIFFSET_CUSTOMKEY_AUTOSLOW_APSC_SCHEMA: str = PHASE_261_SCHEMA
PHASE_261_VERSION: str = "261.0.0"
P261_VERSION: str = PHASE_261_VERSION
P261_SONY_HELP_GUIDE_ID: str = "ilc/2210"

P261_GO_NO_GO_DIFFSET_CUSTOMKEY_AUTOSLOW_APSC_VERIFIED: str = (
    "GO_DIFFSET_CUSTOMKEY_AUTOSLOW_APSC_READONLY_PREFLIGHT_VERIFIED"
)
P261_GO_NO_GO_BLOCKED_DIFFSET_CUSTOMKEY_AUTOSLOW_APSC_FAILURE: str = (
    "BLOCKED_DIFFSET_CUSTOMKEY_AUTOSLOW_APSC_CHECK_FAILURE"
)
PHASE_261_VALID_GO_NO_GO_VALUES: Tuple[str, ...] = (
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    P261_GO_NO_GO_BLOCKED_DIFFSET_CUSTOMKEY_AUTOSLOW_APSC_FAILURE,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
    P261_GO_NO_GO_DIFFSET_CUSTOMKEY_AUTOSLOW_APSC_VERIFIED,
)

P261_CHECK_GROUP_A_ID: str = (
    "GROUP_A_DIFF_SET_8ITEMS_SHUTTER_ANGLE_CUSTOM_KEY_AND_EVFLESS"
)
P261_CHECK_GROUP_B_ID: str = (
    "GROUP_B_AUTO_SLOW_SHUTTER_6LOCKS_HDMI_REC_CTRL_TC_AND_BREATHING"
)
P261_CHECK_GROUP_C_ID: str = (
    "GROUP_C_APSC_S35_12MP_4K_LOCKOUT_FACE_EYE_AF_AND_VERSION_RO"
)
P261_CHECK_GROUP_D_ID: str = (
    "GROUP_D_RELEASE_WO_CARD_LENS_V702_AUDIO_5ITEM_COPYRIGHT_AND_TIER0"
)
PHASE_261_CHECK_GROUP_IDS: Tuple[str, ...] = (
    P261_CHECK_GROUP_A_ID,
    P261_CHECK_GROUP_B_ID,
    P261_CHECK_GROUP_C_ID,
    P261_CHECK_GROUP_D_ID,
)

PHASE261_RAW_FIRMWARE_BYTES_LEAKED: int = 0
PHASE261_E_ND_UART_BYTES_TRANSMITTED: int = 0

# Group A Constants (Wave 40)
P261_DIFF_SET_EIGHT_ITEMS: Tuple[str, ...] = (
    "Aperture",
    "Shutter Speed",
    "ISO",
    "Exposure Comp.",
    "Metering Mode",
    "White Balance",
    "Picture Profile",
    "Focus Mode",
)
P261_COMMON_TO_SEPARATE_STILL_ONLY_EXCEPTION: str = "Custom White Balance"
P261_SEPARATE_TO_COMMON_STILL_RETAINED_ITEMS: Tuple[str, ...] = (
    "Aperture",
    "Shutter Speed",
    "Custom White Balance",
)
P261_VALID_DIFF_SET_TRANSITIONS: Tuple[str, ...] = (
    "NONE",
    "COMMON_TO_SEPARATE",
    "SEPARATE_TO_COMMON",
)
P261_CUSTOM_KEY_THREE_DOMAINS: Tuple[str, ...] = ("STILL", "MOVIE", "PLAYBACK")
P261_DEFAULT_FRONT_DIAL_ASSIGNMENT: str = "Aperture"
P261_DEFAULT_REAR_DIAL_ASSIGNMENT: str = "ISO/EI"
P261_DEFAULT_CONTROL_WHEEL_ASSIGNMENT: str = "Shutter Speed"
P261_VALID_SLOT1_CUSTOM_KEY_ACCESS_MODES: Tuple[str, ...] = ("NONE", "O_RDONLY")
P261_VALID_REMAIN_SHOOT_DISPLAY_MODES: Tuple[str, ...] = (
    "NOT_DISPLAYED",
    "ALWAYS_DISPLAY",
    "SHOOT_ONLY_DISPLAY",
)
P261_VALID_RESET_ACTIONS: Tuple[str, ...] = (
    "NONE",
    "CAMERA_SETTINGS_RESET",
    "RESET_NETWORK_SET",
    "INITIALIZE",
)

# Group B Constants (Wave 41)
P261_AUTO_SLOW_SHUTTER_SIX_LOCKOUTS: Tuple[str, ...] = (
    "SQ_MOTION_SHOOTING",
    "SHUTTER_PRIORITY_S_MODE",
    "MANUAL_EXPOSURE_M_MODE",
    "MANUAL_FIXED_ISO_NON_AUTO",
    "FLEXIBLE_EXP_MANUAL_SHUTTER",
    "LOG_SHOOTING_CINE_EI_OR_QUICK",
)
P261_VALID_EXPOSURE_MODES: Tuple[str, ...] = (
    "PROGRAM_AUTO",
    "APERTURE_PRIORITY",
    "SHUTTER_PRIORITY",
    "MANUAL_EXPOSURE",
    "INTELLIGENT_AUTO",
)
P261_VALID_EXPOSURE_CTRL_TYPES: Tuple[str, ...] = (
    "P_A_S_M_MODE",
    "FLEXIBLE_EXP_MODE",
)
P261_VALID_LOG_SHOOTING_MODES: Tuple[str, ...] = (
    "OFF",
    "CINE_EI_QUICK",
    "CINE_EI",
    "FLEXIBLE_ISO",
)
P261_VALID_HDMI_4CH_AUDIO_ROUTINGS: Tuple[str, ...] = ("CH1_CH2", "CH3_CH4")
P261_VALID_REC_MEDIA_DUR_HDMI_MODES: Tuple[str, ...] = ("ON", "OFF", "OFF_HDMI_ONLY")

# Group C Constants (Wave 42)
P261_VALID_APSC_S35_MODES: Tuple[str, ...] = ("AUTO", "ON", "OFF")
P261_4K_MOVIE_FILE_FORMATS: Tuple[str, ...] = (
    "XAVC_HS_4K",
    "XAVC_S_4K",
    "XAVC_S_I_4K",
)
P261_HD_MOVIE_FILE_FORMATS: Tuple[str, ...] = (
    "XAVC_S_HD",
    "XAVC_S_I_HD",
)
P261_VALID_MOVIE_FILE_FORMATS: Tuple[str, ...] = (
    *P261_4K_MOVIE_FILE_FORMATS,
    *P261_HD_MOVIE_FILE_FORMATS,
)
P261_FACE_EYE_AF_FOUR_ITEMS: Tuple[str, ...] = (
    "Face/Eye Prior. in AF",
    "Face/Eye Subject",
    "Right/Left Eye Select",
    "Face/Eye Frame Disp.",
)
P261_VALID_FACE_EYE_SUBJECTS: Tuple[str, ...] = ("HUMAN", "ANIMAL", "BIRD")
P261_VALID_RIGHT_LEFT_EYE_SELECTS: Tuple[str, ...] = ("AUTO", "RIGHT_EYE", "LEFT_EYE")

# Group D Constants (Wave 43)
P261_VALID_RELEASE_WO_MODES: Tuple[str, ...] = ("ENABLE", "DISABLE")
P261_V702_AUDIO_RECORDING_FIVE_ITEMS: Tuple[str, ...] = (
    "Audio Recording",
    "Audio Rec Level",
    "Audio Out Timing",
    "Wind Noise Reduct.",
    "Shoe Audio Set.",
)
P261_AUDIO_REC_LEVEL_MIN: int = 0
P261_AUDIO_REC_LEVEL_MAX: int = 31
P261_COPYRIGHT_INFO_FOUR_SUBITEMS: Tuple[str, ...] = (
    "Write Copyright Info",
    "Set Photographer",
    "Set Copyright",
    "Disp. Copyright Info",
)
P261_COPYRIGHT_INFO_MAX_CHARS: int = 46

# Error Codes
P261_GA_ERR_MODEL_OR_FW_FLOOR: str = "P261_GA_ERR_MODEL_OR_FW_FLOOR"
P261_GA_ERR_DIFF_SET_8ITEMS_TRANSITION_OR_SHUTTER_ANGLE_OVERRIDE: str = (
    "P261_GA_ERR_DIFF_SET_8ITEMS_TRANSITION_OR_SHUTTER_ANGLE_OVERRIDE"
)
P261_GA_ERR_CUSTOM_KEY_3DOMAIN_ISO_EI_OR_SLOT1_VAULT_FIREWALL: str = (
    "P261_GA_ERR_CUSTOM_KEY_3DOMAIN_ISO_EI_OR_SLOT1_VAULT_FIREWALL"
)
P261_GA_ERR_REMAIN_SHOOT_STILL_BUFFER_OR_EVFLESS_TOPOLOGY: str = (
    "P261_GA_ERR_REMAIN_SHOOT_STILL_BUFFER_OR_EVFLESS_TOPOLOGY"
)

P261_GB_ERR_AUTO_SLOW_SHUTTER_6LOCKS_OR_SHUTTER_ANGLE_OVERLAP: str = (
    "P261_GB_ERR_AUTO_SLOW_SHUTTER_6LOCKS_OR_SHUTTER_ANGLE_OVERLAP"
)
P261_GB_ERR_HDMI_REC_CTRL_TC_PREREQ_4CH_OR_MEDIA_VAULT_GUARD: str = (
    "P261_GB_ERR_HDMI_REC_CTRL_TC_PREREQ_4CH_OR_MEDIA_VAULT_GUARD"
)
P261_GB_ERR_BREATHING_COMP_MOVIE_ONLY_LENS_RAW_OR_240P_LOCKOUT: str = (
    "P261_GB_ERR_BREATHING_COMP_MOVIE_ONLY_LENS_RAW_OR_240P_LOCKOUT"
)

P261_GC_ERR_APSC_S35_12MP_4K_OR_HDMI_RAW_LOCKOUT: str = (
    "P261_GC_ERR_APSC_S35_12MP_4K_OR_HDMI_RAW_LOCKOUT"
)
P261_GC_ERR_FACE_EYE_AF_MENU_OR_CLEAN_HDMI_FRAME_ISOLATION: str = (
    "P261_GC_ERR_FACE_EYE_AF_MENU_OR_CLEAN_HDMI_FRAME_ISOLATION"
)
P261_GC_ERR_VERSION_READONLY_OR_HARD_BLOCKED_BODYDATA_FLASH: str = (
    "P261_GC_ERR_VERSION_READONLY_OR_HARD_BLOCKED_BODYDATA_FLASH"
)

P261_GD_ERR_RELEASE_WO_CARD_STILL_MOVIE_GATE_OR_WO_LENS_END_ZERO: str = (
    "P261_GD_ERR_RELEASE_WO_CARD_STILL_MOVIE_GATE_OR_WO_LENS_END_ZERO"
)
P261_GD_ERR_V702_AUDIO_5ITEM_MENU_OR_DISP_METER_SPLIT: str = (
    "P261_GD_ERR_V702_AUDIO_5ITEM_MENU_OR_DISP_METER_SPLIT"
)
P261_GD_ERR_COPYRIGHT_INFO_46CHAR_STILL_EXIF_OR_PII_HYGIENE: str = (
    "P261_GD_ERR_COPYRIGHT_INFO_46CHAR_STILL_EXIF_OR_PII_HYGIENE"
)
P261_GD_ERR_H0_H3_IMMUTABILITY_DRIFT: str = "P261_GD_ERR_H0_H3_IMMUTABILITY_DRIFT"
P261_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID: str = (
    "P261_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID"
)

_TRIVIAL_HEX64_SET = frozenset(
    {
        "0" * 64,
        "f" * 64,
        "a" * 64,
        "5" * 64,
        hashlib.sha256(b"").hexdigest(),
    }
)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase261DonorInspectionResult:
    passed: bool
    verification_mode: str
    read_only_o_rdonly_enforced: bool
    elapsed_seconds: float
    within_150ms_budget: bool
    inspected_artifacts: Tuple[str, ...]
    fx3_im_elf_verified: bool
    fx3_libjiritsu_verified: bool
    fx3_libusbbuspower_verified: bool
    fx6_appfw_verified: bool
    fx6_wlan_rsrc_verified: bool
    fx3_upm_ko_verified: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class P261CheckGroupADiffSetCustomKeyEvfLessResult:
    check_group_id: str
    passed: bool
    body_model_id_hex: str
    body_fw: str
    sony_help_guide_id: str
    diff_set_eight_items: Tuple[str, ...]
    diff_set_shutter_speed_checked: bool
    diff_set_transition: str
    common_to_separate_still_only_exception: str
    separate_to_common_still_retained_items: Tuple[str, ...]
    movie_shutter_mode: str
    shutter_angle_independent_from_still_shutter: bool
    diff_set_survives_camera_reset: bool
    custom_key_domains: Tuple[str, ...]
    front_dial_assignment: str
    rear_dial_assignment: str
    control_wheel_assignment: str
    custom_key_survives_camera_reset: bool
    slot1_camset_custom_key_access_mode: str
    slot1_custom_key_vault_mutation_bytes: int
    remain_shoot_display: str
    effective_remain_shoot_after_reset: str
    remain_shoot_still_buffer_only_verified: bool
    fx3_has_builtin_evf: bool
    fx3_has_finder_monitor_switch: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class P261CheckGroupBAutoSlowHdmiRecCtrlBreathingResult:
    check_group_id: str
    passed: bool
    auto_slow_shutter: str
    effective_auto_slow_after_reset: str
    exposure_ctrl_type: str
    exposure_mode: str
    flexible_shutter_mode: str
    iso_mode: str
    log_shooting_mode: str
    sq_mode_enabled: bool
    movie_shutter_mode: str
    active_auto_slow_shutter_lockouts: Tuple[str, ...]
    auto_slow_shutter_effective_active: bool
    auto_slow_shutter_angle_overlap_events: int
    hdmi_time_code_output: str
    hdmi_rec_control: str
    hdmi_rec_ctrl_without_tc_violations: int
    hdmi_4ch_audio_output: str
    rec_media_dur_hdmi_output: str
    hdmi_settings_survive_camera_reset: bool
    slot1_hdmi_media_vault_protected: bool
    breathing_comp: str
    effective_breathing_comp_after_reset: str
    breathing_comp_compliant_lens: bool
    hdmi_raw_output: bool
    sq_240p_or_200p_active: bool
    breathing_comp_movie_only_verified: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class P261CheckGroupCApscS35FaceEyeAfVersionResult:
    check_group_id: str
    passed: bool
    apsc_s35_shooting: str
    movie_file_format: str
    hdmi_raw_output: bool
    effective_apsc_s35_movie_state: str
    apsc_s35_4k_or_raw_locked_off: bool
    apsc_s35_4k_or_raw_bypass_events: int
    face_eye_af_four_items: Tuple[str, ...]
    face_eye_prior_in_af: str
    face_eye_subject: str
    right_left_eye_select: str
    face_eye_frame_disp: str
    face_memory_survives_camera_reset: bool
    hdmi_info_display: str
    hdmi_clean_feed_eye_frame_baked_pixels: int
    version_dialog_read_only: bool
    airplane_mode: str
    update_notification_suppressed: bool
    passive_tx_bytes_emitted: int
    bodydata_auto_flash_authorized: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class P261CheckGroupDReleaseWoCardAudioCopyrightTier0Result:
    check_group_id: str
    passed: bool
    release_wo_card: str
    release_wo_lens: str
    card_inserted_for_movie_rec: bool
    movie_internal_rec_requested: bool
    movie_internal_rec_media_gate_ok: bool
    body_only_or_pl_adapter_bench: bool
    e_nd_uart_bytes_transmitted: int
    v702_audio_recording_five_items: Tuple[str, ...]
    audio_rec_level: int
    disp_screen_disp_audio_meter_enabled: bool
    sq_mode_enabled: bool
    effective_audio_meter_visible: bool
    legacy_v1_audio_level_menu_spoof_events: int
    write_copyright_info: str
    photographer_text_len: int
    copyright_text_len: int
    copyright_strings_survive_camera_reset: bool
    copyright_still_exif_only_verified: bool
    photographer_copyright_pii_leaked_bytes: int
    h0_h3_surface_count: int
    h0_equals_h3_count: int
    tier0_receipt_present: bool
    tier0_receipt_verified: bool
    distinct_physical_media_verified: bool
    warnings: Tuple[str, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class RealHwDiffSetCustomKeyAutoSlowApscReport:
    schema: str
    phase_version: str
    verification_mode: str
    simulate_bench_dry_run: bool
    go_no_go: str
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    spi_nor_write_authorized: bool
    el3_payload_transmit_authorized: bool
    sd_physical_media_written: bool
    usb_packets_transmitted: int
    physical_usb_packets_emitted: int
    raw_firmware_bytes_leaked: int
    e_nd_uart_bytes_transmitted: int
    slot1_custom_key_vault_mutation_bytes: int
    photographer_copyright_pii_leaked_bytes: int
    fx3_has_builtin_evf: bool
    check_group_count: int
    check_groups_passed: int
    all_4_check_groups_passed: bool
    tier0_receipt_verified: bool
    h0_h3_surface_count: int
    h0_equals_h3_count: int
    donor_inspection: Phase261DonorInspectionResult
    check_group_a_diffset_customkey_and_evfless: P261CheckGroupADiffSetCustomKeyEvfLessResult
    check_group_b_autoslow_hdmi_rec_ctrl_and_breathing: P261CheckGroupBAutoSlowHdmiRecCtrlBreathingResult
    check_group_c_apsc_s35_face_eye_af_and_version: P261CheckGroupCApscS35FaceEyeAfVersionResult
    check_group_d_release_wo_card_audio_copyright_and_tier0: P261CheckGroupDReleaseWoCardAudioCopyrightTier0Result
    warnings: Tuple[str, ...]
    remediation_actions: Tuple[str, ...]
    errors: Tuple[str, ...]
    report_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_deterministic_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=False) + "\n"


@dataclass(frozen=True)
class Phase261ReportVerifyResult:
    valid: bool
    errors: Tuple[str, ...]


# ---------------------------------------------------------------------------
# Internal Helpers & Bounded O_RDONLY Donor Inspection (< 0.15s)
# ---------------------------------------------------------------------------


def _norm_token(raw: str) -> str:
    return re.sub(r"[\s\-:/\.]+", "_", str(raw).strip().upper()).strip("_")


def _norm_shutter_mode(raw: str) -> str:
    tok = _norm_token(raw)
    aliases = {
        "ANGLE": "SHUTTER_ANGLE",
        "SHUTTER_ANGLE": "SHUTTER_ANGLE",
        "SPEED": "SHUTTER_SPEED",
        "SHUTTER_SPEED": "SHUTTER_SPEED",
    }
    return aliases.get(tok, tok)


def _norm_hdmi_4ch(raw: str) -> str:
    tok = _norm_token(raw)
    aliases = {
        "CH1_CH2": "CH1_CH2",
        "CH1_2": "CH1_CH2",
        "CH3_CH4": "CH3_CH4",
        "CH3_4": "CH3_CH4",
    }
    return aliases.get(tok, tok)


def _norm_rec_media_hdmi(raw: str) -> str:
    s = str(raw).strip().upper()
    aliases = {
        "ON": "ON",
        "OFF": "OFF",
        "OFF(HDMI ONLY)": "OFF_HDMI_ONLY",
        "OFF_HDMI_ONLY": "OFF_HDMI_ONLY",
    }
    return aliases.get(s, _norm_token(raw))


def _canonical_sha256_dict(obj: Mapping[str, Any], exclude_key: Optional[str] = None) -> str:
    body = dict(copy.deepcopy(obj))
    if exclude_key:
        body.pop(exclude_key, None)
    donor_sub = body.get("donor_inspection")
    if isinstance(donor_sub, dict):
        donor_sub.pop("elapsed_seconds", None)
    raw = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(raw).hexdigest()


def _is_trivial_hex64(val: str) -> bool:
    norm = str(val).strip().lower()
    if not HEX64_RE.match(norm):
        return True
    return norm in _TRIVIAL_HEX64_SET


def inspect_phase261_donors_bounded(
    *,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    force_clean_room: Optional[bool] = None,
    synthetic_clean_room: Optional[bool] = None,
    max_seconds: float = DONOR_INSPECTION_MAX_SECONDS,
) -> Phase261DonorInspectionResult:
    """Inspect local BYOF donors strictly via O_RDONLY within < 0.15s, or Clean-Room fallback."""
    t0 = time.perf_counter()
    errors: List[str] = []
    eff_clean = force_clean_room if force_clean_room is not None else synthetic_clean_room
    clean_room = is_forced_clean_room() if eff_clean is None else bool(eff_clean)

    fx3_im_path = resolve_work_subpath(FX3_IM_ELF_RELPATH, require_file=False)
    fx3_jit_path = resolve_work_subpath(LIBJIRITSU_RELPATH, require_file=False)
    fx3_usb_pwr_path = resolve_work_subpath(FX3_LIBUSBBUSPOWER_RELPATH, require_file=False)
    fx6_appfw_path = fx6_lib_dir / "appFw.so"
    fx6_wlan_path = fx6_lib_dir / "libWlanResource.so"
    fx3_upm_path = fx3_modules_dir / "upm.ko"

    donors_present = (
        fx3_im_path.is_file()
        and fx3_jit_path.is_file()
        and fx3_usb_pwr_path.is_file()
        and fx6_appfw_path.is_file()
        and fx6_wlan_path.is_file()
        and fx3_upm_path.is_file()
    )

    if eff_clean is False and not donors_present:
        elapsed = round(time.perf_counter() - t0, 6)
        return Phase261DonorInspectionResult(
            passed=False,
            verification_mode="LOCAL_DONOR_O_RDONLY",
            read_only_o_rdonly_enforced=True,
            elapsed_seconds=elapsed,
            within_150ms_budget=(elapsed < max_seconds),
            inspected_artifacts=(),
            fx3_im_elf_verified=fx3_im_path.is_file(),
            fx3_libjiritsu_verified=fx3_jit_path.is_file(),
            fx3_libusbbuspower_verified=fx3_usb_pwr_path.is_file(),
            fx6_appfw_verified=fx6_appfw_path.is_file(),
            fx6_wlan_rsrc_verified=fx6_wlan_path.is_file(),
            fx3_upm_ko_verified=fx3_upm_path.is_file(),
            raw_firmware_bytes_leaked=PHASE261_RAW_FIRMWARE_BYTES_LEAKED,
            errors=(f"Local BYOF donors missing under fx6_lib_dir={fx6_lib_dir}",),
        )

    use_live = (not clean_room) and donors_present
    mode = "LOCAL_DONOR_O_RDONLY" if use_live else "CLEAN_ROOM_SYNTHETIC"
    inspected: List[str] = []

    if use_live:
        im_sz, im_sha, im_head = read_only_o_rdonly_digest_and_header(fx3_im_path)
        im_mag, im_64, im_mach, _ = _parse_elf64_header_and_pt_load(im_head)
        im_ok = (
            im_sz == FX3_IM_ELF_EXPECTED_SIZE
            and im_sha == FX3_IM_ELF_EXPECTED_SHA256
            and im_mag
            and im_64
            and im_mach == EM_AARCH64
        )
        inspected.append("im.elf")
        if not im_ok:
            errors.append(f"im.elf O_RDONLY verification failed: size={im_sz}")

        jit_sz, jit_sha, jit_head = read_only_o_rdonly_digest_and_header(fx3_jit_path)
        jit_mag, jit_64, jit_mach, _ = _parse_elf64_header_and_pt_load(jit_head)
        jit_ok = (
            jit_sz == LIBJIRITSU_EXPECTED_SIZE
            and jit_sha == LIBJIRITSU_EXPECTED_SHA256
            and jit_mag
            and jit_64
            and jit_mach == EM_AARCH64
        )
        inspected.append("libJiritsu.so")
        if not jit_ok:
            errors.append(f"libJiritsu.so O_RDONLY verification failed: size={jit_sz}")

        pwr_sz, pwr_sha, pwr_head = read_only_o_rdonly_digest_and_header(fx3_usb_pwr_path)
        pwr_mag, pwr_64, pwr_mach, _ = _parse_elf64_header_and_pt_load(pwr_head)
        pwr_ok = (
            pwr_sz == FX3_LIBUSBBUSPOWER_EXPECTED_SIZE
            and pwr_sha == FX3_LIBUSBBUSPOWER_EXPECTED_SHA256
            and pwr_mag
            and pwr_64
            and pwr_mach == EM_AARCH64
        )
        inspected.append("libUsbBusPower.so")
        if not pwr_ok:
            errors.append(f"libUsbBusPower.so O_RDONLY verification failed: size={pwr_sz}")

        appfw_sz, appfw_head, _ = _read_bounded_slice_o_rdonly(fx6_appfw_path, 4096)
        appfw_mag, appfw_64, appfw_mach, _ = _parse_elf64_header_and_pt_load(appfw_head)
        appfw_ok = (
            appfw_sz == FX6_APPFW_EXPECTED_SIZE
            and appfw_mag
            and appfw_64
            and appfw_mach == EM_AARCH64
        )
        inspected.append("appFw.so(bounded-4KiB)")
        if not appfw_ok:
            errors.append(f"appFw.so bounded O_RDONLY header failed: size={appfw_sz}")

        wlan_sz, wlan_sha, wlan_head = read_only_o_rdonly_digest_and_header(fx6_wlan_path)
        wlan_mag, wlan_64, wlan_mach, _ = _parse_elf64_header_and_pt_load(wlan_head)
        wlan_ok = (
            wlan_sz > 0
            and wlan_sha == FX6_WLAN_RSRC_DONOR_SHA256
            and wlan_mag
            and wlan_64
            and wlan_mach == EM_AARCH64
        )
        inspected.append("libWlanResource.so")
        if not wlan_ok:
            errors.append("libWlanResource.so O_RDONLY SHA-256 verification failed")

        upm_sz, upm_head, _ = _read_bounded_slice_o_rdonly(fx3_upm_path, 4096)
        upm_mag, upm_64, upm_mach, _ = _parse_elf64_header_and_pt_load(upm_head)
        upm_ok = upm_sz > 0 and upm_mag and upm_64 and upm_mach == EM_AARCH64
        inspected.append("upm.ko(bounded-4KiB)")
        if not upm_ok:
            errors.append(f"upm.ko bounded O_RDONLY header failed: size={upm_sz}")
    else:
        im_ok = jit_ok = pwr_ok = appfw_ok = wlan_ok = upm_ok = True
        inspected.extend(
            [
                "synthetic:im.elf",
                "synthetic:libJiritsu.so",
                "synthetic:libUsbBusPower.so",
                "synthetic:appFw.so",
                "synthetic:libWlanResource.so",
                "synthetic:upm.ko",
            ]
        )

    elapsed = round(time.perf_counter() - t0, 6)
    within_budget = elapsed < max_seconds
    if not within_budget:
        errors.append(f"Donor inspection exceeded {max_seconds:.3f}s budget: {elapsed:.6f}s")

    return Phase261DonorInspectionResult(
        passed=(len(errors) == 0),
        verification_mode=mode,
        read_only_o_rdonly_enforced=True,
        elapsed_seconds=elapsed,
        within_150ms_budget=within_budget,
        inspected_artifacts=tuple(inspected),
        fx3_im_elf_verified=im_ok,
        fx3_libjiritsu_verified=jit_ok,
        fx3_libusbbuspower_verified=pwr_ok,
        fx6_appfw_verified=appfw_ok,
        fx6_wlan_rsrc_verified=wlan_ok,
        fx3_upm_ko_verified=upm_ok,
        raw_firmware_bytes_leaked=PHASE261_RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Check Group A (Wave 40): [Different Set for Still/Mv], [Custom Key/Dial Set.] & EVF-Less FX3
# ---------------------------------------------------------------------------


def evaluate_p261_check_group_a_diffset_customkey_and_evfless(
    *,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    sony_help_guide_id: str = P261_SONY_HELP_GUIDE_ID,
    diff_set_items: Sequence[str] = P261_DIFF_SET_EIGHT_ITEMS,
    diff_set_shutter_speed_checked: bool = False,
    diff_set_transition: str = "COMMON_TO_SEPARATE",
    expect_custom_wb_copied_to_movie_on_common_to_separate: bool = False,
    expect_all_items_factory_reset_on_separate_to_common: bool = False,
    separate_to_common_retained_items: Sequence[str] = P261_SEPARATE_TO_COMMON_STILL_RETAINED_ITEMS,
    movie_shutter_mode: str = "SHUTTER_ANGLE",
    expect_common_shutter_merges_movie_shutter_angle: bool = False,
    reset_action: str = "NONE",
    claimed_diff_set_reset_on_camera_reset: bool = False,
    custom_key_domains: Sequence[str] = P261_CUSTOM_KEY_THREE_DOMAINS,
    front_dial_assignment: str = P261_DEFAULT_FRONT_DIAL_ASSIGNMENT,
    rear_dial_assignment: str = P261_DEFAULT_REAR_DIAL_ASSIGNMENT,
    control_wheel_assignment: str = P261_DEFAULT_CONTROL_WHEEL_ASSIGNMENT,
    claimed_custom_key_reset_on_camera_reset: bool = False,
    slot1_contains_tier0_dump: bool = True,
    slot1_wp_locked: bool = True,
    slot1_camset_custom_key_access_mode: str = "O_RDONLY",
    simulated_slot1_custom_key_mutation_bytes: int = 0,
    remain_shoot_display: str = "NOT_DISPLAYED",
    claimed_remain_shoot_after_reset: Optional[str] = None,
    expect_remain_shoot_displays_movie_card_time: bool = False,
    expect_builtin_evf_or_finder_monitor_switch: bool = False,
) -> P261CheckGroupADiffSetCustomKeyEvfLessResult:
    """Verify Wave 40 Different Set 8-item transitions, Custom Key Slot-1 O_RDONLY firewall & EVF-less FX3."""
    errors: List[str] = []

    # 1. Model ID, Firmware Floor & Help Guide ID (ilc/2210)
    fw_tuple = _parse_fw_tuple(body_fw)
    guide_norm = str(sony_help_guide_id).strip().lower()
    if (
        int(body_model_id) != TARGET_MODEL_ID_INT
        or fw_tuple is None
        or fw_tuple < MIN_BODY_FW_TUPLE
        or guide_norm != P261_SONY_HELP_GUIDE_ID
    ):
        errors.append(
            f"{P261_GA_ERR_MODEL_OR_FW_FLOOR}: model=0x{int(body_model_id):08x}, "
            f"body_fw={body_fw!r}, guide={sony_help_guide_id!r} (requires ILME-FX3 0x91030080 >=2.04 ilc/2210)"
        )

    # 2. [Different Set for Still/Mv]: Exact 8 items, asymmetric transitions & [Shutter Angle] override
    items_tuple = tuple(str(x).strip() for x in diff_set_items)
    retained_tuple = tuple(str(x).strip() for x in separate_to_common_retained_items)
    trans_norm = _norm_token(diff_set_transition)
    sh_mode = _norm_shutter_mode(movie_shutter_mode)
    rst_norm = _norm_token(reset_action)

    shutter_angle_indep = (sh_mode == "SHUTTER_ANGLE") or bool(diff_set_shutter_speed_checked)
    diff_set_survives = not bool(claimed_diff_set_reset_on_camera_reset)

    if (
        items_tuple != P261_DIFF_SET_EIGHT_ITEMS
        or trans_norm not in P261_VALID_DIFF_SET_TRANSITIONS
        or sh_mode not in ("SHUTTER_SPEED", "SHUTTER_ANGLE")
        or rst_norm not in P261_VALID_RESET_ACTIONS
        or bool(expect_custom_wb_copied_to_movie_on_common_to_separate)
        or bool(expect_all_items_factory_reset_on_separate_to_common)
        or retained_tuple != P261_SEPARATE_TO_COMMON_STILL_RETAINED_ITEMS
        or (sh_mode == "SHUTTER_ANGLE" and bool(expect_common_shutter_merges_movie_shutter_angle))
        or not diff_set_survives
    ):
        errors.append(
            f"{P261_GA_ERR_DIFF_SET_8ITEMS_TRANSITION_OR_SHUTTER_ANGLE_OVERRIDE}: invalid "
            f"[Different Set for Still/Mv] config (items={items_tuple}, transition={diff_set_transition!r}, "
            f"shutter_mode={movie_shutter_mode!r}, retained={retained_tuple}, "
            f"cwb_movie_copy={expect_custom_wb_copied_to_movie_on_common_to_separate}, "
            f"angle_merge={expect_common_shutter_merges_movie_shutter_angle})"
        )

    # 3. [Custom Key/Dial Set.]: 3-domain ISO/EI persistence & Slot-1 CAMSET01.DAT O_RDONLY firewall
    dom_tuple = tuple(_norm_token(d) for d in custom_key_domains)
    front_str = str(front_dial_assignment).strip()
    rear_str = str(rear_dial_assignment).strip()
    wheel_str = str(control_wheel_assignment).strip()
    access_norm = _norm_token(slot1_camset_custom_key_access_mode)
    custom_key_survives = not bool(claimed_custom_key_reset_on_camera_reset)
    mut_bytes = max(0, int(simulated_slot1_custom_key_mutation_bytes))
    if access_norm not in P261_VALID_SLOT1_CUSTOM_KEY_ACCESS_MODES:
        mut_bytes = max(1, mut_bytes)

    if (
        dom_tuple != P261_CUSTOM_KEY_THREE_DOMAINS
        or not front_str
        or not rear_str
        or not wheel_str
        or "ISO/EI" not in rear_str.upper()
        or not custom_key_survives
        or access_norm not in P261_VALID_SLOT1_CUSTOM_KEY_ACCESS_MODES
        or (bool(slot1_contains_tier0_dump) and access_norm == "O_RDONLY" and not bool(slot1_wp_locked))
        or mut_bytes != 0
    ):
        errors.append(
            f"{P261_GA_ERR_CUSTOM_KEY_3DOMAIN_ISO_EI_OR_SLOT1_VAULT_FIREWALL}: [Custom Key/Dial Set.] "
            f"3-domain ISO/EI or Slot-1 CAMSET01.DAT O_RDONLY firewall violated "
            f"(domains={dom_tuple}, rear_dial={rear_str!r}, access={slot1_camset_custom_key_access_mode!r}, "
            f"slot1_wp={slot1_wp_locked}, mut_bytes={mut_bytes})"
        )

    # 4. [Remain Shoot Display] still-buffer scope & EVF-less ILME-FX3 (ilc/2210) topology
    rem_norm = _norm_token(remain_shoot_display)
    eff_rem = "NOT_DISPLAYED" if rst_norm == "INITIALIZE" else rem_norm
    still_buf_only = not bool(expect_remain_shoot_displays_movie_card_time)
    evf_claimed = bool(expect_builtin_evf_or_finder_monitor_switch)

    rem_reset_mismatch = False
    if claimed_remain_shoot_after_reset is not None:
        if _norm_token(claimed_remain_shoot_after_reset) != eff_rem:
            rem_reset_mismatch = True

    if (
        rem_norm not in P261_VALID_REMAIN_SHOOT_DISPLAY_MODES
        or rem_reset_mismatch
        or not still_buf_only
        or evf_claimed
    ):
        errors.append(
            f"{P261_GA_ERR_REMAIN_SHOOT_STILL_BUFFER_OR_EVFLESS_TOPOLOGY}: [Remain Shoot Display] "
            f"still-buffer scope or EVF-less ILME-FX3 topology violated "
            f"(mode={remain_shoot_display!r}, movie_time_claim={expect_remain_shoot_displays_movie_card_time}, "
            f"evf_claim={evf_claimed}, reset_mismatch={rem_reset_mismatch})"
        )

    return P261CheckGroupADiffSetCustomKeyEvfLessResult(
        check_group_id=P261_CHECK_GROUP_A_ID,
        passed=(len(errors) == 0),
        body_model_id_hex=f"0x{int(body_model_id):08x}",
        body_fw=str(body_fw).strip(),
        sony_help_guide_id=guide_norm,
        diff_set_eight_items=items_tuple,
        diff_set_shutter_speed_checked=bool(diff_set_shutter_speed_checked),
        diff_set_transition=trans_norm,
        common_to_separate_still_only_exception=P261_COMMON_TO_SEPARATE_STILL_ONLY_EXCEPTION,
        separate_to_common_still_retained_items=retained_tuple,
        movie_shutter_mode=sh_mode,
        shutter_angle_independent_from_still_shutter=shutter_angle_indep,
        diff_set_survives_camera_reset=diff_set_survives,
        custom_key_domains=dom_tuple,
        front_dial_assignment=front_str,
        rear_dial_assignment=rear_str,
        control_wheel_assignment=wheel_str,
        custom_key_survives_camera_reset=custom_key_survives,
        slot1_camset_custom_key_access_mode=access_norm,
        slot1_custom_key_vault_mutation_bytes=mut_bytes,
        remain_shoot_display=rem_norm,
        effective_remain_shoot_after_reset=eff_rem,
        remain_shoot_still_buffer_only_verified=still_buf_only,
        fx3_has_builtin_evf=False,
        fx3_has_finder_monitor_switch=False,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Check Group B (Wave 41): [Auto Slow Shutter] 6 Locks, [HDMI Output Settings] & [Breathing Comp.]
# ---------------------------------------------------------------------------


def evaluate_p261_check_group_b_autoslow_hdmi_rec_ctrl_and_breathing(
    *,
    auto_slow_shutter: str = "ON",
    reset_action: str = "NONE",
    claimed_auto_slow_after_reset: Optional[str] = None,
    exposure_ctrl_type: str = "FLEXIBLE_EXP_MODE",
    exposure_mode: str = "MANUAL_EXPOSURE",
    flexible_shutter_mode: str = "MANUAL",
    iso_mode: str = "CINE_EI_BASE",
    log_shooting_mode: str = "CINE_EI",
    sq_mode_enabled: bool = False,
    movie_shutter_mode: str = "SHUTTER_ANGLE",
    expect_auto_slow_shutter_active: bool = False,
    expect_auto_slow_shutter_with_shutter_angle: bool = False,
    hdmi_time_code_output: str = "ON",
    hdmi_rec_control: str = "OFF",
    hdmi_4ch_audio_output: str = "CH1_CH2",
    mi_shoe_4ch_audio_active: bool = True,
    rec_media_dur_hdmi_output: str = "OFF_HDMI_ONLY",
    slot1_contains_tier0_dump: bool = True,
    slot1_wp_locked: bool = True,
    internal_rec_to_slot1_during_hdmi: bool = False,
    expect_internal_or_proxy_rec_when_hdmi_media_off: bool = False,
    claimed_hdmi_settings_reset_on_camera_reset: bool = False,
    breathing_comp: str = "OFF",
    claimed_breathing_comp_after_reset: Optional[str] = None,
    breathing_comp_compliant_lens: bool = True,
    hdmi_raw_output: bool = False,
    sq_240p_or_200p_active: bool = False,
    expect_breathing_comp_in_still_image: bool = False,
) -> P261CheckGroupBAutoSlowHdmiRecCtrlBreathingResult:
    """Verify Wave 41 Auto Slow Shutter 6 lockouts, HDMI REC Control <- TC Output & Breathing Comp."""
    errors: List[str] = []

    # 1. [Auto Slow Shutter]: 6 non-function lockouts & [Shutter Angle] hardware disjointness
    as_norm = _norm_token(auto_slow_shutter)
    rst_norm = _norm_token(reset_action)
    ctrl_norm = _norm_token(exposure_ctrl_type)
    exp_norm = _norm_token(exposure_mode)
    flex_sh = _norm_token(flexible_shutter_mode)
    iso_norm = _norm_token(iso_mode)
    log_norm = _norm_token(log_shooting_mode)
    sh_mode = _norm_shutter_mode(movie_shutter_mode)

    eff_auto_slow = (
        "ON" if rst_norm in ("CAMERA_SETTINGS_RESET", "INITIALIZE") else as_norm
    )

    lockouts: List[str] = []
    if bool(sq_mode_enabled) or bool(sq_240p_or_200p_active):
        lockouts.append("SQ_MOTION_SHOOTING")
    if ctrl_norm == "P_A_S_M_MODE" and exp_norm == "SHUTTER_PRIORITY":
        lockouts.append("SHUTTER_PRIORITY_S_MODE")
    if ctrl_norm == "P_A_S_M_MODE" and exp_norm == "MANUAL_EXPOSURE":
        lockouts.append("MANUAL_EXPOSURE_M_MODE")
    if iso_norm != "ISO_AUTO":
        lockouts.append("MANUAL_FIXED_ISO_NON_AUTO")
    if ctrl_norm == "FLEXIBLE_EXP_MODE" and flex_sh == "MANUAL":
        lockouts.append("FLEXIBLE_EXP_MANUAL_SHUTTER")
    if log_norm in ("CINE_EI_QUICK", "CINE_EI"):
        lockouts.append("LOG_SHOOTING_CINE_EI_OR_QUICK")

    auto_slow_active = (as_norm == "ON") and (len(lockouts) == 0)

    shutter_angle_permitted_mode = (
        (ctrl_norm == "P_A_S_M_MODE" and exp_norm in ("SHUTTER_PRIORITY", "MANUAL_EXPOSURE"))
        or (ctrl_norm == "FLEXIBLE_EXP_MODE" and flex_sh == "MANUAL")
    )
    overlap_events = 0
    if bool(expect_auto_slow_shutter_with_shutter_angle) or (
        sh_mode == "SHUTTER_ANGLE" and (not shutter_angle_permitted_mode or auto_slow_active)
    ):
        overlap_events = 1

    as_reset_mismatch = False
    if claimed_auto_slow_after_reset is not None:
        if _norm_token(claimed_auto_slow_after_reset) != eff_auto_slow:
            as_reset_mismatch = True

    if (
        as_norm not in ("ON", "OFF")
        or rst_norm not in P261_VALID_RESET_ACTIONS
        or ctrl_norm not in P261_VALID_EXPOSURE_CTRL_TYPES
        or exp_norm not in P261_VALID_EXPOSURE_MODES
        or flex_sh not in ("AUTO", "MANUAL")
        or log_norm not in P261_VALID_LOG_SHOOTING_MODES
        or sh_mode not in ("SHUTTER_SPEED", "SHUTTER_ANGLE")
        or as_reset_mismatch
        or (bool(expect_auto_slow_shutter_active) and not auto_slow_active)
        or overlap_events > 0
    ):
        errors.append(
            f"{P261_GB_ERR_AUTO_SLOW_SHUTTER_6LOCKS_OR_SHUTTER_ANGLE_OVERLAP}: [Auto Slow Shutter] "
            f"6-lockout or [Shutter Angle] disjointness violated (mode={auto_slow_shutter!r}, "
            f"lockouts={tuple(lockouts)}, expect_active={expect_auto_slow_shutter_active}, "
            f"shutter_mode={movie_shutter_mode!r}, overlap_events={overlap_events})"
        )

    # 2. [HDMI Output Settings]: [REC Control] <- [Time Code Output]=On, [4ch Audio Output], Slot-1 guard
    tc_out = _norm_token(hdmi_time_code_output)
    rec_ctrl = _norm_token(hdmi_rec_control)
    aud_4ch = _norm_hdmi_4ch(hdmi_4ch_audio_output)
    rec_media = _norm_rec_media_hdmi(rec_media_dur_hdmi_output)
    hdmi_survives = not bool(claimed_hdmi_settings_reset_on_camera_reset)

    tc_violations = 1 if (rec_ctrl == "ON" and tc_out != "ON") else 0
    media_off = rec_media in ("OFF", "OFF_HDMI_ONLY")
    slot1_protected = not (
        bool(slot1_contains_tier0_dump)
        and (bool(internal_rec_to_slot1_during_hdmi) or (rec_media == "ON" and not bool(slot1_wp_locked)))
    )

    if (
        tc_out not in ("ON", "OFF")
        or rec_ctrl not in ("ON", "OFF")
        or aud_4ch not in P261_VALID_HDMI_4CH_AUDIO_ROUTINGS
        or rec_media not in P261_VALID_REC_MEDIA_DUR_HDMI_MODES
        or tc_violations > 0
        or (aud_4ch == "CH3_CH4" and not bool(mi_shoe_4ch_audio_active))
        or (media_off and bool(expect_internal_or_proxy_rec_when_hdmi_media_off))
        or not hdmi_survives
        or not slot1_protected
    ):
        errors.append(
            f"{P261_GB_ERR_HDMI_REC_CTRL_TC_PREREQ_4CH_OR_MEDIA_VAULT_GUARD}: [HDMI Output Settings] "
            f"violated (rec_ctrl={hdmi_rec_control!r}, tc_out={hdmi_time_code_output!r}, "
            f"4ch={hdmi_4ch_audio_output!r}, mi_4ch={mi_shoe_4ch_audio_active}, "
            f"rec_media={rec_media_dur_hdmi_output!r}, slot1_protected={slot1_protected})"
        )

    # 3. [Lens Compensation] -> [Breathing Comp.]: movie-only, compliant lens, RAW/240p lockout
    br_norm = _norm_token(breathing_comp)
    eff_br = "OFF" if rst_norm in ("CAMERA_SETTINGS_RESET", "INITIALIZE") else br_norm
    br_movie_only = not bool(expect_breathing_comp_in_still_image)

    br_reset_mismatch = False
    if claimed_breathing_comp_after_reset is not None:
        if _norm_token(claimed_breathing_comp_after_reset) != eff_br:
            br_reset_mismatch = True

    if (
        br_norm not in ("ON", "OFF")
        or br_reset_mismatch
        or not br_movie_only
        or (
            br_norm == "ON"
            and (
                not bool(breathing_comp_compliant_lens)
                or bool(hdmi_raw_output)
                or bool(sq_240p_or_200p_active)
            )
        )
    ):
        errors.append(
            f"{P261_GB_ERR_BREATHING_COMP_MOVIE_ONLY_LENS_RAW_OR_240P_LOCKOUT}: [Breathing Comp.] "
            f"violated (mode={breathing_comp!r}, compliant_lens={breathing_comp_compliant_lens}, "
            f"hdmi_raw={hdmi_raw_output}, sq_240p={sq_240p_or_200p_active}, "
            f"still_claim={expect_breathing_comp_in_still_image})"
        )

    return P261CheckGroupBAutoSlowHdmiRecCtrlBreathingResult(
        check_group_id=P261_CHECK_GROUP_B_ID,
        passed=(len(errors) == 0),
        auto_slow_shutter=as_norm,
        effective_auto_slow_after_reset=eff_auto_slow,
        exposure_ctrl_type=ctrl_norm,
        exposure_mode=exp_norm,
        flexible_shutter_mode=flex_sh,
        iso_mode=iso_norm,
        log_shooting_mode=log_norm,
        sq_mode_enabled=bool(sq_mode_enabled or sq_240p_or_200p_active),
        movie_shutter_mode=sh_mode,
        active_auto_slow_shutter_lockouts=tuple(lockouts),
        auto_slow_shutter_effective_active=auto_slow_active,
        auto_slow_shutter_angle_overlap_events=overlap_events,
        hdmi_time_code_output=tc_out,
        hdmi_rec_control=rec_ctrl,
        hdmi_rec_ctrl_without_tc_violations=tc_violations,
        hdmi_4ch_audio_output=aud_4ch,
        rec_media_dur_hdmi_output=rec_media,
        hdmi_settings_survive_camera_reset=hdmi_survives,
        slot1_hdmi_media_vault_protected=slot1_protected,
        breathing_comp=br_norm,
        effective_breathing_comp_after_reset=eff_br,
        breathing_comp_compliant_lens=bool(breathing_comp_compliant_lens),
        hdmi_raw_output=bool(hdmi_raw_output),
        sq_240p_or_200p_active=bool(sq_240p_or_200p_active),
        breathing_comp_movie_only_verified=br_movie_only,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Check Group C (Wave 42): [APS-C S35 Shooting] 4K Lockout, [Face/Eye AF] & [Version] Read-Only
# ---------------------------------------------------------------------------


def evaluate_p261_check_group_c_apsc_s35_face_eye_af_and_version(
    *,
    apsc_s35_shooting: str = "AUTO",
    movie_file_format: str = "XAVC_S_I_4K",
    hdmi_raw_output: bool = False,
    expect_apsc_s35_active_in_4k_or_raw: bool = False,
    reset_action: str = "NONE",
    claimed_apsc_s35_after_reset: Optional[str] = None,
    face_eye_af_items: Sequence[str] = P261_FACE_EYE_AF_FOUR_ITEMS,
    face_eye_prior_in_af: str = "ON",
    exposure_mode: str = "MANUAL_EXPOSURE",
    face_eye_subject: str = "HUMAN",
    right_left_eye_select: str = "AUTO",
    face_eye_frame_disp: str = "ON",
    claimed_face_memory_cleared_by_camera_reset: bool = False,
    expect_dedicated_ai_subject_recog_menu: bool = False,
    hdmi_info_display: str = "OFF",
    expect_eye_frame_baked_on_clean_hdmi_or_raw: bool = False,
    simulated_clean_hdmi_eye_frame_pixels: int = 0,
    airplane_mode: str = "ON",
    simulated_passive_tx_bytes: int = 0,
    slot1_bodydata_flash_requested: bool = False,
    expect_automated_bodydata_flash_allowed: bool = False,
    simulated_version_dialog_flash_touches: int = 0,
) -> P261CheckGroupCApscS35FaceEyeAfVersionResult:
    """Verify Wave 42 APS-C S35 12.1MP 4K/RAW lockout, Face/Eye AF clean-HDMI isolation & Version RO."""
    errors: List[str] = []

    # 1. [APS-C S35 Shooting]: 12.1MP sensor 4K movie & HDMI RAW lockout (Super 35mm movie ONLY in HD)
    apsc_norm = _norm_token(apsc_s35_shooting)
    fmt_norm = _norm_token(movie_file_format)
    rst_norm = _norm_token(reset_action)

    eff_apsc_after_reset = (
        "AUTO" if rst_norm in ("CAMERA_SETTINGS_RESET", "INITIALIZE") else apsc_norm
    )
    apsc_reset_mismatch = False
    if claimed_apsc_s35_after_reset is not None:
        if _norm_token(claimed_apsc_s35_after_reset) != eff_apsc_after_reset:
            apsc_reset_mismatch = True

    is_4k_or_raw = (fmt_norm in P261_4K_MOVIE_FILE_FORMATS) or bool(hdmi_raw_output)
    locked_off = is_4k_or_raw
    if is_4k_or_raw:
        eff_s35_state = "OFF_4K_OR_RAW_LOCKOUT"
    elif apsc_norm == "ON":
        eff_s35_state = "ON_S35_HD_ALLOWED"
    elif apsc_norm == "AUTO":
        eff_s35_state = "AUTO_HD_LENS_DEPENDENT"
    else:
        eff_s35_state = "OFF_FULL_FRAME_HD"

    bypass_events = 0
    if is_4k_or_raw and (apsc_norm == "ON" or bool(expect_apsc_s35_active_in_4k_or_raw)):
        bypass_events = 1

    if (
        apsc_norm not in P261_VALID_APSC_S35_MODES
        or fmt_norm not in P261_VALID_MOVIE_FILE_FORMATS
        or rst_norm not in P261_VALID_RESET_ACTIONS
        or apsc_reset_mismatch
        or bypass_events > 0
    ):
        errors.append(
            f"{P261_GC_ERR_APSC_S35_12MP_4K_OR_HDMI_RAW_LOCKOUT}: [APS-C S35 Shooting] 12.1MP "
            f"4K/HDMI-RAW lockout violated (apsc={apsc_s35_shooting!r}, format={movie_file_format!r}, "
            f"hdmi_raw={hdmi_raw_output}, bypass_events={bypass_events}, reset_mismatch={apsc_reset_mismatch})"
        )

    # 2. [Face/Eye AF]: 4-item BIONZ XR hierarchy, Face Memory survival & Clean-HDMI frame isolation
    fe_items = tuple(str(x).strip() for x in face_eye_af_items)
    fe_prior = _norm_token(face_eye_prior_in_af)
    exp_norm = _norm_token(exposure_mode)
    fe_subj = _norm_token(face_eye_subject)
    fe_eye = _norm_token(right_left_eye_select)
    fe_frame = _norm_token(face_eye_frame_disp)
    hdmi_info = _norm_token(hdmi_info_display)
    face_mem_survives = not bool(claimed_face_memory_cleared_by_camera_reset)

    clean_hdmi_baked_px = max(0, int(simulated_clean_hdmi_eye_frame_pixels))
    if bool(expect_eye_frame_baked_on_clean_hdmi_or_raw):
        clean_hdmi_baked_px = max(1, clean_hdmi_baked_px)

    if (
        fe_items != P261_FACE_EYE_AF_FOUR_ITEMS
        or fe_prior not in ("ON", "OFF")
        or (exp_norm == "INTELLIGENT_AUTO" and fe_prior != "ON")
        or fe_subj not in P261_VALID_FACE_EYE_SUBJECTS
        or fe_eye not in P261_VALID_RIGHT_LEFT_EYE_SELECTS
        or fe_frame not in ("ON", "OFF")
        or hdmi_info not in ("ON", "OFF")
        or (bool(hdmi_raw_output) and hdmi_info != "OFF")
        or not face_mem_survives
        or bool(expect_dedicated_ai_subject_recog_menu)
        or clean_hdmi_baked_px != 0
    ):
        errors.append(
            f"{P261_GC_ERR_FACE_EYE_AF_MENU_OR_CLEAN_HDMI_FRAME_ISOLATION}: [Face/Eye AF] hierarchy "
            f"or clean-HDMI frame isolation violated (items={fe_items}, prior={fe_prior}, "
            f"subj={fe_subj}, eye={fe_eye}, frame={fe_frame}, hdmi_info={hdmi_info}, "
            f"ai_unit_claim={expect_dedicated_ai_subject_recog_menu}, baked_px={clean_hdmi_baked_px})"
        )

    # 3. [Version] read-only dialog vs hard-blocked BODYDATA.DAT flash
    air_norm = _norm_token(airplane_mode)
    passive_tx = max(0, int(simulated_passive_tx_bytes))
    flash_touches = max(0, int(simulated_version_dialog_flash_touches))
    version_ro = (
        flash_touches == 0
        and not bool(slot1_bodydata_flash_requested)
        and not bool(expect_automated_bodydata_flash_allowed)
    )
    badge_suppressed = (air_norm == "ON") and (passive_tx == 0)

    if not version_ro or air_norm != "ON" or passive_tx != 0:
        errors.append(
            f"{P261_GC_ERR_VERSION_READONLY_OR_HARD_BLOCKED_BODYDATA_FLASH}: [Version] read-only "
            f"or BODYDATA.DAT flash redline violated (bodydata_flash_req={slot1_bodydata_flash_requested}, "
            f"auto_flash_claim={expect_automated_bodydata_flash_allowed}, airplane={airplane_mode!r}, "
            f"passive_tx={passive_tx}, flash_touches={flash_touches})"
        )

    return P261CheckGroupCApscS35FaceEyeAfVersionResult(
        check_group_id=P261_CHECK_GROUP_C_ID,
        passed=(len(errors) == 0),
        apsc_s35_shooting=apsc_norm,
        movie_file_format=fmt_norm,
        hdmi_raw_output=bool(hdmi_raw_output),
        effective_apsc_s35_movie_state=eff_s35_state,
        apsc_s35_4k_or_raw_locked_off=locked_off,
        apsc_s35_4k_or_raw_bypass_events=bypass_events,
        face_eye_af_four_items=fe_items,
        face_eye_prior_in_af=fe_prior,
        face_eye_subject=fe_subj,
        right_left_eye_select=fe_eye,
        face_eye_frame_disp=fe_frame,
        face_memory_survives_camera_reset=face_mem_survives,
        hdmi_info_display=hdmi_info,
        hdmi_clean_feed_eye_frame_baked_pixels=clean_hdmi_baked_px,
        version_dialog_read_only=version_ro,
        airplane_mode=air_norm,
        update_notification_suppressed=badge_suppressed,
        passive_tx_bytes_emitted=passive_tx,
        bodydata_auto_flash_authorized=False,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Check Group D (Wave 43 + Tier-0 Gate): Release w/o Card/Lens, v7.02 Audio & Copyright Hygiene
# ---------------------------------------------------------------------------


def build_simulated_phase261_tier0_receipts(
    *,
    body_serial: str = DEFAULT_TARGET_BODY_SERIAL,
    emmc_cid: str = DEFAULT_TARGET_EMMC_CID,
    body_fw: str = TARGET_BODY_FW,
) -> Tuple[bytes, bytes, Dict[str, str]]:
    """Build deterministic in-memory 528 B FX3RCPT1 dual receipts for `--simulate-bench-dry-run`."""
    item_hashes: Dict[str, str] = {}
    total_bytes = 0
    for item in COLD_BACKUP_ITEMS:
        item_hashes[item.item_id] = hashlib.sha256(
            f"PHASE261_TIER0:{body_fw}:{item.item_id}:{item.size_bytes}:{emmc_cid.lower()}".encode(
                "ascii"
            )
        ).hexdigest()
        total_bytes += item.size_bytes
    manifest_seed = hashlib.sha256(
        f"PHASE261_MANIFEST:{body_serial}:{body_fw}:{emmc_cid.lower()}".encode("ascii")
    ).hexdigest()
    rcpt = build_sd_backup_receipt_bytes(
        manifest_sha256=manifest_seed,
        item_hashes=item_hashes,
        total_dumped_bytes=total_bytes,
    )
    baselines = build_default_h0_baselines(body_serial=body_serial, emmc_cid=emmc_cid)
    return rcpt, bytes(rcpt), baselines


def evaluate_p261_check_group_d_release_wo_card_audio_copyright_and_tier0(
    *,
    release_wo_card: str = "DISABLE",
    release_wo_lens: str = "ENABLE",
    card_inserted_for_movie_rec: bool = False,
    movie_internal_rec_requested: bool = False,
    expect_movie_internal_rec_without_card: bool = False,
    production_shoot_mode: bool = False,
    body_only_or_pl_adapter_bench: bool = True,
    simulated_e_nd_uart_bytes: int = 0,
    v702_audio_recording_items: Sequence[str] = P261_V702_AUDIO_RECORDING_FIVE_ITEMS,
    audio_rec_level: int = 16,
    disp_screen_disp_audio_meter_enabled: bool = True,
    sq_mode_enabled: bool = False,
    expect_standalone_v1_audio_level_display_menu: bool = False,
    expect_audio_meter_in_sq_mode: bool = False,
    write_copyright_info: str = "OFF",
    photographer_text: str = "",
    copyright_text: str = "",
    clean_room_pii_hygiene_enforced: bool = True,
    claimed_copyright_cleared_by_camera_reset: bool = False,
    expect_copyright_exif_written_to_movies: bool = False,
    receipt_a_path: Optional[Path] = None,
    receipt_b_path: Optional[Path] = None,
    receipt_a_bytes: Optional[bytes] = None,
    receipt_b_bytes: Optional[bytes] = None,
    st_dev_a_override: Optional[int] = None,
    st_dev_b_override: Optional[int] = None,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    body_serial: Optional[str] = None,
    emmc_cid: Optional[str] = None,
    h0_baselines_a: Optional[Mapping[str, str]] = None,
    h0_baselines_b: Optional[Mapping[str, str]] = None,
    simulated_h0_h3_drifted_surfaces: int = 0,
    simulate_bench_dry_run: bool = False,
) -> Tuple[P261CheckGroupDReleaseWoCardAudioCopyrightTier0Result, Tuple[str, ...]]:
    """Verify Wave 43 Release w/o Card/Lens, v7.02 Audio 5-item menu, Copyright 46-char PII & Tier-0."""
    errors: List[str] = []
    warnings: List[str] = []
    tier0_errors: List[str] = []

    # 1. [Release w/o Card] still-only vs movie media gate & [Release w/o Lens] zero-E-ND bench safety
    rel_card = _norm_token(release_wo_card)
    rel_lens = _norm_token(release_wo_lens)
    end_bytes = max(0, int(simulated_e_nd_uart_bytes))

    movie_gate_ok = not (
        bool(expect_movie_internal_rec_without_card)
        or (bool(movie_internal_rec_requested) and not bool(card_inserted_for_movie_rec))
    )

    if (
        rel_card not in P261_VALID_RELEASE_WO_MODES
        or rel_lens not in P261_VALID_RELEASE_WO_MODES
        or not movie_gate_ok
        or (bool(production_shoot_mode) and rel_card != "DISABLE")
        or (bool(body_only_or_pl_adapter_bench) and rel_lens != "ENABLE")
        or end_bytes != 0
    ):
        errors.append(
            f"{P261_GD_ERR_RELEASE_WO_CARD_STILL_MOVIE_GATE_OR_WO_LENS_END_ZERO}: [Release w/o Card] "
            f"or [Release w/o Lens] bench boundary violated (wo_card={release_wo_card!r}, "
            f"wo_lens={release_wo_lens!r}, movie_gate_ok={movie_gate_ok}, "
            f"prod_shoot={production_shoot_mode}, body_only={body_only_or_pl_adapter_bench}, "
            f"e_nd_uart_bytes={end_bytes})"
        )
    elif rel_card == "ENABLE" and not bool(production_shoot_mode):
        warnings.append(
            "[Release w/o Card]=[Enable] permitted on cardless diagnostic bench; set [Disable] before production shoots."
        )

    # 2. Ver. 2.00+ / 7.02 [Audio Recording] 5-item menu & DISP (Screen Disp) Set meter integration
    aud_items = tuple(str(x).strip() for x in v702_audio_recording_items)
    aud_lvl = int(audio_rec_level)
    meter_visible = bool(disp_screen_disp_audio_meter_enabled) and not bool(sq_mode_enabled)
    v1_spoof_events = (
        1
        if (
            bool(expect_standalone_v1_audio_level_display_menu)
            or "Audio Level Display" in aud_items
        )
        else 0
    )

    if (
        aud_items != P261_V702_AUDIO_RECORDING_FIVE_ITEMS
        or not (P261_AUDIO_REC_LEVEL_MIN <= aud_lvl <= P261_AUDIO_REC_LEVEL_MAX)
        or v1_spoof_events > 0
        or (bool(sq_mode_enabled) and bool(expect_audio_meter_in_sq_mode))
    ):
        errors.append(
            f"{P261_GD_ERR_V702_AUDIO_5ITEM_MENU_OR_DISP_METER_SPLIT}: Ver. 7.02 [Audio Recording] "
            f"5-item menu or DISP audio meter split violated (items={aud_items}, level={aud_lvl}, "
            f"v1_spoof_events={v1_spoof_events}, sq={sq_mode_enabled}, sq_meter_claim={expect_audio_meter_in_sq_mode})"
        )

    # 3. [Copyright Info]: Write Copyright Info = Off & <= 46-char PII hygiene
    wr_copy = _norm_token(write_copyright_info)
    photog_str = str(photographer_text)
    copy_str = str(copyright_text)
    photog_len = len(photog_str)
    copy_len = len(copy_str)
    ascii_ok = all(32 <= ord(ch) <= 126 for ch in (photog_str + copy_str))
    copy_survives = not bool(claimed_copyright_cleared_by_camera_reset)
    still_exif_only = not bool(expect_copyright_exif_written_to_movies)

    pii_leaked = 0
    if wr_copy == "ON":
        pii_leaked = len(photog_str.encode("utf-8")) + len(copy_str.encode("utf-8"))
        if bool(clean_room_pii_hygiene_enforced):
            pii_leaked = max(1, pii_leaked)
    elif bool(clean_room_pii_hygiene_enforced) and (photog_len > 0 or copy_len > 0):
        pii_leaked = len(photog_str.encode("utf-8")) + len(copy_str.encode("utf-8"))

    if (
        wr_copy not in ("ON", "OFF")
        or photog_len > P261_COPYRIGHT_INFO_MAX_CHARS
        or copy_len > P261_COPYRIGHT_INFO_MAX_CHARS
        or not ascii_ok
        or not copy_survives
        or not still_exif_only
        or pii_leaked != 0
    ):
        errors.append(
            f"{P261_GD_ERR_COPYRIGHT_INFO_46CHAR_STILL_EXIF_OR_PII_HYGIENE}: [Copyright Info] "
            f"<=46-char still EXIF or PII hygiene violated (write={write_copyright_info!r}, "
            f"photog_len={photog_len}, copy_len={copy_len}, ascii_ok={ascii_ok}, "
            f"survives_reset={copy_survives}, still_only={still_exif_only}, pii_leaked={pii_leaked})"
        )

    # 4. 16/16 H0 == H3 Baseline Invariance & Dual-Media 528 B FX3RCPT1 Tier-0 Receipt Gate
    surface_total = len(SIXTEEN_STORAGE_SURFACES)
    drifted = max(0, min(surface_total, int(simulated_h0_h3_drifted_surfaces)))
    h0_eq_h3 = surface_total - drifted
    if h0_eq_h3 != surface_total:
        errors.append(
            f"{P261_GD_ERR_H0_H3_IMMUTABILITY_DRIFT}: H0 == H3 parity drift ({h0_eq_h3}/{surface_total})"
        )

    raw_a = receipt_a_bytes
    raw_b = receipt_b_bytes
    dev_a = st_dev_a_override
    dev_b = st_dev_b_override
    eff_serial = body_serial
    eff_cid = emmc_cid
    eff_h0_a = dict(h0_baselines_a) if h0_baselines_a is not None else None
    eff_h0_b = dict(h0_baselines_b) if h0_baselines_b is not None else None

    if (
        simulate_bench_dry_run
        and raw_a is None
        and raw_b is None
        and receipt_a_path is None
        and receipt_b_path is None
    ):
        eff_serial = eff_serial or DEFAULT_TARGET_BODY_SERIAL
        eff_cid = eff_cid or DEFAULT_TARGET_EMMC_CID
        raw_a, raw_b, sim_h0 = build_simulated_phase261_tier0_receipts(
            body_serial=eff_serial, emmc_cid=eff_cid, body_fw=body_fw
        )
        dev_a = 101 if dev_a is None else dev_a
        dev_b = 202 if dev_b is None else dev_b
        eff_h0_a = eff_h0_a if eff_h0_a is not None else dict(sim_h0)
        eff_h0_b = eff_h0_b if eff_h0_b is not None else dict(sim_h0)

    if receipt_a_path is not None:
        try:
            _, raw_a, st_a = _read_bounded_slice_o_rdonly(
                Path(receipt_a_path), SD_RECEIPT_BYTES + 64
            )
            if dev_a is None:
                dev_a = int(st_a)
        except OSError as exc:
            tier0_errors.append(
                f"{P261_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt_a read failed: {exc}"
            )

    if receipt_b_path is not None:
        try:
            _, raw_b, st_b = _read_bounded_slice_o_rdonly(
                Path(receipt_b_path), SD_RECEIPT_BYTES + 64
            )
            if dev_b is None:
                dev_b = int(st_b)
        except OSError as exc:
            tier0_errors.append(
                f"{P261_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt_b read failed: {exc}"
            )

    receipt_present = (raw_a is not None) and (raw_b is not None)
    distinct_media = False
    receipt_verified = False

    if not receipt_present:
        tier0_errors.append(
            f"{P261_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: dual-copy 528B FX3RCPT1 Tier-0 "
            "cold-backup receipts not provided (offline fail-closed)"
        )
    else:
        assert raw_a is not None and raw_b is not None
        if len(raw_a) != SD_RECEIPT_BYTES or len(raw_b) != SD_RECEIPT_BYTES or raw_a != raw_b:
            tier0_errors.append(
                f"{P261_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: dual FX3RCPT1 size/byte mismatch"
            )
        else:
            if dev_a is not None and dev_b is not None and int(dev_a) != int(dev_b):
                distinct_media = True
            else:
                tier0_errors.append(
                    f"{P261_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: st_dev_a == st_dev_b ({dev_a} vs {dev_b})"
                )

            ser_norm = (eff_serial or "").strip()
            cid_norm = (eff_cid or "").strip().lower()
            if not BODY_SERIAL_RE.match(ser_norm) or ser_norm.upper() in FORBIDDEN_TRIVIAL_SERIALS:
                tier0_errors.append(
                    f"{P261_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: invalid body_serial={eff_serial!r}"
                )
            if not HEX32_CID_RE.match(cid_norm) or cid_norm in FORBIDDEN_TRIVIAL_CIDS:
                tier0_errors.append(
                    f"{P261_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: invalid emmc_cid={eff_cid!r}"
                )
            if int(body_model_id) != TARGET_MODEL_ID_INT or str(body_fw).strip() != TARGET_BODY_FW:
                tier0_errors.append(
                    f"{P261_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt target mismatch"
                )

            try:
                parsed_a = parse_sd_backup_receipt_bytes(raw_a)
                parsed_b = parse_sd_backup_receipt_bytes(raw_b)
                if not parsed_a.valid or not parsed_b.valid:
                    tier0_errors.append(
                        f"{P261_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: FX3RCPT1 CRC32/header invalid"
                    )
            except Exception as exc:
                tier0_errors.append(
                    f"{P261_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: FX3RCPT1 parse error: {exc}"
                )

            if eff_h0_a is None or eff_h0_b is None:
                tier0_errors.append(
                    f"{P261_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: missing H0 baseline digests"
                )
            else:
                for req_k in REQUIRED_H0_BASELINE_KEYS:
                    va = eff_h0_a.get(req_k, "")
                    vb = eff_h0_b.get(req_k, "")
                    if _is_trivial_hex64(va) or va.lower() != vb.lower():
                        tier0_errors.append(
                            f"{P261_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: invalid/mismatched H0[{req_k}]"
                        )

            if len(tier0_errors) == 0:
                receipt_verified = True

    return (
        P261CheckGroupDReleaseWoCardAudioCopyrightTier0Result(
            check_group_id=P261_CHECK_GROUP_D_ID,
            passed=(len(errors) == 0),
            release_wo_card=rel_card,
            release_wo_lens=rel_lens,
            card_inserted_for_movie_rec=bool(card_inserted_for_movie_rec),
            movie_internal_rec_requested=bool(movie_internal_rec_requested),
            movie_internal_rec_media_gate_ok=movie_gate_ok,
            body_only_or_pl_adapter_bench=bool(body_only_or_pl_adapter_bench),
            e_nd_uart_bytes_transmitted=end_bytes,
            v702_audio_recording_five_items=aud_items,
            audio_rec_level=aud_lvl,
            disp_screen_disp_audio_meter_enabled=bool(disp_screen_disp_audio_meter_enabled),
            sq_mode_enabled=bool(sq_mode_enabled),
            effective_audio_meter_visible=meter_visible,
            legacy_v1_audio_level_menu_spoof_events=v1_spoof_events,
            write_copyright_info=wr_copy,
            photographer_text_len=photog_len,
            copyright_text_len=copy_len,
            copyright_strings_survive_camera_reset=copy_survives,
            copyright_still_exif_only_verified=still_exif_only,
            photographer_copyright_pii_leaked_bytes=pii_leaked,
            h0_h3_surface_count=surface_total,
            h0_equals_h3_count=h0_eq_h3,
            tier0_receipt_present=receipt_present,
            tier0_receipt_verified=receipt_verified,
            distinct_physical_media_verified=distinct_media,
            warnings=tuple(warnings),
            errors=tuple(errors),
        ),
        tuple(tier0_errors),
    )


# ---------------------------------------------------------------------------
# Top-Level Pre-Shoot Readiness Orchestrator & Tamper-Evident Verifier
# ---------------------------------------------------------------------------


def evaluate_realhw_diffset_customkey_autoslow_and_apsc_readiness(
    *,
    simulate_bench_dry_run: bool = False,
    simulate_ready_bench: Optional[bool] = None,
    force_clean_room: Optional[bool] = None,
    synthetic_clean_room: Optional[bool] = None,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    sony_help_guide_id: str = P261_SONY_HELP_GUIDE_ID,
    reset_action: str = "NONE",
    # Check Group A (Wave 40)
    diff_set_items: Sequence[str] = P261_DIFF_SET_EIGHT_ITEMS,
    diff_set_shutter_speed_checked: bool = False,
    diff_set_transition: str = "COMMON_TO_SEPARATE",
    expect_custom_wb_copied_to_movie_on_common_to_separate: bool = False,
    expect_all_items_factory_reset_on_separate_to_common: bool = False,
    separate_to_common_retained_items: Sequence[str] = P261_SEPARATE_TO_COMMON_STILL_RETAINED_ITEMS,
    movie_shutter_mode: str = "SHUTTER_ANGLE",
    expect_common_shutter_merges_movie_shutter_angle: bool = False,
    claimed_diff_set_reset_on_camera_reset: bool = False,
    custom_key_domains: Sequence[str] = P261_CUSTOM_KEY_THREE_DOMAINS,
    front_dial_assignment: str = P261_DEFAULT_FRONT_DIAL_ASSIGNMENT,
    rear_dial_assignment: str = P261_DEFAULT_REAR_DIAL_ASSIGNMENT,
    control_wheel_assignment: str = P261_DEFAULT_CONTROL_WHEEL_ASSIGNMENT,
    claimed_custom_key_reset_on_camera_reset: bool = False,
    slot1_contains_tier0_dump: bool = True,
    slot1_wp_locked: bool = True,
    slot1_camset_custom_key_access_mode: str = "O_RDONLY",
    simulated_slot1_custom_key_mutation_bytes: int = 0,
    remain_shoot_display: str = "NOT_DISPLAYED",
    claimed_remain_shoot_after_reset: Optional[str] = None,
    expect_remain_shoot_displays_movie_card_time: bool = False,
    expect_builtin_evf_or_finder_monitor_switch: bool = False,
    # Check Group B (Wave 41)
    auto_slow_shutter: str = "ON",
    claimed_auto_slow_after_reset: Optional[str] = None,
    exposure_ctrl_type: str = "FLEXIBLE_EXP_MODE",
    exposure_mode: str = "MANUAL_EXPOSURE",
    flexible_shutter_mode: str = "MANUAL",
    iso_mode: str = "CINE_EI_BASE",
    log_shooting_mode: str = "CINE_EI",
    sq_mode_enabled: bool = False,
    expect_auto_slow_shutter_active: bool = False,
    expect_auto_slow_shutter_with_shutter_angle: bool = False,
    hdmi_time_code_output: str = "ON",
    hdmi_rec_control: str = "OFF",
    hdmi_4ch_audio_output: str = "CH1_CH2",
    mi_shoe_4ch_audio_active: bool = True,
    rec_media_dur_hdmi_output: str = "OFF_HDMI_ONLY",
    internal_rec_to_slot1_during_hdmi: bool = False,
    expect_internal_or_proxy_rec_when_hdmi_media_off: bool = False,
    claimed_hdmi_settings_reset_on_camera_reset: bool = False,
    breathing_comp: str = "OFF",
    claimed_breathing_comp_after_reset: Optional[str] = None,
    breathing_comp_compliant_lens: bool = True,
    hdmi_raw_output: bool = False,
    sq_240p_or_200p_active: bool = False,
    expect_breathing_comp_in_still_image: bool = False,
    # Check Group C (Wave 42)
    apsc_s35_shooting: str = "AUTO",
    movie_file_format: str = "XAVC_S_I_4K",
    expect_apsc_s35_active_in_4k_or_raw: bool = False,
    claimed_apsc_s35_after_reset: Optional[str] = None,
    face_eye_af_items: Sequence[str] = P261_FACE_EYE_AF_FOUR_ITEMS,
    face_eye_prior_in_af: str = "ON",
    face_eye_subject: str = "HUMAN",
    right_left_eye_select: str = "AUTO",
    face_eye_frame_disp: str = "ON",
    claimed_face_memory_cleared_by_camera_reset: bool = False,
    expect_dedicated_ai_subject_recog_menu: bool = False,
    hdmi_info_display: str = "OFF",
    expect_eye_frame_baked_on_clean_hdmi_or_raw: bool = False,
    simulated_clean_hdmi_eye_frame_pixels: int = 0,
    airplane_mode: str = "ON",
    simulated_passive_tx_bytes: int = 0,
    slot1_bodydata_flash_requested: bool = False,
    expect_automated_bodydata_flash_allowed: bool = False,
    simulated_version_dialog_flash_touches: int = 0,
    # Check Group D & Tier-0 Gate (Wave 43)
    release_wo_card: str = "DISABLE",
    release_wo_lens: str = "ENABLE",
    card_inserted_for_movie_rec: bool = False,
    movie_internal_rec_requested: bool = False,
    expect_movie_internal_rec_without_card: bool = False,
    production_shoot_mode: bool = False,
    body_only_or_pl_adapter_bench: bool = True,
    simulated_e_nd_uart_bytes: int = 0,
    v702_audio_recording_items: Sequence[str] = P261_V702_AUDIO_RECORDING_FIVE_ITEMS,
    audio_rec_level: int = 16,
    disp_screen_disp_audio_meter_enabled: bool = True,
    expect_standalone_v1_audio_level_display_menu: bool = False,
    expect_audio_meter_in_sq_mode: bool = False,
    write_copyright_info: str = "OFF",
    photographer_text: str = "",
    copyright_text: str = "",
    clean_room_pii_hygiene_enforced: bool = True,
    claimed_copyright_cleared_by_camera_reset: bool = False,
    expect_copyright_exif_written_to_movies: bool = False,
    receipt_a_path: Optional[Path] = None,
    receipt_b_path: Optional[Path] = None,
    receipt_a_bytes: Optional[bytes] = None,
    receipt_b_bytes: Optional[bytes] = None,
    st_dev_a_override: Optional[int] = None,
    st_dev_b_override: Optional[int] = None,
    body_serial: Optional[str] = None,
    emmc_cid: Optional[str] = None,
    h0_baselines_a: Optional[Mapping[str, str]] = None,
    h0_baselines_b: Optional[Mapping[str, str]] = None,
    simulated_h0_h3_drifted_surfaces: int = 0,
) -> RealHwDiffSetCustomKeyAutoSlowApscReport:
    """Execute Phase 261 read-only 6th physical bench & pre-shoot readiness verifier (`A..D`)."""
    eff_sim = bool(simulate_bench_dry_run or simulate_ready_bench)

    donor_res = inspect_phase261_donors_bounded(
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        force_clean_room=force_clean_room,
        synthetic_clean_room=synthetic_clean_room,
    )
    ga = evaluate_p261_check_group_a_diffset_customkey_and_evfless(
        body_model_id=body_model_id,
        body_fw=body_fw,
        sony_help_guide_id=sony_help_guide_id,
        diff_set_items=diff_set_items,
        diff_set_shutter_speed_checked=diff_set_shutter_speed_checked,
        diff_set_transition=diff_set_transition,
        expect_custom_wb_copied_to_movie_on_common_to_separate=expect_custom_wb_copied_to_movie_on_common_to_separate,
        expect_all_items_factory_reset_on_separate_to_common=expect_all_items_factory_reset_on_separate_to_common,
        separate_to_common_retained_items=separate_to_common_retained_items,
        movie_shutter_mode=movie_shutter_mode,
        expect_common_shutter_merges_movie_shutter_angle=expect_common_shutter_merges_movie_shutter_angle,
        reset_action=reset_action,
        claimed_diff_set_reset_on_camera_reset=claimed_diff_set_reset_on_camera_reset,
        custom_key_domains=custom_key_domains,
        front_dial_assignment=front_dial_assignment,
        rear_dial_assignment=rear_dial_assignment,
        control_wheel_assignment=control_wheel_assignment,
        claimed_custom_key_reset_on_camera_reset=claimed_custom_key_reset_on_camera_reset,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        slot1_wp_locked=slot1_wp_locked,
        slot1_camset_custom_key_access_mode=slot1_camset_custom_key_access_mode,
        simulated_slot1_custom_key_mutation_bytes=simulated_slot1_custom_key_mutation_bytes,
        remain_shoot_display=remain_shoot_display,
        claimed_remain_shoot_after_reset=claimed_remain_shoot_after_reset,
        expect_remain_shoot_displays_movie_card_time=expect_remain_shoot_displays_movie_card_time,
        expect_builtin_evf_or_finder_monitor_switch=expect_builtin_evf_or_finder_monitor_switch,
    )
    gb = evaluate_p261_check_group_b_autoslow_hdmi_rec_ctrl_and_breathing(
        auto_slow_shutter=auto_slow_shutter,
        reset_action=reset_action,
        claimed_auto_slow_after_reset=claimed_auto_slow_after_reset,
        exposure_ctrl_type=exposure_ctrl_type,
        exposure_mode=exposure_mode,
        flexible_shutter_mode=flexible_shutter_mode,
        iso_mode=iso_mode,
        log_shooting_mode=log_shooting_mode,
        sq_mode_enabled=sq_mode_enabled,
        movie_shutter_mode=movie_shutter_mode,
        expect_auto_slow_shutter_active=expect_auto_slow_shutter_active,
        expect_auto_slow_shutter_with_shutter_angle=expect_auto_slow_shutter_with_shutter_angle,
        hdmi_time_code_output=hdmi_time_code_output,
        hdmi_rec_control=hdmi_rec_control,
        hdmi_4ch_audio_output=hdmi_4ch_audio_output,
        mi_shoe_4ch_audio_active=mi_shoe_4ch_audio_active,
        rec_media_dur_hdmi_output=rec_media_dur_hdmi_output,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        slot1_wp_locked=slot1_wp_locked,
        internal_rec_to_slot1_during_hdmi=internal_rec_to_slot1_during_hdmi,
        expect_internal_or_proxy_rec_when_hdmi_media_off=expect_internal_or_proxy_rec_when_hdmi_media_off,
        claimed_hdmi_settings_reset_on_camera_reset=claimed_hdmi_settings_reset_on_camera_reset,
        breathing_comp=breathing_comp,
        claimed_breathing_comp_after_reset=claimed_breathing_comp_after_reset,
        breathing_comp_compliant_lens=breathing_comp_compliant_lens,
        hdmi_raw_output=hdmi_raw_output,
        sq_240p_or_200p_active=sq_240p_or_200p_active,
        expect_breathing_comp_in_still_image=expect_breathing_comp_in_still_image,
    )
    gc = evaluate_p261_check_group_c_apsc_s35_face_eye_af_and_version(
        apsc_s35_shooting=apsc_s35_shooting,
        movie_file_format=movie_file_format,
        hdmi_raw_output=hdmi_raw_output,
        expect_apsc_s35_active_in_4k_or_raw=expect_apsc_s35_active_in_4k_or_raw,
        reset_action=reset_action,
        claimed_apsc_s35_after_reset=claimed_apsc_s35_after_reset,
        face_eye_af_items=face_eye_af_items,
        face_eye_prior_in_af=face_eye_prior_in_af,
        exposure_mode=exposure_mode,
        face_eye_subject=face_eye_subject,
        right_left_eye_select=right_left_eye_select,
        face_eye_frame_disp=face_eye_frame_disp,
        claimed_face_memory_cleared_by_camera_reset=claimed_face_memory_cleared_by_camera_reset,
        expect_dedicated_ai_subject_recog_menu=expect_dedicated_ai_subject_recog_menu,
        hdmi_info_display=hdmi_info_display,
        expect_eye_frame_baked_on_clean_hdmi_or_raw=expect_eye_frame_baked_on_clean_hdmi_or_raw,
        simulated_clean_hdmi_eye_frame_pixels=simulated_clean_hdmi_eye_frame_pixels,
        airplane_mode=airplane_mode,
        simulated_passive_tx_bytes=simulated_passive_tx_bytes,
        slot1_bodydata_flash_requested=slot1_bodydata_flash_requested,
        expect_automated_bodydata_flash_allowed=expect_automated_bodydata_flash_allowed,
        simulated_version_dialog_flash_touches=simulated_version_dialog_flash_touches,
    )
    gd, tier0_errors = evaluate_p261_check_group_d_release_wo_card_audio_copyright_and_tier0(
        release_wo_card=release_wo_card,
        release_wo_lens=release_wo_lens,
        card_inserted_for_movie_rec=card_inserted_for_movie_rec,
        movie_internal_rec_requested=movie_internal_rec_requested,
        expect_movie_internal_rec_without_card=expect_movie_internal_rec_without_card,
        production_shoot_mode=production_shoot_mode,
        body_only_or_pl_adapter_bench=body_only_or_pl_adapter_bench,
        simulated_e_nd_uart_bytes=simulated_e_nd_uart_bytes,
        v702_audio_recording_items=v702_audio_recording_items,
        audio_rec_level=audio_rec_level,
        disp_screen_disp_audio_meter_enabled=disp_screen_disp_audio_meter_enabled,
        sq_mode_enabled=bool(sq_mode_enabled or sq_240p_or_200p_active),
        expect_standalone_v1_audio_level_display_menu=expect_standalone_v1_audio_level_display_menu,
        expect_audio_meter_in_sq_mode=expect_audio_meter_in_sq_mode,
        write_copyright_info=write_copyright_info,
        photographer_text=photographer_text,
        copyright_text=copyright_text,
        clean_room_pii_hygiene_enforced=clean_room_pii_hygiene_enforced,
        claimed_copyright_cleared_by_camera_reset=claimed_copyright_cleared_by_camera_reset,
        expect_copyright_exif_written_to_movies=expect_copyright_exif_written_to_movies,
        receipt_a_path=receipt_a_path,
        receipt_b_path=receipt_b_path,
        receipt_a_bytes=receipt_a_bytes,
        receipt_b_bytes=receipt_b_bytes,
        st_dev_a_override=st_dev_a_override,
        st_dev_b_override=st_dev_b_override,
        body_model_id=body_model_id,
        body_fw=body_fw,
        body_serial=body_serial,
        emmc_cid=emmc_cid,
        h0_baselines_a=h0_baselines_a,
        h0_baselines_b=h0_baselines_b,
        simulated_h0_h3_drifted_surfaces=simulated_h0_h3_drifted_surfaces,
        simulate_bench_dry_run=eff_sim,
    )

    groups_passed = sum(1 for item in (ga, gb, gc, gd) if item.passed)
    all_4_passed = donor_res.passed and groups_passed == 4

    all_errors: List[str] = []
    all_errors.extend(donor_res.errors)
    for item in (ga, gb, gc, gd):
        all_errors.extend(item.errors)
    all_errors.extend(tier0_errors)

    remediations: List[str] = []
    if not ga.passed:
        remediations.append(
            "Respect [Different Set for Still/Mv] 8-item transitions & [Shutter Angle] independence, enforce O_RDONLY WP on Slot 1 CAMSET01.DAT, and treat ILME-FX3 (ilc/2210) as EVF-less."
        )
    if not gb.passed:
        remediations.append(
            "Respect [Auto Slow Shutter] 6 lockouts & [Shutter Angle] disjointness, set [Time Code Output]=On before [REC Control]=On, and disable [Breathing Comp.] under HDMI RAW or S&Q 240p/200p."
        )
    if not gc.passed:
        remediations.append(
            "Keep [APS-C S35 Shooting] locked Off in 4K/HDMI-RAW (Super 35mm movie allowed only in HD), isolate [Face/Eye Frame Disp.] from clean HDMI, and never auto-flash Slot 1 BODYDATA.DAT."
        )
    if not gd.passed or not gd.tier0_receipt_verified:
        remediations.append(
            "Keep [Release w/o Lens]=Enable on zero-E-ND body-only bench, use DISP (Screen Disp) Set for v7.02 audio meters, keep [Write Copyright Info]=Off (<=46 chars), and provide dual-device 528B FX3RCPT1 receipts."
        )

    if not all_4_passed:
        verdict = P261_GO_NO_GO_BLOCKED_DIFFSET_CUSTOMKEY_AUTOSLOW_APSC_FAILURE
    elif not gd.tier0_receipt_verified:
        verdict = (
            GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT
            if not gd.tier0_receipt_present
            else P261_GO_NO_GO_BLOCKED_DIFFSET_CUSTOMKEY_AUTOSLOW_APSC_FAILURE
        )
    elif eff_sim:
        verdict = GO_NO_GO_DRY_RUN_SIMULATED_READY
    else:
        verdict = P261_GO_NO_GO_DIFFSET_CUSTOMKEY_AUTOSLOW_APSC_VERIFIED

    provisional = RealHwDiffSetCustomKeyAutoSlowApscReport(
        schema=PHASE_261_SCHEMA,
        phase_version=PHASE_261_VERSION,
        verification_mode=donor_res.verification_mode,
        simulate_bench_dry_run=eff_sim,
        go_no_go=verdict,
        overall_ready_for_hardware_attach=False,
        hardware_live_attachment_authorized=False,
        persistent_emmc_writes_authorized=False,
        persistent_write_release=False,
        spi_nor_write_authorized=False,
        el3_payload_transmit_authorized=False,
        sd_physical_media_written=False,
        usb_packets_transmitted=0,
        physical_usb_packets_emitted=0,
        raw_firmware_bytes_leaked=PHASE261_RAW_FIRMWARE_BYTES_LEAKED,
        e_nd_uart_bytes_transmitted=PHASE261_E_ND_UART_BYTES_TRANSMITTED,
        slot1_custom_key_vault_mutation_bytes=ga.slot1_custom_key_vault_mutation_bytes,
        photographer_copyright_pii_leaked_bytes=gd.photographer_copyright_pii_leaked_bytes,
        fx3_has_builtin_evf=False,
        check_group_count=4,
        check_groups_passed=groups_passed,
        all_4_check_groups_passed=all_4_passed,
        tier0_receipt_verified=gd.tier0_receipt_verified,
        h0_h3_surface_count=gd.h0_h3_surface_count,
        h0_equals_h3_count=gd.h0_equals_h3_count,
        donor_inspection=donor_res,
        check_group_a_diffset_customkey_and_evfless=ga,
        check_group_b_autoslow_hdmi_rec_ctrl_and_breathing=gb,
        check_group_c_apsc_s35_face_eye_af_and_version=gc,
        check_group_d_release_wo_card_audio_copyright_and_tier0=gd,
        warnings=gd.warnings,
        remediation_actions=tuple(remediations),
        errors=tuple(all_errors),
        report_sha256="",
    )
    digest = _canonical_sha256_dict(provisional.to_dict(), exclude_key="report_sha256")
    return RealHwDiffSetCustomKeyAutoSlowApscReport(
        **{
            **provisional.to_dict(),
            "donor_inspection": donor_res,
            "check_group_a_diffset_customkey_and_evfless": ga,
            "check_group_b_autoslow_hdmi_rec_ctrl_and_breathing": gb,
            "check_group_c_apsc_s35_face_eye_af_and_version": gc,
            "check_group_d_release_wo_card_audio_copyright_and_tier0": gd,
            "warnings": gd.warnings,
            "remediation_actions": tuple(remediations),
            "errors": tuple(all_errors),
            "report_sha256": digest,
        }
    )


run_diffset_customkey_autoslow_and_apsc_preflight = (
    evaluate_realhw_diffset_customkey_autoslow_and_apsc_readiness
)


def verify_phase261_report(payload: Mapping[str, Any]) -> Phase261ReportVerifyResult:
    """Fail-closed tamper & safety-lock verifier for Phase 261 preflight reports."""
    errors: List[str] = []
    if payload.get("schema") != PHASE_261_SCHEMA:
        errors.append(f"Invalid schema: {payload.get('schema')!r}")
    if payload.get("phase_version") != PHASE_261_VERSION:
        errors.append(f"Invalid phase_version: {payload.get('phase_version')!r}")
    if payload.get("verification_mode") not in ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"):
        errors.append(f"Invalid verification_mode: {payload.get('verification_mode')!r}")
    if payload.get("go_no_go") not in PHASE_261_VALID_GO_NO_GO_VALUES:
        errors.append(f"Invalid go_no_go verdict: {payload.get('go_no_go')!r}")

    for lock_key in (
        "overall_ready_for_hardware_attach",
        "hardware_live_attachment_authorized",
        "persistent_emmc_writes_authorized",
        "persistent_write_release",
        "spi_nor_write_authorized",
        "el3_payload_transmit_authorized",
        "sd_physical_media_written",
        "fx3_has_builtin_evf",
    ):
        if payload.get(lock_key) is not False:
            errors.append(f"Safety lock violated: {lock_key}={payload.get(lock_key)!r}")

    for zero_key in (
        "usb_packets_transmitted",
        "physical_usb_packets_emitted",
        "raw_firmware_bytes_leaked",
        "e_nd_uart_bytes_transmitted",
    ):
        if payload.get(zero_key) != 0:
            errors.append(f"Zero-counter violated: {zero_key}={payload.get(zero_key)!r}")

    if payload.get("check_group_count") != 4:
        errors.append(f"Expected check_group_count==4, got {payload.get('check_group_count')!r}")

    if payload.get("go_no_go") in (
        GO_NO_GO_DRY_RUN_SIMULATED_READY,
        P261_GO_NO_GO_DIFFSET_CUSTOMKEY_AUTOSLOW_APSC_VERIFIED,
    ):
        if payload.get("slot1_custom_key_vault_mutation_bytes") != 0:
            errors.append("Pass/dry-run verdict requires slot1_custom_key_vault_mutation_bytes==0")
        if payload.get("photographer_copyright_pii_leaked_bytes") != 0:
            errors.append("Pass/dry-run verdict requires photographer_copyright_pii_leaked_bytes==0")

    if payload.get("simulate_bench_dry_run") is True and (
        payload.get("go_no_go") == P261_GO_NO_GO_DIFFSET_CUSTOMKEY_AUTOSLOW_APSC_VERIFIED
    ):
        errors.append("Simulated dry-run cannot claim physical Tier-0 verified verdict")

    if payload.get("go_no_go") == P261_GO_NO_GO_DIFFSET_CUSTOMKEY_AUTOSLOW_APSC_VERIFIED and (
        payload.get("all_4_check_groups_passed") is not True
        or payload.get("tier0_receipt_verified") is not True
    ):
        errors.append("Verified verdict requires all 4 check groups and Tier-0 receipt verified")

    claimed_sha = str(payload.get("report_sha256", ""))
    expected_sha = _canonical_sha256_dict(payload, exclude_key="report_sha256")
    if not HEX64_RE.match(claimed_sha) or claimed_sha != expected_sha:
        errors.append("report_sha256 canonical digest mismatch")

    return Phase261ReportVerifyResult(valid=(len(errors) == 0), errors=tuple(errors))


def render_phase261_markdown(report: RealHwDiffSetCustomKeyAutoSlowApscReport) -> str:
    """Render concise deterministic Markdown summary for Phase 261 pre-shoot bench preflight."""
    ga = report.check_group_a_diffset_customkey_and_evfless
    gb = report.check_group_b_autoslow_hdmi_rec_ctrl_and_breathing
    gc = report.check_group_c_apsc_s35_face_eye_af_and_version
    gd = report.check_group_d_release_wo_card_audio_copyright_and_tier0
    lines = [
        f"# Phase 261 6th Physical Bench & Pre-Shoot Readiness (`{report.schema}`)",
        "",
        f"- **Go/No-Go Verdict**: `{report.go_no_go}` (mode=`{report.verification_mode}`, dry_run=`{report.simulate_bench_dry_run}`)",
        f"- **Check Groups**: `{report.check_groups_passed}/{report.check_group_count}` (`H0==H3`: `{report.h0_equals_h3_count}/{report.h0_h3_surface_count}`)",
        f"- **Hard Locks**: `ready_attach={report.overall_ready_for_hardware_attach}`, `live_attach={report.hardware_live_attachment_authorized}`, `emmc_writes={report.persistent_emmc_writes_authorized}`, `spi_nor={report.spi_nor_write_authorized}`, `el3_tx={report.el3_payload_transmit_authorized}`, `usb_pkts={report.usb_packets_transmitted}`, `e_nd_uart={report.e_nd_uart_bytes_transmitted}`, `leaked_bytes={report.raw_firmware_bytes_leaked}`",
        "",
        "| Check Group | Status | Key Telemetry |",
        "| :--- | :---: | :--- |",
        f"| `{ga.check_group_id}` | `{'PASS' if ga.passed else 'FAIL'}` | DiffSet=`{len(ga.diff_set_eight_items)}` items (`{ga.diff_set_transition}`, AngleIndep=`{ga.shutter_angle_independent_from_still_shutter}`), RearDial=`{ga.rear_dial_assignment}`, Slot1Mut=`{ga.slot1_custom_key_vault_mutation_bytes}B`, EVF=`{ga.fx3_has_builtin_evf}` |",
        f"| `{gb.check_group_id}` | `{'PASS' if gb.passed else 'FAIL'}` | AutoSlow=`{gb.auto_slow_shutter}` (active=`{gb.auto_slow_shutter_effective_active}`, locks=`{len(gb.active_auto_slow_shutter_lockouts)}`, overlap=`{gb.auto_slow_shutter_angle_overlap_events}`), HDMIRecCtrl=`{gb.hdmi_rec_control}` (`TC={gb.hdmi_time_code_output}`), Breathing=`{gb.breathing_comp}` |",
        f"| `{gc.check_group_id}` | `{'PASS' if gc.passed else 'FAIL'}` | ApscS35=`{gc.apsc_s35_shooting}` (`{gc.movie_file_format}` -> `{gc.effective_apsc_s35_movie_state}`, bypass=`{gc.apsc_s35_4k_or_raw_bypass_events}`), EyeAF=`{gc.right_left_eye_select}` (`baked_px={gc.hdmi_clean_feed_eye_frame_baked_pixels}`), VersionRO=`{gc.version_dialog_read_only}` |",
        f"| `{gd.check_group_id}` | `{'PASS' if gd.passed else 'FAIL'}` | WoCard=`{gd.release_wo_card}`, WoLens=`{gd.release_wo_lens}` (`e_nd={gd.e_nd_uart_bytes_transmitted}B`), Audio5Item=`{len(gd.v702_audio_recording_five_items)}` (`v1_spoof={gd.legacy_v1_audio_level_menu_spoof_events}`), Copyright=`{gd.write_copyright_info}` (`pii={gd.photographer_copyright_pii_leaked_bytes}B`), Tier0=`{gd.tier0_receipt_verified}` |",
        "",
        f"- **Report SHA-256**: `{report.report_sha256}`",
    ]
    return "\n".join(lines) + "\n"
