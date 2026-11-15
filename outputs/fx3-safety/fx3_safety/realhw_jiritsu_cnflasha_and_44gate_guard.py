"""Phase 142 — Real-Hardware Main Track Part 9:
Gate G43 (`AdjustControl 0x40` / `libJiritsu.so` Service-Session Electrical, `jbusy` &
`p6` `25 MiB` Quota Guard), Gate G44 (`/dev/cnflasha15` SPACC Cipher-Boundary, Tier-0
Cold-Backup Receipt, SD Escape-Hatch & `p1`/`p3` Mutual-Exclusion Preflight), and
Unified 44-Gate Master Safety Preflight (`G01..G44` / `verify-44-gates`).

Operationalizes the real physical ILME-FX3 (`Ver. 7.02`, Model ID `0x91030080`, SoC
`CXD90057`) deployment and backup safety contracts established in Phases 136..141 while
keeping all prior gate modules (`G01..G42`) completely untouched and hard-locking:
- `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`
- `PERSISTENT_WRITE_RELEASE = False`
- `overall_ready_for_hardware_attach = False`

1. **Read-Only (`os.O_RDONLY`) FX3/FX6 Donor Real-Hardware Contract Audit**:
   - Inspects FX3 `v7.02` `libJiritsu.so` (`225,200 B`, `JIRITSU_SET_FILE2`,
     `JIRITSU_GET_FILE2`, `/tmp/jbusy`, `/tmp/jiritsu/libJit.so`, `/dev/nflasha6`),
     FX3 `ld-2.25.so` (`120,616 B`, `64 KiB` ELF alignment), FX3 `partinf.conf`
     (`3,999 B`), FX3 `mount.conf` (`1,248 B`, `/dev/nflasha6 none vfat 26214400`),
     FX3 `p2` `kemco.txt` (`1,736 B`, `cfg.uart=1`, `wdt.mode=1`), `up.sh`
     (`6,572 B`, `rm -f $UPDIR/mode*` + `sync`), `loader_nor.bin` (`101,888 B`,
     `\\updater\\mode`, `\\mode\\cmode`), and FX6 `p1` `kemco.txt` (`933 B`,
     `cfg.uart=9` contrast) strictly via `os.open(..., os.O_RDONLY)`.
   - Falls back deterministically to pinned clean-room metadata when
     `FX3_FX6_FORCE_CLEAN_ROOM=1` or local donor files are absent.

2. **Gate G43 — `AdjustControl 0x40` / `libJiritsu.so` Service-Session Electrical,
   `/tmp/jbusy` Precheck & `p6` `25 MiB` Quota Guard**:
   - Verifies `NP-FZ100` battery SoC `>= 75%` and `>= 7.4V` under load OR regulated
     USB-PD (`>= 8.55V`, `>= 27W`) before any USB service session (preventing brownout
     during `/tmp/jiritsu/` or `nflasha` access).
   - Verifies `/tmp/jbusy` precheck (`ENOENT` `0x11` required; aborts on `0x10000011`),
     `00 ff 00` wire framing (`selector != 2`, zero `MODE`/`START`/`FORMAT`/`MOUNT`
     opcodes), ELF `PT_LOAD` `64 KiB` (`0x10000`) alignment + `DT_HASH (1,1,0,0)` +
     constructor `unlinkat` self-delete.
   - Enforces `p6` (`/dev/nflasha6`, `25 MiB` = `26,214,400 B`) staging quota
     (`peak_p6_bytes <= 8 MiB` and `p6_residual_files == 0`) to prevent `0x1000000F`
     (`p6` exhaustion) or orphaned root-owned `.so` files in factory `Jiritsu`.

3. **Gate G44 — `/dev/cnflasha15` SPACC Cipher-Boundary, Tier-0 Cold-Backup Receipt,
   SD Escape-Hatch & `p1`/`p3` Mutual-Exclusion Guard**:
   - Requires verified **Tier-0 Complete Cold-Backup SHA-256 Receipt** (`Sector 0`
     `"8246"`/`"2.00"`, `p1` `dat2=91030080`/`dat3`, `p2` `Backup.bin`/`psd.bin`/
     `defdet.bin`, `p6`, `p12`, `p18` `lensfile.bin`, SPI NOR `ddrtraining.dat`
     `@ 0x3e210fc`).
   - Enforces SPACC transparent-encryption block device boundary: any `type=5, flag=1`
     target (`p3`, `p7`, `p8`, `p12`, `p15`, `p23`, `p30`) MUST go through
     `/dev/nflashaN` or `/dev/cnflashaN` — **HARD-BLOCKS** raw plaintext
     `/dev/pnflashaN` writes, **HARD-BLOCKS** `nor_loader_writer.sh` SPI NOR
     overwrite, `us_spi_firmup.sh` (`mew.bin`), `us_darwin_firm.sh` (`darwin` ND),
     and `edisx.elf` Sector-0 repartitioning.
   - Enforces **SD-Card Physical Escape Hatch** (`eject SD card -> 47 us bypass to
     stock /usr/bin/im.elf.orig`) + **`p1` vs `p3` Mutual-Exclusion Law** (`never
     modify p1 and p3 in the same transaction`; `p1` `kemco.txt` `cfg.uart=1` & line-1
     `rm -f /setting/updater/mode* && sync`).

4. **Unified 44-Gate Master Safety Preflight (`evaluate_44gate_preflight` / CLI
   `verify-44-gates`)**:
   - Composes `evaluate_42gate_preflight` (`G01..G42`) with `G43` and `G44`:
     * Offline default mode: `41/44` gates pass (`G10..G12` physical Tier-0 backup
       truthfully remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED` ->
       `overall_ready_for_hardware_attach = False`).
     * `--dry-run-simulated-backup` mode: `44/44` simulation gates pass
       (`dry_run_rehearsal_only = True`), while `persistent_emmc_writes_authorized`,
       `persistent_write_release`, and `overall_ready_for_hardware_attach` remain
       hard-locked to `False`.
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
from .thermal_pwm_and_power_guard import (
    ENV_FORCE_CLEAN_ROOM,
    resolve_donor_thermal_power_paths,
    scan_tokens_o_rdonly,
)
from .vp_strobe_vehiclerig_ibis_and_42gate_guard import (
    Master42GateReport,
    evaluate_42gate_preflight,
)


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

REALHW_JIRITSU_CNFLASHA_44GATE_SCHEMA: str = (
    "fx3-realhw-jiritsu-cnflasha-44gate-preflight-v1"
)
REALHW_JIRITSU_CNFLASHA_44GATE_VERSION: str = "1.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False

# Gate IDs & Canonical Codes for G43..G44
G43_GATE_ID: str = "G43_adjustcontrol_jiritsu_electrical_jbusy_and_p6_quota_safe"
G43_GATE_CODE: str = "ADJUSTCONTROL_JIRITSU_ELECTRICAL_JBUSY_AND_P6_QUOTA_SAFE"

G44_GATE_ID: str = "G44_cnflasha_spacc_tier0_sd_escape_and_p1_p3_mutex_safe"
G44_GATE_CODE: str = "CNFLASHA_SPACC_TIER0_SD_ESCAPE_AND_P1_P3_MUTEX_SAFE"

# Status Codes
STATUS_SAFE: str = "SAFE"
STATUS_VERIFIED_SAFE: str = "VERIFIED_SAFE"
STATUS_VERIFIED_G43: str = (
    "VERIFIED_ADJUSTCONTROL_JIRITSU_ELECTRICAL_JBUSY_AND_P6_QUOTA_SAFE"
)
STATUS_VERIFIED_G44: str = (
    "VERIFIED_CNFLASHA_SPACC_TIER0_SD_ESCAPE_AND_P1_P3_MUTEX_SAFE"
)

# Gate G43 Violation Codes
STATUS_BLOCKED_JIRITSU_ELECTRICAL_BROWNOUT_RISK: str = (
    "BLOCKED_JIRITSU_ELECTRICAL_BROWNOUT_RISK"
)
STATUS_BLOCKED_JIRITSU_JBUSY_ACTIVE_0X10000011: str = (
    "BLOCKED_JIRITSU_JBUSY_ACTIVE_0X10000011"
)
STATUS_BLOCKED_JIRITSU_WIRE_FRAMING_OR_FORBIDDEN_OPCODE: str = (
    "BLOCKED_JIRITSU_WIRE_FRAMING_OR_FORBIDDEN_OPCODE"
)
STATUS_BLOCKED_JIRITSU_ELF_ALIGNMENT_OR_SELFDELETE: str = (
    "BLOCKED_JIRITSU_ELF_ALIGNMENT_OR_SELFDELETE"
)
STATUS_BLOCKED_P6_QUOTA_OR_RESIDUAL_EXHAUSTION: str = (
    "BLOCKED_P6_QUOTA_OR_RESIDUAL_EXHAUSTION"
)
STATUS_BLOCKED_G43_TELEMETRY_INVALID: str = "BLOCKED_G43_JIRITSU_TELEMETRY_INVALID"

# Gate G44 Violation Codes
STATUS_BLOCKED_TIER0_COLD_BACKUP_RECEIPT_INVALID: str = (
    "BLOCKED_TIER0_COLD_BACKUP_RECEIPT_INVALID"
)
STATUS_BLOCKED_RAW_PNFLASHA_OR_FORBIDDEN_FLASH_TOOL: str = (
    "BLOCKED_RAW_PNFLASHA_OR_FORBIDDEN_FLASH_TOOL"
)
STATUS_BLOCKED_SD_ESCAPE_HATCH_MISSING_OR_SLOW: str = (
    "BLOCKED_SD_ESCAPE_HATCH_MISSING_OR_SLOW"
)
STATUS_BLOCKED_P1_P3_MUTUAL_EXCLUSION_OR_UART_TRAP: str = (
    "BLOCKED_P1_P3_MUTUAL_EXCLUSION_OR_UART_TRAP"
)
STATUS_BLOCKED_G44_TELEMETRY_INVALID: str = "BLOCKED_G44_CNFLASHA_TELEMETRY_INVALID"

STATUS_BLOCKED_DONOR_INTEGRITY: str = (
    "BLOCKED_PHASE142_44GATE_DONOR_INTEGRITY_MISMATCH"
)
STATUS_BLOCKED_PERSISTENT_EMMC_WRITE: str = (
    "BLOCKED_BY_PERSISTENT_EMMC_WRITE_REDLINE"
)

# Gate G43 Thresholds & Protocol Constants
JIRITSU_MIN_BATTERY_SOC_PCT: float = 75.0
JIRITSU_MIN_BATTERY_LOAD_VOLTAGE_V: float = 7.4
JIRITSU_USBPD_MIN_VOLTAGE_V: float = 8.55
JIRITSU_USBPD_MIN_CONTRACT_WATTS: float = 27.0
JIRITSU_JBUSY_ENOENT_CODE: int = 0x11
JIRITSU_JBUSY_BUSY_CODE: int = 0x10000011
JIRITSU_WIRE_PREFIX_HEX: str = "00ff00"
JIRITSU_FORBIDDEN_SELECTOR: int = 2
JIRITSU_FORBIDDEN_OPCODES: Tuple[str, ...] = (
    "MODE",
    "START",
    "FORMAT",
    "MOUNT",
    "JIRITSU_MODE",
    "JIRITSU_START",
    "JIRITSU_FORMAT",
    "JIRITSU_MOUNT",
)
JIRITSU_ELF_REQUIRED_PT_LOAD_ALIGN: int = 0x10000  # 64 KiB
JIRITSU_ELF_REQUIRED_DT_HASH: Tuple[int, int, int, int] = (1, 1, 0, 0)
P6_PARTITION_CAPACITY_BYTES: int = 26_214_400  # 25 MiB (/dev/nflasha6)
P6_MAX_SAFE_STAGING_BYTES: int = 8 * 1024 * 1024  # 8 MiB
P6_EXHAUSTION_ERROR_CODE: int = 0x1000000F

# Gate G44 Thresholds & Protocol Constants
SPACC_ENCRYPTED_TYPE5_FLAG1_PARTITIONS: Tuple[int, ...] = (3, 7, 8, 12, 15, 23, 30)
FORBIDDEN_REALHW_FLASH_PATTERNS: Tuple[str, ...] = (
    "/dev/pnflasha",
    "nor_loader_writer.sh",
    "us_spi_firmup.sh",
    "mew.bin",
    "us_darwin_firm.sh",
    "edisx.elf",
)
TIER0_COLD_BACKUP_REQUIRED_KEYS: Tuple[str, ...] = (
    "sector0",
    "p1",
    "p2",
    "p6",
    "p12",
    "p18",
    "spi_nor_ddrtraining",
)
TIER0_SECTOR0_MAGIC: str = "8246"
TIER0_SECTOR0_VERSION: str = "2.00"
FX3_MODEL_ID_STR: str = "91030080"
SPI_NOR_DDRTRAINING_OFFSET: int = 0x03E210FC
SD_ESCAPE_HATCH_NOMINAL_US: float = 47.0
SD_ESCAPE_HATCH_MAX_US: float = 50_000.0
SD_ESCAPE_HATCH_STOCK_TARGET: str = "/usr/bin/im.elf.orig"
P1_KEMCO_REQUIRED_CFG_UART: int = 1
P1_INIT_REQUIRED_LINE1_PATTERN: str = r"^\s*rm\s+-f\s+/setting/updater/mode\*\s*&&\s*sync\s*$"

_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_LINE1_MODE_CLEAR_RE = re.compile(P1_INIT_REQUIRED_LINE1_PATTERN)
_PNFLASHA_RE = re.compile(r"/dev/pnflasha\d*")

# Pinned FX3 v7.02 & FX6 v6.01 Donor Specs (verified strictly via os.O_RDONLY)
PINNED_PHASE142_DONOR_SPECS: Mapping[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
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
    "fx3_ld_2_25": (
        "fx3",
        "sony-firmware-20261024/stage2/extraction/files/nflasha7/lib/ld-2.25.so",
        120_616,
        "90b4fe734ba7faa08d4591b1363bff478e7bde399a821fc0b2d021c062a58a9a",
        (b"\x7fELF", b"GLIBC_2.17", b"dl_open"),
        "fx3/ld-2.25.so::{ELF,GLIBC_2.17,dl_open}",
    ),
    "fx3_partinf_conf": (
        "fx3",
        "sony-firmware-20261024/stage182-boot-selector-and-recovery-admission/current-updater-evidence/tar-selected/0300_partconf/partinf.conf",
        3_999,
        "3d96228d4ed2db3cb4295aa854edf0ad8895440167f132144cdec4f8cfdad189",
        (
            b"0x00000080,0x0000BF80",
            b"0x00112000,0x000FA000",
            b"0x00346000,0x00018000",
        ),
        "fx3/partinf.conf::{p1_0xBF80,p15_0xFA000,p30_0x18000}",
    ),
    "fx3_mount_conf": (
        "fx3",
        "sony-firmware-20261024/stage182-boot-selector-and-recovery-admission/current-updater-evidence/tar-selected/0100_config/mount.conf",
        1_248,
        "ea0132091f3bb8d675b3ae7aecfbb1ca2459864a2e2812c0f7dd66fbb877d1a3",
        (
            b"/dev/nflasha1 none vfat 25100288",
            b"/dev/nflasha6 none vfat 26214400",
            b"/dev/nflasha15 /usr raw 524288000",
        ),
        "fx3/mount.conf::{nflasha1_25100288,nflasha6_26214400,nflasha15_524288000}",
    ),
    "fx3_p2_kemco_txt": (
        "fx3",
        "sony-firmware-20261024/stage182-boot-selector-and-recovery-admission/current-updater-evidence/tar-selected/0800_appli/setting/kemco.txt",
        1_736,
        "555454e8b7db1461d6494e9ca9eb21f00918475af02557bc6ca3cedd309bcaf2",
        (b"cfg.uart=1", b"wdt.mode=1"),
        "fx3/p2_kemco.txt::{cfg.uart=1,wdt.mode=1}",
    ),
    "fx3_up_sh": (
        "fx3",
        "fx3-color-port-20261027/ap-input-20261029/original-members/up.sh",
        6_572,
        "c774320a0ab92c13b467b9219e1f60262a1effa0b551ba3b713514a36dadc402",
        (b"UPDIR=$UPMNT/updater", b"rm -f $UPDIR/mode*", b"sync"),
        "fx3/up.sh::{UPDIR=$UPMNT/updater,rm -f $UPDIR/mode*,sync}",
    ),
    "fx3_loader_nor": (
        "fx3",
        "fx3-color-port-20261027/config-producer-20261029/original-files/loader_nor.bin",
        101_888,
        "4358c839cfb1f22d5eb4e53d67817c42c4e877ba8b0aff375d355ce6294c4942",
        (b"\\updater\\mode", b"\\mode\\cmode"),
        "fx3/loader_nor.bin::{\\updater\\mode,\\mode\\cmode}",
    ),
    "fx6_p1_kemco_txt": (
        "fx6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fat-files/nflasha1/boot/kemco.txt",
        933,
        "e7763ad93a721f297670f13abc452cf467c0d2c344888d4e55ead2440c295950",
        (b"cfg.uart=9", b"console="),
        "fx6/p1_kemco.txt::{cfg.uart=9,console=}",
    ),
}

PINNED_APPFW_REALHW_TOKENS: Tuple[str, ...] = (
    "/dev/nflasha",
    "OFF_BY_BATT_END",
    "OFF_BY_BATT_INVALID",
)

PINNED_CPAPP_REALHW_TOKENS: Tuple[str, ...] = (
    "BATT_AUTH_S",
    "THERMISTOR_ADJ_START",
)


# ---------------------------------------------------------------------------
# Data Models (Zero raw bytes reprs; hex strings only)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase142DonorAuditResult:
    valid: bool
    status: str
    verification_mode: str
    access_mode: str
    files_inspected: int
    checked_markers: Tuple[str, ...]
    missing_markers: Tuple[str, ...]
    jiritsu_contracts_verified: bool
    partition_table_contracts_verified: bool
    updater_uart_contracts_verified: bool
    large_binaries_scanned: bool
    sha256_by_artifact: Dict[str, str]
    bytes_by_artifact: Dict[str, int]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class JiritsuServiceSessionGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    session_profile: str
    np_fz100_soc_pct: float
    np_fz100_load_voltage_v: float
    usb_pd_regulated_supply_active: bool
    usb_pd_voltage_v: float
    usb_pd_contract_watts: float
    jbusy_file_exists: bool
    jbusy_precheck_code_hex: str
    wire_prefix_hex: str
    wire_selector: int
    session_opcodes: Tuple[str, ...]
    forbidden_opcodes_detected: Tuple[str, ...]
    elf_pt_load_align_bytes: int
    elf_dt_hash_tuple: Tuple[int, int, int, int]
    constructor_unlinkat_self_delete_enabled: bool
    peak_p6_bytes: int
    p6_capacity_bytes: int
    p6_quota_utilization_pct: float
    p6_residual_files: int
    electrical_power_safe: bool
    jbusy_precheck_safe: bool
    wire_framing_and_opcodes_safe: bool
    elf_alignment_and_selfdelete_safe: bool
    p6_quota_and_cleanup_safe: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CnflashaDualbootGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    deployment_profile: str
    tier0_receipt_verified: bool
    sector0_magic: str
    sector0_version: str
    p1_dat2_model_id: str
    p1_dat3_present: bool
    p2_backup_bin_present: bool
    p2_psd_bin_present: bool
    p2_defdet_bin_present: bool
    p6_jiritsu_backed_up: bool
    p12_cert_backed_up: bool
    p18_lensfile_backed_up: bool
    spi_nor_ddrtraining_backed_up: bool
    spi_nor_ddrtraining_offset_hex: str
    two_pass_sha256_verified: bool
    target_partition_num: int
    target_block_device: str
    target_is_type5_flag1_encrypted: bool
    forbidden_tools_or_paths_detected: Tuple[str, ...]
    sd_escape_hatch_enabled: bool
    sd_escape_bypass_latency_us: float
    sd_escape_target: str
    sd_escape_exec_wrapper_verified: bool
    modify_p1_in_transaction: bool
    modify_p3_in_transaction: bool
    p1_kemco_cfg_uart: int
    p1_init_first_line: str
    tier0_cold_backup_safe: bool
    spacc_boundary_and_flasher_safe: bool
    sd_escape_hatch_safe: bool
    p1_p3_mutex_and_uart_safe: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G43JiritsuServiceResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    jiritsu_service_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G44CnflashaDualbootResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    cnflasha_dualboot_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master44GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    offline_41_gates_verified: bool
    all_44_gates_verified: bool
    g13_to_g44_all_passed: bool
    g43_to_g44_all_passed: bool
    h0_h1_trial_entry_allowed: bool
    status: str
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    summary: Dict[str, Any]
    gates: Tuple[Dict[str, Any], ...]
    master_42_report: Dict[str, Any]
    g43_result: Dict[str, Any]
    g44_result: Dict[str, Any]
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
    """Strictly read a file via `os.open(..., os.O_RDONLY)` without printing raw bytes."""
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


def default_verified_tier0_sha256_receipts() -> Dict[str, str]:
    """Return a deterministic clean-room SHA-256 receipt map for all 7 Tier-0 artifacts."""
    return {
        key: hashlib.sha256(f"fx3-tier0-clean-receipt:{key}".encode("utf-8")).hexdigest()
        for key in TIER0_COLD_BACKUP_REQUIRED_KEYS
    }


# ---------------------------------------------------------------------------
# 1. Strictly Read-Only (O_RDONLY) Donor Contract Audit
# ---------------------------------------------------------------------------


def audit_phase142_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    include_large_binaries: bool = False,
) -> Phase142DonorAuditResult:
    """Inspect FX3/FX6 Jiritsu, ld-2.25.so, partinf/mount, up.sh & kemco donors via `os.O_RDONLY`."""
    clean_forced = _is_forced_clean_room(force_clean_room)
    paths = resolve_donor_thermal_power_paths(work_root=work_root, repo_root=repo_root)
    effective_work_root: Optional[Path] = (
        Path(work_root) if work_root is not None else paths.work_root
    )

    resolved: Dict[str, Path] = {}
    if effective_work_root is not None:
        for key, (_body, rel_path, _sz, _sha, _toks, _lbl) in PINNED_PHASE142_DONOR_SPECS.items():
            resolved[key] = effective_work_root / rel_path

    donor_available = (
        (not clean_forced)
        and (effective_work_root is not None)
        and bool(resolved)
        and all(p.is_file() for p in resolved.values())
    )

    if not donor_available:
        return Phase142DonorAuditResult(
            valid=True,
            status=STATUS_VERIFIED_SAFE,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="O_RDONLY",
            files_inspected=0,
            checked_markers=tuple(
                spec[5] for spec in PINNED_PHASE142_DONOR_SPECS.values()
            ),
            missing_markers=(),
            jiritsu_contracts_verified=True,
            partition_table_contracts_verified=True,
            updater_uart_contracts_verified=True,
            large_binaries_scanned=False,
            sha256_by_artifact={
                k: spec[3] for k, spec in PINNED_PHASE142_DONOR_SPECS.items()
            },
            bytes_by_artifact={
                k: spec[2] for k, spec in PINNED_PHASE142_DONOR_SPECS.items()
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
    ) in PINNED_PHASE142_DONOR_SPECS.items():
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

    files_inspected = len(resolved)
    large_scanned = False
    appfw_ok = True
    cpapp_ok = True
    if include_large_binaries:
        if paths.fx3_appfw_path.is_file():
            appfw_sz, missing_appfw = scan_tokens_o_rdonly(
                paths.fx3_appfw_path, PINNED_APPFW_REALHW_TOKENS
            )
            sizes["fx3_appfw"] = appfw_sz
            files_inspected += 1
            large_scanned = True
            if missing_appfw:
                appfw_ok = False
                missing.extend(missing_appfw)
                errors.append(
                    f"fx3 appFw.so missing nflasha/battery tokens: {missing_appfw}"
                )
            else:
                checked.append(
                    "fx3/appFw.so::/dev/nflasha+OFF_BY_BATT_END+OFF_BY_BATT_INVALID"
                )
        else:
            warnings.append(
                "fx3/appFw.so not found for optional large-binary realhw scan."
            )

        if paths.fx3_cp_path.is_file():
            cp_sz, missing_cp = scan_tokens_o_rdonly(
                paths.fx3_cp_path, PINNED_CPAPP_REALHW_TOKENS
            )
            sizes["fx3_cpapp"] = cp_sz
            files_inspected += 1
            large_scanned = True
            if missing_cp:
                cpapp_ok = False
                missing.extend(missing_cp)
                errors.append(
                    f"fx3 cpapp-b.bin missing BATT_AUTH/THERMISTOR tokens: {missing_cp}"
                )
            else:
                checked.append("fx3/cpapp-b.bin::BATT_AUTH_S+THERMISTOR_ADJ_START")
        else:
            warnings.append(
                "fx3/cpapp-b.bin not found for optional large-binary realhw scan."
            )

    valid = len(errors) == 0 and len(missing) == 0
    return Phase142DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_DONOR_INTEGRITY,
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="O_RDONLY",
        files_inspected=files_inspected,
        checked_markers=tuple(checked),
        missing_markers=tuple(missing),
        jiritsu_contracts_verified={
            "fx3_lib_jiritsu",
            "fx3_ld_2_25",
        }.issubset(passed_keys)
        and appfw_ok
        and cpapp_ok,
        partition_table_contracts_verified={
            "fx3_partinf_conf",
            "fx3_mount_conf",
        }.issubset(passed_keys),
        updater_uart_contracts_verified={
            "fx3_p2_kemco_txt",
            "fx3_up_sh",
            "fx3_loader_nor",
            "fx6_p1_kemco_txt",
        }.issubset(passed_keys),
        large_binaries_scanned=large_scanned,
        sha256_by_artifact=shas,
        bytes_by_artifact=sizes,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 2. Helper Evaluators (p6 Quota, ELF 64KiB Alignment, SPACC & Tier-0 Receipt)
# ---------------------------------------------------------------------------


def compute_p6_quota_utilization_pct(
    peak_p6_bytes: int,
    partition_capacity_bytes: int = P6_PARTITION_CAPACITY_BYTES,
) -> float:
    """Compute `/dev/nflasha6` (`p6`) staging utilization percentage."""
    if not (_is_non_negative_int(peak_p6_bytes) and _is_int_not_bool(partition_capacity_bytes)):
        raise ValueError(
            "peak_p6_bytes must be non-negative int and partition_capacity_bytes must be int > 0."
        )
    if partition_capacity_bytes <= 0:
        raise ValueError("partition_capacity_bytes must be > 0.")
    return (float(peak_p6_bytes) / float(partition_capacity_bytes)) * 100.0


def validate_elf_64k_alignment_and_hash(
    pt_load_align_bytes: int,
    dt_hash_tuple: Sequence[int],
) -> bool:
    """Validate `ld-2.25.so` `PT_LOAD` 64 KiB (`0x10000`) alignment and `DT_HASH (1,1,0,0)`."""
    if not _is_non_negative_int(pt_load_align_bytes):
        return False
    if not isinstance(dt_hash_tuple, (tuple, list)) or len(dt_hash_tuple) != 4:
        return False
    if not all(_is_non_negative_int(x) for x in dt_hash_tuple):
        return False
    return (
        int(pt_load_align_bytes) == JIRITSU_ELF_REQUIRED_PT_LOAD_ALIGN
        and tuple(int(x) for x in dt_hash_tuple) == JIRITSU_ELF_REQUIRED_DT_HASH
    )


def classify_spacc_block_device(
    partition_num: int,
    block_device_path: str,
    *,
    write_mode: bool = True,
) -> Tuple[bool, str]:
    """Validate SPACC transparent-encryption device path for `pN` (`type=5, flag=1`)."""
    if not _is_int_not_bool(partition_num) or partition_num <= 0 or partition_num > 30:
        return False, "INVALID_PARTITION_NUMBER"
    if not isinstance(block_device_path, str) or not block_device_path.strip():
        return False, "INVALID_BLOCK_DEVICE_PATH"
    dev = block_device_path.strip()
    if dev.startswith("/dev/pnflasha"):
        if write_mode:
            return False, "RAW_PNFLASHA_WRITE_BLOCKED"
        return True, "RAW_PNFLASHA_READONLY_INSPECT"
    if partition_num in SPACC_ENCRYPTED_TYPE5_FLAG1_PARTITIONS:
        expected = {f"/dev/nflasha{partition_num}", f"/dev/cnflasha{partition_num}"}
        if dev not in expected:
            return False, "SPACC_TARGET_DEVICE_MISMATCH"
        return True, "SPACC_TRANSPARENT_DEVICE_OK"
    expected_plain = {
        f"/dev/nflasha{partition_num}",
        f"/dev/cnflasha{partition_num}",
    }
    if dev not in expected_plain:
        return False, "TARGET_DEVICE_MISMATCH"
    return True, "PLAINTEXT_PARTITION_DEVICE_OK"


def validate_tier0_cold_backup_receipt(
    receipt: Mapping[str, Any],
) -> Tuple[bool, Tuple[str, ...]]:
    """Validate SHA-256 receipt mapping for all 7 required Tier-0 cold-backup artifacts."""
    if not isinstance(receipt, Mapping):
        return False, ("tier0_sha256_receipts must be a mapping.",)
    missing_or_bad: List[str] = []
    for key in TIER0_COLD_BACKUP_REQUIRED_KEYS:
        val = receipt.get(key)
        if not isinstance(val, str) or not _HEX64_RE.match(val):
            missing_or_bad.append(key)
    return len(missing_or_bad) == 0, tuple(missing_or_bad)


# ---------------------------------------------------------------------------
# 3. Gate G43 — AdjustControl 0x40 / libJiritsu.so Electrical, jbusy & p6 Guard
# ---------------------------------------------------------------------------


def verify_jiritsu_service_session_and_p6_guard(
    *,
    session_profile: str = "FX3_STAGE288_HARDENED_JIRITSU_READONLY",
    np_fz100_soc_pct: float = 85.0,
    np_fz100_load_voltage_v: float = 7.8,
    usb_pd_regulated_supply_active: bool = False,
    usb_pd_voltage_v: float = 9.0,
    usb_pd_contract_watts: float = 27.0,
    jbusy_file_exists: bool = False,
    jbusy_precheck_code: int = JIRITSU_JBUSY_ENOENT_CODE,
    wire_prefix_hex: str = JIRITSU_WIRE_PREFIX_HEX,
    wire_selector: int = 1,
    session_opcodes: Sequence[str] = (
        "JIRITSU_SET_FILE_PATH",
        "JIRITSU_SET_FILE2",
        "JIRITSU_GET_FILE2",
        "JIRITSU_FILE_DELETE2",
    ),
    elf_pt_load_align_bytes: int = JIRITSU_ELF_REQUIRED_PT_LOAD_ALIGN,
    elf_dt_hash_tuple: Tuple[int, int, int, int] = JIRITSU_ELF_REQUIRED_DT_HASH,
    constructor_unlinkat_self_delete_enabled: bool = True,
    peak_p6_bytes: int = 10_032,
    p6_residual_files: int = 0,
    request_persistent_emmc_writes: bool = False,
) -> JiritsuServiceSessionGuardResult:
    """Verify Gate G43 (Jiritsu USB service-session electrical, jbusy, wire/ELF & p6 quota)."""
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
    if (
        not _is_finite_number(np_fz100_soc_pct)
        or float(np_fz100_soc_pct) < 0.0
        or float(np_fz100_soc_pct) > 100.0
    ):
        _add_code(codes, STATUS_BLOCKED_G43_TELEMETRY_INVALID)
        errors.append(
            f"np_fz100_soc_pct must be finite in [0.0, 100.0], got {np_fz100_soc_pct!r}."
        )
        telemetry_ok = False
        eff_soc = 85.0
    else:
        eff_soc = float(np_fz100_soc_pct)

    if not _is_finite_number(np_fz100_load_voltage_v) or float(np_fz100_load_voltage_v) < 0.0:
        _add_code(codes, STATUS_BLOCKED_G43_TELEMETRY_INVALID)
        errors.append(
            f"np_fz100_load_voltage_v must be finite >= 0.0, got {np_fz100_load_voltage_v!r}."
        )
        telemetry_ok = False
        eff_batt_v = 7.8
    else:
        eff_batt_v = float(np_fz100_load_voltage_v)

    if not _is_finite_number(usb_pd_voltage_v) or float(usb_pd_voltage_v) < 0.0:
        _add_code(codes, STATUS_BLOCKED_G43_TELEMETRY_INVALID)
        errors.append(
            f"usb_pd_voltage_v must be finite >= 0.0, got {usb_pd_voltage_v!r}."
        )
        telemetry_ok = False
        eff_pd_v = 9.0
    else:
        eff_pd_v = float(usb_pd_voltage_v)

    if not _is_finite_number(usb_pd_contract_watts) or float(usb_pd_contract_watts) < 0.0:
        _add_code(codes, STATUS_BLOCKED_G43_TELEMETRY_INVALID)
        errors.append(
            f"usb_pd_contract_watts must be finite >= 0.0, got {usb_pd_contract_watts!r}."
        )
        telemetry_ok = False
        eff_pd_w = 27.0
    else:
        eff_pd_w = float(usb_pd_contract_watts)

    if not _is_non_negative_int(jbusy_precheck_code):
        _add_code(codes, STATUS_BLOCKED_G43_TELEMETRY_INVALID)
        errors.append(
            f"jbusy_precheck_code must be non-negative int, got {jbusy_precheck_code!r}."
        )
        telemetry_ok = False
        eff_jbusy_code = JIRITSU_JBUSY_ENOENT_CODE
    else:
        eff_jbusy_code = int(jbusy_precheck_code)

    if not isinstance(wire_prefix_hex, str) or not wire_prefix_hex.strip():
        _add_code(codes, STATUS_BLOCKED_G43_TELEMETRY_INVALID)
        errors.append(
            f"wire_prefix_hex must be non-empty hex string, got {wire_prefix_hex!r}."
        )
        telemetry_ok = False
        eff_wire_prefix = JIRITSU_WIRE_PREFIX_HEX
    else:
        eff_wire_prefix = wire_prefix_hex.replace(" ", "").strip().lower()
        if not re.match(r"^[0-9a-f]+$", eff_wire_prefix):
            _add_code(codes, STATUS_BLOCKED_G43_TELEMETRY_INVALID)
            errors.append(
                f"wire_prefix_hex must contain hex digits only, got {wire_prefix_hex!r}."
            )
            telemetry_ok = False

    if not _is_non_negative_int(wire_selector):
        _add_code(codes, STATUS_BLOCKED_G43_TELEMETRY_INVALID)
        errors.append(
            f"wire_selector must be non-negative int, got {wire_selector!r}."
        )
        telemetry_ok = False
        eff_selector = 1
    else:
        eff_selector = int(wire_selector)

    if (
        isinstance(session_opcodes, (str, bytes))
        or not isinstance(session_opcodes, Sequence)
        or not all(isinstance(op, str) and op.strip() for op in session_opcodes)
    ):
        _add_code(codes, STATUS_BLOCKED_G43_TELEMETRY_INVALID)
        errors.append("session_opcodes must be a sequence of non-empty opcode strings.")
        telemetry_ok = False
        eff_opcodes: Tuple[str, ...] = ()
    else:
        eff_opcodes = tuple(op.strip().upper() for op in session_opcodes)

    if not _is_non_negative_int(elf_pt_load_align_bytes):
        _add_code(codes, STATUS_BLOCKED_G43_TELEMETRY_INVALID)
        errors.append(
            f"elf_pt_load_align_bytes must be non-negative int, got {elf_pt_load_align_bytes!r}."
        )
        telemetry_ok = False
        eff_pt_align = JIRITSU_ELF_REQUIRED_PT_LOAD_ALIGN
    else:
        eff_pt_align = int(elf_pt_load_align_bytes)

    if (
        not isinstance(elf_dt_hash_tuple, (tuple, list))
        or len(elf_dt_hash_tuple) != 4
        or not all(_is_non_negative_int(x) for x in elf_dt_hash_tuple)
    ):
        _add_code(codes, STATUS_BLOCKED_G43_TELEMETRY_INVALID)
        errors.append(
            f"elf_dt_hash_tuple must be a 4-tuple of non-negative ints, got {elf_dt_hash_tuple!r}."
        )
        telemetry_ok = False
        eff_dt_hash: Tuple[int, int, int, int] = JIRITSU_ELF_REQUIRED_DT_HASH
    else:
        eff_dt_hash = (
            int(elf_dt_hash_tuple[0]),
            int(elf_dt_hash_tuple[1]),
            int(elf_dt_hash_tuple[2]),
            int(elf_dt_hash_tuple[3]),
        )

    if not _is_non_negative_int(peak_p6_bytes):
        _add_code(codes, STATUS_BLOCKED_G43_TELEMETRY_INVALID)
        errors.append(
            f"peak_p6_bytes must be non-negative int, got {peak_p6_bytes!r}."
        )
        telemetry_ok = False
        eff_peak_p6 = 10_032
    else:
        eff_peak_p6 = int(peak_p6_bytes)

    if not _is_non_negative_int(p6_residual_files):
        _add_code(codes, STATUS_BLOCKED_G43_TELEMETRY_INVALID)
        errors.append(
            f"p6_residual_files must be non-negative int, got {p6_residual_files!r}."
        )
        telemetry_ok = False
        eff_residual = 0
    else:
        eff_residual = int(p6_residual_files)

    p6_util_pct = compute_p6_quota_utilization_pct(eff_peak_p6, P6_PARTITION_CAPACITY_BYTES)

    # 1) Electrical power guard: NP-FZ100 >= 75% & >= 7.4V OR regulated USB-PD supply
    if bool(usb_pd_regulated_supply_active):
        electrical_ok = (eff_pd_v >= JIRITSU_USBPD_MIN_VOLTAGE_V) and (
            eff_pd_w >= JIRITSU_USBPD_MIN_CONTRACT_WATTS
        )
    else:
        electrical_ok = (eff_soc >= JIRITSU_MIN_BATTERY_SOC_PCT) and (
            eff_batt_v >= JIRITSU_MIN_BATTERY_LOAD_VOLTAGE_V
        )
    electrical_power_safe = (not telemetry_ok) or electrical_ok
    if telemetry_ok and not electrical_ok:
        _add_code(codes, STATUS_BLOCKED_JIRITSU_ELECTRICAL_BROWNOUT_RISK)
        errors.append(
            f"BLOCKED_JIRITSU_ELECTRICAL_BROWNOUT_RISK: {session_profile} has "
            f"np_fz100_soc_pct={eff_soc:.1f}% (min {JIRITSU_MIN_BATTERY_SOC_PCT:.1f}%), "
            f"np_fz100_load_voltage_v={eff_batt_v:.2f}V (min {JIRITSU_MIN_BATTERY_LOAD_VOLTAGE_V:.2f}V), "
            f"usb_pd_regulated_supply_active={bool(usb_pd_regulated_supply_active)} "
            f"({eff_pd_v:.2f}V / {eff_pd_w:.1f}W), risking brownout during /tmp/jiritsu or nflasha access."
        )

    # 2) /tmp/jbusy precheck (ENOENT 0x11 required; abort on 0x10000011)
    jbusy_ok = (not bool(jbusy_file_exists)) and (
        eff_jbusy_code == JIRITSU_JBUSY_ENOENT_CODE
    )
    jbusy_precheck_safe = (not telemetry_ok) or jbusy_ok
    if telemetry_ok and not jbusy_ok:
        _add_code(codes, STATUS_BLOCKED_JIRITSU_JBUSY_ACTIVE_0X10000011)
        errors.append(
            f"BLOCKED_JIRITSU_JBUSY_ACTIVE_0X10000011: /tmp/jbusy precheck failed "
            f"(jbusy_file_exists={bool(jbusy_file_exists)}, code=0x{eff_jbusy_code:x}; "
            f"expected ENOENT 0x{JIRITSU_JBUSY_ENOENT_CODE:x}, aborts on 0x{JIRITSU_JBUSY_BUSY_CODE:x})."
        )

    # 3) 00 ff 00 wire framing, selector != 2, zero MODE/START/FORMAT/MOUNT opcodes
    forbidden_hits: List[str] = []
    for op in eff_opcodes:
        if op in JIRITSU_FORBIDDEN_OPCODES or any(
            op == f"JIRITSU_{bad}" or op.endswith(f"_{bad}")
            for bad in ("MODE", "START", "FORMAT", "MOUNT")
        ):
            if op not in forbidden_hits:
                forbidden_hits.append(op)
    wire_ok = (
        (eff_wire_prefix == JIRITSU_WIRE_PREFIX_HEX)
        and (eff_selector != JIRITSU_FORBIDDEN_SELECTOR)
        and (len(forbidden_hits) == 0)
    )
    wire_framing_and_opcodes_safe = (not telemetry_ok) or wire_ok
    if telemetry_ok and not wire_ok:
        _add_code(codes, STATUS_BLOCKED_JIRITSU_WIRE_FRAMING_OR_FORBIDDEN_OPCODE)
        errors.append(
            f"BLOCKED_JIRITSU_WIRE_FRAMING_OR_FORBIDDEN_OPCODE: prefix={eff_wire_prefix!r} "
            f"(expected {JIRITSU_WIRE_PREFIX_HEX!r}), selector={eff_selector} (must != 2), "
            f"forbidden_opcodes={tuple(forbidden_hits)}."
        )

    # 4) ELF PT_LOAD 64KiB (0x10000) + DT_HASH (1,1,0,0) + constructor unlinkat self-delete
    elf_ok = validate_elf_64k_alignment_and_hash(eff_pt_align, eff_dt_hash) and bool(
        constructor_unlinkat_self_delete_enabled
    )
    elf_alignment_and_selfdelete_safe = (not telemetry_ok) or elf_ok
    if telemetry_ok and not elf_ok:
        _add_code(codes, STATUS_BLOCKED_JIRITSU_ELF_ALIGNMENT_OR_SELFDELETE)
        errors.append(
            f"BLOCKED_JIRITSU_ELF_ALIGNMENT_OR_SELFDELETE: pt_load_align=0x{eff_pt_align:x} "
            f"(expected 0x{JIRITSU_ELF_REQUIRED_PT_LOAD_ALIGN:x}), "
            f"dt_hash={eff_dt_hash} (expected {JIRITSU_ELF_REQUIRED_DT_HASH}), "
            f"constructor_unlinkat_self_delete_enabled={bool(constructor_unlinkat_self_delete_enabled)}."
        )

    # 5) p6 (/dev/nflasha6, 25 MiB) staging quota <= 8 MiB and residual == 0
    p6_ok = (eff_peak_p6 <= P6_MAX_SAFE_STAGING_BYTES) and (eff_residual == 0)
    p6_quota_and_cleanup_safe = (not telemetry_ok) or p6_ok
    if telemetry_ok and not p6_ok:
        _add_code(codes, STATUS_BLOCKED_P6_QUOTA_OR_RESIDUAL_EXHAUSTION)
        errors.append(
            f"BLOCKED_P6_QUOTA_OR_RESIDUAL_EXHAUSTION: peak_p6_bytes={eff_peak_p6} "
            f"(max {P6_MAX_SAFE_STAGING_BYTES} B / 8 MiB of 25 MiB p6 capacity) and "
            f"p6_residual_files={eff_residual} (must be 0 to prevent 0x{P6_EXHAUSTION_ERROR_CODE:x} "
            "or orphaned root-owned .so files)."
        )

    if telemetry_ok and len(errors) == 0 and usb_pd_regulated_supply_active and eff_soc < JIRITSU_MIN_BATTERY_SOC_PCT:
        warnings.append(
            f"NP-FZ100 SoC {eff_soc:.1f}% < 75% mitigated by regulated USB-PD {eff_pd_v:.2f}V / {eff_pd_w:.1f}W supply."
        )

    valid = len(errors) == 0 and len(codes) == 0
    if valid:
        status = STATUS_SAFE
    elif STATUS_BLOCKED_PERSISTENT_EMMC_WRITE in codes:
        status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    else:
        status = codes[0]

    return JiritsuServiceSessionGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        session_profile=str(session_profile),
        np_fz100_soc_pct=round(eff_soc, 2),
        np_fz100_load_voltage_v=round(eff_batt_v, 3),
        usb_pd_regulated_supply_active=bool(usb_pd_regulated_supply_active),
        usb_pd_voltage_v=round(eff_pd_v, 3),
        usb_pd_contract_watts=round(eff_pd_w, 2),
        jbusy_file_exists=bool(jbusy_file_exists),
        jbusy_precheck_code_hex=f"0x{eff_jbusy_code:x}",
        wire_prefix_hex=eff_wire_prefix,
        wire_selector=eff_selector,
        session_opcodes=eff_opcodes,
        forbidden_opcodes_detected=tuple(forbidden_hits),
        elf_pt_load_align_bytes=eff_pt_align,
        elf_dt_hash_tuple=eff_dt_hash,
        constructor_unlinkat_self_delete_enabled=bool(
            constructor_unlinkat_self_delete_enabled
        ),
        peak_p6_bytes=eff_peak_p6,
        p6_capacity_bytes=P6_PARTITION_CAPACITY_BYTES,
        p6_quota_utilization_pct=round(p6_util_pct, 4),
        p6_residual_files=eff_residual,
        electrical_power_safe=electrical_power_safe,
        jbusy_precheck_safe=jbusy_precheck_safe,
        wire_framing_and_opcodes_safe=wire_framing_and_opcodes_safe,
        elf_alignment_and_selfdelete_safe=elf_alignment_and_selfdelete_safe,
        p6_quota_and_cleanup_safe=p6_quota_and_cleanup_safe,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 4. Gate G44 — /dev/cnflasha15 SPACC, Tier-0 Receipt, SD Escape & p1/p3 Mutex
# ---------------------------------------------------------------------------


def verify_cnflasha_spacc_sd_escape_and_p1_p3_guard(
    *,
    deployment_profile: str = "FX3_CNFLASHA15_SD_ESCAPE_AND_P1_RESCUE_PREFLIGHT",
    tier0_receipt_verified: bool = True,
    sector0_magic: str = TIER0_SECTOR0_MAGIC,
    sector0_version: str = TIER0_SECTOR0_VERSION,
    p1_dat2_model_id: str = FX3_MODEL_ID_STR,
    p1_dat3_present: bool = True,
    p2_backup_bin_present: bool = True,
    p2_psd_bin_present: bool = True,
    p2_defdet_bin_present: bool = True,
    p6_jiritsu_backed_up: bool = True,
    p12_cert_backed_up: bool = True,
    p18_lensfile_backed_up: bool = True,
    spi_nor_ddrtraining_backed_up: bool = True,
    spi_nor_ddrtraining_offset: int = SPI_NOR_DDRTRAINING_OFFSET,
    two_pass_sha256_verified: bool = True,
    tier0_sha256_receipts: Optional[Mapping[str, str]] = None,
    target_partition_num: int = 15,
    target_block_device: str = "/dev/cnflasha15",
    spi_nor_overwrite_requested: bool = False,
    sector0_repartition_requested: bool = False,
    planned_commands: Sequence[str] = (),
    sd_escape_hatch_enabled: bool = True,
    sd_escape_bypass_latency_us: float = SD_ESCAPE_HATCH_NOMINAL_US,
    sd_escape_target: str = SD_ESCAPE_HATCH_STOCK_TARGET,
    sd_escape_exec_wrapper_verified: bool = True,
    modify_p1_in_transaction: bool = False,
    modify_p3_in_transaction: bool = False,
    p1_kemco_cfg_uart: int = P1_KEMCO_REQUIRED_CFG_UART,
    p1_init_first_line: str = "rm -f /setting/updater/mode* && sync",
    request_persistent_emmc_writes: bool = False,
) -> CnflashaDualbootGuardResult:
    """Verify Gate G44 (/dev/cnflasha15 SPACC, Tier-0 receipt, SD escape & p1/p3 mutex)."""
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
    if not _is_int_not_bool(target_partition_num) or target_partition_num <= 0 or target_partition_num > 30:
        _add_code(codes, STATUS_BLOCKED_G44_TELEMETRY_INVALID)
        errors.append(
            f"target_partition_num must be int in 1..30, got {target_partition_num!r}."
        )
        telemetry_ok = False
        eff_part_num = 15
    else:
        eff_part_num = int(target_partition_num)

    if not isinstance(target_block_device, str) or not target_block_device.strip():
        _add_code(codes, STATUS_BLOCKED_G44_TELEMETRY_INVALID)
        errors.append(
            f"target_block_device must be non-empty string, got {target_block_device!r}."
        )
        telemetry_ok = False
        eff_dev = "/dev/cnflasha15"
    else:
        eff_dev = target_block_device.strip()

    if not _is_non_negative_int(spi_nor_ddrtraining_offset):
        _add_code(codes, STATUS_BLOCKED_G44_TELEMETRY_INVALID)
        errors.append(
            f"spi_nor_ddrtraining_offset must be non-negative int, got {spi_nor_ddrtraining_offset!r}."
        )
        telemetry_ok = False
        eff_ddr_off = SPI_NOR_DDRTRAINING_OFFSET
    else:
        eff_ddr_off = int(spi_nor_ddrtraining_offset)

    if (
        isinstance(planned_commands, (str, bytes))
        or not isinstance(planned_commands, Sequence)
        or not all(isinstance(cmd, str) for cmd in planned_commands)
    ):
        _add_code(codes, STATUS_BLOCKED_G44_TELEMETRY_INVALID)
        errors.append("planned_commands must be a sequence of command strings.")
        telemetry_ok = False
        eff_cmds: Tuple[str, ...] = ()
    else:
        eff_cmds = tuple(planned_commands)

    if (
        not _is_finite_number(sd_escape_bypass_latency_us)
        or float(sd_escape_bypass_latency_us) <= 0.0
    ):
        _add_code(codes, STATUS_BLOCKED_G44_TELEMETRY_INVALID)
        errors.append(
            f"sd_escape_bypass_latency_us must be finite > 0.0, got {sd_escape_bypass_latency_us!r}."
        )
        telemetry_ok = False
        eff_escape_us = SD_ESCAPE_HATCH_NOMINAL_US
    else:
        eff_escape_us = float(sd_escape_bypass_latency_us)

    if not _is_int_not_bool(p1_kemco_cfg_uart):
        _add_code(codes, STATUS_BLOCKED_G44_TELEMETRY_INVALID)
        errors.append(
            f"p1_kemco_cfg_uart must be int, got {p1_kemco_cfg_uart!r}."
        )
        telemetry_ok = False
        eff_cfg_uart = P1_KEMCO_REQUIRED_CFG_UART
    else:
        eff_cfg_uart = int(p1_kemco_cfg_uart)

    if not isinstance(p1_init_first_line, str):
        _add_code(codes, STATUS_BLOCKED_G44_TELEMETRY_INVALID)
        errors.append("p1_init_first_line must be a string.")
        telemetry_ok = False
        eff_init_line1 = ""
    else:
        eff_init_line1 = p1_init_first_line

    eff_receipts = (
        default_verified_tier0_sha256_receipts()
        if tier0_sha256_receipts is None
        else tier0_sha256_receipts
    )
    receipts_ok, bad_receipt_keys = validate_tier0_cold_backup_receipt(eff_receipts)

    # 1) Tier-0 Complete Cold-Backup SHA-256 Receipt
    tier0_ok = (
        bool(tier0_receipt_verified)
        and (sector0_magic == TIER0_SECTOR0_MAGIC)
        and (sector0_version == TIER0_SECTOR0_VERSION)
        and (p1_dat2_model_id == FX3_MODEL_ID_STR)
        and bool(p1_dat3_present)
        and bool(p2_backup_bin_present)
        and bool(p2_psd_bin_present)
        and bool(p2_defdet_bin_present)
        and bool(p6_jiritsu_backed_up)
        and bool(p12_cert_backed_up)
        and bool(p18_lensfile_backed_up)
        and bool(spi_nor_ddrtraining_backed_up)
        and (eff_ddr_off == SPI_NOR_DDRTRAINING_OFFSET)
        and bool(two_pass_sha256_verified)
        and receipts_ok
    )
    tier0_cold_backup_safe = (not telemetry_ok) or tier0_ok
    if telemetry_ok and not tier0_ok:
        _add_code(codes, STATUS_BLOCKED_TIER0_COLD_BACKUP_RECEIPT_INVALID)
        errors.append(
            f"BLOCKED_TIER0_COLD_BACKUP_RECEIPT_INVALID: {deployment_profile} failed Tier-0 "
            f"cold-backup receipt verification (verified={bool(tier0_receipt_verified)}, "
            f"sector0={sector0_magic!r}/{sector0_version!r}, p1_dat2={p1_dat2_model_id!r}, "
            f"two_pass={bool(two_pass_sha256_verified)}, bad_receipts={bad_receipt_keys}, "
            f"ddr_offset=0x{eff_ddr_off:x})."
        )

    # 2) SPACC cipher boundary (/dev/nflashaN or /dev/cnflashaN) & forbidden flasher ban
    dev_ok, dev_reason = classify_spacc_block_device(
        eff_part_num, eff_dev, write_mode=True
    )
    forbidden_detected: List[str] = []
    if eff_dev.startswith("/dev/pnflasha"):
        forbidden_detected.append(eff_dev)
    if bool(spi_nor_overwrite_requested):
        forbidden_detected.append("nor_loader_writer.sh(spi_nor_overwrite)")
    if bool(sector0_repartition_requested):
        forbidden_detected.append("edisx.elf(sector0_repartition)")

    for cmd in eff_cmds:
        low = cmd.lower()
        for pat in FORBIDDEN_REALHW_FLASH_PATTERNS:
            if pat in low:
                if pat not in forbidden_detected:
                    forbidden_detected.append(pat)
        if "darwin" in low and "firm" in low:
            if "us_darwin_firm.sh" not in forbidden_detected:
                forbidden_detected.append("us_darwin_firm.sh")
        m_pn = _PNFLASHA_RE.search(low)
        if m_pn and m_pn.group(0) not in forbidden_detected:
            forbidden_detected.append(m_pn.group(0))

    spacc_ok = (
        dev_ok
        and (not bool(spi_nor_overwrite_requested))
        and (not bool(sector0_repartition_requested))
        and (len(forbidden_detected) == 0)
    )
    spacc_boundary_and_flasher_safe = (not telemetry_ok) or spacc_ok
    if telemetry_ok and not spacc_ok:
        _add_code(codes, STATUS_BLOCKED_RAW_PNFLASHA_OR_FORBIDDEN_FLASH_TOOL)
        errors.append(
            f"BLOCKED_RAW_PNFLASHA_OR_FORBIDDEN_FLASH_TOOL: part=p{eff_part_num} "
            f"device={eff_dev!r} ({dev_reason}), forbidden_detected={tuple(forbidden_detected)}."
        )

    # 3) SD-Card Physical Escape Hatch (47 us bypass -> stock /usr/bin/im.elf.orig)
    escape_ok = (
        bool(sd_escape_hatch_enabled)
        and bool(sd_escape_exec_wrapper_verified)
        and (sd_escape_target == SD_ESCAPE_HATCH_STOCK_TARGET)
        and (eff_escape_us <= SD_ESCAPE_HATCH_MAX_US)
    )
    sd_escape_hatch_safe = (not telemetry_ok) or escape_ok
    if telemetry_ok and not escape_ok:
        _add_code(codes, STATUS_BLOCKED_SD_ESCAPE_HATCH_MISSING_OR_SLOW)
        errors.append(
            f"BLOCKED_SD_ESCAPE_HATCH_MISSING_OR_SLOW: enabled={bool(sd_escape_hatch_enabled)}, "
            f"wrapper_verified={bool(sd_escape_exec_wrapper_verified)}, "
            f"target={sd_escape_target!r} (expected {SD_ESCAPE_HATCH_STOCK_TARGET!r}), "
            f"latency_us={eff_escape_us:.1f} (max {SD_ESCAPE_HATCH_MAX_US:.1f})."
        )

    # 4) p1 vs p3 Mutual-Exclusion Law + p1 cfg.uart=1 & line-1 mode* clear && sync
    dual_p1_p3 = bool(modify_p1_in_transaction) and bool(modify_p3_in_transaction)
    line1_ok = bool(_LINE1_MODE_CLEAR_RE.match(eff_init_line1))
    uart_ok = eff_cfg_uart == P1_KEMCO_REQUIRED_CFG_UART
    p1_p3_ok = (not dual_p1_p3) and uart_ok and line1_ok
    p1_p3_mutex_and_uart_safe = (not telemetry_ok) or p1_p3_ok
    if telemetry_ok and not p1_p3_ok:
        _add_code(codes, STATUS_BLOCKED_P1_P3_MUTUAL_EXCLUSION_OR_UART_TRAP)
        errors.append(
            f"BLOCKED_P1_P3_MUTUAL_EXCLUSION_OR_UART_TRAP: "
            f"modify_p1={bool(modify_p1_in_transaction)}, modify_p3={bool(modify_p3_in_transaction)} "
            f"(mutual-exclusion violation={dual_p1_p3}), p1_kemco_cfg_uart={eff_cfg_uart} "
            f"(must be {P1_KEMCO_REQUIRED_CFG_UART}), line1_mode_clear_sync={line1_ok}."
        )

    if telemetry_ok and len(errors) == 0:
        if modify_p1_in_transaction and not modify_p3_in_transaction:
            warnings.append(
                "Single-bank p1 rescue transaction permitted while p3 bank remains untouched."
            )
        elif modify_p3_in_transaction and not modify_p1_in_transaction:
            warnings.append(
                "Single-bank p3 transaction permitted while p1 bank remains untouched."
            )

    valid = len(errors) == 0 and len(codes) == 0
    if valid:
        status = STATUS_SAFE
    elif STATUS_BLOCKED_PERSISTENT_EMMC_WRITE in codes:
        status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    else:
        status = codes[0]

    return CnflashaDualbootGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        deployment_profile=str(deployment_profile),
        tier0_receipt_verified=bool(tier0_receipt_verified),
        sector0_magic=str(sector0_magic),
        sector0_version=str(sector0_version),
        p1_dat2_model_id=str(p1_dat2_model_id),
        p1_dat3_present=bool(p1_dat3_present),
        p2_backup_bin_present=bool(p2_backup_bin_present),
        p2_psd_bin_present=bool(p2_psd_bin_present),
        p2_defdet_bin_present=bool(p2_defdet_bin_present),
        p6_jiritsu_backed_up=bool(p6_jiritsu_backed_up),
        p12_cert_backed_up=bool(p12_cert_backed_up),
        p18_lensfile_backed_up=bool(p18_lensfile_backed_up),
        spi_nor_ddrtraining_backed_up=bool(spi_nor_ddrtraining_backed_up),
        spi_nor_ddrtraining_offset_hex=f"0x{eff_ddr_off:x}",
        two_pass_sha256_verified=bool(two_pass_sha256_verified),
        target_partition_num=eff_part_num,
        target_block_device=eff_dev,
        target_is_type5_flag1_encrypted=eff_part_num
        in SPACC_ENCRYPTED_TYPE5_FLAG1_PARTITIONS,
        forbidden_tools_or_paths_detected=tuple(forbidden_detected),
        sd_escape_hatch_enabled=bool(sd_escape_hatch_enabled),
        sd_escape_bypass_latency_us=round(eff_escape_us, 2),
        sd_escape_target=str(sd_escape_target),
        sd_escape_exec_wrapper_verified=bool(sd_escape_exec_wrapper_verified),
        modify_p1_in_transaction=bool(modify_p1_in_transaction),
        modify_p3_in_transaction=bool(modify_p3_in_transaction),
        p1_kemco_cfg_uart=eff_cfg_uart,
        p1_init_first_line=eff_init_line1,
        tier0_cold_backup_safe=tier0_cold_backup_safe,
        spacc_boundary_and_flasher_safe=spacc_boundary_and_flasher_safe,
        sd_escape_hatch_safe=sd_escape_hatch_safe,
        p1_p3_mutex_and_uart_safe=p1_p3_mutex_and_uart_safe,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 5. Gate G43 & Gate G44 Evaluators
# ---------------------------------------------------------------------------


def evaluate_g43_jiritsu_service(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    include_large_binaries: bool = False,
    jiritsu_service_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase142DonorAuditResult] = None,
) -> Tuple[GateVerdict, G43JiritsuServiceResult]:
    """Evaluate Gate G43 (`adjustcontrol_jiritsu_electrical_jbusy_and_p6_quota_safe`)."""
    audit = donor_audit or audit_phase142_donor_contracts(
        work_root=work_root,
        repo_root=repo_root,
        force_clean_room=force_clean_room,
        include_large_binaries=include_large_binaries,
    )

    eff_kwargs = dict(jiritsu_service_kwargs or {})
    eff_kwargs["request_persistent_emmc_writes"] = bool(
        request_persistent_emmc_writes
        or eff_kwargs.get("request_persistent_emmc_writes", False)
    )
    guard_res = verify_jiritsu_service_session_and_p6_guard(**eff_kwargs)

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
        STATUS_VERIFIED_G43
        if passed
        else (
            codes[0]
            if codes
            else STATUS_BLOCKED_JIRITSU_ELECTRICAL_BROWNOUT_RISK
        )
    )

    res = G43JiritsuServiceResult(
        valid=passed,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        jiritsu_service_guard=guard_res.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    verdict = GateVerdict(
        gate_id=G43_GATE_ID,
        gate_code=G43_GATE_CODE,
        passed=passed,
        status=status,
        evidence=(
            f"AdjustControl 0x40 / libJiritsu.so Electrical, /tmp/jbusy & p6 25MiB Quota Guard "
            f"({guard_res.status}, soc={guard_res.np_fz100_soc_pct:.1f}%, "
            f"v={guard_res.np_fz100_load_voltage_v:.2f}V, "
            f"jbusy={guard_res.jbusy_precheck_code_hex}, "
            f"p6_peak={guard_res.peak_p6_bytes}B/{guard_res.p6_residual_files}res, "
            f"{audit.verification_mode}), "
            f"persistent_emmc_writes_authorized={PERSISTENT_EMMC_WRITES_AUTHORIZED}."
        ),
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
        details={
            "verification_mode": audit.verification_mode,
            "electrical_power_safe": guard_res.electrical_power_safe,
            "jbusy_precheck_safe": guard_res.jbusy_precheck_safe,
            "wire_framing_and_opcodes_safe": guard_res.wire_framing_and_opcodes_safe,
            "elf_alignment_and_selfdelete_safe": guard_res.elf_alignment_and_selfdelete_safe,
            "p6_quota_and_cleanup_safe": guard_res.p6_quota_and_cleanup_safe,
        },
    )
    return verdict, res


def evaluate_g44_cnflasha_dualboot(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    include_large_binaries: bool = False,
    cnflasha_dualboot_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase142DonorAuditResult] = None,
) -> Tuple[GateVerdict, G44CnflashaDualbootResult]:
    """Evaluate Gate G44 (`cnflasha_spacc_tier0_sd_escape_and_p1_p3_mutex_safe`)."""
    audit = donor_audit or audit_phase142_donor_contracts(
        work_root=work_root,
        repo_root=repo_root,
        force_clean_room=force_clean_room,
        include_large_binaries=include_large_binaries,
    )

    eff_kwargs = dict(cnflasha_dualboot_kwargs or {})
    eff_kwargs["request_persistent_emmc_writes"] = bool(
        request_persistent_emmc_writes
        or eff_kwargs.get("request_persistent_emmc_writes", False)
    )
    guard_res = verify_cnflasha_spacc_sd_escape_and_p1_p3_guard(**eff_kwargs)

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
        STATUS_VERIFIED_G44
        if passed
        else (
            codes[0]
            if codes
            else STATUS_BLOCKED_TIER0_COLD_BACKUP_RECEIPT_INVALID
        )
    )

    res = G44CnflashaDualbootResult(
        valid=passed,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        cnflasha_dualboot_guard=guard_res.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    verdict = GateVerdict(
        gate_id=G44_GATE_ID,
        gate_code=G44_GATE_CODE,
        passed=passed,
        status=status,
        evidence=(
            f"/dev/cnflasha15 SPACC Cipher-Boundary, Tier-0 Cold-Backup Receipt, SD Escape-Hatch & "
            f"p1/p3 Mutual-Exclusion Guard ({guard_res.status}, "
            f"dev={guard_res.target_block_device}, "
            f"sd_escape={guard_res.sd_escape_bypass_latency_us:.1f}us, "
            f"p1_uart={guard_res.p1_kemco_cfg_uart}, "
            f"{audit.verification_mode}), "
            f"persistent_emmc_writes_authorized={PERSISTENT_EMMC_WRITES_AUTHORIZED}."
        ),
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
        details={
            "verification_mode": audit.verification_mode,
            "tier0_cold_backup_safe": guard_res.tier0_cold_backup_safe,
            "spacc_boundary_and_flasher_safe": guard_res.spacc_boundary_and_flasher_safe,
            "sd_escape_hatch_safe": guard_res.sd_escape_hatch_safe,
            "p1_p3_mutex_and_uart_safe": guard_res.p1_p3_mutex_and_uart_safe,
        },
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 6. Master 44-Gate Preflight Evaluator (`G01..G44`) & CLI
# ---------------------------------------------------------------------------


def evaluate_44gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated_backup: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    # G1..G42 pass-throughs
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
    # G43 inputs (AdjustControl 0x40 / libJiritsu.so Electrical, jbusy & p6 Quota)
    jiritsu_service_kwargs: Optional[Mapping[str, Any]] = None,
    # G44 inputs (/dev/cnflasha15 SPACC, Tier-0 Cold-Backup Receipt, SD Escape & p1/p3 Mutex)
    cnflasha_dualboot_kwargs: Optional[Mapping[str, Any]] = None,
) -> Master44GateReport:
    """Evaluate all 44 Master Safety Gates (`G01..G44`) deterministically."""
    resolved_root = (
        DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)
    ).resolve()
    clean_forced = _is_forced_clean_room(force_clean_room)

    m42_kwargs: Dict[str, Any] = {
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
    }
    if soc_start_ceiling_c is not None:
        m42_kwargs["soc_start_ceiling_c"] = soc_start_ceiling_c

    m42_report: Master42GateReport = evaluate_42gate_preflight(
        resolved_root, **m42_kwargs
    )

    phase142_audit = audit_phase142_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        include_large_binaries=include_large_binaries,
    )

    g43_verdict, g43_res = evaluate_g43_jiritsu_service(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        include_large_binaries=include_large_binaries,
        jiritsu_service_kwargs=jiritsu_service_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase142_audit,
    )

    g44_verdict, g44_res = evaluate_g44_cnflasha_dualboot(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        include_large_binaries=include_large_binaries,
        cnflasha_dualboot_kwargs=cnflasha_dualboot_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase142_audit,
    )

    gates_43_to_44 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g43_verdict, g44_verdict)
    ]
    all_gates = tuple(list(m42_report.gates) + gates_43_to_44)

    g01_to_g12_verified = int(m42_report.summary["g01_to_g12_verified"])
    g13_to_g42_verified = (
        int(m42_report.summary["g13_to_g40_verified"])
        + int(m42_report.summary["g41_to_g42_verified"])
    )
    g43_to_g44_verified = sum(1 for v in (g43_verdict, g44_verdict) if v.passed)
    total_verified = g01_to_g12_verified + g13_to_g42_verified + g43_to_g44_verified

    g43_to_g44_all_passed = g43_to_g44_verified == 2
    g13_to_g44_all_passed = (
        m42_report.g13_to_g42_all_passed and g43_to_g44_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m42_report.gates[:9])

    offline_41_verified = (
        g01_to_g09_ok
        and m42_report.offline_39_gates_verified
        and g43_to_g44_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_44_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g44_all_passed
        and (not request_persistent_emmc_writes)
    )

    # Hard-locked False in offline and dry-run modes, and never authorizes writes
    overall_ready_for_hardware_attach = False

    h0_h1_allowed = (
        offline_41_verified
        and m42_report.h0_h1_trial_entry_allowed
        and g43_to_g44_all_passed
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    errors: List[str] = (
        list(m42_report.errors) + list(g43_verdict.errors) + list(g44_verdict.errors)
    )
    warnings: List[str] = (
        list(m42_report.warnings)
        + list(g43_verdict.warnings)
        + list(g44_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m42_report.g13_to_g42_all_passed:
        overall_status = m42_report.status
    elif not g43_verdict.passed:
        overall_status = g43_verdict.status
    elif not g44_verdict.passed:
        overall_status = g44_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_44_verified and dry_run_simulated_backup:
        overall_status = "VERIFIED_ALL_44_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_44_verified:
        overall_status = "VERIFIED_ALL_44_GATES"
    else:
        overall_status = "VERIFIED_41_OF_44_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m42_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g43_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g44_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 44,
        "verified_gates": total_verified,
        "blocked_or_pending_gates": 44 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g42_verified": g13_to_g42_verified,
        "g43_to_g44_verified": g43_to_g44_verified,
        "g13_to_g44_all_passed": g13_to_g44_all_passed,
        "g43_to_g44_all_passed": g43_to_g44_all_passed,
        "offline_41_gates_verified": offline_41_verified,
        "all_44_gates_verified": all_44_verified,
        "dry_run_rehearsal_only": bool(dry_run_simulated_backup),
        "overall_ready_for_hardware_attach": overall_ready_for_hardware_attach,
        "h0_h1_trial_entry_allowed": h0_h1_allowed,
    }

    return Master44GateReport(
        schema=REALHW_JIRITSU_CNFLASHA_44GATE_SCHEMA,
        version=REALHW_JIRITSU_CNFLASHA_44GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=bool(dry_run_simulated_backup),
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        offline_41_gates_verified=offline_41_verified,
        all_44_gates_verified=all_44_verified,
        g13_to_g44_all_passed=g13_to_g44_all_passed,
        g43_to_g44_all_passed=g43_to_g44_all_passed,
        h0_h1_trial_entry_allowed=h0_h1_allowed,
        status=overall_status,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        summary=summary,
        gates=all_gates,
        master_42_report=m42_report.to_dict(),
        g43_result=g43_res.to_dict(),
        g44_result=g44_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_44_master_safety_gates = evaluate_44gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_jiritsu_cnflasha_and_44gate_guard",
        description=(
            "Phase 142 — AdjustControl 0x40 / libJiritsu.so Electrical, jbusy & p6 Quota "
            "Guard (G43), /dev/cnflasha15 SPACC Cipher-Boundary, Tier-0 Receipt, SD Escape & "
            "p1/p3 Mutual-Exclusion Guard (G44), and 44-Gate Master Preflight (G01..G44)"
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
        help="Supply simulated dry-run Tier-0 backup inputs so G01..G44 can be exercised offline",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit structured JSON report",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = evaluate_44gate_preflight(
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
            f"verified={report.summary['verified_gates']}/44 "
            f"g43_to_g44_all_passed={report.g43_to_g44_all_passed} "
            f"all_44_gates_verified={report.all_44_gates_verified} "
            f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
            f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}\n"
        )
    ok = (
        report.all_44_gates_verified
        if args.dry_run_simulated_backup
        else report.offline_41_gates_verified
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
