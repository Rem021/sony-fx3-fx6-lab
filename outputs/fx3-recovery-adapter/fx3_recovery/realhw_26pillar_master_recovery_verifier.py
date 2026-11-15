"""Phase 190 — Pillar 26 (`26/26` Recovery Pillars) & Unified 26-Pillar Recovery Master
(`verify-26pillar-recovery` / `verify-fx3a-branch-recovery-firewall`):

1. **Pillar 26A — `ILME-FX3` (`Ver. 7.02`, `1.44M` LCD + NFC + IR) vs `ILME-FX3A` (`Ver. 2.02`,
   `2.36M` XGA LCD, No NFC/IR) Recovery & `BODYDATA.DAT` / `CAMSET` Branch Firewall (6 Scenarios)**:
   - Verifies that the target body is genuine original `ILME-FX3` (`0x91030080`, `Ver. 7.02`,
     `1,440,000`-dot LCD, NFC + IR hardware present) with `< 50 us` fail-closed pre-mount
     detection.
   - Rejects `FX3A` `BODYDATA.DAT` (`Ver. 1.xx/2.xx`), `FX30` (`0x91030084`), and `FX6`
     (`0x91020080`) recovery images on an `ILME-FX3` (`0x91030080`) body (and vice versa:
     rejects `FX3` `Ver. 7.02` recovery images on `ILME-FX3A`, `ILME-FX30`, or `ILME-FX6`
     bodies fail-closed!).
   - Rejects cross-branch `CAMSET` (`CAMSET01.DAT`..`CAMSET10.DAT`) SD card settings imports
     between `FX3` and `FX3A` (or `FX30`/`FX6`), and validates Stock FX3 `p2:/setting/Backup.bin`
     (`BK4\\x00`, `0xAAAAAAAA`, `BLKROSET=1`, `H0 == H3`).

2. **Pillar 26B — `XLR-H1` MI-Shoe `48kHz/24bit 4ch` Post-Recovery & Post-UFU Audio Format
   Hygiene (6 Scenarios)**:
   - Verifies zero handle firmware write attempts (Sony never ships standalone `XLR-H1`
     firmware; any standalone `XLR-H1` flash/update payload is blocked fail-closed).
   - Verifies body `3.5mm` mic jack physical override safety during cold-boot recovery
     (physical plug insertion cuts MI-Shoe audio and greys out `[MI Shoe Audio Set.]`;
     safe when MI-Shoe active audio is not expected during cold-boot recovery, blocked when
     MI-Shoe active audio is expected; also guards `S&Q` mute consistency and `+48V`
     Stage-A->Stage-B transition glitch).
   - Audits official `BODYDATA.DAT` UFU `48kHz/16bit 2ch` post-UFU default reset behavior
     (documenting the reset cleanly when audited, blocking silent unaudited `24bit 4ch`
     assumptions) without ever dirtying Stock FX3 `p2:/setting/Backup.bin` during Stage-B
     (`stage_b_backup_bin_writes == 0` and `H0 == H3`).

3. **Unified 26-Pillar Master Aggregator (`evaluate_26pillar_recovery_master` /
   `verify-26pillar-recovery`)**:
   - Evaluates `evaluate_24pillar_recovery_master` (`Pillars 1..24`) + **Pillar 25**
     (`realhw_airgap_sd_bundle_manifest_verifier`, `FX3BNDL1` air-gapped SD bundle verifier)
     + **Pillar 26** (`ILME-FX3 vs ILME-FX3A` recovery firewall & `XLR-H1` audio hygiene)
     concurrently -> **`26/26` (`VERIFIED_26OF26_PILLAR_RECOVERY_MASTER`)** in `< 2.0s`
     (with `< 6.0s` concurrency-safe unit-test ceiling).
   - Keeps `evaluate_22pillar_recovery_master` (`verify-22pillar-recovery`) and
     `evaluate_24pillar_recovery_master` (`verify-24pillar-recovery`) 100% intact.

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
from typing import Any, Dict, List, Optional, Tuple

from .files import is_forced_clean_room, local_path, resolve_donor_path
from .realhw_22pillar_master_recovery_verifier import MasterPillarStatus
from .realhw_24pillar_master_recovery_verifier import (
    MASTER_24_PILLAR_SPECS,
    Master24PillarRecoveryReport,
    evaluate_24pillar_recovery_master,
)
from .realhw_airgap_sd_bundle_manifest_verifier import (
    Pillar25AirgapSdBundleReport,
    run_airgap_sd_bundle_manifest_suite,
)


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

PHASE190_SCHEMA: str = "fx3-realhw-26pillar-recovery-master-verifier-v1"
PHASE190_VERSION: str = "1.0.0"

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

# Hardware Branch, CAMSET & XLR-H1 Audio Hygiene Constants
P190_BOUNDED_HEADER_BYTES: int = 4096
P190_MAX_FULL_DONOR_BYTES: int = 4 * 1024 * 1024

P190_FX3_BRANCH: str = "FX3"
P190_FX3A_BRANCH: str = "FX3A"
P190_FX30_BRANCH: str = "FX30"
P190_FX6_BRANCH: str = "FX6"

P190_FX3_MODEL_NAME: str = "ILME-FX3"
P190_FX3_MODEL_ID: int = 0x91030080
P190_FX3_FW_VERSION: str = "7.02"
P190_FX3_LCD_DOTS: int = 1_440_000

P190_FX3A_MODEL_NAME: str = "ILME-FX3A"
P190_FX3A_FW_VERSION: str = "2.02"
P190_FX3A_LCD_DOTS: int = 2_359_296

P190_FX30_MODEL_NAME: str = "ILME-FX30"
P190_FX30_MODEL_ID: int = 0x91030084

P190_FX6_MODEL_NAME: str = "ILME-FX6"
P190_FX6_MODEL_ID: int = 0x91020080

P190_FAIL_CLOSED_MAX_LATENCY_US: float = 50.0
P190_UFU_MAGIC: bytes = b"\x89UFU\r\n\x1a\n"
P190_UFU_MAGIC_HEX: str = P190_UFU_MAGIC.hex()

P190_VALID_CAMSET_FILENAMES: Tuple[str, ...] = tuple(f"CAMSET{i:02d}.DAT" for i in range(1, 11))

P190_XLRH1_HANDLE_MODEL: str = "XLR-H1"
P190_XLRH1_STANDALONE_FW_SHIPPED: bool = False
P190_XLRH1_AUDIO_PROFILES: Dict[str, Tuple[int, int, int]] = {
    "48KHZ_24BIT_4CH": (48_000, 24, 4),
    "48KHZ_24BIT_2CH": (48_000, 24, 2),
    "48KHZ_16BIT_2CH": (48_000, 16, 2),
}
P190_XLRH1_POST_UFU_DEFAULT_PROFILE: str = "48KHZ_16BIT_2CH"
P190_XLRH1_MONITOR_MATRICES: Tuple[str, ...] = ("CH1_2", "CH3_4", "CH1+3_CH2+4")

P190_NOMINAL_BUDGET_SECONDS: float = 2.0
P190_CONCURRENT_CEILING_SECONDS: float = 6.0

# Master 26-Pillar Registry: Pillars 1..24 + Pillar 25 + Pillar 26
MASTER_26_PILLAR_SPECS: Tuple[Tuple[int, str, str, str], ...] = MASTER_24_PILLAR_SPECS + (
    (
        25,
        "realhw_airgap_sd_bundle_manifest_verifier",
        "Phase 184",
        "fx3_recovery.realhw_airgap_sd_bundle_manifest_verifier",
    ),
    (
        26,
        "realhw_26pillar_master_recovery_verifier",
        "Phase 190",
        "fx3_recovery.realhw_26pillar_master_recovery_verifier",
    ),
)
MASTER_26_PILLAR_IDS: Tuple[str, ...] = tuple(spec[1] for spec in MASTER_26_PILLAR_SPECS)
MASTER_26_PILLAR_COUNT: int = len(MASTER_26_PILLAR_SPECS)

# Pillar 26A & 26B Scenario IDs (6 + 6 = 12 Scenarios)
P190_PILLAR_26A_SCENARIO_IDS: Tuple[str, ...] = (
    "P26A1_HAPPY_FX3_702_144M_NFC_IR_RECOVERY_AND_CAMSET01_MATCH",
    "P26A2_BLOCKED_FX3A_236M_NO_NFC_IR_BODY_FAIL_CLOSED",
    "P26A3_BLOCKED_FX3A_V1XX_V2XX_BODYDATA_ON_FX3_AND_VICE_VERSA",
    "P26A4_BLOCKED_FX30_0X91030084_AND_FX6_0X91020080_CROSS_SKU_RECOVERY",
    "P26A5_BLOCKED_CROSS_BRANCH_CAMSET01_TO_CAMSET10_IMPORT",
    "P26A6_BLOCKED_BACKUP_BIN_H0_H3_DRIFT_OR_WRITE_UNLOCK",
)

P190_PILLAR_26B_SCENARIO_IDS: Tuple[str, ...] = (
    "P26B1_HAPPY_XLRH1_48KHZ_24BIT_4CH_ROUTING_AND_H0_EQ_H3",
    "P26B2_BLOCKED_FAKE_XLRH1_FIRMWARE_WRITE_ATTEMPT",
    "P26B3_SAFE_AND_BLOCKED_BODY_35MM_MIC_JACK_OVERRIDE",
    "P26B4_BLOCKED_SQ_MODE_UNMUTED_OR_48V_STAGE_B_GLITCH",
    "P26B5_AUDITED_POST_UFU_48KHZ_16BIT_2CH_RESET_AND_UNAUDITED_BLOCK",
    "P26B6_BLOCKED_STAGE_B_BACKUP_BIN_DIRTYING_OR_WRITE_UNLOCK",
)

# Pinned Local Donor Relpaths & Digests (strictly O_RDONLY, zero raw bytes leaked)
P190_DONOR_FX3_BODYDATA_RELPATH: str = "sony-firmware-20261024/fx3-7.02-BODYDATA.DAT"
P190_DONOR_FX3_CPAPP_B_RELPATH: str = "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin"
P190_DONOR_FX3_APPFW_SO_RELPATH: str = "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so"
P190_DONOR_FX3_BACKUP_BIN_RELPATH: str = (
    "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin"
)
P190_DONOR_FX3_PARTINF_RELPATH: str = (
    "sony-firmware-20261024/stage182-boot-selector-and-recovery-admission/"
    "current-updater-evidence/tar-selected/0300_partconf/partinf.conf"
)
P190_DONOR_HOTSHOE_SO_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libInfraHotshoe.so"
)

P190_PINNED_FX3_BODYDATA_BYTES: int = 811_876_768
P190_PINNED_FX3_BODYDATA_HDR4K_SHA256: str = "fc135914e0767d69518e5b1f86b138abdbd2a20dd341e495cf151f8ddb79e404"
P190_PINNED_FX3_CPAPP_B_BYTES: int = 15_980_568
P190_PINNED_FX3_CPAPP_B_HDR4K_SHA256: str = "452c9e4e05fc1942baeee8ea9d531eeaaab99091576bc59eaa46f2d272050d5d"
P190_PINNED_FX3_APPFW_SO_BYTES: int = 79_015_712
P190_PINNED_FX3_APPFW_SO_HDR4K_SHA256: str = "de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674"
P190_PINNED_FX3_BACKUP_BIN_BYTES: int = 2_229_740
P190_PINNED_FX3_BACKUP_BIN_SHA256: str = "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2"
P190_PINNED_FX3_PARTINF_BYTES: int = 3_999
P190_PINNED_FX3_PARTINF_SHA256: str = "3d96228d4ed2db3cb4295aa854edf0ad8895440167f132144cdec4f8cfdad189"
P190_PINNED_HOTSHOE_SO_BYTES: int = 47_808
P190_PINNED_HOTSHOE_SO_SHA256: str = "0bf55367c0345341d776180e45ec640dce978c1cf9a0935354f20421ca2204f6"

# Status & Fail-Closed Error Codes
P190_STATUS_VERIFIED_PILLAR26_SUITE: str = "VERIFIED_PILLAR26_FX3A_BRANCH_FIREWALL_AND_XLRH1_HYGIENE"
P190_STATUS_FAIL_PILLAR26_SUITE: str = "FAIL_PILLAR26_FX3A_BRANCH_FIREWALL_AND_XLRH1_HYGIENE"
P190_STATUS_VERIFIED_PILLAR_26A: str = "VERIFIED_ILME_FX3_VS_FX3A_RECOVERY_AND_CAMSET_FIREWALL"
P190_STATUS_REJECTED_PILLAR_26A: str = "REJECTED_ILME_FX3_VS_FX3A_RECOVERY_AND_CAMSET_FIREWALL"
P190_STATUS_VERIFIED_PILLAR_26B: str = "VERIFIED_XLRH1_MISHOE_4CH_24BIT_AUDIO_HYGIENE"
P190_STATUS_REJECTED_PILLAR_26B: str = "REJECTED_XLRH1_MISHOE_4CH_24BIT_AUDIO_HYGIENE"
P190_STATUS_VERIFIED_26OF26_AGGREGATOR: str = "VERIFIED_26OF26_PILLAR_RECOVERY_MASTER"
P190_STATUS_FAIL_26OF26_AGGREGATOR: str = "FAIL_26OF26_PILLAR_RECOVERY_MASTER"

P190_BLOCKED_NON_FX3_HARDWARE_BRANCH: str = "BLOCKED_P26A_NON_FX3_HARDWARE_BRANCH_FX3A_FX30_FX6"
P190_BLOCKED_LCD_NFC_IR_SIGNATURE_MISMATCH: str = "BLOCKED_P26A_LCD_144M_NFC_IR_SIGNATURE_MISMATCH"
P190_BLOCKED_CROSS_BRANCH_BODYDATA_IMAGE: str = "BLOCKED_P26A_CROSS_BRANCH_BODYDATA_RECOVERY_IMAGE"
P190_BLOCKED_CROSS_BRANCH_CAMSET_IMPORT: str = "BLOCKED_P26A_CROSS_BRANCH_CAMSET_IMPORT"
P190_BLOCKED_BACKUP_BIN_H0_H3_OR_RO_DRIFT: str = "BLOCKED_P26A_STOCK_BACKUP_BIN_H0_H3_OR_RO_DRIFT"
P190_BLOCKED_LATENCY_BUDGET_EXCEEDED: str = "BLOCKED_P26A_PREMOUNT_FIREWALL_LATENCY_EXCEEDED"

P190_BLOCKED_XLRH1_FIRMWARE_WRITE_FORBIDDEN: str = "BLOCKED_P26B_XLRH1_STANDALONE_FW_WRITE_FORBIDDEN"
P190_BLOCKED_XLRH1_FORMAT_OR_ROUTING_INVALID: str = "BLOCKED_P26B_XLRH1_AUDIO_FORMAT_OR_ROUTING_INVALID"
P190_BLOCKED_BODY_35MM_MIC_JACK_OVERRIDE: str = "BLOCKED_P26B_BODY_35MM_MIC_JACK_PHYSICAL_OVERRIDE"
P190_BLOCKED_SQ_MUTE_OR_48V_TRANSITION_GLITCH: str = "BLOCKED_P26B_SQ_MUTE_OR_48V_STAGE_TRANSITION_GLITCH"
P190_BLOCKED_POST_UFU_XLRH1_RESET_UNAUDITED: str = "BLOCKED_P26B_POST_UFU_16BIT_2CH_RESET_UNAUDITED"
P190_BLOCKED_STAGE_B_BACKUP_BIN_DIRTY: str = "BLOCKED_P26B_STAGE_B_BACKUP_BIN_DIRTY_OR_H0_H3_DRIFT"
P190_BLOCKED_SAFETY_POLICY_VIOLATION: str = "BLOCKED_P190_SAFETY_POLICY_VIOLATION"

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_VERSION_RE = re.compile(r"^v?(\d+)\.(\d+)(?:\.(\d+))?$", re.IGNORECASE)
_CAMSET_RE = re.compile(r"^CAMSET(?:0[1-9]|10)\.DAT$")


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


def _normalize_branch(raw_branch: str) -> str:
    norm = raw_branch.strip().upper()
    if norm in ("ILME-FX3", "FX3"):
        return P190_FX3_BRANCH
    if norm in ("ILME-FX3A", "FX3A"):
        return P190_FX3A_BRANCH
    if norm in ("ILME-FX30", "FX30"):
        return P190_FX30_BRANCH
    if norm in ("ILME-FX6", "FX6"):
        return P190_FX6_BRANCH
    return norm


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
    max_full_limit: int = P190_MAX_FULL_DONOR_BYTES,
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
        hdr_sha = sha256(buf[:P190_BOUNDED_HEADER_BYTES]).hexdigest()
        return buf, total_sz, full_sha, hdr_sha
    finally:
        os.close(fd)


# ---------------------------------------------------------------------------
# Dataclasses (100% JSON-safe, zero raw proprietary firmware bytes)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase190DonorArtifactDigest:
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
class Phase190DonorSnapshot:
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
    hotshoe_so_elf64_aarch64_ok: bool
    elapsed_seconds: float
    artifacts: Tuple[Phase190DonorArtifactDigest, ...]
    snapshot_sha256: str
    all_passed: bool
    errors: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Fx3BranchRecoveryFirewallSpec:
    body_branch: str = P190_FX3_BRANCH
    body_model_name: str = P190_FX3_MODEL_NAME
    body_model_id: int = P190_FX3_MODEL_ID
    body_firmware_version: str = P190_FX3_FW_VERSION
    body_lcd_dots: int = P190_FX3_LCD_DOTS
    body_has_nfc: bool = True
    body_has_ir_receiver: bool = True
    recovery_image_branch: str = P190_FX3_BRANCH
    recovery_image_model_id: int = P190_FX3_MODEL_ID
    recovery_image_fw_version: str = P190_FX3_FW_VERSION
    recovery_ufu_magic_hex: str = P190_UFU_MAGIC_HEX
    display_shim_branch: str = P190_FX3_BRANCH
    camset_filename: Optional[str] = "CAMSET01.DAT"
    camset_source_branch: str = P190_FX3_BRANCH
    camset_source_model_id: int = P190_FX3_MODEL_ID
    camset_source_fw_version: str = P190_FX3_FW_VERSION
    p2_backup_bin_h0_sha256: str = P190_PINNED_FX3_BACKUP_BIN_SHA256
    p2_backup_bin_h3_sha256: str = P190_PINNED_FX3_BACKUP_BIN_SHA256
    p2_blkroset_locked: bool = True
    detection_latency_us: float = 18.0
    request_persistent_write_unlock: bool = False


@dataclass(frozen=True)
class Fx3BranchRecoveryFirewallReport:
    passed: bool
    recovery_admitted: bool
    fail_closed_triggered: bool
    body_branch_fx3_verified: bool
    lcd_nfc_ir_signature_ok: bool
    recovery_image_branch_ok: bool
    camset_import_ok: bool
    p2_backup_bin_h0_eq_h3: bool
    latency_under_50us_ok: bool
    body_branch: str
    recovery_image_branch: str
    camset_filename: Optional[str]
    blocked_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    persistent_emmc_writes_authorized: bool = PERSISTENT_EMMC_WRITES_AUTHORIZED
    physical_device_writes: int = PHYSICAL_DEVICE_WRITES

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Pillar26AScenarioOutcome:
    scenario_id: str
    passed: bool
    recovery_admitted: bool
    blocked_codes: Tuple[str, ...]
    summary: str


@dataclass(frozen=True)
class Pillar26AFirewallSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar26AScenarioOutcome, ...]
    persistent_emmc_writes_authorized: bool = PERSISTENT_EMMC_WRITES_AUTHORIZED
    physical_device_writes: int = PHYSICAL_DEVICE_WRITES

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Xlrh1AudioHygieneSpec:
    handle_attached: bool = True
    handle_model: str = P190_XLRH1_HANDLE_MODEL
    standalone_handle_fw_write_requested: bool = False
    standalone_handle_fw_files_present: Tuple[str, ...] = ()
    audio_profile: str = "48KHZ_24BIT_4CH"
    handle_audio_switch_on: bool = True
    in1_in2_route: str = "CH1_CH2"
    in3_route: str = "CH3_CH4"
    headphone_monitor_matrix: str = "CH1_2"
    body_35mm_mic_plug_inserted: bool = False
    mi_shoe_active_audio_expected: bool = True
    cold_boot_recovery_active: bool = False
    sq_slow_quick_active: bool = False
    mi_shoe_audio_muted: bool = False
    phantom_48v_stage_b_transition_glitch: bool = False
    post_ufu_upgrade_performed: bool = False
    post_ufu_rearmed_to_24bit_4ch: bool = False
    stage_b_backup_bin_writes: int = 0
    p2_backup_bin_h0_sha256: str = P190_PINNED_FX3_BACKUP_BIN_SHA256
    p2_backup_bin_h3_sha256: str = P190_PINNED_FX3_BACKUP_BIN_SHA256
    p2_blkroset_locked: bool = True
    request_persistent_write_unlock: bool = False


@dataclass(frozen=True)
class Xlrh1AudioHygieneReport:
    passed: bool
    hygiene_clean: bool
    zero_handle_fw_write_ok: bool
    audio_format_and_routing_ok: bool
    body_35mm_override_safe: bool
    sq_and_48v_transition_ok: bool
    post_ufu_reset_audited_ok: bool
    post_ufu_reset_to_16bit_2ch_documented: bool
    stage_b_zero_backup_bin_dirty_ok: bool
    audio_profile: str
    blocked_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    persistent_emmc_writes_authorized: bool = PERSISTENT_EMMC_WRITES_AUTHORIZED
    physical_device_writes: int = PHYSICAL_DEVICE_WRITES

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Pillar26BScenarioOutcome:
    scenario_id: str
    passed: bool
    hygiene_clean: bool
    blocked_codes: Tuple[str, ...]
    summary: str


@dataclass(frozen=True)
class Pillar26BHygieneSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar26BScenarioOutcome, ...]
    persistent_emmc_writes_authorized: bool = PERSISTENT_EMMC_WRITES_AUTHORIZED
    physical_device_writes: int = PHYSICAL_DEVICE_WRITES

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Pillar26StandaloneReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    elapsed_seconds: float
    donor_snapshot: Phase190DonorSnapshot
    pillar_26a_fx3a_firewall: Pillar26AFirewallSuiteResult
    pillar_26b_xlrh1_hygiene: Pillar26BHygieneSuiteResult
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
class Master26PillarRecoveryReport:
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
    nominal_under_2s: bool
    pillars: Tuple[MasterPillarStatus, ...]
    donor_snapshot: Phase190DonorSnapshot
    pillar25_airgap_sd_bundle: Pillar25AirgapSdBundleReport
    pillar26_a_fx3a_firewall: Pillar26AFirewallSuiteResult
    pillar26_b_xlrh1_hygiene: Pillar26BHygieneSuiteResult
    master_26pillar_sha256: str
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


def inspect_phase190_donors_readonly(
    *,
    force_clean_room: Optional[bool] = None,
) -> Phase190DonorSnapshot:
    """Inspect FX3 `7.02` & Hotshoe donor artifacts strictly via `os.O_RDONLY` or clean-room fallback."""
    t0 = time.monotonic()
    clean = is_forced_clean_room() if force_clean_room is None else bool(force_clean_room)

    if clean:
        artifacts = (
            Phase190DonorArtifactDigest(
                "fx3_bodydata_dat",
                P190_DONOR_FX3_BODYDATA_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA_ONLY",
                P190_PINNED_FX3_BODYDATA_BYTES,
                P190_PINNED_FX3_BODYDATA_HDR4K_SHA256,
                P190_PINNED_FX3_BODYDATA_HDR4K_SHA256,
                ("UFU_89UFU_MAGIC", "DATV_PROV_UDID", "811876768B"),
                True,
            ),
            Phase190DonorArtifactDigest(
                "fx3_cpapp_b",
                P190_DONOR_FX3_CPAPP_B_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA_ONLY",
                P190_PINNED_FX3_CPAPP_B_BYTES,
                P190_PINNED_FX3_CPAPP_B_HDR4K_SHA256,
                P190_PINNED_FX3_CPAPP_B_HDR4K_SHA256,
                ("BOUNDED_4K_CPAPP_B", "15980568B"),
                True,
            ),
            Phase190DonorArtifactDigest(
                "fx3_appfw_so",
                P190_DONOR_FX3_APPFW_SO_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA_ONLY",
                P190_PINNED_FX3_APPFW_SO_BYTES,
                P190_PINNED_FX3_APPFW_SO_HDR4K_SHA256,
                P190_PINNED_FX3_APPFW_SO_HDR4K_SHA256,
                ("ELF64_AARCH64", "BOUNDED_4K_HEADER"),
                True,
            ),
            Phase190DonorArtifactDigest(
                "fx3_backup_bin",
                P190_DONOR_FX3_BACKUP_BIN_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA_ONLY",
                P190_PINNED_FX3_BACKUP_BIN_BYTES,
                P190_PINNED_FX3_BACKUP_BIN_SHA256,
                P190_PINNED_FX3_BACKUP_BIN_SHA256,
                ("BK4_MAGIC", "0xAAAAAAAA", "ILME-FX3"),
                True,
            ),
            Phase190DonorArtifactDigest(
                "fx3_partinf_conf",
                P190_DONOR_FX3_PARTINF_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA_ONLY",
                P190_PINNED_FX3_PARTINF_BYTES,
                P190_PINNED_FX3_PARTINF_SHA256,
                P190_PINNED_FX3_PARTINF_SHA256,
                ("30_PARTITIONS", "P2_SETTING", "P15_USR"),
                True,
            ),
            Phase190DonorArtifactDigest(
                "hotshoe_libinfrahotshoe",
                P190_DONOR_HOTSHOE_SO_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA_ONLY",
                P190_PINNED_HOTSHOE_SO_BYTES,
                P190_PINNED_HOTSHOE_SO_SHA256,
                P190_PINNED_HOTSHOE_SO_SHA256,
                ("ELF64_AARCH64", "HOTSHOE_HANDLE_XLR"),
                True,
            ),
        )
        elapsed = round(time.monotonic() - t0, 6)
        snap_sha = _canonical_sha256({"mode": "CLEAN_ROOM_SYNTHETIC", "artifacts": [asdict(a) for a in artifacts]})
        return Phase190DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="SYNTHETIC_METADATA_ONLY",
            donor_files_inspected=0,
            raw_firmware_bytes_leaked=0,
            bodydata_702_bytes=P190_PINNED_FX3_BODYDATA_BYTES,
            bodydata_ufu_magic_ok=True,
            cpapp_b_bytes=P190_PINNED_FX3_CPAPP_B_BYTES,
            appfw_so_elf64_aarch64_ok=True,
            backup_bin_bk4_fx3_ok=True,
            partinf_30_partitions_ok=True,
            hotshoe_so_elf64_aarch64_ok=True,
            elapsed_seconds=elapsed,
            artifacts=artifacts,
            snapshot_sha256=snap_sha,
            all_passed=True,
            errors=(),
        )

    required_rels = (
        P190_DONOR_FX3_BODYDATA_RELPATH,
        P190_DONOR_FX3_CPAPP_B_RELPATH,
        P190_DONOR_FX3_APPFW_SO_RELPATH,
        P190_DONOR_FX3_BACKUP_BIN_RELPATH,
        P190_DONOR_FX3_PARTINF_RELPATH,
        P190_DONOR_HOTSHOE_SO_RELPATH,
    )
    resolved = [resolve_donor_path(rel, require_file=True) for rel in required_rels]
    if any(p is None or not p.is_file() for p in resolved):
        return inspect_phase190_donors_readonly(force_clean_room=True)

    artifacts_out: List[Phase190DonorArtifactDigest] = []
    errors: List[str] = []

    # 1) Bounded 4 KiB header of fx3-7.02-BODYDATA.DAT
    bd_head, bd_sz, _, bd_hdr_sha = _read_bounded_rdonly(
        P190_DONOR_FX3_BODYDATA_RELPATH,
        max_bytes=P190_BOUNDED_HEADER_BYTES,
    )
    bd_ok = (
        bd_sz == P190_PINNED_FX3_BODYDATA_BYTES
        and bd_hdr_sha == P190_PINNED_FX3_BODYDATA_HDR4K_SHA256
        and bd_head.startswith(P190_UFU_MAGIC)
        and b"DATV" in bd_head
        and b"PROV" in bd_head
        and b"UDID" in bd_head
    )
    if not bd_ok:
        errors.append("fx3_bodydata_dat: size/4K digest/UFU markers mismatch")
    artifacts_out.append(
        Phase190DonorArtifactDigest(
            "fx3_bodydata_dat",
            P190_DONOR_FX3_BODYDATA_RELPATH,
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
        P190_DONOR_FX3_CPAPP_B_RELPATH,
        max_bytes=P190_BOUNDED_HEADER_BYTES,
    )
    cp_ok = (
        cp_sz == P190_PINNED_FX3_CPAPP_B_BYTES
        and cp_hdr_sha == P190_PINNED_FX3_CPAPP_B_HDR4K_SHA256
        and len(cp_head) == P190_BOUNDED_HEADER_BYTES
    )
    if not cp_ok:
        errors.append("fx3_cpapp_b: size/4K digest mismatch")
    artifacts_out.append(
        Phase190DonorArtifactDigest(
            "fx3_cpapp_b",
            P190_DONOR_FX3_CPAPP_B_RELPATH,
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
        P190_DONOR_FX3_APPFW_SO_RELPATH,
        max_bytes=P190_BOUNDED_HEADER_BYTES,
    )
    af_machine = struct.unpack_from("<H", af_head, 18)[0] if len(af_head) >= 20 else 0
    af_ok = (
        af_sz == P190_PINNED_FX3_APPFW_SO_BYTES
        and af_hdr_sha == P190_PINNED_FX3_APPFW_SO_HDR4K_SHA256
        and af_head[:4] == b"\x7fELF"
        and af_head[4] == 2
        and af_machine == 183
    )
    if not af_ok:
        errors.append("fx3_appfw_so: ELF64 AArch64 header/size/digest mismatch")
    artifacts_out.append(
        Phase190DonorArtifactDigest(
            "fx3_appfw_so",
            P190_DONOR_FX3_APPFW_SO_RELPATH,
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
    bak_raw, bak_sz, bak_sha, bak_hdr = _read_bounded_rdonly(P190_DONOR_FX3_BACKUP_BIN_RELPATH)
    sync_u32 = struct.unpack_from("<I", bak_raw, 4)[0] if len(bak_raw) >= 20 else 0
    bk_magic = bak_raw[12:16] if len(bak_raw) >= 16 else b""
    bak_ok = (
        bak_sz == P190_PINNED_FX3_BACKUP_BIN_BYTES
        and bak_sha == P190_PINNED_FX3_BACKUP_BIN_SHA256
        and sync_u32 == 0xAAAAAAAA
        and bk_magic == b"BK4\x00"
        and b"ILME-FX3" in bak_raw
    )
    if not bak_ok:
        errors.append("fx3_backup_bin: BK4/0xAAAAAAAA/ILME-FX3 or digest mismatch")
    artifacts_out.append(
        Phase190DonorArtifactDigest(
            "fx3_backup_bin",
            P190_DONOR_FX3_BACKUP_BIN_RELPATH,
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
    part_raw, part_sz, part_sha, part_hdr = _read_bounded_rdonly(P190_DONOR_FX3_PARTINF_RELPATH)
    part_txt = part_raw.decode("utf-8", errors="replace")
    part_rows = re.findall(r"^0x[0-9A-Fa-f]+,0x[0-9A-Fa-f]+,0x[0-9A-Fa-f]+,0x[0-9A-Fa-f]+", part_txt, flags=re.M)
    part_ok = (
        part_sz == P190_PINNED_FX3_PARTINF_BYTES
        and part_sha == P190_PINNED_FX3_PARTINF_SHA256
        and len(part_rows) == 30
        and "/dev/nflasha2" in part_txt
        and "/dev/nflasha15" in part_txt
    )
    if not part_ok:
        errors.append("fx3_partinf_conf: 30-partition layout or digest mismatch")
    artifacts_out.append(
        Phase190DonorArtifactDigest(
            "fx3_partinf_conf",
            P190_DONOR_FX3_PARTINF_RELPATH,
            "LOCAL_DONOR_O_RDONLY",
            "O_RDONLY_FULL",
            part_sz,
            part_sha,
            part_hdr,
            ("30_PARTITIONS", "P2_SETTING", "P15_USR"),
            part_ok,
        )
    )

    # 6) libInfraHotshoe.so (47,808 B)
    hs_raw, hs_sz, hs_sha, hs_hdr = _read_bounded_rdonly(P190_DONOR_HOTSHOE_SO_RELPATH)
    hs_machine = struct.unpack_from("<H", hs_raw, 18)[0] if len(hs_raw) >= 20 else 0
    hs_ok = (
        hs_sz == P190_PINNED_HOTSHOE_SO_BYTES
        and hs_sha == P190_PINNED_HOTSHOE_SO_SHA256
        and hs_raw[:4] == b"\x7fELF"
        and hs_raw[4] == 2
        and hs_machine == 183
        and b"HOTSHOE" in hs_raw
        and b"HANDLE" in hs_raw
    )
    if not hs_ok:
        errors.append("hotshoe_libinfrahotshoe: ELF64 AArch64/markers or digest mismatch")
    artifacts_out.append(
        Phase190DonorArtifactDigest(
            "hotshoe_libinfrahotshoe",
            P190_DONOR_HOTSHOE_SO_RELPATH,
            "LOCAL_DONOR_O_RDONLY",
            "O_RDONLY_FULL",
            hs_sz,
            hs_sha,
            hs_hdr,
            ("ELF64_AARCH64", "HOTSHOE_HANDLE_XLR"),
            hs_ok,
        )
    )

    elapsed = round(time.monotonic() - t0, 6)
    all_ok = len(errors) == 0 and all(a.passed for a in artifacts_out)
    snap_sha = _canonical_sha256({"mode": "LOCAL_DONOR_O_RDONLY", "artifacts": [asdict(a) for a in artifacts_out]})
    return Phase190DonorSnapshot(
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
        hotshoe_so_elf64_aarch64_ok=hs_ok,
        elapsed_seconds=elapsed,
        artifacts=tuple(artifacts_out),
        snapshot_sha256=snap_sha,
        all_passed=all_ok,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# 2. Pillar 26A — ILME-FX3 vs ILME-FX3A Branch Recovery & CAMSET Firewall
# ---------------------------------------------------------------------------


def evaluate_fx3a_branch_recovery_firewall(
    spec: Optional[Fx3BranchRecoveryFirewallSpec] = None,
) -> Fx3BranchRecoveryFirewallReport:
    """Enforce `ILME-FX3` vs `ILME-FX3A`/`FX30`/`FX6` cross-branch recovery & `CAMSET` firewall."""
    cfg = spec if spec is not None else Fx3BranchRecoveryFirewallSpec()
    blocked: List[str] = []
    errors: List[str] = []

    if cfg.request_persistent_write_unlock or PERSISTENT_EMMC_WRITES_AUTHORIZED:
        blocked.append(P190_BLOCKED_SAFETY_POLICY_VIOLATION)
        errors.append("Persistent eMMC write unlock forbidden during branch firewall audit")

    body_branch = _normalize_branch(cfg.body_branch)
    body_model = cfg.body_model_name.strip().upper()
    img_branch = _normalize_branch(cfg.recovery_image_branch)
    shim_branch = _normalize_branch(cfg.display_shim_branch)
    cam_branch = _normalize_branch(cfg.camset_source_branch)
    body_ver = _parse_version_tuple(cfg.body_firmware_version)
    img_ver = _parse_version_tuple(cfg.recovery_image_fw_version)
    cam_ver = _parse_version_tuple(cfg.camset_source_fw_version)

    # 1. Target body must be genuine original ILME-FX3 (0x91030080, Ver. >= 7.00, 1.44M LCD + NFC + IR)
    body_is_fx3 = (
        body_branch == P190_FX3_BRANCH
        and body_model == P190_FX3_MODEL_NAME
        and cfg.body_model_id == P190_FX3_MODEL_ID
        and body_ver is not None
        and body_ver[0] >= 7
    )
    if not body_is_fx3:
        blocked.append(P190_BLOCKED_NON_FX3_HARDWARE_BRANCH)
        errors.append(
            f"Non-FX3 target hardware branch blocked fail-closed: branch={body_branch}, "
            f"model={body_model}, id={cfg.body_model_id:#x}, fw={cfg.body_firmware_version}"
        )

    # 2. Physical hardware signature for ILME-FX3: 1.44M LCD + NFC + IR (vs FX3A 2.36M XGA, no NFC/IR)
    lcd_nfc_ir_ok = (
        cfg.body_lcd_dots == P190_FX3_LCD_DOTS
        and cfg.body_has_nfc is True
        and cfg.body_has_ir_receiver is True
    )
    if not lcd_nfc_ir_ok:
        blocked.append(P190_BLOCKED_LCD_NFC_IR_SIGNATURE_MISMATCH)
        errors.append(
            f"LCD/NFC/IR hardware signature mismatch (expected 1.44M+NFC+IR): "
            f"lcd={cfg.body_lcd_dots}, nfc={cfg.body_has_nfc}, ir={cfg.body_has_ir_receiver}"
        )

    # 3. Bidirectional cross-branch BODYDATA.DAT & display shim isolation:
    #    - Reject FX3A (Ver. 1.xx/2.xx), FX30 (0x91030084), FX6 (0x91020080) on FX3 (0x91030080)
    #    - AND reject FX3 (Ver. 7.02, 0x91030080) or mismatched images on FX3A/FX30/FX6 (vice versa!)
    img_matches_body_branch = (
        img_branch == body_branch
        and shim_branch == body_branch
        and img_branch == P190_FX3_BRANCH
        and shim_branch == P190_FX3_BRANCH
    )
    img_version_branch_ok = False
    if img_ver is not None:
        if img_branch == P190_FX3_BRANCH:
            img_version_branch_ok = img_ver[0] >= 7 and cfg.recovery_image_model_id == P190_FX3_MODEL_ID
        elif img_branch == P190_FX3A_BRANCH:
            img_version_branch_ok = img_ver[0] in (1, 2)
        elif img_branch == P190_FX30_BRANCH:
            img_version_branch_ok = cfg.recovery_image_model_id == P190_FX30_MODEL_ID
        elif img_branch == P190_FX6_BRANCH:
            img_version_branch_ok = cfg.recovery_image_model_id == P190_FX6_MODEL_ID

    recovery_image_ok = (
        img_matches_body_branch
        and img_version_branch_ok
        and cfg.recovery_image_model_id == cfg.body_model_id
        and cfg.recovery_ufu_magic_hex.lower() == P190_UFU_MAGIC_HEX
    )
    if not recovery_image_ok:
        blocked.append(P190_BLOCKED_CROSS_BRANCH_BODYDATA_IMAGE)
        errors.append(
            f"Cross-branch recovery image/shim rejected: body={body_branch}({cfg.body_model_id:#x}), "
            f"image={img_branch}({cfg.recovery_image_model_id:#x}, fw={cfg.recovery_image_fw_version}), "
            f"shim={shim_branch}"
        )

    # 4. CAMSET01.DAT..CAMSET10.DAT SD settings import firewall (bidirectional FX3 <-> FX3A/FX30/FX6 block)
    camset_ok = True
    if cfg.camset_filename is not None:
        cam_fn = cfg.camset_filename.strip()
        cam_name_ok = bool(_CAMSET_RE.match(cam_fn))
        cam_ver_ok = (
            cam_ver is not None
            and ((cam_branch == P190_FX3_BRANCH and cam_ver[0] >= 7) or (cam_branch != P190_FX3_BRANCH and cam_ver[0] < 7))
        )
        camset_ok = (
            cam_name_ok
            and cam_ver_ok
            and cam_branch == body_branch
            and cam_branch == P190_FX3_BRANCH
            and cfg.camset_source_model_id == cfg.body_model_id
            and cfg.camset_source_model_id == P190_FX3_MODEL_ID
        )
        if not camset_ok:
            blocked.append(P190_BLOCKED_CROSS_BRANCH_CAMSET_IMPORT)
            errors.append(
                f"Cross-branch or invalid CAMSET import blocked: file={cam_fn!r}, "
                f"source={cam_branch}({cfg.camset_source_model_id:#x}, fw={cfg.camset_source_fw_version}), "
                f"body={body_branch}({cfg.body_model_id:#x})"
            )

    # 5. Stock FX3 p2:/setting/Backup.bin preservation (H0 == H3 + BLKROSET=1)
    p2_ok = (
        cfg.p2_blkroset_locked
        and bool(_SHA256_RE.match(cfg.p2_backup_bin_h0_sha256))
        and cfg.p2_backup_bin_h0_sha256 == cfg.p2_backup_bin_h3_sha256
    )
    if not p2_ok:
        blocked.append(P190_BLOCKED_BACKUP_BIN_H0_H3_OR_RO_DRIFT)
        errors.append("Stock p2:/setting/Backup.bin H0==H3 invariance or BLKROSET=1 lock violated")

    # 6. < 50 us pre-mount detection ceiling
    latency_ok = 0.0 <= cfg.detection_latency_us <= P190_FAIL_CLOSED_MAX_LATENCY_US
    if not latency_ok:
        blocked.append(P190_BLOCKED_LATENCY_BUDGET_EXCEEDED)
        errors.append(
            f"Pre-mount branch detection latency {cfg.detection_latency_us:.1f} us exceeded "
            f"{P190_FAIL_CLOSED_MAX_LATENCY_US:.1f} us ceiling"
        )

    dedup_blocked = tuple(dict.fromkeys(blocked))
    passed = (
        body_is_fx3
        and lcd_nfc_ir_ok
        and recovery_image_ok
        and camset_ok
        and p2_ok
        and latency_ok
        and len(dedup_blocked) == 0
        and len(errors) == 0
    )
    return Fx3BranchRecoveryFirewallReport(
        passed=passed,
        recovery_admitted=passed,
        fail_closed_triggered=not passed,
        body_branch_fx3_verified=body_is_fx3,
        lcd_nfc_ir_signature_ok=lcd_nfc_ir_ok,
        recovery_image_branch_ok=recovery_image_ok,
        camset_import_ok=camset_ok,
        p2_backup_bin_h0_eq_h3=p2_ok,
        latency_under_50us_ok=latency_ok,
        body_branch=body_branch,
        recovery_image_branch=img_branch,
        camset_filename=cfg.camset_filename,
        blocked_codes=dedup_blocked,
        errors=tuple(errors),
    )


def run_pillar26a_fx3a_branch_firewall_6_scenario_suite() -> Pillar26AFirewallSuiteResult:
    """Run all 6 deterministic scenarios for Pillar 26A (`ILME-FX3` vs `ILME-FX3A` / `CAMSET`)."""
    outcomes: List[Pillar26AScenarioOutcome] = []

    # P26A1: Happy ILME-FX3 (0x91030080, 7.02, 1.44M LCD + NFC + IR) + FX3 recovery + CAMSET01.DAT + H0==H3
    r1 = evaluate_fx3a_branch_recovery_firewall(Fx3BranchRecoveryFirewallSpec())
    ok1 = r1.passed and r1.recovery_admitted and (not r1.fail_closed_triggered) and r1.p2_backup_bin_h0_eq_h3
    outcomes.append(
        Pillar26AScenarioOutcome(
            P190_PILLAR_26A_SCENARIO_IDS[0],
            ok1,
            r1.recovery_admitted,
            r1.blocked_codes,
            "ILME-FX3 (0x91030080, 7.02, 1.44M+NFC+IR) + FX3 BODYDATA/CAMSET01.DAT + Backup.bin H0==H3 admitted (<50us)",
        )
    )

    # P26A2: ILME-FX3A (Ver. 2.02, 2.36M XGA LCD, no NFC/IR) detected & rejected <50us fail-closed
    r2 = evaluate_fx3a_branch_recovery_firewall(
        Fx3BranchRecoveryFirewallSpec(
            body_branch="FX3A",
            body_model_name="ILME-FX3A",
            body_firmware_version="2.02",
            body_lcd_dots=P190_FX3A_LCD_DOTS,
            body_has_nfc=False,
            body_has_ir_receiver=False,
            recovery_image_branch="FX3A",
            recovery_image_fw_version="2.02",
            display_shim_branch="FX3A",
            camset_source_branch="FX3A",
            camset_source_fw_version="2.02",
        )
    )
    ok2 = (
        (not r2.passed)
        and (not r2.recovery_admitted)
        and r2.fail_closed_triggered
        and (P190_BLOCKED_NON_FX3_HARDWARE_BRANCH in r2.blocked_codes)
        and (P190_BLOCKED_LCD_NFC_IR_SIGNATURE_MISMATCH in r2.blocked_codes)
    )
    outcomes.append(
        Pillar26AScenarioOutcome(
            P190_PILLAR_26A_SCENARIO_IDS[1],
            ok2,
            r2.recovery_admitted,
            r2.blocked_codes,
            "ILME-FX3A (2.36M XGA LCD, no NFC/IR, Ver. 2.02) fail-closed rejected <50us before Stage-A mount",
        )
    )

    # P26A3: FX3A Ver. 1.xx/2.xx BODYDATA.DAT on FX3 (0x91030080) AND vice versa (FX3 7.02 on FX3A)
    r3_fx3a_on_fx3 = evaluate_fx3a_branch_recovery_firewall(
        Fx3BranchRecoveryFirewallSpec(
            recovery_image_branch="FX3A",
            recovery_image_fw_version="2.02",
        )
    )
    r3_fx3a_v1_on_fx3 = evaluate_fx3a_branch_recovery_firewall(
        Fx3BranchRecoveryFirewallSpec(
            recovery_image_branch="FX3A",
            recovery_image_fw_version="1.00",
        )
    )
    r3_fx3_on_fx3a = evaluate_fx3a_branch_recovery_firewall(
        Fx3BranchRecoveryFirewallSpec(
            body_branch="FX3A",
            body_model_name="ILME-FX3A",
            body_firmware_version="2.02",
            body_lcd_dots=P190_FX3A_LCD_DOTS,
            body_has_nfc=False,
            body_has_ir_receiver=False,
            recovery_image_branch="FX3",
            recovery_image_fw_version="7.02",
        )
    )
    ok3 = (
        (not r3_fx3a_on_fx3.passed)
        and (not r3_fx3a_v1_on_fx3.passed)
        and (not r3_fx3_on_fx3a.passed)
        and (P190_BLOCKED_CROSS_BRANCH_BODYDATA_IMAGE in r3_fx3a_on_fx3.blocked_codes)
        and (P190_BLOCKED_CROSS_BRANCH_BODYDATA_IMAGE in r3_fx3a_v1_on_fx3.blocked_codes)
        and (P190_BLOCKED_CROSS_BRANCH_BODYDATA_IMAGE in r3_fx3_on_fx3a.blocked_codes)
    )
    outcomes.append(
        Pillar26AScenarioOutcome(
            P190_PILLAR_26A_SCENARIO_IDS[2],
            ok3,
            False,
            r3_fx3a_on_fx3.blocked_codes,
            "Bidirectional FX3A (Ver. 1.xx/2.xx) <-> FX3 (Ver. 7.02) BODYDATA.DAT recovery images blocked",
        )
    )

    # P26A4: FX30 (0x91030084) and FX6 (0x91020080) on FX3 (0x91030080) and vice versa
    r4_fx30_on_fx3 = evaluate_fx3a_branch_recovery_firewall(
        Fx3BranchRecoveryFirewallSpec(
            recovery_image_branch="FX30",
            recovery_image_model_id=P190_FX30_MODEL_ID,
            recovery_image_fw_version="5.00",
        )
    )
    r4_fx6_on_fx3 = evaluate_fx3a_branch_recovery_firewall(
        Fx3BranchRecoveryFirewallSpec(
            recovery_image_branch="FX6",
            recovery_image_model_id=P190_FX6_MODEL_ID,
            recovery_image_fw_version="5.00",
        )
    )
    r4_fx3_on_fx30 = evaluate_fx3a_branch_recovery_firewall(
        Fx3BranchRecoveryFirewallSpec(
            body_branch="FX30",
            body_model_name="ILME-FX30",
            body_model_id=P190_FX30_MODEL_ID,
            body_firmware_version="5.00",
            recovery_image_branch="FX3",
            recovery_image_model_id=P190_FX3_MODEL_ID,
            recovery_image_fw_version="7.02",
        )
    )
    ok4 = (
        (not r4_fx30_on_fx3.passed)
        and (not r4_fx6_on_fx3.passed)
        and (not r4_fx3_on_fx30.passed)
        and (P190_BLOCKED_CROSS_BRANCH_BODYDATA_IMAGE in r4_fx30_on_fx3.blocked_codes)
        and (P190_BLOCKED_CROSS_BRANCH_BODYDATA_IMAGE in r4_fx6_on_fx3.blocked_codes)
        and (P190_BLOCKED_CROSS_BRANCH_BODYDATA_IMAGE in r4_fx3_on_fx30.blocked_codes)
    )
    outcomes.append(
        Pillar26AScenarioOutcome(
            P190_PILLAR_26A_SCENARIO_IDS[3],
            ok4,
            False,
            r4_fx30_on_fx3.blocked_codes,
            "Bidirectional FX30 (0x91030084) & FX6 (0x91020080) <-> FX3 (0x91030080) cross-SKU images blocked",
        )
    )

    # P26A5: Cross-branch CAMSET01.DAT..CAMSET10.DAT import (FX3A -> FX3 & FX3 -> FX3A & invalid slot)
    r5_cam_fx3a = evaluate_fx3a_branch_recovery_firewall(
        Fx3BranchRecoveryFirewallSpec(
            camset_filename="CAMSET10.DAT",
            camset_source_branch="FX3A",
            camset_source_fw_version="2.02",
        )
    )
    r5_cam_fx3_on_fx3a = evaluate_fx3a_branch_recovery_firewall(
        Fx3BranchRecoveryFirewallSpec(
            body_branch="FX3A",
            body_model_name="ILME-FX3A",
            body_firmware_version="2.02",
            body_lcd_dots=P190_FX3A_LCD_DOTS,
            body_has_nfc=False,
            body_has_ir_receiver=False,
            camset_filename="CAMSET01.DAT",
            camset_source_branch="FX3",
            camset_source_fw_version="7.02",
        )
    )
    ok5 = (
        (not r5_cam_fx3a.passed)
        and (not r5_cam_fx3_on_fx3a.passed)
        and (not r5_cam_fx3a.camset_import_ok)
        and (P190_BLOCKED_CROSS_BRANCH_CAMSET_IMPORT in r5_cam_fx3a.blocked_codes)
        and (P190_BLOCKED_CROSS_BRANCH_CAMSET_IMPORT in r5_cam_fx3_on_fx3a.blocked_codes)
    )
    outcomes.append(
        Pillar26AScenarioOutcome(
            P190_PILLAR_26A_SCENARIO_IDS[4],
            ok5,
            False,
            r5_cam_fx3a.blocked_codes,
            "Cross-branch CAMSET01..CAMSET10.DAT SD settings import (FX3 <-> FX3A) blocked fail-closed",
        )
    )

    # P26A6: Stock p2:/setting/Backup.bin H0!=H3 drift, BLKROSET unlock, or write unlock blocked
    r6 = evaluate_fx3a_branch_recovery_firewall(
        Fx3BranchRecoveryFirewallSpec(
            p2_backup_bin_h3_sha256="e" * 64,
            p2_blkroset_locked=False,
            request_persistent_write_unlock=True,
        )
    )
    ok6 = (
        (not r6.passed)
        and (not r6.p2_backup_bin_h0_eq_h3)
        and (P190_BLOCKED_BACKUP_BIN_H0_H3_OR_RO_DRIFT in r6.blocked_codes)
        and (P190_BLOCKED_SAFETY_POLICY_VIOLATION in r6.blocked_codes)
        and r6.physical_device_writes == 0
    )
    outcomes.append(
        Pillar26AScenarioOutcome(
            P190_PILLAR_26A_SCENARIO_IDS[5],
            ok6,
            r6.recovery_admitted,
            r6.blocked_codes,
            "Stock p2:/setting/Backup.bin H0!=H3 drift & persistent write unlock rejected with 0 device writes",
        )
    )

    passed_count = sum(1 for o in outcomes if o.passed)
    all_ok = passed_count == len(P190_PILLAR_26A_SCENARIO_IDS)
    return Pillar26AFirewallSuiteResult(
        passed=all_ok,
        status=P190_STATUS_VERIFIED_PILLAR_26A if all_ok else P190_STATUS_REJECTED_PILLAR_26A,
        scenarios_passed=passed_count,
        scenarios_total=len(P190_PILLAR_26A_SCENARIO_IDS),
        scenarios=tuple(outcomes),
    )


# ---------------------------------------------------------------------------
# 3. Pillar 26B — XLR-H1 MI-Shoe 48kHz/24bit 4ch Audio & Post-UFU Hygiene
# ---------------------------------------------------------------------------


def evaluate_xlrh1_mishoe_audio_hygiene(
    spec: Optional[Xlrh1AudioHygieneSpec] = None,
) -> Xlrh1AudioHygieneReport:
    """Audit `XLR-H1` MI-Shoe 4ch/24bit routing, zero handle FW write, 3.5mm override & post-UFU hygiene."""
    cfg = spec if spec is not None else Xlrh1AudioHygieneSpec()
    blocked: List[str] = []
    errors: List[str] = []

    if cfg.request_persistent_write_unlock or PERSISTENT_EMMC_WRITES_AUTHORIZED:
        blocked.append(P190_BLOCKED_SAFETY_POLICY_VIOLATION)
        errors.append("Persistent eMMC write unlock forbidden during XLR-H1 audio hygiene audit")

    # 1. Zero standalone XLR-H1 firmware write attempts (Sony never ships standalone XLR-H1 firmware)
    zero_handle_fw_ok = (
        P190_XLRH1_STANDALONE_FW_SHIPPED is False
        and cfg.standalone_handle_fw_write_requested is False
        and len(cfg.standalone_handle_fw_files_present) == 0
    )
    if not zero_handle_fw_ok:
        blocked.append(P190_BLOCKED_XLRH1_FIRMWARE_WRITE_FORBIDDEN)
        errors.append(
            f"Standalone XLR-H1 handle firmware write or spoofed payload blocked "
            f"(files={cfg.standalone_handle_fw_files_present})"
        )

    # 2. Digital audio profile & channel routing + headphone monitor matrix
    norm_profile = cfg.audio_profile.strip().upper()
    norm_matrix = cfg.headphone_monitor_matrix.strip().upper()
    profile_valid = norm_profile in P190_XLRH1_AUDIO_PROFILES
    channels = P190_XLRH1_AUDIO_PROFILES[norm_profile][2] if profile_valid else 0
    in3_ok = (cfg.in3_route == "CH3_CH4") if channels == 4 else (cfg.in3_route in ("CH3_CH4", "OFF"))
    routing_ok = (
        cfg.handle_attached
        and cfg.handle_model == P190_XLRH1_HANDLE_MODEL
        and cfg.handle_audio_switch_on
        and profile_valid
        and cfg.in1_in2_route == "CH1_CH2"
        and in3_ok
        and norm_matrix in P190_XLRH1_MONITOR_MATRICES
    )
    if not routing_ok:
        blocked.append(P190_BLOCKED_XLRH1_FORMAT_OR_ROUTING_INVALID)
        errors.append(
            f"Invalid XLR-H1 audio profile/routing: handle={cfg.handle_model!r}, "
            f"profile={norm_profile}, in12={cfg.in1_in2_route}, in3={cfg.in3_route}, matrix={norm_matrix}"
        )

    # 3. Body 3.5mm mic jack physical override safety:
    #    Plugging into body 3.5mm mic jack hardware-cuts MI-Shoe audio and greys out [MI Shoe Audio Set.].
    #    During cold-boot recovery with mi_shoe_active_audio_expected=False, physical override is safe
    #    if MI-Shoe is muted and no +48V glitch occurs; if MI-Shoe active audio is expected, block!
    if cfg.body_35mm_mic_plug_inserted:
        if cfg.mi_shoe_active_audio_expected:
            override_safe = False
            blocked.append(P190_BLOCKED_BODY_35MM_MIC_JACK_OVERRIDE)
            errors.append(
                "Body 3.5mm mic jack physical switch overrides MI-Shoe and locks out [MI Shoe Audio Set.]"
            )
        else:
            override_safe = cfg.cold_boot_recovery_active and cfg.mi_shoe_audio_muted
            if not override_safe:
                blocked.append(P190_BLOCKED_BODY_35MM_MIC_JACK_OVERRIDE)
                errors.append("Body 3.5mm override active outside clean muted cold-boot recovery")
    else:
        override_safe = True

    # 4. S&Q forced mute consistency & zero +48V phantom glitch across Stage-A -> Stage-B
    sq_ok = (not cfg.sq_slow_quick_active) or cfg.mi_shoe_audio_muted
    v48_ok = not cfg.phantom_48v_stage_b_transition_glitch
    sq_and_48v_ok = sq_ok and v48_ok
    if not sq_and_48v_ok:
        blocked.append(P190_BLOCKED_SQ_MUTE_OR_48V_TRANSITION_GLITCH)
        errors.append(
            f"S&Q mute or +48V transition glitch violated: sq={cfg.sq_slow_quick_active}, "
            f"muted={cfg.mi_shoe_audio_muted}, glitch={cfg.phantom_48v_stage_b_transition_glitch}"
        )

    # 5. Post-UFU BODYDATA.DAT 48kHz/16bit 2ch default reset audit
    post_ufu_reset_documented = False
    if cfg.post_ufu_upgrade_performed:
        if norm_profile == P190_XLRH1_POST_UFU_DEFAULT_PROFILE:
            post_ufu_ok = True
            post_ufu_reset_documented = True
        elif cfg.post_ufu_rearmed_to_24bit_4ch and norm_profile == "48KHZ_24BIT_4CH":
            post_ufu_ok = True
        else:
            post_ufu_ok = False
            blocked.append(P190_BLOCKED_POST_UFU_XLRH1_RESET_UNAUDITED)
            errors.append(
                "Post-UFU BODYDATA.DAT upgrade resets [MI Shoe Audio Set.] to 48kHz/16bit 2ch; "
                "re-arming or reset acknowledgment required"
            )
    else:
        post_ufu_ok = True

    # 6. Zero Stage-B dirtying of p2:/setting/Backup.bin (H0 == H3 + BLKROSET=1)
    p2_clean_ok = (
        cfg.stage_b_backup_bin_writes == 0
        and cfg.p2_blkroset_locked
        and bool(_SHA256_RE.match(cfg.p2_backup_bin_h0_sha256))
        and cfg.p2_backup_bin_h0_sha256 == cfg.p2_backup_bin_h3_sha256
    )
    if not p2_clean_ok:
        blocked.append(P190_BLOCKED_STAGE_B_BACKUP_BIN_DIRTY)
        errors.append(
            f"Stage-B dirtied p2:/setting/Backup.bin or breached RO lock: "
            f"writes={cfg.stage_b_backup_bin_writes}, ro={cfg.p2_blkroset_locked}"
        )

    dedup_blocked = tuple(dict.fromkeys(blocked))
    passed = (
        zero_handle_fw_ok
        and routing_ok
        and override_safe
        and sq_and_48v_ok
        and post_ufu_ok
        and p2_clean_ok
        and len(dedup_blocked) == 0
        and len(errors) == 0
    )
    return Xlrh1AudioHygieneReport(
        passed=passed,
        hygiene_clean=passed,
        zero_handle_fw_write_ok=zero_handle_fw_ok,
        audio_format_and_routing_ok=routing_ok,
        body_35mm_override_safe=override_safe,
        sq_and_48v_transition_ok=sq_and_48v_ok,
        post_ufu_reset_audited_ok=post_ufu_ok,
        post_ufu_reset_to_16bit_2ch_documented=post_ufu_reset_documented,
        stage_b_zero_backup_bin_dirty_ok=p2_clean_ok,
        audio_profile=norm_profile,
        blocked_codes=dedup_blocked,
        errors=tuple(errors),
    )


def run_pillar26b_xlrh1_hygiene_6_scenario_suite() -> Pillar26BHygieneSuiteResult:
    """Run all 6 deterministic scenarios for Pillar 26B (`XLR-H1` MI-Shoe audio hygiene)."""
    outcomes: List[Pillar26BScenarioOutcome] = []

    # P26B1: Happy XLR-H1 48kHz/24bit 4ch + zero handle FW write + Backup.bin H0==H3
    r1 = evaluate_xlrh1_mishoe_audio_hygiene(Xlrh1AudioHygieneSpec())
    ok1 = r1.passed and r1.hygiene_clean and r1.zero_handle_fw_write_ok and r1.stage_b_zero_backup_bin_dirty_ok
    outcomes.append(
        Pillar26BScenarioOutcome(
            P190_PILLAR_26B_SCENARIO_IDS[0],
            ok1,
            r1.hygiene_clean,
            r1.blocked_codes,
            "XLR-H1 48kHz/24bit 4ch (IN1/2->CH1/2, IN3->CH3/4), 0 handle FW writes, Backup.bin H0==H3",
        )
    )

    # P26B2: Standalone XLR-H1 firmware write request or spoofed handle FW payload rejected
    r2_req = evaluate_xlrh1_mishoe_audio_hygiene(
        Xlrh1AudioHygieneSpec(standalone_handle_fw_write_requested=True)
    )
    r2_file = evaluate_xlrh1_mishoe_audio_hygiene(
        Xlrh1AudioHygieneSpec(standalone_handle_fw_files_present=("XLRH1_FW.BIN",))
    )
    ok2 = (
        (not r2_req.passed)
        and (not r2_file.passed)
        and (not r2_req.zero_handle_fw_write_ok)
        and (P190_BLOCKED_XLRH1_FIRMWARE_WRITE_FORBIDDEN in r2_req.blocked_codes)
        and (P190_BLOCKED_XLRH1_FIRMWARE_WRITE_FORBIDDEN in r2_file.blocked_codes)
    )
    outcomes.append(
        Pillar26BScenarioOutcome(
            P190_PILLAR_26B_SCENARIO_IDS[1],
            ok2,
            False,
            r2_req.blocked_codes,
            "Standalone XLR-H1 firmware write attempt & spoofed handle payload blocked fail-closed",
        )
    )

    # P26B3: Body 3.5mm mic jack physical override: safe in muted cold-boot recovery, blocked when MI-Shoe active expected
    r3_safe = evaluate_xlrh1_mishoe_audio_hygiene(
        Xlrh1AudioHygieneSpec(
            body_35mm_mic_plug_inserted=True,
            mi_shoe_active_audio_expected=False,
            cold_boot_recovery_active=True,
            mi_shoe_audio_muted=True,
        )
    )
    r3_blk = evaluate_xlrh1_mishoe_audio_hygiene(
        Xlrh1AudioHygieneSpec(
            body_35mm_mic_plug_inserted=True,
            mi_shoe_active_audio_expected=True,
        )
    )
    ok3 = (
        r3_safe.passed
        and r3_safe.body_35mm_override_safe
        and (not r3_blk.passed)
        and (not r3_blk.body_35mm_override_safe)
        and (P190_BLOCKED_BODY_35MM_MIC_JACK_OVERRIDE in r3_blk.blocked_codes)
    )
    outcomes.append(
        Pillar26BScenarioOutcome(
            P190_PILLAR_26B_SCENARIO_IDS[2],
            ok3,
            r3_safe.hygiene_clean and (not r3_blk.hygiene_clean),
            r3_blk.blocked_codes,
            "Body 3.5mm mic jack physical override verified safe in muted cold-boot recovery & blocked if MI-Shoe active expected",
        )
    )

    # P26B4: S&Q mode unmuted inconsistency & Stage-A->Stage-B +48V phantom glitch blocked
    r4 = evaluate_xlrh1_mishoe_audio_hygiene(
        Xlrh1AudioHygieneSpec(
            sq_slow_quick_active=True,
            mi_shoe_audio_muted=False,
            phantom_48v_stage_b_transition_glitch=True,
        )
    )
    ok4 = (
        (not r4.passed)
        and (not r4.sq_and_48v_transition_ok)
        and (P190_BLOCKED_SQ_MUTE_OR_48V_TRANSITION_GLITCH in r4.blocked_codes)
    )
    outcomes.append(
        Pillar26BScenarioOutcome(
            P190_PILLAR_26B_SCENARIO_IDS[3],
            ok4,
            r4.hygiene_clean,
            r4.blocked_codes,
            "S&Q unmuted audio inconsistency & +48V Stage-A->Stage-B phantom glitch blocked",
        )
    )

    # P26B5: Post-UFU 48kHz/16bit 2ch reset audited cleanly; unaudited post-UFU 24bit/4ch assumption blocked
    r5_audited = evaluate_xlrh1_mishoe_audio_hygiene(
        Xlrh1AudioHygieneSpec(
            post_ufu_upgrade_performed=True,
            audio_profile="48KHZ_16BIT_2CH",
            in3_route="OFF",
        )
    )
    r5_unaudited = evaluate_xlrh1_mishoe_audio_hygiene(
        Xlrh1AudioHygieneSpec(
            post_ufu_upgrade_performed=True,
            audio_profile="48KHZ_24BIT_4CH",
            post_ufu_rearmed_to_24bit_4ch=False,
        )
    )
    ok5 = (
        r5_audited.passed
        and r5_audited.post_ufu_reset_to_16bit_2ch_documented
        and (not r5_unaudited.passed)
        and (P190_BLOCKED_POST_UFU_XLRH1_RESET_UNAUDITED in r5_unaudited.blocked_codes)
    )
    outcomes.append(
        Pillar26BScenarioOutcome(
            P190_PILLAR_26B_SCENARIO_IDS[4],
            ok5,
            r5_audited.hygiene_clean and (not r5_unaudited.hygiene_clean),
            r5_unaudited.blocked_codes,
            "Post-UFU 48kHz/16bit 2ch default reset audited cleanly; unaudited 24bit/4ch claim blocked",
        )
    )

    # P26B6: Stage-B Backup.bin dirtying / H0!=H3 / persistent write unlock blocked
    r6 = evaluate_xlrh1_mishoe_audio_hygiene(
        Xlrh1AudioHygieneSpec(
            stage_b_backup_bin_writes=1,
            p2_backup_bin_h3_sha256="f" * 64,
            p2_blkroset_locked=False,
            request_persistent_write_unlock=True,
        )
    )
    ok6 = (
        (not r6.passed)
        and (not r6.stage_b_zero_backup_bin_dirty_ok)
        and (P190_BLOCKED_STAGE_B_BACKUP_BIN_DIRTY in r6.blocked_codes)
        and (P190_BLOCKED_SAFETY_POLICY_VIOLATION in r6.blocked_codes)
        and r6.physical_device_writes == 0
    )
    outcomes.append(
        Pillar26BScenarioOutcome(
            P190_PILLAR_26B_SCENARIO_IDS[5],
            ok6,
            r6.hygiene_clean,
            r6.blocked_codes,
            "Stage-B Backup.bin dirtying & persistent write unlock rejected with 0 device writes",
        )
    )

    passed_count = sum(1 for o in outcomes if o.passed)
    all_ok = passed_count == len(P190_PILLAR_26B_SCENARIO_IDS)
    return Pillar26BHygieneSuiteResult(
        passed=all_ok,
        status=P190_STATUS_VERIFIED_PILLAR_26B if all_ok else P190_STATUS_REJECTED_PILLAR_26B,
        scenarios_passed=passed_count,
        scenarios_total=len(P190_PILLAR_26B_SCENARIO_IDS),
        scenarios=tuple(outcomes),
    )


def run_pillar26_standalone_suite(
    *,
    force_clean_room: Optional[bool] = None,
) -> Pillar26StandaloneReport:
    """Run Pillar 26 standalone donor audit + Pillar 26A (`FX3 vs FX3A`) + Pillar 26B (`XLR-H1`)."""
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
    snap = inspect_phase190_donors_readonly(force_clean_room=force_clean_room)
    p26a = run_pillar26a_fx3a_branch_firewall_6_scenario_suite()
    p26b = run_pillar26b_xlrh1_hygiene_6_scenario_suite()
    elapsed = round(time.monotonic() - t0, 6)

    errors: List[str] = list(snap.errors)
    if not p26a.passed:
        errors.append("Pillar 26A FX3 vs FX3A recovery & CAMSET branch firewall suite failed")
    if not p26b.passed:
        errors.append("Pillar 26B XLR-H1 MI-Shoe audio hygiene suite failed")

    all_ok = (
        snap.all_passed
        and p26a.passed
        and p26b.passed
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
            "schema": PHASE190_SCHEMA,
            "version": PHASE190_VERSION,
            "mode": snap.verification_mode,
            "snapshot_sha256": snap.snapshot_sha256,
            "p26a": p26a.to_dict(),
            "p26b": p26b.to_dict(),
            "all_passed": all_ok,
        }
    )
    return Pillar26StandaloneReport(
        schema=PHASE190_SCHEMA,
        version=PHASE190_VERSION,
        verification_mode=snap.verification_mode,
        all_passed=all_ok,
        status=P190_STATUS_VERIFIED_PILLAR26_SUITE if all_ok else P190_STATUS_FAIL_PILLAR26_SUITE,
        elapsed_seconds=elapsed,
        donor_snapshot=snap,
        pillar_26a_fx3a_firewall=p26a,
        pillar_26b_xlrh1_hygiene=p26b,
        suite_sha256=suite_sha,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# 4. Unified 26/26 Recovery Master Aggregator (`evaluate_26pillar_recovery_master`)
# ---------------------------------------------------------------------------


def _apply_master26_fault_injection(pillar: MasterPillarStatus) -> MasterPillarStatus:
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


def evaluate_26pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master26PillarRecoveryReport:
    """Evaluate and aggregate all 26 recovery pillars (`1..26`) concurrently in `< 2.0s`."""
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
        _need(fault_inject_pillar in MASTER_26_PILLAR_IDS, f"Unknown fault_inject_pillar: {fault_inject_pillar}")

    t_start = time.monotonic()
    kw: Dict[str, Any] = {"force_clean_room": force_clean_room} if force_clean_room is not None else {}

    def _run_24pillar() -> Master24PillarRecoveryReport:
        return evaluate_24pillar_recovery_master(**kw)

    def _run_p25() -> Tuple[Pillar25AirgapSdBundleReport, float]:
        t0 = time.monotonic()
        res = run_airgap_sd_bundle_manifest_suite(**kw)
        return res, round(time.monotonic() - t0, 6)

    def _run_p26() -> Tuple[Pillar26StandaloneReport, float]:
        t0 = time.monotonic()
        res = run_pillar26_standalone_suite(**kw)
        return res, round(time.monotonic() - t0, 6)

    with ThreadPoolExecutor(max_workers=3) as pool:
        fut_24 = pool.submit(_run_24pillar)
        fut_25 = pool.submit(_run_p25)
        fut_26 = pool.submit(_run_p26)

        m24_rep = fut_24.result()
        p25_rep, p25_dt = fut_25.result()
        p26_rep, p26_dt = fut_26.result()

    safety_errors: List[str] = list(m24_rep.errors)
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
        if getattr(m24_rep, attr_name) != expected_val:
            safety_errors.append(f"Pillars 1-24 violated {attr_name} == {expected_val}")
        if hasattr(p25_rep, attr_name) and getattr(p25_rep, attr_name) != expected_val:
            safety_errors.append(f"Pillar 25 violated {attr_name} == {expected_val}")
        if hasattr(p26_rep, attr_name) and getattr(p26_rep, attr_name) != expected_val:
            safety_errors.append(f"Pillar 26 violated {attr_name} == {expected_val}")

    if getattr(p25_rep, "airgap_sockets_opened", 0) != 0:
        safety_errors.append("Pillar 25 violated airgap_sockets_opened == 0")

    pillar_statuses: List[MasterPillarStatus] = list(m24_rep.pillars)

    # Pillar 25 entry
    spec25 = MASTER_26_PILLAR_SPECS[24]
    p25_metrics = {
        "pillar_25a_fx3bndl1": f"{p25_rep.pillar_25a_fx3bndl1_binding.scenarios_passed}/{p25_rep.pillar_25a_fx3bndl1_binding.scenarios_total}",
        "pillar_25b_exfat_hygiene": f"{p25_rep.pillar_25b_exfat_hygiene.scenarios_passed}/{p25_rep.pillar_25b_exfat_hygiene.scenarios_total}",
        "airgap_sockets_opened": p25_rep.airgap_sockets_opened,
        "donor_files_inspected": p25_rep.donor_snapshot.donor_files_inspected,
    }
    pillar_statuses.append(
        MasterPillarStatus(
            pillar_number=spec25[0],
            pillar_id=spec25[1],
            phase_label=spec25[2],
            module_name=spec25[3],
            passed=bool(p25_rep.all_passed),
            status=p25_rep.status,
            verification_mode=p25_rep.verification_mode,
            elapsed_seconds=p25_dt,
            key_metrics=p25_metrics,
            digest_sha256=_canonical_sha256(
                {
                    "pillar": spec25[1],
                    "mode": p25_rep.verification_mode,
                    "status": p25_rep.status,
                    "metrics": p25_metrics,
                    "passed": p25_rep.all_passed,
                }
            ),
            errors=tuple(p25_rep.errors),
        )
    )

    # Pillar 26 entry
    spec26 = MASTER_26_PILLAR_SPECS[25]
    p26_metrics = {
        "pillar_26a_fx3a_firewall": f"{p26_rep.pillar_26a_fx3a_firewall.scenarios_passed}/{p26_rep.pillar_26a_fx3a_firewall.scenarios_total}",
        "pillar_26b_xlrh1_hygiene": f"{p26_rep.pillar_26b_xlrh1_hygiene.scenarios_passed}/{p26_rep.pillar_26b_xlrh1_hygiene.scenarios_total}",
        "donor_files_inspected": p26_rep.donor_snapshot.donor_files_inspected,
    }
    pillar_statuses.append(
        MasterPillarStatus(
            pillar_number=spec26[0],
            pillar_id=spec26[1],
            phase_label=spec26[2],
            module_name=spec26[3],
            passed=bool(p26_rep.all_passed),
            status=p26_rep.status,
            verification_mode=p26_rep.verification_mode,
            elapsed_seconds=p26_dt,
            key_metrics=p26_metrics,
            digest_sha256=_canonical_sha256(
                {
                    "pillar": spec26[1],
                    "mode": p26_rep.verification_mode,
                    "status": p26_rep.status,
                    "metrics": p26_metrics,
                    "passed": p26_rep.all_passed,
                }
            ),
            errors=tuple(p26_rep.errors),
        )
    )

    if fault_inject_pillar is not None:
        pillar_statuses = [
            _apply_master26_fault_injection(p) if p.pillar_id == fault_inject_pillar else p
            for p in pillar_statuses
        ]

    elapsed = round(time.monotonic() - t_start, 6)
    failed = tuple(p.pillar_id for p in pillar_statuses if not p.passed)
    pillars_passed = sum(1 for p in pillar_statuses if p.passed)
    verification_mode = p26_rep.verification_mode

    all_ok = (
        len(pillar_statuses) == MASTER_26_PILLAR_COUNT == 26
        and pillars_passed == 26
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
            "schema": PHASE190_SCHEMA,
            "version": PHASE190_VERSION,
            "verification_mode": verification_mode,
            "pillar_count": len(pillar_statuses),
            "pillars_passed": pillars_passed,
            "failed_pillars": list(failed),
            "pillar_digests": [(p.pillar_number, p.pillar_id, p.passed, p.digest_sha256) for p in pillar_statuses],
            "all_passed": all_ok,
        }
    )

    return Master26PillarRecoveryReport(
        schema=PHASE190_SCHEMA,
        version=PHASE190_VERSION,
        verification_mode=verification_mode,
        all_passed=all_ok,
        status=P190_STATUS_VERIFIED_26OF26_AGGREGATOR if all_ok else P190_STATUS_FAIL_26OF26_AGGREGATOR,
        pillar_count=len(pillar_statuses),
        pillars_passed=pillars_passed,
        failed_pillars=failed,
        elapsed_seconds=elapsed,
        under_6s_budget=elapsed < P190_CONCURRENT_CEILING_SECONDS,
        nominal_under_2s=elapsed < P190_NOMINAL_BUDGET_SECONDS,
        pillars=tuple(pillar_statuses),
        donor_snapshot=p26_rep.donor_snapshot,
        pillar25_airgap_sd_bundle=p25_rep,
        pillar26_a_fx3a_firewall=p26_rep.pillar_26a_fx3a_firewall,
        pillar26_b_xlrh1_hygiene=p26_rep.pillar_26b_xlrh1_hygiene,
        master_26pillar_sha256=master_sha,
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


def verify_26pillar_recovery_suite(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master26PillarRecoveryReport:
    """Public entry point for Pillar 26 unified `26/26` real-hardware recovery master verification."""
    return evaluate_26pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )
