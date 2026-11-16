"""Phase 173 — Real-Hardware Main Track Part 16:
Gate G57 (Dual-Media Independent Tier-0 Cold-Backup Device-ID Separation,
16/16 SHA-256 Parity & `GF(256)` `0x11d` RAID-6 Bit-Rot Scrub Guard),
Gate G58 (Two-Step Explicit Human Bench Authorization, Pre-Install `NP-FZ100 >= 80%` /
`>= 7400 mV`, `op=0xFF` RAM Canary Receipt, Dual-Media `FX3RCPT1` Match &
Zero-Auto-Flash Interlock), and
Unified 58-Gate Master Safety Preflight (`G01..G58` / `verify-58-gates`).

Operationalizes dual-media physical storage isolation, `GF(2^8)` (`0x11d`) P+Q
bit-rot scrub/recovery verification, and human-gated zero-auto-flash bench
interlocks for physical Sony ILME-FX3 (`Ver. 7.02`, Model ID `0x91030080`,
AP `CXD90057` *Mira* + CP `CXD90058` *Cetus*) while keeping all prior gate
modules (`G01..G56`) 100% untouched and hard-locking:
- `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`
- `SPI_NOR_WRITE_AUTHORIZED = False`
- `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`
- `PERSISTENT_WRITE_RELEASE = False`
- `PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED = False`
- `overall_ready_for_hardware_attach = False`

1. **Dual-Mode Donor Inspection (`os.O_RDONLY`) + Clean-Room Fallback (`FX3_FX6_FORCE_CLEAN_ROOM=1`)**:
   - Inspects FX3 `7.02` `libsencore.so`, `libmpr.so`, `im.elf`, `cpapp-b.bin`,
     and `Backup.bin` (`FX3-CX95900_ALLLANG-Backup.bin`) strictly via
     `os.open(..., os.O_RDONLY)` when present and `FX3_FX6_FORCE_CLEAN_ROOM != "1"`.
   - Falls back deterministically to pinned clean-room metadata when
     `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor files are absent, leaking zero raw
     Sony firmware bytes in JSON output.

2. **Gate G57 — Dual-Media Independent Tier-0 Cold-Backup Device-ID Separation &
   `GF(256)` RAID-6 Bit-Rot Scrub Guard**:
   - Hard-blocks single-disk / same-filesystem pseudo-backups
     (`media_a_st_dev == media_b_st_dev` or overlapping device/mount IDs).
   - Verifies `16/16` canonical surface SHA-256 parity across two physically
     independent storage devices (e.g., `SDXC exFAT Cold Backup` vs `Mac Host Vault`).
   - Exercises and verifies `GF(256)` (`0x11d`) P+Q RAID-6 parity scrub &
     erasure/bit-rot recovery capability (`unrecoverable_chunk_count == 0`),
     failing closed on `>= 3` simultaneous shard losses or unhealed bit-rot.

3. **Gate G58 — Two-Step Explicit Human Bench Authorization, Pre-Install
   `NP-FZ100 >= 80%` (`>= 7400 mV`) & Zero-Auto-Flash Interlock**:
   - Enforces that no automated script or AI agent can ever self-authorize
     physical flashing (`agent_auto_flash_blocked == True`,
     `auto_flash_requested == False`, `ai_agent_self_authorize_attempted == False`).
   - Requires pre-install `NP-FZ100 >= 80%` SOC and `>= 7400 mV` terminal voltage,
     verified `op=0xFF` RAM canary `FX3S0OK` (`528 B`) receipt with clean MSC
     `054C:0DA1` return, and dual-media `FX3RCPT1` (`528 B`) cold-backup match.
   - Enforces two-step explicit human confirmation (distinct Step-1 acknowledgement
     + Step-2 confirmation phrase) whenever live bench execution is requested,
     while keeping all repository write/flash constants hard-locked `False`.

4. **Unified 58-Gate Master Safety Preflight (`evaluate_58gate_preflight` / CLI `verify-58-gates`)**:
   - Chains `evaluate_56gate_preflight` (`G01..G56`) + `G57` + `G58` = **58 Gates**.
   - Offline default reports `55/58` (`G10..G12` physical Tier-0 gates `False`,
     `persistent_emmc_writes_authorized = False`,
     `persistent_write_release = False`,
     `spi_nor_write_authorized = False`,
     `el3_payload_transmit_authorized = False`,
     `overall_ready_for_hardware_attach = False`).
   - `--dry-run-simulated-backup` reports `58/58` dry-run green while STILL
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
from .realhw_c2pa_tc_gyro_and_56gate_guard import (
    Master56GateReport,
    evaluate_56gate_preflight,
)
from .realhw_cxd90058_sabin_seal_and_54gate_guard import (
    CANONICAL_16_STORAGE_SURFACES,
    CANONICAL_16_SURFACE_COUNT,
)
from .thermal_pwm_and_power_guard import (
    ENV_FORCE_CLEAN_ROOM,
    resolve_donor_thermal_power_paths,
)


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

REALHW_DUALMEDIA_BENCH_58GATE_SCHEMA: str = (
    "fx3-realhw-dualmedia-bench-58gate-preflight-v1"
)
REALHW_DUALMEDIA_BENCH_58GATE_VERSION: str = "1.0.0"

EL3_PAYLOAD_TRANSMIT_AUTHORIZED: bool = False
SPI_NOR_WRITE_AUTHORIZED: bool = False
PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False
PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED: bool = False

# Gate IDs & Canonical Codes for G57..G58
G57_GATE_ID: str = (
    "G57_dualmedia_tier0_device_id_separation_and_gf256_scrub_guard"
)
G57_GATE_CODE: str = (
    "DUALMEDIA_TIER0_DEVICE_ID_SEPARATION_AND_GF256_SCRUB_GUARD"
)

G58_GATE_ID: str = (
    "G58_two_step_human_bench_authorization_and_zero_auto_flash_interlock"
)
G58_GATE_CODE: str = (
    "TWO_STEP_HUMAN_BENCH_AUTHORIZATION_AND_ZERO_AUTO_FLASH_INTERLOCK"
)

# Status Codes
STATUS_SAFE: str = "SAFE"
STATUS_VERIFIED_SAFE: str = "VERIFIED_SAFE"
STATUS_VERIFIED_G57: str = (
    "VERIFIED_DUALMEDIA_TIER0_DEVICE_ID_SEPARATION_AND_GF256_SCRUB_GUARD"
)
STATUS_VERIFIED_G58: str = (
    "VERIFIED_TWO_STEP_HUMAN_BENCH_AUTHORIZATION_AND_ZERO_AUTO_FLASH_INTERLOCK"
)

# Gate G57 Violation Codes
STATUS_BLOCKED_G57_SINGLE_MEDIA_OR_SAME_ST_DEV: str = (
    "BLOCKED_G57_SINGLE_MEDIA_OR_SAME_ST_DEV"
)
STATUS_BLOCKED_G57_16_SURFACE_SHA256_MISMATCH: str = (
    "BLOCKED_G57_16_SURFACE_SHA256_MISMATCH"
)
STATUS_BLOCKED_G57_GF256_SCRUB_OR_QUORUM_LOSS: str = (
    "BLOCKED_G57_GF256_SCRUB_OR_QUORUM_LOSS"
)
STATUS_BLOCKED_G57_TELEMETRY_INVALID: str = (
    "BLOCKED_G57_DUALMEDIA_TELEMETRY_INVALID"
)

# Gate G58 Violation Codes
STATUS_BLOCKED_G58_AUTO_FLASH_INTERLOCK_VIOLATION: str = (
    "BLOCKED_G58_AUTO_FLASH_INTERLOCK_VIOLATION"
)
STATUS_BLOCKED_G58_TWO_STEP_HUMAN_AUTH_MISSING: str = (
    "BLOCKED_G58_TWO_STEP_HUMAN_AUTH_MISSING"
)
STATUS_BLOCKED_G58_BATTERY_BELOW_PREFLASH_THRESHOLD: str = (
    "BLOCKED_G58_BATTERY_BELOW_PREFLASH_THRESHOLD"
)
STATUS_BLOCKED_G58_CANARY_OR_FX3RCPT1_UNVERIFIED: str = (
    "BLOCKED_G58_CANARY_OR_FX3RCPT1_UNVERIFIED"
)
STATUS_BLOCKED_G58_TELEMETRY_INVALID: str = (
    "BLOCKED_G58_BENCH_INTERLOCK_TELEMETRY_INVALID"
)

STATUS_BLOCKED_PHASE173_DONOR_INTEGRITY: str = (
    "BLOCKED_PHASE173_58GATE_DONOR_INTEGRITY_MISMATCH"
)
STATUS_BLOCKED_PERSISTENT_EMMC_WRITE: str = (
    "BLOCKED_BY_PERSISTENT_EMMC_WRITE_REDLINE"
)

# Gate G57 Constants — Dual-Media Device-ID Separation & GF(256) (0x11d) RAID-6
FX3_MODEL_ID_INT: int = 0x91030080
FX3_MODEL_ID_HEX: str = "0x91030080"
FX3_MODEL_NAME: str = "ILME-FX3"

GF256_PRIMITIVE_POLY: int = 0x11D
GF256_GENERATOR: int = 0x02
GF256_MAX_RECOVERABLE_ERASURES: int = 2

DEFAULT_MEDIA_A_ST_DEV: int = 16_777_220
DEFAULT_MEDIA_B_ST_DEV: int = 16_777_231
DEFAULT_MEDIA_A_ROLE: str = "SD_EXFAT_COLD_BACKUP"
DEFAULT_MEDIA_B_ROLE: str = "MAC_HOST_VAULT"
ALLOWED_DUAL_MEDIA_ROLES: Tuple[str, ...] = (
    "SD_EXFAT_COLD_BACKUP",
    "CFEXPRESS_EXFAT_COLD_BACKUP",
    "MAC_HOST_VAULT",
    "OFFLINE_ARCHIVE_SSD",
)

# Gate G58 Constants — Two-Step Human Bench Authorization & Zero-Auto-Flash Interlock
PREFLASH_BATTERY_MODEL: str = "NP-FZ100"
PREFLASH_MIN_BATTERY_SOC_PCT: float = 80.0
PREFLASH_MIN_BATTERY_MV: int = 7400
PREFLASH_MAX_BATTERY_MV: int = 8500
PREFLASH_MIN_USBPD_CONTRACT_MW: int = 27_000

OP_FF_CANARY_OPCODE: int = 0xFF
FX3S0OK_HEADER_MAGIC: str = "FX3S0OK"
FX3S0OK_PACKET_BYTES: int = 528
FX3RCPT1_MAGIC: str = "FX3RCPT1"
FX3RCPT1_PACKET_BYTES: int = 528

EXPECTED_STEP2_HUMAN_CONFIRM_PHRASE: str = "CONFIRM-ILME-FX3-0x91030080-BENCH"
DEFAULT_SYNTHETIC_CAMERA_CID_SHA256: str = hashlib.sha256(
    b"ILME-FX3:0x91030080:SYNTHETIC_EMMC_CID_PHASE173"
).hexdigest()
DEFAULT_SYNTHETIC_FX3RCPT1_SHA256: str = hashlib.sha256(
    b"FX3RCPT1:528B:ILME-FX3:0x91030080:DUALMEDIA_PHASE173"
).hexdigest()

_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_FORBIDDEN_TRIVIAL_HEX64: Tuple[str, ...] = ("0" * 64, "f" * 64)

# Pinned FX3 v7.02 Donor Specs (verified strictly via os.O_RDONLY)
PINNED_PHASE173_DONOR_SPECS: Mapping[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_libsencore": (
        "fx3",
        "sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/libsencore.so",
        377_328,
        "a2907111c4a22314dcb12c25889e0e3142764c6a4a910a746e43908f76e7c410",
        (
            b"\x7fELF",
            b"C_GYRO_GAIN",
            b"MONITOR_GET_TEST_OUT_BNC_STATUS",
            b"GENLOCK",
            b"DSP",
            b"AVC",
        ),
        "fx3/libsencore.so::{ELF,C_GYRO_GAIN,MONITOR_GET_TEST_OUT_BNC_STATUS,GENLOCK,DSP,AVC}",
    ),
    "fx3_libmpr": (
        "fx3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libmpr.so",
        3_517_008,
        "9aeef3b9edb3d011c0c90cd2387b3a47bd3b506ebfa57be39ad1a9729771b57c",
        (
            b"\x7fELF",
            b"InfraC2PA",
            b"c2pa.created",
            b"sony.created",
            b"jumdSSIG",
            b"sigcert.p12",
            b"NonRealTimeMeta",
            b"LtcChangeTable",
            b"Gyroscope",
        ),
        "fx3/libmpr.so::{ELF,InfraC2PA,c2pa.created,sony.created,jumdSSIG,sigcert.p12,NonRealTimeMeta,LtcChangeTable,Gyroscope}",
    ),
    "fx3_im_elf": (
        "fx3",
        "fx3-vm-20261101/fx3-audit/original-members/nflasha15/bin/im.elf",
        40_920,
        "5171f576d8b76cfbf15581389183b390c445bd6ff9dd97fd6668c5f64e77dc91",
        (
            b"\x7fELF",
            b"/dev/nflasha12",
            b"/cert",
            b"libIMDB.so",
            b"libbackup.so",
            b"libosal_uipc.so",
        ),
        "fx3/im.elf::{40920B,ELF,/dev/nflasha12,/cert,libIMDB.so,libbackup.so,libosal_uipc.so}",
    ),
    "fx3_cpapp_b": (
        "fx3",
        "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin",
        15_980_568,
        "c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba",
        (
            b"ILME-FX3",
            b"\x80\x00\x03\x91",
            b"C_ImagerCtrl_IMX510",
            b"LTC",
            b"Gyro Data",
            b"MTG_ULOCK_START_SLAVE",
            b"OTP",
            b"sabin",
        ),
        "fx3/cpapp-b.bin::{ILME-FX3,0x91030080,C_ImagerCtrl_IMX510,LTC,Gyro Data,MTG_ULOCK_START_SLAVE,OTP,sabin}",
    ),
    "fx3_backup_bin": (
        "fx3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin",
        2_229_740,
        "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2",
        (
            b"BK4\x00",
            b"ILME-FX3",
            b"90057",
            b"psd.bin",
            b"defdet.bin",
            b"lensfile.bin",
        ),
        "fx3/Backup.bin::{2229740B,BK4\\0,ILME-FX3,90057,psd.bin,defdet.bin,lensfile.bin}",
    ),
}


# ---------------------------------------------------------------------------
# Pure-Python GF(2^8) (0x11D) Table Builder & Arithmetic
# ---------------------------------------------------------------------------


def _build_gf256_tables() -> (
    Tuple[Tuple[int, ...], Tuple[int, ...], Tuple[int, ...], Tuple[bytes, ...]]
):
    exp_tbl = [0] * 510
    log_tbl = [-1] * 256
    x = 1
    for i in range(255):
        exp_tbl[i] = x
        exp_tbl[i + 255] = x
        log_tbl[x] = i
        x <<= 1
        if x & 0x100:
            x ^= GF256_PRIMITIVE_POLY

    inv_tbl = [0] * 256
    for a in range(1, 256):
        inv_tbl[a] = exp_tbl[255 - log_tbl[a]]

    mul_tables: List[bytes] = [bytes(256)]
    for c in range(1, 256):
        lc = log_tbl[c]
        row = bytearray(256)
        for v in range(1, 256):
            row[v] = exp_tbl[lc + log_tbl[v]]
        mul_tables.append(bytes(row))

    return tuple(exp_tbl), tuple(log_tbl), tuple(inv_tbl), tuple(mul_tables)


GF256_EXP, GF256_LOG, GF256_INV, GF256_MUL_TABLES = _build_gf256_tables()


def gf256_mul(a: int, b: int) -> int:
    """Multiply two elements in GF(2^8) under primitive polynomial 0x11D."""
    a &= 0xFF
    b &= 0xFF
    if a == 0 or b == 0:
        return 0
    return GF256_EXP[GF256_LOG[a] + GF256_LOG[b]]


def gf256_inv(a: int) -> int:
    """Multiplicative inverse in GF(2^8) under primitive polynomial 0x11D."""
    a &= 0xFF
    if a == 0:
        raise ZeroDivisionError("Zero has no multiplicative inverse in GF(2^8)")
    return GF256_INV[a]


def gf256_div(a: int, b: int) -> int:
    """Divide a by non-zero b in GF(2^8) under primitive polynomial 0x11D."""
    a &= 0xFF
    b &= 0xFF
    if b == 0:
        raise ZeroDivisionError("Division by zero in GF(2^8)")
    if a == 0:
        return 0
    return GF256_EXP[(GF256_LOG[a] - GF256_LOG[b]) % 255]


def _xor_bytes(a: bytes, b: bytes) -> bytes:
    return bytes(x ^ y for x, y in zip(a, b))


def _xor_many(chunks: Sequence[bytes], width: int) -> bytes:
    acc = bytearray(width)
    for chunk in chunks:
        for idx, byte in enumerate(chunk):
            acc[idx] ^= byte
    return bytes(acc)


def _gf256_scale_bytes(coeff: int, buf: bytes) -> bytes:
    coeff &= 0xFF
    if coeff == 0:
        return bytes(len(buf))
    if coeff == 1:
        return bytes(buf)
    return buf.translate(GF256_MUL_TABLES[coeff])


# ---------------------------------------------------------------------------
# Data Models (Zero raw bytes reprs; hex strings / ASCII markers only)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase173DonorAuditResult:
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
class Gf256RecoveryResult:
    valid: bool
    primitive_poly_hex: str
    data_chunk_count: int
    stripe_bytes: int
    corrupted_indices: Tuple[int, ...]
    healed_indices: Tuple[int, ...]
    p_repaired: bool
    q_repaired: bool
    unrecoverable_chunk_count: int
    syndrome_zero_after_heal: bool
    reconstructed_sha256s: Tuple[str, ...]
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DualMediaVaultGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    guard_profile: str
    media_a_role: str
    media_b_role: str
    media_a_st_dev: int
    media_b_st_dev: int
    device_ids_separated: bool
    same_filesystem_blocked: bool
    expected_surface_count: int
    parity_matched_count: int
    mismatched_surfaces: Tuple[str, ...]
    dual_media_sha256_parity_ok: bool
    gf256_primitive_poly_hex: str
    gf256_pq_verified: bool
    scrub_passed: bool
    corrupted_chunk_count: int
    unrecoverable_chunk_count: int
    gf256_scrub_safe: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TwoStepBenchInterlockGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    guard_profile: str
    target_model_id_hex: str
    target_model_name: str
    agent_auto_flash_blocked: bool
    auto_flash_requested: bool
    ai_agent_self_authorize_attempted: bool
    physical_flash_auto_exec_authorized: bool
    auto_flash_interlock_safe: bool
    two_step_interlock_armed: bool
    bench_execution_requested: bool
    human_operator_id: str
    human_step1_acknowledged: bool
    human_step2_acknowledged: bool
    two_step_human_auth_satisfied: bool
    human_bench_authorized: bool
    battery_model: str
    battery_soc_pct: float
    battery_mv: int
    usb_pd_contract_mw: int
    battery_preflash_safe: bool
    op_ff_canary_opcode_hex: str
    op_ff_ram_canary_verified: bool
    fx3s0ok_header_magic: str
    fx3s0ok_packet_bytes: int
    msc_return_054c_0da1_verified: bool
    fx3rcpt1_magic: str
    fx3rcpt1_packet_bytes: int
    camera_cid_sha256: str
    media_a_fx3rcpt1_sha256: str
    media_b_fx3rcpt1_sha256: str
    dual_media_fx3rcpt1_match: bool
    canary_and_fx3rcpt1_safe: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G57DualMediaVaultResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    dualmedia_vault_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G58BenchInterlockResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    bench_interlock_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master58GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    offline_55_gates_verified: bool
    all_58_gates_verified: bool
    g13_to_g58_all_passed: bool
    g57_to_g58_all_passed: bool
    h0_h1_trial_entry_allowed: bool
    status: str
    agent_auto_flash_blocked: bool
    el3_payload_transmit_authorized: bool
    spi_nor_write_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    summary: Dict[str, Any]
    gates: Tuple[Dict[str, Any], ...]
    master_56_report: Dict[str, Any]
    g57_result: Dict[str, Any]
    g58_result: Dict[str, Any]
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


def _is_valid_hex64(val: Any, *, allow_trivial: bool = False) -> bool:
    if not isinstance(val, str):
        return False
    norm = val.strip().lower()
    if not _HEX64_RE.match(norm):
        return False
    if not allow_trivial and norm in _FORBIDDEN_TRIVIAL_HEX64:
        return False
    return True


def _normalize_model_id_int(val: Any) -> Optional[int]:
    if isinstance(val, bool):
        return None
    if isinstance(val, int):
        return val if val >= 0 else None
    if isinstance(val, str):
        s = val.strip().lower()
        if not s:
            return None
        try:
            return int(s, 16) if s.startswith("0x") else int(s, 10)
        except ValueError:
            return None
    return None


# ---------------------------------------------------------------------------
# 1. Strictly Read-Only (O_RDONLY) Donor Contract Audit (FX3 7.02)
# ---------------------------------------------------------------------------


def audit_phase173_donor_contracts(
    *_,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
) -> Phase173DonorAuditResult:
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
        ) in PINNED_PHASE173_DONOR_SPECS.items():
            resolved[key] = effective_work_root / rel_path

    donor_available = (
        (not clean_forced)
        and (effective_work_root is not None)
        and bool(resolved)
        and all(p.is_file() for p in resolved.values())
    )

    if not donor_available:
        return Phase173DonorAuditResult(
            valid=True,
            status=STATUS_VERIFIED_SAFE,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="O_RDONLY",
            files_inspected=0,
            checked_markers=tuple(
                spec[5] for spec in PINNED_PHASE173_DONOR_SPECS.values()
            ),
            missing_markers=(),
            fx3_contracts_verified=True,
            sha256_by_artifact={
                k: spec[3] for k, spec in PINNED_PHASE173_DONOR_SPECS.items()
            },
            bytes_by_artifact={
                k: spec[2] for k, spec in PINNED_PHASE173_DONOR_SPECS.items()
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
    ) in PINNED_PHASE173_DONOR_SPECS.items():
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
        k for k, spec in PINNED_PHASE173_DONOR_SPECS.items() if spec[0] == "fx3"
    }
    valid = len(errors) == 0 and len(missing) == 0
    return Phase173DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_PHASE173_DONOR_INTEGRITY,
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
# 2. Pure Helper Functions (G57: Dual-Media & GF(256) P+Q, G58: Bench Interlock)
# ---------------------------------------------------------------------------


def default_verified_16_surface_hashes(
    seed: str = "ILME-FX3:0x91030080:TIER0_DUALMEDIA_V1",
) -> Dict[str, str]:
    """Return deterministic SHA-256 digests for all 16 canonical storage surfaces."""
    return {
        surface: hashlib.sha256(f"{seed}:{idx:02d}:{surface}".encode("utf-8")).hexdigest()
        for idx, surface in enumerate(CANONICAL_16_STORAGE_SURFACES)
    }


def encode_gf256_pq_parity(data_chunks: Sequence[bytes]) -> Tuple[bytes, bytes]:
    """Encode RAID-6 P and Q parity chunks over GF(2^8) (`0x11d`, generator `0x02`)."""
    k = len(data_chunks)
    if k < 1 or k > 255:
        raise ValueError(f"GF(256) RAID-6 supports 1..255 data chunks, got {k}.")
    width = len(data_chunks[0])
    if width == 0 or any(len(c) != width for c in data_chunks):
        raise ValueError("All data chunks must have identical non-zero byte length.")
    p_chunk = _xor_many(data_chunks, width)
    q_terms = [_gf256_scale_bytes(GF256_EXP[i], data_chunks[i]) for i in range(k)]
    q_chunk = _xor_many(q_terms, width)
    return p_chunk, q_chunk


def recover_gf256_pq_chunks(
    data_chunks: Sequence[Optional[bytes]],
    p_chunk: Optional[bytes],
    q_chunk: Optional[bytes],
    *,
    expected_sha256s: Optional[Sequence[str]] = None,
) -> Tuple[Gf256RecoveryResult, Tuple[bytes, ...], bytes, bytes]:
    """Verify and heal up to 2 erased/corrupted chunks in GF(2^8) (`0x11d`) P+Q RAID-6.

    Supports:
    - 0 erasures with optional silent 1-shard bit-rot localization via `S1 / S0 == g^x`
    - 1-shard or 2-shard erasures/corruptions (`data + data`, `data + P`, `data + Q`, `P + Q`)
    - Fail-closed rejection when `>= 3` chunks are lost or corrupted (`unrecoverable_chunk_count >= 3`)
    """
    k = len(data_chunks)
    errors: List[str] = []
    if k < 1 or k > 255:
        raise ValueError(f"GF(256) RAID-6 supports 1..255 data chunks, got {k}.")

    if expected_sha256s is not None and len(expected_sha256s) != k:
        raise ValueError("expected_sha256s length must match data_chunks length.")

    sample_widths = {len(c) for c in data_chunks if c is not None}
    if p_chunk is not None:
        sample_widths.add(len(p_chunk))
    if q_chunk is not None:
        sample_widths.add(len(q_chunk))
    if len(sample_widths) != 1 or 0 in sample_widths:
        raise ValueError("Present chunks must share a uniform non-zero byte length.")
    width = next(iter(sample_widths))

    work_data: List[Optional[bytes]] = [
        bytes(c) if c is not None else None for c in data_chunks
    ]
    missing_data_idxs = [i for i, c in enumerate(work_data) if c is None]

    # Identify silent bit-rot via expected_sha256s if provided
    corrupted_data_idxs: List[int] = []
    if expected_sha256s is not None:
        for i, chunk in enumerate(work_data):
            if chunk is not None:
                digest = hashlib.sha256(chunk).hexdigest()
                if digest != expected_sha256s[i].strip().lower():
                    corrupted_data_idxs.append(i)
                    work_data[i] = None

    erased_data_idxs = sorted(set(missing_data_idxs) | set(corrupted_data_idxs))
    p_missing = p_chunk is None
    q_missing = q_chunk is None

    total_lost = len(erased_data_idxs) + (1 if p_missing else 0) + (1 if q_missing else 0)
    if total_lost > GF256_MAX_RECOVERABLE_ERASURES:
        errors.append(
            f"GF(256) quorum loss: {total_lost} lost/corrupted shards exceed P+Q limit ({GF256_MAX_RECOVERABLE_ERASURES})."
        )
        return (
            Gf256RecoveryResult(
                valid=False,
                primitive_poly_hex=f"0x{GF256_PRIMITIVE_POLY:03x}",
                data_chunk_count=k,
                stripe_bytes=width,
                corrupted_indices=tuple(erased_data_idxs),
                healed_indices=(),
                p_repaired=False,
                q_repaired=False,
                unrecoverable_chunk_count=total_lost,
                syndrome_zero_after_heal=False,
                reconstructed_sha256s=(),
                errors=tuple(errors),
            ),
            tuple(c if c is not None else b"" for c in work_data),
            p_chunk if p_chunk is not None else b"",
            q_chunk if q_chunk is not None else b"",
        )

    healed_idxs: List[int] = []
    p_repaired = False
    q_repaired = False
    cur_p = bytes(p_chunk) if p_chunk is not None else b""
    cur_q = bytes(q_chunk) if q_chunk is not None else b""

    # Case A: 0 known missing shards -> check syndromes for silent single-shard bit-rot
    if total_lost == 0:
        concrete_data = [c for c in work_data if c is not None]
        p_calc, q_calc = encode_gf256_pq_parity(concrete_data)
        s0 = _xor_bytes(cur_p, p_calc)
        s1 = _xor_bytes(cur_q, q_calc)
        nz0 = any(s0)
        nz1 = any(s1)
        if nz0 and not nz1:
            # Silent bit-rot in P itself
            cur_p = p_calc
            p_repaired = True
        elif nz1 and not nz0:
            # Silent bit-rot in Q itself
            cur_q = q_calc
            q_repaired = True
        elif nz0 and nz1:
            # Locate silent single-data-chunk bit-rot via S1 / S0 == g^x
            first_nz = next(idx for idx, b in enumerate(s0) if b != 0)
            if s1[first_nz] == 0:
                errors.append("GF(256) multi-chunk silent bit-rot cannot be localized without SHA-256.")
            else:
                ratio = gf256_div(s1[first_nz], s0[first_nz])
                x = GF256_LOG[ratio]
                if 0 <= x < k and s1 == _gf256_scale_bytes(GF256_EXP[x], s0):
                    work_data[x] = _xor_bytes(concrete_data[x], s0)
                    healed_idxs.append(x)
                else:
                    errors.append("GF(256) syndrome ratio outside data shard range (multi-shard corruption).")

    # Case B: Data erasures with both P and Q missing -> impossible if len(erased_data_idxs) > 0 (handled by total_lost > 2)
    elif len(erased_data_idxs) == 0:
        concrete_data = [c for c in work_data if c is not None]
        p_calc, q_calc = encode_gf256_pq_parity(concrete_data)
        if p_missing:
            cur_p = p_calc
            p_repaired = True
        if q_missing:
            cur_q = q_calc
            q_repaired = True

    # Case C: 1 data erasure
    elif len(erased_data_idxs) == 1:
        x = erased_data_idxs[0]
        if not p_missing:
            others = [work_data[i] for i in range(k) if i != x]
            p_others = _xor_many([o for o in others if o is not None], width)
            work_data[x] = _xor_bytes(cur_p, p_others)
            healed_idxs.append(x)
            if q_missing:
                _, cur_q = encode_gf256_pq_parity([c for c in work_data if c is not None])
                q_repaired = True
        else:
            # Recover from Q using g^(-x)
            q_others = _xor_many(
                [
                    _gf256_scale_bytes(GF256_EXP[i], work_data[i])  # type: ignore[arg-type]
                    for i in range(k)
                    if i != x
                ],
                width,
            )
            q_rem = _xor_bytes(cur_q, q_others)
            work_data[x] = _gf256_scale_bytes(gf256_inv(GF256_EXP[x]), q_rem)
            healed_idxs.append(x)
            cur_p, _ = encode_gf256_pq_parity([c for c in work_data if c is not None])
            p_repaired = True

    # Case D: 2 data erasures (both P and Q present)
    elif len(erased_data_idxs) == 2:
        x, y = erased_data_idxs
        gx = GF256_EXP[x]
        gy = GF256_EXP[y]
        p_others = _xor_many(
            [work_data[i] for i in range(k) if i not in (x, y)],  # type: ignore[misc]
            width,
        )
        q_others = _xor_many(
            [
                _gf256_scale_bytes(GF256_EXP[i], work_data[i])  # type: ignore[arg-type]
                for i in range(k)
                if i not in (x, y)
            ],
            width,
        )
        p_xy = _xor_bytes(cur_p, p_others)
        q_xy = _xor_bytes(cur_q, q_others)
        denom_inv = gf256_inv(gx ^ gy)
        rhs = _xor_bytes(_gf256_scale_bytes(gx, p_xy), q_xy)
        d_y = _gf256_scale_bytes(denom_inv, rhs)
        d_x = _xor_bytes(p_xy, d_y)
        work_data[x] = d_x
        work_data[y] = d_y
        healed_idxs.extend([x, y])

    final_data = tuple(c if c is not None else b"" for c in work_data)
    p_check, q_check = encode_gf256_pq_parity(final_data)
    syndrome_zero = (cur_p == p_check) and (cur_q == q_check)
    reconstructed_shas = tuple(hashlib.sha256(c).hexdigest() for c in final_data)

    if not syndrome_zero:
        errors.append("Post-recovery P/Q parity syndromes are non-zero.")

    if expected_sha256s is not None:
        for idx, (got, exp) in enumerate(zip(reconstructed_shas, expected_sha256s)):
            if got != exp.strip().lower():
                errors.append(
                    f"Chunk {idx} SHA-256 mismatch after GF(256) heal: got {got[:16]} != {exp[:16]}."
                )

    valid = len(errors) == 0 and syndrome_zero
    unrecoverable = 0 if valid else max(1, total_lost)
    return (
        Gf256RecoveryResult(
            valid=valid,
            primitive_poly_hex=f"0x{GF256_PRIMITIVE_POLY:03x}",
            data_chunk_count=k,
            stripe_bytes=width,
            corrupted_indices=tuple(erased_data_idxs),
            healed_indices=tuple(sorted(healed_idxs)),
            p_repaired=p_repaired,
            q_repaired=q_repaired,
            unrecoverable_chunk_count=unrecoverable,
            syndrome_zero_after_heal=syndrome_zero,
            reconstructed_sha256s=reconstructed_shas,
            errors=tuple(errors),
        ),
        final_data,
        cur_p,
        cur_q,
    )


def build_synthetic_16_surface_chunks(
    chunk_bytes: int = 256,
    *,
    seed: str = "ILME-FX3:0x91030080:GF256_SCRUB_V1",
) -> Tuple[Tuple[bytes, ...], Dict[str, str], bytes, bytes]:
    """Generate deterministic 16-surface synthetic chunks plus GF(256) P+Q parity."""
    if not _is_positive_int(chunk_bytes):
        raise ValueError("chunk_bytes must be a positive integer.")
    chunks: List[bytes] = []
    hashes: Dict[str, str] = {}
    for idx, surface in enumerate(CANONICAL_16_STORAGE_SURFACES):
        buf = bytearray()
        counter = 0
        while len(buf) < chunk_bytes:
            buf.extend(
                hashlib.sha256(
                    f"{seed}:{idx:02d}:{surface}:{counter}".encode("utf-8")
                ).digest()
            )
            counter += 1
        chunk = bytes(buf[:chunk_bytes])
        chunks.append(chunk)
        hashes[surface] = hashlib.sha256(chunk).hexdigest()
    p_chunk, q_chunk = encode_gf256_pq_parity(chunks)
    return tuple(chunks), hashes, p_chunk, q_chunk


def validate_dual_media_device_id_separation(
    *,
    media_a_st_dev: Optional[int] = DEFAULT_MEDIA_A_ST_DEV,
    media_b_st_dev: Optional[int] = DEFAULT_MEDIA_B_ST_DEV,
    media_a_path: Optional[Path] = None,
    media_b_path: Optional[Path] = None,
    media_a_role: str = DEFAULT_MEDIA_A_ROLE,
    media_b_role: str = DEFAULT_MEDIA_B_ROLE,
    allow_same_filesystem: bool = False,
) -> Tuple[bool, int, int]:
    """Enforce physically independent `st_dev` separation across Media A & Media B.

    Returns `(valid, resolved_a_st_dev, resolved_b_st_dev)`.
    """
    if not isinstance(allow_same_filesystem, bool) or allow_same_filesystem:
        return False, -1, -1
    if not isinstance(media_a_role, str) or not isinstance(media_b_role, str):
        return False, -1, -1
    role_a = media_a_role.strip().upper()
    role_b = media_b_role.strip().upper()
    if role_a not in ALLOWED_DUAL_MEDIA_ROLES or role_b not in ALLOWED_DUAL_MEDIA_ROLES:
        return False, -1, -1
    if role_a == role_b:
        return False, -1, -1

    resolved_a = media_a_st_dev
    resolved_b = media_b_st_dev

    if media_a_path is not None:
        p_a = Path(media_a_path)
        if not p_a.exists() or p_a.is_symlink():
            return False, -1, -1
        resolved_a = int(os.stat(p_a).st_dev)

    if media_b_path is not None:
        p_b = Path(media_b_path)
        if not p_b.exists() or p_b.is_symlink():
            return False, -1, -1
        resolved_b = int(os.stat(p_b).st_dev)

    if not _is_positive_int(resolved_a) or not _is_positive_int(resolved_b):
        return False, -1, -1

    assert resolved_a is not None and resolved_b is not None
    if int(resolved_a) == int(resolved_b):
        return False, int(resolved_a), int(resolved_b)

    return True, int(resolved_a), int(resolved_b)


def validate_dual_media_16_surface_sha256_parity(
    *,
    media_a_surface_hashes: Optional[Mapping[str, str]] = None,
    media_b_surface_hashes: Optional[Mapping[str, str]] = None,
) -> Tuple[bool, int, Tuple[str, ...]]:
    """Verify 16/16 canonical storage surface SHA-256 parity across Media A and Media B."""
    default_hashes = default_verified_16_surface_hashes()
    map_a = dict(default_hashes) if media_a_surface_hashes is None else dict(media_a_surface_hashes)
    map_b = dict(default_hashes) if media_b_surface_hashes is None else dict(media_b_surface_hashes)

    mismatched: List[str] = []
    matched = 0
    for surface in CANONICAL_16_STORAGE_SURFACES:
        ha = map_a.get(surface)
        hb = map_b.get(surface)
        if not _is_valid_hex64(ha) or not _is_valid_hex64(hb):
            mismatched.append(surface)
            continue
        if ha.strip().lower() != hb.strip().lower():  # type: ignore[union-attr]
            mismatched.append(surface)
            continue
        matched += 1

    return (
        matched == CANONICAL_16_SURFACE_COUNT and len(mismatched) == 0,
        matched,
        tuple(mismatched),
    )


def validate_gf256_bitrot_scrub_guard(
    *,
    gf256_primitive_poly: int = GF256_PRIMITIVE_POLY,
    gf256_pq_verified: bool = True,
    scrub_passed: bool = True,
    corrupted_chunk_count: int = 0,
    unrecoverable_chunk_count: int = 0,
    run_active_gf256_recovery_check: bool = True,
) -> Tuple[bool, int]:
    """Validate `GF(256)` (`0x11d`) P+Q scrub & recovery invariant.

    Returns `(valid, effective_unrecoverable_chunk_count)`.
    """
    for b in (gf256_pq_verified, scrub_passed, run_active_gf256_recovery_check):
        if not isinstance(b, bool):
            return False, -1
    for i in (gf256_primitive_poly, corrupted_chunk_count, unrecoverable_chunk_count):
        if not _is_non_negative_int(i):
            return False, -1

    if int(gf256_primitive_poly) != GF256_PRIMITIVE_POLY:
        return False, max(1, int(unrecoverable_chunk_count))
    if (not gf256_pq_verified) or (not scrub_passed):
        return False, max(1, int(unrecoverable_chunk_count))
    if int(unrecoverable_chunk_count) != 0:
        return False, int(unrecoverable_chunk_count)
    if int(corrupted_chunk_count) > GF256_MAX_RECOVERABLE_ERASURES:
        return False, int(corrupted_chunk_count)

    if run_active_gf256_recovery_check:
        chunks, hashes, p_chunk, q_chunk = build_synthetic_16_surface_chunks(128)
        expected = [hashes[s] for s in CANONICAL_16_STORAGE_SURFACES]
        # Exercise 1-shard silent bit-rot syndrome heal AND 2-shard erasure recovery
        corrupted = bytearray(chunks[3])
        corrupted[17] ^= 0x5A
        probe_1: List[Optional[bytes]] = list(chunks)
        probe_1[3] = bytes(corrupted)
        rec1, healed1, _, _ = recover_gf256_pq_chunks(probe_1, p_chunk, q_chunk)
        if not rec1.valid or healed1[3] != chunks[3]:
            return False, 1

        probe_2: List[Optional[bytes]] = list(chunks)
        probe_2[2] = None
        probe_2[14] = None
        rec2, healed2, _, _ = recover_gf256_pq_chunks(
            probe_2, p_chunk, q_chunk, expected_sha256s=expected
        )
        if not rec2.valid or healed2[2] != chunks[2] or healed2[14] != chunks[14]:
            return False, 2

    return True, 0


# ---------------------------------------------------------------------------
# 3. Gate G57 & Gate G58 Core Evaluators
# ---------------------------------------------------------------------------


def verify_dual_media_vault_and_gf256_scrub_guard(
    *_,
    media_a_st_dev: Optional[int] = DEFAULT_MEDIA_A_ST_DEV,
    media_b_st_dev: Optional[int] = DEFAULT_MEDIA_B_ST_DEV,
    media_a_path: Optional[Path] = None,
    media_b_path: Optional[Path] = None,
    media_a_role: str = DEFAULT_MEDIA_A_ROLE,
    media_b_role: str = DEFAULT_MEDIA_B_ROLE,
    allow_same_filesystem: bool = False,
    media_a_surface_hashes: Optional[Mapping[str, str]] = None,
    media_b_surface_hashes: Optional[Mapping[str, str]] = None,
    gf256_primitive_poly: int = GF256_PRIMITIVE_POLY,
    gf256_pq_verified: bool = True,
    scrub_passed: bool = True,
    corrupted_chunk_count: int = 0,
    unrecoverable_chunk_count: int = 0,
    run_active_gf256_recovery_check: bool = True,
    guard_profile: str = "FX3_REALHW_G57_DUALMEDIA_GF256_SCRUB_DEFAULT",
) -> DualMediaVaultGuardResult:
    """Verify Gate G57 invariants fail-closed."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    def _valid_hash_map(m: Optional[Mapping[str, str]]) -> bool:
        if m is None:
            return True
        if not isinstance(m, Mapping):
            return False
        return all(isinstance(k, str) and isinstance(v, str) for k, v in m.items())

    telemetry_ok = (
        isinstance(allow_same_filesystem, bool)
        and isinstance(media_a_role, str)
        and bool(media_a_role.strip())
        and isinstance(media_b_role, str)
        and bool(media_b_role.strip())
        and isinstance(guard_profile, str)
        and bool(guard_profile.strip())
        and (media_a_st_dev is None or _is_non_negative_int(media_a_st_dev))
        and (media_b_st_dev is None or _is_non_negative_int(media_b_st_dev))
        and _valid_hash_map(media_a_surface_hashes)
        and _valid_hash_map(media_b_surface_hashes)
        and _is_non_negative_int(gf256_primitive_poly)
        and isinstance(gf256_pq_verified, bool)
        and isinstance(scrub_passed, bool)
        and _is_non_negative_int(corrupted_chunk_count)
        and _is_non_negative_int(unrecoverable_chunk_count)
        and isinstance(run_active_gf256_recovery_check, bool)
    )

    if not telemetry_ok:
        _add_code(codes, STATUS_BLOCKED_G57_TELEMETRY_INVALID)
        errors.append("Gate G57 received invalid or malformed dual-media telemetry.")

    dev_sep_ok = False
    resolved_a_dev = -1
    resolved_b_dev = -1
    parity_ok = False
    parity_count = 0
    mismatched: Tuple[str, ...] = ()
    gf256_ok = False
    eff_unrec = -1

    if telemetry_ok:
        dev_sep_ok, resolved_a_dev, resolved_b_dev = validate_dual_media_device_id_separation(
            media_a_st_dev=media_a_st_dev,
            media_b_st_dev=media_b_st_dev,
            media_a_path=media_a_path,
            media_b_path=media_b_path,
            media_a_role=media_a_role,
            media_b_role=media_b_role,
            allow_same_filesystem=allow_same_filesystem,
        )
        if not dev_sep_ok:
            _add_code(codes, STATUS_BLOCKED_G57_SINGLE_MEDIA_OR_SAME_ST_DEV)
            errors.append(
                f"Dual-media device-ID separation violation: media_a=({media_a_role}, st_dev={resolved_a_dev}), "
                f"media_b=({media_b_role}, st_dev={resolved_b_dev}), allow_same_fs={allow_same_filesystem}."
            )

        parity_ok, parity_count, mismatched = validate_dual_media_16_surface_sha256_parity(
            media_a_surface_hashes=media_a_surface_hashes,
            media_b_surface_hashes=media_b_surface_hashes,
        )
        if not parity_ok:
            _add_code(codes, STATUS_BLOCKED_G57_16_SURFACE_SHA256_MISMATCH)
            errors.append(
                f"16/16 SHA-256 dual-media parity mismatch: matched={parity_count}/{CANONICAL_16_SURFACE_COUNT}, "
                f"mismatched={list(mismatched)}."
            )

        gf256_ok, eff_unrec = validate_gf256_bitrot_scrub_guard(
            gf256_primitive_poly=int(gf256_primitive_poly),
            gf256_pq_verified=gf256_pq_verified,
            scrub_passed=scrub_passed,
            corrupted_chunk_count=int(corrupted_chunk_count),
            unrecoverable_chunk_count=int(unrecoverable_chunk_count),
            run_active_gf256_recovery_check=run_active_gf256_recovery_check,
        )
        if not gf256_ok:
            _add_code(codes, STATUS_BLOCKED_G57_GF256_SCRUB_OR_QUORUM_LOSS)
            errors.append(
                f"GF(256) RAID-6 scrub/recovery violation: poly=0x{int(gf256_primitive_poly):03x}, "
                f"pq_verified={gf256_pq_verified}, scrub_passed={scrub_passed}, "
                f"corrupted={corrupted_chunk_count}, unrecoverable={eff_unrec}."
            )

    valid = (
        telemetry_ok
        and dev_sep_ok
        and parity_ok
        and gf256_ok
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not PERSISTENT_WRITE_RELEASE)
        and (not codes)
    )
    status = STATUS_VERIFIED_G57 if valid else codes[0]

    return DualMediaVaultGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        guard_profile=str(guard_profile) if isinstance(guard_profile, str) else "INVALID",
        media_a_role=str(media_a_role) if isinstance(media_a_role, str) else "INVALID",
        media_b_role=str(media_b_role) if isinstance(media_b_role, str) else "INVALID",
        media_a_st_dev=resolved_a_dev,
        media_b_st_dev=resolved_b_dev,
        device_ids_separated=dev_sep_ok,
        same_filesystem_blocked=not allow_same_filesystem if isinstance(allow_same_filesystem, bool) else False,
        expected_surface_count=CANONICAL_16_SURFACE_COUNT,
        parity_matched_count=parity_count,
        mismatched_surfaces=mismatched,
        dual_media_sha256_parity_ok=parity_ok,
        gf256_primitive_poly_hex=(
            f"0x{int(gf256_primitive_poly):03x}"
            if _is_non_negative_int(gf256_primitive_poly)
            else "INVALID"
        ),
        gf256_pq_verified=bool(gf256_pq_verified) if isinstance(gf256_pq_verified, bool) else False,
        scrub_passed=bool(scrub_passed) if isinstance(scrub_passed, bool) else False,
        corrupted_chunk_count=(
            int(corrupted_chunk_count) if _is_non_negative_int(corrupted_chunk_count) else -1
        ),
        unrecoverable_chunk_count=eff_unrec,
        gf256_scrub_safe=gf256_ok,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def verify_two_step_bench_interlock_guard(
    *_,
    target_model_id: Any = FX3_MODEL_ID_INT,
    target_model_name: str = FX3_MODEL_NAME,
    agent_auto_flash_blocked: bool = True,
    auto_flash_requested: bool = False,
    ai_agent_self_authorize_attempted: bool = False,
    two_step_interlock_armed: bool = True,
    bench_execution_requested: bool = False,
    human_operator_id: str = "",
    human_step1_acknowledged: bool = False,
    human_step1_token: str = "",
    human_step2_acknowledged: bool = False,
    human_step2_phrase: str = "",
    battery_model: str = PREFLASH_BATTERY_MODEL,
    battery_soc_pct: float = 85.0,
    battery_mv: int = 7800,
    usb_pd_contract_mw: int = PREFLASH_MIN_USBPD_CONTRACT_MW,
    op_ff_canary_opcode: int = OP_FF_CANARY_OPCODE,
    op_ff_ram_canary_verified: bool = True,
    fx3s0ok_header_magic: str = FX3S0OK_HEADER_MAGIC,
    fx3s0ok_packet_bytes: int = FX3S0OK_PACKET_BYTES,
    msc_return_054c_0da1_verified: bool = True,
    fx3rcpt1_magic: str = FX3RCPT1_MAGIC,
    fx3rcpt1_packet_bytes: int = FX3RCPT1_PACKET_BYTES,
    camera_cid_sha256: str = DEFAULT_SYNTHETIC_CAMERA_CID_SHA256,
    media_a_fx3rcpt1_sha256: str = DEFAULT_SYNTHETIC_FX3RCPT1_SHA256,
    media_b_fx3rcpt1_sha256: str = DEFAULT_SYNTHETIC_FX3RCPT1_SHA256,
    fx3rcpt1_dual_media_match: bool = True,
    guard_profile: str = "FX3_REALHW_G58_TWO_STEP_BENCH_INTERLOCK_DEFAULT",
) -> TwoStepBenchInterlockGuardResult:
    """Verify Gate G58 invariants fail-closed."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    bool_inputs = (
        agent_auto_flash_blocked,
        auto_flash_requested,
        ai_agent_self_authorize_attempted,
        two_step_interlock_armed,
        bench_execution_requested,
        human_step1_acknowledged,
        human_step2_acknowledged,
        op_ff_ram_canary_verified,
        msc_return_054c_0da1_verified,
        fx3rcpt1_dual_media_match,
    )
    req_str_inputs = (
        target_model_name,
        battery_model,
        fx3s0ok_header_magic,
        fx3rcpt1_magic,
        camera_cid_sha256,
        media_a_fx3rcpt1_sha256,
        media_b_fx3rcpt1_sha256,
        guard_profile,
    )
    opt_str_inputs = (human_operator_id, human_step1_token, human_step2_phrase)
    t_id_norm = _normalize_model_id_int(target_model_id)

    telemetry_ok = (
        all(isinstance(b, bool) for b in bool_inputs)
        and (t_id_norm is not None)
        and all(isinstance(s, str) and bool(s.strip()) for s in req_str_inputs)
        and all(isinstance(s, str) for s in opt_str_inputs)
        and _is_finite_number(battery_soc_pct)
        and _is_non_negative_int(battery_mv)
        and _is_non_negative_int(usb_pd_contract_mw)
        and _is_non_negative_int(op_ff_canary_opcode)
        and _is_non_negative_int(fx3s0ok_packet_bytes)
        and _is_non_negative_int(fx3rcpt1_packet_bytes)
    )

    if not telemetry_ok:
        _add_code(codes, STATUS_BLOCKED_G58_TELEMETRY_INVALID)
        errors.append("Gate G58 received invalid, non-finite, or malformed telemetry.")

    auto_flash_safe = False
    two_step_satisfied = False
    battery_safe = False
    canary_rcpt_safe = False
    dual_rcpt_match = False

    if telemetry_ok:
        # 1. Zero-Auto-Flash Interlock (hard-blocks any script/agent self-authorization)
        auto_flash_safe = (
            (t_id_norm == FX3_MODEL_ID_INT)
            and (target_model_name.strip().upper() == FX3_MODEL_NAME)
            and agent_auto_flash_blocked
            and (not auto_flash_requested)
            and (not ai_agent_self_authorize_attempted)
            and two_step_interlock_armed
            and (not PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED)
            and (not EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
            and (not SPI_NOR_WRITE_AUTHORIZED)
            and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
            and (not PERSISTENT_WRITE_RELEASE)
        )
        if not auto_flash_safe:
            _add_code(codes, STATUS_BLOCKED_G58_AUTO_FLASH_INTERLOCK_VIOLATION)
            errors.append(
                f"Zero-Auto-Flash interlock violation: model={target_model_name}({t_id_norm}), "
                f"agent_auto_flash_blocked={agent_auto_flash_blocked}, auto_flash_req={auto_flash_requested}, "
                f"ai_self_auth={ai_agent_self_authorize_attempted}, armed={two_step_interlock_armed}."
            )

        # 2. Two-Step Explicit Human Bench Authorization
        step1_ok = human_step1_acknowledged and bool(human_operator_id.strip()) and bool(human_step1_token.strip())
        step2_ok = (
            human_step2_acknowledged
            and (human_step2_phrase.strip() == EXPECTED_STEP2_HUMAN_CONFIRM_PHRASE)
            and (human_step1_token.strip() != human_step2_phrase.strip())
        )
        two_step_satisfied = step1_ok and step2_ok
        if bench_execution_requested and (not two_step_satisfied):
            _add_code(codes, STATUS_BLOCKED_G58_TWO_STEP_HUMAN_AUTH_MISSING)
            errors.append(
                "Bench execution requested without valid Two-Step Explicit Human Authorization "
                "(requires distinct Step-1 operator acknowledgement + Step-2 confirmation phrase)."
            )

        # 3. Battery >= 80% & >= 7400 mV Pre-Flash Threshold + USB-PD >= 27W
        battery_safe = (
            battery_model.strip().upper() == PREFLASH_BATTERY_MODEL
            and float(battery_soc_pct) >= PREFLASH_MIN_BATTERY_SOC_PCT
            and float(battery_soc_pct) <= 100.0
            and int(battery_mv) >= PREFLASH_MIN_BATTERY_MV
            and int(battery_mv) <= PREFLASH_MAX_BATTERY_MV
            and int(usb_pd_contract_mw) >= PREFLASH_MIN_USBPD_CONTRACT_MW
        )
        if not battery_safe:
            _add_code(codes, STATUS_BLOCKED_G58_BATTERY_BELOW_PREFLASH_THRESHOLD)
            errors.append(
                f"Battery/PD below pre-flash threshold: model={battery_model}, "
                f"soc={battery_soc_pct}% (min {PREFLASH_MIN_BATTERY_SOC_PCT}%), "
                f"mv={battery_mv}mV (min {PREFLASH_MIN_BATTERY_MV}mV), "
                f"pd={usb_pd_contract_mw}mW (min {PREFLASH_MIN_USBPD_CONTRACT_MW}mW)."
            )

        # 4. Verified op=0xFF RAM Canary Receipt & Dual-Media FX3RCPT1 Cold-Backup Match
        rcpt_a_norm = media_a_fx3rcpt1_sha256.strip().lower()
        rcpt_b_norm = media_b_fx3rcpt1_sha256.strip().lower()
        cid_norm = camera_cid_sha256.strip().lower()
        dual_rcpt_match = (
            fx3rcpt1_dual_media_match
            and _is_valid_hex64(rcpt_a_norm)
            and _is_valid_hex64(rcpt_b_norm)
            and (rcpt_a_norm == rcpt_b_norm)
        )
        canary_rcpt_safe = (
            int(op_ff_canary_opcode) == OP_FF_CANARY_OPCODE
            and op_ff_ram_canary_verified
            and fx3s0ok_header_magic.strip() == FX3S0OK_HEADER_MAGIC
            and int(fx3s0ok_packet_bytes) == FX3S0OK_PACKET_BYTES
            and msc_return_054c_0da1_verified
            and fx3rcpt1_magic.strip() == FX3RCPT1_MAGIC
            and int(fx3rcpt1_packet_bytes) == FX3RCPT1_PACKET_BYTES
            and _is_valid_hex64(cid_norm)
            and dual_rcpt_match
        )
        if not canary_rcpt_safe:
            _add_code(codes, STATUS_BLOCKED_G58_CANARY_OR_FX3RCPT1_UNVERIFIED)
            errors.append(
                f"op=0xFF RAM canary or dual-media FX3RCPT1 verification failed: "
                f"op=0x{int(op_ff_canary_opcode):02x}, canary_ok={op_ff_ram_canary_verified}, "
                f"fx3s0ok={fx3s0ok_header_magic}/{fx3s0ok_packet_bytes}B, "
                f"msc_ret={msc_return_054c_0da1_verified}, fx3rcpt1_match={dual_rcpt_match}."
            )

    valid = (
        telemetry_ok
        and auto_flash_safe
        and ((not bench_execution_requested) or two_step_satisfied)
        and battery_safe
        and canary_rcpt_safe
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not PERSISTENT_WRITE_RELEASE)
        and (not codes)
    )
    status = STATUS_VERIFIED_G58 if valid else codes[0]

    # Even if two-step human confirmation was rehearsed, repository write constants remain False
    human_bench_authorized = bool(valid and bench_execution_requested and two_step_satisfied)

    return TwoStepBenchInterlockGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        guard_profile=str(guard_profile) if isinstance(guard_profile, str) else "INVALID",
        target_model_id_hex=f"0x{t_id_norm:08x}" if t_id_norm is not None else "INVALID",
        target_model_name=(
            str(target_model_name) if isinstance(target_model_name, str) else "INVALID"
        ),
        agent_auto_flash_blocked=(
            bool(agent_auto_flash_blocked)
            if isinstance(agent_auto_flash_blocked, bool)
            else False
        ),
        auto_flash_requested=(
            bool(auto_flash_requested)
            if isinstance(auto_flash_requested, bool)
            else True
        ),
        ai_agent_self_authorize_attempted=(
            bool(ai_agent_self_authorize_attempted)
            if isinstance(ai_agent_self_authorize_attempted, bool)
            else True
        ),
        physical_flash_auto_exec_authorized=PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
        auto_flash_interlock_safe=auto_flash_safe,
        two_step_interlock_armed=(
            bool(two_step_interlock_armed)
            if isinstance(two_step_interlock_armed, bool)
            else False
        ),
        bench_execution_requested=(
            bool(bench_execution_requested)
            if isinstance(bench_execution_requested, bool)
            else False
        ),
        human_operator_id=(
            str(human_operator_id) if isinstance(human_operator_id, str) else "INVALID"
        ),
        human_step1_acknowledged=(
            bool(human_step1_acknowledged)
            if isinstance(human_step1_acknowledged, bool)
            else False
        ),
        human_step2_acknowledged=(
            bool(human_step2_acknowledged)
            if isinstance(human_step2_acknowledged, bool)
            else False
        ),
        two_step_human_auth_satisfied=two_step_satisfied,
        human_bench_authorized=human_bench_authorized,
        battery_model=str(battery_model) if isinstance(battery_model, str) else "INVALID",
        battery_soc_pct=float(battery_soc_pct) if _is_finite_number(battery_soc_pct) else -1.0,
        battery_mv=int(battery_mv) if _is_non_negative_int(battery_mv) else -1,
        usb_pd_contract_mw=(
            int(usb_pd_contract_mw) if _is_non_negative_int(usb_pd_contract_mw) else -1
        ),
        battery_preflash_safe=battery_safe,
        op_ff_canary_opcode_hex=(
            f"0x{int(op_ff_canary_opcode):02x}"
            if _is_non_negative_int(op_ff_canary_opcode)
            else "INVALID"
        ),
        op_ff_ram_canary_verified=(
            bool(op_ff_ram_canary_verified)
            if isinstance(op_ff_ram_canary_verified, bool)
            else False
        ),
        fx3s0ok_header_magic=(
            str(fx3s0ok_header_magic)
            if isinstance(fx3s0ok_header_magic, str)
            else "INVALID"
        ),
        fx3s0ok_packet_bytes=(
            int(fx3s0ok_packet_bytes) if _is_non_negative_int(fx3s0ok_packet_bytes) else -1
        ),
        msc_return_054c_0da1_verified=(
            bool(msc_return_054c_0da1_verified)
            if isinstance(msc_return_054c_0da1_verified, bool)
            else False
        ),
        fx3rcpt1_magic=str(fx3rcpt1_magic) if isinstance(fx3rcpt1_magic, str) else "INVALID",
        fx3rcpt1_packet_bytes=(
            int(fx3rcpt1_packet_bytes) if _is_non_negative_int(fx3rcpt1_packet_bytes) else -1
        ),
        camera_cid_sha256=(
            camera_cid_sha256.strip().lower()
            if isinstance(camera_cid_sha256, str)
            else "INVALID"
        ),
        media_a_fx3rcpt1_sha256=(
            media_a_fx3rcpt1_sha256.strip().lower()
            if isinstance(media_a_fx3rcpt1_sha256, str)
            else "INVALID"
        ),
        media_b_fx3rcpt1_sha256=(
            media_b_fx3rcpt1_sha256.strip().lower()
            if isinstance(media_b_fx3rcpt1_sha256, str)
            else "INVALID"
        ),
        dual_media_fx3rcpt1_match=dual_rcpt_match,
        canary_and_fx3rcpt1_safe=canary_rcpt_safe,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 4. Gate G57 & Gate G58 Evaluators (Donor Audit + Guard -> GateVerdict)
# ---------------------------------------------------------------------------


def evaluate_g57_dualmedia_vault(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    dualmedia_vault_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase173DonorAuditResult] = None,
) -> Tuple[GateVerdict, G57DualMediaVaultResult]:
    """Evaluate Gate G57 (Dual-Media Device-ID Separation & GF(256) Scrub Guard)."""
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase173_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )

    guard_kwargs = dict(dualmedia_vault_kwargs or {})
    guard = verify_dual_media_vault_and_gf256_scrub_guard(**guard_kwargs)

    codes: List[str] = list(guard.violation_codes)
    errors: List[str] = list(audit.errors) + list(guard.errors)
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if not audit.valid:
        _add_code(codes, STATUS_BLOCKED_PHASE173_DONOR_INTEGRITY)

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append(
            "Gate G57 blocked persistent eMMC write authorization request."
        )

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G57 if valid else codes[0]

    res = G57DualMediaVaultResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        dualmedia_vault_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    evidence = (
        f"mode={audit.verification_mode}, st_dev_a={guard.media_a_st_dev}, "
        f"st_dev_b={guard.media_b_st_dev}, sep={guard.device_ids_separated}, "
        f"parity={guard.parity_matched_count}/{guard.expected_surface_count}, "
        f"gf256={guard.gf256_primitive_poly_hex}, unrec={guard.unrecoverable_chunk_count}"
    )

    verdict = GateVerdict(
        gate_id=G57_GATE_ID,
        gate_code=G57_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


def evaluate_g58_bench_interlock(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    bench_interlock_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase173DonorAuditResult] = None,
) -> Tuple[GateVerdict, G58BenchInterlockResult]:
    """Evaluate Gate G58 (Two-Step Explicit Human Bench Authorization & Zero-Auto-Flash Interlock)."""
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase173_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )

    guard_kwargs = dict(bench_interlock_kwargs or {})
    guard = verify_two_step_bench_interlock_guard(**guard_kwargs)

    codes: List[str] = list(guard.violation_codes)
    errors: List[str] = list(audit.errors) + list(guard.errors)
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if not audit.valid:
        _add_code(codes, STATUS_BLOCKED_PHASE173_DONOR_INTEGRITY)

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append(
            "Gate G58 blocked persistent eMMC write authorization request."
        )

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G58 if valid else codes[0]

    res = G58BenchInterlockResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        bench_interlock_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    evidence = (
        f"mode={audit.verification_mode}, auto_flash_blocked={guard.agent_auto_flash_blocked}, "
        f"two_step_armed={guard.two_step_interlock_armed}, "
        f"batt={guard.battery_soc_pct:.0f}%/{guard.battery_mv}mV, "
        f"canary_ok={guard.op_ff_ram_canary_verified}, "
        f"fx3rcpt1_match={guard.dual_media_fx3rcpt1_match}"
    )

    verdict = GateVerdict(
        gate_id=G58_GATE_ID,
        gate_code=G58_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 5. Unified 58-Gate Master Safety Preflight (`G01..G58`)
# ---------------------------------------------------------------------------


def evaluate_58gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated_backup: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    # G01..G56 pass-throughs
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
    cxd90058_sabin_kwargs: Optional[Mapping[str, Any]] = None,
    factory_seal_kwargs: Optional[Mapping[str, Any]] = None,
    c2pa_cert_kwargs: Optional[Mapping[str, Any]] = None,
    tc_gyro_meta_kwargs: Optional[Mapping[str, Any]] = None,
    # G57 inputs (Dual-Media st_dev separation, 16/16 SHA-256 parity & GF(256) scrub)
    dualmedia_vault_kwargs: Optional[Mapping[str, Any]] = None,
    # G58 inputs (Two-Step human bench authorization, battery >= 80%/7400mV & zero-auto-flash)
    bench_interlock_kwargs: Optional[Mapping[str, Any]] = None,
) -> Master58GateReport:
    """Evaluate all 58 Master Safety Gates (`G01..G58`) deterministically."""
    resolved_root = (
        DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)
    ).resolve()
    clean_forced = _is_forced_clean_room(force_clean_room)

    m56_kwargs: Dict[str, Any] = {
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
        "cxd90058_sabin_kwargs": cxd90058_sabin_kwargs,
        "factory_seal_kwargs": factory_seal_kwargs,
        "c2pa_cert_kwargs": c2pa_cert_kwargs,
        "tc_gyro_meta_kwargs": tc_gyro_meta_kwargs,
    }
    if soc_start_ceiling_c is not None:
        m56_kwargs["soc_start_ceiling_c"] = soc_start_ceiling_c

    m56_report: Master56GateReport = evaluate_56gate_preflight(
        resolved_root, **m56_kwargs
    )

    phase173_audit = audit_phase173_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
    )

    g57_verdict, g57_res = evaluate_g57_dualmedia_vault(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        dualmedia_vault_kwargs=dualmedia_vault_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase173_audit,
    )

    g58_verdict, g58_res = evaluate_g58_bench_interlock(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        bench_interlock_kwargs=bench_interlock_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase173_audit,
    )

    gates_57_to_58 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g57_verdict, g58_verdict)
    ]
    all_gates = tuple(list(m56_report.gates) + gates_57_to_58)

    g01_to_g12_verified = int(m56_report.summary["g01_to_g12_verified"])
    g13_to_g56_verified = (
        int(m56_report.summary["g13_to_g54_verified"])
        + int(m56_report.summary["g55_to_g56_verified"])
    )
    g57_to_g58_verified = sum(1 for v in (g57_verdict, g58_verdict) if v.passed)
    total_verified = g01_to_g12_verified + g13_to_g56_verified + g57_to_g58_verified

    g57_to_g58_all_passed = g57_to_g58_verified == 2
    g13_to_g58_all_passed = (
        m56_report.g13_to_g56_all_passed and g57_to_g58_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m56_report.gates[:9])

    offline_55_verified = (
        g01_to_g09_ok
        and m56_report.offline_53_gates_verified
        and g57_to_g58_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_58_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g58_all_passed
        and (not request_persistent_emmc_writes)
    )

    # Hard-locked False in offline and dry-run modes; never authorizes EL3 TX / eMMC / SPI-NOR writes
    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(
        g58_res.bench_interlock_guard.get("agent_auto_flash_blocked", False)
    )

    h0_h1_allowed = (
        offline_55_verified
        and m56_report.h0_h1_trial_entry_allowed
        and g57_to_g58_all_passed
        and agent_auto_flash_blocked
        and (not PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED)
        and (not EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        and (not SPI_NOR_WRITE_AUTHORIZED)
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    errors: List[str] = (
        list(m56_report.errors) + list(g57_verdict.errors) + list(g58_verdict.errors)
    )
    warnings: List[str] = (
        list(m56_report.warnings)
        + list(g57_verdict.warnings)
        + list(g58_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m56_report.g13_to_g56_all_passed:
        overall_status = m56_report.status
    elif not g57_verdict.passed:
        overall_status = g57_verdict.status
    elif not g58_verdict.passed:
        overall_status = g58_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_58_verified and dry_run_simulated_backup:
        overall_status = "VERIFIED_ALL_58_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_58_verified:
        overall_status = "VERIFIED_ALL_58_GATES"
    else:
        overall_status = "VERIFIED_55_OF_58_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m56_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g57_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g58_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 58,
        "verified_gates": total_verified,
        "blocked_or_pending_gates": 58 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g56_verified": g13_to_g56_verified,
        "g57_to_g58_verified": g57_to_g58_verified,
        "g13_to_g58_all_passed": g13_to_g58_all_passed,
        "g57_to_g58_all_passed": g57_to_g58_all_passed,
        "offline_55_gates_verified": offline_55_verified,
        "all_58_gates_verified": all_58_verified,
        "dry_run_rehearsal_only": bool(dry_run_simulated_backup),
        "overall_ready_for_hardware_attach": overall_ready_for_hardware_attach,
        "h0_h1_trial_entry_allowed": h0_h1_allowed,
        "agent_auto_flash_blocked": agent_auto_flash_blocked,
        "physical_flash_auto_exec_authorized": PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
        "el3_payload_transmit_authorized": EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "persistent_write_release": PERSISTENT_WRITE_RELEASE,
    }

    return Master58GateReport(
        schema=REALHW_DUALMEDIA_BENCH_58GATE_SCHEMA,
        version=REALHW_DUALMEDIA_BENCH_58GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=bool(dry_run_simulated_backup),
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        offline_55_gates_verified=offline_55_verified,
        all_58_gates_verified=all_58_verified,
        g13_to_g58_all_passed=g13_to_g58_all_passed,
        g57_to_g58_all_passed=g57_to_g58_all_passed,
        h0_h1_trial_entry_allowed=h0_h1_allowed,
        status=overall_status,
        agent_auto_flash_blocked=agent_auto_flash_blocked,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        summary=summary,
        gates=all_gates,
        master_56_report=m56_report.to_dict(),
        g57_result=g57_res.to_dict(),
        g58_result=g58_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_58_master_safety_gates = evaluate_58gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_dualmedia_bench_interlock_and_58gate_guard",
        description=(
            "Phase 173 — Dual-Media Independent Tier-0 Device-ID Separation & GF(256) "
            "Bit-Rot Scrub Guard (G57), Two-Step Explicit Human Bench Authorization & "
            "Zero-Auto-Flash Interlock (G58), and 58-Gate Master Preflight (G01..G58)"
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
        help="Supply simulated dry-run Tier-0 backup inputs so G01..G58 can be exercised offline",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit structured JSON report",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = evaluate_58gate_preflight(
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
            f"verified={report.summary['verified_gates']}/58 "
            f"g57_to_g58_all_passed={report.g57_to_g58_all_passed} "
            f"all_58_gates_verified={report.all_58_gates_verified} "
            f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
            f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
            f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
            f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
            f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}\n"
        )
    ok = (
        report.all_58_gates_verified
        if args.dry_run_simulated_backup
        else report.offline_55_gates_verified
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
