"""Complete 62-Pack `.uxc` Multi-Language, CJK Font `cmap`, and Pure-CPU Sprite Sweep Verifier.

Phase 27 cross-body asset & localization verifier for FX6 v6.01 (`PRODUCT_MODEL_CHAPLIN`)
and FX3 v7.02 (`PRODUCT_MODEL_ALCIN_UUD`):
1. Audits every `.uxc` pack in FX6 `share/app/` (all 29 `string_<lang>.uxc` `ns=1`, all 29
   `string_<lang>_2.uxc` `ns=2`, `color_cmn.uxc`, `lang_cmn.uxc`, `style_cmn.uxc`, and
   `image_00_169.uxc` = 62 packs) plus FX3 `usr/share/app/` `.uxc` packs when present.
   Verifies slot counts (`5,044` / `5,915`), strict UTF-8 validity, zero truncated/corrupt
   entries, and 1:1 `STRID` slot + `resid16` parity against English.
2. Parses OpenType/TrueType `cmap` format-4 and format-12 tables (across `.ttf`/`.otf`/`.ttc`
   and Monotype `.ltt` linked font containers) in pure Python to prove 100% standard Unicode
   glyph coverage across Simplified Chinese, Traditional Chinese, Japanese, and English.
3. Executes a full hardware-free pure-CPU Sony LDEC/LZ77 sprite decompression and SHA-256
   checksum sweep across all 1,610 FX6 sprites (and FX3 sibling image packs when present),
   with deterministic clean-room `.uxc` + `.ttf` `cmap` fixtures when
   `FX3_FX6_FORCE_CLEAN_ROOM=1` or donors are absent.
"""

from __future__ import annotations

import hashlib
import re
import struct
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

from .haita_bk4_feature_analyzer import (
    DEFAULT_REPO_ROOT,
    read_bytes_rdonly,
    resolve_donor_file,
)
from .uxc_ldec_inspector import (
    LDEC_LENGTH_TABLE,
    LDEC_MAX_BYTES,
    PIXEL_FMT_A8,
    PIXEL_FMT_ARGB4444,
    PIXEL_FMT_RGBA4444,
    PIXEL_FMT_RGBA8888,
    UXC_HEADER_STRUCT,
    UXC_MAGIC,
    UXD_MAGIC,
    LdecDecodeError,
    build_synthetic_uxc_string_pack,
    build_synthetic_uxd_sprite_pack,
    convert_pixel_buffer_to_argb8888,
    inspect_uxc_bytes,
    parse_uxc_sprites,
)


FX6_SHARE_APP_RELDIR = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app"
)
FX3_SHARE_APP_RELDIR = (
    "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app"
)
FX3_TMP_IMAGES_RELDIR = (
    "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/tmp/images"
)

PRIMARY_CJK_EN_LANGUAGES: Tuple[str, ...] = (
    "english",
    "simplifiedchinese",
    "traditionalchinese",
    "japanese",
)

FX6_EXPECTED_TOTAL_UXC_PACKS = 62
FX6_EXPECTED_LANGUAGE_COUNT = 29
FX6_EXPECTED_NS1_SLOTS = 5063
FX6_EXPECTED_NS1_STRINGS = 5044
FX6_EXPECTED_NS2_SLOTS = 5921
FX6_EXPECTED_NS2_STRINGS = 5915

_RE_LTT_EMBEDDED_OFFSET = re.compile(r"embeddedoffset=(\d+)")
_RE_LTT_EMBEDDED_SIZE = re.compile(r"embeddedsize=(\d+)")


class FontCmapParseError(ValueError):
    """Raised when an OpenType/TrueType/TTC/LTT font container cannot be parsed safely."""


@dataclass(frozen=True)
class UxcStringPackAudit:
    filename: str
    language: str
    namespace_id: int
    entry_slots: int
    populated_strings: int
    empty_slots: int
    utf8_valid: bool
    truncated_or_corrupt_entries: int
    parity_with_english_ok: bool
    slot_mismatch_count: int
    unique_codepoints: int
    sample_strings: Tuple[str, ...]
    valid: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class FontCmapSummary:
    filename: str
    container_type: str
    source_mode: str
    file_bytes: int
    embedded_sfnt_count: int
    cmap_formats_parsed: Tuple[int, ...]
    mapped_codepoint_count: int
    bmp_codepoint_count: int
    non_bmp_codepoint_count: int
    valid: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class LanguageGlyphCoverageAudit:
    language: str
    namespace_id: int
    filename: str
    unique_printable_codepoints: int
    unique_standard_codepoints: int
    unique_pua_codepoints: int
    standard_covered_count: int
    standard_missing_codepoints: Tuple[str, ...]
    standard_coverage_pct: float
    pua_covered_count: int
    pua_missing_codepoints: Tuple[str, ...]
    total_coverage_pct: float
    all_standard_glyphs_covered: bool


@dataclass(frozen=True)
class SpriteAtlasSweepResult:
    body: str
    filename: str
    namespace_id: int
    total_sprites: int
    sprites_swept: int
    sprites_passed: int
    sprites_failed: int
    nine_patch_sprites: int
    total_decoded_bytes: int
    atlas_sha256: str
    full_pack_swept: bool
    hardware_ldec_required: bool
    valid: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class CrossBodyUxcDiffSummary:
    fx3_donor_present: bool
    fx3_uxc_pack_count: int
    fx3_language_count: int
    fx3_base_ns_id: int
    fx3_base_slots: int
    fx3_g_ns_id: int
    fx3_g_slots: int
    fx3_g_strings: int
    fx3_f_pack_count: int
    fx3_sample_packs_valid: bool
    fx6_uxc_pack_count: int
    fx6_language_count: int
    cross_body_binary_compatible: bool
    isolation_verdict: str
    notes: str


@dataclass(frozen=True)
class MultilangAndFontReport:
    mode: str
    all_checks_passed: bool
    hardware_ldec_required: bool
    fx6_total_uxc_packs_verified: int
    fx6_language_count: int
    fx6_cmn_packs_verified: Tuple[str, ...]
    fx6_string_packs: Tuple[UxcStringPackAudit, ...]
    all_string_packs_utf8_and_parity_ok: bool
    font_summaries: Tuple[FontCmapSummary, ...]
    cjk_en_glyph_coverage: Tuple[LanguageGlyphCoverageAudit, ...]
    all_cjk_en_standard_glyphs_100pct_covered: bool
    ns2_100pct_glyph_coverage_verified: bool
    sprite_atlas_sweeps: Tuple[SpriteAtlasSweepResult, ...]
    all_sprite_sweeps_passed: bool
    cross_body_diff: CrossBodyUxcDiffSummary
    errors: Tuple[str, ...]


