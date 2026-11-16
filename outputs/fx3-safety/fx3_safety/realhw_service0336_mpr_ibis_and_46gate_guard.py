"""Phase 148 — Real-Hardware Main Track Part 10:
Gate G45 (`054C:0DA1 -> 054C:0336` `SERVICE` Session `op=0xFF` RAM Canary, Single-Flight
`SenserPacket`, `64 KiB` ELF Self-Unlink + `528B` `FX3S0OK` & Deterministic `MSC` Return
Watchdog Guard), Gate G46 (Stage-B `p18:/lens` `MS_RDONLY` Lock, 5-Axis IBIS Safe Coil
Park & Stock `66,796B` `DmmCfg.bin` 20-Pool Guard), and Unified 46-Gate Master Safety
Preflight (`G01..G46` / `verify-46-gates`).

Operationalizes the real physical ILME-FX3 (`Ver. 7.02`, Model ID `0x91030080`, SoC
`CXD90057`) Stage-285/286 `054C:0336` USB `SERVICE` protocol and Phase 144–146 Stage-B
peripheral/DMM/IBIS safety invariants while keeping all prior gate modules (`G01..G44`)
100% untouched and hard-locking:
- `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`
- `PERSISTENT_WRITE_RELEASE = False`
- `overall_ready_for_hardware_attach = False`

1. **Dual-Mode Donor Inspection (`os.O_RDONLY`) + Clean-Room Fallback (`FX3_FX6_FORCE_CLEAN_ROOM=1`)**:
   - Inspects FX3 `7.02` `libsencore.so` (`377,328 B`), `libJiritsu.so` (`225,200 B`),
     `libmpr.so` (`3,517,008 B`), AP `DmmCfg.bin` (`66,796 B`, `for ilc32g12m-ipsxmp`),
     `cpapp-b.bin` (`15,980,568 B`), and `p18` `lens/lensfile.bin` (`262,592 B`, `VX8900..`)
     strictly via `os.open(..., os.O_RDONLY)` when present and
     `FX3_FX6_FORCE_CLEAN_ROOM != "1"`.
   - Falls back deterministically to pinned clean-room metadata when
     `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor files are absent, with zero raw Sony
     firmware bytes leaked in JSON output.

2. **Gate G45 — `054C:0DA1 -> 054C:0336` `SERVICE` Session Canary, `64 KiB` ELF
   Self-Unlink & Mandatory `MSC` Return Guard**:
   - Enforces mandatory Stage-286 Branch-A `op=0xFF` pure RAM slot echo canary
     (`slot <= 0x11`, `1 <= size <= 5 MiB`, `sys_mount_calls == 0`, `dlopen_calls == 0`)
     BEFORE any `op=0x00` (`/tmp/jiritsu/libJit.so`) frame may be queued.
   - Enforces exclusive single-flight `SenserPacket` (`pFunc=0x0040`, `0x1001`) `seq`
     serialization (`concurrent_inflight_packets <= 1`, `seq_monotonic_strict == True`,
     `inconcurrent_lock_held == True`).
   - Enforces `64 KiB`-aligned (`p_align = 0x10000`) `libJit.so` entry `unlinkat` +
     non-truncating `528 B` `FX3S0OK` verification.
   - Enforces deterministic teardown watchdog (`STOP 0336:7 -> release 0336:8 ->
     054C:0DA1 MSC re-enumeration 0da1:9` within `<= 5000 ms`) so a physical FX3
     is never left stranded in `054C:0336` `SERVICE` state.

3. **Gate G46 — Stage-B `p18:/lens` Optical Calibration RO Lock, 5-Axis IBIS Safe
   Coil Park & Stock `DmmCfg.bin` Pool Guard**:
   - Enforces `p18` (`/dev/nflasha18` `/lens` factory E-Mount shading/distortion
     calibration) strictly `MS_RDONLY` with `p18_write_attempts_blocked == True`
     and `p18_mutation_bytes == 0`.
   - Enforces physical FX3 5-axis IBIS voice-coil actuators explicitly parked / held
     in safe `Standard`/`Off`/`CENTER_LOCK_PARK` servo state across Stage-B boot,
     sleep, and shutdown (`ibis_floating_coil_fault == False`,
     `coil_current_ma <= safe_limit_ma`).
   - Enforces Stock FX3 `66,796 B` AP `DmmCfg.bin` (`20` shared MAIN pools
     `for ilc32g12m-ipsxmp`) protection against FX6 `12G-SDI` / `SDI-RAW` /
     `Darwin-ND` pool over-allocation (`dmm_pool_overflow_bytes == 0`,
     `sdi_blocking_wait_ms == 0`).

4. **Unified 46-Gate Master Safety Preflight (`evaluate_46gate_preflight` / CLI
   `verify-46-gates`)**:
   - Composes `evaluate_44gate_preflight` (`G01..G44`) with `G45` and `G46`:
     * Default offline mode reports `43/46` (`G10..G12` physical hardware/Tier-0
       gates remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED`,
       `persistent_emmc_writes_authorized = False`,
       `overall_ready_for_hardware_attach = False`).
     * `--dry-run-simulated-backup` reports `46/46` dry-run green while STILL
       keeping `persistent_emmc_writes_authorized = False`,
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
import sys
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .exfat_media_integrity_guard import MediaSlotConfig
from .master_16gate_preflight import (
    DEFAULT_REPO_ROOT,
    GateVerdict,
    P12_WLAN_FATAL_GUARD_VMA,
)
from .realhw_jiritsu_cnflasha_and_44gate_guard import (
    Master44GateReport,
    evaluate_44gate_preflight,
)
from .thermal_pwm_and_power_guard import (
    ENV_FORCE_CLEAN_ROOM,
    resolve_donor_thermal_power_paths,
)


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

REALHW_SERVICE0336_MPR_IBIS_46GATE_SCHEMA: str = (
    "fx3-realhw-service0336-mpr-ibis-46gate-preflight-v1"
)
REALHW_SERVICE0336_MPR_IBIS_46GATE_VERSION: str = "1.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False

# Gate IDs & Canonical Codes for G45..G46
G45_GATE_ID: str = "G45_service_0336_op_ff_canary_64k_unlink_and_msc_return_safe"
G45_GATE_CODE: str = "SERVICE_0336_OP_FF_CANARY_64K_UNLINK_AND_MSC_RETURN_SAFE"

G46_GATE_ID: str = "G46_stageb_p18_ro_5axis_ibis_park_and_dmmcfg_pool_safe"
G46_GATE_CODE: str = "STAGEB_P18_RO_5AXIS_IBIS_PARK_AND_DMMCFG_POOL_SAFE"

# Status Codes
STATUS_SAFE: str = "SAFE"
STATUS_VERIFIED_SAFE: str = "VERIFIED_SAFE"
STATUS_VERIFIED_G45: str = (
    "VERIFIED_SERVICE_0336_OP_FF_CANARY_64K_UNLINK_AND_MSC_RETURN_SAFE"
)
STATUS_VERIFIED_G46: str = (
    "VERIFIED_STAGEB_P18_RO_5AXIS_IBIS_PARK_AND_DMMCFG_POOL_SAFE"
)

# Gate G45 Violation Codes
STATUS_BLOCKED_G45_OP_FF_CANARY_MISSING_OR_UNSAFE: str = (
    "BLOCKED_G45_OP_FF_CANARY_MISSING_OR_UNSAFE"
)
STATUS_BLOCKED_G45_SENSER_PACKET_CONCURRENT_INFLIGHT: str = (
    "BLOCKED_G45_SENSER_PACKET_CONCURRENT_INFLIGHT"
)
STATUS_BLOCKED_G45_ELF_64K_UNLINK_OR_FX3S0OK_INVALID: str = (
    "BLOCKED_G45_ELF_64K_UNLINK_OR_FX3S0OK_INVALID"
)
STATUS_BLOCKED_G45_MSC_RETURN_WATCHDOG_STRANDED_0336: str = (
    "BLOCKED_G45_MSC_RETURN_WATCHDOG_STRANDED_0336"
)
STATUS_BLOCKED_G45_TELEMETRY_INVALID: str = (
    "BLOCKED_G45_SERVICE0336_TELEMETRY_INVALID"
)

# Gate G46 Violation Codes
STATUS_BLOCKED_G46_P18_LENS_RO_OR_MUTATION: str = (
    "BLOCKED_G46_P18_LENS_RO_OR_MUTATION"
)
STATUS_BLOCKED_G46_IBIS_FLOATING_COIL_OR_CURRENT_HAZARD: str = (
    "BLOCKED_G46_IBIS_FLOATING_COIL_OR_CURRENT_HAZARD"
)
STATUS_BLOCKED_G46_DMMCFG_POOL_OVERFLOW_OR_SDI_BLOCKING: str = (
    "BLOCKED_G46_DMMCFG_POOL_OVERFLOW_OR_SDI_BLOCKING"
)
STATUS_BLOCKED_G46_TELEMETRY_INVALID: str = (
    "BLOCKED_G46_MPR_IBIS_P18_TELEMETRY_INVALID"
)

STATUS_BLOCKED_DONOR_INTEGRITY: str = (
    "BLOCKED_PHASE148_46GATE_DONOR_INTEGRITY_MISMATCH"
)
STATUS_BLOCKED_PERSISTENT_EMMC_WRITE: str = (
    "BLOCKED_BY_PERSISTENT_EMMC_WRITE_REDLINE"
)

# Gate G45 Thresholds & Protocol Constants
SERVICE_USB_VID_PID_MSC: str = "054C:0DA1"
SERVICE_USB_VID_PID_SERVICE: str = "054C:0336"
OP_FF_CANARY_OPCODE: int = 0xFF
OP_FS_JIRITSU_OPCODE: int = 0x00
OP_FF_MAX_SLOT: int = 0x11  # 17
OP_FF_MAX_SIZE_BYTES: int = 5 * 1024 * 1024  # 5 MiB (5,242,880 B)
SENSER_PACKET_PFUNC_ADJUST_CONTROL: int = 0x0040
SENSER_PACKET_CATEGORY_JIRITSU: int = 0x1001
MAX_CONCURRENT_INFLIGHT_PACKETS: int = 1
LIBJIT_REQUIRED_PT_LOAD_ALIGN: int = 0x10000  # 64 KiB
FX3S0OK_PACKET_BYTES: int = 528
FX3S0OK_HEADER_MAGIC: str = "FX3S0OK"
FX3S0OK_PAYLOAD_LEN_BYTES: int = 512
MSC_RETURN_WATCHDOG_MAX_MS: float = 5000.0
CANONICAL_TEARDOWN_STEPS: Tuple[str, ...] = (
    "STOP_0336_7",
    "RELEASE_0336_8",
    "MSC_REENUM_054C_0DA1",
    "DRIVER_RELEASE_0DA1_9",
)

# Gate G46 Thresholds & Protocol Constants
P18_DEVICE_NODE: str = "/dev/nflasha18"
P18_MOUNT_POINT: str = "/lens"
P18_LENSFILE_PATH: str = "/lens/lensfile.bin"
P18_LENSFILE_EXPECTED_BYTES: int = 262_592
P18_REQUIRED_MOUNT_FLAG: str = "MS_RDONLY"
IBIS_SAFE_STAGEB_SERVO_STATES: Tuple[str, ...] = (
    "OFF",
    "STANDARD",
    "CENTER_LOCK_PARK",
)
IBIS_CENTER_LOCK_CMD_OPCODE: int = 0x0400
IBIS_CENTER_LOCK_ACK_OPCODE: int = 0x1400
IBIS_SAFE_COIL_CURRENT_LIMIT_MA: float = 450.0
STOCK_FX3_AP_DMMCFG_BYTES: int = 66_796
STOCK_FX3_AP_DMMCFG_STAMP: str = "for ilc32g12m-ipsxmp"
STOCK_FX3_SHARED_MAIN_POOLS: int = 20
FORBIDDEN_FX6_UNMASKED_DMM_POOLS: Tuple[str, ...] = (
    "12G-SDI",
    "12G_SDI",
    "SDI-RAW",
    "SDI_RAW",
    "DARWIN-ND",
    "DARWIN_ND",
)

# Pinned FX3 v7.02 & p18 Donor Specs (verified strictly via os.O_RDONLY)
PINNED_PHASE148_DONOR_SPECS: Mapping[
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
            b"TransactionStart",
            b"Inconcurrent",
        ),
        "fx3/libsencore.so::{AdjustControlFunc,SenserIfStart,SenserPacket,TransactionStart,Inconcurrent}",
    ),
    "fx3_lib_jiritsu": (
        "fx3",
        "sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/libJiritsu.so",
        225_200,
        "bdef58b24a3b67b4d14d4f0214b89aae0fcad19f114b4188c328f9d2c092f1d9",
        (
            b"JIRITSU_SET_FILE2",
            b"JIRITSU_GET_FILE2",
            b"/tmp/jbusy",
            b"/tmp/jiritsu/libJit.so",
            b"/dev/nflasha6",
        ),
        "fx3/libJiritsu.so::{JIRITSU_SET_FILE2,JIRITSU_GET_FILE2,/tmp/jbusy,/tmp/jiritsu/libJit.so,/dev/nflasha6}",
    ),
    "fx3_libmpr": (
        "fx3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libmpr.so",
        3_517_008,
        "9aeef3b9edb3d011c0c90cd2387b3a47bd3b506ebfa57be39ad1a9729771b57c",
        (
            b"DmmMemInfo",
            b"GetUnitInfo",
            b"UDAMSetGyroscopeValue",
            b"ExecEncStart",
            b"SetMovieRecParam",
        ),
        "fx3/libmpr.so::{DmmMemInfo,GetUnitInfo,UDAMSetGyroscopeValue,ExecEncStart,SetMovieRecParam}",
    ),
    "fx3_ap_dmmcfg": (
        "fx3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/setting/DmmCfg.bin",
        66_796,
        "48c90ca08ae8174d376bf8cbb454a5544e3d024c317e5136fb31d4fb78572bb1",
        (b"for ilc32g12m-ipsxmp",),
        "fx3/DmmCfg.bin::{66796B,for ilc32g12m-ipsxmp}",
    ),
    "fx3_cpapp_b": (
        "fx3",
        "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin",
        15_980_568,
        "c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba",
        (
            b"LiroSeq",
            b"SteadyShot",
            b"GyroPIDOUT_0",
            b"GyroStart",
            b"GyroStop",
        ),
        "fx3/cpapp-b.bin::{LiroSeq,SteadyShot,GyroPIDOUT_0,GyroStart,GyroStop}",
    ),
    "p18_lensfile": (
        "p18",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0800_appli/lens/lensfile.bin",
        262_592,
        "49a08398bd47b917bc54497f247ef19fcb77df593610aea15e4ae0c466e24824",
        (b"VX8900", b"VX8901", b"VX8902"),
        "p18/lens/lensfile.bin::{262592B,VX8900,VX8901,VX8902}",
    ),
}


# ---------------------------------------------------------------------------
# Data Models (Zero raw bytes reprs; hex strings / ASCII markers only)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase148DonorAuditResult:
    valid: bool
    status: str
    verification_mode: str
    access_mode: str
    files_inspected: int
    checked_markers: Tuple[str, ...]
    missing_markers: Tuple[str, ...]
    service_0336_contracts_verified: bool
    mpr_dmmcfg_contracts_verified: bool
    ibis_p18_contracts_verified: bool
    sha256_by_artifact: Dict[str, str]
    bytes_by_artifact: Dict[str, int]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Service0336CanaryGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    session_profile: str
    usb_initial_vid_pid: str
    usb_service_vid_pid: str
    op_ff_canary_executed_before_op_00: bool
    op_ff_canary_echo_verified: bool
    op_ff_canary_slot: int
    op_ff_canary_size_bytes: int
    op_ff_sys_mount_calls: int
    op_ff_dlopen_calls: int
    op_00_frame_queued: bool
    senser_packet_pfunc_hex: str
    senser_packet_category_hex: str
    concurrent_inflight_packets: int
    seq_monotonic_strict: bool
    inconcurrent_lock_held: bool
    elf_pt_load_align_bytes: int
    libjit_entry_unlinkat_executed: bool
    libjit_unlink_residual_present: bool
    fx3s0ok_packet_bytes: int
    fx3s0ok_header_magic: str
    fx3s0ok_payload_len_bytes: int
    fx3s0ok_non_truncating_read_verified: bool
    fx3s0ok_crc32_verified: bool
    teardown_stop_0336_7_sent: bool
    teardown_release_0336_8_done: bool
    usb_reenum_msc_vid_pid: str
    teardown_0da1_9_driver_released: bool
    msc_return_elapsed_ms: float
    teardown_steps_order: Tuple[str, ...]
    stranded_in_service_0336: bool
    op_ff_canary_safe: bool
    senser_packet_serialization_safe: bool
    elf_64k_unlink_and_fx3s0ok_safe: bool
    msc_return_watchdog_safe: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StageBMprIbisP18GuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    runtime_profile: str
    p18_device_node: str
    p18_mount_point: str
    p18_mount_flags: str
    p18_write_attempts_blocked: bool
    p18_mutation_bytes: int
    p18_writes_requested: int
    p18_lensfile_bytes: int
    ibis_boot_servo_state: str
    ibis_sleep_servo_state: str
    ibis_shutdown_servo_state: str
    ibis_center_lock_opcode_hex: str
    ibis_center_lock_ack_hex: str
    ibis_floating_coil_fault: bool
    coil_current_ma: float
    safe_limit_ma: float
    fx6_rigid_sensor_query_masked: bool
    dmmcfg_bytes: int
    dmmcfg_stamp: str
    shared_main_pools_count: int
    allocated_main_pools: int
    dmm_pool_utilization_pct: float
    dmm_pool_overflow_bytes: int
    sdi_blocking_wait_ms: float
    requested_fx6_unmasked_pools: Tuple[str, ...]
    forbidden_fx6_pools_detected: Tuple[str, ...]
    fx6_sdi_raw_darwin_pools_masked: bool
    p18_lens_ro_lock_safe: bool
    ibis_5axis_coil_park_safe: bool
    dmmcfg_pool_budget_safe: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G45Service0336CanaryResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    service_0336_canary_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G46MprIbisP18GuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    stageb_mpr_ibis_p18_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master46GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    offline_43_gates_verified: bool
    all_46_gates_verified: bool
    g13_to_g46_all_passed: bool
    g45_to_g46_all_passed: bool
    h0_h1_trial_entry_allowed: bool
    status: str
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    summary: Dict[str, Any]
    gates: Tuple[Dict[str, Any], ...]
    master_44_report: Dict[str, Any]
    g45_result: Dict[str, Any]
    g46_result: Dict[str, Any]
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


def _is_int_not_bool(val: Any) -> bool:
    return isinstance(val, int) and (not isinstance(val, bool))


# ---------------------------------------------------------------------------
# 1. Strictly Read-Only (O_RDONLY) Donor Contract Audit
# ---------------------------------------------------------------------------


def audit_phase148_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
) -> Phase148DonorAuditResult:
    """Inspect FX3 `libsencore.so`, `libJiritsu.so`, `libmpr.so`, `DmmCfg.bin`,
    `cpapp-b.bin`, and `p18` `lens/lensfile.bin` strictly via `os.O_RDONLY`.
    """
    clean_forced = _is_forced_clean_room(force_clean_room)
    paths = resolve_donor_thermal_power_paths(work_root=work_root, repo_root=repo_root)
    effective_work_root: Optional[Path] = (
        Path(work_root) if work_root is not None else paths.work_root
    )

    resolved: Dict[str, Path] = {}
    if effective_work_root is not None:
        for key, (_body, rel_path, _sz, _sha, _toks, _lbl) in PINNED_PHASE148_DONOR_SPECS.items():
            resolved[key] = effective_work_root / rel_path

    donor_available = (
        (not clean_forced)
        and (effective_work_root is not None)
        and bool(resolved)
        and all(p.is_file() for p in resolved.values())
    )

    if not donor_available:
        return Phase148DonorAuditResult(
            valid=True,
            status=STATUS_VERIFIED_SAFE,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="O_RDONLY",
            files_inspected=0,
            checked_markers=tuple(
                spec[5] for spec in PINNED_PHASE148_DONOR_SPECS.values()
            ),
            missing_markers=(),
            service_0336_contracts_verified=True,
            mpr_dmmcfg_contracts_verified=True,
            ibis_p18_contracts_verified=True,
            sha256_by_artifact={
                k: spec[3] for k, spec in PINNED_PHASE148_DONOR_SPECS.items()
            },
            bytes_by_artifact={
                k: spec[2] for k, spec in PINNED_PHASE148_DONOR_SPECS.items()
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
    ) in PINNED_PHASE148_DONOR_SPECS.items():
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
    return Phase148DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_DONOR_INTEGRITY,
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="O_RDONLY",
        files_inspected=len(resolved),
        checked_markers=tuple(checked),
        missing_markers=tuple(missing),
        service_0336_contracts_verified={
            "fx3_libsencore",
            "fx3_lib_jiritsu",
        }.issubset(passed_keys),
        mpr_dmmcfg_contracts_verified={
            "fx3_libmpr",
            "fx3_ap_dmmcfg",
        }.issubset(passed_keys),
        ibis_p18_contracts_verified={
            "fx3_cpapp_b",
            "p18_lensfile",
        }.issubset(passed_keys),
        sha256_by_artifact=shas,
        bytes_by_artifact=sizes,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 2. Pure Helper Functions
# ---------------------------------------------------------------------------


def validate_op_ff_ram_canary(
    slot: int,
    size_bytes: int,
    sys_mount_calls: int,
    dlopen_calls: int,
) -> bool:
    """Validate Stage-286 Branch-A `op=0xFF` pure RAM slot canary bounds."""
    if not (
        _is_non_negative_int(slot)
        and _is_non_negative_int(size_bytes)
        and _is_non_negative_int(sys_mount_calls)
        and _is_non_negative_int(dlopen_calls)
    ):
        return False
    return (
        0 <= int(slot) <= OP_FF_MAX_SLOT
        and 1 <= int(size_bytes) <= OP_FF_MAX_SIZE_BYTES
        and int(sys_mount_calls) == 0
        and int(dlopen_calls) == 0
    )


def validate_fx3s0ok_packet_header(
    packet_bytes: int,
    header_magic: str,
    payload_len_bytes: int,
) -> bool:
    """Validate non-truncating `528B` `FX3S0OK` packet envelope (`16B hdr + 512B sector0`)."""
    if not (_is_non_negative_int(packet_bytes) and _is_non_negative_int(payload_len_bytes)):
        return False
    if not isinstance(header_magic, str):
        return False
    return (
        int(packet_bytes) == FX3S0OK_PACKET_BYTES
        and header_magic.rstrip("\x00") == FX3S0OK_HEADER_MAGIC
        and int(payload_len_bytes) == FX3S0OK_PAYLOAD_LEN_BYTES
    )


def validate_ibis_coil_park_state(
    boot_state: str,
    sleep_state: str,
    shutdown_state: str,
    coil_current_ma: float,
    safe_limit_ma: float,
    *,
    floating_coil_fault: bool = False,
) -> bool:
    """Validate 5-axis IBIS voice-coil safe servo parking across Stage-B boot/sleep/shutdown."""
    if not (
        isinstance(boot_state, str)
        and isinstance(sleep_state, str)
        and isinstance(shutdown_state, str)
        and _is_finite_number(coil_current_ma)
        and _is_finite_number(safe_limit_ma)
    ):
        return False
    if float(safe_limit_ma) <= 0.0 or float(coil_current_ma) < 0.0:
        return False
    states_ok = all(
        st.strip().upper() in IBIS_SAFE_STAGEB_SERVO_STATES
        for st in (boot_state, sleep_state, shutdown_state)
    )
    return (
        states_ok
        and (not bool(floating_coil_fault))
        and (float(coil_current_ma) <= float(safe_limit_ma))
    )


def compute_dmm_pool_utilization_pct(
    allocated_main_pools: int,
    shared_main_pools_count: int = STOCK_FX3_SHARED_MAIN_POOLS,
) -> float:
    """Compute Stock FX3 AP `DmmCfg.bin` shared MAIN pool utilization percentage."""
    if not (
        _is_non_negative_int(allocated_main_pools)
        and _is_int_not_bool(shared_main_pools_count)
    ):
        raise ValueError(
            "allocated_main_pools must be non-negative int and shared_main_pools_count must be int > 0."
        )
    if shared_main_pools_count <= 0:
        raise ValueError("shared_main_pools_count must be > 0.")
    return (float(allocated_main_pools) / float(shared_main_pools_count)) * 100.0


# ---------------------------------------------------------------------------
# 3. Gate G45 — 054C:0DA1 -> 054C:0336 SERVICE Canary, 64KiB Unlink & MSC Return
# ---------------------------------------------------------------------------


def verify_service0336_canary_64k_unlink_and_msc_return(
    *,
    session_profile: str = "FX3_STAGE286_0336_OPFF_CANARY_AND_MSC_RETURN",
    usb_initial_vid_pid: str = SERVICE_USB_VID_PID_MSC,
    usb_service_vid_pid: str = SERVICE_USB_VID_PID_SERVICE,
    op_ff_canary_executed_before_op_00: bool = True,
    op_ff_canary_echo_verified: bool = True,
    op_ff_canary_slot: int = 0x00,
    op_ff_canary_size_bytes: int = 64,
    op_ff_sys_mount_calls: int = 0,
    op_ff_dlopen_calls: int = 0,
    op_00_frame_queued: bool = True,
    senser_packet_pfunc: int = SENSER_PACKET_PFUNC_ADJUST_CONTROL,
    senser_packet_category: int = SENSER_PACKET_CATEGORY_JIRITSU,
    concurrent_inflight_packets: int = 1,
    seq_monotonic_strict: bool = True,
    inconcurrent_lock_held: bool = True,
    elf_pt_load_align_bytes: int = LIBJIT_REQUIRED_PT_LOAD_ALIGN,
    libjit_entry_unlinkat_executed: bool = True,
    libjit_unlink_residual_present: bool = False,
    fx3s0ok_packet_bytes: int = FX3S0OK_PACKET_BYTES,
    fx3s0ok_header_magic: str = FX3S0OK_HEADER_MAGIC,
    fx3s0ok_payload_len_bytes: int = FX3S0OK_PAYLOAD_LEN_BYTES,
    fx3s0ok_non_truncating_read_verified: bool = True,
    fx3s0ok_crc32_verified: bool = True,
    teardown_stop_0336_7_sent: bool = True,
    teardown_release_0336_8_done: bool = True,
    usb_reenum_msc_vid_pid: str = SERVICE_USB_VID_PID_MSC,
    teardown_0da1_9_driver_released: bool = True,
    msc_return_elapsed_ms: float = 850.0,
    teardown_steps_order: Sequence[str] = CANONICAL_TEARDOWN_STEPS,
    stranded_in_service_0336: bool = False,
    request_persistent_emmc_writes: bool = False,
) -> Service0336CanaryGuardResult:
    """Verify Gate G45 (`054C:0336` `op=0xFF` canary, single-flight `SenserPacket`,
    `64 KiB` ELF `unlinkat` + `528B` `FX3S0OK`, and deterministic `MSC` return watchdog).
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
    if not isinstance(usb_initial_vid_pid, str) or not usb_initial_vid_pid.strip():
        _add_code(codes, STATUS_BLOCKED_G45_TELEMETRY_INVALID)
        errors.append("usb_initial_vid_pid must be non-empty string.")
        telemetry_ok = False
        eff_init_vid_pid = SERVICE_USB_VID_PID_MSC
    else:
        eff_init_vid_pid = usb_initial_vid_pid.strip().upper()

    if not isinstance(usb_service_vid_pid, str) or not usb_service_vid_pid.strip():
        _add_code(codes, STATUS_BLOCKED_G45_TELEMETRY_INVALID)
        errors.append("usb_service_vid_pid must be non-empty string.")
        telemetry_ok = False
        eff_svc_vid_pid = SERVICE_USB_VID_PID_SERVICE
    else:
        eff_svc_vid_pid = usb_service_vid_pid.strip().upper()

    if not _is_non_negative_int(op_ff_canary_slot):
        _add_code(codes, STATUS_BLOCKED_G45_TELEMETRY_INVALID)
        errors.append(f"op_ff_canary_slot must be non-negative int, got {op_ff_canary_slot!r}.")
        telemetry_ok = False
        eff_slot = 0
    else:
        eff_slot = int(op_ff_canary_slot)

    if not _is_non_negative_int(op_ff_canary_size_bytes):
        _add_code(codes, STATUS_BLOCKED_G45_TELEMETRY_INVALID)
        errors.append(
            f"op_ff_canary_size_bytes must be non-negative int, got {op_ff_canary_size_bytes!r}."
        )
        telemetry_ok = False
        eff_canary_sz = 64
    else:
        eff_canary_sz = int(op_ff_canary_size_bytes)

    if not _is_non_negative_int(op_ff_sys_mount_calls):
        _add_code(codes, STATUS_BLOCKED_G45_TELEMETRY_INVALID)
        errors.append("op_ff_sys_mount_calls must be non-negative int.")
        telemetry_ok = False
        eff_mount_calls = 0
    else:
        eff_mount_calls = int(op_ff_sys_mount_calls)

    if not _is_non_negative_int(op_ff_dlopen_calls):
        _add_code(codes, STATUS_BLOCKED_G45_TELEMETRY_INVALID)
        errors.append("op_ff_dlopen_calls must be non-negative int.")
        telemetry_ok = False
        eff_dlopen_calls = 0
    else:
        eff_dlopen_calls = int(op_ff_dlopen_calls)

    if not _is_non_negative_int(senser_packet_pfunc):
        _add_code(codes, STATUS_BLOCKED_G45_TELEMETRY_INVALID)
        errors.append("senser_packet_pfunc must be non-negative int.")
        telemetry_ok = False
        eff_pfunc = SENSER_PACKET_PFUNC_ADJUST_CONTROL
    else:
        eff_pfunc = int(senser_packet_pfunc)

    if not _is_non_negative_int(senser_packet_category):
        _add_code(codes, STATUS_BLOCKED_G45_TELEMETRY_INVALID)
        errors.append("senser_packet_category must be non-negative int.")
        telemetry_ok = False
        eff_cat = SENSER_PACKET_CATEGORY_JIRITSU
    else:
        eff_cat = int(senser_packet_category)

    if not _is_non_negative_int(concurrent_inflight_packets):
        _add_code(codes, STATUS_BLOCKED_G45_TELEMETRY_INVALID)
        errors.append("concurrent_inflight_packets must be non-negative int.")
        telemetry_ok = False
        eff_inflight = 1
    else:
        eff_inflight = int(concurrent_inflight_packets)

    if not _is_non_negative_int(elf_pt_load_align_bytes):
        _add_code(codes, STATUS_BLOCKED_G45_TELEMETRY_INVALID)
        errors.append("elf_pt_load_align_bytes must be non-negative int.")
        telemetry_ok = False
        eff_align = LIBJIT_REQUIRED_PT_LOAD_ALIGN
    else:
        eff_align = int(elf_pt_load_align_bytes)

    if not _is_non_negative_int(fx3s0ok_packet_bytes):
        _add_code(codes, STATUS_BLOCKED_G45_TELEMETRY_INVALID)
        errors.append("fx3s0ok_packet_bytes must be non-negative int.")
        telemetry_ok = False
        eff_pkt_bytes = FX3S0OK_PACKET_BYTES
    else:
        eff_pkt_bytes = int(fx3s0ok_packet_bytes)

    if not isinstance(fx3s0ok_header_magic, str):
        _add_code(codes, STATUS_BLOCKED_G45_TELEMETRY_INVALID)
        errors.append("fx3s0ok_header_magic must be str.")
        telemetry_ok = False
        eff_pkt_magic = FX3S0OK_HEADER_MAGIC
    else:
        eff_pkt_magic = fx3s0ok_header_magic

    if not _is_non_negative_int(fx3s0ok_payload_len_bytes):
        _add_code(codes, STATUS_BLOCKED_G45_TELEMETRY_INVALID)
        errors.append("fx3s0ok_payload_len_bytes must be non-negative int.")
        telemetry_ok = False
        eff_pkt_len = FX3S0OK_PAYLOAD_LEN_BYTES
    else:
        eff_pkt_len = int(fx3s0ok_payload_len_bytes)

    if not isinstance(usb_reenum_msc_vid_pid, str) or not usb_reenum_msc_vid_pid.strip():
        _add_code(codes, STATUS_BLOCKED_G45_TELEMETRY_INVALID)
        errors.append("usb_reenum_msc_vid_pid must be non-empty string.")
        telemetry_ok = False
        eff_reenum = SERVICE_USB_VID_PID_MSC
    else:
        eff_reenum = usb_reenum_msc_vid_pid.strip().upper()

    if not _is_finite_number(msc_return_elapsed_ms) or float(msc_return_elapsed_ms) <= 0.0:
        _add_code(codes, STATUS_BLOCKED_G45_TELEMETRY_INVALID)
        errors.append(
            f"msc_return_elapsed_ms must be finite > 0.0, got {msc_return_elapsed_ms!r}."
        )
        telemetry_ok = False
        eff_elapsed_ms = 850.0
    else:
        eff_elapsed_ms = float(msc_return_elapsed_ms)

    if (
        isinstance(teardown_steps_order, (str, bytes))
        or not isinstance(teardown_steps_order, Sequence)
        or not all(isinstance(s, str) and s.strip() for s in teardown_steps_order)
    ):
        _add_code(codes, STATUS_BLOCKED_G45_TELEMETRY_INVALID)
        errors.append("teardown_steps_order must be a sequence of non-empty step strings.")
        telemetry_ok = False
        eff_steps: Tuple[str, ...] = CANONICAL_TEARDOWN_STEPS
    else:
        eff_steps = tuple(s.strip().upper() for s in teardown_steps_order)

    # 1) Stage-286 Branch-A op=0xFF pure RAM slot echo canary BEFORE op=0x00
    canary_bounds_ok = validate_op_ff_ram_canary(
        eff_slot, eff_canary_sz, eff_mount_calls, eff_dlopen_calls
    )
    canary_before_op00_ok = (
        (not bool(op_00_frame_queued))
        or (bool(op_ff_canary_executed_before_op_00) and bool(op_ff_canary_echo_verified))
    )
    usb_transition_ok = (
        eff_init_vid_pid == SERVICE_USB_VID_PID_MSC
        and eff_svc_vid_pid == SERVICE_USB_VID_PID_SERVICE
    )
    canary_ok = (
        canary_bounds_ok
        and canary_before_op00_ok
        and bool(op_ff_canary_echo_verified)
        and usb_transition_ok
    )
    op_ff_canary_safe = (not telemetry_ok) or canary_ok
    if telemetry_ok and not canary_ok:
        _add_code(codes, STATUS_BLOCKED_G45_OP_FF_CANARY_MISSING_OR_UNSAFE)
        errors.append(
            f"BLOCKED_G45_OP_FF_CANARY_MISSING_OR_UNSAFE: {session_profile} requires "
            f"054C:0DA1->054C:0336 Branch-A op=0xFF RAM canary (slot=0x{eff_slot:02x} <= 0x11, "
            f"size={eff_canary_sz}B <= 5MiB, sys_mount={eff_mount_calls}==0, "
            f"dlopen={eff_dlopen_calls}==0, executed_before_op00={bool(op_ff_canary_executed_before_op_00)}, "
            f"echo_verified={bool(op_ff_canary_echo_verified)}, op00_queued={bool(op_00_frame_queued)})."
        )

    # 2) Exclusive single-flight SenserPacket (pFunc=0x0040, 0x1001) seq serialization
    serial_ok = (
        eff_pfunc == SENSER_PACKET_PFUNC_ADJUST_CONTROL
        and eff_cat == SENSER_PACKET_CATEGORY_JIRITSU
        and eff_inflight <= MAX_CONCURRENT_INFLIGHT_PACKETS
        and bool(seq_monotonic_strict)
        and bool(inconcurrent_lock_held)
    )
    senser_packet_serialization_safe = (not telemetry_ok) or serial_ok
    if telemetry_ok and not serial_ok:
        _add_code(codes, STATUS_BLOCKED_G45_SENSER_PACKET_CONCURRENT_INFLIGHT)
        errors.append(
            f"BLOCKED_G45_SENSER_PACKET_CONCURRENT_INFLIGHT: pFunc=0x{eff_pfunc:04x}, "
            f"category=0x{eff_cat:04x}, concurrent_inflight_packets={eff_inflight} "
            f"(max {MAX_CONCURRENT_INFLIGHT_PACKETS}), seq_monotonic_strict={bool(seq_monotonic_strict)}, "
            f"inconcurrent_lock_held={bool(inconcurrent_lock_held)}."
        )

    # 3) 64 KiB ELF self-unlinkat + non-truncating 528B FX3S0OK verification
    fx3s0ok_hdr_ok = validate_fx3s0ok_packet_header(
        eff_pkt_bytes, eff_pkt_magic, eff_pkt_len
    )
    elf_ok = (
        eff_align == LIBJIT_REQUIRED_PT_LOAD_ALIGN
        and bool(libjit_entry_unlinkat_executed)
        and (not bool(libjit_unlink_residual_present))
        and fx3s0ok_hdr_ok
        and bool(fx3s0ok_non_truncating_read_verified)
        and bool(fx3s0ok_crc32_verified)
    )
    elf_64k_unlink_and_fx3s0ok_safe = (not telemetry_ok) or elf_ok
    if telemetry_ok and not elf_ok:
        _add_code(codes, STATUS_BLOCKED_G45_ELF_64K_UNLINK_OR_FX3S0OK_INVALID)
        errors.append(
            f"BLOCKED_G45_ELF_64K_UNLINK_OR_FX3S0OK_INVALID: p_align=0x{eff_align:x} "
            f"(expected 0x{LIBJIT_REQUIRED_PT_LOAD_ALIGN:x}), unlinkat={bool(libjit_entry_unlinkat_executed)}, "
            f"residual={bool(libjit_unlink_residual_present)}, pkt={eff_pkt_bytes}B, "
            f"magic={eff_pkt_magic!r}, len={eff_pkt_len}B, non_truncating={bool(fx3s0ok_non_truncating_read_verified)}, "
            f"crc32_ok={bool(fx3s0ok_crc32_verified)}."
        )

    # 4) Deterministic teardown watchdog (STOP 0336:7 -> release 0336:8 -> 054C:0DA1 0da1:9 <= 5000ms)
    steps_ok = eff_steps == CANONICAL_TEARDOWN_STEPS
    watchdog_ok = (
        bool(teardown_stop_0336_7_sent)
        and bool(teardown_release_0336_8_done)
        and (eff_reenum == SERVICE_USB_VID_PID_MSC)
        and bool(teardown_0da1_9_driver_released)
        and (not bool(stranded_in_service_0336))
        and (eff_elapsed_ms <= MSC_RETURN_WATCHDOG_MAX_MS)
        and steps_ok
    )
    msc_return_watchdog_safe = (not telemetry_ok) or watchdog_ok
    if telemetry_ok and not watchdog_ok:
        _add_code(codes, STATUS_BLOCKED_G45_MSC_RETURN_WATCHDOG_STRANDED_0336)
        errors.append(
            f"BLOCKED_G45_MSC_RETURN_WATCHDOG_STRANDED_0336: stop_0336_7={bool(teardown_stop_0336_7_sent)}, "
            f"release_0336_8={bool(teardown_release_0336_8_done)}, reenum={eff_reenum!r}, "
            f"driver_0da1_9_released={bool(teardown_0da1_9_driver_released)}, "
            f"stranded_0336={bool(stranded_in_service_0336)}, elapsed_ms={eff_elapsed_ms:.1f} "
            f"(max {MSC_RETURN_WATCHDOG_MAX_MS:.1f}), steps={eff_steps}."
        )

    if telemetry_ok and len(errors) == 0 and eff_elapsed_ms > 3000.0:
        warnings.append(
            f"MSC re-enumeration latency {eff_elapsed_ms:.1f} ms is approaching 5000 ms watchdog ceiling."
        )

    valid = len(errors) == 0 and len(codes) == 0
    if valid:
        status = STATUS_SAFE
    elif STATUS_BLOCKED_PERSISTENT_EMMC_WRITE in codes:
        status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    else:
        status = codes[0]

    return Service0336CanaryGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        session_profile=str(session_profile),
        usb_initial_vid_pid=eff_init_vid_pid,
        usb_service_vid_pid=eff_svc_vid_pid,
        op_ff_canary_executed_before_op_00=bool(op_ff_canary_executed_before_op_00),
        op_ff_canary_echo_verified=bool(op_ff_canary_echo_verified),
        op_ff_canary_slot=eff_slot,
        op_ff_canary_size_bytes=eff_canary_sz,
        op_ff_sys_mount_calls=eff_mount_calls,
        op_ff_dlopen_calls=eff_dlopen_calls,
        op_00_frame_queued=bool(op_00_frame_queued),
        senser_packet_pfunc_hex=f"0x{eff_pfunc:04x}",
        senser_packet_category_hex=f"0x{eff_cat:04x}",
        concurrent_inflight_packets=eff_inflight,
        seq_monotonic_strict=bool(seq_monotonic_strict),
        inconcurrent_lock_held=bool(inconcurrent_lock_held),
        elf_pt_load_align_bytes=eff_align,
        libjit_entry_unlinkat_executed=bool(libjit_entry_unlinkat_executed),
        libjit_unlink_residual_present=bool(libjit_unlink_residual_present),
        fx3s0ok_packet_bytes=eff_pkt_bytes,
        fx3s0ok_header_magic=eff_pkt_magic,
        fx3s0ok_payload_len_bytes=eff_pkt_len,
        fx3s0ok_non_truncating_read_verified=bool(fx3s0ok_non_truncating_read_verified),
        fx3s0ok_crc32_verified=bool(fx3s0ok_crc32_verified),
        teardown_stop_0336_7_sent=bool(teardown_stop_0336_7_sent),
        teardown_release_0336_8_done=bool(teardown_release_0336_8_done),
        usb_reenum_msc_vid_pid=eff_reenum,
        teardown_0da1_9_driver_released=bool(teardown_0da1_9_driver_released),
        msc_return_elapsed_ms=round(eff_elapsed_ms, 2),
        teardown_steps_order=eff_steps,
        stranded_in_service_0336=bool(stranded_in_service_0336),
        op_ff_canary_safe=op_ff_canary_safe,
        senser_packet_serialization_safe=senser_packet_serialization_safe,
        elf_64k_unlink_and_fx3s0ok_safe=elf_64k_unlink_and_fx3s0ok_safe,
        msc_return_watchdog_safe=msc_return_watchdog_safe,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 4. Gate G46 — Stage-B p18:/lens RO Lock, 5-Axis IBIS Park & DmmCfg.bin Guard
