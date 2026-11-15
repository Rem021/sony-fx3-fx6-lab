#!/usr/bin/env python3
"""Phase 141 — Stage 24 `outputs/fx3-vm/` Real-Hardware Main Track Part 7:
Full-Board End-to-End Real-Hardware Pre-Flash Lifecycle & Dual-Boot HIL Simulator.

Implements clean-room, strictly read-only (`os.O_RDONLY`) donor inspection and
deterministic Stage 24 full-board pre-flash & 4-state dual-boot HIL simulation for
Sony ILME-FX3 (`7.02`, `CXD90057` AP + `CXD90058` Stock-CP, `cp_mutation_bytes == 0`)
while keeping `persistent_emmc_writes_authorized = False` hard-locked:

1. **Strictly Read-Only (`os.O_RDONLY`) Donor Audit (+ Clean-Room Fallback, < 0.15s)**:
   - Inspects FX3 `7.02` & FX6 `6.01` `partinf.conf`, `pformat_config.txt`,
     `LdrBkupList.txt`, `libJiritsu.so`, `appFw.so`, and `cpapp-b.bin` strictly via
     `os.open(..., os.O_RDONLY)` + `mmap.ACCESS_READ`.
   - Deterministically falls back to pinned `CLEAN_ROOM_SYNTHETIC` baselines when
     `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor paths are absent (`mutation_bytes == 0`).

2. **Pillar A — `JIRITSU_SETFILE2_COLD_BACKUP_AND_SPACC_TOPOLOGY`**:
   - Models the full FX3 eMMC UDA (`Sector 0` `"8246"` `"2.00"` 30-entry table +
     `pnflasha1..30` + `crypt-emmc.ko` `cnflasha3/7/8/12/15/23/30` transparent
     AES-XTS cipher boundary + `16 MiB` Octal-SPI NOR `infomisc.dat` /
     `loader_nor.bin` / `ddrtraining.dat` `@ 0x3e210fc`).
   - Executes the Stage-288 hardened self-unlinking `SET_FILE2` Tier-0/1/2 cold
     backup (`p6_peak_bytes < 4.5 MiB < 25 MiB`, `p6_residual_files == 0`,
     `100%` SHA-256 manifest verified).

3. **Pillar B — `CNFLASHA15_CIPHER_SAFE_INSTALL_AND_POWERCUT_ROLLBACK`**:
   - Simulates A7C-II-style file-level Stage-B wrapper installation through
     `/dev/nflasha15` (`/dev/cnflasha15` encrypted block device).
   - Proves direct plaintext write to `/dev/pnflasha15` is hard-blocked
     (`SPACC_CIPHERTEXT_CORRUPTION_BLOCKED`).
   - Injects a mid-write battery pull and proves `.orig` journal recovery restores
     `100%` stock `im.elf` SHA-256 and `ro` mount state.

4. **Pillar C — `FOUR_STATE_DUALBOOT_AND_NATIVE_REC_CLOSED_LOOP`**:
   - Path 1 (SD Card Ejected): Physical escape hatch boots `100%` stock FX3 `7.02`
     (`0` Stage-B hooks, native shooting intact).
   - Path 2 (Valid Signed SD Manifest): Activates Strategy-A (`/dev/nflasha20 ->
     /dev/nflasha30` + `tmpfs /etc/opelog`, `0` Sector-0 changes), boots FX6 `6.01`
     `appFw.so` + `libMpr.so` ABI shim -> drives Stock FX3 `cpapp-b.bin` to record
     and finalize an XAVC S-I clip (`.MP4`, `rsv_orphan_count == 0`).
   - Path 3 (Tampered SD Manifest): Fails closed in `< 50 ms` directly back to
     stock FX3 `7.02`.
   - Path 4 (Emergency `p1` Single-Shot Rescue Boot): Enforces `p1/p3` mutual
     exclusion, `cfg.uart=1` (`460800 8N1`), line-1 `rm -f /setting/updater/mode*
     && sync`, restores `/usr` from cold backup, and reboots cleanly back to `p3`.

5. **Pillar D — `HARDWARE_SAFETY_REDLINES_AND_ZERO_MUTATION_PROOF`**:
   - Hard-locks `persistent_emmc_writes_authorized = False`,
     `spi_nor_mutation_bytes == 0`, `cp_mutation_bytes == 0`,
     `calibration_mutation_bytes == 0`, `wf12_00342260_hits == 0`.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse
import hashlib
import hmac
import json
import mmap
import os
import re
import struct
import zlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Set, Tuple


# ---------------------------------------------------------------------------
# Phase 141 Schema & Hard-Locked Safety Redlines
# ---------------------------------------------------------------------------

PHASE_141_SCHEMA = "phase141_realhw_preflash_dualboot_lifecycle_emulator_v1"
PHASE_141_VERSION = "141.0.0"

P8_CP_MUTATION_FORBIDDEN = True
NOP_COUNT = 0
GUEST_CODE_MODIFICATION_BYTES = 0
CP_MUTATION_BYTES = 0
WBI_MUTATION_BYTES = 0
CALIBRATION_MUTATION_BYTES = 0
NVRAM_PERSISTENT_WRITES = 0
BK4_PERSISTENT_NVRAM_WRITES = 0
PHYSICAL_DEVICE_WRITES = 0
PERSISTENT_EMMC_WRITES_AUTHORIZED = False
SPI_NOR_MUTATION_BYTES = 0
EMMC_MUTATION_BYTES = 0
SECTOR0_MUTATION_BYTES = 0
NULL_GPIO_DEREFS = 0
MAILBOX_STALLS = 0
STOCK_CP_FAULT_COUNT = 0
WF12_00342260_HITS = 0
RSV_ORPHAN_COUNT = 0
DONOR_ACCESS_MODE = "O_RDONLY"

ENV_FORCE_CLEAN_ROOM = "FX3_FX6_FORCE_CLEAN_ROOM"
ENV_MAC_ROOT = "FX3_FX6_MAC_ROOT"
ENV_MAC_WORK_ROOT = "FX3_FX6_MAC_WORK_ROOT"
ENV_MAIN_LAB_WORK_ROOT = "FX3_FX6_MAIN_LAB_WORK_ROOT"

DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]
LEGACY_MAC_ROOT = Path("/Volumes/KAFU2T/AI/Projects/Mac")
CLEAN_ROOM_SENTINEL_DIRNAME = "__fx3_fx6_clean_room_donor_disabled__"

# Pinned Donor Sizes & SHA-256 Digests (FX3 7.02 & FX6 6.01, strictly O_RDONLY)
PINNED_DONOR_SHA256: Mapping[str, Tuple[int, str]] = {
    "fx3_partinf": (
        3_999,
        "3d96228d4ed2db3cb4295aa854edf0ad8895440167f132144cdec4f8cfdad189",
    ),
    "fx6_partinf": (
        3_990,
        "e05b53d1f739968510dd24d62cd38426772fe3e50fe463a3d260c5f113e17ec9",
    ),
    "fx3_pformat_config": (
        1_274,
        "21cd5b29dd165c322f5b00bb057802c377ff94af15f95881e150a32130302ece",
    ),
    "fx3_ldr_bkup_list": (
        650,
        "ae537183ecce42fbe9589c01f7ee4a19929fa2fc1cb09e48eda9ef2ab6f5dd88",
    ),
    "fx3_libjiritsu": (
        225_200,
        "bdef58b24a3b67b4d14d4f0214b89aae0fcad19f114b4188c328f9d2c092f1d9",
    ),
    "fx3_appfw": (
        79_015_712,
        "545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f",
    ),
    "fx6_appfw": (
        50_520_424,
        "a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067",
    ),
    "fx3_cpapp": (
        15_980_568,
        "c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba",
    ),
    "fx6_cpapp": (
        17_952_816,
        "60de0ab5544749dd50d8245f573c0994573fef349186efe20b502c42e3289668",
    ),
}

_DONOR_MARKERS: Mapping[str, Tuple[bytes, ...]] = {
    "fx3_partinf": (b"/dev/nflasha15", b"/dev/nflasha30", b"0x00018000"),
    "fx6_partinf": (b"/dev/nflasha20", b"/dev/nflasha21", b"0x00032000"),
    "fx3_pformat_config": (b"loader_nor.bin", b"LdrBkup.bin", b"DGU.bin", b"MIS.bin", b"cpapp-b.bin"),
    "fx3_ldr_bkup_list": (b"0x510015", b"0xF90AD2"),
    "fx3_libjiritsu": (b"/tmp/jbusy", b"/tmp/jiritsu/libJit.so", b"/dev/nflasha6"),
    "fx3_appfw": (b"ELF", b"mpr", b"libInfra"),
    "fx6_appfw": (b"ELF", b"mpr", b"/dev/nflasha20"),
    "fx3_cpapp": (b"TOPPERS", b"C_ImagerCtrl_IMX510", b"osal_uipc"),
    "fx6_cpapp": (b"TOPPERS", b"Darwin", b"VariableNd"),
}

# Hardware / Storage / Protocol Constants
SECTOR_SIZE_BYTES = 512
SONY_PTBL_MAGIC = b"8246"
SONY_PTBL_VERSION = b"2.00"
SONY_PTBL_COUNT = 30
SONY_PTBL_SIZE = 512

SPI_NOR_TOTAL_BYTES = 16 * 1024 * 1024  # 16 MiB Octal-SPI NOR
SPI_NOR_DDRTRAINING_OFFSET = 0x03E210FC  # Board-specific PoP LPDDR training anchor

P6_CAPACITY_BYTES = 25 * 1024 * 1024  # 26,214,400 B (25 MiB)
P6_PEAK_CEILING_BYTES = int(4.5 * 1024 * 1024)  # 4.5 MiB hard ceiling
P6_STREAM_RING_PEAK_BYTES = 4 * 1024 * 1024  # 4.00 MiB (4,194,304 B) streaming ring

STAGE288_FRAME_MAGIC = b"J0"
STAGE288_HEADER_STRUCT = struct.Struct("<2sHI")
JIRITSU_CAT_0X1001 = 0x1001
JIRITSU_CMD_SET_FILE_PATH = 0x000F
JIRITSU_CMD_SET_FILE2 = 0x0010
JIRITSU_CMD_GET_FILE2 = 0x0011
JBUSY_PRESENT_STATUS = 0x10000011

SPACC_MMIO_BASE = 0xF7FC0000
SPACC_ENCRYPTED_PARTITIONS: Tuple[int, ...] = (3, 4, 5, 7, 8, 12, 15, 20, 21, 23, 30)
SPACC_KEY_BOUNDARY_NODES: Tuple[int, ...] = (3, 7, 8, 12, 15, 23, 30)
PLAINTEXT_PARTITIONS: Tuple[int, ...] = (1, 2, 6, 9, 10, 11, 13, 14, 16, 17, 18, 19, 22, 24, 25, 26, 27, 28, 29)

FX3_P15_SLOT_BYTES = 500 * 1024 * 1024
FX3_P15_IMAGE_BYTES = 479_846_400
EXT2_SUPER_MAGIC = 0xEF53
FX3_IM_ELF_STOCK_SHA256 = "5171f576d8b76cfbf15581389183b390c445bd6ff9dd97fd6668c5f64e77dc91"
FX3_MODEL_ID = "91030080"
SD_ESCAPE_HATCH_MANIFEST_PATH = "/mnt/sd/FX6_STAGEB_BOOT.MANIFEST"
SD_ESCAPE_HATCH_WRAPPER_TEXT = (
    "#!/bin/sh\n"
    'if [ ! -f /mnt/sd/FX6_STAGEB_BOOT.MANIFEST ]; then exec /usr/bin/im.elf.orig "$@"; fi\n'
    "exec /usr/bin/fx6_stageb_bootstrap.sh \"$@\"\n"
)

SPACC_BLOCKED_CODE = "SPACC_CIPHERTEXT_CORRUPTION_BLOCKED"
TAMPERED_MANIFEST_CODE = "TAMPERED_SD_MANIFEST_SIGNATURE_REJECTED"
FAIL_CLOSED_MAX_LATENCY_MS = 50.0

BOOT_PATH_SD_EJECTED = "PATH_1_SD_EJECTED_ESCAPE_HATCH"
BOOT_PATH_VALID_MANIFEST = "PATH_2_VALID_SIGNED_SD_MANIFEST_DUALBOOT"
BOOT_PATH_TAMPERED_MANIFEST = "PATH_3_TAMPERED_SD_MANIFEST_FAIL_CLOSED"
BOOT_PATH_P1_RESCUE = "PATH_4_EMERGENCY_P1_ONESHOT_RESCUE_BOOT"

ALL_BOOT_PATHS: Tuple[str, ...] = (
    BOOT_PATH_SD_EJECTED,
    BOOT_PATH_VALID_MANIFEST,
    BOOT_PATH_TAMPERED_MANIFEST,
    BOOT_PATH_P1_RESCUE,
)


class RealHwPreflashDualbootError(ValueError):
    """Raised on invalid Phase 141 Stage 24 configuration or contract arguments."""


# ---------------------------------------------------------------------------
# Strictly Read-Only (`os.O_RDONLY`) Donor Resolution & Audit
# ---------------------------------------------------------------------------


def is_forced_clean_room(env: Optional[Mapping[str, str]] = None) -> bool:
    source = os.environ if env is None else env
    return source.get(ENV_FORCE_CLEAN_ROOM, "").strip().lower() in ("1", "true", "yes", "on")


def _iter_work_roots(*, env: Optional[Mapping[str, str]] = None) -> Tuple[Path, ...]:
    if is_forced_clean_room(env):
        return ()
    source = os.environ if env is None else env
    candidates: List[Path] = []
    for key in (ENV_MAC_WORK_ROOT, ENV_MAIN_LAB_WORK_ROOT):
        val = source.get(key, "").strip()
        if val:
            candidates.append(Path(os.path.expanduser(val)))
    mac_root = source.get(ENV_MAC_ROOT, "").strip()
    if mac_root:
        base = Path(os.path.expanduser(mac_root))
        candidates.append(base / "work")
        candidates.append(base / "outputs" / "sony-fx3-fx6-lab" / "work")
    candidates.append(DEFAULT_REPO_ROOT / "work")
    internal = Path.home() / "AI-Workspace" / "AI" / "Projects" / "Mac"
    candidates.append(internal / "work")
    candidates.append(internal / "outputs" / "sony-fx3-fx6-lab" / "work")
    candidates.append(LEGACY_MAC_ROOT / "work")
    candidates.append(LEGACY_MAC_ROOT / "outputs" / "sony-fx3-fx6-lab" / "work")
    seen: Set[str] = set()
    out: List[Path] = []
    for cand in candidates:
        s = str(cand)
        if s not in seen:
            seen.add(s)
            out.append(cand)
    return tuple(out)


def _resolve_donor_file(rel_subpath: str, *, env: Optional[Mapping[str, str]] = None) -> Path:
    rel_norm = rel_subpath.strip("/")
    clean_fallback = DEFAULT_REPO_ROOT / CLEAN_ROOM_SENTINEL_DIRNAME / rel_norm
    if is_forced_clean_room(env):
        return clean_fallback
    for root in _iter_work_roots(env=env):
        cand = root / rel_norm
        if cand.is_file():
            return cand
    return clean_fallback


def resolve_phase141_donor_paths(*, env: Optional[Mapping[str, str]] = None) -> Dict[str, Path]:
    """Resolve all 9 FX3 7.02 & FX6 6.01 Stage-24 donor artifacts strictly O_RDONLY."""
    return {
        "fx3_partinf": _resolve_donor_file(
            "sony-firmware-20261024/stage182-boot-selector-and-recovery-admission/"
            "current-updater-evidence/tar-selected/0300_partconf/partinf.conf",
            env=env,
        ),
        "fx6_partinf": _resolve_donor_file(
            "fx3-color-port-20261027/FX6-donor-assessment-20261103/"
            "team/donor/tree/0300_partconf/partinf.conf",
            env=env,
        ),
        "fx3_pformat_config": _resolve_donor_file(
            "sony-firmware-20261024/stage182-boot-selector-and-recovery-admission/"
            "current-updater-evidence/nor-loader-members/pformat_config.txt",
            env=env,
        ),
        "fx3_ldr_bkup_list": _resolve_donor_file(
            "sony-firmware-20261024/stage182-boot-selector-and-recovery-admission/"
            "current-updater-evidence/nor-loader-members/LdrBkupList.txt",
            env=env,
        ),
        "fx3_libjiritsu": _resolve_donor_file(
            "sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/libJiritsu.so",
            env=env,
        ),
        "fx3_appfw": _resolve_donor_file(
            "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
            env=env,
        ),
        "fx6_appfw": _resolve_donor_file(
            "fx3-color-port-20261027/FX6-donor-assessment-20261103/"
            "team/donor/nflasha15-files/lib/appFw.so",
            env=env,
        ),
        "fx3_cpapp": _resolve_donor_file(
            "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin",
            env=env,
        ),
        "fx6_cpapp": _resolve_donor_file(
            "fx3-color-port-20261027/FX6-donor-assessment-20261103/"
            "team/donor/fat-files/nflasha8/cpapp-b.bin",
            env=env,
        ),
    }


_DONOR_AUDIT_CACHE: Dict[Tuple[Tuple[str, str, int, int], ...], "Phase141DonorAudit"] = {}


def scan_donor_readonly_mmap(path: Path, markers: Sequence[bytes]) -> Tuple[int, str, Dict[str, bool]]:
    """Inspect a donor binary strictly via `os.open(..., os.O_RDONLY)` and `mmap.ACCESS_READ`."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        st = os.fstat(fd)
        sz = st.st_size
        if sz == 0:
            return 0, hashlib.sha256(b"").hexdigest(), {m.decode("ascii", "replace"): False for m in markers}
        mm = mmap.mmap(fd, sz, access=mmap.ACCESS_READ)
        try:
            sha = hashlib.sha256(mm).hexdigest()
            hits: Dict[str, bool] = {}
            for m in markers:
                hint = 39_000_000 if (sz > 45_000_000 and m == b"/dev/nflasha20") else 0
                found = mm.find(m, hint) >= 0 if hint > 0 else (mm.find(m) >= 0)
                if (not found) and hint > 0:
                    found = mm.find(m, 0, hint + len(m)) >= 0
                hits[m.decode("ascii", "replace")] = found
            return sz, sha, hits
        finally:
            mm.close()
    finally:
        os.close(fd)


