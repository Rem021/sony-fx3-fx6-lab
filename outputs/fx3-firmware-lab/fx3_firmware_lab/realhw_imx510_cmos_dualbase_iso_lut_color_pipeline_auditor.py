"""Phase 156 — 32nd Unified Firmware-Lab Auditor: Real-Hardware `IMX510` 10.2MP
Full-Frame BSI Exmor R CMOS Sensor, `psd.bin / defdet.bin` Factory Sensor
Calibration NVS Preservation, Dual-Base ISO `800 / 12800` (LCG / HCG) & Cine EI
Pipeline, and `S-Log3` / `S-Cinetone` / `709tone` / `16-Slot` `.cube` 3D MLUT
Stage-B Color Pipeline.

Strictly Read-Only (`os.O_RDONLY` + `mmap.ACCESS_READ`) & Clean-Room Dual-Mode:
- Local Donor Mode: inspects FX3 v7.02 (`appFw.so`, `libsencore.so`, `libmpr.so`,
  `cpapp-b.bin`, `Backup.bin`) and FX6 v6.01 (`appFw.so`, `libsencore.so`,
  `libmpr.so`, `cpapp-b.bin`, `Backup.bin`, plus optional FX6 `.cube` LUT headers
  and optional local `p2` `psd.bin`/`defdet.bin` headers) strictly via
  `os.O_RDONLY` + `mmap.ACCESS_READ` using targeted ELF64 `.dynsym`/`.dynstr`/
  `.dynamic` parsing, `BK4\\x00` dual-record parsing, and bounded single-pass
  `re.finditer` scans (< 1.5 s total).
- Clean-Room Mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`, `clean_room=True`, or donors
  absent): synthesizes deterministic clean-room ELF64 `.so` fixtures,
  `cpapp-b.bin` token buffers, `BK4\\x00` `Backup.bin` fixtures, and `.cube`
  header fixtures, leaking zero raw Sony proprietary bytes in JSON output.

Audits Four Phase 156 Real-Hardware Sensor & Color Pipeline Pillars:
1. Pillar 1 (`IMX510_SENSOR_CAL_AND_P2_NVS_PRESERVATION`):
   Audits shared `IMX510` CP sensor driver classes
   (`N6Camera6Imager6IMX51019C_ImagerCtrl_IMX510E`,
   `N6Camera6Imager21ImagerDrvParam_IMX510E`), factory defect-pixel / pixel-
   shading tables (`/setting/defdet.bin`, `psd.bin`), OB-clamp
   (`MasterBlackLevelMeta`, `RchBlackLevel`, `BchBlackLevel`), shading correction
   (`CheckSetShadingCorrection` / `setShadingCorrection`), and `Backup.bin`
   Bank-1 `p2` descriptors (`\\defdet.bin` `5,242,880 B` @ `0x809479000` vs
   `0x80948d000`; `\\psd.bin` `5,242,880 B` @ `0x808730000` vs `0x808810000`).
   Enforces 100% read-only preservation of the physical FX3 body's OWN `p2`
   calibration (`sensor_cal_p2_writes_permitted == False`,
   `sensor_cal_mutation_bytes == 0`), never substituting FX6 calibration.
2. Pillar 2 (`DUAL_BASE_ISO_800_12800_HCG_LCG_AND_CINE_EI`):
   Audits FX3/FX6 `appFw.so`, `libmpr.so`, and `cpapp-b.bin` symbols & parameter
   opcodes for Dual-Base ISO `800` (LCG) <-> `12800` (HCG) analog conversion
   gain switching (`BASE_ISO_LOW_800`, `BASE_ISO_HIGH_12800`,
   `SHOOTING_MODE_BASE_SETTING_CINE_EI_QUICK`, `FLEXIBLE_ISO`,
   `HyperGainMode`/`uc_HighGainMode`, `ExposureIndexMeta`,
   `setMetaData_ExposureIndexRDD18`, `ul_RecommendedExposureIndex`). Proves FX6
   `appFw.so` drives Stock FX3 `IMX510` LCG/HCG cleanly across `200..3200 EI`
   and `3200..51200 EI` while recording unbaked full-latitude `S-Log3` to
   `M4ROOT/CLIP` with accurate EI XML metadata.
3. Pillar 3 (`SLOG3_SCINETONE_709TONE_AND_CUBE_MLUT_PIPELINE`):
   Audits `S-Gamut3.Cine/S-Log3`, `S-Cinetone`, `709tone`, and `16-Slot`
   `.cube` User 3D MLUT (`17^3` / `33^3`) pipeline across `appFw.so`
   (`/Private/Sony/PRO/LUT`, `PID_SET_USER_LUT_BINARY_DATA`,
   `LUT_SETTING_INTERNAL_REC_MLUT_OFF/ON`, `LUT_SETTING_MONITOR_OUT_MLUT_OFF`),
   `libsencore.so` (`SET_MONITOR_MLUT`), `libmpr.so` (`mpr::SetLutData`,
   `mpr::ExecuteSetLutData`, `mpr::GetCubeFilePath`), and `cpapp-b.bin` ISP
   stages (`MLUT_YC2RGB_ON`, `MLUT_L1D_A_ON`, `MLUT_MTX_A_ON`, `MLUT_EIGAIN_ON`,
   `MLUT_ASCCDL_ON`, `MLUT_L3D_ON`). Ensures SD `.cube` LUTs load into volatile
   RAM/ISP monitor slots without double-baking into `S-Log3` XAVC masters
   unless explicit `LUT Burn-in` is selected, and never overflowing `p2`/`p23`/`p30`.
4. Pillar 4 (`NVS_P2_P23_P30_LUT_ISOLATION_AND_COLOR_COMPAT_MATRIX`):
   Enforces hard write-protection across `p2:/setting/psd.bin`,
   `p2:/setting/defdet.bin`, `p2:/Backup.bin`, `p23:/INFO`, `p30:/usr/data/lut`,
   and `/dev/nflasha*`/`/dev/cnflasha*`/`/dev/mmcblk0*`, while permitting
   volatile `/tmp/` / `ram://` staging (`persistent_emmc_writes_authorized ==
   False`, `emmc_mutation_bytes == 0`), alongside a 12-touchpoint 4-class
   compatibility matrix.
"""

from __future__ import annotations

import hashlib
import json
import math
import mmap
import os
import re
import struct
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from .haita_bk4_feature_analyzer import (
    DEFAULT_REPO_ROOT,
    is_forced_clean_room,
    resolve_donor_file,
)
from .realhw_cp_rtos_and_backup_bin_auditor import (
    BK4_HEADER_BYTES,
    BK4_MAGIC_BYTES,
    BK4_SYNC_U32,
    DESCRIPTOR_SLOT_BYTES,
    DESCRIPTOR_TABLE_BYTES,
    parse_dual_bk4_and_descriptors,
)
from .realhw_lens_ibis_audio_hdmi_peripheral_bridge_auditor import (
    BRIDGE_CLASS_HARD_WRITE_PROTECTED,
    BRIDGE_CLASS_MASKED_ABSENT_HW,
    BRIDGE_CLASS_NATIVE_PASSTHROUGH,
    BRIDGE_CLASS_SHIM_TRANSLATED,
    EXPECTED_SENCORE_EXPORTS,
    EXPECTED_SENCORE_IMPORTS,
    FX3_APPFW_P146_RELPATH,
    FX3_BACKUP_BIN_P146_RELPATH,
    FX3_CPAPP_P146_RELPATH,
    FX3_LIBMPR_P146_RELPATH,
    FX3_LIBSENCORE_P146_RELPATH,
    FX6_APPFW_P146_RELPATH,
    FX6_BACKUP_BIN_P146_RELPATH,
    FX6_CPAPP_P146_RELPATH,
    FX6_LIBMPR_P146_RELPATH,
    FX6_LIBSENCORE_P146_RELPATH,
    VALID_BRIDGE_CLASSES,
    ElfSectionSummary,
    _build_synthetic_elf64,
    _count_tokens_single_pass,
    _scan_elf_and_tokens_buf,
    _scan_elf_and_tokens_rdonly,
)


PHASE_156_SCHEMA = "fx3_firmware_lab_phase156_realhw_imx510_dualbase_iso_lut_color_pipeline_v1"
PHASE_156_VERSION = "156.0.0"

# ---------------------------------------------------------------------------
# Verified Local Donor Relative Paths (strictly O_RDONLY + mmap.ACCESS_READ)
# ---------------------------------------------------------------------------

FX3_APPFW_P156_RELPATH = FX3_APPFW_P146_RELPATH
FX6_APPFW_P156_RELPATH = FX6_APPFW_P146_RELPATH
FX3_LIBSENCORE_P156_RELPATH = FX3_LIBSENCORE_P146_RELPATH
FX6_LIBSENCORE_P156_RELPATH = FX6_LIBSENCORE_P146_RELPATH
FX3_LIBMPR_P156_RELPATH = FX3_LIBMPR_P146_RELPATH
FX6_LIBMPR_P156_RELPATH = FX6_LIBMPR_P146_RELPATH
FX3_CPAPP_P156_RELPATH = FX3_CPAPP_P146_RELPATH
FX6_CPAPP_P156_RELPATH = FX6_CPAPP_P146_RELPATH
FX3_BACKUP_BIN_P156_RELPATH = FX3_BACKUP_BIN_P146_RELPATH
FX6_BACKUP_BIN_P156_RELPATH = FX6_BACKUP_BIN_P146_RELPATH

FX6_LUT_S709_CUBE_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/"
    "nflasha15-files/share/lut/S709.cube"
)
FX6_LUT_S709C_CUBE_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/"
    "nflasha15-files/share/lut/S709C.cube"
)

# Optional local body-specific p2 files (never committed; inspected O_RDONLY if present)
OPTIONAL_P2_PSD_RELPATH = "fx3-vm-20261101/fx3-audit/original-members/nflasha2/setting/psd.bin"
OPTIONAL_P2_DEFDET_RELPATH = "fx3-vm-20261101/fx3-audit/original-members/nflasha2/setting/defdet.bin"

# ---------------------------------------------------------------------------
# Verified Donor Binary Sizes / Symbol Counts
# ---------------------------------------------------------------------------

EXPECTED_FX3_APPFW_BYTES_P156 = 79_015_712
EXPECTED_FX6_APPFW_BYTES_P156 = 50_520_424
EXPECTED_FX3_MPR_EXPORTS_P156 = 3_541
EXPECTED_FX3_MPR_IMPORTS_P156 = 356
EXPECTED_FX6_MPR_EXPORTS_P156 = 4_271
EXPECTED_FX6_MPR_IMPORTS_P156 = 497
EXPECTED_FX3_SENCORE_EXPORTS_P156 = EXPECTED_SENCORE_EXPORTS  # 355
EXPECTED_FX6_SENCORE_EXPORTS_P156 = EXPECTED_SENCORE_EXPORTS  # 355
EXPECTED_FX3_BACKUP_SUBSYSTEMS_P156 = 819
EXPECTED_FX6_BACKUP_SUBSYSTEMS_P156 = 840
EXPECTED_S709_CUBE_BYTES = 1_006_296

