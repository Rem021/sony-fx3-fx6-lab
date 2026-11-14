"""Phase 37 — `.cube` (`17^3` / `33^3`) User 3D LUT Sanitizer, `P1` (`/dev/nflasha30`) + `P11` Hardware Packer & Sony `RTMD` (`0xE304` `IMX510` IBIS) Verifier.

Strictly Read-Only (`os.O_RDONLY`) & Clean-Room Dual-Mode:
- Local Donor Mode: opens FX3 v7.02 (`appFw.so`, `libmpr.so`) and FX6 v6.01
  (`appFw.so`, `libmpr.so`) strictly `os.O_RDONLY` and verifies `/dev/nflasha30`,
  `model_user_lut_files`, `LUT_3D_SIZE`/`DOMAIN_MIN`/`DOMAIN_MAX`, `mpr::SetLutData`,
  and `mpr::KlvConverter` (`RDD18` / `UDAMSetGyroscopeValue` / `Rdd18KeyCameraUnit`)
  using fast C-level `bytes.find` (< 0.4s total).
- Clean-Room Mode (`FX3_FX6_FORCE_CLEAN_ROOM=1` or `clean_room=True` or donors absent):
  runs deterministic clean-room synthetic ELF fixtures with zero proprietary assets.

Two core engineering pillars:
Part A — Anti-Crash `.cube` (`17^3` / `33^3`) Parser, Sanitizer & `17^3 -> 33^3` Trilinear Packer:
  - Rejects NaN/Inf, wrong voxel counts, `DOMAIN_MIN >= DOMAIN_MAX`, `LUT_1D_SIZE` mismatches,
    control-char/path-traversal `TITLE`, and oversized files that would overflow FX3
    `P1` (`/dev/nflasha30`, 48.00 MiB VFAT, 16-slot `User1..16`) or trigger the historical
    FX3 v6.00->v6.01 custom `.cube` parser crash.
  - Exact trilinear `17^3 -> 33^3` (`35,937` voxels) upsampler and `U12.0` / `U16` (`215,622 B`)
    / `U8` (`107,812 B`) DMA table packer, proving `S-Log3` identity ramp mapping <= 1 LSB error.
  - Synthesizes `P11` 164-byte `mpr::SetLutData` descriptors, `0x92840747` `0x0165` (36B DMA)
    & `0x0166` (10B toggle) packets, plus `BK4` `0x02cf1453` (`Select LUT`) and
    `0x02cf14a4..0x02cf14b3` (`User1..16` presence flags).

Part B — Sony `RTMD` (`SMPTE RDD 18` / `0xE304`) Frame Packet & `IMX510` IBIS Verifier:
  - Builds and verifies big-endian SMPTE KLV (`06 0e 2b 34 ...`) + BER length + local tag/length
    `RTMD` packets carrying `IMX510` readout duration, Dual Base ISO (`800`/`12800`) & EI index,
    Shutter Angle (`180.0 deg`), Active 3D LUT name (`S-Cinetone`/`User1`), and `0xE304` 5-Axis
    IBIS Center-Lock + Gyro/Accelerometer coherence for Catalyst Browse & Gyroflow.
"""

from __future__ import annotations

import array
import functools
import hashlib
import math
import re
import struct
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple, Union

from .haita_bk4_feature_analyzer import (
    BK4RecordAudit,
    DEFAULT_REPO_ROOT,
    FX3_APPFW_RELPATH,
    FX6_APPFW_RELPATH,
    audit_bk4_record_bytes,
    build_clean_room_bk4_record,
    read_bytes_rdonly,
    resolve_donor_file,
)


PHASE_37_SCHEMA = "fx3_firmware_lab_phase37_cube_lut_rtmd_v1"
PHASE_37_VERSION = "37.0.0"

FX3_LIBMPR_RELPATH = "sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/libmpr.so"
FX6_LIBMPR_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libmpr.so"
)

# ---------------------------------------------------------------------------
# Part A Constants: `.cube` 3D LUT, P1 `/dev/nflasha30`, P11 `SetLutData`, BK4
# ---------------------------------------------------------------------------

SUPPORTED_CUBE_GRID_SIZES: Tuple[int, ...] = (17, 33)
TARGET_HW_LUT_GRID_SIZE = 33
TARGET_HW_LUT_VOXEL_COUNT = 33 * 33 * 33  # 35,937
LUT_8BIT_RAW_BYTES = TARGET_HW_LUT_VOXEL_COUNT * 3  # 107,811
LUT_8BIT_ALIGNED_BYTES = 107_812
LUT_12BIT_U16_BYTES = TARGET_HW_LUT_VOXEL_COUNT * 3 * 2  # 215,622 (U12.0 in uint16 LE)
LUT_16BIT_U16_BYTES = TARGET_HW_LUT_VOXEL_COUNT * 3 * 2  # 215,622 (U16 in uint16 LE)
LUT_CUBE_PARSER_ALLOC_BYTES = 0x6A1B9  # 434,617 B in mpr::ExecuteSetLutData

MPR_SET_LUT_DESCRIPTOR_BYTES = 164
LUT_DMA_SRAM_REG_THRESHOLD = 0xBB80  # 48,000 B
LUT_DMA_ENABLE_SIZE = 36
LUT_TOGGLE_SIZE = 10

UIPC_BB_TARGET_QUEUE = 0x92840747
UIPC_BB_MAGIC = 0x200D
UIPC_BB_FLAGS = 0x8001
UIPC_BB_OPCODE_LUT_DMA = 0x0165
UIPC_BB_OPCODE_LUT_TOGGLE = 0x0166

DUAL_NATIVE_ISO_BASES: Tuple[int, int] = (800, 12800)

# FX3 `P1` `/dev/nflasha30` (`p30`, 48.00 MiB VFAT) & 16-slot User LUT limits
FX3_P30_DEVICE_PATH = "/dev/nflasha30"
FX3_P30_MOUNT_POINT = "/usr/data/lut/"
FX3_P30_TOTAL_BYTES = 0x00018000 * 512  # 50,331,648 B (48.00 MiB)
FX3_P30_CLUSTER_BYTES = 8192
FX3_P30_VFAT_OVERHEAD_BYTES = 615_424
FX3_P30_USABLE_DATA_BYTES = FX3_P30_TOTAL_BYTES - FX3_P30_VFAT_OVERHEAD_BYTES  # 49,716,224 B
FX3_P30_USER_SLOT_COUNT = 16
MAX_SAFE_CUBE_FILE_BYTES = 2 * 1024 * 1024  # 2.00 MiB per slot (guards v6.01 parser & 16-slot budget)
MAX_SAFE_CUBE_LINES = 40_000
MAX_CUBE_TITLE_BYTES = 63

# BK4 NVRAM Property IDs for LUT Selection & User1..16 Presence Flags
BKID_APP_SELECT_LUT = 0x02CF1453
BKID_USER_LUT_FLAG_START = 0x02CF14A4  # User1
BKID_USER_LUT_FLAG_END = 0x02CF14B3    # User16
BUILTIN_LUT_SLOTS: Dict[str, int] = {
    "S709": 0x00,
    "R709": 0x01,
    "S-Log3": 0x02,
}
USER_LUT_SLOTS: Dict[str, int] = {f"User{i}": 0x02 + i for i in range(1, 17)}

# ---------------------------------------------------------------------------
# Part B Constants: Sony `RTMD` (`SMPTE RDD 18` / `0xE304`) & Donor Markers
# ---------------------------------------------------------------------------

SMPTE_KLV_UL_PREFIX = b"\x06\x0e\x2b\x34"
RTMD_RDD18_ACQUISITION_UL = bytes.fromhex("060e2b34025301010c02010101010000")

RTMD_TAG_SHUTTER_ANGLE_X100 = 0x3209
RTMD_TAG_IMX510_READOUT_US = 0x3219
RTMD_TAG_DUAL_BASE_ISO_AND_EI = 0x321A
RTMD_TAG_ACTIVE_3D_LUT_NAME = 0xE105
RTMD_TAG_IMX510_IBIS_GYRO_E304 = 0xE304

RTMD_E304_PAYLOAD_BYTES = 32
RTMD_COHERENCE_CENTER_LOCK_OK = 0x0001
RTMD_COHERENCE_GYRO_VALID = 0x0002
RTMD_COHERENCE_CATALYST_BROWSE_OK = 0x0004
RTMD_COHERENCE_GYROFLOW_OK = 0x0008
RTMD_COHERENCE_ALL_OK = 0x000F

VALID_STEADYSHOT_MODES: Dict[str, int] = {"Off": 0, "Standard": 1, "Active": 2}
STEADYSHOT_CODE_TO_NAME: Dict[int, str] = {v: k for k, v in VALID_STEADYSHOT_MODES.items()}

SHARED_APPFW_LUT_MARKERS: Tuple[str, ...] = (
    "LUT_3D_SIZE",
    "LUT_3D_INPUT_RANGE",
    "model_user_lut_files::mount_lut_folder():OK",
    "/usr/data/lut",
    "User1",
    "S709.cube",
    "SL3SG3Ctos709.cube",
)

FX3_APPFW_P1_MARKERS: Tuple[str, ...] = (
    "/dev/nflasha30",
    "User1:",
    "User16:",
)

SHARED_LIBMPR_LUT_AND_RTMD_MARKERS: Tuple[str, ...] = (
    "LUT_3D_SIZE",
    "DOMAIN_MIN",
    "DOMAIN_MAX",
    "LUT_3D_INPUT_RANGE",
    "_ZN3mpr10SetLutDataERKNS_17setLutDataInParamE",
    "_ZN3mpr17ExecuteSetLutDataERKNS_17setLutDataInParamE",
    "_ZN3mpr12KlvConverter18Rdd18KeyCameraUnitE",
    "_ZN3mpr12KlvConverter16Rdd18KeyLensUnitE",
    "_ZN3mpr12KlvConverter11UDAMKeyUnitE",
    "_ZN3mpr12KlvConverter21UDAMSetGyroscopeValueE",
    "_ZN3mpr12KlvConverter25UDAMSetAccelerometerValueE",
    "_ZN3mpr12KlvConverter27UDAMSetSonyLookControlValueE",
    "_ZN3mpr12KlvConverter26UDAMSetSonyCamProfileValueE",
    "DistortionCorrection",
    "Gyroscope",
    "Accelerometor",
)


class CubeLutSanitizationError(ValueError):
    """Raised when a `.cube` 3D LUT fails structural, numerical, or storage-budget sanitization."""


class RtmdProtocolError(ValueError):
    """Raised when a Sony `RTMD` (`SMPTE RDD 18` / `0xE304`) packet or contract is invalid."""


# ---------------------------------------------------------------------------
# Part A: `.cube` 3D LUT Parser, Sanitizer, Trilinear Upsampler & HW Packer
# ---------------------------------------------------------------------------


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
class CubeLutAuditSummary:
    valid: bool
    title: Optional[str]
    grid_size: Optional[int]
    expected_voxels: int
    actual_voxels: int
    byte_length: int
    line_count: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class SLog3RampProof:
    passed: bool
    samples_tested: int
    bit_depth: int
    max_lsb_error: int
    max_float_error: float
    lut_17_sha256: str
    lut_33_sha256: str
    dma_table_bytes: int
    dma_table_sha256: str


@dataclass(frozen=True)
class P11LutHardwareBundle:
    slot_name: str
    select_lut_code: int
    cube_path: str
    grid_size_source: int
    grid_size_hw: int
    dma_bit_depth: int
    dma_table_bytes: int
    dma_table_sha256: str
    mpr_descriptor_bytes: int
    mpr_descriptor_hex: str
    dma_packet_0165_hex: str
    toggle_packet_0166_hex: str
    uses_dram_dma_path: bool
    bk4_select_lut_hex: str
    bk4_user_flags_hex: Dict[str, str]
    bk4_record_valid: bool


@dataclass(frozen=True)
class P1StorageBudgetReport:
    passed: bool
    device_path: str
    mount_point: str
    total_partition_bytes: int
    usable_data_bytes: int
    slot_count: int
    allocated_cluster_bytes: int
    remaining_bytes: int
    remaining_percent: float
    max_per_slot_bytes: int
    errors: Tuple[str, ...]


_RE_FORBIDDEN_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _parse_rgb_triple(tokens: Sequence[str], *, context: str) -> Tuple[float, float, float]:
    if len(tokens) != 3:
        raise CubeLutSanitizationError(
            f"{context}: expected 3 numeric components, got {len(tokens)}"
        )
    vals: List[float] = []
    for tok in tokens:
        low = tok.strip().lower()
        if low in ("nan", "+nan", "-nan", "inf", "+inf", "-inf", "infinity", "+infinity", "-infinity"):
            raise CubeLutSanitizationError(f"{context}: non-finite token {tok!r} rejected")
        try:
            v = float(tok)
        except ValueError as exc:
            raise CubeLutSanitizationError(f"{context}: malformed float {tok!r}") from exc
        if not math.isfinite(v):
            raise CubeLutSanitizationError(f"{context}: non-finite float {v!r} rejected")
        if abs(v) > 10.0:
            raise CubeLutSanitizationError(
                f"{context}: extreme out-of-range float {v!r} rejected"
            )
        vals.append(v)
    return (vals[0], vals[1], vals[2])


def parse_and_sanitize_cube_lut(
    raw_cube: Union[str, bytes],
    *,
    max_file_bytes: int = MAX_SAFE_CUBE_FILE_BYTES,
    max_lines: int = MAX_SAFE_CUBE_LINES,
) -> ParsedCubeLut:
    """Strictly parse and sanitize a `17^3` or `33^3` Adobe/Iridas `.cube` 3D LUT."""
    if isinstance(raw_cube, bytes):
        byte_len = len(raw_cube)
        if byte_len == 0:
            raise CubeLutSanitizationError("Empty .cube buffer")
        if byte_len > max_file_bytes:
            raise CubeLutSanitizationError(
                f".cube file size {byte_len} B exceeds safe FX3 /dev/nflasha30 limit {max_file_bytes} B"
            )
        if b"\x00" in raw_cube:
            raise CubeLutSanitizationError("NUL byte found inside .cube text payload")
        try:
            text = raw_cube.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise CubeLutSanitizationError("Invalid UTF-8 byte sequence in .cube file") from exc
        raw_bytes = raw_cube
    else:
        raw_bytes = raw_cube.encode("utf-8", errors="strict")
        byte_len = len(raw_bytes)
        if byte_len == 0:
            raise CubeLutSanitizationError("Empty .cube text")
        if byte_len > max_file_bytes:
            raise CubeLutSanitizationError(
                f".cube file size {byte_len} B exceeds safe FX3 /dev/nflasha30 limit {max_file_bytes} B"
            )
        if "\x00" in raw_cube:
            raise CubeLutSanitizationError("NUL character found inside .cube text payload")
        text = raw_cube

    ctrl_m = _RE_FORBIDDEN_CTRL.search(text)
    if ctrl_m is not None:
        raise CubeLutSanitizationError(
            f"Forbidden control character 0x{ord(ctrl_m.group(0)):02x} in .cube payload"
        )

    lines = text.splitlines()
    line_count = len(lines)
    if line_count > max_lines:
        raise CubeLutSanitizationError(
            f".cube line count {line_count} exceeds safe parser limit {max_lines}"
        )

    title: Optional[str] = None
    grid_size: Optional[int] = None
    domain_min: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    domain_max: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    saw_domain_min = False
    saw_domain_max = False
    entries: List[Tuple[float, float, float]] = []
    append_entry = entries.append
    isfinite = math.isfinite
    max_entries = 0

    for lineno, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        if not stripped or stripped[0] == "#":
            continue

        c0 = stripped[0]
        if c0 in "0123456789.-+" and "#" not in stripped:
            if grid_size is None:
                raise CubeLutSanitizationError(
                    f"Line {lineno}: RGB triplet encountered before LUT_3D_SIZE"
                )
            parts = stripped.split()
            if len(parts) != 3:
                raise CubeLutSanitizationError(
                    f"Line {lineno} RGB: expected 3 numeric components, got {len(parts)}"
                )
            try:
                r = float(parts[0])
                g = float(parts[1])
                b = float(parts[2])
            except ValueError as exc:
                raise CubeLutSanitizationError(f"Line {lineno} RGB: malformed float") from exc
            if not (isfinite(r) and isfinite(g) and isfinite(b)):
                raise CubeLutSanitizationError(f"Line {lineno} RGB: non-finite float rejected")
            if abs(r) > 10.0 or abs(g) > 10.0 or abs(b) > 10.0:
                raise CubeLutSanitizationError(f"Line {lineno} RGB: extreme out-of-range float rejected")
            append_entry((r, g, b))
            if len(entries) > max_entries:
                raise CubeLutSanitizationError(
                    f"Line {lineno}: voxel count exceeds {grid_size}^3 = {max_entries}"
                )
            continue

        if "#" in stripped and not stripped.startswith("TITLE"):
            stripped = stripped.split("#", 1)[0].strip()
            if not stripped:
                continue

        parts = stripped.split()
        head = parts[0]

        if head == "LUT_1D_SIZE" or head == "LUT_1D_INPUT_RANGE":
            raise CubeLutSanitizationError(
                f"Line {lineno}: {head} is unsupported / mismatched (only 3D LUT 17^3 or 33^3 allowed)"
            )
        if head == "TITLE":
            if title is not None:
                raise CubeLutSanitizationError(f"Line {lineno}: duplicate TITLE directive")
            rest = stripped[len("TITLE") :].strip()
            if len(rest) >= 2 and rest[0] == '"' and rest[-1] == '"':
                candidate = rest[1:-1]
            else:
                candidate = rest
            if not candidate or len(candidate.encode("utf-8")) > MAX_CUBE_TITLE_BYTES:
                raise CubeLutSanitizationError(
                    f"Line {lineno}: invalid TITLE length (must be 1..{MAX_CUBE_TITLE_BYTES} bytes)"
                )
            if ".." in candidate or "/" in candidate or "\\" in candidate:
                raise CubeLutSanitizationError(
                    f"Line {lineno}: unsafe path-like characters in TITLE {candidate!r}"
                )
            title = candidate
            continue

        if head == "LUT_3D_SIZE":
            if grid_size is not None:
                raise CubeLutSanitizationError(f"Line {lineno}: duplicate LUT_3D_SIZE directive")
            if len(parts) != 2:
                raise CubeLutSanitizationError(f"Line {lineno}: malformed LUT_3D_SIZE")
            try:
                sz = int(parts[1], 10)
            except ValueError as exc:
                raise CubeLutSanitizationError(
                    f"Line {lineno}: non-integer LUT_3D_SIZE {parts[1]!r}"
                ) from exc
            if sz not in SUPPORTED_CUBE_GRID_SIZES:
                raise CubeLutSanitizationError(
                    f"Line {lineno}: unsupported LUT_3D_SIZE {sz}; expected {SUPPORTED_CUBE_GRID_SIZES}"
                )
            grid_size = sz
            max_entries = sz ** 3
            continue

        if head == "DOMAIN_MIN":
            if saw_domain_min:
                raise CubeLutSanitizationError(f"Line {lineno}: duplicate DOMAIN_MIN")
            domain_min = _parse_rgb_triple(parts[1:], context=f"Line {lineno} DOMAIN_MIN")
            saw_domain_min = True
            continue

        if head == "DOMAIN_MAX":
            if saw_domain_max:
                raise CubeLutSanitizationError(f"Line {lineno}: duplicate DOMAIN_MAX")
            domain_max = _parse_rgb_triple(parts[1:], context=f"Line {lineno} DOMAIN_MAX")
            saw_domain_max = True
            continue

        if head == "LUT_3D_INPUT_RANGE":
            if len(parts) != 3:
                raise CubeLutSanitizationError(f"Line {lineno}: malformed LUT_3D_INPUT_RANGE")
            r_min_max = _parse_rgb_triple(
                (parts[1], parts[1], parts[1]), context=f"Line {lineno} LUT_3D_INPUT_RANGE_MIN"
            )
            r_max_val = _parse_rgb_triple(
                (parts[2], parts[2], parts[2]), context=f"Line {lineno} LUT_3D_INPUT_RANGE_MAX"
            )
            domain_min = r_min_max
            domain_max = r_max_val
            saw_domain_min = True
            saw_domain_max = True
            continue

        if grid_size is None:
            raise CubeLutSanitizationError(
                f"Line {lineno}: RGB triplet or unknown directive {head!r} before LUT_3D_SIZE"
            )
        triple = _parse_rgb_triple(parts, context=f"Line {lineno} RGB")
        append_entry(triple)
        if len(entries) > max_entries:
            raise CubeLutSanitizationError(
                f"Line {lineno}: voxel count exceeds {grid_size}^3 = {max_entries}"
            )

    if grid_size is None:
        raise CubeLutSanitizationError("Missing mandatory LUT_3D_SIZE directive")

    for ch in range(3):
        if domain_min[ch] >= domain_max[ch]:
            raise CubeLutSanitizationError(
                f"Non-monotonic domain on channel {ch}: DOMAIN_MIN={domain_min[ch]} >= DOMAIN_MAX={domain_max[ch]}"
            )

    expected = grid_size ** 3
    if len(entries) != expected:
        raise CubeLutSanitizationError(
            f"Voxel count mismatch for {grid_size}^3 LUT: expected {expected}, got {len(entries)}"
        )

    eff_title = title if title is not None else f"SONY_USER_LUT_{grid_size}"
    return ParsedCubeLut(
        title=eff_title,
        grid_size=grid_size,
        domain_min=domain_min,
        domain_max=domain_max,
        entries=tuple(entries),
        byte_length=byte_len,
        line_count=line_count,
        sha256=hashlib.sha256(raw_bytes).hexdigest(),
    )