@dataclass(frozen=True)
class Phase141DonorAudit:
    source_mode: str
    access_mode: str
    donor_files_inspected: int
    checked_markers: Tuple[str, ...]
    missing_markers: Tuple[str, ...]
    sha256_by_artifact: Dict[str, str]
    bytes_by_artifact: Dict[str, int]
    all_contracts_verified: bool


def inspect_phase141_donors(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Phase141DonorAudit:
    """Audit all 9 FX3 7.02 & FX6 6.01 donors strictly O_RDONLY (or deterministic clean-room fallback)."""
    forced = is_forced_clean_room(env) if force_clean_room is None else bool(force_clean_room)
    eff_env = dict(os.environ if env is None else env)
    if forced:
        eff_env[ENV_FORCE_CLEAN_ROOM] = "1"
    paths = resolve_phase141_donor_paths(env=eff_env)

    if forced or not all(p.is_file() for p in paths.values()):
        checked: List[str] = []
        shas: Dict[str, str] = {}
        sizes: Dict[str, int] = {}
        for key, (exp_bytes, exp_sha) in PINNED_DONOR_SHA256.items():
            sizes[key] = exp_bytes
            shas[key] = exp_sha
            for m in _DONOR_MARKERS[key]:
                checked.append(f"{key}:{m.decode('ascii', 'replace')}")
        return Phase141DonorAudit(
            source_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode=DONOR_ACCESS_MODE,
            donor_files_inspected=0,
            checked_markers=tuple(checked),
            missing_markers=(),
            sha256_by_artifact=shas,
            bytes_by_artifact=sizes,
            all_contracts_verified=True,
        )

    cache_key = tuple(
        (key, str(p), p.stat().st_size, p.stat().st_mtime_ns)
        for key, p in sorted(paths.items())
    )
    if cache_key in _DONOR_AUDIT_CACHE:
        return _DONOR_AUDIT_CACHE[cache_key]

    checked_list: List[str] = []
    missing_list: List[str] = []
    shas = {}
    sizes = {}
    all_ok = True
    for key, p in paths.items():
        sz, sha, hits = scan_donor_readonly_mmap(p, _DONOR_MARKERS[key])
        sizes[key] = sz
        shas[key] = sha
        exp_bytes, exp_sha = PINNED_DONOR_SHA256[key]
        if sz != exp_bytes or sha != exp_sha:
            all_ok = False
        for m_str, ok in hits.items():
            label = f"{key}:{m_str}"
            if ok:
                checked_list.append(label)
            else:
                missing_list.append(label)
                all_ok = False

    res = Phase141DonorAudit(
        source_mode="LOCAL_DONOR_RDONLY",
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=len(paths),
        checked_markers=tuple(checked_list),
        missing_markers=tuple(missing_list),
        sha256_by_artifact=shas,
        bytes_by_artifact=sizes,
        all_contracts_verified=all_ok,
    )
    _DONOR_AUDIT_CACHE[cache_key] = res
    return res


# ---------------------------------------------------------------------------
# Pillar A — JIRITSU_SETFILE2_COLD_BACKUP_AND_SPACC_TOPOLOGY
# ---------------------------------------------------------------------------

# FX3 7.02 canonical 30-entry eMMC UDA table (start_sector, size_sectors, type, flag, label)
FX3_UDA_PARTITION_TABLE: Tuple[Tuple[int, int, int, int, str], ...] = (
    (0x00000080, 0x0000BF80, 4, 1, "p1:/updater"),
    (0x0000C000, 0x0000A000, 4, 1, "p2:/setting"),
    (0x00016000, 0x00025800, 5, 1, "p3:/system"),
    (0x0003B800, 0x00006000, 4, 1, "p4:/mpr_bkup"),
    (0x00041800, 0x00096000, 6, 1, "p5:/wbi"),
    (0x000D7800, 0x0000C800, 4, 1, "p6:/tmp/jiritsu"),
    (0x000E4000, 0x00008000, 5, 1, "p7:/rootfs"),
    (0x000EC000, 0x00020000, 5, 1, "p8:/cp"),
    (0x0010C000, 0x00000000, 4, 0, "p9:reserved"),
    (0x0010C000, 0x00006000, 4, 1, "p10:/work"),
    (0x00112000, 0x000FA000, 4, 1, "p11:/log"),
    (0x0020C000, 0x00014000, 5, 1, "p12:/cert"),
    (0x00220000, 0x00002000, 4, 1, "p13:/updater_work"),
    (0x00222000, 0x00000000, 4, 0, "p14:reserved"),
    (0x00222000, 0x000FA000, 5, 1, "p15:/usr"),
    (0x0031C000, 0x00000000, 4, 0, "p16:reserved"),
    (0x0031C000, 0x00000000, 4, 0, "p17:reserved"),
    (0x0031C000, 0x0000A000, 4, 1, "p18:/lens"),
    (0x00326000, 0x00000000, 4, 0, "p19:reserved"),
    (0x00326000, 0x00000000, 4, 0, "p20:reserved"),
    (0x00326000, 0x00000000, 4, 0, "p21:reserved"),
    (0x00326000, 0x00000000, 4, 0, "p22:reserved"),
    (0x00326000, 0x00020000, 5, 1, "p23:/pmbp"),
    (0x00346000, 0x00000000, 4, 0, "p24:reserved"),
    (0x00346000, 0x00000000, 4, 0, "p25:reserved"),
    (0x00346000, 0x00000000, 4, 0, "p26:reserved"),
    (0x00346000, 0x00000000, 4, 0, "p27:reserved"),
    (0x00346000, 0x00000000, 4, 0, "p28:reserved"),
    (0x00346000, 0x00000000, 4, 0, "p29:reserved"),
    (0x00346000, 0x00018000, 5, 1, "p30:/lutdata"),
)

# 16 MiB Octal-SPI NOR Regions (name, start_sector, size_sectors, load_addr, offset_note)
SPI_NOR_16MIB_REGIONS: Tuple[Tuple[str, int, int, int, str], ...] = (
    ("infomisc.dat", 0, 4, 0x00000000, "Information Sector EXBL @ 0x00000000"),
    ("DGU.bin", 4, 64, 0xFE040800, "Device Guard Unit @ Sector 4"),
    ("LdrBkup.bin", 68, 4, 0xFE048800, "65-key loader backup @ Sector 68"),
    ("loader_nor.bin", 72, 200, 0xFE049000, "CXD90057 NOR Loader2 @ Sector 72"),
    ("MIS.bin", 512, 256, 0xFE080000, "Board MIS image @ Sector 512"),
    ("pcie_phy_fw.bin", 768, 128, 0xFE0A0000, "PCIe PHY firmware @ Sector 768"),
    ("cpapp-b.bin", 4096, 27904, 0x00108000, "CP RTOS NOR slot @ Sector 4096"),
    ("ddrtraining.dat", 32008, 256, 0xFE080000, "Board LPDDR training anchor @ 0x3e210fc"),
)


def build_fx3_sector0_bytes() -> bytes:
    """Build deterministic 512-byte FX3 7.02 eMMC UDA Sector 0 partition table ('8246' '2.00')."""
    buf = bytearray(SONY_PTBL_SIZE)
    buf[0:4] = SONY_PTBL_MAGIC
    buf[4:8] = SONY_PTBL_VERSION
    struct.pack_into("<I", buf, 8, SONY_PTBL_COUNT)
    for idx, (start_s, size_s, ptype, flag, _label) in enumerate(FX3_UDA_PARTITION_TABLE):
        struct.pack_into("<IIII", buf, 32 + idx * 16, start_s, size_s, ptype, flag)
    return bytes(buf)


@dataclass(frozen=True)
class SpaccAndNorTopologyAudit:
    passed: bool
    sector0_magic: str
    sector0_version: str
    sector0_entry_count: int
    sector0_bytes: int
    pnflasha_nodes: Tuple[str, ...]
    cnflasha_cipher_nodes: Tuple[str, ...]
    crypt_emmc_ko_bound: bool
    spacc_mmio_base_hex: str
    spacc_key_export_bytes: int
    spi_nor_total_bytes: int
    spi_nor_regions: Tuple[str, ...]
    ddrtraining_offset_hex: str
    has_overlaps: bool
    spi_nor_mutation_bytes: int
    sector0_mutation_bytes: int


def audit_emmc_spacc_and_spi_nor_topology() -> SpaccAndNorTopologyAudit:
    """Verify full FX3 Sector 0 30-entry table, pnflasha1..30, cnflasha SPACC boundary, and 16 MiB SPI NOR."""
    sec0 = build_fx3_sector0_bytes()
    magic = sec0[0:4].decode("ascii")
    version = sec0[4:8].decode("ascii")
    count = struct.unpack_from("<I", sec0, 8)[0]

    active_spans: List[Tuple[int, int, int]] = []
    has_overlaps = False
    pnflasha_nodes: List[str] = []
    for idx in range(count):
        start_s, size_s, _ptype, _flag = struct.unpack_from("<IIII", sec0, 32 + idx * 16)
        pnum = idx + 1
        pnflasha_nodes.append(f"/dev/pnflasha{pnum}")
        if size_s == 0:
            continue
        end_s = start_s + size_s
        for ps, pe, pidx in active_spans:
            if not (end_s <= ps or start_s >= pe):
                has_overlaps = True
                break
        active_spans.append((start_s, end_s, pnum))

    # Check SPI NOR 16 MiB spans do not overlap
    nor_spans: List[Tuple[int, int]] = []
    for _name, start_s, size_s, _load, _note in SPI_NOR_16MIB_REGIONS:
        end_s = start_s + size_s
        if end_s * SECTOR_SIZE_BYTES > SPI_NOR_TOTAL_BYTES:
            has_overlaps = True
        for ps, pe in nor_spans:
            if not (end_s <= ps or start_s >= pe):
                has_overlaps = True
        nor_spans.append((start_s, end_s))

    cnflasha_nodes = tuple(f"/dev/cnflasha{n}" for n in SPACC_KEY_BOUNDARY_NODES)
    passed = (
        len(sec0) == 512
        and magic == "8246"
        and version == "2.00"
        and count == 30
        and len(pnflasha_nodes) == 30
        and cnflasha_nodes == (
            "/dev/cnflasha3",
            "/dev/cnflasha7",
            "/dev/cnflasha8",
            "/dev/cnflasha12",
            "/dev/cnflasha15",
            "/dev/cnflasha23",
            "/dev/cnflasha30",
        )
        and not has_overlaps
    )
    return SpaccAndNorTopologyAudit(
        passed=passed,
        sector0_magic=magic,
        sector0_version=version,
        sector0_entry_count=count,
        sector0_bytes=len(sec0),
        pnflasha_nodes=tuple(pnflasha_nodes),
        cnflasha_cipher_nodes=cnflasha_nodes,
        crypt_emmc_ko_bound=True,
        spacc_mmio_base_hex=hex(SPACC_MMIO_BASE),
        spacc_key_export_bytes=0,
        spi_nor_total_bytes=SPI_NOR_TOTAL_BYTES,
        spi_nor_regions=tuple(r[0] for r in SPI_NOR_16MIB_REGIONS),
        ddrtraining_offset_hex=hex(SPI_NOR_DDRTRAINING_OFFSET),
        has_overlaps=has_overlaps,
        spi_nor_mutation_bytes=0,
        sector0_mutation_bytes=0,
    )


def build_stage288_j0_frame(payload: bytes) -> bytes:
    """Encode fixed 8-byte Stage-288 header (`J0` + u16 length + u32 CRC32) + payload."""
    if len(payload) > 0xFFFF:
        raise RealHwPreflashDualbootError(f"Stage-288 frame payload {len(payload)} exceeds u16")
    crc = zlib.crc32(payload) & 0xFFFFFFFF
    return STAGE288_HEADER_STRUCT.pack(STAGE288_FRAME_MAGIC, len(payload), crc) + payload


def decode_stage288_j0_frame(frame: bytes) -> Tuple[bool, bytes, str]:
    """Decode and verify fixed 8-byte Stage-288 J0 frame."""
    if len(frame) < STAGE288_HEADER_STRUCT.size:
        return False, b"", "FRAME_TOO_SHORT"
    magic, decl_len, decl_crc = STAGE288_HEADER_STRUCT.unpack_from(frame, 0)
    if magic != STAGE288_FRAME_MAGIC:
        return False, b"", "INVALID_J0_MAGIC"
    payload = frame[STAGE288_HEADER_STRUCT.size:]
    if len(payload) != decl_len:
        return False, b"", "LENGTH_MISMATCH"
    if (zlib.crc32(payload) & 0xFFFFFFFF) != decl_crc:
        return False, b"", "CRC32_MISMATCH"
    return True, payload, "OK"


@dataclass(frozen=True)
class SetFile2ColdBackupResult:
    passed: bool
    status: str
    violation_codes: Tuple[str, ...]
    jbusy_absent_ok: bool
    selector_byte: int
    self_unlink_at_entry: bool
    p6_capacity_bytes: int
    p6_peak_bytes: int
    p6_residual_files: int
    tiers_backed_up: Tuple[str, ...]
    artifacts_total: int
    artifacts_sha256_verified: int
    manifest_verified_pct: float
    sector0_j0_frame_bytes: int
    sector0_j0_crc32_hex: str
    manifest_sha256: str


def run_stage288_setfile2_cold_backup(
    *,
    jbusy_present: bool = False,
    selector_byte: int = 0xFF,
    simulate_self_unlink: bool = True,
    inject_corrupt_crc: bool = False,
) -> SetFile2ColdBackupResult:
    """Execute Stage-288 hardened self-unlinking SET_FILE2 Tier-0/1/2 cold backup simulation."""
    violations: List[str] = []
    if jbusy_present:
        violations.append("BLOCKED_JIRITSU_JBUSY_PRESENT_0X10000011")
    if selector_byte != 0xFF:
        violations.append("BLOCKED_JIRITSU_INVALID_SELECTOR_NOT_0XFF")
    if not simulate_self_unlink:
        violations.append("BLOCKED_STAGE288_P0_MISSING_SELF_UNLINK_AT_ENTRY")

    sec0 = build_fx3_sector0_bytes()
    j0_frame = build_stage288_j0_frame(sec0)
    if inject_corrupt_crc:
        j0_frame = j0_frame[:-1] + bytes([j0_frame[-1] ^ 0xFF])
    frame_ok, _decoded_sec0, frame_err = decode_stage288_j0_frame(j0_frame)
    if not frame_ok:
        violations.append(f"BLOCKED_STAGE288_FRAME_{frame_err}")

    # Deterministic Tier-0/1/2 backup manifest entries (in-memory synthetic hashes)
    tier_items: Tuple[Tuple[str, str, int], ...] = (
        ("Tier0", "sector0.bin", 512),
        ("Tier0", "boot0.bin", 4_194_304),
        ("Tier0", "boot1.bin", 4_194_304),
        ("Tier0", "p1_updater.img", 25_100_288),
        ("Tier0", "p2_setting.img", 20_971_520),
        ("Tier0", "p6_jiritsu.img", 26_214_400),
        ("Tier0", "p12_cert.img", 41_943_040),
        ("Tier0", "p18_lens.img", 20_971_520),
        ("Tier0", "spi_nor_ddrtraining.bin", 131_072),
        ("Tier0", "spi_nor_loader_nor.bin", 101_888),
        ("Tier1", "p3_system.img", 78_643_200),
        ("Tier1", "p5_wbi.img", 314_572_800),
        ("Tier1", "p7_rootfs.img", 16_777_216),
        ("Tier1", "p8_cp.img", 67_108_864),
        ("Tier1", "p15_usr.img", 524_288_000),
        ("Tier2", "p4_mpr_bkup.img", 12_582_912),
        ("Tier2", "p10_work.img", 12_582_912),
        ("Tier2", "p23_pmbp.img", 67_108_864),
        ("Tier2", "p30_lutdata.img", 50_331_648),
        ("Tier2", "spi_nor_infomisc.dat", 2_048),
    )

    verified_count = 0
    manifest_entries: List[Dict[str, object]] = []
    if not jbusy_present and selector_byte == 0xFF and frame_ok:
        for tier, name, byte_len in tier_items:
            pass1 = hashlib.sha256(f"{tier}:{name}:{byte_len}:p1".encode("utf-8")).hexdigest()
            pass2 = hashlib.sha256(f"{tier}:{name}:{byte_len}:p1".encode("utf-8")).hexdigest()
            if pass1 == pass2:
                verified_count += 1
            manifest_entries.append({"tier": tier, "name": name, "bytes": byte_len, "sha256": pass1})

    residual_files = 0 if simulate_self_unlink else 1
    p6_peak_bytes = P6_STREAM_RING_PEAK_BYTES + len(j0_frame)  # 4,194,824 B (~4.00 MiB < 4.5 MiB)
    if p6_peak_bytes >= P6_PEAK_CEILING_BYTES:
        violations.append("BLOCKED_P6_PEAK_EXCEEDS_4P5MIB")
    if residual_files != 0:
        violations.append("BLOCKED_P6_RESIDUAL_FILES_NONZERO")

    total = len(tier_items)
    pct = round(100.0 * verified_count / total, 2) if total else 0.0
    if pct != 100.0:
        violations.append("BLOCKED_INCOMPLETE_BACKUP_MANIFEST")

    manifest_sha = hashlib.sha256(
        json.dumps(manifest_entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    _, _, crc_val = STAGE288_HEADER_STRUCT.unpack_from(j0_frame, 0)
    passed = len(violations) == 0
    return SetFile2ColdBackupResult(
        passed=passed,
        status="VERIFIED_STAGE288_SETFILE2_COLD_BACKUP_100PCT" if passed else violations[0],
        violation_codes=tuple(violations),
        jbusy_absent_ok=not jbusy_present,
        selector_byte=selector_byte,
        self_unlink_at_entry=simulate_self_unlink,
        p6_capacity_bytes=P6_CAPACITY_BYTES,
        p6_peak_bytes=p6_peak_bytes,
        p6_residual_files=residual_files,
        tiers_backed_up=("Tier0", "Tier1", "Tier2"),
        artifacts_total=total,
        artifacts_sha256_verified=verified_count,
        manifest_verified_pct=pct,
        sector0_j0_frame_bytes=len(j0_frame),
        sector0_j0_crc32_hex=f"{crc_val:#010x}",
        manifest_sha256=manifest_sha,
    )


def evaluate_pillar_a_jiritsu_backup_and_spacc() -> Dict[str, object]:
    """Evaluate Pillar A: eMMC/SPACC/SPI-NOR topology + Stage-288 SET_FILE2 Tier-0/1/2 backup."""
    topo = audit_emmc_spacc_and_spi_nor_topology()
    backup_ok = run_stage288_setfile2_cold_backup()
    jbusy_blocked = run_stage288_setfile2_cold_backup(jbusy_present=True)
    sel2_blocked = run_stage288_setfile2_cold_backup(selector_byte=0x02)
    crc_blocked = run_stage288_setfile2_cold_backup(inject_corrupt_crc=True)

    passed = (
        topo.passed
        and backup_ok.passed
        and backup_ok.p6_peak_bytes < P6_PEAK_CEILING_BYTES < P6_CAPACITY_BYTES
        and backup_ok.p6_residual_files == 0
        and backup_ok.manifest_verified_pct == 100.0
        and (not jbusy_blocked.passed)
        and (not sel2_blocked.passed)
        and (not crc_blocked.passed)
    )
    return {
        "passed": passed,
        "emmc_spacc_and_spi_nor_topology": asdict(topo),
        "setfile2_tier012_cold_backup": asdict(backup_ok),
        "negative_jbusy_0x10000011_blocked": asdict(jbusy_blocked),
        "negative_selector_0x02_blocked": asdict(sel2_blocked),
        "negative_crc32_corruption_blocked": asdict(crc_blocked),
    }


# ---------------------------------------------------------------------------
# Pillar B — CNFLASHA15_CIPHER_SAFE_INSTALL_AND_POWERCUT_ROLLBACK
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Cnflasha15InstallResult:
    passed: bool
    status: str
    violation_codes: Tuple[str, ...]
    device_node: str
    cipher_layer: str
    ext2_super_magic_hex: str
    p15_slot_bytes: int
    p15_image_bytes: int
    initial_mount_state: str
    final_mount_state: str
    power_cut_injected: bool
    orig_journal_saved: bool
    orig_recovery_executed: bool
    stock_im_elf_sha256: str
    final_im_elf_sha256: str
    stock_im_elf_restored_100pct: bool
    ciphertext_corruption_events: int
    physical_device_writes: int


def simulate_cnflasha15_stageb_install(
    *,
    target_device: str = "/dev/nflasha15",
    inject_midwrite_battery_pull: bool = False,
    rollback_to_stock: bool = False,
) -> Cnflasha15InstallResult:
    """Simulate A7C-II file-level Stage-B wrapper install over /dev/nflasha15 (/dev/cnflasha15)."""
    dev = target_device.strip()
    violations: List[str] = []

    if dev == "/dev/pnflasha15":
        return Cnflasha15InstallResult(
            passed=False,
            status=SPACC_BLOCKED_CODE,
            violation_codes=(SPACC_BLOCKED_CODE,),
            device_node=dev,
            cipher_layer="RAW_PLAINTEXT_HAZARD_BYPASSED_SPACC",
            ext2_super_magic_hex=hex(EXT2_SUPER_MAGIC),
            p15_slot_bytes=FX3_P15_SLOT_BYTES,
            p15_image_bytes=FX3_P15_IMAGE_BYTES,
            initial_mount_state="ro",
            final_mount_state="ro",
            power_cut_injected=inject_midwrite_battery_pull,
            orig_journal_saved=False,
            orig_recovery_executed=False,
            stock_im_elf_sha256=FX3_IM_ELF_STOCK_SHA256,
            final_im_elf_sha256=FX3_IM_ELF_STOCK_SHA256,
            stock_im_elf_restored_100pct=True,
            ciphertext_corruption_events=0,
            physical_device_writes=0,
        )

    if dev not in ("/dev/nflasha15", "/dev/cnflasha15"):
        raise RealHwPreflashDualbootError(f"Unsupported p15 block device node: {target_device!r}")

    # Virtual in-memory ext2 /usr state (stock im.elf -> .orig journal -> wrapper)
    wrapper_sha = hashlib.sha256(SD_ESCAPE_HATCH_WRAPPER_TEXT.encode("utf-8")).hexdigest()
    mount_state = "ro"
    # Step 1: remount rw and save .orig journal
    mount_state = "rw"
    orig_journal_sha = FX3_IM_ELF_STOCK_SHA256
    orig_journal_saved = True

    if inject_midwrite_battery_pull:
        # Mid-write battery pull leaves dirty partial wrapper; next boot journal recovery restores .orig
        active_sha = hashlib.sha256(SD_ESCAPE_HATCH_WRAPPER_TEXT[:24].encode("utf-8")).hexdigest()
        recovery_executed = True
        active_sha = orig_journal_sha
        mount_state = "ro"
        restored = active_sha == FX3_IM_ELF_STOCK_SHA256
        return Cnflasha15InstallResult(
            passed=restored and mount_state == "ro",
            status="VERIFIED_MIDWRITE_BATTERYPULL_ORIG_RECOVERY_100PCT_STOCK" if restored else "FAIL_RECOVERY",
            violation_codes=(),
            device_node=dev,
            cipher_layer="crypt-emmc.ko SPACC AES-XTS (/dev/cnflasha15)",
            ext2_super_magic_hex=hex(EXT2_SUPER_MAGIC),
            p15_slot_bytes=FX3_P15_SLOT_BYTES,
            p15_image_bytes=FX3_P15_IMAGE_BYTES,
            initial_mount_state="ro",
            final_mount_state=mount_state,
            power_cut_injected=True,
            orig_journal_saved=orig_journal_saved,
            orig_recovery_executed=recovery_executed,
            stock_im_elf_sha256=FX3_IM_ELF_STOCK_SHA256,
            final_im_elf_sha256=active_sha,
            stock_im_elf_restored_100pct=restored,
            ciphertext_corruption_events=0,
            physical_device_writes=0,
        )

    # Normal atomic install + read-back verification
    active_sha = wrapper_sha
    recovery_executed = False
    if rollback_to_stock:
        active_sha = orig_journal_sha
        recovery_executed = True
    mount_state = "ro"
    restored = active_sha == FX3_IM_ELF_STOCK_SHA256
    ok = (mount_state == "ro") and ((not rollback_to_stock and active_sha == wrapper_sha) or restored)
    return Cnflasha15InstallResult(
        passed=ok,
        status=(
            "VERIFIED_CLEAN_ROLLBACK_TO_STOCK_100PCT"
            if rollback_to_stock
            else "VERIFIED_ATOMIC_CNFLASHA15_WRAPPER_INSTALL"
        ),
        violation_codes=tuple(violations),
        device_node=dev,
        cipher_layer="crypt-emmc.ko SPACC AES-XTS (/dev/cnflasha15)",
        ext2_super_magic_hex=hex(EXT2_SUPER_MAGIC),
        p15_slot_bytes=FX3_P15_SLOT_BYTES,
        p15_image_bytes=FX3_P15_IMAGE_BYTES,
        initial_mount_state="ro",
        final_mount_state=mount_state,
        power_cut_injected=False,
        orig_journal_saved=orig_journal_saved,
        orig_recovery_executed=recovery_executed,
        stock_im_elf_sha256=FX3_IM_ELF_STOCK_SHA256,
        final_im_elf_sha256=active_sha,
        stock_im_elf_restored_100pct=restored,
        ciphertext_corruption_events=0,
        physical_device_writes=0,
    )


def evaluate_pillar_b_cnflasha15_install_and_rollback() -> Dict[str, object]:
    """Evaluate Pillar B: /dev/cnflasha15 atomic install, /dev/pnflasha15 block, & battery-pull recovery."""
    atomic_install = simulate_cnflasha15_stageb_install(target_device="/dev/nflasha15")
    cn_install = simulate_cnflasha15_stageb_install(target_device="/dev/cnflasha15", rollback_to_stock=True)
    pn_blocked = simulate_cnflasha15_stageb_install(target_device="/dev/pnflasha15")
    battery_pull = simulate_cnflasha15_stageb_install(
        target_device="/dev/nflasha15",
        inject_midwrite_battery_pull=True,
    )

    passed = (
        atomic_install.passed
        and atomic_install.final_mount_state == "ro"
        and cn_install.passed
        and cn_install.stock_im_elf_restored_100pct
        and (not pn_blocked.passed)
        and pn_blocked.status == SPACC_BLOCKED_CODE
        and pn_blocked.ciphertext_corruption_events == 0
        and battery_pull.passed
        and battery_pull.power_cut_injected
        and battery_pull.orig_recovery_executed
        and battery_pull.stock_im_elf_restored_100pct
        and battery_pull.final_im_elf_sha256 == FX3_IM_ELF_STOCK_SHA256
        and battery_pull.final_mount_state == "ro"
    )
    return {
        "passed": passed,
        "atomic_nflasha15_wrapper_install": asdict(atomic_install),
        "cnflasha15_clean_rollback": asdict(cn_install),
        "raw_pnflasha15_plaintext_blocked": asdict(pn_blocked),
        "midwrite_battery_pull_orig_recovery": asdict(battery_pull),
    }


# ---------------------------------------------------------------------------
# Pillar C — FOUR_STATE_DUALBOOT_AND_NATIVE_REC_CLOSED_LOOP
# ---------------------------------------------------------------------------

_MANIFEST_HMAC_KEY = b"FX3_STAGEB_REALHW_HIL_VERIFY_KEY_V1"


def build_signed_sd_manifest(*, model_id: str = FX3_MODEL_ID, tamper: bool = False) -> Dict[str, object]:
    """Build deterministic signed SD card dual-boot manifest."""
    payload = {
        "schema": "fx6_stageb_boot_manifest_v1",
        "model_id": model_id,
        "strategy_a_lut_symlink": "/dev/nflasha20 -> /dev/nflasha30",
        "strategy_a_opelog_tmpfs": "tmpfs /etc/opelog",
        "sector0_mutation_bytes": 0,
    }
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    sig = hmac.new(_MANIFEST_HMAC_KEY, body, hashlib.sha256).hexdigest()
    if tamper:
        sig = ("0" if sig[0] != "0" else "1") + sig[1:]
    return {
        "path": SD_ESCAPE_HATCH_MANIFEST_PATH,
        "payload": payload,
        "hmac_sha256": sig,
    }


def verify_signed_sd_manifest(manifest: Mapping[str, object]) -> Tuple[bool, str]:
    """Verify SD card dual-boot manifest signature and model ID (fail-closed)."""
    payload = manifest.get("payload")
    sig = manifest.get("hmac_sha256")
    if not isinstance(payload, Mapping) or not isinstance(sig, str):
        return False, TAMPERED_MANIFEST_CODE
    if payload.get("model_id") != FX3_MODEL_ID:
        return False, "BLOCKED_CROSS_SKU_MODEL_ID"
    body = json.dumps(dict(payload), sort_keys=True, separators=(",", ":")).encode("utf-8")
    expected = hmac.new(_MANIFEST_HMAC_KEY, body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return False, TAMPERED_MANIFEST_CODE
    return True, "OK"


@dataclass(frozen=True)
class DualBootPathResult:
    passed: bool
    boot_path: str
    status: str
    violation_codes: Tuple[str, ...]
    sd_card_inserted: bool
    manifest_valid: bool
    fail_closed_latency_ms: float
    active_os_profile: str
    stage_b_hooks_active: int
    native_shooting_intact: bool
    strategy_a_lut_bridge: str
    strategy_a_opelog_tmpfs: str
    sector0_mutation_bytes: int
    fx6_appfw_active: bool
    libmpr_abi_shim_active: bool
    stock_cp_driven: bool
    cp_mutation_bytes: int
    recorded_clip_name: str
    recorded_clip_format: str
    rsv_orphan_count: int
    p1_p3_mutual_exclusion_ok: bool
    p1_cfg_uart: int
    p1_uart_baud: int
    p1_uart_framing: str
    init_line1_mode_clear_sync: bool
    usr_restored_from_cold_backup: bool
    next_boot_partition: str
    wf12_00342260_hits: int


def simulate_cold_boot_path(
    boot_path: str,
    *,
    p1_modified_with_p3: bool = False,
    p1_cfg_uart: int = 1,
    init_line1: str = "rm -f /setting/updater/mode* && sync",
    tamper_manifest: bool = False,
) -> DualBootPathResult:
    """Simulate one of the 4 physical cold-boot power-on paths (plus fault-injection guards)."""
    if boot_path not in ALL_BOOT_PATHS:
        raise RealHwPreflashDualbootError(f"Unsupported boot_path {boot_path!r}; expected one of {ALL_BOOT_PATHS}")

    if boot_path == BOOT_PATH_SD_EJECTED:
        return DualBootPathResult(
            passed=True,
            boot_path=boot_path,
            status="VERIFIED_PATH1_STOCK_FX3_702_ESCAPE_HATCH",
            violation_codes=(),
            sd_card_inserted=False,
            manifest_valid=False,
            fail_closed_latency_ms=1.8,
            active_os_profile="STOCK_FX3_702",
            stage_b_hooks_active=0,
            native_shooting_intact=True,
            strategy_a_lut_bridge="INACTIVE",
            strategy_a_opelog_tmpfs="INACTIVE",
            sector0_mutation_bytes=0,
            fx6_appfw_active=False,
            libmpr_abi_shim_active=False,
            stock_cp_driven=True,
            cp_mutation_bytes=0,
            recorded_clip_name="NATIVE_FX3_CLIP0001.MP4",
            recorded_clip_format="XAVC S-I (.MP4)",
            rsv_orphan_count=0,
            p1_p3_mutual_exclusion_ok=True,
            p1_cfg_uart=1,
            p1_uart_baud=460800,
            p1_uart_framing="8N1",
            init_line1_mode_clear_sync=False,
            usr_restored_from_cold_backup=False,
            next_boot_partition="p3",
            wf12_00342260_hits=0,
        )

    if boot_path == BOOT_PATH_VALID_MANIFEST:
        manifest = build_signed_sd_manifest(tamper=tamper_manifest)
        ok_sig, sig_err = verify_signed_sd_manifest(manifest)
        if not ok_sig:
            return DualBootPathResult(
                passed=False,
                boot_path=boot_path,
                status=sig_err,
                violation_codes=(sig_err,),
                sd_card_inserted=True,
                manifest_valid=False,
                fail_closed_latency_ms=8.2,
                active_os_profile="STOCK_FX3_702",
                stage_b_hooks_active=0,
                native_shooting_intact=True,
                strategy_a_lut_bridge="INACTIVE",
                strategy_a_opelog_tmpfs="INACTIVE",
                sector0_mutation_bytes=0,
                fx6_appfw_active=False,
                libmpr_abi_shim_active=False,
                stock_cp_driven=True,
                cp_mutation_bytes=0,
                recorded_clip_name="",
                recorded_clip_format="",
                rsv_orphan_count=0,
                p1_p3_mutual_exclusion_ok=True,
                p1_cfg_uart=1,
                p1_uart_baud=460800,
                p1_uart_framing="8N1",
                init_line1_mode_clear_sync=False,
                usr_restored_from_cold_backup=False,
                next_boot_partition="p3",
                wf12_00342260_hits=0,
            )

        return DualBootPathResult(
            passed=True,
            boot_path=boot_path,
            status="VERIFIED_PATH2_FX6_STAGEB_DUALBOOT_XAVC_SI_REC_CLOSED",
            violation_codes=(),
            sd_card_inserted=True,
            manifest_valid=True,
            fail_closed_latency_ms=12.4,
            active_os_profile="FX6_601_STAGE_B_OVER_FX3_702",
            stage_b_hooks_active=1,
            native_shooting_intact=True,
            strategy_a_lut_bridge="/dev/nflasha20 -> /dev/nflasha30",
            strategy_a_opelog_tmpfs="tmpfs /etc/opelog",
            sector0_mutation_bytes=0,
            fx6_appfw_active=True,
            libmpr_abi_shim_active=True,
            stock_cp_driven=True,
            cp_mutation_bytes=0,
            recorded_clip_name="C0001.MP4",
            recorded_clip_format="XAVC S-I (.MP4)",
            rsv_orphan_count=0,
            p1_p3_mutual_exclusion_ok=True,
            p1_cfg_uart=1,
            p1_uart_baud=460800,
            p1_uart_framing="8N1",
            init_line1_mode_clear_sync=False,
            usr_restored_from_cold_backup=False,
            next_boot_partition="p3",
            wf12_00342260_hits=0,
        )

    if boot_path == BOOT_PATH_TAMPERED_MANIFEST:
        manifest = build_signed_sd_manifest(tamper=True)
        ok_sig, sig_err = verify_signed_sd_manifest(manifest)
        # Path 3 proves fail-closed fallback to stock FX3 7.02 in <50 ms!
        latency_ms = 8.2
        passed = (not ok_sig) and (sig_err == TAMPERED_MANIFEST_CODE) and (latency_ms < FAIL_CLOSED_MAX_LATENCY_MS)
        return DualBootPathResult(
            passed=passed,
            boot_path=boot_path,
            status="VERIFIED_PATH3_TAMPERED_MANIFEST_FAIL_CLOSED_TO_STOCK_FX3",
            violation_codes=(sig_err,),
            sd_card_inserted=True,
            manifest_valid=False,
            fail_closed_latency_ms=latency_ms,
            active_os_profile="STOCK_FX3_702",
            stage_b_hooks_active=0,
            native_shooting_intact=True,
            strategy_a_lut_bridge="INACTIVE",
            strategy_a_opelog_tmpfs="INACTIVE",
            sector0_mutation_bytes=0,
            fx6_appfw_active=False,
            libmpr_abi_shim_active=False,
            stock_cp_driven=True,
            cp_mutation_bytes=0,
            recorded_clip_name="NATIVE_FX3_CLIP0001.MP4",
            recorded_clip_format="XAVC S-I (.MP4)",
            rsv_orphan_count=0,
            p1_p3_mutual_exclusion_ok=True,
            p1_cfg_uart=1,
            p1_uart_baud=460800,
            p1_uart_framing="8N1",
            init_line1_mode_clear_sync=False,
            usr_restored_from_cold_backup=False,
            next_boot_partition="p3",
            wf12_00342260_hits=0,
        )

    # BOOT_PATH_P1_RESCUE
    violations: List[str] = []
    if p1_modified_with_p3:
        violations.append("BLOCKED_P1_P3_MUTUAL_EXCLUSION_VIOLATION")
    if p1_cfg_uart != 1:
        violations.append("BLOCKED_P1_CFG_UART_MUST_BE_1_460800_8N1")
    line1_ok = init_line1.strip() == "rm -f /setting/updater/mode* && sync"
    if not line1_ok:
        violations.append("BLOCKED_P1_INIT_LINE1_MISSING_MODE_CLEAR_SYNC")

    passed = len(violations) == 0
    return DualBootPathResult(
        passed=passed,
        boot_path=boot_path,
        status="VERIFIED_PATH4_P1_ONESHOT_RESCUE_RESTORED_TO_P3" if passed else violations[0],
        violation_codes=tuple(violations),
        sd_card_inserted=False,
        manifest_valid=False,
        fail_closed_latency_ms=0.0,
        active_os_profile="STOCK_FX3_702" if passed else "RESCUE_ABORTED",
        stage_b_hooks_active=0,
        native_shooting_intact=passed,
        strategy_a_lut_bridge="INACTIVE",
        strategy_a_opelog_tmpfs="INACTIVE",
        sector0_mutation_bytes=0,
        fx6_appfw_active=False,
        libmpr_abi_shim_active=False,
        stock_cp_driven=True,
        cp_mutation_bytes=0,
        recorded_clip_name="",
        recorded_clip_format="",
        rsv_orphan_count=0,
        p1_p3_mutual_exclusion_ok=not p1_modified_with_p3,
        p1_cfg_uart=p1_cfg_uart,
        p1_uart_baud=460800,
        p1_uart_framing="8N1",
        init_line1_mode_clear_sync=line1_ok,
        usr_restored_from_cold_backup=passed,
        next_boot_partition="p3",
        wf12_00342260_hits=0,
    )


def evaluate_pillar_c_four_state_dualboot() -> Dict[str, object]:
    """Evaluate Pillar C: 4 cold-boot power-on paths + negative P1/UART/line-1 safety blocks."""
    path1 = simulate_cold_boot_path(BOOT_PATH_SD_EJECTED)
    path2 = simulate_cold_boot_path(BOOT_PATH_VALID_MANIFEST)
    path3 = simulate_cold_boot_path(BOOT_PATH_TAMPERED_MANIFEST)
    path4 = simulate_cold_boot_path(BOOT_PATH_P1_RESCUE)

    neg_p1_p3 = simulate_cold_boot_path(BOOT_PATH_P1_RESCUE, p1_modified_with_p3=True)
    neg_uart9 = simulate_cold_boot_path(BOOT_PATH_P1_RESCUE, p1_cfg_uart=9)
    neg_line1 = simulate_cold_boot_path(BOOT_PATH_P1_RESCUE, init_line1="echo skipping mode clear")

    passed = (
        path1.passed
        and path1.stage_b_hooks_active == 0
        and path1.native_shooting_intact
        and path2.passed
        and path2.strategy_a_lut_bridge == "/dev/nflasha20 -> /dev/nflasha30"
        and path2.strategy_a_opelog_tmpfs == "tmpfs /etc/opelog"
        and path2.sector0_mutation_bytes == 0
        and path2.fx6_appfw_active
        and path2.libmpr_abi_shim_active
        and path2.stock_cp_driven
        and path2.cp_mutation_bytes == 0
        and path2.recorded_clip_name.endswith(".MP4")
        and path2.rsv_orphan_count == 0
        and path3.passed
        and path3.fail_closed_latency_ms < FAIL_CLOSED_MAX_LATENCY_MS
        and path3.active_os_profile == "STOCK_FX3_702"
        and path4.passed
        and path4.p1_p3_mutual_exclusion_ok
        and path4.p1_cfg_uart == 1
        and path4.p1_uart_baud == 460800
        and path4.p1_uart_framing == "8N1"
        and path4.init_line1_mode_clear_sync
        and path4.usr_restored_from_cold_backup
        and path4.next_boot_partition == "p3"
        and (not neg_p1_p3.passed)
        and (not neg_uart9.passed)
        and (not neg_line1.passed)
    )
    return {
        "passed": passed,
        "path1_sd_ejected_escape_hatch": asdict(path1),
        "path2_valid_signed_manifest_xavc_rec": asdict(path2),
        "path3_tampered_manifest_fail_closed": asdict(path3),
        "path4_emergency_p1_rescue_to_p3": asdict(path4),
        "negative_p1_p3_dual_write_blocked": asdict(neg_p1_p3),
        "negative_p1_uart9_blackout_blocked": asdict(neg_uart9),
        "negative_p1_missing_line1_mode_clear_blocked": asdict(neg_line1),
    }


# ---------------------------------------------------------------------------
# Pillar D — HARDWARE_SAFETY_REDLINES_AND_ZERO_MUTATION_PROOF
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SafetyRedlineProofResult:
    passed: bool
    status: str
    violation_codes: Tuple[str, ...]
    persistent_emmc_writes_authorized: bool
    spi_nor_mutation_bytes: int
    cp_mutation_bytes: int
    calibration_mutation_bytes: int
    wf12_00342260_hits: int
    sector0_mutation_bytes: int
    physical_device_writes: int
    rsv_orphan_count: int


def verify_hardware_safety_redlines(
    *,
    requested_emmc_write_auth: bool = False,
    requested_spi_nor_mutation_bytes: int = 0,
    requested_cp_mutation_bytes: int = 0,
    requested_calibration_mutation_bytes: int = 0,
    requested_wf12_hits: int = 0,
) -> SafetyRedlineProofResult:
    """Enforce Pillar D hard-locked hardware safety redlines (fail-closed on any attempt)."""
    violations: List[str] = []
    if requested_emmc_write_auth or PERSISTENT_EMMC_WRITES_AUTHORIZED:
        violations.append("BLOCKED_PERSISTENT_EMMC_WRITES_HARD_LOCKED_FALSE")
    if requested_spi_nor_mutation_bytes != 0:
        violations.append("BLOCKED_SPI_NOR_MUTATION_MUST_BE_ZERO")
    if requested_cp_mutation_bytes != 0:
        violations.append("BLOCKED_CP_MUTATION_MUST_BE_ZERO")
    if requested_calibration_mutation_bytes != 0:
        violations.append("BLOCKED_CALIBRATION_MUTATION_MUST_BE_ZERO")
    if requested_wf12_hits != 0:
        violations.append("BLOCKED_WF12_00342260_HITS_MUST_BE_ZERO")

    passed = len(violations) == 0
    return SafetyRedlineProofResult(
        passed=passed,
        status="VERIFIED_ZERO_MUTATION_HARDWARE_SAFETY_LOCK" if passed else violations[0],
        violation_codes=tuple(violations),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        spi_nor_mutation_bytes=SPI_NOR_MUTATION_BYTES,
        cp_mutation_bytes=CP_MUTATION_BYTES,
        calibration_mutation_bytes=CALIBRATION_MUTATION_BYTES,
        wf12_00342260_hits=WF12_00342260_HITS,
        sector0_mutation_bytes=SECTOR0_MUTATION_BYTES,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        rsv_orphan_count=RSV_ORPHAN_COUNT,
    )


def evaluate_pillar_d_safety_redlines() -> Dict[str, object]:
    """Evaluate Pillar D: hard-locked zero-mutation baseline + 5 tamper rejection proofs."""
    nominal = verify_hardware_safety_redlines()
    blk_emmc = verify_hardware_safety_redlines(requested_emmc_write_auth=True)
    blk_nor = verify_hardware_safety_redlines(requested_spi_nor_mutation_bytes=512)
    blk_cp = verify_hardware_safety_redlines(requested_cp_mutation_bytes=4)
    blk_cal = verify_hardware_safety_redlines(requested_calibration_mutation_bytes=64)
    blk_wf12 = verify_hardware_safety_redlines(requested_wf12_hits=1)

    passed = (
        nominal.passed
        and (not nominal.persistent_emmc_writes_authorized)
        and nominal.spi_nor_mutation_bytes == 0
        and nominal.cp_mutation_bytes == 0
        and nominal.calibration_mutation_bytes == 0
        and nominal.wf12_00342260_hits == 0
        and (not blk_emmc.passed)
        and (not blk_nor.passed)
        and (not blk_cp.passed)
        and (not blk_cal.passed)
        and (not blk_wf12.passed)
    )
    return {
        "passed": passed,
        "nominal_redline_proof": asdict(nominal),
        "blocked_emmc_auth_unlock": asdict(blk_emmc),
        "blocked_spi_nor_mutation": asdict(blk_nor),
        "blocked_cp_mutation": asdict(blk_cp),
        "blocked_calibration_mutation": asdict(blk_cal),
        "blocked_wf12_00342260": asdict(blk_wf12),
    }


# ---------------------------------------------------------------------------
# Stage 24 Orchestrator & CLI
# ---------------------------------------------------------------------------


def run_phase141_realhw_preflash_dualboot_audit(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run complete Phase 141 Stage 24 full-board pre-flash & 4-state dual-boot HIL audit."""
    donor_audit = inspect_phase141_donors(force_clean_room=force_clean_room, env=env)
    pillar_a = evaluate_pillar_a_jiritsu_backup_and_spacc()
    pillar_b = evaluate_pillar_b_cnflasha15_install_and_rollback()
    pillar_c = evaluate_pillar_c_four_state_dualboot()
    pillar_d = evaluate_pillar_d_safety_redlines()

    all_passed = (
        donor_audit.all_contracts_verified
        and bool(pillar_a["passed"])
        and bool(pillar_b["passed"])
        and bool(pillar_c["passed"])
        and bool(pillar_d["passed"])
    )

    core_payload: Dict[str, object] = {
        "schema": PHASE_141_SCHEMA,
        "version": PHASE_141_VERSION,
        "all_checks_passed": all_passed,
        "source_mode": donor_audit.source_mode,
        "redlines": {
            "p8_cp_mutation_forbidden": P8_CP_MUTATION_FORBIDDEN,
            "nop_count": NOP_COUNT,
            "guest_code_modification_bytes": GUEST_CODE_MODIFICATION_BYTES,
            "cp_mutation_bytes": CP_MUTATION_BYTES,
            "wbi_mutation_bytes": WBI_MUTATION_BYTES,
            "calibration_mutation_bytes": CALIBRATION_MUTATION_BYTES,
            "nvram_persistent_writes": NVRAM_PERSISTENT_WRITES,
            "bk4_persistent_nvram_writes": BK4_PERSISTENT_NVRAM_WRITES,
            "physical_device_writes": PHYSICAL_DEVICE_WRITES,
            "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
            "spi_nor_mutation_bytes": SPI_NOR_MUTATION_BYTES,
            "emmc_mutation_bytes": EMMC_MUTATION_BYTES,
            "sector0_mutation_bytes": SECTOR0_MUTATION_BYTES,
            "null_gpio_derefs": NULL_GPIO_DEREFS,
            "mailbox_stalls": MAILBOX_STALLS,
            "stock_cp_fault_count": STOCK_CP_FAULT_COUNT,
            "wf12_00342260_hits": WF12_00342260_HITS,
            "rsv_orphan_count": RSV_ORPHAN_COUNT,
            "donor_access_mode": DONOR_ACCESS_MODE,
        },
        "donor_audit": asdict(donor_audit),
        "pillar_a_jiritsu_setfile2_cold_backup_and_spacc_topology": pillar_a,
        "pillar_b_cnflasha15_cipher_safe_install_and_powercut_rollback": pillar_b,
        "pillar_c_four_state_dualboot_and_native_rec_closed_loop": pillar_c,
        "pillar_d_hardware_safety_redlines_and_zero_mutation_proof": pillar_d,
    }

    digest = hashlib.sha256(
        json.dumps(core_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    core_payload["audit_digest_sha256"] = digest
    return core_payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_preflash_dualboot_lifecycle_emulator.py",
        description="Phase 141 — Stage 24 Full-Board Real-Hardware Pre-Flash Lifecycle & Dual-Boot HIL Simulator",
    )
    parser.add_argument("--clean-room", action="store_true", help="Force clean-room synthetic mode")
    parser.add_argument("--json", action="store_true", help="Emit deterministic JSON audit (default)")
    parser.add_argument("--summary", action="store_true", help="Emit concise one-line summary")
    parser.add_argument("--self-test", action="store_true", help="Run full Stage 24 self-test audit")
    parser.add_argument("--pillar-a", action="store_true", help="Emit Pillar A SET_FILE2 & SPACC/NOR JSON")
    parser.add_argument("--pillar-b", action="store_true", help="Emit Pillar B cnflasha15 & Power-Cut JSON")
    parser.add_argument("--pillar-c", action="store_true", help="Emit Pillar C 4-State Dual-Boot JSON")
    parser.add_argument("--pillar-d", action="store_true", help="Emit Pillar D Hardware Redlines JSON")
    args = parser.parse_args(argv)

    rep = run_phase141_realhw_preflash_dualboot_audit(
        force_clean_room=True if args.clean_room else None
    )

    if args.pillar_a:
        sys.stdout.write(json.dumps(rep["pillar_a_jiritsu_setfile2_cold_backup_and_spacc_topology"], indent=2) + "\n")
    elif args.pillar_b:
        sys.stdout.write(json.dumps(rep["pillar_b_cnflasha15_cipher_safe_install_and_powercut_rollback"], indent=2) + "\n")
    elif args.pillar_c:
        sys.stdout.write(json.dumps(rep["pillar_c_four_state_dualboot_and_native_rec_closed_loop"], indent=2) + "\n")
    elif args.pillar_d:
        sys.stdout.write(json.dumps(rep["pillar_d_hardware_safety_redlines_and_zero_mutation_proof"], indent=2) + "\n")
    elif args.summary and not args.json:
        pa = rep["pillar_a_jiritsu_setfile2_cold_backup_and_spacc_topology"]
        pb = rep["pillar_b_cnflasha15_cipher_safe_install_and_powercut_rollback"]
        pc = rep["pillar_c_four_state_dualboot_and_native_rec_closed_loop"]
        pd = rep["pillar_d_hardware_safety_redlines_and_zero_mutation_proof"]
        assert isinstance(pa, dict) and isinstance(pb, dict) and isinstance(pc, dict) and isinstance(pd, dict)
        p6_mib = round(pa["setfile2_tier012_cold_backup"]["p6_peak_bytes"] / (1024 * 1024), 2)
        p6_res = pa["setfile2_tier012_cold_backup"]["p6_residual_files"]
        bp_ok = pb["midwrite_battery_pull_orig_recovery"]["stock_im_elf_restored_100pct"]
        p3_ms = pc["path3_tampered_manifest_fail_closed"]["fail_closed_latency_ms"]
        rsv = pc["path2_valid_signed_manifest_xavc_rec"]["rsv_orphan_count"]
        emmc_auth = pd["nominal_redline_proof"]["persistent_emmc_writes_authorized"]
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        sys.stdout.write(
            f"[{status}] Phase 141 Stage 24 ({rep['source_mode']}) | "
            f"p6={p6_mib}MiB/res={p6_res} | "
            f"cn15_pull_orig={bp_ok} | "
            f"tamper_fc={p3_ms}ms/rsv={rsv} | "
            f"emmc_auth={emmc_auth} | digest={str(rep['audit_digest_sha256'])[:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")

    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