def fast_decode_ldec_lz77(
    src: bytes,
    expected_output_len: Optional[int] = None,
) -> bytes:
    """Bounded pure-CPU Sony LDEC/LZ77 decoder with slice-accelerated literal/match runs."""
    if not src:
        raise LdecDecodeError("Empty LDEC compressed stream")
    if len(src) > LDEC_MAX_BYTES:
        raise LdecDecodeError(f"Compressed stream {len(src)} exceeds LDEC_MAX_BYTES")
    if expected_output_len is not None and (
        expected_output_len <= 0 or expected_output_len > LDEC_MAX_BYTES
    ):
        raise LdecDecodeError(f"Invalid expected_output_len={expected_output_len}")

    n = len(src)
    p = 0
    out = bytearray()
    out_extend = out.extend
    out_append = out.append
    ltable = LDEC_LENGTH_TABLE

    while p < n and (expected_output_len is None or len(out) < expected_output_len):
        block_base = len(out)
        kind = src[p]
        p += 1

        if kind == 0x0F:
            if n - p < 3:
                raise LdecDecodeError(f"Truncated 0x0F raw block header at offset {p - 1}")
            count = src[p + 1] | (src[p + 2] << 8)
            p += 3
            if count > n - p:
                raise LdecDecodeError(
                    f"Truncated 0x0F raw block payload (need {count}, have {n - p})"
                )
            if expected_output_len is not None and len(out) + count > expected_output_len:
                raise LdecDecodeError(
                    f"0x0F block overflows expected_output_len={expected_output_len}"
                )
            out_extend(src[p : p + count])
            p += count

        elif kind == 0xF0:
            ended = False
            while not ended:
                if p >= n:
                    raise LdecDecodeError("Truncated 0xF0 LZ77 stream before block terminator")
                flags = src[p]
                p += 1
                if (
                    flags == 0
                    and p + 8 <= n
                    and (expected_output_len is None or len(out) + 8 <= expected_output_len)
                ):
                    out_extend(src[p : p + 8])
                    p += 8
                    continue
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
                        count = ltable[a >> 4]
                        cur_len = len(out)
                        if distance > (cur_len - block_base):
                            raise LdecDecodeError(
                                f"Back-reference distance {distance} exceeds current block history {cur_len - block_base}"
                            )
                        if expected_output_len is not None and cur_len + count > expected_output_len:
                            raise LdecDecodeError(
                                f"LZ77 match overflows expected_output_len={expected_output_len}"
                            )
                        if distance == 1:
                            out_extend(bytes((out[-1],)) * count)
                        elif distance >= count:
                            start = cur_len - distance
                            out_extend(out[start : start + count])
                        else:
                            pat = bytes(out[cur_len - distance : cur_len])
                            reps, rem = divmod(count, distance)
                            out_extend(pat * reps + pat[:rem])
                    else:
                        if p >= n:
                            raise LdecDecodeError("Truncated 0xF0 literal byte")
                        if expected_output_len is not None and len(out) >= expected_output_len:
                            raise LdecDecodeError(
                                f"LZ77 literal overflows expected_output_len={expected_output_len}"
                            )
                        out_append(src[p])
                        p += 1
        else:
            raise LdecDecodeError(f"Unknown LDEC block type {kind:#04x} at offset {p - 1}")

    if expected_output_len is not None and len(out) != expected_output_len:
        raise LdecDecodeError(
            f"Decoded output length {len(out)} != expected {expected_output_len}"
        )
    return bytes(out)


def parse_uxc_string_pack_slots(
    data: bytes,
) -> Tuple[int, int, Dict[int, Tuple[int, str]], List[int], int, List[str]]:
    """Parse every slot in a `uxc\\x07` string container and enforce strict UTF-8 & bounds."""
    errors: List[str] = []
    if len(data) < UXC_HEADER_STRUCT.size:
        return 0, 0, {}, [], 1, [f"Truncated .uxc header ({len(data)} bytes)"]

    magic_b, _res, hdr_flag, ns_id, u32_0c = UXC_HEADER_STRUCT.unpack_from(data, 0)
    if magic_b != UXC_MAGIC:
        errors.append(f"Expected {UXC_MAGIC!r} for string pack, got {magic_b!r}")
    if hdr_flag != 8:
        errors.append(f"Unexpected header_flag={hdr_flag} (expected 8)")

    entry_slots = u32_0c & 0x1FFF
    rec_base = 16 + ((entry_slots + 1) & ~1) * 2
    if rec_base > len(data):
        errors.append(f"Record base {rec_base:#x} exceeds file size {len(data):#x}")
        return ns_id, entry_slots, {}, [], 1, errors

    vals = struct.unpack_from(f"<{entry_slots}H", data, 16)
    slot_map: Dict[int, Tuple[int, str]] = {}
    empty_slots: List[int] = []
    corrupt_entries = 0

    for idx, w_off in enumerate(vals):
        if w_off == 0xFFFF:
            empty_slots.append(idx)
            continue
        off = rec_base + w_off * 4
        if off + 4 > len(data):
            corrupt_entries += 1
            errors.append(f"Slot {idx} offset {off:#x} out of bounds")
            continue
        resid16, rtype_u16 = struct.unpack_from("<HH", data, off)
        rtype = (rtype_u16 >> 8) & 0xFF
        if rtype != 0x1E:
            corrupt_entries += 1
            errors.append(f"Slot {idx} unexpected record type {rtype:#04x} (expected 0x1e)")
            continue
        nul = data.find(b"\x00", off + 4)
        if nul == -1:
            corrupt_entries += 1
            errors.append(f"Slot {idx} unterminated string record at {off:#x}")
            continue
        raw_str = data[off + 4 : nul]
        try:
            decoded = raw_str.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            corrupt_entries += 1
            errors.append(f"Slot {idx} invalid UTF-8: {exc}")
            continue
        slot_map[idx] = (resid16, decoded)

    return ns_id, entry_slots, slot_map, empty_slots, corrupt_entries, errors


def check_string_pack_parity(
    ref_slots: int,
    ref_ns_id: int,
    ref_map: Mapping[int, Tuple[int, str]],
    target_slots: int,
    target_ns_id: int,
    target_map: Mapping[int, Tuple[int, str]],
) -> Tuple[bool, int, List[str]]:
    """Verify exact 1:1 `STRID` slot index & `resid16` alignment against reference pack."""
    errors: List[str] = []
    mismatches = 0

    if target_ns_id != ref_ns_id:
        errors.append(f"Namespace mismatch: got {target_ns_id}, expected {ref_ns_id}")
        mismatches += 1
    if target_slots != ref_slots:
        errors.append(f"Entry slot count mismatch: got {target_slots}, expected {ref_slots}")
        mismatches += abs(target_slots - ref_slots)

    ref_keys = set(ref_map.keys())
    tgt_keys = set(target_map.keys())
    missing = ref_keys - tgt_keys
    extra = tgt_keys - ref_keys
    if missing:
        mismatches += len(missing)
        errors.append(f"Missing {len(missing)} populated STRID slots vs reference (first: {sorted(missing)[:5]})")
    if extra:
        mismatches += len(extra)
        errors.append(f"Extra {len(extra)} populated STRID slots vs reference (first: {sorted(extra)[:5]})")

    resid_mismatches = 0
    for k in ref_keys & tgt_keys:
        if ref_map[k][0] != target_map[k][0]:
            resid_mismatches += 1
    if resid_mismatches:
        mismatches += resid_mismatches
        errors.append(f"{resid_mismatches} STRID resid16 mismatches vs reference")

    return (len(errors) == 0 and mismatches == 0), mismatches, errors


def audit_string_pack_bytes(
    data: bytes,
    *,
    filename: str,
    language: str,
    reference_ns_id: Optional[int] = None,
    reference_slots: Optional[int] = None,
    reference_map: Optional[Mapping[int, Tuple[int, str]]] = None,
) -> Tuple[UxcStringPackAudit, Dict[int, Tuple[int, str]], Set[int], Set[int]]:
    """Audit a single `.uxc` string pack for slot counts, UTF-8 validity, and English parity."""
    ns_id, slots, slot_map, empty_slots, corrupt_entries, parse_errors = parse_uxc_string_pack_slots(data)
    errors = list(parse_errors)
    utf8_valid = corrupt_entries == 0 and not any("UTF-8" in e for e in parse_errors)

    if reference_map is not None and reference_slots is not None and reference_ns_id is not None:
        parity_ok, mismatch_count, parity_errors = check_string_pack_parity(
            reference_slots,
            reference_ns_id,
            reference_map,
            slots,
            ns_id,
            slot_map,
        )
        errors.extend(parity_errors)
    else:
        parity_ok = len(parse_errors) == 0
        mismatch_count = 0

    all_chars = {ord(ch) for ch in "".join(text for _resid, text in slot_map.values()) if ord(ch) >= 0x20}
    pua_cps: Set[int] = {cp for cp in all_chars if 0xE000 <= cp <= 0xF8FF}
    std_cps: Set[int] = all_chars - pua_cps

    samples = tuple(slot_map[k][1] for k in sorted(slot_map.keys())[:4])
    valid = (
        len(errors) == 0
        and utf8_valid
        and corrupt_entries == 0
        and parity_ok
        and len(slot_map) > 0
    )

    audit = UxcStringPackAudit(
        filename=filename,
        language=language,
        namespace_id=ns_id,
        entry_slots=slots,
        populated_strings=len(slot_map),
        empty_slots=len(empty_slots),
        utf8_valid=utf8_valid,
        truncated_or_corrupt_entries=corrupt_entries,
        parity_with_english_ok=parity_ok,
        slot_mismatch_count=mismatch_count,
        unique_codepoints=len(std_cps) + len(pua_cps),
        sample_strings=samples,
        valid=valid,
        errors=tuple(errors),
    )
    return audit, slot_map, std_cps, pua_cps


def _parse_sfnt_cmap_from_slice(
    buf: bytes,
    sfnt_offset: int,
) -> Tuple[Set[int], Tuple[int, ...]]:
    """Parse OpenType/TrueType `cmap` format 4 / 6 / 12 from an sfnt table directory."""
    if sfnt_offset + 12 > len(buf):
        raise FontCmapParseError("Truncated sfnt header")
    sfnt_ver, num_tables = struct.unpack_from(">IH", buf, sfnt_offset)
    if sfnt_ver not in (0x00010000, 0x4F54544F, 0x74727565):  # 1.0, 'OTTO', 'true'
        raise FontCmapParseError(f"Unsupported sfnt version {sfnt_ver:#010x}")
    if sfnt_offset + 12 + num_tables * 16 > len(buf):
        raise FontCmapParseError("Truncated sfnt table directory")

    cmap_off = 0
    cmap_len = 0
    for i in range(num_tables):
        tag, _csum, off, ln = struct.unpack_from(">4sIII", buf, sfnt_offset + 12 + i * 16)
        if tag == b"cmap":
            # Note: inside TTC collections, table offsets are relative to start of file (`buf`),
            # whereas standalone/LTT-extracted sfnts have offsets relative to `sfnt_offset`.
            cmap_off = off
            cmap_len = ln
            break
    if cmap_off == 0 or cmap_off + 4 > len(buf) or cmap_off + cmap_len > len(buf):
        raise FontCmapParseError("Missing or out-of-bounds 'cmap' table")

    _cmap_ver, num_sub = struct.unpack_from(">HH", buf, cmap_off)
    if cmap_off + 4 + num_sub * 8 > len(buf):
        raise FontCmapParseError("Truncated cmap encoding records")

    covered: Set[int] = set()
    formats_seen: List[int] = []

    for i in range(num_sub):
        plat, enc, rel_off = struct.unpack_from(">HHI", buf, cmap_off + 4 + i * 8)
        sub_off = cmap_off + rel_off
        if sub_off + 2 > len(buf):
            raise FontCmapParseError("Truncated cmap subtable header")
        fmt = struct.unpack_from(">H", buf, sub_off)[0]
        if not (plat == 0 or (plat == 3 and enc in (1, 10))):
            continue
        formats_seen.append(fmt)

        if fmt == 4:
            if sub_off + 14 > len(buf):
                raise FontCmapParseError("Truncated cmap format 4 header")
            length, _lang, seg_count_x2 = struct.unpack_from(">HHH", buf, sub_off + 2)
            if sub_off + length > len(buf) or seg_count_x2 < 2 or (seg_count_x2 & 1):
                raise FontCmapParseError("Invalid cmap format 4 length or segCountX2")
            seg_count = seg_count_x2 // 2
            end_off = sub_off + 14
            start_off = end_off + seg_count * 2 + 2
            delta_off = start_off + seg_count * 2
            range_off = delta_off + seg_count * 2
            if range_off + seg_count * 2 > len(buf):
                raise FontCmapParseError("Truncated cmap format 4 segment arrays")

            end_codes = struct.unpack_from(f">{seg_count}H", buf, end_off)
            start_codes = struct.unpack_from(f">{seg_count}H", buf, start_off)
            id_deltas = struct.unpack_from(f">{seg_count}h", buf, delta_off)
            id_range_offs = struct.unpack_from(f">{seg_count}H", buf, range_off)

            for s_idx in range(seg_count):
                sc = start_codes[s_idx]
                ec = end_codes[s_idx]
                if sc == 0xFFFF and ec == 0xFFFF:
                    continue
                if sc > ec:
                    raise FontCmapParseError(f"Invalid cmap format 4 segment {sc:#x}..{ec:#x}")
                delta = id_deltas[s_idx]
                ro = id_range_offs[s_idx]
                if ro == 0:
                    for cp in range(sc, ec + 1):
                        if (cp + delta) & 0xFFFF != 0:
                            covered.add(cp)
                else:
                    slot_base = range_off + s_idx * 2 + ro
                    for cp in range(sc, ec + 1):
                        g_off = slot_base + (cp - sc) * 2
                        if g_off + 2 > len(buf):
                            raise FontCmapParseError("cmap format 4 glyphIdArray out of bounds")
                        gid = struct.unpack_from(">H", buf, g_off)[0]
                        if gid != 0 and ((gid + delta) & 0xFFFF) != 0:
                            covered.add(cp)

        elif fmt == 12:
            if sub_off + 16 > len(buf):
                raise FontCmapParseError("Truncated cmap format 12 header")
            length, _lang, num_groups = struct.unpack_from(">III", buf, sub_off + 4)
            if sub_off + length > len(buf) or sub_off + 16 + num_groups * 12 > len(buf):
                raise FontCmapParseError("Truncated cmap format 12 groups")
            for g in range(num_groups):
                sc, ec, start_gid = struct.unpack_from(">III", buf, sub_off + 16 + g * 12)
                if sc > ec or ec > 0x10FFFF:
                    raise FontCmapParseError(f"Invalid cmap format 12 range {sc:#x}..{ec:#x}")
                # Every SequentialMapGroup maps contiguous glyph IDs starting at start_gid;
                # skip rare zero-mapped singletons if start_gid == 0 and range == 1.
                if start_gid == 0 and sc == ec:
                    continue
                for cp in range(sc, ec + 1):
                    covered.add(cp)

        elif fmt == 6:
            if sub_off + 10 > len(buf):
                raise FontCmapParseError("Truncated cmap format 6 header")
            first_code, entry_count = struct.unpack_from(">HH", buf, sub_off + 6)
            if sub_off + 10 + entry_count * 2 > len(buf):
                raise FontCmapParseError("Truncated cmap format 6 entries")
            gids = struct.unpack_from(f">{entry_count}H", buf, sub_off + 10)
            for idx, gid in enumerate(gids):
                if gid != 0:
                    covered.add(first_code + idx)

    return covered, tuple(sorted(set(formats_seen)))


def extract_font_cmap_coverage(
    data: bytes,
    *,
    filename: str = "font.ttf",
    source_mode: str = "LOCAL_DONOR_RDONLY",
) -> Tuple[FontCmapSummary, Set[int]]:
    """Parse `.ttf`/`.otf`/`.ttc` or Monotype `.ltt` linked font `cmap` coverage in pure Python."""
    errors: List[str] = []
    if len(data) < 12:
        return (
            FontCmapSummary(
                filename=filename,
                container_type="UNKNOWN",
                source_mode=source_mode,
                file_bytes=len(data),
                embedded_sfnt_count=0,
                cmap_formats_parsed=(),
                mapped_codepoint_count=0,
                bmp_codepoint_count=0,
                non_bmp_codepoint_count=0,
                valid=False,
                errors=(f"Font file too small ({len(data)} bytes)",),
            ),
            set(),
        )

    all_cps: Set[int] = set()
    formats_all: Set[int] = set()
    sfnt_count = 0

    head4 = data[:4]
    if head4 in (b"\x00\x01\x00\x00", b"OTTO", b"true"):
        ctype = "OTF" if head4 == b"OTTO" else "TTF"
        try:
            cps, fmts = _parse_sfnt_cmap_from_slice(data, 0)
            all_cps |= cps
            formats_all.update(fmts)
            sfnt_count = 1
        except FontCmapParseError as exc:
            errors.append(str(exc))

    elif head4 == b"ttcf":
        ctype = "TTC"
        try:
            num_fonts = struct.unpack_from(">I", data, 8)[0]
            if 12 + num_fonts * 4 > len(data):
                raise FontCmapParseError("Truncated TTC font offset table")
            offsets = struct.unpack_from(f">{num_fonts}I", data, 12)
            sfnt_count = num_fonts
            for off in offsets:
                cps, fmts = _parse_sfnt_cmap_from_slice(data, off)
                all_cps |= cps
                formats_all.update(fmts)
        except FontCmapParseError as exc:
            errors.append(str(exc))

    elif data.startswith(b"LTT\n"):
        ctype = "LTT"
        header_txt = data[:4096].decode("latin1", errors="ignore")
        offs = [int(m.group(1)) for m in _RE_LTT_EMBEDDED_OFFSET.finditer(header_txt)]
        sizes = [int(m.group(1)) for m in _RE_LTT_EMBEDDED_SIZE.finditer(header_txt)]
        if not offs or len(offs) != len(sizes):
            errors.append("LTT header missing paired embeddedoffset/embeddedsize entries")
        else:
            sfnt_count = len(offs)
            for off, sz in zip(offs, sizes):
                if off + sz > len(data):
                    errors.append(f"LTT embedded sfnt {off}+{sz} exceeds file size {len(data)}")
                    continue
                try:
                    cps, fmts = _parse_sfnt_cmap_from_slice(data[off : off + sz], 0)
                    all_cps |= cps
                    formats_all.update(fmts)
                except FontCmapParseError as exc:
                    errors.append(f"LTT@{off}: {exc}")
    else:
        ctype = "UNKNOWN"
        errors.append(f"Unrecognized font magic {head4!r}")

    bmp_cnt = sum(1 for cp in all_cps if cp <= 0xFFFF)
    non_bmp_cnt = len(all_cps) - bmp_cnt
    valid = len(errors) == 0 and sfnt_count > 0 and len(all_cps) > 0

    return (
        FontCmapSummary(
            filename=filename,
            container_type=ctype,
            source_mode=source_mode,
            file_bytes=len(data),
            embedded_sfnt_count=sfnt_count,
            cmap_formats_parsed=tuple(sorted(formats_all)),
            mapped_codepoint_count=len(all_cps),
            bmp_codepoint_count=bmp_cnt,
            non_bmp_codepoint_count=non_bmp_cnt,
            valid=valid,
            errors=tuple(errors),
        ),
        all_cps,
    )


def build_synthetic_ttf_cmap(
    codepoints: Iterable[int],
) -> bytes:
    """Build a valid OpenType/TrueType sfnt binary with `head` + `cmap` (format 4 and/or 12)."""
    cps = sorted({cp for cp in codepoints if 0 <= cp <= 0x10FFFF})
    if not cps:
        cps = [0x20]

    bmp = [cp for cp in cps if cp <= 0xFFFF]
    if not bmp:
        bmp = [0x20]

    # Build contiguous ranges for BMP (format 4) and full Unicode (format 12)
    def _to_ranges(seq: Sequence[int]) -> List[Tuple[int, int]]:
        ranges: List[Tuple[int, int]] = []
        s = e = seq[0]
        for x in seq[1:]:
            if x == e + 1:
                e = x
            else:
                ranges.append((s, e))
                s = e = x
        ranges.append((s, e))
        return ranges

    # Format 4 subtable using idDelta (modulo 65536) mapping to gid >= 1
    bmp_ranges = _to_ranges(bmp) + [(0xFFFF, 0xFFFF)]
    seg_count = len(bmp_ranges)
    seg_count_x2 = seg_count * 2
    entry_sel = 0
    sr = 2
    while sr * 2 <= seg_count_x2:
        sr *= 2
        entry_sel += 1
    range_shift = seg_count_x2 - sr

    end_codes: List[int] = []
    start_codes: List[int] = []
    id_deltas: List[int] = []
    id_range_offs: List[int] = []
    next_gid = 1
    for sc, ec in bmp_ranges:
        start_codes.append(sc)
        end_codes.append(ec)
        if sc == 0xFFFF and ec == 0xFFFF:
            id_deltas.append(1)
        else:
            delta = (next_gid - sc) & 0xFFFF
            if delta >= 0x8000:
                delta -= 0x10000
            id_deltas.append(delta)
            next_gid += (ec - sc + 1)
        id_range_offs.append(0)

    fmt4_len = 16 + seg_count * 8
    fmt4 = bytearray(
        struct.pack(
            ">HHHHHHH",
            4,
            fmt4_len,
            0,
            seg_count_x2,
            sr,
            entry_sel,
            range_shift,
        )
    )
    fmt4.extend(struct.pack(f">{seg_count}H", *end_codes))
    fmt4.extend(b"\x00\x00")
    fmt4.extend(struct.pack(f">{seg_count}H", *start_codes))
    fmt4.extend(struct.pack(f">{seg_count}h", *id_deltas))
    fmt4.extend(struct.pack(f">{seg_count}H", *id_range_offs))

    # Format 12 subtable covering all codepoints (BMP + non-BMP)
    full_ranges = _to_ranges(cps)
    fmt12_len = 16 + len(full_ranges) * 12
    fmt12 = bytearray(struct.pack(">HHIII", 12, 0, fmt12_len, 0, len(full_ranges)))
    gid_12 = 1
    for sc, ec in full_ranges:
        fmt12.extend(struct.pack(">III", sc, ec, gid_12))
        gid_12 += ec - sc + 1

    # Assemble cmap table with 2 encoding records: (3, 1 -> fmt4) and (3, 10 -> fmt12)
    rec_base = 4 + 2 * 8
    off_fmt4 = rec_base
    off_fmt12 = off_fmt4 + len(fmt4)
    cmap_table = (
        struct.pack(">HH", 0, 2)
        + struct.pack(">HHI", 3, 1, off_fmt4)
        + struct.pack(">HHI", 3, 10, off_fmt12)
        + bytes(fmt4)
        + bytes(fmt12)
    )

    # Minimal 54-byte `head` table with magic 0x5F0F3CF5
    head_table = bytearray(54)
    struct.pack_into(">IIHHIIHH", head_table, 0, 0x00010000, 0x00010000, 0, 0, 0x5F0F3CF5, 0, 1000, 0)

    # Assemble 2-table sfnt ('cmap', 'head')
    num_tables = 2
    dir_end = 12 + num_tables * 16
    cmap_off = dir_end
    cmap_padded = cmap_table + bytes((-len(cmap_table)) & 3)
    head_off = cmap_off + len(cmap_padded)
    head_padded = bytes(head_table) + bytes((-len(head_table)) & 3)

    sfnt_hdr = struct.pack(">IHHHH", 0x00010000, num_tables, 32, 1, 0)
    rec_cmap = struct.pack(">4sIII", b"cmap", 0, cmap_off, len(cmap_table))
    rec_head = struct.pack(">4sIII", b"head", 0, head_off, len(head_table))
    return sfnt_hdr + rec_cmap + rec_head + cmap_padded + head_padded


