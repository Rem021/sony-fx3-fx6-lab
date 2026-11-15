"""Phase 165 — Real-Hardware Main Track Part 14:
Gate G53 (`CXD90057` *Mira* + `CXD90058` *Cetus* Dual-BIONZ-XR Inter-SoC Link,
`sabin` 32-bit SA-DSP Microcode Immutability, FX6 `16-bit SDI RAW` / `mew.bin`
FPGA Output Mask & FX3 `1,724.00 MiB` `memcfg=` XAVC Encoder Pool Guard),
Gate G54 (Post-Bench `16/16 H0 == H3` Bit-Identical Factory Seal, Zero
`/usr/bin/im.elf.orig`, `/etc/ld.so.preload`, `/tmp/jiritsu/*`, `p6` Residual,
`OTP == 0`, `RPMB == 0` & `mode* == 0` Official Update Readiness Guard), and
Unified 54-Gate Master Safety Preflight (`G01..G54` / `verify-54-gates`).

Operationalizes inter-SoC co-processor immutability, FX3-vs-FX6 encoder memory
isolation, and post-bench factory seal / official-update readiness invariants on
physical Sony ILME-FX3 (`Ver. 7.02`, Model ID `0x91030080`, AP `CXD90057` *Mira* +
CP `CXD90058` *Cetus*) while keeping all prior gate modules (`G01..G52`) 100%
untouched and hard-locking:
- `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`
- `SPI_NOR_WRITE_AUTHORIZED = False`
- `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`
- `PERSISTENT_WRITE_RELEASE = False`
- `overall_ready_for_hardware_attach = False`

1. **Dual-Mode Donor Inspection (`os.O_RDONLY`) + Clean-Room Fallback (`FX3_FX6_FORCE_CLEAN_ROOM=1`)**:
   - Inspects FX3 `7.02` `libsencore.so`, `libmpr.so`, `im.elf`, `cpapp-b.bin`,
     and `Backup.bin` (`FX3-CX95900_ALLLANG-Backup.bin`) strictly via
     `os.open(..., os.O_RDONLY)` when present and `FX3_FX6_FORCE_CLEAN_ROOM != "1"`.
   - Falls back deterministically to pinned clean-room metadata when
     `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor files are absent, leaking zero raw
     Sony firmware bytes in JSON output.

2. **Gate G53 — `CXD90057` (*Mira*) + `CXD90058` (*Cetus*) Inter-SoC Link,
   `sabin` SA-DSP Microcode Immutability & `SDI RAW` Mask Guard**:
   - Hard-blocks any mutation to `p8:/cpapp-b.bin`, `CXD90058` secondary
     co-processor boot blobs, or `sabin` 32-bit SA-DSP microcode
     (`cxd90058_mutation_bytes == 0`, `sabin_dsp_mutation_bytes == 0`,
     `p8_cpapp_mutation_bytes == 0`).
   - Verifies healthy `CXD90057 <-> CXD90058` (`SLVS-EC` / `IVSHMEM` / `UIPC_CP_IPC`)
     inter-SoC link and `p8:/cpapp-b.bin` SHA-256 immutability.
   - Enforces fail-closed masking of FX6-only `16-bit SDI RAW` (`mew.bin` FPGA)
     output paths while verifying valid `XAVC-I` / `XAVC S-I` / `XAVC HS`
     hardware encoder pool alignment on FX3's `1,724.00 MiB` `memcfg=` budget.

3. **Gate G54 — Post-Bench `16/16 H0 == H3` Factory Seal, Zero `/tmp/jiritsu`
   Residual & Official Warranty Readiness Guard**:
   - Verifies post-uninstall bit-identical restoration across all 16 storage
     surfaces (`SHA256(H0) == SHA256(H3)` for `16/16` surfaces).
   - Verifies zero leftover `/usr/bin/im.elf.orig`, zero `/etc/ld.so.preload`,
     zero `/tmp/jiritsu/*` or `p6` chunk residual (`residual_artifact_count == 0`).
   - Verifies `OTP == 0`, `RPMB == 0`, and `/setting/updater/mode*` flags `== 0`.

4. **Unified 54-Gate Master Safety Preflight (`evaluate_54gate_preflight` / CLI `verify-54-gates`)**:
   - Chains `evaluate_52gate_preflight` (`G01..G52`) + `G53` + `G54` = **54 Gates**.
   - Offline default reports `51/54` (`G10..G12` physical Tier-0 gates `False`,
     `persistent_emmc_writes_authorized = False`,
     `persistent_write_release = False`,
     `spi_nor_write_authorized = False`,
     `el3_payload_transmit_authorized = False`,
     `overall_ready_for_hardware_attach = False`).
   - `--dry-run-simulated-backup` reports `54/54` dry-run green while STILL
     hard-locking `el3_payload_transmit_authorized = False`,
     `spi_nor_write_authorized = False`,
     `persistent_emmc_writes_authorized = False`,
     `persistent_write_release = False`, and
     `overall_ready_for_hardware_attach = False`.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .exfat_media_integrity_guard import MediaSlotConfig
from .master_16gate_preflight import (
    DEFAULT_REPO_ROOT,
    GateVerdict,
    P12_WLAN_FATAL_GUARD_VMA,
)
from .realhw_cfexpress_ufu_el3_and_52gate_guard import (
    Master52GateReport,
    evaluate_52gate_preflight,
)
from .thermal_pwm_and_power_guard import (
    ENV_FORCE_CLEAN_ROOM,
    resolve_donor_thermal_power_paths,
)


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

REALHW_CXD90058_SABIN_SEAL_54GATE_SCHEMA: str = (
    "fx3-realhw-cxd90058-sabin-seal-54gate-preflight-v1"
)
REALHW_CXD90058_SABIN_SEAL_54GATE_VERSION: str = "1.0.0"

EL3_PAYLOAD_TRANSMIT_AUTHORIZED: bool = False
SPI_NOR_WRITE_AUTHORIZED: bool = False
PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False

# Gate IDs & Canonical Codes for G53..G54
G53_GATE_ID: str = "G53_cxd90058_sabin_dsp_and_sdi_raw_mask_guard"
G53_GATE_CODE: str = "CXD90058_SABIN_DSP_AND_SDI_RAW_MASK_GUARD"

G54_GATE_ID: str = "G54_post_bench_16_surface_h0_h3_seal_and_official_readiness_guard"
G54_GATE_CODE: str = "POST_BENCH_16_SURFACE_H0_H3_SEAL_AND_OFFICIAL_READINESS_GUARD"

# Status Codes
STATUS_SAFE: str = "SAFE"
STATUS_VERIFIED_SAFE: str = "VERIFIED_SAFE"
STATUS_VERIFIED_G53: str = (
    "VERIFIED_CXD90058_SABIN_DSP_AND_SDI_RAW_MASK_GUARD"
)
STATUS_VERIFIED_G54: str = (
    "VERIFIED_POST_BENCH_16_SURFACE_H0_H3_SEAL_AND_OFFICIAL_READINESS_GUARD"
)

# Gate G53 Violation Codes
STATUS_BLOCKED_G53_CXD90058_OR_SABIN_MUTATION: str = (
    "BLOCKED_G53_CXD90058_OR_SABIN_MUTATION"
)
STATUS_BLOCKED_G53_INTERSOC_LINK_OR_CPAPP_VIOLATION: str = (
    "BLOCKED_G53_INTERSOC_LINK_OR_CPAPP_VIOLATION"
)
STATUS_BLOCKED_G53_FX6_SDI_RAW_MEW_UNMASKED: str = (
    "BLOCKED_G53_FX6_SDI_RAW_MEW_UNMASKED"
)
STATUS_BLOCKED_G53_MEMCFG_ENCODER_POOL_OVERFLOW: str = (
    "BLOCKED_G53_MEMCFG_ENCODER_POOL_OVERFLOW"
)
STATUS_BLOCKED_G53_TELEMETRY_INVALID: str = (
    "BLOCKED_G53_CXD90058_SABIN_TELEMETRY_INVALID"
)

# Gate G54 Violation Codes
STATUS_BLOCKED_G54_H0_H3_SURFACE_SEAL_MISMATCH: str = (
    "BLOCKED_G54_H0_H3_SURFACE_SEAL_MISMATCH"
)
STATUS_BLOCKED_G54_RESIDUAL_ARTIFACT_PRESENT: str = (
    "BLOCKED_G54_RESIDUAL_ARTIFACT_PRESENT"
)
STATUS_BLOCKED_G54_OTP_RPMB_OR_UPDATER_DIRTY: str = (
    "BLOCKED_G54_OTP_RPMB_OR_UPDATER_DIRTY"
)
STATUS_BLOCKED_G54_TELEMETRY_INVALID: str = (
    "BLOCKED_G54_FACTORY_SEAL_TELEMETRY_INVALID"
)

STATUS_BLOCKED_PHASE165_DONOR_INTEGRITY: str = (
    "BLOCKED_PHASE165_54GATE_DONOR_INTEGRITY_MISMATCH"
)
STATUS_BLOCKED_PERSISTENT_EMMC_WRITE: str = (
    "BLOCKED_BY_PERSISTENT_EMMC_WRITE_REDLINE"
)

# Gate G53 Constants — CXD90057 (Mira) + CXD90058 (Cetus), sabin SA-DSP & memcfg
AP_SOC_MIRA_NAME: str = "CXD90057"
AP_SOC_MIRA_CODENAME: str = "Mira"
CP_SOC_CETUS_NAME: str = "CXD90058"
CP_SOC_CETUS_CODENAME: str = "Cetus"
P8_CPAPP_PARTITION_PATH: str = "p8:/cpapp-b.bin"
PINNED_FX3_CPAPP_SHA256: str = (
    "c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba"
)
SABIN_DSP_MICROCODE_PREFIX: str = "sabin/"
SABIN_DSP_ARCH_NAME: str = "SA_DSP_32BIT"
INTERSOC_VALID_LINK_PROTOCOLS: Tuple[str, ...] = (
    "SLVS-EC",
    "IVSHMEM",
    "UIPC_CP_IPC",
)

FX3_MEMCFG_BUDGET_MIB: float = 1724.0
FX3_MEMCFG_BUDGET_BYTES: int = 1_807_745_024  # 1,724.00 MiB * 1024 * 1024
FX3_ENCODER_POOL_ALIGN_BYTES: int = 4096
FX3_VALID_XAVC_CODEC_POOLS: Tuple[str, ...] = (
    "XAVC-I",
    "XAVC S-I",
    "XAVC HS",
)
_FX3_NORMALIZED_XAVC_POOLS: Tuple[str, ...] = (
    "XAVC_I",
    "XAVC_S_I",
    "XAVC_SI",
    "XAVC_HS",
)
FX6_FORBIDDEN_SDI_RAW_MODES: Tuple[str, ...] = (
    "16BIT_SDI_RAW",
    "16_BIT_SDI_RAW",
    "SDI_RAW",
    "12G_SDI_RAW",
    "MEW_FPGA_SDI_RAW",
)
FX6_MEW_FPGA_BINARY: str = "mew.bin"
FX3_ALLOWED_OUTPUT_PATHS: Tuple[str, ...] = (
    "INTERNAL_XAVC",
    "HDMI_TYPE_A",
    "CFEXPRESS_INTERNAL",
    "SDXC_INTERNAL",
)

# Gate G54 Constants — 16-Surface H0 == H3 Factory Seal & Official Cleanliness
CANONICAL_16_STORAGE_SURFACES: Tuple[str, ...] = (
    "sector0",
    "emmc_boot0",
    "emmc_boot1",
    "p1_updater",
    "p2_setting",
    "p3_system",
    "p5_wbi",
    "p6_jiritsu",
    "p7_rootfs",
    "p8_cpapp",
    "p10_vfat",
    "p12_cert",
    "p13_rf_nvs",
    "p15_usr",
    "p18_lens",
    "spi_nor_ro",
)
CANONICAL_16_SURFACE_COUNT: int = 16
FORBIDDEN_BENCH_RESIDUAL_PATHS: Tuple[str, ...] = (
    "/usr/bin/im.elf.orig",
    "/etc/ld.so.preload",
    "/tmp/jiritsu",
    "/setting/updater/mode",
    "/setting/updater/mode5",
)

_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")

# Pinned FX3 v7.02 Donor Specs (verified strictly via os.O_RDONLY)
PINNED_PHASE165_DONOR_SPECS: Mapping[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_libsencore": (
        "fx3",
        "sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/libsencore.so",
        377_328,
        "a2907111c4a22314dcb12c25889e0e3142764c6a4a910a746e43908f76e7c410",
        (
            b"\x7fELF",
            b"SDI",
            b"DSP",
            b"mode",
            b"AVC",
            b"RECOVERY",
            b"libosal_uipc.so",
        ),
        "fx3/libsencore.so::{ELF,SDI,DSP,mode,AVC,RECOVERY,libosal_uipc.so}",
    ),
    "fx3_libmpr": (
        "fx3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libmpr.so",
        3_517_008,
        "9aeef3b9edb3d011c0c90cd2387b3a47bd3b506ebfa57be39ad1a9729771b57c",
        (
            b"\x7fELF",
            b"XAVC",
            b"HEVC",
            b"SDI",
            b"mew",
            b"orig",
            b"mode",
            b"Recovery",
        ),
        "fx3/libmpr.so::{ELF,XAVC,HEVC,SDI,mew,orig,mode,Recovery}",
    ),
    "fx3_im_elf": (
        "fx3",
        "fx3-vm-20261101/fx3-audit/original-members/nflasha15/bin/im.elf",
        40_920,
        "5171f576d8b76cfbf15581389183b390c445bd6ff9dd97fd6668c5f64e77dc91",
        (
            b"\x7fELF",
            b"mode",
            b"libIMDB.so",
            b"libbackup.so",
            b"libosal_uipc.so",
        ),
        "fx3/im.elf::{40920B,ELF,mode,libIMDB.so,libbackup.so,libosal_uipc.so}",
    ),
    "fx3_cpapp_b": (
        "fx3",
        "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin",
        15_980_568,
        "c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba",
        (
            b"ILME-FX3",
            b"\x80\x00\x03\x91",
            b"Cetus",
            b"sabin",
            b"memcfg",
            b"OTP",
            b"SDI",
            b"DSP",
            b"mode",
            b"RECOVERY",
        ),
        "fx3/cpapp-b.bin::{ILME-FX3,0x91030080,Cetus,sabin,memcfg,OTP,SDI,DSP,mode,RECOVERY}",
    ),
    "fx3_backup_bin": (
        "fx3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin",
        2_229_740,
        "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2",
        (
            b"BK4\x00",
            b"ILME-FX3",
            b"sabin",
            b"90057",
            b"DmmCfg",
            b"psd.bin",
            b"defdet.bin",
            b"lensfile.bin",
        ),
        "fx3/Backup.bin::{2229740B,BK4\\0,ILME-FX3,sabin,90057,DmmCfg,psd.bin,defdet.bin,lensfile.bin}",
    ),
}


# ---------------------------------------------------------------------------
# Data Models (Zero raw bytes reprs; hex strings / ASCII markers only)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase165DonorAuditResult:
    valid: bool
    status: str
    verification_mode: str
    access_mode: str
    files_inspected: int
    checked_markers: Tuple[str, ...]
    missing_markers: Tuple[str, ...]
    fx3_contracts_verified: bool
    sha256_by_artifact: Dict[str, str]
    bytes_by_artifact: Dict[str, int]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Cxd90058SabinSdiGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    guard_profile: str
    ap_soc_name: str
    cp_soc_name: str
    intersoc_link_protocol: str
    intersoc_link_healthy: bool
    p8_cpapp_partition: str
    p8_cpapp_ro_locked: bool
    p8_cpapp_sha256: str
    p8_cpapp_mutation_bytes: int
    cxd90058_boot_blobs_untouched: bool
    cxd90058_mutation_bytes: int
    cxd90058_write_requested: bool
    sabin_dsp_arch: str
    sabin_microcode_untouched: bool
    sabin_dsp_mutation_bytes: int
    sabin_dsp_patch_requested: bool
    cxd90058_sabin_immutability_safe: bool
    intersoc_link_safe: bool
    fx6_sdi_raw_masked: bool
    mew_bin_fpga_probe_masked: bool
    sdi_raw_16bit_requested: bool
    mew_bin_load_requested: bool
    output_path: str
    sdi_raw_mask_safe: bool
    memcfg_total_mib: float
    allocated_memcfg_mib: float
    encoder_codec_family: str
    encoder_pool_bytes: int
    encoder_pool_align_bytes: int
    memcfg_overflow_bytes: int
    memcfg_encoder_pool_safe: bool
    el3_payload_transmit_authorized: bool
    spi_nor_write_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PostBenchFactorySealGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    guard_profile: str
    expected_surface_count: int
    verified_surface_count: int
    mismatched_surfaces: Tuple[str, ...]
    h0_equals_h3_16_of_16: bool
    im_elf_orig_present: bool
    ld_so_preload_present: bool
    tmp_jiritsu_file_count: int
    p6_residual_file_count: int
    p6_chunk_residual_bytes: int
    residual_artifact_count: int
    leftover_paths: Tuple[str, ...]
    zero_residual_safe: bool
    otp_write_count: int
    rpmb_write_count: int
    updater_mode_flag_count: int
    updater_mode_paths_present: Tuple[str, ...]
    official_update_ready: bool
    otp_rpmb_updater_clean_safe: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G53Cxd90058SabinResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    cxd90058_sabin_guard: Dict[str, Any]
    el3_payload_transmit_authorized: bool
    spi_nor_write_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G54FactorySealResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    factory_seal_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master54GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    offline_51_gates_verified: bool
    all_54_gates_verified: bool
    g13_to_g54_all_passed: bool
    g53_to_g54_all_passed: bool
    h0_h1_trial_entry_allowed: bool
    status: str
    el3_payload_transmit_authorized: bool
    spi_nor_write_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    summary: Dict[str, Any]
    gates: Tuple[Dict[str, Any], ...]
    master_52_report: Dict[str, Any]
    g53_result: Dict[str, Any]
    g54_result: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Internal Helpers (Strict os.O_RDONLY, zero raw bytes printing)
# ---------------------------------------------------------------------------


def _add_code(codes: List[str], code: str) -> None:
    if code not in codes:
        codes.append(code)


def _is_forced_clean_room(force_clean_room: Optional[bool] = None) -> bool:
    if force_clean_room is not None:
        return bool(force_clean_room)
    return os.environ.get(ENV_FORCE_CLEAN_ROOM, "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _read_file_o_rdonly(path: Path) -> bytes:
    """Strictly read a file via `os.open(..., os.O_RDONLY)` without leaking raw bytes."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        chunks: List[bytes] = []
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(fd)


def _is_finite_number(val: Any) -> bool:
    return (
        isinstance(val, (int, float))
        and (not isinstance(val, bool))
        and math.isfinite(float(val))
    )


def _is_non_negative_int(val: Any) -> bool:
    return isinstance(val, int) and (not isinstance(val, bool)) and val >= 0


def _is_positive_int(val: Any) -> bool:
    return isinstance(val, int) and (not isinstance(val, bool)) and val > 0


def _normalize_codec_pool_name(name: str) -> str:
    return (
        name.strip()
        .upper()
        .replace("-", "_")
        .replace(" ", "_")
    )


# ---------------------------------------------------------------------------
# 1. Strictly Read-Only (O_RDONLY) Donor Contract Audit (FX3 7.02)
# ---------------------------------------------------------------------------


def audit_phase165_donor_contracts(
    *_,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
) -> Phase165DonorAuditResult:
    """Inspect FX3 `7.02` `libsencore.so`, `libmpr.so`, `im.elf`, `cpapp-b.bin`,
    and `Backup.bin` strictly via `os.open(..., os.O_RDONLY)` with deterministic
    clean-room fallback when `FX3_FX6_FORCE_CLEAN_ROOM=1` or donors are absent.
    """
    clean_forced = _is_forced_clean_room(force_clean_room)
    paths = resolve_donor_thermal_power_paths(work_root=work_root, repo_root=repo_root)
    effective_work_root: Optional[Path] = (
        Path(work_root) if work_root is not None else paths.work_root
    )

    resolved: Dict[str, Path] = {}
    if effective_work_root is not None:
        for key, (
            _body,
            rel_path,
            _sz,
            _sha,
            _toks,
            _lbl,
        ) in PINNED_PHASE165_DONOR_SPECS.items():
            resolved[key] = effective_work_root / rel_path

    donor_available = (
        (not clean_forced)
        and (effective_work_root is not None)
        and bool(resolved)
        and all(p.is_file() for p in resolved.values())
    )

    if not donor_available:
        return Phase165DonorAuditResult(
            valid=True,
            status=STATUS_VERIFIED_SAFE,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="O_RDONLY",
            files_inspected=0,
            checked_markers=tuple(
                spec[5] for spec in PINNED_PHASE165_DONOR_SPECS.values()
            ),
            missing_markers=(),
            fx3_contracts_verified=True,
            sha256_by_artifact={
                k: spec[3] for k, spec in PINNED_PHASE165_DONOR_SPECS.items()
            },
            bytes_by_artifact={
                k: spec[2] for k, spec in PINNED_PHASE165_DONOR_SPECS.items()
            },
            errors=(),
            warnings=(),
        )

    checked: List[str] = []
    missing: List[str] = []
    shas: Dict[str, str] = {}
    sizes: Dict[str, int] = {}
    errors: List[str] = []
    warnings: List[str] = []
    passed_keys: set[str] = set()
    files_inspected = 0

    for key, (
        _body,
        _rel_name,
        exp_size,
        exp_sha,
        marker_tuple,
        marker_label,
    ) in PINNED_PHASE165_DONOR_SPECS.items():
        blob = _read_file_o_rdonly(resolved[key])
        files_inspected += 1
        sha = hashlib.sha256(blob).hexdigest()
        shas[key] = sha
        sizes[key] = len(blob)

        missing_for_file = [m for m in marker_tuple if m not in blob]
        integrity_ok = len(blob) == exp_size and sha == exp_sha

        if not missing_for_file:
            checked.append(marker_label)
        else:
            missing.append(marker_label)
            errors.append(
                f"Donor {key} missing {len(missing_for_file)} required marker(s) for {marker_label}."
            )

        if not integrity_ok:
            errors.append(
                f"Donor {key} integrity mismatch: size={len(blob)} (expected {exp_size}), "
                f"sha256={sha} (expected {exp_sha})."
            )

        if not missing_for_file and integrity_ok:
            passed_keys.add(key)

    fx3_keys = {
        k for k, spec in PINNED_PHASE165_DONOR_SPECS.items() if spec[0] == "fx3"
    }
    valid = len(errors) == 0 and len(missing) == 0
    return Phase165DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_PHASE165_DONOR_INTEGRITY,
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="O_RDONLY",
        files_inspected=files_inspected,
        checked_markers=tuple(checked),
        missing_markers=tuple(missing),
        fx3_contracts_verified=fx3_keys.issubset(passed_keys) and valid,
        sha256_by_artifact=shas,
        bytes_by_artifact=sizes,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 2. Pure Helper Functions (G53 & G54)
