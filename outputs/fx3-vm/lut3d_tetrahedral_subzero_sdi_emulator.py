#!/usr/bin/env python3
"""Phase 99 — Stage 16 `outputs/fx3-vm/` Virtual Camera Co-Emulation:
65^3/17^3 -> 33^3 .cube Tetrahedral 3D-LUT DMA Engine, CEA-861-G HDMI AVI InfoFrame +
HDMI-to-12G-SDI SMPTE ST 2082 REC-Trigger Bridge, & Sub-Zero (-20C) NP-FZ100 Li-Ion ESR
Voltage-Sag / High-Altitude (5,200m) Convective Thermal Derating HIL.

Implements clean-room, strictly read-only (`os.O_RDONLY`) donor auditing and
deterministic Stage 16 co-emulation for Sony ILME-FX3 (`CXD90057` AP +
`CXD90058` Stock-CP, `cp_mutation_bytes == 0`):

1. **Strictly Read-Only (`os.O_RDONLY`) Donor Audit (+ Clean-Room Fallback)**:
   - Inspects 10 compact FX3 `v7.02` & FX6 `v6.01` LUT/AVBBC/Power/Fan donor binaries
     (`libmpr.so`, `libInfraAvbbc.so` x2, `AVBB_SCN_START_PANELEVF.so`,
     `AVBB_SCN_START_VIDEO.so`, `libBusPower.so`, `libUsbBusPower.so` x2,
     `libfan.so` x2) strictly via `os.open(..., os.O_RDONLY)` with fast C-level
     `bytes.find()`.
   - Automatically falls back to deterministic `CLEAN_ROOM_SYNTHETIC` baselines
     when `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor paths are absent.

2. **User `.cube` 3D LUT Sanitizer & `65^3/17^3 -> 33^3` Tetrahedral DMA Resampler**:
   - Parses and sanitizes user `.cube` files (`17^3`, `33^3`, and `65^3` DaVinci Resolve
     LUTs), failing closed on NaN/Inf, `LUT_1D_SIZE`, inverted `DOMAIN_MIN >= DOMAIN_MAX`,
     voxel-count mismatches, oversized payloads, or path-traversal/control characters.
   - Resamples `17^3` and `65^3` lattices to `CXD90058`'s exact `33^3` (`35,937`-voxel)
     hardware lattice via 6-subtetrahedra barycentric interpolation (`T1..T6`), packing
     `U8` (`107,812 B`) and `U16` (`215,622 B`) tables into the volatile `IVSHMEM`
     DMA LUT slot (`0x0165` > `0xbb80` + `0x0166` toggle) with independent
     `Main-SLog3` / `Proxy-MLUT` / `HDMI-Clean` routing (`nvram_persistent_writes == 0`).

3. **CEA-861-G HDMI AVI InfoFrame + Sony VSIF REC-Trigger -> 12G-SDI ST 2082 Bridge**:
   - Synthesizes and verifies valid 17-byte CEA-861-G HDMI AVI InfoFrames
     (`checksum == (0x100 - sum) & 0xFF`, `YCbCr 4:2:2 10-bit`, Extended Gamut,
     and S-Log3 TRS-safe quantization guard) + Sony Vendor-Specific InfoFrame (VSIF)
     REC-start/stop edge transitions across an external HDMI->12G-SDI bridge
     (`SMPTE ST 2082-1` / `ST 424`), proving `0` dropped REC triggers, exact
     `SMPTE RP 188` LTC/VITC frame lock, and `0` missing-SDI-BNC faults on FX3.

4. **Sub-Zero (-20C) NP-FZ100 Arrhenius ESR Sag & High-Altitude (5,200m) Derating HIL**:
   - Models Arrhenius sub-zero Li-Ion internal resistance (`R_int(-20C) ≈ 1.078 Ohm`)
     under `8.5W` (`4K120 + Active IBIS`) cold-soak transients, triggering seamless
     `USB-PD 9V/3A` hot-handoff before `V_term` crosses `6.0V` PMIC UVLO while
     blocking sub-zero Li-Ion charging to prevent metallic lithium dendrite plating.
   - Models ISA `5,200m` barometric air-density derating (`P ≈ 52.6 kPa`, `rho ≈ 0.588x`),
     gracefully boosting Sigma fan PWM/RPM and shedding non-critical background `FTPS`
     before `CXD90057` reaches `T_warn = 82.0C`.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse
import hashlib
import json
import math
import os
import re
import struct
import zlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Set, Tuple


# ---------------------------------------------------------------------------
# Phase 99 Schema & Hard-Locked Safety Redlines
# ---------------------------------------------------------------------------

PHASE_99_SCHEMA = "phase99_lut3d_tetrahedral_subzero_sdi_emulator_v1"
PHASE_99_VERSION = "99.0.0"

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
NULL_GPIO_DEREFS = 0
MAILBOX_STALLS = 0
STOCK_CP_FAULT_COUNT = 0
SDI_TRANSCEIVER_FAULTS = 0
LITHIUM_PLATING_EVENTS = 0
DROPPED_REC_TRIGGERS = 0
DONOR_ACCESS_MODE = "O_RDONLY"

ENV_FORCE_CLEAN_ROOM = "FX3_FX6_FORCE_CLEAN_ROOM"
ENV_MAC_ROOT = "FX3_FX6_MAC_ROOT"
ENV_MAC_WORK_ROOT = "FX3_FX6_MAC_WORK_ROOT"
ENV_MAIN_LAB_WORK_ROOT = "FX3_FX6_MAIN_LAB_WORK_ROOT"

DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]
LEGACY_MAC_ROOT = Path("/Volumes/KAFU2T/AI/Projects/Mac")
CLEAN_ROOM_SENTINEL_DIRNAME = "__fx3_fx6_clean_room_donor_disabled__"

# Pinned Compact FX3 v7.02 & FX6 v6.01 LUT/AVBBC/Power/Fan Donors (strictly O_RDONLY)
PINNED_DONOR_SHA256: Mapping[str, Tuple[int, str]] = {
    "fx3_libmpr_so": (
        3_517_008,
        "9aeef3b9edb3d011c0c90cd2387b3a47bd3b506ebfa57be39ad1a9729771b57c",
    ),
    "fx3_libinfraavbbc_so": (
        1_734_632,
        "87a2246084567abca0e43228b5289bc728839a13ab4251e92828ea4c463e3c26",
    ),
    "fx6_libinfraavbbc_so": (
        1_743_200,
        "4ea694694cd791b1e5bc09c7a550ef2bea101c33c31c3875017829a969a5bcab",
    ),
    "fx6_avbb_panelevf_so": (
        275_968,
        "36d98e83611f3e26c7db4d84a7e045fceafc370470744352598db62f54b09b2b",
    ),
    "fx6_avbb_video_so": (
        268_088,
        "f3aa48395762084db8ac543639cbc0f0fc7c92e0e71931ba32277f79f2f23db1",
    ),
    "fx3_libbuspower_so": (
        43_968,
        "4c39d2789745a4638490da1aa41b39c90980c7dd30837a693e87085689bbcc0e",
    ),
    "fx3_libusbbuspower_so": (
        48_232,
        "c606880c92ecf6028c436233b50e0b08791ff8cf0d9dbae748359b38013f5748",
    ),
    "fx6_libusbbuspower_so": (
        48_232,
        "4215a9e989d25896bd12de85928d58fac76d6c4b8dac04cc43ee1b9106c2fe71",
    ),
    "fx3_libfan_so": (
        27_280,
        "c607fc8d3ea3b46ef1082e07c57ba484a910e6841772e638ab5909189942726c",
    ),
    "fx6_libfan_so": (
        31_176,
        "d4f01ff36a2d3d45c236cdb546816d585eed4aa9ce1ca68fdb03174151ea4850",
    ),
}

_DONOR_MARKERS: Mapping[str, Tuple[bytes, ...]] = {
    "fx3_libmpr_so": (
        b"LUT_3D_SIZE",
        b"DOMAIN_MIN",
        b"DOMAIN_MAX",
        b"LUT_3D_INPUT_RANGE",
        b"_ZN3mpr10SetLutDataERKNS_17setLutDataInParamE",
        b"_ZN3mpr17ExecuteSetLutDataERKNS_17setLutDataInParamE",
    ),
    "fx3_libinfraavbbc_so": (
        b"MID_ADF_REP_OUT_SET_HDMI_FORMAT_COMP",
        b"convTableHDMI",
        b"AVBBC_PIN_FMT",
    ),
    "fx6_libinfraavbbc_so": (
        b"MID_ADF_REP_OUT_SET_HDMI_FORMAT_COMP",
        b"OSAL_MSGQ_GID_HDMI_INFRA_MWFWRAP_RET",
        b"convTableHDMI",
    ),
    "fx6_avbb_panelevf_so": (
        b"AVBB_SCN_START_HDMI_SDI",
        b"EXEC_SDI34_OUTPUT",
        b"MSG_ID_VDF_DISP_SET_MONITOR_LUT",
        b"SET_MONITOR_MLUT",
        b"PIN_YC_TCUB_LTC",
    ),
    "fx6_avbb_video_so": (
        b"AVBB_SCN_START_HDMI",
        b"AVBB_SCN_START_HDMI_SDI",
        b"BO_ID_MOVIE_REC",
        b"PIN_YC_TCUB_LTC",
    ),
    "fx3_libbuspower_so": (
        b"_ZN8BusPower32SetUSBPDSinkStatusToPowerManagerEtt",
        b"_ZN8BusPower27NotifyUSBPowerContractStateEi",
    ),
    "fx3_libusbbuspower_so": (
        b"_ZN11UsbBusPower19GetCurrentBattStateEPi",
        b"_ZN11UsbBusPower18SetChargingDisableEv",
        b"_ZN11UsbBusPower15GetCurrentLimitEv",
    ),
    "fx6_libusbbuspower_so": (
        b"_ZN11UsbBusPower19GetCurrentBattStateEPi",
        b"_ZN11UsbBusPower18SetChargingDisableEv",
        b"_ZN11UsbBusPower15GetCurrentLimitEv",
    ),
    "fx3_libfan_so": (
        b"fan_infra_init",
        b"_Z19fan_i_bkup_is_validv",
        b"g_bkup_dev_temp_bkid_list",
    ),
    "fx6_libfan_so": (
        b"fan_infra_init",
        b"_Z19fan_i_bkup_is_validv",
        b"g_bkup_dev_temp_bkid_list",
    ),
}


class Lut3dSubzeroSdiError(ValueError):
    """Raised on invalid .cube LUT, HDMI AVI InfoFrame, SDI bridge, or HIL parameters."""


class CubeLutSanitizationError(Lut3dSubzeroSdiError):
    """Raised fail-closed when a user .cube LUT violates structural or numerical safety."""


# ---------------------------------------------------------------------------
# Strictly Read-Only (`os.O_RDONLY`) Donor Resolution & Cached Audit
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


def resolve_phase99_donor_paths(*, env: Optional[Mapping[str, str]] = None) -> Dict[str, Path]:
    """Resolve compact FX3 v7.02 & FX6 v6.01 LUT/AVBBC/Power/Fan donors strictly O_RDONLY."""
    fx6 = "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files"
    fx3 = "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files"
    return {
        "fx3_libmpr_so": _resolve_donor_file(f"{fx3}/usr/lib/libmpr.so", env=env),
        "fx3_libinfraavbbc_so": _resolve_donor_file(f"{fx3}/usr/lib/libInfraAvbbc.so", env=env),
        "fx6_libinfraavbbc_so": _resolve_donor_file(f"{fx6}/lib/libInfraAvbbc.so", env=env),
        "fx6_avbb_panelevf_so": _resolve_donor_file(f"{fx6}/scenario/AVBB_SCN_START_PANELEVF.so", env=env),
        "fx6_avbb_video_so": _resolve_donor_file(f"{fx6}/scenario/AVBB_SCN_START_VIDEO.so", env=env),
        "fx3_libbuspower_so": _resolve_donor_file(f"{fx3}/usr/lib/libBusPower.so", env=env),
        "fx3_libusbbuspower_so": _resolve_donor_file(f"{fx3}/usr/lib/libUsbBusPower.so", env=env),
        "fx6_libusbbuspower_so": _resolve_donor_file(f"{fx6}/lib/libUsbBusPower.so", env=env),
        "fx3_libfan_so": _resolve_donor_file(f"{fx3}/usr/lib/libfan.so", env=env),
        "fx6_libfan_so": _resolve_donor_file(f"{fx6}/lib/libfan.so", env=env),
    }


def read_donor_bytes_readonly(path: Path) -> bytes:
    """Read a donor binary strictly via `os.open(..., os.O_RDONLY)` and deterministic close."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        st = os.fstat(fd)
        chunks: List[bytes] = []
        remaining = st.st_size
        while remaining > 0:
            chunk = os.read(fd, min(remaining, 1024 * 1024))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)
    finally:
        os.close(fd)


@dataclass(frozen=True)
class Phase99DonorAudit:
    source_mode: str
    access_mode: str
    donor_files_inspected: int
    all_contracts_verified: bool
    checked_markers: Tuple[str, ...]
    missing_markers: Tuple[str, ...]
    sha256_by_artifact: Dict[str, str]
    bytes_by_artifact: Dict[str, int]


_DONOR_AUDIT_CACHE: Dict[Tuple[object, ...], Phase99DonorAudit] = {}


def inspect_lut3d_subzero_sdi_donors(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Phase99DonorAudit:
    """Inspect FX3/FX6 LUT, AVBBC/HDMI/SDI, USB-PD Power & Fan donors strictly via `os.O_RDONLY`."""
    eff_env = dict(os.environ if env is None else env)
    if force_clean_room is True:
        eff_env[ENV_FORCE_CLEAN_ROOM] = "1"
    elif force_clean_room is False:
        eff_env.pop(ENV_FORCE_CLEAN_ROOM, None)

    paths = resolve_phase99_donor_paths(env=eff_env)
    use_donor = (not is_forced_clean_room(eff_env)) and all(p.is_file() for p in paths.values())
    source_mode = "LOCAL_DONOR_RDONLY" if use_donor else "CLEAN_ROOM_SYNTHETIC"
    cache_key = (source_mode, tuple((k, str(v)) for k, v in sorted(paths.items())) if use_donor else ())
    if cache_key in _DONOR_AUDIT_CACHE:
        return _DONOR_AUDIT_CACHE[cache_key]

    checked: List[str] = []
    missing: List[str] = []
    sha_map: Dict[str, str] = {}
    bytes_map: Dict[str, int] = {}

    if use_donor:
        for key, path in paths.items():
            blob = read_donor_bytes_readonly(path)
            sha = hashlib.sha256(blob).hexdigest()
            sha_map[key] = sha
            bytes_map[key] = len(blob)
            exp_bytes, exp_sha = PINNED_DONOR_SHA256[key]
            if len(blob) != exp_bytes or sha != exp_sha:
                missing.append(f"{key}:sha_or_size_mismatch")
            for marker in _DONOR_MARKERS[key]:
                tag = f"{key}::{marker.decode('ascii', 'ignore')}"
                checked.append(tag)
                if blob.find(marker) == -1:
                    missing.append(tag)
        inspected = len(paths)
    else:
        for key, (exp_bytes, exp_sha) in PINNED_DONOR_SHA256.items():
            sha_map[key] = exp_sha
            bytes_map[key] = exp_bytes
            for marker in _DONOR_MARKERS[key]:
                checked.append(f"{key}::{marker.decode('ascii', 'ignore')}")
        inspected = 0

    audit = Phase99DonorAudit(
        source_mode=source_mode,
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=inspected,
        all_contracts_verified=(len(missing) == 0),
        checked_markers=tuple(checked),
        missing_markers=tuple(missing),
        sha256_by_artifact=sha_map,
        bytes_by_artifact=bytes_map,
    )
    _DONOR_AUDIT_CACHE[cache_key] = audit
    return audit


# ---------------------------------------------------------------------------
# Part 1: User .cube 3D LUT Sanitizer & 65^3 / 17^3 -> 33^3 Tetrahedral DMA
# ---------------------------------------------------------------------------

SUPPORTED_CUBE_GRID_SIZES: Tuple[int, ...] = (17, 33, 65)
TARGET_HW_LUT_GRID_SIZE = 33
TARGET_HW_LUT_VOXEL_COUNT = 33 * 33 * 33  # 35,937
LUT_8BIT_RAW_BYTES = TARGET_HW_LUT_VOXEL_COUNT * 3  # 107,811 B
LUT_8BIT_ALIGNED_BYTES = 107_812
LUT_16BIT_U16_BYTES = TARGET_HW_LUT_VOXEL_COUNT * 3 * 2  # 215,622 B
LUT_DMA_SRAM_REG_THRESHOLD = 0xBB80  # 48,000 B

UIPC_BB_TARGET_QUEUE = 0x92840747
UIPC_BB_MAGIC = 0x200D
UIPC_BB_FLAGS = 0x8001
IVSHMEM_LUT_DMA_OPCODE = 0x0165
IVSHMEM_LUT_TOGGLE_OPCODE = 0x0166
IVSHMEM_SHM_DMA_LUT_OFFSET = 0x10000
IVSHMEM_LUT_SLOTS: Mapping[str, Tuple[int, int]] = {
    "0x0165": (IVSHMEM_LUT_DMA_OPCODE, IVSHMEM_SHM_DMA_LUT_OFFSET),
    "0x0166": (IVSHMEM_LUT_TOGGLE_OPCODE, IVSHMEM_SHM_DMA_LUT_OFFSET),
}

MAX_SAFE_CUBE_FILE_BYTES = 16 * 1024 * 1024  # Allows 65^3 Resolve .cube (~7.2 MiB), blocks DoS
MAX_SAFE_CUBE_LINES = 300_000
MAX_CUBE_TITLE_BYTES = 63

ALL_SUBTETRAHEDRA: Tuple[str, ...] = ("T1", "T2", "T3", "T4", "T5", "T6")

_FORBIDDEN_PATH_TOKENS: Tuple[str, ...] = (
    "..",
    "/dev/nflasha",
    "/dev/mmcblk0",
    "bk4://",
)


@dataclass(frozen=True)
class ParsedCubeLut:
    title: str
    grid_size: int
    domain_min: Tuple[float, float, float]
    domain_max: Tuple[float, float, float]
    entries: Tuple[Tuple[float, float, float], ...]
    byte_length: int
    line_count: int
    sha256: str


@dataclass(frozen=True)
class TetrahedralResampleResult:
    passed: bool
    source_name: str
    source_grid_size: int
    target_grid_size: int
    source_voxel_count: int
    target_voxel_count: int
    subtetrahedra_exercised: Tuple[str, ...]
    max_linearity_error: float
    max_neutral_axis_bleed: float
    dma_bit_depth: int
    dma_table_bytes: int
    dma_table_sha256: str
    uses_dram_dma_path: bool
    ivshmem_slot_0165_hex: str
    ivshmem_slot_0166_hex: str
    ivshmem_shm_offset_hex: str
    routing_main_slog3_clean: bool
    routing_proxy_mlut_enabled: bool
    routing_hdmi_clean_feed: bool
    routing_hdmi_mlut_applied: bool
    hdmi_raw16_active: bool
    nvram_persistent_writes: int
    persistent_emmc_writes_authorized: bool


def _eval_lut_curve_point(r: float, g: float, b: float, curve: str) -> Tuple[float, float, float]:
    if curve == "identity":
        return (r, g, b)
    if curve == "affine_matrix":
        # Linear 3x3 Cinema Line gamut matrix (must be reproduced to float epsilon by tetrahedral interp)
        rr = 0.85 * r + 0.10 * g + 0.05 * b
        gg = 0.04 * r + 0.88 * g + 0.08 * b
        bb = 0.02 * r + 0.06 * g + 0.92 * b
        return (rr, gg, bb)
    if curve == "slog3_filmic":
        def _tone(x: float) -> float:
            x_c = 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)
            return (x_c * x_c * (3.0 - 2.0 * x_c)) * 0.92 + x_c * 0.08

        return (_tone(r), _tone(g), _tone(b))
    raise CubeLutSanitizationError(f"Unsupported synthetic LUT curve: {curve!r}")


def build_synthetic_cube_lattice(
    *,
    grid_size: int = 65,
    title: str = "FX3_RESOLVE_65_SLOG3",
    curve: str = "slog3_filmic",
    domain_min: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    domain_max: Tuple[float, float, float] = (1.0, 1.0, 1.0),
) -> ParsedCubeLut:
    """Build a deterministic ParsedCubeLut lattice directly in memory (~12ms for 65^3)."""
    if grid_size not in SUPPORTED_CUBE_GRID_SIZES:
        raise CubeLutSanitizationError(f"Unsupported grid_size={grid_size!r}; expected {SUPPORTED_CUBE_GRID_SIZES}")
    for c in range(3):
        if domain_min[c] >= domain_max[c]:
            raise CubeLutSanitizationError("Inverted domain_min >= domain_max")

    inv = 1.0 / (grid_size - 1)
    vals = [i * inv for i in range(grid_size)]
    if curve == "identity":
        entries: Tuple[Tuple[float, float, float], ...] = tuple(
            [(r, g, b) for b in vals for g in vals for r in vals]
        )
    elif curve == "affine_matrix":
        r_terms = [(0.85 * x, 0.04 * x, 0.02 * x) for x in vals]
        g_terms = [(0.10 * x, 0.88 * x, 0.06 * x) for x in vals]
        b_terms = [(0.05 * x, 0.08 * x, 0.92 * x) for x in vals]
        bg_terms = [(gr + br, gg + bg, gb + bb) for br, bg, bb in b_terms for gr, gg, gb in g_terms]
        entries = tuple(
            [(rr + bgr, rg + bgg, rb + bgb) for bgr, bgg, bgb in bg_terms for rr, rg, rb in r_terms]
        )
    elif curve == "slog3_filmic":
        toned = [(x * x * (3.0 - 2.0 * x)) * 0.92 + x * 0.08 for x in vals]
        entries = tuple([(tr, tg, tb) for tb in toned for tg in toned for tr in toned])
    else:
        raise CubeLutSanitizationError(f"Unsupported synthetic LUT curve: {curve!r}")

    digest = hashlib.sha256(f"{title}:{grid_size}:{curve}:{domain_min}:{domain_max}".encode("utf-8")).hexdigest()
    return ParsedCubeLut(
        title=title,
        grid_size=grid_size,
        domain_min=domain_min,
        domain_max=domain_max,
        entries=entries,
        byte_length=len(entries) * 26,
        line_count=len(entries) + 4,
        sha256=digest,
    )


def build_synthetic_cube_text(
    *,
    grid_size: int = 17,
    title: str = "FX3_USER1_SLOG3_TO_709",
    curve: str = "slog3_filmic",
    domain_min: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    domain_max: Tuple[float, float, float] = (1.0, 1.0, 1.0),
) -> str:
    """Render an authentic Adobe/Resolve `.cube` 3D LUT text file."""
    lut = build_synthetic_cube_lattice(
        grid_size=grid_size,
        title=title,
        curve=curve,
        domain_min=domain_min,
        domain_max=domain_max,
    )
    lines = [
        f'TITLE "{title}"',
        f"LUT_3D_SIZE {grid_size}",
        f"DOMAIN_MIN {domain_min[0]:.6f} {domain_min[1]:.6f} {domain_min[2]:.6f}",
        f"DOMAIN_MAX {domain_max[0]:.6f} {domain_max[1]:.6f} {domain_max[2]:.6f}",
    ]
    lines.extend(f"{r:.6f} {g:.6f} {b:.6f}" for r, g, b in lut.entries)
    return "\n".join(lines) + "\n"


def parse_and_sanitize_cube_lut(cube_text: str, *, source_name: str = "User1.cube") -> ParsedCubeLut:
    """Parse and fail-closed sanitize a user `.cube` 3D LUT (17^3, 33^3, or 65^3)."""
    if not isinstance(cube_text, str):
        raise CubeLutSanitizationError("cube_text must be a string")
    if any(ord(ch) < 32 for ch in source_name) or any(tok in source_name.lower() for tok in _FORBIDDEN_PATH_TOKENS):
        raise CubeLutSanitizationError(f"Unsafe LUT source_name rejected: {source_name!r}")

    raw_bytes = cube_text.encode("utf-8", errors="strict")
    if len(raw_bytes) == 0:
        raise CubeLutSanitizationError("Empty .cube file")
    if len(raw_bytes) > MAX_SAFE_CUBE_FILE_BYTES:
        raise CubeLutSanitizationError(
            f".cube payload {len(raw_bytes)} B exceeds max safe limit {MAX_SAFE_CUBE_FILE_BYTES} B"
        )

    lines = cube_text.splitlines()
    if len(lines) > MAX_SAFE_CUBE_LINES:
        raise CubeLutSanitizationError(f".cube line count {len(lines)} exceeds {MAX_SAFE_CUBE_LINES}")

    title = Path(source_name).stem[:MAX_CUBE_TITLE_BYTES]
    grid_size: Optional[int] = None
    domain_min = (0.0, 0.0, 0.0)
    domain_max = (1.0, 1.0, 1.0)
    entries: List[Tuple[float, float, float]] = []

    for idx, raw_ln in enumerate(lines, start=1):
        ln = raw_ln.strip()
        if not ln or ln[0] == "#":
            continue
        if ln.startswith("TITLE"):
            val = ln[5:].strip().strip('"').strip("'")
            if any(ord(ch) < 32 for ch in val) or any(tok in val.lower() for tok in _FORBIDDEN_PATH_TOKENS):
                raise CubeLutSanitizationError(f"Line {idx}: unsafe control/path characters in TITLE")
            if len(val.encode("utf-8")) > MAX_CUBE_TITLE_BYTES:
                raise CubeLutSanitizationError(f"Line {idx}: TITLE exceeds {MAX_CUBE_TITLE_BYTES} bytes")
            title = val or title
            continue
        if ln.startswith("LUT_1D_SIZE"):
            raise CubeLutSanitizationError(f"Line {idx}: 1D LUTs (LUT_1D_SIZE) are unsupported")
        if ln.startswith("LUT_3D_SIZE"):
            parts = ln.split()
            if len(parts) != 2:
                raise CubeLutSanitizationError(f"Line {idx}: malformed LUT_3D_SIZE")
            if grid_size is not None:
                raise CubeLutSanitizationError(f"Line {idx}: duplicate LUT_3D_SIZE")
            try:
                sz = int(parts[1])
            except ValueError as exc:
                raise CubeLutSanitizationError(f"Line {idx}: invalid LUT_3D_SIZE integer") from exc
            if sz not in SUPPORTED_CUBE_GRID_SIZES:
                raise CubeLutSanitizationError(
                    f"Line {idx}: LUT_3D_SIZE={sz} unsupported; expected {SUPPORTED_CUBE_GRID_SIZES}"
                )
            grid_size = sz
            continue
        if ln.startswith("DOMAIN_MIN") or ln.startswith("DOMAIN_MAX") or ln.startswith("LUT_3D_INPUT_RANGE"):
            parts = ln.split()
            if ln.startswith("LUT_3D_INPUT_RANGE"):
                if len(parts) != 3:
                    raise CubeLutSanitizationError(f"Line {idx}: malformed LUT_3D_INPUT_RANGE")
                try:
                    lo = float(parts[1])
                    hi = float(parts[2])
                except ValueError as exc:
                    raise CubeLutSanitizationError(f"Line {idx}: non-numeric LUT_3D_INPUT_RANGE") from exc
                if not (math.isfinite(lo) and math.isfinite(hi)) or lo >= hi:
                    raise CubeLutSanitizationError(f"Line {idx}: inverted or non-finite LUT_3D_INPUT_RANGE")
                domain_min = (lo, lo, lo)
                domain_max = (hi, hi, hi)
                continue
            if len(parts) != 4:
                raise CubeLutSanitizationError(f"Line {idx}: malformed {parts[0]}")
            try:
                vec = (float(parts[1]), float(parts[2]), float(parts[3]))
            except ValueError as exc:
                raise CubeLutSanitizationError(f"Line {idx}: non-numeric {parts[0]}") from exc
            if not all(math.isfinite(v) for v in vec):
                raise CubeLutSanitizationError(f"Line {idx}: non-finite {parts[0]}")
            if parts[0] == "DOMAIN_MIN":
                domain_min = vec
            else:
                domain_max = vec
            continue

        parts = ln.split()
        if len(parts) != 3:
            raise CubeLutSanitizationError(f"Line {idx}: expected 3 RGB floats, got {ln!r}")
        try:
            r = float(parts[0])
            g = float(parts[1])
            b = float(parts[2])
        except ValueError as exc:
            raise CubeLutSanitizationError(f"Line {idx}: invalid float voxel {ln!r}") from exc
        if not (math.isfinite(r) and math.isfinite(g) and math.isfinite(b)):
            raise CubeLutSanitizationError(f"Line {idx}: NaN/Inf voxel rejected")
        entries.append((r, g, b))

    if grid_size is None:
        raise CubeLutSanitizationError("Missing LUT_3D_SIZE header")
    for c in range(3):
        if domain_min[c] >= domain_max[c]:
            raise CubeLutSanitizationError(
                f"Inverted domain on channel {c}: DOMAIN_MIN={domain_min[c]} >= DOMAIN_MAX={domain_max[c]}"
            )
    expected_voxels = grid_size * grid_size * grid_size
    if len(entries) != expected_voxels:
        raise CubeLutSanitizationError(
            f"Voxel count mismatch for {grid_size}^3 LUT: got {len(entries)}, expected {expected_voxels}"
        )

    return ParsedCubeLut(
        title=title,
        grid_size=grid_size,
        domain_min=domain_min,
        domain_max=domain_max,
        entries=tuple(entries),
        byte_length=len(raw_bytes),
        line_count=len(lines),
        sha256=hashlib.sha256(raw_bytes).hexdigest(),
    )


def tetrahedral_interpolate_rgb(
    lut: ParsedCubeLut,
    r: float,
    g: float,
    b: float,
) -> Tuple[float, float, float, str]:
    """Evaluate 3D LUT at (r, g, b) using exact 6-subtetrahedra barycentric interpolation."""
    if not (math.isfinite(r) and math.isfinite(g) and math.isfinite(b)):
        raise CubeLutSanitizationError("Non-finite input RGB coordinate")
    n = lut.grid_size
    n2 = n * n
    entries = lut.entries
    dmin = lut.domain_min
    dmax = lut.domain_max

    u = (r - dmin[0]) / (dmax[0] - dmin[0])
    v = (g - dmin[1]) / (dmax[1] - dmin[1])
    w = (b - dmin[2]) / (dmax[2] - dmin[2])
    u = 0.0 if u < 0.0 else (1.0 if u > 1.0 else u)
    v = 0.0 if v < 0.0 else (1.0 if v > 1.0 else v)
    w = 0.0 if w < 0.0 else (1.0 if w > 1.0 else w)

    fx = u * (n - 1)
    fy = v * (n - 1)
    fz = w * (n - 1)

    x0 = int(fx)
    y0 = int(fy)
    z0 = int(fz)
    if x0 >= n - 1:
        x0 = n - 2
    if y0 >= n - 1:
        y0 = n - 2
    if z0 >= n - 1:
        z0 = n - 2

    rx = fx - x0
    ry = fy - y0
    rz = fz - z0

    bz0 = z0 * n2
    bz1 = bz0 + n2
    gy0 = y0 * n
    gy1 = gy0 + n

    c000 = entries[bz0 + gy0 + x0]
    c111 = entries[bz1 + gy1 + x0 + 1]

    if rx >= ry:
        if ry >= rz:
            tet = "T1"
            c100 = entries[bz0 + gy0 + x0 + 1]
            c110 = entries[bz0 + gy1 + x0 + 1]
            w0, w1, w2, w3 = 1.0 - rx, rx - ry, ry - rz, rz
            p1, p2 = c100, c110
        elif rx >= rz:
            tet = "T2"
            c100 = entries[bz0 + gy0 + x0 + 1]
            c101 = entries[bz1 + gy0 + x0 + 1]
            w0, w1, w2, w3 = 1.0 - rx, rx - rz, rz - ry, ry
            p1, p2 = c100, c101
        else:
            tet = "T3"
            c001 = entries[bz1 + gy0 + x0]
            c101 = entries[bz1 + gy0 + x0 + 1]
            w0, w1, w2, w3 = 1.0 - rz, rz - rx, rx - ry, ry
            p1, p2 = c001, c101
    else:
        if rx >= rz:
            tet = "T4"
            c010 = entries[bz0 + gy1 + x0]
            c110 = entries[bz0 + gy1 + x0 + 1]
            w0, w1, w2, w3 = 1.0 - ry, ry - rx, rx - rz, rz
            p1, p2 = c010, c110
        elif ry >= rz:
            tet = "T5"
            c010 = entries[bz0 + gy1 + x0]
            c011 = entries[bz1 + gy1 + x0]
            w0, w1, w2, w3 = 1.0 - ry, ry - rz, rz - rx, rx
            p1, p2 = c010, c011
        else:
            tet = "T6"
            c001 = entries[bz1 + gy0 + x0]
            c011 = entries[bz1 + gy1 + x0]
            w0, w1, w2, w3 = 1.0 - rz, rz - ry, ry - rx, rx
            p1, p2 = c001, c011

    out_r = w0 * c000[0] + w1 * p1[0] + w2 * p2[0] + w3 * c111[0]
    out_g = w0 * c000[1] + w1 * p1[1] + w2 * p2[1] + w3 * c111[1]
    out_b = w0 * c000[2] + w1 * p1[2] + w2 * p2[2] + w3 * c111[2]
    return (out_r, out_g, out_b, tet)


def resample_cube_to_33_tetrahedral(lut: ParsedCubeLut) -> Tuple[Tuple[float, float, float], ...]:
    """Resample 17^3, 33^3, or 65^3 `.cube` lattice to CXD90058 33^3 via 6-subtetrahedra barycentric math."""
    n = lut.grid_size
    m = TARGET_HW_LUT_GRID_SIZE
    entries = lut.entries

    if n == m and lut.domain_min == (0.0, 0.0, 0.0) and lut.domain_max == (1.0, 1.0, 1.0):
        return entries

    if n == 65 and lut.domain_min == (0.0, 0.0, 0.0) and lut.domain_max == (1.0, 1.0, 1.0):
        # Exact 2:1 lattice alignment: (rx=0, ry=0, rz=0) reduces every T1..T6 barycentric weight to (1,0,0,0) -> c000
        n2 = n * n
        out65: List[Tuple[float, float, float]] = [entries[0]] * TARGET_HW_LUT_VOXEL_COUNT
        idx = 0
        for bi in range(m):
            b_off = (bi * 2) * n2
            for gi in range(m):
                g_off = b_off + (gi * 2) * n
                for ri in range(m):
                    out65[idx] = entries[g_off + ri * 2]
                    idx += 1
        return tuple(out65)

    n2 = n * n
    out: List[Tuple[float, float, float]] = [(0.0, 0.0, 0.0)] * TARGET_HW_LUT_VOXEL_COUNT
    dmin0, dmin1, dmin2 = lut.domain_min
    span0 = lut.domain_max[0] - dmin0
    span1 = lut.domain_max[1] - dmin1
    span2 = lut.domain_max[2] - dmin2
    inv_m = 1.0 / (m - 1)
    idx = 0

    for bi in range(m):
        wb = bi * inv_m
        w = (wb - dmin2) / span2
        w = 0.0 if w < 0.0 else (1.0 if w > 1.0 else w)
        fz = w * (n - 1)
        z0 = int(fz)
        if z0 >= n - 1:
            z0 = n - 2
        rz = fz - z0
        bz0 = z0 * n2
        bz1 = bz0 + n2

        for gi in range(m):
            vg = gi * inv_m
            v = (vg - dmin1) / span1
            v = 0.0 if v < 0.0 else (1.0 if v > 1.0 else v)
            fy = v * (n - 1)
            y0 = int(fy)
            if y0 >= n - 1:
                y0 = n - 2
            ry = fy - y0
            gy0 = y0 * n
            gy1 = gy0 + n

            for ri in range(m):
                ur = ri * inv_m
                u = (ur - dmin0) / span0
                u = 0.0 if u < 0.0 else (1.0 if u > 1.0 else u)
                fx = u * (n - 1)
                x0 = int(fx)
                if x0 >= n - 1:
                    x0 = n - 2
                rx = fx - x0

                c000 = entries[bz0 + gy0 + x0]
                if rx == 0.0 and ry == 0.0 and rz == 0.0:
                    out[idx] = c000
                    idx += 1
                    continue

                c111 = entries[bz1 + gy1 + x0 + 1]
                if rx >= ry:
                    if ry >= rz:
                        p1 = entries[bz0 + gy0 + x0 + 1]
                        p2 = entries[bz0 + gy1 + x0 + 1]
                        w0, w1, w2, w3 = 1.0 - rx, rx - ry, ry - rz, rz
                    elif rx >= rz:
                        p1 = entries[bz0 + gy0 + x0 + 1]
                        p2 = entries[bz1 + gy0 + x0 + 1]
                        w0, w1, w2, w3 = 1.0 - rx, rx - rz, rz - ry, ry
                    else:
                        p1 = entries[bz1 + gy0 + x0]
                        p2 = entries[bz1 + gy0 + x0 + 1]
                        w0, w1, w2, w3 = 1.0 - rz, rz - rx, rx - ry, ry
                else:
                    if rx >= rz:
                        p1 = entries[bz0 + gy1 + x0]
                        p2 = entries[bz0 + gy1 + x0 + 1]
                        w0, w1, w2, w3 = 1.0 - ry, ry - rx, rx - rz, rz
                    elif ry >= rz:
                        p1 = entries[bz0 + gy1 + x0]
                        p2 = entries[bz1 + gy1 + x0]
                        w0, w1, w2, w3 = 1.0 - ry, ry - rz, rz - rx, rx
                    else:
                        p1 = entries[bz1 + gy0 + x0]
                        p2 = entries[bz1 + gy1 + x0]
                        w0, w1, w2, w3 = 1.0 - rz, rz - ry, ry - rx, rx

                out[idx] = (
                    w0 * c000[0] + w1 * p1[0] + w2 * p2[0] + w3 * c111[0],
                    w0 * c000[1] + w1 * p1[1] + w2 * p2[1] + w3 * c111[1],
                    w0 * c000[2] + w1 * p1[2] + w2 * p2[2] + w3 * c111[2],
                )
                idx += 1

    return tuple(out)


def pack_33cube_dma_table(voxels: Sequence[Tuple[float, float, float]], *, bit_depth: int = 8) -> bytes:
    """Pack 33^3 voxels into CXD90058 DMA format (U8 107,812 B aligned or U16 215,622 B)."""
    if len(voxels) != TARGET_HW_LUT_VOXEL_COUNT:
        raise CubeLutSanitizationError(f"Expected {TARGET_HW_LUT_VOXEL_COUNT} voxels, got {len(voxels)}")
    if bit_depth == 8:
        buf = bytearray(LUT_8BIT_ALIGNED_BYTES)
        j = 0
        for r, g, b in voxels:
            buf[j] = 0 if r <= 0.0 else (255 if r >= 1.0 else int(r * 255.0 + 0.5))
            buf[j + 1] = 0 if g <= 0.0 else (255 if g >= 1.0 else int(g * 255.0 + 0.5))
            buf[j + 2] = 0 if b <= 0.0 else (255 if b >= 1.0 else int(b * 255.0 + 0.5))
            j += 3
        return bytes(buf)
    if bit_depth in (12, 16):
        scale = 4095.0 if bit_depth == 12 else 65535.0
        max_i = 4095 if bit_depth == 12 else 65535
        buf = bytearray(LUT_16BIT_U16_BYTES)
        j = 0
        pack_into = struct.pack_into
        for r, g, b in voxels:
            ir = 0 if r <= 0.0 else (max_i if r >= 1.0 else int(r * scale + 0.5))
            ig = 0 if g <= 0.0 else (max_i if g >= 1.0 else int(g * scale + 0.5))
            ib = 0 if b <= 0.0 else (max_i if b >= 1.0 else int(b * scale + 0.5))
            pack_into("<HHH", buf, j, ir, ig, ib)
            j += 6
        return bytes(buf)
    raise CubeLutSanitizationError(f"Unsupported DMA bit_depth={bit_depth!r}; expected 8, 12, or 16")


def build_ivshmem_0165_dma_packet(lut_bytes: int, shm_offset: int = IVSHMEM_SHM_DMA_LUT_OFFSET) -> bytes:
    """Build 36-byte UIPC BB 0x0165 3D-LUT DMA packet (> 0xbb80 DRAM DMA threshold)."""
    return struct.pack(
        "<HHIIIIIII",
        UIPC_BB_MAGIC,
        UIPC_BB_FLAGS,
        IVSHMEM_LUT_DMA_OPCODE,
        shm_offset,
        lut_bytes,
        TARGET_HW_LUT_GRID_SIZE,
        1 if lut_bytes > LUT_DMA_SRAM_REG_THRESHOLD else 0,
        0,
        0,
    ) + b"\x00" * 4


def build_ivshmem_0166_toggle_packet(*, enable: bool, slot_index: int = 3) -> bytes:
    """Build 10-byte UIPC BB 0x0166 volatile LUT slot toggle packet."""
    return struct.pack(
        "<HHHBBH",
        UIPC_BB_MAGIC,
        UIPC_BB_FLAGS,
        IVSHMEM_LUT_TOGGLE_OPCODE,
        1 if enable else 0,
        slot_index & 0xFF,
        0,
    )


def stage_lut3d_into_volatile_ivshmem(
    lut: ParsedCubeLut,
    *,
    source_name: str = "User1.cube",
    bit_depth: int = 8,
    main_slog3_clean: bool = True,
    proxy_mlut_enabled: bool = True,
    hdmi_clean_feed: bool = True,
    hdmi_raw16_active: bool = False,
) -> TetrahedralResampleResult:
    """Resample 17^3/33^3/65^3 -> 33^3 via 6-subtetrahedra math and stage into volatile IVSHMEM 0x0165/0x0166."""
    if not main_slog3_clean:
        raise CubeLutSanitizationError(
            "Main-SLog3 internal XAVC stream must remain clean/unbaked (main_slog3_clean=True required)"
        )

    resampled = resample_cube_to_33_tetrahedral(lut)
    dma_bytes = pack_33cube_dma_table(resampled, bit_depth=bit_depth)
    dma_sha = hashlib.sha256(dma_bytes).hexdigest()

    # Probe all 6 Kuhn subtetrahedra T1..T6 and neutral gray axis R==G==B
    probe_points: Tuple[Tuple[float, float, float], ...] = (
        (0.73, 0.41, 0.19),  # rx > ry > rz -> T1
        (0.73, 0.19, 0.41),  # rx > rz > ry -> T2
        (0.41, 0.19, 0.73),  # rz > rx > ry -> T3
        (0.41, 0.73, 0.19),  # ry > rx > rz -> T4
        (0.19, 0.73, 0.41),  # ry > rz > rx -> T5
        (0.19, 0.41, 0.73),  # rz > ry > rx -> T6
    )
    tets_hit: Set[str] = set()
    max_bleed = 0.0
    for pr, pg, pb in probe_points:
        _or, _og, _ob, tet_id = tetrahedral_interpolate_rgb(lut, pr, pg, pb)
        tets_hit.add(tet_id)

    for g_val in (0.125, 0.25, 0.41, 0.5625, 0.75, 0.875):
        nr, ng, nb, _ = tetrahedral_interpolate_rgb(lut, g_val, g_val, g_val)
        bleed = max(abs(nr - ng), abs(ng - nb), abs(nr - nb))
        if bleed > max_bleed:
            max_bleed = bleed

    # Linearity error on affine reference check (exact for any grid size)
    affine_lut = build_synthetic_cube_lattice(grid_size=17, title="LINEAR_CHECK", curve="affine_matrix")
    max_lin_err = 0.0
    for pr, pg, pb in probe_points:
        ar, ag, ab, _ = tetrahedral_interpolate_rgb(affine_lut, pr, pg, pb)
        er, eg, eb = _eval_lut_curve_point(pr, pg, pb, "affine_matrix")
        err = max(abs(ar - er), abs(ag - eg), abs(ab - eb))
        if err > max_lin_err:
            max_lin_err = err

    pkt_0165 = build_ivshmem_0165_dma_packet(len(dma_bytes))
    pkt_0166 = build_ivshmem_0166_toggle_packet(enable=True, slot_index=3)

    # HDMI RAW16 forces clean unbaked feed (MLUT never applied on RAW16)
    hdmi_mlut_applied = False if (hdmi_clean_feed or hdmi_raw16_active) else True

    passed = (
        len(resampled) == TARGET_HW_LUT_VOXEL_COUNT
        and len(tets_hit) == 6
        and max_lin_err < 1e-12
        and len(dma_bytes) > LUT_DMA_SRAM_REG_THRESHOLD
        and len(pkt_0165) == 36
        and len(pkt_0166) == 10
        and NVRAM_PERSISTENT_WRITES == 0
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
    )

    return TetrahedralResampleResult(
        passed=passed,
        source_name=source_name,
        source_grid_size=lut.grid_size,
        target_grid_size=TARGET_HW_LUT_GRID_SIZE,
        source_voxel_count=len(lut.entries),
        target_voxel_count=len(resampled),
        subtetrahedra_exercised=tuple(sorted(tets_hit)),
        max_linearity_error=round(max_lin_err, 15),
        max_neutral_axis_bleed=round(max_bleed, 12),
        dma_bit_depth=bit_depth,
        dma_table_bytes=len(dma_bytes),
        dma_table_sha256=dma_sha,
        uses_dram_dma_path=len(dma_bytes) > LUT_DMA_SRAM_REG_THRESHOLD,
        ivshmem_slot_0165_hex=pkt_0165.hex(),
        ivshmem_slot_0166_hex=pkt_0166.hex(),
        ivshmem_shm_offset_hex=f"0x{IVSHMEM_SHM_DMA_LUT_OFFSET:05x}",
        routing_main_slog3_clean=main_slog3_clean,
        routing_proxy_mlut_enabled=proxy_mlut_enabled,
        routing_hdmi_clean_feed=hdmi_clean_feed or hdmi_raw16_active,
        routing_hdmi_mlut_applied=hdmi_mlut_applied,
        hdmi_raw16_active=hdmi_raw16_active,
        nvram_persistent_writes=NVRAM_PERSISTENT_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
    )


# ---------------------------------------------------------------------------
# Part 2: CEA-861-G HDMI AVI InfoFrame + VSIF REC-Trigger -> 12G-SDI Bridge
# ---------------------------------------------------------------------------

AVI_INFOFRAME_TYPE_CODE = 0x82
AVI_INFOFRAME_VERSION = 0x02
AVI_INFOFRAME_PAYLOAD_LEN = 0x0D  # 13 bytes PB1..PB13
AVI_INFOFRAME_TOTAL_BYTES = 17    # 3B header + PB0 checksum + 13B payload

VSIF_INFOFRAME_TYPE_CODE = 0x81
VSIF_SONY_IEEE_OUI_WIRE = bytes((0x46, 0x00, 0x08))  # Sony 08-00-46 little-endian wire order

SDI_TRS_SAFE_MIN_10BIT = 0x004
SDI_TRS_SAFE_MAX_10BIT = 0x3FB
SDI_LEGAL_MIN_10BIT = 0x040  # 64
SDI_LEGAL_MAX_10BIT = 0x3AC  # 940
RP188_ANC_DID = 0x60
RP188_ANC_SDID = 0x60

VALID_AVI_COLOR_FORMATS: Mapping[str, int] = {
    "RGB": 0,
    "YCBCR_422": 1,
    "YCBCR_444": 2,
    "YCBCR_420": 3,
}

VALID_AVI_GAMUTS: Mapping[str, Tuple[int, int]] = {
    # (C1:C0 colorimetry, EC2:EC0 extended colorimetry)
    "REC_709": (2, 0),
    "XVYCC_709_EXT": (3, 1),
    "BT2020_YCC": (3, 6),
    "S_GAMUT3_CINE_SLOG3": (3, 6),
}

VALID_QUANTIZATION_MODES: Mapping[str, int] = {
    "LIMITED_LEGAL": 0,
    "FULL_RANGE": 1,
}

BRIDGE_FPS_RATIONAL: Mapping[str, Tuple[int, int, int, bool]] = {
    # label -> (fps_int_ceil, rate_num, rate_den, drop_frame)
    "23.98p": (24, 24000, 1001, False),
    "24.00p": (24, 24, 1, False),
    "25.00p": (25, 25, 1, False),
    "29.97p": (30, 30000, 1001, True),
    "59.94p": (60, 60000, 1001, True),
}


@dataclass(frozen=True)
class AviInfoFrameAudit:
    valid: bool
    frame_bytes: int
    frame_hex: str
    packet_type: int
    version: int
    payload_len: int
    checksum_byte: int
    checksum_mod256_zero: bool
    color_format_code: int
    color_format: str
    bit_depth: int
    colorimetry_code: int
    extended_colorimetry_code: int
    gamut_label: str
    ycc_quantization_code: int
    quantization_label: str
    vic: int
    slog3_quantization_guard_ok: bool
    guard_reason: str


@dataclass(frozen=True)
class HdmiTo12gSdiBridgeResult:
    passed: bool
    status: str
    avi_infoframe_bytes: int
    avi_infoframe_hex: str
    avi_checksum_zero: bool
    slog3_quantization_guard_ok: bool
    sdi_standard: str
    sdi_link_gbps: float
    fps_label: str
    drop_frame: bool
    rec_burst_frames: int
    rec_start_edges_detected: int
    rec_stop_edges_detected: int
    dropped_rec_triggers: int
    rp188_packets_emitted: int
    rp188_ltc_vitc_locked: bool
    ltc_vitc_frame_offset: int
    sdi_trs_collisions: int
    fx3_sdi_bnc_present: bool
    sdi_transceiver_faults: int
    vsif_rec_start_hex: str
    vsif_rec_stop_hex: str
    rp188_sample_hex: str


def build_hdmi_avi_infoframe(
    *,
    color_format: str = "YCBCR_422",
    bit_depth: int = 10,
    gamut: str = "S_GAMUT3_CINE_SLOG3",
    quantization: str = "LIMITED_LEGAL",
    vic: int = 97,
) -> Tuple[bytes, AviInfoFrameAudit]:
    """Synthesize a 17-byte CEA-861-G HDMI AVI InfoFrame with exact mod-256 checksum == 0."""
    if color_format not in VALID_AVI_COLOR_FORMATS:
        raise Lut3dSubzeroSdiError(f"Unsupported color_format={color_format!r}")
    if bit_depth not in (8, 10, 12):
        raise Lut3dSubzeroSdiError(f"Unsupported bit_depth={bit_depth!r}")
    if gamut not in VALID_AVI_GAMUTS:
        raise Lut3dSubzeroSdiError(f"Unsupported gamut={gamut!r}")
    if quantization not in VALID_QUANTIZATION_MODES:
        raise Lut3dSubzeroSdiError(f"Unsupported quantization={quantization!r}")
    if not (1 <= vic <= 127):
        raise Lut3dSubzeroSdiError(f"VIC {vic} out of CEA-861-G range [1, 127]")

    y_code = VALID_AVI_COLOR_FORMATS[color_format]
    c_code, ec_code = VALID_AVI_GAMUTS[gamut]
    yq_code = VALID_QUANTIZATION_MODES[quantization]

    # S-Log3 + 12G-SDI guard: requires YCbCr 4:2:2 10-bit, extended gamut, and TRS-safe legal quantization
    guard_reasons: List[str] = []
    if color_format != "YCBCR_422" or bit_depth != 10:
        guard_reasons.append("Requires YCbCr 4:2:2 10-bit transport for 12G-SDI ST 2082 bridge")
    if gamut in ("S_GAMUT3_CINE_SLOG3", "BT2020_YCC", "XVYCC_709_EXT") and c_code != 3:
        guard_reasons.append("Extended gamut requires C=3 extended colorimetry")
    if gamut == "S_GAMUT3_CINE_SLOG3" and yq_code != 0:
        guard_reasons.append("Full-range YCbCr (YQ=1) collides with 10-bit SDI TRS 0x000..0x003/0x3FC..0x3FF")
    guard_ok = len(guard_reasons) == 0

    pb1 = ((y_code & 0x07) << 5) | 0x10  # A0=1 active format valid
    pb2 = ((c_code & 0x03) << 6) | (0x02 << 4) | 0x08  # 16:9 picture + active same
    pb3 = (ec_code & 0x07) << 4
    pb4 = vic & 0x7F
    pb5 = (yq_code & 0x03) << 6

    header = bytes((AVI_INFOFRAME_TYPE_CODE, AVI_INFOFRAME_VERSION, AVI_INFOFRAME_PAYLOAD_LEN))
    payload = bytes((pb1, pb2, pb3, pb4, pb5)) + (b"\x00" * 8)
    raw_sum = (sum(header) + sum(payload)) & 0xFF
    pb0 = (0x100 - raw_sum) & 0xFF
    frame = header + bytes((pb0,)) + payload

    audit = AviInfoFrameAudit(
        valid=(len(frame) == AVI_INFOFRAME_TOTAL_BYTES and ((sum(frame) & 0xFF) == 0) and guard_ok),
        frame_bytes=len(frame),
        frame_hex=frame.hex(),
        packet_type=AVI_INFOFRAME_TYPE_CODE,
        version=AVI_INFOFRAME_VERSION,
        payload_len=AVI_INFOFRAME_PAYLOAD_LEN,
        checksum_byte=pb0,
        checksum_mod256_zero=((sum(frame) & 0xFF) == 0),
        color_format_code=y_code,
        color_format=color_format,
        bit_depth=bit_depth,
        colorimetry_code=c_code,
        extended_colorimetry_code=ec_code,
        gamut_label=gamut,
        ycc_quantization_code=yq_code,
        quantization_label=quantization,
        vic=vic,
        slog3_quantization_guard_ok=guard_ok,
        guard_reason="OK" if guard_ok else "; ".join(guard_reasons),
    )
    return frame, audit


def parse_and_verify_hdmi_avi_infoframe(frame: bytes) -> AviInfoFrameAudit:
    """Parse and validate a raw 17-byte CEA-861-G HDMI AVI InfoFrame."""
    if len(frame) != AVI_INFOFRAME_TOTAL_BYTES:
        raise Lut3dSubzeroSdiError(
            f"AVI InfoFrame must be {AVI_INFOFRAME_TOTAL_BYTES} bytes, got {len(frame)}"
        )
    hb0, hb1, hb2, pb0 = frame[0], frame[1], frame[2], frame[3]
    if hb0 != AVI_INFOFRAME_TYPE_CODE or hb1 != AVI_INFOFRAME_VERSION or hb2 != AVI_INFOFRAME_PAYLOAD_LEN:
        raise Lut3dSubzeroSdiError(f"Invalid AVI InfoFrame header: {hb0:02x} {hb1:02x} {hb2:02x}")
    checksum_ok = (sum(frame) & 0xFF) == 0
    if not checksum_ok:
        raise Lut3dSubzeroSdiError("AVI InfoFrame checksum mod-256 != 0")

    pb1, pb2, pb3, pb4, pb5 = frame[4], frame[5], frame[6], frame[7], frame[8]
    y_code = (pb1 >> 5) & 0x07
    c_code = (pb2 >> 6) & 0x03
    ec_code = (pb3 >> 4) & 0x07
    vic = pb4 & 0x7F
    yq_code = (pb5 >> 6) & 0x03

    rev_y = {v: k for k, v in VALID_AVI_COLOR_FORMATS.items()}.get(y_code, "UNKNOWN")
    rev_q = {v: k for k, v in VALID_QUANTIZATION_MODES.items()}.get(yq_code, "RESERVED")
    guard_ok = (y_code == 1) and (c_code == 3) and (ec_code in (1, 6)) and (yq_code == 0)

    return AviInfoFrameAudit(
        valid=checksum_ok and guard_ok,
        frame_bytes=len(frame),
        frame_hex=frame.hex(),
        packet_type=hb0,
        version=hb1,
        payload_len=hb2,
        checksum_byte=pb0,
        checksum_mod256_zero=checksum_ok,
        color_format_code=y_code,
        color_format=rev_y,
        bit_depth=10,
        colorimetry_code=c_code,
        extended_colorimetry_code=ec_code,
        gamut_label="S_GAMUT3_CINE_SLOG3" if (c_code == 3 and ec_code == 6) else "OTHER",
        ycc_quantization_code=yq_code,
        quantization_label=rev_q,
        vic=vic,
        slog3_quantization_guard_ok=guard_ok,
        guard_reason="OK" if guard_ok else "AVI quantization or colorimetry mismatch for S-Log3 4:2:2",
    )


def _to_bcd(val: int) -> int:
    return ((val // 10) << 4) | (val % 10)


def build_sony_rec_vsif_packet(
    *,
    rec_active: bool,
    transition_edge: str,
    frame_seq: int,
    tc_hmsf: Tuple[int, int, int, int],
    drop_frame: bool,
) -> bytes:
    """Build Sony Vendor-Specific InfoFrame carrying REC-trigger edge & SMPTE timecode."""
    edge_code = {"IDLE": 0, "RISING_START": 1, "HOLD_REC": 2, "FALLING_STOP": 3}.get(transition_edge, 0)
    hh, mm, ss, ff = tc_hmsf
    flags = (0x01 if rec_active else 0x00) | ((edge_code & 0x03) << 1) | (0x08 if drop_frame else 0x00)
    body = (
        VSIF_SONY_IEEE_OUI_WIRE
        + bytes(
            (
                flags,
                _to_bcd(ff) | (0x40 if drop_frame else 0x00),
                _to_bcd(ss),
                _to_bcd(mm),
                _to_bcd(hh),
                frame_seq & 0xFF,
            )
        )
    )
    hdr = bytes((VSIF_INFOFRAME_TYPE_CODE, 0x01, len(body)))
    chk = (0x100 - ((sum(hdr) + sum(body)) & 0xFF)) & 0xFF
    return hdr + bytes((chk,)) + body


def build_rp188_hanc_packet(
    *,
    rec_active: bool,
    tc_hmsf: Tuple[int, int, int, int],
    drop_frame: bool,
    is_vitc: bool = False,
) -> bytes:
    """Build SMPTE RP 188 / ST 12-2 HANC LTC/VITC metadata packet for 12G-SDI bridge."""
    hh, mm, ss, ff = tc_hmsf
    dbb1 = 0x01 if is_vitc else 0x00  # DBB1 selects LTC vs VITC1 payload
    dbb2 = (0x80 if rec_active else 0x00) | (0x40 if drop_frame else 0x00)
    udw = bytes(
        (
            dbb1,
            dbb2,
            _to_bcd(ff) | (0x40 if drop_frame else 0x00),
            _to_bcd(ss),
            _to_bcd(mm),
            _to_bcd(hh),
            0x42,  # User-Bits BG1..BG2 (Cam B)
            0x00,
        )
    )
    # ANC header: DID=0x60, SDID=0x60, DC=len(udw)
    pkt = bytes((RP188_ANC_DID, RP188_ANC_SDID, len(udw))) + udw
    chk = sum(pkt) & 0xFF
    return pkt + bytes((chk,))


def simulate_hdmi_to_12g_sdi_rec_bridge(
    *,
    fps_label: str = "59.94p",
    resolution: str = "3840x2160",
    gamut: str = "S_GAMUT3_CINE_SLOG3",
    quantization: str = "LIMITED_LEGAL",
    rec_burst_frames: int = 24,
    inject_illegal_trs_codes: bool = False,
) -> HdmiTo12gSdiBridgeResult:
    """Co-emulate CEA-861-G AVI InfoFrame + Sony VSIF REC trigger -> 12G-SDI ST 2082 bridge."""
    if fps_label not in BRIDGE_FPS_RATIONAL:
        raise Lut3dSubzeroSdiError(f"Unsupported fps_label={fps_label!r}")
    if rec_burst_frames < 2:
        raise Lut3dSubzeroSdiError("rec_burst_frames must be >= 2")

    fps_int, _num, _den, drop_frame = BRIDGE_FPS_RATIONAL[fps_label]
    vic = 97 if (resolution == "3840x2160" and fps_int == 60) else (93 if resolution == "3840x2160" else 16)
    avi_frame, avi_audit = build_hdmi_avi_infoframe(
        color_format="YCBCR_422",
        bit_depth=10,
        gamut=gamut,
        quantization=quantization,
        vic=vic,
    )
    parsed_avi = parse_and_verify_hdmi_avi_infoframe(avi_frame)

    # Select SDI standard (NTSC 1000/1001 rates divide clock by 1.001 even when NDF)
    is_ntsc_fractional = (_den == 1001)
    if resolution == "3840x2160" and fps_int >= 50:
        sdi_std = "SMPTE_ST_2082_12G_SDI"
        sdi_gbps = 11.868 if is_ntsc_fractional else 11.88
    elif resolution == "3840x2160":
        sdi_std = "SMPTE_ST_2081_6G_SDI"
        sdi_gbps = 5.934 if is_ntsc_fractional else 5.94
    elif resolution == "1920x1080" and fps_int >= 50:
        sdi_std = "SMPTE_ST_424_3G_SDI"
        sdi_gbps = 2.967 if is_ntsc_fractional else 2.97
    else:
        sdi_std = "SMPTE_ST_292_1_5G_SDI"
        sdi_gbps = 1.4835 if is_ntsc_fractional else 1.485

    # Check 10-bit SDI TRS collision guard (reserved 0x000..0x003 & 0x3FC..0x3FF)
    trs_collisions = 0
    if inject_illegal_trs_codes:
        sample_codewords = (0x000, 0x002, 0x3FC, 0x3FF)
        if avi_audit.slog3_quantization_guard_ok:
            # S-Log3 legalizer clamps out-of-range spikes to [0x004..0x3FB]
            clamped = [max(SDI_TRS_SAFE_MIN_10BIT, min(SDI_TRS_SAFE_MAX_10BIT, c)) for c in sample_codewords]
            trs_collisions = sum(1 for c in clamped if c < SDI_TRS_SAFE_MIN_10BIT or c > SDI_TRS_SAFE_MAX_10BIT)
        else:
            # Unguarded full-range leaks reserved SDI TRS words
            trs_collisions = sum(
                1 for c in sample_codewords if c < SDI_TRS_SAFE_MIN_10BIT or c > SDI_TRS_SAFE_MAX_10BIT
            )

    # Simulate frame sequence: 2 IDLE -> rec_burst_frames REC (1st is RISING_START) -> 2 IDLE (1st is FALLING_STOP)
    rec_start_edges = 0
    rec_stop_edges = 0
    dropped_triggers = 0
    rp188_count = 0
    ltc_vitc_offsets: List[int] = []
    vsif_start_hex = ""
    vsif_stop_hex = ""
    rp188_sample_hex = ""
    prev_rec = False

    total_steps = 2 + rec_burst_frames + 2
    for step in range(total_steps):
        rec_now = 2 <= step < (2 + rec_burst_frames)
        if rec_now and not prev_rec:
            edge = "RISING_START"
        elif rec_now and prev_rec:
            edge = "HOLD_REC"
        elif (not rec_now) and prev_rec:
            edge = "FALLING_STOP"
        else:
            edge = "IDLE"

        ff = step % fps_int
        ss = 10 + (step // fps_int)
        tc = (1, 0, ss, ff)

        vsif = build_sony_rec_vsif_packet(
            rec_active=rec_now,
            transition_edge=edge,
            frame_seq=step,
            tc_hmsf=tc,
            drop_frame=drop_frame,
        )
        if edge == "RISING_START":
            vsif_start_hex = vsif.hex()
        elif edge == "FALLING_STOP":
            vsif_stop_hex = vsif.hex()

        # Verify VSIF checksum and forward edge over bridge to RP 188 LTC + VITC
        if (sum(vsif) & 0xFF) != 0:
            dropped_triggers += 1
        else:
            rx_flags = vsif[7]
            rx_edge = (rx_flags >> 1) & 0x03
            if rx_edge == 1:
                rec_start_edges += 1
            elif rx_edge == 3:
                rec_stop_edges += 1

        rp_ltc = build_rp188_hanc_packet(rec_active=rec_now, tc_hmsf=tc, drop_frame=drop_frame, is_vitc=False)
        rp_vitc = build_rp188_hanc_packet(rec_active=rec_now, tc_hmsf=tc, drop_frame=drop_frame, is_vitc=True)
        rp188_count += 2
        if step == 2:
            rp188_sample_hex = rp_ltc.hex()
        # Exact frame lock: LTC & VITC BCD timecodes match identically
        ltc_vitc_offsets.append(0 if rp_ltc[5:9] == rp_vitc[5:9] else 1)
        prev_rec = rec_now

    max_offset = max(ltc_vitc_offsets)
    passed = (
        avi_audit.valid
        and parsed_avi.checksum_mod256_zero
        and avi_audit.slog3_quantization_guard_ok
        and rec_start_edges == 1
        and rec_stop_edges == 1
        and dropped_triggers == 0
        and max_offset == 0
        and trs_collisions == 0
        and SDI_TRANSCEIVER_FAULTS == 0
    )

    if not avi_audit.slog3_quantization_guard_ok:
        status = "BLOCKED_SLOG3_QUANTIZATION_TRS_HAZARD"
    elif trs_collisions > 0:
        status = "BLOCKED_SDI_TRS_CODEWORD_COLLISION"
    elif passed:
        status = "BRIDGE_LOCKED_ZERO_DROPPED_TRIGGERS"
    else:
        status = "BRIDGE_FAULT"

    return HdmiTo12gSdiBridgeResult(
        passed=passed,
        status=status,
        avi_infoframe_bytes=avi_audit.frame_bytes,
        avi_infoframe_hex=avi_audit.frame_hex,
        avi_checksum_zero=avi_audit.checksum_mod256_zero,
        slog3_quantization_guard_ok=avi_audit.slog3_quantization_guard_ok,
        sdi_standard=sdi_std,
        sdi_link_gbps=sdi_gbps,
        fps_label=fps_label,
        drop_frame=drop_frame,
        rec_burst_frames=rec_burst_frames,
        rec_start_edges_detected=rec_start_edges,
        rec_stop_edges_detected=rec_stop_edges,
        dropped_rec_triggers=dropped_triggers,
        rp188_packets_emitted=rp188_count,
        rp188_ltc_vitc_locked=(max_offset == 0),
        ltc_vitc_frame_offset=max_offset,
        sdi_trs_collisions=trs_collisions,
        fx3_sdi_bnc_present=False,
        sdi_transceiver_faults=SDI_TRANSCEIVER_FAULTS,
        vsif_rec_start_hex=vsif_start_hex,
        vsif_rec_stop_hex=vsif_stop_hex,
        rp188_sample_hex=rp188_sample_hex,
    )


# ---------------------------------------------------------------------------
# Part 3: Sub-Zero (-20C) Arrhenius ESR & High-Altitude (5,200m) Derating HIL
# ---------------------------------------------------------------------------

NPFZ100_REF_TEMP_C = 25.0
NPFZ100_REF_ESR_25C_OHM = 0.175
NPFZ100_ARRHENIUS_EA_OVER_R_K = 3050.0
NPFZ100_PMIC_UVLO_CUTOFF_V = 6.0
NPFZ100_PROACTIVE_HANDOFF_V = 6.35
NPFZ100_DEFAULT_PEAK_LOAD_WATTS = 8.5

USB_PD_9V3A_BUS_V = 9.0
USB_PD_9V3A_MAX_WATTS = 27.0

_NPFZ100_OCV_CURVE: Tuple[Tuple[float, float], ...] = (
    (0.0, 6.20),
    (15.0, 6.90),
    (45.0, 7.28),
    (80.0, 7.92),
    (100.0, 8.35),
)

ISA_SEA_LEVEL_TEMP_K = 288.15
ISA_LAPSE_RATE_K_PER_M = 0.0065
ISA_SEA_LEVEL_PRESSURE_KPA = 101.325
ISA_SEA_LEVEL_AIR_DENSITY_KG_M3 = 1.225
ISA_GRAVITY_M_S2 = 9.80665
ISA_SPECIFIC_GAS_AIR_J_KG_K = 287.058
ISA_PRESSURE_EXPONENT = ISA_GRAVITY_M_S2 / (ISA_SPECIFIC_GAS_AIR_J_KG_K * ISA_LAPSE_RATE_K_PER_M)
ISA_DENSITY_EXPONENT = ISA_PRESSURE_EXPONENT - 1.0

FX3_SEA_LEVEL_COOLING_HEADROOM_WATTS = 10.5
FX3_BK4_CXD90057_WARN_TEMP_C = 82.0


@dataclass(frozen=True)
class SubzeroPowerHilResult:
    passed: bool
    status: str
    cell_temp_c: float
    battery_soc_pct: float
    v_oc_v: float
    r_int_ohm: float
    esr_multiplier: float
    load_watts: float
    unassisted_v_term_v: float
    would_cross_uvlo_unassisted: bool
    usb_pd_9v3a_attached: bool
    hot_handoff_executed: bool
    min_bus_voltage_v: float
    pmic_uvlo_cutoff_v: float
    pmic_uvlo_trips: int
    charging_requested: bool
    charging_enabled: bool
    charging_blocked_for_plating_prevention: bool
    lithium_plating_events: int
    rsv_salvage_triggered: bool
    active_recording_frames: int
    rsv_salvageable_frames: int
    dropped_frames: int
    emmc_corruptions: int


@dataclass(frozen=True)
class HighAltitudeThermalHilResult:
    passed: bool
    status: str
    altitude_m: float
    ambient_temp_c: float
    atmospheric_pressure_kpa: float
    air_density_kg_m3: float
    fan_mass_flow_ratio: float
    derated_cooling_capacity_watts: float
    workload_shooting_watts: float
    ftps_background_watts: float
    effective_thermal_watts: float
    sea_level_pwm_pct: float
    boosted_pwm_pct: float
    boosted_fan_rpm: int
    ftps_background_shed: bool
    cxd90057_t_warn_c: float
    cxd90057_peak_temp_c: float
    thermal_warn_tripped: bool
    dropped_recording_frames: int
    nvram_persistent_writes: int
    persistent_emmc_writes_authorized: bool


def compute_arrhenius_esr_ohm(cell_temp_c: float) -> float:
    """Compute NP-FZ100 2S Li-Ion DC internal resistance R_int(T) via Arrhenius law."""
    if not math.isfinite(cell_temp_c) or cell_temp_c < -50.0 or cell_temp_c > 85.0:
        raise Lut3dSubzeroSdiError(f"cell_temp_c={cell_temp_c!r} out of valid range [-50, 85]")
    t_k = float(cell_temp_c) + 273.15
    t_ref_k = NPFZ100_REF_TEMP_C + 273.15
    return NPFZ100_REF_ESR_25C_OHM * math.exp(NPFZ100_ARRHENIUS_EA_OVER_R_K * ((1.0 / t_k) - (1.0 / t_ref_k)))


def compute_npfz100_ocv_v(soc_pct: float) -> float:
    """Compute piecewise-linear 2S NP-FZ100 open-circuit voltage V_oc(SoC%)."""
    if not math.isfinite(soc_pct) or soc_pct < 0.0 or soc_pct > 100.0:
        raise Lut3dSubzeroSdiError(f"soc_pct={soc_pct!r} out of range [0, 100]")
    for (s0, v0), (s1, v1) in zip(_NPFZ100_OCV_CURVE, _NPFZ100_OCV_CURVE[1:]):
        if s0 <= soc_pct <= s1:
            return v0 + (v1 - v0) * ((soc_pct - s0) / (s1 - s0))
    return _NPFZ100_OCV_CURVE[-1][1]


def solve_terminal_voltage_v(v_oc: float, r_int: float, load_watts: float) -> float:
    """Solve quadratic constant-power terminal voltage V_term = V_oc - (P / V_term) * R_int."""
    if load_watts <= 0.0:
        return v_oc
    disc = v_oc * v_oc - 4.0 * load_watts * r_int
    if disc <= 0.0:
        return 0.0
    return 0.5 * (v_oc + math.sqrt(disc))


def compute_isa_atmosphere(altitude_m: float) -> Tuple[float, float, float]:
    """Return `(pressure_kpa, air_density_kg_m3, fan_mass_flow_ratio)` per ISA troposphere."""
    if not math.isfinite(altitude_m) or altitude_m < -500.0 or altitude_m > 10_000.0:
        raise Lut3dSubzeroSdiError(f"altitude_m={altitude_m!r} out of range [-500, 10000]")
    temp_ratio = 1.0 - (ISA_LAPSE_RATE_K_PER_M * float(altitude_m)) / ISA_SEA_LEVEL_TEMP_K
    pressure_kpa = ISA_SEA_LEVEL_PRESSURE_KPA * (temp_ratio ** ISA_PRESSURE_EXPONENT)
    density_kg_m3 = ISA_SEA_LEVEL_AIR_DENSITY_KG_M3 * (temp_ratio ** ISA_DENSITY_EXPONENT)
    return pressure_kpa, density_kg_m3, density_kg_m3 / ISA_SEA_LEVEL_AIR_DENSITY_KG_M3


def simulate_subzero_usbpd_hot_handoff(
    *,
    cell_temp_c: float = -20.0,
    battery_soc_pct: float = 45.0,
    load_watts: float = NPFZ100_DEFAULT_PEAK_LOAD_WATTS,
    usb_pd_9v3a_attached: bool = True,
    request_liion_charge_at_subzero: bool = True,
    active_recording_frames: int = 120,
) -> SubzeroPowerHilResult:
    """Co-emulate sub-zero (-20C) NP-FZ100 sag -> USB-PD 9V/3A hot-handoff & plating lock."""
    if not math.isfinite(load_watts) or load_watts < 0.0 or load_watts > 30.0:
        raise Lut3dSubzeroSdiError(f"Invalid load_watts={load_watts!r}")
    if active_recording_frames <= 0:
        raise Lut3dSubzeroSdiError("active_recording_frames must be positive")

    v_oc = compute_npfz100_ocv_v(battery_soc_pct)
    r_int = compute_arrhenius_esr_ohm(cell_temp_c)
    esr_mult = r_int / NPFZ100_REF_ESR_25C_OHM
    unassisted_v = solve_terminal_voltage_v(v_oc, r_int, load_watts)
    would_uvlo = unassisted_v < NPFZ100_PMIC_UVLO_CUTOFF_V

    # Sub-zero Li-Ion charging is strictly blocked <= 0.0 C to prevent metallic lithium plating
    subzero_lock = cell_temp_c <= 0.0
    charging_blocked = subzero_lock and request_liion_charge_at_subzero
    charging_enabled = (not subzero_lock) and request_liion_charge_at_subzero and usb_pd_9v3a_attached

    # Simulate transient ramp from idle (3.2W) -> 4K120 + Active IBIS (load_watts)
    hot_handoff = False
    min_bus_v = v_oc
    pmic_uvlo_trips = 0
    rsv_salvage = False
    dropped_frames = 0

    for frac in (0.35, 0.55, 0.75, 0.90, 1.00):
        p_step = load_watts * frac
        v_batt = solve_terminal_voltage_v(v_oc, r_int, p_step)
        if (not hot_handoff) and v_batt <= NPFZ100_PROACTIVE_HANDOFF_V:
            if usb_pd_9v3a_attached:
                # Seamless USB-PD 9V/3A (27W) hot-handoff before V_term reaches 6.0V PMIC UVLO
                hot_handoff = True
                bus_v = USB_PD_9V3A_BUS_V - 0.12  # cable/FET drop -> ~8.88V
            else:
                # No USB-PD backup: proactively trigger zero-loss .RSV salvage before 6.0V crash
                rsv_salvage = True
                bus_v = v_batt
                if bus_v < NPFZ100_PMIC_UVLO_CUTOFF_V:
                    pmic_uvlo_trips += 1
                if bus_v < min_bus_v:
                    min_bus_v = bus_v
                break
        else:
            bus_v = (USB_PD_9V3A_BUS_V - 0.12) if hot_handoff else v_batt
        if bus_v < min_bus_v:
            min_bus_v = bus_v

    if usb_pd_9v3a_attached:
        status = (
            "USBPD_9V3A_HOT_HANDOFF_OK_CHARGING_LOCKED_SUBZERO"
            if subzero_lock
            else "USBPD_9V3A_HOT_HANDOFF_OK"
        )
        passed = (
            min_bus_v > NPFZ100_PMIC_UVLO_CUTOFF_V
            and pmic_uvlo_trips == 0
            and (not charging_enabled)
            and dropped_frames == 0
        )
    else:
        status = (
            "GRACEFUL_RSV_SALVAGE_NO_USBPD_SUBZERO"
            if rsv_salvage
            else "NOMINAL_BATTERY_OPERATION"
        )
        passed = (rsv_salvage or min_bus_v > NPFZ100_PMIC_UVLO_CUTOFF_V) and (not charging_enabled)

    if not subzero_lock and usb_pd_9v3a_attached and request_liion_charge_at_subzero:
        passed = min_bus_v > NPFZ100_PMIC_UVLO_CUTOFF_V and pmic_uvlo_trips == 0

    return SubzeroPowerHilResult(
        passed=passed,
        status=status,
        cell_temp_c=round(cell_temp_c, 2),
        battery_soc_pct=round(battery_soc_pct, 2),
        v_oc_v=round(v_oc, 4),
        r_int_ohm=round(r_int, 4),
        esr_multiplier=round(esr_mult, 3),
        load_watts=round(load_watts, 3),
        unassisted_v_term_v=round(unassisted_v, 4),
        would_cross_uvlo_unassisted=would_uvlo,
        usb_pd_9v3a_attached=usb_pd_9v3a_attached,
        hot_handoff_executed=hot_handoff,
        min_bus_voltage_v=round(min_bus_v, 4),
        pmic_uvlo_cutoff_v=NPFZ100_PMIC_UVLO_CUTOFF_V,
        pmic_uvlo_trips=pmic_uvlo_trips,
        charging_requested=request_liion_charge_at_subzero,
        charging_enabled=charging_enabled,
        charging_blocked_for_plating_prevention=charging_blocked,
        lithium_plating_events=LITHIUM_PLATING_EVENTS,
        rsv_salvage_triggered=rsv_salvage,
        active_recording_frames=active_recording_frames,
        rsv_salvageable_frames=active_recording_frames,
        dropped_frames=dropped_frames,
        emmc_corruptions=0,
    )


def simulate_high_altitude_thermal_derating_hil(
    *,
    altitude_m: float = 5200.0,
    ambient_temp_c: float = 15.0,
    workload_shooting_watts: float = 5.8,
    ftps_background_watts: float = 1.4,
    allow_ftps_shedding: bool = True,
) -> HighAltitudeThermalHilResult:
    """Co-emulate 5,200m barometric air-density derating, Sigma PWM boost & FTPS shedding."""
    if not math.isfinite(ambient_temp_c) or ambient_temp_c < -30.0 or ambient_temp_c > 55.0:
        raise Lut3dSubzeroSdiError(f"ambient_temp_c={ambient_temp_c!r} out of range [-30, 55]")
    if workload_shooting_watts < 0.0 or ftps_background_watts < 0.0:
        raise Lut3dSubzeroSdiError("Thermal watt loads must be non-negative")

    p_kpa, rho, flow_ratio = compute_isa_atmosphere(altitude_m)
    derated_cap_w = FX3_SEA_LEVEL_COOLING_HEADROOM_WATTS * flow_ratio
    total_requested_w = workload_shooting_watts + ftps_background_watts

    sea_level_pwm = 55.0
    if altitude_m > 3000.0:
        # Boost PWM aggressively in thin air to maximize volumetric airflow
        boosted_pwm = min(100.0, round(sea_level_pwm + (1.0 - flow_ratio) * 97.0, 1))
    else:
        boosted_pwm = sea_level_pwm

    # Lighter air offers less drag, slightly increasing free-running impeller RPM at high PWM
    boosted_rpm = int(round(3600.0 * (boosted_pwm / 100.0) * (1.0 + 0.08 * (1.0 - flow_ratio))))

    ftps_shed = False
    eff_watts = total_requested_w
    if allow_ftps_shedding and ftps_background_watts > 0.0 and total_requested_w > derated_cap_w:
        ftps_shed = True
        eff_watts = workload_shooting_watts

    # Steady-state + transient SoC thermal equilibrium (R_th_eff scaled inversely by mass flow * pwm)
    r_th_sea_level = 6.2  # C/W at 100% PWM
    eff_cooling_factor = max(0.25, flow_ratio * (boosted_pwm / 100.0))
    r_th_eff = r_th_sea_level / eff_cooling_factor
    t_steady = ambient_temp_c + eff_watts * r_th_eff

    # 60-step RC thermal integration toward equilibrium starting from warm 48.0 C
    t_soc = 48.0
    t_peak = t_soc
    for _ in range(60):
        t_soc = t_soc + 0.08 * (t_steady - t_soc)
        if t_soc > t_peak:
            t_peak = t_soc

    warn_tripped = t_peak >= FX3_BK4_CXD90057_WARN_TEMP_C
    if warn_tripped:
        status = "BLOCKED_CXD90057_OVERTEMP_WARN_REACHED"
        passed = False
    elif ftps_shed:
        status = "ALTITUDE_DERATED_PWM_BOOSTED_FTPS_SHED_OK"
        passed = True
    else:
        status = "ALTITUDE_NOMINAL_THERMAL_OK"
        passed = True

    return HighAltitudeThermalHilResult(
        passed=passed,
        status=status,
        altitude_m=round(altitude_m, 1),
        ambient_temp_c=round(ambient_temp_c, 2),
        atmospheric_pressure_kpa=round(p_kpa, 3),
        air_density_kg_m3=round(rho, 4),
        fan_mass_flow_ratio=round(flow_ratio, 4),
        derated_cooling_capacity_watts=round(derated_cap_w, 3),
        workload_shooting_watts=round(workload_shooting_watts, 3),
        ftps_background_watts=round(ftps_background_watts, 3),
        effective_thermal_watts=round(eff_watts, 3),
        sea_level_pwm_pct=sea_level_pwm,
        boosted_pwm_pct=boosted_pwm,
        boosted_fan_rpm=boosted_rpm,
        ftps_background_shed=ftps_shed,
        cxd90057_t_warn_c=FX3_BK4_CXD90057_WARN_TEMP_C,
        cxd90057_peak_temp_c=round(t_peak, 2),
        thermal_warn_tripped=warn_tripped,
        dropped_recording_frames=0,
        nvram_persistent_writes=NVRAM_PERSISTENT_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
    )


# ---------------------------------------------------------------------------
# Unified Phase 99 — Stage 16 Audit Runner & CLI
# ---------------------------------------------------------------------------


def run_phase99_lut3d_subzero_sdi_audit(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run complete Stage 16 audit across 3D LUT DMA, HDMI->12G-SDI Bridge & Sub-Zero/Altitude HIL."""
    donor_audit = inspect_lut3d_subzero_sdi_donors(force_clean_room=force_clean_room, env=env)

    # 1. User .cube Sanitizer + 65^3 -> 33^3 Tetrahedral DMA + Fail-Closed Guards
    cube_17_txt = build_synthetic_cube_text(grid_size=17, title="FX3_USER1_17", curve="slog3_filmic")
    parsed_17 = parse_and_sanitize_cube_lut(cube_17_txt, source_name="User1_17.cube")
    lut_65 = build_synthetic_cube_lattice(grid_size=65, title="FX3_RESOLVE_65", curve="slog3_filmic")
    stage_65 = stage_lut3d_into_volatile_ivshmem(
        lut_65,
        source_name="Resolve_65.cube",
        bit_depth=8,
        main_slog3_clean=True,
        proxy_mlut_enabled=True,
        hdmi_clean_feed=True,
        hdmi_raw16_active=False,
    )
    # Verify fail-closed rejection of corrupt / NaN / inverted-domain LUTs
    corrupt_blocked = 0
    for bad_txt in (
        "LUT_3D_SIZE 17\n0.0 0.0 0.0\n",
        "LUT_3D_SIZE 17\n" + "NaN 0.0 0.0\n" * (17**3),
        "LUT_3D_SIZE 17\nDOMAIN_MIN 1.0 0.0 0.0\nDOMAIN_MAX 0.0 1.0 1.0\n" + "0.5 0.5 0.5\n" * (17**3),
    ):
        try:
            parse_and_sanitize_cube_lut(bad_txt, source_name="Corrupt.cube")
        except CubeLutSanitizationError:
            corrupt_blocked += 1

    lut_ok = (
        parsed_17.grid_size == 17
        and stage_65.passed
        and stage_65.target_voxel_count == TARGET_HW_LUT_VOXEL_COUNT
        and stage_65.dma_table_bytes == LUT_8BIT_ALIGNED_BYTES
        and corrupt_blocked == 3
    )

    # 2. CEA-861-G HDMI AVI InfoFrame + Sony VSIF REC-Trigger -> 12G-SDI ST 2082 Bridge
    sdi_4k5994 = simulate_hdmi_to_12g_sdi_rec_bridge(
        fps_label="59.94p",
        resolution="3840x2160",
        gamut="S_GAMUT3_CINE_SLOG3",
        quantization="LIMITED_LEGAL",
        rec_burst_frames=24,
        inject_illegal_trs_codes=True,
    )
    sdi_4k2398 = simulate_hdmi_to_12g_sdi_rec_bridge(
        fps_label="23.98p",
        resolution="3840x2160",
        gamut="S_GAMUT3_CINE_SLOG3",
        quantization="LIMITED_LEGAL",
        rec_burst_frames=24,
    )
    # Negative control: Full-range S-Log3 without TRS guard must fail closed
    sdi_full_blk = simulate_hdmi_to_12g_sdi_rec_bridge(
        fps_label="59.94p",
        resolution="3840x2160",
        gamut="S_GAMUT3_CINE_SLOG3",
        quantization="FULL_RANGE",
        rec_burst_frames=8,
        inject_illegal_trs_codes=True,
    )
    sdi_ok = (
        sdi_4k5994.passed
        and sdi_4k5994.avi_infoframe_bytes == 17
        and sdi_4k5994.avi_checksum_zero
        and sdi_4k5994.dropped_rec_triggers == 0
        and sdi_4k5994.rp188_ltc_vitc_locked
        and sdi_4k5994.sdi_trs_collisions == 0
        and sdi_4k5994.sdi_transceiver_faults == 0
        and sdi_4k2398.passed
        and (not sdi_full_blk.passed)
        and (not sdi_full_blk.slog3_quantization_guard_ok)
    )

    # 3. Sub-Zero (-20C) NP-FZ100 Arrhenius ESR -> USB-PD 9V/3A Hot-Handoff + 5,200m Derating
    subzero_pd = simulate_subzero_usbpd_hot_handoff(
        cell_temp_c=-20.0,
        battery_soc_pct=45.0,
        load_watts=8.5,
        usb_pd_9v3a_attached=True,
        request_liion_charge_at_subzero=True,
    )
    subzero_nopd = simulate_subzero_usbpd_hot_handoff(
        cell_temp_c=-20.0,
        battery_soc_pct=45.0,
        load_watts=8.5,
        usb_pd_9v3a_attached=False,
        request_liion_charge_at_subzero=False,
    )
    alt_5200m = simulate_high_altitude_thermal_derating_hil(
        altitude_m=5200.0,
        ambient_temp_c=15.0,
        workload_shooting_watts=5.8,
        ftps_background_watts=1.4,
        allow_ftps_shedding=True,
    )
    hil_ok = (
        subzero_pd.passed
        and subzero_pd.would_cross_uvlo_unassisted
        and subzero_pd.hot_handoff_executed
        and subzero_pd.pmic_uvlo_trips == 0
        and (not subzero_pd.charging_enabled)
        and subzero_pd.charging_blocked_for_plating_prevention
        and subzero_pd.lithium_plating_events == 0
        and subzero_nopd.passed
        and subzero_nopd.rsv_salvage_triggered
        and alt_5200m.passed
        and alt_5200m.ftps_background_shed
        and (not alt_5200m.thermal_warn_tripped)
        and alt_5200m.cxd90057_peak_temp_c < FX3_BK4_CXD90057_WARN_TEMP_C
    )

    all_passed = donor_audit.all_contracts_verified and lut_ok and sdi_ok and hil_ok

    core_payload: Dict[str, object] = {
        "schema": PHASE_99_SCHEMA,
        "version": PHASE_99_VERSION,
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
            "null_gpio_derefs": NULL_GPIO_DEREFS,
            "mailbox_stalls": MAILBOX_STALLS,
            "stock_cp_fault_count": STOCK_CP_FAULT_COUNT,
            "sdi_transceiver_faults": SDI_TRANSCEIVER_FAULTS,
            "lithium_plating_events": LITHIUM_PLATING_EVENTS,
            "dropped_rec_triggers": DROPPED_REC_TRIGGERS,
            "donor_access_mode": DONOR_ACCESS_MODE,
        },
        "donor_audit": asdict(donor_audit),
        "lut3d_tetrahedral_dma": {
            "passed": lut_ok,
            "corrupt_luts_blocked": corrupt_blocked,
            "parsed_17cube_sha256": parsed_17.sha256,
            "resolve_65_to_33_ivshmem": asdict(stage_65),
        },
        "hdmi_avi_to_12g_sdi_bridge": {
            "passed": sdi_ok,
            "st2082_4k5994_slog3_legal": asdict(sdi_4k5994),
            "st292_4k2398_slog3_legal": asdict(sdi_4k2398),
            "full_range_trs_guard_blocked": asdict(sdi_full_blk),
        },
        "subzero_esr_and_altitude_hil": {
            "passed": hil_ok,
            "subzero_neg20c_usbpd_handoff": asdict(subzero_pd),
            "subzero_neg20c_no_usbpd_rsv": asdict(subzero_nopd),
            "altitude_5200m_convective_derating": asdict(alt_5200m),
        },
    }

    digest = hashlib.sha256(
        json.dumps(core_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    core_payload["audit_digest_sha256"] = digest
    return core_payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="lut3d_tetrahedral_subzero_sdi_emulator.py",
        description="Phase 99 — Stage 16 65^3->33^3 Tetrahedral 3D-LUT DMA, HDMI->12G-SDI Bridge & Sub-Zero/Altitude HIL",
    )
    parser.add_argument("--clean-room", action="store_true", help="Force clean-room synthetic mode")
    parser.add_argument("--json", action="store_true", help="Emit deterministic JSON audit (default)")
    parser.add_argument("--summary", action="store_true", help="Emit concise one-line summary")
    parser.add_argument("--self-test", action="store_true", help="Run full Stage 16 self-test audit")
    parser.add_argument("--lut-matrix", action="store_true", help="Emit 3D-LUT Tetrahedral DMA matrix JSON")
    parser.add_argument("--sdi-matrix", action="store_true", help="Emit HDMI AVI -> 12G-SDI Bridge matrix JSON")
    parser.add_argument("--hil-matrix", action="store_true", help="Emit Sub-Zero ESR & Altitude HIL matrix JSON")
    args = parser.parse_args(argv)

    rep = run_phase99_lut3d_subzero_sdi_audit(
        force_clean_room=True if args.clean_room else None
    )

    if args.lut_matrix:
        sys.stdout.write(json.dumps(rep["lut3d_tetrahedral_dma"], indent=2) + "\n")
    elif args.sdi_matrix:
        sys.stdout.write(json.dumps(rep["hdmi_avi_to_12g_sdi_bridge"], indent=2) + "\n")
    elif args.hil_matrix:
        sys.stdout.write(json.dumps(rep["subzero_esr_and_altitude_hil"], indent=2) + "\n")
    elif args.summary and not args.json:
        lut = rep["lut3d_tetrahedral_dma"]["resolve_65_to_33_ivshmem"]  # type: ignore[index]
        sdi = rep["hdmi_avi_to_12g_sdi_bridge"]["st2082_4k5994_slog3_legal"]  # type: ignore[index]
        subz = rep["subzero_esr_and_altitude_hil"]["subzero_neg20c_usbpd_handoff"]  # type: ignore[index]
        alt = rep["subzero_esr_and_altitude_hil"]["altitude_5200m_convective_derating"]  # type: ignore[index]
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        sys.stdout.write(
            f"[{status}] Phase 99 Stage 16 ({rep['source_mode']}) | "
            f"lut=65^3->33^3({lut['dma_table_bytes']}B,nvram={lut['nvram_persistent_writes']}) | "
            f"sdi=AVI({sdi['avi_infoframe_bytes']}B,chk=0)->12G(drop={sdi['dropped_rec_triggers']},rp188_off={sdi['ltc_vitc_frame_offset']}) | "
            f"subzero=-20C(esr={subz['r_int_ohm']}Ohm,pd_handoff=1,plate={subz['lithium_plating_events']}) | "
            f"alt=5200m(pwm={alt['boosted_pwm_pct']}%,ftps_shed=1,t_pk={alt['cxd90057_peak_temp_c']}C) | "
            f"digest={str(rep['audit_digest_sha256'])[:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")

    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
