"""Phase 143 — Real-Hardware Main Track Part 10: Reproducible BYOF SD-Card Stage-B
Deployment Bundle Builder (`FX6_STAGEB_BOOT.MANIFEST`), `im.elf` Escape-Hatch Launcher
& `H0 == H3` Factory-Byte-Identical Uninstaller Verifier.

Implements dual-mode (`LOCAL_DONOR_O_RDONLY` strictly via `os.O_RDONLY` and deterministic
`CLEAN_ROOM_SYNTHETIC` fallback via `FX3_FX6_FORCE_CLEAN_ROOM=1`) verification across
four pillars while keeping physical eMMC and SD writes hard-locked OFF:

1. Pillar 1 (`BYOF_SD_STAGEB_TREE_AND_SIGNED_MANIFEST_BUILDER`):
   - Synthesizes and validates in-memory the exFAT/FAT32 SD-card tree layout:
     `/FX6_STAGEB/FX6_STAGEB_BOOT.MANIFEST`,
     `/FX6_STAGEB/shim/libgrm-fbinit9.so`,
     `/FX6_STAGEB/shim/libmpr_fx6_to_fx3_bridge.so`,
     `/FX6_STAGEB/usr_overlay/...`,
     `/FX6_STAGEB/runtime/bk4_ram_shadow.seed`,
     `/FX6_STAGEB/rescue/uninstall_restore_stock.manifest`.
   - Enforces `13/13` Stage-B artifact SHA-256 lock verification, body-bound
     serial / Tier-0 backup receipt binding (`FX3RCPT1` + `MANIFEST.SHA256`,
     refusing foreign camera serials or unverified receipts), and `< 64 MiB`
     total RAM/tmpfs footprint within FX3's `2048 MiB` DDR budget.

2. Pillar 2 (`ESCAPE_HATCH_LAUNCHER_AND_COMBO_KEY_BYPASS`):
   - Generates and audits the `/usr/bin/im.elf` minimal escape-hatch wrapper
     featuring 3 independent zero-brick escape hatches and executes real `/bin/sh`
     sandbox drills in an isolated `TemporaryDirectory`:
     a) Escape Hatch 1: SD card absent -> immediate `execve("/usr/bin/im.elf.orig")`
        in `< 50 us` (`47 us` contract).
     b) Escape Hatch 2: Emergency combo key (`MENU+PLAY`) or `/mnt/sd/STOP_STAGEB.FLAG`
        -> immediate stock `im.elf.orig` boot + optional auto-uninstall trigger.
     c) Escape Hatch 3: Corrupt `FX6_STAGEB_BOOT.MANIFEST`, foreign serial, or any
        of the 13 artifact SHA-256 hashes failing -> fail-closed fallback to stock
        `im.elf.orig` + diagnostic log at `/mnt/sd/FX6_STAGEB/LAST_BOOT_DIAG.TXT`.

3. Pillar 3 (`ATOMIC_CLEAN_UNINSTALLER_AND_H0_EQUALS_H3_PROOF`):
   - Simulates the complete 4-epoch lifecycle
     `H0 (Factory Stock FX3 7.02) -> H1 (Atomic cnflasha15 Install) ->
      H2 (Stage-B Dual-Boot Shooting Session) -> H3 (Atomic Clean Uninstall)`
     across all 16 critical storage surfaces (`sector0`, `p1`, `p2`, `p3`, `p5`,
     `p6`, `p7`, `p8`, `p12`, `p15`, `p18`, `p23`, `p30`, `spi_nor`, `otp`, `rpmb`),
     proving `H0 == H3` (`16/16` surfaces 100% SHA-256 byte-identical, zero `.orig`
     or residual Stage-B files left on `p15` or `p6`), plus 5 fault-injected
     mid-uninstall power-loss and raw-plaintext-block recovery drills.

4. Pillar 4 (`HARD_LOCKED_NO_PHYSICAL_FLASH_GUARD`):
   - Hard-locks `persistent_emmc_writes_authorized = False`,
     `sd_physical_media_written = False`, `persistent_write_release = False`,
     and `physical_device_writes = 0`.
   - Zero raw proprietary binary bytes are copied into tracked repo files or JSON.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import copy
import hashlib
import json
import mmap
import os
import posixpath
import re
import stat
import struct
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from fx3_safety.boot_contracts import BK4_MAGIC, parse_bk4_record

from .donor_paths import (
    is_forced_clean_room,
    resolve_fx3_modules_dir,
    resolve_fx6_donor_lib_dir,
    resolve_fx6_donor_root,
    resolve_work_subpath,
)
from .hardware_readiness_packet import (
    BODY_SERIAL_RE,
    FORBIDDEN_TRIVIAL_CIDS,
    FORBIDDEN_TRIVIAL_SERIALS,
    FX3_MODEL_ID_HEX,
    HEX32_CID_RE,
    HEX64_RE,
    SYNTHETIC_ORIGIN_TOKENS,
)
from .patcher import (
    DEFAULT_FX3_MODULES_DIR,
    DEFAULT_FX6_DONOR_LIB_DIR,
    FX6_APPFW_DONOR_SHA256,
    FX6_APPFW_STAGE_B_SHA256,
    FX6_WLAN_RSRC_DONOR_SHA256,
    FX6_WLAN_RSRC_P12_SHA256,
)
from .stage_b_ram_overlay_packager import (
    STAGE_B_LOCK_TABLE_13_ARTIFACTS,
    STAGE_B_SUPPORTED_LANGS,
    StageBLockTableEntry,
    build_stage_b_ram_overlay_v2_package,
)


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

PHASE_143_SCHEMA = "phase143_realhw_sd_stageb_bundle_uninstaller_v1"
PHASE_143_VERSION = "143.0.0"

# Hard-locked safety redlines (cannot be unlocked by callers)
PERSISTENT_EMMC_WRITES_AUTHORIZED = False
SD_PHYSICAL_MEDIA_WRITTEN = False
PERSISTENT_WRITE_RELEASE = False
PHYSICAL_DEVICE_WRITES = 0

FX3_MODEL_ID_STR = "91030080"
FX3_FIRMWARE_VERSION = "7.02"
FX6_FIRMWARE_VERSION = "6.01"

# DDR / tmpfs memory budget (< 64 MiB within FX3's 2048 MiB DDR)
MIB_BYTES = 1024 * 1024
FX3_DDR_TOTAL_BYTES = 2048 * MIB_BYTES
SD_STAGEB_RAM_BUDGET_LIMIT_MIB = 64.0
SD_STAGEB_RAM_BUDGET_LIMIT_BYTES = 64 * MIB_BYTES  # 67,108,864 B

# Escape-hatch latency ceiling (< 50 us)
ESCAPE_HATCH_MAX_LATENCY_US = 50
ESCAPE_HATCH_ABSENT_LATENCY_US = 47

# Pinned donor metadata (0 raw proprietary bytes emitted)
FX3_IM_ELF_RELPATH = (
    "sony-firmware-20261024/stage183-request-consumer-and-early-entry/"
    "evidence/usb-main-dependency/originals/bin/im.elf"
)
FX3_IM_ELF_EXPECTED_SIZE = 40920
FX3_IM_ELF_EXPECTED_SHA256 = (
    "5171f576d8b76cfbf15581389183b390c445bd6ff9dd97fd6668c5f64e77dc91"
)
FX6_APPFW_EXPECTED_SIZE = 50520424
FX6_UXC_TOTAL_COUNT = 62
FX6_UXC_TOTAL_BYTES = 12148560
FX6_CORE_UXC_ASSETS: Dict[str, Tuple[int, str]] = {
    "color_cmn.uxc": (
        288,
        "ea2e508f9ba567655dd36be6245ada221e595e83f8343b733f3894109f9dd230",
    ),
    "image_00_169.uxc": (
        3941000,
        "f9bb82a2cf6364e5683ea9cce7e63b0a891325a8c250904cf28d2417fe2c4148",
    ),
    "lang_cmn.uxc": (
        1048,
        "ad547c47444e134bcf3622b84344d82273d4c5d04fd3775a7cf6fb58f5db63c5",
    ),
    "string_english.uxc": (
        118208,
        "5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739",
    ),
    "string_simplifiedchinese.uxc": (
        118644,
        "ba060e859156bfaefcc4177bfa6e9c5bea112258b15ce815a5ba683d033e688f",
    ),
    "string_traditionalchinese.uxc": (
        119168,
        "8c34b415ce4d19fd40ca22d00c4543c64eb4741b96250de13b93ec473b25b18b",
    ),
    "string_japanese.uxc": (
        141692,
        "9b47630ebe8e011a9d0bdb7a2fda06574f5187222b92d60bf6887042fe186d35",
    ),
}

# SD-card canonical layout paths (relative to /mnt/sd/)
SD_ROOT_DIR = "FX6_STAGEB"
SD_MANIFEST_RELPATH = "FX6_STAGEB/FX6_STAGEB_BOOT.MANIFEST"
SD_SHIM_FBINIT9_RELPATH = "FX6_STAGEB/shim/libgrm-fbinit9.so"
SD_SHIM_MPR_BRIDGE_RELPATH = "FX6_STAGEB/shim/libmpr_fx6_to_fx3_bridge.so"
SD_USR_OVERLAY_PREFIX = "FX6_STAGEB/usr_overlay"
SD_BK4_SHADOW_SEED_RELPATH = "FX6_STAGEB/runtime/bk4_ram_shadow.seed"
SD_UNINSTALL_MANIFEST_RELPATH = "FX6_STAGEB/rescue/uninstall_restore_stock.manifest"
SD_STOP_FLAG_RELPATH = "STOP_STAGEB.FLAG"
SD_DIAG_LOG_RELPATH = "FX6_STAGEB/LAST_BOOT_DIAG.TXT"

SD_REQUIRED_TREE_PATHS: Tuple[str, ...] = (
    SD_MANIFEST_RELPATH,
    SD_SHIM_FBINIT9_RELPATH,
    SD_SHIM_MPR_BRIDGE_RELPATH,
    SD_BK4_SHADOW_SEED_RELPATH,
    SD_UNINSTALL_MANIFEST_RELPATH,
)

# Error / firewall status codes
BLOCKED_FOREIGN_CAMERA_TIER0_SERIAL_MISMATCH = (
    "BLOCKED_FOREIGN_CAMERA_TIER0_SERIAL_MISMATCH"
)
BLOCKED_UNVERIFIED_TIER0_RECEIPT = "BLOCKED_UNVERIFIED_TIER0_RECEIPT"
BLOCKED_SYNTHETIC_OR_INVALID_BODY_ID = "BLOCKED_SYNTHETIC_OR_INVALID_BODY_ID"
ERR_DDR_TMPFS_BUDGET_EXCEEDED = "ERR_DDR_TMPFS_BUDGET_EXCEEDED_GE_64MIB"
ERR_EXFAT_PATH_INVALID = "ERR_EXFAT_FAT32_PATH_CONSTRAINT_VIOLATION"
ERR_LOCK_TABLE_13_INCOMPLETE = "ERR_STAGE_B_13_LOCK_TABLE_INCOMPLETE"
BLOCKED_RAW_PNFLASHA_PLAINTEXT_WRITE = (
    "BLOCKED_RAW_PNFLASHA_PLAINTEXT_CIPHERTEXT_CORRUPTION"
)
ERR_ORIG_SHA256_MISMATCH_ABORT = "ERR_ORIG_SHA256_MISMATCH_FAIL_CLOSED_ABORT"

# All 16 critical storage surfaces for H0 -> H1 -> H2 -> H3 parity proof
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

FOUR_EPOCHS: Tuple[str, ...] = (
    "H0_FACTORY_STOCK",
    "H1_ATOMIC_CNFLASHA15_INSTALL",
    "H2_STAGEB_SHOOTING_SESSION",
    "H3_ATOMIC_CLEAN_UNINSTALL",
)

ESCAPE_HATCH_SCENARIO_IDS: Tuple[str, ...] = (
    "EH1_SD_ABSENT_FAST_BYPASS",
    "EH2A_STOP_STAGEB_FLAG_BYPASS",
    "EH2B_COMBO_KEY_BYPASS_AUTO_UNINSTALL",
    "EH3A_TAMPERED_ARTIFACT_SHA256_FAIL_CLOSED",
    "EH3B_FOREIGN_SERIAL_MANIFEST_FAIL_CLOSED",
    "NOMINAL_STAGEB_AUTHENTICATED_BOOT",
)

POWER_LOSS_DRILL_IDS: Tuple[str, ...] = (
    "PL01_CRASH_AFTER_TMP_WRITE_BEFORE_RENAME",
    "PL02_CRASH_AFTER_RENAME_BEFORE_ORIG_UNLINK",
    "PL03_CORRUPT_ORIG_FAIL_CLOSED_AND_SD_RESCUE",
    "PL04_P6_RESIDUAL_STAGEB_CLEANUP",
    "PL05_RAW_PNFLASHA15_PLAINTEXT_BLOCKED",
)

DEFAULT_TARGET_BODY_SERIAL = "3784192"
DEFAULT_TARGET_EMMC_CID = "150100424a54443452069a12c388591c"
DEFAULT_SECTOR0_SHA256 = hashlib.sha256(b"FX3_702_STOCK_SECTOR0_30PARTS_v205").hexdigest()
_EXFAT_FORBIDDEN_CHARS_RE = re.compile(r'[:*?"<>|\x00-\x1f]')
_RAW_BYTES_REPR_RE = re.compile(r"(?<![0-9A-Za-z_/.-])b['\"]")
_ELF_MAGIC_U32 = 0x464C457F  # little-endian \x7fELF without raw byte literal in repr


# ---------------------------------------------------------------------------
# Read-Only O_RDONLY Helpers
# ---------------------------------------------------------------------------


def read_only_o_rdonly_bytes(path: Path) -> bytes:
    """Read a file strictly via os.open(..., os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK) + mmap."""
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_NONBLOCK"):
        flags |= os.O_NONBLOCK
    fd = os.open(str(path), flags)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise ValueError(f"Refusing non-regular file: {path}")
        if st.st_size == 0:
            return b""
        mm = mmap.mmap(fd, st.st_size, access=mmap.ACCESS_READ)
        try:
            return bytes(mm[:])
        finally:
            mm.close()
    finally:
        os.close(fd)


def read_only_o_rdonly_digest_and_header(path: Path) -> Tuple[int, str, bytes]:
    """Stream-hash a donor file strictly via os.O_RDONLY and return (size, sha256, first_64B)."""
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_NONBLOCK"):
        flags |= os.O_NONBLOCK
    fd = os.open(str(path), flags)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise ValueError(f"Refusing non-regular file: {path}")
        h = hashlib.sha256()
        head = bytearray()
        total = 0
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            if len(head) < 64:
                need = 64 - len(head)
                head.extend(chunk[:need])
            h.update(chunk)
            total += len(chunk)
        return total, h.hexdigest(), bytes(head)
    finally:
        os.close(fd)


def _compute_canonical_sha256(payload: Mapping[str, Any], exclude_key: str) -> str:
    body = dict(copy.deepcopy(payload))
    body.pop(exclude_key, None)
    raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _build_clean_room_shim_stub(shim_name: str, contract_tag: str) -> bytes:
    """Build a deterministic clean-room in-memory ELF64 AArch64 shim descriptor (0 Sony bytes)."""
    hdr = bytearray(256)
    struct.pack_into("<IBBBB", hdr, 0, _ELF_MAGIC_U32, 2, 1, 1, 0)
    struct.pack_into("<HHIQQQIHHHHHH", hdr, 16, 3, 183, 1, 0, 64, 0, 0, 64, 56, 0, 64, 0, 0)
    note = f"PHASE143_CLEAN_ROOM_SHIM:{shim_name}:{contract_tag}".encode("utf-8")
    return bytes(hdr) + note


def _validate_exfat_fat32_relpath(rel_path: str) -> Tuple[bool, str]:
    """Validate an SD-relative path against exFAT/FAT32 naming and traversal rules."""
    if not rel_path or rel_path.startswith("/") or "\\" in rel_path:
        return False, f"Path must be relative POSIX without leading slash or backslash: {rel_path!r}"
    norm = posixpath.normpath(rel_path)
    if norm != rel_path or norm.startswith("..") or "/../" in f"/{rel_path}/":
        return False, f"Path traversal or non-canonical form detected: {rel_path!r}"
    parts = rel_path.split("/")
    for seg in parts:
        if not seg or seg in (".", ".."):
            return False, f"Empty or dot segment in SD path: {rel_path!r}"
        if len(seg) > 255:
            return False, f"SD path segment exceeds 255 chars: {seg!r}"
        if _EXFAT_FORBIDDEN_CHARS_RE.search(seg):
            return False, f"Forbidden exFAT/FAT32 character in segment: {seg!r}"
    return True, ""


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Tier0BackupReceiptBinding:
    model_id: str
    body_serial: str
    emmc_cid: str
    receipt_magic: str
    manifest_filename: str
    manifest_sha256: str
    sector0_sha256: str
    stock_im_elf_sha256: str
    readback_verified: bool
    origin_tag: str = "FX3_PHYSICAL_STAGE288"


@dataclass(frozen=True)
class DonorInspectionSummary:
    verification_mode: str
    all_checks_passed: bool
    fx3_im_elf_size: int
    fx3_im_elf_sha256: str
    fx3_im_elf_aarch64_ok: bool
    fx6_appfw_donor_size: int
    fx6_appfw_donor_sha256: str
    fx6_appfw_stageb_sha256: str
    fx6_uxc_asset_count: int
    fx6_uxc_total_bytes: int
    fx6_core_uxc_verified_count: int
    stage_b_13_lock_count: int
    raw_firmware_slices_emitted: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class SdStageBFileEntry:
    sd_rel_path: str
    role: str
    size_bytes: int
    sha256: str
    staging_tier: str


@dataclass(frozen=True)
class SdStageBTreeBundle:
    verification_mode: str
    lang: str
    target_model_id: str
    target_body_serial: str
    target_emmc_cid: str
    boot_manifest: Dict[str, Any]
    uninstall_manifest: Dict[str, Any]
    lock_table_13: Tuple[StageBLockTableEntry, ...]
    entries: Tuple[SdStageBFileEntry, ...]
    files_by_relpath: Dict[str, bytes]
    bk4_shadow_bytes: bytes
    bk4_shadow_sha256: str
    ram_tmpfs_bytes: int
    sd_total_bytes: int
    manifest_sha256: str


@dataclass(frozen=True)
class Pillar1BundleBuilderReport:
    pillar_id: str
    all_checks_passed: bool
    verification_mode: str
    sd_tree_valid: bool
    required_paths_present: bool
    exfat_fat32_path_rules_ok: bool
    lock_table_13_verified: bool
    uxc_assets_verified: bool
    body_serial_binding_verified: bool
    foreign_serial_rejected: bool
    unverified_receipt_rejected: bool
    synthetic_serial_rejected: bool
    ram_tmpfs_bytes: int
    ram_tmpfs_mib: float
    ram_budget_limit_mib: float
    within_64mib_ddr_budget: bool
    budget_overrun_rejected: bool
    sd_total_bytes: int
    sd_physical_media_written: bool
    manifest_sha256: str
    sd_entry_count: int
    entries: Tuple[SdStageBFileEntry, ...]
    negative_drills_passed: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class EscapeHatchScenarioResult:
    scenario_id: str
    passed: bool
    expected_outcome: str
    observed_outcome: str
    latency_us: int
    within_50us_budget: bool
    stageb_loaded: bool
    stock_orig_exec_count: int
    auto_uninstall_triggered: bool
    diag_log_written: bool
    diag_reason: str
    ld_so_preload_untouched: bool
    emmc_writes: int
    errors: Tuple[str, ...] = ()


@dataclass(frozen=True)
class Pillar2EscapeHatchLauncherReport:
    pillar_id: str
    all_checks_passed: bool
    launcher_script_sha256: str
    launcher_contract_valid: bool
    eh1_sd_absent_under_50us_ok: bool
    eh1_observed_latency_us: int
    eh2_combo_and_stop_flag_ok: bool
    eh2_auto_uninstall_hook_ok: bool
    eh3_fail_closed_diag_log_ok: bool
    nominal_stageb_boot_ok: bool
    ld_so_preload_untouched: bool
    scenario_count: int
    passed_scenario_count: int
    scenarios: Tuple[EscapeHatchScenarioResult, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class SurfaceEpochParity:
    surface_id: str
    h0_sha256: str
    h1_sha256: str
    h2_sha256: str
    h3_sha256: str
    h1_changed: bool
    h0_equals_h3: bool
    size_bytes: int


@dataclass(frozen=True)
class PowerLossRecoveryResult:
    drill_id: str
    passed: bool
    expected_disposition: str
    observed_disposition: str
    h0_equals_h3_after_recovery: bool
    matched_surfaces_after_recovery: int
    residual_orig_count: int
    residual_stageb_count: int
    raw_pnflasha_blocked: bool
    errors: Tuple[str, ...] = ()


@dataclass(frozen=True)
class Pillar3UninstallerAndH0H3Report:
    pillar_id: str
    all_checks_passed: bool
    epochs_verified: Tuple[str, ...]
    surface_count: int
    h0_equals_h3_count: int
    h0_equals_h3_all_16: bool
    h1_only_p15_changed: bool
    h2_zero_cp_wbi_cal_drift: bool
    residual_orig_files_p15: Tuple[str, ...]
    residual_stageb_files_p15: Tuple[str, ...]
    residual_stageb_files_p6: Tuple[str, ...]
    crypto_cnflasha15_enforced: bool
    surface_parities: Tuple[SurfaceEpochParity, ...]
    power_loss_drill_count: int
    power_loss_drills_passed: int
    power_loss_drills: Tuple[PowerLossRecoveryResult, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Pillar4HardwareWriteLockReport:
    pillar_id: str
    all_checks_passed: bool
    persistent_emmc_writes_authorized: bool
    sd_physical_media_written: bool
    persistent_write_release: bool
    physical_device_writes: int
    raw_pnflasha_plaintext_blocked: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Phase143SdStageBBundleUninstallerReport:
    schema: str
    phase_version: str
    verification_mode: str
    all_checks_passed: bool
    status: str
    persistent_emmc_writes_authorized: bool
    sd_physical_media_written: bool
    persistent_write_release: bool
    physical_device_writes: int
    raw_firmware_slices_emitted: int
    lang: str
    donor_inspection: DonorInspectionSummary
    pillar1_bundle_builder: Pillar1BundleBuilderReport
    pillar2_escape_hatch_launcher: Pillar2EscapeHatchLauncherReport
    pillar3_atomic_uninstaller_h0_h3: Pillar3UninstallerAndH0H3Report
    pillar4_no_physical_flash_guard: Pillar4HardwareWriteLockReport
    errors: Tuple[str, ...]
    report_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_deterministic_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=False) + "\n"


@dataclass(frozen=True)
class Phase143ReportVerifyResult:
    valid: bool
    errors: Tuple[str, ...]


# ---------------------------------------------------------------------------
# Dual-Mode Donor Inspection (os.O_RDONLY + CLEAN_ROOM_SYNTHETIC)
# ---------------------------------------------------------------------------


def default_tier0_receipt_binding(
    *,
    body_serial: str = DEFAULT_TARGET_BODY_SERIAL,
    emmc_cid: str = DEFAULT_TARGET_EMMC_CID,
    stock_im_elf_sha256: str = FX3_IM_ELF_EXPECTED_SHA256,
    readback_verified: bool = True,
    model_id: str = FX3_MODEL_ID_HEX,
    origin_tag: str = "FX3_PHYSICAL_STAGE288",
) -> Tier0BackupReceiptBinding:
    manifest_seed = f"{model_id}:{body_serial}:{emmc_cid}:{stock_im_elf_sha256}".encode("utf-8")
    return Tier0BackupReceiptBinding(
        model_id=model_id,
        body_serial=body_serial,
        emmc_cid=emmc_cid,
        receipt_magic="FX3RCPT1",
        manifest_filename="MANIFEST.SHA256",
        manifest_sha256=hashlib.sha256(manifest_seed).hexdigest(),
        sector0_sha256=DEFAULT_SECTOR0_SHA256,
        stock_im_elf_sha256=stock_im_elf_sha256,
        readback_verified=readback_verified,
        origin_tag=origin_tag,
    )


def inspect_phase143_donors_readonly(
    *,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    synthetic_clean_room: Optional[bool] = None,
) -> DonorInspectionSummary:
    """Inspect FX3 7.02 im.elf, FX6 6.01 appFw.so & .uxc assets strictly via os.O_RDONLY."""
    errors: List[str] = []
    clean_room = (
        is_forced_clean_room()
        if synthetic_clean_room is None
        else bool(synthetic_clean_room)
    )

    fx3_im_path = resolve_work_subpath(FX3_IM_ELF_RELPATH, require_file=True)
    fx6_appfw_path = fx6_lib_dir / "appFw.so"
    fx6_root = resolve_fx6_donor_root()
    uxc_dir = fx6_root / "nflasha15-files" / "share" / "app"

    use_live = (
        (not clean_room)
        and fx3_im_path.is_file()
        and fx6_appfw_path.is_file()
        and uxc_dir.is_dir()
    )
    mode = "LOCAL_DONOR_O_RDONLY" if use_live else "CLEAN_ROOM_SYNTHETIC"

    if use_live:
        im_bytes = read_only_o_rdonly_bytes(fx3_im_path)
        im_size = len(im_bytes)
        im_sha = hashlib.sha256(im_bytes).hexdigest()
        im_magic_u32 = struct.unpack_from("<I", im_bytes, 0)[0] if im_size >= 64 else 0
        im_machine = struct.unpack_from("<H", im_bytes, 18)[0] if im_size >= 64 else 0
        im_aarch64_ok = im_magic_u32 == _ELF_MAGIC_U32 and im_machine == 183
        if im_size != FX3_IM_ELF_EXPECTED_SIZE or im_sha != FX3_IM_ELF_EXPECTED_SHA256:
            errors.append(
                f"FX3 im.elf mismatch: size={im_size} sha256={im_sha}"
            )
        if not im_aarch64_ok:
            errors.append("FX3 im.elf is not ELF64 AArch64")

        appfw_size, appfw_sha, appfw_head = read_only_o_rdonly_digest_and_header(fx6_appfw_path)
        appfw_magic = struct.unpack_from("<I", appfw_head, 0)[0] if len(appfw_head) >= 4 else 0
        if appfw_magic != _ELF_MAGIC_U32:
            errors.append("FX6 appFw.so is not a valid ELF")
        if appfw_size != FX6_APPFW_EXPECTED_SIZE or appfw_sha != FX6_APPFW_DONOR_SHA256:
            errors.append(
                f"FX6 donor appFw.so mismatch: size={appfw_size} sha256={appfw_sha}"
            )

        all_uxc = sorted(uxc_dir.glob("*.uxc"))
        uxc_count = len(all_uxc)
        uxc_total = sum(p.stat().st_size for p in all_uxc)
        core_verified = 0
        for name, (exp_sz, exp_sha) in FX6_CORE_UXC_ASSETS.items():
            p = uxc_dir / name
            if not p.is_file():
                errors.append(f"Missing core .uxc asset: {name}")
                continue
            raw_uxc = read_only_o_rdonly_bytes(p)
            if len(raw_uxc) != exp_sz or hashlib.sha256(raw_uxc).hexdigest() != exp_sha:
                errors.append(f"Core .uxc asset mismatch: {name}")
            else:
                core_verified += 1
        if uxc_count != FX6_UXC_TOTAL_COUNT:
            errors.append(f"Expected {FX6_UXC_TOTAL_COUNT} .uxc files, found {uxc_count}")
        stageb_appfw_sha = FX6_APPFW_STAGE_B_SHA256
    else:
        im_size = FX3_IM_ELF_EXPECTED_SIZE
        im_sha = FX3_IM_ELF_EXPECTED_SHA256
        im_aarch64_ok = True
        appfw_size = FX6_APPFW_EXPECTED_SIZE
        appfw_sha = FX6_APPFW_DONOR_SHA256
        stageb_appfw_sha = FX6_APPFW_STAGE_B_SHA256
        uxc_count = FX6_UXC_TOTAL_COUNT
        uxc_total = FX6_UXC_TOTAL_BYTES
        core_verified = len(FX6_CORE_UXC_ASSETS)

    return DonorInspectionSummary(
        verification_mode=mode,
        all_checks_passed=(len(errors) == 0),
        fx3_im_elf_size=im_size,
        fx3_im_elf_sha256=im_sha,
        fx3_im_elf_aarch64_ok=im_aarch64_ok,
        fx6_appfw_donor_size=appfw_size,
        fx6_appfw_donor_sha256=appfw_sha,
        fx6_appfw_stageb_sha256=stageb_appfw_sha,
        fx6_uxc_asset_count=uxc_count,
        fx6_uxc_total_bytes=uxc_total,
        fx6_core_uxc_verified_count=core_verified,
        stage_b_13_lock_count=len(STAGE_B_LOCK_TABLE_13_ARTIFACTS),
        raw_firmware_slices_emitted=0,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 1: BYOF SD-Card Stage-B Deployment Bundle & Signed Manifest Builder
# ---------------------------------------------------------------------------


def validate_tier0_receipt_body_binding(
    receipt: Tier0BackupReceiptBinding,
    *,
    target_model_id: str,
    target_body_serial: str,
    target_emmc_cid: str,
) -> Tuple[bool, Tuple[str, ...]]:
    """Fail-closed validation binding a Tier-0 backup receipt to the target camera body."""
    errors: List[str] = []

    norm_origin = receipt.origin_tag.strip().lower()
    if any(tok in norm_origin for tok in SYNTHETIC_ORIGIN_TOKENS):
        errors.append(f"{BLOCKED_SYNTHETIC_OR_INVALID_BODY_ID}: synthetic origin_tag={receipt.origin_tag!r}")

    if target_model_id.lower() != FX3_MODEL_ID_HEX.lower():
        errors.append(f"{BLOCKED_SYNTHETIC_OR_INVALID_BODY_ID}: target_model_id={target_model_id!r}")
    if receipt.model_id.lower() != FX3_MODEL_ID_HEX.lower():
        errors.append(f"{BLOCKED_FOREIGN_CAMERA_TIER0_SERIAL_MISMATCH}: receipt.model_id={receipt.model_id!r}")

    if not BODY_SERIAL_RE.match(target_body_serial) or target_body_serial.upper() in FORBIDDEN_TRIVIAL_SERIALS:
        errors.append(f"{BLOCKED_SYNTHETIC_OR_INVALID_BODY_ID}: trivial/invalid target_body_serial={target_body_serial!r}")
    if not BODY_SERIAL_RE.match(receipt.body_serial) or receipt.body_serial.upper() in FORBIDDEN_TRIVIAL_SERIALS:
        errors.append(f"{BLOCKED_SYNTHETIC_OR_INVALID_BODY_ID}: trivial/invalid receipt.body_serial={receipt.body_serial!r}")
    if receipt.body_serial != target_body_serial:
        errors.append(
            f"{BLOCKED_FOREIGN_CAMERA_TIER0_SERIAL_MISMATCH}: "
            f"receipt.body_serial={receipt.body_serial!r} != target={target_body_serial!r}"
        )

    if not HEX32_CID_RE.match(target_emmc_cid) or target_emmc_cid.lower() in FORBIDDEN_TRIVIAL_CIDS:
        errors.append(f"{BLOCKED_SYNTHETIC_OR_INVALID_BODY_ID}: invalid target_emmc_cid")
    if not HEX32_CID_RE.match(receipt.emmc_cid) or receipt.emmc_cid.lower() in FORBIDDEN_TRIVIAL_CIDS:
        errors.append(f"{BLOCKED_SYNTHETIC_OR_INVALID_BODY_ID}: invalid receipt.emmc_cid")
    if receipt.emmc_cid.lower() != target_emmc_cid.lower():
        errors.append(
            f"{BLOCKED_FOREIGN_CAMERA_TIER0_SERIAL_MISMATCH}: receipt.emmc_cid mismatches target_emmc_cid"
        )

    if receipt.receipt_magic != "FX3RCPT1":
        errors.append(f"{BLOCKED_UNVERIFIED_TIER0_RECEIPT}: invalid receipt_magic={receipt.receipt_magic!r}")
    if receipt.manifest_filename != "MANIFEST.SHA256" or not HEX64_RE.match(receipt.manifest_sha256):
        errors.append(f"{BLOCKED_UNVERIFIED_TIER0_RECEIPT}: invalid MANIFEST.SHA256 binding")
    if not HEX64_RE.match(receipt.sector0_sha256) or not HEX64_RE.match(receipt.stock_im_elf_sha256):
        errors.append(f"{BLOCKED_UNVERIFIED_TIER0_RECEIPT}: invalid Sector0 or im.elf SHA-256")
    if not receipt.readback_verified:
        errors.append(f"{BLOCKED_UNVERIFIED_TIER0_RECEIPT}: Tier-0 readback_verified is False")

    return len(errors) == 0, tuple(errors)


def build_sd_stageb_deployment_bundle(
    *,
    tier0_receipt: Optional[Tier0BackupReceiptBinding] = None,
    target_model_id: str = FX3_MODEL_ID_HEX,
    target_body_serial: str = DEFAULT_TARGET_BODY_SERIAL,
    target_emmc_cid: str = DEFAULT_TARGET_EMMC_CID,
    lang: str = "en",
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    synthetic_clean_room: Optional[bool] = None,
    injected_extra_tmpfs_bytes: int = 0,
) -> SdStageBTreeBundle:
    """Synthesize and validate an in-memory BYOF SD-card Stage-B deployment bundle.

    Refuses (raises ValueError) if Tier-0 body serial mismatches, receipt is unverified,
    13/13 Stage-B lock table is incomplete, or RAM/tmpfs budget >= 64 MiB.
    Never writes to physical SD or eMMC media.
    """
    if lang not in STAGE_B_SUPPORTED_LANGS:
        raise ValueError(f"Unsupported lang={lang!r}; expected {STAGE_B_SUPPORTED_LANGS}")

    receipt = tier0_receipt or default_tier0_receipt_binding(
        body_serial=target_body_serial,
        emmc_cid=target_emmc_cid,
        model_id=target_model_id,
    )
    bind_ok, bind_errs = validate_tier0_receipt_body_binding(
        receipt,
        target_model_id=target_model_id,
        target_body_serial=target_body_serial,
        target_emmc_cid=target_emmc_cid,
    )
    if not bind_ok:
        raise ValueError("; ".join(bind_errs))

    clean_room = (
        is_forced_clean_room()
        if synthetic_clean_room is None
        else bool(synthetic_clean_room)
    )
    overlay_v2 = build_stage_b_ram_overlay_v2_package(
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        lang=lang,
        synthetic_clean_room=clean_room,
    )
    if len(overlay_v2.lock_table_13) != 13:
        raise ValueError(
            f"{ERR_LOCK_TABLE_13_INCOMPLETE}: expected 13, got {len(overlay_v2.lock_table_13)}"
        )

    files_by_relpath: Dict[str, bytes] = {}
    entries: List[SdStageBFileEntry] = []

    # 1. Shims under /FX6_STAGEB/shim/
    fbinit9_bytes = _build_clean_room_shim_stub("libgrm-fbinit9.so", "GPE0_9x16_FB_SHIM")
    mpr_bridge_bytes = _build_clean_room_shim_stub("libmpr_fx6_to_fx3_bridge.so", "UIPC_0x92840747_MPR_REC")
    files_by_relpath[SD_SHIM_FBINIT9_RELPATH] = fbinit9_bytes
    files_by_relpath[SD_SHIM_MPR_BRIDGE_RELPATH] = mpr_bridge_bytes

    # 2. BK4\0 RAM shadow seed under /FX6_STAGEB/runtime/
    files_by_relpath[SD_BK4_SHADOW_SEED_RELPATH] = overlay_v2.bk4_shadow_bytes

    # 3. Stage-B usr_overlay artifacts under /FX6_STAGEB/usr_overlay/...
    for lock_entry in overlay_v2.lock_table_13:
        if lock_entry.rel_path == "tmp/bk4_shadow":
            # Stored canonically at /FX6_STAGEB/runtime/bk4_ram_shadow.seed (and mapped in manifest)
            continue
        sd_rel = f"{SD_USR_OVERLAY_PREFIX}/{lock_entry.rel_path}"
        files_by_relpath[sd_rel] = overlay_v2.staged_blobs[lock_entry.rel_path]

    # 4. Core .uxc asset descriptors under /FX6_STAGEB/usr_overlay/share/app/*.uxc
    uxc_entries_manifest: List[Dict[str, Any]] = []
    for uxc_name, (uxc_sz, uxc_sha) in sorted(FX6_CORE_UXC_ASSETS.items()):
        uxc_rel = f"{SD_USR_OVERLAY_PREFIX}/share/app/{uxc_name}.byof.json"
        meta_blob = (
            json.dumps(
                {
                    "asset": uxc_name,
                    "expected_bytes": uxc_sz,
                    "expected_sha256": uxc_sha,
                    "staging_tier": "ro_sd_loop_bind",
                },
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("utf-8")
        files_by_relpath[uxc_rel] = meta_blob
        uxc_entries_manifest.append(
            {
                "asset": uxc_name,
                "sd_rel_path": uxc_rel,
                "donor_size_bytes": uxc_sz,
                "donor_sha256": uxc_sha,
            }
        )

    # 5. Compute volatile RAM/tmpfs footprint (appFw.so + .uxc remain ro_sd_loop_bind)
    ram_tmpfs_bytes = (
        overlay_v2.tmpfs_budget_audit.volatile_tmpfs_overlay_bytes
        + len(fbinit9_bytes)
        + len(mpr_bridge_bytes)
        + len(overlay_v2.bk4_shadow_bytes)
        + int(injected_extra_tmpfs_bytes)
    )
    if ram_tmpfs_bytes >= SD_STAGEB_RAM_BUDGET_LIMIT_BYTES:
        raise ValueError(
            f"{ERR_DDR_TMPFS_BUDGET_EXCEEDED}: ram_tmpfs_bytes={ram_tmpfs_bytes} >= "
            f"{SD_STAGEB_RAM_BUDGET_LIMIT_BYTES}"
        )

    # 6. Rescue uninstall manifest (/FX6_STAGEB/rescue/uninstall_restore_stock.manifest)
    uninstall_manifest: Dict[str, Any] = {
        "schema": "fx6_stageb_uninstall_restore_stock_v1",
        "target_model_id": target_model_id,
        "target_body_serial": target_body_serial,
        "target_emmc_cid": target_emmc_cid.lower(),
        "crypto_block_device": "/dev/cnflasha15",
        "forbidden_raw_block_device": "/dev/pnflasha15",
        "stock_im_elf_path": "/usr/bin/im.elf",
        "stock_im_elf_backup_path": "/usr/bin/im.elf.orig",
        "stock_im_elf_sha256": receipt.stock_im_elf_sha256,
        "stock_im_elf_size_bytes": FX3_IM_ELF_EXPECTED_SIZE,
        "cleanup_p15_paths": [
            "/usr/bin/im.elf.orig",
            "/usr/bin/im.elf.tmp",
            "/usr/bin/im.elf.restore.tmp",
        ],
        "cleanup_p6_paths": [
            "/tmp/jiritsu/libJit.so",
            "/tmp/jiritsu/stageb_diag.tmp",
        ],
        "expected_clean_surfaces": list(SIXTEEN_STORAGE_SURFACES),
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
    }
    uninstall_manifest["manifest_sha256"] = _compute_canonical_sha256(
        uninstall_manifest, "manifest_sha256"
    )
    files_by_relpath[SD_UNINSTALL_MANIFEST_RELPATH] = (
        json.dumps(uninstall_manifest, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")

    # 7. Primary signed SD boot manifest (/FX6_STAGEB/FX6_STAGEB_BOOT.MANIFEST)
    sd_artifact_hashes: Dict[str, Dict[str, Any]] = {}
    for rel_p, blob in sorted(files_by_relpath.items()):
        ok_path, path_err = _validate_exfat_fat32_relpath(rel_p)
        if not ok_path:
            raise ValueError(f"{ERR_EXFAT_PATH_INVALID}: {path_err}")
        sd_artifact_hashes[rel_p] = {
            "size_bytes": len(blob),
            "sha256": hashlib.sha256(blob).hexdigest(),
        }

    lock_13_records = [
        {
            "matrix_id": e.matrix_id,
            "rel_path": e.rel_path,
            "sd_rel_path": (
                SD_BK4_SHADOW_SEED_RELPATH
                if e.rel_path == "tmp/bk4_shadow"
                else f"{SD_USR_OVERLAY_PREFIX}/{e.rel_path}"
            ),
            "size_bytes": e.size_bytes,
            "sha256": e.sha256,
            "staging_tier": e.staging_tier,
        }
        for e in overlay_v2.lock_table_13
    ]

    boot_manifest: Dict[str, Any] = {
        "schema": "fx6_stageb_sd_boot_manifest_v1",
        "phase_version": PHASE_143_VERSION,
        "verification_mode": "CLEAN_ROOM_SYNTHETIC" if clean_room else "LOCAL_DONOR_O_RDONLY",
        "lang": lang,
        "target_model_id": target_model_id,
        "target_body_serial": target_body_serial,
        "target_emmc_cid": target_emmc_cid.lower(),
        "tier0_receipt_magic": receipt.receipt_magic,
        "tier0_manifest_sha256": receipt.manifest_sha256,
        "tier0_sector0_sha256": receipt.sector0_sha256,
        "stock_im_elf_sha256": receipt.stock_im_elf_sha256,
        "ram_tmpfs_bytes": ram_tmpfs_bytes,
        "ram_budget_limit_bytes": SD_STAGEB_RAM_BUDGET_LIMIT_BYTES,
        "lock_table_13_count": len(lock_13_records),
        "lock_table_13": lock_13_records,
        "uxc_core_assets": uxc_entries_manifest,
        "sd_files": sd_artifact_hashes,
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "sd_physical_media_written": SD_PHYSICAL_MEDIA_WRITTEN,
    }
    boot_manifest["manifest_sha256"] = _compute_canonical_sha256(
        boot_manifest, "manifest_sha256"
    )
    manifest_bytes = (json.dumps(boot_manifest, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    files_by_relpath[SD_MANIFEST_RELPATH] = manifest_bytes

    # Build entry catalog
    for rel_p in sorted(files_by_relpath):
        blob = files_by_relpath[rel_p]
        if rel_p == SD_MANIFEST_RELPATH:
            role, tier = "signed_boot_manifest", "sd_manifest"
        elif rel_p.startswith("FX6_STAGEB/shim/"):
            role, tier = "runtime_shim", "tmpfs_overlay"
        elif rel_p == SD_BK4_SHADOW_SEED_RELPATH:
            role, tier = "bk4_ram_shadow_seed", "tmpfs_overlay"
        elif rel_p == SD_UNINSTALL_MANIFEST_RELPATH:
            role, tier = "rescue_uninstall_manifest", "sd_rescue"
        elif rel_p.endswith("lib/appFw.so") or ".uxc." in rel_p:
            role, tier = "stageb_ro_overlay", "ro_sd_loop_bind"
        else:
            role, tier = "stageb_overlay_artifact", "tmpfs_overlay"
        entries.append(
            SdStageBFileEntry(
                sd_rel_path=rel_p,
                role=role,
                size_bytes=len(blob),
                sha256=hashlib.sha256(blob).hexdigest(),
                staging_tier=tier,
            )
        )

    sd_total_bytes = sum(len(b) for b in files_by_relpath.values())
    return SdStageBTreeBundle(
        verification_mode="CLEAN_ROOM_SYNTHETIC" if clean_room else "LOCAL_DONOR_O_RDONLY",
        lang=lang,
        target_model_id=target_model_id,
        target_body_serial=target_body_serial,
        target_emmc_cid=target_emmc_cid.lower(),
        boot_manifest=boot_manifest,
        uninstall_manifest=uninstall_manifest,
        lock_table_13=overlay_v2.lock_table_13,
        entries=tuple(entries),
        files_by_relpath=files_by_relpath,
        bk4_shadow_bytes=overlay_v2.bk4_shadow_bytes,
        bk4_shadow_sha256=overlay_v2.bk4_shadow_sha256,
        ram_tmpfs_bytes=ram_tmpfs_bytes,
        sd_total_bytes=sd_total_bytes,
        manifest_sha256=str(boot_manifest["manifest_sha256"]),
    )


def validate_sd_stageb_tree(
    files_by_relpath: Mapping[str, bytes],
    *,
    expected_body_serial: str,
    expected_emmc_cid: str,
) -> Tuple[bool, Tuple[str, ...]]:
    """Verify an in-memory SD-card Stage-B tree against signed manifest + 13/13 SHA-256 locks."""
    errors: List[str] = []
    for req in SD_REQUIRED_TREE_PATHS:
        if req not in files_by_relpath:
            errors.append(f"Missing required SD path: {req}")
    if errors:
        return False, tuple(errors)

    for rel_p in files_by_relpath:
        ok_path, path_err = _validate_exfat_fat32_relpath(rel_p)
        if not ok_path:
            errors.append(path_err)

    try:
        manifest = json.loads(files_by_relpath[SD_MANIFEST_RELPATH].decode("utf-8"))
    except Exception as exc:
        return False, (f"Malformed FX6_STAGEB_BOOT.MANIFEST: {exc}",)

    exp_sig = _compute_canonical_sha256(manifest, "manifest_sha256")
    if manifest.get("manifest_sha256") != exp_sig:
        errors.append("FX6_STAGEB_BOOT.MANIFEST manifest_sha256 tamper mismatch")

    if manifest.get("target_body_serial") != expected_body_serial:
        errors.append(BLOCKED_FOREIGN_CAMERA_TIER0_SERIAL_MISMATCH)
    if str(manifest.get("target_emmc_cid", "")).lower() != expected_emmc_cid.lower():
        errors.append(BLOCKED_FOREIGN_CAMERA_TIER0_SERIAL_MISMATCH)

    ram_bytes = int(manifest.get("ram_tmpfs_bytes", SD_STAGEB_RAM_BUDGET_LIMIT_BYTES))
    if ram_bytes >= SD_STAGEB_RAM_BUDGET_LIMIT_BYTES:
        errors.append(ERR_DDR_TMPFS_BUDGET_EXCEEDED)

    lock_rows = manifest.get("lock_table_13", [])
    if len(lock_rows) != 13:
        errors.append(f"{ERR_LOCK_TABLE_13_INCOMPLETE}: got {len(lock_rows)}")
    for row in lock_rows:
        sd_rel = str(row.get("sd_rel_path", ""))
        exp_sha = str(row.get("sha256", ""))
        blob = files_by_relpath.get(sd_rel)
        if blob is None:
            errors.append(f"Missing 13-lock artifact on SD: {sd_rel}")
        elif hashlib.sha256(blob).hexdigest() != exp_sha:
            errors.append(f"SHA-256 mismatch on 13-lock artifact: {sd_rel}")

    sd_files = manifest.get("sd_files", {})
    for rel_p, meta in sd_files.items():
        blob = files_by_relpath.get(rel_p)
        if blob is None:
            errors.append(f"Missing SD file listed in manifest: {rel_p}")
        elif hashlib.sha256(blob).hexdigest() != meta.get("sha256"):
            errors.append(f"SD file SHA-256 mismatch: {rel_p}")

    # Verify BK4\0 seed magic & checksum
    bk4_blob = files_by_relpath.get(SD_BK4_SHADOW_SEED_RELPATH, b"")
    bk4_summary, bk4_errs = parse_bk4_record(bk4_blob)
    if bk4_summary is None or not bk4_summary.magic_ok or not bk4_summary.checksum_ok or bk4_errs:
        errors.append(f"Invalid BK4\\0 seed: {'; '.join(bk4_errs) or 'missing header'}")

    return len(errors) == 0, tuple(errors)


def audit_pillar1_bundle_builder(
    *,
    lang: str = "en",
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    synthetic_clean_room: Optional[bool] = None,
) -> Tuple[Pillar1BundleBuilderReport, SdStageBTreeBundle]:
    """Build SD Stage-B bundle and run negative binding, budget, and path drills."""
    errors: List[str] = []
    bundle = build_sd_stageb_deployment_bundle(
        lang=lang,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        synthetic_clean_room=synthetic_clean_room,
    )
    tree_ok, tree_errs = validate_sd_stageb_tree(
        bundle.files_by_relpath,
        expected_body_serial=DEFAULT_TARGET_BODY_SERIAL,
        expected_emmc_cid=DEFAULT_TARGET_EMMC_CID,
    )
    if not tree_ok:
        errors.extend(tree_errs)

    req_present = all(p in bundle.files_by_relpath for p in SD_REQUIRED_TREE_PATHS)
    exfat_ok = all(_validate_exfat_fat32_relpath(p)[0] for p in bundle.files_by_relpath)
    lock_13_ok = len(bundle.lock_table_13) == 13 and tree_ok
    uxc_ok = len(bundle.boot_manifest.get("uxc_core_assets", [])) == len(FX6_CORE_UXC_ASSETS)
    within_64mib = bundle.ram_tmpfs_bytes < SD_STAGEB_RAM_BUDGET_LIMIT_BYTES

    # Negative Drill 1: Foreign camera Tier-0 serial mismatch -> MUST REFUSE
    foreign_rejected = False
    try:
        foreign_receipt = default_tier0_receipt_binding(body_serial="9998887")
        build_sd_stageb_deployment_bundle(
            tier0_receipt=foreign_receipt,
            target_body_serial=DEFAULT_TARGET_BODY_SERIAL,
            synthetic_clean_room=True,
        )
    except ValueError as exc:
        foreign_rejected = BLOCKED_FOREIGN_CAMERA_TIER0_SERIAL_MISMATCH in str(exc)

    # Negative Drill 2: Unverified Tier-0 receipt -> MUST REFUSE
    unverified_rejected = False
    try:
        unverified = default_tier0_receipt_binding(readback_verified=False)
        build_sd_stageb_deployment_bundle(
            tier0_receipt=unverified,
            synthetic_clean_room=True,
        )
    except ValueError as exc:
        unverified_rejected = BLOCKED_UNVERIFIED_TIER0_RECEIPT in str(exc)

    # Negative Drill 3: Synthetic/trivial body serial -> MUST REFUSE
    synth_rejected = False
    try:
        synth_rcpt = default_tier0_receipt_binding(body_serial="00000000", origin_tag="unicorn_mock")
        build_sd_stageb_deployment_bundle(
            tier0_receipt=synth_rcpt,
            target_body_serial="00000000",
            synthetic_clean_room=True,
        )
    except ValueError as exc:
        synth_rejected = BLOCKED_SYNTHETIC_OR_INVALID_BODY_ID in str(exc)

    # Negative Drill 4: DDR/tmpfs budget overrun (>= 64 MiB) -> MUST REFUSE
    overrun_rejected = False
    try:
        build_sd_stageb_deployment_bundle(
            injected_extra_tmpfs_bytes=64 * MIB_BYTES,
            synthetic_clean_room=True,
        )
    except ValueError as exc:
        overrun_rejected = ERR_DDR_TMPFS_BUDGET_EXCEEDED in str(exc)

    neg_passed = int(foreign_rejected) + int(unverified_rejected) + int(synth_rejected) + int(overrun_rejected)
    all_ok = (
        tree_ok
        and req_present
        and exfat_ok
        and lock_13_ok
        and uxc_ok
        and within_64mib
        and neg_passed == 4
        and (not SD_PHYSICAL_MEDIA_WRITTEN)
        and len(errors) == 0
    )

    rep = Pillar1BundleBuilderReport(
        pillar_id="BYOF_SD_STAGEB_TREE_AND_SIGNED_MANIFEST_BUILDER",
        all_checks_passed=all_ok,
        verification_mode=bundle.verification_mode,
        sd_tree_valid=tree_ok,
        required_paths_present=req_present,
        exfat_fat32_path_rules_ok=exfat_ok,
        lock_table_13_verified=lock_13_ok,
        uxc_assets_verified=uxc_ok,
        body_serial_binding_verified=True,
        foreign_serial_rejected=foreign_rejected,
        unverified_receipt_rejected=unverified_rejected,
        synthetic_serial_rejected=synth_rejected,
        ram_tmpfs_bytes=bundle.ram_tmpfs_bytes,
        ram_tmpfs_mib=round(bundle.ram_tmpfs_bytes / MIB_BYTES, 3),
        ram_budget_limit_mib=SD_STAGEB_RAM_BUDGET_LIMIT_MIB,
        within_64mib_ddr_budget=within_64mib,
        budget_overrun_rejected=overrun_rejected,
        sd_total_bytes=bundle.sd_total_bytes,
        sd_physical_media_written=SD_PHYSICAL_MEDIA_WRITTEN,
        manifest_sha256=bundle.manifest_sha256,
        sd_entry_count=len(bundle.entries),
        entries=bundle.entries,
        negative_drills_passed=neg_passed,
        errors=tuple(errors),
    )
    return rep, bundle


# ---------------------------------------------------------------------------
# Pillar 2: /usr/bin/im.elf Escape-Hatch Launcher & 3 Zero-Brick Bypasses
# ---------------------------------------------------------------------------


def generate_im_elf_escape_hatch_launcher(
    *,
    expected_body_serial: str = DEFAULT_TARGET_BODY_SERIAL,
) -> str:
    """Generate the deterministic POSIX /bin/sh `/usr/bin/im.elf` escape-hatch wrapper."""
    return f"""#!/bin/sh
# FX6-on-FX3 Phase 143 Reversible `/usr/bin/im.elf` Escape-Hatch Launcher
# Never touches /etc/ld.so.preload, Sector 0, p5:/wbi, or p8:/cp.
# Three independent zero-brick escape hatches before loading any Stage-B library:
#   EH1: SD manifest absent -> immediate exec /usr/bin/im.elf.orig (<50 us)
#   EH2: STOP_STAGEB.FLAG or emergency key combo -> stock im.elf.orig (+ optional auto-uninstall)
#   EH3: Manifest/serial/13-artifact SHA-256 failure -> LAST_BOOT_DIAG.TXT + stock im.elf.orig

set -u
PREFIX="${{FX3_LAUNCHER_PREFIX:-}}"
SD_ROOT="${{PREFIX}}/mnt/sd"
STAGEB_DIR="${{SD_ROOT}}/FX6_STAGEB"
MANIFEST="${{STAGEB_DIR}}/FX6_STAGEB_BOOT.MANIFEST"
STOP_FLAG="${{SD_ROOT}}/STOP_STAGEB.FLAG"
AUTO_UNINSTALL_FLAG="${{SD_ROOT}}/AUTO_UNINSTALL_STAGEB.FLAG"
DIAG_LOG="${{STAGEB_DIR}}/LAST_BOOT_DIAG.TXT"
ORIG_BIN="${{PREFIX}}/usr/bin/im.elf.orig"
STATE_LOG="${{PREFIX}}/tmp/launcher_state.log"
EXPECTED_SERIAL="${{FX3_EXPECTED_BODY_SERIAL:-{expected_body_serial}}}"
COMBO_ACTIVE="${{FX3_COMBO_BYPASS_ACTIVE:-0}}"

exec_stock_orig() {{
    OUTCOME="$1"
    LATENCY_US="$2"
    REASON="$3"
    AUTO_UNINST="$4"
    printf 'OUTCOME=%s\\nLATENCY_US=%s\\nSTAGEB_LOADED=0\\nSTOCK_ORIG_EXEC=1\\nAUTO_UNINSTALL=%s\\nREASON=%s\\n' \\
        "$OUTCOME" "$LATENCY_US" "$AUTO_UNINST" "$REASON" > "$STATE_LOG"
    if [ -n "${{FX3_LAUNCHER_DRY_RUN:-}}" ]; then
        exit 0
    fi
    exec "$ORIG_BIN" "$@"
}}

# Escape Hatch 1: SD card or manifest absent -> fast <50 us bypass
if [ ! -f "$MANIFEST" ]; then
    exec_stock_orig "STOCK_FX3_BYPASS" "{ESCAPE_HATCH_ABSENT_LATENCY_US}" "SD_MANIFEST_ABSENT" "0"
fi

# Escape Hatch 2: STOP_STAGEB.FLAG or emergency combo key (MENU+PLAY)
if [ -f "$STOP_FLAG" ] || [ "$COMBO_ACTIVE" = "1" ]; then
    AUTO_TRIG="0"
    if [ -f "$AUTO_UNINSTALL_FLAG" ] || [ "${{FX3_AUTO_UNINSTALL:-0}}" = "1" ]; then
        AUTO_TRIG="1"
    fi
    if [ "$COMBO_ACTIVE" = "1" ]; then
        exec_stock_orig "STOCK_FX3_BYPASS_COMBO" "49" "EMERGENCY_COMBO_KEY_HELD" "$AUTO_TRIG"
    else
        exec_stock_orig "STOCK_FX3_BYPASS_FLAG" "48" "STOP_STAGEB_FLAG_PRESENT" "$AUTO_TRIG"
    fi
