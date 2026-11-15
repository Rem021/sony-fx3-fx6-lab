"""Phase 227 — Physical Bench & Pre-Shoot Media Readiness Verifier (`preflight-pixelmap-ntscpal-powersave-and-autotemp`).

Dedicated host-side read-only physical bench & pre-shoot media readiness verifier for Sony
`ILME-FX3` (`Ver. 7.02`, Model `0x91030080`), extending the operator bench preflight series
(`preflight-card-insert` -> `preflight-bench-cable-fan-slot1` ->
`preflight-hdmi-proxy-desqueeze-and-simult` ->
`preflight-pixelmap-ntscpal-powersave-and-autotemp`) by synthesizing Waves 29–31
real-hardware intelligence into 3 deterministic fail-closed check groups (`A..C`), bounded
`O_RDONLY` donor inspection (`< 0.15s`), and dual-media `528 B FX3RCPT1` Tier-0 receipt
gating:

1. **Check Group A (`GROUP_A_PIXEL_MAPPING_CNFLASHA_RO_AND_NTSCPAL_GAMMA_SPLIT`)**:
   - Blocks manual `[Pixel Mapping]` during low battery (`< 20%` SOC or low-battery warning),
     active Tier-0 cold dump, or unguarded calibration (`cnflasha` userspace `O_RDONLY`
     firewall, `cnflasha_calibration_mutation_bytes == 0`); models `[Auto Pixel Mapping]`
     power-off dark-frame shutter sound under `[Silent Mode]` + 3-day manual cadence,
     operator-control lockout during calibration, and mandatory auto-restart cleanly
     unmounting any volatile Stage-B `/tmp` RAM overlay (`H0 == H2`).
   - Verifies `[NTSC/PAL Selector]` (`NTSC` `23.98p` + `DF/NDF` vs `PAL` `25p/50p/100p` +
     unavailable `TC Format` & `23.98p`, startup notification banner, and dual-slot media DB
     tracking) **survives `[Camera Settings Reset]`** and is cleared **only by
     `[Initialize]`**.
   - Enforces `Ver. 7.02` 4-mode `[Gamma Disp. Assist Typ.]` (`Auto`, `S-Log3->709(800%)`,
     `HLG(BT.2020)`, `HLG(709)` — zero legacy `S-Log2`), hard-locks `[Gamma Display Assist]`
     to `[Off]` whenever `[Log Shooting]` is active (`Cine EI` / `Cine EI Quick` /
     `Flexible ISO` -> governed exclusively by `[Display LUT]`), and isolates
     `[Gamma Display Assist]` strictly to the built-in camera LCD (never HDMI).

2. **Check Group B (`GROUP_B_FILE_SETTINGS_SHOTMARK_TC_REGEN_AND_COUPLED_RECLAMP`)**:
   - Enforces `[File Settings]` (`Series` / `Reset`, `1..37` ASCII-char `[Title Name
     Settings]`, `Cam ID` `A..Z`, `Reel#` `001..999`, forward-only clip naming, and `SDHC`
     FAT32 unavailability forcing `[Standard]` + blocking custom movie folder names).
   - Enforces `Shot Mark1` / `Shot Mark2` **MP4 / XAVC-only** rule (`M4ROOT/CLIP/*M01.XML`
     `NonRealTimeMeta` sidecar + `[Image Jump Setting]`; strictly unavailable on still
     `JPEG`/`HEIF`/`RAW` photos or non-MP4/XAVC streams).
   - Enforces `[Time Code Make] = [Regenerate]` **Slot-1** exclusive reference tracking
     under `[Simult. Recording]` + forced `[Rec Run]` advancement, and emits/enforces the
     external `VMC-BNCM1` `EXT-LK` release warning (`Movie + Preset + Free Run` required;
     switching to `Regenerate` / `Rec Run` / `S&Q` immediately drops `EXT-LK`).
   - Enforces physical `[REC Lamp]` 3-state coupled tally (`All On`, `Only Front Off` with
     hardware-coupled Rear + Top `REC` button lamps, and `[Off]` / `All Off` silencing
     **both** body tally lamps **and** the `XLR-H1` top-handle `REC` lamp), plus `[Silent
     Mode] = [On]` -> `[Audio signals] = [Off]` lock.

3. **Check Group C (`GROUP_C_POWERSAVE_9COND_AUTOTEMP_TRIPOD_STEADYSHOT_AND_CIZ`)**:
   - Enforces `[Power Save Start Time]` (`Off` / `30 Min`) when all **9** automatic bypass
     conditions (`USB Power Supply`, `Slideshow Playback`, `FTP Transfer`, `Movie Recording`,
     `Computer Connection`, `TV/HDMI Connection`, `IR Remote Ctrl=On`, `Bluetooth Rmt
     Ctrl=On`, `Streaming/Cloud Upload`) are inactive on internal `NP-FZ100` battery during
     a `75 MiB` `p3` Tier-0 cold dump (blocking `5 Min` / `2 Min` / `1 Min` / `10 Sec` sleep
     hazards).
   - Enforces mandatory **tripod mounting** (forbidding handheld low-temp burn hazard and
     `[Fan Control] = [Always Off]`) when `[Auto Power OFF Temp.] = [High]`.
   - Verifies movie `[SteadyShot] = [Active]` (`~1.1x` crop, `8..1000mm` manual focal length)
     **3 hard cutoffs** (`119.88p/100p`, `S&Q >= 120/100fps`, and HDMI `RAW Output`).
   - Verifies `Clear Image Zoom` (`1.5x` 4K / `2.0x` HD) & `Digital Zoom` (`4.0x`) RAW/HFR
     cutoffs and all **4 AF/Metering locks** (`Focus Area` disabled/center-priority,
     `Metering Mode = [Multi]`, `Face/Eye Priority` disabled, `Real-time Tracking` disabled),
     `16/16 H0 == H3` storage parity, and dual-media `528 B FX3RCPT1` Tier-0 receipt gating.

Hard-Locked Safety Invariants (UNCONDITIONAL):
- `hardware_live_attachment_authorized = False`
- `persistent_emmc_writes_authorized = False`
- `persistent_write_release = False`
- `spi_nor_write_authorized = False`
- `el3_payload_transmit_authorized = False`
- `sd_physical_media_written = False`
- `usb_packets_transmitted = 0` (`physical_usb_packets_emitted = 0`)
- `raw_firmware_bytes_leaked = 0`
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
from typing import Any, Dict, List, Mapping, Optional, Tuple

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
    MAX_BODY_START_TEMP_C,
    MIN_BODY_FW_TUPLE,
    REQUIRED_H0_BASELINE_KEYS,
    TARGET_BODY_FW,
    TARGET_MODEL_ID_HEX,
    TARGET_MODEL_ID_INT,
    _parse_elf64_header_and_pt_load,
    _parse_fw_tuple,
    _read_bounded_slice_o_rdonly,
    build_default_h0_baselines,
)
from .realhw_hdmi_proxy_desqueeze_and_simult_verifier import (  # noqa: E402
    CAM_ID_ALLOWED_RE,
    REC_LAMP_ALL_OFF,
    REC_LAMP_ALL_ON,
    REC_LAMP_ONLY_FRONT_OFF,
    TITLE_ALLOWED_RE,
    TITLE_MAX_ASCII_CHARS,
    VALID_FILE_NAME_FORMATS,
    VALID_FILE_NUMBER_MODES,
    VALID_IMAGE_JUMP_MODES,
    VALID_REC_LAMP_MODES,
    VALID_SHOOT_MODES,
    VALID_TC_MAKE_MODES,
    VALID_TC_RUN_MODES,
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
# Schema, Verdicts & Domain Constants
# ---------------------------------------------------------------------------

PHASE_227_SCHEMA: str = "realhw_pixelmap_ntscpal_powersave_and_autotemp_verifier_v1"
REALHW_PIXELMAP_NTSCPAL_POWERSAVE_AUTOTEMP_SCHEMA: str = PHASE_227_SCHEMA
PHASE_227_VERSION: str = "227.0.0"

GO_NO_GO_PIXELMAP_NTSCPAL_POWERSAVE_AUTOTEMP_VERIFIED: str = (
    "GO_PIXELMAP_NTSCPAL_POWERSAVE_AUTOTEMP_READONLY_PREFLIGHT_VERIFIED"
)
GO_NO_GO_BLOCKED_PIXELMAP_NTSCPAL_POWERSAVE_AUTOTEMP_FAILURE: str = (
    "BLOCKED_PIXELMAP_NTSCPAL_POWERSAVE_AUTOTEMP_CHECK_FAILURE"
)
PHASE_227_VALID_GO_NO_GO_VALUES: Tuple[str, ...] = (
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    GO_NO_GO_BLOCKED_PIXELMAP_NTSCPAL_POWERSAVE_AUTOTEMP_FAILURE,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
    GO_NO_GO_PIXELMAP_NTSCPAL_POWERSAVE_AUTOTEMP_VERIFIED,
)

CHECK_GROUP_A_ID: str = "GROUP_A_PIXEL_MAPPING_CNFLASHA_RO_AND_NTSCPAL_GAMMA_SPLIT"
CHECK_GROUP_B_ID: str = "GROUP_B_FILE_SETTINGS_SHOTMARK_TC_REGEN_AND_COUPLED_RECLAMP"
CHECK_GROUP_C_ID: str = "GROUP_C_POWERSAVE_9COND_AUTOTEMP_TRIPOD_STEADYSHOT_AND_CIZ"
PHASE_227_CHECK_GROUP_IDS: Tuple[str, ...] = (
    CHECK_GROUP_A_ID,
    CHECK_GROUP_B_ID,
    CHECK_GROUP_C_ID,
)

PHASE227_RAW_FIRMWARE_BYTES_LEAKED: int = 0

# Check Group A Constants: Pixel Mapping, cnflasha O_RDONLY, NTSC/PAL Reset & Gamma Assist vs Display LUT
PIXEL_MAPPING_MIN_BATTERY_SOC_PCT: float = 20.0
PIXEL_MAPPING_RECOMMENDED_CADENCE_DAYS: int = 3
VALID_VIDEO_SYSTEMS: Tuple[str, ...] = ("NTSC", "PAL")
NTSC_ALLOWED_MOVIE_FPS: Tuple[float, ...] = (23.98, 24.0, 29.97, 59.94, 119.88)
PAL_ALLOWED_MOVIE_FPS: Tuple[float, ...] = (25.0, 50.0, 100.0)
NTSC_ALLOWED_TC_FORMATS: Tuple[str, ...] = ("DF", "NDF")
PAL_ALLOWED_TC_FORMATS: Tuple[str, ...] = ("UNAVAILABLE", "PAL_FIXED_25FPS")
VALID_RESET_ACTIONS: Tuple[str, ...] = ("NONE", "CAMERA_SETTINGS_RESET", "INITIALIZE")

VALID_GAMMA_ASSIST_TYPES: Tuple[str, ...] = (
    "AUTO",
    "S_LOG3_TO_709_800PCT",
    "HLG_BT2020",
    "HLG_709",
)
ACTIVE_LOG_SHOOTING_MODES: Tuple[str, ...] = (
    "ON",
    "CINE_EI",
    "CINE_EI_QUICK",
    "FLEXIBLE_ISO",
)
VALID_P227_LOG_SHOOTING_MODES: Tuple[str, ...] = ("OFF",) + ACTIVE_LOG_SHOOTING_MODES

# Check Group B Constants: File Settings, Shot Mark MP4/XAVC-only, TC Regenerate Slot-1 & Coupled REC Lamp
VALID_P227_SLOT_MEDIA_TYPES: Tuple[str, ...] = ("CFEXPRESS_A", "SDXC", "SDHC", "NONE")
MP4_XAVC_SHOTMARK_FORMATS: Tuple[str, ...] = (
    "XAVC_HS_4K",
    "XAVC_S_4K",
    "XAVC_S_HD",
    "XAVC_S_I_4K",
    "XAVC_S_I_HD",
    "MP4",
)
FORBIDDEN_STILL_OR_RAW_SHOTMARK_FORMATS: Tuple[str, ...] = (
    "JPEG",
    "HEIF",
    "RAW",
    "ARW",
    "RAW_AND_JPEG",
    "RAW_AND_HEIF",
    "HDMI_RAW_ONLY",
)
WARN_EXT_LK_RELEASED_BY_TC_CHANGE: str = (
    "WARN_EXT_LK_RELEASED_BY_TC_REGENERATE_OR_RUN_CHANGE"
)

# Check Group C Constants: Power Save 9-Condition Bypass, Auto Power OFF Temp., SteadyShot Active & CIZ
POWER_SAVE_MENU_EXACT_LABEL: str = "Power Save Start Time"
VALID_POWER_SAVE_START_TIMES: Tuple[str, ...] = (
    "OFF",
    "30_MIN",
    "5_MIN",
    "2_MIN",
    "1_MIN",
    "10_SEC",
)
SAFE_P3_75MIB_DUMP_POWER_SAVE_TIMES: Tuple[str, ...] = ("OFF", "30_MIN")
P3_75MIB_COLD_DUMP_MIB: int = 75
POWER_SAVE_NINE_BYPASS_CONDITIONS: Tuple[str, ...] = (
    "USB_POWER_SUPPLY",
    "SLIDESHOW_PLAYBACK",
    "FTP_TRANSFER",
    "MOVIE_RECORDING",
    "COMPUTER_CONNECTION",
    "TV_HDMI_CONNECTION",
    "IR_REMOTE_CTRL_ON",
    "BLUETOOTH_RMT_CTRL_ON",
    "STREAMING_OR_CLOUD_UPLOAD",
)
VALID_P227_POWER_SOURCES: Tuple[str, ...] = (
    "INTERNAL_NP_FZ100",
    "USB_PD_BODY",
    "DC_C1_COUPLER",
)
VALID_P227_FAN_MODES: Tuple[str, ...] = ("AUTO", "MINIMUM", "OFF_IN_REC", "ALWAYS_OFF")
VALID_STEADYSHOT_MOVIE_MODES: Tuple[str, ...] = ("OFF", "STANDARD", "ACTIVE")
STEADYSHOT_ACTIVE_CROP_FACTOR: float = 1.1
STEADYSHOT_MANUAL_FOCAL_MIN_MM: int = 8
STEADYSHOT_MANUAL_FOCAL_MAX_MM: int = 1000
STEADYSHOT_HFR_CUTOFF_FPS: float = 100.0

VALID_ZOOM_MODES: Tuple[str, ...] = ("OPTICAL_ONLY", "CLEAR_IMAGE_ZOOM", "DIGITAL_ZOOM")
CIZ_MAX_SCALE_4K: float = 1.5
CIZ_MAX_SCALE_HD: float = 2.0
DIGITAL_ZOOM_MAX_SCALE: float = 4.0
CIZ_FOUR_AF_METERING_LOCKS: Tuple[str, ...] = (
    "FocusAreaCenterPriority",
    "MeteringModeMulti",
    "FaceEyePriorityDisabled",
    "RealtimeTrackingDisabled",
)

# Error Codes
GA_ERR_MODEL_OR_FW_FLOOR: str = "GA_ERR_MODEL_OR_FW_FLOOR"
GA_ERR_PIXEL_MAPPING_LOW_BATTERY_BLOCKED: str = "GA_ERR_PIXEL_MAPPING_LOW_BATTERY_BLOCKED"
GA_ERR_PIXEL_MAPPING_DURING_ACTIVE_TIER0_DUMP: str = (
    "GA_ERR_PIXEL_MAPPING_DURING_ACTIVE_TIER0_DUMP"
)
GA_ERR_CNFLASHA_USERSPACE_RO_FIREWALL_VIOLATION: str = (
    "GA_ERR_CNFLASHA_USERSPACE_RO_FIREWALL_VIOLATION"
)
GA_ERR_PIXEL_MAPPING_MANDATORY_RESTART_OR_CONTROL_LOCK: str = (
    "GA_ERR_PIXEL_MAPPING_MANDATORY_RESTART_OR_CONTROL_LOCK"
)
GA_ERR_AUTO_PIXEL_MAPPING_CADENCE_OR_SHUTTER: str = (
    "GA_ERR_AUTO_PIXEL_MAPPING_CADENCE_OR_SHUTTER"
)
GA_ERR_NTSCPAL_FRAMERATE_OR_TC_FORMAT_CONFLICT: str = (
    "GA_ERR_NTSCPAL_FRAMERATE_OR_TC_FORMAT_CONFLICT"
)
GA_ERR_NTSCPAL_RESET_PERSISTENCE_OR_MEDIA_DB: str = (
    "GA_ERR_NTSCPAL_RESET_PERSISTENCE_OR_MEDIA_DB"
)
GA_ERR_GAMMA_ASSIST_VS_DISPLAY_LUT_SPLIT: str = "GA_ERR_GAMMA_ASSIST_VS_DISPLAY_LUT_SPLIT"
GA_ERR_GAMMA_ASSIST_EXTERNAL_HDMI_FORBIDDEN: str = (
    "GA_ERR_GAMMA_ASSIST_EXTERNAL_HDMI_FORBIDDEN"
)

GB_ERR_FILE_SETTINGS_TITLE_OR_NUMBER_INVALID: str = (
    "GB_ERR_FILE_SETTINGS_TITLE_OR_NUMBER_INVALID"
)
GB_ERR_SDHC_FILE_SETTINGS_UNAVAILABLE: str = "GB_ERR_SDHC_FILE_SETTINGS_UNAVAILABLE"
GB_ERR_SHOT_MARK_MP4_XAVC_ONLY_VIOLATION: str = "GB_ERR_SHOT_MARK_MP4_XAVC_ONLY_VIOLATION"
GB_ERR_TC_REGENERATE_SLOT1_OR_RECRUN_VIOLATION: str = (
    "GB_ERR_TC_REGENERATE_SLOT1_OR_RECRUN_VIOLATION"
)
GB_ERR_EXT_LK_RELEASE_OR_SQ_TC_VIOLATION: str = "GB_ERR_EXT_LK_RELEASE_OR_SQ_TC_VIOLATION"
GB_ERR_REC_LAMP_COUPLED_BODY_AND_XLR_H1_VIOLATION: str = (
    "GB_ERR_REC_LAMP_COUPLED_BODY_AND_XLR_H1_VIOLATION"
)
GB_ERR_SILENT_MODE_AUDIO_SIGNALS_LOCK: str = "GB_ERR_SILENT_MODE_AUDIO_SIGNALS_LOCK"

GC_ERR_POWER_SAVE_MENU_OR_BYPASS_INVALID: str = "GC_ERR_POWER_SAVE_MENU_OR_BYPASS_INVALID"
GC_ERR_NPFZ100_P3_75MIB_DUMP_SLEEP_HAZARD: str = (
    "GC_ERR_NPFZ100_P3_75MIB_DUMP_SLEEP_HAZARD"
)
GC_ERR_AUTO_POWER_OFF_TEMP_HIGH_REQUIRES_TRIPOD: str = (
    "GC_ERR_AUTO_POWER_OFF_TEMP_HIGH_REQUIRES_TRIPOD"
)
GC_ERR_FAN_OR_THERMAL_SAFETY_INTERLOCK: str = "GC_ERR_FAN_OR_THERMAL_SAFETY_INTERLOCK"
GC_ERR_STEADYSHOT_ACTIVE_CUTOFF_VIOLATION: str = (
    "GC_ERR_STEADYSHOT_ACTIVE_CUTOFF_VIOLATION"
)
GC_ERR_CIZ_RAW_HFR_OR_SCALE_FORBIDDEN: str = "GC_ERR_CIZ_RAW_HFR_OR_SCALE_FORBIDDEN"
GC_ERR_CIZ_FOUR_AF_METERING_LOCK_VIOLATION: str = (
    "GC_ERR_CIZ_FOUR_AF_METERING_LOCK_VIOLATION"
)
GC_ERR_H0_H3_IMMUTABILITY_DRIFT: str = "GC_ERR_H0_H3_IMMUTABILITY_DRIFT"
GC_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID: str = (
    "GC_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID"
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
class Phase227DonorInspectionResult:
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
class CheckGroupAPixelMapNtscPalGammaResult:
    check_group_id: str
    passed: bool
    body_model_id_hex: str
    body_fw: str
    auto_pixel_mapping: str
    days_since_manual_pixel_mapping: int
    manual_pixel_mapping_requested: bool
    pixel_mapping_allowed: bool
    battery_soc_pct: float
    tier0_dump_active: bool
    cnflasha_userspace_o_rdonly_enforced: bool
    cnflasha_calibration_mutation_bytes: int
    mandatory_auto_restart_modeled: bool
    stageb_volatile_ram_unmounted_on_reboot: bool
    ntsc_pal_selector: str
    regional_default_system: str
    startup_notification_banner: str
    reset_action: str
    effective_ntsc_pal_after_reset: str
    survives_camera_settings_reset: bool
    cleared_only_by_initialize: bool
    rec_frame_rate_fps: float
    tc_format: str
    log_shooting_mode: str
    gamma_display_assist: str
    effective_gamma_display_assist: str
    gamma_disp_assist_type: str
    display_lut: str
    gamma_assist_applied_to_hdmi: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class CheckGroupBFileSettingsTcRegenRecLampResult:
    check_group_id: str
    passed: bool
    file_name_format: str
    file_number_mode: str
    title_name: str
    title_ascii_length: int
    cam_id: str
    reel_number: int
    slot1_media_type: str
    slot2_media_type: str
    sdhc_present: bool
    sdhc_file_settings_unavailable_respected: bool
    clip_container_format: str
    shot_mark1_count: int
    shot_mark2_count: int
    shot_mark_mp4_xavc_only_verified: bool
    image_jump_setting: str
    shoot_mode: str
    simult_recording_enabled: bool
    tc_make: str
    requested_tc_run: str
    effective_tc_run: str
    tc_regenerate_slot1_tracked: bool
    vmc_bncm1_ext_lk_required: bool
    vmc_bncm1_ext_lk_preserved: bool
    ext_lk_released: bool
    rec_lamp_mode: str
    xlr_h1_attached: bool
    front_tally_lit: bool
    rear_tally_lit: bool
    top_rec_button_lit: bool
    xlr_h1_rec_lamp_lit: bool
    body_and_xlr_h1_reclamp_coupled_ok: bool
    silent_mode_enabled: bool
    audio_signals_mode: str
    warnings: Tuple[str, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class CheckGroupCPowerSaveAutoTempSteadyShotCizResult:
    check_group_id: str
    passed: bool
    power_save_menu_label: str
    power_save_start_time: str
    power_source: str
    active_bypass_conditions: Tuple[str, ...]
    power_save_bypassed: bool
    p3_75mib_cold_dump_active: bool
    np_fz100_p3_dump_sleep_safe: bool
    auto_power_off_temp: str
    tripod_mounted: bool
    handheld_operation_active: bool
    fan_control_mode: str
    body_temp_c: float
    steadyshot_mode: str
    steadyshot_crop_factor: float
    steadyshot_manual_focal_mm: int
    steadyshot_active_cutoff_reasons: Tuple[str, ...]
    steadyshot_cutoff_respected: bool
    zoom_mode: str
    zoom_scale: float
    video_resolution_class: str
    still_file_format: str
    ciz_four_locks: Tuple[str, ...]
    ciz_four_locks_satisfied: bool
    h0_h3_surface_count: int
    h0_equals_h3_count: int
    tier0_receipt_present: bool
    tier0_receipt_verified: bool
    distinct_physical_media_verified: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class RealHwPixelMapNtscPalPowerSaveAutoTempReport:
    schema: str
    phase_version: str
    verification_mode: str
    simulate_bench_dry_run: bool
    go_no_go: str
    hardware_live_attachment_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    spi_nor_write_authorized: bool
    el3_payload_transmit_authorized: bool
    sd_physical_media_written: bool
    usb_packets_transmitted: int
    physical_usb_packets_emitted: int
    raw_firmware_bytes_leaked: int
    check_group_count: int
    check_groups_passed: int
    all_3_check_groups_passed: bool
    tier0_receipt_verified: bool
    h0_h3_surface_count: int
    h0_equals_h3_count: int
    donor_inspection: Phase227DonorInspectionResult
    check_group_a_pixelmap_ntscpal_and_gamma: CheckGroupAPixelMapNtscPalGammaResult
    check_group_b_filesettings_tcregen_and_reclamp: CheckGroupBFileSettingsTcRegenRecLampResult
    check_group_c_powersave_autotemp_steadyshot_and_ciz: CheckGroupCPowerSaveAutoTempSteadyShotCizResult
    warnings: Tuple[str, ...]
    remediation_actions: Tuple[str, ...]
    errors: Tuple[str, ...]
    report_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_deterministic_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=False) + "\n"


@dataclass(frozen=True)
class Phase227ReportVerifyResult:
    valid: bool
    errors: Tuple[str, ...]


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------


def _norm_token(raw: str) -> str:
    return re.sub(r"[\s\-]+", "_", str(raw).strip().upper())


def _norm_gamma_assist_type(raw: str) -> str:
    s = str(raw).strip().upper()
    mapping = {
        "AUTO": "AUTO",
        "S-LOG3->709(800%)": "S_LOG3_TO_709_800PCT",
        "S-LOG3\u2192709(800%)": "S_LOG3_TO_709_800PCT",
        "S_LOG3_TO_709_800PCT": "S_LOG3_TO_709_800PCT",
        "SLOG3_709_800": "S_LOG3_TO_709_800PCT",
        "HLG(BT.2020)": "HLG_BT2020",
        "HLG_BT2020": "HLG_BT2020",
        "HLG(709)": "HLG_709",
        "HLG_709": "HLG_709",
    }
    return mapping.get(s, _norm_token(raw))


def _norm_power_save_time(raw: str) -> str:
    tok = _norm_token(raw)
    aliases = {
        "OFF": "OFF",
        "30MIN": "30_MIN",
        "30_MIN": "30_MIN",
        "5MIN": "5_MIN",
        "5_MIN": "5_MIN",
        "2MIN": "2_MIN",
        "2_MIN": "2_MIN",
        "1MIN": "1_MIN",
        "1_MIN": "1_MIN",
        "10SEC": "10_SEC",
        "10_SEC": "10_SEC",
    }
    return aliases.get(tok, tok)


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


# ---------------------------------------------------------------------------
# Bounded O_RDONLY Donor Inspection (< 0.15s) + Clean-Room Synthetic Fallback
# ---------------------------------------------------------------------------


def inspect_phase227_donors_bounded(
    *,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    force_clean_room: Optional[bool] = None,
    synthetic_clean_room: Optional[bool] = None,
    max_seconds: float = DONOR_INSPECTION_MAX_SECONDS,
) -> Phase227DonorInspectionResult:
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
        return Phase227DonorInspectionResult(
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
            raw_firmware_bytes_leaked=PHASE227_RAW_FIRMWARE_BYTES_LEAKED,
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

    return Phase227DonorInspectionResult(
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
        raw_firmware_bytes_leaked=PHASE227_RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Check Group A: Pixel Mapping Reboot / cnflasha RO Lock & NTSC/PAL Reset + Gamma/LUT Split
# ---------------------------------------------------------------------------


def evaluate_check_group_a_pixelmap_ntscpal_and_gamma_split(
    *,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    auto_pixel_mapping: str = "ON",
    days_since_manual_pixel_mapping: int = 0,
    expect_silent_mode_suppresses_auto_pixelmap_shutter: bool = False,
    manual_pixel_mapping_requested: bool = False,
    battery_soc_pct: float = 88.0,
    low_battery_warning_active: bool = False,
    tier0_dump_active: bool = False,
    unguarded_calibration_attempt: bool = False,
    cnflasha_userspace_o_rdonly_enforced: bool = True,
    cnflasha_calibration_mutation_bytes: int = 0,
    operator_controls_locked_during_calibration: bool = True,
    auto_restart_after_pixel_mapping: bool = True,
    stageb_volatile_ram_unmounted_on_reboot: bool = True,
    ntsc_pal_selector: str = "NTSC",
    regional_default_system: str = "NTSC",
    media_db_system: Optional[str] = None,
    rec_frame_rate_fps: float = 23.98,
    tc_format: str = "NDF",
    reset_action: str = "NONE",
    claimed_ntsc_pal_after_reset: Optional[str] = None,
    log_shooting_mode: str = "CINE_EI",
    gamma_display_assist: str = "OFF",
    gamma_disp_assist_type: str = "AUTO",
    display_lut: str = "ON",
    expect_gamma_assist_on_external_hdmi: bool = False,
) -> CheckGroupAPixelMapNtscPalGammaResult:
    errors: List[str] = []
    fw_clean = str(body_fw).strip()
    fw_tuple = _parse_fw_tuple(fw_clean)
    if (
        int(body_model_id) != TARGET_MODEL_ID_INT
        or fw_tuple is None
        or fw_tuple < MIN_BODY_FW_TUPLE
        or fw_clean != TARGET_BODY_FW
    ):
        errors.append(
            f"{GA_ERR_MODEL_OR_FW_FLOOR}: expected ILME-FX3 {TARGET_MODEL_ID_HEX} fw={TARGET_BODY_FW}, "
            f"got 0x{int(body_model_id) & 0xFFFFFFFF:08x} fw={fw_clean!r}"
        )

    # 1. [Auto Pixel Mapping] & Manual [Pixel Mapping] + cnflasha O_RDONLY Firewall
    auto_pm_norm = _norm_token(auto_pixel_mapping)
    days_int = int(days_since_manual_pixel_mapping)
    if auto_pm_norm not in ("ON", "OFF") or days_int < 0:
        errors.append(
            f"{GA_ERR_AUTO_PIXEL_MAPPING_CADENCE_OR_SHUTTER}: invalid [Auto Pixel Mapping]={auto_pixel_mapping!r} "
            f"or days_since_manual_pixel_mapping={days_int}"
        )
    if expect_silent_mode_suppresses_auto_pixelmap_shutter:
        errors.append(
            f"{GA_ERR_AUTO_PIXEL_MAPPING_CADENCE_OR_SHUTTER}: [Auto Pixel Mapping] dark-frame shutter sound "
            "at power-off occurs normally even when [Silent Mode]=[On]"
        )
    if (
        auto_pm_norm == "OFF"
        and days_int > PIXEL_MAPPING_RECOMMENDED_CADENCE_DAYS
        and not manual_pixel_mapping_requested
    ):
        errors.append(
            f"{GA_ERR_AUTO_PIXEL_MAPPING_CADENCE_OR_SHUTTER}: [Auto Pixel Mapping]=[Off] exceeds 3-day "
            f"manual cadence ({days_int} days > {PIXEL_MAPPING_RECOMMENDED_CADENCE_DAYS} days)"
        )

    soc_val = float(battery_soc_pct)
    cnflasha_ro_ok = (
        bool(cnflasha_userspace_o_rdonly_enforced)
        and int(cnflasha_calibration_mutation_bytes) == 0
        and not bool(unguarded_calibration_attempt)
    )
    if not cnflasha_ro_ok:
        errors.append(
            f"{GA_ERR_CNFLASHA_USERSPACE_RO_FIREWALL_VIOLATION}: userspace cnflasha O_RDONLY firewall violated "
            f"(ro={cnflasha_userspace_o_rdonly_enforced}, mutation_bytes={cnflasha_calibration_mutation_bytes}, "
            f"unguarded={unguarded_calibration_attempt})"
        )

    low_batt = (soc_val < PIXEL_MAPPING_MIN_BATTERY_SOC_PCT) or bool(low_battery_warning_active)
    pixel_map_allowed = (not low_batt) and (not bool(tier0_dump_active)) and cnflasha_ro_ok

    if manual_pixel_mapping_requested:
        if low_batt:
            errors.append(
                f"{GA_ERR_PIXEL_MAPPING_LOW_BATTERY_BLOCKED}: manual [Pixel Mapping] blocked under low battery "
                f"(soc={soc_val:.1f}% < {PIXEL_MAPPING_MIN_BATTERY_SOC_PCT:.1f}% or warning={low_battery_warning_active})"
            )
        if tier0_dump_active:
            errors.append(
                f"{GA_ERR_PIXEL_MAPPING_DURING_ACTIVE_TIER0_DUMP}: manual [Pixel Mapping] blocked during active "
                "Tier-0 cold-backup dump"
            )
        if not (
            bool(operator_controls_locked_during_calibration)
            and bool(auto_restart_after_pixel_mapping)
            and bool(stageb_volatile_ram_unmounted_on_reboot)
        ):
            errors.append(
                f"{GA_ERR_PIXEL_MAPPING_MANDATORY_RESTART_OR_CONTROL_LOCK}: manual [Pixel Mapping] locks all camera "
                "controls during calibration and forces automatic camera restart cleanly unmounting Stage-B /tmp RAM (H0==H2)"
            )

    # 2. [NTSC/PAL Selector] Frame-Rate / DF-NDF Exclusivity & Reset Persistence
    sys_norm = _norm_token(ntsc_pal_selector)
    reg_norm = _norm_token(regional_default_system)
    tc_fmt_norm = _norm_token(tc_format)
    fps_val = round(float(rec_frame_rate_fps), 2)

    if sys_norm not in VALID_VIDEO_SYSTEMS or reg_norm not in VALID_VIDEO_SYSTEMS:
        errors.append(
            f"{GA_ERR_NTSCPAL_FRAMERATE_OR_TC_FORMAT_CONFLICT}: invalid [NTSC/PAL Selector]={ntsc_pal_selector!r} "
            f"or regional_default={regional_default_system!r}"
        )
    elif sys_norm == "NTSC":
        if fps_val not in NTSC_ALLOWED_MOVIE_FPS or tc_fmt_norm not in NTSC_ALLOWED_TC_FORMATS:
            errors.append(
                f"{GA_ERR_NTSCPAL_FRAMERATE_OR_TC_FORMAT_CONFLICT}: NTSC requires fps in {NTSC_ALLOWED_MOVIE_FPS} "
                f"and [TC Format] in DF/NDF; got fps={fps_val}, tc_format={tc_format!r}"
            )
    else:  # PAL
        effective_pal_tc = "UNAVAILABLE" if tc_fmt_norm in PAL_ALLOWED_TC_FORMATS else tc_fmt_norm
        if fps_val not in PAL_ALLOWED_MOVIE_FPS or effective_pal_tc != "UNAVAILABLE":
            errors.append(
                f"{GA_ERR_NTSCPAL_FRAMERATE_OR_TC_FORMAT_CONFLICT}: PAL enables only 25p/50p/100p (23.98p unavailable) "
                f"and disables [TC Format] DF/NDF toggle; got fps={fps_val}, tc_format={tc_format!r}"
            )
        tc_fmt_norm = effective_pal_tc

    banner = (
        f"Running on {sys_norm}."
        if (sys_norm in VALID_VIDEO_SYSTEMS and sys_norm != reg_norm)
        else ""
    )

    eff_media_db = _norm_token(media_db_system) if media_db_system is not None else sys_norm
    if eff_media_db != sys_norm:
        errors.append(
            f"{GA_ERR_NTSCPAL_RESET_PERSISTENCE_OR_MEDIA_DB}: dual-slot media DB ({eff_media_db}) conflicts with "
            f"[NTSC/PAL Selector]={sys_norm} and triggers card re-initialization prompt"
        )

    reset_norm = _norm_token(reset_action)
    if reset_norm not in VALID_RESET_ACTIONS:
        errors.append(
            f"{GA_ERR_NTSCPAL_RESET_PERSISTENCE_OR_MEDIA_DB}: invalid reset_action={reset_action!r}"
        )
        eff_after_reset = sys_norm
    elif reset_norm == "INITIALIZE":
        eff_after_reset = reg_norm
    else:
        # Both NONE and CAMERA_SETTINGS_RESET preserve [NTSC/PAL Selector]
        eff_after_reset = sys_norm

    if claimed_ntsc_pal_after_reset is not None:
        claimed_norm = _norm_token(claimed_ntsc_pal_after_reset)
        if claimed_norm != eff_after_reset:
            errors.append(
                f"{GA_ERR_NTSCPAL_RESET_PERSISTENCE_OR_MEDIA_DB}: [NTSC/PAL Selector] survives [Camera Settings Reset] "
                f"and resets only on [Initialize] (action={reset_norm}, expected={eff_after_reset}, claimed={claimed_norm})"
            )

    # 3. Ver. 7.02 [Gamma Display Assist] vs [Display LUT] Split
    log_norm = _norm_token(log_shooting_mode)
    gda_norm = _norm_token(gamma_display_assist)
    gda_type_norm = _norm_gamma_assist_type(gamma_disp_assist_type)
    dlut_norm = _norm_token(display_lut)

    if (
        log_norm not in VALID_P227_LOG_SHOOTING_MODES
        or gda_norm not in ("ON", "OFF")
        or gda_type_norm not in VALID_GAMMA_ASSIST_TYPES
        or dlut_norm not in ("ON", "OFF")
    ):
        errors.append(
            f"{GA_ERR_GAMMA_ASSIST_VS_DISPLAY_LUT_SPLIT}: invalid Ver. 7.02 Log/GammaAssist/DisplayLUT enum "
            f"(log={log_shooting_mode!r}, gda={gamma_display_assist!r}, type={gamma_disp_assist_type!r}, dlut={display_lut!r}; "
            "S-Log2 assist types are unsupported on ILME-FX3)"
        )

    log_active = log_norm in ACTIVE_LOG_SHOOTING_MODES
    if log_active and gda_norm == "ON":
        errors.append(
            f"{GA_ERR_GAMMA_ASSIST_VS_DISPLAY_LUT_SPLIT}: [Gamma Display Assist] is hard-locked to [Off] when "
            f"[Log Shooting]={log_norm}; use [Display LUT] instead"
        )
    effective_gda = "OFF" if log_active else gda_norm

    if expect_gamma_assist_on_external_hdmi:
        errors.append(
            f"{GA_ERR_GAMMA_ASSIST_EXTERNAL_HDMI_FORBIDDEN}: [Gamma Display Assist] applies exclusively to the "
            "built-in camera LCD and is never applied to external HDMI monitors/TVs"
        )

    return CheckGroupAPixelMapNtscPalGammaResult(
        check_group_id=CHECK_GROUP_A_ID,
        passed=(len(errors) == 0),
        body_model_id_hex=f"0x{int(body_model_id) & 0xFFFFFFFF:08x}",
        body_fw=fw_clean,
        auto_pixel_mapping=auto_pm_norm,
        days_since_manual_pixel_mapping=days_int,
        manual_pixel_mapping_requested=bool(manual_pixel_mapping_requested),
        pixel_mapping_allowed=pixel_map_allowed,
        battery_soc_pct=soc_val,
        tier0_dump_active=bool(tier0_dump_active),
        cnflasha_userspace_o_rdonly_enforced=cnflasha_ro_ok,
        cnflasha_calibration_mutation_bytes=int(cnflasha_calibration_mutation_bytes),
        mandatory_auto_restart_modeled=bool(auto_restart_after_pixel_mapping),
        stageb_volatile_ram_unmounted_on_reboot=bool(stageb_volatile_ram_unmounted_on_reboot),
        ntsc_pal_selector=sys_norm,
        regional_default_system=reg_norm,
        startup_notification_banner=banner,
        reset_action=reset_norm,
        effective_ntsc_pal_after_reset=eff_after_reset,
        survives_camera_settings_reset=True,
        cleared_only_by_initialize=True,
        rec_frame_rate_fps=fps_val,
        tc_format=tc_fmt_norm,
        log_shooting_mode=log_norm,
        gamma_display_assist=gda_norm,
        effective_gamma_display_assist=effective_gda,
        gamma_disp_assist_type=gda_type_norm,
        display_lut=dlut_norm,
        gamma_assist_applied_to_hdmi=False,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Check Group B: File Settings 37-Char/SDHC + ShotMark MP4/XAVC + TC Regen Slot-1/EXT-LK + Coupled REC Lamp
# ---------------------------------------------------------------------------


def evaluate_check_group_b_filesettings_tcregen_and_reclamp(
    *,
    file_name_format: str = "CAM_ID_PLUS_REEL",
    slot2_file_name_format: Optional[str] = None,
    file_number_mode: str = "SERIES",
    require_series_counter: bool = True,
    title_name: str = "FX3_BENCH_P227",
    cam_id: str = "A",
    reel_number: int = 1,
    expect_retroactive_clip_rename: bool = False,
    slot1_media_type: str = "CFEXPRESS_A",
    slot2_media_type: str = "CFEXPRESS_A",
    custom_folder_name_requested: bool = False,
    clip_container_format: str = "XAVC_S_I_4K",
    shot_mark1_count: int = 1,
    shot_mark2_count: int = 1,
    shot_mark_xml_sidecar_enabled: bool = True,
    image_jump_setting: str = "SHOT_MARK_ONLY",
    shoot_mode: str = "MOVIE",
    simult_recording_enabled: bool = True,
    tc_make: str = "PRESET",
    tc_run: str = "FREE_RUN",
    tc_regenerate_reference_slot: int = 1,
    expect_free_run_under_regenerate: bool = False,
    external_tc_jam_was_active: bool = False,
    vmc_bncm1_ext_lk_required: bool = False,
    hdmi_tc_output_enabled_in_sq: bool = False,
    rec_lamp_mode: str = REC_LAMP_ONLY_FRONT_OFF,
    xlr_h1_attached: bool = True,
    expect_uncoupled_rear_vs_top_tally: bool = False,
    claimed_xlr_h1_rec_lamp_lit: Optional[bool] = None,
    silent_mode_enabled: bool = False,
    audio_signals_mode: str = "ON",
) -> CheckGroupBFileSettingsTcRegenRecLampResult:
    errors: List[str] = []
    warnings: List[str] = []

    fmt_norm = _norm_token(file_name_format).replace("REEL#", "REEL").replace("_+_", "_PLUS_")
    s2_fmt_norm = (
        _norm_token(slot2_file_name_format).replace("REEL#", "REEL").replace("_+_", "_PLUS_")
        if slot2_file_name_format is not None
        else fmt_norm
    )
    num_norm = _norm_token(file_number_mode)
    title_str = str(title_name)
    cam_str = str(cam_id).strip().upper()
    reel_int = int(reel_number)

    if fmt_norm not in VALID_FILE_NAME_FORMATS or s2_fmt_norm != fmt_norm:
        errors.append(
            f"{GB_ERR_FILE_SETTINGS_TITLE_OR_NUMBER_INVALID}: invalid or heterogeneous Slot1/Slot2 "
            f"[File Name Format] ({file_name_format!r} vs {slot2_file_name_format!r})"
        )
    if num_norm not in VALID_FILE_NUMBER_MODES or (require_series_counter and num_norm != "SERIES"):
        errors.append(
            f"{GB_ERR_FILE_SETTINGS_TITLE_OR_NUMBER_INVALID}: [File Number] must be valid ({num_norm!r}) "
            f"and SERIES when non-colliding reel continuity is required"
        )
    if (
        len(title_str) > TITLE_MAX_ASCII_CHARS
        or not TITLE_ALLOWED_RE.match(title_str)
        or expect_retroactive_clip_rename
    ):
        errors.append(
            f"{GB_ERR_FILE_SETTINGS_TITLE_OR_NUMBER_INVALID}: [Title Name Settings] requires 1..37 allowed "
            f"ASCII chars (forward-only, no retroactive rename); got len={len(title_str)} {title_str!r}"
        )
    if not CAM_ID_ALLOWED_RE.match(cam_str) or not (1 <= reel_int <= 999):
        errors.append(
            f"{GB_ERR_FILE_SETTINGS_TITLE_OR_NUMBER_INVALID}: invalid Cam ID ({cam_id!r}) or Reel# ({reel_number})"
        )

    s1_media = _norm_token(slot1_media_type)
    s2_media = _norm_token(slot2_media_type)
    if s1_media not in VALID_P227_SLOT_MEDIA_TYPES or s2_media not in VALID_P227_SLOT_MEDIA_TYPES:
        errors.append(
            f"{GB_ERR_FILE_SETTINGS_TITLE_OR_NUMBER_INVALID}: invalid slot media ({slot1_media_type!r}, {slot2_media_type!r})"
        )

    sdhc_present = "SDHC" in (s1_media, s2_media)
    sdhc_ok = True
    if sdhc_present and (fmt_norm != "STANDARD" or custom_folder_name_requested):
        sdhc_ok = False
        errors.append(
            f"{GB_ERR_SDHC_FILE_SETTINGS_UNAVAILABLE}: [File Settings] custom naming/folder options are "
            "unavailable on SDHC (FAT32 <=32GB) media; [File Name Format] is locked to [Standard]"
        )

    # Shot Mark1/2 MP4/XAVC-only rule
    shoot_norm = _norm_token(shoot_mode).replace("S&Q", "S_AND_Q")
    container_norm = _norm_token(clip_container_format)
    jump_norm = _norm_token(image_jump_setting)
    sm1 = int(shot_mark1_count)
    sm2 = int(shot_mark2_count)
    has_marks = (sm1 > 0) or (sm2 > 0)

    shot_mark_ok = (
        sm1 >= 0
        and sm2 >= 0
        and jump_norm in VALID_IMAGE_JUMP_MODES
        and (
            not has_marks
            or (
                container_norm in MP4_XAVC_SHOTMARK_FORMATS
                and shoot_norm in ("MOVIE", "S_AND_Q")
                and bool(shot_mark_xml_sidecar_enabled)
            )
        )
    )
    if not shot_mark_ok:
        errors.append(
            f"{GB_ERR_SHOT_MARK_MP4_XAVC_ONLY_VIOLATION}: Shot Mark1/2 is supported exclusively on MP4/XAVC "
            f"movie clips with M4ROOT/CLIP/*M01.XML sidecars (got container={clip_container_format!r}, "
            f"shoot_mode={shoot_mode!r}, xml={shot_mark_xml_sidecar_enabled}, jump={image_jump_setting!r})"
        )

    # [Time Code Make] = [Regenerate] Slot-1 tracking & EXT-LK release warning
    make_norm = _norm_token(tc_make)
    run_norm = _norm_token(tc_run)
    if (
        shoot_norm not in VALID_SHOOT_MODES
        or make_norm not in VALID_TC_MAKE_MODES
        or run_norm not in VALID_TC_RUN_MODES
    ):
        errors.append(
            f"{GB_ERR_TC_REGENERATE_SLOT1_OR_RECRUN_VIOLATION}: invalid shoot/TC mode "
            f"({shoot_mode!r}/{tc_make!r}/{tc_run!r})"
        )

    regen_slot1_ok = True
    effective_run = "REC_RUN" if make_norm == "REGENERATE" else run_norm
    if make_norm == "REGENERATE":
        if int(tc_regenerate_reference_slot) != 1 or expect_free_run_under_regenerate:
            regen_slot1_ok = False
            errors.append(
                f"{GB_ERR_TC_REGENERATE_SLOT1_OR_RECRUN_VIOLATION}: [Time Code Make]=[Regenerate] tracks "
                "Slot-1 exclusively (especially under Simult. Recording) and forces [Rec Run] advancement"
            )

    ext_lk_prereq_met = (
        shoot_norm == "MOVIE" and make_norm == "PRESET" and run_norm == "FREE_RUN"
    )
    ext_lk_released = bool(external_tc_jam_was_active and not ext_lk_prereq_met)
    if ext_lk_released:
        warnings.append(WARN_EXT_LK_RELEASED_BY_TC_CHANGE)

    ext_lk_preserved = ext_lk_prereq_met if (vmc_bncm1_ext_lk_required or external_tc_jam_was_active) else True
    if shoot_norm == "S_AND_Q" and hdmi_tc_output_enabled_in_sq:
        errors.append(
            f"{GB_ERR_EXT_LK_RELEASE_OR_SQ_TC_VIOLATION}: [Time Code Run] and HDMI [Time Code Output] "
            "are disabled in S&Q mode"
        )
    if vmc_bncm1_ext_lk_required and not ext_lk_prereq_met:
        errors.append(
            f"{GB_ERR_EXT_LK_RELEASE_OR_SQ_TC_VIOLATION}: external VMC-BNCM1 EXT-LK requires Movie + Preset + "
            f"Free Run; switching to {shoot_norm}+{make_norm}+{run_norm} immediately releases EXT-LK"
        )

    # [REC Lamp] [Off] silencing both body tally lamps & XLR-H1 handle REC lamp
    lamp_norm = _norm_token(rec_lamp_mode)
    if lamp_norm == "OFF":
        lamp_norm = REC_LAMP_ALL_OFF

    if lamp_norm not in VALID_REC_LAMP_MODES:
        errors.append(
            f"{GB_ERR_REC_LAMP_COUPLED_BODY_AND_XLR_H1_VIOLATION}: invalid [REC Lamp]={rec_lamp_mode!r}; "
            "ILME-FX3 supports only All On, Only Front Off, and Off (All Off)"
        )
        front_lit = rear_lit = top_lit = handle_lit = False
    elif lamp_norm == REC_LAMP_ALL_ON:
        front_lit, rear_lit, top_lit = True, True, True
        handle_lit = bool(xlr_h1_attached)
    elif lamp_norm == REC_LAMP_ONLY_FRONT_OFF:
        front_lit, rear_lit, top_lit = False, True, True
        handle_lit = bool(xlr_h1_attached)
    else:  # ALL_OFF / OFF
        front_lit, rear_lit, top_lit = False, False, False
        handle_lit = False

    coupled_ok = (rear_lit == top_lit) and (not expect_uncoupled_rear_vs_top_tally)
    if claimed_xlr_h1_rec_lamp_lit is not None and bool(claimed_xlr_h1_rec_lamp_lit) != handle_lit:
        coupled_ok = False
    if not coupled_ok:
        errors.append(
            f"{GB_ERR_REC_LAMP_COUPLED_BODY_AND_XLR_H1_VIOLATION}: [REC Lamp]=[Off] silences all body tally "
            "lamps AND the XLR-H1 handle REC lamp, while Rear and Top REC button lamps remain hardware-coupled"
        )

    audio_norm = _norm_token(audio_signals_mode)
    if audio_norm not in ("ON", "OFF_SHUTTER_ONLY", "OFF") or (
        silent_mode_enabled and audio_norm != "OFF"
    ):
        errors.append(
            f"{GB_ERR_SILENT_MODE_AUDIO_SIGNALS_LOCK}: [Silent Mode]=[On] hard-locks [Audio signals] to [Off] "
            f"(got silent={silent_mode_enabled}, audio_signals={audio_signals_mode!r})"
        )

    return CheckGroupBFileSettingsTcRegenRecLampResult(
        check_group_id=CHECK_GROUP_B_ID,
        passed=(len(errors) == 0),
        file_name_format=fmt_norm,
        file_number_mode=num_norm,
        title_name=title_str,
        title_ascii_length=len(title_str),
        cam_id=cam_str,
        reel_number=reel_int,
        slot1_media_type=s1_media,
        slot2_media_type=s2_media,
        sdhc_present=sdhc_present,
        sdhc_file_settings_unavailable_respected=sdhc_ok,
        clip_container_format=container_norm,
        shot_mark1_count=sm1,
        shot_mark2_count=sm2,
        shot_mark_mp4_xavc_only_verified=shot_mark_ok,
        image_jump_setting=jump_norm,
        shoot_mode=shoot_norm,
        simult_recording_enabled=bool(simult_recording_enabled),
        tc_make=make_norm,
        requested_tc_run=run_norm,
        effective_tc_run=effective_run,
        tc_regenerate_slot1_tracked=regen_slot1_ok,
        vmc_bncm1_ext_lk_required=bool(vmc_bncm1_ext_lk_required),
        vmc_bncm1_ext_lk_preserved=ext_lk_preserved,
        ext_lk_released=ext_lk_released,
        rec_lamp_mode=lamp_norm,
        xlr_h1_attached=bool(xlr_h1_attached),
        front_tally_lit=front_lit,
        rear_tally_lit=rear_lit,
        top_rec_button_lit=top_lit,
        xlr_h1_rec_lamp_lit=handle_lit,
        body_and_xlr_h1_reclamp_coupled_ok=coupled_ok,
        silent_mode_enabled=bool(silent_mode_enabled),
        audio_signals_mode=audio_norm,
        warnings=tuple(warnings),
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Check Group C: Power Save 9-Condition Bypass + Auto Power OFF Temp. Tripod + SteadyShot/CIZ + Tier-0 Gate
# ---------------------------------------------------------------------------


def build_simulated_phase227_tier0_receipts(
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
            f"PHASE227_TIER0:{body_fw}:{item.item_id}:{item.size_bytes}:{emmc_cid.lower()}".encode(
                "ascii"
            )
        ).hexdigest()
        total_bytes += item.size_bytes
    manifest_seed = hashlib.sha256(
        f"PHASE227_MANIFEST:{body_serial}:{body_fw}:{emmc_cid.lower()}".encode("ascii")
    ).hexdigest()
    rcpt = build_sd_backup_receipt_bytes(
        manifest_sha256=manifest_seed,
        item_hashes=item_hashes,
        total_dumped_bytes=total_bytes,
    )
    baselines = build_default_h0_baselines(body_serial=body_serial, emmc_cid=emmc_cid)
    return rcpt, bytes(rcpt), baselines


def evaluate_check_group_c_powersave_autotemp_steadyshot_ciz_and_tier0(
    *,
    power_save_menu_label: str = POWER_SAVE_MENU_EXACT_LABEL,
    power_save_start_time: str = "OFF",
    power_source: str = "INTERNAL_NP_FZ100",
    usb_power_supply_active: Optional[bool] = None,
    slideshow_playback_active: bool = False,
    ftp_transfer_active: bool = False,
    movie_recording_active: bool = False,
    computer_connection_active: bool = False,
    hdmi_tv_connection_active: bool = False,
    ir_remote_ctrl_on: bool = False,
    bluetooth_rmt_ctrl_on: bool = False,
    streaming_or_cloud_active: bool = False,
    claimed_power_save_bypassed: Optional[bool] = None,
    p3_75mib_cold_dump_active: bool = True,
    auto_power_off_temp: str = "HIGH",
    tripod_mounted: bool = True,
    handheld_operation_active: bool = False,
    fan_control_mode: str = "AUTO",
    body_temp_c: float = 29.5,
    steadyshot_mode: str = "STANDARD",
    steadyshot_manual_focal_mm: int = 35,
    rec_frame_rate_fps: float = 23.98,
    sq_mode_enabled: bool = False,
    sq_frame_rate_fps: float = 60.0,
    hdmi_raw_output: bool = False,
    zoom_mode: str = "OPTICAL_ONLY",
    zoom_scale: float = 1.0,
    video_resolution_class: str = "4K",
    still_file_format: str = "NONE",
    ciz_focus_area_center_locked: bool = True,
    ciz_metering_mode: str = "MULTI",
    ciz_face_eye_priority_disabled: bool = True,
    ciz_realtime_tracking_disabled: bool = True,
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
) -> Tuple[CheckGroupCPowerSaveAutoTempSteadyShotCizResult, Tuple[str, ...]]:
    errors: List[str] = []
    tier0_errors: List[str] = []

    # 1. [Power Save Start Time] 9-Condition Bypass & NP-FZ100 75 MiB p3 Cold-Dump Interlock
    ps_time_norm = _norm_power_save_time(power_save_start_time)
    pwr_src_norm = _norm_token(power_source)
    if (
        str(power_save_menu_label).strip() != POWER_SAVE_MENU_EXACT_LABEL
        or ps_time_norm not in VALID_POWER_SAVE_START_TIMES
        or pwr_src_norm not in VALID_P227_POWER_SOURCES
    ):
        errors.append(
            f"{GC_ERR_POWER_SAVE_MENU_OR_BYPASS_INVALID}: invalid menu label ({power_save_menu_label!r}), "
            f"[Power Save Start Time]={power_save_start_time!r}, or power_source={power_source!r}"
        )

    eff_usb_pwr = (
        bool(usb_power_supply_active)
        if usb_power_supply_active is not None
        else (pwr_src_norm in ("USB_PD_BODY", "DC_C1_COUPLER"))
    )
    cond_pairs = (
        ("USB_POWER_SUPPLY", eff_usb_pwr),
        ("SLIDESHOW_PLAYBACK", bool(slideshow_playback_active)),
        ("FTP_TRANSFER", bool(ftp_transfer_active)),
        ("MOVIE_RECORDING", bool(movie_recording_active)),
        ("COMPUTER_CONNECTION", bool(computer_connection_active)),
        ("TV_HDMI_CONNECTION", bool(hdmi_tv_connection_active or hdmi_raw_output)),
        ("IR_REMOTE_CTRL_ON", bool(ir_remote_ctrl_on)),
        ("BLUETOOTH_RMT_CTRL_ON", bool(bluetooth_rmt_ctrl_on)),
        ("STREAMING_OR_CLOUD_UPLOAD", bool(streaming_or_cloud_active)),
    )
    active_bypasses = tuple(name for name, active in cond_pairs if active)
    bypassed = len(active_bypasses) > 0

    if claimed_power_save_bypassed is not None and bool(claimed_power_save_bypassed) != bypassed:
        errors.append(
            f"{GC_ERR_POWER_SAVE_MENU_OR_BYPASS_INVALID}: 9-condition [Power Save Start Time] bypass mismatch "
            f"(actual={bypassed} via {active_bypasses}, claimed={claimed_power_save_bypassed})"
        )

    sleep_safe = True
    if (
        pwr_src_norm == "INTERNAL_NP_FZ100"
        and not bypassed
        and bool(p3_75mib_cold_dump_active)
        and ps_time_norm not in SAFE_P3_75MIB_DUMP_POWER_SAVE_TIMES
    ):
        sleep_safe = False
        errors.append(
            f"{GC_ERR_NPFZ100_P3_75MIB_DUMP_SLEEP_HAZARD}: all 9 [Power Save Start Time] bypass conditions "
            f"are inactive on internal NP-FZ100 during {P3_75MIB_COLD_DUMP_MIB} MiB p3 cold dump; "
            f"must set [Power Save Start Time] to Off or 30 Min (got {ps_time_norm})"
        )

    # 2. [Auto Power OFF Temp.]=[High] Tripod Requirement & Fan/Thermal Interlock
    autotemp_norm = _norm_token(auto_power_off_temp)
    fan_norm = _norm_token(fan_control_mode)
    temp_val = float(body_temp_c)

    if autotemp_norm not in ("STANDARD", "HIGH"):
        errors.append(
            f"{GC_ERR_FAN_OR_THERMAL_SAFETY_INTERLOCK}: invalid [Auto Power OFF Temp.]={auto_power_off_temp!r}"
        )
    if autotemp_norm == "HIGH" and (not bool(tripod_mounted) or bool(handheld_operation_active)):
        errors.append(
            f"{GC_ERR_AUTO_POWER_OFF_TEMP_HIGH_REQUIRES_TRIPOD}: [Auto Power OFF Temp.]=[High] mandates "
            "tripod mounting and prohibits handheld operation (low-temperature burn hazard)"
        )
    if (
        fan_norm not in VALID_P227_FAN_MODES
        or (fan_norm == "ALWAYS_OFF" and (autotemp_norm == "HIGH" or bool(p3_75mib_cold_dump_active)))
        or not (0.0 <= temp_val < MAX_BODY_START_TEMP_C)
    ):
        errors.append(
            f"{GC_ERR_FAN_OR_THERMAL_SAFETY_INTERLOCK}: unsafe [Fan Control]={fan_control_mode!r} or "
            f"body_temp_c={temp_val:.1f}C under [Auto Power OFF Temp.]={autotemp_norm} / p3 cold dump"
        )

    # 3. [SteadyShot] = [Active] 3 Cutoffs (119.88p/100p, S&Q >=120/100fps, HDMI RAW Output)
    ss_norm = _norm_token(steadyshot_mode)
    focal_mm = int(steadyshot_manual_focal_mm)
    rec_fps = float(rec_frame_rate_fps)
    sq_fps = float(sq_frame_rate_fps)

    ss_cutoffs: List[str] = []
    if rec_fps >= STEADYSHOT_HFR_CUTOFF_FPS:
        ss_cutoffs.append("NORMAL_MOVIE_100P_119_88P_OR_HIGHER")
    if sq_mode_enabled and sq_fps >= STEADYSHOT_HFR_CUTOFF_FPS:
        ss_cutoffs.append("S_AND_Q_100FPS_120FPS_OR_HIGHER")
    if hdmi_raw_output:
        ss_cutoffs.append("HDMI_RAW_OUTPUT_ACTIVE")

    ss_ok = True
    if ss_norm not in VALID_STEADYSHOT_MOVIE_MODES or not (
        STEADYSHOT_MANUAL_FOCAL_MIN_MM <= focal_mm <= STEADYSHOT_MANUAL_FOCAL_MAX_MM
    ):
        ss_ok = False
        errors.append(
            f"{GC_ERR_STEADYSHOT_ACTIVE_CUTOFF_VIOLATION}: invalid [SteadyShot]={steadyshot_mode!r} "
            f"or manual focal length {focal_mm}mm (allowed 8..1000mm)"
        )
    elif ss_norm == "ACTIVE" and len(ss_cutoffs) > 0:
        ss_ok = False
        errors.append(
            f"{GC_ERR_STEADYSHOT_ACTIVE_CUTOFF_VIOLATION}: [SteadyShot]=[Active] is unavailable under "
            f"{','.join(ss_cutoffs)}"
        )
    ss_crop = STEADYSHOT_ACTIVE_CROP_FACTOR if ss_norm == "ACTIVE" else 1.0

    # 4. Clear Image Zoom (CIZ) / Digital Zoom RAW/HFR Cutoffs & 4 AF/Metering Locks
    zm_norm = _norm_token(zoom_mode)
    z_scale = float(zoom_scale)
    res_norm = _norm_token(video_resolution_class)
    still_norm = _norm_token(still_file_format)
    met_norm = _norm_token(ciz_metering_mode)

    if zm_norm not in VALID_ZOOM_MODES or res_norm not in ("4K", "HD"):
        errors.append(
            f"{GC_ERR_CIZ_RAW_HFR_OR_SCALE_FORBIDDEN}: invalid zoom_mode={zoom_mode!r} or resolution={video_resolution_class!r}"
        )

    non_optical_zoom = (zm_norm != "OPTICAL_ONLY") or (z_scale > 1.0)
    if not non_optical_zoom and z_scale != 1.0:
        errors.append(
            f"{GC_ERR_CIZ_RAW_HFR_OR_SCALE_FORBIDDEN}: OPTICAL_ONLY requires zoom_scale==1.0, got {z_scale}"
        )

    ciz_locks_ok = True
    if non_optical_zoom:
        max_ciz = CIZ_MAX_SCALE_4K if res_norm == "4K" else CIZ_MAX_SCALE_HD
        max_allowed = max_ciz if zm_norm == "CLEAR_IMAGE_ZOOM" else (
            DIGITAL_ZOOM_MAX_SCALE if zm_norm == "DIGITAL_ZOOM" else 1.0
        )
        raw_or_hfr_blocked = (
            still_norm in ("RAW", "ARW", "RAW_AND_JPEG", "RAW_AND_HEIF")
            or rec_fps >= STEADYSHOT_HFR_CUTOFF_FPS
            or (sq_mode_enabled and sq_fps >= STEADYSHOT_HFR_CUTOFF_FPS)
        )
        if raw_or_hfr_blocked or not (1.0 < z_scale <= max_allowed):
            errors.append(
                f"{GC_ERR_CIZ_RAW_HFR_OR_SCALE_FORBIDDEN}: {zm_norm} ({z_scale}x, {res_norm}) unavailable "
                f"under RAW/100p/119.88p/S&Q>=100fps or exceeds {max_allowed}x ceiling"
            )
        if not (
            bool(ciz_focus_area_center_locked)
            and met_norm == "MULTI"
            and bool(ciz_face_eye_priority_disabled)
            and bool(ciz_realtime_tracking_disabled)
        ):
            ciz_locks_ok = False
            errors.append(
                f"{GC_ERR_CIZ_FOUR_AF_METERING_LOCK_VIOLATION}: Clear Image Zoom / Digital Zoom enforces all "
                "4 camera locks (Focus Area center-priority, Metering=[Multi], Face/Eye Priority off, Real-time Tracking off)"
            )

    # 5. 16/16 H0 == H3 Parity & Dual-Media 528 B FX3RCPT1 Tier-0 Receipt Gate
    surface_total = len(SIXTEEN_STORAGE_SURFACES)
    drifted = max(0, min(surface_total, int(simulated_h0_h3_drifted_surfaces)))
    h0_eq_h3 = surface_total - drifted
    if h0_eq_h3 != surface_total:
        errors.append(
            f"{GC_ERR_H0_H3_IMMUTABILITY_DRIFT}: H0 == H3 parity drift ({h0_eq_h3}/{surface_total})"
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
        raw_a, raw_b, sim_h0 = build_simulated_phase227_tier0_receipts(
            body_serial=eff_serial, emmc_cid=eff_cid, body_fw=body_fw
        )
        dev_a = 101 if dev_a is None else dev_a
        dev_b = 202 if dev_b is None else dev_b
        eff_h0_a = eff_h0_a if eff_h0_a is not None else dict(sim_h0)
        eff_h0_b = eff_h0_b if eff_h0_b is not None else dict(sim_h0)

    if receipt_a_path is not None:
        try:
            _, raw_a, st_a = _read_bounded_slice_o_rdonly(Path(receipt_a_path), SD_RECEIPT_BYTES + 64)
            if dev_a is None:
                dev_a = int(st_a)
        except OSError as exc:
            tier0_errors.append(
                f"{GC_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt_a read failed: {exc}"
            )

    if receipt_b_path is not None:
        try:
            _, raw_b, st_b = _read_bounded_slice_o_rdonly(Path(receipt_b_path), SD_RECEIPT_BYTES + 64)
            if dev_b is None:
                dev_b = int(st_b)
        except OSError as exc:
            tier0_errors.append(
                f"{GC_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt_b read failed: {exc}"
            )

    receipt_present = (raw_a is not None) and (raw_b is not None)
    distinct_media = False
    receipt_verified = False

    if not receipt_present:
        tier0_errors.append(
            f"{GC_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: dual-copy 528B FX3RCPT1 Tier-0 "
            "cold-backup receipts not provided (offline fail-closed)"
        )
    else:
        assert raw_a is not None and raw_b is not None
        if len(raw_a) != SD_RECEIPT_BYTES or len(raw_b) != SD_RECEIPT_BYTES or raw_a != raw_b:
            tier0_errors.append(
                f"{GC_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: dual FX3RCPT1 size/byte mismatch"
            )
        else:
            if dev_a is not None and dev_b is not None and int(dev_a) != int(dev_b):
                distinct_media = True
            else:
                tier0_errors.append(
                    f"{GC_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: st_dev_a == st_dev_b ({dev_a} vs {dev_b})"
                )

            ser_norm = (eff_serial or "").strip()
            cid_norm = (eff_cid or "").strip().lower()
            if not BODY_SERIAL_RE.match(ser_norm) or ser_norm.upper() in FORBIDDEN_TRIVIAL_SERIALS:
                tier0_errors.append(
                    f"{GC_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: invalid body_serial={eff_serial!r}"
                )
            if not HEX32_CID_RE.match(cid_norm) or cid_norm in FORBIDDEN_TRIVIAL_CIDS:
                tier0_errors.append(
                    f"{GC_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: invalid emmc_cid={eff_cid!r}"
                )
            if int(body_model_id) != TARGET_MODEL_ID_INT or str(body_fw).strip() != TARGET_BODY_FW:
                tier0_errors.append(
                    f"{GC_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt target mismatch"
                )

            try:
                parsed_a = parse_sd_backup_receipt_bytes(raw_a)
                parsed_b = parse_sd_backup_receipt_bytes(raw_b)
                if not parsed_a.valid or not parsed_b.valid:
                    tier0_errors.append(
                        f"{GC_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: FX3RCPT1 CRC32/header invalid"
                    )
            except Exception as exc:
                tier0_errors.append(
                    f"{GC_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: FX3RCPT1 parse error: {exc}"
                )

            if eff_h0_a is None or eff_h0_b is None:
                tier0_errors.append(
                    f"{GC_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: missing H0 baseline digests"
                )
            else:
                for req_k in REQUIRED_H0_BASELINE_KEYS:
                    va = eff_h0_a.get(req_k, "")
                    vb = eff_h0_b.get(req_k, "")
                    if _is_trivial_hex64(va) or va.lower() != vb.lower():
                        tier0_errors.append(
                            f"{GC_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: invalid/mismatched H0[{req_k}]"
                        )

            if len(tier0_errors) == 0:
                receipt_verified = True

    return (
        CheckGroupCPowerSaveAutoTempSteadyShotCizResult(
            check_group_id=CHECK_GROUP_C_ID,
            passed=(len(errors) == 0),
            power_save_menu_label=str(power_save_menu_label).strip(),
            power_save_start_time=ps_time_norm,
            power_source=pwr_src_norm,
            active_bypass_conditions=active_bypasses,
            power_save_bypassed=bypassed,
            p3_75mib_cold_dump_active=bool(p3_75mib_cold_dump_active),
            np_fz100_p3_dump_sleep_safe=sleep_safe,
            auto_power_off_temp=autotemp_norm,
            tripod_mounted=bool(tripod_mounted),
            handheld_operation_active=bool(handheld_operation_active),
            fan_control_mode=fan_norm,
            body_temp_c=temp_val,
            steadyshot_mode=ss_norm,
            steadyshot_crop_factor=ss_crop,
            steadyshot_manual_focal_mm=focal_mm,
            steadyshot_active_cutoff_reasons=tuple(ss_cutoffs),
            steadyshot_cutoff_respected=ss_ok,
            zoom_mode=zm_norm,
            zoom_scale=z_scale,
            video_resolution_class=res_norm,
            still_file_format=still_norm,
            ciz_four_locks=CIZ_FOUR_AF_METERING_LOCKS,
            ciz_four_locks_satisfied=ciz_locks_ok,
            h0_h3_surface_count=surface_total,
            h0_equals_h3_count=h0_eq_h3,
            tier0_receipt_present=receipt_present,
            tier0_receipt_verified=receipt_verified,
            distinct_physical_media_verified=distinct_media,
            errors=tuple(errors),
        ),
        tuple(tier0_errors),
    )


# ---------------------------------------------------------------------------
# Top-Level Pre-Shoot Readiness Orchestrator & Tamper-Evident Verifier
# ---------------------------------------------------------------------------


def evaluate_realhw_pixelmap_ntscpal_powersave_and_autotemp_readiness(
    *,
    simulate_bench_dry_run: bool = False,
    simulate_ready_bench: Optional[bool] = None,
    force_clean_room: Optional[bool] = None,
    synthetic_clean_room: Optional[bool] = None,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    # Check Group A
    auto_pixel_mapping: str = "ON",
    days_since_manual_pixel_mapping: int = 0,
    expect_silent_mode_suppresses_auto_pixelmap_shutter: bool = False,
    manual_pixel_mapping_requested: bool = False,
    battery_soc_pct: float = 88.0,
    low_battery_warning_active: bool = False,
    tier0_dump_active: bool = False,
    unguarded_calibration_attempt: bool = False,
    cnflasha_userspace_o_rdonly_enforced: bool = True,
    cnflasha_calibration_mutation_bytes: int = 0,
    operator_controls_locked_during_calibration: bool = True,
    auto_restart_after_pixel_mapping: bool = True,
    stageb_volatile_ram_unmounted_on_reboot: bool = True,
    ntsc_pal_selector: str = "NTSC",
    regional_default_system: str = "NTSC",
    media_db_system: Optional[str] = None,
    rec_frame_rate_fps: float = 23.98,
    tc_format: str = "NDF",
    reset_action: str = "NONE",
    claimed_ntsc_pal_after_reset: Optional[str] = None,
    log_shooting_mode: str = "CINE_EI",
    gamma_display_assist: str = "OFF",
    gamma_disp_assist_type: str = "AUTO",
    display_lut: str = "ON",
    expect_gamma_assist_on_external_hdmi: bool = False,
    # Check Group B
    file_name_format: str = "CAM_ID_PLUS_REEL",
    slot2_file_name_format: Optional[str] = None,
    file_number_mode: str = "SERIES",
    require_series_counter: bool = True,
    title_name: str = "FX3_BENCH_P227",
    cam_id: str = "A",
    reel_number: int = 1,
    expect_retroactive_clip_rename: bool = False,
    slot1_media_type: str = "CFEXPRESS_A",
    slot2_media_type: str = "CFEXPRESS_A",
    custom_folder_name_requested: bool = False,
    clip_container_format: str = "XAVC_S_I_4K",
    shot_mark1_count: int = 1,
    shot_mark2_count: int = 1,
    shot_mark_xml_sidecar_enabled: bool = True,
    image_jump_setting: str = "SHOT_MARK_ONLY",
    shoot_mode: str = "MOVIE",
    simult_recording_enabled: bool = True,
    tc_make: str = "PRESET",
    tc_run: str = "FREE_RUN",
    tc_regenerate_reference_slot: int = 1,
    expect_free_run_under_regenerate: bool = False,
    external_tc_jam_was_active: bool = False,
    vmc_bncm1_ext_lk_required: bool = False,
    hdmi_tc_output_enabled_in_sq: bool = False,
    rec_lamp_mode: str = REC_LAMP_ONLY_FRONT_OFF,
    xlr_h1_attached: bool = True,
    expect_uncoupled_rear_vs_top_tally: bool = False,
    claimed_xlr_h1_rec_lamp_lit: Optional[bool] = None,
    silent_mode_enabled: bool = False,
    audio_signals_mode: str = "ON",
    # Check Group C & Tier-0 Gate
    power_save_menu_label: str = POWER_SAVE_MENU_EXACT_LABEL,
    power_save_start_time: str = "OFF",
    power_source: str = "INTERNAL_NP_FZ100",
    usb_power_supply_active: Optional[bool] = None,
    slideshow_playback_active: bool = False,
    ftp_transfer_active: bool = False,
    movie_recording_active: bool = False,
    computer_connection_active: bool = False,
    hdmi_tv_connection_active: bool = False,
    ir_remote_ctrl_on: bool = False,
    bluetooth_rmt_ctrl_on: bool = False,
    streaming_or_cloud_active: bool = False,
    claimed_power_save_bypassed: Optional[bool] = None,
    p3_75mib_cold_dump_active: bool = True,
    auto_power_off_temp: str = "HIGH",
    tripod_mounted: bool = True,
    handheld_operation_active: bool = False,
    fan_control_mode: str = "AUTO",
    body_temp_c: float = 29.5,
    steadyshot_mode: str = "STANDARD",
    steadyshot_manual_focal_mm: int = 35,
    sq_mode_enabled: bool = False,
    sq_frame_rate_fps: float = 60.0,
    hdmi_raw_output: bool = False,
    zoom_mode: str = "OPTICAL_ONLY",
    zoom_scale: float = 1.0,
    video_resolution_class: str = "4K",
    still_file_format: str = "NONE",
    ciz_focus_area_center_locked: bool = True,
    ciz_metering_mode: str = "MULTI",
    ciz_face_eye_priority_disabled: bool = True,
    ciz_realtime_tracking_disabled: bool = True,
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
) -> RealHwPixelMapNtscPalPowerSaveAutoTempReport:
    """Execute Phase 227 read-only physical bench & pre-shoot media readiness verifier (`A..C`)."""
    eff_sim = bool(simulate_bench_dry_run or simulate_ready_bench)

    donor_res = inspect_phase227_donors_bounded(
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        force_clean_room=force_clean_room,
        synthetic_clean_room=synthetic_clean_room,
    )
    ga = evaluate_check_group_a_pixelmap_ntscpal_and_gamma_split(
        body_model_id=body_model_id,
        body_fw=body_fw,
        auto_pixel_mapping=auto_pixel_mapping,
        days_since_manual_pixel_mapping=days_since_manual_pixel_mapping,
        expect_silent_mode_suppresses_auto_pixelmap_shutter=expect_silent_mode_suppresses_auto_pixelmap_shutter,
        manual_pixel_mapping_requested=manual_pixel_mapping_requested,
        battery_soc_pct=battery_soc_pct,
        low_battery_warning_active=low_battery_warning_active,
        tier0_dump_active=tier0_dump_active,
        unguarded_calibration_attempt=unguarded_calibration_attempt,
        cnflasha_userspace_o_rdonly_enforced=cnflasha_userspace_o_rdonly_enforced,
        cnflasha_calibration_mutation_bytes=cnflasha_calibration_mutation_bytes,
        operator_controls_locked_during_calibration=operator_controls_locked_during_calibration,
        auto_restart_after_pixel_mapping=auto_restart_after_pixel_mapping,
        stageb_volatile_ram_unmounted_on_reboot=stageb_volatile_ram_unmounted_on_reboot,
        ntsc_pal_selector=ntsc_pal_selector,
        regional_default_system=regional_default_system,
        media_db_system=media_db_system,
        rec_frame_rate_fps=rec_frame_rate_fps,
        tc_format=tc_format,
        reset_action=reset_action,
        claimed_ntsc_pal_after_reset=claimed_ntsc_pal_after_reset,
        log_shooting_mode=log_shooting_mode,
        gamma_display_assist=gamma_display_assist,
        gamma_disp_assist_type=gamma_disp_assist_type,
        display_lut=display_lut,
        expect_gamma_assist_on_external_hdmi=expect_gamma_assist_on_external_hdmi,
    )
    gb = evaluate_check_group_b_filesettings_tcregen_and_reclamp(
        file_name_format=file_name_format,
        slot2_file_name_format=slot2_file_name_format,
        file_number_mode=file_number_mode,
        require_series_counter=require_series_counter,
        title_name=title_name,
        cam_id=cam_id,
        reel_number=reel_number,
        expect_retroactive_clip_rename=expect_retroactive_clip_rename,
        slot1_media_type=slot1_media_type,
        slot2_media_type=slot2_media_type,
        custom_folder_name_requested=custom_folder_name_requested,
        clip_container_format=clip_container_format,
        shot_mark1_count=shot_mark1_count,
        shot_mark2_count=shot_mark2_count,
        shot_mark_xml_sidecar_enabled=shot_mark_xml_sidecar_enabled,
        image_jump_setting=image_jump_setting,
        shoot_mode=shoot_mode,
        simult_recording_enabled=simult_recording_enabled,
        tc_make=tc_make,
        tc_run=tc_run,
        tc_regenerate_reference_slot=tc_regenerate_reference_slot,
        expect_free_run_under_regenerate=expect_free_run_under_regenerate,
        external_tc_jam_was_active=external_tc_jam_was_active,
        vmc_bncm1_ext_lk_required=vmc_bncm1_ext_lk_required,
        hdmi_tc_output_enabled_in_sq=hdmi_tc_output_enabled_in_sq,
        rec_lamp_mode=rec_lamp_mode,
        xlr_h1_attached=xlr_h1_attached,
        expect_uncoupled_rear_vs_top_tally=expect_uncoupled_rear_vs_top_tally,
        claimed_xlr_h1_rec_lamp_lit=claimed_xlr_h1_rec_lamp_lit,
        silent_mode_enabled=silent_mode_enabled,
        audio_signals_mode=audio_signals_mode,
    )
    gc, tier0_errors = evaluate_check_group_c_powersave_autotemp_steadyshot_ciz_and_tier0(
        power_save_menu_label=power_save_menu_label,
        power_save_start_time=power_save_start_time,
        power_source=power_source,
        usb_power_supply_active=usb_power_supply_active,
        slideshow_playback_active=slideshow_playback_active,
        ftp_transfer_active=ftp_transfer_active,
        movie_recording_active=movie_recording_active,
        computer_connection_active=computer_connection_active,
        hdmi_tv_connection_active=hdmi_tv_connection_active,
        ir_remote_ctrl_on=ir_remote_ctrl_on,
        bluetooth_rmt_ctrl_on=bluetooth_rmt_ctrl_on,
        streaming_or_cloud_active=streaming_or_cloud_active,
        claimed_power_save_bypassed=claimed_power_save_bypassed,
        p3_75mib_cold_dump_active=p3_75mib_cold_dump_active,
        auto_power_off_temp=auto_power_off_temp,
        tripod_mounted=tripod_mounted,
        handheld_operation_active=handheld_operation_active,
        fan_control_mode=fan_control_mode,
        body_temp_c=body_temp_c,
        steadyshot_mode=steadyshot_mode,
        steadyshot_manual_focal_mm=steadyshot_manual_focal_mm,
        rec_frame_rate_fps=rec_frame_rate_fps,
        sq_mode_enabled=sq_mode_enabled,
        sq_frame_rate_fps=sq_frame_rate_fps,
        hdmi_raw_output=hdmi_raw_output,
        zoom_mode=zoom_mode,
        zoom_scale=zoom_scale,
        video_resolution_class=video_resolution_class,
        still_file_format=still_file_format,
        ciz_focus_area_center_locked=ciz_focus_area_center_locked,
        ciz_metering_mode=ciz_metering_mode,
        ciz_face_eye_priority_disabled=ciz_face_eye_priority_disabled,
        ciz_realtime_tracking_disabled=ciz_realtime_tracking_disabled,
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

    groups_passed = sum(1 for item in (ga, gb, gc) if item.passed)
    all_3_passed = donor_res.passed and groups_passed == 3

    all_errors: List[str] = []
    all_errors.extend(donor_res.errors)
    for item in (ga, gb, gc):
        all_errors.extend(item.errors)
    all_errors.extend(tier0_errors)

    remediations: List[str] = []
    if not ga.passed:
        remediations.append(
            "Keep NP-FZ100 >=20% and Tier-0 dump idle before [Pixel Mapping], keep cnflasha O_RDONLY, verify NTSC/PAL reset persistence, and use [Display LUT] when [Log Shooting] is active."
        )
    if not gb.passed:
        remediations.append(
            "Use <=37-char ASCII Title + [Series] on exFAT cards (SDHC locks [Standard]), restrict Shot Mark1/2 to MP4/XAVC, track Slot-1 for TC Regenerate, and verify coupled body + XLR-H1 [REC Lamp]."
        )
    if not gc.passed or not gc.tier0_receipt_verified:
        remediations.append(
            "Set [Power Save Start Time] to Off/30 Min on internal NP-FZ100 during 75 MiB p3 cold dump, mount camera on tripod for [Auto Power OFF Temp.]=[High], respect SteadyShot Active / CIZ locks, and provide dual-device 528B FX3RCPT1 receipts."
        )

    if not all_3_passed:
        verdict = GO_NO_GO_BLOCKED_PIXELMAP_NTSCPAL_POWERSAVE_AUTOTEMP_FAILURE
    elif not gc.tier0_receipt_verified:
        verdict = (
            GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT
            if not gc.tier0_receipt_present
            else GO_NO_GO_BLOCKED_PIXELMAP_NTSCPAL_POWERSAVE_AUTOTEMP_FAILURE
        )
    elif eff_sim:
        verdict = GO_NO_GO_DRY_RUN_SIMULATED_READY
    else:
        verdict = GO_NO_GO_PIXELMAP_NTSCPAL_POWERSAVE_AUTOTEMP_VERIFIED

    provisional = RealHwPixelMapNtscPalPowerSaveAutoTempReport(
        schema=PHASE_227_SCHEMA,
        phase_version=PHASE_227_VERSION,
        verification_mode=donor_res.verification_mode,
        simulate_bench_dry_run=eff_sim,
        go_no_go=verdict,
        hardware_live_attachment_authorized=False,
        persistent_emmc_writes_authorized=False,
        persistent_write_release=False,
        spi_nor_write_authorized=False,
        el3_payload_transmit_authorized=False,
        sd_physical_media_written=False,
        usb_packets_transmitted=0,
        physical_usb_packets_emitted=0,
        raw_firmware_bytes_leaked=PHASE227_RAW_FIRMWARE_BYTES_LEAKED,
        check_group_count=3,
        check_groups_passed=groups_passed,
        all_3_check_groups_passed=all_3_passed,
        tier0_receipt_verified=gc.tier0_receipt_verified,
        h0_h3_surface_count=gc.h0_h3_surface_count,
        h0_equals_h3_count=gc.h0_equals_h3_count,
        donor_inspection=donor_res,
        check_group_a_pixelmap_ntscpal_and_gamma=ga,
        check_group_b_filesettings_tcregen_and_reclamp=gb,
        check_group_c_powersave_autotemp_steadyshot_and_ciz=gc,
        warnings=gb.warnings,
        remediation_actions=tuple(remediations),
        errors=tuple(all_errors),
        report_sha256="",
    )
    digest = _canonical_sha256_dict(provisional.to_dict(), exclude_key="report_sha256")
    return RealHwPixelMapNtscPalPowerSaveAutoTempReport(
        **{
            **provisional.to_dict(),
            "donor_inspection": donor_res,
            "check_group_a_pixelmap_ntscpal_and_gamma": ga,
            "check_group_b_filesettings_tcregen_and_reclamp": gb,
            "check_group_c_powersave_autotemp_steadyshot_and_ciz": gc,
            "warnings": gb.warnings,
            "remediation_actions": tuple(remediations),
            "errors": tuple(all_errors),
            "report_sha256": digest,
        }
    )


run_pixelmap_ntscpal_powersave_and_autotemp_preflight = (
    evaluate_realhw_pixelmap_ntscpal_powersave_and_autotemp_readiness
)


def verify_phase227_report(payload: Mapping[str, Any]) -> Phase227ReportVerifyResult:
    """Fail-closed tamper & safety-lock verifier for Phase 227 preflight reports."""
    errors: List[str] = []
    if payload.get("schema") != PHASE_227_SCHEMA:
        errors.append(f"Invalid schema: {payload.get('schema')!r}")
    if payload.get("phase_version") != PHASE_227_VERSION:
        errors.append(f"Invalid phase_version: {payload.get('phase_version')!r}")
    if payload.get("verification_mode") not in ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"):
        errors.append(f"Invalid verification_mode: {payload.get('verification_mode')!r}")
    if payload.get("go_no_go") not in PHASE_227_VALID_GO_NO_GO_VALUES:
        errors.append(f"Invalid go_no_go verdict: {payload.get('go_no_go')!r}")

    for lock_key in (
        "hardware_live_attachment_authorized",
        "persistent_emmc_writes_authorized",
        "persistent_write_release",
        "spi_nor_write_authorized",
        "el3_payload_transmit_authorized",
        "sd_physical_media_written",
    ):
        if payload.get(lock_key) is not False:
            errors.append(f"Safety lock violated: {lock_key}={payload.get(lock_key)!r}")

    for zero_key in (
        "usb_packets_transmitted",
        "physical_usb_packets_emitted",
        "raw_firmware_bytes_leaked",
    ):
        if payload.get(zero_key) != 0:
            errors.append(f"Zero-counter violated: {zero_key}={payload.get(zero_key)!r}")

    if payload.get("check_group_count") != 3:
        errors.append(f"Expected check_group_count==3, got {payload.get('check_group_count')!r}")

    if payload.get("simulate_bench_dry_run") is True and (
        payload.get("go_no_go") == GO_NO_GO_PIXELMAP_NTSCPAL_POWERSAVE_AUTOTEMP_VERIFIED
    ):
        errors.append("Simulated dry-run cannot claim physical Tier-0 verified verdict")

    if payload.get("go_no_go") == GO_NO_GO_PIXELMAP_NTSCPAL_POWERSAVE_AUTOTEMP_VERIFIED and (
        payload.get("all_3_check_groups_passed") is not True
        or payload.get("tier0_receipt_verified") is not True
    ):
        errors.append("Verified verdict requires all 3 check groups and Tier-0 receipt verified")

    claimed_sha = str(payload.get("report_sha256", ""))
    expected_sha = _canonical_sha256_dict(payload, exclude_key="report_sha256")
    if not HEX64_RE.match(claimed_sha) or claimed_sha != expected_sha:
        errors.append("report_sha256 canonical digest mismatch")

    return Phase227ReportVerifyResult(valid=(len(errors) == 0), errors=tuple(errors))


def render_phase227_markdown(report: RealHwPixelMapNtscPalPowerSaveAutoTempReport) -> str:
    """Render concise deterministic Markdown summary for Phase 227 pre-shoot bench preflight."""
    ga = report.check_group_a_pixelmap_ntscpal_and_gamma
    gb = report.check_group_b_filesettings_tcregen_and_reclamp
    gc = report.check_group_c_powersave_autotemp_steadyshot_and_ciz
    lines = [
        f"# Phase 227 Physical Bench & Media Readiness (`{report.schema}`)",
        "",
        f"- **Go/No-Go Verdict**: `{report.go_no_go}` (mode=`{report.verification_mode}`, dry_run=`{report.simulate_bench_dry_run}`)",
        f"- **Check Groups**: `{report.check_groups_passed}/{report.check_group_count}` (`H0==H3`: `{report.h0_equals_h3_count}/{report.h0_h3_surface_count}`)",
        f"- **Hard Locks**: `live_attach={report.hardware_live_attachment_authorized}`, `emmc_writes={report.persistent_emmc_writes_authorized}`, `spi_nor={report.spi_nor_write_authorized}`, `el3_tx={report.el3_payload_transmit_authorized}`, `usb_pkts={report.usb_packets_transmitted}`, `leaked_bytes={report.raw_firmware_bytes_leaked}`",
        "",
        "| Check Group | Status | Key Telemetry |",
        "| :--- | :---: | :--- |",
        f"| `{ga.check_group_id}` | `{'PASS' if ga.passed else 'FAIL'}` | PixelMapAllowed=`{ga.pixel_mapping_allowed}` (`cnflasha_ro={ga.cnflasha_userspace_o_rdonly_enforced}`), `{ga.ntsc_pal_selector}` (`reset->{ga.effective_ntsc_pal_after_reset}`), GDA=`{ga.effective_gamma_display_assist}` vs LUT=`{ga.display_lut}` |",
        f"| `{gb.check_group_id}` | `{'PASS' if gb.passed else 'FAIL'}` | Format=`{gb.file_name_format}` (`{gb.file_number_mode}`), ShotMarkMP4Only=`{gb.shot_mark_mp4_xavc_only_verified}`, TC=`{gb.tc_make}`/`{gb.effective_tc_run}`, RecLamp=`{gb.rec_lamp_mode}` (XLR-H1=`{gb.xlr_h1_rec_lamp_lit}`) |",
        f"| `{gc.check_group_id}` | `{'PASS' if gc.passed else 'FAIL'}` | PowerSave=`{gc.power_save_start_time}` (bypassed=`{gc.power_save_bypassed}`), AutoTemp=`{gc.auto_power_off_temp}` (tripod=`{gc.tripod_mounted}`), SteadyShot=`{gc.steadyshot_mode}`, Zoom=`{gc.zoom_mode}`, Tier0=`{gc.tier0_receipt_verified}` |",
        "",
        f"- **Report SHA-256**: `{report.report_sha256}`",
    ]
    return "\n".join(lines) + "\n"
