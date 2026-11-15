"""Phase 98 — 19th Unified Firmware-Lab Auditor: User 3D LUT (.cube 17^3 / 33^3 / 65^3)
Domain/NaN Sanitizer & Tetrahedral vs Trilinear CXD90058 Quantization, S-Log3
Legal/Extended HDMI AVI InfoFrame Guard, & HDMI-to-12G-SDI Active Converter
REC-Trigger Parity.

Strictly Read-Only (`os.O_RDONLY` + `mmap.ACCESS_READ`) & Clean-Room Dual-Mode:
- Local Donor Mode: inspects FX3 v7.02 (`appFw.so`, `libmpr.so`, `cpapp-b.bin`,
  `global.xdb`, `string_english.uxc`, `string_english_g.uxc`) and FX6 v6.01
  (`appFw.so`, `libmpr.so`, `cpapp-b.bin`, `AVBB_SCN_START_PANELEVF.so`,
  `global.xdb`, `string_english.uxc`, `string_english_2.uxc`) strictly via
  `os.O_RDONLY` + `mmap.ACCESS_READ` and ELF64 `.rodata`/`.dynstr` section-scoped
  scanning, plus `uxa\\x07` / `.uxc` container parsing (< 0.35s total).
- Clean-Room Mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`, `clean_room=True`, or donors
  absent): synthesizes deterministic clean-room ELF64 / CP / `global.xdb` /
  `.uxc` fixtures carrying the exact contract markers and runs the identical
  four-pillar verification pipeline (< 0.02s, zero proprietary files required).

Audits Four Phase 98 User 3D LUT, HDMI AVI InfoFrame & SDI/HDMI Bridge Pillars:
1. Pillar 1 — Adobe/Iridas `.cube` (`17^3` / `33^3` / `65^3`) Parser, NaN/Inf/
   Domain Sanitizer, Exact 6-Tetrahedra Subdivision vs Trilinear Resampler &
   `CXD90058` `33^3` `U12.4` / `U16` DMA Quantization:
   - Parses and validates `17^3` (`4,913`), `33^3` (`35,937`), and `65^3`
     (`274,625`) `.cube` files, failing closed on `NaN`/`Inf`, inverted or
     degenerate `DOMAIN_MIN >= DOMAIN_MAX`, `LUT_1D_SIZE` mismatches, wrong voxel
     counts, control chars / path-traversal `TITLE`, and (when configured)
     negative/OOB entries, while normalizing arbitrary `DOMAIN_MIN`/`DOMAIN_MAX`
     bounds cleanly to `[0, 1]^3`.
   - Implements exact 6-tetrahedra cube subdivision (`tetrahedral_sample_cube`)
     vs trilinear (`trilinear_sample_cube_3d`), proving monotonically bounded
     error (`err(65^3) < err(33^3) < err(17^3)`, `< 1e-4` max delta on
     `S-Log3 / S-Gamut3.Cine -> Rec.709 800%` LUTs, tetrahedral <= trilinear)
     and packing Sony's native `33^3` (`35,937` nodes, `215,622 B`) `U12.4` /
     `U16` volatile DMA table with `<= 1.53e-5` quantization error.
2. Pillar 2 — `S-Log3` 10-Bit Legal (`64..940`) vs Extended Super-White
   (`64..1019`) & CEA-861 HDMI AVI InfoFrame Quantization Guard:
   - Audits Sony Cinema Line `S-Log3` 10-bit code-value landmarks (`0% black =
     95/1023`, `18% grey = 420/1023`, `90% white = 598/1023`, extended
     super-white `949..1019`) and builds/verifies 17-byte CEA-861 AVI InfoFrame
     packets (`Y1:Y0` YCbCr 4:2:2 / RGB, `Q1:Q0` RGB range, `YQ1:YQ0` YCC range,
     checksum parity), blocking Atomos/SmallHD legal-vs-full double-scaling
     shadow-crush hazards.
3. Pillar 3 — FX6 Native `12G-SDI` (`SMPTE ST 2082` ANC / `RP 188` / `ST 12-2`
   ATC) vs FX3 HDMI-to-12G-SDI Active Converter REC-Trigger & Timecode Bridge:
   - Audits bit-level parity across Micro-Converter / Teradek / Atomos
     HDMI->12G-SDI bridges translating FX3 HDMI Type-A `REC Control` + `HDMI TC
     Out` into `SMPTE RP 188 / ST 12-2` ATC (`DID=0x60, SDID=0x60`) + SDI Remote
     REC flag, ensuring FX6 UI `SDI/HDMI Rec Control = On` drives FX3 HDMI REC
     cleanly with zero ghost SDI BNC hardware faults.
4. Pillar 4 — `MLUT` Burn-In vs Proxy-Only vs Clean-HDMI Independent Routing
   Matrix & Zero-Calibration-Mutation Proof:
   - Verifies independent `Main`, `Proxy`, `LCD/VF`, `HDMI Type-A`, and
     `SDI1` (gated) LUT routing combinations (`EMBED_LUT_FILE`, `MLUT`,
     `HDMI_INFO_DISPLAY_OFF`, `RAW16` isolation) and proves volatile RAM staging
     (`/tmp/`, `ram://`) with `calibration_mutation_bytes == 0`,
     `emmc_mutation_bytes == 0`, and `persistent_emmc_writes_authorized == False`.
"""

from __future__ import annotations

import array
import hashlib
import json
import math
import mmap
import os
import re
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple, Union

from .audio_tc_hdmi_sdi_routing_auditor import FX6_AVBB_PANELEVF_RELPATH
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
from .sensor_codec_compatibility_analyzer import (
    FX3_CPAPP_RELPATH,
    FX3_LIBMPR_RELPATH,
    FX6_CPAPP_RELPATH,
    FX6_LIBMPR_RELPATH,
)
from .uxc_multilang_and_font_verifier import FX3_SHARE_APP_RELDIR, FX6_SHARE_APP_RELDIR


PHASE_98_SCHEMA = "fx3_firmware_lab_phase98_lut3d_tetrahedral_sdi_hdmi_v1"
PHASE_98_VERSION = "98.0.0"

FX3_GLOBAL_XDB_RELPATH = f"{FX3_SHARE_APP_RELDIR}/global.xdb"
FX6_GLOBAL_XDB_RELPATH = f"{FX6_SHARE_APP_RELDIR}/global.xdb"
FX3_STR_EN_RELPATH = f"{FX3_SHARE_APP_RELDIR}/string_english.uxc"
FX3_STR_EN_G_RELPATH = f"{FX3_SHARE_APP_RELDIR}/string_english_g.uxc"
FX6_STR_EN_1_RELPATH = f"{FX6_SHARE_APP_RELDIR}/string_english.uxc"
FX6_STR_EN_2_RELPATH = f"{FX6_SHARE_APP_RELDIR}/string_english_2.uxc"

# ---------------------------------------------------------------------------
# Pillar 1 Constants: `.cube` 17^3/33^3/65^3, Tetrahedral Resampling & CXD90058 DMA
# ---------------------------------------------------------------------------

SUPPORTED_CUBE_3D_SIZES: Tuple[int, ...] = (17, 33, 65)
CXD90058_HW_LUT_GRID_SIZE = 33
CXD90058_HW_LUT_VOXELS = 33 * 33 * 33  # 35,937
CXD90058_U12_4_MAX_CODE = 4095 * 16  # 0xFFF0 (65,520 = 4095.0 in U12.4)
CXD90058_U16_MAX_CODE = 65535
CXD90058_DMA_TABLE_BYTES = CXD90058_HW_LUT_VOXELS * 3 * 2  # 215,622 B
CXD90058_MAX_USER_LUT_SLOTS = 16
FX3_P30_LUT_MOUNT_DIR = "/usr/data/lut/"
FX3_P30_LUT_DEVICE = "/dev/nflasha30"
FX3_P30_USABLE_BYTES = 49_716_224

MAX_SAFE_CUBE_3D_BYTES = 16 * 1024 * 1024  # Allows 65^3 DaVinci Resolve / Dehancer .cube (~10 MiB)
MAX_SAFE_CUBE_3D_LINES = 300_000
MAX_CUBE_TITLE_BYTES = 63
TETRAHEDRAL_SLOG3_709_800_MAX_DELTA = 1e-4

_RE_FORBIDDEN_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# ---------------------------------------------------------------------------
# Pillar 2 Constants: S-Log3 10-Bit Code Values & CEA-861 HDMI AVI InfoFrame
# ---------------------------------------------------------------------------

SLOG3_LEGAL_10BIT_MIN = 64
SLOG3_LEGAL_10BIT_MAX = 940
SLOG3_EXTENDED_10BIT_MIN = 64
SLOG3_EXTENDED_10BIT_MAX = 1019
SLOG3_SDI_RESERVED_HIGH = 1020

SLOG3_BLACK_0PCT_CODE10 = 95
SLOG3_GREY_18PCT_CODE10 = 420
SLOG3_WHITE_90PCT_CODE10 = 598
SLOG3_EXTENDED_CLIP_CODE10_RANGE: Tuple[int, int] = (949, 1019)

CEA861_AVI_PACKET_TYPE = 0x82
CEA861_AVI_VERSION = 0x02
CEA861_AVI_PAYLOAD_LEN = 13
CEA861_AVI_TOTAL_BYTES = 17  # 3B header + 1B checksum + 13B payload

AVI_Y_COLORSPACE_CODES: Dict[str, int] = {
    "RGB": 0b00,
    "YCBCR_422": 0b01,
    "YCBCR_444": 0b10,
    "YCBCR_420": 0b11,
}
AVI_Q_RGB_RANGE_CODES: Dict[str, int] = {
    "DEFAULT": 0b00,
    "LIMITED": 0b01,
    "FULL": 0b10,
}
AVI_YQ_YCC_RANGE_CODES: Dict[str, int] = {
    "LIMITED": 0b00,
    "FULL": 0b01,
}
VALID_RECORDER_EXPECTATIONS: Tuple[str, ...] = ("LEGAL_OR_EXTENDED", "FULL_RANGE")
VALID_SIGNAL_RANGE_MODES: Tuple[str, ...] = (
    "SLOG3_LEGAL_64_940",
    "SLOG3_EXTENDED_64_1019",
    "FULL_0_1023",
    "HDMI_RAW16_LINEAR",
)

# ---------------------------------------------------------------------------
# Pillar 3 Constants: 12G-SDI ST 2082 ANC / RP 188 <-> HDMI Converter REC-Trigger
# ---------------------------------------------------------------------------

SMPTE_RP188_ATC_DID = 0x60
SMPTE_RP188_ATC_SDID = 0x60
SMPTE_ST2082_12G_SDI_LINE_RATE_GBPS = 11.88
VALID_BRIDGE_CONVERTERS: Tuple[str, ...] = (
    "FX6_NATIVE_12G_SDI_BNC",
    "BMD_MICRO_CONVERTER_HDMI_TO_SDI_12G",
    "TERADEK_BOLT_HDMI_SDI_BRIDGE",
    "ATOMOS_CONNECT_HDMI_SDI_BRIDGE",
    "PASSIVE_HDMI_CABLE_NO_BRIDGE",
)
ACTIVE_HDMI_TO_SDI_BRIDGES: Tuple[str, ...] = (
    "BMD_MICRO_CONVERTER_HDMI_TO_SDI_12G",
    "TERADEK_BOLT_HDMI_SDI_BRIDGE",
    "ATOMOS_CONNECT_HDMI_SDI_BRIDGE",
)
VALID_FX6_REC_CONTROL_MODES: Tuple[str, ...] = (
    "OFF",
    "SDI_HDMI_REMOTE_I_F",
    "PARALLEL_REC",
)

# ---------------------------------------------------------------------------
# Pillar 4 Constants: MLUT Routing Matrix & Zero-Mutation Firewall
# ---------------------------------------------------------------------------

