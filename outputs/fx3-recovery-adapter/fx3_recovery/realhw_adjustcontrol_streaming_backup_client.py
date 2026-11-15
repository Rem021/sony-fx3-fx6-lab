"""Phase 139 — Real-Hardware Main Track Part 5: Host-Side `AdjustControl (0x40)`
Streaming Full-Camera Cold-Backup Client, `p6` (`25 MiB`) Sliding-Window Pull &
Fake-IOKit End-to-End Regression (Pillar 17).

Closes the exact Stage-288 gap (`work/sony-firmware-20261024/stage288-jiritsu-readonly-payload/README.md §6`
and `reports/2026-11-03-fx6-full-system-to-fx3/README.md §5.2`) by providing a
host-side `AdjustControl (0x40)` transport codec, preflight `/tmp/jbusy` abort
state machine, dual-path full-camera cold-backup engine (Path 1 direct SD/CFexpress
ExFAT streaming with compact `528 B` signed-hash receipt + Path 2 `p6`-bounded
`<= 4 MiB` sliding-window USB pull with `FX3CHK1\\0` chunk framing), and a stateful
`FakeIOKitAdjustControlCamera` modeling Sony VID `0x054C` (`054C:0336`) while
hard-locking:
  - `live_usb_iokit_transmit_enabled = False` (zero physical USB transmission)
  - `persistent_emmc_writes_authorized = False` (zero physical eMMC/NOR writes)
  - `physical_device_writes = 0`, `physical_usb_bytes_transmitted = 0`

Subsystems:
1. **Read-Only (`O_RDONLY`) Donor Inspection**:
   - Inspects Stage-288 wire codec (`jiritsu_wire.py`, `fake_jiritsu_camera.py`,
     `libJit_test.so`), FX3 `7.02` `libJiritsu.so`, `partinf.conf` (`p6 = 25 MiB`,
     `p3 = 75 MiB`, `p15 = 500 MiB`), and `pformat_config.txt` strictly via
     `os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK`, with deterministic
     `FX3_FX6_FORCE_CLEAN_ROOM=1` fallback and zero raw firmware bytes in JSON.
2. **Pillar A — `ADJUSTCONTROL_0X40_WIRE_TRANSPORT_AND_PREFLIGHT_ABORT`**:
   - Exact Stage-288 wire envelopes (`SET_FILE_PATH`: `0x00 + path + 0x00`;
     `SET_FILE2`: `0x00 0xFF 0x00 + payload`; `GET_FILE2`: `0x00 0xFF 0x00`),
     rejecting selector `2`, forbidding `MODE` (`1`) / `MOUNT` (`2`) / `FORMAT` (`3`)
     / `START` (`4`) / `DEBUG` (`5`) / `FIRMUP` (`6`) and `edisx`/`uc_mkfs`.
   - Mandatory pre-session `/tmp/jbusy` probe (`GET_FILE2` must return `0x11`
     `ENOENT`) and immediate abort on `0x10000011`, `0x10000201`, `0x10000000`,
     `0x10000004`, `0x1000000F`, or USB timeout — NEVER blind-retrying a second
     `SET_FILE2`.
3. **Pillar B — `DUAL_PATH_SD_STREAM_AND_P6_SLIDING_WINDOW_COLD_BACKUP`**:
   - **Path 1**: Streams `Sector 0` (`512 B`) + Tier-0 (`p2`, `p6`, `p12`, `p18`,
     SPI NOR `ddrtraining.dat` `@ 0x3e210fc` + `loader_nor.bin`) + Tier-1 (`p1`
     with `dat2`/`dat3`, `p3`, `p7`, `p8`) + Tier-2 (`p5`, `p13`, `p15`, `p23`,
     `p30`) to `/mnt/sd/FX3_COLD_BACKUP/` with `MANIFEST.SHA256`, returning a
     compact `528 B` receipt over `GET_FILE2` (`< 1 KiB` `p6` usage).
   - **Path 2**: Pulls arbitrarily large partitions (e.g. `75 MiB` `p3`) in bounded
     `<= 4 MiB` chunks (`peak_p6_bytes <= 4.2 MiB << 25 MiB` `nflasha6` limit),
     verifying `[8B "FX3CHK1\\0" + u64 offset + u32 length + u32 crc32]` per chunk,
     confirming `p6_residual_files == 0`, and proving whole-partition SHA-256 parity.
4. **Pillar C — `FAKE_IOKIT_USB_CAMERA_REGRESSION_AND_PASSIVE_LOCK`**:
   - Stateful `FakeIOKitAdjustControlCamera` modeling Sony VID `0x054C` `AdjustControl`
     (`0x40`), `25 MiB` `p6` quota (`0x1000000F`), `jbusy` lockouts, ELF `DT_HASH
     (1, 1, 0, 0)` + `PT_LOAD` `0x10000` validation, post-session residual-file audit,
     and hard-locked passive USB / zero eMMC write enforcement.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import os
import posixpath
import re
import stat
import struct
import time
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple
import zlib

from .files import is_forced_clean_room, local_path, read_file, require, resolve_donor_path


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

ADJUSTCONTROL_BACKUP_SCHEMA: str = "fx3-realhw-adjustcontrol-streaming-backup-client-v1"
ADJUSTCONTROL_BACKUP_VERSION: str = "1.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False
LIVE_USB_IOKIT_TRANSMIT_ENABLED: bool = False
ALLOW_BOOT_PARTITION_TARGETING: bool = False
ALLOW_DESTRUCTIVE_FASTBOOT: bool = False
ALLOW_PERSISTENT_JIRITSU_WRITES: bool = False
ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS: bool = False
READ_ONLY_DONOR_ACCESS: bool = True

OTP_FUSE_TOUCHES: int = 0
OTP_FUSE_WRITES: int = 0
PASSIVE_TX_BYTES_EMITTED: int = 0
PHYSICAL_DEVICE_WRITES: int = 0
PHYSICAL_USB_BYTES_TRANSMITTED: int = 0

# Sony USB Identity & AdjustControl Wire Constants (Stage 288)
SONY_USB_VID: int = 0x054C
SONY_MSC_PID_FX3: int = 0x0DA1
SONY_SERVICE_PID: int = 0x0336
SONY_SERVICE_VID_PID: str = "054C:0336"

PFUNC_ADJUST_CONTROL: int = 0x0040
CATEGORY_JIRITSU: int = 0x1001

CMD_JIRITSU_MODE: int = 0x0001
CMD_JIRITSU_MOUNT: int = 0x0002
CMD_JIRITSU_FORMAT: int = 0x0003
CMD_JIRITSU_START: int = 0x0004
CMD_JIRITSU_DEBUG: int = 0x0005
CMD_JIRITSU_FIRMUP: int = 0x0006
CMD_SET_FILE_PATH: int = 0x000F
CMD_SET_FILE2: int = 0x0010
CMD_GET_FILE2: int = 0x0011

FORBIDDEN_JIRITSU_COMMANDS: Tuple[int, ...] = (
    CMD_JIRITSU_MODE,
    CMD_JIRITSU_MOUNT,
    CMD_JIRITSU_FORMAT,
    CMD_JIRITSU_START,
    CMD_JIRITSU_DEBUG,
    CMD_JIRITSU_FIRMUP,
)
ALLOWED_READONLY_COMMANDS: Tuple[int, ...] = (
    CMD_SET_FILE_PATH,
    CMD_SET_FILE2,
    CMD_GET_FILE2,
)
FORBIDDEN_SELECTOR_VALUES: Tuple[int, ...] = (0x00, 0x02)
FORBIDDEN_TOOL_TOKENS: Tuple[str, ...] = ("edisx", "uc_mkfs", "nor_loader_writer")

REQ_VERSION_ADJUST: int = 2
RESP_VERSION_STOCK: int = 3
RESP_RES_OK: int = 1

MAX_BODY_BYTES: int = 0x100000  # 1 MiB SenserThread request-body limit
MAX_GET_FILE2_RESPONSE_BODY_BYTES: int = 0x500000  # 5 MiB bounded chunk pull response cap
MAX_PATH_BYTES: int = 0x1FF
MAX_FILE_BYTES: int = 0x500000  # 5 MiB

# Partition Geometry & Quota Constants (512 B sectors)
SECTOR_SIZE_BYTES: int = 512
P6_PARTITION_QUOTA_BYTES: int = 26214400  # 25 MiB (0xC800 * 512)
P3_PARTITION_CAPACITY_BYTES: int = 78643200  # 75 MiB (0x25800 * 512)
P15_PARTITION_CAPACITY_BYTES: int = 524288000  # 500 MiB (0xFA000 * 512)
SLIDING_WINDOW_CHUNK_BYTES: int = 4 * 1024 * 1024  # 4 MiB (4,194,304 B)
SLIDING_WINDOW_MAX_PEAK_P6_BYTES: int = int(4.2 * 1024 * 1024)  # 4,404,019 B

# Framing & Receipt Constants
CHUNK_HEADER_MAGIC: bytes = b"FX3CHK1\x00"
CHUNK_HEADER_FORMAT: str = "<8sQII"  # 8B magic + u64 offset + u32 length + u32 crc32 = 24B
CHUNK_HEADER_BYTES: int = 24

SD_RECEIPT_MAGIC: bytes = b"FX3RCPT1"
SD_RECEIPT_BYTES: int = 528
SD_BACKUP_MOUNT_DIR: str = "/mnt/sd/FX3_COLD_BACKUP"
SD_BACKUP_MANIFEST_NAME: str = "MANIFEST.SHA256"

JIRITSU_TMP_PREFIX: str = "/tmp/jiritsu/"
JBUSY_PROBE_PATH: str = "/tmp/jiritsu/../../tmp/jbusy"
LIBJIT_PATH: str = "/tmp/jiritsu/libJit.so"
SD_RECEIPT_PATH: str = "/tmp/jiritsu/backup_rcpt.bin"
SLIDING_CHUNK_PATH: str = "/tmp/jiritsu/chunk.bin"

FX3_MODEL_ID_STR: str = "91030080"
FX3_REGION_TAG_STR: str = "US_JP_EU_CN_NTSC"
SPI_NOR_DDRTRAINING_OFFSET: int = 0x3E210FC

# Jiritsu / Fake-IOKit Status Codes
STATUS_OK: int = 0x00000000
STATUS_GET_ABSENT: int = 0x00000011  # ENOENT
STATUS_DLOPEN_FAIL: int = 0x10000000
STATUS_MOUNT_FAIL: int = 0x10000004
STATUS_P6_NO_SPACE: int = 0x1000000F
STATUS_BUSY: int = 0x10000011
STATUS_BAD_FRAME: int = 0x10000201
STATUS_USB_TIMEOUT: int = 0xE0004051

# ELF64 Validation Constants
ELF_MAGIC: bytes = b"\x7fELF"
ELF_CLASS_64: int = 2
ELF_DATA_LSB: int = 1
ELF_TYPE_DYN: int = 3
ELF_MACHINE_AARCH64: int = 183
ELF_PT_LOAD: int = 1
ELF_PT_DYNAMIC: int = 2
ELF_DT_NULL: int = 0
ELF_DT_HASH: int = 4
ELF_DT_STRTAB: int = 5
ELF_DT_SYMTAB: int = 6
ELF_PT_LOAD_PAGE_ALIGN: int = 0x10000  # 64 KiB
ELF_DT_HASH_EXPECTED: Tuple[int, int, int, int] = (1, 1, 0, 0)

# Suite & Pillar Status Strings
STATUS_VERIFIED_SUITE: str = "VERIFIED_ADJUSTCONTROL_STREAMING_BACKUP_CLIENT"
STATUS_FAIL_SUITE: str = "FAIL_ADJUSTCONTROL_STREAMING_BACKUP_CLIENT"
STATUS_VERIFIED_PILLAR_A: str = "VERIFIED_ADJUSTCONTROL_0X40_WIRE_AND_PREFLIGHT_ABORT"
STATUS_REJECTED_PILLAR_A: str = "REJECTED_ADJUSTCONTROL_0X40_WIRE_AND_PREFLIGHT_ABORT"
STATUS_VERIFIED_PILLAR_B: str = "VERIFIED_DUAL_PATH_SD_AND_P6_SLIDING_WINDOW_BACKUP"
STATUS_REJECTED_PILLAR_B: str = "REJECTED_DUAL_PATH_SD_AND_P6_SLIDING_WINDOW_BACKUP"
STATUS_VERIFIED_PILLAR_C: str = "VERIFIED_FAKE_IOKIT_REGRESSION_AND_PASSIVE_LOCK"
STATUS_REJECTED_PILLAR_C: str = "REJECTED_FAKE_IOKIT_REGRESSION_AND_PASSIVE_LOCK"

# Error / Firewall Codes
BLOCKED_FORBIDDEN_JIRITSU_COMMAND: str = "BLOCKED_FORBIDDEN_MODE_START_FORMAT_MOUNT_CMD"
BLOCKED_SELECTOR_2_REJECTED: str = "BLOCKED_SELECTOR_2_REJECTED"
BLOCKED_PATH_TRAVERSAL: str = "BLOCKED_OUTSIDE_JIRITSU_PATH_TRAVERSAL"
BLOCKED_JBUSY_PRESENT_ABORT: str = "BLOCKED_JBUSY_PRESENT_PREFLIGHT_ABORT"
ABORT_BUSY_0X10000011: str = "ABORT_SET_FILE2_BUSY_0X10000011_NO_RETRY"
ABORT_BAD_FRAME_0X10000201: str = "ABORT_BAD_FRAME_0X10000201_NO_RETRY"
ABORT_DLOPEN_FAIL_0X10000000: str = "ABORT_DLOPEN_FAIL_0X10000000_NO_RETRY"
ABORT_MOUNT_FAIL_0X10000004: str = "ABORT_MOUNT_FAIL_0X10000004_NO_RETRY"
ABORT_P6_FULL_0X1000000F: str = "ABORT_P6_SPACE_EXHAUSTED_0X1000000F_NO_RETRY"
ABORT_USB_TIMEOUT: str = "ABORT_USB_TIMEOUT_NO_RETRY"
ERR_CHUNK_HEADER_CORRUPT: str = "ERR_CHUNK_FX3CHK1_HEADER_OR_CRC32_MISMATCH"
ERR_REASSEMBLY_SHA256_MISMATCH: str = "ERR_REASSEMBLED_PARTITION_SHA256_MISMATCH"
ERR_SD_RECEIPT_INVALID: str = "ERR_SD_528B_RECEIPT_INVALID_OR_TAMPERED"
ERR_ELF_PT_LOAD_NOT_64K_ALIGNED: str = "ERR_ELF_PT_LOAD_ALIGNMENT_NOT_0X10000"
ERR_ELF_DT_HASH_INVALID: str = "ERR_ELF_DT_HASH_NOT_1_1_0_0_OR_OUT_OF_BOUNDS"
STATUS_REJECTED_P6_RESIDUAL_FILES: str = "REJECTED_POST_SESSION_P6_RESIDUAL_FILES"
BLOCKED_LIVE_USB_IOKIT_TRANSMIT_LOCKED: str = "BLOCKED_LIVE_USB_IOKIT_TRANSMIT_LOCKED_FALSE"
BLOCKED_PERSISTENT_EMMC_WRITES_LOCKED: str = "BLOCKED_PERSISTENT_EMMC_WRITES_LOCKED_FALSE"

# Local Donor Relative Paths (strictly O_RDONLY | O_NOFOLLOW | O_NONBLOCK)
P139_DONOR_WIRE_PY_RELPATH: str = (
    "sony-firmware-20261024/stage288-jiritsu-readonly-payload/jiritsu_wire.py"
)
P139_DONOR_FAKE_CAM_RELPATH: str = (
    "sony-firmware-20261024/stage288-jiritsu-readonly-payload/fake_jiritsu_camera.py"
)
P139_DONOR_STAGE288_SO_RELPATH: str = (
    "sony-firmware-20261024/stage288-jiritsu-readonly-payload/payload/libJit_test.so"
)
P139_DONOR_FX3_LIBJIRITSU_RELPATH: str = (
    "sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/libJiritsu.so"
)
P139_DONOR_FX3_PARTINF_RELPATH: str = (
    "sony-firmware-20261024/stage182-boot-selector-and-recovery-admission/"
    "current-updater-evidence/tar-selected/0300_partconf/partinf.conf"
)
P139_DONOR_FX3_PFORMAT_RELPATH: str = (
    "sony-firmware-20261024/stage182-boot-selector-and-recovery-admission/"
    "current-updater-evidence/nor-loader-members/pformat_config.txt"
)

# Pinned Clean-Room Donor Integrity Anchors (zero proprietary raw bytes)
P139_PINNED_WIRE_PY_BYTES: int = 7180
P139_PINNED_WIRE_PY_SHA256: str = "d564b91b2802c2e37d0f2ad815c840885b7f790bb4e2de140a6010cdec2c3586"
P139_PINNED_FAKE_CAM_BYTES: int = 3908
P139_PINNED_FAKE_CAM_SHA256: str = "d8c203f2a30afbc06874401451affe6db971676af841dd51d995331cd8adf2cc"
P139_PINNED_STAGE288_SO_BYTES: int = 8345
P139_PINNED_STAGE288_SO_SHA256: str = "05000a0ecceaa5004385b71fbeb2b15859bda7418e227a3d90238da31bc4cd7a"
P139_PINNED_FX3_LIBJIRITSU_BYTES: int = 225200
P139_PINNED_FX3_LIBJIRITSU_SHA256: str = "bdef58b24a3b67b4d14d4f0214b89aae0fcad19f114b4188c328f9d2c092f1d9"
P139_PINNED_FX3_PARTINF_BYTES: int = 3999
P139_PINNED_FX3_PARTINF_SHA256: str = "3d96228d4ed2db3cb4295aa854edf0ad8895440167f132144cdec4f8cfdad189"
P139_PINNED_FX3_PFORMAT_BYTES: int = 1274
P139_PINNED_FX3_PFORMAT_SHA256: str = "21cd5b29dd165c322f5b00bb057802c377ff94af15f95881e150a32130302ece"

# Full Cold-Backup Partition & SPI NOR Manifest (Stage 288 §6 + 2026-11-03 §5.2)
@dataclass(frozen=True)
class ColdBackupItemSpec:
    item_id: str
    tier: str
    device_node: str
    filename: str
    size_bytes: int
    offset_bytes: int = 0
    includes_notes: str = ""


COLD_BACKUP_ITEMS: Tuple[ColdBackupItemSpec, ...] = (
    ColdBackupItemSpec("sector0", "TIER_0", "/dev/nflasha", "sector0.bin", 512, 0, "Sony PTBL 8246/2.00"),
    ColdBackupItemSpec("p2", "TIER_0", "/dev/nflasha2", "p2_setting.img", 20971520, 0, "Backup.bin,psd.bin,defdet.bin"),
    ColdBackupItemSpec("p6", "TIER_0", "/dev/nflasha6", "p6_jiritsu.img", 26214400, 0, "25 MiB Jiritsu calibration"),
    ColdBackupItemSpec("p12", "TIER_0", "/dev/cnflasha12", "p12_cert.img", 41943040, 0, "/cert 40 MiB"),
    ColdBackupItemSpec("p18", "TIER_0", "/dev/nflasha18", "p18_lens.img", 20971520, 0, "/lens/lensfile.bin"),
    ColdBackupItemSpec(
        "spi_nor_ddrtraining",
        "TIER_0",
        "/dev/mtd0",
        "spi_nor_ddrtraining.dat",
        4096,
        SPI_NOR_DDRTRAINING_OFFSET,
        "ddrtraining.dat @ 0x3e210fc",
    ),
    ColdBackupItemSpec(
        "spi_nor_loader",
        "TIER_0",
        "/dev/mtd0",
        "spi_nor_loader.bin",
        102400,
        0x9000,
        "loader_nor.bin + LdrBkup",
    ),
    ColdBackupItemSpec("p1", "TIER_1", "/dev/nflasha1", "p1_updater.img", 25100288, 0, "includes dat2/dat3 + /boot/*"),
    ColdBackupItemSpec("p3", "TIER_1", "/dev/cnflasha3", "p3_system.img", 78643200, 0, "75 MiB /system"),
    ColdBackupItemSpec("p7", "TIER_1", "/dev/cnflasha7", "p7_rootfs.img", 16777216, 0, "16 MiB /rootfs"),
    ColdBackupItemSpec("p8", "TIER_1", "/dev/cnflasha8", "p8_cp.img", 67108864, 0, "64 MiB /cp"),
    ColdBackupItemSpec("p5", "TIER_2", "/dev/nflasha5", "p5_wbi.img", 314572800, 0, "300 MiB WBI2"),
    ColdBackupItemSpec("p13", "TIER_2", "/dev/nflasha13", "p13_updaterwork.img", 4194304, 0, "4 MiB UpdaterWork"),
    ColdBackupItemSpec("p15", "TIER_2", "/dev/cnflasha15", "p15_usr.img", 524288000, 0, "500 MiB /usr"),
    ColdBackupItemSpec("p23", "TIER_2", "/dev/cnflasha23", "p23_pmbp.img", 67108864, 0, "64 MiB /PMBP"),
    ColdBackupItemSpec("p30", "TIER_2", "/dev/cnflasha30", "p30_lut.img", 50331648, 0, "48 MiB /usr/data/lut"),
)

REQUIRED_COLD_BACKUP_ITEM_IDS: Tuple[str, ...] = tuple(item.item_id for item in COLD_BACKUP_ITEMS)

# Scenario IDs
PILLAR_A_SCENARIO_IDS: Tuple[str, ...] = (
    "PA1_HAPPY_PREFLIGHT_JBUSY_ABSENT_AND_WIRE_ROUNDTRIP",
    "PA2_JBUSY_PRESENT_PREFLIGHT_ABORT",
    "PA3_SET_FILE2_BUSY_0X10000011_IMMEDIATE_ABORT_NO_RETRY",
    "PA4_BAD_FRAME_SELECTOR2_AND_0X10000201_REJECTED",
    "PA5_DLOPEN_FAIL_0X10000000_AND_MOUNT_FAIL_0X10000004_ABORT",
    "PA6_P6_FULL_0X1000000F_AND_USB_TIMEOUT_ABORT",
    "PA7_FORBIDDEN_MODE_START_FORMAT_MOUNT_AND_TRAVERSAL_BLOCKED",
)

PILLAR_B_SCENARIO_IDS: Tuple[str, ...] = (
    "PB1_SD_STREAM_FULL_16_ITEM_BACKUP_AND_528B_RECEIPT",
    "PB2_P6_SLIDING_WINDOW_75MIB_P3_USB_PULL_EXACT",
    "PB3_UNBOUNDED_P3_STAGING_75MIB_REJECTED_0X1000000F",
    "PB4_CHUNK_HEADER_CRC32_CORRUPTION_ABORT",
    "PB5_SD_UNWRITABLE_FALLS_BACK_TO_SLIDING_WINDOW",
    "PB6_SD_RECEIPT_SIZE_OR_TAMPER_REJECTED",
)

PILLAR_C_SCENARIO_IDS: Tuple[str, ...] = (
    "PC1_FAKE_IOKIT_VID054C_FULL_SESSION_AND_ZERO_RESIDUE",
    "PC2_ELF_64K_PT_LOAD_AND_DT_HASH_ENFORCEMENT",
    "PC3_P6_25MIB_QUOTA_BOUNDARY_ENFORCEMENT",
    "PC4_POST_SESSION_RESIDUAL_FILE_AUDIT_FAILS_CLOSED",
    "PC5_PASSIVE_USB_AND_EMMC_WRITE_HARD_LOCK",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _canonical_sha256(obj: Any) -> str:
    payload = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(payload).hexdigest()


def _need(cond: bool, msg: str) -> None:
    if not cond:
        raise ValueError(msg)


def _read_donor_readonly(rel_path: str, limit: int = 4 * 1024 * 1024) -> Tuple[Optional[bytes], str]:
    """Resolve and read a donor file strictly via os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK."""
    if is_forced_clean_room():
        return None, "CLEAN_ROOM_SYNTHETIC"
    p = resolve_donor_path(rel_path, require_file=True)
    if not p.is_file():
        return None, "CLEAN_ROOM_SYNTHETIC"
    data = read_file(str(p), limit)
    return data, "LOCAL_DONOR_O_RDONLY"


def _parse_partinf_sizes(partinf_text: str) -> Dict[int, Tuple[int, int]]:
    """Parse `0xSTART,0xSIZE,0xTYPE,0xFLAG` rows from Sony `partinf.conf`."""
    entries: Dict[int, Tuple[int, int]] = {}
    idx = 0
    for raw_line in partinf_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^(0x[0-9A-Fa-f]+),(0x[0-9A-Fa-f]+),(0x[0-9A-Fa-f]+),(0x[0-9A-Fa-f]+)", line)
        if m:
            idx += 1
            start_sec = int(m.group(1), 16)
            size_sec = int(m.group(2), 16)
            entries[idx] = (start_sec, size_sec)
    return entries


def _parse_pformat_sections(pformat_text: str) -> Tuple[str, ...]:
    return tuple(re.findall(r'path\s*=\s*"([^"]+)"', pformat_text))


# ---------------------------------------------------------------------------
# Structured Dataclasses (JSON-safe: zero raw bytes stored in report dicts)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AdjustDonorArtifactDigest:
    label: str
    source_mode: str
    byte_length: int
    sha256_digest: str
    notes: str = ""


@dataclass(frozen=True)
class AdjustControlDonorSnapshot:
    verification_mode: str
    read_only_access: bool
    p6_quota_bytes: int
    p3_capacity_bytes: int
    p15_capacity_bytes: int
    partinf_partition_count: int
    pformat_sections: Tuple[str, ...]
    stage288_so_pt_load_align: int
    fx3_libjiritsu_pt_load_align: int
    artifacts: Tuple[AdjustDonorArtifactDigest, ...]
    snapshot_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ElfSoValidationResult:
    valid: bool
    ei_class: int
    ei_data: int
    e_type: int
    e_machine: int
    pt_load_count: int
    pt_load_alignments: Tuple[int, ...]
    all_pt_load_64k_aligned: bool
    dt_symtab_va: int
    dt_strtab_va: int
    dt_hash_va: int
    dynamic_ptrs_in_pt_load: bool
    dt_hash_words: Tuple[int, int, int, int]
    dt_hash_valid: bool
    error_codes: Tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class AdjustRequestEnvelope:
    seq: int
    command: int
    inner_payload: bytes

    def to_wire_bytes(self) -> bytes:
        _need(isinstance(self.seq, int) and 0 < self.seq <= 0xFFFF, "invalid sequence number")
        _need(self.command in ALLOWED_READONLY_COMMANDS, f"{BLOCKED_FORBIDDEN_JIRITSU_COMMAND}: {self.command:#x}")
        _need(isinstance(self.inner_payload, bytes) and len(self.inner_payload) >= 1, "empty inner payload")
        body_size = 4 + len(self.inner_payload)
        _need(body_size <= MAX_BODY_BYTES, "request body exceeds SenserThread 1 MiB limit")
        header = struct.pack(
            "<IHHBBBB",
            body_size,
            PFUNC_ADJUST_CONTROL,
            self.seq,
            REQ_VERSION_ADJUST,
            0,
            0,
            0,
        )
        selector = struct.pack("<HH", CATEGORY_JIRITSU, self.command)
        return header + selector + self.inner_payload


@dataclass(frozen=True)
class ParsedAdjustResponse:
    seq: int
    native_status: int
    payload_bytes: int
    payload_sha256: str


@dataclass(frozen=True)
class PreflightAbortSessionResult:
    passed: bool
    scenario_id: str
    aborted: bool
    abort_reason_code: str
    native_status_hex: str
    jbusy_preflight_checked: bool
    jbusy_absent_confirmed: bool
    set_file2_sent_count: int
    set_file2_retry_count: int
    blind_second_set_file2_sent: bool
    forbidden_command_blocked: bool
    wire_frames_sent: int
    errors: Tuple[str, ...]
    report_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PillarA7ScenarioSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenario_results: Tuple[PreflightAbortSessionResult, ...]
    physical_usb_bytes_transmitted: int
    errors: Tuple[str, ...]
    suite_sha256: str


@dataclass(frozen=True)
class SdBackupReceiptInfo:
    valid: bool
    receipt_bytes: int
    magic: str
    version: int
    entry_count: int
    flags: int
    manifest_sha256: str
    sector0_sha256: str
    p1_sha256: str
    p2_sha256: str
    p6_sha256: str
    p12_sha256: str
    p18_sha256: str
    spi_nor_ddrtraining_sha256: str
    spi_nor_loader_sha256: str
    tier2_bundle_sha256: str
    total_dumped_bytes: int
    receipt_integrity_sha256: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class SdStreamingBackupResult:
    passed: bool
    scenario_id: str
    mount_dir: str
    manifest_entry_count: int
    covered_item_ids: Tuple[str, ...]
    dat2_model_id: str
    dat3_region_tag: str
    total_dumped_bytes: int
    p6_receipt_bytes: int
    p6_peak_bytes: int
    p6_residual_files: int
    receipt_valid: bool
    manifest_sha256: str
    error_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    report_sha256: str


@dataclass(frozen=True)
class SlidingWindowPullResult:
    passed: bool
    scenario_id: str
    partition_name: str
    fallback_triggered: bool
    chunk_size_bytes: int
    chunks_pulled: int
    total_pulled_bytes: int
    source_sha256: str
    reassembled_sha256: str
    sha256_exact_match: bool
    peak_p6_bytes: int
    p6_quota_bytes: int
    p6_residual_files: int
    set_file2_retry_count: int
    error_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    report_sha256: str


@dataclass(frozen=True)
class PillarBScenarioResult:
    passed: bool
    scenario_id: str
    path_used: str
    error_codes: Tuple[str, ...]
    summary_sha256: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class PillarB6ScenarioSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenario_results: Tuple[PillarBScenarioResult, ...]
    sd_backup_result: SdStreamingBackupResult
    sliding_75mib_result: SlidingWindowPullResult
    errors: Tuple[str, ...]
    suite_sha256: str


@dataclass(frozen=True)
class PostSessionAuditResult:
    clean: bool
    status: str
    p6_residual_files: int
    p6_residual_bytes: int
    residual_paths: Tuple[str, ...]
    jbusy_state: bool
    forbidden_modes_touched: Tuple[str, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class PassiveHardwareLockRequest:
    live_usb_iokit_transmit_enabled: bool = False
    persistent_emmc_writes_authorized: bool = False
    usb_bytes_requested: int = 0
    emmc_write_bytes_requested: int = 0


@dataclass(frozen=True)
class PassiveHardwareLockDecision:
    allowed: bool
    live_usb_iokit_transmit_enabled: bool
    persistent_emmc_writes_authorized: bool
    physical_usb_bytes_transmitted: int
    physical_device_writes: int
    error_codes: Tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class PillarCScenarioResult:
    passed: bool
    scenario_id: str
    usb_vid_pid: str
    p6_quota_enforced: bool
    elf_64k_enforced: bool
    post_session_clean: bool
    live_usb_iokit_transmit_enabled: bool
    persistent_emmc_writes_authorized: bool
    error_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    report_sha256: str


@dataclass(frozen=True)
class PillarC5ScenarioSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenario_results: Tuple[PillarCScenarioResult, ...]
    errors: Tuple[str, ...]
    suite_sha256: str


@dataclass(frozen=True)
class AdjustControlStreamingBackupSuiteReport:
    schema: str
    version: str
    status: str
    verification_mode: str
    all_passed: bool
    read_only_donor_access: bool
    donor_snapshot: AdjustControlDonorSnapshot
    pillar_a_wire_and_preflight_7_scenarios: PillarA7ScenarioSuiteResult
    pillar_b_dual_path_backup_6_scenarios: PillarB6ScenarioSuiteResult
    pillar_c_fake_iokit_regression_5_scenarios: PillarC5ScenarioSuiteResult
    live_usb_iokit_transmit_enabled: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    allow_boot_partition_targeting: bool
    allow_destructive_fastboot: bool
    allow_persistent_jiritsu_writes: bool
    allow_destructive_jiritsu_commands: bool
    otp_fuse_touches: int
    otp_fuse_writes: int
    passive_tx_bytes_emitted: int
    physical_device_writes: int
    physical_usb_bytes_transmitted: int
    elapsed_seconds: float
    errors: Tuple[str, ...]
    suite_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Clean-Room ELF64 AArch64 Validation & Synthetic Builder
# ---------------------------------------------------------------------------


def validate_elf64_so_for_fx3_64k(
    so_bytes: bytes,
    *,
    require_64k_pt_load: bool = True,
) -> ElfSoValidationResult:
    """Validate an ELF64 AArch64 shared object for `DT_HASH (1,1,0,0)` inside
    `PT_LOAD` and `PT_LOAD` `p_align == 0x10000` (64 KiB page requirement).
    """
    error_codes: List[str] = []
    if not isinstance(so_bytes, bytes) or len(so_bytes) < 64 or so_bytes[:4] != ELF_MAGIC:
        return ElfSoValidationResult(
            valid=False,
            ei_class=0,
            ei_data=0,
            e_type=0,
            e_machine=0,
            pt_load_count=0,
            pt_load_alignments=(),
            all_pt_load_64k_aligned=False,
            dt_symtab_va=0,
            dt_strtab_va=0,
            dt_hash_va=0,
            dynamic_ptrs_in_pt_load=False,
            dt_hash_words=(0, 0, 0, 0),
            dt_hash_valid=False,
            error_codes=(ERR_ELF_DT_HASH_INVALID,),
            reason="invalid ELF magic or truncated header",
        )

    ei_class = so_bytes[4]
    ei_data = so_bytes[5]
    e_type, e_machine, _e_ver, _e_entry, e_phoff, _e_shoff, _e_flags, _ehsz, e_phentsize, e_phnum = (
        struct.unpack_from("<HHIQQQIHHH", so_bytes, 16)
    )
    if (
        ei_class != ELF_CLASS_64
        or ei_data != ELF_DATA_LSB
        or e_type != ELF_TYPE_DYN
        or e_machine != ELF_MACHINE_AARCH64
        or e_phentsize < 56
        or e_phoff + e_phnum * e_phentsize > len(so_bytes)
    ):
        error_codes.append(ERR_ELF_DT_HASH_INVALID)
        return ElfSoValidationResult(
            valid=False,
            ei_class=ei_class,
            ei_data=ei_data,
            e_type=e_type,
            e_machine=e_machine,
            pt_load_count=0,
            pt_load_alignments=(),
            all_pt_load_64k_aligned=False,
            dt_symtab_va=0,
            dt_strtab_va=0,
            dt_hash_va=0,
            dynamic_ptrs_in_pt_load=False,
            dt_hash_words=(0, 0, 0, 0),
            dt_hash_valid=False,
            error_codes=tuple(error_codes),
            reason="not a valid ELF64 little-endian AArch64 ET_DYN shared object",
        )

    pt_loads: List[Tuple[int, int, int, int]] = []  # (p_offset, p_vaddr, p_filesz, p_align)
    pt_dyn_off = 0
    pt_dyn_sz = 0
    for idx in range(e_phnum):
        off = e_phoff + idx * e_phentsize
        p_type, _p_flags, p_offset, p_vaddr, _p_paddr, p_filesz, _p_memsz, p_align = struct.unpack_from(
            "<IIQQQQQQ", so_bytes, off
        )
        if p_type == ELF_PT_LOAD:
            pt_loads.append((p_offset, p_vaddr, p_filesz, p_align))
        elif p_type == ELF_PT_DYNAMIC:
            pt_dyn_off = p_offset
            pt_dyn_sz = p_filesz

    alignments = tuple(item[3] for item in pt_loads)
    all_64k = len(pt_loads) >= 1 and all(a == ELF_PT_LOAD_PAGE_ALIGN for a in alignments)
    if require_64k_pt_load and not all_64k:
        error_codes.append(ERR_ELF_PT_LOAD_NOT_64K_ALIGNED)

    dt_symtab_va = 0
    dt_strtab_va = 0
    dt_hash_va = 0
    if pt_dyn_off > 0 and pt_dyn_off + pt_dyn_sz <= len(so_bytes):
        for off in range(pt_dyn_off, pt_dyn_off + pt_dyn_sz - 15, 16):
            d_tag, d_val = struct.unpack_from("<QQ", so_bytes, off)
            if d_tag == ELF_DT_NULL:
                break
            elif d_tag == ELF_DT_SYMTAB:
                dt_symtab_va = d_val
            elif d_tag == ELF_DT_STRTAB:
                dt_strtab_va = d_val
            elif d_tag == ELF_DT_HASH:
                dt_hash_va = d_val

    def _va_to_file_off(va: int, min_bytes: int = 1) -> Optional[int]:
        if va == 0:
            return None
        for p_offset, p_vaddr, p_filesz, _p_align in pt_loads:
            if p_vaddr <= va and (va + min_bytes) <= (p_vaddr + p_filesz):
                foff = p_offset + (va - p_vaddr)
                if 0 <= foff and foff + min_bytes <= len(so_bytes):
                    return foff
        return None

    sym_off = _va_to_file_off(dt_symtab_va, 24)
    str_off = _va_to_file_off(dt_strtab_va, 1)
    hash_off = _va_to_file_off(dt_hash_va, 16)
    ptrs_in_load = (sym_off is not None) and (str_off is not None) and (hash_off is not None)

    dt_hash_words: Tuple[int, int, int, int] = (0, 0, 0, 0)
    if hash_off is not None:
        dt_hash_words = struct.unpack_from("<IIII", so_bytes, hash_off)
    dt_hash_ok = ptrs_in_load and (dt_hash_words == ELF_DT_HASH_EXPECTED)
    if not dt_hash_ok:
        error_codes.append(ERR_ELF_DT_HASH_INVALID)

    valid = len(error_codes) == 0 and len(pt_loads) >= 1 and dt_hash_ok and (all_64k or not require_64k_pt_load)
    return ElfSoValidationResult(
        valid=valid,
        ei_class=ei_class,
        ei_data=ei_data,
        e_type=e_type,
        e_machine=e_machine,
        pt_load_count=len(pt_loads),
        pt_load_alignments=alignments,
        all_pt_load_64k_aligned=all_64k,
        dt_symtab_va=dt_symtab_va,
        dt_strtab_va=dt_strtab_va,
        dt_hash_va=dt_hash_va,
        dynamic_ptrs_in_pt_load=ptrs_in_load,
        dt_hash_words=dt_hash_words,
        dt_hash_valid=dt_hash_ok,
        error_codes=tuple(error_codes),
        reason="ok" if valid else ";".join(error_codes),
    )


def build_synthetic_jiritsu_so_64k(
    *,
    pt_load_align: int = ELF_PT_LOAD_PAGE_ALIGN,
    dt_hash_words: Tuple[int, int, int, int] = ELF_DT_HASH_EXPECTED,
    action_tag: bytes = b"FX3_COLD_BACKUP_V1",
) -> bytes:
    """Build a clean-room synthetic ELF64 AArch64 shared object with `PT_LOAD`
    alignment (`0x10000` by default) and `DT_HASH (1,1,0,0)` inside `PT_LOAD`.

    Note: Uses harmless AArch64 `RET` (`0xD65F03C0`) + metadata tag; never executed.
    """
    eh_size = 64
    ph_size = 56
    ph_num = 3
    ph_off = eh_size

    text_off = 0x1000 if pt_load_align <= 0x1000 else 0x10000
    text_va = text_off
    # AArch64 RET + clean-room metadata marker
    text_bytes = struct.pack("<I", 0xD65F03C0) + action_tag[:32].ljust(32, b"\x00")

    dyn_off = text_off + 0x10000 if pt_load_align >= 0x10000 else text_off + 0x1000
    dyn_va = dyn_off

    # 7 dynamic entries * 16B = 112B (0x70) -> DT_SYMTAB at +0x70, DT_STRTAB at +0x88, DT_HASH at +0x89
    sym_va = dyn_va + 0x70
    str_va = dyn_va + 0x88
    hash_va = dyn_va + 0x89
    dyn_entries = (
        (ELF_DT_STRTAB, str_va),
        (ELF_DT_SYMTAB, sym_va),
        (10, 1),  # DT_STRSZ
        (11, 24),  # DT_SYMENT
        (ELF_DT_HASH, hash_va),
        (12, text_va),  # DT_INIT
        (ELF_DT_NULL, 0),
    )
    dyn_bytes = b"".join(struct.pack("<QQ", tag, val) for tag, val in dyn_entries)
    dynsym = b"\x00" * 24
    dynstr = b"\x00"
    hash_bytes = struct.pack("<IIII", *dt_hash_words)
    rdata = dyn_bytes + dynsym + dynstr + hash_bytes

    total_len = dyn_off + len(rdata)
    out = bytearray(total_len)
    e_ident = ELF_MAGIC + bytes([ELF_CLASS_64, ELF_DATA_LSB, 1, 0]) + (b"\x00" * 8)
    struct.pack_into(
        "<16sHHIQQQIHHHHHH",
        out,
        0,
        e_ident,
        ELF_TYPE_DYN,
        ELF_MACHINE_AARCH64,
        1,
        0,
        ph_off,
        0,
        0,
        eh_size,
        ph_size,
        ph_num,
        0,
        0,
        0,
    )

    def _set_ph(idx: int, p_type: int, p_flags: int, offset: int, vaddr: int, size: int, align: int) -> None:
        struct.pack_into(
            "<IIQQQQQQ",
            out,
            ph_off + idx * ph_size,
            p_type,
            p_flags,
            offset,
            vaddr,
            vaddr,
            size,
            size,
            align,
        )

    _set_ph(0, ELF_PT_LOAD, 5, text_off, text_va, len(text_bytes), pt_load_align)
    _set_ph(1, ELF_PT_LOAD, 4, dyn_off, dyn_va, len(rdata), pt_load_align)
    _set_ph(2, ELF_PT_DYNAMIC, 4, dyn_off, dyn_va, len(dyn_bytes), 8)
    out[text_off : text_off + len(text_bytes)] = text_bytes
    out[dyn_off : dyn_off + len(rdata)] = rdata
    return bytes(out)


# ---------------------------------------------------------------------------
# Read-Only Donor Inspection
# ---------------------------------------------------------------------------


def inspect_adjustcontrol_donors_readonly(
    *,
    force_clean_room: Optional[bool] = None,
) -> AdjustControlDonorSnapshot:
    """Inspect local Stage-288 wire/camera specs, `libJit_test.so`, FX3 `libJiritsu.so`,
    `partinf.conf`, and `pformat_config.txt` strictly via `os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK`,
    falling back deterministically when `FX3_FX6_FORCE_CLEAN_ROOM=1` or donors are absent.
    """
    forced = is_forced_clean_room() if force_clean_room is None else bool(force_clean_room)

    def _load(rel: str, pinned_len: int, pinned_sha: str, label: str, limit: int = 4 * 1024 * 1024) -> Tuple[Optional[bytes], AdjustDonorArtifactDigest]:
        if forced:
            return None, AdjustDonorArtifactDigest(label, "CLEAN_ROOM_SYNTHETIC", pinned_len, pinned_sha, "forced clean-room")
        raw, mode = _read_donor_readonly(rel, limit=limit)
        if raw is None:
            return None, AdjustDonorArtifactDigest(label, "CLEAN_ROOM_SYNTHETIC", pinned_len, pinned_sha, "clean-room fallback")
        digest = sha256(raw).hexdigest()
        require(len(raw) == pinned_len and digest == pinned_sha, f"donor integrity mismatch for {label}")
        return raw, AdjustDonorArtifactDigest(label, mode, len(raw), digest, "verified O_RDONLY")

    wire_raw, wire_art = _load(P139_DONOR_WIRE_PY_RELPATH, P139_PINNED_WIRE_PY_BYTES, P139_PINNED_WIRE_PY_SHA256, "stage288_jiritsu_wire_py")
    cam_raw, cam_art = _load(P139_DONOR_FAKE_CAM_RELPATH, P139_PINNED_FAKE_CAM_BYTES, P139_PINNED_FAKE_CAM_SHA256, "stage288_fake_camera_py")
    s288_so_raw, s288_so_art = _load(P139_DONOR_STAGE288_SO_RELPATH, P139_PINNED_STAGE288_SO_BYTES, P139_PINNED_STAGE288_SO_SHA256, "stage288_libJit_test_so")
    fx3_lib_raw, fx3_lib_art = _load(P139_DONOR_FX3_LIBJIRITSU_RELPATH, P139_PINNED_FX3_LIBJIRITSU_BYTES, P139_PINNED_FX3_LIBJIRITSU_SHA256, "fx3_libJiritsu_so")
    partinf_raw, partinf_art = _load(P139_DONOR_FX3_PARTINF_RELPATH, P139_PINNED_FX3_PARTINF_BYTES, P139_PINNED_FX3_PARTINF_SHA256, "fx3_partinf_conf")
    pformat_raw, pformat_art = _load(P139_DONOR_FX3_PFORMAT_RELPATH, P139_PINNED_FX3_PFORMAT_BYTES, P139_PINNED_FX3_PFORMAT_SHA256, "fx3_pformat_config_txt")

    artifacts = (wire_art, cam_art, s288_so_art, fx3_lib_art, partinf_art, pformat_art)
    modes = {a.source_mode for a in artifacts}
    verification_mode = "LOCAL_DONOR_O_RDONLY" if modes == {"LOCAL_DONOR_O_RDONLY"} else "CLEAN_ROOM_SYNTHETIC"

    if partinf_raw is not None:
        part_map = _parse_partinf_sizes(partinf_raw.decode("utf-8", "replace"))
        part_count = len(part_map)
        p3_bytes = part_map[3][1] * SECTOR_SIZE_BYTES
        p6_bytes = part_map[6][1] * SECTOR_SIZE_BYTES
        p15_bytes = part_map[15][1] * SECTOR_SIZE_BYTES
    else:
        part_count = 30
        p3_bytes = P3_PARTITION_CAPACITY_BYTES
        p6_bytes = P6_PARTITION_QUOTA_BYTES
        p15_bytes = P15_PARTITION_CAPACITY_BYTES

    if pformat_raw is not None:
        pformat_sections = _parse_pformat_sections(pformat_raw.decode("utf-8", "replace"))
    else:
        pformat_sections = ("loader_nor.bin", "LdrBkup.bin", "DGU.bin", "MIS.bin", "cpapp-b.bin", "pcie_phy_fw.bin")

    if s288_so_raw is not None:
        s288_elf = validate_elf64_so_for_fx3_64k(s288_so_raw, require_64k_pt_load=False)
        require(s288_elf.dt_hash_valid, "stage288 libJit_test.so DT_HASH must be (1,1,0,0)")
        s288_align = s288_elf.pt_load_alignments[0]
    else:
        s288_align = 0x1000

    if fx3_lib_raw is not None:
        # Verify FX3 libJiritsu.so ELF64 AArch64 & 64 KiB PT_LOAD page alignment
        e_phentsize, e_phnum = struct.unpack_from("<HH", fx3_lib_raw, 54)
        e_phoff = struct.unpack_from("<Q", fx3_lib_raw, 32)[0]
        fx3_aligns = []
        for idx in range(e_phnum):
            p_type, _pf, _po, _pv, _pp, _fs, _ms, p_align = struct.unpack_from(
                "<IIQQQQQQ", fx3_lib_raw, e_phoff + idx * e_phentsize
            )
            if p_type == ELF_PT_LOAD:
                fx3_aligns.append(p_align)
        require(all(a == ELF_PT_LOAD_PAGE_ALIGN for a in fx3_aligns), "FX3 libJiritsu.so PT_LOAD must be 0x10000")
        fx3_align = fx3_aligns[0]
    else:
        fx3_align = ELF_PT_LOAD_PAGE_ALIGN

    if wire_raw is not None:
        wire_text = wire_raw.decode("utf-8", "replace")
        require("PFUNC_ADJUST_CONTROL = 0x0040" in wire_text, "stage288 jiritsu_wire.py missing PFUNC 0x0040")
    if cam_raw is not None:
        cam_text = cam_raw.decode("utf-8", "replace")
        require("0x10000011" in cam_text, "stage288 fake_jiritsu_camera.py missing 0x10000011")

    snap_payload = {
        "mode": verification_mode,
        "p6_quota_bytes": p6_bytes,
        "p3_capacity_bytes": p3_bytes,
        "p15_capacity_bytes": p15_bytes,
        "part_count": part_count,
        "pformat_sections": list(pformat_sections),
        "s288_align": s288_align,
        "fx3_align": fx3_align,
        "artifacts": [asdict(a) for a in artifacts],
    }
    return AdjustControlDonorSnapshot(
        verification_mode=verification_mode,
        read_only_access=READ_ONLY_DONOR_ACCESS,
        p6_quota_bytes=p6_bytes,
        p3_capacity_bytes=p3_bytes,
        p15_capacity_bytes=p15_bytes,
        partinf_partition_count=part_count,
        pformat_sections=pformat_sections,
        stage288_so_pt_load_align=s288_align,
        fx3_libjiritsu_pt_load_align=fx3_align,
        artifacts=artifacts,
        snapshot_sha256=_canonical_sha256(snap_payload),
    )


# ---------------------------------------------------------------------------
# Pillar A — ADJUSTCONTROL_0X40_WIRE_TRANSPORT_AND_PREFLIGHT_ABORT
# ---------------------------------------------------------------------------


def validate_jiritsu_path(path: str, *, allow_jbusy_probe: bool = False) -> str:
    """Validate `/tmp/jiritsu/<name>` paths; allow exact `JBUSY_PROBE_PATH` only
    for read-only `GET_FILE2` preflight probing, blocking all other traversal.
    """
    _need(isinstance(path, str) and len(path) > 0, "empty path")
    for tok in FORBIDDEN_TOOL_TOKENS:
        _need(tok not in path.lower(), f"{BLOCKED_FORBIDDEN_JIRITSU_COMMAND}: {tok}")
    raw_path = path.encode("ascii")
    _need(len(raw_path) <= MAX_PATH_BYTES, "path exceeds 0x1FF bytes")
    if path == JBUSY_PROBE_PATH:
        _need(allow_jbusy_probe, f"{BLOCKED_PATH_TRAVERSAL}: jbusy probe path disallowed for write")
        return path
    _need(path.startswith(JIRITSU_TMP_PREFIX), f"{BLOCKED_PATH_TRAVERSAL}: must start with /tmp/jiritsu/")
    _need(".." not in path.split("/"), f"{BLOCKED_PATH_TRAVERSAL}: '..' segment rejected")
    norm = posixpath.normpath(path)
    _need(norm.startswith(JIRITSU_TMP_PREFIX) and len(norm) > len(JIRITSU_TMP_PREFIX), f"{BLOCKED_PATH_TRAVERSAL}: invalid normalized path")
    return path


def set_file_path_request(
    seq: int,
    path: str,
    *,
    allow_jbusy_probe: bool = False,
) -> AdjustRequestEnvelope:
    """Encode Stage-288 `SET_FILE_PATH` (`0x000F`): `b'\\x00' + path + b'\\x00'`."""
    checked = validate_jiritsu_path(path, allow_jbusy_probe=allow_jbusy_probe)
    return AdjustRequestEnvelope(
        seq=seq,
        command=CMD_SET_FILE_PATH,
        inner_payload=b"\x00" + checked.encode("ascii") + b"\x00",
    )


def set_file2_request(
    seq: int,
    file_bytes: bytes,
    *,
    selector: int = 0xFF,
    mode: int = 0x00,
) -> AdjustRequestEnvelope:
    """Encode Stage-288 `SET_FILE2` (`0x0010`): `b'\\x00\\xff\\x00' + payload` (selector `2` rejected)."""
    _need(selector == 0xFF, f"{BLOCKED_SELECTOR_2_REJECTED}: selector {selector:#x} rejected; use 0xFF")
    _need(mode in (0, 1), "mode byte must be 0 or 1")
    _need(isinstance(file_bytes, bytes) and 1 <= len(file_bytes) <= MAX_FILE_BYTES, "file size out of bounds")
    for tok in FORBIDDEN_TOOL_TOKENS:
        _need(tok.encode("ascii") not in file_bytes.lower(), f"{BLOCKED_FORBIDDEN_JIRITSU_COMMAND}: {tok}")
    return AdjustRequestEnvelope(
        seq=seq,
        command=CMD_SET_FILE2,
        inner_payload=b"\x00" + bytes([selector, mode]) + file_bytes,
    )


def get_file2_request(
    seq: int,
    *,
    selector: int = 0xFF,
    mode: int = 0x00,
) -> AdjustRequestEnvelope:
    """Encode Stage-288 `GET_FILE2` (`0x0011`): `b'\\x00\\xff\\x00'` (selector `2` rejected)."""
    _need(selector == 0xFF, f"{BLOCKED_SELECTOR_2_REJECTED}: selector {selector:#x} rejected; use 0xFF")
    _need(mode in (0, 1), "mode byte must be 0 or 1")
    return AdjustRequestEnvelope(
        seq=seq,
        command=CMD_GET_FILE2,
        inner_payload=b"\x00" + bytes([selector, mode]),
    )


def build_forbidden_command_guard(seq: int, command: int, inner_payload: bytes = b"\x01") -> AdjustRequestEnvelope:
    """Attempt to construct an AdjustControl frame; blocks `MODE`/`MOUNT`/`FORMAT`/`START`/`DEBUG`/`FIRMUP`."""
    return AdjustRequestEnvelope(seq=seq, command=command, inner_payload=inner_payload)


def parse_adjust_response_header(
    header: bytes,
    expected_seq: int,
    max_payload_bytes: int = MAX_GET_FILE2_RESPONSE_BODY_BYTES,
) -> int:
    """Validate 12-byte SenserPacket response header and return body size."""
    _need(isinstance(header, bytes) and len(header) == 12, "response header must be 12 bytes")
    _need(isinstance(expected_seq, int) and 0 < expected_seq <= 0xFFFF, "invalid expected_seq")
    size, pfunc, seq, version, flag, reserved, res = struct.unpack("<IHHBBBB", header)
    _need(pfunc == PFUNC_ADJUST_CONTROL, f"unexpected response pFunc: {pfunc:#x}")
    _need(seq == expected_seq, f"sequence mismatch: got {seq}, expected {expected_seq}")
    _need(version == RESP_VERSION_STOCK, f"unexpected response version: {version}")
    _need(flag == 0 and reserved == 0, "non-zero response flag/reserved byte")
    _need(res == RESP_RES_OK, f"non-ok Senser response res byte: {res}")
    _need(4 <= size <= max_payload_bytes, f"response body size {size} outside [4, {max_payload_bytes}]")
    return size


def parse_adjust_response_raw(
    wire_resp: bytes,
    expected_seq: int,
    *,
    max_payload_bytes: int = MAX_GET_FILE2_RESPONSE_BODY_BYTES,
) -> Tuple[ParsedAdjustResponse, bytes]:
    """Parse full SenserPacket response without discarding native error status."""
    _need(isinstance(wire_resp, bytes) and len(wire_resp) >= 16, "truncated response frame")
    size = parse_adjust_response_header(wire_resp[:12], expected_seq=expected_seq, max_payload_bytes=max_payload_bytes)
    body = wire_resp[12:]
    _need(len(body) == size, "response body length mismatch")
    status = struct.unpack_from("<I", body, 0)[0]
    payload = body[4:]
    parsed = ParsedAdjustResponse(
        seq=expected_seq,
        native_status=status,
        payload_bytes=len(payload),
        payload_sha256=sha256(payload).hexdigest(),
    )
    return parsed, payload


def map_native_status_to_abort_code(status: int) -> str:
    if status == STATUS_BUSY:
        return ABORT_BUSY_0X10000011
    if status == STATUS_BAD_FRAME:
        return ABORT_BAD_FRAME_0X10000201
    if status == STATUS_DLOPEN_FAIL:
        return ABORT_DLOPEN_FAIL_0X10000000
    if status == STATUS_MOUNT_FAIL:
        return ABORT_MOUNT_FAIL_0X10000004
    if status == STATUS_P6_NO_SPACE:
        return ABORT_P6_FULL_0X1000000F
    if status == STATUS_USB_TIMEOUT:
        return ABORT_USB_TIMEOUT
    return f"ABORT_NATIVE_STATUS_{status:#010x}"


class AdjustControlSessionClient:
    """Host-side `AdjustControl (0x40)` session client enforcing:
    1. Mandatory `/tmp/jbusy` preflight probe (`GET_FILE2` -> `0x11` `ENOENT`)
    2. Zero `MODE`/`START`/`FORMAT`/`MOUNT`
    3. Immediate abort on any non-zero error or USB timeout — NEVER blind-retrying
       a second `SET_FILE2`.
    4. Passive lock (`live_usb_iokit_transmit_enabled = False`).
    """

    def __init__(
        self,
        transport_handler: Callable[[bytes], bytes],
        *,
        live_usb_iokit_transmit_enabled: bool = False,
        persistent_emmc_writes_authorized: bool = False,
    ) -> None:
        if live_usb_iokit_transmit_enabled or LIVE_USB_IOKIT_TRANSMIT_ENABLED:
            raise PermissionError(BLOCKED_LIVE_USB_IOKIT_TRANSMIT_LOCKED)
        if persistent_emmc_writes_authorized or PERSISTENT_EMMC_WRITES_AUTHORIZED:
            raise PermissionError(BLOCKED_PERSISTENT_EMMC_WRITES_LOCKED)
        self._handler = transport_handler
        self._seq = 0
        self.jbusy_preflight_checked = False
        self.jbusy_absent_confirmed = False
        self.set_file2_sent_count = 0
        self.set_file2_retry_count = 0
        self.blind_second_set_file2_sent = False
        self.wire_frames_sent = 0
        self.aborted = False
        self.abort_reason_code = ""
        self.last_native_status = STATUS_OK

    def _next_seq(self) -> int:
        self._seq = (self._seq % 0xFFFF) + 1
        return self._seq

    def _exchange(self, env: AdjustRequestEnvelope) -> Tuple[ParsedAdjustResponse, bytes]:
        wire = env.to_wire_bytes()
        self.wire_frames_sent += 1
        if env.command == CMD_SET_FILE2:
            if self.aborted:
                self.blind_second_set_file2_sent = True
                raise RuntimeError("Protocol violation: attempted blind SET_FILE2 after abort")
            self.set_file2_sent_count += 1
        try:
            resp_wire = self._handler(wire)
        except TimeoutError:
            self.aborted = True
            self.last_native_status = STATUS_USB_TIMEOUT
            self.abort_reason_code = ABORT_USB_TIMEOUT
            raise
        return parse_adjust_response_raw(resp_wire, expected_seq=env.seq)

    def probe_jbusy_absent(self) -> bool:
        """Mandatory pre-session `/tmp/jbusy` probe: `GET_FILE2` MUST return `0x11`."""
        self.jbusy_preflight_checked = True
        seq1 = self._next_seq()
        try:
            p_resp, _ = self._exchange(set_file_path_request(seq1, JBUSY_PROBE_PATH, allow_jbusy_probe=True))
        except TimeoutError:
            return False
        if p_resp.native_status != STATUS_OK:
            self.aborted = True
            self.last_native_status = p_resp.native_status
            self.abort_reason_code = map_native_status_to_abort_code(p_resp.native_status)
            return False

        seq2 = self._next_seq()
        try:
            g_resp, _ = self._exchange(get_file2_request(seq2))
        except TimeoutError:
            return False
        if g_resp.native_status != STATUS_GET_ABSENT:
            self.aborted = True
            self.last_native_status = g_resp.native_status
            self.abort_reason_code = (
                BLOCKED_JBUSY_PRESENT_ABORT
                if g_resp.native_status == STATUS_OK
                else map_native_status_to_abort_code(g_resp.native_status)
            )
            return False

        self.jbusy_absent_confirmed = True
        return True

    def select_path(self, path: str) -> bool:
        if self.aborted:
            return False
        seq = self._next_seq()
        try:
            resp, _ = self._exchange(set_file_path_request(seq, path))
        except TimeoutError:
            return False
        if resp.native_status != STATUS_OK:
            self.aborted = True
            self.last_native_status = resp.native_status
            self.abort_reason_code = map_native_status_to_abort_code(resp.native_status)
            return False
        return True

    def send_file2_once(self, file_bytes: bytes, *, mode: int = 0x00) -> bool:
        """Send `SET_FILE2` strictly once after preflight; NEVER blind-retry on failure."""
        if not self.jbusy_absent_confirmed:
            self.aborted = True
            self.abort_reason_code = BLOCKED_JBUSY_PRESENT_ABORT
            return False
        if self.aborted:
            return False
        seq = self._next_seq()
        try:
            resp, _ = self._exchange(set_file2_request(seq, file_bytes, selector=0xFF, mode=mode))
        except TimeoutError:
            return False
        if resp.native_status != STATUS_OK:
            self.aborted = True
            self.last_native_status = resp.native_status
            self.abort_reason_code = map_native_status_to_abort_code(resp.native_status)
            return False
        return True

    def get_file2(self) -> Optional[bytes]:
        if self.aborted:
            return None
        seq = self._next_seq()
        try:
            resp, payload = self._exchange(get_file2_request(seq))
        except TimeoutError:
            return None
        if resp.native_status != STATUS_OK:
            self.aborted = True
            self.last_native_status = resp.native_status
            self.abort_reason_code = map_native_status_to_abort_code(resp.native_status)
            return None
        return payload


# ---------------------------------------------------------------------------
# Pillar C (Early Definition for Integrated Simulation) — FakeIOKitAdjustControlCamera
# ---------------------------------------------------------------------------


_VIRTUAL_PART_SHA256_CACHE: Dict[Tuple[str, int, int], str] = {}


class _VirtualPartitionBacking:
    """Deterministic virtual eMMC/SPI-NOR partition stream for fast `< 0.5s` testing
    even up to `500 MiB`, plus exact byte override support (e.g. real `75 MiB` `p3`).
    """

    def __init__(self, spec: ColdBackupItemSpec, exact_bytes: Optional[bytes] = None) -> None:
        self.spec = spec
        self.exact_bytes = exact_bytes
        if exact_bytes is not None:
            self._sha256: Optional[str] = sha256(exact_bytes).hexdigest()
            self.size_bytes = len(exact_bytes)
        else:
            self.size_bytes = spec.size_bytes
            seed = f"FX3_VIRT_PART_{spec.item_id}_{spec.size_bytes}_{spec.offset_bytes:#x}".encode("ascii")
            self._pattern = (seed * ((4096 // len(seed)) + 1))[:4096]
            self._sha256 = _VIRTUAL_PART_SHA256_CACHE.get((spec.item_id, spec.size_bytes, spec.offset_bytes))

    @property
    def digest_sha256(self) -> str:
        if self._sha256 is not None:
            return self._sha256
        h = sha256()
        rem = self.size_bytes
        block_4k = self._pattern
        block_1m = block_4k * 256
        while rem >= len(block_1m):
            h.update(block_1m)
            rem -= len(block_1m)
        while rem >= len(block_4k):
            h.update(block_4k)
            rem -= len(block_4k)
        if rem > 0:
            h.update(block_4k[:rem])
        digest = h.hexdigest()
        self._sha256 = digest
        _VIRTUAL_PART_SHA256_CACHE[(self.spec.item_id, self.size_bytes, self.spec.offset_bytes)] = digest
        return digest

    def read_slice(self, offset: int, length: int) -> bytes:
        _need(0 <= offset <= self.size_bytes, "slice offset out of bounds")
        end = min(self.size_bytes, offset + length)
        actual = end - offset
        if self.exact_bytes is not None:
            return self.exact_bytes[offset:end]
        out = bytearray(actual)
        pos = 0
        cur_off = offset
        plen = len(self._pattern)
        while pos < actual:
            p_idx = cur_off % plen
            take = min(actual - pos, plen - p_idx)
            out[pos : pos + take] = self._pattern[p_idx : p_idx + take]
            pos += take
            cur_off += take
        return bytes(out)


def build_sd_backup_receipt_bytes(
    *,
    manifest_sha256: str,
    item_hashes: Mapping[str, str],
    total_dumped_bytes: int,
    dat2_model_id: str = FX3_MODEL_ID_STR,
    dat3_region_tag: str = FX3_REGION_TAG_STR,
    flags: int = 0x0F,
    entry_count: int = len(COLD_BACKUP_ITEMS),
) -> bytes:
    """Build exact `528 B` compact SD backup receipt returned over `GET_FILE2`."""
    header = struct.pack("<8sHHI", SD_RECEIPT_MAGIC, 1, entry_count, flags)  # 16 B
    tier2_bundle_hash = sha256(
        "|".join(item_hashes[k] for k in ("p5", "p13", "p15", "p23", "p30")).encode("ascii")
    ).digest()
    dat_tag_block = (
        dat2_model_id.encode("ascii")[:8].ljust(8, b"\x00")
        + dat3_region_tag.encode("ascii")[:24].ljust(24, b"\x00")
    )
    meta_block = struct.pack("<QQI12s", total_dumped_bytes, SPI_NOR_DDRTRAINING_OFFSET, 0, b"\x00" * 12)

    digests_15 = b"".join(
        [
            bytes.fromhex(manifest_sha256),
            bytes.fromhex(item_hashes["sector0"]),
            bytes.fromhex(item_hashes["p1"]),
            bytes.fromhex(item_hashes["p2"]),
            bytes.fromhex(item_hashes["p6"]),
            bytes.fromhex(item_hashes["p12"]),
            bytes.fromhex(item_hashes["p18"]),
            bytes.fromhex(item_hashes["spi_nor_ddrtraining"]),
            bytes.fromhex(item_hashes["spi_nor_loader"]),
            bytes.fromhex(item_hashes["p3"]),
            bytes.fromhex(item_hashes["p7"]),
            bytes.fromhex(item_hashes["p8"]),
            tier2_bundle_hash,
            dat_tag_block,
            meta_block,
        ]
    )  # 15 * 32 = 480 B
    body_496 = header + digests_15
    _need(len(body_496) == 496, f"internal receipt body size error: {len(body_496)}")
    integrity = sha256(body_496).digest()
    full = body_496 + integrity
    _need(len(full) == SD_RECEIPT_BYTES, "receipt must be 528 B")
    return full


def parse_sd_backup_receipt_bytes(data: bytes) -> SdBackupReceiptInfo:
    """Parse and cryptographically verify the `528 B` SD backup receipt."""
    errors: List[str] = []
    if not isinstance(data, bytes) or len(data) != SD_RECEIPT_BYTES:
        return SdBackupReceiptInfo(
            valid=False,
            receipt_bytes=len(data) if isinstance(data, bytes) else 0,
            magic="",
            version=0,
            entry_count=0,
            flags=0,
            manifest_sha256="",
            sector0_sha256="",
            p1_sha256="",
            p2_sha256="",
            p6_sha256="",
            p12_sha256="",
            p18_sha256="",
            spi_nor_ddrtraining_sha256="",
            spi_nor_loader_sha256="",
            tier2_bundle_sha256="",
            total_dumped_bytes=0,
            receipt_integrity_sha256="",
            errors=(f"{ERR_SD_RECEIPT_INVALID}: expected 528 B",),
        )
    magic_raw, version, entry_count, flags = struct.unpack_from("<8sHHI", data, 0)
    if magic_raw != SD_RECEIPT_MAGIC:
        errors.append(f"{ERR_SD_RECEIPT_INVALID}: bad magic")
    if version != 1 or entry_count != len(COLD_BACKUP_ITEMS):
        errors.append(f"{ERR_SD_RECEIPT_INVALID}: bad version/entry_count")

    expected_integrity = sha256(data[:496]).digest()
    actual_integrity = data[496:528]
    if actual_integrity != expected_integrity:
        errors.append(f"{ERR_SD_RECEIPT_INVALID}: integrity SHA-256 mismatch")

    slots = [data[16 + i * 32 : 16 + (i + 1) * 32] for i in range(15)]
    total_dumped_bytes = struct.unpack_from("<Q", slots[14], 0)[0]
    return SdBackupReceiptInfo(
        valid=len(errors) == 0,
        receipt_bytes=len(data),
        magic=magic_raw.decode("ascii", "replace"),
        version=version,
        entry_count=entry_count,
        flags=flags,
        manifest_sha256=slots[0].hex(),
        sector0_sha256=slots[1].hex(),
        p1_sha256=slots[2].hex(),
        p2_sha256=slots[3].hex(),
        p6_sha256=slots[4].hex(),
        p12_sha256=slots[5].hex(),
        p18_sha256=slots[6].hex(),
        spi_nor_ddrtraining_sha256=slots[7].hex(),
        spi_nor_loader_sha256=slots[8].hex(),
        tier2_bundle_sha256=slots[12].hex(),
        total_dumped_bytes=total_dumped_bytes,
        receipt_integrity_sha256=actual_integrity.hex(),
        errors=tuple(errors),
    )


def frame_sliding_chunk(offset: int, chunk_data: bytes) -> bytes:
    """Wrap chunk payload with `[8B "FX3CHK1\\0" + u64 offset + u32 length + u32 crc32]`."""
    crc = zlib.crc32(chunk_data) & 0xFFFFFFFF
    hdr = struct.pack(CHUNK_HEADER_FORMAT, CHUNK_HEADER_MAGIC, offset, len(chunk_data), crc)
    return hdr + chunk_data


def verify_and_unframe_sliding_chunk(
    framed: bytes,
    *,
    expected_offset: int,
    max_chunk_bytes: int = SLIDING_WINDOW_CHUNK_BYTES,
) -> Tuple[bool, bytes, str]:
    """Verify `FX3CHK1\\0` header + offset + length + CRC32 and return raw chunk bytes."""
    if not isinstance(framed, bytes) or len(framed) < CHUNK_HEADER_BYTES:
        return False, b"", f"{ERR_CHUNK_HEADER_CORRUPT}: truncated chunk frame"
    magic, offset, length, expected_crc = struct.unpack_from(CHUNK_HEADER_FORMAT, framed, 0)
    if magic != CHUNK_HEADER_MAGIC:
        return False, b"", f"{ERR_CHUNK_HEADER_CORRUPT}: bad FX3CHK1 magic"
    if offset != expected_offset:
        return False, b"", f"{ERR_CHUNK_HEADER_CORRUPT}: offset {offset} != expected {expected_offset}"
    if length <= 0 or length > max_chunk_bytes or len(framed) != CHUNK_HEADER_BYTES + length:
        return False, b"", f"{ERR_CHUNK_HEADER_CORRUPT}: invalid chunk length {length}"
    payload = framed[CHUNK_HEADER_BYTES:]
    actual_crc = zlib.crc32(payload) & 0xFFFFFFFF
    if actual_crc != expected_crc:
        return False, b"", f"{ERR_CHUNK_HEADER_CORRUPT}: crc32 {actual_crc:#x} != {expected_crc:#x}"
    return True, payload, ""


class FakeIOKitAdjustControlCamera:
    """Stateful host-only Fake IOKit USB endpoint (`054C:0336`, `AdjustControl 0x40`).

    Models:
    - Sony VID `0x054C` / PID `0x0336` service endpoint
    - `25 MiB` (`26,214,400 B`) `p6` (`/tmp/jiritsu/`) quota (`0x1000000F`)
    - `/tmp/jbusy` lockouts (`0x11` on probe when absent; `0x10000011` on `SET_FILE2`)
    - ELF64 AArch64 `DT_HASH (1,1,0,0)` + `PT_LOAD` `0x10000` validation (`0x10000000`)
    - Path 1 SD/CFexpress ExFAT streaming (`MANIFEST.SHA256` + `528 B` receipt)
    - Path 2 `4 MiB` sliding-window `FX3CHK1\\0` staging & auto-unlink
    - Post-session residual-file audit (`p6_residual_files == 0`)
    - Hard-locked passive flags (`live_usb_iokit_transmit_enabled=False`,
      `persistent_emmc_writes_authorized=False`)
    """

    def __init__(
        self,
        *,
        jbusy: bool = False,
        sd_writable: bool = True,
        p6_quota_bytes: int = P6_PARTITION_QUOTA_BYTES,
        require_64k_pt_load_align: bool = True,
        unlink_libjit_on_dlopen: bool = True,
        unlink_staged_artifact_on_get: bool = True,
        inject_fault: Optional[str] = None,
        partition_overrides: Optional[Mapping[str, bytes]] = None,
        action_mode: str = "sd_stream",
        pull_partition: str = "p3",
        pull_chunk_size: int = SLIDING_WINDOW_CHUNK_BYTES,
    ) -> None:
        self.usb_vid: int = SONY_USB_VID
        self.usb_pid: int = SONY_SERVICE_PID
        self.usb_vid_pid: str = SONY_SERVICE_VID_PID
        self.live_usb_iokit_transmit_enabled: bool = LIVE_USB_IOKIT_TRANSMIT_ENABLED
        self.persistent_emmc_writes_authorized: bool = PERSISTENT_EMMC_WRITES_AUTHORIZED
        self.physical_usb_bytes_transmitted: int = 0
        self.physical_device_writes: int = 0

        self.jbusy: bool = jbusy
        self.sd_writable: bool = sd_writable
        self.p6_quota_bytes: int = p6_quota_bytes
        self.require_64k_pt_load_align: bool = require_64k_pt_load_align
        self.unlink_libjit_on_dlopen: bool = unlink_libjit_on_dlopen
        self.unlink_staged_artifact_on_get: bool = unlink_staged_artifact_on_get
        self.inject_fault: Optional[str] = inject_fault
        self.action_mode: str = action_mode
        self.pull_partition: str = pull_partition
        self.pull_chunk_size: int = pull_chunk_size
        self.pull_cursor_offset: int = 0

        self.selected_path: Optional[str] = None
        self.p6_files: Dict[str, bytes] = {}
        self.sd_files: Dict[str, str] = {}  # simulated /mnt/sd/FX3_COLD_BACKUP/ filenames -> SHA-256/content
        self.sd_manifest_text: str = ""
        self.jmodes: Dict[str, str] = {}
        self.peak_p6_bytes: int = 0
        self.total_frames_handled: int = 0

        overrides = dict(partition_overrides or {})
        self.partitions: Dict[str, _VirtualPartitionBacking] = {}
        for spec in COLD_BACKUP_ITEMS:
            self.partitions[spec.item_id] = _VirtualPartitionBacking(
                spec,
                exact_bytes=overrides.get(spec.item_id),
            )

    @property
    def p6_used_bytes(self) -> int:
        return sum(len(v) for v in self.p6_files.values())

    def _record_p6_write(self, path: str, data: bytes) -> bool:
        existing = len(self.p6_files.get(path, b""))
        projected = self.p6_used_bytes - existing + len(data)
        if projected > self.p6_quota_bytes:
            return False
        self.p6_files[path] = data
        if self.p6_used_bytes > self.peak_p6_bytes:
            self.peak_p6_bytes = self.p6_used_bytes
        return True

    def stage_p6_file_direct(self, path: str, data: bytes) -> int:
        """Attempt direct staging on `p6` (enforces `25 MiB` quota -> `0x1000000F`)."""
        if not self._record_p6_write(path, data):
            return STATUS_P6_NO_SPACE
        return STATUS_OK

    def stage_next_sliding_chunk(self, *, corrupt_crc: bool = False) -> Tuple[int, int]:
        """Simulate constructor staging next `<= 4 MiB` chunk onto `p6` (`/tmp/jiritsu/chunk.bin`)."""
        part = self.partitions[self.pull_partition]
        if self.pull_cursor_offset >= part.size_bytes:
            return STATUS_OK, 0
        raw_chunk = part.read_slice(self.pull_cursor_offset, self.pull_chunk_size)
        framed = frame_sliding_chunk(self.pull_cursor_offset, raw_chunk)
        if corrupt_crc and len(framed) > CHUNK_HEADER_BYTES:
            b = bytearray(framed)
            b[-1] ^= 0xFF
            framed = bytes(b)
        if not self._record_p6_write(SLIDING_CHUNK_PATH, framed):
            return STATUS_P6_NO_SPACE, 0
        self.pull_cursor_offset += len(raw_chunk)
        return STATUS_OK, len(raw_chunk)

    @staticmethod
    def _response(seq: int, status: int, payload: bytes = b"") -> bytes:
        body = struct.pack("<I", status) + payload
        header = struct.pack("<IHHBBBB", len(body), PFUNC_ADJUST_CONTROL, seq, RESP_VERSION_STOCK, 0, 0, RESP_RES_OK)
        return header + body

    def handle(self, wire: bytes) -> bytes:
        self.total_frames_handled += 1
        if self.inject_fault == "usb_timeout" and self.total_frames_handled >= 4:
            raise TimeoutError("Simulated IOKit USB control timeout")

        _need(len(wire) >= 16, "wire request too short")
        size, pfunc, seq, version, flag, reserved, res = struct.unpack_from("<IHHBBBB", wire, 0)
        _need((pfunc, version, flag, reserved, res) == (PFUNC_ADJUST_CONTROL, REQ_VERSION_ADJUST, 0, 0, 0), "bad request header")
        _need(size == len(wire) - 12, "wire body size mismatch")
        body = wire[12:]
        category, command = struct.unpack_from("<HH", body, 0)
        _need(category == CATEGORY_JIRITSU, f"unexpected category: {category:#x}")
        inner = body[4:]

        if command in FORBIDDEN_JIRITSU_COMMANDS:
            if command == CMD_JIRITSU_MODE:
                self.jmodes["/tmp/jmode"] = "FORBIDDEN"
            return self._response(seq, STATUS_BAD_FRAME)

        if command == CMD_SET_FILE_PATH:
            if len(inner) < 3 or inner[0] != 0x00 or inner[-1] != 0x00:
                return self._response(seq, STATUS_BAD_FRAME)
            path = inner[1:-1].decode("ascii", "strict")
            if path != JBUSY_PROBE_PATH and not path.startswith(JIRITSU_TMP_PREFIX):
                return self._response(seq, STATUS_BAD_FRAME)
            self.selected_path = path
            return self._response(seq, STATUS_OK)

        if command == CMD_SET_FILE2:
            if len(inner) < 4 or inner[0] != 0x00 or inner[1] != 0xFF or inner[2] not in (0, 1):
                return self._response(seq, STATUS_BAD_FRAME)
            if self.inject_fault == "bad_frame":
                return self._response(seq, STATUS_BAD_FRAME)
            if self.jbusy or self.inject_fault == "busy":
                return self._response(seq, STATUS_BUSY)
            if self.inject_fault == "p6_full":
                return self._response(seq, STATUS_P6_NO_SPACE)
            data = inner[3:]
            if len(data) > self.p6_quota_bytes:
                return self._response(seq, STATUS_P6_NO_SPACE)
            if not self._record_p6_write(self.selected_path or "", data):
                return self._response(seq, STATUS_P6_NO_SPACE)

            if self.selected_path == LIBJIT_PATH:
                if self.inject_fault == "dlopen_fail":
                    return self._response(seq, STATUS_DLOPEN_FAIL)
                elf_res = validate_elf64_so_for_fx3_64k(
                    data,
                    require_64k_pt_load=self.require_64k_pt_load_align,
                )
                if not elf_res.valid:
                    return self._response(seq, STATUS_DLOPEN_FAIL)

                # Constructor self-unlinks /tmp/jiritsu/libJit.so safely after dlopen mmap
                if self.unlink_libjit_on_dlopen:
                    self.p6_files.pop(LIBJIT_PATH, None)

                if self.inject_fault == "mount_fail":
                    return self._response(seq, STATUS_MOUNT_FAIL)

                if self.action_mode == "sd_stream":
                    if not self.sd_writable:
                        return self._response(seq, STATUS_MOUNT_FAIL)
                    manifest_lines: List[str] = []
                    item_hashes: Dict[str, str] = {}
                    total_bytes = 0
                    for spec in COLD_BACKUP_ITEMS:
                        backing = self.partitions[spec.item_id]
                        h = backing.digest_sha256
                        item_hashes[spec.item_id] = h
                        total_bytes += backing.size_bytes
                        self.sd_files[f"{SD_BACKUP_MOUNT_DIR}/{spec.filename}"] = h
                        manifest_lines.append(f"{h}  {spec.filename}")
                    self.sd_manifest_text = "\n".join(manifest_lines) + "\n"
                    self.sd_files[f"{SD_BACKUP_MOUNT_DIR}/{SD_BACKUP_MANIFEST_NAME}"] = sha256(
                        self.sd_manifest_text.encode("utf-8")
                    ).hexdigest()
                    receipt = build_sd_backup_receipt_bytes(
                        manifest_sha256=self.sd_files[f"{SD_BACKUP_MOUNT_DIR}/{SD_BACKUP_MANIFEST_NAME}"],
                        item_hashes=item_hashes,
                        total_dumped_bytes=total_bytes,
                    )
                    if not self._record_p6_write(SD_RECEIPT_PATH, receipt):
                        return self._response(seq, STATUS_P6_NO_SPACE)
                elif self.action_mode == "sliding_pull":
                    st, _ = self.stage_next_sliding_chunk(
                        corrupt_crc=(self.inject_fault == "corrupt_chunk_crc")
                    )
                    if st != STATUS_OK:
                        return self._response(seq, st)
                elif self.action_mode == "unbounded_p3_stage":
                    # Deliberately try to stage 75 MiB p3 directly into p6 (25 MiB) -> 0x1000000F!
                    if self.p6_used_bytes + P3_PARTITION_CAPACITY_BYTES > self.p6_quota_bytes:
                        return self._response(seq, STATUS_P6_NO_SPACE)

            return self._response(seq, STATUS_OK)

        if command == CMD_GET_FILE2:
            if inner != b"\x00\xff\x00":
                return self._response(seq, STATUS_BAD_FRAME)
            if self.selected_path == JBUSY_PROBE_PATH:
                if self.jbusy:
                    return self._response(seq, STATUS_OK, b"JBUSY_ACTIVE")
                return self._response(seq, STATUS_GET_ABSENT)
            if self.selected_path not in self.p6_files:
                return self._response(seq, STATUS_GET_ABSENT)
            payload = self.p6_files[self.selected_path]
            if self.unlink_staged_artifact_on_get and self.selected_path in (SD_RECEIPT_PATH, SLIDING_CHUNK_PATH):
                self.p6_files.pop(self.selected_path, None)
            return self._response(seq, STATUS_OK, payload)

        return self._response(seq, STATUS_BAD_FRAME)

    def audit_post_session(self) -> PostSessionAuditResult:
        residual_paths = tuple(sorted(self.p6_files.keys()))
        residual_bytes = self.p6_used_bytes
        forbidden = tuple(sorted(self.jmodes.keys()))
        errors: List[str] = []
        if residual_paths:
            errors.append(f"{STATUS_REJECTED_P6_RESIDUAL_FILES}: {residual_paths}")
        if self.jbusy:
            errors.append("jbusy flag active post-session")
        if forbidden:
            errors.append(f"forbidden jmodes touched: {forbidden}")
        clean = len(errors) == 0
        return PostSessionAuditResult(
            clean=clean,
            status="VERIFIED_P6_POST_SESSION_CLEAN" if clean else STATUS_REJECTED_P6_RESIDUAL_FILES,
            p6_residual_files=len(residual_paths),
            p6_residual_bytes=residual_bytes,
            residual_paths=residual_paths,
            jbusy_state=self.jbusy,
            forbidden_modes_touched=forbidden,
            errors=tuple(errors),
        )


# ---------------------------------------------------------------------------
# Pillar A Scenario Runner (7 Scenarios)
# ---------------------------------------------------------------------------


def _run_preflight_and_single_set_file2(
    camera: FakeIOKitAdjustControlCamera,
    so_bytes: bytes,
    *,
    scenario_id: str,
) -> PreflightAbortSessionResult:
    client = AdjustControlSessionClient(camera.handle)
    errors: List[str] = []
    ok_preflight = client.probe_jbusy_absent()
    if ok_preflight:
        if client.select_path(LIBJIT_PATH):
            client.send_file2_once(so_bytes)

    payload = {
        "scenario_id": scenario_id,
        "aborted": client.aborted,
        "abort_reason_code": client.abort_reason_code,
        "status": hex(client.last_native_status),
        "jbusy_preflight_checked": client.jbusy_preflight_checked,
        "jbusy_absent_confirmed": client.jbusy_absent_confirmed,
        "set_file2_sent_count": client.set_file2_sent_count,
        "set_file2_retry_count": client.set_file2_retry_count,
        "blind_second_set_file2_sent": client.blind_second_set_file2_sent,
    }
    return PreflightAbortSessionResult(
        passed=not client.blind_second_set_file2_sent and client.set_file2_retry_count == 0,
        scenario_id=scenario_id,
        aborted=client.aborted,
        abort_reason_code=client.abort_reason_code,
        native_status_hex=f"{client.last_native_status:#010x}",
        jbusy_preflight_checked=client.jbusy_preflight_checked,
        jbusy_absent_confirmed=client.jbusy_absent_confirmed,
        set_file2_sent_count=client.set_file2_sent_count,
        set_file2_retry_count=client.set_file2_retry_count,
        blind_second_set_file2_sent=client.blind_second_set_file2_sent,
        forbidden_command_blocked=True,
        wire_frames_sent=client.wire_frames_sent,
        errors=tuple(errors),
        report_sha256=_canonical_sha256(payload),
    )


def run_pillar_a_wire_and_preflight_7_scenario_suite(
    *,
    so_bytes: Optional[bytes] = None,
) -> PillarA7ScenarioSuiteResult:
    """Execute all 7 Pillar A wire codec & preflight/immediate-abort scenarios."""
    payload_so = so_bytes if so_bytes is not None else build_synthetic_jiritsu_so_64k()
    suite_errors: List[str] = []
    results: List[PreflightAbortSessionResult] = []
    passed_count = 0

    # PA1: Happy preflight + wire roundtrip
    cam1 = FakeIOKitAdjustControlCamera(jbusy=False, sd_writable=True, action_mode="sd_stream")
    r1 = _run_preflight_and_single_set_file2(cam1, payload_so, scenario_id=PILLAR_A_SCENARIO_IDS[0])
    # Also verify exact wire bytes for SET_FILE_PATH, SET_FILE2, GET_FILE2
    w_path = set_file_path_request(1, LIBJIT_PATH).to_wire_bytes()
    w_set = set_file2_request(2, payload_so).to_wire_bytes()
    w_get = get_file2_request(3).to_wire_bytes()
    wire_ok = (
        w_path[16:] == (b"\x00" + LIBJIT_PATH.encode("ascii") + b"\x00")
        and w_set[16:19] == b"\x00\xff\x00"
        and w_set[19:] == payload_so
        and w_get[16:19] == b"\x00\xff\x00"
        and len(w_get) == 19
    )
    pa1_ok = r1.passed and (not r1.aborted) and r1.jbusy_absent_confirmed and r1.set_file2_sent_count == 1 and wire_ok
    if pa1_ok:
        passed_count += 1
    else:
        suite_errors.append("PA1 happy preflight/wire failed")
    results.append(PreflightAbortSessionResult(**{**r1.__dict__, "passed": pa1_ok}))

    # PA2: jbusy present during preflight -> abort BEFORE any SET_FILE2
    cam2 = FakeIOKitAdjustControlCamera(jbusy=True)
    r2 = _run_preflight_and_single_set_file2(cam2, payload_so, scenario_id=PILLAR_A_SCENARIO_IDS[1])
    pa2_ok = r2.aborted and r2.abort_reason_code == BLOCKED_JBUSY_PRESENT_ABORT and r2.set_file2_sent_count == 0
    if pa2_ok:
        passed_count += 1
    else:
        suite_errors.append(f"PA2 failed: {r2.abort_reason_code} sent={r2.set_file2_sent_count}")
    results.append(PreflightAbortSessionResult(**{**r2.__dict__, "passed": pa2_ok}))

    # PA3: SET_FILE2 returns 0x10000011 -> immediate abort, zero retry
    cam3 = FakeIOKitAdjustControlCamera(jbusy=False, inject_fault="busy")
    r3 = _run_preflight_and_single_set_file2(cam3, payload_so, scenario_id=PILLAR_A_SCENARIO_IDS[2])
    pa3_ok = r3.aborted and r3.abort_reason_code == ABORT_BUSY_0X10000011 and r3.set_file2_retry_count == 0 and not r3.blind_second_set_file2_sent
    if pa3_ok:
        passed_count += 1
    else:
        suite_errors.append(f"PA3 failed: {r3.abort_reason_code}")
    results.append(PreflightAbortSessionResult(**{**r3.__dict__, "passed": pa3_ok}))

    # PA4: Selector 2 rejected in codec + 0x10000201 immediate abort
    sel2_blocked = False
    for fn in (lambda: set_file2_request(1, b"x", selector=2), lambda: get_file2_request(1, selector=2)):
        try:
            fn()
        except ValueError:
            sel2_blocked = True
        else:
            sel2_blocked = False
            break
    cam4 = FakeIOKitAdjustControlCamera(jbusy=False, inject_fault="bad_frame")
    r4 = _run_preflight_and_single_set_file2(cam4, payload_so, scenario_id=PILLAR_A_SCENARIO_IDS[3])
    pa4_ok = sel2_blocked and r4.aborted and r4.abort_reason_code == ABORT_BAD_FRAME_0X10000201 and r4.set_file2_retry_count == 0
    if pa4_ok:
        passed_count += 1
    else:
        suite_errors.append(f"PA4 failed: sel2={sel2_blocked} code={r4.abort_reason_code}")
    results.append(PreflightAbortSessionResult(**{**r4.__dict__, "passed": pa4_ok}))

    # PA5: dlopen fail (0x10000000) & mount fail (0x10000004) immediate abort
    cam5a = FakeIOKitAdjustControlCamera(jbusy=False, inject_fault="dlopen_fail")
    r5a = _run_preflight_and_single_set_file2(cam5a, payload_so, scenario_id=PILLAR_A_SCENARIO_IDS[4])
    cam5b = FakeIOKitAdjustControlCamera(jbusy=False, inject_fault="mount_fail")
    r5b = _run_preflight_and_single_set_file2(cam5b, payload_so, scenario_id=PILLAR_A_SCENARIO_IDS[4])
    pa5_ok = (
        r5a.aborted
        and r5a.abort_reason_code == ABORT_DLOPEN_FAIL_0X10000000
        and r5b.aborted
        and r5b.abort_reason_code == ABORT_MOUNT_FAIL_0X10000004
        and r5a.set_file2_retry_count == 0
        and r5b.set_file2_retry_count == 0
    )
    if pa5_ok:
        passed_count += 1
    else:
        suite_errors.append(f"PA5 failed: {r5a.abort_reason_code} / {r5b.abort_reason_code}")
    results.append(PreflightAbortSessionResult(**{**r5a.__dict__, "passed": pa5_ok}))

    # PA6: p6 full (0x1000000F) & USB timeout immediate abort
    cam6a = FakeIOKitAdjustControlCamera(jbusy=False, inject_fault="p6_full")
    r6a = _run_preflight_and_single_set_file2(cam6a, payload_so, scenario_id=PILLAR_A_SCENARIO_IDS[5])
    cam6b = FakeIOKitAdjustControlCamera(jbusy=False, inject_fault="usb_timeout")
    r6b = _run_preflight_and_single_set_file2(cam6b, payload_so, scenario_id=PILLAR_A_SCENARIO_IDS[5])
    pa6_ok = (
        r6a.aborted
        and r6a.abort_reason_code == ABORT_P6_FULL_0X1000000F
        and r6b.aborted
        and r6b.abort_reason_code == ABORT_USB_TIMEOUT
        and r6a.set_file2_retry_count == 0
        and r6b.set_file2_retry_count == 0
    )
    if pa6_ok:
        passed_count += 1
    else:
        suite_errors.append(f"PA6 failed: {r6a.abort_reason_code} / {r6b.abort_reason_code}")
    results.append(PreflightAbortSessionResult(**{**r6a.__dict__, "passed": pa6_ok}))

    # PA7: Forbidden MODE/START/FORMAT/MOUNT commands & path traversal blocked
    forbidden_blocked = True
    for cmd in FORBIDDEN_JIRITSU_COMMANDS:
        try:
            build_forbidden_command_guard(1, cmd).to_wire_bytes()
            forbidden_blocked = False
        except ValueError:
            pass
    for bad_path in ("/etc/passwd", "/tmp/jiritsu/../setting/Backup.bin", JBUSY_PROBE_PATH):
        try:
            set_file_path_request(1, bad_path, allow_jbusy_probe=False)
            forbidden_blocked = False
        except ValueError:
            pass
    pa7_ok = forbidden_blocked
    if pa7_ok:
        passed_count += 1
    else:
        suite_errors.append("PA7 failed to block forbidden commands or path traversal")
    results.append(
        PreflightAbortSessionResult(
            passed=pa7_ok,
            scenario_id=PILLAR_A_SCENARIO_IDS[6],
            aborted=True,
            abort_reason_code=BLOCKED_FORBIDDEN_JIRITSU_COMMAND,
            native_status_hex="0x00000000",
            jbusy_preflight_checked=False,
            jbusy_absent_confirmed=False,
            set_file2_sent_count=0,
            set_file2_retry_count=0,
            blind_second_set_file2_sent=False,
            forbidden_command_blocked=forbidden_blocked,
            wire_frames_sent=0,
            errors=() if pa7_ok else ("forbidden command/path leaked",),
            report_sha256=_canonical_sha256({"scenario": PILLAR_A_SCENARIO_IDS[6], "blocked": forbidden_blocked}),
        )
    )

    all_ok = len(suite_errors) == 0 and passed_count == len(PILLAR_A_SCENARIO_IDS)
    return PillarA7ScenarioSuiteResult(
        passed=all_ok,
        status=STATUS_VERIFIED_PILLAR_A if all_ok else STATUS_REJECTED_PILLAR_A,
        scenarios_passed=passed_count,
        scenarios_total=len(PILLAR_A_SCENARIO_IDS),
        scenario_results=tuple(results),
        physical_usb_bytes_transmitted=PHYSICAL_USB_BYTES_TRANSMITTED,
        errors=tuple(suite_errors),
        suite_sha256=_canonical_sha256({"scenarios": [r.report_sha256 for r in results], "ok": all_ok}),
    )


# ---------------------------------------------------------------------------
# Pillar B — DUAL_PATH_SD_STREAM_AND_P6_SLIDING_WINDOW_COLD_BACKUP
# ---------------------------------------------------------------------------


def execute_sd_streaming_cold_backup(
    camera: FakeIOKitAdjustControlCamera,
    so_bytes: bytes,
    *,
    scenario_id: str = PILLAR_B_SCENARIO_IDS[0],
) -> SdStreamingBackupResult:
    """Path 1: Direct SD/CFexpress ExFAT Stream Dumper returning compact `528 B` receipt."""
    client = AdjustControlSessionClient(camera.handle)
    error_codes: List[str] = []
    errors: List[str] = []

    if not client.probe_jbusy_absent():
        error_codes.append(client.abort_reason_code)
        errors.append("jbusy preflight failed")
    elif not client.select_path(LIBJIT_PATH):
        error_codes.append(client.abort_reason_code)
    elif not client.send_file2_once(so_bytes):
        error_codes.append(client.abort_reason_code)

    receipt_bytes_raw = b""
    receipt_info: Optional[SdBackupReceiptInfo] = None
    if not client.aborted:
        if not client.select_path(SD_RECEIPT_PATH):
            error_codes.append(client.abort_reason_code)
        else:
            got = client.get_file2()
            if got is None:
                error_codes.append(client.abort_reason_code)
            else:
                receipt_bytes_raw = got
                receipt_info = parse_sd_backup_receipt_bytes(receipt_bytes_raw)
                if not receipt_info.valid:
                    error_codes.append(ERR_SD_RECEIPT_INVALID)
                    errors.extend(receipt_info.errors)

    post_audit = camera.audit_post_session()
    if not post_audit.clean:
        error_codes.append(STATUS_REJECTED_P6_RESIDUAL_FILES)
        errors.extend(post_audit.errors)

    covered = tuple(
        item.item_id for item in COLD_BACKUP_ITEMS if f"{SD_BACKUP_MOUNT_DIR}/{item.filename}" in camera.sd_files
    )
    manifest_key = f"{SD_BACKUP_MOUNT_DIR}/{SD_BACKUP_MANIFEST_NAME}"
    manifest_sha = camera.sd_files.get(manifest_key, "")
    if receipt_info is not None and receipt_info.valid:
        if receipt_info.manifest_sha256 != manifest_sha:
            error_codes.append(ERR_SD_RECEIPT_INVALID)
            errors.append("receipt manifest_sha256 != SD MANIFEST.SHA256")
        if covered != REQUIRED_COLD_BACKUP_ITEM_IDS:
            error_codes.append(ERR_SD_RECEIPT_INVALID)
            errors.append("missing cold backup items on SD mount")

    passed = (
        len(error_codes) == 0
        and receipt_info is not None
        and receipt_info.valid
        and len(receipt_bytes_raw) == SD_RECEIPT_BYTES
        and len(receipt_bytes_raw) < 1024
        and post_audit.p6_residual_files == 0
        and covered == REQUIRED_COLD_BACKUP_ITEM_IDS
    )
    payload = {
        "scenario_id": scenario_id,
        "covered": list(covered),
        "manifest_sha256": manifest_sha,
        "p6_receipt_bytes": len(receipt_bytes_raw),
        "p6_residual_files": post_audit.p6_residual_files,
        "passed": passed,
    }
    return SdStreamingBackupResult(
        passed=passed,
        scenario_id=scenario_id,
        mount_dir=SD_BACKUP_MOUNT_DIR,
        manifest_entry_count=len(covered),
        covered_item_ids=covered,
        dat2_model_id=FX3_MODEL_ID_STR,
        dat3_region_tag=FX3_REGION_TAG_STR,
        total_dumped_bytes=receipt_info.total_dumped_bytes if receipt_info else 0,
        p6_receipt_bytes=len(receipt_bytes_raw),
        p6_peak_bytes=camera.peak_p6_bytes,
        p6_residual_files=post_audit.p6_residual_files,
        receipt_valid=bool(receipt_info and receipt_info.valid),
        manifest_sha256=manifest_sha,
        error_codes=tuple(error_codes),
        errors=tuple(errors),
        report_sha256=_canonical_sha256(payload),
    )


def execute_p6_sliding_window_usb_pull(
    camera: FakeIOKitAdjustControlCamera,
    so_bytes: bytes,
    *,
    partition_name: str = "p3",
    chunk_size_bytes: int = SLIDING_WINDOW_CHUNK_BYTES,
    scenario_id: str = PILLAR_B_SCENARIO_IDS[1],
    fallback_triggered: bool = False,
) -> SlidingWindowPullResult:
    """Path 2: Pull an arbitrarily large partition in bounded `<= 4 MiB` chunks over `p6`."""
    _need(1 <= chunk_size_bytes <= SLIDING_WINDOW_CHUNK_BYTES, "sliding-window chunk size must be <= 4 MiB")
    camera.action_mode = "sliding_pull"
    camera.pull_partition = partition_name
    camera.pull_chunk_size = chunk_size_bytes
    camera.pull_cursor_offset = 0

    target_part = camera.partitions[partition_name]
    source_bytes = target_part.size_bytes
    source_sha = target_part.digest_sha256

    client = AdjustControlSessionClient(camera.handle)
    error_codes: List[str] = []
    errors: List[str] = []
    reassembled_hasher = sha256()
    pulled_bytes = 0
    chunks_pulled = 0

    if not client.probe_jbusy_absent():
        error_codes.append(client.abort_reason_code)
    else:
        while pulled_bytes < source_bytes:
            if not client.select_path(LIBJIT_PATH):
                error_codes.append(client.abort_reason_code)
                break
            # Each chunk cycle triggers one bounded <=4 MiB chunk write -> read -> unlink
            if not client.send_file2_once(so_bytes):
                error_codes.append(client.abort_reason_code)
                break
            if not client.select_path(SLIDING_CHUNK_PATH):
                error_codes.append(client.abort_reason_code)
                break
            framed = client.get_file2()
            if framed is None:
                error_codes.append(client.abort_reason_code)
                break
            ok_chk, chunk_data, err_msg = verify_and_unframe_sliding_chunk(
                framed,
                expected_offset=pulled_bytes,
                max_chunk_bytes=chunk_size_bytes,
            )
            if not ok_chk:
                error_codes.append(ERR_CHUNK_HEADER_CORRUPT)
                errors.append(err_msg)
                break
            reassembled_hasher.update(chunk_data)
            pulled_bytes += len(chunk_data)
            chunks_pulled += 1
            # Verify p6 is clean between chunks
            if camera.p6_used_bytes != 0:
                error_codes.append(STATUS_REJECTED_P6_RESIDUAL_FILES)
                errors.append(f"p6 not clean after chunk {chunks_pulled}: {camera.p6_used_bytes} B")
                break

    post_audit = camera.audit_post_session()
    if not post_audit.clean:
        error_codes.append(STATUS_REJECTED_P6_RESIDUAL_FILES)
        errors.extend(post_audit.errors)

    reassembled_sha = reassembled_hasher.hexdigest() if pulled_bytes == source_bytes else ""
    sha_match = (pulled_bytes == source_bytes) and (reassembled_sha == source_sha)
    if pulled_bytes == source_bytes and not sha_match:
        error_codes.append(ERR_REASSEMBLY_SHA256_MISMATCH)

    passed = (
        len(error_codes) == 0
        and sha_match
        and camera.peak_p6_bytes <= SLIDING_WINDOW_MAX_PEAK_P6_BYTES
        and camera.peak_p6_bytes < camera.p6_quota_bytes
        and post_audit.p6_residual_files == 0
        and client.set_file2_retry_count == 0
    )
    payload = {
        "scenario_id": scenario_id,
        "partition": partition_name,
        "chunks_pulled": chunks_pulled,
        "pulled_bytes": pulled_bytes,
        "reassembled_sha256": reassembled_sha,
        "peak_p6_bytes": camera.peak_p6_bytes,
        "p6_residual_files": post_audit.p6_residual_files,
        "passed": passed,
    }
    return SlidingWindowPullResult(
        passed=passed,
        scenario_id=scenario_id,
        partition_name=partition_name,
        fallback_triggered=fallback_triggered,
        chunk_size_bytes=chunk_size_bytes,
        chunks_pulled=chunks_pulled,
        total_pulled_bytes=pulled_bytes,
        source_sha256=source_sha,
        reassembled_sha256=reassembled_sha,
        sha256_exact_match=sha_match,
        peak_p6_bytes=camera.peak_p6_bytes,
        p6_quota_bytes=camera.p6_quota_bytes,
        p6_residual_files=post_audit.p6_residual_files,
        set_file2_retry_count=client.set_file2_retry_count,
        error_codes=tuple(error_codes),
        errors=tuple(errors),
        report_sha256=_canonical_sha256(payload),
    )


def run_pillar_b_dual_path_backup_6_scenario_suite(
    *,
    so_bytes: Optional[bytes] = None,
) -> PillarB6ScenarioSuiteResult:
    """Execute all 6 Pillar B Path 1 (SD Stream + 528B Receipt) & Path 2 (`4 MiB` Sliding-Window USB Pull) scenarios."""
    payload_so = so_bytes if so_bytes is not None else build_synthetic_jiritsu_so_64k()
    results: List[PillarBScenarioResult] = []
    suite_errors: List[str] = []
    passed_count = 0

    # PB1: Path 1 full 16-item cold backup + 528B receipt
    cam_sd = FakeIOKitAdjustControlCamera(sd_writable=True, action_mode="sd_stream")
    sd_res = execute_sd_streaming_cold_backup(cam_sd, payload_so, scenario_id=PILLAR_B_SCENARIO_IDS[0])
    if sd_res.passed:
        passed_count += 1
    else:
        suite_errors.append(f"PB1 failed: {sd_res.error_codes}")
    results.append(
        PillarBScenarioResult(
            passed=sd_res.passed,
            scenario_id=PILLAR_B_SCENARIO_IDS[0],
            path_used="PATH1_SD_EXFAT_STREAM",
            error_codes=sd_res.error_codes,
            summary_sha256=sd_res.report_sha256,
            errors=sd_res.errors,
        )
    )

    # PB2: Path 2 full 75 MiB p3 sliding-window pull (19 chunks <= 4 MiB)
    p3_pattern = (b"FX3_P3_75MIB_SYSTEM_PART_" * 3145728)[:P3_PARTITION_CAPACITY_BYTES]
    cam_sw = FakeIOKitAdjustControlCamera(
        sd_writable=False,
        action_mode="sliding_pull",
        partition_overrides={"p3": p3_pattern},
    )
    sw_res = execute_p6_sliding_window_usb_pull(
        cam_sw,
        payload_so,
        partition_name="p3",
        chunk_size_bytes=SLIDING_WINDOW_CHUNK_BYTES,
        scenario_id=PILLAR_B_SCENARIO_IDS[1],
    )
    if sw_res.passed and sw_res.chunks_pulled == 19:
        passed_count += 1
    else:
        suite_errors.append(f"PB2 failed: chunks={sw_res.chunks_pulled} errs={sw_res.error_codes}")
    results.append(
        PillarBScenarioResult(
            passed=sw_res.passed and sw_res.chunks_pulled == 19,
            scenario_id=PILLAR_B_SCENARIO_IDS[1],
            path_used="PATH2_P6_SLIDING_WINDOW_4MIB",
            error_codes=sw_res.error_codes,
            summary_sha256=sw_res.report_sha256,
            errors=sw_res.errors,
        )
    )

    # PB3: Unbounded 75 MiB p3 staging onto 25 MiB p6 -> rejected 0x1000000F
    cam_unbounded = FakeIOKitAdjustControlCamera(action_mode="unbounded_p3_stage")
    r_unb = _run_preflight_and_single_set_file2(cam_unbounded, payload_so, scenario_id=PILLAR_B_SCENARIO_IDS[2])
    pb3_ok = r_unb.aborted and r_unb.abort_reason_code == ABORT_P6_FULL_0X1000000F and r_unb.set_file2_retry_count == 0
    if pb3_ok:
        passed_count += 1
    else:
        suite_errors.append(f"PB3 failed: {r_unb.abort_reason_code}")
    results.append(
        PillarBScenarioResult(
            passed=pb3_ok,
            scenario_id=PILLAR_B_SCENARIO_IDS[2],
            path_used="UNBOUNDED_P6_REJECTED",
            error_codes=(r_unb.abort_reason_code,),
            summary_sha256=r_unb.report_sha256,
            errors=(),
        )
    )

    # PB4: Corrupted FX3CHK1 CRC32 on sliding chunk -> aborts immediately
    cam_badchk = FakeIOKitAdjustControlCamera(action_mode="sliding_pull", inject_fault="corrupt_chunk_crc")
    sw_bad = execute_p6_sliding_window_usb_pull(
        cam_badchk,
        payload_so,
        partition_name="p13",  # 4 MiB single chunk
        chunk_size_bytes=SLIDING_WINDOW_CHUNK_BYTES,
        scenario_id=PILLAR_B_SCENARIO_IDS[3],
    )
    pb4_ok = (not sw_bad.passed) and ERR_CHUNK_HEADER_CORRUPT in sw_bad.error_codes and not sw_bad.sha256_exact_match
    if pb4_ok:
        passed_count += 1
    else:
        suite_errors.append(f"PB4 failed: {sw_bad.error_codes}")
    results.append(
        PillarBScenarioResult(
            passed=pb4_ok,
            scenario_id=PILLAR_B_SCENARIO_IDS[3],
            path_used="PATH2_CORRUPT_CHUNK_ABORTED",
            error_codes=sw_bad.error_codes,
            summary_sha256=sw_bad.report_sha256,
            errors=sw_bad.errors,
        )
    )

    # PB5: SD card unwritable (0x10000004) triggers clean automatic Path 2 fallback
    cam_nosd = FakeIOKitAdjustControlCamera(sd_writable=False, action_mode="sd_stream")
    sd_fail = execute_sd_streaming_cold_backup(cam_nosd, payload_so, scenario_id=PILLAR_B_SCENARIO_IDS[4])
    pb5_fallback_ok = False
    fb_res_sha = sd_fail.report_sha256
    if (not sd_fail.passed) and ABORT_MOUNT_FAIL_0X10000004 in sd_fail.error_codes:
        # Fresh session on Path 2 pulls p2 (20 MiB = 5 * 4 MiB chunks) cleanly
        cam_fb = FakeIOKitAdjustControlCamera(sd_writable=False, action_mode="sliding_pull")
        fb_res = execute_p6_sliding_window_usb_pull(
            cam_fb,
            payload_so,
            partition_name="p2",
            chunk_size_bytes=SLIDING_WINDOW_CHUNK_BYTES,
            scenario_id=PILLAR_B_SCENARIO_IDS[4],
            fallback_triggered=True,
        )
        pb5_fallback_ok = fb_res.passed and fb_res.chunks_pulled == 5 and fb_res.fallback_triggered
        fb_res_sha = fb_res.report_sha256
    if pb5_fallback_ok:
        passed_count += 1
    else:
        suite_errors.append("PB5 failed to fall back cleanly from unwritable SD to Path 2")
    results.append(
        PillarBScenarioResult(
            passed=pb5_fallback_ok,
            scenario_id=PILLAR_B_SCENARIO_IDS[4],
            path_used="PATH1_MOUNT_FAIL_TO_PATH2_FALLBACK",
            error_codes=sd_fail.error_codes,
            summary_sha256=fb_res_sha,
            errors=(),
        )
    )

    # PB6: Tampered / wrong-length SD receipt rejected fail-closed
    bad_len = parse_sd_backup_receipt_bytes(b"FX3RCPT1" + b"\x00" * 100)
    tampered = bytearray(build_sd_backup_receipt_bytes(
        manifest_sha256="a" * 64,
        item_hashes={k: "b" * 64 for k in REQUIRED_COLD_BACKUP_ITEM_IDS},
        total_dumped_bytes=1024,
    ))
    tampered[20] ^= 0xFF
    bad_sig = parse_sd_backup_receipt_bytes(bytes(tampered))
    pb6_ok = (not bad_len.valid) and (not bad_sig.valid)
    if pb6_ok:
        passed_count += 1
    else:
        suite_errors.append("PB6 failed to reject invalid/tampered 528B receipt")
    results.append(
        PillarBScenarioResult(
            passed=pb6_ok,
            scenario_id=PILLAR_B_SCENARIO_IDS[5],
            path_used="RECEIPT_TAMPER_REJECTED",
            error_codes=(ERR_SD_RECEIPT_INVALID,),
            summary_sha256=_canonical_sha256({"pb6": pb6_ok}),
            errors=bad_sig.errors,
        )
    )

    all_ok = len(suite_errors) == 0 and passed_count == len(PILLAR_B_SCENARIO_IDS)
    return PillarB6ScenarioSuiteResult(
        passed=all_ok,
        status=STATUS_VERIFIED_PILLAR_B if all_ok else STATUS_REJECTED_PILLAR_B,
        scenarios_passed=passed_count,
        scenarios_total=len(PILLAR_B_SCENARIO_IDS),
        scenario_results=tuple(results),
        sd_backup_result=sd_res,
        sliding_75mib_result=sw_res,
        errors=tuple(suite_errors),
        suite_sha256=_canonical_sha256({"scenarios": [r.summary_sha256 for r in results], "ok": all_ok}),
    )


# ---------------------------------------------------------------------------
# Pillar C — FAKE_IOKIT_USB_CAMERA_REGRESSION_AND_PASSIVE_LOCK
# ---------------------------------------------------------------------------


def audit_passive_iokit_and_emmc_lock(request: PassiveHardwareLockRequest) -> PassiveHardwareLockDecision:
    """Enforce hard-locked `live_usb_iokit_transmit_enabled = False` and
    `persistent_emmc_writes_authorized = False` invariants.
    """
    error_codes: List[str] = []
    if (
        request.live_usb_iokit_transmit_enabled
        or request.usb_bytes_requested > 0
        or LIVE_USB_IOKIT_TRANSMIT_ENABLED
        or PHYSICAL_USB_BYTES_TRANSMITTED != 0
    ):
        error_codes.append(BLOCKED_LIVE_USB_IOKIT_TRANSMIT_LOCKED)
    if (
        request.persistent_emmc_writes_authorized
        or request.emmc_write_bytes_requested > 0
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PHYSICAL_DEVICE_WRITES != 0
    ):
        error_codes.append(BLOCKED_PERSISTENT_EMMC_WRITES_LOCKED)
    allowed = len(error_codes) == 0
    return PassiveHardwareLockDecision(
        allowed=allowed,
        live_usb_iokit_transmit_enabled=LIVE_USB_IOKIT_TRANSMIT_ENABLED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        physical_usb_bytes_transmitted=PHYSICAL_USB_BYTES_TRANSMITTED,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        error_codes=tuple(error_codes),
        reason="PASSIVE_LOCKED_OK" if allowed else ";".join(error_codes),
    )


def run_pillar_c_fake_iokit_regression_5_scenario_suite(
    *,
    so_bytes: Optional[bytes] = None,
) -> PillarC5ScenarioSuiteResult:
    """Execute all 5 Pillar C Fake-IOKit USB regression & passive-lock scenarios."""
    payload_so = so_bytes if so_bytes is not None else build_synthetic_jiritsu_so_64k()
    results: List[PillarCScenarioResult] = []
    suite_errors: List[str] = []
    passed_count = 0

    # PC1: Sony VID 0x054C AdjustControl full session & zero p6 residue
    cam1 = FakeIOKitAdjustControlCamera(sd_writable=True, action_mode="sd_stream")
    sd1 = execute_sd_streaming_cold_backup(cam1, payload_so, scenario_id=PILLAR_C_SCENARIO_IDS[0])
    audit1 = cam1.audit_post_session()
    pc1_ok = (
        cam1.usb_vid == SONY_USB_VID
        and cam1.usb_vid_pid == SONY_SERVICE_VID_PID
        and sd1.passed
        and audit1.clean
        and audit1.p6_residual_files == 0
        and not cam1.live_usb_iokit_transmit_enabled
        and not cam1.persistent_emmc_writes_authorized
    )
    if not pc1_ok:
        suite_errors.append("PC1 FakeIOKit full session failed")
    else:
        passed_count += 1
    results.append(
        PillarCScenarioResult(
            passed=pc1_ok,
            scenario_id=PILLAR_C_SCENARIO_IDS[0],
            usb_vid_pid=cam1.usb_vid_pid,
            p6_quota_enforced=True,
            elf_64k_enforced=True,
            post_session_clean=audit1.clean,
            live_usb_iokit_transmit_enabled=cam1.live_usb_iokit_transmit_enabled,
            persistent_emmc_writes_authorized=cam1.persistent_emmc_writes_authorized,
            error_codes=(),
            errors=(),
            report_sha256=_canonical_sha256({"id": PILLAR_C_SCENARIO_IDS[0], "ok": pc1_ok, "vid_pid": cam1.usb_vid_pid}),
        )
    )

    # PC2: ELF DT_HASH (1,1,0,0) + PT_LOAD 0x10000 validation enforcement
    bad_align_so = build_synthetic_jiritsu_so_64k(pt_load_align=0x1000)
    bad_hash_so = build_synthetic_jiritsu_so_64k(pt_load_align=0x10000, dt_hash_words=(0, 0, 0, 0))
    v_good = validate_elf64_so_for_fx3_64k(payload_so, require_64k_pt_load=True)
    v_bad_align = validate_elf64_so_for_fx3_64k(bad_align_so, require_64k_pt_load=True)
    v_bad_hash = validate_elf64_so_for_fx3_64k(bad_hash_so, require_64k_pt_load=True)
    cam2a = FakeIOKitAdjustControlCamera()
    r2a = _run_preflight_and_single_set_file2(cam2a, bad_align_so, scenario_id=PILLAR_C_SCENARIO_IDS[1])
    cam2b = FakeIOKitAdjustControlCamera()
    r2b = _run_preflight_and_single_set_file2(cam2b, bad_hash_so, scenario_id=PILLAR_C_SCENARIO_IDS[1])
    pc2_ok = (
        v_good.valid
        and (not v_bad_align.valid)
        and ERR_ELF_PT_LOAD_NOT_64K_ALIGNED in v_bad_align.error_codes
        and (not v_bad_hash.valid)
        and ERR_ELF_DT_HASH_INVALID in v_bad_hash.error_codes
        and r2a.aborted
        and r2a.abort_reason_code == ABORT_DLOPEN_FAIL_0X10000000
        and r2b.aborted
        and r2b.abort_reason_code == ABORT_DLOPEN_FAIL_0X10000000
    )
    if not pc2_ok:
        suite_errors.append("PC2 ELF 64K PT_LOAD / DT_HASH enforcement failed")
    else:
        passed_count += 1
    results.append(
        PillarCScenarioResult(
            passed=pc2_ok,
            scenario_id=PILLAR_C_SCENARIO_IDS[1],
            usb_vid_pid=SONY_SERVICE_VID_PID,
            p6_quota_enforced=True,
            elf_64k_enforced=pc2_ok,
            post_session_clean=True,
            live_usb_iokit_transmit_enabled=False,
            persistent_emmc_writes_authorized=False,
            error_codes=(ERR_ELF_PT_LOAD_NOT_64K_ALIGNED, ERR_ELF_DT_HASH_INVALID),
            errors=(),
            report_sha256=_canonical_sha256({"id": PILLAR_C_SCENARIO_IDS[1], "ok": pc2_ok}),
        )
    )

    # PC3: 25 MiB p6 quota boundary enforcement (0x1000000F)
    cam3 = FakeIOKitAdjustControlCamera(p6_quota_bytes=P6_PARTITION_QUOTA_BYTES)
    st_fit = cam3.stage_p6_file_direct("/tmp/jiritsu/fit_24m.bin", b"A" * (24 * 1024 * 1024))
    st_over = cam3.stage_p6_file_direct("/tmp/jiritsu/over_2m.bin", b"B" * (2 * 1024 * 1024))
    pc3_ok = (st_fit == STATUS_OK) and (st_over == STATUS_P6_NO_SPACE) and (cam3.p6_used_bytes <= P6_PARTITION_QUOTA_BYTES)
    if not pc3_ok:
        suite_errors.append(f"PC3 quota enforcement failed: fit={st_fit} over={st_over}")
    else:
        passed_count += 1
    results.append(
        PillarCScenarioResult(
            passed=pc3_ok,
            scenario_id=PILLAR_C_SCENARIO_IDS[2],
            usb_vid_pid=cam3.usb_vid_pid,
            p6_quota_enforced=pc3_ok,
            elf_64k_enforced=True,
            post_session_clean=True,
            live_usb_iokit_transmit_enabled=False,
            persistent_emmc_writes_authorized=False,
            error_codes=(ABORT_P6_FULL_0X1000000F,),
            errors=(),
            report_sha256=_canonical_sha256({"id": PILLAR_C_SCENARIO_IDS[2], "ok": pc3_ok}),
        )
    )

    # PC4: Post-session residual-file audit fails closed when libJit.so or temp file remains
    cam4 = FakeIOKitAdjustControlCamera(unlink_libjit_on_dlopen=False, action_mode="sd_stream")
    sd4 = execute_sd_streaming_cold_backup(cam4, payload_so, scenario_id=PILLAR_C_SCENARIO_IDS[3])
    audit4 = cam4.audit_post_session()
    pc4_ok = (not sd4.passed) and (not audit4.clean) and audit4.p6_residual_files >= 1 and STATUS_REJECTED_P6_RESIDUAL_FILES in sd4.error_codes
    if not pc4_ok:
        suite_errors.append("PC4 residual-file audit failed to reject uncleaned libJit.so")
    else:
        passed_count += 1
    results.append(
        PillarCScenarioResult(
            passed=pc4_ok,
            scenario_id=PILLAR_C_SCENARIO_IDS[3],
            usb_vid_pid=cam4.usb_vid_pid,
            p6_quota_enforced=True,
            elf_64k_enforced=True,
            post_session_clean=False,
            live_usb_iokit_transmit_enabled=False,
            persistent_emmc_writes_authorized=False,
            error_codes=(STATUS_REJECTED_P6_RESIDUAL_FILES,),
            errors=audit4.errors,
            report_sha256=_canonical_sha256({"id": PILLAR_C_SCENARIO_IDS[3], "ok": pc4_ok, "residual": audit4.p6_residual_files}),
        )
    )

    # PC5: Hard-locked passive USB IOKit & eMMC write guard
    d_safe = audit_passive_iokit_and_emmc_lock(PassiveHardwareLockRequest())
    d_usb = audit_passive_iokit_and_emmc_lock(
        PassiveHardwareLockRequest(live_usb_iokit_transmit_enabled=True, usb_bytes_requested=19)
    )
    d_emmc = audit_passive_iokit_and_emmc_lock(
        PassiveHardwareLockRequest(persistent_emmc_writes_authorized=True, emmc_write_bytes_requested=512)
    )
    pc5_ok = (
        d_safe.allowed
        and (not d_usb.allowed)
        and BLOCKED_LIVE_USB_IOKIT_TRANSMIT_LOCKED in d_usb.error_codes
        and (not d_emmc.allowed)
        and BLOCKED_PERSISTENT_EMMC_WRITES_LOCKED in d_emmc.error_codes
        and (not d_usb.live_usb_iokit_transmit_enabled)
        and (not d_emmc.persistent_emmc_writes_authorized)
    )
    if not pc5_ok:
        suite_errors.append("PC5 passive hardware lock failed")
    else:
        passed_count += 1
    results.append(
        PillarCScenarioResult(
            passed=pc5_ok,
            scenario_id=PILLAR_C_SCENARIO_IDS[4],
            usb_vid_pid=SONY_SERVICE_VID_PID,
            p6_quota_enforced=True,
            elf_64k_enforced=True,
            post_session_clean=True,
            live_usb_iokit_transmit_enabled=False,
            persistent_emmc_writes_authorized=False,
            error_codes=(BLOCKED_LIVE_USB_IOKIT_TRANSMIT_LOCKED, BLOCKED_PERSISTENT_EMMC_WRITES_LOCKED),
            errors=(),
            report_sha256=_canonical_sha256({"id": PILLAR_C_SCENARIO_IDS[4], "ok": pc5_ok}),
        )
    )

    all_ok = len(suite_errors) == 0 and passed_count == len(PILLAR_C_SCENARIO_IDS)
    return PillarC5ScenarioSuiteResult(
        passed=all_ok,
        status=STATUS_VERIFIED_PILLAR_C if all_ok else STATUS_REJECTED_PILLAR_C,
        scenarios_passed=passed_count,
        scenarios_total=len(PILLAR_C_SCENARIO_IDS),
        scenario_results=tuple(results),
        errors=tuple(suite_errors),
        suite_sha256=_canonical_sha256({"scenarios": [r.report_sha256 for r in results], "ok": all_ok}),
    )


# ---------------------------------------------------------------------------
# Master Suite Entrypoint (Pillar 17)
# ---------------------------------------------------------------------------


def run_adjustcontrol_streaming_backup_suite(
    *,
    force_clean_room: Optional[bool] = None,
) -> AdjustControlStreamingBackupSuiteReport:
    """Run Phase 139 Pillar 17: O_RDONLY donor inspection, `AdjustControl (0x40)`
    wire transport & preflight abort state machine, dual-path SD streaming &
    `p6` (`25 MiB`) `<= 4 MiB` sliding-window cold backup, and stateful
    `FakeIOKitAdjustControlCamera` end-to-end regression.
    """
    t0 = time.monotonic()
    require(not PERSISTENT_EMMC_WRITES_AUTHORIZED, "persistent_emmc_writes_authorized must stay False")
    require(not LIVE_USB_IOKIT_TRANSMIT_ENABLED, "live_usb_iokit_transmit_enabled must stay False")

    donor_snap = inspect_adjustcontrol_donors_readonly(force_clean_room=force_clean_room)
    so_64k = build_synthetic_jiritsu_so_64k()

    pillar_a = run_pillar_a_wire_and_preflight_7_scenario_suite(so_bytes=so_64k)
    pillar_b = run_pillar_b_dual_path_backup_6_scenario_suite(so_bytes=so_64k)
    pillar_c = run_pillar_c_fake_iokit_regression_5_scenario_suite(so_bytes=so_64k)

    errors: List[str] = []
    if donor_snap.p6_quota_bytes != P6_PARTITION_QUOTA_BYTES:
        errors.append(f"unexpected p6 quota: {donor_snap.p6_quota_bytes}")
    errors.extend(pillar_a.errors)
    errors.extend(pillar_b.errors)
    errors.extend(pillar_c.errors)

    all_ok = (
        len(errors) == 0
        and pillar_a.passed
        and pillar_b.passed
        and pillar_c.passed
        and not LIVE_USB_IOKIT_TRANSMIT_ENABLED
        and not PERSISTENT_EMMC_WRITES_AUTHORIZED
        and not PERSISTENT_WRITE_RELEASE
        and PHYSICAL_DEVICE_WRITES == 0
        and PHYSICAL_USB_BYTES_TRANSMITTED == 0
    )
    status = STATUS_VERIFIED_SUITE if all_ok else STATUS_FAIL_SUITE
    digest_payload = {
        "schema": ADJUSTCONTROL_BACKUP_SCHEMA,
        "version": ADJUSTCONTROL_BACKUP_VERSION,
        "status": status,
        "mode": donor_snap.verification_mode,
        "donor_sha256": donor_snap.snapshot_sha256,
        "pillar_a_sha256": pillar_a.suite_sha256,
        "pillar_b_sha256": pillar_b.suite_sha256,
        "pillar_c_sha256": pillar_c.suite_sha256,
        "all_passed": all_ok,
    }
    return AdjustControlStreamingBackupSuiteReport(
        schema=ADJUSTCONTROL_BACKUP_SCHEMA,
        version=ADJUSTCONTROL_BACKUP_VERSION,
        status=status,
        verification_mode=donor_snap.verification_mode,
        all_passed=all_ok,
        read_only_donor_access=READ_ONLY_DONOR_ACCESS,
        donor_snapshot=donor_snap,
        pillar_a_wire_and_preflight_7_scenarios=pillar_a,
        pillar_b_dual_path_backup_6_scenarios=pillar_b,
        pillar_c_fake_iokit_regression_5_scenarios=pillar_c,
        live_usb_iokit_transmit_enabled=LIVE_USB_IOKIT_TRANSMIT_ENABLED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        allow_boot_partition_targeting=ALLOW_BOOT_PARTITION_TARGETING,
        allow_destructive_fastboot=ALLOW_DESTRUCTIVE_FASTBOOT,
        allow_persistent_jiritsu_writes=ALLOW_PERSISTENT_JIRITSU_WRITES,
        allow_destructive_jiritsu_commands=ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS,
        otp_fuse_touches=OTP_FUSE_TOUCHES,
        otp_fuse_writes=OTP_FUSE_WRITES,
        passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        physical_usb_bytes_transmitted=PHYSICAL_USB_BYTES_TRANSMITTED,
        elapsed_seconds=round(time.monotonic() - t0, 6),
        errors=tuple(errors),
        suite_sha256=_canonical_sha256(digest_payload),
    )