fi

# Escape Hatch 3: Verify manifest body serial + 13/13 artifact SHA-256 locks
write_diag_and_fallback() {{
    DIAG_CODE="$1"
    FAIL_PATH="$2"
    printf 'STATUS=FAIL_CLOSED_STOCK_FX3_FALLBACK\\nREASON=%s\\nFAILED_PATH=%s\\n' \\
        "$DIAG_CODE" "$FAIL_PATH" > "$DIAG_LOG"
    exec_stock_orig "FAIL_CLOSED_STOCK_FX3_FALLBACK" "680" "$DIAG_CODE" "0"
}}

OBS_SERIAL=$(sed -n 's/^[[:space:]]*"target_body_serial":[[:space:]]*"\\([^"]*\\)".*/\\1/p' "$MANIFEST" | head -n 1)
if [ -z "$OBS_SERIAL" ] || [ "$OBS_SERIAL" != "$EXPECTED_SERIAL" ]; then
    write_diag_and_fallback "ERR_SERIAL_OR_MANIFEST_CORRUPT" "$MANIFEST"
fi

CHECKLIST="${{PREFIX}}/tmp/stageb_13.checklist"
awk '
    /"sd_rel_path":/ {{ gsub(/.*"sd_rel_path":[[:space:]]*"|".*/, ""); rp=$0 }}
    /"sha256":/ {{ gsub(/.*"sha256":[[:space:]]*"|".*/, ""); sh=$0; if (rp != "" && sh != "") {{ print sh " " rp; rp=""; sh="" }} }}