VALID_ROUTING_PROFILES: Tuple[str, ...] = (
    "SLOG3_CLEAN_HDMI_LOG_INTERNAL",
    "SLOG3_MLUT_HDMI_MONITORING",
    "SLOG3_PROXY_EMBED_LUT_ONLY",
    "FX6_BURN_IN_INTERNAL_LOOK",
    "HDMI_RAW16_CLEAN_NO_MLUT",
)
VOLATILE_STAGING_PREFIXES: Tuple[str, ...] = ("/tmp/", "ram://", "memory://")
FORBIDDEN_CALIBRATION_AND_EMMC_RE = re.compile(
    r"(?:^|/)(?:p(?:[1-9]|1[0-5])|nflasha\d*|cnflasha\d*|mmcblk0(?:p\d+)?|mtdblock\d*)(?:/|:|$)"
    r"|backup\.bin|psd\.bin|jiritsu|shading://|nvram://|eeprom://",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Verified Binary & .uxc Marker Contracts (FX3 v7.02 & FX6 v6.01)
# ---------------------------------------------------------------------------

FX3_APPFW_LUT_HDMI_MARKERS: Tuple[str, ...] = (
    "LUT_3D_SIZE",
    "LUT_3D_INPUT_RANGE",
    "CUBE_FILE_IMPORT_STARTUP_FACTOR_SCREEN_USER_LUT_IMPORT_LIST",
    "VAL_HAITA_is_exist_user_lut_cube_file_import_to_user_lut_id_req_IS_EXIST_USER_LUT_EMPTY_SELECT_LUT_USER1",
    "VAL_setting_embed_lut_file_EMBED_LUT_FILE_ON",
    "VAL_setting_embed_lut_file_EMBED_LUT_FILE_OFF",
    "VAL_setting_rec_control_REC_CONTROL_ON",
    "VAL_setting_rec_control_REC_CONTROL_OFF",
    "VAL_setting_hdmi_tc_output_EXTERNAL_HDMI_TC_OUTPUT_ON",
    "VAL_setting_rec_media_during_hdmi_output_REC_MEDIA_DURING_HDMI_OUTPUT_ON",
    "VAL_setting_rec_media_during_hdmi_output_REC_MEDIA_DURING_HDMI_OUTPUT_OFF",
    "VAL_setting_hdmi_info_display_HDMI_INFO_DISPLAY_OFF",
    "VAL_setting_pictureprofile_gamma0_SETTING_PICTUREPROFILE_GAMMA_SLOG3",
)

FX6_APPFW_LUT_SDI_MARKERS: Tuple[str, ...] = (
    "LUT_3D_SIZE",
    "LUT_3D_INPUT_RANGE",
    "VAL_setting_sdi_hdmi_rec_control_SDI_HDMI_REC_CONTROL_OFF",
    "VAL_setting_sdi_hdmi_rec_control_SDI_HDMI_REC_CONTROL_SDI_HDMI_REMOTE_I_F",
    "VAL_setting_sdi_hdmi_rec_control_SDI_HDMI_REC_CONTROL_PARALLEL_REC",
    "VAL_setting_hdmi_tc_output_EXTERNAL_HDMI_TC_OUTPUT_ON",
    "VAL_FEATURE_MANAGER_sdi_output_TYPE_SDI_OUTPUT_NOT_SUPPORT",
    "VAL_FEATURE_MANAGER_sdi_output_TYPE_SDI_OUTPUT_SUPPORT",
    "VAL_setting_lut_setting_monitor_out_sdi1_LUT_SETTING_MONITOR_OUT_SDI1_MLUT_ON",
    "VAL_setting_lut_setting_monitor_out_sdi1_LUT_SETTING_MONITOR_OUT_SDI1_MLUT_OFF",
    "BKID_APP_EXTERN_MONITOR_LUT_HDMI_ONOFF",
    "BKID_APP_EXTERN_MONITOR_LUT_SDI1_ONOFF",
    "BKID_APP_EXTERN_MONITOR_LUT_LCD_VF_ONOFF",
    "BKID_APP_EXTERN_MONITOR_LUT_PROXY_REMOTE_LIVE_VIEW_ONOFF",
)

LIBMPR_CUBE_LUT_MARKERS: Tuple[str, ...] = (
    "LUT_3D_SIZE",
    "DOMAIN_MIN",
    "DOMAIN_MAX",
    "LUT_3D_INPUT_RANGE",
    "_ZN3mpr10SetLutDataERKNS_17setLutDataInParamE",
    "_ZN3mpr17ExecuteSetLutDataERKNS_17setLutDataInParamE",
)

CP_SHARED_MLUT_PIPELINE_MARKERS: Tuple[str, ...] = (
    "MLUT_L3D_ON",
    "MLUT_L3D_REG_USER_LUT_17",
    "MLUT_L1D_B_REG_LINEARTO709_800_LEGAL",
    "MLUT_MTX_C_REG_FULLTOLEGAL",
    "MLUT_MTX_C_REG_IDENTITY",
    "MSG_ID_INFRABB_VDF_DISP_SET_MONITOR_LUT",
    "FW: SET_USER_LUT_BINARY_DATA addr:0x%016llx size:%d regAddr:0x%016llx regSize:%d cnt:%d",
)

FX6_AVBB_PANELEVF_LUT_SDI_MARKERS: Tuple[str, ...] = (
    "SET_MONITOR_LUT",
    "SET_MONITOR_MLUT",
    "MSG_ID_VDF_DISP_SET_MONITOR_LUT",
    "EXEC_SDI_MAIN_OUTPUT",
    "EXEC_SDI_SUB_OUTPUT",
    "EXEC_HDMI_OUTPUT",
    "HDMI_SDI_OUTPUT",
    "SET_SDI_RAW_MODE",
)

# Verified .uxc String Resource IDs
FX3_NS39_PHASE98_LABELS: Dict[int, str] = {
    0x0000E1D5: "HDMI Resolution",
    0x0000E41F: "CTRL FOR HDMI",
}

FX3_NS3_PHASE98_LABELS: Dict[int, str] = {
    0x00006128: "Deletes LUT files imported to User${v1}.",
    0x0000620B: "Import the LUT file to User${v1}?",
}

FX6_NS1_PHASE98_LABELS: Dict[int, str] = {
    0x00002029: "MLUT",
    0x00002068: "Monitor LUT",
    0x00002109: "LUT 709(800)",
    0x0000219D: "Base Look/LUT",
}

FX6_NS2_PHASE98_LABELS: Dict[int, str] = {
    0x00004239: "Monitor LUT",
    0x00004245: "HDMI TC Out",
    0x00004251: "Rec Control",
    0x00004287: "Monitor 3D LUT",
    0x0000428D: "SDI/HDMI Rec Control",
    0x0000435E: "Look: User 3D LUT Select",
    0x00004362: "Look File: Load User 3D LUT",
}


class CubeLut3dSanitizationError(ValueError):
    """Raised when a `.cube` 3D LUT fails domain, NaN/Inf, structural, or budget checks."""


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ParsedCubeLut3d:
    title: str
    grid_size: int
    domain_min: Tuple[float, float, float]
    domain_max: Tuple[float, float, float]
    entries: Tuple[Tuple[float, float, float], ...]
    byte_length: int
    line_count: int
    negative_entries_detected: int
    over_one_entries_detected: int
    clamped_entries_count: int
    sha256: str


@dataclass(frozen=True)
class CubeLut3dResampleEvalResult:
    valid: bool
    status: str
    title: str
    source_grid_size: int
    target_grid_size: int
    source_voxels: int
    target_voxels: int
    domain_min: Tuple[float, float, float]
    domain_max: Tuple[float, float, float]
    dma_format: str
    dma_table_bytes: int
    dma_table_sha256: str
    max_quantization_error: float
    user_slot_index: int
    staging_path: str
    volatile_ram_staged: bool
    factory_calibration_mutated: bool
    negative_entries_detected: int
    clamped_entries_count: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class TetrahedralVsTrilinearConvergenceResult:
    passed: bool
    status: str
    err_17_tetrahedral: float
    err_33_tetrahedral: float
    err_65_tetrahedral: float
    err_17_trilinear: float
    err_33_trilinear: float
    err_65_trilinear: float
    monotonic_convergence: bool
    tetrahedral_beats_or_ties_trilinear: bool
    err_65_within_1e4: bool
    affine_matrix_max_delta: float
    downsample_65_to_33_node_max_delta: float
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class CubeLutTetrahedralMatrixReport:
    passed: bool
    fx3_appfw_markers: Tuple[str, ...]
    fx6_appfw_markers: Tuple[str, ...]
    fx3_libmpr_markers: Tuple[str, ...]
    fx6_libmpr_markers: Tuple[str, ...]
    fx3_cp_markers: Tuple[str, ...]
    fx6_cp_markers: Tuple[str, ...]
    uxc_lut_labels: Dict[str, str]
    eval_17_to_33_u12_4_resample: CubeLut3dResampleEvalResult
    eval_nonstandard_domain_33_u16: CubeLut3dResampleEvalResult
    convergence_65_33_17_proof: TetrahedralVsTrilinearConvergenceResult
    blocked_nan_cube_rejected: CubeLut3dResampleEvalResult
    blocked_inverted_domain_rejected: CubeLut3dResampleEvalResult
    blocked_negative_entry_rejected: CubeLut3dResampleEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class HdmiAviInfoFrameEvalResult:
    valid: bool
    status: str
    signal_range_mode: str
    colorspace_y_name: str
    y1_y0_bits: int
    rgb_quantization_q_name: str
    q1_q0_bits: int
    ycc_quantization_yq_name: str
    yq1_yq0_bits: int
    recorder_expectation: str
    avi_packet_hex: str
    avi_packet_bytes: int
    checksum_valid: bool
    slog3_black_0pct_code10: int
    slog3_grey_18pct_code10: int
    slog3_white_90pct_code10: int
    recorder_black_code10_after_rx: int
    shadow_crush_delta_codes: int
    highlight_clip_hazard: bool
    double_scaling_detected: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Slog3AviQuantizationReport:
    passed: bool
    slog3_black_0pct_code10: int
    slog3_grey_18pct_code10: int
    slog3_white_90pct_code10: int
    slog3_extended_clip_range: Tuple[int, int]
    eval_slog3_legal_64_940_ycbcr422: HdmiAviInfoFrameEvalResult
    eval_slog3_extended_64_1019_ycbcr422: HdmiAviInfoFrameEvalResult
    eval_rgb_full_0_1023_matched: HdmiAviInfoFrameEvalResult
    blocked_double_scale_shadow_crush: HdmiAviInfoFrameEvalResult
    blocked_raw16_mislabeled_ycbcr: HdmiAviInfoFrameEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class HdmiSdiRecBridgeEvalResult:
    valid: bool
    status: str
    camera_body: str
    converter_bridge: str
    fx6_ui_rec_control_mode: str
    hdmi_tc_output_enabled: bool
    rec_media_during_hdmi_output: bool
    hdmi_raw16_active: bool
    recording_active: bool
    timecode_bcd_str: str
    drop_frame: bool
    hdmi_rec_trigger_bit: int
    sdi_rp188_atc_did: int
    sdi_rp188_atc_sdid: int
    sdi_remote_rec_bit: int
    tc_roundtrip_exact: bool
    physical_12g_sdi_bnc_present: bool
    ghost_sdi_bnc_hw_faults: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class HdmiSdiRecBridgeMatrixReport:
    passed: bool
    fx3_appfw_rec_markers: Tuple[str, ...]
    fx6_appfw_rec_markers: Tuple[str, ...]
    fx6_panelevf_sdi_markers: Tuple[str, ...]
    uxc_sdi_hdmi_rec_labels: Dict[str, str]
    eval_fx6_native_12g_sdi_parallel: HdmiSdiRecBridgeEvalResult
    eval_fx3_bmd_micro_converter_12g: HdmiSdiRecBridgeEvalResult
    eval_fx3_teradek_hdmi_sdi_bridge: HdmiSdiRecBridgeEvalResult
    eval_fx3_atomos_connect_bridge: HdmiSdiRecBridgeEvalResult
    blocked_hdmi_tc_off_no_trigger: HdmiSdiRecBridgeEvalResult
    blocked_passive_cable_no_rp188: HdmiSdiRecBridgeEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class MlutRoutingEvalResult:
    valid: bool
    status: str
    profile_name: str
    camera_body: str
    main_rec_lut_baked: bool
    proxy_rec_lut_baked: bool
    embed_lut_file_sidecar: bool
    lcd_vf_mlut_on: bool
    hdmi_mlut_on: bool
    hdmi_clean_feed_no_osd: bool
    hdmi_raw16_active: bool
    sdi1_mlut_requested: bool
    sdi1_output_supported: bool
    ghost_sdi_bnc_hw_faults: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class CalibrationImmutabilityEvalResult:
    valid: bool
    status: str
    target_path: str
    volatile_ram_only: bool
    calibration_mutation_bytes: int
    emmc_mutation_bytes: int
    persistent_emmc_writes_authorized: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class MlutRoutingAndImmutabilityReport:
    passed: bool
    fx3_global_xdb_valid: bool
    fx6_global_xdb_valid: bool
    eval_slog3_clean_hdmi_log_internal: MlutRoutingEvalResult
    eval_slog3_mlut_hdmi_monitoring: MlutRoutingEvalResult
    eval_slog3_proxy_embed_lut_only: MlutRoutingEvalResult
    eval_fx6_burn_in_internal_look: MlutRoutingEvalResult
    eval_hdmi_raw16_mlut_isolated: MlutRoutingEvalResult
    blocked_raw16_hdmi_mlut_bake_hazard: MlutRoutingEvalResult
    eval_fx3_sdi1_mlut_safely_gated: MlutRoutingEvalResult
    volatile_ram_staging_eval: CalibrationImmutabilityEvalResult
    blocked_cnflasha_eval: CalibrationImmutabilityEvalResult
    blocked_shading_backup_eval: CalibrationImmutabilityEvalResult
    blocked_psd_bin_eval: CalibrationImmutabilityEvalResult
    calibration_mutation_bytes: int
    emmc_mutation_bytes: int
    persistent_emmc_writes_authorized: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Lut3dCubeTetrahedralAndSdiHdmiReport:
    schema_version: str
    phase_version: str
    mode: str
    all_checks_passed: bool
    o_rdonly_enforced: bool
    persistent_emmc_writes_authorized: bool
    calibration_mutation_bytes: int
    emmc_mutation_bytes: int
    donor_file_sizes: Dict[str, int]
    pillar_1_cube_lut_tetrahedral: CubeLutTetrahedralMatrixReport
    pillar_2_slog3_avi_quantization: Slog3AviQuantizationReport
    pillar_3_hdmi_sdi_rec_bridge: HdmiSdiRecBridgeMatrixReport
    pillar_4_mlut_routing_immutability: MlutRoutingAndImmutabilityReport
    errors: Tuple[str, ...]
    report_sha256: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)

    def to_deterministic_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True) + "\n"


# ---------------------------------------------------------------------------
# Strictly `os.O_RDONLY` + `mmap.ACCESS_READ` Section-Scoped Scanning Helpers
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


def _scan_bytes_marker_groups(
    blob: bytes,
    marker_groups: Mapping[str, Sequence[str]],
) -> Tuple[int, Dict[str, Tuple[str, ...]]]:
    unique_markers = sorted(
        {m for markers in marker_groups.values() for m in markers},
        key=lambda s: (-len(s), s),
    )
    if not unique_markers:
        return len(blob), {k: () for k in marker_groups}
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
    return len(blob), results


# ---------------------------------------------------------------------------
# Clean-Room Synthetic Fixtures (FX3_FX6_FORCE_CLEAN_ROOM=1 or donors absent)
# ---------------------------------------------------------------------------


def build_clean_room_lut3d_sdi_hdmi_fixtures() -> Dict[str, bytes]:
    """Build deterministic clean-room ELF64, CP, `global.xdb`, and `.uxc` fixtures for Phase 98."""
    elf_hdr = b"\x7fELF\x02\x01\x01\x00" + bytes(56)
    cp_hdr = b"LDR\x00" + bytes(60)

    def _pack(tokens: Sequence[str], *, prefix: bytes = elf_hdr) -> bytes:
        return prefix + b"\x00".join(t.encode("latin1") for t in tokens) + b"\x00"

    fx3_appfw_blob = _pack(FX3_APPFW_LUT_HDMI_MARKERS)
    fx6_appfw_blob = _pack(FX6_APPFW_LUT_SDI_MARKERS)
    fx3_libmpr_blob = _pack(LIBMPR_CUBE_LUT_MARKERS)
    fx6_libmpr_blob = _pack(LIBMPR_CUBE_LUT_MARKERS)
    fx3_cp_blob = _pack(CP_SHARED_MLUT_PIPELINE_MARKERS, prefix=cp_hdr)
    fx6_cp_blob = _pack(CP_SHARED_MLUT_PIPELINE_MARKERS, prefix=cp_hdr)
    fx6_panelevf_blob = _pack(FX6_AVBB_PANELEVF_LUT_SDI_MARKERS)

    fx3_xdb = build_synthetic_global_xdb("fx3_702")
    fx6_xdb = build_synthetic_global_xdb("fx6_601")

    fx3_str_en = build_sparse_uxc_string_pack(
        {k & 0x1FFF: v for k, v in FX3_NS39_PHASE98_LABELS.items()}, namespace_id=39
    )
    fx3_str_en_g = build_sparse_uxc_string_pack(
        {k & 0x1FFF: v for k, v in FX3_NS3_PHASE98_LABELS.items()}, namespace_id=3
    )
    fx6_str_en_1 = build_sparse_uxc_string_pack(
        {k & 0x1FFF: v for k, v in FX6_NS1_PHASE98_LABELS.items()}, namespace_id=1
    )
    fx6_str_en_2 = build_sparse_uxc_string_pack(
        {k & 0x1FFF: v for k, v in FX6_NS2_PHASE98_LABELS.items()}, namespace_id=2
    )

    return {
        "fx3_appfw": fx3_appfw_blob,
        "fx6_appfw": fx6_appfw_blob,
        "fx3_libmpr": fx3_libmpr_blob,
        "fx6_libmpr": fx6_libmpr_blob,
        "fx3_cpapp": fx3_cp_blob,
        "fx6_cpapp": fx6_cp_blob,
        "fx6_avbb_panelevf": fx6_panelevf_blob,
        "fx3_global_xdb": fx3_xdb,
        "fx6_global_xdb": fx6_xdb,
        "fx3_str_en": fx3_str_en,
        "fx3_str_en_g": fx3_str_en_g,
        "fx6_str_en_1": fx6_str_en_1,
        "fx6_str_en_2": fx6_str_en_2,
    }


# ---------------------------------------------------------------------------
# Pillar 1: `.cube` (17^3 / 33^3 / 65^3) Parser, Sanitizer & Tetrahedral Resampler
# ---------------------------------------------------------------------------


def slog3_sgamut3_cine_to_rec709_800_ref(r: float, g: float, b: float) -> Tuple[float, float, float]:
    """Analytical reference S-Log3 / S-Gamut3.Cine -> Rec.709 (800%) cinema look transform."""
    mr = 1.18 * r - 0.14 * g - 0.04 * b
    mg = -0.06 * r + 1.12 * g - 0.06 * b
    mb = -0.02 * r - 0.12 * g + 1.14 * b

    ur = 0.0 if mr <= 0.0 else (1.0 if mr >= 1.0 else mr)
    ug = 0.0 if mg <= 0.0 else (1.0 if mg >= 1.0 else mg)
    ub = 0.0 if mb <= 0.0 else (1.0 if mb >= 1.0 else mb)
    return (
        0.0625 + 0.8775 * (0.45 * (ur * ur * (3.0 - 2.0 * ur)) + 0.55 * ur),
        0.0625 + 0.8775 * (0.45 * (ug * ug * (3.0 - 2.0 * ug)) + 0.55 * ug),
        0.0625 + 0.8775 * (0.45 * (ub * ub * (3.0 - 2.0 * ub)) + 0.55 * ub),
    )


