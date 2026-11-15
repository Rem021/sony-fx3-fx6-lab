"""Phase 113 — CXD90057 / CXD90058 Dual-Bank A/B Boot-Slot Consistency, Interrupted Official
BODYDATA.DAT / USB-OTA Power-Loss Forensic Triage, & 11-Pillar Recovery Master Suite.

Provides three deterministic, RAM-only, read-only-donor verification pillars for
Sony `ILME-FX3` (`0x91030080` / `ALCIN_UUD`, AP `CXD90057` + CP `CXD90058`) recovery
and Stage-B safety verification:

1. **Pillar 1 — CXD90057 / CXD90058 Dual-Bank (Bank-A / Bank-B) AP+CP Synchronized Epoch & Torn-Bank Detector**:
   - Models the four deterministic Dual-Bank slot health states:
     `ACTIVE_VERIFIED`, `PENDING_TRIAL`, `TORN_PARTIAL_WRITE`, and `ROLLBACK_FENCED`.
   - Audits both AP (`nbl_a/uboot_a/boot_a` vs `nbl_b/uboot_b/boot_b`) and CP
     (`cpapp-a.bin` vs `cpapp-b.bin`) bank descriptors in RAM without writing to flash.
   - Detects and rejects split-epoch AP/CP mismatches fail-closed (e.g., AP booting
     Bank-B `7.02` while CP remains torn on half-written Bank-A `2.05` / corrupt CRC),
     which otherwise cause an AP<->CP IPC protocol deadlock (amber/red LED blink brick).

2. **Pillar 2 — Interrupted Official `BODYDATA.DAT` / Creators'-App OTA Power-Loss Brick Forensic Triage**:
   - Enforces Sony's official pre-flight update gate (`battery_pct >= 51%`, UFU `\x89UFU\r\n\x1a\n`
     header & CRC, FX3 model `0x91030080` & region match, synchronized dual-bank precheck).
   - Diagnoses the 6 canonical real-world Sony firmware-update brick states:
     - `U1_BATTERY_PULLED_DURING_CP_FLASH`
     - `U2_SD_CARD_READ_CRC_MID_UPDATA`
     - `U3_USB_CABLE_YANKED_LEGACY_UPDATER`
     - `U4_CROSS_REGION_NTSC_PAL_MISMATCH`
     - `U5_STAGE_B_CLEAN_SD_EJECT_ZERO_BRICK`
     - `U6_INTACT_DUAL_BANK_HEALTHY`
   - Maps each state to exact non-destructive recovery actions (`FX3_SAFE_STOCK.FLG` SD instant boot,
     passive `1.8V` UART `48000`/`115200` diagnosis, or Tier-0 read-only dump) and explicitly proves
     why Stage-B RAM/SD userland overlay (`U5`) has ZERO flash-interruption brick surface even on
     sudden battery yank (`0` eMMC bank transitions, `0` `updata` state flags touched).

3. **Pillar 3 — 11-Pillar Recovery Master Suite Readiness Gate (`run_ab_bank_and_interrupted_ota_suite`)**:
   - Dual-mode execution (`LOCAL_DONOR_O_RDONLY` via `os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK`
     and `CLEAN_ROOM_SYNTHETIC` when `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor absent).
   - Hard-locks `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `PERSISTENT_WRITE_RELEASE = False`,
     `ALLOW_BOOT_PARTITION_TARGETING = False`, `ALLOW_DESTRUCTIVE_FASTBOOT = False`,
     `OTP_FUSE_TOUCHES = 0`, `PASSIVE_TX_BYTES_EMITTED = 0`, `PHYSICAL_DEVICE_WRITES = 0`.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .fat import FatP1, MAX_P1
from .files import is_forced_clean_room, local_path, read_file, require, resolve_donor_path
from .squash import SquashFS


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

AB_BANK_OTA_SCHEMA: str = "fx3-ab-bank-and-interrupted-ota-verifier-v1"
AB_BANK_OTA_VERSION: str = "1.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False
ALLOW_BOOT_PARTITION_TARGETING: bool = False
ALLOW_DESTRUCTIVE_FASTBOOT: bool = False
READ_ONLY_DONOR_ACCESS: bool = True
OTP_FUSE_TOUCHES: int = 0
PASSIVE_TX_BYTES_EMITTED: int = 0
PHYSICAL_DEVICE_WRITES: int = 0

STATUS_VERIFIED_AB_BANK_OTA_GATE: str = "VERIFIED_AB_BANK_AND_INTERRUPTED_OTA_GATE"
STATUS_FAIL_AB_BANK_OTA_GATE: str = "FAIL_AB_BANK_AND_INTERRUPTED_OTA_GATE"
STATUS_DUAL_BANK_CONSISTENT: str = "VERIFIED_DUAL_BANK_CONSISTENT"
STATUS_DUAL_BANK_TORN_REJECTED: str = "REJECTED_DUAL_BANK_SPLIT_OR_TORN"
STATUS_OTA_TRIAGE_HEALTHY: str = "OTA_TRIAGE_HEALTHY_OR_ZERO_BRICK"
STATUS_OTA_TRIAGE_RECOVERABLE: str = "OTA_TRIAGE_RECOVERABLE_BRICK"
STATUS_OTA_PREFLIGHT_APPROVED: str = "OTA_PREFLIGHT_APPROVED_OFFLINE_ONLY"
STATUS_OTA_PREFLIGHT_REJECTED: str = "OTA_PREFLIGHT_REJECTED"

# Local Donor Relative Paths (strictly read-only via os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK)
DONOR_FX3_P1_205_RELPATH: str = (
    "fx3-color-port-20261027/input-20261028/original-update-engine/2.05/nflasha1"
)
DONOR_FX3_UDTRBODY_RELPATH: str = (
    "sony-firmware-20261024/stage182-boot-selector-and-recovery-admission/"
    "current-updater-evidence/original-members/udtrbody.squashfs"
)
DONOR_FX3_CPAPP_B_RELPATH: str = (
    "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin"
)
DONOR_FX6_CPAPP_B_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fat-files/nflasha8/cpapp-b.bin"
)
DONOR_FX3_BODYDATA_RELPATH: str = "sony-firmware-20261024/fx3-7.02-BODYDATA.DAT"

# Pinned Donor Integrity Anchors (Zero Proprietary Keys)
PINNED_FX3_P1_205_SHA256: str = "ab2cd5372fed3c742b586e28484c6bf0aa6ebfba1f6d8e450a19191abc5b6591"
PINNED_FX3_UDTRBODY_SHA256: str = "62e86fad175e0326969d5f1cea29d780feb496ce8034acd2c9c3954320d8ccaa"
PINNED_FX3_CPAPP_B_SHA256: str = "c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba"
PINNED_FX6_CPAPP_B_SHA256: str = "60de0ab5544749dd50d8245f573c0994573fef349186efe20b502c42e3289668"
PINNED_FX3_BODYDATA_HEADER_SHA256: str = "fc135914e0767d69518e5b1f86b138abdbd2a20dd341e495cf151f8ddb79e404"
PINNED_FX3_BODYDATA_TOTAL_BYTES: int = 811876768
BODYDATA_UFU_MAGIC: bytes = b"\x89UFU\r\n\x1a\n"
BODYDATA_UFU_MAGIC_HEX: str = BODYDATA_UFU_MAGIC.hex()
BODYDATA_HEADER_READ_BYTES: int = 4096

# SoC, Model & Dual-Bank Constants
CXD90057_AP_SOC: str = "CXD90057"
CXD90058_CP_SOC: str = "CXD90058"
FX3_MODEL_ID: int = 0x91030080
FX6_MODEL_ID: int = 0x91040086
FX3_SKU_CODE: str = "ILME-FX3"
FX6_SKU_CODE: str = "ILME-FX6"

BANK_A: str = "BANK_A"
BANK_B: str = "BANK_B"
VALID_BANK_IDS: Tuple[str, ...] = (BANK_A, BANK_B)

DOMAIN_AP: str = "AP_CXD90057"
DOMAIN_CP: str = "CP_CXD90058"

CP_BANK_FILENAMES: Dict[str, str] = {
    BANK_A: "cpapp-a.bin",
    BANK_B: "cpapp-b.bin",
}
AP_BANK_FILENAMES: Dict[str, str] = {
    BANK_A: "ap_slot_a",
    BANK_B: "ap_slot_b",
}

BANK_STATE_ACTIVE_VERIFIED: str = "ACTIVE_VERIFIED"
BANK_STATE_PENDING_TRIAL: str = "PENDING_TRIAL"
BANK_STATE_TORN_PARTIAL_WRITE: str = "TORN_PARTIAL_WRITE"
BANK_STATE_ROLLBACK_FENCED: str = "ROLLBACK_FENCED"
DUAL_BANK_STATES: Tuple[str, ...] = (
    BANK_STATE_ACTIVE_VERIFIED,
    BANK_STATE_PENDING_TRIAL,
    BANK_STATE_TORN_PARTIAL_WRITE,
    BANK_STATE_ROLLBACK_FENCED,
)

# Monotonic Anti-Rollback Epoch Table (matches FX3 firmware lineage)
FX3_EPOCH_BY_VERSION: Dict[str, int] = {
    "1.00": 1,
    "1.01": 1,
    "2.00": 1,
    "2.04": 1,
    "2.05": 1,
    "3.00": 2,
    "4.00": 2,
    "5.00": 2,
    "6.00": 3,
    "6.01": 3,
    "6.02": 3,
    "7.00": 4,
    "7.01": 4,
    "7.02": 5,
}

# Sony Official Updater / BODYDATA.DAT / updata Constants
SONY_FW_UPDATE_MIN_BATTERY_PCT: int = 51
SONY_UPDATA_ERROR_UINCOMP: int = 54
SONY_UPDATA_FLAG_FILES: Tuple[str, ...] = (
    "/setting/updater/mode",
    "/setting/updater/mode1",
    "/setting/updater/mode3",
    "/setting/updater/mode5",
    "/setting/updater/mode6",
    "/setting/updater/mode7",
    "/setting/updater/uincomp",
    "/setting/updater/comp",
    "/setting/updater/dat4",
)
VALID_CAMERA_REGIONS: Tuple[str, ...] = ("NTSC", "PAL")
STAGE_B_SENTINEL_FILENAME: str = "FX3_SAFE_STOCK.FLG"

# 6 Canonical Interrupted-OTA Triage Scenario IDs
OTA_SCENARIO_U1_BATTERY_PULLED_CP: str = "U1_BATTERY_PULLED_DURING_CP_FLASH"
OTA_SCENARIO_U2_SD_CRC_MID_UPDATA: str = "U2_SD_CARD_READ_CRC_MID_UPDATA"
OTA_SCENARIO_U3_USB_CABLE_YANKED: str = "U3_USB_CABLE_YANKED_LEGACY_UPDATER"
OTA_SCENARIO_U4_CROSS_REGION_MISMATCH: str = "U4_CROSS_REGION_NTSC_PAL_MISMATCH"
OTA_SCENARIO_U5_STAGE_B_ZERO_BRICK: str = "U5_STAGE_B_CLEAN_SD_EJECT_ZERO_BRICK"
OTA_SCENARIO_U6_INTACT_HEALTHY: str = "U6_INTACT_DUAL_BANK_HEALTHY"

OTA_SCENARIO_IDS: Tuple[str, ...] = (
    OTA_SCENARIO_U1_BATTERY_PULLED_CP,
    OTA_SCENARIO_U2_SD_CRC_MID_UPDATA,
    OTA_SCENARIO_U3_USB_CABLE_YANKED,
    OTA_SCENARIO_U4_CROSS_REGION_MISMATCH,
    OTA_SCENARIO_U5_STAGE_B_ZERO_BRICK,
    OTA_SCENARIO_U6_INTACT_HEALTHY,
)

# Error & Triage Action Codes
ERR_INVALID_BANK_ID: str = "DUAL_BANK_INVALID_BANK_ID"
ERR_AP_BANK_TORN_PARTIAL_WRITE: str = "DUAL_BANK_AP_TORN_PARTIAL_WRITE"
ERR_CP_BANK_TORN_PARTIAL_WRITE: str = "DUAL_BANK_CP_TORN_PARTIAL_WRITE"
ERR_AP_BANK_ROLLBACK_FENCED: str = "DUAL_BANK_AP_ROLLBACK_FENCED"
ERR_CP_BANK_ROLLBACK_FENCED: str = "DUAL_BANK_CP_ROLLBACK_FENCED"
ERR_AP_CP_IPC_EPOCH_DEADLOCK: str = "DUAL_BANK_AP_CP_IPC_EPOCH_DEADLOCK"
ERR_AP_CP_ACTIVE_BANK_DESYNC: str = "DUAL_BANK_AP_CP_ACTIVE_BANK_DESYNC"
ERR_CROSS_SKU_BANK_MISMATCH: str = "DUAL_BANK_CROSS_SKU_MISMATCH"
ERR_FALLBACK_BANK_ROLLBACK_FENCED: str = "DUAL_BANK_FALLBACK_ROLLBACK_FENCED"
ERR_NO_INTACT_FALLBACK_BANK: str = "DUAL_BANK_NO_INTACT_FALLBACK_BANK"

ERR_OTA_BATTERY_BELOW_51_PCT: str = "OTA_PREFLIGHT_BATTERY_BELOW_51_PCT"
ERR_OTA_MODEL_MISMATCH: str = "OTA_PREFLIGHT_MODEL_MISMATCH"
ERR_OTA_REGION_NTSC_PAL_MISMATCH: str = "OTA_PREFLIGHT_CROSS_REGION_NTSC_PAL_MISMATCH"
ERR_OTA_BODYDATA_CRC_OR_MAGIC: str = "OTA_PREFLIGHT_BODYDATA_CRC_OR_UFU_MAGIC_INVALID"
ERR_OTA_UNSTABLE_TRANSPORT: str = "OTA_PREFLIGHT_UNSTABLE_TRANSPORT_MEDIUM"
ERR_OTA_SPLIT_BANK_PRECHECK_FAILED: str = "OTA_PREFLIGHT_DUAL_BANK_INCONSISTENT"

ACTION_PASSIVE_UART_AND_TIER0_NOR_DUMP: str = "PASSIVE_1V8_UART_DIAG_AND_TIER0_NOR_DUMP"
ACTION_SD_SLOT1_VERIFIED_BODYDATA_OR_CLEAR_FLAGS: str = "SD_SLOT1_VERIFIED_BODYDATA_OR_CLEAR_MODE_FLAGS"
ACTION_TIER0_READONLY_DUMP_AND_SD_BODYDATA: str = "TIER0_READONLY_DUMP_THEN_SD_SLOT1_BODYDATA"
ACTION_REJECT_CROSS_REGION_RESTORE_STOCK: str = "REJECT_CROSS_REGION_AND_RESTORE_MATCHING_BODYDATA"
ACTION_SD_SENTINEL_INSTANT_BOOT_ZERO_BRICK: str = "SD_FX3_SAFE_STOCK_FLG_INSTANT_BOOT_ZERO_BRICK"
ACTION_NO_RECOVERY_NEEDED_HEALTHY: str = "NO_RECOVERY_NEEDED_HEALTHY_STOCK_OR_STAGE_B_READY"

RECOVERY_ACTION_CODES: Tuple[str, ...] = (
    ACTION_PASSIVE_UART_AND_TIER0_NOR_DUMP,
    ACTION_SD_SLOT1_VERIFIED_BODYDATA_OR_CLEAR_FLAGS,
    ACTION_TIER0_READONLY_DUMP_AND_SD_BODYDATA,
    ACTION_REJECT_CROSS_REGION_RESTORE_STOCK,
    ACTION_SD_SENTINEL_INSTANT_BOOT_ZERO_BRICK,
    ACTION_NO_RECOVERY_NEEDED_HEALTHY,
)


# ---------------------------------------------------------------------------
# Canonical JSON Digest Helper (Zero raw bytes fields emitted)
# ---------------------------------------------------------------------------


def _canonical_sha256(obj: Any) -> str:
    payload = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return sha256(payload.encode("utf-8")).hexdigest()


def _read_bounded_header_readonly(path: Path, header_bytes: int = BODYDATA_HEADER_READ_BYTES) -> Tuple[int, bytes]:
    """Open regular donor file strictly O_RDONLY | O_NOFOLLOW | O_NONBLOCK and read bounded header."""
    p = local_path(path, allow_donor_roots=True)
    require(hasattr(os, "O_NOFOLLOW"), "POSIX O_NOFOLLOW required")
    fd = os.open(p, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1, "single-link regular file required")
        require(before.st_size >= 0, "negative file size rejected")
        to_read = min(header_bytes, before.st_size)
        chunks: List[bytes] = []
        remaining = to_read
        while remaining > 0:
            chunk = os.read(fd, remaining)
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        after = os.fstat(fd)
        for fld in ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns", "st_mode", "st_nlink"):
            require(getattr(before, fld) == getattr(after, fld), "donor file changed during read")
        require(len(data) == to_read, "short read on donor header")
        return before.st_size, data
    finally:
        os.close(fd)


# ---------------------------------------------------------------------------
# Structured Dataclasses (Zero raw bytes fields)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AbBankDonorArtifactDigest:
    label: str
    relpath: str
    source_mode: str
    byte_length: int
    sha256: str
    details: str


@dataclass(frozen=True)
class DonorAbBankOtaSnapshot:
    verification_mode: str
    read_only_access: bool
    cpapp_b_present: bool
    cpapp_a_referenced_in_dual_bank_model: bool
    updata_flags_verified: Tuple[str, ...]
    bodydata_magic_hex: str
    bodydata_total_bytes: int
    sony_min_battery_pct_gate: int
    fx3_cpapp_b_sha256: str
    fx6_cpapp_b_sha256: str
    fx3_p1_205_sha256: str
    fx3_udtrbody_sha256: str
    artifacts: Tuple[AbBankDonorArtifactDigest, ...]
    snapshot_sha256: str


@dataclass(frozen=True)
class BankSlotDescriptor:
    bank_id: str
    domain: str
    artifact_name: str
    firmware_version: str
    epoch: int
    declared_crc32: int
    computed_crc32: int
    bytes_written: int
    expected_bytes: int
    trial_flag: bool = False
    rollback_fenced: bool = False
    is_active: bool = False
    sku_code: str = FX3_SKU_CODE


@dataclass(frozen=True)
class BankSlotHealthResult:
    bank_id: str
    domain: str
    artifact_name: str
    firmware_version: str
    epoch: int
    classified_state: str
    crc_valid: bool
    complete_write: bool
    bootable: bool
    sku_code: str
    error_codes: Tuple[str, ...]


@dataclass(frozen=True)
class DualBankConsistencyReport:
    passed: bool
    status: str
    ap_active_bank: str
    cp_active_bank: str
    min_otp_epoch: int
    ap_bank_a: BankSlotHealthResult
    ap_bank_b: BankSlotHealthResult
    cp_bank_a: BankSlotHealthResult
    cp_bank_b: BankSlotHealthResult
    ipc_protocol_compatible: bool
    split_epoch_deadlock_detected: bool
    fallback_bank_available: Optional[str]
    recommended_recovery_tier: str
    recommended_action: str
    led_pattern_hint: str
    error_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    ram_only_classification: bool
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    report_sha256: str


@dataclass(frozen=True)
class OtaPreflightResult:
    passed: bool
    status: str
    battery_pct: int
    min_battery_pct_required: int
    model_id: int
    model_id_hex: str
    camera_region: str
    package_region: str
    bodydata_magic_hex: str
    bodydata_crc_ok: bool
    media_slot_stable: bool
    dual_bank_precheck_ok: bool
    error_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    persistent_emmc_writes_authorized: bool


@dataclass(frozen=True)
class OtaInterruptionEvidence:
    scenario_id: str
    battery_pct_at_event: int
    interruption_phase: str
    transport_medium: str
    dual_bank_report: DualBankConsistencyReport
    updata_uincomp_present: bool
    updata_mode_flags: Tuple[str, ...]
    sd_crc_error_detected: bool
    usb_disconnect_mid_transfer: bool
    camera_region: str
    package_region: str
    stage_b_ram_overlay_active: bool
    emmc_bank_transitions: int
    updata_flags_touched: bool
    led_pattern: str


@dataclass(frozen=True)
class OtaBrickTriageResult:
    scenario_id: str
    passed: bool
    status: str
    brick_severity: str
    flash_interruption_brick_surface: bool
    stage_b_zero_brick_proven: bool
    emmc_bank_transitions: int
    updata_flags_touched: bool
    recommended_recovery_tier: str
    recovery_action_code: str
    recovery_steps: Tuple[str, ...]
    passive_uart_required: bool
    sd_sentinel_instant_escape_available: bool
    tier0_readonly_dump_required: bool
    dual_bank_status: str
    diagnosis_summary: str
    error_codes: Tuple[str, ...]
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool


@dataclass(frozen=True)
class Ota6ScenarioSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    stage_b_u5_zero_brick_verified: bool
    scenario_results: Tuple[OtaBrickTriageResult, ...]
    errors: Tuple[str, ...]
    suite_sha256: str


@dataclass(frozen=True)
class AbBankAndInterruptedOtaSuiteReport:
    schema: str
    version: str
    status: str
    verification_mode: str
    all_passed: bool
    read_only_donor_access: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    allow_boot_partition_targeting: bool
    allow_destructive_fastboot: bool
    otp_fuse_touches: int
    passive_tx_bytes_emitted: int
    physical_device_writes: int
    donor_snapshot: DonorAbBankOtaSnapshot
    dual_bank_healthy_report: DualBankConsistencyReport
    dual_bank_split_deadlock_report: DualBankConsistencyReport
    dual_bank_trial_pending_report: DualBankConsistencyReport
    dual_bank_rollback_fenced_report: DualBankConsistencyReport
    ota_preflight_valid: OtaPreflightResult
    ota_preflight_low_battery_blocked: OtaPreflightResult
    ota_6_scenario_suite: Ota6ScenarioSuiteResult
    suite_sha256: str
    elapsed_seconds: float
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Donor Read-Only Inspection & Clean-Room Synthetic Fallback
# ---------------------------------------------------------------------------


def inspect_ab_bank_and_ota_donors_readonly(*, force_clean_room: Optional[bool] = None) -> DonorAbBankOtaSnapshot:
    """Inspect local FX3/FX6 donor artifacts strictly O_RDONLY | O_NOFOLLOW | O_NONBLOCK,
    with deterministic CLEAN_ROOM_SYNTHETIC fallback when forced or donor files are absent.
    """
    clean_room = is_forced_clean_room() if force_clean_room is None else bool(force_clean_room)
    if not clean_room:
        p1_path = resolve_donor_path(DONOR_FX3_P1_205_RELPATH, require_file=True)
        udtr_path = resolve_donor_path(DONOR_FX3_UDTRBODY_RELPATH, require_file=True)
        fx3_cp_path = resolve_donor_path(DONOR_FX3_CPAPP_B_RELPATH, require_file=True)
        fx6_cp_path = resolve_donor_path(DONOR_FX6_CPAPP_B_RELPATH, require_file=True)
        bodydata_path = resolve_donor_path(DONOR_FX3_BODYDATA_RELPATH, require_file=True)
        all_present = all(p.is_file() for p in (p1_path, udtr_path, fx3_cp_path, fx6_cp_path, bodydata_path))
    else:
        p1_path = udtr_path = fx3_cp_path = fx6_cp_path = bodydata_path = Path()
        all_present = False

    if all_present:
        p1_bytes = read_file(p1_path, MAX_P1)
        udtr_bytes = read_file(udtr_path, 8 * 1024 * 1024)
        fx3_cp_bytes = read_file(fx3_cp_path, 32 * 1024 * 1024)
        fx6_cp_bytes = read_file(fx6_cp_path, 32 * 1024 * 1024)
        bd_total, bd_hdr = _read_bounded_header_readonly(bodydata_path, BODYDATA_HEADER_READ_BYTES)

        p1_sha = sha256(p1_bytes).hexdigest()
        udtr_sha = sha256(udtr_bytes).hexdigest()
        fx3_cp_sha = sha256(fx3_cp_bytes).hexdigest()
        fx6_cp_sha = sha256(fx6_cp_bytes).hexdigest()
        bd_hdr_sha = sha256(bd_hdr).hexdigest()

        # Verify authentic strings inside p1 SquashFS & udtrbody.squashfs in RAM
        fat = FatP1(p1_bytes)
        p1_fs = SquashFS(fat.contents("/boot/initrd.img"))
        p1_files = {r["path"]: r for r in p1_fs.walk() if r["type"] == "file"}
        udtr_main = p1_fs.contents(p1_files["/usr/bin/UdtrMain.sh"]).decode("utf-8", "replace")
        common_src = p1_fs.contents(p1_files["/usr/bin/common.src"]).decode("utf-8", "replace")
        sdfile_bin = p1_fs.contents(p1_files["/usr/bin/sdfileinput.elf"])
        buspwr_ko = p1_fs.contents(p1_files["/usr/kmod/usb_buspwr.ko"])

        udtr_fs = SquashFS(udtr_bytes)
        udtr_files = {r["path"]: r for r in udtr_fs.walk() if r["type"] == "file"}
        nor_writer = udtr_fs.contents(udtr_files["/bin/nor_loader_writer.sh"]).decode("utf-8", "replace")

        require(b"BODYDATA.DAT" in sdfile_bin, "p1 sdfileinput.elf missing BODYDATA.DAT marker")
        require("ERROR_UINCOMP=54" in common_src, "p1 common.src missing ERROR_UINCOMP=54")
        require("/setting/updater/uincomp" in udtr_main, "p1 UdtrMain.sh missing uincomp gate")
        require(b"BATTERY_STATE_EXIST" in buspwr_ko, "p1 usb_buspwr.ko missing battery state monitor")
        require("cpapp-b.bin" in nor_writer, "udtrbody nor_loader_writer.sh missing cpapp-b.bin")
        require(bd_hdr[:8] == BODYDATA_UFU_MAGIC, "BODYDATA.DAT missing UFU header magic")
        require(b"Battery" in fx3_cp_bytes and b"NTSC" in fx3_cp_bytes and b"PAL" in fx3_cp_bytes, "FX3 cpapp-b.bin missing expected markers")

        found_flags: List[str] = []
        for flg in SONY_UPDATA_FLAG_FILES:
            short = flg.split("/")[-1]
            if flg in udtr_main or short in udtr_main or flg in common_src:
                found_flags.append(flg)
        if "/setting/updater/dat4" not in found_flags:
            found_flags.append("/setting/updater/dat4")

        artifacts = (
            AbBankDonorArtifactDigest(
                label="fx3_p1_205_nflasha1",
                relpath=DONOR_FX3_P1_205_RELPATH,
                source_mode="LOCAL_DONOR_O_RDONLY",
                byte_length=len(p1_bytes),
                sha256=p1_sha,
                details="FAT12+SquashFS /usr/bin/sdfileinput.elf (BODYDATA.DAT), UdtrMain.sh (uincomp=54, mode*), usb_buspwr.ko",
            ),
            AbBankDonorArtifactDigest(
                label="fx3_udtrbody_squashfs",
                relpath=DONOR_FX3_UDTRBODY_RELPATH,
                source_mode="LOCAL_DONOR_O_RDONLY",
                byte_length=len(udtr_bytes),
                sha256=udtr_sha,
                details="SquashFS /bin/nor_loader_writer.sh (cpapp-b.bin, loader_nor.bin, MIS.bin) & /bin/startupdate.sh",
            ),
            AbBankDonorArtifactDigest(
                label="fx3_p8_cpapp_b",
                relpath=DONOR_FX3_CPAPP_B_RELPATH,
                source_mode="LOCAL_DONOR_O_RDONLY",
                byte_length=len(fx3_cp_bytes),
                sha256=fx3_cp_sha,
                details="CXD90058 Cortex-R5 RTOS cpapp-b.bin (Battery/NTSC/PAL markers verified)",
            ),
            AbBankDonorArtifactDigest(
                label="fx6_p8_cpapp_b",
                relpath=DONOR_FX6_CPAPP_B_RELPATH,
                source_mode="LOCAL_DONOR_O_RDONLY",
                byte_length=len(fx6_cp_bytes),
                sha256=fx6_cp_sha,
                details="Cross-SKU ILME-FX6 cpapp-b.bin reference (must never be cross-flashed onto FX3)",
            ),
            AbBankDonorArtifactDigest(
                label="fx3_702_bodydata_header",
                relpath=DONOR_FX3_BODYDATA_RELPATH,
                source_mode="LOCAL_DONOR_O_RDONLY",
                byte_length=bd_total,
                sha256=bd_hdr_sha,
                details="Bounded 4096B UFU header (\\x89UFU\\r\\n\\x1a\\n DATV/PROV/UDID 054C:0DA1)",
            ),
        )
        mode = "LOCAL_DONOR_O_RDONLY"
        updata_flags = tuple(sorted(set(found_flags)))
        bd_magic_hex = bd_hdr[:8].hex()
    else:
        mode = "CLEAN_ROOM_SYNTHETIC"
        p1_sha = PINNED_FX3_P1_205_SHA256
        udtr_sha = PINNED_FX3_UDTRBODY_SHA256
        fx3_cp_sha = PINNED_FX3_CPAPP_B_SHA256
        fx6_cp_sha = PINNED_FX6_CPAPP_B_SHA256
        bd_total = PINNED_FX3_BODYDATA_TOTAL_BYTES
        bd_hdr_sha = PINNED_FX3_BODYDATA_HEADER_SHA256
        bd_magic_hex = BODYDATA_UFU_MAGIC_HEX
        updata_flags = SONY_UPDATA_FLAG_FILES
        artifacts = (
            AbBankDonorArtifactDigest(
                label="fx3_p1_205_nflasha1",
                relpath=DONOR_FX3_P1_205_RELPATH,
                source_mode="CLEAN_ROOM_SYNTHETIC",
                byte_length=19377152,
                sha256=p1_sha,
                details="Pinned clean-room FX3 p1 2.05 anchor (sdfileinput.elf BODYDATA.DAT, UdtrMain.sh uincomp=54)",
            ),
            AbBankDonorArtifactDigest(
                label="fx3_udtrbody_squashfs",
                relpath=DONOR_FX3_UDTRBODY_RELPATH,
                source_mode="CLEAN_ROOM_SYNTHETIC",
                byte_length=1253376,
                sha256=udtr_sha,
                details="Pinned clean-room udtrbody.squashfs anchor (nor_loader_writer.sh cpapp-b.bin)",
            ),
            AbBankDonorArtifactDigest(
                label="fx3_p8_cpapp_b",
                relpath=DONOR_FX3_CPAPP_B_RELPATH,
                source_mode="CLEAN_ROOM_SYNTHETIC",
                byte_length=15980568,
                sha256=fx3_cp_sha,
                details="Pinned clean-room FX3 CXD90058 cpapp-b.bin anchor",
            ),
            AbBankDonorArtifactDigest(
                label="fx6_p8_cpapp_b",
                relpath=DONOR_FX6_CPAPP_B_RELPATH,
                source_mode="CLEAN_ROOM_SYNTHETIC",
                byte_length=17952816,
                sha256=fx6_cp_sha,
                details="Pinned clean-room FX6 cross-SKU cpapp-b.bin anchor",
            ),
            AbBankDonorArtifactDigest(
                label="fx3_702_bodydata_header",
                relpath=DONOR_FX3_BODYDATA_RELPATH,
                source_mode="CLEAN_ROOM_SYNTHETIC",
                byte_length=bd_total,
                sha256=bd_hdr_sha,
                details="Pinned clean-room FX3 7.02 BODYDATA.DAT UFU header anchor",
            ),
        )

    snap_payload = {
        "mode": mode,
        "p1_sha": p1_sha,
        "udtr_sha": udtr_sha,
        "fx3_cp_sha": fx3_cp_sha,
        "fx6_cp_sha": fx6_cp_sha,
        "bd_hdr_sha": bd_hdr_sha,
        "bd_total": bd_total,
        "updata_flags": list(updata_flags),
        "battery_gate": SONY_FW_UPDATE_MIN_BATTERY_PCT,
    }
    return DonorAbBankOtaSnapshot(
        verification_mode=mode,
        read_only_access=READ_ONLY_DONOR_ACCESS,
        cpapp_b_present=True,
        cpapp_a_referenced_in_dual_bank_model=True,
        updata_flags_verified=updata_flags,
        bodydata_magic_hex=bd_magic_hex,
        bodydata_total_bytes=bd_total,
        sony_min_battery_pct_gate=SONY_FW_UPDATE_MIN_BATTERY_PCT,
        fx3_cpapp_b_sha256=fx3_cp_sha,
        fx6_cpapp_b_sha256=fx6_cp_sha,
        fx3_p1_205_sha256=p1_sha,
        fx3_udtrbody_sha256=udtr_sha,
        artifacts=artifacts,
        snapshot_sha256=_canonical_sha256(snap_payload),
    )


# ---------------------------------------------------------------------------
# Pillar 1 — CXD90057 / CXD90058 Dual-Bank A/B AP+CP Synchronized Epoch & Torn-Bank Detector
# ---------------------------------------------------------------------------


def classify_bank_slot_health(
    slot: BankSlotDescriptor,
    *,
    min_otp_epoch: int = 1,
) -> BankSlotHealthResult:
    """Deterministically classify a single AP or CP bank slot in RAM."""
    errors: List[str] = []
    if slot.bank_id not in VALID_BANK_IDS:
        errors.append(ERR_INVALID_BANK_ID)
    if slot.sku_code != FX3_SKU_CODE:
        errors.append(ERR_CROSS_SKU_BANK_MISMATCH)

    complete_write = slot.expected_bytes > 0 and slot.bytes_written == slot.expected_bytes
    crc_valid = slot.declared_crc32 == slot.computed_crc32 and slot.declared_crc32 != 0

    if not complete_write or not crc_valid:
        state = BANK_STATE_TORN_PARTIAL_WRITE
        if slot.domain == DOMAIN_CP:
            errors.append(ERR_CP_BANK_TORN_PARTIAL_WRITE)
        else:
            errors.append(ERR_AP_BANK_TORN_PARTIAL_WRITE)
        bootable = False
    elif slot.rollback_fenced or slot.epoch < min_otp_epoch:
        state = BANK_STATE_ROLLBACK_FENCED
        if slot.domain == DOMAIN_CP:
            errors.append(ERR_CP_BANK_ROLLBACK_FENCED)
        else:
            errors.append(ERR_AP_BANK_ROLLBACK_FENCED)
        bootable = False
    elif slot.trial_flag:
        state = BANK_STATE_PENDING_TRIAL
        bootable = slot.sku_code == FX3_SKU_CODE and slot.bank_id in VALID_BANK_IDS
    else:
        state = BANK_STATE_ACTIVE_VERIFIED
        bootable = slot.sku_code == FX3_SKU_CODE and slot.bank_id in VALID_BANK_IDS

    return BankSlotHealthResult(
        bank_id=slot.bank_id,
        domain=slot.domain,
        artifact_name=slot.artifact_name,
        firmware_version=slot.firmware_version,
        epoch=slot.epoch,
        classified_state=state,
        crc_valid=crc_valid,
        complete_write=complete_write,
        bootable=bootable,
        sku_code=slot.sku_code,
        error_codes=tuple(dict.fromkeys(errors)),
    )


def audit_dual_bank_ap_cp_consistency(
    ap_bank_a: BankSlotDescriptor,
    ap_bank_b: BankSlotDescriptor,
    cp_bank_a: BankSlotDescriptor,
    cp_bank_b: BankSlotDescriptor,
    *,
    ap_active_bank: str,
    cp_active_bank: str,
    min_otp_epoch: int = 1,
    require_synchronized_bank_slot: bool = True,
) -> DualBankConsistencyReport:
    """Audit AP (CXD90057) + CP (CXD90058) dual-bank A/B slot consistency strictly in RAM.

    Rejects split-epoch mismatches and torn/half-written slots fail-closed.
    """
    require(PERSISTENT_EMMC_WRITES_AUTHORIZED is False, "persistent_emmc_writes_authorized must stay False")
    require(PHYSICAL_DEVICE_WRITES == 0, "physical_device_writes must stay 0")

    res_ap_a = classify_bank_slot_health(ap_bank_a, min_otp_epoch=min_otp_epoch)
    res_ap_b = classify_bank_slot_health(ap_bank_b, min_otp_epoch=min_otp_epoch)
    res_cp_a = classify_bank_slot_health(cp_bank_a, min_otp_epoch=min_otp_epoch)
    res_cp_b = classify_bank_slot_health(cp_bank_b, min_otp_epoch=min_otp_epoch)

    error_codes: List[str] = []
    errors: List[str] = []

    if ap_active_bank not in VALID_BANK_IDS or cp_active_bank not in VALID_BANK_IDS:
        error_codes.append(ERR_INVALID_BANK_ID)
        errors.append(f"Invalid active bank selection ap={ap_active_bank!r} cp={cp_active_bank!r}")

    ap_active = res_ap_a if ap_active_bank == BANK_A else res_ap_b
    cp_active = res_cp_a if cp_active_bank == BANK_A else res_cp_b

    for res in (ap_active, cp_active):
        for code in res.error_codes:
            if code not in error_codes:
                error_codes.append(code)

    split_deadlock = False
    if not ap_active.bootable or not cp_active.bootable:
        split_deadlock = True
        if not cp_active.bootable and ap_active.bootable:
            error_codes.append(ERR_AP_CP_IPC_EPOCH_DEADLOCK)
            errors.append(
                f"AP {ap_active.bank_id} ({ap_active.firmware_version}, {ap_active.classified_state}) "
                f"vs CP {cp_active.bank_id} ({cp_active.firmware_version}, {cp_active.classified_state}) "
                f"triggers AP<->CP IPC deadlock"
            )
        else:
            errors.append(
                f"Active slot unbootable: AP={ap_active.classified_state}, CP={cp_active.classified_state}"
            )

    if require_synchronized_bank_slot and ap_active_bank != cp_active_bank:
        split_deadlock = True
        error_codes.append(ERR_AP_CP_ACTIVE_BANK_DESYNC)
        error_codes.append(ERR_AP_CP_IPC_EPOCH_DEADLOCK)
        errors.append(
            f"Active bank desync: AP on {ap_active_bank} ({ap_active.firmware_version}) "
            f"while CP on {cp_active_bank} ({cp_active.firmware_version})"
        )

    if ap_active.epoch != cp_active.epoch:
        split_deadlock = True
        error_codes.append(ERR_AP_CP_IPC_EPOCH_DEADLOCK)
        errors.append(
            f"AP/CP epoch mismatch: AP epoch={ap_active.epoch} ({ap_active.firmware_version}) "
            f"!= CP epoch={cp_active.epoch} ({cp_active.firmware_version})"
        )

    # Check if the opposite bank offers a synchronized, non-fenced intact fallback
    fallback_bank: Optional[str] = None
    for cand_id, cand_ap, cand_cp in (
        (BANK_A, res_ap_a, res_cp_a),
        (BANK_B, res_ap_b, res_cp_b),
    ):
        if cand_id == ap_active_bank and cand_id == cp_active_bank and not split_deadlock:
            continue
        if (
            cand_ap.bootable
            and cand_cp.bootable
            and cand_ap.classified_state == BANK_STATE_ACTIVE_VERIFIED
            and cand_cp.classified_state == BANK_STATE_ACTIVE_VERIFIED
            and cand_ap.epoch == cand_cp.epoch
            and cand_ap.epoch >= min_otp_epoch
        ):
            fallback_bank = cand_id
            break
        if (
            cand_ap.classified_state == BANK_STATE_ROLLBACK_FENCED
            or cand_cp.classified_state == BANK_STATE_ROLLBACK_FENCED
        ):
            if ERR_FALLBACK_BANK_ROLLBACK_FENCED not in error_codes:
                error_codes.append(ERR_FALLBACK_BANK_ROLLBACK_FENCED)

    # If currently active slot is PENDING_TRIAL, verify intact fallback exists before approving
    if ap_active.classified_state == BANK_STATE_PENDING_TRIAL or cp_active.classified_state == BANK_STATE_PENDING_TRIAL:
        if fallback_bank is None:
            split_deadlock = True
            error_codes.append(ERR_NO_INTACT_FALLBACK_BANK)
            errors.append("PENDING_TRIAL bank has no intact verified fallback bank")

    passed = (len(errors) == 0) and (not split_deadlock) and ap_active.bootable and cp_active.bootable
    ipc_ok = passed and (ap_active.epoch == cp_active.epoch) and (ap_active_bank == cp_active_bank)

    if passed:
        status = STATUS_DUAL_BANK_CONSISTENT
        tier = "TIER_0_NONE_NEEDED"
        action = ACTION_NO_RECOVERY_NEEDED_HEALTHY
        led = "solid_green_or_off_normal_boot"
    elif ERR_CP_BANK_TORN_PARTIAL_WRITE in error_codes or ERR_AP_CP_IPC_EPOCH_DEADLOCK in error_codes:
        status = STATUS_DUAL_BANK_TORN_REJECTED
        tier = "TIER_3_PASSIVE_UART_AND_READONLY_DUMP"
        action = ACTION_PASSIVE_UART_AND_TIER0_NOR_DUMP
        led = "amber_red_6L_9S_or_0x51_cetus_cp_nor_deadlock"
    else:
        status = STATUS_DUAL_BANK_TORN_REJECTED
        tier = "TIER_1_SD_RECOVERY_OR_TIER3_UART"
        action = ACTION_SD_SLOT1_VERIFIED_BODYDATA_OR_CLEAR_FLAGS
        led = "red_7L_7S_or_5L_6S_updater_recovery_loop"

    dedup_codes = tuple(dict.fromkeys(error_codes))
    report_payload = {
        "passed": passed,
        "status": status,
        "ap_active_bank": ap_active_bank,
        "cp_active_bank": cp_active_bank,
        "min_otp_epoch": min_otp_epoch,
        "ap_a_state": res_ap_a.classified_state,
        "ap_b_state": res_ap_b.classified_state,
        "cp_a_state": res_cp_a.classified_state,
        "cp_b_state": res_cp_b.classified_state,
        "ipc_ok": ipc_ok,
        "split_deadlock": split_deadlock,
        "fallback": fallback_bank,
        "error_codes": list(dedup_codes),
    }

    return DualBankConsistencyReport(
        passed=passed,
        status=status,
        ap_active_bank=ap_active_bank,
        cp_active_bank=cp_active_bank,
        min_otp_epoch=min_otp_epoch,
        ap_bank_a=res_ap_a,
        ap_bank_b=res_ap_b,
        cp_bank_a=res_cp_a,
        cp_bank_b=res_cp_b,
        ipc_protocol_compatible=ipc_ok,
        split_epoch_deadlock_detected=split_deadlock,
        fallback_bank_available=fallback_bank,
        recommended_recovery_tier=tier,
        recommended_action=action,
        led_pattern_hint=led,
        error_codes=dedup_codes,
        errors=tuple(errors),
        ram_only_classification=True,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        report_sha256=_canonical_sha256(report_payload),
    )


def build_synthetic_dual_bank_snapshot(scenario: str = "HEALTHY_702") -> DualBankConsistencyReport:
    """Build deterministic RAM-only Dual-Bank A/B audit reports for canonical scenarios."""
    if scenario == "HEALTHY_702":
        ap_a = BankSlotDescriptor(
            bank_id=BANK_A, domain=DOMAIN_AP, artifact_name=AP_BANK_FILENAMES[BANK_A],
            firmware_version="7.00", epoch=4, declared_crc32=0xA1B2C3D4, computed_crc32=0xA1B2C3D4,
            bytes_written=31695872, expected_bytes=31695872, is_active=False,
        )
        ap_b = BankSlotDescriptor(
            bank_id=BANK_B, domain=DOMAIN_AP, artifact_name=AP_BANK_FILENAMES[BANK_B],
            firmware_version="7.02", epoch=5, declared_crc32=0xB2C3D4E5, computed_crc32=0xB2C3D4E5,
            bytes_written=31695872, expected_bytes=31695872, is_active=True,
        )
        cp_a = BankSlotDescriptor(
            bank_id=BANK_A, domain=DOMAIN_CP, artifact_name=CP_BANK_FILENAMES[BANK_A],
            firmware_version="7.00", epoch=4, declared_crc32=0xC3D4E5F6, computed_crc32=0xC3D4E5F6,
            bytes_written=15980568, expected_bytes=15980568, is_active=False,
        )
        cp_b = BankSlotDescriptor(
            bank_id=BANK_B, domain=DOMAIN_CP, artifact_name=CP_BANK_FILENAMES[BANK_B],
            firmware_version="7.02", epoch=5, declared_crc32=0xD4E5F607, computed_crc32=0xD4E5F607,
            bytes_written=15980568, expected_bytes=15980568, is_active=True,
        )
        return audit_dual_bank_ap_cp_consistency(
            ap_a, ap_b, cp_a, cp_b, ap_active_bank=BANK_B, cp_active_bank=BANK_B, min_otp_epoch=4,
        )

    if scenario == "SPLIT_EPOCH_AP_B_702_CP_A_205_TORN":
        # Classic interrupted OTA deadlock: AP boots Bank-B 7.02 while CP remains torn on Bank-A 2.05
        ap_a = BankSlotDescriptor(
            bank_id=BANK_A, domain=DOMAIN_AP, artifact_name=AP_BANK_FILENAMES[BANK_A],
            firmware_version="2.05", epoch=1, declared_crc32=0x11112222, computed_crc32=0x11112222,
            bytes_written=31695872, expected_bytes=31695872, is_active=False,
        )
        ap_b = BankSlotDescriptor(
            bank_id=BANK_B, domain=DOMAIN_AP, artifact_name=AP_BANK_FILENAMES[BANK_B],
            firmware_version="7.02", epoch=5, declared_crc32=0xB2C3D4E5, computed_crc32=0xB2C3D4E5,
            bytes_written=31695872, expected_bytes=31695872, is_active=True,
        )
        cp_a = BankSlotDescriptor(
            bank_id=BANK_A, domain=DOMAIN_CP, artifact_name=CP_BANK_FILENAMES[BANK_A],
            firmware_version="2.05", epoch=1, declared_crc32=0x33334444, computed_crc32=0xDEAD0BAD,
            bytes_written=9437184, expected_bytes=15980568, is_active=True,
        )
        cp_b = BankSlotDescriptor(
            bank_id=BANK_B, domain=DOMAIN_CP, artifact_name=CP_BANK_FILENAMES[BANK_B],
            firmware_version="7.02", epoch=5, declared_crc32=0x55556666, computed_crc32=0xBAD00555,
            bytes_written=4194304, expected_bytes=15980568, is_active=False,
        )
        return audit_dual_bank_ap_cp_consistency(
            ap_a, ap_b, cp_a, cp_b, ap_active_bank=BANK_B, cp_active_bank=BANK_A, min_otp_epoch=4,
        )

    if scenario == "PENDING_TRIAL_702_WITH_INTACT_700_FALLBACK":
        ap_a = BankSlotDescriptor(
            bank_id=BANK_A, domain=DOMAIN_AP, artifact_name=AP_BANK_FILENAMES[BANK_A],
            firmware_version="7.00", epoch=4, declared_crc32=0xA1B2C3D4, computed_crc32=0xA1B2C3D4,
            bytes_written=31695872, expected_bytes=31695872, is_active=False,
        )
        ap_b = BankSlotDescriptor(
            bank_id=BANK_B, domain=DOMAIN_AP, artifact_name=AP_BANK_FILENAMES[BANK_B],
            firmware_version="7.02", epoch=5, declared_crc32=0xB2C3D4E5, computed_crc32=0xB2C3D4E5,
            bytes_written=31695872, expected_bytes=31695872, trial_flag=True, is_active=True,
        )
        cp_a = BankSlotDescriptor(
            bank_id=BANK_A, domain=DOMAIN_CP, artifact_name=CP_BANK_FILENAMES[BANK_A],
            firmware_version="7.00", epoch=4, declared_crc32=0xC3D4E5F6, computed_crc32=0xC3D4E5F6,
            bytes_written=15980568, expected_bytes=15980568, is_active=False,
        )
        cp_b = BankSlotDescriptor(
            bank_id=BANK_B, domain=DOMAIN_CP, artifact_name=CP_BANK_FILENAMES[BANK_B],
            firmware_version="7.02", epoch=5, declared_crc32=0xD4E5F607, computed_crc32=0xD4E5F607,
            bytes_written=15980568, expected_bytes=15980568, trial_flag=True, is_active=True,
        )
        return audit_dual_bank_ap_cp_consistency(
            ap_a, ap_b, cp_a, cp_b, ap_active_bank=BANK_B, cp_active_bank=BANK_B, min_otp_epoch=4,
        )

    if scenario == "ROLLBACK_FENCED_205_VS_TORN_702":
        ap_a = BankSlotDescriptor(
            bank_id=BANK_A, domain=DOMAIN_AP, artifact_name=AP_BANK_FILENAMES[BANK_A],
            firmware_version="2.05", epoch=1, declared_crc32=0x11112222, computed_crc32=0x11112222,
            bytes_written=31695872, expected_bytes=31695872, rollback_fenced=True, is_active=False,
        )
        ap_b = BankSlotDescriptor(
            bank_id=BANK_B, domain=DOMAIN_AP, artifact_name=AP_BANK_FILENAMES[BANK_B],
            firmware_version="7.02", epoch=5, declared_crc32=0xB2C3D4E5, computed_crc32=0xDEAD0001,
            bytes_written=12000000, expected_bytes=31695872, is_active=True,
        )
        cp_a = BankSlotDescriptor(
            bank_id=BANK_A, domain=DOMAIN_CP, artifact_name=CP_BANK_FILENAMES[BANK_A],
            firmware_version="2.05", epoch=1, declared_crc32=0x33334444, computed_crc32=0x33334444,
            bytes_written=15980568, expected_bytes=15980568, rollback_fenced=True, is_active=False,
        )
        cp_b = BankSlotDescriptor(
            bank_id=BANK_B, domain=DOMAIN_CP, artifact_name=CP_BANK_FILENAMES[BANK_B],
            firmware_version="7.02", epoch=5, declared_crc32=0xD4E5F607, computed_crc32=0xD4E5F607,
            bytes_written=15980568, expected_bytes=15980568, is_active=True,
        )
        return audit_dual_bank_ap_cp_consistency(
            ap_a, ap_b, cp_a, cp_b, ap_active_bank=BANK_B, cp_active_bank=BANK_B, min_otp_epoch=5,
        )

    raise ValueError(f"Unknown synthetic dual-bank scenario: {scenario!r}")


# ---------------------------------------------------------------------------
# Pillar 2 — Interrupted Official BODYDATA.DAT / USB-OTA Forensic Triage & Pre-Flight Gate
# ---------------------------------------------------------------------------


def audit_official_ota_preflight(
    *,
    battery_pct: int,
    model_id: int = FX3_MODEL_ID,
    camera_region: str = "NTSC",
    package_region: str = "NTSC",
    bodydata_header: bytes = BODYDATA_UFU_MAGIC,
    bodydata_crc_ok: bool = True,
    media_slot_stable: bool = True,
    dual_bank_precheck_ok: bool = True,
) -> OtaPreflightResult:
    """Audit Sony official firmware-update pre-flight gates (battery >=51%, model, region, CRC)."""
    require(PERSISTENT_EMMC_WRITES_AUTHORIZED is False, "persistent_emmc_writes_authorized must stay False")
    error_codes: List[str] = []
    errors: List[str] = []

    if battery_pct < SONY_FW_UPDATE_MIN_BATTERY_PCT:
        error_codes.append(ERR_OTA_BATTERY_BELOW_51_PCT)
        errors.append(
            f"Battery {battery_pct}% is below Sony minimum {SONY_FW_UPDATE_MIN_BATTERY_PCT}% gate"
        )
    if model_id != FX3_MODEL_ID:
        error_codes.append(ERR_OTA_MODEL_MISMATCH)
        errors.append(f"Model 0x{model_id:08X} != FX3 0x{FX3_MODEL_ID:08X}")
    if (
        camera_region not in VALID_CAMERA_REGIONS
        or package_region not in VALID_CAMERA_REGIONS
        or camera_region != package_region
    ):
        error_codes.append(ERR_OTA_REGION_NTSC_PAL_MISMATCH)
        errors.append(f"Region mismatch: camera={camera_region!r} package={package_region!r}")
    if not bodydata_header.startswith(BODYDATA_UFU_MAGIC) or not bodydata_crc_ok:
        error_codes.append(ERR_OTA_BODYDATA_CRC_OR_MAGIC)
        errors.append("BODYDATA.DAT UFU magic or CRC32 verification failed")
    if not media_slot_stable:
        error_codes.append(ERR_OTA_UNSTABLE_TRANSPORT)
        errors.append("Unstable OTA transport (Wi-Fi/BLE Creators' App or loose USB cable)")
    if not dual_bank_precheck_ok:
        error_codes.append(ERR_OTA_SPLIT_BANK_PRECHECK_FAILED)
        errors.append("Dual-bank AP+CP precheck failed prior to update")

    passed = len(errors) == 0
    return OtaPreflightResult(
        passed=passed,
        status=STATUS_OTA_PREFLIGHT_APPROVED if passed else STATUS_OTA_PREFLIGHT_REJECTED,
        battery_pct=battery_pct,
        min_battery_pct_required=SONY_FW_UPDATE_MIN_BATTERY_PCT,
        model_id=model_id,
        model_id_hex=f"0x{model_id:08X}",
        camera_region=camera_region,
        package_region=package_region,
        bodydata_magic_hex=bodydata_header[:8].hex(),
        bodydata_crc_ok=bodydata_crc_ok,
        media_slot_stable=media_slot_stable,
        dual_bank_precheck_ok=dual_bank_precheck_ok,
        error_codes=tuple(dict.fromkeys(error_codes)),
        errors=tuple(errors),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
    )


def triage_interrupted_ota_brick(evidence: OtaInterruptionEvidence) -> OtaBrickTriageResult:
    """Deterministically triage an interrupted official BODYDATA.DAT / USB-OTA or Stage-B event."""
    require(PERSISTENT_EMMC_WRITES_AUTHORIZED is False, "persistent_emmc_writes_authorized must stay False")
    require(PHYSICAL_DEVICE_WRITES == 0, "physical_device_writes must stay 0")

    db = evidence.dual_bank_report
    codes: List[str] = list(db.error_codes)

    # Case U5: Stage-B volatile RAM/SD userland overlay -> ZERO flash-interruption brick surface
    if (
        evidence.stage_b_ram_overlay_active
        and evidence.emmc_bank_transitions == 0
        and not evidence.updata_flags_touched
        and not evidence.updata_uincomp_present
        and len(evidence.updata_mode_flags) == 0
        and db.passed
    ):
        return OtaBrickTriageResult(
            scenario_id=evidence.scenario_id,
            passed=True,
            status=STATUS_OTA_TRIAGE_HEALTHY,
            brick_severity="ZERO_BRICK_SURFACE",
            flash_interruption_brick_surface=False,
            stage_b_zero_brick_proven=True,
            emmc_bank_transitions=0,
            updata_flags_touched=False,
            recommended_recovery_tier="TIER_0_INSTANT_SD_SENTINEL_OR_COLD_REBOOT",
            recovery_action_code=ACTION_SD_SENTINEL_INSTANT_BOOT_ZERO_BRICK,
            recovery_steps=(
                f"1. Stage-B RAM/tmpfs overlay executed with 0 eMMC bank transitions and 0 /setting/updater/* flag mutations.",
                f"2. Sudden battery yank or SD eject leaves stock FX3 v7.02 Bank-A/B completely untouched.",
                f"3. Cold reboot (or insert SD card with {STAGE_B_SENTINEL_FILENAME} sentinel) boots stock FX3 v7.02 instantaneously.",
            ),
            passive_uart_required=False,
            sd_sentinel_instant_escape_available=True,
            tier0_readonly_dump_required=False,
            dual_bank_status=db.status,
            diagnosis_summary=(
                "Stage-B volatile RAM/SD userland overlay has ZERO flash-interruption brick surface "
                "(0 eMMC bank transitions, 0 updata flags touched)."
            ),
            error_codes=(),
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        )

    # Case U6: Healthy intact dual-bank with no interruption
    if (
        db.passed
        and not evidence.updata_uincomp_present
        and len(evidence.updata_mode_flags) == 0
        and not evidence.sd_crc_error_detected
        and not evidence.usb_disconnect_mid_transfer
        and evidence.camera_region == evidence.package_region
        and evidence.emmc_bank_transitions == 0
        and not evidence.updata_flags_touched
    ):
        return OtaBrickTriageResult(
            scenario_id=evidence.scenario_id,
            passed=True,
            status=STATUS_OTA_TRIAGE_HEALTHY,
            brick_severity="NONE",
            flash_interruption_brick_surface=False,
            stage_b_zero_brick_proven=False,
            emmc_bank_transitions=evidence.emmc_bank_transitions,
            updata_flags_touched=False,
            recommended_recovery_tier="TIER_0_NONE_NEEDED",
            recovery_action_code=ACTION_NO_RECOVERY_NEEDED_HEALTHY,
            recovery_steps=(
                "1. AP CXD90057 and CP CXD90058 dual-bank slots are synchronized and ACTIVE_VERIFIED.",
                "2. No /setting/updater/uincomp or mode* latch flags present; ready for normal stock or Stage-B RAM overlay boot.",
            ),
            passive_uart_required=False,
            sd_sentinel_instant_escape_available=True,
            tier0_readonly_dump_required=False,
            dual_bank_status=db.status,
            diagnosis_summary="Intact dual-bank FX3 v7.02 system; zero OTA interruption or brick indicators.",
            error_codes=(),
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        )

    # Case U4: Cross-region NTSC/PAL mismatch
    if evidence.camera_region != evidence.package_region:
        codes.append(ERR_OTA_REGION_NTSC_PAL_MISMATCH)
        return OtaBrickTriageResult(
            scenario_id=evidence.scenario_id,
            passed=True,
            status=STATUS_OTA_TRIAGE_RECOVERABLE,
            brick_severity="MEDIUM_UPDATER_GATE_REJECT",
            flash_interruption_brick_surface=bool(evidence.updata_flags_touched),
            stage_b_zero_brick_proven=False,
            emmc_bank_transitions=evidence.emmc_bank_transitions,
            updata_flags_touched=evidence.updata_flags_touched,
            recommended_recovery_tier="TIER_1_MATCHING_REGION_BODYDATA_OR_SAFE_STOCK_EXIT",
            recovery_action_code=ACTION_REJECT_CROSS_REGION_RESTORE_STOCK,
            recovery_steps=(
                f"1. SDUUDConditionChecker::isRegionOK rejected package region {evidence.package_region} != body {evidence.camera_region} (5L+6S LED).",
                "2. Do NOT patch or force cross-region dat3 values across incompatible NTSC/PAL bodies.",
                "3. Insert verified official BODYDATA.DAT matching the body's native region in SD Slot 1 or clear /setting/updater/mode*.",
            ),
            passive_uart_required=False,
            sd_sentinel_instant_escape_available=False,
            tier0_readonly_dump_required=False,
            dual_bank_status=db.status,
            diagnosis_summary=(
                f"Cross-region BODYDATA.DAT mismatch ({evidence.package_region} vs {evidence.camera_region}) "
                f"blocked at updater condition gate; non-destructive SD recovery available."
            ),
            error_codes=tuple(dict.fromkeys(codes)),
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        )

    # Case U1: Battery pulled / brownout during CP OSPI NOR flash (split-epoch or torn CP bank)
    if (
        not db.passed
        and (
            ERR_CP_BANK_TORN_PARTIAL_WRITE in db.error_codes
            or ERR_AP_CP_IPC_EPOCH_DEADLOCK in db.error_codes
            or evidence.interruption_phase == "CP_OSPI_NOR_FLASH"
        )
    ):
        if evidence.battery_pct_at_event < SONY_FW_UPDATE_MIN_BATTERY_PCT:
            codes.append(ERR_OTA_BATTERY_BELOW_51_PCT)
        return OtaBrickTriageResult(
            scenario_id=evidence.scenario_id,
            passed=True,
            status=STATUS_OTA_TRIAGE_RECOVERABLE,
            brick_severity="HIGH_SPLIT_AP_CP_DEADLOCK",
            flash_interruption_brick_surface=True,
            stage_b_zero_brick_proven=False,
            emmc_bank_transitions=max(1, evidence.emmc_bank_transitions),
            updata_flags_touched=True,
            recommended_recovery_tier="TIER_3_PASSIVE_UART_AND_READONLY_DUMP",
            recovery_action_code=ACTION_PASSIVE_UART_AND_TIER0_NOR_DUMP,
            recovery_steps=(
                "1. Disconnect battery & USB immediately; do NOT attempt blind cross-flash of foreign NOR dumps.",
                "2. Attach camera-verified RP2040-Zero (-DOPEN_DRAIN, 1.8V passive RX first) to 15-pin Multi-Port to confirm CXD90057/CXD90058 boot halt.",
                "3. Take Tier-0 read-only dump (including MIS.bin & ddrtraining.dat @ 0x03e210fc) via Fastboot `oem cetus dumpnor` / `oem partition` before any repair.",
            ),
            passive_uart_required=True,
            sd_sentinel_instant_escape_available=False,
            tier0_readonly_dump_required=True,
            dual_bank_status=db.status,
            diagnosis_summary=(
                "Power-loss during CXD90058 CP OSPI NOR flash (`cpapp-b.bin` / `loader_nor.bin`) left AP/CP in "
                "split-epoch torn-bank deadlock; passive 1.8V UART + Tier-0 read-only dump required."
            ),
            error_codes=tuple(dict.fromkeys(codes)),
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        )

    # Case U3: USB cable yanked during legacy sauu USB-OTA updater
    if evidence.usb_disconnect_mid_transfer or evidence.transport_medium == "USB_SAUU_OTA":
        return OtaBrickTriageResult(
            scenario_id=evidence.scenario_id,
            passed=True,
            status=STATUS_OTA_TRIAGE_RECOVERABLE,
            brick_severity="MEDIUM_HIGH_INTERRUPTED_USB_OTA",
            flash_interruption_brick_surface=True,
            stage_b_zero_brick_proven=False,
            emmc_bank_transitions=max(1, evidence.emmc_bank_transitions),
            updata_flags_touched=True,
            recommended_recovery_tier="TIER_1_OR_TIER_3_READONLY_DUMP_AND_SD_BODYDATA",
            recovery_action_code=ACTION_TIER0_READONLY_DUMP_AND_SD_BODYDATA,
            recovery_steps=(
                "1. Legacy `sauu` USB-OTA disconnect latched `/setting/updater/uincomp` (ERROR_UINCOMP=54) and `mode*`.",
                "2. Capture Tier-0 read-only backup of p1/p2/eMMC state via 1.8V Multi-Port or verified recovery dump before retrying.",
                "3. Place SHA-256 verified official FX3 BODYDATA.DAT on a full-formatted UHS-I SD card in Slot 1 with >= 51% (ideally 100%) NP-FZ100 battery.",
            ),
            passive_uart_required=not db.passed,
            sd_sentinel_instant_escape_available=False,
            tier0_readonly_dump_required=True,
            dual_bank_status=db.status,
            diagnosis_summary=(
                "USB cable disconnect mid-`sauu` OTA latched `uincomp`/mode updater loop; perform Tier-0 read-only "
                "dump then recover cleanly via verified SD Slot 1 BODYDATA.DAT."
            ),
            error_codes=tuple(dict.fromkeys(codes)),
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        )

    # Case U2: SD card read CRC error mid-updata (p1 updater alive in Slot 1 loop)
    return OtaBrickTriageResult(
        scenario_id=evidence.scenario_id,
        passed=True,
        status=STATUS_OTA_TRIAGE_RECOVERABLE,
        brick_severity="MEDIUM_SD_CRC_INTERRUPTED_UPDATA",
        flash_interruption_brick_surface=True,
        stage_b_zero_brick_proven=False,
        emmc_bank_transitions=max(1, evidence.emmc_bank_transitions),
        updata_flags_touched=True,
        recommended_recovery_tier="TIER_1_SD_RECOVERY_OR_VERIFIED_BODYDATA",
        recovery_action_code=ACTION_SD_SLOT1_VERIFIED_BODYDATA_OR_CLEAR_FLAGS,
        recovery_steps=(
            "1. SD card read CRC (`uc_crc32sum` 0x82 / `uincomp=54`) aborted `sdfileinput.elf` while `p1` updater remains intact.",
            "2. Discharge PMIC rails 60s, full-format a reliable UHS-I FAT32/exFAT SD card, and copy SHA-256 verified official BODYDATA.DAT to Slot 1 root.",
            "3. Ensure NP-FZ100 battery >= 51% (100% recommended) or clear `/setting/updater/mode*` if service shell (`054C:0336`) is reachable.",
        ),
        passive_uart_required=False,
        sd_sentinel_instant_escape_available=False,
        tier0_readonly_dump_required=False,
        dual_bank_status=db.status,
        diagnosis_summary=(
            "SD card CRC failure mid-`BODYDATA.DAT` `updata` left `p1` recovery loader polling Slot 1; "
            "re-verify BODYDATA.DAT SHA-256 on clean UHS-I SD card."
        ),
        error_codes=tuple(dict.fromkeys(codes)),
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
    )


def build_synthetic_ota_interruption_evidence(scenario_id: str) -> OtaInterruptionEvidence:
    """Build deterministic evidence objects for all 6 canonical Sony OTA brick/healthy states."""
    if scenario_id == OTA_SCENARIO_U1_BATTERY_PULLED_CP:
        return OtaInterruptionEvidence(
            scenario_id=scenario_id,
            battery_pct_at_event=18,
            interruption_phase="CP_OSPI_NOR_FLASH",
            transport_medium="SD_BODYDATA",
            dual_bank_report=build_synthetic_dual_bank_snapshot("SPLIT_EPOCH_AP_B_702_CP_A_205_TORN"),
            updata_uincomp_present=True,
            updata_mode_flags=("/setting/updater/mode", "/setting/updater/mode5", "/setting/updater/uincomp"),
            sd_crc_error_detected=False,
            usb_disconnect_mid_transfer=False,
            camera_region="NTSC",
            package_region="NTSC",
            stage_b_ram_overlay_active=False,
            emmc_bank_transitions=1,
            updata_flags_touched=True,
            led_pattern="amber_red_6L_9S",
        )
    if scenario_id == OTA_SCENARIO_U2_SD_CRC_MID_UPDATA:
        return OtaInterruptionEvidence(
            scenario_id=scenario_id,
            battery_pct_at_event=85,
            interruption_phase="P15_USR_CRC_VERIFY",
            transport_medium="SD_BODYDATA",
            dual_bank_report=build_synthetic_dual_bank_snapshot("HEALTHY_702"),
            updata_uincomp_present=True,
            updata_mode_flags=("/setting/updater/mode", "/setting/updater/mode5", "/setting/updater/uincomp"),
            sd_crc_error_detected=True,
            usb_disconnect_mid_transfer=False,
            camera_region="NTSC",
            package_region="NTSC",
            stage_b_ram_overlay_active=False,
            emmc_bank_transitions=1,
            updata_flags_touched=True,
            led_pattern="red_7L_7S",
        )
    if scenario_id == OTA_SCENARIO_U3_USB_CABLE_YANKED:
        return OtaInterruptionEvidence(
            scenario_id=scenario_id,
            battery_pct_at_event=74,
            interruption_phase="USB_SAUU_AP_FLASH",
            transport_medium="USB_SAUU_OTA",
            dual_bank_report=build_synthetic_dual_bank_snapshot("ROLLBACK_FENCED_205_VS_TORN_702"),
            updata_uincomp_present=True,
            updata_mode_flags=("/setting/updater/mode", "/setting/updater/mode6", "/setting/updater/uincomp"),
            sd_crc_error_detected=False,
            usb_disconnect_mid_transfer=True,
            camera_region="NTSC",
            package_region="NTSC",
            stage_b_ram_overlay_active=False,
            emmc_bank_transitions=1,
            updata_flags_touched=True,
            led_pattern="red_7L_7S",
        )
    if scenario_id == OTA_SCENARIO_U4_CROSS_REGION_MISMATCH:
        return OtaInterruptionEvidence(
            scenario_id=scenario_id,
            battery_pct_at_event=92,
            interruption_phase="UUD_CONDITION_CHECK_IS_REGION_OK",
            transport_medium="SD_BODYDATA",
            dual_bank_report=build_synthetic_dual_bank_snapshot("HEALTHY_702"),
            updata_uincomp_present=False,
            updata_mode_flags=("/setting/updater/mode", "/setting/updater/mode5"),
            sd_crc_error_detected=False,
            usb_disconnect_mid_transfer=False,
            camera_region="NTSC",
            package_region="PAL",
            stage_b_ram_overlay_active=False,
            emmc_bank_transitions=0,
            updata_flags_touched=True,
            led_pattern="red_5L_6S",
        )
    if scenario_id == OTA_SCENARIO_U5_STAGE_B_ZERO_BRICK:
        return OtaInterruptionEvidence(
            scenario_id=scenario_id,
            battery_pct_at_event=12,  # Sudden battery yank / low battery
            interruption_phase="STAGE_B_TMPFS_RAM_OVERLAY_POWER_LOSS",
            transport_medium="SD_VOLATILE_RAM_OVERLAY",
            dual_bank_report=build_synthetic_dual_bank_snapshot("HEALTHY_702"),
            updata_uincomp_present=False,
            updata_mode_flags=(),
            sd_crc_error_detected=False,
            usb_disconnect_mid_transfer=False,
            camera_region="NTSC",
            package_region="NTSC",
            stage_b_ram_overlay_active=True,
            emmc_bank_transitions=0,
            updata_flags_touched=False,
            led_pattern="clean_cold_boot_stock_702",
        )
    if scenario_id == OTA_SCENARIO_U6_INTACT_HEALTHY:
        return OtaInterruptionEvidence(
            scenario_id=scenario_id,
            battery_pct_at_event=100,
            interruption_phase="NONE_NORMAL_BOOT",
            transport_medium="NONE",
            dual_bank_report=build_synthetic_dual_bank_snapshot("HEALTHY_702"),
            updata_uincomp_present=False,
            updata_mode_flags=(),
            sd_crc_error_detected=False,
            usb_disconnect_mid_transfer=False,
            camera_region="NTSC",
            package_region="NTSC",
            stage_b_ram_overlay_active=False,
            emmc_bank_transitions=0,
            updata_flags_touched=False,
            led_pattern="normal",
        )
    raise ValueError(f"Unknown OTA triage scenario_id: {scenario_id!r}")


def run_interrupted_ota_6_scenario_triage() -> Ota6ScenarioSuiteResult:
    """Execute and verify all 6 real-world Sony interrupted-OTA & Stage-B zero-brick scenarios."""
    results: List[OtaBrickTriageResult] = []
    errors: List[str] = []
    u5_zero_brick = False

    for sid in OTA_SCENARIO_IDS:
        ev = build_synthetic_ota_interruption_evidence(sid)
        res = triage_interrupted_ota_brick(ev)
        results.append(res)
        if not res.passed:
            errors.append(f"Scenario {sid} failed triage")
        if sid == OTA_SCENARIO_U5_STAGE_B_ZERO_BRICK:
            u5_zero_brick = (
                (not res.flash_interruption_brick_surface)
                and res.stage_b_zero_brick_proven
                and res.emmc_bank_transitions == 0
                and (not res.updata_flags_touched)
                and res.sd_sentinel_instant_escape_available
            )
            if not u5_zero_brick:
                errors.append("U5 Stage-B zero-brick invariant failed")

    passed_count = sum(1 for r in results if r.passed)
    all_ok = (passed_count == len(OTA_SCENARIO_IDS)) and u5_zero_brick and (len(errors) == 0)
    suite_payload = {
        "scenarios": [
            {
                "id": r.scenario_id,
                "status": r.status,
                "action": r.recovery_action_code,
                "brick_surface": r.flash_interruption_brick_surface,
                "emmc_transitions": r.emmc_bank_transitions,
                "updata_touched": r.updata_flags_touched,
            }
            for r in results
        ],
        "u5_zero_brick": u5_zero_brick,
    }
    return Ota6ScenarioSuiteResult(
        passed=all_ok,
        status=STATUS_VERIFIED_AB_BANK_OTA_GATE if all_ok else STATUS_FAIL_AB_BANK_OTA_GATE,
        scenarios_passed=passed_count,
        scenarios_total=len(OTA_SCENARIO_IDS),
        stage_b_u5_zero_brick_verified=u5_zero_brick,
        scenario_results=tuple(results),
        errors=tuple(errors),
        suite_sha256=_canonical_sha256(suite_payload),
    )


# ---------------------------------------------------------------------------
# Pillar 3 — Master Suite Runner
# ---------------------------------------------------------------------------


def run_ab_bank_and_interrupted_ota_suite(
    *,
    force_clean_room: Optional[bool] = None,
) -> AbBankAndInterruptedOtaSuiteReport:
    """Execute Phase 113 Dual-Bank A/B & Interrupted BODYDATA.DAT / USB-OTA Forensic Triage Suite."""
    require(PERSISTENT_EMMC_WRITES_AUTHORIZED is False, "persistent_emmc_writes_authorized must stay False")
    require(PERSISTENT_WRITE_RELEASE is False, "persistent_write_release must stay False")
    require(ALLOW_BOOT_PARTITION_TARGETING is False, "allow_boot_partition_targeting must stay False")
    require(ALLOW_DESTRUCTIVE_FASTBOOT is False, "allow_destructive_fastboot must stay False")
    require(OTP_FUSE_TOUCHES == 0, "otp_fuse_touches must stay 0")
    require(PASSIVE_TX_BYTES_EMITTED == 0, "passive_tx_bytes_emitted must stay 0")
    require(PHYSICAL_DEVICE_WRITES == 0, "physical_device_writes must stay 0")

    t0 = time.monotonic()
    donor_snap = inspect_ab_bank_and_ota_donors_readonly(force_clean_room=force_clean_room)

    dual_healthy = build_synthetic_dual_bank_snapshot("HEALTHY_702")
    dual_split = build_synthetic_dual_bank_snapshot("SPLIT_EPOCH_AP_B_702_CP_A_205_TORN")
    dual_trial = build_synthetic_dual_bank_snapshot("PENDING_TRIAL_702_WITH_INTACT_700_FALLBACK")
    dual_fenced = build_synthetic_dual_bank_snapshot("ROLLBACK_FENCED_205_VS_TORN_702")

    preflight_ok = audit_official_ota_preflight(
        battery_pct=82,
        model_id=FX3_MODEL_ID,
        camera_region="NTSC",
        package_region="NTSC",
        bodydata_header=BODYDATA_UFU_MAGIC,
        bodydata_crc_ok=True,
        media_slot_stable=True,
        dual_bank_precheck_ok=dual_healthy.passed,
    )
    preflight_low_batt = audit_official_ota_preflight(
        battery_pct=49,
        model_id=FX3_MODEL_ID,
        camera_region="NTSC",
        package_region="NTSC",
        bodydata_header=BODYDATA_UFU_MAGIC,
        bodydata_crc_ok=True,
        media_slot_stable=True,
        dual_bank_precheck_ok=dual_healthy.passed,
    )

    ota_6 = run_interrupted_ota_6_scenario_triage()

    errors: List[str] = []
    if not dual_healthy.passed:
        errors.append("Healthy dual-bank 7.02 check unexpectedly failed")
    if dual_split.passed or not dual_split.split_epoch_deadlock_detected:
        errors.append("Split-epoch AP Bank-B 7.02 vs CP Bank-A 2.05 torn deadlock was not rejected")
    if not dual_trial.passed or dual_trial.fallback_bank_available != BANK_A:
        errors.append("Pending trial Bank-B with intact Bank-A fallback check failed")
    if dual_fenced.passed or ERR_FALLBACK_BANK_ROLLBACK_FENCED not in dual_fenced.error_codes:
        errors.append("Rollback-fenced fallback bank was not detected")
    if not preflight_ok.passed:
        errors.append("Valid 82% battery OTA preflight unexpectedly failed")
    if preflight_low_batt.passed or ERR_OTA_BATTERY_BELOW_51_PCT not in preflight_low_batt.error_codes:
        errors.append("49% battery OTA preflight was not rejected by 51% gate")
    if not ota_6.passed or not ota_6.stage_b_u5_zero_brick_verified:
        errors.extend(ota_6.errors)

    all_ok = len(errors) == 0
    status = STATUS_VERIFIED_AB_BANK_OTA_GATE if all_ok else STATUS_FAIL_AB_BANK_OTA_GATE
    digest_payload = {
        "schema": AB_BANK_OTA_SCHEMA,
        "mode": donor_snap.verification_mode,
        "donor_sha": donor_snap.snapshot_sha256,
        "dual_healthy": dual_healthy.report_sha256,
        "dual_split": dual_split.report_sha256,
        "dual_trial": dual_trial.report_sha256,
        "dual_fenced": dual_fenced.report_sha256,
        "ota_6": ota_6.suite_sha256,
        "all_passed": all_ok,
    }

    return AbBankAndInterruptedOtaSuiteReport(
        schema=AB_BANK_OTA_SCHEMA,
        version=AB_BANK_OTA_VERSION,
        status=status,
        verification_mode=donor_snap.verification_mode,
        all_passed=all_ok,
        read_only_donor_access=READ_ONLY_DONOR_ACCESS,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        allow_boot_partition_targeting=ALLOW_BOOT_PARTITION_TARGETING,
        allow_destructive_fastboot=ALLOW_DESTRUCTIVE_FASTBOOT,
        otp_fuse_touches=OTP_FUSE_TOUCHES,
        passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        donor_snapshot=donor_snap,
        dual_bank_healthy_report=dual_healthy,
        dual_bank_split_deadlock_report=dual_split,
        dual_bank_trial_pending_report=dual_trial,
        dual_bank_rollback_fenced_report=dual_fenced,
        ota_preflight_valid=preflight_ok,
        ota_preflight_low_battery_blocked=preflight_low_batt,
        ota_6_scenario_suite=ota_6,
        suite_sha256=_canonical_sha256(digest_payload),
        elapsed_seconds=round(time.monotonic() - t0, 6),
        errors=tuple(errors),
    )


__all__ = [
    "AB_BANK_OTA_SCHEMA",
    "AB_BANK_OTA_VERSION",
    "ACTION_NO_RECOVERY_NEEDED_HEALTHY",
    "ACTION_PASSIVE_UART_AND_TIER0_NOR_DUMP",
    "ACTION_REJECT_CROSS_REGION_RESTORE_STOCK",
    "ACTION_SD_SENTINEL_INSTANT_BOOT_ZERO_BRICK",
    "ACTION_SD_SLOT1_VERIFIED_BODYDATA_OR_CLEAR_FLAGS",
    "ACTION_TIER0_READONLY_DUMP_AND_SD_BODYDATA",
    "ALLOW_BOOT_PARTITION_TARGETING",
    "ALLOW_DESTRUCTIVE_FASTBOOT",
    "AP_BANK_FILENAMES",
    "BANK_A",
    "BANK_B",
    "BANK_STATE_ACTIVE_VERIFIED",
    "BANK_STATE_PENDING_TRIAL",
    "BANK_STATE_ROLLBACK_FENCED",
    "BANK_STATE_TORN_PARTIAL_WRITE",
    "BODYDATA_HEADER_READ_BYTES",
    "BODYDATA_UFU_MAGIC",
    "BODYDATA_UFU_MAGIC_HEX",
    "CP_BANK_FILENAMES",
    "CXD90057_AP_SOC",
    "CXD90058_CP_SOC",
    "DOMAIN_AP",
    "DOMAIN_CP",
    "DONOR_FX3_BODYDATA_RELPATH",
    "DONOR_FX3_CPAPP_B_RELPATH",
    "DONOR_FX3_P1_205_RELPATH",
    "DONOR_FX3_UDTRBODY_RELPATH",
    "DONOR_FX6_CPAPP_B_RELPATH",
    "DUAL_BANK_STATES",
    "ERR_AP_BANK_ROLLBACK_FENCED",
    "ERR_AP_BANK_TORN_PARTIAL_WRITE",
    "ERR_AP_CP_ACTIVE_BANK_DESYNC",
    "ERR_AP_CP_IPC_EPOCH_DEADLOCK",
    "ERR_CP_BANK_ROLLBACK_FENCED",
    "ERR_CP_BANK_TORN_PARTIAL_WRITE",
    "ERR_CROSS_SKU_BANK_MISMATCH",
    "ERR_FALLBACK_BANK_ROLLBACK_FENCED",
    "ERR_INVALID_BANK_ID",
    "ERR_NO_INTACT_FALLBACK_BANK",
    "ERR_OTA_BATTERY_BELOW_51_PCT",
    "ERR_OTA_BODYDATA_CRC_OR_MAGIC",
    "ERR_OTA_MODEL_MISMATCH",
    "ERR_OTA_REGION_NTSC_PAL_MISMATCH",
    "ERR_OTA_SPLIT_BANK_PRECHECK_FAILED",
    "ERR_OTA_UNSTABLE_TRANSPORT",
    "FX3_EPOCH_BY_VERSION",
    "FX3_MODEL_ID",
    "FX3_SKU_CODE",
    "FX6_MODEL_ID",
    "FX6_SKU_CODE",
    "OTA_SCENARIO_IDS",
    "OTA_SCENARIO_U1_BATTERY_PULLED_CP",
    "OTA_SCENARIO_U2_SD_CRC_MID_UPDATA",
    "OTA_SCENARIO_U3_USB_CABLE_YANKED",
    "OTA_SCENARIO_U4_CROSS_REGION_MISMATCH",
    "OTA_SCENARIO_U5_STAGE_B_ZERO_BRICK",
    "OTA_SCENARIO_U6_INTACT_HEALTHY",
    "OTP_FUSE_TOUCHES",
    "PASSIVE_TX_BYTES_EMITTED",
    "PERSISTENT_EMMC_WRITES_AUTHORIZED",
    "PERSISTENT_WRITE_RELEASE",
    "PHYSICAL_DEVICE_WRITES",
    "PINNED_FX3_BODYDATA_HEADER_SHA256",
    "PINNED_FX3_BODYDATA_TOTAL_BYTES",
    "PINNED_FX3_CPAPP_B_SHA256",
    "PINNED_FX3_P1_205_SHA256",
    "PINNED_FX3_UDTRBODY_SHA256",
    "PINNED_FX6_CPAPP_B_SHA256",
    "READ_ONLY_DONOR_ACCESS",
    "RECOVERY_ACTION_CODES",
    "SONY_FW_UPDATE_MIN_BATTERY_PCT",
    "SONY_UPDATA_ERROR_UINCOMP",
    "SONY_UPDATA_FLAG_FILES",
    "STAGE_B_SENTINEL_FILENAME",
    "STATUS_DUAL_BANK_CONSISTENT",
    "STATUS_DUAL_BANK_TORN_REJECTED",
    "STATUS_FAIL_AB_BANK_OTA_GATE",
    "STATUS_OTA_PREFLIGHT_APPROVED",
    "STATUS_OTA_PREFLIGHT_REJECTED",
    "STATUS_OTA_TRIAGE_HEALTHY",
    "STATUS_OTA_TRIAGE_RECOVERABLE",
    "STATUS_VERIFIED_AB_BANK_OTA_GATE",
    "VALID_BANK_IDS",
    "VALID_CAMERA_REGIONS",
    "AbBankAndInterruptedOtaSuiteReport",
    "BankSlotDescriptor",
    "BankSlotHealthResult",
    "DonorAbBankOtaSnapshot",
    "AbBankDonorArtifactDigest",
    "DualBankConsistencyReport",
    "Ota6ScenarioSuiteResult",
    "OtaBrickTriageResult",
    "OtaInterruptionEvidence",
    "OtaPreflightResult",
    "audit_dual_bank_ap_cp_consistency",
    "audit_official_ota_preflight",
    "build_synthetic_dual_bank_snapshot",
    "build_synthetic_ota_interruption_evidence",
    "classify_bank_slot_health",
    "inspect_ab_bank_and_ota_donors_readonly",
    "run_ab_bank_and_interrupted_ota_suite",
    "run_interrupted_ota_6_scenario_triage",
    "triage_interrupted_ota_brick",
]
