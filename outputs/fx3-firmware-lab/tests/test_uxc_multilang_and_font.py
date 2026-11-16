"""Unit tests for Phase 27 62-pack `.uxc` multi-language, CJK font `cmap`, and CPU LDEC sprite verifier.

Runs in BOTH Local Donor mode (`O_RDONLY`) and `FX3_FX6_FORCE_CLEAN_ROOM=1` mode,
keeping combined `fx3-firmware-lab` test suite runtime under 4 seconds.
"""

from __future__ import annotations

import json
import os
import struct
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Optional

from fx3_firmware_lab.__main__ import main as cli_main, run_audit_all
from fx3_firmware_lab.haita_bk4_feature_analyzer import is_forced_clean_room
from fx3_firmware_lab.uxc_ldec_inspector import (
    PIXEL_FMT_A8,
    PIXEL_FMT_RGBA4444,
    UXC_HEADER_STRUCT,
    UXC_MAGIC,
    LdecDecodeError,
    build_synthetic_uxc_string_pack,
    build_synthetic_uxd_sprite_pack,
    decode_ldec_lz77,
    encode_ldec_lz77_raw_or_match,
)
from fx3_firmware_lab.uxc_multilang_and_font_verifier import (
    FX6_EXPECTED_LANGUAGE_COUNT,
    FX6_EXPECTED_NS1_STRINGS,
    FX6_EXPECTED_NS2_STRINGS,
    FX6_EXPECTED_TOTAL_UXC_PACKS,
    MultilangAndFontReport,
    audit_string_pack_bytes,
    build_synthetic_ttf_cmap,
    check_string_pack_parity,
    evaluate_language_glyph_coverage,
    extract_font_cmap_coverage,
    fast_decode_ldec_lz77,
    parse_uxc_string_pack_slots,
    sweep_uxd_sprite_atlas,
    verify_multilang_and_fonts,
)


PKG_ROOT = Path(__file__).resolve().parents[1]


class TestDonorAndActiveMultilangAudit(unittest.TestCase):
    _active_report: Optional[MultilangAndFontReport] = None

    @classmethod
    def setUpClass(cls) -> None:
        cls._active_report = verify_multilang_and_fonts()

    def test_active_mode_full_62_pack_and_font_audit(self) -> None:
        rep = self._active_report
        assert rep is not None
        self.assertTrue(rep.all_checks_passed, msg=f"Errors: {rep.errors}")
        self.assertFalse(rep.hardware_ldec_required)
        self.assertTrue(rep.all_string_packs_utf8_and_parity_ok)
        self.assertTrue(rep.all_cjk_en_standard_glyphs_100pct_covered)
        self.assertTrue(rep.ns2_100pct_glyph_coverage_verified)
        self.assertTrue(rep.all_sprite_sweeps_passed)

        if not is_forced_clean_room() and rep.mode == "LOCAL_DONOR_VERIFIED":
            self.assertEqual(rep.fx6_total_uxc_packs_verified, FX6_EXPECTED_TOTAL_UXC_PACKS)
            self.assertEqual(rep.fx6_language_count, FX6_EXPECTED_LANGUAGE_COUNT)
            self.assertEqual(len(rep.fx6_string_packs), FX6_EXPECTED_LANGUAGE_COUNT * 2)
            self.assertEqual(
                rep.fx6_cmn_packs_verified,
                ("color_cmn.uxc", "lang_cmn.uxc", "style_cmn.uxc"),
            )
            fx6_sweep = next(s for s in rep.sprite_atlas_sweeps if s.body == "FX6")
            self.assertTrue(fx6_sweep.full_pack_swept)
            self.assertEqual(fx6_sweep.sprites_passed, 1610)
            self.assertEqual(fx6_sweep.sprites_failed, 0)
            self.assertGreater(fx6_sweep.total_decoded_bytes, 50_000_000)

    def test_cjk_en_language_packs_present_and_aligned(self) -> None:
        rep = self._active_report
        assert rep is not None
        by_file = {p.filename: p for p in rep.fx6_string_packs}
        for lang in ("english", "simplifiedchinese", "traditionalchinese", "japanese"):
            for suf in ("", "_2"):
                fname = f"string_{lang}{suf}.uxc"
                self.assertIn(fname, by_file)
                pack = by_file[fname]
                self.assertTrue(pack.valid)
                self.assertTrue(pack.utf8_valid)
                self.assertTrue(pack.parity_with_english_ok)
                self.assertEqual(pack.slot_mismatch_count, 0)
                if rep.mode == "LOCAL_DONOR_VERIFIED":
                    expected = FX6_EXPECTED_NS2_STRINGS if suf == "_2" else FX6_EXPECTED_NS1_STRINGS
                    self.assertEqual(pack.populated_strings, expected)

    def test_cross_body_fx3_isolation_verdict(self) -> None:
        rep = self._active_report
        assert rep is not None
        diff = rep.cross_body_diff
        self.assertFalse(diff.cross_body_binary_compatible)
        self.assertEqual(diff.isolation_verdict, "MOUNT_FX6_UXC_WITH_FX6_APPFW_ONLY")
        if rep.mode == "LOCAL_DONOR_VERIFIED" and diff.fx3_donor_present:
            self.assertEqual(diff.fx3_language_count, 34)
            self.assertEqual(diff.fx3_base_ns_id, 39)
            self.assertEqual(diff.fx3_base_slots, 2692)
            self.assertEqual(diff.fx3_g_ns_id, 3)
            self.assertEqual(diff.fx3_g_strings, 1390)
            self.assertTrue(diff.fx3_sample_packs_valid)


class TestCleanRoomAndStringParity(unittest.TestCase):
    def test_clean_room_mode_passes_deterministically(self) -> None:
        rep = verify_multilang_and_fonts(clean_room=True)
        self.assertTrue(rep.all_checks_passed, msg=f"Errors: {rep.errors}")
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC_VERIFIED")
        self.assertFalse(rep.hardware_ldec_required)
        self.assertEqual(rep.fx6_language_count, 4)
        self.assertEqual(len(rep.fx6_string_packs), 8)
        self.assertTrue(rep.all_cjk_en_standard_glyphs_100pct_covered)
        self.assertTrue(rep.ns2_100pct_glyph_coverage_verified)

    def test_env_force_clean_room_disables_donor_access(self) -> None:
        rep = verify_multilang_and_fonts(env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"})
        self.assertTrue(rep.all_checks_passed)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC_VERIFIED")

    def test_string_pack_slot_count_mismatch_detected(self) -> None:
        en_raw = build_synthetic_uxc_string_pack(("One", "Two", "Three"), namespace_id=2)
        sc_raw = build_synthetic_uxc_string_pack(("一", "二"), namespace_id=2)
        en_ns, en_slots, en_map, _, _, _ = parse_uxc_string_pack_slots(en_raw)
        audit, _, _, _ = audit_string_pack_bytes(
            sc_raw,
            filename="string_simplifiedchinese_2.uxc",
            language="simplifiedchinese",
            reference_ns_id=en_ns,
            reference_slots=en_slots,
            reference_map=en_map,
        )
        self.assertFalse(audit.valid)
        self.assertFalse(audit.parity_with_english_ok)
        self.assertGreater(audit.slot_mismatch_count, 0)

    def test_string_pack_resid16_shift_detected(self) -> None:
        en_raw = build_synthetic_uxc_string_pack(("One", "Two"), namespace_id=2)
        sc_raw = bytearray(build_synthetic_uxc_string_pack(("一", "二"), namespace_id=2))
        en_ns, en_slots, en_map, _, _, _ = parse_uxc_string_pack_slots(en_raw)
        # Mutate resid16 of record 0 in sc_raw
        rec_base = 16 + ((2 + 1) & ~1) * 2
        struct.pack_into("<H", sc_raw, rec_base, 0x7FFF)
        audit, _, _, _ = audit_string_pack_bytes(
            bytes(sc_raw),
            filename="string_sc_shift.uxc",
            language="simplifiedchinese",
            reference_ns_id=en_ns,
            reference_slots=en_slots,
            reference_map=en_map,
        )
        self.assertFalse(audit.valid)
        self.assertFalse(audit.parity_with_english_ok)
        self.assertEqual(audit.slot_mismatch_count, 1)

    def test_string_pack_invalid_utf8_rejected(self) -> None:
        raw = bytearray(build_synthetic_uxc_string_pack(("Valid", "ABC"), namespace_id=2))
        # Overwrite 'ABC' bytes with invalid UTF-8 lead bytes
        idx = raw.find(b"ABC")
        self.assertGreater(idx, 0)
        raw[idx : idx + 3] = b"\xff\xfe\x80"
        audit, _, _, _ = audit_string_pack_bytes(
            bytes(raw),
            filename="string_corrupt_utf8.uxc",
            language="japanese",
        )
        self.assertFalse(audit.valid)
        self.assertFalse(audit.utf8_valid)
        self.assertEqual(audit.truncated_or_corrupt_entries, 1)

    def test_string_pack_unterminated_and_oob_record_rejected(self) -> None:
        raw = bytearray(build_synthetic_uxc_string_pack(("Hello",), namespace_id=1))
        # Remove NUL terminator by replacing trailing 0s with 'x'
        pos = raw.find(b"Hello")
        for i in range(pos + 5, len(raw)):
            raw[i] = ord("x")
        _ns, _sl, _mp, _emp, corrupt, errs = parse_uxc_string_pack_slots(bytes(raw))
        self.assertGreater(corrupt, 0)
        self.assertTrue(any("unterminated" in e for e in errs))

        # OOB slot offset
        raw2 = bytearray(build_synthetic_uxc_string_pack(("Hello",), namespace_id=1))
        struct.pack_into("<H", raw2, 16, 0x7000)
        _ns2, _sl2, _mp2, _emp2, corrupt2, errs2 = parse_uxc_string_pack_slots(bytes(raw2))
        self.assertGreater(corrupt2, 0)
        self.assertTrue(any("out of bounds" in e for e in errs2))

    def test_string_pack_bad_magic_and_header_flag_rejected(self) -> None:
        bad_magic = b"bad!" + build_synthetic_uxc_string_pack(("A",))[4:]
        _, _, _, _, _, errs = parse_uxc_string_pack_slots(bad_magic)
        self.assertTrue(any("Expected" in e for e in errs))

        bad_flag = bytearray(build_synthetic_uxc_string_pack(("A",)))
        struct.pack_into("<H", bad_flag, 8, 99)
        _, _, _, _, _, errs2 = parse_uxc_string_pack_slots(bytes(bad_flag))
        self.assertTrue(any("header_flag" in e for e in errs2))


class TestFontCmapAndGlyphCoverage(unittest.TestCase):
    def test_synthetic_ttf_cmap_format4_bmp_cjk_roundtrip(self) -> None:
        cps = [ord(c) for c in "AB电影曝光指數シネマ"]
        ttf = build_synthetic_ttf_cmap(cps)
        summ, mapped = extract_font_cmap_coverage(ttf, filename="bmp_cjk.ttf", source_mode="SYNTHETIC")
        self.assertTrue(summ.valid, msg=f"Errors: {summ.errors}")
        self.assertEqual(summ.container_type, "TTF")
        self.assertIn(4, summ.cmap_formats_parsed)
        self.assertTrue(set(cps).issubset(mapped))

    def test_synthetic_ttf_cmap_format12_non_bmp_cjk_ext_b(self) -> None:
        cps = [0x4E2D, 0x20000, 0x20001, 0x2A6D6]
        ttf = build_synthetic_ttf_cmap(cps)
        summ, mapped = extract_font_cmap_coverage(ttf, filename="ext_b.ttf", source_mode="SYNTHETIC")
        self.assertTrue(summ.valid)
        self.assertIn(12, summ.cmap_formats_parsed)
        self.assertEqual(summ.non_bmp_codepoint_count, 3)
        for cp in cps:
            self.assertIn(cp, mapped)

    def test_ttf_cmap_format4_id_range_offset_nonzero(self) -> None:
        # Build hand-crafted format 4 subtable with 2 segments (0x4E00..0x4E02 via glyphIdArray, 0xFFFF sentinel)
        # glyphIdArray: [10, 0, 12] -> 0x4E00 mapped, 0x4E01 unmapped (gid=0), 0x4E02 mapped
        seg_count = 2
        fmt4_len = 16 + seg_count * 8 + 3 * 2
        fmt4 = bytearray(struct.pack(">HHHHHHH", 4, fmt4_len, 0, seg_count * 2, 4, 1, 0))
        fmt4.extend(struct.pack(">2H", 0x4E02, 0xFFFF))  # endCodes
        fmt4.extend(b"\x00\x00")
        fmt4.extend(struct.pack(">2H", 0x4E00, 0xFFFF))  # startCodes
        fmt4.extend(struct.pack(">2h", 0, 1))  # idDelta
        # idRangeOffset for seg 0 points 4 bytes forward (past seg0 + seg1 slots) into glyphIdArray
        fmt4.extend(struct.pack(">2H", 4, 0))
        fmt4.extend(struct.pack(">3H", 10, 0, 12))

        cmap = struct.pack(">HH", 0, 1) + struct.pack(">HHI", 3, 1, 12) + bytes(fmt4)
        sfnt = (
            struct.pack(">IHHHH", 0x00010000, 1, 16, 0, 0)
            + struct.pack(">4sIII", b"cmap", 0, 28, len(cmap))
            + cmap
        )
        summ, mapped = extract_font_cmap_coverage(sfnt, filename="range_off.ttf", source_mode="SYNTHETIC")
        self.assertTrue(summ.valid)
        self.assertEqual(mapped, {0x4E00, 0x4E02})

    def test_ttc_font_collection_parsing(self) -> None:
        ttf1 = build_synthetic_ttf_cmap([0x41, 0x42])
        ttf2 = build_synthetic_ttf_cmap([0x4E2D, 0x6587])
        # Build TTC v1 header (12 + 2*4 = 20 bytes), adjusting table offsets inside each embedded sfnt
        off1 = 20
        off2 = off1 + len(ttf1)

        def _rebase_sfnt(raw: bytes, base: int) -> bytes:
            buf = bytearray(raw)
            nt = struct.unpack_from(">H", buf, 4)[0]
            for i in range(nt):
                cur_off = struct.unpack_from(">I", buf, 12 + i * 16 + 8)[0]
                struct.pack_into(">I", buf, 12 + i * 16 + 8, cur_off + base)
            return bytes(buf)

        ttc = (
            struct.pack(">4sIII", b"ttcf", 0x00010000, 2, off1)
            + struct.pack(">I", off2)
            + _rebase_sfnt(ttf1, off1)
            + _rebase_sfnt(ttf2, off2)
        )
        summ, mapped = extract_font_cmap_coverage(ttc, filename="combo.ttc", source_mode="SYNTHETIC")
        self.assertTrue(summ.valid)
        self.assertEqual(summ.container_type, "TTC")
        self.assertEqual(summ.embedded_sfnt_count, 2)
        self.assertEqual(mapped, {0x41, 0x42, 0x4E2D, 0x6587})

    def test_ltt_linked_font_container_parsing(self) -> None:
        sfnt1 = build_synthetic_ttf_cmap([0x41, 0x42])
        sfnt2 = build_synthetic_ttf_cmap([0x65E5, 0x672C])
        hdr_prefix = b"LTT\n7\n2\n"
        # Reserve 512 bytes for ASCII header so offsets are fixed
        off1 = 512
        off2 = off1 + len(sfnt1)
        hdr_body = (
            f"LTT\n7\n2\nembeddedoffset={off1}\nembeddedsize={len(sfnt1)}\n"
            f"embeddedoffset={off2}\nembeddedsize={len(sfnt2)}\n"
        ).encode("ascii")
        hdr = hdr_body.ljust(512, b" ")
        blob = hdr + sfnt1 + sfnt2
        summ, mapped = extract_font_cmap_coverage(blob, filename="linked.ltt", source_mode="SYNTHETIC")
        self.assertTrue(summ.valid, msg=f"Errors: {summ.errors}")
        self.assertEqual(summ.container_type, "LTT")
        self.assertEqual(summ.embedded_sfnt_count, 2)
        self.assertEqual(mapped, {0x41, 0x42, 0x65E5, 0x672C})

    def test_ltt_corrupt_bounds_and_unknown_font_magic_rejected(self) -> None:
        bad_ltt = b"LTT\n7\n2\nembeddedoffset=999999\nembeddedsize=500\n"
        summ1, mapped1 = extract_font_cmap_coverage(bad_ltt, filename="bad.ltt")
        self.assertFalse(summ1.valid)
        self.assertEqual(len(mapped1), 0)

        bad_magic = b"NOPE" + bytes(32)
        summ2, _ = extract_font_cmap_coverage(bad_magic, filename="bad.bin")
        self.assertFalse(summ2.valid)
        self.assertEqual(summ2.container_type, "UNKNOWN")

    def test_evaluate_language_glyph_coverage_detects_missing_cjk_glyph(self) -> None:
        cov = evaluate_language_glyph_coverage(
            "simplifiedchinese",
            2,
            "string_sc.uxc",
            {0x4E2D, 0x6587, 0x9F99},
            set(),
            {0x4E2D, 0x6587},
        )
        self.assertFalse(cov.all_standard_glyphs_covered)
        self.assertEqual(cov.standard_missing_codepoints, ("0x9f99",))
        self.assertLess(cov.standard_coverage_pct, 100.0)

    def test_evaluate_language_glyph_coverage_separates_pua_icons(self) -> None:
        cov = evaluate_language_glyph_coverage(
            "english",
            1,
            "string_english.uxc",
            {0x41, 0x42},
            {0xE6DA},
            {0x41, 0x42},
        )
        self.assertTrue(cov.all_standard_glyphs_covered)
        self.assertEqual(cov.standard_coverage_pct, 100.0)
        self.assertEqual(cov.pua_missing_codepoints, ("0xe6da",))


class TestFastLdecSweepAndCli(unittest.TestCase):
    def test_fast_decode_matches_reference_ldec_decoder(self) -> None:
        # Mix of 2-byte pixel repeats (distance=2), 4-byte repeats, and raw literals
        raw_payload = (
            bytes(range(64))
            + (b"\x12\x34" * 80)
            + (b"\xAA\xBB\xCC\xDD" * 50)
            + b"\x01\x02\x03\x04\x05\x06\x07\x08\x09"
        )
        comp_lz = encode_ldec_lz77_raw_or_match(raw_payload, prefer_lz77=True)
        ref_dec, _ = decode_ldec_lz77(comp_lz, expected_output_len=len(raw_payload))
        fast_dec = fast_decode_ldec_lz77(comp_lz, expected_output_len=len(raw_payload))
        self.assertEqual(fast_dec, raw_payload)
        self.assertEqual(fast_dec, ref_dec)

        comp_raw = encode_ldec_lz77_raw_or_match(raw_payload, prefer_lz77=False)
        self.assertEqual(fast_decode_ldec_lz77(comp_raw, expected_output_len=len(raw_payload)), raw_payload)

    def test_fast_decode_bounds_and_error_guards(self) -> None:
        with self.assertRaises(LdecDecodeError):
            fast_decode_ldec_lz77(b"")
        with self.assertRaises(LdecDecodeError):
            fast_decode_ldec_lz77(b"\x99\x00\x00", expected_output_len=4)
        with self.assertRaises(LdecDecodeError):
            fast_decode_ldec_lz77(b"\xF0\x01\x00\x05", expected_output_len=3)
        with self.assertRaises(LdecDecodeError):
            fast_decode_ldec_lz77(b"\x0F\x00\x10\x00\xAA", expected_output_len=16)

    def test_sweep_uxd_sprite_atlas_checksum_and_corruption_guard(self) -> None:
        px0 = struct.pack("<H", 0xF00F) * (16 * 2)
        px1 = bytes([0x7F]) * (16 * 2)
        uxd = bytearray(
            build_synthetic_uxd_sprite_pack(
                (
                    (8, 2, PIXEL_FMT_RGBA4444, px0, False, True),
                    (6, 2, PIXEL_FMT_A8, px1, False, False),
                ),
                namespace_id=0,
            )
        )
        ok_sw = sweep_uxd_sprite_atlas(bytes(uxd), body="SYNTHETIC", filename="img.uxd")
        self.assertTrue(ok_sw.valid)
        self.assertEqual(ok_sw.sprites_passed, 2)
        self.assertEqual(len(ok_sw.atlas_sha256), 64)

        from fx3_firmware_lab.uxc_ldec_inspector import parse_uxc_sprites

        sps = parse_uxc_sprites(bytes(uxd))
        # Flip a raw pixel byte in sprite 1 (0x0F raw block): succeeds with different SHA-256
        uxd_px_tamper = bytearray(uxd)
        uxd_px_tamper[sps[1].payload_offset + 5] ^= 0x55
        tamper_sw = sweep_uxd_sprite_atlas(bytes(uxd_px_tamper), body="SYNTHETIC", filename="img.uxd")
        self.assertTrue(tamper_sw.valid)
        self.assertNotEqual(tamper_sw.atlas_sha256, ok_sw.atlas_sha256)

        # Corrupt LDEC block kind byte at sprite 0 payload_offset -> fails sweep
        uxd[sps[0].payload_offset] ^= 0xFF
        bad_sw = sweep_uxd_sprite_atlas(bytes(uxd), body="SYNTHETIC", filename="img.uxd")
        self.assertFalse(bad_sw.valid)
        self.assertGreater(bad_sw.sprites_failed, 0)

    def test_cli_audit_multilang_clean_room_deterministic_json(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(PKG_ROOT)
        proc1 = subprocess.run(
            [sys.executable, "-B", "-m", "fx3_firmware_lab", "audit-multilang", "--clean-room"],
            capture_output=True,
            text=True,
            env=env,
            check=True,
        )
        proc2 = subprocess.run(
            [sys.executable, "-B", "-m", "fx3_firmware_lab", "audit-multilang", "--clean-room"],
            capture_output=True,
            text=True,
            env=env,
            check=True,
        )
        self.assertEqual(proc1.stdout, proc2.stdout)
        parsed = json.loads(proc1.stdout)
        self.assertTrue(parsed["all_checks_passed"])
        self.assertFalse(parsed["hardware_ldec_required"])

    def test_cli_audit_multilang_and_audit_all_in_process(self) -> None:
        buf = StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-multilang", "--clean-room"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertTrue(parsed["all_checks_passed"])

        all_res = run_audit_all(clean_room=True)
        self.assertTrue(all_res["all_checks_passed"])
        self.assertIn("uxc_multilang_and_font_audit", all_res)


if __name__ == "__main__":
    unittest.main()
