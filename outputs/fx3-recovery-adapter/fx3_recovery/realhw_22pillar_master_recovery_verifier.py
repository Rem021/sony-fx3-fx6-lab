"""Phase 166 — Pillar 22 (22/22 Recovery Pillars): Unified 22-Pillar Real-Hardware
Recovery Master Verifier (`verify-22pillar-recovery`) & Dual-Media Tier-0
Cold-Backup Bit-Rot Scrub / GF(256) Pre-Restore Rehearsal Engine.

Closes the final operator cold-backup storage durability & unified `22/22`
real-hardware recovery master readiness gate for `Sony ILME-FX3` (`Ver. 7.02`,
Model ID `0x91030080`, SoC `CXD90057` Mira + `CXD90058` Cetus) while hard-locking
every physical write, transmit, and fuse/RPMB safety gate:
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

1. **Dual-Mode Donor Inspection (`os.O_RDONLY`) + Clean-Room Fallback (`FX3_FX6_FORCE_CLEAN_ROOM=1`)**:
   - Inspects FX3 `7.02` donor artifacts (`partinf.conf`, `mount.conf`,
     `loader_nor.bin`, `nflasha1`, `FX3-CX95900_ALLLANG-Backup.bin`, bounded
     4 KiB header of `cpapp-b.bin`, and bounded 4 KiB ext2 superblock of
     `nflasha15.img`) strictly via `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)`.
   - Deterministic `CLEAN_ROOM_SYNTHETIC` fallback when `FX3_FX6_FORCE_CLEAN_ROOM=1`
     or donors are absent, leaking zero raw Sony firmware bytes in JSON output.

2. **Pillar 22A — Dual-Media Independent Tier-0 Cold-Backup & `FX3RCPT1` Gate**:
   - Enforces the mandatory rule that a camera's 16-surface Tier-0 cold backup
     (`FX3RCPT1` 528 B receipt + `pnflasha*`/`cnflasha*`/`mtd0ro`/`ext_csd` +
     `p2:/setting/psd.bin,defdet.bin,Backup.bin` + `p18:/lens/LENSFILE.BIN`)
     MUST exist on **two distinct physical storage media** (`media_a_device_id != media_b_device_id`
     and `media_a_hardware_uuid != media_b_hardware_uuid`, e.g., Host NVMe +
     external SSD/SDXC card) with matching SHA-256 manifests before any Stage-A
     installation can even be staged!

3. **Pillar 22B — RAID-6 `GF(256)` (`0x11d`) Bit-Rot Scrub & `16/16` Pre-Restore RAM Dry-Run**:
   - Simulates silent SSD/SD bit-rot on up to 2 chunks (1-chunk pure `GF(256)`
     syndrome localization or 2-chunk `P+Q` dual-parity reconstruction over
     `GF(2^8)` `0x11d`), proves lossless SHA-256 recovery, rejects `>= 3` chunk
     quorum loss fail-closed, and executes a full `16/16` pre-restore RAM
     dry-run verification (`physical_device_writes == 0`).

4. **Unified `22/22` Recovery Master Aggregator (`evaluate_22pillar_recovery_master`)**:
   - Evaluates and aggregates all Pillars `1..22` (including Pillars 18, 19, 20,
     21, and 22) concurrently in `< 2.0s` across both `LOCAL_DONOR_O_RDONLY`
     and `CLEAN_ROOM_SYNTHETIC` modes, asserting all zero-write/zero-transmit/zero-fuse
     safety invariants.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import os
import re
import stat
import struct
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple
import zlib

from .ab_bank_and_interrupted_ota_verifier import run_ab_bank_and_interrupted_ota_suite
from .bootrom_usb_and_emmc_bootpart_verifier import run_bootrom_usb_and_emmc_bootpart_suite
from .factory_cal_ibis_defectpixel_and_nvs_verifier import run_factory_cal_ibis_defectpixel_and_nvs_suite
from .fdt_bootargs_and_kernel_verifier import run_fdt_bootargs_and_kernel_suite
from .files import is_forced_clean_room, local_path, resolve_donor_path
from .gpt_rpmb_and_rescue_bundle_verifier import run_gpt_rpmb_and_rescue_bundle_suite
from .ramdisk_overlay_and_emmc_health_verifier import run_ramdisk_overlay_and_emmc_health_suite
from .realhw_adjustcontrol_streaming_backup_client import (
    SD_RECEIPT_BYTES,
    SD_RECEIPT_MAGIC,
    run_adjustcontrol_streaming_backup_suite,
)
from .realhw_bootrom_el3_and_ufu_stock_reflash_verifier import (
    run_realhw_bootrom_el3_and_ufu_stock_reflash_suite,
)
from .realhw_ext2_installer_and_p1_rescue_verifier import (
    run_realhw_ext2_installer_and_p1_rescue_suite,
)
from .realhw_pnflasha_cnflasha_mtdro_tier0_vault_verifier import (
    DOMAIN_EMMC_REG_METADATA,
    DOMAIN_RAW_PNFLASHA_ISP,
    DOMAIN_SPACC_CNFLASHA_LOGICAL,
    DOMAIN_SPI_NOR_MTDRO,
    LENS_VX8900_MAGIC,
    MANDATORY_16_SURFACE_IDS,
    TIER0_16_SURFACES,
    Tier0SurfaceSpec,
    build_synthetic_bk4_sample,
    build_synthetic_ext2_sample,
    build_synthetic_ext_csd_sample,
    build_synthetic_fx3_sector0_30_partitions,
    build_synthetic_high_entropy_spacc_sample,
    build_synthetic_spi_nor_sample,
    build_synthetic_squashfs_sample,
    build_synthetic_vfat_sample,
    build_synthetic_wbi2_sample,
    run_realhw_pnflasha_cnflasha_mtdro_tier0_vault_suite,
)
from .realhw_service_usb_session_and_libjit_elf_hardener import (
    run_realhw_service_usb_and_libjit_hardener_suite,
)
from .realhw_uart_460800_post_triage_and_isp_guard import (
    run_realhw_uart_460800_post_triage_and_isp_suite,
)
from .recovery_master_suite_and_uart_decoder import run_recovery_master_suite
from .secureboot_chain_and_partition_align_verifier import (
    run_secureboot_chain_and_partition_align_suite,
)
from .squashfs_and_hibdrv_wbi_verifier import run_squashfs_and_hibdrv_wbi_suite
from .tier0_backup_parity_and_manifest_guard import (
    GF256_PRIMITIVE_POLY,
    encode_gf256_pq_parity,
    heal_gf256_pq_shards,
)


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

PHASE166_SCHEMA: str = "fx3-realhw-22pillar-recovery-master-verifier-v1"
PHASE166_VERSION: str = "1.0.0"

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

# Bounded Donor Read & Receipt Constants
P166_BOUNDED_HEADER_BYTES: int = 4096
P166_BOUNDED_MAX_BYTES: int = 65536
P166_FX3_MODEL_ID: int = 0x91030080
P166_FX3_MODEL_NAME: str = "ILME-FX3"
P166_FX3_STOCK_VERSION: str = "7.02"

P166_FX3RCPT1_MAGIC: bytes = SD_RECEIPT_MAGIC  # b"FX3RCPT1"
P166_FX3RCPT1_MAGIC_HEX: str = P166_FX3RCPT1_MAGIC.hex()
P166_FX3RCPT1_BYTES: int = SD_RECEIPT_BYTES  # 528 B
P166_FX3RCPT1_VERSION: int = 1
P166_FX3RCPT1_FLAGS_DUAL_MEDIA_READY: int = 0x00000001

P166_GF256_POLYNOMIAL: int = GF256_PRIMITIVE_POLY  # 0x11D
P166_GF256_MAX_CHUNKS_HEALABLE: int = 2

P166_MANDATORY_16_SURFACES: Tuple[str, ...] = MANDATORY_16_SURFACE_IDS
P166_MANDATORY_P2_SETTING_FILES: Tuple[str, ...] = ("psd.bin", "defdet.bin", "Backup.bin")
P166_MANDATORY_P18_LENS_FILES: Tuple[str, ...] = ("LENSFILE.BIN",)
P166_VALID_MEDIA_KINDS: Tuple[str, ...] = (
    "HOST_NVME",
    "EXTERNAL_SSD",
    "SDXC_V90",
    "CFEXPRESS_TYPE_A",
    "EXTERNAL_HDD",
)

# Master 22-Pillar Registry: (pillar_number, pillar_id, phase_label, module_name)
MASTER_22_PILLAR_SPECS: Tuple[Tuple[int, str, str, str], ...] = (
    (1, "macos_usb_transport_guard", "Phase 38", "fx3_recovery.macos_usb_transport_guard"),
    (2, "rp2040_multiport_fixture_selftest", "Phase 59", "fx3_recovery.rp2040_multiport_fixture_selftest"),
    (3, "init2_escape_and_watchdog_simulator", "Phase 66", "fx3_recovery.init2_escape_and_watchdog_simulator"),
    (4, "tier0_backup_parity_and_manifest_guard", "Phase 72", "fx3_recovery.tier0_backup_parity_and_manifest_guard"),
    (5, "firmware_updata_and_antirollback_guard", "Phase 79", "fx3_recovery.firmware_updata_and_antirollback_guard"),
    (6, "unbrick_ladder_and_capsule_verifier", "Phase 47", "fx3_recovery.unbrick_ladder_and_capsule_verifier"),
    (7, "passive_uart_boot_stage_decoder", "Phase 86", "fx3_recovery.recovery_master_suite_and_uart_decoder"),
    (8, "gpt_rpmb_and_rescue_bundle_verifier", "Phase 94", "fx3_recovery.gpt_rpmb_and_rescue_bundle_verifier"),
    (9, "ramdisk_overlay_and_emmc_health_verifier", "Phase 101", "fx3_recovery.ramdisk_overlay_and_emmc_health_verifier"),
    (10, "fdt_bootargs_and_kernel_verifier", "Phase 106", "fx3_recovery.fdt_bootargs_and_kernel_verifier"),
    (11, "ab_bank_and_interrupted_ota_verifier", "Phase 113", "fx3_recovery.ab_bank_and_interrupted_ota_verifier"),
    (12, "squashfs_and_hibdrv_wbi_verifier", "Phase 119", "fx3_recovery.squashfs_and_hibdrv_wbi_verifier"),
    (13, "bootrom_usb_and_emmc_bootpart_verifier", "Phase 124", "fx3_recovery.bootrom_usb_and_emmc_bootpart_verifier"),
    (14, "factory_cal_ibis_defectpixel_and_nvs_verifier", "Phase 126", "fx3_recovery.factory_cal_ibis_defectpixel_and_nvs_verifier"),
    (15, "secureboot_chain_and_partition_align_verifier", "Phase 134", "fx3_recovery.secureboot_chain_and_partition_align_verifier"),
    (16, "realhw_ext2_installer_and_p1_rescue_verifier", "Phase 138", "fx3_recovery.realhw_ext2_installer_and_p1_rescue_verifier"),
    (17, "realhw_adjustcontrol_streaming_backup_client", "Phase 139", "fx3_recovery.realhw_adjustcontrol_streaming_backup_client"),
    (18, "realhw_service_usb_session_and_libjit_elf_hardener", "Phase 144", "fx3_recovery.realhw_service_usb_session_and_libjit_elf_hardener"),
    (19, "realhw_pnflasha_cnflasha_mtdro_tier0_vault_verifier", "Phase 151", "fx3_recovery.realhw_pnflasha_cnflasha_mtdro_tier0_vault_verifier"),
    (20, "realhw_uart_460800_post_triage_and_isp_guard", "Phase 155", "fx3_recovery.realhw_uart_460800_post_triage_and_isp_guard"),
    (21, "realhw_bootrom_el3_and_ufu_stock_reflash_verifier", "Phase 160", "fx3_recovery.realhw_bootrom_el3_and_ufu_stock_reflash_verifier"),
    (22, "realhw_22pillar_master_recovery_verifier", "Phase 166", "fx3_recovery.realhw_22pillar_master_recovery_verifier"),
)
MASTER_22_PILLAR_IDS: Tuple[str, ...] = tuple(spec[1] for spec in MASTER_22_PILLAR_SPECS)
MASTER_22_PILLAR_COUNT: int = len(MASTER_22_PILLAR_SPECS)

# Scenario IDs
P166_PILLAR_A_SCENARIO_IDS: Tuple[str, ...] = (
    "P22A1_HAPPY_DUAL_MEDIA_NVME_PLUS_SSD_16_SURFACES",
    "P22A2_BLOCKED_SINGLE_MEDIUM_BACKUP_ONLY",
    "P22A3_BLOCKED_SAME_DEVICE_ID_DUPLICATE_PATH",
    "P22A4_BLOCKED_MISSING_P2_PSD_DEFDET_OR_P18_LENSFILE",
    "P22A5_BLOCKED_INVALID_OR_MISMATCHED_FX3RCPT1",
    "P22A6_BLOCKED_DUAL_MEDIA_MANIFEST_DRIFT",
)
P166_PILLAR_B_SCENARIO_IDS: Tuple[str, ...] = (
    "P22B1_HAPPY_ZERO_BITROT_16_OF_16_RAM_PRERESTORE",
    "P22B2_HEALED_1_CHUNK_SILENT_BITROT_GF256_SYNDROME",
    "P22B3_HEALED_2_CHUNK_SIMULTANEOUS_BITROT_GF256_PQ",
    "P22B4_HEALED_DATA_PLUS_PARITY_BITROT_GF256",
    "P22B5_BLOCKED_3_CHUNK_QUORUM_LOSS_FAIL_CLOSED",
    "P22B6_BLOCKED_CROSS_DOMAIN_OR_WRITE_UNLOCK_IN_REHEARSAL",
)

# Pinned FX3 7.02 Donor Relpaths & Digests (strictly O_RDONLY, zero raw bytes emitted)
P166_DONOR_FX3_PARTINF_RELPATH: str = (
    "sony-firmware-20261024/stage182-boot-selector-and-recovery-admission/"
    "current-updater-evidence/tar-selected/0300_partconf/partinf.conf"
)
P166_DONOR_FX3_MOUNT_RELPATH: str = (
    "sony-firmware-20261024/stage182-boot-selector-and-recovery-admission/"
    "current-updater-evidence/tar-selected/0100_config/mount.conf"
)
P166_DONOR_FX3_LOADER_NOR_RELPATH: str = (
    "sony-firmware-20261024/stage182-boot-selector-and-recovery-admission/"
    "current-updater-evidence/nor-loader-members/loader_nor.bin"
)
P166_DONOR_FX3_P1_205_RELPATH: str = (
    "fx3-color-port-20261027/input-20261028/original-update-engine/2.05/nflasha1"
)
P166_DONOR_FX3_BACKUP_BIN_RELPATH: str = (
    "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin"
)
P166_DONOR_FX3_CPAPP_B_RELPATH: str = (
    "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin"
)
P166_DONOR_FX3_NFLASHA15_RELPATH: str = (
    "sony-firmware-20261024/stage2/extraction/nflasha15.img"
)

P166_PINNED_FX3_PARTINF_BYTES: int = 3999
P166_PINNED_FX3_PARTINF_SHA256: str = "3d96228d4ed2db3cb4295aa854edf0ad8895440167f132144cdec4f8cfdad189"
P166_PINNED_FX3_MOUNT_BYTES: int = 1248
P166_PINNED_FX3_MOUNT_SHA256: str = "ea0132091f3bb8d675b3ae7aecfbb1ca2459864a2e2812c0f7dd66fbb877d1a3"
P166_PINNED_FX3_LOADER_NOR_BYTES: int = 101888
P166_PINNED_FX3_LOADER_NOR_SHA256: str = "4358c839cfb1f22d5eb4e53d67817c42c4e877ba8b0aff375d355ce6294c4942"
P166_PINNED_FX3_P1_205_BYTES: int = 19377152
P166_PINNED_FX3_P1_205_SHA256: str = "ab2cd5372fed3c742b586e28484c6bf0aa6ebfba1f6d8e450a19191abc5b6591"
P166_PINNED_FX3_BACKUP_BIN_BYTES: int = 2229740
P166_PINNED_FX3_BACKUP_BIN_SHA256: str = "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2"
P166_PINNED_FX3_CPAPP_B_BYTES: int = 15980568
P166_PINNED_FX3_CPAPP_B_HDR4K_SHA256: str = "452c9e4e05fc1942baeee8ea9d531eeaaab99091576bc59eaa46f2d272050d5d"
P166_PINNED_FX3_NFLASHA15_BYTES: int = 479846400
P166_PINNED_FX3_NFLASHA15_HDR4K_SHA256: str = "6d05ebbd28c554d1d9dcc54503face9af111170befaf2ca2a19c52d7bd8910d6"

# Status & Fail-Closed Error Codes
P166_STATUS_VERIFIED_SUITE: str = "VERIFIED_22PILLAR_REALHW_RECOVERY_MASTER"
P166_STATUS_FAIL_SUITE: str = "FAIL_22PILLAR_REALHW_RECOVERY_MASTER"
P166_STATUS_VERIFIED_PILLAR_A: str = "VERIFIED_DUAL_MEDIA_COLD_BACKUP_AND_FX3RCPT1"
P166_STATUS_REJECTED_PILLAR_A: str = "REJECTED_DUAL_MEDIA_COLD_BACKUP_OR_FX3RCPT1"
P166_STATUS_VERIFIED_PILLAR_B: str = "VERIFIED_GF256_BITROT_SCRUB_AND_16OF16_PRERESTORE"
P166_STATUS_REJECTED_PILLAR_B: str = "REJECTED_GF256_BITROT_SCRUB_OR_16OF16_PRERESTORE"
P166_STATUS_VERIFIED_22OF22_AGGREGATOR: str = "VERIFIED_22OF22_PILLAR_RECOVERY_MASTER"
P166_STATUS_FAIL_22OF22_AGGREGATOR: str = "FAIL_22OF22_PILLAR_RECOVERY_MASTER"

BLOCKED_SINGLE_MEDIA_COLD_BACKUP_INSUFFICIENT: str = "BLOCKED_SINGLE_MEDIA_COLD_BACKUP_INSUFFICIENT"
BLOCKED_SAME_PHYSICAL_MEDIUM_FORBIDDEN: str = "BLOCKED_SAME_PHYSICAL_MEDIUM_FORBIDDEN"
BLOCKED_DUAL_MEDIA_MANIFEST_DRIFT: str = "BLOCKED_DUAL_MEDIA_MANIFEST_DRIFT"
BLOCKED_MISSING_16_SURFACE_COLD_BACKUP: str = "BLOCKED_MISSING_16_SURFACE_COLD_BACKUP"
BLOCKED_MISSING_CRITICAL_CAL_FILES: str = "BLOCKED_MISSING_CRITICAL_P2_OR_P18_CAL_FILES"
BLOCKED_INVALID_FX3RCPT1_RECEIPT: str = "BLOCKED_INVALID_OR_TAMPERED_FX3RCPT1_RECEIPT"
BLOCKED_CROSS_CAMERA_VAULT_IDENTITY_MISMATCH: str = "BLOCKED_CROSS_CAMERA_VAULT_IDENTITY_MISMATCH"
BLOCKED_GF256_QUORUM_EXCEEDED_3_CHUNKS: str = "BLOCKED_GF256_QUORUM_EXCEEDED_3_OR_MORE_CHUNKS"
BLOCKED_CROSS_DOMAIN_RESTORE_OR_WRITE_LOCKED: str = "BLOCKED_CROSS_DOMAIN_RESTORE_OR_WRITE_LOCKED"
BLOCKED_STAGE_A_STAGING_PRECONDITION_FAILED: str = "BLOCKED_STAGE_A_STAGING_PRECONDITION_FAILED"
BLOCKED_SAFETY_POLICY_INVARIANT_VIOLATION: str = "BLOCKED_SAFETY_POLICY_INVARIANT_VIOLATION"

_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")
_SURFACE_SPEC_MAP: Dict[str, Tier0SurfaceSpec] = {s.surface_id: s for s in TIER0_16_SURFACES}


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------


def _canonical_sha256(obj: Any) -> str:
    payload = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(payload).hexdigest()


def _need(cond: bool, msg: str) -> None:
    if not cond:
        raise ValueError(msg)


def _open_rdonly_bounded_inspect(
    relpath: str,
    *,
    max_read_bytes: Optional[int] = None,
    compute_full_sha_under_limit: int = 20 * 1024 * 1024,
) -> Tuple[Optional[bytes], Optional[int], Optional[str], Optional[str]]:
    """Open regular donor file strictly with `os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK`."""
    p = resolve_donor_path(relpath, require_file=True)
    if p is None or not p.is_file():
        return None, None, None, None
    checked = local_path(p, allow_donor_roots=True)
    fd = os.open(checked, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        st_before = os.fstat(fd)
        _need(stat.S_ISREG(st_before.st_mode) and st_before.st_nlink == 1, "donor must be single-link regular file")
        total_size = int(st_before.st_size)
        if max_read_bytes is not None:
            head_len = min(total_size, max_read_bytes)
            head = os.pread(fd, head_len, 0) if hasattr(os, "pread") else b""
            if not head and head_len > 0:
                with os.fdopen(os.dup(fd), "rb") as f:
                    head = f.read(head_len)
            hdr_sha = sha256(head).hexdigest()
            return head, total_size, None, hdr_sha
        if total_size <= compute_full_sha_under_limit:
            with os.fdopen(os.dup(fd), "rb") as f:
                data = f.read(total_size + 1)
            _need(len(data) == total_size, "donor size changed during read")
            full_sha = sha256(data).hexdigest()
            hdr_sha = sha256(data[:P166_BOUNDED_HEADER_BYTES]).hexdigest()
            return data, total_size, full_sha, hdr_sha
        head = os.pread(fd, min(total_size, P166_BOUNDED_HEADER_BYTES), 0)
        return head, total_size, None, sha256(head).hexdigest()
    finally:
        os.close(fd)


# ---------------------------------------------------------------------------
# Dataclasses (100% JSON-safe, zero raw proprietary firmware bytes)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase166DonorArtifactDigest:
    artifact_id: str
    relpath: str
    source_mode: str
    access_mode: str
    byte_length: int
    sha256_digest: str
    header_4k_sha256: Optional[str]
    verified_markers: Tuple[str, ...]
    passed: bool


@dataclass(frozen=True)
class Phase166DonorSnapshot:
    verification_mode: str
    access_mode: str
    donor_files_inspected: int
    raw_firmware_bytes_leaked: int
    partinf_partition_count: int
    mount_entries_verified: bool
    loader_nor_el3_ok: bool
    backup_bin_bk4_fx3_ok: bool
    nflasha15_ext2_magic_ok: bool
    artifacts: Tuple[Phase166DonorArtifactDigest, ...]
    snapshot_sha256: str
    all_passed: bool
    errors: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Fx3Rcpt1ReceiptInfo:
    valid: bool
    magic_hex: str
    version: int
    model_id: int
    surface_count: int
    flags: int
    body_serial_sha256: str
    emmc_cid_sha256: str
    manifest_sha256: str
    p2_cal_bundle_sha256: str
    p18_lensfile_sha256: str
    crc32_valid: bool
    errors: Tuple[str, ...] = ()


@dataclass(frozen=True)
class ColdBackupMediaCopy:
    media_label: str
    device_id: str
    hardware_uuid: str
    media_kind: str
    mount_point: str
    body_serial_sha256: str
    emmc_cid_sha256: str
    surface_sha256s: Dict[str, str]
    surface_domains: Dict[str, str]
    p2_setting_files: Dict[str, str]
    p18_lens_files: Dict[str, str]
    fx3rcpt1_receipt_hex: str
    manifest_sha256: str


@dataclass(frozen=True)
class DualMediaBackupAuditReport:
    passed: bool
    status: str
    stage_a_staging_permitted: bool
    media_a_present: bool
    media_b_present: bool
    distinct_physical_media: bool
    media_a_device_id: str
    media_b_device_id: str
    media_a_kind: str
    media_b_kind: str
    surface_count_a: int
    surface_count_b: int
    all_16_surfaces_present: bool
    dual_media_manifest_match: bool
    p2_setting_files_verified: bool
    p18_lensfile_verified: bool
    fx3rcpt1_valid: bool
    identity_bound_ok: bool
    blocked_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    persistent_emmc_writes_authorized: bool = PERSISTENT_EMMC_WRITES_AUTHORIZED
    spi_nor_write_authorized: bool = SPI_NOR_WRITE_AUTHORIZED
    physical_device_writes: int = PHYSICAL_DEVICE_WRITES

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Gf256ArchiveBundle:
    surface_order: Tuple[str, ...]
    surface_sizes: Dict[str, int]
    surface_sha256s: Dict[str, str]
    surface_domains: Dict[str, str]
    stripe_bytes: int
    shards_bytes: Tuple[bytes, ...]
    p_parity: bytes
    q_parity: bytes
    p_sha256: str
    q_sha256: str
    archive_manifest_sha256: str


@dataclass(frozen=True)
class SurfaceDryRunCheck:
    surface_id: str
    layer_domain: str
    passed: bool
    domain_ok: bool
    magic_ok: bool
    sha256_exact: bool
    original_sha256: str
    reconstructed_sha256: str
    errors: Tuple[str, ...] = ()


@dataclass(frozen=True)
class BitRotScrubAndPreRestoreReport:
    passed: bool
    status: str
    gf256_polynomial_hex: str
    repair_mode: str
    injected_bitrot_chunks: Tuple[str, ...]
    corrupted_chunk_count: int
    healed_chunks: Tuple[str, ...]
    surfaces_verified_count: int
    surfaces_total_count: int
    prerestore_16of16_exact: bool
    archive_manifest_sha256: str
    reconstructed_manifest_sha256: str
    surface_checks: Tuple[SurfaceDryRunCheck, ...]
    blocked_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    physical_device_writes: int = PHYSICAL_DEVICE_WRITES
    persistent_emmc_writes_authorized: bool = PERSISTENT_EMMC_WRITES_AUTHORIZED
    spi_nor_write_authorized: bool = SPI_NOR_WRITE_AUTHORIZED
    el3_payload_transmit_authorized: bool = EL3_PAYLOAD_TRANSMIT_AUTHORIZED
    isp_write_authorized: bool = ISP_WRITE_AUTHORIZED

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Pillar22AScenarioOutcome:
    scenario_id: str
    passed: bool
    stage_a_staging_permitted: bool
    blocked_codes: Tuple[str, ...]
    summary: str


@dataclass(frozen=True)
class Pillar22AScenarioSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar22AScenarioOutcome, ...]
    physical_device_writes: int = PHYSICAL_DEVICE_WRITES
    persistent_emmc_writes_authorized: bool = PERSISTENT_EMMC_WRITES_AUTHORIZED

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Pillar22BScenarioOutcome:
    scenario_id: str
    passed: bool
    repair_mode: str
    corrupted_chunk_count: int
    prerestore_16of16_exact: bool
    blocked_codes: Tuple[str, ...]
    summary: str


@dataclass(frozen=True)
class Pillar22BScenarioSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar22BScenarioOutcome, ...]
    physical_device_writes: int = PHYSICAL_DEVICE_WRITES
    persistent_emmc_writes_authorized: bool = PERSISTENT_EMMC_WRITES_AUTHORIZED

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Pillar22StandaloneReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    donor_snapshot: Phase166DonorSnapshot
    pillar_a_dual_media_6_scenarios: Pillar22AScenarioSuiteResult
    pillar_b_gf256_scrub_6_scenarios: Pillar22BScenarioSuiteResult
    suite_sha256: str
    physical_device_writes: int = PHYSICAL_DEVICE_WRITES
    persistent_emmc_writes_authorized: bool = PERSISTENT_EMMC_WRITES_AUTHORIZED
    spi_nor_write_authorized: bool = SPI_NOR_WRITE_AUTHORIZED
    errors: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MasterPillarStatus:
    pillar_number: int
    pillar_id: str
    phase_label: str
    module_name: str
    passed: bool
    status: str
    verification_mode: str
    elapsed_seconds: float
    key_metrics: Dict[str, Any]
    digest_sha256: str
    errors: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master22PillarRecoveryReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    pillar_count: int
    pillars_passed: int
    failed_pillars: Tuple[str, ...]
    elapsed_seconds: float
    under_2s_budget: bool
    pillars: Tuple[MasterPillarStatus, ...]
    donor_snapshot: Phase166DonorSnapshot
    pillar22_a_dual_media: Pillar22AScenarioSuiteResult
    pillar22_b_gf256_scrub: Pillar22BScenarioSuiteResult
    master_22pillar_sha256: str
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
# 1. Dual-Mode Donor Inspection (`os.O_RDONLY`) + Clean-Room Fallback
# ---------------------------------------------------------------------------


def inspect_phase166_donors_readonly(*, force_clean_room: Optional[bool] = None) -> Phase166DonorSnapshot:
    """Inspect FX3 `7.02` donor artifacts strictly via `os.O_RDONLY` or deterministic clean-room fallback."""
    forced = is_forced_clean_room() if force_clean_room is None else bool(force_clean_room)
    if forced:
        artifacts = (
            Phase166DonorArtifactDigest(
                "fx3_partinf_conf",
                P166_DONOR_FX3_PARTINF_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA_ONLY",
                P166_PINNED_FX3_PARTINF_BYTES,
                P166_PINNED_FX3_PARTINF_SHA256,
                None,
                ("30_PARTITIONS", "P2_SETTING", "P18_LENS_0x31C000"),
                True,
            ),
            Phase166DonorArtifactDigest(
                "fx3_mount_conf",
                P166_DONOR_FX3_MOUNT_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA_ONLY",
                P166_PINNED_FX3_MOUNT_BYTES,
                P166_PINNED_FX3_MOUNT_SHA256,
                None,
                ("MOUNT_SETTING", "MOUNT_LENS", "MOUNT_USR"),
                True,
            ),
            Phase166DonorArtifactDigest(
                "fx3_loader_nor_bin",
                P166_DONOR_FX3_LOADER_NOR_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA_ONLY",
                P166_PINNED_FX3_LOADER_NOR_BYTES,
                P166_PINNED_FX3_LOADER_NOR_SHA256,
                None,
                ("EL3_VBAR_0xD51EC001", "SPI_NOR_MTD0RO"),
                True,
            ),
            Phase166DonorArtifactDigest(
                "fx3_p1_205",
                P166_DONOR_FX3_P1_205_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA_ONLY",
                P166_PINNED_FX3_P1_205_BYTES,
                P166_PINNED_FX3_P1_205_SHA256,
                None,
                ("FAT12_0x55AA", "UPDATER_P1"),
                True,
            ),
            Phase166DonorArtifactDigest(
                "fx3_backup_bin",
                P166_DONOR_FX3_BACKUP_BIN_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA_ONLY",
                P166_PINNED_FX3_BACKUP_BIN_BYTES,
                P166_PINNED_FX3_BACKUP_BIN_SHA256,
                None,
                ("BK4_MAGIC", "0xAAAAAAAA", "ILME-FX3"),
                True,
            ),
            Phase166DonorArtifactDigest(
                "fx3_cpapp_b",
                P166_DONOR_FX3_CPAPP_B_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA_ONLY",
                P166_PINNED_FX3_CPAPP_B_BYTES,
                P166_PINNED_FX3_CPAPP_B_HDR4K_SHA256,
                P166_PINNED_FX3_CPAPP_B_HDR4K_SHA256,
                ("BOUNDED_4K_HEADER", "CPAPP_P8"),
                True,
            ),
            Phase166DonorArtifactDigest(
                "fx3_nflasha15_img",
                P166_DONOR_FX3_NFLASHA15_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA_ONLY",
                P166_PINNED_FX3_NFLASHA15_BYTES,
                P166_PINNED_FX3_NFLASHA15_HDR4K_SHA256,
                P166_PINNED_FX3_NFLASHA15_HDR4K_SHA256,
                ("BOUNDED_4K_SUPERBLOCK", "EXT2_0xEF53"),
                True,
            ),
        )
        snap_sha = _canonical_sha256({"mode": "CLEAN_ROOM_SYNTHETIC", "artifacts": [asdict(a) for a in artifacts]})
        return Phase166DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="SYNTHETIC_METADATA_ONLY",
            donor_files_inspected=0,
            raw_firmware_bytes_leaked=0,
            partinf_partition_count=30,
            mount_entries_verified=True,
            loader_nor_el3_ok=True,
            backup_bin_bk4_fx3_ok=True,
            nflasha15_ext2_magic_ok=True,
            artifacts=artifacts,
            snapshot_sha256=snap_sha,
            all_passed=True,
            errors=(),
        )

    specs = (
        ("fx3_partinf_conf", P166_DONOR_FX3_PARTINF_RELPATH, P166_PINNED_FX3_PARTINF_BYTES, P166_PINNED_FX3_PARTINF_SHA256, None),
        ("fx3_mount_conf", P166_DONOR_FX3_MOUNT_RELPATH, P166_PINNED_FX3_MOUNT_BYTES, P166_PINNED_FX3_MOUNT_SHA256, None),
        ("fx3_loader_nor_bin", P166_DONOR_FX3_LOADER_NOR_RELPATH, P166_PINNED_FX3_LOADER_NOR_BYTES, P166_PINNED_FX3_LOADER_NOR_SHA256, None),
        ("fx3_p1_205", P166_DONOR_FX3_P1_205_RELPATH, P166_PINNED_FX3_P1_205_BYTES, P166_PINNED_FX3_P1_205_SHA256, None),
        ("fx3_backup_bin", P166_DONOR_FX3_BACKUP_BIN_RELPATH, P166_PINNED_FX3_BACKUP_BIN_BYTES, P166_PINNED_FX3_BACKUP_BIN_SHA256, None),
        ("fx3_cpapp_b", P166_DONOR_FX3_CPAPP_B_RELPATH, P166_PINNED_FX3_CPAPP_B_BYTES, P166_PINNED_FX3_CPAPP_B_HDR4K_SHA256, P166_BOUNDED_HEADER_BYTES),
        ("fx3_nflasha15_img", P166_DONOR_FX3_NFLASHA15_RELPATH, P166_PINNED_FX3_NFLASHA15_BYTES, P166_PINNED_FX3_NFLASHA15_HDR4K_SHA256, P166_BOUNDED_HEADER_BYTES),
    )

    resolved_paths = [resolve_donor_path(rel, require_file=True) for _, rel, _, _, _ in specs]
    if any(p is None or not p.is_file() for p in resolved_paths):
        return inspect_phase166_donors_readonly(force_clean_room=True)

    artifacts_out: List[Phase166DonorArtifactDigest] = []
    errors: List[str] = []
    partinf_count = 0
    mount_ok = False
    loader_ok = False
    backup_ok = False
    ext2_ok = False

    for label, relpath, exp_bytes, exp_sha, bounded_lim in specs:
        raw, total_sz, full_sha, hdr_sha = _open_rdonly_bounded_inspect(relpath, max_read_bytes=bounded_lim)
        if raw is None or total_sz is None:
            return inspect_phase166_donors_readonly(force_clean_room=True)
        markers: List[str] = []
        item_ok = total_sz == exp_bytes
        if not item_ok:
            errors.append(f"{label}: size {total_sz} != {exp_bytes}")

        if bounded_lim is not None:
            digest = hdr_sha or ""
            if label == "fx3_cpapp_b":
                if hdr_sha == exp_sha:
                    markers.extend(["BOUNDED_4K_HEADER", "CPAPP_P8"])
                else:
                    item_ok = False
                    errors.append(f"fx3_cpapp_b: hdr4k sha mismatch {hdr_sha}")
            elif label == "fx3_nflasha15_img":
                ext2_magic = struct.unpack_from("<H", raw, 1024 + 56)[0] if len(raw) >= 1082 else 0
                ext2_ok = (ext2_magic == 0xEF53) and (hdr_sha == exp_sha)
                if ext2_ok:
                    markers.extend(["BOUNDED_4K_SUPERBLOCK", "EXT2_0xEF53"])
                else:
                    item_ok = False
                    errors.append(f"fx3_nflasha15_img: ext2 magic={ext2_magic:#x} or hdr4k mismatch")
        else:
            digest = full_sha or ""
            if digest != exp_sha:
                item_ok = False
                errors.append(f"{label}: sha256 mismatch")
            if label == "fx3_partinf_conf":
                txt = raw.decode("utf-8", errors="replace")
                rows = re.findall(r"^0x[0-9A-Fa-f]+,0x[0-9A-Fa-f]+,0x[0-9A-Fa-f]+,0x[0-9A-Fa-f]+", txt, flags=re.M)
                partinf_count = len(rows)
                if partinf_count == 30 and "0x0031c000" in txt.lower():
                    markers.extend(["30_PARTITIONS", "P2_SETTING", "P18_LENS_0x31C000"])
                else:
                    item_ok = False
                    errors.append(f"fx3_partinf_conf: unexpected rows={partinf_count}")
            elif label == "fx3_mount_conf":
                txt = raw.decode("utf-8", errors="replace")
                mount_ok = ("/setting" in txt) and ("/lens" in txt) and ("/usr" in txt)
                if mount_ok:
                    markers.extend(["MOUNT_SETTING", "MOUNT_LENS", "MOUNT_USR"])
                else:
                    item_ok = False
                    errors.append("fx3_mount_conf: missing /setting /lens /usr")
            elif label == "fx3_loader_nor_bin":
                loader_ok = b"\x01\xc0\x1e\xd5" in raw[:512]
                if loader_ok:
                    markers.extend(["EL3_VBAR_0xD51EC001", "SPI_NOR_MTD0RO"])
                else:
                    item_ok = False
                    errors.append("fx3_loader_nor_bin: missing EL3 VBAR_EL3 prologue")
            elif label == "fx3_p1_205":
                if len(raw) >= 512 and raw[510:512] == b"\x55\xaa":
                    markers.extend(["FAT12_0x55AA", "UPDATER_P1"])
                else:
                    item_ok = False
                    errors.append("fx3_p1_205: missing VFAT 0x55AA boot signature")
            elif label == "fx3_backup_bin":
                sync_u32 = struct.unpack_from("<I", raw, 4)[0] if len(raw) >= 20 else 0
                bk_magic = raw[12:16] if len(raw) >= 16 else b""
                subsystems = struct.unpack_from("<I", raw, 16)[0] if len(raw) >= 20 else 0
                backup_ok = (sync_u32 == 0xAAAAAAAA) and (bk_magic == b"BK4\x00") and (subsystems == 819) and (b"ILME-FX3" in raw)
                if backup_ok:
                    markers.extend(["BK4_MAGIC", "0xAAAAAAAA", "ILME-FX3"])
                else:
                    item_ok = False
                    errors.append("fx3_backup_bin: missing BK4/0xAAAAAAAA/ILME-FX3")

        artifacts_out.append(
            Phase166DonorArtifactDigest(
                artifact_id=label,
                relpath=relpath,
                source_mode="LOCAL_DONOR_O_RDONLY",
                access_mode="O_RDONLY_BOUNDED",
                byte_length=total_sz,
                sha256_digest=digest,
                header_4k_sha256=hdr_sha,
                verified_markers=tuple(markers),
                passed=item_ok,
            )
        )

    all_ok = len(errors) == 0 and all(a.passed for a in artifacts_out)
    snap_sha = _canonical_sha256({"mode": "LOCAL_DONOR_O_RDONLY", "artifacts": [asdict(a) for a in artifacts_out]})
    return Phase166DonorSnapshot(
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="O_RDONLY_BOUNDED",
        donor_files_inspected=len(artifacts_out),
        raw_firmware_bytes_leaked=0,
        partinf_partition_count=partinf_count,
        mount_entries_verified=mount_ok,
        loader_nor_el3_ok=loader_ok,
        backup_bin_bk4_fx3_ok=backup_ok,
        nflasha15_ext2_magic_ok=ext2_ok,
        artifacts=tuple(artifacts_out),
        snapshot_sha256=snap_sha,
        all_passed=all_ok,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# 2. Pillar 22A: Dual-Media Cold-Backup Archive & FX3RCPT1 Receipt Firewall
# ---------------------------------------------------------------------------


def build_fx3rcpt1_receipt(
    *,
    body_serial_sha256: str,
    emmc_cid_sha256: str,
    manifest_sha256: str,
    p2_cal_bundle_sha256: str,
    p18_lensfile_sha256: str,
    model_id: int = P166_FX3_MODEL_ID,
    surface_count: int = 16,
    flags: int = P166_FX3RCPT1_FLAGS_DUAL_MEDIA_READY,
) -> bytes:
    """Build a deterministic 528-byte `FX3RCPT1` cold-backup verification receipt."""
    for label, digest in (
        ("body_serial_sha256", body_serial_sha256),
        ("emmc_cid_sha256", emmc_cid_sha256),
        ("manifest_sha256", manifest_sha256),
        ("p2_cal_bundle_sha256", p2_cal_bundle_sha256),
        ("p18_lensfile_sha256", p18_lensfile_sha256),
    ):
        _need(bool(_SHA256_HEX_RE.match(digest)), f"invalid sha256 for {label}")

    hdr = struct.pack(
        "<8sIIII",
        P166_FX3RCPT1_MAGIC,
        P166_FX3RCPT1_VERSION,
        model_id,
        surface_count,
        flags,
    )
    body = (
        hdr
        + bytes.fromhex(body_serial_sha256)
        + bytes.fromhex(emmc_cid_sha256)
        + bytes.fromhex(manifest_sha256)
        + bytes.fromhex(p2_cal_bundle_sha256)
        + bytes.fromhex(p18_lensfile_sha256)
    )
    pad_len = P166_FX3RCPT1_BYTES - 4 - len(body)
    _need(pad_len >= 0, "FX3RCPT1 body exceeds 524 bytes")
    payload = body + (b"\x00" * pad_len)
    crc = zlib.crc32(payload) & 0xFFFFFFFF
    receipt = payload + struct.pack("<I", crc)
    _need(len(receipt) == P166_FX3RCPT1_BYTES, "FX3RCPT1 must be exactly 528 bytes")
    return receipt


def parse_fx3rcpt1_receipt(raw: bytes) -> Fx3Rcpt1ReceiptInfo:
    """Parse and validate a 528-byte `FX3RCPT1` cold-backup receipt."""
    if not isinstance(raw, (bytes, bytearray)) or len(raw) != P166_FX3RCPT1_BYTES:
        return Fx3Rcpt1ReceiptInfo(
            valid=False,
            magic_hex=bytes(raw[:8]).hex() if isinstance(raw, (bytes, bytearray)) else "",
            version=0,
            model_id=0,
            surface_count=0,
            flags=0,
            body_serial_sha256="",
            emmc_cid_sha256="",
            manifest_sha256="",
            p2_cal_bundle_sha256="",
            p18_lensfile_sha256="",
            crc32_valid=False,
            errors=(f"{BLOCKED_INVALID_FX3RCPT1_RECEIPT}:length={len(raw) if isinstance(raw, (bytes, bytearray)) else -1}",),
        )
    buf = bytes(raw)
    magic, version, model_id, surface_count, flags = struct.unpack_from("<8sIIII", buf, 0)
    crc_stored = struct.unpack_from("<I", buf, P166_FX3RCPT1_BYTES - 4)[0]
    crc_calc = zlib.crc32(buf[: P166_FX3RCPT1_BYTES - 4]) & 0xFFFFFFFF
    crc_ok = crc_stored == crc_calc
    errs: List[str] = []
    if magic != P166_FX3RCPT1_MAGIC:
        errs.append(f"{BLOCKED_INVALID_FX3RCPT1_RECEIPT}:bad_magic={magic.hex()}")
    if version != P166_FX3RCPT1_VERSION:
        errs.append(f"{BLOCKED_INVALID_FX3RCPT1_RECEIPT}:bad_version={version}")
    if model_id != P166_FX3_MODEL_ID:
        errs.append(f"{BLOCKED_INVALID_FX3RCPT1_RECEIPT}:bad_model_id={model_id:#x}")
    if surface_count != 16:
        errs.append(f"{BLOCKED_INVALID_FX3RCPT1_RECEIPT}:bad_surface_count={surface_count}")
    if not crc_ok:
        errs.append(f"{BLOCKED_INVALID_FX3RCPT1_RECEIPT}:crc32_mismatch")

    return Fx3Rcpt1ReceiptInfo(
        valid=len(errs) == 0,
        magic_hex=magic.hex(),
        version=version,
        model_id=model_id,
        surface_count=surface_count,
        flags=flags,
        body_serial_sha256=buf[24:56].hex(),
        emmc_cid_sha256=buf[56:88].hex(),
        manifest_sha256=buf[88:120].hex(),
        p2_cal_bundle_sha256=buf[120:152].hex(),
        p18_lensfile_sha256=buf[152:184].hex(),
        crc32_valid=crc_ok,
        errors=tuple(errs),
    )


def build_synthetic_16_surface_chunks(
    *,
    body_tag: str = "fx3-unit-primary",
) -> Tuple[Dict[str, bytes], Dict[str, str], Dict[str, str]]:
    """Build deterministic clean-room 16-surface Tier-0 chunks + p2/p18 calibration files."""
    tag_bytes = body_tag.encode("utf-8")
    chunks: Dict[str, bytes] = {
        "sector0": build_synthetic_fx3_sector0_30_partitions(),
        "p1": build_synthetic_vfat_sample(marker=b"DAT2=91030080"),
        "p2": build_synthetic_bk4_sample(),
        "p3": build_synthetic_high_entropy_spacc_sample(seed_tag=tag_bytes + b"-p3"),
        "p5": build_synthetic_wbi2_sample(),
        "p6": build_synthetic_vfat_sample(marker=b"JIRITSU_P6_STAGING"),
        "p7": build_synthetic_high_entropy_spacc_sample(seed_tag=tag_bytes + b"-p7"),
        "p8": build_synthetic_high_entropy_spacc_sample(seed_tag=tag_bytes + b"-p8"),
        "p12": build_synthetic_high_entropy_spacc_sample(seed_tag=tag_bytes + b"-p12-cert"),
        "p13": build_synthetic_vfat_sample(marker=b"UPDATER_WORK_NVS"),
        "p15": build_synthetic_high_entropy_spacc_sample(seed_tag=tag_bytes + b"-p15-usr"),
        "p18": build_synthetic_vfat_sample(marker=LENS_VX8900_MAGIC + b":LENSFILE.BIN"),
        "p23": build_synthetic_high_entropy_spacc_sample(seed_tag=tag_bytes + b"-p23-bk4"),
        "p30": build_synthetic_high_entropy_spacc_sample(seed_tag=tag_bytes + b"-p30-lut"),
        "spi_nor_mtd0ro": build_synthetic_spi_nor_sample(),
        "emmc_ext_csd": build_synthetic_ext_csd_sample(),
    }
    p2_files = {
        "psd.bin": sha256(f"{body_tag}:p2:/setting/psd.bin".encode("utf-8")).hexdigest(),
        "defdet.bin": sha256(f"{body_tag}:p2:/setting/defdet.bin".encode("utf-8")).hexdigest(),
        "Backup.bin": sha256(f"{body_tag}:p2:/setting/Backup.bin:BK4".encode("utf-8")).hexdigest(),
    }
    p18_files = {
        "LENSFILE.BIN": sha256(f"{body_tag}:p18:/lens/LENSFILE.BIN:VX8900".encode("utf-8")).hexdigest(),
    }
    return chunks, p2_files, p18_files


def build_synthetic_dual_media_cold_backup(
    *,
    body_tag: str = "fx3-unit-primary",
    media_a_device_id: str = "disk3s1-host-nvme-vault",
    media_a_hardware_uuid: str = "NVME-A111-0001-FX3VAULT",
    media_a_kind: str = "HOST_NVME",
    media_a_mount: str = "/Users/operator/FX3_Vault",
    media_b_device_id: str = "disk5s1-ext-sandisk-ssd",
    media_b_hardware_uuid: str = "EXTSSD-B222-0002-FX3COLD",
    media_b_kind: str = "EXTERNAL_SSD",
    media_b_mount: str = "/Volumes/FX3_COLD_SSD",
) -> Tuple[ColdBackupMediaCopy, ColdBackupMediaCopy, Dict[str, bytes]]:
    """Build matching dual-media 16-surface Tier-0 cold-backup copies + `FX3RCPT1` receipt."""
    chunks, p2_files, p18_files = build_synthetic_16_surface_chunks(body_tag=body_tag)
    surface_shas = {sid: sha256(chunks[sid]).hexdigest() for sid in P166_MANDATORY_16_SURFACES}
    surface_domains = {sid: _SURFACE_SPEC_MAP[sid].primary_layer_domain for sid in P166_MANDATORY_16_SURFACES}

    body_serial_sha = sha256(f"BODY-SERIAL:{body_tag}".encode("utf-8")).hexdigest()
    emmc_cid_sha = sha256(f"EMMC-CID:{body_tag}".encode("utf-8")).hexdigest()
    p2_cal_bundle_sha = _canonical_sha256(p2_files)
    p18_lens_sha = p18_files["LENSFILE.BIN"]
    manifest_sha = _canonical_sha256(
        {
            "body_serial_sha256": body_serial_sha,
            "emmc_cid_sha256": emmc_cid_sha,
            "surface_sha256s": surface_shas,
            "p2_setting_files": p2_files,
            "p18_lens_files": p18_files,
        }
    )
    rcpt = build_fx3rcpt1_receipt(
        body_serial_sha256=body_serial_sha,
        emmc_cid_sha256=emmc_cid_sha,
        manifest_sha256=manifest_sha,
        p2_cal_bundle_sha256=p2_cal_bundle_sha,
        p18_lensfile_sha256=p18_lens_sha,
    )
    rcpt_hex = rcpt.hex()

    copy_a = ColdBackupMediaCopy(
        media_label="MEDIA_A",
        device_id=media_a_device_id,
        hardware_uuid=media_a_hardware_uuid,
        media_kind=media_a_kind,
        mount_point=media_a_mount,
        body_serial_sha256=body_serial_sha,
        emmc_cid_sha256=emmc_cid_sha,
        surface_sha256s=dict(surface_shas),
        surface_domains=dict(surface_domains),
        p2_setting_files=dict(p2_files),
        p18_lens_files=dict(p18_files),
        fx3rcpt1_receipt_hex=rcpt_hex,
        manifest_sha256=manifest_sha,
    )
    copy_b = ColdBackupMediaCopy(
        media_label="MEDIA_B",
        device_id=media_b_device_id,
        hardware_uuid=media_b_hardware_uuid,
        media_kind=media_b_kind,
        mount_point=media_b_mount,
        body_serial_sha256=body_serial_sha,
        emmc_cid_sha256=emmc_cid_sha,
        surface_sha256s=dict(surface_shas),
        surface_domains=dict(surface_domains),
        p2_setting_files=dict(p2_files),
        p18_lens_files=dict(p18_files),
        fx3rcpt1_receipt_hex=rcpt_hex,
        manifest_sha256=manifest_sha,
    )
    return copy_a, copy_b, chunks


def verify_dual_media_cold_backup_vault(
    media_a: Optional[ColdBackupMediaCopy],
    media_b: Optional[ColdBackupMediaCopy],
    *,
    expected_body_serial_sha256: Optional[str] = None,
    expected_emmc_cid_sha256: Optional[str] = None,
    stage_a_staging_requested: bool = True,
    request_persistent_write_unlock: bool = False,
) -> DualMediaBackupAuditReport:
    """Enforce dual-media independence, 16-surface completeness, p2/p18 calibration files, and FX3RCPT1 receipt."""
    blocked: List[str] = []
    errors: List[str] = []

    if request_persistent_write_unlock:
        blocked.append(BLOCKED_SAFETY_POLICY_INVARIANT_VIOLATION)
        errors.append("Persistent eMMC/SPI-NOR write unlock request denied (hard-locked False)")

    media_a_present = media_a is not None
    media_b_present = media_b is not None
    if not media_a_present or not media_b_present:
        blocked.append(BLOCKED_SINGLE_MEDIA_COLD_BACKUP_INSUFFICIENT)
        errors.append("Mandatory dual-media cold backup missing at least one independent medium")
        return DualMediaBackupAuditReport(
            passed=False,
            status=P166_STATUS_REJECTED_PILLAR_A,
            stage_a_staging_permitted=False,
            media_a_present=media_a_present,
            media_b_present=media_b_present,
            distinct_physical_media=False,
            media_a_device_id=media_a.device_id if media_a else "",
            media_b_device_id=media_b.device_id if media_b else "",
            media_a_kind=media_a.media_kind if media_a else "",
            media_b_kind=media_b.media_kind if media_b else "",
            surface_count_a=len(media_a.surface_sha256s) if media_a else 0,
            surface_count_b=len(media_b.surface_sha256s) if media_b else 0,
            all_16_surfaces_present=False,
            dual_media_manifest_match=False,
            p2_setting_files_verified=False,
            p18_lensfile_verified=False,
            fx3rcpt1_valid=False,
            identity_bound_ok=False,
            blocked_codes=tuple(dict.fromkeys(blocked)),
            errors=tuple(errors),
        )

    assert media_a is not None and media_b is not None

    distinct_media = (
        bool(media_a.device_id.strip())
        and bool(media_b.device_id.strip())
        and (media_a.device_id.strip() != media_b.device_id.strip())
        and bool(media_a.hardware_uuid.strip())
        and bool(media_b.hardware_uuid.strip())
        and (media_a.hardware_uuid.strip() != media_b.hardware_uuid.strip())
        and (media_a.mount_point.strip() != media_b.mount_point.strip())
    )
    if not distinct_media:
        blocked.append(BLOCKED_SAME_PHYSICAL_MEDIUM_FORBIDDEN)
        errors.append(
            f"Dual-media violation: device_id/hardware_uuid/mount_point collided "
            f"({media_a.device_id} vs {media_b.device_id})"
        )

    if media_a.media_kind not in P166_VALID_MEDIA_KINDS or media_b.media_kind not in P166_VALID_MEDIA_KINDS:
        blocked.append(BLOCKED_SAME_PHYSICAL_MEDIUM_FORBIDDEN)
        errors.append(f"Invalid media_kind: {media_a.media_kind}, {media_b.media_kind}")

    missing_a = [s for s in P166_MANDATORY_16_SURFACES if not _SHA256_HEX_RE.match(media_a.surface_sha256s.get(s, ""))]
    missing_b = [s for s in P166_MANDATORY_16_SURFACES if not _SHA256_HEX_RE.match(media_b.surface_sha256s.get(s, ""))]
    all_16_ok = (len(missing_a) == 0) and (len(missing_b) == 0)
    if not all_16_ok:
        blocked.append(BLOCKED_MISSING_16_SURFACE_COLD_BACKUP)
        errors.append(f"Missing 16-surface entries: media_a={missing_a}, media_b={missing_b}")

    # Check domain tagging for all 16 surfaces
    for copy_tag, copy_obj in (("media_a", media_a), ("media_b", media_b)):
        for sid, spec in _SURFACE_SPEC_MAP.items():
            dom = copy_obj.surface_domains.get(sid)
            if dom != spec.primary_layer_domain:
                blocked.append(BLOCKED_CROSS_DOMAIN_RESTORE_OR_WRITE_LOCKED)
                errors.append(f"{copy_tag}:{sid} domain={dom} != expected {spec.primary_layer_domain}")

    # Verify p2:/setting/{psd.bin,defdet.bin,Backup.bin} and p18:/lens/LENSFILE.BIN
    p2_ok = all(
        _SHA256_HEX_RE.match(media_a.p2_setting_files.get(fn, ""))
        and media_a.p2_setting_files.get(fn) == media_b.p2_setting_files.get(fn)
        for fn in P166_MANDATORY_P2_SETTING_FILES
    )
    p18_ok = all(
        _SHA256_HEX_RE.match(media_a.p18_lens_files.get(fn, ""))
        and media_a.p18_lens_files.get(fn) == media_b.p18_lens_files.get(fn)
        for fn in P166_MANDATORY_P18_LENS_FILES
    )
    if not p2_ok or not p18_ok:
        blocked.append(BLOCKED_MISSING_CRITICAL_CAL_FILES)
        errors.append(f"Critical calibration files invalid/missing: p2_ok={p2_ok}, p18_ok={p18_ok}")

    # Dual-media SHA-256 manifest parity
    surface_parity = all(
        media_a.surface_sha256s.get(sid) == media_b.surface_sha256s.get(sid)
        for sid in P166_MANDATORY_16_SURFACES
    )
    manifest_match = (
        surface_parity
        and bool(_SHA256_HEX_RE.match(media_a.manifest_sha256))
        and (media_a.manifest_sha256 == media_b.manifest_sha256)
    )
    if not manifest_match:
        blocked.append(BLOCKED_DUAL_MEDIA_MANIFEST_DRIFT)
        errors.append("Media A vs Media B SHA-256 manifest mismatch")

    # Identity binding
    exp_body = expected_body_serial_sha256 or media_a.body_serial_sha256
    exp_cid = expected_emmc_cid_sha256 or media_a.emmc_cid_sha256
    identity_ok = (
        bool(_SHA256_HEX_RE.match(media_a.body_serial_sha256))
        and bool(_SHA256_HEX_RE.match(media_a.emmc_cid_sha256))
        and (media_a.body_serial_sha256 == media_b.body_serial_sha256 == exp_body)
        and (media_a.emmc_cid_sha256 == media_b.emmc_cid_sha256 == exp_cid)
    )
    if not identity_ok:
        blocked.append(BLOCKED_CROSS_CAMERA_VAULT_IDENTITY_MISMATCH)
        errors.append("Body serial / eMMC CID SHA-256 identity mismatch across media or target camera")

    # FX3RCPT1 528B receipt validation on both media copies
    try:
        rcpt_a_bytes = bytes.fromhex(media_a.fx3rcpt1_receipt_hex)
        rcpt_b_bytes = bytes.fromhex(media_b.fx3rcpt1_receipt_hex)
    except ValueError:
        rcpt_a_bytes = b""
        rcpt_b_bytes = b""
    rcpt_a = parse_fx3rcpt1_receipt(rcpt_a_bytes)
    rcpt_b = parse_fx3rcpt1_receipt(rcpt_b_bytes)
    p2_bundle_sha = _canonical_sha256(media_a.p2_setting_files) if p2_ok else ""
    p18_lens_sha = media_a.p18_lens_files.get("LENSFILE.BIN", "")
    rcpt_ok = (
        rcpt_a.valid
        and rcpt_b.valid
        and (rcpt_a_bytes == rcpt_b_bytes)
        and (rcpt_a.manifest_sha256 == media_a.manifest_sha256)
        and (rcpt_a.body_serial_sha256 == media_a.body_serial_sha256)
        and (rcpt_a.emmc_cid_sha256 == media_a.emmc_cid_sha256)
        and (rcpt_a.p2_cal_bundle_sha256 == p2_bundle_sha)
        and (rcpt_a.p18_lensfile_sha256 == p18_lens_sha)
    )
    if not rcpt_ok:
        blocked.append(BLOCKED_INVALID_FX3RCPT1_RECEIPT)
        errors.extend(rcpt_a.errors or rcpt_b.errors or ("FX3RCPT1 receipt mismatch against manifest/p2/p18",))

    passed = (
        distinct_media
        and all_16_ok
        and manifest_match
        and p2_ok
        and p18_ok
        and rcpt_ok
        and identity_ok
        and len(blocked) == 0
        and len(errors) == 0
    )
    stage_a_ok = bool(passed and stage_a_staging_requested)
    return DualMediaBackupAuditReport(
        passed=passed,
        status=P166_STATUS_VERIFIED_PILLAR_A if passed else P166_STATUS_REJECTED_PILLAR_A,
        stage_a_staging_permitted=stage_a_ok,
        media_a_present=media_a_present,
        media_b_present=media_b_present,
        distinct_physical_media=distinct_media,
        media_a_device_id=media_a.device_id,
        media_b_device_id=media_b.device_id,
        media_a_kind=media_a.media_kind,
        media_b_kind=media_b.media_kind,
        surface_count_a=len(media_a.surface_sha256s),
        surface_count_b=len(media_b.surface_sha256s),
        all_16_surfaces_present=all_16_ok,
        dual_media_manifest_match=manifest_match,
        p2_setting_files_verified=p2_ok,
        p18_lensfile_verified=p18_ok,
        fx3rcpt1_valid=rcpt_ok,
        identity_bound_ok=identity_ok,
        blocked_codes=tuple(dict.fromkeys(blocked)),
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# 3. Pillar 22B: RAID-6 GF(256) (0x11d) Bit-Rot Scrub & 16/16 Pre-Restore RAM Dry-Run
# ---------------------------------------------------------------------------


def encode_16_surface_gf256_archive(
    surface_chunks: Mapping[str, bytes],
) -> Gf256ArchiveBundle:
    """Encode all 16 Tier-0 cold-backup surfaces with RAID-6 `GF(256)` (`0x11d`) P+Q parity."""
    missing = [sid for sid in P166_MANDATORY_16_SURFACES if sid not in surface_chunks]
    _need(len(missing) == 0, f"{BLOCKED_MISSING_16_SURFACE_COLD_BACKUP}:{missing}")

    ordered_bytes = tuple(bytes(surface_chunks[sid]) for sid in P166_MANDATORY_16_SURFACES)
    stripe = encode_gf256_pq_parity(ordered_bytes, shard_names=P166_MANDATORY_16_SURFACES)
    sizes = {sid: len(surface_chunks[sid]) for sid in P166_MANDATORY_16_SURFACES}
    shas = {sid: sha256(surface_chunks[sid]).hexdigest() for sid in P166_MANDATORY_16_SURFACES}
    domains = {sid: _SURFACE_SPEC_MAP[sid].primary_layer_domain for sid in P166_MANDATORY_16_SURFACES}
    manifest_sha = _canonical_sha256({"surface_sha256s": shas, "p": stripe.p_sha256, "q": stripe.q_sha256})
    return Gf256ArchiveBundle(
        surface_order=P166_MANDATORY_16_SURFACES,
        surface_sizes=sizes,
        surface_sha256s=shas,
        surface_domains=domains,
        stripe_bytes=stripe.stripe_bytes,
        shards_bytes=ordered_bytes,
        p_parity=stripe.p_parity,
        q_parity=stripe.q_parity,
        p_sha256=stripe.p_sha256,
        q_sha256=stripe.q_sha256,
        archive_manifest_sha256=manifest_sha,
    )


def _check_surface_prerestore_magic(surface_id: str, data: bytes) -> Tuple[bool, str]:
    if surface_id == "sector0":
        return (len(data) == 512 and data[:4] == b"8246"), "SECTOR0_8246"
    if surface_id == "p2":
        return (b"BK4\x00" in data[:64]), "BK4_NVRAM"
    if surface_id == "p5":
        return (data[:4] == b"WBI2"), "WBI2"
    if surface_id == "p18":
        return (LENS_VX8900_MAGIC in data and data[510:512] == b"\x55\xaa"), "LENS_VX8900"
    if surface_id in ("p1", "p6", "p13"):
        return (len(data) >= 512 and data[510:512] == b"\x55\xaa"), "VFAT"
    if surface_id in ("p3", "p7", "p8", "p12", "p15", "p23", "p30"):
        # High-entropy SPACC ciphertext
        return (len(data) >= 256 and len(set(data[:256])) >= 120), "SPACC_CIPHERTEXT"
    if surface_id == "spi_nor_mtd0ro":
        upper = data.upper()
        return (b"IPL" in upper and b"BLOADER" in upper and b"BL31" in upper), "SPI_NOR_ENVELOPE"
    if surface_id == "emmc_ext_csd":
        return (len(data) == 512), "EXT_CSD"
    return False, "UNKNOWN"


def _xor_bitrot(raw: bytes, pattern: int) -> bytes:
    if not raw:
        return raw
    arr = bytearray(raw)
    for idx in range(0, min(len(arr), 16)):
        arr[idx] ^= pattern
    return bytes(arr)


def scrub_and_rehearse_dual_media_bitrot_recovery(
    archive: Gf256ArchiveBundle,
    *,
    corrupt_chunks: Sequence[str] = (),
    use_pure_syndrome_for_single_bitrot: bool = False,
    bitrot_pattern: int = 0xA5,
    cross_domain_inject_surface: Optional[str] = None,
    request_persistent_write_unlock: bool = False,
) -> BitRotScrubAndPreRestoreReport:
    """Simulate bit-rot on specified chunks, heal via GF(256) `0x11d` P+Q, and dry-run 16/16 pre-restore."""
    blocked: List[str] = []
    errors: List[str] = []

    if request_persistent_write_unlock:
        blocked.append(BLOCKED_SAFETY_POLICY_INVARIANT_VIOLATION)
        errors.append("Persistent eMMC/SPI-NOR/EL3/ISP write unlock denied during rehearsal")

    shards_mut: List[Optional[bytes]] = list(archive.shards_bytes)
    p_mut: Optional[bytes] = archive.p_parity
    q_mut: Optional[bytes] = archive.q_parity
    name_to_idx = {sid: idx for idx, sid in enumerate(archive.surface_order)}

    corrupted_labels: List[str] = []
    for target in corrupt_chunks:
        if target == "P":
            p_mut = _xor_bitrot(p_mut, bitrot_pattern) if p_mut is not None else None
            corrupted_labels.append("P")
        elif target == "Q":
            q_mut = _xor_bitrot(q_mut, bitrot_pattern) if q_mut is not None else None
            corrupted_labels.append("Q")
        elif target in name_to_idx:
            idx = name_to_idx[target]
            cur = shards_mut[idx]
            if cur is not None:
                shards_mut[idx] = _xor_bitrot(cur, bitrot_pattern)
            corrupted_labels.append(target)
        else:
            raise ValueError(f"Unknown scrub chunk target: {target}")

    exp_shas: Optional[Tuple[str, ...]] = tuple(archive.surface_sha256s[s] for s in archive.surface_order)
    exp_p_sha: Optional[str] = archive.p_sha256
    exp_q_sha: Optional[str] = archive.q_sha256
    if use_pure_syndrome_for_single_bitrot:
        # Force pure GF(256) algebraic syndrome localization without per-shard SHA hints
        exp_shas = None
        exp_p_sha = None
        exp_q_sha = None

    shard_sizes = tuple(archive.surface_sizes[s] for s in archive.surface_order)
    heal_res, healed_p, healed_q = heal_gf256_pq_shards(
        shards_mut,
        p_mut,
        q_mut,
        shard_sizes=shard_sizes,
        stripe_bytes=archive.stripe_bytes,
        expected_shard_sha256s=exp_shas,
        expected_p_sha256=exp_p_sha,
        expected_q_sha256=exp_q_sha,
        shard_names=archive.surface_order,
    )

    if not heal_res.passed or heal_res.reconstructed_shards is None:
        if len(corrupt_chunks) >= 3:
            blocked.append(BLOCKED_GF256_QUORUM_EXCEEDED_3_CHUNKS)
        errors.extend(heal_res.errors)
        return BitRotScrubAndPreRestoreReport(
            passed=False,
            status=P166_STATUS_REJECTED_PILLAR_B,
            gf256_polynomial_hex=f"0x{P166_GF256_POLYNOMIAL:03x}",
            repair_mode=heal_res.repair_mode,
            injected_bitrot_chunks=tuple(corrupted_labels),
            corrupted_chunk_count=len(corrupted_labels),
            healed_chunks=(),
            surfaces_verified_count=0,
            surfaces_total_count=len(archive.surface_order),
            prerestore_16of16_exact=False,
            archive_manifest_sha256=archive.archive_manifest_sha256,
            reconstructed_manifest_sha256="",
            surface_checks=(),
            blocked_codes=tuple(dict.fromkeys(blocked)),
            errors=tuple(errors),
        )

    # Execute 16/16 Pre-Restore RAM Dry-Run Verification
    reconstructed_shas: Dict[str, str] = {}
    checks: List[SurfaceDryRunCheck] = []
    for idx, sid in enumerate(archive.surface_order):
        recon_bytes = heal_res.reconstructed_shards[idx]
        recon_sha = sha256(recon_bytes).hexdigest()
        orig_sha = archive.surface_sha256s[sid]
        reconstructed_shas[sid] = recon_sha
        expected_dom = _SURFACE_SPEC_MAP[sid].primary_layer_domain
        observed_dom = (
            DOMAIN_RAW_PNFLASHA_ISP if expected_dom == DOMAIN_SPACC_CNFLASHA_LOGICAL else DOMAIN_SPACC_CNFLASHA_LOGICAL
        ) if cross_domain_inject_surface == sid else archive.surface_domains[sid]
        dom_ok = observed_dom == expected_dom
        magic_ok, _ = _check_surface_prerestore_magic(sid, recon_bytes)
        sha_exact = recon_sha == orig_sha
        s_errs: List[str] = []
        if not dom_ok:
            s_errs.append(f"{BLOCKED_CROSS_DOMAIN_RESTORE_OR_WRITE_LOCKED}:{sid}:{observed_dom}!={expected_dom}")
            blocked.append(BLOCKED_CROSS_DOMAIN_RESTORE_OR_WRITE_LOCKED)
        if not magic_ok:
            s_errs.append(f"MAGIC_FAILED:{sid}")
        if not sha_exact:
            s_errs.append(f"SHA256_MISMATCH:{sid}")
        s_ok = dom_ok and magic_ok and sha_exact
        if not s_ok:
            errors.extend(s_errs)
        checks.append(
            SurfaceDryRunCheck(
                surface_id=sid,
                layer_domain=observed_dom,
                passed=s_ok,
                domain_ok=dom_ok,
                magic_ok=magic_ok,
                sha256_exact=sha_exact,
                original_sha256=orig_sha,
                reconstructed_sha256=recon_sha,
                errors=tuple(s_errs),
            )
        )

    assert healed_p is not None and healed_q is not None
    recon_manifest = _canonical_sha256(
        {
            "surface_sha256s": reconstructed_shas,
            "p": sha256(healed_p).hexdigest(),
            "q": sha256(healed_q).hexdigest(),
        }
    )
    verified_count = sum(1 for c in checks if c.passed)
    exact_16 = (verified_count == 16) and (recon_manifest == archive.archive_manifest_sha256)
    healed_names = list(heal_res.healed_names)
    if "P" in corrupted_labels and heal_res.passed:
        healed_names.append("P")
    if "Q" in corrupted_labels and heal_res.passed:
        healed_names.append("Q")

    passed = exact_16 and len(blocked) == 0 and len(errors) == 0
    return BitRotScrubAndPreRestoreReport(
        passed=passed,
        status=P166_STATUS_VERIFIED_PILLAR_B if passed else P166_STATUS_REJECTED_PILLAR_B,
        gf256_polynomial_hex=f"0x{P166_GF256_POLYNOMIAL:03x}",
        repair_mode=heal_res.repair_mode,
        injected_bitrot_chunks=tuple(corrupted_labels),
        corrupted_chunk_count=len(corrupted_labels),
        healed_chunks=tuple(dict.fromkeys(healed_names)),
        surfaces_verified_count=verified_count,
        surfaces_total_count=len(archive.surface_order),
        prerestore_16of16_exact=exact_16,
        archive_manifest_sha256=archive.archive_manifest_sha256,
        reconstructed_manifest_sha256=recon_manifest,
        surface_checks=tuple(checks),
        blocked_codes=tuple(dict.fromkeys(blocked)),
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# 4. Pillar 22A & Pillar 22B Scenario Suites
# ---------------------------------------------------------------------------


def run_pillar22_a_dual_media_6_scenario_suite() -> Pillar22AScenarioSuiteResult:
    """Run all 6 Dual-Media Independent Tier-0 Cold-Backup & `FX3RCPT1` scenarios."""
    outcomes: List[Pillar22AScenarioOutcome] = []
    copy_a, copy_b, _ = build_synthetic_dual_media_cold_backup(body_tag="p22a-suite")

    # P22A1: Happy dual-media NVMe + External SSD with 16 surfaces + p2/p18 + FX3RCPT1
    r1 = verify_dual_media_cold_backup_vault(copy_a, copy_b)
    ok1 = r1.passed and r1.stage_a_staging_permitted and r1.distinct_physical_media and r1.fx3rcpt1_valid
    outcomes.append(Pillar22AScenarioOutcome(P166_PILLAR_A_SCENARIO_IDS[0], ok1, r1.stage_a_staging_permitted, r1.blocked_codes, "Dual-media NVMe+SSD 16/16 + FX3RCPT1 verified"))

    # P22A2: Single medium only
    r2 = verify_dual_media_cold_backup_vault(copy_a, None)
    ok2 = (not r2.passed) and (not r2.stage_a_staging_permitted) and (BLOCKED_SINGLE_MEDIA_COLD_BACKUP_INSUFFICIENT in r2.blocked_codes)
    outcomes.append(Pillar22AScenarioOutcome(P166_PILLAR_A_SCENARIO_IDS[1], ok2, r2.stage_a_staging_permitted, r2.blocked_codes, "Single-medium cold backup blocked"))

    # P22A3: Same device_id masquerading as two copies
    dup_b = ColdBackupMediaCopy(**{**asdict(copy_b), "device_id": copy_a.device_id, "hardware_uuid": copy_a.hardware_uuid})
    r3 = verify_dual_media_cold_backup_vault(copy_a, dup_b)
    ok3 = (not r3.passed) and (not r3.stage_a_staging_permitted) and (BLOCKED_SAME_PHYSICAL_MEDIUM_FORBIDDEN in r3.blocked_codes)
    outcomes.append(Pillar22AScenarioOutcome(P166_PILLAR_A_SCENARIO_IDS[2], ok3, r3.stage_a_staging_permitted, r3.blocked_codes, "Same-physical-medium duplicate blocked"))

    # P22A4: Missing p2:/setting/psd.bin or p18:/lens/LENSFILE.BIN
    no_p2_p18 = ColdBackupMediaCopy(
        **{
            **asdict(copy_a),
            "p2_setting_files": {"Backup.bin": copy_a.p2_setting_files["Backup.bin"]},
            "p18_lens_files": {},
        }
    )
    r4 = verify_dual_media_cold_backup_vault(no_p2_p18, copy_b)
    ok4 = (not r4.passed) and (not r4.stage_a_staging_permitted) and (BLOCKED_MISSING_CRITICAL_CAL_FILES in r4.blocked_codes)
    outcomes.append(Pillar22AScenarioOutcome(P166_PILLAR_A_SCENARIO_IDS[3], ok4, r4.stage_a_staging_permitted, r4.blocked_codes, "Missing psd.bin/defdet.bin/LENSFILE.BIN blocked"))

    # P22A5: Invalid / tampered FX3RCPT1 receipt
    bad_rcpt_bytes = bytearray.fromhex(copy_a.fx3rcpt1_receipt_hex)
    bad_rcpt_bytes[10] ^= 0xFF
    bad_rcpt_copy = ColdBackupMediaCopy(**{**asdict(copy_a), "fx3rcpt1_receipt_hex": bytes(bad_rcpt_bytes).hex()})
    r5 = verify_dual_media_cold_backup_vault(bad_rcpt_copy, copy_b)
    ok5 = (not r5.passed) and (not r5.stage_a_staging_permitted) and (BLOCKED_INVALID_FX3RCPT1_RECEIPT in r5.blocked_codes)
    outcomes.append(Pillar22AScenarioOutcome(P166_PILLAR_A_SCENARIO_IDS[4], ok5, r5.stage_a_staging_permitted, r5.blocked_codes, "Tampered FX3RCPT1 528B receipt blocked"))

    # P22A6: Dual-media manifest drift (Media B surface hash altered)
    drift_surfaces = dict(copy_b.surface_sha256s)
    drift_surfaces["p18"] = "0" * 64
    drift_b = ColdBackupMediaCopy(**{**asdict(copy_b), "surface_sha256s": drift_surfaces})
    r6 = verify_dual_media_cold_backup_vault(copy_a, drift_b)
    ok6 = (not r6.passed) and (not r6.stage_a_staging_permitted) and (BLOCKED_DUAL_MEDIA_MANIFEST_DRIFT in r6.blocked_codes)
    outcomes.append(Pillar22AScenarioOutcome(P166_PILLAR_A_SCENARIO_IDS[5], ok6, r6.stage_a_staging_permitted, r6.blocked_codes, "Dual-media manifest drift blocked"))

    passed_count = sum(1 for o in outcomes if o.passed)
    all_ok = passed_count == len(P166_PILLAR_A_SCENARIO_IDS) == 6
    return Pillar22AScenarioSuiteResult(
        passed=all_ok,
        status=P166_STATUS_VERIFIED_PILLAR_A if all_ok else P166_STATUS_REJECTED_PILLAR_A,
        scenarios_passed=passed_count,
        scenarios_total=len(P166_PILLAR_A_SCENARIO_IDS),
        scenarios=tuple(outcomes),
    )


def run_pillar22_b_gf256_scrub_6_scenario_suite() -> Pillar22BScenarioSuiteResult:
    """Run all 6 RAID-6 `GF(256)` (`0x11d`) Bit-Rot Scrub & 16/16 Pre-Restore RAM Dry-Run scenarios."""
    outcomes: List[Pillar22BScenarioOutcome] = []
    _, _, chunks = build_synthetic_dual_media_cold_backup(body_tag="p22b-suite")
    archive = encode_16_surface_gf256_archive(chunks)

    # P22B1: Zero bit-rot clean 16/16 scrub & pre-restore
    b1 = scrub_and_rehearse_dual_media_bitrot_recovery(archive)
    ok1 = b1.passed and b1.prerestore_16of16_exact and b1.surfaces_verified_count == 16 and b1.physical_device_writes == 0
    outcomes.append(Pillar22BScenarioOutcome(P166_PILLAR_B_SCENARIO_IDS[0], ok1, b1.repair_mode, b1.corrupted_chunk_count, b1.prerestore_16of16_exact, b1.blocked_codes, "Clean 16/16 pre-restore dry-run"))

    # P22B2: 1-chunk silent bit-rot healed via pure GF(256) syndrome localization
    b2 = scrub_and_rehearse_dual_media_bitrot_recovery(archive, corrupt_chunks=("p18",), use_pure_syndrome_for_single_bitrot=True)
    ok2 = b2.passed and b2.prerestore_16of16_exact and b2.repair_mode == "SYNDROME_SINGLE_CORRUPT_HEAL" and "p18" in b2.healed_chunks
    outcomes.append(Pillar22BScenarioOutcome(P166_PILLAR_B_SCENARIO_IDS[1], ok2, b2.repair_mode, b2.corrupted_chunk_count, b2.prerestore_16of16_exact, b2.blocked_codes, "1-chunk GF(256) syndrome heal"))

    # P22B3: 2-chunk simultaneous silent bit-rot (p2 + spi_nor_mtd0ro) healed via GF(256) P+Q
    b3 = scrub_and_rehearse_dual_media_bitrot_recovery(archive, corrupt_chunks=("p2", "spi_nor_mtd0ro"))
    ok3 = b3.passed and b3.prerestore_16of16_exact and set(b3.healed_chunks) == {"p2", "spi_nor_mtd0ro"}
    outcomes.append(Pillar22BScenarioOutcome(P166_PILLAR_B_SCENARIO_IDS[2], ok3, b3.repair_mode, b3.corrupted_chunk_count, b3.prerestore_16of16_exact, b3.blocked_codes, "2-chunk GF(256) P+Q heal"))

    # P22B4: 1 data chunk + Q parity chunk corrupted simultaneously
    b4 = scrub_and_rehearse_dual_media_bitrot_recovery(archive, corrupt_chunks=("p15", "Q"))
    ok4 = b4.passed and b4.prerestore_16of16_exact and "p15" in b4.healed_chunks
    outcomes.append(Pillar22BScenarioOutcome(P166_PILLAR_B_SCENARIO_IDS[3], ok4, b4.repair_mode, b4.corrupted_chunk_count, b4.prerestore_16of16_exact, b4.blocked_codes, "Data + Q parity heal"))

    # P22B5: 3-chunk quorum loss fails closed
    b5 = scrub_and_rehearse_dual_media_bitrot_recovery(archive, corrupt_chunks=("p2", "p15", "p18"))
    ok5 = (not b5.passed) and (not b5.prerestore_16of16_exact) and (BLOCKED_GF256_QUORUM_EXCEEDED_3_CHUNKS in b5.blocked_codes)
    outcomes.append(Pillar22BScenarioOutcome(P166_PILLAR_B_SCENARIO_IDS[4], ok5, b5.repair_mode, b5.corrupted_chunk_count, b5.prerestore_16of16_exact, b5.blocked_codes, "3-chunk quorum loss fail-closed"))

    # P22B6: Cross-domain mismatch or write-unlock request fails closed
    b6 = scrub_and_rehearse_dual_media_bitrot_recovery(archive, cross_domain_inject_surface="p15", request_persistent_write_unlock=True)
    ok6 = (
        (not b6.passed)
        and (not b6.prerestore_16of16_exact)
        and (BLOCKED_CROSS_DOMAIN_RESTORE_OR_WRITE_LOCKED in b6.blocked_codes)
        and (BLOCKED_SAFETY_POLICY_INVARIANT_VIOLATION in b6.blocked_codes)
        and b6.physical_device_writes == 0
    )
    outcomes.append(Pillar22BScenarioOutcome(P166_PILLAR_B_SCENARIO_IDS[5], ok6, b6.repair_mode, b6.corrupted_chunk_count, b6.prerestore_16of16_exact, b6.blocked_codes, "Cross-domain / write-unlock blocked"))

    passed_count = sum(1 for o in outcomes if o.passed)
    all_ok = passed_count == len(P166_PILLAR_B_SCENARIO_IDS) == 6
    return Pillar22BScenarioSuiteResult(
        passed=all_ok,
        status=P166_STATUS_VERIFIED_PILLAR_B if all_ok else P166_STATUS_REJECTED_PILLAR_B,
        scenarios_passed=passed_count,
        scenarios_total=len(P166_PILLAR_B_SCENARIO_IDS),
        scenarios=tuple(outcomes),
    )


def run_pillar22_standalone_suite(*, force_clean_room: Optional[bool] = None) -> Pillar22StandaloneReport:
    """Run Pillar 22 standalone donor audit + Pillar 22A + Pillar 22B (for `--with-phase166`)."""
    snap = inspect_phase166_donors_readonly(force_clean_room=force_clean_room)
    pa = run_pillar22_a_dual_media_6_scenario_suite()
    pb = run_pillar22_b_gf256_scrub_6_scenario_suite()
    errors: List[str] = list(snap.errors)
    if not pa.passed:
        errors.append("Pillar 22A dual-media cold-backup suite failed")
    if not pb.passed:
        errors.append("Pillar 22B GF(256) bit-rot scrub suite failed")
    all_ok = snap.all_passed and pa.passed and pb.passed and PHYSICAL_DEVICE_WRITES == 0
    suite_sha = _canonical_sha256(
        {
            "schema": PHASE166_SCHEMA,
            "mode": snap.verification_mode,
            "snapshot_sha256": snap.snapshot_sha256,
            "pa": pa.to_dict(),
            "pb": pb.to_dict(),
            "all_passed": all_ok,
        }
    )
    return Pillar22StandaloneReport(
        schema=PHASE166_SCHEMA,
        version=PHASE166_VERSION,
        verification_mode=snap.verification_mode,
        all_passed=all_ok,
        status=P166_STATUS_VERIFIED_SUITE if all_ok else P166_STATUS_FAIL_SUITE,
        donor_snapshot=snap,
        pillar_a_dual_media_6_scenarios=pa,
        pillar_b_gf256_scrub_6_scenarios=pb,
        suite_sha256=suite_sha,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# 5. Unified 22/22 Recovery Master Aggregator (`evaluate_22pillar_recovery_master`)
# ---------------------------------------------------------------------------


def _run_timed(fn: Any, *args: Any, **kwargs: Any) -> Tuple[Any, float]:
    t0 = time.monotonic()
    res = fn(*args, **kwargs)
    return res, round(time.monotonic() - t0, 6)


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


def evaluate_22pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master22PillarRecoveryReport:
    """Evaluate and aggregate all 22 recovery pillars (`1..22`) concurrently in `< 2.0s`."""
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

    if fault_inject_pillar is not None:
        _need(fault_inject_pillar in MASTER_22_PILLAR_IDS, f"Unknown fault_inject_pillar: {fault_inject_pillar}")

    t_start = time.monotonic()
    kw: Dict[str, Any] = {"force_clean_room": force_clean_room} if force_clean_room is not None else {}

    def _run_lane_1() -> Any:
        return run_recovery_master_suite(**kw)

    def _run_lane_2() -> Dict[int, Tuple[Any, float]]:
        return {
            9: _run_timed(run_ramdisk_overlay_and_emmc_health_suite, **kw),
            10: _run_timed(run_fdt_bootargs_and_kernel_suite, **kw),
            12: _run_timed(run_squashfs_and_hibdrv_wbi_suite, **kw),
            13: _run_timed(run_bootrom_usb_and_emmc_bootpart_suite, **kw),
            16: _run_timed(run_realhw_ext2_installer_and_p1_rescue_suite, **kw),
            17: _run_timed(run_adjustcontrol_streaming_backup_suite, **kw),
            18: _run_timed(run_realhw_service_usb_and_libjit_hardener_suite, **kw),
            20: _run_timed(run_realhw_uart_460800_post_triage_and_isp_suite, **kw),
            21: _run_timed(run_realhw_bootrom_el3_and_ufu_stock_reflash_suite, **kw),
            22: _run_timed(run_pillar22_standalone_suite, **kw),
        }

    def _run_lane_3() -> Dict[int, Tuple[Any, float]]:
        return {
            8: _run_timed(run_gpt_rpmb_and_rescue_bundle_suite, **kw),
            11: _run_timed(run_ab_bank_and_interrupted_ota_suite, **kw),
            14: _run_timed(run_factory_cal_ibis_defectpixel_and_nvs_suite, **kw),
            15: _run_timed(run_secureboot_chain_and_partition_align_suite, **kw),
            19: _run_timed(run_realhw_pnflasha_cnflasha_mtdro_tier0_vault_suite, **kw),
        }

    # 3 balanced lanes execute Pillars 8-22 while Pillar 3 waits on /bin/sh subprocesses (< 2.0s)
    with ThreadPoolExecutor(max_workers=3) as pool:
        fut_lane1 = pool.submit(_run_lane_1)
        fut_lane2 = pool.submit(_run_lane_2)
        fut_lane3 = pool.submit(_run_lane_3)

        master_rep = fut_lane1.result()
        lane2_map = fut_lane2.result()
        lane2_map.update(fut_lane3.result())

    # Build Pillars 1..7 from run_recovery_master_suite
    pillar_statuses: List[MasterPillarStatus] = []
    safety_errors: List[str] = []

    for idx, p in enumerate(master_rep.pillars):
        spec = MASTER_22_PILLAR_SPECS[idx]
        pillar_statuses.append(
            MasterPillarStatus(
                pillar_number=spec[0],
                pillar_id=spec[1],
                phase_label=spec[2],
                module_name=spec[3],
                passed=bool(p.passed),
                status=p.status,
                verification_mode=p.verification_mode,
                elapsed_seconds=p.elapsed_seconds,
                key_metrics=dict(p.summary_metrics),
                digest_sha256=p.deterministic_digest_sha256,
                errors=tuple(p.errors),
            )
        )

    if master_rep.passive_tx_bytes_emitted != 0:
        safety_errors.append("Pillars 1-7 violated passive_tx_bytes_emitted == 0")
    if master_rep.physical_device_writes != 0 or master_rep.persistent_emmc_writes_authorized is not False:
        safety_errors.append("Pillars 1-7 violated zero-write safety invariant")

    # Helper for Pillars 8..22
    def _add_suite_pillar(num: int, rep: Any, dt: float, metrics: Dict[str, Any]) -> None:
        spec = MASTER_22_PILLAR_SPECS[num - 1]
        rep_mode = getattr(rep, "verification_mode", master_rep.verification_mode)
        rep_status = getattr(rep, "status", "UNKNOWN")
        rep_passed = bool(getattr(rep, "all_passed", False))
        rep_errs = tuple(getattr(rep, "errors", ()))
        # Assert shared safety attributes when present on the suite report
        for attr_name, expected_val in (
            ("otp_fuse_touches", 0),
            ("otp_fuse_writes", 0),
            ("rpmb_counter_increments", 0),
            ("passive_tx_bytes_emitted", 0),
            ("physical_usb_packets_emitted", 0),
            ("physical_usb_bytes_transmitted", 0),
            ("usb_tx_packets_emitted", 0),
            ("physical_device_writes", 0),
            ("raw_firmware_bytes_leaked", 0),
            ("el3_payload_transmit_authorized", False),
            ("isp_write_authorized", False),
            ("spi_nor_write_authorized", False),
            ("persistent_emmc_writes_authorized", False),
            ("persistent_write_release", False),
            ("live_usb_iokit_transmit_enabled", False),
        ):
            if hasattr(rep, attr_name) and getattr(rep, attr_name) != expected_val:
                safety_errors.append(f"Pillar {num} ({spec[1]}) violated {attr_name} == {expected_val}")
        digest = _canonical_sha256({"pillar": spec[1], "mode": rep_mode, "status": rep_status, "metrics": metrics, "passed": rep_passed})
        pillar_statuses.append(
            MasterPillarStatus(
                pillar_number=spec[0],
                pillar_id=spec[1],
                phase_label=spec[2],
                module_name=spec[3],
                passed=rep_passed,
                status=rep_status,
                verification_mode=rep_mode,
                elapsed_seconds=dt,
                key_metrics=metrics,
                digest_sha256=digest,
                errors=rep_errs,
            )
        )

    p8_rep, p8_dt = lane2_map[8]
    _add_suite_pillar(8, p8_rep, p8_dt, {"gpt_partitions": p8_rep.gpt_healthy_check.primary_audit.active_partition_count, "rpmb_writes_emitted": p8_rep.rpmb_writes_emitted})

    p9_rep, p9_dt = lane2_map[9]
    _add_suite_pillar(9, p9_rep, p9_dt, {"cpio_entries": p9_rep.cpio_valid_report.entry_count, "zero_rw_block_mounts": p9_rep.mount_isolation_report.zero_rw_block_mounts})

    p10_rep, p10_dt = lane2_map[10]
    _add_suite_pillar(10, p10_rep, p10_dt, {"fdt_nodes": p10_rep.stage_b_fdt_parse_report.node_count, "stage_b_boot_gate_ready": p10_rep.stage_b_boot_gate_ready})

    p11_rep, p11_dt = lane2_map[11]
    _add_suite_pillar(11, p11_rep, p11_dt, {"ota_scenarios": f"{p11_rep.ota_6_scenario_suite.scenarios_passed}/{p11_rep.ota_6_scenario_suite.scenarios_total}"})

    p12_rep, p12_dt = lane2_map[12]
    _add_suite_pillar(12, p12_rep, p12_dt, {"wbi_scenarios": f"{p12_rep.wbi_6_scenario_suite.scenarios_passed}/{p12_rep.wbi_6_scenario_suite.scenarios_total}", "wbi_partition_writes": p12_rep.wbi_partition_writes})

    p13_rep, p13_dt = lane2_map[13]
    _add_suite_pillar(13, p13_rep, p13_dt, {"bootpart_scenarios": f"{p13_rep.emmc_bootpart_6_scenario_suite.scenarios_passed}/{p13_rep.emmc_bootpart_6_scenario_suite.scenarios_total}", "bootrom_scenarios": f"{p13_rep.bootrom_usb_5_scenario_suite.scenarios_passed}/{p13_rep.bootrom_usb_5_scenario_suite.scenarios_total}"})

    p14_rep, p14_dt = lane2_map[14]
    _add_suite_pillar(14, p14_rep, p14_dt, {"factory_cal_scenarios": f"{p14_rep.factory_cal_6_scenario_firewall.scenarios_passed}/{p14_rep.factory_cal_6_scenario_firewall.scenarios_total}", "sensor_ibis_scenarios": f"{p14_rep.sensor_ibis_6_scenario_suite.scenarios_passed}/{p14_rep.sensor_ibis_6_scenario_suite.scenarios_total}"})

    p15_rep, p15_dt = lane2_map[15]
    _add_suite_pillar(15, p15_rep, p15_dt, {"secureboot_scenarios": f"{p15_rep.secureboot_6_scenario_firewall.scenarios_passed}/{p15_rep.secureboot_6_scenario_firewall.scenarios_total}", "partalign_scenarios": f"{p15_rep.partition_align_6_scenario_firewall.scenarios_passed}/{p15_rep.partition_align_6_scenario_firewall.scenarios_total}"})

    p16_rep, p16_dt = lane2_map[16]
    _add_suite_pillar(16, p16_rep, p16_dt, {"ext2_scenarios": f"{p16_rep.pillar_a_ext2_installer_6_scenarios.scenarios_passed}/{p16_rep.pillar_a_ext2_installer_6_scenarios.scenarios_total}", "p1_rescue_scenarios": f"{p16_rep.pillar_b_p1_rescue_6_scenarios.scenarios_passed}/{p16_rep.pillar_b_p1_rescue_6_scenarios.scenarios_total}"})

    p17_rep, p17_dt = lane2_map[17]
    _add_suite_pillar(17, p17_rep, p17_dt, {"wire_scenarios": f"{p17_rep.pillar_a_wire_and_preflight_7_scenarios.scenarios_passed}/{p17_rep.pillar_a_wire_and_preflight_7_scenarios.scenarios_total}", "dual_path_scenarios": f"{p17_rep.pillar_b_dual_path_backup_6_scenarios.scenarios_passed}/{p17_rep.pillar_b_dual_path_backup_6_scenarios.scenarios_total}", "live_usb_iokit_transmit_enabled": p17_rep.live_usb_iokit_transmit_enabled})

    p18_rep, p18_dt = lane2_map[18]
    _add_suite_pillar(18, p18_rep, p18_dt, {"service_usb_scenarios": f"{p18_rep.pillar_a_service_usb_8_scenarios.scenarios_passed}/{p18_rep.pillar_a_service_usb_8_scenarios.scenarios_total}", "hardened_libjit_scenarios": f"{p18_rep.pillar_b_hardened_libjit_8_scenarios.scenarios_passed}/{p18_rep.pillar_b_hardened_libjit_8_scenarios.scenarios_total}", "usb_tx_packets_emitted": p18_rep.usb_tx_packets_emitted})

    p19_rep, p19_dt = lane2_map[19]
    _add_suite_pillar(19, p19_rep, p19_dt, {"surfaces": f"{p19_rep.pillar_a_vault_manifest_report.surface_count}/16", "pillar_a_scenarios": f"{p19_rep.pillar_a_firewall_8_scenarios.scenarios_passed}/{p19_rep.pillar_a_firewall_8_scenarios.scenarios_total}", "pillar_b_scenarios": f"{p19_rep.pillar_b_gate_6_scenarios.scenarios_passed}/{p19_rep.pillar_b_gate_6_scenarios.scenarios_total}"})

    p20_rep, p20_dt = lane2_map[20]
    _add_suite_pillar(20, p20_rep, p20_dt, {"pillar_a_triage": f"{p20_rep.pillar_a_triage_8_scenarios.scenarios_passed}/{p20_rep.pillar_a_triage_8_scenarios.scenarios_total}", "pillar_b_firewall": f"{p20_rep.pillar_b_firewall_6_scenarios.scenarios_passed}/{p20_rep.pillar_b_firewall_6_scenarios.scenarios_total}", "pillar_c_isp": f"{p20_rep.pillar_c_isp_6_scenarios.scenarios_passed}/{p20_rep.pillar_c_isp_6_scenarios.scenarios_total}"})

    p21_rep, p21_dt = lane2_map[21]
    _add_suite_pillar(21, p21_rep, p21_dt, {"pillar_a_ufu": f"{p21_rep.pillar_a_ufu_8_scenarios.scenarios_passed}/{p21_rep.pillar_a_ufu_8_scenarios.scenarios_total}", "pillar_b_el3": f"{p21_rep.pillar_b_el3_6_scenarios.scenarios_passed}/{p21_rep.pillar_b_el3_6_scenarios.scenarios_total}", "pillar_c_5tier": f"{p21_rep.pillar_c_5tier_8_scenarios.scenarios_passed}/{p21_rep.pillar_c_5tier_8_scenarios.scenarios_total}", "el3_payload_transmit_authorized": p21_rep.el3_payload_transmit_authorized})

    p22_rep, p22_dt = lane2_map[22]
    _add_suite_pillar(22, p22_rep, p22_dt, {"pillar22_a_dual_media": f"{p22_rep.pillar_a_dual_media_6_scenarios.scenarios_passed}/{p22_rep.pillar_a_dual_media_6_scenarios.scenarios_total}", "pillar22_b_gf256_scrub": f"{p22_rep.pillar_b_gf256_scrub_6_scenarios.scenarios_passed}/{p22_rep.pillar_b_gf256_scrub_6_scenarios.scenarios_total}", "donor_files_inspected": p22_rep.donor_snapshot.donor_files_inspected})

    if fault_inject_pillar is not None:
        pillar_statuses = [
            _apply_master_fault_injection(p) if p.pillar_id == fault_inject_pillar else p
            for p in pillar_statuses
        ]

    elapsed = round(time.monotonic() - t_start, 6)
    failed = tuple(p.pillar_id for p in pillar_statuses if not p.passed)
    pillars_passed = sum(1 for p in pillar_statuses if p.passed)
    verification_mode = p22_rep.verification_mode

    all_ok = (
        len(pillar_statuses) == MASTER_22_PILLAR_COUNT == 22
        and pillars_passed == 22
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
    )

    master_sha = _canonical_sha256(
        {
            "schema": PHASE166_SCHEMA,
            "version": PHASE166_VERSION,
            "verification_mode": verification_mode,
            "pillar_count": len(pillar_statuses),
            "pillars_passed": pillars_passed,
            "failed_pillars": list(failed),
            "pillar_digests": [(p.pillar_number, p.pillar_id, p.passed, p.digest_sha256) for p in pillar_statuses],
            "all_passed": all_ok,
        }
    )

    return Master22PillarRecoveryReport(
        schema=PHASE166_SCHEMA,
        version=PHASE166_VERSION,
        verification_mode=verification_mode,
        all_passed=all_ok,
        status=P166_STATUS_VERIFIED_22OF22_AGGREGATOR if all_ok else P166_STATUS_FAIL_22OF22_AGGREGATOR,
        pillar_count=len(pillar_statuses),
        pillars_passed=pillars_passed,
        failed_pillars=failed,
        elapsed_seconds=elapsed,
        under_2s_budget=elapsed < 2.0,
        pillars=tuple(pillar_statuses),
        donor_snapshot=p22_rep.donor_snapshot,
        pillar22_a_dual_media=p22_rep.pillar_a_dual_media_6_scenarios,
        pillar22_b_gf256_scrub=p22_rep.pillar_b_gf256_scrub_6_scenarios,
        master_22pillar_sha256=master_sha,
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


def verify_22pillar_recovery_suite(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master22PillarRecoveryReport:
    """Public entry point for Pillar 22 unified `22/22` real-hardware recovery master verification."""
    return evaluate_22pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )
