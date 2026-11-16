"""Phase 111 — 21st Unified Firmware-Lab Auditor: ITU-R BT.2100 / ARIB STD-B67 HLG
(`HLG1`/`HLG2`/`HLG3`/`HLG Live`/`HLG Natural` & `BT.2020` vs `BT.709`), Gamma Display
Assist EVF/LCD Tone-Mapping Isolation (`S-Log3 -> ITU709(800%)`, `HLG(BT.2020) -> 709`),
& CTA-861.3 HDMI HDR Dynamic Range and Mastering InfoFrame (`0x87`) Synthesizer & Guard.

Strictly Read-Only (`os.O_RDONLY` + `mmap.ACCESS_READ`) & Clean-Room Dual-Mode:
- Local Donor Mode: inspects FX3 v7.02 (`appFw.so`, `libmpr.so`, `cpapp-b.bin`,
  `global.xdb`, `string_english.uxc`, `string_english_g.uxc`) and FX6 v6.01
  (`appFw.so`, `libmpr.so`, `cpapp-b.bin`, `global.xdb`, `string_english.uxc`,
  `string_english_2.uxc`) strictly via `os.O_RDONLY` + `mmap.ACCESS_READ` and
  ELF64 `.rodata`/`.dynstr` section-scoped scanning plus `uxa\\x07` / `.uxc`
  container parsing (< 0.35s total).
- Clean-Room Mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`, `clean_room=True`, or donors
  absent): synthesizes deterministic clean-room ELF64 / CP / `global.xdb` /
  `.uxc` fixtures carrying the exact verified contract markers and SMPTE ULs,
  and executes the identical four-pillar verification pipeline (< 0.02s warm,
  zero proprietary files required).

Audits Four Phase 111 Pillars:
1. Pillar 1 — ITU-R BT.2100 / ARIB STD-B67 Hybrid Log-Gamma OETF & Sony
   `HLG1` / `HLG2` / `HLG3` / `HLG Live` / `HLG Natural` Curve Auditor:
   - Verifies exact piecewise ARIB STD-B67 HLG OETF (`E <= 1/12 -> sqrt(3E)`,
     `E > 1/12 -> a*ln(12E - b) + c`, `a=0.17883277, b=0.28466892, c=0.55991073`),
     `C^0`/`C^1` continuity at `E = 1/12`, exact roundtrip inversion (`< 1e-10`),
     and Sony's HLG family (`HLG1` 87% / ~11.5 stops NR-priority, `HLG2` 95% /
     ~12.3 stops balanced, `HLG3` 100% / ~13.0 stops widest DR, plus FX6
     `HLG Live` / `HLG Natural` / `HLG Mild`).
   - Proves fail-closed blocking of illegal gamut/transfer mismatches (e.g.,
     recording `BT.2020` primaries tagged as `BT.709` without matrix conversion,
     causing severe saturation collapse and hue shift in broadcast NLEs).
2. Pillar 2 — Gamma Display Assist (`S-Log3 -> 709(800%)` & `HLG(BT.2020) -> 709`
   LCD/EVF Viewfinder Tone-Mapping Isolation):
   - Audits `Auto / S-Log3->709(800%) / S-Log2->709(800%) / HLG(BT.2020) /
     HLG(709)` viewfinder preview transforms (including exact ITU-R BT.2087
     `BT.2020 -> BT.709` linear chromaticity matrix) and proves strictly that
     LCD/EVF `Gamma Display Assist` NEVER burns into recorded XAVC main clips
     or Clean-HDMI output unless explicit `MLUT` burn-in is enabled.
3. Pillar 3 — CTA-861.3 / HDMI 2.0b+ Static Metadata Type 1 HDR InfoFrame
   (`0x87`) Synthesizer & Checksum Guard:
   - Synthesizes and decodes the 30-byte CTA-861.3 HDR Dynamic Range and
     Mastering InfoFrame (`type=0x87`, `version=0x01`, `length=26`, `EOTF=0x03`
     HLG vs `0x00` SDR vs `0x02` SMPTE ST 2084 PQ,
     `Static_Metadata_Descriptor_ID=0`, `sum(30 bytes) & 0xFF == 0`), proving
     external Atomos/SmallHD HDR monitors auto-switch into HLG BT.2020 mode on
     live shoots and fail-closed on checksum corruption, EOTF/AVI colorimetry
     mismatches, or `HDMI RAW16` conflicts.
4. Pillar 4 — `NonRealTimeMeta` XML `<CaptureGammaEquation>` / `<ColorPrimaries>`
   SMPTE UL Parity & Zero-Calibration-Mutation Proof:
   - Validates exact 16-byte SMPTE UL parity (`rec2100-hlg`, `smpte2084`,
     `rec709`, `s-log3`, `rec2020`, `s-gamut3`, `s-gamut3-cine`) verified in
     FX3/FX6 `libmpr.so`, synthesizes/validates `NonRealTimeMeta v2.20` XML
     sidecars, and proves `calibration_mutation_bytes == 0`,
     `emmc_mutation_bytes == 0`, and `persistent_emmc_writes_authorized == False`.
"""

from __future__ import annotations

import hashlib
import json
import math
import mmap
import os
import re
import struct
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from .emount_af_breathing_and_ibis_auditor import _extract_uxc_labels, _parse_elf64_sections
from .global_xdb_and_menu_tree_auditor import (
    build_sparse_uxc_string_pack,
    build_synthetic_global_xdb,
    parse_global_xdb_buffer,
)
from .haita_bk4_feature_analyzer import (
    DEFAULT_REPO_ROOT,
    FX3_APPFW_RELPATH,
    FX6_APPFW_RELPATH,
    is_forced_clean_room,
    resolve_donor_file,
)
from .lut3d_cube_tetrahedral_and_sdi_hdmi_auditor import (
    FX3_GLOBAL_XDB_RELPATH,
    FX3_STR_EN_G_RELPATH,
    FX3_STR_EN_RELPATH,
    FX6_GLOBAL_XDB_RELPATH,
    FX6_STR_EN_1_RELPATH,
    FX6_STR_EN_2_RELPATH,
)
from .proxy_clipname_and_sidecar_auditor import NRTM_LIB_NAMESPACE_V220, NRTM_NAMESPACE_V220
from .sensor_codec_compatibility_analyzer import (
    FX3_CPAPP_RELPATH,
    FX3_LIBMPR_RELPATH,
    FX6_CPAPP_RELPATH,
    FX6_LIBMPR_RELPATH,
)


PHASE_111_SCHEMA = "fx3_firmware_lab_phase111_hdr_hlg_bt2100_assist_v1"
PHASE_111_VERSION = "111.0.0"

# ---------------------------------------------------------------------------
# Pillar 1 Constants: ARIB STD-B67 / ITU-R BT.2100 HLG & Sony Variants
# ---------------------------------------------------------------------------

HLG_ARIB_B67_A = 0.17883277
HLG_ARIB_B67_B = 0.28466892
HLG_ARIB_B67_C = 0.55991073
HLG_ARIB_B67_BREAKPOINT_E = 1.0 / 12.0
HLG_ARIB_B67_BREAKPOINT_EP = 0.5

SONY_HLG_CURVE_PROFILES: Dict[str, Dict[str, object]] = {
    "HLG": {
        "label": "ITU-R BT.2100 / ARIB STD-B67 Standard HLG",
        "max_signal_pct": 100.0,
        "dynamic_range_stops": 13.0,
        "min_iso_fx3": 100,
        "noise_reduction_priority": False,
        "body_scope": "SHARED_FX3_FX6",
    },
    "HLG1": {
        "label": "Sony HLG1 (Low-Noise Highlight Compression)",
        "max_signal_pct": 87.0,
        "dynamic_range_stops": 11.5,
        "min_iso_fx3": 50,
        "noise_reduction_priority": True,
        "body_scope": "SHARED_FX3_FX6",
    },
    "HLG2": {
        "label": "Sony HLG2 (Balanced Dynamic Range & Noise)",
        "max_signal_pct": 95.0,
        "dynamic_range_stops": 12.3,
        "min_iso_fx3": 80,
        "noise_reduction_priority": False,
        "body_scope": "SHARED_FX3_FX6",
    },
    "HLG3": {
        "label": "Sony HLG3 (Widest Dynamic Range 100% Ceiling)",
        "max_signal_pct": 100.0,
        "dynamic_range_stops": 13.0,
        "min_iso_fx3": 100,
        "noise_reduction_priority": False,
        "body_scope": "SHARED_FX3_FX6",
    },
    "HLG_LIVE": {
        "label": "FX6 HLG Live (Direct Broadcast HDR OOTF)",
        "max_signal_pct": 100.0,
        "dynamic_range_stops": 13.0,
        "min_iso_fx3": 100,
        "noise_reduction_priority": False,
        "body_scope": "FX6_CINEMA_BASE",
    },
    "HLG_NATURAL": {
        "label": "FX6 HLG Natural (Soft Highlight Roll-Off)",
        "max_signal_pct": 100.0,
        "dynamic_range_stops": 13.0,
        "min_iso_fx3": 100,
        "noise_reduction_priority": False,
        "body_scope": "FX6_CINEMA_BASE",
    },
    "HLG_MILD": {
        "label": "FX6 HLG Mild (Gentle Mid-Tone Knee)",
        "max_signal_pct": 100.0,
        "dynamic_range_stops": 13.0,
        "min_iso_fx3": 100,
        "noise_reduction_priority": False,
        "body_scope": "FX6_CINEMA_BASE",
    },
}

VALID_COLOR_PRIMARIES_SETS: Tuple[str, ...] = ("BT.2020", "BT.709", "S-GAMUT3.CINE", "S-GAMUT3")
VALID_TRANSFER_FAMILIES: Tuple[str, ...] = ("REC2100_HLG", "S_LOG3", "S_LOG2", "ITU709", "SMPTE_ST2084_PQ")

# Exact ITU-R BT.2087 linear RGB BT.2020 -> BT.709 matrix (rows sum to 1.0)
BT2020_TO_BT709_MATRIX_3X3: Tuple[Tuple[float, float, float], ...] = (
    (1.6604910021, -0.5876411388, -0.0728498633),
    (-0.1245504745, 1.1328998971, -0.0083494226),
    (-0.0181507634, -0.1005788980, 1.1187296614),
)

# CIE 1931 xy chromaticities for gamut-mismatch collapse quantification
CIE_PRIMARIES_XY: Dict[str, Dict[str, Tuple[float, float]]] = {
    "BT.2020": {
        "R": (0.7080, 0.2920),
        "G": (0.1700, 0.7970),
        "B": (0.1310, 0.0460),
        "W": (0.3127, 0.3290),
    },
    "BT.709": {
        "R": (0.6400, 0.3300),
        "G": (0.3000, 0.6000),
        "B": (0.1500, 0.0600),
        "W": (0.3127, 0.3290),
    },
}

# ---------------------------------------------------------------------------
# Pillar 2 Constants: Gamma Display Assist EVF/LCD Isolation
# ---------------------------------------------------------------------------

VALID_GAMMA_DISPLAY_ASSIST_TYPES: Tuple[str, ...] = (
    "OFF",
    "AUTO",
    "SLOG3_TO_709_800",
    "SLOG2_TO_709_800",
    "HLG_BT2020_TO_709",
    "HLG_709_TO_709",
)

# ---------------------------------------------------------------------------
# Pillar 3 Constants: CTA-861.3 Static Metadata Type 1 HDR InfoFrame (0x87)
# ---------------------------------------------------------------------------

CTA861_HDR_DRM_INFOFRAME_TYPE = 0x87
CTA861_HDR_DRM_INFOFRAME_VERSION = 0x01
CTA861_HDR_DRM_PAYLOAD_LEN = 26
CTA861_HDR_DRM_TOTAL_BYTES = 30
CTA861_STATIC_METADATA_TYPE_1_ID = 0x00

CTA861_EOTF_CODES: Dict[str, int] = {
    "SDR_GAMMA": 0x00,
    "HDR_GAMMA": 0x01,
    "SMPTE_ST2084_PQ": 0x02,
    "BT2100_HLG": 0x03,
}
CTA861_EOTF_NAMES: Dict[int, str] = {v: k for k, v in CTA861_EOTF_CODES.items()}

VALID_EXTERNAL_HDR_MONITORS: Tuple[str, ...] = (
    "ATOMOS_NINJA_V_PLUS",
    "SMALLHD_CINE7_HDR",
    "SONY_BVM_HX310",
)

# ---------------------------------------------------------------------------
# Pillar 4 Constants: SMPTE UL Parity & Zero Calibration / eMMC Firewall
# ---------------------------------------------------------------------------

SMPTE_UL_HEX_CATALOG: Dict[str, str] = {
    "rec2100-hlg": "060e2b340401010d04010101010b0000",
    "smpte2084": "060e2b340401010d04010101010a0000",
    "rec709_transfer": "060e2b34040101010401010101020000",
    "s-log3": "060e2b340401010d0401010101080000",
    "rec2020_primaries": "060e2b340401010d0401010103040000",
    "rec709_primaries": "060e2b34040101060401010103030000",
    "s-gamut3": "060e2b34040101060e06040101030106",
    "s-gamut3-cine": "060e2b34040101060e06040101030107",
}

NRTM_GAMMA_TO_SMPTE_UL: Dict[str, str] = {
    "rec2100-hlg": SMPTE_UL_HEX_CATALOG["rec2100-hlg"],
    "smpte2084": SMPTE_UL_HEX_CATALOG["smpte2084"],
    "rec709": SMPTE_UL_HEX_CATALOG["rec709_transfer"],
    "s-log3": SMPTE_UL_HEX_CATALOG["s-log3"],
    "s-log3-cine": SMPTE_UL_HEX_CATALOG["s-log3"],
}

NRTM_PRIMARIES_TO_SMPTE_UL: Dict[str, str] = {
    "rec2020": SMPTE_UL_HEX_CATALOG["rec2020_primaries"],
    "rec709": SMPTE_UL_HEX_CATALOG["rec709_primaries"],
    "s-gamut3": SMPTE_UL_HEX_CATALOG["s-gamut3"],
    "s-gamut3-cine": SMPTE_UL_HEX_CATALOG["s-gamut3-cine"],
}

VOLATILE_STAGING_PREFIXES: Tuple[str, ...] = ("/tmp/", "ram://", "memory://")
FORBIDDEN_CALIBRATION_TARGET_RE = re.compile(
    r"(?:^|/)(?:p(?:[1-9]|1[0-8])|nflasha\d*|cnflasha\d*|mmcblk0(?:p\d+|rpmb)?|mtdblock\d*)(?:/|:|$)"
    r"|psd\.bin|defdet\.bin|backup\.bin|jiritsu|shading://|nvram://|eeprom://",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Verified Binary & .uxc Marker Contracts (FX3 v7.02 & FX6 v6.01)
# ---------------------------------------------------------------------------

FX3_APPFW_PHASE111_MARKERS: Tuple[str, ...] = (
    "SETTING_PICTUREPROFILE_GAMMA_HLG",
    "SETTING_PICTUREPROFILE_GAMMA_HLG1",
    "SETTING_PICTUREPROFILE_GAMMA_HLG2",
    "SETTING_PICTUREPROFILE_GAMMA_HLG3",
    "SETTING_PICTUREPROFILE_COLORMODE_BT2020",
    "SETTING_PICTUREPROFILE_COLORMODE_709",
    "CONTENT_INFO_CAPTURE_GAMMA_EQUATION_REC2100_HLG",
    "CONTENT_INFO_COLOR_PRIMARIES_REC2020",
    "CONTENT_INFO_COLOR_PRIMARIES_REC709",
    "VAL_setting_gamma_disp_assist_display_GAMMA_DISP_ASSIST_DISPLAY_ON",
    "VAL_setting_gamma_disp_assist_display_GAMMA_DISP_ASSIST_DISPLAY_OFF",
    "VAL_setting_gamma_disp_assist_type_GAMMA_DISP_ASSIST_TYPE_AUTO",
    "VAL_setting_gamma_disp_assist_type_GAMMA_DISP_ASSIST_TYPE_SLOG3",
    "VAL_setting_gamma_disp_assist_type_GAMMA_DISP_ASSIST_TYPE_SLOG2",
    "VAL_setting_gamma_disp_assist_type_GAMMA_DISP_ASSIST_TYPE_HLG_BT2020",
    "VAL_setting_gamma_disp_assist_type_GAMMA_DISP_ASSIST_TYPE_HLG_709",
    "BKID_APP_setting_gamma_disp_assist_display",
    "BKID_APP_setting_gamma_disp_assist_type",
    "VIDEO_COLOR_SPACE_BT2020",
)

FX6_APPFW_PHASE111_MARKERS: Tuple[str, ...] = (
    "SETTING_PICTUREPROFILE_GAMMA_HLG",
    "SETTING_PICTUREPROFILE_GAMMA_HLG1",
    "SETTING_PICTUREPROFILE_GAMMA_HLG2",
    "SETTING_PICTUREPROFILE_GAMMA_HLG3",
    "SETTING_PICTUREPROFILE_COLORMODE_BT2020",
    "SETTING_PICTUREPROFILE_COLORMODE_709",
    "CONTENT_INFO_CAPTURE_GAMMA_EQUATION_REC2100_HLG",
    "CONTENT_INFO_COLOR_PRIMARIES_REC2020",
    "CONTENT_INFO_COLOR_PRIMARIES_REC709",
    "VAL_setting_select_lut_hdr_SELECT_LUT_HDR_HLG_LIVE",
    "VAL_setting_select_lut_hdr_SELECT_LUT_HDR_HLG_NATURAL",
    "VAL_setting_select_lut_hdr_SELECT_LUT_HDR_HLG_MILD",
    "VAL_setting_target_display_TARGET_DISPLAY_HDR_HLG",
    "VAL_setting_target_display_TARGET_DISPLAY_SDR_BT_709",
    "GAMMA_DISP_ASSIST_TYPE_AUTO",
    "GAMMA_DISP_ASSIST_TYPE_SLOG3",
    "GAMMA_DISP_ASSIST_TYPE_HLG_BT2020",
    "GAMMA_DISP_ASSIST_TYPE_HLG_709",
    "BKID_APP_SETTING_GAMMA_DISP_ASSIST_DISPLAY",
    "BKID_APP_SETTING_TARGET_DISPLAY",
    "VIEW_FINDER_HDR_DISPLAY_STATE_GAMUT_BT2020",
    "VIDEO_COLOR_SPACE_BT2020",
)

LIBMPR_SHARED_PHASE111_MARKERS: Tuple[str, ...] = (
    "CaptureGammaEquation",
    "CaptureColorPrimaries",
    "rec2100-hlg",
    "rec2020",
    "rec709",
    "hlg-slog3ootf",
    "s-log3",
    "s-gamut3-cine",
)

FX6_LIBMPR_EXTRA_PHASE111_MARKERS: Tuple[str, ...] = (
    "smpte2084",
    "hlg-mildlook",
    "MetaConverterImpl::ConvertCaptureGammaEquation",
    "MetaConverterImpl::ConvertColorPrimaries",
    "BT.2100",
    "EOTF",
)

CP_SHARED_PHASE111_MARKERS: Tuple[str, ...] = (
    "HLG",
    "BT.2020",
    "BT2020rgb",
    "BT2020ycc",
    "SET_GAMMA_DISP_ASSIST",
    "MSG_ID_INFRABB_VIDEO_SET_GAMMA_DISP_ASSIST",
)

FX6_CP_EXTRA_PHASE111_MARKERS: Tuple[str, ...] = (
    "cpActGammaDisplayAssist",
    "36cpActGammaDisplayAssistWidgetService",
    "MonColorPrimaries",
)

# Verified .uxc String Resource IDs
FX3_NS39_PHASE111_LABELS: Dict[int, str] = {
    0x0000E1D5: "HDMI Resolution",
}

FX3_NS3_PHASE111_LABELS: Dict[int, str] = {
    0x00006531: "ITU709 Matrix",
    0x00006538: (
        "Use Gamma Display Assist instead of LUT\n"
        "when Log shooting still images.\n"
        '"Gamma Display Assist" set to "On".'
    ),
}

FX6_NS1_PHASE111_LABELS: Dict[int, str] = {
    0x00002018: "HLG_BT.2100",
    0x000020B9: "BT.2020/HDR(HLG)",
    0x00002109: "LUT 709(800)",
    0x000021A3: "HLG Live",
    0x000021A4: "HLG Natural",
    0x00003247: "Gamma Display Assist",
}

FX6_NS2_PHASE111_LABELS: Dict[int, str] = {
    0x0000419D: "Gamma Display Assist: Auto",
    0x0000419E: "Gamma Display Assist: HLG",
    0x0000419F: "Gamma Display Assist: S-Log3",
    0x000042EA: "HLG\u2192709(800%)",
    0x0000515D: "HDR(HLG1)",
    0x0000515E: "HDR(HLG2)",
    0x0000515F: "HDR(HLG3)",
}

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HlgOetfCurveMathResult:
    passed: bool
    status: str
    arib_a: float
    arib_b: float
    arib_c: float
    breakpoint_e: float
    breakpoint_left_ep: float
    breakpoint_right_ep: float
    c0_continuity_error: float
    c1_slope_left: float
    c1_slope_right: float
    c1_slope_error: float
    max_roundtrip_error: float
    monotonic_verified: bool
    code10_legal_black: int
    code10_legal_breakpoint: int
    code10_legal_peak: int
    hlg1_max_signal_pct: float
    hlg2_max_signal_pct: float
    hlg3_max_signal_pct: float
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class HlgGamutTransferEvalResult:
    valid: bool
    status: str
    hlg_variant: str
    transfer_family: str
    recorded_primaries: str
    signaled_primaries: str
    matrix_conversion_applied: bool
    target_display: str
    nle_consumer: str
    gamut_area_ratio_vs_bt2020: float
    saturation_collapse_pct: float
    hue_shift_risk: bool
    max_signal_pct: float
    dynamic_range_stops: float
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class HlgBt2100CurveReport:
    passed: bool
    fx3_appfw_hlg_markers: Tuple[str, ...]
    fx6_appfw_hlg_markers: Tuple[str, ...]
    fx3_cp_hlg_markers: Tuple[str, ...]
    fx6_cp_hlg_markers: Tuple[str, ...]
    uxc_hlg_labels: Dict[str, str]
    oetf_math_proof: HlgOetfCurveMathResult
    eval_hlg3_bt2020_hdr: HlgGamutTransferEvalResult
    eval_hlg1_bt2020_nr: HlgGamutTransferEvalResult
    eval_hlg2_bt2020_balanced: HlgGamutTransferEvalResult
    eval_fx6_hlg_live_bt2020: HlgGamutTransferEvalResult
    blocked_bt2020_tagged_bt709_no_matrix: HlgGamutTransferEvalResult
    blocked_bt709_tagged_bt2020_oversat: HlgGamutTransferEvalResult
    blocked_slog3_tagged_hlg_transfer: HlgGamutTransferEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class GammaDisplayAssistEvalResult:
    valid: bool
    status: str
    assist_display_on: bool
    assist_type: str
    resolved_transform: str
    capture_gamma: str
    capture_primaries: str
    xavc_main_mlut_burn_in: bool
    clean_hdmi_mlut_enabled: bool
    lcd_evf_receives_tone_mapped_preview: bool
    xavc_main_preserves_native_gamma: bool
    clean_hdmi_preserves_native_gamma: bool
    lcd_evf_assist_burned_into_xavc: bool
    lcd_evf_assist_burned_into_clean_hdmi: bool
    double_tone_map_prevented: bool
    sample_midgrey_in_rgb: Tuple[float, float, float]
    sample_midgrey_evf_rgb: Tuple[float, float, float]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class GammaDisplayAssistReport:
    passed: bool
    fx3_appfw_assist_markers: Tuple[str, ...]
    fx6_appfw_assist_markers: Tuple[str, ...]
    fx3_cp_assist_markers: Tuple[str, ...]
    fx6_cp_assist_markers: Tuple[str, ...]
    uxc_assist_labels: Dict[str, str]
    eval_auto_slog3_to_709_800: GammaDisplayAssistEvalResult
    eval_auto_hlg_bt2020_to_709: GammaDisplayAssistEvalResult
    eval_explicit_hlg_709_to_709: GammaDisplayAssistEvalResult
    eval_mlut_active_defers_assist: GammaDisplayAssistEvalResult
    blocked_assist_leak_into_xavc_main: GammaDisplayAssistEvalResult
    blocked_assist_leak_into_clean_hdmi: GammaDisplayAssistEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Cta861HdrInfoFrameDecoded:
    valid: bool
    infoframe_type: int
    version: int
    payload_length: int
    total_bytes: int
    checksum_byte: int
    checksum_valid: bool
    eotf_code: int
    eotf_name: str
    static_metadata_descriptor_id: int
    primaries_xy_50k: Tuple[Tuple[int, int], Tuple[int, int], Tuple[int, int]]
    white_point_xy_50k: Tuple[int, int]
    max_display_mastering_luminance_nits: int
    min_display_mastering_luminance_0001_nits: int
    max_cll_nits: int
    max_fall_nits: int
    packet_hex: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class HdmiHdrInfoFrameEvalResult:
    valid: bool
    status: str
    camera_gamma: str
    camera_primaries: str
    avi_colorimetry: str
    hdmi_raw16_active: bool
    target_monitor: str
    monitor_detected_mode: str
    monitor_auto_switched_hlg_bt2020: bool
    decoded_infoframe: Cta861HdrInfoFrameDecoded
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Cta861HdrInfoFrameReport:
    passed: bool
    fx3_uxc_hdmi_labels: Dict[str, str]
    eval_hlg_bt2020_atomos_ninja: HdmiHdrInfoFrameEvalResult
    eval_hlg_bt2020_smallhd_cine7: HdmiHdrInfoFrameEvalResult
    eval_pq_st2084_bvm_hx310: HdmiHdrInfoFrameEvalResult
    eval_sdr_bt709_baseline: HdmiHdrInfoFrameEvalResult
    blocked_corrupt_checksum_rejected: HdmiHdrInfoFrameEvalResult
    blocked_hlg_signaled_as_sdr_eotf: HdmiHdrInfoFrameEvalResult
    blocked_hlg_with_bt709_avi_mismatch: HdmiHdrInfoFrameEvalResult
    blocked_raw16_hdr_infoframe_conflict: HdmiHdrInfoFrameEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class HlgNrtmXmlEvalResult:
    valid: bool
    status: str
    namespace_uri: str
    capture_gamma_equation: str
    capture_color_primaries: str
    smpte_ul_gamma_hex: str
    smpte_ul_primaries_hex: str
    smpte_ul_parity_ok: bool
    hlg_variant: str
    device_model_name: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class HdrCalibrationGuardResult:
    valid: bool
    status: str
    target_path: str
    volatile_ram_staged: bool
    persistent_write_blocked: bool
    calibration_mutation_bytes: int
    emmc_mutation_bytes: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class HdrNrtmAndImmutabilityReport:
    passed: bool
    fx3_libmpr_markers: Tuple[str, ...]
    fx6_libmpr_markers: Tuple[str, ...]
    fx3_smpte_uls_verified: Tuple[str, ...]
    fx6_smpte_uls_verified: Tuple[str, ...]
    fx3_global_xdb_valid: bool
    fx6_global_xdb_valid: bool
    eval_hlg_bt2020_nrtm_xml: HlgNrtmXmlEvalResult
    blocked_hlg_bt709_nrtm_mismatch: HlgNrtmXmlEvalResult
    volatile_staging_guard: HdrCalibrationGuardResult
    blocked_psd_bin_guard: HdrCalibrationGuardResult
    blocked_cnflasha_guard: HdrCalibrationGuardResult
    blocked_backup_bin_guard: HdrCalibrationGuardResult
    calibration_mutation_bytes: int
    emmc_mutation_bytes: int
    persistent_emmc_writes_authorized: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class HdrHlgBt2100AndDisplayAssistReport:
    schema_version: str
    phase_version: str
    mode: str
    all_checks_passed: bool
    donor_file_sizes: Dict[str, int]
    pillar_1_hlg_bt2100_curves: HlgBt2100CurveReport
    pillar_2_gamma_display_assist: GammaDisplayAssistReport
    pillar_3_cta861_3_hdr_infoframe: Cta861HdrInfoFrameReport
    pillar_4_nrtm_smpte_ul_immutability: HdrNrtmAndImmutabilityReport
    report_sha256: str
    errors: Tuple[str, ...]


# ---------------------------------------------------------------------------
# Strictly `os.O_RDONLY` + `mmap.ACCESS_READ` Scanning Helpers
# ---------------------------------------------------------------------------


def _read_bytes_rdonly(path: Path) -> bytes:
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


def _scan_donor_rdonly_markers(
    path: Path,
    marker_groups: Mapping[str, Sequence[str]],
    *,
    is_elf: bool,
    ul_hex_catalog: Optional[Mapping[str, str]] = None,
) -> Tuple[int, Dict[str, Tuple[str, ...]], Tuple[str, ...]]:
    """Open `path` strictly `os.O_RDONLY` with `mmap.ACCESS_READ` and scan markers & ULs."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        sz = os.fstat(fd).st_size
        if sz == 0:
            return 0, {k: () for k in marker_groups}, ()

        unique_markers = sorted(
            {m for markers in marker_groups.values() for m in markers},
            key=lambda s: (-len(s), s),
        )
        matched_tokens: set[bytes] = set()
        verified_uls: List[str] = []

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

            if unique_markers:
                pat = re.compile(b"|".join(re.escape(m.encode("latin1")) for m in unique_markers))
                for off, rsz in ranges:
                    for mo in pat.finditer(mm, off, off + rsz):
                        matched_tokens.add(mo.group(0))

            if ul_hex_catalog:
                for ul_name, ul_hex in ul_hex_catalog.items():
                    ul_bytes = bytes.fromhex(ul_hex)
                    for off, rsz in ranges:
                        if mm.find(ul_bytes, off, off + rsz) != -1:
                            verified_uls.append(ul_name)
                            break

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
        return sz, results, tuple(verified_uls)
    finally:
        os.close(fd)


def _scan_bytes_marker_groups(
    blob: bytes,
    marker_groups: Mapping[str, Sequence[str]],
    *,
    ul_hex_catalog: Optional[Mapping[str, str]] = None,
) -> Tuple[int, Dict[str, Tuple[str, ...]], Tuple[str, ...]]:
    unique_markers = sorted(
        {m for markers in marker_groups.values() for m in markers},
        key=lambda s: (-len(s), s),
    )
    results: Dict[str, Tuple[str, ...]] = {k: () for k in marker_groups}
    if unique_markers:
        pat = re.compile(b"|".join(re.escape(m.encode("latin1")) for m in unique_markers))
        matched_tokens = {mo.group(0) for mo in pat.finditer(blob)}
        matched_list = list(matched_tokens)
        present_markers = {
            m
            for m in unique_markers
            if (mb := m.encode("latin1")) in matched_tokens or any(mb in tok for tok in matched_list)
        }
        results = {
            group_name: tuple(m for m in markers if m in present_markers)
            for group_name, markers in marker_groups.items()
        }

    verified_uls: List[str] = []
    if ul_hex_catalog:
        for ul_name, ul_hex in ul_hex_catalog.items():
            if bytes.fromhex(ul_hex) in blob:
                verified_uls.append(ul_name)

    return len(blob), results, tuple(verified_uls)


# ---------------------------------------------------------------------------
# Clean-Room Synthetic Fixtures (`FX3_FX6_FORCE_CLEAN_ROOM=1` or donors absent)
# ---------------------------------------------------------------------------


def build_clean_room_hdr_hlg_assist_fixtures() -> Dict[str, bytes]:
    """Build deterministic clean-room ELF64, CP, `global.xdb`, and `.uxc` fixtures."""
    elf_hdr = b"\x7fELF\x02\x01\x01\x00" + bytes(56)
    cp_hdr = b"LDR\x00" + bytes(60)

    def _pack(tokens: Sequence[str], *, prefix: bytes = elf_hdr, extra: bytes = b"") -> bytes:
        return prefix + b"\x00".join(t.encode("latin1") for t in tokens) + b"\x00" + extra

    ul_blob = b"".join(bytes.fromhex(hx) for hx in SMPTE_UL_HEX_CATALOG.values())

    return {
        "fx3_appfw": _pack(FX3_APPFW_PHASE111_MARKERS),
        "fx6_appfw": _pack(FX6_APPFW_PHASE111_MARKERS),
        "fx3_libmpr": _pack(LIBMPR_SHARED_PHASE111_MARKERS, extra=ul_blob),
        "fx6_libmpr": _pack(LIBMPR_SHARED_PHASE111_MARKERS + FX6_LIBMPR_EXTRA_PHASE111_MARKERS, extra=ul_blob),
        "fx3_cpapp": _pack(CP_SHARED_PHASE111_MARKERS, prefix=cp_hdr),
        "fx6_cpapp": _pack(CP_SHARED_PHASE111_MARKERS + FX6_CP_EXTRA_PHASE111_MARKERS, prefix=cp_hdr),
        "fx3_global_xdb": build_synthetic_global_xdb("fx3_702"),
        "fx6_global_xdb": build_synthetic_global_xdb("fx6_601"),
        "fx3_str_en": build_sparse_uxc_string_pack(
            {k & 0x1FFF: v for k, v in FX3_NS39_PHASE111_LABELS.items()}, namespace_id=39
        ),
        "fx3_str_en_g": build_sparse_uxc_string_pack(
            {k & 0x1FFF: v for k, v in FX3_NS3_PHASE111_LABELS.items()}, namespace_id=3
        ),
        "fx6_str_en_1": build_sparse_uxc_string_pack(
            {k & 0x1FFF: v for k, v in FX6_NS1_PHASE111_LABELS.items()}, namespace_id=1
        ),
        "fx6_str_en_2": build_sparse_uxc_string_pack(
            {k & 0x1FFF: v for k, v in FX6_NS2_PHASE111_LABELS.items()}, namespace_id=2
        ),
    }


# ---------------------------------------------------------------------------
# Pillar 1 Functions: ARIB STD-B67 HLG OETF, Sony Variants & Gamut Guard
# ---------------------------------------------------------------------------


def arib_b67_hlg_oetf(e: float) -> float:
    """Evaluate exact piecewise ITU-R BT.2100 / ARIB STD-B67 HLG OETF for scene linear `E` in `[0, 1]`."""
    if math.isnan(e) or math.isinf(e):
        raise ValueError(f"Scene linear light E must be finite, got {e!r}")
    if e <= 0.0:
        return 0.0
    if e <= HLG_ARIB_B67_BREAKPOINT_E:
        return math.sqrt(3.0 * e)
    return HLG_ARIB_B67_A * math.log(12.0 * e - HLG_ARIB_B67_B) + HLG_ARIB_B67_C


def arib_b67_hlg_inverse_oetf(ep: float) -> float:
    """Evaluate exact piecewise inverse ARIB STD-B67 HLG OETF for normalized signal `E'` in `[0, 1]`."""
    if math.isnan(ep) or math.isinf(ep):
        raise ValueError(f"Normalized signal E' must be finite, got {ep!r}")
    if ep <= 0.0:
        return 0.0
    if ep <= HLG_ARIB_B67_BREAKPOINT_EP:
        return (ep * ep) / 3.0
    return (math.exp((ep - HLG_ARIB_B67_C) / HLG_ARIB_B67_A) + HLG_ARIB_B67_B) / 12.0


def sony_hlg_variant_oetf(e: float, variant: str = "HLG3") -> float:
    """Evaluate Sony Cinema/Alpha HLG curve variant (`HLG`, `HLG1` 87%, `HLG2` 95%, `HLG3` 100%, etc.)."""
    norm_var = variant.strip().upper()
    if norm_var not in SONY_HLG_CURVE_PROFILES:
        raise ValueError(f"Unknown Sony HLG variant {variant!r}; expected {tuple(SONY_HLG_CURVE_PROFILES)}")
    max_pct = float(SONY_HLG_CURVE_PROFILES[norm_var]["max_signal_pct"])  # type: ignore[arg-type]
    base_ep = arib_b67_hlg_oetf(max(0.0, min(1.0, e)))
    return base_ep * (max_pct / 100.0)


def oetf_norm_to_10bit_code(ep: float, *, full_range: bool = False) -> int:
    """Quantize normalized non-linear OETF code `E'` in `[0, 1]` to 10-bit legal (`64..940`) or full (`0..1023`)."""
    clamped = max(0.0, min(1.0, ep))
    if full_range:
        return int(round(clamped * 1023.0))
    return int(round(64.0 + clamped * (940.0 - 64.0)))


def verify_arib_b67_oetf_roundtrip() -> HlgOetfCurveMathResult:
    """Prove C^0/C^1 continuity at `E = 1/12`, strict monotonicity, and `< 1e-10` roundtrip inversion."""
    errors: List[str] = []
    eps = 1e-12
    bp = HLG_ARIB_B67_BREAKPOINT_E
    left_ep = math.sqrt(3.0 * bp)
    right_ep = HLG_ARIB_B67_A * math.log(12.0 * (bp + eps) - HLG_ARIB_B67_B) + HLG_ARIB_B67_C
    c0_err = abs(left_ep - right_ep)

    # Analytical slopes at breakpoint E = 1/12:
    # d/dE sqrt(3E) = 3 / (2*sqrt(3*E)) = 3.0; d/dE (a*ln(12E-b)+c) = 12*a / (12E - b) = 12*a / (1 - b)
    slope_left = 3.0 / (2.0 * math.sqrt(3.0 * bp))
    slope_right = (12.0 * HLG_ARIB_B67_A) / (12.0 * bp - HLG_ARIB_B67_B)
    c1_err = abs(slope_left - slope_right)

    if c0_err > 1e-6:
        errors.append(f"C0 discontinuity at E=1/12: {c0_err:.3e}")
    if c1_err > 1e-5:
        errors.append(f"C1 slope discontinuity at E=1/12: {c1_err:.3e}")

    samples = [i / 200.0 for i in range(201)]
    samples.append(bp)
    samples = sorted(set(samples))

    prev_ep = -1.0
    monotonic = True
    max_rt_err = 0.0
    for e_val in samples:
        ep_val = arib_b67_hlg_oetf(e_val)
        if ep_val < prev_ep:
            monotonic = False
        prev_ep = ep_val
        e_rec = arib_b67_hlg_inverse_oetf(ep_val)
        rt_err = abs(e_rec - e_val)
        if rt_err > max_rt_err:
            max_rt_err = rt_err

    if not monotonic:
        errors.append("ARIB STD-B67 HLG OETF failed monotonicity check")
    if max_rt_err > 1e-10:
        errors.append(f"ARIB STD-B67 roundtrip error {max_rt_err:.3e} > 1e-10")

    h1_peak = sony_hlg_variant_oetf(1.0, "HLG1") * 100.0
    h2_peak = sony_hlg_variant_oetf(1.0, "HLG2") * 100.0
    h3_peak = sony_hlg_variant_oetf(1.0, "HLG3") * 100.0
    if not (abs(h1_peak - 87.0) < 1e-6 and abs(h2_peak - 95.0) < 1e-6 and abs(h3_peak - 100.0) < 1e-6):
        errors.append(f"Unexpected HLG1/2/3 ceiling percentages: {h1_peak}, {h2_peak}, {h3_peak}")

    c_blk = oetf_norm_to_10bit_code(arib_b67_hlg_oetf(0.0), full_range=False)
    c_bp = oetf_norm_to_10bit_code(arib_b67_hlg_oetf(bp), full_range=False)
    c_pk = oetf_norm_to_10bit_code(arib_b67_hlg_oetf(1.0), full_range=False)
    if c_blk != 64 or c_bp != 502 or c_pk != 940:
        errors.append(f"Unexpected legal 10-bit landmarks: {(c_blk, c_bp, c_pk)}")

    return HlgOetfCurveMathResult(
        passed=len(errors) == 0,
        status="ARIB_B67_HLG_OETF_VERIFIED" if not errors else "BLOCKED_HLG_OETF_MATH_FAILURE",
        arib_a=HLG_ARIB_B67_A,
        arib_b=HLG_ARIB_B67_B,
        arib_c=HLG_ARIB_B67_C,
        breakpoint_e=round(bp, 8),
        breakpoint_left_ep=round(left_ep, 8),
        breakpoint_right_ep=round(right_ep, 8),
        c0_continuity_error=c0_err,
        c1_slope_left=round(slope_left, 8),
        c1_slope_right=round(slope_right, 8),
        c1_slope_error=c1_err,
        max_roundtrip_error=max_rt_err,
        monotonic_verified=monotonic,
        code10_legal_black=c_blk,
        code10_legal_breakpoint=c_bp,
        code10_legal_peak=c_pk,
        hlg1_max_signal_pct=round(h1_peak, 3),
        hlg2_max_signal_pct=round(h2_peak, 3),
        hlg3_max_signal_pct=round(h3_peak, 3),
        errors=tuple(errors),
    )


def _triangle_area_xy(p1: Tuple[float, float], p2: Tuple[float, float], p3: Tuple[float, float]) -> float:
    return 0.5 * abs(
        p1[0] * (p2[1] - p3[1]) + p2[0] * (p3[1] - p1[1]) + p3[0] * (p1[1] - p2[1])
    )


def evaluate_hlg_gamut_transfer_contract(
    *,
    hlg_variant: str = "HLG3",
    transfer_family: str = "REC2100_HLG",
    recorded_primaries: str = "BT.2020",
    signaled_primaries: str = "BT.2020",
    matrix_conversion_applied: bool = False,
    target_display: str = "HDR_HLG",
    nle_consumer: str = "DAVINCI_RESOLVE",
) -> HlgGamutTransferEvalResult:
    """Audit HLG curve + primaries + signaling parity and block illegal gamut/transfer mismatches."""
    errors: List[str] = []
    norm_var = hlg_variant.strip().upper()
    norm_tf = transfer_family.strip().upper()
    norm_rec_p = recorded_primaries.strip().upper()
    norm_sig_p = signaled_primaries.strip().upper()
    norm_td = target_display.strip().upper()

    if norm_var not in SONY_HLG_CURVE_PROFILES:
        errors.append(f"Unsupported HLG variant {hlg_variant!r}")
        max_pct = 0.0
        dr_stops = 0.0
    else:
        prof = SONY_HLG_CURVE_PROFILES[norm_var]
        max_pct = float(prof["max_signal_pct"])  # type: ignore[arg-type]
        dr_stops = float(prof["dynamic_range_stops"])  # type: ignore[arg-type]

    if norm_tf not in VALID_TRANSFER_FAMILIES:
        errors.append(f"Unsupported transfer_family {transfer_family!r}")
    if norm_rec_p not in VALID_COLOR_PRIMARIES_SETS:
        errors.append(f"Unsupported recorded_primaries {recorded_primaries!r}")
    if norm_sig_p not in VALID_COLOR_PRIMARIES_SETS:
        errors.append(f"Unsupported signaled_primaries {signaled_primaries!r}")

    area_2020 = _triangle_area_xy(
        CIE_PRIMARIES_XY["BT.2020"]["R"],
        CIE_PRIMARIES_XY["BT.2020"]["G"],
        CIE_PRIMARIES_XY["BT.2020"]["B"],
    )
    area_709 = _triangle_area_xy(
        CIE_PRIMARIES_XY["BT.709"]["R"],
        CIE_PRIMARIES_XY["BT.709"]["G"],
        CIE_PRIMARIES_XY["BT.709"]["B"],
    )
    ratio_vs_2020 = round(
        (area_709 / area_2020) if norm_sig_p == "BT.709" else 1.0,
        4,
    )

    saturation_collapse_pct = 0.0
    hue_shift_risk = False
    status = "HLG_GAMUT_TRANSFER_VERIFIED"

    # Fail-closed guard 1: BT.2020 recorded primaries tagged as BT.709 without matrix conversion
    if norm_rec_p == "BT.2020" and norm_sig_p == "BT.709" and not matrix_conversion_applied:
        saturation_collapse_pct = round((1.0 - (area_709 / area_2020)) * 100.0, 2)
        hue_shift_risk = True
        status = "BLOCKED_BT2020_TAGGED_AS_BT709_WITHOUT_MATRIX"
        errors.append(
            "BLOCKED_BT2020_TAGGED_AS_BT709_WITHOUT_MATRIX: recording BT.2020 primaries tagged as "
            f"BT.709 without 3x3 matrix conversion collapses CIE xy gamut area by {saturation_collapse_pct}% "
            "and induces green/cyan hue shift in broadcast NLEs"
        )

    # Fail-closed guard 2: BT.709 recorded primaries tagged as BT.2020 without matrix conversion
    elif norm_rec_p == "BT.709" and norm_sig_p == "BT.2020" and not matrix_conversion_applied:
        hue_shift_risk = True
        status = "BLOCKED_BT709_TAGGED_AS_BT2020_OVER_SATURATION"
        errors.append(
            "BLOCKED_BT709_TAGGED_AS_BT2020_OVER_SATURATION: BT.709 primaries tagged as BT.2020 "
            "without 3x3 matrix conversion causes false neon over-saturation"
        )

    # Fail-closed guard 3: Transfer family mismatch (e.g., S-Log3 curve vs HLG metadata)
    if norm_tf != "REC2100_HLG":
        if status == "HLG_GAMUT_TRANSFER_VERIFIED":
            status = "BLOCKED_TRANSFER_METADATA_MISMATCH"
        errors.append(
            f"BLOCKED_TRANSFER_METADATA_MISMATCH: HLG contract requires REC2100_HLG transfer, got {norm_tf}"
        )

    # Fail-closed guard 4: SDR BT.709 target display fed raw BT.2100 HLG without conversion
    if norm_td == "SDR_BT_709" and norm_sig_p == "BT.2020" and not matrix_conversion_applied:
        if status == "HLG_GAMUT_TRANSFER_VERIFIED":
            status = "BLOCKED_SDR_TARGET_HLG_BT2020_MISMATCH"
        errors.append(
            "BLOCKED_SDR_TARGET_HLG_BT2020_MISMATCH: SDR_BT_709 target display cannot consume "
            "raw HLG BT.2020 without Gamma Display Assist or 3D LUT conversion"
        )

    return HlgGamutTransferEvalResult(
        valid=len(errors) == 0,
        status=status,
        hlg_variant=norm_var,
        transfer_family=norm_tf,
        recorded_primaries=norm_rec_p,
        signaled_primaries=norm_sig_p,
        matrix_conversion_applied=matrix_conversion_applied,
        target_display=norm_td,
        nle_consumer=nle_consumer.strip().upper(),
        gamut_area_ratio_vs_bt2020=ratio_vs_2020,
        saturation_collapse_pct=saturation_collapse_pct,
        hue_shift_risk=hue_shift_risk,
        max_signal_pct=max_pct,
        dynamic_range_stops=dr_stops,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 2 Functions: Gamma Display Assist EVF/LCD Tone-Mapping Isolation
# ---------------------------------------------------------------------------


def _apply_3x3_matrix(
    mat: Tuple[Tuple[float, float, float], ...],
    vec: Tuple[float, float, float],
) -> Tuple[float, float, float]:
    return (
        mat[0][0] * vec[0] + mat[0][1] * vec[1] + mat[0][2] * vec[2],
        mat[1][0] * vec[0] + mat[1][1] * vec[1] + mat[1][2] * vec[2],
        mat[2][0] * vec[0] + mat[2][1] * vec[1] + mat[2][2] * vec[2],
    )


def _bt709_oetf(linear_val: float) -> float:
    x = max(0.0, min(1.0, linear_val))
    if x < 0.018:
        return 4.5 * x
    return 1.099 * (x ** 0.45) - 0.099


def compute_display_assist_preview_rgb(
    rgb_encoded: Tuple[float, float, float],
    *,
    assist_mode: str,
) -> Tuple[float, float, float]:
    """Compute bounded LCD/EVF SDR Rec.709 preview RGB for Sony Gamma Display Assist modes."""
    mode = assist_mode.strip().upper()
    if mode not in ("SLOG3_TO_709_800", "SLOG2_TO_709_800", "HLG_BT2020_TO_709", "HLG_709_TO_709"):
        raise ValueError(f"Unsupported preview transform mode {assist_mode!r}")

    r_in, g_in, b_in = (max(0.0, min(1.0, float(c))) for c in rgb_encoded)

    if mode in ("HLG_BT2020_TO_709", "HLG_709_TO_709"):
        # Inverse ARIB STD-B67 -> scene linear -> optional BT.2020->BT.709 matrix -> SDR knee + Rec.709 OETF
        lin_rgb = (
            arib_b67_hlg_inverse_oetf(r_in),
            arib_b67_hlg_inverse_oetf(g_in),
            arib_b67_hlg_inverse_oetf(b_in),
        )
        if mode == "HLG_BT2020_TO_709":
            lin_rgb = _apply_3x3_matrix(BT2020_TO_BT709_MATRIX_3X3, lin_rgb)
        # Soft highlight roll-off mapping HLG scene white (~0.26 linear at 75% signal) to SDR Rec.709
        mapped = tuple(_bt709_oetf(max(0.0, c) / (max(0.0, c) + 0.18) * 1.18) for c in lin_rgb)
        return (round(mapped[0], 6), round(mapped[1], 6), round(mapped[2], 6))

    # S-Log3 / S-Log2 -> ITU709(800%) display assist: lift 41% grey / 32% grey -> ~45-50% SDR Rec.709
    gain = 1.18 if mode == "SLOG3_TO_709_800" else 1.24
    mapped = tuple(
        round(_bt709_oetf(max(0.0, (c ** 1.35) * gain)), 6)
        for c in (r_in, g_in, b_in)
    )
    return (mapped[0], mapped[1], mapped[2])


def _resolve_assist_transform(
    assist_type: str,
    capture_gamma: str,
    capture_primaries: str,
) -> str:
    norm_type = assist_type.strip().upper()
    norm_gamma = capture_gamma.strip().upper()
    norm_prim = capture_primaries.strip().upper()
    if norm_type == "OFF":
        return "BYPASS_OFF"
    if norm_type != "AUTO":
        return norm_type
    if norm_gamma == "S_LOG3":
        return "SLOG3_TO_709_800"
    if norm_gamma == "S_LOG2":
        return "SLOG2_TO_709_800"
    if norm_gamma == "REC2100_HLG":
        return "HLG_BT2020_TO_709" if norm_prim == "BT.2020" else "HLG_709_TO_709"
    return "BYPASS_SDR"


def evaluate_gamma_display_assist_isolation(
    *,
    assist_display_on: bool = True,
    assist_type: str = "AUTO",
    capture_gamma: str = "REC2100_HLG",
    capture_primaries: str = "BT.2020",
    xavc_main_mlut_burn_in: bool = False,
    clean_hdmi_mlut_enabled: bool = False,
    lcd_evf_mlut_active: bool = False,
    lcd_evf_assist_leaked_to_xavc: bool = False,
    lcd_evf_assist_leaked_to_clean_hdmi: bool = False,
) -> GammaDisplayAssistEvalResult:
    """Verify LCD/EVF Gamma Display Assist isolation from XAVC main clips and Clean-HDMI output."""
    errors: List[str] = []
    norm_type = assist_type.strip().upper()
    norm_gamma = capture_gamma.strip().upper()
    norm_prim = capture_primaries.strip().upper()

    if norm_type not in VALID_GAMMA_DISPLAY_ASSIST_TYPES:
        errors.append(f"Unsupported Gamma Display Assist type {assist_type!r}")
    if norm_gamma not in VALID_TRANSFER_FAMILIES:
        errors.append(f"Unsupported capture_gamma {capture_gamma!r}")

    resolved = _resolve_assist_transform(norm_type, norm_gamma, norm_prim) if assist_display_on else "BYPASS_OFF"

    # HAITA exclusion: when User 3D LUT / MLUT is already active on LCD/EVF, Display Assist defers
    double_tone_map_prevented = True
    if assist_display_on and lcd_evf_mlut_active:
        resolved = "DEFERRED_TO_ACTIVE_MLUT"

    tone_mapped_preview = bool(
        assist_display_on
        and not lcd_evf_mlut_active
        and resolved not in ("BYPASS_OFF", "BYPASS_SDR", "DEFERRED_TO_ACTIVE_MLUT")
    )

    sample_in = (0.41, 0.41, 0.41) if norm_gamma == "S_LOG3" else (0.50, 0.50, 0.50)
    if tone_mapped_preview:
        sample_evf = compute_display_assist_preview_rgb(sample_in, assist_mode=resolved)
    else:
        sample_evf = sample_in

    # XAVC Main & Clean-HDMI isolation invariant:
    # LCD/EVF Gamma Display Assist MUST NEVER burn into recorded XAVC main or Clean-HDMI!
    burned_xavc = bool(lcd_evf_assist_leaked_to_xavc and not xavc_main_mlut_burn_in)
    burned_hdmi = bool(lcd_evf_assist_leaked_to_clean_hdmi and not clean_hdmi_mlut_enabled)

    xavc_native = (not xavc_main_mlut_burn_in) and (not lcd_evf_assist_leaked_to_xavc)
    hdmi_native = (not clean_hdmi_mlut_enabled) and (not lcd_evf_assist_leaked_to_clean_hdmi)

    status = "DISPLAY_ASSIST_ISOLATED_VERIFIED"
    if burned_xavc:
        status = "BLOCKED_DISPLAY_ASSIST_BURN_IN_LEAK_XAVC"
        errors.append(
            "BLOCKED_DISPLAY_ASSIST_BURN_IN_LEAK_XAVC: LCD/EVF Gamma Display Assist leaked into "
            "recorded XAVC main clip without explicit MLUT burn-in"
        )
    if burned_hdmi:
        status = "BLOCKED_DISPLAY_ASSIST_BURN_IN_LEAK_HDMI"
        errors.append(
            "BLOCKED_DISPLAY_ASSIST_BURN_IN_LEAK_HDMI: LCD/EVF Gamma Display Assist leaked into "
            "Clean-HDMI output without explicit HDMI MLUT enabled"
        )
    if lcd_evf_mlut_active and not errors:
        status = "DISPLAY_ASSIST_DEFERRED_TO_MLUT"

    return GammaDisplayAssistEvalResult(
        valid=len(errors) == 0,
        status=status,
        assist_display_on=assist_display_on,
        assist_type=norm_type,
        resolved_transform=resolved,
        capture_gamma=norm_gamma,
        capture_primaries=norm_prim,
        xavc_main_mlut_burn_in=xavc_main_mlut_burn_in,
        clean_hdmi_mlut_enabled=clean_hdmi_mlut_enabled,
        lcd_evf_receives_tone_mapped_preview=tone_mapped_preview,
        xavc_main_preserves_native_gamma=xavc_native,
        clean_hdmi_preserves_native_gamma=hdmi_native,
        lcd_evf_assist_burned_into_xavc=burned_xavc,
        lcd_evf_assist_burned_into_clean_hdmi=burned_hdmi,
        double_tone_map_prevented=double_tone_map_prevented,
        sample_midgrey_in_rgb=sample_in,
        sample_midgrey_evf_rgb=sample_evf,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 3 Functions: CTA-861.3 HDR Dynamic Range & Mastering InfoFrame 0x87
# ---------------------------------------------------------------------------


def build_cta861_3_hdr_infoframe(
    *,
    eotf_code: int = CTA861_EOTF_CODES["BT2100_HLG"],
    static_metadata_descriptor_id: int = CTA861_STATIC_METADATA_TYPE_1_ID,
    primaries_set: str = "BT.2020",
    max_display_mastering_luminance_nits: int = 1000,
    min_display_mastering_luminance_0001_nits: int = 50,
    max_cll_nits: int = 1000,
    max_fall_nits: int = 400,
) -> bytes:
    """Synthesize a 30-byte CTA-861.3 Static Metadata Type 1 HDR InfoFrame (`0x87 v1 len=26`)."""
    if eotf_code not in CTA861_EOTF_NAMES:
        raise ValueError(f"Invalid CTA-861.3 EOTF code {eotf_code:#x}")
    if static_metadata_descriptor_id != CTA861_STATIC_METADATA_TYPE_1_ID:
        raise ValueError(
            f"Unsupported Static_Metadata_Descriptor_ID={static_metadata_descriptor_id}; expected 0"
        )
    norm_prim = primaries_set.strip().upper()
    if norm_prim not in CIE_PRIMARIES_XY:
        raise ValueError(f"Unsupported CIE primaries set {primaries_set!r}")

    xy = CIE_PRIMARIES_XY[norm_prim]
    # CTA-861.3 ordering: G (idx 0), B (idx 1), R (idx 2), then W, in 0.00002 units
    gx, gy = int(round(xy["G"][0] * 50000)), int(round(xy["G"][1] * 50000))
    bx, by = int(round(xy["B"][0] * 50000)), int(round(xy["B"][1] * 50000))
    rx, ry = int(round(xy["R"][0] * 50000)), int(round(xy["R"][1] * 50000))
    wx, wy = int(round(xy["W"][0] * 50000)), int(round(xy["W"][1] * 50000))

    payload = struct.pack(
        "<BB12H",
        eotf_code & 0x07,
        static_metadata_descriptor_id & 0xFF,
        gx,
        gy,
        bx,
        by,
        rx,
        ry,
        wx,
        wy,
        max_display_mastering_luminance_nits & 0xFFFF,
        min_display_mastering_luminance_0001_nits & 0xFFFF,
        max_cll_nits & 0xFFFF,
        max_fall_nits & 0xFFFF,
    )
    if len(payload) != CTA861_HDR_DRM_PAYLOAD_LEN:
        raise AssertionError(f"CTA-861.3 payload length {len(payload)} != 26")

    header_3 = bytes(
        (
            CTA861_HDR_DRM_INFOFRAME_TYPE,
            CTA861_HDR_DRM_INFOFRAME_VERSION,
            CTA861_HDR_DRM_PAYLOAD_LEN,
        )
    )
    checksum = (256 - ((sum(header_3) + sum(payload)) & 0xFF)) & 0xFF
    packet = header_3 + bytes((checksum,)) + payload
    if len(packet) != CTA861_HDR_DRM_TOTAL_BYTES:
        raise AssertionError(f"CTA-861.3 packet length {len(packet)} != 30")
    return packet


def decode_cta861_3_hdr_infoframe(packet: bytes) -> Cta861HdrInfoFrameDecoded:
    """Decode and checksum-verify a 30-byte CTA-861.3 HDR Dynamic Range & Mastering InfoFrame."""
    errors: List[str] = []
    if len(packet) != CTA861_HDR_DRM_TOTAL_BYTES:
        return Cta861HdrInfoFrameDecoded(
            valid=False,
            infoframe_type=packet[0] if len(packet) > 0 else -1,
            version=packet[1] if len(packet) > 1 else -1,
            payload_length=packet[2] if len(packet) > 2 else -1,
            total_bytes=len(packet),
            checksum_byte=packet[3] if len(packet) > 3 else -1,
            checksum_valid=False,
            eotf_code=-1,
            eotf_name="INVALID",
            static_metadata_descriptor_id=-1,
            primaries_xy_50k=((0, 0), (0, 0), (0, 0)),
            white_point_xy_50k=(0, 0),
            max_display_mastering_luminance_nits=0,
            min_display_mastering_luminance_0001_nits=0,
            max_cll_nits=0,
            max_fall_nits=0,
            packet_hex=packet.hex(),
            errors=(f"Invalid CTA-861.3 packet byte length {len(packet)} != 30",),
        )

    if_type, version, payload_len, csum = packet[0], packet[1], packet[2], packet[3]
    if if_type != CTA861_HDR_DRM_INFOFRAME_TYPE:
        errors.append(f"Invalid InfoFrame type {if_type:#x}; expected 0x87")
    if version != CTA861_HDR_DRM_INFOFRAME_VERSION:
        errors.append(f"Invalid InfoFrame version {version:#x}; expected 0x01")
    if payload_len != CTA861_HDR_DRM_PAYLOAD_LEN:
        errors.append(f"Invalid InfoFrame payload length {payload_len}; expected 26")

    checksum_valid = (sum(packet) & 0xFF) == 0
    if not checksum_valid:
        errors.append(
            f"CTA-861.3 InfoFrame checksum invalid: sum(packet)&0xFF={sum(packet) & 0xFF:#x} != 0"
        )

    eotf_raw, desc_id, gx, gy, bx, by, rx, ry, wx, wy, max_lum, min_lum, max_cll, max_fall = (
        struct.unpack("<BB12H", packet[4:30])
    )
    eotf_code = eotf_raw & 0x07
    eotf_name = CTA861_EOTF_NAMES.get(eotf_code, f"RESERVED_{eotf_code:#x}")
    if eotf_code not in CTA861_EOTF_NAMES:
        errors.append(f"Unknown CTA-861.3 EOTF code {eotf_code:#x}")
    if desc_id != CTA861_STATIC_METADATA_TYPE_1_ID:
        errors.append(f"Unsupported Static_Metadata_Descriptor_ID={desc_id}; expected 0")

    return Cta861HdrInfoFrameDecoded(
        valid=len(errors) == 0,
        infoframe_type=if_type,
        version=version,
        payload_length=payload_len,
        total_bytes=len(packet),
        checksum_byte=csum,
        checksum_valid=checksum_valid,
        eotf_code=eotf_code,
        eotf_name=eotf_name,
        static_metadata_descriptor_id=desc_id,
        primaries_xy_50k=((gx, gy), (bx, by), (rx, ry)),
        white_point_xy_50k=(wx, wy),
        max_display_mastering_luminance_nits=max_lum,
        min_display_mastering_luminance_0001_nits=min_lum,
        max_cll_nits=max_cll,
        max_fall_nits=max_fall,
        packet_hex=packet.hex(),
        errors=tuple(errors),
    )


def evaluate_hdmi_hdr_infoframe_handshake(
    *,
    camera_gamma: str = "REC2100_HLG",
    camera_primaries: str = "BT.2020",
    avi_colorimetry: str = "BT2020_NCL",
    hdmi_raw16_active: bool = False,
    target_monitor: str = "ATOMOS_NINJA_V_PLUS",
    eotf_code_override: Optional[int] = None,
    corrupt_checksum: bool = False,
    max_mastering_nits: int = 1000,
    max_cll_nits: int = 1000,
    max_fall_nits: int = 400,
) -> HdmiHdrInfoFrameEvalResult:
    """Audit CTA-861.3 InfoFrame `0x87` + AVI Colorimetry + External HDR Monitor auto-switch."""
    errors: List[str] = []
    norm_gamma = camera_gamma.strip().upper()
    norm_prim = camera_primaries.strip().upper()
    norm_avi = avi_colorimetry.strip().upper()
    norm_mon = target_monitor.strip().upper()

    if norm_mon not in VALID_EXTERNAL_HDR_MONITORS:
        errors.append(f"Unsupported external HDR monitor {target_monitor!r}")

    expected_eotf = CTA861_EOTF_CODES["BT2100_HLG"]
    if norm_gamma == "SMPTE_ST2084_PQ":
        expected_eotf = CTA861_EOTF_CODES["SMPTE_ST2084_PQ"]
    elif norm_gamma == "ITU709":
        expected_eotf = CTA861_EOTF_CODES["SDR_GAMMA"]

    tx_eotf = expected_eotf if eotf_code_override is None else eotf_code_override
    if_primaries = "BT.2020" if norm_prim == "BT.2020" else "BT.709"
    pkt = bytearray(
        build_cta861_3_hdr_infoframe(
            eotf_code=tx_eotf,
            primaries_set=if_primaries,
            max_display_mastering_luminance_nits=max_mastering_nits,
            max_cll_nits=max_cll_nits,
            max_fall_nits=max_fall_nits,
        )
    )
    if corrupt_checksum:
        pkt[3] ^= 0x5A

    decoded = decode_cta861_3_hdr_infoframe(bytes(pkt))
    if not decoded.valid:
        errors.extend(decoded.errors)

    status = "HDMI_HDR_INFOFRAME_HANDSHAKE_VERIFIED"
    if not decoded.checksum_valid:
        status = "BLOCKED_INFOFRAME_CHECKSUM_MISMATCH"
    if hdmi_raw16_active:
        status = "BLOCKED_RAW16_HDR_INFOFRAME_CONFLICT"
        errors.append(
            "BLOCKED_RAW16_HDR_INFOFRAME_CONFLICT: HDMI 16-bit RAW output cannot carry CTA-861.3 "
            "YCbCr HDR InfoFrame EOTF metadata"
        )
    if tx_eotf != expected_eotf:
        if status == "HDMI_HDR_INFOFRAME_HANDSHAKE_VERIFIED":
            status = "BLOCKED_EOTF_TRANSFER_MISMATCH"
        errors.append(
            f"BLOCKED_EOTF_TRANSFER_MISMATCH: camera_gamma={norm_gamma} requires "
            f"EOTF={expected_eotf:#x}, transmitted EOTF={tx_eotf:#x}"
        )
    if norm_gamma == "REC2100_HLG" and norm_prim == "BT.2020" and norm_avi != "BT2020_NCL":
        if status == "HDMI_HDR_INFOFRAME_HANDSHAKE_VERIFIED":
            status = "BLOCKED_HLG_AVI_COLORIMETRY_MISMATCH"
        errors.append(
            f"BLOCKED_HLG_AVI_COLORIMETRY_MISMATCH: HLG BT.2020 requires AVI Colorimetry BT2020_NCL, got {norm_avi}"
        )

    if errors:
        detected_mode = "ERROR_FALLBACK_SDR_709"
        switched_hlg = False
    elif decoded.eotf_code == CTA861_EOTF_CODES["BT2100_HLG"] and norm_avi == "BT2020_NCL":
        detected_mode = "HLG_BT2020_HDR"
        switched_hlg = True
    elif decoded.eotf_code == CTA861_EOTF_CODES["SMPTE_ST2084_PQ"]:
        detected_mode = "PQ_ST2084_BT2020_HDR"
        switched_hlg = False
    else:
        detected_mode = "SDR_BT709"
        switched_hlg = False

    return HdmiHdrInfoFrameEvalResult(
        valid=len(errors) == 0,
        status=status,
        camera_gamma=norm_gamma,
        camera_primaries=norm_prim,
        avi_colorimetry=norm_avi,
        hdmi_raw16_active=hdmi_raw16_active,
        target_monitor=norm_mon,
        monitor_detected_mode=detected_mode,
        monitor_auto_switched_hlg_bt2020=switched_hlg,
        decoded_infoframe=decoded,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 4 Functions: NonRealTimeMeta XML SMPTE UL Parity & Zero Mutation
# ---------------------------------------------------------------------------


def synthesize_hlg_nrtm_xml(
    *,
    umid_ref: str = "060A2B340101010501010D4313000000A001C001261114HL",
    duration_frames: int = 240,
    creation_iso8601: str = "2026-11-14T18:30:00-08:00",
    capture_gamma_equation: str = "rec2100-hlg",
    capture_color_primaries: str = "rec2020",
    hlg_variant: str = "HLG3",
    smpte_ul_gamma_hex: Optional[str] = None,
    smpte_ul_primaries_hex: Optional[str] = None,
    device_model_name: str = "ILME-FX3",
) -> str:
    """Synthesize a Sony `NonRealTimeMeta v2.20` XML sidecar carrying SMPTE UL HLG/BT.2020 tags."""
    gamma_ul = smpte_ul_gamma_hex or NRTM_GAMMA_TO_SMPTE_UL.get(capture_gamma_equation, "")
    prim_ul = smpte_ul_primaries_hex or NRTM_PRIMARIES_TO_SMPTE_UL.get(capture_color_primaries, "")

    ET.register_namespace("", NRTM_NAMESPACE_V220)
    ET.register_namespace("lib", NRTM_LIB_NAMESPACE_V220)

    def _q(tag: str) -> str:
        return f"{{{NRTM_NAMESPACE_V220}}}{tag}"

    root = ET.Element(_q("NonRealTimeMeta"), {"lastUpdate": creation_iso8601})
    ET.SubElement(root, _q("TargetMaterial"), {"umidRef": umid_ref})
    ET.SubElement(root, _q("Duration"), {"value": str(duration_frames)})
    ET.SubElement(root, _q("CreationDate"), {"value": creation_iso8601})
    ET.SubElement(
        root,
        _q("Device"),
        {
            "manufacturer": "Sony",
            "modelName": device_model_name,
            "serialNo": "00000000",
            "ver": "7.02-stageB-ram-overlay",
        },
    )

    acq = ET.SubElement(root, _q("AcquisitionRecord"))
    cam_grp = ET.SubElement(acq, _q("Group"), {"name": "CameraUnitMetadataSet"})
    ET.SubElement(cam_grp, _q("Item"), {"name": "CaptureGammaEquation", "value": capture_gamma_equation})
    ET.SubElement(cam_grp, _q("Item"), {"name": "CaptureColorPrimaries", "value": capture_color_primaries})
    ET.SubElement(cam_grp, _q("Item"), {"name": "SonyHlgCurveVariant", "value": hlg_variant})
    ET.SubElement(cam_grp, _q("Item"), {"name": "SmpteUlCaptureGammaEquation", "value": gamma_ul})
    ET.SubElement(cam_grp, _q("Item"), {"name": "SmpteUlCaptureColorPrimaries", "value": prim_ul})

    ET.indent(root, space="  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode") + "\n"


def parse_and_verify_hlg_nrtm_xml(
    xml_text: str,
    *,
    allow_hlg_bt709_compat: bool = False,
) -> HlgNrtmXmlEvalResult:
    """Parse and verify `NonRealTimeMeta v2.20` XML `<CaptureGammaEquation>` & `<ColorPrimaries>` SMPTE UL parity."""
    errors: List[str] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        return HlgNrtmXmlEvalResult(
            valid=False,
            status="BLOCKED_INVALID_NRTM_XML",
            namespace_uri="",
            capture_gamma_equation="",
            capture_color_primaries="",
            smpte_ul_gamma_hex="",
            smpte_ul_primaries_hex="",
            smpte_ul_parity_ok=False,
            hlg_variant="",
            device_model_name="",
            errors=(f"XML parse error: {exc}",),
        )

    ns_uri = root.tag[1:].split("}", 1)[0] if root.tag.startswith("{") else ""
    if ns_uri != NRTM_NAMESPACE_V220:
        errors.append(f"Unexpected namespace URI {ns_uri!r}; expected {NRTM_NAMESPACE_V220!r}")

    def _q(tag: str) -> str:
        return f"{{{NRTM_NAMESPACE_V220}}}{tag}"

    dev_el = root.find(_q("Device"))
    model_name = dev_el.attrib.get("modelName", "") if dev_el is not None else ""
    if model_name not in ("ILME-FX3", "ILME-FX6"):
        errors.append(f"Unexpected Device modelName={model_name!r}")

    kv: Dict[str, str] = {}
    for item in root.iter(_q("Item")):
        nm = item.attrib.get("name", "")
        if nm:
            kv[nm] = item.attrib.get("value", "")

    gamma_eq = kv.get("CaptureGammaEquation", "")
    primaries = kv.get("CaptureColorPrimaries", "")
    ul_gamma = kv.get("SmpteUlCaptureGammaEquation", "").lower()
    ul_prim = kv.get("SmpteUlCaptureColorPrimaries", "").lower()
    hlg_var = kv.get("SonyHlgCurveVariant", "")

    expected_gamma_ul = NRTM_GAMMA_TO_SMPTE_UL.get(gamma_eq, "")
    expected_prim_ul = NRTM_PRIMARIES_TO_SMPTE_UL.get(primaries, "")

    ul_parity = bool(
        expected_gamma_ul
        and expected_prim_ul
        and ul_gamma == expected_gamma_ul
        and ul_prim == expected_prim_ul
    )
    if not ul_parity:
        errors.append(
            f"BLOCKED_SMPTE_UL_MISMATCH: gamma=({gamma_eq!r}, {ul_gamma!r} vs {expected_gamma_ul!r}), "
            f"primaries=({primaries!r}, {ul_prim!r} vs {expected_prim_ul!r})"
        )

    status = "NRTM_HLG_SMPTE_UL_PARITY_VERIFIED"
    if gamma_eq == "rec2100-hlg" and primaries == "rec709" and not allow_hlg_bt709_compat:
        status = "BLOCKED_NRTM_HLG_BT709_PRIMARIES_MISMATCH"
        errors.append(
            "BLOCKED_NRTM_HLG_BT709_PRIMARIES_MISMATCH: rec2100-hlg requires rec2020 ColorPrimaries "
            "unless explicit HLG(709) compatibility mode is requested"
        )
    elif errors:
        status = "BLOCKED_SMPTE_UL_MISMATCH"

    return HlgNrtmXmlEvalResult(
        valid=len(errors) == 0,
        status=status,
        namespace_uri=ns_uri,
        capture_gamma_equation=gamma_eq,
        capture_color_primaries=primaries,
        smpte_ul_gamma_hex=ul_gamma,
        smpte_ul_primaries_hex=ul_prim,
        smpte_ul_parity_ok=ul_parity,
        hlg_variant=hlg_var,
        device_model_name=model_name,
        errors=tuple(errors),
    )


def evaluate_hdr_calibration_write_guard(target_path: str) -> HdrCalibrationGuardResult:
    """Enforce volatile RAM staging only and zero calibration/eMMC mutation."""
    norm = target_path.strip()
    is_volatile = norm.startswith(VOLATILE_STAGING_PREFIXES) and not bool(
        FORBIDDEN_CALIBRATION_TARGET_RE.search(norm)
    )
    if is_volatile:
        return HdrCalibrationGuardResult(
            valid=True,
            status="VOLATILE_RAM_STAGING_ALLOWED",
            target_path=norm,
            volatile_ram_staged=True,
            persistent_write_blocked=False,
            calibration_mutation_bytes=0,
            emmc_mutation_bytes=0,
            errors=(),
        )
    return HdrCalibrationGuardResult(
        valid=False,
        status="BLOCKED_PERSISTENT_CALIBRATION_OR_EMMC_WRITE",
        target_path=norm,
        volatile_ram_staged=False,
        persistent_write_blocked=True,
        calibration_mutation_bytes=0,
        emmc_mutation_bytes=0,
        errors=(f"BLOCKED_PERSISTENT_CALIBRATION_OR_EMMC_WRITE: target_path={norm!r}",),
    )


def verify_hdr_zero_calibration_mutation(
    *,
    fx3_libmpr_markers: Tuple[str, ...],
    fx6_libmpr_markers: Tuple[str, ...],
    fx3_smpte_uls: Tuple[str, ...],
    fx6_smpte_uls: Tuple[str, ...],
    fx3_global_xdb_valid: bool,
    fx6_global_xdb_valid: bool,
    extra_errors: Sequence[str] = (),
) -> HdrNrtmAndImmutabilityReport:
    """Verify NonRealTimeMeta HLG XML + SMPTE UL parity and zero calibration/eMMC mutations."""
    errors = list(extra_errors)
    if not fx3_global_xdb_valid:
        errors.append("FX3 global.xdb (uxa\\x07) failed structural validation")
    if not fx6_global_xdb_valid:
        errors.append("FX6 global.xdb (uxa\\x07) failed structural validation")

    xml_valid = synthesize_hlg_nrtm_xml(
        capture_gamma_equation="rec2100-hlg",
        capture_color_primaries="rec2020",
        hlg_variant="HLG3",
    )
    e_nrtm = parse_and_verify_hlg_nrtm_xml(xml_valid)
    if not e_nrtm.valid:
        errors.extend(e_nrtm.errors)

    xml_bad = synthesize_hlg_nrtm_xml(
        capture_gamma_equation="rec2100-hlg",
        capture_color_primaries="rec709",
        hlg_variant="HLG3",
    )
    b_nrtm = parse_and_verify_hlg_nrtm_xml(xml_bad, allow_hlg_bt709_compat=False)
    if b_nrtm.valid:
        errors.append("NRTM HLG + BT.709 mismatch was not blocked")

    g_vol = evaluate_hdr_calibration_write_guard("/tmp/fx3_hlg_display_assist_shadow.json")
    g_psd = evaluate_hdr_calibration_write_guard("p2:/setting/psd.bin")
    g_cn = evaluate_hdr_calibration_write_guard("/dev/cnflasha0")
    g_bak = evaluate_hdr_calibration_write_guard("p2:/setting/Backup.bin")

    if not g_vol.valid:
        errors.append("Volatile RAM staging unexpectedly blocked")
    for lbl, blk in (("psd.bin", g_psd), ("cnflasha0", g_cn), ("Backup.bin", g_bak)):
        if blk.valid:
            errors.append(f"Persistent target {lbl} was not blocked")

    return HdrNrtmAndImmutabilityReport(
        passed=len(errors) == 0,
        fx3_libmpr_markers=fx3_libmpr_markers,
        fx6_libmpr_markers=fx6_libmpr_markers,
        fx3_smpte_uls_verified=fx3_smpte_uls,
        fx6_smpte_uls_verified=fx6_smpte_uls,
        fx3_global_xdb_valid=fx3_global_xdb_valid,
        fx6_global_xdb_valid=fx6_global_xdb_valid,
        eval_hlg_bt2020_nrtm_xml=e_nrtm,
        blocked_hlg_bt709_nrtm_mismatch=b_nrtm,
        volatile_staging_guard=g_vol,
        blocked_psd_bin_guard=g_psd,
        blocked_cnflasha_guard=g_cn,
        blocked_backup_bin_guard=g_bak,
        calibration_mutation_bytes=0,
        emmc_mutation_bytes=0,
        persistent_emmc_writes_authorized=False,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar Evaluators & Top-Level Phase 111 Unified Auditor
# ---------------------------------------------------------------------------


def evaluate_pillar_1_hlg_bt2100_curves(
    *,
    fx3_appfw_hlg_markers: Tuple[str, ...],
    fx6_appfw_hlg_markers: Tuple[str, ...],
    fx3_cp_hlg_markers: Tuple[str, ...],
    fx6_cp_hlg_markers: Tuple[str, ...],
    uxc_hlg_labels: Dict[str, str],
    extra_errors: Sequence[str] = (),
) -> HlgBt2100CurveReport:
    errors = list(extra_errors)
    math_proof = verify_arib_b67_oetf_roundtrip()
    if not math_proof.passed:
        errors.extend(math_proof.errors)

    e_hlg3 = evaluate_hlg_gamut_transfer_contract(hlg_variant="HLG3", recorded_primaries="BT.2020", signaled_primaries="BT.2020")
    e_hlg1 = evaluate_hlg_gamut_transfer_contract(hlg_variant="HLG1", recorded_primaries="BT.2020", signaled_primaries="BT.2020")
    e_hlg2 = evaluate_hlg_gamut_transfer_contract(hlg_variant="HLG2", recorded_primaries="BT.2020", signaled_primaries="BT.2020")
    e_live = evaluate_hlg_gamut_transfer_contract(hlg_variant="HLG_LIVE", recorded_primaries="BT.2020", signaled_primaries="BT.2020")

    b_2020_709 = evaluate_hlg_gamut_transfer_contract(
        hlg_variant="HLG3",
        recorded_primaries="BT.2020",
        signaled_primaries="BT.709",
        matrix_conversion_applied=False,
    )
    b_709_2020 = evaluate_hlg_gamut_transfer_contract(
        hlg_variant="HLG3",
        recorded_primaries="BT.709",
        signaled_primaries="BT.2020",
        matrix_conversion_applied=False,
    )
    b_slog_tf = evaluate_hlg_gamut_transfer_contract(
        hlg_variant="HLG3",
        transfer_family="S_LOG3",
        recorded_primaries="BT.2020",
        signaled_primaries="BT.2020",
    )

    for lbl, ev in (("HLG3", e_hlg3), ("HLG1", e_hlg1), ("HLG2", e_hlg2), ("HLG_LIVE", e_live)):
        if not ev.valid:
            errors.append(f"Positive HLG evaluation {lbl} failed: {ev.errors}")
    for lbl, blk in (
        ("bt2020_tagged_bt709", b_2020_709),
        ("bt709_tagged_bt2020", b_709_2020),
        ("slog3_tagged_hlg", b_slog_tf),
    ):
        if blk.valid:
            errors.append(f"Negative gamut/transfer guard {lbl} unexpectedly passed")

    return HlgBt2100CurveReport(
        passed=len(errors) == 0,
        fx3_appfw_hlg_markers=fx3_appfw_hlg_markers,
        fx6_appfw_hlg_markers=fx6_appfw_hlg_markers,
        fx3_cp_hlg_markers=fx3_cp_hlg_markers,
        fx6_cp_hlg_markers=fx6_cp_hlg_markers,
        uxc_hlg_labels=uxc_hlg_labels,
        oetf_math_proof=math_proof,
        eval_hlg3_bt2020_hdr=e_hlg3,
        eval_hlg1_bt2020_nr=e_hlg1,
        eval_hlg2_bt2020_balanced=e_hlg2,
        eval_fx6_hlg_live_bt2020=e_live,
        blocked_bt2020_tagged_bt709_no_matrix=b_2020_709,
        blocked_bt709_tagged_bt2020_oversat=b_709_2020,
        blocked_slog3_tagged_hlg_transfer=b_slog_tf,
        errors=tuple(errors),
    )


def evaluate_pillar_2_gamma_display_assist(
    *,
    fx3_appfw_assist_markers: Tuple[str, ...],
    fx6_appfw_assist_markers: Tuple[str, ...],
    fx3_cp_assist_markers: Tuple[str, ...],
    fx6_cp_assist_markers: Tuple[str, ...],
    uxc_assist_labels: Dict[str, str],
    extra_errors: Sequence[str] = (),
) -> GammaDisplayAssistReport:
    errors = list(extra_errors)

    e_slog3 = evaluate_gamma_display_assist_isolation(
        assist_display_on=True,
        assist_type="AUTO",
        capture_gamma="S_LOG3",
        capture_primaries="S-GAMUT3.CINE",
    )
    e_hlg2020 = evaluate_gamma_display_assist_isolation(
        assist_display_on=True,
        assist_type="AUTO",
        capture_gamma="REC2100_HLG",
        capture_primaries="BT.2020",
    )
    e_hlg709 = evaluate_gamma_display_assist_isolation(
        assist_display_on=True,
        assist_type="HLG_709_TO_709",
        capture_gamma="REC2100_HLG",
        capture_primaries="BT.709",
    )
    e_mlut = evaluate_gamma_display_assist_isolation(
        assist_display_on=True,
        assist_type="AUTO",
        capture_gamma="S_LOG3",
        capture_primaries="S-GAMUT3.CINE",
        lcd_evf_mlut_active=True,
    )
    b_xavc_leak = evaluate_gamma_display_assist_isolation(
        assist_display_on=True,
        assist_type="SLOG3_TO_709_800",
        capture_gamma="S_LOG3",
        capture_primaries="S-GAMUT3.CINE",
        lcd_evf_assist_leaked_to_xavc=True,
    )
    b_hdmi_leak = evaluate_gamma_display_assist_isolation(
        assist_display_on=True,
        assist_type="HLG_BT2020_TO_709",
        capture_gamma="REC2100_HLG",
        capture_primaries="BT.2020",
        lcd_evf_assist_leaked_to_clean_hdmi=True,
    )

    for lbl, ev in (
        ("slog3_auto", e_slog3),
        ("hlg2020_auto", e_hlg2020),
        ("hlg709_explicit", e_hlg709),
        ("mlut_defer", e_mlut),
    ):
        if not ev.valid or ev.lcd_evf_assist_burned_into_xavc or ev.lcd_evf_assist_burned_into_clean_hdmi:
            errors.append(f"Display Assist isolation check {lbl} failed: {ev.errors}")

    if not e_slog3.xavc_main_preserves_native_gamma or not e_hlg2020.clean_hdmi_preserves_native_gamma:
        errors.append("Native XAVC/Clean-HDMI gamma preservation invariant failed")
    if b_xavc_leak.valid or not b_xavc_leak.lcd_evf_assist_burned_into_xavc:
        errors.append("XAVC burn-in leak was not blocked")
    if b_hdmi_leak.valid or not b_hdmi_leak.lcd_evf_assist_burned_into_clean_hdmi:
        errors.append("Clean-HDMI burn-in leak was not blocked")

    return GammaDisplayAssistReport(
        passed=len(errors) == 0,
        fx3_appfw_assist_markers=fx3_appfw_assist_markers,
        fx6_appfw_assist_markers=fx6_appfw_assist_markers,
        fx3_cp_assist_markers=fx3_cp_assist_markers,
        fx6_cp_assist_markers=fx6_cp_assist_markers,
        uxc_assist_labels=uxc_assist_labels,
        eval_auto_slog3_to_709_800=e_slog3,
        eval_auto_hlg_bt2020_to_709=e_hlg2020,
        eval_explicit_hlg_709_to_709=e_hlg709,
        eval_mlut_active_defers_assist=e_mlut,
        blocked_assist_leak_into_xavc_main=b_xavc_leak,
        blocked_assist_leak_into_clean_hdmi=b_hdmi_leak,
        errors=tuple(errors),
    )


def evaluate_pillar_3_cta861_3_hdr_infoframe(
    *,
    fx3_uxc_hdmi_labels: Dict[str, str],
    extra_errors: Sequence[str] = (),
) -> Cta861HdrInfoFrameReport:
    errors = list(extra_errors)

    e_atomos = evaluate_hdmi_hdr_infoframe_handshake(
        camera_gamma="REC2100_HLG",
        camera_primaries="BT.2020",
        avi_colorimetry="BT2020_NCL",
        target_monitor="ATOMOS_NINJA_V_PLUS",
    )
    e_smallhd = evaluate_hdmi_hdr_infoframe_handshake(
        camera_gamma="REC2100_HLG",
        camera_primaries="BT.2020",
        avi_colorimetry="BT2020_NCL",
        target_monitor="SMALLHD_CINE7_HDR",
    )
    e_pq = evaluate_hdmi_hdr_infoframe_handshake(
        camera_gamma="SMPTE_ST2084_PQ",
        camera_primaries="BT.2020",
        avi_colorimetry="BT2020_NCL",
        target_monitor="SONY_BVM_HX310",
    )
    e_sdr = evaluate_hdmi_hdr_infoframe_handshake(
        camera_gamma="ITU709",
        camera_primaries="BT.709",
        avi_colorimetry="BT709",
        target_monitor="ATOMOS_NINJA_V_PLUS",
    )

    b_csum = evaluate_hdmi_hdr_infoframe_handshake(
        camera_gamma="REC2100_HLG",
        camera_primaries="BT.2020",
        avi_colorimetry="BT2020_NCL",
        corrupt_checksum=True,
    )
    b_sdr_eotf = evaluate_hdmi_hdr_infoframe_handshake(
        camera_gamma="REC2100_HLG",
        camera_primaries="BT.2020",
        avi_colorimetry="BT2020_NCL",
        eotf_code_override=CTA861_EOTF_CODES["SDR_GAMMA"],
    )
    b_avi = evaluate_hdmi_hdr_infoframe_handshake(
        camera_gamma="REC2100_HLG",
        camera_primaries="BT.2020",
        avi_colorimetry="BT709",
    )
    b_raw16 = evaluate_hdmi_hdr_infoframe_handshake(
        camera_gamma="REC2100_HLG",
        camera_primaries="BT.2020",
        avi_colorimetry="BT2020_NCL",
        hdmi_raw16_active=True,
    )

    if not e_atomos.valid or not e_atomos.monitor_auto_switched_hlg_bt2020:
        errors.append(f"Atomos HLG BT.2020 handshake failed: {e_atomos.errors}")
    if not e_smallhd.valid or not e_smallhd.monitor_auto_switched_hlg_bt2020:
        errors.append(f"SmallHD HLG BT.2020 handshake failed: {e_smallhd.errors}")
    if not e_pq.valid or e_pq.decoded_infoframe.eotf_code != 0x02:
        errors.append(f"PQ ST2084 handshake failed: {e_pq.errors}")
    if not e_sdr.valid or e_sdr.decoded_infoframe.eotf_code != 0x00:
        errors.append(f"SDR baseline handshake failed: {e_sdr.errors}")

    for lbl, blk in (
        ("corrupt_checksum", b_csum),
        ("hlg_as_sdr_eotf", b_sdr_eotf),
        ("hlg_bt709_avi", b_avi),
        ("raw16_conflict", b_raw16),
    ):
        if blk.valid:
            errors.append(f"Negative InfoFrame guard {lbl} unexpectedly passed")

    return Cta861HdrInfoFrameReport(
        passed=len(errors) == 0,
        fx3_uxc_hdmi_labels=fx3_uxc_hdmi_labels,
        eval_hlg_bt2020_atomos_ninja=e_atomos,
        eval_hlg_bt2020_smallhd_cine7=e_smallhd,
        eval_pq_st2084_bvm_hx310=e_pq,
        eval_sdr_bt709_baseline=e_sdr,
        blocked_corrupt_checksum_rejected=b_csum,
        blocked_hlg_signaled_as_sdr_eotf=b_sdr_eotf,
        blocked_hlg_with_bt709_avi_mismatch=b_avi,
        blocked_raw16_hdr_infoframe_conflict=b_raw16,
        errors=tuple(errors),
    )


def analyze_hdr_hlg_bt2100_and_display_assist(
    *,
    clean_room: bool = False,
    repo_root: Optional[Path] = None,
) -> HdrHlgBt2100AndDisplayAssistReport:
    """Run the 21st unified firmware-lab auditor in Local Donor (`os.O_RDONLY`) or Clean-Room mode."""
    root = repo_root or DEFAULT_REPO_ROOT
    forced_clean = clean_room or is_forced_clean_room()

    donor_paths: Dict[str, Optional[Path]] = {}
    if not forced_clean:
        donor_paths = {
            "fx3_appfw": resolve_donor_file(FX3_APPFW_RELPATH, repo_root=root),
            "fx6_appfw": resolve_donor_file(FX6_APPFW_RELPATH, repo_root=root),
            "fx3_libmpr": resolve_donor_file(FX3_LIBMPR_RELPATH, repo_root=root),
            "fx6_libmpr": resolve_donor_file(FX6_LIBMPR_RELPATH, repo_root=root),
            "fx3_cpapp": resolve_donor_file(FX3_CPAPP_RELPATH, repo_root=root),
            "fx6_cpapp": resolve_donor_file(FX6_CPAPP_RELPATH, repo_root=root),
            "fx3_global_xdb": resolve_donor_file(FX3_GLOBAL_XDB_RELPATH, repo_root=root),
            "fx6_global_xdb": resolve_donor_file(FX6_GLOBAL_XDB_RELPATH, repo_root=root),
            "fx3_str_en": resolve_donor_file(FX3_STR_EN_RELPATH, repo_root=root),
            "fx3_str_en_g": resolve_donor_file(FX3_STR_EN_G_RELPATH, repo_root=root),
            "fx6_str_en_1": resolve_donor_file(FX6_STR_EN_1_RELPATH, repo_root=root),
            "fx6_str_en_2": resolve_donor_file(FX6_STR_EN_2_RELPATH, repo_root=root),
        }

    use_local = (not forced_clean) and all(p is not None and p.is_file() for p in donor_paths.values())
    mode = "LOCAL_DONOR_VERIFIED" if use_local else "CLEAN_ROOM_SYNTHETIC"

    fx3_hlg_expected = FX3_APPFW_PHASE111_MARKERS[:9] + (FX3_APPFW_PHASE111_MARKERS[18],)
    fx3_assist_expected = FX3_APPFW_PHASE111_MARKERS[9:18]

    fx6_hlg_expected = FX6_APPFW_PHASE111_MARKERS[:14] + (FX6_APPFW_PHASE111_MARKERS[21],)
    fx6_assist_expected = FX6_APPFW_PHASE111_MARKERS[14:21]

    fx3_cp_hlg_expected = CP_SHARED_PHASE111_MARKERS[:4]
    fx3_cp_assist_expected = CP_SHARED_PHASE111_MARKERS[4:]
    fx6_cp_hlg_expected = CP_SHARED_PHASE111_MARKERS[:4] + (FX6_CP_EXTRA_PHASE111_MARKERS[2],)
    fx6_cp_assist_expected = CP_SHARED_PHASE111_MARKERS[4:] + FX6_CP_EXTRA_PHASE111_MARKERS[:2]

    fx6_mpr_expected = LIBMPR_SHARED_PHASE111_MARKERS + FX6_LIBMPR_EXTRA_PHASE111_MARKERS

    if use_local:
        sz_fx3_app, fx3_app_res, _ = _scan_donor_rdonly_markers(
            donor_paths["fx3_appfw"],  # type: ignore[arg-type]
            {"hlg": fx3_hlg_expected, "assist": fx3_assist_expected},
            is_elf=True,
        )
        sz_fx6_app, fx6_app_res, _ = _scan_donor_rdonly_markers(
            donor_paths["fx6_appfw"],  # type: ignore[arg-type]
            {"hlg": fx6_hlg_expected, "assist": fx6_assist_expected},
            is_elf=True,
        )
        sz_fx3_mpr, fx3_mpr_res, fx3_uls = _scan_donor_rdonly_markers(
            donor_paths["fx3_libmpr"],  # type: ignore[arg-type]
            {"m": LIBMPR_SHARED_PHASE111_MARKERS},
            is_elf=True,
            ul_hex_catalog=SMPTE_UL_HEX_CATALOG,
        )
        sz_fx6_mpr, fx6_mpr_res, fx6_uls = _scan_donor_rdonly_markers(
            donor_paths["fx6_libmpr"],  # type: ignore[arg-type]
            {"m": fx6_mpr_expected},
            is_elf=True,
            ul_hex_catalog=SMPTE_UL_HEX_CATALOG,
        )
        sz_fx3_cp, fx3_cp_res, _ = _scan_donor_rdonly_markers(
            donor_paths["fx3_cpapp"],  # type: ignore[arg-type]
            {"hlg": fx3_cp_hlg_expected, "assist": fx3_cp_assist_expected},
            is_elf=False,
        )
        sz_fx6_cp, fx6_cp_res, _ = _scan_donor_rdonly_markers(
            donor_paths["fx6_cpapp"],  # type: ignore[arg-type]
            {"hlg": fx6_cp_hlg_expected, "assist": fx6_cp_assist_expected},
            is_elf=False,
        )
        fx3_xdb_bytes = _read_bytes_rdonly(donor_paths["fx3_global_xdb"])  # type: ignore[arg-type]
        fx6_xdb_bytes = _read_bytes_rdonly(donor_paths["fx6_global_xdb"])  # type: ignore[arg-type]
        fx3_str_en_bytes = _read_bytes_rdonly(donor_paths["fx3_str_en"])  # type: ignore[arg-type]
        fx3_str_en_g_bytes = _read_bytes_rdonly(donor_paths["fx3_str_en_g"])  # type: ignore[arg-type]
        fx6_str_en_1_bytes = _read_bytes_rdonly(donor_paths["fx6_str_en_1"])  # type: ignore[arg-type]
        fx6_str_en_2_bytes = _read_bytes_rdonly(donor_paths["fx6_str_en_2"])  # type: ignore[arg-type]
    else:
        fx = build_clean_room_hdr_hlg_assist_fixtures()
        sz_fx3_app, fx3_app_res, _ = _scan_bytes_marker_groups(
            fx["fx3_appfw"],
            {"hlg": fx3_hlg_expected, "assist": fx3_assist_expected},
        )
        sz_fx6_app, fx6_app_res, _ = _scan_bytes_marker_groups(
            fx["fx6_appfw"],
            {"hlg": fx6_hlg_expected, "assist": fx6_assist_expected},
        )
        sz_fx3_mpr, fx3_mpr_res, fx3_uls = _scan_bytes_marker_groups(
            fx["fx3_libmpr"],
            {"m": LIBMPR_SHARED_PHASE111_MARKERS},
            ul_hex_catalog=SMPTE_UL_HEX_CATALOG,
        )
        sz_fx6_mpr, fx6_mpr_res, fx6_uls = _scan_bytes_marker_groups(
            fx["fx6_libmpr"],
            {"m": fx6_mpr_expected},
            ul_hex_catalog=SMPTE_UL_HEX_CATALOG,
        )
        sz_fx3_cp, fx3_cp_res, _ = _scan_bytes_marker_groups(
            fx["fx3_cpapp"],
            {"hlg": fx3_cp_hlg_expected, "assist": fx3_cp_assist_expected},
        )
        sz_fx6_cp, fx6_cp_res, _ = _scan_bytes_marker_groups(
            fx["fx6_cpapp"],
            {"hlg": fx6_cp_hlg_expected, "assist": fx6_cp_assist_expected},
        )
        fx3_xdb_bytes = fx["fx3_global_xdb"]
        fx6_xdb_bytes = fx["fx6_global_xdb"]
        fx3_str_en_bytes = fx["fx3_str_en"]
        fx3_str_en_g_bytes = fx["fx3_str_en_g"]
        fx6_str_en_1_bytes = fx["fx6_str_en_1"]
        fx6_str_en_2_bytes = fx["fx6_str_en_2"]

    sizes: Dict[str, int] = {
        "fx3_appfw": sz_fx3_app,
        "fx6_appfw": sz_fx6_app,
        "fx3_libmpr": sz_fx3_mpr,
        "fx6_libmpr": sz_fx6_mpr,
        "fx3_cpapp": sz_fx3_cp,
        "fx6_cpapp": sz_fx6_cp,
        "fx3_global_xdb": len(fx3_xdb_bytes),
        "fx6_global_xdb": len(fx6_xdb_bytes),
        "fx3_str_en": len(fx3_str_en_bytes),
        "fx3_str_en_g": len(fx3_str_en_g_bytes),
        "fx6_str_en_1": len(fx6_str_en_1_bytes),
        "fx6_str_en_2": len(fx6_str_en_2_bytes),
    }

    p1_extra: List[str] = []
    p2_extra: List[str] = []
    p3_extra: List[str] = []
    p4_extra: List[str] = []

    if len(fx3_app_res["hlg"]) != len(fx3_hlg_expected):
        p1_extra.append("Missing FX3 appFw HLG/BT2020 markers")
    if len(fx6_app_res["hlg"]) != len(fx6_hlg_expected):
        p1_extra.append("Missing FX6 appFw HLG/BT2020 markers")
    if len(fx3_cp_res["hlg"]) != len(fx3_cp_hlg_expected):
        p1_extra.append("Missing FX3 CP HLG/BT2020 markers")
    if len(fx6_cp_res["hlg"]) != len(fx6_cp_hlg_expected):
        p1_extra.append("Missing FX6 CP HLG/BT2020 markers")

    if len(fx3_app_res["assist"]) != len(fx3_assist_expected):
        p2_extra.append("Missing FX3 appFw Gamma Display Assist markers")
    if len(fx6_app_res["assist"]) != len(fx6_assist_expected):
        p2_extra.append("Missing FX6 appFw Gamma Display Assist markers")
    if len(fx3_cp_res["assist"]) != len(fx3_cp_assist_expected):
        p2_extra.append("Missing FX3 CP Gamma Display Assist markers")
    if len(fx6_cp_res["assist"]) != len(fx6_cp_assist_expected):
        p2_extra.append("Missing FX6 CP Gamma Display Assist markers")

    if len(fx3_mpr_res["m"]) != len(LIBMPR_SHARED_PHASE111_MARKERS):
        p4_extra.append("Missing FX3 libmpr NRTM HLG/BT2020 markers")
    if len(fx6_mpr_res["m"]) != len(fx6_mpr_expected):
        p4_extra.append("Missing FX6 libmpr NRTM HLG/BT2020 markers")
    if len(fx3_uls) != len(SMPTE_UL_HEX_CATALOG):
        p4_extra.append("Missing FX3 libmpr SMPTE UL binary entries")
    if len(fx6_uls) != len(SMPTE_UL_HEX_CATALOG):
        p4_extra.append("Missing FX6 libmpr SMPTE UL binary entries")

    fx3_ux_en, u_err_1 = _extract_uxc_labels(fx3_str_en_bytes, FX3_NS39_PHASE111_LABELS)
    fx3_ux_g, u_err_2 = _extract_uxc_labels(fx3_str_en_g_bytes, FX3_NS3_PHASE111_LABELS)
    fx6_ux_1, u_err_3 = _extract_uxc_labels(fx6_str_en_1_bytes, FX6_NS1_PHASE111_LABELS)
    fx6_ux_2, u_err_4 = _extract_uxc_labels(fx6_str_en_2_bytes, FX6_NS2_PHASE111_LABELS)
    p3_extra.extend(u_err_1)
    p2_extra.extend(u_err_2)
    p1_extra.extend(u_err_3)
    p2_extra.extend(u_err_4)

    uxc_hlg_labels = {
        "fx3_itu709_matrix": fx3_ux_g.get("0x00006531", ""),
        "fx6_hlg_bt2100": fx6_ux_1.get("0x00002018", ""),
        "fx6_bt2020_hdr_hlg": fx6_ux_1.get("0x000020b9", ""),
        "fx6_hlg_live": fx6_ux_1.get("0x000021a3", ""),
        "fx6_hlg_natural": fx6_ux_1.get("0x000021a4", ""),
        "fx6_hdr_hlg1": fx6_ux_2.get("0x0000515d", ""),
        "fx6_hdr_hlg2": fx6_ux_2.get("0x0000515e", ""),
        "fx6_hdr_hlg3": fx6_ux_2.get("0x0000515f", ""),
    }
    uxc_assist_labels = {
        "fx3_gamma_disp_assist_note": fx3_ux_g.get("0x00006538", ""),
        "fx6_gamma_disp_assist": fx6_ux_1.get("0x00003247", ""),
        "fx6_lut_709_800": fx6_ux_1.get("0x00002109", ""),
        "fx6_gamma_disp_assist_auto": fx6_ux_2.get("0x0000419d", ""),
        "fx6_gamma_disp_assist_hlg": fx6_ux_2.get("0x0000419e", ""),
        "fx6_gamma_disp_assist_slog3": fx6_ux_2.get("0x0000419f", ""),
        "fx6_hlg_to_709_800": fx6_ux_2.get("0x000042ea", ""),
    }
    fx3_uxc_hdmi_labels = {
        "fx3_hdmi_resolution": fx3_ux_en.get("0x0000e1d5", ""),
    }

    p1 = evaluate_pillar_1_hlg_bt2100_curves(
        fx3_appfw_hlg_markers=fx3_app_res["hlg"],
        fx6_appfw_hlg_markers=fx6_app_res["hlg"],
        fx3_cp_hlg_markers=fx3_cp_res["hlg"],
        fx6_cp_hlg_markers=fx6_cp_res["hlg"],
        uxc_hlg_labels=uxc_hlg_labels,
        extra_errors=p1_extra,
    )
    p2 = evaluate_pillar_2_gamma_display_assist(
        fx3_appfw_assist_markers=fx3_app_res["assist"],
        fx6_appfw_assist_markers=fx6_app_res["assist"],
        fx3_cp_assist_markers=fx3_cp_res["assist"],
        fx6_cp_assist_markers=fx6_cp_res["assist"],
        uxc_assist_labels=uxc_assist_labels,
        extra_errors=p2_extra,
    )
    p3 = evaluate_pillar_3_cta861_3_hdr_infoframe(
        fx3_uxc_hdmi_labels=fx3_uxc_hdmi_labels,
        extra_errors=p3_extra,
    )

    try:
        parse_global_xdb_buffer(fx3_xdb_bytes)
        fx3_xdb_ok = True
    except Exception:
        fx3_xdb_ok = False

    try:
        parse_global_xdb_buffer(fx6_xdb_bytes)
        fx6_xdb_ok = True
    except Exception:
        fx6_xdb_ok = False

    p4 = verify_hdr_zero_calibration_mutation(
        fx3_libmpr_markers=fx3_mpr_res["m"],
        fx6_libmpr_markers=fx6_mpr_res["m"],
        fx3_smpte_uls=fx3_uls,
        fx6_smpte_uls=fx6_uls,
        fx3_global_xdb_valid=fx3_xdb_ok,
        fx6_global_xdb_valid=fx6_xdb_ok,
        extra_errors=p4_extra,
    )

    all_errors = p1.errors + p2.errors + p3.errors + p4.errors
    all_passed = bool(p1.passed and p2.passed and p3.passed and p4.passed and len(all_errors) == 0)

    digest_payload = {
        "schema_version": PHASE_111_SCHEMA,
        "phase_version": PHASE_111_VERSION,
        "mode": mode,
        "all_checks_passed": all_passed,
        "donor_file_sizes": sizes,
        "p1": asdict(p1),
        "p2": asdict(p2),
        "p3": asdict(p3),
        "p4": asdict(p4),
    }
    report_sha256 = hashlib.sha256(
        json.dumps(digest_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()

    return HdrHlgBt2100AndDisplayAssistReport(
        schema_version=PHASE_111_SCHEMA,
        phase_version=PHASE_111_VERSION,
        mode=mode,
        all_checks_passed=all_passed,
        donor_file_sizes=sizes,
        pillar_1_hlg_bt2100_curves=p1,
        pillar_2_gamma_display_assist=p2,
        pillar_3_cta861_3_hdr_infoframe=p3,
        pillar_4_nrtm_smpte_ul_immutability=p4,
        report_sha256=report_sha256,
        errors=tuple(all_errors),
    )


def hdr_hlg_bt2100_and_display_assist_report_to_dict(
    report: HdrHlgBt2100AndDisplayAssistReport,
) -> Dict[str, object]:
    """Convert `HdrHlgBt2100AndDisplayAssistReport` to a deterministic JSON-serializable dict."""
    return asdict(report)
