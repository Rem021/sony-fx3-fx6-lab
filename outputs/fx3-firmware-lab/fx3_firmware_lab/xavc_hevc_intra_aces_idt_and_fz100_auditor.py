"""Phase 133 — 26th Unified Firmware-Lab Auditor: BIONZ XR XAVC HS (HEVC 10-Bit 4:2:2)
vs XAVC S-I (All-Intra) Hardware VBR/CBR GOP Matrix, ACES 1.3/2.0 S-Log3 /
S-Gamut3.Cine AP0/AP1 IDT Matrix Verifier, & NP-FZ100 InfoLITHIUM C-Pin /
SMBus Fuel-Gauge & Counterfeit-Pack Handshake Auditor.

Strictly Read-Only (`os.O_RDONLY` + `mmap.ACCESS_READ`) & Clean-Room Dual-Mode:
- Local Donor Mode: inspects FX3 v7.02 (`appFw.so`, `libmpr.so`, `cpapp-b.bin`,
  `global.xdb`, `string_english.uxc`, `string_english_g.uxc`) and FX6 v6.01
  (`appFw.so`, `libmpr.so`, `cpapp-b.bin`, `global.xdb`, `string_english.uxc`,
  `string_english_2.uxc`) strictly via `os.O_RDONLY` + `mmap.ACCESS_READ` and
  ELF64 `.rodata`/`.dynstr`/`.data.rel.ro`/`.strtab` section-scoped scanning plus
  `uxa\\x07`/`.uxc` container parsing (< 0.35s total).
- Clean-Room Mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`, `clean_room=True`, or donors
  absent): synthesizes deterministic clean-room ELF64 / CP / `global.xdb` /
  `.uxc` fixtures carrying the exact verified contract markers and runs the
  identical four-pillar verification pipeline (< 0.02s warm, zero proprietary
  files required).

Audits Four Phase 133 Pillars:
1. Pillar A — `BIONZ XR` Hardware Codec Translator (`FX6 XAVC-I Class 300 MXF`
   <-> `FX3 XAVC S-I 4K 240..600 Mbps` & `XAVC HS HEVC 4:2:2 10-bit`, Long-GOP
   vs All-Intra VBV buffer & `VPG200/VPG400` media bitrate budget).
2. Pillar B — `ACES 1.3 / 2.0` `S-Log3` Piece-Wise Log<->Linear Transfer Function
   (`x >= 171.2102946929 / 1023.0` vs linear toe; CV `95/420/598`) &
   `S-Gamut3.Cine / S-Gamut3 -> ACES2065-1 (AP0) / ACEScg (AP1)` `3x3` Matrix
   Invertibility & White-Point (`1.0, 1.0, 1.0`) Conservation Verifier
   (`max_whitepoint_error < 1e-4`, supporting both `BRADFORD` and `CAT02`).
3. Pillar C — `NP-FZ100` (`7.2V` FX3) vs `BP-U35/U70` (`14.4V` FX6) `InfoLITHIUM`
   Battery-Telemetry & Regulated Dummy-Battery `C-Pin` Safe Degradation Contract
   (proving FX6 `14.4V` / `19.5V DC IN` thresholds in `appFw.so` never falsely
   trigger `LOW_BATTERY_SHUTDOWN` on FX3's `7.2V` `NP-FZ100` rail in Stage-B).
4. Pillar D — Volatile RAM Staging & Zero Persistent `eMMC` / Calibration
   Mutation Proof (`emmc_mutation_bytes == 0`, `calibration_mutation_bytes == 0`,
   `persistent_emmc_writes_authorized == False`).
"""

from __future__ import annotations

import hashlib
import math
import mmap
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from .emount_af_breathing_and_ibis_auditor import (
    _extract_uxc_labels,
    _parse_elf64_sections,
)
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
from .sensor_codec_compatibility_analyzer import (
    FX3_CPAPP_RELPATH,
    FX3_LIBMPR_RELPATH,
    FX6_CPAPP_RELPATH,
    FX6_LIBMPR_RELPATH,
)


PHASE_133_SCHEMA = "fx3_firmware_lab_phase133_xavc_hevc_aces_fz100_v1"
PHASE_133_VERSION = "133.0.0"

# ---------------------------------------------------------------------------
# Pillar A Constants: BIONZ XR XAVC HS (HEVC) vs XAVC S-I / XAVC-I Matrix
# ---------------------------------------------------------------------------

VALID_CODEC_PROFILES: Tuple[str, ...] = (
    "FX6_XAVC_I_CLASS300_MXF",
    "FX3_XAVC_S_I_4K_MP4",
    "FX3_XAVC_HS_4K_HEVC_422_10BIT",
    "FX3_XAVC_HS_4K_HEVC_420_10BIT",
    "FX6_XAVC_L_4K_420_8BIT",
)

VALID_CODEC_FPS: Tuple[float, ...] = (23.976, 24.0, 25.0, 29.97, 50.0, 59.94, 100.0, 119.88)
XAVC_HS_FORBIDDEN_FPS_FX3: Tuple[float, ...] = (25.0, 29.97)

# Sustained media card write ceiling in MB/s (1 MB/s = 8 Mbps)
MEDIA_SPEED_CLASSES_MBPS: Dict[str, float] = {
    "SDXC_V30": 240.0,           # 30 MB/s
    "SDXC_V60": 480.0,           # 60 MB/s
    "SDXC_V90": 720.0,           # 90 MB/s
    "CFEXPRESS_A_VPG200": 1600.0,  # 200 MB/s
    "CFEXPRESS_A_VPG400": 3200.0,  # 400 MB/s
}

# Bitrate tables (Mbps) keyed by fps
ALL_INTRA_4K_BITRATES_MBPS: Dict[float, float] = {
    23.976: 240.0,
    24.0: 240.0,
    25.0: 250.0,
    29.97: 300.0,
    50.0: 500.0,
    59.94: 600.0,
    100.0: 1000.0,  # S&Q 100p (effective stream bitrate on media)
    119.88: 1200.0,  # S&Q 120p (requires CFexpress VPG200/VPG400)
}

XAVC_HS_4K_422_10BIT_BITRATES_MBPS: Dict[float, Tuple[float, ...]] = {
    23.976: (100.0, 50.0),
    24.0: (100.0, 50.0),
    50.0: (200.0, 100.0),
    59.94: (200.0, 100.0),
    100.0: (280.0,),
    119.88: (280.0,),
}

XAVC_HS_4K_420_10BIT_BITRATES_MBPS: Dict[float, Tuple[float, ...]] = {
    23.976: (75.0, 45.0, 30.0),
    24.0: (75.0, 45.0, 30.0),
    50.0: (150.0, 75.0, 45.0),
    59.94: (150.0, 75.0, 45.0),
    100.0: (200.0,),
    119.88: (200.0,),
}

FX6_XAVC_L_4K_420_8BIT_BITRATES_MBPS: Dict[float, float] = {
    23.976: 100.0,
    24.0: 100.0,
    25.0: 100.0,
    29.97: 100.0,
    50.0: 150.0,
    59.94: 150.0,
}

# ---------------------------------------------------------------------------
# Pillar B Constants: ACES 1.3 / 2.0 S-Log3 & S-Gamut3(.Cine) -> AP0 / AP1
# ---------------------------------------------------------------------------

SLOG3_BLACK_CV10 = 95.0
SLOG3_GRAY_18_CV10 = 420.0
SLOG3_WHITE_90_CV10 = 598.0
SLOG3_BREAK_CV10 = 171.2102946929
SLOG3_BREAK_LIN = 0.01125000
SLOG3_BREAK_NORM = SLOG3_BREAK_CV10 / 1023.0
SLOG3_LIN_OFFSET = 0.01
SLOG3_LIN_SCALE = 0.18 + 0.01
SLOG3_LOG_SLOPE = 261.5
SLOG3_TOE_SLOPE = (SLOG3_BREAK_CV10 - SLOG3_BLACK_CV10) / SLOG3_BREAK_LIN

ACES_MAX_WHITEPOINT_ERROR = 1e-4
ACES_MIN_DET_ABS = 0.50

CIE_WP_D65: Tuple[float, float] = (0.3127, 0.3290)
CIE_WP_ACES: Tuple[float, float] = (0.32168, 0.33767)

GAMUT_PRIMARIES_XY: Dict[str, Tuple[Tuple[float, float], Tuple[float, float], Tuple[float, float], Tuple[float, float]]] = {
    "S_GAMUT3": ((0.730, 0.280), (0.140, 0.855), (0.100, -0.050), CIE_WP_D65),
    "S_GAMUT3_CINE": ((0.766, 0.275), (0.225, 0.800), (0.089, -0.087), CIE_WP_D65),
    "ACES2065_1_AP0": ((0.73470, 0.26530), (0.00000, 1.00000), (0.00010, -0.07700), CIE_WP_ACES),
    "ACESCG_AP1": ((0.71300, 0.29300), (0.16500, 0.83000), (0.12800, 0.04400), CIE_WP_ACES),
}

CAT_BRADFORD_3X3: Tuple[Tuple[float, float, float], ...] = (
    (0.8951000, 0.2664000, -0.1614000),
    (-0.7502000, 1.7135000, 0.0367000),
    (0.0389000, -0.0685000, 1.0296000),
)

CAT_CAT02_3X3: Tuple[Tuple[float, float, float], ...] = (
    (0.7328000, 0.4296000, -0.1624000),
    (-0.7036000, 1.6975000, 0.0061000),
    (0.0030000, 0.0136000, 0.9834000),
)

ACES_OCIO_CLF_TRANSFORM_IDS: Dict[str, str] = {
    "S_GAMUT3": "urn:ampas:aces:transformId:v2.0:CSC.Sony.SLog3_SGamut3_to_ACES.a2.v1",
    "S_GAMUT3_CINE": "urn:ampas:aces:transformId:v2.0:CSC.Sony.SLog3_SGamut3Cine_to_ACES.a2.v1",
}

VALID_SOURCE_GAMUTS: Tuple[str, ...] = ("S_GAMUT3", "S_GAMUT3_CINE")
VALID_TARGET_ACES_SPACES: Tuple[str, ...] = ("ACES2065_1_AP0", "ACESCG_AP1")
VALID_ADAPTATION_TRANSFORMS: Tuple[str, ...] = ("BRADFORD", "CAT02")

# ---------------------------------------------------------------------------
# Pillar C Constants: NP-FZ100 (7.2V) vs BP-U35/U70 (14.4V) & C-Pin Guard
# ---------------------------------------------------------------------------

