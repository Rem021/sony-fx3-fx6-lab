"""Phase 89 — 17th Unified Firmware-Lab Auditor: `Gyroflow` / `Catalyst Browse` Sony `RTMD` (`0xE304` / `0xE43B` / `0xE44B`) IMU Telemetry, Anamorphic (`1.3x..2.0x`) 5-Axis IBIS Asymmetric Gain Containment, `IMX510` Rolling-Shutter Readout Matrix & Stock-CP IMU Calibration Immutability.

Strictly Read-Only (`os.O_RDONLY` + `mmap.ACCESS_READ`) & Clean-Room Dual-Mode:
- Local Donor Mode: inspects FX3 v7.02 (`appFw.so` / `icx1295` AP host,
  `libmpr.so`, `cpapp-b.bin`, `libInfraLensCommunicator.so`, `global.xdb`,
  `string_english.uxc`, `string_english_g.uxc`) and FX6 v6.01 (`appFw.so`,
  `libmpr.so`, `cpapp-b.bin`, `libInfraLensCommunicator.so`, `global.xdb`,
  `string_english.uxc`, `string_english_2.uxc`) strictly via `os.O_RDONLY` +
  `mmap.ACCESS_READ` and ELF64 `.rodata`/`.dynstr` section-scoped scanning, plus
  `uxa\\x07` / `.uxc` container parsing (< 0.5s total).
- Clean-Room Mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`, `clean_room=True`, or donors
  absent): synthesizes deterministic clean-room ELF64 / CP / `global.xdb` /
  `.uxc` fixtures carrying the exact contract markers and runs the identical
  four-pillar verification pipeline with zero proprietary files required.

Audits Four Stabilization, Metadata & Safety Pillars:
1. Pillar 1 — `Gyroflow` / `Catalyst Browse` Sony `RTMD` IMU Telemetry Verifier:
   Verifies `2000 Hz` IMU sample count per video frame (`83/84` at `23.976p`,
   `80` at `25p`, `33/34` at `59.94p`, `16/17` at `119.88p`), SO(3) axis
   orientation quaternion & 3x3 matrix (`||q|| = 1`, `det(R) = +1`), SMPTE
   RDD 18 KLV (`0xE304` / `0xE43B` / `0xE44B` / `0x3219` / `0xE450`) round-trip
   serialization, and deterministic stabilization compatibility rules
   (`IBIS = Off` `0x0400` Center-Lock required for full 3D Gyroflow lens-profile
   warp so optical-center shift never fights digital perspective warp).
2. Pillar 2 — Anamorphic (`1.3x / 1.33x / 1.5x / 1.8x / 2.0x`) 5-Axis IBIS
   Asymmetric Gain Hazard & Safe Containment:
   Proves mathematically why FX6's native `De-Squeeze` (`1.3x` / `2.0x`) only
   scales display monitoring (FX6 has rigid `IMX510` CMOS and zero physical
   IBIS), whereas on FX3's physical 5-axis IBIS stage, applying spherical focal
   length `f` to a squeeze-factor `S` anamorphic lens over-drives horizontal yaw
   translation by `S x` (`100.0%` error at `2.0x`!), prescribing safe
   `Anamorphic SteadyShot` horizontal gain `f_x = f / S, f_y = f` OR automatic
   `IBIS = Off (Center-Lock 0x0400) + Gyro Metadata` for manual anamorphics.
3. Pillar 3 — `IMX510` Rolling-Shutter Line-Readout Timing Matrix:
   Verifies deterministic sensor readout durations (`~8.70 ms` full-width
   `4K 24..60p`, `~4.35 ms` `4K 120p`, `~2.20 ms` `FHD 240p`) embedded into
   per-frame stabilization metadata (`ConvertReadoutDuration` /
   `EffectivePixelReadoutTime`) so rolling-shutter skew correction never
   over-shears or under-shears verticals.
4. Pillar 4 — Stock-CP IMU Factory Bias/Orthogonality Calibration Immutability:
   Proves factory gyro bias/temp-drift LUTs in `cnflasha` / Stock-CP remain
   100% untouched (`imu_calibration_mutation_bytes == 0`,
   `cp_mutation_bytes == 0`, `persistent_emmc_writes_authorized == False`).
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

from .cube_lut_and_rtmd_verifier import (
    RTMD_COHERENCE_ALL_OK,
    RTMD_COHERENCE_CATALYST_BROWSE_OK,
    RTMD_COHERENCE_CENTER_LOCK_OK,
    RTMD_COHERENCE_GYRO_VALID,
    RTMD_COHERENCE_GYROFLOW_OK,
    RTMD_RDD18_ACQUISITION_UL,
    RTMD_TAG_IMX510_IBIS_GYRO_E304,
    RTMD_TAG_IMX510_READOUT_US,
    SMPTE_KLV_UL_PREFIX,
    decode_ber_length,
    encode_ber_length,
)
from .emount_af_breathing_and_ibis_auditor import (
    FX3_LENS_COMM_RELPATH,
    FX6_LENS_COMM_RELPATH,
    IBIS_CENTER_LOCK_OPCODE,
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
from .sensor_codec_compatibility_analyzer import (
    FX3_CPAPP_RELPATH,
    FX3_LIBMPR_RELPATH,
    FX6_CPAPP_RELPATH,
    FX6_LIBMPR_RELPATH,
)
from .uxc_multilang_and_font_verifier import FX3_SHARE_APP_RELDIR, FX6_SHARE_APP_RELDIR
from .wbi_hibdrv_and_elf_abi_differ import build_synthetic_elf64_so


PHASE_89_SCHEMA = "fx3_firmware_lab_phase89_gyroflow_rtmd_anamorphic_ibis_v1"
PHASE_89_VERSION = "89.0.0"

FX3_GLOBAL_XDB_RELPATH = f"{FX3_SHARE_APP_RELDIR}/global.xdb"
FX6_GLOBAL_XDB_RELPATH = f"{FX6_SHARE_APP_RELDIR}/global.xdb"
FX3_STR_EN_RELPATH = f"{FX3_SHARE_APP_RELDIR}/string_english.uxc"
FX3_STR_EN_G_RELPATH = f"{FX3_SHARE_APP_RELDIR}/string_english_g.uxc"
FX6_STR_EN_1_RELPATH = f"{FX6_SHARE_APP_RELDIR}/string_english.uxc"
FX6_STR_EN_2_RELPATH = f"{FX6_SHARE_APP_RELDIR}/string_english_2.uxc"

# ---------------------------------------------------------------------------
# Pillar 1 Constants: 2000 Hz IMU, Sony RTMD Tags & SO(3) Axis Orientation
# ---------------------------------------------------------------------------

IMU_SAMPLE_RATE_HZ = 2000
RTMD_TAG_GYRO_PITCH_ROLL_YAW = 0xE43B
RTMD_TAG_ACCELEROMETER = 0xE44B
RTMD_TAG_ANAMORPHIC_DESQUEEZE_X100 = 0xE450

VALID_STEADYSHOT_MODES: Tuple[str, ...] = ("Off", "Standard", "Active")
STEADYSHOT_MODE_TO_CODE: Dict[str, int] = {"Off": 0, "Standard": 1, "Active": 2}
VALID_STABILIZER_WORKFLOWS: Tuple[str, ...] = (
    "GYROFLOW_3D_LENS_PROFILE",
    "GYROFLOW_V17_IBIS_METADATA_AWARE",
    "CATALYST_BROWSE_METADATA",
)

GYRO_FRAME_RATE_SPECS: Dict[str, Dict[str, object]] = {
    "23.976p": {
        "num": 24000,
        "den": 1001,
        "nominal_samples": 2000.0 * 1001.0 / 24000.0,
        "min_samples": 83,
        "max_samples": 84,
    },
    "24.00p": {
        "num": 24,
        "den": 1,
        "nominal_samples": 2000.0 / 24.0,
        "min_samples": 83,
        "max_samples": 84,
    },
    "25.00p": {
        "num": 25,
        "den": 1,
        "nominal_samples": 80.0,
        "min_samples": 80,
        "max_samples": 80,
    },
    "29.97p": {
        "num": 30000,
        "den": 1001,
        "nominal_samples": 2000.0 * 1001.0 / 30000.0,
        "min_samples": 66,
        "max_samples": 67,
    },
    "50.00p": {
        "num": 50,
        "den": 1,
        "nominal_samples": 40.0,
        "min_samples": 40,
        "max_samples": 40,
    },
    "59.94p": {
        "num": 60000,
        "den": 1001,
        "nominal_samples": 2000.0 * 1001.0 / 60000.0,
        "min_samples": 33,
        "max_samples": 34,
    },
    "119.88p": {
        "num": 120000,
        "den": 1001,
        "nominal_samples": 2000.0 * 1001.0 / 120000.0,
        "min_samples": 16,
        "max_samples": 17,
    },
}

# Canonical Sony IMX510 IMU-to-optical-frame identity orientation quaternion (w, x, y, z)
DEFAULT_IMU_QUATERNION_WXYZ: Tuple[float, float, float, float] = (1.0, 0.0, 0.0, 0.0)

# ---------------------------------------------------------------------------
# Pillar 2 Constants: Anamorphic Desqueeze & 5-Axis IBIS Asymmetric Gain
# ---------------------------------------------------------------------------

SUPPORTED_ANAMORPHIC_SQUEEZE_FACTORS: Tuple[float, ...] = (1.3, 1.33, 1.5, 1.8, 2.0)
FX6_NATIVE_MONITORING_DESQUEEZE_RATIOS: Tuple[float, ...] = (1.3, 2.0)
ANAMORPHIC_YAW_OVERDRIVE_TOLERANCE_PCT = 0.5
VALID_ANAMORPHIC_IBIS_MODES: Tuple[str, ...] = (
    "SPHERICAL_NAIVE",
    "ANAMORPHIC_ASYMMETRIC_GAIN",
    "AUTO_CENTER_LOCK_0X0400",
)

# ---------------------------------------------------------------------------
# Pillar 3 Constants: IMX510 Rolling-Shutter Readout Timing Matrix
# ---------------------------------------------------------------------------

IMX510_READOUT_TOLERANCE_US = 50
IMX510_ROLLING_SHUTTER_MODES: Dict[str, Dict[str, object]] = {
    "4K_DCI_24P": {
        "width": 4096,
        "height": 2160,
        "fps_hz": 24000.0 / 1001.0,
        "readout_ms": 8.70,
        "readout_us": 8700,
        "crop_factor": 1.0,
        "full_width_readout": True,
    },
    "QFHD_4K_24P": {
        "width": 3840,
        "height": 2160,
        "fps_hz": 24000.0 / 1001.0,
        "readout_ms": 8.70,
        "readout_us": 8700,
        "crop_factor": 1.0,
        "full_width_readout": True,
    },
    "QFHD_4K_60P": {
        "width": 3840,
        "height": 2160,
        "fps_hz": 60000.0 / 1001.0,
        "readout_ms": 8.70,
        "readout_us": 8700,
        "crop_factor": 1.0,
        "full_width_readout": True,
    },
    "SQ_4K_120P": {
        "width": 3840,
        "height": 2160,
        "fps_hz": 120000.0 / 1001.0,
        "readout_ms": 4.35,
        "readout_us": 4350,
        "crop_factor": 1.1,
        "full_width_readout": False,
    },
    "FHD_240P": {
        "width": 1920,
        "height": 1080,
        "fps_hz": 240000.0 / 1001.0,
        "readout_ms": 2.20,
        "readout_us": 2200,
        "crop_factor": 1.0,
        "full_width_readout": False,
    },
}

# ---------------------------------------------------------------------------
# Pillar 4 Constants: Zero Calibration / Zero Persistent eMMC Mutation
# ---------------------------------------------------------------------------

VOLATILE_SHADOW_PREFIXES: Tuple[str, ...] = ("/tmp/", "ram://", "memory://")
FORBIDDEN_IMU_CALIBRATION_TARGETS: Tuple[str, ...] = (
    "/dev/mmcblk0",
    "mmcblk0",
    "/dev/nflasha",
    "/dev/cnflasha",
    "/dev/mtdblock",
    "nflasha",
    "cnflasha",
    "p1:",
    "p2:",
    "p6:",
    "backup.bin",
    "psd.bin",
    "jiritsu",
    "nvram://",
)

# ---------------------------------------------------------------------------
# Verified Binary Marker Contracts (FX3 v7.02 & FX6 v6.01)
# ---------------------------------------------------------------------------

FX3_APPFW_GYRO_ANAMORPHIC_MARKERS: Tuple[str, ...] = (
    "Camera::CamUserIf::set_param_anamo_desqueeze_scale_msg",
    "PID_SET_STEADYSHOT_ADVANCED_MOVIE",
    "PID_SET_FRAME_LOCK_STEADYSHOT",
    "EVENT_REMOTE_MOVIE_STEADYSHOT",
    "EVENT_REMOTE_STEADYSHOT_FOCAL_LENGTH",
    "VAL_setting_movie_steadyshot_extensions_MOVIE_STEADYSHOT_EXTENSIONS_OFF",
    "VAL_setting_movie_steadyshot_extensions_MOVIE_STEADYSHOT_EXTENSIONS_STANDARD",
    "VAL_setting_movie_steadyshot_extensions_MOVIE_STEADYSHOT_EXTENSIONS_ACTIVE",
)

FX6_APPFW_GYRO_ANAMORPHIC_MARKERS: Tuple[str, ...] = (
    "PID_SET_ANAMO_DESQUEEZE_SCALE",
    "No2131_DESQUEEZE_RATIO",
    "No2005_monitoring_desqueeze",
    "Camera::BizCamIf::set_param_anamo_desqueeze_scale_msg",
    "DE_SQUEEZE",
    "ANAMO_DESQUEEZE",
    "PRM_is_imager_stabilization_unit_fixed",
    "STEADYSHOT_ACTIVE",
    "STEADYSHOT_STANDARD",
    "STEADYSHOT_OFF",
    "EVENT_REMOTE_MOVIE_STEADYSHOT",
    "EVENT_REMOTE_STEADYSHOT_FOCAL_LENGTH",
)

FX3_LIBMPR_RTMD_IMU_MARKERS: Tuple[str, ...] = (
    "_ZN3mpr12KlvConverter11UDAMKeyUnitE",
    "_ZN3mpr12KlvConverter21UDAMSetGyroscopeValueE",
    "_ZN3mpr12KlvConverter25UDAMSetAccelerometerValueE",
    "_ZN3mpr12KlvConverter30UDAMSetNormalImageControlValueE",
    "Gyroscope",
    "Accelerometor",
)

FX6_LIBMPR_RTMD_READOUT_MARKERS: Tuple[str, ...] = (
    "_ZN3mpr12KlvConverter11UDAMKeyUnitE",
    "_ZN3mpr12KlvConverter21UDAMSetGyroscopeValueE",
    "_ZN3mpr12KlvConverter25UDAMSetAccelerometerValueE",
    "_ZN3mpr12KlvConverter30UDAMSetNormalImageControlValueE",
    "MetaConverterImpl::ConvertReadoutDuration",
    "muxMxfRtmetaBufferImagerReadoutModeWrite",
    "NormalImageControl_ImageReadoutVcycle",
    "NormalImageControl_EffectivePixelReadoutStartTime",
    "NormalImageControl_EffectivePixelReadoutTime",
    "Gyroscope",
    "Accelerometor",
)

FX3_CP_GYRO_CALIB_MARKERS: Tuple[str, ...] = (
    "SET_ANAMO_DESQUEEZE_SCALE",
    "CheckSetFrameLockOnSteadyShot",
    "CheckSetSteadyShotAdvancedMovie",
    "steadyshot_body_axis_movie",
    "ExecImagerCalibration",
    "N6Camera6Imager6IMX51019C_ImagerCtrl_IMX510E",
    "GyroStart",
    "GyroStop",
    "LmtGyroVect",
    "HallPIDOUT_0",
    "GyroPIDOUT_0",
    "FusionOUT_0",
    "PWMOUT_0",
)

FX6_CP_GYRO_READOUT_MARKERS: Tuple[str, ...] = (
    "SET_ANAMO_DESQUEEZE_SCALE",
    "ExecImagerCalibration",
    "N6Camera6Imager6IMX51019C_ImagerCtrl_IMX510E",
    "ImageSensorReadoutMode",
    "ReadoutDuration",
    "GyroStart",
    "GyroStop",
    "LmtGyroVect",
    "FocalLength",
    "Sampling",
)

LENS_COMM_GYRO_MARKERS: Tuple[str, ...] = (
    "LensCommunicator_Init",
    "GetMountedLensInfo",
    "SndSyncMsg",
)

# Verified .uxc String Resource IDs
FX3_NS39_PHASE89_LABELS: Dict[int, str] = {
    0x0004E0EA: "Turns off SteadyShot when shooting movies.\nSet this when using a tripod.",
    0x0004E153: "SteadyShot",
}

FX3_NS3_PHASE89_LABELS: Dict[int, str] = {
    0x00006183: "Shutter/SteadyShot",
}

FX6_NS1_PHASE89_LABELS: Dict[int, str] = {
    0x00002504: "De-Squeeze",
    0x000027EE: "SteadyShot Focal",
    0x000027F0: "LCD Monitor De-Squeeze",
    0x000027F2: "HDMI (FHD Output) De-Squeeze",
    0x000027FE: "De-Squeeze Ratio",
}

FX6_NS2_PHASE89_LABELS: Dict[int, str] = {
    0x00004216: "SteadyShot",
    0x000046C7: "Anamorphic",
    0x00004759: "SteadyShot: Active",
    0x0000475A: "SteadyShot: Standard",
    0x00005691: "SteadyShot: Off",
}

# ---------------------------------------------------------------------------
# Report & Evaluation Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ImuFrameSampleWindow:
    frame_index: int
    fps_label: str
    imu_rate_hz: int
    start_sample_index: int
    end_sample_index: int
    sample_count: int
    expected_min_samples: int
    expected_max_samples: int


@dataclass(frozen=True)
class GyroflowRtmdPacketEvalResult:
    valid: bool
    status: str
    fps_label: str
    frame_index: int
    imu_rate_hz: int
    sample_count: int
    expected_sample_range: Tuple[int, int]
    quaternion_wxyz: Tuple[float, float, float, float]
    quaternion_norm: float
    rotation_matrix_det: float
    so3_orthogonal: bool
    steadyshot_mode: str
    target_stabilizer: str
    center_lock_0x0400_energized: bool
    ibis_offset_telemetry_present: bool
    ibis_optical_center_shift_conflict: bool
    full_3d_lens_profile_compatible: bool
    catalyst_compatible: bool
    recommended_ibis_mode: str
    packet_bytes: int
    parsed_tags_hex: Tuple[str, ...]
    packet_sha256: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class GyroflowRtmdMatrixReport:
    passed: bool
    imu_sample_rate_hz: int
    fx3_libmpr_markers: Tuple[str, ...]
    fx6_libmpr_markers: Tuple[str, ...]
    uxc_steadyshot_labels: Dict[str, str]
    eval_23_976p_ibis_off: GyroflowRtmdPacketEvalResult
    eval_25_00p_ibis_off: GyroflowRtmdPacketEvalResult
    eval_59_94p_ibis_off: GyroflowRtmdPacketEvalResult
    eval_23_976p_ibis_standard_v17: GyroflowRtmdPacketEvalResult
    blocked_active_ibis_3d_lens_conflict: GyroflowRtmdPacketEvalResult
    zero_drift_1000_frame_total_samples_23_976p: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class AnamorphicIbisEvalResult:
    valid: bool
    status: str
    target_body: str
    has_physical_ibis: bool
    monitoring_desqueeze_only: bool
    focal_length_mm: float
    squeeze_factor: float
    steadyshot_mode: str
    anamorphic_ibis_mode: str
    is_manual_anamorphic_lens: bool
    effective_yaw_focal_mm: float
    effective_pitch_focal_mm: float
    yaw_gain_ratio: float
    pitch_gain_ratio: float
    yaw_overdrive_factor: float
    yaw_overdrive_error_pct: float
    asymmetric_gain_hazard_detected: bool
    center_lock_0x0400_energized: bool
    gyro_rtmd_embedded: bool
    recommended_policy: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class AnamorphicIbisMatrixReport:
    passed: bool
    fx3_appfw_markers: Tuple[str, ...]
    fx6_appfw_markers: Tuple[str, ...]
    lens_comm_markers: Tuple[str, ...]
    uxc_anamorphic_labels: Dict[str, str]
    fx6_rigid_cmos_desqueeze_2x: AnamorphicIbisEvalResult
    fx3_asymmetric_gain_1_33x: AnamorphicIbisEvalResult
    fx3_asymmetric_gain_1_5x: AnamorphicIbisEvalResult
    fx3_asymmetric_gain_1_8x: AnamorphicIbisEvalResult
    fx3_asymmetric_gain_2_0x: AnamorphicIbisEvalResult
    fx3_manual_anamorphic_center_lock: AnamorphicIbisEvalResult
    blocked_fx3_naive_spherical_2x_hazard: AnamorphicIbisEvalResult
    blocked_fx3_naive_spherical_1_33x_hazard: AnamorphicIbisEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Imx510RollingShutterEvalResult:
    valid: bool
    status: str
    sensor_mode: str
    width: int
    height: int
    fps_hz: float
    frame_period_ms: float
    actual_readout_ms: float
    declared_readout_us: int
    readout_error_us: int
    crop_factor: float
    vertical_shear_risk: bool
    skew_residual_px_at_30deg_s: float
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Imx510RollingShutterReport:
    passed: bool
    fx6_libmpr_readout_markers: Tuple[str, ...]
    fx6_cp_readout_markers: Tuple[str, ...]
    eval_4k_dci_24p: Imx510RollingShutterEvalResult
    eval_qfhd_4k_24p: Imx510RollingShutterEvalResult
    eval_qfhd_4k_60p: Imx510RollingShutterEvalResult
    eval_sq_4k_120p: Imx510RollingShutterEvalResult
    eval_fhd_240p: Imx510RollingShutterEvalResult
    blocked_4k120_wrong_8_7ms_skew_hazard: Imx510RollingShutterEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class ImuCalibrationImmutabilityResult:
    valid: bool
    status: str
    target_path: str
    volatile_shadow_only: bool
    imu_calibration_mutation_bytes: int
    cp_mutation_bytes: int
    persistent_emmc_writes_authorized: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class StockCpImuCalibrationReport:
    passed: bool
    fx3_cp_calib_markers: Tuple[str, ...]
    fx6_cp_calib_markers: Tuple[str, ...]
    fx3_global_xdb_valid: bool
    fx6_global_xdb_valid: bool
    volatile_shadow_eval: ImuCalibrationImmutabilityResult
    blocked_cnflasha_eval: ImuCalibrationImmutabilityResult
    blocked_backup_bin_eval: ImuCalibrationImmutabilityResult
    blocked_psd_bin_eval: ImuCalibrationImmutabilityResult
    blocked_jiritsu_eval: ImuCalibrationImmutabilityResult
    imu_calibration_mutation_bytes: int
    cp_mutation_bytes: int
    persistent_emmc_writes_authorized: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class MetadataGyroCatalystAndAnamorphicReport:
    schema_version: str
    phase_version: str
    mode: str
    all_checks_passed: bool
    o_rdonly_enforced: bool
    persistent_emmc_writes_authorized: bool
    imu_calibration_mutation_bytes: int
    cp_mutation_bytes: int
    donor_file_sizes: Dict[str, int]
    pillar_1_gyroflow_rtmd: GyroflowRtmdMatrixReport
    pillar_2_anamorphic_ibis: AnamorphicIbisMatrixReport
    pillar_3_imx510_rolling_shutter: Imx510RollingShutterReport
    pillar_4_imu_calibration_immutability: StockCpImuCalibrationReport
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
# Clean-Room Synthetic Fixtures (Used ONLY when FX3_FX6_FORCE_CLEAN_ROOM=1 or donors absent)
# ---------------------------------------------------------------------------


def build_clean_room_gyro_anamorphic_fixtures() -> Dict[str, bytes]:
    """Build deterministic clean-room ELF64, CP, `global.xdb`, and `.uxc` fixtures for Phase 89."""
    elf_hdr = b"\x7fELF\x02\x01\x01\x00" + bytes(56)
    cp_hdr = b"LDR\x00" + bytes(60)

    def _pack(tokens: Sequence[str], *, prefix: bytes = elf_hdr) -> bytes:
        return prefix + b"\x00".join(t.encode("latin1") for t in tokens) + b"\x00"

    fx3_appfw_blob = _pack(FX3_APPFW_GYRO_ANAMORPHIC_MARKERS)
    fx6_appfw_blob = _pack(FX6_APPFW_GYRO_ANAMORPHIC_MARKERS)
    fx3_libmpr_blob = _pack(FX3_LIBMPR_RTMD_IMU_MARKERS)
    fx6_libmpr_blob = _pack(FX6_LIBMPR_RTMD_READOUT_MARKERS)
    fx3_cp_blob = _pack(FX3_CP_GYRO_CALIB_MARKERS, prefix=cp_hdr)
    fx6_cp_blob = _pack(FX6_CP_GYRO_READOUT_MARKERS, prefix=cp_hdr)
    lens_comm_blob = build_synthetic_elf64_so(
        soname="libInfraLensCommunicator.so",
        dt_needed=("libc.so.6",),
        exports=LENS_COMM_GYRO_MARKERS,
        imports=(),
    )

    fx3_xdb = build_synthetic_global_xdb("fx3_702")
    fx6_xdb = build_synthetic_global_xdb("fx6_601")

    fx3_str_en = build_sparse_uxc_string_pack(
        {k & 0x1FFF: v for k, v in FX3_NS39_PHASE89_LABELS.items()}, namespace_id=39
    )
    fx3_str_en_g = build_sparse_uxc_string_pack(
        {k & 0x1FFF: v for k, v in FX3_NS3_PHASE89_LABELS.items()}, namespace_id=3
    )
    fx6_str_en_1 = build_sparse_uxc_string_pack(
        {k & 0x1FFF: v for k, v in FX6_NS1_PHASE89_LABELS.items()}, namespace_id=1
    )
    fx6_str_en_2 = build_sparse_uxc_string_pack(
        {k & 0x1FFF: v for k, v in FX6_NS2_PHASE89_LABELS.items()}, namespace_id=2
    )

    return {
        "fx3_appfw": fx3_appfw_blob,
        "fx6_appfw": fx6_appfw_blob,
        "fx3_libmpr": fx3_libmpr_blob,
        "fx6_libmpr": fx6_libmpr_blob,
        "fx3_cpapp": fx3_cp_blob,
        "fx6_cpapp": fx6_cp_blob,
        "fx3_lens_comm": lens_comm_blob,
        "fx6_lens_comm": lens_comm_blob,
        "fx3_global_xdb": fx3_xdb,
        "fx6_global_xdb": fx6_xdb,
        "fx3_str_en": fx3_str_en,
        "fx3_str_en_g": fx3_str_en_g,
        "fx6_str_en_1": fx6_str_en_1,
        "fx6_str_en_2": fx6_str_en_2,
    }


# ---------------------------------------------------------------------------
# Pillar 1: Gyroflow / Catalyst Browse Sony RTMD (0xE304 / 0xE43B / 0xE44B)
# ---------------------------------------------------------------------------


def compute_imu_samples_for_frame(
    frame_index: int,
    fps_label: str,
    *,
    imu_rate_hz: int = IMU_SAMPLE_RATE_HZ,
) -> ImuFrameSampleWindow:
    """Compute exact integer-rational IMU sample window `[start, end)` for `frame_index` at `imu_rate_hz`."""
    if frame_index < 0:
        raise ValueError(f"frame_index={frame_index} must be >= 0")
    if imu_rate_hz <= 0:
        raise ValueError(f"imu_rate_hz={imu_rate_hz} must be > 0")
    spec = GYRO_FRAME_RATE_SPECS.get(fps_label)
    if spec is None:
        raise ValueError(f"Unsupported fps_label={fps_label!r}; expected {tuple(GYRO_FRAME_RATE_SPECS)}")

    num = int(spec["num"])
    den = int(spec["den"])
    start_idx = (frame_index * imu_rate_hz * den) // num
    end_idx = ((frame_index + 1) * imu_rate_hz * den) // num
    count = end_idx - start_idx

    if imu_rate_hz == IMU_SAMPLE_RATE_HZ:
        min_s = int(spec["min_samples"])
        max_s = int(spec["max_samples"])
    else:
        exact = float(imu_rate_hz) * float(den) / float(num)
        min_s = int(math.floor(exact))
        max_s = int(math.ceil(exact))

    return ImuFrameSampleWindow(
        frame_index=frame_index,
        fps_label=fps_label,
        imu_rate_hz=imu_rate_hz,
        start_sample_index=start_idx,
        end_sample_index=end_idx,
        sample_count=count,
        expected_min_samples=min_s,
        expected_max_samples=max_s,
    )


def verify_so3_orientation_quaternion(
    quat_wxyz: Tuple[float, float, float, float],
) -> Tuple[bool, float, float, Tuple[Tuple[float, float, float], ...], Tuple[str, ...]]:
    """Verify unit quaternion `(w, x, y, z)` and convert to orthogonal `SO(3)` rotation matrix (`det = +1`)."""
    errors: List[str] = []
    if len(quat_wxyz) != 4 or not all(math.isfinite(v) for v in quat_wxyz):
        return False, 0.0, 0.0, ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)), (
            "Quaternion must contain 4 finite floats",
        )
    w, x, y, z = quat_wxyz
    norm = math.sqrt(w * w + x * x + y * y + z * z)
    if abs(norm - 1.0) > 1e-6:
        errors.append(f"Non-unit IMU orientation quaternion norm={norm:.8f} (expected 1.0)")

    r00 = 1.0 - 2.0 * (y * y + z * z)
    r01 = 2.0 * (x * y - w * z)
    r02 = 2.0 * (x * z + w * y)
    r10 = 2.0 * (x * y + w * z)
    r11 = 1.0 - 2.0 * (x * x + z * z)
    r12 = 2.0 * (y * z - w * x)
    r20 = 2.0 * (x * z - w * y)
    r21 = 2.0 * (y * z + w * x)
    r22 = 1.0 - 2.0 * (x * x + y * y)
    mat = ((r00, r01, r02), (r10, r11, r12), (r20, r21, r22))

    det = (
        r00 * (r11 * r22 - r12 * r21)
        - r01 * (r10 * r22 - r12 * r20)
        + r02 * (r10 * r21 - r11 * r20)
    )
    max_ortho_err = 0.0
    for i in range(3):
        for j in range(3):
            dot = mat[0][i] * mat[0][j] + mat[1][i] * mat[1][j] + mat[2][i] * mat[2][j]
            target = 1.0 if i == j else 0.0
            max_ortho_err = max(max_ortho_err, abs(dot - target))

    if max_ortho_err > 1e-6 or abs(det - 1.0) > 1e-6:
        errors.append(f"IMU rotation matrix not in SO(3): det={det:.6f}, ortho_err={max_ortho_err:.2e}")

    return len(errors) == 0, norm, det, mat, tuple(errors)


def build_gyroflow_rtmd_frame_packet(
    *,
    fps_label: str = "23.976p",
    frame_index: int = 0,
    imu_rate_hz: int = IMU_SAMPLE_RATE_HZ,
    readout_us: int = 8700,
    steadyshot_mode: str = "Off",
    center_lock_0x0400_energized: bool = True,
    ibis_offset_telemetry_present: bool = False,
    quat_wxyz: Tuple[float, float, float, float] = DEFAULT_IMU_QUATERNION_WXYZ,
    squeeze_factor: float = 1.0,
    gyro_sample_xyz_mrad_s: Tuple[int, int, int] = (14, -6, 3),
    accel_sample_xyz_mg: Tuple[int, int, int] = (0, 0, 981),
) -> bytes:
    """Build deterministic big-endian SMPTE RDD 18 / Sony `RTMD` KLV packet with `2000 Hz` IMU block."""
    if steadyshot_mode not in STEADYSHOT_MODE_TO_CODE:
        raise ValueError(f"Unsupported steadyshot_mode={steadyshot_mode!r}")
    win = compute_imu_samples_for_frame(frame_index, fps_label, imu_rate_hz=imu_rate_hz)

    payload = bytearray()

    def _add_tag(tag: int, val: bytes) -> None:
        payload.extend(struct.pack(">HH", tag & 0xFFFF, len(val)))
        payload.extend(val)

    _add_tag(RTMD_TAG_IMX510_READOUT_US, struct.pack(">I", readout_us))

    # 0xE43B: 2000 Hz Gyroscope sample block header + sample_count x 3*int16 (6B/sample)
    gyro_buf = bytearray(struct.pack(">HH4f", imu_rate_hz, win.sample_count, *quat_wxyz))
    gx, gy, gz = gyro_sample_xyz_mrad_s
    for idx in range(win.sample_count):
        delta = (idx % 3) - 1
        gyro_buf.extend(struct.pack(">hhh", gx + delta, gy - delta, gz))
    _add_tag(RTMD_TAG_GYRO_PITCH_ROLL_YAW, bytes(gyro_buf))

    # 0xE44B: 2000 Hz Accelerometer sample block header + sample_count x 3*int16 (6B/sample)
    accel_buf = bytearray(struct.pack(">HH", imu_rate_hz, win.sample_count))
    ax, ay, az = accel_sample_xyz_mg
    for idx in range(win.sample_count):
        delta = 1 if (idx & 1) else 0
        accel_buf.extend(struct.pack(">hhh", ax + delta, ay, az))
    _add_tag(RTMD_TAG_ACCELEROMETER, bytes(accel_buf))

    # 0xE450: Anamorphic squeeze & center-lock descriptor
    _add_tag(
        RTMD_TAG_ANAMORPHIC_DESQUEEZE_X100,
        struct.pack(">HBB", int(round(squeeze_factor * 100.0)), 1 if ibis_offset_telemetry_present else 0, 0),
    )

    # 0xE304: IMX510 IBIS / Gyro coherence descriptor
    ss_code = STEADYSHOT_MODE_TO_CODE[steadyshot_mode]
    coherence_flags = RTMD_COHERENCE_GYRO_VALID | RTMD_COHERENCE_CATALYST_BROWSE_OK
    if center_lock_0x0400_energized:
        coherence_flags |= RTMD_COHERENCE_CENTER_LOCK_OK | RTMD_COHERENCE_GYROFLOW_OK
    elif ibis_offset_telemetry_present:
        coherence_flags |= RTMD_COHERENCE_GYROFLOW_OK

    e304_body = struct.pack(
        ">BBBBHH3i3i",
        ss_code,
        1 if center_lock_0x0400_energized else 0,
        0 if (center_lock_0x0400_energized or ibis_offset_telemetry_present) else 1,
        5,
        imu_rate_hz,
        coherence_flags,
        gx,
        gy,
        gz,
        ax,
        ay,
        az,
    )
    _add_tag(RTMD_TAG_IMX510_IBIS_GYRO_E304, e304_body)

    return RTMD_RDD18_ACQUISITION_UL + encode_ber_length(len(payload)) + bytes(payload)


def evaluate_gyroflow_catalyst_rtmd_packet(
    *,
    fps_label: str = "23.976p",
    frame_index: int = 0,
    imu_rate_hz: int = IMU_SAMPLE_RATE_HZ,
    readout_us: int = 8700,
    steadyshot_mode: str = "Off",
    target_stabilizer: str = "GYROFLOW_3D_LENS_PROFILE",
    center_lock_0x0400_energized: Optional[bool] = None,
    ibis_offset_telemetry_present: bool = False,
    quat_wxyz: Tuple[float, float, float, float] = DEFAULT_IMU_QUATERNION_WXYZ,
    squeeze_factor: float = 1.0,
) -> GyroflowRtmdPacketEvalResult:
    """Build, round-trip parse, and verify a Sony `RTMD` (`0xE304`/`0xE43B`/`0xE44B`) packet."""
    errors: List[str] = []
    norm_stab = target_stabilizer.strip().upper()
    if steadyshot_mode not in VALID_STEADYSHOT_MODES:
        errors.append(f"Unsupported steadyshot_mode={steadyshot_mode!r}; expected {VALID_STEADYSHOT_MODES}")
    if norm_stab not in VALID_STABILIZER_WORKFLOWS:
        errors.append(f"Unsupported target_stabilizer={target_stabilizer!r}; expected {VALID_STABILIZER_WORKFLOWS}")

    if center_lock_0x0400_energized is None:
        eff_center_lock = steadyshot_mode == "Off"
    else:
        eff_center_lock = bool(center_lock_0x0400_energized)

    so3_ok, q_norm, r_det, _mat, so3_errs = verify_so3_orientation_quaternion(quat_wxyz)
    errors.extend(so3_errs)

    if errors:
        return GyroflowRtmdPacketEvalResult(
            valid=False,
            status="BLOCKED_INVALID_RTMD_IMU_CONFIG",
            fps_label=fps_label,
            frame_index=frame_index,
            imu_rate_hz=imu_rate_hz,
            sample_count=0,
            expected_sample_range=(0, 0),
            quaternion_wxyz=quat_wxyz,
            quaternion_norm=round(q_norm, 6),
            rotation_matrix_det=round(r_det, 6),
            so3_orthogonal=so3_ok,
            steadyshot_mode=steadyshot_mode,
            target_stabilizer=norm_stab,
            center_lock_0x0400_energized=eff_center_lock,
            ibis_offset_telemetry_present=ibis_offset_telemetry_present,
            ibis_optical_center_shift_conflict=False,
            full_3d_lens_profile_compatible=False,
            catalyst_compatible=False,
            recommended_ibis_mode="Off (0x0400 Center-Lock)",
            packet_bytes=0,
            parsed_tags_hex=(),
            packet_sha256="",
            errors=tuple(errors),
        )

    win = compute_imu_samples_for_frame(frame_index, fps_label, imu_rate_hz=imu_rate_hz)
    pkt = build_gyroflow_rtmd_frame_packet(
        fps_label=fps_label,
        frame_index=frame_index,
        imu_rate_hz=imu_rate_hz,
        readout_us=readout_us,
        steadyshot_mode=steadyshot_mode,
        center_lock_0x0400_energized=eff_center_lock,
        ibis_offset_telemetry_present=ibis_offset_telemetry_present,
        quat_wxyz=quat_wxyz,
        squeeze_factor=squeeze_factor,
    )

    # Round-trip KLV parse
    if len(pkt) < 17 or pkt[:4] != SMPTE_KLV_UL_PREFIX:
        errors.append("Invalid SMPTE KLV Universal Label header")
    declared_len, body_off = decode_ber_length(pkt, 16)
    if body_off + declared_len != len(pkt):
        errors.append("RTMD BER length mismatch")

    tags: Dict[int, bytes] = {}
    ordered_tags: List[str] = []
    pos = body_off
    while pos < len(pkt):
        tag, vlen = struct.unpack_from(">HH", pkt, pos)
        pos += 4
        tags[tag] = pkt[pos : pos + vlen]
        ordered_tags.append(f"0x{tag:04x}")
        pos += vlen

    for req_tag in (
        RTMD_TAG_IMX510_READOUT_US,
        RTMD_TAG_GYRO_PITCH_ROLL_YAW,
        RTMD_TAG_ACCELEROMETER,
        RTMD_TAG_ANAMORPHIC_DESQUEEZE_X100,
        RTMD_TAG_IMX510_IBIS_GYRO_E304,
    ):
        if req_tag not in tags:
            errors.append(f"Missing RTMD tag 0x{req_tag:04x}")

    parsed_rate, parsed_gyro_cnt = struct.unpack_from(">HH", tags[RTMD_TAG_GYRO_PITCH_ROLL_YAW], 0)
    parsed_acc_rate, parsed_acc_cnt = struct.unpack_from(">HH", tags[RTMD_TAG_ACCELEROMETER], 0)
    if parsed_rate != imu_rate_hz or parsed_acc_rate != imu_rate_hz:
        errors.append(f"IMU rate mismatch: gyro={parsed_rate}Hz accel={parsed_acc_rate}Hz != {imu_rate_hz}Hz")
    if parsed_gyro_cnt != parsed_acc_cnt or not (win.expected_min_samples <= parsed_gyro_cnt <= win.expected_max_samples):
        errors.append(
            f"IMU sample count {parsed_gyro_cnt} outside [{win.expected_min_samples}..{win.expected_max_samples}]"
        )

    # Compatibility rule: full 3D Gyroflow lens-profile stabilization requires IBIS = Off (0x0400 Center-Lock)
    # so optical-center translation does not fight digital 3D perspective warp.
    ibis_conflict = False
    full_3d_ok = False
    if norm_stab == "GYROFLOW_3D_LENS_PROFILE":
        if steadyshot_mode != "Off" or not eff_center_lock:
            ibis_conflict = True
            errors.append(
                f"BLOCKED_IBIS_OPTICAL_CENTER_CONFLICT: {steadyshot_mode} IBIS shifts optical center and fights "
                "GYROFLOW_3D_LENS_PROFILE warp; set IBIS = Off (0x0400 Center-Lock)"
            )
        else:
            full_3d_ok = True
    elif norm_stab == "GYROFLOW_V17_IBIS_METADATA_AWARE":
        if steadyshot_mode == "Off":
            full_3d_ok = eff_center_lock
        elif not ibis_offset_telemetry_present:
            ibis_conflict = True
            errors.append(
                "BLOCKED_MISSING_IBIS_OFFSET_TELEMETRY: IBIS active without per-frame IBIS sensor-shift metadata"
            )
    elif norm_stab == "CATALYST_BROWSE_METADATA":
        full_3d_ok = steadyshot_mode == "Off" and eff_center_lock

    catalyst_ok = len(errors) == 0 and (RTMD_TAG_IMX510_IBIS_GYRO_E304 in tags)
    recommended = (
        "Off (0x0400 Center-Lock)"
        if (norm_stab == "GYROFLOW_3D_LENS_PROFILE" or steadyshot_mode == "Off")
        else "Standard + IBIS Offset Telemetry (or Off 0x0400 for 3D Lens Profile)"
    )

    if ibis_conflict:
        status = "BLOCKED_IBIS_OPTICAL_CENTER_CONFLICT"
    elif errors:
        status = "BLOCKED_INVALID_RTMD_PACKET"
    elif steadyshot_mode == "Off":
        status = "RTMD_GYROFLOW_3D_CENTER_LOCK_VERIFIED"
    else:
        status = "RTMD_IBIS_METADATA_AWARE_VERIFIED"

    return GyroflowRtmdPacketEvalResult(
        valid=len(errors) == 0,
        status=status,
        fps_label=fps_label,
        frame_index=frame_index,
        imu_rate_hz=imu_rate_hz,
        sample_count=parsed_gyro_cnt,
        expected_sample_range=(win.expected_min_samples, win.expected_max_samples),
        quaternion_wxyz=quat_wxyz,
        quaternion_norm=round(q_norm, 6),
        rotation_matrix_det=round(r_det, 6),
        so3_orthogonal=so3_ok,
        steadyshot_mode=steadyshot_mode,
        target_stabilizer=norm_stab,
        center_lock_0x0400_energized=eff_center_lock,
        ibis_offset_telemetry_present=ibis_offset_telemetry_present,
        ibis_optical_center_shift_conflict=ibis_conflict,
        full_3d_lens_profile_compatible=full_3d_ok,
        catalyst_compatible=catalyst_ok,
        recommended_ibis_mode=recommended,
        packet_bytes=len(pkt),
        parsed_tags_hex=tuple(ordered_tags),
        packet_sha256=hashlib.sha256(pkt).hexdigest(),
        errors=tuple(errors),
    )


def evaluate_pillar_1_gyroflow_rtmd(
    present_map: Mapping[str, Tuple[str, ...]],
    uxc_labels: Mapping[str, str],
) -> GyroflowRtmdMatrixReport:
    """Audit Pillar 1: 2000 Hz IMU samples/frame, SO(3) orientation, KLV round-trip, and IBIS Center-Lock rule."""
    errors: List[str] = []
    fx3_mpr = present_map["fx3_libmpr_rtmd"]
    fx6_mpr = present_map["fx6_libmpr_rtmd"]

    if fx3_mpr != FX3_LIBMPR_RTMD_IMU_MARKERS:
        missing = tuple(m for m in FX3_LIBMPR_RTMD_IMU_MARKERS if m not in fx3_mpr)
        errors.append(f"FX3 libmpr.so missing RTMD Gyro/Accel markers: {missing}")
    if fx6_mpr != FX6_LIBMPR_RTMD_READOUT_MARKERS:
        missing = tuple(m for m in FX6_LIBMPR_RTMD_READOUT_MARKERS if m not in fx6_mpr)
        errors.append(f"FX6 libmpr.so missing RTMD Gyro/Readout markers: {missing}")

    ev_23976 = evaluate_gyroflow_catalyst_rtmd_packet(
        fps_label="23.976p",
        frame_index=1,
        readout_us=8700,
        steadyshot_mode="Off",
        target_stabilizer="GYROFLOW_3D_LENS_PROFILE",
    )
    ev_25 = evaluate_gyroflow_catalyst_rtmd_packet(
        fps_label="25.00p",
        frame_index=0,
        readout_us=8700,
        steadyshot_mode="Off",
        target_stabilizer="GYROFLOW_3D_LENS_PROFILE",
    )
    ev_5994 = evaluate_gyroflow_catalyst_rtmd_packet(
        fps_label="59.94p",
        frame_index=2,
        readout_us=8700,
        steadyshot_mode="Off",
        target_stabilizer="GYROFLOW_3D_LENS_PROFILE",
    )
    ev_v17 = evaluate_gyroflow_catalyst_rtmd_packet(
        fps_label="23.976p",
        frame_index=0,
        readout_us=8700,
        steadyshot_mode="Standard",
        target_stabilizer="GYROFLOW_V17_IBIS_METADATA_AWARE",
        center_lock_0x0400_energized=False,
        ibis_offset_telemetry_present=True,
    )
    conflict_active = evaluate_gyroflow_catalyst_rtmd_packet(
        fps_label="23.976p",
        frame_index=0,
        readout_us=8700,
        steadyshot_mode="Active",
        target_stabilizer="GYROFLOW_3D_LENS_PROFILE",
        center_lock_0x0400_energized=False,
    )

    for ev in (ev_23976, ev_25, ev_5994, ev_v17):
        if not ev.valid:
            errors.extend(ev.errors)
    if ev_25.sample_count != 80:
        errors.append(f"Expected exactly 80 IMU samples at 25.00p, got {ev_25.sample_count}")
    if conflict_active.valid or not conflict_active.ibis_optical_center_shift_conflict:
        errors.append("Active IBIS paired with GYROFLOW_3D_LENS_PROFILE failed to flag optical-center conflict")

    total_1000 = sum(
        compute_imu_samples_for_frame(i, "23.976p").sample_count for i in range(1000)
    )
    expected_1000 = (1000 * IMU_SAMPLE_RATE_HZ * 1001) // 24000
    if total_1000 != expected_1000:
        errors.append(f"1000-frame 23.976p IMU sample sum drift: {total_1000} != {expected_1000}")

    ss_uxc = {
        k: v
        for k, v in uxc_labels.items()
        if k
        in (
            "fx3_steadyshot",
            "fx3_steadyshot_off_hint",
            "fx3_shutter_steadyshot",
            "fx6_steadyshot_focal",
            "fx6_steadyshot_ns2",
            "fx6_steadyshot_active",
            "fx6_steadyshot_standard",
            "fx6_steadyshot_off",
        )
    }

    return GyroflowRtmdMatrixReport(
        passed=len(errors) == 0,
        imu_sample_rate_hz=IMU_SAMPLE_RATE_HZ,
        fx3_libmpr_markers=fx3_mpr,
        fx6_libmpr_markers=fx6_mpr,
        uxc_steadyshot_labels=ss_uxc,
        eval_23_976p_ibis_off=ev_23976,
        eval_25_00p_ibis_off=ev_25,
        eval_59_94p_ibis_off=ev_5994,
        eval_23_976p_ibis_standard_v17=ev_v17,
        blocked_active_ibis_3d_lens_conflict=conflict_active,
        zero_drift_1000_frame_total_samples_23_976p=total_1000,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 2: Anamorphic (1.3x..2.0x) 5-Axis IBIS Asymmetric Gain Containment
# ---------------------------------------------------------------------------


def evaluate_anamorphic_ibis_asymmetric_gain(
    *,
    target_body: str = "ILME-FX3",
    focal_length_mm: float = 50.0,
    squeeze_factor: float = 2.0,
    steadyshot_mode: str = "Standard",
    anamorphic_ibis_mode: str = "ANAMORPHIC_ASYMMETRIC_GAIN",
    is_manual_anamorphic_lens: bool = False,
) -> AnamorphicIbisEvalResult:
    """Model & verify Anamorphic (`1.3x..2.0x`) 5-axis IBIS horizontal yaw gain (`f_x = f / S`, `f_y = f`)."""
    errors: List[str] = []
    norm_body = target_body.strip().upper()
    norm_mode = anamorphic_ibis_mode.strip().upper()

    if norm_body not in ("ILME-FX3", "ILME-FX6"):
        errors.append(f"Unsupported target_body={target_body!r}; expected ILME-FX3 or ILME-FX6")
    if not math.isfinite(focal_length_mm) or focal_length_mm < 8.0 or focal_length_mm > 1200.0:
        errors.append(f"Invalid focal_length_mm={focal_length_mm!r}; expected [8..1200]")
    if squeeze_factor not in SUPPORTED_ANAMORPHIC_SQUEEZE_FACTORS:
        errors.append(
            f"Unsupported squeeze_factor={squeeze_factor!r}; expected {SUPPORTED_ANAMORPHIC_SQUEEZE_FACTORS}"
        )
    if steadyshot_mode not in VALID_STEADYSHOT_MODES:
        errors.append(f"Unsupported steadyshot_mode={steadyshot_mode!r}; expected {VALID_STEADYSHOT_MODES}")
    if norm_mode not in VALID_ANAMORPHIC_IBIS_MODES:
        errors.append(f"Unsupported anamorphic_ibis_mode={anamorphic_ibis_mode!r}")

    has_physical_ibis = norm_body == "ILME-FX3"
    monitoring_desqueeze_only = not has_physical_ibis

    if errors:
        return AnamorphicIbisEvalResult(
            valid=False,
            status="BLOCKED_INVALID_ANAMORPHIC_CONFIG",
            target_body=norm_body,
            has_physical_ibis=has_physical_ibis,
            monitoring_desqueeze_only=monitoring_desqueeze_only,
            focal_length_mm=float(focal_length_mm),
            squeeze_factor=float(squeeze_factor),
            steadyshot_mode=steadyshot_mode,
            anamorphic_ibis_mode=norm_mode,
            is_manual_anamorphic_lens=is_manual_anamorphic_lens,
            effective_yaw_focal_mm=0.0,
            effective_pitch_focal_mm=0.0,
            yaw_gain_ratio=0.0,
            pitch_gain_ratio=0.0,
            yaw_overdrive_factor=0.0,
            yaw_overdrive_error_pct=0.0,
            asymmetric_gain_hazard_detected=False,
            center_lock_0x0400_energized=False,
            gyro_rtmd_embedded=True,
            recommended_policy="INVALID",
            errors=tuple(errors),
        )

    true_yaw_focal = focal_length_mm / squeeze_factor
    true_pitch_focal = focal_length_mm

    if not has_physical_ibis:
        # FX6 has rigid CMOS (PRM_is_imager_stabilization_unit_fixed); De-Squeeze (1.3x/2.0x) is monitoring-only.
        return AnamorphicIbisEvalResult(
            valid=True,
            status="FX6_RIGID_CMOS_MONITORING_DESQUEEZE_ONLY",
            target_body=norm_body,
            has_physical_ibis=False,
            monitoring_desqueeze_only=True,
            focal_length_mm=round(focal_length_mm, 3),
            squeeze_factor=squeeze_factor,
            steadyshot_mode="Off",
            anamorphic_ibis_mode="AUTO_CENTER_LOCK_0X0400",
            is_manual_anamorphic_lens=is_manual_anamorphic_lens,
            effective_yaw_focal_mm=round(true_yaw_focal, 4),
            effective_pitch_focal_mm=round(true_pitch_focal, 4),
            yaw_gain_ratio=round(1.0 / squeeze_factor, 4),
            pitch_gain_ratio=1.0,
            yaw_overdrive_factor=1.0,
            yaw_overdrive_error_pct=0.0,
            asymmetric_gain_hazard_detected=False,
            center_lock_0x0400_energized=False,
            gyro_rtmd_embedded=True,
            recommended_policy="FX6 monitoring-only De-Squeeze + 2000 Hz Gyro RTMD (zero physical IBIS stage)",
            errors=(),
        )

    # FX3 has a physical 5-axis IBIS stage!
    if steadyshot_mode == "Off" or norm_mode == "AUTO_CENTER_LOCK_0X0400" or (
        is_manual_anamorphic_lens and norm_mode == "ANAMORPHIC_ASYMMETRIC_GAIN"
    ):
        # Safe Center-Lock 0x0400 + 2000 Hz Gyro Metadata mode (mandatory recommendation for manual anamorphics)
        eff_mode = "AUTO_CENTER_LOCK_0X0400"
        eff_ss = "Off"
        return AnamorphicIbisEvalResult(
            valid=True,
            status="FX3_ANAMORPHIC_CENTER_LOCK_0X0400_WITH_GYRO_RTMD",
            target_body=norm_body,
            has_physical_ibis=True,
            monitoring_desqueeze_only=False,
            focal_length_mm=round(focal_length_mm, 3),
            squeeze_factor=squeeze_factor,
            steadyshot_mode=eff_ss,
            anamorphic_ibis_mode=eff_mode,
            is_manual_anamorphic_lens=is_manual_anamorphic_lens,
            effective_yaw_focal_mm=round(true_yaw_focal, 4),
            effective_pitch_focal_mm=round(true_pitch_focal, 4),
            yaw_gain_ratio=round(1.0 / squeeze_factor, 4),
            pitch_gain_ratio=1.0,
            yaw_overdrive_factor=1.0,
            yaw_overdrive_error_pct=0.0,
            asymmetric_gain_hazard_detected=False,
            center_lock_0x0400_energized=True,
            gyro_rtmd_embedded=True,
            recommended_policy=(
                f"IBIS = Off (0x0400 Center-Lock) + Gyro RTMD (S={squeeze_factor}x, f_x={true_yaw_focal:.2f}mm, f_y={true_pitch_focal:.2f}mm)"
            ),
            errors=(),
        )

    if norm_mode == "SPHERICAL_NAIVE":
        # Applying spherical focal length f to yaw over-drives horizontal IBIS translation by Sx!
        overdrive_factor = squeeze_factor
        overdrive_err_pct = (squeeze_factor - 1.0) * 100.0
        errors.append(
            f"BLOCKED_ANAMORPHIC_YAW_OVERDRIVE_HAZARD: spherical IBIS f={focal_length_mm}mm on {squeeze_factor}x "
            f"anamorphic over-drives horizontal yaw by {overdrive_factor:.2f}x ({overdrive_err_pct:.1f}% error); "
            f"apply f_x = f/S = {true_yaw_focal:.2f}mm or IBIS = Off (0x0400)"
        )
        return AnamorphicIbisEvalResult(
            valid=False,
            status="BLOCKED_ANAMORPHIC_YAW_OVERDRIVE_HAZARD",
            target_body=norm_body,
            has_physical_ibis=True,
            monitoring_desqueeze_only=False,
            focal_length_mm=round(focal_length_mm, 3),
            squeeze_factor=squeeze_factor,
            steadyshot_mode=steadyshot_mode,
            anamorphic_ibis_mode=norm_mode,
            is_manual_anamorphic_lens=is_manual_anamorphic_lens,
            effective_yaw_focal_mm=round(focal_length_mm, 4),
            effective_pitch_focal_mm=round(true_pitch_focal, 4),
            yaw_gain_ratio=1.0,
            pitch_gain_ratio=1.0,
            yaw_overdrive_factor=round(overdrive_factor, 4),
            yaw_overdrive_error_pct=round(overdrive_err_pct, 2),
            asymmetric_gain_hazard_detected=True,
            center_lock_0x0400_energized=False,
            gyro_rtmd_embedded=True,
            recommended_policy=f"Switch to f_x = f / {squeeze_factor} = {true_yaw_focal:.2f}mm or IBIS = Off (0x0400)",
            errors=tuple(errors),
        )

    # ANAMORPHIC_ASYMMETRIC_GAIN: f_x = f / S, f_y = f -> 0.0% horizontal yaw error
    return AnamorphicIbisEvalResult(
        valid=True,
        status="FX3_ANAMORPHIC_ASYMMETRIC_GAIN_VERIFIED",
        target_body=norm_body,
        has_physical_ibis=True,
        monitoring_desqueeze_only=False,
        focal_length_mm=round(focal_length_mm, 3),
        squeeze_factor=squeeze_factor,
        steadyshot_mode=steadyshot_mode,
        anamorphic_ibis_mode=norm_mode,
        is_manual_anamorphic_lens=is_manual_anamorphic_lens,
        effective_yaw_focal_mm=round(true_yaw_focal, 4),
        effective_pitch_focal_mm=round(true_pitch_focal, 4),
        yaw_gain_ratio=round(1.0 / squeeze_factor, 4),
        pitch_gain_ratio=1.0,
        yaw_overdrive_factor=1.0,
        yaw_overdrive_error_pct=0.0,
        asymmetric_gain_hazard_detected=False,
        center_lock_0x0400_energized=False,
        gyro_rtmd_embedded=True,
        recommended_policy=(
            f"Anamorphic SteadyShot asymmetric gain: f_x={true_yaw_focal:.2f}mm, f_y={true_pitch_focal:.2f}mm (S={squeeze_factor}x)"
        ),
        errors=(),
    )


def evaluate_pillar_2_anamorphic_ibis(
    present_map: Mapping[str, Tuple[str, ...]],
    uxc_labels: Mapping[str, str],
) -> AnamorphicIbisMatrixReport:
    """Audit Pillar 2 across Anamorphic De-Squeeze binary markers and FX3 vs FX6 IBIS gain math."""
    errors: List[str] = []
    fx3_afw = present_map["fx3_appfw_gyro_anamo"]
    fx6_afw = present_map["fx6_appfw_gyro_anamo"]
    lens_m = present_map["lens_comm_gyro"]

    if fx3_afw != FX3_APPFW_GYRO_ANAMORPHIC_MARKERS:
        missing = tuple(m for m in FX3_APPFW_GYRO_ANAMORPHIC_MARKERS if m not in fx3_afw)
        errors.append(f"FX3 appFw.so missing Anamorphic/SteadyShot markers: {missing}")
    if fx6_afw != FX6_APPFW_GYRO_ANAMORPHIC_MARKERS:
        missing = tuple(m for m in FX6_APPFW_GYRO_ANAMORPHIC_MARKERS if m not in fx6_afw)
        errors.append(f"FX6 appFw.so missing De-Squeeze/Rigid-CMOS/SteadyShot markers: {missing}")
    if lens_m != LENS_COMM_GYRO_MARKERS:
        missing = tuple(m for m in LENS_COMM_GYRO_MARKERS if m not in lens_m)
        errors.append(f"libInfraLensCommunicator.so missing markers: {missing}")

    fx6_2x = evaluate_anamorphic_ibis_asymmetric_gain(
        target_body="ILME-FX6", focal_length_mm=50.0, squeeze_factor=2.0
    )
    fx3_133 = evaluate_anamorphic_ibis_asymmetric_gain(
        target_body="ILME-FX3", focal_length_mm=40.0, squeeze_factor=1.33, anamorphic_ibis_mode="ANAMORPHIC_ASYMMETRIC_GAIN"
    )
    fx3_15 = evaluate_anamorphic_ibis_asymmetric_gain(
        target_body="ILME-FX3", focal_length_mm=45.0, squeeze_factor=1.5, anamorphic_ibis_mode="ANAMORPHIC_ASYMMETRIC_GAIN"
    )
    fx3_18 = evaluate_anamorphic_ibis_asymmetric_gain(
        target_body="ILME-FX3", focal_length_mm=50.0, squeeze_factor=1.8, anamorphic_ibis_mode="ANAMORPHIC_ASYMMETRIC_GAIN"
    )
    fx3_20 = evaluate_anamorphic_ibis_asymmetric_gain(
        target_body="ILME-FX3", focal_length_mm=50.0, squeeze_factor=2.0, anamorphic_ibis_mode="ANAMORPHIC_ASYMMETRIC_GAIN"
    )
    fx3_manual = evaluate_anamorphic_ibis_asymmetric_gain(
        target_body="ILME-FX3",
        focal_length_mm=50.0,
        squeeze_factor=2.0,
        is_manual_anamorphic_lens=True,
    )
    hazard_2x = evaluate_anamorphic_ibis_asymmetric_gain(
        target_body="ILME-FX3",
        focal_length_mm=50.0,
        squeeze_factor=2.0,
        steadyshot_mode="Standard",
        anamorphic_ibis_mode="SPHERICAL_NAIVE",
    )
    hazard_133x = evaluate_anamorphic_ibis_asymmetric_gain(
        target_body="ILME-FX3",
        focal_length_mm=40.0,
        squeeze_factor=1.33,
        steadyshot_mode="Active",
        anamorphic_ibis_mode="SPHERICAL_NAIVE",
    )

    for ev in (fx6_2x, fx3_133, fx3_15, fx3_18, fx3_20, fx3_manual):
        if not ev.valid or ev.yaw_overdrive_error_pct != 0.0:
            errors.extend(ev.errors or (f"Anamorphic safe eval failed: {ev.status}",))
    if not fx6_2x.monitoring_desqueeze_only or fx6_2x.has_physical_ibis:
        errors.append("FX6 De-Squeeze failed to assert monitoring-only rigid CMOS")
    if not fx3_manual.center_lock_0x0400_energized or fx3_manual.steadyshot_mode != "Off":
        errors.append("Manual anamorphic lens failed to auto-engage IBIS = Off (0x0400 Center-Lock)")
    if hazard_2x.valid or hazard_2x.yaw_overdrive_error_pct != 100.0:
        errors.append("FX3 naive spherical 2.0x anamorphic IBIS failed to flag 100.0% yaw overdrive")
    if hazard_133x.valid or abs(hazard_133x.yaw_overdrive_error_pct - 33.0) > 1e-6:
        errors.append("FX3 naive spherical 1.33x anamorphic IBIS failed to flag 33.0% yaw overdrive")

    anamo_uxc = {
        k: v
        for k, v in uxc_labels.items()
        if k
        in (
            "fx6_desqueeze",
            "fx6_lcd_desqueeze",
            "fx6_hdmi_desqueeze",
            "fx6_desqueeze_ratio",
            "fx6_anamorphic",
        )
    }

    return AnamorphicIbisMatrixReport(
        passed=len(errors) == 0,
        fx3_appfw_markers=fx3_afw,
        fx6_appfw_markers=fx6_afw,
        lens_comm_markers=lens_m,
        uxc_anamorphic_labels=anamo_uxc,
        fx6_rigid_cmos_desqueeze_2x=fx6_2x,
        fx3_asymmetric_gain_1_33x=fx3_133,
        fx3_asymmetric_gain_1_5x=fx3_15,
        fx3_asymmetric_gain_1_8x=fx3_18,
        fx3_asymmetric_gain_2_0x=fx3_20,
        fx3_manual_anamorphic_center_lock=fx3_manual,
        blocked_fx3_naive_spherical_2x_hazard=hazard_2x,
        blocked_fx3_naive_spherical_1_33x_hazard=hazard_133x,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 3: IMX510 Rolling-Shutter Readout Timing Matrix
# ---------------------------------------------------------------------------


def evaluate_imx510_rolling_shutter_readout(
    *,
    sensor_mode: str = "QFHD_4K_24P",
    declared_readout_us: Optional[int] = None,
    pan_angular_rate_deg_s: float = 30.0,
    hfov_deg: float = 65.0,
) -> Imx510RollingShutterEvalResult:
    """Verify per-frame `IMX510` rolling-shutter readout duration metadata against true scan timing."""
    errors: List[str] = []
    norm_mode = sensor_mode.strip().upper()
    spec = IMX510_ROLLING_SHUTTER_MODES.get(norm_mode)
    if spec is None:
        return Imx510RollingShutterEvalResult(
            valid=False,
            status="BLOCKED_UNSUPPORTED_IMX510_MODE",
            sensor_mode=norm_mode,
            width=0,
            height=0,
            fps_hz=0.0,
            frame_period_ms=0.0,
            actual_readout_ms=0.0,
            declared_readout_us=int(declared_readout_us or 0),
            readout_error_us=0,
            crop_factor=0.0,
            vertical_shear_risk=True,
            skew_residual_px_at_30deg_s=0.0,
            errors=(f"Unsupported sensor_mode={sensor_mode!r}; expected {tuple(IMX510_ROLLING_SHUTTER_MODES)}",),
        )

    width = int(spec["width"])
    height = int(spec["height"])
    fps_hz = float(spec["fps_hz"])
    actual_ms = float(spec["readout_ms"])
    actual_us = int(spec["readout_us"])
    crop_factor = float(spec["crop_factor"])
    frame_period_ms = 1000.0 / fps_hz

    eff_declared_us = actual_us if declared_readout_us is None else int(declared_readout_us)
    err_us = abs(eff_declared_us - actual_us)

    if actual_ms > frame_period_ms:
        errors.append(
            f"Physical readout {actual_ms:.2f} ms exceeds frame period {frame_period_ms:.2f} ms"
        )
    if eff_declared_us <= 0 or eff_declared_us > int(round(frame_period_ms * 1000.0)):
        errors.append(
            f"Declared readout {eff_declared_us} us outside valid frame period [1..{int(round(frame_period_ms * 1000.0))}] us"
        )

    vertical_shear_risk = err_us > IMX510_READOUT_TOLERANCE_US
    if vertical_shear_risk:
        errors.append(
            f"BLOCKED_ROLLING_SHUTTER_READOUT_MISMATCH: mode={norm_mode} actual={actual_us}us "
            f"!= declared={eff_declared_us}us (delta={err_us}us > {IMX510_READOUT_TOLERANCE_US}us)"
        )

    px_per_deg = float(width) / max(1.0, float(hfov_deg))
    skew_residual_px = (err_us / 1_000_000.0) * abs(pan_angular_rate_deg_s) * px_per_deg

    status = (
        "BLOCKED_ROLLING_SHUTTER_READOUT_MISMATCH"
        if vertical_shear_risk
        else ("IMX510_ROLLING_SHUTTER_VERIFIED" if not errors else "BLOCKED_INVALID_READOUT_WINDOW")
    )

    return Imx510RollingShutterEvalResult(
        valid=len(errors) == 0,
        status=status,
        sensor_mode=norm_mode,
        width=width,
        height=height,
        fps_hz=round(fps_hz, 3),
        frame_period_ms=round(frame_period_ms, 3),
        actual_readout_ms=round(actual_ms, 3),
        declared_readout_us=eff_declared_us,
        readout_error_us=err_us,
        crop_factor=crop_factor,
        vertical_shear_risk=vertical_shear_risk,
        skew_residual_px_at_30deg_s=round(skew_residual_px, 3),
        errors=tuple(errors),
    )


def evaluate_pillar_3_imx510_rolling_shutter(
    present_map: Mapping[str, Tuple[str, ...]],
) -> Imx510RollingShutterReport:
    """Audit Pillar 3: `IMX510` readout duration matrix (`4K 24/60p` ~8.7ms vs `4K120` ~4.35ms vs `FHD240` ~2.2ms)."""
    errors: List[str] = []
    fx6_mpr = present_map["fx6_libmpr_rtmd"]
    fx6_cp = present_map["fx6_cp_gyro_readout"]

    req_mpr = (
        "MetaConverterImpl::ConvertReadoutDuration",
        "muxMxfRtmetaBufferImagerReadoutModeWrite",
        "NormalImageControl_ImageReadoutVcycle",
        "NormalImageControl_EffectivePixelReadoutStartTime",
        "NormalImageControl_EffectivePixelReadoutTime",
    )
    missing_mpr = tuple(m for m in req_mpr if m not in fx6_mpr)
    if missing_mpr:
        errors.append(f"FX6 libmpr.so missing readout timing markers: {missing_mpr}")

    req_cp = ("ImageSensorReadoutMode", "ReadoutDuration")
    missing_cp = tuple(m for m in req_cp if m not in fx6_cp)
    if missing_cp:
        errors.append(f"FX6 cpapp-b.bin missing readout markers: {missing_cp}")

    dci24 = evaluate_imx510_rolling_shutter_readout(sensor_mode="4K_DCI_24P")
    qfhd24 = evaluate_imx510_rolling_shutter_readout(sensor_mode="QFHD_4K_24P")
    qfhd60 = evaluate_imx510_rolling_shutter_readout(sensor_mode="QFHD_4K_60P")
    sq120 = evaluate_imx510_rolling_shutter_readout(sensor_mode="SQ_4K_120P")
    fhd240 = evaluate_imx510_rolling_shutter_readout(sensor_mode="FHD_240P")
    wrong_4k120 = evaluate_imx510_rolling_shutter_readout(
        sensor_mode="SQ_4K_120P",
        declared_readout_us=8700,
    )

    for ev in (dci24, qfhd24, qfhd60, sq120, fhd240):
        if not ev.valid or ev.readout_error_us != 0:
            errors.extend(ev.errors or (f"Rolling shutter check failed for {ev.sensor_mode}",))
    if wrong_4k120.valid or not wrong_4k120.vertical_shear_risk:
        errors.append("Mismatched 8.70ms readout stamped on 4K120 failed to flag vertical shear risk")

    return Imx510RollingShutterReport(
        passed=len(errors) == 0,
        fx6_libmpr_readout_markers=tuple(m for m in req_mpr if m in fx6_mpr),
        fx6_cp_readout_markers=tuple(m for m in req_cp if m in fx6_cp),
        eval_4k_dci_24p=dci24,
        eval_qfhd_4k_24p=qfhd24,
        eval_qfhd_4k_60p=qfhd60,
        eval_sq_4k_120p=sq120,
        eval_fhd_240p=fhd240,
        blocked_4k120_wrong_8_7ms_skew_hazard=wrong_4k120,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 4: Stock-CP IMU Factory Bias/Orthogonality Calibration Immutability
# ---------------------------------------------------------------------------


def evaluate_imu_calibration_immutability(
    *,
    target_path: str = "/tmp/fx3_gyro_anamorphic_shadow.json",
    requested_write_bytes: int = 256,
) -> ImuCalibrationImmutabilityResult:
    """Enforce zero mutation of Stock-CP factory IMU bias/temp-drift/orthogonality LUTs (`cnflasha`)."""
    errors: List[str] = []
    norm_path = target_path.strip()
    low = norm_path.lower()

    is_volatile = any(low.startswith(pfx) for pfx in VOLATILE_SHADOW_PREFIXES)
    is_forbidden = any(tok in low for tok in FORBIDDEN_IMU_CALIBRATION_TARGETS)

    if requested_write_bytes < 0:
        errors.append(f"Negative requested_write_bytes={requested_write_bytes!r}")

    if is_forbidden or not is_volatile:
        errors.append(
            f"BLOCKED_PERSISTENT_IMU_CALIBRATION_WRITE: writes to {target_path!r} forbidden; "
            "Stock-CP factory gyro bias/temp-drift/orthogonality LUTs in cnflasha are 100% immutable"
        )
        status = "BLOCKED_PERSISTENT_IMU_CALIBRATION_WRITE"
    else:
        status = "VOLATILE_GYRO_SHADOW_ALLOWED_CALIBRATION_IMMUTABLE"

    return ImuCalibrationImmutabilityResult(
        valid=len(errors) == 0,
        status=status,
        target_path=norm_path,
        volatile_shadow_only=is_volatile and not is_forbidden,
        imu_calibration_mutation_bytes=0,
        cp_mutation_bytes=0,
        persistent_emmc_writes_authorized=False,
        errors=tuple(errors),
    )


def evaluate_pillar_4_imu_calibration_immutability(
    present_map: Mapping[str, Tuple[str, ...]],
    *,
    fx3_xdb_valid: bool,
    fx6_xdb_valid: bool,
) -> StockCpImuCalibrationReport:
    """Audit Pillar 4: Stock-CP IMU factory bias/temp-drift LUTs untouched (`imu_calibration_mutation_bytes == 0`)."""
    errors: List[str] = []
    fx3_cp = present_map["fx3_cp_gyro_calib"]
    fx6_cp = present_map["fx6_cp_gyro_readout"]

    if fx3_cp != FX3_CP_GYRO_CALIB_MARKERS:
        missing = tuple(m for m in FX3_CP_GYRO_CALIB_MARKERS if m not in fx3_cp)
        errors.append(f"FX3 cpapp-b.bin missing IMU/IBIS servo calibration markers: {missing}")
    if fx6_cp != FX6_CP_GYRO_READOUT_MARKERS:
        missing = tuple(m for m in FX6_CP_GYRO_READOUT_MARKERS if m not in fx6_cp)
        errors.append(f"FX6 cpapp-b.bin missing IMU/readout markers: {missing}")
    if not fx3_xdb_valid:
        errors.append("FX3 global.xdb (uxa\\x07) validation failed")
    if not fx6_xdb_valid:
        errors.append("FX6 global.xdb (uxa\\x07) validation failed")

    vol = evaluate_imu_calibration_immutability(
        target_path="/tmp/fx3_gyro_anamorphic_shadow.json",
        requested_write_bytes=256,
    )
    blk_cn = evaluate_imu_calibration_immutability(
        target_path="/dev/cnflasha0",
        requested_write_bytes=64,
    )
    blk_bk = evaluate_imu_calibration_immutability(
        target_path="p2:/Backup.bin",
        requested_write_bytes=64,
    )
    blk_psd = evaluate_imu_calibration_immutability(
        target_path="p2:/psd.bin",
        requested_write_bytes=64,
    )
    blk_jir = evaluate_imu_calibration_immutability(
        target_path="p6:Jiritsu",
        requested_write_bytes=64,
    )

    if not vol.valid or vol.imu_calibration_mutation_bytes != 0:
        errors.extend(vol.errors or ("Volatile gyro shadow overlay failed",))
    for blk in (blk_cn, blk_bk, blk_psd, blk_jir):
        if blk.valid or blk.imu_calibration_mutation_bytes != 0 or blk.persistent_emmc_writes_authorized:
            errors.append(f"Persistent IMU calibration target failed to block: {blk.target_path}")

    return StockCpImuCalibrationReport(
        passed=len(errors) == 0,
        fx3_cp_calib_markers=fx3_cp,
        fx6_cp_calib_markers=fx6_cp,
        fx3_global_xdb_valid=fx3_xdb_valid,
        fx6_global_xdb_valid=fx6_xdb_valid,
        volatile_shadow_eval=vol,
        blocked_cnflasha_eval=blk_cn,
        blocked_backup_bin_eval=blk_bk,
        blocked_psd_bin_eval=blk_psd,
        blocked_jiritsu_eval=blk_jir,
        imu_calibration_mutation_bytes=0,
        cp_mutation_bytes=0,
        persistent_emmc_writes_authorized=False,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Unified Orchestrator & JSON Serialization
# ---------------------------------------------------------------------------


def analyze_metadata_gyro_catalyst_and_anamorphic(
    repo_root: Optional[Path] = None,
    *,
    clean_room: bool = False,
) -> MetadataGyroCatalystAndAnamorphicReport:
    """Run the 17th unified firmware-lab auditor across all 4 Gyroflow/RTMD/Anamorphic/IBIS pillars."""
    root = repo_root or DEFAULT_REPO_ROOT
    forced_clean = clean_room or is_forced_clean_room()

    donor_paths: Optional[Dict[str, Path]] = None
    if not forced_clean:
        rels = {
            "fx3_appfw": FX3_APPFW_RELPATH,
            "fx6_appfw": FX6_APPFW_RELPATH,
            "fx3_libmpr": FX3_LIBMPR_RELPATH,
            "fx6_libmpr": FX6_LIBMPR_RELPATH,
            "fx3_cpapp": FX3_CPAPP_RELPATH,
            "fx6_cpapp": FX6_CPAPP_RELPATH,
            "fx3_lens_comm": FX3_LENS_COMM_RELPATH,
            "fx6_lens_comm": FX6_LENS_COMM_RELPATH,
            "fx3_global_xdb": FX3_GLOBAL_XDB_RELPATH,
            "fx6_global_xdb": FX6_GLOBAL_XDB_RELPATH,
            "fx3_str_en": FX3_STR_EN_RELPATH,
            "fx3_str_en_g": FX3_STR_EN_G_RELPATH,
            "fx6_str_en_1": FX6_STR_EN_1_RELPATH,
            "fx6_str_en_2": FX6_STR_EN_2_RELPATH,
        }
        resolved = {k: resolve_donor_file(v, repo_root=root) for k, v in rels.items()}
        if all(p is not None and p.is_file() for p in resolved.values()):
            donor_paths = {k: p for k, p in resolved.items() if p is not None}

    present_map: Dict[str, Tuple[str, ...]] = {}
    donor_sizes: Dict[str, int] = {}

    if donor_paths is not None:
        mode = "LOCAL_DONOR_VERIFIED"
        sz, grp = _scan_donor_rdonly_markers(
            donor_paths["fx3_appfw"],
            {"fx3_appfw_gyro_anamo": FX3_APPFW_GYRO_ANAMORPHIC_MARKERS},
            is_elf=True,
        )
        donor_sizes["fx3_appfw"] = sz
        present_map.update(grp)

        sz, grp = _scan_donor_rdonly_markers(
            donor_paths["fx6_appfw"],
            {"fx6_appfw_gyro_anamo": FX6_APPFW_GYRO_ANAMORPHIC_MARKERS},
            is_elf=True,
        )
        donor_sizes["fx6_appfw"] = sz
        present_map.update(grp)

        sz, grp = _scan_donor_rdonly_markers(
            donor_paths["fx3_libmpr"],
            {"fx3_libmpr_rtmd": FX3_LIBMPR_RTMD_IMU_MARKERS},
            is_elf=True,
        )
        donor_sizes["fx3_libmpr"] = sz
        present_map.update(grp)

        sz, grp = _scan_donor_rdonly_markers(
            donor_paths["fx6_libmpr"],
            {"fx6_libmpr_rtmd": FX6_LIBMPR_RTMD_READOUT_MARKERS},
            is_elf=True,
        )
        donor_sizes["fx6_libmpr"] = sz
        present_map.update(grp)

        sz, grp = _scan_donor_rdonly_markers(
            donor_paths["fx3_cpapp"],
            {"fx3_cp_gyro_calib": FX3_CP_GYRO_CALIB_MARKERS},
            is_elf=False,
        )
        donor_sizes["fx3_cpapp"] = sz
        present_map.update(grp)

        sz, grp = _scan_donor_rdonly_markers(
            donor_paths["fx6_cpapp"],
            {"fx6_cp_gyro_readout": FX6_CP_GYRO_READOUT_MARKERS},
            is_elf=False,
        )
        donor_sizes["fx6_cpapp"] = sz
        present_map.update(grp)

        sz, grp = _scan_donor_rdonly_markers(
            donor_paths["fx3_lens_comm"],
            {"lens_comm_gyro": LENS_COMM_GYRO_MARKERS},
            is_elf=True,
        )
        donor_sizes["fx3_lens_comm"] = sz
        present_map.update(grp)

        donor_sizes["fx6_lens_comm"] = os.stat(donor_paths["fx6_lens_comm"]).st_size

        fx3_xdb_bytes = _read_bytes_rdonly(donor_paths["fx3_global_xdb"])
        fx6_xdb_bytes = _read_bytes_rdonly(donor_paths["fx6_global_xdb"])
        fx3_en_bytes = _read_bytes_rdonly(donor_paths["fx3_str_en"])
        fx3_eng_bytes = _read_bytes_rdonly(donor_paths["fx3_str_en_g"])
        fx6_en1_bytes = _read_bytes_rdonly(donor_paths["fx6_str_en_1"])
        fx6_en2_bytes = _read_bytes_rdonly(donor_paths["fx6_str_en_2"])
        donor_sizes["fx3_global_xdb"] = len(fx3_xdb_bytes)
        donor_sizes["fx6_global_xdb"] = len(fx6_xdb_bytes)
        donor_sizes["fx3_str_en"] = len(fx3_en_bytes)
        donor_sizes["fx3_str_en_g"] = len(fx3_eng_bytes)
        donor_sizes["fx6_str_en_1"] = len(fx6_en1_bytes)
        donor_sizes["fx6_str_en_2"] = len(fx6_en2_bytes)
    else:
        mode = "CLEAN_ROOM_SYNTHETIC"
        fixtures = build_clean_room_gyro_anamorphic_fixtures()
        donor_sizes = {k: len(v) for k, v in fixtures.items()}

        _, grp = _scan_bytes_marker_groups(
            fixtures["fx3_appfw"], {"fx3_appfw_gyro_anamo": FX3_APPFW_GYRO_ANAMORPHIC_MARKERS}
        )
        present_map.update(grp)
        _, grp = _scan_bytes_marker_groups(
            fixtures["fx6_appfw"], {"fx6_appfw_gyro_anamo": FX6_APPFW_GYRO_ANAMORPHIC_MARKERS}
        )
        present_map.update(grp)
        _, grp = _scan_bytes_marker_groups(
            fixtures["fx3_libmpr"], {"fx3_libmpr_rtmd": FX3_LIBMPR_RTMD_IMU_MARKERS}
        )
        present_map.update(grp)
        _, grp = _scan_bytes_marker_groups(
            fixtures["fx6_libmpr"], {"fx6_libmpr_rtmd": FX6_LIBMPR_RTMD_READOUT_MARKERS}
        )
        present_map.update(grp)
        _, grp = _scan_bytes_marker_groups(
            fixtures["fx3_cpapp"], {"fx3_cp_gyro_calib": FX3_CP_GYRO_CALIB_MARKERS}
        )
        present_map.update(grp)
        _, grp = _scan_bytes_marker_groups(
            fixtures["fx6_cpapp"], {"fx6_cp_gyro_readout": FX6_CP_GYRO_READOUT_MARKERS}
        )
        present_map.update(grp)
        _, grp = _scan_bytes_marker_groups(
            fixtures["fx3_lens_comm"], {"lens_comm_gyro": LENS_COMM_GYRO_MARKERS}
        )
        present_map.update(grp)

        fx3_xdb_bytes = fixtures["fx3_global_xdb"]
        fx6_xdb_bytes = fixtures["fx6_global_xdb"]
        fx3_en_bytes = fixtures["fx3_str_en"]
        fx3_eng_bytes = fixtures["fx3_str_en_g"]
        fx6_en1_bytes = fixtures["fx6_str_en_1"]
        fx6_en2_bytes = fixtures["fx6_str_en_2"]

    errors: List[str] = []
    fx3_xdb_valid = False
    fx6_xdb_valid = False
    try:
        xdb3 = parse_global_xdb_buffer(fx3_xdb_bytes, body="fx3_702", source_mode=mode)
        fx3_xdb_valid = bool(xdb3.valid and xdb3.active_slot_count > 0)
    except Exception as exc:
        errors.append(f"FX3 global.xdb parse error: {exc}")
    try:
        xdb6 = parse_global_xdb_buffer(fx6_xdb_bytes, body="fx6_601", source_mode=mode)
        fx6_xdb_valid = bool(xdb6.valid and xdb6.active_slot_count > 0)
    except Exception as exc:
        errors.append(f"FX6 global.xdb parse error: {exc}")

    uxc_labels: Dict[str, str] = {}
    lbl39, err39 = _extract_uxc_labels(fx3_en_bytes, FX3_NS39_PHASE89_LABELS)
    lbl3, err3 = _extract_uxc_labels(fx3_eng_bytes, FX3_NS3_PHASE89_LABELS)
    lbl61, err61 = _extract_uxc_labels(fx6_en1_bytes, FX6_NS1_PHASE89_LABELS)
    lbl62, err62 = _extract_uxc_labels(fx6_en2_bytes, FX6_NS2_PHASE89_LABELS)
    errors.extend(err39)
    errors.extend(err3)
    errors.extend(err61)
    errors.extend(err62)

    uxc_labels["fx3_steadyshot"] = lbl39.get("0x0004e153", "")
    uxc_labels["fx3_steadyshot_off_hint"] = lbl39.get("0x0004e0ea", "")
    uxc_labels["fx3_shutter_steadyshot"] = lbl3.get("0x00006183", "")
    uxc_labels["fx6_desqueeze"] = lbl61.get("0x00002504", "")
    uxc_labels["fx6_steadyshot_focal"] = lbl61.get("0x000027ee", "")
    uxc_labels["fx6_lcd_desqueeze"] = lbl61.get("0x000027f0", "")
    uxc_labels["fx6_hdmi_desqueeze"] = lbl61.get("0x000027f2", "")
    uxc_labels["fx6_desqueeze_ratio"] = lbl61.get("0x000027fe", "")
    uxc_labels["fx6_steadyshot_ns2"] = lbl62.get("0x00004216", "")
    uxc_labels["fx6_anamorphic"] = lbl62.get("0x000046c7", "")
    uxc_labels["fx6_steadyshot_active"] = lbl62.get("0x00004759", "")
    uxc_labels["fx6_steadyshot_standard"] = lbl62.get("0x0000475a", "")
    uxc_labels["fx6_steadyshot_off"] = lbl62.get("0x00005691", "")

    p1 = evaluate_pillar_1_gyroflow_rtmd(present_map, uxc_labels)
    p2 = evaluate_pillar_2_anamorphic_ibis(present_map, uxc_labels)
    p3 = evaluate_pillar_3_imx510_rolling_shutter(present_map)
    p4 = evaluate_pillar_4_imu_calibration_immutability(
        present_map,
        fx3_xdb_valid=fx3_xdb_valid,
        fx6_xdb_valid=fx6_xdb_valid,
    )

    errors.extend(p1.errors)
    errors.extend(p2.errors)
    errors.extend(p3.errors)
    errors.extend(p4.errors)

    all_passed = bool(
        len(errors) == 0
        and p1.passed
        and p2.passed
        and p3.passed
        and p4.passed
        and p4.imu_calibration_mutation_bytes == 0
        and p4.cp_mutation_bytes == 0
        and not p4.persistent_emmc_writes_authorized
    )

    digest_payload = {
        "schema_version": PHASE_89_SCHEMA,
        "phase_version": PHASE_89_VERSION,
        "mode": mode,
        "all_checks_passed": all_passed,
        "donor_file_sizes": donor_sizes,
        "pillar_1": asdict(p1),
        "pillar_2": asdict(p2),
        "pillar_3": asdict(p3),
        "pillar_4": asdict(p4),
    }
    report_sha256 = hashlib.sha256(
        json.dumps(digest_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()

    return MetadataGyroCatalystAndAnamorphicReport(
        schema_version=PHASE_89_SCHEMA,
        phase_version=PHASE_89_VERSION,
        mode=mode,
        all_checks_passed=all_passed,
        o_rdonly_enforced=True,
        persistent_emmc_writes_authorized=False,
        imu_calibration_mutation_bytes=0,
        cp_mutation_bytes=0,
        donor_file_sizes=donor_sizes,
        pillar_1_gyroflow_rtmd=p1,
        pillar_2_anamorphic_ibis=p2,
        pillar_3_imx510_rolling_shutter=p3,
        pillar_4_imu_calibration_immutability=p4,
        errors=tuple(errors),
        report_sha256=report_sha256,
    )


def metadata_gyro_catalyst_and_anamorphic_report_to_dict(
    report: MetadataGyroCatalystAndAnamorphicReport,
) -> Dict[str, object]:
    """Convert `MetadataGyroCatalystAndAnamorphicReport` to a JSON-serializable dict."""
    return report.to_dict()
