"""Hardware-Free Sony `.uxc` / `uxd\\x07` Resource Container & CPU LDEC/LZ77 Asset Inspector.

Replaces hardware `/dev/ldec` (`ldec.ko`) dependency with a pure-CPU bounded Sony LZ77
(`0x0F` raw + `0xF0` back-reference) decoder, `.uxc`/`uxd\\x07` container parser, and
pixel conversion verifier (`RGBA4444`, `RGBA8888`, `A8`, `ARGB4444` -> `ARGB8888`).

Strictly Read-Only (`os.O_RDONLY`) on local donor `.uxc` packs (`image_00_169.uxc`,
`string_english_2.uxc`, and sibling `.uxc` packs) with deterministic synthetic Clean-Room
`.uxc` builders when `FX3_FX6_FORCE_CLEAN_ROOM=1` or donors are absent.
"""

from __future__ import annotations

import hashlib
import struct
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from .haita_bk4_feature_analyzer import (
    DEFAULT_REPO_ROOT,
    read_bytes_rdonly,
    resolve_donor_file,
)


UXC_MAGIC = b"uxc\x07"
UXD_MAGIC = b"uxd\x07"
UXC_HEADER_STRUCT = struct.Struct("<4sIHHI")  # magic, reserved, hdr_flag(8), ns_id, u32_count_meta

UXC_SHARE_APP_RELDIR = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app"
)

# Sony LDEC / libux_core::Lz77Decoder length lookup table (4-bit code -> 3..64 bytes)
LDEC_LENGTH_TABLE: Tuple[int, ...] = (
    3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 32, 64
)
LDEC_MAX_BYTES = 16 * 1024 * 1024

# Pixel formats aligned with fx6_live_guest.c / BMP_PixelFormat / Stella
PIXEL_FMT_RGBA4444 = "RGBA4444"
PIXEL_FMT_RGBA8888 = "RGBA8888"
PIXEL_FMT_ARGB4444 = "ARGB4444"
PIXEL_FMT_A8 = "A8"
SUPPORTED_PIXEL_FORMATS: Tuple[str, ...] = (
    PIXEL_FMT_RGBA4444,
    PIXEL_FMT_RGBA8888,
    PIXEL_FMT_ARGB4444,
    PIXEL_FMT_A8,
)

# Known FX6 namespace mapping (matching fx6_native_menu_tables.h / liblibra sys_getNamespaceID)
KNOWN_NAMESPACES: Dict[int, str] = {
    0: "image_00_169.uxc",
    1: "string_english.uxc",
    2: "string_english_2.uxc",
    3: "style_cmn.uxc",
    5: "lang_cmn.uxc",
    6: "color_cmn.uxc",
}


class LdecDecodeError(ValueError):
    """Raised when a Sony LZ77 / LDEC stream fails bounds or grammar verification."""


@dataclass(frozen=True)
class LdecDecodeResult:
    ok: bool
    input_bytes_consumed: int
    output_bytes: int
    block_count: int
    raw_block_count: int
    lz77_block_count: int
    literals: int
    matches: int
    max_distance: int
    output_sha256: str
    error: str = ""


@dataclass(frozen=True)
class UxcSpriteEntry:
    index: int
    resid: int
    record_offset: int
    flags: int
    compress_format: int
    resource_pixel_format: int
    pixel_format_name: str
    is_nine_patch: bool
    resident_flag: bool
    width: int
    height: int
    aligned_width: int
    compressed_size: int
    payload_offset: int
    expected_decoded_bytes: int


@dataclass(frozen=True)
class UxcContainerSummary:
    filename: str
    source_mode: str
    file_bytes: int
    magic: str
    namespace_id: int
    entry_slots: int
    non_empty_entries: int
    record_base_offset: int
    record_types_seen: Tuple[str, ...]
    sprite_count: int
    nine_patch_sprite_count: int
    string_count: int
    sample_strings: Dict[str, str]
    valid: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class UxcSpriteDecodeVerification:
    index: int
    resid: int
    dimensions: str
    aligned_width: int
    pixel_format: str
    is_nine_patch: bool
    compressed_size: int
    decoded_bytes: int
    argb8888_pixels: int
    non_zero_argb_pixels: int
    ok: bool