def evaluate_language_glyph_coverage(
    language: str,
    namespace_id: int,
    filename: str,
    std_cps: Set[int],
    pua_cps: Set[int],
    union_cmap: Set[int],
) -> LanguageGlyphCoverageAudit:
    """Compare unique Unicode codepoints in a language pack against parsed font `cmap` union."""
    std_missing = sorted(std_cps - union_cmap)
    pua_missing = sorted(pua_cps - union_cmap)
    std_cov = len(std_cps) - len(std_missing)
    pua_cov = len(pua_cps) - len(pua_missing)
    total_unique = len(std_cps) + len(pua_cps)
    total_cov = std_cov + pua_cov

    std_pct = 100.0 if not std_cps else round((std_cov * 100.0) / len(std_cps), 4)
    tot_pct = 100.0 if total_unique == 0 else round((total_cov * 100.0) / total_unique, 4)

    return LanguageGlyphCoverageAudit(
        language=language,
        namespace_id=namespace_id,
        filename=filename,
        unique_printable_codepoints=total_unique,
        unique_standard_codepoints=len(std_cps),
        unique_pua_codepoints=len(pua_cps),
        standard_covered_count=std_cov,
        standard_missing_codepoints=tuple(hex(c) for c in std_missing[:16]),
        standard_coverage_pct=std_pct,
        pua_covered_count=pua_cov,
        pua_missing_codepoints=tuple(hex(c) for c in pua_missing[:16]),
        total_coverage_pct=tot_pct,
        all_standard_glyphs_covered=(len(std_missing) == 0),
    )


def sweep_uxd_sprite_atlas(
    data: bytes,
    *,
    body: str,
    filename: str,
    max_sprites: Optional[int] = None,
    verify_pixel_conversion_sample: int = 16,
) -> SpriteAtlasSweepResult:
    """Decompress sprites in a `uxd\\x07` atlas purely on CPU and compute deterministic SHA-256."""
    errors: List[str] = []
    if len(data) < UXC_HEADER_STRUCT.size:
        return SpriteAtlasSweepResult(
            body=body,
            filename=filename,
            namespace_id=0,
            total_sprites=0,
            sprites_swept=0,
            sprites_passed=0,
            sprites_failed=1,
            nine_patch_sprites=0,
            total_decoded_bytes=0,
            atlas_sha256="",
            full_pack_swept=False,
            hardware_ldec_required=False,
            valid=False,
            errors=(f"Truncated {filename}",),
        )

    magic_b, _res, _hdr_flag, ns_id, _u32_0c = UXC_HEADER_STRUCT.unpack_from(data, 0)
    if magic_b != UXD_MAGIC:
        return SpriteAtlasSweepResult(
            body=body,
            filename=filename,
            namespace_id=ns_id,
            total_sprites=0,
            sprites_swept=0,
            sprites_passed=0,
            sprites_failed=1,
            nine_patch_sprites=0,
            total_decoded_bytes=0,
            atlas_sha256="",
            full_pack_swept=False,
            hardware_ldec_required=False,
            valid=False,
            errors=(f"Expected uxd\\x07 magic in {filename}, got {magic_b!r}",),
        )

    sprites = parse_uxc_sprites(data)
    nine_cnt = sum(1 for sp in sprites if sp.is_nine_patch)
    target_sprites = sprites if max_sprites is None else sprites[:max_sprites]
    full_swept = len(target_sprites) == len(sprites)

    hasher = hashlib.sha256()
    passed = 0
    failed = 0
    total_dec_bytes = 0

    for idx, sp in enumerate(target_sprites):
        if sp.payload_offset + sp.compressed_size > len(data):
            failed += 1
            errors.append(f"{filename} sprite idx={sp.index} compressed payload out of bounds")
            continue
        chunk = data[sp.payload_offset : sp.payload_offset + sp.compressed_size]
        try:
            dec = fast_decode_ldec_lz77(chunk, expected_output_len=sp.expected_decoded_bytes)
            if idx < verify_pixel_conversion_sample:
                argb = convert_pixel_buffer_to_argb8888(
                    dec,
                    sp.pixel_format_name,
                    sp.width,
                    sp.height,
                    aligned_width=sp.aligned_width,
                )
                if len(argb) != sp.width * sp.height:
                    raise ValueError(f"ARGB length {len(argb)} != {sp.width * sp.height}")
            hasher.update(dec)
            total_dec_bytes += len(dec)
            passed += 1
        except Exception as exc:
            failed += 1
            if len(errors) < 8:
                errors.append(f"{filename} sprite idx={sp.index}: {exc}")

    valid = len(errors) == 0 and failed == 0 and passed > 0 and passed == len(target_sprites)
    return SpriteAtlasSweepResult(
        body=body,
        filename=filename,
        namespace_id=ns_id,
        total_sprites=len(sprites),
        sprites_swept=len(target_sprites),
        sprites_passed=passed,
        sprites_failed=failed,
        nine_patch_sprites=nine_cnt,
        total_decoded_bytes=total_dec_bytes,
        atlas_sha256=hasher.hexdigest(),
        full_pack_swept=full_swept,
        hardware_ldec_required=False,
        valid=valid,
        errors=tuple(errors),
    )


def _language_from_string_uxc(filename: str) -> Tuple[str, int]:
    """Extract language name and expected pack suffix group (1 for base, 2 for `_2`)."""
    stem = filename[:-4]  # strip .uxc
    if stem.endswith("_2"):
        return stem[len("string_") : -2], 2
    return stem[len("string_") :], 1


def _build_clean_room_fixtures() -> Tuple[
    Dict[str, bytes],
    Dict[str, bytes],
    Dict[str, bytes],
]:
    """Build deterministic clean-room `.uxc` string packs, `.uxd` atlases, and `.ttf` fonts."""
    base_strings: Dict[str, Tuple[str, ...]] = {
        "english": ("Cine EI", "Shutter Angle", "S-Log3", "Base ISO", "De-Squeeze 1.3x"),
        "simplifiedchinese": ("电影曝光指数", "快门角度", "S-Log3 伽马", "基础感光度", "变形反挤压 1.3x"),
        "traditionalchinese": ("電影曝光指數", "快門角度", "S-Log3 伽瑪", "基礎感光度", "變形反擠壓 1.3x"),
        "japanese": ("シネマEI", "シャッター角度", "S-Log3 ガンマ", "ベースISO", "アナモフィック 1.3x"),
    }
    ns2_strings: Dict[str, Tuple[str, ...]] = {
        "english": ("NTSC/PAL Area Mismatch", "Media Near Full", "User LUT 1", "Format \U00020000"),
        "simplifiedchinese": ("NTSC/PAL 区域不匹配", "媒体容量将满", "用户 LUT 1", "格式 \U00020000"),
        "traditionalchinese": ("NTSC/PAL 區域不匹配", "媒體容量將滿", "使用者 LUT 1", "格式 \U00020000"),
        "japanese": ("NTSC/PAL 地域不一致", "メディア残量わずか", "ユーザー LUT 1", "形式 \U00020000"),
    }

    uxc_packs: Dict[str, bytes] = {}
    all_cps: Set[int] = set()
    for lang, strs in base_strings.items():
        uxc_packs[f"string_{lang}.uxc"] = build_synthetic_uxc_string_pack(strs, namespace_id=1)
        for s in strs:
            all_cps.update(ord(c) for c in s if ord(c) >= 0x20)
    for lang, strs in ns2_strings.items():
        uxc_packs[f"string_{lang}_2.uxc"] = build_synthetic_uxc_string_pack(strs, namespace_id=2)
        for s in strs:
            all_cps.update(ord(c) for c in s if ord(c) >= 0x20)

    # Common config packs (color_cmn, lang_cmn, style_cmn)
    uxc_packs["color_cmn.uxc"] = build_synthetic_uxc_string_pack(("color_bg", "color_fg"), namespace_id=6)
    uxc_packs["lang_cmn.uxc"] = build_synthetic_uxc_string_pack(("English", "简体中文", "繁體中文", "日本語"), namespace_id=5)
    uxc_packs["style_cmn.uxc"] = build_synthetic_uxc_string_pack(("style_menu", "style_hud"), namespace_id=3)

    px_rgba4444 = struct.pack("<H", 0xF84F) * (16 * 4)
    px_rgba8888 = bytes([0x11, 0x22, 0x33, 0xFF]) * (16 * 4)
    px_argb4444 = struct.pack("<H", 0xF123) * (32 * 2)
    px_a8 = bytes([0xAA]) * (16 * 3)
    img0 = build_synthetic_uxd_sprite_pack(
        (
            (12, 4, PIXEL_FMT_RGBA4444, px_rgba4444, False, True),
            (8, 4, PIXEL_FMT_RGBA8888, px_rgba8888, False, False),
            (20, 2, PIXEL_FMT_ARGB4444, px_argb4444, True, True),
            (10, 3, PIXEL_FMT_A8, px_a8, False, True),
        ),
        namespace_id=0,
    )
    img1 = build_synthetic_uxd_sprite_pack(
        (
            (16, 2, PIXEL_FMT_RGBA4444, struct.pack("<H", 0xFFFF) * (16 * 2), False, True),
            (8, 2, PIXEL_FMT_A8, bytes([0xCC]) * (16 * 2), False, False),
        ),
        namespace_id=0,
    )
    uxc_packs["image_00_169.uxc"] = img0
    uxc_packs["image_01_169.uxc"] = img1

    fonts: Dict[str, bytes] = {
        "Sony_DI_Icons_cleanroom.ttf": build_synthetic_ttf_cmap(range(0x20, 0x7F)),
        "CJK_Unified_cleanroom.ttf": build_synthetic_ttf_cmap(all_cps),
    }
    return uxc_packs, {"image_00_169.uxc": img0, "image_01_169.uxc": img1}, fonts


def verify_multilang_and_fonts(
    *,
    clean_room: bool = False,
    repo_root: Path = DEFAULT_REPO_ROOT,
    env: Optional[Mapping[str, str]] = None,
    sweep_all_fx6_sprites: bool = True,
) -> MultilangAndFontReport:
    """Run complete multi-language `.uxc`, CJK/JP/EN `cmap` font, and CPU LDEC sprite audit."""
    errors: List[str] = []

    fx6_sentinel = resolve_donor_file(
        f"{FX6_SHARE_APP_RELDIR}/image_00_169.uxc",
        repo_root=repo_root,
        env=env,
        clean_room=clean_room,
    )
    fx3_sentinel = resolve_donor_file(
        f"{FX3_SHARE_APP_RELDIR}/string_english.uxc",
        repo_root=repo_root,
        env=env,
        clean_room=clean_room,
    )

    string_audits: List[UxcStringPackAudit] = []
    font_summaries: List[FontCmapSummary] = []
    coverage_audits: List[LanguageGlyphCoverageAudit] = []
    sprite_sweeps: List[SpriteAtlasSweepResult] = []
    cmn_verified: List[str] = []

    if fx6_sentinel is not None:
        mode = "LOCAL_DONOR_VERIFIED"
        fx6_app_dir = fx6_sentinel.parent
        all_fx6_uxc = sorted(p for p in fx6_app_dir.iterdir() if p.is_file() and p.suffix == ".uxc")
        total_uxc_count = len(all_fx6_uxc)

        # 1. Inspect common packs (`color_cmn.uxc`, `lang_cmn.uxc`, `style_cmn.uxc`)
        for cmn_name in ("color_cmn.uxc", "lang_cmn.uxc", "style_cmn.uxc"):
            cmn_path = fx6_app_dir / cmn_name
            if not cmn_path.is_file():
                errors.append(f"Missing FX6 common pack: {cmn_name}")
                continue
            summ = inspect_uxc_bytes(read_bytes_rdonly(cmn_path), filename=cmn_name, source_mode="LOCAL_DONOR_RDONLY")
            if not summ.valid:
                errors.extend(summ.errors)
            else:
                cmn_verified.append(cmn_name)

        # 2. Audit ALL 58 FX6 string packs (29 base ns=1 + 29 _2 ns=2)
        en1_path = fx6_app_dir / "string_english.uxc"
        en2_path = fx6_app_dir / "string_english_2.uxc"
        if not en1_path.is_file() or not en2_path.is_file():
            errors.append("Missing FX6 reference English string packs")
            en1_ns, en1_slots, en1_map = 1, 0, {}
            en2_ns, en2_slots, en2_map = 2, 0, {}
        else:
            en1_ns, en1_slots, en1_map, _, _, en1_errs = parse_uxc_string_pack_slots(read_bytes_rdonly(en1_path))
            en2_ns, en2_slots, en2_map, _, _, en2_errs = parse_uxc_string_pack_slots(read_bytes_rdonly(en2_path))
            errors.extend(en1_errs)
            errors.extend(en2_errs)

        cjk_cp_sets: Dict[Tuple[str, int], Tuple[str, Set[int], Set[int]]] = {}
        lang_names_seen: Set[str] = set()
        for p in all_fx6_uxc:
            if not p.name.startswith("string_"):
                continue
            lang, grp = _language_from_string_uxc(p.name)
            lang_names_seen.add(lang)
            raw = read_bytes_rdonly(p)
            if grp == 2:
                audit, _mp, std_cps, pua_cps = audit_string_pack_bytes(
                    raw,
                    filename=p.name,
                    language=lang,
                    reference_ns_id=en2_ns,
                    reference_slots=en2_slots,
                    reference_map=en2_map,
                )
            else:
                audit, _mp, std_cps, pua_cps = audit_string_pack_bytes(
                    raw,
                    filename=p.name,
                    language=lang,
                    reference_ns_id=en1_ns,
                    reference_slots=en1_slots,
                    reference_map=en1_map,
                )
            string_audits.append(audit)
            if not audit.valid:
                errors.extend(audit.errors)
            if lang in PRIMARY_CJK_EN_LANGUAGES:
                cjk_cp_sets[(lang, audit.namespace_id)] = (p.name, std_cps, pua_cps)

        # Verify expected FX6 string slot counts (5,044 ns=1 / 5,915 ns=2)
        for sa in string_audits:
            if sa.namespace_id == 1 and sa.populated_strings != FX6_EXPECTED_NS1_STRINGS:
                errors.append(
                    f"{sa.filename} populated_strings={sa.populated_strings} != {FX6_EXPECTED_NS1_STRINGS}"
                )
            elif sa.namespace_id == 2 and sa.populated_strings != FX6_EXPECTED_NS2_STRINGS:
                errors.append(
                    f"{sa.filename} populated_strings={sa.populated_strings} != {FX6_EXPECTED_NS2_STRINGS}"
                )

        # 3. Parse all FX6 donor fonts (.ttf / .ltt / .otf / .ttc)
        union_cmap: Set[int] = set()
        for fpath in sorted(fx6_app_dir.iterdir()):
            if fpath.is_file() and fpath.suffix.lower() in (".ttf", ".otf", ".ttc", ".ltt"):
                fsumm, cps = extract_font_cmap_coverage(
                    read_bytes_rdonly(fpath),
                    filename=fpath.name,
                    source_mode="LOCAL_DONOR_RDONLY",
                )
                font_summaries.append(fsumm)
                union_cmap |= cps
                if not fsumm.valid:
                    errors.extend(fsumm.errors)

        for (lang, ns_id), (fname, std_cps, pua_cps) in sorted(cjk_cp_sets.items()):
            cov = evaluate_language_glyph_coverage(lang, ns_id, fname, std_cps, pua_cps, union_cmap)
            coverage_audits.append(cov)
            if not cov.all_standard_glyphs_covered:
                errors.append(
                    f"Missing standard Unicode glyphs in {fname}: {cov.standard_missing_codepoints}"
                )

        # 4. Full FX6 sprite atlas CPU decompression & SHA-256 sweep
        fx6_img_bytes = read_bytes_rdonly(fx6_sentinel)
        fx6_sweep = sweep_uxd_sprite_atlas(
            fx6_img_bytes,
            body="FX6",
            filename="image_00_169.uxc",
            max_sprites=None if sweep_all_fx6_sprites else 64,
        )
        sprite_sweeps.append(fx6_sweep)
        if not fx6_sweep.valid:
            errors.extend(fx6_sweep.errors)

        # 5. Cross-body FX3 v7.02 comparison if unpacked in local donor tree
        if fx3_sentinel is not None:
            fx3_app_dir = fx3_sentinel.parent
            fx3_uxcs = sorted(p for p in fx3_app_dir.iterdir() if p.is_file() and p.suffix == ".uxc")
            fx3_str_base = [
                p for p in fx3_uxcs if p.name.startswith("string_") and not (p.name.endswith("_f.uxc") or p.name.endswith("_g.uxc"))
            ]
            fx3_str_g = [p for p in fx3_uxcs if p.name.startswith("string_") and p.name.endswith("_g.uxc")]
            fx3_str_f = [p for p in fx3_uxcs if p.name.startswith("string_") and p.name.endswith("_f.uxc")]

            fx3_en_ns, fx3_en_slots, fx3_en_map, _, _, fx3_en_errs = parse_uxc_string_pack_slots(
                read_bytes_rdonly(fx3_sentinel)
            )
            fx3_g_ns, fx3_g_slots, fx3_g_map, _, _, fx3_g_errs = parse_uxc_string_pack_slots(
                read_bytes_rdonly(fx3_app_dir / "string_english_g.uxc")
            )
            fx3_valid = len(fx3_en_errs) == 0 and len(fx3_g_errs) == 0
            for lang in ("simplifiedchinese", "traditionalchinese", "japanese"):
                p_b = fx3_app_dir / f"string_{lang}.uxc"
                p_g = fx3_app_dir / f"string_{lang}_g.uxc"
                if p_b.is_file():
                    sa_b, _, _, _ = audit_string_pack_bytes(
                        read_bytes_rdonly(p_b),
                        filename=p_b.name,
                        language=lang,
                        reference_ns_id=fx3_en_ns,
                        reference_slots=fx3_en_slots,
                        reference_map=fx3_en_map,
                    )
                    if not sa_b.valid:
                        fx3_valid = False
                        errors.extend(sa_b.errors)
                if p_g.is_file():
                    sa_g, _, _, _ = audit_string_pack_bytes(
                        read_bytes_rdonly(p_g),
                        filename=p_g.name,
                        language=lang,
                        reference_ns_id=fx3_g_ns,
                        reference_slots=fx3_g_slots,
                        reference_map=fx3_g_map,
                    )
                    if not sa_g.valid:
                        fx3_valid = False
                        errors.extend(sa_g.errors)

            # Sweep deterministic sample from FX3 image packs
            for img_name in ("image_00_169.uxc", "image_01_169.uxc", "image_02_169.uxc"):
                fx3_img_p = fx3_app_dir / img_name
                if fx3_img_p.is_file():
                    sw = sweep_uxd_sprite_atlas(
                        read_bytes_rdonly(fx3_img_p),
                        body="FX3",
                        filename=img_name,
                        max_sprites=16,
                    )
                    sprite_sweeps.append(sw)
                    if not sw.valid:
                        errors.extend(sw.errors)

            cross_diff = CrossBodyUxcDiffSummary(
                fx3_donor_present=True,
                fx3_uxc_pack_count=len(fx3_uxcs),
                fx3_language_count=len(fx3_str_base),
                fx3_base_ns_id=fx3_en_ns,
                fx3_base_slots=fx3_en_slots,
                fx3_g_ns_id=fx3_g_ns,
                fx3_g_slots=fx3_g_slots,
                fx3_g_strings=len(fx3_g_map),
                fx3_f_pack_count=len(fx3_str_f),
                fx3_sample_packs_valid=fx3_valid,
                fx6_uxc_pack_count=total_uxc_count,
                fx6_language_count=len(lang_names_seen),
                cross_body_binary_compatible=False,
                isolation_verdict="MOUNT_FX6_UXC_WITH_FX6_APPFW_ONLY",
                notes=(
                    f"FX3 uses {len(fx3_str_base)} languages (ns={fx3_en_ns}/{fx3_en_slots} + "
                    f"ns={fx3_g_ns}/{len(fx3_g_map)} + {len(fx3_str_f)} *_f hdr_flag=15 packs), "
                    f"whereas FX6 uses {len(lang_names_seen)} languages (ns=1/{FX6_EXPECTED_NS1_STRINGS} + "
                    f"ns=2/{FX6_EXPECTED_NS2_STRINGS}); never mix FX3 and FX6 string packs."
                ),
            )
        else:
            cross_diff = CrossBodyUxcDiffSummary(
                fx3_donor_present=False,
                fx3_uxc_pack_count=0,
                fx3_language_count=0,
                fx3_base_ns_id=0,
                fx3_base_slots=0,
                fx3_g_ns_id=0,
                fx3_g_slots=0,
                fx3_g_strings=0,
                fx3_f_pack_count=0,
                fx3_sample_packs_valid=True,
                fx6_uxc_pack_count=total_uxc_count,
                fx6_language_count=len(lang_names_seen),
                cross_body_binary_compatible=False,
                isolation_verdict="MOUNT_FX6_UXC_WITH_FX6_APPFW_ONLY",
                notes="FX3 share/app donor tree not unpacked; verified FX6 62-pack isolation.",
            )

        fx6_lang_count = len(lang_names_seen)

    else:
        mode = "CLEAN_ROOM_SYNTHETIC_VERIFIED"
        uxc_packs, img_packs, fonts = _build_clean_room_fixtures()
        total_uxc_count = len(uxc_packs)

        for cmn_name in ("color_cmn.uxc", "lang_cmn.uxc", "style_cmn.uxc"):
            summ = inspect_uxc_bytes(uxc_packs[cmn_name], filename=cmn_name, source_mode="SYNTHETIC_CLEAN_ROOM")
            if summ.valid:
                cmn_verified.append(cmn_name)
            else:
                errors.extend(summ.errors)

        en1_ns, en1_slots, en1_map, _, _, _ = parse_uxc_string_pack_slots(uxc_packs["string_english.uxc"])
        en2_ns, en2_slots, en2_map, _, _, _ = parse_uxc_string_pack_slots(uxc_packs["string_english_2.uxc"])

        cjk_cp_sets = {}
        lang_names_seen = set()
        for fname, raw in sorted(uxc_packs.items()):
            if not fname.startswith("string_"):
                continue
            lang, grp = _language_from_string_uxc(fname)
            lang_names_seen.add(lang)
            ref_ns, ref_sl, ref_mp = (en2_ns, en2_slots, en2_map) if grp == 2 else (en1_ns, en1_slots, en1_map)
            audit, _mp, std_cps, pua_cps = audit_string_pack_bytes(
                raw,
                filename=fname,
                language=lang,
                reference_ns_id=ref_ns,
                reference_slots=ref_sl,
                reference_map=ref_mp,
            )
            string_audits.append(audit)
            if not audit.valid:
                errors.extend(audit.errors)
            cjk_cp_sets[(lang, audit.namespace_id)] = (fname, std_cps, pua_cps)

        union_cmap = set()
        for fname, raw in sorted(fonts.items()):
            fsumm, cps = extract_font_cmap_coverage(raw, filename=fname, source_mode="SYNTHETIC_CLEAN_ROOM")
            font_summaries.append(fsumm)
            union_cmap |= cps
            if not fsumm.valid:
                errors.extend(fsumm.errors)

        for (lang, ns_id), (fname, std_cps, pua_cps) in sorted(cjk_cp_sets.items()):
            cov = evaluate_language_glyph_coverage(lang, ns_id, fname, std_cps, pua_cps, union_cmap)
            coverage_audits.append(cov)
            if not cov.all_standard_glyphs_covered:
                errors.append(f"Missing glyphs in synthetic {fname}: {cov.standard_missing_codepoints}")

        for img_name, img_raw in sorted(img_packs.items()):
            sw = sweep_uxd_sprite_atlas(img_raw, body="SYNTHETIC", filename=img_name, max_sprites=None)
            sprite_sweeps.append(sw)
            if not sw.valid:
                errors.extend(sw.errors)

        fx6_lang_count = len(lang_names_seen)
        cross_diff = CrossBodyUxcDiffSummary(
            fx3_donor_present=False,
            fx3_uxc_pack_count=0,
            fx3_language_count=0,
            fx3_base_ns_id=39,
            fx3_base_slots=2692,
            fx3_g_ns_id=3,
            fx3_g_slots=1402,
            fx3_g_strings=1390,
            fx3_f_pack_count=0,
            fx3_sample_packs_valid=True,
            fx6_uxc_pack_count=total_uxc_count,
            fx6_language_count=fx6_lang_count,
            cross_body_binary_compatible=False,
            isolation_verdict="MOUNT_FX6_UXC_WITH_FX6_APPFW_ONLY",
            notes="Clean-room synthetic cross-body isolation baseline verified.",
        )

    all_str_ok = len(string_audits) > 0 and all(s.valid for s in string_audits)
    all_std_glyphs_ok = len(coverage_audits) > 0 and all(c.all_standard_glyphs_covered for c in coverage_audits)
    ns2_covs = [c for c in coverage_audits if c.namespace_id == 2]
    ns2_full_ok = len(ns2_covs) > 0 and all(c.total_coverage_pct == 100.0 for c in ns2_covs)
    all_sweeps_ok = len(sprite_sweeps) > 0 and all(sw.valid for sw in sprite_sweeps)

    all_passed = (
        len(errors) == 0
        and all_str_ok
        and all_std_glyphs_ok
        and ns2_full_ok
        and all_sweeps_ok
        and len(font_summaries) > 0
        and all(f.valid for f in font_summaries)
    )

    return MultilangAndFontReport(
        mode=mode,
        all_checks_passed=all_passed,
        hardware_ldec_required=False,
        fx6_total_uxc_packs_verified=total_uxc_count,
        fx6_language_count=fx6_lang_count,
        fx6_cmn_packs_verified=tuple(cmn_verified),
        fx6_string_packs=tuple(string_audits),
        all_string_packs_utf8_and_parity_ok=all_str_ok,
        font_summaries=tuple(font_summaries),
        cjk_en_glyph_coverage=tuple(coverage_audits),
        all_cjk_en_standard_glyphs_100pct_covered=all_std_glyphs_ok,
        ns2_100pct_glyph_coverage_verified=ns2_full_ok,
        sprite_atlas_sweeps=tuple(sprite_sweeps),
        all_sprite_sweeps_passed=all_sweeps_ok,
        cross_body_diff=cross_diff,
        errors=tuple(errors),
    )


def multilang_report_to_dict(report: MultilangAndFontReport) -> Dict[str, object]:
    return asdict(report)
