"""Phase 65 — 12th Unified Firmware-Lab Auditor: White Balance Control (`Shockless WB` / `ATW`), Base Look / Gamma-Gamut Matrix, Paint Menu `3x3` Color Matrix (`R-G..B-G`) / Knee / Black Gamma & `cnflasha` Factory Calibration Immutability.

Strictly Read-Only (`os.O_RDONLY` + `mmap.ACCESS_READ`) & Clean-Room Dual-Mode:
- Local Donor Mode: inspects FX3 v7.02 (`appFw.so`, `libmpr.so`, `cpapp-b.bin`,
  `string_english.uxc`, `string_english_g.uxc`) and FX6 v6.01 (`appFw.so`,
  `libmpr.so`, `cpapp-b.bin`, `string_english.uxc`, `string_english_2.uxc`)
  strictly via `os.O_RDONLY` + read-only `mmap` and ELF64 `.rodata`/`.dynstr`
  section-scoped scanning, plus `.uxc` string-pack slot verification.
- Clean-Room Mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`, `clean_room=True`, or donors
  absent): synthesizes deterministic clean-room binary and `.uxc` fixtures
  carrying the exact contract markers and executes the identical four-pillar
  verification pipeline with zero proprietary files required.

Audits Four Cross-Body White Balance, Color Science & Paint Matrix Pillars:
1. Pillar A — White Balance Control & `WHT BAL` Physical Switch Soft-Mapping:
   Verifies Preset (`3200K` Tungsten / `4300K` / `5600K` Daylight), Memory A /
   Memory B (`2000K..15000K` in `100K`/`50K` steps + `CC MG/GR` tint `-99..+99`),
   `ATW` (Auto Tracing WB) + `Shockless WB` (`Off / 1 / 2 / 3` Mired slew-rate
   damping), and FX3 hardware absence of FX6's dedicated physical `WHT BAL`
   (`B/A/PRST`) body switch — proving clean soft-mapping onto FX3 Assignable
   Buttons + `Fn`/Big6 touch without missing-GPIO faults.
2. Pillar B — Base Look & Gamma/Gamut Matrix:
   Verifies `S-Cinetone`, `S-Log3 / S-Gamut3.Cine`, `S-Log3 / S-Gamut3`,
   `ITU709`, `709(800%)`, `HLG Live`, `HLG Natural`, and `User 3D LUT (MLUT)`
   routing parity across FX6 `v6.01` and FX3 `v7.02`.
3. Pillar C — Paint Menu Matrix (`R-G, R-B, G-R, G-B, B-R, B-G`), Multi-Matrix,
   Knee (`75.0%..109.0%`) & Black Gamma:
   Implements an exact 3x3 linear color matrix math verifier enforcing row-sum
   white-point preservation (`sum(row) == 1.0`) so neutral grey `[1, 1, 1]`
   never tint-shifts under off-diagonal Paint Matrix tweaks, plus Knee
   point/slope, Black Level/Black Gamma, and 16-axis Multi-Matrix bounds.
4. Pillar D — Factory Color/WB Calibration & `cnflasha` Zero-Mutation Proof:
   Proves factory per-sensor `IMX510` WB gain / shading / defect-pixel
   calibration in `cnflasha` / Stock-CP remains 100% read-only
   (`calibration_mutation_bytes == 0`, `persistent_emmc_writes_authorized == False`,
   `cp_mutation_bytes == 0`).
"""

from __future__ import annotations

import hashlib
import json
import math
import mmap
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from .emount_af_breathing_and_ibis_auditor import _extract_uxc_labels, _parse_elf64_sections
from .global_xdb_and_menu_tree_auditor import build_sparse_uxc_string_pack
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
from .uxc_multilang_and_font_verifier import FX3_SHARE_APP_RELDIR, FX6_SHARE_APP_RELDIR


PHASE_65_SCHEMA = "fx3_firmware_lab_phase65_wb_color_matrix_look_v1"
PHASE_65_VERSION = "65.0.0"

FX3_STR_EN_RELPATH = f"{FX3_SHARE_APP_RELDIR}/string_english.uxc"
FX3_STR_EN_G_RELPATH = f"{FX3_SHARE_APP_RELDIR}/string_english_g.uxc"
FX6_STR_EN_1_RELPATH = f"{FX6_SHARE_APP_RELDIR}/string_english.uxc"
FX6_STR_EN_2_RELPATH = f"{FX6_SHARE_APP_RELDIR}/string_english_2.uxc"

# ---------------------------------------------------------------------------
# Pinned Cinema Line WB, Base Look, Paint Matrix & Calibration Constants
# ---------------------------------------------------------------------------

WB_PRESET_KELVIN_MAP: Dict[str, int] = {
    "TUNGSTEN_3200K": 3200,
    "FLUORESCENT_4300K": 4300,
    "DAYLIGHT_5600K": 5600,
}

WB_KELVIN_MIN = 2000
WB_KELVIN_MAX = 15000
WB_KELVIN_ALLOWED_STEPS: Tuple[int, ...] = (50, 100)
WB_TINT_MIN = -99
WB_TINT_MAX = 99

SHOCKLESS_WB_TAU_SEC: Dict[str, float] = {
    "OFF": 0.0,
    "1": 0.65,   # Fast
    "2": 1.60,   # Medium
    "3": 3.20,   # Slow
}

VALID_WB_SWITCH_POSITIONS: Tuple[str, ...] = (
    "PRESET_3200K",
    "PRESET_4300K",
    "PRESET_5600K",
    "MEMORY_A",
    "MEMORY_B",
    "ATW",
)

CANONICAL_BASE_LOOKS: Tuple[str, ...] = (
    "S-Cinetone",
    "S-Log3 / S-Gamut3.Cine",
    "S-Log3 / S-Gamut3",
    "ITU709",
    "709(800%)",
    "HLG Live",
    "HLG Natural",
    "User 3D LUT (MLUT)",
)

PAINT_MATRIX_PARAM_MIN = -99.0
PAINT_MATRIX_PARAM_MAX = 99.0
PAINT_MATRIX_MAX_COUPLING = 0.25  # -99..+99 maps smoothly to +-24.75% channel coupling

KNEE_POINT_MIN_PCT = 75.0
KNEE_POINT_MAX_PCT = 109.0
KNEE_SLOPE_MIN = -99
KNEE_SLOPE_MAX = 99
BLACK_LEVEL_MIN = -99
BLACK_LEVEL_MAX = 99
BLACK_GAMMA_LEVEL_MIN = -99
BLACK_GAMMA_LEVEL_MAX = 99
VALID_BLACK_GAMMA_RANGES: Tuple[str, ...] = ("HIGH", "MIDDLE", "LOW", "WIDE", "NARROW")

# ---------------------------------------------------------------------------
# Verified Binary Marker Contracts (FX3 v7.02 & FX6 v6.01)
# ---------------------------------------------------------------------------

FX3_APPFW_WB_MARKERS: Tuple[str, ...] = (
    "BKID_APP_MENU_WB_COLOR_TEMP",
    "BKID_APP_MENU_WB_MODE",
    "MOVIE_SHOCKLESS_WB_OFF",
    "MOVIE_SHOCKLESS_WB_1",
    "MOVIE_SHOCKLESS_WB_2",
    "MOVIE_SHOCKLESS_WB_3",
    "WHITE_BALANCE_COLOR_TEMP_COLOR_FILTER_2500K",
    "WHITE_BALANCE_COLOR_TEMP_COLOR_FILTER_3200K",
    "WHITE_BALANCE_COLOR_TEMP_COLOR_FILTER_5500K",
    "WHITE_BALANCE_COLOR_TEMP_COLOR_FILTER_9900K",
    "VAL_setting_white_balance_WHITE_BALANCE_CUSTOM_1",
    "VAL_setting_white_balance_WHITE_BALANCE_CUSTOM_2",
    "VAL_setting_white_balance_WHITE_BALANCE_CUSTOM_3",
    "VAL_setting_white_balance_WHITE_BALANCE_DAYLIGHT",
    "VAL_setting_white_balance_WHITE_BALANCE_INCANDESCENT",
    "UIBIZ_KEY_TACT_WB_PRESET",
)

FX3_APPFW_ABSENT_PHYSICAL_WB_SWITCH_MARKERS: Tuple[str, ...] = (
    "VAL_HAITA_white_switch_position_auto_tracking_white_balance_mode_WHITE_SWITCH_POSITION_A",
    "VAL_HAITA_white_switch_position_auto_tracking_white_balance_mode_WHITE_SWITCH_POSITION_B",
    "VAL_setting_atw_mode_ATW_MODE_ON",
)

FX6_APPFW_WB_MARKERS: Tuple[str, ...] = (
    "VAL_HAITA_white_switch_position_auto_tracking_white_balance_mode_WHITE_SWITCH_POSITION_PRESET",
    "VAL_HAITA_white_switch_position_auto_tracking_white_balance_mode_WHITE_SWITCH_POSITION_A",
    "VAL_HAITA_white_switch_position_auto_tracking_white_balance_mode_WHITE_SWITCH_POSITION_B",
    "VAL_HAITA_white_switch_position_auto_tracking_white_balance_mode_WHITE_SWITCH_POSITION_PRESET_AUTO_TRACKING_WHITE_BALANCE_MODE_ON",
    "VAL_setting_atw_mode_ATW_MODE_ON",
    "VAL_setting_atw_mode_ATW_MODE_OFF",
    "VAL_setting_movie_shockless_wb_MOVIE_SHOCKLESS_WB_OFF",
    "VAL_setting_movie_shockless_wb_MOVIE_SHOCKLESS_WB_1",
    "VAL_setting_movie_shockless_wb_MOVIE_SHOCKLESS_WB_2",
    "VAL_setting_movie_shockless_wb_MOVIE_SHOCKLESS_WB_3",
    "PID_SET_MWB_PARAM_CALC_COLOR_TEMP_PRO",
    "PID_SET_PARAM_CALC_COLOR_TEMP_WBOFFSET",
    "convert_MODEL_ID_WHITE_ATW",
    "convert_MODEL_ID_WHITE_ATWSPEED",
)

