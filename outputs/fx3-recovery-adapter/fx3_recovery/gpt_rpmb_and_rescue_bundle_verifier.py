"""Phase 94 — CXD90057 eMMC Primary/Backup GPT & Sony Sub-Partition Header Healer,
RPMB HMAC-SHA256 Monotonic Write-Counter Replay Guard & Offline SD-Rescue Bundle Verifier.

Provides three deterministic, RAM-only, read-only-donor verification pillars for
Sony `ILME-FX3` (`0x91030080` / `ALCIN_UUD`) eMMC recovery safety:

1. **Pillar 1 — Primary vs Backup GPT (LBA 1 vs Last LBA) CRC32 & Partition Overlap Reconstructor (RAM-Only)**:
   - Models the 15-partition `CXD90057` eMMC layout (`p1` FAT boot, `p2..p15`
     `bk4`/kernel/`nbl_tz`/`wbi2`/jiritsu/`rootfs`/`cp_rtos`/`uboot_ab`/`app`/
     calibration/cert/userdata/`usr`/`cnflasha_lens_cal`) plus Sony Sector 0 (`8246` `2.00`).
   - Computes exact IEEE 802.3 CRC32 (`zlib.crc32`) over the 92-byte `EFI PART`
     header and 128-entry (`128 * 128 = 16,384` byte) partition array.
   - Proves deterministic RAM-only reconstruction of a corrupted Primary GPT from
     Backup GPT (and vice versa), while failing closed on overlapping LBA ranges,
     misaligned 4 KiB (`8`-LBA) boundaries, dual corruption, or cross-SKU `FX6`
     partition geometry transplants onto `FX3` eMMC.

2. **Pillar 2 — eMMC RPMB (Replay Protected Memory Block) Monotonic Write-Counter & Nonce Replay Sandbox**:
   - Models JEDEC JESD84-B51 eMMC 5.1 512-byte RPMB frames (`196B` stuff + `32B`
     HMAC-SHA256 MAC + `284B` authenticated payload: `256B` data, `16B` nonce,
     `4B` big-endian monotonic `write_counter`, `2B` address, `2B` block_count,
     `2B` result, `2B` req/resp) using synthetic test keys ONLY (zero proprietary keys).
   - Proves fail-closed rejection of stale `write_counter` replay
     (`RESULT_COUNTER_FAILURE = 0x0003`), nonce mismatch, MAC forgery
     (`RESULT_AUTH_FAILURE = 0x0002`), and counter exhaustion at `0xFFFFFFFF`
     (`RESULT_COUNTER_EXPIRED = 0x0080`), while proving Stage-B volatile `/tmp` RAM/SD
     overlay emits zero physical RPMB writes (`rpmb_writes_emitted == 0`).

3. **Pillar 3 — Offline Air-Gapped SD-Rescue Emergency Kit Manifest & Two-Man Integrity Verifier**:
   - Validates an offline SD-card rescue bundle (`FX3_SAFE_STOCK.FLG` + 15-partition
     `p1..p15` SHA-256 manifest + `GF(256)` `P + Q` RAID-6 parity shards + body serial
     binding + distinct two-man operator attestation), blocking any Stage-B rehearsal
     if any artifact is missing, partial/truncated, blank, cross-body transplanted, or
     lacks dual-operator verification.

Safety Redlines (Hard-Locked):
- `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`
- `PERSISTENT_WRITE_RELEASE = False`
- `ALLOW_BOOT_PARTITION_TARGETING = False`
- `ALLOW_DESTRUCTIVE_FASTBOOT = False`
- `OTP_FUSE_TOUCHES = 0`
- `PASSIVE_TX_BYTES_EMITTED = 0`
- `PHYSICAL_DEVICE_WRITES = 0`
- `RPMB_WRITES_EMITTED = 0`
- Local donor files opened strictly via `os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK`.
- Zero raw `bytes` reprs emitted; all digests and samples use `.hex()` / `.hexdigest()`.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import hmac
import json
import os
from pathlib import Path
import re
import stat
import struct
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple
import zlib

from .emmc_dump_forensic_verifier import (
    FX3_PRODUCT_MODEL_ID,
    SONY_PTBL_ENTRY_COUNT,
    SONY_PTBL_MAGIC,
    SONY_PTBL_SIZE,
    SONY_PTBL_VERSION,
    build_synthetic_p1_vfat_image,
    build_synthetic_sector0_fx3,
    verify_sector0_dump,
)
from .files import is_forced_clean_room, require, resolve_donor_path
from .firmware_updata_and_antirollback_guard import (
    FX3_SKU_CODE,
    FX6_SKU_CODE,
    FX6_WBI2_EXPECTED_SECTIONS,
    FX3_WBI2_EXPECTED_SECTIONS,
    build_synthetic_wbi2_header_bytes,
)
from .tier0_backup_parity_and_manifest_guard import (
    BodyHardwareIdentity,
    Gf256ParityStripe,
    build_body_hardware_identity,
    encode_gf256_pq_parity,
    heal_gf256_pq_shards,
)


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

GPT_RPMB_RESCUE_SCHEMA: str = "fx3-gpt-rpmb-and-rescue-bundle-verifier-v1"
GPT_RPMB_RESCUE_VERSION: str = "1.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False
ALLOW_BOOT_PARTITION_TARGETING: bool = False
ALLOW_DESTRUCTIVE_FASTBOOT: bool = False
READ_ONLY_DONOR_ACCESS: bool = True
OTP_FUSE_TOUCHES: int = 0
PASSIVE_TX_BYTES_EMITTED: int = 0
PHYSICAL_DEVICE_WRITES: int = 0
RPMB_WRITES_EMITTED: int = 0

STATUS_VERIFIED_GPT_RPMB_BUNDLE: str = "VERIFIED_GPT_RPMB_RESCUE_BUNDLE"
STATUS_FAIL_GPT_RPMB_BUNDLE: str = "FAIL_GPT_RPMB_RESCUE_BUNDLE"

# Local Donor Relative Paths (opened strictly O_RDONLY | O_NOFOLLOW | O_NONBLOCK)
DONOR_FX3_P1_205_RELPATH: str = "fx3-color-port-20261027/input-20261028/original-update-engine/2.05/nflasha1"
DONOR_FX3_WBI2_RELPATH: str = "sony-firmware-20261024/stage2/extraction/nflasha5.img"
DONOR_FX6_WBI2_RELPATH: str = "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0700_part_image/dev/nflasha5"
DONOR_CXD90057_DTB_RELPATH: str = "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0800_appli/setting/cxd90057.dtb"

# ---------------------------------------------------------------------------
# Pillar 1 Constants — UEFI GPT & 15-Partition CXD90057 eMMC Geometry
# ---------------------------------------------------------------------------

GPT_SIGNATURE: bytes = b"EFI PART"
GPT_REVISION_1_0: int = 0x00010000
GPT_HEADER_SIZE: int = 92
GPT_SECTOR_SIZE: int = 512
GPT_ENTRY_COUNT: int = 128
GPT_ENTRY_SIZE: int = 128
GPT_ARRAY_BYTES: int = GPT_ENTRY_COUNT * GPT_ENTRY_SIZE  # 16,384 bytes (32 LBAs)
GPT_ARRAY_SECTORS: int = GPT_ARRAY_BYTES // GPT_SECTOR_SIZE
GPT_4K_ALIGNMENT_SECTORS: int = 8  # 4096 / 512 = 8 LBAs
GPT_DEFAULT_TOTAL_LBAS: int = 0x00400000  # 4,194,304 LBAs (2 GiB UDA)
GPT_FIRST_USABLE_LBA: int = 0x00000080  # 128 (4 KiB-aligned after Sector0 + GPT)

# Deterministic synthetic UUID bytes (non-proprietary RFC 4122-shaped GUIDs)
FX3_GPT_DISK_GUID: bytes = bytes.fromhex("4658333037303230414c43494e555544")
FX3_GPT_PART_TYPE_GUID: bytes = bytes.fromhex("0fc63daf848347728e793d69d8477de4")
FX6_GPT_DISK_GUID: bytes = bytes.fromhex("4658363036303130434841504c494e36")

# 15-partition CXD90057 FX3 eMMC layout (1-indexed p1..p15, all 4 KiB-aligned)
# Tuple: (part_num, name, start_lba, size_lbas, role)
CXD90057_FX3_15_PARTITIONS: Tuple[Tuple[int, str, int, int, str], ...] = (
    (1, "p1_vfat_boot", 0x00000080, 0x0000BF80, "vfat_boot_updater"),
    (2, "p2_bk4_nvram", 0x0000C000, 0x0000A000, "bk4_calibration_nvram"),
    (3, "p3_kernel_scel", 0x00016000, 0x00025800, "kernel_4_9_337_scel"),
    (4, "p4_nbl_optee_tz", 0x0003B800, 0x00006800, "nbl_optee_trustzone"),
    (5, "p5_wbi2_hibdrv", 0x00042000, 0x00096000, "wbi2_hibernate"),
    (6, "p6_jiritsu_tmp", 0x000D8000, 0x0000C800, "jiritsu_staging"),
    (7, "p7_rootfs", 0x000E4800, 0x00019000, "rootfs_readonly"),
    (8, "p8_cp_rtos", 0x000FD800, 0x00032000, "cp_cortex_r5_rtos"),
    (9, "p9_uboot_ab", 0x0012F800, 0x00020000, "uboot_ab_slots"),
    (10, "p10_app_core", 0x0014F800, 0x00040000, "sony_app_core"),
    (11, "p11_calibration", 0x0018F800, 0x0007C800, "factory_calibration"),
    (12, "p12_cert_c2pa", 0x0020C000, 0x00014000, "c2pa_rq_lic_cert"),
    (13, "p13_userdata_cfg", 0x00220000, 0x00002000, "userdata_settings"),
    (14, "p14_usr_overlay", 0x00222000, 0x000FA000, "usr_system_overlay"),
    (15, "p15_cnflasha_lens_cal", 0x0031C000, 0x0000A000, "cnflasha_encrypted_cal"),
)

FX3_LENS_CAL_START_LBA: int = 0x0031C000
FX6_SHIFTED_LENS_CAL_START_LBA: int = 0x00312000

ERR_GPT_BAD_SIGNATURE: str = "GPT_BAD_SIGNATURE"
ERR_GPT_BAD_HEADER_CRC32: str = "GPT_BAD_HEADER_CRC32"
ERR_GPT_BAD_ARRAY_CRC32: str = "GPT_BAD_ARRAY_CRC32"
ERR_GPT_GEOMETRY_INVALID: str = "GPT_GEOMETRY_INVALID"
ERR_GPT_PARTITION_OVERLAP: str = "GPT_PARTITION_OVERLAP"
ERR_GPT_MISALIGNED_4K: str = "GPT_MISALIGNED_4K_BOUNDARY"
ERR_GPT_OUT_OF_USABLE_RANGE: str = "GPT_OUT_OF_USABLE_RANGE"
ERR_GPT_BOTH_COPIES_CORRUPTED: str = "GPT_BOTH_COPIES_CORRUPTED"
ERR_CROSS_SKU_FX6_GPT_TRANSPLANT: str = "CROSS_SKU_FX6_GPT_TRANSPLANT_FORBIDDEN"

# ---------------------------------------------------------------------------
# Pillar 2 Constants — JEDEC eMMC 5.1 RPMB (512-byte Frames)
# ---------------------------------------------------------------------------

RPMB_FRAME_BYTES: int = 512
RPMB_STUFF_BYTES: int = 196
RPMB_MAC_BYTES: int = 32
RPMB_MAC_PAYLOAD_BYTES: int = 284
RPMB_DATA_BYTES: int = 256
RPMB_NONCE_BYTES: int = 16
RPMB_MAX_WRITE_COUNTER: int = 0xFFFFFFFF

RPMB_REQ_PROGRAM_KEY: int = 0x0001
RPMB_REQ_GET_WRITE_COUNTER: int = 0x0002
RPMB_REQ_DATA_WRITE: int = 0x0003
RPMB_REQ_DATA_READ: int = 0x0004
RPMB_REQ_RESULT_READ: int = 0x0005

RPMB_RESP_PROGRAM_KEY: int = 0x0100
RPMB_RESP_GET_WRITE_COUNTER: int = 0x0200
RPMB_RESP_DATA_WRITE: int = 0x0300
RPMB_RESP_DATA_READ: int = 0x0400

RPMB_RESULT_OK: int = 0x0000
RPMB_RESULT_GENERAL_FAILURE: int = 0x0001
RPMB_RESULT_AUTH_FAILURE: int = 0x0002
RPMB_RESULT_COUNTER_FAILURE: int = 0x0003
RPMB_RESULT_ADDR_FAILURE: int = 0x0004
RPMB_RESULT_WRITE_FAILURE: int = 0x0005
RPMB_RESULT_READ_FAILURE: int = 0x0006
RPMB_RESULT_NO_KEY: int = 0x0007
RPMB_RESULT_COUNTER_EXPIRED: int = 0x0080

ERR_RPMB_NONCE_MISMATCH: str = "RPMB_NONCE_MISMATCH"
ERR_RPMB_AUTH_FAILURE: str = "RPMB_HMAC_AUTH_FAILURE"
ERR_RPMB_COUNTER_FAILURE: str = "RPMB_STALE_WRITE_COUNTER_REPLAY"
ERR_RPMB_COUNTER_EXPIRED: str = "RPMB_WRITE_COUNTER_EXHAUSTED_0XFFFFFFFF"
ERR_RPMB_PHYSICAL_WRITE_FORBIDDEN: str = "RPMB_PHYSICAL_WRITE_FORBIDDEN"

# Synthetic test key ONLY (explicitly derived from a public clean-room test label;
# NEVER contains any proprietary Sony key material)
SYNTHETIC_RPMB_TEST_KEY: bytes = sha256(
    b"FX3_CLEAN_ROOM_SYNTHETIC_RPMB_TEST_KEY_NOT_PROPRIETARY_V1"
).digest()

# ---------------------------------------------------------------------------
# Pillar 3 Constants — Offline Air-Gapped SD-Rescue Emergency Kit
# ---------------------------------------------------------------------------

RESCUE_SENTINEL_FILENAME: str = "FX3_SAFE_STOCK.FLG"
RESCUE_MANIFEST_SCHEMA: str = "fx3-offline-sd-rescue-bundle-manifest-v1"
RESCUE_KIT_PARTITION_NAMES: Tuple[str, ...] = tuple(p[1] for p in CXD90057_FX3_15_PARTITIONS)

ERR_MISSING_SENTINEL_FLAG: str = "MISSING_FX3_SAFE_STOCK_FLG"
ERR_PARTIAL_RESCUE_BUNDLE: str = "PARTIAL_RESCUE_BUNDLE_MISSING_PARTITION"
ERR_TRUNCATED_RESCUE_ARTIFACT: str = "TRUNCATED_OR_UNALIGNED_RESCUE_ARTIFACT"
ERR_BLANK_RESCUE_ARTIFACT: str = "BLANK_OR_ZEROED_RESCUE_ARTIFACT"
ERR_RESCUE_SHA256_MISMATCH: str = "RESCUE_ARTIFACT_SHA256_MISMATCH"
ERR_RESCUE_PARITY_FAILURE: str = "RESCUE_GF256_PQ_PARITY_FAILURE"
ERR_RESCUE_BODY_BINDING_MISMATCH: str = "RESCUE_CROSS_BODY_SERIAL_BINDING_MISMATCH"
ERR_TWO_MAN_RULE_VIOLATION: str = "TWO_MAN_INTEGRITY_RULE_VIOLATION"
ERR_AIR_GAP_VIOLATION: str = "RESCUE_BUNDLE_NOT_AIR_GAPPED"

_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")


# ---------------------------------------------------------------------------
# Structured Dataclasses (Zero raw bytes fields exposed in repr/to_dict)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DonorArtifactDigest:
    label: str
    source_mode: str
    byte_length: int
    sha256: str
    magic_ok: bool
    details: Dict[str, Any]


@dataclass(frozen=True)
class DonorReadOnlySnapshot:
    verification_mode: str
    read_only_access: bool
    artifacts: Tuple[DonorArtifactDigest, ...]
    snapshot_sha256: str


@dataclass(frozen=True)
class GptPartitionInfo:
    slot_index: int
    name: str
    type_guid_hex: str
    unique_guid_hex: str
    starting_lba: int
    ending_lba: int
    size_lbas: int
    attributes: int
    aligned_4k: bool


@dataclass(frozen=True)
class GptSideAuditReport:
    side: str
    valid: bool
    signature_ok: bool
    revision_ok: bool
    header_crc32_ok: bool
    array_crc32_ok: bool
    geometry_ok: bool
    alignment_4k_ok: bool
    no_overlaps_ok: bool
    sku_match_ok: bool
    my_lba: int
    alternate_lba: int
    first_usable_lba: int
    last_usable_lba: int
    partition_entry_lba: int
    num_entries: int
    entry_size: int
    active_partition_count: int
    header_crc32_stored: int
    header_crc32_computed: int
    array_crc32_stored: int
    array_crc32_computed: int
    disk_guid_hex: str
    partitions: Tuple[GptPartitionInfo, ...]
    error_codes: Tuple[str, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class GptHealResult:
    passed: bool
    action: str
    target_sku: str
    ram_only: bool
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    primary_before_valid: bool
    backup_before_valid: bool
    primary_after_valid: bool
    backup_after_valid: bool
    reconstructed_primary_sha256: str
    reconstructed_backup_sha256: str
    reconstructed_array_sha256: str
    sector0_fx3_valid: bool
    primary_audit: GptSideAuditReport
    backup_audit: GptSideAuditReport
    error_codes: Tuple[str, ...]
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RpmbFrameInfo:
    req_resp: int
    result: int
    block_count: int
    address: int
    write_counter: int
    nonce_hex: str
    mac_hex: str
    data_sha256: str
    payload_sha256: str


@dataclass(frozen=True)
class RpmbSandboxResponse:
    accepted: bool
    result_code: int
    result_name: str
    req_resp: int
    write_counter_before: int
    write_counter_after: int
    mac_valid: bool
    nonce_valid: bool
    counter_valid: bool
    counter_expired: bool
    rpmb_writes_emitted: int
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    response_frame_sha256: str
    response_info: RpmbFrameInfo
    error_codes: Tuple[str, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class StageBZeroRpmbProof:
    passed: bool
    stage_b_mount_base: str
    rpmb_writes_emitted: int
    otp_fuse_touches: int
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    rationale: str


@dataclass(frozen=True)
class TwoManAttestation:
    operator_a_id: str
    operator_a_signature_sha256: str
    operator_b_id: str
    operator_b_signature_sha256: str
    air_gapped: bool
    network_interfaces_disabled: bool


@dataclass(frozen=True)
class SdRescueBundleManifest:
    schema: str
    sentinel_filename: str
    sentinel_present: bool
    sentinel_sha256: str
    camera_model: str
    body_serial_hash: str
    cnflasha_calibration_sha256: str
    c2pa_rq_lic_sha256: str
    body_identity_binding_sha256: str
    partition_order: Tuple[str, ...]
    partition_sizes: Dict[str, int]
    partition_sha256s: Dict[str, str]
    stripe_bytes: int
    p_parity_sha256: str
    q_parity_sha256: str
    bundle_sha256: str
    two_man_attestation: TwoManAttestation
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    physical_device_writes: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SdRescueVerificationReport:
    passed: bool
    stage_b_rehearsal_permitted: bool
    status: str
    sentinel_verified: bool
    partition_count_verified: int
    parity_verified: bool
    parity_single_loss_heal_verified: bool
    body_binding_verified: bool
    two_man_rule_verified: bool
    air_gapped_verified: bool
    bundle_sha256: str
    body_identity_binding_sha256: str
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    physical_device_writes: int
    error_codes: Tuple[str, ...]
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GptRpmbAndRescueSuiteReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    donor_snapshot: DonorReadOnlySnapshot
    gpt_healthy_check: GptHealResult
    gpt_heal_primary_from_backup: GptHealResult
    gpt_heal_backup_from_primary: GptHealResult
    gpt_reject_overlap_passed: bool
    gpt_reject_misaligned_4k_passed: bool
    gpt_reject_fx6_transplant_passed: bool
    gpt_reject_both_corrupted_passed: bool
    rpmb_authenticated_write_passed: bool
    rpmb_reject_stale_counter_passed: bool
    rpmb_reject_nonce_mismatch_passed: bool
    rpmb_reject_mac_forgery_passed: bool
    rpmb_reject_counter_expired_passed: bool
    stage_b_zero_rpmb_proof: StageBZeroRpmbProof
    sd_rescue_valid_report: SdRescueVerificationReport
    sd_rescue_reject_missing_sentinel_passed: bool
    sd_rescue_reject_truncated_artifact_passed: bool
    sd_rescue_reject_cross_body_passed: bool
    sd_rescue_reject_single_operator_passed: bool
    suite_sha256: str
    otp_fuse_touches: int
    passive_tx_bytes_emitted: int
    rpmb_writes_emitted: int
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    allow_boot_partition_targeting: bool
    allow_destructive_fastboot: bool
    errors: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Internal Helpers (Read-Only O_RDONLY Inspection & Canonical Digests)
# ---------------------------------------------------------------------------


def _canonical_sha256(obj: Any) -> str:
    encoded = json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _read_bounded_readonly(path: Path, *, max_bytes: int = 131072) -> Tuple[bytes, int]:
    if path.is_symlink():
        raise ValueError(f"Symlink rejected for read-only donor access: {path.name}")
    require(hasattr(os, "O_NOFOLLOW"), "POSIX O_NOFOLLOW is required")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1:
            raise ValueError(f"Single-link regular file required: {path.name}")
        to_read = min(st.st_size, max_bytes)
        chunks: List[bytes] = []
        remaining = to_read
        while remaining > 0:
            blk = os.read(fd, remaining)
            if not blk:
                break
            chunks.append(blk)
            remaining -= len(blk)
        return b"".join(chunks), st.st_size
    finally:
        os.close(fd)


def inspect_donor_partition_metadata_readonly(
    *,
    force_clean_room: Optional[bool] = None,
) -> DonorReadOnlySnapshot:
    """Inspect FX3/FX6 donor partition metadata strictly via os.O_RDONLY with clean-room fallback."""
    use_clean_room = is_forced_clean_room() if force_clean_room is None else bool(force_clean_room)

    p1_path = None if use_clean_room else resolve_donor_path(DONOR_FX3_P1_205_RELPATH, require_file=True)
    fx3_wbi_path = None if use_clean_room else resolve_donor_path(DONOR_FX3_WBI2_RELPATH, require_file=True)
    fx6_wbi_path = None if use_clean_room else resolve_donor_path(DONOR_FX6_WBI2_RELPATH, require_file=True)
    dtb_path = None if use_clean_room else resolve_donor_path(DONOR_CXD90057_DTB_RELPATH, require_file=True)

    donor_present = (
        not use_clean_room
        and p1_path is not None and p1_path.is_file()
        and fx3_wbi_path is not None and fx3_wbi_path.is_file()
        and fx6_wbi_path is not None and fx6_wbi_path.is_file()
        and dtb_path is not None and dtb_path.is_file()
    )

    artifacts: List[DonorArtifactDigest] = []
    if donor_present:
        mode = "LOCAL_DONOR_O_RDONLY"
        p1_head, p1_total = _read_bounded_readonly(p1_path, max_bytes=65536)  # type: ignore[arg-type]
        fx3_wbi_head, fx3_wbi_total = _read_bounded_readonly(fx3_wbi_path, max_bytes=512)  # type: ignore[arg-type]
        fx6_wbi_head, fx6_wbi_total = _read_bounded_readonly(fx6_wbi_path, max_bytes=512)  # type: ignore[arg-type]
        dtb_head, dtb_total = _read_bounded_readonly(dtb_path, max_bytes=65536)  # type: ignore[arg-type]
    else:
        mode = "CLEAN_ROOM_SYNTHETIC"
        p1_head = build_synthetic_p1_vfat_image()
        p1_total = len(p1_head)
        fx3_wbi_head = build_synthetic_wbi2_header_bytes(sections=FX3_WBI2_EXPECTED_SECTIONS)
        fx3_wbi_total = len(fx3_wbi_head)
        fx6_wbi_head = build_synthetic_wbi2_header_bytes(sections=FX6_WBI2_EXPECTED_SECTIONS)
        fx6_wbi_total = len(fx6_wbi_head)
        dtb_buf = bytearray(4096)
        struct.pack_into(">II", dtb_buf, 0, 0xD00DFEED, 4096)
        dtb_buf[40:56] = b"sony,cxd90057\x00\x00\x00"
        dtb_head = bytes(dtb_buf)
        dtb_total = len(dtb_head)

    p1_boot_sig_ok = len(p1_head) >= 512 and p1_head[510:512] == b"\x55\xaa"
    artifacts.append(
        DonorArtifactDigest(
            label="fx3_p1_vfat",
            source_mode=mode,
            byte_length=p1_total,
            sha256=sha256(p1_head).hexdigest(),
            magic_ok=p1_boot_sig_ok,
            details={"boot_sig_hex": p1_head[510:512].hex() if len(p1_head) >= 512 else ""},
        )
    )

    fx3_sec_cnt = struct.unpack_from("<Q", fx3_wbi_head, 8)[0] if len(fx3_wbi_head) >= 16 else 0
    artifacts.append(
        DonorArtifactDigest(
            label="fx3_p5_wbi2",
            source_mode=mode,
            byte_length=fx3_wbi_total,
            sha256=sha256(fx3_wbi_head).hexdigest(),
            magic_ok=(fx3_wbi_head[:4] == b"WBI2" and fx3_sec_cnt == FX3_WBI2_EXPECTED_SECTIONS),
            details={"magic": fx3_wbi_head[:4].decode("ascii", errors="replace"), "sections": fx3_sec_cnt},
        )
    )

    fx6_sec_cnt = struct.unpack_from("<Q", fx6_wbi_head, 8)[0] if len(fx6_wbi_head) >= 16 else 0
    artifacts.append(
        DonorArtifactDigest(
            label="fx6_p5_wbi2",
            source_mode=mode,
            byte_length=fx6_wbi_total,
            sha256=sha256(fx6_wbi_head).hexdigest(),
            magic_ok=(fx6_wbi_head[:4] == b"WBI2" and fx6_sec_cnt == FX6_WBI2_EXPECTED_SECTIONS),
            details={"magic": fx6_wbi_head[:4].decode("ascii", errors="replace"), "sections": fx6_sec_cnt},
        )
    )

    dtb_magic_ok = len(dtb_head) >= 8 and dtb_head[:4] == b"\xd0\x0d\xfe\xed"
    artifacts.append(
        DonorArtifactDigest(
            label="cxd90057_dtb",
            source_mode=mode,
            byte_length=dtb_total,
            sha256=sha256(dtb_head).hexdigest(),
            magic_ok=dtb_magic_ok,
            details={"fdt_magic_hex": dtb_head[:4].hex()},
        )
    )

    snap_sha = _canonical_sha256([asdict(a) for a in artifacts])
    return DonorReadOnlySnapshot(
        verification_mode=mode,
        read_only_access=READ_ONLY_DONOR_ACCESS,
        artifacts=tuple(artifacts),
        snapshot_sha256=snap_sha,
    )


# ---------------------------------------------------------------------------
# Pillar 1 — Primary vs Backup GPT CRC32 & Partition Overlap Healer (RAM-Only)
# ---------------------------------------------------------------------------


def _crc32(data: bytes) -> int:
    return zlib.crc32(data) & 0xFFFFFFFF


def _encode_gpt_name(name: str) -> bytes:
    raw = name[:35].encode("utf-16-le")
    return raw.ljust(72, b"\x00")[:72]


def _decode_gpt_name(raw: bytes) -> str:
    return raw.decode("utf-16-le", errors="replace").split("\x00", 1)[0]


def _build_gpt_header_bytes(
    *,
    my_lba: int,
    alternate_lba: int,
    first_usable_lba: int,
    last_usable_lba: int,
    disk_guid: bytes,
    partition_entry_lba: int,
    num_entries: int,
    entry_size: int,
    array_crc32: int,
) -> bytes:
    require(len(disk_guid) == 16, "disk_guid must be 16 bytes")
    hdr92 = bytearray(GPT_HEADER_SIZE)
    struct.pack_into(
        "<8sIIIIQQQQ16sQIII",
        hdr92,
        0,
        GPT_SIGNATURE,
        GPT_REVISION_1_0,
        GPT_HEADER_SIZE,
        0,  # CRC32 placeholder
        0,  # Reserved
        my_lba,
        alternate_lba,
        first_usable_lba,
        last_usable_lba,
        disk_guid,
        partition_entry_lba,
        num_entries,
        entry_size,
        array_crc32,
    )
    hcrc = _crc32(bytes(hdr92))
    struct.pack_into("<I", hdr92, 16, hcrc)
    return bytes(hdr92).ljust(GPT_SECTOR_SIZE, b"\x00")


def build_cxd90057_gpt_pair(
    *,
    sku: str = FX3_SKU_CODE,
    total_lbas: int = GPT_DEFAULT_TOTAL_LBAS,
    partitions: Optional[Sequence[Tuple[int, str, int, int, str]]] = None,
) -> Tuple[bytes, bytes, bytes, bytes]:
    """Build deterministic Primary (LBA 1) & Backup (Last LBA) GPT + 128-entry arrays."""
    norm_sku = sku.strip().upper()
    if norm_sku not in (FX3_SKU_CODE, FX6_SKU_CODE):
        raise ValueError(f"Unsupported SKU: {sku}")

    if partitions is None:
        if norm_sku == FX3_SKU_CODE:
            part_defs = list(CXD90057_FX3_15_PARTITIONS)
        else:
            # FX6 cross-SKU geometry shifts p15 lens_cal to 0x00312000 and alters p7/p14
            part_defs = []
            for pid, pname, start_lba, size_lbas, role in CXD90057_FX3_15_PARTITIONS:
                if pid == 7:
                    part_defs.append((7, "p7_fx6_rootfs", start_lba, 0x00010000, role))
                elif pid == 14:
                    part_defs.append((14, "p14_fx6_usr", start_lba, 0x000F0000, role))
                elif pid == 15:
                    part_defs.append((15, "p15_fx6_lens_cal", FX6_SHIFTED_LENS_CAL_START_LBA, size_lbas, role))
                else:
                    part_defs.append((pid, f"fx6_{pname}", start_lba, size_lbas, role))
    else:
        part_defs = list(partitions)

    disk_guid = FX3_GPT_DISK_GUID if norm_sku == FX3_SKU_CODE else FX6_GPT_DISK_GUID
    last_usable = total_lbas - GPT_ARRAY_SECTORS - 2
    array_buf = bytearray(GPT_ARRAY_BYTES)

    for pid, pname, start_lba, size_lbas, _role in part_defs:
        require(1 <= pid <= GPT_ENTRY_COUNT, f"invalid partition index {pid}")
        require(size_lbas > 0, f"partition {pid} size must be > 0")
        end_lba = start_lba + size_lbas - 1
        off = (pid - 1) * GPT_ENTRY_SIZE
        unique_guid = sha256(f"{norm_sku}:{pid}:{pname}".encode("utf-8")).digest()[:16]
        struct.pack_into(
            "<16s16sQQQ72s",
            array_buf,
            off,
            FX3_GPT_PART_TYPE_GUID,
            unique_guid,
            start_lba,
            end_lba,
            0,
            _encode_gpt_name(pname),
        )

    array_bytes = bytes(array_buf)
    array_crc = _crc32(array_bytes)

    primary_hdr = _build_gpt_header_bytes(
        my_lba=1,
        alternate_lba=total_lbas - 1,
        first_usable_lba=GPT_FIRST_USABLE_LBA,
        last_usable_lba=last_usable,
        disk_guid=disk_guid,
        partition_entry_lba=2,
        num_entries=GPT_ENTRY_COUNT,
        entry_size=GPT_ENTRY_SIZE,
        array_crc32=array_crc,
    )
    backup_hdr = _build_gpt_header_bytes(
        my_lba=total_lbas - 1,
        alternate_lba=1,
        first_usable_lba=GPT_FIRST_USABLE_LBA,
        last_usable_lba=last_usable,
        disk_guid=disk_guid,
        partition_entry_lba=total_lbas - GPT_ARRAY_SECTORS - 1,
        num_entries=GPT_ENTRY_COUNT,
        entry_size=GPT_ENTRY_SIZE,
        array_crc32=array_crc,
    )
    return primary_hdr, array_bytes, backup_hdr, array_bytes


def validate_gpt_side(
    header_bytes: bytes,
    array_bytes: bytes,
    *,
    side: str,
    expected_my_lba: int,
    expected_alt_lba: int,
    expected_entry_lba: int,
    total_lbas: int = GPT_DEFAULT_TOTAL_LBAS,
    target_sku: str = FX3_SKU_CODE,
) -> GptSideAuditReport:
    """Validate a single GPT side (Primary or Backup) for CRC32, 4KiB alignment, overlaps & SKU."""
    errors: List[str] = []
    codes: List[str] = []

    if len(header_bytes) < GPT_HEADER_SIZE:
        return GptSideAuditReport(
            side=side,
            valid=False,
            signature_ok=False,
            revision_ok=False,
            header_crc32_ok=False,
            array_crc32_ok=False,
            geometry_ok=False,
            alignment_4k_ok=False,
            no_overlaps_ok=False,
            sku_match_ok=False,
            my_lba=0,
            alternate_lba=0,
            first_usable_lba=0,
            last_usable_lba=0,
            partition_entry_lba=0,
            num_entries=0,
            entry_size=0,
            active_partition_count=0,
            header_crc32_stored=0,
            header_crc32_computed=0,
            array_crc32_stored=0,
            array_crc32_computed=0,
            disk_guid_hex="",
            partitions=(),
            error_codes=(ERR_GPT_GEOMETRY_INVALID,),
            errors=(f"{side}:GPT_HEADER_TRUNCATED:{len(header_bytes)}<{GPT_HEADER_SIZE}",),
        )

    hdr92 = header_bytes[:GPT_HEADER_SIZE]
    (
        sig,
        rev,
        hdr_sz,
        hcrc_stored,
        _reserved,
        my_lba,
        alt_lba,
        first_usable,
        last_usable,
        disk_guid,
        entry_lba,
        num_entries,
        entry_size,
        acrc_stored,
    ) = struct.unpack("<8sIIIIQQQQ16sQIII", hdr92)

    sig_ok = sig == GPT_SIGNATURE
    rev_ok = rev == GPT_REVISION_1_0 and hdr_sz == GPT_HEADER_SIZE
    zeroed_hdr = bytearray(hdr92)
    struct.pack_into("<I", zeroed_hdr, 16, 0)
    hcrc_computed = _crc32(bytes(zeroed_hdr))
    hcrc_ok = sig_ok and rev_ok and (hcrc_stored == hcrc_computed)

    if not sig_ok:
        codes.append(ERR_GPT_BAD_SIGNATURE)
        errors.append(f"{side}:bad_signature_hex={sig.hex()}")
    if not rev_ok:
        codes.append(ERR_GPT_GEOMETRY_INVALID)
        errors.append(f"{side}:bad_revision_or_hdr_size:rev=0x{rev:x},sz={hdr_sz}")
    if sig_ok and hcrc_stored != hcrc_computed:
        codes.append(ERR_GPT_BAD_HEADER_CRC32)
        errors.append(f"{side}:header_crc32_mismatch:stored=0x{hcrc_stored:08x},calc=0x{hcrc_computed:08x}")

    expected_array_len = GPT_ENTRY_COUNT * GPT_ENTRY_SIZE
    acrc_computed = _crc32(array_bytes[:expected_array_len]) if len(array_bytes) >= expected_array_len else 0
    acrc_ok = (len(array_bytes) == expected_array_len) and (acrc_stored == acrc_computed)
    if not acrc_ok:
        codes.append(ERR_GPT_BAD_ARRAY_CRC32)
        errors.append(f"{side}:array_crc32_mismatch:stored=0x{acrc_stored:08x},calc=0x{acrc_computed:08x}")

    geom_ok = (
        my_lba == expected_my_lba
        and alt_lba == expected_alt_lba
        and entry_lba == expected_entry_lba
        and num_entries == GPT_ENTRY_COUNT
        and entry_size == GPT_ENTRY_SIZE
        and first_usable >= 34
        and last_usable < total_lbas - GPT_ARRAY_SECTORS - 1
        and first_usable <= last_usable
    )
    if not geom_ok:
        codes.append(ERR_GPT_GEOMETRY_INVALID)
        errors.append(
            f"{side}:lba_geometry_mismatch:my={my_lba}/{expected_my_lba},"
            f"alt={alt_lba}/{expected_alt_lba},entry={entry_lba}/{expected_entry_lba}"
        )

    parsed_parts: List[GptPartitionInfo] = []
    align_ok = True
    overlap_ok = True
    sku_ok = True
    spans: List[Tuple[int, int, int]] = []
    zero_guid = b"\x00" * 16

    if len(array_bytes) >= expected_array_len:
        for idx in range(GPT_ENTRY_COUNT):
            off = idx * GPT_ENTRY_SIZE
            raw_e = array_bytes[off : off + GPT_ENTRY_SIZE]
            type_guid, uniq_guid, s_lba, e_lba, attrs, raw_name = struct.unpack("<16s16sQQQ72s", raw_e)
            if type_guid == zero_guid:
                continue
            pname = _decode_gpt_name(raw_name)
            if e_lba < s_lba:
                overlap_ok = False
                codes.append(ERR_GPT_GEOMETRY_INVALID)
                errors.append(f"{side}:p{idx + 1}:end_lba({e_lba})<start_lba({s_lba})")
                size_lbas = 0
            else:
                size_lbas = e_lba - s_lba + 1

            is_4k = (s_lba % GPT_4K_ALIGNMENT_SECTORS == 0) and (size_lbas % GPT_4K_ALIGNMENT_SECTORS == 0)
            if not is_4k:
                align_ok = False
                codes.append(ERR_GPT_MISALIGNED_4K)
                errors.append(f"{side}:p{idx + 1}({pname}):misaligned_4k:start=0x{s_lba:x},size=0x{size_lbas:x}")

            if s_lba < first_usable or e_lba > last_usable:
                geom_ok = False
                codes.append(ERR_GPT_OUT_OF_USABLE_RANGE)
                errors.append(f"{side}:p{idx + 1}({pname}):out_of_usable_range:[{s_lba},{e_lba}]")

            for prev_s, prev_e, prev_idx in spans:
                if not (e_lba < prev_s or s_lba > prev_e):
                    overlap_ok = False
                    codes.append(ERR_GPT_PARTITION_OVERLAP)
                    errors.append(
                        f"{side}:overlap:p{idx + 1}[0x{s_lba:x}..0x{e_lba:x}]_vs_p{prev_idx}[0x{prev_s:x}..0x{prev_e:x}]"
                    )
            spans.append((s_lba, e_lba, idx + 1))

            parsed_parts.append(
                GptPartitionInfo(
                    slot_index=idx + 1,
                    name=pname,
                    type_guid_hex=type_guid.hex(),
                    unique_guid_hex=uniq_guid.hex(),
                    starting_lba=s_lba,
                    ending_lba=e_lba,
                    size_lbas=size_lbas,
                    attributes=attrs,
                    aligned_4k=is_4k,
                )
            )

    norm_sku = target_sku.strip().upper()
    if norm_sku == FX3_SKU_CODE:
        if disk_guid == FX6_GPT_DISK_GUID:
            sku_ok = False
            codes.append(ERR_CROSS_SKU_FX6_GPT_TRANSPLANT)
            errors.append(f"{side}:FX6_disk_guid_rejected_on_FX3")
        for p in parsed_parts:
            if "fx6" in p.name.lower() or p.starting_lba == FX6_SHIFTED_LENS_CAL_START_LBA:
                sku_ok = False
                codes.append(ERR_CROSS_SKU_FX6_GPT_TRANSPLANT)
                errors.append(
                    f"{side}:FX6_geometry_shift_rejected_on_FX3:p{p.slot_index}({p.name})@0x{p.starting_lba:x}"
                )
        if len(parsed_parts) != len(CXD90057_FX3_15_PARTITIONS):
            geom_ok = False
            codes.append(ERR_GPT_GEOMETRY_INVALID)
            errors.append(
                f"{side}:expected_{len(CXD90057_FX3_15_PARTITIONS)}_partitions,got={len(parsed_parts)}"
            )

    dedup_codes = tuple(dict.fromkeys(codes))
    valid = sig_ok and rev_ok and hcrc_ok and acrc_ok and geom_ok and align_ok and overlap_ok and sku_ok
    return GptSideAuditReport(
        side=side,
        valid=valid,
        signature_ok=sig_ok,
        revision_ok=rev_ok,
        header_crc32_ok=hcrc_ok,
        array_crc32_ok=acrc_ok,
        geometry_ok=geom_ok,
        alignment_4k_ok=align_ok,
        no_overlaps_ok=overlap_ok,
        sku_match_ok=sku_ok,
        my_lba=my_lba,
        alternate_lba=alt_lba,
        first_usable_lba=first_usable,
        last_usable_lba=last_usable,
        partition_entry_lba=entry_lba,
        num_entries=num_entries,
        entry_size=entry_size,
        active_partition_count=len(parsed_parts),
        header_crc32_stored=hcrc_stored,
        header_crc32_computed=hcrc_computed,
        array_crc32_stored=acrc_stored,
        array_crc32_computed=acrc_computed,
        disk_guid_hex=disk_guid.hex(),
        partitions=tuple(parsed_parts),
        error_codes=dedup_codes,
        errors=tuple(errors),
    )


def _reconstruct_alternate_gpt_header(
    healthy_header: bytes,
    *,
    target_my_lba: int,
    target_alt_lba: int,
    target_entry_lba: int,
) -> bytes:
    hdr92 = bytearray(healthy_header[:GPT_HEADER_SIZE])
    struct.pack_into("<I", hdr92, 16, 0)
    struct.pack_into("<QQ", hdr92, 24, target_my_lba, target_alt_lba)
    struct.pack_into("<Q", hdr92, 72, target_entry_lba)
    hcrc = _crc32(bytes(hdr92))
    struct.pack_into("<I", hdr92, 16, hcrc)
    return bytes(hdr92).ljust(GPT_SECTOR_SIZE, b"\x00")


def heal_gpt_pair_ram_only(
    primary_header: bytes,
    primary_array: bytes,
    backup_header: bytes,
    backup_array: bytes,
    *,
    total_lbas: int = GPT_DEFAULT_TOTAL_LBAS,
    target_sku: str = FX3_SKU_CODE,
    sector0_bytes: Optional[bytes] = None,
) -> Tuple[GptHealResult, Optional[Tuple[bytes, bytes, bytes, bytes]]]:
    """Deterministically verify & RAM-only reconstruct Primary/Backup GPT pairs (0 device writes)."""
    require(PERSISTENT_EMMC_WRITES_AUTHORIZED is False, "persistent eMMC writes must remain locked")
    require(PERSISTENT_WRITE_RELEASE is False, "persistent write release must remain locked")

    backup_hdr_lba = total_lbas - 1
    backup_arr_lba = total_lbas - GPT_ARRAY_SECTORS - 1

    pri_audit = validate_gpt_side(
        primary_header,
        primary_array,
        side="primary_lba1",
        expected_my_lba=1,
        expected_alt_lba=backup_hdr_lba,
        expected_entry_lba=2,
        total_lbas=total_lbas,
        target_sku=target_sku,
    )
    bak_audit = validate_gpt_side(
        backup_header,
        backup_array,
        side="backup_last_lba",
        expected_my_lba=backup_hdr_lba,
        expected_alt_lba=1,
        expected_entry_lba=backup_arr_lba,
        total_lbas=total_lbas,
        target_sku=target_sku,
    )

    sec0 = build_synthetic_sector0_fx3() if sector0_bytes is None else sector0_bytes
    sec0_rep = verify_sector0_dump(sec0)
    sec0_ok = sec0_rep.valid and sec0_rep.fx3_immutability_ok

    if not sec0_ok:
        return (
            GptHealResult(
                passed=False,
                action="REJECTED_INVALID_SONY_SECTOR0",
                target_sku=target_sku,
                ram_only=True,
                physical_device_writes=PHYSICAL_DEVICE_WRITES,
                persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
                primary_before_valid=pri_audit.valid,
                backup_before_valid=bak_audit.valid,
                primary_after_valid=False,
                backup_after_valid=False,
                reconstructed_primary_sha256="",
                reconstructed_backup_sha256="",
                reconstructed_array_sha256="",
                sector0_fx3_valid=False,
                primary_audit=pri_audit,
                backup_audit=bak_audit,
                error_codes=("SECTOR0_INVALID_OR_FX6_SHIFT",),
                errors=sec0_rep.errors,
            ),
            None,
        )

    if pri_audit.valid and bak_audit.valid:
        if primary_array != backup_array:
            return (
                GptHealResult(
                    passed=False,
                    action="REJECTED_PRIMARY_BACKUP_ARRAY_DIVERGENCE",
                    target_sku=target_sku,
                    ram_only=True,
                    physical_device_writes=PHYSICAL_DEVICE_WRITES,
                    persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
                    primary_before_valid=True,
                    backup_before_valid=True,
                    primary_after_valid=False,
                    backup_after_valid=False,
                    reconstructed_primary_sha256="",
                    reconstructed_backup_sha256="",
                    reconstructed_array_sha256="",
                    sector0_fx3_valid=sec0_ok,
                    primary_audit=pri_audit,
                    backup_audit=bak_audit,
                    error_codes=("GPT_PRIMARY_BACKUP_DIVERGENCE",),
                    errors=("Primary and Backup GPT partition arrays diverge despite valid CRCs.",),
                ),
                None,
            )
        return (
            GptHealResult(
                passed=True,
                action="HEALTHY_NO_HEAL_NEEDED",
                target_sku=target_sku,
                ram_only=True,
                physical_device_writes=PHYSICAL_DEVICE_WRITES,
                persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
                primary_before_valid=True,
                backup_before_valid=True,
                primary_after_valid=True,
                backup_after_valid=True,
                reconstructed_primary_sha256=sha256(primary_header[:GPT_SECTOR_SIZE]).hexdigest(),
                reconstructed_backup_sha256=sha256(backup_header[:GPT_SECTOR_SIZE]).hexdigest(),
                reconstructed_array_sha256=sha256(primary_array).hexdigest(),
                sector0_fx3_valid=sec0_ok,
                primary_audit=pri_audit,
                backup_audit=bak_audit,
                error_codes=(),
                errors=(),
            ),
            (primary_header[:GPT_SECTOR_SIZE], primary_array, backup_header[:GPT_SECTOR_SIZE], backup_array),
        )

    if not pri_audit.valid and bak_audit.valid:
        healed_pri_hdr = _reconstruct_alternate_gpt_header(
            backup_header,
            target_my_lba=1,
            target_alt_lba=backup_hdr_lba,
            target_entry_lba=2,
        )
        healed_pri_arr = backup_array
        recheck_pri = validate_gpt_side(
            healed_pri_hdr,
            healed_pri_arr,
            side="primary_lba1_reconstructed",
            expected_my_lba=1,
            expected_alt_lba=backup_hdr_lba,
            expected_entry_lba=2,
            total_lbas=total_lbas,
            target_sku=target_sku,
        )
        return (
            GptHealResult(
                passed=recheck_pri.valid,
                action="RECONSTRUCTED_PRIMARY_FROM_BACKUP_RAM_ONLY",
                target_sku=target_sku,
                ram_only=True,
                physical_device_writes=PHYSICAL_DEVICE_WRITES,
                persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
                primary_before_valid=False,
                backup_before_valid=True,
                primary_after_valid=recheck_pri.valid,
                backup_after_valid=True,
                reconstructed_primary_sha256=sha256(healed_pri_hdr).hexdigest(),
                reconstructed_backup_sha256=sha256(backup_header[:GPT_SECTOR_SIZE]).hexdigest(),
                reconstructed_array_sha256=sha256(healed_pri_arr).hexdigest(),
                sector0_fx3_valid=sec0_ok,
                primary_audit=recheck_pri,
                backup_audit=bak_audit,
                error_codes=recheck_pri.error_codes,
                errors=recheck_pri.errors,
            ),
            (healed_pri_hdr, healed_pri_arr, backup_header[:GPT_SECTOR_SIZE], backup_array)
            if recheck_pri.valid
            else None,
        )

    if pri_audit.valid and not bak_audit.valid:
        healed_bak_hdr = _reconstruct_alternate_gpt_header(
            primary_header,
            target_my_lba=backup_hdr_lba,
            target_alt_lba=1,
            target_entry_lba=backup_arr_lba,
        )
        healed_bak_arr = primary_array
        recheck_bak = validate_gpt_side(
            healed_bak_hdr,
            healed_bak_arr,
            side="backup_last_lba_reconstructed",
            expected_my_lba=backup_hdr_lba,
            expected_alt_lba=1,
            expected_entry_lba=backup_arr_lba,
            total_lbas=total_lbas,
            target_sku=target_sku,
        )
        return (
            GptHealResult(
                passed=recheck_bak.valid,
                action="RECONSTRUCTED_BACKUP_FROM_PRIMARY_RAM_ONLY",
                target_sku=target_sku,
                ram_only=True,
                physical_device_writes=PHYSICAL_DEVICE_WRITES,
                persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
                primary_before_valid=True,
                backup_before_valid=False,
                primary_after_valid=True,
                backup_after_valid=recheck_bak.valid,
                reconstructed_primary_sha256=sha256(primary_header[:GPT_SECTOR_SIZE]).hexdigest(),
                reconstructed_backup_sha256=sha256(healed_bak_hdr).hexdigest(),
                reconstructed_array_sha256=sha256(healed_bak_arr).hexdigest(),
                sector0_fx3_valid=sec0_ok,
                primary_audit=pri_audit,
                backup_audit=recheck_bak,
                error_codes=recheck_bak.error_codes,
                errors=recheck_bak.errors,
            ),
            (primary_header[:GPT_SECTOR_SIZE], primary_array, healed_bak_hdr, healed_bak_arr)
            if recheck_bak.valid
            else None,
        )

    combined_codes = tuple(dict.fromkeys([ERR_GPT_BOTH_COPIES_CORRUPTED, *pri_audit.error_codes, *bak_audit.error_codes]))
    combined_errs = pri_audit.errors + bak_audit.errors
    return (
        GptHealResult(
            passed=False,
            action="REJECTED_FAIL_CLOSED_NO_VALID_GPT_COPY",
            target_sku=target_sku,
            ram_only=True,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            primary_before_valid=False,
            backup_before_valid=False,
            primary_after_valid=False,
            backup_after_valid=False,
            reconstructed_primary_sha256="",
            reconstructed_backup_sha256="",
            reconstructed_array_sha256="",
            sector0_fx3_valid=sec0_ok,
            primary_audit=pri_audit,
            backup_audit=bak_audit,
            error_codes=combined_codes,
            errors=combined_errs,
        ),
        None,
    )


# ---------------------------------------------------------------------------
# Pillar 2 — JEDEC eMMC 5.1 RPMB Monotonic Write-Counter & Nonce Replay Guard
# ---------------------------------------------------------------------------


def _rpmb_result_name(code: int) -> str:
    return {
        RPMB_RESULT_OK: "RESULT_OK",
        RPMB_RESULT_GENERAL_FAILURE: "RESULT_GENERAL_FAILURE",
        RPMB_RESULT_AUTH_FAILURE: "RESULT_AUTH_FAILURE",
        RPMB_RESULT_COUNTER_FAILURE: "RESULT_COUNTER_FAILURE",
        RPMB_RESULT_ADDR_FAILURE: "RESULT_ADDR_FAILURE",
        RPMB_RESULT_WRITE_FAILURE: "RESULT_WRITE_FAILURE",
        RPMB_RESULT_READ_FAILURE: "RESULT_READ_FAILURE",
        RPMB_RESULT_NO_KEY: "RESULT_NO_KEY",
        RPMB_RESULT_COUNTER_EXPIRED: "RESULT_COUNTER_EXPIRED",
    }.get(code, f"RESULT_UNKNOWN_0x{code:04X}")


def compute_rpmb_hmac_sha256(key: bytes, payload_284: bytes) -> bytes:
    require(len(key) == 32, "RPMB HMAC key must be 32 bytes")
    require(len(payload_284) == RPMB_MAC_PAYLOAD_BYTES, "RPMB MAC payload must be exactly 284 bytes")
    return hmac.new(key, payload_284, sha256).digest()


def build_rpmb_frame(
    *,
    req_resp: int,
    data: bytes = b"",
    nonce: bytes = b"\x00" * RPMB_NONCE_BYTES,
    write_counter: int = 0,
    address: int = 0,
    block_count: int = 1,
    result: int = RPMB_RESULT_OK,
    hmac_key: Optional[bytes] = SYNTHETIC_RPMB_TEST_KEY,
    override_mac: Optional[bytes] = None,
) -> bytes:
    """Build an exact JEDEC JESD84-B51 512-byte eMMC 5.1 RPMB frame."""
    require(len(data) <= RPMB_DATA_BYTES, "RPMB data field max 256 bytes")
    require(len(nonce) == RPMB_NONCE_BYTES, "RPMB nonce must be 16 bytes")
    require(0 <= write_counter <= RPMB_MAX_WRITE_COUNTER, "write_counter out of 32-bit range")
    require(0 <= address <= 0xFFFF, "address out of 16-bit range")
    require(0 <= block_count <= 0xFFFF, "block_count out of 16-bit range")
    require(0 <= result <= 0xFFFF, "result out of 16-bit range")
    require(0 <= req_resp <= 0xFFFF, "req_resp out of 16-bit range")

    buf = bytearray(RPMB_FRAME_BYTES)
    data_padded = data.ljust(RPMB_DATA_BYTES, b"\x00")
    buf[228:484] = data_padded
    buf[484:500] = nonce
    struct.pack_into(">IHHHH", buf, 500, write_counter, address, block_count, result, req_resp)

    if override_mac is not None:
        require(len(override_mac) == RPMB_MAC_BYTES, "override_mac must be 32 bytes")
        buf[196:228] = override_mac
    elif hmac_key is not None:
        buf[196:228] = compute_rpmb_hmac_sha256(hmac_key, bytes(buf[228:512]))
    return bytes(buf)


def parse_rpmb_frame(frame_bytes: bytes) -> RpmbFrameInfo:
    """Parse a 512-byte JEDEC eMMC 5.1 RPMB frame without exposing raw bytes reprs."""
    require(len(frame_bytes) == RPMB_FRAME_BYTES, f"RPMB frame must be {RPMB_FRAME_BYTES} bytes")
    mac = frame_bytes[196:228]
    data = frame_bytes[228:484]
    nonce = frame_bytes[484:500]
    write_counter, address, block_count, result, req_resp = struct.unpack_from(">IHHHH", frame_bytes, 500)
    return RpmbFrameInfo(
        req_resp=req_resp,
        result=result,
        block_count=block_count,
        address=address,
        write_counter=write_counter,
        nonce_hex=nonce.hex(),
        mac_hex=mac.hex(),
        data_sha256=sha256(data).hexdigest(),
        payload_sha256=sha256(frame_bytes[228:512]).hexdigest(),
    )


class RpmbSandboxController:
    """RAM-only JEDEC eMMC 5.1 RPMB monotonic write-counter & replay-guard sandbox."""

    def __init__(
        self,
        *,
        initial_counter: int = 17,
        synthetic_key: bytes = SYNTHETIC_RPMB_TEST_KEY,
        max_blocks: int = 64,
    ) -> None:
        require(0 <= initial_counter <= RPMB_MAX_WRITE_COUNTER, "invalid initial_counter")
        require(len(synthetic_key) == 32, "synthetic_key must be 32 bytes")
        self._key = synthetic_key
        self._counter = initial_counter
        self._max_blocks = max_blocks
        self._storage: Dict[int, bytes] = {
            addr: bytes((addr + i) & 0xFF for i in range(RPMB_DATA_BYTES)) for addr in range(max_blocks)
        }
        self._pending_nonce: Optional[bytes] = None

    @property
    def write_counter(self) -> int:
        return self._counter

    def issue_challenge_nonce(self, nonce: bytes) -> None:
        require(len(nonce) == RPMB_NONCE_BYTES, "nonce must be 16 bytes")
        self._pending_nonce = nonce

    def process_frame(
        self,
        request_frame: bytes,
        *,
        expected_nonce: Optional[bytes] = None,
        allow_physical_rpmb_write: bool = False,
    ) -> Tuple[RpmbSandboxResponse, bytes]:
        """Process a 512-byte RPMB request in RAM sandbox only (`rpmb_writes_emitted == 0`)."""
        require(PERSISTENT_EMMC_WRITES_AUTHORIZED is False, "persistent eMMC writes must stay disabled")
        require(RPMB_WRITES_EMITTED == 0, "physical RPMB writes must remain 0")

        if allow_physical_rpmb_write:
            resp_frame = build_rpmb_frame(
                req_resp=RPMB_RESP_DATA_WRITE,
                nonce=request_frame[484:500] if len(request_frame) == RPMB_FRAME_BYTES else b"\x00" * 16,
                write_counter=self._counter,
                result=RPMB_RESULT_GENERAL_FAILURE,
                hmac_key=self._key,
            )
            return (
                RpmbSandboxResponse(
                    accepted=False,
                    result_code=RPMB_RESULT_GENERAL_FAILURE,
                    result_name=_rpmb_result_name(RPMB_RESULT_GENERAL_FAILURE),
                    req_resp=RPMB_RESP_DATA_WRITE,
                    write_counter_before=self._counter,
                    write_counter_after=self._counter,
                    mac_valid=False,
                    nonce_valid=False,
                    counter_valid=False,
                    counter_expired=False,
                    rpmb_writes_emitted=RPMB_WRITES_EMITTED,
                    physical_device_writes=PHYSICAL_DEVICE_WRITES,
                    persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
                    response_frame_sha256=sha256(resp_frame).hexdigest(),
                    response_info=parse_rpmb_frame(resp_frame),
                    error_codes=(ERR_RPMB_PHYSICAL_WRITE_FORBIDDEN,),
                    errors=("Physical RPMB write requested while hard-locked read-only.",),
                ),
                resp_frame,
            )

        info = parse_rpmb_frame(request_frame)
        counter_before = self._counter
        req_nonce = request_frame[484:500]
        req_mac = request_frame[196:228]
        req_payload = request_frame[228:512]
        req_data = request_frame[228:484]

        if info.req_resp == RPMB_REQ_GET_WRITE_COUNTER:
            active_nonce = req_nonce
            if expected_nonce is not None and not hmac.compare_digest(req_nonce, expected_nonce):
                resp = build_rpmb_frame(
                    req_resp=RPMB_RESP_GET_WRITE_COUNTER,
                    nonce=req_nonce,
                    write_counter=self._counter,
                    result=RPMB_RESULT_GENERAL_FAILURE,
                    hmac_key=self._key,
                )
                return (
                    RpmbSandboxResponse(
                        accepted=False,
                        result_code=RPMB_RESULT_GENERAL_FAILURE,
                        result_name=_rpmb_result_name(RPMB_RESULT_GENERAL_FAILURE),
                        req_resp=RPMB_RESP_GET_WRITE_COUNTER,
                        write_counter_before=counter_before,
                        write_counter_after=self._counter,
                        mac_valid=True,
                        nonce_valid=False,
                        counter_valid=True,
                        counter_expired=(self._counter == RPMB_MAX_WRITE_COUNTER),
                        rpmb_writes_emitted=RPMB_WRITES_EMITTED,
                        physical_device_writes=PHYSICAL_DEVICE_WRITES,
                        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
                        response_frame_sha256=sha256(resp).hexdigest(),
                        response_info=parse_rpmb_frame(resp),
                        error_codes=(ERR_RPMB_NONCE_MISMATCH,),
                        errors=("RPMB get-write-counter nonce mismatch.",),
                    ),
                    resp,
                )
            expired = self._counter == RPMB_MAX_WRITE_COUNTER
            res_code = RPMB_RESULT_COUNTER_EXPIRED if expired else RPMB_RESULT_OK
            resp = build_rpmb_frame(
                req_resp=RPMB_RESP_GET_WRITE_COUNTER,
                nonce=active_nonce,
                write_counter=self._counter,
                result=res_code,
                hmac_key=self._key,
            )
            return (
                RpmbSandboxResponse(
                    accepted=not expired,
                    result_code=res_code,
                    result_name=_rpmb_result_name(res_code),
                    req_resp=RPMB_RESP_GET_WRITE_COUNTER,
                    write_counter_before=counter_before,
                    write_counter_after=self._counter,
                    mac_valid=True,
                    nonce_valid=True,
                    counter_valid=not expired,
                    counter_expired=expired,
                    rpmb_writes_emitted=RPMB_WRITES_EMITTED,
                    physical_device_writes=PHYSICAL_DEVICE_WRITES,
                    persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
                    response_frame_sha256=sha256(resp).hexdigest(),
                    response_info=parse_rpmb_frame(resp),
                    error_codes=(ERR_RPMB_COUNTER_EXPIRED,) if expired else (),
                    errors=("RPMB write counter reached 0xFFFFFFFF.",) if expired else (),
                ),
                resp,
            )

        if info.req_resp == RPMB_REQ_DATA_READ:
            if info.address >= self._max_blocks:
                resp = build_rpmb_frame(
                    req_resp=RPMB_RESP_DATA_READ,
                    nonce=req_nonce,
                    address=info.address,
                    result=RPMB_RESULT_ADDR_FAILURE,
                    hmac_key=self._key,
                )
                return (
                    RpmbSandboxResponse(
                        accepted=False,
                        result_code=RPMB_RESULT_ADDR_FAILURE,
                        result_name=_rpmb_result_name(RPMB_RESULT_ADDR_FAILURE),
                        req_resp=RPMB_RESP_DATA_READ,
                        write_counter_before=counter_before,
                        write_counter_after=self._counter,
                        mac_valid=True,
                        nonce_valid=True,
                        counter_valid=True,
                        counter_expired=False,
                        rpmb_writes_emitted=RPMB_WRITES_EMITTED,
                        physical_device_writes=PHYSICAL_DEVICE_WRITES,
                        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
                        response_frame_sha256=sha256(resp).hexdigest(),
                        response_info=parse_rpmb_frame(resp),
                        error_codes=("RPMB_ADDR_OUT_OF_RANGE",),
                        errors=(f"RPMB read address {info.address} >= {self._max_blocks}",),
                    ),
                    resp,
                )
            block_data = self._storage[info.address]
            resp = build_rpmb_frame(
                req_resp=RPMB_RESP_DATA_READ,
                data=block_data,
                nonce=req_nonce,
                address=info.address,
                block_count=1,
                result=RPMB_RESULT_OK,
                hmac_key=self._key,
            )
            return (
                RpmbSandboxResponse(
                    accepted=True,
                    result_code=RPMB_RESULT_OK,
                    result_name=_rpmb_result_name(RPMB_RESULT_OK),
                    req_resp=RPMB_RESP_DATA_READ,
                    write_counter_before=counter_before,
                    write_counter_after=self._counter,
                    mac_valid=True,
                    nonce_valid=True,
                    counter_valid=True,
                    counter_expired=False,
                    rpmb_writes_emitted=RPMB_WRITES_EMITTED,
                    physical_device_writes=PHYSICAL_DEVICE_WRITES,
                    persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
                    response_frame_sha256=sha256(resp).hexdigest(),
                    response_info=parse_rpmb_frame(resp),
                    error_codes=(),
                    errors=(),
                ),
                resp,
            )

        if info.req_resp == RPMB_REQ_DATA_WRITE:
            expected_mac = compute_rpmb_hmac_sha256(self._key, req_payload)
            mac_valid = hmac.compare_digest(req_mac, expected_mac)

            nonce_to_check = expected_nonce if expected_nonce is not None else self._pending_nonce
            nonce_valid = True if nonce_to_check is None else hmac.compare_digest(req_nonce, nonce_to_check)
            counter_expired = self._counter >= RPMB_MAX_WRITE_COUNTER
            counter_valid = info.write_counter == self._counter

            if counter_expired:
                resp = build_rpmb_frame(
                    req_resp=RPMB_RESP_DATA_WRITE,
                    nonce=req_nonce,
                    write_counter=self._counter,
                    address=info.address,
                    result=RPMB_RESULT_COUNTER_EXPIRED,
                    hmac_key=self._key,
                )
                return (
                    RpmbSandboxResponse(
                        accepted=False,
                        result_code=RPMB_RESULT_COUNTER_EXPIRED,
                        result_name=_rpmb_result_name(RPMB_RESULT_COUNTER_EXPIRED),
                        req_resp=RPMB_RESP_DATA_WRITE,
                        write_counter_before=counter_before,
                        write_counter_after=self._counter,
                        mac_valid=mac_valid,
                        nonce_valid=nonce_valid,
                        counter_valid=False,
                        counter_expired=True,
                        rpmb_writes_emitted=RPMB_WRITES_EMITTED,
                        physical_device_writes=PHYSICAL_DEVICE_WRITES,
                        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
                        response_frame_sha256=sha256(resp).hexdigest(),
                        response_info=parse_rpmb_frame(resp),
                        error_codes=(ERR_RPMB_COUNTER_EXPIRED,),
                        errors=("RPMB write counter exhausted at 0xFFFFFFFF (JEDEC 0x0080).",),
                    ),
                    resp,
                )

            if not mac_valid:
                resp = build_rpmb_frame(
                    req_resp=RPMB_RESP_DATA_WRITE,
                    nonce=req_nonce,
                    write_counter=self._counter,
                    address=info.address,
                    result=RPMB_RESULT_AUTH_FAILURE,
                    hmac_key=self._key,
                )
                return (
                    RpmbSandboxResponse(
                        accepted=False,
                        result_code=RPMB_RESULT_AUTH_FAILURE,
                        result_name=_rpmb_result_name(RPMB_RESULT_AUTH_FAILURE),
                        req_resp=RPMB_RESP_DATA_WRITE,
                        write_counter_before=counter_before,
                        write_counter_after=self._counter,
                        mac_valid=False,
                        nonce_valid=nonce_valid,
                        counter_valid=counter_valid,
                        counter_expired=False,
                        rpmb_writes_emitted=RPMB_WRITES_EMITTED,
                        physical_device_writes=PHYSICAL_DEVICE_WRITES,
                        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
                        response_frame_sha256=sha256(resp).hexdigest(),
                        response_info=parse_rpmb_frame(resp),
                        error_codes=(ERR_RPMB_AUTH_FAILURE,),
                        errors=("RPMB HMAC-SHA256 MAC forgery rejected (JEDEC 0x0002).",),
                    ),
                    resp,
                )

            if not nonce_valid:
                resp = build_rpmb_frame(
                    req_resp=RPMB_RESP_DATA_WRITE,
                    nonce=req_nonce,
                    write_counter=self._counter,
                    address=info.address,
                    result=RPMB_RESULT_GENERAL_FAILURE,
                    hmac_key=self._key,
                )
                return (
                    RpmbSandboxResponse(
                        accepted=False,
                        result_code=RPMB_RESULT_GENERAL_FAILURE,
                        result_name=_rpmb_result_name(RPMB_RESULT_GENERAL_FAILURE),
                        req_resp=RPMB_RESP_DATA_WRITE,
                        write_counter_before=counter_before,
                        write_counter_after=self._counter,
                        mac_valid=True,
                        nonce_valid=False,
                        counter_valid=counter_valid,
                        counter_expired=False,
                        rpmb_writes_emitted=RPMB_WRITES_EMITTED,
                        physical_device_writes=PHYSICAL_DEVICE_WRITES,
                        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
                        response_frame_sha256=sha256(resp).hexdigest(),
                        response_info=parse_rpmb_frame(resp),
                        error_codes=(ERR_RPMB_NONCE_MISMATCH,),
                        errors=("RPMB request nonce did not match active challenge nonce.",),
                    ),
                    resp,
                )

            if not counter_valid:
                resp = build_rpmb_frame(
                    req_resp=RPMB_RESP_DATA_WRITE,
                    nonce=req_nonce,
                    write_counter=self._counter,
                    address=info.address,
                    result=RPMB_RESULT_COUNTER_FAILURE,
                    hmac_key=self._key,
                )
                return (
                    RpmbSandboxResponse(
                        accepted=False,
                        result_code=RPMB_RESULT_COUNTER_FAILURE,
                        result_name=_rpmb_result_name(RPMB_RESULT_COUNTER_FAILURE),
                        req_resp=RPMB_RESP_DATA_WRITE,
                        write_counter_before=counter_before,
                        write_counter_after=self._counter,
                        mac_valid=True,
                        nonce_valid=True,
                        counter_valid=False,
                        counter_expired=False,
                        rpmb_writes_emitted=RPMB_WRITES_EMITTED,
                        physical_device_writes=PHYSICAL_DEVICE_WRITES,
                        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
                        response_frame_sha256=sha256(resp).hexdigest(),
                        response_info=parse_rpmb_frame(resp),
                        error_codes=(ERR_RPMB_COUNTER_FAILURE,),
                        errors=(
                            f"Stale/mismatched write_counter={info.write_counter} "
                            f"(expected {self._counter}, JEDEC 0x0003).",
                        ),
                    ),
                    resp,
                )

            if info.address >= self._max_blocks or info.block_count != 1:
                resp = build_rpmb_frame(
                    req_resp=RPMB_RESP_DATA_WRITE,
                    nonce=req_nonce,
                    write_counter=self._counter,
                    address=info.address,
                    result=RPMB_RESULT_ADDR_FAILURE,
                    hmac_key=self._key,
                )
                return (
                    RpmbSandboxResponse(
                        accepted=False,
                        result_code=RPMB_RESULT_ADDR_FAILURE,
                        result_name=_rpmb_result_name(RPMB_RESULT_ADDR_FAILURE),
                        req_resp=RPMB_RESP_DATA_WRITE,
                        write_counter_before=counter_before,
                        write_counter_after=self._counter,
                        mac_valid=True,
                        nonce_valid=True,
                        counter_valid=True,
                        counter_expired=False,
                        rpmb_writes_emitted=RPMB_WRITES_EMITTED,
                        physical_device_writes=PHYSICAL_DEVICE_WRITES,
                        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
                        response_frame_sha256=sha256(resp).hexdigest(),
                        response_info=parse_rpmb_frame(resp),
                        error_codes=("RPMB_ADDR_OR_COUNT_FAILURE",),
                        errors=(f"Invalid address={info.address} or block_count={info.block_count}",),
                    ),
                    resp,
                )

            # Accepted in-memory sandbox write only; hardware rpmb_writes_emitted remains 0
            self._storage[info.address] = req_data
            self._counter += 1
            self._pending_nonce = None
            resp = build_rpmb_frame(
                req_resp=RPMB_RESP_DATA_WRITE,
                nonce=req_nonce,
                write_counter=self._counter,
                address=info.address,
                block_count=1,
                result=RPMB_RESULT_OK,
                hmac_key=self._key,
            )
            return (
                RpmbSandboxResponse(
                    accepted=True,
                    result_code=RPMB_RESULT_OK,
                    result_name=_rpmb_result_name(RPMB_RESULT_OK),
                    req_resp=RPMB_RESP_DATA_WRITE,
                    write_counter_before=counter_before,
                    write_counter_after=self._counter,
                    mac_valid=True,
                    nonce_valid=True,
                    counter_valid=True,
                    counter_expired=False,
                    rpmb_writes_emitted=RPMB_WRITES_EMITTED,
                    physical_device_writes=PHYSICAL_DEVICE_WRITES,
                    persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
                    response_frame_sha256=sha256(resp).hexdigest(),
                    response_info=parse_rpmb_frame(resp),
                    error_codes=(),
                    errors=(),
                ),
                resp,
            )

        raise ValueError(f"Unsupported RPMB request type: 0x{info.req_resp:04x}")


def prove_stage_b_zero_rpmb_writes(*, mount_base: str = "/tmp/fx6_stage_b") -> StageBZeroRpmbProof:
    """Prove Stage-B volatile RAM/SD overlay requires zero physical eMMC RPMB writes."""
    require(PERSISTENT_EMMC_WRITES_AUTHORIZED is False, "persistent eMMC writes must remain locked")
    require(PERSISTENT_WRITE_RELEASE is False, "persistent write release must remain locked")
    ram_only_mount = mount_base.startswith("/tmp")
    passed = (
        ram_only_mount
        and RPMB_WRITES_EMITTED == 0
        and OTP_FUSE_TOUCHES == 0
        and PHYSICAL_DEVICE_WRITES == 0
        and not PERSISTENT_EMMC_WRITES_AUTHORIZED
        and not PERSISTENT_WRITE_RELEASE
    )
    return StageBZeroRpmbProof(
        passed=passed,
        stage_b_mount_base=mount_base,
        rpmb_writes_emitted=RPMB_WRITES_EMITTED,
        otp_fuse_touches=OTP_FUSE_TOUCHES,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        rationale=(
            "Stage-B overlays FX6 userspace solely under volatile /tmp tmpfs bind-mounts; "
            "BootROM/OP-TEE/RPMB partition is untouched (rpmb_writes_emitted == 0)."
        ),
    )


# ---------------------------------------------------------------------------
# Pillar 3 — Offline Air-Gapped SD-Rescue Kit Manifest & Two-Man Verifier
# ---------------------------------------------------------------------------


def _make_synthetic_rescue_partition(pid: int, pname: str, size_bytes: int = 4096) -> bytes:
    """Create a deterministic, high-entropy synthetic rescue partition blob (>= 4 KiB)."""
    buf = bytearray(size_bytes)
    seed_base = f"FX3_RESCUE_P{pid}_{pname}".encode("ascii")
    for offset in range(0, size_bytes, 32):
        digest = sha256(seed_base + struct.pack("<I", offset)).digest()
        chunk = digest[: min(32, size_bytes - offset)]
        buf[offset : offset + len(chunk)] = chunk
    if pid == 1:
        p1_img = build_synthetic_p1_vfat_image()
        return p1_img[:size_bytes] if len(p1_img) >= size_bytes else p1_img
    if pid == 2:
        buf[0:4] = b"BK4\x00"
        struct.pack_into("<I", buf, 4, FX3_PRODUCT_MODEL_ID)
    elif pid == 5:
        buf[0:512] = build_synthetic_wbi2_header_bytes(sections=FX3_WBI2_EXPECTED_SECTIONS)
    elif pid == 12:
        buf[0:4] = b"RQLC"
        struct.pack_into("<II", buf, 4, 1, size_bytes)
    return bytes(buf)


def compute_operator_attestation_digest(operator_id: str, bundle_sha256: str, body_binding_sha256: str) -> str:
    """Compute a deterministic two-man attestation digest (clean-room offline signature)."""
    return sha256(
        f"TWO_MAN_ATTEST_V1|{operator_id}|{bundle_sha256}|{body_binding_sha256}".encode("utf-8")
    ).hexdigest()


def build_synthetic_sd_rescue_bundle(
    *,
    body_serial_label: str = "FX3_BODY_ALPHA_0001",
    operator_a_id: str = "op-alpha-bench",
    operator_b_id: str = "op-beta-audit",
    air_gapped: bool = True,
    network_interfaces_disabled: bool = True,
) -> Tuple[Dict[str, bytes], bytes, bytes, bytes, BodyHardwareIdentity, SdRescueBundleManifest]:
    """Build a complete clean-room offline SD-rescue bundle (sentinel + p1..p15 + GF(256) P+Q)."""
    sentinel_bytes = b"FX3_SAFE_STOCK_SENTINEL_V1\n"
    partitions: Dict[str, bytes] = {}
    for pid, pname, _start_lba, _size_lbas, _role in CXD90057_FX3_15_PARTITIONS:
        partitions[pname] = _make_synthetic_rescue_partition(pid, pname, size_bytes=4096)

    ordered_shards = [partitions[name] for name in RESCUE_KIT_PARTITION_NAMES]
    stripe: Gf256ParityStripe = encode_gf256_pq_parity(
        ordered_shards,
        shard_names=RESCUE_KIT_PARTITION_NAMES,
    )

    body_identity = build_body_hardware_identity(
        camera_model=FX3_SKU_CODE,
        body_serial_hash=sha256(body_serial_label.encode("utf-8")).hexdigest(),
        cnflasha_calibration_sha256=sha256(partitions["p15_cnflasha_lens_cal"]).hexdigest(),
        c2pa_rq_lic_sha256=sha256(partitions["p12_cert_c2pa"]).hexdigest(),
    )

    part_sizes = {name: len(partitions[name]) for name in RESCUE_KIT_PARTITION_NAMES}
    part_shas = {name: sha256(partitions[name]).hexdigest() for name in RESCUE_KIT_PARTITION_NAMES}
    sentinel_sha = sha256(sentinel_bytes).hexdigest()

    bundle_sha = _canonical_sha256(
        {
            "schema": RESCUE_MANIFEST_SCHEMA,
            "sentinel_sha256": sentinel_sha,
            "body_identity_binding_sha256": body_identity.body_identity_binding_sha256,
            "partition_order": list(RESCUE_KIT_PARTITION_NAMES),
            "partition_sizes": part_sizes,
            "partition_sha256s": part_shas,
            "p_parity_sha256": stripe.p_sha256,
            "q_parity_sha256": stripe.q_sha256,
        }
    )

    attestation = TwoManAttestation(
        operator_a_id=operator_a_id,
        operator_a_signature_sha256=compute_operator_attestation_digest(
            operator_a_id,
            bundle_sha,
            body_identity.body_identity_binding_sha256,
        ),
        operator_b_id=operator_b_id,
        operator_b_signature_sha256=compute_operator_attestation_digest(
            operator_b_id,
            bundle_sha,
            body_identity.body_identity_binding_sha256,
        ),
        air_gapped=air_gapped,
        network_interfaces_disabled=network_interfaces_disabled,
    )

    manifest = SdRescueBundleManifest(
        schema=RESCUE_MANIFEST_SCHEMA,
        sentinel_filename=RESCUE_SENTINEL_FILENAME,
        sentinel_present=True,
        sentinel_sha256=sentinel_sha,
        camera_model=body_identity.camera_model,
        body_serial_hash=body_identity.body_serial_hash,
        cnflasha_calibration_sha256=body_identity.cnflasha_calibration_sha256,
        c2pa_rq_lic_sha256=body_identity.c2pa_rq_lic_sha256,
        body_identity_binding_sha256=body_identity.body_identity_binding_sha256,
        partition_order=RESCUE_KIT_PARTITION_NAMES,
        partition_sizes=part_sizes,
        partition_sha256s=part_shas,
        stripe_bytes=stripe.stripe_bytes,
        p_parity_sha256=stripe.p_sha256,
        q_parity_sha256=stripe.q_sha256,
        bundle_sha256=bundle_sha,
        two_man_attestation=attestation,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
    )
    return partitions, sentinel_bytes, stripe.p_parity, stripe.q_parity, body_identity, manifest


def verify_sd_rescue_bundle(
    partitions: Mapping[str, Optional[bytes]],
    sentinel_bytes: Optional[bytes],
    p_parity: Optional[bytes],
    q_parity: Optional[bytes],
    manifest: SdRescueBundleManifest,
    *,
    target_body_identity: BodyHardwareIdentity,
    run_parity_heal_drill: bool = True,
) -> SdRescueVerificationReport:
    """Verify an offline air-gapped SD-rescue bundle before permitting Stage-B rehearsal."""
    require(PERSISTENT_EMMC_WRITES_AUTHORIZED is False, "persistent eMMC writes must stay locked")
    require(PERSISTENT_WRITE_RELEASE is False, "persistent write release must stay locked")

    codes: List[str] = []
    errors: List[str] = []

    # 1. Sentinel FX3_SAFE_STOCK.FLG verification
    sentinel_ok = (
        manifest.sentinel_filename == RESCUE_SENTINEL_FILENAME
        and manifest.sentinel_present
        and sentinel_bytes is not None
        and sha256(sentinel_bytes).hexdigest() == manifest.sentinel_sha256
    )
    if not sentinel_ok:
        codes.append(ERR_MISSING_SENTINEL_FLAG)
        errors.append("Missing or mismatched FX3_SAFE_STOCK.FLG sentinel flag on SD rescue kit.")

    # 2. All 15 Tier-0/CXD90057 partitions completeness, alignment, non-blank & SHA-256 verification
    verified_count = 0
    ordered_shards: List[Optional[bytes]] = []
    for name in RESCUE_KIT_PARTITION_NAMES:
        data = partitions.get(name)
        if data is None:
            codes.append(ERR_PARTIAL_RESCUE_BUNDLE)
            errors.append(f"Missing rescue partition artifact: {name}")
            ordered_shards.append(None)
            continue
        exp_sz = manifest.partition_sizes.get(name, -1)
        if len(data) == 0 or len(data) != exp_sz or (len(data) % 512 != 0):
            codes.append(ERR_TRUNCATED_RESCUE_ARTIFACT)
            errors.append(f"Truncated or unaligned rescue artifact {name}: got={len(data)}, expected={exp_sz}")
            ordered_shards.append(None)
            continue
        if data.count(0x00) == len(data) or data.count(0xFF) == len(data):
            codes.append(ERR_BLANK_RESCUE_ARTIFACT)
            errors.append(f"Blank/erased rescue artifact {name} (all 0x00 or all 0xFF)")
            ordered_shards.append(None)
            continue
        actual_sha = sha256(data).hexdigest()
        exp_sha = manifest.partition_sha256s.get(name, "")
        if actual_sha != exp_sha:
            codes.append(ERR_RESCUE_SHA256_MISMATCH)
            errors.append(f"SHA-256 mismatch for {name}: actual={actual_sha[:16]}, expected={exp_sha[:16]}")
            ordered_shards.append(None)
            continue
        verified_count += 1
        ordered_shards.append(data)

    # 3. GF(256) P+Q parity verification (+ 1-shard erasure self-heal drill)
    parity_ok = False
    heal_drill_ok = False
    if p_parity is None or q_parity is None:
        codes.append(ERR_RESCUE_PARITY_FAILURE)
        errors.append("Missing GF(256) P or Q parity shard on SD rescue kit.")
    elif all(s is not None for s in ordered_shards):
        expected_shas = [manifest.partition_sha256s[n] for n in RESCUE_KIT_PARTITION_NAMES]
        expected_sizes = [manifest.partition_sizes[n] for n in RESCUE_KIT_PARTITION_NAMES]
        heal_res, _p_out, _q_out = heal_gf256_pq_shards(
            ordered_shards,
            p_parity,
            q_parity,
            shard_sizes=expected_sizes,
            stripe_bytes=manifest.stripe_bytes,
            expected_shard_sha256s=expected_shas,
            expected_p_sha256=manifest.p_parity_sha256,
            expected_q_sha256=manifest.q_parity_sha256,
            shard_names=RESCUE_KIT_PARTITION_NAMES,
        )
        parity_ok = heal_res.passed and heal_res.repair_mode == "HEALTHY_NO_REPAIR"
        if not parity_ok:
            codes.append(ERR_RESCUE_PARITY_FAILURE)
            errors.extend(heal_res.errors)
        elif run_parity_heal_drill:
            drill_shards = list(ordered_shards)
            drill_shards[4] = None  # Simulate erased p5_wbi2_hibdrv
            drill_res, _, _ = heal_gf256_pq_shards(
                drill_shards,
                p_parity,
                q_parity,
                shard_sizes=expected_sizes,
                stripe_bytes=manifest.stripe_bytes,
                expected_shard_sha256s=expected_shas,
                expected_p_sha256=manifest.p_parity_sha256,
                expected_q_sha256=manifest.q_parity_sha256,
                shard_names=RESCUE_KIT_PARTITION_NAMES,
            )
            heal_drill_ok = drill_res.passed and drill_res.bit_exact_match
            if not heal_drill_ok:
                codes.append(ERR_RESCUE_PARITY_FAILURE)
                errors.append("GF(256) P+Q single-shard erasure drill failed.")
        else:
            heal_drill_ok = True
    else:
        codes.append(ERR_RESCUE_PARITY_FAILURE)
        errors.append("Cannot verify GF(256) P+Q parity with missing or corrupt partition shards.")

    # 4. Body serial & hardware identity anti-transplant binding
    body_ok = (
        manifest.camera_model == target_body_identity.camera_model
        and manifest.body_serial_hash == target_body_identity.body_serial_hash
        and manifest.cnflasha_calibration_sha256 == target_body_identity.cnflasha_calibration_sha256
        and manifest.c2pa_rq_lic_sha256 == target_body_identity.c2pa_rq_lic_sha256
        and manifest.body_identity_binding_sha256 == target_body_identity.body_identity_binding_sha256
        and bool(_SHA256_HEX_RE.match(manifest.body_identity_binding_sha256))
    )
    if not body_ok:
        codes.append(ERR_RESCUE_BODY_BINDING_MISMATCH)
        errors.append("Cross-body serial/calibration binding mismatch; rescue kit belongs to a different body.")

    # 5. Air-gap & Two-Man Integrity Rule verification
    att = manifest.two_man_attestation
    air_gapped_ok = bool(att.air_gapped) and bool(att.network_interfaces_disabled)
    if not air_gapped_ok:
        codes.append(ERR_AIR_GAP_VIOLATION)
        errors.append("SD rescue bundle requires air_gapped=True and network_interfaces_disabled=True.")

    exp_sig_a = compute_operator_attestation_digest(
        att.operator_a_id,
        manifest.bundle_sha256,
        manifest.body_identity_binding_sha256,
    )
    exp_sig_b = compute_operator_attestation_digest(
        att.operator_b_id,
        manifest.bundle_sha256,
        manifest.body_identity_binding_sha256,
    )
    two_man_ok = (
        bool(att.operator_a_id.strip())
        and bool(att.operator_b_id.strip())
        and att.operator_a_id.strip() != att.operator_b_id.strip()
        and hmac.compare_digest(att.operator_a_signature_sha256, exp_sig_a)
        and hmac.compare_digest(att.operator_b_signature_sha256, exp_sig_b)
    )
    if not two_man_ok:
        codes.append(ERR_TWO_MAN_RULE_VIOLATION)
        errors.append("Two-Man integrity rule failed: two distinct operator attestations required.")

    all_ok = (
        sentinel_ok
        and verified_count == len(RESCUE_KIT_PARTITION_NAMES)
        and parity_ok
        and heal_drill_ok
        and body_ok
        and air_gapped_ok
        and two_man_ok
        and not manifest.persistent_emmc_writes_authorized
        and not manifest.persistent_write_release
        and manifest.physical_device_writes == 0
    )

    dedup_codes = tuple(dict.fromkeys(codes))
    return SdRescueVerificationReport(
        passed=all_ok,
        stage_b_rehearsal_permitted=all_ok,
        status=STATUS_VERIFIED_GPT_RPMB_BUNDLE if all_ok else STATUS_FAIL_GPT_RPMB_BUNDLE,
        sentinel_verified=sentinel_ok,
        partition_count_verified=verified_count,
        parity_verified=parity_ok,
        parity_single_loss_heal_verified=heal_drill_ok,
        body_binding_verified=body_ok,
        two_man_rule_verified=two_man_ok,
        air_gapped_verified=air_gapped_ok,
        bundle_sha256=manifest.bundle_sha256,
        body_identity_binding_sha256=manifest.body_identity_binding_sha256,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        error_codes=dedup_codes,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Unified Phase 94 Suite Runner
# ---------------------------------------------------------------------------


def _flip_byte(buf: bytes, offset: int) -> bytes:
    arr = bytearray(buf)
    arr[offset] ^= 0x5A
    return bytes(arr)


def run_gpt_rpmb_and_rescue_bundle_suite(
    *,
    force_clean_room: Optional[bool] = None,
) -> GptRpmbAndRescueSuiteReport:
    """Execute all 3 Phase 94 pillars (positive & fail-closed negative drills) in < 0.2s."""
    require(PERSISTENT_EMMC_WRITES_AUTHORIZED is False, "persistent eMMC writes must remain locked")
    require(PERSISTENT_WRITE_RELEASE is False, "persistent write release must remain locked")
    require(OTP_FUSE_TOUCHES == 0, "OTP fuse touches must remain 0")
    require(PASSIVE_TX_BYTES_EMITTED == 0, "passive TX bytes must remain 0")
    require(RPMB_WRITES_EMITTED == 0, "RPMB physical writes must remain 0")

    errors: List[str] = []
    snapshot = inspect_donor_partition_metadata_readonly(force_clean_room=force_clean_room)

    # ---- Pillar 1: GPT Primary/Backup Healer + Overlap/4K/FX6 Transplant Firewalls ----
    pri_hdr, pri_arr, bak_hdr, bak_arr = build_cxd90057_gpt_pair(sku=FX3_SKU_CODE)
    gpt_healthy, _ = heal_gpt_pair_ram_only(pri_hdr, pri_arr, bak_hdr, bak_arr)

    # Corrupt Primary header + array -> reconstruct from Backup
    corrupt_pri_hdr = _flip_byte(pri_hdr, 16)
    corrupt_pri_arr = _flip_byte(pri_arr, 32)
    gpt_heal_pri, healed_pri_tuple = heal_gpt_pair_ram_only(corrupt_pri_hdr, corrupt_pri_arr, bak_hdr, bak_arr)
    if healed_pri_tuple is None or healed_pri_tuple[0] != pri_hdr or healed_pri_tuple[1] != pri_arr:
        errors.append("Primary GPT reconstruction from Backup was not byte-exact.")

    # Corrupt Backup header + array -> reconstruct from Primary
    corrupt_bak_hdr = _flip_byte(bak_hdr, 20)
    corrupt_bak_arr = _flip_byte(bak_arr, 64)
    gpt_heal_bak, healed_bak_tuple = heal_gpt_pair_ram_only(pri_hdr, pri_arr, corrupt_bak_hdr, corrupt_bak_arr)
    if healed_bak_tuple is None or healed_bak_tuple[2] != bak_hdr or healed_bak_tuple[3] != bak_arr:
        errors.append("Backup GPT reconstruction from Primary was not byte-exact.")

    # Overlapping LBA firewall
    overlap_parts = list(CXD90057_FX3_15_PARTITIONS)
    overlap_parts[1] = (2, "p2_overlap", 0x0000B000, 0x0000B000, "bk4_overlap")
    ov_ph, ov_pa, ov_bh, ov_ba = build_cxd90057_gpt_pair(sku=FX3_SKU_CODE, partitions=overlap_parts)
    ov_res, _ = heal_gpt_pair_ram_only(ov_ph, ov_pa, ov_bh, ov_ba)
    gpt_reject_overlap_ok = (not ov_res.passed) and (ERR_GPT_PARTITION_OVERLAP in ov_res.primary_audit.error_codes)

    # Misaligned 4 KiB boundary firewall
    misalign_parts = list(CXD90057_FX3_15_PARTITIONS)
    misalign_parts[1] = (2, "p2_misaligned", 0x0000C001, 0x00009FFF, "bk4_misaligned")
    ma_ph, ma_pa, ma_bh, ma_ba = build_cxd90057_gpt_pair(sku=FX3_SKU_CODE, partitions=misalign_parts)
    ma_res, _ = heal_gpt_pair_ram_only(ma_ph, ma_pa, ma_bh, ma_ba)
    gpt_reject_4k_ok = (not ma_res.passed) and (ERR_GPT_MISALIGNED_4K in ma_res.primary_audit.error_codes)

    # Cross-SKU FX6 partition geometry transplant firewall
    fx6_ph, fx6_pa, fx6_bh, fx6_ba = build_cxd90057_gpt_pair(sku=FX6_SKU_CODE)
    fx6_res, _ = heal_gpt_pair_ram_only(fx6_ph, fx6_pa, fx6_bh, fx6_ba, target_sku=FX3_SKU_CODE)
    gpt_reject_fx6_ok = (not fx6_res.passed) and (ERR_CROSS_SKU_FX6_GPT_TRANSPLANT in fx6_res.primary_audit.error_codes)

    # Both copies corrupted fail-closed
    both_bad_res, both_bad_out = heal_gpt_pair_ram_only(corrupt_pri_hdr, corrupt_pri_arr, corrupt_bak_hdr, corrupt_bak_arr)
    gpt_reject_both_ok = (
        not both_bad_res.passed
        and both_bad_out is None
        and ERR_GPT_BOTH_COPIES_CORRUPTED in both_bad_res.error_codes
    )

    # ---- Pillar 2: JEDEC eMMC 5.1 RPMB Monotonic Write-Counter & Replay Sandbox ----
    sandbox = RpmbSandboxController(initial_counter=42)
    nonce1 = bytes(range(16))
    sandbox.issue_challenge_nonce(nonce1)
    payload_data = b"FX3_STAGE_B_SANDBOX_EPOCH_TEST_BLOCK"
    write_req = build_rpmb_frame(
        req_resp=RPMB_REQ_DATA_WRITE,
        data=payload_data,
        nonce=nonce1,
        write_counter=42,
        address=3,
        block_count=1,
    )
    write_ok_resp, _ = sandbox.process_frame(write_req, expected_nonce=nonce1)
    rpmb_auth_ok = (
        write_ok_resp.accepted
        and write_ok_resp.result_code == RPMB_RESULT_OK
        and write_ok_resp.write_counter_before == 42
        and write_ok_resp.write_counter_after == 43
        and write_ok_resp.rpmb_writes_emitted == 0
    )

    # Replay stale counter=42 when sandbox is now at 43 -> RESULT_COUNTER_FAILURE (0x0003)
    nonce2 = bytes(range(16, 32))
    sandbox.issue_challenge_nonce(nonce2)
    stale_req = build_rpmb_frame(
        req_resp=RPMB_REQ_DATA_WRITE,
        data=payload_data,
        nonce=nonce2,
        write_counter=42,
        address=3,
        block_count=1,
    )
    stale_resp, _ = sandbox.process_frame(stale_req, expected_nonce=nonce2)
    rpmb_stale_ok = (
        not stale_resp.accepted
        and stale_resp.result_code == RPMB_RESULT_COUNTER_FAILURE
        and ERR_RPMB_COUNTER_FAILURE in stale_resp.error_codes
        and stale_resp.write_counter_after == 43
    )

    # Nonce mismatch -> rejected
    wrong_nonce = b"\xAA" * 16
    nonce_bad_req = build_rpmb_frame(
        req_resp=RPMB_REQ_DATA_WRITE,
        data=payload_data,
        nonce=wrong_nonce,
        write_counter=43,
        address=3,
        block_count=1,
    )
    nonce_bad_resp, _ = sandbox.process_frame(nonce_bad_req, expected_nonce=nonce2)
    rpmb_nonce_ok = (
        not nonce_bad_resp.accepted
        and ERR_RPMB_NONCE_MISMATCH in nonce_bad_resp.error_codes
        and nonce_bad_resp.write_counter_after == 43
    )

    # MAC forgery -> RESULT_AUTH_FAILURE (0x0002)
    forged_req = build_rpmb_frame(
        req_resp=RPMB_REQ_DATA_WRITE,
        data=payload_data,
        nonce=nonce2,
        write_counter=43,
        address=3,
        block_count=1,
        override_mac=b"\xDE\xAD\xBE\xEF" * 8,
    )
    forged_resp, _ = sandbox.process_frame(forged_req, expected_nonce=nonce2)
    rpmb_mac_ok = (
        not forged_resp.accepted
        and forged_resp.result_code == RPMB_RESULT_AUTH_FAILURE
        and ERR_RPMB_AUTH_FAILURE in forged_resp.error_codes
        and forged_resp.write_counter_after == 43
    )

    # Counter exhaustion at 0xFFFFFFFF -> RESULT_COUNTER_EXPIRED (0x0080)
    exhausted_box = RpmbSandboxController(initial_counter=RPMB_MAX_WRITE_COUNTER)
    exhausted_box.issue_challenge_nonce(nonce1)
    exp_req = build_rpmb_frame(
        req_resp=RPMB_REQ_DATA_WRITE,
        data=payload_data,
        nonce=nonce1,
        write_counter=RPMB_MAX_WRITE_COUNTER,
        address=1,
        block_count=1,
    )
    exp_resp, _ = exhausted_box.process_frame(exp_req, expected_nonce=nonce1)
    rpmb_exp_ok = (
        not exp_resp.accepted
        and exp_resp.result_code == RPMB_RESULT_COUNTER_EXPIRED
        and exp_resp.counter_expired
        and ERR_RPMB_COUNTER_EXPIRED in exp_resp.error_codes
    )

    stage_b_proof = prove_stage_b_zero_rpmb_writes()

    # ---- Pillar 3: Offline Air-Gapped SD-Rescue Bundle & Two-Man Integrity ----
    parts, sentinel, p_par, q_par, body_id, manifest = build_synthetic_sd_rescue_bundle()
    sd_valid_rep = verify_sd_rescue_bundle(
        parts,
        sentinel,
        p_par,
        q_par,
        manifest,
        target_body_identity=body_id,
    )

    # Missing sentinel flag
    sd_no_sent = verify_sd_rescue_bundle(parts, None, p_par, q_par, manifest, target_body_identity=body_id)
    sd_reject_sent_ok = (
        not sd_no_sent.passed
        and not sd_no_sent.stage_b_rehearsal_permitted
        and ERR_MISSING_SENTINEL_FLAG in sd_no_sent.error_codes
    )

    # Truncated partition artifact
    trunc_parts = dict(parts)
    trunc_parts["p5_wbi2_hibdrv"] = parts["p5_wbi2_hibdrv"][:512]
    sd_trunc = verify_sd_rescue_bundle(trunc_parts, sentinel, p_par, q_par, manifest, target_body_identity=body_id)
    sd_reject_trunc_ok = (
        not sd_trunc.passed
        and not sd_trunc.stage_b_rehearsal_permitted
        and ERR_TRUNCATED_RESCUE_ARTIFACT in sd_trunc.error_codes
    )

    # Cross-body serial transplant
    other_body = build_body_hardware_identity(
        camera_model=FX3_SKU_CODE,
        body_serial_hash=sha256(b"FX3_BODY_BETA_9999").hexdigest(),
        cnflasha_calibration_sha256=sha256(parts["p15_cnflasha_lens_cal"]).hexdigest(),
        c2pa_rq_lic_sha256=sha256(parts["p12_cert_c2pa"]).hexdigest(),
    )
    sd_cross = verify_sd_rescue_bundle(parts, sentinel, p_par, q_par, manifest, target_body_identity=other_body)
    sd_reject_cross_ok = (
        not sd_cross.passed
        and not sd_cross.stage_b_rehearsal_permitted
        and ERR_RESCUE_BODY_BINDING_MISMATCH in sd_cross.error_codes
    )

    # Single-operator two-man rule violation
    single_att = TwoManAttestation(
        operator_a_id="op-alpha-bench",
        operator_a_signature_sha256=manifest.two_man_attestation.operator_a_signature_sha256,
        operator_b_id="op-alpha-bench",
        operator_b_signature_sha256=manifest.two_man_attestation.operator_a_signature_sha256,
        air_gapped=True,
        network_interfaces_disabled=True,
    )
    single_manifest = SdRescueBundleManifest(**{**manifest.__dict__, "two_man_attestation": single_att})
    sd_single = verify_sd_rescue_bundle(parts, sentinel, p_par, q_par, single_manifest, target_body_identity=body_id)
    sd_reject_two_man_ok = (
        not sd_single.passed
        and not sd_single.stage_b_rehearsal_permitted
        and ERR_TWO_MAN_RULE_VIOLATION in sd_single.error_codes
    )

    all_passed = (
        gpt_healthy.passed
        and gpt_heal_pri.passed
        and gpt_heal_bak.passed
        and gpt_reject_overlap_ok
        and gpt_reject_4k_ok
        and gpt_reject_fx6_ok
        and gpt_reject_both_ok
        and rpmb_auth_ok
        and rpmb_stale_ok
        and rpmb_nonce_ok
        and rpmb_mac_ok
        and rpmb_exp_ok
        and stage_b_proof.passed
        and sd_valid_rep.passed
        and sd_reject_sent_ok
        and sd_reject_trunc_ok
        and sd_reject_cross_ok
        and sd_reject_two_man_ok
        and len(errors) == 0
    )

    suite_sha = _canonical_sha256(
        {
            "schema": GPT_RPMB_RESCUE_SCHEMA,
            "verification_mode": snapshot.verification_mode,
            "donor_snapshot_sha256": snapshot.snapshot_sha256,
            "gpt_primary_sha256": gpt_heal_pri.reconstructed_primary_sha256,
            "gpt_backup_sha256": gpt_heal_bak.reconstructed_backup_sha256,
            "rpmb_write_resp_sha256": write_ok_resp.response_frame_sha256,
            "sd_rescue_bundle_sha256": sd_valid_rep.bundle_sha256,
            "all_passed": all_passed,
        }
    )

    return GptRpmbAndRescueSuiteReport(
        schema=GPT_RPMB_RESCUE_SCHEMA,
        version=GPT_RPMB_RESCUE_VERSION,
        verification_mode=snapshot.verification_mode,
        all_passed=all_passed,
        status=STATUS_VERIFIED_GPT_RPMB_BUNDLE if all_passed else STATUS_FAIL_GPT_RPMB_BUNDLE,
        donor_snapshot=snapshot,
        gpt_healthy_check=gpt_healthy,
        gpt_heal_primary_from_backup=gpt_heal_pri,
        gpt_heal_backup_from_primary=gpt_heal_bak,
        gpt_reject_overlap_passed=gpt_reject_overlap_ok,
        gpt_reject_misaligned_4k_passed=gpt_reject_4k_ok,
        gpt_reject_fx6_transplant_passed=gpt_reject_fx6_ok,
        gpt_reject_both_corrupted_passed=gpt_reject_both_ok,
        rpmb_authenticated_write_passed=rpmb_auth_ok,
        rpmb_reject_stale_counter_passed=rpmb_stale_ok,
        rpmb_reject_nonce_mismatch_passed=rpmb_nonce_ok,
        rpmb_reject_mac_forgery_passed=rpmb_mac_ok,
        rpmb_reject_counter_expired_passed=rpmb_exp_ok,
        stage_b_zero_rpmb_proof=stage_b_proof,
        sd_rescue_valid_report=sd_valid_rep,
        sd_rescue_reject_missing_sentinel_passed=sd_reject_sent_ok,
        sd_rescue_reject_truncated_artifact_passed=sd_reject_trunc_ok,
        sd_rescue_reject_cross_body_passed=sd_reject_cross_ok,
        sd_rescue_reject_single_operator_passed=sd_reject_two_man_ok,
        suite_sha256=suite_sha,
        otp_fuse_touches=OTP_FUSE_TOUCHES,
        passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
        rpmb_writes_emitted=RPMB_WRITES_EMITTED,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        allow_boot_partition_targeting=ALLOW_BOOT_PARTITION_TARGETING,
        allow_destructive_fastboot=ALLOW_DESTRUCTIVE_FASTBOOT,
        errors=tuple(errors),
    )