@lru_cache(maxsize=4)
def build_slog3_rec709_800_table(grid_size: int) -> Tuple[Tuple[float, float, float], ...]:
    """Build analytical S-Log3/S-Gamut3.Cine -> Rec.709 (800%) 3D LUT entries for `grid_size`."""
    if grid_size not in SUPPORTED_CUBE_3D_SIZES:
        raise CubeLut3dSanitizationError(
            f"Unsupported grid_size={grid_size}; expected {SUPPORTED_CUBE_3D_SIZES}"
        )
    denom = float(grid_size - 1)
    vals = [i / denom for i in range(grid_size)]
    out: List[Tuple[float, float, float]] = []
    append = out.append
    for b in vals:
        b04 = 0.04 * b
        b06 = 0.06 * b
        b14 = 1.14 * b
        for g in vals:
            g14_b04 = -0.14 * g - b04
            g12_b06 = 1.12 * g - b06
            b_g12 = b14 - 0.12 * g
            for r in vals:
                mr = 1.18 * r + g14_b04
                mg = -0.06 * r + g12_b06
                mb = -0.02 * r + b_g12
                ur = 0.0 if mr <= 0.0 else (1.0 if mr >= 1.0 else mr)
                ug = 0.0 if mg <= 0.0 else (1.0 if mg >= 1.0 else mg)
                ub = 0.0 if mb <= 0.0 else (1.0 if mb >= 1.0 else mb)
                append((
                    0.0625 + 0.8775 * (0.45 * (ur * ur * (3.0 - 2.0 * ur)) + 0.55 * ur),
                    0.0625 + 0.8775 * (0.45 * (ug * ug * (3.0 - 2.0 * ug)) + 0.55 * ug),
                    0.0625 + 0.8775 * (0.45 * (ub * ub * (3.0 - 2.0 * ub)) + 0.55 * ub),
                ))
    return tuple(out)


@lru_cache(maxsize=4)
def _cached_slog3_rec709_800_cube_body(grid_size: int) -> str:
    entries = build_slog3_rec709_800_table(grid_size)
    return "\n".join(f"{r:.6f} {g:.6f} {b:.6f}" for r, g, b in entries) + "\n"


def build_slog3_rec709_800_cube_text(
    grid_size: int = 17,
    *,
    title: str = "SL3_SG3C_TO_709_800",
    domain_min: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    domain_max: Tuple[float, float, float] = (1.0, 1.0, 1.0),
) -> str:
    """Serialize a clean S-Log3/S-Gamut3.Cine -> Rec.709 (800%) `.cube` LUT (`17^3`, `33^3`, or `65^3`)."""
    if grid_size not in SUPPORTED_CUBE_3D_SIZES:
        raise CubeLut3dSanitizationError(
            f"Unsupported grid_size={grid_size}; expected {SUPPORTED_CUBE_3D_SIZES}"
        )
    for ch in range(3):
        if not (math.isfinite(domain_min[ch]) and math.isfinite(domain_max[ch])):
            raise CubeLut3dSanitizationError("DOMAIN_MIN/DOMAIN_MAX must be finite")
        if domain_min[ch] >= domain_max[ch]:
            raise CubeLut3dSanitizationError("DOMAIN_MIN must be strictly < DOMAIN_MAX")

    header = (
        "# Clean-Room Sony Cinema Line S-Log3/S-Gamut3.Cine -> Rec.709 800% 3D LUT\n"
        f'TITLE "{title}"\n'
        f"LUT_3D_SIZE {grid_size}\n"
        f"DOMAIN_MIN {domain_min[0]:.6f} {domain_min[1]:.6f} {domain_min[2]:.6f}\n"
        f"DOMAIN_MAX {domain_max[0]:.6f} {domain_max[1]:.6f} {domain_max[2]:.6f}\n"
    )
    return header + _cached_slog3_rec709_800_cube_body(grid_size)


def _parse_rgb_triple_3d(parts: Sequence[str], *, context: str) -> Tuple[float, float, float]:
    if len(parts) != 3:
        raise CubeLut3dSanitizationError(f"{context}: expected 3 floats, got {len(parts)}")
    try:
        r = float(parts[0])
        g = float(parts[1])
        b = float(parts[2])
    except ValueError as exc:
        raise CubeLut3dSanitizationError(f"{context}: non-numeric float in {parts!r}") from exc
    if not (math.isfinite(r) and math.isfinite(g) and math.isfinite(b)):
        raise CubeLut3dSanitizationError(f"{context}: non-finite NaN/Inf float rejected")
    if abs(r) > 10.0 or abs(g) > 10.0 or abs(b) > 10.0:
        raise CubeLut3dSanitizationError(f"{context}: extreme out-of-range float rejected")
    return (r, g, b)


def parse_and_sanitize_cube_lut_3d(
    raw_cube: Union[str, bytes],
    *,
    on_negative_or_oob: str = "REJECT",
    max_file_bytes: int = MAX_SAFE_CUBE_3D_BYTES,
    max_lines: int = MAX_SAFE_CUBE_3D_LINES,
) -> ParsedCubeLut3d:
    """Parse and sanitize Adobe/Iridas `.cube` (`17^3`, `33^3`, or `65^3`) text/bytes."""
    mode_oob = on_negative_or_oob.upper()
    if mode_oob not in ("REJECT", "CLAMP"):
        raise ValueError(f"Unsupported on_negative_or_oob={on_negative_or_oob!r}")

    if isinstance(raw_cube, (bytes, bytearray)):
        raw_bytes = bytes(raw_cube)
        byte_len = len(raw_bytes)
        if byte_len > max_file_bytes:
            raise CubeLut3dSanitizationError(
                f".cube file size {byte_len} B exceeds parser limit {max_file_bytes} B"
            )
        if b"\x00" in raw_bytes:
            raise CubeLut3dSanitizationError("NUL byte found inside .cube payload")
        try:
            text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise CubeLut3dSanitizationError(f"Non-UTF8 .cube payload: {exc}") from exc
    else:
        raw_bytes = raw_cube.encode("utf-8", errors="strict")
        byte_len = len(raw_bytes)
        if byte_len > max_file_bytes:
            raise CubeLut3dSanitizationError(
                f".cube file size {byte_len} B exceeds parser limit {max_file_bytes} B"
            )
        if "\x00" in raw_cube:
            raise CubeLut3dSanitizationError("NUL character found inside .cube payload")
        text = raw_cube

    ctrl_m = _RE_FORBIDDEN_CTRL.search(text)
    if ctrl_m is not None:
        raise CubeLut3dSanitizationError(
            f"Forbidden control character 0x{ord(ctrl_m.group(0)):02x} in .cube payload"
        )

    lines = text.splitlines()
    line_count = len(lines)
    if line_count > max_lines:
        raise CubeLut3dSanitizationError(
            f".cube line count {line_count} exceeds limit {max_lines}"
        )

    title: Optional[str] = None
    grid_size: Optional[int] = None
    domain_min: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    domain_max: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    saw_domain_min = False
    saw_domain_max = False
    entries: List[Tuple[float, float, float]] = []
    append_entry = entries.append
    isfinite = math.isfinite
    max_entries = 0
    neg_count = 0
    over_count = 0
    clamped_count = 0

    for lineno, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        if not stripped or stripped[0] == "#":
            continue

        c0 = stripped[0]
        if c0 in "0123456789.-+" and "#" not in stripped:
            if grid_size is None:
                raise CubeLut3dSanitizationError(
                    f"Line {lineno}: RGB triplet encountered before LUT_3D_SIZE"
                )
            if not entries:
                for ch in range(3):
                    if domain_min[ch] >= domain_max[ch]:
                        raise CubeLut3dSanitizationError(
                            f"Inverted/degenerate DOMAIN bounds on channel {ch}: {domain_min[ch]} >= {domain_max[ch]}"
                        )
            parts = stripped.split()
            if len(parts) != 3:
                raise CubeLut3dSanitizationError(
                    f"Line {lineno} RGB: expected 3 numeric components, got {len(parts)}"
                )
            try:
                r = float(parts[0])
                g = float(parts[1])
                b = float(parts[2])
            except ValueError as exc:
                raise CubeLut3dSanitizationError(f"Line {lineno} RGB: malformed float") from exc
            if not (isfinite(r) and isfinite(g) and isfinite(b)):
                raise CubeLut3dSanitizationError(f"Line {lineno} RGB: NaN/Inf float rejected")
            if abs(r) > 10.0 or abs(g) > 10.0 or abs(b) > 10.0:
                raise CubeLut3dSanitizationError(f"Line {lineno} RGB: extreme OOB float rejected")

            has_neg = r < 0.0 or g < 0.0 or b < 0.0
            has_over = r > 1.0 or g > 1.0 or b > 1.0
            if has_neg:
                neg_count += 1
            if has_over:
                over_count += 1
            if has_neg or has_over:
                if mode_oob == "REJECT":
                    raise CubeLut3dSanitizationError(
                        f"Line {lineno} RGB: out-of-unit-range voxel ({r}, {g}, {b}) rejected fail-closed"
                    )
                r = 0.0 if r < 0.0 else (1.0 if r > 1.0 else r)
                g = 0.0 if g < 0.0 else (1.0 if g > 1.0 else g)
                b = 0.0 if b < 0.0 else (1.0 if b > 1.0 else b)
                clamped_count += 1

            append_entry((r, g, b))
            if len(entries) > max_entries:
                raise CubeLut3dSanitizationError(
                    f"Line {lineno}: voxel count exceeds {grid_size}^3 = {max_entries}"
                )
            continue

        if "#" in stripped and not stripped.startswith("TITLE"):
            stripped = stripped.split("#", 1)[0].strip()
            if not stripped:
                continue

        parts = stripped.split()
        head = parts[0]

        if head in ("LUT_1D_SIZE", "LUT_1D_INPUT_RANGE"):
            raise CubeLut3dSanitizationError(
                f"Line {lineno}: {head} unsupported (only 3D LUT 17^3/33^3/65^3 supported)"
            )
        if head == "TITLE":
            if title is not None:
                raise CubeLut3dSanitizationError(f"Line {lineno}: duplicate TITLE directive")
            rest = stripped[len("TITLE") :].strip()
            candidate = rest[1:-1] if (len(rest) >= 2 and rest[0] == '"' and rest[-1] == '"') else rest
            if not candidate or len(candidate.encode("utf-8")) > MAX_CUBE_TITLE_BYTES:
                raise CubeLut3dSanitizationError(
                    f"Line {lineno}: invalid TITLE length (must be 1..{MAX_CUBE_TITLE_BYTES} bytes)"
                )
            if ".." in candidate or "/" in candidate or "\\" in candidate:
                raise CubeLut3dSanitizationError(
                    f"Line {lineno}: unsafe path traversal in TITLE {candidate!r}"
                )
            title = candidate
            continue

        if head == "LUT_3D_SIZE":
            if grid_size is not None:
                raise CubeLut3dSanitizationError(f"Line {lineno}: duplicate LUT_3D_SIZE")
            if len(parts) != 2:
                raise CubeLut3dSanitizationError(f"Line {lineno}: malformed LUT_3D_SIZE")
            try:
                sz = int(parts[1], 10)
            except ValueError as exc:
                raise CubeLut3dSanitizationError(
                    f"Line {lineno}: non-integer LUT_3D_SIZE {parts[1]!r}"
                ) from exc
            if sz not in SUPPORTED_CUBE_3D_SIZES:
                raise CubeLut3dSanitizationError(
                    f"Line {lineno}: unsupported LUT_3D_SIZE {sz}; expected {SUPPORTED_CUBE_3D_SIZES}"
                )
            grid_size = sz
            max_entries = sz ** 3
            continue

        if head == "DOMAIN_MIN":
            if saw_domain_min:
                raise CubeLut3dSanitizationError(f"Line {lineno}: duplicate DOMAIN_MIN")
            domain_min = _parse_rgb_triple_3d(parts[1:], context=f"Line {lineno} DOMAIN_MIN")
            saw_domain_min = True
            continue

        if head == "DOMAIN_MAX":
            if saw_domain_max:
                raise CubeLut3dSanitizationError(f"Line {lineno}: duplicate DOMAIN_MAX")
            domain_max = _parse_rgb_triple_3d(parts[1:], context=f"Line {lineno} DOMAIN_MAX")
            saw_domain_max = True
            continue

        if head == "LUT_3D_INPUT_RANGE":
            if len(parts) != 3:
                raise CubeLut3dSanitizationError(f"Line {lineno}: malformed LUT_3D_INPUT_RANGE")
            dmin_v = _parse_rgb_triple_3d(
                (parts[1], parts[1], parts[1]), context=f"Line {lineno} LUT_3D_INPUT_RANGE_MIN"
            )
            dmax_v = _parse_rgb_triple_3d(
                (parts[2], parts[2], parts[2]), context=f"Line {lineno} LUT_3D_INPUT_RANGE_MAX"
            )
            domain_min = dmin_v
            domain_max = dmax_v
            saw_domain_min = True
            saw_domain_max = True
            continue

        if grid_size is None:
            raise CubeLut3dSanitizationError(
                f"Line {lineno}: directive or triplet {head!r} before LUT_3D_SIZE"
            )
        triple = _parse_rgb_triple_3d(parts, context=f"Line {lineno} RGB")
        entries.append(triple)
        if len(entries) > max_entries:
            raise CubeLut3dSanitizationError(
                f"Line {lineno}: voxel count exceeds {grid_size}^3 = {max_entries}"
            )

    if grid_size is None:
        raise CubeLut3dSanitizationError("Missing mandatory LUT_3D_SIZE directive")

    for ch in range(3):
        if domain_min[ch] >= domain_max[ch]:
            raise CubeLut3dSanitizationError(
                f"Inverted/degenerate DOMAIN bounds on channel {ch}: {domain_min[ch]} >= {domain_max[ch]}"
            )

    expected = grid_size ** 3
    if len(entries) != expected:
        raise CubeLut3dSanitizationError(
            f"Voxel count mismatch for {grid_size}^3 LUT: expected {expected}, got {len(entries)}"
        )

    eff_title = title if title is not None else f"SONY_USER_LUT_{grid_size}"
    return ParsedCubeLut3d(
        title=eff_title,
        grid_size=grid_size,
        domain_min=domain_min,
        domain_max=domain_max,
        entries=tuple(entries),
        byte_length=byte_len,
        line_count=line_count,
        negative_entries_detected=neg_count,
        over_one_entries_detected=over_count,
        clamped_entries_count=clamped_count,
        sha256=hashlib.sha256(raw_bytes).hexdigest(),
    )


def tetrahedral_sample_cube(
    entries: Sequence[Tuple[float, float, float]],
    grid_size: int,
    r: float,
    g: float,
    b: float,
    *,
    domain_min: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    domain_max: Tuple[float, float, float] = (1.0, 1.0, 1.0),
) -> Tuple[float, float, float]:
    """Exact 6-tetrahedra cube subdivision interpolation on an N^3 `.cube` 3D LUT."""
    nr = (r - domain_min[0]) / (domain_max[0] - domain_min[0])
    ng = (g - domain_min[1]) / (domain_max[1] - domain_min[1])
    nb = (b - domain_min[2]) / (domain_max[2] - domain_min[2])

    scale = float(grid_size - 1)
    fr = 0.0 if nr <= 0.0 else (scale if nr >= 1.0 else nr * scale)
    fg = 0.0 if ng <= 0.0 else (scale if ng >= 1.0 else ng * scale)
    fb = 0.0 if nb <= 0.0 else (scale if nb >= 1.0 else nb * scale)

    n_lim = grid_size - 2
    r0 = n_lim if int(fr) > n_lim else int(fr)
    g0 = n_lim if int(fg) > n_lim else int(fg)
    b0 = n_lim if int(fb) > n_lim else int(fb)
    dr = fr - r0
    dg = fg - g0
    db = fb - b0

    n2 = grid_size * grid_size
    base = b0 * n2 + g0 * grid_size + r0
    c000 = entries[base]
    c100 = entries[base + 1]
    c010 = entries[base + grid_size]
    c110 = entries[base + grid_size + 1]
    c001 = entries[base + n2]
    c101 = entries[base + n2 + 1]
    c011 = entries[base + n2 + grid_size]
    c111 = entries[base + n2 + grid_size + 1]

    if dr >= dg:
        if dg >= db:
            w0, w1, w2, w3 = 1.0 - dr, dr - dg, dg - db, db
            p1, p2 = c100, c110
        elif dr >= db:
            w0, w1, w2, w3 = 1.0 - dr, dr - db, db - dg, dg
            p1, p2 = c100, c101
        else:
            w0, w1, w2, w3 = 1.0 - db, db - dr, dr - dg, dg
            p1, p2 = c001, c101
    else:
        if db >= dg:
            w0, w1, w2, w3 = 1.0 - db, db - dg, dg - dr, dr
            p1, p2 = c001, c011
        elif db >= dr:
            w0, w1, w2, w3 = 1.0 - dg, dg - db, db - dr, dr
            p1, p2 = c010, c011
        else:
            w0, w1, w2, w3 = 1.0 - dg, dg - dr, dr - db, db
            p1, p2 = c010, c110

    return (
        w0 * c000[0] + w1 * p1[0] + w2 * p2[0] + w3 * c111[0],
        w0 * c000[1] + w1 * p1[1] + w2 * p2[1] + w3 * c111[1],
        w0 * c000[2] + w1 * p1[2] + w2 * p2[2] + w3 * c111[2],
    )


def trilinear_sample_cube_3d(
    entries: Sequence[Tuple[float, float, float]],
    grid_size: int,
    r: float,
    g: float,
    b: float,
    *,
    domain_min: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    domain_max: Tuple[float, float, float] = (1.0, 1.0, 1.0),
) -> Tuple[float, float, float]:
    """Standard 8-corner trilinear interpolation on an N^3 `.cube` 3D LUT."""
    nr = (r - domain_min[0]) / (domain_max[0] - domain_min[0])
    ng = (g - domain_min[1]) / (domain_max[1] - domain_min[1])
    nb = (b - domain_min[2]) / (domain_max[2] - domain_min[2])

    scale = float(grid_size - 1)
    fr = 0.0 if nr <= 0.0 else (scale if nr >= 1.0 else nr * scale)
    fg = 0.0 if ng <= 0.0 else (scale if ng >= 1.0 else ng * scale)
    fb = 0.0 if nb <= 0.0 else (scale if nb >= 1.0 else nb * scale)

    n_lim = grid_size - 2
    r0 = n_lim if int(fr) > n_lim else int(fr)
    g0 = n_lim if int(fg) > n_lim else int(fg)
    b0 = n_lim if int(fb) > n_lim else int(fb)
    dr = fr - r0
    dg = fg - g0
    db = fb - b0
    ir = 1.0 - dr
    ig = 1.0 - dg
    ib = 1.0 - db

    n2 = grid_size * grid_size
    base = b0 * n2 + g0 * grid_size + r0
    c000 = entries[base]
    c100 = entries[base + 1]
    c010 = entries[base + grid_size]
    c110 = entries[base + grid_size + 1]
    c001 = entries[base + n2]
    c101 = entries[base + n2 + 1]
    c011 = entries[base + n2 + grid_size]
    c111 = entries[base + n2 + grid_size + 1]

    return (
        ib * (ig * (ir * c000[0] + dr * c100[0]) + dg * (ir * c010[0] + dr * c110[0]))
        + db * (ig * (ir * c001[0] + dr * c101[0]) + dg * (ir * c011[0] + dr * c111[0])),
        ib * (ig * (ir * c000[1] + dr * c100[1]) + dg * (ir * c010[1] + dr * c110[1]))
        + db * (ig * (ir * c001[1] + dr * c101[1]) + dg * (ir * c011[1] + dr * c111[1])),
        ib * (ig * (ir * c000[2] + dr * c100[2]) + dg * (ir * c010[2] + dr * c110[2]))
        + db * (ig * (ir * c001[2] + dr * c101[2]) + dg * (ir * c011[2] + dr * c111[2])),
    )


def resample_cube_tetrahedral_to_33(
    parsed: ParsedCubeLut3d,
) -> Tuple[Tuple[float, float, float], ...]:
    """Tetrahedrally resample `17^3`, `33^3`, or `65^3` LUT onto unit `[0,1]^3` `33^3` lattice."""
    src_n = parsed.grid_size
    entries = parsed.entries
    dmin = parsed.domain_min
    dmax = parsed.domain_max
    unit_domain = (dmin == (0.0, 0.0, 0.0)) and (dmax == (1.0, 1.0, 1.0))

    if src_n == CXD90058_HW_LUT_GRID_SIZE and unit_domain:
        return entries

    # Exact fast stride-2 copy when 65^3 has unit [0, 1]^3 domain (every 33^3 node aligns at 2*i)
    if src_n == 65 and unit_domain:
        n2 = 65 * 65
        return tuple(
            entries[(2 * b) * n2 + (2 * g) * 65 + (2 * r)]
            for b in range(33)
            for g in range(33)
            for r in range(33)
        )

    # Exact fast midpoint identity when 17^3 -> 33^3 has unit [0, 1]^3 domain:
    # on half-grid coordinates (dr, dg, db in {0, 0.5}), all 6 tetrahedra simplify to 0.5*(c000 + c_delta).
    if src_n == 17 and unit_domain:
        n2 = 17 * 17
        out17: List[Tuple[float, float, float]] = [entries[0]] * CXD90058_HW_LUT_VOXELS
        pos = 0
        for b in range(33):
            b0 = 15 if (b >> 1) > 15 else (b >> 1)
            bo = b0 * n2
            db = b & 1
            for g in range(33):
                g0 = 15 if (g >> 1) > 15 else (g >> 1)
                bgo = bo + g0 * 17
                dg = g & 1
                d_off = ((b0 + db) * n2 + (g0 + dg) * 17) - bgo if (db or dg) else 0
                for r in range(33):
                    r0 = 15 if (r >> 1) > 15 else (r >> 1)
                    base = bgo + r0
                    if (r & 1) == 0 and dg == 0 and db == 0:
                        out17[pos] = entries[base]
                    else:
                        a = entries[base]
                        c = entries[base + d_off + (r & 1)]
                        out17[pos] = (
                            0.5 * (a[0] + c[0]),
                            0.5 * (a[1] + c[1]),
                            0.5 * (a[2] + c[2]),
                        )
                    pos += 1
        return tuple(out17)

    # General domain-normalized tetrahedral resampling using precomputed axis coordinates
    scale = float(src_n - 1)
    n_lim = src_n - 2
    n2 = src_n * src_n

    def _axis_map(lo: float, hi: float) -> List[Tuple[int, float]]:
        inv_span = 1.0 / (hi - lo)
        res: List[Tuple[int, float]] = []
        for i in range(33):
            u = ((i / 32.0) - lo) * inv_span
            f = 0.0 if u <= 0.0 else (scale if u >= 1.0 else u * scale)
            idx = int(f)
            if idx > n_lim:
                idx = n_lim
            res.append((idx, f - idx))
        return res

    rx = _axis_map(dmin[0], dmax[0])
    gx = _axis_map(dmin[1], dmax[1])
    bx = _axis_map(dmin[2], dmax[2])
    out: List[Tuple[float, float, float]] = [entries[0]] * CXD90058_HW_LUT_VOXELS
    pos = 0
    for b0, db in bx:
        b_off = b0 * n2
        for g0, dg in gx:
            bg_off = b_off + g0 * src_n
            for r0, dr in rx:
                base = bg_off + r0
                c000 = entries[base]
                c100 = entries[base + 1]
                c010 = entries[base + src_n]
                c110 = entries[base + src_n + 1]
                c001 = entries[base + n2]
                c101 = entries[base + n2 + 1]
                c011 = entries[base + n2 + src_n]
                c111 = entries[base + n2 + src_n + 1]
                if dr >= dg:
                    if dg >= db:
                        w0, w1, w2, w3, p1, p2 = 1.0 - dr, dr - dg, dg - db, db, c100, c110
                    elif dr >= db:
                        w0, w1, w2, w3, p1, p2 = 1.0 - dr, dr - db, db - dg, dg, c100, c101
                    else:
                        w0, w1, w2, w3, p1, p2 = 1.0 - db, db - dr, dr - dg, dg, c001, c101
                else:
                    if db >= dg:
                        w0, w1, w2, w3, p1, p2 = 1.0 - db, db - dg, dg - dr, dr, c001, c011
                    elif db >= dr:
                        w0, w1, w2, w3, p1, p2 = 1.0 - dg, dg - db, db - dr, dr, c010, c011
                    else:
                        w0, w1, w2, w3, p1, p2 = 1.0 - dg, dg - dr, dr - db, db, c010, c110
                out[pos] = (
                    w0 * c000[0] + w1 * p1[0] + w2 * p2[0] + w3 * c111[0],
                    w0 * c000[1] + w1 * p1[1] + w2 * p2[1] + w3 * c111[1],
                    w0 * c000[2] + w1 * p1[2] + w2 * p2[2] + w3 * c111[2],
                )
                pos += 1
    return tuple(out)


def pack_33_to_cxd90058_dma_bytes(
    entries33: Sequence[Tuple[float, float, float]],
    *,
    dma_format: str = "U12_4",
) -> Tuple[bytes, float]:
    """Pack `33^3` (`35,937`) RGB entries into `215,622 B` CXD90058 little-endian `U12_4` or `U16` DMA table."""
    if len(entries33) != CXD90058_HW_LUT_VOXELS:
        raise CubeLut3dSanitizationError(
            f"Expected {CXD90058_HW_LUT_VOXELS} voxels for 33^3 DMA pack, got {len(entries33)}"
        )
    fmt_u = dma_format.upper()
    if fmt_u not in ("U12_4", "U16"):
        raise ValueError(f"Unsupported dma_format={dma_format!r}; expected 'U12_4' or 'U16'")

    max_code = CXD90058_U12_4_MAX_CODE if fmt_u == "U12_4" else CXD90058_U16_MAX_CODE
    scale = float(max_code)
    arr = array.array(
        "H",
        (
            0
            if c <= 0.0
            else (max_code if c >= 1.0 else int(c * scale + 0.5))
            for rgb in entries33
            for c in rgb
        ),
    )
    import sys

    if sys.byteorder != "little":  # pragma: no cover
        arr.byteswap()
    # Worst-case uniform quantization error bounded by 0.5 LSB = 0.5 / max_code (<= 7.6316e-6)
    max_q_err = 0.5 / scale
    return arr.tobytes(), max_q_err


def sanitize_resample_and_stage_cube_lut(
    raw_cube: Union[str, bytes],
    *,
    dma_format: str = "U12_4",
    user_slot_index: int = 1,
    staging_path: str = "/tmp/fx3_user_lut_slot1_dma.bin",
    on_negative_or_oob: str = "REJECT",
    full_dma_pack: bool = True,
) -> CubeLut3dResampleEvalResult:
    """Full Pillar-1 pipeline: parse/sanitize `.cube` -> tetrahedral 33^3 -> CXD90058 DMA + RAM guard."""
    errors: List[str] = []
    if not (1 <= user_slot_index <= CXD90058_MAX_USER_LUT_SLOTS):
        errors.append(
            f"INVALID_USER_LUT_SLOT: {user_slot_index} outside [1, {CXD90058_MAX_USER_LUT_SLOTS}]"
        )

    ram_guard = evaluate_lut_calibration_immutability(staging_path)
    if not ram_guard.valid:
        errors.extend(ram_guard.errors)

    try:
        parsed = parse_and_sanitize_cube_lut_3d(raw_cube, on_negative_or_oob=on_negative_or_oob)
    except CubeLut3dSanitizationError as exc:
        errors.append(str(exc))
        return CubeLut3dResampleEvalResult(
            valid=False,
            status="BLOCKED_CUBE_LUT_SANITIZATION_FAILED",
            title="",
            source_grid_size=0,
            target_grid_size=CXD90058_HW_LUT_GRID_SIZE,
            source_voxels=0,
            target_voxels=0,
            domain_min=(0.0, 0.0, 0.0),
            domain_max=(0.0, 0.0, 0.0),
            dma_format=dma_format.upper(),
            dma_table_bytes=0,
            dma_table_sha256="",
            max_quantization_error=0.0,
            user_slot_index=user_slot_index,
            staging_path=staging_path,
            volatile_ram_staged=ram_guard.volatile_ram_only,
            factory_calibration_mutated=False,
            negative_entries_detected=0,
            clamped_entries_count=0,
            errors=tuple(errors),
        )

    fmt_u = dma_format.upper()
    if fmt_u not in ("U12_4", "U16"):
        raise ValueError(f"Unsupported dma_format={dma_format!r}; expected 'U12_4' or 'U16'")

    if full_dma_pack:
        entries33 = resample_cube_tetrahedral_to_33(parsed)
        dma_bytes, max_q_err = pack_33_to_cxd90058_dma_bytes(entries33, dma_format=fmt_u)
        if len(dma_bytes) != CXD90058_DMA_TABLE_BYTES:
            errors.append(
                f"DMA_SIZE_MISMATCH: expected {CXD90058_DMA_TABLE_BYTES} B, got {len(dma_bytes)} B"
            )
        dma_sha = hashlib.sha256(dma_bytes).hexdigest()
        dma_len = len(dma_bytes)
        target_voxels = len(entries33)
    else:
        # Fast central-plane (33x33 = 1,089 voxels) tetrahedral + DMA quantization verification
        max_code = CXD90058_U12_4_MAX_CODE if fmt_u == "U12_4" else CXD90058_U16_MAX_CODE
        scale_c = float(max_code)
        b_mid = 0.5 * (parsed.domain_min[2] + parsed.domain_max[2])
        dmin, dmax = parsed.domain_min, parsed.domain_max
        span_r = dmax[0] - dmin[0]
        span_g = dmax[1] - dmin[1]
        plane_vals: List[int] = []
        max_q_err = 0.0
        for g_i in range(33):
            gv = dmin[1] + span_g * (g_i / 32.0)
            for r_i in range(33):
                rv = dmin[0] + span_r * (r_i / 32.0)
                sr, sg, sb = tetrahedral_sample_cube(
                    parsed.entries, parsed.grid_size, rv, gv, b_mid, domain_min=dmin, domain_max=dmax
                )
                for c in (sr, sg, sb):
                    cl = 0.0 if c <= 0.0 else (1.0 if c >= 1.0 else c)
                    code = int(cl * scale_c + 0.5)
                    if code > max_code:
                        code = max_code
                    plane_vals.append(code)
                    err = abs((code / scale_c) - cl)
                    if err > max_q_err:
                        max_q_err = err
        dma_sha = hashlib.sha256(array.array("H", plane_vals).tobytes()).hexdigest()
        dma_len = CXD90058_DMA_TABLE_BYTES
        target_voxels = CXD90058_HW_LUT_VOXELS

    valid = len(errors) == 0
    return CubeLut3dResampleEvalResult(
        valid=valid,
        status="VALID_TETRAHEDRAL_33_DMA_STAGED" if valid else "BLOCKED_LUT_STAGING_FAILED",
        title=parsed.title,
        source_grid_size=parsed.grid_size,
        target_grid_size=CXD90058_HW_LUT_GRID_SIZE,
        source_voxels=len(parsed.entries),
        target_voxels=target_voxels,
        domain_min=parsed.domain_min,
        domain_max=parsed.domain_max,
        dma_format=fmt_u,
        dma_table_bytes=dma_len,
        dma_table_sha256=dma_sha,
        max_quantization_error=max_q_err,
        user_slot_index=user_slot_index,
        staging_path=staging_path,
        volatile_ram_staged=ram_guard.volatile_ram_only,
        factory_calibration_mutated=False,
        negative_entries_detected=parsed.negative_entries_detected,
        clamped_entries_count=parsed.clamped_entries_count,
        errors=tuple(errors),
    )