@dataclass(frozen=True)
class UxcInspectionReport:
    mode: str
    all_checks_passed: bool
    hardware_ldec_required: bool
    containers_inspected: int
    sibling_uxc_packs: Tuple[str, ...]
    container_summaries: Tuple[UxcContainerSummary, ...]
    sprites_decoded_and_verified: int
    sprite_verifications: Tuple[UxcSpriteDecodeVerification, ...]
    rgba4444_to_argb8888_parity_ok: bool
    errors: Tuple[str, ...]


def decode_ldec_lz77(
    src: bytes,
    expected_output_len: Optional[int] = None,
) -> Tuple[bytes, LdecDecodeResult]:
    """Decode a Sony LDEC / LZ77 byte stream purely on CPU (no `/dev/ldec`)."""
    if not src:
        raise LdecDecodeError("Empty LDEC compressed stream")
    if len(src) > LDEC_MAX_BYTES:
        raise LdecDecodeError(f"Compressed stream {len(src)} exceeds LDEC_MAX_BYTES")
    if expected_output_len is not None and (expected_output_len <= 0 or expected_output_len > LDEC_MAX_BYTES):
        raise LdecDecodeError(f"Invalid expected_output_len={expected_output_len}")

    n = len(src)
    p = 0
    out = bytearray()
    blocks = 0
    raw_blocks = 0
    lz_blocks = 0
    literals = 0
    matches = 0
    max_distance = 0

    while p < n and (expected_output_len is None or len(out) < expected_output_len):
        block_base = len(out)
        kind = src[p]
        p += 1
        blocks += 1

        if kind == 0x0F:
            if n - p < 3:
                raise LdecDecodeError(f"Truncated 0x0F raw block header at offset {p - 1}")
            count = src[p + 1] | (src[p + 2] << 8)
            p += 3
            if count > n - p:
                raise LdecDecodeError(f"Truncated 0x0F raw block payload (need {count}, have {n - p})")
            if expected_output_len is not None and len(out) + count > expected_output_len:
                raise LdecDecodeError(
                    f"0x0F block overflows expected_output_len={expected_output_len}"
                )
            out.extend(src[p : p + count])
            p += count
            raw_blocks += 1
            literals += count

        elif kind == 0xF0:
            lz_blocks += 1
            ended = False
            while not ended:
                if p >= n:
                    raise LdecDecodeError("Truncated 0xF0 LZ77 stream before block terminator")
                flags = src[p]
                p += 1
                for bit in range(8):
                    if flags & (1 << bit):
                        if n - p < 2:
                            raise LdecDecodeError("Truncated 0xF0 back-reference token")
                        a = src[p]
                        b = src[p + 1]
                        p += 2
                        distance = ((a & 0x0F) << 8) | b
                        if distance == 0:
                            ended = True
                            break
                        count = LDEC_LENGTH_TABLE[a >> 4]
                        if distance > (len(out) - block_base):
                            raise LdecDecodeError(
                                f"Back-reference distance {distance} exceeds current block history {len(out) - block_base}"
                            )
                        if expected_output_len is not None and len(out) + count > expected_output_len:
                            raise LdecDecodeError(
                                f"LZ77 match overflows expected_output_len={expected_output_len}"
                            )
                        for _ in range(count):
                            out.append(out[-distance])
                        matches += 1
                        if distance > max_distance:
                            max_distance = distance
                    else:
                        if p >= n:
                            raise LdecDecodeError("Truncated 0xF0 literal byte")
                        if expected_output_len is not None and len(out) >= expected_output_len:
                            raise LdecDecodeError(
                                f"LZ77 literal overflows expected_output_len={expected_output_len}"
                            )
                        out.append(src[p])
                        p += 1
                        literals += 1
        else:
            raise LdecDecodeError(f"Unknown LDEC block type {kind:#04x} at offset {p - 1}")

    if expected_output_len is not None and len(out) != expected_output_len:
        raise LdecDecodeError(
            f"Decoded output length {len(out)} != expected {expected_output_len}"
        )

    decoded = bytes(out)
    return decoded, LdecDecodeResult(
        ok=True,
        input_bytes_consumed=p,
        output_bytes=len(decoded),
        block_count=blocks,
        raw_block_count=raw_blocks,
        lz77_block_count=lz_blocks,
        literals=literals,
        matches=matches,
        max_distance=max_distance,
        output_sha256=hashlib.sha256(decoded).hexdigest(),
    )


def encode_ldec_lz77_raw_or_match(raw: bytes, *, prefer_lz77: bool = True) -> bytes:
    """Encode raw bytes into deterministic LDEC stream (`0xF0` LZ77 with RLE/literals or `0x0F` raw)."""
    if not raw:
        raise ValueError("Cannot encode empty payload")
    if not prefer_lz77:
        if len(raw) > 0xFFFF:
            raise ValueError("Raw block limited to 65535 bytes")
        return bytes([0x0F, 0x00, len(raw) & 0xFF, (len(raw) >> 8) & 0xFF]) + raw

    out = bytearray()
    chunk_limit = 4096
    pos = 0
    while pos < len(raw):
        block = raw[pos : pos + chunk_limit]
        pos += len(block)
        out.append(0xF0)
        tokens: List[Tuple[int, bytes]] = []  # (is_match, bytes)
        i = 0
        while i < len(block):
            # Look for simple distance-1 RLE or short distance-2..16 match of length 3..16/32/64
            best_len = 0
            best_dist = 0
            best_code = 0
            if i > 0:
                max_d = min(i, 4095)
                # Fast scan of recent distances (1..16)
                for d in range(1, min(max_d, 16) + 1):
                    match_len = 0
                    while (
                        i + match_len < len(block)
                        and match_len < 64
                        and block[i + match_len] == block[i + match_len - d]
                    ):
                        match_len += 1
                    for code in range(len(LDEC_LENGTH_TABLE) - 1, -1, -1):
                        lval = LDEC_LENGTH_TABLE[code]
                        if lval <= match_len and lval > best_len:
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
        # Block terminator token (distance == 0)
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


def rgba4444_to_argb8888(pv: int) -> int:
    """Convert 16-bit RGBA4444 nibble pixel (0xRGBA) to 32-bit ARGB8888 (0xAARRGGBB)."""
    r = ((pv >> 12) & 0xF) * 17
    g = ((pv >> 8) & 0xF) * 17
    b = ((pv >> 4) & 0xF) * 17
    a = (pv & 0xF) * 17
    return (a << 24) | (r << 16) | (g << 8) | b


def argb4444_to_argb8888(pv: int) -> int:
    """Convert 16-bit ARGB4444 nibble pixel (0xARGB) to 32-bit ARGB8888 (0xAARRGGBB)."""
    a = ((pv >> 12) & 0xF) * 17
    r = ((pv >> 8) & 0xF) * 17
    g = ((pv >> 4) & 0xF) * 17
    b = (pv & 0xF) * 17
    return (a << 24) | (r << 16) | (g << 8) | b


def convert_pixel_buffer_to_argb8888(
    buf: bytes,
    pixel_format: str,
    width: int,
    height: int,
    *,
    aligned_width: Optional[int] = None,
    tint_rgb: int = 0xFFFFFF,
) -> List[int]:
    """Convert decoded sprite pixel buffer (`RGBA4444`/`RGBA8888`/`ARGB4444`/`A8`) to ARGB8888 list."""
    stride_px = width if aligned_width is None else aligned_width
    out: List[int] = []
    tr = (tint_rgb >> 16) & 0xFF
    tg = (tint_rgb >> 8) & 0xFF
    tb = tint_rgb & 0xFF

    if pixel_format == PIXEL_FMT_RGBA4444:
        for y in range(height):
            row_off = y * stride_px * 2
            for x in range(width):
                pv = struct.unpack_from("<H", buf, row_off + x * 2)[0]
                out.append(rgba4444_to_argb8888(pv))
    elif pixel_format == PIXEL_FMT_ARGB4444:
        for y in range(height):
            row_off = y * stride_px * 2
            for x in range(width):
                pv = struct.unpack_from("<H", buf, row_off + x * 2)[0]
                out.append(argb4444_to_argb8888(pv))
    elif pixel_format == PIXEL_FMT_RGBA8888:
        for y in range(height):
            row_off = y * stride_px * 4
            for x in range(width):
                r, g, b, a = buf[row_off + x * 4 : row_off + x * 4 + 4]
                out.append((a << 24) | (r << 16) | (g << 8) | b)
    elif pixel_format == PIXEL_FMT_A8:
        for y in range(height):
            row_off = y * stride_px
            for x in range(width):
                a = buf[row_off + x]
                out.append((a << 24) | (tr << 16) | (tg << 8) | tb)
    else:
        raise ValueError(f"Unsupported pixel format: {pixel_format!r}")
    return out


def _map_resource_pixel_format(res_fmt: int) -> str:
    # Observed in image_00_169.uxc (res_fmt=0 -> RGBA4444 2 Bpp) and stella/BMP mapping
    if res_fmt in (0, 7):
        return PIXEL_FMT_RGBA4444
    if res_fmt in (1, 2):
        return PIXEL_FMT_RGBA8888
    if res_fmt == 3:
        return PIXEL_FMT_ARGB4444
    if res_fmt in (4, 8):
        return PIXEL_FMT_A8
    return PIXEL_FMT_RGBA4444


def parse_uxc_sprites(data: bytes) -> List[UxcSpriteEntry]:
    """Extract all sprite descriptor entries from an `uxd\\x07` container."""
    if len(data) < UXC_HEADER_STRUCT.size:
        raise ValueError("Truncated .uxc/.uxd header")
    magic, _res, _hdr_flag, ns_id, u32_0c = UXC_HEADER_STRUCT.unpack_from(data, 0)
    if magic != UXD_MAGIC:
        raise ValueError(f"Expected {UXD_MAGIC!r} for sprite container, got {magic!r}")

    entry_slots = u32_0c & 0x1FFF
    rec_base = 16 + ((entry_slots + 1) & ~1) * 2
    vals = struct.unpack_from(f"<{entry_slots}H", data, 16)

    sprites: List[UxcSpriteEntry] = []
    for idx, word_off in enumerate(vals):
        if word_off == 0xFFFF:
            continue
        off = rec_base + word_off * 4
        if off + 20 > len(data):
            continue
        w0, w1, w2 = struct.unpack_from("<3I", data, off)
        rtype = (w0 >> 24) & 0xFF
        if rtype != 0x1A:
            continue
        resid = (ns_id << 13) | idx
        is_nine = bool(w1 & 0x08000000)
        resident = bool(w1 & 0x80000000)
        comp_fmt = (w1 >> 28) & 0x7
        res_px_fmt = (w1 >> 16) & 0x3F
        px_name = _map_resource_pixel_format(res_px_fmt)
        w = w2 & 0xFFFF
        h = (w2 >> 16) & 0xFFFF
        aw = (w + 15) & ~15
        if not is_nine:
            csz, rel = struct.unpack_from("<2I", data, off + 12)
        else:
            if off + 40 > len(data):
                continue
            csz, rel = struct.unpack_from("<2I", data, off + 32)
        payload_off = off + 4 + rel
        bpp = 4 if px_name == PIXEL_FMT_RGBA8888 else (1 if px_name == PIXEL_FMT_A8 else 2)
        sprites.append(
            UxcSpriteEntry(
                index=idx,
                resid=resid,
                record_offset=off,
                flags=w1,
                compress_format=comp_fmt,
                resource_pixel_format=res_px_fmt,
                pixel_format_name=px_name,
                is_nine_patch=is_nine,
                resident_flag=resident,
                width=w,
                height=h,
                aligned_width=aw,
                compressed_size=csz,
                payload_offset=payload_off,
                expected_decoded_bytes=aw * h * bpp,
            )
        )
    return sprites


def inspect_uxc_bytes(
    data: bytes,
    *,
    filename: str,
    source_mode: str,
) -> UxcContainerSummary:
    """Parse `.uxc` / `uxd\\x07` header, index table, record types, and sample strings/sprites."""
    errors: List[str] = []
    if len(data) < UXC_HEADER_STRUCT.size:
        return UxcContainerSummary(
            filename=filename,
            source_mode=source_mode,
            file_bytes=len(data),
            magic="",
            namespace_id=0,
            entry_slots=0,
            non_empty_entries=0,
            record_base_offset=0,
            record_types_seen=(),
            sprite_count=0,
            nine_patch_sprite_count=0,
            string_count=0,
            sample_strings={},
            valid=False,
            errors=(f"File too small ({len(data)} bytes)",),
        )

    magic_b, _res, hdr_flag, ns_id, u32_0c = UXC_HEADER_STRUCT.unpack_from(data, 0)
    if magic_b not in (UXC_MAGIC, UXD_MAGIC):
        errors.append(f"Unexpected .uxc magic {magic_b!r}")
    if hdr_flag != 8:
        errors.append(f"Unexpected header_flag={hdr_flag} (expected 8)")

    entry_slots = u32_0c & 0x1FFF
    rec_base = 16 + ((entry_slots + 1) & ~1) * 2
    if rec_base > len(data):
        errors.append(f"Record base {rec_base:#x} exceeds file size {len(data):#x}")
        return UxcContainerSummary(
            filename=filename,
            source_mode=source_mode,
            file_bytes=len(data),
            magic=magic_b.decode("latin1"),
            namespace_id=ns_id,
            entry_slots=entry_slots,
            non_empty_entries=0,
            record_base_offset=rec_base,
            record_types_seen=(),
            sprite_count=0,
            nine_patch_sprite_count=0,
            string_count=0,
            sample_strings={},
            valid=False,
            errors=tuple(errors),
        )

    vals = struct.unpack_from(f"<{entry_slots}H", data, 16)
    non_empty = 0
    rtypes = set()
    sprite_cnt = 0
    nine_cnt = 0
    str_cnt = 0
    sample_strings: Dict[str, str] = {}

    for _idx, w_off in enumerate(vals):
        if w_off == 0xFFFF:
            continue
        non_empty += 1
        off = rec_base + w_off * 4
        if off + 4 > len(data):
            errors.append(f"Record offset {off:#x} out of bounds")
            continue
        resid16, rtype_u16 = struct.unpack_from("<HH", data, off)
        rtype = (rtype_u16 >> 8) & 0xFF
        rtypes.add(f"0x{rtype:02x}")
        if rtype == 0x1A and magic_b == UXD_MAGIC and off + 12 <= len(data):
            sprite_cnt += 1
            w1 = struct.unpack_from("<I", data, off + 4)[0]
            if w1 & 0x08000000:
                nine_cnt += 1
        elif rtype == 0x1E:
            str_cnt += 1
            nul = data.find(b"\x00", off + 4)
            if nul != -1 and len(sample_strings) < 8:
                sample_strings[f"0x{resid16:04x}"] = data[off + 4 : nul].decode("utf-8", errors="replace")

    return UxcContainerSummary(
        filename=filename,
        source_mode=source_mode,
        file_bytes=len(data),
        magic=magic_b.decode("latin1"),
        namespace_id=ns_id,
        entry_slots=entry_slots,
        non_empty_entries=non_empty,
        record_base_offset=rec_base,
        record_types_seen=tuple(sorted(rtypes)),
        sprite_count=sprite_cnt,
        nine_patch_sprite_count=nine_cnt,
        string_count=str_cnt,
        sample_strings=sample_strings,
        valid=len(errors) == 0 and non_empty > 0,
        errors=tuple(errors),
    )


def build_synthetic_uxd_sprite_pack(
    sprites: Sequence[Tuple[int, int, str, bytes, bool, bool]],
    *,
    namespace_id: int = 0,
) -> bytes:
    """Build a synthetic `uxd\\x07` sprite container `(w, h, px_fmt, raw_pixels, nine_patch, use_lz77)`."""
    count = len(sprites)
    rec_base = 16 + ((count + 1) & ~1) * 2
    header = UXC_HEADER_STRUCT.pack(UXD_MAGIC, 0, 8, namespace_id, count)
    table = bytearray(((count + 1) & ~1) * 2)

    descriptors = bytearray()
    payloads = bytearray()

    # First pass to compute descriptor total size so payloads start after descriptors
    desc_offsets: List[int] = []
    desc_cursor = 0
    for _w, _h, _fmt, _raw, nine_patch, _use_lz77 in sprites:
        desc_offsets.append(desc_cursor)
        desc_cursor += 40 if nine_patch else 20

    fmt_code_map = {
        PIXEL_FMT_RGBA4444: 0,
        PIXEL_FMT_RGBA8888: 1,
        PIXEL_FMT_ARGB4444: 3,
        PIXEL_FMT_A8: 4,
    }

    for idx, (w, h, px_fmt, raw, nine_patch, use_lz77) in enumerate(sprites):
        aw = (w + 15) & ~15
        bpp = 4 if px_fmt == PIXEL_FMT_RGBA8888 else (1 if px_fmt == PIXEL_FMT_A8 else 2)
        expected_len = aw * h * bpp
        if len(raw) != expected_len:
            raise ValueError(f"Sprite {idx} raw len {len(raw)} != aligned expected {expected_len}")

        comp = encode_ldec_lz77_raw_or_match(raw, prefer_lz77=use_lz77)
        d_off = desc_offsets[idx]
        struct.pack_into("<H", table, idx * 2, d_off // 4)

        p_abs_rel_to_rec_base = desc_cursor + len(payloads)
        rel_from_rec_plus_4 = p_abs_rel_to_rec_base - (d_off + 4)

        res_code = fmt_code_map[px_fmt]
        w0 = (0x1A << 24) | ((namespace_id << 13) | idx)
        w1 = 0xC0000000 | (0x08000000 if nine_patch else 0) | ((res_code & 0x3F) << 16)
        w2 = (h << 16) | w

        if not nine_patch:
            descriptors.extend(struct.pack("<5I", w0, w1, w2, len(comp), rel_from_rec_plus_4))
        else:
            descriptors.extend(
                struct.pack(
                    "<10I",
                    w0,
                    w1,
                    w2,
                    0x00010002,
                    0,
                    0x00030000,
                    0x00030003,
                    3,
                    len(comp),
                    rel_from_rec_plus_4,
                )
            )
        payloads.extend(comp)
        while len(payloads) % 4 != 0:
            payloads.append(0)

    return header + bytes(table) + bytes(descriptors) + bytes(payloads)


def build_synthetic_uxc_string_pack(
    strings: Sequence[str],
    *,
    namespace_id: int = 2,
) -> bytes:
    """Build a synthetic `uxc\\x07` string pack compatible with `string_english_2.uxc`."""
    count = len(strings)
    header = UXC_HEADER_STRUCT.pack(UXC_MAGIC, 0, 8, namespace_id, count)
    table = bytearray(((count + 1) & ~1) * 2)
    records = bytearray()
    for idx, text in enumerate(strings):
        struct.pack_into("<H", table, idx * 2, len(records) // 4)
        resid = (namespace_id << 13) | idx
        records.extend(struct.pack("<HH", resid, 0x1E00))
        records.extend(text.encode("utf-8") + b"\x00")
        while len(records) % 4 != 0:
            records.append(0)
    return header + bytes(table) + bytes(records)


def _select_sprite_sample(sprites: Sequence[UxcSpriteEntry], max_sample: int = 36) -> List[UxcSpriteEntry]:
    """Select simple, 9-patch, and flag-variant sprites for fast deterministic decode verification."""
    selected: List[UxcSpriteEntry] = []
    seen = set()
    # First 16 sprites
    for sp in sprites[:16]:
        selected.append(sp)
        seen.add(sp.index)
    # Include 9-patch and non-resident (0x40000000 / 0x48000000) variants
    for sp in sprites:
        if len(selected) >= max_sample:
            break
        if sp.index not in seen and (sp.is_nine_patch or not sp.resident_flag):
            selected.append(sp)
            seen.add(sp.index)
    return selected


def inspect_uxc_and_ldec(
    *,
    clean_room: bool = False,
    repo_root: Path = DEFAULT_REPO_ROOT,
    env: Optional[Mapping[str, str]] = None,
    max_sprite_sample: int = 36,
) -> UxcInspectionReport:
    """Inspect `.uxc` resource containers and verify hardware-free CPU LDEC + pixel conversion."""
    errors: List[str] = []
    share_dir = resolve_donor_file(
        f"{UXC_SHARE_APP_RELDIR}/image_00_169.uxc",
        repo_root=repo_root,
        env=env,
        clean_room=clean_room,
    )

    summaries: List[UxcContainerSummary] = []
    verifications: List[UxcSpriteDecodeVerification] = []
    sibling_names: List[str] = []

    if share_dir is not None:
        mode = "LOCAL_DONOR_VERIFIED"
        app_dir = share_dir.parent
        sibling_paths = sorted(p for p in app_dir.iterdir() if p.is_file() and p.suffix == ".uxc")
        sibling_names = [p.name for p in sibling_paths]

        # Inspect core packs + representative siblings (O_RDONLY)
        target_names = [
            "image_00_169.uxc",
            "string_english_2.uxc",
            "string_english.uxc",
            "color_cmn.uxc",
            "lang_cmn.uxc",
            "style_cmn.uxc",
        ]
        img_bytes = b""
        for fname in target_names:
            fpath = app_dir / fname
            if not fpath.is_file():
                errors.append(f"Missing expected donor .uxc pack: {fname}")
                continue
            raw = read_bytes_rdonly(fpath)
            if fname == "image_00_169.uxc":
                img_bytes = raw
            summ = inspect_uxc_bytes(raw, filename=fname, source_mode="LOCAL_DONOR_RDONLY")
            summaries.append(summ)
            if not summ.valid:
                errors.extend(summ.errors)

        sprites = parse_uxc_sprites(img_bytes)
        sample = _select_sprite_sample(sprites, max_sample=max_sprite_sample)
        for sp in sample:
            chunk = img_bytes[sp.payload_offset : sp.payload_offset + sp.compressed_size]
            try:
                dec, dec_res = decode_ldec_lz77(chunk, expected_output_len=sp.expected_decoded_bytes)
                argb = convert_pixel_buffer_to_argb8888(
                    dec,
                    sp.pixel_format_name,
                    sp.width,
                    sp.height,
                    aligned_width=sp.aligned_width,
                )
                nz = sum(1 for px in argb if (px >> 24) != 0)
                ok = dec_res.ok and len(argb) == sp.width * sp.height
            except Exception as exc:
                errors.append(f"Sprite idx={sp.index} decode failure: {exc}")
                dec = b""
                argb = []
                nz = 0
                ok = False
            verifications.append(
                UxcSpriteDecodeVerification(
                    index=sp.index,
                    resid=sp.resid,
                    dimensions=f"{sp.width}x{sp.height}",
                    aligned_width=sp.aligned_width,
                    pixel_format=sp.pixel_format_name,
                    is_nine_patch=sp.is_nine_patch,
                    compressed_size=sp.compressed_size,
                    decoded_bytes=len(dec),
                    argb8888_pixels=len(argb),
                    non_zero_argb_pixels=nz,
                    ok=ok,
                )
            )
    else:
        mode = "CLEAN_ROOM_SYNTHETIC_VERIFIED"
        sibling_names = [
            "image_00_169.uxc",
            "string_english_2.uxc",
            "color_cmn.uxc",
        ]
        # Build deterministic synthetic RGBA4444 (LZ77), RGBA8888 (0x0F raw), ARGB4444 (9-patch LZ77), and A8 (LZ77)
        # Sprite 0: 12x4 RGBA4444 (aligned 16x4 = 128 bytes)
        px_rgba4444 = struct.pack("<H", 0xF84F) * (16 * 4)
        # Sprite 1: 8x4 RGBA8888 (aligned 16x4 = 256 bytes, raw 0x0F block)
        px_rgba8888 = bytes([0x11, 0x22, 0x33, 0xFF]) * (16 * 4)
        # Sprite 2: 20x2 ARGB4444 nine-patch (aligned 32x2 = 128 bytes, LZ77)
        px_argb4444 = struct.pack("<H", 0xF123) * (32 * 2)
        # Sprite 3: 10x3 A8 (aligned 16x3 = 48 bytes, LZ77)
        px_a8 = bytes([0xAA]) * (16 * 3)

        img_bytes = build_synthetic_uxd_sprite_pack(
            (
                (12, 4, PIXEL_FMT_RGBA4444, px_rgba4444, False, True),
                (8, 4, PIXEL_FMT_RGBA8888, px_rgba8888, False, False),
                (20, 2, PIXEL_FMT_ARGB4444, px_argb4444, True, True),
                (10, 3, PIXEL_FMT_A8, px_a8, False, True),
            ),
            namespace_id=0,
        )
        str_bytes = build_synthetic_uxc_string_pack(
            ("NTSC/PAL Area Mismatch", "Media Near Full", "Set", "Cine EI", "S-Log3"),
            namespace_id=2,
        )
        summaries.append(
            inspect_uxc_bytes(img_bytes, filename="image_00_169.uxc", source_mode="SYNTHETIC_CLEAN_ROOM")
        )
        summaries.append(
            inspect_uxc_bytes(str_bytes, filename="string_english_2.uxc", source_mode="SYNTHETIC_CLEAN_ROOM")
        )

        sprites = parse_uxc_sprites(img_bytes)
        for sp in sprites:
            chunk = img_bytes[sp.payload_offset : sp.payload_offset + sp.compressed_size]
            dec, dec_res = decode_ldec_lz77(chunk, expected_output_len=sp.expected_decoded_bytes)
            argb = convert_pixel_buffer_to_argb8888(
                dec,
                sp.pixel_format_name,
                sp.width,
                sp.height,
                aligned_width=sp.aligned_width,
            )
            nz = sum(1 for px in argb if (px >> 24) != 0)
            verifications.append(
                UxcSpriteDecodeVerification(
                    index=sp.index,
                    resid=sp.resid,
                    dimensions=f"{sp.width}x{sp.height}",
                    aligned_width=sp.aligned_width,
                    pixel_format=sp.pixel_format_name,
                    is_nine_patch=sp.is_nine_patch,
                    compressed_size=sp.compressed_size,
                    decoded_bytes=len(dec),
                    argb8888_pixels=len(argb),
                    non_zero_argb_pixels=nz,
                    ok=dec_res.ok and len(argb) == sp.width * sp.height,
                )
            )

    # Verify exact RGBA4444 -> ARGB8888 nibble expansion parity
    parity_vectors = (
        (0x0000, 0x00000000),
        (0xFFFF, 0xFFFFFFFF),
        (0xF00F, 0xFFFF0000),
        (0x0F0F, 0xFF00FF00),
        (0x00FF, 0xFF0000FF),
        (0xA538, 0x88AA5533),
    )
    parity_ok = all(rgba4444_to_argb8888(inp) == exp for inp, exp in parity_vectors)
    if not parity_ok:
        errors.append("RGBA4444 -> ARGB8888 conversion parity check failed")

    all_ok = (
        len(errors) == 0
        and parity_ok
        and len(summaries) > 0
        and all(s.valid for s in summaries)
        and len(verifications) > 0
        and all(v.ok for v in verifications)
    )

    return UxcInspectionReport(
        mode=mode,
        all_checks_passed=all_ok,
        hardware_ldec_required=False,
        containers_inspected=len(summaries),
        sibling_uxc_packs=tuple(sibling_names),
        container_summaries=tuple(summaries),
        sprites_decoded_and_verified=len(verifications),
        sprite_verifications=tuple(verifications),
        rgba4444_to_argb8888_parity_ok=parity_ok,
        errors=tuple(errors),
    )


def uxc_report_to_dict(report: UxcInspectionReport) -> Dict[str, object]:
    return asdict(report)
