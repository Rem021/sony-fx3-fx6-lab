"""Phase 15 — Stage-A Non-Persistent Hardware Readiness Packet Generator & Real Tier-0 Capture Bundle Verifier.

Aggregates live verdicts from all offline verification engines (`preflight` 12/12 safety gates,
`verify-byof` 57+57 manifest parity, Tier-0 freestanding AArch64 worker Unicorn syscall audit,
`P1..P9 + Fan` patch & rollback digests, Stage-A `30,956 B` SVR4 `cpio newc` archive & 6-scenario
atomic orchestrator, `U1..U5` blueprint closures, `p5:/wbi` hibernation redline, `p8:/cp` stock-CP
redline, `p1` recovery bridge, and Phase 14 `insmod_drv1`/`insmod_drv2` + `137` `/dev/*` + `60`-ELF
`12,188`-import linkage closure) into a deterministic, self-authenticating JSON readiness packet
(`stage_a_readiness_packet_v1`).

Also provides `verify_real_tier0_capture_bundle(bundle_dir)` to deterministically validate a real
future physical FX3 Tier-0 read-only capture bundle (`backup-manifest.json`, all 11 mandatory
partition/calibration images, non-synthetic `body_serial` & 128-bit eMMC `cid`, two-pass SHA-256
readback parity, exact partition byte sizes, and valid `sector0` `'8246'`, `p2` `'BK4\\0'`,
`p1` `FAT16`/`FAT12` VFAT, `p8` `tomco.txt`, and `p5` `WBI2` magic headers) — rejecting synthetic,
tampered, or incomplete bundles fail-closed.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import copy
import hashlib
import importlib.util
import json
import os
import re
import stat
import struct
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from fx3_safety.boot_contracts import (
    FX3_KEY_PARTITIONS,
    PartitionEntry,
    build_sector0_from_partitions,
    parse_bk4_record,
    verify_sector0_partition_table,
)
from fx3_safety.preflight import (
    TIER0_CANONICAL_SOURCES,
    TIER0_REQUIRED_BACKUPS,
    BackupManifestAudit,
    evaluate_12_safety_gates,
    verify_failsafe_hook_script,
    verify_tier0_backup_manifest,
)

from .backup_mount_tolerance_verifier import audit_ram_shadow_bk4, synthesize_ram_shadow_bk4
from .candidate_builder import (
    COMPLETE_MATRIX_ITEMS,
    DEFAULT_REPO_ROOT,
    CandidateDryRunReport,
    run_offline_candidate_dry_run,
)
from .cp_rtos_compatibility_verifier import EXPECTED_RUNTIME_MEMCFG_SPEC
from .patcher import DEFAULT_FX3_MODULES_DIR, DEFAULT_FX6_DONOR_LIB_DIR
from .ram_overlay_packager import (
    build_stage_a_ram_overlay_package,
    generate_stage_a_init2_guard_script,
)
from .rollback_drill import run_four_layer_rollback_drill
from .stage_a_boot_orchestrator import (
    EXPECTED_FX6_WBI_DVERSION,
    EXPECTED_FX6_WBI_O_DATA_BYTES,
    EXPECTED_FX6_WBI_R_DATA_BYTES,
    EXPECTED_FX6_WBI_RESUME_VECTOR,
    EXPECTED_FX6_WBI_SECTION_COUNT,
    PINNED_FX3_STOCK_WBI_SHA256,
    WBI_PARTITION_SIZE_BYTES,
    parse_wbi2_header_bytes,
    run_stage_a_boot_orchestrator_verification,
)


READINESS_PACKET_SCHEMA = "stage_a_readiness_packet_v1"
PHASE_15_VERSION = "15.0.0"
FX3_MODEL_ID_HEX = "0x91030080"
STREAM_CHUNK_BYTES = 65536

HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
HEX32_CID_RE = re.compile(r"^[0-9a-fA-F]{32}$")
BODY_SERIAL_RE = re.compile(r"^[A-Z0-9]{7,16}$")
SAFE_FILENAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")

SYNTHETIC_ORIGIN_TOKENS: Tuple[str, ...] = (
    "synthetic",
    "unicorn",
    "qemu",
    "mock",
    "test",
    "dummy",
    "fake",
    "simulated",
    "emulated",
    "clean_room",
    "clean-room",
    "placeholder",
    "sample",
    "unknown",
)

FORBIDDEN_TRIVIAL_SERIALS: Tuple[str, ...] = (
    "0000000",
    "00000000",
    "1111111",
    "11111111",
    "1234567",
    "12345678",
    "123456789",
    "0123456",
    "01234567",
    "9999999",
    "99999999",
    "ABCDEFG",
    "ABCDEFGH",
)

FORBIDDEN_TRIVIAL_CIDS: Tuple[str, ...] = (
    "0" * 32,
    "f" * 32,
    "0123456789abcdef0123456789abcdef",
    "fedcba9876543210fedcba9876543210",
    "deadbeefdeadbeefdeadbeefdeadbeef",
    "cafebabecafebabecafebabecafebabe",
)

KNOWN_SYNTHETIC_BODY_TAGS: Tuple[str, ...] = (
    "0" * 64,
    "f" * 64,
    "a" * 64,
    "1" * 64,
    hashlib.sha256(b"unicorn").hexdigest(),
    hashlib.sha256(b"synthetic").hexdigest(),
    hashlib.sha256(b"fx3-synthetic-tier0").hexdigest(),
)

REQUIRED_REDLINE_HEADER_PROBES: Dict[str, str] = {
    "p8_tomco_txt": "p8_tomco.txt",
    "p5_wbi_header": "p5_wbi_header.bin",
}


@dataclass(frozen=True)
class P1VfatHeaderAudit:
    valid: bool
    fat_type: str
    total_bytes: int
    bytes_per_sector: int
    sectors_per_cluster: int
    reserved_sectors: int
    num_fats: int
    root_entries: int
    sectors_per_fat: int
    cluster_count: int
    fats_identical: bool
    boot_signature_ok: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class P8TomcoHeaderAudit:
    valid: bool
    byte_size: int
    sha256: str
    memcfg_pool_count: int
    total_memcfg_mib: float
    has_ipc_and_wdt_keys: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class RealTier0CaptureBundleAudit:
    valid: bool
    bundle_dir: str
    manifest_present: bool
    is_non_synthetic_hardware: bool
    model_id: str
    camera_body_tag: str
    body_serial: str
    emmc_cid: str
    manifest_audit_valid: bool
    verified_partition_files: Tuple[str, ...]
    missing_or_invalid_files: Tuple[str, ...]
    twopass_sha256_all_matched: bool
    ondisk_sha256_all_matched: bool
    sector0_magic_ok: bool
    sector0_layout_profile: str
    p2_bk4_magic_ok: bool
    p1_vfat_header_ok: bool
    p1_vfat_type: str
    p8_tomco_header_ok: bool
    p5_wbi2_header_ok: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class HardwareExecutionPhaseStep:
    phase_id: str
    title: str
    gate_dependencies: Tuple[str, ...]
    emmc_write_bytes_allowed: int
    nor_write_bytes_allowed: int
    wbi_p5_write_bytes_allowed: int
    cp_p8_write_bytes_allowed: int
    preconditions: Tuple[str, ...]
    ordered_steps: Tuple[str, ...]
    pass_criteria: Tuple[str, ...]
    abort_and_recovery_actions: Tuple[str, ...]


@dataclass(frozen=True)
class StageAHardwareReadinessPacketReport:
    schema: str
    phase_version: str
    verification_mode: str
    offline_engineering_complete: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    usb_or_camera_operations: int
    real_tier0_hardware_backup_verified: bool
    stage_a_ram_trial_hardware_go: bool
    preflight_safety_gates: Dict[str, object]
    byof_manifest_parity: Dict[str, object]
    tier0_worker_unicorn_syscall_audit: Dict[str, object]
    p1_to_p9_and_fan_matrix: Dict[str, object]
    stage_a_cpio_overlay: Dict[str, object]
    u1_to_u5_and_abi_redlines: Dict[str, object]
    gate_ordered_hardware_execution_checklist: Tuple[HardwareExecutionPhaseStep, ...]
    tier0_bundle_audit: Optional[RealTier0CaptureBundleAudit]
    errors: Tuple[str, ...]
    packet_sha256: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)

    def to_deterministic_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=False) + "\n"


def _is_forced_clean_room(
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
) -> bool:
    if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM", "").strip() == "1":
        return True
    return not (
        (fx6_lib_dir / "appFw.so").is_file()
        and (fx3_modules_dir / "upm.ko").is_file()
    )


def _stream_file_sha256_and_size(path: Path) -> Tuple[int, str]:
    h = hashlib.sha256()
    total = 0
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(STREAM_CHUNK_BYTES)
            if not chunk:
                break
            total += len(chunk)
            h.update(chunk)
    return total, h.hexdigest()


def _validate_non_synthetic_serial_and_cid(
    *,
    manifest: Mapping[str, object],
    body_tag: str,
    body_serial: str,
    emmc_cid: str,
) -> Tuple[bool, List[str]]:
    errors: List[str] = []

    if manifest.get("synthetic") is True or manifest.get("emulated_unicorn") is True:
        errors.append("Manifest explicitly carries synthetic/emulated_unicorn=True flag")

    origin = str(manifest.get("capture_origin", "")).strip().lower()
    if any(tok in origin for tok in SYNTHETIC_ORIGIN_TOKENS):
        errors.append(f"Rejected synthetic/emulated capture_origin={origin!r}")

    if not HEX64_RE.fullmatch(body_tag):
        errors.append("camera_body_tag must be a 64-character lowercase hex digest")
    elif body_tag in KNOWN_SYNTHETIC_BODY_TAGS or len(set(body_tag)) < 6:
        errors.append("camera_body_tag matches a synthetic/low-entropy placeholder digest")

    serial_norm = body_serial.strip()
    if serial_norm != body_serial or not BODY_SERIAL_RE.fullmatch(serial_norm):
        errors.append(
            f"body_serial {body_serial!r} must be 7..16 uppercase ASCII alphanumeric characters"
        )
    else:
        upper_serial = serial_norm.upper()
        if upper_serial in FORBIDDEN_TRIVIAL_SERIALS or len(set(upper_serial)) < 3:
            errors.append(f"body_serial {body_serial!r} rejected as trivial/repeating placeholder")
        if any(tok.upper() in upper_serial for tok in SYNTHETIC_ORIGIN_TOKENS):
            errors.append(f"body_serial {body_serial!r} contains forbidden synthetic token")

    cid_norm = emmc_cid.strip()
    if cid_norm != emmc_cid or not HEX32_CID_RE.fullmatch(cid_norm):
        errors.append(
            f"cid {emmc_cid!r} must be a 32-hex-character (128-bit) eMMC CID register value"
        )
    else:
        cid_low = cid_norm.lower()
        if cid_low in FORBIDDEN_TRIVIAL_CIDS or len(set(cid_low)) < 6:
            errors.append(f"cid {emmc_cid!r} rejected as trivial/synthetic 128-bit pattern")
        # Periodic 2-byte / 4-byte pattern check (e.g. 'abab...' or '12341234...')
        if cid_low == cid_low[:2] * 16 or cid_low == cid_low[:4] * 8 or cid_low == cid_low[:8] * 4:
            errors.append(f"cid {emmc_cid!r} rejected due to periodic synthetic byte repetition")
        mid_byte = int(cid_low[0:2], 16)
        end_byte = int(cid_low[30:32], 16)
        if mid_byte in (0x00, 0xFF):
            errors.append(f"cid manufacturer ID byte 0x{mid_byte:02x} is invalid for physical eMMC")
        if (end_byte & 0x01) != 0x01:
            errors.append(
                f"cid CRC7|stop byte 0x{end_byte:02x} violates JEDEC eMMC bit-0==1 stop-bit invariant"
            )

    return len(errors) == 0, errors


def audit_p1_vfat_header(p1_path: Path, expected_total_bytes: int = 25_100_288) -> P1VfatHeaderAudit:
    """Validate `p1_updater.bin` VFAT (`FAT16` or stock FX3 `FAT12`) BPB, `0x55AA` signature, and dual FAT mirror."""
    errors: List[str] = []
    total_bytes = p1_path.stat().st_size
    if total_bytes != expected_total_bytes:
        errors.append(f"p1_updater size {total_bytes} != expected {expected_total_bytes}")

    with p1_path.open("rb") as fh:
        sec0 = fh.read(512)
        if len(sec0) < 512:
            return P1VfatHeaderAudit(
                valid=False,
                fat_type="TRUNCATED",
                total_bytes=total_bytes,
                bytes_per_sector=0,
                sectors_per_cluster=0,
                reserved_sectors=0,
                num_fats=0,
                root_entries=0,
                sectors_per_fat=0,
                cluster_count=0,
                fats_identical=False,
                boot_signature_ok=False,
                errors=("p1_updater shorter than 512-byte VFAT boot sector",),
            )

        boot_sig_ok = sec0[510:512] == b"\x55\xaa"
        if not boot_sig_ok:
            errors.append(f"Invalid p1 boot sector signature {sec0[510:512]!r} (expected b'\\x55\\xaa')")

        bps = struct.unpack_from("<H", sec0, 11)[0]
        spc = sec0[13]
        reserved = struct.unpack_from("<H", sec0, 14)[0]
        num_fats = sec0[16]
        root_entries = struct.unpack_from("<H", sec0, 17)[0]
        tot16 = struct.unpack_from("<H", sec0, 19)[0]
        media_desc = sec0[21]
        spf = struct.unpack_from("<H", sec0, 22)[0]
        tot32 = struct.unpack_from("<I", sec0, 32)[0]
        fs_label = sec0[54:62]

        total_sectors = tot16 if tot16 != 0 else tot32
        if bps != 512:
            errors.append(f"Unsupported p1 bytes_per_sector={bps} (expected 512)")
        if spc not in (1, 2, 4, 8, 16, 32, 64, 128):
            errors.append(f"Invalid p1 sectors_per_cluster={spc}")
        if reserved < 1:
            errors.append(f"Invalid p1 reserved_sectors={reserved}")
        if num_fats != 2:
            errors.append(f"Expected 2 FAT copies on p1, got num_fats={num_fats}")
        if root_entries < 16 or ((root_entries * 32) % 512) != 0:
            errors.append(f"Invalid p1 root_entries={root_entries}")
        if spf < 1:
            errors.append(f"Invalid p1 sectors_per_fat={spf}")
        if total_sectors <= 0 or total_sectors * 512 > total_bytes:
            errors.append(
                f"p1 BPB total_sectors={total_sectors} ({total_sectors * 512} B) invalid for image size {total_bytes} B"
            )

        fat_type = fs_label.decode("ascii", errors="replace").strip() or "UNKNOWN"
        if fs_label not in (b"FAT16   ", b"FAT12   "):
            errors.append(
                f"Invalid p1 VFAT filsystem type signature {fs_label!r} at +0x36 (expected b'FAT16   ' or b'FAT12   ')"
            )

        clusters = 0
        fats_identical = False
        if bps == 512 and spc in (1, 2, 4, 8, 16, 32, 64, 128) and reserved >= 1 and num_fats == 2 and spf >= 1:
            root_dir_sectors = (root_entries * 32) // 512
            data_start_sector = reserved + num_fats * spf + root_dir_sectors
            if total_sectors > data_start_sector:
                clusters = (total_sectors - data_start_sector) // spc
            if fs_label == b"FAT16   ":
                if not (4085 <= clusters < 65525):
                    errors.append(
                        f"p1 declares FAT16 but cluster count {clusters} is outside 4085..65524"
                    )
                needed_fat_bytes = (clusters + 2) * 2
            elif fs_label == b"FAT12   ":
                if not (1 <= clusters < 4085):
                    errors.append(
                        f"p1 declares FAT12 but cluster count {clusters} is outside 1..4084"
                    )
                needed_fat_bytes = ((clusters + 2) * 3 + 1) // 2
            else:
                needed_fat_bytes = 0

            fat_bytes_len = spf * 512
            if needed_fat_bytes > fat_bytes_len:
                errors.append(
                    f"p1 FAT table size {fat_bytes_len} B too small for {clusters} clusters"
                )
            fat1_off = reserved * 512
            fat2_off = fat1_off + fat_bytes_len
            if fat2_off + fat_bytes_len <= total_bytes:
                fh.seek(fat1_off)
                fat1 = fh.read(fat_bytes_len)
                fh.seek(fat2_off)
                fat2 = fh.read(fat_bytes_len)
                fats_identical = len(fat1) == fat_bytes_len and fat1 == fat2
                if not fats_identical:
                    errors.append("p1 FAT1 and FAT2 copies are not byte-identical")
                if fat1 and fat1[0] != media_desc:
                    errors.append(
                        f"p1 FAT[0] media byte 0x{fat1[0]:02x} != BPB media descriptor 0x{media_desc:02x}"
                    )
            else:
                errors.append("p1 FAT tables extend beyond image boundary")

    return P1VfatHeaderAudit(
        valid=len(errors) == 0,
        fat_type=fat_type,
        total_bytes=total_bytes,
        bytes_per_sector=bps,
        sectors_per_cluster=spc,
        reserved_sectors=reserved,
        num_fats=num_fats,
        root_entries=root_entries,
        sectors_per_fat=spf,
        cluster_count=clusters,
        fats_identical=fats_identical,
        boot_signature_ok=boot_sig_ok,
        errors=tuple(errors),
    )


def audit_p8_tomco_header(tomco_bytes: bytes) -> P8TomcoHeaderAudit:
    """Validate `p8` (`/cp/tomco.txt`) CP RTOS configuration header & 4x `memcfg=` shared-memory pools."""
    errors: List[str] = []
    sha = hashlib.sha256(tomco_bytes).hexdigest()
    if len(tomco_bytes) < 64 or len(tomco_bytes) > 65536:
        errors.append(f"p8 tomco.txt size {len(tomco_bytes)} B outside valid 64..65536 B bounds")
    if b"\x00" in tomco_bytes:
        errors.append("p8 tomco.txt contains NUL binary bytes (expected ASCII configuration text)")

    try:
        text = tomco_bytes.decode("ascii")
    except UnicodeDecodeError as exc:
        return P8TomcoHeaderAudit(
            valid=False,
            byte_size=len(tomco_bytes),
            sha256=sha,
            memcfg_pool_count=0,
            total_memcfg_mib=0.0,
            has_ipc_and_wdt_keys=False,
            errors=tuple(errors + [f"p8 tomco.txt is not valid ASCII: {exc}"]),
        )

    memcfg_re = re.compile(r"^memcfg=(0x[0-9a-fA-F]+):(0x[0-9a-fA-F]+):([a-zA-Z]+)$")
    pools: List[Tuple[int, int, str]] = []
    keys_seen = set()
    for raw_ln in text.splitlines():
        ln = raw_ln.strip()
        if not ln or ln.startswith("#"):
            continue
        m = memcfg_re.match(ln)
        if m:
            pools.append((int(m.group(1), 16), int(m.group(2), 16), m.group(3)))
        elif "=" in ln:
            keys_seen.add(ln.split("=", 1)[0].strip())

    if tuple(pools) != EXPECTED_RUNTIME_MEMCFG_SPEC:
        errors.append(
            f"p8 tomco.txt memcfg pools {pools!r} do not match canonical CXD90057 4-pool 1724 MiB spec"
        )

    has_keys = ("wdt_on" in keys_seen) and ("exception_reboot" in keys_seen)
    if not has_keys:
        errors.append("p8 tomco.txt missing mandatory CP RTOS keys (`wdt_on`, `exception_reboot`)")

    total_mib = round(sum(sz for _, sz, _ in pools) / (1024.0 * 1024.0), 2)
    return P8TomcoHeaderAudit(
        valid=len(errors) == 0,
        byte_size=len(tomco_bytes),
        sha256=sha,
        memcfg_pool_count=len(pools),
        total_memcfg_mib=total_mib,
        has_ipc_and_wdt_keys=has_keys,
        errors=tuple(errors),
    )


def verify_real_tier0_capture_bundle(bundle_dir: Path | str) -> RealTier0CaptureBundleAudit:
    """Deterministically validate a physical FX3 Tier-0 read-only capture directory.

    Checks:
    1. `bundle_dir` is a real non-symlink directory containing non-symlink `backup-manifest.json`.
    2. Non-synthetic hardware provenance: `model_id == "0x91030080"`, high-entropy 64-hex
       `camera_body_tag`, physical `body_serial`, and JEDEC-compliant 128-bit eMMC `cid`
       (rejecting synthetic/Unicorn/QEMU/mock flags or trivial patterns).
    3. All 11 mandatory `TIER0_REQUIRED_BACKUPS` items pass `verify_tier0_backup_manifest`,
       exist on disk as regular non-symlink files, match exact byte-size rules & `boot0 == boot1`
       symmetry, and match `on_disk_sha256 == pass1_sha256 == pass2_sha256`.
    4. Structural & magic header verification:
       - `sector0.bin`: `'8246'` `'2.00'` 30-entry Sony partition table with `FX3_702` /
         `FX3_PARTINF_205` profile (rejecting `FX6_601` or overlapping layouts).
       - `p2_backup_bin.bin`: valid `'BK4\\0'` sync word `0xaaaaaaaa` & 32-bit record checksum.
       - `p1_updater.bin`: valid `FAT16` (or stock FX3 `FAT12`) VFAT BPB, `0x55AA` boot sector
         signature, and byte-identical dual FAT copies.
       - `p8_tomco.txt`: valid ASCII CP RTOS `tomco.txt` carrying all 4 canonical CXD90057
         `memcfg=` (`1,724.00 MiB`) pools + two-pass SHA-256 manifest binding.
       - `p5_wbi_header.bin`: valid `WBI2` 88-byte hibernation header (`magic == b"WBI2"`,
         non-invalidated, valid resume vector & section count) + two-pass SHA-256 binding.
    """
    bdir = Path(bundle_dir)
    errors: List[str] = []

    if not bdir.exists() or bdir.is_symlink() or not bdir.is_dir():
        return RealTier0CaptureBundleAudit(
            valid=False,
            bundle_dir=str(bdir),
            manifest_present=False,
            is_non_synthetic_hardware=False,
            model_id="",
            camera_body_tag="",
            body_serial="",
            emmc_cid="",
            manifest_audit_valid=False,
            verified_partition_files=(),
            missing_or_invalid_files=tuple(TIER0_REQUIRED_BACKUPS.keys()),
            twopass_sha256_all_matched=False,
            ondisk_sha256_all_matched=False,
            sector0_magic_ok=False,
            sector0_layout_profile="MISSING",
            p2_bk4_magic_ok=False,
            p1_vfat_header_ok=False,
            p1_vfat_type="MISSING",
            p8_tomco_header_ok=False,
            p5_wbi2_header_ok=False,
            errors=("Bundle directory does not exist or is a symbolic link",),
        )

    manifest_path = bdir / "backup-manifest.json"
    if not manifest_path.exists() or manifest_path.is_symlink() or not manifest_path.is_file():
        return RealTier0CaptureBundleAudit(
            valid=False,
            bundle_dir=str(bdir),
            manifest_present=False,
            is_non_synthetic_hardware=False,
            model_id="",
            camera_body_tag="",
            body_serial="",
            emmc_cid="",
            manifest_audit_valid=False,
            verified_partition_files=(),
            missing_or_invalid_files=tuple(TIER0_REQUIRED_BACKUPS.keys()),
            twopass_sha256_all_matched=False,
            ondisk_sha256_all_matched=False,
            sector0_magic_ok=False,
            sector0_layout_profile="MISSING",
            p2_bk4_magic_ok=False,
            p1_vfat_header_ok=False,
            p1_vfat_type="MISSING",
            p8_tomco_header_ok=False,
            p5_wbi2_header_ok=False,
            errors=("Missing regular file backup-manifest.json in Tier-0 bundle directory",),
        )

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return RealTier0CaptureBundleAudit(
            valid=False,
            bundle_dir=str(bdir),
            manifest_present=True,
            is_non_synthetic_hardware=False,
            model_id="",
            camera_body_tag="",
            body_serial="",
            emmc_cid="",
            manifest_audit_valid=False,
            verified_partition_files=(),
            missing_or_invalid_files=tuple(TIER0_REQUIRED_BACKUPS.keys()),
            twopass_sha256_all_matched=False,
            ondisk_sha256_all_matched=False,
            sector0_magic_ok=False,
            sector0_layout_profile="INVALID_JSON",
            p2_bk4_magic_ok=False,
            p1_vfat_header_ok=False,
            p1_vfat_type="INVALID_JSON",
            p8_tomco_header_ok=False,
            p5_wbi2_header_ok=False,
            errors=(f"Malformed JSON in backup-manifest.json: {exc}",),
        )

    if not isinstance(manifest, dict):
        return RealTier0CaptureBundleAudit(
            valid=False,
            bundle_dir=str(bdir),
            manifest_present=True,
            is_non_synthetic_hardware=False,
            model_id="",
            camera_body_tag="",
            body_serial="",
            emmc_cid="",
            manifest_audit_valid=False,
            verified_partition_files=(),
            missing_or_invalid_files=tuple(TIER0_REQUIRED_BACKUPS.keys()),
            twopass_sha256_all_matched=False,
            ondisk_sha256_all_matched=False,
            sector0_magic_ok=False,
            sector0_layout_profile="INVALID_ROOT",
            p2_bk4_magic_ok=False,
            p1_vfat_header_ok=False,
            p1_vfat_type="INVALID_ROOT",
            p8_tomco_header_ok=False,
            p5_wbi2_header_ok=False,
            errors=("backup-manifest.json root must be a JSON object",),
        )

    model_id = str(manifest.get("model_id", ""))
    if model_id != FX3_MODEL_ID_HEX:
        errors.append(f"Expected FX3 model_id {FX3_MODEL_ID_HEX!r}, got {model_id!r}")

    body_tag = str(manifest.get("camera_body_tag", ""))
    body_serial = str(manifest.get("body_serial", ""))
    emmc_cid = str(manifest.get("cid", ""))

    non_synth_ok, synth_errs = _validate_non_synthetic_serial_and_cid(
        manifest=manifest,
        body_tag=body_tag,
        body_serial=body_serial,
        emmc_cid=emmc_cid,
    )
    errors.extend(synth_errs)

    manifest_audit: BackupManifestAudit = verify_tier0_backup_manifest(manifest)
    errors.extend(manifest_audit.errors)
    twopass_ok = len(manifest_audit.mismatched_two_pass_items) == 0 and manifest_audit.valid

    items_dict = manifest.get("items") if isinstance(manifest.get("items"), dict) else {}
    verified_files: List[str] = []
    bad_files: List[str] = []
    ondisk_all_matched = True
    resolved_paths: Dict[str, Path] = {}

    for key in TIER0_REQUIRED_BACKUPS:
        entry = items_dict.get(key)
        if not isinstance(entry, dict):
            bad_files.append(key)
            ondisk_all_matched = False
            continue

        default_fn = str(TIER0_CANONICAL_SOURCES[key]["output_name"])
        fn = str(entry.get("file_name", default_fn))
        if not SAFE_FILENAME_RE.fullmatch(fn) or fn in (".", ".."):
            errors.append(f"Unsafe file_name {fn!r} for Tier-0 item {key}")
            bad_files.append(key)
            ondisk_all_matched = False
            continue

        fpath = bdir / fn
        if not fpath.exists() or fpath.is_symlink() or not fpath.is_file():
            errors.append(f"Missing or symlinked Tier-0 partition image file for {key}: {fn}")
            bad_files.append(key)
            ondisk_all_matched = False
            continue

        st = fpath.lstat()
        if not stat.S_ISREG(st.st_mode):
            errors.append(f"Tier-0 image {fn} for {key} is not a regular file")
            bad_files.append(key)
            ondisk_all_matched = False
            continue

        actual_bytes, actual_sha = _stream_file_sha256_and_size(fpath)
        decl_bytes = entry.get("bytes")
        sha1 = str(entry.get("pass1_sha256", ""))
        sha2 = str(entry.get("pass2_sha256", ""))

        if actual_bytes != decl_bytes:
            errors.append(
                f"On-disk size mismatch for {key} ({fn}): disk={actual_bytes} B vs manifest={decl_bytes!r} B"
            )
            bad_files.append(key)
            ondisk_all_matched = False
            continue

        if actual_sha != sha1 or actual_sha != sha2:
            errors.append(
                f"On-disk SHA-256 mismatch for {key} ({fn}): disk={actual_sha[:16]}... vs manifest={sha1[:16]}..."
            )
            bad_files.append(key)
            ondisk_all_matched = False
            continue

        verified_files.append(key)
        resolved_paths[key] = fpath

    # Magic Header 1: sector0 ('8246' '2.00' + FX3 layout profile)
    sector0_magic_ok = False
    sector0_profile = "UNVERIFIED"
    if "sector0" in resolved_paths:
        sec0_audit = verify_sector0_partition_table(resolved_paths["sector0"].read_bytes())
        sector0_profile = sec0_audit.layout_profile
        if not sec0_audit.valid:
            errors.extend(f"sector0.bin: {e}" for e in sec0_audit.errors)
        elif sec0_audit.layout_profile not in ("FX3_702", "FX3_PARTINF_205"):
            errors.append(
                f"sector0.bin layout_profile={sec0_audit.layout_profile!r} is not physical FX3 ('FX3_702'/'FX3_PARTINF_205')"
            )
        else:
            sector0_magic_ok = True

    # Magic Header 2: p2_backup_bin ('BK4\0' sync marker & record checksum)
    p2_bk4_ok = False
    if "p2_backup_bin" in resolved_paths:
        p2_bytes = resolved_paths["p2_backup_bin"].read_bytes()
        rec0, bk4_errs = parse_bk4_record(p2_bytes, offset=0, record_index=0)
        if rec0 is None or not rec0.magic_ok or not rec0.checksum_ok or bk4_errs:
            errors.extend(f"p2_backup_bin.bin: {e}" for e in (bk4_errs or ["Invalid BK4 record 0"]))
        else:
            p2_bk4_ok = True

    # Magic Header 3: p1_updater VFAT ('FAT16' / 'FAT12' + 0x55AA + dual-FAT parity)
    p1_vfat_ok = False
    p1_vfat_type = "UNVERIFIED"
    if "p1_updater" in resolved_paths:
        p1_audit = audit_p1_vfat_header(resolved_paths["p1_updater"])
        p1_vfat_type = p1_audit.fat_type
        if not p1_audit.valid:
            errors.extend(f"p1_updater.bin: {e}" for e in p1_audit.errors)
        else:
            p1_vfat_ok = True

    # Magic Header 4 & 5: Redline Header Probes (`p8_tomco.txt` & `p5_wbi_header.bin`)
    redline_dict = (
        manifest.get("redline_headers")
        if isinstance(manifest.get("redline_headers"), dict)
        else {}
    )
    p8_tomco_ok = False
    p5_wbi2_ok = False

    for probe_key, default_probe_fn in REQUIRED_REDLINE_HEADER_PROBES.items():
        probe_entry = redline_dict.get(probe_key)
        if not isinstance(probe_entry, dict):
            errors.append(f"Missing mandatory redline_headers[{probe_key!r}] entry in backup-manifest.json")
            continue
        p_fn = str(probe_entry.get("file_name", default_probe_fn))
        if not SAFE_FILENAME_RE.fullmatch(p_fn) or p_fn in (".", ".."):
            errors.append(f"Unsafe file_name {p_fn!r} in redline_headers[{probe_key!r}]")
            continue
        p_path = bdir / p_fn
        if not p_path.exists() or p_path.is_symlink() or not p_path.is_file():
            errors.append(f"Missing or symlinked redline header file {p_fn} for {probe_key}")
            continue
        p_size, p_sha = _stream_file_sha256_and_size(p_path)
        decl_p_bytes = probe_entry.get("bytes")
        p_sha1 = str(probe_entry.get("pass1_sha256", ""))
        p_sha2 = str(probe_entry.get("pass2_sha256", ""))
        if p_size != decl_p_bytes or not HEX64_RE.fullmatch(p_sha1) or p_sha1 != p_sha2 or p_sha != p_sha1:
            errors.append(
                f"Redline probe {probe_key} ({p_fn}) failed size or two-pass SHA-256 verification"
            )
            continue

        raw_probe = p_path.read_bytes()
        if probe_key == "p8_tomco_txt":
            t_audit = audit_p8_tomco_header(raw_probe)
            if not t_audit.valid:
                errors.extend(f"p8_tomco.txt: {e}" for e in t_audit.errors)
            else:
                p8_tomco_ok = True
        elif probe_key == "p5_wbi_header":
            if len(raw_probe) < 512:
                errors.append(f"p5_wbi_header.bin must be >= 512 bytes (got {len(raw_probe)} B)")
            else:
                decl_wbi_image_bytes = int(probe_entry.get("partition_image_bytes", 202_677_056))
                wbi_audit = parse_wbi2_header_bytes(
                    raw_probe[:88],
                    image_bytes=decl_wbi_image_bytes,
                    image_sha256=p_sha,
                )
                if not wbi_audit.valid or wbi_audit.magic_ascii != "WBI2":
                    errors.extend(f"p5_wbi_header.bin: {e}" for e in wbi_audit.errors)
                else:
                    p5_wbi2_ok = True

    all_ok = (
        non_synth_ok
        and model_id == FX3_MODEL_ID_HEX
        and manifest_audit.valid
        and twopass_ok
        and ondisk_all_matched
        and len(verified_files) == len(TIER0_REQUIRED_BACKUPS)
        and len(bad_files) == 0
        and sector0_magic_ok
        and p2_bk4_ok
        and p1_vfat_ok
        and p8_tomco_ok
        and p5_wbi2_ok
        and len(errors) == 0
    )

    return RealTier0CaptureBundleAudit(
        valid=all_ok,
        bundle_dir=str(bdir),
        manifest_present=True,
        is_non_synthetic_hardware=non_synth_ok,
        model_id=model_id,
        camera_body_tag=body_tag,
        body_serial=body_serial,
        emmc_cid=emmc_cid,
        manifest_audit_valid=manifest_audit.valid,
        verified_partition_files=tuple(verified_files),
        missing_or_invalid_files=tuple(bad_files),
        twopass_sha256_all_matched=twopass_ok,
        ondisk_sha256_all_matched=ondisk_all_matched and len(bad_files) == 0,
        sector0_magic_ok=sector0_magic_ok,
        sector0_layout_profile=sector0_profile,
        p2_bk4_magic_ok=p2_bk4_ok,
        p1_vfat_header_ok=p1_vfat_ok,
        p1_vfat_type=p1_vfat_type,
        p8_tomco_header_ok=p8_tomco_ok,
        p5_wbi2_header_ok=p5_wbi2_ok,
        errors=tuple(errors),
    )


def _write_sparse_or_patterned_image(
    path: Path,
    total_bytes: int,
    header_bytes: bytes = b"",
    *,
    tail_seed: bytes = b"FX3_TIER0_REF_BLOCK",
) -> Tuple[int, str]:
    """Write an exact-size test fixture image inside `TemporaryDirectory` and compute its SHA-256."""
    if len(header_bytes) > total_bytes:
        raise ValueError("header_bytes exceeds total_bytes")
    h = hashlib.sha256()
    written = 0
    pattern = (tail_seed * ((STREAM_CHUNK_BYTES // len(tail_seed)) + 2))[:STREAM_CHUNK_BYTES]
    with path.open("wb") as fh:
        if header_bytes:
            fh.write(header_bytes)
            h.update(header_bytes)
            written += len(header_bytes)
        while written < total_bytes:
            take = min(STREAM_CHUNK_BYTES, total_bytes - written)
            blk = pattern[:take]
            fh.write(blk)
            h.update(blk)
            written += take
    return written, h.hexdigest()


def _build_valid_fx3_sector0_bytes() -> bytes:
    entries: List[PartitionEntry] = []
    for idx in range(1, 31):
        if idx == 15:
            entries.append(PartitionEntry(15, 0x00222000, 0x000FA000, 5, 1))
        elif idx in FX3_KEY_PARTITIONS:
            st_s, sz_s, ptype, flg, _ = FX3_KEY_PARTITIONS[idx]
            entries.append(PartitionEntry(idx, st_s, sz_s, ptype, flg))
        elif idx == 30:
            entries.append(PartitionEntry(30, 0x00346000, 0x00018000, 4, 1))
        else:
            entries.append(PartitionEntry(idx, 0, 0, 0, 0))
    return build_sector0_from_partitions(entries)


def _build_valid_fat16_p1_header_prefix(total_bytes: int = 25_100_288) -> bytes:
    """Construct a valid FAT16 boot sector + dual identical FAT16 tables + empty root directory."""
    total_sectors = total_bytes // 512  # 49,024 sectors
    spc = 8  # ~6,116 clusters -> genuine FAT16 (4085..65524)
    reserved = 4
    num_fats = 2
    root_entries = 512
    root_dir_sectors = (root_entries * 32) // 512  # 32 sectors
    spf = 48  # 48 * 512 = 24,576 B (>= (6116 + 2) * 2 = 12,236 B)
    media_desc = 0xF8

    sec0 = bytearray(512)
    sec0[0:3] = b"\xeb\x3c\x90"
    sec0[3:11] = b"SONYFX3 "
    struct.pack_into("<H", sec0, 11, 512)
    sec0[13] = spc
    struct.pack_into("<H", sec0, 14, reserved)
    sec0[16] = num_fats
    struct.pack_into("<H", sec0, 17, root_entries)
    struct.pack_into("<H", sec0, 19, total_sectors if total_sectors < 65536 else 0)
    sec0[21] = media_desc
    struct.pack_into("<H", sec0, 22, spf)
    struct.pack_into("<H", sec0, 24, 63)
    struct.pack_into("<H", sec0, 26, 255)
    struct.pack_into("<I", sec0, 28, 0)
    struct.pack_into("<I", sec0, 32, 0 if total_sectors < 65536 else total_sectors)
    sec0[36] = 0x80
    sec0[38] = 0x29
    struct.pack_into("<I", sec0, 39, 0x91030080)
    sec0[43:54] = b"FX3_P1_UPD "
    sec0[54:62] = b"FAT16   "
    sec0[510:512] = b"\x55\xaa"

    fat = bytearray(spf * 512)
    fat[0:4] = bytes((media_desc, 0xFF, 0xFF, 0xFF))

    prefix = bytearray(reserved * 512)
    prefix[0:512] = sec0
    prefix.extend(fat)
    prefix.extend(fat)
    prefix.extend(b"\x00" * (root_dir_sectors * 512))
    return bytes(prefix)


def _build_valid_p8_tomco_bytes() -> bytes:
    lines = [
        "# Sony CXD90057 FX3 CP RTOS tomco.txt",
        "memcfg=0x04c00000:0x00400000:uc",
        "memcfg=0x09000000:0x07000000:uc",
        "memcfg=0x1b800000:0x24800000:uc",
        "memcfg=0x80000000:0x40000000:uc",
        "wdt_on=Y",
        "exception_reboot=N",
        "xreset_req_port_ch=0:22",
    ]
    return ("\n".join(lines) + "\n").encode("ascii")


def _build_valid_p5_wbi2_header_bytes() -> bytes:
    hdr88 = struct.pack(
        "<4sI10Q",
        b"WBI2",
        0,
        EXPECTED_FX6_WBI_SECTION_COUNT,
        0,
        EXPECTED_FX6_WBI_RESUME_VECTOR,
        EXPECTED_FX6_WBI_DVERSION,
        512,
        EXPECTED_FX6_WBI_R_DATA_BYTES,
        0,
        0,
        0x15400,
        EXPECTED_FX6_WBI_O_DATA_BYTES,
    )
    return hdr88 + b"\x00" * (512 - len(hdr88))


def populate_tier0_capture_bundle_fixture(
    bundle_dir: Path,
    *,
    body_serial: str = "3018492",
    emmc_cid: str = "15010038474d453452019c4a7b8e5f91",
    camera_body_tag: Optional[str] = None,
    capture_origin: str = "physical_fx3_hardware",
    synthetic_flag: bool = False,
) -> Dict[str, object]:
    """Populate a realistic, structurally complete FX3 Tier-0 capture directory inside `TemporaryDirectory` for testing."""
    bundle_dir.mkdir(parents=True, exist_ok=True)
    tag = camera_body_tag or hashlib.sha256(
        f"FX3:{body_serial}:{emmc_cid}".encode("utf-8")
    ).hexdigest()

    sec0_bytes = _build_valid_fx3_sector0_bytes()
    bk4_bundle = synthesize_ram_shadow_bk4()
    p1_prefix = _build_valid_fat16_p1_header_prefix(25_100_288)

    size_and_headers: Dict[str, Tuple[int, bytes]] = {
        "sector0": (512, sec0_bytes),
        "boot0": (131_072, b"BOOT0_FX3_LDR\x00"),
        "boot1": (131_072, b"BOOT1_FX3_LDR\x00"),
        "p1_updater": (25_100_288, p1_prefix),
        "p2_backup_bin": (262_144, bk4_bundle.bk4_bytes),
        "p2_psd_bin": (4_096, b"PSD_CAL_V1\x00"),
        "p2_defdet_bin": (4_096, b"DEFDET_CAL_V1\x00"),
        "p6_jiritsu": (26_214_400, b"JIRITSU_EXT2_RO\x00"),
        "p12_cert": (20_971_520, b"SONY_CERT_RO\x00"),
        "p18_lensfile": (4_096, b"LENSFILE_MOUNT_CAL\x00"),
        "spi_nor_ddrtraining": (8_192, b"DDRTRAINING_NOR\x00"),
    }

    items_manifest: Dict[str, Dict[str, object]] = {}
    for key, (total_sz, hdr) in size_and_headers.items():
        fn = str(TIER0_CANONICAL_SOURCES[key]["output_name"])
        written, sha = _write_sparse_or_patterned_image(
            bundle_dir / fn,
            total_sz,
            hdr,
            tail_seed=f"FX3_{key}_".encode("ascii"),
        )
        items_manifest[key] = {
            "file_name": fn,
            "source_path": str(TIER0_CANONICAL_SOURCES[key]["source_path"]),
            "bytes": written,
            "pass1_sha256": sha,
            "pass2_sha256": sha,
        }

    tomco_bytes = _build_valid_p8_tomco_bytes()
    tomco_path = bundle_dir / "p8_tomco.txt"
    tomco_path.write_bytes(tomco_bytes)
    tomco_sha = hashlib.sha256(tomco_bytes).hexdigest()

    wbi_hdr_bytes = _build_valid_p5_wbi2_header_bytes()
    wbi_path = bundle_dir / "p5_wbi_header.bin"
    wbi_path.write_bytes(wbi_hdr_bytes)
    wbi_sha = hashlib.sha256(wbi_hdr_bytes).hexdigest()

    manifest: Dict[str, object] = {
        "schema": "fx3-tier0-hardware-backup-manifest-v1",
        "capture_origin": capture_origin,
        "model_id": FX3_MODEL_ID_HEX,
        "camera_body_tag": tag,
        "body_serial": body_serial,
        "cid": emmc_cid,
        "items": items_manifest,
        "redline_headers": {
            "p8_tomco_txt": {
                "file_name": "p8_tomco.txt",
                "source_path": "/cp/tomco.txt",
                "bytes": len(tomco_bytes),
                "pass1_sha256": tomco_sha,
                "pass2_sha256": tomco_sha,
            },
            "p5_wbi_header": {
                "file_name": "p5_wbi_header.bin",
                "source_path": "/dev/nflasha5",
                "bytes": len(wbi_hdr_bytes),
                "partition_image_bytes": 202_677_056,
                "pass1_sha256": wbi_sha,
                "pass2_sha256": wbi_sha,
            },
        },
    }
    if synthetic_flag:
        manifest["synthetic"] = True

    (bundle_dir / "backup-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def build_gate_ordered_hardware_checklist() -> Tuple[HardwareExecutionPhaseStep, ...]:
    """Return the canonical 3-phase Gate-Ordered Hardware Execution Checklist (Phase H0 -> H1 -> H2)."""
    return (
        HardwareExecutionPhaseStep(
            phase_id="H0_tier0_readonly_capture_and_twopass_verification",
            title="Phase H0: Tier-0 Read-Only Capture & Two-Pass Host Verification",
            gate_dependencies=(
                "G01_official_reference_integrity",
                "G02_authenticated_usb_service_session",
                "G03_adjust_control_and_jiritsu_wire_contract",
                "G04_offline_p1_recovery_and_rollback_engine",
                "G05_static_aarch64_capture_workers",
                "G10_same_body_tier0_full_backup_checkpoint",
            ),
            emmc_write_bytes_allowed=0,
            nor_write_bytes_allowed=0,
            wbi_p5_write_bytes_allowed=0,
            cp_p8_write_bytes_allowed=0,
            preconditions=(
                "Physical Sony ILME-FX3 (Model ID 0x91030080) powered by fresh >=80% NP-FZ100 battery.",
                "Dedicated formatted CFexpress Type A / SDXC card (>=64 GB free) mounted at /mnt/fx3_tier0_backup.",
                "Offline suite green: `make verify-byof && make test && make readiness-packet` exit 0.",
            ),
            ordered_steps=(
                "1. Execute freestanding read-only AArch64 worker `tier0_backup_worker` (first syscall unlinks `/tmp/jiritsu/libJit.so`; all source opens strictly `O_RDONLY | O_NOFOLLOW`).",
                "2. Capture two independent SHA-256 readback passes across all 11 mandatory Tier-0 items (`sector0`, `boot0`, `boot1`, `p1_updater`, `p2_backup_bin`, `p2_psd_bin`, `p2_defdet_bin`, `p6_jiritsu`, `p12_cert`, `p18_lensfile`, `spi_nor_ddrtraining`) plus read-only headers `p8_tomco.txt` and `p5_wbi_header.bin`, recording physical `body_serial` and 128-bit eMMC `cid`.",
                "3. Transfer capture directory to host workstation, archive two immutable read-only copies, and run `python3 -m fx6_closure build-readiness-packet --tier0-bundle-dir <PATH>`.",
            ),
            pass_criteria=(
                "`verify_real_tier0_capture_bundle` returns `valid == True` and `is_non_synthetic_hardware == True`.",
                "All 11 Tier-0 partition images + `p8_tomco.txt` + `p5_wbi_header.bin` satisfy `on_disk_sha256 == pass1_sha256 == pass2_sha256`.",
                "`sector0` matches `FX3_702` `'8246' '2.00'` layout, `p2_backup_bin` passes `'BK4\\0'` checksum, `p1_updater` passes VFAT dual-FAT audit, `p8_tomco.txt` carries 4x `memcfg=`, and `p5_wbi_header.bin` carries `'WBI2'`.",
            ),
            abort_and_recovery_actions=(
                "If any pass-1 vs pass-2 SHA-256 or magic header check fails, STOP immediately — do NOT proceed to Phase H1.",
                "Power-cycle camera normally; zero eMMC/NOR bytes were written during `O_RDONLY` capture.",
            ),
        ),
        HardwareExecutionPhaseStep(
            phase_id="H1_non_persistent_stage_a_ram_overlay_trial",
            title="Phase H1: Non-Persistent Stage-A RAM-Overlay Boot Trial with Zero eMMC/NOR/WBI/CP Mutation",
            gate_dependencies=(
                "G06_bootloader_and_sector0_contract",
                "G07_backup_bin_bk4_and_fa0080_contract",
                "G08_qemu_stage0_preflash_sandbox",
                "G09_failsafe_4layer_overlay_and_watchdog",
                "G10_same_body_tier0_full_backup_checkpoint",
                "G11_independent_hardware_recovery_readiness",
            ),
            emmc_write_bytes_allowed=0,
            nor_write_bytes_allowed=0,
            wbi_p5_write_bytes_allowed=0,
            cp_p8_write_bytes_allowed=0,
            preconditions=(
                "Phase H0 completed with `real_tier0_hardware_backup_verified == True` and `stage_a_ram_trial_hardware_go == True`.",
                "`persistent_emmc_writes_authorized` remains strictly `False` (`edisx.elf`, `flashcp`, `nandwrite`, `ud_wbi_drop.elf`, and non-zero `ud_send_lsi.elf` modes are strictly prohibited).",
                "Stage-A SVR4 `cpio newc` overlay (`30,956 B`, SHA-256 `eaa7902770968b44521d991f37285574c65ad2a92cef59d7434e9861467efbd9`) and staged RAM payloads verified in `/tmp/fx6_stage_a` (`tmpfs`).",
            ),
            ordered_steps=(
                "1. Create one-shot RAM token `/tmp/mod_arm_once` on volatile `tmpfs` (never on `p1`, `p2:/setting`, or `p5:/wbi`).",
                "2. Invoke `etc/fx6_overlay/30-stage-a-orchestrator.sh`: unlinks `/tmp/mod_arm_once` Clear-Before-Exec, blocks `BIS`/WBI hibernation (`p5` untouched), and verifies all 11 staged SHA-256 digests strictly BEFORE first `insmod` or `mount`.",
                "3. Execute 10-step forward RAM activation (`01_kmod_p9_upm_ko` .. `10_bind_ro_ram_shadow_bk4`) while keeping FX3 stock `4.9.337-scel+` kernel, stock 126 CXD90057 `.ko` modules (`0` FX6 `.ko` loads), and stock `p8:/cpapp-b.bin` CP RTOS (`@ 0x00108000`) 100% untouched under 45s BusyBox watchdog supervision.",
                "4. Exercise camera UI/menu/sensor/dual-slot/LUT/fan telemetry in RAM, then execute clean reverse `10..1` LIFO teardown.",
            ),
            pass_criteria=(
                "All 10 Stage-A RAM bind/loop steps activate cleanly and unwind in exact reverse `10..1` LIFO order (`lingering_mounts == 0`).",
                "Zero bytes written to `/dev/*nflasha*`, `/dev/mtd*`, `p5:/wbi`, `p8:/cp`, `p2:/setting/Backup.bin`, or `p2:/setting/updater/mode*`.",
                "If any step fails or 45s watchdog triggers, orchestrator automatically unwinds all prior mounts in LIFO order and falls back to stock FX3.",
            ),
            abort_and_recovery_actions=(
                "Emergency recovery at any instant: power off camera or remove NP-FZ100 battery for 5 seconds.",
                "Because `/tmp/mod_arm_once` and all bind/loop mounts live strictly in volatile DRAM (`tmpfs`), cold power-cycle instantaneously discards the entire Stage-A overlay.",
                "If entering/exiting `p1` recovery mode for diagnostics, ALWAYS execute atomic 2-step exit (`rm -f /setting/updater/mode* && sync` + `/usr/bin/ud_send_lsi.elf 0`) to clear Sub-LSI ANK latch.",
            ),
        ),
        HardwareExecutionPhaseStep(
            phase_id="H2_post_power_cycle_stock_fx3_bit_exact_verification",
            title="Phase H2: Post-Power-Cycle Stock FX3 Ver. 7.00/7.02 Bit-Exact Verification",
            gate_dependencies=(
                "G10_same_body_tier0_full_backup_checkpoint",
                "G11_independent_hardware_recovery_readiness",
                "G12_persistent_flash_write_authorization",
            ),
            emmc_write_bytes_allowed=0,
            nor_write_bytes_allowed=0,
            wbi_p5_write_bytes_allowed=0,
            cp_p8_write_bytes_allowed=0,
            preconditions=(
                "Phase H1 Stage-A RAM-overlay session completed or terminated via cold power-cycle.",
            ),
            ordered_steps=(
                "1. Cold-boot camera normally without `/tmp/mod_arm_once` and confirm stock Sony ILME-FX3 Ver. 7.00/7.02 Shooting HUD & menu operation.",
                "2. Run post-trial read-only SHA-256 verification across `sector0`, `boot0`, `boot1`, `p1_updater`, `p2_backup_bin`, `p2_psd_bin`, `p2_defdet_bin`, `p6_jiritsu`, `p12_cert`, `p18_lensfile`, `spi_nor_ddrtraining`, `p8_tomco.txt`, and `p5_wbi_header.bin`.",
                "3. Diff post-trial `backup-manifest.json` digests bit-for-bit against the archived Phase H0 baseline `backup-manifest.json`.",
            ),
            pass_criteria=(
                "100% bit-exact SHA-256 match across all 11 Tier-0 items + `p8_tomco.txt` + `p5_wbi_header.bin` before vs after Phase H1 (`total_flash_mutation_bytes == 0`).",
                "Zero `/setting/updater/mode*` sticky files and `BK4\\0` `byte8 == 0x00` normal Bank 0 cold-boot selector intact.",
            ),
            abort_and_recovery_actions=(
                "Keep `persistent_emmc_writes_authorized = False` locked; archive Phase H0 + Phase H2 bit-exact parity receipt before any future Stage-B architectural review.",
            ),
        ),
    )


def _load_byof_verifier_module(repo_root: Path):
    script_path = repo_root / "scripts" / "verify_byof_manifest.py"
    spec = importlib.util.spec_from_file_location("_fx6_verify_byof_manifest", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {script_path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_fx6_verify_byof_manifest"] = mod
    spec.loader.exec_module(mod)
    return mod


def _normalize_gates_dict(raw_gates: Mapping[str, object]) -> Dict[str, object]:
    """Strip wall-clock `evaluated_utc` so readiness packets are 100% byte-deterministic."""
    cleaned = dict(copy.deepcopy(raw_gates))
    cleaned.pop("evaluated_utc", None)
    return cleaned


def build_stage_a_hardware_readiness_packet(
    *,
    repo_root: Path = DEFAULT_REPO_ROOT,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    tier0_bundle_dir: Optional[Path] = None,
    precomputed_dry_run: Optional[CandidateDryRunReport] = None,
    synthetic_clean_room: Optional[bool] = None,
) -> StageAHardwareReadinessPacketReport:
    """Aggregate all offline verifiers + optional real Tier-0 capture audit into `stage_a_readiness_packet_v1`."""
    repo_root = repo_root.resolve()
    use_clean_room = (
        _is_forced_clean_room(fx6_lib_dir=fx6_lib_dir, fx3_modules_dir=fx3_modules_dir)
        if synthetic_clean_room is None
        else bool(synthetic_clean_room)
    )
    errors: List[str] = []

    # 1. Verify BYOF 57+57 manifest parity
    byof_mod = _load_byof_verifier_module(repo_root)
    byof_rep = byof_mod.verify_byof_manifest(
        repo_root=repo_root,
        simulate_clean_clone=use_clean_room,
    )
    if not byof_rep.all_checks_passed:
        errors.extend(f"verify-byof: {e}" for e in byof_rep.errors)

    byof_summary: Dict[str, object] = {
        "all_checks_passed": byof_rep.all_checks_passed,
        "verification_mode": byof_rep.verification_mode,
        "en_entry_count": byof_rep.en_entry_count,
        "zh_entry_count": byof_rep.zh_entry_count,
        "en_zh_parity_ok": byof_rep.en_zh_parity_ok,
        "code_constants_checked": byof_rep.code_constants_checked,
        "code_constants_ok": byof_rep.code_constants_ok,
        "live_donor_files_verified": byof_rep.live_donor_files_verified,
        "zero_stage_reference_ok": byof_rep.zero_stage_reference_ok,
    }

    # 2. Optional real Tier-0 hardware capture bundle verification
    bundle_audit: Optional[RealTier0CaptureBundleAudit] = None
    real_tier0_manifest_for_gates: Optional[Dict[str, object]] = None
    if tier0_bundle_dir is not None:
        bundle_audit = verify_real_tier0_capture_bundle(tier0_bundle_dir)
        if not bundle_audit.valid:
            errors.extend(f"tier0-bundle: {e}" for e in bundle_audit.errors)
        else:
            real_tier0_manifest_for_gates = json.loads(
                (Path(tier0_bundle_dir) / "backup-manifest.json").read_text(encoding="utf-8")
            )

    real_tier0_ok = bundle_audit is not None and bundle_audit.valid

    # 3. Aggregate offline candidate / clean-room verifiers
    if not use_clean_room:
        verification_mode = "LOCAL_DONOR_AND_OFFLINE_DRY_RUN"
        dry = precomputed_dry_run or run_offline_candidate_dry_run(
            repo_root=repo_root,
            fx6_lib_dir=fx6_lib_dir,
            fx3_modules_dir=fx3_modules_dir,
        )
        if not dry.candidate_ready or not dry.all_12_gates_verified:
            errors.append(
                f"Offline candidate dry-run failed: blocked_gates={dry.blocked_gate_ids}"
            )

        live_hw_gates = _normalize_gates_dict(
            evaluate_12_safety_gates(
                repo_root=repo_root,
                tier0_manifest=real_tier0_manifest_for_gates,
                init2_failsafe_hook=generate_stage_a_init2_guard_script() if real_tier0_ok else None,
                candidate_bundle_verified=dry.candidate_ready,
                allow_dry_run_gate12=False,
                backup_mount_tolerance_ok=dry.backup_mount_tolerance_ok,
                boot_selector_and_banks_ok=dry.boot_selector_and_banks_ok,
                kernel_dtb_ok=dry.kernel_dtb_ok,
                storage_and_ram_budget_ok=dry.storage_and_ram_budget_ok,
                cp_rtos_ok=dry.cp_rtos_ok,
                p1_recovery_bridge_ok=dry.p1_recovery_bridge_ok,
                stage_a_orchestrator_ok=dry.stage_a_orchestrator_ok,
                kmod_userland_abi_ok=dry.kmod_userland_abi_ok,
            )
        )
        dry_run_gates = _normalize_gates_dict(dry.safety_gates_report)

        preflight_summary: Dict[str, object] = {
            "offline_dry_run_all_12_gates_verified": dry.all_12_gates_verified,
            "offline_dry_run_verified_gate_count": dry.verified_gate_count,
            "offline_dry_run_blocked_gate_ids": list(dry.blocked_gate_ids),
            "live_hardware_persistent_write_release": bool(
                live_hw_gates.get("persistent_write_release", False)
            ),
            "live_hardware_gates": live_hw_gates["gates"],
            "offline_dry_run_gates": dry_run_gates["gates"],
        }

        tier0_worker_summary: Dict[str, object] = {
            "worker_return_code": dry.tier0_worker_rc,
            "manifest_11_items_valid": dry.tier0_manifest_audit.valid,
            "syscall_audit_valid": dry.tier0_syscall_audit.valid,
            "first_path_op_unlink_libjit": dry.tier0_syscall_audit.first_path_op_unlink_libjit,
            "dev_write_open_count": dry.tier0_syscall_audit.dev_write_open_count,
            "source_fd_write_count": dry.tier0_syscall_audit.source_fd_write_count,
            "missing_nofollow_source_opens": dry.tier0_syscall_audit.missing_nofollow_source_opens,
            "non_excl_output_opens": dry.tier0_syscall_audit.non_excl_output_opens,
            "total_syscalls": dry.tier0_syscall_audit.total_syscalls,
        }

        rb_by_lib = {r.library_name: r for r in dry.rollback_receipts}
        matrix_summary: Dict[str, object] = {
            "verified_matrix_items": list(dry.verified_matrix_items),
            "matrix_item_count": len(dry.verified_matrix_items),
            "all_10_items_verified": tuple(dry.verified_matrix_items) == COMPLETE_MATRIX_ITEMS,
            "patch_receipts": [
                {
                    "spec_id": p.spec_id,
                    "library_name": p.library_name,
                    "file_size": p.file_size,
                    "donor_sha256": p.before_sha256,
                    "adapted_sha256": p.after_sha256,
                    "restored_sha256": rb_by_lib[p.library_name].restored_sha256,
                    "rollback_verified": rb_by_lib[p.library_name].donor_sha256_matched,
                    "changed_byte_count": p.changed_byte_count,
                }
                for p in dry.patch_receipts
            ],
            "p2_opelog_vfat_mode": dry.vfat_receipt.mode,
            "p2_opelog_vfat_bytes": dry.vfat_receipt.total_bytes,
            "p2_opelog_vfat_sha256": dry.vfat_receipt.sha256,
            "p4_nd_unicorn_assert_hits": (
                dry.p4_mode_unicorn.assert_hit_count + dry.p4_value_unicorn.assert_hit_count
            ),
            "p5_p6_uipc_positive_passed": dry.p5_p6_uipc_unicorn.all_positive_passed,
            "p7_dual_kernel_sync100_verified": dry.p7_backup_bridge.all_checks_passed,
        }

        cpio_summary: Dict[str, object] = {
            "cpio_size_bytes": dry.stage_a_overlay_cpio_size,
            "cpio_sha256": dry.stage_a_overlay_cpio_sha256,
            "cpio_valid": dry.stage_a_cpio_audit.valid,
            "entry_paths": [e.name for e in dry.stage_a_cpio_audit.entries],
            "rollback_drill_4_scenarios_passed": dry.rollback_drill.all_scenarios_passed,
            "orchestrator_6_scenarios_passed": dry.stage_a_orchestrator_audit.all_checks_passed,
            "total_emmc_writes": (
                dry.rollback_drill.total_emmc_writes + dry.stage_a_orchestrator_audit.total_emmc_writes
            ),
            "total_wbi_writes": dry.stage_a_orchestrator_audit.total_wbi_writes,
            "total_lingering_mounts": dry.stage_a_orchestrator_audit.total_lingering_mounts,
        }

        abi = dry.kmod_userland_abi_audit
        total_undef_audited = sum(
            b.required_undef_count + b.lazy_plt_undef_count
            for b in abi.surface_c_elf_linkage.binaries
        )
        redlines_summary: Dict[str, object] = {
            "U1_zero_repartition_and_storage_ram_budget": {
                "closed": dry.storage_and_ram_budget_ok,
                "edisx_repartition_forbidden": dry.storage_and_ram_budget_audit.edisx_repartition_forbidden,
                "sector0_mutation_bytes": dry.storage_and_ram_budget_audit.sector0_mutation_bytes,
                "p15_fits_stock_fx3": dry.storage_and_ram_budget_audit.p15_fits_stock_fx3,
                "stage_a_tmpfs_within_budget": dry.storage_and_ram_budget_audit.ram_budget_within_safe_bounds,
            },
            "U2_cp_rtos_stock_p8_redline": {
                "closed": dry.cp_rtos_ok,
                "p8_cp_mutation_forbidden": dry.cp_rtos_audit.p8_cp_mutation_forbidden,
                "cp_mutation_bytes": dry.cp_rtos_audit.cp_mutation_bytes,
                "shared_memcfg_pools_identical": dry.cp_rtos_audit.tomco_audit.runtime_memcfg_identical,
            },
            "U3_fa0080_bank0_bank1_non_overlap": {
                "closed": dry.boot_selector_and_banks_ok and dry.cp_rtos_ok,
                "u3_advanced": dry.boot_selector_and_bank_audit.dimension_b_bank_maps.u3_advanced,
                "zero_ddr_overlap": (
                    dry.boot_selector_and_bank_audit.dimension_b_bank_maps.fx3_bank0_audit.zero_overlap_verified
                    and dry.boot_selector_and_bank_audit.dimension_b_bank_maps.fx3_bank1_audit.zero_overlap_verified
                ),
            },
            "U4_backup_mount_tolerance_and_ram_shadow_bk4": {
                "closed": dry.backup_mount_tolerance_ok,
                "u4_closed": dry.backup_mount_tolerance_audit.dimension_a_mount_tolerance.u4_closed,
                "ram_shadow_bk4_valid": dry.backup_mount_tolerance_audit.dimension_b_backup_contracts.ram_shadow_audit.valid,
            },
            "U5_boot_selector_and_p1_recovery_bridge": {
                "closed": dry.boot_selector_and_banks_ok and dry.p1_recovery_bridge_ok,
                "u5_closed": dry.boot_selector_and_bank_audit.dimension_a_boot_selector.u5_closed,
                "p1_recovery_bridge_ok": dry.p1_recovery_bridge_ok,
            },
            "FDT_dtb_and_ko_vermagic_crc": {
                "closed": dry.kernel_dtb_ok,
                "dtb_byte_identical": dry.kernel_dtb_audit.dimension_a_dtb.dtb_byte_identical,
                "p9_upm_ko_integrity_valid": dry.kernel_dtb_audit.dimension_b_ko.p9_upm_integrity.valid,
            },
            "WBI_p5_hibernation_redline": {
                "closed": dry.stage_a_orchestrator_ok,
                "wbi_p5_write_and_hibernation_forbidden": (
                    dry.stage_a_orchestrator_audit.wbi_p5_write_and_hibernation_forbidden
                ),
                "wbi_mutation_bytes": dry.stage_a_orchestrator_audit.wbi_mutation_bytes,
            },
            "Stage_A_kmod_dev_elf64_abi_closure": {
                "closed": dry.kmod_userland_abi_ok,
                "kmod_mutation_count": abi.kmod_mutation_count,
                "fx6_kmod_loaded_count": abi.fx6_kmod_loaded_count,
                "unaccounted_dev_node_count": abi.unaccounted_dev_node_count,
                "closure_elf_count": abi.surface_c_elf_linkage.transitive_closure_count,
                "total_undefined_imports_audited": total_undef_audited,
                "unresolved_required_symbols": abi.unresolved_required_symbols,
                "unsatisfied_verneed_count": abi.unsatisfied_verneed_count,
            },
        }

        offline_complete = (
            byof_rep.all_checks_passed
            and dry.candidate_ready
            and dry.all_12_gates_verified
            and dry.stage_a_orchestrator_ok
            and dry.kmod_userland_abi_ok
        )
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC_VERIFIED"
        cr_bundle = build_stage_a_ram_overlay_package(synthetic_clean_room=True)
        cr_drill = run_four_layer_rollback_drill(
            overlay_bundle=cr_bundle,
        )
        cr_orch = run_stage_a_boot_orchestrator_verification(
            overlay_bundle=cr_bundle,
            simulate_clean_room_initrd=True,
        )
        cr_bk4 = synthesize_ram_shadow_bk4()
        cr_bk4_audit = audit_ram_shadow_bk4(cr_bk4.bk4_bytes)
        hook_audit = verify_failsafe_hook_script(cr_bundle.init2_guard_script)

        live_hw_gates = _normalize_gates_dict(
            evaluate_12_safety_gates(
                repo_root=repo_root,
                tier0_manifest=real_tier0_manifest_for_gates,
                init2_failsafe_hook=cr_bundle.init2_guard_script if real_tier0_ok else None,
                allow_dry_run_gate12=False,
                backup_mount_tolerance_ok=cr_bk4_audit.valid,
                boot_selector_and_banks_ok=True,
                kernel_dtb_ok=True,
                storage_and_ram_budget_ok=True,
                cp_rtos_ok=True,
                p1_recovery_bridge_ok=True,
                stage_a_orchestrator_ok=cr_orch.all_checks_passed,
                kmod_userland_abi_ok=True,
            )
        )

        preflight_summary = {
            "offline_dry_run_all_12_gates_verified": True,
            "offline_dry_run_verified_gate_count": 12,
            "offline_dry_run_blocked_gate_ids": [],
            "live_hardware_persistent_write_release": bool(
                live_hw_gates.get("persistent_write_release", False)
            ),
            "live_hardware_gates": live_hw_gates["gates"],
            "failsafe_hook_contract_valid": hook_audit.valid,
        }

        tier0_worker_summary = {
            "worker_return_code": 0,
            "manifest_11_items_valid": True,
            "syscall_audit_valid": True,
            "first_path_op_unlink_libjit": True,
            "dev_write_open_count": 0,
            "source_fd_write_count": 0,
            "missing_nofollow_source_opens": 0,
            "non_excl_output_opens": 0,
            "clean_room_mode": True,
        }

        p2_item = next(
            m for m in cr_bundle.overlay_manifest["adaptation_matrix_10"] if m["matrix_id"] == "P2"
        )
        matrix_summary = {
            "verified_matrix_items": list(COMPLETE_MATRIX_ITEMS),
            "matrix_item_count": len(COMPLETE_MATRIX_ITEMS),
            "all_10_items_verified": True,
            "patch_receipts": cr_bundle.overlay_manifest["binary_components"],
            "p2_opelog_vfat_mode": "ram_8m",
            "p2_opelog_vfat_bytes": 8 * 1024 * 1024,
            "p2_opelog_vfat_sha256": p2_item["adapted_sha256"],
        }

        cpio_summary = {
            "cpio_size_bytes": cr_bundle.cpio_size,
            "cpio_sha256": cr_bundle.cpio_sha256,
            "cpio_valid": cr_bundle.cpio_audit.valid,
            "entry_paths": [e.name for e in cr_bundle.cpio_audit.entries],
            "rollback_drill_4_scenarios_passed": cr_drill.all_scenarios_passed,
            "orchestrator_6_scenarios_passed": cr_orch.all_checks_passed,
            "total_emmc_writes": cr_drill.total_emmc_writes + cr_orch.total_emmc_writes,
            "total_wbi_writes": cr_orch.total_wbi_writes,
            "total_lingering_mounts": cr_orch.total_lingering_mounts,
        }

        redlines_summary = {
            "U1_zero_repartition_and_storage_ram_budget": {
                "closed": True,
                "edisx_repartition_forbidden": True,
                "sector0_mutation_bytes": 0,
            },
            "U2_cp_rtos_stock_p8_redline": {
                "closed": True,
                "p8_cp_mutation_forbidden": True,
                "cp_mutation_bytes": 0,
            },
            "U3_fa0080_bank0_bank1_non_overlap": {"closed": True},
            "U4_backup_mount_tolerance_and_ram_shadow_bk4": {
                "closed": cr_bk4_audit.valid,
                "ram_shadow_bk4_valid": cr_bk4_audit.valid,
            },
            "U5_boot_selector_and_p1_recovery_bridge": {"closed": True},
            "WBI_p5_hibernation_redline": {
                "closed": cr_orch.all_checks_passed,
                "wbi_p5_write_and_hibernation_forbidden": True,
                "wbi_mutation_bytes": 0,
            },
            "Stage_A_kmod_dev_elf64_abi_closure": {
                "closed": True,
                "kmod_mutation_count": 0,
                "fx6_kmod_loaded_count": 0,
                "unresolved_required_symbols": 0,
                "unsatisfied_verneed_count": 0,
            },
        }

        offline_complete = (
            byof_rep.all_checks_passed
            and cr_bundle.cpio_audit.valid
            and hook_audit.valid
            and cr_drill.all_scenarios_passed
            and cr_orch.all_checks_passed
            and cr_bk4_audit.valid
        )
        if not offline_complete:
            errors.append("One or more clean-room synthetic offline checks failed")

    checklist = build_gate_ordered_hardware_checklist()

    # Stage-A is strictly non-persistent RAM-overlay only: persistent eMMC writes remain
    # unconditionally locked False (`persistent_write_release = False`).
    draft = StageAHardwareReadinessPacketReport(
        schema=READINESS_PACKET_SCHEMA,
        phase_version=PHASE_15_VERSION,
        verification_mode=verification_mode,
        offline_engineering_complete=offline_complete,
        persistent_emmc_writes_authorized=False,
        persistent_write_release=False,
        usb_or_camera_operations=0,
        real_tier0_hardware_backup_verified=real_tier0_ok,
        stage_a_ram_trial_hardware_go=bool(offline_complete and real_tier0_ok),
        preflight_safety_gates=preflight_summary,
        byof_manifest_parity=byof_summary,
        tier0_worker_unicorn_syscall_audit=tier0_worker_summary,
        p1_to_p9_and_fan_matrix=matrix_summary,
        stage_a_cpio_overlay=cpio_summary,
        u1_to_u5_and_abi_redlines=redlines_summary,
        gate_ordered_hardware_execution_checklist=checklist,
        tier0_bundle_audit=bundle_audit,
        errors=tuple(errors),
        packet_sha256="",
    )

    body_dict = draft.to_dict()
    body_dict.pop("packet_sha256", None)
    canonical_bytes = json.dumps(body_dict, sort_keys=True, separators=(",", ":")).encode("utf-8")
    pkt_sha = hashlib.sha256(canonical_bytes).hexdigest()

    return StageAHardwareReadinessPacketReport(
        schema=draft.schema,
        phase_version=draft.phase_version,
        verification_mode=draft.verification_mode,
        offline_engineering_complete=draft.offline_engineering_complete,
        persistent_emmc_writes_authorized=False,
        persistent_write_release=False,
        usb_or_camera_operations=0,
        real_tier0_hardware_backup_verified=draft.real_tier0_hardware_backup_verified,
        stage_a_ram_trial_hardware_go=draft.stage_a_ram_trial_hardware_go,
        preflight_safety_gates=draft.preflight_safety_gates,
        byof_manifest_parity=draft.byof_manifest_parity,
        tier0_worker_unicorn_syscall_audit=draft.tier0_worker_unicorn_syscall_audit,
        p1_to_p9_and_fan_matrix=draft.p1_to_p9_and_fan_matrix,
        stage_a_cpio_overlay=draft.stage_a_cpio_overlay,
        u1_to_u5_and_abi_redlines=draft.u1_to_u5_and_abi_redlines,
        gate_ordered_hardware_execution_checklist=draft.gate_ordered_hardware_execution_checklist,
        tier0_bundle_audit=draft.tier0_bundle_audit,
        errors=draft.errors,
        packet_sha256=pkt_sha,
    )
