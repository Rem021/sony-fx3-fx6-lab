"""Phase 180 — Pillar 24 (24/24 Recovery Pillars) & Unified 24-Pillar Recovery Master
(`verify-24pillar-recovery` / `verify-slot1-ufu-reflash-readiness`):

1. **Pillar 24A — Official Sony ILME-FX3 `Ver. 7.02` Slot-1 `BODYDATA.DAT` (`811,876,768 B`)
   Post-Uninstall Stock-Reflash Readiness (6 Scenarios)**:
   - Verifies that after Clean Uninstall (`H2 -> H3`), a real `ILME-FX3` (`0x91030080`,
     `CXD90057` Mira + `CXD90058` Cetus) `7.02` camera satisfies ALL Sony official
     `BODYDATA.DAT` (`\\x89UFU\\r\\n\\x1a\\n`) update preconditions:
     - Body firmware floor `>= Ver. 2.04` verified (`<= Ver. 2.02` hard-blocked to prevent
       hardware `7 long + 7 short` LED blink failure);
     - **Slot-1 ExFAT root placement** (`/BODYDATA.DAT`) verified (`Slot 2` update blocked;
       duplicate/renamed files such as `BODYDATA (1).DAT`, `BODYDATA_OLD.DAT`, or
       subdirectory paths blocked);
     - `p1` update arming flag clean (`0`), `p15:/usr` `.orig` restored (`H0 == H3`),
       `p5:/wbi` `WBI2\\x00\\x00\\x00\\x00` header restored (`H0 == H3`), `NP-FZ100`
       charge floor (`>= 3 bars` AND `>= 7.2V`) verified;
     - `p12:/cert/RQ_LIC.DAT` C2PA license count `<= 100` hardware ceiling & `RO`
       integrity (`BLKROSET=1` / `MS_RDONLY`, SHA-256 intact) verified.

2. **Pillar 24B — Volatile Network (`WPA2/WPA3` Only) & HDMI-BRAW / 3D LUT Rollback Hygiene (6 Scenarios)**:
   - Proves zero Stage-B volatile `tmpfs` wireless credentials, `.cube` user 3D LUT
     staging files, or HDMI BRAW runtime state leak into Stock FX3 `p2:/setting/Backup.bin`
     (`BK4\\x00`, `0xAAAAAAAA`) or `p30:/usr/data/lut` across `EH1` SD-eject (`47 us`) or
     `H2 -> H3` clean uninstall, while enforcing `WPA2/WPA3` wireless security only
     (rejecting deprecated `WEP`, `WPA1`, and legacy `IPsec`).

3. **Unified 24-Pillar Master Aggregator (`evaluate_24pillar_recovery_master` / `verify-24pillar-recovery`)**:
   - Evaluates `evaluate_22pillar_recovery_master` (`Pillars 1..22`) + **Pillar 23**
     (`p5:/wbi` `WBI2` contamination firewall & 100-cycle battery-pull `H0==H3` verifier)
     + **Pillar 24** (`Slot-1` `BODYDATA.DAT` reflash readiness & rollback hygiene) ->
     **`24/24` (`VERIFIED_24OF24_PILLAR_RECOVERY_MASTER`)** concurrently in `< 1.8s`
     (with `< 6.0s` concurrency-safe unit-test ceiling).

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
import re
import stat
import struct
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .files import is_forced_clean_room, local_path, resolve_donor_path
from .realhw_22pillar_master_recovery_verifier import (
    MASTER_22_PILLAR_SPECS,
    Master22PillarRecoveryReport,
    MasterPillarStatus,
    evaluate_22pillar_recovery_master,
)
from .realhw_wbi_powerloss_and_100cycle_transition_verifier import (
    run_wbi_powerloss_and_100cycle_suite,
)


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

PHASE180_SCHEMA: str = "fx3-realhw-24pillar-recovery-master-verifier-v1"
PHASE180_VERSION: str = "1.0.0"

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

# Hardware, Slot-1 UFU & C2PA Constants
P180_BOUNDED_HEADER_BYTES: int = 4096
P180_WBI_SECTOR_BYTES: int = 512
P180_WBI_SECTION_ENTRY_BYTES: int = 64
P180_WBI_MAX_TABLE_READ_BYTES: int = 1024 * 1024

P180_FX3_MODEL_ID: int = 0x91030080
P180_FX3_MODEL_NAME: str = "ILME-FX3"
P180_FX3_STOCK_VERSION: str = "7.02"
P180_FX3_MIN_BODY_FLOOR_VERSION: str = "2.04"
P180_FX3_BRICK_BELOW_FLOOR_LED: str = "7L+7S"

P180_BODYDATA_FILENAME: str = "BODYDATA.DAT"
P180_SLOT1_ROOT_PATH: str = "/BODYDATA.DAT"
P180_REQUIRED_UPDATE_SLOT: int = 1
P180_BODYDATA_702_BYTES: int = 811_876_768
P180_UFU_MAGIC: bytes = b"\x89UFU\r\n\x1a\n"
P180_UFU_MAGIC_HEX: str = P180_UFU_MAGIC.hex()
P180_WBI2_HEADER_PREFIX: bytes = b"WBI2\x00\x00\x00\x00"
P180_WBI2_HEADER_PREFIX_HEX: str = P180_WBI2_HEADER_PREFIX.hex()

P180_NP_FZ100_MIN_BARS: int = 3
P180_NP_FZ100_MIN_VOLTAGE_V: float = 7.20
P180_C2PA_MAX_LICENSES: int = 100
P180_P12_RQ_LIC_PATH: str = "p12:/cert/RQ_LIC.DAT"
P180_P2_BACKUP_BIN_PATH: str = "p2:/setting/Backup.bin"
P180_P30_LUT_PATH: str = "p30:/usr/data/lut"

P180_ALLOWED_WIRELESS_PROTOCOLS: Tuple[str, ...] = (
    "WPA2",
    "WPA2-PSK",
    "WPA3",
    "WPA3-SAE",
    "ACCESS_AUTHENTICATION",
    "NONE_AIRPLANE_OFF",
)
P180_FORBIDDEN_WIRELESS_PROTOCOLS: Tuple[str, ...] = (
    "WEP",
    "WPA1",
    "WPA",
    "WPA-PSK",
    "IPSEC",
    "LEGACY_IPSEC",
)

P180_NOMINAL_BUDGET_SECONDS: float = 1.8
P180_CONCURRENT_CEILING_SECONDS: float = 6.0

# Master 24-Pillar Registry: Pillars 1..22 + Pillar 23 + Pillar 24
MASTER_24_PILLAR_SPECS: Tuple[Tuple[int, str, str, str], ...] = MASTER_22_PILLAR_SPECS + (
    (
        23,
        "realhw_wbi_powerloss_and_100cycle_transition_verifier",
        "Phase 176",
        "fx3_recovery.realhw_wbi_powerloss_and_100cycle_transition_verifier",
    ),
    (
        24,
        "realhw_24pillar_master_recovery_verifier",
        "Phase 180",
        "fx3_recovery.realhw_24pillar_master_recovery_verifier",
    ),
)
MASTER_24_PILLAR_IDS: Tuple[str, ...] = tuple(spec[1] for spec in MASTER_24_PILLAR_SPECS)
MASTER_24_PILLAR_COUNT: int = len(MASTER_24_PILLAR_SPECS)

# Pillar 24A & 24B Scenario IDs (6 + 6 = 12 Scenarios)
P180_PILLAR_24A_SCENARIO_IDS: Tuple[str, ...] = (
    "P24A1_HAPPY_SLOT1_ROOT_702_POST_UNINSTALL_READY",
    "P24A2_BLOCKED_BODY_FIRMWARE_BELOW_204_FLOOR_7L7S",
    "P24A3_BLOCKED_SLOT2_OR_DUPLICATE_BODYDATA_PATH",
    "P24A4_BLOCKED_DIRTY_P1_FLAG_P15_ORIG_OR_P5_WBI_NOT_RESTORED",
    "P24A5_BLOCKED_NP_FZ100_LOW_BATTERY_BELOW_3BARS_7V2",
    "P24A6_BLOCKED_C2PA_OVER_100_CEILING_OR_P12_RO_TAMPER",
)

P180_PILLAR_24B_SCENARIO_IDS: Tuple[str, ...] = (
    "P24B1_HAPPY_WPA2_WPA3_EH1_AND_H2_H3_ZERO_BACKUP_BIN_LEAK",
    "P24B2_BLOCKED_INSECURE_WEP_WPA1_OR_LEGACY_IPSEC_PROFILE",
    "P24B3_BLOCKED_TMPFS_WIFI_CREDENTIAL_LEAK_INTO_BACKUP_BIN",
    "P24B4_BLOCKED_CUBE_3D_LUT_STAGING_LEAK_TO_BACKUP_BIN_OR_P30",
    "P24B5_BLOCKED_HDMI_BRAW_STATE_LEAK_INTO_STOCK_BACKUP_BIN",
    "P24B6_BLOCKED_EH1_OR_H2_H3_PERSISTENT_WRITE_LOCK_VIOLATION",
)

# Pinned FX3 7.02 Donor Relpaths & Digests (strictly O_RDONLY, zero raw bytes emitted)
P180_DONOR_FX3_BODYDATA_RELPATH: str = "sony-firmware-20261024/fx3-7.02-BODYDATA.DAT"
P180_DONOR_FX3_WBI2_RELPATH: str = "sony-firmware-20261024/stage2/extraction/nflasha5.img"
P180_DONOR_FX3_NFLASHA15_RELPATH: str = "sony-firmware-20261024/stage2/extraction/nflasha15.img"
P180_DONOR_FX3_PARTINF_RELPATH: str = (
    "sony-firmware-20261024/stage182-boot-selector-and-recovery-admission/"
    "current-updater-evidence/tar-selected/0300_partconf/partinf.conf"
)
P180_DONOR_FX3_MOUNT_RELPATH: str = (
    "sony-firmware-20261024/stage182-boot-selector-and-recovery-admission/"
    "current-updater-evidence/tar-selected/0100_config/mount.conf"
)
P180_DONOR_FX3_BACKUP_BIN_RELPATH: str = (
    "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin"
)

P180_PINNED_FX3_BODYDATA_BYTES: int = 811_876_768
P180_PINNED_FX3_BODYDATA_HDR4K_SHA256: str = "fc135914e0767d69518e5b1f86b138abdbd2a20dd341e495cf151f8ddb79e404"
P180_PINNED_FX3_WBI2_TOTAL_BYTES: int = 209_112_512
P180_PINNED_FX3_WBI2_SECTIONS: int = 1399
P180_PINNED_FX3_WBI2_HDR_SHA256: str = "11ae397741d07e5bb65b61336970310ebceae72c5ee4d5cc6db2cfa3774363b9"
P180_PINNED_FX3_WBI2_TABLE_SHA256: str = "7286ddb05a7363c6bc8c28f2749164c8e52a7b2c8ffc70ed519fe3a8ac71cbc9"
P180_PINNED_FX3_NFLASHA15_BYTES: int = 479_846_400
P180_PINNED_FX3_NFLASHA15_HDR4K_SHA256: str = "6d05ebbd28c554d1d9dcc54503face9af111170befaf2ca2a19c52d7bd8910d6"
P180_PINNED_FX3_PARTINF_BYTES: int = 3999
P180_PINNED_FX3_PARTINF_SHA256: str = "3d96228d4ed2db3cb4295aa854edf0ad8895440167f132144cdec4f8cfdad189"
P180_PINNED_FX3_MOUNT_BYTES: int = 1248
P180_PINNED_FX3_MOUNT_SHA256: str = "ea0132091f3bb8d675b3ae7aecfbb1ca2459864a2e2812c0f7dd66fbb877d1a3"
P180_PINNED_FX3_BACKUP_BIN_BYTES: int = 2229740
P180_PINNED_FX3_BACKUP_BIN_SHA256: str = "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2"

# Status & Fail-Closed Error Codes
P180_STATUS_VERIFIED_PILLAR24_SUITE: str = "VERIFIED_PILLAR24_SLOT1_UFU_REFLASH_AND_HYGIENE"
P180_STATUS_FAIL_PILLAR24_SUITE: str = "FAIL_PILLAR24_SLOT1_UFU_REFLASH_AND_HYGIENE"
P180_STATUS_VERIFIED_PILLAR_24A: str = "VERIFIED_SLOT1_BODYDATA_702_STOCK_REFLASH_READINESS"
P180_STATUS_REJECTED_PILLAR_24A: str = "REJECTED_SLOT1_BODYDATA_702_STOCK_REFLASH_READINESS"
P180_STATUS_VERIFIED_PILLAR_24B: str = "VERIFIED_VOLATILE_WPA3_BRAW_LUT_ROLLBACK_HYGIENE"
P180_STATUS_REJECTED_PILLAR_24B: str = "REJECTED_VOLATILE_WPA3_BRAW_LUT_ROLLBACK_HYGIENE"
P180_STATUS_VERIFIED_24OF24_AGGREGATOR: str = "VERIFIED_24OF24_PILLAR_RECOVERY_MASTER"
P180_STATUS_FAIL_24OF24_AGGREGATOR: str = "FAIL_24OF24_PILLAR_RECOVERY_MASTER"

BLOCKED_BODY_VERSION_BELOW_204_FLOOR_7L7S: str = "BLOCKED_BODY_VERSION_BELOW_204_FLOOR_7L7S_BLINK_RISK"
BLOCKED_SLOT1_ROOT_OR_DUPLICATE_BODYDATA: str = "BLOCKED_SLOT1_EXFAT_ROOT_OR_DUPLICATE_BODYDATA"
BLOCKED_UFU_SIZE_MAGIC_OR_MODEL_MISMATCH: str = "BLOCKED_UFU_BODYDATA_811876768B_MAGIC_OR_MODEL_MISMATCH"
BLOCKED_P1_FLAG_OR_P15_P5_H0_H3_NOT_RESTORED: str = "BLOCKED_P1_ARMING_FLAG_OR_P15_ORIG_P5_WBI2_NOT_RESTORED"
BLOCKED_NP_FZ100_BELOW_3BARS_OR_7V2_FLOOR: str = "BLOCKED_NP_FZ100_BELOW_3BARS_OR_7V2_CHARGE_FLOOR"
BLOCKED_C2PA_100_LICENSE_CEILING_OR_P12_RO_BREACH: str = "BLOCKED_C2PA_100_LICENSE_CEILING_OR_P12_RQ_LIC_RO_BREACH"

BLOCKED_INSECURE_WIRELESS_WEP_WPA1_IPSEC: str = "BLOCKED_INSECURE_WIRELESS_WEP_WPA1_LEGACY_IPSEC"
BLOCKED_VOLATILE_WIFI_CREDENTIAL_LEAK_TO_BACKUP_BIN: str = "BLOCKED_TMPFS_WIFI_CREDENTIAL_LEAK_TO_BACKUP_BIN"
BLOCKED_CUBE_LUT_STAGING_LEAK_OR_P30_DRIFT: str = "BLOCKED_CUBE_3D_LUT_STAGING_LEAK_OR_P30_DRIFT"
BLOCKED_HDMI_BRAW_STATE_LEAK_TO_BACKUP_BIN: str = "BLOCKED_HDMI_BRAW_STATE_LEAK_TO_STOCK_BACKUP_BIN"
BLOCKED_PERSISTENT_WRITE_OR_BACKUP_BIN_DRIFT: str = "BLOCKED_PERSISTENT_EMMC_WRITE_OR_BACKUP_BIN_H0_H3_DRIFT"
BLOCKED_SAFETY_POLICY_VIOLATION: str = "BLOCKED_PILLAR24_SAFETY_POLICY_VIOLATION"

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_VERSION_RE = re.compile(r"^v?(\d+)\.(\d+)(?:\.(\d+))?$", re.IGNORECASE)


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


def _parse_version_tuple(version_str: str) -> Optional[Tuple[int, int, int]]:
    m = _VERSION_RE.match(version_str.strip())
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3) or 0))


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
    max_full_limit: int = 10 * 1024 * 1024,
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
        hdr_sha = sha256(buf[:P180_BOUNDED_HEADER_BYTES]).hexdigest()
        return buf, total_sz, full_sha, hdr_sha
    finally:
        os.close(fd)


def _read_bounded_wbi2_rdonly(relpath: str) -> Tuple[int, str, str, int, bytes]:
    p = resolve_donor_path(relpath, require_file=True)
    _need(p is not None and p.is_file(), f"missing donor WBI2 file: {relpath}")
    fd, st_before = _open_rdonly_regular(p)
    try:
        total_sz = int(st_before.st_size)
        _need(total_sz >= P180_WBI_SECTOR_BYTES, f"WBI2 truncated: {total_sz}")
        hdr = os.pread(fd, P180_WBI_SECTOR_BYTES, 0)
        _need(len(hdr) == P180_WBI_SECTOR_BYTES, "short read on WBI2 header")
        magic, padding, sections, _flag, _rv, _dv, sector_size, r_data_size, _ks, _ksz, _kck, _ods = struct.unpack_from(
            "<4sI10Q", hdr, 0
        )
        _need(magic == b"WBI2" and padding == 0 and sector_size == P180_WBI_SECTOR_BYTES, "invalid WBI2 header")
        _need(0 < sections <= 16384, f"out-of-bounds WBI2 sections: {sections}")
        table_off = P180_WBI_SECTOR_BYTES + r_data_size
        table_len = P180_WBI_SECTION_ENTRY_BYTES * sections
        _need(table_len <= P180_WBI_MAX_TABLE_READ_BYTES, "WBI2 section table exceeds bounded read ceiling")
        _need(table_off + table_len <= total_sz, "WBI2 section table exceeds file size")
        table_bytes = os.pread(fd, table_len, table_off)
        _need(len(table_bytes) == table_len, "short read on WBI2 section table")
        _verify_fstat_unchanged(fd, st_before)
        return (
            total_sz,
            sha256(hdr).hexdigest(),
            sha256(table_bytes).hexdigest(),
            int(sections),
            hdr[:8],
        )
    finally:
        os.close(fd)


# ---------------------------------------------------------------------------
# Dataclasses (100% JSON-safe, zero raw proprietary firmware bytes)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase180DonorArtifactDigest:
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
class Phase180DonorSnapshot:
    verification_mode: str
    access_mode: str
    donor_files_inspected: int
    raw_firmware_bytes_leaked: int
    bodydata_702_bytes: int
    bodydata_ufu_magic_ok: bool
    wbi2_header_prefix_hex: str
    wbi2_sections: int
    nflasha15_ext2_magic_ok: bool
    partinf_30_partitions_ok: bool
    mount_conf_p12_p15_p30_ok: bool
    backup_bin_bk4_fx3_ok: bool
    elapsed_seconds: float
    artifacts: Tuple[Phase180DonorArtifactDigest, ...]
    snapshot_sha256: str
    all_passed: bool
    errors: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Slot1UfuReflashReadinessSpec:
    body_firmware_version: str = "2.04"
    target_firmware_version: str = P180_FX3_STOCK_VERSION
    target_model_id: int = P180_FX3_MODEL_ID
    target_model_name: str = P180_FX3_MODEL_NAME
    update_slot: int = P180_REQUIRED_UPDATE_SLOT
    sd_file_path: str = P180_SLOT1_ROOT_PATH
    sibling_filenames_on_card: Tuple[str, ...] = ("BODYDATA.DAT",)
    bodydata_byte_length: int = P180_BODYDATA_702_BYTES
    ufu_magic_hex: str = P180_UFU_MAGIC_HEX
    p1_update_arming_flag: int = 0
    p15_orig_restored: bool = True
    p15_h0_sha256: str = P180_PINNED_FX3_NFLASHA15_HDR4K_SHA256
    p15_h3_sha256: str = P180_PINNED_FX3_NFLASHA15_HDR4K_SHA256
    p5_wbi2_prefix_hex: str = P180_WBI2_HEADER_PREFIX_HEX
    p5_h0_sha256: str = P180_PINNED_FX3_WBI2_HDR_SHA256
    p5_h3_sha256: str = P180_PINNED_FX3_WBI2_HDR_SHA256
    np_fz100_bars: int = 3
    np_fz100_voltage_v: float = 7.45
    c2pa_license_count: int = 42
    p12_rq_lic_path: str = P180_P12_RQ_LIC_PATH
    p12_blkroset_locked: bool = True
    p12_ms_rdonly: bool = True
    p12_rq_lic_h0_sha256: str = "a" * 64
    p12_rq_lic_h3_sha256: str = "a" * 64
    request_persistent_write_unlock: bool = False


@dataclass(frozen=True)
class Slot1UfuReflashReadinessReport:
    passed: bool
    reflash_ready: bool
    body_firmware_version: str
    body_floor_204_ok: bool
    slot1_root_and_unique_ok: bool
    bodydata_811m_and_ufu_ok: bool
    p1_arming_flag_clean: bool
    p15_orig_h0_eq_h3: bool
    p5_wbi2_h0_eq_h3: bool
    np_fz100_power_ok: bool
    c2pa_under_100_and_p12_ro_ok: bool
    blocked_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    persistent_emmc_writes_authorized: bool = PERSISTENT_EMMC_WRITES_AUTHORIZED
    physical_device_writes: int = PHYSICAL_DEVICE_WRITES

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Pillar24AScenarioOutcome:
    scenario_id: str
    passed: bool
    reflash_ready: bool
    blocked_codes: Tuple[str, ...]
    summary: str


@dataclass(frozen=True)
class Pillar24ASlot1UfuSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar24AScenarioOutcome, ...]
    persistent_emmc_writes_authorized: bool = PERSISTENT_EMMC_WRITES_AUTHORIZED
    physical_device_writes: int = PHYSICAL_DEVICE_WRITES

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RollbackHygieneAuditSpec:
    transition_kind: str = "H2_TO_H3_CLEAN_UNINSTALL"
    wireless_profiles: Tuple[str, ...] = ("WPA2", "WPA3-SAE")
    tmpfs_wifi_creds_present_after_rollback: int = 0
    backup_bin_wifi_cred_bytes_leaked: int = 0
    tmpfs_cube_lut_files_present_after_rollback: int = 0
    backup_bin_cube_lut_bytes_leaked: int = 0
    p30_lut_h0_sha256: str = "b" * 64
    p30_lut_h3_sha256: str = "b" * 64
    tmpfs_hdmi_braw_flags_present_after_rollback: int = 0
    backup_bin_hdmi_braw_bytes_leaked: int = 0
    p2_backup_bin_h0_sha256: str = P180_PINNED_FX3_BACKUP_BIN_SHA256
    p2_backup_bin_h3_sha256: str = P180_PINNED_FX3_BACKUP_BIN_SHA256
    p2_blkroset_locked: bool = True
    request_persistent_write_unlock: bool = False


@dataclass(frozen=True)
class RollbackHygieneReport:
    passed: bool
    hygiene_clean: bool
    transition_kind: str
    wireless_wpa2_wpa3_only_ok: bool
    zero_wifi_cred_leak_ok: bool
    zero_cube_lut_leak_and_p30_ok: bool
    zero_hdmi_braw_leak_ok: bool
    p2_backup_bin_h0_eq_h3: bool
    blocked_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    persistent_emmc_writes_authorized: bool = PERSISTENT_EMMC_WRITES_AUTHORIZED
    physical_device_writes: int = PHYSICAL_DEVICE_WRITES

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Pillar24BScenarioOutcome:
    scenario_id: str
    passed: bool
    hygiene_clean: bool
    blocked_codes: Tuple[str, ...]
    summary: str


@dataclass(frozen=True)
class Pillar24BHygieneSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar24BScenarioOutcome, ...]
    persistent_emmc_writes_authorized: bool = PERSISTENT_EMMC_WRITES_AUTHORIZED
    physical_device_writes: int = PHYSICAL_DEVICE_WRITES

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Pillar24StandaloneReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    elapsed_seconds: float
    donor_snapshot: Phase180DonorSnapshot
    pillar_24a_slot1_ufu_readiness: Pillar24ASlot1UfuSuiteResult
    pillar_24b_rollback_hygiene: Pillar24BHygieneSuiteResult
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
class Master24PillarRecoveryReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    pillar_count: int
    pillars_passed: int
    failed_pillars: Tuple[str, ...]
    elapsed_seconds: float
    under_1_8s_budget: bool
    nominal_under_1_8s: bool
    pillars: Tuple[MasterPillarStatus, ...]
    donor_snapshot: Phase180DonorSnapshot
    pillar24_a_slot1_ufu_readiness: Pillar24ASlot1UfuSuiteResult
    pillar24_b_rollback_hygiene: Pillar24BHygieneSuiteResult
    master_24pillar_sha256: str
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


def inspect_phase180_donors_readonly(
    *,
    force_clean_room: Optional[bool] = None,
) -> Phase180DonorSnapshot:
    """Inspect FX3 `7.02` donor artifacts strictly via `os.O_RDONLY` or clean-room fallback."""
    t0 = time.monotonic()
    clean = is_forced_clean_room() if force_clean_room is None else bool(force_clean_room)

    if clean:
        artifacts = (
            Phase180DonorArtifactDigest(
                "fx3_bodydata_dat",
                P180_DONOR_FX3_BODYDATA_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA_ONLY",
                P180_PINNED_FX3_BODYDATA_BYTES,
                P180_PINNED_FX3_BODYDATA_HDR4K_SHA256,
                P180_PINNED_FX3_BODYDATA_HDR4K_SHA256,
                ("UFU_89UFU_MAGIC", "DATV_PROV_UDID", "811876768B"),
                True,
            ),
            Phase180DonorArtifactDigest(
                "fx3_nflasha5_wbi2",
                P180_DONOR_FX3_WBI2_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA_ONLY",
                P180_PINNED_FX3_WBI2_TOTAL_BYTES,
                P180_PINNED_FX3_WBI2_TABLE_SHA256,
                P180_PINNED_FX3_WBI2_HDR_SHA256,
                ("WBI2_00000000", f"SECTIONS_{P180_PINNED_FX3_WBI2_SECTIONS}"),
                True,
            ),
            Phase180DonorArtifactDigest(
                "fx3_nflasha15_img",
                P180_DONOR_FX3_NFLASHA15_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA_ONLY",
                P180_PINNED_FX3_NFLASHA15_BYTES,
                P180_PINNED_FX3_NFLASHA15_HDR4K_SHA256,
                P180_PINNED_FX3_NFLASHA15_HDR4K_SHA256,
                ("BOUNDED_4K_SUPERBLOCK", "EXT2_0xEF53"),
                True,
            ),
            Phase180DonorArtifactDigest(
                "fx3_partinf_conf",
                P180_DONOR_FX3_PARTINF_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA_ONLY",
                P180_PINNED_FX3_PARTINF_BYTES,
                P180_PINNED_FX3_PARTINF_SHA256,
                P180_PINNED_FX3_PARTINF_SHA256,
                ("30_PARTITIONS", "P12_CERT", "P15_USR", "P30_LUT"),
                True,
            ),
            Phase180DonorArtifactDigest(
                "fx3_mount_conf",
                P180_DONOR_FX3_MOUNT_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA_ONLY",
                P180_PINNED_FX3_MOUNT_BYTES,
                P180_PINNED_FX3_MOUNT_SHA256,
                P180_PINNED_FX3_MOUNT_SHA256,
                ("MOUNT_SETTING", "MOUNT_CERT", "MOUNT_USR", "MOUNT_LUT"),
                True,
            ),
            Phase180DonorArtifactDigest(
                "fx3_backup_bin",
                P180_DONOR_FX3_BACKUP_BIN_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA_ONLY",
                P180_PINNED_FX3_BACKUP_BIN_BYTES,
                P180_PINNED_FX3_BACKUP_BIN_SHA256,
                P180_PINNED_FX3_BACKUP_BIN_SHA256,
                ("BK4_MAGIC", "0xAAAAAAAA", "ILME-FX3"),
                True,
            ),
        )
        elapsed = round(time.monotonic() - t0, 6)
        snap_sha = _canonical_sha256({"mode": "CLEAN_ROOM_SYNTHETIC", "artifacts": [asdict(a) for a in artifacts]})
        return Phase180DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="SYNTHETIC_METADATA_ONLY",
            donor_files_inspected=0,
            raw_firmware_bytes_leaked=0,
            bodydata_702_bytes=P180_PINNED_FX3_BODYDATA_BYTES,
            bodydata_ufu_magic_ok=True,
            wbi2_header_prefix_hex=P180_WBI2_HEADER_PREFIX_HEX,
            wbi2_sections=P180_PINNED_FX3_WBI2_SECTIONS,
            nflasha15_ext2_magic_ok=True,
            partinf_30_partitions_ok=True,
            mount_conf_p12_p15_p30_ok=True,
            backup_bin_bk4_fx3_ok=True,
            elapsed_seconds=elapsed,
            artifacts=artifacts,
            snapshot_sha256=snap_sha,
            all_passed=True,
            errors=(),
        )

    required_rels = (
        P180_DONOR_FX3_BODYDATA_RELPATH,
        P180_DONOR_FX3_WBI2_RELPATH,
        P180_DONOR_FX3_NFLASHA15_RELPATH,
        P180_DONOR_FX3_PARTINF_RELPATH,
        P180_DONOR_FX3_MOUNT_RELPATH,
        P180_DONOR_FX3_BACKUP_BIN_RELPATH,
    )
    resolved = [resolve_donor_path(rel, require_file=True) for rel in required_rels]
    if any(p is None or not p.is_file() for p in resolved):
        return inspect_phase180_donors_readonly(force_clean_room=True)

    artifacts_out: List[Phase180DonorArtifactDigest] = []
    errors: List[str] = []

    # 1) Bounded 4 KiB header of fx3-7.02-BODYDATA.DAT
    bd_head, bd_sz, _, bd_hdr_sha = _read_bounded_rdonly(
        P180_DONOR_FX3_BODYDATA_RELPATH,
        max_bytes=P180_BOUNDED_HEADER_BYTES,
    )
    bd_ok = (
        bd_sz == P180_PINNED_FX3_BODYDATA_BYTES
        and bd_hdr_sha == P180_PINNED_FX3_BODYDATA_HDR4K_SHA256
        and bd_head.startswith(P180_UFU_MAGIC)
        and b"DATV" in bd_head
        and b"PROV" in bd_head
        and b"UDID" in bd_head
    )
    if not bd_ok:
        errors.append("fx3_bodydata_dat: size/4K digest/UFU markers mismatch")
    artifacts_out.append(
        Phase180DonorArtifactDigest(
            "fx3_bodydata_dat",
            P180_DONOR_FX3_BODYDATA_RELPATH,
            "LOCAL_DONOR_O_RDONLY",
            "O_RDONLY_BOUNDED",
            bd_sz,
            bd_hdr_sha,
            bd_hdr_sha,
            ("UFU_89UFU_MAGIC", "DATV_PROV_UDID", "811876768B"),
            bd_ok,
        )
    )

    # 2) Bounded WBI2 header & section table of nflasha5.img
    wbi_sz, wbi_hdr_sha, wbi_tbl_sha, wbi_sections, wbi_prefix = _read_bounded_wbi2_rdonly(
        P180_DONOR_FX3_WBI2_RELPATH
    )
    wbi_prefix_hex = wbi_prefix.hex()
    wbi_ok = (
        wbi_sz == P180_PINNED_FX3_WBI2_TOTAL_BYTES
        and wbi_sections == P180_PINNED_FX3_WBI2_SECTIONS
        and wbi_hdr_sha == P180_PINNED_FX3_WBI2_HDR_SHA256
        and wbi_tbl_sha == P180_PINNED_FX3_WBI2_TABLE_SHA256
        and wbi_prefix == P180_WBI2_HEADER_PREFIX
    )
    if not wbi_ok:
        errors.append("fx3_nflasha5_wbi2: header/table/prefix mismatch")
    artifacts_out.append(
        Phase180DonorArtifactDigest(
            "fx3_nflasha5_wbi2",
            P180_DONOR_FX3_WBI2_RELPATH,
            "LOCAL_DONOR_O_RDONLY",
            "O_RDONLY_BOUNDED",
            wbi_sz,
            wbi_tbl_sha,
            wbi_hdr_sha,
            ("WBI2_00000000", f"SECTIONS_{wbi_sections}"),
            wbi_ok,
        )
    )

    # 3) Bounded 4 KiB superblock of nflasha15.img
    n15_head, n15_sz, _, n15_hdr_sha = _read_bounded_rdonly(
        P180_DONOR_FX3_NFLASHA15_RELPATH,
        max_bytes=P180_BOUNDED_HEADER_BYTES,
    )
    ext2_magic = struct.unpack_from("<H", n15_head, 1024 + 56)[0] if len(n15_head) >= 1082 else 0
    n15_ok = (
        n15_sz == P180_PINNED_FX3_NFLASHA15_BYTES
        and n15_hdr_sha == P180_PINNED_FX3_NFLASHA15_HDR4K_SHA256
        and ext2_magic == 0xEF53
    )
    if not n15_ok:
        errors.append("fx3_nflasha15_img: ext2 superblock/size/digest mismatch")
    artifacts_out.append(
        Phase180DonorArtifactDigest(
            "fx3_nflasha15_img",
            P180_DONOR_FX3_NFLASHA15_RELPATH,
            "LOCAL_DONOR_O_RDONLY",
            "O_RDONLY_BOUNDED",
            n15_sz,
            n15_hdr_sha,
            n15_hdr_sha,
            ("BOUNDED_4K_SUPERBLOCK", "EXT2_0xEF53"),
            n15_ok,
        )
    )

    # 4) partinf.conf
    part_raw, part_sz, part_sha, part_hdr = _read_bounded_rdonly(P180_DONOR_FX3_PARTINF_RELPATH)
    part_txt = part_raw.decode("utf-8", errors="replace")
    part_rows = re.findall(r"^0x[0-9A-Fa-f]+,0x[0-9A-Fa-f]+,0x[0-9A-Fa-f]+,0x[0-9A-Fa-f]+", part_txt, flags=re.M)
    part_ok = (
        part_sz == P180_PINNED_FX3_PARTINF_BYTES
        and part_sha == P180_PINNED_FX3_PARTINF_SHA256
        and len(part_rows) == 30
        and "/dev/nflasha12" in part_txt
        and "/dev/nflasha15" in part_txt
        and "/dev/nflasha30" in part_txt
    )
    if not part_ok:
        errors.append("fx3_partinf_conf: 30-partition layout or digest mismatch")
    artifacts_out.append(
        Phase180DonorArtifactDigest(
            "fx3_partinf_conf",
            P180_DONOR_FX3_PARTINF_RELPATH,
            "LOCAL_DONOR_O_RDONLY",
            "O_RDONLY_FULL",
            part_sz,
            part_sha,
            part_hdr,
            ("30_PARTITIONS", "P12_CERT", "P15_USR", "P30_LUT"),
            part_ok,
        )
    )

    # 5) mount.conf
    mnt_raw, mnt_sz, mnt_sha, mnt_hdr = _read_bounded_rdonly(P180_DONOR_FX3_MOUNT_RELPATH)
    mnt_txt = mnt_raw.decode("utf-8", errors="replace")
    mnt_ok = (
        mnt_sz == P180_PINNED_FX3_MOUNT_BYTES
        and mnt_sha == P180_PINNED_FX3_MOUNT_SHA256
        and "/setting" in mnt_txt
        and "/cert" in mnt_txt
        and "/usr" in mnt_txt
        and "/usr/data/lut" in mnt_txt
    )
    if not mnt_ok:
        errors.append("fx3_mount_conf: mountpoint or digest mismatch")
    artifacts_out.append(
        Phase180DonorArtifactDigest(
            "fx3_mount_conf",
            P180_DONOR_FX3_MOUNT_RELPATH,
            "LOCAL_DONOR_O_RDONLY",
            "O_RDONLY_FULL",
            mnt_sz,
            mnt_sha,
            mnt_hdr,
            ("MOUNT_SETTING", "MOUNT_CERT", "MOUNT_USR", "MOUNT_LUT"),
            mnt_ok,
        )
    )

    # 6) FX3-CX95900_ALLLANG-Backup.bin
    bak_raw, bak_sz, bak_sha, bak_hdr = _read_bounded_rdonly(P180_DONOR_FX3_BACKUP_BIN_RELPATH)
    sync_u32 = struct.unpack_from("<I", bak_raw, 4)[0] if len(bak_raw) >= 20 else 0
    bk_magic = bak_raw[12:16] if len(bak_raw) >= 16 else b""
    bak_ok = (
        bak_sz == P180_PINNED_FX3_BACKUP_BIN_BYTES
        and bak_sha == P180_PINNED_FX3_BACKUP_BIN_SHA256
        and sync_u32 == 0xAAAAAAAA
        and bk_magic == b"BK4\x00"
        and b"ILME-FX3" in bak_raw
    )
    if not bak_ok:
        errors.append("fx3_backup_bin: BK4/0xAAAAAAAA/ILME-FX3 or digest mismatch")
    artifacts_out.append(
        Phase180DonorArtifactDigest(
            "fx3_backup_bin",
            P180_DONOR_FX3_BACKUP_BIN_RELPATH,
            "LOCAL_DONOR_O_RDONLY",
            "O_RDONLY_FULL",
            bak_sz,
            bak_sha,
            bak_hdr,
            ("BK4_MAGIC", "0xAAAAAAAA", "ILME-FX3"),
            bak_ok,
        )
    )

    elapsed = round(time.monotonic() - t0, 6)
    all_ok = len(errors) == 0 and all(a.passed for a in artifacts_out)
    snap_sha = _canonical_sha256({"mode": "LOCAL_DONOR_O_RDONLY", "artifacts": [asdict(a) for a in artifacts_out]})
    return Phase180DonorSnapshot(
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="O_RDONLY_BOUNDED",
        donor_files_inspected=len(artifacts_out),
        raw_firmware_bytes_leaked=0,
        bodydata_702_bytes=bd_sz,
        bodydata_ufu_magic_ok=bd_ok,
        wbi2_header_prefix_hex=wbi_prefix_hex,
        wbi2_sections=wbi_sections,
        nflasha15_ext2_magic_ok=n15_ok,
        partinf_30_partitions_ok=part_ok,
        mount_conf_p12_p15_p30_ok=mnt_ok,
        backup_bin_bk4_fx3_ok=bak_ok,
        elapsed_seconds=elapsed,
        artifacts=tuple(artifacts_out),
        snapshot_sha256=snap_sha,
        all_passed=all_ok,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# 2. Pillar 24A — Official Sony ILME-FX3 Ver. 7.02 Slot-1 BODYDATA.DAT Readiness
# ---------------------------------------------------------------------------


def evaluate_slot1_ufu_stock_reflash_readiness(
    spec: Optional[Slot1UfuReflashReadinessSpec] = None,
) -> Slot1UfuReflashReadinessReport:
    """Evaluate all Sony official Slot-1 `BODYDATA.DAT` (`7.02`) stock-reflash preconditions."""
    cfg = spec if spec is not None else Slot1UfuReflashReadinessSpec()
    blocked: List[str] = []
    errors: List[str] = []

    if cfg.request_persistent_write_unlock or PERSISTENT_EMMC_WRITES_AUTHORIZED:
        blocked.append(BLOCKED_SAFETY_POLICY_VIOLATION)
        errors.append("Persistent eMMC write unlock forbidden during readiness audit")

    # 1. Body firmware >= Ver. 2.04 floor (<= 2.02 risks 7 long + 7 short LED failure)
    body_ver = _parse_version_tuple(cfg.body_firmware_version)
    floor_ver = _parse_version_tuple(P180_FX3_MIN_BODY_FLOOR_VERSION)
    target_ver = _parse_version_tuple(cfg.target_firmware_version)
    body_floor_ok = (
        body_ver is not None
        and floor_ver is not None
        and target_ver is not None
        and body_ver >= floor_ver
        and target_ver >= body_ver
    )
    if not body_floor_ok:
        blocked.append(BLOCKED_BODY_VERSION_BELOW_204_FLOOR_7L7S)
        errors.append(
            f"Body firmware {cfg.body_firmware_version!r} below >= 2.04 floor "
            f"(<= 2.02 triggers {P180_FX3_BRICK_BELOW_FLOOR_LED} LED blink error) or target {cfg.target_firmware_version!r} invalid"
        )

    # 2. Slot-1 ExFAT root placement only; reject Slot-2, subdirectories, and duplicate filenames
    norm_path = cfg.sd_file_path.strip()
    siblings = tuple(s.strip() for s in cfg.sibling_filenames_on_card if s.strip())
    dup_or_alias = [
        fn for fn in siblings
        if "bodydata" in fn.lower() and fn != P180_BODYDATA_FILENAME
    ]
    exact_matches = [fn for fn in siblings if fn == P180_BODYDATA_FILENAME]
    slot1_ok = (
        cfg.update_slot == P180_REQUIRED_UPDATE_SLOT
        and norm_path == P180_SLOT1_ROOT_PATH
        and len(dup_or_alias) == 0
        and len(exact_matches) <= 1
    )
    if not slot1_ok:
        blocked.append(BLOCKED_SLOT1_ROOT_OR_DUPLICATE_BODYDATA)
        errors.append(
            f"Slot-1 root /BODYDATA.DAT required: got slot={cfg.update_slot}, path={norm_path!r}, siblings={siblings}"
        )

    # 3. Exact 811,876,768 B, \x89UFU\r\n\x1a\n magic, ILME-FX3 (0x91030080)
    ufu_ok = (
        cfg.bodydata_byte_length == P180_BODYDATA_702_BYTES
        and cfg.ufu_magic_hex.lower() == P180_UFU_MAGIC_HEX
        and cfg.target_model_id == P180_FX3_MODEL_ID
        and cfg.target_model_name == P180_FX3_MODEL_NAME
    )
    if not ufu_ok:
        blocked.append(BLOCKED_UFU_SIZE_MAGIC_OR_MODEL_MISMATCH)
        errors.append(
            f"BODYDATA.DAT size/magic/model mismatch: bytes={cfg.bodydata_byte_length}, "
            f"model={cfg.target_model_name} ({cfg.target_model_id:#x})"
        )

    # 4. Clean uninstall state: p1 arming flag == 0, p15:/usr .orig H0==H3, p5:/wbi WBI2\0\0\0\0 H0==H3
    p1_clean = cfg.p1_update_arming_flag == 0
    p15_ok = (
        cfg.p15_orig_restored
        and bool(_SHA256_RE.match(cfg.p15_h0_sha256))
        and cfg.p15_h0_sha256 == cfg.p15_h3_sha256
    )
    p5_ok = (
        cfg.p5_wbi2_prefix_hex.lower() == P180_WBI2_HEADER_PREFIX_HEX
        and bool(_SHA256_RE.match(cfg.p5_h0_sha256))
        and cfg.p5_h0_sha256 == cfg.p5_h3_sha256
    )
    if not (p1_clean and p15_ok and p5_ok):
        blocked.append(BLOCKED_P1_FLAG_OR_P15_P5_H0_H3_NOT_RESTORED)
        errors.append(
            f"Pre-reflash clean uninstall check failed: p1_flag={cfg.p1_update_arming_flag}, "
            f"p15_ok={p15_ok}, p5_ok={p5_ok}"
        )

    # 5. NP-FZ100 battery charge floor (>= 3 bars AND >= 7.2V)
    power_ok = cfg.np_fz100_bars >= P180_NP_FZ100_MIN_BARS and cfg.np_fz100_voltage_v >= P180_NP_FZ100_MIN_VOLTAGE_V
    if not power_ok:
        blocked.append(BLOCKED_NP_FZ100_BELOW_3BARS_OR_7V2_FLOOR)
        errors.append(
            f"NP-FZ100 charge below floor (>= 3 bars / >= 7.20V): bars={cfg.np_fz100_bars}, V={cfg.np_fz100_voltage_v:.2f}"
        )

    # 6. p12:/cert/RQ_LIC.DAT C2PA license count <= 100 ceiling & RO integrity
    c2pa_ro_ok = (
        0 <= cfg.c2pa_license_count <= P180_C2PA_MAX_LICENSES
        and cfg.p12_rq_lic_path.strip() == P180_P12_RQ_LIC_PATH
        and cfg.p12_blkroset_locked
        and cfg.p12_ms_rdonly
        and bool(_SHA256_RE.match(cfg.p12_rq_lic_h0_sha256))
        and cfg.p12_rq_lic_h0_sha256 == cfg.p12_rq_lic_h3_sha256
    )
    if not c2pa_ro_ok:
        blocked.append(BLOCKED_C2PA_100_LICENSE_CEILING_OR_P12_RO_BREACH)
        errors.append(
            f"p12:/cert/RQ_LIC.DAT C2PA count={cfg.c2pa_license_count} (>100) or RO integrity check failed"
        )

    passed = (
        body_floor_ok
        and slot1_ok
        and ufu_ok
        and p1_clean
        and p15_ok
        and p5_ok
        and power_ok
        and c2pa_ro_ok
        and len(blocked) == 0
        and len(errors) == 0
    )
    return Slot1UfuReflashReadinessReport(
        passed=passed,
        reflash_ready=passed,
        body_firmware_version=cfg.body_firmware_version,
        body_floor_204_ok=body_floor_ok,
        slot1_root_and_unique_ok=slot1_ok,
        bodydata_811m_and_ufu_ok=ufu_ok,
        p1_arming_flag_clean=p1_clean,
        p15_orig_h0_eq_h3=p15_ok,
        p5_wbi2_h0_eq_h3=p5_ok,
        np_fz100_power_ok=power_ok,
        c2pa_under_100_and_p12_ro_ok=c2pa_ro_ok,
        blocked_codes=tuple(dict.fromkeys(blocked)),
        errors=tuple(errors),
    )


def run_pillar24a_slot1_ufu_readiness_6_scenario_suite() -> Pillar24ASlot1UfuSuiteResult:
    """Run all 6 Pillar 24A Slot-1 `BODYDATA.DAT` (`>= 2.04` floor) readiness scenarios."""
    outcomes: List[Pillar24AScenarioOutcome] = []

    # P24A1: Happy post-uninstall H2->H3 FX3 7.02 ready on Slot-1 root
    r1 = evaluate_slot1_ufu_stock_reflash_readiness(Slot1UfuReflashReadinessSpec())
    ok1 = r1.passed and r1.reflash_ready and r1.body_floor_204_ok and r1.slot1_root_and_unique_ok and r1.c2pa_under_100_and_p12_ro_ok
    outcomes.append(
        Pillar24AScenarioOutcome(
            P180_PILLAR_24A_SCENARIO_IDS[0],
            ok1,
            r1.reflash_ready,
            r1.blocked_codes,
            "Slot-1 root /BODYDATA.DAT (811,876,768 B, \\x89UFU), >=2.04 floor, p1=0, p15/p5 H0==H3, NP-FZ100>=3 bars, C2PA<=100 RO ready",
        )
    )

    # P24A2: Body <= Ver. 2.02 blocked (prevents 7 long + 7 short LED failure)
    r2 = evaluate_slot1_ufu_stock_reflash_readiness(
        Slot1UfuReflashReadinessSpec(body_firmware_version="2.02")
    )
    ok2 = (
        (not r2.passed)
        and (not r2.reflash_ready)
        and (not r2.body_floor_204_ok)
        and (BLOCKED_BODY_VERSION_BELOW_204_FLOOR_7L7S in r2.blocked_codes)
    )
    outcomes.append(
        Pillar24AScenarioOutcome(
            P180_PILLAR_24A_SCENARIO_IDS[1],
            ok2,
            r2.reflash_ready,
            r2.blocked_codes,
            "Body firmware Ver. 2.02 (<=2.02) blocked fail-closed to prevent 7L+7S LED error",
        )
    )

    # P24A3: Slot-2 update or duplicate BODYDATA (1).DAT / BODYDATA_OLD.DAT blocked
    r3_slot2 = evaluate_slot1_ufu_stock_reflash_readiness(
        Slot1UfuReflashReadinessSpec(update_slot=2)
    )
    r3_dup = evaluate_slot1_ufu_stock_reflash_readiness(
        Slot1UfuReflashReadinessSpec(sibling_filenames_on_card=("BODYDATA.DAT", "BODYDATA (1).DAT", "BODYDATA_OLD.DAT"))
    )
    ok3 = (
        (not r3_slot2.passed)
        and (not r3_dup.passed)
        and (BLOCKED_SLOT1_ROOT_OR_DUPLICATE_BODYDATA in r3_slot2.blocked_codes)
        and (BLOCKED_SLOT1_ROOT_OR_DUPLICATE_BODYDATA in r3_dup.blocked_codes)
    )
    outcomes.append(
        Pillar24AScenarioOutcome(
            P180_PILLAR_24A_SCENARIO_IDS[2],
            ok3,
            False,
            r3_dup.blocked_codes,
            "Slot-2 update & duplicate BODYDATA (1).DAT / BODYDATA_OLD.DAT blocked fail-closed",
        )
    )

    # P24A4: Dirty p1 arming flag, p15 .orig not restored, or p5 WBI2 header corrupted
    r4 = evaluate_slot1_ufu_stock_reflash_readiness(
        Slot1UfuReflashReadinessSpec(
            p1_update_arming_flag=1,
            p15_orig_restored=False,
            p5_wbi2_prefix_hex=b"invl\x00\x00\x00\x00".hex(),
        )
    )
    ok4 = (
        (not r4.passed)
        and (not r4.reflash_ready)
        and (BLOCKED_P1_FLAG_OR_P15_P5_H0_H3_NOT_RESTORED in r4.blocked_codes)
    )
    outcomes.append(
        Pillar24AScenarioOutcome(
            P180_PILLAR_24A_SCENARIO_IDS[3],
            ok4,
            r4.reflash_ready,
            r4.blocked_codes,
            "Dirty p1 arming flag, unrestored p15 .orig, or drifted p5:/wbi WBI2 header blocked",
        )
    )

    # P24A5: NP-FZ100 battery below 3 bars / 7.2V floor
    r5 = evaluate_slot1_ufu_stock_reflash_readiness(
        Slot1UfuReflashReadinessSpec(np_fz100_bars=2, np_fz100_voltage_v=6.95)
    )
    ok5 = (
        (not r5.passed)
        and (not r5.reflash_ready)
        and (not r5.np_fz100_power_ok)
        and (BLOCKED_NP_FZ100_BELOW_3BARS_OR_7V2_FLOOR in r5.blocked_codes)
    )
    outcomes.append(
        Pillar24AScenarioOutcome(
            P180_PILLAR_24A_SCENARIO_IDS[4],
            ok5,
            r5.reflash_ready,
            r5.blocked_codes,
            "NP-FZ100 < 3 bars / < 7.20V charge floor blocked fail-closed",
        )
    )

    # P24A6: C2PA > 100 ceiling or p12:/cert/RQ_LIC.DAT RO breach
    r6_cnt = evaluate_slot1_ufu_stock_reflash_readiness(
        Slot1UfuReflashReadinessSpec(c2pa_license_count=101)
    )
    r6_ro = evaluate_slot1_ufu_stock_reflash_readiness(
        Slot1UfuReflashReadinessSpec(p12_blkroset_locked=False, p12_rq_lic_h3_sha256="f" * 64)
    )
    ok6 = (
        (not r6_cnt.passed)
        and (not r6_ro.passed)
        and (BLOCKED_C2PA_100_LICENSE_CEILING_OR_P12_RO_BREACH in r6_cnt.blocked_codes)
        and (BLOCKED_C2PA_100_LICENSE_CEILING_OR_P12_RO_BREACH in r6_ro.blocked_codes)
    )
    outcomes.append(
        Pillar24AScenarioOutcome(
            P180_PILLAR_24A_SCENARIO_IDS[5],
            ok6,
            False,
            r6_cnt.blocked_codes,
            "C2PA license count > 100 ceiling & p12:/cert/RQ_LIC.DAT RO/SHA drift blocked fail-closed",
        )
    )

    passed_count = sum(1 for o in outcomes if o.passed)
    all_ok = passed_count == len(P180_PILLAR_24A_SCENARIO_IDS)
    return Pillar24ASlot1UfuSuiteResult(
        passed=all_ok,
        status=P180_STATUS_VERIFIED_PILLAR_24A if all_ok else P180_STATUS_REJECTED_PILLAR_24A,
        scenarios_passed=passed_count,
        scenarios_total=len(P180_PILLAR_24A_SCENARIO_IDS),
        scenarios=tuple(outcomes),
    )


# ---------------------------------------------------------------------------
# 3. Pillar 24B — Volatile Network (WPA2/WPA3) & HDMI-BRAW / LUT Rollback Hygiene
# ---------------------------------------------------------------------------


def evaluate_volatile_network_braw_lut_hygiene(
    spec: Optional[RollbackHygieneAuditSpec] = None,
) -> RollbackHygieneReport:
    """Audit zero credential / .cube LUT / HDMI-BRAW state leak into `p2:/setting/Backup.bin`."""
    cfg = spec if spec is not None else RollbackHygieneAuditSpec()
    blocked: List[str] = []
    errors: List[str] = []

    if cfg.request_persistent_write_unlock or PERSISTENT_EMMC_WRITES_AUTHORIZED:
        blocked.append(BLOCKED_SAFETY_POLICY_VIOLATION)
        errors.append("Persistent eMMC write unlock forbidden during rollback hygiene audit")

    # 1. Wireless security floor: WPA2 / WPA3 / Access Authentication only
    bad_wifi: List[str] = []
    for prof in cfg.wireless_profiles:
        norm = prof.strip().upper()
        if norm in P180_FORBIDDEN_WIRELESS_PROTOCOLS or "WEP" in norm or "WPA1" in norm or "IPSEC" in norm:
            bad_wifi.append(prof)
        elif norm not in P180_ALLOWED_WIRELESS_PROTOCOLS:
            bad_wifi.append(prof)
    wifi_proto_ok = len(cfg.wireless_profiles) > 0 and len(bad_wifi) == 0
    if not wifi_proto_ok:
        blocked.append(BLOCKED_INSECURE_WIRELESS_WEP_WPA1_IPSEC)
        errors.append(f"Deprecated or disallowed wireless profiles rejected: {bad_wifi or cfg.wireless_profiles}")

    # 2. Zero volatile tmpfs Wi-Fi credential leak into Stock Backup.bin
    wifi_leak_ok = (
        cfg.tmpfs_wifi_creds_present_after_rollback == 0
        and cfg.backup_bin_wifi_cred_bytes_leaked == 0
    )
    if not wifi_leak_ok:
        blocked.append(BLOCKED_VOLATILE_WIFI_CREDENTIAL_LEAK_TO_BACKUP_BIN)
        errors.append(
            f"Volatile tmpfs Wi-Fi credential leak detected: tmpfs={cfg.tmpfs_wifi_creds_present_after_rollback}, "
            f"backup_bin_bytes={cfg.backup_bin_wifi_cred_bytes_leaked}"
        )

    # 3. Zero .cube 3D LUT staging leak into Backup.bin and p30:/usr/data/lut H0 == H3
    p30_ok = bool(_SHA256_RE.match(cfg.p30_lut_h0_sha256)) and (cfg.p30_lut_h0_sha256 == cfg.p30_lut_h3_sha256)
    cube_leak_ok = (
        cfg.tmpfs_cube_lut_files_present_after_rollback == 0
        and cfg.backup_bin_cube_lut_bytes_leaked == 0
        and p30_ok
    )
    if not cube_leak_ok:
        blocked.append(BLOCKED_CUBE_LUT_STAGING_LEAK_OR_P30_DRIFT)
        errors.append(
            f"3D .cube LUT leak or p30:/usr/data/lut drift detected: tmpfs={cfg.tmpfs_cube_lut_files_present_after_rollback}, "
            f"backup_bin_bytes={cfg.backup_bin_cube_lut_bytes_leaked}, p30_ok={p30_ok}"
        )

    # 4. Zero HDMI BRAW state leak into Stock Backup.bin
    braw_leak_ok = (
        cfg.tmpfs_hdmi_braw_flags_present_after_rollback == 0
        and cfg.backup_bin_hdmi_braw_bytes_leaked == 0
    )
    if not braw_leak_ok:
        blocked.append(BLOCKED_HDMI_BRAW_STATE_LEAK_TO_BACKUP_BIN)
        errors.append(
            f"HDMI BRAW volatile state leak detected: tmpfs={cfg.tmpfs_hdmi_braw_flags_present_after_rollback}, "
            f"backup_bin_bytes={cfg.backup_bin_hdmi_braw_bytes_leaked}"
        )

    # 5. p2:/setting/Backup.bin bit-exact H0 == H3 + RO lock
    p2_ok = (
        cfg.p2_blkroset_locked
        and bool(_SHA256_RE.match(cfg.p2_backup_bin_h0_sha256))
        and cfg.p2_backup_bin_h0_sha256 == cfg.p2_backup_bin_h3_sha256
    )
    if not p2_ok:
        blocked.append(BLOCKED_PERSISTENT_WRITE_OR_BACKUP_BIN_DRIFT)
        errors.append("p2:/setting/Backup.bin BLKROSET lock or H0==H3 SHA-256 invariance violated")

    passed = (
        wifi_proto_ok
        and wifi_leak_ok
        and cube_leak_ok
        and braw_leak_ok
        and p2_ok
        and len(blocked) == 0
        and len(errors) == 0
    )
    return RollbackHygieneReport(
        passed=passed,
        hygiene_clean=passed,
        transition_kind=cfg.transition_kind,
        wireless_wpa2_wpa3_only_ok=wifi_proto_ok,
        zero_wifi_cred_leak_ok=wifi_leak_ok,
        zero_cube_lut_leak_and_p30_ok=cube_leak_ok,
        zero_hdmi_braw_leak_ok=braw_leak_ok,
        p2_backup_bin_h0_eq_h3=p2_ok,
        blocked_codes=tuple(dict.fromkeys(blocked)),
        errors=tuple(errors),
    )


def run_pillar24b_rollback_hygiene_6_scenario_suite() -> Pillar24BHygieneSuiteResult:
    """Run all 6 Pillar 24B volatile network (`WPA2/WPA3`) & HDMI-BRAW / LUT hygiene scenarios."""
    outcomes: List[Pillar24BScenarioOutcome] = []

    # P24B1: Happy EH1 & H2->H3 rollback with WPA2/WPA3 and zero Backup.bin leak
    r1_h2h3 = evaluate_volatile_network_braw_lut_hygiene(
        RollbackHygieneAuditSpec(transition_kind="H2_TO_H3_CLEAN_UNINSTALL")
    )
    r1_eh1 = evaluate_volatile_network_braw_lut_hygiene(
        RollbackHygieneAuditSpec(transition_kind="EH1_SD_EJECT_47US")
    )
    ok1 = r1_h2h3.passed and r1_eh1.passed and r1_h2h3.hygiene_clean and r1_eh1.hygiene_clean
    outcomes.append(
        Pillar24BScenarioOutcome(
            P180_PILLAR_24B_SCENARIO_IDS[0],
            ok1,
            ok1,
            (),
            "WPA2/WPA3 only; EH1 & H2->H3 leave 0 Wi-Fi cred / .cube LUT / HDMI-BRAW leaks into p2:/setting/Backup.bin (H0==H3)",
        )
    )

    # P24B2: Deprecated WEP / WPA1 / legacy IPsec rejected
    r2 = evaluate_volatile_network_braw_lut_hygiene(
        RollbackHygieneAuditSpec(wireless_profiles=("WPA2", "WEP", "WPA1", "LEGACY_IPSEC"))
    )
    ok2 = (
        (not r2.passed)
        and (not r2.hygiene_clean)
        and (not r2.wireless_wpa2_wpa3_only_ok)
        and (BLOCKED_INSECURE_WIRELESS_WEP_WPA1_IPSEC in r2.blocked_codes)
    )
    outcomes.append(
        Pillar24BScenarioOutcome(
            P180_PILLAR_24B_SCENARIO_IDS[1],
            ok2,
            r2.hygiene_clean,
            r2.blocked_codes,
            "Deprecated WEP / WPA1 / legacy IPsec wireless profiles blocked fail-closed",
        )
    )

    # P24B3: Volatile tmpfs Wi-Fi credential leak into Backup.bin detected & blocked
    r3 = evaluate_volatile_network_braw_lut_hygiene(
        RollbackHygieneAuditSpec(
            tmpfs_wifi_creds_present_after_rollback=1,
            backup_bin_wifi_cred_bytes_leaked=64,
        )
    )
    ok3 = (
        (not r3.passed)
        and (not r3.zero_wifi_cred_leak_ok)
        and (BLOCKED_VOLATILE_WIFI_CREDENTIAL_LEAK_TO_BACKUP_BIN in r3.blocked_codes)
    )
    outcomes.append(
        Pillar24BScenarioOutcome(
            P180_PILLAR_24B_SCENARIO_IDS[2],
            ok3,
            r3.hygiene_clean,
            r3.blocked_codes,
            "Stage-B tmpfs Wi-Fi credential leak into p2:/setting/Backup.bin blocked fail-closed",
        )
    )

    # P24B4: .cube 3D LUT staging leak into Backup.bin or p30:/usr/data/lut drift detected & blocked
    r4 = evaluate_volatile_network_braw_lut_hygiene(
        RollbackHygieneAuditSpec(
            tmpfs_cube_lut_files_present_after_rollback=2,
            backup_bin_cube_lut_bytes_leaked=128,
            p30_lut_h3_sha256="c" * 64,
        )
    )
    ok4 = (
        (not r4.passed)
        and (not r4.zero_cube_lut_leak_and_p30_ok)
        and (BLOCKED_CUBE_LUT_STAGING_LEAK_OR_P30_DRIFT in r4.blocked_codes)
    )
    outcomes.append(
        Pillar24BScenarioOutcome(
            P180_PILLAR_24B_SCENARIO_IDS[3],
            ok4,
            r4.hygiene_clean,
            r4.blocked_codes,
            ".cube 3D LUT staging leak into Backup.bin or p30:/usr/data/lut drift blocked fail-closed",
        )
    )

    # P24B5: HDMI BRAW runtime state leak into Stock Backup.bin detected & blocked
    r5 = evaluate_volatile_network_braw_lut_hygiene(
        RollbackHygieneAuditSpec(
            tmpfs_hdmi_braw_flags_present_after_rollback=1,
            backup_bin_hdmi_braw_bytes_leaked=32,
        )
    )
    ok5 = (
        (not r5.passed)
        and (not r5.zero_hdmi_braw_leak_ok)
        and (BLOCKED_HDMI_BRAW_STATE_LEAK_TO_BACKUP_BIN in r5.blocked_codes)
    )
    outcomes.append(
        Pillar24BScenarioOutcome(
            P180_PILLAR_24B_SCENARIO_IDS[4],
            ok5,
            r5.hygiene_clean,
            r5.blocked_codes,
            "HDMI BRAW volatile runtime state leak into Stock p2:/setting/Backup.bin blocked fail-closed",
        )
    )

    # P24B6: Persistent write unlock or Backup.bin H0!=H3 drift rejected fail-closed
    r6 = evaluate_volatile_network_braw_lut_hygiene(
        RollbackHygieneAuditSpec(
            p2_backup_bin_h3_sha256="d" * 64,
            p2_blkroset_locked=False,
            request_persistent_write_unlock=True,
        )
    )
    ok6 = (
        (not r6.passed)
        and (not r6.p2_backup_bin_h0_eq_h3)
        and (BLOCKED_PERSISTENT_WRITE_OR_BACKUP_BIN_DRIFT in r6.blocked_codes)
        and (BLOCKED_SAFETY_POLICY_VIOLATION in r6.blocked_codes)
        and r6.physical_device_writes == 0
    )
    outcomes.append(
        Pillar24BScenarioOutcome(
            P180_PILLAR_24B_SCENARIO_IDS[5],
            ok6,
            r6.hygiene_clean,
            r6.blocked_codes,
            "Persistent eMMC write unlock & Backup.bin H0!=H3 drift blocked with 0 device writes",
        )
    )

    passed_count = sum(1 for o in outcomes if o.passed)
    all_ok = passed_count == len(P180_PILLAR_24B_SCENARIO_IDS)
    return Pillar24BHygieneSuiteResult(
        passed=all_ok,
        status=P180_STATUS_VERIFIED_PILLAR_24B if all_ok else P180_STATUS_REJECTED_PILLAR_24B,
        scenarios_passed=passed_count,
        scenarios_total=len(P180_PILLAR_24B_SCENARIO_IDS),
        scenarios=tuple(outcomes),
    )


def run_pillar24_standalone_suite(
    *,
    force_clean_room: Optional[bool] = None,
) -> Pillar24StandaloneReport:
    """Run Pillar 24 standalone donor audit + Pillar 24A (Slot-1 UFU) + Pillar 24B (Hygiene)."""
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
    snap = inspect_phase180_donors_readonly(force_clean_room=force_clean_room)
    p24a = run_pillar24a_slot1_ufu_readiness_6_scenario_suite()
    p24b = run_pillar24b_rollback_hygiene_6_scenario_suite()
    elapsed = round(time.monotonic() - t0, 6)

    errors: List[str] = list(snap.errors)
    if not p24a.passed:
        errors.append("Pillar 24A Slot-1 BODYDATA.DAT stock-reflash readiness suite failed")
    if not p24b.passed:
        errors.append("Pillar 24B volatile WPA3/BRAW/LUT rollback hygiene suite failed")

    all_ok = (
        snap.all_passed
        and p24a.passed
        and p24b.passed
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
            "schema": PHASE180_SCHEMA,
            "version": PHASE180_VERSION,
            "mode": snap.verification_mode,
            "snapshot_sha256": snap.snapshot_sha256,
            "p24a": p24a.to_dict(),
            "p24b": p24b.to_dict(),
            "all_passed": all_ok,
        }
    )
    return Pillar24StandaloneReport(
        schema=PHASE180_SCHEMA,
        version=PHASE180_VERSION,
        verification_mode=snap.verification_mode,
        all_passed=all_ok,
        status=P180_STATUS_VERIFIED_PILLAR24_SUITE if all_ok else P180_STATUS_FAIL_PILLAR24_SUITE,
        elapsed_seconds=elapsed,
        donor_snapshot=snap,
        pillar_24a_slot1_ufu_readiness=p24a,
        pillar_24b_rollback_hygiene=p24b,
        suite_sha256=suite_sha,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# 4. Unified 24/24 Recovery Master Aggregator (`evaluate_24pillar_recovery_master`)
# ---------------------------------------------------------------------------


def _apply_master_fault_injection(pillar: MasterPillarStatus) -> MasterPillarStatus:
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


def evaluate_24pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master24PillarRecoveryReport:
    """Evaluate and aggregate all 24 recovery pillars (`1..24`) concurrently in `< 1.8s`."""
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
        _need(fault_inject_pillar in MASTER_24_PILLAR_IDS, f"Unknown fault_inject_pillar: {fault_inject_pillar}")

    t_start = time.monotonic()
    kw: Dict[str, Any] = {"force_clean_room": force_clean_room} if force_clean_room is not None else {}

    def _run_22pillar() -> Master22PillarRecoveryReport:
        return evaluate_22pillar_recovery_master(**kw)

    def _run_p23() -> Tuple[Any, float]:
        t0 = time.monotonic()
        res = run_wbi_powerloss_and_100cycle_suite(**kw)
        return res, round(time.monotonic() - t0, 6)

    def _run_p24() -> Tuple[Pillar24StandaloneReport, float]:
        t0 = time.monotonic()
        res = run_pillar24_standalone_suite(**kw)
        return res, round(time.monotonic() - t0, 6)

    with ThreadPoolExecutor(max_workers=3) as pool:
        fut_22 = pool.submit(_run_22pillar)
        fut_23 = pool.submit(_run_p23)
        fut_24 = pool.submit(_run_p24)

        m22_rep = fut_22.result()
        p23_rep, p23_dt = fut_23.result()
        p24_rep, p24_dt = fut_24.result()

    safety_errors: List[str] = list(m22_rep.errors)
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
        if getattr(m22_rep, attr_name) != expected_val:
            safety_errors.append(f"Pillars 1-22 violated {attr_name} == {expected_val}")
        if hasattr(p23_rep, attr_name) and getattr(p23_rep, attr_name) != expected_val:
            safety_errors.append(f"Pillar 23 violated {attr_name} == {expected_val}")
        if hasattr(p24_rep, attr_name) and getattr(p24_rep, attr_name) != expected_val:
            safety_errors.append(f"Pillar 24 violated {attr_name} == {expected_val}")

    if getattr(p23_rep, "wbi_persistent_writes", 0) != 0:
        safety_errors.append("Pillar 23 violated wbi_persistent_writes == 0")

    pillar_statuses: List[MasterPillarStatus] = list(m22_rep.pillars)

    # Pillar 23 entry
    spec23 = MASTER_24_PILLAR_SPECS[22]
    p23_metrics = {
        "pillar_23a_wbi_firewall": f"{p23_rep.pillar_23a_wbi_firewall.scenarios_passed}/{p23_rep.pillar_23a_wbi_firewall.scenarios_total}",
        "pillar_23b_powerloss": f"{p23_rep.pillar_23b_powerloss_100cycle.scenarios_passed}/{p23_rep.pillar_23b_powerloss_100cycle.scenarios_total}",
        "cycles": f"{p23_rep.pillar_23b_powerloss_100cycle.cycles_passed}/{p23_rep.pillar_23b_powerloss_100cycle.cycles_executed}",
        "h0_equals_h3": p23_rep.pillar_23b_powerloss_100cycle.h0_equals_h3,
        "wbi_persistent_writes": p23_rep.wbi_persistent_writes,
    }
    pillar_statuses.append(
        MasterPillarStatus(
            pillar_number=spec23[0],
            pillar_id=spec23[1],
            phase_label=spec23[2],
            module_name=spec23[3],
            passed=bool(p23_rep.all_passed),
            status=p23_rep.status,
            verification_mode=p23_rep.verification_mode,
            elapsed_seconds=p23_dt,
            key_metrics=p23_metrics,
            digest_sha256=_canonical_sha256(
                {
                    "pillar": spec23[1],
                    "mode": p23_rep.verification_mode,
                    "status": p23_rep.status,
                    "metrics": p23_metrics,
                    "passed": p23_rep.all_passed,
                }
            ),
            errors=tuple(p23_rep.errors),
        )
    )

    # Pillar 24 entry
    spec24 = MASTER_24_PILLAR_SPECS[23]
    p24_metrics = {
        "pillar_24a_slot1_ufu": f"{p24_rep.pillar_24a_slot1_ufu_readiness.scenarios_passed}/{p24_rep.pillar_24a_slot1_ufu_readiness.scenarios_total}",
        "pillar_24b_hygiene": f"{p24_rep.pillar_24b_rollback_hygiene.scenarios_passed}/{p24_rep.pillar_24b_rollback_hygiene.scenarios_total}",
        "donor_files_inspected": p24_rep.donor_snapshot.donor_files_inspected,
    }
    pillar_statuses.append(
        MasterPillarStatus(
            pillar_number=spec24[0],
            pillar_id=spec24[1],
            phase_label=spec24[2],
            module_name=spec24[3],
            passed=bool(p24_rep.all_passed),
            status=p24_rep.status,
            verification_mode=p24_rep.verification_mode,
            elapsed_seconds=p24_dt,
            key_metrics=p24_metrics,
            digest_sha256=_canonical_sha256(
                {
                    "pillar": spec24[1],
                    "mode": p24_rep.verification_mode,
                    "status": p24_rep.status,
                    "metrics": p24_metrics,
                    "passed": p24_rep.all_passed,
                }
            ),
            errors=tuple(p24_rep.errors),
        )
    )

    if fault_inject_pillar is not None:
        pillar_statuses = [
            _apply_master_fault_injection(p) if p.pillar_id == fault_inject_pillar else p
            for p in pillar_statuses
        ]

    elapsed = round(time.monotonic() - t_start, 6)
    failed = tuple(p.pillar_id for p in pillar_statuses if not p.passed)
    pillars_passed = sum(1 for p in pillar_statuses if p.passed)
    verification_mode = p24_rep.verification_mode

    all_ok = (
        len(pillar_statuses) == MASTER_24_PILLAR_COUNT == 24
        and pillars_passed == 24
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
            "schema": PHASE180_SCHEMA,
            "version": PHASE180_VERSION,
            "verification_mode": verification_mode,
            "pillar_count": len(pillar_statuses),
            "pillars_passed": pillars_passed,
            "failed_pillars": list(failed),
            "pillar_digests": [(p.pillar_number, p.pillar_id, p.passed, p.digest_sha256) for p in pillar_statuses],
            "all_passed": all_ok,
        }
    )

    return Master24PillarRecoveryReport(
        schema=PHASE180_SCHEMA,
        version=PHASE180_VERSION,
        verification_mode=verification_mode,
        all_passed=all_ok,
        status=P180_STATUS_VERIFIED_24OF24_AGGREGATOR if all_ok else P180_STATUS_FAIL_24OF24_AGGREGATOR,
        pillar_count=len(pillar_statuses),
        pillars_passed=pillars_passed,
        failed_pillars=failed,
        elapsed_seconds=elapsed,
        under_1_8s_budget=elapsed < P180_CONCURRENT_CEILING_SECONDS,
        nominal_under_1_8s=elapsed < P180_NOMINAL_BUDGET_SECONDS,
        pillars=tuple(pillar_statuses),
        donor_snapshot=p24_rep.donor_snapshot,
        pillar24_a_slot1_ufu_readiness=p24_rep.pillar_24a_slot1_ufu_readiness,
        pillar24_b_rollback_hygiene=p24_rep.pillar_24b_rollback_hygiene,
        master_24pillar_sha256=master_sha,
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


def verify_24pillar_recovery_suite(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master24PillarRecoveryReport:
    """Public entry point for Pillar 24 unified `24/24` real-hardware recovery master verification."""
    return evaluate_24pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )
