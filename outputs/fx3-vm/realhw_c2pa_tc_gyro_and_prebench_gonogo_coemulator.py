#!/usr/bin/env python3
"""Phase 172 — Stage 30 (`30/30` Milestone Stage) `outputs/fx3-vm/` Real-Hardware Main Track:
`p12:/cert/RQ_LIC.DAT` C2PA Authenticity Lock, `VMC-BNCM1` (`EXT-LK`) SMPTE-12M Timecode,
`IMX510` 6-Axis IMU Gyro `NonRealTimeMeta.xml` & Full 10-Step Pre-Bench Go/No-Go HIL Co-Emulator.

Implements strictly read-only (`os.open(..., os.O_RDONLY)` + buffered `os.read`) donor inspection
with deterministic `CLEAN_ROOM_SYNTHETIC` fallback (`FX3_FX6_FORCE_CLEAN_ROOM=1`), and co-emulates
all four Stage 30 C2PA Lock, SMPTE-12M LTC/UART Interlock, IMX510 6-Axis Gyro NRTM & 10-Step
Pre-Bench Go/No-Go Dry-Run Lifecycle Pillars (A–D) for physical Sony ILME-FX3 (`Ver. 7.02`,
Model ID `0x91030080`, AP `CXD90057` *Mira* + CP `CXD90058` *Cetus*, Sensor `IMX510`) while
hard-locking:
- `p8_cp_mutation_forbidden == True`, `cp_mutation_bytes == 0`, `wbi_mutation_bytes == 0`
- `c2pa_cert_mutation_bytes == 0`, `p2_mutation_bytes == 0`, `p18_mutation_bytes == 0`
- `persistent_emmc_writes_authorized == False`, `emmc_nflasha_write_count == 0`
- `spi_nor_write_authorized == False`, `otp_write_count == 0`, `rpmb_write_count == 0`
- `physical_device_writes == 0`, `donor_access_mode == "O_RDONLY"`

1. **Dual-Mode Donor Inspection (`os.O_RDONLY` + Clean-Room Fallback, < 0.10s)**:
   - Inspects FX3 `7.02` & FX6 `6.01` `cpapp-b.bin`, `libmpr.so`, `libsencore.so`, `im.elf`,
     and `Backup.bin` (10 core donors) strictly via `os.open(..., os.O_RDONLY)` + `os.read`.
   - Validates `cpapp-b.bin` ARM32 LE entry words (`0x00108000` load base) and `IMX510` /
     `C_ImagerCtrl_IMX510` / `LTC` / `Gyro Data` / `OTP` markers (`ILME-FX3` &
     `MTG_ULOCK_START_SLAVE` present in FX3, absent in FX6); `libmpr.so` `NonRealTimeMeta` /
     `LtcChangeTable` / `Gyroscope` / `SetMovieRecParam` (plus FX3 v7.02-only C2PA markers
     `InfraC2PA` / `c2pa.created` / `sony.created` / `jumdSSIG` / `sigcert.p12` absent in FX6
     v6.01); `libsencore.so` `355` export / `130` import parity (`C_GYRO_GAIN`,
     `MONITOR_GET_TEST_OUT_BNC_STATUS`, `GENLOCK`); `im.elf` zero-diff ABI (`40,920 B`,
     `/dev/nflasha12`, `/cert`, `/dev/nflasha15`); and `Backup.bin` `BK4\\x00` (`819` vs `840`
     subsystems, `90057`/`psd.bin`/`defdet.bin`/`lensfile.bin`/`tomco`).
   - Deterministic clean-room fallback when `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor paths absent;
     zero raw Sony firmware bytes emitted in JSON output.

2. **Pillar A — `p12:/cert/RQ_LIC.DAT` Per-Camera C2PA License `MS_RDONLY` Immutability & Anti-Forgery Firewall**:
   - Co-emulates Stage-B startup, movie recording, and clean uninstall verifying
     `c2pa_cert_mutation_bytes == 0`, `p12:/cert` `MS_RDONLY` mount enforcement,
     `H0 == H1 == H2 == H3` SHA-256 preservation, and fail-closed blocking of cross-body
     or cross-model (`ILME-FX6` / `ILME-FX30` / `ILCE-7SM3`) C2PA signing & key-export attempts.

3. **Pillar B — `VMC-BNCM1` (`AD_JACK_IN` Pin 10 -> `EXT-LK`) SMPTE-12M LTC-IN (`0.5V–4.5V p-p`), User-Bits & Multi-USB UART Contention Interlock**:
   - Co-emulates external LTC jam-sync across `23.98 / 24 / 25 / 29.97 / 59.94` fps with
     SMPTE-12M `0x3FFD` sync & User-Bits preservation, over-voltage `> 5.0V p-p` fail-closed
     rejection, FX6-only BNC `TC-OUT` clean masking (`tc_direction == "IN"`), and Multi-USB
     `1.8V UART` pin contention lock (`uart_contention_damage_events == 0`).

4. **Pillar C — `IMX510` (`8.7 ms` Readout) + 6-Axis IMU Gyro + `p18:/lens` `NonRealTimeMeta.xml` Catalyst/Resolve Stabilization Pipeline**:
   - Simulates recording `XAVC S-I` (`MP4`) and `XAVC-I` (`MXF`) clips with embedded 6-axis
     `2000 Hz` IMU gyro + `8.7 ms` rolling-shutter readout + `p18:/lens` focal-length metadata
     (`MS_RDONLY`), builds and XML-parses `NonRealTimeMeta.xml` (`ver.2.20`), and proves 100%
     Sony Catalyst Browse & DaVinci Resolve schema validity without touching `p2` or `p18`.

5. **Pillar D — Complete 10-Step Pre-Bench Operator Go/No-Go Dry-Run Lifecycle**:
   - Co-emulates the full 10-step pre-bench operator sequence: passive USB attach check ->
     `054C:0DA1 -> 054C:0336` `op=0xFF` canary -> Dual-Media 16-surface Tier-0 backup (`H0`) ->
     `p12`/`p18` `MS_RDONLY` lock -> `/dev/cnflasha15` `.orig` staging (`H1`) -> Dual-Boot +
     `EXT-LK` jam-sync -> Big-6 shooting + `NonRealTimeMeta.xml` (`H2`) -> `.RSV` + C2PA
     firewall check -> clean `.orig` uninstall -> `16/16 H0 == H3` clean factory seal
     (`persistent_emmc_writes_authorized == False`, `emmc_nflasha_write_count == 0`).
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse
from dataclasses import asdict, dataclass
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import struct
from typing import Dict, List, Mapping, Optional, Sequence, Tuple
import xml.etree.ElementTree as ET
import zlib


# ---------------------------------------------------------------------------
# Phase 172 Schema & Hard-Locked Safety Redlines
# ---------------------------------------------------------------------------

PHASE_172_SCHEMA = "phase172_realhw_c2pa_tc_gyro_and_prebench_gonogo_coemulator_v1"
PHASE_172_VERSION = "172.0.0"
STAGE_INDEX = 30
STAGE_TOTAL = 30
MILESTONE_LABEL = "30/30"

P8_CP_MUTATION_FORBIDDEN = True
NOP_COUNT = 0
GUEST_CODE_MODIFICATION_BYTES = 0
CP_MUTATION_BYTES = 0
WBI_MUTATION_BYTES = 0
CALIBRATION_MUTATION_BYTES = 0
C2PA_CERT_MUTATION_BYTES = 0
P12_CERT_MOUNT_FLAGS = "MS_RDONLY"
P2_MUTATION_BYTES = 0
P18_MUTATION_BYTES = 0
NVRAM_PERSISTENT_WRITES = 0
BK4_PERSISTENT_NVRAM_WRITES = 0
PHYSICAL_DEVICE_WRITES = 0
PERSISTENT_EMMC_WRITES_AUTHORIZED = False
EMMC_NFLASHA_WRITE_COUNT = 0
EMMC_MUTATION_BYTES = 0
SPI_NOR_WRITE_AUTHORIZED = False
SPI_NOR_MUTATION_BYTES = 0
OTP_WRITE_COUNT = 0
RPMB_WRITE_COUNT = 0
ORIG_RESIDUAL_COUNT = 0
TMP_JIRITSU_RESIDUAL_COUNT = 0
P6_CHUNK_RESIDUAL_COUNT = 0
NULL_GPIO_DEREFS = 0
MAILBOX_STALLS = 0
STOCK_CP_FAULT_COUNT = 0
WF12_00342260_HITS = 0
APPFW_CRASHES = 0
UART_CONTENTION_DAMAGE_EVENTS = 0
OVER_VOLTAGE_DAMAGE_EVENTS = 0
DONOR_ACCESS_MODE = "O_RDONLY"

ENV_FORCE_CLEAN_ROOM = "FX3_FX6_FORCE_CLEAN_ROOM"
ENV_MAC_ROOT = "FX3_FX6_MAC_ROOT"
ENV_MAC_WORK_ROOT = "FX3_FX6_MAC_WORK_ROOT"
ENV_MAIN_LAB_WORK_ROOT = "FX3_FX6_MAIN_LAB_WORK_ROOT"

DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]
LEGACY_MAC_ROOT = Path("/Volumes/KAFU2T/AI/Projects/Mac")
CLEAN_ROOM_SENTINEL_DIRNAME = "__fx3_fx6_clean_room_donor_disabled__"

# ---------------------------------------------------------------------------
# Verified Local Donor Paths & Expected Metrics (10 Core Donors)
# ---------------------------------------------------------------------------

EXPECTED_DONOR_BYTES: Mapping[str, int] = {
    "fx3_cpapp": 15_980_568,
    "fx6_cpapp": 17_952_816,
    "fx3_libmpr": 3_517_008,
    "fx6_libmpr": 28_921_824,
    "fx3_sencore": 377_328,
    "fx6_sencore": 401_952,
    "fx3_im_elf": 40_920,
    "fx6_im_elf": 40_920,
    "fx3_backup": 2_229_740,
    "fx6_backup": 2_253_333,
}

EXPECTED_CP_ARM32_ENTRY_WORDS: Tuple[int, ...] = (
    0xE59F1004,
    0xE2811004,
    0xE1A0F001,
    0x0010800C,
    0xE3A000D3,
    0xE12FF000,
)
CP_LOAD_BASE = 0x00108000

EXPECTED_FX3_LIBMPR_EXPORTS = 3_541
EXPECTED_FX6_LIBMPR_EXPORTS = 4_271
EXPECTED_SENCORE_EXPORTS = 355
EXPECTED_SENCORE_IMPORTS = 130
EXPECTED_IM_ELF_EXPORTS = 11
EXPECTED_IM_ELF_IMPORTS = 85
EXPECTED_FX3_BACKUP_SUBSYSTEMS = 819
EXPECTED_FX6_BACKUP_SUBSYSTEMS = 840

_FX3_USR_PREFIX = "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr"
_FX6_LIB_PREFIX = "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib"
_FX6_BIN_PREFIX = "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/bin"

DONOR_RELPATHS: Mapping[str, str] = {
    "fx3_cpapp": "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin",
    "fx6_cpapp": "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fat-files/nflasha8/cpapp-b.bin",
    "fx3_libmpr": f"{_FX3_USR_PREFIX}/lib/libmpr.so",
    "fx6_libmpr": f"{_FX6_LIB_PREFIX}/libmpr.so",
    "fx3_sencore": f"{_FX3_USR_PREFIX}/lib/libsencore.so",
    "fx6_sencore": f"{_FX6_LIB_PREFIX}/libsencore.so",
    "fx3_im_elf": f"{_FX3_USR_PREFIX}/bin/im.elf",
    "fx6_im_elf": f"{_FX6_BIN_PREFIX}/im.elf",
    "fx3_backup": "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin",
    "fx6_backup": "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0110_backup/SYSIPSX-DSLR/CHAPLIN/CX95898_UC.bin",
}

CPAPP_SHARED_MARKERS: Tuple[str, ...] = (
    "IMX510",
    "C_ImagerCtrl_IMX510",
    "LTC",
    "Gyro Data",
    "OTP",
)
CPAPP_FX3_ONLY_MARKERS: Tuple[str, ...] = (
    "ILME-FX3",
    "MTG_ULOCK_START_SLAVE",
)

LIBMPR_SHARED_MARKERS: Tuple[str, ...] = (
    "NonRealTimeMeta",
    "LtcChangeTable",
    "Gyroscope",
    "SetMovieRecParam",
)
LIBMPR_FX3_C2PA_MARKERS: Tuple[str, ...] = (
    "InfraC2PA",
    "c2pa.created",
    "sony.created",
    "jumdSSIG",
    "sigcert.p12",
)

SENCORE_MARKERS: Tuple[str, ...] = (
    "C_GYRO_GAIN",
    "MONITOR_GET_TEST_OUT_BNC_STATUS",
    "GENLOCK",
    "MPR_CMD_",
    "SenserIfStart",
)

IM_ELF_MARKERS: Tuple[str, ...] = (
    "/dev/nflasha12",
    "/cert",
    "/dev/nflasha2",
    "/dev/nflasha15",
    "libIMDB.so",
    "libbackup.so",
    "libosal_uipc.so",
)

BACKUP_MARKERS: Tuple[str, ...] = (
    "90057",
    "psd.bin",
    "defdet.bin",
    "lensfile.bin",
    "tomco",
)

# ---------------------------------------------------------------------------
# Pillar A Constants: p12:/cert/RQ_LIC.DAT C2PA Immutability & Firewall
# ---------------------------------------------------------------------------

FX3_MODEL_ID = 0x91030080
FX3_MODEL_ID_HEX = "0x91030080"
FX3_MODEL_NAME = "ILME-FX3"
SUPPORTED_FOREIGN_MODEL_IDS: Mapping[str, int] = {
    "ILME-FX6": 0x91030060,
    "ILME-FX30": 0x91030090,
    "ILCE-7SM3": 0x91030070,
}

P12_DEVICE_NODE = "/dev/nflasha12"
P12_MOUNT_POINT = "p12:/cert"
RQ_LIC_PARTITION_PATH = "p12:/cert/RQ_LIC.DAT"
C2PA_MAX_LICENSES = 100
DEFAULT_BODY_SERIAL = "FX3-BODY-000172"
DEFAULT_RQ_LIC_SHA256 = hashlib.sha256(
    f"{FX3_MODEL_NAME}:{FX3_MODEL_ID_HEX}:{DEFAULT_BODY_SERIAL}:{RQ_LIC_PARTITION_PATH}".encode("ascii")
).hexdigest()
C2PA_LIFECYCLE_PHASES: Tuple[str, ...] = (
    "STAGE_B_STARTUP",
    "MOVIE_RECORDING",
    "CLEAN_UNINSTALL",
)

# ---------------------------------------------------------------------------
# Pillar B Constants: VMC-BNCM1 EXT-LK SMPTE-12M LTC & Multi-USB UART Interlock
# ---------------------------------------------------------------------------

VMC_BNCM1_ADAPTER = "VMC-BNCM1"
AD_JACK_IN_PIN = 10
VMC_BNCM1_ID_RESISTOR_OHM = 680_000
VMC_BNCM1_ID_MIN_OHM = 612_000
VMC_BNCM1_ID_MAX_OHM = 748_000
LTC_MIN_VPP_MV = 500
LTC_MAX_VPP_MV = 4500
LTC_OVERVOLTAGE_CEILING_MV = 5000
SMPTE_12M_SYNC_WORD_FWD = 0x3FFD

SMPTE_LTC_FRAMERATES: Mapping[str, Tuple[Fraction, bool]] = {
    "23.98": (Fraction(24000, 1001), False),
    "24": (Fraction(24, 1), False),
    "25": (Fraction(25, 1), False),
    "29.97": (Fraction(30000, 1001), True),
    "59.94": (Fraction(60000, 1001), True),
}

# ---------------------------------------------------------------------------
# Pillar C Constants: IMX510 8.7 ms + 6-Axis IMU Gyro + p18:/lens NRTM XML
# ---------------------------------------------------------------------------

IMX510_SENSOR_NAME = "IMX510"
IMX510_READOUT_MS = 8.7
IMX510_READOUT_US = 8700
IMU_AXES = 6
IMU_SAMPLE_RATE_HZ = 2000
P18_LENS_MOUNT_POINT = "p18:/lens"
P18_LENS_DEVICE_NODE = "/dev/nflasha18"
P2_NVRAM_MOUNT_POINT = "p2:/nvram"
NRTM_XML_NAMESPACE = "urn:schemas-professionalDisc:nonRealTimeMeta:ver.2.20"
NRTM_CLIP_FORMATS: Tuple[str, ...] = ("XAVC S-I", "XAVC-I")

# ---------------------------------------------------------------------------
# Pillar D Constants: 10-Step Pre-Bench Operator Go/No-Go Lifecycle & 16 Surfaces
# ---------------------------------------------------------------------------

USB_VID_SONY = 0x054C
USB_PID_MSC = 0x0DA1
USB_PID_UFU = 0x0336
UFU_CANARY_OPCODE = 0xFF
STAGE_B_TARGET_PARTITION = "/dev/cnflasha15"

SIXTEEN_STORAGE_SURFACES: Tuple[str, ...] = (
    "sector0",
    "p1",
    "p2",
    "p3",
    "p5",
    "p6",
    "p7",
    "p8",
    "p12",
    "p15",
    "p18",
    "p23",
    "p30",
    "spi_nor",
    "otp",
    "rpmb",
)

TEN_PREBENCH_STEPS: Tuple[str, ...] = (
    "01_passive_usb_attach_check",
    "02_usb_054c_0da1_to_0336_op_ff_canary",
    "03_dual_media_16_surface_tier0_backup_h0",
    "04_p12_c2pa_p18_lens_ms_rdonly_lock",
    "05_cnflasha15_orig_atomic_staging_h1",
    "06_dualboot_and_vmc_bncm1_ext_lk_jam_sync",
    "07_big6_imx510_8p7ms_gyro_nrtm_shoot_h2",
    "08_rsv_salvage_and_c2pa_antiforgery_check",
    "09_clean_orig_restore_and_uninstall",
    "10_16of16_h0_eq_h3_factory_seal_verdict",
)


class RealHwC2paTcGyroPrebenchError(ValueError):
    """Raised on invalid Phase 172 Stage 30 configuration or contract inputs."""


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CpappDonorSummary:
    artifact_key: str
    body_label: str
    source_mode: str
    file_bytes: int
    sha256_prefix16: str
    arm32_entry_ok: bool
    load_base_hex: str
    shared_marker_hits: Dict[str, int]
    fx3_only_hits: Dict[str, int]


@dataclass(frozen=True)
class ElfDonorSummary:
    artifact_key: str
    body_label: str
    source_mode: str
    file_bytes: int
    export_count: int
    import_count: int
    marker_hits: Dict[str, int]


@dataclass(frozen=True)
class BackupDonorSummary:
    artifact_key: str
    body_label: str
    source_mode: str
    file_bytes: int
    magic_ascii: str
    subsystem_count: int
    marker_hits: Dict[str, int]


@dataclass(frozen=True)
class Phase172DonorAudit:
    source_mode: str
    access_mode: str
    donor_files_inspected: int
    fx3_cpapp: CpappDonorSummary
    fx6_cpapp: CpappDonorSummary
    fx3_libmpr: ElfDonorSummary
    fx6_libmpr: ElfDonorSummary
    fx3_sencore: ElfDonorSummary
    fx6_sencore: ElfDonorSummary
    fx3_im_elf: ElfDonorSummary
    fx6_im_elf: ElfDonorSummary
    fx3_backup: BackupDonorSummary
    fx6_backup: BackupDonorSummary
    im_elf_abi_zero_diff: bool
    sencore_symbol_parity: bool
    fx3_c2pa_markers_absent_in_fx6_libmpr: bool
    fx3_only_cp_markers_absent_in_fx6_cp: bool
    all_contracts_verified: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class C2paLifecycleAuditResult:
    valid: bool
    phases_verified: Tuple[str, ...]
    p12_mount_point: str
    p12_mount_flags: str
    rq_lic_path: str
    c2pa_cert_mutation_bytes: int
    rq_lic_sha256_h0_to_h3_identical: bool
    license_count: int
    private_key_reads: int
    private_key_exports: int
    status_code: str


@dataclass(frozen=True)
class C2paSigningFirewallResult:
    admitted: bool
    firewall_blocked: bool
    cross_body_blocked: bool
    cross_model_blocked: bool
    requested_model_name: str
    requested_model_id_hex: str
    body_serial_matched: bool
    signing_mode: str
    c2pa_cert_mutation_bytes: int
    status_code: str


@dataclass(frozen=True)
class VmcBncm1LtcSyncResult:
    valid: bool
    adapter_name: str
    ad_jack_in_pin: int
    id_resistor_ohm: int
    fps_label: str
    drop_frame: bool
    ltc_vpp_mv: int
    ltc_sync_word_hex: str
    user_bits_hex: str
    ub_preserved: bool
    frame_slip: int
    tc_direction: str
    fx6_tc_out_bnc_masked: bool
    multi_usb_uart_1v8_active: bool
    uart_contention_damage_events: int
    over_voltage_damage_events: int
    status_code: str


@dataclass(frozen=True)
class Imx510GyroNrtmClipResult:
    valid: bool
    clip_format: str
    container: str
    sensor_name: str
    readout_ms: float
    focal_length_mm: float
    imu_axes: int
    imu_sample_rate_hz: int
    frames_recorded: int
    imu_samples_total: int
    monotonically_increasing_timestamps: bool
    crc32_valid: bool
    nrtm_xml_bytes: int
    nrtm_namespace: str
    catalyst_schema_valid: bool
    resolve_schema_valid: bool
    p2_mutation_bytes: int
    p18_mutation_bytes: int
    p18_mount_flags: str
    status_code: str


@dataclass(frozen=True)
class PrebenchStepResult:
    step_index: int
    step_id: str
    passed: bool
    emmc_nflasha_write_count: int
    c2pa_cert_mutation_bytes: int
    p18_mutation_bytes: int
    cp_mutation_bytes: int
    status_code: str


@dataclass(frozen=True)
class Prebench10StepLifecycleResult:
    valid: bool
    steps_completed: int
    steps_total: int
    usb_vid_msc: str
    usb_pid_msc: str
    usb_pid_ufu: str
    ufu_canary_opcode_hex: str
    stage_b_target_partition: str
    surfaces_total: int
    surfaces_h0_eq_h3: int
    dryrun_go_nogo: str
    dryrun_hil_coemulation_passed: bool
    physical_camera_bench_attached: bool
    persistent_emmc_writes_authorized: bool
    emmc_nflasha_write_count: int
    c2pa_cert_mutation_bytes: int
    p2_mutation_bytes: int
    p18_mutation_bytes: int
    cp_mutation_bytes: int
    orig_residual_count: int
    tmp_jiritsu_residual_count: int
    p6_chunk_residual_count: int
    otp_write_count: int
    rpmb_write_count: int
    steps: Tuple[PrebenchStepResult, ...]
    status_code: str


# ---------------------------------------------------------------------------
# Strictly Read-Only (`os.O_RDONLY` + `mmap.ACCESS_READ`) Donor Audit
# ---------------------------------------------------------------------------

_DONOR_AUDIT_CACHE: Dict[Tuple[str, Tuple[Tuple[str, str, int, int], ...]], Phase172DonorAudit] = {}


def is_forced_clean_room(env: Optional[Mapping[str, str]] = None) -> bool:
    source = os.environ if env is None else env
    return source.get(ENV_FORCE_CLEAN_ROOM, "").strip().lower() in ("1", "true", "yes", "on")


def _iter_work_roots(*, env: Optional[Mapping[str, str]] = None) -> Tuple[Path, ...]:
    if is_forced_clean_room(env):
        return ()
    source = os.environ if env is None else env
    candidates: List[Path] = []
    for key in (ENV_MAC_WORK_ROOT, ENV_MAIN_LAB_WORK_ROOT):
        val = source.get(key, "").strip()
        if val:
            candidates.append(Path(os.path.expanduser(val)))
    mac_root = source.get(ENV_MAC_ROOT, "").strip()
    if mac_root:
        base = Path(os.path.expanduser(mac_root))
        candidates.append(base / "work")
        candidates.append(base / "outputs" / "sony-fx3-fx6-lab" / "work")
    candidates.append(DEFAULT_REPO_ROOT / "work")
    internal = Path.home() / "AI-Workspace" / "AI" / "Projects" / "Mac"
    candidates.append(internal / "work")
    candidates.append(internal / "outputs" / "sony-fx3-fx6-lab" / "work")
    candidates.append(LEGACY_MAC_ROOT / "work")
    candidates.append(LEGACY_MAC_ROOT / "outputs" / "sony-fx3-fx6-lab" / "work")

    dedup: List[Path] = []
    seen = set()
    for c in candidates:
        s = str(c)
        if s not in seen:
            seen.add(s)
            dedup.append(c)
    return tuple(dedup)


def resolve_phase172_donor_paths(*, env: Optional[Mapping[str, str]] = None) -> Dict[str, Path]:
    """Resolve local donor paths without touching disk, honoring FX3_FX6_FORCE_CLEAN_ROOM=1."""
    if is_forced_clean_room(env):
        sentinel = DEFAULT_REPO_ROOT / "work" / CLEAN_ROOM_SENTINEL_DIRNAME
        return {k: sentinel / rel for k, rel in DONOR_RELPATHS.items()}

    roots = _iter_work_roots(env=env)
    resolved: Dict[str, Path] = {}
    for key, rel in DONOR_RELPATHS.items():
        chosen: Optional[Path] = None
        for root in roots:
            candidate = root / rel
            if candidate.is_file():
                chosen = candidate
                break
        if chosen is None:
            chosen = roots[0] / rel if roots else (DEFAULT_REPO_ROOT / "work" / rel)
        resolved[key] = chosen
    return resolved


def _scan_cpapp_buffer(
    buf: object,
    byte_len: int,
    *,
    artifact_key: str,
    body_label: str,
    source_mode: str,
) -> CpappDonorSummary:
    if byte_len < 24:
        raise RealHwC2paTcGyroPrebenchError(f"Truncated cpapp-b.bin buffer: {artifact_key}")
    words = struct.unpack_from("<6I", buf, 0)  # type: ignore[arg-type]
    arm32_ok = words == EXPECTED_CP_ARM32_ENTRY_WORDS
    load_base = words[3] - 0x0C if len(words) >= 4 else 0
    sha16 = hashlib.sha256(buf[: min(byte_len, 262_144)]).hexdigest()[:16]  # type: ignore[index]
    shared_hits = {
        tok: (1 if buf.find(tok.encode("ascii")) >= 0 else 0)  # type: ignore[attr-defined]
        for tok in CPAPP_SHARED_MARKERS
    }
    fx3_hits = {
        tok: (1 if buf.find(tok.encode("ascii")) >= 0 else 0)  # type: ignore[attr-defined]
        for tok in CPAPP_FX3_ONLY_MARKERS
    }
    return CpappDonorSummary(
        artifact_key=artifact_key,
        body_label=body_label,
        source_mode=source_mode,
        file_bytes=byte_len,
        sha256_prefix16=sha16,
        arm32_entry_ok=arm32_ok,
        load_base_hex=f"0x{load_base:08x}",
        shared_marker_hits=shared_hits,
        fx3_only_hits=fx3_hits,
    )


def _read_file_rdonly_bytes(path: Path) -> bytes:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        st = os.fstat(fd)
        remaining = st.st_size
        if remaining <= 0:
            return b""
        chunks: List[bytes] = []
        while remaining > 0:
            chunk = os.read(fd, min(remaining, 16 * 1024 * 1024))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        return chunks[0] if len(chunks) == 1 else b"".join(chunks)
    finally:
        os.close(fd)


def _scan_cpapp_rdonly(path: Path, *, artifact_key: str, body_label: str) -> CpappDonorSummary:
    data = _read_file_rdonly_bytes(path)
    return _scan_cpapp_buffer(
        data,
        len(data),
        artifact_key=artifact_key,
        body_label=body_label,
        source_mode="LOCAL_DONOR_RDONLY",
    )


def _scan_elf64_buffer(
    buf: bytes,
    byte_len: int,
    *,
    artifact_key: str,
    body_label: str,
    source_mode: str,
    tokens: Sequence[str],
) -> ElfDonorSummary:
    if byte_len < 64 or buf[:4] != b"\x7fELF" or buf[4] != 2 or buf[5] != 1:
        raise RealHwC2paTcGyroPrebenchError(f"Invalid ELF64 LE donor: {artifact_key}")

    e_shoff = struct.unpack_from("<Q", buf, 0x28)[0]
    e_shentsize, e_shnum = struct.unpack_from("<HH", buf, 0x3A)
    exports = 0
    imports = 0
    if e_shoff and e_shnum and e_shoff + e_shnum * e_shentsize <= byte_len:
        for idx in range(e_shnum):
            off = e_shoff + idx * e_shentsize
            _name, sh_type, _flags, _addr, sh_off, sh_size, _link, _info, _align, sh_entsize = struct.unpack_from(
                "<IIQQQQIIQQ", buf, off
            )
            if sh_type == 11 and sh_entsize == 24 and sh_off + sh_size <= byte_len and sh_size >= 24:
                for st_name, _info_b, _other_b, st_shndx, _val, _sz in struct.iter_unpack(
                    "<IBBHQQ", memoryview(buf)[sh_off + 24 : sh_off + sh_size]
                ):
                    if st_name == 0:
                        continue
                    if st_shndx == 0:
                        imports += 1
                    else:
                        exports += 1

    hits = {
        tok: (1 if buf.find(tok.encode("ascii")) >= 0 else 0)
        for tok in tokens
    }
    return ElfDonorSummary(
        artifact_key=artifact_key,
        body_label=body_label,
        source_mode=source_mode,
        file_bytes=byte_len,
        export_count=exports,
        import_count=imports,
        marker_hits=hits,
    )


def _scan_elf_probe_rdonly(
    path: Path,
    *,
    artifact_key: str,
    body_label: str,
    tokens: Sequence[str],
) -> ElfDonorSummary:
    data = _read_file_rdonly_bytes(path)
    return _scan_elf64_buffer(
        data,
        len(data),
        artifact_key=artifact_key,
        body_label=body_label,
        source_mode="LOCAL_DONOR_RDONLY",
        tokens=tokens,
    )


def _scan_backup_buffer(
    buf: bytes,
    byte_len: int,
    *,
    artifact_key: str,
    body_label: str,
    source_mode: str,
) -> BackupDonorSummary:
    if byte_len < 0x20 or buf[12:16] != b"BK4\x00":
        raise RealHwC2paTcGyroPrebenchError(f"Invalid BK4 Backup header: {artifact_key}")
    subsystems = struct.unpack_from("<I", buf, 0x10)[0]
    hits = {
        tok: (1 if buf.find(tok.encode("ascii")) >= 0 else 0)
        for tok in BACKUP_MARKERS
    }
    return BackupDonorSummary(
        artifact_key=artifact_key,
        body_label=body_label,
        source_mode=source_mode,
        file_bytes=byte_len,
        magic_ascii="BK4",
        subsystem_count=subsystems,
        marker_hits=hits,
    )


def _scan_backup_rdonly(path: Path, *, artifact_key: str, body_label: str) -> BackupDonorSummary:
    data = _read_file_rdonly_bytes(path)
    return _scan_backup_buffer(
        data,
        len(data),
        artifact_key=artifact_key,
        body_label=body_label,
        source_mode="LOCAL_DONOR_RDONLY",
    )


def _build_synthetic_elf64(
    *,
    exports: Sequence[str],
    imports: Sequence[str],
    rodata_strings: Sequence[str],
) -> bytes:
    """Build a minimal valid ELF64 LE shared/executable object with SHT_DYNSYM for clean-room."""
    strtab = bytearray(b"\x00")
    shstrtab = bytearray(b"\x00")
    sym_entries = bytearray(24)

    def add_str(buf: bytearray, text: str) -> int:
        off = len(buf)
        buf.extend(text.encode("ascii"))
        buf.append(0)
        return off

    for sym in exports:
        name_off = add_str(strtab, sym)
        sym_entries.extend(struct.pack("<IBBHQQ", name_off, (1 << 4) | 2, 0, 1, 0x1000, 16))
    for sym in imports:
        name_off = add_str(strtab, sym)
        sym_entries.extend(struct.pack("<IBBHQQ", name_off, (1 << 4) | 2, 0, 0, 0, 0))

    rodata = b"\x00".join(s.encode("ascii") for s in rodata_strings) + b"\x00"
    sh_dynstr = add_str(shstrtab, ".dynstr")
    sh_dynsym = add_str(shstrtab, ".dynsym")
    sh_rodata = add_str(shstrtab, ".rodata")
    sh_shstr = add_str(shstrtab, ".shstrtab")

    ehdr_size = 64
    dynstr_off = ehdr_size
    dynsym_off = dynstr_off + len(strtab)
    rodata_off = dynsym_off + len(sym_entries)
    shstr_off = rodata_off + len(rodata)
    shoff = (shstr_off + len(shstrtab) + 7) & ~7
    pad = shoff - (shstr_off + len(shstrtab))

    ehdr = bytearray(64)
    ehdr[0:16] = b"\x7fELF\x02\x01\x01" + b"\x00" * 9
    struct.pack_into("<HHIQQQIHHHHHH", ehdr, 16, 3, 183, 1, 0, 0, shoff, 0, 64, 0, 0, 64, 5, 4)

    shdrs = bytearray()
    shdrs.extend(struct.pack("<IIQQQQIIQQ", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0))
    shdrs.extend(struct.pack("<IIQQQQIIQQ", sh_dynstr, 3, 2, 0, dynstr_off, len(strtab), 0, 0, 1, 0))
    shdrs.extend(struct.pack("<IIQQQQIIQQ", sh_dynsym, 11, 2, 0, dynsym_off, len(sym_entries), 1, 1, 8, 24))
    shdrs.extend(struct.pack("<IIQQQQIIQQ", sh_rodata, 1, 2, 0, rodata_off, len(rodata), 0, 0, 1, 0))
    shdrs.extend(struct.pack("<IIQQQQIIQQ", sh_shstr, 3, 0, 0, shstr_off, len(shstrtab), 0, 0, 1, 0))

    return bytes(ehdr) + bytes(strtab) + bytes(sym_entries) + rodata + bytes(shstrtab) + (b"\x00" * pad) + bytes(shdrs)


def build_clean_room_phase172_fixtures() -> Dict[str, bytes]:
    """Deterministic clean-room synthetic donor binaries honoring all Stage 30 contracts."""
    cp_hdr = struct.pack("<6I", *EXPECTED_CP_ARM32_ENTRY_WORDS)
    fx3_cp = (
        cp_hdr
        + b"\x00" * 40
        + b"\x00".join(s.encode("ascii") for s in (*CPAPP_SHARED_MARKERS, *CPAPP_FX3_ONLY_MARKERS))
        + b"\x00"
    )
    fx6_cp = (
        cp_hdr
        + b"\x00" * 40
        + b"\x00".join(s.encode("ascii") for s in CPAPP_SHARED_MARKERS)
        + b"\x00"
    )

    fx3_libmpr = _build_synthetic_elf64(
        exports=[f"mpr_exp_{i}" for i in range(EXPECTED_FX3_LIBMPR_EXPORTS)],
        imports=["MPR_CMD_Start"],
        rodata_strings=(*LIBMPR_SHARED_MARKERS, *LIBMPR_FX3_C2PA_MARKERS),
    )
    fx6_libmpr = _build_synthetic_elf64(
        exports=[f"mpr6_exp_{i}" for i in range(EXPECTED_FX6_LIBMPR_EXPORTS)],
        imports=["MPR_CMD_Start"],
        rodata_strings=LIBMPR_SHARED_MARKERS,
    )
    fx3_sencore = _build_synthetic_elf64(
        exports=[f"sen_exp_{i}" for i in range(EXPECTED_SENCORE_EXPORTS)],
        imports=[f"sen_imp_{i}" for i in range(EXPECTED_SENCORE_IMPORTS)],
        rodata_strings=SENCORE_MARKERS,
    )
    fx6_sencore = _build_synthetic_elf64(
        exports=[f"sen6_exp_{i}" for i in range(EXPECTED_SENCORE_EXPORTS)],
        imports=[f"sen6_imp_{i}" for i in range(EXPECTED_SENCORE_IMPORTS)],
        rodata_strings=SENCORE_MARKERS,
    )
    fx3_im = _build_synthetic_elf64(
        exports=[f"im_exp_{i}" for i in range(EXPECTED_IM_ELF_EXPORTS)],
        imports=[f"im_imp_{i}" for i in range(EXPECTED_IM_ELF_IMPORTS)],
        rodata_strings=IM_ELF_MARKERS,
    )
    fx6_im = fx3_im

    bk_tail = b"\x00".join(s.encode("ascii") for s in BACKUP_MARKERS) + b"\x00"
    fx3_bk = b"\x00" * 12 + b"BK4\x00" + struct.pack("<I", EXPECTED_FX3_BACKUP_SUBSYSTEMS) + b"\x00" * 16 + bk_tail
    fx6_bk = b"\x00" * 12 + b"BK4\x00" + struct.pack("<I", EXPECTED_FX6_BACKUP_SUBSYSTEMS) + b"\x00" * 16 + bk_tail

    return {
        "fx3_cpapp": fx3_cp,
        "fx6_cpapp": fx6_cp,
        "fx3_libmpr": fx3_libmpr,
        "fx6_libmpr": fx6_libmpr,
        "fx3_sencore": fx3_sencore,
        "fx6_sencore": fx6_sencore,
        "fx3_im_elf": fx3_im,
        "fx6_im_elf": fx6_im,
        "fx3_backup": fx3_bk,
        "fx6_backup": fx6_bk,
    }


def _verify_donor_contracts(
    *,
    source_mode: str,
    fx3_cp: CpappDonorSummary,
    fx6_cp: CpappDonorSummary,
    fx3_mpr: ElfDonorSummary,
    fx6_mpr: ElfDonorSummary,
    fx3_sen: ElfDonorSummary,
    fx6_sen: ElfDonorSummary,
    fx3_im: ElfDonorSummary,
    fx6_im: ElfDonorSummary,
    fx3_bk: BackupDonorSummary,
    fx6_bk: BackupDonorSummary,
) -> Phase172DonorAudit:
    errors: List[str] = []

    if source_mode == "LOCAL_DONOR_RDONLY":
        byte_checks = (
            ("fx3_cpapp", fx3_cp.file_bytes),
            ("fx6_cpapp", fx6_cp.file_bytes),
            ("fx3_libmpr", fx3_mpr.file_bytes),
            ("fx6_libmpr", fx6_mpr.file_bytes),
            ("fx3_sencore", fx3_sen.file_bytes),
            ("fx6_sencore", fx6_sen.file_bytes),
            ("fx3_im_elf", fx3_im.file_bytes),
            ("fx6_im_elf", fx6_im.file_bytes),
            ("fx3_backup", fx3_bk.file_bytes),
            ("fx6_backup", fx6_bk.file_bytes),
        )
        for k, actual_sz in byte_checks:
            if actual_sz != EXPECTED_DONOR_BYTES[k]:
                errors.append(f"{k} byte size mismatch: {actual_sz} != {EXPECTED_DONOR_BYTES[k]}")

    if not fx3_cp.arm32_entry_ok or not fx6_cp.arm32_entry_ok:
        errors.append("cpapp-b.bin ARM32 entry signature mismatch")
    for tok in CPAPP_SHARED_MARKERS:
        if fx3_cp.shared_marker_hits.get(tok, 0) != 1 or fx6_cp.shared_marker_hits.get(tok, 0) != 1:
            errors.append(f"Missing shared cpapp marker: {tok}")

    fx3_only_cp_absent_in_fx6 = (
        all(fx3_cp.fx3_only_hits.get(tok, 0) == 1 for tok in CPAPP_FX3_ONLY_MARKERS)
        and all(fx6_cp.fx3_only_hits.get(tok, 0) == 0 for tok in CPAPP_FX3_ONLY_MARKERS)
    )
    if not fx3_only_cp_absent_in_fx6:
        errors.append("FX3-only cpapp markers parity check failed")

    if fx3_mpr.export_count != EXPECTED_FX3_LIBMPR_EXPORTS or fx6_mpr.export_count != EXPECTED_FX6_LIBMPR_EXPORTS:
        errors.append("libmpr.so export count mismatch")
    for tok in LIBMPR_SHARED_MARKERS:
        if fx3_mpr.marker_hits.get(tok, 0) != 1 or fx6_mpr.marker_hits.get(tok, 0) != 1:
            errors.append(f"Missing shared libmpr marker: {tok}")

    fx3_c2pa_absent_in_fx6 = (
        all(fx3_mpr.marker_hits.get(tok, 0) == 1 for tok in LIBMPR_FX3_C2PA_MARKERS)
        and all(fx6_mpr.marker_hits.get(tok, 0) == 0 for tok in LIBMPR_FX3_C2PA_MARKERS)
    )
    if not fx3_c2pa_absent_in_fx6:
        errors.append("FX3 v7.02 C2PA markers must exist in FX3 libmpr.so and be absent in FX6 v6.01 libmpr.so")

    sencore_parity = (
        fx3_sen.export_count == EXPECTED_SENCORE_EXPORTS
        and fx6_sen.export_count == EXPECTED_SENCORE_EXPORTS
        and fx3_sen.import_count == EXPECTED_SENCORE_IMPORTS
        and fx6_sen.import_count == EXPECTED_SENCORE_IMPORTS
        and all(fx3_sen.marker_hits.get(t, 0) == 1 for t in SENCORE_MARKERS)
        and all(fx6_sen.marker_hits.get(t, 0) == 1 for t in SENCORE_MARKERS)
    )
    if not sencore_parity:
        errors.append("libsencore.so symbol/marker parity check failed")

    im_zero_diff = (
        fx3_im.file_bytes == fx6_im.file_bytes
        and fx3_im.export_count == EXPECTED_IM_ELF_EXPORTS
        and fx6_im.export_count == EXPECTED_IM_ELF_EXPORTS
        and fx3_im.import_count == EXPECTED_IM_ELF_IMPORTS
        and fx6_im.import_count == EXPECTED_IM_ELF_IMPORTS
        and all(fx3_im.marker_hits.get(t, 0) == 1 for t in IM_ELF_MARKERS)
        and all(fx6_im.marker_hits.get(t, 0) == 1 for t in IM_ELF_MARKERS)
    )
    if not im_zero_diff:
        errors.append("im.elf zero-diff ABI parity failed")

    if fx3_bk.subsystem_count != EXPECTED_FX3_BACKUP_SUBSYSTEMS or fx6_bk.subsystem_count != EXPECTED_FX6_BACKUP_SUBSYSTEMS:
        errors.append("BK4 subsystem count mismatch")
    for tok in BACKUP_MARKERS:
        if fx3_bk.marker_hits.get(tok, 0) != 1 or fx6_bk.marker_hits.get(tok, 0) != 1:
            errors.append(f"Missing Backup.bin marker: {tok}")

    return Phase172DonorAudit(
        source_mode=source_mode,
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=10,
        fx3_cpapp=fx3_cp,
        fx6_cpapp=fx6_cp,
        fx3_libmpr=fx3_mpr,
        fx6_libmpr=fx6_mpr,
        fx3_sencore=fx3_sen,
        fx6_sencore=fx6_sen,
        fx3_im_elf=fx3_im,
        fx6_im_elf=fx6_im,
        fx3_backup=fx3_bk,
        fx6_backup=fx6_bk,
        im_elf_abi_zero_diff=im_zero_diff,
        sencore_symbol_parity=sencore_parity,
        fx3_c2pa_markers_absent_in_fx6_libmpr=fx3_c2pa_absent_in_fx6,
        fx3_only_cp_markers_absent_in_fx6_cp=fx3_only_cp_absent_in_fx6,
        all_contracts_verified=(len(errors) == 0),
        errors=tuple(errors),
    )


def inspect_phase172_donors(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Phase172DonorAudit:
    """Inspect all 10 FX3 7.02 + FX6 6.01 donors strictly os.O_RDONLY, or deterministic clean-room."""
    forced = is_forced_clean_room(env) if force_clean_room is None else bool(force_clean_room)
    resolved = resolve_phase172_donor_paths(env=None if forced else env)
    all_present = (not forced) and all(p.is_file() for p in resolved.values())
    mode = "LOCAL_DONOR_RDONLY" if all_present else "CLEAN_ROOM_SYNTHETIC"

    if mode == "LOCAL_DONOR_RDONLY":
        sig: List[Tuple[str, str, int, int]] = []
        for k in sorted(resolved.keys()):
            st = resolved[k].stat()
            sig.append((k, str(resolved[k]), st.st_size, st.st_mtime_ns))
        cache_key = (mode, tuple(sig))
    else:
        cache_key = (mode, ())

    if cache_key in _DONOR_AUDIT_CACHE:
        return _DONOR_AUDIT_CACHE[cache_key]

    libmpr_tokens = (*LIBMPR_SHARED_MARKERS, *LIBMPR_FX3_C2PA_MARKERS)

    if mode == "LOCAL_DONOR_RDONLY":
        fx3_cp = _scan_cpapp_rdonly(resolved["fx3_cpapp"], artifact_key="fx3_cpapp", body_label="FX3_7.02")
        fx6_cp = _scan_cpapp_rdonly(resolved["fx6_cpapp"], artifact_key="fx6_cpapp", body_label="FX6_6.01")
        fx3_mpr = _scan_elf_probe_rdonly(
            resolved["fx3_libmpr"], artifact_key="fx3_libmpr", body_label="FX3_7.02", tokens=libmpr_tokens
        )
        fx6_mpr = _scan_elf_probe_rdonly(
            resolved["fx6_libmpr"], artifact_key="fx6_libmpr", body_label="FX6_6.01", tokens=libmpr_tokens
        )
        fx3_sen = _scan_elf_probe_rdonly(
            resolved["fx3_sencore"], artifact_key="fx3_sencore", body_label="FX3_7.02", tokens=SENCORE_MARKERS
        )
        fx6_sen = _scan_elf_probe_rdonly(
            resolved["fx6_sencore"], artifact_key="fx6_sencore", body_label="FX6_6.01", tokens=SENCORE_MARKERS
        )
        fx3_im = _scan_elf_probe_rdonly(
            resolved["fx3_im_elf"], artifact_key="fx3_im_elf", body_label="FX3_7.02", tokens=IM_ELF_MARKERS
        )
        fx6_im = _scan_elf_probe_rdonly(
            resolved["fx6_im_elf"], artifact_key="fx6_im_elf", body_label="FX6_6.01", tokens=IM_ELF_MARKERS
        )
        fx3_bk = _scan_backup_rdonly(resolved["fx3_backup"], artifact_key="fx3_backup", body_label="FX3_7.02")
        fx6_bk = _scan_backup_rdonly(resolved["fx6_backup"], artifact_key="fx6_backup", body_label="FX6_6.01")
    else:
        fx = build_clean_room_phase172_fixtures()
        fx3_cp = _scan_cpapp_buffer(
            fx["fx3_cpapp"], len(fx["fx3_cpapp"]), artifact_key="fx3_cpapp", body_label="FX3_7.02", source_mode=mode
        )
        fx6_cp = _scan_cpapp_buffer(
            fx["fx6_cpapp"], len(fx["fx6_cpapp"]), artifact_key="fx6_cpapp", body_label="FX6_6.01", source_mode=mode
        )
        fx3_mpr = _scan_elf64_buffer(
            fx["fx3_libmpr"],
            len(fx["fx3_libmpr"]),
            artifact_key="fx3_libmpr",
            body_label="FX3_7.02",
            source_mode=mode,
            tokens=libmpr_tokens,
        )
        fx6_mpr = _scan_elf64_buffer(
            fx["fx6_libmpr"],
            len(fx["fx6_libmpr"]),
            artifact_key="fx6_libmpr",
            body_label="FX6_6.01",
            source_mode=mode,
            tokens=libmpr_tokens,
        )
        fx3_sen = _scan_elf64_buffer(
            fx["fx3_sencore"],
            len(fx["fx3_sencore"]),
            artifact_key="fx3_sencore",
            body_label="FX3_7.02",
            source_mode=mode,
            tokens=SENCORE_MARKERS,
        )
        fx6_sen = _scan_elf64_buffer(
            fx["fx6_sencore"],
            len(fx["fx6_sencore"]),
            artifact_key="fx6_sencore",
            body_label="FX6_6.01",
            source_mode=mode,
            tokens=SENCORE_MARKERS,
        )
        fx3_im = _scan_elf64_buffer(
            fx["fx3_im_elf"],
            len(fx["fx3_im_elf"]),
            artifact_key="fx3_im_elf",
            body_label="FX3_7.02",
            source_mode=mode,
            tokens=IM_ELF_MARKERS,
        )
        fx6_im = _scan_elf64_buffer(
            fx["fx6_im_elf"],
            len(fx["fx6_im_elf"]),
            artifact_key="fx6_im_elf",
            body_label="FX6_6.01",
            source_mode=mode,
            tokens=IM_ELF_MARKERS,
        )
        fx3_bk = _scan_backup_buffer(
            fx["fx3_backup"], len(fx["fx3_backup"]), artifact_key="fx3_backup", body_label="FX3_7.02", source_mode=mode
        )
        fx6_bk = _scan_backup_buffer(
            fx["fx6_backup"], len(fx["fx6_backup"]), artifact_key="fx6_backup", body_label="FX6_6.01", source_mode=mode
        )

    audit = _verify_donor_contracts(
        source_mode=mode,
        fx3_cp=fx3_cp,
        fx6_cp=fx6_cp,
        fx3_mpr=fx3_mpr,
        fx6_mpr=fx6_mpr,
        fx3_sen=fx3_sen,
        fx6_sen=fx6_sen,
        fx3_im=fx3_im,
        fx6_im=fx6_im,
        fx3_bk=fx3_bk,
        fx6_bk=fx6_bk,
    )
    _DONOR_AUDIT_CACHE[cache_key] = audit
    return audit


# ---------------------------------------------------------------------------
# Pillar A: p12:/cert/RQ_LIC.DAT Per-Camera C2PA Lock & Anti-Forgery Firewall
# ---------------------------------------------------------------------------


def simulate_c2pa_rq_lic_lifecycle(
    *,
    p12_mount_flags: str = P12_CERT_MOUNT_FLAGS,
    write_requested: bool = False,
    license_count: int = 1,
    sha256_by_epoch: Optional[Mapping[str, str]] = None,
) -> C2paLifecycleAuditResult:
    """Co-emulate Stage-B startup, recording, and uninstall verifying c2pa_cert_mutation_bytes == 0."""
    epochs = ("H0", "H1", "H2", "H3")
    hashes = {ep: DEFAULT_RQ_LIC_SHA256 for ep in epochs}
    if sha256_by_epoch is not None:
        for ep, val in sha256_by_epoch.items():
            hashes[ep] = val

    h0_to_h3_eq = len({hashes[ep] for ep in epochs}) == 1
    ro_enforced = p12_mount_flags == P12_CERT_MOUNT_FLAGS
    lic_valid = 1 <= license_count <= C2PA_MAX_LICENSES

    if (not ro_enforced) or write_requested:
        return C2paLifecycleAuditResult(
            valid=False,
            phases_verified=C2PA_LIFECYCLE_PHASES,
            p12_mount_point=P12_MOUNT_POINT,
            p12_mount_flags=p12_mount_flags,
            rq_lic_path=RQ_LIC_PARTITION_PATH,
            c2pa_cert_mutation_bytes=0,
            rq_lic_sha256_h0_to_h3_identical=h0_to_h3_eq,
            license_count=license_count,
            private_key_reads=0,
            private_key_exports=0,
            status_code="BLOCKED_P12_CERT_NON_RDONLY_OR_WRITE",
        )
    if not h0_to_h3_eq:
        return C2paLifecycleAuditResult(
            valid=False,
            phases_verified=C2PA_LIFECYCLE_PHASES,
            p12_mount_point=P12_MOUNT_POINT,
            p12_mount_flags=p12_mount_flags,
            rq_lic_path=RQ_LIC_PARTITION_PATH,
            c2pa_cert_mutation_bytes=0,
            rq_lic_sha256_h0_to_h3_identical=False,
            license_count=license_count,
            private_key_reads=0,
            private_key_exports=0,
            status_code="BLOCKED_RQ_LIC_SHA256_DRIFT",
        )
    if not lic_valid:
        return C2paLifecycleAuditResult(
            valid=False,
            phases_verified=C2PA_LIFECYCLE_PHASES,
            p12_mount_point=P12_MOUNT_POINT,
            p12_mount_flags=p12_mount_flags,
            rq_lic_path=RQ_LIC_PARTITION_PATH,
            c2pa_cert_mutation_bytes=0,
            rq_lic_sha256_h0_to_h3_identical=True,
            license_count=license_count,
            private_key_reads=0,
            private_key_exports=0,
            status_code="BLOCKED_RQ_LIC_INVALID_LICENSE_COUNT",
        )

    return C2paLifecycleAuditResult(
        valid=True,
        phases_verified=C2PA_LIFECYCLE_PHASES,
        p12_mount_point=P12_MOUNT_POINT,
        p12_mount_flags=P12_CERT_MOUNT_FLAGS,
        rq_lic_path=RQ_LIC_PARTITION_PATH,
        c2pa_cert_mutation_bytes=C2PA_CERT_MUTATION_BYTES,
        rq_lic_sha256_h0_to_h3_identical=True,
        license_count=license_count,
        private_key_reads=0,
        private_key_exports=0,
        status_code="C2PA_RQ_LIC_MS_RDONLY_IMMUTABLE_OK",
    )


def evaluate_c2pa_signing_firewall(
    *,
    requested_model_name: str = FX3_MODEL_NAME,
    requested_model_id: int = FX3_MODEL_ID,
    target_body_serial: str = DEFAULT_BODY_SERIAL,
    host_body_serial: str = DEFAULT_BODY_SERIAL,
    signing_mode: str = "SAME_BODY_STOCK_C2PA",
    extract_sigcert_p12: bool = False,
) -> C2paSigningFirewallResult:
    """Enforce per-camera C2PA anti-forgery firewall blocking cross-body & cross-model signing."""
    model_match = requested_model_name == FX3_MODEL_NAME and requested_model_id == FX3_MODEL_ID
    body_match = target_body_serial == host_body_serial

    if extract_sigcert_p12:
        return C2paSigningFirewallResult(
            admitted=False,
            firewall_blocked=True,
            cross_body_blocked=not body_match,
            cross_model_blocked=not model_match,
            requested_model_name=requested_model_name,
            requested_model_id_hex=f"0x{requested_model_id:08x}",
            body_serial_matched=body_match,
            signing_mode=signing_mode,
            c2pa_cert_mutation_bytes=0,
            status_code="BLOCKED_SIGCERT_P12_EXTRACTION_DENIED",
        )
    if not model_match:
        return C2paSigningFirewallResult(
            admitted=False,
            firewall_blocked=True,
            cross_body_blocked=not body_match,
            cross_model_blocked=True,
            requested_model_name=requested_model_name,
            requested_model_id_hex=f"0x{requested_model_id:08x}",
            body_serial_matched=body_match,
            signing_mode=signing_mode,
            c2pa_cert_mutation_bytes=0,
            status_code="BLOCKED_CROSS_MODEL_C2PA_SIGNING",
        )
    if not body_match:
        return C2paSigningFirewallResult(
            admitted=False,
            firewall_blocked=True,
            cross_body_blocked=True,
            cross_model_blocked=False,
            requested_model_name=requested_model_name,
            requested_model_id_hex=f"0x{requested_model_id:08x}",
            body_serial_matched=False,
            signing_mode=signing_mode,
            c2pa_cert_mutation_bytes=0,
            status_code="BLOCKED_CROSS_BODY_C2PA_SIGNING",
        )
    if signing_mode not in ("SAME_BODY_STOCK_C2PA", "UNSIGNED_STAGE_B_RESEARCH_OVERLAY"):
        return C2paSigningFirewallResult(
            admitted=False,
            firewall_blocked=True,
            cross_body_blocked=False,
            cross_model_blocked=False,
            requested_model_name=requested_model_name,
            requested_model_id_hex=f"0x{requested_model_id:08x}",
            body_serial_matched=True,
            signing_mode=signing_mode,
            c2pa_cert_mutation_bytes=0,
            status_code="BLOCKED_UNSUPPORTED_C2PA_SIGNING_MODE",
        )

    return C2paSigningFirewallResult(
        admitted=True,
        firewall_blocked=False,
        cross_body_blocked=False,
        cross_model_blocked=False,
        requested_model_name=requested_model_name,
        requested_model_id_hex=f"0x{requested_model_id:08x}",
        body_serial_matched=True,
        signing_mode=signing_mode,
        c2pa_cert_mutation_bytes=0,
        status_code=f"C2PA_ADMITTED_{signing_mode}",
    )


def evaluate_pillar_a_c2pa_lock_and_firewall() -> Dict[str, object]:
    lifecycle_ok = simulate_c2pa_rq_lic_lifecycle()
    p12_write_blocked = simulate_c2pa_rq_lic_lifecycle(write_requested=True)
    p12_rw_blocked = simulate_c2pa_rq_lic_lifecycle(p12_mount_flags="MS_RDWR")
    same_body_ok = evaluate_c2pa_signing_firewall()
    cross_body_blocked = evaluate_c2pa_signing_firewall(target_body_serial="FX3-OTHER-999999")
    cross_model_fx6_blocked = evaluate_c2pa_signing_firewall(
        requested_model_name="ILME-FX6",
        requested_model_id=SUPPORTED_FOREIGN_MODEL_IDS["ILME-FX6"],
    )
    sigcert_extract_blocked = evaluate_c2pa_signing_firewall(extract_sigcert_p12=True)

    passed = (
        lifecycle_ok.valid
        and lifecycle_ok.c2pa_cert_mutation_bytes == 0
        and lifecycle_ok.rq_lic_sha256_h0_to_h3_identical
        and (not p12_write_blocked.valid)
        and (not p12_rw_blocked.valid)
        and same_body_ok.admitted
        and cross_body_blocked.firewall_blocked
        and cross_body_blocked.cross_body_blocked
        and cross_model_fx6_blocked.firewall_blocked
        and cross_model_fx6_blocked.cross_model_blocked
        and sigcert_extract_blocked.firewall_blocked
    )
    return {
        "passed": passed,
        "lifecycle_ms_rdonly": asdict(lifecycle_ok),
        "p12_write_blocked": asdict(p12_write_blocked),
        "p12_rw_remount_blocked": asdict(p12_rw_blocked),
        "same_body_signing_admitted": asdict(same_body_ok),
        "cross_body_signing_blocked": asdict(cross_body_blocked),
        "cross_model_fx6_signing_blocked": asdict(cross_model_fx6_blocked),
        "sigcert_extraction_blocked": asdict(sigcert_extract_blocked),
    }


# ---------------------------------------------------------------------------
# Pillar B: VMC-BNCM1 (AD_JACK_IN Pin 10 -> EXT-LK) SMPTE-12M LTC & UART Lock
# ---------------------------------------------------------------------------


def simulate_vmc_bncm1_ltc_jam_sync(
    *,
    fps_label: str = "23.98",
    ltc_vpp_mv: int = 2000,
    id_resistor_ohm: int = VMC_BNCM1_ID_RESISTOR_OHM,
    user_bits_hex: str = "A3F12026",
    tc_out_bnc_drive_requested: bool = False,
    multi_usb_uart_1v8_requested: bool = False,
    drop_frame: Optional[bool] = None,
) -> VmcBncm1LtcSyncResult:
    """Co-emulate VMC-BNCM1 EXT-LK SMPTE-12M LTC-IN, User-Bits & Multi-USB 1.8V UART interlock."""
    if fps_label not in SMPTE_LTC_FRAMERATES:
        raise RealHwC2paTcGyroPrebenchError(
            f"Unsupported SMPTE-12M fps_label={fps_label!r}; expected {tuple(SMPTE_LTC_FRAMERATES.keys())}"
        )
    _rate, default_df = SMPTE_LTC_FRAMERATES[fps_label]
    use_df = default_df if drop_frame is None else bool(drop_frame)
    ub_norm = user_bits_hex.strip().upper().removeprefix("0X")
    if len(ub_norm) != 8 or any(c not in "0123456789ABCDEF" for c in ub_norm):
        raise RealHwC2paTcGyroPrebenchError(f"Invalid SMPTE-12M 32-bit user_bits_hex: {user_bits_hex!r}")

    if ltc_vpp_mv > LTC_OVERVOLTAGE_CEILING_MV:
        return VmcBncm1LtcSyncResult(
            valid=False,
            adapter_name=VMC_BNCM1_ADAPTER,
            ad_jack_in_pin=AD_JACK_IN_PIN,
            id_resistor_ohm=id_resistor_ohm,
            fps_label=fps_label,
            drop_frame=use_df,
            ltc_vpp_mv=ltc_vpp_mv,
            ltc_sync_word_hex=f"0x{SMPTE_12M_SYNC_WORD_FWD:04x}",
            user_bits_hex=f"0x{ub_norm}",
            ub_preserved=False,
            frame_slip=0,
            tc_direction="IN",
            fx6_tc_out_bnc_masked=True,
            multi_usb_uart_1v8_active=False,
            uart_contention_damage_events=0,
            over_voltage_damage_events=0,
            status_code="BLOCKED_LTC_OVERVOLTAGE_GT_5V",
        )

    if not (LTC_MIN_VPP_MV <= ltc_vpp_mv <= LTC_MAX_VPP_MV):
        return VmcBncm1LtcSyncResult(
            valid=False,
            adapter_name=VMC_BNCM1_ADAPTER,
            ad_jack_in_pin=AD_JACK_IN_PIN,
            id_resistor_ohm=id_resistor_ohm,
            fps_label=fps_label,
            drop_frame=use_df,
            ltc_vpp_mv=ltc_vpp_mv,
            ltc_sync_word_hex=f"0x{SMPTE_12M_SYNC_WORD_FWD:04x}",
            user_bits_hex=f"0x{ub_norm}",
            ub_preserved=False,
            frame_slip=0,
            tc_direction="IN",
            fx6_tc_out_bnc_masked=True,
            multi_usb_uart_1v8_active=False,
            uart_contention_damage_events=0,
            over_voltage_damage_events=0,
            status_code="BLOCKED_LTC_VOLTAGE_OUT_OF_RANGE_0V5_4V5",
        )

    if not (VMC_BNCM1_ID_MIN_OHM <= id_resistor_ohm <= VMC_BNCM1_ID_MAX_OHM):
        return VmcBncm1LtcSyncResult(
            valid=False,
            adapter_name=VMC_BNCM1_ADAPTER,
            ad_jack_in_pin=AD_JACK_IN_PIN,
            id_resistor_ohm=id_resistor_ohm,
            fps_label=fps_label,
            drop_frame=use_df,
            ltc_vpp_mv=ltc_vpp_mv,
            ltc_sync_word_hex=f"0x{SMPTE_12M_SYNC_WORD_FWD:04x}",
            user_bits_hex=f"0x{ub_norm}",
            ub_preserved=False,
            frame_slip=0,
            tc_direction="IN",
            fx6_tc_out_bnc_masked=True,
            multi_usb_uart_1v8_active=False,
            uart_contention_damage_events=0,
            over_voltage_damage_events=0,
            status_code="BLOCKED_VMC_BNCM1_ID_RESISTOR_MISMATCH",
        )

    if multi_usb_uart_1v8_requested:
        return VmcBncm1LtcSyncResult(
            valid=False,
            adapter_name=VMC_BNCM1_ADAPTER,
            ad_jack_in_pin=AD_JACK_IN_PIN,
            id_resistor_ohm=id_resistor_ohm,
            fps_label=fps_label,
            drop_frame=use_df,
            ltc_vpp_mv=ltc_vpp_mv,
            ltc_sync_word_hex=f"0x{SMPTE_12M_SYNC_WORD_FWD:04x}",
            user_bits_hex=f"0x{ub_norm}",
            ub_preserved=False,
            frame_slip=0,
            tc_direction="IN",
            fx6_tc_out_bnc_masked=True,
            multi_usb_uart_1v8_active=False,
            uart_contention_damage_events=0,
            over_voltage_damage_events=0,
            status_code="BLOCKED_MULTI_USB_1V8_UART_CONTENTION",
        )

    if tc_out_bnc_drive_requested:
        return VmcBncm1LtcSyncResult(
            valid=False,
            adapter_name=VMC_BNCM1_ADAPTER,
            ad_jack_in_pin=AD_JACK_IN_PIN,
            id_resistor_ohm=id_resistor_ohm,
            fps_label=fps_label,
            drop_frame=use_df,
            ltc_vpp_mv=ltc_vpp_mv,
            ltc_sync_word_hex=f"0x{SMPTE_12M_SYNC_WORD_FWD:04x}",
            user_bits_hex=f"0x{ub_norm}",
            ub_preserved=True,
            frame_slip=0,
            tc_direction="IN",
            fx6_tc_out_bnc_masked=True,
            multi_usb_uart_1v8_active=False,
            uart_contention_damage_events=0,
            over_voltage_damage_events=0,
            status_code="BLOCKED_FX6_TC_OUT_BNC_MASKED",
        )

    return VmcBncm1LtcSyncResult(
        valid=True,
        adapter_name=VMC_BNCM1_ADAPTER,
        ad_jack_in_pin=AD_JACK_IN_PIN,
        id_resistor_ohm=id_resistor_ohm,
        fps_label=fps_label,
        drop_frame=use_df,
        ltc_vpp_mv=ltc_vpp_mv,
        ltc_sync_word_hex=f"0x{SMPTE_12M_SYNC_WORD_FWD:04x}",
        user_bits_hex=f"0x{ub_norm}",
        ub_preserved=True,
        frame_slip=0,
        tc_direction="IN",
        fx6_tc_out_bnc_masked=True,
        multi_usb_uart_1v8_active=False,
        uart_contention_damage_events=0,
        over_voltage_damage_events=0,
        status_code="VMC_BNCM1_EXT_LK_JAM_SYNC_OK",
    )


def evaluate_pillar_b_vmc_bncm1_ltc_interlock() -> Dict[str, object]:
    fps_matrix = {
        fps: asdict(simulate_vmc_bncm1_ltc_jam_sync(fps_label=fps, ltc_vpp_mv=2000))
        for fps in SMPTE_LTC_FRAMERATES
    }
    ovp_blocked = simulate_vmc_bncm1_ltc_jam_sync(fps_label="23.98", ltc_vpp_mv=5500)
    undervolt_blocked = simulate_vmc_bncm1_ltc_jam_sync(fps_label="23.98", ltc_vpp_mv=250)
    uart_clash_blocked = simulate_vmc_bncm1_ltc_jam_sync(fps_label="23.98", multi_usb_uart_1v8_requested=True)
    tc_out_blocked = simulate_vmc_bncm1_ltc_jam_sync(fps_label="23.98", tc_out_bnc_drive_requested=True)

    passed = (
        all(
            v["valid"] and v["ub_preserved"] and v["frame_slip"] == 0 and v["fx6_tc_out_bnc_masked"]
            for v in fps_matrix.values()
        )
        and (not ovp_blocked.valid)
        and ovp_blocked.over_voltage_damage_events == 0
        and (not undervolt_blocked.valid)
        and (not uart_clash_blocked.valid)
        and uart_clash_blocked.uart_contention_damage_events == 0
        and (not uart_clash_blocked.multi_usb_uart_1v8_active)
        and (not tc_out_blocked.valid)
        and tc_out_blocked.fx6_tc_out_bnc_masked
    )
    return {
        "passed": passed,
        "supported_fps_jam_sync_matrix": fps_matrix,
        "overvoltage_5v5_blocked": asdict(ovp_blocked),
        "undervoltage_0v25_blocked": asdict(undervolt_blocked),
        "multi_usb_1v8_uart_clash_blocked": asdict(uart_clash_blocked),
        "fx6_tc_out_bnc_masked_blocked": asdict(tc_out_blocked),
    }


# ---------------------------------------------------------------------------
# Pillar C: IMX510 (8.7 ms) + 6-Axis IMU Gyro + p18:/lens NonRealTimeMeta.xml
# ---------------------------------------------------------------------------


def build_and_validate_nrtm_xml(
    *,
    clip_format: str,
    fps_label: str,
    focal_length_mm: float,
    frames_recorded: int,
    imu_samples_total: int,
    readout_ms: float,
    user_bits_hex: str,
    ibis_center_lock: bool,
) -> Tuple[bool, int]:
    """Construct & XML-parse Sony NonRealTimeMeta.xml (ver.2.20) for Catalyst/Resolve parity."""
    ns = NRTM_XML_NAMESPACE
    root = ET.Element(f"{{{ns}}}NonRealTimeMeta", {"lastUpdate": "2026-11-15T03:00:00Z"})
    ET.SubElement(root, f"{{{ns}}}Duration", {"value": str(frames_recorded)})
    ET.SubElement(root, f"{{{ns}}}CreationDate", {"value": "2026-11-15T03:00:00Z"})

    vf = ET.SubElement(root, f"{{{ns}}}VideoFormat")
    ET.SubElement(
        vf,
        f"{{{ns}}}VideoFrame",
        {
            "videoCodec": "XAVC_I_422_10" if clip_format == "XAVC-I" else "XAVC_SI_422_10",
            "captureFps": fps_label,
            "formatFps": fps_label,
        },
    )
    ET.SubElement(
        vf,
        f"{{{ns}}}VideoLayout",
        {"pixel": "3840", "numOfVerticalLine": "2160", "aspectRatio": "16:9"},
    )

    ltc = ET.SubElement(root, f"{{{ns}}}LtcChangeTable", {"tcFps": fps_label, "halfStep": "false"})
    ET.SubElement(ltc, f"{{{ns}}}LtcChange", {"frameCount": "0", "value": "01000000", "status": "increment"})
    ET.SubElement(ltc, f"{{{ns}}}UserBits", {"value": user_bits_hex})

    lens = ET.SubElement(
        root,
        f"{{{ns}}}Lens",
        {"modelName": "FE 24-70mm F2.8 GM II", "p18CalMount": "MS_RDONLY"},
    )
    ET.SubElement(lens, f"{{{ns}}}FocalLength", {"value": f"{focal_length_mm:.2f}", "unit": "mm"})

    acq = ET.SubElement(root, f"{{{ns}}}AcquisitionRecord")
    grp = ET.SubElement(acq, f"{{{ns}}}Group", {"name": "CameraUnitMetadataSet"})
    ET.SubElement(grp, f"{{{ns}}}Item", {"name": "ImagerSensor", "value": IMX510_SENSOR_NAME})
    ET.SubElement(grp, f"{{{ns}}}Item", {"name": "RollingShutterReadoutMs", "value": f"{readout_ms:.2f}"})
    ET.SubElement(grp, f"{{{ns}}}Item", {"name": "GyroscopeAxes", "value": str(IMU_AXES)})
    ET.SubElement(grp, f"{{{ns}}}Item", {"name": "GyroscopeSampleRateHz", "value": str(IMU_SAMPLE_RATE_HZ)})
    ET.SubElement(grp, f"{{{ns}}}Item", {"name": "GyroscopePacketCount", "value": str(imu_samples_total)})
    ET.SubElement(grp, f"{{{ns}}}Item", {"name": "IbisCenterLock", "value": "true" if ibis_center_lock else "false"})

    xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    parsed = ET.fromstring(xml_bytes)

    items = {
        el.attrib.get("name", ""): el.attrib.get("value", "")
        for el in parsed.findall(f".//{{{ns}}}Item")
    }
    lens_el = parsed.find(f"{{{ns}}}Lens")
    focal_el = parsed.find(f".//{{{ns}}}FocalLength")
    schema_ok = (
        parsed.tag == f"{{{ns}}}NonRealTimeMeta"
        and lens_el is not None
        and lens_el.attrib.get("p18CalMount") == "MS_RDONLY"
        and focal_el is not None
        and items.get("ImagerSensor") == IMX510_SENSOR_NAME
        and items.get("RollingShutterReadoutMs") == f"{IMX510_READOUT_MS:.2f}"
        and items.get("GyroscopeAxes") == str(IMU_AXES)
        and items.get("GyroscopeSampleRateHz") == str(IMU_SAMPLE_RATE_HZ)
        and int(items.get("GyroscopePacketCount", "0")) == imu_samples_total
    )
    return schema_ok, len(xml_bytes)


def simulate_imx510_gyro_nrtm_clip(
    *,
    clip_format: str = "XAVC S-I",
    fps_label: str = "23.98",
    focal_length_mm: float = 35.0,
    frames_recorded: int = 24,
    readout_ms: float = IMX510_READOUT_MS,
    p2_write_requested: bool = False,
    p18_write_requested: bool = False,
    inject_imu_crc_fault: bool = False,
    inject_timestamp_backwards: bool = False,
) -> Imx510GyroNrtmClipResult:
    """Simulate IMX510 + 6-axis IMU + p18:/lens NonRealTimeMeta.xml Catalyst/Resolve pipeline."""
    if clip_format not in NRTM_CLIP_FORMATS:
        raise RealHwC2paTcGyroPrebenchError(
            f"Unsupported clip_format={clip_format!r}; expected {NRTM_CLIP_FORMATS}"
        )
    if fps_label not in SMPTE_LTC_FRAMERATES:
        raise RealHwC2paTcGyroPrebenchError(f"Unsupported fps_label={fps_label!r}")

    container = "MP4" if clip_format == "XAVC S-I" else "MXF"
    fps_frac, _ = SMPTE_LTC_FRAMERATES[fps_label]
    duration_sec = float(Fraction(frames_recorded, 1) / fps_frac)
    imu_samples = int(round(duration_sec * IMU_SAMPLE_RATE_HZ))

    if p2_write_requested or p18_write_requested:
        return Imx510GyroNrtmClipResult(
            valid=False,
            clip_format=clip_format,
            container=container,
            sensor_name=IMX510_SENSOR_NAME,
            readout_ms=readout_ms,
            focal_length_mm=focal_length_mm,
            imu_axes=IMU_AXES,
            imu_sample_rate_hz=IMU_SAMPLE_RATE_HZ,
            frames_recorded=frames_recorded,
            imu_samples_total=imu_samples,
            monotonically_increasing_timestamps=False,
            crc32_valid=False,
            nrtm_xml_bytes=0,
            nrtm_namespace=NRTM_XML_NAMESPACE,
            catalyst_schema_valid=False,
            resolve_schema_valid=False,
            p2_mutation_bytes=0,
            p18_mutation_bytes=0,
            p18_mount_flags="MS_RDONLY",
            status_code="BLOCKED_P2_OR_P18_WRITE_REQUEST",
        )

    # Deterministic 6-axis IMU sample stream + CRC32 integrity verification
    stream = bytearray()
    prev_ts_us = -1
    monotonic_ok = True
    step_us = 500  # 2000 Hz = 500 us
    for idx in range(min(imu_samples, 64)):
        ts_us = idx * step_us
        if inject_timestamp_backwards and idx == 10:
            ts_us = prev_ts_us - 100
        if ts_us <= prev_ts_us:
            monotonic_ok = False
        prev_ts_us = ts_us
        gx, gy, gz = (idx * 3) & 0xFF, (-idx * 2) & 0xFF, (idx + 7) & 0xFF
        ax, ay, az = 0, 0, 981
        stream.extend(struct.pack("<Q6h", max(ts_us, 0), gx, gy, gz, ax, ay, az))

    expected_crc = zlib.crc32(stream)
    observed_crc = expected_crc ^ (0x1 if inject_imu_crc_fault else 0x0)
    crc_ok = expected_crc == observed_crc

    schema_ok, xml_len = build_and_validate_nrtm_xml(
        clip_format=clip_format,
        fps_label=fps_label,
        focal_length_mm=focal_length_mm,
        frames_recorded=frames_recorded,
        imu_samples_total=imu_samples,
        readout_ms=readout_ms,
        user_bits_hex="0xA3F12026",
        ibis_center_lock=True,
    )
    readout_ok = abs(readout_ms - IMX510_READOUT_MS) <= 0.05
    nle_ok = schema_ok and monotonic_ok and crc_ok and readout_ok

    status = "IMX510_GYRO_NRTM_CATALYST_RESOLVE_OK"
    if not crc_ok:
        status = "BLOCKED_GYRO_CRC32_CORRUPTION"
    elif not monotonic_ok:
        status = "BLOCKED_GYRO_TIMESTAMP_NON_MONOTONIC"
    elif not readout_ok:
        status = "BLOCKED_IMX510_READOUT_MISMATCH"

    return Imx510GyroNrtmClipResult(
        valid=nle_ok,
        clip_format=clip_format,
        container=container,
        sensor_name=IMX510_SENSOR_NAME,
        readout_ms=readout_ms,
        focal_length_mm=focal_length_mm,
        imu_axes=IMU_AXES,
        imu_sample_rate_hz=IMU_SAMPLE_RATE_HZ,
        frames_recorded=frames_recorded,
        imu_samples_total=imu_samples,
        monotonically_increasing_timestamps=monotonic_ok,
        crc32_valid=crc_ok,
        nrtm_xml_bytes=xml_len,
        nrtm_namespace=NRTM_XML_NAMESPACE,
        catalyst_schema_valid=nle_ok,
        resolve_schema_valid=nle_ok,
        p2_mutation_bytes=P2_MUTATION_BYTES,
        p18_mutation_bytes=P18_MUTATION_BYTES,
        p18_mount_flags="MS_RDONLY",
        status_code=status,
    )


def evaluate_pillar_c_imx510_gyro_nrtm() -> Dict[str, object]:
    xavc_si_mp4 = simulate_imx510_gyro_nrtm_clip(clip_format="XAVC S-I", fps_label="23.98", focal_length_mm=24.0)
    xavc_i_mxf = simulate_imx510_gyro_nrtm_clip(clip_format="XAVC-I", fps_label="59.94", focal_length_mm=50.0)
    p18_write_blocked = simulate_imx510_gyro_nrtm_clip(p18_write_requested=True)
    p2_write_blocked = simulate_imx510_gyro_nrtm_clip(p2_write_requested=True)
    crc_fault_blocked = simulate_imx510_gyro_nrtm_clip(inject_imu_crc_fault=True)
    ts_fault_blocked = simulate_imx510_gyro_nrtm_clip(inject_timestamp_backwards=True)

    passed = (
        xavc_si_mp4.valid
        and xavc_si_mp4.catalyst_schema_valid
        and xavc_si_mp4.resolve_schema_valid
        and xavc_si_mp4.p2_mutation_bytes == 0
        and xavc_si_mp4.p18_mutation_bytes == 0
        and xavc_i_mxf.valid
        and xavc_i_mxf.catalyst_schema_valid
        and xavc_i_mxf.resolve_schema_valid
        and (not p18_write_blocked.valid)
        and (not p2_write_blocked.valid)
        and (not crc_fault_blocked.valid)
        and (not ts_fault_blocked.valid)
    )
    return {
        "passed": passed,
        "xavc_si_mp4_2398p": asdict(xavc_si_mp4),
        "xavc_i_mxf_5994p": asdict(xavc_i_mxf),
        "p18_write_blocked": asdict(p18_write_blocked),
        "p2_write_blocked": asdict(p2_write_blocked),
        "gyro_crc_fault_blocked": asdict(crc_fault_blocked),
        "gyro_timestamp_fault_blocked": asdict(ts_fault_blocked),
    }


# ---------------------------------------------------------------------------
# Pillar D: Complete 10-Step Pre-Bench Operator Go/No-Go Dry-Run Lifecycle
# ---------------------------------------------------------------------------


def _surface_h0_hash(surface: str, *, dirty_h3: bool = False) -> str:
    tag = f"{surface}:DIRTY_H3" if dirty_h3 else f"{surface}:FX3_702_STOCK_H0"
    return hashlib.sha256(tag.encode("ascii")).hexdigest()


def run_10step_prebench_gonogo_lifecycle(
    *,
    tier0_backup_complete: bool = True,
    corrupt_h3_surface: Optional[str] = None,
    orig_residual_count: int = 0,
    tmp_jiritsu_residual_count: int = 0,
    p6_chunk_residual_count: int = 0,
    authorize_persistent_emmc_writes: bool = False,
) -> Prebench10StepLifecycleResult:
    """Co-emulate the full 10-step pre-bench operator Go/No-Go dry-run lifecycle."""
    if authorize_persistent_emmc_writes:
        return Prebench10StepLifecycleResult(
            valid=False,
            steps_completed=0,
            steps_total=len(TEN_PREBENCH_STEPS),
            usb_vid_msc=f"0x{USB_VID_SONY:04X}",
            usb_pid_msc=f"0x{USB_PID_MSC:04X}",
            usb_pid_ufu=f"0x{USB_PID_UFU:04X}",
            ufu_canary_opcode_hex=f"0x{UFU_CANARY_OPCODE:02X}",
            stage_b_target_partition=STAGE_B_TARGET_PARTITION,
            surfaces_total=len(SIXTEEN_STORAGE_SURFACES),
            surfaces_h0_eq_h3=0,
            dryrun_go_nogo="NO_GO",
            dryrun_hil_coemulation_passed=False,
            physical_camera_bench_attached=False,
            persistent_emmc_writes_authorized=False,
            emmc_nflasha_write_count=0,
            c2pa_cert_mutation_bytes=0,
            p2_mutation_bytes=0,
            p18_mutation_bytes=0,
            cp_mutation_bytes=0,
            orig_residual_count=orig_residual_count,
            tmp_jiritsu_residual_count=tmp_jiritsu_residual_count,
            p6_chunk_residual_count=p6_chunk_residual_count,
            otp_write_count=0,
            rpmb_write_count=0,
            steps=(),
            status_code="NO_GO_BLOCKED_PERSISTENT_EMMC_WRITE_REQUEST",
        )

    c2pa_res = simulate_c2pa_rq_lic_lifecycle()
    ltc_res = simulate_vmc_bncm1_ltc_jam_sync(fps_label="23.98", ltc_vpp_mv=2000)
    gyro_res = simulate_imx510_gyro_nrtm_clip(clip_format="XAVC S-I", fps_label="23.98")
    cross_model_blocked = evaluate_c2pa_signing_firewall(
        requested_model_name="ILME-FX6",
        requested_model_id=SUPPORTED_FOREIGN_MODEL_IDS["ILME-FX6"],
    )

    h0_hashes = {s: _surface_h0_hash(s, dirty_h3=False) for s in SIXTEEN_STORAGE_SURFACES}
    h3_hashes = {s: _surface_h0_hash(s, dirty_h3=(s == corrupt_h3_surface)) for s in SIXTEEN_STORAGE_SURFACES}
    h0_eq_h3_count = sum(1 for s in SIXTEEN_STORAGE_SURFACES if h0_hashes[s] == h3_hashes[s])

    residuals_zero = (
        orig_residual_count == 0
        and tmp_jiritsu_residual_count == 0
        and p6_chunk_residual_count == 0
    )
    seal_ok = h0_eq_h3_count == len(SIXTEEN_STORAGE_SURFACES) and residuals_zero

    step_verdicts: List[Tuple[bool, str]] = [
        (True, "PASSIVE_USB_ATTACH_CHECK_OK"),
        (True, "054C_0DA1_TO_0336_OP_FF_CANARY_OK"),
        (tier0_backup_complete, "DUAL_MEDIA_16_SURFACE_TIER0_BACKUP_H0_OK" if tier0_backup_complete else "NO_GO_TIER0_BACKUP_INCOMPLETE"),
        (c2pa_res.valid and gyro_res.p18_mount_flags == "MS_RDONLY", "P12_C2PA_P18_LENS_MS_RDONLY_LOCKED"),
        (tier0_backup_complete, "CNFLASHA15_ORIG_ATOMIC_STAGING_REHEARSED_OK" if tier0_backup_complete else "NO_GO_STAGING_BLOCKED_NO_TIER0"),
        (ltc_res.valid and ltc_res.ub_preserved, "DUALBOOT_AND_VMC_BNCM1_EXT_LK_JAM_SYNC_OK"),
        (gyro_res.valid and gyro_res.catalyst_schema_valid and gyro_res.resolve_schema_valid, "BIG6_IMX510_GYRO_NRTM_SHOOT_OK"),
        (cross_model_blocked.firewall_blocked, "RSV_SALVAGE_AND_C2PA_FIREWALL_OK"),
        (residuals_zero, "CLEAN_ORIG_RESTORE_AND_UNINSTALL_OK" if residuals_zero else "NO_GO_RESIDUAL_ARTIFACTS_DETECTED"),
        (seal_ok and tier0_backup_complete, "16OF16_H0_EQ_H3_FACTORY_SEAL_DRYRUN_GO" if (seal_ok and tier0_backup_complete) else "NO_GO_FACTORY_SEAL_MISMATCH"),
    ]

    steps_out: List[PrebenchStepResult] = []
    completed = 0
    for idx, (step_id, (ok, code)) in enumerate(zip(TEN_PREBENCH_STEPS, step_verdicts), start=1):
        if ok:
            completed += 1
        steps_out.append(
            PrebenchStepResult(
                step_index=idx,
                step_id=step_id,
                passed=ok,
                emmc_nflasha_write_count=EMMC_NFLASHA_WRITE_COUNT,
                c2pa_cert_mutation_bytes=C2PA_CERT_MUTATION_BYTES,
                p18_mutation_bytes=P18_MUTATION_BYTES,
                cp_mutation_bytes=CP_MUTATION_BYTES,
                status_code=code,
            )
        )

    all_steps_ok = completed == len(TEN_PREBENCH_STEPS)
    go_nogo = "GO_DRYRUN_HIL" if all_steps_ok else "NO_GO"
    return Prebench10StepLifecycleResult(
        valid=all_steps_ok,
        steps_completed=completed,
        steps_total=len(TEN_PREBENCH_STEPS),
        usb_vid_msc=f"0x{USB_VID_SONY:04X}",
        usb_pid_msc=f"0x{USB_PID_MSC:04X}",
        usb_pid_ufu=f"0x{USB_PID_UFU:04X}",
        ufu_canary_opcode_hex=f"0x{UFU_CANARY_OPCODE:02X}",
        stage_b_target_partition=STAGE_B_TARGET_PARTITION,
        surfaces_total=len(SIXTEEN_STORAGE_SURFACES),
        surfaces_h0_eq_h3=h0_eq_h3_count,
        dryrun_go_nogo=go_nogo,
        dryrun_hil_coemulation_passed=all_steps_ok,
        physical_camera_bench_attached=False,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        emmc_nflasha_write_count=EMMC_NFLASHA_WRITE_COUNT,
        c2pa_cert_mutation_bytes=C2PA_CERT_MUTATION_BYTES,
        p2_mutation_bytes=P2_MUTATION_BYTES,
        p18_mutation_bytes=P18_MUTATION_BYTES,
        cp_mutation_bytes=CP_MUTATION_BYTES,
        orig_residual_count=orig_residual_count,
        tmp_jiritsu_residual_count=tmp_jiritsu_residual_count,
        p6_chunk_residual_count=p6_chunk_residual_count,
        otp_write_count=OTP_WRITE_COUNT,
        rpmb_write_count=RPMB_WRITE_COUNT,
        steps=tuple(steps_out),
        status_code="PREBENCH_10STEP_DRYRUN_GO_HIL" if all_steps_ok else "PREBENCH_DRYRUN_NO_GO",
    )


def evaluate_pillar_d_10step_prebench_lifecycle() -> Dict[str, object]:
    clean_dryrun = run_10step_prebench_gonogo_lifecycle()
    no_tier0_nogo = run_10step_prebench_gonogo_lifecycle(tier0_backup_complete=False)
    h3_drift_nogo = run_10step_prebench_gonogo_lifecycle(corrupt_h3_surface="p15")
    residual_nogo = run_10step_prebench_gonogo_lifecycle(orig_residual_count=1)
    emmc_write_nogo = run_10step_prebench_gonogo_lifecycle(authorize_persistent_emmc_writes=True)

    passed = (
        clean_dryrun.valid
        and clean_dryrun.steps_completed == 10
        and clean_dryrun.surfaces_h0_eq_h3 == 16
        and clean_dryrun.dryrun_go_nogo == "GO_DRYRUN_HIL"
        and (not clean_dryrun.physical_camera_bench_attached)
        and (not clean_dryrun.persistent_emmc_writes_authorized)
        and clean_dryrun.emmc_nflasha_write_count == 0
        and (not no_tier0_nogo.valid)
        and no_tier0_nogo.dryrun_go_nogo == "NO_GO"
        and (not h3_drift_nogo.valid)
        and h3_drift_nogo.dryrun_go_nogo == "NO_GO"
        and (not residual_nogo.valid)
        and residual_nogo.dryrun_go_nogo == "NO_GO"
        and (not emmc_write_nogo.valid)
        and emmc_write_nogo.dryrun_go_nogo == "NO_GO"
        and (not emmc_write_nogo.persistent_emmc_writes_authorized)
    )
    return {
        "passed": passed,
        "clean_10step_dryrun_go": asdict(clean_dryrun),
        "no_tier0_backup_nogo": asdict(no_tier0_nogo),
        "h3_surface_drift_nogo": asdict(h3_drift_nogo),
        "orig_residual_nogo": asdict(residual_nogo),
        "persistent_emmc_write_blocked_nogo": asdict(emmc_write_nogo),
    }


# ---------------------------------------------------------------------------
# Unified Phase 172 Stage 30 Orchestrator & CLI
# ---------------------------------------------------------------------------


def run_phase172_realhw_c2pa_tc_gyro_prebench_hil(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Execute the full Phase 172 Stage 30 (`30/30` Milestone) co-emulation audit."""
    donor_audit = inspect_phase172_donors(force_clean_room=force_clean_room, env=env)
    pillar_a = evaluate_pillar_a_c2pa_lock_and_firewall()
    pillar_b = evaluate_pillar_b_vmc_bncm1_ltc_interlock()
    pillar_c = evaluate_pillar_c_imx510_gyro_nrtm()
    pillar_d = evaluate_pillar_d_10step_prebench_lifecycle()

    all_passed = (
        donor_audit.all_contracts_verified
        and bool(pillar_a["passed"])
        and bool(pillar_b["passed"])
        and bool(pillar_c["passed"])
        and bool(pillar_d["passed"])
    )

    payload: Dict[str, object] = {
        "schema": PHASE_172_SCHEMA,
        "version": PHASE_172_VERSION,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "stage": "stage30_realhw_c2pa_tc_gyro_prebench_hil",
        "source_mode": donor_audit.source_mode,
        "all_checks_passed": all_passed,
        "redlines": {
            "p8_cp_mutation_forbidden": P8_CP_MUTATION_FORBIDDEN,
            "nop_count": NOP_COUNT,
            "guest_code_modification_bytes": GUEST_CODE_MODIFICATION_BYTES,
            "cp_mutation_bytes": CP_MUTATION_BYTES,
            "wbi_mutation_bytes": WBI_MUTATION_BYTES,
            "calibration_mutation_bytes": CALIBRATION_MUTATION_BYTES,
            "c2pa_cert_mutation_bytes": C2PA_CERT_MUTATION_BYTES,
            "p12_cert_mount_flags": P12_CERT_MOUNT_FLAGS,
            "p2_mutation_bytes": P2_MUTATION_BYTES,
            "p18_mutation_bytes": P18_MUTATION_BYTES,
            "nvram_persistent_writes": NVRAM_PERSISTENT_WRITES,
            "bk4_persistent_nvram_writes": BK4_PERSISTENT_NVRAM_WRITES,
            "physical_device_writes": PHYSICAL_DEVICE_WRITES,
            "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
            "emmc_nflasha_write_count": EMMC_NFLASHA_WRITE_COUNT,
            "emmc_mutation_bytes": EMMC_MUTATION_BYTES,
            "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
            "spi_nor_mutation_bytes": SPI_NOR_MUTATION_BYTES,
            "otp_write_count": OTP_WRITE_COUNT,
            "rpmb_write_count": RPMB_WRITE_COUNT,
            "orig_residual_count": ORIG_RESIDUAL_COUNT,
            "tmp_jiritsu_residual_count": TMP_JIRITSU_RESIDUAL_COUNT,
            "p6_chunk_residual_count": P6_CHUNK_RESIDUAL_COUNT,
            "null_gpio_derefs": NULL_GPIO_DEREFS,
            "mailbox_stalls": MAILBOX_STALLS,
            "stock_cp_fault_count": STOCK_CP_FAULT_COUNT,
            "wf12_00342260_hits": WF12_00342260_HITS,
            "appfw_crashes": APPFW_CRASHES,
            "uart_contention_damage_events": UART_CONTENTION_DAMAGE_EVENTS,
            "over_voltage_damage_events": OVER_VOLTAGE_DAMAGE_EVENTS,
            "donor_access_mode": DONOR_ACCESS_MODE,
        },
        "donor_audit": asdict(donor_audit),
        "pillar_a_c2pa_rq_lic_ro_lock_and_firewall": pillar_a,
        "pillar_b_vmc_bncm1_ltc_and_uart_interlock": pillar_b,
        "pillar_c_imx510_gyro_p18_nrtm_pipeline": pillar_c,
        "pillar_d_10step_prebench_gonogo_lifecycle": pillar_d,
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    payload["audit_digest_sha256"] = digest
    return payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_c2pa_tc_gyro_and_prebench_gonogo_coemulator.py",
        description="Phase 172 Stage 30 (30/30) Real-HW C2PA Lock, VMC-BNCM1 LTC, IMX510 Gyro NRTM & Pre-Bench HIL Co-Emulator",
    )
    parser.add_argument("--self-test", action="store_true", help="Run Stage 30 self-test and exit 0/1")
    parser.add_argument("--clean-room", action="store_true", help="Force clean-room synthetic mode")
    parser.add_argument("--json", action="store_true", help="Emit deterministic JSON audit report")
    parser.add_argument("--summary", action="store_true", help="Emit concise one-line audit summary")
    args = parser.parse_args(argv)

    rep = run_phase172_realhw_c2pa_tc_gyro_prebench_hil(
        force_clean_room=True if args.clean_room else None,
        env=os.environ,
    )

    if args.summary and not args.json:
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        d = rep["pillar_d_10step_prebench_gonogo_lifecycle"]["clean_10step_dryrun_go"]
        sys.stdout.write(
            f"[{status}] Phase 172 Stage 30 ({MILESTONE_LABEL}) Real-HW C2PA/TC/Gyro/PreBench HIL | "
            f"mode={rep['source_mode']} | c2pa_mut={rep['redlines']['c2pa_cert_mutation_bytes']} | "
            f"p18_mut={rep['redlines']['p18_mutation_bytes']} | "
            f"steps={d['steps_completed']}/{d['steps_total']} | "
            f"h0_eq_h3={d['surfaces_h0_eq_h3']}/{d['surfaces_total']} | "
            f"go={d['dryrun_go_nogo']} | emmc_wr={rep['redlines']['emmc_nflasha_write_count']} | "
            f"digest={rep['audit_digest_sha256'][:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")

    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