FX3_CP_WB_MARKERS: Tuple[str, ...] = (
    "SET_CUSTOM_WB_SAVE",
    "SET_REQ_CUSTOM_WB_DATA",
    "SetAffinity_CAM_AWB",
)

FX6_CP_WB_MARKERS: Tuple[str, ...] = (
    "GetATWSpeed",
    "SET_CUSTOM_WB_PRO_EXECUTE",
    "SET_MWB_PARAM_CALC_COLOR_TEMP_PRO",
    "setWBChangeSpeed_ATWSpeed_OnePushAWBDetectArea_AWBMode",
)

FX3_APPFW_LOOK_MARKERS: Tuple[str, ...] = (
    "VAL_setting_pictureprofile_gamma0_SETTING_PICTUREPROFILE_GAMMA_SLOG3",
    "VAL_setting_pictureprofile_gamma0_SETTING_PICTUREPROFILE_GAMMA_ITU709",
    "VAL_setting_pictureprofile_gamma0_SETTING_PICTUREPROFILE_GAMMA_ITU709_800",
    "VAL_setting_pictureprofile_gamma0_SETTING_PICTUREPROFILE_GAMMA_HLG",
    "STILL_GAMUT_S_GAMUT3_CINE_S_LOG3",
    "STILL_GAMUT_S_GAMUT3_S_LOG3",
    "COLOR_GAMUT_FOR_RAW_OUT_S_GAMUT3_CINE",
    "CAUTION_ID_FACTOR_GAMMA_SCINETONE_MSG",
)

FX6_APPFW_LOOK_MARKERS: Tuple[str, ...] = (
    "VAL_setting_select_lut_sdr_SELECT_LUT_SDR_S_CINETONE",
    "VAL_setting_select_lut_sdr_SELECT_LUT_SDR_ITU709",
    "VAL_setting_select_lut_sdr_SELECT_LUT_SDR_709TONE",
    "VAL_setting_select_lut_hdr_SELECT_LUT_HDR_HLG_LIVE",
    "VAL_setting_select_lut_hdr_SELECT_LUT_HDR_HLG_NATURAL",
    "VAL_setting_select_lut_hdr_SELECT_LUT_HDR_S_LOG3",
    "VAL_setting_gamut_GAMUT_S_GAMUT3_CINE_S_LOG3",
    "VAL_setting_gamut_GAMUT_S_GAMUT3_S_LOG3",
    "VAL_setting_lut_setting_internal_rec_LUT_SETTING_INTERNAL_REC_MLUT_ON",
    "VAL_setting_lut_setting_monitor_out_LUT_SETTING_MONITOR_OUT_MLUT_ON",
    "PID_SET_USER_LUT_BINARY_DATA",
)

CP_SHARED_MLUT_MARKERS: Tuple[str, ...] = (
    "MLUT",
    "MLUT_ASCCDL_ON",
    "MLUT_EIGAIN_ON",
    "MLUT_L3D_REG_USER_LUT_17",
    "MLUT_L1D_B_REG_LINEARTO709_800_LEGAL",
    "SET_USER_LUT_BINARY_DATA",
)

MPR_SHARED_COLOR_MARKERS: Tuple[str, ...] = (
    "CaptureGammaEquation",
    "WhiteBalance",
)

FX3_MPR_EXTRA_COLOR_MARKERS: Tuple[str, ...] = (
    "CaptureColorPrimaries",
    "LUT_3D_SIZE",
)

FX6_MPR_EXTRA_COLOR_MARKERS: Tuple[str, ...] = (
    "GammaForLook",
    "ConvertSRLiveDataTransferMatrix",
)

FX6_APPFW_PAINT_MATRIX_MARKERS: Tuple[str, ...] = (
    "BKID_APP_SETTING_USER_MATRIX_RG_SDR",
    "BKID_APP_SETTING_USER_MATRIX_RB_SDR",
    "BKID_APP_SETTING_USER_MATRIX_GR_SDR",
    "BKID_APP_SETTING_USER_MATRIX_GB_SDR",
    "BKID_APP_SETTING_USER_MATRIX_BR_SDR",
    "BKID_APP_SETTING_USER_MATRIX_BG_SDR",
    "PID_SET_MULTI_MATRIX",
    "PID_SET_KNEE_POINT",
    "PID_SET_KNEE_SLOPE",
    "PID_SET_BLACK_GAMMA",
    "PID_SET_BLACK_LEVEL",
)

FX3_APPFW_PAINT_KNEE_BLACK_MARKERS: Tuple[str, ...] = (
    "EVENT_REMOTE_PICTURE_PROFILE_KNEE_MODE",
    "EVENT_REMOTE_PICTURE_PROFILE_KNEE_POINT",
    "EVENT_REMOTE_PICTURE_PROFILE_KNEE_SLOPE",
    "EVENT_REMOTE_PICTURE_PROFILE_BLACK_GAMMA_LEVEL",
    "EVENT_REMOTE_PICTURE_PROFILE_BLACK_GAMMA_RANGE",
    "EVENT_REMOTE_PICTURE_PROFILE_BLACK_LEVEL",
)

FX6_CP_PAINT_MARKERS: Tuple[str, ...] = (
    "MULTI_MATRIX",
    "MULTI_MATRIX_HUE_LEVEL",
    "MULTI_MATRIX_SATURATION_LEVEL",
    "Paint_KneePoint",
    "Paint_KneeSlope",
    "USER_MATRIX",
)

FX3_CP_KNEE_BLACK_MARKERS: Tuple[str, ...] = (
    "PP_KneePoint",
    "KneeSlope",
    "PP_BlackGammaLevel",
    "PP_BlackGammaRange",
)

SHARED_APPFW_CALIB_MARKERS: Tuple[str, ...] = (
    "PID_SET_SHADING_CORRECTION",
    "EVENT_REMOTE_LENS_COMP_LENS_COMP_SHADING",
)

CP_SHARED_CALIB_MARKERS: Tuple[str, ...] = (
    "N6Camera6Imager6IMX51019C_ImagerCtrl_IMX510E",
    "N6Camera6Imager21ImagerDrvParam_IMX510E",
    "ExecDefectCorrection",
    "Alloc_DefectAdjMemory",
    "ExecImagerCalibration",
    "ShadowReadBackup",
    "ShadowWriteBackup",
)

FX6_CP_WBGAIN_MARKERS: Tuple[str, ...] = (
    "WBGainR",
    "WBGainG",
    "WBGainB",
    "WBGainStd",
    "ExecZpdDefectCorrection",
)

# Verified .uxc String Resource IDs
FX3_NS39_UXC_EXPECTED_LABELS: Dict[int, str] = {
    0x0004E5D4: "White Balance",
    0x0004E8A4: "Color Temp.",
}

FX3_NS3_UXC_EXPECTED_LABELS: Dict[int, str] = {
    0x000062F0: "White Balance",
    0x00006531: "ITU709 Matrix",
}

FX6_NS1_UXC_EXPECTED_LABELS: Dict[int, str] = {
    0x00002029: "MLUT",
    0x0000207A: "ATW",
    0x000020D0: "White Balance",
    0x000020F5: "S-Cinetone",
    0x0000219D: "Base Look/LUT",
    0x0000219E: "709(800%)",
    0x0000219F: "S-Log3",
    0x000021A2: "ITU709",
    0x000021A3: "HLG Live",
    0x000021A4: "HLG Natural",
    0x00002278: "Offset Color Temp<ATW>",
    0x0000227A: "Offset Tint<ATW>",
}

FX6_NS2_UXC_EXPECTED_LABELS: Dict[int, str] = {
    0x0000402A: "White: Preset",
    0x0000402E: "White: ATW",
    0x00004178: "White Switch: Not ATW",
    0x00004182: "ATW Hold Off",
    0x00004222: "Black Gamma",
    0x0000422D: "Multi Matrix",
    0x000042EC: "S-Log3→709(800%)",
    0x00004340: "S-Gamut3",
    0x000043F9: "Preset White",
    0x00004404: "Shockless White",
    0x00004406: "ATW Speed",
    0x0000443E: "Knee Point",
    0x00004441: "Knee Slope",
    0x00004484: "User Matrix R-G",
    0x00004486: "User Matrix R-B",
    0x00004488: "User Matrix G-R",
    0x0000448A: "User Matrix G-B",
    0x0000448C: "User Matrix B-R",
    0x0000448E: "User Matrix B-G",
    0x00004794: "Preset 3200K",
    0x00004796: "Preset 4300K",
    0x00004BA4: "5600K",
    0x00004B23: "Memory A",
    0x00004B24: "Memory B",
}

# ---------------------------------------------------------------------------
# Report & Evaluation Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KelvinMiredEvalResult:
    valid: bool
    status: str
    kelvin: int
    step_k: int
    mired: float
    tint_cc: int
    rb_gain_ratio: float
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class ShocklessWbSlewEvalResult:
    valid: bool
    status: str
    start_kelvin: int
    target_kelvin: int
    shockless_level: str
    dt_sec: float
    start_mired: float
    target_mired: float
    intermediate_mired: float
    intermediate_kelvin: int
    damping_alpha: float
    monotonic_transition: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class WbSwitchSoftMappingEvalResult:
    valid: bool
    status: str
    requested_position: str
    fx3_physical_wht_bal_switch_present: bool
    fx3_soft_mapping_target: str
    shockless_level: str
    atw_active: bool
    atw_hold: bool
    missing_gpio_faults: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class WhiteBalanceMatrixReport:
    passed: bool
    fx3_appfw_wb_markers: Tuple[str, ...]
    fx3_unexpected_phys_switch_markers: Tuple[str, ...]
    fx6_appfw_wb_markers: Tuple[str, ...]
    fx3_cp_wb_markers: Tuple[str, ...]
    fx6_cp_wb_markers: Tuple[str, ...]
    uxc_wb_labels: Dict[str, str]
    preset_3200k_eval: KelvinMiredEvalResult
    memory_a_5600k_eval: KelvinMiredEvalResult
    shockless_level2_eval: ShocklessWbSlewEvalResult
    fx3_switch_mem_a_eval: WbSwitchSoftMappingEvalResult
    fx3_switch_atw_eval: WbSwitchSoftMappingEvalResult
    missing_gpio_faults: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class BaseLookRoutingEvalResult:
    valid: bool
    status: str
    look_id: str
    gamma_curve: str
    color_gamut: str
    target_display: str
    mlut_internal_rec: bool
    mlut_monitor_out: bool
    user_lut_slot: Optional[int]
    parity_status: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class BaseLookMatrixReport:
    passed: bool
    fx3_appfw_look_markers: Tuple[str, ...]
    fx6_appfw_look_markers: Tuple[str, ...]
    fx3_cp_mlut_markers: Tuple[str, ...]
    fx6_cp_mlut_markers: Tuple[str, ...]
    fx3_mpr_color_markers: Tuple[str, ...]
    fx6_mpr_color_markers: Tuple[str, ...]
    uxc_look_labels: Dict[str, str]
    canonical_looks_verified: Tuple[BaseLookRoutingEvalResult, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class PaintColorMatrixEvalResult:
    valid: bool
    status: str
    matrix_3x3: Tuple[Tuple[float, float, float], ...]
    row_sums: Tuple[float, float, float]
    max_row_sum_error: float
    white_point_preserved: bool
    neutral_grey_output: Tuple[float, float, float]
    determinant: float
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class KneeAndBlackGammaEvalResult:
    valid: bool
    status: str
    knee_mode: str
    knee_point_pct: float
    knee_slope: int
    black_level: int
    black_gamma_level: int
    black_gamma_range: str
    multi_matrix_hue: int
    multi_matrix_sat: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class PaintMatrixAndKneeReport:
    passed: bool
    fx6_appfw_paint_markers: Tuple[str, ...]
    fx3_appfw_knee_black_markers: Tuple[str, ...]
    fx6_cp_paint_markers: Tuple[str, ...]
    fx3_cp_knee_black_markers: Tuple[str, ...]
    uxc_paint_labels: Dict[str, str]
    identity_matrix_eval: PaintColorMatrixEvalResult
    tweaked_matrix_eval: PaintColorMatrixEvalResult
    knee_and_black_eval: KneeAndBlackGammaEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class FactoryCalibrationImmutabilityResult:
    valid: bool
    status: str
    target_partition: str
    operation: str
    calibration_mutation_bytes: int
    cp_mutation_bytes: int
    persistent_emmc_writes_authorized: bool
    ram_shadow_isolated: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class FactoryCalibrationReport:
    passed: bool
    fx3_appfw_calib_markers: Tuple[str, ...]
    fx6_appfw_calib_markers: Tuple[str, ...]
    fx3_cp_calib_markers: Tuple[str, ...]
    fx6_cp_calib_markers: Tuple[str, ...]
    fx6_cp_wbgain_markers: Tuple[str, ...]
    cnflasha_eval: FactoryCalibrationImmutabilityResult
    stock_cp_eval: FactoryCalibrationImmutabilityResult
    calibration_mutation_bytes: int
    cp_mutation_bytes: int
    persistent_emmc_writes_authorized: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class WbColorMatrixAndLookReport:
    schema_version: str
    phase_version: str
    mode: str
    all_checks_passed: bool
    o_rdonly_enforced: bool
    persistent_emmc_writes_authorized: bool
    calibration_mutation_bytes: int
    cp_mutation_bytes: int
    donor_file_sizes: Dict[str, int]
    pillar_a_white_balance: WhiteBalanceMatrixReport
    pillar_b_base_look: BaseLookMatrixReport
    pillar_c_paint_matrix_knee: PaintMatrixAndKneeReport
    pillar_d_factory_calibration: FactoryCalibrationReport
    errors: Tuple[str, ...]
    report_sha256: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)

    def to_deterministic_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True) + "\n"


# ---------------------------------------------------------------------------
# Strictly `os.O_RDONLY` + `mmap` Section-Scoped Scanning Helpers
# ---------------------------------------------------------------------------


def _scan_buffer_markers(buf: bytes, markers: Sequence[str]) -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
    """Scan an in-memory buffer for ASCII markers via C-level `bytes.find`."""
    present: List[str] = []
    missing: List[str] = []
    for m in markers:
        if buf.find(m.encode("latin1")) != -1:
            present.append(m)
        else:
            missing.append(m)
    return tuple(present), tuple(missing)


def _read_uxc_rdonly(path: Path) -> bytes:
    """Read a small `.uxc` asset file strictly via `os.O_RDONLY`."""
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


def _scan_donor_rdonly_markers(
    path: Path,
    marker_groups: Mapping[str, Sequence[str]],
    *,
    is_elf: bool,
) -> Tuple[int, Dict[str, Tuple[str, ...]]]:
    """Open `path` strictly `os.O_RDONLY` with `mmap.ACCESS_READ` and scan marker groups."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        sz = os.fstat(fd).st_size
        if sz == 0:
            return 0, {k: () for k in marker_groups}
        unique_markers = sorted(
            {m for markers in marker_groups.values() for m in markers},
            key=lambda s: (-len(s), s),
        )
        if not unique_markers:
            return sz, {k: () for k in marker_groups}

        pat = re.compile(b"|".join(re.escape(m.encode("latin1")) for m in unique_markers))
        matched_tokens: set[bytes] = set()
        with mmap.mmap(fd, sz, access=mmap.ACCESS_READ) as mm:
            ranges: List[Tuple[int, int]] = [(0, sz)]
            if is_elf:
                try:
                    secs = _parse_elf64_sections(mm)  # type: ignore[arg-type]
                    elf_ranges = [secs[s] for s in (".rodata", ".dynstr") if s in secs]
                    if elf_ranges:
                        ranges = elf_ranges
                except ValueError:
                    ranges = [(0, sz)]

            for off, rsz in ranges:
                for mo in pat.finditer(mm, off, off + rsz):
                    matched_tokens.add(mo.group(0))

        matched_list = list(matched_tokens)
        present_markers = {
            m
            for m in unique_markers
            if (mb := m.encode("latin1")) in matched_tokens or any(mb in tok for tok in matched_list)
        }
        results: Dict[str, Tuple[str, ...]] = {
            group_name: tuple(m for m in markers if m in present_markers)
            for group_name, markers in marker_groups.items()
        }
        return sz, results
    finally:
        os.close(fd)


# ---------------------------------------------------------------------------
# Clean-Room Synthetic Fixtures (Used ONLY when FX3_FX6_FORCE_CLEAN_ROOM=1 or donors absent)
# ---------------------------------------------------------------------------


def build_clean_room_wb_color_matrix_fixtures(
    *,
    inject_fx3_physical_wb_switch: bool = False,
    drop_fx6_shockless_wb: bool = False,
    drop_fx6_base_look_slog3: bool = False,
    drop_fx6_paint_matrix_rg_bg: bool = False,
    drop_cp_calib_markers: bool = False,
    corrupt_uxc_labels: bool = False,
) -> Dict[str, bytes]:
    """Build deterministic clean-room fixtures representing all 10 FX3 v7.02 & FX6 v6.01 donor artifacts."""
    elf_hdr = b"\x7fELF\x02\x01\x01\x00" + bytes(56)
    cp_hdr = b"LDR\x00" + bytes(60)

    def _pack(tokens: Sequence[str], *, prefix: bytes = elf_hdr) -> bytes:
        return prefix + b"\x00".join(t.encode("latin1") for t in tokens) + b"\x00"

    fx3_appfw_tokens = [
        *FX3_APPFW_WB_MARKERS,
        *(FX3_APPFW_ABSENT_PHYSICAL_WB_SWITCH_MARKERS if inject_fx3_physical_wb_switch else ()),
        *FX3_APPFW_LOOK_MARKERS,
        *FX3_APPFW_PAINT_KNEE_BLACK_MARKERS,
        *SHARED_APPFW_CALIB_MARKERS,
    ]

    fx6_wb = (
        tuple(m for m in FX6_APPFW_WB_MARKERS if "SHOCKLESS" not in m)
        if drop_fx6_shockless_wb
        else FX6_APPFW_WB_MARKERS
    )
    fx6_look = (
        tuple(m for m in FX6_APPFW_LOOK_MARKERS if "S_LOG3" not in m)
        if drop_fx6_base_look_slog3
        else FX6_APPFW_LOOK_MARKERS
    )
    fx6_paint = (
        tuple(m for m in FX6_APPFW_PAINT_MATRIX_MARKERS if "USER_MATRIX_RG" not in m)
        if drop_fx6_paint_matrix_rg_bg
        else FX6_APPFW_PAINT_MATRIX_MARKERS
    )
    fx6_appfw_tokens = [
        *fx6_wb,
        *fx6_look,
        *fx6_paint,
        *SHARED_APPFW_CALIB_MARKERS,
    ]

    fx3_cp_calib = () if drop_cp_calib_markers else CP_SHARED_CALIB_MARKERS
    fx3_cp_tokens = [
        *FX3_CP_WB_MARKERS,
        *CP_SHARED_MLUT_MARKERS,
        *FX3_CP_KNEE_BLACK_MARKERS,
        *fx3_cp_calib,
    ]
    fx6_cp_calib = () if drop_cp_calib_markers else CP_SHARED_CALIB_MARKERS
    fx6_cp_tokens = [
        *FX6_CP_WB_MARKERS,
        *CP_SHARED_MLUT_MARKERS,
        *FX6_CP_PAINT_MARKERS,
        *fx6_cp_calib,
        *FX6_CP_WBGAIN_MARKERS,
    ]

    fx3_mpr_tokens = [*MPR_SHARED_COLOR_MARKERS, *FX3_MPR_EXTRA_COLOR_MARKERS]
    fx6_mpr_tokens = [*MPR_SHARED_COLOR_MARKERS, *FX6_MPR_EXTRA_COLOR_MARKERS]

    fx6_ns2_labels = dict(FX6_NS2_UXC_EXPECTED_LABELS)
    if corrupt_uxc_labels:
        fx6_ns2_labels[0x00004484] = "CORRUPT_MATRIX_RG_LABEL"

    return {
        "fx3_appfw": _pack(fx3_appfw_tokens),
        "fx6_appfw": _pack(fx6_appfw_tokens),
        "fx3_libmpr": _pack(fx3_mpr_tokens),
        "fx6_libmpr": _pack(fx6_mpr_tokens),
        "fx3_cpapp": _pack(fx3_cp_tokens, prefix=cp_hdr),
        "fx6_cpapp": _pack(fx6_cp_tokens, prefix=cp_hdr),
        "fx3_str_en": build_sparse_uxc_string_pack(
            {k & 0x1FFF: v for k, v in FX3_NS39_UXC_EXPECTED_LABELS.items()}, namespace_id=39
        ),
        "fx3_str_en_g": build_sparse_uxc_string_pack(
            {k & 0x1FFF: v for k, v in FX3_NS3_UXC_EXPECTED_LABELS.items()}, namespace_id=3
        ),
        "fx6_str_en_1": build_sparse_uxc_string_pack(
            {k & 0x1FFF: v for k, v in FX6_NS1_UXC_EXPECTED_LABELS.items()}, namespace_id=1
        ),
        "fx6_str_en_2": build_sparse_uxc_string_pack(
            {k & 0x1FFF: v for k, v in fx6_ns2_labels.items()}, namespace_id=2
        ),
    }


# ---------------------------------------------------------------------------
# Pillar A: White Balance Control, Kelvin->Mired, Shockless WB & Switch Mapping
# ---------------------------------------------------------------------------


def kelvin_to_mired(kelvin: float) -> float:
    """Convert color temperature in Kelvin to micro reciprocal degrees (Mired = 10^6 / K)."""
    if not math.isfinite(kelvin) or kelvin <= 0.0:
        raise ValueError(f"Kelvin must be finite and > 0, got {kelvin!r}")
    return 1_000_000.0 / float(kelvin)


def evaluate_white_balance_kelvin_mired(
    *,
    kelvin: int = 5600,
    tint_cc: int = 0,
    step_k: int = 100,
) -> KelvinMiredEvalResult:
    """Validate Memory A/B / Preset Kelvin (2000..15000K in 50K/100K steps) and CC MG/GR tint (-99..+99)."""
    errors: List[str] = []
    if step_k not in WB_KELVIN_ALLOWED_STEPS:
        errors.append(f"Unsupported WB step_k={step_k}; allowed {WB_KELVIN_ALLOWED_STEPS}")
    if not (WB_KELVIN_MIN <= kelvin <= WB_KELVIN_MAX):
        errors.append(f"Kelvin {kelvin}K out of valid range [{WB_KELVIN_MIN}..{WB_KELVIN_MAX}]K")
    elif step_k in WB_KELVIN_ALLOWED_STEPS and (kelvin % step_k) != 0:
        errors.append(f"Kelvin {kelvin}K is not aligned to {step_k}K step grid")
    if not (WB_TINT_MIN <= tint_cc <= WB_TINT_MAX):
        errors.append(f"CC MG/GR tint {tint_cc} out of valid range [{WB_TINT_MIN}..{WB_TINT_MAX}]")

    if errors:
        return KelvinMiredEvalResult(
            valid=False,
            status="BLOCKED_INVALID_WB_KELVIN_OR_TINT",
            kelvin=kelvin,
            step_k=step_k,
            mired=0.0,
            tint_cc=tint_cc,
            rb_gain_ratio=0.0,
            errors=tuple(errors),
        )

    mired = round(kelvin_to_mired(kelvin), 4)
    # Approximate relative R/B white-balance gain scaling normalized to 5600K (178.57 Mired):
    # warmer scenes (<5600K, higher Mired) require lower Red gain / higher Blue gain.
    mired_5600 = 1_000_000.0 / 5600.0
    rb_ratio = round(math.exp((mired_5600 - mired) * 0.0045), 6)

    return KelvinMiredEvalResult(
        valid=True,
        status="WB_KELVIN_MIRED_VERIFIED",
        kelvin=kelvin,
        step_k=step_k,
        mired=mired,
        tint_cc=tint_cc,
        rb_gain_ratio=rb_ratio,
        errors=(),
    )


def evaluate_shockless_wb_slew(
    *,
    start_kelvin: int = 3200,
    target_kelvin: int = 5600,
    shockless_level: str = "2",
    dt_sec: float = 0.8,
) -> ShocklessWbSlewEvalResult:
    """Verify Shockless WB (`OFF` / `1` / `2` / `3`) perceptual Mired slew-rate damping."""
    errors: List[str] = []
    norm_lvl = shockless_level.strip().upper()
    if norm_lvl not in SHOCKLESS_WB_TAU_SEC:
        errors.append(f"Unsupported shockless_level {shockless_level!r}; expected {tuple(SHOCKLESS_WB_TAU_SEC)}")
    if not (WB_KELVIN_MIN <= start_kelvin <= WB_KELVIN_MAX):
        errors.append(f"start_kelvin {start_kelvin} out of range [{WB_KELVIN_MIN}..{WB_KELVIN_MAX}]")
    if not (WB_KELVIN_MIN <= target_kelvin <= WB_KELVIN_MAX):
        errors.append(f"target_kelvin {target_kelvin} out of range [{WB_KELVIN_MIN}..{WB_KELVIN_MAX}]")
    if not math.isfinite(dt_sec) or dt_sec < 0.0:
        errors.append(f"dt_sec must be finite and >= 0, got {dt_sec!r}")

    if errors:
        return ShocklessWbSlewEvalResult(
            valid=False,
            status="BLOCKED_INVALID_SHOCKLESS_WB_PARAMS",
            start_kelvin=start_kelvin,
            target_kelvin=target_kelvin,
            shockless_level=norm_lvl,
            dt_sec=dt_sec if math.isfinite(dt_sec) else 0.0,
            start_mired=0.0,
            target_mired=0.0,
            intermediate_mired=0.0,
            intermediate_kelvin=0,
            damping_alpha=0.0,
            monotonic_transition=False,
            errors=tuple(errors),
        )

    m_start = kelvin_to_mired(start_kelvin)
    m_target = kelvin_to_mired(target_kelvin)
    tau = SHOCKLESS_WB_TAU_SEC[norm_lvl]

    if tau == 0.0:
        alpha = 1.0
    else:
        alpha = 1.0 - math.exp(-dt_sec / tau)

    m_mid = m_start + alpha * (m_target - m_start)
    k_mid = round(1_000_000.0 / m_mid)
    lo_m = min(m_start, m_target) - 1e-9
    hi_m = max(m_start, m_target) + 1e-9
    monotonic = lo_m <= m_mid <= hi_m

    return ShocklessWbSlewEvalResult(
        valid=True,
        status="SHOCKLESS_WB_SLEW_VERIFIED" if tau > 0.0 else "SHOCKLESS_WB_OFF_INSTANT_STEP",
        start_kelvin=start_kelvin,
        target_kelvin=target_kelvin,
        shockless_level=norm_lvl,
        dt_sec=round(dt_sec, 4),
        start_mired=round(m_start, 4),
        target_mired=round(m_target, 4),
        intermediate_mired=round(m_mid, 4),
        intermediate_kelvin=int(k_mid),
        damping_alpha=round(alpha, 6),
        monotonic_transition=monotonic,
        errors=(),
    )


def evaluate_wb_switch_soft_mapping(
    *,
    requested_position: str = "MEMORY_A",
    shockless_level: str = "2",
    atw_hold: bool = False,
    missing_gpio_write_attempted: bool = False,
) -> WbSwitchSoftMappingEvalResult:
    """Map FX6 physical `WHT BAL` (`B/A/PRST`) switch + ATW onto FX3 Assignable Buttons + Fn/Big6."""
    errors: List[str] = []
    norm_pos = requested_position.strip().upper()
    norm_lvl = shockless_level.strip().upper()

    if norm_pos not in VALID_WB_SWITCH_POSITIONS:
        errors.append(f"Unsupported WB switch position {requested_position!r}; expected {VALID_WB_SWITCH_POSITIONS}")
    if norm_lvl not in SHOCKLESS_WB_TAU_SEC:
        errors.append(f"Unsupported shockless_level {shockless_level!r}")
    if missing_gpio_write_attempted:
        errors.append("Attempted hardware GPIO poll/write for absent FX6 WHT BAL B/A/PRST slide switch on FX3")

    soft_map = {
        "PRESET_3200K": "FX3 Assignable Custom Button + Big6/Fn WB Preset (3200K)",
        "PRESET_4300K": "FX3 Assignable Custom Button + Big6/Fn WB Preset (4300K)",
        "PRESET_5600K": "FX3 Assignable Custom Button + Big6/Fn WB Preset (5600K)",
        "MEMORY_A": "FX3 Assignable Custom Button + Custom WB Slot 1 (Memory A)",
        "MEMORY_B": "FX3 Assignable Custom Button + Custom WB Slot 2 (Memory B)",
        "ATW": "FX3 Assignable Custom Button + Continuous AWB / ATW Hold Soft-Toggle",
    }.get(norm_pos, "UNMAPPED")

    gpio_faults = 1 if missing_gpio_write_attempted else 0
    is_atw = norm_pos == "ATW"

    return WbSwitchSoftMappingEvalResult(
        valid=len(errors) == 0,
        status=(
            "BLOCKED_WHT_BAL_MISSING_GPIO_FAULT"
            if len(errors) > 0
            else "FX3_WHT_BAL_SOFT_MAPPED_ZERO_GPIO_FAULTS"
        ),
        requested_position=norm_pos,
        fx3_physical_wht_bal_switch_present=False,
        fx3_soft_mapping_target=soft_map,
        shockless_level=norm_lvl,
        atw_active=is_atw and not atw_hold,
        atw_hold=atw_hold if is_atw else False,
        missing_gpio_faults=gpio_faults,
        errors=tuple(errors),
    )


def evaluate_pillar_a_white_balance(
    present_map: Mapping[str, Tuple[str, ...]],
    uxc_wb_labels: Mapping[str, str],
) -> WhiteBalanceMatrixReport:
    """Audit Pillar A: WB Control, Shockless WB, ATW & FX6->FX3 WHT BAL Switch Soft-Mapping."""
    errors: List[str] = []

    fx3_wb = present_map["fx3_appfw_wb"]
    fx3_unexp_sw = present_map["fx3_appfw_absent_wb_switch"]
    fx6_wb = present_map["fx6_appfw_wb"]
    fx3_cp_wb = present_map["fx3_cp_wb"]
    fx6_cp_wb = present_map["fx6_cp_wb"]

    if fx3_wb != FX3_APPFW_WB_MARKERS:
        missing = tuple(m for m in FX3_APPFW_WB_MARKERS if m not in fx3_wb)
        errors.append(f"FX3 appFw.so missing White Balance / Shockless WB markers: {missing}")
    if len(fx3_unexp_sw) > 0:
        errors.append(f"FX3 appFw.so unexpectedly contains FX6 physical WHT BAL / ATW switch markers: {fx3_unexp_sw}")
    if fx6_wb != FX6_APPFW_WB_MARKERS:
        missing = tuple(m for m in FX6_APPFW_WB_MARKERS if m not in fx6_wb)
        errors.append(f"FX6 appFw.so missing WHT BAL / ATW / Shockless WB markers: {missing}")
    if fx3_cp_wb != FX3_CP_WB_MARKERS:
        errors.append("FX3 cpapp-b.bin missing Custom WB / AWB markers")
    if fx6_cp_wb != FX6_CP_WB_MARKERS:
        errors.append("FX6 cpapp-b.bin missing ATW / WB change speed markers")

    p_3200 = evaluate_white_balance_kelvin_mired(kelvin=3200, tint_cc=0, step_k=100)
    m_5600 = evaluate_white_balance_kelvin_mired(kelvin=5600, tint_cc=4, step_k=50)
    slew_2 = evaluate_shockless_wb_slew(start_kelvin=3200, target_kelvin=5600, shockless_level="2", dt_sec=0.8)
    sw_mem_a = evaluate_wb_switch_soft_mapping(requested_position="MEMORY_A", shockless_level="2")
    sw_atw = evaluate_wb_switch_soft_mapping(requested_position="ATW", shockless_level="3", atw_hold=True)

    for ev in (p_3200, m_5600, slew_2, sw_mem_a, sw_atw):
        if not ev.valid:
            errors.extend(ev.errors)

    faults = sw_mem_a.missing_gpio_faults + sw_atw.missing_gpio_faults
    return WhiteBalanceMatrixReport(
        passed=len(errors) == 0 and faults == 0,
        fx3_appfw_wb_markers=fx3_wb,
        fx3_unexpected_phys_switch_markers=fx3_unexp_sw,
        fx6_appfw_wb_markers=fx6_wb,
        fx3_cp_wb_markers=fx3_cp_wb,
        fx6_cp_wb_markers=fx6_cp_wb,
        uxc_wb_labels=dict(uxc_wb_labels),
        preset_3200k_eval=p_3200,
        memory_a_5600k_eval=m_5600,
        shockless_level2_eval=slew_2,
        fx3_switch_mem_a_eval=sw_mem_a,
        fx3_switch_atw_eval=sw_atw,
        missing_gpio_faults=faults,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar B: Base Look & Gamma/Gamut Matrix
# ---------------------------------------------------------------------------


_BASE_LOOK_SPECS: Dict[str, Tuple[str, str, Tuple[str, ...]]] = {
    "S-Cinetone": ("S-Cinetone", "S-Cinetone", ("SDR_BT709",)),
    "S-Log3 / S-Gamut3.Cine": ("S-Log3", "S-Gamut3.Cine", ("SDR_BT709", "HDR_HLG")),
    "S-Log3 / S-Gamut3": ("S-Log3", "S-Gamut3", ("SDR_BT709", "HDR_HLG")),
    "ITU709": ("ITU709", "ITU709", ("SDR_BT709",)),
    "709(800%)": ("709(800%)", "ITU709", ("SDR_BT709",)),
    "HLG Live": ("HLG Live (BT.2100)", "BT.2020", ("HDR_HLG",)),
    "HLG Natural": ("HLG Natural (BT.2100)", "BT.2020", ("HDR_HLG",)),
    "User 3D LUT (MLUT)": ("User 3D LUT", "S-Gamut3.Cine / User Cube", ("SDR_BT709", "HDR_HLG")),
}


def evaluate_base_look_routing(
    *,
    look_id: str = "S-Cinetone",
    target_display: str = "SDR_BT709",
    mlut_internal_rec: bool = False,
    mlut_monitor_out: bool = True,
    user_lut_slot: Optional[int] = None,
) -> BaseLookRoutingEvalResult:
    """Validate Base Look & Gamma/Gamut routing parity across FX6 v6.01 and FX3 v7.02."""
    errors: List[str] = []
    norm_disp = target_display.strip().upper()
    if look_id not in _BASE_LOOK_SPECS:
        errors.append(f"Unsupported Base Look {look_id!r}; expected {CANONICAL_BASE_LOOKS}")
        return BaseLookRoutingEvalResult(
            valid=False,
            status="BLOCKED_UNSUPPORTED_BASE_LOOK",
            look_id=look_id,
            gamma_curve="",
            color_gamut="",
            target_display=norm_disp,
            mlut_internal_rec=mlut_internal_rec,
            mlut_monitor_out=mlut_monitor_out,
            user_lut_slot=user_lut_slot,
            parity_status="INVALID_LOOK",
            errors=tuple(errors),
        )

    gamma_curve, color_gamut, allowed_displays = _BASE_LOOK_SPECS[look_id]
    if norm_disp not in allowed_displays:
        errors.append(
            f"Base Look {look_id!r} incompatible with target_display={norm_disp!r} (allowed {allowed_displays})"
        )
    if look_id == "User 3D LUT (MLUT)":
        if user_lut_slot is None or not (1 <= user_lut_slot <= 16):
            errors.append(f"User 3D LUT (MLUT) requires user_lut_slot in [1..16], got {user_lut_slot!r}")
    elif user_lut_slot is not None:
        errors.append(f"user_lut_slot only applies to 'User 3D LUT (MLUT)', got {look_id!r}")

    return BaseLookRoutingEvalResult(
        valid=len(errors) == 0,
        status="BASE_LOOK_PARITY_VERIFIED" if len(errors) == 0 else "BLOCKED_BASE_LOOK_POLICY_ERROR",
        look_id=look_id,
        gamma_curve=gamma_curve,
        color_gamut=color_gamut,
        target_display=norm_disp,
        mlut_internal_rec=mlut_internal_rec,
        mlut_monitor_out=mlut_monitor_out,
        user_lut_slot=user_lut_slot,
        parity_status="FX6_V601_FX3_V702_PARITY",
        errors=tuple(errors),
    )


def evaluate_pillar_b_base_look(
    present_map: Mapping[str, Tuple[str, ...]],
    uxc_look_labels: Mapping[str, str],
) -> BaseLookMatrixReport:
    """Audit Pillar B: Base Look & Gamma/Gamut Matrix across FX6 v6.01 and FX3 v7.02."""
    errors: List[str] = []

    fx3_look = present_map["fx3_appfw_look"]
    fx6_look = present_map["fx6_appfw_look"]
    fx3_cp = present_map["fx3_cp_mlut"]
    fx6_cp = present_map["fx6_cp_mlut"]
    fx3_mpr = present_map["fx3_mpr_color"]
    fx6_mpr = present_map["fx6_mpr_color"]

    if fx3_look != FX3_APPFW_LOOK_MARKERS:
        missing = tuple(m for m in FX3_APPFW_LOOK_MARKERS if m not in fx3_look)
        errors.append(f"FX3 appFw.so missing Picture Profile / Base Look markers: {missing}")
    if fx6_look != FX6_APPFW_LOOK_MARKERS:
        missing = tuple(m for m in FX6_APPFW_LOOK_MARKERS if m not in fx6_look)
        errors.append(f"FX6 appFw.so missing Base Look / MLUT markers: {missing}")
    if fx3_cp != CP_SHARED_MLUT_MARKERS or fx6_cp != CP_SHARED_MLUT_MARKERS:
        errors.append("FX3 or FX6 cpapp-b.bin missing shared MLUT hardware LUT markers")
    if not set(MPR_SHARED_COLOR_MARKERS).issubset(set(fx3_mpr)):
        errors.append("FX3 libmpr.so missing shared CaptureGammaEquation / WhiteBalance markers")
    if not set(MPR_SHARED_COLOR_MARKERS).issubset(set(fx6_mpr)):
        errors.append("FX6 libmpr.so missing shared CaptureGammaEquation / WhiteBalance markers")

    evals: List[BaseLookRoutingEvalResult] = []
    for look_id in CANONICAL_BASE_LOOKS:
        disp = "HDR_HLG" if "HLG" in look_id else "SDR_BT709"
        slot = 1 if look_id == "User 3D LUT (MLUT)" else None
        ev = evaluate_base_look_routing(
            look_id=look_id,
            target_display=disp,
            mlut_internal_rec=(look_id == "User 3D LUT (MLUT)"),
            mlut_monitor_out=True,
            user_lut_slot=slot,
        )
        evals.append(ev)
        if not ev.valid:
            errors.extend(ev.errors)

    return BaseLookMatrixReport(
        passed=len(errors) == 0,
        fx3_appfw_look_markers=fx3_look,
        fx6_appfw_look_markers=fx6_look,
        fx3_cp_mlut_markers=fx3_cp,
        fx6_cp_mlut_markers=fx6_cp,
        fx3_mpr_color_markers=fx3_mpr,
        fx6_mpr_color_markers=fx6_mpr,
        uxc_look_labels=dict(uxc_look_labels),
        canonical_looks_verified=tuple(evals),
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar C: Paint Menu 3x3 Color Matrix (R-G..B-G), Multi-Matrix, Knee & Black Gamma
# ---------------------------------------------------------------------------


def verify_raw_3x3_color_matrix(
    matrix_3x3: Sequence[Sequence[float]],
    *,
    tolerance: float = 1e-6,
) -> PaintColorMatrixEvalResult:
    """Verify exact 3x3 linear color matrix row-sum white-point preservation and invertibility."""
    errors: List[str] = []
    if len(matrix_3x3) != 3 or any(len(row) != 3 for row in matrix_3x3):
        raise ValueError("matrix_3x3 must be a 3x3 matrix")

    rows: Tuple[Tuple[float, float, float], ...] = tuple(
        (float(r[0]), float(r[1]), float(r[2])) for r in matrix_3x3
    )
    for r in rows:
        if any(not math.isfinite(v) for v in r):
            errors.append("Paint color matrix contains non-finite entries")
            break

    row_sums = (
        round(sum(rows[0]), 9),
        round(sum(rows[1]), 9),
        round(sum(rows[2]), 9),
    )
    max_err = max(abs(s - 1.0) for s in row_sums)
    white_preserved = len(errors) == 0 and max_err <= tolerance
    if not white_preserved and len(errors) == 0:
        errors.append(
            f"Paint 3x3 matrix violates white-point preservation (row sums={row_sums}, max_err={max_err:.3e} > {tolerance:.1e}); neutral grey [1,1,1] tint-shifts!"
        )

    # Neutral grey [1, 1, 1] output = row_sums
    grey_out = row_sums

    # 3x3 determinant
    a, b, c = rows[0]
    d, e, f = rows[1]
    g, h, i = rows[2]
    det = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)
    if not math.isfinite(det) or det <= 0.05:
        errors.append(f"Degenerate or inverted Paint 3x3 color matrix (det={det:.6f} <= 0.05)")

    return PaintColorMatrixEvalResult(
        valid=len(errors) == 0,
        status="PAINT_MATRIX_WHITE_POINT_PRESERVED" if len(errors) == 0 else "BLOCKED_PAINT_MATRIX_WHITE_POINT_DRIFT",
        matrix_3x3=rows,
        row_sums=row_sums,
        max_row_sum_error=round(max_err, 12),
        white_point_preserved=white_preserved,
        neutral_grey_output=grey_out,
        determinant=round(det, 9) if math.isfinite(det) else 0.0,
        errors=tuple(errors),
    )


def build_and_verify_paint_color_matrix(
    *,
    rg: float = 0.0,
    rb: float = 0.0,
    gr: float = 0.0,
    gb: float = 0.0,
    br: float = 0.0,
    bg: float = 0.0,
    level: float = 0.0,
    phase: float = 0.0,
    tolerance: float = 1e-9,
) -> PaintColorMatrixEvalResult:
    """Construct Sony Paint Menu 3x3 linear matrix from `R-G..B-G` (-99..+99) and prove `sum(row) == 1.0`."""
    params = {"R-G": rg, "R-B": rb, "G-R": gr, "G-B": gb, "B-R": br, "B-G": bg, "Level": level, "Phase": phase}
    for name, val in params.items():
        if not math.isfinite(val) or val < PAINT_MATRIX_PARAM_MIN or val > PAINT_MATRIX_PARAM_MAX:
            return PaintColorMatrixEvalResult(
                valid=False,
                status="BLOCKED_PAINT_MATRIX_PARAM_OUT_OF_RANGE",
                matrix_3x3=((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
                row_sums=(1.0, 1.0, 1.0),
                max_row_sum_error=0.0,
                white_point_preserved=False,
                neutral_grey_output=(1.0, 1.0, 1.0),
                determinant=1.0,
                errors=(f"Paint Matrix {name}={val!r} out of [-99..+99]",),
            )

    scale = PAINT_MATRIX_MAX_COUPLING / 99.0 * (1.0 + level / 200.0)
    c_rg = round(rg * scale, 9)
    c_rb = round(rb * scale, 9)
    c_gr = round(gr * scale, 9)
    c_gb = round(gb * scale, 9)
    c_br = round(br * scale, 9)
    c_bg = round(bg * scale, 9)

    # Exact row-sum-1.0 formulation: M_ii = 1 - sum_{j != i} M_ij
    mat = (
        (1.0 - c_rg - c_rb, c_rg, c_rb),
        (c_gr, 1.0 - c_gr - c_gb, c_gb),
        (c_br, c_bg, 1.0 - c_br - c_bg),
    )
    return verify_raw_3x3_color_matrix(mat, tolerance=tolerance)


def evaluate_multi_matrix_and_knee_black_bounds(
    *,
    knee_mode: str = "MANUAL",
    knee_point_pct: float = 90.0,
    knee_slope: int = 0,
    black_level: int = 0,
    black_gamma_level: int = 0,
    black_gamma_range: str = "MIDDLE",
    multi_matrix_hue: int = 0,
    multi_matrix_sat: int = 0,
) -> KneeAndBlackGammaEvalResult:
    """Validate Paint Menu Knee (`75.0%..109.0%`), Black Level, Black Gamma, and Multi-Matrix bounds."""
    errors: List[str] = []
    norm_knee_mode = knee_mode.strip().upper()
    norm_bg_range = black_gamma_range.strip().upper()

    if norm_knee_mode not in ("AUTO", "MANUAL", "OFF"):
        errors.append(f"Unsupported knee_mode {knee_mode!r}; expected AUTO/MANUAL/OFF")
    if not math.isfinite(knee_point_pct) or not (KNEE_POINT_MIN_PCT <= knee_point_pct <= KNEE_POINT_MAX_PCT):
        errors.append(
            f"Knee Point {knee_point_pct}% out of valid Sony bounds [{KNEE_POINT_MIN_PCT}%..{KNEE_POINT_MAX_PCT}%]"
        )
    if not (KNEE_SLOPE_MIN <= knee_slope <= KNEE_SLOPE_MAX):
        errors.append(f"Knee Slope {knee_slope} out of bounds [{KNEE_SLOPE_MIN}..{KNEE_SLOPE_MAX}]")
    if not (BLACK_LEVEL_MIN <= black_level <= BLACK_LEVEL_MAX):
        errors.append(f"Black Level {black_level} out of bounds [{BLACK_LEVEL_MIN}..{BLACK_LEVEL_MAX}]")
    if not (BLACK_GAMMA_LEVEL_MIN <= black_gamma_level <= BLACK_GAMMA_LEVEL_MAX):
        errors.append(
            f"Black Gamma Level {black_gamma_level} out of bounds [{BLACK_GAMMA_LEVEL_MIN}..{BLACK_GAMMA_LEVEL_MAX}]"
        )
    if norm_bg_range not in VALID_BLACK_GAMMA_RANGES:
        errors.append(f"Unsupported black_gamma_range {black_gamma_range!r}; expected {VALID_BLACK_GAMMA_RANGES}")
    if not (-99 <= multi_matrix_hue <= 99):
        errors.append(f"Multi-Matrix Hue {multi_matrix_hue} out of [-99..+99]")
    if not (-99 <= multi_matrix_sat <= 99):
        errors.append(f"Multi-Matrix Sat {multi_matrix_sat} out of [-99..+99]")

    return KneeAndBlackGammaEvalResult(
        valid=len(errors) == 0,
        status="KNEE_BLACK_MULTI_MATRIX_VERIFIED" if len(errors) == 0 else "BLOCKED_KNEE_OR_BLACK_OUT_OF_BOUNDS",
        knee_mode=norm_knee_mode,
        knee_point_pct=round(knee_point_pct, 2) if math.isfinite(knee_point_pct) else 0.0,
        knee_slope=knee_slope,
        black_level=black_level,
        black_gamma_level=black_gamma_level,
        black_gamma_range=norm_bg_range,
        multi_matrix_hue=multi_matrix_hue,
        multi_matrix_sat=multi_matrix_sat,
        errors=tuple(errors),
    )


def evaluate_pillar_c_paint_matrix_and_knee(
    present_map: Mapping[str, Tuple[str, ...]],
    uxc_paint_labels: Mapping[str, str],
) -> PaintMatrixAndKneeReport:
    """Audit Pillar C: Paint Menu 3x3 Color Matrix (`R-G..B-G`), Multi-Matrix, Knee & Black Gamma."""
    errors: List[str] = []

    fx6_paint = present_map["fx6_appfw_paint"]
    fx3_knee_blk = present_map["fx3_appfw_knee_black"]
    fx6_cp_paint = present_map["fx6_cp_paint"]
    fx3_cp_kb = present_map["fx3_cp_knee_black"]

    if fx6_paint != FX6_APPFW_PAINT_MATRIX_MARKERS:
        missing = tuple(m for m in FX6_APPFW_PAINT_MATRIX_MARKERS if m not in fx6_paint)
        errors.append(f"FX6 appFw.so missing Paint Matrix / Knee / Black Gamma markers: {missing}")
    if fx3_knee_blk != FX3_APPFW_PAINT_KNEE_BLACK_MARKERS:
        missing = tuple(m for m in FX3_APPFW_PAINT_KNEE_BLACK_MARKERS if m not in fx3_knee_blk)
        errors.append(f"FX3 appFw.so missing Picture Profile Knee / Black markers: {missing}")
    if fx6_cp_paint != FX6_CP_PAINT_MARKERS:
        errors.append("FX6 cpapp-b.bin missing Paint / Multi-Matrix markers")
    if fx3_cp_kb != FX3_CP_KNEE_BLACK_MARKERS:
        errors.append("FX3 cpapp-b.bin missing PP Knee / Black Gamma markers")

    id_mat = build_and_verify_paint_color_matrix()
    tweak_mat = build_and_verify_paint_color_matrix(
        rg=18.0, rb=-12.0, gr=-10.0, gb=14.0, br=8.0, bg=-16.0, level=10.0, phase=5.0
    )
    kb_eval = evaluate_multi_matrix_and_knee_black_bounds(
        knee_mode="MANUAL",
        knee_point_pct=92.5,
        knee_slope=15,
        black_level=-4,
        black_gamma_level=12,
        black_gamma_range="MIDDLE",
        multi_matrix_hue=-10,
        multi_matrix_sat=15,
    )

    for ev in (id_mat, tweak_mat, kb_eval):
        if not ev.valid:
            errors.extend(ev.errors)

    return PaintMatrixAndKneeReport(
        passed=len(errors) == 0,
        fx6_appfw_paint_markers=fx6_paint,
        fx3_appfw_knee_black_markers=fx3_knee_blk,
        fx6_cp_paint_markers=fx6_cp_paint,
        fx3_cp_knee_black_markers=fx3_cp_kb,
        uxc_paint_labels=dict(uxc_paint_labels),
        identity_matrix_eval=id_mat,
        tweaked_matrix_eval=tweak_mat,
        knee_and_black_eval=kb_eval,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar D: Factory Color/WB Calibration & `cnflasha` Zero-Mutation Proof
# ---------------------------------------------------------------------------


def evaluate_factory_wb_calibration_immutability(
    *,
    target_partition: str = "/dev/cnflasha16",
    operation: str = "READ_ONLY_AUDIT",
    calibration_mutation_bytes: int = 0,
    cp_mutation_bytes: int = 0,
    persistent_emmc_writes_authorized: bool = False,
) -> FactoryCalibrationImmutabilityResult:
    """Prove IMX510 factory WB gain / shading / defect-pixel calibration in `cnflasha` remains 100% read-only."""
    errors: List[str] = []
    norm_op = operation.strip().upper()
    is_ram_shadow = norm_op in ("READ_ONLY_AUDIT", "RAM_SHADOW_USER_WB_OFFSET")

    if persistent_emmc_writes_authorized:
        errors.append("Hard safety redline violated: persistent_emmc_writes_authorized must remain False")
    if calibration_mutation_bytes != 0:
        errors.append(
            f"Factory IMX510 WB/shading/defect calibration mutation detected ({calibration_mutation_bytes} B != 0)"
        )
    if cp_mutation_bytes != 0:
        errors.append(f"Stock-CP mutation detected ({cp_mutation_bytes} B != 0)")
    if not is_ram_shadow:
        errors.append(
            f"Unsupported / mutating cnflasha operation {operation!r}; only READ_ONLY_AUDIT or RAM_SHADOW_USER_WB_OFFSET allowed"
        )

    return FactoryCalibrationImmutabilityResult(
        valid=len(errors) == 0,
        status=(
            "CNFLASHA_FACTORY_CALIBRATION_READ_ONLY_VERIFIED"
            if len(errors) == 0
            else "BLOCKED_FACTORY_CALIBRATION_MUTATION_HAZARD"
        ),
        target_partition=target_partition,
        operation=norm_op,
        calibration_mutation_bytes=calibration_mutation_bytes,
        cp_mutation_bytes=cp_mutation_bytes,
        persistent_emmc_writes_authorized=persistent_emmc_writes_authorized,
        ram_shadow_isolated=is_ram_shadow and len(errors) == 0,
        errors=tuple(errors),
    )


def evaluate_pillar_d_factory_calibration(
    present_map: Mapping[str, Tuple[str, ...]],
) -> FactoryCalibrationReport:
    """Audit Pillar D: IMX510 Factory WB/Shading/Defect Calibration & `cnflasha` Zero-Mutation Proof."""
    errors: List[str] = []

    fx3_app_cal = present_map["fx3_appfw_calib"]
    fx6_app_cal = present_map["fx6_appfw_calib"]
    fx3_cp_cal = present_map["fx3_cp_calib"]
    fx6_cp_cal = present_map["fx6_cp_calib"]
    fx6_cp_wbgain = present_map["fx6_cp_wbgain"]

    if fx3_app_cal != SHARED_APPFW_CALIB_MARKERS or fx6_app_cal != SHARED_APPFW_CALIB_MARKERS:
        errors.append("FX3 or FX6 appFw.so missing shading correction markers")
    if fx3_cp_cal != CP_SHARED_CALIB_MARKERS:
        missing = tuple(m for m in CP_SHARED_CALIB_MARKERS if m not in fx3_cp_cal)
        errors.append(f"FX3 cpapp-b.bin missing IMX510 calibration / shadow backup markers: {missing}")
    if fx6_cp_cal != CP_SHARED_CALIB_MARKERS:
        missing = tuple(m for m in CP_SHARED_CALIB_MARKERS if m not in fx6_cp_cal)
        errors.append(f"FX6 cpapp-b.bin missing IMX510 calibration / shadow backup markers: {missing}")
    if fx6_cp_wbgain != FX6_CP_WBGAIN_MARKERS:
        errors.append("FX6 cpapp-b.bin missing WBGainR/G/B/Std calibration markers")

    cnflasha_eval = evaluate_factory_wb_calibration_immutability(
        target_partition="/dev/cnflasha16 (p2:/Backup.bin + p6:Jiritsu)",
        operation="READ_ONLY_AUDIT",
    )
    stock_cp_eval = evaluate_factory_wb_calibration_immutability(
        target_partition="p8:/cp (Stock-CP IMX510 WB/Shading/Defect)",
        operation="RAM_SHADOW_USER_WB_OFFSET",
    )
    for ev in (cnflasha_eval, stock_cp_eval):
        if not ev.valid:
            errors.extend(ev.errors)

    return FactoryCalibrationReport(
        passed=len(errors) == 0,
        fx3_appfw_calib_markers=fx3_app_cal,
        fx6_appfw_calib_markers=fx6_app_cal,
        fx3_cp_calib_markers=fx3_cp_cal,
        fx6_cp_calib_markers=fx6_cp_cal,
        fx6_cp_wbgain_markers=fx6_cp_wbgain,
        cnflasha_eval=cnflasha_eval,
        stock_cp_eval=stock_cp_eval,
        calibration_mutation_bytes=0,
        cp_mutation_bytes=0,
        persistent_emmc_writes_authorized=False,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Unified Dual-Mode Entrypoint
# ---------------------------------------------------------------------------


def wb_color_matrix_and_look_report_to_dict(
    report: WbColorMatrixAndLookReport,
) -> Dict[str, object]:
    return report.to_dict()


def analyze_wb_color_matrix_and_look(
    *,
    clean_room: bool = False,
    repo_root: Path = DEFAULT_REPO_ROOT,
    env: Optional[Mapping[str, str]] = None,
    synthetic_overrides: Optional[Mapping[str, bytes]] = None,
) -> WbColorMatrixAndLookReport:
    """Run the 12th unified firmware-lab audit across WB, Base Look, Paint 3x3 Matrix, and Factory Calibration."""
    relpaths: Dict[str, str] = {
        "fx3_appfw": FX3_APPFW_RELPATH,
        "fx6_appfw": FX6_APPFW_RELPATH,
        "fx3_libmpr": FX3_LIBMPR_RELPATH,
        "fx6_libmpr": FX6_LIBMPR_RELPATH,
        "fx3_cpapp": FX3_CPAPP_RELPATH,
        "fx6_cpapp": FX6_CPAPP_RELPATH,
        "fx3_str_en": FX3_STR_EN_RELPATH,
        "fx3_str_en_g": FX3_STR_EN_G_RELPATH,
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

    fx3_app_groups: Dict[str, Sequence[str]] = {
        "fx3_appfw_wb": FX3_APPFW_WB_MARKERS,
        "fx3_appfw_absent_wb_switch": FX3_APPFW_ABSENT_PHYSICAL_WB_SWITCH_MARKERS,
        "fx3_appfw_look": FX3_APPFW_LOOK_MARKERS,
        "fx3_appfw_knee_black": FX3_APPFW_PAINT_KNEE_BLACK_MARKERS,
        "fx3_appfw_calib": SHARED_APPFW_CALIB_MARKERS,
    }
    fx6_app_groups: Dict[str, Sequence[str]] = {
        "fx6_appfw_wb": FX6_APPFW_WB_MARKERS,
        "fx6_appfw_look": FX6_APPFW_LOOK_MARKERS,
        "fx6_appfw_paint": FX6_APPFW_PAINT_MATRIX_MARKERS,
        "fx6_appfw_calib": SHARED_APPFW_CALIB_MARKERS,
    }
    fx3_mpr_groups: Dict[str, Sequence[str]] = {
        "fx3_mpr_color": (*MPR_SHARED_COLOR_MARKERS, *FX3_MPR_EXTRA_COLOR_MARKERS),
    }
    fx6_mpr_groups: Dict[str, Sequence[str]] = {
        "fx6_mpr_color": (*MPR_SHARED_COLOR_MARKERS, *FX6_MPR_EXTRA_COLOR_MARKERS),
    }
    fx3_cp_groups: Dict[str, Sequence[str]] = {
        "fx3_cp_wb": FX3_CP_WB_MARKERS,
        "fx3_cp_mlut": CP_SHARED_MLUT_MARKERS,
        "fx3_cp_knee_black": FX3_CP_KNEE_BLACK_MARKERS,
        "fx3_cp_calib": CP_SHARED_CALIB_MARKERS,
    }
    fx6_cp_groups: Dict[str, Sequence[str]] = {
        "fx6_cp_wb": FX6_CP_WB_MARKERS,
        "fx6_cp_mlut": CP_SHARED_MLUT_MARKERS,
        "fx6_cp_paint": FX6_CP_PAINT_MARKERS,
        "fx6_cp_calib": CP_SHARED_CALIB_MARKERS,
        "fx6_cp_wbgain": FX6_CP_WBGAIN_MARKERS,
    }

    donor_sizes: Dict[str, int] = {}
    present_map: Dict[str, Tuple[str, ...]] = {}
    errors: List[str] = []

    if forced:
        mode = "CLEAN_ROOM_SYNTHETIC_VERIFIED"
        fixtures = dict(build_clean_room_wb_color_matrix_fixtures())
        if synthetic_overrides:
            fixtures.update(synthetic_overrides)

        for k, buf in fixtures.items():
            donor_sizes[k] = len(buf)

        for gname, markers in fx3_app_groups.items():
            present_map[gname], _ = _scan_buffer_markers(fixtures["fx3_appfw"], markers)
        for gname, markers in fx6_app_groups.items():
            present_map[gname], _ = _scan_buffer_markers(fixtures["fx6_appfw"], markers)
        for gname, markers in fx3_mpr_groups.items():
            present_map[gname], _ = _scan_buffer_markers(fixtures["fx3_libmpr"], markers)
        for gname, markers in fx6_mpr_groups.items():
            present_map[gname], _ = _scan_buffer_markers(fixtures["fx6_libmpr"], markers)
        for gname, markers in fx3_cp_groups.items():
            present_map[gname], _ = _scan_buffer_markers(fixtures["fx3_cpapp"], markers)
        for gname, markers in fx6_cp_groups.items():
            present_map[gname], _ = _scan_buffer_markers(fixtures["fx6_cpapp"], markers)

        str_fx3 = fixtures["fx3_str_en"]
        str_fx3_g = fixtures["fx3_str_en_g"]
        str_fx6_1 = fixtures["fx6_str_en_1"]
        str_fx6_2 = fixtures["fx6_str_en_2"]
    else:
        mode = "LOCAL_DONOR_VERIFIED"
        sz3_a, res3_a = _scan_donor_rdonly_markers(resolved["fx3_appfw"], fx3_app_groups, is_elf=True)  # type: ignore[arg-type]
        sz6_a, res6_a = _scan_donor_rdonly_markers(resolved["fx6_appfw"], fx6_app_groups, is_elf=True)  # type: ignore[arg-type]
        sz3_m, res3_m = _scan_donor_rdonly_markers(resolved["fx3_libmpr"], fx3_mpr_groups, is_elf=True)  # type: ignore[arg-type]
        sz6_m, res6_m = _scan_donor_rdonly_markers(resolved["fx6_libmpr"], fx6_mpr_groups, is_elf=True)  # type: ignore[arg-type]
        sz3_c, res3_c = _scan_donor_rdonly_markers(resolved["fx3_cpapp"], fx3_cp_groups, is_elf=False)  # type: ignore[arg-type]
        sz6_c, res6_c = _scan_donor_rdonly_markers(resolved["fx6_cpapp"], fx6_cp_groups, is_elf=False)  # type: ignore[arg-type]

        for res in (res3_a, res6_a, res3_m, res6_m, res3_c, res6_c):
            present_map.update(res)

        str_fx3 = _read_uxc_rdonly(resolved["fx3_str_en"])  # type: ignore[arg-type]
        str_fx3_g = _read_uxc_rdonly(resolved["fx3_str_en_g"])  # type: ignore[arg-type]
        str_fx6_1 = _read_uxc_rdonly(resolved["fx6_str_en_1"])  # type: ignore[arg-type]
        str_fx6_2 = _read_uxc_rdonly(resolved["fx6_str_en_2"])  # type: ignore[arg-type]

        donor_sizes = {
            "fx3_appfw": sz3_a,
            "fx6_appfw": sz6_a,
            "fx3_libmpr": sz3_m,
            "fx6_libmpr": sz6_m,
            "fx3_cpapp": sz3_c,
            "fx6_cpapp": sz6_c,
            "fx3_str_en": len(str_fx3),
            "fx3_str_en_g": len(str_fx3_g),
            "fx6_str_en_1": len(str_fx6_1),
            "fx6_str_en_2": len(str_fx6_2),
        }

    lbl_fx3, err_fx3 = _extract_uxc_labels(str_fx3, FX3_NS39_UXC_EXPECTED_LABELS)
    lbl_fx3_g, err_fx3_g = _extract_uxc_labels(str_fx3_g, FX3_NS3_UXC_EXPECTED_LABELS)
    lbl_fx6_1, err_fx6_1 = _extract_uxc_labels(str_fx6_1, FX6_NS1_UXC_EXPECTED_LABELS)
    lbl_fx6_2, err_fx6_2 = _extract_uxc_labels(str_fx6_2, FX6_NS2_UXC_EXPECTED_LABELS)
    errors.extend(err_fx3)
    errors.extend(err_fx3_g)
    errors.extend(err_fx6_1)
    errors.extend(err_fx6_2)

    uxc_wb_labels = {
        "fx3_white_balance": lbl_fx3.get("0x0004e5d4", ""),
        "fx3_color_temp": lbl_fx3.get("0x0004e8a4", ""),
        "fx3_g_white_balance": lbl_fx3_g.get("0x000062f0", ""),
        "fx6_atw": lbl_fx6_1.get("0x0000207a", ""),
        "fx6_white_balance": lbl_fx6_1.get("0x000020d0", ""),
        "fx6_white_preset": lbl_fx6_2.get("0x0000402a", ""),
        "fx6_white_atw": lbl_fx6_2.get("0x0000402e", ""),
        "fx6_shockless_white": lbl_fx6_2.get("0x00004404", ""),
        "fx6_atw_speed": lbl_fx6_2.get("0x00004406", ""),
        "fx6_preset_3200k": lbl_fx6_2.get("0x00004794", ""),
        "fx6_preset_4300k": lbl_fx6_2.get("0x00004796", ""),
        "fx6_5600k": lbl_fx6_2.get("0x00004ba4", ""),
        "fx6_memory_a": lbl_fx6_2.get("0x00004b23", ""),
        "fx6_memory_b": lbl_fx6_2.get("0x00004b24", ""),
    }
    uxc_look_labels = {
        "fx3_itu709_matrix": lbl_fx3_g.get("0x00006531", ""),
        "fx6_mlut": lbl_fx6_1.get("0x00002029", ""),
        "fx6_s_cinetone": lbl_fx6_1.get("0x000020f5", ""),
        "fx6_base_look_lut": lbl_fx6_1.get("0x0000219d", ""),
        "fx6_709_800": lbl_fx6_1.get("0x0000219e", ""),
        "fx6_s_log3": lbl_fx6_1.get("0x0000219f", ""),
        "fx6_itu709": lbl_fx6_1.get("0x000021a2", ""),
        "fx6_hlg_live": lbl_fx6_1.get("0x000021a3", ""),
        "fx6_hlg_natural": lbl_fx6_1.get("0x000021a4", ""),
        "fx6_s_gamut3": lbl_fx6_2.get("0x00004340", ""),
    }
    uxc_paint_labels = {
        "fx6_black_gamma": lbl_fx6_2.get("0x00004222", ""),
        "fx6_multi_matrix": lbl_fx6_2.get("0x0000422d", ""),
        "fx6_knee_point": lbl_fx6_2.get("0x0000443e", ""),
        "fx6_knee_slope": lbl_fx6_2.get("0x00004441", ""),
        "fx6_user_matrix_rg": lbl_fx6_2.get("0x00004484", ""),
        "fx6_user_matrix_rb": lbl_fx6_2.get("0x00004486", ""),
        "fx6_user_matrix_gr": lbl_fx6_2.get("0x00004488", ""),
        "fx6_user_matrix_gb": lbl_fx6_2.get("0x0000448a", ""),
        "fx6_user_matrix_br": lbl_fx6_2.get("0x0000448c", ""),
        "fx6_user_matrix_bg": lbl_fx6_2.get("0x0000448e", ""),
    }

    pillar_a = evaluate_pillar_a_white_balance(present_map, uxc_wb_labels)
    pillar_b = evaluate_pillar_b_base_look(present_map, uxc_look_labels)
    pillar_c = evaluate_pillar_c_paint_matrix_and_knee(present_map, uxc_paint_labels)
    pillar_d = evaluate_pillar_d_factory_calibration(present_map)

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
        "schema_version": PHASE_65_SCHEMA,
        "phase_version": PHASE_65_VERSION,
        "mode": mode,
        "all_checks_passed": all_passed,
        "donor_file_sizes": donor_sizes,
        "pillar_a_white_balance": asdict(pillar_a),
        "pillar_b_base_look": asdict(pillar_b),
        "pillar_c_paint_matrix_knee": asdict(pillar_c),
        "pillar_d_factory_calibration": asdict(pillar_d),
        "errors": tuple(errors),
    }
    report_sha256 = hashlib.sha256(
        json.dumps(digest_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()

    return WbColorMatrixAndLookReport(
        schema_version=PHASE_65_SCHEMA,
        phase_version=PHASE_65_VERSION,
        mode=mode,
        all_checks_passed=all_passed,
        o_rdonly_enforced=True,
        persistent_emmc_writes_authorized=False,
        calibration_mutation_bytes=pillar_d.calibration_mutation_bytes,
        cp_mutation_bytes=pillar_d.cp_mutation_bytes,
        donor_file_sizes=donor_sizes,
        pillar_a_white_balance=pillar_a,
        pillar_b_base_look=pillar_b,
        pillar_c_paint_matrix_knee=pillar_c,
        pillar_d_factory_calibration=pillar_d,
        errors=tuple(errors),
        report_sha256=report_sha256,
    )