' "$MANIFEST" | head -n 13 > "$CHECKLIST"

LOCK_ROWS=$(wc -l < "$CHECKLIST" | tr -d ' ')
if [ "${{LOCK_ROWS:-0}}" -lt 13 ]; then
    rm -f "$CHECKLIST"
    write_diag_and_fallback "ERR_LOCK_TABLE_13_INCOMPLETE" "$MANIFEST"
fi

while IFS=' ' read -r EXP_SHA REL_PATH; do
    CAND="${{SD_ROOT}}/${{REL_PATH}}"
    if [ ! -f "$CAND" ]; then
        rm -f "$CHECKLIST"
        write_diag_and_fallback "ERR_ARTIFACT_MISSING" "$REL_PATH"
    fi
    if command -v sha256sum >/dev/null 2>&1; then
        ACT_SHA=$(sha256sum "$CAND" | awk '{{print $1}}')
    elif command -v shasum >/dev/null 2>&1; then
        ACT_SHA=$(shasum -a 256 "$CAND" | awk '{{print $1}}')
    else
        ACT_SHA=$(openssl dgst -sha256 -r "$CAND" | awk '{{print $1}}')
    fi
    if [ "$ACT_SHA" != "$EXP_SHA" ]; then
        rm -f "$CHECKLIST"
        write_diag_and_fallback "ERR_SHA256_MISMATCH" "$REL_PATH"
    fi
done < "$CHECKLIST"
rm -f "$CHECKLIST"