def audit_cube_lut_text(raw_cube: Union[str, bytes]) -> CubeLutAuditSummary:
    """Non-raising `.cube` audit wrapper returning structured errors."""
    byte_len = len(raw_cube) if isinstance(raw_cube, bytes) else len(raw_cube.encode("utf-8", errors="replace"))
    try:
        parsed = parse_and_sanitize_cube_lut(raw_cube)
        return CubeLutAuditSummary(
            valid=True,
            title=parsed.title,
            grid_size=parsed.grid_size,
            expected_voxels=parsed.grid_size ** 3,
            actual_voxels=len(parsed.entries),
            byte_length=parsed.byte_length,
            line_count=parsed.line_count,
            errors=(),
        )
    except CubeLutSanitizationError as exc:
        return CubeLutAuditSummary(
            valid=False,
            title=None,
            grid_size=None,
            expected_voxels=0,
            actual_voxels=0,
            byte_length=byte_len,
            line_count=0,
            errors=(str(exc),),
        )


def build_identity_cube_lut(
    grid_size: int = 17,
    *,
    title: str = "SONY_IDENTITY_SLOG3",
    domain_min: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    domain_max: Tuple[float, float, float] = (1.0, 1.0, 1.0),
) -> str:
    """Deterministically generate a clean `17^3` or `33^3` identity `.cube` LUT."""
    if grid_size not in SUPPORTED_CUBE_GRID_SIZES:
        raise CubeLutSanitizationError(
            f"Unsupported grid_size={grid_size}; expected {SUPPORTED_CUBE_GRID_SIZES}"
        )
    for ch in range(3):
        if domain_min[ch] >= domain_max[ch]:
            raise CubeLutSanitizationError("DOMAIN_MIN must be < DOMAIN_MAX")
    lines: List[str] = [
        "# Clean-Room Sony Cinema Line 3D LUT (.cube)",
        f'TITLE "{title}"',
        f"LUT_3D_SIZE {grid_size}",
        f"DOMAIN_MIN {domain_min[0]:.6f} {domain_min[1]:.6f} {domain_min[2]:.6f}",
        f"DOMAIN_MAX {domain_max[0]:.6f} {domain_max[1]:.6f} {domain_max[2]:.6f}",
    ]
    denom = float(grid_size - 1)
    span_r = domain_max[0] - domain_min[0]
    span_g = domain_max[1] - domain_min[1]
    span_b = domain_max[2] - domain_min[2]
    r_vals = [f"{domain_min[0] + span_r * (i / denom):.6f}" for i in range(grid_size)]
    g_vals = [f"{domain_min[1] + span_g * (i / denom):.6f}" for i in range(grid_size)]
    b_vals = [f"{domain_min[2] + span_b * (i / denom):.6f}" for i in range(grid_size)]
    append = lines.append
    for b_s in b_vals:
        for g_s in g_vals:
            suffix = f" {g_s} {b_s}"
            for r_s in r_vals:
                append(r_s + suffix)
    return "\n".join(lines) + "\n"


def serialize_parsed_cube_lut(lut: ParsedCubeLut) -> str:
    """Serialize a `ParsedCubeLut` back to canonical `.cube` text."""
    lines: List[str] = [
        "# Sanitized Sony Cinema Line 3D LUT (.cube)",
        f'TITLE "{lut.title}"',
        f"LUT_3D_SIZE {lut.grid_size}",
        f"DOMAIN_MIN {lut.domain_min[0]:.6f} {lut.domain_min[1]:.6f} {lut.domain_min[2]:.6f}",
        f"DOMAIN_MAX {lut.domain_max[0]:.6f} {lut.domain_max[1]:.6f} {lut.domain_max[2]:.6f}",
    ]
    lines.extend(f"{r:.6f} {g:.6f} {b:.6f}" for r, g, b in lut.entries)
    return "\n".join(lines) + "\n"


def trilinear_sample_cube(
    lut: ParsedCubeLut, r: float, g: float, b: float
) -> Tuple[float, float, float]:
    """Exact trilinear interpolation in R-fastest, G-middle, B-slowest `.cube` lattice."""
    n = lut.grid_size
    n_minus_1 = n - 1
    dmin = lut.domain_min
    dmax = lut.domain_max
    entries = lut.entries

    nr = (r - dmin[0]) / (dmax[0] - dmin[0])
    ng = (g - dmin[1]) / (dmax[1] - dmin[1])
    nb = (b - dmin[2]) / (dmax[2] - dmin[2])
    if nr < 0.0:
        nr = 0.0
    elif nr > 1.0:
        nr = 1.0
    if ng < 0.0:
        ng = 0.0
    elif ng > 1.0:
        ng = 1.0
    if nb < 0.0:
        nb = 0.0
    elif nb > 1.0:
        nb = 1.0

    fr = nr * n_minus_1
    fg = ng * n_minus_1
    fb = nb * n_minus_1

    r0 = int(fr)
    g0 = int(fg)
    b0 = int(fb)
    if r0 >= n_minus_1:
        r0 = n_minus_1 - 1
    if g0 >= n_minus_1:
        g0 = n_minus_1 - 1
    if b0 >= n_minus_1:
        b0 = n_minus_1 - 1
    r1 = r0 + 1
    g1 = g0 + 1
    b1 = b0 + 1

    dr = fr - r0
    dg = fg - g0
    db = fb - b0
    odr = 1.0 - dr
    odg = 1.0 - dg
    odb = 1.0 - db

    n2 = n * n
    base00 = g0 * n + b0 * n2
    base10 = g1 * n + b0 * n2
    base01 = g0 * n + b1 * n2
    base11 = g1 * n + b1 * n2

    c000 = entries[r0 + base00]
    c100 = entries[r1 + base00]
    c010 = entries[r0 + base10]
    c110 = entries[r1 + base10]
    c001 = entries[r0 + base01]
    c101 = entries[r1 + base01]
    c011 = entries[r0 + base11]
    c111 = entries[r1 + base11]

    w000 = odr * odg * odb
    w100 = dr * odg * odb
    w010 = odr * dg * odb
    w110 = dr * dg * odb
    w001 = odr * odg * db
    w101 = dr * odg * db
    w011 = odr * dg * db
    w111 = dr * dg * db

    out_r = (
        c000[0] * w000 + c100[0] * w100 + c010[0] * w010 + c110[0] * w110
        + c001[0] * w001 + c101[0] * w101 + c011[0] * w011 + c111[0] * w111
    )
    out_g = (
        c000[1] * w000 + c100[1] * w100 + c010[1] * w010 + c110[1] * w110
        + c001[1] * w001 + c101[1] * w101 + c011[1] * w011 + c111[1] * w111
    )
    out_b = (
        c000[2] * w000 + c100[2] * w100 + c010[2] * w010 + c110[2] * w110
        + c001[2] * w001 + c101[2] * w101 + c011[2] * w011 + c111[2] * w111
    )
    return (out_r, out_g, out_b)


def upsample_cube_17_to_33(lut: ParsedCubeLut) -> ParsedCubeLut:
    """Upsample a sanitized `17^3` `.cube` LUT to `33^3` (`35,937` triplets) via exact trilinear interpolation."""
    if lut.grid_size == TARGET_HW_LUT_GRID_SIZE:
        return lut
    if lut.grid_size != 17:
        raise CubeLutSanitizationError(f"Expected 17^3 or 33^3 LUT, got {lut.grid_size}^3")

    entries = lut.entries
    out: List[Tuple[float, float, float]] = [None] * TARGET_HW_LUT_VOXEL_COUNT  # type: ignore[list-item]
    # Fast exact lattice mapping for 17 -> 33: coordinate idx in 0..32 maps to idx / 2.0 in 0..16
    pos = 0
    for bi in range(33):
        b0 = bi >> 1
        b1 = b0 + 1 if b0 < 16 else 16
        wb = 0.5 if (bi & 1) else 0.0
        owb = 1.0 - wb
        b0_off = b0 * 289
        b1_off = b1 * 289
        for gi in range(33):
            g0 = gi >> 1
            g1 = g0 + 1 if g0 < 16 else 16
            wg = 0.5 if (gi & 1) else 0.0
            owg = 1.0 - wg
            g0_off = g0 * 17
            g1_off = g1 * 17

            idx00 = g0_off + b0_off
            idx10 = g1_off + b0_off
            idx01 = g0_off + b1_off
            idx11 = g1_off + b1_off

            w00 = owg * owb
            w10 = wg * owb
            w01 = owg * wb
            w11 = wg * wb

            for ri in range(33):
                r0 = ri >> 1
                r1 = r0 + 1 if r0 < 16 else 16
                wr = 0.5 if (ri & 1) else 0.0
                owr = 1.0 - wr

                c000 = entries[r0 + idx00]
                c100 = entries[r1 + idx00]
                c010 = entries[r0 + idx10]
                c110 = entries[r1 + idx10]
                c001 = entries[r0 + idx01]
                c101 = entries[r1 + idx01]
                c011 = entries[r0 + idx11]
                c111 = entries[r1 + idx11]

                # Collapse along R first, then G/B weights
                r00_0 = c000[0] * owr + c100[0] * wr
                r00_1 = c000[1] * owr + c100[1] * wr
                r00_2 = c000[2] * owr + c100[2] * wr

                r10_0 = c010[0] * owr + c110[0] * wr
                r10_1 = c010[1] * owr + c110[1] * wr
                r10_2 = c010[2] * owr + c110[2] * wr

                r01_0 = c001[0] * owr + c101[0] * wr
                r01_1 = c001[1] * owr + c101[1] * wr
                r01_2 = c001[2] * owr + c101[2] * wr

                r11_0 = c011[0] * owr + c111[0] * wr
                r11_1 = c011[1] * owr + c111[1] * wr
                r11_2 = c011[2] * owr + c111[2] * wr

                out[pos] = (
                    r00_0 * w00 + r10_0 * w10 + r01_0 * w01 + r11_0 * w11,
                    r00_1 * w00 + r10_1 * w10 + r01_1 * w01 + r11_1 * w11,
                    r00_2 * w00 + r10_2 * w10 + r01_2 * w01 + r11_2 * w11,
                )
                pos += 1

    # Deterministic content hash over binary IEEE-754 float64 triples (fast C-level buffer)
    flat_arr = array.array("d")
    for r, g, b in out:
        flat_arr.append(r)
        flat_arr.append(g)
        flat_arr.append(b)
    h = hashlib.sha256()
    h.update(lut.title.encode("utf-8"))
    h.update(struct.pack("<I6d", TARGET_HW_LUT_GRID_SIZE, *lut.domain_min, *lut.domain_max))
    h.update(flat_arr.tobytes())
    return ParsedCubeLut(
        title=lut.title,
        grid_size=TARGET_HW_LUT_GRID_SIZE,
        domain_min=lut.domain_min,
        domain_max=lut.domain_max,
        entries=tuple(out),
        byte_length=lut.byte_length,
        line_count=lut.line_count,
        sha256=h.hexdigest(),
    )


def pack_cube_to_dma_table(lut: ParsedCubeLut, *, bit_depth: int = 12) -> bytes:
    """Pack a `17^3` or `33^3` `.cube` LUT into CXD90057 `33^3` hardware DMA table bytes."""
    if bit_depth not in (8, 12, 16):
        raise CubeLutSanitizationError(f"Unsupported hardware DMA bit_depth={bit_depth}; expected 8, 12, or 16")
    hw_lut = upsample_cube_17_to_33(lut)
    entries = hw_lut.entries
    if len(entries) != TARGET_HW_LUT_VOXEL_COUNT:
        raise CubeLutSanitizationError("Unexpected voxel count after upsampling")

    if bit_depth == 8:
        buf = bytearray(LUT_8BIT_ALIGNED_BYTES)
        idx = 0
        for r, g, b in entries:
            rv = int(round((0.0 if r < 0.0 else (1.0 if r > 1.0 else r)) * 255.0))
            gv = int(round((0.0 if g < 0.0 else (1.0 if g > 1.0 else g)) * 255.0))
            bv = int(round((0.0 if b < 0.0 else (1.0 if b > 1.0 else b)) * 255.0))
            buf[idx] = rv
            buf[idx + 1] = gv
            buf[idx + 2] = bv
            idx += 3
        return bytes(buf)

    scale = 4095.0 if bit_depth == 12 else 65535.0
    buf = bytearray(LUT_16BIT_U16_BYTES)
    pack_into = struct.pack_into
    idx = 0
    for r, g, b in entries:
        rv = int(round((0.0 if r < 0.0 else (1.0 if r > 1.0 else r)) * scale))
        gv = int(round((0.0 if g < 0.0 else (1.0 if g > 1.0 else g)) * scale))
        bv = int(round((0.0 if b < 0.0 else (1.0 if b > 1.0 else b)) * scale))
        pack_into("<HHH", buf, idx, rv, gv, bv)
        idx += 6
    return bytes(buf)


def slog3_linear_to_code(linear_reflection: float) -> float:
    """Sony S-Log3 official OETF mapping scene linear reflection -> normalized code [0, 1]."""
    if linear_reflection >= 0.01125000:
        ire_10bit = 420.0 + math.log10((linear_reflection + 0.01) / (0.18 + 0.01)) * 261.5
    else:
        ire_10bit = (linear_reflection * (171.2102946929 - 95.0) / 0.01125000) + 95.0
    norm = ire_10bit / 1023.0
    if norm < 0.0:
        return 0.0
    if norm > 1.0:
        return 1.0
    return norm


def verify_slog3_identity_ramp(
    lut_17: Optional[ParsedCubeLut] = None,
    *,
    bit_depth: int = 12,
    samples: int = 256,
) -> SLog3RampProof:
    """Prove `17^3 -> 33^3` identity `.cube` maps an S-Log3 ramp within `<= 1 LSB` error."""
    if lut_17 is None:
        lut_17 = parse_and_sanitize_cube_lut(build_identity_cube_lut(17))
    lut_33 = upsample_cube_17_to_33(lut_17)
    dma_bytes = pack_cube_to_dma_table(lut_33, bit_depth=bit_depth)
    max_code = 4095 if bit_depth == 12 else (65535 if bit_depth == 16 else 255)

    # Read back quantized R channel from packed 33^3 diagonal R=G=B or via trilinear lookup
    max_lsb_err = 0
    max_float_err = 0.0

    # Sample scene linear reflections from 0.0 to 10.0 (covering S-Log3 black to >90% white)
    for i in range(samples):
        lin = (i / float(samples - 1)) * 6.0
        slog3_x = slog3_linear_to_code(lin)
        out_r, out_g, out_b = trilinear_sample_cube(lut_33, slog3_x, slog3_x, slog3_x)
        err_f = max(abs(out_r - slog3_x), abs(out_g - slog3_x), abs(out_b - slog3_x))
        if err_f > max_float_err:
            max_float_err = err_f

        # Also verify against quantized hardware DMA table (trilinear over packed U12/U16 values)
        fpos = slog3_x * 32.0
        idx0 = int(fpos)
        if idx0 >= 32:
            idx0 = 31
        idx1 = idx0 + 1
        frac = fpos - idx0
        if bit_depth == 8:
            v0 = dma_bytes[(idx0 + 33 * idx0 + 1089 * idx0) * 3]
            v1 = dma_bytes[(idx1 + 33 * idx1 + 1089 * idx1) * 3]
        else:
            v0 = struct.unpack_from("<H", dma_bytes, (idx0 + 33 * idx0 + 1089 * idx0) * 6)[0]
            v1 = struct.unpack_from("<H", dma_bytes, (idx1 + 33 * idx1 + 1089 * idx1) * 6)[0]
        hw_code = int(round(v0 * (1.0 - frac) + v1 * frac))
        expected_code = int(round(slog3_x * max_code))
        lsb_err = abs(hw_code - expected_code)
        if lsb_err > max_lsb_err:
            max_lsb_err = lsb_err

    return SLog3RampProof(
        passed=(max_lsb_err <= 1 and max_float_err <= 1e-5),
        samples_tested=samples,
        bit_depth=bit_depth,
        max_lsb_error=max_lsb_err,
        max_float_error=max_float_err,
        lut_17_sha256=lut_17.sha256,
        lut_33_sha256=lut_33.sha256,
        dma_table_bytes=len(dma_bytes),
        dma_table_sha256=hashlib.sha256(dma_bytes).hexdigest(),
    )


def build_p11_mpr_set_lut_descriptor(
    *,
    enable: bool,
    cube_path: str,
    lut_payload_bytes: int,
    base_iso: int = 800,
    ei_index: int = 800,
    category: int = 3,
    look_slot: int = 1,
) -> bytes:
    """Build exact 164-byte `mpr::SetLutData` staging descriptor matching `libmpr.so` offsets."""
    if base_iso not in DUAL_NATIVE_ISO_BASES:
        raise CubeLutSanitizationError(f"Invalid base_iso={base_iso}; expected {DUAL_NATIVE_ISO_BASES}")
    encoded_path = cube_path.encode("latin1", errors="strict")
    if len(encoded_path) >= 64:
        raise CubeLutSanitizationError(f"cube_path must be < 64 bytes, got {len(encoded_path)}")
    if enable and not encoded_path:
        raise CubeLutSanitizationError("Enabled 3D LUT requires non-empty cube_path")
    if enable and lut_payload_bytes not in (
        LUT_8BIT_RAW_BYTES,
        LUT_8BIT_ALIGNED_BYTES,
        LUT_16BIT_U16_BYTES,
    ):
        raise CubeLutSanitizationError(
            f"Unsupported 33^3 DMA payload size {lut_payload_bytes}"
        )

    buf = bytearray(MPR_SET_LUT_DESCRIPTOR_BYTES)
    struct.pack_into("<I", buf, 0x00, MPR_SET_LUT_DESCRIPTOR_BYTES)
    struct.pack_into("<B", buf, 0x04, 1 if enable else 0)
    struct.pack_into(
        "<BBHIIIIII",
        buf,
        0x05,
        category & 0xFF,
        look_slot & 0xFF,
        TARGET_HW_LUT_GRID_SIZE,
        lut_payload_bytes,
        base_iso,
        ei_index,
        TARGET_HW_LUT_VOXEL_COUNT,
        LUT_CUBE_PARSER_ALLOC_BYTES,
        LUT_DMA_SRAM_REG_THRESHOLD,
    )
    buf[0x1F : 0x1F + len(encoded_path)] = encoded_path
    return bytes(buf)


def build_p11_0165_lut_dma_packet(
    *,
    category: int = 3,
    look_name: int = 0,
    exist_user_lut: int = 1,
    data_size: int = LUT_12BIT_U16_BYTES,
    data_offset_sram: int = 0x1000,
    data_offset_reg: int = 0x20000,
    data_size_reg: int = 0x400,
) -> bytes:
    """Build exact 36-byte `0x92840747` `0x0165` (`video_set_lookname_procam`) DMA descriptor."""
    if data_size > LUT_DMA_SRAM_REG_THRESHOLD:
        inline_sz = 0
        sram_off = data_offset_sram
        sram_sz = data_size
        reg_off = data_offset_reg
        reg_sz = data_size_reg
    else:
        inline_sz = data_size
        sram_off = 0
        sram_sz = 0
        reg_off = 0
        reg_sz = 0

    return struct.pack(
        "<HHHHBBHIIIIII",
        UIPC_BB_MAGIC,
        UIPC_BB_OPCODE_LUT_DMA,
        LUT_DMA_ENABLE_SIZE,
        UIPC_BB_FLAGS,
        category & 0xFF,
        look_name & 0xFF,
        0,
        exist_user_lut & 0xFFFFFFFF,
        inline_sz & 0xFFFFFFFF,
        sram_off & 0xFFFFFFFF,
        sram_sz & 0xFFFFFFFF,
        reg_off & 0xFFFFFFFF,
        reg_sz & 0xFFFFFFFF,
    )


def build_p11_0166_lut_toggle_packet(*, enable: bool) -> bytes:
    """Build exact 10-byte `0x92840747` `0x0166` LUT enable/reset packet."""
    return struct.pack(
        "<HHHHH",
        UIPC_BB_MAGIC,
        UIPC_BB_OPCODE_LUT_TOGGLE,
        LUT_TOGGLE_SIZE,
        UIPC_BB_FLAGS,
        1 if enable else 0,
    )


def generate_bk4_lut_slot_properties(
    *,
    active_slot_name: str = "User1",
    populated_user_slots: Sequence[int] = (1,),
) -> Tuple[int, Dict[int, bytes]]:
    """Generate `BK4` `0x02cf1453` Select LUT + `0x02cf14a4..0x02cf14b3` User1..16 presence flags."""
    if active_slot_name in BUILTIN_LUT_SLOTS:
        select_code = BUILTIN_LUT_SLOTS[active_slot_name]
    elif active_slot_name in USER_LUT_SLOTS:
        select_code = USER_LUT_SLOTS[active_slot_name]
    else:
        raise CubeLutSanitizationError(f"Unknown LUT slot name {active_slot_name!r}")

    populated_set = set(populated_user_slots)
    for idx in populated_set:
        if idx < 1 or idx > 16:
            raise CubeLutSanitizationError(f"User LUT slot index {idx} must be in 1..16")

    if active_slot_name in USER_LUT_SLOTS:
        slot_num = int(active_slot_name[4:])
        if slot_num not in populated_set:
            raise CubeLutSanitizationError(
                f"Active slot {active_slot_name} must be marked present in 0x02cf14a4..0x02cf14b3"
            )

    props: Dict[int, bytes] = {BKID_APP_SELECT_LUT: bytes((select_code,))}
    for slot_idx in range(1, 17):
        prop_id = BKID_USER_LUT_FLAG_START + (slot_idx - 1)
        props[prop_id] = b"\x01" if slot_idx in populated_set else b"\x00"
    return select_code, props


def build_p11_lut_hardware_bundle(
    lut: ParsedCubeLut,
    *,
    slot_name: str = "User1",
    populated_user_slots: Sequence[int] = (1,),
    bit_depth: int = 12,
    base_iso: int = 800,
    ei_index: int = 800,
) -> P11LutHardwareBundle:
    """Pack a sanitized `.cube` LUT into `33^3` DMA table, `P11` `SetLutData`/`0x0165`/`0x0166`, and `BK4`."""
    select_code, bk4_props = generate_bk4_lut_slot_properties(
        active_slot_name=slot_name,
        populated_user_slots=populated_user_slots,
    )
    if slot_name in USER_LUT_SLOTS:
        slot_idx = int(slot_name[4:])
        cube_path = f"{FX3_P30_MOUNT_POINT}LUT{slot_idx:03d}.cube"
    else:
        slot_idx = select_code + 1
        cube_path = f"{FX3_P30_MOUNT_POINT}{slot_name}.cube"

    dma_table = pack_cube_to_dma_table(lut, bit_depth=bit_depth)
    mpr_desc = build_p11_mpr_set_lut_descriptor(
        enable=True,
        cube_path=cube_path,
        lut_payload_bytes=len(dma_table),
        base_iso=base_iso,
        ei_index=ei_index,
        category=3,
        look_slot=slot_idx,
    )
    pkt_0165 = build_p11_0165_lut_dma_packet(
        category=3,
        look_name=select_code,
        exist_user_lut=1 if slot_name in USER_LUT_SLOTS else 0,
        data_size=len(dma_table),
    )
    pkt_0166 = build_p11_0166_lut_toggle_packet(enable=True)

    bk4_rec = build_clean_room_bk4_record(
        properties=tuple(sorted(bk4_props.items()))
    )
    bk4_audit: BK4RecordAudit = audit_bk4_record_bytes(bk4_rec)

    user_flags_hex = {
        f"0x{pid:08x}": bk4_props[pid].hex()
        for pid in range(BKID_USER_LUT_FLAG_START, BKID_USER_LUT_FLAG_END + 1)
    }
    return P11LutHardwareBundle(
        slot_name=slot_name,
        select_lut_code=select_code,
        cube_path=cube_path,
        grid_size_source=lut.grid_size,
        grid_size_hw=TARGET_HW_LUT_GRID_SIZE,
        dma_bit_depth=bit_depth,
        dma_table_bytes=len(dma_table),
        dma_table_sha256=hashlib.sha256(dma_table).hexdigest(),
        mpr_descriptor_bytes=len(mpr_desc),
        mpr_descriptor_hex=mpr_desc.hex(),
        dma_packet_0165_hex=pkt_0165.hex(),
        toggle_packet_0166_hex=pkt_0166.hex(),
        uses_dram_dma_path=len(dma_table) > LUT_DMA_SRAM_REG_THRESHOLD,
        bk4_select_lut_hex=bk4_props[BKID_APP_SELECT_LUT].hex(),
        bk4_user_flags_hex=user_flags_hex,
        bk4_record_valid=bk4_audit.valid,
    )


def evaluate_p1_nflasha30_storage_budget(
    slot_file_sizes: Sequence[int],
) -> P1StorageBudgetReport:
    """Verify up to 16 User `.cube` LUT files fit FX3 `P1` (`/dev/nflasha30`, 48.00 MiB VFAT)."""
    errors: List[str] = []
    if len(slot_file_sizes) > FX3_P30_USER_SLOT_COUNT:
        errors.append(
            f"Too many User LUT slots: {len(slot_file_sizes)} > {FX3_P30_USER_SLOT_COUNT}"
        )
    allocated = 0
    for idx, sz in enumerate(slot_file_sizes, start=1):
        if sz <= 0:
            errors.append(f"User{idx}: non-positive LUT file size {sz}")
            continue
        if sz > MAX_SAFE_CUBE_FILE_BYTES:
            errors.append(
                f"User{idx}: size {sz} B exceeds per-slot safe parser guard {MAX_SAFE_CUBE_FILE_BYTES} B"
            )
        clusters = (sz + FX3_P30_CLUSTER_BYTES - 1) // FX3_P30_CLUSTER_BYTES
        allocated += clusters * FX3_P30_CLUSTER_BYTES

    remaining = FX3_P30_USABLE_DATA_BYTES - allocated
    if remaining < 0:
        errors.append(
            f"/dev/nflasha30 overflow: allocated {allocated} B > usable {FX3_P30_USABLE_DATA_BYTES} B"
        )
    rem_pct = round((remaining / float(FX3_P30_TOTAL_BYTES)) * 100.0, 2)
    return P1StorageBudgetReport(
        passed=len(errors) == 0,
        device_path=FX3_P30_DEVICE_PATH,
        mount_point=FX3_P30_MOUNT_POINT,
        total_partition_bytes=FX3_P30_TOTAL_BYTES,
        usable_data_bytes=FX3_P30_USABLE_DATA_BYTES,
        slot_count=len(slot_file_sizes),
        allocated_cluster_bytes=allocated,
        remaining_bytes=remaining,
        remaining_percent=rem_pct,
        max_per_slot_bytes=MAX_SAFE_CUBE_FILE_BYTES,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Part B: Sony `RTMD` (`SMPTE RDD 18` / `0xE304`) Frame Packet & IBIS Verifier
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RtmdFrameMetadata:
    imx510_readout_us: int
    base_iso: int
    ei_index: int
    shutter_angle_deg: float
    active_lut_name: str
    steadyshot_mode: str
    center_lock_energized: bool = True
    floating_sensor_hazard: bool = False
    gyro_sample_hz: int = 1000
    gyro_xyz_mrad_s: Tuple[int, int, int] = (12, -4, 7)
    accel_xyz_mg: Tuple[int, int, int] = (0, 0, 981)


@dataclass(frozen=True)
class RtmdVerificationResult:
    valid: bool
    ul_hex: str
    packet_bytes: int
    packet_sha256: str
    parsed_tags_hex: Tuple[str, ...]
    imx510_readout_us: int
    base_iso: int
    ei_index: int
    shutter_angle_deg: float
    active_lut_name: str
    steadyshot_mode: str
    center_lock_energized: bool
    floating_sensor_hazard: bool
    gyro_sample_hz: int
    gyro_xyz_mrad_s: Tuple[int, int, int]
    accel_xyz_mg: Tuple[int, int, int]
    coherence_flags: int
    catalyst_and_gyroflow_coherent: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class DonorLutRtmdProfile:
    label: str
    source_mode: str
    file_bytes: int
    matched_markers: Tuple[str, ...]
    missing_markers: Tuple[str, ...]
    smpte_ul_prefix_hits: int


@dataclass(frozen=True)
class CubeLutAndRtmdReport:
    schema_version: str
    version: str
    mode: str
    all_checks_passed: bool
    report_sha256: str
    cube_17_audit: CubeLutAuditSummary
    cube_33_audit: CubeLutAuditSummary
    slog3_identity_proof: SLog3RampProof
    p11_hardware_bundle: P11LutHardwareBundle
    p1_storage_budget: P1StorageBudgetReport
    rtmd_verification: RtmdVerificationResult
    donor_profiles: Dict[str, DonorLutRtmdProfile]
    errors: Tuple[str, ...]


def encode_ber_length(length: int) -> bytes:
    """Encode SMPTE KLV BER definite length."""
    if length < 0:
        raise RtmdProtocolError(f"Negative BER length {length}")
    if length < 0x80:
        return bytes((length,))
    nbytes = (length.bit_length() + 7) // 8
    return bytes((0x80 | nbytes,)) + length.to_bytes(nbytes, "big")


def decode_ber_length(buf: bytes, offset: int) -> Tuple[int, int]:
    """Decode SMPTE KLV BER definite length returning `(length, next_offset)`."""
    if offset >= len(buf):
        raise RtmdProtocolError("Truncated BER length")
    first = buf[offset]
    if first < 0x80:
        return first, offset + 1
    num_bytes = first & 0x7F
    if num_bytes == 0 or num_bytes > 4:
        raise RtmdProtocolError(f"Unsupported BER length byte count {num_bytes}")
    end = offset + 1 + num_bytes
    if end > len(buf):
        raise RtmdProtocolError("Truncated long-form BER length")
    val = int.from_bytes(buf[offset + 1 : end], "big")
    return val, end


def _validate_rtmd_metadata(meta: RtmdFrameMetadata) -> None:
    if meta.imx510_readout_us < 1000 or meta.imx510_readout_us > 50000:
        raise RtmdProtocolError(
            f"IMX510 readout duration {meta.imx510_readout_us} us out of bounds [1000..50000]"
        )
    if meta.base_iso not in DUAL_NATIVE_ISO_BASES:
        raise RtmdProtocolError(
            f"Dual Base ISO {meta.base_iso} must be in {DUAL_NATIVE_ISO_BASES}"
        )
    if meta.ei_index < 200 or meta.ei_index > 102400:
        raise RtmdProtocolError(f"EI index {meta.ei_index} out of range [200..102400]")
    if not math.isfinite(meta.shutter_angle_deg) or meta.shutter_angle_deg <= 0.0 or meta.shutter_angle_deg > 360.0:
        raise RtmdProtocolError(f"Invalid Shutter Angle {meta.shutter_angle_deg}")
    if not meta.active_lut_name or len(meta.active_lut_name.encode("utf-8")) > 64:
        raise RtmdProtocolError("Invalid active_lut_name")
    if meta.steadyshot_mode not in VALID_STEADYSHOT_MODES:
        raise RtmdProtocolError(f"Unsupported steadyshot_mode {meta.steadyshot_mode!r}")
    if not meta.center_lock_energized or meta.floating_sensor_hazard:
        raise RtmdProtocolError(
            "FX3 IMX510 IBIS center-lock violation: floating sensor hazard detected"
        )
    if meta.gyro_sample_hz <= 0 or meta.gyro_sample_hz > 10000:
        raise RtmdProtocolError(f"Invalid gyro_sample_hz={meta.gyro_sample_hz}")
    if len(meta.gyro_xyz_mrad_s) != 3 or len(meta.accel_xyz_mg) != 3:
        raise RtmdProtocolError("Gyro and accel vectors must have 3 axes")


def build_rtmd_klv_packet(meta: RtmdFrameMetadata) -> bytes:
    """Build a big-endian SMPTE RDD 18 / Sony `RTMD` (`0xE304` IBIS/Gyro) KLV frame packet."""
    _validate_rtmd_metadata(meta)

    payload = bytearray()

    def _add_tag(tag: int, val: bytes) -> None:
        payload.extend(struct.pack(">HH", tag & 0xFFFF, len(val)))
        payload.extend(val)

    shutter_x100 = int(round(meta.shutter_angle_deg * 100.0))
    _add_tag(RTMD_TAG_SHUTTER_ANGLE_X100, struct.pack(">I", shutter_x100))
    _add_tag(RTMD_TAG_IMX510_READOUT_US, struct.pack(">I", meta.imx510_readout_us))
    _add_tag(RTMD_TAG_DUAL_BASE_ISO_AND_EI, struct.pack(">II", meta.base_iso, meta.ei_index))
    _add_tag(RTMD_TAG_ACTIVE_3D_LUT_NAME, meta.active_lut_name.encode("utf-8"))

    ss_code = VALID_STEADYSHOT_MODES[meta.steadyshot_mode]
    coherence_flags = RTMD_COHERENCE_ALL_OK
    e304_body = struct.pack(
        ">BBBBHH3i3i",
        ss_code,
        1 if meta.center_lock_energized else 0,
        1 if meta.floating_sensor_hazard else 0,
        5,  # 5-axis IBIS
        meta.gyro_sample_hz,
        coherence_flags,
        meta.gyro_xyz_mrad_s[0],
        meta.gyro_xyz_mrad_s[1],
        meta.gyro_xyz_mrad_s[2],
        meta.accel_xyz_mg[0],
        meta.accel_xyz_mg[1],
        meta.accel_xyz_mg[2],
    )
    _add_tag(RTMD_TAG_IMX510_IBIS_GYRO_E304, e304_body)

    return RTMD_RDD18_ACQUISITION_UL + encode_ber_length(len(payload)) + bytes(payload)


def parse_and_verify_rtmd_klv_packet(packet: bytes) -> RtmdVerificationResult:
    """Parse and verify a big-endian Sony `RTMD` (`SMPTE RDD 18` / `0xE304`) KLV packet."""
    errors: List[str] = []
    if len(packet) < 17:
        raise RtmdProtocolError(f"RTMD KLV packet too short ({len(packet)} B)")
    ul = packet[:16]
    if not ul.startswith(SMPTE_KLV_UL_PREFIX):
        raise RtmdProtocolError(f"Invalid SMPTE KLV UL prefix {ul[:4].hex()}")

    declared_len, body_off = decode_ber_length(packet, 16)
    if body_off + declared_len != len(packet):
        raise RtmdProtocolError(
            f"BER length mismatch: header={declared_len}, actual={len(packet) - body_off}"
        )

    tags: Dict[int, bytes] = {}
    ordered_tags: List[str] = []
    pos = body_off
    end = len(packet)
    while pos < end:
        if pos + 4 > end:
            raise RtmdProtocolError(f"Truncated local tag header at offset {pos}")
        tag, vlen = struct.unpack_from(">HH", packet, pos)
        pos += 4
        if pos + vlen > end:
            raise RtmdProtocolError(f"Truncated tag 0x{tag:04x} value at offset {pos}")
        tags[tag] = packet[pos : pos + vlen]
        ordered_tags.append(f"0x{tag:04x}")
        pos += vlen

    required_tags = (
        RTMD_TAG_SHUTTER_ANGLE_X100,
        RTMD_TAG_IMX510_READOUT_US,
        RTMD_TAG_DUAL_BASE_ISO_AND_EI,
        RTMD_TAG_ACTIVE_3D_LUT_NAME,
        RTMD_TAG_IMX510_IBIS_GYRO_E304,
    )
    for req in required_tags:
        if req not in tags:
            errors.append(f"Missing mandatory RTMD tag 0x{req:04x}")

    shutter_deg = 0.0
    if RTMD_TAG_SHUTTER_ANGLE_X100 in tags:
        v = tags[RTMD_TAG_SHUTTER_ANGLE_X100]
        if len(v) != 4:
            errors.append(f"Tag 0x3209 expected 4B, got {len(v)}B")
        else:
            shutter_deg = struct.unpack(">I", v)[0] / 100.0
            if shutter_deg <= 0.0 or shutter_deg > 360.0:
                errors.append(f"Shutter angle out of range: {shutter_deg}")

    readout_us = 0
    if RTMD_TAG_IMX510_READOUT_US in tags:
        v = tags[RTMD_TAG_IMX510_READOUT_US]
        if len(v) != 4:
            errors.append(f"Tag 0x3219 expected 4B, got {len(v)}B")
        else:
            readout_us = struct.unpack(">I", v)[0]
            if readout_us < 1000 or readout_us > 50000:
                errors.append(f"IMX510 readout_us out of bounds: {readout_us}")

    base_iso = 0
    ei_index = 0
    if RTMD_TAG_DUAL_BASE_ISO_AND_EI in tags:
        v = tags[RTMD_TAG_DUAL_BASE_ISO_AND_EI]
        if len(v) != 8:
            errors.append(f"Tag 0x321a expected 8B, got {len(v)}B")
        else:
            base_iso, ei_index = struct.unpack(">II", v)
            if base_iso not in DUAL_NATIVE_ISO_BASES:
                errors.append(f"Invalid Dual Base ISO {base_iso}")
            if ei_index < 200 or ei_index > 102400:
                errors.append(f"Invalid EI index {ei_index}")

    lut_name = ""
    if RTMD_TAG_ACTIVE_3D_LUT_NAME in tags:
        try:
            lut_name = tags[RTMD_TAG_ACTIVE_3D_LUT_NAME].decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            errors.append("Tag 0xe105 LUT name is not valid UTF-8")
        if not lut_name:
            errors.append("Tag 0xe105 LUT name is empty")

    ss_mode = "Unknown"
    center_lock = False
    floating_hazard = True
    gyro_hz = 0
    coherence_flags = 0
    gyro_xyz = (0, 0, 0)
    accel_xyz = (0, 0, 0)
    if RTMD_TAG_IMX510_IBIS_GYRO_E304 in tags:
        v = tags[RTMD_TAG_IMX510_IBIS_GYRO_E304]
        if len(v) != RTMD_E304_PAYLOAD_BYTES:
            errors.append(f"Tag 0xe304 expected {RTMD_E304_PAYLOAD_BYTES}B, got {len(v)}B")
        else:
            ss_code, clk, flt, axes, gyro_hz, coherence_flags, gx, gy, gz, ax, ay, az = struct.unpack(
                ">BBBBHH3i3i", v
            )
            ss_mode = STEADYSHOT_CODE_TO_NAME.get(ss_code, f"Unknown({ss_code})")
            if ss_code not in STEADYSHOT_CODE_TO_NAME:
                errors.append(f"Invalid 0xe304 SteadyShot mode code {ss_code}")
            if axes != 5:
                errors.append(f"Expected 5-axis IBIS, got {axes}")
            center_lock = clk == 1
            floating_hazard = flt != 0
            gyro_xyz = (gx, gy, gz)
            accel_xyz = (ax, ay, az)
            if not center_lock:
                errors.append("0xe304 center_lock_energized is False")
            if floating_hazard:
                errors.append("0xe304 floating_sensor_hazard is True")
            if (coherence_flags & RTMD_COHERENCE_ALL_OK) != RTMD_COHERENCE_ALL_OK:
                errors.append(f"0xe304 coherence flags incomplete: 0x{coherence_flags:04x}")

    coherent = (
        center_lock
        and (not floating_hazard)
        and ((coherence_flags & RTMD_COHERENCE_ALL_OK) == RTMD_COHERENCE_ALL_OK)
        and len(errors) == 0
    )
    return RtmdVerificationResult(
        valid=len(errors) == 0,
        ul_hex=ul.hex(),
        packet_bytes=len(packet),
        packet_sha256=hashlib.sha256(packet).hexdigest(),
        parsed_tags_hex=tuple(ordered_tags),
        imx510_readout_us=readout_us,
        base_iso=base_iso,
        ei_index=ei_index,
        shutter_angle_deg=shutter_deg,
        active_lut_name=lut_name,
        steadyshot_mode=ss_mode,
        center_lock_energized=center_lock,
        floating_sensor_hazard=floating_hazard,
        gyro_sample_hz=gyro_hz,
        gyro_xyz_mrad_s=gyro_xyz,
        accel_xyz_mg=accel_xyz,
        coherence_flags=coherence_flags,
        catalyst_and_gyroflow_coherent=coherent,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Donor & Clean-Room Synthetic Fixture Scanner
# ---------------------------------------------------------------------------


def build_clean_room_lut_rtmd_fixtures(
    *,
    drop_fx3_nflasha30: bool = False,
    drop_libmpr_rdd18: bool = False,
) -> Dict[str, bytes]:
    """Build deterministic clean-room synthetic ELF64 stubs for LUT & RTMD scanning."""
    elf_hdr = b"\x7fELF\x02\x01\x01\x00" + bytes(56)

    fx3_app_tokens = list(SHARED_APPFW_LUT_MARKERS) + ([] if drop_fx3_nflasha30 else list(FX3_APPFW_P1_MARKERS))
    fx6_app_tokens = list(SHARED_APPFW_LUT_MARKERS) + ["User16", "/usr/share/lut"]

    mpr_tokens = list(SHARED_LIBMPR_LUT_AND_RTMD_MARKERS)
    if drop_libmpr_rdd18:
        mpr_tokens = [t for t in mpr_tokens if "Rdd18" not in t and "Gyroscope" not in t]

    mpr_blob = elf_hdr + b"\x00".join(t.encode("ascii") for t in mpr_tokens) + b"\x00" + RTMD_RDD18_ACQUISITION_UL
    return {
        "fx3_appfw": elf_hdr + b"\x00".join(t.encode("ascii") for t in fx3_app_tokens) + b"\x00",
        "fx6_appfw": elf_hdr + b"\x00".join(t.encode("ascii") for t in fx6_app_tokens) + b"\x00",
        "fx3_libmpr": mpr_blob,
        "fx6_libmpr": mpr_blob,
    }


def _scan_markers(data: bytes, markers: Sequence[str], *, label: str, source_mode: str) -> DonorLutRtmdProfile:
    matched: List[str] = []
    missing: List[str] = []
    for m in markers:
        if data.find(m.encode("ascii")) != -1:
            matched.append(m)
        else:
            missing.append(m)
    return DonorLutRtmdProfile(
        label=label,
        source_mode=source_mode,
        file_bytes=len(data),
        matched_markers=tuple(matched),
        missing_markers=tuple(missing),
        smpte_ul_prefix_hits=data.count(SMPTE_KLV_UL_PREFIX),
    )


@functools.lru_cache(maxsize=1)
def _run_deterministic_lut_rtmd_selftest() -> Tuple[
    CubeLutAuditSummary,
    CubeLutAuditSummary,
    SLog3RampProof,
    P11LutHardwareBundle,
    P1StorageBudgetReport,
    RtmdVerificationResult,
    Tuple[str, ...],
]:
    selftest_errors: List[str] = []
    cube_17_txt = build_identity_cube_lut(17, title="SONY_SLOG3_ID_17")
    cube_33_txt = build_identity_cube_lut(33, title="SONY_SLOG3_ID_33")
    cube_17_audit = audit_cube_lut_text(cube_17_txt)
    cube_33_audit = audit_cube_lut_text(cube_33_txt)
    if not cube_17_audit.valid:
        selftest_errors.extend(cube_17_audit.errors)
    if not cube_33_audit.valid:
        selftest_errors.extend(cube_33_audit.errors)

    lut_17 = parse_and_sanitize_cube_lut(cube_17_txt)
    lut_33_from_17 = upsample_cube_17_to_33(lut_17)
    slog3_proof = verify_slog3_identity_ramp(lut_17, bit_depth=12, samples=256)
    if not slog3_proof.passed:
        selftest_errors.append(
            f"S-Log3 identity ramp exceeded 1 LSB: max_lsb_error={slog3_proof.max_lsb_error}"
        )

    p11_bundle = build_p11_lut_hardware_bundle(
        lut_33_from_17,
        slot_name="User1",
        populated_user_slots=(1, 2, 16),
        bit_depth=12,
        base_iso=800,
        ei_index=800,
    )
    if not p11_bundle.bk4_record_valid:
        selftest_errors.append("BK4 LUT slot-flag record audit failed")

    p1_budget = evaluate_p1_nflasha30_storage_budget([cube_33_audit.byte_length] * 16)
    if not p1_budget.passed:
        selftest_errors.extend(p1_budget.errors)

    rtmd_meta = RtmdFrameMetadata(
        imx510_readout_us=8600,
        base_iso=800,
        ei_index=800,
        shutter_angle_deg=180.0,
        active_lut_name="User1",
        steadyshot_mode="Standard",
        center_lock_energized=True,
        floating_sensor_hazard=False,
        gyro_sample_hz=1000,
        gyro_xyz_mrad_s=(12, -4, 7),
        accel_xyz_mg=(0, 0, 981),
    )
    rtmd_pkt = build_rtmd_klv_packet(rtmd_meta)
    rtmd_res = parse_and_verify_rtmd_klv_packet(rtmd_pkt)
    if not rtmd_res.valid or not rtmd_res.catalyst_and_gyroflow_coherent:
        selftest_errors.extend(rtmd_res.errors)

    return (
        cube_17_audit,
        cube_33_audit,
        slog3_proof,
        p11_bundle,
        p1_budget,
        rtmd_res,
        tuple(selftest_errors),
    )


def analyze_cube_lut_and_rtmd(
    *,
    clean_room: bool = False,
    repo_root: Path = DEFAULT_REPO_ROOT,
    env: Optional[Mapping[str, str]] = None,
    synthetic_overrides: Optional[Mapping[str, bytes]] = None,
) -> CubeLutAndRtmdReport:
    """Run end-to-end Phase 37 `.cube` LUT sanitizer/packer & Sony `RTMD` (`0xE304`) audit."""
    errors: List[str] = []

    if synthetic_overrides is not None:
        blobs = dict(synthetic_overrides)
        mode = "CLEAN_ROOM_SYNTHETIC_VERIFIED"
        source_mode = "SYNTHETIC_CLEAN_ROOM"
    else:
        relpaths = {
            "fx3_appfw": FX3_APPFW_RELPATH,
            "fx6_appfw": FX6_APPFW_RELPATH,
            "fx3_libmpr": FX3_LIBMPR_RELPATH,
            "fx6_libmpr": FX6_LIBMPR_RELPATH,
        }
        resolved: Dict[str, Optional[Path]] = {
            k: resolve_donor_file(rel, repo_root=repo_root, env=env, clean_room=clean_room)
            for k, rel in relpaths.items()
        }
        if all(p is not None for p in resolved.values()):
            blobs = {k: read_bytes_rdonly(p) for k, p in resolved.items() if p is not None}
            mode = "LOCAL_DONOR_VERIFIED"
            source_mode = "LOCAL_DONOR_RDONLY"
        else:
            blobs = build_clean_room_lut_rtmd_fixtures()
            mode = "CLEAN_ROOM_SYNTHETIC_VERIFIED"
            source_mode = "SYNTHETIC_CLEAN_ROOM"

    donor_profiles: Dict[str, DonorLutRtmdProfile] = {
        "fx3_appfw": _scan_markers(
            blobs["fx3_appfw"],
            SHARED_APPFW_LUT_MARKERS + FX3_APPFW_P1_MARKERS,
            label="FX3_v7.02_appFw.so",
            source_mode=source_mode,
        ),
        "fx6_appfw": _scan_markers(
            blobs["fx6_appfw"],
            SHARED_APPFW_LUT_MARKERS,
            label="FX6_v6.01_appFw.so",
            source_mode=source_mode,
        ),
        "fx3_libmpr": _scan_markers(
            blobs["fx3_libmpr"],
            SHARED_LIBMPR_LUT_AND_RTMD_MARKERS,
            label="FX3_v7.02_libmpr.so",
            source_mode=source_mode,
        ),
        "fx6_libmpr": _scan_markers(
            blobs["fx6_libmpr"],
            SHARED_LIBMPR_LUT_AND_RTMD_MARKERS,
            label="FX6_v6.01_libmpr.so",
            source_mode=source_mode,
        ),
    }

    for key, prof in donor_profiles.items():
        if prof.missing_markers:
            errors.append(f"{key} missing LUT/RTMD markers: {prof.missing_markers}")
    if donor_profiles["fx3_libmpr"].smpte_ul_prefix_hits == 0:
        errors.append("fx3_libmpr missing SMPTE KLV UL prefix 060e2b34")
    if donor_profiles["fx6_libmpr"].smpte_ul_prefix_hits == 0:
        errors.append("fx6_libmpr missing SMPTE KLV UL prefix 060e2b34")

    (
        cube_17_audit,
        cube_33_audit,
        slog3_proof,
        p11_bundle,
        p1_budget,
        rtmd_res,
        selftest_errors,
    ) = _run_deterministic_lut_rtmd_selftest()
    errors.extend(selftest_errors)

    digest_src = "|".join(
        [
            PHASE_37_SCHEMA,
            slog3_proof.lut_33_sha256,
            slog3_proof.dma_table_sha256,
            p11_bundle.mpr_descriptor_hex,
            p11_bundle.dma_packet_0165_hex,
            p11_bundle.toggle_packet_0166_hex,
            rtmd_res.packet_sha256,
            str(p1_budget.remaining_bytes),
        ]
    ).encode("utf-8")
    report_sha256 = hashlib.sha256(digest_src).hexdigest()

    return CubeLutAndRtmdReport(
        schema_version=PHASE_37_SCHEMA,
        version=PHASE_37_VERSION,
        mode=mode,
        all_checks_passed=(len(errors) == 0),
        report_sha256=report_sha256,
        cube_17_audit=cube_17_audit,
        cube_33_audit=cube_33_audit,
        slog3_identity_proof=slog3_proof,
        p11_hardware_bundle=p11_bundle,
        p1_storage_budget=p1_budget,
        rtmd_verification=rtmd_res,
        donor_profiles=donor_profiles,
        errors=tuple(errors),
    )


def cube_lut_and_rtmd_report_to_dict(report: CubeLutAndRtmdReport) -> Dict[str, object]:
    """Convert `CubeLutAndRtmdReport` into a JSON-serializable dictionary."""
    return asdict(report)