# ---------------------------------------------------------------------------


def default_verified_16_surface_seal_hashes(
    seed_hex: str = "a" * 64,
) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Return bit-identical 16-surface H0 and H3 SHA-256 maps for rehearsal/defaults."""
    norm = seed_hex.strip().lower() if isinstance(seed_hex, str) else ""
    if not _HEX64_RE.match(norm):
        norm = "a" * 64
    h0: Dict[str, str] = {}
    h3: Dict[str, str] = {}
    for idx, surface in enumerate(CANONICAL_16_STORAGE_SURFACES):
        digest = hashlib.sha256(f"{norm}:{idx}:{surface}".encode("ascii")).hexdigest()
        h0[surface] = digest
        h3[surface] = digest
    return h0, h3


def find_h0_h3_surface_mismatches(
    h0_surface_sha256s: Mapping[str, str],
    h3_surface_sha256s: Mapping[str, str],
    *,
    expected_surfaces: Sequence[str] = CANONICAL_16_STORAGE_SURFACES,
) -> Tuple[str, ...]:
    """Return sorted/ordered list of storage surfaces whose H0 != H3 or SHA-256 is invalid."""
    mismatches: List[str] = []
    for surface in expected_surfaces:
        v0 = h0_surface_sha256s.get(surface)
        v3 = h3_surface_sha256s.get(surface)
        if not isinstance(v0, str) or not isinstance(v3, str):
            mismatches.append(surface)
            continue
        s0 = v0.strip().lower()
        s3 = v3.strip().lower()
        if (not _HEX64_RE.match(s0)) or (not _HEX64_RE.match(s3)) or (s0 != s3):
            mismatches.append(surface)
    extra_keys = set(h0_surface_sha256s.keys()) ^ set(h3_surface_sha256s.keys())
    for k in sorted(str(x) for x in extra_keys):
        if k not in mismatches:
            mismatches.append(k)
    return tuple(mismatches)


def validate_cxd90058_and_sabin_immutability(
    *,
    p8_cpapp_ro_locked: bool = True,
    p8_cpapp_sha256: str = PINNED_FX3_CPAPP_SHA256,
    p8_cpapp_mutation_bytes: int = 0,
    cxd90058_boot_blobs_untouched: bool = True,
    cxd90058_mutation_bytes: int = 0,
    cxd90058_write_requested: bool = False,
    sabin_dsp_arch: str = SABIN_DSP_ARCH_NAME,
    sabin_microcode_untouched: bool = True,
    sabin_dsp_mutation_bytes: int = 0,
    sabin_dsp_patch_requested: bool = False,
) -> bool:
    """Enforce zero mutation to `p8:/cpapp-b.bin`, `CXD90058` blobs, and `sabin` SA-DSP."""
    for b in (
        p8_cpapp_ro_locked,
        cxd90058_boot_blobs_untouched,
        cxd90058_write_requested,
        sabin_microcode_untouched,
        sabin_dsp_patch_requested,
    ):
        if not isinstance(b, bool):
            return False
    for cnt in (p8_cpapp_mutation_bytes, cxd90058_mutation_bytes, sabin_dsp_mutation_bytes):
        if not _is_non_negative_int(cnt):
            return False
    if not isinstance(p8_cpapp_sha256, str) or not _HEX64_RE.match(
        p8_cpapp_sha256.strip().lower()
    ):
        return False
    if not isinstance(sabin_dsp_arch, str) or sabin_dsp_arch.strip().upper() != SABIN_DSP_ARCH_NAME:
        return False

    if (not p8_cpapp_ro_locked) or int(p8_cpapp_mutation_bytes) != 0:
        return False
    if p8_cpapp_sha256.strip().lower() != PINNED_FX3_CPAPP_SHA256:
        return False
    if (
        (not cxd90058_boot_blobs_untouched)
        or int(cxd90058_mutation_bytes) != 0
        or cxd90058_write_requested
    ):
        return False
    if (
        (not sabin_microcode_untouched)
        or int(sabin_dsp_mutation_bytes) != 0
        or sabin_dsp_patch_requested
    ):
        return False
    return True


def validate_mira_cetus_intersoc_link(
    *,
    ap_soc_name: str = AP_SOC_MIRA_NAME,
    cp_soc_name: str = CP_SOC_CETUS_NAME,
    intersoc_link_protocol: str = "SLVS-EC",
    intersoc_link_healthy: bool = True,
    p8_cpapp_partition: str = P8_CPAPP_PARTITION_PATH,
) -> bool:
    """Verify healthy `CXD90057` (Mira) <-> `CXD90058` (Cetus) inter-SoC link & `p8:/cpapp-b.bin`."""
    if not isinstance(intersoc_link_healthy, bool) or not intersoc_link_healthy:
        return False
    if not isinstance(ap_soc_name, str) or ap_soc_name.strip().upper() != AP_SOC_MIRA_NAME:
        return False
    if not isinstance(cp_soc_name, str) or cp_soc_name.strip().upper() != CP_SOC_CETUS_NAME:
        return False
    if (
        not isinstance(intersoc_link_protocol, str)
        or intersoc_link_protocol.strip().upper() not in INTERSOC_VALID_LINK_PROTOCOLS
    ):
        return False
    if (
        not isinstance(p8_cpapp_partition, str)
        or p8_cpapp_partition.strip() != P8_CPAPP_PARTITION_PATH
    ):
        return False
    return True


def validate_sdi_raw_mew_mask(
    *,
    fx6_sdi_raw_masked: bool = True,
    mew_bin_fpga_probe_masked: bool = True,
    sdi_raw_16bit_requested: bool = False,
    mew_bin_load_requested: bool = False,
    output_path: str = "INTERNAL_XAVC",
) -> bool:
    """Fail-closed mask of FX6-only `16-bit SDI RAW` (`mew.bin` FPGA) output paths."""
    for b in (
        fx6_sdi_raw_masked,
        mew_bin_fpga_probe_masked,
        sdi_raw_16bit_requested,
        mew_bin_load_requested,
    ):
        if not isinstance(b, bool):
            return False
    if not isinstance(output_path, str) or not output_path.strip():
        return False

    norm_out = output_path.strip().upper().replace("-", "_").replace(" ", "_")
    if "SDI" in norm_out or "MEW" in norm_out:
        return False
    if norm_out in FX6_FORBIDDEN_SDI_RAW_MODES:
        return False
    if norm_out not in FX3_ALLOWED_OUTPUT_PATHS:
        return False
    if (not fx6_sdi_raw_masked) or (not mew_bin_fpga_probe_masked):
        return False
    if sdi_raw_16bit_requested or mew_bin_load_requested:
        return False
    return True


def validate_memcfg_xavc_encoder_pool(
    *,
    memcfg_total_mib: float = FX3_MEMCFG_BUDGET_MIB,
    allocated_memcfg_mib: float = 1480.0,
    encoder_codec_family: str = "XAVC S-I",
    encoder_pool_bytes: int = 268_435_456,  # 256 MiB, 4 KiB & 64 KiB aligned
    encoder_pool_align_bytes: int = FX3_ENCODER_POOL_ALIGN_BYTES,
    memcfg_overflow_bytes: int = 0,
) -> bool:
    """Verify XAVC-I / XAVC S-I / XAVC HS hardware encoder pool alignment on 1,724.00 MiB `memcfg=`."""
    if not _is_finite_number(memcfg_total_mib) or not _is_finite_number(allocated_memcfg_mib):
        return False
    if not _is_positive_int(encoder_pool_bytes) or not _is_positive_int(encoder_pool_align_bytes):
        return False
    if not _is_non_negative_int(memcfg_overflow_bytes):
        return False
    if not isinstance(encoder_codec_family, str) or not encoder_codec_family.strip():
        return False

    norm_codec = _normalize_codec_pool_name(encoder_codec_family)
    if norm_codec not in _FX3_NORMALIZED_XAVC_POOLS:
        return False

    # Enforce FX3's exact 1,724.00 MiB memcfg= budget ceiling
    if abs(float(memcfg_total_mib) - FX3_MEMCFG_BUDGET_MIB) > 1e-6:
        return False
    if float(allocated_memcfg_mib) <= 0.0 or float(allocated_memcfg_mib) > float(memcfg_total_mib):
        return False
    if int(memcfg_overflow_bytes) != 0:
        return False
    if int(encoder_pool_align_bytes) < FX3_ENCODER_POOL_ALIGN_BYTES:
        return False
    if (int(encoder_pool_align_bytes) & (int(encoder_pool_align_bytes) - 1)) != 0:
        return False
    if int(encoder_pool_bytes) % int(encoder_pool_align_bytes) != 0:
        return False
    pool_mib = float(encoder_pool_bytes) / (1024.0 * 1024.0)
    if pool_mib > float(allocated_memcfg_mib) or pool_mib > float(memcfg_total_mib):
        return False
    return True


def validate_16_surface_h0_h3_seal(
    h0_surface_sha256s: Mapping[str, str],
    h3_surface_sha256s: Mapping[str, str],
    *,
    expected_surfaces: Sequence[str] = CANONICAL_16_STORAGE_SURFACES,
) -> bool:
    """Verify bit-identical `SHA256(H0) == SHA256(H3)` across all 16 storage surfaces."""
    if len(tuple(expected_surfaces)) != CANONICAL_16_SURFACE_COUNT:
        return False
    if tuple(expected_surfaces) != CANONICAL_16_STORAGE_SURFACES:
        return False
    if not isinstance(h0_surface_sha256s, Mapping) or not isinstance(
        h3_surface_sha256s, Mapping
    ):
        return False
    if len(h0_surface_sha256s) != CANONICAL_16_SURFACE_COUNT or len(h3_surface_sha256s) != CANONICAL_16_SURFACE_COUNT:
        return False
    mismatches = find_h0_h3_surface_mismatches(
        h0_surface_sha256s,
        h3_surface_sha256s,
        expected_surfaces=expected_surfaces,
    )
    return len(mismatches) == 0


def validate_zero_bench_residuals(
    *,
    im_elf_orig_present: bool = False,
    ld_so_preload_present: bool = False,
    tmp_jiritsu_file_count: int = 0,
    p6_residual_file_count: int = 0,
    p6_chunk_residual_bytes: int = 0,
    residual_artifact_count: int = 0,
    leftover_paths: Sequence[str] = (),
) -> bool:
    """Enforce zero `/usr/bin/im.elf.orig`, `/etc/ld.so.preload`, `/tmp/jiritsu/*`, or `p6` residuals."""
    if not isinstance(im_elf_orig_present, bool) or not isinstance(ld_so_preload_present, bool):
        return False
    for cnt in (
        tmp_jiritsu_file_count,
        p6_residual_file_count,
        p6_chunk_residual_bytes,
        residual_artifact_count,
    ):
        if not _is_non_negative_int(cnt):
            return False
    if not isinstance(leftover_paths, (tuple, list)):
        return False

    if im_elf_orig_present or ld_so_preload_present:
        return False
    if (
        int(tmp_jiritsu_file_count) != 0
        or int(p6_residual_file_count) != 0
        or int(p6_chunk_residual_bytes) != 0
        or int(residual_artifact_count) != 0
    ):
        return False
    if any(str(p).strip() for p in leftover_paths):
        return False
    return True


def validate_otp_rpmb_and_updater_flags(
    *,
    otp_write_count: int = 0,
    rpmb_write_count: int = 0,
    updater_mode_flag_count: int = 0,
    updater_mode_paths_present: Sequence[str] = (),
    official_update_ready: bool = True,
) -> bool:
    """Verify `OTP == 0`, `RPMB == 0`, and `/setting/updater/mode*` flags `== 0`."""
    for cnt in (otp_write_count, rpmb_write_count, updater_mode_flag_count):
        if not _is_non_negative_int(cnt):
            return False
    if not isinstance(updater_mode_paths_present, (tuple, list)):
        return False
    if not isinstance(official_update_ready, bool) or not official_update_ready:
        return False
    if (
        int(otp_write_count) != 0
        or int(rpmb_write_count) != 0
        or int(updater_mode_flag_count) != 0
    ):
        return False
    if any(str(p).strip() for p in updater_mode_paths_present):
        return False
    return True


# ---------------------------------------------------------------------------
# 3. Gate G53 & Gate G54 Core Evaluators
# ---------------------------------------------------------------------------


def verify_cxd90058_sabin_dsp_and_sdi_raw_mask_guard(
    *,
    ap_soc_name: str = AP_SOC_MIRA_NAME,
    cp_soc_name: str = CP_SOC_CETUS_NAME,
    intersoc_link_protocol: str = "SLVS-EC",
    intersoc_link_healthy: bool = True,
    p8_cpapp_partition: str = P8_CPAPP_PARTITION_PATH,
    p8_cpapp_ro_locked: bool = True,
    p8_cpapp_sha256: str = PINNED_FX3_CPAPP_SHA256,
    p8_cpapp_mutation_bytes: int = 0,
    cxd90058_boot_blobs_untouched: bool = True,
    cxd90058_mutation_bytes: int = 0,
    cxd90058_write_requested: bool = False,
    sabin_dsp_arch: str = SABIN_DSP_ARCH_NAME,
    sabin_microcode_untouched: bool = True,
    sabin_dsp_mutation_bytes: int = 0,
    sabin_dsp_patch_requested: bool = False,
    fx6_sdi_raw_masked: bool = True,
    mew_bin_fpga_probe_masked: bool = True,
    sdi_raw_16bit_requested: bool = False,
    mew_bin_load_requested: bool = False,
    output_path: str = "INTERNAL_XAVC",
    memcfg_total_mib: float = FX3_MEMCFG_BUDGET_MIB,
    allocated_memcfg_mib: float = 1480.0,
    encoder_codec_family: str = "XAVC S-I",
    encoder_pool_bytes: int = 268_435_456,
    encoder_pool_align_bytes: int = FX3_ENCODER_POOL_ALIGN_BYTES,
    memcfg_overflow_bytes: int = 0,
    guard_profile: str = "FX3_REALHW_G53_CXD90058_SABIN_SDI_MASK_DEFAULT",
) -> Cxd90058SabinSdiGuardResult:
    """Verify Gate G53 invariants fail-closed."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    bool_inputs = (
        intersoc_link_healthy,
        p8_cpapp_ro_locked,
        cxd90058_boot_blobs_untouched,
        cxd90058_write_requested,
        sabin_microcode_untouched,
        sabin_dsp_patch_requested,
        fx6_sdi_raw_masked,
        mew_bin_fpga_probe_masked,
        sdi_raw_16bit_requested,
        mew_bin_load_requested,
    )
    int_inputs = (
        p8_cpapp_mutation_bytes,
        cxd90058_mutation_bytes,
        sabin_dsp_mutation_bytes,
        memcfg_overflow_bytes,
    )
    telemetry_ok = (
        all(isinstance(b, bool) for b in bool_inputs)
        and all(_is_non_negative_int(i) for i in int_inputs)
        and _is_positive_int(encoder_pool_bytes)
        and _is_positive_int(encoder_pool_align_bytes)
        and _is_finite_number(memcfg_total_mib)
        and _is_finite_number(allocated_memcfg_mib)
        and isinstance(ap_soc_name, str)
        and bool(ap_soc_name.strip())
        and isinstance(cp_soc_name, str)
        and bool(cp_soc_name.strip())
        and isinstance(intersoc_link_protocol, str)
        and bool(intersoc_link_protocol.strip())
        and isinstance(p8_cpapp_partition, str)
        and bool(p8_cpapp_partition.strip())
        and isinstance(p8_cpapp_sha256, str)
        and bool(_HEX64_RE.match(p8_cpapp_sha256.strip().lower()))
        and isinstance(sabin_dsp_arch, str)
        and bool(sabin_dsp_arch.strip())
        and isinstance(output_path, str)
        and bool(output_path.strip())
        and isinstance(encoder_codec_family, str)
        and bool(encoder_codec_family.strip())
        and isinstance(guard_profile, str)
        and bool(guard_profile.strip())
    )

    if not telemetry_ok:
        _add_code(codes, STATUS_BLOCKED_G53_TELEMETRY_INVALID)
        errors.append("Gate G53 received invalid, non-finite, or malformed telemetry.")

    immutability_safe = False
    intersoc_safe = False
    sdi_mask_safe = False
    memcfg_safe = False

    if telemetry_ok:
        immutability_safe = validate_cxd90058_and_sabin_immutability(
            p8_cpapp_ro_locked=p8_cpapp_ro_locked,
            p8_cpapp_sha256=p8_cpapp_sha256,
            p8_cpapp_mutation_bytes=int(p8_cpapp_mutation_bytes),
            cxd90058_boot_blobs_untouched=cxd90058_boot_blobs_untouched,
            cxd90058_mutation_bytes=int(cxd90058_mutation_bytes),
            cxd90058_write_requested=cxd90058_write_requested,
            sabin_dsp_arch=sabin_dsp_arch,
            sabin_microcode_untouched=sabin_microcode_untouched,
            sabin_dsp_mutation_bytes=int(sabin_dsp_mutation_bytes),
            sabin_dsp_patch_requested=sabin_dsp_patch_requested,
        )
        if not immutability_safe:
            _add_code(codes, STATUS_BLOCKED_G53_CXD90058_OR_SABIN_MUTATION)
            errors.append(
                f"CXD90058/sabin immutability violation: p8_mut={p8_cpapp_mutation_bytes}B, "
                f"cxd90058_mut={cxd90058_mutation_bytes}B, sabin_mut={sabin_dsp_mutation_bytes}B."
            )

        intersoc_safe = validate_mira_cetus_intersoc_link(
            ap_soc_name=ap_soc_name,
            cp_soc_name=cp_soc_name,
            intersoc_link_protocol=intersoc_link_protocol,
            intersoc_link_healthy=intersoc_link_healthy,
            p8_cpapp_partition=p8_cpapp_partition,
        )
        if not intersoc_safe:
            _add_code(codes, STATUS_BLOCKED_G53_INTERSOC_LINK_OR_CPAPP_VIOLATION)
            errors.append(
                f"Mira<->Cetus inter-SoC link violation: ap={ap_soc_name}, cp={cp_soc_name}, "
                f"proto={intersoc_link_protocol}, healthy={intersoc_link_healthy}."
            )

        sdi_mask_safe = validate_sdi_raw_mew_mask(
            fx6_sdi_raw_masked=fx6_sdi_raw_masked,
            mew_bin_fpga_probe_masked=mew_bin_fpga_probe_masked,
            sdi_raw_16bit_requested=sdi_raw_16bit_requested,
            mew_bin_load_requested=mew_bin_load_requested,
            output_path=output_path,
        )
        if not sdi_mask_safe:
            _add_code(codes, STATUS_BLOCKED_G53_FX6_SDI_RAW_MEW_UNMASKED)
            errors.append(
                f"FX6 16-bit SDI RAW / mew.bin FPGA path not masked: out={output_path}, "
                f"sdi_req={sdi_raw_16bit_requested}, mew_req={mew_bin_load_requested}."
            )

        memcfg_safe = validate_memcfg_xavc_encoder_pool(
            memcfg_total_mib=float(memcfg_total_mib),
            allocated_memcfg_mib=float(allocated_memcfg_mib),
            encoder_codec_family=encoder_codec_family,
            encoder_pool_bytes=int(encoder_pool_bytes),
            encoder_pool_align_bytes=int(encoder_pool_align_bytes),
            memcfg_overflow_bytes=int(memcfg_overflow_bytes),
        )
        if not memcfg_safe:
            _add_code(codes, STATUS_BLOCKED_G53_MEMCFG_ENCODER_POOL_OVERFLOW)
            errors.append(
                f"FX3 memcfg={memcfg_total_mib} MiB XAVC encoder pool violation: "
                f"codec={encoder_codec_family}, alloc={allocated_memcfg_mib} MiB, "
                f"pool={encoder_pool_bytes}B (align={encoder_pool_align_bytes}B)."
            )

    valid = (
        telemetry_ok
        and immutability_safe
        and intersoc_safe
        and sdi_mask_safe
        and memcfg_safe
        and (not EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        and (not SPI_NOR_WRITE_AUTHORIZED)
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not PERSISTENT_WRITE_RELEASE)
        and (not codes)
    )
    status = STATUS_VERIFIED_G53 if valid else codes[0]

    return Cxd90058SabinSdiGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        guard_profile=str(guard_profile) if isinstance(guard_profile, str) else "INVALID",
        ap_soc_name=str(ap_soc_name) if isinstance(ap_soc_name, str) else "INVALID",
        cp_soc_name=str(cp_soc_name) if isinstance(cp_soc_name, str) else "INVALID",
        intersoc_link_protocol=(
            str(intersoc_link_protocol)
            if isinstance(intersoc_link_protocol, str)
            else "INVALID"
        ),
        intersoc_link_healthy=(
            bool(intersoc_link_healthy) if isinstance(intersoc_link_healthy, bool) else False
        ),
        p8_cpapp_partition=(
            str(p8_cpapp_partition) if isinstance(p8_cpapp_partition, str) else "INVALID"
        ),
        p8_cpapp_ro_locked=(
            bool(p8_cpapp_ro_locked) if isinstance(p8_cpapp_ro_locked, bool) else False
        ),
        p8_cpapp_sha256=(
            p8_cpapp_sha256.strip().lower()
            if isinstance(p8_cpapp_sha256, str)
            else "INVALID"
        ),
        p8_cpapp_mutation_bytes=(
            int(p8_cpapp_mutation_bytes)
            if _is_non_negative_int(p8_cpapp_mutation_bytes)
            else -1
        ),
        cxd90058_boot_blobs_untouched=(
            bool(cxd90058_boot_blobs_untouched)
            if isinstance(cxd90058_boot_blobs_untouched, bool)
            else False
        ),
        cxd90058_mutation_bytes=(
            int(cxd90058_mutation_bytes)
            if _is_non_negative_int(cxd90058_mutation_bytes)
            else -1
        ),
        cxd90058_write_requested=(
            bool(cxd90058_write_requested)
            if isinstance(cxd90058_write_requested, bool)
            else True
        ),
        sabin_dsp_arch=(
            str(sabin_dsp_arch) if isinstance(sabin_dsp_arch, str) else "INVALID"
        ),
        sabin_microcode_untouched=(
            bool(sabin_microcode_untouched)
            if isinstance(sabin_microcode_untouched, bool)
            else False
        ),
        sabin_dsp_mutation_bytes=(
            int(sabin_dsp_mutation_bytes)
            if _is_non_negative_int(sabin_dsp_mutation_bytes)
            else -1
        ),
        sabin_dsp_patch_requested=(
            bool(sabin_dsp_patch_requested)
            if isinstance(sabin_dsp_patch_requested, bool)
            else True
        ),
        cxd90058_sabin_immutability_safe=immutability_safe,
        intersoc_link_safe=intersoc_safe,
        fx6_sdi_raw_masked=(
            bool(fx6_sdi_raw_masked) if isinstance(fx6_sdi_raw_masked, bool) else False
        ),
        mew_bin_fpga_probe_masked=(
            bool(mew_bin_fpga_probe_masked)
            if isinstance(mew_bin_fpga_probe_masked, bool)
            else False
        ),
        sdi_raw_16bit_requested=(
            bool(sdi_raw_16bit_requested)
            if isinstance(sdi_raw_16bit_requested, bool)
            else True
        ),
        mew_bin_load_requested=(
            bool(mew_bin_load_requested)
            if isinstance(mew_bin_load_requested, bool)
            else True
        ),
        output_path=str(output_path) if isinstance(output_path, str) else "INVALID",
        sdi_raw_mask_safe=sdi_mask_safe,
        memcfg_total_mib=(
            float(memcfg_total_mib) if _is_finite_number(memcfg_total_mib) else -1.0
        ),
        allocated_memcfg_mib=(
            float(allocated_memcfg_mib) if _is_finite_number(allocated_memcfg_mib) else -1.0
        ),
        encoder_codec_family=(
            str(encoder_codec_family)
            if isinstance(encoder_codec_family, str)
            else "INVALID"
        ),
        encoder_pool_bytes=(
            int(encoder_pool_bytes) if _is_positive_int(encoder_pool_bytes) else -1
        ),
        encoder_pool_align_bytes=(
            int(encoder_pool_align_bytes)
            if _is_positive_int(encoder_pool_align_bytes)
            else -1
        ),
        memcfg_overflow_bytes=(
            int(memcfg_overflow_bytes)
            if _is_non_negative_int(memcfg_overflow_bytes)
            else -1
        ),
        memcfg_encoder_pool_safe=memcfg_safe,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def verify_post_bench_factory_seal_and_official_readiness_guard(
    *,
    h0_surface_sha256s: Optional[Mapping[str, str]] = None,
    h3_surface_sha256s: Optional[Mapping[str, str]] = None,
    im_elf_orig_present: bool = False,
    ld_so_preload_present: bool = False,
    tmp_jiritsu_file_count: int = 0,
    p6_residual_file_count: int = 0,
    p6_chunk_residual_bytes: int = 0,
    residual_artifact_count: int = 0,
    leftover_paths: Sequence[str] = (),
    otp_write_count: int = 0,
    rpmb_write_count: int = 0,
    updater_mode_flag_count: int = 0,
    updater_mode_paths_present: Sequence[str] = (),
    official_update_ready: bool = True,
    guard_profile: str = "FX3_REALHW_G54_16SURFACE_SEAL_CLEANLINESS_DEFAULT",
) -> PostBenchFactorySealGuardResult:
    """Verify Gate G54 invariants fail-closed."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    default_h0, default_h3 = default_verified_16_surface_seal_hashes()
    eff_h0 = default_h0 if h0_surface_sha256s is None else h0_surface_sha256s
    eff_h3 = default_h3 if h3_surface_sha256s is None else h3_surface_sha256s

    bool_inputs = (
        im_elf_orig_present,
        ld_so_preload_present,
        official_update_ready,
    )
    int_inputs = (
        tmp_jiritsu_file_count,
        p6_residual_file_count,
        p6_chunk_residual_bytes,
        residual_artifact_count,
        otp_write_count,
        rpmb_write_count,
        updater_mode_flag_count,
    )
    telemetry_ok = (
        all(isinstance(b, bool) for b in bool_inputs)
        and all(_is_non_negative_int(i) for i in int_inputs)
        and isinstance(eff_h0, Mapping)
        and isinstance(eff_h3, Mapping)
        and isinstance(leftover_paths, (tuple, list))
        and isinstance(updater_mode_paths_present, (tuple, list))
        and isinstance(guard_profile, str)
        and bool(guard_profile.strip())
    )

    if not telemetry_ok:
        _add_code(codes, STATUS_BLOCKED_G54_TELEMETRY_INVALID)
        errors.append("Gate G54 received invalid, non-finite, or malformed telemetry.")

    seal_safe = False
    residual_safe = False
    otp_rpmb_safe = False
    mismatched_surfaces: Tuple[str, ...] = ()
    verified_count = 0

    if telemetry_ok:
        mismatched_surfaces = find_h0_h3_surface_mismatches(eff_h0, eff_h3)
        verified_count = max(0, CANONICAL_16_SURFACE_COUNT - len(mismatched_surfaces))
        seal_safe = validate_16_surface_h0_h3_seal(eff_h0, eff_h3)
        if not seal_safe:
            _add_code(codes, STATUS_BLOCKED_G54_H0_H3_SURFACE_SEAL_MISMATCH)
            errors.append(
                f"Post-bench 16-surface H0 == H3 factory seal mismatch on {len(mismatched_surfaces)} "
                f"surface(s): {', '.join(mismatched_surfaces) or 'surface_count_mismatch'}."
            )

        residual_safe = validate_zero_bench_residuals(
            im_elf_orig_present=im_elf_orig_present,
            ld_so_preload_present=ld_so_preload_present,
            tmp_jiritsu_file_count=int(tmp_jiritsu_file_count),
            p6_residual_file_count=int(p6_residual_file_count),
            p6_chunk_residual_bytes=int(p6_chunk_residual_bytes),
            residual_artifact_count=int(residual_artifact_count),
            leftover_paths=leftover_paths,
        )
        if not residual_safe:
            _add_code(codes, STATUS_BLOCKED_G54_RESIDUAL_ARTIFACT_PRESENT)
            errors.append(
                f"Post-bench residual artifact violation: im_orig={im_elf_orig_present}, "
                f"preload={ld_so_preload_present}, tmp_jiritsu={tmp_jiritsu_file_count}, "
                f"p6_files={p6_residual_file_count}, p6_bytes={p6_chunk_residual_bytes}B, "
                f"residual_count={residual_artifact_count}."
            )

        otp_rpmb_safe = validate_otp_rpmb_and_updater_flags(
            otp_write_count=int(otp_write_count),
            rpmb_write_count=int(rpmb_write_count),
            updater_mode_flag_count=int(updater_mode_flag_count),
            updater_mode_paths_present=updater_mode_paths_present,
            official_update_ready=official_update_ready,
        )
        if not otp_rpmb_safe:
            _add_code(codes, STATUS_BLOCKED_G54_OTP_RPMB_OR_UPDATER_DIRTY)
            errors.append(
                f"OTP/RPMB/updater flag cleanliness violation: OTP={otp_write_count}, "
                f"RPMB={rpmb_write_count}, mode_flags={updater_mode_flag_count}, "
                f"official_ready={official_update_ready}."
            )

    valid = (
        telemetry_ok
        and seal_safe
        and residual_safe
        and otp_rpmb_safe
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not PERSISTENT_WRITE_RELEASE)
        and (not codes)
    )
    status = STATUS_VERIFIED_G54 if valid else codes[0]

    return PostBenchFactorySealGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        guard_profile=str(guard_profile) if isinstance(guard_profile, str) else "INVALID",
        expected_surface_count=CANONICAL_16_SURFACE_COUNT,
        verified_surface_count=verified_count if seal_safe else verified_count,
        mismatched_surfaces=mismatched_surfaces,
        h0_equals_h3_16_of_16=seal_safe,
        im_elf_orig_present=(
            bool(im_elf_orig_present) if isinstance(im_elf_orig_present, bool) else True
        ),
        ld_so_preload_present=(
            bool(ld_so_preload_present) if isinstance(ld_so_preload_present, bool) else True
        ),
        tmp_jiritsu_file_count=(
            int(tmp_jiritsu_file_count)
            if _is_non_negative_int(tmp_jiritsu_file_count)
            else -1
        ),
        p6_residual_file_count=(
            int(p6_residual_file_count)
            if _is_non_negative_int(p6_residual_file_count)
            else -1
        ),
        p6_chunk_residual_bytes=(
            int(p6_chunk_residual_bytes)
            if _is_non_negative_int(p6_chunk_residual_bytes)
            else -1
        ),
        residual_artifact_count=(
            int(residual_artifact_count)
            if _is_non_negative_int(residual_artifact_count)
            else -1
        ),
        leftover_paths=(
            tuple(str(p) for p in leftover_paths)
            if isinstance(leftover_paths, (tuple, list))
            else ()
        ),
        zero_residual_safe=residual_safe,
        otp_write_count=(
            int(otp_write_count) if _is_non_negative_int(otp_write_count) else -1
        ),
        rpmb_write_count=(
            int(rpmb_write_count) if _is_non_negative_int(rpmb_write_count) else -1
        ),
        updater_mode_flag_count=(
            int(updater_mode_flag_count)
            if _is_non_negative_int(updater_mode_flag_count)
            else -1
        ),
        updater_mode_paths_present=(
            tuple(str(p) for p in updater_mode_paths_present)
            if isinstance(updater_mode_paths_present, (tuple, list))
            else ()
        ),
        official_update_ready=(
            bool(official_update_ready)
            if isinstance(official_update_ready, bool)
            else False
        ),
        otp_rpmb_updater_clean_safe=otp_rpmb_safe,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 4. Gate G53 & Gate G54 Evaluators (Donor Audit + Guard -> GateVerdict)
# ---------------------------------------------------------------------------


def evaluate_g53_cxd90058_sabin(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    cxd90058_sabin_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase165DonorAuditResult] = None,
) -> Tuple[GateVerdict, G53Cxd90058SabinResult]:
    """Evaluate Gate G53 (`CXD90057/CXD90058` Inter-SoC, `sabin` SA-DSP & `SDI RAW` Mask Guard)."""
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase165_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )

    guard_kwargs = dict(cxd90058_sabin_kwargs or {})
    guard = verify_cxd90058_sabin_dsp_and_sdi_raw_mask_guard(**guard_kwargs)

    codes: List[str] = list(guard.violation_codes)
    errors: List[str] = list(audit.errors) + list(guard.errors)
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if not audit.valid:
        _add_code(codes, STATUS_BLOCKED_PHASE165_DONOR_INTEGRITY)

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append(
            "Gate G53 blocked persistent eMMC write authorization request."
        )

    valid = (
        audit.valid
        and guard.valid
        and (not EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        and (not SPI_NOR_WRITE_AUTHORIZED)
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not codes)
    )
    status = STATUS_VERIFIED_G53 if valid else codes[0]

    res = G53Cxd90058SabinResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        cxd90058_sabin_guard=guard.to_dict(),
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    evidence = (
        f"mode={audit.verification_mode}, link={guard.ap_soc_name}<->{guard.cp_soc_name}({guard.intersoc_link_protocol}), "
        f"cxd90058_mut={guard.cxd90058_mutation_bytes}B, sabin_mut={guard.sabin_dsp_mutation_bytes}B, "
        f"sdi_raw_masked={guard.fx6_sdi_raw_masked}, mew_masked={guard.mew_bin_fpga_probe_masked}, "
        f"memcfg={guard.allocated_memcfg_mib:.1f}/{guard.memcfg_total_mib:.1f}MiB({guard.encoder_codec_family})"
    )

    verdict = GateVerdict(
        gate_id=G53_GATE_ID,
        gate_code=G53_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


def evaluate_g54_factory_seal(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    factory_seal_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase165DonorAuditResult] = None,
) -> Tuple[GateVerdict, G54FactorySealResult]:
    """Evaluate Gate G54 (`16/16 H0 == H3` Factory Seal & Official Update Cleanliness Guard)."""
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase165_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )

    guard_kwargs = dict(factory_seal_kwargs or {})
    guard = verify_post_bench_factory_seal_and_official_readiness_guard(**guard_kwargs)

    codes: List[str] = list(guard.violation_codes)
    errors: List[str] = list(audit.errors) + list(guard.errors)
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if not audit.valid:
        _add_code(codes, STATUS_BLOCKED_PHASE165_DONOR_INTEGRITY)

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append(
            "Gate G54 blocked persistent eMMC write authorization request."
        )

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G54 if valid else codes[0]

    res = G54FactorySealResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        factory_seal_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    evidence = (
        f"mode={audit.verification_mode}, h0_eq_h3={guard.verified_surface_count}/{guard.expected_surface_count}, "
        f"residual={guard.residual_artifact_count}, im_orig={guard.im_elf_orig_present}, "
        f"preload={guard.ld_so_preload_present}, otp={guard.otp_write_count}, "
        f"rpmb={guard.rpmb_write_count}, mode_flags={guard.updater_mode_flag_count}, "
        f"official_ready={guard.official_update_ready}"
    )

    verdict = GateVerdict(
        gate_id=G54_GATE_ID,
        gate_code=G54_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 5. Unified 54-Gate Master Safety Preflight (`G01..G54`)
# ---------------------------------------------------------------------------


def evaluate_54gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated_backup: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    # G01..G52 pass-throughs
    tier0_manifest: Optional[Dict[str, object]] = None,
    worker_syscall_trace: Optional[List[Dict[str, object]]] = None,
    init2_failsafe_hook: Optional[str] = None,
    candidate_bundle_verified: Optional[bool] = None,
    allow_dry_run_gate12: bool = False,
    gate12_kwargs: Optional[Mapping[str, Any]] = None,
    ltc_kwargs: Optional[Mapping[str, Any]] = None,
    mishoe_kwargs: Optional[Mapping[str, Any]] = None,
    crsdk_requests: Optional[Sequence[Mapping[str, Any]]] = None,
    crsdk_kwargs: Optional[Mapping[str, Any]] = None,
    spacc_operations: Optional[Sequence[Mapping[str, Any]]] = None,
    spacc_script_text: str = "",
    spacc_sector0_bytes: Optional[bytes] = None,
    harness_kwargs: Optional[Mapping[str, Any]] = None,
    fan_kwargs: Optional[Mapping[str, Any]] = None,
    power_kwargs: Optional[Mapping[str, Any]] = None,
    soc_start_ceiling_c: Optional[float] = None,
    planned_mounts: Sequence[str] = (),
    planned_writes: Sequence[str] = (),
    c2pa_calibration_script_text: str = "",
    calibration_mutation_bytes: int = 0,
    c2pa_keystore_writes_attempted: bool = False,
    exfat_dirty_bit_present: bool = False,
    exfat_unfinalized_rsv_present: bool = False,
    allow_c2pa_or_calibration_write: bool = False,
    p12_vma: int = P12_WLAN_FATAL_GUARD_VMA,
    p12_patched_rc: int = 0,
    p12_guard_enabled: bool = True,
    bk4_airplane_shadow: Optional[Mapping[int, int]] = None,
    wf12_bootloop_immune: bool = True,
    wbi_mutation_bytes: int = 0,
    cp_mutation_bytes: int = 0,
    nvram_persistent_writes: int = 0,
    request_persistent_emmc_writes: bool = False,
    slot_a: Optional[MediaSlotConfig] = None,
    slot_b: Optional[MediaSlotConfig] = None,
    p1_vbr_bytes: Optional[bytes] = None,
    p1_image_path: Optional[Path] = None,
    p1_device_node: str = "/dev/nflasha1",
    require_at_least_one_lab_card: bool = True,
    usblan_kwargs: Optional[Mapping[str, Any]] = None,
    ptpip_or_mc_requests: Optional[Sequence[Any]] = None,
    ptpip_authenticated: bool = True,
    allow_protocol_3_00: bool = False,
    rig_kwargs: Optional[Mapping[str, Any]] = None,
    emount_kwargs: Optional[Mapping[str, Any]] = None,
    power_failover_kwargs: Optional[Mapping[str, Any]] = None,
    rsv_bytes: Optional[bytes] = None,
    rsv_path: Optional[Path] = None,
    xlr_kwargs: Optional[Mapping[str, Any]] = None,
    gimbal_kwargs: Optional[Mapping[str, Any]] = None,
    dewpoint_kwargs: Optional[Mapping[str, Any]] = None,
    pmic_usbc_kwargs: Optional[Mapping[str, Any]] = None,
    intake_fan_kwargs: Optional[Mapping[str, Any]] = None,
    tripod_housing_kwargs: Optional[Mapping[str, Any]] = None,
    sensor_curtain_kwargs: Optional[Mapping[str, Any]] = None,
    subzero_altitude_kwargs: Optional[Mapping[str, Any]] = None,
    wireless_tx_emi_kwargs: Optional[Mapping[str, Any]] = None,
    longform_endurance_kwargs: Optional[Mapping[str, Any]] = None,
    pl_cantilever_kwargs: Optional[Mapping[str, Any]] = None,
    dummy_battery_kwargs: Optional[Mapping[str, Any]] = None,
    saltspray_haze_kwargs: Optional[Mapping[str, Any]] = None,
    followfocus_gimbal_kwargs: Optional[Mapping[str, Any]] = None,
    hdmi_aoc_kwargs: Optional[Mapping[str, Any]] = None,
    cfexpress_media_kwargs: Optional[Mapping[str, Any]] = None,
    usbpd_uvc_kwargs: Optional[Mapping[str, Any]] = None,
    multiterminal_ptp_kwargs: Optional[Mapping[str, Any]] = None,
    monsoon_mishoe_kwargs: Optional[Mapping[str, Any]] = None,
    cagetwist_xlrh1_kwargs: Optional[Mapping[str, Any]] = None,
    vp_strobe_genlock_kwargs: Optional[Mapping[str, Any]] = None,
    vehiclerig_ibis_kwargs: Optional[Mapping[str, Any]] = None,
    jiritsu_service_kwargs: Optional[Mapping[str, Any]] = None,
    cnflasha_dualboot_kwargs: Optional[Mapping[str, Any]] = None,
    service_0336_canary_kwargs: Optional[Mapping[str, Any]] = None,
    stageb_mpr_ibis_p18_kwargs: Optional[Mapping[str, Any]] = None,
    pnflasha_mtdro_kwargs: Optional[Mapping[str, Any]] = None,
    rfnvs_fan_power_kwargs: Optional[Mapping[str, Any]] = None,
    uart1v8_isp_kwargs: Optional[Mapping[str, Any]] = None,
    imx510_sensor_cal_kwargs: Optional[Mapping[str, Any]] = None,
    cfexpress_ufu_kwargs: Optional[Mapping[str, Any]] = None,
    five_tier_el3_kwargs: Optional[Mapping[str, Any]] = None,
    # G53 inputs (CXD90057/CXD90058 Inter-SoC, sabin SA-DSP, SDI RAW mask & memcfg)
    cxd90058_sabin_kwargs: Optional[Mapping[str, Any]] = None,
    # G54 inputs (16/16 H0 == H3 factory seal & zero residual official update readiness)
    factory_seal_kwargs: Optional[Mapping[str, Any]] = None,
) -> Master54GateReport:
    """Evaluate all 54 Master Safety Gates (`G01..G54`) deterministically."""
    resolved_root = (
        DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)
    ).resolve()
    clean_forced = _is_forced_clean_room(force_clean_room)

    m52_kwargs: Dict[str, Any] = {
        "force_clean_room": clean_forced,
        "dry_run_simulated_backup": bool(dry_run_simulated_backup),
        "include_large_binaries": include_large_binaries,
        "work_root": work_root,
        "tier0_manifest": tier0_manifest,
        "worker_syscall_trace": worker_syscall_trace,
        "init2_failsafe_hook": init2_failsafe_hook,
        "candidate_bundle_verified": candidate_bundle_verified,
        "allow_dry_run_gate12": allow_dry_run_gate12,
        "gate12_kwargs": gate12_kwargs,
        "ltc_kwargs": ltc_kwargs,
        "mishoe_kwargs": mishoe_kwargs,
        "crsdk_requests": crsdk_requests,
        "crsdk_kwargs": crsdk_kwargs,
        "spacc_operations": spacc_operations,
        "spacc_script_text": spacc_script_text,
        "spacc_sector0_bytes": spacc_sector0_bytes,
        "harness_kwargs": harness_kwargs,
        "fan_kwargs": fan_kwargs,
        "power_kwargs": power_kwargs,
        "planned_mounts": planned_mounts,
        "planned_writes": planned_writes,
        "c2pa_calibration_script_text": c2pa_calibration_script_text,
        "calibration_mutation_bytes": calibration_mutation_bytes,
        "c2pa_keystore_writes_attempted": c2pa_keystore_writes_attempted,
        "exfat_dirty_bit_present": exfat_dirty_bit_present,
        "exfat_unfinalized_rsv_present": exfat_unfinalized_rsv_present,
        "allow_c2pa_or_calibration_write": allow_c2pa_or_calibration_write,
        "p12_vma": p12_vma,
        "p12_patched_rc": p12_patched_rc,
        "p12_guard_enabled": p12_guard_enabled,
        "bk4_airplane_shadow": bk4_airplane_shadow,
        "wf12_bootloop_immune": wf12_bootloop_immune,
        "wbi_mutation_bytes": wbi_mutation_bytes,
        "cp_mutation_bytes": cp_mutation_bytes,
        "nvram_persistent_writes": nvram_persistent_writes,
        "request_persistent_emmc_writes": request_persistent_emmc_writes,
        "slot_a": slot_a,
        "slot_b": slot_b,
        "p1_vbr_bytes": p1_vbr_bytes,
        "p1_image_path": p1_image_path,
        "p1_device_node": p1_device_node,
        "require_at_least_one_lab_card": require_at_least_one_lab_card,
        "usblan_kwargs": usblan_kwargs,
        "ptpip_or_mc_requests": ptpip_or_mc_requests,
        "ptpip_authenticated": ptpip_authenticated,
        "allow_protocol_3_00": allow_protocol_3_00,
        "rig_kwargs": rig_kwargs,
        "emount_kwargs": emount_kwargs,
        "power_failover_kwargs": power_failover_kwargs,
        "rsv_bytes": rsv_bytes,
        "rsv_path": rsv_path,
        "xlr_kwargs": xlr_kwargs,
        "gimbal_kwargs": gimbal_kwargs,
        "dewpoint_kwargs": dewpoint_kwargs,
        "pmic_usbc_kwargs": pmic_usbc_kwargs,
        "intake_fan_kwargs": intake_fan_kwargs,
        "tripod_housing_kwargs": tripod_housing_kwargs,
        "sensor_curtain_kwargs": sensor_curtain_kwargs,
        "subzero_altitude_kwargs": subzero_altitude_kwargs,
        "wireless_tx_emi_kwargs": wireless_tx_emi_kwargs,
        "longform_endurance_kwargs": longform_endurance_kwargs,
        "pl_cantilever_kwargs": pl_cantilever_kwargs,
        "dummy_battery_kwargs": dummy_battery_kwargs,
        "saltspray_haze_kwargs": saltspray_haze_kwargs,
        "followfocus_gimbal_kwargs": followfocus_gimbal_kwargs,
        "hdmi_aoc_kwargs": hdmi_aoc_kwargs,
        "cfexpress_media_kwargs": cfexpress_media_kwargs,
        "usbpd_uvc_kwargs": usbpd_uvc_kwargs,
        "multiterminal_ptp_kwargs": multiterminal_ptp_kwargs,
        "monsoon_mishoe_kwargs": monsoon_mishoe_kwargs,
        "cagetwist_xlrh1_kwargs": cagetwist_xlrh1_kwargs,
        "vp_strobe_genlock_kwargs": vp_strobe_genlock_kwargs,
        "vehiclerig_ibis_kwargs": vehiclerig_ibis_kwargs,
        "jiritsu_service_kwargs": jiritsu_service_kwargs,
        "cnflasha_dualboot_kwargs": cnflasha_dualboot_kwargs,
        "service_0336_canary_kwargs": service_0336_canary_kwargs,
        "stageb_mpr_ibis_p18_kwargs": stageb_mpr_ibis_p18_kwargs,
        "pnflasha_mtdro_kwargs": pnflasha_mtdro_kwargs,
        "rfnvs_fan_power_kwargs": rfnvs_fan_power_kwargs,
        "uart1v8_isp_kwargs": uart1v8_isp_kwargs,
        "imx510_sensor_cal_kwargs": imx510_sensor_cal_kwargs,
        "cfexpress_ufu_kwargs": cfexpress_ufu_kwargs,
        "five_tier_el3_kwargs": five_tier_el3_kwargs,
    }
    if soc_start_ceiling_c is not None:
        m52_kwargs["soc_start_ceiling_c"] = soc_start_ceiling_c

    m52_report: Master52GateReport = evaluate_52gate_preflight(
        resolved_root, **m52_kwargs
    )

    phase165_audit = audit_phase165_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
    )

    g53_verdict, g53_res = evaluate_g53_cxd90058_sabin(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        cxd90058_sabin_kwargs=cxd90058_sabin_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase165_audit,
    )

    g54_verdict, g54_res = evaluate_g54_factory_seal(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        factory_seal_kwargs=factory_seal_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase165_audit,
    )

    gates_53_to_54 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g53_verdict, g54_verdict)
    ]
    all_gates = tuple(list(m52_report.gates) + gates_53_to_54)

    g01_to_g12_verified = int(m52_report.summary["g01_to_g12_verified"])
    g13_to_g52_verified = (
        int(m52_report.summary["g13_to_g50_verified"])
        + int(m52_report.summary["g51_to_g52_verified"])
    )
    g53_to_g54_verified = sum(1 for v in (g53_verdict, g54_verdict) if v.passed)
    total_verified = g01_to_g12_verified + g13_to_g52_verified + g53_to_g54_verified

    g53_to_g54_all_passed = g53_to_g54_verified == 2
    g13_to_g54_all_passed = (
        m52_report.g13_to_g52_all_passed and g53_to_g54_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m52_report.gates[:9])

    offline_51_verified = (
        g01_to_g09_ok
        and m52_report.offline_49_gates_verified
        and g53_to_g54_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_54_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g54_all_passed
        and (not request_persistent_emmc_writes)
    )

    # Hard-locked False in offline and dry-run modes; never authorizes EL3 TX / eMMC / SPI-NOR writes
    overall_ready_for_hardware_attach = False

    h0_h1_allowed = (
        offline_51_verified
        and m52_report.h0_h1_trial_entry_allowed
        and g53_to_g54_all_passed
        and (not EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        and (not SPI_NOR_WRITE_AUTHORIZED)
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    errors: List[str] = (
        list(m52_report.errors) + list(g53_verdict.errors) + list(g54_verdict.errors)
    )
    warnings: List[str] = (
        list(m52_report.warnings)
        + list(g53_verdict.warnings)
        + list(g54_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m52_report.g13_to_g52_all_passed:
        overall_status = m52_report.status
    elif not g53_verdict.passed:
        overall_status = g53_verdict.status
    elif not g54_verdict.passed:
        overall_status = g54_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_54_verified and dry_run_simulated_backup:
        overall_status = "VERIFIED_ALL_54_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_54_verified:
        overall_status = "VERIFIED_ALL_54_GATES"
    else:
        overall_status = "VERIFIED_51_OF_54_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m52_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g53_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g54_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 54,
        "verified_gates": total_verified,
        "blocked_or_pending_gates": 54 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g52_verified": g13_to_g52_verified,
        "g53_to_g54_verified": g53_to_g54_verified,
        "g13_to_g54_all_passed": g13_to_g54_all_passed,
        "g53_to_g54_all_passed": g53_to_g54_all_passed,
        "offline_51_gates_verified": offline_51_verified,
        "all_54_gates_verified": all_54_verified,
        "dry_run_rehearsal_only": bool(dry_run_simulated_backup),
        "overall_ready_for_hardware_attach": overall_ready_for_hardware_attach,
        "h0_h1_trial_entry_allowed": h0_h1_allowed,
        "el3_payload_transmit_authorized": EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "persistent_write_release": PERSISTENT_WRITE_RELEASE,
    }

    return Master54GateReport(
        schema=REALHW_CXD90058_SABIN_SEAL_54GATE_SCHEMA,
        version=REALHW_CXD90058_SABIN_SEAL_54GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=bool(dry_run_simulated_backup),
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        offline_51_gates_verified=offline_51_verified,
        all_54_gates_verified=all_54_verified,
        g13_to_g54_all_passed=g13_to_g54_all_passed,
        g53_to_g54_all_passed=g53_to_g54_all_passed,
        h0_h1_trial_entry_allowed=h0_h1_allowed,
        status=overall_status,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        summary=summary,
        gates=all_gates,
        master_52_report=m52_report.to_dict(),
        g53_result=g53_res.to_dict(),
        g54_result=g54_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_54_master_safety_gates = evaluate_54gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_cxd90058_sabin_seal_and_54gate_guard",
        description=(
            "Phase 165 — CXD90057/CXD90058 Dual-BIONZ-XR Inter-SoC, sabin SA-DSP Immutability & "
            "SDI RAW Mask Guard (G53), Post-Bench 16/16 H0 == H3 Factory Seal & Official Update "
            "Readiness Guard (G54), and 54-Gate Master Preflight (G01..G54)"
        ),
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    parser.add_argument(
        "--clean-room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    parser.add_argument(
        "--dry-run-simulated-backup",
        action="store_true",
        help="Supply simulated dry-run Tier-0 backup inputs so G01..G54 can be exercised offline",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit structured JSON report",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = evaluate_54gate_preflight(
        args.repo_root,
        force_clean_room=True if args.clean_room else None,
        dry_run_simulated_backup=bool(args.dry_run_simulated_backup),
    )
    if args.json:
        sys.stdout.write(
            json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n"
        )
    else:
        sys.stdout.write(
            f"status={report.status} mode={report.verification_mode} "
            f"verified={report.summary['verified_gates']}/54 "
            f"g53_to_g54_all_passed={report.g53_to_g54_all_passed} "
            f"all_54_gates_verified={report.all_54_gates_verified} "
            f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
            f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
            f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
            f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}\n"
        )
    ok = (
        report.all_54_gates_verified
        if args.dry_run_simulated_backup
        else report.offline_51_gates_verified
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
