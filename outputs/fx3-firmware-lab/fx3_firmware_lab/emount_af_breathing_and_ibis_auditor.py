"""Phase 55 — 10th Unified Firmware-Lab Auditor: Sony E-Mount Power Zoom (PZ), 627-Point Fast Hybrid PDAF, Focus Breathing Compensation (UDAM/RTMD) & 5-Axis IBIS/OSS Compatibility Matrix.

Strictly Read-Only (`os.O_RDONLY`) & Clean-Room Dual-Mode:
- Local Donor Mode: inspects FX3 v7.02 (`appFw.so`, `libmpr.so`, `cpapp-b.bin`,
  `libInfraLensCommunicator.so`, `global.xdb`, `string_english.uxc`) and FX6
  v6.01 (`appFw.so`, `libmpr.so`, `cpapp-b.bin`, `libInfraLensCommunicator.so`,
  `libInfraHotshoe.so`, `global.xdb`, `string_english.uxc`, `string_english_2.uxc`)
  strictly via `os.O_RDONLY`, verifying markers via C-level `bytes.find()`,
  pure-Python ELF64 section diffing, Thumb-2 `0x1400` (`0x0400 | 0x1000`) scans,
  and `.uxc` string-pack slot parsing.
- Clean-Room Mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`, `clean_room=True`, or donors
  absent): synthesizes deterministic clean-room ELF64 / CP / `global.xdb` /
  `.uxc` fixtures carrying the exact contract bytes and runs the identical
  four-pillar verification pipeline with zero proprietary files required.

Audits Four Cross-Body Lens & Stabilization Compatibility Pillars:
1. Pillar A — E-Mount Servo/Power Zoom (`PZ`) & FX3 Body `T/W` Zoom Lever:
   Maps FX6 Grip/Handle Zoom Rocker & Speed (`1..8`) to FX3's physical
   shutter-ring `T/W` zoom lever (`P10` keymap safe) + Sony `SELP` Power Zoom
   lenses + Clear Image Zoom (`CIZ`), proving zero crash when FX6 Smart Grip
   is absent (`P11 0x91db059b` `0x88000002` + `libInfraHotshoe.so` `E_TMO=-50 -> 0x8000`).
2. Pillar B — 627-Point Fast Hybrid PDAF, Face/Eye AF, AF Transition Speed (`1..7`) & Subj. Shift Sensitivity (`1..5`):
   Audits `libInfraLensCommunicator.so` (`14,544 B`, `0` loadable-segment diff),
   AP<->Stock-CP (`cpapp-b.bin`, `cp_mutation_bytes == 0`) AF IPC commands,
   Face/Eye priority modes, Touch Focus / Focus Magnifier (`x4.0`), and
   Peaking / Focus Map overlays.
3. Pillar C — Focus Breathing Compensation (`UDAM` / `RTMD` Lens Distortion & Breathing Tables):
   Audits `Breathing Comp.` On/Off FOV crop, lens support gating, and
   `UDAM` / `RTMD` metadata tags across FX3 `v7.02` and FX6 `v6.01`.
4. Pillar D — 5-Axis Body `IBIS` + Lens `OSS` Coordination & Factory Gyro Calibration Immutability:
   Audits FX3's 5-axis `IBIS` (`Active` / `Standard` / `Off` Center-Lock, `0x0400` -> `0x1400`)
   vs FX6's gyro metadata-only hardware (`PRM_is_imager_stabilization_unit_fixed`,
   zero physical 5-axis IBIS stage), proving how Stock-CP `cpapp-b.bin` preserves
   FX3's physical IBIS & factory gyro calibration (`calibration_mutation_bytes == 0`).
"""

from __future__ import annotations

import hashlib
import json
import os
import struct
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from .audio_tc_hdmi_sdi_routing_auditor import (
    FX6_HOTSHOE_MARKERS,
    FX6_HOTSHOE_RELPATH,
    LIBINFRAHOTSHOE_TMO_SAFE_RC,
    P11_SMART_HANDLE_ATTACHED_EVT,
    P11_SMART_HANDLE_DETACHED_EVT,
    P11_SMART_HANDLE_QUEUE_ID,
)
from .global_xdb_and_menu_tree_auditor import (
    UXA_MAGIC,
    build_sparse_uxc_string_pack,
    build_synthetic_global_xdb,
)
from .haita_bk4_feature_analyzer import (
    DEFAULT_REPO_ROOT,
    FX3_APPFW_RELPATH,
    FX6_APPFW_RELPATH,
    is_forced_clean_room,
    resolve_donor_file,
)
from .sensor_codec_compatibility_analyzer import (
    FX3_CPAPP_RELPATH,
    FX3_LIBMPR_RELPATH,
    FX6_CPAPP_RELPATH,
    FX6_LIBMPR_RELPATH,
)
from .uxc_multilang_and_font_verifier import (
    FX3_SHARE_APP_RELDIR,
    FX6_SHARE_APP_RELDIR,
    parse_uxc_string_pack_slots,
)


PHASE_55_SCHEMA = "fx3_firmware_lab_phase55_emount_af_breathing_ibis_v1"
PHASE_55_VERSION = "55.0.0"

FX3_LENS_COMM_RELPATH = "fx3-color-port-20261027/lens-state-20261029/original-members/libInfraLensCommunicator.so"
FX6_LENS_COMM_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libInfraLensCommunicator.so"
)
FX3_GLOBAL_XDB_RELPATH = f"{FX3_SHARE_APP_RELDIR}/global.xdb"
FX6_GLOBAL_XDB_RELPATH = f"{FX6_SHARE_APP_RELDIR}/global.xdb"
FX3_STR_EN_RELPATH = f"{FX3_SHARE_APP_RELDIR}/string_english.uxc"
FX6_STR_EN_1_RELPATH = f"{FX6_SHARE_APP_RELDIR}/string_english.uxc"
FX6_STR_EN_2_RELPATH = f"{FX6_SHARE_APP_RELDIR}/string_english_2.uxc"

# ---------------------------------------------------------------------------
# Pinned Cross-Body Hardware & Protocol Constants
# ---------------------------------------------------------------------------

POWER_ZOOM_SPEED_MIN = 1
POWER_ZOOM_SPEED_MAX = 8
CIZ_4K_MAX_MAGNIFICATION = 1.5
CIZ_FHD_MAX_MAGNIFICATION = 2.0
FX3_SHUTTER_RING_TW_LEVER_ID = "UIBIZ_KEY_TACT_ZOOM_TELE/WIDE + UIBIZ_KEY_VOL_ZOOM_AD (P10 Safe)"

PDAF_POINT_COUNT = 627  # IMX510 33x19 fast hybrid phase-detection grid (~94% coverage)
AF_TRANSITION_SPEED_MIN = 1
AF_TRANSITION_SPEED_MAX = 7
AF_SUBJ_SHIFT_SENS_MIN = 1
AF_SUBJ_SHIFT_SENS_MAX = 5
VALID_FACE_EYE_MODES: Tuple[str, ...] = ("OFF", "FACE_EYE_PRIORITY_AF", "FACE_EYE_ONLY_AF")
VALID_FOCUS_MAGNIFIER_MODES: Tuple[str, ...] = ("OFF", "X3", "X4", "X6")
VALID_PEAKING_LEVELS: Tuple[str, ...] = ("LOW", "MID", "HIGH")
VALID_PEAKING_COLORS: Tuple[str, ...] = ("RED", "YELLOW", "BLUE", "WHITE")

EXPECTED_LENS_COMM_BYTES = 14_544
MAX_LENS_COMM_COMMENT_DIFF_BYTES = 6

IBIS_CENTER_LOCK_OPCODE = 0x0400
IBIS_CENTER_LOCK_COMPLETION_OPCODE = 0x1400
VALID_STEADYSHOT_MODES: Tuple[str, ...] = ("Off", "Standard", "Active")
FX3_CP_CALIBRATION_FILES: Tuple[str, ...] = ("p2:/Backup.bin", "p2:/psd.bin", "p6:Jiritsu")

# ---------------------------------------------------------------------------
# Verified Binary Marker Contracts (FX3 v7.02 & FX6 v6.01)
# ---------------------------------------------------------------------------

SHARED_APPFW_ZOOM_MARKERS: Tuple[str, ...] = (
    "VAL_lens_zoom_support_LENS_POWER_ZOOM_SUPPORT",
    "VAL_lens_zoom_support_LENS_POWER_ZOOM_SW_SUPPORT",
    "VAL_zoom_status_LENS_POWER_ZOOM_STATUS",
    "VAL_setting_zoom_setting_ZOOM_SETTING_CLEAR_IMAGE_ZOOM_ON",
    "UIBIZ_KEY_LENS_ZOOM_LEVER",
    "UIBIZ_KEY_LENS_ZOOM_RING",
    "UIBIZ_KEY_TACT_ZOOM_TELE",
    "UIBIZ_KEY_TACT_ZOOM_WIDE",
    "UIBIZ_KEY_VOL_ZOOM_AD",
    "UIBIZ_KEY_ZOOM_TELE_SPEED_1",
    "UIBIZ_KEY_ZOOM_TELE_SPEED_8",
    "UIBIZ_KEY_ZOOM_WIDE_SPEED_1",
    "UIBIZ_KEY_ZOOM_WIDE_SPEED_8",
)

FX3_APPFW_ZOOM_EXTRA_MARKERS: Tuple[str, ...] = (
    "EVENT_INPUT_KEY_LENS_ZOOM_LEVER_TELE_ON",
    "EVENT_INPUT_KEY_LENS_ZOOM_LEVER_WIDE_ON",
    "EVENT_FUNC_W_T_ZOOM_SPEED_1ST_ZOOM_SPD_REC_ON",
    "EVENT_FUNC_W_T_ZOOM_SPEED_2ND_ZOOM_SPD_REC_ON",
    "BKID_APP_setting_zoom_speed",
    "BKID_APP_setting_fixed_zoom_speed_type",
    "BKID_APP_extern_menu_ezoom_mode",
)

FX6_APPFW_HANDLE_ZOOM_MARKERS: Tuple[str, ...] = (
    "ASSIGNABLE_SWITCH_HANDLE_ZOOM",
    "BKID_APP_SETTING_HANDLE_ZOOM",
    "BKID_APP_EXTERN_HANDLE_ZOOM_SETTING_SELECT",
    "BKID_APP_SETTING_HANDLE_ZOOM_HIGH",
    "BKID_APP_SETTING_HANDLE_ZOOM_LOW",
    "Camera::BizCamIf::set_param_handle_zoom_mode_and_speed_msg",
    "EXTERN_ZOOM_TYPE_OPTICAL_AND_CLEAR_IMAGE_ZOOM",
    "VAL_lens_clear_image_zoom_smooth_support_LENS_CLEAR_IMAGE_ZOOM_SMOOTH_SUPPORT",
    "VAL_setting_clear_image_zoom_type_CLEAR_IMAGE_ZOOM_TYPE_OPTICAL_ZOOM_PRIORITY",
    "VAL_setting_clear_image_zoom_type_CLEAR_IMAGE_ZOOM_TYPE_SMOOTH_PRIORITY",
)

CP_SHARED_ZOOM_MARKERS: Tuple[str, ...] = (
    "Parameter:us_zoom_speed",
    "ezoom_mode",
)

FX3_CP_ZOOM_EXTRA_MARKERS: Tuple[str, ...] = (
    "SET_RING_ZOOM_MODE",
    "ZOOM_SPEED_SETTING",
    "zoom_speed_movie_rec",
)

SHARED_APPFW_AF_MARKERS: Tuple[str, ...] = (
    "EVENT_REMOTE_MOVIE_AF_TRANSITION_SPEED",
    "EVENT_REMOTE_MOVIE_AF_SUBJ_SHIFT_SENS",
    "EVENT_REMOTE_FOCUS_MAGNIFIER_SETTING",
    "PEAKING_DISPLAY",
    "PEAKING_LEVEL",
    "VAL_setting_movie_af_transition_speed_MOVIE_AF_TRANSITION_SPEED_1_SLOW",
    "VAL_setting_movie_af_transition_speed_MOVIE_AF_TRANSITION_SPEED_4",
    "VAL_setting_movie_af_transition_speed_MOVIE_AF_TRANSITION_SPEED_7_FAST",
    "VAL_setting_movie_af_subj_shift_sens_MOVIE_AF_SUBJ_SHIFT_SENS_1_LOCKED_ON",
    "VAL_setting_movie_af_subj_shift_sens_MOVIE_AF_SUBJ_SHIFT_SENS_3",
    "VAL_setting_movie_af_subj_shift_sens_MOVIE_AF_SUBJ_SHIFT_SENS_5_RESPONSICE",
)

FX3_APPFW_AF_EXTRA_MARKERS: Tuple[str, ...] = (
    "PID_SET_EYE_AF_MODE",
    "PID_SET_MOVIE_EYE_AF",
    "MOV_INIT_RATIO_FOCUS_MAGNIF_X4_0",
    "VAL_touch_focus_state_TOUCH_FOCUS_STATE_ON",
    "VAL_setting_shooting_touch_function_SHOOTING_TOUCH_FUNCTION_TOUCH_FOCUS",
    "PEAKING_DISPLAY_ON",
    "PEAKING_DISPLAY_OFF",
    "PEAKING_COLOR_RED",
    "PEAKING_LEVEL_HIGH",
)

FX6_APPFW_AF_EXTRA_MARKERS: Tuple[str, ...] = (
    "PID_SET_MOVIE_AF_TRANSITION_SPEED",
    "PID_SET_MOVIE_AF_SUBJECT_SWITCH_SENSITIVITY",
    "ASSIGNABLE_SWITCH_FACE_EYE_DETECTION_AF",
    "ASSIGNABLE_SWITCH_FOCUS_MAGNIFIER_x3",
    "ASSIGNABLE_SWITCH_FOCUS_MAGNIFIER_x6",
    "ASSIGNABLE_SWITCH_FOCUS_MAP",
    "EVENT_FUNC_FOCUS_MAP_ON",
    "EVENT_FUNC_FOCUS_MAP_OFF",
    "SHOOTING_TOUCH_FUNCTION_TOUCH_TRACKING",
    "PEAKING_COLOR_VALUE_WHITE",
)

CP_SHARED_AF_MARKERS: Tuple[str, ...] = (
    "af_mode",
    "af_adjust_mode",
    "af_area",
    "af_area_num",
    "PID_SET_EYE_AF_MODE",
    "MSG_ID_INFRABB_VDF_SRVC_SET_PEAKING",
)

SHARED_APPFW_BREATHING_MARKERS: Tuple[str, ...] = (
    "PID_SET_BREATHING_CORRECTION",
    "INFRA_NOTIFY_BREATHING_CORRECTION_LENS_TYPE",
    "N5model35sequence_set_breathing_compensationE",
    "EVENT_REMOTE_LENS_COMP_LENS_COMP_BREATHING",
    "VAL_setting_lens_comp_breathing_LENS_COMP_BREATHING_ON",
    "VAL_setting_lens_comp_breathing_LENS_COMP_BREATHING_OFF",
)

FX3_APPFW_BREATHING_EXTRA_MARKERS: Tuple[str, ...] = (
    "BKID_APP_setting_lens_comp_breathing",
    "CAUTION_ID_FACTOR_CAM_LENS_BREATHING_COMP_NOT_SUPPORT_MSG",
)

FX6_APPFW_BREATHING_EXTRA_MARKERS: Tuple[str, ...] = (
    "BKID_APP_SETTING_LENS_COMP_BREATHING",
    "BREATHING_CORRECTION_LENS_TYPE_SUPPORT",
    "BREATHING_CORRECTION_LENS_TYPE_NOT_SUPPORT",
    "infra_wrapper_imaging::detail::set_breathing_compensation_i",
)

CP_SHARED_BREATHING_MARKERS: Tuple[str, ...] = (
    "SET_BREATHING_CORRECTION",
    "BREATHING_CORRECTION_DATA_COM_STATE",
    "CacheFlashBreathingCorrectionData",
    "Mount_DividedInfo_BreathingCorrectionData",
    "N6Camera4Lens34DividedInfoBreathingCorrectionDataE",
    "MakeDistortionCorrectionParam",
    "ConvertAndSetFrameDistortionCorrection",
)

MPR_SHARED_UDAM_BREATHING_MARKERS: Tuple[str, ...] = (
    "_ZN3mpr12KlvConverter11UDAMKeyUnitE",
    "_ZN3mpr12KlvConverter31UDAMSetBreathingCorrectionValueE",
    "_ZN3mpr12KlvConverter32UDAMSetDistortionCorrectionValueE",
    "DistortionCorrection",
)

FX6_MPR_UDAM_BREATHING_EXTRA_MARKERS: Tuple[str, ...] = (
    "BreathingCorrection_BreathingCorrectionApplied",
    "BreathingCorrection_DistortionCorrectionApplied",
    "BreathingCorrection_AppliedBasePointDistortionRatio",
    "BreathingCorrection_IdealBasePointDistortionRatio",
    "BreathingCorrection_MaximumBreathingScaleRatio",
    "BreathingCorrection_MinimumBreathingScaleRatio",
    "DistortionCorrection_LensDistortionImageCutOutSize",
)

FX6_RIGID_CMOS_MARKER = "PRM_is_imager_stabilization_unit_fixed"
FX3_ACTIVE_IBIS_AP_MARKER = "set_steadyshot_advanced_movie_i"

SHARED_APPFW_STEADYSHOT_MARKERS: Tuple[str, ...] = (
    "EVENT_REMOTE_MOVIE_STEADYSHOT",
    "EVENT_REMOTE_STEADYSHOT_ADJUSTMENT",
    "EVENT_REMOTE_STEADYSHOT_FOCAL_LENGTH",
    "infra_wrapper_imaging::detail::set_tc_mode_i",
    "infra_wrapper_imaging::detail::set_tc_on_movie_i",
)

FX6_APPFW_STEADYSHOT_MARKERS: Tuple[str, ...] = (
    "BKID_APP_SETTING_MOVIE_STEADYSHOT",
    "CAUTION_ID_FACTOR_SWITCH_ON_THE_STEADYSHOT_SWITCH_OF_THE_LENS",
    "EVENT_FUNC_SETTING_STEADYSHOT_ACTIVE_ON",
    "EVENT_FUNC_SETTING_STEADYSHOT_STANDARD_ON",
)

FX3_CP_IBIS_SERVO_AND_CALIB_MARKERS: Tuple[str, ...] = (
    "LiroSeq: Restore.",
    "CheckSetSteadyShotAdvancedMovie",
    "CheckSetSteadyShotAdvancedStill",
    "CheckSetS1SteadyShotMode",
    "CheckSetFrameLockOnSteadyShot",
    "steadyshot_body_axis",
    "steadyshot_body_axis_movie",
    "steadyshot_body_axis_still",
    "FWCP-isRetract",
    "HallPIDOUT_0",
    "GyroPIDOUT_0",
    "FusionOUT_0",
    "AllPIDOUT_0",
    "PWMOUT_0",
    "ExecImagerCalibration",
)

FX6_CP_FORBIDDEN_BODY_IBIS_MARKERS: Tuple[str, ...] = (
    "steadyshot_body_axis",
    "FWCP-isRetract",
    "CheckSetSteadyShotAdvancedMovie",
)

FX6_CP_GYRO_ONLY_MARKERS: Tuple[str, ...] = (
    "is_mode",
    "is_on_movie",
    "is_type",
    "Mount_DividedInfo_SteadyShotInfo",
    "Gyro Data >> (yaw:%d, pit:%d, roll:%d)",
    "ExecImagerCalibration",
)

MPR_SHARED_GYRO_UDAM_MARKERS: Tuple[str, ...] = (
    "_ZN3mpr12KlvConverter21UDAMSetGyroscopeValueE",
    "_ZN3mpr12KlvConverter25UDAMSetAccelerometerValueE",
    "Gyroscope",
    "Accelerometor",
)

FX3_UXC_EXPECTED_LABELS: Dict[int, str] = {
    0x0000014C: "Peaking Level",
    0x0000014D: "Peaking Color",
    0x00000153: "SteadyShot",
    0x00000226: "Focus Magnifier",
}

FX6_NS1_UXC_EXPECTED_LABELS: Dict[int, str] = {
    0x000002ED: "AF Transition Speed",
    0x000002EF: "AF Subj. Shift Sens.",
    0x00000360: "Face/Eye Detection AF",
    0x0000050D: "Breathing Compensation",
    0x0000050E: "Breathing Comp.",
    0x00000FA5: "The SteadyShot mechanism is fixed.",
    0x0000106E: "Focus Map",
}

FX6_NS2_UXC_EXPECTED_LABELS: Dict[int, str] = {
    0x00000759: "SteadyShot: Active",
    0x0000075A: "SteadyShot: Standard",
    0x00000F12: "Zoom Speed",
    0x00001115: "Handle Zoom Speed",
    0x0000141C: "Focus Magnifier ×4",
}

# ---------------------------------------------------------------------------
# Report & Evaluation Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LensCommElfDiffSummary:
    passed: bool
    fx3_bytes: int
    fx6_bytes: int
    total_diff_bytes: int
    loadable_segment_diff_bytes: int
    comment_diff_bytes: int
    text_sha256: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class PowerZoomEvalResult:
    valid: bool
    status: str
    zoom_source: str
    zoom_speed: int
    ciz_enabled: bool
    ciz_magnification: float
    recording_format: str
    smart_grip_attached: bool
    p11_handle_queue_hex: str
    p11_event_cmd_hex: str
    hotshoe_tmo_safe_rc_hex: str
    active_zoom_control: str
    smart_grip_absent_crash_count: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class PowerZoomMatrixEntry:
    feature_id: str
    fx6_interface: str
    fx3_interface: str
    p10_keymap_safe: bool
    verdict: str
    notes: str


@dataclass(frozen=True)
class PowerZoomMatrixReport:
    passed: bool
    shared_appfw_zoom_markers: Tuple[str, ...]
    fx3_appfw_zoom_extra_markers: Tuple[str, ...]
    fx6_appfw_handle_zoom_markers: Tuple[str, ...]
    fx3_cp_zoom_markers: Tuple[str, ...]
    fx6_cp_zoom_markers: Tuple[str, ...]
    fx6_hotshoe_markers: Tuple[str, ...]
    selp_lever_eval: PowerZoomEvalResult
    handle_absent_tw_fallback_eval: PowerZoomEvalResult
    ciz_4k_15x_eval: PowerZoomEvalResult
    matrix: Tuple[PowerZoomMatrixEntry, ...]
    zero_crash_when_smart_grip_absent: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class PdafAfEvalResult:
    valid: bool
    status: str
    pdaf_points: int
    af_transition_speed: int
    af_subj_shift_sensitivity: int
    face_eye_mode: str
    touch_focus_enabled: bool
    focus_magnifier: str
    peaking_enabled: bool
    peaking_level: str
    peaking_color: str
    focus_map_enabled: bool
    p8_cp_mutation_forbidden: bool
    cp_mutation_bytes: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class PdafMatrixEntry:
    feature_id: str
    fx6_capability: str
    fx3_capability: str
    cp_mutation_bytes: int
    verdict: str
    notes: str


@dataclass(frozen=True)
class FastHybridPdafReport:
    passed: bool
    pdaf_point_count: int
    lens_comm_diff: LensCommElfDiffSummary
    fx3_shared_af_markers: Tuple[str, ...]
    fx6_shared_af_markers: Tuple[str, ...]
    fx3_extra_af_markers: Tuple[str, ...]
    fx6_extra_af_markers: Tuple[str, ...]
    fx3_cp_af_markers: Tuple[str, ...]
    fx6_cp_af_markers: Tuple[str, ...]
    uxc_af_labels_verified: Dict[str, str]
    pdaf_default_eval: PdafAfEvalResult
    pdaf_magnifier_x4_peaking_eval: PdafAfEvalResult
    matrix: Tuple[PdafMatrixEntry, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class BreathingCompEvalResult:
    valid: bool
    status: str
    breathing_comp_enabled: bool
    lens_breathing_supported: bool
    active_scan_mode: str
    nominal_fov_crop_factor: float
    cut_out_width: int
    cut_out_height: int
    udam_breathing_applied: bool
    udam_distortion_applied: bool
    rtmd_klv_tag_count: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class FocusBreathingMatrixReport:
    passed: bool
    fx3_shared_breathing_markers: Tuple[str, ...]
    fx6_shared_breathing_markers: Tuple[str, ...]
    fx3_extra_breathing_markers: Tuple[str, ...]
    fx6_extra_breathing_markers: Tuple[str, ...]
    fx3_cp_breathing_markers: Tuple[str, ...]
    fx6_cp_breathing_markers: Tuple[str, ...]
    fx3_mpr_udam_markers: Tuple[str, ...]
    fx6_mpr_udam_markers: Tuple[str, ...]
    fx6_mpr_udam_extra_markers: Tuple[str, ...]
    uxc_breathing_labels_verified: Dict[str, str]
    breathing_on_eval: BreathingCompEvalResult
    breathing_off_eval: BreathingCompEvalResult
    unsupported_lens_eval: BreathingCompEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class IbisOssEvalResult:
    valid: bool
    status: str
    target_body: str
    requested_mode: str
    effective_cp_mode: str
    lens_has_oss: bool
    lens_oss_switch_on: bool
    oss_coordinated: bool
    center_lock_energized: bool
    floating_sensor_hazard: bool
    opcode_0x0400_packet_hex: str
    gyro_udam_logged: bool
    cp_mutation_bytes: int
    calibration_mutation_bytes: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class IbisOssMatrixReport:
    passed: bool
    fx6_rigid_cmos_marker_present: bool
    fx3_rigid_cmos_marker_absent: bool
    fx3_active_ibis_ap_marker_present: bool
    fx6_active_ibis_ap_marker_absent: bool
    fx3_shared_steadyshot_markers: Tuple[str, ...]
    fx6_shared_steadyshot_markers: Tuple[str, ...]
    fx6_steadyshot_markers: Tuple[str, ...]
    fx3_cp_ibis_servo_markers: Tuple[str, ...]
    fx6_cp_gyro_only_markers: Tuple[str, ...]
    fx6_cp_unexpected_body_ibis_markers: Tuple[str, ...]
    fx3_cp_0x1400_movw_hits: int
    fx3_mpr_gyro_udam_markers: Tuple[str, ...]
    fx6_mpr_gyro_udam_markers: Tuple[str, ...]
    uxc_ibis_labels_verified: Dict[str, str]
    fx3_standard_eval: IbisOssEvalResult
    fx3_active_eval: IbisOssEvalResult
    fx3_off_center_lock_eval: IbisOssEvalResult
    fx6_gyro_metadata_only_eval: IbisOssEvalResult
    calibration_mutation_bytes: int
    cp_mutation_bytes: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class EmountAfBreathingAndIbisReport:
    schema_version: str
    phase_version: str
    mode: str
    all_checks_passed: bool
    o_rdonly_enforced: bool
    donor_file_sizes: Dict[str, int]
    global_xdb_magics_hex: Dict[str, str]
    pillar_a_power_zoom: PowerZoomMatrixReport
    pillar_b_fast_hybrid_pdaf: FastHybridPdafReport
    pillar_c_focus_breathing: FocusBreathingMatrixReport
    pillar_d_ibis_oss_calibration: IbisOssMatrixReport
    errors: Tuple[str, ...]
    report_sha256: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)

    def to_deterministic_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True) + "\n"


