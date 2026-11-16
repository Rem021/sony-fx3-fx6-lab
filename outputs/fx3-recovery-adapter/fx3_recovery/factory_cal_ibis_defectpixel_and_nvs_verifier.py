"""Phase 126 — Per-Unit Factory Calibration (`nvs` / `cnflasha` / `adj`), `IMX510`
Defect-Pixel / Dual-Base ISO ADC Offset & 5-Axis `IBIS` Hall-Zero Cross-Serial Donor
Poisoning Firewall, and 14-Pillar Recovery Master Suite.

Provides three deterministic, RAM-only, read-only-donor verification pillars for
Sony `ILME-FX3` (`0x91030080` / `ALCIN_UUD`, `CXD90057` / `CXD90058`) recovery safety:

1. **Read-Only (`O_RDONLY`) FX3/FX6 Donor Calibration/Backup/Sensor/IBIS Inspection**:
   - Opens local FX3 `v7.02` (`libbackup.so`, `backup.ko`, `appFw.so`, and `cpapp-b.bin`
     when requested) and FX6 `v6.01` (`libbackup.so`, `appFw.so`, `cpapp-b.bin`) donor
     artifacts strictly via `os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK`, verifying
     calibration/backup/IMX510/IBIS/Hall/gyro symbol anchors and cross-SKU separation
     with zero raw firmware bytes or private keys emitted.
   - Deterministically falls back to pinned `CLEAN_ROOM_SYNTHETIC` metadata when
     `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor files are absent.

2. **Pillar A — Per-Body Factory Calibration Partition (`nvs` / `adj` / `cnflasha`)
   Triple-Copy SHA-256 Parity & Cross-Serial Donor Transplant Firewall**:
   - Enforces fail-closed:
     a) `BLOCKED_CROSS_SERIAL_FACTORY_CAL_TRANSPLANT` if a restore manifest's
        calibration partition `body_serial_hash` / `board_uid_hash` does not match the
        target camera's Tier-0 backup identity,
     b) `BLOCKED_MISSING_TIER0_FACTORY_CAL_TRIPLE_PARITY` if fewer than 2 independent
        matching SHA-256 copies exist for `nvs` / `adj` / `cnflasha`,
     c) `BLOCKED_CNFLASHA_KEY_VAULT_WRITE_OR_EXTRACTION` if any operation attempts to
        modify `cnflasha` or read raw asymmetric key material (`private_key_bytes_read == 0`).

3. **Pillar B — `IMX510` Defect-Pixel Map (`Base ISO 800 / 12800` Dual-Gain
   Column-ADC) & 5-Axis `IBIS` Hall-Sensor / `IMU` Gyro Temperature-Bias Table
   Integrity Verifier**:
   - Validates clean-room structural invariants of per-sensor calibration tables:
     monotonic row-major pixel coordinates within `4264 x 2408` active `IMX510` array,
     bounded dual-gain `ISO 800 / 12800` dark-current & column-FPN offsets, bounded
     5-axis `IBIS` (`pitch`, `yaw`, `roll`, `x`, `y`) Hall-sensor zero-centers,
     `-10°C..+60°C` `IMU` gyro bias polynomials, and CRC32 integrity verification.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
import re
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple
import zlib

from .files import is_forced_clean_room, read_file, require, resolve_donor_path


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

FACTORY_CAL_IBIS_NVS_SCHEMA: str = "fx3-factory-cal-ibis-defectpixel-and-nvs-verifier-v1"
FACTORY_CAL_IBIS_NVS_VERSION: str = "1.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False
ALLOW_BOOT_PARTITION_TARGETING: bool = False
ALLOW_DESTRUCTIVE_FASTBOOT: bool = False
READ_ONLY_DONOR_ACCESS: bool = True
OTP_FUSE_TOUCHES: int = 0
PASSIVE_TX_BYTES_EMITTED: int = 0
PHYSICAL_DEVICE_WRITES: int = 0
FACTORY_CAL_MUTATION_BYTES: int = 0
PRIVATE_KEY_BYTES_READ: int = 0

FX3_CAL_MODEL_ID: int = 0x91030080
FX6_CAL_MODEL_ID: int = 0x91040086
FX3_CAL_SKU_CODE: str = "ILME-FX3"
FX6_CAL_SKU_CODE: str = "ILME-FX6"

STATUS_VERIFIED_FACTORY_CAL_GUARD: str = "VERIFIED_FACTORY_CAL_IBIS_AND_NVS_GUARD"
STATUS_FAIL_FACTORY_CAL_GUARD: str = "FAIL_FACTORY_CAL_IBIS_AND_NVS_GUARD"
STATUS_VERIFIED_FACTORY_CAL_PARITY: str = "VERIFIED_FACTORY_CAL_TRIPLE_PARITY"
STATUS_REJECTED_FACTORY_CAL_FIREWALL: str = "REJECTED_FACTORY_CAL_FIREWALL"
STATUS_VERIFIED_SENSOR_IBIS_CAL_TABLES: str = "VERIFIED_IMX510_AND_IBIS_CAL_TABLES"
STATUS_REJECTED_SENSOR_IBIS_CAL_TABLES: str = "REJECTED_IMX510_OR_IBIS_CAL_TABLES"

# Local Donor Relative Paths (strictly read-only via os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK)
DONOR_FX3_LIBBACKUP_RELPATH: str = (
    "sony-firmware-20261024/stage208-Backup-record-routing/originals/lib/libbackup.so"
)
DONOR_FX6_LIBBACKUP_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libbackup.so"
)
DONOR_FX3_BACKUP_KO_RELPATH: str = (
    "sony-firmware-20261024/stage208-Backup-record-routing/originals/kmod/backup.ko"
)
DONOR_FX3_APPFW_RELPATH: str = (
    "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so"
)
DONOR_FX6_APPFW_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so"
)
DONOR_FX3_CPAPP_B_RELPATH: str = (
    "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin"
)
DONOR_FX6_CPAPP_B_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fat-files/nflasha8/cpapp-b.bin"
)

# Pinned Donor Integrity Anchors (Zero Proprietary Keys / Zero Raw Firmware Bytes)
PINNED_FX3_LIBBACKUP_BYTES: int = 14232
PINNED_FX3_LIBBACKUP_SHA256: str = "6a3c5f6067620c00d790cbe520844acdbb721fa5d0e7433b00a227f922ab9d0d"
PINNED_FX6_LIBBACKUP_BYTES: int = 14232
PINNED_FX6_LIBBACKUP_SHA256: str = "e003e2d8a1f42fdf629dda012a01f225940c016b2ab4dbf482a761378e8d286f"
PINNED_FX3_BACKUP_KO_BYTES: int = 144976
PINNED_FX3_BACKUP_KO_SHA256: str = "8a8d8c949699c130c116d0006806d8b7f92b20869c92a72876529a2001d60c4d"
PINNED_FX3_APPFW_BYTES: int = 79015712
PINNED_FX3_APPFW_SHA256: str = "545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f"
PINNED_FX6_APPFW_BYTES: int = 50520424
PINNED_FX6_APPFW_SHA256: str = "a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067"
PINNED_FX3_CPAPP_B_BYTES: int = 15980568
PINNED_FX3_CPAPP_B_SHA256: str = "c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba"
PINNED_FX6_CPAPP_B_BYTES: int = 17952816
PINNED_FX6_CPAPP_B_SHA256: str = "60de0ab5544749dd50d8245f573c0994573fef349186efe20b502c42e3289668"

# ---------------------------------------------------------------------------
# Pillar A Constants — Per-Body Factory Calibration (`nvs` / `adj` / `cnflasha`)
# ---------------------------------------------------------------------------

FACTORY_CAL_PARTITIONS: Tuple[str, ...] = ("nvs", "adj", "cnflasha")
FACTORY_CAL_TRIPLE_COPY_SLOTS: Tuple[str, ...] = (
    "tier0_primary",
    "tier0_sd_mirror",
    "tier0_airgap_archive",
)
MIN_TRIPLE_PARITY_MATCHING_COPIES: int = 2

# Required Pillar A Firewall Codes (exact names per Phase 126 spec)
BLOCKED_CROSS_SERIAL_FACTORY_CAL_TRANSPLANT: str = "BLOCKED_CROSS_SERIAL_FACTORY_CAL_TRANSPLANT"
BLOCKED_MISSING_TIER0_FACTORY_CAL_TRIPLE_PARITY: str = "BLOCKED_MISSING_TIER0_FACTORY_CAL_TRIPLE_PARITY"
BLOCKED_CNFLASHA_KEY_VAULT_WRITE_OR_EXTRACTION: str = "BLOCKED_CNFLASHA_KEY_VAULT_WRITE_OR_EXTRACTION"

ERR_FACTORY_CAL_SKU_MISMATCH: str = "FACTORY_CAL_CROSS_SKU_FX6_REJECTED"
ERR_FACTORY_CAL_INVALID_SHA256: str = "FACTORY_CAL_INVALID_SHA256_FORMAT"
ERR_FACTORY_CAL_MUTATION_FORBIDDEN: str = "FACTORY_CAL_PERSISTENT_MUTATION_FORBIDDEN"

FORBIDDEN_CNFLASHA_OPERATION_VERBS: Tuple[str, ...] = (
    "write_cnflasha",
    "flash_cnflasha",
    "erase_cnflasha",
    "patch_cnflasha",
    "overwrite_cnflasha",
    "modify_cnflasha",
    "extract_cnflasha",
    "extract_private_key",
    "read_private_key",
    "dump_private_key",
    "read_asymmetric_key",
    "export_rsa_key",
    "export_ecdsa_key",
    "dump_key_vault",
)

FORBIDDEN_FACTORY_CAL_WRITE_VERBS: Tuple[str, ...] = (
    "write_nvs",
    "flash_nvs",
    "erase_nvs",
    "overwrite_nvs",
    "write_adj",
    "flash_adj",
    "erase_adj",
    "overwrite_adj",
    "write_factory_cal",
    "mutate_cal",
)

FACTORY_CAL_FIREWALL_SCENARIO_IDS: Tuple[str, ...] = (
    "F1_HEALTHY_SAME_BODY_TRIPLE_PARITY",
    "F2_HEALTHY_2_OF_3_QUORUM_SURVIVES_SINGLE_CORRUPTION",
    "F3_CROSS_SERIAL_DONOR_TRANSPLANT_BLOCKED",
    "F4_MISSING_TIER0_TRIPLE_PARITY_BLOCKED",
    "F5_CNFLASHA_KEY_VAULT_WRITE_BLOCKED",
    "F6_CNFLASHA_PRIVATE_KEY_EXTRACTION_BLOCKED",
)

# ---------------------------------------------------------------------------
# Pillar B Constants — IMX510 Defect-Pixel & 5-Axis IBIS / IMU Calibration
# ---------------------------------------------------------------------------

IMX510_ACTIVE_WIDTH: int = 4264
IMX510_ACTIVE_HEIGHT: int = 2408
IMX510_DUAL_BASE_ISOS: Tuple[int, int] = (800, 12800)
IMX510_MIN_DEFECT_PIXELS: int = 1
IMX510_MAX_DEFECT_PIXELS: int = 16384
IMX510_MIN_COLUMN_FPN_BANKS: int = 16
IMX510_DARK_CURRENT_OFFSET_MIN_LSB: float = -64.0
IMX510_DARK_CURRENT_OFFSET_MAX_LSB: float = 256.0
IMX510_COLUMN_FPN_OFFSET_ABS_MAX_LSB: float = 32.0
IMX510_ANALOG_GAIN_MIN: float = 0.5
IMX510_ANALOG_GAIN_MAX: float = 64.0
IMX510_DUAL_GAIN_RATIO_MIN: float = 4.0
IMX510_DUAL_GAIN_RATIO_MAX: float = 20.0

IBIS_5_AXES: Tuple[str, ...] = ("pitch", "yaw", "roll", "x", "y")
IBIS_HALL_ADC_MAX: int = 4095
IBIS_HALL_ZERO_CENTER_MIN: int = 1024
IBIS_HALL_ZERO_CENTER_MAX: int = 3072
IBIS_HALL_STROKE_LIMIT_MIN: int = 128
IBIS_HALL_STROKE_LIMIT_MAX: int = 1600

IMU_TEMP_MIN_C: float = -10.0
IMU_TEMP_MAX_C: float = 60.0
IMU_TEMP_REF_C: float = 25.0
IMU_GYRO_BIAS_ABS_MAX_DPS: float = 5.0
IMU_GYRO_C1_ABS_MAX_DPS_PER_C: float = 0.08
IMU_GYRO_C2_ABS_MAX_DPS_PER_C2: float = 0.002

ERR_IMX510_EMPTY_OR_OVERSIZED_DEFECT_MAP: str = "IMX510_EMPTY_OR_OVERSIZED_DEFECT_MAP"
ERR_IMX510_PIXEL_OUT_OF_BOUNDS: str = "IMX510_DEFECT_PIXEL_OUT_OF_4264X2408_BOUNDS"
ERR_IMX510_NON_MONOTONIC_COORDINATES: str = "IMX510_NON_MONOTONIC_OR_DUPLICATE_COORDINATES"
ERR_IMX510_DUAL_ISO_CONFIG_INVALID: str = "IMX510_DUAL_BASE_ISO_800_12800_INVALID"
ERR_IMX510_ADC_OFFSET_OUT_OF_RANGE: str = "IMX510_COLUMN_ADC_OR_DARK_OFFSET_OUT_OF_RANGE"
ERR_IMX510_CRC32_MISMATCH: str = "IMX510_CAL_TABLE_CRC32_MISMATCH"
ERR_IBIS_AXES_MISMATCH: str = "IBIS_5AXIS_MAP_INCOMPLETE_OR_INVALID"
ERR_IBIS_HALL_ZERO_OUT_OF_RANGE: str = "IBIS_HALL_ZERO_CENTER_OUT_OF_RANGE"
ERR_IMU_TEMP_RANGE_COVERAGE_INVALID: str = "IMU_TEMP_RANGE_MINUS10_TO_PLUS60_UNCOVERED"
ERR_IMU_GYRO_BIAS_POLY_OUT_OF_RANGE: str = "IMU_GYRO_TEMP_BIAS_POLYNOMIAL_OUT_OF_RANGE"
ERR_IBIS_IMU_CRC32_MISMATCH: str = "IBIS_IMU_CAL_TABLE_CRC32_MISMATCH"
ERR_SENSOR_BODY_BINDING_MISMATCH: str = "SENSOR_IBIS_TABLE_BODY_SERIAL_MISMATCH"

SENSOR_IBIS_SCENARIO_IDS: Tuple[str, ...] = (
    "S1_HEALTHY_IMX510_AND_5AXIS_IBIS_VALID",
    "S2_IMX510_OUT_OF_BOUNDS_OR_NON_MONOTONIC_REJECTED",
    "S3_IMX510_DUAL_ISO_ADC_OFFSET_DRIFT_REJECTED",
    "S4_IBIS_HALL_ZERO_CENTER_RAIL_SATURATION_REJECTED",
    "S5_IMU_GYRO_TEMP_BIAS_POLY_DIVERGENCE_REJECTED",
    "S6_CAL_TABLE_CRC32_TAMPER_REJECTED",
)

_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")


# ---------------------------------------------------------------------------
# Internal Helpers (Zero raw bytes / zero NaN)
# ---------------------------------------------------------------------------


def _canonical_json_bytes(obj: Any) -> bytes:
    return json.dumps(
        obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _canonical_sha256(obj: Any) -> str:
    return sha256(_canonical_json_bytes(obj)).hexdigest()


def _is_valid_sha256_hex(val: str) -> bool:
    return isinstance(val, str) and bool(_SHA256_HEX_RE.match(val))


def _is_finite_float(val: Any) -> bool:
    return isinstance(val, (int, float)) and not isinstance(val, bool) and math.isfinite(float(val))


# ---------------------------------------------------------------------------
# Structured Dataclasses (Zero raw bytes / zero private keys)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FactoryCalDonorArtifactDigest:
    label: str
    relpath: str
    source_mode: str
    byte_length: int
    sha256: str
    inspected: bool
    symbols_verified: Tuple[str, ...]
    details: str


@dataclass(frozen=True)
class DonorFactoryCalSnapshot:
    verification_mode: str
    read_only_access: bool
    include_cpapp: bool
    fx3_libbackup_sha256: str
    fx6_libbackup_sha256: str
    fx3_backup_ko_sha256: str
    fx3_appfw_sha256: str
    fx6_appfw_sha256: str
    fx3_cpapp_b_sha256: str
    fx6_cpapp_b_sha256: str
    cross_sku_distinct: bool
    artifacts: Tuple[FactoryCalDonorArtifactDigest, ...]
    snapshot_sha256: str


@dataclass(frozen=True)
class FactoryCalTargetIdentity:
    sku_code: str = FX3_CAL_SKU_CODE
    model_id: int = FX3_CAL_MODEL_ID
    body_serial_hash: str = ""
    board_uid_hash: str = ""


@dataclass(frozen=True)
class FactoryCalCopyDigest:
    partition_name: str
    copy_slot: str
    media_location: str
    byte_length: int
    sha256: str
    blank_or_erased: bool = False
    present: bool = True


@dataclass(frozen=True)
class FactoryCalRestoreManifest:
    manifest_id: str
    target_sku_code: str
    target_model_id: int
    body_serial_hash: str
    board_uid_hash: str
    partition_copies: Tuple[FactoryCalCopyDigest, ...]
    requested_operations: Tuple[str, ...] = ("verify_parity_readonly",)
    read_private_key_bytes_requested: int = 0
    write_bytes_requested: int = 0


@dataclass(frozen=True)
class CnflashaVaultDecision:
    allowed: bool
    status: str
    operation: str
    target_partition: str
    read_private_key_bytes_requested: int
    write_bytes_requested: int
    private_key_bytes_read: int
    factory_cal_mutation_bytes: int
    physical_device_writes: int
    error_codes: Tuple[str, ...]
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PartitionParityStatus:
    partition_name: str
    total_copies_present: int
    independent_matching_copies: int
    consensus_sha256: str
    quorum_met: bool


@dataclass(frozen=True)
class FactoryCalFirewallReport:
    passed: bool
    status: str
    scenario_id: str
    target_sku_code: str
    manifest_sku_code: str
    cross_serial_blocked: bool
    missing_triple_parity_blocked: bool
    cnflasha_vault_blocked: bool
    triple_parity_verified: bool
    identity_match_verified: bool
    cnflasha_vault_protected: bool
    partition_parity: Tuple[PartitionParityStatus, ...]
    physical_device_writes: int
    factory_cal_mutation_bytes: int
    private_key_bytes_read: int
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    error_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    report_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FactoryCal6ScenarioSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenario_results: Tuple[FactoryCalFirewallReport, ...]
    vault_write_decision: CnflashaVaultDecision
    vault_extract_decision: CnflashaVaultDecision
    physical_device_writes: int
    factory_cal_mutation_bytes: int
    private_key_bytes_read: int
    errors: Tuple[str, ...]
    suite_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Imx510DefectPixelCoord:
    x: int
    y: int
    defect_kind: int = 1


@dataclass(frozen=True)
class Imx510BaseIsoAdcProfile:
    base_iso: int
    analog_gain: float
    dark_current_offset_lsb: float
    column_fpn_offsets_lsb: Tuple[float, ...]


@dataclass(frozen=True)
class Imx510DefectAndAdcCalTable:
    body_serial_hash: str
    sensor_model: str
    active_width: int
    active_height: int
    defect_pixels: Tuple[Imx510DefectPixelCoord, ...]
    iso_800_profile: Imx510BaseIsoAdcProfile
    iso_12800_profile: Imx510BaseIsoAdcProfile
    crc32: int


@dataclass(frozen=True)
class IbisAxisHallCalEntry:
    axis_name: str
    hall_zero_center_adc: int
    positive_stroke_limit_adc: int
    negative_stroke_limit_adc: int


@dataclass(frozen=True)
class ImuGyroTempBiasPolyEntry:
    axis_name: str
    c0_dps: float
    c1_dps_per_c: float
    c2_dps_per_c2: float


@dataclass(frozen=True)
class IbisAndImuCalTable:
    body_serial_hash: str
    temp_min_c: float
    temp_max_c: float
    ibis_axes: Tuple[IbisAxisHallCalEntry, ...]
    imu_gyro_polys: Tuple[ImuGyroTempBiasPolyEntry, ...]
    crc32: int


@dataclass(frozen=True)
class SensorIbisCalVerificationReport:
    passed: bool
    status: str
    scenario_id: str
    imx510_defect_count: int
    imx510_monotonic_in_bounds: bool
    imx510_dual_iso_offsets_bounded: bool
    imx510_crc32_valid: bool
    ibis_5axis_hall_zero_bounded: bool
    imu_gyro_temp_poly_bounded: bool
    ibis_imu_crc32_valid: bool
    body_serial_binding_valid: bool
    physical_device_writes: int
    factory_cal_mutation_bytes: int
    private_key_bytes_read: int
    error_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    report_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SensorIbisCal6ScenarioSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenario_results: Tuple[SensorIbisCalVerificationReport, ...]
    errors: Tuple[str, ...]
    suite_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FactoryCalIbisAndNvsSuiteReport:
    schema: str
    version: str
    status: str
    verification_mode: str
    all_passed: bool
    read_only_donor_access: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    allow_boot_partition_targeting: bool
    allow_destructive_fastboot: bool
    otp_fuse_touches: int
    passive_tx_bytes_emitted: int
    physical_device_writes: int
    factory_cal_mutation_bytes: int
    private_key_bytes_read: int
    donor_snapshot: DonorFactoryCalSnapshot
    factory_cal_6_scenario_firewall: FactoryCal6ScenarioSuiteResult
    sensor_ibis_6_scenario_suite: SensorIbisCal6ScenarioSuiteResult
    suite_sha256: str
    elapsed_seconds: float
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Read-Only (O_RDONLY) Donor Inspection & Clean-Room Synthetic Fallback
# ---------------------------------------------------------------------------


def _scan_symbols(blob: bytes, symbols: Sequence[bytes]) -> Tuple[str, ...]:
    found: List[str] = []
    for sym in symbols:
        if sym in blob:
            found.append(sym.decode("ascii", errors="replace"))
    return tuple(found)


def inspect_factory_cal_and_sensor_donors_readonly(
    *,
    force_clean_room: Optional[bool] = None,
    include_cpapp: bool = True,
) -> DonorFactoryCalSnapshot:
    """Inspect local FX3 v7.02 & FX6 v6.01 calibration/backup/sensor/IBIS symbol & string
    references (`libbackup.so`, `backup.ko`, `appFw.so`, and `cpapp-b.bin` when requested)
    strictly via `os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK`, falling back deterministically
    to pinned `CLEAN_ROOM_SYNTHETIC` metadata when forced or donor files are absent.
    """
    clean_room = is_forced_clean_room() if force_clean_room is None else bool(force_clean_room)

    fx3_libbk_syms = (b"Backup_read", b"Backup_write", b"Backup_read_setting_attr", b"Backup_write_setting_attr")
    fx6_libbk_syms = (b"Backup_read", b"Backup_write", b"Backup_read_setting_attr")
    fx3_bko_syms = (b"/setting/Backup.bin", b"/Backup.bak", b"Data_CalChecksum", b"Backup_read_setting_attr")
    fx3_appfw_syms = (b"Backup_read", b"Backup_write", b"SteadyShot", b"gyro", b"sensor")
    fx6_appfw_syms = (b"Backup_read", b"Backup_write", b"000_main/adjust/senser.cpp", b"procam_adjust_check_controller")
    cpapp_syms = (b"IMX510", b"Alloc_DefectAdjMemory", b"Hall_AD_0", b"Hall_AD_1", b"KDGyro_AD_0", b"Backup_read")

    if not clean_room:
        fx3_libbk_p = resolve_donor_path(DONOR_FX3_LIBBACKUP_RELPATH, require_file=True)
        fx6_libbk_p = resolve_donor_path(DONOR_FX6_LIBBACKUP_RELPATH, require_file=True)
        fx3_bko_p = resolve_donor_path(DONOR_FX3_BACKUP_KO_RELPATH, require_file=True)
        fx3_appfw_p = resolve_donor_path(DONOR_FX3_APPFW_RELPATH, require_file=True)
        fx6_appfw_p = resolve_donor_path(DONOR_FX6_APPFW_RELPATH, require_file=True)
        required_paths: List[Any] = [fx3_libbk_p, fx6_libbk_p, fx3_bko_p, fx3_appfw_p, fx6_appfw_p]
        if include_cpapp:
            fx3_cp_p = resolve_donor_path(DONOR_FX3_CPAPP_B_RELPATH, require_file=True)
            fx6_cp_p = resolve_donor_path(DONOR_FX6_CPAPP_B_RELPATH, require_file=True)
            required_paths.extend([fx3_cp_p, fx6_cp_p])
        else:
            fx3_cp_p = fx6_cp_p = None
        all_present = all(p.is_file() for p in required_paths)
    else:
        fx3_libbk_p = fx6_libbk_p = fx3_bko_p = fx3_appfw_p = fx6_appfw_p = fx3_cp_p = fx6_cp_p = None
        all_present = False

    if all_present:
        mode = "LOCAL_DONOR_O_RDONLY"
        fx3_libbk_bytes = read_file(fx3_libbk_p, 2 * 1024 * 1024)
        fx6_libbk_bytes = read_file(fx6_libbk_p, 2 * 1024 * 1024)
        fx3_bko_bytes = read_file(fx3_bko_p, 4 * 1024 * 1024)
        fx3_appfw_bytes = read_file(fx3_appfw_p, 96 * 1024 * 1024)
        fx6_appfw_bytes = read_file(fx6_appfw_p, 96 * 1024 * 1024)

        found_fx3_libbk = _scan_symbols(fx3_libbk_bytes, fx3_libbk_syms)
        found_fx6_libbk = _scan_symbols(fx6_libbk_bytes, fx6_libbk_syms)
        found_fx3_bko = _scan_symbols(fx3_bko_bytes, fx3_bko_syms)
        found_fx3_appfw = _scan_symbols(fx3_appfw_bytes, fx3_appfw_syms)
        found_fx6_appfw = _scan_symbols(fx6_appfw_bytes, fx6_appfw_syms)

        require(len(found_fx3_libbk) == len(fx3_libbk_syms), "FX3 libbackup.so missing expected Backup symbols")
        require(len(found_fx6_libbk) == len(fx6_libbk_syms), "FX6 libbackup.so missing expected Backup symbols")
        require(len(found_fx3_bko) == len(fx3_bko_syms), "FX3 backup.ko missing expected /setting/Backup.bin anchors")
        require(len(found_fx3_appfw) == len(fx3_appfw_syms), "FX3 appFw.so missing expected calibration/gyro symbols")
        require(len(found_fx6_appfw) == len(fx6_appfw_syms), "FX6 appFw.so missing expected adjust/senser symbols")

        fx3_libbk_len = len(fx3_libbk_bytes)
        fx3_libbk_sha = sha256(fx3_libbk_bytes).hexdigest()
        fx6_libbk_len = len(fx6_libbk_bytes)
        fx6_libbk_sha = sha256(fx6_libbk_bytes).hexdigest()
        fx3_bko_len = len(fx3_bko_bytes)
        fx3_bko_sha = sha256(fx3_bko_bytes).hexdigest()
        fx3_appfw_len = len(fx3_appfw_bytes)
        fx3_appfw_sha = sha256(fx3_appfw_bytes).hexdigest()
        fx6_appfw_len = len(fx6_appfw_bytes)
        fx6_appfw_sha = sha256(fx6_appfw_bytes).hexdigest()

        if include_cpapp and fx3_cp_p is not None and fx6_cp_p is not None:
            fx3_cp_bytes = read_file(fx3_cp_p, 32 * 1024 * 1024)
            fx6_cp_bytes = read_file(fx6_cp_p, 32 * 1024 * 1024)
            found_fx3_cp = _scan_symbols(fx3_cp_bytes, cpapp_syms)
            found_fx6_cp = _scan_symbols(fx6_cp_bytes, cpapp_syms)
            require(len(found_fx3_cp) == len(cpapp_syms), "FX3 cpapp-b.bin missing expected IMX510/Hall/Gyro/Defect anchors")
            require(len(found_fx6_cp) == len(cpapp_syms), "FX6 cpapp-b.bin missing expected IMX510/Hall/Gyro/Defect anchors")
            fx3_cp_len = len(fx3_cp_bytes)
            fx3_cp_sha = sha256(fx3_cp_bytes).hexdigest()
            fx6_cp_len = len(fx6_cp_bytes)
            fx6_cp_sha = sha256(fx6_cp_bytes).hexdigest()
            cp_inspected = True
        else:
            found_fx3_cp = tuple(s.decode("ascii") for s in cpapp_syms)
            found_fx6_cp = tuple(s.decode("ascii") for s in cpapp_syms)
            fx3_cp_len = PINNED_FX3_CPAPP_B_BYTES
            fx3_cp_sha = PINNED_FX3_CPAPP_B_SHA256
            fx6_cp_len = PINNED_FX6_CPAPP_B_BYTES
            fx6_cp_sha = PINNED_FX6_CPAPP_B_SHA256
            cp_inspected = False
    else:
        mode = "CLEAN_ROOM_SYNTHETIC"
        fx3_libbk_len = PINNED_FX3_LIBBACKUP_BYTES
        fx3_libbk_sha = PINNED_FX3_LIBBACKUP_SHA256
        fx6_libbk_len = PINNED_FX6_LIBBACKUP_BYTES
        fx6_libbk_sha = PINNED_FX6_LIBBACKUP_SHA256
        fx3_bko_len = PINNED_FX3_BACKUP_KO_BYTES
        fx3_bko_sha = PINNED_FX3_BACKUP_KO_SHA256
        fx3_appfw_len = PINNED_FX3_APPFW_BYTES
        fx3_appfw_sha = PINNED_FX3_APPFW_SHA256
        fx6_appfw_len = PINNED_FX6_APPFW_BYTES
        fx6_appfw_sha = PINNED_FX6_APPFW_SHA256
        fx3_cp_len = PINNED_FX3_CPAPP_B_BYTES
        fx3_cp_sha = PINNED_FX3_CPAPP_B_SHA256
        fx6_cp_len = PINNED_FX6_CPAPP_B_BYTES
        fx6_cp_sha = PINNED_FX6_CPAPP_B_SHA256
        found_fx3_libbk = tuple(s.decode("ascii") for s in fx3_libbk_syms)
        found_fx6_libbk = tuple(s.decode("ascii") for s in fx6_libbk_syms)
        found_fx3_bko = tuple(s.decode("ascii") for s in fx3_bko_syms)
        found_fx3_appfw = tuple(s.decode("ascii") for s in fx3_appfw_syms)
        found_fx6_appfw = tuple(s.decode("ascii") for s in fx6_appfw_syms)
        found_fx3_cp = tuple(s.decode("ascii") for s in cpapp_syms)
        found_fx6_cp = tuple(s.decode("ascii") for s in cpapp_syms)
        cp_inspected = False

    cross_sku_distinct = (
        (fx3_libbk_sha != fx6_libbk_sha)
        and (fx3_appfw_sha != fx6_appfw_sha)
        and (fx3_cp_sha != fx6_cp_sha)
    )
    cp_mode = mode if cp_inspected else "CLEAN_ROOM_SYNTHETIC"

    artifacts = (
        FactoryCalDonorArtifactDigest(
            label="fx3_v702_libbackup_so",
            relpath=DONOR_FX3_LIBBACKUP_RELPATH,
            source_mode=mode,
            byte_length=fx3_libbk_len,
            sha256=fx3_libbk_sha,
            inspected=(mode == "LOCAL_DONOR_O_RDONLY"),
            symbols_verified=found_fx3_libbk,
            details="FX3 v7.02 libbackup.so NVS/setting attribute backup router",
        ),
        FactoryCalDonorArtifactDigest(
            label="fx6_v601_libbackup_so",
            relpath=DONOR_FX6_LIBBACKUP_RELPATH,
            source_mode=mode,
            byte_length=fx6_libbk_len,
            sha256=fx6_libbk_sha,
            inspected=(mode == "LOCAL_DONOR_O_RDONLY"),
            symbols_verified=found_fx6_libbk,
            details="FX6 v6.01 cross-SKU libbackup.so NVS/setting attribute router",
        ),
        FactoryCalDonorArtifactDigest(
            label="fx3_v702_backup_ko",
            relpath=DONOR_FX3_BACKUP_KO_RELPATH,
            source_mode=mode,
            byte_length=fx3_bko_len,
            sha256=fx3_bko_sha,
            inspected=(mode == "LOCAL_DONOR_O_RDONLY"),
            symbols_verified=found_fx3_bko,
            details="FX3 v7.02 backup.ko kernel NVS/Backup.bin checksum & SENSER sync driver",
        ),
        FactoryCalDonorArtifactDigest(
            label="fx3_v702_appfw_so",
            relpath=DONOR_FX3_APPFW_RELPATH,
            source_mode=mode,
            byte_length=fx3_appfw_len,
            sha256=fx3_appfw_sha,
            inspected=(mode == "LOCAL_DONOR_O_RDONLY"),
            symbols_verified=found_fx3_appfw,
            details="FX3 v7.02 appFw.so AP backup, gyro & SteadyShot calibration consumer",
        ),
        FactoryCalDonorArtifactDigest(
            label="fx6_v601_appfw_so",
            relpath=DONOR_FX6_APPFW_RELPATH,
            source_mode=mode,
            byte_length=fx6_appfw_len,
            sha256=fx6_appfw_sha,
            inspected=(mode == "LOCAL_DONOR_O_RDONLY"),
            symbols_verified=found_fx6_appfw,
            details="FX6 v6.01 cross-SKU appFw.so adjust/senser calibration consumer",
        ),
        FactoryCalDonorArtifactDigest(
            label="fx3_v702_cpapp_b_bin",
            relpath=DONOR_FX3_CPAPP_B_RELPATH,
            source_mode=cp_mode,
            byte_length=fx3_cp_len,
            sha256=fx3_cp_sha,
            inspected=cp_inspected,
            symbols_verified=found_fx3_cp,
            details="FX3 v7.02 CXD90058 cpapp-b.bin IMX510/DefectAdj/Hall/KDGyro RTOS firmware",
        ),
        FactoryCalDonorArtifactDigest(
            label="fx6_v601_cpapp_b_bin",
            relpath=DONOR_FX6_CPAPP_B_RELPATH,
            source_mode=cp_mode,
            byte_length=fx6_cp_len,
            sha256=fx6_cp_sha,
            inspected=cp_inspected,
            symbols_verified=found_fx6_cp,
            details="FX6 v6.01 cross-SKU cpapp-b.bin IMX510/Hall/KDGyro RTOS firmware",
        ),
    )

    snap_payload = {
        "mode": mode,
        "include_cpapp": include_cpapp,
        "fx3_libbk_sha": fx3_libbk_sha,
        "fx6_libbk_sha": fx6_libbk_sha,
        "fx3_bko_sha": fx3_bko_sha,
        "fx3_appfw_sha": fx3_appfw_sha,
        "fx6_appfw_sha": fx6_appfw_sha,
        "fx3_cp_sha": fx3_cp_sha,
        "fx6_cp_sha": fx6_cp_sha,
    }
    return DonorFactoryCalSnapshot(
        verification_mode=mode,
        read_only_access=READ_ONLY_DONOR_ACCESS,
        include_cpapp=include_cpapp,
        fx3_libbackup_sha256=fx3_libbk_sha,
        fx6_libbackup_sha256=fx6_libbk_sha,
        fx3_backup_ko_sha256=fx3_bko_sha,
        fx3_appfw_sha256=fx3_appfw_sha,
        fx6_appfw_sha256=fx6_appfw_sha,
        fx3_cpapp_b_sha256=fx3_cp_sha,
        fx6_cpapp_b_sha256=fx6_cp_sha,
        cross_sku_distinct=cross_sku_distinct,
        artifacts=artifacts,
        snapshot_sha256=_canonical_sha256(snap_payload),
    )


# ---------------------------------------------------------------------------
# Pillar A — Per-Body Factory Calibration (`nvs` / `adj` / `cnflasha`)
# Triple-Copy SHA-256 Parity & Cross-Serial Donor Transplant Firewall
# ---------------------------------------------------------------------------


def build_synthetic_factory_cal_identity(
    seed: str = "fx3-body-alpha",
    *,
    sku_code: str = FX3_CAL_SKU_CODE,
    model_id: int = FX3_CAL_MODEL_ID,
) -> FactoryCalTargetIdentity:
    """Build a synthetic clean-room camera identity using hashed opaque IDs (never raw serials)."""
    return FactoryCalTargetIdentity(
        sku_code=sku_code,
        model_id=model_id,
        body_serial_hash=sha256(f"synthetic-body-serial:{sku_code}:{seed}".encode("utf-8")).hexdigest(),
        board_uid_hash=sha256(f"synthetic-board-uid:{sku_code}:{seed}".encode("utf-8")).hexdigest(),
    )


def build_synthetic_factory_cal_manifest(
    target_identity: FactoryCalTargetIdentity,
    *,
    manifest_id: str = "tier0-factory-cal-manifest-v1",
    donor_identity: Optional[FactoryCalTargetIdentity] = None,
    matching_copies_by_partition: Optional[Mapping[str, int]] = None,
    requested_operations: Sequence[str] = ("verify_parity_readonly",),
    read_private_key_bytes_requested: int = 0,
    write_bytes_requested: int = 0,
) -> FactoryCalRestoreManifest:
    """Build a synthetic clean-room Tier-0 factory-cal manifest for `nvs` / `adj` / `cnflasha`."""
    source_id = target_identity if donor_identity is None else donor_identity
    counts = dict(matching_copies_by_partition or {})
    default_sizes = {"nvs": 262144, "adj": 524288, "cnflasha": 1048576}
    copies: List[FactoryCalCopyDigest] = []

    for part in FACTORY_CAL_PARTITIONS:
        desired = counts.get(part, 3)
        canonical_sha = sha256(
            f"synthetic-cal:{part}:{source_id.body_serial_hash}:{source_id.board_uid_hash}".encode("utf-8")
        ).hexdigest()
        for idx, slot in enumerate(FACTORY_CAL_TRIPLE_COPY_SLOTS):
            if idx < desired:
                copy_sha = canonical_sha
                blank = False
            else:
                copy_sha = sha256(f"corrupt:{part}:{idx}:{source_id.body_serial_hash}".encode("utf-8")).hexdigest()
                blank = False
            copies.append(
                FactoryCalCopyDigest(
                    partition_name=part,
                    copy_slot=slot,
                    media_location=f"archive_media_{idx + 1}/{slot}/{part}.sha256",
                    byte_length=default_sizes[part],
                    sha256=copy_sha,
                    blank_or_erased=blank,
                    present=(desired > 0 or idx == 0),
                )
            )

    return FactoryCalRestoreManifest(
        manifest_id=manifest_id,
        target_sku_code=source_id.sku_code,
        target_model_id=source_id.model_id,
        body_serial_hash=source_id.body_serial_hash,
        board_uid_hash=source_id.board_uid_hash,
        partition_copies=tuple(copies),
        requested_operations=tuple(requested_operations),
        read_private_key_bytes_requested=read_private_key_bytes_requested,
        write_bytes_requested=write_bytes_requested,
    )


def audit_cnflasha_key_vault_operation(
    operation: str,
    *,
    target_partition: str = "cnflasha",
    read_private_key_bytes_requested: int = 0,
    write_bytes_requested: int = 0,
) -> CnflashaVaultDecision:
    """Fail-closed firewall blocking any `cnflasha` modification or raw private-key extraction."""
    raw_op = (operation or "").strip()
    lower = raw_op.lower()
    part_lower = (target_partition or "").strip().lower()

    is_cnflasha_verb = any(verb in lower for verb in FORBIDDEN_CNFLASHA_OPERATION_VERBS)
    touches_key_material = any(
        tok in lower
        for tok in ("private_key", "asymmetric_key", "rsa_key", "ecdsa_key", "key_vault", "aes_key", "xts_key")
    ) and any(act in lower for act in ("read", "dump", "extract", "export", "write", "patch", "erase"))
    writes_cnflasha = (part_lower == "cnflasha") and (
        write_bytes_requested > 0
        or any(w in lower for w in ("write", "flash", "erase", "patch", "overwrite", "format", "modify", "dd"))
    )
    reads_private_key = read_private_key_bytes_requested > 0

    vault_hazard = is_cnflasha_verb or touches_key_material or writes_cnflasha or reads_private_key
    error_codes: List[str] = []
    errors: List[str] = []

    if vault_hazard:
        error_codes.append(BLOCKED_CNFLASHA_KEY_VAULT_WRITE_OR_EXTRACTION)
        errors.append(
            f"Blocked cnflasha key-vault write or asymmetric key extraction "
            f"(op='{raw_op[:80]}', partition='{target_partition}', "
            f"key_bytes_req={read_private_key_bytes_requested}, write_bytes_req={write_bytes_requested})."
        )
    elif write_bytes_requested > 0 or any(verb in lower for verb in FORBIDDEN_FACTORY_CAL_WRITE_VERBS):
        error_codes.append(ERR_FACTORY_CAL_MUTATION_FORBIDDEN)
        errors.append(
            f"Persistent factory-cal mutation blocked under read-only safety lock (op='{raw_op[:80]}')."
        )

    allowed = (not vault_hazard) and (len(errors) == 0)
    return CnflashaVaultDecision(
        allowed=allowed,
        status=(
            BLOCKED_CNFLASHA_KEY_VAULT_WRITE_OR_EXTRACTION
            if vault_hazard
            else ("ALLOWED_READONLY_PARITY_AUDIT" if allowed else "BLOCKED_READONLY_POLICY")
        ),
        operation=raw_op,
        target_partition=target_partition,
        read_private_key_bytes_requested=read_private_key_bytes_requested,
        write_bytes_requested=write_bytes_requested,
        private_key_bytes_read=PRIVATE_KEY_BYTES_READ,
        factory_cal_mutation_bytes=FACTORY_CAL_MUTATION_BYTES,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        error_codes=tuple(error_codes),
        errors=tuple(errors),
    )


def verify_factory_cal_triple_parity_and_firewall(
    target_identity: FactoryCalTargetIdentity,
    restore_manifest: FactoryCalRestoreManifest,
    *,
    scenario_id: str = "CUSTOM_FACTORY_CAL_FIREWALL",
) -> FactoryCalFirewallReport:
    """Verify per-body factory calibration identity, 2-of-3 Tier-0 SHA-256 parity, and cnflasha lock."""
    error_codes: List[str] = []
    errors: List[str] = []

    def _add(code: str, msg: str) -> None:
        if code not in error_codes:
            error_codes.append(code)
        errors.append(msg)

    # 1. Cross-SKU & Cross-Serial Donor Transplant Firewall
    if (
        target_identity.sku_code != FX3_CAL_SKU_CODE
        or restore_manifest.target_sku_code != FX3_CAL_SKU_CODE
        or target_identity.model_id != FX3_CAL_MODEL_ID
        or restore_manifest.target_model_id != FX3_CAL_MODEL_ID
    ):
        _add(
            ERR_FACTORY_CAL_SKU_MISMATCH,
            f"Cross-SKU factory calibration manifest rejected "
            f"(target={target_identity.sku_code}/0x{target_identity.model_id:08x}, "
            f"manifest={restore_manifest.target_sku_code}/0x{restore_manifest.target_model_id:08x}).",
        )

    if (
        not _is_valid_sha256_hex(target_identity.body_serial_hash)
        or not _is_valid_sha256_hex(target_identity.board_uid_hash)
        or not _is_valid_sha256_hex(restore_manifest.body_serial_hash)
        or not _is_valid_sha256_hex(restore_manifest.board_uid_hash)
    ):
        _add(
            BLOCKED_CROSS_SERIAL_FACTORY_CAL_TRANSPLANT,
            "Missing or malformed 64-hex body_serial_hash / board_uid_hash identity anchor.",
        )
    elif (
        restore_manifest.body_serial_hash != target_identity.body_serial_hash
        or restore_manifest.board_uid_hash != target_identity.board_uid_hash
    ):
        _add(
            BLOCKED_CROSS_SERIAL_FACTORY_CAL_TRANSPLANT,
            "Cross-serial donor calibration transplant blocked: manifest body_serial_hash/board_uid_hash "
            "does not match target camera Tier-0 identity.",
        )

    # 2. Triple-Copy SHA-256 Parity Quorum (>= 2 independent matching copies per partition)
    parity_statuses: List[PartitionParityStatus] = []
    for part in FACTORY_CAL_PARTITIONS:
        part_copies = [
            c
            for c in restore_manifest.partition_copies
            if c.partition_name == part
            and c.present
            and (not c.blank_or_erased)
            and c.byte_length > 0
            and _is_valid_sha256_hex(c.sha256)
        ]
        by_sha: Dict[str, List[FactoryCalCopyDigest]] = {}
        for c in part_copies:
            by_sha.setdefault(c.sha256, []).append(c)

        best_sha = ""
        best_independent = 0
        for sha_val, items in by_sha.items():
            # Count distinct independent copy slots AND media locations
            indep_slots = len({(it.copy_slot, it.media_location) for it in items})
            distinct_media = len({it.media_location for it in items})
            indep_count = min(indep_slots, distinct_media)
            if indep_count > best_independent:
                best_independent = indep_count
                best_sha = sha_val

        quorum_ok = best_independent >= MIN_TRIPLE_PARITY_MATCHING_COPIES
        if not quorum_ok:
            _add(
                BLOCKED_MISSING_TIER0_FACTORY_CAL_TRIPLE_PARITY,
                f"Partition '{part}' has only {best_independent} independent matching SHA-256 copies "
                f"(minimum {MIN_TRIPLE_PARITY_MATCHING_COPIES} of 3 required).",
            )
        parity_statuses.append(
            PartitionParityStatus(
                partition_name=part,
                total_copies_present=len(part_copies),
                independent_matching_copies=best_independent,
                consensus_sha256=best_sha,
                quorum_met=quorum_ok,
            )
        )

    # 3. cnflasha Key-Vault Write & Asymmetric Private-Key Extraction Firewall
    if restore_manifest.read_private_key_bytes_requested > 0 or restore_manifest.write_bytes_requested > 0:
        dec = audit_cnflasha_key_vault_operation(
            ",".join(restore_manifest.requested_operations) or "manifest_request",
            target_partition="cnflasha",
            read_private_key_bytes_requested=restore_manifest.read_private_key_bytes_requested,
            write_bytes_requested=restore_manifest.write_bytes_requested,
        )
        for code, msg in zip(dec.error_codes, dec.errors):
            _add(code, msg)

    for op in restore_manifest.requested_operations:
        target_part = "cnflasha" if "cnflasha" in op.lower() else "factory_cal"
        dec = audit_cnflasha_key_vault_operation(op, target_partition=target_part)
        for code, msg in zip(dec.error_codes, dec.errors):
            _add(code, msg)

    cross_serial_blocked = BLOCKED_CROSS_SERIAL_FACTORY_CAL_TRANSPLANT in error_codes
    missing_parity_blocked = BLOCKED_MISSING_TIER0_FACTORY_CAL_TRIPLE_PARITY in error_codes
    cnflasha_blocked = BLOCKED_CNFLASHA_KEY_VAULT_WRITE_OR_EXTRACTION in error_codes

    passed = len(error_codes) == 0
    status = STATUS_VERIFIED_FACTORY_CAL_PARITY if passed else STATUS_REJECTED_FACTORY_CAL_FIREWALL

    digest_payload = {
        "scenario_id": scenario_id,
        "status": status,
        "passed": passed,
        "cross_serial_blocked": cross_serial_blocked,
        "missing_parity_blocked": missing_parity_blocked,
        "cnflasha_blocked": cnflasha_blocked,
        "error_codes": error_codes,
        "parity": [
            {
                "part": p.partition_name,
                "indep": p.independent_matching_copies,
                "quorum": p.quorum_met,
            }
            for p in parity_statuses
        ],
    }
    return FactoryCalFirewallReport(
        passed=passed,
        status=status,
        scenario_id=scenario_id,
        target_sku_code=target_identity.sku_code,
        manifest_sku_code=restore_manifest.target_sku_code,
        cross_serial_blocked=cross_serial_blocked,
        missing_triple_parity_blocked=missing_parity_blocked,
        cnflasha_vault_blocked=cnflasha_blocked,
        triple_parity_verified=(not missing_parity_blocked) and all(p.quorum_met for p in parity_statuses),
        identity_match_verified=(not cross_serial_blocked) and (ERR_FACTORY_CAL_SKU_MISMATCH not in error_codes),
        cnflasha_vault_protected=(not cnflasha_blocked) and (PRIVATE_KEY_BYTES_READ == 0),
        partition_parity=tuple(parity_statuses),
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        factory_cal_mutation_bytes=FACTORY_CAL_MUTATION_BYTES,
        private_key_bytes_read=PRIVATE_KEY_BYTES_READ,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        error_codes=tuple(error_codes),
        errors=tuple(errors),
        report_sha256=_canonical_sha256(digest_payload),
    )


def run_factory_cal_6_scenario_firewall() -> FactoryCal6ScenarioSuiteResult:
    """Execute the 6 canonical per-body factory calibration & cross-serial firewall scenarios."""
    target = build_synthetic_factory_cal_identity("fx3-body-alpha")
    donor_other = build_synthetic_factory_cal_identity("fx3-body-beta-donor")

    # F1: Healthy same-body 3/3 triple parity
    r1 = verify_factory_cal_triple_parity_and_firewall(
        target,
        build_synthetic_factory_cal_manifest(target, manifest_id="f1-healthy-3of3"),
        scenario_id=FACTORY_CAL_FIREWALL_SCENARIO_IDS[0],
    )
    # F2: Healthy 2/3 quorum survives single copy corruption across nvs/adj/cnflasha
    r2 = verify_factory_cal_triple_parity_and_firewall(
        target,
        build_synthetic_factory_cal_manifest(
            target,
            manifest_id="f2-healthy-2of3",
            matching_copies_by_partition={"nvs": 2, "adj": 2, "cnflasha": 2},
        ),
        scenario_id=FACTORY_CAL_FIREWALL_SCENARIO_IDS[1],
    )
    # F3: Cross-serial donor transplant blocked
    r3 = verify_factory_cal_triple_parity_and_firewall(
        target,
        build_synthetic_factory_cal_manifest(
            target,
            manifest_id="f3-cross-serial",
            donor_identity=donor_other,
        ),
        scenario_id=FACTORY_CAL_FIREWALL_SCENARIO_IDS[2],
    )
    # F4: Missing Tier-0 triple parity (< 2 matching copies)
    r4 = verify_factory_cal_triple_parity_and_firewall(
        target,
        build_synthetic_factory_cal_manifest(
            target,
            manifest_id="f4-missing-parity",
            matching_copies_by_partition={"nvs": 1, "adj": 3, "cnflasha": 1},
        ),
        scenario_id=FACTORY_CAL_FIREWALL_SCENARIO_IDS[3],
    )
    # F5: cnflasha key-vault write attempt blocked
    r5 = verify_factory_cal_triple_parity_and_firewall(
        target,
        build_synthetic_factory_cal_manifest(
            target,
            manifest_id="f5-cnflasha-write",
            requested_operations=("write_cnflasha",),
            write_bytes_requested=4096,
        ),
        scenario_id=FACTORY_CAL_FIREWALL_SCENARIO_IDS[4],
    )
    # F6: cnflasha raw asymmetric private-key extraction attempt blocked
    r6 = verify_factory_cal_triple_parity_and_firewall(
        target,
        build_synthetic_factory_cal_manifest(
            target,
            manifest_id="f6-cnflasha-extract",
            requested_operations=("extract_cnflasha", "read_asymmetric_key"),
            read_private_key_bytes_requested=256,
        ),
        scenario_id=FACTORY_CAL_FIREWALL_SCENARIO_IDS[5],
    )

    vault_write_dec = audit_cnflasha_key_vault_operation("write_cnflasha", write_bytes_requested=4096)
    vault_extract_dec = audit_cnflasha_key_vault_operation(
        "read_asymmetric_key", read_private_key_bytes_requested=256
    )

    results = (r1, r2, r3, r4, r5, r6)
    suite_errors: List[str] = []
    passed_count = 0

    if r1.passed and r1.triple_parity_verified and r1.identity_match_verified and r1.cnflasha_vault_protected:
        passed_count += 1
    else:
        suite_errors.append(f"F1 failed: {r1.error_codes}")

    if r2.passed and r2.triple_parity_verified:
        passed_count += 1
    else:
        suite_errors.append(f"F2 failed: {r2.error_codes}")

    if (not r3.passed) and r3.cross_serial_blocked and (BLOCKED_CROSS_SERIAL_FACTORY_CAL_TRANSPLANT in r3.error_codes):
        passed_count += 1
    else:
        suite_errors.append("F3 failed to detect BLOCKED_CROSS_SERIAL_FACTORY_CAL_TRANSPLANT")

    if (not r4.passed) and r4.missing_triple_parity_blocked and (BLOCKED_MISSING_TIER0_FACTORY_CAL_TRIPLE_PARITY in r4.error_codes):
        passed_count += 1
    else:
        suite_errors.append("F4 failed to detect BLOCKED_MISSING_TIER0_FACTORY_CAL_TRIPLE_PARITY")

    if (not r5.passed) and r5.cnflasha_vault_blocked and (BLOCKED_CNFLASHA_KEY_VAULT_WRITE_OR_EXTRACTION in r5.error_codes):
        passed_count += 1
    else:
        suite_errors.append("F5 failed to detect BLOCKED_CNFLASHA_KEY_VAULT_WRITE_OR_EXTRACTION on write")

    if (not r6.passed) and r6.cnflasha_vault_blocked and (BLOCKED_CNFLASHA_KEY_VAULT_WRITE_OR_EXTRACTION in r6.error_codes):
        passed_count += 1
    else:
        suite_errors.append("F6 failed to detect BLOCKED_CNFLASHA_KEY_VAULT_WRITE_OR_EXTRACTION on extract")

    for label, dec in (("write", vault_write_dec), ("extract", vault_extract_dec)):
        if (
            dec.allowed
            or BLOCKED_CNFLASHA_KEY_VAULT_WRITE_OR_EXTRACTION not in dec.error_codes
            or dec.private_key_bytes_read != 0
            or dec.factory_cal_mutation_bytes != 0
            or dec.physical_device_writes != 0
        ):
            suite_errors.append(f"cnflasha firewall {label} failed zero-read/zero-write invariant")

    for r in results:
        if (
            r.physical_device_writes != 0
            or r.factory_cal_mutation_bytes != 0
            or r.private_key_bytes_read != 0
            or r.persistent_emmc_writes_authorized
            or r.persistent_write_release
        ):
            suite_errors.append(f"{r.scenario_id} violated zero-write/zero-key-read invariant")

    all_ok = len(suite_errors) == 0 and passed_count == len(FACTORY_CAL_FIREWALL_SCENARIO_IDS)
    suite_payload = {
        "scenarios": [
            {
                "id": r.scenario_id,
                "status": r.status,
                "passed": r.passed,
                "error_codes": list(r.error_codes),
            }
            for r in results
        ]
    }
    return FactoryCal6ScenarioSuiteResult(
        passed=all_ok,
        status=STATUS_VERIFIED_FACTORY_CAL_GUARD if all_ok else STATUS_FAIL_FACTORY_CAL_GUARD,
        scenarios_passed=passed_count,
        scenarios_total=len(FACTORY_CAL_FIREWALL_SCENARIO_IDS),
        scenario_results=results,
        vault_write_decision=vault_write_dec,
        vault_extract_decision=vault_extract_dec,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        factory_cal_mutation_bytes=FACTORY_CAL_MUTATION_BYTES,
        private_key_bytes_read=PRIVATE_KEY_BYTES_READ,
        errors=tuple(suite_errors),
        suite_sha256=_canonical_sha256(suite_payload),
    )


# ---------------------------------------------------------------------------
# Pillar B — IMX510 Defect-Pixel Map (Dual-Base ISO 800/12800 Column-ADC) &
# 5-Axis IBIS Hall-Sensor / IMU Gyro Temperature-Bias Table Verifier
# ---------------------------------------------------------------------------


def compute_imx510_cal_crc32(
    *,
    body_serial_hash: str,
    sensor_model: str,
    active_width: int,
    active_height: int,
    defect_pixels: Sequence[Imx510DefectPixelCoord],
    iso_800_profile: Imx510BaseIsoAdcProfile,
    iso_12800_profile: Imx510BaseIsoAdcProfile,
) -> int:
    payload = {
        "body_serial_hash": body_serial_hash,
        "sensor_model": sensor_model,
        "active_width": active_width,
        "active_height": active_height,
        "defect_pixels": [[p.x, p.y, p.defect_kind] for p in defect_pixels],
        "iso_800": {
            "base_iso": iso_800_profile.base_iso,
            "analog_gain": round(float(iso_800_profile.analog_gain), 6),
            "dark_current_offset_lsb": round(float(iso_800_profile.dark_current_offset_lsb), 6),
            "column_fpn_offsets_lsb": [round(float(v), 6) for v in iso_800_profile.column_fpn_offsets_lsb],
        },
        "iso_12800": {
            "base_iso": iso_12800_profile.base_iso,
            "analog_gain": round(float(iso_12800_profile.analog_gain), 6),
            "dark_current_offset_lsb": round(float(iso_12800_profile.dark_current_offset_lsb), 6),
            "column_fpn_offsets_lsb": [round(float(v), 6) for v in iso_12800_profile.column_fpn_offsets_lsb],
        },
    }
    return zlib.crc32(_canonical_json_bytes(payload)) & 0xFFFFFFFF


def compute_ibis_imu_cal_crc32(
    *,
    body_serial_hash: str,
    temp_min_c: float,
    temp_max_c: float,
    ibis_axes: Sequence[IbisAxisHallCalEntry],
    imu_gyro_polys: Sequence[ImuGyroTempBiasPolyEntry],
) -> int:
    payload = {
        "body_serial_hash": body_serial_hash,
        "temp_min_c": round(float(temp_min_c), 4),
        "temp_max_c": round(float(temp_max_c), 4),
        "ibis_axes": [
            {
                "axis_name": ax.axis_name,
                "hall_zero_center_adc": ax.hall_zero_center_adc,
                "positive_stroke_limit_adc": ax.positive_stroke_limit_adc,
                "negative_stroke_limit_adc": ax.negative_stroke_limit_adc,
            }
            for ax in ibis_axes
        ],
        "imu_gyro_polys": [
            {
                "axis_name": g.axis_name,
                "c0_dps": round(float(g.c0_dps), 6),
                "c1_dps_per_c": round(float(g.c1_dps_per_c), 6),
                "c2_dps_per_c2": round(float(g.c2_dps_per_c2), 6),
            }
            for g in imu_gyro_polys
        ],
    }
    return zlib.crc32(_canonical_json_bytes(payload)) & 0xFFFFFFFF


def build_synthetic_imx510_cal_table(
    body_serial_hash: str,
    *,
    defect_pixels: Optional[Sequence[Imx510DefectPixelCoord]] = None,
    iso_800_dark_lsb: float = 12.5,
    iso_12800_dark_lsb: float = 28.0,
    iso_12800_col_fpn_peak_lsb: float = 3.2,
    corrupt_crc32: bool = False,
) -> Imx510DefectAndAdcCalTable:
    pixels = tuple(defect_pixels) if defect_pixels is not None else (
        Imx510DefectPixelCoord(120, 48, 1),
        Imx510DefectPixelCoord(2132, 48, 2),
        Imx510DefectPixelCoord(4096, 612, 1),
        Imx510DefectPixelCoord(880, 1204, 1),
        Imx510DefectPixelCoord(3420, 1890, 2),
        Imx510DefectPixelCoord(4263, 2407, 1),
    )
    iso_800_cols = tuple(round(((i % 5) - 2) * 0.45, 4) for i in range(IMX510_MIN_COLUMN_FPN_BANKS))
    iso_12800_cols = tuple(
        round(iso_12800_col_fpn_peak_lsb if i == 0 else ((i % 7) - 3) * 0.5, 4)
        for i in range(IMX510_MIN_COLUMN_FPN_BANKS)
    )
    prof_800 = Imx510BaseIsoAdcProfile(
        base_iso=800,
        analog_gain=1.0,
        dark_current_offset_lsb=iso_800_dark_lsb,
        column_fpn_offsets_lsb=iso_800_cols,
    )
    prof_12800 = Imx510BaseIsoAdcProfile(
        base_iso=12800,
        analog_gain=16.0,
        dark_current_offset_lsb=iso_12800_dark_lsb,
        column_fpn_offsets_lsb=iso_12800_cols,
    )
    crc = compute_imx510_cal_crc32(
        body_serial_hash=body_serial_hash,
        sensor_model="IMX510",
        active_width=IMX510_ACTIVE_WIDTH,
        active_height=IMX510_ACTIVE_HEIGHT,
        defect_pixels=pixels,
        iso_800_profile=prof_800,
        iso_12800_profile=prof_12800,
    )
    if corrupt_crc32:
        crc ^= 0xDEADBEEF
    return Imx510DefectAndAdcCalTable(
        body_serial_hash=body_serial_hash,
        sensor_model="IMX510",
        active_width=IMX510_ACTIVE_WIDTH,
        active_height=IMX510_ACTIVE_HEIGHT,
        defect_pixels=pixels,
        iso_800_profile=prof_800,
        iso_12800_profile=prof_12800,
        crc32=crc,
    )


def build_synthetic_ibis_imu_cal_table(
    body_serial_hash: str,
    *,
    hall_zero_overrides: Optional[Mapping[str, int]] = None,
    temp_min_c: float = IMU_TEMP_MIN_C,
    temp_max_c: float = IMU_TEMP_MAX_C,
    pitch_c1_override: Optional[float] = None,
    corrupt_crc32: bool = False,
) -> IbisAndImuCalTable:
    overrides = dict(hall_zero_overrides or {})
    default_zeros = {"pitch": 2044, "yaw": 2052, "roll": 2048, "x": 2039, "y": 2056}
    ibis_axes = tuple(
        IbisAxisHallCalEntry(
            axis_name=ax,
            hall_zero_center_adc=overrides.get(ax, default_zeros[ax]),
            positive_stroke_limit_adc=640,
            negative_stroke_limit_adc=640,
        )
        for ax in IBIS_5_AXES
    )
    imu_polys = tuple(
        ImuGyroTempBiasPolyEntry(
            axis_name=ax,
            c0_dps=0.12 if ax != "roll" else -0.08,
            c1_dps_per_c=(
                pitch_c1_override
                if (ax == "pitch" and pitch_c1_override is not None)
                else 0.0045
            ),
            c2_dps_per_c2=0.00012,
        )
        for ax in ("pitch", "yaw", "roll")
    )
    crc = compute_ibis_imu_cal_crc32(
        body_serial_hash=body_serial_hash,
        temp_min_c=temp_min_c,
        temp_max_c=temp_max_c,
        ibis_axes=ibis_axes,
        imu_gyro_polys=imu_polys,
    )
    if corrupt_crc32:
        crc ^= 0xCAFEBABE
    return IbisAndImuCalTable(
        body_serial_hash=body_serial_hash,
        temp_min_c=temp_min_c,
        temp_max_c=temp_max_c,
        ibis_axes=ibis_axes,
        imu_gyro_polys=imu_polys,
        crc32=crc,
    )


def verify_imx510_and_ibis_cal_tables(
    target_identity: FactoryCalTargetIdentity,
    imx510_table: Imx510DefectAndAdcCalTable,
    ibis_imu_table: IbisAndImuCalTable,
    *,
    scenario_id: str = "CUSTOM_SENSOR_IBIS_CAL_AUDIT",
) -> SensorIbisCalVerificationReport:
    """Verify clean-room structural invariants and CRC32 for IMX510 & 5-axis IBIS/IMU tables."""
    error_codes: List[str] = []
    errors: List[str] = []

    def _add(code: str, msg: str) -> None:
        if code not in error_codes:
            error_codes.append(code)
        errors.append(msg)

    # Body serial binding across target, IMX510 table, and IBIS/IMU table
    body_bind_ok = (
        _is_valid_sha256_hex(target_identity.body_serial_hash)
        and imx510_table.body_serial_hash == target_identity.body_serial_hash
        and ibis_imu_table.body_serial_hash == target_identity.body_serial_hash
    )
    if not body_bind_ok:
        _add(
            ERR_SENSOR_BODY_BINDING_MISMATCH,
            "IMX510 or IBIS/IMU calibration table body_serial_hash does not match target body.",
        )

    # 1. IMX510 Defect-Pixel Map (monotonic row-major within 4264 x 2408)
    imx_bounds_ok = True
    if imx510_table.sensor_model != "IMX510" or imx510_table.active_width != IMX510_ACTIVE_WIDTH or imx510_table.active_height != IMX510_ACTIVE_HEIGHT:
        imx_bounds_ok = False
        _add(
            ERR_IMX510_PIXEL_OUT_OF_BOUNDS,
            f"IMX510 geometry mismatch: got {imx510_table.sensor_model} {imx510_table.active_width}x{imx510_table.active_height}.",
        )

    pix_count = len(imx510_table.defect_pixels)
    if pix_count < IMX510_MIN_DEFECT_PIXELS or pix_count > IMX510_MAX_DEFECT_PIXELS:
        imx_bounds_ok = False
        _add(
            ERR_IMX510_EMPTY_OR_OVERSIZED_DEFECT_MAP,
            f"IMX510 defect pixel count {pix_count} outside [{IMX510_MIN_DEFECT_PIXELS}, {IMX510_MAX_DEFECT_PIXELS}].",
        )

    prev_key: Optional[Tuple[int, int]] = None
    for idx, px in enumerate(imx510_table.defect_pixels):
        if not (0 <= px.x < IMX510_ACTIVE_WIDTH and 0 <= px.y < IMX510_ACTIVE_HEIGHT):
            imx_bounds_ok = False
            _add(
                ERR_IMX510_PIXEL_OUT_OF_BOUNDS,
                f"Defect pixel[{idx}] ({px.x}, {px.y}) outside 4264x2408 IMX510 active array.",
            )
            break
        cur_key = (px.y, px.x)
        if prev_key is not None and cur_key <= prev_key:
            imx_bounds_ok = False
            _add(
                ERR_IMX510_NON_MONOTONIC_COORDINATES,
                f"Defect pixel[{idx}] ({px.x}, {px.y}) violates strict row-major monotonicity after ({prev_key[1]}, {prev_key[0]}).",
            )
            break
        prev_key = cur_key

    # 2. Dual-Base ISO 800 / 12800 Dark-Current & Column-ADC FPN Offsets
    dual_iso_ok = True
    p800 = imx510_table.iso_800_profile
    p128 = imx510_table.iso_12800_profile
    if (p800.base_iso, p128.base_iso) != IMX510_DUAL_BASE_ISOS:
        dual_iso_ok = False
        _add(
            ERR_IMX510_DUAL_ISO_CONFIG_INVALID,
            f"Dual-base ISO pair {(p800.base_iso, p128.base_iso)} != expected {IMX510_DUAL_BASE_ISOS}.",
        )
    if (
        not _is_finite_float(p800.analog_gain)
        or not _is_finite_float(p128.analog_gain)
        or p800.analog_gain < IMX510_ANALOG_GAIN_MIN
        or p128.analog_gain > IMX510_ANALOG_GAIN_MAX
        or p800.analog_gain <= 0
    ):
        dual_iso_ok = False
        _add(ERR_IMX510_DUAL_ISO_CONFIG_INVALID, "Invalid analog gain values in IMX510 dual-ISO profiles.")
    else:
        ratio = p128.analog_gain / p800.analog_gain
        if not (IMX510_DUAL_GAIN_RATIO_MIN <= ratio <= IMX510_DUAL_GAIN_RATIO_MAX):
            dual_iso_ok = False
            _add(
                ERR_IMX510_DUAL_ISO_CONFIG_INVALID,
                f"Dual-gain ratio {ratio:.2f} outside [{IMX510_DUAL_GAIN_RATIO_MIN}, {IMX510_DUAL_GAIN_RATIO_MAX}].",
            )

    for prof in (p800, p128):
        if (
            not _is_finite_float(prof.dark_current_offset_lsb)
            or not (IMX510_DARK_CURRENT_OFFSET_MIN_LSB <= prof.dark_current_offset_lsb <= IMX510_DARK_CURRENT_OFFSET_MAX_LSB)
        ):
            dual_iso_ok = False
            _add(
                ERR_IMX510_ADC_OFFSET_OUT_OF_RANGE,
                f"ISO {prof.base_iso} dark_current_offset_lsb={prof.dark_current_offset_lsb} out of bounds.",
            )
        if len(prof.column_fpn_offsets_lsb) < IMX510_MIN_COLUMN_FPN_BANKS:
            dual_iso_ok = False
            _add(
                ERR_IMX510_ADC_OFFSET_OUT_OF_RANGE,
                f"ISO {prof.base_iso} column_fpn_offsets_lsb length {len(prof.column_fpn_offsets_lsb)} < {IMX510_MIN_COLUMN_FPN_BANKS}.",
            )
        for col_idx, col_off in enumerate(prof.column_fpn_offsets_lsb):
            if (not _is_finite_float(col_off)) or abs(float(col_off)) > IMX510_COLUMN_FPN_OFFSET_ABS_MAX_LSB:
                dual_iso_ok = False
                _add(
                    ERR_IMX510_ADC_OFFSET_OUT_OF_RANGE,
                    f"ISO {prof.base_iso} column_fpn[{col_idx}]={col_off} exceeds +/-{IMX510_COLUMN_FPN_OFFSET_ABS_MAX_LSB} LSB.",
                )
                break

    # 3. IMX510 CRC32 Check
    imx_crc_ok = False
    if dual_iso_ok:
        expected_imx_crc = compute_imx510_cal_crc32(
            body_serial_hash=imx510_table.body_serial_hash,
            sensor_model=imx510_table.sensor_model,
            active_width=imx510_table.active_width,
            active_height=imx510_table.active_height,
            defect_pixels=imx510_table.defect_pixels,
            iso_800_profile=p800,
            iso_12800_profile=p128,
        )
        imx_crc_ok = (imx510_table.crc32 == expected_imx_crc)
        if not imx_crc_ok:
            _add(
                ERR_IMX510_CRC32_MISMATCH,
                f"IMX510 CRC32 mismatch: got 0x{imx510_table.crc32:08x} != expected 0x{expected_imx_crc:08x}.",
            )

    # 4. 5-Axis IBIS Hall-Sensor Zero-Centers & Stroke Bounds
    ibis_ok = True
    seen_axes = tuple(ax.axis_name for ax in ibis_imu_table.ibis_axes)
    if set(seen_axes) != set(IBIS_5_AXES) or len(seen_axes) != len(IBIS_5_AXES):
        ibis_ok = False
        _add(
            ERR_IBIS_AXES_MISMATCH,
            f"IBIS axes {seen_axes} != required 5-axis set {IBIS_5_AXES}.",
        )
    for ax in ibis_imu_table.ibis_axes:
        if not (IBIS_HALL_ZERO_CENTER_MIN <= ax.hall_zero_center_adc <= IBIS_HALL_ZERO_CENTER_MAX):
            ibis_ok = False
            _add(
                ERR_IBIS_HALL_ZERO_OUT_OF_RANGE,
                f"IBIS axis '{ax.axis_name}' Hall zero-center {ax.hall_zero_center_adc} outside [{IBIS_HALL_ZERO_CENTER_MIN}, {IBIS_HALL_ZERO_CENTER_MAX}].",
            )
        if (
            not (IBIS_HALL_STROKE_LIMIT_MIN <= ax.positive_stroke_limit_adc <= IBIS_HALL_STROKE_LIMIT_MAX)
            or not (IBIS_HALL_STROKE_LIMIT_MIN <= ax.negative_stroke_limit_adc <= IBIS_HALL_STROKE_LIMIT_MAX)
            or ax.hall_zero_center_adc + ax.positive_stroke_limit_adc > IBIS_HALL_ADC_MAX
            or ax.hall_zero_center_adc - ax.negative_stroke_limit_adc < 0
        ):
            ibis_ok = False
            _add(
                ERR_IBIS_HALL_ZERO_OUT_OF_RANGE,
                f"IBIS axis '{ax.axis_name}' stroke range overflows 12-bit Hall ADC [0, {IBIS_HALL_ADC_MAX}].",
            )

    # 5. IMU Gyro Temperature-Bias Polynomials over -10°C..+60°C
    imu_ok = True
    if (
        not _is_finite_float(ibis_imu_table.temp_min_c)
        or not _is_finite_float(ibis_imu_table.temp_max_c)
        or ibis_imu_table.temp_min_c > IMU_TEMP_MIN_C
        or ibis_imu_table.temp_max_c < IMU_TEMP_MAX_C
        or ibis_imu_table.temp_min_c >= ibis_imu_table.temp_max_c
    ):
        imu_ok = False
        _add(
            ERR_IMU_TEMP_RANGE_COVERAGE_INVALID,
            f"IMU temperature envelope [{ibis_imu_table.temp_min_c}, {ibis_imu_table.temp_max_c}]C must cover [-10.0, +60.0]C.",
        )

    gyro_axes = tuple(g.axis_name for g in ibis_imu_table.imu_gyro_polys)
    if set(gyro_axes) != {"pitch", "yaw", "roll"} or len(gyro_axes) != 3:
        imu_ok = False
        _add(ERR_IMU_GYRO_BIAS_POLY_OUT_OF_RANGE, f"IMU gyro polynomial axes {gyro_axes} must cover pitch/yaw/roll.")

    for g in ibis_imu_table.imu_gyro_polys:
        if (
            not _is_finite_float(g.c0_dps)
            or not _is_finite_float(g.c1_dps_per_c)
            or not _is_finite_float(g.c2_dps_per_c2)
            or abs(g.c1_dps_per_c) > IMU_GYRO_C1_ABS_MAX_DPS_PER_C
            or abs(g.c2_dps_per_c2) > IMU_GYRO_C2_ABS_MAX_DPS_PER_C2
        ):
            imu_ok = False
            _add(
                ERR_IMU_GYRO_BIAS_POLY_OUT_OF_RANGE,
                f"IMU gyro '{g.axis_name}' temperature coefficients out of bounded range.",
            )
            continue
        for temp_c in (-10.0, 0.0, 25.0, 45.0, 60.0):
            dt = temp_c - IMU_TEMP_REF_C
            bias_dps = g.c0_dps + g.c1_dps_per_c * dt + g.c2_dps_per_c2 * (dt * dt)
            if abs(bias_dps) > IMU_GYRO_BIAS_ABS_MAX_DPS:
                imu_ok = False
                _add(
                    ERR_IMU_GYRO_BIAS_POLY_OUT_OF_RANGE,
                    f"IMU gyro '{g.axis_name}' bias {bias_dps:.3f} dps at {temp_c}C exceeds +/-{IMU_GYRO_BIAS_ABS_MAX_DPS} dps.",
                )
                break

    # 6. IBIS/IMU CRC32 Check
    ibis_crc_ok = False
    if _is_finite_float(ibis_imu_table.temp_min_c) and _is_finite_float(ibis_imu_table.temp_max_c) and all(
        _is_finite_float(g.c0_dps) and _is_finite_float(g.c1_dps_per_c) and _is_finite_float(g.c2_dps_per_c2)
        for g in ibis_imu_table.imu_gyro_polys
    ):
        expected_ibis_crc = compute_ibis_imu_cal_crc32(
            body_serial_hash=ibis_imu_table.body_serial_hash,
            temp_min_c=ibis_imu_table.temp_min_c,
            temp_max_c=ibis_imu_table.temp_max_c,
            ibis_axes=ibis_imu_table.ibis_axes,
            imu_gyro_polys=ibis_imu_table.imu_gyro_polys,
        )
        ibis_crc_ok = (ibis_imu_table.crc32 == expected_ibis_crc)
        if not ibis_crc_ok:
            _add(
                ERR_IBIS_IMU_CRC32_MISMATCH,
                f"IBIS/IMU CRC32 mismatch: got 0x{ibis_imu_table.crc32:08x} != expected 0x{expected_ibis_crc:08x}.",
            )

    passed = len(error_codes) == 0 and body_bind_ok and imx_bounds_ok and dual_iso_ok and imx_crc_ok and ibis_ok and imu_ok and ibis_crc_ok
    status = STATUS_VERIFIED_SENSOR_IBIS_CAL_TABLES if passed else STATUS_REJECTED_SENSOR_IBIS_CAL_TABLES

    digest_payload = {
        "scenario_id": scenario_id,
        "status": status,
        "passed": passed,
        "imx510_crc_ok": imx_crc_ok,
        "ibis_crc_ok": ibis_crc_ok,
        "error_codes": error_codes,
    }
    return SensorIbisCalVerificationReport(
        passed=passed,
        status=status,
        scenario_id=scenario_id,
        imx510_defect_count=pix_count,
        imx510_monotonic_in_bounds=imx_bounds_ok,
        imx510_dual_iso_offsets_bounded=dual_iso_ok,
        imx510_crc32_valid=imx_crc_ok,
        ibis_5axis_hall_zero_bounded=ibis_ok,
        imu_gyro_temp_poly_bounded=imu_ok,
        ibis_imu_crc32_valid=ibis_crc_ok,
        body_serial_binding_valid=body_bind_ok,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        factory_cal_mutation_bytes=FACTORY_CAL_MUTATION_BYTES,
        private_key_bytes_read=PRIVATE_KEY_BYTES_READ,
        error_codes=tuple(error_codes),
        errors=tuple(errors),
        report_sha256=_canonical_sha256(digest_payload),
    )


def run_sensor_ibis_cal_6_scenario_suite() -> SensorIbisCal6ScenarioSuiteResult:
    """Execute the 6 canonical IMX510 defect-pixel/dual-ISO & 5-axis IBIS/IMU verification scenarios."""
    target = build_synthetic_factory_cal_identity("fx3-body-alpha")
    bsh = target.body_serial_hash

    valid_imx = build_synthetic_imx510_cal_table(bsh)
    valid_ibis = build_synthetic_ibis_imu_cal_table(bsh)

    # S1: Healthy IMX510 & 5-axis IBIS/IMU tables
    r1 = verify_imx510_and_ibis_cal_tables(
        target, valid_imx, valid_ibis, scenario_id=SENSOR_IBIS_SCENARIO_IDS[0]
    )
    # S2: IMX510 out-of-bounds (4264, 100) coordinate
    r2 = verify_imx510_and_ibis_cal_tables(
        target,
        build_synthetic_imx510_cal_table(
            bsh,
            defect_pixels=(Imx510DefectPixelCoord(100, 100), Imx510DefectPixelCoord(4264, 100)),
        ),
        valid_ibis,
        scenario_id=SENSOR_IBIS_SCENARIO_IDS[1],
    )
    # S3: IMX510 ISO 12800 column-FPN offset exceeding +/-32 LSB bound
    r3 = verify_imx510_and_ibis_cal_tables(
        target,
        build_synthetic_imx510_cal_table(bsh, iso_12800_col_fpn_peak_lsb=49.5),
        valid_ibis,
        scenario_id=SENSOR_IBIS_SCENARIO_IDS[2],
    )
    # S4: IBIS Hall-sensor zero-center saturated at rail (4090)
    r4 = verify_imx510_and_ibis_cal_tables(
        target,
        valid_imx,
        build_synthetic_ibis_imu_cal_table(bsh, hall_zero_overrides={"yaw": 4090}),
        scenario_id=SENSOR_IBIS_SCENARIO_IDS[3],
    )
    # S5: IMU gyro temperature-bias polynomial diverges at +60C
    r5 = verify_imx510_and_ibis_cal_tables(
        target,
        valid_imx,
        build_synthetic_ibis_imu_cal_table(bsh, pitch_c1_override=0.25),
        scenario_id=SENSOR_IBIS_SCENARIO_IDS[4],
    )
    # S6: Tampered CRC32 on IMX510 & IBIS/IMU calibration tables
    r6 = verify_imx510_and_ibis_cal_tables(
        target,
        build_synthetic_imx510_cal_table(bsh, corrupt_crc32=True),
        build_synthetic_ibis_imu_cal_table(bsh, corrupt_crc32=True),
        scenario_id=SENSOR_IBIS_SCENARIO_IDS[5],
    )

    results = (r1, r2, r3, r4, r5, r6)
    suite_errors: List[str] = []
    passed_count = 0

    if r1.passed and r1.status == STATUS_VERIFIED_SENSOR_IBIS_CAL_TABLES:
        passed_count += 1
    else:
        suite_errors.append(f"S1 failed: {r1.error_codes}")

    if (not r2.passed) and (ERR_IMX510_PIXEL_OUT_OF_BOUNDS in r2.error_codes):
        passed_count += 1
    else:
        suite_errors.append("S2 failed to detect ERR_IMX510_PIXEL_OUT_OF_BOUNDS")

    if (not r3.passed) and (ERR_IMX510_ADC_OFFSET_OUT_OF_RANGE in r3.error_codes):
        passed_count += 1
    else:
        suite_errors.append("S3 failed to detect ERR_IMX510_ADC_OFFSET_OUT_OF_RANGE")

    if (not r4.passed) and (ERR_IBIS_HALL_ZERO_OUT_OF_RANGE in r4.error_codes):
        passed_count += 1
    else:
        suite_errors.append("S4 failed to detect ERR_IBIS_HALL_ZERO_OUT_OF_RANGE")

    if (not r5.passed) and (ERR_IMU_GYRO_BIAS_POLY_OUT_OF_RANGE in r5.error_codes):
        passed_count += 1
    else:
        suite_errors.append("S5 failed to detect ERR_IMU_GYRO_BIAS_POLY_OUT_OF_RANGE")

    if (
        (not r6.passed)
        and (ERR_IMX510_CRC32_MISMATCH in r6.error_codes)
        and (ERR_IBIS_IMU_CRC32_MISMATCH in r6.error_codes)
    ):
        passed_count += 1
    else:
        suite_errors.append("S6 failed to detect CRC32 mismatch on IMX510/IBIS tables")

    all_ok = len(suite_errors) == 0 and passed_count == len(SENSOR_IBIS_SCENARIO_IDS)
    suite_payload = {
        "scenarios": [
            {
                "id": r.scenario_id,
                "status": r.status,
                "passed": r.passed,
                "error_codes": list(r.error_codes),
            }
            for r in results
        ]
    }
    return SensorIbisCal6ScenarioSuiteResult(
        passed=all_ok,
        status=STATUS_VERIFIED_FACTORY_CAL_GUARD if all_ok else STATUS_FAIL_FACTORY_CAL_GUARD,
        scenarios_passed=passed_count,
        scenarios_total=len(SENSOR_IBIS_SCENARIO_IDS),
        scenario_results=results,
        errors=tuple(suite_errors),
        suite_sha256=_canonical_sha256(suite_payload),
    )


# ---------------------------------------------------------------------------
# Master Suite Entrypoint (Pillar 14)
# ---------------------------------------------------------------------------


def run_factory_cal_ibis_defectpixel_and_nvs_suite(
    *,
    force_clean_room: Optional[bool] = None,
    include_cpapp: bool = True,
) -> FactoryCalIbisAndNvsSuiteReport:
    """Run Phase 126 Pillar 14: O_RDONLY donor inspection, per-body factory calibration
    (`nvs`/`adj`/`cnflasha`) triple-copy parity & cross-serial firewall, and IMX510
    defect-pixel / dual-ISO / 5-axis IBIS Hall-zero & IMU gyro table integrity verifier.
    """
    t0 = time.monotonic()
    donor_snap = inspect_factory_cal_and_sensor_donors_readonly(
        force_clean_room=force_clean_room,
        include_cpapp=include_cpapp,
    )
    firewall_suite = run_factory_cal_6_scenario_firewall()
    sensor_suite = run_sensor_ibis_cal_6_scenario_suite()

    errors: List[str] = []
    if not donor_snap.cross_sku_distinct:
        errors.append("Cross-SKU FX3/FX6 calibration/backup donor separation check failed.")
    errors.extend(firewall_suite.errors)
    errors.extend(sensor_suite.errors)

    all_passed = (
        donor_snap.cross_sku_distinct
        and firewall_suite.passed
        and sensor_suite.passed
        and (PHYSICAL_DEVICE_WRITES == 0)
        and (FACTORY_CAL_MUTATION_BYTES == 0)
        and (PRIVATE_KEY_BYTES_READ == 0)
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not PERSISTENT_WRITE_RELEASE)
    )
    suite_payload = {
        "schema": FACTORY_CAL_IBIS_NVS_SCHEMA,
        "version": FACTORY_CAL_IBIS_NVS_VERSION,
        "mode": donor_snap.verification_mode,
        "donor_sha256": donor_snap.snapshot_sha256,
        "firewall_sha256": firewall_suite.suite_sha256,
        "sensor_sha256": sensor_suite.suite_sha256,
        "all_passed": all_passed,
    }
    elapsed = round(time.monotonic() - t0, 4)
    return FactoryCalIbisAndNvsSuiteReport(
        schema=FACTORY_CAL_IBIS_NVS_SCHEMA,
        version=FACTORY_CAL_IBIS_NVS_VERSION,
        status=STATUS_VERIFIED_FACTORY_CAL_GUARD if all_passed else STATUS_FAIL_FACTORY_CAL_GUARD,
        verification_mode=donor_snap.verification_mode,
        all_passed=all_passed,
        read_only_donor_access=READ_ONLY_DONOR_ACCESS,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        allow_boot_partition_targeting=ALLOW_BOOT_PARTITION_TARGETING,
        allow_destructive_fastboot=ALLOW_DESTRUCTIVE_FASTBOOT,
        otp_fuse_touches=OTP_FUSE_TOUCHES,
        passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        factory_cal_mutation_bytes=FACTORY_CAL_MUTATION_BYTES,
        private_key_bytes_read=PRIVATE_KEY_BYTES_READ,
        donor_snapshot=donor_snap,
        factory_cal_6_scenario_firewall=firewall_suite,
        sensor_ibis_6_scenario_suite=sensor_suite,
        suite_sha256=_canonical_sha256(suite_payload),
        elapsed_seconds=elapsed,
        errors=tuple(errors),
    )