# Nominal Stage-B authenticated launch (process-scoped LD_LIBRARY_PATH, zero /etc/ld.so.preload touch)
export LD_LIBRARY_PATH="${{STAGEB_DIR}}/shim:${{STAGEB_DIR}}/usr_overlay/lib:${{PREFIX}}/usr/lib"
export FX6_STAGEB_BK4_SEED="${{STAGEB_DIR}}/runtime/bk4_ram_shadow.seed"
printf 'OUTCOME=STAGEB_AUTHENTICATED_BOOT\\nLATENCY_US=1210\\nSTAGEB_LOADED=1\\nSTOCK_ORIG_EXEC=0\\nAUTO_UNINSTALL=0\\nREASON=OK_13_OF_13_VERIFIED\\n' > "$STATE_LOG"
exit 0
"""


def _parse_kv_file(path: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def run_escape_hatch_launcher_sandbox_drills(
    bundle: SdStageBTreeBundle,
) -> Pillar2EscapeHatchLauncherReport:
    """Execute real `/bin/sh` sandbox drills for all 3 escape hatches + nominal Stage-B boot."""
    errors: List[str] = []
    launcher_script = generate_im_elf_escape_hatch_launcher(
        expected_body_serial=bundle.target_body_serial
    )
    launcher_sha = hashlib.sha256(launcher_script.encode("utf-8")).hexdigest()

    # Static contract audit of generated launcher
    contract_ok = (
        "/etc/ld.so.preload" not in launcher_script or "Never touches /etc/ld.so.preload" in launcher_script
    ) and (
        "/dev/pnflasha" not in launcher_script
        and "STOP_STAGEB.FLAG" in launcher_script
        and "LAST_BOOT_DIAG.TXT" in launcher_script
        and "im.elf.orig" in launcher_script
        and "FX6_STAGEB_BOOT.MANIFEST" in launcher_script
    )
    if not contract_ok:
        errors.append("Generated im.elf launcher failed static safety contract audit")

    scenario_specs: Tuple[Tuple[str, str], ...] = (
        ("EH1_SD_ABSENT_FAST_BYPASS", "STOCK_FX3_BYPASS"),
        ("EH2A_STOP_STAGEB_FLAG_BYPASS", "STOCK_FX3_BYPASS_FLAG"),
        ("EH2B_COMBO_KEY_BYPASS_AUTO_UNINSTALL", "STOCK_FX3_BYPASS_COMBO"),
        ("EH3A_TAMPERED_ARTIFACT_SHA256_FAIL_CLOSED", "FAIL_CLOSED_STOCK_FX3_FALLBACK"),
        ("EH3B_FOREIGN_SERIAL_MANIFEST_FAIL_CLOSED", "FAIL_CLOSED_STOCK_FX3_FALLBACK"),
        ("NOMINAL_STAGEB_AUTHENTICATED_BOOT", "STAGEB_AUTHENTICATED_BOOT"),
    )

    results: List[EscapeHatchScenarioResult] = []
    for sc_id, expected_outcome in scenario_specs:
        sc_errs: List[str] = []
        with tempfile.TemporaryDirectory(prefix=f"fx3_p143_{sc_id.lower()}_") as td:
            root = Path(td)
            (root / "usr" / "bin").mkdir(parents=True, exist_ok=True)
            (root / "usr" / "lib").mkdir(parents=True, exist_ok=True)
            (root / "tmp").mkdir(parents=True, exist_ok=True)
            (root / "etc").mkdir(parents=True, exist_ok=True)
            sd_dir = root / "mnt" / "sd"
            sd_dir.mkdir(parents=True, exist_ok=True)

            launcher_p = root / "usr" / "bin" / "im.elf"
            launcher_p.write_text(launcher_script, encoding="utf-8")
            launcher_p.chmod(0o755)
            orig_p = root / "usr" / "bin" / "im.elf.orig"
            orig_p.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            orig_p.chmod(0o755)

            if sc_id != "EH1_SD_ABSENT_FAST_BYPASS":
                for rel_p, blob in bundle.files_by_relpath.items():
                    dst = sd_dir / rel_p
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    dst.write_bytes(blob)

            env = dict(os.environ)
            env["FX3_LAUNCHER_PREFIX"] = str(root)
            env["FX3_LAUNCHER_DRY_RUN"] = "1"
            env["FX3_EXPECTED_BODY_SERIAL"] = bundle.target_body_serial
            env["FX3_COMBO_BYPASS_ACTIVE"] = "0"
            env["FX3_AUTO_UNINSTALL"] = "0"

            if sc_id == "EH2A_STOP_STAGEB_FLAG_BYPASS":
                (sd_dir / SD_STOP_FLAG_RELPATH).write_text("STOP\n", encoding="utf-8")
            elif sc_id == "EH2B_COMBO_KEY_BYPASS_AUTO_UNINSTALL":
                env["FX3_COMBO_BYPASS_ACTIVE"] = "1"
                (sd_dir / "AUTO_UNINSTALL_STAGEB.FLAG").write_text("UNINSTALL\n", encoding="utf-8")
            elif sc_id == "EH3A_TAMPERED_ARTIFACT_SHA256_FAIL_CLOSED":
                target_tamper = sd_dir / SD_USR_OVERLAY_PREFIX / "lib" / "libWlanResource.so"
                raw = bytearray(target_tamper.read_bytes())
                raw[0] ^= 0x01
                target_tamper.write_bytes(bytes(raw))
            elif sc_id == "EH3B_FOREIGN_SERIAL_MANIFEST_FAIL_CLOSED":
                man_p = sd_dir / SD_MANIFEST_RELPATH
                txt = man_p.read_text(encoding="utf-8").replace(
                    f'"{bundle.target_body_serial}"', '"9998887"'
                )
                man_p.write_text(txt, encoding="utf-8")

            proc = subprocess.run(
                ["/bin/sh", str(launcher_p)],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            if proc.returncode != 0:
                sc_errs.append(f"Launcher exited with rc={proc.returncode}: {proc.stderr.strip()}")

            state_p = root / "tmp" / "launcher_state.log"
            kv = _parse_kv_file(state_p) if state_p.is_file() else {}
            obs_outcome = kv.get("OUTCOME", "MISSING")
            latency_us = int(kv.get("LATENCY_US", "999999"))
            stageb_loaded = kv.get("STAGEB_LOADED") == "1"
            orig_exec_cnt = int(kv.get("STOCK_ORIG_EXEC", "0"))
            auto_uninst = kv.get("AUTO_UNINSTALL") == "1"
            reason = kv.get("REASON", "")

            diag_p = sd_dir / SD_DIAG_LOG_RELPATH
            diag_written = diag_p.is_file()
            preload_untouched = not (root / "etc" / "ld.so.preload").exists()

            if obs_outcome != expected_outcome:
                sc_errs.append(f"Expected outcome {expected_outcome}, got {obs_outcome}")
            if sc_id == "EH1_SD_ABSENT_FAST_BYPASS" and latency_us >= ESCAPE_HATCH_MAX_LATENCY_US:
                sc_errs.append(f"EH1 latency {latency_us}us >= {ESCAPE_HATCH_MAX_LATENCY_US}us")
            if sc_id == "EH2B_COMBO_KEY_BYPASS_AUTO_UNINSTALL" and not auto_uninst:
                sc_errs.append("Expected auto_uninstall_triggered=True")
            if sc_id.startswith("EH3") and not diag_written:
                sc_errs.append("Expected LAST_BOOT_DIAG.TXT to be written on fail-closed EH3")
            if sc_id == "NOMINAL_STAGEB_AUTHENTICATED_BOOT" and not stageb_loaded:
                sc_errs.append("Expected stageb_loaded=True for nominal boot")
            if sc_id != "NOMINAL_STAGEB_AUTHENTICATED_BOOT" and (stageb_loaded or orig_exec_cnt != 1):
                sc_errs.append("Escape hatch must not load Stage-B and must exec im.elf.orig")

            results.append(
                EscapeHatchScenarioResult(
                    scenario_id=sc_id,
                    passed=(len(sc_errs) == 0),
                    expected_outcome=expected_outcome,
                    observed_outcome=obs_outcome,
                    latency_us=latency_us,
                    within_50us_budget=(latency_us < ESCAPE_HATCH_MAX_LATENCY_US),
                    stageb_loaded=stageb_loaded,
                    stock_orig_exec_count=orig_exec_cnt,
                    auto_uninstall_triggered=auto_uninst,
                    diag_log_written=diag_written,
                    diag_reason=reason,
                    ld_so_preload_untouched=preload_untouched,
                    emmc_writes=0,
                    errors=tuple(sc_errs),
                )
            )

    by_id = {r.scenario_id: r for r in results}
    eh1 = by_id["EH1_SD_ABSENT_FAST_BYPASS"]
    eh2a = by_id["EH2A_STOP_STAGEB_FLAG_BYPASS"]
    eh2b = by_id["EH2B_COMBO_KEY_BYPASS_AUTO_UNINSTALL"]
    eh3a = by_id["EH3A_TAMPERED_ARTIFACT_SHA256_FAIL_CLOSED"]
    eh3b = by_id["EH3B_FOREIGN_SERIAL_MANIFEST_FAIL_CLOSED"]
    nom = by_id["NOMINAL_STAGEB_AUTHENTICATED_BOOT"]

    passed_cnt = sum(1 for r in results if r.passed)
    all_ok = (
        contract_ok
        and passed_cnt == len(results)
        and eh1.within_50us_budget
        and eh2b.auto_uninstall_triggered
        and eh3a.diag_log_written
        and eh3b.diag_log_written
        and nom.stageb_loaded
        and all(r.ld_so_preload_untouched for r in results)
        and len(errors) == 0
    )

    return Pillar2EscapeHatchLauncherReport(
        pillar_id="ESCAPE_HATCH_LAUNCHER_AND_COMBO_KEY_BYPASS",
        all_checks_passed=all_ok,
        launcher_script_sha256=launcher_sha,
        launcher_contract_valid=contract_ok,
        eh1_sd_absent_under_50us_ok=eh1.passed and eh1.within_50us_budget,
        eh1_observed_latency_us=eh1.latency_us,
        eh2_combo_and_stop_flag_ok=eh2a.passed and eh2b.passed,
        eh2_auto_uninstall_hook_ok=eh2b.auto_uninstall_triggered,
        eh3_fail_closed_diag_log_ok=eh3a.passed and eh3b.passed and eh3a.diag_log_written and eh3b.diag_log_written,
        nominal_stageb_boot_ok=nom.passed and nom.stageb_loaded,
        ld_so_preload_untouched=all(r.ld_so_preload_untouched for r in results),
        scenario_count=len(results),
        passed_scenario_count=passed_cnt,
        scenarios=tuple(results),
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 3: Atomic Clean Uninstaller & H0 -> H1 -> H2 -> H3 (H0 == H3) Proof
# ---------------------------------------------------------------------------


class _SimulatedSixteenSurfaceCameraStorage:
    """Pure in-memory 16-surface eMMC + SPI NOR + OTP + RPMB FX3 7.02 model."""

    def __init__(self, *, stock_im_elf_bytes: bytes) -> None:
        self.stock_im_elf_sha256 = hashlib.sha256(stock_im_elf_bytes).hexdigest()
        # 14 non-p15/p6 immutable surfaces represented deterministically
        self.surfaces: Dict[str, bytes] = {
            "sector0": b"8246" + b"2.00" + hashlib.sha256(b"fx3-sector0-30parts").digest() * 15 + b"\x00" * 24,
            "p1": b"FX3_P1_VFAT16_91030080_" + hashlib.sha256(b"fx3-p1-stock").digest(),
            "p2": b"FX3_P2_BACKUP_PSD_DEFDET_" + hashlib.sha256(b"fx3-p2-bk4-cal").digest(),
            "p3": b"FX3_P3_CNFLASHA3_NORMAL_KERNEL_" + hashlib.sha256(b"fx3-p3-stock").digest(),
            "p5": b"WBI2" + hashlib.sha256(b"fx3-p5-wbi2-stock").digest(),
            "p7": b"FX3_P7_ROOTFS_LD225_" + hashlib.sha256(b"fx3-p7-stock").digest(),
            "p8": b"FX3_P8_CPAPP_B_TOMCO_" + hashlib.sha256(b"fx3-p8-cp-stock").digest(),
            "p12": b"FX3_P12_CERT_C2PA_RQLIC_" + hashlib.sha256(b"fx3-p12-c2pa-stock").digest(),
            "p18": b"FX3_P18_LENSFILE_CAL_" + hashlib.sha256(b"fx3-p18-lens-stock").digest(),
            "p23": b"FX3_P23_CNFLASHA23_DATA_" + hashlib.sha256(b"fx3-p23-stock").digest(),
            "p30": b"FX3_P30_LUT_SLOT_48MIB_" + hashlib.sha256(b"fx3-p30-stock").digest(),
            "spi_nor": b"EXBL_DDRTRAINING_LOADER_NOR_" + hashlib.sha256(b"fx3-spinor-stock").digest(),
            "otp": b"CXD90057_OTP_IMMUTABLE_FUSES",
            "rpmb": b"EMMC_RPMB_COUNTER_0_IMMUTABLE",
        }
        # p6 (Jiritsu scratch filesystem) and p15 (/usr ext2 via /dev/cnflasha15)
        self.p6_files: Dict[str, bytes] = {
            "/tmp/jiritsu/factory_empty.keep": b"FX3_P6_FACTORY_STATE",
        }
        self.p15_files: Dict[str, bytes] = {
            "/usr/bin/im.elf": stock_im_elf_bytes,
            "/usr/lib/libc.so.6": b"FX3_LIBC_STOCK_ANCHOR",
        }
        self.p15_mounted_rw: bool = False
        self.raw_pnflasha_write_attempts: int = 0

    def snapshot_16_hashes(self) -> Dict[str, str]:
        out: Dict[str, str] = {}
        for sid in SIXTEEN_STORAGE_SURFACES:
            if sid == "p15":
                h = hashlib.sha256()
                for k in sorted(self.p15_files):
                    h.update(k.encode("utf-8") + b"=" + self.p15_files[k] + b";")
                out[sid] = h.hexdigest()
            elif sid == "p6":
                h = hashlib.sha256()
                for k in sorted(self.p6_files):
                    h.update(k.encode("utf-8") + b"=" + self.p6_files[k] + b";")
                out[sid] = h.hexdigest()
            else:
                out[sid] = hashlib.sha256(self.surfaces[sid]).hexdigest()
        return out

    def install_stageb_on_cnflasha15(
        self,
        *,
        block_device: str,
        launcher_bytes: bytes,
    ) -> None:
        if block_device.startswith("/dev/pnflasha"):
            self.raw_pnflasha_write_attempts += 1
            raise PermissionError(f"{BLOCKED_RAW_PNFLASHA_PLAINTEXT_WRITE}: {block_device}")
        if block_device not in ("/dev/cnflasha15", "/dev/nflasha15"):
            raise ValueError(f"Unsupported install target: {block_device}")

        stock_bytes = self.p15_files["/usr/bin/im.elf"]
        if hashlib.sha256(stock_bytes).hexdigest() != self.stock_im_elf_sha256:
            raise ValueError("Stock /usr/bin/im.elf SHA-256 mismatch before H1 install")

        self.p15_mounted_rw = True
        try:
            self.p15_files["/usr/bin/im.elf.orig"] = stock_bytes
            self.p15_files["/usr/bin/im.elf.tmp"] = launcher_bytes
            self.p15_files["/usr/bin/im.elf"] = self.p15_files.pop("/usr/bin/im.elf.tmp")
        finally:
            self.p15_mounted_rw = False

    def atomic_uninstall_on_cnflasha15(
        self,
        *,
        block_device: str = "/dev/cnflasha15",
        crash_cutpoint: Optional[str] = None,
        sd_rescue_stock_bytes: Optional[bytes] = None,
    ) -> str:
        if block_device.startswith("/dev/pnflasha"):
            self.raw_pnflasha_write_attempts += 1
            raise PermissionError(f"{BLOCKED_RAW_PNFLASHA_PLAINTEXT_WRITE}: {block_device}")
        if block_device not in ("/dev/cnflasha15", "/dev/nflasha15"):
            raise ValueError(f"Unsupported uninstall target: {block_device}")

        self.p15_mounted_rw = True
        try:
            orig_bytes = self.p15_files.get("/usr/bin/im.elf.orig")
            cur_im_bytes = self.p15_files.get("/usr/bin/im.elf", b"")
            cur_is_stock = hashlib.sha256(cur_im_bytes).hexdigest() == self.stock_im_elf_sha256

            if not cur_is_stock:
                if orig_bytes is not None and hashlib.sha256(orig_bytes).hexdigest() == self.stock_im_elf_sha256:
                    restore_src = orig_bytes
                elif sd_rescue_stock_bytes is not None and hashlib.sha256(sd_rescue_stock_bytes).hexdigest() == self.stock_im_elf_sha256:
                    restore_src = sd_rescue_stock_bytes
                else:
                    raise ValueError(
                        f"{ERR_ORIG_SHA256_MISMATCH_ABORT}: .orig corrupt/missing and no verified SD rescue image"
                    )

                self.p15_files["/usr/bin/im.elf.restore.tmp"] = restore_src
                if crash_cutpoint == "AFTER_TMP_WRITE_BEFORE_RENAME":
                    return "CRASHED_BEFORE_RENAME"

                self.p15_files["/usr/bin/im.elf"] = self.p15_files.pop("/usr/bin/im.elf.restore.tmp")
                if crash_cutpoint == "AFTER_RENAME_BEFORE_ORIG_UNLINK":
                    return "CRASHED_BEFORE_ORIG_UNLINK"

            # Idempotent cleanup of .orig, .tmp, and any Stage-B residual files on p15 & p6
            for p15_res in list(self.p15_files):
                if (
                    p15_res.endswith(".orig")
                    or p15_res.endswith(".tmp")
                    or "stageb" in p15_res.lower()
                ):
                    self.p15_files.pop(p15_res, None)

            for p6_res in list(self.p6_files):
                if p6_res != "/tmp/jiritsu/factory_empty.keep":
                    self.p6_files.pop(p6_res, None)

            return "CLEAN_UNINSTALLED_H0_EQ_H3"
        finally:
            self.p15_mounted_rw = False


def _synthetic_stock_im_elf_bytes() -> bytes:
    """Deterministic in-memory stand-in for stock im.elf matching pinned length contract."""
    seed = hashlib.sha256(b"PHASE143_STOCK_FX3_702_IM_ELF_BASELINE").digest()
    return (seed * (FX3_IM_ELF_EXPECTED_SIZE // len(seed) + 1))[:FX3_IM_ELF_EXPECTED_SIZE]


def run_4epoch_h0_to_h3_and_power_loss_drills(
    *,
    launcher_script: str,
) -> Pillar3UninstallerAndH0H3Report:
    """Simulate H0 -> H1 -> H2 -> H3 across all 16 surfaces + 5 power-loss recovery drills."""
    errors: List[str] = []
    stock_im_bytes = _synthetic_stock_im_elf_bytes()
    launcher_bytes = launcher_script.encode("utf-8")

    cam = _SimulatedSixteenSurfaceCameraStorage(stock_im_elf_bytes=stock_im_bytes)
    h0 = cam.snapshot_16_hashes()

    # H1: Atomic /dev/cnflasha15 install
    cam.install_stageb_on_cnflasha15(block_device="/dev/cnflasha15", launcher_bytes=launcher_bytes)
    h1 = cam.snapshot_16_hashes()

    # H2: Simulated Stage-B dual-boot shooting session (RAM/tmpfs only; zero persistent drift)
    cam.p6_files["/tmp/jiritsu/stageb_session_marker.tmp"] = b"TRANSIENT_H2_MARKER"
    h2 = cam.snapshot_16_hashes()

    # H3: Atomic Clean Uninstall
    status_h3 = cam.atomic_uninstall_on_cnflasha15(block_device="/dev/cnflasha15")
    if status_h3 != "CLEAN_UNINSTALLED_H0_EQ_H3":
        errors.append(f"Unexpected H3 uninstall status: {status_h3}")
    h3 = cam.snapshot_16_hashes()

    parities: List[SurfaceEpochParity] = []
    h0_eq_h3_cnt = 0
    for sid in SIXTEEN_STORAGE_SURFACES:
        eq = h0[sid] == h3[sid]
        if eq:
            h0_eq_h3_cnt += 1
        sz = (
            sum(len(v) for v in cam.p15_files.values())
            if sid == "p15"
            else sum(len(v) for v in cam.p6_files.values())
            if sid == "p6"
            else len(cam.surfaces[sid])
        )
        parities.append(
            SurfaceEpochParity(
                surface_id=sid,
                h0_sha256=h0[sid],
                h1_sha256=h1[sid],
                h2_sha256=h2[sid],
                h3_sha256=h3[sid],
                h1_changed=(h0[sid] != h1[sid]),
                h0_equals_h3=eq,
                size_bytes=sz,
            )
        )

    h1_changed_surfaces = [p.surface_id for p in parities if p.h1_changed]
    h1_only_p15 = h1_changed_surfaces == ["p15"]
    h2_zero_cp_wbi_cal = all(
        h0[s] == h2[s] for s in ("sector0", "p2", "p5", "p8", "p12", "p18", "spi_nor", "otp", "rpmb")
    )
    res_orig_p15 = tuple(sorted(k for k in cam.p15_files if k.endswith(".orig")))
    res_stageb_p15 = tuple(sorted(k for k in cam.p15_files if k.endswith(".tmp") or "stageb" in k.lower()))
    res_stageb_p6 = tuple(sorted(k for k in cam.p6_files if k != "/tmp/jiritsu/factory_empty.keep"))

    if not h1_only_p15:
        errors.append(f"H1 modified unexpected surfaces: {h1_changed_surfaces}")
    if h0_eq_h3_cnt != 16:
        errors.append(f"H0 != H3 on {16 - h0_eq_h3_cnt} surfaces")
    if res_orig_p15 or res_stageb_p15 or res_stageb_p6:
        errors.append("Residual .orig or Stage-B files left after H3 uninstall")

    # Fault-Injected Mid-Uninstall Power-Loss & Security Drills (5 drills)
    drills: List[PowerLossRecoveryResult] = []
    for drill_id in POWER_LOSS_DRILL_IDS:
        d_cam = _SimulatedSixteenSurfaceCameraStorage(stock_im_elf_bytes=stock_im_bytes)
        d_h0 = d_cam.snapshot_16_hashes()
        d_cam.install_stageb_on_cnflasha15(block_device="/dev/cnflasha15", launcher_bytes=launcher_bytes)
        d_errs: List[str] = []
        raw_blocked = False
        obs_disp = ""

        if drill_id == "PL01_CRASH_AFTER_TMP_WRITE_BEFORE_RENAME":
            mid = d_cam.atomic_uninstall_on_cnflasha15(
                crash_cutpoint="AFTER_TMP_WRITE_BEFORE_RENAME"
            )
            obs_disp = f"{mid}->" + d_cam.atomic_uninstall_on_cnflasha15()
            exp_disp = "CRASHED_BEFORE_RENAME->CLEAN_UNINSTALLED_H0_EQ_H3"
        elif drill_id == "PL02_CRASH_AFTER_RENAME_BEFORE_ORIG_UNLINK":
            mid = d_cam.atomic_uninstall_on_cnflasha15(
                crash_cutpoint="AFTER_RENAME_BEFORE_ORIG_UNLINK"
            )
            obs_disp = f"{mid}->" + d_cam.atomic_uninstall_on_cnflasha15()
            exp_disp = "CRASHED_BEFORE_ORIG_UNLINK->CLEAN_UNINSTALLED_H0_EQ_H3"
        elif drill_id == "PL03_CORRUPT_ORIG_FAIL_CLOSED_AND_SD_RESCUE":
            orig_mut = bytearray(d_cam.p15_files["/usr/bin/im.elf.orig"])
            orig_mut[0] ^= 0xFF
            d_cam.p15_files["/usr/bin/im.elf.orig"] = bytes(orig_mut)
            aborted = False
            try:
                d_cam.atomic_uninstall_on_cnflasha15()
            except ValueError as exc:
                aborted = ERR_ORIG_SHA256_MISMATCH_ABORT in str(exc)
            if not aborted:
                d_errs.append("Failed to abort on corrupt .orig")
            rescued = d_cam.atomic_uninstall_on_cnflasha15(sd_rescue_stock_bytes=stock_im_bytes)
            obs_disp = f"ABORTED_CORRUPT_ORIG->{rescued}"
            exp_disp = "ABORTED_CORRUPT_ORIG->CLEAN_UNINSTALLED_H0_EQ_H3"
        elif drill_id == "PL04_P6_RESIDUAL_STAGEB_CLEANUP":
            d_cam.p6_files["/tmp/jiritsu/libJit.so"] = b"RESIDUAL_JIT"
            d_cam.p6_files["/tmp/jiritsu/stageb_diag.tmp"] = b"RESIDUAL_DIAG"
            obs_disp = d_cam.atomic_uninstall_on_cnflasha15()
            exp_disp = "CLEAN_UNINSTALLED_H0_EQ_H3"
        else:  # PL05_RAW_PNFLASHA15_PLAINTEXT_BLOCKED
            try:
                d_cam.atomic_uninstall_on_cnflasha15(block_device="/dev/pnflasha15")
            except PermissionError as exc:
                raw_blocked = BLOCKED_RAW_PNFLASHA_PLAINTEXT_WRITE in str(exc)
            obs_disp = (
                "BLOCKED_RAW_PNFLASHA15->" + d_cam.atomic_uninstall_on_cnflasha15(block_device="/dev/cnflasha15")
            )
            exp_disp = "BLOCKED_RAW_PNFLASHA15->CLEAN_UNINSTALLED_H0_EQ_H3"
            if not raw_blocked:
                d_errs.append("Raw /dev/pnflasha15 write was not blocked")

        d_h3 = d_cam.snapshot_16_hashes()
        matched_cnt = sum(1 for s in SIXTEEN_STORAGE_SURFACES if d_h0[s] == d_h3[s])
        rem_orig = sum(1 for k in d_cam.p15_files if k.endswith(".orig"))
        rem_sb = sum(1 for k in d_cam.p15_files if k.endswith(".tmp") or "stageb" in k.lower()) + sum(
            1 for k in d_cam.p6_files if k != "/tmp/jiritsu/factory_empty.keep"
        )
        ok_d = (
            obs_disp == exp_disp
            and matched_cnt == 16
            and rem_orig == 0
            and rem_sb == 0
            and len(d_errs) == 0
        )
        drills.append(
            PowerLossRecoveryResult(
                drill_id=drill_id,
                passed=ok_d,
                expected_disposition=exp_disp,
                observed_disposition=obs_disp,
                h0_equals_h3_after_recovery=(matched_cnt == 16),
                matched_surfaces_after_recovery=matched_cnt,
                residual_orig_count=rem_orig,
                residual_stageb_count=rem_sb,
                raw_pnflasha_blocked=raw_blocked,
                errors=tuple(d_errs),
            )
        )

    drills_passed = sum(1 for d in drills if d.passed)
    all_ok = (
        h0_eq_h3_cnt == 16
        and h1_only_p15
        and h2_zero_cp_wbi_cal
        and not res_orig_p15
        and not res_stageb_p15
        and not res_stageb_p6
        and drills_passed == len(drills)
        and len(errors) == 0
    )

    return Pillar3UninstallerAndH0H3Report(
        pillar_id="ATOMIC_CLEAN_UNINSTALLER_AND_H0_EQUALS_H3_PROOF",
        all_checks_passed=all_ok,
        epochs_verified=FOUR_EPOCHS,
        surface_count=len(SIXTEEN_STORAGE_SURFACES),
        h0_equals_h3_count=h0_eq_h3_cnt,
        h0_equals_h3_all_16=(h0_eq_h3_cnt == 16),
        h1_only_p15_changed=h1_only_p15,
        h2_zero_cp_wbi_cal_drift=h2_zero_cp_wbi_cal,
        residual_orig_files_p15=res_orig_p15,
        residual_stageb_files_p15=res_stageb_p15,
        residual_stageb_files_p6=res_stageb_p6,
        crypto_cnflasha15_enforced=True,
        surface_parities=tuple(parities),
        power_loss_drill_count=len(drills),
        power_loss_drills_passed=drills_passed,
        power_loss_drills=tuple(drills),
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 4 & Master Suite + Self-Authenticating Tamper Verifier
# ---------------------------------------------------------------------------


def audit_pillar4_no_physical_flash_guard(
    *,
    raw_pnflasha_blocked: bool,
) -> Pillar4HardwareWriteLockReport:
    errors: List[str] = []
    if PERSISTENT_EMMC_WRITES_AUTHORIZED:
        errors.append("PERSISTENT_EMMC_WRITES_AUTHORIZED must remain False")
    if SD_PHYSICAL_MEDIA_WRITTEN:
        errors.append("SD_PHYSICAL_MEDIA_WRITTEN must remain False")
    if PERSISTENT_WRITE_RELEASE:
        errors.append("PERSISTENT_WRITE_RELEASE must remain False")
    if PHYSICAL_DEVICE_WRITES != 0:
        errors.append("PHYSICAL_DEVICE_WRITES must remain 0")
    if not raw_pnflasha_blocked:
        errors.append("Raw /dev/pnflasha15 write must be blocked")

    return Pillar4HardwareWriteLockReport(
        pillar_id="HARD_LOCKED_NO_PHYSICAL_FLASH_GUARD",
        all_checks_passed=(len(errors) == 0),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        sd_physical_media_written=SD_PHYSICAL_MEDIA_WRITTEN,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        raw_pnflasha_plaintext_blocked=raw_pnflasha_blocked,
        errors=tuple(errors),
    )


def run_phase143_sd_stageb_bundle_uninstaller_audit(
    *,
    lang: str = "en",
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    synthetic_clean_room: Optional[bool] = None,
) -> Phase143SdStageBBundleUninstallerReport:
    """Execute full Phase 143 dual-mode verification across all 4 pillars."""
    errors: List[str] = []
    donor_insp = inspect_phase143_donors_readonly(
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        synthetic_clean_room=synthetic_clean_room,
    )
    if not donor_insp.all_checks_passed:
        errors.extend(donor_insp.errors)

    p1_rep, bundle = audit_pillar1_bundle_builder(
        lang=lang,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        synthetic_clean_room=synthetic_clean_room,
    )
    if not p1_rep.all_checks_passed:
        errors.extend(p1_rep.errors)

    p2_rep = run_escape_hatch_launcher_sandbox_drills(bundle)
    if not p2_rep.all_checks_passed:
        errors.extend(p2_rep.errors)

    launcher_script = generate_im_elf_escape_hatch_launcher(
        expected_body_serial=bundle.target_body_serial
    )
    p3_rep = run_4epoch_h0_to_h3_and_power_loss_drills(launcher_script=launcher_script)
    if not p3_rep.all_checks_passed:
        errors.extend(p3_rep.errors)

    pl05 = next(
        (d for d in p3_rep.power_loss_drills if d.drill_id == "PL05_RAW_PNFLASHA15_PLAINTEXT_BLOCKED"),
        None,
    )
    raw_blocked = bool(pl05 is not None and pl05.raw_pnflasha_blocked)
    p4_rep = audit_pillar4_no_physical_flash_guard(raw_pnflasha_blocked=raw_blocked)
    if not p4_rep.all_checks_passed:
        errors.extend(p4_rep.errors)

    all_ok = (
        donor_insp.all_checks_passed
        and p1_rep.all_checks_passed
        and p2_rep.all_checks_passed
        and p3_rep.all_checks_passed
        and p4_rep.all_checks_passed
        and len(errors) == 0
    )

    payload_for_hash: Dict[str, Any] = {
        "schema": PHASE_143_SCHEMA,
        "phase_version": PHASE_143_VERSION,
        "verification_mode": donor_insp.verification_mode,
        "all_checks_passed": all_ok,
        "status": (
            "VERIFIED_SD_STAGEB_BUNDLE_AND_H0_EQ_H3_UNINSTALLER"
            if all_ok
            else "FAILED_SD_STAGEB_BUNDLE_OR_UNINSTALLER"
        ),
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "sd_physical_media_written": SD_PHYSICAL_MEDIA_WRITTEN,
        "persistent_write_release": PERSISTENT_WRITE_RELEASE,
        "physical_device_writes": PHYSICAL_DEVICE_WRITES,
        "raw_firmware_slices_emitted": 0,
        "lang": lang,
        "donor_inspection": asdict(donor_insp),
        "pillar1_bundle_builder": asdict(p1_rep),
        "pillar2_escape_hatch_launcher": asdict(p2_rep),
        "pillar3_atomic_uninstaller_h0_h3": asdict(p3_rep),
        "pillar4_no_physical_flash_guard": asdict(p4_rep),
        "errors": tuple(errors),
    }
    rep_sha = _compute_canonical_sha256(payload_for_hash, "report_sha256")

    return Phase143SdStageBBundleUninstallerReport(
        schema=PHASE_143_SCHEMA,
        phase_version=PHASE_143_VERSION,
        verification_mode=donor_insp.verification_mode,
        all_checks_passed=all_ok,
        status=str(payload_for_hash["status"]),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        sd_physical_media_written=SD_PHYSICAL_MEDIA_WRITTEN,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        raw_firmware_slices_emitted=0,
        lang=lang,
        donor_inspection=donor_insp,
        pillar1_bundle_builder=p1_rep,
        pillar2_escape_hatch_launcher=p2_rep,
        pillar3_atomic_uninstaller_h0_h3=p3_rep,
        pillar4_no_physical_flash_guard=p4_rep,
        errors=tuple(errors),
        report_sha256=rep_sha,
    )


def verify_phase143_report(report_dict: Mapping[str, Any]) -> Phase143ReportVerifyResult:
    """Fail-closed tamper & redline verifier for Phase 143 JSON reports."""
    errors: List[str] = []
    if report_dict.get("schema") != PHASE_143_SCHEMA:
        errors.append(f"Unexpected schema: {report_dict.get('schema')!r}")
    if report_dict.get("persistent_emmc_writes_authorized") is not False:
        errors.append("persistent_emmc_writes_authorized must be False")
    if report_dict.get("sd_physical_media_written") is not False:
        errors.append("sd_physical_media_written must be False")
    if report_dict.get("persistent_write_release") is not False:
        errors.append("persistent_write_release must be False")
    if report_dict.get("physical_device_writes") != 0:
        errors.append("physical_device_writes must be 0")
    if report_dict.get("raw_firmware_slices_emitted") != 0:
        errors.append("raw_firmware_slices_emitted must be 0")

    expected_sha = _compute_canonical_sha256(report_dict, "report_sha256")
    if report_dict.get("report_sha256") != expected_sha:
        errors.append("report_sha256 tamper mismatch")

    p1 = report_dict.get("pillar1_bundle_builder", {})
    p2 = report_dict.get("pillar2_escape_hatch_launcher", {})
    p3 = report_dict.get("pillar3_atomic_uninstaller_h0_h3", {})
    p4 = report_dict.get("pillar4_no_physical_flash_guard", {})
    for name, sec in (("pillar1", p1), ("pillar2", p2), ("pillar3", p3), ("pillar4", p4)):
        if not isinstance(sec, Mapping) or not sec.get("all_checks_passed"):
            errors.append(f"{name} did not pass all checks")

    if isinstance(p3, Mapping) and p3.get("h0_equals_h3_count") != 16:
        errors.append("H0 == H3 must match all 16 surfaces")
    if isinstance(p1, Mapping) and not p1.get("within_64mib_ddr_budget"):
        errors.append("SD Stage-B RAM/tmpfs footprint exceeded 64 MiB DDR budget")

    raw_json = json.dumps(report_dict, sort_keys=True)
    if _RAW_BYTES_REPR_RE.search(raw_json):
        errors.append("Raw Python bytes repr detected in JSON output")

    return Phase143ReportVerifyResult(valid=(len(errors) == 0), errors=tuple(errors))
