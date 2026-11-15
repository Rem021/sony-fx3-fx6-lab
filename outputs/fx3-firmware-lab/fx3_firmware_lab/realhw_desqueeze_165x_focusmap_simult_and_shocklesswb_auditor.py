"""Phase 205 — 43rd Firmware-Lab Auditor (43/43): Real-Hardware `ILME-FX3`
(`Ver. 7.02`) `[De-Squeeze Display]` (`1.6x = 1.65x` & 4 Hard Locks / HDMI RAW
Bypass), External `M&C Focus Map` (`>=150fps` Cutoff) & `[Simult. + Auto Switch]`
/ `[Shockless WB]` Auditor.

Strictly Read-Only (`os.O_RDONLY` + `os.pread` bounded section inspection) &
Clean-Room Dual-Mode:
- Local Donor Mode: inspects Stock FX3 `Ver. 7.02` (`appFw.so`,
  `string_english_f.uxc`, `CPAPP-B.BIN`) vs FX6 `Ver. 6.01` (`appFw.so`,
  `string_english.uxc`, `cpapp-b.bin`) strictly via `os.O_RDONLY` + bounded
  `os.pread` (< 0.15 s cold, cached per process via `_DONOR_SCAN_CACHE_P205`).
- Clean-Room Mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`, `clean_room=True`, or donors
  absent): synthesizes deterministic clean-room ELF64 `.so`, `.uxc` string
  packs, and `cpapp-b.bin` RTOS token slices with zero proprietary bytes leaked
  (`raw_firmware_bytes_leaked == 0`).

Audits Four Core Wave-27 Real-Hardware Pillars:
1. Pillar 1 (`DESQUEEZE_165X_FOUR_HARD_LOCKS_AND_FIVE_SUPPRESSIONS`):
   Audits `MENU -> Setup -> [Display Option] -> [De-Squeeze Display]` exact
   5-state enum (`Off`, `1.3x`, `1.5x`, `1.6x`, `2.0x`, where `Ver. 7.00+`
   `1.6x` applies exact `1.65` horizontal CinemaScope `2.39:1` stretch),
   enforces the 4 hard-locked camera settings when active (`[Focus Mode] =
   Manual Focus`, `[Focus Area] = Wide`, `[SteadyShot] = Off`,
   `[Face Priority in Multi Metering] = Off`), and models automatic de-squeeze
   suppression under `[RAW Output] = On`, `[Rec. Media dur HDMI Output] =
   Off(HDMI Only)` (forcing `[HDMI Info. Display] = Off`), `[Log Shooting] =
   Off`, `[Remote Shooting]`, and Still/Photo capture.
2. Pillar 2 (`EXTERNAL_MC_FOCUS_MAP_ZERO_INBODY_MENU_AND_150FPS_CUTOFF`):
   Proves `ILME-FX3` (`Ver. 7.02`) has zero in-body `[Focus Map]` menu/switch
   items (`BKID_APP_USER_MENU_FOCUS_MAP == 0`, `ASSIGNABLE_SWITCH_FOCUS_MAP == 0`
   vs `ILME-FX30` / `ILME-FX6`), routing `Ver. 6.00+` PDAF depth telemetry
   exclusively to external `Monitor & Control`, hard-blocking Stage-B in-body
   Focus Map overlay injection, and enforcing cutoffs at `>= 150 fps`
   (`200/240fps S&Q`), with mount adapters / non-PDAF lenses, over UVC, or
   during playback (while permitting `1..6 fps` on `FX3` unlike `FX6`'s `<=6fps`
   lower cutoff).
3. Pillar 3 (`SIMULT_AUTO_SWITCH_CONTINUATION_AND_SHOCKLESS_WB_KELVIN_BYPASS`):
   Models `Ver. 2.0..7.02` `[Simult. Recording]` + `[Auto Switch Media] = On`
   seamless single-card continuation when one slot fills (and automatic dual-slot
   resumption upon hot-swapping a fresh card) vs `[Auto Switch Media] = Off`
   strict dual-copy halt, plus `[Shockless WB]` (`Off / 1 (Fast) / 2 / 3 (Slow)`)
   across all frame rates (`23.98p .. 240fps`) where direct `[C.Temp./Filter]`
   Kelvin edits and `A-B / G-M` fine-grid shifts bypass smoothing (`0` frames).
4. Pillar 4 (`ZERO_WRITE_FIREWALL_AND_12TP_COMPAT_MATRIX`):
   Enforces hard safety invariants (`persistent_emmc_writes_authorized = False`,
   `spi_nor_write_authorized = False`, `el3_payload_transmit_authorized = False`,
   `physical_usb_packets_emitted = 0`, `raw_firmware_bytes_leaked = 0`) and
   builds a 12-touchpoint 4-class Wave-27 compatibility matrix.
"""

from __future__ import annotations

import math
import os
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from .haita_bk4_feature_analyzer import (
    DEFAULT_REPO_ROOT,
    is_forced_clean_room,
    resolve_donor_file,
)
from .realhw_fx3_vs_fx3a_and_xlrh1_mishoe_auditor import (
    _scan_elf_buf_ordered,
    _scan_elf_fast_rdonly,
)
from .realhw_lens_ibis_audio_hdmi_peripheral_bridge_auditor import (
    BRIDGE_CLASS_HARD_WRITE_PROTECTED,
    BRIDGE_CLASS_MASKED_ABSENT_HW,
    BRIDGE_CLASS_NATIVE_PASSTHROUGH,
    BRIDGE_CLASS_SHIM_TRANSLATED,
    FX3_APPFW_P146_RELPATH,
    FX3_CPAPP_P146_RELPATH,
    FX6_APPFW_P146_RELPATH,
    FX6_CPAPP_P146_RELPATH,
    VALID_BRIDGE_CLASSES,
    ElfSectionSummary,
    _build_synthetic_elf64,
)
from .uxc_multilang_and_font_verifier import (
    FX3_SHARE_APP_RELDIR,
    FX6_SHARE_APP_RELDIR,
)

import hashlib


PHASE_205_SCHEMA = (
    "fx3_firmware_lab_phase205_realhw_desqueeze_165x_focusmap_simult_shocklesswb_v1"
)
PHASE_205_VERSION = "205.0.0"

# ---------------------------------------------------------------------------
# Verified Local Donor Relative Paths (strictly O_RDONLY + bounded os.pread)
# ---------------------------------------------------------------------------

FX3_APPFW_P205_RELPATH = FX3_APPFW_P146_RELPATH
FX6_APPFW_P205_RELPATH = FX6_APPFW_P146_RELPATH
FX3_UXC_EN_F_P205_RELPATH = f"{FX3_SHARE_APP_RELDIR}/string_english_f.uxc"
FX6_UXC_EN_P205_RELPATH = f"{FX6_SHARE_APP_RELDIR}/string_english.uxc"
FX3_CPAPP_P205_RELPATH = FX3_CPAPP_P146_RELPATH
FX6_CPAPP_P205_RELPATH = FX6_CPAPP_P146_RELPATH

EXPECTED_FX3_APPFW_BYTES_P205 = 79_015_712
EXPECTED_FX6_APPFW_BYTES_P205 = 50_520_424
EXPECTED_FX3_UXC_EN_F_BYTES_P205 = 373_820
EXPECTED_FX6_UXC_EN_BYTES_P205 = 118_208
EXPECTED_FX3_CPAPP_BYTES_P205 = 15_980_568
EXPECTED_FX6_CPAPP_BYTES_P205 = 17_952_816

CPAPP_BOUNDED_HEAD_BYTES_P205 = 768 * 1024
CPAPP_BOUNDED_TAIL_BYTES_P205 = 6 * 1024 * 1024
DONOR_COLD_SCAN_BUDGET_SEC_P205 = 0.15

# ---------------------------------------------------------------------------
# Domain Constants — Pillar 1 (`[De-Squeeze Display]` 1.6x=1.65x, 4 Locks, 5 Bypass)
# ---------------------------------------------------------------------------

FX3_DESQUEEZE_DISPLAY_MENU_PATH_P205 = (
    "MENU -> Setup -> [Display Option] -> [De-Squeeze Display]"
)

FX3_DESQUEEZE_MENU_STATES_P205: Tuple[str, ...] = (
    "Off",
    "1.3x",
    "1.5x",
    "1.6x",
    "2.0x",
)
FX3_LEGACY_PRE_700_DESQUEEZE_STATES_P205: Tuple[str, ...] = ("Off", "1.3x", "2.0x")
FX3_700_PLUS_NEW_DESQUEEZE_STATES_P205: Tuple[str, ...] = ("1.5x", "1.6x")

# Sony Help Guide (`ILME-FX3 Ver. 7.00 / 7.02`): `[1.6x]` applies an exact `1.65`
# horizontal stretch factor to restore CinemaScope `2.39:1` widescreen geometry.
DESQUEEZE_EFFECTIVE_HORIZONTAL_SCALE_P205: Dict[str, float] = {
    "Off": 1.00,
    "1.3x": 1.30,
    "1.5x": 1.50,
    "1.6x": 1.65,
    "2.0x": 2.00,
}

CINEMASCOPE_TARGET_ASPECT_P205 = 2.39

DESQUEEZE_FOUR_HARD_LOCKED_SETTINGS_P205: Dict[str, str] = {
    "Focus Mode": "Manual Focus",
    "Focus Area": "Wide",
    "SteadyShot": "Off",
    "Face Priority in Multi Metering": "Off",
}

DESQUEEZE_FIVE_SUPPRESSION_CONDITIONS_P205: Tuple[str, ...] = (
    "HDMI_RAW_OUTPUT_ON",
    "REC_MEDIA_DUR_HDMI_OUTPUT_OFF_HDMI_ONLY",
    "LOG_SHOOTING_OFF",
    "REMOTE_SHOOTING_ACTIVE",
    "PHOTO_STILL_CAPTURE_MODE",
)

VALID_FOCUS_MODES_P205: Tuple[str, ...] = ("Manual Focus", "AF-C", "AF-S")
VALID_FOCUS_AREAS_P205: Tuple[str, ...] = (
    "Wide",
    "Zone",
    "Center Fix",
    "Spot: M",
    "Tracking: Spot M",
)
VALID_STEADYSHOT_MODES_P205: Tuple[str, ...] = ("Off", "Standard", "Active")
VALID_ON_OFF_P205: Tuple[str, ...] = ("On", "Off")
VALID_REC_MEDIA_HDMI_MODES_P205: Tuple[str, ...] = ("On", "Off(HDMI Only)")
VALID_LOG_SHOOTING_MODES_P205: Tuple[str, ...] = (
    "Off",
    "Cine EI",
    "Cine EI Quick",
    "Flexible ISO",
)
VALID_CAPTURE_MODES_P205: Tuple[str, ...] = ("Movie", "S&Q", "Photo")

# ---------------------------------------------------------------------------
# Domain Constants — Pillar 2 (External `M&C Focus Map` & `>=150fps` Cutoff)
# ---------------------------------------------------------------------------

FOCUS_MAP_MIN_FX3_FW_MAJOR_P205 = 6
FOCUS_MAP_HFR_CUTOFF_FPS_P205 = 150
FX6_FOCUS_MAP_LOW_FPS_CUTOFF_MAX_P205 = 6

VALID_FOCUS_MAP_BODIES_P205: Tuple[str, ...] = (
    "ILME-FX3",
    "ILME-FX30",
    "ILME-FX6",
)
IN_BODY_FOCUS_MAP_CAPABLE_BODIES_P205: Tuple[str, ...] = (
    "ILME-FX30",
    "ILME-FX6",
)
VALID_FOCUS_MAP_RENDER_TARGETS_P205: Tuple[str, ...] = (
    "EXTERNAL_MONITOR_AND_CONTROL_APP",
    "FX3_IN_BODY_LCD_OSD_OVERLAY",
    "IN_BODY_NATIVE_LCD_EVF",
)
VALID_LENS_PDAF_STATES_P205: Tuple[str, ...] = (
    "SONY_NATIVE_EMOUNT_PDAF_LENS",
    "NO_LENS_ATTACHED",
    "MOUNT_ADAPTER_LA_EA5_OR_MANUAL",
    "NON_PDAF_LENS",
)
VALID_CAMERA_OP_STATES_P205: Tuple[str, ...] = (
    "LIVE_SHOOTING_STANDBY",
    "LIVE_MOVIE_RECORDING",
    "PLAYBACK",
)

# ---------------------------------------------------------------------------
# Domain Constants — Pillar 3 (`[Simult. + Auto Switch]` & `[Shockless WB]`)
# ---------------------------------------------------------------------------

SIMULT_CONTINUATION_MIN_FW_MAJOR_P205 = 2
VALID_RECORDING_MEDIA_MODES_P205: Tuple[str, ...] = (
    "Simult. Recording",
    "Slot 1",
    "Slot 2",
    "Sort Recording",
)

FX3_SHOCKLESS_WB_MENU_PATH_P205 = (
    "MENU -> Exposure/Color -> [White Balance] -> [Shockless WB]"
)
FX3_SHOCKLESS_WB_STATES_P205: Tuple[str, ...] = (
    "Off",
    "1 (Fast)",
    "2",
    "3 (Slow)",
)
SHOCKLESS_WB_TAU_SECONDS_P205: Dict[str, float] = {
    "Off": 0.0,
    "1 (Fast)": 0.65,
    "2": 1.60,
    "3 (Slow)": 3.20,
}
ALL_FX3_MOVIE_AND_SQ_FPS_P205: Tuple[float, ...] = (
    1.0,
    6.0,
    23.976,
    24.0,
    25.0,
    29.97,
    50.0,
    59.94,
    100.0,
    119.88,
    200.0,
    240.0,
)
WB_CHANGE_TRIGGER_TYPES_P205: Tuple[str, ...] = (
    "WB_MODE_SWITCH_PRESET_TO_CUSTOM",
    "WB_MODE_SWITCH_MEMORY_A_TO_B",
    "ATW_CONVERGENCE",
    "CTEMP_KELVIN_DIRECT_EDIT",
    "AB_GM_FINE_GRID_SHIFT",
)
IMMEDIATE_BYPASS_WB_TRIGGERS_P205: Tuple[str, ...] = (
    "CTEMP_KELVIN_DIRECT_EDIT",
    "AB_GM_FINE_GRID_SHIFT",
)
CTEMP_FILTER_MIN_KELVIN_P205 = 2500
CTEMP_FILTER_MAX_KELVIN_P205 = 9900
WB_FINE_GRID_AXIS_LIMIT_P205 = 7.0

# ---------------------------------------------------------------------------
# Verified Donor Binary Marker Catalogs (strictly O_RDONLY bounded read)
# ---------------------------------------------------------------------------

APPFW_SHARED_WAVE27_MARKERS_P205: Tuple[str, ...] = (
    "N5model25setting_de_squeeze_disp_tE",
    "set_de_squeeze_disp_i",
    "set_param_anamo_desqueeze_scale_msg",
    "video_set_de_squeeze_disp",
    "FOCUS_MODE_MF",
    "FACE_DETECTION_IN_MULTI",
    "sequence_notify_focus_map",
    "view_mp_focus_map",
    "VAL_setting_movie_recording_media_MOVIE_RECORDING_MEDIA_SIMULTANEOUS_RECORDING",
    "RELAY_REC_ON",
    "N5model28setting_movie_shockless_wb_tE",
    "movie_shockless_wb_seq",
    "MOVIE_SHOCKLESS_WB_OFF",
    "MOVIE_SHOCKLESS_WB_1",
    "MOVIE_SHOCKLESS_WB_2",
    "MOVIE_SHOCKLESS_WB_3",
)

APPFW_FX3_702_EXCLUSIVE_MARKERS_P205: Tuple[str, ...] = (
    "BKID_APP_setting_de_squeeze_disp",
    "VAL_HAITA_setting_de_squeeze_disp_general_shooting_mode_DE_SQUEEZE_DISP_1_3X",
    "VAL_HAITA_setting_de_squeeze_disp_general_shooting_mode_DE_SQUEEZE_DISP_1_5X",
    "VAL_HAITA_setting_de_squeeze_disp_general_shooting_mode_DE_SQUEEZE_DISP_1_6X",
    "VAL_HAITA_setting_de_squeeze_disp_general_shooting_mode_DE_SQUEEZE_DISP_2_0X",
    "STEADY_SHOT_OFF",
    "to_remote_event_focus_map",
    "SIMULT_REC",
    "setting_relay_rec_movie",
    "CAUTION_ID_2CARD_REQUIRED_SIMULTANEOIUS_FOR_MOVIE_RECORD",
    "BKID_APP_setting_movie_shockless_wb",
    "BKID_APP_MENU_WB_COLOR_TEMP",
    "WHITE_BALANCE_COLOR_TEMP_COLOR_FILTER_5500K",
)

APPFW_FX6_601_EXCLUSIVE_MARKERS_P205: Tuple[str, ...] = (
    "BKID_APP_USER_MENU_FOCUS_MAP",
    "ASSIGNABLE_SWITCH_FOCUS_MAP",
    "EVENT_FUNC_FOCUS_MAP_ON",
    "EVENT_FUNC_FOCUS_MAP_OFF",
    "PID_SET_ANAMO_DESQUEEZE_SCALE",
    "BKID_APP_SETTING_SIMUL_REC",
    "PID_SET_SHOCKLESS_GAIN_MODE",
)

UXC_FX3_EN_F_REQUIRED_TOKENS_P205: Tuple[str, ...] = (
    "De-Squeeze Display",
    "1.3x",
    "1.5x",
    "1.6x",
    "2.0x",
    "Off",
    "Manual Focus",
    "Wide",
    "SteadyShot",
    "Face Priority in Multi Metering",
    "RAW Output",
    "Off(HDMI Only)",
    "HDMI Info. Display",
    "Log Shooting",
    "Remote Shooting",
    "Focus Map",
    "Simult. Recording",
    "Auto Switch Media",
    "Shockless WB",
    "C.Temp./Filter",
    "1 (Fast)",
    "3 (Slow)",
)

UXC_FX6_EN_REQUIRED_TOKENS_P205: Tuple[str, ...] = (
    "1.3x",
    "1.5x",
    "1.6x",
    "2.0x",
    "Off",
    "Manual Focus",
    "SteadyShot",
    "RAW Output",
    "Focus Map",
    "Fast",
    "Slow",
)

CPAPP_SHARED_MARKERS_P205: Tuple[str, ...] = (
    "C_ImagerCtrl_IMX510",
    "AWB",
    "Mount_DividedInfo",
)

CPAPP_FX3_FOCUSMAP_MARKERS_P205: Tuple[str, ...] = (
    "cpActFocusMap",
    "cpActFocusMapWidgetService",
    "paramYcFocusMap",
)

# ---------------------------------------------------------------------------
# Write-Firewall Patterns
# ---------------------------------------------------------------------------

VOLATILE_WAVE27_OVERLAY_DIR_P205 = "/tmp/fx6_wave27_overlay"
VOLATILE_ALLOWED_PREFIXES_P205: Tuple[str, ...] = (
    "/tmp/fx6_wave27_overlay",
    "/tmp/",
    "/tmp_wbshd/",
    "ram://",
    "memfd:",
)

FORBIDDEN_PERSISTENT_TARGET_RE_P205 = re.compile(
    r"(?:"
    r"^/dev/(?:[cp]?nflasha\d*|mmcblk0(?:p\d+|rpmb)?|rtc0)"
    r"|^p(?:0|1|2|3|5|6|7|8|12|13|15|18):/"
    r"|^/(?:wbi|setting|cert|lens)(?:/|$)"
    r"|^spi_nor:"
    r"|^sector0:"
    r"|Backup\.bin$"
    r"|cpapp-b\.bin$"
    r"|CPAPP-B\.BIN$"
    r"|BODYDATA\.DAT$"
    r"|LENSFILE\.BIN$"
    r"|loader_nor\.bin$"
    r")",
    re.IGNORECASE,
)

# Per-process bounded O_RDONLY donor scan cache (< 0.15s cold, < 1ms warm)
_DONOR_SCAN_CACHE_P205: Dict[Tuple[str, ...], Dict[str, object]] = {}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BoundedUxcSummaryP205:
    pack_name: str
    body_label: str
    source_mode: str
    file_bytes: int
    uxc_magic_valid: bool
    required_token_hits: Dict[str, int]


@dataclass(frozen=True)
class BoundedCpappSummaryP205:
    binary_name: str
    body_label: str
    source_mode: str
    file_bytes: int
    bounded_bytes_read: int
    shared_marker_hits: Dict[str, int]
    fx3_focusmap_marker_hits: Dict[str, int]


@dataclass(frozen=True)
class Desqueeze165xLocksAndSuppressionEvalResult:
    valid: bool
    menu_path: str
    firmware_version: str
    menu_state: str
    nominal_label_ratio: float
    configured_horizontal_scale: float
    effective_horizontal_scale: float
    displayed_16_9_aspect_ratio: float
    cinemascope_165x_stretch_applied: bool
    four_hard_locks_active: bool
    locked_settings: Dict[str, str]
    focus_mode: str
    focus_area: str
    steady_shot: str
    face_priority_in_multi_metering: str
    desqueeze_suppressed: bool
    suppression_reasons: Tuple[str, ...]
    hdmi_info_display_forced_off: bool
    effective_hdmi_info_display: str
    bridge_class: str
    status: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class ExternalMcFocusMapCutoffEvalResult:
    valid: bool
    camera_body: str
    firmware_version: str
    in_body_focus_map_menu_present: bool
    requested_render_target: str
    in_body_focus_map_overlay_injected: bool
    sensor_fps: int
    fx3_low_fps_1_to_6_permitted: bool
    hfr_150fps_cutoff_triggered: bool
    lens_state: str
    usb_uvc_streaming_active: bool
    camera_operating_state: str
    external_mc_focus_map_available: bool
    cutoff_reasons: Tuple[str, ...]
    bridge_class: str
    status: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class SimultRecordingAutoSwitchEvalResult:
    valid: bool
    firmware_version: str
    recording_media_mode: str
    auto_switch_media: str
    slot1_inserted: bool
    slot2_inserted: bool
    slot1_remaining_sec: float
    slot2_remaining_sec: float
    elapsed_rec_sec: float
    hot_swap_fresh_card_into_exhausted_slot: bool
    recording_continues: bool
    single_card_continuation_active: bool
    strict_dual_backup_halt_enforced: bool
    resumed_dual_slot_after_card_swap: bool
    active_slots: Tuple[str, ...]
    frames_dropped: int
    recording_state: str
    bridge_class: str
    status: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class ShocklessWbAndKelvinBypassEvalResult:
    valid: bool
    menu_path: str
    shockless_wb_setting: str
    frame_rate_fps: float
    supported_at_all_fps: bool
    trigger_type: str
    ctemp_kelvin: int
    ab_grid_offset: float
    gm_grid_offset: float
    shockless_smoothing_applied: bool
    immediate_bypass_triggered: bool
    tau_seconds: float
    transition_frames: int
    bridge_class: str
    status: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Phase205WriteGuardResult:
    valid: bool
    target_path: str
    volatile_overlay_allowed: bool
    persistent_write_blocked: bool
    persistent_emmc_writes_authorized: bool
    spi_nor_write_authorized: bool
    el3_payload_transmit_authorized: bool
    physical_usb_packets_emitted: int
    persistent_writes: int
    calibration_mutation_bytes: int
    status: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Phase205TouchpointEntry:
    touchpoint_id: str
    pillar: str
    fx6_or_host_component: str
    fx3_target: str
    bridge_class: str
    safety_invariant: str


@dataclass(frozen=True)
class Phase205CompatMatrixSummary:
    total_touchpoints: int
    class_counts: Dict[str, int]
    pillar_counts: Dict[str, int]
    touchpoints: Tuple[Phase205TouchpointEntry, ...]

@dataclass(frozen=True)
class Pillar1Desqueeze165xAndLocksReport:
    passed: bool
    fx3_appfw_desqueeze_hits: Dict[str, int]
    fx6_appfw_desqueeze_hits: Dict[str, int]
    fx3_uxc_en_f_summary: BoundedUxcSummaryP205
    fx6_uxc_en_summary: BoundedUxcSummaryP205
    eval_16x_applies_165x_with_4_hard_locks_ok: Desqueeze165xLocksAndSuppressionEvalResult
    eval_off_state_unlocks_af_and_ibis_ok: Desqueeze165xLocksAndSuppressionEvalResult
    eval_lock_violation_afc_or_steadyshot_rejected: Desqueeze165xLocksAndSuppressionEvalResult
    eval_suppressed_by_hdmi_raw_output_ok: Desqueeze165xLocksAndSuppressionEvalResult
    eval_suppressed_by_off_hdmi_only_forces_info_off_ok: Desqueeze165xLocksAndSuppressionEvalResult
    eval_suppressed_by_log_off_remote_and_photo_ok: Desqueeze165xLocksAndSuppressionEvalResult
    eval_pre_700_rejects_15x_16x_states: Desqueeze165xLocksAndSuppressionEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Pillar2ExternalMcFocusMapReport:
    passed: bool
    fx3_appfw_focusmap_hits: Dict[str, int]
    fx6_appfw_inbody_focusmap_hits_in_fx6: Dict[str, int]
    fx6_appfw_inbody_focusmap_hits_in_fx3: Dict[str, int]
    fx3_cpapp_summary: BoundedCpappSummaryP205
    fx6_cpapp_summary: BoundedCpappSummaryP205
    eval_fx3_external_mc_24p_and_120p_ok: ExternalMcFocusMapCutoffEvalResult
    eval_fx3_low_fps_1_to_6_permitted_vs_fx6_blocked: Tuple[
        ExternalMcFocusMapCutoffEvalResult, ExternalMcFocusMapCutoffEvalResult
    ]
    eval_fx3_hfr_150_200_240fps_cutoff_blocked: ExternalMcFocusMapCutoffEvalResult
    eval_fx3_mount_adapter_uvc_and_playback_blocked: ExternalMcFocusMapCutoffEvalResult
    eval_stage_b_inbody_focus_map_overlay_rejected: ExternalMcFocusMapCutoffEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Pillar3SimultAutoSwitchAndShocklessWbReport:
    passed: bool
    fx3_appfw_simult_wb_hits: Dict[str, int]
    fx6_appfw_simult_wb_hits: Dict[str, int]
    eval_simult_auto_switch_on_single_card_continuation_ok: SimultRecordingAutoSwitchEvalResult
    eval_simult_auto_switch_on_card_hotswap_resumes_dual_ok: SimultRecordingAutoSwitchEvalResult
    eval_simult_auto_switch_off_strict_dual_halt_ok: SimultRecordingAutoSwitchEvalResult
    eval_simult_missing_second_card_at_start_rejected: SimultRecordingAutoSwitchEvalResult
    eval_shockless_wb_preset_smoothed_at_24p_and_240fps_ok: Tuple[
        ShocklessWbAndKelvinBypassEvalResult, ShocklessWbAndKelvinBypassEvalResult
    ]
    eval_shockless_wb_ctemp_kelvin_immediate_bypass_0frames_ok: ShocklessWbAndKelvinBypassEvalResult
    eval_shockless_wb_ab_gm_grid_immediate_bypass_0frames_ok: ShocklessWbAndKelvinBypassEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Pillar4Phase205WriteGuardAndMatrixReport:
    passed: bool
    blocked_p2_setting_eval: Phase205WriteGuardResult
    blocked_backup_bin_eval: Phase205WriteGuardResult
    blocked_cpapp_bin_eval: Phase205WriteGuardResult
    blocked_lensfile_bin_eval: Phase205WriteGuardResult
    blocked_spi_nor_eval: Phase205WriteGuardResult
    allowed_wave27_overlay_eval: Phase205WriteGuardResult
    allowed_ram_shadow_eval: Phase205WriteGuardResult
    compatibility_matrix: Phase205CompatMatrixSummary
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class RealhwDesqueeze165xFocusmapSimultAndShocklesswbReport:
    schema_version: str
    phase_version: str
    auditor_index: str
    mode: str
    cache_hit: bool
    cold_or_cached_scan_elapsed_sec: float
    all_checks_passed: bool
    o_rdonly_enforced: bool
    raw_firmware_bytes_leaked: int
    persistent_emmc_writes_authorized: bool
    spi_nor_write_authorized: bool
    el3_payload_transmit_authorized: bool
    physical_usb_packets_emitted: int
    in_body_focus_map_overlay_injected: bool
    persistent_writes: int
    calibration_mutation_bytes: int
    desqueeze_165x_locks_and_suppression_verified: bool
    external_mc_focus_map_150fps_cutoff_verified: bool
    simult_auto_switch_and_shockless_wb_bypass_verified: bool
    zero_write_firewall_and_matrix_verified: bool
    donor_file_sizes: Dict[str, int]
    pillar_1_desqueeze_165x_locks: Pillar1Desqueeze165xAndLocksReport
    pillar_2_external_mc_focus_map: Pillar2ExternalMcFocusMapReport
    pillar_3_simult_and_shockless_wb: Pillar3SimultAutoSwitchAndShocklessWbReport
    pillar_4_write_guard_matrix: Pillar4Phase205WriteGuardAndMatrixReport
    report_sha256: str
    errors: Tuple[str, ...]


# ---------------------------------------------------------------------------
# Helpers & Pillar 1 Evaluator — `[De-Squeeze Display]` (1.6x=1.65x, 4 Locks)
# ---------------------------------------------------------------------------


def _parse_fw_major_minor_p205(fw_version: str) -> Optional[Tuple[int, int]]:
    m = re.match(r"^\s*(\d+)\.(\d+)(?:\.\d+)?\s*$", fw_version)
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)))


def compute_desqueezed_display_aspect_ratio(
    menu_state: str,
    sensor_aspect: Tuple[int, int] = (16, 9),
) -> Tuple[float, float]:
    """Return `(effective_horizontal_scale, displayed_aspect_ratio)` (`1.6x -> 1.65x`)."""
    st = menu_state.strip()
    if st not in DESQUEEZE_EFFECTIVE_HORIZONTAL_SCALE_P205:
        raise ValueError(f"Unsupported [De-Squeeze Display] state: {menu_state}")
    w, h = sensor_aspect
    if w <= 0 or h <= 0:
        raise ValueError(f"Invalid sensor_aspect: {sensor_aspect}")
    scale = DESQUEEZE_EFFECTIVE_HORIZONTAL_SCALE_P205[st]
    return (scale, round((float(w) / float(h)) * scale, 4))


def evaluate_desqueeze_display_165x_locks_and_suppression(
    *,
    menu_state: str = "1.6x",
    firmware_version: str = "7.02",
    focus_mode: str = "Manual Focus",
    focus_area: str = "Wide",
    steady_shot: str = "Off",
    face_priority_in_multi_metering: str = "Off",
    hdmi_raw_output: str = "Off",
    rec_media_dur_hdmi_output: str = "On",
    hdmi_info_display: str = "Off",
    log_shooting: str = "Cine EI",
    remote_shooting_active: bool = False,
    capture_mode: str = "Movie",
    stage_b_force_desqueeze_during_suppression: bool = False,
) -> Desqueeze165xLocksAndSuppressionEvalResult:
    """Evaluate `ILME-FX3` (`Ver. 7.02`) `[De-Squeeze Display]` (`1.6x=1.65x`), 4 locks & 5 bypasses."""
    errors: List[str] = []
    st_clean = menu_state.strip()
    fw_clean = firmware_version.strip()
    fm_clean = focus_mode.strip()
    fa_clean = focus_area.strip()
    ss_clean = steady_shot.strip()
    fp_clean = face_priority_in_multi_metering.strip()
    raw_clean = hdmi_raw_output.strip()
    rmed_clean = rec_media_dur_hdmi_output.strip()
    hinfo_clean = hdmi_info_display.strip()
    log_clean = log_shooting.strip()
    cap_clean = capture_mode.strip()

    fw_parsed = _parse_fw_major_minor_p205(fw_clean)
    if fw_parsed is None:
        errors.append(f"INVALID_FIRMWARE_VERSION: {fw_clean}")

    if st_clean not in FX3_DESQUEEZE_MENU_STATES_P205:
        errors.append(f"INVALID_DESQUEEZE_DISPLAY_STATE: {st_clean}")
        nominal_ratio = 1.0
        configured_scale = 1.0
    else:
        nominal_ratio = (
            1.0 if st_clean == "Off" else float(st_clean.rstrip("x"))
        )
        configured_scale = DESQUEEZE_EFFECTIVE_HORIZONTAL_SCALE_P205[st_clean]
        if (
            fw_parsed is not None
            and fw_parsed < (7, 0)
            and st_clean in FX3_700_PLUS_NEW_DESQUEEZE_STATES_P205
        ):
            errors.append(
                f"DESQUEEZE_STATE_REQUIRES_FX3_FW_7_00_OR_NEWER:{st_clean}@Ver.{fw_clean}"
            )

    if fm_clean not in VALID_FOCUS_MODES_P205:
        errors.append(f"INVALID_FOCUS_MODE: {fm_clean}")
    if fa_clean not in VALID_FOCUS_AREAS_P205:
        errors.append(f"INVALID_FOCUS_AREA: {fa_clean}")
    if ss_clean not in VALID_STEADYSHOT_MODES_P205:
        errors.append(f"INVALID_STEADYSHOT_MODE: {ss_clean}")
    if fp_clean not in VALID_ON_OFF_P205:
        errors.append(f"INVALID_FACE_PRIORITY_IN_MULTI_SETTING: {fp_clean}")
    if raw_clean not in VALID_ON_OFF_P205:
        errors.append(f"INVALID_HDMI_RAW_OUTPUT_SETTING: {raw_clean}")
    if rmed_clean not in VALID_REC_MEDIA_HDMI_MODES_P205:
        errors.append(f"INVALID_REC_MEDIA_DUR_HDMI_SETTING: {rmed_clean}")
    if hinfo_clean not in VALID_ON_OFF_P205:
        errors.append(f"INVALID_HDMI_INFO_DISPLAY_SETTING: {hinfo_clean}")
    if log_clean not in VALID_LOG_SHOOTING_MODES_P205:
        errors.append(f"INVALID_LOG_SHOOTING_SETTING: {log_clean}")
    if cap_clean not in VALID_CAPTURE_MODES_P205:
        errors.append(f"INVALID_CAPTURE_MODE: {cap_clean}")

    suppression_reasons: List[str] = []
    hdmi_info_forced_off = False
    effective_hinfo = hinfo_clean

    if rmed_clean == "Off(HDMI Only)":
        hdmi_info_forced_off = True
        effective_hinfo = "Off"

    if st_clean != "Off" and st_clean in FX3_DESQUEEZE_MENU_STATES_P205:
        if raw_clean == "On":
            suppression_reasons.append("HDMI_RAW_OUTPUT_ON")
        if rmed_clean == "Off(HDMI Only)":
            suppression_reasons.append("REC_MEDIA_DUR_HDMI_OUTPUT_OFF_HDMI_ONLY")
        if log_clean == "Off":
            suppression_reasons.append("LOG_SHOOTING_OFF")
        if remote_shooting_active:
            suppression_reasons.append("REMOTE_SHOOTING_ACTIVE")
        if cap_clean == "Photo":
            suppression_reasons.append("PHOTO_STILL_CAPTURE_MODE")

    suppressed = len(suppression_reasons) > 0

    if suppressed and stage_b_force_desqueeze_during_suppression:
        errors.append(
            "STAGE_B_FORBIDDEN_DESQUEEZE_OVERRIDE_DURING_SUPPRESSION:"
            + ",".join(suppression_reasons)
        )

    four_locks_active = st_clean != "Off" and not suppressed and len(errors) == 0
    if st_clean != "Off" and not suppressed and st_clean in FX3_DESQUEEZE_MENU_STATES_P205:
        if fm_clean != "Manual Focus":
            errors.append(f"DESQUEEZE_HARD_LOCK_VIOLATION_FOCUS_MODE_MUST_BE_MF:{fm_clean}")
        if fa_clean != "Wide":
            errors.append(f"DESQUEEZE_HARD_LOCK_VIOLATION_FOCUS_AREA_MUST_BE_WIDE:{fa_clean}")
        if ss_clean != "Off":
            errors.append(f"DESQUEEZE_HARD_LOCK_VIOLATION_STEADYSHOT_MUST_BE_OFF:{ss_clean}")
        if fp_clean != "Off":
            errors.append(
                f"DESQUEEZE_HARD_LOCK_VIOLATION_FACE_PRIORITY_MULTI_MUST_BE_OFF:{fp_clean}"
            )
        four_locks_active = len(errors) == 0

    effective_scale = (
        1.00 if (st_clean == "Off" or suppressed or errors) else configured_scale
    )
    disp_aspect = round((16.0 / 9.0) * effective_scale, 4)
    is_165x = st_clean == "1.6x" and math.isclose(effective_scale, 1.65, abs_tol=1e-6)

    if errors:
        b_cls = BRIDGE_CLASS_HARD_WRITE_PROTECTED
        status = errors[0]
    elif suppressed:
        b_cls = BRIDGE_CLASS_SHIM_TRANSLATED
        status = f"OK_DESQUEEZE_AUTO_SUPPRESSED:{suppression_reasons[0]}"
    elif st_clean == "Off":
        b_cls = BRIDGE_CLASS_NATIVE_PASSTHROUGH
        status = "OK_DESQUEEZE_OFF_AF_AND_IBIS_UNLOCKED"
    elif st_clean == "1.6x":
        b_cls = BRIDGE_CLASS_SHIM_TRANSLATED
        status = "OK_DESQUEEZE_1_6X_APPLIES_1_65X_CINEMASCOPE_WITH_4_HARD_LOCKS"
    else:
        b_cls = BRIDGE_CLASS_NATIVE_PASSTHROUGH
        status = f"OK_DESQUEEZE_{st_clean.upper()}_ACTIVE_WITH_4_HARD_LOCKS"

    return Desqueeze165xLocksAndSuppressionEvalResult(
        valid=len(errors) == 0,
        menu_path=FX3_DESQUEEZE_DISPLAY_MENU_PATH_P205,
        firmware_version=fw_clean,
        menu_state=st_clean,
        nominal_label_ratio=nominal_ratio,
        configured_horizontal_scale=configured_scale,
        effective_horizontal_scale=effective_scale,
        displayed_16_9_aspect_ratio=disp_aspect,
        cinemascope_165x_stretch_applied=is_165x,
        four_hard_locks_active=four_locks_active,
        locked_settings=dict(DESQUEEZE_FOUR_HARD_LOCKED_SETTINGS_P205),
        focus_mode=fm_clean,
        focus_area=fa_clean,
        steady_shot=ss_clean,
        face_priority_in_multi_metering=fp_clean,
        desqueeze_suppressed=suppressed,
        suppression_reasons=tuple(suppression_reasons),
        hdmi_info_display_forced_off=hdmi_info_forced_off,
        effective_hdmi_info_display=effective_hinfo,
        bridge_class=b_cls,
        status=status,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 2 Evaluator — External `M&C Focus Map` & `>=150fps` Cutoff
# ---------------------------------------------------------------------------


def evaluate_external_mc_focus_map_and_150fps_cutoff(
    *,
    camera_body: str = "ILME-FX3",
    firmware_version: str = "7.02",
    requested_render_target: str = "EXTERNAL_MONITOR_AND_CONTROL_APP",
    sensor_fps: int = 24,
    lens_state: str = "SONY_NATIVE_EMOUNT_PDAF_LENS",
    usb_uvc_streaming_active: bool = False,
    camera_operating_state: str = "LIVE_MOVIE_RECORDING",
    stage_b_inject_in_body_focus_map_overlay: bool = False,
) -> ExternalMcFocusMapCutoffEvalResult:
    """Audit `ILME-FX3` absent in-body `[Focus Map]` menu & external `M&C >=150fps` cutoff."""
    errors: List[str] = []
    body_clean = camera_body.strip().upper()
    fw_clean = firmware_version.strip()
    target_clean = requested_render_target.strip()
    lens_clean = lens_state.strip()
    op_clean = camera_operating_state.strip()

    if body_clean not in VALID_FOCUS_MAP_BODIES_P205:
        errors.append(f"INVALID_FOCUS_MAP_CAMERA_BODY: {body_clean}")
    fw_parsed = _parse_fw_major_minor_p205(fw_clean)
    if fw_parsed is None:
        errors.append(f"INVALID_FIRMWARE_VERSION: {fw_clean}")
    if target_clean not in VALID_FOCUS_MAP_RENDER_TARGETS_P205:
        errors.append(f"INVALID_FOCUS_MAP_RENDER_TARGET: {target_clean}")
    if int(sensor_fps) < 1 or int(sensor_fps) > 240:
        errors.append(f"INVALID_SENSOR_FPS_OUT_OF_RANGE_1_TO_240: {sensor_fps}")
    if lens_clean not in VALID_LENS_PDAF_STATES_P205:
        errors.append(f"INVALID_LENS_PDAF_STATE: {lens_clean}")
    if op_clean not in VALID_CAMERA_OP_STATES_P205:
        errors.append(f"INVALID_CAMERA_OPERATING_STATE: {op_clean}")

    in_body_menu = body_clean in IN_BODY_FOCUS_MAP_CAPABLE_BODIES_P205

    # Hard Stage-B prohibition: ILME-FX3 has ZERO in-body Focus Map menu/hardware overlay!
    if body_clean == "ILME-FX3" and (
        target_clean in ("FX3_IN_BODY_LCD_OSD_OVERLAY", "IN_BODY_NATIVE_LCD_EVF")
        or stage_b_inject_in_body_focus_map_overlay
    ):
        errors.append(
            "FX3_ABSENT_IN_BODY_FOCUS_MAP_MENU_OVERLAY_FORBIDDEN: "
            "ILME-FX3 streams Focus Map exclusively to external Monitor & Control"
        )

    cutoff_reasons: List[str] = []
    fps_int = int(sensor_fps)

    if (
        body_clean == "ILME-FX3"
        and fw_parsed is not None
        and fw_parsed[0] < FOCUS_MAP_MIN_FX3_FW_MAJOR_P205
    ):
        cutoff_reasons.append("BLOCKED_FX3_REQUIRES_FW_6_00_OR_NEWER")

    hfr_cutoff = fps_int >= FOCUS_MAP_HFR_CUTOFF_FPS_P205
    if hfr_cutoff:
        cutoff_reasons.append("BLOCKED_FPS_GE_150_HFR_CUTOFF")

    if body_clean == "ILME-FX6" and fps_int <= FX6_FOCUS_MAP_LOW_FPS_CUTOFF_MAX_P205:
        cutoff_reasons.append("BLOCKED_FX6_LOW_FPS_LE_6_CUTOFF")

    if lens_clean != "SONY_NATIVE_EMOUNT_PDAF_LENS":
        cutoff_reasons.append(f"BLOCKED_LENS_PDAF_UNAVAILABLE:{lens_clean}")

    if usb_uvc_streaming_active:
        cutoff_reasons.append("BLOCKED_DURING_UVC_USB_STREAMING")

    if op_clean == "PLAYBACK":
        cutoff_reasons.append("BLOCKED_DURING_IN_CAMERA_PLAYBACK")

    fx3_low_fps_ok = (
        body_clean == "ILME-FX3" and 1 <= fps_int <= FX6_FOCUS_MAP_LOW_FPS_CUTOFF_MAX_P205
    )
    mc_available = len(errors) == 0 and len(cutoff_reasons) == 0

    if errors:
        b_cls = (
            BRIDGE_CLASS_MASKED_ABSENT_HW
            if any("FX3_ABSENT_IN_BODY_FOCUS_MAP" in e for e in errors)
            else BRIDGE_CLASS_HARD_WRITE_PROTECTED
        )
        status = errors[0]
    elif cutoff_reasons:
        b_cls = BRIDGE_CLASS_SHIM_TRANSLATED
        status = f"OK_FOCUS_MAP_DISABLED_BY_CUTOFF:{cutoff_reasons[0]}"
    elif body_clean == "ILME-FX3":
        b_cls = BRIDGE_CLASS_SHIM_TRANSLATED
        status = "OK_FX3_EXTERNAL_MC_FOCUS_MAP_PDAF_STREAM_ACTIVE"
    else:
        b_cls = BRIDGE_CLASS_NATIVE_PASSTHROUGH
        status = f"OK_{body_clean}_FOCUS_MAP_ACTIVE"

    return ExternalMcFocusMapCutoffEvalResult(
        valid=len(errors) == 0,
        camera_body=body_clean,
        firmware_version=fw_clean,
        in_body_focus_map_menu_present=in_body_menu,
        requested_render_target=target_clean,
        in_body_focus_map_overlay_injected=False,
        sensor_fps=fps_int,
        fx3_low_fps_1_to_6_permitted=fx3_low_fps_ok,
        hfr_150fps_cutoff_triggered=hfr_cutoff,
        lens_state=lens_clean,
        usb_uvc_streaming_active=bool(usb_uvc_streaming_active),
        camera_operating_state=op_clean,
        external_mc_focus_map_available=mc_available,
        cutoff_reasons=tuple(cutoff_reasons),
        bridge_class=b_cls,
        status=status,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 3 Evaluators — `[Simult. + Auto Switch]` & `[Shockless WB]` Bypass
# ---------------------------------------------------------------------------


def evaluate_simult_recording_and_auto_switch_media(
    *,
    firmware_version: str = "7.02",
    recording_media_mode: str = "Simult. Recording",
    auto_switch_media: str = "On",
    slot1_inserted: bool = True,
    slot2_inserted: bool = True,
    slot1_remaining_sec: float = 120.0,
    slot2_remaining_sec: float = 1800.0,
    elapsed_rec_sec: float = 300.0,
    hot_swap_fresh_card_into_exhausted_slot: bool = False,
) -> SimultRecordingAutoSwitchEvalResult:
    """Model `Ver. 2.0..7.02` `[Simult. Recording]` + `[Auto Switch Media]` continuation vs strict halt."""
    errors: List[str] = []
    fw_clean = firmware_version.strip()
    mode_clean = recording_media_mode.strip()
    asw_clean = auto_switch_media.strip()

    fw_parsed = _parse_fw_major_minor_p205(fw_clean)
    if fw_parsed is None:
        errors.append(f"INVALID_FIRMWARE_VERSION: {fw_clean}")
    if mode_clean not in VALID_RECORDING_MEDIA_MODES_P205:
        errors.append(f"INVALID_RECORDING_MEDIA_MODE: {mode_clean}")
    if asw_clean not in VALID_ON_OFF_P205:
        errors.append(f"INVALID_AUTO_SWITCH_MEDIA_SETTING: {asw_clean}")
    if slot1_remaining_sec < 0.0 or slot2_remaining_sec < 0.0 or elapsed_rec_sec < 0.0:
        errors.append("NEGATIVE_MEDIA_DURATION_FORBIDDEN")

    if mode_clean == "Simult. Recording" and (not slot1_inserted or not slot2_inserted):
        errors.append(
            "CAUTION_ID_2CARD_REQUIRED_SIMULTANEOIUS_FOR_MOVIE_RECORD: "
            "Simult. Recording requires cards inserted in both Slot 1 and Slot 2 at REC start"
        )

    if errors:
        return SimultRecordingAutoSwitchEvalResult(
            valid=False,
            firmware_version=fw_clean,
            recording_media_mode=mode_clean,
            auto_switch_media=asw_clean,
            slot1_inserted=bool(slot1_inserted),
            slot2_inserted=bool(slot2_inserted),
            slot1_remaining_sec=float(slot1_remaining_sec),
            slot2_remaining_sec=float(slot2_remaining_sec),
            elapsed_rec_sec=float(elapsed_rec_sec),
            hot_swap_fresh_card_into_exhausted_slot=bool(
                hot_swap_fresh_card_into_exhausted_slot
            ),
            recording_continues=False,
            single_card_continuation_active=False,
            strict_dual_backup_halt_enforced=False,
            resumed_dual_slot_after_card_swap=False,
            active_slots=(),
            frames_dropped=0,
            recording_state="REJECTED_INVALID_OR_MISSING_CARD",
            bridge_class=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
            status=errors[0],
            errors=tuple(errors),
        )

    assert fw_parsed is not None
    s1_exhausted = float(elapsed_rec_sec) >= float(slot1_remaining_sec)
    s2_exhausted = float(elapsed_rec_sec) >= float(slot2_remaining_sec)

    single_cont = False
    strict_halt = False
    resumed_dual = False

    if mode_clean == "Simult. Recording":
        if not s1_exhausted and not s2_exhausted:
            rec_continues = True
            active_slots: Tuple[str, ...] = ("Slot 1", "Slot 2")
            rec_state = "DUAL_SLOT_SIMULTANEOUS_ACTIVE"
            b_cls = BRIDGE_CLASS_NATIVE_PASSTHROUGH
        elif s1_exhausted and s2_exhausted:
            rec_continues = False
            active_slots = ()
            rec_state = "HALTED_BOTH_SLOTS_FULL"
            b_cls = BRIDGE_CLASS_NATIVE_PASSTHROUGH
        else:
            # Exactly one card exhausted
            remaining_slot = "Slot 2" if s1_exhausted else "Slot 1"
            if asw_clean == "On" and fw_parsed[0] >= SIMULT_CONTINUATION_MIN_FW_MAJOR_P205:
                rec_continues = True
                if hot_swap_fresh_card_into_exhausted_slot:
                    resumed_dual = True
                    single_cont = False
                    active_slots = ("Slot 1", "Slot 2")
                    rec_state = "RESUMED_DUAL_SLOT_AFTER_FRESH_CARD_HOTSWAP"
                else:
                    single_cont = True
                    active_slots = (remaining_slot,)
                    rec_state = f"SINGLE_CARD_CONTINUATION_ON_{remaining_slot.replace(' ', '_').upper()}"
                b_cls = BRIDGE_CLASS_SHIM_TRANSLATED
            else:
                rec_continues = False
                strict_halt = True
                active_slots = ()
                rec_state = "HALTED_STRICT_DUAL_PARITY_ONE_CARD_FULL"
                b_cls = BRIDGE_CLASS_NATIVE_PASSTHROUGH
    elif mode_clean == "Slot 1":
        if not s1_exhausted:
            rec_continues = True
            active_slots = ("Slot 1",)
            rec_state = "SINGLE_SLOT_1_ACTIVE"
        elif asw_clean == "On" and slot2_inserted and not s2_exhausted:
            rec_continues = True
            single_cont = True
            active_slots = ("Slot 2",)
            rec_state = "RELAY_SWITCHED_SLOT_1_TO_SLOT_2"
        else:
            rec_continues = False
            active_slots = ()
            rec_state = "HALTED_SLOT_1_FULL"
        b_cls = BRIDGE_CLASS_NATIVE_PASSTHROUGH
    else:
        rec_continues = not (s1_exhausted or s2_exhausted)
        active_slots = ("Slot 2",) if mode_clean == "Slot 2" and not s2_exhausted else (
            ("Slot 1", "Slot 2") if rec_continues else ()
        )
        rec_state = f"{mode_clean.upper().replace(' ', '_')}_{'ACTIVE' if rec_continues else 'HALTED'}"
        b_cls = BRIDGE_CLASS_NATIVE_PASSTHROUGH

    return SimultRecordingAutoSwitchEvalResult(
        valid=True,
        firmware_version=fw_clean,
        recording_media_mode=mode_clean,
        auto_switch_media=asw_clean,
        slot1_inserted=bool(slot1_inserted),
        slot2_inserted=bool(slot2_inserted),
        slot1_remaining_sec=float(slot1_remaining_sec),
        slot2_remaining_sec=float(slot2_remaining_sec),
        elapsed_rec_sec=float(elapsed_rec_sec),
        hot_swap_fresh_card_into_exhausted_slot=bool(
            hot_swap_fresh_card_into_exhausted_slot
        ),
        recording_continues=rec_continues,
        single_card_continuation_active=single_cont,
        strict_dual_backup_halt_enforced=strict_halt,
        resumed_dual_slot_after_card_swap=resumed_dual,
        active_slots=active_slots,
        frames_dropped=0,
        recording_state=rec_state,
        bridge_class=b_cls,
        status=f"OK_{rec_state}",
        errors=(),
    )


def evaluate_shockless_wb_and_ctemp_grid_bypass(
    *,
    shockless_wb_setting: str = "2",
    frame_rate_fps: float = 23.976,
    trigger_type: str = "WB_MODE_SWITCH_PRESET_TO_CUSTOM",
    ctemp_kelvin: int = 5500,
    ab_grid_offset: float = 0.0,
    gm_grid_offset: float = 0.0,
) -> ShocklessWbAndKelvinBypassEvalResult:
    """Audit `[Shockless WB]` all-FPS smoothing vs `[C.Temp./Filter]` Kelvin & `A-B/G-M` grid 0-frame bypass."""
    errors: List[str] = []
    swb_clean = shockless_wb_setting.strip()
    trig_clean = trigger_type.strip()
    fps_f = float(frame_rate_fps)

    if swb_clean not in FX3_SHOCKLESS_WB_STATES_P205:
        errors.append(f"INVALID_SHOCKLESS_WB_SETTING: {swb_clean}")
    if fps_f <= 0.0 or fps_f > 240.0:
        errors.append(f"INVALID_FRAME_RATE_FPS_OUT_OF_RANGE: {fps_f}")
    if trig_clean not in WB_CHANGE_TRIGGER_TYPES_P205:
        errors.append(f"INVALID_WB_TRIGGER_TYPE: {trig_clean}")
    if not (CTEMP_FILTER_MIN_KELVIN_P205 <= int(ctemp_kelvin) <= CTEMP_FILTER_MAX_KELVIN_P205):
        errors.append(
            f"CTEMP_FILTER_KELVIN_OUT_OF_RANGE_2500_TO_9900: {ctemp_kelvin}"
        )
    if (
        abs(float(ab_grid_offset)) > WB_FINE_GRID_AXIS_LIMIT_P205
        or abs(float(gm_grid_offset)) > WB_FINE_GRID_AXIS_LIMIT_P205
    ):
        errors.append(
            f"WB_AB_GM_GRID_OFFSET_OUT_OF_RANGE_7: ab={ab_grid_offset}, gm={gm_grid_offset}"
        )

    if errors:
        return ShocklessWbAndKelvinBypassEvalResult(
            valid=False,
            menu_path=FX3_SHOCKLESS_WB_MENU_PATH_P205,
            shockless_wb_setting=swb_clean,
            frame_rate_fps=fps_f,
            supported_at_all_fps=True,
            trigger_type=trig_clean,
            ctemp_kelvin=int(ctemp_kelvin),
            ab_grid_offset=float(ab_grid_offset),
            gm_grid_offset=float(gm_grid_offset),
            shockless_smoothing_applied=False,
            immediate_bypass_triggered=False,
            tau_seconds=0.0,
            transition_frames=0,
            bridge_class=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
            status=errors[0],
            errors=tuple(errors),
        )

    configured_tau = SHOCKLESS_WB_TAU_SECONDS_P205[swb_clean]
    is_immediate_bypass = trig_clean in IMMEDIATE_BYPASS_WB_TRIGGERS_P205

    if is_immediate_bypass:
        effective_tau = 0.0
        trans_frames = 0
        smoothed = False
        b_cls = BRIDGE_CLASS_SHIM_TRANSLATED
        status = f"OK_SHOCKLESS_WB_IMMEDIATE_0FRAME_BYPASS:{trig_clean}"
    elif swb_clean == "Off":
        effective_tau = 0.0
        trans_frames = 0
        smoothed = False
        b_cls = BRIDGE_CLASS_NATIVE_PASSTHROUGH
        status = "OK_SHOCKLESS_WB_OFF_IMMEDIATE_SWITCH"
    else:
        effective_tau = configured_tau
        trans_frames = max(1, int(round(effective_tau * fps_f)))
        smoothed = True
        b_cls = BRIDGE_CLASS_NATIVE_PASSTHROUGH
        status = f"OK_SHOCKLESS_WB_SMOOTH_TRANSITION_{trans_frames}F"

    return ShocklessWbAndKelvinBypassEvalResult(
        valid=True,
        menu_path=FX3_SHOCKLESS_WB_MENU_PATH_P205,
        shockless_wb_setting=swb_clean,
        frame_rate_fps=fps_f,
        supported_at_all_fps=True,
        trigger_type=trig_clean,
        ctemp_kelvin=int(ctemp_kelvin),
        ab_grid_offset=float(ab_grid_offset),
        gm_grid_offset=float(gm_grid_offset),
        shockless_smoothing_applied=smoothed,
        immediate_bypass_triggered=is_immediate_bypass,
        tau_seconds=effective_tau,
        transition_frames=trans_frames,
        bridge_class=b_cls,
        status=status,
        errors=(),
    )


# ---------------------------------------------------------------------------
# Pillar 4 Evaluator — Hard Write Firewall & 12-Touchpoint Compatibility Matrix
# ---------------------------------------------------------------------------


def evaluate_phase205_write_guard(target_path: str) -> Phase205WriteGuardResult:
    """Enforce zero persistent eMMC / SPI-NOR / calibration / lensfile mutations."""
    clean = target_path.strip()
    if not clean:
        return Phase205WriteGuardResult(
            valid=False,
            target_path=clean,
            volatile_overlay_allowed=False,
            persistent_write_blocked=True,
            persistent_emmc_writes_authorized=False,
            spi_nor_write_authorized=False,
            el3_payload_transmit_authorized=False,
            physical_usb_packets_emitted=0,
            persistent_writes=0,
            calibration_mutation_bytes=0,
            status="EMPTY_TARGET_PATH_BLOCKED",
            errors=("EMPTY_TARGET_PATH_BLOCKED",),
        )

    norm = os.path.normpath(clean) if clean.startswith("/") else clean
    if (
        ".." in clean.split("/")
        or FORBIDDEN_PERSISTENT_TARGET_RE_P205.search(clean)
        or FORBIDDEN_PERSISTENT_TARGET_RE_P205.search(norm)
    ):
        err = f"HARD_WRITE_PROTECTED_TARGET_BLOCKED: {clean}"
        return Phase205WriteGuardResult(
            valid=False,
            target_path=clean,
            volatile_overlay_allowed=False,
            persistent_write_blocked=True,
            persistent_emmc_writes_authorized=False,
            spi_nor_write_authorized=False,
            el3_payload_transmit_authorized=False,
            physical_usb_packets_emitted=0,
            persistent_writes=0,
            calibration_mutation_bytes=0,
            status=err,
            errors=(err,),
        )

    if not any(clean.startswith(pfx) for pfx in VOLATILE_ALLOWED_PREFIXES_P205):
        err = f"UNAPPROVED_NON_VOLATILE_PATH_BLOCKED: {clean}"
        return Phase205WriteGuardResult(
            valid=False,
            target_path=clean,
            volatile_overlay_allowed=False,
            persistent_write_blocked=True,
            persistent_emmc_writes_authorized=False,
            spi_nor_write_authorized=False,
            el3_payload_transmit_authorized=False,
            physical_usb_packets_emitted=0,
            persistent_writes=0,
            calibration_mutation_bytes=0,
            status=err,
            errors=(err,),
        )

    return Phase205WriteGuardResult(
        valid=True,
        target_path=clean,
        volatile_overlay_allowed=True,
        persistent_write_blocked=False,
        persistent_emmc_writes_authorized=False,
        spi_nor_write_authorized=False,
        el3_payload_transmit_authorized=False,
        physical_usb_packets_emitted=0,
        persistent_writes=0,
        calibration_mutation_bytes=0,
        status="OK_VOLATILE_OVERLAY_TARGET_PERMITTED",
        errors=(),
    )


def build_phase205_compat_matrix() -> Phase205CompatMatrixSummary:
    """Build deterministic 12-touchpoint 4-class Wave-27 compatibility matrix."""
    entries: Tuple[Phase205TouchpointEntry, ...] = (
        Phase205TouchpointEntry(
            touchpoint_id="P205-01",
            pillar="PILLAR_1_DESQUEEZE_165X_LOCKS",
            fx6_or_host_component="MENU -> Setup -> [Display Option] -> [De-Squeeze Display] (Off, 1.3x, 1.5x, 1.6x, 2.0x)",
            fx3_target="1.6x applies exact 1.65x CinemaScope 2.39:1 horizontal stretch (Ver. 7.00+ / 7.02)",
            bridge_class=BRIDGE_CLASS_SHIM_TRANSLATED,
            safety_invariant="effective_horizontal_scale == 1.65 when menu_state == '1.6x'",
        ),
        Phase205TouchpointEntry(
            touchpoint_id="P205-02",
            pillar="PILLAR_1_DESQUEEZE_165X_LOCKS",
            fx6_or_host_component="Active Anamorphic De-Squeeze 4 Camera Hard Locks",
            fx3_target="[Focus Mode]=Manual Focus, [Focus Area]=Wide, [SteadyShot]=Off, [Face Priority in Multi]=Off",
            bridge_class=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
            safety_invariant="four_hard_locks_active == True whenever De-Squeeze != Off & unsuppressed",
        ),
        Phase205TouchpointEntry(
            touchpoint_id="P205-03",
            pillar="PILLAR_1_DESQUEEZE_165X_LOCKS",
            fx6_or_host_component="HDMI [RAW Output]=On & [Rec. Media dur HDMI Output]=[Off(HDMI Only)] Bypass",
            fx3_target="Auto-suppresses de-squeeze to 1.0x & forces [HDMI Info. Display]=Off on Off(HDMI Only)",
            bridge_class=BRIDGE_CLASS_SHIM_TRANSLATED,
            safety_invariant="desqueeze_suppressed == True && effective_hdmi_info_display == 'Off'",
        ),
        Phase205TouchpointEntry(
            touchpoint_id="P205-04",
            pillar="PILLAR_1_DESQUEEZE_165X_LOCKS",
            fx6_or_host_component="[Log Shooting]=Off, [Remote Shooting], and Photo Capture De-Squeeze Suppression",
            fx3_target="Automatic 1.0x bypass without corrupting stored [De-Squeeze Display] preference",
            bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            safety_invariant="effective_horizontal_scale == 1.0 during Log Off / Remote / Photo",
        ),
        Phase205TouchpointEntry(
            touchpoint_id="P205-05",
            pillar="PILLAR_2_EXTERNAL_MC_FOCUS_MAP",
            fx6_or_host_component="FX30 / FX6 In-Body [Focus Map] Menu & Assignable Button (BKID_APP_USER_MENU_FOCUS_MAP)",
            fx3_target="Absent on ILME-FX3 (Ver. 7.02) -> hard-blocks Stage-B local LCD Focus Map overlay injection",
            bridge_class=BRIDGE_CLASS_MASKED_ABSENT_HW,
            safety_invariant="in_body_focus_map_menu_present == False && in_body_focus_map_overlay_injected == False",
        ),
        Phase205TouchpointEntry(
            touchpoint_id="P205-06",
            pillar="PILLAR_2_EXTERNAL_MC_FOCUS_MAP",
            fx6_or_host_component="External Monitor & Control PDAF Focus Map Telemetry (to_remote_event_focus_map)",
            fx3_target="Streams cpActFocusMap / paramYcFocusMap depth map on ILME-FX3 Ver. 6.00+ (< 150 fps)",
            bridge_class=BRIDGE_CLASS_SHIM_TRANSLATED,
            safety_invariant="external_mc_focus_map_available == True for Sony PDAF lens at < 150 fps",
        ),
        Phase205TouchpointEntry(
            touchpoint_id="P205-07",
            pillar="PILLAR_2_EXTERNAL_MC_FOCUS_MAP",
            fx6_or_host_component="High Frame Rate >= 150 fps (200/240fps S&Q) vs FX3 1..6 fps Low-Rate Boundary",
            fx3_target="Hard cutoff at >= 150 fps on FX3 while allowing 1..6 fps (unlike FX6 <= 6 fps cutoff)",
            bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            safety_invariant="hfr_150fps_cutoff_triggered == (sensor_fps >= 150) && fx3_low_fps_1_to_6_permitted",
        ),
        Phase205TouchpointEntry(
            touchpoint_id="P205-08",
            pillar="PILLAR_2_EXTERNAL_MC_FOCUS_MAP",
            fx6_or_host_component="Mount Adapter / Non-PDAF Lens, UVC Streaming & In-Camera Playback Focus Map Gate",
            fx3_target="Disables external Focus Map stream cleanly when PDAF phase telemetry is unavailable",
            bridge_class=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
            safety_invariant="external_mc_focus_map_available == False under adapter/UVC/playback",
        ),
        Phase205TouchpointEntry(
            touchpoint_id="P205-09",
            pillar="PILLAR_3_SIMULT_AND_SHOCKLESS_WB",
            fx6_or_host_component="[Simult. Recording] + [Auto Switch Media] = [On] (Ver. 2.0..7.02)",
            fx3_target="Seamless 0-drop single-card continuation on remaining slot + dual resume on card swap",
            bridge_class=BRIDGE_CLASS_SHIM_TRANSLATED,
            safety_invariant="recording_continues == True && frames_dropped == 0 when one card fills",
        ),
        Phase205TouchpointEntry(
            touchpoint_id="P205-10",
            pillar="PILLAR_3_SIMULT_AND_SHOCKLESS_WB",
            fx6_or_host_component="[Simult. Recording] + [Auto Switch Media] = [Off] Strict Dual-Copy Vault Rule",
            fx3_target="Halts recording immediately when either card fills so dual-card parity stays 1:1",
            bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            safety_invariant="strict_dual_backup_halt_enforced == True when Auto Switch Media == 'Off'",
        ),
        Phase205TouchpointEntry(
            touchpoint_id="P205-11",
            pillar="PILLAR_3_SIMULT_AND_SHOCKLESS_WB",
            fx6_or_host_component="[Shockless WB] (Off / 1 (Fast) / 2 / 3 (Slow)) All-FPS Slew-Rate Smoothing",
            fx3_target="Active across 23.98p..120p & 200/240fps S&Q for WB preset / Custom / Memory switches",
            bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            safety_invariant="supported_at_all_fps == True && transition_frames > 0 for preset switches",
        ),
        Phase205TouchpointEntry(
            touchpoint_id="P205-12",
            pillar="PILLAR_3_SIMULT_AND_SHOCKLESS_WB",
            fx6_or_host_component="[C.Temp./Filter] Direct Kelvin Edits & A-B / G-M Fine-Grid Shifts",
            fx3_target="Bypasses [Shockless WB] damping and applies immediately in 0 transition frames",
            bridge_class=BRIDGE_CLASS_SHIM_TRANSLATED,
            safety_invariant="immediate_bypass_triggered == True && transition_frames == 0",
        ),
    )
    class_counts: Dict[str, int] = {c: 0 for c in VALID_BRIDGE_CLASSES}
    pillar_counts: Dict[str, int] = {}
    for entry in entries:
        class_counts[entry.bridge_class] = class_counts.get(entry.bridge_class, 0) + 1
        pillar_counts[entry.pillar] = pillar_counts.get(entry.pillar, 0) + 1
    return Phase205CompatMatrixSummary(
        total_touchpoints=len(entries),
        class_counts=class_counts,
        pillar_counts=pillar_counts,
        touchpoints=entries,
    )


# ---------------------------------------------------------------------------
# Bounded O_RDONLY Donor Scanners & Clean-Room Synthetic Fixture Builder
# ---------------------------------------------------------------------------


def _scan_uxc_bounded_rdonly_p205(
    path: Path,
    *,
    pack_name: str,
    body_label: str,
    required_tokens: Sequence[str],
) -> BoundedUxcSummaryP205:
    """Strictly `os.O_RDONLY` bounded `os.pread` scanner for `.uxc` string packs (< 400 KiB)."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        sz = int(os.fstat(fd).st_size)
        buf = os.pread(fd, sz, 0) if sz > 0 else b""
        magic_ok = len(buf) >= 4 and buf[:4] in (b"uxd\x07", b"uxc\x07")
        req_hits = {t: buf.count(t.encode("utf-8")) for t in required_tokens}
        return BoundedUxcSummaryP205(
            pack_name=pack_name,
            body_label=body_label,
            source_mode="LOCAL_DONOR_RDONLY",
            file_bytes=sz,
            uxc_magic_valid=magic_ok,
            required_token_hits=req_hits,
        )
    finally:
        os.close(fd)


def _scan_uxc_buf_clean_room_p205(
    buf: bytes,
    *,
    pack_name: str,
    body_label: str,
    required_tokens: Sequence[str],
) -> BoundedUxcSummaryP205:
    magic_ok = len(buf) >= 4 and buf[:4] in (b"uxd\x07", b"uxc\x07")
    return BoundedUxcSummaryP205(
        pack_name=pack_name,
        body_label=body_label,
        source_mode="CLEAN_ROOM_SYNTHETIC",
        file_bytes=len(buf),
        uxc_magic_valid=magic_ok,
        required_token_hits={t: buf.count(t.encode("utf-8")) for t in required_tokens},
    )


def _scan_cpapp_bounded_rdonly_p205(
    path: Path,
    *,
    binary_name: str,
    body_label: str,
    shared_tokens: Sequence[str],
    fx3_focusmap_tokens: Sequence[str],
) -> BoundedCpappSummaryP205:
    """Strictly `os.O_RDONLY` bounded `os.pread` of CP RTOS head (768 KiB) + tail (6 MiB)."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        sz = int(os.fstat(fd).st_size)
        sh_counts: Dict[str, int] = {t: 0 for t in shared_tokens}
        fm_counts: Dict[str, int] = {t: 0 for t in fx3_focusmap_tokens}
        sh_enc = [(t, t.encode("ascii")) for t in shared_tokens]
        fm_enc = [(t, t.encode("ascii")) for t in fx3_focusmap_tokens]
        head_len = min(sz, CPAPP_BOUNDED_HEAD_BYTES_P205)
        slices: List[Tuple[int, int]] = [(0, head_len)]
        tail_off = max(head_len, sz - CPAPP_BOUNDED_TAIL_BYTES_P205)
        if tail_off < sz:
            slices.append((tail_off, sz - tail_off))
        bytes_read = 0
        for off, ln in slices:
            if ln > 0:
                chunk = os.pread(fd, ln, off)
                bytes_read += len(chunk)
                for tok, b_tok in sh_enc:
                    sh_counts[tok] += chunk.count(b_tok)
                for tok, b_tok in fm_enc:
                    fm_counts[tok] += chunk.count(b_tok)
        return BoundedCpappSummaryP205(
            binary_name=binary_name,
            body_label=body_label,
            source_mode="LOCAL_DONOR_RDONLY",
            file_bytes=sz,
            bounded_bytes_read=bytes_read,
            shared_marker_hits=sh_counts,
            fx3_focusmap_marker_hits=fm_counts,
        )
    finally:
        os.close(fd)


def _scan_cpapp_buf_clean_room_p205(
    buf: bytes,
    *,
    binary_name: str,
    body_label: str,
    shared_tokens: Sequence[str],
    fx3_focusmap_tokens: Sequence[str],
) -> BoundedCpappSummaryP205:
    return BoundedCpappSummaryP205(
        binary_name=binary_name,
        body_label=body_label,
        source_mode="CLEAN_ROOM_SYNTHETIC",
        file_bytes=len(buf),
        bounded_bytes_read=len(buf),
        shared_marker_hits={t: buf.count(t.encode("ascii")) for t in shared_tokens},
        fx3_focusmap_marker_hits={
            t: buf.count(t.encode("ascii")) for t in fx3_focusmap_tokens
        },
    )


def build_clean_room_realhw_desqueeze_focusmap_shocklesswb_fixtures() -> Dict[str, bytes]:
    """Synthesize deterministic clean-room fixtures (`raw_firmware_bytes_leaked == 0`)."""
    fx3_appfw_tokens = (
        APPFW_SHARED_WAVE27_MARKERS_P205 + APPFW_FX3_702_EXCLUSIVE_MARKERS_P205
    )
    fx6_appfw_tokens = (
        APPFW_SHARED_WAVE27_MARKERS_P205 + APPFW_FX6_601_EXCLUSIVE_MARKERS_P205
    )

    fx3_appfw_elf = _build_synthetic_elf64(
        exports=("appfw_fx3_702_desqueeze_focusmap_shocklesswb_entry",),
        imports=("mpr_set_desqueeze_scale",),
        dt_needed=("libmpr.so", "libc.so"),
        rodata_strings=fx3_appfw_tokens,
    )
    fx6_appfw_elf = _build_synthetic_elf64(
        exports=("appfw_fx6_601_desqueeze_focusmap_shocklesswb_entry",),
        imports=("mpr_set_desqueeze_scale",),
        dt_needed=("libmpr.so", "libc.so"),
        rodata_strings=fx6_appfw_tokens,
    )

    fx3_uxc_en_f = (
        b"uxd\x07"
        + b"\x00" * 12
        + b"\x00".join(t.encode("utf-8") for t in UXC_FX3_EN_F_REQUIRED_TOKENS_P205)
        + b"\x00"
    )
    fx6_uxc_en = (
        b"uxd\x07"
        + b"\x00" * 12
        + b"\x00".join(t.encode("utf-8") for t in UXC_FX6_EN_REQUIRED_TOKENS_P205)
        + b"\x00"
    )
    fx3_cpapp_payload = (
        b"\x00".join(
            t.encode("ascii")
            for t in (CPAPP_SHARED_MARKERS_P205 + CPAPP_FX3_FOCUSMAP_MARKERS_P205)
        )
        + b"\x00"
    )
    fx6_cpapp_payload = (
        b"\x00".join(t.encode("ascii") for t in CPAPP_SHARED_MARKERS_P205) + b"\x00"
    )

    return {
        "fx3_appfw": fx3_appfw_elf,
        "fx6_appfw": fx6_appfw_elf,
        "fx3_uxc_en_f": fx3_uxc_en_f,
        "fx6_uxc_en": fx6_uxc_en,
        "fx3_cpapp": fx3_cpapp_payload,
        "fx6_cpapp": fx6_cpapp_payload,
    }


def _inspect_donors_or_clean_room_p205(
    *,
    clean_room: bool,
    repo_root: Path,
) -> Tuple[str, bool, float, Dict[str, object]]:
    """Bounded `O_RDONLY` donor inspection (< 0.15s cold, cached per process) or synthetic fallback."""
    t_start = time.perf_counter()
    all_appfw_scan_tokens = (
        APPFW_SHARED_WAVE27_MARKERS_P205
        + APPFW_FX3_702_EXCLUSIVE_MARKERS_P205
        + APPFW_FX6_601_EXCLUSIVE_MARKERS_P205
    )

    use_clean_room = bool(clean_room or is_forced_clean_room())
    donor_paths: Dict[str, Optional[Path]] = {}
    if not use_clean_room:
        rel_map = {
            "fx3_appfw": FX3_APPFW_P205_RELPATH,
            "fx6_appfw": FX6_APPFW_P205_RELPATH,
            "fx3_uxc_en_f": FX3_UXC_EN_F_P205_RELPATH,
            "fx6_uxc_en": FX6_UXC_EN_P205_RELPATH,
            "fx3_cpapp": FX3_CPAPP_P205_RELPATH,
            "fx6_cpapp": FX6_CPAPP_P205_RELPATH,
        }
        for key, rel in rel_map.items():
            donor_paths[key] = resolve_donor_file(rel, repo_root=repo_root)
        if any(p is None or not p.is_file() for p in donor_paths.values()):
            use_clean_room = True

    if use_clean_room:
        fx = build_clean_room_realhw_desqueeze_focusmap_shocklesswb_fixtures()
        fx3_elf = _scan_elf_buf_ordered(
            fx["fx3_appfw"],
            binary_name="appFw.so",
            body_label="FX3_702",
            source_mode="CLEAN_ROOM_SYNTHETIC",
            tokens=all_appfw_scan_tokens,
        )
        fx6_elf = _scan_elf_buf_ordered(
            fx["fx6_appfw"],
            binary_name="appFw.so",
            body_label="FX6_601",
            source_mode="CLEAN_ROOM_SYNTHETIC",
            tokens=all_appfw_scan_tokens,
        )
        fx3_uxc = _scan_uxc_buf_clean_room_p205(
            fx["fx3_uxc_en_f"],
            pack_name="string_english_f.uxc",
            body_label="FX3_702",
            required_tokens=UXC_FX3_EN_F_REQUIRED_TOKENS_P205,
        )
        fx6_uxc = _scan_uxc_buf_clean_room_p205(
            fx["fx6_uxc_en"],
            pack_name="string_english.uxc",
            body_label="FX6_601",
            required_tokens=UXC_FX6_EN_REQUIRED_TOKENS_P205,
        )
        fx3_cp = _scan_cpapp_buf_clean_room_p205(
            fx["fx3_cpapp"],
            binary_name="CPAPP-B.BIN",
            body_label="FX3_702",
            shared_tokens=CPAPP_SHARED_MARKERS_P205,
            fx3_focusmap_tokens=CPAPP_FX3_FOCUSMAP_MARKERS_P205,
        )
        fx6_cp = _scan_cpapp_buf_clean_room_p205(
            fx["fx6_cpapp"],
            binary_name="cpapp-b.bin",
            body_label="FX6_601",
            shared_tokens=CPAPP_SHARED_MARKERS_P205,
            fx3_focusmap_tokens=CPAPP_FX3_FOCUSMAP_MARKERS_P205,
        )
        bundle: Dict[str, object] = {
            "fx3_elf": fx3_elf,
            "fx6_elf": fx6_elf,
            "fx3_uxc": fx3_uxc,
            "fx6_uxc": fx6_uxc,
            "fx3_cp": fx3_cp,
            "fx6_cp": fx6_cp,
            "donor_sizes": {
                "fx3_appfw": fx3_elf.file_bytes,
                "fx6_appfw": fx6_elf.file_bytes,
                "fx3_string_english_f_uxc": fx3_uxc.file_bytes,
                "fx6_string_english_uxc": fx6_uxc.file_bytes,
                "fx3_cpapp_b_bin": fx3_cp.file_bytes,
                "fx6_cpapp_b_bin": fx6_cp.file_bytes,
            },
        }
        return (
            "CLEAN_ROOM_SYNTHETIC",
            False,
            round(time.perf_counter() - t_start, 6),
            bundle,
        )

    cache_key = tuple(str(donor_paths[k]) for k in sorted(donor_paths.keys()))
    if cache_key in _DONOR_SCAN_CACHE_P205:
        return (
            "LOCAL_DONOR_RDONLY",
            True,
            round(time.perf_counter() - t_start, 6),
            _DONOR_SCAN_CACHE_P205[cache_key],
        )

    p_fx3_app = donor_paths["fx3_appfw"]
    p_fx6_app = donor_paths["fx6_appfw"]
    p_fx3_uxc = donor_paths["fx3_uxc_en_f"]
    p_fx6_uxc = donor_paths["fx6_uxc_en"]
    p_fx3_cp = donor_paths["fx3_cpapp"]
    p_fx6_cp = donor_paths["fx6_cpapp"]
    assert p_fx3_app and p_fx6_app and p_fx3_uxc and p_fx6_uxc and p_fx3_cp and p_fx6_cp

    fx3_elf = _scan_elf_fast_rdonly(
        p_fx3_app,
        binary_name="appFw.so",
        body_label="FX3_702",
        tokens=all_appfw_scan_tokens,
    )
    fx6_elf = _scan_elf_fast_rdonly(
        p_fx6_app,
        binary_name="appFw.so",
        body_label="FX6_601",
        tokens=all_appfw_scan_tokens,
    )
    fx3_uxc = _scan_uxc_bounded_rdonly_p205(
        p_fx3_uxc,
        pack_name="string_english_f.uxc",
        body_label="FX3_702",
        required_tokens=UXC_FX3_EN_F_REQUIRED_TOKENS_P205,
    )
    fx6_uxc = _scan_uxc_bounded_rdonly_p205(
        p_fx6_uxc,
        pack_name="string_english.uxc",
        body_label="FX6_601",
        required_tokens=UXC_FX6_EN_REQUIRED_TOKENS_P205,
    )
    fx3_cp = _scan_cpapp_bounded_rdonly_p205(
        p_fx3_cp,
        binary_name="CPAPP-B.BIN",
        body_label="FX3_702",
        shared_tokens=CPAPP_SHARED_MARKERS_P205,
        fx3_focusmap_tokens=CPAPP_FX3_FOCUSMAP_MARKERS_P205,
    )
    fx6_cp = _scan_cpapp_bounded_rdonly_p205(
        p_fx6_cp,
        binary_name="cpapp-b.bin",
        body_label="FX6_601",
        shared_tokens=CPAPP_SHARED_MARKERS_P205,
        fx3_focusmap_tokens=CPAPP_FX3_FOCUSMAP_MARKERS_P205,
    )

    bundle = {
        "fx3_elf": fx3_elf,
        "fx6_elf": fx6_elf,
        "fx3_uxc": fx3_uxc,
        "fx6_uxc": fx6_uxc,
        "fx3_cp": fx3_cp,
        "fx6_cp": fx6_cp,
        "donor_sizes": {
            "fx3_appfw": fx3_elf.file_bytes,
            "fx6_appfw": fx6_elf.file_bytes,
            "fx3_string_english_f_uxc": fx3_uxc.file_bytes,
            "fx6_string_english_uxc": fx6_uxc.file_bytes,
            "fx3_cpapp_b_bin": fx3_cp.file_bytes,
            "fx6_cpapp_b_bin": fx6_cp.file_bytes,
        },
    }
    _DONOR_SCAN_CACHE_P205[cache_key] = bundle
    return (
        "LOCAL_DONOR_RDONLY",
        False,
        round(time.perf_counter() - t_start, 6),
        bundle,
    )


# ---------------------------------------------------------------------------
# Top-Level Phase 205 Auditor Entrypoint & Deterministic Serialization
# ---------------------------------------------------------------------------


def analyze_realhw_desqueeze_165x_focusmap_simult_and_shocklesswb(
    *,
    clean_room: bool = False,
    repo_root: Optional[Path] = None,
) -> RealhwDesqueeze165xFocusmapSimultAndShocklesswbReport:
    """Run the 43rd Firmware-Lab Auditor (`43/43` in `audit-all`)."""
    root = repo_root or DEFAULT_REPO_ROOT
    mode, cache_hit, elapsed, bundle = _inspect_donors_or_clean_room_p205(
        clean_room=clean_room,
        repo_root=root,
    )

    fx3_elf: ElfSectionSummary = bundle["fx3_elf"]  # type: ignore[assignment]
    fx6_elf: ElfSectionSummary = bundle["fx6_elf"]  # type: ignore[assignment]
    fx3_uxc: BoundedUxcSummaryP205 = bundle["fx3_uxc"]  # type: ignore[assignment]
    fx6_uxc: BoundedUxcSummaryP205 = bundle["fx6_uxc"]  # type: ignore[assignment]
    fx3_cp: BoundedCpappSummaryP205 = bundle["fx3_cp"]  # type: ignore[assignment]
    fx6_cp: BoundedCpappSummaryP205 = bundle["fx6_cp"]  # type: ignore[assignment]
    donor_sizes: Dict[str, int] = bundle["donor_sizes"]  # type: ignore[assignment]

    # --- Pillar 1: [De-Squeeze Display] 1.6x=1.65x, 4 Hard Locks & 5 Suppressions ---
    p1_errors: List[str] = []
    fx3_dsq_keys = (
        "N5model25setting_de_squeeze_disp_tE",
        "set_de_squeeze_disp_i",
        "set_param_anamo_desqueeze_scale_msg",
        "video_set_de_squeeze_disp",
        "BKID_APP_setting_de_squeeze_disp",
        "VAL_HAITA_setting_de_squeeze_disp_general_shooting_mode_DE_SQUEEZE_DISP_1_3X",
        "VAL_HAITA_setting_de_squeeze_disp_general_shooting_mode_DE_SQUEEZE_DISP_1_5X",
        "VAL_HAITA_setting_de_squeeze_disp_general_shooting_mode_DE_SQUEEZE_DISP_1_6X",
        "VAL_HAITA_setting_de_squeeze_disp_general_shooting_mode_DE_SQUEEZE_DISP_2_0X",
        "FOCUS_MODE_MF",
        "STEADY_SHOT_OFF",
        "FACE_DETECTION_IN_MULTI",
    )
    fx6_dsq_keys = (
        "N5model25setting_de_squeeze_disp_tE",
        "set_de_squeeze_disp_i",
        "set_param_anamo_desqueeze_scale_msg",
        "video_set_de_squeeze_disp",
        "PID_SET_ANAMO_DESQUEEZE_SCALE",
        "FOCUS_MODE_MF",
        "FACE_DETECTION_IN_MULTI",
    )
    fx3_dsq_hits = {k: fx3_elf.marker_hits.get(k, 0) for k in fx3_dsq_keys}
    fx6_dsq_hits = {k: fx6_elf.marker_hits.get(k, 0) for k in fx6_dsq_keys}

    for k, v in fx3_dsq_hits.items():
        if v < 1:
            p1_errors.append(f"MISSING_FX3_DESQUEEZE_MARKER:{k}")
    for k, v in fx6_dsq_hits.items():
        if v < 1:
            p1_errors.append(f"MISSING_FX6_DESQUEEZE_MARKER:{k}")
    if not fx3_uxc.uxc_magic_valid or not fx6_uxc.uxc_magic_valid:
        p1_errors.append("INVALID_UXC_CONTAINER_MAGIC")
    for k, v in fx3_uxc.required_token_hits.items():
        if v < 1:
            p1_errors.append(f"MISSING_FX3_UXC_TOKEN:{k}")
    for k, v in fx6_uxc.required_token_hits.items():
        if v < 1:
            p1_errors.append(f"MISSING_FX6_UXC_TOKEN:{k}")

    ev_165x_ok = evaluate_desqueeze_display_165x_locks_and_suppression(menu_state="1.6x")
    ev_off_ok = evaluate_desqueeze_display_165x_locks_and_suppression(
        menu_state="Off",
        focus_mode="AF-C",
        focus_area="Tracking: Spot M",
        steady_shot="Active",
        face_priority_in_multi_metering="On",
    )
    ev_lock_viol = evaluate_desqueeze_display_165x_locks_and_suppression(
        menu_state="1.6x",
        focus_mode="AF-C",
        steady_shot="Active",
    )
    ev_sup_raw = evaluate_desqueeze_display_165x_locks_and_suppression(
        menu_state="2.0x",
        hdmi_raw_output="On",
    )
    ev_sup_hdmi_only = evaluate_desqueeze_display_165x_locks_and_suppression(
        menu_state="1.6x",
        rec_media_dur_hdmi_output="Off(HDMI Only)",
        hdmi_info_display="On",
    )
    ev_sup_log_rem_photo = evaluate_desqueeze_display_165x_locks_and_suppression(
        menu_state="1.5x",
        log_shooting="Off",
        remote_shooting_active=True,
        capture_mode="Photo",
    )
    ev_pre700_rej = evaluate_desqueeze_display_165x_locks_and_suppression(
        menu_state="1.6x",
        firmware_version="6.01",
    )

    if not (
        ev_165x_ok.valid
        and ev_165x_ok.cinemascope_165x_stretch_applied
        and ev_165x_ok.four_hard_locks_active
    ):
        p1_errors.append("EVAL_16X_165X_LOCKS_FAILED")
    if not (ev_off_ok.valid and not ev_off_ok.four_hard_locks_active):
        p1_errors.append("EVAL_OFF_UNLOCK_FAILED")
    if ev_lock_viol.valid:
        p1_errors.append("EVAL_LOCK_VIOLATION_NOT_REJECTED")
    if not (ev_sup_raw.valid and ev_sup_raw.desqueeze_suppressed):
        p1_errors.append("EVAL_HDMI_RAW_SUPPRESSION_FAILED")
    if not (
        ev_sup_hdmi_only.valid
        and ev_sup_hdmi_only.desqueeze_suppressed
        and ev_sup_hdmi_only.hdmi_info_display_forced_off
        and ev_sup_hdmi_only.effective_hdmi_info_display == "Off"
    ):
        p1_errors.append("EVAL_OFF_HDMI_ONLY_SUPPRESSION_FAILED")
    if not (
        ev_sup_log_rem_photo.valid
        and len(ev_sup_log_rem_photo.suppression_reasons) == 3
    ):
        p1_errors.append("EVAL_LOG_REMOTE_PHOTO_SUPPRESSION_FAILED")
    if ev_pre700_rej.valid:
        p1_errors.append("EVAL_PRE700_16X_NOT_REJECTED")

    pillar_1 = Pillar1Desqueeze165xAndLocksReport(
        passed=len(p1_errors) == 0,
        fx3_appfw_desqueeze_hits=fx3_dsq_hits,
        fx6_appfw_desqueeze_hits=fx6_dsq_hits,
        fx3_uxc_en_f_summary=fx3_uxc,
        fx6_uxc_en_summary=fx6_uxc,
        eval_16x_applies_165x_with_4_hard_locks_ok=ev_165x_ok,
        eval_off_state_unlocks_af_and_ibis_ok=ev_off_ok,
        eval_lock_violation_afc_or_steadyshot_rejected=ev_lock_viol,
        eval_suppressed_by_hdmi_raw_output_ok=ev_sup_raw,
        eval_suppressed_by_off_hdmi_only_forces_info_off_ok=ev_sup_hdmi_only,
        eval_suppressed_by_log_off_remote_and_photo_ok=ev_sup_log_rem_photo,
        eval_pre_700_rejects_15x_16x_states=ev_pre700_rej,
        errors=tuple(p1_errors),
    )

    # --- Pillar 2: External M&C [Focus Map] & >=150fps Cutoff ---
    p2_errors: List[str] = []
    fx3_fm_keys = (
        "sequence_notify_focus_map",
        "view_mp_focus_map",
        "to_remote_event_focus_map",
    )
    fx6_inbody_fm_keys = (
        "BKID_APP_USER_MENU_FOCUS_MAP",
        "ASSIGNABLE_SWITCH_FOCUS_MAP",
        "EVENT_FUNC_FOCUS_MAP_ON",
        "EVENT_FUNC_FOCUS_MAP_OFF",
    )
    fx3_fm_hits = {k: fx3_elf.marker_hits.get(k, 0) for k in fx3_fm_keys}
    fx6_fm_in_fx6 = {k: fx6_elf.marker_hits.get(k, 0) for k in fx6_inbody_fm_keys}
    fx6_fm_in_fx3 = {k: fx3_elf.marker_hits.get(k, 0) for k in fx6_inbody_fm_keys}

    for k, v in fx3_fm_hits.items():
        if v < 1:
            p2_errors.append(f"MISSING_FX3_REMOTE_FOCUSMAP_MARKER:{k}")
    for k, v in fx6_fm_in_fx6.items():
        if v < 1:
            p2_errors.append(f"MISSING_FX6_INBODY_FOCUSMAP_MARKER:{k}")
    for k, v in fx6_fm_in_fx3.items():
        if v != 0:
            p2_errors.append(f"UNEXPECTED_INBODY_FOCUSMAP_MENU_IN_FX3:{k}={v}")
    for k, v in fx3_cp.shared_marker_hits.items():
        if v < 1:
            p2_errors.append(f"MISSING_FX3_CPAPP_SHARED_MARKER:{k}")
    for k, v in fx6_cp.shared_marker_hits.items():
        if v < 1:
            p2_errors.append(f"MISSING_FX6_CPAPP_SHARED_MARKER:{k}")
    for k, v in fx3_cp.fx3_focusmap_marker_hits.items():
        if v < 1:
            p2_errors.append(f"MISSING_FX3_CPAPP_FOCUSMAP_MARKER:{k}")

    ev_fm_120_ok = evaluate_external_mc_focus_map_and_150fps_cutoff(sensor_fps=120)
    ev_fm_fx3_6fps = evaluate_external_mc_focus_map_and_150fps_cutoff(
        camera_body="ILME-FX3", sensor_fps=6
    )
    ev_fm_fx6_6fps = evaluate_external_mc_focus_map_and_150fps_cutoff(
        camera_body="ILME-FX6", firmware_version="6.01", sensor_fps=6
    )
    ev_fm_240_cut = evaluate_external_mc_focus_map_and_150fps_cutoff(sensor_fps=240)
    ev_fm_adap_uvc_play = evaluate_external_mc_focus_map_and_150fps_cutoff(
        lens_state="MOUNT_ADAPTER_LA_EA5_OR_MANUAL",
        usb_uvc_streaming_active=True,
        camera_operating_state="PLAYBACK",
    )
    ev_fm_inbody_rej = evaluate_external_mc_focus_map_and_150fps_cutoff(
        requested_render_target="FX3_IN_BODY_LCD_OSD_OVERLAY",
        stage_b_inject_in_body_focus_map_overlay=True,
    )

    if not (ev_fm_120_ok.valid and ev_fm_120_ok.external_mc_focus_map_available):
        p2_errors.append("EVAL_FX3_MC_120FPS_FAILED")
    if not (
        ev_fm_fx3_6fps.external_mc_focus_map_available
        and ev_fm_fx3_6fps.fx3_low_fps_1_to_6_permitted
        and not ev_fm_fx6_6fps.external_mc_focus_map_available
    ):
        p2_errors.append("EVAL_FX3_VS_FX6_6FPS_ASYMMETRY_FAILED")
    if not (
        ev_fm_240_cut.valid
        and ev_fm_240_cut.hfr_150fps_cutoff_triggered
        and not ev_fm_240_cut.external_mc_focus_map_available
    ):
        p2_errors.append("EVAL_FX3_240FPS_CUTOFF_FAILED")
    if not (
        ev_fm_adap_uvc_play.valid
        and len(ev_fm_adap_uvc_play.cutoff_reasons) == 3
        and not ev_fm_adap_uvc_play.external_mc_focus_map_available
    ):
        p2_errors.append("EVAL_ADAPTER_UVC_PLAYBACK_CUTOFF_FAILED")
    if ev_fm_inbody_rej.valid:
        p2_errors.append("EVAL_STAGE_B_INBODY_OVERLAY_NOT_REJECTED")

    pillar_2 = Pillar2ExternalMcFocusMapReport(
        passed=len(p2_errors) == 0,
        fx3_appfw_focusmap_hits=fx3_fm_hits,
        fx6_appfw_inbody_focusmap_hits_in_fx6=fx6_fm_in_fx6,
        fx6_appfw_inbody_focusmap_hits_in_fx3=fx6_fm_in_fx3,
        fx3_cpapp_summary=fx3_cp,
        fx6_cpapp_summary=fx6_cp,
        eval_fx3_external_mc_24p_and_120p_ok=ev_fm_120_ok,
        eval_fx3_low_fps_1_to_6_permitted_vs_fx6_blocked=(
            ev_fm_fx3_6fps,
            ev_fm_fx6_6fps,
        ),
        eval_fx3_hfr_150_200_240fps_cutoff_blocked=ev_fm_240_cut,
        eval_fx3_mount_adapter_uvc_and_playback_blocked=ev_fm_adap_uvc_play,
        eval_stage_b_inbody_focus_map_overlay_rejected=ev_fm_inbody_rej,
        errors=tuple(p2_errors),
    )

    # --- Pillar 3: [Simult. + Auto Switch] & [Shockless WB] Bypass ---
    p3_errors: List[str] = []
    fx3_sw_keys = (
        "VAL_setting_movie_recording_media_MOVIE_RECORDING_MEDIA_SIMULTANEOUS_RECORDING",
        "SIMULT_REC",
        "setting_relay_rec_movie",
        "RELAY_REC_ON",
        "CAUTION_ID_2CARD_REQUIRED_SIMULTANEOIUS_FOR_MOVIE_RECORD",
        "N5model28setting_movie_shockless_wb_tE",
        "movie_shockless_wb_seq",
        "BKID_APP_setting_movie_shockless_wb",
        "MOVIE_SHOCKLESS_WB_OFF",
        "MOVIE_SHOCKLESS_WB_1",
        "MOVIE_SHOCKLESS_WB_2",
        "MOVIE_SHOCKLESS_WB_3",
        "BKID_APP_MENU_WB_COLOR_TEMP",
        "WHITE_BALANCE_COLOR_TEMP_COLOR_FILTER_5500K",
    )
    fx6_sw_keys = (
        "VAL_setting_movie_recording_media_MOVIE_RECORDING_MEDIA_SIMULTANEOUS_RECORDING",
        "BKID_APP_SETTING_SIMUL_REC",
        "RELAY_REC_ON",
        "N5model28setting_movie_shockless_wb_tE",
        "movie_shockless_wb_seq",
        "MOVIE_SHOCKLESS_WB_OFF",
        "MOVIE_SHOCKLESS_WB_1",
        "MOVIE_SHOCKLESS_WB_2",
        "MOVIE_SHOCKLESS_WB_3",
        "PID_SET_SHOCKLESS_GAIN_MODE",
    )
    fx3_sw_hits = {k: fx3_elf.marker_hits.get(k, 0) for k in fx3_sw_keys}
    fx6_sw_hits = {k: fx6_elf.marker_hits.get(k, 0) for k in fx6_sw_keys}

    for k, v in fx3_sw_hits.items():
        if v < 1:
            p3_errors.append(f"MISSING_FX3_SIMULT_WB_MARKER:{k}")
    for k, v in fx6_sw_hits.items():
        if v < 1:
            p3_errors.append(f"MISSING_FX6_SIMULT_WB_MARKER:{k}")

    ev_sim_cont = evaluate_simult_recording_and_auto_switch_media(
        auto_switch_media="On",
        slot1_remaining_sec=120.0,
        slot2_remaining_sec=1800.0,
        elapsed_rec_sec=300.0,
    )
    ev_sim_swap = evaluate_simult_recording_and_auto_switch_media(
        auto_switch_media="On",
        slot1_remaining_sec=120.0,
        slot2_remaining_sec=1800.0,
        elapsed_rec_sec=300.0,
        hot_swap_fresh_card_into_exhausted_slot=True,
    )
    ev_sim_strict = evaluate_simult_recording_and_auto_switch_media(
        auto_switch_media="Off",
        slot1_remaining_sec=120.0,
        slot2_remaining_sec=1800.0,
        elapsed_rec_sec=300.0,
    )
    ev_sim_1card = evaluate_simult_recording_and_auto_switch_media(
        slot1_inserted=True,
        slot2_inserted=False,
    )

    ev_swb_24 = evaluate_shockless_wb_and_ctemp_grid_bypass(
        shockless_wb_setting="2",
        frame_rate_fps=24.0,
        trigger_type="WB_MODE_SWITCH_PRESET_TO_CUSTOM",
    )
    ev_swb_240 = evaluate_shockless_wb_and_ctemp_grid_bypass(
        shockless_wb_setting="3 (Slow)",
        frame_rate_fps=240.0,
        trigger_type="WB_MODE_SWITCH_MEMORY_A_TO_B",
    )
    ev_swb_kelvin = evaluate_shockless_wb_and_ctemp_grid_bypass(
        shockless_wb_setting="3 (Slow)",
        frame_rate_fps=24.0,
        trigger_type="CTEMP_KELVIN_DIRECT_EDIT",
        ctemp_kelvin=4300,
    )
    ev_swb_grid = evaluate_shockless_wb_and_ctemp_grid_bypass(
        shockless_wb_setting="3 (Slow)",
        frame_rate_fps=119.88,
        trigger_type="AB_GM_FINE_GRID_SHIFT",
        ab_grid_offset=2.5,
        gm_grid_offset=-1.5,
    )

    if not (
        ev_sim_cont.valid
        and ev_sim_cont.recording_continues
        and ev_sim_cont.single_card_continuation_active
        and ev_sim_cont.active_slots == ("Slot 2",)
    ):
        p3_errors.append("EVAL_SIMULT_SINGLE_CARD_CONTINUATION_FAILED")
    if not (
        ev_sim_swap.valid
        and ev_sim_swap.resumed_dual_slot_after_card_swap
        and ev_sim_swap.active_slots == ("Slot 1", "Slot 2")
    ):
        p3_errors.append("EVAL_SIMULT_HOTSWAP_RESUME_FAILED")
    if not (
        ev_sim_strict.valid
        and not ev_sim_strict.recording_continues
        and ev_sim_strict.strict_dual_backup_halt_enforced
    ):
        p3_errors.append("EVAL_SIMULT_STRICT_DUAL_HALT_FAILED")
    if ev_sim_1card.valid:
        p3_errors.append("EVAL_SIMULT_MISSING_CARD_NOT_REJECTED")
    if not (
        ev_swb_24.valid
        and ev_swb_24.shockless_smoothing_applied
        and ev_swb_24.transition_frames > 0
        and ev_swb_240.valid
        and ev_swb_240.shockless_smoothing_applied
        and ev_swb_240.transition_frames > ev_swb_24.transition_frames
    ):
        p3_errors.append("EVAL_SHOCKLESS_WB_ALL_FPS_SMOOTHING_FAILED")
    if not (
        ev_swb_kelvin.valid
        and ev_swb_kelvin.immediate_bypass_triggered
        and ev_swb_kelvin.transition_frames == 0
        and ev_swb_grid.valid
        and ev_swb_grid.immediate_bypass_triggered
        and ev_swb_grid.transition_frames == 0
    ):
        p3_errors.append("EVAL_SHOCKLESS_WB_KELVIN_OR_GRID_BYPASS_FAILED")

    pillar_3 = Pillar3SimultAutoSwitchAndShocklessWbReport(
        passed=len(p3_errors) == 0,
        fx3_appfw_simult_wb_hits=fx3_sw_hits,
        fx6_appfw_simult_wb_hits=fx6_sw_hits,
        eval_simult_auto_switch_on_single_card_continuation_ok=ev_sim_cont,
        eval_simult_auto_switch_on_card_hotswap_resumes_dual_ok=ev_sim_swap,
        eval_simult_auto_switch_off_strict_dual_halt_ok=ev_sim_strict,
        eval_simult_missing_second_card_at_start_rejected=ev_sim_1card,
        eval_shockless_wb_preset_smoothed_at_24p_and_240fps_ok=(
            ev_swb_24,
            ev_swb_240,
        ),
        eval_shockless_wb_ctemp_kelvin_immediate_bypass_0frames_ok=ev_swb_kelvin,
        eval_shockless_wb_ab_gm_grid_immediate_bypass_0frames_ok=ev_swb_grid,
        errors=tuple(p3_errors),
    )

    # --- Pillar 4: Write Firewall & 12-Touchpoint Matrix ---
    p4_errors: List[str] = []
    g_p2 = evaluate_phase205_write_guard("p2:/setting/Backup.bin")
    g_bk = evaluate_phase205_write_guard("/setting/Backup.bin")
    g_cp = evaluate_phase205_write_guard("/firmware/CPAPP-B.BIN")
    g_lf = evaluate_phase205_write_guard("p18:/lens/LENSFILE.BIN")
    g_nor = evaluate_phase205_write_guard("spi_nor:/loader_nor.bin")
    g_ok_ov = evaluate_phase205_write_guard(
        "/tmp/fx6_wave27_overlay/desqueeze_wb_state.json"
    )
    g_ok_ram = evaluate_phase205_write_guard(
        "ram://fx6_wave27_shadow/focusmap_mc_state"
    )
    matrix = build_phase205_compat_matrix()

    for g_blk in (g_p2, g_bk, g_cp, g_lf, g_nor):
        if g_blk.valid or not g_blk.persistent_write_blocked:
            p4_errors.append(f"WRITE_GUARD_FAILED_TO_BLOCK:{g_blk.target_path}")
    for g_ok in (g_ok_ov, g_ok_ram):
        if not g_ok.valid or not g_ok.volatile_overlay_allowed:
            p4_errors.append(f"WRITE_GUARD_BLOCKED_VOLATILE:{g_ok.target_path}")
    if matrix.total_touchpoints != 12 or sum(matrix.class_counts.values()) != 12:
        p4_errors.append("INVALID_PHASE205_COMPAT_MATRIX_COUNTS")

    pillar_4 = Pillar4Phase205WriteGuardAndMatrixReport(
        passed=len(p4_errors) == 0,
        blocked_p2_setting_eval=g_p2,
        blocked_backup_bin_eval=g_bk,
        blocked_cpapp_bin_eval=g_cp,
        blocked_lensfile_bin_eval=g_lf,
        blocked_spi_nor_eval=g_nor,
        allowed_wave27_overlay_eval=g_ok_ov,
        allowed_ram_shadow_eval=g_ok_ram,
        compatibility_matrix=matrix,
        errors=tuple(p4_errors),
    )

    all_errors = tuple(p1_errors + p2_errors + p3_errors + p4_errors)
    all_ok = (
        pillar_1.passed
        and pillar_2.passed
        and pillar_3.passed
        and pillar_4.passed
        and len(all_errors) == 0
    )

    hash_payload = repr(
        (
            PHASE_205_SCHEMA,
            PHASE_205_VERSION,
            "43/43",
            mode,
            all_ok,
            donor_sizes,
            asdict(pillar_1),
            asdict(pillar_2),
            asdict(pillar_3),
            asdict(pillar_4),
            all_errors,
        )
    ).encode("utf-8")
    digest = hashlib.sha256(hash_payload).hexdigest()

    return RealhwDesqueeze165xFocusmapSimultAndShocklesswbReport(
        schema_version=PHASE_205_SCHEMA,
        phase_version=PHASE_205_VERSION,
        auditor_index="43/43",
        mode=mode,
        cache_hit=cache_hit,
        cold_or_cached_scan_elapsed_sec=elapsed,
        all_checks_passed=all_ok,
        o_rdonly_enforced=True,
        raw_firmware_bytes_leaked=0,
        persistent_emmc_writes_authorized=False,
        spi_nor_write_authorized=False,
        el3_payload_transmit_authorized=False,
        physical_usb_packets_emitted=0,
        in_body_focus_map_overlay_injected=False,
        persistent_writes=0,
        calibration_mutation_bytes=0,
        desqueeze_165x_locks_and_suppression_verified=pillar_1.passed,
        external_mc_focus_map_150fps_cutoff_verified=pillar_2.passed,
        simult_auto_switch_and_shockless_wb_bypass_verified=pillar_3.passed,
        zero_write_firewall_and_matrix_verified=pillar_4.passed,
        donor_file_sizes=donor_sizes,
        pillar_1_desqueeze_165x_locks=pillar_1,
        pillar_2_external_mc_focus_map=pillar_2,
        pillar_3_simult_and_shockless_wb=pillar_3,
        pillar_4_write_guard_matrix=pillar_4,
        report_sha256=digest,
        errors=all_errors,
    )


def _normalize_json_value_p205(obj: object) -> object:
    if isinstance(obj, dict):
        return {str(k): _normalize_json_value_p205(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_normalize_json_value_p205(v) for v in obj]
    return obj


def realhw_desqueeze_165x_focusmap_simult_and_shocklesswb_report_to_dict(
    report: RealhwDesqueeze165xFocusmapSimultAndShocklesswbReport,
) -> Dict[str, object]:
    """Convert `RealhwDesqueeze165xFocusmapSimultAndShocklesswbReport` to deterministic JSON-ready dict."""
    raw = asdict(report)
    raw.pop("cold_or_cached_scan_elapsed_sec", None)
    raw.pop("cache_hit", None)
    return _normalize_json_value_p205(raw)  # type: ignore[return-value]
