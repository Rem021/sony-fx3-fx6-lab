"""Phase 153 — Real-Hardware Main Track Part 11:
Gate G47 (Dual-Layer `pnflasha/cnflasha` SPACC Cipher-Pairing, Per-Camera `CID`
OTP Binding & `/dev/mtd0ro` SPI-NOR Read-Only Guard), Gate G48 (`p12/p13` RF
Regulatory NVS Firewall, `USB MSC 054C:0DA1` Preservation, `Off-in-Rec` `>=65°C`
`100% PWM` Thermal Override & `<=6100 mV` `EncWfiStop` Guard), and Unified
48-Gate Master Safety Preflight (`G01..G48` / `verify-48-gates`).

Operationalizes the Phase 149–152 physical ILME-FX3 (`Ver. 7.02`, Model ID
`0x91030080`, SoC `CXD90057`) eMMC `pnflasha*` vs `cnflasha*` SPACC cipher
boundary, `/dev/mtd0ro` SPI-NOR boot flash immutability, `p12/p13` RF/MAC NVS
firewall, `Off in Rec` cooling fan `65°C` `100% PWM` override, and `NP-FZ100`
`6100 mV` graceful `EncWfiStop` invariants while keeping all prior gate modules
(`G01..G46`) 100% untouched and hard-locking:
- `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`
- `PERSISTENT_WRITE_RELEASE = False`
- `SPI_NOR_WRITE_AUTHORIZED = False`
- `overall_ready_for_hardware_attach = False`

1. **Dual-Mode Donor Inspection (`os.O_RDONLY`) + Clean-Room Fallback (`FX3_FX6_FORCE_CLEAN_ROOM=1`)**:
   - Inspects FX3 `7.02` `libsencore.so` (`377,328 B`), `libmpr.so` (`3,517,008 B`),
     `im.elf` (`40,920 B`), `cpapp-b.bin` (`15,980,568 B`), and `Backup.bin`
     (`2,229,740 B`, `BK4\\0`) strictly via `os.open(..., os.O_RDONLY)` when present
     and `FX3_FX6_FORCE_CLEAN_ROOM != "1"`.
   - Falls back deterministically to pinned clean-room metadata when
     `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor files are absent, leaking zero raw
     Sony firmware bytes in JSON output.

2. **Gate G47 — Dual-Layer `pnflasha/cnflasha` Cipher-Pairing, Per-Camera `CID`
   Binding & `/dev/mtd0ro` SPI-NOR Guard**:
   - Hard-blocks cross-domain restore (`SPACC_CNFLASHA_LOGICAL` onto
     `RAW_PNFLASHA_ISP` or vice versa).
   - Hard-blocks restoring `RAW_PNFLASHA_ISP` (or cross-body) ciphertext onto a
     mismatched `camera_cid_sha256` (OTP key mismatch).
   - Hard-blocks `/dev/mtd*` non-`ro` device nodes, write open modes, or
     `MEMERASE` / `MEMWRITEOOB` ioctls (`spi_nor_write_authorized == False`).

3. **Gate G48 — `p12/p13` RF Regulatory NVS Lock, `USB MSC 054C:0DA1`
   Preservation, `Off-in-Rec` `>=65°C` `100% PWM` Thermal Override &
   `<=6100 mV` `EncWfiStop` Guard**:
   - Hard-blocks `p12/p13` RF/MAC NVS mutation (`rf_nvs_mutation_bytes == 0`).
   - Verifies `USB MSC 054C:0DA1` recovery mode remains reachable.
   - Enforces `cpapp-b.bin` `SET_FAN_EQ_ID` thermal override (`>=58°C -> >=45% PWM`,
     `>=65°C -> 100% PWM`, `>=72°C -> EncWfiStop`, rejecting `ALWAYS_OFF`).
   - Enforces `NP-FZ100` `<=6100 mV` (`2%`) graceful `EncWfiStop` with zero
     false `19.5V DC-IN` alarms.

4. **Unified 48-Gate Master Safety Preflight (`evaluate_48gate_preflight` / CLI
   `verify-48-gates`)**:
   - Offline default reports `45/48` (`G10..G12` physical Tier-0 gates `False`,
     `persistent_emmc_writes_authorized = False`,
     `overall_ready_for_hardware_attach = False`).
   - `--dry-run-simulated-backup` reports `48/48` dry-run green while STILL
     keeping `persistent_emmc_writes_authorized = False`,
     `persistent_write_release = False`, `spi_nor_write_authorized = False`,
     and `overall_ready_for_hardware_attach = False`.
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
from .realhw_service0336_mpr_ibis_and_46gate_guard import (
    Master46GateReport,
    evaluate_46gate_preflight,
)
from .thermal_pwm_and_power_guard import (
    ENV_FORCE_CLEAN_ROOM,
    resolve_donor_thermal_power_paths,
)


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

REALHW_PNFLASHA_MTDRO_RFNVS_48GATE_SCHEMA: str = (
    "fx3-realhw-pnflasha-mtdro-rfnvs-48gate-preflight-v1"
)
REALHW_PNFLASHA_MTDRO_RFNVS_48GATE_VERSION: str = "1.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False
SPI_NOR_WRITE_AUTHORIZED: bool = False

# Gate IDs & Canonical Codes for G47..G48
G47_GATE_ID: str = "G47_pnflasha_cnflasha_cid_pairing_and_mtd0ro_guard"
G47_GATE_CODE: str = "PNFLASHA_CNFLASHA_CID_PAIRING_AND_MTD0RO_GUARD"

G48_GATE_ID: str = (
    "G48_rfnvs_p12_p13_msc_0da1_fan_65c_override_and_6100mv_encwfistop_safe"
)
G48_GATE_CODE: str = (
    "RFNVS_P12_P13_MSC_0DA1_FAN_65C_OVERRIDE_AND_6100MV_ENCWFISTOP_SAFE"
)

# Status Codes
STATUS_SAFE: str = "SAFE"
STATUS_VERIFIED_SAFE: str = "VERIFIED_SAFE"
STATUS_VERIFIED_G47: str = (
    "VERIFIED_PNFLASHA_CNFLASHA_CID_PAIRING_AND_MTD0RO_GUARD"
)
STATUS_VERIFIED_G48: str = (
    "VERIFIED_RFNVS_P12_P13_MSC_0DA1_FAN_65C_OVERRIDE_AND_6100MV_ENCWFISTOP_SAFE"
)

# Gate G47 Violation Codes
STATUS_BLOCKED_G47_CROSS_DOMAIN_CIPHER_MISMATCH: str = (
    "BLOCKED_G47_CROSS_DOMAIN_CIPHER_MISMATCH"
)
STATUS_BLOCKED_G47_CAMERA_CID_OTP_KEY_MISMATCH: str = (
    "BLOCKED_G47_CAMERA_CID_OTP_KEY_MISMATCH"
)
STATUS_BLOCKED_G47_MTD_NON_RO_OR_IOCTL_WRITE: str = (
    "BLOCKED_G47_MTD_NON_RO_OR_IOCTL_WRITE"
)
STATUS_BLOCKED_G47_TELEMETRY_INVALID: str = (
    "BLOCKED_G47_PNFLASHA_MTDRO_TELEMETRY_INVALID"
)

# Gate G48 Violation Codes
STATUS_BLOCKED_G48_RF_NVS_OR_MAC_MUTATION: str = (
    "BLOCKED_G48_RF_NVS_OR_MAC_MUTATION"
)
STATUS_BLOCKED_G48_USB_MSC_0DA1_UNREACHABLE: str = (
    "BLOCKED_G48_USB_MSC_0DA1_UNREACHABLE"
)
STATUS_BLOCKED_G48_FAN_THERMAL_OVERRIDE_VIOLATION: str = (
    "BLOCKED_G48_FAN_THERMAL_OVERRIDE_VIOLATION"
)
STATUS_BLOCKED_G48_BATT_6100MV_OR_FALSE_DCIN_ALARM: str = (
    "BLOCKED_G48_BATT_6100MV_OR_FALSE_DCIN_ALARM"
)
STATUS_BLOCKED_G48_TELEMETRY_INVALID: str = (
    "BLOCKED_G48_RFNVS_FAN_POWER_TELEMETRY_INVALID"
)

STATUS_BLOCKED_DONOR_INTEGRITY: str = (
    "BLOCKED_PHASE153_48GATE_DONOR_INTEGRITY_MISMATCH"
)
STATUS_BLOCKED_PERSISTENT_EMMC_WRITE: str = (
    "BLOCKED_BY_PERSISTENT_EMMC_WRITE_REDLINE"
)

# Gate G47 Thresholds & Protocol Constants
CIPHER_DOMAIN_RAW_PNFLASHA_ISP: str = "RAW_PNFLASHA_ISP"
CIPHER_DOMAIN_SPACC_CNFLASHA_LOGICAL: str = "SPACC_CNFLASHA_LOGICAL"
VALID_CIPHER_DOMAINS: Tuple[str, ...] = (
    CIPHER_DOMAIN_RAW_PNFLASHA_ISP,
    CIPHER_DOMAIN_SPACC_CNFLASHA_LOGICAL,
)
DEFAULT_SYNTHETIC_CAMERA_CID_SHA256: str = "a" * 64
CANONICAL_MTD_RO_NODE: str = "/dev/mtd0ro"
FORBIDDEN_MTD_IOCTLS: Tuple[str, ...] = (
    "MEMERASE",
    "MEMERASE64",
    "MEMWRITEOOB",
    "MEMWRITEOOB64",
    "MEMWRITE",
    "MEMLOCK",
    "MEMUNLOCK",
    "OTPSELECT",
    "OTPLOCK",
)
ALLOWED_MTD_RO_IOCTLS: Tuple[str, ...] = (
    "MEMGETINFO",
    "MEMGETREGIONCOUNT",
    "MEMGETREGIONINFO",
    "MEMGETOOBSEL",
    "ECCGETLAYOUT",
    "ECCGETSTATS",
)

# Gate G48 Thresholds & Protocol Constants
RF_NVS_PARTITIONS: Tuple[str, ...] = ("p12", "p13")
RF_NVS_REQUIRED_MOUNT_FLAG: str = "MS_RDONLY"
USB_MSC_RECOVERY_VID_PID: str = "054C:0DA1"
FAN_SET_FAN_EQ_ID_CMD: str = "SET_FAN_EQ_ID"
FAN_MODE_OFF_IN_REC: str = "OFF_IN_REC"
FAN_MODE_AUTO1: str = "AUTO1"
FAN_MODE_AUTO2: str = "AUTO2"
FAN_MODE_MINIMUM: str = "MINIMUM"
FAN_MODE_ALWAYS_OFF: str = "ALWAYS_OFF"
SAFE_REALHW_FAN_MODES: Tuple[str, ...] = (
    FAN_MODE_OFF_IN_REC,
    FAN_MODE_AUTO1,
    FAN_MODE_AUTO2,
    FAN_MODE_MINIMUM,
)
FAN_OVERRIDE_WARM_TEMP_C: float = 58.0
FAN_OVERRIDE_WARM_MIN_PWM_PCT: float = 45.0
FAN_OVERRIDE_FULL_TEMP_C: float = 65.0
FAN_OVERRIDE_FULL_PWM_PCT: float = 100.0
FAN_THERMAL_ENCWFISTOP_TEMP_C: float = 72.0
NPFZ100_NEAR_END_MV: float = 6350.0
NPFZ100_NEAR_END_SOC_PCT: float = 5.0
NPFZ100_ENCWFISTOP_MV: float = 6100.0
NPFZ100_ENCWFISTOP_SOC_PCT: float = 2.0
FORBIDDEN_FALSE_DCIN_ALARM_VOLTAGES_V: Tuple[float, ...] = (18.0, 19.5)

_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_MTD_RO_NODE_RE = re.compile(r"^/dev/mtd\d+ro$")

# Pinned FX3 v7.02 Donor Specs (verified strictly via os.O_RDONLY)
PINNED_PHASE153_DONOR_SPECS: Mapping[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_libsencore": (
        "fx3",
        "sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/libsencore.so",
        377_328,
        "a2907111c4a22314dcb12c25889e0e3142764c6a4a910a746e43908f76e7c410",
        (
            b"AdjustControlFunc",
            b"SenserIfStart",
            b"SenserPacket",
            b"FAN_SET_SPEED",
            b"CXS_WRITE_PWM",
            b"GET_TEMPERATURE",
            b"USB_BUSPOWER_SUPPLY_CONTROL",
        ),
        "fx3/libsencore.so::{AdjustControlFunc,FAN_SET_SPEED,CXS_WRITE_PWM,GET_TEMPERATURE,USB_BUSPOWER_SUPPLY_CONTROL}",
    ),
    "fx3_libmpr": (
        "fx3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libmpr.so",
        3_517_008,
        "9aeef3b9edb3d011c0c90cd2387b3a47bd3b506ebfa57be39ad1a9729771b57c",
        (
            b"DmmMemInfo",
            b"GetUnitInfo",
            b"EncWfiStop",
            b"EncWfiStopReserve",
            b"ExecEncStart",
        ),
        "fx3/libmpr.so::{DmmMemInfo,GetUnitInfo,EncWfiStop,EncWfiStopReserve,ExecEncStart}",
    ),
    "fx3_im_elf": (
        "fx3",
        "fx3-vm-20261101/fx3-audit/original-members/nflasha15/bin/im.elf",
        40_920,
        "5171f576d8b76cfbf15581389183b390c445bd6ff9dd97fd6668c5f64e77dc91",
        (
            b"\x7fELF",
            b"libIMDB.so",
            b"libbackup.so",
            b"libosal_uipc.so",
        ),
        "fx3/im.elf::{40920B,ELF,libIMDB.so,libbackup.so,libosal_uipc.so}",
    ),
    "fx3_cpapp_b": (
        "fx3",
        "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin",
        15_980_568,
        "c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba",
        (
            b"SET_FAN_EQ_ID",
            b"PROC_MSG_SET_FAN_EQ_ID:",
            b"FAN_R",
            b"PWM",
            b"THERM",
            b"BATT_AUTH_Snd",
            b"ACV_BATT_Snd",
            b"LiroSeq",
        ),
        "fx3/cpapp-b.bin::{SET_FAN_EQ_ID,PROC_MSG_SET_FAN_EQ_ID:,FAN_R,PWM,THERM,BATT_AUTH_Snd,ACV_BATT_Snd}",
    ),
    "fx3_backup_bin": (
        "fx3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin",
        2_229_740,
        "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2",
        (b"BK4\x00",),
        "fx3/Backup.bin::{2229740B,BK4\\0}",
    ),
}


# ---------------------------------------------------------------------------
# Data Models (Zero raw bytes reprs; hex strings / ASCII markers only)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase153DonorAuditResult:
    valid: bool
    status: str
    verification_mode: str
    access_mode: str
    files_inspected: int
    checked_markers: Tuple[str, ...]
    missing_markers: Tuple[str, ...]
    sencore_mpr_contracts_verified: bool
    im_elf_contracts_verified: bool
    cpapp_backup_contracts_verified: bool
    sha256_by_artifact: Dict[str, str]
    bytes_by_artifact: Dict[str, int]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PnflashaMtdroVaultGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    vault_profile: str
    backup_cipher_domain: str
    restore_target_domain: str
    source_block_device: str
    target_block_device: str
    backup_camera_cid_sha256: str
    target_camera_cid_sha256: str
    cid_otp_key_binding_verified: bool
    mtd_device_node: str
    mtd_open_mode: str
    requested_mtd_ioctls: Tuple[str, ...]
    forbidden_mtd_ioctls_detected: Tuple[str, ...]
    spi_nor_write_attempts_blocked: bool
    spi_nor_mutation_bytes: int
    spi_nor_write_authorized: bool
    cipher_pairing_safe: bool
    camera_cid_binding_safe: bool
    mtd_readonly_guard_safe: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RfnvsMscFanPowerGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    guard_profile: str
    p12_device_node: str
    p13_device_node: str
    p12_mount_flags: str
    p13_mount_flags: str
    rf_nvs_write_attempts_blocked: bool
    rf_nvs_mutation_bytes: int
    rf_nvs_writes_requested: int
    mac_address_override_attempted: bool
    regdomain_override_attempted: bool
    usb_msc_recovery_vid_pid: str
    usb_msc_0da1_reachable: bool
    usb_phy_disabled_or_masked: bool
    usb_descriptor_spoofed: bool
    fan_mode: str
    set_fan_eq_id_cmd: str
    sensor_temp_c: float
    fan_pwm_pct: float
    expected_min_pwm_pct: float
    stock_cp_thermal_override_masked: bool
    thermal_encwfistop_triggered: bool
    battery_mv: float
    battery_soc_pct: float
    usb_pd_attached: bool
    batt_encwfistop_triggered: bool
    batt_power_state: str
    false_19v5_dcin_alarms: int
    dcin_18v_19v5_comparator_masked: bool
    rsv_orphan_risk: bool
    rf_nvs_lock_safe: bool
    usb_msc_0da1_safe: bool
    fan_thermal_override_safe: bool
    battery_6100mv_encwfistop_safe: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G47PnflashaMtdroVaultResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    pnflasha_mtdro_guard: Dict[str, Any]
    spi_nor_write_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G48RfnvsFanPowerGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    rfnvs_fan_power_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master48GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    offline_45_gates_verified: bool
    all_48_gates_verified: bool
    g13_to_g48_all_passed: bool
    g47_to_g48_all_passed: bool
    h0_h1_trial_entry_allowed: bool
    status: str
    spi_nor_write_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    summary: Dict[str, Any]
    gates: Tuple[Dict[str, Any], ...]
    master_46_report: Dict[str, Any]
    g47_result: Dict[str, Any]
    g48_result: Dict[str, Any]
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


# ---------------------------------------------------------------------------
# 1. Strictly Read-Only (O_RDONLY) Donor Contract Audit
# ---------------------------------------------------------------------------


def audit_phase153_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
) -> Phase153DonorAuditResult:
    """Inspect FX3 `libsencore.so`, `libmpr.so`, `im.elf`, `cpapp-b.bin`, and
    `Backup.bin` strictly via `os.O_RDONLY` with deterministic clean-room fallback.
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
        ) in PINNED_PHASE153_DONOR_SPECS.items():
            resolved[key] = effective_work_root / rel_path

    donor_available = (
        (not clean_forced)
        and (effective_work_root is not None)
        and bool(resolved)
        and all(p.is_file() for p in resolved.values())
    )

    if not donor_available:
        return Phase153DonorAuditResult(
            valid=True,
            status=STATUS_VERIFIED_SAFE,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="O_RDONLY",
            files_inspected=0,
            checked_markers=tuple(
                spec[5] for spec in PINNED_PHASE153_DONOR_SPECS.values()
            ),
            missing_markers=(),
            sencore_mpr_contracts_verified=True,
            im_elf_contracts_verified=True,
            cpapp_backup_contracts_verified=True,
            sha256_by_artifact={
                k: spec[3] for k, spec in PINNED_PHASE153_DONOR_SPECS.items()
            },
            bytes_by_artifact={
                k: spec[2] for k, spec in PINNED_PHASE153_DONOR_SPECS.items()
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

    for key, (
        _body,
        _rel_name,
        exp_size,
        exp_sha,
        marker_tuple,
        marker_label,
    ) in PINNED_PHASE153_DONOR_SPECS.items():
        blob = _read_file_o_rdonly(resolved[key])
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

    valid = len(errors) == 0 and len(missing) == 0
    return Phase153DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_DONOR_INTEGRITY,
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="O_RDONLY",
        files_inspected=len(resolved),
        checked_markers=tuple(checked),
        missing_markers=tuple(missing),
        sencore_mpr_contracts_verified={
            "fx3_libsencore",
            "fx3_libmpr",
        }.issubset(passed_keys),
        im_elf_contracts_verified={"fx3_im_elf"}.issubset(passed_keys),
        cpapp_backup_contracts_verified={
            "fx3_cpapp_b",
            "fx3_backup_bin",
        }.issubset(passed_keys),
        sha256_by_artifact=shas,
        bytes_by_artifact=sizes,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 2. Pure Helper Functions
# ---------------------------------------------------------------------------


def validate_dual_layer_cipher_pairing(
    backup_cipher_domain: str,
    restore_target_domain: str,
    source_block_device: str = "/dev/cnflasha15",
    target_block_device: str = "/dev/cnflasha15",
) -> bool:
    """Validate strict same-domain SPACC vs raw-ISP cipher pairing and block device match."""
    if not (
        isinstance(backup_cipher_domain, str)
        and isinstance(restore_target_domain, str)
        and isinstance(source_block_device, str)
        and isinstance(target_block_device, str)
    ):
        return False

    b_dom = backup_cipher_domain.strip().upper()
    t_dom = restore_target_domain.strip().upper()
    src_dev = source_block_device.strip().lower()
    dst_dev = target_block_device.strip().lower()

    if b_dom not in VALID_CIPHER_DOMAINS or t_dom not in VALID_CIPHER_DOMAINS:
        return False
    if b_dom != t_dom:
        return False

    if b_dom == CIPHER_DOMAIN_RAW_PNFLASHA_ISP:
        return src_dev.startswith("/dev/pnflasha") and dst_dev.startswith(
            "/dev/pnflasha"
        )
    # CIPHER_DOMAIN_SPACC_CNFLASHA_LOGICAL
    return src_dev.startswith("/dev/cnflasha") and dst_dev.startswith(
        "/dev/cnflasha"
    )


def validate_camera_cid_binding(
    backup_camera_cid_sha256: str,
    target_camera_cid_sha256: str,
) -> bool:
    """Validate per-camera eMMC CID SHA-256 OTP key binding match."""
    if not (
        isinstance(backup_camera_cid_sha256, str)
        and isinstance(target_camera_cid_sha256, str)
    ):
        return False
    b_cid = backup_camera_cid_sha256.strip().lower()
    t_cid = target_camera_cid_sha256.strip().lower()
    if not (_HEX64_RE.match(b_cid) and _HEX64_RE.match(t_cid)):
        return False
    return b_cid == t_cid


def validate_mtd_readonly_guard(
    mtd_device_node: str,
    mtd_open_mode: str = "O_RDONLY",
    requested_mtd_ioctls: Sequence[str] = (),
) -> bool:
    """Enforce strictly `/dev/mtd*ro`, `O_RDONLY`, and zero write/erase MTD ioctls."""
    if not (isinstance(mtd_device_node, str) and isinstance(mtd_open_mode, str)):
        return False
    if isinstance(requested_mtd_ioctls, (str, bytes)) or not isinstance(
        requested_mtd_ioctls, Sequence
    ):
        return False
    dev = mtd_device_node.strip()
    mode = mtd_open_mode.strip().upper()
    if not _MTD_RO_NODE_RE.match(dev):
        return False
    if mode != "O_RDONLY":
        return False
    for ioctl_name in requested_mtd_ioctls:
        if not isinstance(ioctl_name, str):
            return False
        norm = ioctl_name.strip().upper()
        if norm in FORBIDDEN_MTD_IOCTLS or (norm and norm not in ALLOWED_MTD_RO_IOCTLS):
            return False
    return True


def compute_cpapp_fan_override_pwm_pct(
    fan_mode: str,
    sensor_temp_c: float,
) -> Tuple[float, bool]:
    """Compute required `cpapp-b.bin` `SET_FAN_EQ_ID` PWM duty % and `EncWfiStop` flag.

    Returns `(min_required_pwm_pct, enc_wfi_stop_required)`.
    Raises `ValueError` on `ALWAYS_OFF` or invalid telemetry.
    """
    if not isinstance(fan_mode, str) or not _is_finite_number(sensor_temp_c):
        raise ValueError("fan_mode must be str and sensor_temp_c must be finite float.")
    mode = fan_mode.strip().upper()
    if mode == FAN_MODE_ALWAYS_OFF or mode not in SAFE_REALHW_FAN_MODES:
        raise ValueError(f"Unsupported or forbidden fan_mode: {fan_mode!r}")

    temp = float(sensor_temp_c)
    if temp >= FAN_THERMAL_ENCWFISTOP_TEMP_C:
        return (FAN_OVERRIDE_FULL_PWM_PCT, True)
    if temp >= FAN_OVERRIDE_FULL_TEMP_C:
        return (FAN_OVERRIDE_FULL_PWM_PCT, False)
    if temp >= FAN_OVERRIDE_WARM_TEMP_C:
        return (FAN_OVERRIDE_WARM_MIN_PWM_PCT, False)
    if mode == FAN_MODE_OFF_IN_REC:
        return (0.0, False)
    return (25.0, False)


def evaluate_npfz100_6100mv_encwfistop(
    battery_mv: float,
    battery_soc_pct: float,
    *,
    usb_pd_attached: bool = False,
) -> str:
    """Classify `NP-FZ100` (`7.2V`) state into `NOMINAL`, `NEAR_END`, or `ENC_WFI_STOP`."""
    if not (_is_finite_number(battery_mv) and _is_finite_number(battery_soc_pct)):
        raise ValueError("battery_mv and battery_soc_pct must be finite numbers.")
    mv = float(battery_mv)
    soc = float(battery_soc_pct)
    if mv <= 0.0 or soc < 0.0 or soc > 100.0:
        raise ValueError("battery_mv must be > 0 and battery_soc_pct in [0, 100].")
    if usb_pd_attached:
        return "USB_PD_ASSISTED"
    if mv <= NPFZ100_ENCWFISTOP_MV or soc <= NPFZ100_ENCWFISTOP_SOC_PCT:
        return "ENC_WFI_STOP"
    if mv <= NPFZ100_NEAR_END_MV or soc <= NPFZ100_NEAR_END_SOC_PCT:
        return "NEAR_END"
    return "NOMINAL"


# ---------------------------------------------------------------------------
# 3. Gate G47 — Dual-Layer pnflasha/cnflasha Cipher-Pairing, CID & /dev/mtd0ro
# ---------------------------------------------------------------------------


def verify_pnflasha_cnflasha_cid_and_mtdro_guard(
    *,
    vault_profile: str = "FX3_REALHW_SPACC_CNFLASHA_CID_AND_MTD0RO_VAULT",
    backup_cipher_domain: str = CIPHER_DOMAIN_SPACC_CNFLASHA_LOGICAL,
    restore_target_domain: str = CIPHER_DOMAIN_SPACC_CNFLASHA_LOGICAL,
    source_block_device: str = "/dev/cnflasha15",
    target_block_device: str = "/dev/cnflasha15",
    backup_camera_cid_sha256: str = DEFAULT_SYNTHETIC_CAMERA_CID_SHA256,
    target_camera_cid_sha256: str = DEFAULT_SYNTHETIC_CAMERA_CID_SHA256,
    cid_otp_key_binding_verified: bool = True,
    mtd_device_node: str = CANONICAL_MTD_RO_NODE,
    mtd_open_mode: str = "O_RDONLY",
    requested_mtd_ioctls: Sequence[str] = ("MEMGETINFO",),
    spi_nor_write_attempts_blocked: bool = True,
    spi_nor_mutation_bytes: int = 0,
    request_spi_nor_writes: bool = False,
    request_persistent_emmc_writes: bool = False,
) -> PnflashaMtdroVaultGuardResult:
    """Verify Gate G47 (Dual-layer `pnflasha/cnflasha` cipher-pairing, per-camera
    `CID` OTP binding, and `/dev/mtd0ro` SPI-NOR read-only guard).
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append(
            "Persistent eMMC writes are hard-locked False (PERSISTENT_EMMC_WRITES_AUTHORIZED=False)."
        )

    telemetry_ok = True
    if not isinstance(backup_cipher_domain, str) or not backup_cipher_domain.strip():
        _add_code(codes, STATUS_BLOCKED_G47_TELEMETRY_INVALID)
        errors.append("backup_cipher_domain must be non-empty string.")
        telemetry_ok = False
        eff_b_dom = CIPHER_DOMAIN_SPACC_CNFLASHA_LOGICAL
    else:
        eff_b_dom = backup_cipher_domain.strip().upper()

    if not isinstance(restore_target_domain, str) or not restore_target_domain.strip():
        _add_code(codes, STATUS_BLOCKED_G47_TELEMETRY_INVALID)
        errors.append("restore_target_domain must be non-empty string.")
        telemetry_ok = False
        eff_t_dom = CIPHER_DOMAIN_SPACC_CNFLASHA_LOGICAL
    else:
        eff_t_dom = restore_target_domain.strip().upper()

    if not isinstance(source_block_device, str) or not source_block_device.strip():
        _add_code(codes, STATUS_BLOCKED_G47_TELEMETRY_INVALID)
        errors.append("source_block_device must be non-empty string.")
        telemetry_ok = False
        eff_src_dev = "/dev/cnflasha15"
    else:
        eff_src_dev = source_block_device.strip()

    if not isinstance(target_block_device, str) or not target_block_device.strip():
        _add_code(codes, STATUS_BLOCKED_G47_TELEMETRY_INVALID)
        errors.append("target_block_device must be non-empty string.")
        telemetry_ok = False
        eff_dst_dev = "/dev/cnflasha15"
    else:
        eff_dst_dev = target_block_device.strip()

    if not isinstance(backup_camera_cid_sha256, str) or not _HEX64_RE.match(
        backup_camera_cid_sha256.strip().lower()
    ):
        _add_code(codes, STATUS_BLOCKED_G47_TELEMETRY_INVALID)
        errors.append("backup_camera_cid_sha256 must be 64-char lowercase hex SHA-256.")
        telemetry_ok = False
        eff_b_cid = DEFAULT_SYNTHETIC_CAMERA_CID_SHA256
    else:
        eff_b_cid = backup_camera_cid_sha256.strip().lower()

    if not isinstance(target_camera_cid_sha256, str) or not _HEX64_RE.match(
        target_camera_cid_sha256.strip().lower()
    ):
        _add_code(codes, STATUS_BLOCKED_G47_TELEMETRY_INVALID)
        errors.append("target_camera_cid_sha256 must be 64-char lowercase hex SHA-256.")
        telemetry_ok = False
        eff_t_cid = DEFAULT_SYNTHETIC_CAMERA_CID_SHA256
    else:
        eff_t_cid = target_camera_cid_sha256.strip().lower()

    if not isinstance(mtd_device_node, str) or not mtd_device_node.strip():
        _add_code(codes, STATUS_BLOCKED_G47_TELEMETRY_INVALID)
        errors.append("mtd_device_node must be non-empty string.")
        telemetry_ok = False
        eff_mtd_dev = CANONICAL_MTD_RO_NODE
    else:
        eff_mtd_dev = mtd_device_node.strip()

    if not isinstance(mtd_open_mode, str) or not mtd_open_mode.strip():
        _add_code(codes, STATUS_BLOCKED_G47_TELEMETRY_INVALID)
        errors.append("mtd_open_mode must be non-empty string.")
        telemetry_ok = False
        eff_mtd_mode = "O_RDONLY"
    else:
        eff_mtd_mode = mtd_open_mode.strip().upper()

    if (
        isinstance(requested_mtd_ioctls, (str, bytes))
        or not isinstance(requested_mtd_ioctls, Sequence)
        or not all(isinstance(x, str) for x in requested_mtd_ioctls)
    ):
        _add_code(codes, STATUS_BLOCKED_G47_TELEMETRY_INVALID)
        errors.append("requested_mtd_ioctls must be a sequence of ioctl strings.")
        telemetry_ok = False
        eff_ioctls: Tuple[str, ...] = ()
    else:
        eff_ioctls = tuple(x.strip().upper() for x in requested_mtd_ioctls if x.strip())

    if not _is_non_negative_int(spi_nor_mutation_bytes):
        _add_code(codes, STATUS_BLOCKED_G47_TELEMETRY_INVALID)
        errors.append("spi_nor_mutation_bytes must be non-negative int.")
        telemetry_ok = False
        eff_spi_mut = 0
    else:
        eff_spi_mut = int(spi_nor_mutation_bytes)

    # 1) Dual-layer pnflasha vs cnflasha SPACC cipher-domain pairing
    pairing_ok = validate_dual_layer_cipher_pairing(
        eff_b_dom,
        eff_t_dom,
        eff_src_dev,
        eff_dst_dev,
    )
    cipher_pairing_safe = (not telemetry_ok) or pairing_ok
    if telemetry_ok and not pairing_ok:
        _add_code(codes, STATUS_BLOCKED_G47_CROSS_DOMAIN_CIPHER_MISMATCH)
        errors.append(
            f"BLOCKED_G47_CROSS_DOMAIN_CIPHER_MISMATCH: {vault_profile} forbids cross-domain "
            f"backup={eff_b_dom!r} ({eff_src_dev}) -> target={eff_t_dom!r} ({eff_dst_dev})."
        )

    # 2) Per-camera eMMC CID OTP key binding (RAW_PNFLASHA_ISP & same-body invariant)
    cid_match_ok = validate_camera_cid_binding(eff_b_cid, eff_t_cid) and bool(
        cid_otp_key_binding_verified
    )
    camera_cid_binding_safe = (not telemetry_ok) or cid_match_ok
    if telemetry_ok and not cid_match_ok:
        _add_code(codes, STATUS_BLOCKED_G47_CAMERA_CID_OTP_KEY_MISMATCH)
        errors.append(
            f"BLOCKED_G47_CAMERA_CID_OTP_KEY_MISMATCH: backup_cid={eff_b_cid[:12]}... != "
            f"target_cid={eff_t_cid[:12]}... (otp_verified={bool(cid_otp_key_binding_verified)}); "
            f"cross-body RAW_PNFLASHA_ISP ciphertext restore would fail OTP decryption."
        )

    # 3) /dev/mtd0ro SPI-NOR Read-Only Guard & zero MEMERASE/MEMWRITEOOB ioctls
    forbidden_ioctls = tuple(
        x
        for x in eff_ioctls
        if x in FORBIDDEN_MTD_IOCTLS or x not in ALLOWED_MTD_RO_IOCTLS
    )
    mtd_guard_ok = (
        validate_mtd_readonly_guard(eff_mtd_dev, eff_mtd_mode, eff_ioctls)
        and bool(spi_nor_write_attempts_blocked)
        and eff_spi_mut == 0
        and (not bool(request_spi_nor_writes))
        and (not SPI_NOR_WRITE_AUTHORIZED)
    )
    mtd_readonly_guard_safe = (not telemetry_ok) or mtd_guard_ok
    if telemetry_ok and not mtd_guard_ok:
        _add_code(codes, STATUS_BLOCKED_G47_MTD_NON_RO_OR_IOCTL_WRITE)
        errors.append(
            f"BLOCKED_G47_MTD_NON_RO_OR_IOCTL_WRITE: mtd={eff_mtd_dev!r} mode={eff_mtd_mode!r}, "
            f"forbidden_ioctls={forbidden_ioctls}, blocked={bool(spi_nor_write_attempts_blocked)}, "
            f"mutation_bytes={eff_spi_mut}, request_spi_nor_writes={bool(request_spi_nor_writes)}, "
            f"spi_nor_write_authorized={SPI_NOR_WRITE_AUTHORIZED}."
        )

    if telemetry_ok and len(errors) == 0 and eff_b_dom == CIPHER_DOMAIN_RAW_PNFLASHA_ISP:
        warnings.append(
            "RAW_PNFLASHA_ISP domain selected: valid ONLY for identical camera_cid_sha256 "
            "cold-vault restore; never use for logical file extraction."
        )

    valid = len(errors) == 0 and len(codes) == 0
    if valid:
        status = STATUS_SAFE
    elif STATUS_BLOCKED_PERSISTENT_EMMC_WRITE in codes:
        status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    else:
        status = codes[0]

    return PnflashaMtdroVaultGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        vault_profile=str(vault_profile),
        backup_cipher_domain=eff_b_dom,
        restore_target_domain=eff_t_dom,
        source_block_device=eff_src_dev,
        target_block_device=eff_dst_dev,
        backup_camera_cid_sha256=eff_b_cid,
        target_camera_cid_sha256=eff_t_cid,
        cid_otp_key_binding_verified=bool(cid_otp_key_binding_verified),
        mtd_device_node=eff_mtd_dev,
        mtd_open_mode=eff_mtd_mode,
        requested_mtd_ioctls=eff_ioctls,
        forbidden_mtd_ioctls_detected=forbidden_ioctls,
        spi_nor_write_attempts_blocked=bool(spi_nor_write_attempts_blocked),
        spi_nor_mutation_bytes=eff_spi_mut,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        cipher_pairing_safe=cipher_pairing_safe,
        camera_cid_binding_safe=camera_cid_binding_safe,
        mtd_readonly_guard_safe=mtd_readonly_guard_safe,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 4. Gate G48 — p12/p13 RF NVS Firewall, USB MSC 054C:0DA1, Fan >=65°C & 6100mV
# ---------------------------------------------------------------------------


def verify_rfnvs_msc_fan_override_and_power_guard(
    *,
    guard_profile: str = "FX3_REALHW_RFNVS_MSC_0DA1_FAN_65C_AND_6100MV_GUARD",
    p12_device_node: str = "/dev/nflasha12",
    p13_device_node: str = "/dev/nflasha13",
    p12_mount_flags: str = RF_NVS_REQUIRED_MOUNT_FLAG,
    p13_mount_flags: str = RF_NVS_REQUIRED_MOUNT_FLAG,
    rf_nvs_write_attempts_blocked: bool = True,
    rf_nvs_mutation_bytes: int = 0,
    rf_nvs_writes_requested: int = 0,
    mac_address_override_attempted: bool = False,
    regdomain_override_attempted: bool = False,
    usb_msc_recovery_vid_pid: str = USB_MSC_RECOVERY_VID_PID,
    usb_msc_0da1_reachable: bool = True,
    usb_phy_disabled_or_masked: bool = False,
    usb_descriptor_spoofed: bool = False,
    fan_mode: str = FAN_MODE_OFF_IN_REC,
    set_fan_eq_id_cmd: str = FAN_SET_FAN_EQ_ID_CMD,
    sensor_temp_c: float = 65.0,
    fan_pwm_pct: float = 100.0,
    stock_cp_thermal_override_masked: bool = False,
    thermal_encwfistop_triggered: bool = False,
    battery_mv: float = 7600.0,
    battery_soc_pct: float = 85.0,
    usb_pd_attached: bool = False,
    batt_encwfistop_triggered: bool = False,
    false_19v5_dcin_alarms: int = 0,
    dcin_18v_19v5_comparator_masked: bool = True,
    rsv_orphan_risk: bool = False,
    request_persistent_emmc_writes: bool = False,
) -> RfnvsMscFanPowerGuardResult:
    """Verify Gate G48 (`p12/p13` RF NVS firewall, `USB MSC 054C:0DA1` reachability,
    `Off-in-Rec` `>=65°C` `100% PWM` override, and `NP-FZ100` `<=6100 mV` `EncWfiStop`).
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append(
            "Persistent eMMC writes are hard-locked False (PERSISTENT_EMMC_WRITES_AUTHORIZED=False)."
        )

    telemetry_ok = True
    for lbl, val in (
        ("p12_device_node", p12_device_node),
        ("p13_device_node", p13_device_node),
        ("p12_mount_flags", p12_mount_flags),
        ("p13_mount_flags", p13_mount_flags),
        ("usb_msc_recovery_vid_pid", usb_msc_recovery_vid_pid),
        ("fan_mode", fan_mode),
        ("set_fan_eq_id_cmd", set_fan_eq_id_cmd),
    ):
        if not isinstance(val, str) or not val.strip():
            _add_code(codes, STATUS_BLOCKED_G48_TELEMETRY_INVALID)
            errors.append(f"{lbl} must be non-empty string.")
            telemetry_ok = False

    eff_p12_dev = p12_device_node.strip() if isinstance(p12_device_node, str) else ""
    eff_p13_dev = p13_device_node.strip() if isinstance(p13_device_node, str) else ""
    eff_p12_flags = p12_mount_flags.strip() if isinstance(p12_mount_flags, str) else ""
    eff_p13_flags = p13_mount_flags.strip() if isinstance(p13_mount_flags, str) else ""
    eff_msc_vid = (
        usb_msc_recovery_vid_pid.strip().upper()
        if isinstance(usb_msc_recovery_vid_pid, str)
        else ""
    )
    eff_fan_mode = fan_mode.strip().upper() if isinstance(fan_mode, str) else ""
    eff_fan_cmd = set_fan_eq_id_cmd.strip() if isinstance(set_fan_eq_id_cmd, str) else ""

    if not _is_non_negative_int(rf_nvs_mutation_bytes):
        _add_code(codes, STATUS_BLOCKED_G48_TELEMETRY_INVALID)
        errors.append("rf_nvs_mutation_bytes must be non-negative int.")
        telemetry_ok = False
        eff_rf_mut = 0
    else:
        eff_rf_mut = int(rf_nvs_mutation_bytes)

    if not _is_non_negative_int(rf_nvs_writes_requested):
        _add_code(codes, STATUS_BLOCKED_G48_TELEMETRY_INVALID)
        errors.append("rf_nvs_writes_requested must be non-negative int.")
        telemetry_ok = False
        eff_rf_req = 0
    else:
        eff_rf_req = int(rf_nvs_writes_requested)

    if not _is_non_negative_int(false_19v5_dcin_alarms):
        _add_code(codes, STATUS_BLOCKED_G48_TELEMETRY_INVALID)
        errors.append("false_19v5_dcin_alarms must be non-negative int.")
        telemetry_ok = False
        eff_dcin_alarms = 0
    else:
        eff_dcin_alarms = int(false_19v5_dcin_alarms)

    if not _is_finite_number(sensor_temp_c) or float(sensor_temp_c) < -40.0 or float(sensor_temp_c) > 130.0:
        _add_code(codes, STATUS_BLOCKED_G48_TELEMETRY_INVALID)
        errors.append("sensor_temp_c must be finite in [-40, 130].")
        telemetry_ok = False
        eff_temp_c = 65.0
    else:
        eff_temp_c = float(sensor_temp_c)

    if not _is_finite_number(fan_pwm_pct) or float(fan_pwm_pct) < 0.0 or float(fan_pwm_pct) > 100.0:
        _add_code(codes, STATUS_BLOCKED_G48_TELEMETRY_INVALID)
        errors.append("fan_pwm_pct must be finite in [0.0, 100.0].")
        telemetry_ok = False
        eff_pwm_pct = 100.0
    else:
        eff_pwm_pct = float(fan_pwm_pct)

    if not _is_finite_number(battery_mv) or float(battery_mv) <= 0.0:
        _add_code(codes, STATUS_BLOCKED_G48_TELEMETRY_INVALID)
        errors.append("battery_mv must be finite > 0.0.")
        telemetry_ok = False
        eff_batt_mv = 7600.0
    else:
        eff_batt_mv = float(battery_mv)

    if (
        not _is_finite_number(battery_soc_pct)
        or float(battery_soc_pct) < 0.0
        or float(battery_soc_pct) > 100.0
    ):
        _add_code(codes, STATUS_BLOCKED_G48_TELEMETRY_INVALID)
        errors.append("battery_soc_pct must be finite in [0.0, 100.0].")
        telemetry_ok = False
        eff_soc_pct = 85.0
    else:
        eff_soc_pct = float(battery_soc_pct)

    # 1) p12/p13 RF/MAC Regulatory NVS Firewall
    def _is_ro_flag(flags: str) -> bool:
        toks = [t.strip().upper() for t in flags.replace("|", ",").split(",") if t.strip()]
        return (RF_NVS_REQUIRED_MOUNT_FLAG in toks) and ("MS_RDWR" not in toks and "RW" not in toks)

    p12_p13_devs_ok = eff_p12_dev in ("/dev/nflasha12", "/dev/cnflasha12") and eff_p13_dev in (
        "/dev/nflasha13",
        "/dev/cnflasha13",
    )
    rf_ok = (
        p12_p13_devs_ok
        and _is_ro_flag(eff_p12_flags)
        and _is_ro_flag(eff_p13_flags)
        and bool(rf_nvs_write_attempts_blocked)
        and eff_rf_mut == 0
        and eff_rf_req == 0
        and (not bool(mac_address_override_attempted))
        and (not bool(regdomain_override_attempted))
    )
    rf_nvs_lock_safe = (not telemetry_ok) or rf_ok
    if telemetry_ok and not rf_ok:
        _add_code(codes, STATUS_BLOCKED_G48_RF_NVS_OR_MAC_MUTATION)
        errors.append(
            f"BLOCKED_G48_RF_NVS_OR_MAC_MUTATION: p12={eff_p12_dev}({eff_p12_flags}), "
            f"p13={eff_p13_dev}({eff_p13_flags}), blocked={bool(rf_nvs_write_attempts_blocked)}, "
            f"mutation_bytes={eff_rf_mut}, writes_requested={eff_rf_req}, "
            f"mac_override={bool(mac_address_override_attempted)}, "
            f"regdomain_override={bool(regdomain_override_attempted)}."
        )

    # 2) USB MSC 054C:0DA1 Recovery Reachability
    msc_ok = (
        eff_msc_vid == USB_MSC_RECOVERY_VID_PID
        and bool(usb_msc_0da1_reachable)
        and (not bool(usb_phy_disabled_or_masked))
        and (not bool(usb_descriptor_spoofed))
    )
    usb_msc_0da1_safe = (not telemetry_ok) or msc_ok
    if telemetry_ok and not msc_ok:
        _add_code(codes, STATUS_BLOCKED_G48_USB_MSC_0DA1_UNREACHABLE)
        errors.append(
            f"BLOCKED_G48_USB_MSC_0DA1_UNREACHABLE: vid_pid={eff_msc_vid!r}, "
            f"reachable={bool(usb_msc_0da1_reachable)}, phy_masked={bool(usb_phy_disabled_or_masked)}, "
            f"descriptor_spoofed={bool(usb_descriptor_spoofed)}."
        )

    # 3) Off-in-Rec >=58°C 45% / >=65°C 100% / >=72°C EncWfiStop & reject ALWAYS_OFF
    exp_min_pwm = 0.0
    exp_therm_wfi = False
    fan_mode_valid = eff_fan_mode in SAFE_REALHW_FAN_MODES
    if telemetry_ok and fan_mode_valid:
        exp_min_pwm, exp_therm_wfi = compute_cpapp_fan_override_pwm_pct(
            eff_fan_mode, eff_temp_c
        )
    fan_ok = (
        fan_mode_valid
        and eff_fan_cmd == FAN_SET_FAN_EQ_ID_CMD
        and (not bool(stock_cp_thermal_override_masked))
        and (eff_pwm_pct >= exp_min_pwm)
        and ((not exp_therm_wfi) or bool(thermal_encwfistop_triggered))
    )
    fan_thermal_override_safe = (not telemetry_ok) or fan_ok
    if telemetry_ok and not fan_ok:
        _add_code(codes, STATUS_BLOCKED_G48_FAN_THERMAL_OVERRIDE_VIOLATION)
        errors.append(
            f"BLOCKED_G48_FAN_THERMAL_OVERRIDE_VIOLATION: fan_mode={eff_fan_mode!r}, "
            f"cmd={eff_fan_cmd!r}, temp_c={eff_temp_c:.1f}, pwm_pct={eff_pwm_pct:.1f} "
            f"(expected >= {exp_min_pwm:.1f}%), cp_override_masked={bool(stock_cp_thermal_override_masked)}, "
            f"thermal_encwfistop_triggered={bool(thermal_encwfistop_triggered)} "
            f"(required={exp_therm_wfi})."
        )

    # 4) NP-FZ100 <=6100 mV (2%) graceful EncWfiStop & zero false 19.5V DC-IN alarms
    batt_state = "NOMINAL"
    if telemetry_ok:
        batt_state = evaluate_npfz100_6100mv_encwfistop(
            eff_batt_mv, eff_soc_pct, usb_pd_attached=bool(usb_pd_attached)
        )
    batt_wfi_required = (not bool(usb_pd_attached)) and (
        eff_batt_mv <= NPFZ100_ENCWFISTOP_MV or eff_soc_pct <= NPFZ100_ENCWFISTOP_SOC_PCT
    )
    power_ok = (
        eff_dcin_alarms == 0
        and bool(dcin_18v_19v5_comparator_masked)
        and (not bool(rsv_orphan_risk))
        and ((not batt_wfi_required) or bool(batt_encwfistop_triggered))
    )
    battery_6100mv_encwfistop_safe = (not telemetry_ok) or power_ok
    if telemetry_ok and not power_ok:
        _add_code(codes, STATUS_BLOCKED_G48_BATT_6100MV_OR_FALSE_DCIN_ALARM)
        errors.append(
            f"BLOCKED_G48_BATT_6100MV_OR_FALSE_DCIN_ALARM: batt={eff_batt_mv:.1f}mV "
            f"({eff_soc_pct:.1f}%), state={batt_state}, usb_pd={bool(usb_pd_attached)}, "
            f"encwfistop_triggered={bool(batt_encwfistop_triggered)} (required={batt_wfi_required}), "
            f"false_19v5_dcin_alarms={eff_dcin_alarms}, comparator_masked={bool(dcin_18v_19v5_comparator_masked)}, "
            f"rsv_orphan_risk={bool(rsv_orphan_risk)}."
        )

    if telemetry_ok and len(errors) == 0 and batt_state == "NEAR_END":
        warnings.append(
            f"NP-FZ100 at {eff_batt_mv:.0f} mV ({eff_soc_pct:.1f}%): NEAR_END warning active; "
            f"EncWfiStop will fire at <= {NPFZ100_ENCWFISTOP_MV:.0f} mV / 2%."
        )

    valid = len(errors) == 0 and len(codes) == 0
    if valid:
        status = STATUS_SAFE
    elif STATUS_BLOCKED_PERSISTENT_EMMC_WRITE in codes:
        status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    else:
        status = codes[0]

    return RfnvsMscFanPowerGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        guard_profile=str(guard_profile),
        p12_device_node=eff_p12_dev,
        p13_device_node=eff_p13_dev,
        p12_mount_flags=eff_p12_flags,
        p13_mount_flags=eff_p13_flags,
        rf_nvs_write_attempts_blocked=bool(rf_nvs_write_attempts_blocked),
        rf_nvs_mutation_bytes=eff_rf_mut,
        rf_nvs_writes_requested=eff_rf_req,
        mac_address_override_attempted=bool(mac_address_override_attempted),
        regdomain_override_attempted=bool(regdomain_override_attempted),
        usb_msc_recovery_vid_pid=eff_msc_vid,
        usb_msc_0da1_reachable=bool(usb_msc_0da1_reachable),
        usb_phy_disabled_or_masked=bool(usb_phy_disabled_or_masked),
        usb_descriptor_spoofed=bool(usb_descriptor_spoofed),
        fan_mode=eff_fan_mode,
        set_fan_eq_id_cmd=eff_fan_cmd,
        sensor_temp_c=round(eff_temp_c, 2),
        fan_pwm_pct=round(eff_pwm_pct, 2),
        expected_min_pwm_pct=round(exp_min_pwm, 2),
        stock_cp_thermal_override_masked=bool(stock_cp_thermal_override_masked),
        thermal_encwfistop_triggered=bool(thermal_encwfistop_triggered),
        battery_mv=round(eff_batt_mv, 2),
        battery_soc_pct=round(eff_soc_pct, 2),
        usb_pd_attached=bool(usb_pd_attached),
        batt_encwfistop_triggered=bool(batt_encwfistop_triggered),
        batt_power_state=batt_state,
        false_19v5_dcin_alarms=eff_dcin_alarms,
        dcin_18v_19v5_comparator_masked=bool(dcin_18v_19v5_comparator_masked),
        rsv_orphan_risk=bool(rsv_orphan_risk),
        rf_nvs_lock_safe=rf_nvs_lock_safe,
        usb_msc_0da1_safe=usb_msc_0da1_safe,
        fan_thermal_override_safe=fan_thermal_override_safe,
        battery_6100mv_encwfistop_safe=battery_6100mv_encwfistop_safe,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 5. Gate G47 & Gate G48 Evaluators
# ---------------------------------------------------------------------------


def evaluate_g47_pnflasha_mtdro_vault(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    pnflasha_mtdro_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase153DonorAuditResult] = None,
) -> Tuple[GateVerdict, G47PnflashaMtdroVaultResult]:
    """Evaluate Gate G47 (`pnflasha_cnflasha_cid_pairing_and_mtd0ro_guard`)."""
    audit = donor_audit or audit_phase153_donor_contracts(
        work_root=work_root,
        repo_root=repo_root,
        force_clean_room=force_clean_room,
    )

    eff_kwargs = dict(pnflasha_mtdro_kwargs or {})
    eff_kwargs["request_persistent_emmc_writes"] = bool(
        request_persistent_emmc_writes
        or eff_kwargs.get("request_persistent_emmc_writes", False)
    )
    guard_res = verify_pnflasha_cnflasha_cid_and_mtdro_guard(**eff_kwargs)

    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if not audit.valid:
        _add_code(codes, audit.status)
        errors.extend(audit.errors)
    for c in guard_res.violation_codes:
        _add_code(codes, c)
    errors.extend(guard_res.errors)
    warnings.extend(audit.warnings)
    warnings.extend(guard_res.warnings)

    passed = (
        audit.valid
        and guard_res.valid
        and (not SPI_NOR_WRITE_AUTHORIZED)
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not errors)
    )
    status = (
        STATUS_VERIFIED_G47
        if passed
        else (
            codes[0]
            if codes
            else STATUS_BLOCKED_G47_CROSS_DOMAIN_CIPHER_MISMATCH
        )
    )

    res = G47PnflashaMtdroVaultResult(
        valid=passed,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        pnflasha_mtdro_guard=guard_res.to_dict(),
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    verdict = GateVerdict(
        gate_id=G47_GATE_ID,
        gate_code=G47_GATE_CODE,
        passed=passed,
        status=status,
        evidence=(
            f"Dual-Layer pnflasha/cnflasha Cipher-Pairing, Per-Camera CID Binding & /dev/mtd0ro Guard "
            f"({guard_res.status}, domain={guard_res.backup_cipher_domain}->{guard_res.restore_target_domain}, "
            f"mtd={guard_res.mtd_device_node}, spi_nor_write_authorized={SPI_NOR_WRITE_AUTHORIZED}, "
            f"{audit.verification_mode}), "
            f"persistent_emmc_writes_authorized={PERSISTENT_EMMC_WRITES_AUTHORIZED}."
        ),
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
        details={
            "verification_mode": audit.verification_mode,
            "cipher_pairing_safe": guard_res.cipher_pairing_safe,
            "camera_cid_binding_safe": guard_res.camera_cid_binding_safe,
            "mtd_readonly_guard_safe": guard_res.mtd_readonly_guard_safe,
            "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
        },
    )
    return verdict, res


def evaluate_g48_rfnvs_fan_power_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    rfnvs_fan_power_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase153DonorAuditResult] = None,
) -> Tuple[GateVerdict, G48RfnvsFanPowerGuardResult]:
    """Evaluate Gate G48 (`rfnvs_p12_p13_msc_0da1_fan_65c_override_and_6100mv_encwfistop_safe`)."""
    audit = donor_audit or audit_phase153_donor_contracts(
        work_root=work_root,
        repo_root=repo_root,
        force_clean_room=force_clean_room,
    )

    eff_kwargs = dict(rfnvs_fan_power_kwargs or {})
    eff_kwargs["request_persistent_emmc_writes"] = bool(
        request_persistent_emmc_writes
        or eff_kwargs.get("request_persistent_emmc_writes", False)
    )
    guard_res = verify_rfnvs_msc_fan_override_and_power_guard(**eff_kwargs)

    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if not audit.valid:
        _add_code(codes, audit.status)
        errors.extend(audit.errors)
    for c in guard_res.violation_codes:
        _add_code(codes, c)
    errors.extend(guard_res.errors)
    warnings.extend(audit.warnings)
    warnings.extend(guard_res.warnings)

    passed = (
        audit.valid
        and guard_res.valid
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not errors)
    )
    status = (
        STATUS_VERIFIED_G48
        if passed
        else (
            codes[0]
            if codes
            else STATUS_BLOCKED_G48_RF_NVS_OR_MAC_MUTATION
        )
    )

    res = G48RfnvsFanPowerGuardResult(
        valid=passed,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        rfnvs_fan_power_guard=guard_res.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    verdict = GateVerdict(
        gate_id=G48_GATE_ID,
        gate_code=G48_GATE_CODE,
        passed=passed,
        status=status,
        evidence=(
            f"p12/p13 RF NVS Firewall, USB MSC 054C:0DA1, Off-in-Rec >=65C 100% PWM & 6100mV EncWfiStop "
            f"({guard_res.status}, rf_mut={guard_res.rf_nvs_mutation_bytes}B, "
            f"msc={guard_res.usb_msc_recovery_vid_pid}, fan={guard_res.fan_pwm_pct:.0f}%@{guard_res.sensor_temp_c:.0f}C, "
            f"batt={guard_res.battery_mv:.0f}mV/{guard_res.batt_power_state}, {audit.verification_mode}), "
            f"persistent_emmc_writes_authorized={PERSISTENT_EMMC_WRITES_AUTHORIZED}."
        ),
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
        details={
            "verification_mode": audit.verification_mode,
            "rf_nvs_lock_safe": guard_res.rf_nvs_lock_safe,
            "usb_msc_0da1_safe": guard_res.usb_msc_0da1_safe,
            "fan_thermal_override_safe": guard_res.fan_thermal_override_safe,
            "battery_6100mv_encwfistop_safe": guard_res.battery_6100mv_encwfistop_safe,
        },
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 6. Unified 48-Gate Master Safety Preflight (`G01..G48`)
# ---------------------------------------------------------------------------


def evaluate_48gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated_backup: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    # G1..G46 pass-throughs
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
    ptpip_or_mc_requests: Optional[Sequence[Mapping[str, Any]]] = None,
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
    # G47 inputs (Dual-layer pnflasha/cnflasha cipher-pairing, CID & /dev/mtd0ro)
    pnflasha_mtdro_kwargs: Optional[Mapping[str, Any]] = None,
    # G48 inputs (p12/p13 RF NVS, USB MSC 054C:0DA1, Fan >=65C & 6100mV EncWfiStop)
    rfnvs_fan_power_kwargs: Optional[Mapping[str, Any]] = None,
) -> Master48GateReport:
    """Evaluate all 48 Master Safety Gates (`G01..G48`) deterministically."""
    resolved_root = (
        DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)
    ).resolve()
    clean_forced = _is_forced_clean_room(force_clean_room)

    m46_kwargs: Dict[str, Any] = {
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
    }
    if soc_start_ceiling_c is not None:
        m46_kwargs["soc_start_ceiling_c"] = soc_start_ceiling_c

    m46_report: Master46GateReport = evaluate_46gate_preflight(
        resolved_root, **m46_kwargs
    )

    phase153_audit = audit_phase153_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
    )

    g47_verdict, g47_res = evaluate_g47_pnflasha_mtdro_vault(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        pnflasha_mtdro_kwargs=pnflasha_mtdro_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase153_audit,
    )

    g48_verdict, g48_res = evaluate_g48_rfnvs_fan_power_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        rfnvs_fan_power_kwargs=rfnvs_fan_power_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase153_audit,
    )

    gates_47_to_48 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g47_verdict, g48_verdict)
    ]
    all_gates = tuple(list(m46_report.gates) + gates_47_to_48)

    g01_to_g12_verified = int(m46_report.summary["g01_to_g12_verified"])
    g13_to_g46_verified = (
        int(m46_report.summary["g13_to_g44_verified"])
        + int(m46_report.summary["g45_to_g46_verified"])
    )
    g47_to_g48_verified = sum(1 for v in (g47_verdict, g48_verdict) if v.passed)
    total_verified = g01_to_g12_verified + g13_to_g46_verified + g47_to_g48_verified

    g47_to_g48_all_passed = g47_to_g48_verified == 2
    g13_to_g48_all_passed = (
        m46_report.g13_to_g46_all_passed and g47_to_g48_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m46_report.gates[:9])

    offline_45_verified = (
        g01_to_g09_ok
        and m46_report.offline_43_gates_verified
        and g47_to_g48_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_48_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g48_all_passed
        and (not request_persistent_emmc_writes)
    )

    # Hard-locked False in offline and dry-run modes; never authorizes eMMC/SPI-NOR writes
    overall_ready_for_hardware_attach = False

    h0_h1_allowed = (
        offline_45_verified
        and m46_report.h0_h1_trial_entry_allowed
        and g47_to_g48_all_passed
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not SPI_NOR_WRITE_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    errors: List[str] = (
        list(m46_report.errors) + list(g47_verdict.errors) + list(g48_verdict.errors)
    )
    warnings: List[str] = (
        list(m46_report.warnings)
        + list(g47_verdict.warnings)
        + list(g48_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m46_report.g13_to_g46_all_passed:
        overall_status = m46_report.status
    elif not g47_verdict.passed:
        overall_status = g47_verdict.status
    elif not g48_verdict.passed:
        overall_status = g48_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_48_verified and dry_run_simulated_backup:
        overall_status = "VERIFIED_ALL_48_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_48_verified:
        overall_status = "VERIFIED_ALL_48_GATES"
    else:
        overall_status = "VERIFIED_45_OF_48_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m46_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g47_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g48_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 48,
        "verified_gates": total_verified,
        "blocked_or_pending_gates": 48 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g46_verified": g13_to_g46_verified,
        "g47_to_g48_verified": g47_to_g48_verified,
        "g13_to_g48_all_passed": g13_to_g48_all_passed,
        "g47_to_g48_all_passed": g47_to_g48_all_passed,
        "offline_45_gates_verified": offline_45_verified,
        "all_48_gates_verified": all_48_verified,
        "dry_run_rehearsal_only": bool(dry_run_simulated_backup),
        "overall_ready_for_hardware_attach": overall_ready_for_hardware_attach,
        "h0_h1_trial_entry_allowed": h0_h1_allowed,
        "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
    }

    return Master48GateReport(
        schema=REALHW_PNFLASHA_MTDRO_RFNVS_48GATE_SCHEMA,
        version=REALHW_PNFLASHA_MTDRO_RFNVS_48GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=bool(dry_run_simulated_backup),
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        offline_45_gates_verified=offline_45_verified,
        all_48_gates_verified=all_48_verified,
        g13_to_g48_all_passed=g13_to_g48_all_passed,
        g47_to_g48_all_passed=g47_to_g48_all_passed,
        h0_h1_trial_entry_allowed=h0_h1_allowed,
        status=overall_status,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        summary=summary,
        gates=all_gates,
        master_46_report=m46_report.to_dict(),
        g47_result=g47_res.to_dict(),
        g48_result=g48_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_48_master_safety_gates = evaluate_48gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_pnflasha_mtdro_rfnvs_and_48gate_guard",
        description=(
            "Phase 153 — Dual-Layer pnflasha/cnflasha Cipher-Pairing & /dev/mtd0ro Guard "
            "(G47), p12/p13 RF NVS, USB MSC 054C:0DA1, Off-in-Rec 65C Fan Override & "
            "6100mV EncWfiStop Guard (G48), and 48-Gate Master Preflight (G01..G48)"
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
        help="Supply simulated dry-run Tier-0 backup inputs so G01..G48 can be exercised offline",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit structured JSON report",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = evaluate_48gate_preflight(
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
            f"verified={report.summary['verified_gates']}/48 "
            f"g47_to_g48_all_passed={report.g47_to_g48_all_passed} "
            f"all_48_gates_verified={report.all_48_gates_verified} "
            f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
            f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
            f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}\n"
        )
    ok = (
        report.all_48_gates_verified
        if args.dry_run_simulated_backup
        else report.offline_45_gates_verified
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
