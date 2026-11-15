"""Phase 134 — CXD90057 IPL / BLoader / ATF BL31 / Kernel Secure-Boot Chain-of-Trust
Envelope Verifier, `nflasha1..nflasha20` `4 KiB / 512 KiB` Erase-Group
Partition-Boundary Overlap Firewall, & 15-Pillar Recovery Master Suite.

Provides three deterministic, RAM-only, read-only-donor verification pillars for
Sony `ILME-FX3` (`0x91030080` / `ALCIN_UUD`, `CXD90057`) recovery safety:

1. **Read-Only (`O_RDONLY`) FX3/FX6 Boot/Partition/Crypto Donor Inspection**:
   - Opens local FX3 `v7.02` (`loader_nor.bin`, `partinf.conf`, `vmlinux.bin`) and
     FX6 `v6.01` (`loader_nor.tar` -> `loader_nor.bin`, `partinf.conf`, `vmlinux.bin`)
     artifacts strictly via `os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK`, verifying
     boot/partition/SPAcc/eFuse/OTP symbol anchors and cross-SKU partition boundary
     divergence (`0x0031C000` FX3 vs `0x00312000` FX6 LensData) with zero raw
     firmware bytes or private/OTP keys emitted.
   - Deterministically falls back to pinned `CLEAN_ROOM_SYNTHETIC` metadata when
     `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor files are absent.

2. **Pillar A — `CXD90057` `IPL -> BLoader -> ARM Trusted Firmware (BL31) -> Kernel`
   Secure-Boot Envelope & Cross-SKU Signature Mismatch Firewall**:
   - Models the structural envelope of Sony signed boot stages (monotonic
     version/epoch, payload byte length vs partition capacity, RSA/ECDSA
     signature-block structural presence without touching hardware keys, and
     `Model ID` `0x91030080` FX3 vs `0x91040086` FX6 SKU tag check).
   - Enforces fail-closed:
     a) `BLOCKED_UNSIGNED_OR_PATCHED_BOOT_STAGE_ON_LOCKED_SOC` if any boot-chain
        stage (`IPL`, `BLoader`, `BL31`, `Kernel`) has a modified payload digest
        without an untouched original Sony signature envelope when targeting eMMC
        boot (whereas Stage-B userland/RAM overlay inside `QEMU` or post-kernel
        userland bind-mount never modifies signed boot stages!),
     b) `BLOCKED_CROSS_SKU_FX6_BOOTLOADER_ON_FX3_SOC` if an FX6
        bootloader/PMIC-init image is staged for FX3 hardware,
     c) `BLOCKED_OTP_EFUSE_OR_SPACC_KEYSLOT_ACCESS` if any manifest requests
        `eFuse/OTP` blow or `SPAcc` key-slot dump.

3. **Pillar B — `nflasha1..nflasha20` `eMMC` `512 B` LBA / `4 KiB` Page / `512 KiB`
   Erase-Group Boundary & Neighbor-Partition Bleed Firewall**:
   - Implements a deterministic interval-tree (`LbaIntervalTree`) and LBA-range
     verifier across the partition map (`start_lba`, `end_lba`,
     `erase_group_lba_multiple = 1024` sectors = `512 KiB`) that catches:
     a) `PARTITION_LBA_OVERLAP_DETECTED` across any pair of partitions,
     b) `UNALIGNED_ERASE_GROUP_BLEED_HAZARD` if a flash/erase operation is not
        aligned to the `512 KiB` eMMC erase-group boundary or exceeds
        `partition_sector_count`,
     c) `PROTECTED_PARTITION_WRITE_ATTEMPT_BLOCKED` on `BOOT0`, `BOOT1`, `RPMB`,
        `nvs`, `adj`, `cnflasha`.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import io
import json
import re
import tarfile
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .files import is_forced_clean_room, read_file, require, resolve_donor_path


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

SECUREBOOT_PARTALIGN_SCHEMA: str = "fx3-secureboot-chain-and-partition-align-verifier-v1"
SECUREBOOT_PARTALIGN_VERSION: str = "1.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False
ALLOW_BOOT_PARTITION_TARGETING: bool = False
ALLOW_DESTRUCTIVE_FASTBOOT: bool = False
READ_ONLY_DONOR_ACCESS: bool = True
OTP_FUSE_TOUCHES: int = 0
OTP_FUSE_WRITES: int = 0
SPACC_KEY_READS: int = 0
PASSIVE_TX_BYTES_EMITTED: int = 0
PHYSICAL_DEVICE_WRITES: int = 0

FX3_SOC_MODEL_ID: int = 0x91030080
FX6_SOC_MODEL_ID: int = 0x91040086
FX3_SOC_SKU_CODE: str = "ILME-FX3"
FX6_SOC_SKU_CODE: str = "ILME-FX6"

STATUS_VERIFIED_SECUREBOOT_PARTALIGN_GATE: str = "VERIFIED_SECUREBOOT_CHAIN_AND_PARTALIGN_GATE"
STATUS_FAIL_SECUREBOOT_PARTALIGN_GATE: str = "FAIL_SECUREBOOT_CHAIN_AND_PARTALIGN_GATE"
STATUS_VERIFIED_SECUREBOOT_ENVELOPE: str = "VERIFIED_SECUREBOOT_CHAIN_ENVELOPE"
STATUS_VERIFIED_STAGE_B_UNTOUCHED_BOOTCHAIN: str = "VERIFIED_STAGE_B_VOLATILE_OVERLAY_UNTOUCHED_BOOTCHAIN"
STATUS_REJECTED_SECUREBOOT_FIREWALL: str = "REJECTED_SECUREBOOT_CHAIN_FIREWALL"
STATUS_VERIFIED_PARTITION_ALIGN_FIREWALL: str = "VERIFIED_PARTITION_ALIGN_FIREWALL"
STATUS_REJECTED_PARTITION_ALIGN_FIREWALL: str = "REJECTED_PARTITION_ALIGN_FIREWALL"

# Local Donor Relative Paths (strictly read-only via os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK)
SBPA_DONOR_FX3_LOADER_NOR_BIN_RELPATH: str = (
    "sony-firmware-20261024/stage182-boot-selector-and-recovery-admission/"
    "current-updater-evidence/nor-loader-members/loader_nor.bin"
)
SBPA_DONOR_FX6_LOADER_NOR_TAR_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0750_nor_loader/loader_nor.tar"
)
SBPA_DONOR_FX3_PARTINF_CONF_RELPATH: str = (
    "sony-firmware-20261024/stage182-boot-selector-and-recovery-admission/"
    "current-updater-evidence/tar-selected/0300_partconf/partinf.conf"
)
SBPA_DONOR_FX6_PARTINF_CONF_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0300_partconf/partinf.conf"
)
SBPA_DONOR_FX3_VMLINUX_RELPATH: str = (
    "sony-firmware-20261024/stage182-boot-selector-and-recovery-admission/"
    "current-updater-evidence/p3-main/vmlinux.bin"
)
SBPA_DONOR_FX6_VMLINUX_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fat-files/nflasha3/vmlinux.bin"
)

# Pinned Donor Integrity Anchors (Zero Proprietary Keys / Zero Raw Firmware Bytes)
SBPA_PINNED_FX3_LOADER_NOR_BIN_BYTES: int = 101888
SBPA_PINNED_FX3_LOADER_NOR_BIN_SHA256: str = "4358c839cfb1f22d5eb4e53d67817c42c4e877ba8b0aff375d355ce6294c4942"
SBPA_PINNED_FX6_LOADER_NOR_BIN_BYTES: int = 92448
SBPA_PINNED_FX6_LOADER_NOR_BIN_SHA256: str = "d91d21a80afbad0053c95ba59129b97d59fd4feedf0cb4a0c01eac7ef7cebe08"
SBPA_PINNED_FX3_PARTINF_CONF_BYTES: int = 3999
SBPA_PINNED_FX3_PARTINF_CONF_SHA256: str = "3d96228d4ed2db3cb4295aa854edf0ad8895440167f132144cdec4f8cfdad189"
SBPA_PINNED_FX6_PARTINF_CONF_BYTES: int = 3990
SBPA_PINNED_FX6_PARTINF_CONF_SHA256: str = "e05b53d1f739968510dd24d62cd38426772fe3e50fe463a3d260c5f113e17ec9"
SBPA_PINNED_FX3_VMLINUX_BYTES: int = 6610952
SBPA_PINNED_FX3_VMLINUX_SHA256: str = "da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c"
SBPA_PINNED_FX6_VMLINUX_BYTES: int = 6610952
SBPA_PINNED_FX6_VMLINUX_SHA256: str = "bc4925e701ae363c797f22ef28f29dc48fd17af7f25a3f64d7d0824312c0dab9"

# ---------------------------------------------------------------------------
# Pillar A Constants — CXD90057 Secure-Boot Chain-of-Trust Envelope
# ---------------------------------------------------------------------------

CXD90057_SECUREBOOT_STAGES: Tuple[str, ...] = ("IPL", "BLoader", "BL31", "Kernel")
SECUREBOOT_TARGET_EMMC_LOCKED_SOC: str = "EMMC_LOCKED_SOC"
SECUREBOOT_TARGET_STAGE_B_QEMU_OVERLAY: str = "STAGE_B_QEMU_USERLAND_OVERLAY"
SECUREBOOT_TARGET_STAGE_B_BIND_MOUNT: str = "STAGE_B_POST_KERNEL_BIND_MOUNT"
STAGE_B_UNTOUCHED_TARGETS: Tuple[str, ...] = (
    SECUREBOOT_TARGET_STAGE_B_QEMU_OVERLAY,
    SECUREBOOT_TARGET_STAGE_B_BIND_MOUNT,
)

SUPPORTED_SIGNATURE_ALGORITHMS: Tuple[str, ...] = (
    "RSA-2048-PSS-SHA256",
    "RSA-4096-PSS-SHA256",
    "ECDSA-P256-SHA256",
)

# Required Pillar A Firewall Codes (exact names per Phase 134 spec)
BLOCKED_UNSIGNED_OR_PATCHED_BOOT_STAGE_ON_LOCKED_SOC: str = (
    "BLOCKED_UNSIGNED_OR_PATCHED_BOOT_STAGE_ON_LOCKED_SOC"
)
BLOCKED_CROSS_SKU_FX6_BOOTLOADER_ON_FX3_SOC: str = (
    "BLOCKED_CROSS_SKU_FX6_BOOTLOADER_ON_FX3_SOC"
)
BLOCKED_OTP_EFUSE_OR_SPACC_KEYSLOT_ACCESS: str = (
    "BLOCKED_OTP_EFUSE_OR_SPACC_KEYSLOT_ACCESS"
)

ERR_SECUREBOOT_EPOCH_ROLLBACK: str = "SECUREBOOT_MONOTONIC_EPOCH_ROLLBACK"
ERR_SECUREBOOT_CAPACITY_OVERFLOW: str = "SECUREBOOT_PAYLOAD_EXCEEDS_PARTITION_CAPACITY"
ERR_SECUREBOOT_STAGE_ORDER_OR_MISSING: str = "SECUREBOOT_STAGE_CHAIN_INCOMPLETE"
ERR_SECUREBOOT_STAGE_B_MODIFIED_BOOTSTAGE: str = "STAGE_B_MUST_NOT_MODIFY_SIGNED_BOOT_STAGES"

FORBIDDEN_OTP_EFUSE_SPACC_VERBS: Tuple[str, ...] = (
    "blow_efuse",
    "burn_efuse",
    "write_efuse",
    "program_efuse",
    "blow_otp",
    "burn_otp",
    "write_otp",
    "program_otp",
    "efuse_blow",
    "otp_blow",
    "dump_spacc",
    "read_spacc",
    "extract_spacc",
    "spacc_keyslot",
    "spacc_key_slot",
    "dump_keyslot",
    "read_keyslot",
)

SECUREBOOT_FIREWALL_SCENARIO_IDS: Tuple[str, ...] = (
    "SB1_HEALTHY_FX3_EMMC_BOOT_CHAIN",
    "SB2_STAGE_B_QEMU_AND_USERLAND_BIND_MOUNT_PASSES",
    "SB3_PATCHED_BL31_ON_LOCKED_SOC_BLOCKED",
    "SB4_UNSIGNED_KERNEL_OR_OVERFLOW_BLOCKED",
    "SB5_CROSS_SKU_FX6_BOOTLOADER_ON_FX3_BLOCKED",
    "SB6_OTP_EFUSE_BLOW_AND_SPACC_KEYSLOT_DUMP_BLOCKED",
)

# ---------------------------------------------------------------------------
# Pillar B Constants — nflasha1..nflasha20 eMMC Geometry & Bleed Firewall
# ---------------------------------------------------------------------------

EMMC_SECTOR_BYTES: int = 512
EMMC_PAGE_BYTES: int = 4096
EMMC_PAGE_LBA_MULTIPLE: int = 8  # 8 * 512 B = 4 KiB
EMMC_ERASE_GROUP_BYTES: int = 524288  # 512 KiB
EMMC_ERASE_GROUP_LBA_MULTIPLE: int = 1024  # 1024 * 512 B = 512 KiB

PROTECTED_EMMC_PARTITIONS: Tuple[str, ...] = (
    "BOOT0",
    "BOOT1",
    "RPMB",
    "nvs",
    "adj",
    "cnflasha",
)

# Required Pillar B Firewall Codes (exact names per Phase 134 spec)
PARTITION_LBA_OVERLAP_DETECTED: str = "PARTITION_LBA_OVERLAP_DETECTED"
UNALIGNED_ERASE_GROUP_BLEED_HAZARD: str = "UNALIGNED_ERASE_GROUP_BLEED_HAZARD"
PROTECTED_PARTITION_WRITE_ATTEMPT_BLOCKED: str = "PROTECTED_PARTITION_WRITE_ATTEMPT_BLOCKED"

ERR_PARTALIGN_INVALID_GEOMETRY: str = "PARTITION_INVALID_LBA_GEOMETRY"
ERR_PARTALIGN_MISALIGNED_4K_PAGE: str = "PARTITION_MISALIGNED_4K_PAGE_BOUNDARY"
ERR_PARTALIGN_UNKNOWN_TARGET_PARTITION: str = "PARTALIGN_UNKNOWN_TARGET_PARTITION"

PARTALIGN_FIREWALL_SCENARIO_IDS: Tuple[str, ...] = (
    "PA1_HEALTHY_FX3_20PART_MAP_AND_ALIGNED_OP",
    "PA2_PARTITION_LBA_OVERLAP_DETECTED",
    "PA3_UNALIGNED_ERASE_GROUP_512K_BLEED",
    "PA4_OP_EXCEEDS_PARTITION_BLEEDS_INTO_NEIGHBOR",
    "PA5_PROTECTED_BOOT0_BOOT1_RPMB_WRITE_BLOCKED",
    "PA6_PROTECTED_NVS_ADJ_CNFLASHA_WRITE_BLOCKED",
)

# Canonical FX3 CXD90057 nflasha1..nflasha20 map (from FX3 partinf.conf)
# Tuple: (partition_name, start_lba, size_lbas, role, protected, reserved_empty)
FX3_NFLASHA_1_TO_20_LAYOUT: Tuple[Tuple[str, int, int, str, bool, bool], ...] = (
    ("nflasha1", 0x00000080, 0x0000BF80, "updater_vfat_boot", False, False),
    ("nflasha2", 0x0000C000, 0x0000A000, "setting_bk4_nvs", True, False),
    ("nflasha3", 0x00016000, 0x00025800, "kernel_main", False, False),
    ("nflasha4", 0x0003B800, 0x00006000, "mpr_flash_backup_adj", True, False),
    ("nflasha5", 0x00041800, 0x00096000, "warm_boot_wbi2", False, False),
    ("nflasha6", 0x000D7800, 0x0000C800, "jiritsu_staging", False, False),
    ("nflasha7", 0x000E4000, 0x00008000, "rootfs", False, False),
    ("nflasha8", 0x000EC000, 0x00020000, "cp_data", False, False),
    ("nflasha9", 0x0010C000, 0x00000000, "reserved_sys", False, True),
    ("nflasha10", 0x0010C000, 0x00006000, "work_scratch", False, False),
    ("nflasha11", 0x00112000, 0x000FA000, "log_work", False, False),
    ("nflasha12", 0x0020C000, 0x00014000, "network_config", False, False),
    ("nflasha13", 0x00220000, 0x00002000, "updater_work", False, False),
    ("nflasha14", 0x00222000, 0x00000000, "reserved_work", False, True),
    ("nflasha15", 0x00222000, 0x000FA000, "usr_app", False, False),
    ("nflasha16", 0x0031C000, 0x00000000, "reserved_usr_a", False, True),
    ("nflasha17", 0x0031C000, 0x00000000, "reserved_usr_b", False, True),
    ("nflasha18", 0x0031C000, 0x0000A000, "lens_data_cnflasha", True, False),
    ("nflasha19", 0x00326000, 0x00000000, "reserved_usr_c", False, True),
    ("nflasha20", 0x00326000, 0x00000000, "reserved_usr_d", False, True),
)

_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")


# ---------------------------------------------------------------------------
# Internal Helpers (Zero raw bytes / Zero NaN)
# ---------------------------------------------------------------------------


def _canonical_json_bytes(obj: Any) -> bytes:
    return json.dumps(
        obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _canonical_sha256(obj: Any) -> str:
    return sha256(_canonical_json_bytes(obj)).hexdigest()


def _is_valid_sha256_hex(val: str) -> bool:
    return isinstance(val, str) and bool(_SHA256_HEX_RE.match(val))


def _scan_symbols(blob: bytes, symbols: Sequence[bytes]) -> Tuple[str, ...]:
    found: List[str] = []
    for sym in symbols:
        if sym in blob:
            found.append(sym.decode("ascii", errors="replace"))
    return tuple(found)


def _parse_partinf_lensdata_start_lba(partinf_text: str) -> Optional[int]:
    """Parse nflasha18 (LensData) start LBA from Sony partinf.conf."""
    lines = [
        ln.strip()
        for ln in partinf_text.splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    if len(lines) < 18:
        return None
    parts = [tok.strip() for tok in lines[17].split(",")]
    if not parts:
        return None
    return int(parts[0], 16)


# ---------------------------------------------------------------------------
# Structured Dataclasses (Zero raw bytes / Zero private/OTP keys)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SecurebootPartalignDonorArtifactDigest:
    label: str
    relpath: str
    source_mode: str
    byte_length: int
    sha256: str
    inspected: bool
    symbols_verified: Tuple[str, ...]
    details: str


@dataclass(frozen=True)
class DonorSecurebootPartalignSnapshot:
    verification_mode: str
    read_only_access: bool
    fx3_loader_nor_sha256: str
    fx6_loader_nor_sha256: str
    fx3_partinf_sha256: str
    fx6_partinf_sha256: str
    fx3_vmlinux_sha256: str
    fx6_vmlinux_sha256: str
    fx3_lensdata_start_lba: int
    fx6_lensdata_start_lba: int
    cross_sku_distinct: bool
    artifacts: Tuple[SecurebootPartalignDonorArtifactDigest, ...]
    snapshot_sha256: str


@dataclass(frozen=True)
class SecureBootStageEnvelope:
    stage_name: str
    monotonic_epoch: int
    payload_bytes: int
    partition_capacity_bytes: int
    payload_sha256: str
    signed_payload_sha256: str
    signature_algorithm: str
    signature_block_present: bool
    signature_block_bytes: int
    signature_envelope_untouched: bool
    model_id: int
    sku_code: str
    pmic_init_profile: str


@dataclass(frozen=True)
class SecureBootChainManifest:
    manifest_id: str
    boot_target: str
    target_sku_code: str
    target_model_id: int
    min_monotonic_epoch: int
    stages: Tuple[SecureBootStageEnvelope, ...]
    requested_operations: Tuple[str, ...] = ("verify_boot_chain_envelope",)
    efuse_otp_write_requested: bool = False
    spacc_keyslot_read_requested: bool = False
    stage_b_modifies_boot_stages: bool = False


@dataclass(frozen=True)
class OtpEfuseSpaccDecision:
    allowed: bool
    status: str
    operation: str
    efuse_otp_write_requested: bool
    spacc_keyslot_read_requested: bool
    otp_fuse_writes: int
    spacc_key_reads: int
    physical_device_writes: int
    error_codes: Tuple[str, ...]
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SecureBootChainReport:
    passed: bool
    status: str
    scenario_id: str
    boot_target: str
    target_sku_code: str
    target_model_id: int
    stages_verified: Tuple[str, ...]
    stage_b_volatile_overlay_only: bool
    boot_stages_untouched: bool
    unsigned_or_patched_blocked: bool
    cross_sku_fx6_blocked: bool
    otp_efuse_spacc_blocked: bool
    physical_device_writes: int
    otp_fuse_writes: int
    spacc_key_reads: int
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    error_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    report_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SecureBoot6ScenarioSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenario_results: Tuple[SecureBootChainReport, ...]
    otp_efuse_decision: OtpEfuseSpaccDecision
    spacc_keyslot_decision: OtpEfuseSpaccDecision
    physical_device_writes: int
    otp_fuse_writes: int
    spacc_key_reads: int
    errors: Tuple[str, ...]
    suite_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EmmcPartitionEntry:
    partition_name: str
    start_lba: int
    end_lba: int
    partition_sector_count: int
    erase_group_lba_multiple: int = EMMC_ERASE_GROUP_LBA_MULTIPLE
    role: str = "data"
    protected: bool = False
    reserved_empty: bool = False
    hardware_area: str = "UDA"


@dataclass(frozen=True)
class EmmcFlashOrEraseOp:
    op_id: str
    operation: str
    target_partition: str
    seek_lba: int
    sector_count: int
    block_size_bytes: int = EMMC_SECTOR_BYTES
    use_absolute_lba: bool = False
    is_write: bool = False
    is_erase_or_trim: bool = False


@dataclass(frozen=True)
class PartitionOverlapPair:
    partition_a: str
    partition_b: str
    overlap_start_lba: int
    overlap_end_lba: int
    hardware_area: str


@dataclass(frozen=True)
class PartitionAlignFirewallReport:
    passed: bool
    status: str
    scenario_id: str
    partition_count: int
    active_partition_count: int
    overlap_pairs: Tuple[PartitionOverlapPair, ...]
    neighbor_bleed_partitions: Tuple[str, ...]
    overlap_detected: bool
    unaligned_erase_bleed_detected: bool
    protected_partition_write_blocked: bool
    erase_group_lba_multiple: int
    physical_device_writes: int
    otp_fuse_writes: int
    spacc_key_reads: int
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    error_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    report_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PartitionAlign6ScenarioSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenario_results: Tuple[PartitionAlignFirewallReport, ...]
    physical_device_writes: int
    otp_fuse_writes: int
    spacc_key_reads: int
    errors: Tuple[str, ...]
    suite_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SecurebootChainAndPartitionAlignSuiteReport:
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
    otp_fuse_writes: int
    spacc_key_reads: int
    passive_tx_bytes_emitted: int
    physical_device_writes: int
    donor_snapshot: DonorSecurebootPartalignSnapshot
    secureboot_6_scenario_firewall: SecureBoot6ScenarioSuiteResult
    partition_align_6_scenario_firewall: PartitionAlign6ScenarioSuiteResult
    suite_sha256: str
    elapsed_seconds: float
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Read-Only (O_RDONLY) Donor Inspection & Clean-Room Synthetic Fallback
# ---------------------------------------------------------------------------


def inspect_secureboot_and_partalign_donors_readonly(
    *,
    force_clean_room: Optional[bool] = None,
) -> DonorSecurebootPartalignSnapshot:
    """Inspect local FX3 v7.02 & FX6 v6.01 boot/partition/crypto donor references
    strictly via `os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK`, falling back deterministically
    to pinned `CLEAN_ROOM_SYNTHETIC` metadata when `FX3_FX6_FORCE_CLEAN_ROOM=1` or
    donor files are absent. Zero raw firmware bytes or private/OTP keys emitted.
    """
    clean_room = is_forced_clean_room() if force_clean_room is None else bool(force_clean_room)

    fx3_loader_syms = (b"NOR Loader", b"Norm Boot seq", b"OSPI-NOR", b"TZ", b"INS_E:Sign")
    fx6_loader_syms = (b"NOR Loader", b"OSPI-NOR", b"EXBL", b"TZ", b"INS_E:Sign")
    fx3_part_syms = (b"/dev/nflasha1", b"/dev/nflasha18", b"LensData", b"0x0031C000")
    fx6_part_syms = (b"/dev/nflasha1", b"/dev/nflasha18", b"LensData", b"0x00312000")
    fx3_kern_syms = (b"4.9.337-scel+", b"cxd90057", b"spacc", b"efuse", b"OTP", b"PSCI", b"SMC", b"dic-build-scm-u20-028")
    fx6_kern_syms = (b"4.9.337-scel+", b"cxd90057", b"spacc", b"efuse", b"OTP", b"PSCI", b"SMC", b"dic-build-scm-u24-002")

    if not clean_room:
        fx3_ldr_p = resolve_donor_path(SBPA_DONOR_FX3_LOADER_NOR_BIN_RELPATH, require_file=True)
        fx6_tar_p = resolve_donor_path(SBPA_DONOR_FX6_LOADER_NOR_TAR_RELPATH, require_file=True)
        fx3_part_p = resolve_donor_path(SBPA_DONOR_FX3_PARTINF_CONF_RELPATH, require_file=True)
        fx6_part_p = resolve_donor_path(SBPA_DONOR_FX6_PARTINF_CONF_RELPATH, require_file=True)
        fx3_kern_p = resolve_donor_path(SBPA_DONOR_FX3_VMLINUX_RELPATH, require_file=True)
        fx6_kern_p = resolve_donor_path(SBPA_DONOR_FX6_VMLINUX_RELPATH, require_file=True)
        all_present = all(
            p.is_file()
            for p in (fx3_ldr_p, fx6_tar_p, fx3_part_p, fx6_part_p, fx3_kern_p, fx6_kern_p)
        )
    else:
        fx3_ldr_p = fx6_tar_p = fx3_part_p = fx6_part_p = fx3_kern_p = fx6_kern_p = None
        all_present = False

    if all_present:
        mode = "LOCAL_DONOR_O_RDONLY"
        fx3_ldr_bytes = read_file(fx3_ldr_p, 2 * 1024 * 1024)
        fx6_tar_bytes = read_file(fx6_tar_p, 2 * 1024 * 1024)
        fx3_part_bytes = read_file(fx3_part_p, 256 * 1024)
        fx6_part_bytes = read_file(fx6_part_p, 256 * 1024)
        fx3_kern_bytes = read_file(fx3_kern_p, 32 * 1024 * 1024)
        fx6_kern_bytes = read_file(fx6_kern_p, 32 * 1024 * 1024)

        fx6_ldr_bytes = b""
        with tarfile.open(fileobj=io.BytesIO(fx6_tar_bytes), mode="r:*") as tf:
            for member in tf.getmembers():
                if member.isfile() and member.name.endswith("loader_nor.bin"):
                    extracted = tf.extractfile(member)
                    if extracted is not None:
                        fx6_ldr_bytes = extracted.read()
                    break
        require(len(fx6_ldr_bytes) > 0, "FX6 loader_nor.tar missing loader_nor.bin member")

        found_fx3_ldr = _scan_symbols(fx3_ldr_bytes, fx3_loader_syms)
        found_fx6_ldr = _scan_symbols(fx6_ldr_bytes, fx6_loader_syms)
        found_fx3_part = _scan_symbols(fx3_part_bytes, fx3_part_syms)
        found_fx6_part = _scan_symbols(fx6_part_bytes, fx6_part_syms)
        found_fx3_kern = _scan_symbols(fx3_kern_bytes, fx3_kern_syms)
        found_fx6_kern = _scan_symbols(fx6_kern_bytes, fx6_kern_syms)

        require(len(found_fx3_ldr) == len(fx3_loader_syms), "FX3 loader_nor.bin missing expected boot/sign symbols")
        require(len(found_fx6_ldr) == len(fx6_loader_syms), "FX6 loader_nor.bin missing expected CHAPLIN/boot symbols")
        require(len(found_fx3_part) == len(fx3_part_syms), "FX3 partinf.conf missing expected LensData 0x0031C000 anchor")
        require(len(found_fx6_part) == len(fx6_part_syms), "FX6 partinf.conf missing expected LensData 0x00312000 anchor")
        require(len(found_fx3_kern) == len(fx3_kern_syms), "FX3 vmlinux.bin missing expected spacc/efuse/PSCI symbols")
        require(len(found_fx6_kern) == len(fx6_kern_syms), "FX6 vmlinux.bin missing expected spacc/efuse/PSCI symbols")

        fx3_lens_lba = _parse_partinf_lensdata_start_lba(fx3_part_bytes.decode("utf-8", errors="replace"))
        fx6_lens_lba = _parse_partinf_lensdata_start_lba(fx6_part_bytes.decode("utf-8", errors="replace"))
        require(fx3_lens_lba == 0x0031C000, f"Unexpected FX3 LensData start LBA: {fx3_lens_lba}")
        require(fx6_lens_lba == 0x00312000, f"Unexpected FX6 LensData start LBA: {fx6_lens_lba}")

        fx3_ldr_len, fx3_ldr_sha = len(fx3_ldr_bytes), sha256(fx3_ldr_bytes).hexdigest()
        fx6_ldr_len, fx6_ldr_sha = len(fx6_ldr_bytes), sha256(fx6_ldr_bytes).hexdigest()
        fx3_part_len, fx3_part_sha = len(fx3_part_bytes), sha256(fx3_part_bytes).hexdigest()
        fx6_part_len, fx6_part_sha = len(fx6_part_bytes), sha256(fx6_part_bytes).hexdigest()
        fx3_kern_len, fx3_kern_sha = len(fx3_kern_bytes), sha256(fx3_kern_bytes).hexdigest()
        fx6_kern_len, fx6_kern_sha = len(fx6_kern_bytes), sha256(fx6_kern_bytes).hexdigest()
    else:
        mode = "CLEAN_ROOM_SYNTHETIC"
        fx3_ldr_len, fx3_ldr_sha = SBPA_PINNED_FX3_LOADER_NOR_BIN_BYTES, SBPA_PINNED_FX3_LOADER_NOR_BIN_SHA256
        fx6_ldr_len, fx6_ldr_sha = SBPA_PINNED_FX6_LOADER_NOR_BIN_BYTES, SBPA_PINNED_FX6_LOADER_NOR_BIN_SHA256
        fx3_part_len, fx3_part_sha = SBPA_PINNED_FX3_PARTINF_CONF_BYTES, SBPA_PINNED_FX3_PARTINF_CONF_SHA256
        fx6_part_len, fx6_part_sha = SBPA_PINNED_FX6_PARTINF_CONF_BYTES, SBPA_PINNED_FX6_PARTINF_CONF_SHA256
        fx3_kern_len, fx3_kern_sha = SBPA_PINNED_FX3_VMLINUX_BYTES, SBPA_PINNED_FX3_VMLINUX_SHA256
        fx6_kern_len, fx6_kern_sha = SBPA_PINNED_FX6_VMLINUX_BYTES, SBPA_PINNED_FX6_VMLINUX_SHA256
        fx3_lens_lba = 0x0031C000
        fx6_lens_lba = 0x00312000
        found_fx3_ldr = tuple(s.decode("ascii") for s in fx3_loader_syms)
        found_fx6_ldr = tuple(s.decode("ascii") for s in fx6_loader_syms)
        found_fx3_part = tuple(s.decode("ascii") for s in fx3_part_syms)
        found_fx6_part = tuple(s.decode("ascii") for s in fx6_part_syms)
        found_fx3_kern = tuple(s.decode("ascii") for s in fx3_kern_syms)
        found_fx6_kern = tuple(s.decode("ascii") for s in fx6_kern_syms)

    cross_sku_distinct = (
        (fx3_ldr_sha != fx6_ldr_sha)
        and (fx3_part_sha != fx6_part_sha)
        and (fx3_kern_sha != fx6_kern_sha)
        and (fx3_lens_lba != fx6_lens_lba)
    )

    artifacts = (
        SecurebootPartalignDonorArtifactDigest(
            label="fx3_v702_loader_nor_bin",
            relpath=SBPA_DONOR_FX3_LOADER_NOR_BIN_RELPATH,
            source_mode=mode,
            byte_length=fx3_ldr_len,
            sha256=fx3_ldr_sha,
            inspected=(mode == "LOCAL_DONOR_O_RDONLY"),
            symbols_verified=found_fx3_ldr,
            details="FX3 v7.02 NOR IPL/BLoader signed stage image",
        ),
        SecurebootPartalignDonorArtifactDigest(
            label="fx6_v601_loader_nor_bin",
            relpath=SBPA_DONOR_FX6_LOADER_NOR_TAR_RELPATH,
            source_mode=mode,
            byte_length=fx6_ldr_len,
            sha256=fx6_ldr_sha,
            inspected=(mode == "LOCAL_DONOR_O_RDONLY"),
            symbols_verified=found_fx6_ldr,
            details="FX6 v6.01 cross-SKU CHAPLIN NOR bootloader inside loader_nor.tar",
        ),
        SecurebootPartalignDonorArtifactDigest(
            label="fx3_v702_partinf_conf",
            relpath=SBPA_DONOR_FX3_PARTINF_CONF_RELPATH,
            source_mode=mode,
            byte_length=fx3_part_len,
            sha256=fx3_part_sha,
            inspected=(mode == "LOCAL_DONOR_O_RDONLY"),
            symbols_verified=found_fx3_part,
            details="FX3 v7.02 nflasha1..nflasha30 eMMC partition geometry (LensData @ 0x0031C000)",
        ),
        SecurebootPartalignDonorArtifactDigest(
            label="fx6_v601_partinf_conf",
            relpath=SBPA_DONOR_FX6_PARTINF_CONF_RELPATH,
            source_mode=mode,
            byte_length=fx6_part_len,
            sha256=fx6_part_sha,
            inspected=(mode == "LOCAL_DONOR_O_RDONLY"),
            symbols_verified=found_fx6_part,
            details="FX6 v6.01 cross-SKU nflasha1..nflasha30 partition table (LensData @ 0x00312000)",
        ),
        SecurebootPartalignDonorArtifactDigest(
            label="fx3_v702_vmlinux_bin",
            relpath=SBPA_DONOR_FX3_VMLINUX_RELPATH,
            source_mode=mode,
            byte_length=fx3_kern_len,
            sha256=fx3_kern_sha,
            inspected=(mode == "LOCAL_DONOR_O_RDONLY"),
            symbols_verified=found_fx3_kern,
            details="FX3 v7.02 CXD90057 Linux 4.9.337-scel+ kernel with PSCI/SPAcc/eFuse anchors",
        ),
        SecurebootPartalignDonorArtifactDigest(
            label="fx6_v601_vmlinux_bin",
            relpath=SBPA_DONOR_FX6_VMLINUX_RELPATH,
            source_mode=mode,
            byte_length=fx6_kern_len,
            sha256=fx6_kern_sha,
            inspected=(mode == "LOCAL_DONOR_O_RDONLY"),
            symbols_verified=found_fx6_kern,
            details="FX6 v6.01 cross-SKU Linux 4.9.337-scel+ kernel (dic-build-scm-u24-002)",
        ),
    )

    snap_payload = {
        "mode": mode,
        "fx3_ldr_sha": fx3_ldr_sha,
        "fx6_ldr_sha": fx6_ldr_sha,
        "fx3_part_sha": fx3_part_sha,
        "fx6_part_sha": fx6_part_sha,
        "fx3_kern_sha": fx3_kern_sha,
        "fx6_kern_sha": fx6_kern_sha,
        "fx3_lens_lba": fx3_lens_lba,
        "fx6_lens_lba": fx6_lens_lba,
    }
    return DonorSecurebootPartalignSnapshot(
        verification_mode=mode,
        read_only_access=READ_ONLY_DONOR_ACCESS,
        fx3_loader_nor_sha256=fx3_ldr_sha,
        fx6_loader_nor_sha256=fx6_ldr_sha,
        fx3_partinf_sha256=fx3_part_sha,
        fx6_partinf_sha256=fx6_part_sha,
        fx3_vmlinux_sha256=fx3_kern_sha,
        fx6_vmlinux_sha256=fx6_kern_sha,
        fx3_lensdata_start_lba=fx3_lens_lba,
        fx6_lensdata_start_lba=fx6_lens_lba,
        cross_sku_distinct=cross_sku_distinct,
        artifacts=artifacts,
        snapshot_sha256=_canonical_sha256(snap_payload),
    )


# ---------------------------------------------------------------------------
# Pillar A — CXD90057 IPL -> BLoader -> BL31 -> Kernel Secure-Boot Envelope
# & Cross-SKU Signature Mismatch Firewall
# ---------------------------------------------------------------------------


def build_synthetic_secureboot_chain_manifest(
    *,
    manifest_id: str = "fx3-v702-secureboot-chain-v1",
    boot_target: str = SECUREBOOT_TARGET_EMMC_LOCKED_SOC,
    min_monotonic_epoch: int = 702,
    patched_stage: Optional[str] = None,
    unsigned_stage: Optional[str] = None,
    overflow_stage: Optional[str] = None,
    cross_sku_fx6_stage: Optional[str] = None,
    downgrade_stage: Optional[str] = None,
    requested_operations: Sequence[str] = ("verify_boot_chain_envelope",),
    efuse_otp_write_requested: bool = False,
    spacc_keyslot_read_requested: bool = False,
    stage_b_modifies_boot_stages: bool = False,
) -> SecureBootChainManifest:
    """Build a synthetic clean-room CXD90057 IPL->BLoader->BL31->Kernel envelope manifest."""
    stage_specs = (
        ("IPL", 101888, 131072, 256, "RSA-2048-PSS-SHA256"),
        ("BLoader", 262144, 524288, 256, "RSA-2048-PSS-SHA256"),
        ("BL31", 196608, 524288, 64, "ECDSA-P256-SHA256"),
        ("Kernel", 6610952, 16777216, 512, "RSA-4096-PSS-SHA256"),
    )
    envelopes: List[SecureBootStageEnvelope] = []
    for stage_name, payload_bytes, capacity_bytes, sig_bytes, alg in stage_specs:
        signed_digest = sha256(f"synthetic-sony-signed:{stage_name}:fx3-702".encode("utf-8")).hexdigest()
        actual_digest = signed_digest
        sig_present = True
        sig_len = sig_bytes
        sig_untouched = True
        epoch = min_monotonic_epoch
        sku = FX3_SOC_SKU_CODE
        model_id = FX3_SOC_MODEL_ID
        pmic = "FX3_ALCIN_PMIC_INIT"
        actual_payload = payload_bytes

        if patched_stage == stage_name:
            actual_digest = sha256(f"patched-unsigned-payload:{stage_name}".encode("utf-8")).hexdigest()
            sig_untouched = False
        if unsigned_stage == stage_name:
            sig_present = False
            sig_len = 0
            sig_untouched = False
        if overflow_stage == stage_name:
            actual_payload = capacity_bytes + 4096
        if cross_sku_fx6_stage == stage_name:
            sku = FX6_SOC_SKU_CODE
            model_id = FX6_SOC_MODEL_ID
            pmic = "FX6_CHAPLIN_PMIC_INIT"
        if downgrade_stage == stage_name:
            epoch = max(1, min_monotonic_epoch - 102)

        envelopes.append(
            SecureBootStageEnvelope(
                stage_name=stage_name,
                monotonic_epoch=epoch,
                payload_bytes=actual_payload,
                partition_capacity_bytes=capacity_bytes,
                payload_sha256=actual_digest,
                signed_payload_sha256=signed_digest,
                signature_algorithm=alg,
                signature_block_present=sig_present,
                signature_block_bytes=sig_len,
                signature_envelope_untouched=sig_untouched,
                model_id=model_id,
                sku_code=sku,
                pmic_init_profile=pmic,
            )
        )

    return SecureBootChainManifest(
        manifest_id=manifest_id,
        boot_target=boot_target,
        target_sku_code=FX3_SOC_SKU_CODE,
        target_model_id=FX3_SOC_MODEL_ID,
        min_monotonic_epoch=min_monotonic_epoch,
        stages=tuple(envelopes),
        requested_operations=tuple(requested_operations),
        efuse_otp_write_requested=efuse_otp_write_requested,
        spacc_keyslot_read_requested=spacc_keyslot_read_requested,
        stage_b_modifies_boot_stages=stage_b_modifies_boot_stages,
    )


def audit_otp_efuse_and_spacc_operation(
    operation: str,
    *,
    efuse_otp_write_requested: bool = False,
    spacc_keyslot_read_requested: bool = False,
) -> OtpEfuseSpaccDecision:
    """Fail-closed firewall blocking any CXD90057 eFuse/OTP blow or SPAcc key-slot access."""
    raw_op = (operation or "").strip()
    lower = raw_op.lower()

    verb_hit = any(v in lower for v in FORBIDDEN_OTP_EFUSE_SPACC_VERBS)
    token_hit = (
        ("efuse" in lower or "otp" in lower)
        and any(act in lower for act in ("blow", "burn", "write", "program", "fuse", "set"))
    ) or (
        ("spacc" in lower or "keyslot" in lower or "key_slot" in lower)
        and any(act in lower for act in ("dump", "read", "extract", "export", "key"))
    )

    hazard = verb_hit or token_hit or efuse_otp_write_requested or spacc_keyslot_read_requested
    error_codes: List[str] = []
    errors: List[str] = []
    if hazard:
        error_codes.append(BLOCKED_OTP_EFUSE_OR_SPACC_KEYSLOT_ACCESS)
        errors.append(
            f"Blocked eFuse/OTP blow or SPAcc key-slot access "
            f"(op='{raw_op[:80]}', efuse_req={efuse_otp_write_requested}, "
            f"spacc_req={spacc_keyslot_read_requested})."
        )

    return OtpEfuseSpaccDecision(
        allowed=not hazard,
        status=(
            BLOCKED_OTP_EFUSE_OR_SPACC_KEYSLOT_ACCESS
            if hazard
            else "ALLOWED_READONLY_ENVELOPE_AUDIT"
        ),
        operation=raw_op,
        efuse_otp_write_requested=efuse_otp_write_requested,
        spacc_keyslot_read_requested=spacc_keyslot_read_requested,
        otp_fuse_writes=OTP_FUSE_WRITES,
        spacc_key_reads=SPACC_KEY_READS,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        error_codes=tuple(error_codes),
        errors=tuple(errors),
    )


def verify_cxd90057_secureboot_envelope(
    manifest: SecureBootChainManifest,
    *,
    scenario_id: str = "CUSTOM_SECUREBOOT_ENVELOPE",
) -> SecureBootChainReport:
    """Verify CXD90057 IPL->BLoader->BL31->Kernel secure-boot envelope, cross-SKU model ID,
    Stage-B userland/QEMU non-modification exception, and OTP/SPAcc access lock.
    """
    error_codes: List[str] = []
    errors: List[str] = []

    def _add(code: str, msg: str) -> None:
        if code not in error_codes:
            error_codes.append(code)
        errors.append(msg)

    is_stage_b_volatile = manifest.boot_target in STAGE_B_UNTOUCHED_TARGETS

    # 1. OTP / eFuse blow & SPAcc key-slot dump firewall
    if manifest.efuse_otp_write_requested or manifest.spacc_keyslot_read_requested:
        dec = audit_otp_efuse_and_spacc_operation(
            ",".join(manifest.requested_operations) or "manifest_hw_key_request",
            efuse_otp_write_requested=manifest.efuse_otp_write_requested,
            spacc_keyslot_read_requested=manifest.spacc_keyslot_read_requested,
        )
        for code, msg in zip(dec.error_codes, dec.errors):
            _add(code, msg)

    for op in manifest.requested_operations:
        dec = audit_otp_efuse_and_spacc_operation(op)
        for code, msg in zip(dec.error_codes, dec.errors):
            _add(code, msg)

    # 2. Target SoC SKU check
    if manifest.target_sku_code != FX3_SOC_SKU_CODE or manifest.target_model_id != FX3_SOC_MODEL_ID:
        _add(
            BLOCKED_CROSS_SKU_FX6_BOOTLOADER_ON_FX3_SOC,
            f"Target manifest SKU/Model mismatch: expected {FX3_SOC_SKU_CODE}/0x{FX3_SOC_MODEL_ID:08x}, "
            f"got {manifest.target_sku_code}/0x{manifest.target_model_id:08x}.",
        )

    # 3. Boot-chain stage completeness & order (IPL -> BLoader -> BL31 -> Kernel)
    stage_names = tuple(st.stage_name for st in manifest.stages)
    if stage_names != CXD90057_SECUREBOOT_STAGES:
        _add(
            ERR_SECUREBOOT_STAGE_ORDER_OR_MISSING,
            f"Boot-chain stage order {stage_names} != required {CXD90057_SECUREBOOT_STAGES}.",
        )

    if is_stage_b_volatile and manifest.stage_b_modifies_boot_stages:
        _add(
            ERR_SECUREBOOT_STAGE_B_MODIFIED_BOOTSTAGE,
            "Stage-B QEMU/userland overlay must never modify signed eMMC boot stages.",
        )

    # 4. Per-stage envelope, signature integrity & cross-SKU checks
    all_boot_stages_untouched = not manifest.stage_b_modifies_boot_stages
    for st in manifest.stages:
        # Cross-SKU FX6 bootloader/PMIC-init check
        pmic_upper = st.pmic_init_profile.upper()
        if (
            st.model_id != FX3_SOC_MODEL_ID
            or st.sku_code != FX3_SOC_SKU_CODE
            or "FX6" in pmic_upper
            or "CHAPLIN" in pmic_upper
        ):
            _add(
                BLOCKED_CROSS_SKU_FX6_BOOTLOADER_ON_FX3_SOC,
                f"Cross-SKU FX6 stage '{st.stage_name}' (sku={st.sku_code}, model=0x{st.model_id:08x}, "
                f"pmic={st.pmic_init_profile}) blocked on FX3 CXD90057 SoC.",
            )

        # Payload length vs partition capacity
        if st.payload_bytes <= 0 or st.partition_capacity_bytes <= 0 or st.payload_bytes > st.partition_capacity_bytes:
            _add(
                ERR_SECUREBOOT_CAPACITY_OVERFLOW,
                f"Stage '{st.stage_name}' payload {st.payload_bytes}B exceeds partition capacity {st.partition_capacity_bytes}B.",
            )
            _add(
                BLOCKED_UNSIGNED_OR_PATCHED_BOOT_STAGE_ON_LOCKED_SOC,
                f"Stage '{st.stage_name}' failed capacity bounds for locked CXD90057 boot envelope.",
            )

        # Monotonic version/epoch check
        if st.monotonic_epoch < manifest.min_monotonic_epoch:
            _add(
                ERR_SECUREBOOT_EPOCH_ROLLBACK,
                f"Stage '{st.stage_name}' monotonic_epoch={st.monotonic_epoch} < min={manifest.min_monotonic_epoch}.",
            )
            _add(
                BLOCKED_UNSIGNED_OR_PATCHED_BOOT_STAGE_ON_LOCKED_SOC,
                f"Stage '{st.stage_name}' failed anti-rollback epoch envelope.",
            )

        # Signature envelope & digest check (without touching hardware keys)
        digest_ok = (
            _is_valid_sha256_hex(st.payload_sha256)
            and _is_valid_sha256_hex(st.signed_payload_sha256)
            and st.payload_sha256 == st.signed_payload_sha256
        )
        sig_ok = (
            st.signature_block_present
            and st.signature_block_bytes > 0
            and st.signature_algorithm in SUPPORTED_SIGNATURE_ALGORITHMS
            and st.signature_envelope_untouched
        )
        if not (digest_ok and sig_ok):
            all_boot_stages_untouched = False
            _add(
                BLOCKED_UNSIGNED_OR_PATCHED_BOOT_STAGE_ON_LOCKED_SOC,
                f"Stage '{st.stage_name}' has unsigned or patched payload without untouched Sony signature envelope.",
            )

    unsigned_or_patched_blocked = BLOCKED_UNSIGNED_OR_PATCHED_BOOT_STAGE_ON_LOCKED_SOC in error_codes
    cross_sku_fx6_blocked = BLOCKED_CROSS_SKU_FX6_BOOTLOADER_ON_FX3_SOC in error_codes
    otp_efuse_spacc_blocked = BLOCKED_OTP_EFUSE_OR_SPACC_KEYSLOT_ACCESS in error_codes

    passed = len(error_codes) == 0
    if passed:
        status = (
            STATUS_VERIFIED_STAGE_B_UNTOUCHED_BOOTCHAIN
            if is_stage_b_volatile
            else STATUS_VERIFIED_SECUREBOOT_ENVELOPE
        )
    else:
        status = STATUS_REJECTED_SECUREBOOT_FIREWALL

    digest_payload = {
        "scenario_id": scenario_id,
        "boot_target": manifest.boot_target,
        "status": status,
        "passed": passed,
        "stages": list(stage_names),
        "error_codes": error_codes,
    }
    return SecureBootChainReport(
        passed=passed,
        status=status,
        scenario_id=scenario_id,
        boot_target=manifest.boot_target,
        target_sku_code=manifest.target_sku_code,
        target_model_id=manifest.target_model_id,
        stages_verified=stage_names,
        stage_b_volatile_overlay_only=is_stage_b_volatile and all_boot_stages_untouched,
        boot_stages_untouched=all_boot_stages_untouched,
        unsigned_or_patched_blocked=unsigned_or_patched_blocked,
        cross_sku_fx6_blocked=cross_sku_fx6_blocked,
        otp_efuse_spacc_blocked=otp_efuse_spacc_blocked,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        otp_fuse_writes=OTP_FUSE_WRITES,
        spacc_key_reads=SPACC_KEY_READS,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        error_codes=tuple(error_codes),
        errors=tuple(errors),
        report_sha256=_canonical_sha256(digest_payload),
    )


def run_secureboot_envelope_6_scenario_firewall() -> SecureBoot6ScenarioSuiteResult:
    """Execute the 6 canonical CXD90057 secure-boot envelope & cross-SKU firewall scenarios."""
    r1 = verify_cxd90057_secureboot_envelope(
        build_synthetic_secureboot_chain_manifest(
            manifest_id="sb1-healthy-emmc-chain",
            boot_target=SECUREBOOT_TARGET_EMMC_LOCKED_SOC,
        ),
        scenario_id=SECUREBOOT_FIREWALL_SCENARIO_IDS[0],
    )
    r2 = verify_cxd90057_secureboot_envelope(
        build_synthetic_secureboot_chain_manifest(
            manifest_id="sb2-stage-b-qemu-userland-overlay",
            boot_target=SECUREBOOT_TARGET_STAGE_B_QEMU_OVERLAY,
            requested_operations=("mount_stage_b_tmpfs_overlay", "verify_boot_chain_untouched"),
        ),
        scenario_id=SECUREBOOT_FIREWALL_SCENARIO_IDS[1],
    )
    r3 = verify_cxd90057_secureboot_envelope(
        build_synthetic_secureboot_chain_manifest(
            manifest_id="sb3-patched-bl31-locked-soc",
            boot_target=SECUREBOOT_TARGET_EMMC_LOCKED_SOC,
            patched_stage="BL31",
        ),
        scenario_id=SECUREBOOT_FIREWALL_SCENARIO_IDS[2],
    )
    r4 = verify_cxd90057_secureboot_envelope(
        build_synthetic_secureboot_chain_manifest(
            manifest_id="sb4-unsigned-kernel-overflow",
            boot_target=SECUREBOOT_TARGET_EMMC_LOCKED_SOC,
            unsigned_stage="Kernel",
            overflow_stage="Kernel",
        ),
        scenario_id=SECUREBOOT_FIREWALL_SCENARIO_IDS[3],
    )
    r5 = verify_cxd90057_secureboot_envelope(
        build_synthetic_secureboot_chain_manifest(
            manifest_id="sb5-cross-sku-fx6-bloader",
            boot_target=SECUREBOOT_TARGET_EMMC_LOCKED_SOC,
            cross_sku_fx6_stage="BLoader",
        ),
        scenario_id=SECUREBOOT_FIREWALL_SCENARIO_IDS[4],
    )
    r6 = verify_cxd90057_secureboot_envelope(
        build_synthetic_secureboot_chain_manifest(
            manifest_id="sb6-otp-efuse-spacc-access",
            boot_target=SECUREBOOT_TARGET_EMMC_LOCKED_SOC,
            requested_operations=("blow_efuse", "dump_spacc_keyslot"),
            efuse_otp_write_requested=True,
            spacc_keyslot_read_requested=True,
        ),
        scenario_id=SECUREBOOT_FIREWALL_SCENARIO_IDS[5],
    )

    otp_dec = audit_otp_efuse_and_spacc_operation("blow_efuse", efuse_otp_write_requested=True)
    spacc_dec = audit_otp_efuse_and_spacc_operation("dump_spacc_keyslot", spacc_keyslot_read_requested=True)

    results = (r1, r2, r3, r4, r5, r6)
    suite_errors: List[str] = []
    passed_count = 0

    if r1.passed and r1.status == STATUS_VERIFIED_SECUREBOOT_ENVELOPE and r1.boot_stages_untouched:
        passed_count += 1
    else:
        suite_errors.append(f"SB1 failed: {r1.error_codes}")

    if r2.passed and r2.status == STATUS_VERIFIED_STAGE_B_UNTOUCHED_BOOTCHAIN and r2.stage_b_volatile_overlay_only:
        passed_count += 1
    else:
        suite_errors.append(f"SB2 failed: {r2.error_codes}")

    if (not r3.passed) and r3.unsigned_or_patched_blocked:
        passed_count += 1
    else:
        suite_errors.append("SB3 failed to block patched BL31 on locked SoC")

    if (not r4.passed) and r4.unsigned_or_patched_blocked and (ERR_SECUREBOOT_CAPACITY_OVERFLOW in r4.error_codes):
        passed_count += 1
    else:
        suite_errors.append("SB4 failed to block unsigned/overflowed Kernel")

    if (not r5.passed) and r5.cross_sku_fx6_blocked:
        passed_count += 1
    else:
        suite_errors.append("SB5 failed to block cross-SKU FX6 bootloader on FX3 SoC")

    if (not r6.passed) and r6.otp_efuse_spacc_blocked:
        passed_count += 1
    else:
        suite_errors.append("SB6 failed to block eFuse/OTP blow or SPAcc key-slot dump")

    for label, dec in (("otp", otp_dec), ("spacc", spacc_dec)):
        if (
            dec.allowed
            or BLOCKED_OTP_EFUSE_OR_SPACC_KEYSLOT_ACCESS not in dec.error_codes
            or dec.otp_fuse_writes != 0
            or dec.spacc_key_reads != 0
            or dec.physical_device_writes != 0
        ):
            suite_errors.append(f"{label} firewall failed zero-write/zero-read invariant")

    for r in results:
        if (
            r.physical_device_writes != 0
            or r.otp_fuse_writes != 0
            or r.spacc_key_reads != 0
            or r.persistent_emmc_writes_authorized
            or r.persistent_write_release
        ):
            suite_errors.append(f"{r.scenario_id} violated hard-locked zero-write/zero-key-read invariant")

    all_ok = len(suite_errors) == 0 and passed_count == len(SECUREBOOT_FIREWALL_SCENARIO_IDS)
    suite_payload = {
        "scenarios": [
            {
                "id": r.scenario_id,
                "status": r.status,
                "passed": r.passed,
                "error_codes": list(r.error_codes),
            }
            for r in results
        ]
    }
    return SecureBoot6ScenarioSuiteResult(
        passed=all_ok,
        status=STATUS_VERIFIED_SECUREBOOT_PARTALIGN_GATE if all_ok else STATUS_FAIL_SECUREBOOT_PARTALIGN_GATE,
        scenarios_passed=passed_count,
        scenarios_total=len(SECUREBOOT_FIREWALL_SCENARIO_IDS),
        scenario_results=results,
        otp_efuse_decision=otp_dec,
        spacc_keyslot_decision=spacc_dec,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        otp_fuse_writes=OTP_FUSE_WRITES,
        spacc_key_reads=SPACC_KEY_READS,
        errors=tuple(suite_errors),
        suite_sha256=_canonical_sha256(suite_payload),
    )


# ---------------------------------------------------------------------------
# Pillar B — nflasha1..nflasha20 eMMC 512B/4KiB/512KiB Erase-Group Interval
# Tree & Neighbor-Partition Bleed Firewall
# ---------------------------------------------------------------------------


class _IntervalTreeNode:
    __slots__ = ("entry", "max_end", "left", "right")

    def __init__(self, entry: EmmcPartitionEntry) -> None:
        self.entry = entry
        self.max_end = entry.end_lba
        self.left: Optional[_IntervalTreeNode] = None
        self.right: Optional[_IntervalTreeNode] = None


class LbaIntervalTree:
    """Deterministic augmented interval tree over (start_lba, end_lba) ranges."""

    def __init__(self) -> None:
        self.root: Optional[_IntervalTreeNode] = None

    def insert(self, entry: EmmcPartitionEntry) -> None:
        node = _IntervalTreeNode(entry)
        if self.root is None:
            self.root = node
            return
        cur = self.root
        while True:
            if entry.end_lba > cur.max_end:
                cur.max_end = entry.end_lba
            if (entry.start_lba, entry.end_lba, entry.partition_name) < (
                cur.entry.start_lba,
                cur.entry.end_lba,
                cur.entry.partition_name,
            ):
                if cur.left is None:
                    cur.left = node
                    return
                cur = cur.left
            else:
                if cur.right is None:
                    cur.right = node
                    return
                cur = cur.right

    def query_overlaps(self, start_lba: int, end_lba: int) -> List[EmmcPartitionEntry]:
        hits: List[EmmcPartitionEntry] = []

        def _visit(node: Optional[_IntervalTreeNode]) -> None:
            if node is None or node.max_end < start_lba:
                return
            if node.left is not None and node.left.max_end >= start_lba:
                _visit(node.left)
            if node.entry.start_lba <= end_lba and start_lba <= node.entry.end_lba:
                hits.append(node.entry)
            if node.right is not None and node.entry.start_lba <= end_lba:
                _visit(node.right)

        _visit(self.root)
        return hits


def build_synthetic_fx3_nflasha_partition_map(
    *,
    include_hardware_boot_areas: bool = True,
    overlap_pair: Optional[Tuple[str, int]] = None,
) -> Tuple[EmmcPartitionEntry, ...]:
    """Build deterministic FX3 nflasha1..nflasha20 (plus BOOT0/BOOT1/RPMB) partition map."""
    entries: List[EmmcPartitionEntry] = []
    for name, start_lba, size_lbas, role, protected, reserved_empty in FX3_NFLASHA_1_TO_20_LAYOUT:
        adj_start = start_lba
        if overlap_pair is not None and overlap_pair[0] == name:
            adj_start = overlap_pair[1]
        end_lba = (adj_start - 1) if reserved_empty else (adj_start + size_lbas - 1)
        entries.append(
            EmmcPartitionEntry(
                partition_name=name,
                start_lba=adj_start,
                end_lba=end_lba,
                partition_sector_count=size_lbas,
                erase_group_lba_multiple=EMMC_ERASE_GROUP_LBA_MULTIPLE,
                role=role,
                protected=protected,
                reserved_empty=reserved_empty,
                hardware_area="UDA",
            )
        )

    if include_hardware_boot_areas:
        # Separate JEDEC eMMC hardware partitions (4 MiB BOOT0/BOOT1, 4 MiB RPMB)
        entries.extend(
            [
                EmmcPartitionEntry(
                    partition_name="BOOT0",
                    start_lba=0,
                    end_lba=8191,
                    partition_sector_count=8192,
                    erase_group_lba_multiple=EMMC_ERASE_GROUP_LBA_MULTIPLE,
                    role="hardware_boot0",
                    protected=True,
                    reserved_empty=False,
                    hardware_area="BOOT0",
                ),
                EmmcPartitionEntry(
                    partition_name="BOOT1",
                    start_lba=0,
                    end_lba=8191,
                    partition_sector_count=8192,
                    erase_group_lba_multiple=EMMC_ERASE_GROUP_LBA_MULTIPLE,
                    role="hardware_boot1",
                    protected=True,
                    reserved_empty=False,
                    hardware_area="BOOT1",
                ),
                EmmcPartitionEntry(
                    partition_name="RPMB",
                    start_lba=0,
                    end_lba=8191,
                    partition_sector_count=8192,
                    erase_group_lba_multiple=EMMC_ERASE_GROUP_LBA_MULTIPLE,
                    role="hardware_rpmb",
                    protected=True,
                    reserved_empty=False,
                    hardware_area="RPMB",
                ),
            ]
        )
    return tuple(entries)


def _normalize_partition_token(name: str) -> str:
    clean = (name or "").strip()
    if clean.startswith("/dev/"):
        clean = clean[len("/dev/"):]
    return clean


def _is_protected_partition_target(target_name: str, entry: Optional[EmmcPartitionEntry]) -> bool:
    norm = _normalize_partition_token(target_name).lower()
    protected_lower = {p.lower() for p in PROTECTED_EMMC_PARTITIONS}
    if norm in protected_lower:
        return True
    if norm in ("mmcblk0boot0", "mmcblk0boot1", "mmcblk0rpmb", "nflashab0", "nflashab1"):
        return True
    if entry is not None:
        if entry.protected:
            return True
        if any(tok in entry.role.lower() for tok in ("nvs", "adj", "cnflasha", "boot0", "boot1", "rpmb")):
            return True
    return False


def _resolve_target_partition(
    target_name: str,
    partitions: Sequence[EmmcPartitionEntry],
) -> Optional[EmmcPartitionEntry]:
    norm = _normalize_partition_token(target_name).lower()
    alias_map = {
        "nvs": "nflasha2",
        "adj": "nflasha4",
        "cnflasha": "nflasha18",
        "mmcblk0boot0": "boot0",
        "mmcblk0boot1": "boot1",
        "mmcblk0rpmb": "rpmb",
    }
    for p in partitions:
        if p.partition_name.lower() == norm:
            return p
    mapped = alias_map.get(norm)
    if mapped is not None:
        for p in partitions:
            if p.partition_name.lower() == mapped:
                return p
    return None


def find_partition_lba_overlaps(
    partitions: Sequence[EmmcPartitionEntry],
) -> Tuple[PartitionOverlapPair, ...]:
    """Find all overlapping active partition pairs per hardware_area using LbaIntervalTree."""
    by_area: Dict[str, List[EmmcPartitionEntry]] = {}
    for p in partitions:
        if p.reserved_empty or p.partition_sector_count == 0:
            continue
        by_area.setdefault(p.hardware_area, []).append(p)

    overlaps: List[PartitionOverlapPair] = []
    seen_pairs: set[Tuple[str, str, str]] = set()

    for area, items in sorted(by_area.items()):
        tree = LbaIntervalTree()
        for item in items:
            if item.end_lba < item.start_lba:
                continue
            hits = tree.query_overlaps(item.start_lba, item.end_lba)
            for other in hits:
                pair_names = tuple(sorted((item.partition_name, other.partition_name)))
                key = (area, pair_names[0], pair_names[1])
                if key not in seen_pairs:
                    seen_pairs.add(key)
                    overlaps.append(
                        PartitionOverlapPair(
                            partition_a=pair_names[0],
                            partition_b=pair_names[1],
                            overlap_start_lba=max(item.start_lba, other.start_lba),
                            overlap_end_lba=min(item.end_lba, other.end_lba),
                            hardware_area=area,
                        )
                    )
            tree.insert(item)

    return tuple(overlaps)


def verify_partition_map_and_flash_ops(
    partitions: Sequence[EmmcPartitionEntry],
    ops: Sequence[EmmcFlashOrEraseOp] = (),
    *,
    scenario_id: str = "CUSTOM_PARTALIGN_FIREWALL",
) -> PartitionAlignFirewallReport:
    """Verify partition LBA geometry, interval-tree non-overlap, 4KiB/512KiB erase-group
    boundaries, neighbor-partition bleed, and protected-partition write blocks.
    """
    error_codes: List[str] = []
    errors: List[str] = []
    bleed_neighbors: List[str] = []

    def _add(code: str, msg: str) -> None:
        if code not in error_codes:
            error_codes.append(code)
        errors.append(msg)

    active_partitions = [p for p in partitions if not p.reserved_empty]

    # 1. Validate individual partition LBA geometry & 4 KiB page boundaries
    for p in active_partitions:
        expected_count = p.end_lba - p.start_lba + 1
        if (
            p.start_lba < 0
            or p.end_lba < p.start_lba
            or p.partition_sector_count <= 0
            or p.partition_sector_count != expected_count
            or p.erase_group_lba_multiple <= 0
        ):
            _add(
                ERR_PARTALIGN_INVALID_GEOMETRY,
                f"Partition '{p.partition_name}' has invalid LBA geometry "
                f"(start={p.start_lba}, end={p.end_lba}, count={p.partition_sector_count}).",
            )
            continue
        if (p.start_lba % EMMC_PAGE_LBA_MULTIPLE != 0) or (
            p.partition_sector_count % EMMC_PAGE_LBA_MULTIPLE != 0
        ):
            _add(
                ERR_PARTALIGN_MISALIGNED_4K_PAGE,
                f"Partition '{p.partition_name}' is not 4 KiB (8-LBA) aligned "
                f"(start=0x{p.start_lba:x}, count=0x{p.partition_sector_count:x}).",
            )

    # 2. Interval-tree overlap detection across partition map
    overlap_pairs = find_partition_lba_overlaps(partitions)
    for ov in overlap_pairs:
        _add(
            PARTITION_LBA_OVERLAP_DETECTED,
            f"Partition LBA overlap in '{ov.hardware_area}': '{ov.partition_a}' and '{ov.partition_b}' "
            f"overlap across LBA [0x{ov.overlap_start_lba:x}, 0x{ov.overlap_end_lba:x}].",
        )

    # 3. Build interval trees per hardware_area for neighbor-bleed operation checks
    trees_by_area: Dict[str, LbaIntervalTree] = {}
    for p in active_partitions:
        if p.end_lba >= p.start_lba:
            trees_by_area.setdefault(p.hardware_area, LbaIntervalTree()).insert(p)

    # 4. Audit flash/erase/write/dd operations
    for op in ops:
        entry = _resolve_target_partition(op.target_partition, partitions)
        op_lower = (op.operation or "").lower()
        mutating = (
            op.is_write
            or op.is_erase_or_trim
            or any(
                tok in op_lower
                for tok in ("write", "flash", "erase", "trim", "discard", "dd", "format", "program")
            )
        )

        # Protected partition write attempt check (even before geometry checks)
        if mutating and _is_protected_partition_target(op.target_partition, entry):
            _add(
                PROTECTED_PARTITION_WRITE_ATTEMPT_BLOCKED,
                f"Blocked mutating op '{op.operation}' on protected partition '{op.target_partition}'.",
            )

        if entry is None:
            if mutating or op.sector_count > 0:
                _add(
                    ERR_PARTALIGN_UNKNOWN_TARGET_PARTITION,
                    f"Op '{op.op_id}' references unknown partition '{op.target_partition}'.",
                )
            continue

        if not mutating:
            continue

        if entry.reserved_empty or entry.partition_sector_count <= 0:
            _add(
                UNALIGNED_ERASE_GROUP_BLEED_HAZARD,
                f"Op '{op.op_id}' targets zero-size reserved partition '{entry.partition_name}'.",
            )
            continue

        if op.block_size_bytes <= 0 or (op.block_size_bytes % EMMC_SECTOR_BYTES != 0):
            _add(
                UNALIGNED_ERASE_GROUP_BLEED_HAZARD,
                f"Op '{op.op_id}' block_size_bytes={op.block_size_bytes} is not 512 B LBA-aligned.",
            )
            continue

        lba_scale = op.block_size_bytes // EMMC_SECTOR_BYTES
        rel_start_lba = (
            (op.seek_lba * lba_scale - entry.start_lba)
            if op.use_absolute_lba
            else (op.seek_lba * lba_scale)
        )
        op_sectors = op.sector_count * lba_scale
        abs_start_lba = entry.start_lba + rel_start_lba
        abs_end_lba = abs_start_lba + op_sectors - 1
        eg_mult = entry.erase_group_lba_multiple

        # 512 KiB (1024-LBA) erase-group alignment & boundary overflow checks
        if op_sectors <= 0 or rel_start_lba < 0:
            _add(
                UNALIGNED_ERASE_GROUP_BLEED_HAZARD,
                f"Op '{op.op_id}' on '{entry.partition_name}' has invalid seek/sector range "
                f"(rel_start_lba={rel_start_lba}, op_sectors={op_sectors}).",
            )
        else:
            if (abs_start_lba % eg_mult != 0) or (op_sectors % eg_mult != 0):
                _add(
                    UNALIGNED_ERASE_GROUP_BLEED_HAZARD,
                    f"Op '{op.op_id}' on '{entry.partition_name}' is not aligned to {eg_mult}-sector "
                    f"(512 KiB) eMMC erase-group boundary (abs_start=0x{abs_start_lba:x}, sectors={op_sectors}).",
                )
            if rel_start_lba + op_sectors > entry.partition_sector_count:
                _add(
                    UNALIGNED_ERASE_GROUP_BLEED_HAZARD,
                    f"Op '{op.op_id}' on '{entry.partition_name}' exceeds partition_sector_count "
                    f"({rel_start_lba + op_sectors} > {entry.partition_sector_count}), risking neighbor bleed.",
                )

            # Query interval tree for neighbor-partition bleed
            area_tree = trees_by_area.get(entry.hardware_area)
            if area_tree is not None:
                hits = area_tree.query_overlaps(abs_start_lba, abs_end_lba)
                for hit in hits:
                    if hit.partition_name != entry.partition_name:
                        if hit.partition_name not in bleed_neighbors:
                            bleed_neighbors.append(hit.partition_name)
                        _add(
                            UNALIGNED_ERASE_GROUP_BLEED_HAZARD,
                            f"Op '{op.op_id}' on '{entry.partition_name}' bleeds across boundary into "
                            f"neighbor partition '{hit.partition_name}' ({hit.role}).",
                        )

    overlap_detected = PARTITION_LBA_OVERLAP_DETECTED in error_codes
    unaligned_bleed = UNALIGNED_ERASE_GROUP_BLEED_HAZARD in error_codes
    protected_blocked = PROTECTED_PARTITION_WRITE_ATTEMPT_BLOCKED in error_codes

    passed = len(error_codes) == 0
    status = STATUS_VERIFIED_PARTITION_ALIGN_FIREWALL if passed else STATUS_REJECTED_PARTITION_ALIGN_FIREWALL

    digest_payload = {
        "scenario_id": scenario_id,
        "status": status,
        "passed": passed,
        "partition_count": len(partitions),
        "active_partition_count": len(active_partitions),
        "overlap_count": len(overlap_pairs),
        "bleed_neighbors": bleed_neighbors,
        "error_codes": error_codes,
    }
    return PartitionAlignFirewallReport(
        passed=passed,
        status=status,
        scenario_id=scenario_id,
        partition_count=len(partitions),
        active_partition_count=len(active_partitions),
        overlap_pairs=overlap_pairs,
        neighbor_bleed_partitions=tuple(bleed_neighbors),
        overlap_detected=overlap_detected,
        unaligned_erase_bleed_detected=unaligned_bleed,
        protected_partition_write_blocked=protected_blocked,
        erase_group_lba_multiple=EMMC_ERASE_GROUP_LBA_MULTIPLE,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        otp_fuse_writes=OTP_FUSE_WRITES,
        spacc_key_reads=SPACC_KEY_READS,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        error_codes=tuple(error_codes),
        errors=tuple(errors),
        report_sha256=_canonical_sha256(digest_payload),
    )


def run_partition_align_6_scenario_firewall() -> PartitionAlign6ScenarioSuiteResult:
    """Execute the 6 canonical nflasha1..nflasha20 partition-boundary & bleed firewall scenarios."""
    base_map = build_synthetic_fx3_nflasha_partition_map()

    # PA1: Healthy 20-partition FX3 map + aligned 512 KiB dry-run audit op on non-protected nflasha10
    r1 = verify_partition_map_and_flash_ops(
        base_map,
        ops=(
            EmmcFlashOrEraseOp(
                op_id="pa1-aligned-work-plan",
                operation="dryrun_aligned_erase_check",
                target_partition="nflasha10",
                seek_lba=0,
                sector_count=1024,
                is_erase_or_trim=True,
            ),
        ),
        scenario_id=PARTALIGN_FIREWALL_SCENARIO_IDS[0],
    )

    # PA2: Overlapping LBA pair (e.g., FX6-shifted nflasha15 overlapping nflasha18/cnflasha)
    overlap_map = build_synthetic_fx3_nflasha_partition_map(
        overlap_pair=("nflasha18", 0x00312000),
    )
    r2 = verify_partition_map_and_flash_ops(
        overlap_map,
        scenario_id=PARTALIGN_FIREWALL_SCENARIO_IDS[1],
    )

    # PA3: Unaligned off-by-one dd seek=1 / non-512KiB TRIM on nflasha7 (rootfs)
    r3 = verify_partition_map_and_flash_ops(
        base_map,
        ops=(
            EmmcFlashOrEraseOp(
                op_id="pa3-off-by-one-dd-seek",
                operation="dd_write",
                target_partition="nflasha7",
                seek_lba=1,
                sector_count=512,
                is_write=True,
            ),
        ),
        scenario_id=PARTALIGN_FIREWALL_SCENARIO_IDS[2],
    )

    # PA4: Overflow past end of nflasha15 (usr) bleeding into nflasha18 (cnflasha LensData)
    r4 = verify_partition_map_and_flash_ops(
        base_map,
        ops=(
            EmmcFlashOrEraseOp(
                op_id="pa4-overflow-bleed-into-cnflasha",
                operation="erase_trim",
                target_partition="nflasha15",
                seek_lba=0x000F9C00,
                sector_count=2048,
                is_erase_or_trim=True,
            ),
        ),
        scenario_id=PARTALIGN_FIREWALL_SCENARIO_IDS[3],
    )

    # PA5: Protected hardware partition write attempt (BOOT0, BOOT1, RPMB)
    r5 = verify_partition_map_and_flash_ops(
        base_map,
        ops=(
            EmmcFlashOrEraseOp(
                op_id="pa5-boot0-write",
                operation="dd_write",
                target_partition="BOOT0",
                seek_lba=0,
                sector_count=1024,
                is_write=True,
            ),
            EmmcFlashOrEraseOp(
                op_id="pa5-boot1-erase",
                operation="erase",
                target_partition="BOOT1",
                seek_lba=0,
                sector_count=1024,
                is_erase_or_trim=True,
            ),
            EmmcFlashOrEraseOp(
                op_id="pa5-rpmb-write",
                operation="flash_partition",
                target_partition="RPMB",
                seek_lba=0,
                sector_count=1024,
                is_write=True,
            ),
        ),
        scenario_id=PARTALIGN_FIREWALL_SCENARIO_IDS[4],
    )

    # PA6: Protected per-body calibration partition write attempt (nvs, adj, cnflasha)
    r6 = verify_partition_map_and_flash_ops(
        base_map,
        ops=(
            EmmcFlashOrEraseOp(
                op_id="pa6-nvs-write",
                operation="dd_write",
                target_partition="nvs",
                seek_lba=0,
                sector_count=1024,
                is_write=True,
            ),
            EmmcFlashOrEraseOp(
                op_id="pa6-adj-erase",
                operation="erase",
                target_partition="adj",
                seek_lba=0,
                sector_count=1024,
                is_erase_or_trim=True,
            ),
            EmmcFlashOrEraseOp(
                op_id="pa6-cnflasha-write",
                operation="flash_partition",
                target_partition="cnflasha",
                seek_lba=0,
                sector_count=1024,
                is_write=True,
            ),
        ),
        scenario_id=PARTALIGN_FIREWALL_SCENARIO_IDS[5],
    )

    results = (r1, r2, r3, r4, r5, r6)
    suite_errors: List[str] = []
    passed_count = 0

    if r1.passed and r1.status == STATUS_VERIFIED_PARTITION_ALIGN_FIREWALL:
        passed_count += 1
    else:
        suite_errors.append(f"PA1 failed: {r1.error_codes}")

    if (not r2.passed) and r2.overlap_detected and len(r2.overlap_pairs) >= 1:
        passed_count += 1
    else:
        suite_errors.append("PA2 failed to detect PARTITION_LBA_OVERLAP_DETECTED")

    if (not r3.passed) and r3.unaligned_erase_bleed_detected:
        passed_count += 1
    else:
        suite_errors.append("PA3 failed to detect UNALIGNED_ERASE_GROUP_BLEED_HAZARD")

    if (not r4.passed) and r4.unaligned_erase_bleed_detected and ("nflasha18" in r4.neighbor_bleed_partitions):
        passed_count += 1
    else:
        suite_errors.append("PA4 failed to detect neighbor partition bleed into nflasha18")

    if (not r5.passed) and r5.protected_partition_write_blocked:
        passed_count += 1
    else:
        suite_errors.append("PA5 failed to block write to BOOT0/BOOT1/RPMB")

    if (not r6.passed) and r6.protected_partition_write_blocked:
        passed_count += 1
    else:
        suite_errors.append("PA6 failed to block write to nvs/adj/cnflasha")

    for r in results:
        if (
            r.physical_device_writes != 0
            or r.otp_fuse_writes != 0
            or r.spacc_key_reads != 0
            or r.persistent_emmc_writes_authorized
            or r.persistent_write_release
        ):
            suite_errors.append(f"{r.scenario_id} violated hard-locked zero-write/zero-key-read invariant")

    all_ok = len(suite_errors) == 0 and passed_count == len(PARTALIGN_FIREWALL_SCENARIO_IDS)
    suite_payload = {
        "scenarios": [
            {
                "id": r.scenario_id,
                "status": r.status,
                "passed": r.passed,
                "error_codes": list(r.error_codes),
            }
            for r in results
        ]
    }
    return PartitionAlign6ScenarioSuiteResult(
        passed=all_ok,
        status=STATUS_VERIFIED_SECUREBOOT_PARTALIGN_GATE if all_ok else STATUS_FAIL_SECUREBOOT_PARTALIGN_GATE,
        scenarios_passed=passed_count,
        scenarios_total=len(PARTALIGN_FIREWALL_SCENARIO_IDS),
        scenario_results=results,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        otp_fuse_writes=OTP_FUSE_WRITES,
        spacc_key_reads=SPACC_KEY_READS,
        errors=tuple(suite_errors),
        suite_sha256=_canonical_sha256(suite_payload),
    )


# ---------------------------------------------------------------------------
# Master Suite Entrypoint (Pillar 15)
# ---------------------------------------------------------------------------


def run_secureboot_chain_and_partition_align_suite(
    *,
    force_clean_room: Optional[bool] = None,
) -> SecurebootChainAndPartitionAlignSuiteReport:
    """Run Phase 134 Pillar 15: O_RDONLY donor inspection, CXD90057 IPL->BLoader->BL31->Kernel
    secure-boot chain-of-trust envelope firewall, and nflasha1..nflasha20 4KiB/512KiB
    erase-group partition-boundary overlap & bleed firewall.
    """
    t0 = time.monotonic()
    donor_snap = inspect_secureboot_and_partalign_donors_readonly(
        force_clean_room=force_clean_room,
    )
    secureboot_suite = run_secureboot_envelope_6_scenario_firewall()
    partalign_suite = run_partition_align_6_scenario_firewall()

    errors: List[str] = []
    if not donor_snap.cross_sku_distinct:
        errors.append("Cross-SKU FX3/FX6 boot/partition/kernel donor separation check failed.")
    errors.extend(secureboot_suite.errors)
    errors.extend(partalign_suite.errors)

    all_passed = (
        donor_snap.cross_sku_distinct
        and secureboot_suite.passed
        and partalign_suite.passed
        and (PHYSICAL_DEVICE_WRITES == 0)
        and (OTP_FUSE_WRITES == 0)
        and (OTP_FUSE_TOUCHES == 0)
        and (SPACC_KEY_READS == 0)
        and (PASSIVE_TX_BYTES_EMITTED == 0)
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not PERSISTENT_WRITE_RELEASE)
    )
    suite_payload = {
        "schema": SECUREBOOT_PARTALIGN_SCHEMA,
        "version": SECUREBOOT_PARTALIGN_VERSION,
        "mode": donor_snap.verification_mode,
        "donor_sha256": donor_snap.snapshot_sha256,
        "secureboot_sha256": secureboot_suite.suite_sha256,
        "partalign_sha256": partalign_suite.suite_sha256,
        "all_passed": all_passed,
    }
    elapsed = round(time.monotonic() - t0, 4)
    return SecurebootChainAndPartitionAlignSuiteReport(
        schema=SECUREBOOT_PARTALIGN_SCHEMA,
        version=SECUREBOOT_PARTALIGN_VERSION,
        status=STATUS_VERIFIED_SECUREBOOT_PARTALIGN_GATE if all_passed else STATUS_FAIL_SECUREBOOT_PARTALIGN_GATE,
        verification_mode=donor_snap.verification_mode,
        all_passed=all_passed,
        read_only_donor_access=READ_ONLY_DONOR_ACCESS,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        allow_boot_partition_targeting=ALLOW_BOOT_PARTITION_TARGETING,
        allow_destructive_fastboot=ALLOW_DESTRUCTIVE_FASTBOOT,
        otp_fuse_touches=OTP_FUSE_TOUCHES,
        otp_fuse_writes=OTP_FUSE_WRITES,
        spacc_key_reads=SPACC_KEY_READS,
        passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        donor_snapshot=donor_snap,
        secureboot_6_scenario_firewall=secureboot_suite,
        partition_align_6_scenario_firewall=partalign_suite,
        suite_sha256=_canonical_sha256(suite_payload),
        elapsed_seconds=elapsed,
        errors=tuple(errors),
    )
