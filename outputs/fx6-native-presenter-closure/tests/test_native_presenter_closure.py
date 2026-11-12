#!/usr/bin/env python3
"""Offline clean-room unit tests for FX6 native presenter closure (Rounds 1-6)."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import re
import struct
import sys
import tempfile
import unittest
import zlib
from typing import Dict, List, Tuple

TESTS_DIR = pathlib.Path(__file__).resolve().parent
CLOSURE_DIR = TESTS_DIR.parent
REPO_ROOT = CLOSURE_DIR.parent.parent
REPORT_DIR = REPO_ROOT / "reports" / "2026-11-10-fx6-native-presenter-closure"
ASSETS_DIR = REPORT_DIR / "assets"


def _load_closure_module(module_name: str, filename: str):
    path = CLOSURE_DIR / filename
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


def _parse_and_validate_png(png_bytes: bytes) -> Tuple[int, int, bytes]:
    if png_bytes[:8] != b"\x89PNG\r\n\x1a\n":
        raise AssertionError("Invalid PNG signature")
    pos = 8
    seen_ihdr = False
    seen_iend = False
    width = 0
    height = 0
    idat_parts: List[bytes] = []
    n_len = len(png_bytes)
    while pos < n_len:
        if pos + 8 > n_len:
            raise AssertionError("Truncated PNG chunk header")
        length = struct.unpack_from(">I", png_bytes, pos)[0]
        ctype = png_bytes[pos + 4 : pos + 8]
        data_start = pos + 8
        data_end = data_start + length
        crc_end = data_end + 4
        if crc_end > n_len:
            raise AssertionError(f"Truncated PNG chunk {ctype!r}")
        payload = png_bytes[data_start:data_end]
        expected_crc = struct.unpack_from(">I", png_bytes, data_end)[0]
        actual_crc = zlib.crc32(ctype + payload) & 0xFFFFFFFF
        if actual_crc != expected_crc:
            raise AssertionError(
                f"CRC mismatch in chunk {ctype!r}: 0x{actual_crc:08x} != 0x{expected_crc:08x}"
            )
        if ctype == b"IHDR":
            if len(payload) != 13:
                raise AssertionError(f"Invalid IHDR length {len(payload)}")
            width, height, bit_depth, color_type, comp, filt, interlace = struct.unpack(
                ">IIBBBBB", payload
            )
            if (bit_depth, color_type, comp, filt, interlace) != (8, 6, 0, 0, 0):
                raise AssertionError(
                    f"Unexpected IHDR format {(bit_depth, color_type, comp, filt, interlace)}"
                )
            seen_ihdr = True
        elif ctype == b"IDAT":
            idat_parts.append(payload)
        elif ctype == b"IEND":
            seen_iend = True
            pos = crc_end
            break
        pos = crc_end
    if not seen_ihdr or not seen_iend or pos != n_len:
        raise AssertionError("Incomplete or trailing bytes in PNG stream")
    raw_scanlines = zlib.decompress(b"".join(idat_parts))
    expected_scanline_bytes = (width * 4 + 1) * height
    if len(raw_scanlines) != expected_scanline_bytes:
        raise AssertionError(
            f"Decompressed IDAT size {len(raw_scanlines)} != {expected_scanline_bytes}"
        )
    return width, height, raw_scanlines


class TestPixelUnpackingAndPngExport(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = _load_closure_module(
            "fx6_build_and_run_round", "build_and_run_round.py"
        )

    def test_rgba4444_synthetic_vectors(self) -> None:
        self.assertEqual(self.runner.unpack_rgba4444_pixel(0x0000), (0, 0, 0, 0))
        self.assertEqual(self.runner.unpack_rgba4444_pixel(0xFFFF), (255, 255, 255, 255))
        self.assertEqual(self.runner.unpack_rgba4444_pixel(0xF84C), (255, 136, 68, 204))
        self.assertEqual(self.runner.unpack_rgba4444_pixel(0x1234), (17, 34, 51, 68))

        packed = struct.pack("<HHHH", 0x0000, 0xF00F, 0x0F08, 0x00FF)
        unpacked = self.runner.unpack_rgba4444_buffer(packed)
        expected = bytes(
            [
                0, 0, 0, 0,
                255, 0, 0, 255,
                0, 255, 0, 136,
                0, 0, 255, 255,
            ]
        )
        self.assertEqual(unpacked, expected)
        with self.assertRaises(ValueError):
            self.runner.unpack_rgba4444_buffer(b"\x01\x02\x03")

    def test_rgba8888_synthetic_vectors(self) -> None:
        px = bytes([0x12, 0x34, 0x56, 0x78])
        self.assertEqual(self.runner.unpack_rgba8888_pixel(px), (0x12, 0x34, 0x56, 0x78))
        with self.assertRaises(ValueError):
            self.runner.unpack_rgba8888_pixel(b"\x00\x01\x02")

        src_rgba = bytes([0xAA, 0xBB, 0xCC, 0xDD, 0x10, 0x20, 0x30, 0xFF])
        gpe_bgra = self.runner.unpack_rgba8888_buffer(src_rgba)
        u0, u1 = struct.unpack("<II", gpe_bgra)
        self.assertEqual(u0, 0xDDAABBCC)
        self.assertEqual(u1, 0xFF102030)
        with self.assertRaises(ValueError):
            self.runner.unpack_rgba8888_buffer(b"\x01\x02")

    def test_write_rgba_png_and_export_gpe0_pngs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            # 1. Small synthetic 4x2 PNG round-trip
            rgba_small = bytes(
                [
                    255, 0, 0, 255,   0, 255, 0, 128,   0, 0, 255, 0,   255, 255, 255, 64,
                    17, 34, 51, 255,  68, 85, 102, 255, 0, 0, 0, 0,     240, 180, 30, 255,
                ]
            )
            small_png = tmp_dir / "small.png"
            meta = self.runner.write_rgba_png(small_png, 4, 2, rgba_small)
            self.assertEqual(meta["bytes"], small_png.stat().st_size)
            w, h, scan = _parse_and_validate_png(small_png.read_bytes())
            self.assertEqual((w, h), (4, 2))
            self.assertEqual(scan[1:17], rgba_small[:16])
            self.assertEqual(scan[18:34], rgba_small[16:32])

            # 2. Full 1024x540 GPE0 export_gpe0_pngs round-trip
            raw_fb = bytearray(self.runner.FB_BYTES)
            # Pixel 0: opaque orange 0xFFFF8800 -> LE [0x00, 0x88, 0xFF, 0xFF]
            struct.pack_into("<I", raw_fb, 0, 0xFFFF8800)
            # Pixel 1: 50% white 0x80FFFFFF
            struct.pack_into("<I", raw_fb, 4, 0x80FFFFFF)
            # Pixel 2: transparent 0x00000000 -> backdrop #161a20 in composited
            raw_path = tmp_dir / "synthetic.gpe0"
            raw_path.write_bytes(raw_fb)

            stats = self.runner.analyze_gpe0_raw(raw_path)
            self.assertTrue(stats["present"])
            self.assertEqual(stats["total_pixels"], 1024 * 540)
            self.assertEqual(stats["nonzero_pixels"], 2)
            self.assertEqual(stats["unique_colors"], 3)

            exported = self.runner.export_gpe0_pngs(raw_path, tmp_dir, "synth")
            self.assertEqual(exported["transparent_pixels"], 1024 * 540 - 1)
            _, _, alpha_scan = _parse_and_validate_png(
                pathlib.Path(exported["alpha_png"]["path"]).read_bytes()
            )
            _, _, comp_scan = _parse_and_validate_png(
                pathlib.Path(exported["composited_png"]["path"]).read_bytes()
            )
            # Row 0 filter byte = 0, then pixel 0..2
            self.assertEqual(tuple(alpha_scan[1:5]), (0xFF, 0x88, 0x00, 0xFF))
            self.assertEqual(tuple(alpha_scan[5:9]), (0xFF, 0xFF, 0xFF, 0x80))
            self.assertEqual(tuple(alpha_scan[9:13]), (0x00, 0x00, 0x00, 0x00))

            self.assertEqual(tuple(comp_scan[1:5]), (0xFF, 0x88, 0x00, 0xFF))
            self.assertEqual(tuple(comp_scan[9:13]), (0x16, 0x1A, 0x20, 0xFF))

    def test_parse_key_seq(self) -> None:
        steps = self.runner.parse_key_seq("0x718c:120:4500, 0x7023:10:5, 0x01ac:120:900")
        self.assertEqual(
            steps,
            [(0x718C, 120, 4500), (0x7023, 20, 20), (0x01AC, 120, 900)],
        )
        self.assertEqual(self.runner.parse_key_seq(""), [])
        with self.assertRaises(ValueError):
            self.runner.parse_key_seq("0x718c:120")


class TestStaticContractsAndSourceGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contracts_path = CLOSURE_DIR / "static-contracts-summary.json"
        cls.contracts = json.loads(cls.contracts_path.read_text(encoding="utf-8"))
        cls.shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        cls.launch_src = (CLOSURE_DIR / "appfw-launch.c").read_text(encoding="utf-8")

    def test_static_contracts_schema_and_keys(self) -> None:
        for top_key in (
            "donor_root",
            "digests",
            "imdb_highlights",
            "snippet_line_counts",
            "round4_contracts",
            "round5_contracts",
            "round6_contracts",
        ):
            self.assertIn(top_key, self.contracts)

        # Round 4 UIPC & NVRAM contracts
        r4 = self.contracts["round4_contracts"]
        self.assertIn("0x80cf016d", r4["uipc_queues"])
        self.assertEqual(r4["uipc_queues"]["0x80cf016d"]["service"], "SeqQueueNetwork")
        self.assertIn("0x92840747", r4["uipc_queues"])
        self.assertEqual(r4["nvram_backup"]["donor_bk4"], "CX95898_NTSC.bin")

        # Round 5 pixel formats & InfraInput key codebook
        r5 = self.contracts["round5_contracts"]
        self.assertEqual(r5["bmp_pixel_formats"]["1"]["stella_gpe_fmt"], 7)
        self.assertEqual(r5["bmp_pixel_formats"]["2"]["stella_gpe_fmt"], 1)
        msg32 = r5["infra_input_key_msg_32b"]
        self.assertEqual(msg32["src_qid"], "0x007a804c")
        self.assertEqual(msg32["dest_qid"], "0x005503e0")
        self.assertEqual(msg32["size_bytes"], 32)
        keycodes = msg32["verified_keycodes"]
        for required_key in (
            "0x718c",
            "0x01ab",
            "0x01ac",
            "0x0003",
            "0x0030",
            "0x0015",
            "0x01af",
            "0x719a",
            "0x7023",
            "0x704d",
            "0x704f",
            "0x7098",
            "0x7177",
            "0x7180",
        ):
            self.assertIn(required_key, keycodes)

        # Round 6 presenter RTTI / sid & sid=0xc9 notice origin
        r6 = self.contracts["round6_contracts"]
        self.assertEqual(r6["sid_0xc9_notice_origin"]["sid"], "0xc9")
        self.assertEqual(
            r6["sid_0xc9_notice_origin"]["presenter_rtti"],
            "27procam_msg_2label_presenter",
        )
        self.assertEqual(
            r6["sid_0xc9_notice_origin"]["controller_rtti"],
            "28procam_msg_2label_controller",
        )
        presenters = r6["presenters_verified"]
        expected_presenters = {
            "0x14": "37procam_menu_initial_setting_presenter",
            "0x02": "25procam_shooting_presenter",
            "0x0a": "31procam_big6_menu_home_presenter",
            "0x0c": "34procam_big6_menu_setting_presenter",
            "0x0f": "31procam_menu_layer_1st_presenter",
            "0x10": "31procam_menu_layer_2nd_presenter",
            "0xc9": "27procam_msg_2label_presenter",
        }
        for sid_hex, rtti_name in expected_presenters.items():
            self.assertIn(sid_hex, presenters)
            self.assertEqual(presenters[sid_hex]["presenter_rtti"], rtti_name)

    def test_native_faithful_c_source_guards(self) -> None:
        # Both C sources must default FX6_NATIVE_FAITHFUL to 1 and FX6_ROUND >= 5 when faithful
        for name, src in (
            ("libgrm-fbinit9.c", self.shim_src),
            ("appfw-launch.c", self.launch_src),
        ):
            self.assertRegex(
                src,
                r"#ifndef\s+FX6_NATIVE_FAITHFUL\s+#define\s+FX6_NATIVE_FAITHFUL\s+1\s+#endif",
                f"{name} missing FX6_NATIVE_FAITHFUL=1 default guard",
            )
            self.assertRegex(
                src,
                r"#ifndef\s+FX6_ROUND\s+#define\s+FX6_ROUND\s+\(FX6_NATIVE_FAITHFUL\s*\?\s*6\s*:\s*3\)",
                f"{name} must default FX6_ROUND to 6 under FX6_NATIVE_FAITHFUL=1",
            )

        # Verify FX6_RESTORE_ALL_EARLY & FX6_RESTORE_INFRA70 default to 1 when FX6_NATIVE_FAITHFUL=1
        self.assertIn(
            "#define FX6_RESTORE_ALL_EARLY ((FX6_NATIVE_FAITHFUL && (FX6_ROUND >= 5)) ? 1 : 0)",
            self.shim_src,
        )
        self.assertIn(
            "#define FX6_RESTORE_INFRA70 ((FX6_NATIVE_FAITHFUL && (FX6_ROUND >= 5)) ? 1 : 0)",
            self.shim_src,
        )

        # Verify fx6_patch_blocking_calls only adds NOPs under !FX6_RESTORE_ALL_EARLY or FX6_ROUND < 3
        patch_m = re.search(
            r"static void fx6_patch_blocking_calls\(.*?\n\}\n",
            self.shim_src,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(patch_m)
        patch_body = patch_m.group(0)
        self.assertIn("#if !FX6_RESTORE_ALL_EARLY", patch_body)
        self.assertIn("#if FX6_ROUND < 3", patch_body)
        # Ensure no unconditional offs[count++] exists outside those two legacy diagnostic guards
        stripped = re.sub(
            r"#if !FX6_RESTORE_ALL_EARLY.*?#endif\s*#endif",
            "",
            patch_body,
            flags=re.DOTALL,
        )
        stripped = re.sub(r"#if FX6_ROUND < 3.*?#endif", "", stripped, flags=re.DOTALL)
        self.assertNotIn("offs[count++]", stripped)

        # Enforce zero presenter/color/image substitution invariant banner
        self.assertIn(
            "subst_color=0 subst_image=0 forced_render=0 skipped_node=0 lock_bypass=0",
            self.shim_src,
        )
        for forbidden in ("subst_presenter", "fake_presenter", "synthetic_widget"):
            self.assertNotIn(forbidden, self.shim_src.lower())
            self.assertNotIn(forbidden, self.launch_src.lower())

    def test_clean_room_directory_hygiene(self) -> None:
        forbidden_suffixes = {".cpio", ".so", ".fb", ".raw", ".o", ".dylib", ".pyc"}
        for root in (CLOSURE_DIR, REPORT_DIR):
            for p in root.rglob("*"):
                if p.is_file():
                    self.assertNotIn(
                        p.suffix.lower(),
                        forbidden_suffixes,
                        f"Forbidden binary/bytecode artifact in tracked tree: {p}",
                    )


class TestReportPngAssets(unittest.TestCase):
    DISTINCT_PRESENTER_STEMS = (
        "r5a-initial-setting",
        "r5b-shooting-hud",
        "r5c-big6-menu-home",
        "r5d-menu-layer-1st",
        "r6a-big6-subdialog",
        "r6b-menu-layer-2nd",
    )
    EXPECTED_STEMS = DISTINCT_PRESENTER_STEMS + ("r6c-back-to-shooting",)

    def test_all_png_receipts_valid_and_distinct(self) -> None:
        self.assertTrue(ASSETS_DIR.is_dir(), f"Missing assets dir: {ASSETS_DIR}")
        alpha_digests: Dict[str, str] = {}
        comp_digests: Dict[str, str] = {}

        # Validate every *.png in assets/ plus ensure all expected r5a..r6c stems exist
        all_pngs = sorted(ASSETS_DIR.glob("*.png"))
        self.assertGreaterEqual(len(all_pngs), len(self.EXPECTED_STEMS) * 2)
        for png_path in all_pngs:
            raw = png_path.read_bytes()
            w, h, _ = _parse_and_validate_png(raw)
            self.assertEqual((w, h), (1024, 540), f"Unexpected dimensions in {png_path.name}")

        for stem in self.EXPECTED_STEMS:
            for variant, bucket in (("alpha", alpha_digests), ("composited", comp_digests)):
                png_path = ASSETS_DIR / f"{stem}-{variant}.png"
                self.assertTrue(png_path.is_file(), f"Missing PNG receipt: {png_path}")
                bucket[stem] = hashlib.sha256(png_path.read_bytes()).hexdigest()

        # All 6 distinct presenters (sid=0x14, 0x02, 0x0a, 0x0f, 0x0c, 0x10) must be pairwise distinct
        distinct_alpha = {alpha_digests[s] for s in self.DISTINCT_PRESENTER_STEMS}
        distinct_comp = {comp_digests[s] for s in self.DISTINCT_PRESENTER_STEMS}
        self.assertEqual(
            len(distinct_alpha),
            len(self.DISTINCT_PRESENTER_STEMS),
            f"Duplicate alpha PNG SHA-256 across distinct presenters: {alpha_digests}",
        )
        self.assertEqual(
            len(distinct_comp),
            len(self.DISTINCT_PRESENTER_STEMS),
            f"Duplicate composited PNG SHA-256 across distinct presenters: {comp_digests}",
        )

        # r6c-back-to-shooting closes Big6 Home (337,227 px) via Presenter::close and must restore
        # 25procam_shooting_presenter (r5b-shooting-hud, 5,451 px) bit-for-bit with zero stale Big6 pixels
        self.assertEqual(
            alpha_digests["r6c-back-to-shooting"],
            alpha_digests["r5b-shooting-hud"],
        )
        self.assertEqual(
            comp_digests["r6c-back-to-shooting"],
            comp_digests["r5b-shooting-hud"],
        )
        for overlay_stem in (
            "r5a-initial-setting",
            "r5c-big6-menu-home",
            "r5d-menu-layer-1st",
            "r6a-big6-subdialog",
            "r6b-menu-layer-2nd",
        ):
            self.assertNotEqual(
                alpha_digests["r6c-back-to-shooting"],
                alpha_digests[overlay_stem],
            )


class TestOptionalDonorBinariesReadOnly(unittest.TestCase):
    @staticmethod
    def _verify_donor_root(tc: unittest.TestCase, donor_root: pathlib.Path, contracts: dict) -> None:
        if not donor_root.exists():
            tc.skipTest(f"Optional external donor tree absent: {donor_root}")
        appfw_path = donor_root / "lib" / "appFw.so"
        if not appfw_path.exists():
            tc.skipTest(f"Optional donor appFw.so absent: {appfw_path}")
        tc.assertEqual(
            appfw_path.stat().st_size,
            contracts["digests"]["lib/appFw.so"]["size_bytes"],
        )
        with appfw_path.open("rb") as f:
            f.seek(0x2245A10)
            table_bytes = f.read(449 * 8)
        mapping = dict(struct.iter_unpack("<II", table_bytes))
        tc.assertEqual(mapping.get(0x0003), 0x0002)  # UP
        tc.assertEqual(mapping.get(0x0015), 0x0004)  # LEFT
        tc.assertEqual(mapping.get(0x0030), 0x0006)  # DOWN
        tc.assertEqual(mapping.get(0x01AF), 0x0016)  # RIGHT
        tc.assertEqual(mapping.get(0x01AB), 0x0013)  # MENU
        tc.assertEqual(mapping.get(0x01AC), 0x0014)  # ENTER
        tc.assertEqual(mapping.get(0x7023), 0x0029)  # KURU_PON
        tc.assertEqual(mapping.get(0x718C), 0x0184)  # HOME
        tc.assertEqual(mapping.get(0x719A), 0x0192)  # CANCEL

    def test_donor_digests_and_key_table_when_present(self) -> None:
        contracts = json.loads(
            (CLOSURE_DIR / "static-contracts-summary.json").read_text(encoding="utf-8")
        )
        self._verify_donor_root(self, pathlib.Path(contracts["donor_root"]), contracts)

    def test_absent_donor_tree_skips_gracefully_offline(self) -> None:
        contracts = json.loads(
            (CLOSURE_DIR / "static-contracts-summary.json").read_text(encoding="utf-8")
        )
        missing = pathlib.Path("/nonexistent/fx3-color-port-20261027/absent-donor")
        with self.assertRaises(unittest.SkipTest):
            self._verify_donor_root(self, missing, contracts)


if __name__ == "__main__":
    unittest.main()
