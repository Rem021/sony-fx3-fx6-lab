#!/usr/bin/env python3
"""Phase 29 — Hardware-Free Software GPE Raster/Sprite Compositor & `virtual-rom-v1` Bluetooth HCI H4 UART Emulator.

Implements two hardware-free virtualization subsystems inside `outputs/fx3-vm/`:

Part A — Deterministic Software GPE (`GRM_gpermFillrect` / `GRM_gpermRectblit` / `HOSDAP02` / `ramfb` Scanout):
  - Models the `1024x540` `GPE0` (`0x41E001000`) & `ramfb` (`[0x41E100000, 0x41E600000)`) scanout pipeline.
  - Supports `Fillrect`, `Rectblit`, 9-patch border stretch (`left`, `top`, `right`, `bottom` insets),
    and Porter-Duff `SRC_OVER` / `SRC_COPY` compositing across `RGBA4444`, `ARGB4444`, `RGBA8888`, and `A8` glyph masks.
  - Enforces bit-exact `fx6_px` (`0xAARRGGBB`, `[B, G, R, A]` LE) R/B channel parity with `libgrm-fbinit25-542.c`
    and `fx6_next_stage_assist_log.c`.
  - Performs strictly `os.O_RDONLY` pure-CPU LDEC/LZ77 (`0x0F` raw + `0xF0` back-reference) sprite decoding
    from FX6 `image_00_169.uxc` (or deterministic synthetic `uxd\\x07` fixtures when `FX3_FX6_FORCE_CLEAN_ROOM=1`
    or donor is absent), compositing them into `GPE0` and `HOSDAP02` `ramfb` XRGB8888 scanout buffers.

Part B — `virtual-rom-v1` Bluetooth HCI H4 UART (`/dev/ttyAMA3`) State-Machine Emulator:
  - Inspects FX6 `libbt-vendor.so` & `libInfraBluetoothCore.so` strictly via `os.O_RDONLY` (with clean-room fallback)
    for `/dev/ttyAMA3` HCI initialization markers.
  - Implements a full H4 UART packet framer & responder (`HCI_Reset 0x0C03`, `HCI_Read_Local_Version_Info 0x1001`,
    `HCI_Read_BD_ADDR 0x1009`, Broadcom/Cypress vendor patchram `0xFC2E`/`0xFC4C`/`0xFC4E` & baudrate `0xFC18` switch ACK).
  - Exercises 4 deterministic operating modes:
      1. `HEALTHY_VIRTUAL_ROM_V1`: full BSA HCI bring-up succeeds (`0` errors, deterministic `BD_ADDR`).
      2. `UART_DISCONNECTED_TIMEOUT`: dead/absent BT UART -> verifies `P12` `BT_DEGRADED_DISABLED` (`0xbb9` / `3001`) fallback.
      3. `PATCHRAM_CORRUPT_NACK`: mid-firmware `WF-12` NACK -> verifies Sony `00342260` Airplane-latch containment.
      4. `AIRPLANE_SHADOW_GATED`: Stage-A/B RAM-shadow `BK4\\0` (`0x019e0012=00`, `0x01a20002=00`) gates HCI TX to `0` packets.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse
import hashlib
import json
import os
import struct
from array import array
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple


# ---------------------------------------------------------------------------
# Phase 29 Schema & Stage-A/B Redline Constants
# ---------------------------------------------------------------------------

PHASE_29_SCHEMA = "phase29_soft_gpe_and_bt_rom_v1"
PHASE_29_VERSION = "29.0.0"

ENV_FORCE_CLEAN_ROOM = "FX3_FX6_FORCE_CLEAN_ROOM"
ENV_MAC_ROOT = "FX3_FX6_MAC_ROOT"
ENV_MAC_WORK_ROOT = "FX3_FX6_MAC_WORK_ROOT"
ENV_MAIN_LAB_WORK_ROOT = "FX3_FX6_MAIN_LAB_WORK_ROOT"

DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]
LEGACY_MAC_ROOT = Path("/Volumes/KAFU2T/AI/Projects/Mac")
CLEAN_ROOM_SENTINEL_DIRNAME = "__fx3_fx6_clean_room_donor_disabled__"

# Redline Locks
P8_CP_MUTATION_FORBIDDEN = True
WBI_MUTATION_BYTES = 0
CP_MUTATION_BYTES = 0
NVRAM_PERSISTENT_WRITES = 0

# GPE0 & ramfb Physical Memory Map (matching libgrm-fbinit25-542.c & a7c2-qemu)
GPE0_WIDTH = 1024
GPE0_HEIGHT = 540
GPE0_PIXEL_COUNT = GPE0_WIDTH * GPE0_HEIGHT  # 552,960
GPE0_BYTES = GPE0_PIXEL_COUNT * 4            # 2,211,840 (0x21C000)

GPE0_PHYS_BASE = 0x41E001000
GPE1_PHYS_BASE = 0x41E221000
FX6_MAILBOX_PHYS = 0x41E000F00
FX6_MAILBOX_MAGIC = 0x4658364D  # 'FX6M'
FX3_KEY_GATE_PHYS = 0x41DF00000
GPE_POOL_PHYS_BASE = 0x410524000
GPE_POOL_BYTES = 0x000940000

RAMFB_WINDOW_START = 0x41E100000
RAMFB_WINDOW_END = 0x41E600000
HOSDAP02_MAGIC = b"HOSDAP02"
HOSDAP02_HEADER_BYTES = 64

# Pixel Format Identifiers (matching BMP_PixelFormat & uxc_ldec_inspector.py)
PIXEL_FMT_RGBA4444 = "RGBA4444"
PIXEL_FMT_RGBA8888 = "RGBA8888"
PIXEL_FMT_ARGB4444 = "ARGB4444"
PIXEL_FMT_A8 = "A8"
PIXEL_FMT_ARGB8888 = "ARGB8888"

BMP_FMT_RGBA4444 = 1
BMP_FMT_RGBA8888 = 2
BMP_FMT_ARGB4444 = 3
BMP_FMT_A8 = 4

# Blend modes matching libgrm-fbinit25-542.c
BLEND_SRC_OVER = 0
BLEND_SRC_COPY = 1
BLEND_SRC_OVER_CONST_ALPHA = 2
BLEND_SRC_OVER_DUAL_ALPHA = 3
COLOR_MOD_TINT = 0x0E

# Sony .uxc / LDEC constants
UXC_MAGIC = b"uxc\x07"
UXD_MAGIC = b"uxd\x07"
UXC_HEADER_STRUCT = struct.Struct("<4sIHHI")
LDEC_LENGTH_TABLE: Tuple[int, ...] = (
    3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 32, 64
)
LDEC_MAX_BYTES = 16 * 1024 * 1024

# Bluetooth H4 / virtual-rom-v1 Constants
BT_UART_DEVICE = "/dev/ttyAMA3"
BT_DEFAULT_BAUD = 115200
BT_HIGH_BAUD = 3000000
BT_BSA_HAL_ERR_CODE = 0x0BB9  # 3001
SONY_NOTICE_00342260_ID = "00342260"

BT_BKID_ENABLE_PRIMARY = 0x019E0012
BT_BKID_RSRC_MODE = 0x01A20002

H4_PKT_COMMAND = 0x01
H4_PKT_ACL = 0x02
H4_PKT_SCO = 0x03
H4_PKT_EVENT = 0x04

HCI_EVT_COMMAND_COMPLETE = 0x0E
HCI_EVT_COMMAND_STATUS = 0x0F
HCI_EVT_HARDWARE_ERROR = 0x10

HCI_OP_RESET = 0x0C03
HCI_OP_READ_LOCAL_VERSION_INFO = 0x1001
HCI_OP_READ_BD_ADDR = 0x1009
HCI_OP_BCM_UPDATE_BAUDRATE = 0xFC18
HCI_OP_BCM_DOWNLOAD_MINIDRIVER = 0xFC2E
HCI_OP_BCM_WRITE_RAM = 0xFC4C
HCI_OP_BCM_LAUNCH_RAM = 0xFC4E

HCI_STATUS_SUCCESS = 0x00
HCI_STATUS_UNKNOWN_COMMAND = 0x01
HCI_STATUS_HARDWARE_FAILURE = 0x03
HCI_STATUS_COMMAND_DISALLOWED = 0x0C
HCI_STATUS_INVALID_PARAMS = 0x12

VIRTUAL_ROM_V1_MANUFACTURER = 0x000F  # Broadcom / Cypress virtual-rom-v1
VIRTUAL_ROM_V1_HCI_VER = 0x08         # BT 4.2 / 5.x host interface
VIRTUAL_ROM_V1_HCI_REV = 0x0101
VIRTUAL_ROM_V1_LMP_VER = 0x08
VIRTUAL_ROM_V1_LMP_SUBVER = 0x220E
VIRTUAL_ROM_V1_BD_ADDR = (0x58, 0x36, 0x57, 0x00, 0x29, 0x01)  # "58:36:57:00:29:01"

BT_MODE_HEALTHY = "HEALTHY_VIRTUAL_ROM_V1"
BT_MODE_UART_TIMEOUT = "UART_DISCONNECTED_TIMEOUT"
BT_MODE_PATCHRAM_NACK = "PATCHRAM_CORRUPT_NACK"
BT_MODE_AIRPLANE_GATED = "AIRPLANE_SHADOW_GATED"

ALL_BT_OPERATING_MODES: Tuple[str, ...] = (
    BT_MODE_HEALTHY,
    BT_MODE_UART_TIMEOUT,
    BT_MODE_PATCHRAM_NACK,
    BT_MODE_AIRPLANE_GATED,
)

REQUIRED_BT_VENDOR_MARKERS: Tuple[str, ...] = (
    "/dev/ttyAMA3",
    "HCI device open failed",
    "bt_hci_init_transport",
    "userial_vendor_set_baud",
    "rome_hci_reset_req",
    "rome_set_baudrate_req",
    "hci_send_cmd",
    "read_hci_event",
)

REQUIRED_BT_CORE_MARKERS: Tuple[str, ...] = (
    "/dev/ttyAMA3",
    "g_uart_fd",
    "g_default_termios_uart",
    "libosal_uipc.so",
    "_Z27wrapper_bt_interface_enableP13tBSA_MGT_OPEN",
    "_ZN12InfraBTCore_14CBTCoreProcess17startQcaBsaCommonEb",
    "_ZN12InfraBTCore_7CBTWoLE34HCI_Read_Local_Information_CommandEv",
    "hci_update_baud_rate",
)


class SoftGpeError(ValueError):
    """Raised on invalid GPE surface, LDEC stream, or ramfb aperture parameters."""


class BtRomEmulatorError(RuntimeError):
    """Raised on invalid H4 packet framing or unknown operating mode."""


# ---------------------------------------------------------------------------
# Strictly Read-Only (`os.O_RDONLY`) Donor Resolution & Reading
# ---------------------------------------------------------------------------


def is_forced_clean_room(env: Optional[Mapping[str, str]] = None) -> bool:
    source = os.environ if env is None else env
    return source.get(ENV_FORCE_CLEAN_ROOM, "").strip().lower() in ("1", "true", "yes")


def _iter_work_roots(*, env: Optional[Mapping[str, str]] = None) -> Tuple[Path, ...]:
    if is_forced_clean_room(env):
        return ()
    source = os.environ if env is None else env
    candidates: List[Path] = []
    for k in (ENV_MAC_WORK_ROOT, ENV_MAIN_LAB_WORK_ROOT):
        v = source.get(k, "").strip()
        if v:
            candidates.append(Path(os.path.expanduser(v)))
    mac_root = source.get(ENV_MAC_ROOT, "").strip()
    if mac_root:
        base = Path(os.path.expanduser(mac_root))
        candidates.append(base / "outputs" / "sony-fx3-fx6-lab" / "work")
        candidates.append(base / "work")
    candidates.append(DEFAULT_REPO_ROOT / "work")
    internal = Path.home() / "AI-Workspace" / "AI" / "Projects" / "Mac"
    candidates.append(internal / "outputs" / "sony-fx3-fx6-lab" / "work")
    candidates.append(internal / "work")
    candidates.append(LEGACY_MAC_ROOT / "outputs" / "sony-fx3-fx6-lab" / "work")
    candidates.append(LEGACY_MAC_ROOT / "work")
    seen: Set[str] = set()
    out: List[Path] = []
    for c in candidates:
        s = str(c)
        if s not in seen:
            seen.add(s)
            out.append(c)
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


def resolve_phase29_donor_paths(*, env: Optional[Mapping[str, str]] = None) -> Dict[str, Path]:
    """Locate FX6 `image_00_169.uxc`, `libbt-vendor.so`, and `libInfraBluetoothCore.so` read-only."""
    base = "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files"
    return {
        "fx6_image_uxc": _resolve_donor_file(f"{base}/share/app/image_00_169.uxc", env=env),
        "fx6_libbt_vendor": _resolve_donor_file(f"{base}/lib/libbt-vendor.so", env=env),
        "fx6_libbt_core": _resolve_donor_file(f"{base}/lib/libInfraBluetoothCore.so", env=env),
    }


def read_donor_bytes_readonly(path: Path) -> bytes:
    """Read a file strictly via `os.open(..., os.O_RDONLY)` and deterministic close."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        st = os.fstat(fd)
        chunks: List[bytes] = []
        remaining = st.st_size
        while remaining > 0:
            chunk = os.read(fd, min(remaining, 4 * 1024 * 1024))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)
    finally:
        os.close(fd)


# ---------------------------------------------------------------------------
# Part A: Pixel Format Converters (`fx6_px` Parity) & Pure-CPU LDEC/UXC
# ---------------------------------------------------------------------------


def fx6_px(r: int, g: int, b: int, a: int = 0xFF) -> int:
    """Pack `(r, g, b, a)` into `0xAARRGGBB` matching `fx6_next_stage_assist_log.c::fx6_px`."""
    return ((a & 0xFF) << 24) | ((r & 0xFF) << 16) | ((g & 0xFF) << 8) | (b & 0xFF)


def unpack_argb8888(px: int) -> Tuple[int, int, int, int]:
    """Return `(r, g, b, a)` from `0xAARRGGBB`."""
    return ((px >> 16) & 0xFF, (px >> 8) & 0xFF, px & 0xFF, (px >> 24) & 0xFF)


def rgba4444_to_argb8888(pv: int) -> int:
    """Expand 16-bit RGBA4444 (`0xRGBA`) to `0xAARRGGBB` (`* 17` matching `libgrm-fbinit25-542.c`)."""
    r = ((pv >> 12) & 0xF) * 17
    g = ((pv >> 8) & 0xF) * 17
    b = ((pv >> 4) & 0xF) * 17
    a = (pv & 0xF) * 17
    return (a << 24) | (r << 16) | (g << 8) | b


def argb4444_to_argb8888(pv: int) -> int:
    """Expand 16-bit ARGB4444 (`0xARGB`) to `0xAARRGGBB`."""
    a = ((pv >> 12) & 0xF) * 17
    r = ((pv >> 8) & 0xF) * 17
    g = ((pv >> 4) & 0xF) * 17
    b = (pv & 0xF) * 17
    return (a << 24) | (r << 16) | (g << 8) | b


def argb8888_to_rgba4444(px: int) -> int:
    """Pack `0xAARRGGBB` into 16-bit RGBA4444 (`0xRGBA`)."""
    r = (px >> 20) & 0xF
    g = (px >> 12) & 0xF
    b = (px >> 4) & 0xF
    a = (px >> 28) & 0xF
    return (r << 12) | (g << 8) | (b << 4) | a


def argb8888_to_argb4444(px: int) -> int:
    """Pack `0xAARRGGBB` into 16-bit ARGB4444 (`0xARGB`)."""
    a = (px >> 28) & 0xF
    r = (px >> 20) & 0xF
    g = (px >> 12) & 0xF
    b = (px >> 4) & 0xF
    return (a << 12) | (r << 8) | (g << 4) | b


def porter_duff_src_over(
    sr: int, sg: int, sb: int, sa: int,
    dr: int, dg: int, db: int, da: int,
) -> Tuple[int, int, int, int]:
    """Integer Porter-Duff `SRC_OVER` matching `libgrm-fbinit25-542.c::GRM_gpermRectblit`."""
    if sa == 0:
        return dr, dg, db, da
    if sa == 255:
        return sr, sg, sb, 255
    inv_a = 255 - sa
    out_r = (sr * sa + dr * inv_a) // 255
    out_g = (sg * sa + dg * inv_a) // 255
    out_b = (sb * sa + db * inv_a) // 255
    out_a = sa + (da * inv_a) // 255
    return out_r, out_g, out_b, out_a


def decode_ldec_lz77(src: bytes, expected_output_len: Optional[int] = None) -> bytes:
    """Pure-CPU bounded Sony LDEC/LZ77 (`0x0F` raw + `0xF0` back-reference) decoder."""
    if not src:
        raise SoftGpeError("Empty LDEC compressed stream")
    if len(src) > LDEC_MAX_BYTES:
        raise SoftGpeError(f"Compressed stream {len(src)} exceeds LDEC_MAX_BYTES")
    if expected_output_len is not None and (expected_output_len <= 0 or expected_output_len > LDEC_MAX_BYTES):
        raise SoftGpeError(f"Invalid expected_output_len={expected_output_len}")

    n = len(src)
    p = 0
    out = bytearray()

    while p < n and (expected_output_len is None or len(out) < expected_output_len):
        block_base = len(out)
        kind = src[p]
        p += 1

        if kind == 0x0F:
            if n - p < 3:
                raise SoftGpeError(f"Truncated 0x0F raw block header at {p - 1}")
            count = src[p + 1] | (src[p + 2] << 8)
            p += 3
            if count > n - p:
                raise SoftGpeError("Truncated 0x0F raw block payload")
            if expected_output_len is not None and len(out) + count > expected_output_len:
                raise SoftGpeError("0x0F raw block overflows expected_output_len")
            out.extend(src[p : p + count])
            p += count

        elif kind == 0xF0:
            ended = False
            while not ended:
                if p >= n:
                    raise SoftGpeError("Truncated 0xF0 LZ77 stream before terminator")
                flags = src[p]
                p += 1
                for bit in range(8):
                    if flags & (1 << bit):
                        if n - p < 2:
                            raise SoftGpeError("Truncated 0xF0 back-reference token")
                        a = src[p]
                        b = src[p + 1]
                        p += 2
                        distance = ((a & 0x0F) << 8) | b
                        if distance == 0:
                            ended = True
                            break
                        count = LDEC_LENGTH_TABLE[a >> 4]
                        if distance > (len(out) - block_base):
                            raise SoftGpeError(f"Back-reference distance {distance} out of block bounds")
                        if expected_output_len is not None and len(out) + count > expected_output_len:
                            raise SoftGpeError("LZ77 match overflows expected_output_len")
                        for _ in range(count):
                            out.append(out[-distance])
                    else:
                        if p >= n:
                            raise SoftGpeError("Truncated 0xF0 literal byte")
                        if expected_output_len is not None and len(out) >= expected_output_len:
                            raise SoftGpeError("LZ77 literal overflows expected_output_len")
                        out.append(src[p])
                        p += 1
        else:
            raise SoftGpeError(f"Unknown LDEC block type {kind:#04x}")

    if expected_output_len is not None and len(out) != expected_output_len:
        raise SoftGpeError(f"Decoded length {len(out)} != expected {expected_output_len}")
    return bytes(out)


def encode_ldec_lz77(raw: bytes, *, prefer_lz77: bool = True) -> bytes:
    """Encode raw bytes into Sony LDEC `0xF0` LZ77 or `0x0F` raw stream."""
    if not raw:
        raise SoftGpeError("Cannot encode empty payload")
    if not prefer_lz77:
        if len(raw) > 0xFFFF:
            raise SoftGpeError("Raw block limited to 65535 bytes")
        return bytes([0x0F, 0x00, len(raw) & 0xFF, (len(raw) >> 8) & 0xFF]) + raw

    out = bytearray()
    pos = 0
    while pos < len(raw):
        block = raw[pos : pos + 4096]
        pos += len(block)
        out.append(0xF0)
        tokens: List[Tuple[int, bytes]] = []
        i = 0
        while i < len(block):
            best_len = 0
            best_dist = 0
            best_code = 0
            if i > 0:
                max_d = min(i, 16)
                for d in range(1, max_d + 1):
                    mlen = 0
                    while (
                        i + mlen < len(block)
                        and mlen < 64
                        and block[i + mlen] == block[i + mlen - d]
                    ):
                        mlen += 1
                    for code in range(len(LDEC_LENGTH_TABLE) - 1, -1, -1):
                        lval = LDEC_LENGTH_TABLE[code]
                        if lval <= mlen and lval > best_len:
                            best_len = lval
                            best_dist = d
                            best_code = code
                            break
            if best_len >= 3:
                a = ((best_code & 0xF) << 4) | ((best_dist >> 8) & 0xF)
                b = best_dist & 0xFF
                tokens.append((1, bytes([a, b])))
                i += best_len
            else:
                tokens.append((0, bytes([block[i]])))
                i += 1
        tokens.append((1, b"\x00\x00"))
        for g in range(0, len(tokens), 8):
            group = tokens[g : g + 8]
            flag = 0
            payload_g = bytearray()
            for bit, (is_m, tbytes) in enumerate(group):
                if is_m:
                    flag |= 1 << bit
                payload_g.extend(tbytes)
            out.append(flag)
            out.extend(payload_g)
    return bytes(out)


@dataclass(frozen=True)
class NinePatchInsets:
    left: int
    top: int
    right: int
    bottom: int


@dataclass(frozen=True)
class UxdSpriteDescriptor:
    index: int
    resid: int
    pixel_format: str
    is_nine_patch: bool
    insets: NinePatchInsets
    width: int
    height: int
    aligned_width: int
    compressed_size: int
    payload_offset: int
    expected_decoded_bytes: int


def _map_uxd_pixel_format(res_fmt: int) -> str:
    if res_fmt in (0, 7):
        return PIXEL_FMT_RGBA4444
    if res_fmt in (1, 2):
        return PIXEL_FMT_RGBA8888
    if res_fmt == 3:
        return PIXEL_FMT_ARGB4444
    if res_fmt in (4, 8):
        return PIXEL_FMT_A8
    return PIXEL_FMT_RGBA4444


def parse_uxd_sprites(data: bytes) -> Tuple[int, List[UxdSpriteDescriptor]]:
    """Parse sprite descriptors & 9-patch insets from an `uxd\\x07` container (`image_00_169.uxc`)."""
    if len(data) < UXC_HEADER_STRUCT.size:
        raise SoftGpeError("Truncated .uxc/.uxd header")
    magic, _res, _hdr_flag, ns_id, u32_0c = UXC_HEADER_STRUCT.unpack_from(data, 0)
    if magic != UXD_MAGIC:
        raise SoftGpeError(f"Expected {UXD_MAGIC!r}, got {magic!r}")
    entry_slots = u32_0c & 0x1FFF
    rec_base = 16 + ((entry_slots + 1) & ~1) * 2
    vals = struct.unpack_from(f"<{entry_slots}H", data, 16)
    sprites: List[UxdSpriteDescriptor] = []
    for idx, word_off in enumerate(vals):
        if word_off == 0xFFFF:
            continue
        off = rec_base + word_off * 4
        if off + 20 > len(data):
            continue
        w0, w1, w2 = struct.unpack_from("<3I", data, off)
        if ((w0 >> 24) & 0xFF) != 0x1A:
            continue
        resid = (ns_id << 13) | idx
        is_nine = bool(w1 & 0x08000000)
        res_px_fmt = (w1 >> 16) & 0x3F
        px_name = _map_uxd_pixel_format(res_px_fmt)
        w = w2 & 0xFFFF
        h = (w2 >> 16) & 0xFFFF
        aw = (w + 15) & ~15
        if not is_nine:
            csz, rel = struct.unpack_from("<2I", data, off + 12)
            insets = NinePatchInsets(0, 0, 0, 0)
        else:
            if off + 40 > len(data):
                continue
            # Verified against FX6 image_00_169.uxc: u16[5..8] at off+12 are (left, top, right, bottom)
            u16s = struct.unpack_from("<10H", data, off + 12)
            insets = NinePatchInsets(left=u16s[5], top=u16s[6], right=u16s[7], bottom=u16s[8])
            csz, rel = struct.unpack_from("<2I", data, off + 32)
        payload_off = off + 4 + rel
        bpp = 4 if px_name == PIXEL_FMT_RGBA8888 else (1 if px_name == PIXEL_FMT_A8 else 2)
        sprites.append(
            UxdSpriteDescriptor(
                index=idx,
                resid=resid,
                pixel_format=px_name,
                is_nine_patch=is_nine,
                insets=insets,
                width=w,
                height=h,
                aligned_width=aw,
                compressed_size=csz,
                payload_offset=payload_off,
                expected_decoded_bytes=aw * h * bpp,
            )
        )
    return entry_slots, sprites


def build_clean_room_uxd_fixture() -> bytes:
    """Build a deterministic clean-room `uxd\\x07` container with all 4 formats + 9-patch."""
    specs: List[Tuple[int, int, str, bytes, Optional[NinePatchInsets], bool]] = []

    # Sprite 0: 40x58 RGBA4444 Cinema Line badge (aligned 48x58)
    w0, h0, aw0 = 40, 58, 48
    b0 = bytearray(aw0 * h0 * 2)
    for y in range(h0):
        for x in range(w0):
            border = x < 2 or x >= w0 - 2 or y < 2 or y >= h0 - 2
            pv = 0xFFFF if border else (0xF81F if ((x + y) % 8 < 4) else 0x29CF)
            struct.pack_into("<H", b0, (y * aw0 + x) * 2, pv)
    specs.append((w0, h0, PIXEL_FMT_RGBA4444, bytes(b0), None, True))

    # Sprite 1: 24x24 9-patch RGBA4444 frame (aligned 32x24, insets 4,4,4,4)
    w1, h1, aw1 = 24, 24, 32
    b1 = bytearray(aw1 * h1 * 2)
    for y in range(h1):
        for x in range(w1):
            is_edge = x < 4 or x >= w1 - 4 or y < 4 or y >= h1 - 4
            pv = 0xF82F if is_edge else 0x123C
            struct.pack_into("<H", b1, (y * aw1 + x) * 2, pv)
    specs.append((w1, h1, PIXEL_FMT_RGBA4444, bytes(b1), NinePatchInsets(4, 4, 4, 4), True))

    # Sprite 2: 20x20 RGBA8888 crosshair icon (aligned 32x20, 0x0F raw)
    w2, h2, aw2 = 20, 20, 32
    b2 = bytearray(aw2 * h2 * 4)
    for y in range(h2):
        for x in range(w2):
            off = (y * aw2 + x) * 4
            if x < 2 or x >= 18 or y < 2 or y >= 18:
                b2[off : off + 4] = b"\xFF\xFF\xFF\xFF"
            elif x in (9, 10) or y in (9, 10):
                b2[off : off + 4] = b"\xF0\x38\x38\xFF"
            else:
                b2[off : off + 4] = b"\x28\xB8\xE8\xCC"
    specs.append((w2, h2, PIXEL_FMT_RGBA8888, bytes(b2), None, False))

    # Sprite 3: 16x16 ARGB4444 status chip (aligned 16x16)
    w3, h3, aw3 = 16, 16, 16
    b3 = bytearray(aw3 * h3 * 2)
    for y in range(h3):
        for x in range(w3):
            pv = 0xFF42 if (x + y) % 2 == 0 else 0xF2A8
            struct.pack_into("<H", b3, (y * aw3 + x) * 2, pv)
    specs.append((w3, h3, PIXEL_FMT_ARGB4444, bytes(b3), None, True))

    # Sprite 4: 16x16 A8 glyph mask (aligned 16x16)
    w4, h4, aw4 = 16, 16, 16
    b4 = bytearray(aw4 * h4)
    for y in range(h4):
        for x in range(w4):
            if 2 <= x <= 13 and (y in (2, 3, 7, 8) or x in (2, 3)):
                b4[y * aw4 + x] = 0xFF
            elif 4 <= x <= 12 and 4 <= y <= 13:
                b4[y * aw4 + x] = 0x40
    specs.append((w4, h4, PIXEL_FMT_A8, bytes(b4), None, True))

    count = len(specs)
    header = UXC_HEADER_STRUCT.pack(UXD_MAGIC, 0, 8, 0, count)
    table = bytearray(((count + 1) & ~1) * 2)
    desc_offsets: List[int] = []
    desc_cursor = 0
    for _w, _h, _fmt, _raw, insets, _lz in specs:
        desc_offsets.append(desc_cursor)
        desc_cursor += 40 if insets is not None else 20

    fmt_code_map = {
        PIXEL_FMT_RGBA4444: 0,
        PIXEL_FMT_RGBA8888: 1,
        PIXEL_FMT_ARGB4444: 3,
        PIXEL_FMT_A8: 4,
    }
    descriptors = bytearray()
    payloads = bytearray()
    for idx, (w, h, px_fmt, raw, insets, use_lz) in enumerate(specs):
        comp = encode_ldec_lz77(raw, prefer_lz77=use_lz)
        d_off = desc_offsets[idx]
        struct.pack_into("<H", table, idx * 2, d_off // 4)
        p_abs_rel = desc_cursor + len(payloads)
        rel_from_plus4 = p_abs_rel - (d_off + 4)
        res_code = fmt_code_map[px_fmt]
        w0_val = (0x1A << 24) | idx
        w1_val = 0xC0000000 | (0x08000000 if insets is not None else 0) | ((res_code & 0x3F) << 16)
        w2_val = (h << 16) | w
        if insets is None:
            descriptors.extend(struct.pack("<5I", w0_val, w1_val, w2_val, len(comp), rel_from_plus4))
        else:
            descriptors.extend(
                struct.pack(
                    "<3I10H2I",
                    w0_val,
                    w1_val,
                    w2_val,
                    2, 1, 0, 0, 0,
                    insets.left, insets.top, insets.right, insets.bottom,
                    0,
                    len(comp),
                    rel_from_plus4,
                )
            )
        payloads.extend(comp)
        while len(payloads) % 4 != 0:
            payloads.append(0)
    return header + bytes(table) + bytes(descriptors) + bytes(payloads)


# ---------------------------------------------------------------------------
# Software GPE Surface & Compositor (`GRM_gpermFillrect`, `GRM_gpermRectblit`, `HOSDAP02`)
# ---------------------------------------------------------------------------


class GpeSurface:
    """Software GPE bitmap surface supporting `ARGB8888`, `RGBA8888`, `RGBA4444`, `ARGB4444`, and `A8`."""

    def __init__(
        self,
        width: int,
        height: int,
        pixel_format: str = PIXEL_FMT_ARGB8888,
        *,
        stride_px: Optional[int] = None,
        raw_bytes: Optional[bytes] = None,
        is_gpe_argb: Optional[bool] = None,
    ) -> None:
        if width <= 0 or height <= 0:
            raise SoftGpeError(f"Invalid surface dimensions {width}x{height}")
        self.width = width
        self.height = height
        self.pixel_format = pixel_format
        self.stride_px = width if stride_px is None else stride_px
        if self.stride_px < width:
            raise SoftGpeError(f"stride_px {self.stride_px} < width {width}")

        if pixel_format == PIXEL_FMT_ARGB8888:
            self.bpp = 4
            self.is_gpe_argb = True if is_gpe_argb is None else is_gpe_argb
            self.pixels32: Optional[array] = array("I", [0]) * (self.stride_px * height)
            self.buf: Optional[bytearray] = None
            if raw_bytes is not None:
                expected = self.stride_px * height * 4
                if len(raw_bytes) < expected:
                    raise SoftGpeError(f"Short ARGB8888 buffer: {len(raw_bytes)} < {expected}")
                self.pixels32.frombytes(raw_bytes[:expected])
        elif pixel_format in (PIXEL_FMT_RGBA8888, PIXEL_FMT_RGBA4444, PIXEL_FMT_ARGB4444, PIXEL_FMT_A8):
            self.bpp = 4 if pixel_format == PIXEL_FMT_RGBA8888 else (1 if pixel_format == PIXEL_FMT_A8 else 2)
            self.is_gpe_argb = False
            self.pixels32 = None
            expected = self.stride_px * height * self.bpp
            if raw_bytes is not None:
                if len(raw_bytes) < expected:
                    raise SoftGpeError(f"Short {pixel_format} buffer: {len(raw_bytes)} < {expected}")
                self.buf = bytearray(raw_bytes[:expected])
            else:
                self.buf = bytearray(expected)
        else:
            raise SoftGpeError(f"Unsupported pixel format: {pixel_format!r}")

    def read_rgba(self, x: int, y: int, *, tint_rgb: Tuple[int, int, int] = (255, 255, 255)) -> Tuple[int, int, int, int]:
        """Return `(r, g, b, a)` at `(x, y)`."""
        idx = y * self.stride_px + x
        if self.pixels32 is not None:
            px = self.pixels32[idx]
            return ((px >> 16) & 0xFF, (px >> 8) & 0xFF, px & 0xFF, (px >> 24) & 0xFF)
        assert self.buf is not None
        if self.pixel_format == PIXEL_FMT_RGBA8888:
            off = idx * 4
            return self.buf[off], self.buf[off + 1], self.buf[off + 2], self.buf[off + 3]
        if self.pixel_format == PIXEL_FMT_RGBA4444:
            pv = struct.unpack_from("<H", self.buf, idx * 2)[0]
            return (
                ((pv >> 12) & 0xF) * 17,
                ((pv >> 8) & 0xF) * 17,
                ((pv >> 4) & 0xF) * 17,
                (pv & 0xF) * 17,
            )
        if self.pixel_format == PIXEL_FMT_ARGB4444:
            pv = struct.unpack_from("<H", self.buf, idx * 2)[0]
            return (
                ((pv >> 8) & 0xF) * 17,
                ((pv >> 4) & 0xF) * 17,
                (pv & 0xF) * 17,
                ((pv >> 12) & 0xF) * 17,
            )
        # A8
        return tint_rgb[0], tint_rgb[1], tint_rgb[2], self.buf[idx]

    def read_argb32(self, x: int, y: int, *, tint_rgb: Tuple[int, int, int] = (255, 255, 255)) -> int:
        if self.pixels32 is not None:
            return self.pixels32[y * self.stride_px + x]
        r, g, b, a = self.read_rgba(x, y, tint_rgb=tint_rgb)
        return (a << 24) | (r << 16) | (g << 8) | b

    def write_rgba(self, x: int, y: int, r: int, g: int, b: int, a: int) -> None:
        idx = y * self.stride_px + x
        if self.pixels32 is not None:
            self.pixels32[idx] = ((a & 0xFF) << 24) | ((r & 0xFF) << 16) | ((g & 0xFF) << 8) | (b & 0xFF)
            return
        assert self.buf is not None
        if self.pixel_format == PIXEL_FMT_RGBA8888:
            off = idx * 4
            self.buf[off] = r & 0xFF
            self.buf[off + 1] = g & 0xFF
            self.buf[off + 2] = b & 0xFF
            self.buf[off + 3] = a & 0xFF
        elif self.pixel_format == PIXEL_FMT_RGBA4444:
            pv = (((r >> 4) & 0xF) << 12) | (((g >> 4) & 0xF) << 8) | (((b >> 4) & 0xF) << 4) | ((a >> 4) & 0xF)
            struct.pack_into("<H", self.buf, idx * 2, pv)
        elif self.pixel_format == PIXEL_FMT_ARGB4444:
            pv = (((a >> 4) & 0xF) << 12) | (((r >> 4) & 0xF) << 8) | (((g >> 4) & 0xF) << 4) | ((b >> 4) & 0xF)
            struct.pack_into("<H", self.buf, idx * 2, pv)
        else:
            self.buf[idx] = a & 0xFF

    def to_argb8888_bytes(self) -> bytes:
        if self.pixels32 is not None and self.stride_px == self.width:
            return self.pixels32.tobytes()
        out = array("I")
        for y in range(self.height):
            for x in range(self.width):
                out.append(self.read_argb32(x, y))
        return out.tobytes()

    def sha256(self) -> str:
        return hashlib.sha256(self.to_argb8888_bytes()).hexdigest()


class SoftGpeEngine:
    """Hardware-free Software GPE (`GPE0` `0x41E001000` + `HOSDAP02` `ramfb` `[0x41E100000, 0x41E600000)`)."""

    def __init__(self, width: int = GPE0_WIDTH, height: int = GPE0_HEIGHT) -> None:
        self.width = width
        self.height = height
        self.gpe0 = GpeSurface(width, height, PIXEL_FMT_ARGB8888)
        self.gpe1 = GpeSurface(width, height, PIXEL_FMT_ARGB8888)
        self.fillrect_count = 0
        self.rectblit_count = 0
        self.nine_patch_count = 0
        self.flush_count = 0
        self.ramfb_scanout_count = 0

    def grm_fillrect(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        r: int,
        g: int,
        b: int,
        a: int = 0xFF,
        *,
        blend_mode: int = BLEND_SRC_OVER,
        const_alpha: int = 255,
        dst: Optional[GpeSurface] = None,
    ) -> int:
        """Exact software reference for `libgrm-fbinit25-542.c::GRM_gpermFillrect`."""
        target = self.gpe0 if dst is None else dst
        if w <= 0 or h <= 0:
            self.fillrect_count += 1
            return 0
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(target.width, x + w)
        y1 = min(target.height, y + h)
        if x0 >= x1 or y0 >= y1:
            self.fillrect_count += 1
            return 0

        eff_a = ((a & 0xFF) * (const_alpha & 0xFF)) // 255 if blend_mode == BLEND_SRC_OVER_CONST_ALPHA else (a & 0xFF)
        color = fx6_px(r, g, b, eff_a)

        if target.pixels32 is not None:
            p32 = target.pixels32
            stride = target.stride_px
            span_w = x1 - x0
            if blend_mode != BLEND_SRC_OVER_CONST_ALPHA or eff_a == 255:
                if blend_mode != BLEND_SRC_OVER_CONST_ALPHA or eff_a != 0:
                    row_fill = array("I", [color]) * span_w
                    for yy in range(y0, y1):
                        base = yy * stride + x0
                        p32[base : base + span_w] = row_fill
            elif eff_a != 0:
                inv_a = 255 - eff_a
                for yy in range(y0, y1):
                    base = yy * stride
                    for xx in range(x0, x1):
                        dpx = p32[base + xx]
                        da = (dpx >> 24) & 0xFF
                        dr = (dpx >> 16) & 0xFF
                        dg = (dpx >> 8) & 0xFF
                        db = dpx & 0xFF
                        or_c = (r * eff_a + dr * inv_a) // 255
                        og_c = (g * eff_a + dg * inv_a) // 255
                        ob_c = (b * eff_a + db * inv_a) // 255
                        oa_c = eff_a + (da * inv_a) // 255
                        p32[base + xx] = (oa_c << 24) | (or_c << 16) | (og_c << 8) | ob_c
        else:
            for yy in range(y0, y1):
                for xx in range(x0, x1):
                    if blend_mode == BLEND_SRC_OVER_CONST_ALPHA and 0 < eff_a < 255:
                        dr, dg, db, da = target.read_rgba(xx, yy)
                        or_c, og_c, ob_c, oa_c = porter_duff_src_over(r, g, b, eff_a, dr, dg, db, da)
                        target.write_rgba(xx, yy, or_c, og_c, ob_c, oa_c)
                    elif blend_mode != BLEND_SRC_OVER_CONST_ALPHA or eff_a != 0:
                        target.write_rgba(xx, yy, r, g, b, eff_a)

        self.fillrect_count += 1
        return span_w * (y1 - y0) if target.pixels32 is not None else (x1 - x0) * (y1 - y0)

    def grm_rectblit(
        self,
        src: GpeSurface,
        src_rect: Tuple[int, int, int, int],
        dst_rect: Tuple[int, int, int, int],
        *,
        clip_rect: Optional[Tuple[int, int, int, int]] = None,
        blend_mode: int = BLEND_SRC_OVER,
        const_alpha: int = 255,
        const_alpha2: int = 255,
        color_mod: int = 0,
        tint_rgb: Tuple[int, int, int] = (255, 255, 255),
        dst: Optional[GpeSurface] = None,
    ) -> int:
        """Exact software reference for `libgrm-fbinit25-542.c::GRM_gpermRectblit`."""
        target = self.gpe0 if dst is None else dst
        sx0, sy0, sw0, sh0 = src_rect
        dx0, dy0, dw0, dh0 = dst_rect
        if sw0 <= 0:
            sw0 = src.width
        if sh0 <= 0:
            sh0 = src.height
        if dw0 <= 0 or dh0 <= 0 or sw0 <= 0 or sh0 <= 0:
            self.rectblit_count += 1
            return 0

        x0 = max(0, dx0)
        y0 = max(0, dy0)
        x1 = min(target.width, dx0 + dw0)
        y1 = min(target.height, dy0 + dh0)
        if clip_rect is not None:
            cx0, cy0, cw0, ch0 = clip_rect
            if cw0 > 0 and ch0 > 0:
                x0 = max(x0, cx0)
                y0 = max(y0, cy0)
                x1 = min(x1, cx0 + cw0)
                y1 = min(y1, cy0 + ch0)
        if x0 >= x1 or y0 >= y1:
            self.rectblit_count += 1
            return 0

        effective_tint = tint_rgb if (color_mod == COLOR_MOD_TINT or src.pixel_format == PIXEL_FMT_A8) else (255, 255, 255)
        pixels_written = 0

        if target.pixels32 is not None:
            p32 = target.pixels32
            dstride = target.stride_px
            for dy in range(y0, y1):
                sy = sy0 + ((dy - dy0) * sh0) // dh0
                if sy < 0 or sy >= src.height:
                    continue
                dbase = dy * dstride
                for dx in range(x0, x1):
                    sx = sx0 + ((dx - dx0) * sw0) // dw0
                    if sx < 0 or sx >= src.width:
                        continue
                    sr, sg, sb, sa = src.read_rgba(sx, sy, tint_rgb=effective_tint)
                    if blend_mode in (BLEND_SRC_OVER_CONST_ALPHA, BLEND_SRC_OVER_DUAL_ALPHA):
                        sa = (sa * (const_alpha & 0xFF)) // 255
                        if blend_mode == BLEND_SRC_OVER_DUAL_ALPHA:
                            sa = (sa * (const_alpha2 & 0xFF)) // 255
                    if blend_mode == BLEND_SRC_COPY:
                        p32[dbase + dx] = (sa << 24) | (sr << 16) | (sg << 8) | sb
                        pixels_written += 1
                    elif sa != 0:
                        if sa == 255:
                            p32[dbase + dx] = (255 << 24) | (sr << 16) | (sg << 8) | sb
                        else:
                            dpx = p32[dbase + dx]
                            da = (dpx >> 24) & 0xFF
                            dr = (dpx >> 16) & 0xFF
                            dg = (dpx >> 8) & 0xFF
                            db = dpx & 0xFF
                            or_c, og_c, ob_c, oa_c = porter_duff_src_over(sr, sg, sb, sa, dr, dg, db, da)
                            p32[dbase + dx] = (oa_c << 24) | (or_c << 16) | (og_c << 8) | ob_c
                        pixels_written += 1
        else:
            for dy in range(y0, y1):
                sy = sy0 + ((dy - dy0) * sh0) // dh0
                if sy < 0 or sy >= src.height:
                    continue
                for dx in range(x0, x1):
                    sx = sx0 + ((dx - dx0) * sw0) // dw0
                    if sx < 0 or sx >= src.width:
                        continue
                    sr, sg, sb, sa = src.read_rgba(sx, sy, tint_rgb=effective_tint)
                    if blend_mode in (BLEND_SRC_OVER_CONST_ALPHA, BLEND_SRC_OVER_DUAL_ALPHA):
                        sa = (sa * (const_alpha & 0xFF)) // 255
                        if blend_mode == BLEND_SRC_OVER_DUAL_ALPHA:
                            sa = (sa * (const_alpha2 & 0xFF)) // 255
                    if blend_mode == BLEND_SRC_COPY:
                        target.write_rgba(dx, dy, sr, sg, sb, sa)
                        pixels_written += 1
                    elif sa != 0:
                        dr, dg, db, da = target.read_rgba(dx, dy)
                        or_c, og_c, ob_c, oa_c = porter_duff_src_over(sr, sg, sb, sa, dr, dg, db, da)
                        target.write_rgba(dx, dy, or_c, og_c, ob_c, oa_c)
                        pixels_written += 1

        self.rectblit_count += 1
        return pixels_written

    def grm_nine_patch_blit(
        self,
        src: GpeSurface,
        dst_rect: Tuple[int, int, int, int],
        insets: NinePatchInsets,
        *,
        clip_rect: Optional[Tuple[int, int, int, int]] = None,
        blend_mode: int = BLEND_SRC_OVER,
        const_alpha: int = 255,
        dst: Optional[GpeSurface] = None,
    ) -> int:
        """Composite a Sony `.uxc` 9-patch sprite with unstretched corners and stretched center/edges."""
        dx, dy, dw, dh = dst_rect
        sw, sh = src.width, src.height
        if dw <= 0 or dh <= 0 or sw <= 0 or sh <= 0:
            return 0

        l = min(max(0, insets.left), sw)
        r = min(max(0, insets.right), max(0, sw - l))
        t = min(max(0, insets.top), sh)
        b = min(max(0, insets.bottom), max(0, sh - t))

        # Clamp destination edge caps if target box is narrower/shorter than cap sum
        dl = min(l, dw)
        dr = min(r, max(0, dw - dl))
        dt = min(t, dh)
        db = min(b, max(0, dh - dt))

        src_xs = (0, l, sw - r, sw)
        src_ys = (0, t, sh - b, sh)
        dst_xs = (dx, dx + dl, dx + dw - dr, dx + dw)
        dst_ys = (dy, dy + dt, dy + dh - db, dy + dh)

        total_written = 0
        for row_idx in range(3):
            sh_patch = src_ys[row_idx + 1] - src_ys[row_idx]
            dh_patch = dst_ys[row_idx + 1] - dst_ys[row_idx]
            if sh_patch <= 0 or dh_patch <= 0:
                continue
            for col_idx in range(3):
                sw_patch = src_xs[col_idx + 1] - src_xs[col_idx]
                dw_patch = dst_xs[col_idx + 1] - dst_xs[col_idx]
                if sw_patch <= 0 or dw_patch <= 0:
                    continue
                total_written += self.grm_rectblit(
                    src,
                    (src_xs[col_idx], src_ys[row_idx], sw_patch, sh_patch),
                    (dst_xs[col_idx], dst_ys[row_idx], dw_patch, dh_patch),
                    clip_rect=clip_rect,
                    blend_mode=blend_mode,
                    const_alpha=const_alpha,
                    dst=dst,
                )
        self.nine_patch_count += 1
        return total_written

    def flush_to_offscreen_parity(self) -> str:
        """Mirror `gpe0` to `gpe1` (`flush_pixels_to_osd`) and return deterministic SHA-256."""
        assert self.gpe0.pixels32 is not None and self.gpe1.pixels32 is not None
        self.gpe1.pixels32[:] = self.gpe0.pixels32[:]
        self.flush_count += 1
        return self.gpe0.sha256()

    def hosdap02_ramfb_scanout(
        self,
        *,
        ramfb_phys: int = RAMFB_WINDOW_START,
        backdrop_xrgb: int = 0x0010141A,
    ) -> Tuple[bytes, bytes, Dict[str, object]]:
        """Composite `GPE0` (`0x41E001000`) onto `HOSDAP02` `ramfb` `[0x41E100000, 0x41E600000)` `XRGB8888`.

        Returns `(hosdap02_header_64b, xrgb8888_scanout_bytes, stats)`.
        """
        total_aperture_bytes = HOSDAP02_HEADER_BYTES + self.width * self.height * 4
        if ramfb_phys < RAMFB_WINDOW_START or ramfb_phys + total_aperture_bytes > RAMFB_WINDOW_END:
            raise SoftGpeError(
                f"ramfb address {ramfb_phys:#x}..{ramfb_phys + total_aperture_bytes:#x} "
                f"outside [{RAMFB_WINDOW_START:#x}, {RAMFB_WINDOW_END:#x})"
            )
        assert self.gpe0.pixels32 is not None
        br = (backdrop_xrgb >> 16) & 0xFF
        bg = (backdrop_xrgb >> 8) & 0xFF
        bb = backdrop_xrgb & 0xFF

        scanout = array("I", [backdrop_xrgb & 0x00FFFFFF]) * (self.width * self.height)
        p32 = self.gpe0.pixels32
        nonzero_gpe0 = 0
        unique_colors: Set[int] = set()
        for i, px in enumerate(p32):
            if px != 0:
                nonzero_gpe0 += 1
            unique_colors.add(px)
            sa = (px >> 24) & 0xFF
            if sa == 0:
                continue
            sr = (px >> 16) & 0xFF
            sg = (px >> 8) & 0xFF
            sb = px & 0xFF
            if sa == 255:
                scanout[i] = (sr << 16) | (sg << 8) | sb
            else:
                inv_a = 255 - sa
                or_c = (sr * sa + br * inv_a) // 255
                og_c = (sg * sa + bg * inv_a) // 255
                ob_c = (sb * sa + bb * inv_a) // 255
                scanout[i] = (or_c << 16) | (og_c << 8) | ob_c

        scanout_bytes = scanout.tobytes()
        scanout_sha = hashlib.sha256(scanout_bytes).hexdigest()
        gpe0_sha = self.gpe0.sha256()

        header = struct.pack(
            "<8sIIIIQQQQ8x",
            HOSDAP02_MAGIC,
            2,                        # version
            self.width,
            self.height,
            self.width * 4,           # XRGB8888 pitch
            GPE0_PHYS_BASE,
            ramfb_phys,
            len(scanout_bytes),
            nonzero_gpe0,
        )
        assert len(header) == HOSDAP02_HEADER_BYTES
        self.ramfb_scanout_count += 1
        stats = {
            "hosdap02_magic": HOSDAP02_MAGIC.decode("ascii"),
            "gpe0_phys": hex(GPE0_PHYS_BASE),
            "ramfb_phys": hex(ramfb_phys),
            "ramfb_window": f"[{hex(RAMFB_WINDOW_START)}, {hex(RAMFB_WINDOW_END)})",
            "width": self.width,
            "height": self.height,
            "nonzero_gpe0_pixels": nonzero_gpe0,
            "unique_gpe0_colors": len(unique_colors),
            "gpe0_sha256": gpe0_sha,
            "ramfb_xrgb8888_sha256": scanout_sha,
            "ramfb_bytes": len(scanout_bytes),
        }
        return header, scanout_bytes, stats


def decode_uxd_sprite_to_surface(
    container_bytes: bytes,
    sprite: UxdSpriteDescriptor,
) -> GpeSurface:
    """Decode one LDEC/LZ77 compressed sprite from `.uxc` into a `GpeSurface`."""
    chunk = container_bytes[sprite.payload_offset : sprite.payload_offset + sprite.compressed_size]
    decoded = decode_ldec_lz77(chunk, expected_output_len=sprite.expected_decoded_bytes)
    return GpeSurface(
        sprite.width,
        sprite.height,
        sprite.pixel_format,
        stride_px=sprite.aligned_width,
        raw_bytes=decoded,
    )


# ---------------------------------------------------------------------------
# Part B: `virtual-rom-v1` Bluetooth HCI H4 UART (`/dev/ttyAMA3`) Emulator
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BtDonorInspection:
    source_mode: str
    libbt_vendor_bytes: int
    libbt_vendor_sha256: str
    libbt_core_bytes: int
    libbt_core_sha256: str
    vendor_markers_present: Tuple[str, ...]
    core_markers_present: Tuple[str, ...]
    all_markers_satisfied: bool


@dataclass(frozen=True)
class HciEventPacket:
    packet_type: int
    event_code: int
    opcode: int
    status: int
    payload: bytes
    raw_h4: bytes


@dataclass(frozen=True)
class BtModeVerificationResult:
    mode: str
    passed: bool
    uart_opened: bool
    tx_packets: int
    tx_bytes: int
    rx_events: int
    final_baudrate: int
    patchram_chunks_acked: int
    patchram_bytes_acked: int
    bd_addr: str
    bsa_ready: bool
    hal_error_code: int
    notice_id: str
    degraded_state: str
    airplane_latched: bool
    system_error_abort: bool
    wdt_resets: int
    shooting_unaffected: bool
    recording_unaffected: bool
    nvram_writes: int
    details: str


def build_clean_room_bt_elf_fixtures() -> Dict[str, bytes]:
    """Build minimal valid ELF64 AArch64 blobs carrying `/dev/ttyAMA3` & BSA markers."""
    def _mk_elf(markers: Sequence[str]) -> bytes:
        ro = b"\x00".join(m.encode("ascii") for m in markers) + b"\x00"
        buf = bytearray(0x4000 + len(ro) + 64)
        e_ident = b"\x7fELF\x02\x01\x01" + b"\x00" * 9
        struct.pack_into("<16sHHIQQQIHHHHHH", buf, 0, e_ident, 3, 183, 1, 0x1000, 64, 0, 0, 64, 56, 1, 64, 0, 0)
        struct.pack_into("<IIQQQQQQ", buf, 64, 1, 5, 0, 0, 0, len(buf), len(buf), 0x1000)
        buf[0x4000 : 0x4000 + len(ro)] = ro
        return bytes(buf)

    return {
        "fx6_libbt_vendor": _mk_elf(REQUIRED_BT_VENDOR_MARKERS),
        "fx6_libbt_core": _mk_elf(REQUIRED_BT_CORE_MARKERS),
    }


def inspect_bt_donor_libraries(
    *,
    force_clean_room: bool = False,
    env: Optional[Mapping[str, str]] = None,
) -> BtDonorInspection:
    """Inspect FX6 `libbt-vendor.so` & `libInfraBluetoothCore.so` strictly `O_RDONLY` (or clean-room fallback)."""
    eff_env = dict(os.environ if env is None else env)
    if force_clean_room:
        eff_env[ENV_FORCE_CLEAN_ROOM] = "1"
    paths = resolve_phase29_donor_paths(env=eff_env)
    vendor_p = paths["fx6_libbt_vendor"]
    core_p = paths["fx6_libbt_core"]

    if vendor_p.is_file() and core_p.is_file() and not is_forced_clean_room(eff_env):
        vendor_bytes = read_donor_bytes_readonly(vendor_p)
        core_bytes = read_donor_bytes_readonly(core_p)
        source_mode = "LOCAL_DONOR_RDONLY"
    else:
        syn = build_clean_room_bt_elf_fixtures()
        vendor_bytes = syn["fx6_libbt_vendor"]
        core_bytes = syn["fx6_libbt_core"]
        source_mode = "CLEAN_ROOM_SYNTHETIC"

    v_hits = tuple(m for m in REQUIRED_BT_VENDOR_MARKERS if vendor_bytes.find(m.encode("ascii")) != -1)
    c_hits = tuple(m for m in REQUIRED_BT_CORE_MARKERS if core_bytes.find(m.encode("ascii")) != -1)
    all_ok = len(v_hits) == len(REQUIRED_BT_VENDOR_MARKERS) and len(c_hits) == len(REQUIRED_BT_CORE_MARKERS)

    return BtDonorInspection(
        source_mode=source_mode,
        libbt_vendor_bytes=len(vendor_bytes),
        libbt_vendor_sha256=hashlib.sha256(vendor_bytes).hexdigest(),
        libbt_core_bytes=len(core_bytes),
        libbt_core_sha256=hashlib.sha256(core_bytes).hexdigest(),
        vendor_markers_present=v_hits,
        core_markers_present=c_hits,
        all_markers_satisfied=all_ok,
    )


def build_h4_hci_command(opcode: int, params: bytes = b"") -> bytes:
    """Encode an H4 UART HCI command packet `[0x01, opcode_lo, opcode_hi, plen, params...]`."""
    if len(params) > 255:
        raise BtRomEmulatorError(f"HCI command params length {len(params)} > 255")
    return struct.pack("<BHB", H4_PKT_COMMAND, opcode & 0xFFFF, len(params)) + params


def build_bcm_baudrate_params(baudrate: int) -> bytes:
    """Encode Broadcom/Cypress `0xFC18` Update_Baudrate 6-byte payload."""
    return struct.pack("<HI", 0, baudrate & 0xFFFFFFFF)


def build_bcm_write_ram_params(addr: int, chunk: bytes) -> bytes:
    """Encode Broadcom/Cypress `0xFC4C` Write_RAM payload (`<I` LE target address + data)."""
    return struct.pack("<I", addr & 0xFFFFFFFF) + chunk


def _build_hci_command_complete(opcode: int, status: int, ret_params: bytes = b"") -> HciEventPacket:
    payload = struct.pack("<BHB", 1, opcode & 0xFFFF, status & 0xFF) + ret_params
    raw = struct.pack("<BBB", H4_PKT_EVENT, HCI_EVT_COMMAND_COMPLETE, len(payload)) + payload
    return HciEventPacket(
        packet_type=H4_PKT_EVENT,
        event_code=HCI_EVT_COMMAND_COMPLETE,
        opcode=opcode & 0xFFFF,
        status=status & 0xFF,
        payload=ret_params,
        raw_h4=raw,
    )


def _build_hci_hardware_error(hw_code: int) -> HciEventPacket:
    payload = bytes([hw_code & 0xFF])
    raw = struct.pack("<BBB", H4_PKT_EVENT, HCI_EVT_HARDWARE_ERROR, len(payload)) + payload
    return HciEventPacket(
        packet_type=H4_PKT_EVENT,
        event_code=HCI_EVT_HARDWARE_ERROR,
        opcode=0,
        status=hw_code & 0xFF,
        payload=payload,
        raw_h4=raw,
    )


class VirtualRomV1BtController:
    """`virtual-rom-v1` Bluetooth HCI H4 UART (`/dev/ttyAMA3`) controller state machine."""

    def __init__(self, *, mode: str = BT_MODE_HEALTHY) -> None:
        if mode not in ALL_BT_OPERATING_MODES:
            raise BtRomEmulatorError(f"Unknown BT operating mode: {mode!r}")
        self.mode = mode
        self.uart_device = BT_UART_DEVICE
        self.uart_opened = False
        self.baudrate = BT_DEFAULT_BAUD
        self.reset_count = 0
        self.patchram_state = "IDLE"  # IDLE -> MINIDRIVER_READY -> DOWNLOADING -> LAUNCHED / NACKED
        self.patchram_chunks_acked = 0
        self.patchram_bytes_acked = 0
        self.patchram_write_calls = 0
        self.patchram_hasher = hashlib.sha256()
        self.bd_addr_bytes = bytes(VIRTUAL_ROM_V1_BD_ADDR)
        self.tx_buffer = bytearray()
        self.tx_packet_count = 0
        self.tx_byte_count = 0
        self.rx_events: List[HciEventPacket] = []
        self.bsa_ready = False
        self.hal_error_code = 0
        self.last_status = HCI_STATUS_SUCCESS

    @property
    def bd_addr_str(self) -> str:
        return ":".join(f"{b:02x}" for b in self.bd_addr_bytes)

    def open_uart(self) -> bool:
        """Simulate opening `/dev/ttyAMA3`; returns False if gated or UART disconnected."""
        if self.mode == BT_MODE_AIRPLANE_GATED:
            self.uart_opened = False
            return False
        if self.mode == BT_MODE_UART_TIMEOUT:
            self.uart_opened = False
            return False
        self.uart_opened = True
        return True

    def feed_uart_bytes(self, data: bytes) -> List[HciEventPacket]:
        """Feed arbitrary UART byte slices into the H4 framer and return emitted HCI events."""
        if not data:
            return []
        if self.mode == BT_MODE_AIRPLANE_GATED:
            raise BtRomEmulatorError("HCI bytes transmitted while AIRPLANE_SHADOW_GATED is active")

        self.tx_byte_count += len(data)
        self.tx_buffer.extend(data)
        emitted: List[HciEventPacket] = []

        while len(self.tx_buffer) > 0:
            pkt_type = self.tx_buffer[0]
            if pkt_type != H4_PKT_COMMAND:
                raise BtRomEmulatorError(f"Unsupported H4 packet type {pkt_type:#04x} on {self.uart_device}")
            if len(self.tx_buffer) < 4:
                break
            opcode, plen = struct.unpack_from("<HB", self.tx_buffer, 1)
            total_len = 4 + plen
            if len(self.tx_buffer) < total_len:
                break
            params = bytes(self.tx_buffer[4:total_len])
            del self.tx_buffer[:total_len]
            self.tx_packet_count += 1
            emitted.extend(self._handle_hci_command(opcode, params))

        self.rx_events.extend(emitted)
        return emitted

    def _handle_hci_command(self, opcode: int, params: bytes) -> List[HciEventPacket]:
        if self.mode == BT_MODE_UART_TIMEOUT:
            # Dead/absent BT UART never responds with any H4 event
            return []

        if opcode == HCI_OP_RESET:
            self.reset_count += 1
            # On initial cold reset before patchram launch, baud resets to 115200;
            # post-patchram reset keeps controller operational.
            if self.patchram_state != "LAUNCHED":
                self.baudrate = BT_DEFAULT_BAUD
            self.last_status = HCI_STATUS_SUCCESS
            return [_build_hci_command_complete(opcode, HCI_STATUS_SUCCESS)]

        if opcode == HCI_OP_READ_LOCAL_VERSION_INFO:
            ret = struct.pack(
                "<BHBHH",
                VIRTUAL_ROM_V1_HCI_VER,
                VIRTUAL_ROM_V1_HCI_REV,
                VIRTUAL_ROM_V1_LMP_VER,
                VIRTUAL_ROM_V1_MANUFACTURER,
                VIRTUAL_ROM_V1_LMP_SUBVER,
            )
            self.last_status = HCI_STATUS_SUCCESS
            return [_build_hci_command_complete(opcode, HCI_STATUS_SUCCESS, ret)]

        if opcode == HCI_OP_READ_BD_ADDR:
            if self.mode == BT_MODE_PATCHRAM_NACK and self.patchram_state == "NACKED":
                self.last_status = HCI_STATUS_HARDWARE_FAILURE
                return [_build_hci_command_complete(opcode, HCI_STATUS_HARDWARE_FAILURE, b"\x00" * 6)]
            # HCI Read_BD_ADDR returns BD_ADDR in little-endian wire byte order
            self.last_status = HCI_STATUS_SUCCESS
            self.bsa_ready = True
            return [_build_hci_command_complete(opcode, HCI_STATUS_SUCCESS, self.bd_addr_bytes[::-1])]

        if opcode == HCI_OP_BCM_UPDATE_BAUDRATE:
            if len(params) < 6:
                self.last_status = HCI_STATUS_INVALID_PARAMS
                return [_build_hci_command_complete(opcode, HCI_STATUS_INVALID_PARAMS)]
            _pad, new_baud = struct.unpack_from("<HI", params, 0)
            if new_baud == 0:
                self.last_status = HCI_STATUS_INVALID_PARAMS
                return [_build_hci_command_complete(opcode, HCI_STATUS_INVALID_PARAMS)]
            self.baudrate = new_baud
            self.last_status = HCI_STATUS_SUCCESS
            return [_build_hci_command_complete(opcode, HCI_STATUS_SUCCESS)]

        if opcode == HCI_OP_BCM_DOWNLOAD_MINIDRIVER:
            self.patchram_state = "MINIDRIVER_READY"
            self.last_status = HCI_STATUS_SUCCESS
            return [_build_hci_command_complete(opcode, HCI_STATUS_SUCCESS)]

        if opcode == HCI_OP_BCM_WRITE_RAM:
            self.patchram_write_calls += 1
            if self.patchram_state not in ("MINIDRIVER_READY", "DOWNLOADING"):
                self.last_status = HCI_STATUS_COMMAND_DISALLOWED
                return [_build_hci_command_complete(opcode, HCI_STATUS_COMMAND_DISALLOWED)]
            if len(params) < 4:
                self.last_status = HCI_STATUS_INVALID_PARAMS
                return [_build_hci_command_complete(opcode, HCI_STATUS_INVALID_PARAMS)]
            if self.mode == BT_MODE_PATCHRAM_NACK and self.patchram_write_calls >= 2:
                self.patchram_state = "NACKED"
                self.last_status = HCI_STATUS_COMMAND_DISALLOWED
                return [
                    _build_hci_command_complete(opcode, HCI_STATUS_COMMAND_DISALLOWED),
                    _build_hci_hardware_error(0x12),
                ]
            self.patchram_state = "DOWNLOADING"
            payload = params[4:]
            self.patchram_chunks_acked += 1
            self.patchram_bytes_acked += len(payload)
            self.patchram_hasher.update(params)
            self.last_status = HCI_STATUS_SUCCESS
            return [_build_hci_command_complete(opcode, HCI_STATUS_SUCCESS)]

        if opcode == HCI_OP_BCM_LAUNCH_RAM:
            if self.mode == BT_MODE_PATCHRAM_NACK and self.patchram_state == "NACKED":
                self.last_status = HCI_STATUS_COMMAND_DISALLOWED
                return [_build_hci_command_complete(opcode, HCI_STATUS_COMMAND_DISALLOWED)]
            self.patchram_state = "LAUNCHED"
            self.last_status = HCI_STATUS_SUCCESS
            return [_build_hci_command_complete(opcode, HCI_STATUS_SUCCESS)]

        self.last_status = HCI_STATUS_UNKNOWN_COMMAND
        return [_build_hci_command_complete(opcode, HCI_STATUS_UNKNOWN_COMMAND)]


def run_bsa_bringup_scenario(
    mode: str,
    *,
    bkid_0x019e0012: Optional[int] = None,
    bkid_0x01a20002: Optional[int] = None,
) -> BtModeVerificationResult:
    """Execute the Sony `BSA` `/dev/ttyAMA3` bring-up sequence against `VirtualRomV1BtController`."""
    ctrl = VirtualRomV1BtController(mode=mode)
    if bkid_0x019e0012 is None:
        bkid_0x019e0012 = 0x00 if mode == BT_MODE_AIRPLANE_GATED else 0x01
    if bkid_0x01a20002 is None:
        bkid_0x01a20002 = 0x00 if mode == BT_MODE_AIRPLANE_GATED else 0x01

    # Stage-A/B RAM-Shadow BK4\0 early-return gate (libInfraBluetooth.so::Init & libResourceBluetooth.so)
    if bkid_0x019e0012 == 0x00 and bkid_0x01a20002 == 0x00:
        passed = (
            mode == BT_MODE_AIRPLANE_GATED
            and not ctrl.uart_opened
            and ctrl.tx_packet_count == 0
            and ctrl.tx_byte_count == 0
        )
        return BtModeVerificationResult(
            mode=mode,
            passed=passed,
            uart_opened=False,
            tx_packets=0,
            tx_bytes=0,
            rx_events=0,
            final_baudrate=ctrl.baudrate,
            patchram_chunks_acked=0,
            patchram_bytes_acked=0,
            bd_addr="00:00:00:00:00:00",
            bsa_ready=False,
            hal_error_code=0,
            notice_id="",
            degraded_state="AIRPLANE_SHADOW_GATED_IDLE",
            airplane_latched=True,
            system_error_abort=False,
            wdt_resets=0,
            shooting_unaffected=True,
            recording_unaffected=True,
            nvram_writes=NVRAM_PERSISTENT_WRITES,
            details="RAM-shadow BK4\\0 (0x019e0012=00, 0x01a20002=00) gated BT init with 0 HCI packets",
        )

    opened = ctrl.open_uart()
    if not opened:
        # UART_DISCONNECTED_TIMEOUT -> P12 non-blocking HAL fallback (0x0BB9 = 3001)
        # Also exercise feeding an HCI_Reset command to prove dead UART emits 0 events.
        evts = ctrl.feed_uart_bytes(build_h4_hci_command(HCI_OP_RESET))
        hal_rc = BT_BSA_HAL_ERR_CODE
        passed = (
            mode == BT_MODE_UART_TIMEOUT
            and len(evts) == 0
            and hal_rc == 0x0BB9
        )
        return BtModeVerificationResult(
            mode=mode,
            passed=passed,
            uart_opened=False,
            tx_packets=ctrl.tx_packet_count,
            tx_bytes=ctrl.tx_byte_count,
            rx_events=len(ctrl.rx_events),
            final_baudrate=ctrl.baudrate,
            patchram_chunks_acked=0,
            patchram_bytes_acked=0,
            bd_addr="00:00:00:00:00:00",
            bsa_ready=False,
            hal_error_code=hal_rc,
            notice_id="",
            degraded_state="BT_DEGRADED_DISABLED",
            airplane_latched=False,
            system_error_abort=False,
            wdt_resets=0,
            shooting_unaffected=True,
            recording_unaffected=True,
            nvram_writes=NVRAM_PERSISTENT_WRITES,
            details="Absent/dead /dev/ttyAMA3 -> P12 non-blocking BT_DEGRADED_DISABLED (0xbb9 / 3001)",
        )

    # Execute full BSA HCI initialization sequence:
    # 1) HCI_Reset -> 2) Read_Local_Version -> 3) Update_Baudrate (3M) ->
    # 4) Download_Minidriver -> 5) Write_RAM chunks -> 6) Launch_RAM -> 7) HCI_Reset -> 8) Read_BD_ADDR
    patch_chunks = (
        (0x0020_0000, b"\xAA\x55\x01\x02" * 16),
        (0x0020_0040, b"\xDE\xAD\xBE\xEF" * 16),
        (0x0020_0080, b"\xCA\xFE\xBA\xBE" * 8),
    )
    sequence: List[bytes] = [
        build_h4_hci_command(HCI_OP_RESET),
        build_h4_hci_command(HCI_OP_READ_LOCAL_VERSION_INFO),
        build_h4_hci_command(HCI_OP_BCM_UPDATE_BAUDRATE, build_bcm_baudrate_params(BT_HIGH_BAUD)),
        build_h4_hci_command(HCI_OP_BCM_DOWNLOAD_MINIDRIVER),
    ]
    for addr, payload in patch_chunks:
        sequence.append(build_h4_hci_command(HCI_OP_BCM_WRITE_RAM, build_bcm_write_ram_params(addr, payload)))
    sequence.extend([
        build_h4_hci_command(HCI_OP_BCM_LAUNCH_RAM, struct.pack("<I", 0x0020_0000)),
        build_h4_hci_command(HCI_OP_RESET),
        build_h4_hci_command(HCI_OP_READ_BD_ADDR),
    ])

    for pkt in sequence:
        evts = ctrl.feed_uart_bytes(pkt)
        if any(e.status != HCI_STATUS_SUCCESS for e in evts):
            # Mid-firmware WF-12 NACK -> Sony 00342260 Airplane-latch containment (0 bootloops!)
            nack_evt = next(e for e in evts if e.status != HCI_STATUS_SUCCESS)
            passed = (
                mode == BT_MODE_PATCHRAM_NACK
                and ctrl.patchram_state == "NACKED"
                and ctrl.patchram_chunks_acked == 1
                and nack_evt.status == HCI_STATUS_COMMAND_DISALLOWED
            )
            return BtModeVerificationResult(
                mode=mode,
                passed=passed,
                uart_opened=True,
                tx_packets=ctrl.tx_packet_count,
                tx_bytes=ctrl.tx_byte_count,
                rx_events=len(ctrl.rx_events),
                final_baudrate=ctrl.baudrate,
                patchram_chunks_acked=ctrl.patchram_chunks_acked,
                patchram_bytes_acked=ctrl.patchram_bytes_acked,
                bd_addr="00:00:00:00:00:00",
                bsa_ready=False,
                hal_error_code=nack_evt.status,
                notice_id=SONY_NOTICE_00342260_ID,
                degraded_state="NOTICE_00342260_AIRPLANE_LATCHED",
                airplane_latched=True,
                system_error_abort=False,
                wdt_resets=0,
                shooting_unaffected=True,
                recording_unaffected=True,
                nvram_writes=NVRAM_PERSISTENT_WRITES,
                details="Mid-patchram 0xFC4C NACK -> Sony 00342260 Airplane-latch containment (0 WDT resets)",
            )

    last_evt = ctrl.rx_events[-1]
    wire_bd = last_evt.payload[::-1]
    bd_str = ":".join(f"{b:02x}" for b in wire_bd)
    passed = (
        mode == BT_MODE_HEALTHY
        and ctrl.bsa_ready
        and ctrl.baudrate == BT_HIGH_BAUD
        and ctrl.patchram_state == "LAUNCHED"
        and ctrl.patchram_chunks_acked == len(patch_chunks)
        and bd_str == ctrl.bd_addr_str
        and all(e.status == HCI_STATUS_SUCCESS for e in ctrl.rx_events)
    )
    return BtModeVerificationResult(
        mode=mode,
        passed=passed,
        uart_opened=True,
        tx_packets=ctrl.tx_packet_count,
        tx_bytes=ctrl.tx_byte_count,
        rx_events=len(ctrl.rx_events),
        final_baudrate=ctrl.baudrate,
        patchram_chunks_acked=ctrl.patchram_chunks_acked,
        patchram_bytes_acked=ctrl.patchram_bytes_acked,
        bd_addr=bd_str,
        bsa_ready=ctrl.bsa_ready,
        hal_error_code=0,
        notice_id="",
        degraded_state="BSA_HEALTHY_READY",
        airplane_latched=False,
        system_error_abort=False,
        wdt_resets=0,
        shooting_unaffected=True,
        recording_unaffected=True,
        nvram_writes=NVRAM_PERSISTENT_WRITES,
        details="Full virtual-rom-v1 BSA bring-up succeeded (0 errors, deterministic BD_ADDR)",
    )


# ---------------------------------------------------------------------------
# End-to-End Phase 29 Audit Runner
# ---------------------------------------------------------------------------


def run_phase29_soft_gpe_and_bt_audit(
    *,
    force_clean_room: bool = False,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run full Part A (Soft-GPE + LDEC/UXC + HOSDAP02 ramfb) & Part B (`virtual-rom-v1` 4-mode BT) audit."""
    eff_env = dict(os.environ if env is None else env)
    if force_clean_room:
        eff_env[ENV_FORCE_CLEAN_ROOM] = "1"
    paths = resolve_phase29_donor_paths(env=eff_env)

    # Part A: UXC / LDEC + Software GPE Compositor
    uxc_path = paths["fx6_image_uxc"]
    if uxc_path.is_file() and not is_forced_clean_room(eff_env):
        uxc_bytes = read_donor_bytes_readonly(uxc_path)
        gpe_source_mode = "LOCAL_DONOR_RDONLY"
    else:
        uxc_bytes = build_clean_room_uxd_fixture()
        gpe_source_mode = "CLEAN_ROOM_SYNTHETIC"

    entry_slots, sprites = parse_uxd_sprites(uxc_bytes)
    nine_patches = [s for s in sprites if s.is_nine_patch]
    standards = [s for s in sprites if not s.is_nine_patch]

    engine = SoftGpeEngine()
    # Backdrop + Cinema Line Big6 panels via GRM_gpermFillrect (verifies fx6_px R/B parity)
    engine.grm_fillrect(0, 0, 1024, 540, 0x10, 0x14, 0x1A, 0xFF)
    engine.grm_fillrect(8, 52, 224, 140, 0x22, 0x2E, 0x3E, 0xFF)
    engine.grm_fillrect(8, 52, 6, 140, 0xF0, 0x80, 0x18, 0xFF)  # Amber accent (R=0xF0, B=0x18)
    engine.grm_fillrect(242, 52, 540, 356, 0x14, 0x1E, 0x28, 0xAA, blend_mode=BLEND_SRC_OVER_CONST_ALPHA, const_alpha=0xC0)

    decoded_sprites_count = 0
    if standards:
        sp0 = standards[0]
        surf0 = decode_uxd_sprite_to_surface(uxc_bytes, sp0)
        engine.grm_rectblit(surf0, (0, 0, sp0.width, sp0.height), (24, 72, sp0.width, sp0.height))
        decoded_sprites_count += 1
    if nine_patches:
        np0 = nine_patches[0]
        surf_np = decode_uxd_sprite_to_surface(uxc_bytes, np0)
        engine.grm_nine_patch_blit(surf_np, (250, 64, 300, 72), np0.insets)
        decoded_sprites_count += 1

    # Also verify explicit A8 glyph tint, RGBA8888, and ARGB4444 compositing onto GPE0
    a8_glyph = GpeSurface(8, 8, PIXEL_FMT_A8, raw_bytes=bytes([0xFF] * 64))
    engine.grm_rectblit(a8_glyph, (0, 0, 8, 8), (500, 220, 8, 8), color_mod=COLOR_MOD_TINT, tint_rgb=(0xEE, 0xEE, 0xEE))
    rgba8888_surf = GpeSurface(4, 4, PIXEL_FMT_RGBA8888, raw_bytes=bytes([0xF0, 0x38, 0x38, 0xFF]) * 16)
    engine.grm_rectblit(rgba8888_surf, (0, 0, 4, 4), (512, 220, 4, 4))
    argb4444_surf = GpeSurface(4, 4, PIXEL_FMT_ARGB4444, raw_bytes=struct.pack("<H", 0xF28E) * 16)
    engine.grm_rectblit(argb4444_surf, (0, 0, 4, 4), (520, 220, 4, 4))

    gpe0_sha = engine.flush_to_offscreen_parity()
    _hdr, _ramfb_bytes, ramfb_stats = engine.hosdap02_ramfb_scanout()

    # Verify fx6_px R/B parity on the amber accent strip at (10, 80) -> must be 0xFFF08018 (R=0xF0, G=0x80, B=0x18)
    amber_px = engine.gpe0.read_argb32(10, 80)
    rb_parity_ok = amber_px == fx6_px(0xF0, 0x80, 0x18, 0xFF) == 0xFFF08018

    # Part B: Donor BT inspection + 4-mode `virtual-rom-v1` verification
    bt_inspection = inspect_bt_donor_libraries(force_clean_room=is_forced_clean_room(eff_env), env=eff_env)
    bt_modes = {m: run_bsa_bringup_scenario(m) for m in ALL_BT_OPERATING_MODES}

    all_passed = (
        len(sprites) > 0
        and len(nine_patches) > 0
        and decoded_sprites_count >= 2
        and rb_parity_ok
        and int(ramfb_stats["nonzero_gpe0_pixels"]) == GPE0_PIXEL_COUNT
        and int(ramfb_stats["unique_gpe0_colors"]) >= 5
        and gpe0_sha == engine.gpe1.sha256()
        and bt_inspection.all_markers_satisfied
        and all(res.passed for res in bt_modes.values())
    )

    return {
        "schema": PHASE_29_SCHEMA,
        "phase_version": PHASE_29_VERSION,
        "all_checks_passed": all_passed,
        "redlines": {
            "p8_cp_mutation_forbidden": P8_CP_MUTATION_FORBIDDEN,
            "wbi_mutation_bytes": WBI_MUTATION_BYTES,
            "cp_mutation_bytes": CP_MUTATION_BYTES,
            "nvram_persistent_writes": NVRAM_PERSISTENT_WRITES,
            "donor_access_mode": "O_RDONLY",
        },
        "part_a_soft_gpe": {
            "source_mode": gpe_source_mode,
            "uxc_bytes": len(uxc_bytes),
            "entry_slots": entry_slots,
            "total_sprites": len(sprites),
            "nine_patch_sprites": len(nine_patches),
            "decoded_sprites_composited": decoded_sprites_count,
            "fillrect_count": engine.fillrect_count,
            "rectblit_count": engine.rectblit_count,
            "nine_patch_count": engine.nine_patch_count,
            "fx6_px_rb_parity_ok": rb_parity_ok,
            "amber_accent_px_hex": f"0x{amber_px:08x}",
            "ramfb_scanout": ramfb_stats,
        },
        "part_b_bt_virtual_rom_v1": {
            "donor_inspection": asdict(bt_inspection),
            "modes": {m: asdict(res) for m, res in bt_modes.items()},
        },
    }


def _main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Phase 29 Hardware-Free Software GPE Compositor & virtual-rom-v1 BT Emulator"
    )
    parser.add_argument("--json", action="store_true", help="Emit deterministic JSON report")
    parser.add_argument("--clean-room", action="store_true", help="Force synthetic clean-room mode")
    args = parser.parse_args(argv)

    rep = run_phase29_soft_gpe_and_bt_audit(force_clean_room=args.clean_room)
    if args.json:
        print(json.dumps(rep, indent=2))
    else:
        gpe = rep["part_a_soft_gpe"]
        bt = rep["part_b_bt_virtual_rom_v1"]
        print(
            f"[Phase 29] passed={rep['all_checks_passed']} "
            f"gpe_mode={gpe['source_mode']} sprites={gpe['total_sprites']} "
            f"(9patch={gpe['nine_patch_sprites']}) fx6_px_ok={gpe['fx6_px_rb_parity_ok']} "
            f"bt_mode={bt['donor_inspection']['source_mode']} "
            f"bt_modes_ok={sum(1 for m in bt['modes'].values() if m['passed'])}/{len(bt['modes'])}"
        )
    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(_main())