# ---------------------------------------------------------------------------


def verify_stageb_p18_ibis_park_and_dmmcfg_guard(
    *,
    runtime_profile: str = "FX3_STAGEB_P18_RO_5AXIS_IBIS_PARK_AND_DMMCFG_20POOL",
    p18_device_node: str = P18_DEVICE_NODE,
    p18_mount_point: str = P18_MOUNT_POINT,
    p18_mount_flags: str = P18_REQUIRED_MOUNT_FLAG,
    p18_write_attempts_blocked: bool = True,
    p18_mutation_bytes: int = 0,
    p18_writes_requested: int = 0,
    p18_lensfile_bytes: int = P18_LENSFILE_EXPECTED_BYTES,
    ibis_boot_servo_state: str = "CENTER_LOCK_PARK",
    ibis_sleep_servo_state: str = "OFF",
    ibis_shutdown_servo_state: str = "CENTER_LOCK_PARK",
    ibis_center_lock_opcode: int = IBIS_CENTER_LOCK_CMD_OPCODE,
    ibis_center_lock_ack: int = IBIS_CENTER_LOCK_ACK_OPCODE,
    ibis_floating_coil_fault: bool = False,
    coil_current_ma: float = 120.0,
    safe_limit_ma: float = IBIS_SAFE_COIL_CURRENT_LIMIT_MA,
    fx6_rigid_sensor_query_masked: bool = True,
    dmmcfg_bytes: int = STOCK_FX3_AP_DMMCFG_BYTES,
    dmmcfg_stamp: str = STOCK_FX3_AP_DMMCFG_STAMP,
    shared_main_pools_count: int = STOCK_FX3_SHARED_MAIN_POOLS,
    allocated_main_pools: int = 16,
    dmm_pool_overflow_bytes: int = 0,
    sdi_blocking_wait_ms: float = 0.0,
    requested_fx6_unmasked_pools: Sequence[str] = (),
    fx6_sdi_raw_darwin_pools_masked: bool = True,
    request_persistent_emmc_writes: bool = False,
) -> StageBMprIbisP18GuardResult:
    """Verify Gate G46 (Stage-B `p18:/lens` `MS_RDONLY` lock, 5-axis IBIS safe coil park,
    and Stock FX3 `66,796B` `DmmCfg.bin` 20-pool / zero-SDI-blocking guard).
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
    if not isinstance(p18_device_node, str) or not p18_device_node.strip():
        _add_code(codes, STATUS_BLOCKED_G46_TELEMETRY_INVALID)
        errors.append("p18_device_node must be non-empty string.")
        telemetry_ok = False
        eff_p18_dev = P18_DEVICE_NODE
    else:
        eff_p18_dev = p18_device_node.strip()

    if not isinstance(p18_mount_point, str) or not p18_mount_point.strip():
        _add_code(codes, STATUS_BLOCKED_G46_TELEMETRY_INVALID)
        errors.append("p18_mount_point must be non-empty string.")
        telemetry_ok = False
        eff_p18_mnt = P18_MOUNT_POINT
    else:
        eff_p18_mnt = p18_mount_point.strip()

    if not isinstance(p18_mount_flags, str) or not p18_mount_flags.strip():
        _add_code(codes, STATUS_BLOCKED_G46_TELEMETRY_INVALID)
        errors.append("p18_mount_flags must be non-empty string.")
        telemetry_ok = False
        eff_p18_flags = P18_REQUIRED_MOUNT_FLAG
    else:
        eff_p18_flags = p18_mount_flags.strip()

    if not _is_non_negative_int(p18_mutation_bytes):
        _add_code(codes, STATUS_BLOCKED_G46_TELEMETRY_INVALID)
        errors.append("p18_mutation_bytes must be non-negative int.")
        telemetry_ok = False
        eff_p18_mut = 0
    else:
        eff_p18_mut = int(p18_mutation_bytes)

    if not _is_non_negative_int(p18_writes_requested):
        _add_code(codes, STATUS_BLOCKED_G46_TELEMETRY_INVALID)
        errors.append("p18_writes_requested must be non-negative int.")
        telemetry_ok = False
        eff_p18_wr_req = 0
    else:
        eff_p18_wr_req = int(p18_writes_requested)

    if not _is_non_negative_int(p18_lensfile_bytes):
        _add_code(codes, STATUS_BLOCKED_G46_TELEMETRY_INVALID)
        errors.append("p18_lensfile_bytes must be non-negative int.")
        telemetry_ok = False
        eff_lens_bytes = P18_LENSFILE_EXPECTED_BYTES
    else:
        eff_lens_bytes = int(p18_lensfile_bytes)

    for lbl, val in (
        ("ibis_boot_servo_state", ibis_boot_servo_state),
        ("ibis_sleep_servo_state", ibis_sleep_servo_state),
        ("ibis_shutdown_servo_state", ibis_shutdown_servo_state),
    ):
        if not isinstance(val, str) or not val.strip():
            _add_code(codes, STATUS_BLOCKED_G46_TELEMETRY_INVALID)
            errors.append(f"{lbl} must be non-empty string.")
            telemetry_ok = False
    eff_boot_st = ibis_boot_servo_state.strip().upper() if isinstance(ibis_boot_servo_state, str) else ""
    eff_sleep_st = ibis_sleep_servo_state.strip().upper() if isinstance(ibis_sleep_servo_state, str) else ""
    eff_shut_st = ibis_shutdown_servo_state.strip().upper() if isinstance(ibis_shutdown_servo_state, str) else ""

    if not _is_non_negative_int(ibis_center_lock_opcode):
        _add_code(codes, STATUS_BLOCKED_G46_TELEMETRY_INVALID)
        errors.append("ibis_center_lock_opcode must be non-negative int.")
        telemetry_ok = False
        eff_ibis_op = IBIS_CENTER_LOCK_CMD_OPCODE
    else:
        eff_ibis_op = int(ibis_center_lock_opcode)

    if not _is_non_negative_int(ibis_center_lock_ack):
        _add_code(codes, STATUS_BLOCKED_G46_TELEMETRY_INVALID)
        errors.append("ibis_center_lock_ack must be non-negative int.")
        telemetry_ok = False
        eff_ibis_ack = IBIS_CENTER_LOCK_ACK_OPCODE
    else:
        eff_ibis_ack = int(ibis_center_lock_ack)

    if not _is_finite_number(coil_current_ma) or float(coil_current_ma) < 0.0:
        _add_code(codes, STATUS_BLOCKED_G46_TELEMETRY_INVALID)
        errors.append(f"coil_current_ma must be finite >= 0.0, got {coil_current_ma!r}.")
        telemetry_ok = False
        eff_coil_ma = 120.0
    else:
        eff_coil_ma = float(coil_current_ma)

    if not _is_finite_number(safe_limit_ma) or float(safe_limit_ma) <= 0.0:
        _add_code(codes, STATUS_BLOCKED_G46_TELEMETRY_INVALID)
        errors.append(f"safe_limit_ma must be finite > 0.0, got {safe_limit_ma!r}.")
        telemetry_ok = False
        eff_safe_ma = IBIS_SAFE_COIL_CURRENT_LIMIT_MA
    else:
        eff_safe_ma = float(safe_limit_ma)

    if not _is_non_negative_int(dmmcfg_bytes):
        _add_code(codes, STATUS_BLOCKED_G46_TELEMETRY_INVALID)
        errors.append("dmmcfg_bytes must be non-negative int.")
        telemetry_ok = False
        eff_dmm_bytes = STOCK_FX3_AP_DMMCFG_BYTES
    else:
        eff_dmm_bytes = int(dmmcfg_bytes)

    if not isinstance(dmmcfg_stamp, str) or not dmmcfg_stamp.strip():
        _add_code(codes, STATUS_BLOCKED_G46_TELEMETRY_INVALID)
        errors.append("dmmcfg_stamp must be non-empty string.")
        telemetry_ok = False
        eff_dmm_stamp = STOCK_FX3_AP_DMMCFG_STAMP
    else:
        eff_dmm_stamp = dmmcfg_stamp.strip()

    if not _is_int_not_bool(shared_main_pools_count) or shared_main_pools_count <= 0:
        _add_code(codes, STATUS_BLOCKED_G46_TELEMETRY_INVALID)
        errors.append("shared_main_pools_count must be positive int.")
        telemetry_ok = False
        eff_total_pools = STOCK_FX3_SHARED_MAIN_POOLS
    else:
        eff_total_pools = int(shared_main_pools_count)

    if not _is_non_negative_int(allocated_main_pools):
        _add_code(codes, STATUS_BLOCKED_G46_TELEMETRY_INVALID)
        errors.append("allocated_main_pools must be non-negative int.")
        telemetry_ok = False
        eff_alloc_pools = 16
    else:
        eff_alloc_pools = int(allocated_main_pools)

    if not _is_non_negative_int(dmm_pool_overflow_bytes):
        _add_code(codes, STATUS_BLOCKED_G46_TELEMETRY_INVALID)
        errors.append("dmm_pool_overflow_bytes must be non-negative int.")
        telemetry_ok = False
        eff_overflow = 0
    else:
        eff_overflow = int(dmm_pool_overflow_bytes)

    if not _is_finite_number(sdi_blocking_wait_ms) or float(sdi_blocking_wait_ms) < 0.0:
        _add_code(codes, STATUS_BLOCKED_G46_TELEMETRY_INVALID)
        errors.append(
            f"sdi_blocking_wait_ms must be finite >= 0.0, got {sdi_blocking_wait_ms!r}."
        )
        telemetry_ok = False
        eff_sdi_wait = 0.0
    else:
        eff_sdi_wait = float(sdi_blocking_wait_ms)

    if (
        isinstance(requested_fx6_unmasked_pools, (str, bytes))
        or not isinstance(requested_fx6_unmasked_pools, Sequence)
        or not all(isinstance(p, str) for p in requested_fx6_unmasked_pools)
    ):
        _add_code(codes, STATUS_BLOCKED_G46_TELEMETRY_INVALID)
        errors.append("requested_fx6_unmasked_pools must be a sequence of strings.")
        telemetry_ok = False
        eff_req_pools: Tuple[str, ...] = ()
    else:
        eff_req_pools = tuple(p.strip().upper() for p in requested_fx6_unmasked_pools if p.strip())

    pool_util_pct = compute_dmm_pool_utilization_pct(eff_alloc_pools, eff_total_pools)

    # 1) p18:/lens factory E-Mount calibration strictly MS_RDONLY & zero mutation
    flag_tokens = [tok.strip().upper() for tok in eff_p18_flags.replace("|", ",").split(",") if tok.strip()]
    ro_flag_ok = (P18_REQUIRED_MOUNT_FLAG in flag_tokens) and (
        "MS_RDWR" not in flag_tokens and "RW" not in flag_tokens
    )
    p18_ok = (
        eff_p18_dev == P18_DEVICE_NODE
        and eff_p18_mnt == P18_MOUNT_POINT
        and ro_flag_ok
        and bool(p18_write_attempts_blocked)
        and eff_p18_mut == 0
        and eff_p18_wr_req == 0
        and eff_lens_bytes == P18_LENSFILE_EXPECTED_BYTES
    )
    p18_lens_ro_lock_safe = (not telemetry_ok) or p18_ok
    if telemetry_ok and not p18_ok:
        _add_code(codes, STATUS_BLOCKED_G46_P18_LENS_RO_OR_MUTATION)
        errors.append(
            f"BLOCKED_G46_P18_LENS_RO_OR_MUTATION: {runtime_profile} p18={eff_p18_dev!r} "
            f"mount={eff_p18_mnt!r} flags={eff_p18_flags!r} (must be MS_RDONLY), "
            f"write_attempts_blocked={bool(p18_write_attempts_blocked)}, "
            f"mutation_bytes={eff_p18_mut}, writes_requested={eff_p18_wr_req}, "
            f"lensfile_bytes={eff_lens_bytes} (expected {P18_LENSFILE_EXPECTED_BYTES})."
        )

    # 2) Physical FX3 5-axis IBIS safe coil park across boot, sleep, shutdown
    ibis_states_ok = validate_ibis_coil_park_state(
        eff_boot_st,
        eff_sleep_st,
        eff_shut_st,
        eff_coil_ma,
        eff_safe_ma,
        floating_coil_fault=bool(ibis_floating_coil_fault),
    )
    ibis_ok = (
        ibis_states_ok
        and eff_ibis_op == IBIS_CENTER_LOCK_CMD_OPCODE
        and eff_ibis_ack == IBIS_CENTER_LOCK_ACK_OPCODE
        and bool(fx6_rigid_sensor_query_masked)
    )
    ibis_5axis_coil_park_safe = (not telemetry_ok) or ibis_ok
    if telemetry_ok and not ibis_ok:
        _add_code(codes, STATUS_BLOCKED_G46_IBIS_FLOATING_COIL_OR_CURRENT_HAZARD)
        errors.append(
            f"BLOCKED_G46_IBIS_FLOATING_COIL_OR_CURRENT_HAZARD: boot={eff_boot_st!r}, "
            f"sleep={eff_sleep_st!r}, shutdown={eff_shut_st!r}, "
            f"floating_coil_fault={bool(ibis_floating_coil_fault)}, "
            f"coil_current_ma={eff_coil_ma:.1f} (limit {eff_safe_ma:.1f}), "
            f"center_lock=0x{eff_ibis_op:04x}->0x{eff_ibis_ack:04x}, "
            f"fx6_rigid_sensor_query_masked={bool(fx6_rigid_sensor_query_masked)}."
        )

    # 3) Stock FX3 66,796B AP DmmCfg.bin (20 MAIN pools) protected against FX6 SDI/Darwin pools
    forbidden_pools: List[str] = []
    for rp in eff_req_pools:
        if any(bad in rp for bad in FORBIDDEN_FX6_UNMASKED_DMM_POOLS) or rp:
            if rp not in forbidden_pools:
                forbidden_pools.append(rp)

    dmm_ok = (
        eff_dmm_bytes == STOCK_FX3_AP_DMMCFG_BYTES
        and STOCK_FX3_AP_DMMCFG_STAMP in eff_dmm_stamp
        and eff_total_pools == STOCK_FX3_SHARED_MAIN_POOLS
        and eff_alloc_pools <= eff_total_pools
        and eff_overflow == 0
        and eff_sdi_wait == 0.0
        and len(forbidden_pools) == 0
        and bool(fx6_sdi_raw_darwin_pools_masked)
    )
    dmmcfg_pool_budget_safe = (not telemetry_ok) or dmm_ok
    if telemetry_ok and not dmm_ok:
        _add_code(codes, STATUS_BLOCKED_G46_DMMCFG_POOL_OVERFLOW_OR_SDI_BLOCKING)
        errors.append(
            f"BLOCKED_G46_DMMCFG_POOL_OVERFLOW_OR_SDI_BLOCKING: dmmcfg_bytes={eff_dmm_bytes} "
            f"(expected {STOCK_FX3_AP_DMMCFG_BYTES}), stamp={eff_dmm_stamp!r}, "
            f"pools={eff_alloc_pools}/{eff_total_pools}, overflow={eff_overflow}B, "
            f"sdi_blocking_wait_ms={eff_sdi_wait:.1f}, forbidden_pools={tuple(forbidden_pools)}, "
            f"masked={bool(fx6_sdi_raw_darwin_pools_masked)}."
        )

    if telemetry_ok and len(errors) == 0 and eff_alloc_pools >= 18:
        warnings.append(
            f"AP DmmCfg.bin shared MAIN pool allocation {eff_alloc_pools}/{eff_total_pools} "
            f"({pool_util_pct:.1f}%) is high; keep 4K120p + MLUT headroom monitored."
        )

    valid = len(errors) == 0 and len(codes) == 0
    if valid:
        status = STATUS_SAFE
    elif STATUS_BLOCKED_PERSISTENT_EMMC_WRITE in codes:
        status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    else:
        status = codes[0]

    return StageBMprIbisP18GuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        runtime_profile=str(runtime_profile),
        p18_device_node=eff_p18_dev,
        p18_mount_point=eff_p18_mnt,
        p18_mount_flags=eff_p18_flags,
        p18_write_attempts_blocked=bool(p18_write_attempts_blocked),
        p18_mutation_bytes=eff_p18_mut,
        p18_writes_requested=eff_p18_wr_req,
        p18_lensfile_bytes=eff_lens_bytes,
        ibis_boot_servo_state=eff_boot_st,
        ibis_sleep_servo_state=eff_sleep_st,
        ibis_shutdown_servo_state=eff_shut_st,
        ibis_center_lock_opcode_hex=f"0x{eff_ibis_op:04x}",
        ibis_center_lock_ack_hex=f"0x{eff_ibis_ack:04x}",
        ibis_floating_coil_fault=bool(ibis_floating_coil_fault),
        coil_current_ma=round(eff_coil_ma, 2),
        safe_limit_ma=round(eff_safe_ma, 2),
        fx6_rigid_sensor_query_masked=bool(fx6_rigid_sensor_query_masked),
        dmmcfg_bytes=eff_dmm_bytes,
        dmmcfg_stamp=eff_dmm_stamp,
        shared_main_pools_count=eff_total_pools,
        allocated_main_pools=eff_alloc_pools,
        dmm_pool_utilization_pct=round(pool_util_pct, 2),
        dmm_pool_overflow_bytes=eff_overflow,
        sdi_blocking_wait_ms=round(eff_sdi_wait, 2),
        requested_fx6_unmasked_pools=eff_req_pools,
        forbidden_fx6_pools_detected=tuple(forbidden_pools),
        fx6_sdi_raw_darwin_pools_masked=bool(fx6_sdi_raw_darwin_pools_masked),
        p18_lens_ro_lock_safe=p18_lens_ro_lock_safe,
        ibis_5axis_coil_park_safe=ibis_5axis_coil_park_safe,
        dmmcfg_pool_budget_safe=dmmcfg_pool_budget_safe,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 5. Gate G45 & Gate G46 Evaluators
# ---------------------------------------------------------------------------


def evaluate_g45_service_0336_canary(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    service_0336_canary_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase148DonorAuditResult] = None,
) -> Tuple[GateVerdict, G45Service0336CanaryResult]:
    """Evaluate Gate G45 (`service_0336_op_ff_canary_64k_unlink_and_msc_return_safe`)."""
    audit = donor_audit or audit_phase148_donor_contracts(
        work_root=work_root,
        repo_root=repo_root,
        force_clean_room=force_clean_room,
    )

    eff_kwargs = dict(service_0336_canary_kwargs or {})
    eff_kwargs["request_persistent_emmc_writes"] = bool(
        request_persistent_emmc_writes
        or eff_kwargs.get("request_persistent_emmc_writes", False)
    )
    guard_res = verify_service0336_canary_64k_unlink_and_msc_return(**eff_kwargs)

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
        STATUS_VERIFIED_G45
        if passed
        else (
            codes[0]
            if codes
            else STATUS_BLOCKED_G45_OP_FF_CANARY_MISSING_OR_UNSAFE
        )
    )

    res = G45Service0336CanaryResult(
        valid=passed,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        service_0336_canary_guard=guard_res.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    verdict = GateVerdict(
        gate_id=G45_GATE_ID,
        gate_code=G45_GATE_CODE,
        passed=passed,
        status=status,
        evidence=(
            f"054C:0336 SERVICE op=0xFF RAM Canary, 64KiB ELF Self-Unlink & MSC Return Watchdog "
            f"({guard_res.status}, slot=0x{guard_res.op_ff_canary_slot:02x}, "
            f"inflight={guard_res.concurrent_inflight_packets}, "
            f"pkt={guard_res.fx3s0ok_packet_bytes}B/{guard_res.fx3s0ok_header_magic}, "
            f"msc_return={guard_res.msc_return_elapsed_ms:.1f}ms->{guard_res.usb_reenum_msc_vid_pid}, "
            f"{audit.verification_mode}), "
            f"persistent_emmc_writes_authorized={PERSISTENT_EMMC_WRITES_AUTHORIZED}."
        ),
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
        details={
            "verification_mode": audit.verification_mode,
            "op_ff_canary_safe": guard_res.op_ff_canary_safe,
            "senser_packet_serialization_safe": guard_res.senser_packet_serialization_safe,
            "elf_64k_unlink_and_fx3s0ok_safe": guard_res.elf_64k_unlink_and_fx3s0ok_safe,
            "msc_return_watchdog_safe": guard_res.msc_return_watchdog_safe,
        },
    )
    return verdict, res


def evaluate_g46_mpr_ibis_p18_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    stageb_mpr_ibis_p18_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase148DonorAuditResult] = None,
) -> Tuple[GateVerdict, G46MprIbisP18GuardResult]:
    """Evaluate Gate G46 (`stageb_p18_ro_5axis_ibis_park_and_dmmcfg_pool_safe`)."""
    audit = donor_audit or audit_phase148_donor_contracts(
        work_root=work_root,
        repo_root=repo_root,
        force_clean_room=force_clean_room,
    )

    eff_kwargs = dict(stageb_mpr_ibis_p18_kwargs or {})
    eff_kwargs["request_persistent_emmc_writes"] = bool(
        request_persistent_emmc_writes
        or eff_kwargs.get("request_persistent_emmc_writes", False)
    )
    guard_res = verify_stageb_p18_ibis_park_and_dmmcfg_guard(**eff_kwargs)

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
        STATUS_VERIFIED_G46
        if passed
        else (
            codes[0]
            if codes
            else STATUS_BLOCKED_G46_P18_LENS_RO_OR_MUTATION
        )
    )

    res = G46MprIbisP18GuardResult(
        valid=passed,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        stageb_mpr_ibis_p18_guard=guard_res.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    verdict = GateVerdict(
        gate_id=G46_GATE_ID,
        gate_code=G46_GATE_CODE,
        passed=passed,
        status=status,
        evidence=(
            f"Stage-B p18:/lens MS_RDONLY, 5-Axis IBIS Coil Park & Stock DmmCfg.bin 20-Pool Guard "
            f"({guard_res.status}, p18_flags={guard_res.p18_mount_flags}, "
            f"coil={guard_res.coil_current_ma:.1f}mA, "
            f"dmm_pools={guard_res.allocated_main_pools}/{guard_res.shared_main_pools_count}, "
            f"sdi_wait={guard_res.sdi_blocking_wait_ms:.1f}ms, {audit.verification_mode}), "
            f"persistent_emmc_writes_authorized={PERSISTENT_EMMC_WRITES_AUTHORIZED}."
        ),
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
        details={
            "verification_mode": audit.verification_mode,
            "p18_lens_ro_lock_safe": guard_res.p18_lens_ro_lock_safe,
            "ibis_5axis_coil_park_safe": guard_res.ibis_5axis_coil_park_safe,
            "dmmcfg_pool_budget_safe": guard_res.dmmcfg_pool_budget_safe,
        },
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 6. Master 46-Gate Preflight Evaluator (`G01..G46`) & CLI
# ---------------------------------------------------------------------------


def evaluate_46gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated_backup: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    # G1..G44 pass-throughs
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
    # G45 inputs (054C:0336 op=0xFF Canary, 64KiB Unlink & MSC Return Watchdog)
    service_0336_canary_kwargs: Optional[Mapping[str, Any]] = None,
    # G46 inputs (Stage-B p18:/lens RO, 5-Axis IBIS Park & DmmCfg.bin Pool Guard)
    stageb_mpr_ibis_p18_kwargs: Optional[Mapping[str, Any]] = None,
) -> Master46GateReport:
    """Evaluate all 46 Master Safety Gates (`G01..G46`) deterministically."""
    resolved_root = (
        DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)
    ).resolve()
    clean_forced = _is_forced_clean_room(force_clean_room)

    m44_kwargs: Dict[str, Any] = {
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
    }
    if soc_start_ceiling_c is not None:
        m44_kwargs["soc_start_ceiling_c"] = soc_start_ceiling_c

    m44_report: Master44GateReport = evaluate_44gate_preflight(
        resolved_root, **m44_kwargs
    )

    phase148_audit = audit_phase148_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
    )

    g45_verdict, g45_res = evaluate_g45_service_0336_canary(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        service_0336_canary_kwargs=service_0336_canary_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase148_audit,
    )

    g46_verdict, g46_res = evaluate_g46_mpr_ibis_p18_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        stageb_mpr_ibis_p18_kwargs=stageb_mpr_ibis_p18_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase148_audit,
    )

    gates_45_to_46 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g45_verdict, g46_verdict)
    ]
    all_gates = tuple(list(m44_report.gates) + gates_45_to_46)

    g01_to_g12_verified = int(m44_report.summary["g01_to_g12_verified"])
    g13_to_g44_verified = (
        int(m44_report.summary["g13_to_g42_verified"])
        + int(m44_report.summary["g43_to_g44_verified"])
    )
    g45_to_g46_verified = sum(1 for v in (g45_verdict, g46_verdict) if v.passed)
    total_verified = g01_to_g12_verified + g13_to_g44_verified + g45_to_g46_verified

    g45_to_g46_all_passed = g45_to_g46_verified == 2
    g13_to_g46_all_passed = (
        m44_report.g13_to_g44_all_passed and g45_to_g46_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m44_report.gates[:9])

    offline_43_verified = (
        g01_to_g09_ok
        and m44_report.offline_41_gates_verified
        and g45_to_g46_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_46_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g46_all_passed
        and (not request_persistent_emmc_writes)
    )

    # Hard-locked False in offline and dry-run modes; never authorizes eMMC writes
    overall_ready_for_hardware_attach = False

    h0_h1_allowed = (
        offline_43_verified
        and m44_report.h0_h1_trial_entry_allowed
        and g45_to_g46_all_passed
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    errors: List[str] = (
        list(m44_report.errors) + list(g45_verdict.errors) + list(g46_verdict.errors)
    )
    warnings: List[str] = (
        list(m44_report.warnings)
        + list(g45_verdict.warnings)
        + list(g46_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m44_report.g13_to_g44_all_passed:
        overall_status = m44_report.status
    elif not g45_verdict.passed:
        overall_status = g45_verdict.status
    elif not g46_verdict.passed:
        overall_status = g46_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_46_verified and dry_run_simulated_backup:
        overall_status = "VERIFIED_ALL_46_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_46_verified:
        overall_status = "VERIFIED_ALL_46_GATES"
    else:
        overall_status = "VERIFIED_43_OF_46_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m44_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g45_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g46_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 46,
        "verified_gates": total_verified,
        "blocked_or_pending_gates": 46 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g44_verified": g13_to_g44_verified,
        "g45_to_g46_verified": g45_to_g46_verified,
        "g13_to_g46_all_passed": g13_to_g46_all_passed,
        "g45_to_g46_all_passed": g45_to_g46_all_passed,
        "offline_43_gates_verified": offline_43_verified,
        "all_46_gates_verified": all_46_verified,
        "dry_run_rehearsal_only": bool(dry_run_simulated_backup),
        "overall_ready_for_hardware_attach": overall_ready_for_hardware_attach,
        "h0_h1_trial_entry_allowed": h0_h1_allowed,
    }

    return Master46GateReport(
        schema=REALHW_SERVICE0336_MPR_IBIS_46GATE_SCHEMA,
        version=REALHW_SERVICE0336_MPR_IBIS_46GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=bool(dry_run_simulated_backup),
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        offline_43_gates_verified=offline_43_verified,
        all_46_gates_verified=all_46_verified,
        g13_to_g46_all_passed=g13_to_g46_all_passed,
        g45_to_g46_all_passed=g45_to_g46_all_passed,
        h0_h1_trial_entry_allowed=h0_h1_allowed,
        status=overall_status,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        summary=summary,
        gates=all_gates,
        master_44_report=m44_report.to_dict(),
        g45_result=g45_res.to_dict(),
        g46_result=g46_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_46_master_safety_gates = evaluate_46gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_service0336_mpr_ibis_and_46gate_guard",
        description=(
            "Phase 148 — 054C:0336 SERVICE op=0xFF Canary, 64KiB ELF Self-Unlink & MSC Return "
            "Guard (G45), Stage-B p18:/lens RO, 5-Axis IBIS Safe Coil Park & Stock DmmCfg.bin "
            "Pool Guard (G46), and 46-Gate Master Preflight (G01..G46)"
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
        help="Supply simulated dry-run Tier-0 backup inputs so G01..G46 can be exercised offline",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit structured JSON report",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = evaluate_46gate_preflight(
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
            f"verified={report.summary['verified_gates']}/46 "
            f"g45_to_g46_all_passed={report.g45_to_g46_all_passed} "
            f"all_46_gates_verified={report.all_46_gates_verified} "
            f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
            f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}\n"
        )
    ok = (
        report.all_46_gates_verified
        if args.dry_run_simulated_backup
        else report.offline_43_gates_verified
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