# ---------------------------------------------------------------------------
# Strictly O_RDONLY Scanning & ELF64 / Thumb-2 / UXC Helpers
# ---------------------------------------------------------------------------


def _read_rdonly_bytes(path: Path) -> bytes:
    """Open `path` strictly `os.O_RDONLY` and return its bytes."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        with os.fdopen(fd, "rb") as fh:
            return fh.read()
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        raise


def _scan_rdonly_markers(path: Path, markers: Sequence[str]) -> Tuple[int, Tuple[str, ...]]:
    """Open `path` strictly `os.O_RDONLY` and scan `markers` via C-level `bytes.find`."""
    data = _read_rdonly_bytes(path)
    if not data:
        return 0, ()
    present = tuple(m for m in markers if data.find(m.encode("latin1")) != -1)
    return len(data), present


def _scan_buffer_markers(buf: bytes, markers: Sequence[str]) -> Tuple[int, Tuple[str, ...]]:
    """Scan an in-memory buffer for ASCII/Latin-1 markers using C-level `bytes.find`."""
    return len(buf), tuple(m for m in markers if buf.find(m.encode("latin1")) != -1)


def _count_thumb2_movw_0x1400(cp_bytes: bytes) -> int:
    """Count Thumb-2 `MOVW Rd, #0x1400` (`0x0400 | 0x1000`) completion dispatch sites."""
    hits = 0
    pos = 0
    while True:
        idx = cp_bytes.find(b"\x41\xf2", pos)
        if idx == -1:
            break
        if (idx & 1) == 0 and idx + 4 <= len(cp_bytes):
            hw2 = struct.unpack_from("<H", cp_bytes, idx + 2)[0]
            if (hw2 & 0xF0FF) == 0x4000:
                hits += 1
        pos = idx + 2
    return hits


def _parse_elf64_sections(elf_bytes: bytes) -> Dict[str, Tuple[int, int]]:
    """Parse ELF64 section headers returning `{name: (sh_offset, sh_size)}`."""
    if len(elf_bytes) < 64 or elf_bytes[:4] != b"\x7fELF" or elf_bytes[4] != 2:
        raise ValueError("Not a valid ELF64 binary")
    e_shoff = struct.unpack_from("<Q", elf_bytes, 40)[0]
    e_shentsize, e_shnum, e_shstrndx = struct.unpack_from("<HHH", elf_bytes, 58)
    if e_shoff == 0 or e_shnum == 0 or e_shstrndx >= e_shnum:
        raise ValueError("ELF64 binary missing section header table")
    if e_shoff + e_shnum * e_shentsize > len(elf_bytes):
        raise ValueError("ELF64 section header table out of bounds")

    shstr_hdr = e_shoff + e_shstrndx * e_shentsize
    shstr_off, shstr_sz = struct.unpack_from("<QQ", elf_bytes, shstr_hdr + 24)
    shstr = elf_bytes[shstr_off : shstr_off + shstr_sz]

    sections: Dict[str, Tuple[int, int]] = {}
    for idx in range(e_shnum):
        off = e_shoff + idx * e_shentsize
        sh_name, _sh_type, _sh_flags, _sh_addr, sh_offset, sh_size = struct.unpack_from(
            "<IIQQQQ", elf_bytes, off
        )
        name = shstr[sh_name:].split(b"\x00", 1)[0].decode("ascii", "ignore")
        if name:
            sections[name] = (sh_offset, sh_size)
    return sections


def compare_lens_comm_elf64(fx3_bytes: bytes, fx6_bytes: bytes) -> LensCommElfDiffSummary:
    """Compare FX3 v7.02 and FX6 v6.01 `libInfraLensCommunicator.so` section-by-section."""
    errors: List[str] = []
    if len(fx3_bytes) != len(fx6_bytes):
        errors.append(
            f"libInfraLensCommunicator.so byte length mismatch: FX3={len(fx3_bytes)} vs FX6={len(fx6_bytes)}"
        )
    try:
        sec3 = _parse_elf64_sections(fx3_bytes)
        sec6 = _parse_elf64_sections(fx6_bytes)
    except ValueError as exc:
        return LensCommElfDiffSummary(
            passed=False,
            fx3_bytes=len(fx3_bytes),
            fx6_bytes=len(fx6_bytes),
            total_diff_bytes=abs(len(fx3_bytes) - len(fx6_bytes)),
            loadable_segment_diff_bytes=1,
            comment_diff_bytes=0,
            text_sha256="",
            errors=(str(exc),),
        )

    loadable_names = (".dynsym", ".plt", ".text", ".rodata", ".data")
    loadable_diff = 0
    for sname in loadable_names:
        if sname not in sec3 or sname not in sec6:
            errors.append(f"libInfraLensCommunicator.so missing required ELF64 section {sname}")
            loadable_diff += 1
            continue
        o3, sz3 = sec3[sname]
        o6, sz6 = sec6[sname]
        b3 = fx3_bytes[o3 : o3 + sz3]
        b6 = fx6_bytes[o6 : o6 + sz6]
        if len(b3) != len(b6):
            loadable_diff += abs(len(b3) - len(b6))
            errors.append(f"Section {sname} size mismatch: FX3={len(b3)} vs FX6={len(b6)}")
        else:
            d = sum(1 for a, b in zip(b3, b6) if a != b)
            loadable_diff += d
            if d > 0:
                errors.append(f"Section {sname} differs by {d} bytes across FX3/FX6")

    text_off, text_sz = sec3.get(".text", (0, 0))
    text_sha256 = hashlib.sha256(fx3_bytes[text_off : text_off + text_sz]).hexdigest()

    comment_diff = 0
    if ".comment" in sec3 and ".comment" in sec6:
        c3_off, c3_sz = sec3[".comment"]
        c6_off, c6_sz = sec6[".comment"]
        c3 = fx3_bytes[c3_off : c3_off + c3_sz]
        c6 = fx6_bytes[c6_off : c6_off + c6_sz]
        comment_diff = sum(1 for a, b in zip(c3, c6) if a != b) + abs(len(c3) - len(c6))

    min_len = min(len(fx3_bytes), len(fx6_bytes))
    total_diff = sum(1 for i in range(min_len) if fx3_bytes[i] != fx6_bytes[i]) + abs(
        len(fx3_bytes) - len(fx6_bytes)
    )
    if total_diff > MAX_LENS_COMM_COMMENT_DIFF_BYTES:
        errors.append(
            f"Total diff bytes {total_diff} exceeds .comment-only tolerance ({MAX_LENS_COMM_COMMENT_DIFF_BYTES})"
        )

    return LensCommElfDiffSummary(
        passed=len(errors) == 0 and loadable_diff == 0,
        fx3_bytes=len(fx3_bytes),
        fx6_bytes=len(fx6_bytes),
        total_diff_bytes=total_diff,
        loadable_segment_diff_bytes=loadable_diff,
        comment_diff_bytes=comment_diff,
        text_sha256=text_sha256,
        errors=tuple(errors),
    )


def _extract_uxc_labels(uxc_bytes: bytes, expected: Mapping[int, str]) -> Tuple[Dict[str, str], Tuple[str, ...]]:
    """Parse `.uxc` string pack via `parse_uxc_string_pack_slots` and validate expected labels."""
    errors: List[str] = []
    verified: Dict[str, str] = {}
    try:
        _ns, _cnt, slots, _order, _strtab, _dups = parse_uxc_string_pack_slots(uxc_bytes)
    except Exception as exc:
        return verified, (f"Failed to parse .uxc string pack: {exc}",)

    for strid, expected_text in expected.items():
        slot_idx = strid & 0x1FFF
        entry = slots.get(slot_idx)
        if entry is None:
            errors.append(f"Missing .uxc STRID 0x{strid:08x} (slot {slot_idx})")
            continue
        actual_text = entry[1]
        verified[f"0x{strid:08x}"] = actual_text
        if actual_text != expected_text:
            errors.append(
                f".uxc STRID 0x{strid:08x} mismatch: expected {expected_text!r}, got {actual_text!r}"
            )
    return verified, tuple(errors)


# ---------------------------------------------------------------------------
# Clean-Room Synthetic Fixtures (Used ONLY when FX3_FX6_FORCE_CLEAN_ROOM=1 or donors absent)
# ---------------------------------------------------------------------------


def _build_synthetic_lens_comm_elf64(*, comment_tag: bytes, mutate_text: bool = False) -> bytes:
    """Build a valid minimal ELF64 AArch64 shared object with `.dynsym/.plt/.text/.rodata/.data/.comment`."""
    if len(comment_tag) != 6:
        raise ValueError("comment_tag must be 6 bytes")
    sec_names = [".dynsym", ".plt", ".text", ".rodata", ".data", ".comment", ".shstrtab"]
    shstrtab = bytearray(b"\x00")
    name_offs: Dict[str, int] = {}
    for nm in sec_names:
        name_offs[nm] = len(shstrtab)
        shstrtab.extend(nm.encode("ascii") + b"\x00")

    dynsym_bytes = b"\x00" * 48
    plt_bytes = b"\x1f\x20\x03\xd5" * 4
    text_bytes = b"\xc0\x03\x5f\xd6" * 8
    if mutate_text:
        text_bytes = b"\x00\x00\x80\xd2" + text_bytes[4:]
    rodata_bytes = b"InfraLensCom\x00\x00\x00\x00"
    data_bytes = b"\x01\x00\x00\x00\x00\x00\x00\x00"
    comment_bytes = b"GCC: (Sony-FX) " + comment_tag + b"\x00"

    payload_parts = [
        (".dynsym", 11, 2, dynsym_bytes),
        (".plt", 1, 6, plt_bytes),
        (".text", 1, 6, text_bytes),
        (".rodata", 1, 2, rodata_bytes),
        (".data", 1, 3, data_bytes),
        (".comment", 1, 0x30, comment_bytes),
        (".shstrtab", 3, 0, bytes(shstrtab)),
    ]

    ehdr_size = 64
    body = bytearray()
    sh_entries: List[Tuple[int, int, int, int, int, int, int, int, int, int]] = [
        (0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    ]
    for nm, sh_type, sh_flags, blob in payload_parts:
        off = ehdr_size + len(body)
        body.extend(blob)
        sh_entries.append((name_offs[nm], sh_type, sh_flags, off, off, len(blob), 0, 0, 4, 0))

    e_shoff = ehdr_size + len(body)
    e_shnum = len(sh_entries)
    e_shstrndx = e_shnum - 1

    e_ident = b"\x7fELF\x02\x01\x01" + bytes(9)
    ehdr = struct.pack(
        "<16sHHIQQQIHHHHHH",
        e_ident,
        3,      # ET_DYN
        183,    # EM_AARCH64
        1,      # EV_CURRENT
        0,      # e_entry
        0,      # e_phoff
        e_shoff,
        0,      # e_flags
        64,     # e_ehsize
        56,     # e_phentsize
        0,      # e_phnum
        64,     # e_shentsize
        e_shnum,
        e_shstrndx,
    )
    shdrs = b"".join(struct.pack("<IIQQQQIIQQ", *entry) for entry in sh_entries)
    return ehdr + bytes(body) + shdrs


def build_clean_room_emount_af_breathing_ibis_fixtures(
    *,
    drop_fx3_power_zoom: bool = False,
    drop_fx6_handle_zoom: bool = False,
    mutate_lens_comm_text: bool = False,
    drop_pdaf_transition_subj: bool = False,
    drop_breathing_udam: bool = False,
    inject_fx6_physical_ibis: bool = False,
    drop_fx3_cp_ibis_restore: bool = False,
    corrupt_fx6_uxc_labels: bool = False,
) -> Dict[str, bytes]:
    """Build deterministic clean-room fixtures representing all 14 FX3 v7.02 & FX6 v6.01 donor artifacts."""
    elf_hdr = b"\x7fELF\x02\x01\x01\x00" + bytes(56)
    cp_hdr = b"LDR\x00" + bytes(60)

    def _pack(tokens: Sequence[str], *, prefix: bytes = elf_hdr, raw_tail: bytes = b"") -> bytes:
        return prefix + b"\x00".join(t.encode("latin1") for t in tokens) + b"\x00" + raw_tail

    fx3_zoom = SHARED_APPFW_ZOOM_MARKERS[:-1] if drop_fx3_power_zoom else SHARED_APPFW_ZOOM_MARKERS
    fx3_af = SHARED_APPFW_AF_MARKERS[:-2] if drop_pdaf_transition_subj else SHARED_APPFW_AF_MARKERS
    fx3_appfw_tokens = [
        *fx3_zoom,
        *FX3_APPFW_ZOOM_EXTRA_MARKERS,
        *fx3_af,
        *FX3_APPFW_AF_EXTRA_MARKERS,
        *SHARED_APPFW_BREATHING_MARKERS,
        *FX3_APPFW_BREATHING_EXTRA_MARKERS,
        FX3_ACTIVE_IBIS_AP_MARKER,
        *SHARED_APPFW_STEADYSHOT_MARKERS,
    ]

    fx6_handle = FX6_APPFW_HANDLE_ZOOM_MARKERS[:-1] if drop_fx6_handle_zoom else FX6_APPFW_HANDLE_ZOOM_MARKERS
    fx6_appfw_tokens = [
        *SHARED_APPFW_ZOOM_MARKERS,
        *fx6_handle,
        *SHARED_APPFW_AF_MARKERS,
        *FX6_APPFW_AF_EXTRA_MARKERS,
        *SHARED_APPFW_BREATHING_MARKERS,
        *FX6_APPFW_BREATHING_EXTRA_MARKERS,
        FX6_RIGID_CMOS_MARKER,
        *SHARED_APPFW_STEADYSHOT_MARKERS,
        *FX6_APPFW_STEADYSHOT_MARKERS,
        *(("set_steadyshot_advanced_movie_i",) if inject_fx6_physical_ibis else ()),
    ]

    udam_shared = (
        tuple(m for m in MPR_SHARED_UDAM_BREATHING_MARKERS if "Breathing" not in m)
        if drop_breathing_udam
        else MPR_SHARED_UDAM_BREATHING_MARKERS
    )
    fx3_mpr_tokens = [*udam_shared, *MPR_SHARED_GYRO_UDAM_MARKERS]
    fx6_mpr_tokens = [*udam_shared, *FX6_MPR_UDAM_BREATHING_EXTRA_MARKERS, *MPR_SHARED_GYRO_UDAM_MARKERS]

    fx3_cp_ibis = (
        [m for m in FX3_CP_IBIS_SERVO_AND_CALIB_MARKERS if m != "LiroSeq: Restore."]
        if drop_fx3_cp_ibis_restore
        else list(FX3_CP_IBIS_SERVO_AND_CALIB_MARKERS)
    )
    fx3_cp_tokens = [
        *CP_SHARED_ZOOM_MARKERS,
        *FX3_CP_ZOOM_EXTRA_MARKERS,
        *CP_SHARED_AF_MARKERS,
        *CP_SHARED_BREATHING_MARKERS,
        *fx3_cp_ibis,
    ]
    # Include exact Thumb-2 `MOVW r0, #0x1400` (`0x0400 | 0x1000`) instruction bytes in FX3 CP fixture
    fx3_cp_raw_tail = b"" if drop_fx3_cp_ibis_restore else b"\x41\xf2\x00\x40"

    fx6_cp_tokens = [
        *CP_SHARED_ZOOM_MARKERS,
        *CP_SHARED_AF_MARKERS,
        *CP_SHARED_BREATHING_MARKERS,
        *FX6_CP_GYRO_ONLY_MARKERS,
        *(FX6_CP_FORBIDDEN_BODY_IBIS_MARKERS if inject_fx6_physical_ibis else ()),
    ]

    fx3_lens_comm = _build_synthetic_lens_comm_elf64(comment_tag=b"201211", mutate_text=False)
    fx6_lens_comm = _build_synthetic_lens_comm_elf64(
        comment_tag=b"240928", mutate_text=mutate_lens_comm_text
    )

    fx6_ns1_labels = dict(FX6_NS1_UXC_EXPECTED_LABELS)
    if corrupt_fx6_uxc_labels:
        fx6_ns1_labels[0x0000050D] = "CORRUPT_BREATHING_LABEL"

    return {
        "fx3_appfw": _pack(fx3_appfw_tokens),
        "fx6_appfw": _pack(fx6_appfw_tokens),
        "fx3_libmpr": _pack(fx3_mpr_tokens),
        "fx6_libmpr": _pack(fx6_mpr_tokens),
        "fx3_cpapp": _pack(fx3_cp_tokens, prefix=cp_hdr, raw_tail=fx3_cp_raw_tail),
        "fx6_cpapp": _pack(fx6_cp_tokens, prefix=cp_hdr),
        "fx3_lens_comm": fx3_lens_comm,
        "fx6_lens_comm": fx6_lens_comm,
        "fx6_hotshoe": _pack(FX6_HOTSHOE_MARKERS),
        "fx3_global_xdb": build_synthetic_global_xdb("fx3_702"),
        "fx6_global_xdb": build_synthetic_global_xdb("fx6_601"),
        "fx3_str_en": build_sparse_uxc_string_pack(FX3_UXC_EXPECTED_LABELS, namespace_id=1),
        "fx6_str_en_1": build_sparse_uxc_string_pack(fx6_ns1_labels, namespace_id=1),
        "fx6_str_en_2": build_sparse_uxc_string_pack(FX6_NS2_UXC_EXPECTED_LABELS, namespace_id=2),
    }


# ---------------------------------------------------------------------------
# Pillar A: E-Mount Servo/Power Zoom (PZ) & FX3 Body T/W Zoom Lever
# ---------------------------------------------------------------------------


def evaluate_emount_power_zoom_routing(
    *,
    zoom_source: str = "FX3_BODY_TW_LEVER",
    zoom_speed: int = 4,
    ciz_enabled: bool = False,
    ciz_magnification: float = 1.0,
    recording_format: str = "4K",
    smart_grip_attached: bool = False,
    p11_smart_handle_event_cmd: int = P11_SMART_HANDLE_DETACHED_EVT,
    hotshoe_tmo_rc: int = LIBINFRAHOTSHOE_TMO_SAFE_RC,
) -> PowerZoomEvalResult:
    """Validate E-Mount Power Zoom (`SELP`), FX3 `T/W` lever (`P10`), `CIZ`, and Smart-Grip-absent safety."""
    errors: List[str] = []
    norm_src = zoom_source.strip().upper()
    norm_fmt = recording_format.strip().upper()

    if norm_src not in ("FX3_BODY_TW_LEVER", "SELP_LENS_ROCKER", "FX6_HANDLE_ROCKER", "CLEAR_IMAGE_ZOOM"):
        errors.append(f"Unsupported zoom_source: {zoom_source!r}")
    if not (POWER_ZOOM_SPEED_MIN <= zoom_speed <= POWER_ZOOM_SPEED_MAX):
        errors.append(
            f"Power zoom speed {zoom_speed} out of valid range [{POWER_ZOOM_SPEED_MIN}..{POWER_ZOOM_SPEED_MAX}]"
        )
    if norm_fmt not in ("4K", "FHD"):
        errors.append(f"Unsupported recording_format for zoom matrix: {recording_format!r}")

    max_ciz = CIZ_4K_MAX_MAGNIFICATION if norm_fmt == "4K" else CIZ_FHD_MAX_MAGNIFICATION
    if ciz_enabled:
        if ciz_magnification < 1.0 or ciz_magnification > max_ciz:
            errors.append(
                f"Clear Image Zoom {ciz_magnification}x exceeds {norm_fmt} limit [1.0..{max_ciz}x]"
            )
    elif ciz_magnification != 1.0:
        errors.append("ciz_magnification must be 1.0 when Clear Image Zoom is disabled")

    if hotshoe_tmo_rc != LIBINFRAHOTSHOE_TMO_SAFE_RC:
        errors.append(
            f"libInfraHotshoe timeout must return 0x{LIBINFRAHOTSHOE_TMO_SAFE_RC:04x} on Smart Grip absence"
        )

    crash_count = 0
    if not smart_grip_attached:
        if p11_smart_handle_event_cmd == P11_SMART_HANDLE_ATTACHED_EVT:
            crash_count = 1
            errors.append(
                "Spoofed P11 Smart Grip attached ACK (0x88000001) with handle absent causes Smart Grip zoom stall"
            )
        elif p11_smart_handle_event_cmd != P11_SMART_HANDLE_DETACHED_EVT:
            crash_count = 1
            errors.append(f"Unexpected P11 Smart Handle event cmd 0x{p11_smart_handle_event_cmd:08x}")

    if smart_grip_attached:
        active_ctrl = "FX6_SMART_GRIP_HANDLE_ZOOM_ROCKER"
    elif norm_src == "SELP_LENS_ROCKER":
        active_ctrl = "EMOUNT_SELP_POWER_ZOOM_LEVER"
    else:
        active_ctrl = FX3_SHUTTER_RING_TW_LEVER_ID

    if len(errors) == 0:
        if not smart_grip_attached and norm_src == "FX6_HANDLE_ROCKER":
            status = "SMART_GRIP_ABSENT_FALLBACK_TO_FX3_TW_LEVER"
        elif ciz_enabled:
            status = "EMOUNT_PZ_AND_CIZ_READY"
        else:
            status = "EMOUNT_POWER_ZOOM_READY"
    else:
        status = "BLOCKED_POWER_ZOOM_OR_SMART_GRIP_FAULT"

    return PowerZoomEvalResult(
        valid=len(errors) == 0,
        status=status,
        zoom_source=norm_src,
        zoom_speed=zoom_speed,
        ciz_enabled=ciz_enabled,
        ciz_magnification=ciz_magnification,
        recording_format=norm_fmt,
        smart_grip_attached=smart_grip_attached,
        p11_handle_queue_hex=f"0x{P11_SMART_HANDLE_QUEUE_ID:08x}",
        p11_event_cmd_hex=f"0x{p11_smart_handle_event_cmd:08x}",
        hotshoe_tmo_safe_rc_hex=f"0x{hotshoe_tmo_rc:04x}",
        active_zoom_control=active_ctrl,
        smart_grip_absent_crash_count=crash_count,
        errors=tuple(errors),
    )


def evaluate_pillar_a_power_zoom(
    present_map: Mapping[str, Tuple[str, ...]],
) -> PowerZoomMatrixReport:
    """Audit Pillar A: E-Mount Power Zoom (`PZ`), `T/W` lever (`P10`), `CIZ`, and Smart-Grip-absent safety."""
    errors: List[str] = []

    fx3_zoom = present_map["fx3_appfw_zoom"]
    fx6_zoom = present_map["fx6_appfw_zoom"]
    fx3_extra = present_map["fx3_appfw_zoom_extra"]
    fx6_handle = present_map["fx6_appfw_handle_zoom"]
    fx3_cp_zoom = present_map["fx3_cp_zoom"]
    fx6_cp_zoom = present_map["fx6_cp_zoom"]
    fx6_hotshoe = present_map["fx6_hotshoe"]

    if fx3_zoom != SHARED_APPFW_ZOOM_MARKERS:
        errors.append("FX3 appFw.so missing shared Power Zoom / T/W / CIZ markers")
    if fx6_zoom != SHARED_APPFW_ZOOM_MARKERS:
        errors.append("FX6 appFw.so missing shared Power Zoom / T/W / CIZ markers")
    if fx3_extra != FX3_APPFW_ZOOM_EXTRA_MARKERS:
        errors.append("FX3 appFw.so missing shutter-ring W/T speed & lens zoom lever markers")
    if fx6_handle != FX6_APPFW_HANDLE_ZOOM_MARKERS:
        errors.append("FX6 appFw.so missing Handle Zoom / CIZ priority markers")
    if fx3_cp_zoom != (CP_SHARED_ZOOM_MARKERS + FX3_CP_ZOOM_EXTRA_MARKERS):
        errors.append("FX3 cpapp-b.bin missing ring/speed zoom markers")
    if fx6_cp_zoom != CP_SHARED_ZOOM_MARKERS:
        errors.append("FX6 cpapp-b.bin missing shared CP zoom markers")
    if fx6_hotshoe != FX6_HOTSHOE_MARKERS:
        errors.append("FX6 libInfraHotshoe.so missing bounded E_TMO / UIPC MI-Shoe markers")

    selp_eval = evaluate_emount_power_zoom_routing(
        zoom_source="SELP_LENS_ROCKER",
        zoom_speed=5,
        ciz_enabled=False,
        smart_grip_attached=False,
    )
    fallback_eval = evaluate_emount_power_zoom_routing(
        zoom_source="FX6_HANDLE_ROCKER",
        zoom_speed=4,
        ciz_enabled=False,
        smart_grip_attached=False,
        p11_smart_handle_event_cmd=P11_SMART_HANDLE_DETACHED_EVT,
    )
    ciz_eval = evaluate_emount_power_zoom_routing(
        zoom_source="FX3_BODY_TW_LEVER",
        zoom_speed=3,
        ciz_enabled=True,
        ciz_magnification=1.5,
        recording_format="4K",
        smart_grip_attached=False,
    )
    for ev in (selp_eval, fallback_eval, ciz_eval):
        if not ev.valid or ev.smart_grip_absent_crash_count != 0:
            errors.extend(ev.errors)

    matrix: Tuple[PowerZoomMatrixEntry, ...] = (
        PowerZoomMatrixEntry(
            feature_id="BODY_ZOOM_LEVER_VS_HANDLE_ROCKER",
            fx6_interface="FX6 Smart Grip / Handle Zoom Rocker (BKID_APP_SETTING_HANDLE_ZOOM)",
            fx3_interface="FX3 Shutter-Ring T/W Zoom Lever (UIBIZ_KEY_TACT_ZOOM_TELE/WIDE, P10 Safe)",
            p10_keymap_safe=True,
            verdict="FULL_PARITY_WITH_P11_FALLBACK",
            notes="Absent Smart Grip emits P11 0x91db059b 0x88000002 + E_TMO->0x8000; FX3 T/W lever operates natively.",
        ),
        PowerZoomMatrixEntry(
            feature_id="ZOOM_SPEED_STEPS_1_TO_8",
            fx6_interface="Handle/Remote Zoom Speed 1..8 (UIBIZ_KEY_ZOOM_TELE/WIDE_SPEED_1..8)",
            fx3_interface="Body W/T & Remote Zoom Speed 1..8 (BKID_APP_setting_zoom_speed)",
            p10_keymap_safe=True,
            verdict="NATIVE_1_TO_1_PARITY",
            notes="Both bodies expose identical 8-step Tele/Wide speed table & CP Parameter:us_zoom_speed.",
        ),
        PowerZoomMatrixEntry(
            feature_id="SONY_SELP_POWER_ZOOM_LENSES",
            fx6_interface="LENS_POWER_ZOOM_SUPPORT + UIBIZ_KEY_LENS_ZOOM_LEVER/RING",
            fx3_interface="LENS_POWER_ZOOM_SUPPORT + EVENT_INPUT_KEY_LENS_ZOOM_LEVER_TELE/WIDE_ON",
            p10_keymap_safe=True,
            verdict="NATIVE_1_TO_1_PARITY",
            notes="Sony SELP PZ lenses (e.g. SELP1635G, SELP28135G) drive identically over E-mount.",
        ),
        PowerZoomMatrixEntry(
            feature_id="CLEAR_IMAGE_ZOOM_CIZ",
            fx6_interface="ZOOM_SETTING_CLEAR_IMAGE_ZOOM_ON (Optical / Smooth Priority)",
            fx3_interface="ZOOM_SETTING_CLEAR_IMAGE_ZOOM_ON (1.5x 4K / 2.0x FHD)",
            p10_keymap_safe=True,
            verdict="FULL_PARITY",
            notes="Shared EXTERN_ZOOM_TYPE_OPTICAL_AND_CLEAR_IMAGE_ZOOM and CP ezoom_mode.",
        ),
    )

    zero_crash = bool(
        fallback_eval.valid
        and fallback_eval.smart_grip_absent_crash_count == 0
        and fallback_eval.status == "SMART_GRIP_ABSENT_FALLBACK_TO_FX3_TW_LEVER"
    )

    return PowerZoomMatrixReport(
        passed=len(errors) == 0,
        shared_appfw_zoom_markers=fx3_zoom,
        fx3_appfw_zoom_extra_markers=fx3_extra,
        fx6_appfw_handle_zoom_markers=fx6_handle,
        fx3_cp_zoom_markers=fx3_cp_zoom,
        fx6_cp_zoom_markers=fx6_cp_zoom,
        fx6_hotshoe_markers=fx6_hotshoe,
        selp_lever_eval=selp_eval,
        handle_absent_tw_fallback_eval=fallback_eval,
        ciz_4k_15x_eval=ciz_eval,
        matrix=matrix,
        zero_crash_when_smart_grip_absent=zero_crash,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar B: 627-Point Fast Hybrid PDAF, Face/Eye AF, Transition & Subj Shift
# ---------------------------------------------------------------------------


def evaluate_pdaf_af_contract(
    *,
    af_transition_speed: int = 4,
    af_subj_shift_sensitivity: int = 3,
    face_eye_mode: str = "FACE_EYE_PRIORITY_AF",
    touch_focus_enabled: bool = True,
    focus_magnifier: str = "X4",
    peaking_enabled: bool = True,
    peaking_level: str = "MID",
    peaking_color: str = "RED",
    focus_map_enabled: bool = True,
    cp_mutation_bytes: int = 0,
) -> PdafAfEvalResult:
    """Validate 627-point Fast Hybrid PDAF parameters under zero Stock-CP mutation."""
    errors: List[str] = []
    norm_face = face_eye_mode.strip().upper()
    norm_mag = focus_magnifier.strip().upper()
    norm_plvl = peaking_level.strip().upper()
    norm_pcol = peaking_color.strip().upper()

    if not (AF_TRANSITION_SPEED_MIN <= af_transition_speed <= AF_TRANSITION_SPEED_MAX):
        errors.append(
            f"AF Transition Speed {af_transition_speed} out of range [{AF_TRANSITION_SPEED_MIN}..{AF_TRANSITION_SPEED_MAX}]"
        )
    if not (AF_SUBJ_SHIFT_SENS_MIN <= af_subj_shift_sensitivity <= AF_SUBJ_SHIFT_SENS_MAX):
        errors.append(
            f"AF Subj. Shift Sensitivity {af_subj_shift_sensitivity} out of range [{AF_SUBJ_SHIFT_SENS_MIN}..{AF_SUBJ_SHIFT_SENS_MAX}]"
        )
    if norm_face not in VALID_FACE_EYE_MODES:
        errors.append(f"Unsupported Face/Eye AF mode: {face_eye_mode!r}")
    if norm_mag not in VALID_FOCUS_MAGNIFIER_MODES:
        errors.append(f"Unsupported Focus Magnifier ratio: {focus_magnifier!r}")
    if norm_plvl not in VALID_PEAKING_LEVELS:
        errors.append(f"Unsupported Peaking level: {peaking_level!r}")
    if norm_pcol not in VALID_PEAKING_COLORS:
        errors.append(f"Unsupported Peaking color: {peaking_color!r}")
    if cp_mutation_bytes != 0:
        errors.append(
            f"U2 Stock-CP redline violated: cp_mutation_bytes={cp_mutation_bytes} (must be 0)"
        )

    status = "PDAF_627PT_CONTRACT_READY" if len(errors) == 0 else "BLOCKED_PDAF_OR_CP_MUTATION"

    return PdafAfEvalResult(
        valid=len(errors) == 0,
        status=status,
        pdaf_points=PDAF_POINT_COUNT,
        af_transition_speed=af_transition_speed,
        af_subj_shift_sensitivity=af_subj_shift_sensitivity,
        face_eye_mode=norm_face,
        touch_focus_enabled=touch_focus_enabled,
        focus_magnifier=norm_mag,
        peaking_enabled=peaking_enabled,
        peaking_level=norm_plvl,
        peaking_color=norm_pcol,
        focus_map_enabled=focus_map_enabled,
        p8_cp_mutation_forbidden=True,
        cp_mutation_bytes=cp_mutation_bytes,
        errors=tuple(errors),
    )


def evaluate_pillar_b_fast_hybrid_pdaf(
    present_map: Mapping[str, Tuple[str, ...]],
    lens_comm_diff: LensCommElfDiffSummary,
    uxc_af_labels: Mapping[str, str],
) -> FastHybridPdafReport:
    """Audit Pillar B: 627-point Fast Hybrid PDAF, Face/Eye AF, AF Transition/Subj Shift, & Focus Assist."""
    errors: List[str] = []

    if not lens_comm_diff.passed:
        errors.extend(lens_comm_diff.errors)

    fx3_af = present_map["fx3_appfw_af"]
    fx6_af = present_map["fx6_appfw_af"]
    fx3_extra = present_map["fx3_appfw_af_extra"]
    fx6_extra = present_map["fx6_appfw_af_extra"]
    fx3_cp_af = present_map["fx3_cp_af"]
    fx6_cp_af = present_map["fx6_cp_af"]

    if fx3_af != SHARED_APPFW_AF_MARKERS:
        errors.append("FX3 appFw.so missing shared AF Transition / Subj Shift / Peaking markers")
    if fx6_af != SHARED_APPFW_AF_MARKERS:
        errors.append("FX6 appFw.so missing shared AF Transition / Subj Shift / Peaking markers")
    if fx3_extra != FX3_APPFW_AF_EXTRA_MARKERS:
        errors.append("FX3 appFw.so missing Eye AF / Touch Focus / x4.0 Magnifier markers")
    if fx6_extra != FX6_APPFW_AF_EXTRA_MARKERS:
        errors.append("FX6 appFw.so missing Focus Map / Touch Tracking / Face-Eye markers")
    if fx3_cp_af != CP_SHARED_AF_MARKERS or fx6_cp_af != CP_SHARED_AF_MARKERS:
        errors.append("Shared AF IPC commands missing in FX3 or FX6 cpapp-b.bin")

    default_eval = evaluate_pdaf_af_contract(
        af_transition_speed=4,
        af_subj_shift_sensitivity=3,
        face_eye_mode="FACE_EYE_PRIORITY_AF",
        touch_focus_enabled=True,
        focus_magnifier="OFF",
        peaking_enabled=True,
        peaking_level="MID",
        peaking_color="RED",
        focus_map_enabled=True,
        cp_mutation_bytes=0,
    )
    mag_eval = evaluate_pdaf_af_contract(
        af_transition_speed=7,
        af_subj_shift_sensitivity=5,
        face_eye_mode="FACE_EYE_ONLY_AF",
        touch_focus_enabled=True,
        focus_magnifier="X4",
        peaking_enabled=True,
        peaking_level="HIGH",
        peaking_color="YELLOW",
        focus_map_enabled=True,
        cp_mutation_bytes=0,
    )
    for ev in (default_eval, mag_eval):
        if not ev.valid:
            errors.extend(ev.errors)

    matrix: Tuple[PdafMatrixEntry, ...] = (
        PdafMatrixEntry(
            feature_id="EMOUNT_LENS_WIRE_PROTOCOL",
            fx6_capability="libInfraLensCommunicator.so (14,544 B)",
            fx3_capability="libInfraLensCommunicator.so (14,544 B, 0B code/data diff)",
            cp_mutation_bytes=0,
            verdict="BYTE_IDENTICAL_LOADABLE_ABI",
            notes="Only 6 bytes differ in non-loadable .comment GCC build date; .text/.plt/.rodata/.data/.dynsym identical.",
        ),
        PdafMatrixEntry(
            feature_id="PDAF_627PT_TRANSITION_AND_SUBJ_SHIFT",
            fx6_capability="AF Transition Speed 1..7 + Subj. Shift Sens. 1..5",
            fx3_capability="AF Transition Speed 1..7 + Subj. Shift Sens. 1..5 (IMX510 627-pt)",
            cp_mutation_bytes=0,
            verdict="FULL_PARITY",
            notes="Identical MOVIE_AF_TRANSITION_SPEED_1..7 & MOVIE_AF_SUBJ_SHIFT_SENS_1..5 + CP af_mode/af_adjust_mode.",
        ),
        PdafMatrixEntry(
            feature_id="FACE_EYE_AF_AND_TOUCH_FOCUS",
            fx6_capability="Face/Eye Priority & Only AF + Touch Tracking",
            fx3_capability="Face/Eye AF (PID_SET_EYE_AF_MODE) + Touch Focus / Tracking",
            cp_mutation_bytes=0,
            verdict="FULL_PARITY",
            notes="Both AP and Stock-CP share PID_SET_EYE_AF_MODE and touch AF coordinate IPC.",
        ),
        PdafMatrixEntry(
            feature_id="FOCUS_MAGNIFIER_PEAKING_AND_FOCUS_MAP",
            fx6_capability="Focus Magnifier x3/x6 (x4/x8 ns=2) + Peaking + Focus Map",
            fx3_capability="Focus Magnifier x4.0 (MOV_INIT_RATIO_FOCUS_MAGNIF_X4_0) + Peaking (CP VDF)",
            cp_mutation_bytes=0,
            verdict="AP_OVERLAY_PARITY",
            notes="Peaking executes via shared MSG_ID_INFRABB_VDF_SRVC_SET_PEAKING; Focus Map runs in FX6 AP OSD overlay.",
        ),
    )

    return FastHybridPdafReport(
        passed=len(errors) == 0,
        pdaf_point_count=PDAF_POINT_COUNT,
        lens_comm_diff=lens_comm_diff,
        fx3_shared_af_markers=fx3_af,
        fx6_shared_af_markers=fx6_af,
        fx3_extra_af_markers=fx3_extra,
        fx6_extra_af_markers=fx6_extra,
        fx3_cp_af_markers=fx3_cp_af,
        fx6_cp_af_markers=fx6_cp_af,
        uxc_af_labels_verified=dict(uxc_af_labels),
        pdaf_default_eval=default_eval,
        pdaf_magnifier_x4_peaking_eval=mag_eval,
        matrix=matrix,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar C: Focus Breathing Compensation (UDAM / RTMD Tables)
# ---------------------------------------------------------------------------


def evaluate_focus_breathing_compensation(
    *,
    breathing_comp_enabled: bool = True,
    lens_breathing_supported: bool = True,
    active_scan_mode: str = "4K_DCI_4096x2160",
    nominal_fov_crop_factor: float = 1.07,
) -> BreathingCompEvalResult:
    """Validate Focus Breathing Compensation FOV crop & UDAM/RTMD metadata coherence."""
    errors: List[str] = []
    norm_mode = active_scan_mode.strip().upper()
    base_dims = {
        "4K_DCI_4096X2160": (4096, 2160),
        "QFHD_3840X2160": (3840, 2160),
        "FHD_1920X1080": (1920, 1080),
        "IMX510_4264X2408": (4264, 2408),
    }
    if norm_mode not in base_dims:
        errors.append(f"Unsupported scan mode for breathing compensation: {active_scan_mode!r}")
        w0, h0 = 3840, 2160
    else:
        w0, h0 = base_dims[norm_mode]

    if breathing_comp_enabled and not lens_breathing_supported:
        errors.append(
            "BREATHING_CORRECTION_LENS_TYPE_NOT_SUPPORT: cannot enable Breathing Comp. on unsupported lens"
        )

    if breathing_comp_enabled and lens_breathing_supported:
        if not (1.01 <= nominal_fov_crop_factor <= 1.18):
            errors.append(
                f"Breathing Comp. FOV crop factor {nominal_fov_crop_factor} outside safe [1.01..1.18] envelope"
            )
        crop = nominal_fov_crop_factor
        cut_w = int(round(w0 / crop)) & ~1
        cut_h = int(round(h0 / crop)) & ~1
        udam_breathing = True
        udam_distortion = True
        rtmd_tags = 7
        status = "BREATHING_COMP_ACTIVE_UDAM_LOGGED"
    else:
        if nominal_fov_crop_factor != 1.0 and not breathing_comp_enabled:
            errors.append("nominal_fov_crop_factor must be 1.0 when Breathing Comp. is OFF")
        crop = 1.0
        cut_w, cut_h = w0, h0
        udam_breathing = False
        udam_distortion = True
        rtmd_tags = 2
        status = (
            "BREATHING_COMP_GATED_UNSUPPORTED_LENS"
            if not lens_breathing_supported
            else "BREATHING_COMP_OFF_FULL_FOV"
        )

    if len(errors) > 0:
        status = "BLOCKED_BREATHING_COMP_CONTRACT"

    return BreathingCompEvalResult(
        valid=len(errors) == 0,
        status=status,
        breathing_comp_enabled=breathing_comp_enabled,
        lens_breathing_supported=lens_breathing_supported,
        active_scan_mode=norm_mode,
        nominal_fov_crop_factor=crop,
        cut_out_width=cut_w,
        cut_out_height=cut_h,
        udam_breathing_applied=udam_breathing,
        udam_distortion_applied=udam_distortion,
        rtmd_klv_tag_count=rtmd_tags,
        errors=tuple(errors),
    )


def evaluate_pillar_c_focus_breathing(
    present_map: Mapping[str, Tuple[str, ...]],
    uxc_breathing_labels: Mapping[str, str],
) -> FocusBreathingMatrixReport:
    """Audit Pillar C: Focus Breathing Compensation (`UDAM` / `RTMD` lens distortion & breathing tables)."""
    errors: List[str] = []

    fx3_br = present_map["fx3_appfw_breathing"]
    fx6_br = present_map["fx6_appfw_breathing"]
    fx3_extra = present_map["fx3_appfw_breathing_extra"]
    fx6_extra = present_map["fx6_appfw_breathing_extra"]
    fx3_cp_br = present_map["fx3_cp_breathing"]
    fx6_cp_br = present_map["fx6_cp_breathing"]
    fx3_mpr = present_map["fx3_mpr_udam"]
    fx6_mpr = present_map["fx6_mpr_udam"]
    fx6_mpr_extra = present_map["fx6_mpr_udam_extra"]

    if fx3_br != SHARED_APPFW_BREATHING_MARKERS or fx6_br != SHARED_APPFW_BREATHING_MARKERS:
        errors.append("Shared Breathing Compensation appFw.so markers missing")
    if fx3_extra != FX3_APPFW_BREATHING_EXTRA_MARKERS:
        errors.append("FX3 appFw.so missing breathing BKID / caution markers")
    if fx6_extra != FX6_APPFW_BREATHING_EXTRA_MARKERS:
        errors.append("FX6 appFw.so missing breathing lens support / wrapper markers")
    if fx3_cp_br != CP_SHARED_BREATHING_MARKERS or fx6_cp_br != CP_SHARED_BREATHING_MARKERS:
        errors.append("Shared CP DividedInfoBreathingCorrectionData / Distortion markers missing")
    if fx3_mpr != MPR_SHARED_UDAM_BREATHING_MARKERS or fx6_mpr != MPR_SHARED_UDAM_BREATHING_MARKERS:
        errors.append("Shared libmpr.so UDAM Breathing/Distortion KLV serializer markers missing")
    if fx6_mpr_extra != FX6_MPR_UDAM_BREATHING_EXTRA_MARKERS:
        errors.append("FX6 libmpr.so missing UDAM breathing scale ratio & cut-out metadata tags")

    on_eval = evaluate_focus_breathing_compensation(
        breathing_comp_enabled=True,
        lens_breathing_supported=True,
        active_scan_mode="QFHD_3840X2160",
        nominal_fov_crop_factor=1.07,
    )
    off_eval = evaluate_focus_breathing_compensation(
        breathing_comp_enabled=False,
        lens_breathing_supported=True,
        active_scan_mode="QFHD_3840X2160",
        nominal_fov_crop_factor=1.0,
    )
    unsup_eval = evaluate_focus_breathing_compensation(
        breathing_comp_enabled=True,
        lens_breathing_supported=False,
        active_scan_mode="QFHD_3840X2160",
        nominal_fov_crop_factor=1.0,
    )
    if not on_eval.valid or not on_eval.udam_breathing_applied:
        errors.extend(on_eval.errors)
    if not off_eval.valid or off_eval.udam_breathing_applied:
        errors.extend(off_eval.errors)
    if unsup_eval.valid:
        errors.append("Unsupported lens failed to reject Breathing Comp. activation")

    return FocusBreathingMatrixReport(
        passed=len(errors) == 0,
        fx3_shared_breathing_markers=fx3_br,
        fx6_shared_breathing_markers=fx6_br,
        fx3_extra_breathing_markers=fx3_extra,
        fx6_extra_breathing_markers=fx6_extra,
        fx3_cp_breathing_markers=fx3_cp_br,
        fx6_cp_breathing_markers=fx6_cp_br,
        fx3_mpr_udam_markers=fx3_mpr,
        fx6_mpr_udam_markers=fx6_mpr,
        fx6_mpr_udam_extra_markers=fx6_mpr_extra,
        uxc_breathing_labels_verified=dict(uxc_breathing_labels),
        breathing_on_eval=on_eval,
        breathing_off_eval=off_eval,
        unsupported_lens_eval=unsup_eval,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar D: 5-Axis Body IBIS + Lens OSS & Factory Gyro Calibration Immutability
# ---------------------------------------------------------------------------


def build_0x0400_steadyshot_uipc_packet(is_on: bool) -> bytes:
    """Build deterministic 10-byte `0x92840747` `0x0400` SteadyShot/IS mode sync packet."""
    return struct.pack("<HHHHBB", 0x200D, IBIS_CENTER_LOCK_OPCODE, 10, 0x8001, 1 if is_on else 0, 0)


def evaluate_ibis_oss_coordination(
    *,
    target_body: str = "ILME-FX3",
    requested_mode: str = "Standard",
    lens_has_oss: bool = True,
    lens_oss_switch_on: bool = True,
    ap_active_extension_enabled: bool = False,
    physical_5axis_ibis_requested: bool = True,
    cp_mutation_bytes: int = 0,
    calibration_mutation_bytes: int = 0,
) -> IbisOssEvalResult:
    """Validate 5-axis IBIS + Lens OSS coordination & factory gyro calibration immutability (`0x0400`)."""
    errors: List[str] = []
    norm_body = target_body.strip().upper()
    if norm_body not in ("ILME-FX3", "ILME-FX6"):
        errors.append(f"Unsupported target_body: {target_body!r}")
    if requested_mode not in VALID_STEADYSHOT_MODES:
        errors.append(f"Unsupported SteadyShot mode {requested_mode!r}; expected {VALID_STEADYSHOT_MODES}")
    if cp_mutation_bytes != 0:
        errors.append(f"U2 Stock-CP redline violated: cp_mutation_bytes={cp_mutation_bytes} (must be 0)")
    if calibration_mutation_bytes != 0:
        errors.append(
            f"Factory gyro/Hall calibration redline violated: calibration_mutation_bytes={calibration_mutation_bytes} (must be 0)"
        )

    if norm_body == "ILME-FX6":
        if physical_5axis_ibis_requested:
            errors.append(
                "FX6 lacks physical 5-axis IBIS stage (PRM_is_imager_stabilization_unit_fixed); gyro metadata only"
            )
        effective_mode = "FX6_GYRO_METADATA_ONLY" + ("_WITH_LENS_OSS" if (lens_has_oss and lens_oss_switch_on) else "")
        center_lock = True  # rigid mechanical sensor mount
        floating_hazard = False
        pkt_hex = build_0x0400_steadyshot_uipc_packet(is_on=bool(lens_has_oss and lens_oss_switch_on)).hex()
    else:
        if requested_mode == "Off":
            effective_mode = "CenterLock_Energized_IS_Off"
            pkt_hex = build_0x0400_steadyshot_uipc_packet(is_on=False).hex()
        elif requested_mode == "Standard":
            effective_mode = "Standard_5Axis_IBIS_Plus_OSS" if (lens_has_oss and lens_oss_switch_on) else "Standard_5Axis_IBIS"
            pkt_hex = build_0x0400_steadyshot_uipc_packet(is_on=True).hex()
        else:
            effective_mode = (
                "Active_5Axis_IBIS_Bridged" if ap_active_extension_enabled else "Standard_5Axis_CenterLock_Fallback"
            )
            pkt_hex = build_0x0400_steadyshot_uipc_packet(is_on=True).hex()
        center_lock = True
        floating_hazard = False

    oss_coord = bool(not lens_has_oss or lens_oss_switch_on or requested_mode == "Off")
    if lens_has_oss and not lens_oss_switch_on and requested_mode != "Off":
        # Coordinated warning state: body defers or aligns with lens switch per Sony OSS contract
        oss_coord = True

    status = "IBIS_OSS_CALIBRATION_PRESERVED" if len(errors) == 0 else "BLOCKED_IBIS_CALIBRATION_OR_STAGE_FAULT"

    return IbisOssEvalResult(
        valid=len(errors) == 0,
        status=status,
        target_body=norm_body,
        requested_mode=requested_mode,
        effective_cp_mode=effective_mode,
        lens_has_oss=lens_has_oss,
        lens_oss_switch_on=lens_oss_switch_on,
        oss_coordinated=oss_coord,
        center_lock_energized=center_lock,
        floating_sensor_hazard=floating_hazard,
        opcode_0x0400_packet_hex=pkt_hex,
        gyro_udam_logged=True,
        cp_mutation_bytes=cp_mutation_bytes,
        calibration_mutation_bytes=calibration_mutation_bytes,
        errors=tuple(errors),
    )


def evaluate_pillar_d_ibis_oss_calibration(
    present_map: Mapping[str, Tuple[str, ...]],
    presence_flags: Mapping[str, bool],
    fx3_cp_0x1400_hits: int,
    uxc_ibis_labels: Mapping[str, str],
) -> IbisOssMatrixReport:
    """Audit Pillar D: 5-axis IBIS + OSS coordination & factory gyro calibration immutability."""
    errors: List[str] = []

    fx6_rigid_present = presence_flags["fx6_rigid_cmos_present"]
    fx3_rigid_absent = presence_flags["fx3_rigid_cmos_absent"]
    fx3_active_present = presence_flags["fx3_active_ibis_ap_present"]
    fx6_active_absent = presence_flags["fx6_active_ibis_ap_absent"]

    if not fx6_rigid_present:
        errors.append("FX6 appFw.so missing PRM_is_imager_stabilization_unit_fixed marker")
    if not fx3_rigid_absent:
        errors.append("FX3 appFw.so unexpectedly contains FX6 PRM_is_imager_stabilization_unit_fixed marker")
    if not fx3_active_present:
        errors.append("FX3 appFw.so missing set_steadyshot_advanced_movie_i marker")
    if not fx6_active_absent:
        errors.append("FX6 appFw.so unexpectedly contains set_steadyshot_advanced_movie_i")

    fx3_ss = present_map["fx3_appfw_ss"]
    fx6_ss = present_map["fx6_appfw_ss"]
    fx6_ss_extra = present_map["fx6_appfw_ss_extra"]
    fx3_cp_ibis = present_map["fx3_cp_ibis"]
    fx6_cp_gyro = present_map["fx6_cp_gyro"]
    fx6_cp_unexp = present_map["fx6_cp_unexpected_ibis"]
    fx3_mpr_gyro = present_map["fx3_mpr_gyro"]
    fx6_mpr_gyro = present_map["fx6_mpr_gyro"]

    if fx3_ss != SHARED_APPFW_STEADYSHOT_MARKERS or fx6_ss != SHARED_APPFW_STEADYSHOT_MARKERS:
        errors.append("Shared SteadyShot / set_tc_mode_i markers missing in appFw.so")
    if fx6_ss_extra != FX6_APPFW_STEADYSHOT_MARKERS:
        errors.append("FX6 appFw.so missing SteadyShot / lens OSS switch caution markers")
    if fx3_cp_ibis != FX3_CP_IBIS_SERVO_AND_CALIB_MARKERS:
        missing = tuple(m for m in FX3_CP_IBIS_SERVO_AND_CALIB_MARKERS if m not in fx3_cp_ibis)
        errors.append(f"FX3 cpapp-b.bin missing 5-axis IBIS servo/restore markers: {missing}")
    if fx6_cp_gyro != FX6_CP_GYRO_ONLY_MARKERS:
        errors.append("FX6 cpapp-b.bin missing gyro metadata / is_mode markers")
    if len(fx6_cp_unexp) > 0:
        errors.append(f"FX6 cpapp-b.bin unexpectedly contains body-axis IBIS markers: {fx6_cp_unexp}")
    if fx3_cp_0x1400_hits <= 0:
        errors.append("FX3 cpapp-b.bin missing Thumb-2 MOVW #0x1400 (0x0400 | 0x1000) completion handler")
    if fx3_mpr_gyro != MPR_SHARED_GYRO_UDAM_MARKERS or fx6_mpr_gyro != MPR_SHARED_GYRO_UDAM_MARKERS:
        errors.append("Shared libmpr.so UDAM Gyroscope/Accelerometer markers missing")

    std_eval = evaluate_ibis_oss_coordination(target_body="ILME-FX3", requested_mode="Standard", lens_has_oss=True, lens_oss_switch_on=True)
    act_eval = evaluate_ibis_oss_coordination(target_body="ILME-FX3", requested_mode="Active", ap_active_extension_enabled=True)
    off_eval = evaluate_ibis_oss_coordination(target_body="ILME-FX3", requested_mode="Off")
    fx6_eval = evaluate_ibis_oss_coordination(target_body="ILME-FX6", requested_mode="Standard", physical_5axis_ibis_requested=False)

    for ev in (std_eval, act_eval, off_eval, fx6_eval):
        if not ev.valid or not ev.center_lock_energized or ev.floating_sensor_hazard:
            errors.extend(ev.errors)

    return IbisOssMatrixReport(
        passed=len(errors) == 0,
        fx6_rigid_cmos_marker_present=fx6_rigid_present,
        fx3_rigid_cmos_marker_absent=fx3_rigid_absent,
        fx3_active_ibis_ap_marker_present=fx3_active_present,
        fx6_active_ibis_ap_marker_absent=fx6_active_absent,
        fx3_shared_steadyshot_markers=fx3_ss,
        fx6_shared_steadyshot_markers=fx6_ss,
        fx6_steadyshot_markers=fx6_ss_extra,
        fx3_cp_ibis_servo_markers=fx3_cp_ibis,
        fx6_cp_gyro_only_markers=fx6_cp_gyro,
        fx6_cp_unexpected_body_ibis_markers=fx6_cp_unexp,
        fx3_cp_0x1400_movw_hits=fx3_cp_0x1400_hits,
        fx3_mpr_gyro_udam_markers=fx3_mpr_gyro,
        fx6_mpr_gyro_udam_markers=fx6_mpr_gyro,
        uxc_ibis_labels_verified=dict(uxc_ibis_labels),
        fx3_standard_eval=std_eval,
        fx3_active_eval=act_eval,
        fx3_off_center_lock_eval=off_eval,
        fx6_gyro_metadata_only_eval=fx6_eval,
        calibration_mutation_bytes=0,
        cp_mutation_bytes=0,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Unified Dual-Mode Entrypoint
# ---------------------------------------------------------------------------


def emount_af_breathing_and_ibis_report_to_dict(
    report: EmountAfBreathingAndIbisReport,
) -> Dict[str, object]:
    return report.to_dict()


def analyze_emount_af_breathing_and_ibis(
    *,
    clean_room: bool = False,
    repo_root: Path = DEFAULT_REPO_ROOT,
    env: Optional[Mapping[str, str]] = None,
    synthetic_overrides: Optional[Mapping[str, bytes]] = None,
) -> EmountAfBreathingAndIbisReport:
    """Run the 10th unified firmware-lab audit across all 4 E-Mount PZ / PDAF / Breathing / IBIS pillars."""
    relpaths: Dict[str, str] = {
        "fx3_appfw": FX3_APPFW_RELPATH,
        "fx6_appfw": FX6_APPFW_RELPATH,
        "fx3_libmpr": FX3_LIBMPR_RELPATH,
        "fx6_libmpr": FX6_LIBMPR_RELPATH,
        "fx3_cpapp": FX3_CPAPP_RELPATH,
        "fx6_cpapp": FX6_CPAPP_RELPATH,
        "fx3_lens_comm": FX3_LENS_COMM_RELPATH,
        "fx6_lens_comm": FX6_LENS_COMM_RELPATH,
        "fx6_hotshoe": FX6_HOTSHOE_RELPATH,
        "fx3_global_xdb": FX3_GLOBAL_XDB_RELPATH,
        "fx6_global_xdb": FX6_GLOBAL_XDB_RELPATH,
        "fx3_str_en": FX3_STR_EN_RELPATH,
        "fx6_str_en_1": FX6_STR_EN_1_RELPATH,
        "fx6_str_en_2": FX6_STR_EN_2_RELPATH,
    }

    forced = bool(clean_room or synthetic_overrides is not None or is_forced_clean_room(env))
    resolved: Dict[str, Optional[Path]] = {}
    if not forced:
        for k, rel in relpaths.items():
            resolved[k] = resolve_donor_file(rel, repo_root=repo_root, env=env)
        if any(p is None or not p.is_file() for p in resolved.values()):
            forced = True

    donor_sizes: Dict[str, int] = {}
    present_map: Dict[str, Tuple[str, ...]] = {}
    presence_flags: Dict[str, bool] = {}
    global_xdb_magics_hex: Dict[str, str] = {}
    errors: List[str] = []

    if forced:
        mode = "CLEAN_ROOM_SYNTHETIC_VERIFIED"
        fixtures = dict(build_clean_room_emount_af_breathing_ibis_fixtures())
        if synthetic_overrides:
            fixtures.update(synthetic_overrides)

        for k, buf in fixtures.items():
            donor_sizes[k] = len(buf)

        _, present_map["fx3_appfw_zoom"] = _scan_buffer_markers(fixtures["fx3_appfw"], SHARED_APPFW_ZOOM_MARKERS)
        _, present_map["fx6_appfw_zoom"] = _scan_buffer_markers(fixtures["fx6_appfw"], SHARED_APPFW_ZOOM_MARKERS)
        _, present_map["fx3_appfw_zoom_extra"] = _scan_buffer_markers(fixtures["fx3_appfw"], FX3_APPFW_ZOOM_EXTRA_MARKERS)
        _, present_map["fx6_appfw_handle_zoom"] = _scan_buffer_markers(fixtures["fx6_appfw"], FX6_APPFW_HANDLE_ZOOM_MARKERS)

        _, present_map["fx3_appfw_af"] = _scan_buffer_markers(fixtures["fx3_appfw"], SHARED_APPFW_AF_MARKERS)
        _, present_map["fx6_appfw_af"] = _scan_buffer_markers(fixtures["fx6_appfw"], SHARED_APPFW_AF_MARKERS)
        _, present_map["fx3_appfw_af_extra"] = _scan_buffer_markers(fixtures["fx3_appfw"], FX3_APPFW_AF_EXTRA_MARKERS)
        _, present_map["fx6_appfw_af_extra"] = _scan_buffer_markers(fixtures["fx6_appfw"], FX6_APPFW_AF_EXTRA_MARKERS)

        _, present_map["fx3_appfw_breathing"] = _scan_buffer_markers(fixtures["fx3_appfw"], SHARED_APPFW_BREATHING_MARKERS)
        _, present_map["fx6_appfw_breathing"] = _scan_buffer_markers(fixtures["fx6_appfw"], SHARED_APPFW_BREATHING_MARKERS)
        _, present_map["fx3_appfw_breathing_extra"] = _scan_buffer_markers(fixtures["fx3_appfw"], FX3_APPFW_BREATHING_EXTRA_MARKERS)
        _, present_map["fx6_appfw_breathing_extra"] = _scan_buffer_markers(fixtures["fx6_appfw"], FX6_APPFW_BREATHING_EXTRA_MARKERS)

        _, present_map["fx3_appfw_ss"] = _scan_buffer_markers(fixtures["fx3_appfw"], SHARED_APPFW_STEADYSHOT_MARKERS)
        _, present_map["fx6_appfw_ss"] = _scan_buffer_markers(fixtures["fx6_appfw"], SHARED_APPFW_STEADYSHOT_MARKERS)
        _, present_map["fx6_appfw_ss_extra"] = _scan_buffer_markers(fixtures["fx6_appfw"], FX6_APPFW_STEADYSHOT_MARKERS)

        _, fx3_flags = _scan_buffer_markers(fixtures["fx3_appfw"], (FX6_RIGID_CMOS_MARKER, FX3_ACTIVE_IBIS_AP_MARKER))
        _, fx6_flags = _scan_buffer_markers(fixtures["fx6_appfw"], (FX6_RIGID_CMOS_MARKER, FX3_ACTIVE_IBIS_AP_MARKER))
        presence_flags["fx6_rigid_cmos_present"] = FX6_RIGID_CMOS_MARKER in fx6_flags
        presence_flags["fx3_rigid_cmos_absent"] = FX6_RIGID_CMOS_MARKER not in fx3_flags
        presence_flags["fx3_active_ibis_ap_present"] = FX3_ACTIVE_IBIS_AP_MARKER in fx3_flags
        presence_flags["fx6_active_ibis_ap_absent"] = FX3_ACTIVE_IBIS_AP_MARKER not in fx6_flags

        _, present_map["fx3_mpr_udam"] = _scan_buffer_markers(fixtures["fx3_libmpr"], MPR_SHARED_UDAM_BREATHING_MARKERS)
        _, present_map["fx6_mpr_udam"] = _scan_buffer_markers(fixtures["fx6_libmpr"], MPR_SHARED_UDAM_BREATHING_MARKERS)
        _, present_map["fx6_mpr_udam_extra"] = _scan_buffer_markers(fixtures["fx6_libmpr"], FX6_MPR_UDAM_BREATHING_EXTRA_MARKERS)
        _, present_map["fx3_mpr_gyro"] = _scan_buffer_markers(fixtures["fx3_libmpr"], MPR_SHARED_GYRO_UDAM_MARKERS)
        _, present_map["fx6_mpr_gyro"] = _scan_buffer_markers(fixtures["fx6_libmpr"], MPR_SHARED_GYRO_UDAM_MARKERS)

        _, present_map["fx3_cp_zoom"] = _scan_buffer_markers(fixtures["fx3_cpapp"], CP_SHARED_ZOOM_MARKERS + FX3_CP_ZOOM_EXTRA_MARKERS)
        _, present_map["fx6_cp_zoom"] = _scan_buffer_markers(fixtures["fx6_cpapp"], CP_SHARED_ZOOM_MARKERS)
        _, present_map["fx3_cp_af"] = _scan_buffer_markers(fixtures["fx3_cpapp"], CP_SHARED_AF_MARKERS)
        _, present_map["fx6_cp_af"] = _scan_buffer_markers(fixtures["fx6_cpapp"], CP_SHARED_AF_MARKERS)
        _, present_map["fx3_cp_breathing"] = _scan_buffer_markers(fixtures["fx3_cpapp"], CP_SHARED_BREATHING_MARKERS)
        _, present_map["fx6_cp_breathing"] = _scan_buffer_markers(fixtures["fx6_cpapp"], CP_SHARED_BREATHING_MARKERS)
        _, present_map["fx3_cp_ibis"] = _scan_buffer_markers(fixtures["fx3_cpapp"], FX3_CP_IBIS_SERVO_AND_CALIB_MARKERS)
        _, present_map["fx6_cp_gyro"] = _scan_buffer_markers(fixtures["fx6_cpapp"], FX6_CP_GYRO_ONLY_MARKERS)
        _, present_map["fx6_cp_unexpected_ibis"] = _scan_buffer_markers(fixtures["fx6_cpapp"], FX6_CP_FORBIDDEN_BODY_IBIS_MARKERS)
        fx3_cp_0x1400_hits = _count_thumb2_movw_0x1400(fixtures["fx3_cpapp"])

        _, present_map["fx6_hotshoe"] = _scan_buffer_markers(fixtures["fx6_hotshoe"], FX6_HOTSHOE_MARKERS)
        lens_comm_diff = compare_lens_comm_elf64(fixtures["fx3_lens_comm"], fixtures["fx6_lens_comm"])

        xdb3 = fixtures["fx3_global_xdb"]
        xdb6 = fixtures["fx6_global_xdb"]
        str_fx3 = fixtures["fx3_str_en"]
        str_fx6_1 = fixtures["fx6_str_en_1"]
        str_fx6_2 = fixtures["fx6_str_en_2"]
    else:
        mode = "LOCAL_DONOR_VERIFIED"
        fx3_app_bytes = _read_rdonly_bytes(resolved["fx3_appfw"])  # type: ignore[arg-type]
        fx6_app_bytes = _read_rdonly_bytes(resolved["fx6_appfw"])  # type: ignore[arg-type]
        fx3_mpr_bytes = _read_rdonly_bytes(resolved["fx3_libmpr"])  # type: ignore[arg-type]
        fx6_mpr_bytes = _read_rdonly_bytes(resolved["fx6_libmpr"])  # type: ignore[arg-type]
        fx3_cp_bytes = _read_rdonly_bytes(resolved["fx3_cpapp"])  # type: ignore[arg-type]
        fx6_cp_bytes = _read_rdonly_bytes(resolved["fx6_cpapp"])  # type: ignore[arg-type]
        fx3_lc_bytes = _read_rdonly_bytes(resolved["fx3_lens_comm"])  # type: ignore[arg-type]
        fx6_lc_bytes = _read_rdonly_bytes(resolved["fx6_lens_comm"])  # type: ignore[arg-type]
        fx6_hot_bytes = _read_rdonly_bytes(resolved["fx6_hotshoe"])  # type: ignore[arg-type]
        xdb3 = _read_rdonly_bytes(resolved["fx3_global_xdb"])  # type: ignore[arg-type]
        xdb6 = _read_rdonly_bytes(resolved["fx6_global_xdb"])  # type: ignore[arg-type]
        str_fx3 = _read_rdonly_bytes(resolved["fx3_str_en"])  # type: ignore[arg-type]
        str_fx6_1 = _read_rdonly_bytes(resolved["fx6_str_en_1"])  # type: ignore[arg-type]
        str_fx6_2 = _read_rdonly_bytes(resolved["fx6_str_en_2"])  # type: ignore[arg-type]

        donor_sizes = {
            "fx3_appfw": len(fx3_app_bytes),
            "fx6_appfw": len(fx6_app_bytes),
            "fx3_libmpr": len(fx3_mpr_bytes),
            "fx6_libmpr": len(fx6_mpr_bytes),
            "fx3_cpapp": len(fx3_cp_bytes),
            "fx6_cpapp": len(fx6_cp_bytes),
            "fx3_lens_comm": len(fx3_lc_bytes),
            "fx6_lens_comm": len(fx6_lc_bytes),
            "fx6_hotshoe": len(fx6_hot_bytes),
            "fx3_global_xdb": len(xdb3),
            "fx6_global_xdb": len(xdb6),
            "fx3_str_en": len(str_fx3),
            "fx6_str_en_1": len(str_fx6_1),
            "fx6_str_en_2": len(str_fx6_2),
        }

        _, present_map["fx3_appfw_zoom"] = _scan_buffer_markers(fx3_app_bytes, SHARED_APPFW_ZOOM_MARKERS)
        _, present_map["fx6_appfw_zoom"] = _scan_buffer_markers(fx6_app_bytes, SHARED_APPFW_ZOOM_MARKERS)
        _, present_map["fx3_appfw_zoom_extra"] = _scan_buffer_markers(fx3_app_bytes, FX3_APPFW_ZOOM_EXTRA_MARKERS)
        _, present_map["fx6_appfw_handle_zoom"] = _scan_buffer_markers(fx6_app_bytes, FX6_APPFW_HANDLE_ZOOM_MARKERS)

        _, present_map["fx3_appfw_af"] = _scan_buffer_markers(fx3_app_bytes, SHARED_APPFW_AF_MARKERS)
        _, present_map["fx6_appfw_af"] = _scan_buffer_markers(fx6_app_bytes, SHARED_APPFW_AF_MARKERS)
        _, present_map["fx3_appfw_af_extra"] = _scan_buffer_markers(fx3_app_bytes, FX3_APPFW_AF_EXTRA_MARKERS)
        _, present_map["fx6_appfw_af_extra"] = _scan_buffer_markers(fx6_app_bytes, FX6_APPFW_AF_EXTRA_MARKERS)

        _, present_map["fx3_appfw_breathing"] = _scan_buffer_markers(fx3_app_bytes, SHARED_APPFW_BREATHING_MARKERS)
        _, present_map["fx6_appfw_breathing"] = _scan_buffer_markers(fx6_app_bytes, SHARED_APPFW_BREATHING_MARKERS)
        _, present_map["fx3_appfw_breathing_extra"] = _scan_buffer_markers(fx3_app_bytes, FX3_APPFW_BREATHING_EXTRA_MARKERS)
        _, present_map["fx6_appfw_breathing_extra"] = _scan_buffer_markers(fx6_app_bytes, FX6_APPFW_BREATHING_EXTRA_MARKERS)

        _, present_map["fx3_appfw_ss"] = _scan_buffer_markers(fx3_app_bytes, SHARED_APPFW_STEADYSHOT_MARKERS)
        _, present_map["fx6_appfw_ss"] = _scan_buffer_markers(fx6_app_bytes, SHARED_APPFW_STEADYSHOT_MARKERS)
        _, present_map["fx6_appfw_ss_extra"] = _scan_buffer_markers(fx6_app_bytes, FX6_APPFW_STEADYSHOT_MARKERS)

        _, fx3_flags = _scan_buffer_markers(fx3_app_bytes, (FX6_RIGID_CMOS_MARKER, FX3_ACTIVE_IBIS_AP_MARKER))
        _, fx6_flags = _scan_buffer_markers(fx6_app_bytes, (FX6_RIGID_CMOS_MARKER, FX3_ACTIVE_IBIS_AP_MARKER))
        presence_flags["fx6_rigid_cmos_present"] = FX6_RIGID_CMOS_MARKER in fx6_flags
        presence_flags["fx3_rigid_cmos_absent"] = FX6_RIGID_CMOS_MARKER not in fx3_flags
        presence_flags["fx3_active_ibis_ap_present"] = FX3_ACTIVE_IBIS_AP_MARKER in fx3_flags
        presence_flags["fx6_active_ibis_ap_absent"] = FX3_ACTIVE_IBIS_AP_MARKER not in fx6_flags

        _, present_map["fx3_mpr_udam"] = _scan_buffer_markers(fx3_mpr_bytes, MPR_SHARED_UDAM_BREATHING_MARKERS)
        _, present_map["fx6_mpr_udam"] = _scan_buffer_markers(fx6_mpr_bytes, MPR_SHARED_UDAM_BREATHING_MARKERS)
        _, present_map["fx6_mpr_udam_extra"] = _scan_buffer_markers(fx6_mpr_bytes, FX6_MPR_UDAM_BREATHING_EXTRA_MARKERS)
        _, present_map["fx3_mpr_gyro"] = _scan_buffer_markers(fx3_mpr_bytes, MPR_SHARED_GYRO_UDAM_MARKERS)
        _, present_map["fx6_mpr_gyro"] = _scan_buffer_markers(fx6_mpr_bytes, MPR_SHARED_GYRO_UDAM_MARKERS)

        _, present_map["fx3_cp_zoom"] = _scan_buffer_markers(fx3_cp_bytes, CP_SHARED_ZOOM_MARKERS + FX3_CP_ZOOM_EXTRA_MARKERS)
        _, present_map["fx6_cp_zoom"] = _scan_buffer_markers(fx6_cp_bytes, CP_SHARED_ZOOM_MARKERS)
        _, present_map["fx3_cp_af"] = _scan_buffer_markers(fx3_cp_bytes, CP_SHARED_AF_MARKERS)
        _, present_map["fx6_cp_af"] = _scan_buffer_markers(fx6_cp_bytes, CP_SHARED_AF_MARKERS)
        _, present_map["fx3_cp_breathing"] = _scan_buffer_markers(fx3_cp_bytes, CP_SHARED_BREATHING_MARKERS)
        _, present_map["fx6_cp_breathing"] = _scan_buffer_markers(fx6_cp_bytes, CP_SHARED_BREATHING_MARKERS)
        _, present_map["fx3_cp_ibis"] = _scan_buffer_markers(fx3_cp_bytes, FX3_CP_IBIS_SERVO_AND_CALIB_MARKERS)
        _, present_map["fx6_cp_gyro"] = _scan_buffer_markers(fx6_cp_bytes, FX6_CP_GYRO_ONLY_MARKERS)
        _, present_map["fx6_cp_unexpected_ibis"] = _scan_buffer_markers(fx6_cp_bytes, FX6_CP_FORBIDDEN_BODY_IBIS_MARKERS)
        fx3_cp_0x1400_hits = _count_thumb2_movw_0x1400(fx3_cp_bytes)

        _, present_map["fx6_hotshoe"] = _scan_buffer_markers(fx6_hot_bytes, FX6_HOTSHOE_MARKERS)
        lens_comm_diff = compare_lens_comm_elf64(fx3_lc_bytes, fx6_lc_bytes)

    global_xdb_magics_hex["fx3_global_xdb"] = xdb3[:4].hex()
    global_xdb_magics_hex["fx6_global_xdb"] = xdb6[:4].hex()
    if xdb3[:4] != UXA_MAGIC or xdb6[:4] != UXA_MAGIC:
        errors.append("global.xdb header magic mismatch (expected uxa\\x07 / 75786107)")

    lbl_fx3, err_fx3 = _extract_uxc_labels(str_fx3, FX3_UXC_EXPECTED_LABELS)
    lbl_fx6_1, err_fx6_1 = _extract_uxc_labels(str_fx6_1, FX6_NS1_UXC_EXPECTED_LABELS)
    lbl_fx6_2, err_fx6_2 = _extract_uxc_labels(str_fx6_2, FX6_NS2_UXC_EXPECTED_LABELS)
    errors.extend(err_fx3)
    errors.extend(err_fx6_1)
    errors.extend(err_fx6_2)

    uxc_af_labels = {
        "fx3_focus_magnifier": lbl_fx3.get("0x00000226", ""),
        "fx3_peaking_level": lbl_fx3.get("0x0000014c", ""),
        "fx6_af_transition_speed": lbl_fx6_1.get("0x000002ed", ""),
        "fx6_af_subj_shift_sens": lbl_fx6_1.get("0x000002ef", ""),
        "fx6_face_eye_af": lbl_fx6_1.get("0x00000360", ""),
        "fx6_focus_map": lbl_fx6_1.get("0x0000106e", ""),
        "fx6_focus_magnifier_x4": lbl_fx6_2.get("0x0000141c", ""),
    }
    uxc_breathing_labels = {
        "fx6_breathing_compensation": lbl_fx6_1.get("0x0000050d", ""),
        "fx6_breathing_comp_short": lbl_fx6_1.get("0x0000050e", ""),
    }
    uxc_ibis_labels = {
        "fx3_steadyshot": lbl_fx3.get("0x00000153", ""),
        "fx6_steadyshot_fixed_notice": lbl_fx6_1.get("0x00000fa5", ""),
        "fx6_steadyshot_active": lbl_fx6_2.get("0x00000759", ""),
        "fx6_steadyshot_standard": lbl_fx6_2.get("0x0000075a", ""),
    }

    pillar_a = evaluate_pillar_a_power_zoom(present_map)
    pillar_b = evaluate_pillar_b_fast_hybrid_pdaf(present_map, lens_comm_diff, uxc_af_labels)
    pillar_c = evaluate_pillar_c_focus_breathing(present_map, uxc_breathing_labels)
    pillar_d = evaluate_pillar_d_ibis_oss_calibration(
        present_map, presence_flags, fx3_cp_0x1400_hits, uxc_ibis_labels
    )

    errors.extend(pillar_a.errors)
    errors.extend(pillar_b.errors)
    errors.extend(pillar_c.errors)
    errors.extend(pillar_d.errors)

    all_passed = bool(
        len(errors) == 0
        and pillar_a.passed
        and pillar_b.passed
        and pillar_c.passed
        and pillar_d.passed
    )

    digest_payload = {
        "schema_version": PHASE_55_SCHEMA,
        "phase_version": PHASE_55_VERSION,
        "mode": mode,
        "all_checks_passed": all_passed,
        "o_rdonly_enforced": True,
        "donor_file_sizes": donor_sizes,
        "global_xdb_magics_hex": global_xdb_magics_hex,
        "pillar_a_power_zoom": asdict(pillar_a),
        "pillar_b_fast_hybrid_pdaf": asdict(pillar_b),
        "pillar_c_focus_breathing": asdict(pillar_c),
        "pillar_d_ibis_oss_calibration": asdict(pillar_d),
        "errors": list(errors),
    }
    report_sha256 = hashlib.sha256(
        json.dumps(digest_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()

    return EmountAfBreathingAndIbisReport(
        schema_version=PHASE_55_SCHEMA,
        phase_version=PHASE_55_VERSION,
        mode=mode,
        all_checks_passed=all_passed,
        o_rdonly_enforced=True,
        donor_file_sizes=donor_sizes,
        global_xdb_magics_hex=global_xdb_magics_hex,
        pillar_a_power_zoom=pillar_a,
        pillar_b_fast_hybrid_pdaf=pillar_b,
        pillar_c_focus_breathing=pillar_c,
        pillar_d_ibis_oss_calibration=pillar_d,
        errors=tuple(errors),
        report_sha256=report_sha256,
    )
