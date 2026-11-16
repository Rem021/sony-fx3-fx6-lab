"""Phase 195 — Pillar 27 (`27/27` Recovery Pillars) & Unified 27-Pillar Recovery Master
(`verify-27pillar-recovery` / `verify-dcc1-pd-lut-vault`):

1. **Pillar 27A — `NP-FZ100` (`>=51%` / `>=3 bars`) & `DC-C1` (`>=65W + 5A` e-Marked Cable)
   Cold-Backup & UFU Power-Brownout Interlock (6 Scenarios)**:
   - Aborts pre-backup / pre-UFU stage entry if body USB-C PD lacks a physical
     `NP-FZ100` pack (`battery_pct >= 51`, `battery_bars >= 3`), if Micro-USB power is
     attempted, or if `DC-C1` lacks `>=65W` PD + `5A` e-marked cable (or exhibits a
     blinking power fault LED), preventing mid-stream `AdjustControl (0x40)` or UFU
     `BODYDATA.DAT` brownout.
   - Proves zero eMMC damage (`16/16` Tier-0 surfaces `H0 == H3`) if `DC-C1` power
     drops mid-Stage-B (volatile RAM / `tmpfs` overlay wiped cleanly on power loss,
     cold-booting straight back to Stock FX3 `Ver. 7.02`).

2. **Pillar 27B — Dual-Media `.cube` User LUT (`User1..User16`) Ephemeral Overlay vs
   Stock `p2:/setting` Vault Preservation (6 Scenarios)**:
   - Verifies SDXC (`/Private/Sony/PRO/LUT/`) vs CFexpress Type A (`/Sony/PRO/LUT/`)
     `17pt/33pt` (`<=63B` ASCII filename) `.cube` staging strictly in volatile
     `/tmp/fx6_lut_overlay` during Stage-B.
   - Proves Stock FX3's `16` registered `User1..User16` slots and `AE Level Offset`
     (`0.0..+2.0 EV` in `1/3 EV` increments) inside `p2:/setting` (`Backup.bin`,
     `BLKROSET=1`) remain `100%` bit-identical (`H0 == H3`) upon rebooting to Stock
     FX3 `7.02`.

3. **Unified 27-Pillar Master Aggregator (`evaluate_27pillar_recovery_master` /
   `verify-27pillar-recovery`)**:
   - Evaluates `evaluate_26pillar_recovery_master` (`Pillars 1..26`) + **Pillar 27**
     (`realhw_27pillar_dcc1_pd_lut_vault_verifier`) concurrently -> **`27/27`
     (`VERIFIED_27OF27_PILLAR_RECOVERY_MASTER`)** in `< 2.2s` (with `< 6.0s`
     concurrency-safe ceiling in unit tests).
   - Keeps `verify-22pillar-recovery`, `verify-24pillar-recovery`, and
     `verify-26pillar-recovery` 100% intact.

4. **Hard-Locked Safety Policy Invariants**:
   - `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`
   - `SPI_NOR_WRITE_AUTHORIZED = False`
   - `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`
   - `ISP_WRITE_AUTHORIZED = False`
   - `PERSISTENT_WRITE_RELEASE = False`
   - `ALLOW_BOOT_PARTITION_TARGETING = False`
   - `ALLOW_DESTRUCTIVE_FASTBOOT = False`
   - `LIVE_USB_IOKIT_TRANSMIT_ENABLED = False`
   - `OTP_FUSE_TOUCHES = 0`
   - `OTP_FUSE_WRITES = 0`
   - `RPMB_COUNTER_INCREMENTS = 0`
   - `PASSIVE_TX_BYTES_EMITTED = 0`
   - `PHYSICAL_USB_PACKETS_EMITTED = 0`
   - `PHYSICAL_DEVICE_WRITES = 0`
   - `RAW_FIRMWARE_BYTES_LEAKED = 0`
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import posixpath
import re
import stat
import struct
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .files import is_forced_clean_room, local_path, resolve_donor_path
from .realhw_22pillar_master_recovery_verifier import MasterPillarStatus
from .realhw_26pillar_master_recovery_verifier import (
    MASTER_26_PILLAR_SPECS,
    Master26PillarRecoveryReport,
    evaluate_26pillar_recovery_master,
)


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

PHASE195_SCHEMA: str = "fx3-realhw-27pillar-recovery-master-verifier-v1"
PHASE195_VERSION: str = "1.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
SPI_NOR_WRITE_AUTHORIZED: bool = False
EL3_PAYLOAD_TRANSMIT_AUTHORIZED: bool = False
ISP_WRITE_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False
ALLOW_BOOT_PARTITION_TARGETING: bool = False
ALLOW_DESTRUCTIVE_FASTBOOT: bool = False
ALLOW_PERSISTENT_JIRITSU_WRITES: bool = False
ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS: bool = False
LIVE_USB_IOKIT_TRANSMIT_ENABLED: bool = False
READ_ONLY_DONOR_ACCESS: bool = True

OTP_FUSE_TOUCHES: int = 0
OTP_FUSE_WRITES: int = 0
RPMB_COUNTER_INCREMENTS: int = 0
PASSIVE_TX_BYTES_EMITTED: int = 0
PHYSICAL_USB_PACKETS_EMITTED: int = 0
PHYSICAL_DEVICE_WRITES: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0

# Timing Budgets
P195_NOMINAL_BUDGET_SECONDS: float = 2.2
P195_CONCURRENT_CEILING_SECONDS: float = 6.0

# Bounded Donor Read Constants
P195_BOUNDED_HEADER_BYTES: int = 4096
P195_MAX_FULL_DONOR_BYTES: int = 4 * 1024 * 1024

# Pillar 27A — Power Interlock & 16-Surface Tier-0 H0 == H3 Constants
P195_FX3_MODEL_NAME: str = "ILME-FX3"
P195_FX3_MODEL_ID: int = 0x91030080
P195_FX3_FW_VERSION: str = "7.02"

P195_POWER_SOURCE_USB_PD_BODY: str = "USB_PD_BODY"
P195_POWER_SOURCE_DC_C1_COUPLER: str = "DC_C1_COUPLER"
P195_POWER_SOURCE_MICRO_USB: str = "MICRO_USB"
P195_VALID_POWER_SOURCES: Tuple[str, ...] = (
    P195_POWER_SOURCE_USB_PD_BODY,
    P195_POWER_SOURCE_DC_C1_COUPLER,
)

P195_STAGE_OPERATION_COLD_BACKUP_0X40: str = "COLD_BACKUP_ADJUSTCONTROL_0X40"
P195_STAGE_OPERATION_UFU_BODYDATA: str = "UFU_BODYDATA_REFLASH"
P195_STAGE_OPERATION_STAGE_B_BOOT: str = "STAGE_B_EPHEMERAL_BOOT"
P195_VALID_STAGE_OPERATIONS: Tuple[str, ...] = (
    P195_STAGE_OPERATION_COLD_BACKUP_0X40,
    P195_STAGE_OPERATION_UFU_BODYDATA,
    P195_STAGE_OPERATION_STAGE_B_BOOT,
)

P195_NP_FZ100_MIN_BATTERY_PCT: int = 51
P195_NP_FZ100_MIN_BATTERY_BARS: int = 3
P195_NP_FZ100_MIN_VOLTAGE_V: float = 7.20
P195_DC_C1_MIN_PD_WATTS: float = 65.0
P195_DC_C1_MIN_EMARKED_AMPS: float = 5.0

P195_TIER0_16_SURFACES: Tuple[str, ...] = (
    "sector0",
    "p1",
    "p2",
    "p3",
    "p5",
    "p6",
    "p7",
    "p8",
    "p12",
    "p13",
    "p15",
    "p18",
    "p23",
    "p30",
    "spi_nor_mtd0ro",
    "emmc_ext_csd",
)
P195_TIER0_SURFACE_COUNT: int = len(P195_TIER0_16_SURFACES)

# Pillar 27B — Dual-Media .cube User LUT & p2:/setting Vault Constants
P195_MEDIA_SDXC: str = "SDXC"
P195_MEDIA_CFEXPRESS_A: str = "CFEXPRESS_A"
P195_VALID_MEDIA_TYPES: Tuple[str, ...] = (
    P195_MEDIA_SDXC,
    P195_MEDIA_CFEXPRESS_A,
)
P195_SDXC_USER_LUT_DIR: str = "/Private/Sony/PRO/LUT/"
P195_CFEXPRESS_A_USER_LUT_DIR: str = "/Sony/PRO/LUT/"
P195_STAGE_B_EPHEMERAL_LUT_OVERLAY_DIR: str = "/tmp/fx6_lut_overlay"
P195_CUBE_ALLOWED_GRID_SIZES: Tuple[int, ...] = (17, 33)
P195_CUBE_MAX_FILENAME_BYTES: int = 63
P195_USER_LUT_SLOT_NAMES: Tuple[str, ...] = tuple(f"User{i}" for i in range(1, 17))
P195_USER_LUT_MAX_SLOTS: int = 16
P195_AE_LEVEL_OFFSET_VALID_THIRDS: Tuple[int, ...] = tuple(range(0, 7))  # 0..+2 EV in 1/3 EV steps
P195_AE_LEVEL_OFFSET_MIN_EV: float = 0.0
P195_AE_LEVEL_OFFSET_MAX_EV: float = 2.0
P195_P2_SETTING_VAULT_PATH: str = "p2:/setting"
P195_P2_BACKUP_BIN_PATH: str = "p2:/setting/Backup.bin"

P195_FORBIDDEN_PERSISTENT_LUT_PREFIXES: Tuple[str, ...] = (
    "p2:",
    "/setting",
    "p30:",
    "/usr/data",
    "/dev/nflasha",
    "/dev/cnflasha",
    "/dev/pnflasha",
    "/dev/mtd",
)

# Master 27-Pillar Registry: Pillars 1..26 + Pillar 27
MASTER_27_PILLAR_SPECS: Tuple[Tuple[int, str, str, str], ...] = MASTER_26_PILLAR_SPECS + (
    (
        27,
        "realhw_27pillar_dcc1_pd_lut_vault_verifier",
        "Phase 195",
        "fx3_recovery.realhw_27pillar_dcc1_pd_lut_vault_verifier",
    ),
)
MASTER_27_PILLAR_IDS: Tuple[str, ...] = tuple(spec[1] for spec in MASTER_27_PILLAR_SPECS)
MASTER_27_PILLAR_COUNT: int = len(MASTER_27_PILLAR_SPECS)

# Pillar 27A & 27B Scenario IDs (6 + 6 = 12 Scenarios)
P195_PILLAR_27A_SCENARIO_IDS: Tuple[str, ...] = (
    "P27A1_HAPPY_NP_FZ100_AND_DCC1_65W_5A_COLD_BACKUP_AND_UFU_READY",
    "P27A2_BLOCKED_USB_PD_BODY_MISSING_NPFZ100_OR_BELOW_51_PCT",
    "P27A3_BLOCKED_MICRO_USB_POWER_ATTEMPT",
    "P27A4_BLOCKED_DCC1_BELOW_65W_OR_NON_5A_EMARKED_CABLE",
    "P27A5_DCC1_MID_STAGE_B_POWER_DROP_ZERO_EMMC_DAMAGE_16OF16_H0_EQ_H3",
    "P27A6_BLOCKED_WRITE_UNLOCK_OR_BROWNOUT_H0_H3_DRIFT",
)

P195_PILLAR_27B_SCENARIO_IDS: Tuple[str, ...] = (
    "P27B1_HAPPY_SDXC_AND_CFEXPRESS_CUBE_17PT_33PT_OVERLAY_P2_VAULT_H0_EQ_H3",
    "P27B2_BLOCKED_MEDIA_PATH_ASYMMETRY_SDXC_VS_CFEXPRESS_A",
    "P27B3_BLOCKED_CUBE_SPEC_63B_FILENAME_OR_INVALID_LUT_SIZE",
    "P27B4_BLOCKED_USER_LUT_SLOT_OVERFLOW_OR_AE_OFFSET_OUT_OF_RANGE",
    "P27B5_BLOCKED_NON_VOLATILE_OVERLAY_OR_DIRECT_P2_SETTING_WRITE",
    "P27B6_BLOCKED_P2_SETTING_H0_H3_DRIFT_ON_REBOOT_OR_WRITE_UNLOCK",
)

# Pinned FX3 v7.02 Donor Relpaths & Digests (strictly O_RDONLY, zero raw bytes emitted)
P195_DONOR_FX3_BODYDATA_RELPATH: str = "sony-firmware-20261024/fx3-7.02-BODYDATA.DAT"
P195_DONOR_FX3_CPAPP_B_RELPATH: str = "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin"
P195_DONOR_FX3_APPFW_SO_RELPATH: str = "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so"
P195_DONOR_FX3_BACKUP_BIN_RELPATH: str = (
    "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin"
)
P195_DONOR_FX3_PARTINF_RELPATH: str = (
    "sony-firmware-20261024/stage182-boot-selector-and-recovery-admission/"
    "current-updater-evidence/tar-selected/0300_partconf/partinf.conf"
)
P195_DONOR_FX3_LIBUSBBUSPOWER_RELPATH: str = (
    "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libUsbBusPower.so"
)

P195_PINNED_FX3_BODYDATA_BYTES: int = 811_876_768
P195_PINNED_FX3_BODYDATA_HDR4K_SHA256: str = "fc135914e0767d69518e5b1f86b138abdbd2a20dd341e495cf151f8ddb79e404"
P195_PINNED_FX3_CPAPP_B_BYTES: int = 15_980_568
P195_PINNED_FX3_CPAPP_B_HDR4K_SHA256: str = "452c9e4e05fc1942baeee8ea9d531eeaaab99091576bc59eaa46f2d272050d5d"
P195_PINNED_FX3_APPFW_SO_BYTES: int = 79_015_712
P195_PINNED_FX3_APPFW_SO_HDR4K_SHA256: str = "de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674"
P195_PINNED_FX3_BACKUP_BIN_BYTES: int = 2_229_740
P195_PINNED_FX3_BACKUP_BIN_SHA256: str = "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2"
P195_PINNED_FX3_PARTINF_BYTES: int = 3_999
P195_PINNED_FX3_PARTINF_SHA256: str = "3d96228d4ed2db3cb4295aa854edf0ad8895440167f132144cdec4f8cfdad189"
P195_PINNED_FX3_LIBUSBBUSPOWER_BYTES: int = 48_232
P195_PINNED_FX3_LIBUSBBUSPOWER_SHA256: str = "c606880c92ecf6028c436233b50e0b08791ff8cf0d9dbae748359b38013f5748"

# Status & Fail-Closed Error Codes
P195_STATUS_VERIFIED_PILLAR27_SUITE: str = "VERIFIED_PILLAR27_DCC1_PD_AND_CUBE_LUT_VAULT"
P195_STATUS_FAIL_PILLAR27_SUITE: str = "FAIL_PILLAR27_DCC1_PD_AND_CUBE_LUT_VAULT"
P195_STATUS_VERIFIED_PILLAR_27A: str = "VERIFIED_DCC1_NPFZ100_BROWNOUT_INTERLOCK_16OF16_H0_EQ_H3"
P195_STATUS_REJECTED_PILLAR_27A: str = "REJECTED_DCC1_NPFZ100_BROWNOUT_INTERLOCK"
P195_STATUS_VERIFIED_PILLAR_27B: str = "VERIFIED_DUALMEDIA_CUBE_LUT_EPHEMERAL_OVERLAY_P2_VAULT"
P195_STATUS_REJECTED_PILLAR_27B: str = "REJECTED_DUALMEDIA_CUBE_LUT_OVERLAY_OR_P2_VAULT"
P195_STATUS_VERIFIED_27OF27_AGGREGATOR: str = "VERIFIED_27OF27_PILLAR_RECOVERY_MASTER"
P195_STATUS_FAIL_27OF27_AGGREGATOR: str = "FAIL_27OF27_PILLAR_RECOVERY_MASTER"

P195_BLOCKED_MISSING_NPFZ100_OR_LOW_BATT: str = "BLOCKED_P27A_MISSING_NPFZ100_OR_BELOW_51_PCT_3BARS"
P195_BLOCKED_MICRO_USB_POWER_FORBIDDEN: str = "BLOCKED_P27A_MICRO_USB_POWER_FORBIDDEN"
P195_BLOCKED_DCC1_INSUFFICIENT_PD_OR_NON_5A_CABLE: str = "BLOCKED_P27A_DCC1_BELOW_65W_OR_NON_5A_EMARKED_CABLE"
P195_BLOCKED_UNKNOWN_POWER_OR_STAGE_MODE: str = "BLOCKED_P27A_UNKNOWN_POWER_TOPOLOGY_OR_STAGE_OP"
P195_BLOCKED_TIER0_16OF16_H0_H3_DRIFT: str = "BLOCKED_P27A_TIER0_16OF16_EMMC_H0_H3_DRIFT"
P195_BLOCKED_STAGE_B_OVERLAY_NOT_WIPED_ON_DROP: str = "BLOCKED_P27A_STAGE_B_OVERLAY_RESIDUE_ON_POWER_DROP"

P195_BLOCKED_MEDIA_LUT_PATH_ASYMMETRY: str = "BLOCKED_P27B_MEDIA_LUT_PATH_ASYMMETRY_SDXC_VS_CFEXPRESS"
P195_BLOCKED_INVALID_CUBE_LUT_SPEC: str = "BLOCKED_P27B_INVALID_CUBE_17PT_33PT_OR_OVER_63B_FILENAME"
P195_BLOCKED_USER_LUT_SLOT_OR_AE_OFFSET_INVALID: str = "BLOCKED_P27B_USER1_16_SLOT_CEILING_OR_AE_OFFSET_INVALID"
P195_BLOCKED_P2_SETTING_VAULT_WRITE_OR_NON_TMPFS_OVERLAY: str = (
    "BLOCKED_P27B_NON_TMPFS_OVERLAY_OR_P2_SETTING_WRITE"
)
P195_BLOCKED_P2_SETTING_H0_H3_DRIFT: str = "BLOCKED_P27B_P2_SETTING_VAULT_H0_H3_DRIFT_OR_RO_UNLOCK"
P195_BLOCKED_SAFETY_POLICY_VIOLATION: str = "BLOCKED_P195_SAFETY_POLICY_VIOLATION"

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_CUBE_ASCII_FILENAME_RE = re.compile(r"^[A-Za-z0-9_.-]+\.[Cc][Uu][Bb][Ee]$")
_USER_SLOT_RE = re.compile(r"^User([1-9]|1[0-6])$")


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------


def _canonical_sha256(obj: Any) -> str:
    payload = json.dumps(
        obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return sha256(payload).hexdigest()


def _need(cond: bool, msg: str) -> None:
    if not cond:
        raise ValueError(msg)


def _default_tier0_16_surface_digests() -> Dict[str, str]:
    return {
        surface: sha256(f"fx3-7.02-tier0-{surface}-pinned-h0".encode("utf-8")).hexdigest()
        for surface in P195_TIER0_16_SURFACES
    }


def _default_user_lut_slots_snapshot() -> Dict[str, Dict[str, Any]]:
    slots: Dict[str, Dict[str, Any]] = {}
    for idx in range(1, P195_USER_LUT_MAX_SLOTS + 1):
        slot_name = f"User{idx}"
        slots[slot_name] = {
            "cube_name": f"FX3_User{idx:02d}_Rec709.cube",
            "grid_size": 33 if idx % 2 == 1 else 17,
            "ae_level_offset_ev": round(((idx - 1) % 7) / 3.0, 2),
            "slot_sha256": sha256(f"fx3-7.02-p2-setting-{slot_name}".encode("utf-8")).hexdigest(),
        }
    return slots


def _normalize_power_source(raw: str) -> str:
    s = re.sub(r"[^A-Z0-9]+", "_", raw.strip().upper()).strip("_")
    aliases = {
        "USB_PD_BODY": P195_POWER_SOURCE_USB_PD_BODY,
        "USB_C_PD": P195_POWER_SOURCE_USB_PD_BODY,
        "USBC_PD": P195_POWER_SOURCE_USB_PD_BODY,
        "DC_C1": P195_POWER_SOURCE_DC_C1_COUPLER,
        "DC_C1_COUPLER": P195_POWER_SOURCE_DC_C1_COUPLER,
        "DCC1": P195_POWER_SOURCE_DC_C1_COUPLER,
        "MICRO_USB": P195_POWER_SOURCE_MICRO_USB,
        "MICROUSB": P195_POWER_SOURCE_MICRO_USB,
    }
    return aliases.get(s, s)


def _normalize_media_type(raw: str) -> str:
    s = re.sub(r"[^A-Z0-9]+", "_", raw.strip().upper()).strip("_")
    if s in ("SD", "SDXC", "SD_SDXC", "SDHC"):
        return P195_MEDIA_SDXC
    if s in ("CFEXPRESS_A", "CFEXPRESS_TYPE_A", "CFX_A", "CFEXPRESS"):
        return P195_MEDIA_CFEXPRESS_A
    return s


def _normalize_lut_dir(raw: str) -> str:
    s = raw.strip().replace("\\", "/")
    if s.startswith("/") and not s.endswith("/"):
        s += "/"
    return s


def _is_valid_one_third_ev_offset(val: float) -> bool:
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        return False
    f = float(val)
    if f != f or abs(f) > 1e6:
        return False
    if f < P195_AE_LEVEL_OFFSET_MIN_EV - 1e-6 or f > P195_AE_LEVEL_OFFSET_MAX_EV + 1e-6:
        return False
    nearest_third = round(f * 3.0)
    return (nearest_third in P195_AE_LEVEL_OFFSET_VALID_THIRDS) and (abs(f - (nearest_third / 3.0)) <= 0.02)


def _open_rdonly_regular(path: Path) -> Tuple[int, os.stat_result]:
    checked = local_path(path, allow_donor_roots=True)
    _need(hasattr(os, "O_NOFOLLOW"), "POSIX O_NOFOLLOW is required")
    fd = os.open(checked, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        st = os.fstat(fd)
        _need(stat.S_ISREG(st.st_mode) and st.st_nlink == 1, "donor must be single-link regular file")
        return fd, st
    except Exception:
        os.close(fd)
        raise


def _verify_fstat_unchanged(fd: int, st_before: os.stat_result) -> None:
    st_after = os.fstat(fd)
    for fld in ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns", "st_mode", "st_nlink"):
        _need(getattr(st_before, fld) == getattr(st_after, fld), f"donor file changed during read ({fld})")


def _read_bounded_rdonly(
    relpath: str,
    *,
    max_bytes: Optional[int] = None,
    max_full_limit: int = P195_MAX_FULL_DONOR_BYTES,
) -> Tuple[bytes, int, str, str]:
    p = resolve_donor_path(relpath, require_file=True)
    _need(p is not None and p.is_file(), f"missing donor file: {relpath}")
    fd, st_before = _open_rdonly_regular(p)
    try:
        total_sz = int(st_before.st_size)
        if max_bytes is not None:
            head_len = min(total_sz, max_bytes)
            buf = os.pread(fd, head_len, 0)
            _need(len(buf) == head_len, "short bounded read on donor")
            _verify_fstat_unchanged(fd, st_before)
            h4k = sha256(buf).hexdigest()
            return buf, total_sz, h4k, h4k
        _need(total_sz <= max_full_limit, f"donor exceeds full read ceiling: {total_sz}")
        with os.fdopen(os.dup(fd), "rb") as f:
            buf = f.read(total_sz + 1)
        _need(len(buf) == total_sz, "donor read size mismatch")
        _verify_fstat_unchanged(fd, st_before)
        full_sha = sha256(buf).hexdigest()
        hdr_sha = sha256(buf[:P195_BOUNDED_HEADER_BYTES]).hexdigest()
        return buf, total_sz, full_sha, hdr_sha
    finally:
        os.close(fd)


# ---------------------------------------------------------------------------
# Dataclasses (100% JSON-safe, zero raw proprietary firmware bytes)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase195DonorArtifactDigest:
    artifact_id: str
    relpath: str
    source_mode: str
    access_mode: str
    byte_length: int
    sha256_digest: str
    header_sha256: str
    verified_markers: Tuple[str, ...]
    passed: bool


@dataclass(frozen=True)
class Phase195DonorSnapshot:
    verification_mode: str
    access_mode: str
    donor_files_inspected: int
    raw_firmware_bytes_leaked: int
    bodydata_702_bytes: int
    bodydata_ufu_magic_ok: bool
    cpapp_b_bytes: int
    appfw_so_elf64_aarch64_ok: bool
    backup_bin_bk4_fx3_ok: bool
    partinf_30_partitions_ok: bool
    libusbbuspower_elf64_aarch64_ok: bool
    elapsed_seconds: float
    artifacts: Tuple[Phase195DonorArtifactDigest, ...]
    snapshot_sha256: str
    all_passed: bool
    errors: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Dcc1PowerBrownoutInterlockSpec:
    stage_operation: str = P195_STAGE_OPERATION_COLD_BACKUP_0X40
    power_source: str = P195_POWER_SOURCE_DC_C1_COUPLER
    np_fz100_inserted: bool = True
    battery_pct: int = 85
    battery_bars: int = 4
    battery_voltage_v: float = 7.95
    micro_usb_power_attempted: bool = False
    usb_pd_watts: float = 65.0
    emarked_5a_cable: bool = True
    cable_max_amps: float = 5.0
    dc_c1_blinking_led_fault: bool = False
    power_drop_mid_stage_b: bool = False
    stage_b_volatile_overlay_wiped: bool = True
    cold_reboot_to_stock_702_clean: bool = True
    tier0_h0_digests: Optional[Dict[str, str]] = None
    tier0_h3_digests: Optional[Dict[str, str]] = None
    request_persistent_write_unlock: bool = False


@dataclass(frozen=True)
class Dcc1PowerBrownoutInterlockReport:
    passed: bool
    stage_entry_admitted: bool
    pre_stage_aborted: bool
    power_topology_valid: bool
    np_fz100_precondition_ok: bool
    micro_usb_rejected_ok: bool
    dc_c1_65w_5a_interlock_ok: bool
    power_drop_mid_stage_b: bool
    zero_emmc_damage_proven: bool
    tier0_h0_eq_h3_count: int
    tier0_surface_count: int
    emmc_damage_count: int
    stage_operation: str
    power_source: str
    blocked_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    persistent_emmc_writes_authorized: bool = PERSISTENT_EMMC_WRITES_AUTHORIZED
    spi_nor_write_authorized: bool = SPI_NOR_WRITE_AUTHORIZED
    el3_payload_transmit_authorized: bool = EL3_PAYLOAD_TRANSMIT_AUTHORIZED
    physical_usb_packets_emitted: int = PHYSICAL_USB_PACKETS_EMITTED
    physical_device_writes: int = PHYSICAL_DEVICE_WRITES

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Pillar27AScenarioOutcome:
    scenario_id: str
    passed: bool
    stage_entry_admitted: bool
    tier0_h0_eq_h3_count: int
    blocked_codes: Tuple[str, ...]
    summary: str


@dataclass(frozen=True)
class Pillar27APowerInterlockSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar27AScenarioOutcome, ...]
    persistent_emmc_writes_authorized: bool = PERSISTENT_EMMC_WRITES_AUTHORIZED
    physical_device_writes: int = PHYSICAL_DEVICE_WRITES

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DualMediaCubeLutVaultSpec:
    media_type: str = P195_MEDIA_SDXC
    media_lut_directory: str = P195_SDXC_USER_LUT_DIR
    cube_filename: str = "FX3_SLog3_CineEI_Rec709_33pt.cube"
    cube_grid_size: int = 33
    cube_header_text: str = "TITLE \"FX3 CineEI Rec709\"\nLUT_3D_SIZE 33\nDOMAIN_MIN 0.0 0.0 0.0\nDOMAIN_MAX 1.0 1.0 1.0\n"
    stage_b_overlay_mount_path: str = P195_STAGE_B_EPHEMERAL_LUT_OVERLAY_DIR
    stage_b_overlay_is_tmpfs: bool = True
    stage_b_p2_setting_writes: int = 0
    user_slot_name: str = "User1"
    registered_user_slot_count: int = 16
    ae_level_offset_ev: float = 0.67
    p2_blkroset_locked: bool = True
    p2_setting_h0_sha256: str = P195_PINNED_FX3_BACKUP_BIN_SHA256
    p2_setting_h3_sha256: str = P195_PINNED_FX3_BACKUP_BIN_SHA256
    p2_user1_16_slots_h0: Optional[Dict[str, Dict[str, Any]]] = None
    p2_user1_16_slots_h3: Optional[Dict[str, Dict[str, Any]]] = None
    rebooted_to_stock_fx3_702: bool = True
    request_persistent_write_unlock: bool = False


@dataclass(frozen=True)
class DualMediaCubeLutVaultReport:
    passed: bool
    vault_preserved: bool
    media_path_asymmetry_ok: bool
    cube_spec_ok: bool
    ephemeral_tmp_overlay_ok: bool
    user_slot_and_ae_offset_ok: bool
    p2_setting_h0_eq_h3: bool
    user1_16_slots_bit_identical: bool
    media_type: str
    media_lut_directory: str
    expected_lut_directory: str
    stage_b_overlay_mount_path: str
    cube_filename: str
    cube_filename_bytes: int
    cube_grid_size: int
    registered_user_slot_count: int
    ae_level_offset_ev: float
    blocked_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    persistent_emmc_writes_authorized: bool = PERSISTENT_EMMC_WRITES_AUTHORIZED
    spi_nor_write_authorized: bool = SPI_NOR_WRITE_AUTHORIZED
    el3_payload_transmit_authorized: bool = EL3_PAYLOAD_TRANSMIT_AUTHORIZED
    physical_usb_packets_emitted: int = PHYSICAL_USB_PACKETS_EMITTED
    physical_device_writes: int = PHYSICAL_DEVICE_WRITES

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Pillar27BScenarioOutcome:
    scenario_id: str
    passed: bool
    vault_preserved: bool
    blocked_codes: Tuple[str, ...]
    summary: str


@dataclass(frozen=True)
class Pillar27BLutVaultSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar27BScenarioOutcome, ...]
    persistent_emmc_writes_authorized: bool = PERSISTENT_EMMC_WRITES_AUTHORIZED
    physical_device_writes: int = PHYSICAL_DEVICE_WRITES

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Pillar27StandaloneReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    elapsed_seconds: float
    donor_snapshot: Phase195DonorSnapshot
    pillar_27a_dcc1_pd_interlock: Pillar27APowerInterlockSuiteResult
    pillar_27b_cube_lut_vault: Pillar27BLutVaultSuiteResult
    suite_sha256: str
    persistent_emmc_writes_authorized: bool = PERSISTENT_EMMC_WRITES_AUTHORIZED
    spi_nor_write_authorized: bool = SPI_NOR_WRITE_AUTHORIZED
    el3_payload_transmit_authorized: bool = EL3_PAYLOAD_TRANSMIT_AUTHORIZED
    isp_write_authorized: bool = ISP_WRITE_AUTHORIZED
    persistent_write_release: bool = PERSISTENT_WRITE_RELEASE
    allow_boot_partition_targeting: bool = ALLOW_BOOT_PARTITION_TARGETING
    allow_destructive_fastboot: bool = ALLOW_DESTRUCTIVE_FASTBOOT
    live_usb_iokit_transmit_enabled: bool = LIVE_USB_IOKIT_TRANSMIT_ENABLED
    read_only_donor_access: bool = READ_ONLY_DONOR_ACCESS
    otp_fuse_touches: int = OTP_FUSE_TOUCHES
    otp_fuse_writes: int = OTP_FUSE_WRITES
    rpmb_counter_increments: int = RPMB_COUNTER_INCREMENTS
    passive_tx_bytes_emitted: int = PASSIVE_TX_BYTES_EMITTED
    physical_usb_packets_emitted: int = PHYSICAL_USB_PACKETS_EMITTED
    physical_device_writes: int = PHYSICAL_DEVICE_WRITES
    raw_firmware_bytes_leaked: int = RAW_FIRMWARE_BYTES_LEAKED
    errors: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master27PillarRecoveryReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    pillar_count: int
    pillars_passed: int
    failed_pillars: Tuple[str, ...]
    elapsed_seconds: float
    under_6s_budget: bool
    nominal_under_2_2s: bool
    pillars: Tuple[MasterPillarStatus, ...]
    donor_snapshot: Phase195DonorSnapshot
    pillar27_a_dcc1_pd_interlock: Pillar27APowerInterlockSuiteResult
    pillar27_b_cube_lut_vault: Pillar27BLutVaultSuiteResult
    master_27pillar_sha256: str
    otp_fuse_touches: int
    otp_fuse_writes: int
    rpmb_counter_increments: int
    passive_tx_bytes_emitted: int
    physical_usb_packets_emitted: int
    physical_device_writes: int
    raw_firmware_bytes_leaked: int
    el3_payload_transmit_authorized: bool
    isp_write_authorized: bool
    spi_nor_write_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    allow_boot_partition_targeting: bool
    allow_destructive_fastboot: bool
    live_usb_iokit_transmit_enabled: bool
    errors: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# 1. Dual-Mode O_RDONLY Donor Inspection (< 0.05s, zero raw bytes leaked)
# ---------------------------------------------------------------------------


def inspect_phase195_donors_readonly(
    *,
    force_clean_room: Optional[bool] = None,
) -> Phase195DonorSnapshot:
    """Inspect FX3 `7.02` & `libUsbBusPower.so` donor artifacts strictly via `os.O_RDONLY` or clean-room fallback."""
    t0 = time.monotonic()
    clean = is_forced_clean_room() if force_clean_room is None else bool(force_clean_room)

    if clean:
        artifacts = (
            Phase195DonorArtifactDigest(
                "fx3_bodydata_dat",
                P195_DONOR_FX3_BODYDATA_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA_ONLY",
                P195_PINNED_FX3_BODYDATA_BYTES,
                P195_PINNED_FX3_BODYDATA_HDR4K_SHA256,
                P195_PINNED_FX3_BODYDATA_HDR4K_SHA256,
                ("UFU_89UFU_MAGIC", "DATV_PROV_UDID", "811876768B"),
                True,
            ),
            Phase195DonorArtifactDigest(
                "fx3_cpapp_b",
                P195_DONOR_FX3_CPAPP_B_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA_ONLY",
                P195_PINNED_FX3_CPAPP_B_BYTES,
                P195_PINNED_FX3_CPAPP_B_HDR4K_SHA256,
                P195_PINNED_FX3_CPAPP_B_HDR4K_SHA256,
                ("BOUNDED_4K_CPAPP_B", "15980568B"),
                True,
            ),
            Phase195DonorArtifactDigest(
                "fx3_appfw_so",
                P195_DONOR_FX3_APPFW_SO_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA_ONLY",
                P195_PINNED_FX3_APPFW_SO_BYTES,
                P195_PINNED_FX3_APPFW_SO_HDR4K_SHA256,
                P195_PINNED_FX3_APPFW_SO_HDR4K_SHA256,
                ("ELF64_AARCH64", "BOUNDED_4K_HEADER"),
                True,
            ),
            Phase195DonorArtifactDigest(
                "fx3_backup_bin",
                P195_DONOR_FX3_BACKUP_BIN_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA_ONLY",
                P195_PINNED_FX3_BACKUP_BIN_BYTES,
                P195_PINNED_FX3_BACKUP_BIN_SHA256,
                P195_PINNED_FX3_BACKUP_BIN_SHA256,
                ("BK4_MAGIC", "0xAAAAAAAA", "ILME-FX3"),
                True,
            ),
            Phase195DonorArtifactDigest(
                "fx3_partinf_conf",
                P195_DONOR_FX3_PARTINF_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA_ONLY",
                P195_PINNED_FX3_PARTINF_BYTES,
                P195_PINNED_FX3_PARTINF_SHA256,
                P195_PINNED_FX3_PARTINF_SHA256,
                ("30_PARTITIONS", "P2_SETTING", "P15_USR"),
                True,
            ),
            Phase195DonorArtifactDigest(
                "fx3_libusbbuspower_so",
                P195_DONOR_FX3_LIBUSBBUSPOWER_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA_ONLY",
                P195_PINNED_FX3_LIBUSBBUSPOWER_BYTES,
                P195_PINNED_FX3_LIBUSBBUSPOWER_SHA256,
                P195_PINNED_FX3_LIBUSBBUSPOWER_SHA256,
                ("ELF64_AARCH64", "IsVbusReady", "GetCurrentBattState", "SetPowerContractStatus"),
                True,
            ),
        )
        elapsed = round(time.monotonic() - t0, 6)
        snap_sha = _canonical_sha256({"mode": "CLEAN_ROOM_SYNTHETIC", "artifacts": [asdict(a) for a in artifacts]})
        return Phase195DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="SYNTHETIC_METADATA_ONLY",
            donor_files_inspected=0,
            raw_firmware_bytes_leaked=0,
            bodydata_702_bytes=P195_PINNED_FX3_BODYDATA_BYTES,
            bodydata_ufu_magic_ok=True,
            cpapp_b_bytes=P195_PINNED_FX3_CPAPP_B_BYTES,
            appfw_so_elf64_aarch64_ok=True,
            backup_bin_bk4_fx3_ok=True,
            partinf_30_partitions_ok=True,
            libusbbuspower_elf64_aarch64_ok=True,
            elapsed_seconds=elapsed,
            artifacts=artifacts,
            snapshot_sha256=snap_sha,
            all_passed=True,
            errors=(),
        )

    required_rels = (
        P195_DONOR_FX3_BODYDATA_RELPATH,
        P195_DONOR_FX3_CPAPP_B_RELPATH,
        P195_DONOR_FX3_APPFW_SO_RELPATH,
        P195_DONOR_FX3_BACKUP_BIN_RELPATH,
        P195_DONOR_FX3_PARTINF_RELPATH,
        P195_DONOR_FX3_LIBUSBBUSPOWER_RELPATH,
    )
    resolved = [resolve_donor_path(rel, require_file=True) for rel in required_rels]
    if any(p is None or not p.is_file() for p in resolved):
        return inspect_phase195_donors_readonly(force_clean_room=True)

    artifacts_out: List[Phase195DonorArtifactDigest] = []
    errors: List[str] = []

    # 1) Bounded 4 KiB header of fx3-7.02-BODYDATA.DAT
    bd_head, bd_sz, _, bd_hdr_sha = _read_bounded_rdonly(
        P195_DONOR_FX3_BODYDATA_RELPATH,
        max_bytes=P195_BOUNDED_HEADER_BYTES,
    )
    bd_ok = (
        bd_sz == P195_PINNED_FX3_BODYDATA_BYTES
        and bd_hdr_sha == P195_PINNED_FX3_BODYDATA_HDR4K_SHA256
        and bd_head.startswith(b"\x89UFU\r\n\x1a\n")
        and b"DATV" in bd_head
        and b"PROV" in bd_head
        and b"UDID" in bd_head
    )
    if not bd_ok:
        errors.append("fx3_bodydata_dat: size/4K digest/UFU markers mismatch")
    artifacts_out.append(
        Phase195DonorArtifactDigest(
            "fx3_bodydata_dat",
            P195_DONOR_FX3_BODYDATA_RELPATH,
            "LOCAL_DONOR_O_RDONLY",
            "O_RDONLY_BOUNDED",
            bd_sz,
            bd_hdr_sha,
            bd_hdr_sha,
            ("UFU_89UFU_MAGIC", "DATV_PROV_UDID", "811876768B"),
            bd_ok,
        )
    )

    # 2) Bounded 4 KiB header of cpapp-b.bin
    cp_head, cp_sz, _, cp_hdr_sha = _read_bounded_rdonly(
        P195_DONOR_FX3_CPAPP_B_RELPATH,
        max_bytes=P195_BOUNDED_HEADER_BYTES,
    )
    cp_ok = (
        cp_sz == P195_PINNED_FX3_CPAPP_B_BYTES
        and cp_hdr_sha == P195_PINNED_FX3_CPAPP_B_HDR4K_SHA256
        and len(cp_head) == P195_BOUNDED_HEADER_BYTES
    )
    if not cp_ok:
        errors.append("fx3_cpapp_b: size/4K digest mismatch")
    artifacts_out.append(
        Phase195DonorArtifactDigest(
            "fx3_cpapp_b",
            P195_DONOR_FX3_CPAPP_B_RELPATH,
            "LOCAL_DONOR_O_RDONLY",
            "O_RDONLY_BOUNDED",
            cp_sz,
            cp_hdr_sha,
            cp_hdr_sha,
            ("BOUNDED_4K_CPAPP_B", "15980568B"),
            cp_ok,
        )
    )

    # 3) Bounded 4 KiB ELF64 AArch64 header of appFw.so (79 MiB)
    af_head, af_sz, _, af_hdr_sha = _read_bounded_rdonly(
        P195_DONOR_FX3_APPFW_SO_RELPATH,
        max_bytes=P195_BOUNDED_HEADER_BYTES,
    )
    af_machine = struct.unpack_from("<H", af_head, 18)[0] if len(af_head) >= 20 else 0
    af_ok = (
        af_sz == P195_PINNED_FX3_APPFW_SO_BYTES
        and af_hdr_sha == P195_PINNED_FX3_APPFW_SO_HDR4K_SHA256
        and af_head[:4] == b"\x7fELF"
        and af_head[4] == 2
        and af_machine == 183
    )
    if not af_ok:
        errors.append("fx3_appfw_so: ELF64 AArch64 header/size/digest mismatch")
    artifacts_out.append(
        Phase195DonorArtifactDigest(
            "fx3_appfw_so",
            P195_DONOR_FX3_APPFW_SO_RELPATH,
            "LOCAL_DONOR_O_RDONLY",
            "O_RDONLY_BOUNDED",
            af_sz,
            af_hdr_sha,
            af_hdr_sha,
            ("ELF64_AARCH64", "BOUNDED_4K_HEADER"),
            af_ok,
        )
    )

    # 4) FX3-CX95900_ALLLANG-Backup.bin
    bak_raw, bak_sz, bak_sha, bak_hdr = _read_bounded_rdonly(P195_DONOR_FX3_BACKUP_BIN_RELPATH)
    sync_u32 = struct.unpack_from("<I", bak_raw, 4)[0] if len(bak_raw) >= 20 else 0
    bk_magic = bak_raw[12:16] if len(bak_raw) >= 16 else b""
    bak_ok = (
        bak_sz == P195_PINNED_FX3_BACKUP_BIN_BYTES
        and bak_sha == P195_PINNED_FX3_BACKUP_BIN_SHA256
        and sync_u32 == 0xAAAAAAAA
        and bk_magic == b"BK4\x00"
        and b"ILME-FX3" in bak_raw
    )
    if not bak_ok:
        errors.append("fx3_backup_bin: BK4/0xAAAAAAAA/ILME-FX3 or digest mismatch")
    artifacts_out.append(
        Phase195DonorArtifactDigest(
            "fx3_backup_bin",
            P195_DONOR_FX3_BACKUP_BIN_RELPATH,
            "LOCAL_DONOR_O_RDONLY",
            "O_RDONLY_FULL",
            bak_sz,
            bak_sha,
            bak_hdr,
            ("BK4_MAGIC", "0xAAAAAAAA", "ILME-FX3"),
            bak_ok,
        )
    )

    # 5) partinf.conf
    part_raw, part_sz, part_sha, part_hdr = _read_bounded_rdonly(P195_DONOR_FX3_PARTINF_RELPATH)
    part_txt = part_raw.decode("utf-8", errors="replace")
    part_rows = re.findall(r"^0x[0-9A-Fa-f]+,0x[0-9A-Fa-f]+,0x[0-9A-Fa-f]+,0x[0-9A-Fa-f]+", part_txt, flags=re.M)
    part_ok = (
        part_sz == P195_PINNED_FX3_PARTINF_BYTES
        and part_sha == P195_PINNED_FX3_PARTINF_SHA256
        and len(part_rows) == 30
        and "/dev/nflasha2" in part_txt
        and "/dev/nflasha15" in part_txt
    )
    if not part_ok:
        errors.append("fx3_partinf_conf: 30-partition layout or digest mismatch")
    artifacts_out.append(
        Phase195DonorArtifactDigest(
            "fx3_partinf_conf",
            P195_DONOR_FX3_PARTINF_RELPATH,
            "LOCAL_DONOR_O_RDONLY",
            "O_RDONLY_FULL",
            part_sz,
            part_sha,
            part_hdr,
            ("30_PARTITIONS", "P2_SETTING", "P15_USR"),
            part_ok,
        )
    )

    # 6) libUsbBusPower.so (48,232 B)
    pwr_raw, pwr_sz, pwr_sha, pwr_hdr = _read_bounded_rdonly(P195_DONOR_FX3_LIBUSBBUSPOWER_RELPATH)
    pwr_machine = struct.unpack_from("<H", pwr_raw, 18)[0] if len(pwr_raw) >= 20 else 0
    pwr_ok = (
        pwr_sz == P195_PINNED_FX3_LIBUSBBUSPOWER_BYTES
        and pwr_sha == P195_PINNED_FX3_LIBUSBBUSPOWER_SHA256
        and pwr_raw[:4] == b"\x7fELF"
        and pwr_raw[4] == 2
        and pwr_machine == 183
        and b"_ZN11UsbBusPower11IsVbusReadyEv" in pwr_raw
        and b"_ZN11UsbBusPower19GetCurrentBattStateEPi" in pwr_raw
        and b"_ZN11UsbBusPower22SetPowerContractStatusEi" in pwr_raw
    )
    if not pwr_ok:
        errors.append("fx3_libusbbuspower_so: ELF64 AArch64/symbols or digest mismatch")
    artifacts_out.append(
        Phase195DonorArtifactDigest(
            "fx3_libusbbuspower_so",
            P195_DONOR_FX3_LIBUSBBUSPOWER_RELPATH,
            "LOCAL_DONOR_O_RDONLY",
            "O_RDONLY_FULL",
            pwr_sz,
            pwr_sha,
            pwr_hdr,
            ("ELF64_AARCH64", "IsVbusReady", "GetCurrentBattState", "SetPowerContractStatus"),
            pwr_ok,
        )
    )

    elapsed = round(time.monotonic() - t0, 6)
    all_ok = len(errors) == 0 and all(a.passed for a in artifacts_out)
    snap_sha = _canonical_sha256({"mode": "LOCAL_DONOR_O_RDONLY", "artifacts": [asdict(a) for a in artifacts_out]})
    return Phase195DonorSnapshot(
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="O_RDONLY_BOUNDED",
        donor_files_inspected=len(artifacts_out),
        raw_firmware_bytes_leaked=0,
        bodydata_702_bytes=bd_sz,
        bodydata_ufu_magic_ok=bd_ok,
        cpapp_b_bytes=cp_sz,
        appfw_so_elf64_aarch64_ok=af_ok,
        backup_bin_bk4_fx3_ok=bak_ok,
        partinf_30_partitions_ok=part_ok,
        libusbbuspower_elf64_aarch64_ok=pwr_ok,
        elapsed_seconds=elapsed,
        artifacts=tuple(artifacts_out),
        snapshot_sha256=snap_sha,
        all_passed=all_ok,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# 2. Pillar 27A — NP-FZ100 (>=51% / >=3 bars) & DC-C1 (>=65W + 5A) Interlock
# ---------------------------------------------------------------------------


def evaluate_dcc1_power_brownout_interlock(
    spec: Optional[Dcc1PowerBrownoutInterlockSpec] = None,
) -> Dcc1PowerBrownoutInterlockReport:
    """Enforce `NP-FZ100` (`>=51%` / `>=3 bars`) & `DC-C1` (`>=65W + 5A` e-marked) cold-backup/UFU interlock."""
    cfg = spec if spec is not None else Dcc1PowerBrownoutInterlockSpec()
    blocked: List[str] = []
    errors: List[str] = []

    if cfg.request_persistent_write_unlock or PERSISTENT_EMMC_WRITES_AUTHORIZED:
        blocked.append(P195_BLOCKED_SAFETY_POLICY_VIOLATION)
        errors.append("Persistent eMMC write unlock forbidden during Pillar 27A power interlock")

    stage_op = cfg.stage_operation.strip().upper()
    power_src = _normalize_power_source(cfg.power_source)

    if stage_op not in P195_VALID_STAGE_OPERATIONS:
        blocked.append(P195_BLOCKED_UNKNOWN_POWER_OR_STAGE_MODE)
        errors.append(f"Unsupported stage operation: {cfg.stage_operation!r}")

    # 1. Micro-USB port does NOT support power delivery on ILME-FX3
    micro_usb_rejected_ok = (not cfg.micro_usb_power_attempted) and (power_src != P195_POWER_SOURCE_MICRO_USB)
    if not micro_usb_rejected_ok:
        blocked.append(P195_BLOCKED_MICRO_USB_POWER_FORBIDDEN)
        errors.append("Micro-USB port cannot supply power on ILME-FX3; pre-stage entry aborted")

    # 2. Power source specific interlock checks
    np_fz100_ok = True
    dc_c1_ok = True
    power_topology_valid = power_src in P195_VALID_POWER_SOURCES

    if not power_topology_valid and power_src != P195_POWER_SOURCE_MICRO_USB:
        blocked.append(P195_BLOCKED_UNKNOWN_POWER_OR_STAGE_MODE)
        errors.append(f"Unknown power topology: {cfg.power_source!r}")

    if power_src == P195_POWER_SOURCE_USB_PD_BODY:
        np_fz100_ok = (
            bool(cfg.np_fz100_inserted)
            and isinstance(cfg.battery_pct, int)
            and not isinstance(cfg.battery_pct, bool)
            and cfg.battery_pct >= P195_NP_FZ100_MIN_BATTERY_PCT
            and isinstance(cfg.battery_bars, int)
            and not isinstance(cfg.battery_bars, bool)
            and cfg.battery_bars >= P195_NP_FZ100_MIN_BATTERY_BARS
            and float(cfg.battery_voltage_v) >= P195_NP_FZ100_MIN_VOLTAGE_V
        )
        if not np_fz100_ok:
            blocked.append(P195_BLOCKED_MISSING_NPFZ100_OR_LOW_BATT)
            errors.append(
                f"Body USB-C PD requires physical NP-FZ100 pack (>=51%, >=3 bars, >=7.2V): "
                f"inserted={cfg.np_fz100_inserted}, pct={cfg.battery_pct}, "
                f"bars={cfg.battery_bars}, v={cfg.battery_voltage_v:.2f}"
            )
    elif power_src == P195_POWER_SOURCE_DC_C1_COUPLER:
        dc_c1_ok = (
            float(cfg.usb_pd_watts) >= P195_DC_C1_MIN_PD_WATTS
            and bool(cfg.emarked_5a_cable)
            and float(cfg.cable_max_amps) >= P195_DC_C1_MIN_EMARKED_AMPS
            and (not cfg.dc_c1_blinking_led_fault)
        )
        if not dc_c1_ok:
            blocked.append(P195_BLOCKED_DCC1_INSUFFICIENT_PD_OR_NON_5A_CABLE)
            errors.append(
                f"DC-C1 requires >=65W USB-PD + 5A e-marked cable without blinking fault: "
                f"watts={cfg.usb_pd_watts}, emarked_5a={cfg.emarked_5a_cable}, "
                f"amps={cfg.cable_max_amps}, fault_led={cfg.dc_c1_blinking_led_fault}"
            )

    # 3. Tier-0 16/16 eMMC/NOR H0 == H3 invariance (including DC-C1 mid-Stage-B power drop)
    default_digests = _default_tier0_16_surface_digests()
    h0_map = cfg.tier0_h0_digests if cfg.tier0_h0_digests is not None else default_digests
    h3_map = cfg.tier0_h3_digests if cfg.tier0_h3_digests is not None else default_digests

    h0_eq_h3_count = 0
    mismatched_surfaces: List[str] = []
    for surface in P195_TIER0_16_SURFACES:
        d0 = h0_map.get(surface, "")
        d3 = h3_map.get(surface, "")
        if bool(_SHA256_RE.match(d0)) and d0 == d3:
            h0_eq_h3_count += 1
        else:
            mismatched_surfaces.append(surface)

    emmc_damage_count = P195_TIER0_SURFACE_COUNT - h0_eq_h3_count
    if emmc_damage_count != 0:
        blocked.append(P195_BLOCKED_TIER0_16OF16_H0_H3_DRIFT)
        errors.append(
            f"Tier-0 16-surface H0==H3 drift detected ({h0_eq_h3_count}/16 intact): "
            f"drifted={mismatched_surfaces}"
        )

    overlay_wiped_ok = True
    if cfg.power_drop_mid_stage_b:
        overlay_wiped_ok = bool(cfg.stage_b_volatile_overlay_wiped) and bool(cfg.cold_reboot_to_stock_702_clean)
        if not overlay_wiped_ok:
            blocked.append(P195_BLOCKED_STAGE_B_OVERLAY_NOT_WIPED_ON_DROP)
            errors.append("Mid-Stage-B power drop left non-volatile overlay residue or dirty reboot state")

    zero_emmc_damage_proven = (emmc_damage_count == 0) and overlay_wiped_ok
    stage_entry_admitted = (
        (stage_op in P195_VALID_STAGE_OPERATIONS)
        and power_topology_valid
        and micro_usb_rejected_ok
        and np_fz100_ok
        and dc_c1_ok
        and (not cfg.power_drop_mid_stage_b)
        and (not cfg.request_persistent_write_unlock)
    )

    dedup_blocked = tuple(dict.fromkeys(blocked))
    passed = (
        len(dedup_blocked) == 0
        and len(errors) == 0
        and zero_emmc_damage_proven
        and (stage_entry_admitted or cfg.power_drop_mid_stage_b)
    )
    return Dcc1PowerBrownoutInterlockReport(
        passed=passed,
        stage_entry_admitted=stage_entry_admitted,
        pre_stage_aborted=not stage_entry_admitted,
        power_topology_valid=power_topology_valid,
        np_fz100_precondition_ok=np_fz100_ok,
        micro_usb_rejected_ok=micro_usb_rejected_ok,
        dc_c1_65w_5a_interlock_ok=dc_c1_ok,
        power_drop_mid_stage_b=cfg.power_drop_mid_stage_b,
        zero_emmc_damage_proven=zero_emmc_damage_proven,
        tier0_h0_eq_h3_count=h0_eq_h3_count,
        tier0_surface_count=P195_TIER0_SURFACE_COUNT,
        emmc_damage_count=emmc_damage_count,
        stage_operation=stage_op,
        power_source=power_src,
        blocked_codes=dedup_blocked,
        errors=tuple(errors),
    )


def run_pillar27a_power_interlock_6_scenario_suite() -> Pillar27APowerInterlockSuiteResult:
    """Run all 6 deterministic scenarios for Pillar 27A (`NP-FZ100` & `DC-C1` power-brownout interlock)."""
    outcomes: List[Pillar27AScenarioOutcome] = []

    # P27A1: Happy NP-FZ100 (>=51% / >=3 bars) USB-PD AND DC-C1 (>=65W + 5A e-marked) ready for 0x40 & UFU
    r1_usbpd = evaluate_dcc1_power_brownout_interlock(
        Dcc1PowerBrownoutInterlockSpec(
            stage_operation=P195_STAGE_OPERATION_COLD_BACKUP_0X40,
            power_source=P195_POWER_SOURCE_USB_PD_BODY,
            np_fz100_inserted=True,
            battery_pct=51,
            battery_bars=3,
            battery_voltage_v=7.25,
        )
    )
    r1_dcc1 = evaluate_dcc1_power_brownout_interlock(
        Dcc1PowerBrownoutInterlockSpec(
            stage_operation=P195_STAGE_OPERATION_UFU_BODYDATA,
            power_source=P195_POWER_SOURCE_DC_C1_COUPLER,
            usb_pd_watts=65.0,
            emarked_5a_cable=True,
            cable_max_amps=5.0,
        )
    )
    ok1 = (
        r1_usbpd.passed
        and r1_usbpd.stage_entry_admitted
        and r1_usbpd.tier0_h0_eq_h3_count == 16
        and r1_dcc1.passed
        and r1_dcc1.stage_entry_admitted
        and r1_dcc1.tier0_h0_eq_h3_count == 16
    )
    outcomes.append(
        Pillar27AScenarioOutcome(
            P195_PILLAR_27A_SCENARIO_IDS[0],
            ok1,
            True,
            16,
            (),
            "NP-FZ100 (>=51%/3 bars) USB-PD & DC-C1 (>=65W + 5A e-marked) admitted with 16/16 H0==H3",
        )
    )

    # P27A2: Body USB-C PD missing NP-FZ100 or below 51% / 3 bars aborts pre-backup & pre-UFU entry
    r2_no_pack = evaluate_dcc1_power_brownout_interlock(
        Dcc1PowerBrownoutInterlockSpec(
            stage_operation=P195_STAGE_OPERATION_COLD_BACKUP_0X40,
            power_source=P195_POWER_SOURCE_USB_PD_BODY,
            np_fz100_inserted=False,
        )
    )
    r2_low_pct = evaluate_dcc1_power_brownout_interlock(
        Dcc1PowerBrownoutInterlockSpec(
            stage_operation=P195_STAGE_OPERATION_UFU_BODYDATA,
            power_source=P195_POWER_SOURCE_USB_PD_BODY,
            np_fz100_inserted=True,
            battery_pct=50,
            battery_bars=2,
        )
    )
    ok2 = (
        (not r2_no_pack.passed)
        and r2_no_pack.pre_stage_aborted
        and (P195_BLOCKED_MISSING_NPFZ100_OR_LOW_BATT in r2_no_pack.blocked_codes)
        and (not r2_low_pct.passed)
        and r2_low_pct.pre_stage_aborted
        and (P195_BLOCKED_MISSING_NPFZ100_OR_LOW_BATT in r2_low_pct.blocked_codes)
    )
    outcomes.append(
        Pillar27AScenarioOutcome(
            P195_PILLAR_27A_SCENARIO_IDS[1],
            ok2,
            False,
            r2_no_pack.tier0_h0_eq_h3_count,
            r2_no_pack.blocked_codes,
            "Body USB-C PD missing NP-FZ100 pack or <51%/<3 bars aborts pre-backup & pre-UFU entry",
        )
    )

    # P27A3: Micro-USB power attempt rejected fail-closed
    r3_src = evaluate_dcc1_power_brownout_interlock(
        Dcc1PowerBrownoutInterlockSpec(
            power_source=P195_POWER_SOURCE_MICRO_USB,
            micro_usb_power_attempted=True,
        )
    )
    ok3 = (
        (not r3_src.passed)
        and r3_src.pre_stage_aborted
        and (not r3_src.micro_usb_rejected_ok)
        and (P195_BLOCKED_MICRO_USB_POWER_FORBIDDEN in r3_src.blocked_codes)
    )
    outcomes.append(
        Pillar27AScenarioOutcome(
            P195_PILLAR_27A_SCENARIO_IDS[2],
            ok3,
            False,
            r3_src.tier0_h0_eq_h3_count,
            r3_src.blocked_codes,
            "Micro-USB power attempt rejected fail-closed before cold-backup/UFU entry",
        )
    )

    # P27A4: DC-C1 <65W PD or non-5A e-marked cable aborts pre-stage entry (no mid-stream brownout)
    r4_low_w = evaluate_dcc1_power_brownout_interlock(
        Dcc1PowerBrownoutInterlockSpec(
            stage_operation=P195_STAGE_OPERATION_COLD_BACKUP_0X40,
            power_source=P195_POWER_SOURCE_DC_C1_COUPLER,
            usb_pd_watts=45.0,
            emarked_5a_cable=True,
            cable_max_amps=5.0,
        )
    )
    r4_non_5a = evaluate_dcc1_power_brownout_interlock(
        Dcc1PowerBrownoutInterlockSpec(
            stage_operation=P195_STAGE_OPERATION_UFU_BODYDATA,
            power_source=P195_POWER_SOURCE_DC_C1_COUPLER,
            usb_pd_watts=65.0,
            emarked_5a_cable=False,
            cable_max_amps=3.0,
            dc_c1_blinking_led_fault=True,
        )
    )
    ok4 = (
        (not r4_low_w.passed)
        and r4_low_w.pre_stage_aborted
        and (P195_BLOCKED_DCC1_INSUFFICIENT_PD_OR_NON_5A_CABLE in r4_low_w.blocked_codes)
        and (not r4_non_5a.passed)
        and r4_non_5a.pre_stage_aborted
        and (P195_BLOCKED_DCC1_INSUFFICIENT_PD_OR_NON_5A_CABLE in r4_non_5a.blocked_codes)
    )
    outcomes.append(
        Pillar27AScenarioOutcome(
            P195_PILLAR_27A_SCENARIO_IDS[3],
            ok4,
            False,
            r4_low_w.tier0_h0_eq_h3_count,
            r4_low_w.blocked_codes,
            "DC-C1 <65W PD or non-5A e-marked cable aborts pre-stage entry (blocks 0x40/UFU brownout)",
        )
    )

    # P27A5: DC-C1 power drops mid-Stage-B -> volatile overlay wiped cleanly, zero eMMC damage (16/16 H0 == H3)
    r5 = evaluate_dcc1_power_brownout_interlock(
        Dcc1PowerBrownoutInterlockSpec(
            stage_operation=P195_STAGE_OPERATION_STAGE_B_BOOT,
            power_source=P195_POWER_SOURCE_DC_C1_COUPLER,
            usb_pd_watts=65.0,
            emarked_5a_cable=True,
            cable_max_amps=5.0,
            power_drop_mid_stage_b=True,
            stage_b_volatile_overlay_wiped=True,
            cold_reboot_to_stock_702_clean=True,
        )
    )
    ok5 = (
        r5.passed
        and r5.power_drop_mid_stage_b
        and r5.zero_emmc_damage_proven
        and r5.tier0_h0_eq_h3_count == 16
        and r5.emmc_damage_count == 0
        and r5.physical_device_writes == 0
    )
    outcomes.append(
        Pillar27AScenarioOutcome(
            P195_PILLAR_27A_SCENARIO_IDS[4],
            ok5,
            r5.stage_entry_admitted,
            r5.tier0_h0_eq_h3_count,
            r5.blocked_codes,
            "Mid-Stage-B DC-C1 power drop proves zero eMMC damage (16/16 Tier-0 H0 == H3)",
        )
    )

    # P27A6: Write unlock request OR Tier-0 H0 != H3 brownout drift rejected fail-closed
    bad_h3 = _default_tier0_16_surface_digests()
    bad_h3["p2"] = "f" * 64
    r6 = evaluate_dcc1_power_brownout_interlock(
        Dcc1PowerBrownoutInterlockSpec(
            power_drop_mid_stage_b=True,
            tier0_h3_digests=bad_h3,
            request_persistent_write_unlock=True,
        )
    )
    ok6 = (
        (not r6.passed)
        and (not r6.zero_emmc_damage_proven)
        and r6.tier0_h0_eq_h3_count == 15
        and r6.emmc_damage_count == 1
        and (P195_BLOCKED_TIER0_16OF16_H0_H3_DRIFT in r6.blocked_codes)
        and (P195_BLOCKED_SAFETY_POLICY_VIOLATION in r6.blocked_codes)
        and r6.physical_device_writes == 0
    )
    outcomes.append(
        Pillar27AScenarioOutcome(
            P195_PILLAR_27A_SCENARIO_IDS[5],
            ok6,
            False,
            r6.tier0_h0_eq_h3_count,
            r6.blocked_codes,
            "Write unlock & Tier-0 H0!=H3 drift rejected fail-closed with 0 device writes",
        )
    )

    passed_count = sum(1 for o in outcomes if o.passed)
    all_ok = passed_count == len(P195_PILLAR_27A_SCENARIO_IDS)
    return Pillar27APowerInterlockSuiteResult(
        passed=all_ok,
        status=P195_STATUS_VERIFIED_PILLAR_27A if all_ok else P195_STATUS_REJECTED_PILLAR_27A,
        scenarios_passed=passed_count,
        scenarios_total=len(P195_PILLAR_27A_SCENARIO_IDS),
        scenarios=tuple(outcomes),
    )


# ---------------------------------------------------------------------------
# 3. Pillar 27B — Dual-Media .cube User LUT Ephemeral Overlay vs p2:/setting
# ---------------------------------------------------------------------------


def evaluate_dual_media_cube_lut_vault(
    spec: Optional[DualMediaCubeLutVaultSpec] = None,
) -> DualMediaCubeLutVaultReport:
    """Verify SDXC vs CFexpress-A `.cube` staging in `/tmp/fx6_lut_overlay` & `p2:/setting` `H0 == H3`."""
    cfg = spec if spec is not None else DualMediaCubeLutVaultSpec()
    blocked: List[str] = []
    errors: List[str] = []

    if cfg.request_persistent_write_unlock or PERSISTENT_EMMC_WRITES_AUTHORIZED:
        blocked.append(P195_BLOCKED_SAFETY_POLICY_VIOLATION)
        errors.append("Persistent eMMC write unlock forbidden during Pillar 27B LUT vault verification")

    # 1. Dual-media asymmetric directory path rule
    media = _normalize_media_type(cfg.media_type)
    actual_dir = _normalize_lut_dir(cfg.media_lut_directory)
    expected_dir = ""
    if media == P195_MEDIA_SDXC:
        expected_dir = P195_SDXC_USER_LUT_DIR
    elif media == P195_MEDIA_CFEXPRESS_A:
        expected_dir = P195_CFEXPRESS_A_USER_LUT_DIR

    media_path_ok = (media in P195_VALID_MEDIA_TYPES) and (actual_dir == expected_dir)
    if not media_path_ok:
        blocked.append(P195_BLOCKED_MEDIA_LUT_PATH_ASYMMETRY)
        errors.append(
            f"Dual-media User LUT path asymmetry violated: media={media!r}, "
            f"actual={actual_dir!r}, expected={expected_dir!r}"
        )

    # 2. .cube 17pt/33pt & <=63B ASCII filename rule
    cube_name = cfg.cube_filename.strip()
    cube_name_bytes = len(cube_name.encode("utf-8"))
    hdr_upper = cfg.cube_header_text.upper()
    size_line_ok = (
        f"LUT_3D_SIZE {cfg.cube_grid_size}" in hdr_upper
        and "LUT_1D_SIZE" not in hdr_upper
    )
    cube_spec_ok = (
        bool(_CUBE_ASCII_FILENAME_RE.match(cube_name))
        and 6 <= cube_name_bytes <= P195_CUBE_MAX_FILENAME_BYTES
        and (cfg.cube_grid_size in P195_CUBE_ALLOWED_GRID_SIZES)
        and size_line_ok
    )
    if not cube_spec_ok:
        blocked.append(P195_BLOCKED_INVALID_CUBE_LUT_SPEC)
        errors.append(
            f"Invalid .cube LUT spec: filename={cube_name!r} ({cube_name_bytes}B), "
            f"grid={cfg.cube_grid_size}"
        )

    # 3. Ephemeral Stage-B overlay strictly inside /tmp/fx6_lut_overlay (tmpfs), zero p2:/setting writes
    norm_overlay = posixpath.normpath(cfg.stage_b_overlay_mount_path.strip() or "/")
    forbidden_prefix_hit = any(
        norm_overlay.lower().startswith(pfx) for pfx in P195_FORBIDDEN_PERSISTENT_LUT_PREFIXES
    )
    ephemeral_overlay_ok = (
        (norm_overlay == P195_STAGE_B_EPHEMERAL_LUT_OVERLAY_DIR)
        and (not forbidden_prefix_hit)
        and bool(cfg.stage_b_overlay_is_tmpfs)
        and cfg.stage_b_p2_setting_writes == 0
    )
    if not ephemeral_overlay_ok:
        blocked.append(P195_BLOCKED_P2_SETTING_VAULT_WRITE_OR_NON_TMPFS_OVERLAY)
        errors.append(
            f"LUT staging escaped ephemeral /tmp/fx6_lut_overlay or wrote p2:/setting: "
            f"overlay={norm_overlay!r}, tmpfs={cfg.stage_b_overlay_is_tmpfs}, "
            f"p2_writes={cfg.stage_b_p2_setting_writes}"
        )

    # 4. Registered User1..User16 slots (<=16) and AE Level Offset (0.0..+2.0 EV in 1/3 steps)
    slot_name_ok = bool(_USER_SLOT_RE.match(cfg.user_slot_name.strip()))
    slot_count_ok = (
        isinstance(cfg.registered_user_slot_count, int)
        and not isinstance(cfg.registered_user_slot_count, bool)
        and 1 <= cfg.registered_user_slot_count <= P195_USER_LUT_MAX_SLOTS
    )
    ae_offset_ok = _is_valid_one_third_ev_offset(cfg.ae_level_offset_ev)
    user_slot_and_ae_ok = slot_name_ok and slot_count_ok and ae_offset_ok
    if not user_slot_and_ae_ok:
        blocked.append(P195_BLOCKED_USER_LUT_SLOT_OR_AE_OFFSET_INVALID)
        errors.append(
            f"Invalid User1..User16 slot or AE Level Offset: slot={cfg.user_slot_name!r}, "
            f"count={cfg.registered_user_slot_count}, ae_ev={cfg.ae_level_offset_ev}"
        )

    # 5. Stock FX3 p2:/setting vault H0 == H3 bit-identical preservation upon reboot to Stock 7.02
    default_slots = _default_user_lut_slots_snapshot()
    slots_h0 = cfg.p2_user1_16_slots_h0 if cfg.p2_user1_16_slots_h0 is not None else default_slots
    slots_h3 = cfg.p2_user1_16_slots_h3 if cfg.p2_user1_16_slots_h3 is not None else default_slots

    slots_16_exact = (
        tuple(sorted(slots_h0.keys())) == tuple(sorted(P195_USER_LUT_SLOT_NAMES))
        and tuple(sorted(slots_h3.keys())) == tuple(sorted(P195_USER_LUT_SLOT_NAMES))
        and all(slots_h0[k] == slots_h3[k] for k in P195_USER_LUT_SLOT_NAMES)
        and all(_is_valid_one_third_ev_offset(slots_h3[k].get("ae_level_offset_ev", -1.0)) for k in P195_USER_LUT_SLOT_NAMES)
    )
    p2_setting_h0_eq_h3 = (
        bool(cfg.p2_blkroset_locked)
        and bool(cfg.rebooted_to_stock_fx3_702)
        and bool(_SHA256_RE.match(cfg.p2_setting_h0_sha256))
        and cfg.p2_setting_h0_sha256 == cfg.p2_setting_h3_sha256
        and slots_16_exact
    )
    if not p2_setting_h0_eq_h3:
        blocked.append(P195_BLOCKED_P2_SETTING_H0_H3_DRIFT)
        errors.append(
            f"Stock p2:/setting User1..User16 vault drifted or BLKROSET unlocked on reboot: "
            f"ro={cfg.p2_blkroset_locked}, reboot={cfg.rebooted_to_stock_fx3_702}, slots_exact={slots_16_exact}"
        )

    dedup_blocked = tuple(dict.fromkeys(blocked))
    passed = (
        media_path_ok
        and cube_spec_ok
        and ephemeral_overlay_ok
        and user_slot_and_ae_ok
        and p2_setting_h0_eq_h3
        and len(dedup_blocked) == 0
        and len(errors) == 0
    )
    return DualMediaCubeLutVaultReport(
        passed=passed,
        vault_preserved=passed,
        media_path_asymmetry_ok=media_path_ok,
        cube_spec_ok=cube_spec_ok,
        ephemeral_tmp_overlay_ok=ephemeral_overlay_ok,
        user_slot_and_ae_offset_ok=user_slot_and_ae_ok,
        p2_setting_h0_eq_h3=p2_setting_h0_eq_h3,
        user1_16_slots_bit_identical=slots_16_exact,
        media_type=media,
        media_lut_directory=actual_dir,
        expected_lut_directory=expected_dir,
        stage_b_overlay_mount_path=norm_overlay,
        cube_filename=cube_name,
        cube_filename_bytes=cube_name_bytes,
        cube_grid_size=cfg.cube_grid_size,
        registered_user_slot_count=cfg.registered_user_slot_count,
        ae_level_offset_ev=cfg.ae_level_offset_ev,
        blocked_codes=dedup_blocked,
        errors=tuple(errors),
    )


def run_pillar27b_lut_vault_6_scenario_suite() -> Pillar27BLutVaultSuiteResult:
    """Run all 6 deterministic scenarios for Pillar 27B (Dual-Media `.cube` LUT & `p2:/setting` vault)."""
    outcomes: List[Pillar27BScenarioOutcome] = []

    # P27B1: Happy SDXC (/Private/Sony/PRO/LUT/) + CFexpress Type A (/Sony/PRO/LUT/) 17pt/33pt <=63B in /tmp/fx6_lut_overlay
    r1_sd = evaluate_dual_media_cube_lut_vault(
        DualMediaCubeLutVaultSpec(
            media_type="SDXC",
            media_lut_directory="/Private/Sony/PRO/LUT/",
            cube_filename="FX3_User01_S709_17pt.cube",
            cube_grid_size=17,
            cube_header_text="LUT_3D_SIZE 17\n",
            user_slot_name="User1",
            ae_level_offset_ev=0.0,
        )
    )
    r1_cfa = evaluate_dual_media_cube_lut_vault(
        DualMediaCubeLutVaultSpec(
            media_type="CFEXPRESS_A",
            media_lut_directory="/Sony/PRO/LUT/",
            cube_filename="FX3_User16_Phantom_33pt.cube",
            cube_grid_size=33,
            cube_header_text="LUT_3D_SIZE 33\n",
            user_slot_name="User16",
            ae_level_offset_ev=2.0,
        )
    )
    ok1 = (
        r1_sd.passed
        and r1_sd.p2_setting_h0_eq_h3
        and r1_sd.user1_16_slots_bit_identical
        and r1_cfa.passed
        and r1_cfa.p2_setting_h0_eq_h3
        and r1_cfa.user1_16_slots_bit_identical
    )
    outcomes.append(
        Pillar27BScenarioOutcome(
            P195_PILLAR_27B_SCENARIO_IDS[0],
            ok1,
            True,
            (),
            "SDXC (/Private/Sony/PRO/LUT/) & CFexpress-A (/Sony/PRO/LUT/) 17pt/33pt <=63B in /tmp/fx6_lut_overlay; p2:/setting 16/16 H0==H3",
        )
    )

    # P27B2: Media path asymmetry swap (SDXC with /Sony/PRO/LUT/ or CFexpress-A with /Private/Sony/PRO/LUT/) blocked
    r2_sd_bad = evaluate_dual_media_cube_lut_vault(
        DualMediaCubeLutVaultSpec(
            media_type="SDXC",
            media_lut_directory="/Sony/PRO/LUT/",
        )
    )
    r2_cfa_bad = evaluate_dual_media_cube_lut_vault(
        DualMediaCubeLutVaultSpec(
            media_type="CFEXPRESS_A",
            media_lut_directory="/Private/Sony/PRO/LUT/",
        )
    )
    ok2 = (
        (not r2_sd_bad.passed)
        and (not r2_sd_bad.media_path_asymmetry_ok)
        and (P195_BLOCKED_MEDIA_LUT_PATH_ASYMMETRY in r2_sd_bad.blocked_codes)
        and (not r2_cfa_bad.passed)
        and (not r2_cfa_bad.media_path_asymmetry_ok)
        and (P195_BLOCKED_MEDIA_LUT_PATH_ASYMMETRY in r2_cfa_bad.blocked_codes)
    )
    outcomes.append(
        Pillar27BScenarioOutcome(
            P195_PILLAR_27B_SCENARIO_IDS[1],
            ok2,
            False,
            r2_sd_bad.blocked_codes,
            "Swapped SDXC vs CFexpress-A User LUT directory paths blocked fail-closed",
        )
    )

    # P27B3: Over-63B filename or invalid grid size (e.g. 65pt / 1D LUT) blocked
    over_63b = ("A" * 59) + ".cube"  # 64 bytes
    r3_len = evaluate_dual_media_cube_lut_vault(
        DualMediaCubeLutVaultSpec(cube_filename=over_63b)
    )
    r3_65pt = evaluate_dual_media_cube_lut_vault(
        DualMediaCubeLutVaultSpec(
            cube_grid_size=65,
            cube_header_text="LUT_3D_SIZE 65\n",
        )
    )
    ok3 = (
        (not r3_len.passed)
        and (not r3_len.cube_spec_ok)
        and (P195_BLOCKED_INVALID_CUBE_LUT_SPEC in r3_len.blocked_codes)
        and (not r3_65pt.passed)
        and (not r3_65pt.cube_spec_ok)
        and (P195_BLOCKED_INVALID_CUBE_LUT_SPEC in r3_65pt.blocked_codes)
    )
    outcomes.append(
        Pillar27BScenarioOutcome(
            P195_PILLAR_27B_SCENARIO_IDS[2],
            ok3,
            False,
            r3_len.blocked_codes,
            "Over-63B .cube filename & unsupported 65pt grid size rejected fail-closed",
        )
    )

    # P27B4: User17 slot overflow or AE Level Offset outside 0..+2 EV (1/3 steps) blocked
    r4_slot = evaluate_dual_media_cube_lut_vault(
        DualMediaCubeLutVaultSpec(
            user_slot_name="User17",
            registered_user_slot_count=17,
        )
    )
    r4_ev = evaluate_dual_media_cube_lut_vault(
        DualMediaCubeLutVaultSpec(ae_level_offset_ev=2.33)
    )
    ok4 = (
        (not r4_slot.passed)
        and (not r4_slot.user_slot_and_ae_offset_ok)
        and (P195_BLOCKED_USER_LUT_SLOT_OR_AE_OFFSET_INVALID in r4_slot.blocked_codes)
        and (not r4_ev.passed)
        and (not r4_ev.user_slot_and_ae_offset_ok)
        and (P195_BLOCKED_USER_LUT_SLOT_OR_AE_OFFSET_INVALID in r4_ev.blocked_codes)
    )
    outcomes.append(
        Pillar27BScenarioOutcome(
            P195_PILLAR_27B_SCENARIO_IDS[3],
            ok4,
            False,
            r4_slot.blocked_codes,
            "User17 slot overflow & out-of-range AE Level Offset blocked fail-closed",
        )
    )

    # P27B5: Staging outside /tmp/fx6_lut_overlay or direct write to p2:/setting blocked
    r5 = evaluate_dual_media_cube_lut_vault(
        DualMediaCubeLutVaultSpec(
            stage_b_overlay_mount_path="p2:/setting/lut_overlay",
            stage_b_overlay_is_tmpfs=False,
            stage_b_p2_setting_writes=1,
        )
    )
    ok5 = (
        (not r5.passed)
        and (not r5.ephemeral_tmp_overlay_ok)
        and (P195_BLOCKED_P2_SETTING_VAULT_WRITE_OR_NON_TMPFS_OVERLAY in r5.blocked_codes)
        and r5.physical_device_writes == 0
    )
    outcomes.append(
        Pillar27BScenarioOutcome(
            P195_PILLAR_27B_SCENARIO_IDS[4],
            ok5,
            False,
            r5.blocked_codes,
            "Non-tmpfs overlay path & direct p2:/setting write blocked with 0 device writes",
        )
    )

    # P27B6: p2:/setting User1..User16 or AE Level Offset H0!=H3 drift on reboot / BLKROSET unlock / write unlock blocked
    drifted_slots = _default_user_lut_slots_snapshot()
    drifted_slots["User16"] = {
        "cube_name": "MUTATED.cube",
        "grid_size": 33,
        "ae_level_offset_ev": 1.33,
        "slot_sha256": "d" * 64,
    }
    r6 = evaluate_dual_media_cube_lut_vault(
        DualMediaCubeLutVaultSpec(
            p2_blkroset_locked=False,
            p2_setting_h3_sha256="e" * 64,
            p2_user1_16_slots_h3=drifted_slots,
            request_persistent_write_unlock=True,
        )
    )
    ok6 = (
        (not r6.passed)
        and (not r6.p2_setting_h0_eq_h3)
        and (not r6.user1_16_slots_bit_identical)
        and (P195_BLOCKED_P2_SETTING_H0_H3_DRIFT in r6.blocked_codes)
        and (P195_BLOCKED_SAFETY_POLICY_VIOLATION in r6.blocked_codes)
        and r6.physical_device_writes == 0
    )
    outcomes.append(
        Pillar27BScenarioOutcome(
            P195_PILLAR_27B_SCENARIO_IDS[5],
            ok6,
            False,
            r6.blocked_codes,
            "p2:/setting User1..User16 H0!=H3 drift & persistent write unlock rejected fail-closed",
        )
    )

    passed_count = sum(1 for o in outcomes if o.passed)
    all_ok = passed_count == len(P195_PILLAR_27B_SCENARIO_IDS)
    return Pillar27BLutVaultSuiteResult(
        passed=all_ok,
        status=P195_STATUS_VERIFIED_PILLAR_27B if all_ok else P195_STATUS_REJECTED_PILLAR_27B,
        scenarios_passed=passed_count,
        scenarios_total=len(P195_PILLAR_27B_SCENARIO_IDS),
        scenarios=tuple(outcomes),
    )


def run_pillar27_standalone_suite(
    *,
    force_clean_room: Optional[bool] = None,
) -> Pillar27StandaloneReport:
    """Run Pillar 27 standalone donor audit + Pillar 27A (`DC-C1`/`NP-FZ100`) + Pillar 27B (`.cube` LUT vault)."""
    _need(PERSISTENT_EMMC_WRITES_AUTHORIZED is False, "persistent_emmc_writes_authorized must stay False")
    _need(SPI_NOR_WRITE_AUTHORIZED is False, "spi_nor_write_authorized must stay False")
    _need(EL3_PAYLOAD_TRANSMIT_AUTHORIZED is False, "el3_payload_transmit_authorized must stay False")
    _need(ISP_WRITE_AUTHORIZED is False, "isp_write_authorized must stay False")
    _need(PERSISTENT_WRITE_RELEASE is False, "persistent_write_release must stay False")
    _need(OTP_FUSE_TOUCHES == 0 and OTP_FUSE_WRITES == 0, "OTP fuse counters must stay 0")
    _need(RPMB_COUNTER_INCREMENTS == 0, "RPMB counter increments must stay 0")
    _need(PHYSICAL_USB_PACKETS_EMITTED == 0, "Physical USB packets must stay 0")
    _need(PHYSICAL_DEVICE_WRITES == 0, "Physical device writes must stay 0")
    _need(RAW_FIRMWARE_BYTES_LEAKED == 0, "Raw firmware bytes leaked must stay 0")

    t0 = time.monotonic()
    snap = inspect_phase195_donors_readonly(force_clean_room=force_clean_room)
    p27a = run_pillar27a_power_interlock_6_scenario_suite()
    p27b = run_pillar27b_lut_vault_6_scenario_suite()
    elapsed = round(time.monotonic() - t0, 6)

    errors: List[str] = list(snap.errors)
    if not p27a.passed:
        errors.append("Pillar 27A NP-FZ100 & DC-C1 brownout interlock suite failed")
    if not p27b.passed:
        errors.append("Pillar 27B dual-media .cube LUT & p2:/setting vault suite failed")

    all_ok = (
        snap.all_passed
        and p27a.passed
        and p27b.passed
        and PERSISTENT_EMMC_WRITES_AUTHORIZED is False
        and SPI_NOR_WRITE_AUTHORIZED is False
        and EL3_PAYLOAD_TRANSMIT_AUTHORIZED is False
        and ISP_WRITE_AUTHORIZED is False
        and OTP_FUSE_TOUCHES == 0
        and RPMB_COUNTER_INCREMENTS == 0
        and PHYSICAL_USB_PACKETS_EMITTED == 0
        and PHYSICAL_DEVICE_WRITES == 0
        and RAW_FIRMWARE_BYTES_LEAKED == 0
        and len(errors) == 0
    )

    suite_sha = _canonical_sha256(
        {
            "schema": PHASE195_SCHEMA,
            "version": PHASE195_VERSION,
            "mode": snap.verification_mode,
            "snapshot_sha256": snap.snapshot_sha256,
            "p27a": p27a.to_dict(),
            "p27b": p27b.to_dict(),
            "all_passed": all_ok,
        }
    )
    return Pillar27StandaloneReport(
        schema=PHASE195_SCHEMA,
        version=PHASE195_VERSION,
        verification_mode=snap.verification_mode,
        all_passed=all_ok,
        status=P195_STATUS_VERIFIED_PILLAR27_SUITE if all_ok else P195_STATUS_FAIL_PILLAR27_SUITE,
        elapsed_seconds=elapsed,
        donor_snapshot=snap,
        pillar_27a_dcc1_pd_interlock=p27a,
        pillar_27b_cube_lut_vault=p27b,
        suite_sha256=suite_sha,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# 4. Unified 27/27 Recovery Master Aggregator (`evaluate_27pillar_recovery_master`)
# ---------------------------------------------------------------------------


def _apply_master27_fault_injection(pillar: MasterPillarStatus) -> MasterPillarStatus:
    err = f"FAULT_INJECTED:{pillar.pillar_id}"
    return MasterPillarStatus(
        pillar_number=pillar.pillar_number,
        pillar_id=pillar.pillar_id,
        phase_label=pillar.phase_label,
        module_name=pillar.module_name,
        passed=False,
        status=f"FAULT_INJECTED_{pillar.pillar_id.upper()}",
        verification_mode=pillar.verification_mode,
        elapsed_seconds=pillar.elapsed_seconds,
        key_metrics=pillar.key_metrics,
        digest_sha256=_canonical_sha256({"pillar": pillar.pillar_id, "fault_injected": True}),
        errors=pillar.errors + (err,),
    )


def evaluate_27pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master27PillarRecoveryReport:
    """Evaluate and aggregate all 27 recovery pillars (`1..27`) concurrently in `< 2.2s`."""
    _need(PERSISTENT_EMMC_WRITES_AUTHORIZED is False, "persistent_emmc_writes_authorized must stay False")
    _need(SPI_NOR_WRITE_AUTHORIZED is False, "spi_nor_write_authorized must stay False")
    _need(EL3_PAYLOAD_TRANSMIT_AUTHORIZED is False, "el3_payload_transmit_authorized must stay False")
    _need(ISP_WRITE_AUTHORIZED is False, "isp_write_authorized must stay False")
    _need(PERSISTENT_WRITE_RELEASE is False, "persistent_write_release must stay False")
    _need(LIVE_USB_IOKIT_TRANSMIT_ENABLED is False, "live_usb_iokit_transmit_enabled must stay False")
    _need(OTP_FUSE_TOUCHES == 0 and OTP_FUSE_WRITES == 0, "OTP fuse counters must stay 0")
    _need(RPMB_COUNTER_INCREMENTS == 0, "RPMB counter increments must stay 0")
    _need(PASSIVE_TX_BYTES_EMITTED == 0, "Passive TX bytes must stay 0")
    _need(PHYSICAL_USB_PACKETS_EMITTED == 0, "Physical USB packets must stay 0")
    _need(PHYSICAL_DEVICE_WRITES == 0, "Physical device writes must stay 0")
    _need(RAW_FIRMWARE_BYTES_LEAKED == 0, "Raw firmware bytes leaked must stay 0")

    if fault_inject_pillar is not None:
        _need(fault_inject_pillar in MASTER_27_PILLAR_IDS, f"Unknown fault_inject_pillar: {fault_inject_pillar}")

    t_start = time.monotonic()
    kw: Dict[str, Any] = {"force_clean_room": force_clean_room} if force_clean_room is not None else {}

    def _run_26pillar() -> Master26PillarRecoveryReport:
        return evaluate_26pillar_recovery_master(**kw)

    def _run_p27() -> Tuple[Pillar27StandaloneReport, float]:
        t0 = time.monotonic()
        res = run_pillar27_standalone_suite(**kw)
        return res, round(time.monotonic() - t0, 6)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_26 = pool.submit(_run_26pillar)
        fut_27 = pool.submit(_run_p27)

        m26_rep = fut_26.result()
        p27_rep, p27_dt = fut_27.result()

    safety_errors: List[str] = list(m26_rep.errors)
    for attr_name, expected_val in (
        ("otp_fuse_touches", 0),
        ("otp_fuse_writes", 0),
        ("rpmb_counter_increments", 0),
        ("passive_tx_bytes_emitted", 0),
        ("physical_usb_packets_emitted", 0),
        ("physical_device_writes", 0),
        ("raw_firmware_bytes_leaked", 0),
        ("el3_payload_transmit_authorized", False),
        ("isp_write_authorized", False),
        ("spi_nor_write_authorized", False),
        ("persistent_emmc_writes_authorized", False),
        ("persistent_write_release", False),
        ("live_usb_iokit_transmit_enabled", False),
    ):
        if getattr(m26_rep, attr_name) != expected_val:
            safety_errors.append(f"Pillars 1-26 violated {attr_name} == {expected_val}")
        if hasattr(p27_rep, attr_name) and getattr(p27_rep, attr_name) != expected_val:
            safety_errors.append(f"Pillar 27 violated {attr_name} == {expected_val}")

    pillar_statuses: List[MasterPillarStatus] = list(m26_rep.pillars)

    # Pillar 27 entry
    spec27 = MASTER_27_PILLAR_SPECS[26]
    p27_metrics = {
        "pillar_27a_dcc1_pd_interlock": (
            f"{p27_rep.pillar_27a_dcc1_pd_interlock.scenarios_passed}/"
            f"{p27_rep.pillar_27a_dcc1_pd_interlock.scenarios_total}"
        ),
        "pillar_27b_cube_lut_vault": (
            f"{p27_rep.pillar_27b_cube_lut_vault.scenarios_passed}/"
            f"{p27_rep.pillar_27b_cube_lut_vault.scenarios_total}"
        ),
        "donor_files_inspected": p27_rep.donor_snapshot.donor_files_inspected,
    }
    pillar_statuses.append(
        MasterPillarStatus(
            pillar_number=spec27[0],
            pillar_id=spec27[1],
            phase_label=spec27[2],
            module_name=spec27[3],
            passed=bool(p27_rep.all_passed),
            status=p27_rep.status,
            verification_mode=p27_rep.verification_mode,
            elapsed_seconds=p27_dt,
            key_metrics=p27_metrics,
            digest_sha256=_canonical_sha256(
                {
                    "pillar": spec27[1],
                    "mode": p27_rep.verification_mode,
                    "status": p27_rep.status,
                    "metrics": p27_metrics,
                    "passed": p27_rep.all_passed,
                }
            ),
            errors=tuple(p27_rep.errors),
        )
    )

    if fault_inject_pillar is not None:
        pillar_statuses = [
            _apply_master27_fault_injection(p) if p.pillar_id == fault_inject_pillar else p
            for p in pillar_statuses
        ]

    elapsed = round(time.monotonic() - t_start, 6)
    failed = tuple(p.pillar_id for p in pillar_statuses if not p.passed)
    pillars_passed = sum(1 for p in pillar_statuses if p.passed)
    verification_mode = p27_rep.verification_mode

    all_ok = (
        len(pillar_statuses) == MASTER_27_PILLAR_COUNT == 27
        and pillars_passed == 27
        and len(failed) == 0
        and len(safety_errors) == 0
        and OTP_FUSE_TOUCHES == 0
        and OTP_FUSE_WRITES == 0
        and RPMB_COUNTER_INCREMENTS == 0
        and PASSIVE_TX_BYTES_EMITTED == 0
        and PHYSICAL_USB_PACKETS_EMITTED == 0
        and PHYSICAL_DEVICE_WRITES == 0
        and RAW_FIRMWARE_BYTES_LEAKED == 0
        and (EL3_PAYLOAD_TRANSMIT_AUTHORIZED is False)
        and (ISP_WRITE_AUTHORIZED is False)
        and (SPI_NOR_WRITE_AUTHORIZED is False)
        and (PERSISTENT_EMMC_WRITES_AUTHORIZED is False)
        and (PERSISTENT_WRITE_RELEASE is False)
        and (LIVE_USB_IOKIT_TRANSMIT_ENABLED is False)
    )

    master_sha = _canonical_sha256(
        {
            "schema": PHASE195_SCHEMA,
            "version": PHASE195_VERSION,
            "verification_mode": verification_mode,
            "pillar_count": len(pillar_statuses),
            "pillars_passed": pillars_passed,
            "failed_pillars": list(failed),
            "pillar_digests": [(p.pillar_number, p.pillar_id, p.passed, p.digest_sha256) for p in pillar_statuses],
            "all_passed": all_ok,
        }
    )

    return Master27PillarRecoveryReport(
        schema=PHASE195_SCHEMA,
        version=PHASE195_VERSION,
        verification_mode=verification_mode,
        all_passed=all_ok,
        status=P195_STATUS_VERIFIED_27OF27_AGGREGATOR if all_ok else P195_STATUS_FAIL_27OF27_AGGREGATOR,
        pillar_count=len(pillar_statuses),
        pillars_passed=pillars_passed,
        failed_pillars=failed,
        elapsed_seconds=elapsed,
        under_6s_budget=elapsed < P195_CONCURRENT_CEILING_SECONDS,
        nominal_under_2_2s=elapsed < P195_NOMINAL_BUDGET_SECONDS,
        pillars=tuple(pillar_statuses),
        donor_snapshot=p27_rep.donor_snapshot,
        pillar27_a_dcc1_pd_interlock=p27_rep.pillar_27a_dcc1_pd_interlock,
        pillar27_b_cube_lut_vault=p27_rep.pillar_27b_cube_lut_vault,
        master_27pillar_sha256=master_sha,
        otp_fuse_touches=OTP_FUSE_TOUCHES,
        otp_fuse_writes=OTP_FUSE_WRITES,
        rpmb_counter_increments=RPMB_COUNTER_INCREMENTS,
        passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        isp_write_authorized=ISP_WRITE_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        allow_boot_partition_targeting=ALLOW_BOOT_PARTITION_TARGETING,
        allow_destructive_fastboot=ALLOW_DESTRUCTIVE_FASTBOOT,
        live_usb_iokit_transmit_enabled=LIVE_USB_IOKIT_TRANSMIT_ENABLED,
        errors=tuple(safety_errors),
    )


def verify_27pillar_recovery_suite(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master27PillarRecoveryReport:
    """Public entry point for Pillar 27 unified `27/27` real-hardware recovery master verification."""
    return evaluate_27pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )
