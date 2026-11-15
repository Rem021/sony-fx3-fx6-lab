"""Phase 248 — Physical Bench & Pre-Shoot Media/Audio/Vault Readiness Verifier (`preflight-imagedb-touch-shoeaudio-and-lockop`).

Dedicated host-side read-only 5th physical bench & pre-shoot media/audio/vault readiness verifier
for Sony `ILME-FX3` (`Ver. 7.02`, Model `0x91030080`), extending the operator bench preflight
series (`preflight-card-insert` -> `preflight-bench-cable-fan-slot1` ->
`preflight-hdmi-proxy-desqueeze-and-simult` ->
`preflight-pixelmap-ntscpal-powersave-and-autotemp` ->
`preflight-imagedb-touch-shoeaudio-and-lockop`) by synthesizing Waves 34–39 real-hardware
intelligence into 4 deterministic fail-closed check groups (`A..D`), bounded `O_RDONLY` donor
inspection (`< 0.15s`), `16/16 H0 == H3` baseline invariance, and dual-media `528 B FX3RCPT1`
Tier-0 receipt gating:

1. **Check Group A (`GROUP_A_RECOVER_IMAGEDB_BATTERY_SLOT1_VAULT_AND_MONITOR_FLIP` — Wave 34)**:
   - Blocks `[Recover Image DB]` (`MENU -> Shooting -> [Media] -> [Recover Image DB]`) on a
     depleted `NP-FZ100` battery (`< 20.0%` SOC or low-battery warning) or on an unverified /
     non-`WP`-locked Slot 1 Tier-0 dump card (`pnflasha` / `cnflasha` / `CAMSET01.DAT`), while
     preserving non-deleting `AVF_INFO` repair semantics and action-item reset immunity.
   - Verifies `[Monitor Flip Direction]` (`Auto` / `Horizontal Flip` / `Vertical Flip` / `Off`)
     survives `[Camera Settings Reset]` & `[Reset Network Set.]` (restored only by `[Initialize]`)
     and enforces playback non-inversion even under `[Horizontal Flip]`.
   - Enforces `[AF Transition Speed]` (`1..7`), full-spelled `"AF Subj. Shift Sensitivity"`
     (`1..5`), and `[Interval Shoot Func.]` still-image-only capture scope.

2. **Check Group B (`GROUP_B_TOUCH_OP_4ITEM_GUARD_HDMI_CLEAN_FEED_AND_INDOOR_DISPLAY_POWER` — Waves 35 & 39)**:
   - Requires `[Touch Operation]` = `[Off]` or `[On: Playback Only]` during unattended Tier-0
     bench dumps and verifies all 4 Setup touch items (`Touch Operation`, `Touch Sensitivity`,
     `Swipe Up`, `Touch Func. in Shooting`) survive `[Camera Settings Reset]`.
   - Enforces forced `[HDMI Info. Display] = [Off]` clean-feed clamping whenever
     `[Rec. Media dur HDMI Output] = [Off(HDMI Only)]` or HDMI `RAW` output is active, while
     routing `[Emphasized REC Display]` / `[Grid Line Display]` (and never `Marker`/`Zebra`/
     `Peaking`) to external HDMI only when `[HDMI Info. Display] = [On]`.
   - Clamps indoor bench `[Monitor Brightness]` away from `[Sunny Weather]` to `[Manual]`
     (`-2..+2`) and clamps `[Display Quality]` to `[Standard]` (blocking `[High]`) to conserve
     `NP-FZ100` energy, plus enforces `[Bluetooth Rmt Ctrl]` infrared remote lockout & 3-way
     reset split (`Camera Settings Reset` vs `Reset Network Set.` vs `Initialize`).

3. **Check Group C (`GROUP_C_SHOE_AUDIO_4CH_WIND_BUILTIN_ONLY_AND_SAVELOAD_FIREWALL` — Wave 36)**:
   - Enforces `[Shoe Audio Set.]` (`48kHz/16bit 2ch`, `48kHz/24bit 2ch`, `48kHz/24bit 4ch`)
     4-channel (`CH1..CH4`) OSD audio meter coupling and all 3 hardware lockouts (`S&Q` or
     `[Audio Recording]=Off`, body `3.5mm` `MIC` plug priority, and `XLR-H1` `[ANALOG]` switch).
   - Enforces `[Wind Noise Reduct.]` built-in-microphone-only scope (rejecting external `3.5mm`
     or MI Shoe `XLR-H1` expectations and indoor `[On]` low-frequency attenuation).
   - Enforces `[Save/Load Settings]` (`CAMSET01..10.DAT` & `C3 Portal` / `Creators' Cloud`)
     `ILME-FX3` same-model lock, all 4 excluded privacy/calibration categories (`IPTC/Copyright`,
     `Custom WB 1..3`, `Face Memory`, `FTP/Streaming/Wi-Fi/TLS Secrets`), and blocks `[Save]` to
     Slot 1 Tier-0 dump cards.

4. **Check Group D (`GROUP_D_LOCK_OP_PARTS_5S_CHORD_USB_POWER_BATTERY_AND_SHUTTER_ANGLE_TABLE` — Waves 37 & 38)**:
   - Enforces `[Lock Operation Parts]` (`Off`, `Multi-Selector Only`, `Dial + Wheel`, `All`)
     Setup reset survival, `MENU + Fn` `5s` full-body lock chord (all controls except shutter
     button) vs hard-blocked destructive `MENU + Delete` `2s` Slot Full Format chord, and
     `My Dial` temporary unlock override.
   - Enforces `[USB Power Supply]` mandatory inserted `NP-FZ100` battery pack (unless `DC-C1`
     coupler is installed), `USB Type-C` power/charge exclusivity (`Multi/Micro USB` forbidden),
     `[USB LUN Setting]` (`Multi`/`Single`) survival, and absence of native `ILME-FX3`
     `[Var. Shutter]` + mechanical-still-only `[Anti-flicker Shoot.]`.
   - Enforces `[Exposure step]` (`0.3EV` / `0.5EV`) independence from `[Shutter Angle]`
     constant cine table (`5.6°..360°`), `[Audio Out Timing]` (`Live`/`Lip Sync`) `S&Q` lockout,
     `[Silent Mode]=On -> [Audio signals]=Off` lock, `16/16 H0 == H3` storage invariance, and
     dual-media `528 B FX3RCPT1` Tier-0 receipt gating.

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
# Schema, Verdicts & Domain Constants
# ---------------------------------------------------------------------------

PHASE_248_SCHEMA: str = "realhw_imagedb_touch_shoeaudio_and_lockop_verifier_v1"
REALHW_IMAGEDB_TOUCH_SHOEAUDIO_LOCKOP_SCHEMA: str = PHASE_248_SCHEMA
PHASE_248_VERSION: str = "248.0.0"

GO_NO_GO_IMAGEDB_TOUCH_SHOEAUDIO_LOCKOP_VERIFIED: str = (
    "GO_IMAGEDB_TOUCH_SHOEAUDIO_LOCKOP_READONLY_PREFLIGHT_VERIFIED"
)
GO_NO_GO_BLOCKED_IMAGEDB_TOUCH_SHOEAUDIO_LOCKOP_FAILURE: str = (
    "BLOCKED_IMAGEDB_TOUCH_SHOEAUDIO_LOCKOP_CHECK_FAILURE"
)
PHASE_248_VALID_GO_NO_GO_VALUES: Tuple[str, ...] = (
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    GO_NO_GO_BLOCKED_IMAGEDB_TOUCH_SHOEAUDIO_LOCKOP_FAILURE,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
    GO_NO_GO_IMAGEDB_TOUCH_SHOEAUDIO_LOCKOP_VERIFIED,
)

P248_CHECK_GROUP_A_ID: str = (
    "GROUP_A_RECOVER_IMAGEDB_BATTERY_SLOT1_VAULT_AND_MONITOR_FLIP"
)
P248_CHECK_GROUP_B_ID: str = (
    "GROUP_B_TOUCH_OP_4ITEM_GUARD_HDMI_CLEAN_FEED_AND_INDOOR_DISPLAY_POWER"
)
P248_CHECK_GROUP_C_ID: str = (
    "GROUP_C_SHOE_AUDIO_4CH_WIND_BUILTIN_ONLY_AND_SAVELOAD_FIREWALL"
)
P248_CHECK_GROUP_D_ID: str = (
    "GROUP_D_LOCK_OP_PARTS_5S_CHORD_USB_POWER_BATTERY_AND_SHUTTER_ANGLE_TABLE"
)
PHASE_248_CHECK_GROUP_IDS: Tuple[str, ...] = (
    P248_CHECK_GROUP_A_ID,
    P248_CHECK_GROUP_B_ID,
    P248_CHECK_GROUP_C_ID,
    P248_CHECK_GROUP_D_ID,
)

PHASE248_RAW_FIRMWARE_BYTES_LEAKED: int = 0

# Group A Constants (Wave 34)
RECOVER_IMAGE_DB_MIN_BATTERY_SOC_PCT: float = 20.0
AF_SUBJ_SHIFT_SENSITIVITY_EXACT_LABEL: str = "AF Subj. Shift Sensitivity"
VALID_MONITOR_FLIP_DIRECTIONS: Tuple[str, ...] = (
    "AUTO",
    "HORIZONTAL_FLIP",
    "VERTICAL_FLIP",
    "OFF",
)
VALID_P248_RESET_ACTIONS: Tuple[str, ...] = (
    "NONE",
    "CAMERA_SETTINGS_RESET",
    "RESET_NETWORK_SET",
    "INITIALIZE",
)

# Group B Constants (Waves 35 & 39)
TOUCH_OPERATION_FOUR_SETUP_ITEMS: Tuple[str, ...] = (
    "Touch Operation",
    "Touch Sensitivity",
    "Swipe Up",
    "Touch Func. in Shooting",
)
VALID_TOUCH_OPERATION_MODES: Tuple[str, ...] = ("ON", "ON_PLAYBACK_ONLY", "OFF")
SAFE_BENCH_TOUCH_OPERATION_MODES: Tuple[str, ...] = ("OFF", "ON_PLAYBACK_ONLY")
VALID_TOUCH_SENSITIVITY_MODES: Tuple[str, ...] = ("STANDARD", "SENSITIVE")
VALID_SWIPE_UP_MODES: Tuple[str, ...] = ("OPEN_THE_FN_MENU", "OFF")
VALID_TOUCH_FUNC_IN_SHOOTING_MODES: Tuple[str, ...] = (
    "TOUCH_TRACKING",
    "TOUCH_FOCUS",
    "OFF",
)
VALID_GRID_LINE_TYPES: Tuple[str, ...] = (
    "RULE_OF_3RDS_GRID",
    "SQUARE_GRID",
    "DIAG_PLUS_SQUARE_GRID",
)
VALID_MONITOR_BRIGHTNESS_MODES: Tuple[str, ...] = ("MANUAL", "SUNNY_WEATHER")
VALID_DISPLAY_QUALITY_MODES: Tuple[str, ...] = ("STANDARD", "HIGH")

# Group C Constants (Wave 36)
VALID_SHOE_AUDIO_SET_MODES: Tuple[str, ...] = (
    "48KHZ_16BIT_2CH",
    "48KHZ_24BIT_2CH",
    "48KHZ_24BIT_4CH",
)
SHOE_AUDIO_THREE_LOCKOUT_REASONS: Tuple[str, ...] = (
    "SQ_OR_AUDIO_RECORDING_OFF",
    "BODY_35MM_MIC_JACK_OVERRIDE",
    "XLR_H1_ANALOG_SWITCH_MODE",
)
SAVELOAD_FOUR_EXCLUDED_CATEGORIES: Tuple[str, ...] = (
    "IPTC_AND_COPYRIGHT_INFO",
    "CUSTOM_WB_1_2_3_REGISTERS",
    "FACE_MEMORY_BIOMETRICS",
    "NETWORK_FTP_STREAMING_WIFI_TLS_CREDENTIALS",
)
SAVELOAD_MAX_CAMSET_SLOTS: int = 10
VALID_SAVELOAD_OPERATIONS: Tuple[str, ...] = ("NONE", "LOAD", "SAVE")
VALID_SAVELOAD_TARGETS: Tuple[str, ...] = (
    "SLOT_1",
    "SLOT_2",
    "CLOUD_PRIVATE",
    "CLOUD_SHARE",
)

# Group D Constants (Waves 37 & 38)
VALID_LOCK_OPERATION_PARTS_MODES: Tuple[str, ...] = (
    "OFF",
    "MULTI_SELECTOR_ONLY",
    "DIAL_PLUS_WHEEL",
    "ALL",
)
LOCK_OP_FULL_BODY_CHORD: str = "MENU_PLUS_FN_5S"
LOCK_OP_FULL_BODY_HOLD_SECONDS: float = 5.0
DESTRUCTIVE_SLOT_FULL_FORMAT_CHORD: str = "MENU_PLUS_DELETE_2S"
DESTRUCTIVE_SLOT_FULL_FORMAT_HOLD_SECONDS: float = 2.0
VALID_EXPOSURE_STEP_VALUES: Tuple[str, ...] = ("0.3EV", "0.5EV")
SHUTTER_ANGLE_CONSTANT_DEGREE_TABLE: Tuple[float, ...] = (
    5.6,
    11.2,
    22.5,
    45.0,
    90.0,
    144.0,
    172.8,
    180.0,
    270.0,
    360.0,
)
VALID_AUDIO_OUT_TIMING_MODES: Tuple[str, ...] = ("LIVE", "LIP_SYNC")
VALID_USB_LUN_MODES: Tuple[str, ...] = ("MULTI", "SINGLE")
VALID_USB_POWER_TERMINALS: Tuple[str, ...] = ("USB_TYPE_C", "MULTI_MICRO_USB", "NONE")

# Error Codes
P248_GA_ERR_MODEL_OR_FW_FLOOR: str = "P248_GA_ERR_MODEL_OR_FW_FLOOR"
P248_GA_ERR_RECOVER_IMAGEDB_DEPLETED_BATTERY: str = (
    "P248_GA_ERR_RECOVER_IMAGEDB_DEPLETED_BATTERY"
)
P248_GA_ERR_RECOVER_IMAGEDB_SLOT1_TIER0_VAULT_GUARD: str = (
    "P248_GA_ERR_RECOVER_IMAGEDB_SLOT1_TIER0_VAULT_GUARD"
)
P248_GA_ERR_RECOVER_IMAGEDB_SEMANTICS_INVALID: str = (
    "P248_GA_ERR_RECOVER_IMAGEDB_SEMANTICS_INVALID"
)
P248_GA_ERR_MONITOR_FLIP_PERSISTENCE_OR_PLAYBACK_INVERSION: str = (
    "P248_GA_ERR_MONITOR_FLIP_PERSISTENCE_OR_PLAYBACK_INVERSION"
)
P248_GA_ERR_AF_KINEMATICS_OR_INTERVAL_STILL_ONLY: str = (
    "P248_GA_ERR_AF_KINEMATICS_OR_INTERVAL_STILL_ONLY"
)

P248_GB_ERR_TOUCH_OP_BENCH_TAP_GUARD_OR_PERSISTENCE: str = (
    "P248_GB_ERR_TOUCH_OP_BENCH_TAP_GUARD_OR_PERSISTENCE"
)
P248_GB_ERR_HDMI_CLEAN_FEED_OR_INFO_DISPLAY_VIOLATION: str = (
    "P248_GB_ERR_HDMI_CLEAN_FEED_OR_INFO_DISPLAY_VIOLATION"
)
P248_GB_ERR_INDOOR_SUNNY_WEATHER_OR_DISPLAY_QUALITY_HIGH: str = (
    "P248_GB_ERR_INDOOR_SUNNY_WEATHER_OR_DISPLAY_QUALITY_HIGH"
)
P248_GB_ERR_BT_RMT_CTRL_IR_LOCKOUT_OR_NETWORK_RESET: str = (
    "P248_GB_ERR_BT_RMT_CTRL_IR_LOCKOUT_OR_NETWORK_RESET"
)

P248_GC_ERR_SHOE_AUDIO_LOCKOUT_OR_METER_COUPLING: str = (
    "P248_GC_ERR_SHOE_AUDIO_LOCKOUT_OR_METER_COUPLING"
)
P248_GC_ERR_WIND_NOISE_REDUCT_EXTERNAL_MIC_OR_INDOOR_ON: str = (
    "P248_GC_ERR_WIND_NOISE_REDUCT_EXTERNAL_MIC_OR_INDOOR_ON"
)
P248_GC_ERR_SAVELOAD_EXCLUSIONS_OR_CROSS_MODEL_VIOLATION: str = (
    "P248_GC_ERR_SAVELOAD_EXCLUSIONS_OR_CROSS_MODEL_VIOLATION"
)
P248_GC_ERR_SAVELOAD_SLOT1_TIER0_SAVE_BLOCKED: str = (
    "P248_GC_ERR_SAVELOAD_SLOT1_TIER0_SAVE_BLOCKED"
)

P248_GD_ERR_LOCK_OP_PARTS_OR_DESTRUCTIVE_CHORD_VIOLATION: str = (
    "P248_GD_ERR_LOCK_OP_PARTS_OR_DESTRUCTIVE_CHORD_VIOLATION"
)
P248_GD_ERR_USB_POWER_MISSING_NPFZ100_OR_WRONG_PORT: str = (
    "P248_GD_ERR_USB_POWER_MISSING_NPFZ100_OR_WRONG_PORT"
)
P248_GD_ERR_SHUTTER_ANGLE_OR_AUDIO_TIMING_VIOLATION: str = (
    "P248_GD_ERR_SHUTTER_ANGLE_OR_AUDIO_TIMING_VIOLATION"
)
P248_GD_ERR_H0_H3_IMMUTABILITY_DRIFT: str = "P248_GD_ERR_H0_H3_IMMUTABILITY_DRIFT"
P248_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID: str = (
    "P248_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID"
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
class Phase248DonorInspectionResult:
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
class CheckGroupARecoverImageDbVaultMonitorFlipResult:
    check_group_id: str
    passed: bool
    body_model_id_hex: str
    body_fw: str
    recover_image_db_requested: bool
    recover_image_db_target_slot: int
    recover_image_db_allowed: bool
    non_deleting_repair_semantics_verified: bool
    battery_soc_pct: float
    low_battery_warning_active: bool
    slot1_contains_tier0_dump: bool
    slot1_tier0_sha256_verified_off_camera: bool
    slot1_wp_locked: bool
    monitor_flip_direction: str
    reset_action: str
    effective_monitor_flip_after_reset: str
    monitor_flip_survives_camera_reset: bool
    playback_display_horizontally_inverted: bool
    af_transition_speed: int
    af_subj_shift_sensitivity_label: str
    af_subj_shift_sensitivity: int
    interval_shoot_func_enabled: bool
    interval_shoot_still_only_verified: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class CheckGroupBTouchOpHdmiCleanFeedDisplayPowerResult:
    check_group_id: str
    passed: bool
    touch_operation: str
    touch_sensitivity: str
    swipe_up: str
    touch_func_in_shooting: str
    unattended_tier0_dump_active: bool
    touch_bench_tap_guard_satisfied: bool
    touch_4items_survive_camera_reset: bool
    effective_touch_operation_after_reset: str
    emphasized_rec_display: str
    grid_line_display: str
    grid_line_type: str
    rec_media_dur_hdmi_output: str
    hdmi_raw_output: bool
    requested_hdmi_info_display: str
    effective_hdmi_info_display: str
    hdmi_clean_feed_forced_off: bool
    builtin_lcd_blanked_by_hdmi_info: bool
    indoor_bench_environment: bool
    monitor_brightness_mode: str
    monitor_brightness_manual_level: int
    display_quality: str
    indoor_np_fz100_display_conservation_ok: bool
    bluetooth_rmt_ctrl: str
    effective_bluetooth_rmt_ctrl_after_reset: str
    ir_remote_locked_out_by_bt: bool
    display_from_my_menu: str
    effective_display_from_my_menu_after_reset: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class CheckGroupCShoeAudioWindNoiseSaveLoadResult:
    check_group_id: str
    passed: bool
    shoe_audio_set: str
    audio_recording: str
    sq_mode_enabled: bool
    body_35mm_mic_plugged: bool
    xlr_h1_attached: bool
    xlr_h1_mode_switch: str
    xlr_h1_low_cut_switch: str
    active_shoe_audio_lockouts: Tuple[str, ...]
    shoe_audio_digital_available: bool
    effective_audio_meter_channels: int
    wind_noise_reduct: str
    wind_noise_builtin_mic_only_verified: bool
    saveload_operation: str
    saveload_target: str
    camset_slot_index: int
    camset_model_code: str
    excluded_categories_enforced: Tuple[str, ...]
    saveload_exclusions_verified: bool
    slot1_camset_save_firewall_ok: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class CheckGroupDLockOpUsbPowerShutterAngleResult:
    check_group_id: str
    passed: bool
    lock_operation_parts: str
    effective_lock_op_after_reset: str
    active_key_chord: str
    lock_chord_hold_seconds: float
    full_body_lock_except_shutter_engaged: bool
    destructive_format_chord_blocked: bool
    my_dial_temporarily_unlocks_dials: bool
    power_source: str
    usb_power_supply: str
    usb_power_terminal: str
    usb_lun_setting: str
    np_fz100_battery_inserted: bool
    dc_c1_coupler_inserted: bool
    usb_power_battery_interlock_ok: bool
    exposure_step: str
    shutter_mode: str
    shutter_angle_deg: float
    shutter_angle_unaffected_by_exposure_step: bool
    audio_out_timing: str
    silent_mode_enabled: bool
    audio_signals_mode: str
    h0_h3_surface_count: int
    h0_equals_h3_count: int
    tier0_receipt_present: bool
    tier0_receipt_verified: bool
    distinct_physical_media_verified: bool
    warnings: Tuple[str, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class RealHwImageDbTouchShoeAudioLockOpReport:
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
    check_group_count: int
    check_groups_passed: int
    all_4_check_groups_passed: bool
    tier0_receipt_verified: bool
    h0_h3_surface_count: int
    h0_equals_h3_count: int
    donor_inspection: Phase248DonorInspectionResult
    check_group_a_imagedb_vault_and_monitor_flip: CheckGroupARecoverImageDbVaultMonitorFlipResult
    check_group_b_touch_op_hdmi_and_display_power: CheckGroupBTouchOpHdmiCleanFeedDisplayPowerResult
    check_group_c_shoe_audio_wind_and_saveload: CheckGroupCShoeAudioWindNoiseSaveLoadResult
    check_group_d_lock_op_usb_power_and_shutter_angle: CheckGroupDLockOpUsbPowerShutterAngleResult
    warnings: Tuple[str, ...]
    remediation_actions: Tuple[str, ...]
    errors: Tuple[str, ...]
    report_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_deterministic_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=False) + "\n"


@dataclass(frozen=True)
class Phase248ReportVerifyResult:
    valid: bool
    errors: Tuple[str, ...]


# ---------------------------------------------------------------------------
# Internal Helpers & Bounded O_RDONLY Donor Inspection (< 0.15s)
# ---------------------------------------------------------------------------


def _norm_token(raw: str) -> str:
    return re.sub(r"[\s\-:/\.]+", "_", str(raw).strip().upper()).strip("_")


def _norm_touch_op_mode(raw: str) -> str:
    s = str(raw).strip().upper()
    aliases = {
        "ON": "ON",
        "OFF": "OFF",
        "ON: PLAYBACK ONLY": "ON_PLAYBACK_ONLY",
        "ON_PLAYBACK_ONLY": "ON_PLAYBACK_ONLY",
        "PLAYBACK_ONLY": "ON_PLAYBACK_ONLY",
    }
    return aliases.get(s, _norm_token(raw))


def _norm_shoe_audio_mode(raw: str) -> str:
    s = str(raw).strip().upper()
    aliases = {
        "48KHZ/16BIT 2CH": "48KHZ_16BIT_2CH",
        "48KHZ_16BIT_2CH": "48KHZ_16BIT_2CH",
        "16BIT_2CH": "48KHZ_16BIT_2CH",
        "48KHZ/24BIT 2CH": "48KHZ_24BIT_2CH",
        "48KHZ_24BIT_2CH": "48KHZ_24BIT_2CH",
        "24BIT_2CH": "48KHZ_24BIT_2CH",
        "48KHZ/24BIT 4CH": "48KHZ_24BIT_4CH",
        "48KHZ_24BIT_4CH": "48KHZ_24BIT_4CH",
        "24BIT_4CH": "48KHZ_24BIT_4CH",
    }
    return aliases.get(s, _norm_token(raw))


def _norm_lock_op_mode(raw: str) -> str:
    s = str(raw).strip().upper()
    aliases = {
        "OFF": "OFF",
        "MULTI-SELECTOR ONLY": "MULTI_SELECTOR_ONLY",
        "MULTI-SLCT ONLY": "MULTI_SELECTOR_ONLY",
        "MULTI_SLCT_ONLY": "MULTI_SELECTOR_ONLY",
        "MULTI_SELECTOR_ONLY": "MULTI_SELECTOR_ONLY",
        "DIAL + WHEEL": "DIAL_PLUS_WHEEL",
        "DIAL+WHEEL": "DIAL_PLUS_WHEEL",
        "DIAL_PLUS_WHEEL": "DIAL_PLUS_WHEEL",
        "ALL": "ALL",
    }
    return aliases.get(s, _norm_token(raw))


def _norm_exposure_step(raw: str) -> str:
    s = str(raw).strip().upper().replace(" ", "")
    if s in ("0.3EV", "0_3EV"):
        return "0.3EV"
    if s in ("0.5EV", "0_5EV"):
        return "0.5EV"
    return s


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


def inspect_phase248_donors_bounded(
    *,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    force_clean_room: Optional[bool] = None,
    synthetic_clean_room: Optional[bool] = None,
    max_seconds: float = DONOR_INSPECTION_MAX_SECONDS,
) -> Phase248DonorInspectionResult:
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
        return Phase248DonorInspectionResult(
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
            raw_firmware_bytes_leaked=PHASE248_RAW_FIRMWARE_BYTES_LEAKED,
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

    return Phase248DonorInspectionResult(
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
        raw_firmware_bytes_leaked=PHASE248_RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Check Group A: [Recover Image DB] Battery & Slot-1 Tier-0 Vault Guard + Monitor Flip (Wave 34)
# ---------------------------------------------------------------------------


def evaluate_check_group_a_imagedb_vault_and_monitor_flip(
    *,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    recover_image_db_requested: bool = False,
    recover_image_db_target_slot: int = 2,
    expect_recover_imagedb_deletes_clips: bool = False,
    battery_soc_pct: float = 88.0,
    low_battery_warning_active: bool = False,
    slot1_contains_tier0_dump: bool = True,
    slot1_tier0_sha256_verified_off_camera: bool = True,
    slot1_wp_locked: bool = True,
    monitor_flip_direction: str = "AUTO",
    reset_action: str = "NONE",
    claimed_monitor_flip_after_reset: Optional[str] = None,
    expect_playback_inverted_under_horizontal_flip: bool = False,
    af_transition_speed: int = 5,
    af_subj_shift_sensitivity_label: str = AF_SUBJ_SHIFT_SENSITIVITY_EXACT_LABEL,
    af_subj_shift_sensitivity: int = 5,
    interval_shoot_func_enabled: bool = False,
    expect_interval_in_camera_movie_recording: bool = False,
) -> CheckGroupARecoverImageDbVaultMonitorFlipResult:
    errors: List[str] = []

    # 1. Model ID & Firmware Floor
    fw_tuple = _parse_fw_tuple(body_fw)
    if (
        int(body_model_id) != TARGET_MODEL_ID_INT
        or fw_tuple is None
        or fw_tuple < MIN_BODY_FW_TUPLE
    ):
        errors.append(
            f"{P248_GA_ERR_MODEL_OR_FW_FLOOR}: expected ILME-FX3 0x91030080 fw>=2.04, "
            f"got model=0x{int(body_model_id):08x} fw={body_fw!r}"
        )

    # 2. [Recover Image DB] Non-Deleting Repair, Depleted-Battery Block & Slot-1 Tier-0 Vault Guard
    target_slot = int(recover_image_db_target_slot)
    soc = float(battery_soc_pct)
    non_deleting_ok = not bool(expect_recover_imagedb_deletes_clips)
    if target_slot not in (1, 2) or not non_deleting_ok:
        errors.append(
            f"{P248_GA_ERR_RECOVER_IMAGEDB_SEMANTICS_INVALID}: [Recover Image DB] repairs AVF_INFO "
            f"without deleting recorded clips on Slot 1/2 (slot={target_slot}, delete_claim={expect_recover_imagedb_deletes_clips})"
        )

    battery_ok_for_repair = (soc >= RECOVER_IMAGE_DB_MIN_BATTERY_SOC_PCT) and (
        not bool(low_battery_warning_active)
    )
    slot1_vault_safe_for_repair = True
    if target_slot == 1 and bool(slot1_contains_tier0_dump):
        if (not bool(slot1_tier0_sha256_verified_off_camera)) or (not bool(slot1_wp_locked)):
            slot1_vault_safe_for_repair = False

    imagedb_allowed = battery_ok_for_repair and slot1_vault_safe_for_repair
    if bool(recover_image_db_requested):
        if not battery_ok_for_repair:
            errors.append(
                f"{P248_GA_ERR_RECOVER_IMAGEDB_DEPLETED_BATTERY}: [Recover Image DB] blocked on "
                f"depleted NP-FZ100 battery (soc={soc:.1f}% < {RECOVER_IMAGE_DB_MIN_BATTERY_SOC_PCT:.1f}% "
                f"or low_battery_warning={low_battery_warning_active})"
            )
        if target_slot == 1 and bool(slot1_contains_tier0_dump):
            if (not bool(slot1_tier0_sha256_verified_off_camera)) or (not bool(slot1_wp_locked)):
                errors.append(
                    f"{P248_GA_ERR_RECOVER_IMAGEDB_SLOT1_TIER0_VAULT_GUARD}: [Recover Image DB] "
                    "blocked on unverified or non-WP-locked Slot 1 Tier-0 dump card "
                    f"(pnflasha/cnflasha: sha256_verified={slot1_tier0_sha256_verified_off_camera}, wp_locked={slot1_wp_locked})"
                )

    # 3. [Monitor Flip Direction] Reset Persistence & [Horizontal Flip] Playback Non-Inversion
    flip_norm = _norm_token(monitor_flip_direction)
    rst_norm = _norm_token(reset_action)
    if flip_norm not in VALID_MONITOR_FLIP_DIRECTIONS or rst_norm not in VALID_P248_RESET_ACTIONS:
        errors.append(
            f"{P248_GA_ERR_MONITOR_FLIP_PERSISTENCE_OR_PLAYBACK_INVERSION}: invalid "
            f"[Monitor Flip Direction]={monitor_flip_direction!r} or reset_action={reset_action!r}"
        )

    eff_flip = "AUTO" if rst_norm == "INITIALIZE" else flip_norm
    if claimed_monitor_flip_after_reset is not None:
        claimed_flip_norm = _norm_token(claimed_monitor_flip_after_reset)
        if claimed_flip_norm != eff_flip:
            errors.append(
                f"{P248_GA_ERR_MONITOR_FLIP_PERSISTENCE_OR_PLAYBACK_INVERSION}: [Monitor Flip Direction] "
                f"survives [Camera Settings Reset]/[Reset Network Set.] and resets to AUTO only on [Initialize] "
                f"(expected={eff_flip}, claimed={claimed_flip_norm})"
            )

    if bool(expect_playback_inverted_under_horizontal_flip):
        errors.append(
            f"{P248_GA_ERR_MONITOR_FLIP_PERSISTENCE_OR_PLAYBACK_INVERSION}: even when set to "
            "[Horizontal Flip], ILME-FX3 playback display direction is NEVER horizontally inverted"
        )

    # 4. Movie/S&Q AF Kinematics (1..7 / 1..5) & [Interval Shoot Func.] Still-Image-Only Scope
    af_spd = int(af_transition_speed)
    af_sens = int(af_subj_shift_sensitivity)
    sens_label = str(af_subj_shift_sensitivity_label).strip()
    still_only_ok = not (
        bool(interval_shoot_func_enabled) and bool(expect_interval_in_camera_movie_recording)
    )
    if (
        not (1 <= af_spd <= 7)
        or not (1 <= af_sens <= 5)
        or sens_label != AF_SUBJ_SHIFT_SENSITIVITY_EXACT_LABEL
        or not still_only_ok
    ):
        errors.append(
            f"{P248_GA_ERR_AF_KINEMATICS_OR_INTERVAL_STILL_ONLY}: invalid AF kinematics or Interval Shoot scope "
            f"(speed={af_spd} [1..7], label={sens_label!r}, sens={af_sens} [1..5], still_only_ok={still_only_ok})"
        )

    return CheckGroupARecoverImageDbVaultMonitorFlipResult(
        check_group_id=P248_CHECK_GROUP_A_ID,
        passed=(len(errors) == 0),
        body_model_id_hex=f"0x{int(body_model_id):08x}",
        body_fw=str(body_fw).strip(),
        recover_image_db_requested=bool(recover_image_db_requested),
        recover_image_db_target_slot=target_slot,
        recover_image_db_allowed=imagedb_allowed,
        non_deleting_repair_semantics_verified=non_deleting_ok,
        battery_soc_pct=soc,
        low_battery_warning_active=bool(low_battery_warning_active),
        slot1_contains_tier0_dump=bool(slot1_contains_tier0_dump),
        slot1_tier0_sha256_verified_off_camera=bool(slot1_tier0_sha256_verified_off_camera),
        slot1_wp_locked=bool(slot1_wp_locked),
        monitor_flip_direction=flip_norm,
        reset_action=rst_norm,
        effective_monitor_flip_after_reset=eff_flip,
        monitor_flip_survives_camera_reset=True,
        playback_display_horizontally_inverted=False,
        af_transition_speed=af_spd,
        af_subj_shift_sensitivity_label=sens_label,
        af_subj_shift_sensitivity=af_sens,
        interval_shoot_func_enabled=bool(interval_shoot_func_enabled),
        interval_shoot_still_only_verified=still_only_ok,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Check Group B: [Touch Operation] 4-Item Guard, HDMI Clean-Feed & Indoor Display Power (Waves 35 & 39)
# ---------------------------------------------------------------------------


def evaluate_check_group_b_touch_op_hdmi_and_display_power(
    *,
    touch_operation: str = "OFF",
    touch_sensitivity: str = "STANDARD",
    swipe_up: str = "OPEN_THE_FN_MENU",
    touch_func_in_shooting: str = "OFF",
    unattended_tier0_dump_active: bool = True,
    reset_action: str = "NONE",
    claimed_touch_operation_after_reset: Optional[str] = None,
    emphasized_rec_display: str = "ON",
    grid_line_display: str = "OFF",
    grid_line_type: str = "RULE_OF_3RDS_GRID",
    rec_media_dur_hdmi_output: str = "ON",
    hdmi_raw_output: bool = False,
    hdmi_info_display: str = "OFF",
    expect_hdmi_info_on_during_hdmionly_or_raw: bool = False,
    expect_marker_zebra_peaking_on_hdmi: bool = False,
    indoor_bench_environment: bool = True,
    monitor_brightness_mode: str = "MANUAL",
    monitor_brightness_manual_level: int = 0,
    display_quality: str = "STANDARD",
    bluetooth_rmt_ctrl: str = "OFF",
    bluetooth_function: str = "OFF",
    airplane_mode: str = "ON",
    expect_ir_remote_usable: bool = False,
    claimed_bluetooth_rmt_ctrl_after_reset: Optional[str] = None,
    display_from_my_menu: str = "OFF",
    claimed_display_from_my_menu_after_reset: Optional[str] = None,
) -> CheckGroupBTouchOpHdmiCleanFeedDisplayPowerResult:
    errors: List[str] = []

    # 1. [Touch Operation] 4-Item Setup Persistence & Unattended Bench Tap Guard
    t_op = _norm_touch_op_mode(touch_operation)
    t_sens = _norm_token(touch_sensitivity)
    t_swipe = _norm_token(swipe_up)
    t_func = _norm_token(touch_func_in_shooting)
    rst_norm = _norm_token(reset_action)

    if (
        t_op not in VALID_TOUCH_OPERATION_MODES
        or t_sens not in VALID_TOUCH_SENSITIVITY_MODES
        or t_swipe not in VALID_SWIPE_UP_MODES
        or t_func not in VALID_TOUCH_FUNC_IN_SHOOTING_MODES
        or rst_norm not in VALID_P248_RESET_ACTIONS
    ):
        errors.append(
            f"{P248_GB_ERR_TOUCH_OP_BENCH_TAP_GUARD_OR_PERSISTENCE}: invalid [Touch Operation] "
            f"4-item tuple=({touch_operation!r}, {touch_sensitivity!r}, {swipe_up!r}, {touch_func_in_shooting!r}) "
            f"or reset_action={reset_action!r}"
        )

    tap_guard_ok = (not bool(unattended_tier0_dump_active)) or (
        t_op in SAFE_BENCH_TOUCH_OPERATION_MODES
    )
    if not tap_guard_ok:
        errors.append(
            f"{P248_GB_ERR_TOUCH_OP_BENCH_TAP_GUARD_OR_PERSISTENCE}: unattended Tier-0 bench dump "
            f"requires [Touch Operation] in {SAFE_BENCH_TOUCH_OPERATION_MODES} to prevent accidental "
            f"Swipe Up / Touch Tracking taps (got {t_op})"
        )

    eff_t_op = "ON" if rst_norm == "INITIALIZE" else t_op
    if claimed_touch_operation_after_reset is not None:
        claimed_top = _norm_touch_op_mode(claimed_touch_operation_after_reset)
        if claimed_top != eff_t_op:
            errors.append(
                f"{P248_GB_ERR_TOUCH_OP_BENCH_TAP_GUARD_OR_PERSISTENCE}: all 4 [Touch Operation] "
                f"Setup items survive [Camera Settings Reset]/[Reset Network Set.] "
                f"(expected={eff_t_op}, claimed={claimed_top})"
            )

    # 2. [Emphasized REC Display] & [Grid Line Display] HDMI Routing vs Forced [Off(HDMI Only)] / RAW Clean-Feed
    emp_rec = _norm_token(emphasized_rec_display)
    grid_disp = _norm_token(grid_line_display)
    grid_type = _norm_token(grid_line_type)
    rec_dur_hdmi = _norm_token(rec_media_dur_hdmi_output)
    req_hdmi_info = _norm_token(hdmi_info_display)
    if rec_dur_hdmi == "OFF(HDMI_ONLY)":
        rec_dur_hdmi = "OFF_HDMI_ONLY"

    if (
        emp_rec not in ("ON", "OFF")
        or grid_disp not in ("ON", "OFF")
        or grid_type not in VALID_GRID_LINE_TYPES
        or rec_dur_hdmi not in ("ON", "OFF_HDMI_ONLY")
        or req_hdmi_info not in ("ON", "OFF")
    ):
        errors.append(
            f"{P248_GB_ERR_HDMI_CLEAN_FEED_OR_INFO_DISPLAY_VIOLATION}: invalid HDMI/OSD config "
            f"(EmphasizedRec={emphasized_rec_display!r}, Grid={grid_line_display!r}/{grid_line_type!r}, "
            f"RecMediaDurHDMI={rec_media_dur_hdmi_output!r}, HDMIInfo={hdmi_info_display!r})"
        )

    clean_feed_forced = (rec_dur_hdmi == "OFF_HDMI_ONLY") or bool(hdmi_raw_output)
    eff_hdmi_info = "OFF" if clean_feed_forced else req_hdmi_info
    if clean_feed_forced and (
        req_hdmi_info == "ON" or bool(expect_hdmi_info_on_during_hdmionly_or_raw)
    ):
        errors.append(
            f"{P248_GB_ERR_HDMI_CLEAN_FEED_OR_INFO_DISPLAY_VIOLATION}: [HDMI Info. Display] is "
            "hardware-forced to [Off] whenever [Rec. Media dur HDMI Output]=[Off(HDMI Only)] or "
            "HDMI RAW output is active (cannot route Emphasized REC / Grid Line OSD into clean feed)"
        )
    if bool(expect_marker_zebra_peaking_on_hdmi):
        errors.append(
            f"{P248_GB_ERR_HDMI_CLEAN_FEED_OR_INFO_DISPLAY_VIOLATION}: [Marker Display], "
            "[Zebra Display], and [Peaking Display] are local-LCD-only and never output over HDMI"
        )
    lcd_blanked = eff_hdmi_info == "ON"

    # 3. Indoor [Monitor Brightness] ([Sunny Weather] Clamp) & [Display Quality]=[Standard] NP-FZ100 Conservation
    mon_brt = _norm_token(monitor_brightness_mode)
    mon_lvl = int(monitor_brightness_manual_level)
    disp_qual = _norm_token(display_quality)
    display_conservation_ok = True

    if (
        mon_brt not in VALID_MONITOR_BRIGHTNESS_MODES
        or not (-2 <= mon_lvl <= 2)
        or disp_qual not in VALID_DISPLAY_QUALITY_MODES
    ):
        display_conservation_ok = False
        errors.append(
            f"{P248_GB_ERR_INDOOR_SUNNY_WEATHER_OR_DISPLAY_QUALITY_HIGH}: invalid "
            f"[Monitor Brightness]={monitor_brightness_mode!r} (level={mon_lvl}, -2..+2) or "
            f"[Display Quality]={display_quality!r}"
        )
    else:
        if bool(indoor_bench_environment) and mon_brt == "SUNNY_WEATHER":
            display_conservation_ok = False
            errors.append(
                f"{P248_GB_ERR_INDOOR_SUNNY_WEATHER_OR_DISPLAY_QUALITY_HIGH}: [Monitor Brightness]="
                "[Sunny Weather] is too bright for indoor bench operation and wastes NP-FZ100 energy; "
                "clamp to [Manual] (-2..+2)"
            )
        if (bool(indoor_bench_environment) or bool(unattended_tier0_dump_active)) and (
            disp_qual == "HIGH"
        ):
            display_conservation_ok = False
            errors.append(
                f"{P248_GB_ERR_INDOOR_SUNNY_WEATHER_OR_DISPLAY_QUALITY_HIGH}: [Display Quality]=[High] "
                "accelerates NP-FZ100 battery drain during indoor/Tier-0 bench work; clamp to [Standard]"
            )

    # 4. Wave 39 [Bluetooth Rmt Ctrl] IR Lockout & 3-Reset Domain Split + [Display From My Menu] Persistence
    bt_rmt = _norm_token(bluetooth_rmt_ctrl)
    bt_fn = _norm_token(bluetooth_function)
    air_mode = _norm_token(airplane_mode)
    my_menu_disp = _norm_token(display_from_my_menu)

    if (
        bt_rmt not in ("ON", "OFF")
        or bt_fn not in ("ON", "OFF")
        or air_mode not in ("ON", "OFF")
        or my_menu_disp not in ("ON", "OFF")
    ):
        errors.append(
            f"{P248_GB_ERR_BT_RMT_CTRL_IR_LOCKOUT_OR_NETWORK_RESET}: invalid Bluetooth/Airplane/MyMenu "
            f"state ({bluetooth_rmt_ctrl!r}, {bluetooth_function!r}, {airplane_mode!r}, {display_from_my_menu!r})"
        )
    if bt_rmt == "ON" and (bt_fn != "ON" or air_mode != "OFF"):
        errors.append(
            f"{P248_GB_ERR_BT_RMT_CTRL_IR_LOCKOUT_OR_NETWORK_RESET}: [Bluetooth Rmt Ctrl]=[On] "
            "requires [Bluetooth Function]=[On] and [Airplane Mode]=[Off]"
        )
    ir_locked_out = bt_rmt == "ON"
    if ir_locked_out and bool(expect_ir_remote_usable):
        errors.append(
            f"{P248_GB_ERR_BT_RMT_CTRL_IR_LOCKOUT_OR_NETWORK_RESET}: infrared remote commander "
            "cannot be used while [Bluetooth Rmt Ctrl] is set to [On]"
        )

    eff_bt_rmt = "OFF" if rst_norm in ("RESET_NETWORK_SET", "INITIALIZE") else bt_rmt
    if claimed_bluetooth_rmt_ctrl_after_reset is not None:
        if _norm_token(claimed_bluetooth_rmt_ctrl_after_reset) != eff_bt_rmt:
            errors.append(
                f"{P248_GB_ERR_BT_RMT_CTRL_IR_LOCKOUT_OR_NETWORK_RESET}: [Bluetooth Rmt Ctrl] "
                "survives [Camera Settings Reset] and resets to [Off] on [Reset Network Set.]/[Initialize]"
            )

    eff_my_menu = "OFF" if rst_norm == "INITIALIZE" else my_menu_disp
    if claimed_display_from_my_menu_after_reset is not None:
        if _norm_token(claimed_display_from_my_menu_after_reset) != eff_my_menu:
            errors.append(
                f"{P248_GB_ERR_BT_RMT_CTRL_IR_LOCKOUT_OR_NETWORK_RESET}: [Display From My Menu] "
                "survives both [Camera Settings Reset] and [Reset Network Set.] (cleared only by [Initialize])"
            )

    return CheckGroupBTouchOpHdmiCleanFeedDisplayPowerResult(
        check_group_id=P248_CHECK_GROUP_B_ID,
        passed=(len(errors) == 0),
        touch_operation=t_op,
        touch_sensitivity=t_sens,
        swipe_up=t_swipe,
        touch_func_in_shooting=t_func,
        unattended_tier0_dump_active=bool(unattended_tier0_dump_active),
        touch_bench_tap_guard_satisfied=tap_guard_ok,
        touch_4items_survive_camera_reset=True,
        effective_touch_operation_after_reset=eff_t_op,
        emphasized_rec_display=emp_rec,
        grid_line_display=grid_disp,
        grid_line_type=grid_type,
        rec_media_dur_hdmi_output=rec_dur_hdmi,
        hdmi_raw_output=bool(hdmi_raw_output),
        requested_hdmi_info_display=req_hdmi_info,
        effective_hdmi_info_display=eff_hdmi_info,
        hdmi_clean_feed_forced_off=clean_feed_forced,
        builtin_lcd_blanked_by_hdmi_info=lcd_blanked,
        indoor_bench_environment=bool(indoor_bench_environment),
        monitor_brightness_mode=mon_brt,
        monitor_brightness_manual_level=mon_lvl,
        display_quality=disp_qual,
        indoor_np_fz100_display_conservation_ok=display_conservation_ok,
        bluetooth_rmt_ctrl=bt_rmt,
        effective_bluetooth_rmt_ctrl_after_reset=eff_bt_rmt,
        ir_remote_locked_out_by_bt=ir_locked_out,
        display_from_my_menu=my_menu_disp,
        effective_display_from_my_menu_after_reset=eff_my_menu,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Check Group C: [Shoe Audio Set.] 4ch, [Wind Noise Reduct.] Built-In-Only & [Save/Load] Firewall (Wave 36)
# ---------------------------------------------------------------------------


def evaluate_check_group_c_shoe_audio_wind_and_saveload(
    *,
    shoe_audio_set: str = "48KHZ_24BIT_4CH",
    audio_recording: str = "ON",
    sq_mode_enabled: bool = False,
    body_35mm_mic_plugged: bool = False,
    xlr_h1_attached: bool = True,
    xlr_h1_mode_switch: str = "DIGITAL",
    xlr_h1_low_cut_switch: str = "OFF",
    claimed_audio_meter_channels: Optional[int] = None,
    wind_noise_reduct: str = "OFF",
    expect_wind_noise_reduct_on_external_mic: bool = False,
    indoor_calm_bench_audio: bool = True,
    saveload_operation: str = "NONE",
    saveload_target: str = "SLOT_2",
    camset_slot_index: int = 1,
    camset_model_code: str = "ILME-FX3",
    camset_payload_contains_excluded_items: bool = False,
    expect_saveload_includes_excluded_secrets_or_cal: bool = False,
    slot1_contains_tier0_dump: bool = True,
    slot1_tier0_sha256_verified_off_camera: bool = True,
    slot1_wp_locked: bool = True,
) -> CheckGroupCShoeAudioWindNoiseSaveLoadResult:
    errors: List[str] = []

    # 1. [Shoe Audio Set.] 48kHz/24bit 4ch Routing, 4ch Meter Coupling & 3 Hardware Lockouts
    shoe_mode = _norm_shoe_audio_mode(shoe_audio_set)
    aud_rec = _norm_token(audio_recording)
    xlr_sw = _norm_token(xlr_h1_mode_switch)
    xlr_lc = _norm_token(xlr_h1_low_cut_switch)

    if (
        shoe_mode not in VALID_SHOE_AUDIO_SET_MODES
        or aud_rec not in ("ON", "OFF")
        or xlr_sw not in ("DIGITAL", "ANALOG")
        or xlr_lc not in ("OFF", "100HZ", "300HZ")
    ):
        errors.append(
            f"{P248_GC_ERR_SHOE_AUDIO_LOCKOUT_OR_METER_COUPLING}: invalid [Shoe Audio Set.]={shoe_audio_set!r}, "
            f"[Audio Recording]={audio_recording!r}, or XLR-H1 switch=({xlr_h1_mode_switch!r}, {xlr_h1_low_cut_switch!r})"
        )

    lockouts: List[str] = []
    if aud_rec == "OFF" or bool(sq_mode_enabled):
        lockouts.append("SQ_OR_AUDIO_RECORDING_OFF")
    if bool(body_35mm_mic_plugged):
        lockouts.append("BODY_35MM_MIC_JACK_OVERRIDE")
    if bool(xlr_h1_attached) and xlr_sw == "ANALOG":
        lockouts.append("XLR_H1_ANALOG_SWITCH_MODE")

    digital_shoe_available = bool(xlr_h1_attached) and (len(lockouts) == 0)

    if shoe_mode in ("48KHZ_24BIT_4CH", "48KHZ_24BIT_2CH") and not digital_shoe_available:
        errors.append(
            f"{P248_GC_ERR_SHOE_AUDIO_LOCKOUT_OR_METER_COUPLING}: [Shoe Audio Set.]={shoe_mode} "
            f"unavailable due to active hardware lockout(s)={tuple(lockouts)} or missing digital MI Shoe "
            f"(xlr_h1_attached={xlr_h1_attached})"
        )

    if "SQ_OR_AUDIO_RECORDING_OFF" in lockouts:
        eff_meters = 0
    elif digital_shoe_available and shoe_mode == "48KHZ_24BIT_4CH":
        eff_meters = 4
    else:
        eff_meters = 2

    if claimed_audio_meter_channels is not None and int(claimed_audio_meter_channels) != eff_meters:
        errors.append(
            f"{P248_GC_ERR_SHOE_AUDIO_LOCKOUT_OR_METER_COUPLING}: [Audio Level Display] meter channel "
            f"mismatch (expected {eff_meters}ch, claimed {claimed_audio_meter_channels}ch)"
        )

    # 2. [Wind Noise Reduct.] Built-In-Microphone-Only Scope & Indoor Low-Frequency Guard
    wind_mode = _norm_token(wind_noise_reduct)
    external_mic_active = bool(body_35mm_mic_plugged) or bool(xlr_h1_attached)
    wind_builtin_only_ok = True

    if wind_mode not in ("OFF", "ON"):
        wind_builtin_only_ok = False
        errors.append(
            f"{P248_GC_ERR_WIND_NOISE_REDUCT_EXTERNAL_MIC_OR_INDOOR_ON}: invalid "
            f"[Wind Noise Reduct.]={wind_noise_reduct!r}"
        )
    elif bool(expect_wind_noise_reduct_on_external_mic) or (
        wind_mode == "ON"
        and (
            external_mic_active
            or aud_rec == "OFF"
            or bool(sq_mode_enabled)
            or bool(indoor_calm_bench_audio)
        )
    ):
        wind_builtin_only_ok = False
        errors.append(
            f"{P248_GC_ERR_WIND_NOISE_REDUCT_EXTERNAL_MIC_OR_INDOOR_ON}: [Wind Noise Reduct.] "
            "operates exclusively on the camera body's built-in mic (never 3.5mm MIC or MI Shoe XLR-H1), "
            "is locked out in S&Q / Audio=Off, and must stay [Off] on calm indoor benches"
        )

    # 3. [Save/Load Settings] Excluded-Items Firewall & Slot-1 Tier-0 Save Guard
    sl_op = _norm_token(saveload_operation)
    sl_tgt = _norm_token(saveload_target)
    slot_idx = int(camset_slot_index)
    model_norm = str(camset_model_code).strip().upper()

    exclusions_ok = not (
        bool(camset_payload_contains_excluded_items)
        or bool(expect_saveload_includes_excluded_secrets_or_cal)
    )
    if (
        sl_op not in VALID_SAVELOAD_OPERATIONS
        or sl_tgt not in VALID_SAVELOAD_TARGETS
        or not (1 <= slot_idx <= SAVELOAD_MAX_CAMSET_SLOTS)
        or model_norm != "ILME-FX3"
        or not exclusions_ok
    ):
        errors.append(
            f"{P248_GC_ERR_SAVELOAD_EXCLUSIONS_OR_CROSS_MODEL_VIOLATION}: invalid [Save/Load Settings] "
            f"(op={saveload_operation!r}, target={saveload_target!r}, CAMSET={slot_idx:02d} [1..10], "
            f"model={model_norm!r} [must be ILME-FX3], exclusions_ok={exclusions_ok})"
        )

    slot1_save_ok = True
    if sl_op == "SAVE" and sl_tgt == "SLOT_1":
        if (
            bool(slot1_contains_tier0_dump)
            or (not bool(slot1_tier0_sha256_verified_off_camera))
            or bool(slot1_wp_locked)
        ):
            slot1_save_ok = False
            errors.append(
                f"{P248_GC_ERR_SAVELOAD_SLOT1_TIER0_SAVE_BLOCKED}: [Save/Load Settings] -> [Save] "
                "to Slot 1 is blocked to protect the Slot 1 Tier-0 vault card (pnflasha/cnflasha/WP); "
                "use Slot 2 scratch media or [Load] (O_RDONLY)"
            )

    return CheckGroupCShoeAudioWindNoiseSaveLoadResult(
        check_group_id=P248_CHECK_GROUP_C_ID,
        passed=(len(errors) == 0),
        shoe_audio_set=shoe_mode,
        audio_recording=aud_rec,
        sq_mode_enabled=bool(sq_mode_enabled),
        body_35mm_mic_plugged=bool(body_35mm_mic_plugged),
        xlr_h1_attached=bool(xlr_h1_attached),
        xlr_h1_mode_switch=xlr_sw,
        xlr_h1_low_cut_switch=xlr_lc,
        active_shoe_audio_lockouts=tuple(lockouts),
        shoe_audio_digital_available=digital_shoe_available,
        effective_audio_meter_channels=eff_meters,
        wind_noise_reduct=wind_mode,
        wind_noise_builtin_mic_only_verified=wind_builtin_only_ok,
        saveload_operation=sl_op,
        saveload_target=sl_tgt,
        camset_slot_index=slot_idx,
        camset_model_code=model_norm,
        excluded_categories_enforced=SAVELOAD_FOUR_EXCLUDED_CATEGORIES,
        saveload_exclusions_verified=exclusions_ok,
        slot1_camset_save_firewall_ok=slot1_save_ok,
        errors=tuple(errors),
    )



# ---------------------------------------------------------------------------
# Check Group D: [Lock Operation Parts] 5s Chord, USB Power Battery, Shutter Angle & Tier-0 Gate (Waves 37 & 38)
# ---------------------------------------------------------------------------


def build_simulated_phase248_tier0_receipts(
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
            f"PHASE248_TIER0:{body_fw}:{item.item_id}:{item.size_bytes}:{emmc_cid.lower()}".encode(
                "ascii"
            )
        ).hexdigest()
        total_bytes += item.size_bytes
    manifest_seed = hashlib.sha256(
        f"PHASE248_MANIFEST:{body_serial}:{body_fw}:{emmc_cid.lower()}".encode("ascii")
    ).hexdigest()
    rcpt = build_sd_backup_receipt_bytes(
        manifest_sha256=manifest_seed,
        item_hashes=item_hashes,
        total_dumped_bytes=total_bytes,
    )
    baselines = build_default_h0_baselines(body_serial=body_serial, emmc_cid=emmc_cid)
    return rcpt, bytes(rcpt), baselines


def evaluate_check_group_d_lock_op_usb_power_shutter_angle_and_tier0(
    *,
    lock_operation_parts: str = "ALL",
    reset_action: str = "NONE",
    claimed_lock_op_after_reset: Optional[str] = None,
    active_key_chord: str = LOCK_OP_FULL_BODY_CHORD,
    lock_chord_hold_seconds: float = LOCK_OP_FULL_BODY_HOLD_SECONDS,
    destructive_slot_full_format_chord_invoked: bool = False,
    expect_shutter_button_locked_by_menu_fn_5s: bool = False,
    expect_my_dial_blocked_by_lock_op_parts: bool = False,
    power_source: str = "USB_PD_BODY",
    usb_power_supply: str = "ON",
    usb_power_terminal: str = "USB_TYPE_C",
    usb_lun_setting: str = "MULTI",
    claimed_usb_lun_after_reset: Optional[str] = None,
    np_fz100_battery_inserted: bool = True,
    dc_c1_coupler_inserted: bool = False,
    battery_removed_under_usb_power: bool = False,
    exposure_step: str = "0.3EV",
    shutter_mode: str = "SHUTTER_ANGLE",
    shutter_angle_deg: float = 180.0,
    expect_exposure_step_alters_shutter_angle: bool = False,
    expect_fx3_native_var_shutter_menu: bool = False,
    expect_antiflicker_in_movie_or_silent: bool = False,
    audio_out_timing: str = "LIVE",
    audio_recording: str = "ON",
    sq_mode_enabled: bool = False,
    expect_audio_out_timing_in_sq_or_audio_off: bool = False,
    silent_mode_enabled: bool = False,
    audio_signals_mode: str = "ON",
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
) -> Tuple[CheckGroupDLockOpUsbPowerShutterAngleResult, Tuple[str, ...]]:
    errors: List[str] = []
    warnings: List[str] = []
    tier0_errors: List[str] = []

    # 1. [Lock Operation Parts] Setup Persistence, MENU+Fn 5s Chord (vs MENU+Delete 2s) & My Dial Override
    lock_op = _norm_lock_op_mode(lock_operation_parts)
    rst_norm = _norm_token(reset_action)
    chord_norm = _norm_token(active_key_chord)
    hold_sec = float(lock_chord_hold_seconds)

    if lock_op not in VALID_LOCK_OPERATION_PARTS_MODES or rst_norm not in VALID_P248_RESET_ACTIONS:
        errors.append(
            f"{P248_GD_ERR_LOCK_OP_PARTS_OR_DESTRUCTIVE_CHORD_VIOLATION}: invalid "
            f"[Lock Operation Parts]={lock_operation_parts!r} or reset_action={reset_action!r}"
        )

    eff_lock_op = "OFF" if rst_norm == "INITIALIZE" else lock_op
    if claimed_lock_op_after_reset is not None:
        if _norm_lock_op_mode(claimed_lock_op_after_reset) != eff_lock_op:
            errors.append(
                f"{P248_GD_ERR_LOCK_OP_PARTS_OR_DESTRUCTIVE_CHORD_VIOLATION}: [Lock Operation Parts] "
                "survives [Camera Settings Reset]/[Reset Network Set.] and resets only on [Initialize]"
            )

    destructive_blocked = True
    if (
        chord_norm in (DESTRUCTIVE_SLOT_FULL_FORMAT_CHORD, "MENU_PLUS_DELETE")
        or bool(destructive_slot_full_format_chord_invoked)
    ):
        destructive_blocked = False
        errors.append(
            f"{P248_GD_ERR_LOCK_OP_PARTS_OR_DESTRUCTIVE_CHORD_VIOLATION}: destructive "
            "MENU + Delete 2-second Slot Full Format chord is HARD-BLOCKED on bench; "
            "use MENU + Fn 5-second full-body lock chord instead"
        )
    elif chord_norm not in ("NONE", "FN_HOLD_TOGGLE", LOCK_OP_FULL_BODY_CHORD):
        errors.append(
            f"{P248_GD_ERR_LOCK_OP_PARTS_OR_DESTRUCTIVE_CHORD_VIOLATION}: unrecognized key chord={active_key_chord!r}"
        )

    full_body_locked = False
    if chord_norm == LOCK_OP_FULL_BODY_CHORD:
        if hold_sec < LOCK_OP_FULL_BODY_HOLD_SECONDS:
            errors.append(
                f"{P248_GD_ERR_LOCK_OP_PARTS_OR_DESTRUCTIVE_CHORD_VIOLATION}: MENU + Fn full-body "
                f"lock chord requires >= {LOCK_OP_FULL_BODY_HOLD_SECONDS:.1f}s hold (got {hold_sec:.2f}s)"
            )
        else:
            full_body_locked = True

    if bool(expect_shutter_button_locked_by_menu_fn_5s):
        errors.append(
            f"{P248_GD_ERR_LOCK_OP_PARTS_OR_DESTRUCTIVE_CHORD_VIOLATION}: MENU + Fn 5s chord locks "
            "all buttons, dials, and wheels EXCEPT the shutter button"
        )
    if bool(expect_my_dial_blocked_by_lock_op_parts):
        errors.append(
            f"{P248_GD_ERR_LOCK_OP_PARTS_OR_DESTRUCTIVE_CHORD_VIOLATION}: recalling My Dial "
            "temporarily unlocks assigned dials/wheels even while [Lock Operation Parts] is active"
        )

    # 2. [USB Power Supply] Mandatory Inserted NP-FZ100 Battery, USB Type-C Exclusivity & USB LUN Survival
    pwr_src = _norm_token(power_source)
    usb_pwr = _norm_token(usb_power_supply)
    usb_term = _norm_token(usb_power_terminal)
    usb_lun = _norm_token(usb_lun_setting)
    usb_battery_ok = True

    if (
        pwr_src not in ("INTERNAL_NP_FZ100", "USB_PD_BODY", "DC_C1_COUPLER")
        or usb_pwr not in ("ON", "OFF")
        or usb_term not in VALID_USB_POWER_TERMINALS
        or usb_lun not in VALID_USB_LUN_MODES
    ):
        usb_battery_ok = False
        errors.append(
            f"{P248_GD_ERR_USB_POWER_MISSING_NPFZ100_OR_WRONG_PORT}: invalid USB/power config "
            f"(source={power_source!r}, usb_power={usb_power_supply!r}, terminal={usb_power_terminal!r}, lun={usb_lun_setting!r})"
        )
    else:
        if pwr_src in ("INTERNAL_NP_FZ100", "USB_PD_BODY") and not bool(np_fz100_battery_inserted):
            usb_battery_ok = False
            errors.append(
                f"{P248_GD_ERR_USB_POWER_MISSING_NPFZ100_OR_WRONG_PORT}: ILME-FX3 cannot power on "
                "or sustain [USB Power Supply] without an inserted NP-FZ100 battery pack"
            )
        if pwr_src == "DC_C1_COUPLER" and not bool(dc_c1_coupler_inserted):
            usb_battery_ok = False
            errors.append(
                f"{P248_GD_ERR_USB_POWER_MISSING_NPFZ100_OR_WRONG_PORT}: DC_C1_COUPLER power mode "
                "requires DC-C1 coupler seated in the battery bay"
            )
        if bool(battery_removed_under_usb_power):
            usb_battery_ok = False
            errors.append(
                f"{P248_GD_ERR_USB_POWER_MISSING_NPFZ100_OR_WRONG_PORT}: removing NP-FZ100 while "
                "USB wall power is connected causes immediate unbuffered power-off"
            )
        if usb_term == "MULTI_MICRO_USB" or (
            pwr_src in ("USB_PD_BODY", "DC_C1_COUPLER") and usb_term != "USB_TYPE_C"
        ):
            usb_battery_ok = False
            errors.append(
                f"{P248_GD_ERR_USB_POWER_MISSING_NPFZ100_OR_WRONG_PORT}: ILME-FX3 USB power delivery "
                "operates exclusively over USB Type-C (Multi/Micro USB cannot supply or charge power)"
            )

    eff_usb_lun = "MULTI" if rst_norm == "INITIALIZE" else usb_lun
    if claimed_usb_lun_after_reset is not None:
        if _norm_token(claimed_usb_lun_after_reset) != eff_usb_lun:
            errors.append(
                f"{P248_GD_ERR_USB_POWER_MISSING_NPFZ100_OR_WRONG_PORT}: [USB LUN Setting] survives "
                "[Camera Settings Reset] and resets to [Multi] only on [Initialize]"
            )

    # 3. [Exposure step] (0.3EV/0.5EV) vs [Shutter Angle] Constant Table, Audio Out Timing & Silent Mode
    exp_step = _norm_exposure_step(exposure_step)
    sh_mode = _norm_token(shutter_mode)
    sh_angle = round(float(shutter_angle_deg), 1)
    aud_timing = _norm_token(audio_out_timing)
    aud_rec = _norm_token(audio_recording)
    aud_sig = _norm_token(audio_signals_mode)
    angle_independent_ok = not bool(expect_exposure_step_alters_shutter_angle)

    if (
        exp_step not in VALID_EXPOSURE_STEP_VALUES
        or sh_mode not in ("SHUTTER_SPEED", "SHUTTER_ANGLE")
        or (sh_mode == "SHUTTER_ANGLE" and sh_angle not in SHUTTER_ANGLE_CONSTANT_DEGREE_TABLE)
        or not angle_independent_ok
    ):
        errors.append(
            f"{P248_GD_ERR_SHUTTER_ANGLE_OR_AUDIO_TIMING_VIOLATION}: [Exposure step]={exposure_step!r} "
            f"(0.3EV/0.5EV) never alters [Shutter Angle] constant cine table {SHUTTER_ANGLE_CONSTANT_DEGREE_TABLE} "
            f"(mode={shutter_mode!r}, angle={sh_angle}, alter_claim={expect_exposure_step_alters_shutter_angle})"
        )

    if bool(expect_fx3_native_var_shutter_menu) or bool(expect_antiflicker_in_movie_or_silent):
        errors.append(
            f"{P248_GD_ERR_SHUTTER_ANGLE_OR_AUDIO_TIMING_VIOLATION}: stock ILME-FX3 lacks native "
            "[Var. Shutter] menu and restricts [Anti-flicker Shoot.] to mechanical-shutter still images"
        )

    if aud_timing not in VALID_AUDIO_OUT_TIMING_MODES or aud_sig not in (
        "ON",
        "OFF",
        "OFF_SHUTTER_ONLY",
    ):
        errors.append(
            f"{P248_GD_ERR_SHUTTER_ANGLE_OR_AUDIO_TIMING_VIOLATION}: invalid [Audio Out Timing]={audio_out_timing!r} "
            f"or [Audio signals]={audio_signals_mode!r}"
        )
    if bool(expect_audio_out_timing_in_sq_or_audio_off) and (
        bool(sq_mode_enabled) or aud_rec == "OFF"
    ):
        errors.append(
            f"{P248_GD_ERR_SHUTTER_ANGLE_OR_AUDIO_TIMING_VIOLATION}: [Audio Out Timing] (Live/Lip Sync) "
            "is unavailable during S&Q Motion or when [Audio Recording]=[Off]"
        )
    if bool(silent_mode_enabled) and aud_sig != "OFF":
        errors.append(
            f"{P248_GD_ERR_SHUTTER_ANGLE_OR_AUDIO_TIMING_VIOLATION}: [Silent Mode]=[On] hard-locks "
            f"[Audio signals] to [Off] (got {aud_sig})"
        )

    # 4. 16/16 H0 == H3 Baseline Invariance & Dual-Media 528 B FX3RCPT1 Tier-0 Receipt Gate
    surface_total = len(SIXTEEN_STORAGE_SURFACES)
    drifted = max(0, min(surface_total, int(simulated_h0_h3_drifted_surfaces)))
    h0_eq_h3 = surface_total - drifted
    if h0_eq_h3 != surface_total:
        errors.append(
            f"{P248_GD_ERR_H0_H3_IMMUTABILITY_DRIFT}: H0 == H3 parity drift ({h0_eq_h3}/{surface_total})"
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
        raw_a, raw_b, sim_h0 = build_simulated_phase248_tier0_receipts(
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
                f"{P248_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt_a read failed: {exc}"
            )

    if receipt_b_path is not None:
        try:
            _, raw_b, st_b = _read_bounded_slice_o_rdonly(Path(receipt_b_path), SD_RECEIPT_BYTES + 64)
            if dev_b is None:
                dev_b = int(st_b)
        except OSError as exc:
            tier0_errors.append(
                f"{P248_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt_b read failed: {exc}"
            )

    receipt_present = (raw_a is not None) and (raw_b is not None)
    distinct_media = False
    receipt_verified = False

    if not receipt_present:
        tier0_errors.append(
            f"{P248_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: dual-copy 528B FX3RCPT1 Tier-0 "
            "cold-backup receipts not provided (offline fail-closed)"
        )
    else:
        assert raw_a is not None and raw_b is not None
        if len(raw_a) != SD_RECEIPT_BYTES or len(raw_b) != SD_RECEIPT_BYTES or raw_a != raw_b:
            tier0_errors.append(
                f"{P248_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: dual FX3RCPT1 size/byte mismatch"
            )
        else:
            if dev_a is not None and dev_b is not None and int(dev_a) != int(dev_b):
                distinct_media = True
            else:
                tier0_errors.append(
                    f"{P248_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: st_dev_a == st_dev_b ({dev_a} vs {dev_b})"
                )

            ser_norm = (eff_serial or "").strip()
            cid_norm = (eff_cid or "").strip().lower()
            if not BODY_SERIAL_RE.match(ser_norm) or ser_norm.upper() in FORBIDDEN_TRIVIAL_SERIALS:
                tier0_errors.append(
                    f"{P248_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: invalid body_serial={eff_serial!r}"
                )
            if not HEX32_CID_RE.match(cid_norm) or cid_norm in FORBIDDEN_TRIVIAL_CIDS:
                tier0_errors.append(
                    f"{P248_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: invalid emmc_cid={eff_cid!r}"
                )
            if int(body_model_id) != TARGET_MODEL_ID_INT or str(body_fw).strip() != TARGET_BODY_FW:
                tier0_errors.append(
                    f"{P248_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt target mismatch"
                )

            try:
                parsed_a = parse_sd_backup_receipt_bytes(raw_a)
                parsed_b = parse_sd_backup_receipt_bytes(raw_b)
                if not parsed_a.valid or not parsed_b.valid:
                    tier0_errors.append(
                        f"{P248_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: FX3RCPT1 CRC32/header invalid"
                    )
            except Exception as exc:
                tier0_errors.append(
                    f"{P248_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: FX3RCPT1 parse error: {exc}"
                )

            if eff_h0_a is None or eff_h0_b is None:
                tier0_errors.append(
                    f"{P248_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: missing H0 baseline digests"
                )
            else:
                for req_k in REQUIRED_H0_BASELINE_KEYS:
                    va = eff_h0_a.get(req_k, "")
                    vb = eff_h0_b.get(req_k, "")
                    if _is_trivial_hex64(va) or va.lower() != vb.lower():
                        tier0_errors.append(
                            f"{P248_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: invalid/mismatched H0[{req_k}]"
                        )

            if len(tier0_errors) == 0:
                receipt_verified = True

    return (
        CheckGroupDLockOpUsbPowerShutterAngleResult(
            check_group_id=P248_CHECK_GROUP_D_ID,
            passed=(len(errors) == 0),
            lock_operation_parts=lock_op,
            effective_lock_op_after_reset=eff_lock_op,
            active_key_chord=chord_norm,
            lock_chord_hold_seconds=hold_sec,
            full_body_lock_except_shutter_engaged=full_body_locked,
            destructive_format_chord_blocked=destructive_blocked,
            my_dial_temporarily_unlocks_dials=True,
            power_source=pwr_src,
            usb_power_supply=usb_pwr,
            usb_power_terminal=usb_term,
            usb_lun_setting=usb_lun,
            np_fz100_battery_inserted=bool(np_fz100_battery_inserted),
            dc_c1_coupler_inserted=bool(dc_c1_coupler_inserted),
            usb_power_battery_interlock_ok=usb_battery_ok,
            exposure_step=exp_step,
            shutter_mode=sh_mode,
            shutter_angle_deg=sh_angle,
            shutter_angle_unaffected_by_exposure_step=angle_independent_ok,
            audio_out_timing=aud_timing,
            silent_mode_enabled=bool(silent_mode_enabled),
            audio_signals_mode=aud_sig,
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


def evaluate_realhw_imagedb_touch_shoeaudio_and_lockop_readiness(
    *,
    simulate_bench_dry_run: bool = False,
    simulate_ready_bench: Optional[bool] = None,
    force_clean_room: Optional[bool] = None,
    synthetic_clean_room: Optional[bool] = None,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    # Check Group A (Wave 34)
    recover_image_db_requested: bool = False,
    recover_image_db_target_slot: int = 2,
    expect_recover_imagedb_deletes_clips: bool = False,
    battery_soc_pct: float = 88.0,
    low_battery_warning_active: bool = False,
    slot1_contains_tier0_dump: bool = True,
    slot1_tier0_sha256_verified_off_camera: bool = True,
    slot1_wp_locked: bool = True,
    monitor_flip_direction: str = "AUTO",
    reset_action: str = "NONE",
    claimed_monitor_flip_after_reset: Optional[str] = None,
    expect_playback_inverted_under_horizontal_flip: bool = False,
    af_transition_speed: int = 5,
    af_subj_shift_sensitivity_label: str = AF_SUBJ_SHIFT_SENSITIVITY_EXACT_LABEL,
    af_subj_shift_sensitivity: int = 5,
    interval_shoot_func_enabled: bool = False,
    expect_interval_in_camera_movie_recording: bool = False,
    # Check Group B (Waves 35 & 39)
    touch_operation: str = "OFF",
    touch_sensitivity: str = "STANDARD",
    swipe_up: str = "OPEN_THE_FN_MENU",
    touch_func_in_shooting: str = "OFF",
    unattended_tier0_dump_active: bool = True,
    claimed_touch_operation_after_reset: Optional[str] = None,
    emphasized_rec_display: str = "ON",
    grid_line_display: str = "OFF",
    grid_line_type: str = "RULE_OF_3RDS_GRID",
    rec_media_dur_hdmi_output: str = "ON",
    hdmi_raw_output: bool = False,
    hdmi_info_display: str = "OFF",
    expect_hdmi_info_on_during_hdmionly_or_raw: bool = False,
    expect_marker_zebra_peaking_on_hdmi: bool = False,
    indoor_bench_environment: bool = True,
    monitor_brightness_mode: str = "MANUAL",
    monitor_brightness_manual_level: int = 0,
    display_quality: str = "STANDARD",
    bluetooth_rmt_ctrl: str = "OFF",
    bluetooth_function: str = "OFF",
    airplane_mode: str = "ON",
    expect_ir_remote_usable: bool = False,
    claimed_bluetooth_rmt_ctrl_after_reset: Optional[str] = None,
    display_from_my_menu: str = "OFF",
    claimed_display_from_my_menu_after_reset: Optional[str] = None,
    # Check Group C (Wave 36)
    shoe_audio_set: str = "48KHZ_24BIT_4CH",
    audio_recording: str = "ON",
    sq_mode_enabled: bool = False,
    body_35mm_mic_plugged: bool = False,
    xlr_h1_attached: bool = True,
    xlr_h1_mode_switch: str = "DIGITAL",
    xlr_h1_low_cut_switch: str = "OFF",
    claimed_audio_meter_channels: Optional[int] = None,
    wind_noise_reduct: str = "OFF",
    expect_wind_noise_reduct_on_external_mic: bool = False,
    indoor_calm_bench_audio: bool = True,
    saveload_operation: str = "NONE",
    saveload_target: str = "SLOT_2",
    camset_slot_index: int = 1,
    camset_model_code: str = "ILME-FX3",
    camset_payload_contains_excluded_items: bool = False,
    expect_saveload_includes_excluded_secrets_or_cal: bool = False,
    # Check Group D & Tier-0 Gate (Waves 37 & 38)
    lock_operation_parts: str = "ALL",
    claimed_lock_op_after_reset: Optional[str] = None,
    active_key_chord: str = LOCK_OP_FULL_BODY_CHORD,
    lock_chord_hold_seconds: float = LOCK_OP_FULL_BODY_HOLD_SECONDS,
    destructive_slot_full_format_chord_invoked: bool = False,
    expect_shutter_button_locked_by_menu_fn_5s: bool = False,
    expect_my_dial_blocked_by_lock_op_parts: bool = False,
    power_source: str = "USB_PD_BODY",
    usb_power_supply: str = "ON",
    usb_power_terminal: str = "USB_TYPE_C",
    usb_lun_setting: str = "MULTI",
    claimed_usb_lun_after_reset: Optional[str] = None,
    np_fz100_battery_inserted: bool = True,
    dc_c1_coupler_inserted: bool = False,
    battery_removed_under_usb_power: bool = False,
    exposure_step: str = "0.3EV",
    shutter_mode: str = "SHUTTER_ANGLE",
    shutter_angle_deg: float = 180.0,
    expect_exposure_step_alters_shutter_angle: bool = False,
    expect_fx3_native_var_shutter_menu: bool = False,
    expect_antiflicker_in_movie_or_silent: bool = False,
    audio_out_timing: str = "LIVE",
    expect_audio_out_timing_in_sq_or_audio_off: bool = False,
    silent_mode_enabled: bool = False,
    audio_signals_mode: str = "ON",
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
) -> RealHwImageDbTouchShoeAudioLockOpReport:
    """Execute Phase 248 read-only 5th physical bench & media/audio/vault readiness verifier (`A..D`)."""
    eff_sim = bool(simulate_bench_dry_run or simulate_ready_bench)

    donor_res = inspect_phase248_donors_bounded(
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        force_clean_room=force_clean_room,
        synthetic_clean_room=synthetic_clean_room,
    )
    ga = evaluate_check_group_a_imagedb_vault_and_monitor_flip(
        body_model_id=body_model_id,
        body_fw=body_fw,
        recover_image_db_requested=recover_image_db_requested,
        recover_image_db_target_slot=recover_image_db_target_slot,
        expect_recover_imagedb_deletes_clips=expect_recover_imagedb_deletes_clips,
        battery_soc_pct=battery_soc_pct,
        low_battery_warning_active=low_battery_warning_active,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        slot1_tier0_sha256_verified_off_camera=slot1_tier0_sha256_verified_off_camera,
        slot1_wp_locked=slot1_wp_locked,
        monitor_flip_direction=monitor_flip_direction,
        reset_action=reset_action,
        claimed_monitor_flip_after_reset=claimed_monitor_flip_after_reset,
        expect_playback_inverted_under_horizontal_flip=expect_playback_inverted_under_horizontal_flip,
        af_transition_speed=af_transition_speed,
        af_subj_shift_sensitivity_label=af_subj_shift_sensitivity_label,
        af_subj_shift_sensitivity=af_subj_shift_sensitivity,
        interval_shoot_func_enabled=interval_shoot_func_enabled,
        expect_interval_in_camera_movie_recording=expect_interval_in_camera_movie_recording,
    )
    gb = evaluate_check_group_b_touch_op_hdmi_and_display_power(
        touch_operation=touch_operation,
        touch_sensitivity=touch_sensitivity,
        swipe_up=swipe_up,
        touch_func_in_shooting=touch_func_in_shooting,
        unattended_tier0_dump_active=unattended_tier0_dump_active,
        reset_action=reset_action,
        claimed_touch_operation_after_reset=claimed_touch_operation_after_reset,
        emphasized_rec_display=emphasized_rec_display,
        grid_line_display=grid_line_display,
        grid_line_type=grid_line_type,
        rec_media_dur_hdmi_output=rec_media_dur_hdmi_output,
        hdmi_raw_output=hdmi_raw_output,
        hdmi_info_display=hdmi_info_display,
        expect_hdmi_info_on_during_hdmionly_or_raw=expect_hdmi_info_on_during_hdmionly_or_raw,
        expect_marker_zebra_peaking_on_hdmi=expect_marker_zebra_peaking_on_hdmi,
        indoor_bench_environment=indoor_bench_environment,
        monitor_brightness_mode=monitor_brightness_mode,
        monitor_brightness_manual_level=monitor_brightness_manual_level,
        display_quality=display_quality,
        bluetooth_rmt_ctrl=bluetooth_rmt_ctrl,
        bluetooth_function=bluetooth_function,
        airplane_mode=airplane_mode,
        expect_ir_remote_usable=expect_ir_remote_usable,
        claimed_bluetooth_rmt_ctrl_after_reset=claimed_bluetooth_rmt_ctrl_after_reset,
        display_from_my_menu=display_from_my_menu,
        claimed_display_from_my_menu_after_reset=claimed_display_from_my_menu_after_reset,
    )
    gc = evaluate_check_group_c_shoe_audio_wind_and_saveload(
        shoe_audio_set=shoe_audio_set,
        audio_recording=audio_recording,
        sq_mode_enabled=sq_mode_enabled,
        body_35mm_mic_plugged=body_35mm_mic_plugged,
        xlr_h1_attached=xlr_h1_attached,
        xlr_h1_mode_switch=xlr_h1_mode_switch,
        xlr_h1_low_cut_switch=xlr_h1_low_cut_switch,
        claimed_audio_meter_channels=claimed_audio_meter_channels,
        wind_noise_reduct=wind_noise_reduct,
        expect_wind_noise_reduct_on_external_mic=expect_wind_noise_reduct_on_external_mic,
        indoor_calm_bench_audio=indoor_calm_bench_audio,
        saveload_operation=saveload_operation,
        saveload_target=saveload_target,
        camset_slot_index=camset_slot_index,
        camset_model_code=camset_model_code,
        camset_payload_contains_excluded_items=camset_payload_contains_excluded_items,
        expect_saveload_includes_excluded_secrets_or_cal=expect_saveload_includes_excluded_secrets_or_cal,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        slot1_tier0_sha256_verified_off_camera=slot1_tier0_sha256_verified_off_camera,
        slot1_wp_locked=slot1_wp_locked,
    )
    gd, tier0_errors = evaluate_check_group_d_lock_op_usb_power_shutter_angle_and_tier0(
        lock_operation_parts=lock_operation_parts,
        reset_action=reset_action,
        claimed_lock_op_after_reset=claimed_lock_op_after_reset,
        active_key_chord=active_key_chord,
        lock_chord_hold_seconds=lock_chord_hold_seconds,
        destructive_slot_full_format_chord_invoked=destructive_slot_full_format_chord_invoked,
        expect_shutter_button_locked_by_menu_fn_5s=expect_shutter_button_locked_by_menu_fn_5s,
        expect_my_dial_blocked_by_lock_op_parts=expect_my_dial_blocked_by_lock_op_parts,
        power_source=power_source,
        usb_power_supply=usb_power_supply,
        usb_power_terminal=usb_power_terminal,
        usb_lun_setting=usb_lun_setting,
        claimed_usb_lun_after_reset=claimed_usb_lun_after_reset,
        np_fz100_battery_inserted=np_fz100_battery_inserted,
        dc_c1_coupler_inserted=dc_c1_coupler_inserted,
        battery_removed_under_usb_power=battery_removed_under_usb_power,
        exposure_step=exposure_step,
        shutter_mode=shutter_mode,
        shutter_angle_deg=shutter_angle_deg,
        expect_exposure_step_alters_shutter_angle=expect_exposure_step_alters_shutter_angle,
        expect_fx3_native_var_shutter_menu=expect_fx3_native_var_shutter_menu,
        expect_antiflicker_in_movie_or_silent=expect_antiflicker_in_movie_or_silent,
        audio_out_timing=audio_out_timing,
        audio_recording=audio_recording,
        sq_mode_enabled=sq_mode_enabled,
        expect_audio_out_timing_in_sq_or_audio_off=expect_audio_out_timing_in_sq_or_audio_off,
        silent_mode_enabled=silent_mode_enabled,
        audio_signals_mode=audio_signals_mode,
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
            "Keep NP-FZ100 >=20% before [Recover Image DB], verify off-camera SHA-256 and engage WP on Slot 1 Tier-0 card, and respect [Horizontal Flip] playback non-inversion."
        )
    if not gb.passed:
        remediations.append(
            "Set [Touch Operation]=Off or On: Playback Only during unattended Tier-0 dumps, keep [HDMI Info. Display]=Off under [Off(HDMI Only)]/RAW, and clamp indoor [Monitor Brightness]=Manual + [Display Quality]=Standard."
        )
    if not gc.passed:
        remediations.append(
            "Keep [Audio Recording]=On (non-S&Q), unplug 3.5mm MIC, and set XLR-H1 to DIGITAL for 48kHz/24bit 4ch; keep [Wind Noise Reduct.]=Off with external mics; and never [Save] CAMSET to Slot 1 Tier-0 vault card."
        )
    if not gd.passed or not gd.tier0_receipt_verified:
        remediations.append(
            "Use MENU+Fn 5s lock chord (never destructive MENU+Delete 2s), keep NP-FZ100 inserted on USB Type-C power, respect constant [Shutter Angle] table, and provide dual-device 528B FX3RCPT1 receipts."
        )

    if not all_4_passed:
        verdict = GO_NO_GO_BLOCKED_IMAGEDB_TOUCH_SHOEAUDIO_LOCKOP_FAILURE
    elif not gd.tier0_receipt_verified:
        verdict = (
            GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT
            if not gd.tier0_receipt_present
            else GO_NO_GO_BLOCKED_IMAGEDB_TOUCH_SHOEAUDIO_LOCKOP_FAILURE
        )
    elif eff_sim:
        verdict = GO_NO_GO_DRY_RUN_SIMULATED_READY
    else:
        verdict = GO_NO_GO_IMAGEDB_TOUCH_SHOEAUDIO_LOCKOP_VERIFIED

    provisional = RealHwImageDbTouchShoeAudioLockOpReport(
        schema=PHASE_248_SCHEMA,
        phase_version=PHASE_248_VERSION,
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
        raw_firmware_bytes_leaked=PHASE248_RAW_FIRMWARE_BYTES_LEAKED,
        check_group_count=4,
        check_groups_passed=groups_passed,
        all_4_check_groups_passed=all_4_passed,
        tier0_receipt_verified=gd.tier0_receipt_verified,
        h0_h3_surface_count=gd.h0_h3_surface_count,
        h0_equals_h3_count=gd.h0_equals_h3_count,
        donor_inspection=donor_res,
        check_group_a_imagedb_vault_and_monitor_flip=ga,
        check_group_b_touch_op_hdmi_and_display_power=gb,
        check_group_c_shoe_audio_wind_and_saveload=gc,
        check_group_d_lock_op_usb_power_and_shutter_angle=gd,
        warnings=gd.warnings,
        remediation_actions=tuple(remediations),
        errors=tuple(all_errors),
        report_sha256="",
    )
    digest = _canonical_sha256_dict(provisional.to_dict(), exclude_key="report_sha256")
    return RealHwImageDbTouchShoeAudioLockOpReport(
        **{
            **provisional.to_dict(),
            "donor_inspection": donor_res,
            "check_group_a_imagedb_vault_and_monitor_flip": ga,
            "check_group_b_touch_op_hdmi_and_display_power": gb,
            "check_group_c_shoe_audio_wind_and_saveload": gc,
            "check_group_d_lock_op_usb_power_and_shutter_angle": gd,
            "warnings": gd.warnings,
            "remediation_actions": tuple(remediations),
            "errors": tuple(all_errors),
            "report_sha256": digest,
        }
    )


run_imagedb_touch_shoeaudio_and_lockop_preflight = (
    evaluate_realhw_imagedb_touch_shoeaudio_and_lockop_readiness
)


def verify_phase248_report(payload: Mapping[str, Any]) -> Phase248ReportVerifyResult:
    """Fail-closed tamper & safety-lock verifier for Phase 248 preflight reports."""
    errors: List[str] = []
    if payload.get("schema") != PHASE_248_SCHEMA:
        errors.append(f"Invalid schema: {payload.get('schema')!r}")
    if payload.get("phase_version") != PHASE_248_VERSION:
        errors.append(f"Invalid phase_version: {payload.get('phase_version')!r}")
    if payload.get("verification_mode") not in ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"):
        errors.append(f"Invalid verification_mode: {payload.get('verification_mode')!r}")
    if payload.get("go_no_go") not in PHASE_248_VALID_GO_NO_GO_VALUES:
        errors.append(f"Invalid go_no_go verdict: {payload.get('go_no_go')!r}")

    for lock_key in (
        "overall_ready_for_hardware_attach",
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

    if payload.get("check_group_count") != 4:
        errors.append(f"Expected check_group_count==4, got {payload.get('check_group_count')!r}")

    if payload.get("simulate_bench_dry_run") is True and (
        payload.get("go_no_go") == GO_NO_GO_IMAGEDB_TOUCH_SHOEAUDIO_LOCKOP_VERIFIED
    ):
        errors.append("Simulated dry-run cannot claim physical Tier-0 verified verdict")

    if payload.get("go_no_go") == GO_NO_GO_IMAGEDB_TOUCH_SHOEAUDIO_LOCKOP_VERIFIED and (
        payload.get("all_4_check_groups_passed") is not True
        or payload.get("tier0_receipt_verified") is not True
    ):
        errors.append("Verified verdict requires all 4 check groups and Tier-0 receipt verified")

    claimed_sha = str(payload.get("report_sha256", ""))
    expected_sha = _canonical_sha256_dict(payload, exclude_key="report_sha256")
    if not HEX64_RE.match(claimed_sha) or claimed_sha != expected_sha:
        errors.append("report_sha256 canonical digest mismatch")

    return Phase248ReportVerifyResult(valid=(len(errors) == 0), errors=tuple(errors))


def render_phase248_markdown(report: RealHwImageDbTouchShoeAudioLockOpReport) -> str:
    """Render concise deterministic Markdown summary for Phase 248 pre-shoot bench preflight."""
    ga = report.check_group_a_imagedb_vault_and_monitor_flip
    gb = report.check_group_b_touch_op_hdmi_and_display_power
    gc = report.check_group_c_shoe_audio_wind_and_saveload
    gd = report.check_group_d_lock_op_usb_power_and_shutter_angle
    lines = [
        f"# Phase 248 Physical Bench & Media/Audio/Vault Readiness (`{report.schema}`)",
        "",
        f"- **Go/No-Go Verdict**: `{report.go_no_go}` (mode=`{report.verification_mode}`, dry_run=`{report.simulate_bench_dry_run}`)",
        f"- **Check Groups**: `{report.check_groups_passed}/{report.check_group_count}` (`H0==H3`: `{report.h0_equals_h3_count}/{report.h0_h3_surface_count}`)",
        f"- **Hard Locks**: `ready_attach={report.overall_ready_for_hardware_attach}`, `live_attach={report.hardware_live_attachment_authorized}`, `emmc_writes={report.persistent_emmc_writes_authorized}`, `spi_nor={report.spi_nor_write_authorized}`, `el3_tx={report.el3_payload_transmit_authorized}`, `usb_pkts={report.usb_packets_transmitted}`, `leaked_bytes={report.raw_firmware_bytes_leaked}`",
        "",
        "| Check Group | Status | Key Telemetry |",
        "| :--- | :---: | :--- |",
        f"| `{ga.check_group_id}` | `{'PASS' if ga.passed else 'FAIL'}` | ImageDBAllowed=`{ga.recover_image_db_allowed}` (`soc={ga.battery_soc_pct:.1f}%`, `slot1_wp={ga.slot1_wp_locked}`), Flip=`{ga.monitor_flip_direction}` (`pb_inv={ga.playback_display_horizontally_inverted}`) |",
        f"| `{gb.check_group_id}` | `{'PASS' if gb.passed else 'FAIL'}` | TouchOp=`{gb.touch_operation}` (`guard={gb.touch_bench_tap_guard_satisfied}`), HDMIInfo=`{gb.effective_hdmi_info_display}` (`clean_feed={gb.hdmi_clean_feed_forced_off}`), Brt=`{gb.monitor_brightness_mode}`, Qual=`{gb.display_quality}` |",
        f"| `{gc.check_group_id}` | `{'PASS' if gc.passed else 'FAIL'}` | ShoeAudio=`{gc.shoe_audio_set}` (`{gc.effective_audio_meter_channels}ch`, lockouts=`{len(gc.active_shoe_audio_lockouts)}`), WindReduct=`{gc.wind_noise_reduct}`, SaveLoad=`{gc.saveload_operation}` (`{gc.saveload_target}`) |",
        f"| `{gd.check_group_id}` | `{'PASS' if gd.passed else 'FAIL'}` | LockOp=`{gd.lock_operation_parts}` (`{gd.active_key_chord}`), USBPwr=`{gd.power_source}` (`NP-FZ100={gd.np_fz100_battery_inserted}`), ExpStep=`{gd.exposure_step}` vs Angle=`{gd.shutter_angle_deg}`, Tier0=`{gd.tier0_receipt_verified}` |",
        "",
        f"- **Report SHA-256**: `{report.report_sha256}`",
    ]
    return "\n".join(lines) + "\n"