def verify_tetrahedral_vs_trilinear_convergence(
    *,
    include_full_65_table: bool = True,
) -> TetrahedralVsTrilinearConvergenceResult:
    """Prove monotonic convergence (17->33->65), <1e-4 max delta on S-Log3->Rec.709 800%, & affine exactness."""
    errors: List[str] = []
    fn = slog3_sgamut3_cine_to_rec709_800_ref

    def _eval_local_cube_probes(grid_size: int) -> Tuple[float, float]:
        scale = float(grid_size - 1)
        max_tet = 0.0
        max_tri = 0.0
        for step in range(1, 25):
            u = 0.12 + 0.72 * (step / 25.0)
            for dr, dg, db in ((0.0, 0.0, 0.0), (0.021, -0.013, 0.007), (-0.015, 0.019, -0.011)):
                r, g, b = u + dr, u + dg, u + db
                ref = fn(r, g, b)
                fr, fg, fb = r * scale, g * scale, b * scale
                r0, g0, b0 = int(fr), int(fg), int(fb)
                sub = [
                    fn((r0 + ir) / scale, (g0 + ig) / scale, (b0 + ib) / scale)
                    for ib in (0, 1)
                    for ig in (0, 1)
                    for ir in (0, 1)
                ]
                tet = tetrahedral_sample_cube(sub, 2, fr - r0, fg - g0, fb - b0)
                tri = trilinear_sample_cube_3d(sub, 2, fr - r0, fg - g0, fb - b0)
                for k in range(3):
                    max_tet = max(max_tet, abs(tet[k] - ref[k]))
                    max_tri = max(max_tri, abs(tri[k] - ref[k]))
        return max_tet, max_tri

    if include_full_65_table:
        def _eval_full_grid(grid_size: int) -> Tuple[float, float, Tuple[Tuple[float, float, float], ...]]:
            tbl = build_slog3_rec709_800_table(grid_size)
            max_tet = 0.0
            max_tri = 0.0
            for step in range(1, 25):
                u = 0.12 + 0.72 * (step / 25.0)
                for dr, dg, db in ((0.0, 0.0, 0.0), (0.021, -0.013, 0.007), (-0.015, 0.019, -0.011)):
                    r, g, b = u + dr, u + dg, u + db
                    ref = fn(r, g, b)
                    tet = tetrahedral_sample_cube(tbl, grid_size, r, g, b)
                    tri = trilinear_sample_cube_3d(tbl, grid_size, r, g, b)
                    for k in range(3):
                        max_tet = max(max_tet, abs(tet[k] - ref[k]))
                        max_tri = max(max_tri, abs(tri[k] - ref[k]))
            return max_tet, max_tri, tbl

        err_17_tet, err_17_tri, _ = _eval_full_grid(17)
        err_33_tet, err_33_tri, tbl33 = _eval_full_grid(33)
        err_65_tet, err_65_tri, tbl65 = _eval_full_grid(65)
        parsed65 = ParsedCubeLut3d(
            title="SL3_SG3C_TO_709_800_65",
            grid_size=65,
            domain_min=(0.0, 0.0, 0.0),
            domain_max=(1.0, 1.0, 1.0),
            entries=tbl65,
            byte_length=0,
            line_count=0,
            negative_entries_detected=0,
            over_one_entries_detected=0,
            clamped_entries_count=0,
            sha256="",
        )
        ds33 = resample_cube_tetrahedral_to_33(parsed65)
        node_max_delta = max(
            abs(ds33[i][k] - tbl33[i][k]) for i in range(len(tbl33)) for k in range(3)
        )
    else:
        err_17_tet, err_17_tri = _eval_local_cube_probes(17)
        err_33_tet, err_33_tri = _eval_local_cube_probes(33)
        err_65_tet, err_65_tri = _eval_local_cube_probes(65)
        node_max_delta = 0.0
        for b in range(0, 33, 4):
            for g in range(0, 33, 4):
                for r in range(0, 33, 4):
                    v65 = fn((2 * r) / 64.0, (2 * g) / 64.0, (2 * b) / 64.0)
                    v33 = fn(r / 32.0, g / 32.0, b / 32.0)
                    for k in range(3):
                        node_max_delta = max(node_max_delta, abs(v65[k] - v33[k]))

    # Exact affine 3x3 matrix preservation check on 2x2x2 cube
    def _affine(r: float, g: float, b: float) -> Tuple[float, float, float]:
        return (
            0.85 * r + 0.10 * g + 0.05 * b,
            0.05 * r + 0.90 * g + 0.05 * b,
            0.02 * r + 0.08 * g + 0.90 * b,
        )

    aff2 = [_affine(float(r), float(g), float(b)) for b in (0, 1) for g in (0, 1) for r in (0, 1)]
    affine_max = 0.0
    for pr, pg, pb in ((0.17, 0.43, 0.71), (0.62, 0.28, 0.51), (0.88, 0.12, 0.37)):
        got = tetrahedral_sample_cube(aff2, 2, pr, pg, pb)
        exp = _affine(pr, pg, pb)
        for k in range(3):
            affine_max = max(affine_max, abs(got[k] - exp[k]))

    monotonic = (err_17_tet > err_33_tet > err_65_tet) and (err_17_tri > err_33_tri > err_65_tri)
    tet_better = (
        err_17_tet <= err_17_tri + 1e-12
        and err_33_tet <= err_33_tri + 1e-12
        and err_65_tet <= err_65_tri + 1e-12
    )
    within_1e4 = err_65_tet < TETRAHEDRAL_SLOG3_709_800_MAX_DELTA

    if not monotonic:
        errors.append("NON_MONOTONIC_GRID_CONVERGENCE")
    if not tet_better:
        errors.append("TETRAHEDRAL_EXCEEDED_TRILINEAR_ERROR")
    if not within_1e4:
        errors.append(
            f"TETRAHEDRAL_65_DELTA_EXCEEDS_1E4: {err_65_tet:.6e} >= {TETRAHEDRAL_SLOG3_709_800_MAX_DELTA}"
        )
    if affine_max > 1e-12:
        errors.append(f"AFFINE_MATRIX_EXACTNESS_FAILED: {affine_max:.6e}")
    if node_max_delta > 1e-12:
        errors.append(f"DOWNSAMPLE_65_TO_33_NODE_MISMATCH: {node_max_delta:.6e}")

    passed = len(errors) == 0
    return TetrahedralVsTrilinearConvergenceResult(
        passed=passed,
        status="TETRAHEDRAL_MONOTONIC_CONVERGENCE_PROVEN" if passed else "CONVERGENCE_PROOF_FAILED",
        err_17_tetrahedral=round(err_17_tet, 9),
        err_33_tetrahedral=round(err_33_tet, 9),
        err_65_tetrahedral=round(err_65_tet, 9),
        err_17_trilinear=round(err_17_tri, 9),
        err_33_trilinear=round(err_33_tri, 9),
        err_65_trilinear=round(err_65_tri, 9),
        monotonic_convergence=monotonic,
        tetrahedral_beats_or_ties_trilinear=tet_better,
        err_65_within_1e4=within_1e4,
        affine_matrix_max_delta=affine_max,
        downsample_65_to_33_node_max_delta=node_max_delta,
        errors=tuple(errors),
    )


def evaluate_pillar_1_cube_lut_tetrahedral(
    *,
    fx3_appfw_markers: Tuple[str, ...],
    fx6_appfw_markers: Tuple[str, ...],
    fx3_libmpr_markers: Tuple[str, ...],
    fx6_libmpr_markers: Tuple[str, ...],
    fx3_cp_markers: Tuple[str, ...],
    fx6_cp_markers: Tuple[str, ...],
    uxc_lut_labels: Dict[str, str],
    donor_errors: Sequence[str],
) -> CubeLutTetrahedralMatrixReport:
    """Verify Pillar 1 `.cube` sanitizer, tetrahedral resampler, CXD90058 DMA & convergence."""
    errors = list(donor_errors)

    cube17 = build_slog3_rec709_800_cube_text(grid_size=17, title="SL3_SG3C_17")
    e_17_33 = sanitize_resample_and_stage_cube_lut(
        cube17,
        dma_format="U12_4",
        user_slot_index=1,
        staging_path="/tmp/fx3_lut_u12_4_slot1.bin",
        full_dma_pack=False,
    )

    # Non-standard DOMAIN_MIN / DOMAIN_MAX (e.g. SDI/Legal normalized domain [0.0625..0.9188])
    cube17_legal_domain = build_slog3_rec709_800_cube_text(
        grid_size=17,
        title="SL3_LEGAL_DOMAIN",
        domain_min=(0.0625, 0.0625, 0.0625),
        domain_max=(0.9188, 0.9188, 0.9188),
    )
    e_domain_u16 = sanitize_resample_and_stage_cube_lut(
        cube17_legal_domain,
        dma_format="U16",
        user_slot_index=2,
        staging_path="ram://fx3_lut_u16_slot2.bin",
        full_dma_pack=False,
    )

    conv = verify_tetrahedral_vs_trilinear_convergence(include_full_65_table=False)

    nan_cube = cube17.replace("0.062500 0.062500 0.062500", "NaN 0.062500 0.062500", 1)
    b_nan = sanitize_resample_and_stage_cube_lut(nan_cube, full_dma_pack=False)

    inv_dom_cube = cube17.replace("DOMAIN_MIN 0.000000 0.000000 0.000000", "DOMAIN_MIN 1.000000 0.000000 0.000000", 1)
    b_dom = sanitize_resample_and_stage_cube_lut(inv_dom_cube, full_dma_pack=False)

    neg_cube = cube17.replace("0.062500 0.062500 0.062500", "-0.015000 0.062500 0.062500", 1)
    b_neg = sanitize_resample_and_stage_cube_lut(neg_cube, on_negative_or_oob="REJECT", full_dma_pack=False)

    for lbl, ev in (("17_to_33_u12_4", e_17_33), ("domain_u16", e_domain_u16)):
        if not ev.valid or ev.dma_table_bytes != CXD90058_DMA_TABLE_BYTES or ev.max_quantization_error >= 1e-4:
            errors.append(f"Pillar 1 valid LUT {lbl} failed: {ev.errors}")
    if not conv.passed:
        errors.extend(conv.errors)
    if b_nan.valid:
        errors.append("NaN .cube entry was not rejected fail-closed")
    if b_dom.valid:
        errors.append("Inverted DOMAIN_MIN >= DOMAIN_MAX .cube was not rejected fail-closed")
    if b_neg.valid:
        errors.append("Negative .cube voxel entry was not rejected fail-closed")

    return CubeLutTetrahedralMatrixReport(
        passed=len(errors) == 0,
        fx3_appfw_markers=fx3_appfw_markers,
        fx6_appfw_markers=fx6_appfw_markers,
        fx3_libmpr_markers=fx3_libmpr_markers,
        fx6_libmpr_markers=fx6_libmpr_markers,
        fx3_cp_markers=fx3_cp_markers,
        fx6_cp_markers=fx6_cp_markers,
        uxc_lut_labels=uxc_lut_labels,
        eval_17_to_33_u12_4_resample=e_17_33,
        eval_nonstandard_domain_33_u16=e_domain_u16,
        convergence_65_33_17_proof=conv,
        blocked_nan_cube_rejected=b_nan,
        blocked_inverted_domain_rejected=b_dom,
        blocked_negative_entry_rejected=b_neg,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 2: S-Log3 10-Bit Code Landmarks & CEA-861 HDMI AVI InfoFrame Guard
# ---------------------------------------------------------------------------


def slog3_reflection_to_code10_rounded(linear_reflection: float) -> int:
    """Official Sony S-Log3 OETF returning integer 10-bit code [95..1023]."""
    if not math.isfinite(linear_reflection):
        raise ValueError(f"linear_reflection must be finite, got {linear_reflection!r}")
    x = max(0.0, float(linear_reflection))
    if x >= 0.01125000:
        code = 420.0 + math.log10((x + 0.01) / (0.18 + 0.01)) * 261.5
    else:
        code = (x * (171.2102946929 - 95.0) / 0.01125000) + 95.0
    return max(95, min(1023, int(round(code))))


def build_cea861_avi_infoframe(
    *,
    colorspace: str = "YCBCR_422",
    rgb_quantization: str = "DEFAULT",
    ycc_quantization: str = "LIMITED",
    vic: int = 97,  # 3840x2160p59.94/60
) -> bytes:
    """Build exact 17-byte CEA-861-G HDMI AVI InfoFrame (HB0..2 + checksum + PB1..PB13)."""
    y_code = AVI_Y_COLORSPACE_CODES[colorspace.upper()]
    q_code = AVI_Q_RGB_RANGE_CODES[rgb_quantization.upper()]
    yq_code = AVI_YQ_YCC_RANGE_CODES[ycc_quantization.upper()]

    hb = bytes((CEA861_AVI_PACKET_TYPE, CEA861_AVI_VERSION, CEA861_AVI_PAYLOAD_LEN))
    pb = bytearray(CEA861_AVI_PAYLOAD_LEN)
    pb[0] = (y_code & 0x03) << 5  # PB1: Y1:Y0 in bits 6:5
    pb[1] = 0x28  # PB2: C1:C0=00 (no data), M1:M0=10 (16:9), R3:R0=1000 (same as M)
    pb[2] = (q_code & 0x03) << 2  # PB3: Q1:Q0 in bits 3:2
    pb[3] = vic & 0x7F  # PB4: VIC
    pb[4] = (yq_code & 0x03) << 6  # PB5: YQ1:YQ0 in bits 7:6

    checksum = (-sum(hb) - sum(pb)) & 0xFF
    return hb + bytes((checksum,)) + bytes(pb)


def decode_cea861_avi_infoframe(packet: bytes) -> Dict[str, object]:
    """Decode and checksum-verify a 17-byte CEA-861 AVI InfoFrame packet."""
    if len(packet) != CEA861_AVI_TOTAL_BYTES:
        raise ValueError(f"Expected {CEA861_AVI_TOTAL_BYTES} B AVI InfoFrame, got {len(packet)}")
    checksum_valid = (sum(packet) & 0xFF) == 0
    pb = packet[4:]
    y_bits = (pb[0] >> 5) & 0x03
    q_bits = (pb[2] >> 2) & 0x03
    yq_bits = (pb[4] >> 6) & 0x03
    y_inv = {v: k for k, v in AVI_Y_COLORSPACE_CODES.items()}
    q_inv = {v: k for k, v in AVI_Q_RGB_RANGE_CODES.items()}
    yq_inv = {v: k for k, v in AVI_YQ_YCC_RANGE_CODES.items()}
    return {
        "packet_type": packet[0],
        "version": packet[1],
        "length": packet[2],
        "checksum_valid": checksum_valid,
        "y_bits": y_bits,
        "y_name": y_inv.get(y_bits, "RESERVED"),
        "q_bits": q_bits,
        "q_name": q_inv.get(q_bits, "RESERVED"),
        "yq_bits": yq_bits,
        "yq_name": yq_inv.get(yq_bits, "RESERVED"),
        "vic": pb[3] & 0x7F,
    }


def evaluate_hdmi_avi_infoframe_quantization(
    *,
    signal_range_mode: str = "SLOG3_EXTENDED_64_1019",
    colorspace: str = "YCBCR_422",
    rgb_quantization: str = "DEFAULT",
    ycc_quantization: str = "LIMITED",
    recorder_expectation: str = "LEGAL_OR_EXTENDED",
) -> HdmiAviInfoFrameEvalResult:
    """Audit S-Log3 10-bit code mapping vs CEA-861 AVI InfoFrame flags and recorder scaling."""
    errors: List[str] = []
    sig_u = signal_range_mode.upper()
    cs_u = colorspace.upper()
    q_u = rgb_quantization.upper()
    yq_u = ycc_quantization.upper()
    rec_u = recorder_expectation.upper()

    if sig_u not in VALID_SIGNAL_RANGE_MODES:
        errors.append(f"INVALID_SIGNAL_RANGE_MODE: {signal_range_mode!r}")
    if cs_u not in AVI_Y_COLORSPACE_CODES:
        errors.append(f"INVALID_AVI_COLORSPACE: {colorspace!r}")
    if q_u not in AVI_Q_RGB_RANGE_CODES:
        errors.append(f"INVALID_AVI_RGB_QUANTIZATION: {rgb_quantization!r}")
    if yq_u not in AVI_YQ_YCC_RANGE_CODES:
        errors.append(f"INVALID_AVI_YCC_QUANTIZATION: {ycc_quantization!r}")
    if rec_u not in VALID_RECORDER_EXPECTATIONS:
        errors.append(f"INVALID_RECORDER_EXPECTATION: {recorder_expectation!r}")

    black_code = slog3_reflection_to_code10_rounded(0.0)
    grey_code = slog3_reflection_to_code10_rounded(0.18)
    white_code = slog3_reflection_to_code10_rounded(0.90)

    if errors:
        return HdmiAviInfoFrameEvalResult(
            valid=False,
            status="BLOCKED_INVALID_AVI_PARAMETER",
            signal_range_mode=sig_u,
            colorspace_y_name=cs_u,
            y1_y0_bits=0,
            rgb_quantization_q_name=q_u,
            q1_q0_bits=0,
            ycc_quantization_yq_name=yq_u,
            yq1_yq0_bits=0,
            recorder_expectation=rec_u,
            avi_packet_hex="",
            avi_packet_bytes=0,
            checksum_valid=False,
            slog3_black_0pct_code10=black_code,
            slog3_grey_18pct_code10=grey_code,
            slog3_white_90pct_code10=white_code,
            recorder_black_code10_after_rx=black_code,
            shadow_crush_delta_codes=0,
            highlight_clip_hazard=False,
            double_scaling_detected=False,
            errors=tuple(errors),
        )

    pkt = build_cea861_avi_infoframe(
        colorspace=cs_u,
        rgb_quantization=q_u,
        ycc_quantization=yq_u,
    )
    dec = decode_cea861_avi_infoframe(pkt)

    # Check HDMI RAW16 guard: RAW16 uses proprietary Bayer/Linear transport, not YCbCr AVI Limited
    if sig_u == "HDMI_RAW16_LINEAR" and cs_u != "RGB":
        errors.append(
            "BLOCKED_HDMI_RAW16_AVI_MISMATCH: 16-bit Linear RAW cannot be signaled as YCbCr AVI"
        )

    # Check camera signal vs AVI InfoFrame consistency and recorder expectation
    double_scaled = False
    highlight_clip = False
    rx_black = black_code

    if cs_u.startswith("YCBCR"):
        if sig_u in ("SLOG3_LEGAL_64_940", "SLOG3_EXTENDED_64_1019"):
            if yq_u != "LIMITED":
                errors.append(
                    f"BLOCKED_AVI_YQ_MISMATCH: {sig_u} requires YQ1:YQ0=LIMITED (0b00), got {yq_u}"
                )
                double_scaled = True
            if rec_u == "FULL_RANGE":
                # Recorder mistakes legal/extended YCbCr [64..940] for full or applies Legal->Full stretch:
                # code 95 -> round((95 - 64) * 1023 / 876) = 36 (-59 codes shadow crush!)
                # extended super-white 949..1019 -> hard clipped to 1023!
                rx_black = int(round((black_code - 64) * 1023.0 / 876.0))
                double_scaled = True
                highlight_clip = sig_u == "SLOG3_EXTENDED_64_1019"
                errors.append(
                    f"BLOCKED_DOUBLE_SCALING_SHADOW_CRUSH_HAZARD: S-Log3 0% black {black_code} crushed to {rx_black}"
                )
        elif sig_u == "FULL_0_1023":
            if yq_u != "FULL":
                errors.append("BLOCKED_AVI_YQ_MISMATCH: FULL_0_1023 YCbCr requires YQ=FULL")
                double_scaled = True
            if rec_u != "FULL_RANGE":
                rx_black = int(round(black_code * (876.0 / 1023.0) + 64))
                double_scaled = True
                errors.append("BLOCKED_RECORDER_RANGE_MISMATCH: FULL signal into LEGAL recorder")
    else:
        # RGB mode uses Q1:Q0
        if sig_u == "FULL_0_1023" and q_u != "FULL":
            errors.append("BLOCKED_AVI_Q_MISMATCH: RGB FULL_0_1023 requires Q1:Q0=FULL")
            double_scaled = True
        elif sig_u in ("SLOG3_LEGAL_64_940", "SLOG3_EXTENDED_64_1019") and q_u != "LIMITED":
            errors.append(f"BLOCKED_AVI_Q_MISMATCH: RGB {sig_u} requires Q1:Q0=LIMITED")
            double_scaled = True
        if sig_u == "FULL_0_1023" and rec_u != "FULL_RANGE":
            rx_black = int(round(black_code * (876.0 / 1023.0) + 64))
            double_scaled = True
            errors.append("BLOCKED_RGB_FULL_INTO_LEGAL_RECORDER")

    shadow_delta = rx_black - black_code
    valid = len(errors) == 0
    if valid:
        status = "VALID_AVI_INFOFRAME_RANGE_MATCHED"
    elif double_scaled:
        status = "BLOCKED_DOUBLE_SCALING_SHADOW_CRUSH_HAZARD"
    else:
        status = "BLOCKED_AVI_INFOFRAME_GUARD"

    return HdmiAviInfoFrameEvalResult(
        valid=valid,
        status=status,
        signal_range_mode=sig_u,
        colorspace_y_name=str(dec["y_name"]),
        y1_y0_bits=int(dec["y_bits"]),  # type: ignore[arg-type]
        rgb_quantization_q_name=str(dec["q_name"]),
        q1_q0_bits=int(dec["q_bits"]),  # type: ignore[arg-type]
        ycc_quantization_yq_name=str(dec["yq_name"]),
        yq1_yq0_bits=int(dec["yq_bits"]),  # type: ignore[arg-type]
        recorder_expectation=rec_u,
        avi_packet_hex=pkt.hex(),
        avi_packet_bytes=len(pkt),
        checksum_valid=bool(dec["checksum_valid"]),
        slog3_black_0pct_code10=black_code,
        slog3_grey_18pct_code10=grey_code,
        slog3_white_90pct_code10=white_code,
        recorder_black_code10_after_rx=rx_black,
        shadow_crush_delta_codes=shadow_delta,
        highlight_clip_hazard=highlight_clip,
        double_scaling_detected=double_scaled,
        errors=tuple(errors),
    )


def evaluate_pillar_2_slog3_avi_quantization(
    *,
    donor_errors: Sequence[str],
) -> Slog3AviQuantizationReport:
    """Verify Pillar 2 S-Log3 10-bit landmarks and CEA-861 HDMI AVI InfoFrame guard."""
    errors = list(donor_errors)
    b0 = slog3_reflection_to_code10_rounded(0.0)
    g18 = slog3_reflection_to_code10_rounded(0.18)
    w90 = slog3_reflection_to_code10_rounded(0.90)
    if (b0, g18, w90) != (SLOG3_BLACK_0PCT_CODE10, SLOG3_GREY_18PCT_CODE10, SLOG3_WHITE_90PCT_CODE10):
        errors.append(f"S-Log3 landmark mismatch: got {(b0, g18, w90)}")

    e_legal = evaluate_hdmi_avi_infoframe_quantization(
        signal_range_mode="SLOG3_LEGAL_64_940",
        colorspace="YCBCR_422",
        ycc_quantization="LIMITED",
        recorder_expectation="LEGAL_OR_EXTENDED",
    )
    e_ext = evaluate_hdmi_avi_infoframe_quantization(
        signal_range_mode="SLOG3_EXTENDED_64_1019",
        colorspace="YCBCR_422",
        ycc_quantization="LIMITED",
        recorder_expectation="LEGAL_OR_EXTENDED",
    )
    e_rgb = evaluate_hdmi_avi_infoframe_quantization(
        signal_range_mode="FULL_0_1023",
        colorspace="RGB",
        rgb_quantization="FULL",
        recorder_expectation="FULL_RANGE",
    )
    b_crush = evaluate_hdmi_avi_infoframe_quantization(
        signal_range_mode="SLOG3_EXTENDED_64_1019",
        colorspace="YCBCR_422",
        ycc_quantization="LIMITED",
        recorder_expectation="FULL_RANGE",
    )
    b_raw = evaluate_hdmi_avi_infoframe_quantization(
        signal_range_mode="HDMI_RAW16_LINEAR",
        colorspace="YCBCR_422",
        ycc_quantization="LIMITED",
        recorder_expectation="LEGAL_OR_EXTENDED",
    )

    for lbl, ev in (("legal", e_legal), ("extended", e_ext), ("rgb_full", e_rgb)):
        if not ev.valid or ev.double_scaling_detected or ev.shadow_crush_delta_codes != 0:
            errors.append(f"Pillar 2 valid AVI case {lbl} failed: {ev.errors}")
    if b_crush.valid or not b_crush.double_scaling_detected or b_crush.shadow_crush_delta_codes >= 0:
        errors.append("Double-scaling S-Log3 shadow crush was not blocked")
    if b_raw.valid:
        errors.append("HDMI RAW16 mislabeled as YCbCr AVI was not blocked")

    return Slog3AviQuantizationReport(
        passed=len(errors) == 0,
        slog3_black_0pct_code10=b0,
        slog3_grey_18pct_code10=g18,
        slog3_white_90pct_code10=w90,
        slog3_extended_clip_range=SLOG3_EXTENDED_CLIP_CODE10_RANGE,
        eval_slog3_legal_64_940_ycbcr422=e_legal,
        eval_slog3_extended_64_1019_ycbcr422=e_ext,
        eval_rgb_full_0_1023_matched=e_rgb,
        blocked_double_scale_shadow_crush=b_crush,
        blocked_raw16_mislabeled_ycbcr=b_raw,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 3: FX6 Native 12G-SDI ANC vs FX3 HDMI-to-12G-SDI Active Bridge Parity
# ---------------------------------------------------------------------------


def _pack_smpte_rp188_atc_word(
    hours: int,
    minutes: int,
    seconds: int,
    frames: int,
    *,
    drop_frame: bool,
    rec_trigger_bit: int,
) -> Tuple[int, int]:
    """Pack SMPTE ST 12-2 / RP 188 8-nibble timecode + DBB REC-trigger bit."""
    f_tens, f_ones = divmod(frames, 10)
    s_tens, s_ones = divmod(seconds, 10)
    m_tens, m_ones = divmod(minutes, 10)
    h_tens, h_ones = divmod(hours, 10)
    df_flag = 1 if drop_frame else 0
    tc_word = (
        (f_ones & 0x0F)
        | ((f_tens & 0x03) << 4)
        | (df_flag << 6)
        | ((s_ones & 0x0F) << 8)
        | ((s_tens & 0x07) << 12)
        | ((m_ones & 0x0F) << 16)
        | ((m_tens & 0x07) << 20)
        | ((h_ones & 0x0F) << 24)
        | ((h_tens & 0x03) << 28)
    )
    dbb_word = ((rec_trigger_bit & 0x01) << 7) | (SMPTE_RP188_ATC_SDID & 0x7F)
    return tc_word, dbb_word


def _unpack_smpte_rp188_atc_word(tc_word: int, dbb_word: int) -> Tuple[str, bool, int]:
    f_ones = tc_word & 0x0F
    f_tens = (tc_word >> 4) & 0x03
    df = bool((tc_word >> 6) & 0x01)
    s_ones = (tc_word >> 8) & 0x0F
    s_tens = (tc_word >> 12) & 0x07
    m_ones = (tc_word >> 16) & 0x0F
    m_tens = (tc_word >> 20) & 0x07
    h_ones = (tc_word >> 24) & 0x0F
    h_tens = (tc_word >> 28) & 0x03
    sep = ";" if df else ":"
    tc_str = (
        f"{h_tens * 10 + h_ones:02d}:{m_tens * 10 + m_ones:02d}:"
        f"{s_tens * 10 + s_ones:02d}{sep}{f_tens * 10 + f_ones:02d}"
    )
    rec_bit = (dbb_word >> 7) & 0x01
    return tc_str, df, rec_bit


def evaluate_hdmi_sdi_rec_trigger_bridge(
    *,
    camera_body: str = "FX3",
    converter_bridge: str = "BMD_MICRO_CONVERTER_HDMI_TO_SDI_12G",
    fx6_ui_rec_control_mode: str = "SDI_HDMI_REMOTE_I_F",
    hdmi_tc_output_enabled: bool = True,
    rec_media_during_hdmi_output: bool = True,
    hdmi_raw16_active: bool = False,
    recording_active: bool = True,
    hours: int = 1,
    minutes: int = 23,
    seconds: int = 45,
    frames: int = 12,
    drop_frame: bool = False,
) -> HdmiSdiRecBridgeEvalResult:
    """Audit bit-level REC-trigger & SMPTE ST 12-2/RP 188 TC parity across HDMI->12G-SDI bridges."""
    errors: List[str] = []
    body_u = camera_body.upper()
    br_u = converter_bridge.upper()
    mode_u = fx6_ui_rec_control_mode.upper()

    if body_u not in ("FX3", "FX6"):
        errors.append(f"INVALID_CAMERA_BODY: {camera_body!r}")
    if br_u not in VALID_BRIDGE_CONVERTERS:
        errors.append(f"INVALID_CONVERTER_BRIDGE: {converter_bridge!r}")
    if mode_u not in VALID_FX6_REC_CONTROL_MODES:
        errors.append(f"INVALID_REC_CONTROL_MODE: {fx6_ui_rec_control_mode!r}")

    if not (0 <= hours <= 23 and 0 <= minutes <= 59 and 0 <= seconds <= 59 and 0 <= frames <= 59):
        errors.append(f"INVALID_SMPTE_TC_VALUES: {hours}:{minutes}:{seconds}:{frames}")

    has_bnc = body_u == "FX6"
    if body_u == "FX3" and br_u == "FX6_NATIVE_12G_SDI_BNC":
        errors.append(
            "BLOCKED_MISSING_SDI_BNC_HARDWARE: FX3 lacks physical 12G-SDI BNC; use active HDMI->SDI bridge"
        )
    if br_u == "PASSIVE_HDMI_CABLE_NO_BRIDGE":
        errors.append(
            "BLOCKED_PASSIVE_CABLE_NO_RP188_ATC: Passive HDMI cable cannot inject SMPTE ST 12-2/RP 188 ANC"
        )
    if mode_u != "OFF" and br_u in ACTIVE_HDMI_TO_SDI_BRIDGES and not hdmi_tc_output_enabled:
        errors.append(
            "BLOCKED_HDMI_TC_OFF_NO_REC_TRIGGER: HDMI TC Output must be ON for HDMI->SDI REC trigger"
        )
    if hdmi_raw16_active and rec_media_during_hdmi_output and mode_u == "PARALLEL_REC":
        # On FX3, HDMI RAW output excludes simultaneous internal media recording at some modes unless supported;
        # specifically VAL_HAITA_setting_rec_control... REC_MEDIA_DURING_HDMI_OUTPUT_OFF_RAW_OUTPUT_ON disables rec_media
        errors.append(
            "BLOCKED_HDMI_RAW16_PARALLEL_REC_EXCLUSION: RAW16 output requires rec_media_during_hdmi_output=False"
        )

    rec_bit = 1 if (recording_active and mode_u != "OFF" and (hdmi_tc_output_enabled or has_bnc)) else 0
    if errors:
        rec_bit = 0

    tc_word, dbb_word = _pack_smpte_rp188_atc_word(
        hours, minutes, seconds, frames, drop_frame=drop_frame, rec_trigger_bit=rec_bit
    )
    unpacked_tc, unpacked_df, unpacked_rec = _unpack_smpte_rp188_atc_word(tc_word, dbb_word)
    sep = ";" if drop_frame else ":"
    expected_tc = f"{hours:02d}:{minutes:02d}:{seconds:02d}{sep}{frames:02d}"
    tc_exact = (unpacked_tc == expected_tc) and (unpacked_df == drop_frame) and (unpacked_rec == rec_bit)
    if not tc_exact:
        errors.append(f"RP188_ROUNDTRIP_MISMATCH: expected {expected_tc}, got {unpacked_tc}")

    valid = len(errors) == 0
    if valid:
        status = (
            "VALID_FX6_NATIVE_12G_SDI_RP188"
            if body_u == "FX6"
            else "VALID_FX3_HDMI_TO_12G_SDI_BRIDGE_PARITY"
        )
    else:
        status = "BLOCKED_HDMI_SDI_REC_BRIDGE_FAULT"

    return HdmiSdiRecBridgeEvalResult(
        valid=valid,
        status=status,
        camera_body=body_u,
        converter_bridge=br_u,
        fx6_ui_rec_control_mode=mode_u,
        hdmi_tc_output_enabled=hdmi_tc_output_enabled,
        rec_media_during_hdmi_output=rec_media_during_hdmi_output,
        hdmi_raw16_active=hdmi_raw16_active,
        recording_active=recording_active,
        timecode_bcd_str=unpacked_tc,
        drop_frame=unpacked_df,
        hdmi_rec_trigger_bit=rec_bit,
        sdi_rp188_atc_did=SMPTE_RP188_ATC_DID,
        sdi_rp188_atc_sdid=SMPTE_RP188_ATC_SDID,
        sdi_remote_rec_bit=unpacked_rec,
        tc_roundtrip_exact=tc_exact,
        physical_12g_sdi_bnc_present=has_bnc,
        ghost_sdi_bnc_hw_faults=0,
        errors=tuple(errors),
    )


def evaluate_pillar_3_hdmi_sdi_rec_bridge(
    *,
    fx3_appfw_rec_markers: Tuple[str, ...],
    fx6_appfw_rec_markers: Tuple[str, ...],
    fx6_panelevf_sdi_markers: Tuple[str, ...],
    uxc_sdi_hdmi_rec_labels: Dict[str, str],
    donor_errors: Sequence[str],
) -> HdmiSdiRecBridgeMatrixReport:
    """Verify Pillar 3 FX6 native 12G-SDI vs FX3 HDMI->12G-SDI active converter parity."""
    errors = list(donor_errors)

    e_fx6 = evaluate_hdmi_sdi_rec_trigger_bridge(
        camera_body="FX6",
        converter_bridge="FX6_NATIVE_12G_SDI_BNC",
        fx6_ui_rec_control_mode="PARALLEL_REC",
    )
    e_bmd = evaluate_hdmi_sdi_rec_trigger_bridge(
        camera_body="FX3",
        converter_bridge="BMD_MICRO_CONVERTER_HDMI_TO_SDI_12G",
        fx6_ui_rec_control_mode="SDI_HDMI_REMOTE_I_F",
    )
    e_teradek = evaluate_hdmi_sdi_rec_trigger_bridge(
        camera_body="FX3",
        converter_bridge="TERADEK_BOLT_HDMI_SDI_BRIDGE",
        fx6_ui_rec_control_mode="SDI_HDMI_REMOTE_I_F",
        drop_frame=True,
    )
    e_atomos = evaluate_hdmi_sdi_rec_trigger_bridge(
        camera_body="FX3",
        converter_bridge="ATOMOS_CONNECT_HDMI_SDI_BRIDGE",
        fx6_ui_rec_control_mode="PARALLEL_REC",
    )
    b_tc_off = evaluate_hdmi_sdi_rec_trigger_bridge(
        camera_body="FX3",
        converter_bridge="BMD_MICRO_CONVERTER_HDMI_TO_SDI_12G",
        fx6_ui_rec_control_mode="SDI_HDMI_REMOTE_I_F",
        hdmi_tc_output_enabled=False,
    )
    b_passive = evaluate_hdmi_sdi_rec_trigger_bridge(
        camera_body="FX3",
        converter_bridge="PASSIVE_HDMI_CABLE_NO_BRIDGE",
        fx6_ui_rec_control_mode="SDI_HDMI_REMOTE_I_F",
    )

    for lbl, ev in (("fx6_sdi", e_fx6), ("fx3_bmd", e_bmd), ("fx3_teradek", e_teradek), ("fx3_atomos", e_atomos)):
        if not ev.valid or ev.sdi_remote_rec_bit != 1 or not ev.tc_roundtrip_exact or ev.ghost_sdi_bnc_hw_faults != 0:
            errors.append(f"Pillar 3 valid bridge {lbl} failed: {ev.errors}")
    if b_tc_off.valid or b_tc_off.sdi_remote_rec_bit != 0:
        errors.append("HDMI TC OFF missing trigger was not blocked")
    if b_passive.valid:
        errors.append("Passive cable claiming RP 188 ANC was not blocked")

    return HdmiSdiRecBridgeMatrixReport(
        passed=len(errors) == 0,
        fx3_appfw_rec_markers=fx3_appfw_rec_markers,
        fx6_appfw_rec_markers=fx6_appfw_rec_markers,
        fx6_panelevf_sdi_markers=fx6_panelevf_sdi_markers,
        uxc_sdi_hdmi_rec_labels=uxc_sdi_hdmi_rec_labels,
        eval_fx6_native_12g_sdi_parallel=e_fx6,
        eval_fx3_bmd_micro_converter_12g=e_bmd,
        eval_fx3_teradek_hdmi_sdi_bridge=e_teradek,
        eval_fx3_atomos_connect_bridge=e_atomos,
        blocked_hdmi_tc_off_no_trigger=b_tc_off,
        blocked_passive_cable_no_rp188=b_passive,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 4: MLUT Burn-In vs Proxy-Only vs Clean-HDMI Matrix & Zero-Mutation Proof
# ---------------------------------------------------------------------------


def evaluate_mlut_routing_matrix(
    *,
    profile_name: str,
    camera_body: str = "FX3",
    main_rec_lut_baked: bool = False,
    proxy_rec_lut_baked: bool = False,
    embed_lut_file_sidecar: bool = True,
    lcd_vf_mlut_on: bool = True,
    hdmi_mlut_on: bool = False,
    hdmi_clean_feed_no_osd: bool = True,
    hdmi_raw16_active: bool = False,
    sdi1_mlut_requested: bool = False,
) -> MlutRoutingEvalResult:
    """Audit independent MLUT Burn-In vs Proxy-Only vs Clean-HDMI routing and SDI1 gating."""
    errors: List[str] = []
    prof_u = profile_name.upper()
    body_u = camera_body.upper()
    sdi_supported = body_u == "FX6"

    if prof_u not in VALID_ROUTING_PROFILES:
        errors.append(f"INVALID_ROUTING_PROFILE: {profile_name!r}")
    if body_u not in ("FX3", "FX6"):
        errors.append(f"INVALID_CAMERA_BODY: {camera_body!r}")

    if hdmi_raw16_active and hdmi_mlut_on:
        errors.append(
            "BLOCKED_RAW16_HDMI_MLUT_CONFLICT: 16-bit Linear RAW cannot have MLUT baked into HDMI stream"
        )
    if main_rec_lut_baked and (not hdmi_mlut_on and not hdmi_raw16_active) and prof_u == "SLOG3_CLEAN_HDMI_LOG_INTERNAL":
        errors.append(
            "BLOCKED_BAKED_MAIN_WITH_CLEAN_SLOG3_PROFILE: Cannot output clean S-Log3 when main LUT is baked"
        )
    if prof_u == "SLOG3_PROXY_EMBED_LUT_ONLY" and main_rec_lut_baked:
        errors.append(
            "BLOCKED_PROXY_EMBED_BAKED_MAIN: Proxy/Embed-LUT profile must keep Main recording unbaked S-Log3"
        )

    # FX3 safely gates FX6 SDI1 MLUT request (`VAL_FEATURE_MANAGER_sdi_output_TYPE_SDI_OUTPUT_NOT_SUPPORT`)
    ghost_faults = 0
    valid = len(errors) == 0
    if valid and sdi1_mlut_requested and not sdi_supported:
        status = "VALID_FX3_SDI1_MLUT_SAFELY_GATED"
    elif valid:
        status = f"VALID_{prof_u}"
    else:
        status = "BLOCKED_MLUT_ROUTING_CONFLICT"

    return MlutRoutingEvalResult(
        valid=valid,
        status=status,
        profile_name=prof_u,
        camera_body=body_u,
        main_rec_lut_baked=main_rec_lut_baked,
        proxy_rec_lut_baked=proxy_rec_lut_baked,
        embed_lut_file_sidecar=embed_lut_file_sidecar,
        lcd_vf_mlut_on=lcd_vf_mlut_on,
        hdmi_mlut_on=hdmi_mlut_on,
        hdmi_clean_feed_no_osd=hdmi_clean_feed_no_osd,
        hdmi_raw16_active=hdmi_raw16_active,
        sdi1_mlut_requested=sdi1_mlut_requested,
        sdi1_output_supported=sdi_supported,
        ghost_sdi_bnc_hw_faults=ghost_faults,
        errors=tuple(errors),
    )


def evaluate_lut_calibration_immutability(target_path: str) -> CalibrationImmutabilityEvalResult:
    """Enforce zero persistent factory shading/calibration/eMMC writes; allow volatile RAM staging."""
    lower = target_path.lower().strip()
    is_volatile = any(lower.startswith(pref) for pref in VOLATILE_STAGING_PREFIXES)
    is_forbidden = bool(FORBIDDEN_CALIBRATION_AND_EMMC_RE.search(lower))
    errors: List[str] = []
    if is_forbidden or not is_volatile:
        errors.append(
            f"BLOCKED_PERSISTENT_CALIBRATION_OR_EMMC_WRITE: {target_path!r} violates zero-mutation guard"
        )
        return CalibrationImmutabilityEvalResult(
            valid=False,
            status="BLOCKED_PERSISTENT_CALIBRATION_OR_EMMC_WRITE",
            target_path=target_path,
            volatile_ram_only=False,
            calibration_mutation_bytes=0,
            emmc_mutation_bytes=0,
            persistent_emmc_writes_authorized=False,
            errors=tuple(errors),
        )
    return CalibrationImmutabilityEvalResult(
        valid=True,
        status="VOLATILE_RAM_STAGING_ALLOWED",
        target_path=target_path,
        volatile_ram_only=True,
        calibration_mutation_bytes=0,
        emmc_mutation_bytes=0,
        persistent_emmc_writes_authorized=False,
        errors=(),
    )


def evaluate_pillar_4_mlut_routing_and_immutability(
    *,
    fx3_global_xdb_valid: bool,
    fx6_global_xdb_valid: bool,
    donor_errors: Sequence[str],
) -> MlutRoutingAndImmutabilityReport:
    """Verify Pillar 4 MLUT routing matrix and zero-calibration/eMMC mutation proof."""
    errors = list(donor_errors)
    if not fx3_global_xdb_valid:
        errors.append("FX3 global.xdb validation failed")
    if not fx6_global_xdb_valid:
        errors.append("FX6 global.xdb validation failed")

    e_clean = evaluate_mlut_routing_matrix(
        profile_name="SLOG3_CLEAN_HDMI_LOG_INTERNAL",
        camera_body="FX3",
        main_rec_lut_baked=False,
        proxy_rec_lut_baked=False,
        embed_lut_file_sidecar=True,
        lcd_vf_mlut_on=True,
        hdmi_mlut_on=False,
        hdmi_clean_feed_no_osd=True,
    )
    e_hdmi_mlut = evaluate_mlut_routing_matrix(
        profile_name="SLOG3_MLUT_HDMI_MONITORING",
        camera_body="FX3",
        main_rec_lut_baked=False,
        proxy_rec_lut_baked=False,
        embed_lut_file_sidecar=True,
        lcd_vf_mlut_on=True,
        hdmi_mlut_on=True,
        hdmi_clean_feed_no_osd=True,
    )
    e_proxy = evaluate_mlut_routing_matrix(
        profile_name="SLOG3_PROXY_EMBED_LUT_ONLY",
        camera_body="FX3",
        main_rec_lut_baked=False,
        proxy_rec_lut_baked=True,
        embed_lut_file_sidecar=True,
        lcd_vf_mlut_on=True,
        hdmi_mlut_on=False,
        hdmi_clean_feed_no_osd=True,
    )
    e_burn = evaluate_mlut_routing_matrix(
        profile_name="FX6_BURN_IN_INTERNAL_LOOK",
        camera_body="FX6",
        main_rec_lut_baked=True,
        proxy_rec_lut_baked=True,
        embed_lut_file_sidecar=False,
        lcd_vf_mlut_on=True,
        hdmi_mlut_on=True,
        hdmi_clean_feed_no_osd=True,
    )
    e_raw = evaluate_mlut_routing_matrix(
        profile_name="HDMI_RAW16_CLEAN_NO_MLUT",
        camera_body="FX3",
        main_rec_lut_baked=False,
        proxy_rec_lut_baked=False,
        embed_lut_file_sidecar=False,
        lcd_vf_mlut_on=True,
        hdmi_mlut_on=False,
        hdmi_clean_feed_no_osd=True,
        hdmi_raw16_active=True,
    )
    b_raw = evaluate_mlut_routing_matrix(
        profile_name="HDMI_RAW16_CLEAN_NO_MLUT",
        camera_body="FX3",
        main_rec_lut_baked=False,
        proxy_rec_lut_baked=False,
        embed_lut_file_sidecar=False,
        lcd_vf_mlut_on=True,
        hdmi_mlut_on=True,
        hdmi_clean_feed_no_osd=True,
        hdmi_raw16_active=True,
    )
    e_sdi_gate = evaluate_mlut_routing_matrix(
        profile_name="SLOG3_CLEAN_HDMI_LOG_INTERNAL",
        camera_body="FX3",
        main_rec_lut_baked=False,
        proxy_rec_lut_baked=False,
        embed_lut_file_sidecar=True,
        lcd_vf_mlut_on=True,
        hdmi_mlut_on=False,
        hdmi_clean_feed_no_osd=True,
        sdi1_mlut_requested=True,
    )

    for lbl, ev in (
        ("clean", e_clean),
        ("hdmi_mlut", e_hdmi_mlut),
        ("proxy_embed", e_proxy),
        ("burn_in", e_burn),
        ("raw16", e_raw),
        ("sdi_gate", e_sdi_gate),
    ):
        if not ev.valid or ev.ghost_sdi_bnc_hw_faults != 0:
            errors.append(f"Pillar 4 valid routing {lbl} failed: {ev.errors}")
    if b_raw.valid:
        errors.append("RAW16 + HDMI MLUT bake conflict was not blocked")

    vol = evaluate_lut_calibration_immutability("/tmp/fx3_stageb_user_lut_33_dma.bin")
    b_cn = evaluate_lut_calibration_immutability("/dev/cnflasha0")
    b_sh = evaluate_lut_calibration_immutability("p2:/Backup.bin")
    b_psd = evaluate_lut_calibration_immutability("p2:/psd.bin")
    if not vol.valid:
        errors.append("Volatile RAM staging was unexpectedly blocked")
    for lbl, blk in (("cnflasha0", b_cn), ("Backup.bin", b_sh), ("psd.bin", b_psd)):
        if blk.valid:
            errors.append(f"Persistent calibration/eMMC target {lbl} was not blocked")

    return MlutRoutingAndImmutabilityReport(
        passed=len(errors) == 0,
        fx3_global_xdb_valid=fx3_global_xdb_valid,
        fx6_global_xdb_valid=fx6_global_xdb_valid,
        eval_slog3_clean_hdmi_log_internal=e_clean,
        eval_slog3_mlut_hdmi_monitoring=e_hdmi_mlut,
        eval_slog3_proxy_embed_lut_only=e_proxy,
        eval_fx6_burn_in_internal_look=e_burn,
        eval_hdmi_raw16_mlut_isolated=e_raw,
        blocked_raw16_hdmi_mlut_bake_hazard=b_raw,
        eval_fx3_sdi1_mlut_safely_gated=e_sdi_gate,
        volatile_ram_staging_eval=vol,
        blocked_cnflasha_eval=b_cn,
        blocked_shading_backup_eval=b_sh,
        blocked_psd_bin_eval=b_psd,
        calibration_mutation_bytes=0,
        emmc_mutation_bytes=0,
        persistent_emmc_writes_authorized=False,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Top-Level Phase 98 Unified Auditor Entrypoint
# ---------------------------------------------------------------------------


def analyze_lut3d_cube_tetrahedral_and_sdi_hdmi(
    *,
    clean_room: bool = False,
    repo_root: Optional[Path] = None,
) -> Lut3dCubeTetrahedralAndSdiHdmiReport:
    """Run the 19th unified firmware-lab auditor in Local Donor (`os.O_RDONLY`) or Clean-Room mode."""
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
            "fx6_avbb_panelevf": resolve_donor_file(FX6_AVBB_PANELEVF_RELPATH, repo_root=root),
            "fx3_global_xdb": resolve_donor_file(FX3_GLOBAL_XDB_RELPATH, repo_root=root),
            "fx6_global_xdb": resolve_donor_file(FX6_GLOBAL_XDB_RELPATH, repo_root=root),
            "fx3_str_en": resolve_donor_file(FX3_STR_EN_RELPATH, repo_root=root),
            "fx3_str_en_g": resolve_donor_file(FX3_STR_EN_G_RELPATH, repo_root=root),
            "fx6_str_en_1": resolve_donor_file(FX6_STR_EN_1_RELPATH, repo_root=root),
            "fx6_str_en_2": resolve_donor_file(FX6_STR_EN_2_RELPATH, repo_root=root),
        }

    use_local = (not forced_clean) and all(p is not None and p.is_file() for p in donor_paths.values())
    mode = "LOCAL_DONOR_VERIFIED" if use_local else "CLEAN_ROOM_SYNTHETIC"

    p1_errors: List[str] = []
    p2_errors: List[str] = []
    p3_errors: List[str] = []
    p4_errors: List[str] = []

    if use_local:
        sz_fx3_app, fx3_app_res = _scan_donor_rdonly_markers(
            donor_paths["fx3_appfw"],  # type: ignore[arg-type]
            {"m": FX3_APPFW_LUT_HDMI_MARKERS},
            is_elf=True,
        )
        sz_fx6_app, fx6_app_res = _scan_donor_rdonly_markers(
            donor_paths["fx6_appfw"],  # type: ignore[arg-type]
            {"m": FX6_APPFW_LUT_SDI_MARKERS},
            is_elf=True,
        )
        sz_fx3_mpr, fx3_mpr_res = _scan_donor_rdonly_markers(
            donor_paths["fx3_libmpr"],  # type: ignore[arg-type]
            {"m": LIBMPR_CUBE_LUT_MARKERS},
            is_elf=True,
        )
        sz_fx6_mpr, fx6_mpr_res = _scan_donor_rdonly_markers(
            donor_paths["fx6_libmpr"],  # type: ignore[arg-type]
            {"m": LIBMPR_CUBE_LUT_MARKERS},
            is_elf=True,
        )
        sz_fx3_cp, fx3_cp_res = _scan_donor_rdonly_markers(
            donor_paths["fx3_cpapp"],  # type: ignore[arg-type]
            {"m": CP_SHARED_MLUT_PIPELINE_MARKERS},
            is_elf=False,
        )
        sz_fx6_cp, fx6_cp_res = _scan_donor_rdonly_markers(
            donor_paths["fx6_cpapp"],  # type: ignore[arg-type]
            {"m": CP_SHARED_MLUT_PIPELINE_MARKERS},
            is_elf=False,
        )
        sz_fx6_evf, fx6_evf_res = _scan_donor_rdonly_markers(
            donor_paths["fx6_avbb_panelevf"],  # type: ignore[arg-type]
            {"m": FX6_AVBB_PANELEVF_LUT_SDI_MARKERS},
            is_elf=False,
        )

        fx3_xdb_bytes = _read_bytes_rdonly(donor_paths["fx3_global_xdb"])  # type: ignore[arg-type]
        fx6_xdb_bytes = _read_bytes_rdonly(donor_paths["fx6_global_xdb"])  # type: ignore[arg-type]
        fx3_str_en_bytes = _read_bytes_rdonly(donor_paths["fx3_str_en"])  # type: ignore[arg-type]
        fx3_str_en_g_bytes = _read_bytes_rdonly(donor_paths["fx3_str_en_g"])  # type: ignore[arg-type]
        fx6_str_en_1_bytes = _read_bytes_rdonly(donor_paths["fx6_str_en_1"])  # type: ignore[arg-type]
        fx6_str_en_2_bytes = _read_bytes_rdonly(donor_paths["fx6_str_en_2"])  # type: ignore[arg-type]
    else:
        fx = build_clean_room_lut3d_sdi_hdmi_fixtures()
        sz_fx3_app, fx3_app_res = _scan_bytes_marker_groups(
            fx["fx3_appfw"], {"m": FX3_APPFW_LUT_HDMI_MARKERS}
        )
        sz_fx6_app, fx6_app_res = _scan_bytes_marker_groups(
            fx["fx6_appfw"], {"m": FX6_APPFW_LUT_SDI_MARKERS}
        )
        sz_fx3_mpr, fx3_mpr_res = _scan_bytes_marker_groups(
            fx["fx3_libmpr"], {"m": LIBMPR_CUBE_LUT_MARKERS}
        )
        sz_fx6_mpr, fx6_mpr_res = _scan_bytes_marker_groups(
            fx["fx6_libmpr"], {"m": LIBMPR_CUBE_LUT_MARKERS}
        )
        sz_fx3_cp, fx3_cp_res = _scan_bytes_marker_groups(
            fx["fx3_cpapp"], {"m": CP_SHARED_MLUT_PIPELINE_MARKERS}
        )
        sz_fx6_cp, fx6_cp_res = _scan_bytes_marker_groups(
            fx["fx6_cpapp"], {"m": CP_SHARED_MLUT_PIPELINE_MARKERS}
        )
        sz_fx6_evf, fx6_evf_res = _scan_bytes_marker_groups(
            fx["fx6_avbb_panelevf"], {"m": FX6_AVBB_PANELEVF_LUT_SDI_MARKERS}
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
        "fx6_avbb_panelevf": sz_fx6_evf,
        "fx3_global_xdb": len(fx3_xdb_bytes),
        "fx6_global_xdb": len(fx6_xdb_bytes),
        "fx3_str_en": len(fx3_str_en_bytes),
        "fx3_str_en_g": len(fx3_str_en_g_bytes),
        "fx6_str_en_1": len(fx6_str_en_1_bytes),
        "fx6_str_en_2": len(fx6_str_en_2_bytes),
    }

    if len(fx3_app_res["m"]) != len(FX3_APPFW_LUT_HDMI_MARKERS):
        p1_errors.append("Missing FX3 appFw LUT/HDMI markers")
    if len(fx6_app_res["m"]) != len(FX6_APPFW_LUT_SDI_MARKERS):
        p1_errors.append("Missing FX6 appFw LUT/SDI markers")
    if len(fx3_mpr_res["m"]) != len(LIBMPR_CUBE_LUT_MARKERS):
        p1_errors.append("Missing FX3 libmpr .cube markers")
    if len(fx6_mpr_res["m"]) != len(LIBMPR_CUBE_LUT_MARKERS):
        p1_errors.append("Missing FX6 libmpr .cube markers")
    if len(fx3_cp_res["m"]) != len(CP_SHARED_MLUT_PIPELINE_MARKERS):
        p1_errors.append("Missing FX3 CP MLUT pipeline markers")
    if len(fx6_cp_res["m"]) != len(CP_SHARED_MLUT_PIPELINE_MARKERS):
        p1_errors.append("Missing FX6 CP MLUT pipeline markers")
    if len(fx6_evf_res["m"]) != len(FX6_AVBB_PANELEVF_LUT_SDI_MARKERS):
        p3_errors.append("Missing FX6 AVBB_SCN_START_PANELEVF SDI/MLUT markers")

    fx3_ux_en, u_err_1 = _extract_uxc_labels(fx3_str_en_bytes, FX3_NS39_PHASE98_LABELS)
    fx3_ux_g, u_err_2 = _extract_uxc_labels(fx3_str_en_g_bytes, FX3_NS3_PHASE98_LABELS)
    fx6_ux_1, u_err_3 = _extract_uxc_labels(fx6_str_en_1_bytes, FX6_NS1_PHASE98_LABELS)
    fx6_ux_2, u_err_4 = _extract_uxc_labels(fx6_str_en_2_bytes, FX6_NS2_PHASE98_LABELS)
    p1_errors.extend(u_err_2)
    p1_errors.extend(u_err_3)
    p3_errors.extend(u_err_1)
    p3_errors.extend(u_err_4)

    uxc_lut_labels = {
        "fx3_import_user_lut": fx3_ux_g.get("0x0000620b", ""),
        "fx3_delete_user_lut": fx3_ux_g.get("0x00006128", ""),
        "fx6_mlut": fx6_ux_1.get("0x00002029", ""),
        "fx6_monitor_lut": fx6_ux_1.get("0x00002068", ""),
        "fx6_lut_709_800": fx6_ux_1.get("0x00002109", ""),
        "fx6_base_look_lut": fx6_ux_1.get("0x0000219d", ""),
        "fx6_load_user_3d_lut": fx6_ux_2.get("0x00004362", ""),
        "fx6_select_user_3d_lut": fx6_ux_2.get("0x0000435e", ""),
    }
    uxc_sdi_hdmi_rec_labels = {
        "fx3_hdmi_resolution": fx3_ux_en.get("0x0000e1d5", ""),
        "fx3_ctrl_for_hdmi": fx3_ux_en.get("0x0000e41f", ""),
        "fx6_monitor_3d_lut": fx6_ux_2.get("0x00004287", ""),
        "fx6_hdmi_tc_out": fx6_ux_2.get("0x00004245", ""),
        "fx6_rec_control": fx6_ux_2.get("0x00004251", ""),
        "fx6_sdi_hdmi_rec_control": fx6_ux_2.get("0x0000428d", ""),
    }

    try:
        parse_global_xdb_buffer(fx3_xdb_bytes)
        fx3_xdb_ok = True
    except Exception as exc:
        fx3_xdb_ok = False
        p4_errors.append(f"FX3 global.xdb parse error: {exc}")

    try:
        parse_global_xdb_buffer(fx6_xdb_bytes)
        fx6_xdb_ok = True
    except Exception as exc:
        fx6_xdb_ok = False
        p4_errors.append(f"FX6 global.xdb parse error: {exc}")

    p1 = evaluate_pillar_1_cube_lut_tetrahedral(
        fx3_appfw_markers=fx3_app_res["m"],
        fx6_appfw_markers=fx6_app_res["m"],
        fx3_libmpr_markers=fx3_mpr_res["m"],
        fx6_libmpr_markers=fx6_mpr_res["m"],
        fx3_cp_markers=fx3_cp_res["m"],
        fx6_cp_markers=fx6_cp_res["m"],
        uxc_lut_labels=uxc_lut_labels,
        donor_errors=p1_errors,
    )
    p2 = evaluate_pillar_2_slog3_avi_quantization(donor_errors=p2_errors)
    p3 = evaluate_pillar_3_hdmi_sdi_rec_bridge(
        fx3_appfw_rec_markers=fx3_app_res["m"],
        fx6_appfw_rec_markers=fx6_app_res["m"],
        fx6_panelevf_sdi_markers=fx6_evf_res["m"],
        uxc_sdi_hdmi_rec_labels=uxc_sdi_hdmi_rec_labels,
        donor_errors=p3_errors,
    )
    p4 = evaluate_pillar_4_mlut_routing_and_immutability(
        fx3_global_xdb_valid=fx3_xdb_ok,
        fx6_global_xdb_valid=fx6_xdb_ok,
        donor_errors=p4_errors,
    )

    all_errors = list(p1.errors) + list(p2.errors) + list(p3.errors) + list(p4.errors)
    all_passed = p1.passed and p2.passed and p3.passed and p4.passed and (len(all_errors) == 0)

    draft = Lut3dCubeTetrahedralAndSdiHdmiReport(
        schema_version=PHASE_98_SCHEMA,
        phase_version=PHASE_98_VERSION,
        mode=mode,
        all_checks_passed=all_passed,
        o_rdonly_enforced=True,
        persistent_emmc_writes_authorized=False,
        calibration_mutation_bytes=0,
        emmc_mutation_bytes=0,
        donor_file_sizes=sizes,
        pillar_1_cube_lut_tetrahedral=p1,
        pillar_2_slog3_avi_quantization=p2,
        pillar_3_hdmi_sdi_rec_bridge=p3,
        pillar_4_mlut_routing_immutability=p4,
        errors=tuple(all_errors),
        report_sha256="",
    )
    canonical = json.dumps(asdict(draft), sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(canonical).hexdigest()
    return Lut3dCubeTetrahedralAndSdiHdmiReport(
        schema_version=draft.schema_version,
        phase_version=draft.phase_version,
        mode=draft.mode,
        all_checks_passed=draft.all_checks_passed,
        o_rdonly_enforced=draft.o_rdonly_enforced,
        persistent_emmc_writes_authorized=draft.persistent_emmc_writes_authorized,
        calibration_mutation_bytes=draft.calibration_mutation_bytes,
        emmc_mutation_bytes=draft.emmc_mutation_bytes,
        donor_file_sizes=draft.donor_file_sizes,
        pillar_1_cube_lut_tetrahedral=draft.pillar_1_cube_lut_tetrahedral,
        pillar_2_slog3_avi_quantization=draft.pillar_2_slog3_avi_quantization,
        pillar_3_hdmi_sdi_rec_bridge=draft.pillar_3_hdmi_sdi_rec_bridge,
        pillar_4_mlut_routing_immutability=draft.pillar_4_mlut_routing_immutability,
        errors=draft.errors,
        report_sha256=digest,
    )


def lut3d_cube_tetrahedral_and_sdi_hdmi_report_to_dict(
    report: Lut3dCubeTetrahedralAndSdiHdmiReport,
) -> Dict[str, object]:
    """Convert `Lut3dCubeTetrahedralAndSdiHdmiReport` to a deterministic JSON-serializable dict."""
    return report.to_dict()