NP_FZ100_NOMINAL_MV = 7200
NP_FZ100_MAX_SAFE_MV = 8400
NP_FZ100_MIN_SAFE_MV = 6000
NP_FZ100_NEAR_END_MV = 6400
NP_FZ100_CAPACITY_MAH = 2280
NP_FZ100_ENERGY_WH = 16.4
NP_FZ100_FW_UPDATE_MIN_SOC_PCT = 51

BP_U_NOMINAL_MV = 14400
BP_U_NEAR_END_MV = 12800
BP_U_SHUTDOWN_MV = 12000
FX6_DC_IN_NOMINAL_MV = 19500
FX6_DC_IN_LOW_MV = 18000

BATTERY_SAFE_TEMP_MIN_C = 0.0
BATTERY_SAFE_TEMP_MAX_C = 60.0

VALID_BATTERY_PACK_TYPES: Tuple[str, ...] = (
    "OEM_NP_FZ100",
    "DECODED_3P_NP_FZ100",
    "UNDECODED_3P_NP_FZ100",
    "REGULATED_DUMMY_CPIN_ABSENT",
    "UNREGULATED_DANGEROUS_DUMMY",
    "FX6_BP_U35_14V4_NATIVE",
)

VALID_CAMERA_POWER_RAILS: Tuple[str, ...] = (
    "FX3_7V2_NP_FZ100",
    "FX6_14V4_BP_U",
)

# ---------------------------------------------------------------------------
# Pillar D Constants: Volatile RAM Staging & Zero Persistent eMMC Guard
# ---------------------------------------------------------------------------

VOLATILE_STAGING_PREFIXES_P133: Tuple[str, ...] = ("/tmp/", "ram://", "memory://")
FORBIDDEN_PERSISTENT_EMMC_RE_P133 = re.compile(
    r"(?:^|/)(?:p(?:[1-9]|1[0-8])|nflasha\d*|cnflasha\d*|mmcblk0(?:p\d+|rpmb)?|mtdblock\d*)(?:/|:|$)"
    r"|bodydata\.dat|udtrfirm|psd\.bin|defdet\.bin|backup\.bin|jiritsu|updater://|nvram://|eeprom://",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Verified Binary & .uxc Marker Contracts (FX3 v7.02 & FX6 v6.01)
# ---------------------------------------------------------------------------

FX3_APPFW_PHASE133_MARKERS: Tuple[str, ...] = (
    "SQ_RECORD_SETTING_XAVC_HS_4K_120P_100P_280M_422_10BIT",
    "SQ_RECORD_SETTING_XAVC_HS_4K_24P_100M_422_10BIT",
    "CAUTION_ID_XAVC_S_I_TRANSFER_RATE_DISABLE_UNDER_400MBPS_MEDIA_SLOT1_MSG",
    "CAUTION_ID_FACTOR_XAVC_HS_4K_RESTRICTED_STREAMING_ON_25P",
    "VAL_HAITA_setting_pictureprofile_colormode_setting_picture_profile0_SETTING_PICTUREPROFILE_COLORMODE_SGAMUT3",
    "VAL_HAITA_setting_pictureprofile_colormode_setting_picture_profile0_SETTING_PICTUREPROFILE_COLORMODE_SGAMUT3_CINE",
    "VAL_HAITA_setting_pictureprofile_gamma_setting_picture_profile0_SETTING_PICTUREPROFILE_GAMMA_SLOG3",
    "OFF_BY_BATT_DEAD",
    "OFF_BY_BATT_END",
    "OFF_BY_BATT_INVALID",
    "INFRA_NOTIFY_BATTERY_REMAIN",
    "VAL_battery_status_BATTERY_STATUS_INVALID",
)

FX6_APPFW_PHASE133_MARKERS: Tuple[str, ...] = (
    "SETTING_PICTUREPROFILE_COLORMODE_SGAMUT3",
    "SETTING_PICTUREPROFILE_COLORMODE_SGAMUT3_CINE",
    "SETTING_PICTUREPROFILE_GAMMA_SLOG3",
    "ATTACHED_BATTERY_TYPE_SONY_INFO",
    "BATTERY_TYPE_DC_IN",
    "BKID_APP_USER_MENU_DC_VOLTAGE_ALARM0",
    "VAL_power_supply_end_status_DC_VOLTAGE_END",
    "VAL_power_supply_end_status_SONY_INFO_BATTERY_END",
    "OFF_BY_BATT_LOW",
)

FX3_LIBMPR_PHASE133_MARKERS: Tuple[str, ...] = (
    "HEVC_3840_2160_M42210P",
    "HEVC_3840_2160_M10P",
    "AVC480_3840_2160_H422IP",
    "AVC480CBG_4096_2160_H422IP",
    "_ZN9RateCheck49getMediaTransferRateCheckType_Normal_HEVC_Long_4KEN3mpr13movieRecParamE",
)

FX6_LIBMPR_PHASE133_MARKERS: Tuple[str, ...] = (
    "HEVC_3840_2160_M42210P",
    "HEVC_3840_2160_M10P",
    "AVC480_3840_2160_H422IP",
    "AVC480CBG_4096_2160_H422IP",
    "LOG_ID_LIBXAVCMXF_MUX",
    "LOG_ID_LIBXAVCMP4",
)

CP_SHARED_PHASE133_MARKERS: Tuple[str, ...] = (
    "BATT_AUTH_Snd",
    "BATT_STATE1_Snd",
    "BATT_STATE2_Snd",
    "BATT_TYPE1_Snd",
)

FX3_NS39_PHASE133_LABELS: Dict[int, str] = {
    0x0000E02E: (
        "Cannot record in this setting. Either\nswitch to a memory card higher than\n"
        "CFexpress VPG200 or change the\n\ue660File Format. You may be able to\n"
        "record by setting \ue5cbProxy Recording to\n\"Off\". Slot 2"
    ),
    0x0000E24E: "The operation and safety of this battery\ncannot be guaranteed.\nContinue use?",
    0x0000E704: "Battery exhausted.",
}

FX3_NS3_PHASE133_LABELS: Dict[int, str] = {
    0x00006013: "Update cannot be executed due to\ninsufficient battery power.",
    0x000060CE: (
        "Cannot perform this operation for movies\nrecorded with their \"\ue660File Format\"\n"
        "set to \"XAVC S-I DCI 4K\"."
    ),
}

FX6_NS1_PHASE133_LABELS: Dict[int, str] = {
    0x0000219F: "S-Log3",
    0x00002B03: "XAVC S-I",
    0x00002693: "Battery Error\nPlease Change Battery",
}

FX6_NS2_PHASE133_LABELS: Dict[int, str] = {
    0x00004005: "Voltage Low",
    0x00004269: "DC Voltage Alarm",
    0x000044FE: "S-Gamut \u2192 S-Gamut3.Cine",
    0x00004550: "Battery Remain",
}

# ---------------------------------------------------------------------------
# Dataclasses (JSON-clean: no raw bytes attributes)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class XavcCodecProfileEvalResult:
    valid: bool
    status: str
    codec_profile: str
    container_format: str
    compression_scheme: str
    gop_mode: str
    bit_depth: int
    chroma_subsampling: str
    fps: float
    bitrate_mbps: float
    media_card_class: str
    media_ceiling_mbps: float
    vbv_buffer_kbytes: int
    storage_gb_per_hour: float
    bitstream_lossless_rewrap_compatible: bool
    hw_decode_engine_recommended: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class BionzXrCodecMatrixReport:
    passed: bool
    fx3_appfw_codec_markers: Tuple[str, ...]
    fx3_libmpr_codec_markers: Tuple[str, ...]
    fx6_libmpr_codec_markers: Tuple[str, ...]
    uxc_codec_labels: Dict[str, str]
    eval_fx6_xavc_i_class300_2398p_mxf: XavcCodecProfileEvalResult
    eval_fx3_xavc_s_i_4k60_600mbps_v90: XavcCodecProfileEvalResult
    eval_fx3_xavc_s_i_sq120_1200mbps_vpg200: XavcCodecProfileEvalResult
    eval_fx3_xavc_hs_4k60_200mbps_422_10bit: XavcCodecProfileEvalResult
    eval_fx3_xavc_hs_4k24_100mbps_422_10bit: XavcCodecProfileEvalResult
    blocked_xavc_hs_2997p_fx3_gap: XavcCodecProfileEvalResult
    blocked_xavc_s_i_sq120_under_v60_card: XavcCodecProfileEvalResult
    blocked_xavc_s_i_600mbps_under_v60_card: XavcCodecProfileEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class SLog3TransferProofResult:
    valid: bool
    status: str
    black_0pct_cv10: float
    gray_18pct_cv10: float
    white_90pct_cv10: float
    breakpoint_lin: float
    breakpoint_cv10: float
    toe_continuity_delta: float
    max_roundtrip_error: float
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class AcesIdtMatrixEvalResult:
    valid: bool
    status: str
    source_gamut: str
    target_space: str
    adaptation_method: str
    ocio_transform_id: str
    matrix_3x3: Tuple[Tuple[float, float, float], ...]
    inverse_3x3: Tuple[Tuple[float, float, float], ...]
    determinant: float
    max_inv_roundtrip_error: float
    mapped_whitepoint: Tuple[float, float, float]
    max_whitepoint_error: float
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class AcesSLog3IdtMatrixReport:
    passed: bool
    fx3_appfw_gamut_markers: Tuple[str, ...]
    fx6_appfw_gamut_markers: Tuple[str, ...]
    uxc_gamut_labels: Dict[str, str]
    slog3_transfer_proof: SLog3TransferProofResult
    eval_sgamut3_cine_to_ap0_bradford: AcesIdtMatrixEvalResult
    eval_sgamut3_cine_to_ap1_bradford: AcesIdtMatrixEvalResult
    eval_sgamut3_to_ap0_bradford: AcesIdtMatrixEvalResult
    eval_sgamut3_to_ap1_bradford: AcesIdtMatrixEvalResult
    eval_sgamut3_cine_to_ap0_cat02: AcesIdtMatrixEvalResult
    eval_sgamut3_to_ap0_cat02: AcesIdtMatrixEvalResult
    cat02_vs_bradford_max_entry_delta: float
    blocked_singular_matrix_guard: AcesIdtMatrixEvalResult
    blocked_whitepoint_drift_guard: AcesIdtMatrixEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class BatteryHandshakeEvalResult:
    valid: bool
    status: str
    pack_type: str
    camera_rail: str
    stage_b_fx6_overlay_active: bool
    pack_voltage_mv: int
    soc_pct: Optional[int]
    temp_c: float
    c_pin_auth_passed: bool
    c_pin_telemetry_present: bool
    degraded_power_mode: bool
    percentage_display_visible: bool
    fw_update_allowed: bool
    false_low_batt_shutdown_triggered: bool
    safe_to_operate: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class NpFz100BatteryHandshakeReport:
    passed: bool
    fx3_appfw_batt_markers: Tuple[str, ...]
    fx6_appfw_batt_markers: Tuple[str, ...]
    fx3_cp_batt_markers: Tuple[str, ...]
    fx6_cp_batt_markers: Tuple[str, ...]
    uxc_batt_labels: Dict[str, str]
    eval_oem_np_fz100_stageb_fx6_ui: BatteryHandshakeEvalResult
    eval_decoded_3p_np_fz100_ok: BatteryHandshakeEvalResult
    eval_undecoded_3p_confirmed_degraded: BatteryHandshakeEvalResult
    eval_regulated_dummy_cpin_absent_confirmed: BatteryHandshakeEvalResult
    eval_fx6_bpu35_14v4_native: BatteryHandshakeEvalResult
    blocked_false_fx6_14v4_threshold_on_fx3_7v2: BatteryHandshakeEvalResult
    blocked_unregulated_overvolt_dummy: BatteryHandshakeEvalResult
    blocked_undecoded_user_cancelled: BatteryHandshakeEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Phase133WriteGuardResult:
    valid: bool
    status: str
    target_path: str
    volatile_ram_staged: bool
    persistent_write_blocked: bool
    emmc_mutation_bytes: int
    calibration_mutation_bytes: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class ZeroMutationPhase133GuardReport:
    passed: bool
    fx3_global_xdb_valid: bool
    fx6_global_xdb_valid: bool
    volatile_staging_guard: Phase133WriteGuardResult
    blocked_bodydata_dat_guard: Phase133WriteGuardResult
    blocked_nflasha15_guard: Phase133WriteGuardResult
    blocked_cnflasha0_guard: Phase133WriteGuardResult
    blocked_backup_bin_guard: Phase133WriteGuardResult
    emmc_mutation_bytes: int
    calibration_mutation_bytes: int
    persistent_emmc_writes_authorized: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class XavcHevcIntraAcesIdtAndFz100Report:
    schema_version: str
    phase_version: str
    mode: str
    all_checks_passed: bool
    donor_file_sizes: Dict[str, int]
    pillar_a_bionz_xr_codec_matrix: BionzXrCodecMatrixReport
    pillar_b_aces_slog3_idt_matrix: AcesSLog3IdtMatrixReport
    pillar_c_np_fz100_battery_handshake: NpFz100BatteryHandshakeReport
    pillar_d_zero_mutation_guard: ZeroMutationPhase133GuardReport
    report_sha256: str
    errors: Tuple[str, ...]


# ---------------------------------------------------------------------------
# Strictly Read-Only ELF64 / Donor Scanner Helpers (`os.O_RDONLY` + `mmap`)
# ---------------------------------------------------------------------------


def _read_bytes_rdonly(path: Path) -> bytes:
    fd = os.open(path, os.O_RDONLY)
    try:
        st = os.fstat(fd)
        if st.st_size == 0:
            return b""
        mm = mmap.mmap(fd, 0, access=mmap.ACCESS_READ)
        try:
            return bytes(mm)
        finally:
            mm.close()
    finally:
        os.close(fd)


def _scan_donor_rdonly_markers(
    path: Path,
    marker_groups: Dict[str, Tuple[str, ...]],
    *,
    is_elf: bool = True,
) -> Tuple[int, Dict[str, Tuple[str, ...]]]:
    """Scan ELF64 `.rodata`/`.dynstr` (or raw buffer) strictly `os.O_RDONLY` + `mmap.ACCESS_READ`."""
    fd = os.open(path, os.O_RDONLY)
    try:
        st = os.fstat(fd)
        size = int(st.st_size)
        if size == 0:
            return 0, {k: () for k in marker_groups}
        mm = mmap.mmap(fd, 0, access=mmap.ACCESS_READ)
        try:
            windows: List[Tuple[int, int]] = []
            if is_elf:
                try:
                    sections = _parse_elf64_sections(mm)
                except ValueError:
                    sections = {}
                for sec_name in (".rodata", ".dynstr", ".data.rel.ro", ".strtab"):
                    if sec_name in sections:
                        off, sec_sz = sections[sec_name]
                        if sec_sz > 0 and off + sec_sz <= size:
                            windows.append((off, off + sec_sz))
            if not windows:
                windows = [(0, size)]

            found: Dict[str, Tuple[str, ...]] = {}
            for group_name, tokens in marker_groups.items():
                matched: List[str] = []
                for tok in tokens:
                    needle = tok.encode("latin1")
                    if any(mm.find(needle, start, end) != -1 for start, end in windows):
                        matched.append(tok)
                found[group_name] = tuple(matched)
            return size, found
        finally:
            mm.close()
    finally:
        os.close(fd)


def _scan_bytes_marker_groups(
    data: bytes,
    marker_groups: Dict[str, Tuple[str, ...]],
) -> Tuple[int, Dict[str, Tuple[str, ...]]]:
    found: Dict[str, Tuple[str, ...]] = {}
    for group_name, tokens in marker_groups.items():
        found[group_name] = tuple(tok for tok in tokens if tok.encode("latin1") in data)
    return len(data), found


# ---------------------------------------------------------------------------
# Pillar A Functions: BIONZ XR XAVC HS (HEVC) vs XAVC S-I / XAVC-I Matrix
# ---------------------------------------------------------------------------


def evaluate_bionz_xr_codec_profile(
    *,
    codec_profile: str = "FX3_XAVC_S_I_4K_MP4",
    fps: float = 23.976,
    requested_bitrate_mbps: Optional[float] = None,
    media_card_class: str = "CFEXPRESS_A_VPG200",
    proxy_enabled: bool = False,
) -> XavcCodecProfileEvalResult:
    """Evaluate BIONZ XR XAVC HS (HEVC) vs XAVC S-I / XAVC-I GOP, VBV & card speed class."""
    prof = codec_profile.strip().upper()
    card = media_card_class.strip().upper()
    if prof not in VALID_CODEC_PROFILES:
        raise ValueError(f"Unsupported codec_profile={codec_profile!r}")
    if card not in MEDIA_SPEED_CLASSES_MBPS:
        raise ValueError(f"Unsupported media_card_class={media_card_class!r}")
    if fps not in VALID_CODEC_FPS:
        raise ValueError(f"Unsupported fps={fps!r}")

    media_ceil = MEDIA_SPEED_CLASSES_MBPS[card]
    errors: List[str] = []
    container = "MXF_OP1A" if prof.startswith("FX6_") else "MP4_ISOBMFF"
    bitrate = 0.0
    bit_depth = 10
    chroma = "4:2:2"
    scheme = "AVC_H264_HIGH_422_INTRA"
    gop_mode = "ALL_INTRA_CBG"
    vbv_kb = 0
    rewrap_ok = False
    hw_dec = False

    if prof in ("FX6_XAVC_I_CLASS300_MXF", "FX3_XAVC_S_I_4K_MP4"):
        bitrate = ALL_INTRA_4K_BITRATES_MBPS[fps]
        if requested_bitrate_mbps is not None and abs(requested_bitrate_mbps - bitrate) > 1.0:
            errors.append(
                f"BLOCKED_ALL_INTRA_FIXED_RATE_MISMATCH: {prof} at {fps}p locks to "
                f"{bitrate:.0f} Mbps, got {requested_bitrate_mbps:.0f} Mbps"
            )
        # All-Intra VBV buffer ~ 1 frame payload + 25% header margin
        vbv_kb = int(round((bitrate * 1000.0 / 8.0) / min(fps, 59.94) * 1.25))
        rewrap_ok = True
        hw_dec = False
        if fps >= 100.0 and prof == "FX3_XAVC_S_I_4K_MP4":
            if card not in ("CFEXPRESS_A_VPG200", "CFEXPRESS_A_VPG400"):
                errors.append(
                    f"BLOCKED_INSUFFICIENT_MEDIA_SPEED_CLASS: {prof} S&Q {fps}p ({bitrate:.0f} Mbps) "
                    f"requires CFexpress Type A VPG200+, rejected on {card}"
                )
    elif prof in ("FX3_XAVC_HS_4K_HEVC_422_10BIT", "FX3_XAVC_HS_4K_HEVC_420_10BIT"):
        scheme = "HEVC_H265_MAIN_422_10" if "422" in prof else "HEVC_H265_MAIN_10"
        chroma = "4:2:2" if "422" in prof else "4:2:0"
        gop_mode = "LONG_GOP_VBR"
        hw_dec = True
        table = (
            XAVC_HS_4K_422_10BIT_BITRATES_MBPS
            if "422" in prof
            else XAVC_HS_4K_420_10BIT_BITRATES_MBPS
        )
        if fps in XAVC_HS_FORBIDDEN_FPS_FX3 or fps not in table:
            errors.append(
                f"BLOCKED_XAVC_HS_UNSUPPORTED_FPS: FX3 {prof} does not support {fps}p internally "
                "(requires XAVC S or XAVC S-I for 25p/29.97p)"
            )
            bitrate = 0.0
        else:
            allowed_rates = table[fps]
            bitrate = allowed_rates[0] if requested_bitrate_mbps is None else requested_bitrate_mbps
            if bitrate not in allowed_rates:
                errors.append(
                    f"BLOCKED_INVALID_XAVC_HS_BITRATE: {bitrate:.0f} Mbps not in {allowed_rates} for {fps}p"
                )
        # Long-GOP VBV CPB: ~1.5s burst headroom in KB
        vbv_kb = int(round(bitrate * 1000.0 / 8.0 * 1.5))
    else:  # FX6_XAVC_L_4K_420_8BIT
        scheme = "AVC_H264_HIGH_420_8"
        bit_depth = 8
        chroma = "4:2:0"
        gop_mode = "LONG_GOP_VBR"
        if fps not in FX6_XAVC_L_4K_420_8BIT_BITRATES_MBPS:
            errors.append(f"BLOCKED_XAVC_L_UNSUPPORTED_FPS: {fps}p not supported in FX6 XAVC-L 4K")
        else:
            bitrate = FX6_XAVC_L_4K_420_8BIT_BITRATES_MBPS[fps]
        vbv_kb = int(round(bitrate * 1000.0 / 8.0 * 1.5))

    effective_mbps = bitrate + (16.0 if (proxy_enabled and fps < 100.0) else 0.0)
    if effective_mbps > media_ceil:
        errors.append(
            f"BLOCKED_INSUFFICIENT_MEDIA_SPEED_CLASS: {effective_mbps:.0f} Mbps exceeds {card} "
            f"sustained ceiling ({media_ceil:.0f} Mbps)"
        )

    gb_per_hr = round(bitrate * 3600.0 / 8000.0, 2)
    status = "BIONZ_XR_CODEC_MATRIX_VERIFIED" if not errors else errors[0].split(":", 1)[0]
    return XavcCodecProfileEvalResult(
        valid=len(errors) == 0,
        status=status,
        codec_profile=prof,
        container_format=container,
        compression_scheme=scheme,
        gop_mode=gop_mode,
        bit_depth=bit_depth,
        chroma_subsampling=chroma,
        fps=fps,
        bitrate_mbps=bitrate,
        media_card_class=card,
        media_ceiling_mbps=media_ceil,
        vbv_buffer_kbytes=vbv_kb,
        storage_gb_per_hour=gb_per_hr,
        bitstream_lossless_rewrap_compatible=rewrap_ok,
        hw_decode_engine_recommended=hw_dec,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar B Functions: ACES 1.3 / 2.0 S-Log3 & S-Gamut3(.Cine) IDT Verifier
# ---------------------------------------------------------------------------


def slog3_linear_to_norm(linear_reflection: float) -> float:
    """Sony official S-Log3 Scene-Linear Reflection -> Normalized Code [0..1]."""
    if not math.isfinite(linear_reflection):
        raise ValueError("linear_reflection must be finite")
    if linear_reflection >= SLOG3_BREAK_LIN:
        cv = SLOG3_GRAY_18_CV10 + math.log10((linear_reflection + SLOG3_LIN_OFFSET) / SLOG3_LIN_SCALE) * SLOG3_LOG_SLOPE
    else:
        cv = linear_reflection * SLOG3_TOE_SLOPE + SLOG3_BLACK_CV10
    return cv / 1023.0


def slog3_norm_to_linear(slog3_norm: float) -> float:
    """Sony official Normalized S-Log3 [0..1] -> Scene-Linear Reflection."""
    if not math.isfinite(slog3_norm):
        raise ValueError("slog3_norm must be finite")
    cv = slog3_norm * 1023.0
    if slog3_norm >= SLOG3_BREAK_NORM:
        return (10.0 ** ((cv - SLOG3_GRAY_18_CV10) / SLOG3_LOG_SLOPE)) * SLOG3_LIN_SCALE - SLOG3_LIN_OFFSET
    return (cv - SLOG3_BLACK_CV10) / SLOG3_TOE_SLOPE


def verify_slog3_transfer_landmarks() -> SLog3TransferProofResult:
    """Verify Sony S-Log3 landmarks (95 / 420 / 598), C0 toe continuity & roundtrip precision."""
    errors: List[str] = []
    cv_0 = slog3_linear_to_norm(0.0) * 1023.0
    cv_18 = slog3_linear_to_norm(0.18) * 1023.0
    cv_90 = slog3_linear_to_norm(0.90) * 1023.0

    # Check exact piece-wise C0 continuity at x_break = 0.01125000
    cv_toe_break = (SLOG3_BREAK_LIN * SLOG3_TOE_SLOPE + SLOG3_BLACK_CV10)
    cv_log_break = SLOG3_GRAY_18_CV10 + math.log10((SLOG3_BREAK_LIN + SLOG3_LIN_OFFSET) / SLOG3_LIN_SCALE) * SLOG3_LOG_SLOPE
    toe_delta = abs(cv_toe_break - cv_log_break)

    if abs(cv_0 - 95.0) > 1e-6:
        errors.append(f"S-Log3 0% black CV {cv_0:.6f} != 95.0")
    if abs(cv_18 - 420.0) > 1e-6:
        errors.append(f"S-Log3 18% gray CV {cv_18:.6f} != 420.0")
    if abs(cv_90 - 598.0) > 0.25:
        errors.append(f"S-Log3 90% white CV {cv_90:.6f} outside 598 +/- 0.25")
    if toe_delta > 1e-6:
        errors.append(f"S-Log3 piece-wise break discontinuity {toe_delta:.9e}")

    max_rt = 0.0
    for lin in (0.0, 0.002, 0.008, 0.01125, 0.05, 0.18, 0.90, 2.5, 10.0, 38.4):
        norm = slog3_linear_to_norm(lin)
        rt = slog3_norm_to_linear(norm)
        max_rt = max(max_rt, abs(rt - lin))
    if max_rt > 1e-11:
        errors.append(f"S-Log3 roundtrip inversion residual {max_rt:.3e} > 1e-11")

    status = "SLOG3_PIECEWISE_VERIFIED" if not errors else "SLOG3_TRANSFER_ERROR"
    return SLog3TransferProofResult(
        valid=len(errors) == 0,
        status=status,
        black_0pct_cv10=round(cv_0, 6),
        gray_18pct_cv10=round(cv_18, 6),
        white_90pct_cv10=round(cv_90, 6),
        breakpoint_lin=SLOG3_BREAK_LIN,
        breakpoint_cv10=SLOG3_BREAK_CV10,
        toe_continuity_delta=toe_delta,
        max_roundtrip_error=max_rt,
        errors=tuple(errors),
    )


def matrix_determinant_3x3(m: Sequence[Sequence[float]]) -> float:
    a, b, c = m[0]
    d, e, f = m[1]
    g, h, i = m[2]
    return a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)


def invert_3x3_matrix(m: Sequence[Sequence[float]]) -> Tuple[Tuple[float, float, float], ...]:
    det = matrix_determinant_3x3(m)
    if abs(det) < 1e-12:
        raise ValueError(f"Singular 3x3 matrix (det={det:.3e})")
    a, b, c = m[0]
    d, e, f = m[1]
    g, h, i = m[2]
    return (
        ((e * i - f * h) / det, (c * h - b * i) / det, (b * f - c * e) / det),
        ((f * g - d * i) / det, (a * i - c * g) / det, (c * d - a * f) / det),
        ((d * h - e * g) / det, (b * g - a * h) / det, (a * e - b * d) / det),
    )


def _matmul3(a: Sequence[Sequence[float]], b: Sequence[Sequence[float]]) -> Tuple[Tuple[float, float, float], ...]:
    return tuple(
        tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3))
        for i in range(3)
    )


def _matvec3(a: Sequence[Sequence[float]], v: Sequence[float]) -> Tuple[float, float, float]:
    return (
        a[0][0] * v[0] + a[0][1] * v[1] + a[0][2] * v[2],
        a[1][0] * v[0] + a[1][1] * v[1] + a[1][2] * v[2],
        a[2][0] * v[0] + a[2][1] * v[1] + a[2][2] * v[2],
    )


def compute_rgb_to_xyz_3x3(
    r_xy: Tuple[float, float],
    g_xy: Tuple[float, float],
    b_xy: Tuple[float, float],
    w_xy: Tuple[float, float],
) -> Tuple[Tuple[float, float, float], ...]:
    xr, yr = r_xy
    xg, yg = g_xy
    xb, yb = b_xy
    xw, yw = w_xy
    m_prim = (
        (xr / yr, xg / yg, xb / yb),
        (1.0, 1.0, 1.0),
        ((1.0 - xr - yr) / yr, (1.0 - xg - yg) / yg, (1.0 - xb - yb) / yb),
    )
    w_xyz = (xw / yw, 1.0, (1.0 - xw - yw) / yw)
    s = _matvec3(invert_3x3_matrix(m_prim), w_xyz)
    return tuple(tuple(m_prim[r][c] * s[c] for c in range(3)) for r in range(3))


def compute_chromatic_adaptation_3x3(
    method: str,
    src_wp: Tuple[float, float],
    dst_wp: Tuple[float, float],
) -> Tuple[Tuple[float, float, float], ...]:
    m_cat = CAT_BRADFORD_3X3 if method == "BRADFORD" else CAT_CAT02_3X3
    src_xyz = (src_wp[0] / src_wp[1], 1.0, (1.0 - src_wp[0] - src_wp[1]) / src_wp[1])
    dst_xyz = (dst_wp[0] / dst_wp[1], 1.0, (1.0 - dst_wp[0] - dst_wp[1]) / dst_wp[1])
    src_cone = _matvec3(m_cat, src_xyz)
    dst_cone = _matvec3(m_cat, dst_xyz)
    diag = (
        (dst_cone[0] / src_cone[0], 0.0, 0.0),
        (0.0, dst_cone[1] / src_cone[1], 0.0),
        (0.0, 0.0, dst_cone[2] / src_cone[2]),
    )
    return _matmul3(invert_3x3_matrix(m_cat), _matmul3(diag, m_cat))


def compute_aces_idt_matrix_3x3(
    source_gamut: str,
    target_space: str,
    adaptation_method: str = "BRADFORD",
) -> Tuple[Tuple[float, float, float], ...]:
    """Compute exact 3x3 linear IDT matrix from Sony S-Gamut3(.Cine) to ACES AP0 or AP1."""
    src = source_gamut.strip().upper()
    dst = target_space.strip().upper()
    cat = adaptation_method.strip().upper()
    if src not in VALID_SOURCE_GAMUTS:
        raise ValueError(f"Unsupported source_gamut={source_gamut!r}")
    if dst not in VALID_TARGET_ACES_SPACES:
        raise ValueError(f"Unsupported target_space={target_space!r}")
    if cat not in VALID_ADAPTATION_TRANSFORMS:
        raise ValueError(f"Unsupported adaptation_method={adaptation_method!r}")

    m_src = compute_rgb_to_xyz_3x3(*GAMUT_PRIMARIES_XY[src])
    m_dst_inv = invert_3x3_matrix(compute_rgb_to_xyz_3x3(*GAMUT_PRIMARIES_XY[dst]))
    m_adapt = compute_chromatic_adaptation_3x3(cat, CIE_WP_D65, CIE_WP_ACES)
    return _matmul3(m_dst_inv, _matmul3(m_adapt, m_src))


def verify_aces_idt_matrix(
    *,
    source_gamut: str = "S_GAMUT3_CINE",
    target_space: str = "ACES2065_1_AP0",
    adaptation_method: str = "BRADFORD",
    custom_matrix: Optional[Sequence[Sequence[float]]] = None,
) -> AcesIdtMatrixEvalResult:
    """Verify 3x3 ACES IDT matrix invertibility and (1.0, 1.0, 1.0) white-point conservation."""
    src = source_gamut.strip().upper()
    dst = target_space.strip().upper()
    cat = adaptation_method.strip().upper()
    if src not in VALID_SOURCE_GAMUTS:
        raise ValueError(f"Unsupported source_gamut={source_gamut!r}")
    if dst not in VALID_TARGET_ACES_SPACES:
        raise ValueError(f"Unsupported target_space={target_space!r}")
    if cat not in VALID_ADAPTATION_TRANSFORMS:
        raise ValueError(f"Unsupported adaptation_method={adaptation_method!r}")

    mat = (
        tuple(tuple(float(x) for x in r) for r in custom_matrix)
        if custom_matrix is not None
        else compute_aces_idt_matrix_3x3(src, dst, cat)
    )
    errors: List[str] = []
    det = matrix_determinant_3x3(mat)
    inv_mat: Tuple[Tuple[float, float, float], ...] = ((0.0, 0.0, 0.0),) * 3
    max_inv_err = 1.0

    if not math.isfinite(det) or abs(det) < 1e-6:
        errors.append(f"BLOCKED_SINGULAR_IDT_MATRIX: det={det:.3e} < 1e-6")
    else:
        if abs(det) < ACES_MIN_DET_ABS:
            errors.append(f"BLOCKED_DEGENERATE_IDT_DETERMINANT: |det|={abs(det):.4f} < {ACES_MIN_DET_ABS}")
        inv_mat = invert_3x3_matrix(mat)
        prod = _matmul3(mat, inv_mat)
        max_inv_err = max(
            abs(prod[i][j] - (1.0 if i == j else 0.0))
            for i in range(3)
            for j in range(3)
        )
        if max_inv_err > 1e-9:
            errors.append(f"BLOCKED_MATRIX_INVERSION_RESIDUAL: {max_inv_err:.3e} > 1e-9")

    wp = _matvec3(mat, (1.0, 1.0, 1.0))
    wp_err = max(abs(wp[0] - 1.0), abs(wp[1] - 1.0), abs(wp[2] - 1.0))
    if wp_err >= ACES_MAX_WHITEPOINT_ERROR:
        errors.append(
            f"BLOCKED_WHITEPOINT_CONSERVATION_DRIFT: max_whitepoint_error={wp_err:.3e} >= {ACES_MAX_WHITEPOINT_ERROR}"
        )

    status = "ACES_IDT_MATRIX_VERIFIED" if not errors else errors[0].split(":", 1)[0]
    return AcesIdtMatrixEvalResult(
        valid=len(errors) == 0,
        status=status,
        source_gamut=src,
        target_space=dst,
        adaptation_method=cat,
        ocio_transform_id=ACES_OCIO_CLF_TRANSFORM_IDS[src],
        matrix_3x3=tuple(tuple(round(x, 12) for x in r) for r in mat),
        inverse_3x3=tuple(tuple(round(x, 12) for x in r) for r in inv_mat),
        determinant=round(det, 12),
        max_inv_roundtrip_error=max_inv_err,
        mapped_whitepoint=tuple(round(v, 12) for v in wp),  # type: ignore[arg-type]
        max_whitepoint_error=wp_err,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar C Functions: NP-FZ100 InfoLITHIUM C-Pin & Cross-Rail Voltage Guard
# ---------------------------------------------------------------------------


def evaluate_np_fz100_battery_handshake(
    *,
    pack_type: str = "OEM_NP_FZ100",
    camera_rail: str = "FX3_7V2_NP_FZ100",
    pack_voltage_mv: int = 7600,
    reported_soc_pct: Optional[int] = 78,
    temp_c: float = 28.0,
    c_pin_connected: bool = True,
    c_pin_auth_valid: bool = True,
    user_confirmed_continue: bool = True,
    stage_b_fx6_overlay_active: bool = True,
    fx6_ui_normalized_pct_mapped: bool = True,
) -> BatteryHandshakeEvalResult:
    """Audit NP-FZ100 C-pin InfoLITHIUM handshake & Stage-B FX6 14.4V threshold isolation."""
    pack = pack_type.strip().upper()
    rail = camera_rail.strip().upper()
    if pack not in VALID_BATTERY_PACK_TYPES:
        raise ValueError(f"Unsupported pack_type={pack_type!r}")
    if rail not in VALID_CAMERA_POWER_RAILS:
        raise ValueError(f"Unsupported camera_rail={camera_rail!r}")

    errors: List[str] = []
    degraded = False
    pct_visible = True
    fw_allowed = True
    false_shutdown = False
    safe_op = True

    # Thermal check
    if not (BATTERY_SAFE_TEMP_MIN_C <= temp_c <= BATTERY_SAFE_TEMP_MAX_C):
        safe_op = False
        fw_allowed = False
        errors.append(f"BLOCKED_BATTERY_THERMAL_SHUTDOWN: temp_c={temp_c:.1f}C outside [0..60]C")

    # Rail voltage envelope check
    if rail == "FX3_7V2_NP_FZ100":
        if pack_voltage_mv > NP_FZ100_MAX_SAFE_MV or pack_voltage_mv < NP_FZ100_MIN_SAFE_MV:
            safe_op = False
            fw_allowed = False
            errors.append(
                f"BLOCKED_BATTERY_RAIL_OUT_OF_SAFE_ENVELOPE: {pack_voltage_mv} mV outside "
                f"[{NP_FZ100_MIN_SAFE_MV}..{NP_FZ100_MAX_SAFE_MV}] mV for FX3 7.2V rail"
            )
        # Crucial Stage-B guard: FX6 appFw.so 14.4V (12.0V shutdown) must NEVER compare raw mV
        # against FX3's 7.2V NP-FZ100 rail!
        if stage_b_fx6_overlay_active and not fx6_ui_normalized_pct_mapped:
            false_shutdown = True
            safe_op = False
            fw_allowed = False
            errors.append(
                f"BLOCKED_FALSE_FX6_14V4_LOW_BATT_SHUTDOWN: unmapped FX6 14.4V threshold ({BP_U_SHUTDOWN_MV} mV) "
                f"falsely trips OFF_BY_BATT_LOW on healthy {pack_voltage_mv} mV FX3 NP-FZ100 rail"
            )
    else:  # FX6_14V4_BP_U
        if pack_voltage_mv < BP_U_SHUTDOWN_MV or pack_voltage_mv > 20500:
            safe_op = False
            fw_allowed = False
            errors.append(
                f"BLOCKED_FX6_BP_U_VOLTAGE_END: {pack_voltage_mv} mV outside safe FX6 BP-U/DC-IN envelope"
            )

    # C-pin authentication & safe degradation contract
    auth_ok = bool(c_pin_connected and c_pin_auth_valid and pack in ("OEM_NP_FZ100", "DECODED_3P_NP_FZ100", "FX6_BP_U35_14V4_NATIVE"))
    if not auth_ok:
        pct_visible = False
        fw_allowed = False
        if not user_confirmed_continue:
            safe_op = False
            errors.append(
                "BLOCKED_UNVERIFIED_BATTERY_USER_CANCELLED: C-pin handshake failed (STRID 0x0000e24e) "
                "and user selected Cancel -> clean power-off"
            )
        elif safe_op:
            degraded = True

    if auth_ok:
        soc = reported_soc_pct if reported_soc_pct is not None else round(
            max(0.0, min(100.0, (pack_voltage_mv - NP_FZ100_MIN_SAFE_MV) / (NP_FZ100_MAX_SAFE_MV - NP_FZ100_MIN_SAFE_MV) * 100.0))
        )
        if soc < NP_FZ100_FW_UPDATE_MIN_SOC_PCT:
            fw_allowed = False
    else:
        soc = None

    if errors:
        status = errors[0].split(":", 1)[0]
    elif degraded:
        status = "SAFE_DEGRADED_POWER_NO_PCT"
    else:
        status = "INFOLITHIUM_C_PIN_VERIFIED"

    return BatteryHandshakeEvalResult(
        valid=len(errors) == 0,
        status=status,
        pack_type=pack,
        camera_rail=rail,
        stage_b_fx6_overlay_active=stage_b_fx6_overlay_active,
        pack_voltage_mv=pack_voltage_mv,
        soc_pct=soc,
        temp_c=temp_c,
        c_pin_auth_passed=auth_ok,
        c_pin_telemetry_present=c_pin_connected,
        degraded_power_mode=degraded,
        percentage_display_visible=pct_visible,
        fw_update_allowed=fw_allowed,
        false_low_batt_shutdown_triggered=false_shutdown,
        safe_to_operate=safe_op,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar D Functions: Volatile RAM Staging & Zero Persistent eMMC Mutation Guard
# ---------------------------------------------------------------------------


def evaluate_phase133_write_guard(target_path: str) -> Phase133WriteGuardResult:
    """Enforce volatile RAM staging only and zero persistent eMMC/OTA/calibration mutation."""
    norm = target_path.strip()
    is_volatile = norm.startswith(VOLATILE_STAGING_PREFIXES_P133) and not bool(
        FORBIDDEN_PERSISTENT_EMMC_RE_P133.search(norm)
    )
    if is_volatile:
        return Phase133WriteGuardResult(
            valid=True,
            status="VOLATILE_RAM_STAGING_ALLOWED",
            target_path=norm,
            volatile_ram_staged=True,
            persistent_write_blocked=False,
            emmc_mutation_bytes=0,
            calibration_mutation_bytes=0,
            errors=(),
        )
    return Phase133WriteGuardResult(
        valid=False,
        status="BLOCKED_PERSISTENT_EMMC_OR_OTA_WRITE",
        target_path=norm,
        volatile_ram_staged=False,
        persistent_write_blocked=True,
        emmc_mutation_bytes=0,
        calibration_mutation_bytes=0,
        errors=(f"BLOCKED_PERSISTENT_EMMC_OR_OTA_WRITE: target_path={norm!r}",),
    )


# ---------------------------------------------------------------------------
# Pillar Evaluators & Top-Level Phase 133 Unified Auditor
# ---------------------------------------------------------------------------


def evaluate_pillar_a_bionz_xr_codec_matrix(
    *,
    fx3_appfw_codec_markers: Tuple[str, ...],
    fx3_libmpr_codec_markers: Tuple[str, ...],
    fx6_libmpr_codec_markers: Tuple[str, ...],
    uxc_codec_labels: Dict[str, str],
    extra_errors: Sequence[str] = (),
) -> BionzXrCodecMatrixReport:
    errors = list(extra_errors)

    e_fx6_mxf = evaluate_bionz_xr_codec_profile(
        codec_profile="FX6_XAVC_I_CLASS300_MXF",
        fps=23.976,
        media_card_class="CFEXPRESS_A_VPG200",
    )
    e_fx3_si_600 = evaluate_bionz_xr_codec_profile(
        codec_profile="FX3_XAVC_S_I_4K_MP4",
        fps=59.94,
        media_card_class="SDXC_V90",
    )
    e_fx3_si_120 = evaluate_bionz_xr_codec_profile(
        codec_profile="FX3_XAVC_S_I_4K_MP4",
        fps=119.88,
        media_card_class="CFEXPRESS_A_VPG400",
    )
    e_fx3_hs_60 = evaluate_bionz_xr_codec_profile(
        codec_profile="FX3_XAVC_HS_4K_HEVC_422_10BIT",
        fps=59.94,
        requested_bitrate_mbps=200.0,
        media_card_class="SDXC_V60",
    )
    e_fx3_hs_24 = evaluate_bionz_xr_codec_profile(
        codec_profile="FX3_XAVC_HS_4K_HEVC_422_10BIT",
        fps=23.976,
        requested_bitrate_mbps=100.0,
        media_card_class="SDXC_V60",
    )
    b_hs_2997 = evaluate_bionz_xr_codec_profile(
        codec_profile="FX3_XAVC_HS_4K_HEVC_422_10BIT",
        fps=29.97,
        media_card_class="CFEXPRESS_A_VPG200",
    )
    b_si_120_v60 = evaluate_bionz_xr_codec_profile(
        codec_profile="FX3_XAVC_S_I_4K_MP4",
        fps=119.88,
        media_card_class="SDXC_V60",
    )
    b_si_600_v60 = evaluate_bionz_xr_codec_profile(
        codec_profile="FX3_XAVC_S_I_4K_MP4",
        fps=59.94,
        media_card_class="SDXC_V60",
    )

    for lbl, ev in (
        ("fx6_xavc_i", e_fx6_mxf),
        ("fx3_si_600", e_fx3_si_600),
        ("fx3_si_120", e_fx3_si_120),
        ("fx3_hs_60", e_fx3_hs_60),
        ("fx3_hs_24", e_fx3_hs_24),
    ):
        if not ev.valid:
            errors.append(f"Positive BIONZ XR codec check {lbl} failed: {ev.errors}")
    for lbl, blk in (
        ("hs_2997p", b_hs_2997),
        ("si_120_v60", b_si_120_v60),
        ("si_600_v60", b_si_600_v60),
    ):
        if blk.valid:
            errors.append(f"Negative BIONZ XR codec guard {lbl} unexpectedly passed")

    return BionzXrCodecMatrixReport(
        passed=len(errors) == 0,
        fx3_appfw_codec_markers=fx3_appfw_codec_markers,
        fx3_libmpr_codec_markers=fx3_libmpr_codec_markers,
        fx6_libmpr_codec_markers=fx6_libmpr_codec_markers,
        uxc_codec_labels=uxc_codec_labels,
        eval_fx6_xavc_i_class300_2398p_mxf=e_fx6_mxf,
        eval_fx3_xavc_s_i_4k60_600mbps_v90=e_fx3_si_600,
        eval_fx3_xavc_s_i_sq120_1200mbps_vpg200=e_fx3_si_120,
        eval_fx3_xavc_hs_4k60_200mbps_422_10bit=e_fx3_hs_60,
        eval_fx3_xavc_hs_4k24_100mbps_422_10bit=e_fx3_hs_24,
        blocked_xavc_hs_2997p_fx3_gap=b_hs_2997,
        blocked_xavc_s_i_sq120_under_v60_card=b_si_120_v60,
        blocked_xavc_s_i_600mbps_under_v60_card=b_si_600_v60,
        errors=tuple(errors),
    )


def evaluate_pillar_b_aces_slog3_idt_matrix(
    *,
    fx3_appfw_gamut_markers: Tuple[str, ...],
    fx6_appfw_gamut_markers: Tuple[str, ...],
    uxc_gamut_labels: Dict[str, str],
    extra_errors: Sequence[str] = (),
) -> AcesSLog3IdtMatrixReport:
    errors = list(extra_errors)

    slog3_proof = verify_slog3_transfer_landmarks()
    if not slog3_proof.valid:
        errors.extend(slog3_proof.errors)

    e_cine_ap0_b = verify_aces_idt_matrix(
        source_gamut="S_GAMUT3_CINE",
        target_space="ACES2065_1_AP0",
        adaptation_method="BRADFORD",
    )
    e_cine_ap1_b = verify_aces_idt_matrix(
        source_gamut="S_GAMUT3_CINE",
        target_space="ACESCG_AP1",
        adaptation_method="BRADFORD",
    )
    e_sg3_ap0_b = verify_aces_idt_matrix(
        source_gamut="S_GAMUT3",
        target_space="ACES2065_1_AP0",
        adaptation_method="BRADFORD",
    )
    e_sg3_ap1_b = verify_aces_idt_matrix(
        source_gamut="S_GAMUT3",
        target_space="ACESCG_AP1",
        adaptation_method="BRADFORD",
    )
    e_cine_ap0_c = verify_aces_idt_matrix(
        source_gamut="S_GAMUT3_CINE",
        target_space="ACES2065_1_AP0",
        adaptation_method="CAT02",
    )
    e_sg3_ap0_c = verify_aces_idt_matrix(
        source_gamut="S_GAMUT3",
        target_space="ACES2065_1_AP0",
        adaptation_method="CAT02",
    )

    cat_delta = max(
        abs(e_cine_ap0_c.matrix_3x3[r][c] - e_cine_ap0_b.matrix_3x3[r][c])
        for r in range(3)
        for c in range(3)
    )

    b_singular = verify_aces_idt_matrix(
        source_gamut="S_GAMUT3_CINE",
        target_space="ACES2065_1_AP0",
        adaptation_method="BRADFORD",
        custom_matrix=(
            (0.5, 0.5, 0.0),
            (0.5, 0.5, 0.0),
            (0.0, 0.0, 1.0),
        ),
    )
    b_wp_drift = verify_aces_idt_matrix(
        source_gamut="S_GAMUT3_CINE",
        target_space="ACES2065_1_AP0",
        adaptation_method="BRADFORD",
        custom_matrix=(
            (0.65, 0.27, 0.09),  # row sum = 1.01 -> +1% red tint shift
            (0.00, 1.08, -0.08),
            (-0.03, -0.02, 1.05),
        ),
    )

    for lbl, ev in (
        ("cine_ap0_bradford", e_cine_ap0_b),
        ("cine_ap1_bradford", e_cine_ap1_b),
        ("sg3_ap0_bradford", e_sg3_ap0_b),
        ("sg3_ap1_bradford", e_sg3_ap1_b),
        ("cine_ap0_cat02", e_cine_ap0_c),
        ("sg3_ap0_cat02", e_sg3_ap0_c),
    ):
        if not ev.valid or ev.max_whitepoint_error >= ACES_MAX_WHITEPOINT_ERROR:
            errors.append(f"Positive ACES IDT matrix check {lbl} failed: {ev.errors}")
    for lbl, blk in (("singular", b_singular), ("wp_drift", b_wp_drift)):
        if blk.valid:
            errors.append(f"Negative ACES IDT matrix guard {lbl} unexpectedly passed")

    return AcesSLog3IdtMatrixReport(
        passed=len(errors) == 0,
        fx3_appfw_gamut_markers=fx3_appfw_gamut_markers,
        fx6_appfw_gamut_markers=fx6_appfw_gamut_markers,
        uxc_gamut_labels=uxc_gamut_labels,
        slog3_transfer_proof=slog3_proof,
        eval_sgamut3_cine_to_ap0_bradford=e_cine_ap0_b,
        eval_sgamut3_cine_to_ap1_bradford=e_cine_ap1_b,
        eval_sgamut3_to_ap0_bradford=e_sg3_ap0_b,
        eval_sgamut3_to_ap1_bradford=e_sg3_ap1_b,
        eval_sgamut3_cine_to_ap0_cat02=e_cine_ap0_c,
        eval_sgamut3_to_ap0_cat02=e_sg3_ap0_c,
        cat02_vs_bradford_max_entry_delta=round(cat_delta, 9),
        blocked_singular_matrix_guard=b_singular,
        blocked_whitepoint_drift_guard=b_wp_drift,
        errors=tuple(errors),
    )


def evaluate_pillar_c_np_fz100_battery_handshake(
    *,
    fx3_appfw_batt_markers: Tuple[str, ...],
    fx6_appfw_batt_markers: Tuple[str, ...],
    fx3_cp_batt_markers: Tuple[str, ...],
    fx6_cp_batt_markers: Tuple[str, ...],
    uxc_batt_labels: Dict[str, str],
    extra_errors: Sequence[str] = (),
) -> NpFz100BatteryHandshakeReport:
    errors = list(extra_errors)

    e_oem = evaluate_np_fz100_battery_handshake(
        pack_type="OEM_NP_FZ100",
        camera_rail="FX3_7V2_NP_FZ100",
        pack_voltage_mv=7650,
        reported_soc_pct=82,
        stage_b_fx6_overlay_active=True,
        fx6_ui_normalized_pct_mapped=True,
    )
    e_dec3p = evaluate_np_fz100_battery_handshake(
        pack_type="DECODED_3P_NP_FZ100",
        camera_rail="FX3_7V2_NP_FZ100",
        pack_voltage_mv=7400,
        reported_soc_pct=65,
        stage_b_fx6_overlay_active=True,
        fx6_ui_normalized_pct_mapped=True,
    )
    e_undec_ok = evaluate_np_fz100_battery_handshake(
        pack_type="UNDECODED_3P_NP_FZ100",
        camera_rail="FX3_7V2_NP_FZ100",
        pack_voltage_mv=7450,
        c_pin_connected=True,
        c_pin_auth_valid=False,
        user_confirmed_continue=True,
        stage_b_fx6_overlay_active=True,
        fx6_ui_normalized_pct_mapped=True,
    )
    e_dummy_ok = evaluate_np_fz100_battery_handshake(
        pack_type="REGULATED_DUMMY_CPIN_ABSENT",
        camera_rail="FX3_7V2_NP_FZ100",
        pack_voltage_mv=7800,
        c_pin_connected=False,
        c_pin_auth_valid=False,
        user_confirmed_continue=True,
        stage_b_fx6_overlay_active=True,
        fx6_ui_normalized_pct_mapped=True,
    )
    e_fx6_native = evaluate_np_fz100_battery_handshake(
        pack_type="FX6_BP_U35_14V4_NATIVE",
        camera_rail="FX6_14V4_BP_U",
        pack_voltage_mv=14800,
        reported_soc_pct=75,
        stage_b_fx6_overlay_active=False,
    )
    b_false_14v4 = evaluate_np_fz100_battery_handshake(
        pack_type="OEM_NP_FZ100",
        camera_rail="FX3_7V2_NP_FZ100",
        pack_voltage_mv=7650,
        reported_soc_pct=82,
        stage_b_fx6_overlay_active=True,
        fx6_ui_normalized_pct_mapped=False,
    )
    b_overvolt = evaluate_np_fz100_battery_handshake(
        pack_type="UNREGULATED_DANGEROUS_DUMMY",
        camera_rail="FX3_7V2_NP_FZ100",
        pack_voltage_mv=12000,
        c_pin_connected=False,
        c_pin_auth_valid=False,
        user_confirmed_continue=True,
    )
    b_cancelled = evaluate_np_fz100_battery_handshake(
        pack_type="UNDECODED_3P_NP_FZ100",
        camera_rail="FX3_7V2_NP_FZ100",
        pack_voltage_mv=7400,
        c_pin_connected=True,
        c_pin_auth_valid=False,
        user_confirmed_continue=False,
    )

    for lbl, ev in (
        ("oem_fz100", e_oem),
        ("decoded_3p", e_dec3p),
        ("undecoded_degraded", e_undec_ok),
        ("dummy_degraded", e_dummy_ok),
        ("fx6_bpu35", e_fx6_native),
    ):
        if not ev.valid or ev.false_low_batt_shutdown_triggered or not ev.safe_to_operate:
            errors.append(f"Positive NP-FZ100 handshake check {lbl} failed: {ev.errors}")
    if not e_undec_ok.degraded_power_mode or e_undec_ok.percentage_display_visible or e_undec_ok.fw_update_allowed:
        errors.append("Undecoded 3P pack failed to enter safe degraded no-pct / no-fw-update mode")
    if not e_dummy_ok.degraded_power_mode or e_dummy_ok.c_pin_telemetry_present:
        errors.append("Regulated dummy coupler failed to enter C-pin-absent safe degraded mode")
    for lbl, blk in (
        ("false_14v4", b_false_14v4),
        ("overvolt", b_overvolt),
        ("user_cancel", b_cancelled),
    ):
        if blk.valid:
            errors.append(f"Negative NP-FZ100 guard {lbl} unexpectedly passed")
    if not b_false_14v4.false_low_batt_shutdown_triggered:
        errors.append("Unmapped FX6 14.4V guard failed to flag false_low_batt_shutdown_triggered")

    return NpFz100BatteryHandshakeReport(
        passed=len(errors) == 0,
        fx3_appfw_batt_markers=fx3_appfw_batt_markers,
        fx6_appfw_batt_markers=fx6_appfw_batt_markers,
        fx3_cp_batt_markers=fx3_cp_batt_markers,
        fx6_cp_batt_markers=fx6_cp_batt_markers,
        uxc_batt_labels=uxc_batt_labels,
        eval_oem_np_fz100_stageb_fx6_ui=e_oem,
        eval_decoded_3p_np_fz100_ok=e_dec3p,
        eval_undecoded_3p_confirmed_degraded=e_undec_ok,
        eval_regulated_dummy_cpin_absent_confirmed=e_dummy_ok,
        eval_fx6_bpu35_14v4_native=e_fx6_native,
        blocked_false_fx6_14v4_threshold_on_fx3_7v2=b_false_14v4,
        blocked_unregulated_overvolt_dummy=b_overvolt,
        blocked_undecoded_user_cancelled=b_cancelled,
        errors=tuple(errors),
    )


def evaluate_pillar_d_zero_mutation_phase133_guard(
    *,
    fx3_global_xdb_valid: bool,
    fx6_global_xdb_valid: bool,
    extra_errors: Sequence[str] = (),
) -> ZeroMutationPhase133GuardReport:
    errors = list(extra_errors)
    if not fx3_global_xdb_valid:
        errors.append("FX3 global.xdb (uxa\\x07) failed structural validation")
    if not fx6_global_xdb_valid:
        errors.append("FX6 global.xdb (uxa\\x07) failed structural validation")

    g_vol = evaluate_phase133_write_guard("/tmp/fx3_stageb_xavc_aces_fz100.json")
    g_body = evaluate_phase133_write_guard("/mnt/sd/BODYDATA.DAT")
    g_nf15 = evaluate_phase133_write_guard("/dev/nflasha15")
    g_cn0 = evaluate_phase133_write_guard("/dev/cnflasha0")
    g_bak = evaluate_phase133_write_guard("p2:/setting/Backup.bin")

    if not g_vol.valid:
        errors.append("Volatile RAM staging unexpectedly blocked")
    for lbl, blk in (
        ("BODYDATA.DAT", g_body),
        ("nflasha15", g_nf15),
        ("cnflasha0", g_cn0),
        ("Backup.bin", g_bak),
    ):
        if blk.valid:
            errors.append(f"Persistent eMMC/OTA target {lbl} was not blocked")

    return ZeroMutationPhase133GuardReport(
        passed=len(errors) == 0,
        fx3_global_xdb_valid=fx3_global_xdb_valid,
        fx6_global_xdb_valid=fx6_global_xdb_valid,
        volatile_staging_guard=g_vol,
        blocked_bodydata_dat_guard=g_body,
        blocked_nflasha15_guard=g_nf15,
        blocked_cnflasha0_guard=g_cn0,
        blocked_backup_bin_guard=g_bak,
        emmc_mutation_bytes=0,
        calibration_mutation_bytes=0,
        persistent_emmc_writes_authorized=False,
        errors=tuple(errors),
    )


def build_clean_room_xavc_aces_fz100_fixtures() -> Dict[str, bytes]:
    """Build deterministic clean-room ELF64, CP, `global.xdb`, and `.uxc` fixtures."""
    elf_hdr = b"\x7fELF\x02\x01\x01\x00" + bytes(56)

    def _pack(tokens: Sequence[str]) -> bytes:
        return elf_hdr + b"\x00".join(t.encode("latin1") for t in tokens) + b"\x00"

    return {
        "fx3_appfw": _pack(FX3_APPFW_PHASE133_MARKERS),
        "fx6_appfw": _pack(FX6_APPFW_PHASE133_MARKERS),
        "fx3_libmpr": _pack(FX3_LIBMPR_PHASE133_MARKERS),
        "fx6_libmpr": _pack(FX6_LIBMPR_PHASE133_MARKERS),
        "fx3_cp": b"CPAPP_FX3\x00" + b"\x00".join(t.encode("latin1") for t in CP_SHARED_PHASE133_MARKERS) + b"\x00",
        "fx6_cp": b"CPAPP_FX6\x00" + b"\x00".join(t.encode("latin1") for t in CP_SHARED_PHASE133_MARKERS) + b"\x00",
        "fx3_global_xdb": build_synthetic_global_xdb("fx3_702"),
        "fx6_global_xdb": build_synthetic_global_xdb("fx6_601"),
        "fx3_str_en": build_sparse_uxc_string_pack(
            {k & 0x1FFF: v for k, v in FX3_NS39_PHASE133_LABELS.items()}, namespace_id=39
        ),
        "fx3_str_en_g": build_sparse_uxc_string_pack(
            {k & 0x1FFF: v for k, v in FX3_NS3_PHASE133_LABELS.items()}, namespace_id=3
        ),
        "fx6_str_en_1": build_sparse_uxc_string_pack(
            {k & 0x1FFF: v for k, v in FX6_NS1_PHASE133_LABELS.items()}, namespace_id=1
        ),
        "fx6_str_en_2": build_sparse_uxc_string_pack(
            {k & 0x1FFF: v for k, v in FX6_NS2_PHASE133_LABELS.items()}, namespace_id=2
        ),
    }


def analyze_xavc_hevc_intra_aces_idt_and_fz100(
    *,
    clean_room: bool = False,
    repo_root: Optional[Path] = None,
) -> XavcHevcIntraAcesIdtAndFz100Report:
    """Run the 26th unified firmware-lab auditor in Local Donor (`os.O_RDONLY`) or Clean-Room mode."""
    root = repo_root or DEFAULT_REPO_ROOT
    forced_clean = clean_room or is_forced_clean_room()

    donor_paths: Dict[str, Optional[Path]] = {}
    if not forced_clean:
        donor_paths = {
            "fx3_appfw": resolve_donor_file(FX3_APPFW_RELPATH, repo_root=root),
            "fx6_appfw": resolve_donor_file(FX6_APPFW_RELPATH, repo_root=root),
            "fx3_libmpr": resolve_donor_file(FX3_LIBMPR_RELPATH, repo_root=root),
            "fx6_libmpr": resolve_donor_file(FX6_LIBMPR_RELPATH, repo_root=root),
            "fx3_cp": resolve_donor_file(FX3_CPAPP_RELPATH, repo_root=root),
            "fx6_cp": resolve_donor_file(FX6_CPAPP_RELPATH, repo_root=root),
            "fx3_global_xdb": resolve_donor_file(FX3_GLOBAL_XDB_RELPATH, repo_root=root),
            "fx6_global_xdb": resolve_donor_file(FX6_GLOBAL_XDB_RELPATH, repo_root=root),
            "fx3_str_en": resolve_donor_file(FX3_STR_EN_RELPATH, repo_root=root),
            "fx3_str_en_g": resolve_donor_file(FX3_STR_EN_G_RELPATH, repo_root=root),
            "fx6_str_en_1": resolve_donor_file(FX6_STR_EN_1_RELPATH, repo_root=root),
            "fx6_str_en_2": resolve_donor_file(FX6_STR_EN_2_RELPATH, repo_root=root),
        }

    use_local = (not forced_clean) and all(p is not None and p.is_file() for p in donor_paths.values())
    mode = "LOCAL_DONOR_VERIFIED" if use_local else "CLEAN_ROOM_SYNTHETIC"

    fx3_app_groups = {
        "codec": FX3_APPFW_PHASE133_MARKERS[:4],
        "gamut": FX3_APPFW_PHASE133_MARKERS[4:7],
        "batt": FX3_APPFW_PHASE133_MARKERS[7:],
    }
    fx6_app_groups = {
        "gamut": FX6_APPFW_PHASE133_MARKERS[:3],
        "batt": FX6_APPFW_PHASE133_MARKERS[3:],
    }
    fx3_mpr_groups = {"codec": FX3_LIBMPR_PHASE133_MARKERS}
    fx6_mpr_groups = {"codec": FX6_LIBMPR_PHASE133_MARKERS}
    cp_groups = {"batt": CP_SHARED_PHASE133_MARKERS}

    if use_local:
        sz_fx3_app, fx3_app_res = _scan_donor_rdonly_markers(donor_paths["fx3_appfw"], fx3_app_groups, is_elf=True)  # type: ignore[arg-type]
        sz_fx6_app, fx6_app_res = _scan_donor_rdonly_markers(donor_paths["fx6_appfw"], fx6_app_groups, is_elf=True)  # type: ignore[arg-type]
        sz_fx3_mpr, fx3_mpr_res = _scan_donor_rdonly_markers(donor_paths["fx3_libmpr"], fx3_mpr_groups, is_elf=True)  # type: ignore[arg-type]
        sz_fx6_mpr, fx6_mpr_res = _scan_donor_rdonly_markers(donor_paths["fx6_libmpr"], fx6_mpr_groups, is_elf=True)  # type: ignore[arg-type]
        sz_fx3_cp, fx3_cp_res = _scan_donor_rdonly_markers(donor_paths["fx3_cp"], cp_groups, is_elf=False)  # type: ignore[arg-type]
        sz_fx6_cp, fx6_cp_res = _scan_donor_rdonly_markers(donor_paths["fx6_cp"], cp_groups, is_elf=False)  # type: ignore[arg-type]
        fx3_xdb_bytes = _read_bytes_rdonly(donor_paths["fx3_global_xdb"])  # type: ignore[arg-type]
        fx6_xdb_bytes = _read_bytes_rdonly(donor_paths["fx6_global_xdb"])  # type: ignore[arg-type]
        fx3_str_en_bytes = _read_bytes_rdonly(donor_paths["fx3_str_en"])  # type: ignore[arg-type]
        fx3_str_en_g_bytes = _read_bytes_rdonly(donor_paths["fx3_str_en_g"])  # type: ignore[arg-type]
        fx6_str_en_1_bytes = _read_bytes_rdonly(donor_paths["fx6_str_en_1"])  # type: ignore[arg-type]
        fx6_str_en_2_bytes = _read_bytes_rdonly(donor_paths["fx6_str_en_2"])  # type: ignore[arg-type]
    else:
        fx = build_clean_room_xavc_aces_fz100_fixtures()
        sz_fx3_app, fx3_app_res = _scan_bytes_marker_groups(fx["fx3_appfw"], fx3_app_groups)
        sz_fx6_app, fx6_app_res = _scan_bytes_marker_groups(fx["fx6_appfw"], fx6_app_groups)
        sz_fx3_mpr, fx3_mpr_res = _scan_bytes_marker_groups(fx["fx3_libmpr"], fx3_mpr_groups)
        sz_fx6_mpr, fx6_mpr_res = _scan_bytes_marker_groups(fx["fx6_libmpr"], fx6_mpr_groups)
        sz_fx3_cp, fx3_cp_res = _scan_bytes_marker_groups(fx["fx3_cp"], cp_groups)
        sz_fx6_cp, fx6_cp_res = _scan_bytes_marker_groups(fx["fx6_cp"], cp_groups)
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
        "fx3_cp": sz_fx3_cp,
        "fx6_cp": sz_fx6_cp,
        "fx3_global_xdb": len(fx3_xdb_bytes),
        "fx6_global_xdb": len(fx6_xdb_bytes),
        "fx3_str_en": len(fx3_str_en_bytes),
        "fx3_str_en_g": len(fx3_str_en_g_bytes),
        "fx6_str_en_1": len(fx6_str_en_1_bytes),
        "fx6_str_en_2": len(fx6_str_en_2_bytes),
    }

    pa_extra: List[str] = []
    pb_extra: List[str] = []
    pc_extra: List[str] = []
    pd_extra: List[str] = []

    for label, actual, expected, bucket in (
        ("FX3 appFw Codec", fx3_app_res["codec"], fx3_app_groups["codec"], pa_extra),
        ("FX3 libmpr Codec", fx3_mpr_res["codec"], fx3_mpr_groups["codec"], pa_extra),
        ("FX6 libmpr Codec", fx6_mpr_res["codec"], fx6_mpr_groups["codec"], pa_extra),
        ("FX3 appFw Gamut", fx3_app_res["gamut"], fx3_app_groups["gamut"], pb_extra),
        ("FX6 appFw Gamut", fx6_app_res["gamut"], fx6_app_groups["gamut"], pb_extra),
        ("FX3 appFw Battery", fx3_app_res["batt"], fx3_app_groups["batt"], pc_extra),
        ("FX6 appFw Battery", fx6_app_res["batt"], fx6_app_groups["batt"], pc_extra),
        ("FX3 cpapp Battery", fx3_cp_res["batt"], cp_groups["batt"], pc_extra),
        ("FX6 cpapp Battery", fx6_cp_res["batt"], cp_groups["batt"], pc_extra),
    ):
        if len(actual) != len(expected):
            bucket.append(f"Missing {label} markers ({len(actual)}/{len(expected)})")

    fx3_ux_en, u_err_1 = _extract_uxc_labels(fx3_str_en_bytes, FX3_NS39_PHASE133_LABELS)
    fx3_ux_g, u_err_2 = _extract_uxc_labels(fx3_str_en_g_bytes, FX3_NS3_PHASE133_LABELS)
    fx6_ux_1, u_err_3 = _extract_uxc_labels(fx6_str_en_1_bytes, FX6_NS1_PHASE133_LABELS)
    fx6_ux_2, u_err_4 = _extract_uxc_labels(fx6_str_en_2_bytes, FX6_NS2_PHASE133_LABELS)
    pa_extra.extend(u_err_1[:1] if u_err_1 else ())
    pa_extra.extend(u_err_2)
    pb_extra.extend(u_err_3)
    pc_extra.extend(u_err_1)
    pc_extra.extend(u_err_4)

    uxc_codec_labels = {
        "fx3_vpg200_caution": fx3_ux_en.get("0x0000e02e", ""),
        "fx3_xavc_s_i_dci4k": fx3_ux_g.get("0x000060ce", ""),
        "fx6_xavc_s_i": fx6_ux_1.get("0x00002b03", ""),
    }
    uxc_gamut_labels = {
        "fx6_slog3": fx6_ux_1.get("0x0000219f", ""),
        "fx6_sgamut_to_sgamut3_cine": fx6_ux_2.get("0x000044fe", ""),
    }
    uxc_batt_labels = {
        "fx3_battery_auth_caution": fx3_ux_en.get("0x0000e24e", ""),
        "fx3_battery_exhausted": fx3_ux_en.get("0x0000e704", ""),
        "fx3_update_low_batt": fx3_ux_g.get("0x00006013", ""),
        "fx6_battery_error": fx6_ux_1.get("0x00002693", ""),
        "fx6_voltage_low": fx6_ux_2.get("0x00004005", ""),
        "fx6_dc_voltage_alarm": fx6_ux_2.get("0x00004269", ""),
        "fx6_battery_remain": fx6_ux_2.get("0x00004550", ""),
    }

    pa = evaluate_pillar_a_bionz_xr_codec_matrix(
        fx3_appfw_codec_markers=fx3_app_res["codec"],
        fx3_libmpr_codec_markers=fx3_mpr_res["codec"],
        fx6_libmpr_codec_markers=fx6_mpr_res["codec"],
        uxc_codec_labels=uxc_codec_labels,
        extra_errors=pa_extra,
    )
    pb = evaluate_pillar_b_aces_slog3_idt_matrix(
        fx3_appfw_gamut_markers=fx3_app_res["gamut"],
        fx6_appfw_gamut_markers=fx6_app_res["gamut"],
        uxc_gamut_labels=uxc_gamut_labels,
        extra_errors=pb_extra,
    )
    pc = evaluate_pillar_c_np_fz100_battery_handshake(
        fx3_appfw_batt_markers=fx3_app_res["batt"],
        fx6_appfw_batt_markers=fx6_app_res["batt"],
        fx3_cp_batt_markers=fx3_cp_res["batt"],
        fx6_cp_batt_markers=fx6_cp_res["batt"],
        uxc_batt_labels=uxc_batt_labels,
        extra_errors=pc_extra,
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

    pd = evaluate_pillar_d_zero_mutation_phase133_guard(
        fx3_global_xdb_valid=fx3_xdb_ok,
        fx6_global_xdb_valid=fx6_xdb_ok,
        extra_errors=pd_extra,
    )

    all_errors = pa.errors + pb.errors + pc.errors + pd.errors
    passed = bool(pa.passed and pb.passed and pc.passed and pd.passed and not all_errors)

    digest_src = {
        "schema_version": PHASE_133_SCHEMA,
        "phase_version": PHASE_133_VERSION,
        "mode": mode,
        "all_checks_passed": passed,
        "donor_file_sizes": sizes,
        "pillar_a_bionz_xr_codec_matrix": asdict(pa),
        "pillar_b_aces_slog3_idt_matrix": asdict(pb),
        "pillar_c_np_fz100_battery_handshake": asdict(pc),
        "pillar_d_zero_mutation_guard": asdict(pd),
        "errors": list(all_errors),
    }
    import json

    report_sha256 = hashlib.sha256(
        json.dumps(digest_src, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    return XavcHevcIntraAcesIdtAndFz100Report(
        schema_version=PHASE_133_SCHEMA,
        phase_version=PHASE_133_VERSION,
        mode=mode,
        all_checks_passed=passed,
        donor_file_sizes=sizes,
        pillar_a_bionz_xr_codec_matrix=pa,
        pillar_b_aces_slog3_idt_matrix=pb,
        pillar_c_np_fz100_battery_handshake=pc,
        pillar_d_zero_mutation_guard=pd,
        report_sha256=report_sha256,
        errors=all_errors,
    )


def xavc_hevc_intra_aces_idt_and_fz100_report_to_dict(
    report: XavcHevcIntraAcesIdtAndFz100Report,
) -> Dict[str, object]:
    return asdict(report)