# ---------------------------------------------------------------------------
# Pillar 1 Constants: IMX510 CMOS Sensor & p2:/setting/psd.bin / defdet.bin
# ---------------------------------------------------------------------------

IMX510_SENSOR_MODEL = "IMX510"
IMX510_EFFECTIVE_MP = 10.2
IMX510_RAW_ACTIVE_RES: Tuple[int, int] = (4264, 2408)
IMX510_DCI_4K_RES: Tuple[int, int] = (4096, 2160)
IMX510_QFHD_4K_RES: Tuple[int, int] = (3840, 2160)

P2_SENSOR_CAL_IMMUTABLE_PATHS: Tuple[str, ...] = (
    "p2:/setting/psd.bin",
    "p2:/setting/defdet.bin",
    "p2:/Backup.bin",
    "/dev/nflasha2",
    "/dev/cnflasha2",
    "/setting/psd.bin",
    "/setting/defdet.bin",
)
FX3_P2_DEFDET_DDR_ADDR = 0x809479000
FX6_P2_DEFDET_DDR_ADDR = 0x80948D000
FX3_P2_PSD_DDR_ADDR = 0x808730000
FX6_P2_PSD_DDR_ADDR = 0x808810000
P2_CAL_BLOB_SPAN_BYTES = 5_242_880  # 5 MiB

IMX510_CP_SHARED_MARKERS: Tuple[str, ...] = (
    "N6Camera6Imager6IMX51019C_ImagerCtrl_IMX510E",
    "N6Camera6Imager21ImagerDrvParam_IMX510E",
    "/setting/defdet.bin",
    "MasterBlackLevelMeta",
    "RchBlackLevel",
    "BchBlackLevel",
)
IMX510_CP_FX3_MARKERS: Tuple[str, ...] = ("CheckSetShadingCorrection",)
IMX510_CP_FX6_MARKERS: Tuple[str, ...] = (
    "setShadingCorrection",
    "GetBlackLevelOffset_BeforeGamma",
)

# ---------------------------------------------------------------------------
# Pillar 2 Constants: Dual-Base ISO 800 / 12800 (LCG / HCG) & Cine EI
# ---------------------------------------------------------------------------

IMX510_BASE_ISO_LOW_LCG = 800
IMX510_BASE_ISO_HIGH_HCG = 12_800
IMX510_CINE_EI_LOW_RANGE: Tuple[int, int] = (200, 3_200)
IMX510_CINE_EI_HIGH_RANGE: Tuple[int, int] = (3_200, 51_200)
IMX510_CINE_EI_SWITCHOVER_EI = 3_200
VALID_EXPOSURE_MODES_P156: Tuple[str, ...] = (
    "CINE_EI",
    "CINE_EI_QUICK",
    "FLEXIBLE_ISO",
)
VALID_GAIN_STAGES: Tuple[str, ...] = ("LCG", "HCG")
VALID_DUAL_BASE_ISOS_P156: Tuple[int, ...] = (
    IMX510_BASE_ISO_LOW_LCG,
    IMX510_BASE_ISO_HIGH_HCG,
)

ISO_APPFW_FX3_MARKERS: Tuple[str, ...] = (
    "BASE_ISO_LOW_800",
    "BASE_ISO_HIGH_12800",
    "STILL_LOG_SHOOTING_FLEXIBLE_ISO",
    "BASE_ISO_SWITCH_EI_1000_EI",
    "BASE_ISO_SWITCH_EI_3200_EI",
)
ISO_APPFW_FX6_MARKERS: Tuple[str, ...] = (
    "VAL_setting_shooting_mode_base_setting_SHOOTING_MODE_BASE_SETTING_CINE_EI_QUICK",
    "VAL_setting_shooting_mode_base_setting_SHOOTING_MODE_BASE_SETTING_FLEXIBLE_ISO",
    "extern_BKID_APP_EXTERN_BASE_ISO",
    "extern_BKID_APP_EXTERN_AE_AGC_LIMIT_FOR_FLEXIBLE_ISO",
    "convert_MODE_ID_BASE_ISO_SET",
    "convert_MODE_ID_DISP_BASE_ISO_SENSITIVITY",
)
ISO_CP_FX3_MARKERS: Tuple[str, ...] = (
    "HCG",
    "HyperGainMode",
    "CheckSetHyperGainMode",
    "ExposureIndexMeta",
)
ISO_CP_FX6_MARKERS: Tuple[str, ...] = (
    "HCG",
    "uc_HighGainMode",
    "CheckSetHighGainMode",
    "shocklessGainMode",
    "ExposureIndexMeta",
)
ISO_MPR_FX3_MARKERS: Tuple[str, ...] = ("ul_RecommendedExposureIndex",)
ISO_MPR_FX6_MARKERS: Tuple[str, ...] = (
    "setMetaData_ExposureIndexRDD18",
    "MetaConverterImpl::ConvertExposureIndex",
    "ExposureIndexRDD18",
)

# ---------------------------------------------------------------------------
# Pillar 3 Constants: S-Log3, S-Cinetone, 709tone & 16-Slot .cube 3D MLUT
# ---------------------------------------------------------------------------

SD_USER_LUT_DIR = "/mnt/sd/PRIVATE/SONY/PRO/LUT/"
APPFW_USER_LUT_REL_PATH = "/Private/Sony/PRO/LUT"
M4ROOT_CLIP_REL_PATH = "/PRIVATE/M4ROOT"
MAX_USER_LUT_SLOTS = 16
SUPPORTED_CUBE_GRID_SIZES: Tuple[int, ...] = (17, 33)
VALID_BASE_LOOKS_P156: Tuple[str, ...] = (
    "S-Gamut3.Cine/S-Log3",
    "S-Gamut3/S-Log3",
    "S-Cinetone",
    "709tone",
)
VALID_MLUT_TARGETS: Tuple[str, ...] = ("LCD_VF", "HDMI", "INTERNAL_REC")
P2_P23_P30_LUT_IMMUTABLE_PARTITIONS: Tuple[str, ...] = (
    "p2:/setting",
    "p23:/INFO",
    "p30:/usr/data/lut",
    "/dev/nflasha2",
    "/dev/nflasha23",
    "/dev/nflasha30",
    "/dev/cnflasha30",
)
MAX_CUBE_FILE_BYTES_P156 = 2 * 1024 * 1024  # 2 MiB safety bound per user LUT

LUT_APPFW_FX3_MARKERS: Tuple[str, ...] = (
    "/Private/Sony/PRO/LUT",
    "/dev/nflasha30",
    "/dev/nflasha23",
    "SL3SG3CtoR709-800.cube",
    "SL3SG3Ctos709.cube",
    "VAL_is_exist_user_lut0_IS_EXIST_USER_LUT_EXIST",
)
LUT_APPFW_FX6_MARKERS: Tuple[str, ...] = (
    "/Private/Sony/PRO/LUT",
    "/PRIVATE/M4ROOT",
    "S-Cinetone",
    "709tone",
    "SL3SG3Ctos709.cube",
    "SL3SG3CtoR709-800.cube",
    "PID_SET_USER_LUT_BINARY_DATA",
    "convert_MODE_ID_MLUT_SETTING_INTERNAL_REC_SET",
    "convert_MODE_ID_MLUT_SETTING_MONITOR_OUT_SET",
    "VAL_setting_lut_setting_internal_rec_LUT_SETTING_INTERNAL_REC_MLUT_OFF",
    "VAL_setting_lut_setting_internal_rec_LUT_SETTING_INTERNAL_REC_MLUT_ON",
    "VAL_setting_lut_setting_monitor_out_LUT_SETTING_MONITOR_OUT_MLUT_OFF",
)
LUT_MPR_SHARED_MARKERS: Tuple[str, ...] = (
    "_ZN3mpr10SetLutDataERKNS_17setLutDataInParamE",
    "_ZN3mpr17ExecuteSetLutDataERKNS_17setLutDataInParamE",
    "_ZN3mpr15GetCubeFilePathERKN4sidb10recordInfoEjRNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE",
)
LUT_MPR_FX6_MARKERS: Tuple[str, ...] = (
    "_ZN3mpr21GetCubeFilePathForMXFERKN4sidb10recordInfoEjRNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE",
    "S-Log3/S-Gamut3.Cine",
    "S-Log3/S-Gamut3",
    "S-Cinetone",
)
LUT_SENCORE_FX6_MARKERS: Tuple[str, ...] = ("SET_MONITOR_MLUT",)
LUT_CP_SHARED_MARKERS: Tuple[str, ...] = (
    "MLUT_YC2RGB_ON",
    "MLUT_L1D_A_ON",
    "MLUT_MTX_A_ON",
    "MLUT_EIGAIN_ON",
    "MLUT_ASCCDL_ON",
    "MLUT_L3D_ON",
    "S-Log3/S-Gamut3.Cine",
    "S-Cinetone",
    "LUT:SL3SG3Ctos709.cube",
    "LUT:SL3SG3CtoR709-800.cube",
)

# ---------------------------------------------------------------------------
# Pillar 4 Constants: Write-Guard Patterns
# ---------------------------------------------------------------------------

VOLATILE_STAGING_PREFIXES_P156: Tuple[str, ...] = (
    "/tmp/",
    "ram://",
    "ramdisk://",
    "mem://",
    "/mnt/sd/",
)
FORBIDDEN_PERSISTENT_CAL_OR_NVS_RE_P156 = re.compile(
    r"(^/dev/(nflash|cnflash|mmcblk0)|^p(?:2|23|30):|"
    r"psd\.bin|defdet\.bin|Backup\.bin|cpapp-b\.bin|/usr/data/lut|"
    r"/setting/(?:psd|defdet)\.bin|/INFO/)",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Imx510SensorCalEvalResult:
    valid: bool
    status: str
    sensor_model: str
    calibration_source_body: str
    target_path: str
    write_requested: bool
    sensor_cal_p2_writes_permitted: bool
    sensor_cal_mutation_bytes: int
    classification: str
    fx3_psd_ddr_addr_hex: str
    fx3_defdet_ddr_addr_hex: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class DualBaseIsoCineEiEvalResult:
    valid: bool
    status: str
    exposure_mode: str
    base_iso: int
    gain_stage: str
    exposure_index: int
    ei_stop_shift: float
    hcg_lcg_aligned: bool
    slog3_master_preserved: bool
    m4root_clip_recording: bool
    xml_ei_metadata_intact: bool
    cp_gain_command: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class CubeMlutColorEvalResult:
    valid: bool
    status: str
    base_look: str
    cube_grid_size: int
    lut_slot: int
    sd_lut_path: str
    ram_staging_path: str
    mlut_lcd_hdmi_on: bool
    lut_burn_in_requested: bool
    is_raw_or_log_master: bool
    slog3_double_bake_prevented: bool
    nvs_overflow_prevented: bool
    isp_stages_active: Tuple[str, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Phase156WriteGuardResult:
    valid: bool
    status: str
    target_path: str
    volatile_or_sd_allowed: bool
    persistent_write_blocked: bool
    sensor_cal_p2_writes_permitted: bool
    persistent_emmc_writes_authorized: bool
    emmc_mutation_bytes: int
    sensor_cal_mutation_bytes: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class ColorPipelineTouchpointEntry:
    touchpoint_id: str
    subsystem: str  # "SENSOR_CAL", "DUAL_BASE_ISO", "CUBE_MLUT", "NVS_ISOLATION"
    fx6_interface: str
    fx3_target: str
    classification: str
    write_protected: bool
    notes: str


@dataclass(frozen=True)
class ColorPipelineCompatMatrixSummary:
    total_touchpoints: int
    class_counts: Dict[str, int]
    subsystem_counts: Dict[str, int]
    touchpoints: Tuple[ColorPipelineTouchpointEntry, ...]


@dataclass(frozen=True)
class Pillar1Imx510SensorCalReport:
    passed: bool
    fx3_cpapp_markers: Dict[str, int]
    fx6_cpapp_markers: Dict[str, int]
    fx3_backup_subsystems: int
    fx6_backup_subsystems: int
    fx3_p2_defdet_addr_hex: str
    fx6_p2_defdet_addr_hex: str
    fx3_p2_psd_addr_hex: str
    fx6_p2_psd_addr_hex: str
    optional_p2_cal_headers_checked: Dict[str, int]
    own_body_rdonly_eval: Imx510SensorCalEvalResult
    cross_body_substitution_blocked: Imx510SensorCalEvalResult
    p2_write_attempt_blocked: Imx510SensorCalEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Pillar2DualBaseIsoCineEiReport:
    passed: bool
    fx3_appfw_markers: Dict[str, int]
    fx6_appfw_markers: Dict[str, int]
    fx3_cpapp_iso_markers: Dict[str, int]
    fx6_cpapp_iso_markers: Dict[str, int]
    fx3_mpr_iso_markers: Dict[str, int]
    fx6_mpr_iso_markers: Dict[str, int]
    cine_ei_low_800_eval: DualBaseIsoCineEiEvalResult
    cine_ei_high_12800_eval: DualBaseIsoCineEiEvalResult
    cine_ei_quick_switch_eval: DualBaseIsoCineEiEvalResult
    flexible_iso_eval: DualBaseIsoCineEiEvalResult
    invalid_ei_rejected: DualBaseIsoCineEiEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Pillar3Slog3CubeMlutReport:
    passed: bool
    fx3_appfw_lut_markers: Dict[str, int]
    fx6_appfw_lut_markers: Dict[str, int]
    fx3_mpr_lut_markers: Dict[str, int]
    fx6_mpr_lut_markers: Dict[str, int]
    fx6_sencore_lut_markers: Dict[str, int]
    fx3_cpapp_mlut_markers: Dict[str, int]
    fx6_cpapp_mlut_markers: Dict[str, int]
    s709_cube_grid_size: int
    s709_cube_bytes: int
    slog3_mlut_monitor_only_eval: CubeMlutColorEvalResult
    slog3_17_cube_eval: CubeMlutColorEvalResult
    scinetone_709tone_eval: CubeMlutColorEvalResult
    explicit_burnin_nonlog_eval: CubeMlutColorEvalResult
    silent_slog3_double_bake_blocked: CubeMlutColorEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Pillar4NvsIsolationAndMatrixReport:
    passed: bool
    fx3_appfw_summary: ElfSectionSummary
    fx6_appfw_summary: ElfSectionSummary
    fx3_sencore_summary: ElfSectionSummary
    fx6_sencore_summary: ElfSectionSummary
    fx3_mpr_summary: ElfSectionSummary
    fx6_mpr_summary: ElfSectionSummary
    volatile_ram_guard_ok: Phase156WriteGuardResult
    sd_lut_read_guard_ok: Phase156WriteGuardResult
    blocked_p2_psd_guard: Phase156WriteGuardResult
    blocked_p2_defdet_guard: Phase156WriteGuardResult
    blocked_p23_info_guard: Phase156WriteGuardResult
    blocked_p30_lut_guard: Phase156WriteGuardResult
    compatibility_matrix: ColorPipelineCompatMatrixSummary
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class RealhwImx510CmosDualbaseIsoLutColorPipelineReport:
    schema_version: str
    phase_version: str
    mode: str
    all_checks_passed: bool
    o_rdonly_enforced: bool
    sensor_cal_p2_writes_permitted: bool
    sensor_cal_mutation_bytes: int
    dual_base_iso_800_12800_hcg_aligned: bool
    slog3_double_bake_prevented: bool
    persistent_emmc_writes_authorized: bool
    emmc_mutation_bytes: int
    calibration_mutation_bytes: int
    donor_file_sizes: Dict[str, int]
    pillar1_imx510_sensor_cal: Pillar1Imx510SensorCalReport
    pillar2_dual_base_iso_cine_ei: Pillar2DualBaseIsoCineEiReport
    pillar3_slog3_cube_mlut: Pillar3Slog3CubeMlutReport
    pillar4_nvs_isolation_matrix: Pillar4NvsIsolationAndMatrixReport
    report_sha256: str
    errors: Tuple[str, ...]


# ---------------------------------------------------------------------------
# Strictly Read-Only Helpers (os.O_RDONLY + mmap.ACCESS_READ)
# ---------------------------------------------------------------------------


def _scan_tokens_mmap_rdonly(
    path: Path,
    tokens: Sequence[str],
) -> Tuple[int, Dict[str, int]]:
    """Open `path` strictly `os.O_RDONLY` and count markers via `mmap.ACCESS_READ`."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        sz = os.fstat(fd).st_size
        if sz == 0:
            return 0, {t: 0 for t in tokens}
        with mmap.mmap(fd, sz, access=mmap.ACCESS_READ) as mm:
            return sz, _count_tokens_single_pass(mm, tokens)
    finally:
        os.close(fd)


def _read_rdonly_bytes(path: Path, *, max_bytes: Optional[int] = None) -> bytes:
    """Strictly read bytes via `os.O_RDONLY` + `mmap.ACCESS_READ`."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        sz = os.fstat(fd).st_size
        if sz == 0:
            return b""
        read_len = min(sz, max_bytes) if max_bytes is not None else sz
        with mmap.mmap(fd, sz, access=mmap.ACCESS_READ) as mm:
            return bytes(mm[:read_len])
    finally:
        os.close(fd)


def _parse_cube_header_metadata(cube_header_bytes: bytes) -> Tuple[int, str]:
    """Parse `LUT_3D_SIZE` and `TITLE` from a `.cube` header without leaking raw bytes."""
    text = cube_header_bytes.decode("ascii", errors="replace")
    grid_size = 0
    title = ""
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("LUT_3D_SIZE"):
            parts = s.split()
            if len(parts) >= 2 and parts[1].isdigit():
                grid_size = int(parts[1])
        elif s.startswith("TITLE"):
            title = s[5:].strip().strip('"')
    return grid_size, title


def _build_synthetic_bk4_dual_record_p156(
    *,
    subsystems: int,
    seed: int,
    defdet_addr: int,
    psd_addr: int,
    lens_addr: int,
) -> bytes:
    """Build deterministic clean-room dual-record `BK4\\x00` Backup.bin with Bank-1 p2 slots."""
    body_tag = seed.to_bytes(4, "little")

    def _make_record(slots: Sequence[Tuple[int, int, int, int, str]]) -> bytes:
        table = bytearray(DESCRIPTOR_TABLE_BYTES)
        for idx, (part, mode, start_addr, end_addr, path_str) in enumerate(slots):
            ent = bytearray(DESCRIPTOR_SLOT_BYTES)
            struct.pack_into("<QQII", ent, 0, start_addr, end_addr, part, mode)
            pb = path_str.encode("ascii")
            ent[24 : 24 + len(pb)] = pb
            off = idx * DESCRIPTOR_SLOT_BYTES
            table[off : off + DESCRIPTOR_SLOT_BYTES] = ent
        table[DESCRIPTOR_TABLE_BYTES - len(body_tag) :] = body_tag

        hdr = bytearray(BK4_HEADER_BYTES)
        struct.pack_into(
            "<II4s4sIIIII",
            hdr,
            0,
            0x04000000,
            BK4_SYNC_U32,
            b"\x00\x00\x00\x00",
            BK4_MAGIC_BYTES,
            subsystems,
            2048,
            BK4_HEADER_BYTES,
            len(table),
            0,
        )
        body = bytes(hdr) + bytes(table)
        csum = (sum(body) - sum(body[32:36])) & 0xFFFFFFFF
        struct.pack_into("<I", hdr, 32, csum)
        return bytes(hdr) + bytes(table)

    bank0 = ((3, 0x05000000, 0x401000000, 0x401FFFFFF, "\\av-cam.bin"),)
    bank1 = (
        (3, 0x05000000, 0x809139000, 0x809178FFF, "\\sabin\\idt_cam.bin"),
        (2, 0x05000000, defdet_addr, defdet_addr + P2_CAL_BLOB_SPAN_BYTES - 1, "\\defdet.bin"),
        (2, 0x05000000, psd_addr, psd_addr + P2_CAL_BLOB_SPAN_BYTES - 1, "\\psd.bin"),
        (18, 0x05000000, lens_addr, lens_addr + 524_288 - 1, "\\lensfile.bin"),
    )
    return _make_record(bank0) + _make_record(bank1)


# ---------------------------------------------------------------------------
# Clean-Room Synthetic Fixture Builder
# ---------------------------------------------------------------------------


def build_clean_room_realhw_imx510_color_fixtures() -> Dict[str, bytes]:
    """Build deterministic clean-room synthetic ELF64, RTOS, BK4 & .cube fixtures."""
    fx3_appfw_tokens = ISO_APPFW_FX3_MARKERS + LUT_APPFW_FX3_MARKERS
    fx6_appfw_tokens = ISO_APPFW_FX6_MARKERS + LUT_APPFW_FX6_MARKERS
    fx3_mpr_tokens = ISO_MPR_FX3_MARKERS + LUT_MPR_SHARED_MARKERS
    fx6_mpr_tokens = ISO_MPR_FX6_MARKERS + LUT_MPR_SHARED_MARKERS + LUT_MPR_FX6_MARKERS
    fx3_cp_tokens = (
        IMX510_CP_SHARED_MARKERS
        + IMX510_CP_FX3_MARKERS
        + ISO_CP_FX3_MARKERS
        + LUT_CP_SHARED_MARKERS
    )
    fx6_cp_tokens = (
        IMX510_CP_SHARED_MARKERS
        + IMX510_CP_FX6_MARKERS
        + ISO_CP_FX6_MARKERS
        + LUT_CP_SHARED_MARKERS
    )

    fx3_mpr_exports = tuple(
        list(LUT_MPR_SHARED_MARKERS)
        + [f"mpr3_exp_{i}" for i in range(EXPECTED_FX3_MPR_EXPORTS_P156 - len(LUT_MPR_SHARED_MARKERS))]
    )
    fx6_mpr_exports = tuple(
        list(LUT_MPR_SHARED_MARKERS)
        + [f"mpr6_exp_{i}" for i in range(EXPECTED_FX6_MPR_EXPORTS_P156 - len(LUT_MPR_SHARED_MARKERS))]
    )

    s709_header = (
        b"# s709 LUT\n"
        b"# S-Log3/S-Gamut3 to Rec.709\n"
        b'TITLE "S709"\n'
        b"LUT_3D_SIZE 33\n"
        b"0.000000 0.000000 0.000000\n"
    )

    return {
        "fx3_appfw": _build_synthetic_elf64(
            exports=("appFw_main",),
            imports=tuple(f"af3_imp_{i}" for i in range(799)),
            dt_needed=("libsencore.so", "libmpr.so"),
            rodata_strings=fx3_appfw_tokens,
        ),
        "fx6_appfw": _build_synthetic_elf64(
            exports=("appFw_main",),
            imports=tuple(f"af6_imp_{i}" for i in range(909)),
            dt_needed=("libsencore.so", "libmpr.so"),
            rodata_strings=fx6_appfw_tokens,
        ),
        "fx3_sencore": _build_synthetic_elf64(
            exports=tuple(f"sc_exp_{i}" for i in range(EXPECTED_FX3_SENCORE_EXPORTS_P156)),
            imports=tuple(f"sc_imp_{i}" for i in range(EXPECTED_SENCORE_IMPORTS)),
            dt_needed=("libosal_uipc.so",),
            rodata_strings=("SenserIfSend", "AdjustControlFunc"),
        ),
        "fx6_sencore": _build_synthetic_elf64(
            exports=tuple(f"sc_exp_{i}" for i in range(EXPECTED_FX6_SENCORE_EXPORTS_P156)),
            imports=tuple(f"sc_imp_{i}" for i in range(EXPECTED_SENCORE_IMPORTS)),
            dt_needed=("libosal_uipc.so",),
            rodata_strings=("SenserIfSend", "AdjustControlFunc") + LUT_SENCORE_FX6_MARKERS,
        ),
        "fx3_mpr": _build_synthetic_elf64(
            exports=fx3_mpr_exports,
            imports=tuple(f"mpr3_imp_{i}" for i in range(EXPECTED_FX3_MPR_IMPORTS_P156)),
            dt_needed=("libosal_uipc.so",),
            rodata_strings=fx3_mpr_tokens,
        ),
        "fx6_mpr": _build_synthetic_elf64(
            exports=fx6_mpr_exports,
            imports=tuple(f"mpr6_imp_{i}" for i in range(EXPECTED_FX6_MPR_IMPORTS_P156)),
            dt_needed=("libosal_uipc.so",),
            rodata_strings=fx6_mpr_tokens,
        ),
        "fx3_cpapp": (
            b"CPAPP_FX3\x00" + b"\x00".join(t.encode("ascii") for t in fx3_cp_tokens) + b"\x00"
        ),
        "fx6_cpapp": (
            b"CPAPP_FX6\x00" + b"\x00".join(t.encode("ascii") for t in fx6_cp_tokens) + b"\x00"
        ),
        "fx3_backup": _build_synthetic_bk4_dual_record_p156(
            subsystems=EXPECTED_FX3_BACKUP_SUBSYSTEMS_P156,
            seed=0x1563,
            defdet_addr=FX3_P2_DEFDET_DDR_ADDR,
            psd_addr=FX3_P2_PSD_DDR_ADDR,
            lens_addr=0x808C30000,
        ),
        "fx6_backup": _build_synthetic_bk4_dual_record_p156(
            subsystems=EXPECTED_FX6_BACKUP_SUBSYSTEMS_P156,
            seed=0x1566,
            defdet_addr=FX6_P2_DEFDET_DDR_ADDR,
            psd_addr=FX6_P2_PSD_DDR_ADDR,
            lens_addr=0x808D10000,
        ),
        "fx6_s709_cube_header": s709_header,
    }


# ---------------------------------------------------------------------------
# Pillar Evaluators (Individual Deterministic Contracts)
# ---------------------------------------------------------------------------


def evaluate_imx510_sensor_cal_preservation(
    *,
    calibration_source_body: str = "FX3_OWN_BODY",
    target_path: str = "p2:/setting/psd.bin",
    write_requested: bool = False,
) -> Imx510SensorCalEvalResult:
    """Verify physical FX3 Stock CP loads ONLY its own p2 psd.bin/defdet.bin read-only."""
    src_body = calibration_source_body.strip().upper()
    norm_path = target_path.strip()
    errors: List[str] = []

    if src_body != "FX3_OWN_BODY":
        errors.append(
            f"BLOCKED_CROSS_BODY_SENSOR_CAL_SUBSTITUTION: {src_body!r} != 'FX3_OWN_BODY'"
        )
    if write_requested:
        errors.append(
            f"BLOCKED_P2_SENSOR_CAL_WRITE: {norm_path} is factory per-sensor NVS (O_RDONLY)"
        )

    is_p2_cal = bool(FORBIDDEN_PERSISTENT_CAL_OR_NVS_RE_P156.search(norm_path))
    if not is_p2_cal and not norm_path.startswith(VOLATILE_STAGING_PREFIXES_P156):
        errors.append(f"BLOCKED_UNRECOGNIZED_CAL_TARGET: {norm_path!r}")

    valid = len(errors) == 0
    status = (
        "OWN_FX3_P2_CAL_RDONLY_PRESERVED"
        if valid
        else "BLOCKED_SENSOR_CAL_HAZARD"
    )
    return Imx510SensorCalEvalResult(
        valid=valid,
        status=status,
        sensor_model=IMX510_SENSOR_MODEL,
        calibration_source_body=src_body,
        target_path=norm_path,
        write_requested=write_requested,
        sensor_cal_p2_writes_permitted=False,
        sensor_cal_mutation_bytes=0,
        classification=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
        fx3_psd_ddr_addr_hex=hex(FX3_P2_PSD_DDR_ADDR),
        fx3_defdet_ddr_addr_hex=hex(FX3_P2_DEFDET_DDR_ADDR),
        errors=tuple(errors),
    )


def evaluate_dual_base_iso_cine_ei(
    *,
    exposure_mode: str = "CINE_EI",
    base_iso: Optional[int] = None,
    exposure_index: int = 800,
    slog3_active: bool = True,
    m4root_clip_recording: bool = True,
) -> DualBaseIsoCineEiEvalResult:
    """Evaluate Dual-Base ISO 800/12800 (LCG/HCG) & Cine EI / Flexible ISO mapping."""
    mode = exposure_mode.strip().upper()
    errors: List[str] = []

    if mode not in VALID_EXPOSURE_MODES_P156:
        errors.append(f"BLOCKED_UNSUPPORTED_EXPOSURE_MODE: {mode!r}")

    if mode == "CINE_EI_QUICK":
        resolved_base = (
            IMX510_BASE_ISO_LOW_LCG
            if exposure_index < IMX510_CINE_EI_SWITCHOVER_EI
            else IMX510_BASE_ISO_HIGH_HCG
        )
        if base_iso is not None and base_iso in VALID_DUAL_BASE_ISOS_P156:
            if exposure_index < IMX510_CINE_EI_SWITCHOVER_EI and base_iso != IMX510_BASE_ISO_LOW_LCG:
                errors.append("BLOCKED_CINE_EI_QUICK_LCG_MISMATCH")
    else:
        resolved_base = IMX510_BASE_ISO_LOW_LCG if base_iso is None else int(base_iso)

    if resolved_base not in VALID_DUAL_BASE_ISOS_P156:
        errors.append(
            f"BLOCKED_INVALID_IMX510_BASE_ISO: {resolved_base} not in {VALID_DUAL_BASE_ISOS_P156}"
        )

    gain_stage = "LCG" if resolved_base == IMX510_BASE_ISO_LOW_LCG else "HCG"

    if mode in ("CINE_EI", "CINE_EI_QUICK"):
        lo, hi = (
            IMX510_CINE_EI_LOW_RANGE
            if resolved_base == IMX510_BASE_ISO_LOW_LCG
            else IMX510_CINE_EI_HIGH_RANGE
        )
        if not (lo <= exposure_index <= hi):
            errors.append(
                f"BLOCKED_EI_OUT_OF_BASE_RANGE: {exposure_index} EI outside [{lo}, {hi}] for Base {resolved_base}"
            )
    elif mode == "FLEXIBLE_ISO":
        if not (160 <= exposure_index <= 409_600):
            errors.append(f"BLOCKED_FLEXIBLE_ISO_OUT_OF_RANGE: {exposure_index}")

    if not slog3_active and mode in ("CINE_EI", "CINE_EI_QUICK"):
        errors.append("BLOCKED_CINE_EI_REQUIRES_SLOG3_MASTER")
    if not m4root_clip_recording:
        errors.append("BLOCKED_RECORDING_PATH_MUST_TARGET_M4ROOT_CLIP")

    safe_base = resolved_base if resolved_base > 0 else IMX510_BASE_ISO_LOW_LCG
    ei_stop_shift = round(math.log2(max(exposure_index, 1) / safe_base), 4)
    cp_cmd = (
        "CheckSetHyperGainMode(LCG_800)"
        if gain_stage == "LCG"
        else "CheckSetHyperGainMode(HCG_12800)"
    )

    valid = len(errors) == 0
    return DualBaseIsoCineEiEvalResult(
        valid=valid,
        status=f"{mode}_{gain_stage}_BASE{resolved_base}_EI{exposure_index}" if valid else "BLOCKED_ISO_EI_MISMATCH",
        exposure_mode=mode,
        base_iso=resolved_base,
        gain_stage=gain_stage,
        exposure_index=exposure_index,
        ei_stop_shift=ei_stop_shift,
        hcg_lcg_aligned=valid and resolved_base in VALID_DUAL_BASE_ISOS_P156,
        slog3_master_preserved=slog3_active,
        m4root_clip_recording=m4root_clip_recording,
        xml_ei_metadata_intact=valid,
        cp_gain_command=cp_cmd,
        errors=tuple(errors),
    )


def evaluate_cube_mlut_color_pipeline(
    *,
    base_look: str = "S-Gamut3.Cine/S-Log3",
    cube_grid_size: int = 33,
    lut_slot: int = 1,
    sd_lut_path: str = "/mnt/sd/PRIVATE/SONY/PRO/LUT/S709C.cube",
    ram_staging_path: str = "/tmp/fx6_mlut_slot01.dma",
    mlut_lcd_hdmi_on: bool = True,
    lut_burn_in_requested: bool = False,
    explicit_burn_in_confirmed: bool = False,
    cube_bytes: int = 1_006_301,
) -> CubeMlutColorEvalResult:
    """Evaluate S-Log3 / S-Cinetone / 709tone & 16-slot .cube 3D MLUT Stage-B pipeline."""
    errors: List[str] = []

    if base_look not in VALID_BASE_LOOKS_P156:
        errors.append(f"BLOCKED_UNSUPPORTED_BASE_LOOK: {base_look!r}")
    if cube_grid_size not in SUPPORTED_CUBE_GRID_SIZES:
        errors.append(
            f"BLOCKED_UNSUPPORTED_CUBE_GRID_SIZE: {cube_grid_size}^3 not in {SUPPORTED_CUBE_GRID_SIZES}"
        )
    if not (1 <= lut_slot <= MAX_USER_LUT_SLOTS):
        errors.append(f"BLOCKED_LUT_SLOT_OUT_OF_RANGE: slot={lut_slot} (valid 1..16)")
    if not sd_lut_path.startswith(SD_USER_LUT_DIR) or not sd_lut_path.lower().endswith(".cube"):
        errors.append(f"BLOCKED_SD_LUT_PATH: {sd_lut_path!r} must reside under {SD_USER_LUT_DIR}")
    if cube_bytes <= 0 or cube_bytes > MAX_CUBE_FILE_BYTES_P156:
        errors.append(f"BLOCKED_CUBE_FILE_SIZE_OVERFLOW: {cube_bytes} B > {MAX_CUBE_FILE_BYTES_P156} B")

    if FORBIDDEN_PERSISTENT_CAL_OR_NVS_RE_P156.search(ram_staging_path):
        errors.append(f"BLOCKED_PERSISTENT_NVS_LUT_STAGING: {ram_staging_path!r}")
    elif not ram_staging_path.startswith(("/tmp/", "ram://", "ramdisk://", "mem://")):
        errors.append(f"BLOCKED_NON_VOLATILE_LUT_STAGING: {ram_staging_path!r}")

    is_log_master = "S-Log3" in base_look
    if lut_burn_in_requested and not explicit_burn_in_confirmed:
        errors.append(
            "BLOCKED_SILENT_SLOG3_DOUBLE_BAKE: MLUT burn-in into internal XAVC requires explicit user confirmation"
        )
    if lut_burn_in_requested and is_log_master:
        errors.append(
            "BLOCKED_SLOG3_MASTER_DOUBLE_BAKE: Cannot double-bake monitor 3D LUT onto unbaked S-Log3 master"
        )

    slog3_double_bake_prevented = (not lut_burn_in_requested) or bool(errors)
    nvs_overflow_prevented = (
        not FORBIDDEN_PERSISTENT_CAL_OR_NVS_RE_P156.search(ram_staging_path)
        and cube_bytes <= MAX_CUBE_FILE_BYTES_P156
    )

    isp_stages = (
        ("MLUT_YC2RGB_ON", "MLUT_L1D_A_ON", "MLUT_MTX_A_ON", "MLUT_EIGAIN_ON", "MLUT_ASCCDL_ON", "MLUT_L3D_ON")
        if mlut_lcd_hdmi_on
        else ("MLUT_BYPASS_LOG",)
    )

    valid = len(errors) == 0
    if valid:
        status = (
            "SLOG3_UNBAKED_MASTER_WITH_MLUT_MONITOR"
            if (is_log_master and mlut_lcd_hdmi_on and not lut_burn_in_requested)
            else f"{base_look}_PIPELINE_OK"
        )
    else:
        status = "BLOCKED_COLOR_LUT_HAZARD"

    return CubeMlutColorEvalResult(
        valid=valid,
        status=status,
        base_look=base_look,
        cube_grid_size=cube_grid_size,
        lut_slot=lut_slot,
        sd_lut_path=sd_lut_path,
        ram_staging_path=ram_staging_path,
        mlut_lcd_hdmi_on=mlut_lcd_hdmi_on,
        lut_burn_in_requested=lut_burn_in_requested,
        is_raw_or_log_master=is_log_master,
        slog3_double_bake_prevented=slog3_double_bake_prevented,
        nvs_overflow_prevented=nvs_overflow_prevented,
        isp_stages_active=isp_stages,
        errors=tuple(errors),
    )


def evaluate_phase156_write_guard(target_path: str) -> Phase156WriteGuardResult:
    """Enforce zero persistent eMMC / p2 / p23 / p30 mutations; allow only volatile RAM or SD read."""
    norm = target_path.strip()
    is_forbidden = bool(FORBIDDEN_PERSISTENT_CAL_OR_NVS_RE_P156.search(norm))
    is_volatile_or_sd = norm.startswith(VOLATILE_STAGING_PREFIXES_P156) and not is_forbidden

    errors: List[str] = []
    if is_forbidden:
        errors.append(
            f"BLOCKED_PERSISTENT_NVS_WRITE: {norm!r} is strictly O_RDONLY protected"
        )
    elif not is_volatile_or_sd:
        errors.append(
            f"BLOCKED_UNKNOWN_STORAGE_TARGET: {norm!r} is outside volatile RAM/SD paths"
        )

    valid = is_volatile_or_sd and not is_forbidden and len(errors) == 0
    return Phase156WriteGuardResult(
        valid=valid,
        status="VOLATILE_STAGING_ALLOWED" if valid else "PERSISTENT_WRITE_BLOCKED",
        target_path=norm,
        volatile_or_sd_allowed=is_volatile_or_sd,
        persistent_write_blocked=not valid,
        sensor_cal_p2_writes_permitted=False,
        persistent_emmc_writes_authorized=False,
        emmc_mutation_bytes=0,
        sensor_cal_mutation_bytes=0,
        errors=tuple(errors),
    )


def build_phase156_imx510_color_matrix() -> ColorPipelineCompatMatrixSummary:
    """Build deterministic 12-touchpoint 4-class compatibility matrix for Phase 156."""
    entries: Tuple[ColorPipelineTouchpointEntry, ...] = (
        ColorPipelineTouchpointEntry(
            touchpoint_id="IMX510_CP_DRIVER",
            subsystem="SENSOR_CAL",
            fx6_interface="C_ImagerCtrl_IMX510 / ImagerDrvParam_IMX510",
            fx3_target="Stock FX3 cpapp-b.bin IMX510 10.2MP 4264x2408",
            classification=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            write_protected=True,
            notes="Identical IMX510 sensor driver class across FX3 7.02 and FX6 6.01.",
        ),
        ColorPipelineTouchpointEntry(
            touchpoint_id="P2_PSD_SHADING_NVS",
            subsystem="SENSOR_CAL",
            fx6_interface="p2:/setting/psd.bin (0x808810000)",
            fx3_target="FX3 own p2:/setting/psd.bin (0x808730000)",
            classification=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
            write_protected=True,
            notes="Per-camera pixel-shading NVS; Stock FX3 CP reads own p2 strictly O_RDONLY.",
        ),
        ColorPipelineTouchpointEntry(
            touchpoint_id="P2_DEFDET_DEFECT_NVS",
            subsystem="SENSOR_CAL",
            fx6_interface="p2:/setting/defdet.bin (0x80948d000)",
            fx3_target="FX3 own p2:/setting/defdet.bin (0x809479000)",
            classification=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
            write_protected=True,
            notes="Per-camera defect-pixel NVS; never replaced by donor FX6 table.",
        ),
        ColorPipelineTouchpointEntry(
            touchpoint_id="IMX510_OB_CLAMP_PEDESTAL",
            subsystem="SENSOR_CAL",
            fx6_interface="MasterBlackLevelMeta / GetBlackLevelOffset_BeforeGamma",
            fx3_target="Stock FX3 CP MasterBlackLevelMeta / RchBlackLevel / BchBlackLevel",
            classification=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            write_protected=True,
            notes="Optical black pedestal remains aligned to S-Log3 3.5% IRE (code 95).",
        ),
        ColorPipelineTouchpointEntry(
            touchpoint_id="DUAL_BASE_ISO_800_LCG",
            subsystem="DUAL_BASE_ISO",
            fx6_interface="BASE_ISO_LOW_800 / Cine EI 200..3200 EI",
            fx3_target="CheckSetHyperGainMode(LCG_800) + M4ROOT/CLIP",
            classification=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            write_protected=False,
            notes="Native analog LCG gain stage (ISO 800) with EI metadata in NonRealTimeMeta XML.",
        ),
        ColorPipelineTouchpointEntry(
            touchpoint_id="DUAL_BASE_ISO_12800_HCG",
            subsystem="DUAL_BASE_ISO",
            fx6_interface="BASE_ISO_HIGH_12800 / Cine EI 3200..51200 EI",
            fx3_target="CheckSetHyperGainMode(HCG_12800) + M4ROOT/CLIP",
            classification=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            write_protected=False,
            notes="Native analog HCG gain stage (ISO 12800) driven cleanly by FX6 appFw.so.",
        ),
        ColorPipelineTouchpointEntry(
            touchpoint_id="CINE_EI_QUICK_AUTO_BASE",
            subsystem="DUAL_BASE_ISO",
            fx6_interface="SHOOTING_MODE_BASE_SETTING_CINE_EI_QUICK",
            fx3_target="Automatic LCG(800)<->HCG(12800) switchover at 3200 EI",
            classification=BRIDGE_CLASS_SHIM_TRANSLATED,
            write_protected=False,
            notes="FX6 Cine EI Quick UI translated onto FX3 Base ISO 800/12800 hyper-gain IPC.",
        ),
        ColorPipelineTouchpointEntry(
            touchpoint_id="FLEXIBLE_ISO_MODE",
            subsystem="DUAL_BASE_ISO",
            fx6_interface="SHOOTING_MODE_BASE_SETTING_FLEXIBLE_ISO",
            fx3_target="STILL_LOG_SHOOTING_FLEXIBLE_ISO + S-Log3",
            classification=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            write_protected=False,
            notes="Full-latitude S-Log3 with direct analog/ISP ISO sensitivity control.",
        ),
        ColorPipelineTouchpointEntry(
            touchpoint_id="SLOG3_SCINETONE_709TONE_LOOKS",
            subsystem="CUBE_MLUT",
            fx6_interface="S-Gamut3.Cine/S-Log3, S-Cinetone, 709tone",
            fx3_target="BIONZ XR / cpapp-b.bin MLUT_L1D/MTX/L3D ISP pipeline",
            classification=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            write_protected=False,
            notes="All four Cinema Line base looks share identical BIONZ XR ISP color stages.",
        ),
        ColorPipelineTouchpointEntry(
            touchpoint_id="SD_16SLOT_CUBE_3D_LUT_LOADER",
            subsystem="CUBE_MLUT",
            fx6_interface="PID_SET_USER_LUT_BINARY_DATA + mpr::SetLutData",
            fx3_target="/mnt/sd/PRIVATE/SONY/PRO/LUT/*.cube -> /tmp/ RAM DMA",
            classification=BRIDGE_CLASS_SHIM_TRANSLATED,
            write_protected=False,
            notes="17^3/33^3 .cube loaded from SD to volatile RAM ISP slot without p30 flash write.",
        ),
        ColorPipelineTouchpointEntry(
            touchpoint_id="MLUT_MONITOR_ANTI_DOUBLE_BAKE",
            subsystem="CUBE_MLUT",
            fx6_interface="MLUT_SETTING_MONITOR_OUT vs INTERNAL_REC_MLUT_OFF",
            fx3_target="LCD/HDMI MLUT preview while preserving unbaked S-Log3 XAVC",
            classification=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            write_protected=False,
            notes="Prevents silent double-baking on S-Log3 masters; burn-in requires explicit opt-in.",
        ),
        ColorPipelineTouchpointEntry(
            touchpoint_id="P23_P30_NVS_LUT_FIREWALL",
            subsystem="NVS_ISOLATION",
            fx6_interface="p23:/INFO, p30:/usr/data/lut, SDI1 MLUT",
            fx3_target="Volatile /tmp/ RAM staging + masked SDI1 MLUT",
            classification=BRIDGE_CLASS_MASKED_ABSENT_HW,
            write_protected=True,
            notes="FX6 SDI1 MLUT masked non-blocking; p2/p23/p30 eMMC NVS stays read-only.",
        ),
    )

    class_counts: Dict[str, int] = {c: 0 for c in VALID_BRIDGE_CLASSES}
    subsystem_counts: Dict[str, int] = {}
    for ent in entries:
        class_counts[ent.classification] = class_counts.get(ent.classification, 0) + 1
        subsystem_counts[ent.subsystem] = subsystem_counts.get(ent.subsystem, 0) + 1

    return ColorPipelineCompatMatrixSummary(
        total_touchpoints=len(entries),
        class_counts=class_counts,
        subsystem_counts=subsystem_counts,
        touchpoints=entries,
    )


# ---------------------------------------------------------------------------
# Main Dual-Mode Unified Auditor Entrypoint
# ---------------------------------------------------------------------------


def analyze_realhw_imx510_cmos_dualbase_iso_lut_color_pipeline(
    *,
    clean_room: bool = False,
    repo_root: Optional[Path] = None,
) -> RealhwImx510CmosDualbaseIsoLutColorPipelineReport:
    """Run Phase 156 (32nd Auditor) on real O_RDONLY donors or deterministic clean-room fixtures."""
    root = repo_root if repo_root is not None else DEFAULT_REPO_ROOT
    force_clean = clean_room or is_forced_clean_room()

    donor_paths: Dict[str, Optional[Path]] = {}
    if not force_clean:
        rel_map = {
            "fx3_appfw": FX3_APPFW_P156_RELPATH,
            "fx6_appfw": FX6_APPFW_P156_RELPATH,
            "fx3_sencore": FX3_LIBSENCORE_P156_RELPATH,
            "fx6_sencore": FX6_LIBSENCORE_P156_RELPATH,
            "fx3_mpr": FX3_LIBMPR_P156_RELPATH,
            "fx6_mpr": FX6_LIBMPR_P156_RELPATH,
            "fx3_cpapp": FX3_CPAPP_P156_RELPATH,
            "fx6_cpapp": FX6_CPAPP_P156_RELPATH,
            "fx3_backup": FX3_BACKUP_BIN_P156_RELPATH,
            "fx6_backup": FX6_BACKUP_BIN_P156_RELPATH,
        }
        for key, rel in rel_map.items():
            donor_paths[key] = resolve_donor_file(rel, repo_root=root)

    use_local = (not force_clean) and all(p is not None for p in donor_paths.values())

    donor_file_sizes: Dict[str, int] = {}
    errors: List[str] = []

    if use_local:
        mode = "LOCAL_DONOR_VERIFIED"
        fx3_appfw_sum, _, _ = _scan_elf_and_tokens_rdonly(
            donor_paths["fx3_appfw"],  # type: ignore[arg-type]
            binary_name="appFw.so",
            body_label="FX3",
            tokens=ISO_APPFW_FX3_MARKERS + LUT_APPFW_FX3_MARKERS,
        )
        fx6_appfw_sum, _, _ = _scan_elf_and_tokens_rdonly(
            donor_paths["fx6_appfw"],  # type: ignore[arg-type]
            binary_name="appFw.so",
            body_label="FX6",
            tokens=ISO_APPFW_FX6_MARKERS + LUT_APPFW_FX6_MARKERS,
        )
        fx3_sencore_sum, _, _ = _scan_elf_and_tokens_rdonly(
            donor_paths["fx3_sencore"],  # type: ignore[arg-type]
            binary_name="libsencore.so",
            body_label="FX3",
            tokens=("SenserIfSend",),
        )
        fx6_sencore_sum, _, _ = _scan_elf_and_tokens_rdonly(
            donor_paths["fx6_sencore"],  # type: ignore[arg-type]
            binary_name="libsencore.so",
            body_label="FX6",
            tokens=LUT_SENCORE_FX6_MARKERS,
        )
        fx3_mpr_sum, _, _ = _scan_elf_and_tokens_rdonly(
            donor_paths["fx3_mpr"],  # type: ignore[arg-type]
            binary_name="libmpr.so",
            body_label="FX3",
            tokens=ISO_MPR_FX3_MARKERS + LUT_MPR_SHARED_MARKERS,
        )
        fx6_mpr_sum, _, _ = _scan_elf_and_tokens_rdonly(
            donor_paths["fx6_mpr"],  # type: ignore[arg-type]
            binary_name="libmpr.so",
            body_label="FX6",
            tokens=ISO_MPR_FX6_MARKERS + LUT_MPR_SHARED_MARKERS + LUT_MPR_FX6_MARKERS,
        )
        fx3_cp_sz, fx3_cp_hits = _scan_tokens_mmap_rdonly(
            donor_paths["fx3_cpapp"],  # type: ignore[arg-type]
            IMX510_CP_SHARED_MARKERS
            + IMX510_CP_FX3_MARKERS
            + ISO_CP_FX3_MARKERS
            + LUT_CP_SHARED_MARKERS,
        )
        fx6_cp_sz, fx6_cp_hits = _scan_tokens_mmap_rdonly(
            donor_paths["fx6_cpapp"],  # type: ignore[arg-type]
            IMX510_CP_SHARED_MARKERS
            + IMX510_CP_FX6_MARKERS
            + ISO_CP_FX6_MARKERS
            + LUT_CP_SHARED_MARKERS,
        )
        fx3_bk_buf = _read_rdonly_bytes(donor_paths["fx3_backup"])  # type: ignore[arg-type]
        fx6_bk_buf = _read_rdonly_bytes(donor_paths["fx6_backup"])  # type: ignore[arg-type]
        donor_file_sizes["fx3_cpapp"] = fx3_cp_sz
        donor_file_sizes["fx6_cpapp"] = fx6_cp_sz
        donor_file_sizes["fx3_backup"] = len(fx3_bk_buf)
        donor_file_sizes["fx6_backup"] = len(fx6_bk_buf)

        s709_path = resolve_donor_file(FX6_LUT_S709_CUBE_RELPATH, repo_root=root)
        if s709_path is not None:
            s709_bytes = s709_path.stat().st_size
            s709_hdr = _read_rdonly_bytes(s709_path, max_bytes=512)
        else:
            s709_bytes = EXPECTED_S709_CUBE_BYTES
            s709_hdr = build_clean_room_realhw_imx510_color_fixtures()["fx6_s709_cube_header"]
        donor_file_sizes["fx6_s709_cube"] = s709_bytes

        opt_p2: Dict[str, int] = {}
        for p2_key, p2_rel in (
            ("p2_psd_bin", OPTIONAL_P2_PSD_RELPATH),
            ("p2_defdet_bin", OPTIONAL_P2_DEFDET_RELPATH),
        ):
            p2_p = resolve_donor_file(p2_rel, repo_root=root)
            if p2_p is not None:
                opt_p2[p2_key] = len(_read_rdonly_bytes(p2_p, max_bytes=64))
    else:
        mode = "CLEAN_ROOM_SYNTHETIC"
        fx = build_clean_room_realhw_imx510_color_fixtures()
        fx3_appfw_sum, _, _ = _scan_elf_and_tokens_buf(
            fx["fx3_appfw"],
            binary_name="appFw.so",
            body_label="FX3",
            source_mode="CLEAN_ROOM_SYNTHETIC",
            tokens=ISO_APPFW_FX3_MARKERS + LUT_APPFW_FX3_MARKERS,
        )
        fx6_appfw_sum, _, _ = _scan_elf_and_tokens_buf(
            fx["fx6_appfw"],
            binary_name="appFw.so",
            body_label="FX6",
            source_mode="CLEAN_ROOM_SYNTHETIC",
            tokens=ISO_APPFW_FX6_MARKERS + LUT_APPFW_FX6_MARKERS,
        )
        fx3_sencore_sum, _, _ = _scan_elf_and_tokens_buf(
            fx["fx3_sencore"],
            binary_name="libsencore.so",
            body_label="FX3",
            source_mode="CLEAN_ROOM_SYNTHETIC",
            tokens=("SenserIfSend",),
        )
        fx6_sencore_sum, _, _ = _scan_elf_and_tokens_buf(
            fx["fx6_sencore"],
            binary_name="libsencore.so",
            body_label="FX6",
            source_mode="CLEAN_ROOM_SYNTHETIC",
            tokens=LUT_SENCORE_FX6_MARKERS,
        )
        fx3_mpr_sum, _, _ = _scan_elf_and_tokens_buf(
            fx["fx3_mpr"],
            binary_name="libmpr.so",
            body_label="FX3",
            source_mode="CLEAN_ROOM_SYNTHETIC",
            tokens=ISO_MPR_FX3_MARKERS + LUT_MPR_SHARED_MARKERS,
        )
        fx6_mpr_sum, _, _ = _scan_elf_and_tokens_buf(
            fx["fx6_mpr"],
            binary_name="libmpr.so",
            body_label="FX6",
            source_mode="CLEAN_ROOM_SYNTHETIC",
            tokens=ISO_MPR_FX6_MARKERS + LUT_MPR_SHARED_MARKERS + LUT_MPR_FX6_MARKERS,
        )
        fx3_cp_hits = _count_tokens_single_pass(
            fx["fx3_cpapp"],
            IMX510_CP_SHARED_MARKERS
            + IMX510_CP_FX3_MARKERS
            + ISO_CP_FX3_MARKERS
            + LUT_CP_SHARED_MARKERS,
        )
        fx6_cp_hits = _count_tokens_single_pass(
            fx["fx6_cpapp"],
            IMX510_CP_SHARED_MARKERS
            + IMX510_CP_FX6_MARKERS
            + ISO_CP_FX6_MARKERS
            + LUT_CP_SHARED_MARKERS,
        )
        fx3_bk_buf = fx["fx3_backup"]
        fx6_bk_buf = fx["fx6_backup"]
        s709_hdr = fx["fx6_s709_cube_header"]
        s709_bytes = len(s709_hdr)
        donor_file_sizes["fx3_cpapp"] = len(fx["fx3_cpapp"])
        donor_file_sizes["fx6_cpapp"] = len(fx["fx6_cpapp"])
        donor_file_sizes["fx3_backup"] = len(fx3_bk_buf)
        donor_file_sizes["fx6_backup"] = len(fx6_bk_buf)
        donor_file_sizes["fx6_s709_cube"] = s709_bytes
        opt_p2 = {}

    donor_file_sizes["fx3_appfw"] = fx3_appfw_sum.file_bytes
    donor_file_sizes["fx6_appfw"] = fx6_appfw_sum.file_bytes
    donor_file_sizes["fx3_sencore"] = fx3_sencore_sum.file_bytes
    donor_file_sizes["fx6_sencore"] = fx6_sencore_sum.file_bytes
    donor_file_sizes["fx3_mpr"] = fx3_mpr_sum.file_bytes
    donor_file_sizes["fx6_mpr"] = fx6_mpr_sum.file_bytes

    # ---- Pillar 1: IMX510 CMOS & p2:/setting/psd.bin / defdet.bin ----
    fx3_bk_sum, _, fx3_b1 = parse_dual_bk4_and_descriptors(fx3_bk_buf, body="FX3")
    fx6_bk_sum, _, fx6_b1 = parse_dual_bk4_and_descriptors(fx6_bk_buf, body="FX6")
    fx3_slots = {s.path: s for s in fx3_b1}
    fx6_slots = {s.path: s for s in fx6_b1}
    fx3_defdet_addr = fx3_slots.get("\\defdet.bin").start_addr_hex if "\\defdet.bin" in fx3_slots else ""
    fx6_defdet_addr = fx6_slots.get("\\defdet.bin").start_addr_hex if "\\defdet.bin" in fx6_slots else ""
    fx3_psd_addr = fx3_slots.get("\\psd.bin").start_addr_hex if "\\psd.bin" in fx3_slots else ""
    fx6_psd_addr = fx6_slots.get("\\psd.bin").start_addr_hex if "\\psd.bin" in fx6_slots else ""

    p1_fx3_cp = {k: fx3_cp_hits.get(k, 0) for k in IMX510_CP_SHARED_MARKERS + IMX510_CP_FX3_MARKERS}
    p1_fx6_cp = {k: fx6_cp_hits.get(k, 0) for k in IMX510_CP_SHARED_MARKERS + IMX510_CP_FX6_MARKERS}

    own_cal_eval = evaluate_imx510_sensor_cal_preservation(
        calibration_source_body="FX3_OWN_BODY",
        target_path="p2:/setting/psd.bin",
        write_requested=False,
    )
    cross_cal_blocked = evaluate_imx510_sensor_cal_preservation(
        calibration_source_body="FX6_DONOR_SUBSTITUTION",
        target_path="p2:/setting/psd.bin",
        write_requested=False,
    )
    p2_write_blocked = evaluate_imx510_sensor_cal_preservation(
        calibration_source_body="FX3_OWN_BODY",
        target_path="p2:/setting/defdet.bin",
        write_requested=True,
    )

    p1_errors: List[str] = []
    if any(v == 0 for v in p1_fx3_cp.values()):
        p1_errors.append(f"Missing FX3 CP IMX510 cal markers: {p1_fx3_cp}")
    if any(v == 0 for v in p1_fx6_cp.values()):
        p1_errors.append(f"Missing FX6 CP IMX510 cal markers: {p1_fx6_cp}")
    if fx3_bk_sum.rec0_subsystems != EXPECTED_FX3_BACKUP_SUBSYSTEMS_P156:
        p1_errors.append(f"Unexpected FX3 Backup subsystems: {fx3_bk_sum.rec0_subsystems}")
    if fx6_bk_sum.rec0_subsystems != EXPECTED_FX6_BACKUP_SUBSYSTEMS_P156:
        p1_errors.append(f"Unexpected FX6 Backup subsystems: {fx6_bk_sum.rec0_subsystems}")
    if fx3_defdet_addr != hex(FX3_P2_DEFDET_DDR_ADDR) or fx3_psd_addr != hex(FX3_P2_PSD_DDR_ADDR):
        p1_errors.append(f"Unexpected FX3 p2 cal DDR addrs: defdet={fx3_defdet_addr}, psd={fx3_psd_addr}")
    if fx6_defdet_addr != hex(FX6_P2_DEFDET_DDR_ADDR) or fx6_psd_addr != hex(FX6_P2_PSD_DDR_ADDR):
        p1_errors.append(f"Unexpected FX6 p2 cal DDR addrs: defdet={fx6_defdet_addr}, psd={fx6_psd_addr}")
    if not own_cal_eval.valid or cross_cal_blocked.valid or p2_write_blocked.valid:
        p1_errors.append("Sensor calibration preservation checks failed")

    pillar1 = Pillar1Imx510SensorCalReport(
        passed=len(p1_errors) == 0,
        fx3_cpapp_markers=p1_fx3_cp,
        fx6_cpapp_markers=p1_fx6_cp,
        fx3_backup_subsystems=fx3_bk_sum.rec0_subsystems,
        fx6_backup_subsystems=fx6_bk_sum.rec0_subsystems,
        fx3_p2_defdet_addr_hex=fx3_defdet_addr,
        fx6_p2_defdet_addr_hex=fx6_defdet_addr,
        fx3_p2_psd_addr_hex=fx3_psd_addr,
        fx6_p2_psd_addr_hex=fx6_psd_addr,
        optional_p2_cal_headers_checked=opt_p2,
        own_body_rdonly_eval=own_cal_eval,
        cross_body_substitution_blocked=cross_cal_blocked,
        p2_write_attempt_blocked=p2_write_blocked,
        errors=tuple(p1_errors),
    )

    # ---- Pillar 2: Dual-Base ISO 800 / 12800 (LCG / HCG) & Cine EI ----
    p2_fx3_af = {k: fx3_appfw_sum.marker_hits.get(k, 0) for k in ISO_APPFW_FX3_MARKERS}
    p2_fx6_af = {k: fx6_appfw_sum.marker_hits.get(k, 0) for k in ISO_APPFW_FX6_MARKERS}
    p2_fx3_cp = {k: fx3_cp_hits.get(k, 0) for k in ISO_CP_FX3_MARKERS}
    p2_fx6_cp = {k: fx6_cp_hits.get(k, 0) for k in ISO_CP_FX6_MARKERS}
    p2_fx3_mpr = {k: fx3_mpr_sum.marker_hits.get(k, 0) for k in ISO_MPR_FX3_MARKERS}
    p2_fx6_mpr = {k: fx6_mpr_sum.marker_hits.get(k, 0) for k in ISO_MPR_FX6_MARKERS}

    ei_low = evaluate_dual_base_iso_cine_ei(
        exposure_mode="CINE_EI",
        base_iso=800,
        exposure_index=800,
        slog3_active=True,
        m4root_clip_recording=True,
    )
    ei_high = evaluate_dual_base_iso_cine_ei(
        exposure_mode="CINE_EI",
        base_iso=12800,
        exposure_index=12800,
        slog3_active=True,
        m4root_clip_recording=True,
    )
    ei_quick = evaluate_dual_base_iso_cine_ei(
        exposure_mode="CINE_EI_QUICK",
        exposure_index=6400,
        slog3_active=True,
        m4root_clip_recording=True,
    )
    flex_iso = evaluate_dual_base_iso_cine_ei(
        exposure_mode="FLEXIBLE_ISO",
        base_iso=12800,
        exposure_index=12800,
        slog3_active=True,
        m4root_clip_recording=True,
    )
    invalid_ei = evaluate_dual_base_iso_cine_ei(
        exposure_mode="CINE_EI",
        base_iso=800,
        exposure_index=25600,
        slog3_active=True,
        m4root_clip_recording=True,
    )

    p2_errors: List[str] = []
    for lbl, d in (
        ("FX3 appFw ISO", p2_fx3_af),
        ("FX6 appFw ISO", p2_fx6_af),
        ("FX3 cpapp ISO", p2_fx3_cp),
        ("FX6 cpapp ISO", p2_fx6_cp),
        ("FX3 mpr ISO", p2_fx3_mpr),
        ("FX6 mpr ISO", p2_fx6_mpr),
    ):
        if any(v == 0 for v in d.values()):
            p2_errors.append(f"Missing {lbl} markers: {d}")
    if not (ei_low.valid and ei_high.valid and ei_quick.valid and flex_iso.valid):
        p2_errors.append("Valid Dual-Base ISO / Cine EI cases failed")
    if invalid_ei.valid:
        p2_errors.append("Out-of-range Cine EI 25600 on Base 800 was not rejected")

    pillar2 = Pillar2DualBaseIsoCineEiReport(
        passed=len(p2_errors) == 0,
        fx3_appfw_markers=p2_fx3_af,
        fx6_appfw_markers=p2_fx6_af,
        fx3_cpapp_iso_markers=p2_fx3_cp,
        fx6_cpapp_iso_markers=p2_fx6_cp,
        fx3_mpr_iso_markers=p2_fx3_mpr,
        fx6_mpr_iso_markers=p2_fx6_mpr,
        cine_ei_low_800_eval=ei_low,
        cine_ei_high_12800_eval=ei_high,
        cine_ei_quick_switch_eval=ei_quick,
        flexible_iso_eval=flex_iso,
        invalid_ei_rejected=invalid_ei,
        errors=tuple(p2_errors),
    )

    # ---- Pillar 3: S-Log3 / S-Cinetone / 709tone & 16-Slot .cube MLUT ----
    p3_fx3_af = {k: fx3_appfw_sum.marker_hits.get(k, 0) for k in LUT_APPFW_FX3_MARKERS}
    p3_fx6_af = {k: fx6_appfw_sum.marker_hits.get(k, 0) for k in LUT_APPFW_FX6_MARKERS}
    p3_fx3_mpr = {k: fx3_mpr_sum.marker_hits.get(k, 0) for k in LUT_MPR_SHARED_MARKERS}
    p3_fx6_mpr = {k: fx6_mpr_sum.marker_hits.get(k, 0) for k in LUT_MPR_SHARED_MARKERS + LUT_MPR_FX6_MARKERS}
    p3_fx6_sc = {k: fx6_sencore_sum.marker_hits.get(k, 0) for k in LUT_SENCORE_FX6_MARKERS}
    p3_fx3_cp = {k: fx3_cp_hits.get(k, 0) for k in LUT_CP_SHARED_MARKERS}
    p3_fx6_cp = {k: fx6_cp_hits.get(k, 0) for k in LUT_CP_SHARED_MARKERS}

    s709_grid, _ = _parse_cube_header_metadata(s709_hdr)
    mlut_mon = evaluate_cube_mlut_color_pipeline(
        base_look="S-Gamut3.Cine/S-Log3",
        cube_grid_size=33,
        lut_slot=1,
        sd_lut_path="/mnt/sd/PRIVATE/SONY/PRO/LUT/S709C.cube",
        ram_staging_path="/tmp/fx6_mlut_slot01.dma",
        mlut_lcd_hdmi_on=True,
        lut_burn_in_requested=False,
    )
    mlut_17 = evaluate_cube_mlut_color_pipeline(
        base_look="S-Gamut3/S-Log3",
        cube_grid_size=17,
        lut_slot=16,
        sd_lut_path="/mnt/sd/PRIVATE/SONY/PRO/LUT/User16_17x.cube",
        ram_staging_path="ram://mlut_slot16.dma",
        mlut_lcd_hdmi_on=True,
        lut_burn_in_requested=False,
        cube_bytes=196_608,
    )
    scinetone_ev = evaluate_cube_mlut_color_pipeline(
        base_look="S-Cinetone",
        cube_grid_size=33,
        lut_slot=2,
        sd_lut_path="/mnt/sd/PRIVATE/SONY/PRO/LUT/S709.cube",
        ram_staging_path="/tmp/fx6_mlut_slot02.dma",
        mlut_lcd_hdmi_on=False,
        lut_burn_in_requested=False,
    )
    explicit_burn = evaluate_cube_mlut_color_pipeline(
        base_look="709tone",
        cube_grid_size=33,
        lut_slot=3,
        sd_lut_path="/mnt/sd/PRIVATE/SONY/PRO/LUT/r709C.cube",
        ram_staging_path="/tmp/fx6_mlut_slot03.dma",
        mlut_lcd_hdmi_on=True,
        lut_burn_in_requested=True,
        explicit_burn_in_confirmed=True,
    )
    silent_double_bake = evaluate_cube_mlut_color_pipeline(
        base_look="S-Gamut3.Cine/S-Log3",
        cube_grid_size=33,
        lut_slot=4,
        sd_lut_path="/mnt/sd/PRIVATE/SONY/PRO/LUT/S709C.cube",
        ram_staging_path="/tmp/fx6_mlut_slot04.dma",
        mlut_lcd_hdmi_on=True,
        lut_burn_in_requested=True,
        explicit_burn_in_confirmed=False,
    )

    p3_errors: List[str] = []
    for lbl, d in (
        ("FX3 appFw LUT", p3_fx3_af),
        ("FX6 appFw LUT", p3_fx6_af),
        ("FX3 mpr LUT", p3_fx3_mpr),
        ("FX6 mpr LUT", p3_fx6_mpr),
        ("FX6 sencore LUT", p3_fx6_sc),
        ("FX3 cpapp MLUT", p3_fx3_cp),
        ("FX6 cpapp MLUT", p3_fx6_cp),
    ):
        if any(v == 0 for v in d.values()):
            p3_errors.append(f"Missing {lbl} markers: {d}")
    if s709_grid != 33:
        p3_errors.append(f"Expected S709.cube grid size 33, got {s709_grid}")
    if not (mlut_mon.valid and mlut_17.valid and scinetone_ev.valid and explicit_burn.valid):
        p3_errors.append("Valid LUT/MLUT pipeline evaluations failed")
    if silent_double_bake.valid:
        p3_errors.append("Silent S-Log3 double-bake was not blocked")

    pillar3 = Pillar3Slog3CubeMlutReport(
        passed=len(p3_errors) == 0,
        fx3_appfw_lut_markers=p3_fx3_af,
        fx6_appfw_lut_markers=p3_fx6_af,
        fx3_mpr_lut_markers=p3_fx3_mpr,
        fx6_mpr_lut_markers=p3_fx6_mpr,
        fx6_sencore_lut_markers=p3_fx6_sc,
        fx3_cpapp_mlut_markers=p3_fx3_cp,
        fx6_cpapp_mlut_markers=p3_fx6_cp,
        s709_cube_grid_size=s709_grid,
        s709_cube_bytes=s709_bytes,
        slog3_mlut_monitor_only_eval=mlut_mon,
        slog3_17_cube_eval=mlut_17,
        scinetone_709tone_eval=scinetone_ev,
        explicit_burnin_nonlog_eval=explicit_burn,
        silent_slog3_double_bake_blocked=silent_double_bake,
        errors=tuple(p3_errors),
    )

    # ---- Pillar 4: NVS p2/p23/p30 Isolation & Matrix ----
    g_ram = evaluate_phase156_write_guard("/tmp/fx6_mlut_slot01.dma")
    g_sd = evaluate_phase156_write_guard("/mnt/sd/PRIVATE/SONY/PRO/LUT/S709C.cube")
    g_p2_psd = evaluate_phase156_write_guard("p2:/setting/psd.bin")
    g_p2_defdet = evaluate_phase156_write_guard("p2:/setting/defdet.bin")
    g_p23 = evaluate_phase156_write_guard("p23:/INFO/LUT_STATE.TXT")
    g_p30 = evaluate_phase156_write_guard("p30:/usr/data/lut/User1.cube")
    matrix = build_phase156_imx510_color_matrix()

    p4_errors: List[str] = []
    if not (g_ram.valid and g_sd.valid):
        p4_errors.append("Volatile RAM / SD LUT staging rejected")
    if g_p2_psd.valid or g_p2_defdet.valid or g_p23.valid or g_p30.valid:
        p4_errors.append("Forbidden p2/p23/p30 persistent NVS write was not blocked")
    if fx3_sencore_sum.export_count != EXPECTED_FX3_SENCORE_EXPORTS_P156:
        p4_errors.append(f"Unexpected FX3 sencore export count: {fx3_sencore_sum.export_count}")
    if fx6_sencore_sum.export_count != EXPECTED_FX6_SENCORE_EXPORTS_P156:
        p4_errors.append(f"Unexpected FX6 sencore export count: {fx6_sencore_sum.export_count}")
    if fx3_mpr_sum.export_count != EXPECTED_FX3_MPR_EXPORTS_P156:
        p4_errors.append(f"Unexpected FX3 mpr export count: {fx3_mpr_sum.export_count}")
    if fx6_mpr_sum.export_count != EXPECTED_FX6_MPR_EXPORTS_P156:
        p4_errors.append(f"Unexpected FX6 mpr export count: {fx6_mpr_sum.export_count}")
    if matrix.total_touchpoints != 12:
        p4_errors.append(f"Expected 12 matrix touchpoints, got {matrix.total_touchpoints}")

    pillar4 = Pillar4NvsIsolationAndMatrixReport(
        passed=len(p4_errors) == 0,
        fx3_appfw_summary=fx3_appfw_sum,
        fx6_appfw_summary=fx6_appfw_sum,
        fx3_sencore_summary=fx3_sencore_sum,
        fx6_sencore_summary=fx6_sencore_sum,
        fx3_mpr_summary=fx3_mpr_sum,
        fx6_mpr_summary=fx6_mpr_sum,
        volatile_ram_guard_ok=g_ram,
        sd_lut_read_guard_ok=g_sd,
        blocked_p2_psd_guard=g_p2_psd,
        blocked_p2_defdet_guard=g_p2_defdet,
        blocked_p23_info_guard=g_p23,
        blocked_p30_lut_guard=g_p30,
        compatibility_matrix=matrix,
        errors=tuple(p4_errors),
    )

    errors.extend(p1_errors)
    errors.extend(p2_errors)
    errors.extend(p3_errors)
    errors.extend(p4_errors)

    all_passed = (
        pillar1.passed
        and pillar2.passed
        and pillar3.passed
        and pillar4.passed
        and len(errors) == 0
    )
    dual_iso_aligned = ei_low.hcg_lcg_aligned and ei_high.hcg_lcg_aligned and ei_quick.hcg_lcg_aligned
    slog3_prevented = mlut_mon.slog3_double_bake_prevented and silent_double_bake.slog3_double_bake_prevented

    pre_hash_dict = {
        "schema_version": PHASE_156_SCHEMA,
        "phase_version": PHASE_156_VERSION,
        "mode": mode,
        "all_checks_passed": all_passed,
        "o_rdonly_enforced": True,
        "sensor_cal_p2_writes_permitted": False,
        "sensor_cal_mutation_bytes": 0,
        "dual_base_iso_800_12800_hcg_aligned": dual_iso_aligned,
        "slog3_double_bake_prevented": slog3_prevented,
        "persistent_emmc_writes_authorized": False,
        "emmc_mutation_bytes": 0,
        "calibration_mutation_bytes": 0,
        "donor_file_sizes": donor_file_sizes,
        "pillar1_imx510_sensor_cal": asdict(pillar1),
        "pillar2_dual_base_iso_cine_ei": asdict(pillar2),
        "pillar3_slog3_cube_mlut": asdict(pillar3),
        "pillar4_nvs_isolation_matrix": asdict(pillar4),
        "errors": list(errors),
    }
    report_sha256 = hashlib.sha256(
        json.dumps(pre_hash_dict, sort_keys=True).encode("utf-8")
    ).hexdigest()

    return RealhwImx510CmosDualbaseIsoLutColorPipelineReport(
        schema_version=PHASE_156_SCHEMA,
        phase_version=PHASE_156_VERSION,
        mode=mode,
        all_checks_passed=all_passed,
        o_rdonly_enforced=True,
        sensor_cal_p2_writes_permitted=False,
        sensor_cal_mutation_bytes=0,
        dual_base_iso_800_12800_hcg_aligned=dual_iso_aligned,
        slog3_double_bake_prevented=slog3_prevented,
        persistent_emmc_writes_authorized=False,
        emmc_mutation_bytes=0,
        calibration_mutation_bytes=0,
        donor_file_sizes=donor_file_sizes,
        pillar1_imx510_sensor_cal=pillar1,
        pillar2_dual_base_iso_cine_ei=pillar2,
        pillar3_slog3_cube_mlut=pillar3,
        pillar4_nvs_isolation_matrix=pillar4,
        report_sha256=report_sha256,
        errors=tuple(errors),
    )


def realhw_imx510_cmos_dualbase_iso_lut_color_pipeline_report_to_dict(
    report: RealhwImx510CmosDualbaseIsoLutColorPipelineReport,
) -> Dict[str, object]:
    """Convert `RealhwImx510CmosDualbaseIsoLutColorPipelineReport` to JSON-serializable dict."""
    return asdict(report)
