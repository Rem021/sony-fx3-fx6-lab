#!/usr/bin/env python3
"""Offline clean-room unit tests for FX6 native presenter closure (Rounds 1-23)."""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import struct
import sys
import tempfile
import unittest
import zlib
from typing import Dict, List, Tuple
from unittest import mock

TESTS_DIR = pathlib.Path(__file__).resolve().parent
CLOSURE_DIR = TESTS_DIR.parent
REPO_ROOT = CLOSURE_DIR.parent.parent
REPORT_DIR = REPO_ROOT / "reports" / "2026-11-10-fx6-native-presenter-closure"
ASSETS_DIR = REPORT_DIR / "assets"
HYBRID_REPORT_DIR = REPO_ROOT / "reports" / "2026-11-14-fx6-on-fx3-qemu-hybrid"
HYBRID_ASSETS_DIR = HYBRID_REPORT_DIR / "assets"
ROUND9_REPORT_DIR = REPO_ROOT / "reports" / "2026-11-14-round9-fx6-on-fx3-p10-presenter"
ROUND9_ASSETS_DIR = ROUND9_REPORT_DIR / "assets"
ROUND10_REPORT_DIR = REPO_ROOT / "reports" / "2026-11-14-round10-fx6-on-fx3-full-icon-presenter"
ROUND10_ASSETS_DIR = ROUND10_REPORT_DIR / "assets"
ROUND11_REPORT_DIR = REPO_ROOT / "reports" / "2026-11-14-round11-fx6-on-fx3-schinese-p12-presenter"
ROUND11_ASSETS_DIR = ROUND11_REPORT_DIR / "assets"
ROUND12_REPORT_DIR = REPO_ROOT / "reports" / "2026-11-14-round12-fx6-on-fx3-cjk-ja-p110-presenter"
ROUND12_ASSETS_DIR = ROUND12_REPORT_DIR / "assets"
ROUND13_REPORT_DIR = REPO_ROOT / "reports" / "2026-11-14-round13-fx6-on-fx3-status-4lang-closure"
ROUND13_ASSETS_DIR = ROUND13_REPORT_DIR / "assets"
ROUND14_REPORT_DIR = REPO_ROOT / "reports" / "2026-11-14-round14-fx6-on-fx3-statuscheck-4lang-matrix"
ROUND14_ASSETS_DIR = ROUND14_REPORT_DIR / "assets"
ROUND15_REPORT_DIR = REPO_ROOT / "reports" / "2026-11-14-round15-fx6-on-fx3-multitab-status-monitoring"
ROUND15_ASSETS_DIR = ROUND15_REPORT_DIR / "assets"
ROUND16_REPORT_DIR = REPO_ROOT / "reports" / "2026-11-14-round16-fx6-on-fx3-status-tabs45-tcmedia"
ROUND16_ASSETS_DIR = ROUND16_REPORT_DIR / "assets"
ROUND17_REPORT_DIR = REPO_ROOT / "reports" / "2026-11-14-round17-fx6-on-fx3-status-fullsweep-audio"
ROUND17_ASSETS_DIR = ROUND17_REPORT_DIR / "assets"
ROUND18_REPORT_DIR = REPO_ROOT / "reports" / "2026-11-14-round18-fx6-on-fx3-menu-8category-closure"
ROUND18_ASSETS_DIR = ROUND18_REPORT_DIR / "assets"
ROUND19_REPORT_DIR = REPO_ROOT / "reports" / "2026-11-14-round19-fx6-on-fx3-menu-11cat-fullsweep"
ROUND19_ASSETS_DIR = ROUND19_REPORT_DIR / "assets"
ROUND20_REPORT_DIR = REPO_ROOT / "reports" / "2026-11-14-round20-fx6-on-fx3-network-4lang-wf12-closure"
ROUND20_ASSETS_DIR = ROUND20_REPORT_DIR / "assets"
ROUND21_REPORT_DIR = REPO_ROOT / "reports" / "2026-11-14-round21-fx6-on-fx3-audio-4lang-dualsurface-closure"
ROUND21_ASSETS_DIR = ROUND21_REPORT_DIR / "assets"
ROUND22_REPORT_DIR = REPO_ROOT / "reports" / "2026-11-14-round22-fx6-on-fx3-paintlook-camera-4lang-closure"
ROUND22_ASSETS_DIR = ROUND22_REPORT_DIR / "assets"
ROUND23_REPORT_DIR = REPO_ROOT / "reports" / "2026-11-14-round23-fx6-on-fx3-monitoring-4lang-dualsurface-closure"
ROUND23_ASSETS_DIR = ROUND23_REPORT_DIR / "assets"


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


_DECODED_PNG_CACHE: Dict[bytes, Tuple[int, int, List[bytes]]] = {}


def _decode_png_rgba_rows(png_bytes: bytes) -> Tuple[int, int, List[bytes]]:
    cache_key = hashlib.sha256(png_bytes).digest()
    cached = _DECODED_PNG_CACHE.get(cache_key)
    if cached is not None:
        return cached
    width, height, raw_scanlines = _parse_and_validate_png(png_bytes)
    stride = width * 4
    rows: List[bytes] = []
    pos = 0
    prev = bytearray(stride)
    for _ in range(height):
        filt = raw_scanlines[pos]
        pos += 1
        row = bytearray(raw_scanlines[pos : pos + stride])
        pos += stride
        if filt == 1:
            for x in range(4, stride):
                row[x] = (row[x] + row[x - 4]) & 0xFF
        elif filt == 2:
            for x in range(stride):
                row[x] = (row[x] + prev[x]) & 0xFF
        elif filt == 3:
            for x in range(stride):
                a = row[x - 4] if x >= 4 else 0
                row[x] = (row[x] + ((a + prev[x]) >> 1)) & 0xFF
        elif filt == 4:
            for x in range(stride):
                a = row[x - 4] if x >= 4 else 0
                b = prev[x]
                c = prev[x - 4] if x >= 4 else 0
                pa = abs(b - c)
                pb = abs(a - c)
                pc = abs(a + b - 2 * c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                row[x] = (row[x] + pr) & 0xFF
        elif filt != 0:
            raise AssertionError(f"Unsupported PNG filter {filt}")
        prev = row
        rows.append(bytes(row))
    result = (width, height, rows)
    _DECODED_PNG_CACHE[cache_key] = result
    return result


def _diff_rows_u32(ra: List[bytes], rb: List[bytes]) -> int:
    import operator
    ne = operator.ne
    return sum(
        sum(map(ne, memoryview(ya).cast("I"), memoryview(yb).cast("I")))
        for ya, yb in zip(ra, rb)
        if ya != yb
    )


def _count_amber_u32(rows: List[bytes]) -> int:
    amber_word = int.from_bytes(b"\xff\xaa\x00\xff", sys.byteorder)
    return sum(
        sum(1 for px in memoryview(row).cast("I") if px == amber_word)
        for row in rows
        if b"\xff\xaa\x00\xff" in row
    )


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
            "round7_contracts",
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

        # Round 7 libbackup write ABI, Cine EI gating, Big6 grid, and deep presenters
        r7 = self.contracts["round7_contracts"]
        bk_abi = r7["libbackup_write_abi"]
        self.assertEqual(bk_abi["Backup_write"]["argc"], 3)
        self.assertEqual(bk_abi["Backup_write"]["ipc_cmd"], 9)
        self.assertEqual(bk_abi["Backup_write_vsize"]["argc"], 4)
        self.assertEqual(bk_abi["Backup_write_vsize"]["ipc_cmd"], 10)
        self.assertEqual(bk_abi["Backup_write_multi"]["argc"], 3)
        self.assertEqual(bk_abi["Backup_write_multi"]["ipc_cmd"], 11)
        self.assertEqual(set(r7["big6_grid_cells"]["cells"].keys()), {"0", "1", "2", "3", "4", "5"})
        self.assertIn("0x02cf0482", r7["cine_ei_nvram_gating"]["shooting_mode_bkid"])
        self.assertIn("0x02cf1373", r7["cine_ei_nvram_gating"]["cine_ei_submode_bkid"])

        r7_presenters = r7["presenters_verified"]
        expected_r7_presenters = {
            "0x0b": "38procam_big6_menu_look_middle_presenter",
            "0x11": "31procam_menu_layer_3rd_presenter",
            "0x17": "34procam_select_value_list_presenter",
            "0x5a": "43procam_msg_execute_confirm_common_presenter",
        }
        for sid_hex, rtti_name in expected_r7_presenters.items():
            self.assertIn(sid_hex, r7_presenters)
            self.assertEqual(r7_presenters[sid_hex]["presenter_rtti"], rtti_name)

    def test_native_faithful_c_source_guards(self) -> None:
        # Both C sources must default FX6_NATIVE_FAITHFUL to 1 and FX6_ROUND == 7 when faithful
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
                r"#ifndef\s+FX6_ROUND\s+#define\s+FX6_ROUND\s+\(FX6_NATIVE_FAITHFUL\s*\?\s*7\s*:\s*3\)",
                f"{name} must default FX6_ROUND to 7 under FX6_NATIVE_FAITHFUL=1",
            )

        # Verify 3-arg Backup_write + Backup_write_vsize + Backup_write_multi ABI in libgrm-fbinit9.c
        self.assertIn(
            "int Backup_write(unsigned int subsystem, unsigned int id, const void *buf)",
            self.shim_src,
        )
        self.assertIn(
            "int Backup_write_vsize(unsigned int subsystem, unsigned int id, const void *buf, int size)",
            self.shim_src,
        )
        self.assertIn(
            "int Backup_write_multi(unsigned int subsystem, const unsigned int *ids, const void *const *ptrs)",
            self.shim_src,
        )
        self.assertIn("fx6_record_bk_write(", self.shim_src)

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
        forbidden_suffixes = {".cpio", ".so", ".ko", ".fb", ".raw", ".o", ".dylib", ".pyc"}
        max_bytes = 50 * 1024 * 1024
        for root in (
            CLOSURE_DIR,
            REPORT_DIR,
            HYBRID_REPORT_DIR,
            ROUND9_REPORT_DIR,
            ROUND10_REPORT_DIR,
            ROUND11_REPORT_DIR,
        ):
            self.assertFalse(
                (root / "runs").exists(),
                f"Transient QEMU runs directory must not remain in tracked tree: {root / 'runs'}",
            )
            if not root.exists():
                continue
            for p in root.rglob("*"):
                if p.is_file():
                    self.assertNotIn(
                        p.suffix.lower(),
                        forbidden_suffixes,
                        f"Forbidden binary/bytecode artifact in tracked tree: {p}",
                    )
                    self.assertLessEqual(
                        p.stat().st_size,
                        max_bytes,
                        f"Tracked file exceeds 50 MiB limit: {p}",
                    )

    def test_round8_hybrid_c_source_guards(self) -> None:
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        self.assertIn("#if FX6_ROUND >= 8", self.shim_src)
        self.assertIn("FX6_STAGE_A_BRIDGE", self.shim_src)
        self.assertIn("FX6_ROUND >= 8", self.launch_src)
        self.assertIn("FX6_HYBRID_BRIDGE_INIT", self.launch_src)
        for token in (
            "FX6_STAGE_A_VERIFY_PASS",
            "FX6_STAGE_A_P1_LINK",
            "FX6_STAGE_A_P2_MOUNT",
            "FX6_STAGE_A_BK4_SHADOW",
            "FX6_STAGE_A_P9_UPM",
            "FX6_HYBRID_PROC_VERSION",
            "/dev/cnflasha30",
            "/dev/nflasha30",
            "LOOP_SET_FD",
            "posix_attr",
            "/etc/opelog",
            "magic=BK4_0",
        ):
            self.assertIn(token, verify_src)

    def test_round8_migration_and_stage_a_contracts(self) -> None:
        runner = _load_closure_module(
            "fx6_build_and_run_round_r8", "build_and_run_round.py"
        )
        readme_text = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")
        self.assertNotIn("/Volumes/KAFU2T", readme_text)
        self.assertIn("2026-11-14-fx6-on-fx3-qemu-hybrid", readme_text)

        # Verify dynamic path probing honors env override and internal HOME_AI_MAC candidate
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            fake_override = tmp_dir / "override.bin"
            fake_override.write_bytes(b"ok")
            with mock.patch.dict(os.environ, {"FX6_TEST_PROBE": str(fake_override)}):
                self.assertEqual(
                    runner._resolve_migrated_path(
                        "FX6_TEST_PROBE",
                        "work/missing/file.bin",
                        "/Volumes/KAFU2T/AI/Projects/Mac/work/missing/file.bin",
                    ),
                    fake_override,
                )

            fake_home = tmp_dir / "home"
            expected_internal = (
                fake_home
                / "AI-Workspace"
                / "AI"
                / "Projects"
                / "Mac"
                / "work"
                / "probe"
                / "target.bin"
            )
            expected_internal.parent.mkdir(parents=True, exist_ok=True)
            expected_internal.write_bytes(b"internal")
            with mock.patch.dict(os.environ, {"FX6_TEST_PROBE": ""}, clear=False):
                with mock.patch.object(
                    runner,
                    "HOME_AI_MAC",
                    fake_home / "AI-Workspace" / "AI" / "Projects" / "Mac",
                ), mock.patch.object(
                    runner,
                    "HOME_AI_LAB",
                    fake_home
                    / "AI-Workspace"
                    / "AI"
                    / "Projects"
                    / "Mac"
                    / "outputs"
                    / "sony-fx3-fx6-lab",
                ):
                    resolved = runner._resolve_migrated_path(
                        "FX6_TEST_PROBE",
                        "work/probe/target.bin",
                        "/Volumes/KAFU2T/AI/Projects/Mac/work/probe/target.bin",
                    )
                    self.assertEqual(resolved, expected_internal)

        # Verify read-only Stage-A pure-stdlib import does not pull unicorn
        patcher_mod, vfat_mod, bmtv_mod = runner._import_stage_a_modules()
        self.assertTrue(hasattr(patcher_mod, "P1_P4_P8_APPFW_COMBINED_SPEC"))
        self.assertTrue(hasattr(vfat_mod, "build_opelog_vfat_image"))
        self.assertTrue(hasattr(bmtv_mod, "synthesize_ram_shadow_bk4"))

        # Verify CLI accepts --round 8/9/10 and --run-dir, and patch_cpio fixes c_mode==0
        runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")
        self.assertIn("choices=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]", runner_src)
        self.assertIn("--run-dir", runner_src)
        self.assertIn("/private/tmp/{tmp_prefix}", runner_src)

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            parent_cpio = tmp_dir / "parent.cpio"
            out_cpio = tmp_dir / "patched.cpio"
            raw_archive = (
                runner.make_cpio_member("usr/lib/libInfraSetupFile.so", b"AAAA", ino=10, mode=0)
                + runner.make_cpio_member("TRAILER!!!", b"", ino=0, mode=0)
            )
            parent_cpio.write_bytes(raw_archive)
            meta = runner.patch_cpio(
                parent_cpio,
                out_cpio,
                {"usr/lib/libInfraSetupFile.so": b"PATCHED_ELF"},
                additions={"etc/stage_a_flag": (b"1\n", 0o100644)},
            )
            self.assertEqual(meta["replaced_members"], ["usr/lib/libInfraSetupFile.so"])
            self.assertEqual(meta["added_members"], ["etc/stage_a_flag"])
            with out_cpio.open("rb") as f:
                import mmap as _mmap

                with _mmap.mmap(f.fileno(), 0, access=_mmap.ACCESS_READ) as mm:
                    rows = runner.scan_cpio(mm)
            by_name = {r["name"]: r for r in rows}
            self.assertEqual(by_name["usr/lib/libInfraSetupFile.so"]["fields"][1], 0o100755)
            self.assertEqual(by_name["etc/stage_a_flag"]["fields"][1], 0o100644)


class TestReportPngAssets(unittest.TestCase):
    DISTINCT_PRESENTER_STEMS = (
        "r5a-initial-setting",
        "r5b-shooting-hud",
        "r5c-big6-menu-home",
        "r5d-menu-layer-1st",
        "r6a-big6-subdialog",
        "r6b-menu-layer-2nd",
        "r7a-big6-base-look",
        "r7b-menu-layer-3rd",
        "r7c-param-mutation-roundtrip",
    )
    EXPECTED_STEMS = DISTINCT_PRESENTER_STEMS + ("r6c-back-to-shooting",)

    def test_all_png_receipts_valid_and_distinct(self) -> None:
        self.assertTrue(ASSETS_DIR.is_dir(), f"Missing assets dir: {ASSETS_DIR}")
        alpha_digests: Dict[str, str] = {}
        comp_digests: Dict[str, str] = {}

        # Validate every *.png in assets/ plus ensure all expected r5a..r7c stems exist (20 PNGs)
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

        # All 9 distinct stems (r5a..r5d, r6a, r6b, r7a..r7c) must be pairwise distinct
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
            "r7a-big6-base-look",
            "r7b-menu-layer-3rd",
            "r7c-param-mutation-roundtrip",
        ):
            self.assertNotEqual(
                alpha_digests["r6c-back-to-shooting"],
                alpha_digests[overlay_stem],
            )

    def test_r7c_mutation_roundtrip_glyph_delta_vs_r5c(self) -> None:
        w1, h1, r5c_rows = _decode_png_rgba_rows(
            (ASSETS_DIR / "r5c-big6-menu-home-alpha.png").read_bytes()
        )
        w2, h2, r7c_rows = _decode_png_rgba_rows(
            (ASSETS_DIR / "r7c-param-mutation-roundtrip-alpha.png").read_bytes()
        )
        self.assertEqual((w1, h1), (1024, 540))
        self.assertEqual((w2, h2), (1024, 540))
        diff_px = 0
        min_x, min_y, max_x, max_y = 1024, 540, -1, -1
        for y in range(540):
            a, b = r5c_rows[y], r7c_rows[y]
            if a != b:
                for x in range(1024):
                    if a[x * 4 : x * 4 + 4] != b[x * 4 : x * 4 + 4]:
                        diff_px += 1
                        min_x = min(min_x, x)
                        min_y = min(min_y, y)
                        max_x = max(max_x, x)
                        max_y = max(max_y, y)
        # Mutating Scene File in cell[4] (Bottom-Middle) paints crisp "S-Cinetone" glyphs
        # strictly inside cell[4]'s value readout box with zero extraneous artifact pixels.
        self.assertEqual(diff_px, 1928)
        self.assertEqual((min_x, min_y, max_x, max_y), (378, 413, 572, 440))


class TestRound8HybridReportAndAssets(unittest.TestCase):
    EXPECTED_STEMS = (
        "r8a-hybrid-shooting-hud",
        "r8b-hybrid-big6-home",
    )

    def test_hybrid_summary_json_and_report_present(self) -> None:
        self.assertTrue((HYBRID_REPORT_DIR / "README.md").is_file())
        summary_path = HYBRID_REPORT_DIR / "summary.json"
        self.assertTrue(summary_path.is_file())
        data = json.loads(summary_path.read_text(encoding="utf-8"))
        self.assertEqual(data["schema"], "fx6-on-fx3-hybrid-stage-a-qemu-v1")
        self.assertIn("Linux version 4.9.337-scel+", data["kernel_version"])

        runs = data["runs"]
        self.assertEqual(set(runs.keys()), {"r8a_shooting_hud", "r8b_big6_menu_home"})

        for key, expected_sid, expected_min_px in (
            ("r8a_shooting_hud", "0x02", 5000),
            ("r8b_big6_menu_home", "0x0a", 300000),
        ):
            run = runs[key]
            self.assertEqual(run["round"], 8)
            self.assertEqual(run["target_sid"], expected_sid)
            self.assertEqual(run["nop_count"], 0)
            self.assertGreaterEqual(run["total_threads_seen"], 140)
            self.assertEqual(
                run["faithful_invariants"],
                {
                    "FX6_NATIVE_FAITHFUL": 1,
                    "subst_color": 0,
                    "subst_image": 0,
                    "forced_render": 0,
                    "skipped_node": 0,
                    "lock_bypass": 0,
                },
            )
            sa = run["stage_a"]
            self.assertEqual(len(sa["manifest_items"]), 10)
            for patch_key in (
                "P1_libInfraSetupFile",
                "P1_libInfraMediaCommon",
                "P1_libInfraMediaConfig",
                "P3_libInfraAppRemoteBoard",
                "Fan_libfan",
                "P1_P4_P8_appFw_combined",
                "P9_upm_ko",
            ):
                self.assertIn(patch_key, sa["patches"])
            self.assertEqual(sa["p2_vfat"]["mode"], "8m_ram")
            self.assertEqual(sa["p2_vfat"]["bytes"], 8 * 1024 * 1024)
            self.assertFalse(sa["ram_shadow_bk4"]["flash_write_allowed"])

            markers = "\n".join(sa["guest_boot_markers"])
            self.assertIn("FX6_STAGE_A_VERIFY_PASS count=10", markers)
            self.assertIn("FX6_STAGE_A_P2_MOUNT rc=0 errno=0", markers)
            self.assertIn("opts=posix_attr ope=1 ope00=1 ope01=1", markers)
            self.assertIn("FX6_STAGE_A_P9_UPM module_loaded=1", markers)
            self.assertIn("FX6_STAGE_A_VERIFY_RC=0", markers)
            self.assertIn("FX6_HYBRID_BRIDGE_INIT round=8 faithful=1", markers)
            self.assertIn("FX6_STAGE_A_BRIDGE round=8 faithful=1 nop_count=0", markers)

            gpe = run["gpe0_readback"]
            self.assertTrue(gpe["present"])
            self.assertGreaterEqual(gpe["nonzero_pixels"], expected_min_px)
            self.assertGreaterEqual(gpe["unique_colors"], 25)

    def test_round8_png_receipts_valid_and_pixel_verified(self) -> None:
        self.assertTrue(HYBRID_ASSETS_DIR.is_dir())
        for stem in self.EXPECTED_STEMS:
            for variant in ("alpha", "composited"):
                png_path = HYBRID_ASSETS_DIR / f"{stem}-{variant}.png"
                self.assertTrue(png_path.is_file(), f"Missing Round 8 PNG: {png_path}")
                w, h, _ = _parse_and_validate_png(png_path.read_bytes())
                self.assertEqual((w, h), (1024, 540))

        # r8a Shooting HUD on FX3 7.02 Kernel + Stage-A must match r5b Shooting HUD bit-for-bit
        for variant in ("alpha", "composited"):
            r8a_hash = hashlib.sha256(
                (HYBRID_ASSETS_DIR / f"r8a-hybrid-shooting-hud-{variant}.png").read_bytes()
            ).hexdigest()
            r5b_hash = hashlib.sha256(
                (ASSETS_DIR / f"r5b-shooting-hud-{variant}.png").read_bytes()
            ).hexdigest()
            self.assertEqual(r8a_hash, r5b_hash)

            r8b_hash = hashlib.sha256(
                (HYBRID_ASSETS_DIR / f"r8b-hybrid-big6-home-{variant}.png").read_bytes()
            ).hexdigest()
            self.assertNotEqual(r8a_hash, r8b_hash)

        # r8b Big6 Home should match r5c except dynamic RTC minute/timecode box
        _, _, r5c_rows = _decode_png_rgba_rows(
            (ASSETS_DIR / "r5c-big6-menu-home-alpha.png").read_bytes()
        )
        _, _, r8b_rows = _decode_png_rgba_rows(
            (HYBRID_ASSETS_DIR / "r8b-hybrid-big6-home-alpha.png").read_bytes()
        )
        diff_px = 0
        min_x, min_y, max_x, max_y = 1024, 540, -1, -1
        for y in range(540):
            a, b = r5c_rows[y], r8b_rows[y]
            if a != b:
                for x in range(1024):
                    if a[x * 4 : x * 4 + 4] != b[x * 4 : x * 4 + 4]:
                        diff_px += 1
                        min_x = min(min_x, x)
                        min_y = min(min_y, y)
                        max_x = max(max_x, x)
                        max_y = max(max_y, y)
        self.assertGreater(diff_px, 0)
        self.assertLessEqual(diff_px, 400)
        self.assertGreaterEqual(min_x, 140)
        self.assertLessEqual(max_x, 220)
        self.assertGreaterEqual(min_y, 270)
        self.assertLessEqual(max_y, 320)


class TestRound9StageBP10AndReport(unittest.TestCase):
    EXPECTED_RUN_KEYS = (
        "r9a_stage_b_shooting_hud",
        "r9b_fn_big6_home",
        "r9c_c1_big6_subdialog",
        "r9d_c2_menu_3layer",
    )
    EXPECTED_STEMS = (
        "r9a-stage-b-shooting-hud",
        "r9b-fn-big6-home",
        "r9c-c1-big6-subdialog",
        "r9d-c2-menu-3layer",
    )

    def test_round9_c_source_guards_and_fx3_keymap_router(self) -> None:
        shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")

        self.assertIn("#if FX6_ROUND >= 9", shim_src)
        self.assertIn("#if (FX6_KEY_COUNT > 0) || (FX6_ROUND >= 9)", shim_src)
        for token in (
            "fx3_phy_to_infra_key_id",
            "poll_srm3kye5_key_mailbox",
            "FX6_STAGE_B_P10_LIVE_CHECK",
            "FX6_STAGE_B_BRIDGE",
            "FX3_PHY_KEY_MAP",
            "FX3_SRM3KYE5_KEY",
            "0x0013U: infra = 0x7095U",
            "0x001dU: infra = 0x0066U",
            "0x0024U: infra = 0x70e7U",
            "0x0025U: infra = 0x70ecU",
            "0x000bU: infra = 0x01f7U",
            "0x000cU: infra = 0x01f8U",
            "0x0011U: infra = 0x01abU",
            "0x2245e7cUL",
            "0x2245a84UL",
            "0x224610cUL",
            "0x2246134UL",
            "0x2245b24UL",
            "0x2245b2cUL",
        ):
            self.assertIn(token, shim_src)

        self.assertIn("FX6_STAGE_B_VERIFY_PASS", verify_src)
        self.assertIn("/etc/fx6_stage_b", verify_src)
        self.assertRegex(
            runner_src,
            r'tmp_prefix\s*=\s*\(\s*"fx6-r11"\s+if\s+args\.round\s*>=\s*11\s+else\s+\("fx6-r10"\s+if\s+args\.round\s*>=\s*10\s+else\s+\("fx6-r9"\s+if\s+args\.round\s*>=\s*9',
        )
        self.assertIn("etc/fx6_stage_b", runner_src)

    def test_round9_p10_spec_loading_without_unicorn(self) -> None:
        runner = _load_closure_module(
            "fx6_build_and_run_round_r9", "build_and_run_round.py"
        )
        patcher_mod, _, _ = runner._import_stage_a_modules()
        p10_spec = runner._load_p10_keymap_spec(patcher_mod)
        self.assertEqual(p10_spec.spec_id, "P10_FX3_TO_FX6_KEYMAP_ADAPTER")
        self.assertEqual(p10_spec.library_name, "appFw.so")
        self.assertEqual(len(p10_spec.sites), 6)
        self.assertEqual(sum(s.size for s in p10_spec.sites), 24)
        self.assertEqual(
            [s.site_id for s in p10_spec.sites],
            [
                "p10_fn_to_home",
                "p10_c1_to_kuru_pon",
                "p10_c2_to_menu_cancel",
                "p10_c3_to_disp_sel",
                "p10_play_to_thumbnail",
                "p10_delete_to_user",
            ],
        )

    def test_round9_summary_json_and_stage_b_invariants(self) -> None:
        self.assertTrue((ROUND9_REPORT_DIR / "README.md").is_file())
        readme_text = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn("2026-11-14-round9-fx6-on-fx3-p10-presenter", readme_text)
        r9_readme = (ROUND9_REPORT_DIR / "README.md").read_text(encoding="utf-8")
        self.assertNotIn("/Volumes/KAFU2T", r9_readme)

        summary_path = ROUND9_REPORT_DIR / "summary.json"
        self.assertTrue(summary_path.is_file())
        data = json.loads(summary_path.read_text(encoding="utf-8"))
        self.assertEqual(data["schema"], "fx6-on-fx3-round9-stage-b-p10-presenter-v1")
        self.assertIn("Linux version 4.9.337-scel+", data["kernel_version"])
        self.assertEqual(data["fx3_phy_to_infra_pipeline"], "0x007a804c -> 0x005503e0")

        runs = data["runs"]
        self.assertEqual(set(runs.keys()), set(self.EXPECTED_RUN_KEYS))

        expectations = {
            "r9a_stage_b_shooting_hud": ("0x02", 5451, 29, 0, ()),
            "r9b_fn_big6_home": ("0x0a", 337227, 74, 0, ("name=FX3_Fn",)),
            "r9c_c1_big6_subdialog": ("0x0c", 37924, 59, 2035, ("name=FX3_Fn", "name=FX3_C1")),
            "r9d_c2_menu_3layer": (
                "0x10",
                434010,
                87,
                0,
                ("name=FX3_Fn", "name=FX3_C2", "name=FX3_MENU"),
            ),
        }
        for key, (sid, min_px, min_col, min_amber, phy_tokens) in expectations.items():
            run = runs[key]
            self.assertEqual(run["round"], 9)
            self.assertEqual(run["target_sid"], sid)
            self.assertEqual(run["nop_count"], 0)
            self.assertGreaterEqual(run["total_threads_seen"], 158)
            self.assertEqual(
                run["faithful_invariants"],
                {
                    "FX6_NATIVE_FAITHFUL": 1,
                    "subst_color": 0,
                    "subst_image": 0,
                    "forced_render": 0,
                    "skipped_node": 0,
                    "lock_bypass": 0,
                },
            )
            sb = run["stage_b"]
            self.assertEqual(sb["stage"], "B")
            self.assertEqual(sb["manifest_count"], 11)
            self.assertEqual(len(sb["manifest_items"]), 11)
            self.assertIn(
                "/usr/lib/libgrm-fbinit9.so",
                [item["guest_path"] for item in sb["manifest_items"]],
            )
            for patch_key in (
                "P1_libInfraSetupFile",
                "P1_libInfraMediaCommon",
                "P1_libInfraMediaConfig",
                "P3_libInfraAppRemoteBoard",
                "Fan_libfan",
                "P1_P4_P8_P10_appFw_combined",
                "P10_FX3_TO_FX6_KEYMAP_ADAPTER",
                "P9_upm_ko",
            ):
                self.assertIn(patch_key, sb["patches"])
            self.assertEqual(sb["patches"]["P10_FX3_TO_FX6_KEYMAP_ADAPTER"]["changed_bytes"], 24)

            markers = "\n".join(sb["guest_boot_markers"])
            self.assertIn("FX6_STAGE_A_VERIFY_PASS count=11", markers)
            self.assertIn("FX6_STAGE_B_VERIFY_PASS count=11 stage_b=1 p10_keymap=1", markers)
            self.assertIn("FX6_STAGE_A_VERIFY_RC=0", markers)
            self.assertIn(
                "FX6_STAGE_B_P10_LIVE_CHECK ok=1 fn=0x7095->0x0184 c1=0x0066->0x0029 "
                "c2=0x70e7->0x0192 c3=0x70ec->0x0199 play=0x01f7->0x0183 del=0x01f8->0x0185",
                markers,
            )
            self.assertIn("FX6_STAGE_B_BRIDGE round=9 faithful=1 nop_count=0", markers)

            phy_log = "\n".join(sb["fx3_phy_key_events"])
            for tok in phy_tokens:
                self.assertIn(tok, phy_log)

            gpe = run["gpe0_readback"]
            self.assertTrue(gpe["present"])
            self.assertEqual(gpe["nonzero_pixels"], min_px)
            self.assertGreaterEqual(gpe["unique_colors"], min_col)
            self.assertEqual(run["amber_0xffffaa00_pixels"], min_amber)

    def test_round9_png_receipts_valid_and_pixel_verified(self) -> None:
        self.assertTrue(ROUND9_ASSETS_DIR.is_dir())
        alpha_digests: Dict[str, str] = {}
        comp_digests: Dict[str, str] = {}
        for stem in self.EXPECTED_STEMS:
            for variant, bucket in (("alpha", alpha_digests), ("composited", comp_digests)):
                png_path = ROUND9_ASSETS_DIR / f"{stem}-{variant}.png"
                self.assertTrue(png_path.is_file(), f"Missing Round 9 PNG: {png_path}")
                w, h, _ = _parse_and_validate_png(png_path.read_bytes())
                self.assertEqual((w, h), (1024, 540))
                bucket[stem] = hashlib.sha256(png_path.read_bytes()).hexdigest()

        self.assertEqual(len(set(alpha_digests.values())), len(self.EXPECTED_STEMS))
        self.assertEqual(len(set(comp_digests.values())), len(self.EXPECTED_STEMS))

        # Bit-for-bit consistency with Rounds 5/6/8 visual ground truth
        for variant in ("alpha", "composited"):
            self.assertEqual(
                hashlib.sha256(
                    (ROUND9_ASSETS_DIR / f"r9a-stage-b-shooting-hud-{variant}.png").read_bytes()
                ).hexdigest(),
                hashlib.sha256(
                    (ASSETS_DIR / f"r5b-shooting-hud-{variant}.png").read_bytes()
                ).hexdigest(),
            )
            self.assertEqual(
                hashlib.sha256(
                    (ROUND9_ASSETS_DIR / f"r9c-c1-big6-subdialog-{variant}.png").read_bytes()
                ).hexdigest(),
                hashlib.sha256(
                    (ASSETS_DIR / f"r6a-big6-subdialog-{variant}.png").read_bytes()
                ).hexdigest(),
            )
            self.assertEqual(
                hashlib.sha256(
                    (ROUND9_ASSETS_DIR / f"r9d-c2-menu-3layer-{variant}.png").read_bytes()
                ).hexdigest(),
                hashlib.sha256(
                    (ASSETS_DIR / f"r6b-menu-layer-2nd-{variant}.png").read_bytes()
                ).hexdigest(),
            )

        # Verify Cinema Line amber 0xffffaa00 highlight in r9c Big6 Setting Sub-Dialog
        _, _, r9c_rows = _decode_png_rgba_rows(
            (ROUND9_ASSETS_DIR / "r9c-c1-big6-subdialog-alpha.png").read_bytes()
        )
        amber_px = 0
        for row in r9c_rows:
            for x in range(0, 1024 * 4, 4):
                if row[x : x + 4] == b"\xff\xaa\x00\xff":
                    amber_px += 1
        self.assertEqual(amber_px, 2035)


class TestOptionalDonorBinariesReadOnly(unittest.TestCase):
    @staticmethod
    def _verify_donor_root(tc: unittest.TestCase, donor_root: pathlib.Path, contracts: dict) -> None:
        if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1":
            tc.skipTest("FX3_FX6_FORCE_CLEAN_ROOM=1")
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
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "0"}):
            with self.assertRaises(unittest.SkipTest):
                self._verify_donor_root(self, missing, contracts)

    def test_force_clean_room_env_skips_donor_checks(self) -> None:
        contracts = json.loads(
            (CLOSURE_DIR / "static-contracts-summary.json").read_text(encoding="utf-8")
        )
        with tempfile.TemporaryDirectory() as tmp:
            fake_donor = pathlib.Path(tmp)
            with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
                with self.assertRaisesRegex(unittest.SkipTest, "^FX3_FX6_FORCE_CLEAN_ROOM=1$"):
                    self._verify_donor_root(self, fake_donor, contracts)


class TestRound10IconBlitterUipcAndReport(unittest.TestCase):
    EXPECTED_RUN_KEYS = (
        "r10a_r10_shooting_hud",
        "r10b_fn_big6_home",
        "r10c_c1_big6_subdialog",
        "r10d_c2_menu_3layer",
    )
    EXPECTED_STEMS = (
        "r10a-r10-shooting-hud",
        "r10b-fn-big6-home",
        "r10c-c1-big6-subdialog",
        "r10d-c2-menu-3layer",
    )

    def test_round10_c_source_guards_gpe_pool_and_uipc_telemetry(self) -> None:
        shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")

        self.assertIn("#if FX6_ROUND >= 10", shim_src)
        for token in (
            "FX6_GPE_POOL_PHYS_BASE 0x410524000UL",
            "FX6_GPE_POOL_BYTES     0x000940000UL",
            "gpe_pool_alloc",
            "gpe_pool_free",
            "unmark_gpe_argb_surface",
            "_ZN3grm3bmp10BitmapImpl7destroyEi",
            "emit_r10_telemetry",
            "fx6_p11_probe_rtc0",
            "FX6_R10_ICON_TELEMETRY",
            "FX6_P11_UIPC_TELEMETRY",
            "FX6_P11_HANDLE_ACK",
            "FX6_P11_RTC_SYNC",
            "FX6_P11_RTC0_PROBE",
            "FX6_STAGE_B_R10_BRIDGE",
            "/usr/share/app/image_00_169.uxc",
            "0x91db059bU",
            "0x88000002U",
            "xlr_h1_preserved=1",
            "g_fmt1_rgba4444_blits",
            "g_fmt2_rgba8888_blits",
            "g_fmt3_argb4444_blits",
            "g_fmt4_a8_blits",
            "g_icon_blit_count",
            "g_glyph_blit_count",
            "icon_blit=%d subst_image=0",
        ):
            self.assertIn(token, shim_src)

        for token in (
            "FX6_STAGE_B_R10_VERIFY_PASS",
            "FX6_STAGE_B_R10_UXC",
            "FX6_STAGE_B_R10_RTC0",
            "verify_uxc_archive",
            "probe_r10_rtc0",
            "/usr/share/app/image_00_169.uxc",
            "/etc/fx6_stage_r10",
            "FX6_RTC_RD_TIME",
        ):
            self.assertIn(token, verify_src)

        for token in (
            "DONOR_IMAGE_00_169_UXC",
            "def read_bytes_readonly",
            "enable_r10",
            "etc/fx6_stage_r10",
            '"r10_telemetry"',
            "choices=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]",
        ):
            self.assertIn(token, runner_src)

    def test_round10_pixel_formats_and_readonly_audit(self) -> None:
        shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        # Ensure src_is_gpe_argb is declared in GRM_gpermRectblit scope and all 4 pixel formats handled
        rect_m = re.search(
            r"int GRM_gpermRectblit\(.*?\n\}\n",
            shim_src,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(rect_m)
        rect_body = rect_m.group(0)
        self.assertIn("int src_is_gpe_argb = 0;", rect_body)
        for fmt_tok in ("fmt == 1", "fmt == 3", "bpp == 4", "bpp == 1", "src_is_gpe_argb"):
            self.assertIn(fmt_tok, rect_body)

        # Verify read_bytes_readonly strictly passes os.O_RDONLY and never writes donor files
        runner = _load_closure_module(
            "fx6_build_and_run_round_r10_ro", "build_and_run_round.py"
        )
        runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")
        tree = ast.parse(runner_src)
        ro_fn = next(
            (n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "read_bytes_readonly"),
            None,
        )
        self.assertIsNotNone(ro_fn)
        ro_dump = ast.dump(ro_fn)
        self.assertIn("O_RDONLY", ro_dump)
        self.assertNotIn("O_WRONLY", ro_dump)
        self.assertNotIn("O_RDWR", ro_dump)
        with tempfile.TemporaryDirectory() as tmp:
            sample = pathlib.Path(tmp) / "sample.uxc"
            sample.write_bytes(b"uxd\x07TEST_PAYLOAD")
            self.assertEqual(runner.read_bytes_readonly(sample), b"uxd\x07TEST_PAYLOAD")

    def test_round10_stage_a_overlay_uxc_and_clean_room_fallback(self) -> None:
        runner = _load_closure_module(
            "fx6_build_and_run_round_r10_ovl", "build_and_run_round.py"
        )
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            parent_cpio = tmp_dir / "parent.cpio"
            uxc_cpio_bytes = b"uxd\x07" + b"C" * 60
            uxc_donor_bytes = b"uxd\x07" + b"D" * 60
            uxc_bad_bytes = b"BAD!" + b"\x00" * 60
            init_body = (
                b"#!/bin/sh\n"
                b'LD_PRELOAD="$FX6_PRELOAD" /usr/bin/appfw-launch\n'
            )
            members = (
                ("init", init_body),
                ("usr/lib/libInfraSetupFile.so", b"SETUP"),
                ("usr/lib/libInfraMediaCommon.so", b"MCOMM"),
                ("usr/lib/libInfraMediaConfig.so", b"MCFG"),
                ("usr/lib/libInfraAppRemoteBoard.so", b"RBRD"),
                ("usr/lib/libfan.so", b"FAN"),
                ("usr/lib/appFw.so", b"APPFW"),
                ("usr/kmod/upm.ko", b"UPMKO"),
                ("usr/share/app/image_00_169.uxc", uxc_cpio_bytes),
            )
            archive = b"".join(
                runner.make_cpio_member(name, body, ino=idx + 1, mode=0o100755)
                for idx, (name, body) in enumerate(members)
            ) + runner.make_cpio_member("TRAILER!!!", b"", ino=0, mode=0)
            parent_cpio.write_bytes(archive)

            class _FakeRes:
                def __init__(self, site_id: str) -> None:
                    self.site_id = site_id

            class _FakeReceipt:
                def __init__(self, before: bytes, after: bytes, sites: list) -> None:
                    self.before_sha256 = hashlib.sha256(before).hexdigest()
                    self.after_sha256 = hashlib.sha256(after).hexdigest()
                    self.changed_byte_count = 4
                    self.resolutions = [_FakeRes(s.site_id) for s in sites]

            class _FakePatcher:
                P1_P4_P8_APPFW_COMBINED_SPEC = mock.Mock(
                    library_name="appFw.so",
                    expected_size=5,
                    donor_sha256="0" * 64,
                    sites=(mock.Mock(site_id="p1"),),
                    elf_kind="so",
                    source_domain="fx6",
                )
                P1_LIB_INFRA_SETUP_FILE_SPEC = mock.Mock(spec_id="P1_s", library_name="s", sites=[mock.Mock(site_id="s1")])
                P1_LIB_INFRA_MEDIA_COMMON_SPEC = mock.Mock(spec_id="P1_c", library_name="c", sites=[mock.Mock(site_id="c1")])
                P1_LIB_INFRA_MEDIA_CONFIG_SPEC = mock.Mock(spec_id="P1_g", library_name="g", sites=[mock.Mock(site_id="g1")])
                P3_LIB_INFRA_APP_REMOTE_BOARD_SPEC = mock.Mock(spec_id="P3_r", library_name="r", sites=[mock.Mock(site_id="r1")])
                FAN_LIBFAN_SPEC = mock.Mock(spec_id="Fan_f", library_name="f", sites=[mock.Mock(site_id="f1")])
                P9_UPM_KO_SPEC = mock.Mock(spec_id="P9_u", library_name="upm.ko", sites=[mock.Mock(site_id="u1")])
                LibraryPatchSpec = lambda **kw: type("FakeSpec", (), kw)()
                PatchSiteSpec = object
                PF_R = 4

                @staticmethod
                def apply_patch_spec(data: bytes, spec: object, verify_donor_sha256: bool = True):
                    after = data + b"_P"
                    return after, _FakeReceipt(data, after, getattr(spec, "sites", []))

                @staticmethod
                def resolve_and_verify_sites(data: bytes, spec: object, expect_patched_state: bool = True):
                    return [_FakeRes("u1")]

            class _FakeVfat:
                @staticmethod
                def build_opelog_vfat_image(mode: str):
                    img = b"VFAT" * 16
                    receipt = mock.Mock(
                        mode=mode,
                        fat_type="FAT16",
                        total_bytes=len(img),
                        sha256=hashlib.sha256(img).hexdigest(),
                        precreated_dirs=("OPE", "OPE/00", "OPE/01"),
                    )
                    return img, receipt

                @staticmethod
                def verify_vfat_image(_img: bytes):
                    return mock.Mock(valid=True, errors=[])

            class _FakeBmtv:
                @staticmethod
                def build_canonical_fa0080_normal_boot_table(donor_seed_bk4_path=None):
                    return b"T"

                @staticmethod
                def synthesize_ram_shadow_bk4(**_kw):
                    bk = b"BK4" + b"\x00" * 13
                    return mock.Mock(
                        bk4_bytes=bk,
                        total_bytes=len(bk),
                        sha256=hashlib.sha256(bk).hexdigest(),
                        flash_write_allowed=False,
                        active_byte8_selector=0,
                        synthesized_key_count=1,
                    )

            fake_p10 = type(
                "FakeP10",
                (),
                {
                    "spec_id": "P10_FX3_TO_FX6_KEYMAP_ADAPTER",
                    "library_name": "appFw.so",
                    "sites": (mock.Mock(site_id="p10_fn", size=4),),
                },
            )()

            def _fake_subproc_run(cmd, **_kw):
                out_path = pathlib.Path(cmd[-1])
                out_path.write_bytes(b"ELF_VERIFY")
                return mock.Mock(returncode=0, stderr="")

            donor_uxc_path = tmp_dir / "donor_image_00_169.uxc"
            donor_uxc_path.write_bytes(uxc_donor_bytes)
            missing_upm = tmp_dir / "absent_upm.ko"
            missing_seed = tmp_dir / "absent_seed.bin"
            build_dir = tmp_dir / "build"

            with mock.patch.object(
                runner, "_import_stage_a_modules", return_value=(_FakePatcher, _FakeVfat, _FakeBmtv)
            ), mock.patch.object(
                runner, "_load_p10_keymap_spec", return_value=fake_p10
            ), mock.patch.object(
                runner, "DONOR_IMAGE_00_169_UXC", donor_uxc_path
            ), mock.patch.object(
                runner, "FX3_UPM_KO", missing_upm
            ), mock.patch.object(
                runner, "FX3_SEED_BK4", missing_seed
            ), mock.patch.object(
                runner.subprocess, "run", side_effect=_fake_subproc_run
            ):
                # 1. Clean-room mode falls back to CPIO-staged UXC
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
                    rep, add, meta = runner.build_stage_a_overlay(
                        build_dir,
                        parent_cpio,
                        b"BK4_NTSC",
                        enable_p10=True,
                        enable_r10=True,
                        shim_bytes=b"SHIM10",
                    )
                self.assertEqual(meta["manifest_count"], 12)
                self.assertTrue(meta["r10_enabled"])
                self.assertEqual(meta["image_00_169_uxc"]["source"], "cpio_preloaded")
                self.assertEqual(meta["image_00_169_uxc"]["magic"], "uxd_07")
                self.assertEqual(rep["usr/share/app/image_00_169.uxc"], uxc_cpio_bytes)
                self.assertIn("etc/fx6_stage_r10", add)
                self.assertIn("/usr/bin/fx6-stage-a-verify", rep["init"].decode("utf-8"))

                # 2. Local donor mode reads DONOR_IMAGE_00_169_UXC via O_RDONLY
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "0"}):
                    rep2, _add2, meta2 = runner.build_stage_a_overlay(
                        build_dir,
                        parent_cpio,
                        b"BK4_NTSC",
                        enable_p10=True,
                        enable_r10=True,
                        shim_bytes=b"SHIM10",
                    )
                self.assertEqual(meta2["image_00_169_uxc"]["source"], "donor_o_rdonly")
                self.assertEqual(rep2["usr/share/app/image_00_169.uxc"], uxc_donor_bytes)

                # 3. Bad magic fails loudly
                donor_uxc_path.write_bytes(uxc_bad_bytes)
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "0"}):
                    with self.assertRaises(RuntimeError):
                        runner.build_stage_a_overlay(
                            build_dir,
                            parent_cpio,
                            b"BK4_NTSC",
                            enable_p10=True,
                            enable_r10=True,
                            shim_bytes=b"SHIM10",
                        )

    def test_round10_extract_milestones_telemetry_parser(self) -> None:
        runner = _load_closure_module(
            "fx6_build_and_run_round_r10_ms", "build_and_run_round.py"
        )
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_STAGE_B_R10_VERIFY_PASS count=12 stage_b=1 p10_keymap=1 p11_uipc=1 uxc=1",
                "FX6_STAGE_B_R10_UXC path=/usr/share/app/image_00_169.uxc bytes=3941000 magic=uxd_07 status=OK",
                "FX6_GPE_POOL_READY phys=0x410524000 bytes=0x940000 va=0x7df537d000",
                "FX6_P11_HANDLE_ACK count=1 dest=0x91db059b cb_qid=0x8000610e req_cmd=0x81000001 evt_cmd=0x88000002 free_rc=0 snd_rc=0 xlr_h1_preserved=1",
                "FX6_R10_ICON_TELEMETRY reason=pump icon_blits=14879 glyph_blits=214 total_blits=15093 fmt1_rgba4444=14879 fmt2_rgba8888=0 fmt3_argb4444=0 fmt4_a8=214 gpe_pool_alloc=26 gpe_pool_free=2 gpe_pool_fallback=0 gpe_pool_cur=310000 gpe_pool_peak=347904 subst_color=0 subst_image=0",
                "FX6_P11_UIPC_TELEMETRY reason=pump rtc_0x92d2091c=1 rtc0_ok=0 rtc0_year=0 handle_0x91db059b=1 bb_0x92840747=130 lut_0165=1 lut_0166=2 dev_0169_0416=4 p5_032d=1 cine_ei_mode=1 cine_ei_ready=1 lut_dma_ready=1 xlr_h1_preserved=1",
            ]
        )
        ms = runner.extract_milestones(serial)
        self.assertIn("4.9.337-scel+", ms["kernel_version"])
        self.assertEqual(ms["prefix_counts"]["FX6_R10_"], 1)
        self.assertEqual(ms["prefix_counts"]["FX6_P11_"], 2)
        r10 = ms["r10_telemetry"]
        self.assertIsNotNone(r10)
        self.assertEqual(r10["icon_blitter"]["icon_blits"], 14879)
        self.assertEqual(r10["icon_blitter"]["glyph_blits"], 214)
        self.assertEqual(r10["icon_blitter"]["gpe_pool_alloc"], 26)
        self.assertEqual(r10["icon_blitter"]["gpe_pool_fallback"], 0)
        self.assertEqual(r10["icon_blitter"]["subst_image"], 0)
        self.assertEqual(r10["p11_uipc"]["handle_0x91db059b"], 1)
        self.assertEqual(r10["p11_uipc"]["bb_0x92840747"], 130)
        self.assertEqual(r10["p11_uipc"]["xlr_h1_preserved"], 1)

    def test_round10_donor_uxc_readonly_when_present(self) -> None:
        if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1":
            self.skipTest("FX3_FX6_FORCE_CLEAN_ROOM=1")
        runner = _load_closure_module(
            "fx6_build_and_run_round_r10_uxc", "build_and_run_round.py"
        )
        uxc_path = runner.DONOR_IMAGE_00_169_UXC
        if not uxc_path.is_file():
            self.skipTest(f"Optional donor UXC absent: {uxc_path}")
        data = runner.read_bytes_readonly(uxc_path)
        self.assertEqual(data[:4], b"uxd\x07")
        self.assertEqual(len(data), 3941000)
        self.assertEqual(
            hashlib.sha256(data).hexdigest(),
            "f9bb82a2cf6364e5683ea9cce7e63b0a891325a8c250904cf28d2417fe2c4148",
        )

    def test_round10_summary_json_and_telemetry_invariants(self) -> None:
        self.assertTrue((ROUND10_REPORT_DIR / "README.md").is_file())
        closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn("2026-11-14-round10-fx6-on-fx3-full-icon-presenter", closure_readme)
        r10_readme = (ROUND10_REPORT_DIR / "README.md").read_text(encoding="utf-8")
        self.assertNotIn("/Volumes/KAFU2T", r10_readme)
        self.assertNotIn("/Volumes/KAFU2T", closure_readme)

        summary_path = ROUND10_REPORT_DIR / "summary.json"
        self.assertTrue(summary_path.is_file())
        raw_text = summary_path.read_text(encoding="utf-8")
        self.assertNotIn("/Volumes/KAFU2T", raw_text)
        self.assertNotIn("/private/tmp", raw_text)
        data = json.loads(raw_text)
        self.assertEqual(data["schema"], "fx6-on-fx3-round10-full-icon-presenter-v1")
        self.assertIn("Linux version 4.9.337-scel+", data["kernel_version"])
        self.assertEqual(data["uxc_asset"], "/usr/share/app/image_00_169.uxc")
        self.assertEqual(data["gpe_phys_pool"], "0x410524000..0x410e64000")

        runs = data["runs"]
        self.assertEqual(set(runs.keys()), set(self.EXPECTED_RUN_KEYS))

        expectations = {
            "r10a_r10_shooting_hud": ("0x02", 14274, 30, 0, 8823, ()),
            "r10b_fn_big6_home": ("0x0a", 346050, 87, 0, 14894, ("name=FX3_Fn",)),
            "r10c_c1_big6_subdialog": ("0x0c", 46267, 60, 2035, 8343, ("name=FX3_Fn", "name=FX3_C1")),
            "r10d_c2_menu_3layer": (
                "0x10",
                434579,
                357,
                0,
                37473,
                ("name=FX3_Fn", "name=FX3_C2", "name=FX3_MENU"),
            ),
        }
        for key, (sid, exp_px, exp_col, exp_amber, exp_diff, phy_tokens) in expectations.items():
            run = runs[key]
            self.assertEqual(run["round"], 10)
            self.assertEqual(run["target_sid"], sid)
            self.assertEqual(run["nop_count"], 0)
            self.assertEqual(run["crashes"], 0)
            self.assertGreater(run["ldec103_ioctl_count"], 40)
            self.assertGreaterEqual(run["total_threads_seen"], 160)
            self.assertEqual(
                run["faithful_invariants"],
                {
                    "FX6_NATIVE_FAITHFUL": 1,
                    "subst_color": 0,
                    "subst_image": 0,
                    "forced_render": 0,
                    "skipped_node": 0,
                    "lock_bypass": 0,
                },
            )
            sb = run["stage_b"]
            self.assertEqual(sb["stage"], "B")
            self.assertTrue(sb["r10_enabled"])
            self.assertEqual(sb["manifest_count"], 12)
            self.assertEqual(len(sb["manifest_items"]), 12)
            self.assertIn(
                "/usr/share/app/image_00_169.uxc",
                [item["guest_path"] for item in sb["manifest_items"]],
            )
            self.assertEqual(sb["image_00_169_uxc"]["magic"], "uxd_07")
            self.assertEqual(sb["image_00_169_uxc"]["bytes"], 3941000)

            markers = "\n".join(sb["guest_boot_markers"])
            self.assertIn("FX6_STAGE_A_VERIFY_PASS count=12", markers)
            self.assertIn("FX6_STAGE_B_VERIFY_PASS count=12 stage_b=1 p10_keymap=1", markers)
            self.assertIn("FX6_STAGE_B_R10_VERIFY_PASS count=12 stage_b=1 p10_keymap=1 p11_uipc=1 uxc=1", markers)
            self.assertIn("FX6_STAGE_B_R10_UXC path=/usr/share/app/image_00_169.uxc bytes=3941000 magic=uxd_07 status=OK", markers)
            self.assertIn("FX6_GPE_POOL_READY phys=0x410524000 bytes=0x940000", markers)
            self.assertIn("FX6_STAGE_B_R10_BRIDGE round=10 faithful=1 nop_count=0", markers)

            phy_log = "\n".join(sb["fx3_phy_key_events"])
            for tok in phy_tokens:
                self.assertIn(tok, phy_log)

            telem = run["r10_telemetry"]
            ib = telem["icon_blitter"]
            self.assertGreater(ib["icon_blits"], 10000)
            self.assertGreater(ib["gpe_pool_alloc"], 20)
            self.assertEqual(ib["gpe_pool_fallback"], 0)
            self.assertEqual(ib["subst_color"], 0)
            self.assertEqual(ib["subst_image"], 0)

            p11 = telem["p11_uipc"]
            self.assertGreaterEqual(p11["handle_0x91db059b"], 1)
            self.assertGreater(p11["bb_0x92840747"], 100)
            self.assertEqual(p11["cine_ei_ready"], 1)
            self.assertEqual(p11["lut_dma_ready"], 1)
            self.assertEqual(p11["xlr_h1_preserved"], 1)

            gpe = run["gpe0_readback"]
            self.assertTrue(gpe["present"])
            self.assertEqual(gpe["nonzero_pixels"], exp_px)
            self.assertEqual(gpe["unique_colors"], exp_col)
            self.assertEqual(run["amber_0xffffaa00_pixels"], exp_amber)
            self.assertEqual(run["pixel_diff_vs_round9"]["diff_pixels"], exp_diff)

    def test_round10_png_receipts_valid_size_and_pixel_verified(self) -> None:
        self.assertTrue(ROUND10_ASSETS_DIR.is_dir())
        alpha_digests: Dict[str, str] = {}
        comp_digests: Dict[str, str] = {}
        for stem in self.EXPECTED_STEMS:
            for variant, bucket in (("alpha", alpha_digests), ("composited", comp_digests)):
                png_path = ROUND10_ASSETS_DIR / f"{stem}-{variant}.png"
                self.assertTrue(png_path.is_file(), f"Missing Round 10 PNG: {png_path}")
                raw = png_path.read_bytes()
                self.assertLess(len(raw), 300 * 1024, f"PNG exceeds 300 KiB: {png_path}")
                w, h, _ = _parse_and_validate_png(raw)
                self.assertEqual((w, h), (1024, 540))
                bucket[stem] = hashlib.sha256(raw).hexdigest()

        self.assertEqual(len(set(alpha_digests.values())), len(self.EXPECTED_STEMS))
        self.assertEqual(len(set(comp_digests.values())), len(self.EXPECTED_STEMS))

        # Verify Cinema Line amber 0xffffaa00 highlight preserved in r10c Big6 Sub-Dialog
        _, _, r10c_rows = _decode_png_rgba_rows(
            (ROUND10_ASSETS_DIR / "r10c-c1-big6-subdialog-alpha.png").read_bytes()
        )
        amber_px = 0
        for row in r10c_rows:
            for x in range(0, 1024 * 4, 4):
                if row[x : x + 4] == b"\xff\xaa\x00\xff":
                    amber_px += 1
        self.assertEqual(amber_px, 2035)


class TestRound11P12WlanSChineseAndReport(unittest.TestCase):
    EXPECTED_RUN_KEYS = (
        "r11a_r11_shooting_hud",
        "r11b_fn_big6_schinese",
        "r11c_c1_big6_subdialog_schinese",
        "r11d_c2_menu_3layer_schinese",
    )
    EXPECTED_STEMS = (
        "r11a-r11-shooting-hud",
        "r11b-fn-big6-schinese",
        "r11c-c1-big6-subdialog-schinese",
        "r11d-c2-menu-3layer-schinese",
    )

    def test_round11_c_source_guards_p12_airplane_and_schinese_hooks(self) -> None:
        shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")

        self.assertIn("#if FX6_ROUND >= 11", shim_src)
        for token in (
            "FX6_STAGE_B_R11_BRIDGE",
            "FX6_R11_LANG_TELEMETRY",
            "FX6_BK4_R11_AIRPLANE_OVERRIDE",
            "FX6_R11_LANG_BK4",
            "FX6_R11_SWITCH_BANK",
            "FX6_R11_SET_FONT_NS",
            "_ZN2ux6resmgr15ResourceManager10switchBankEth",
            "0x019e0012U",
            "0x0051000fU",
            "0x01a20002U",
            "0x02cf019cU",
            "0x19U",
            "p12_wlan=1",
        ):
            self.assertIn(token, shim_src)

        for token in (
            "FX6_STAGE_B_R11_VERIFY_PASS",
            "FX6_STAGE_B_R11_LANG_ASSET",
            "FX6_STAGE_B_R11_FONTLIST",
            "/etc/fx6_stage_r11",
            "string_simplifiedchinese.uxc",
            "string_simplifiedchinese_2.uxc",
            "MYingHeiC-GB18030-SJ_wIcon.ltt",
            "fontlist.dat",
            "FONT_S_CHINESE",
        ):
            self.assertIn(token, verify_src)

        for token in (
            "def _load_p12_wlan_spec",
            "P12_WLAN_FATAL_GUARD_SPEC",
            "DONOR_STRING_SCHINESE_UXC",
            "DONOR_STRING_SCHINESE_2_UXC",
            "DONOR_FONT_SCHINESE_LTT",
            "enable_p12",
            "etc/fx6_stage_r11",
            '"r11_telemetry"',
            "--lang",
        ):
            self.assertIn(token, runner_src)

    def test_round11_p12_wlan_spec_loading_without_unicorn(self) -> None:
        runner = _load_closure_module(
            "fx6_build_and_run_round_r11_p12", "build_and_run_round.py"
        )
        patcher_mod, _, _ = runner._import_stage_a_modules()
        p12_spec = runner._load_p12_wlan_spec(patcher_mod)
        self.assertEqual(p12_spec.spec_id, "P12_libWlanResource_fatal_guard")
        self.assertEqual(p12_spec.library_name, "libWlanResource.so")
        self.assertEqual(len(p12_spec.sites), 1)
        self.assertEqual(sum(s.size for s in p12_spec.sites), 8)
        self.assertEqual(
            p12_spec.donor_sha256,
            "eb7785e025d11eefced79de3a918034960422ee75dc09b0fead69646f7e8bd88",
        )

    def test_round11_stage_a_overlay_p12_schinese_and_clean_room_fallback(self) -> None:
        runner = _load_closure_module(
            "fx6_build_and_run_round_r11_ovl", "build_and_run_round.py"
        )
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            parent_cpio = tmp_dir / "parent.cpio"
            init_body = (
                b"#!/bin/sh\n"
                b'LD_PRELOAD="$FX6_PRELOAD" /usr/bin/appfw-launch\n'
            )
            members = (
                ("init", init_body),
                ("usr/lib/libInfraSetupFile.so", b"SETUP"),
                ("usr/lib/libInfraMediaCommon.so", b"MCOMM"),
                ("usr/lib/libInfraMediaConfig.so", b"MCFG"),
                ("usr/lib/libInfraAppRemoteBoard.so", b"RBRD"),
                ("usr/lib/libfan.so", b"FAN"),
                ("usr/lib/appFw.so", b"APPFW"),
                ("usr/lib/libWlanResource.so", b"WLAN_DONOR_12345"),
                ("usr/kmod/upm.ko", b"UPMKO"),
                ("usr/share/app/image_00_169.uxc", b"uxd\x07" + b"C" * 32),
                ("usr/share/app/string_simplifiedchinese.uxc", b"uxc\x07" + b"S1" * 16),
                ("usr/share/app/string_simplifiedchinese_2.uxc", b"uxc\x07" + b"S2" * 16),
                ("usr/share/app/MYingHeiC-GB18030-SJ_wIcon.ltt", b"LTT\n" + b"FC" * 16),
                ("usr/share/app/fontlist.dat", b"FONT_S_CHINESE\t/usr/share/app/MYingHeiC-GB18030-SJ_wIcon.ltt\t0\t0\n"),
            )
            archive = b"".join(
                runner.make_cpio_member(name, body, ino=idx + 1, mode=0o100755)
                for idx, (name, body) in enumerate(members)
            ) + runner.make_cpio_member("TRAILER!!!", b"", ino=0, mode=0)
            parent_cpio.write_bytes(archive)

            class _FakeRes:
                def __init__(self, site_id: str) -> None:
                    self.site_id = site_id

            class _FakeReceipt:
                def __init__(self, before: bytes, after: bytes, sites: list) -> None:
                    self.before_sha256 = hashlib.sha256(before).hexdigest()
                    self.after_sha256 = hashlib.sha256(after).hexdigest()
                    self.changed_byte_count = 8
                    self.resolutions = [_FakeRes(s.site_id) for s in sites]

            class _FakePatcher:
                P1_P4_P8_APPFW_COMBINED_SPEC = mock.Mock(
                    library_name="appFw.so",
                    expected_size=5,
                    donor_sha256="0" * 64,
                    sites=(mock.Mock(site_id="p1"),),
                    elf_kind="so",
                    source_domain="fx6",
                )
                P1_LIB_INFRA_SETUP_FILE_SPEC = mock.Mock(spec_id="P1_s", library_name="s", sites=[mock.Mock(site_id="s1")])
                P1_LIB_INFRA_MEDIA_COMMON_SPEC = mock.Mock(spec_id="P1_c", library_name="c", sites=[mock.Mock(site_id="c1")])
                P1_LIB_INFRA_MEDIA_CONFIG_SPEC = mock.Mock(spec_id="P1_g", library_name="g", sites=[mock.Mock(site_id="g1")])
                P3_LIB_INFRA_APP_REMOTE_BOARD_SPEC = mock.Mock(spec_id="P3_r", library_name="r", sites=[mock.Mock(site_id="r1")])
                FAN_LIBFAN_SPEC = mock.Mock(spec_id="Fan_f", library_name="f", sites=[mock.Mock(site_id="f1")])
                P9_UPM_KO_SPEC = mock.Mock(spec_id="P9_u", library_name="upm.ko", sites=[mock.Mock(site_id="u1")])
                LibraryPatchSpec = lambda **kw: type("FakeSpec", (), kw)()
                PatchSiteSpec = object
                PF_R = 4

                @staticmethod
                def apply_patch_spec(data: bytes, spec: object, verify_donor_sha256: bool = True):
                    after = data + b"_P"
                    return after, _FakeReceipt(data, after, getattr(spec, "sites", []))

                @staticmethod
                def resolve_and_verify_sites(data: bytes, spec: object, expect_patched_state: bool = True):
                    return [_FakeRes("u1")]

            class _FakeVfat:
                @staticmethod
                def build_opelog_vfat_image(mode: str):
                    img = b"VFAT" * 16
                    receipt = mock.Mock(
                        mode=mode,
                        fat_type="FAT16",
                        total_bytes=len(img),
                        sha256=hashlib.sha256(img).hexdigest(),
                        precreated_dirs=("OPE", "OPE/00", "OPE/01"),
                    )
                    return img, receipt

                @staticmethod
                def verify_vfat_image(_img: bytes):
                    return mock.Mock(valid=True, errors=[])

            class _FakeBmtv:
                @staticmethod
                def build_canonical_fa0080_normal_boot_table(donor_seed_bk4_path=None):
                    return b"T"

                @staticmethod
                def synthesize_ram_shadow_bk4(**_kw):
                    bk = b"BK4\x00" + b"\x00" * 12
                    return mock.Mock(
                        bk4_bytes=bk,
                        total_bytes=len(bk),
                        sha256=hashlib.sha256(bk).hexdigest(),
                        flash_write_allowed=False,
                        active_byte8_selector=0,
                        synthesized_key_count=1,
                    )

            fake_p10 = type(
                "FakeP10",
                (),
                {
                    "spec_id": "P10_FX3_TO_FX6_KEYMAP_ADAPTER",
                    "library_name": "appFw.so",
                    "sites": (mock.Mock(site_id="p10_fn", size=4),),
                },
            )()
            fake_p12 = type(
                "FakeP12",
                (),
                {
                    "spec_id": "P12_libWlanResource_fatal_guard",
                    "library_name": "libWlanResource.so",
                    "sites": (mock.Mock(site_id="p12_wlan", size=8),),
                },
            )()

            def _fake_subproc_run(cmd, **_kw):
                out_path = pathlib.Path(cmd[-1])
                out_path.write_bytes(b"ELF_VERIFY_11")
                return mock.Mock(returncode=0, stderr="")

            donor_s1 = tmp_dir / "donor_s1.uxc"
            donor_s2 = tmp_dir / "donor_s2.uxc"
            donor_ltt = tmp_dir / "donor_gb18030.ltt"
            donor_uxc = tmp_dir / "donor_img.uxc"
            donor_s1.write_bytes(b"uxc\x07" + b"D1" * 16)
            donor_s2.write_bytes(b"uxc\x07" + b"D2" * 16)
            donor_ltt.write_bytes(b"LTT\n" + b"FD" * 16)
            donor_uxc.write_bytes(b"uxd\x07" + b"D" * 32)
            build_dir = tmp_dir / "build"

            with mock.patch.object(
                runner, "_import_stage_a_modules", return_value=(_FakePatcher, _FakeVfat, _FakeBmtv)
            ), mock.patch.object(
                runner, "_load_p10_keymap_spec", return_value=fake_p10
            ), mock.patch.object(
                runner, "_load_p12_wlan_spec", return_value=fake_p12
            ), mock.patch.object(
                runner, "DONOR_IMAGE_00_169_UXC", donor_uxc
            ), mock.patch.object(
                runner, "DONOR_STRING_SCHINESE_UXC", donor_s1
            ), mock.patch.object(
                runner, "DONOR_STRING_SCHINESE_2_UXC", donor_s2
            ), mock.patch.object(
                runner, "DONOR_FONT_SCHINESE_LTT", donor_ltt
            ), mock.patch.object(
                runner, "FX3_UPM_KO", tmp_dir / "absent_upm.ko"
            ), mock.patch.object(
                runner, "FX3_SEED_BK4", tmp_dir / "absent_seed.bin"
            ), mock.patch.object(
                runner.subprocess, "run", side_effect=_fake_subproc_run
            ):
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
                    rep, add, meta = runner.build_stage_a_overlay(
                        build_dir,
                        parent_cpio,
                        b"BK4_NTSC",
                        enable_p10=True,
                        enable_r10=True,
                        enable_p12=True,
                        lang="schinese",
                        shim_bytes=b"SHIM11",
                    )
                self.assertEqual(meta["manifest_count"], 13)
                self.assertTrue(meta["p12_enabled"])
                self.assertEqual(meta["lang"], "schinese")
                self.assertIn("P12_libWlanResource_fatal_guard", meta["patches"])
                self.assertIn("etc/fx6_stage_r11", add)
                self.assertEqual(meta["schinese_assets"]["string_simplifiedchinese"]["source"], "cpio_preloaded")
                self.assertEqual(meta["schinese_assets"]["font_gb18030_ltt"]["source"], "cpio_preloaded")
                self.assertEqual(rep["usr/share/app/string_simplifiedchinese_2.uxc"], b"uxc\x07" + b"S2" * 16)

                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "0"}):
                    rep2, _add2, meta2 = runner.build_stage_a_overlay(
                        build_dir,
                        parent_cpio,
                        b"BK4_NTSC",
                        enable_p10=True,
                        enable_r10=True,
                        enable_p12=True,
                        lang="schinese",
                        shim_bytes=b"SHIM11",
                    )
                self.assertEqual(meta2["schinese_assets"]["string_simplifiedchinese"]["source"], "donor_o_rdonly")
                self.assertEqual(rep2["usr/share/app/MYingHeiC-GB18030-SJ_wIcon.ltt"], b"LTT\n" + b"FD" * 16)

    def test_round11_extract_milestones_lang_telemetry_parser(self) -> None:
        runner = _load_closure_module(
            "fx6_build_and_run_round_r11_ms", "build_and_run_round.py"
        )
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_STAGE_B_R11_VERIFY_PASS count=13 stage_b=1 p10_keymap=1 p11_uipc=1 p12_wlan=1 uxc=1 schinese=1",
                "FX6_R11_LANG_BK4 hit=1 id=0x02cf019c val=0x19 enum=0x2b45_CHINESE_SIMPLIFIED bank=19",
                "FX6_R11_SWITCH_BANK ns=4 bank=23 rc=1 lr=0x7f000(appFw+0xcc6e28)",
                "FX6_R11_SWITCH_BANK ns=1 bank=19 rc=1 lr=0x7f001(appFw+0xcc6e38)",
                "FX6_R11_SWITCH_BANK ns=2 bank=19 rc=1 lr=0x7f002(appFw+0xcc6e48)",
                "FX6_R11_LANG_TELEMETRY reason=pump lang=schinese bk4_lang_id=0x02cf019c bk4_lang_val=0x19 lang_bk4_hits=3 airplane_bk4_hits=0 font_create=33871 glyph_blits=24891 icon_blits=17817 p12_wlan=1 subst_color=0 subst_image=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        self.assertEqual(ms["prefix_counts"]["FX6_R11_"], 5)
        r11 = ms["r11_telemetry"]
        self.assertIsNotNone(r11)
        self.assertEqual(r11["lang"], "schinese")
        self.assertEqual(r11["bk4_lang_id"], "0x02cf019c")
        self.assertEqual(r11["bk4_lang_val"], "0x19")
        self.assertEqual(r11["lang_bk4_hits"], 3)
        self.assertEqual(r11["font_create"], 33871)
        self.assertEqual(r11["glyph_blits"], 24891)
        self.assertEqual(r11["p12_wlan"], 1)
        self.assertEqual(r11["subst_color"], 0)
        self.assertEqual(r11["subst_image"], 0)

    def test_round11_donor_schinese_assets_readonly_when_present(self) -> None:
        if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1":
            self.skipTest("FX3_FX6_FORCE_CLEAN_ROOM=1")
        runner = _load_closure_module(
            "fx6_build_and_run_round_r11_assets", "build_and_run_round.py"
        )
        checked = 0
        for path, magic in (
            (runner.DONOR_STRING_SCHINESE_UXC, b"uxc\x07"),
            (runner.DONOR_STRING_SCHINESE_2_UXC, b"uxc\x07"),
            (runner.DONOR_FONT_SCHINESE_LTT, b"LTT\n"),
        ):
            if not path.is_file():
                continue
            data = runner.read_bytes_readonly(path)
            self.assertEqual(data[:4], magic)
            self.assertGreater(len(data), 100000)
            checked += 1
        if checked == 0:
            self.skipTest("Optional donor Simplified Chinese UXC/LTT assets absent")

    def test_round11_summary_json_and_schinese_invariants(self) -> None:
        self.assertTrue((ROUND11_REPORT_DIR / "README.md").is_file())
        closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn("2026-11-14-round11-fx6-on-fx3-schinese-p12-presenter", closure_readme)
        r11_readme = (ROUND11_REPORT_DIR / "README.md").read_text(encoding="utf-8")
        self.assertNotIn("/Volumes/KAFU2T", r11_readme)

        summary_path = ROUND11_REPORT_DIR / "summary.json"
        self.assertTrue(summary_path.is_file())
        raw_text = summary_path.read_text(encoding="utf-8")
        self.assertNotIn("/Volumes/KAFU2T", raw_text)
        self.assertNotIn("/private/tmp", raw_text)
        data = json.loads(raw_text)
        self.assertEqual(data["schema"], "fx6-on-fx3-round11-schinese-p12-presenter-v1")
        self.assertIn("Linux version 4.9.337-scel+", data["kernel_version"])
        self.assertEqual(data["language_enum"], "0x2b45")
        self.assertEqual(data["bk4_language_id"], "0x02cf019c")
        self.assertEqual(data["bk4_language_val"], "0x19")
        self.assertEqual(data["uxc_banks"], {"font": 23, "ns1_string": 19, "ns2_string": 19})

        runs = data["runs"]
        self.assertEqual(set(runs.keys()), set(self.EXPECTED_RUN_KEYS))

        expectations = {
            "r11a_r11_shooting_hud": ("0x02", 14430, 30, 0, 3038, ()),
            "r11b_fn_big6_schinese": ("0x0a", 346206, 87, 0, 11928, ("name=FX3_Fn",)),
            "r11c_c1_big6_subdialog_schinese": ("0x0c", 44968, 60, 1995, 14754, ("name=FX3_Fn", "name=FX3_C1")),
            "r11d_c2_menu_3layer_schinese": (
                "0x10",
                435667,
                476,
                0,
                52878,
                ("name=FX3_Fn", "name=FX3_C2", "name=FX3_MENU"),
            ),
        }
        for key, (sid, exp_px, exp_col, exp_amber, exp_diff, phy_tokens) in expectations.items():
            run = runs[key]
            self.assertEqual(run["round"], 11)
            self.assertEqual(run["lang"], "schinese")
            self.assertEqual(run["target_sid"], sid)
            self.assertEqual(run["nop_count"], 0)
            self.assertEqual(run["crashes"], 0)
            self.assertGreater(run["ldec103_ioctl_count"], 40)
            self.assertGreaterEqual(run["total_threads_seen"], 160)
            self.assertEqual(
                run["faithful_invariants"],
                {
                    "FX6_NATIVE_FAITHFUL": 1,
                    "subst_color": 0,
                    "subst_image": 0,
                    "forced_render": 0,
                    "skipped_node": 0,
                    "lock_bypass": 0,
                },
            )
            sb = run["stage_b"]
            self.assertEqual(sb["stage"], "B")
            self.assertTrue(sb["r10_enabled"])
            self.assertTrue(sb["p12_enabled"])
            self.assertEqual(sb["manifest_count"], 13)
            self.assertEqual(len(sb["manifest_items"]), 13)
            self.assertIn(
                "/usr/lib/libWlanResource.so",
                [item["guest_path"] for item in sb["manifest_items"]],
            )
            self.assertIn("P12_libWlanResource_fatal_guard", sb["patches"])

            markers = "\n".join(sb["guest_boot_markers"])
            self.assertIn("FX6_STAGE_A_VERIFY_PASS count=13", markers)
            self.assertIn("FX6_STAGE_B_R11_VERIFY_PASS count=13 stage_b=1 p10_keymap=1 p11_uipc=1 p12_wlan=1 uxc=1 schinese=1", markers)
            self.assertIn("FX6_STAGE_B_R11_BRIDGE round=11 faithful=1 nop_count=0 p12_wlan=1 airplane_mode=1 lang=schinese bk4_lang=0x19 schinese=1", markers)

            sw_log = "\n".join(sb["r11_switch_bank_events"])
            for sw_tok in ("ns=4 bank=23 rc=1", "ns=1 bank=19 rc=1", "ns=2 bank=19 rc=1"):
                self.assertIn(sw_tok, sw_log)

            phy_log = "\n".join(sb["fx3_phy_key_events"])
            for tok in phy_tokens:
                self.assertIn(tok, phy_log)

            r11_telem = run["r11_telemetry"]
            self.assertEqual(r11_telem["lang"], "schinese")
            self.assertEqual(r11_telem["bk4_lang_val"], "0x19")
            self.assertEqual(r11_telem["p12_wlan"], 1)
            self.assertEqual(r11_telem["subst_color"], 0)
            self.assertEqual(r11_telem["subst_image"], 0)

            gpe = run["gpe0_readback"]
            self.assertTrue(gpe["present"])
            self.assertEqual(gpe["nonzero_pixels"], exp_px)
            self.assertEqual(gpe["unique_colors"], exp_col)
            self.assertEqual(run["amber_0xffffaa00_pixels"], exp_amber)
            self.assertEqual(run["pixel_diff_vs_round10"]["diff_pixels"], exp_diff)

    def test_round11_png_receipts_valid_delta_vs_round10_and_amber_verified(self) -> None:
        self.assertTrue(ROUND11_ASSETS_DIR.is_dir())
        alpha_digests: Dict[str, str] = {}
        comp_digests: Dict[str, str] = {}
        for stem in self.EXPECTED_STEMS:
            for variant, bucket in (("alpha", alpha_digests), ("composited", comp_digests)):
                png_path = ROUND11_ASSETS_DIR / f"{stem}-{variant}.png"
                self.assertTrue(png_path.is_file(), f"Missing Round 11 PNG: {png_path}")
                raw = png_path.read_bytes()
                self.assertLess(len(raw), 300 * 1024, f"PNG exceeds 300 KiB: {png_path}")
                w, h, _ = _parse_and_validate_png(raw)
                self.assertEqual((w, h), (1024, 540))
                bucket[stem] = hashlib.sha256(raw).hexdigest()

        self.assertEqual(len(set(alpha_digests.values())), len(self.EXPECTED_STEMS))
        self.assertEqual(len(set(comp_digests.values())), len(self.EXPECTED_STEMS))

        # Verify pixel deltas vs Round 10 English baseline (r10a..r10d)
        expected_deltas = (
            ("r11a-r11-shooting-hud", "r10a-r10-shooting-hud", 3038),
            ("r11b-fn-big6-schinese", "r10b-fn-big6-home", 11928),
            ("r11c-c1-big6-subdialog-schinese", "r10c-c1-big6-subdialog", 14754),
            ("r11d-c2-menu-3layer-schinese", "r10d-c2-menu-3layer", 52878),
        )
        for s11, s10, exp_diff in expected_deltas:
            _, _, rows11 = _decode_png_rgba_rows((ROUND11_ASSETS_DIR / f"{s11}-alpha.png").read_bytes())
            _, _, rows10 = _decode_png_rgba_rows((ROUND10_ASSETS_DIR / f"{s10}-alpha.png").read_bytes())
            self.assertEqual(_diff_rows_u32(rows11, rows10), exp_diff)

        # Verify Cinema Line amber 0xffffaa00 highlight preserved in r11c Big6 Sub-Dialog
        _, _, r11c_rows = _decode_png_rgba_rows(
            (ROUND11_ASSETS_DIR / "r11c-c1-big6-subdialog-schinese-alpha.png").read_bytes()
        )
        self.assertEqual(_count_amber_u32(r11c_rows), 1995)


class TestRound12MultiCjkP4P110AndReport(unittest.TestCase):
    EXPECTED_RUN_KEYS = (
        "r12a_fn_big6_tchinese",
        "r12b_fn_big6_japanese",
        "r12c_p110_assignable_button_schinese",
        "r12d_c2_menu_3layer_japanese",
    )
    EXPECTED_STEMS = (
        "r12a-fn-big6-tchinese",
        "r12b-fn-big6-japanese",
        "r12c-p110-assignable-button-schinese",
        "r12d-c2-menu-3layer-japanese",
    )

    def test_round12_c_source_guards_multilang_p4_and_status_check(self) -> None:
        shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")

        self.assertIn("#if FX6_ROUND >= 12", shim_src)
        for token in (
            "FX6_LANG_CODE",
            "fx6_lang_name",
            "fx6_lang_bk4_byte",
            "fx6_lang_enum_label",
            "fx6_lang_str_bank",
            "0x18U",
            "0x01U",
            "0x19U",
            "0x2b44_LANGUAGE_CHINESE_TRADITIONAL",
            "0x2b30_LANGUAGE_JAPANESE",
            "0x2b45_CHINESE_SIMPLIFIED",
            "0x7052U",
            "INFRA_STATUS_CHECK",
            "FX6_STAGE_B_P4_ND_CLEAR_CHECK",
            "0x2111358UL",
            "0x21113f0UL",
            "0xd503201fU",
            "0x1400001bU",
            "FX6_STAGE_B_R12_BRIDGE",
            "FX6_R12_LANG_TELEMETRY",
            "FX6_R12_LANG_BK4",
        ):
            self.assertIn(token, shim_src)

        for token in (
            "FX6_STAGE_B_R12_VERIFY_PASS",
            "FX6_STAGE_B_R12_LANG_ASSET",
            "FX6_STAGE_B_R12_FONTLIST",
            "/etc/fx6_stage_r12",
            "string_traditionalchinese.uxc",
            "MYingHeiC-Big5HKSCS-SJ_wIcon.ltt",
            "FONT_T_CHINESE",
            "string_japanese.uxc",
            "HeiseiKakuGothW5-SJ_wIcon.ltt",
            "FONT_JAPANESE",
        ):
            self.assertIn(token, verify_src)

        for token in (
            "LANG_CODE_MAP",
            "DONOR_STRING_TCHINESE_UXC",
            "DONOR_STRING_TCHINESE_2_UXC",
            "DONOR_FONT_TCHINESE_LTT",
            "DONOR_STRING_JAPANESE_UXC",
            "DONOR_STRING_JAPANESE_2_UXC",
            "DONOR_FONT_JAPANESE_LTT",
            "enable_r12",
            "etc/fx6_stage_r12",
            '"r12_telemetry"',
            '"tchinese"',
            '"japanese"',
        ):
            self.assertIn(token, runner_src)

    def test_round12_lang_code_map_and_cli_choices(self) -> None:
        runner = _load_closure_module(
            "fx6_build_and_run_round_r12_lang", "build_and_run_round.py"
        )
        self.assertEqual(
            runner.LANG_CODE_MAP,
            {
                "en": 0,
                "english": 0,
                "japanese": 1,
                "tchinese": 2,
                "schinese": 3,
            },
        )
        runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")
        self.assertIn("choices=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]", runner_src)
        self.assertIn(
            'choices=["en", "english", "schinese", "tchinese", "japanese"]', runner_src
        )

    def _run_overlay_lang_dual_mode(
        self,
        lang: str,
        uxc1_name: str,
        uxc2_name: str,
        ltt_name: str,
        fontlist_key: str,
        asset_key_u1: str,
        asset_key_ltt: str,
        donor_attr_u1: str,
        donor_attr_u2: str,
        donor_attr_ltt: str,
    ) -> None:
        runner = _load_closure_module(
            f"fx6_build_and_run_round_r12_ovl_{lang}", "build_and_run_round.py"
        )
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            parent_cpio = tmp_dir / "parent.cpio"
            init_body = (
                b"#!/bin/sh\n"
                b'LD_PRELOAD="$FX6_PRELOAD" /usr/bin/appfw-launch\n'
            )
            members = (
                ("init", init_body),
                ("usr/lib/libInfraSetupFile.so", b"SETUP"),
                ("usr/lib/libInfraMediaCommon.so", b"MCOMM"),
                ("usr/lib/libInfraMediaConfig.so", b"MCFG"),
                ("usr/lib/libInfraAppRemoteBoard.so", b"RBRD"),
                ("usr/lib/libfan.so", b"FAN"),
                ("usr/lib/appFw.so", b"APPFW"),
                ("usr/lib/libWlanResource.so", b"WLAN_DONOR_12345"),
                ("usr/kmod/upm.ko", b"UPMKO"),
                ("usr/share/app/image_00_169.uxc", b"uxd\x07" + b"C" * 32),
                (f"usr/share/app/{uxc1_name}", b"uxc\x07" + b"C1" * 16),
                (f"usr/share/app/{uxc2_name}", b"uxc\x07" + b"C2" * 16),
                (f"usr/share/app/{ltt_name}", b"LTT\n" + b"CL" * 16),
                (
                    "usr/share/app/fontlist.dat",
                    f"{fontlist_key}\t/usr/share/app/{ltt_name}\t0\t0\n".encode("ascii"),
                ),
            )
            archive = b"".join(
                runner.make_cpio_member(name, body, ino=idx + 1, mode=0o100755)
                for idx, (name, body) in enumerate(members)
            ) + runner.make_cpio_member("TRAILER!!!", b"", ino=0, mode=0)
            parent_cpio.write_bytes(archive)

            class _FakeRes:
                def __init__(self, site_id: str) -> None:
                    self.site_id = site_id

            class _FakeReceipt:
                def __init__(self, before: bytes, after: bytes, sites: list) -> None:
                    self.before_sha256 = hashlib.sha256(before).hexdigest()
                    self.after_sha256 = hashlib.sha256(after).hexdigest()
                    self.changed_byte_count = 8
                    self.resolutions = [_FakeRes(s.site_id) for s in sites]

            class _FakePatcher:
                P1_P4_P8_APPFW_COMBINED_SPEC = mock.Mock(
                    library_name="appFw.so",
                    expected_size=5,
                    donor_sha256="0" * 64,
                    sites=(mock.Mock(site_id="p1"),),
                    elf_kind="so",
                    source_domain="fx6",
                )
                P1_LIB_INFRA_SETUP_FILE_SPEC = mock.Mock(spec_id="P1_s", library_name="s", sites=[mock.Mock(site_id="s1")])
                P1_LIB_INFRA_MEDIA_COMMON_SPEC = mock.Mock(spec_id="P1_c", library_name="c", sites=[mock.Mock(site_id="c1")])
                P1_LIB_INFRA_MEDIA_CONFIG_SPEC = mock.Mock(spec_id="P1_g", library_name="g", sites=[mock.Mock(site_id="g1")])
                P3_LIB_INFRA_APP_REMOTE_BOARD_SPEC = mock.Mock(spec_id="P3_r", library_name="r", sites=[mock.Mock(site_id="r1")])
                FAN_LIBFAN_SPEC = mock.Mock(spec_id="Fan_f", library_name="f", sites=[mock.Mock(site_id="f1")])
                P9_UPM_KO_SPEC = mock.Mock(spec_id="P9_u", library_name="upm.ko", sites=[mock.Mock(site_id="u1")])
                LibraryPatchSpec = lambda **kw: type("FakeSpec", (), kw)()
                PatchSiteSpec = object
                PF_R = 4

                @staticmethod
                def apply_patch_spec(data: bytes, spec: object, verify_donor_sha256: bool = True):
                    after = data + b"_P"
                    return after, _FakeReceipt(data, after, getattr(spec, "sites", []))

                @staticmethod
                def resolve_and_verify_sites(data: bytes, spec: object, expect_patched_state: bool = True):
                    return [_FakeRes("u1")]

            class _FakeVfat:
                @staticmethod
                def build_opelog_vfat_image(mode: str):
                    img = b"VFAT" * 16
                    receipt = mock.Mock(
                        mode=mode,
                        fat_type="FAT16",
                        total_bytes=len(img),
                        sha256=hashlib.sha256(img).hexdigest(),
                        precreated_dirs=("OPE", "OPE/00", "OPE/01"),
                    )
                    return img, receipt

                @staticmethod
                def verify_vfat_image(_img: bytes):
                    return mock.Mock(valid=True, errors=[])

            class _FakeBmtv:
                @staticmethod
                def build_canonical_fa0080_normal_boot_table(donor_seed_bk4_path=None):
                    return b"T"

                @staticmethod
                def synthesize_ram_shadow_bk4(**_kw):
                    bk = b"BK4\x00" + b"\x00" * 12
                    return mock.Mock(
                        bk4_bytes=bk,
                        total_bytes=len(bk),
                        sha256=hashlib.sha256(bk).hexdigest(),
                        flash_write_allowed=False,
                        active_byte8_selector=0,
                        synthesized_key_count=1,
                    )

            fake_p10 = type(
                "FakeP10",
                (),
                {
                    "spec_id": "P10_FX3_TO_FX6_KEYMAP_ADAPTER",
                    "library_name": "appFw.so",
                    "sites": (mock.Mock(site_id="p10_fn", size=4),),
                },
            )()
            fake_p12 = type(
                "FakeP12",
                (),
                {
                    "spec_id": "P12_libWlanResource_fatal_guard",
                    "library_name": "libWlanResource.so",
                    "sites": (mock.Mock(site_id="p12_wlan", size=8),),
                },
            )()

            def _fake_subproc_run(cmd, **_kw):
                out_path = pathlib.Path(cmd[-1])
                out_path.write_bytes(b"ELF_VERIFY_12")
                return mock.Mock(returncode=0, stderr="")

            donor_u1 = tmp_dir / "donor_u1.uxc"
            donor_u2 = tmp_dir / "donor_u2.uxc"
            donor_ltt = tmp_dir / "donor_font.ltt"
            donor_uxc = tmp_dir / "donor_img.uxc"
            donor_u1.write_bytes(b"uxc\x07" + b"D1" * 16)
            donor_u2.write_bytes(b"uxc\x07" + b"D2" * 16)
            donor_ltt.write_bytes(b"LTT\n" + b"FD" * 16)
            donor_uxc.write_bytes(b"uxd\x07" + b"D" * 32)
            build_dir = tmp_dir / "build"

            with mock.patch.object(
                runner, "_import_stage_a_modules", return_value=(_FakePatcher, _FakeVfat, _FakeBmtv)
            ), mock.patch.object(
                runner, "_load_p10_keymap_spec", return_value=fake_p10
            ), mock.patch.object(
                runner, "_load_p12_wlan_spec", return_value=fake_p12
            ), mock.patch.object(
                runner, "DONOR_IMAGE_00_169_UXC", donor_uxc
            ), mock.patch.object(
                runner, donor_attr_u1, donor_u1
            ), mock.patch.object(
                runner, donor_attr_u2, donor_u2
            ), mock.patch.object(
                runner, donor_attr_ltt, donor_ltt
            ), mock.patch.object(
                runner, "FX3_UPM_KO", tmp_dir / "absent_upm.ko"
            ), mock.patch.object(
                runner, "FX3_SEED_BK4", tmp_dir / "absent_seed.bin"
            ), mock.patch.object(
                runner.subprocess, "run", side_effect=_fake_subproc_run
            ):
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
                    rep, add, meta = runner.build_stage_a_overlay(
                        build_dir,
                        parent_cpio,
                        b"BK4_NTSC",
                        enable_p10=True,
                        enable_r10=True,
                        enable_p12=True,
                        enable_r12=True,
                        lang=lang,
                        shim_bytes=b"SHIM12",
                    )
                self.assertEqual(meta["manifest_count"], 13)
                self.assertTrue(meta["r12_enabled"])
                self.assertEqual(meta["lang"], lang)
                self.assertIn("etc/fx6_stage_r12", add)
                self.assertIn(f"lang={lang}".encode("utf-8"), add["etc/fx6_stage_r12"][0])
                self.assertEqual(meta["lang_assets"][asset_key_u1]["source"], "cpio_preloaded")
                self.assertEqual(meta["lang_assets"][asset_key_ltt]["source"], "cpio_preloaded")
                self.assertEqual(meta["lang_assets"]["fontlist_dat"]["fontlist_key"], fontlist_key)
                self.assertEqual(rep[f"usr/share/app/{uxc2_name}"], b"uxc\x07" + b"C2" * 16)

                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "0"}):
                    rep2, _add2, meta2 = runner.build_stage_a_overlay(
                        build_dir,
                        parent_cpio,
                        b"BK4_NTSC",
                        enable_p10=True,
                        enable_r10=True,
                        enable_p12=True,
                        enable_r12=True,
                        lang=lang,
                        shim_bytes=b"SHIM12",
                    )
                self.assertEqual(meta2["lang_assets"][asset_key_u1]["source"], "donor_o_rdonly")
                self.assertEqual(rep2[f"usr/share/app/{ltt_name}"], b"LTT\n" + b"FD" * 16)

    def test_round12_stage_a_overlay_tchinese_and_clean_room_fallback(self) -> None:
        self._run_overlay_lang_dual_mode(
            lang="tchinese",
            uxc1_name="string_traditionalchinese.uxc",
            uxc2_name="string_traditionalchinese_2.uxc",
            ltt_name="MYingHeiC-Big5HKSCS-SJ_wIcon.ltt",
            fontlist_key="FONT_T_CHINESE",
            asset_key_u1="string_traditionalchinese",
            asset_key_ltt="font_big5hkscs_ltt",
            donor_attr_u1="DONOR_STRING_TCHINESE_UXC",
            donor_attr_u2="DONOR_STRING_TCHINESE_2_UXC",
            donor_attr_ltt="DONOR_FONT_TCHINESE_LTT",
        )

    def test_round12_stage_a_overlay_japanese_and_clean_room_fallback(self) -> None:
        self._run_overlay_lang_dual_mode(
            lang="japanese",
            uxc1_name="string_japanese.uxc",
            uxc2_name="string_japanese_2.uxc",
            ltt_name="HeiseiKakuGothW5-SJ_wIcon.ltt",
            fontlist_key="FONT_JAPANESE",
            asset_key_u1="string_japanese",
            asset_key_ltt="font_japanese_ltt",
            donor_attr_u1="DONOR_STRING_JAPANESE_UXC",
            donor_attr_u2="DONOR_STRING_JAPANESE_2_UXC",
            donor_attr_ltt="DONOR_FONT_JAPANESE_LTT",
        )

    def test_round12_extract_milestones_lang_telemetry_parser(self) -> None:
        runner = _load_closure_module(
            "fx6_build_and_run_round_r12_ms", "build_and_run_round.py"
        )
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_STAGE_B_R12_VERIFY_PASS count=13 stage_b=1 p10_keymap=1 p11_uipc=1 p12_wlan=1 p4_nd_clear=1 uxc=1 lang=japanese",
                "FX6_STAGE_B_P4_ND_CLEAR_CHECK ok=1 nd_mode=0xd503201f nd_val=0x1400001b",
                "FX6_R12_LANG_BK4 hit=1 id=0x02cf019c lang=japanese val=0x01 enum=0x2b30_LANGUAGE_JAPANESE bank=12",
                "FX6_R12_LANG_TELEMETRY reason=pump lang=japanese bk4_lang_id=0x02cf019c bk4_lang_val=0x01 lang_enum=0x2b30_LANGUAGE_JAPANESE lang_bk4_hits=3 airplane_bk4_hits=0 p4_nd_clear=1 p10_keymap=1 p11_xlr_h1=1 font_create=26754 glyph_blits=16530 icon_blits=14486 p12_wlan=1 subst_color=0 subst_image=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        self.assertEqual(ms["prefix_counts"]["FX6_R12_"], 2)
        r12 = ms["r12_telemetry"]
        self.assertIsNotNone(r12)
        self.assertEqual(r12["lang"], "japanese")
        self.assertEqual(r12["bk4_lang_id"], "0x02cf019c")
        self.assertEqual(r12["bk4_lang_val"], "0x01")
        self.assertEqual(r12["p4_nd_clear"], 1)
        self.assertEqual(r12["p10_keymap"], 1)
        self.assertEqual(r12["p11_xlr_h1"], 1)
        self.assertEqual(r12["p12_wlan"], 1)
        self.assertEqual(r12["glyph_blits"], 16530)
        self.assertEqual(r12["icon_blits"], 14486)
        self.assertEqual(r12["subst_color"], 0)
        self.assertEqual(r12["subst_image"], 0)

    def test_round12_donor_tchinese_and_japanese_assets_readonly_when_present(self) -> None:
        if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1":
            self.skipTest("FX3_FX6_FORCE_CLEAN_ROOM=1")
        runner = _load_closure_module(
            "fx6_build_and_run_round_r12_assets", "build_and_run_round.py"
        )
        checked = 0
        for path, magic in (
            (runner.DONOR_STRING_TCHINESE_UXC, b"uxc\x07"),
            (runner.DONOR_STRING_TCHINESE_2_UXC, b"uxc\x07"),
            (runner.DONOR_FONT_TCHINESE_LTT, b"LTT\n"),
            (runner.DONOR_STRING_JAPANESE_UXC, b"uxc\x07"),
            (runner.DONOR_STRING_JAPANESE_2_UXC, b"uxc\x07"),
            (runner.DONOR_FONT_JAPANESE_LTT, b"LTT\n"),
        ):
            if not path.is_file():
                continue
            data = runner.read_bytes_readonly(path)
            self.assertEqual(data[:4], magic)
            self.assertGreater(len(data), 100000)
            checked += 1
        if checked == 0:
            self.skipTest("Optional donor Traditional Chinese / Japanese UXC/LTT assets absent")

    def test_round12_summary_json_and_multilang_p4_p110_invariants(self) -> None:
        self.assertTrue((ROUND12_REPORT_DIR / "README.md").is_file())
        closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn("2026-11-14-round12-fx6-on-fx3-cjk-ja-p110-presenter", closure_readme)
        r12_readme = (ROUND12_REPORT_DIR / "README.md").read_text(encoding="utf-8")
        self.assertNotIn("/Volumes/KAFU2T", r12_readme)
        self.assertNotIn("/Users/", r12_readme)

        summary_path = ROUND12_REPORT_DIR / "summary.json"
        self.assertTrue(summary_path.is_file())
        raw_text = summary_path.read_text(encoding="utf-8")
        self.assertNotIn("/Volumes/KAFU2T", raw_text)
        self.assertNotIn("/private/tmp", raw_text)
        self.assertNotIn("/Users/", raw_text)
        data = json.loads(raw_text)
        self.assertEqual(data["schema"], "fx6-on-fx3-round12-cjk-ja-p110-presenter-v1")
        self.assertIn("Linux version 4.9.337-scel+", data["kernel_version"])
        self.assertEqual(
            data["languages"]["tchinese"]["uxc_banks"],
            {"font": 27, "ns1_string": 22, "ns2_string": 22},
        )
        self.assertEqual(
            data["languages"]["japanese"]["uxc_banks"],
            {"font": 1, "ns1_string": 12, "ns2_string": 12},
        )
        self.assertEqual(
            data["languages"]["schinese"]["uxc_banks"],
            {"font": 23, "ns1_string": 19, "ns2_string": 19},
        )
        self.assertEqual(
            data["p4_nd_clear_sites"],
            {
                "nd_mode": "0x2111358 -> 0xd503201f",
                "nd_val": "0x21113f0 -> 0x1400001b",
            },
        )

        runs = data["runs"]
        self.assertEqual(set(runs.keys()), set(self.EXPECTED_RUN_KEYS))

        expectations = {
            "r12a_fn_big6_tchinese": (
                "tchinese", "0x0a", "0x18", ("ns=4 bank=27 rc=1", "ns=1 bank=22 rc=1", "ns=2 bank=22 rc=1"),
                346686, 87, 0, ("name=FX3_Fn",),
            ),
            "r12b_fn_big6_japanese": (
                "japanese", "0x0a", "0x01", ("ns=4 bank=1 rc=1", "ns=1 bank=12 rc=1", "ns=2 bank=12 rc=1"),
                346206, 87, 0, ("name=FX3_Fn",),
            ),
            "r12c_p110_assignable_button_schinese": (
                "schinese", "0x30", "0x19", ("ns=4 bank=23 rc=1", "ns=1 bank=19 rc=1", "ns=2 bank=19 rc=1"),
                437403, 80, 260, ("name=FX3_Fn", "name=FX3_C2", "name=INFRA_STATUS_CHECK"),
            ),
            "r12d_c2_menu_3layer_japanese": (
                "japanese", "0x11", "0x01", ("ns=4 bank=1 rc=1", "ns=1 bank=12 rc=1", "ns=2 bank=12 rc=1"),
                437575, 233, 1257, ("name=FX3_Fn", "name=FX3_C2", "name=FX3_MENU"),
            ),
        }
        for key, (lang, sid, bk4_val, sw_tokens, exp_px, exp_col, exp_amber, phy_tokens) in expectations.items():
            run = runs[key]
            self.assertEqual(run["round"], 12)
            self.assertEqual(run["lang"], lang)
            self.assertEqual(run["target_sid"], sid)
            self.assertEqual(run["nop_count"], 0)
            self.assertEqual(run["crashes"], 0)
            self.assertGreater(run["ldec103_ioctl_count"], 40)
            self.assertGreaterEqual(run["total_threads_seen"], 160)
            self.assertEqual(
                run["faithful_invariants"],
                {
                    "FX6_NATIVE_FAITHFUL": 1,
                    "subst_color": 0,
                    "subst_image": 0,
                    "forced_render": 0,
                    "skipped_node": 0,
                    "lock_bypass": 0,
                },
            )
            sb = run["stage_b"]
            self.assertEqual(sb["stage"], "B")
            self.assertTrue(sb["r10_enabled"])
            self.assertTrue(sb["p12_enabled"])
            self.assertTrue(sb["r12_enabled"])
            self.assertEqual(sb["manifest_count"], 13)
            self.assertEqual(len(sb["manifest_items"]), 13)
            markers = "\n".join(sb["guest_boot_markers"])
            self.assertIn("FX6_STAGE_A_VERIFY_PASS count=13", markers)
            self.assertIn(f"FX6_STAGE_B_R12_VERIFY_PASS count=13 stage_b=1 p10_keymap=1 p11_uipc=1 p12_wlan=1 p4_nd_clear=1 uxc=1 lang={lang}", markers)
            self.assertIn("FX6_STAGE_B_P4_ND_CLEAR_CHECK ok=1 nd_mode=0xd503201f nd_val=0x1400001b", markers)
            self.assertIn(f"FX6_STAGE_B_R12_BRIDGE round=12 faithful=1 nop_count=0 p12_wlan=1 p10_keymap=1 p4_nd_clear=1 p11_xlr_h1=1 lang={lang} bk4_lang={bk4_val}", markers)

            sw_log = "\n".join(sb["r11_switch_bank_events"])
            for sw_tok in sw_tokens:
                self.assertIn(sw_tok, sw_log)

            phy_log = "\n".join(sb["fx3_phy_key_events"])
            for tok in phy_tokens:
                self.assertIn(tok, phy_log)

            r12_telem = run["r12_telemetry"]
            self.assertEqual(r12_telem["lang"], lang)
            self.assertEqual(r12_telem["bk4_lang_val"], bk4_val)
            self.assertEqual(r12_telem["p4_nd_clear"], 1)
            self.assertEqual(r12_telem["p10_keymap"], 1)
            self.assertEqual(r12_telem["p11_xlr_h1"], 1)
            self.assertEqual(r12_telem["p12_wlan"], 1)
            self.assertEqual(r12_telem["subst_color"], 0)
            self.assertEqual(r12_telem["subst_image"], 0)

            gpe = run["gpe0_readback"]
            self.assertTrue(gpe["present"])
            self.assertEqual(gpe["nonzero_pixels"], exp_px)
            self.assertEqual(gpe["unique_colors"], exp_col)
            self.assertEqual(run["amber_0xffffaa00_pixels"], exp_amber)

    def test_round12_png_receipts_valid_deltas_and_amber_verified(self) -> None:
        self.assertTrue(ROUND12_ASSETS_DIR.is_dir())
        alpha_digests: Dict[str, str] = {}
        comp_digests: Dict[str, str] = {}
        for stem in self.EXPECTED_STEMS:
            for variant, bucket in (("alpha", alpha_digests), ("composited", comp_digests)):
                png_path = ROUND12_ASSETS_DIR / f"{stem}-{variant}.png"
                self.assertTrue(png_path.is_file(), f"Missing Round 12 PNG: {png_path}")
                raw = png_path.read_bytes()
                self.assertLess(len(raw), 300 * 1024, f"PNG exceeds 300 KiB: {png_path}")
                w, h, _ = _parse_and_validate_png(raw)
                self.assertEqual((w, h), (1024, 540))
                bucket[stem] = hashlib.sha256(raw).hexdigest()

        self.assertEqual(len(set(alpha_digests.values())), len(self.EXPECTED_STEMS))
        self.assertEqual(len(set(comp_digests.values())), len(self.EXPECTED_STEMS))

        expected_deltas = (
            ("r12a-fn-big6-tchinese", "r10b-fn-big6-home", 11252),
            ("r12b-fn-big6-japanese", "r10b-fn-big6-home", 11961),
            ("r12d-c2-menu-3layer-japanese", "r10d-c2-menu-3layer", 109578),
        )
        for s12, s10, exp_diff in expected_deltas:
            _, _, rows12 = _decode_png_rgba_rows((ROUND12_ASSETS_DIR / f"{s12}-alpha.png").read_bytes())
            _, _, rows10 = _decode_png_rgba_rows((ROUND10_ASSETS_DIR / f"{s10}-alpha.png").read_bytes())
            self.assertEqual(_diff_rows_u32(rows12, rows10), exp_diff)

        for stem, exp_amber in (
            ("r12c-p110-assignable-button-schinese", 260),
            ("r12d-c2-menu-3layer-japanese", 1257),
        ):
            _, _, rows = _decode_png_rgba_rows((ROUND12_ASSETS_DIR / f"{stem}-alpha.png").read_bytes())
            self.assertEqual(_count_amber_u32(rows), exp_amber)


class TestRound13StatusCheckAndFourLangMatrixClosure(unittest.TestCase):
    EXPECTED_STEMS = (
        "r13a-status-check-schinese",
        "r13b-menu-3layer-tchinese",
        "r13c-menu-3layer-paintlook-schinese",
    )
    EXPECTED_RUN_KEYS = (
        "r13a_status_check_schinese",
        "r13b_menu_3layer_tchinese",
        "r13c_menu_3layer_paintlook_schinese",
    )

    def test_round13_c_source_guards_and_runner_support(self) -> None:
        shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")

        self.assertIn("#if FX6_ROUND >= 13", shim_src)
        for token in (
            "fx6_lang_font_bank",
            "FX6_R13_LANG_TELEMETRY",
            "FX6_STAGE_B_R13_BRIDGE",
            "4lang_matrix=1",
        ):
            self.assertIn(token, shim_src)

        for token in ("/etc/fx6_stage_r13", "FX6_STAGE_B_R13_VERIFY_PASS"):
            self.assertIn(token, verify_src)

        for token in (
            "enable_r13",
            "etc/fx6_stage_r13",
            '"r13_telemetry"',
            "def decode_png_rgba_rows",
            "def compute_png_pixel_diff",
            "choices=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]",
        ):
            self.assertIn(token, runner_src)

    def test_round13_stage_a_overlay_english_and_clean_room_fallback(self) -> None:
        r12_helper = TestRound12MultiCjkP4P110AndReport()
        r12_helper._run_overlay_lang_dual_mode(
            lang="english",
            uxc1_name="string_english.uxc",
            uxc2_name="string_english_2.uxc",
            ltt_name="UniversOTS-SJ_wIcon.ltt",
            fontlist_key="FONT_UNIVERS",
            asset_key_u1="string_english",
            asset_key_ltt="font_univers_ltt",
            donor_attr_u1="DONOR_STRING_ENGLISH_UXC",
            donor_attr_u2="DONOR_STRING_ENGLISH_2_UXC",
            donor_attr_ltt="DONOR_FONT_ENGLISH_LTT",
        )

    def test_round13_stage_a_overlay_r13_flag_and_4lang_map(self) -> None:
        runner = _load_closure_module(
            "fx6_build_and_run_round_r13_map", "build_and_run_round.py"
        )
        self.assertEqual(
            runner.LANG_CODE_MAP,
            {"en": 0, "english": 0, "japanese": 1, "tchinese": 2, "schinese": 3},
        )
        self.assertEqual(runner.parse_key_seq("0x7052:120:5500"), [(0x7052, 120, 5500)])

    def test_round13_extract_milestones_lang_telemetry_parser(self) -> None:
        runner = _load_closure_module(
            "fx6_build_and_run_round_r13_ms", "build_and_run_round.py"
        )
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_STAGE_B_R13_VERIFY_PASS count=13 stage_b=1 p10_keymap=1 p11_uipc=1 p12_wlan=1 p4_nd_clear=1 uxc=1 lang=tchinese",
                "FX6_STAGE_B_R13_BRIDGE round=13 faithful=1 nop_count=0 p12_wlan=1 p10_keymap=1 p4_nd_clear=1 p11_xlr_h1=1 lang=tchinese bk4_lang=0x18 enum=0x2b44_LANGUAGE_CHINESE_TRADITIONAL font_bank=27 str_bank=22 4lang_matrix=1",
                "FX6_R13_LANG_TELEMETRY reason=pump lang=tchinese bk4_lang_id=0x02cf019c bk4_lang_val=0x18 lang_enum=0x2b44_LANGUAGE_CHINESE_TRADITIONAL font_bank=27 str_bank=22 lang_bk4_hits=3 airplane_bk4_hits=0 p4_nd_clear=1 p10_keymap=1 p11_xlr_h1=1 p12_wlan=1 font_create=26569 glyph_blits=16282 icon_blits=14282 gpe_alloc=167 gpe_fb=0 subst_color=0 subst_image=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        self.assertEqual(ms["prefix_counts"]["FX6_R13_"], 1)
        r13 = ms["r13_telemetry"]
        self.assertIsNotNone(r13)
        self.assertEqual(r13["lang"], "tchinese")
        self.assertEqual(r13["font_bank"], 27)
        self.assertEqual(r13["str_bank"], 22)
        self.assertEqual(r13["gpe_alloc"], 167)
        self.assertEqual(r13["gpe_fb"], 0)
        self.assertEqual(r13["subst_color"], 0)
        self.assertEqual(r13["subst_image"], 0)

    def test_round13_png_pixel_diff_helper_synthetic_vectors(self) -> None:
        runner = _load_closure_module(
            "fx6_build_and_run_round_r13_diff", "build_and_run_round.py"
        )
        with tempfile.TemporaryDirectory() as tmp:
            p1 = pathlib.Path(tmp) / "a.png"
            p2 = pathlib.Path(tmp) / "b.png"
            p3 = pathlib.Path(tmp) / "c.png"
            buf_a = bytearray(b"\x10\x20\x30\xff" * 4)
            buf_b = bytearray(buf_a)
            buf_b[0:4] = b"\xff\xaa\x00\xff"
            runner.write_rgba_png(p1, 2, 2, bytes(buf_a))
            runner.write_rgba_png(p2, 2, 2, bytes(buf_b))
            runner.write_rgba_png(p3, 4, 1, bytes(buf_a))
            self.assertEqual(runner.compute_png_pixel_diff(p1, p1), 0)
            self.assertEqual(runner.compute_png_pixel_diff(p1, p2), 1)
            with self.assertRaises(ValueError):
                runner.compute_png_pixel_diff(p1, p3)

    def test_round13_donor_english_assets_readonly_when_present(self) -> None:
        if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1":
            self.skipTest("FX3_FX6_FORCE_CLEAN_ROOM=1")
        runner = _load_closure_module(
            "fx6_build_and_run_round_r13_en_assets", "build_and_run_round.py"
        )
        checked = 0
        for path, magic in (
            (runner.DONOR_STRING_ENGLISH_UXC, b"uxc\x07"),
            (runner.DONOR_STRING_ENGLISH_2_UXC, b"uxc\x07"),
            (runner.DONOR_FONT_ENGLISH_LTT, b"LTT\n"),
        ):
            if not path.is_file():
                continue
            data = runner.read_bytes_readonly(path)
            self.assertEqual(data[:4], magic)
            self.assertGreater(len(data), 50000)
            checked += 1
        if checked == 0:
            self.skipTest("Optional donor English UXC/LTT assets absent")

    def test_round13_report_and_summary_json_invariants(self) -> None:
        self.assertTrue((ROUND13_REPORT_DIR / "README.md").is_file())
        closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn("2026-11-14-round13-fx6-on-fx3-status-4lang-closure", closure_readme)
        r13_readme = (ROUND13_REPORT_DIR / "README.md").read_text(encoding="utf-8")
        for forbidden in ("/Volumes/KAFU2T", "/Users/"):
            self.assertNotIn(forbidden, r13_readme)

        summary_path = ROUND13_REPORT_DIR / "summary.json"
        self.assertTrue(summary_path.is_file())
        raw_text = summary_path.read_text(encoding="utf-8")
        for forbidden in ("/Volumes/KAFU2T", "/private/tmp", "/Users/"):
            self.assertNotIn(forbidden, raw_text)
        data = json.loads(raw_text)
        self.assertEqual(data["schema"], "fx6-on-fx3-round13-status-4lang-closure-v1")
        self.assertIn("Linux version 4.9.337-scel+", data["kernel_version"])
        self.assertEqual(set(data["languages"].keys()), {"en", "tchinese", "japanese", "schinese"})

        runs = data["runs"]
        self.assertEqual(set(runs.keys()), set(self.EXPECTED_RUN_KEYS))
        expectations = {
            "r13a_status_check_schinese": ("schinese", "0x2f", "0x19", 437403, 85, 237),
            "r13b_menu_3layer_tchinese": ("tchinese", "0x11", "0x18", 437575, 248, 1257),
            "r13c_menu_3layer_paintlook_schinese": ("schinese", "0x11", "0x19", 437095, 268, 804),
        }
        for key, (lang, sid, bk4_val, exp_px, exp_col, exp_amber) in expectations.items():
            run = runs[key]
            self.assertEqual(run["round"], 13)
            self.assertEqual(run["lang"], lang)
            self.assertEqual(run["target_sid"], sid)
            self.assertEqual(run["nop_count"], 0)
            self.assertEqual(run["crashes"], 0)
            self.assertGreater(run["ldec103_ioctl_count"], 40)
            self.assertGreaterEqual(run["total_threads_seen"], 161)
            sb = run["stage_b"]
            self.assertTrue(sb["r13_enabled"])
            self.assertEqual(sb["manifest_count"], 13)
            markers = "\n".join(sb["guest_boot_markers"])
            self.assertIn("FX6_STAGE_A_VERIFY_PASS count=13", markers)
            self.assertIn(f"FX6_STAGE_B_R13_VERIFY_PASS count=13", markers)
            self.assertIn("FX6_STAGE_B_R13_BRIDGE round=13 faithful=1 nop_count=0", markers)
            self.assertEqual(run["r13_telemetry"]["bk4_lang_val"], bk4_val)
            self.assertEqual(run["r13_telemetry"]["gpe_fb"], 0)
            self.assertEqual(run["gpe0_readback"]["nonzero_pixels"], exp_px)
            self.assertEqual(run["gpe0_readback"]["unique_colors"], exp_col)
            self.assertEqual(run["amber_0xffffaa00_pixels"], exp_amber)

    def test_round13_4lang_6pair_matrix_and_switchbank_invariants(self) -> None:
        data = json.loads((ROUND13_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        audit = data["r13d_4lang_matrix_audit"]
        self.assertEqual(audit["languages_verified"], ["en", "schinese", "tchinese", "japanese"])
        self.assertTrue(audit["all_6_pairs_strictly_positive_big6"])
        self.assertTrue(audit["all_6_pairs_strictly_positive_menu"])

        sw = audit["switch_bank_matrix"]
        self.assertEqual(sw["en"]["uxc_banks"], {"font": 0, "ns1_string": 4, "ns2_string": 4})
        self.assertEqual(sw["schinese"]["uxc_banks"], {"font": 23, "ns1_string": 19, "ns2_string": 19})
        self.assertEqual(sw["tchinese"]["uxc_banks"], {"font": 27, "ns1_string": 22, "ns2_string": 22})
        self.assertEqual(sw["japanese"]["uxc_banks"], {"font": 1, "ns1_string": 12, "ns2_string": 12})

        for section in ("big6_home_6pair_deltas", "full_menu_6pair_deltas"):
            pairs = audit[section]
            self.assertEqual(len(pairs), 6)
            for pair_info in pairs.values():
                self.assertTrue(pair_info["strictly_positive"])
                self.assertGreater(pair_info["diff_pixels"], 0)
                self.assertTrue((REPO_ROOT / pair_info["png_a"]).is_file())
                self.assertTrue((REPO_ROOT / pair_info["png_b"]).is_file())

    def test_round13_png_receipts_valid_size_under_85kib_and_amber(self) -> None:
        self.assertTrue(ROUND13_ASSETS_DIR.is_dir())
        alpha_digests: Dict[str, str] = {}
        comp_digests: Dict[str, str] = {}
        for stem in self.EXPECTED_STEMS:
            for variant, bucket in (("alpha", alpha_digests), ("composited", comp_digests)):
                png_path = ROUND13_ASSETS_DIR / f"{stem}-{variant}.png"
                self.assertTrue(png_path.is_file(), f"Missing Round 13 PNG: {png_path}")
                raw = png_path.read_bytes()
                self.assertLess(len(raw), 85 * 1024, f"PNG exceeds 85 KiB: {png_path}")
                w, h, _ = _parse_and_validate_png(raw)
                self.assertEqual((w, h), (1024, 540))
                bucket[stem] = hashlib.sha256(raw).hexdigest()
        self.assertEqual(len(set(alpha_digests.values())), len(self.EXPECTED_STEMS))
        self.assertEqual(len(set(comp_digests.values())), len(self.EXPECTED_STEMS))

        for stem, exp_amber in (
            ("r13a-status-check-schinese", 237),
            ("r13b-menu-3layer-tchinese", 1257),
            ("r13c-menu-3layer-paintlook-schinese", 804),
        ):
            _, _, rows = _decode_png_rgba_rows((ROUND13_ASSETS_DIR / f"{stem}-alpha.png").read_bytes())
            self.assertEqual(_count_amber_u32(rows), exp_amber)


class TestRound14StatusCheck4LangFullMatrix(unittest.TestCase):
    EXPECTED_STEMS = (
        "r14a-status-check-japanese",
        "r14b-status-check-tchinese",
        "r14c-status-check-english",
    )
    EXPECTED_RUN_KEYS = (
        "r14a_status_check_japanese",
        "r14b_status_check_tchinese",
        "r14c_status_check_english",
    )

    def test_round14_c_source_guards_and_runner_support(self) -> None:
        shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")

        self.assertIn("#if FX6_ROUND >= 14", shim_src)
        for token in (
            "FX6_R14_LANG_TELEMETRY",
            "FX6_STAGE_B_R14_BRIDGE",
            "statuscheck_4lang_matrix=1",
            "statuscheck_matrix=1",
        ):
            self.assertIn(token, shim_src)

        for token in (
            "/etc/fx6_stage_r14",
            "FX6_STAGE_B_R14_VERIFY_PASS",
            "statuscheck_4lang=1",
        ):
            self.assertIn(token, verify_src)

        for token in (
            "enable_r14",
            "etc/fx6_stage_r14",
            '"r14_telemetry"',
            '"fx6-r14"',
            "choices=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]",
        ):
            self.assertIn(token, runner_src)

    def _assert_r14_overlay_dual_mode(
        self,
        lang: str,
        uxc1_name: str,
        uxc2_name: str,
        ltt_name: str,
        fontlist_key: str,
        asset_key_u1: str,
        asset_key_ltt: str,
        donor_attr_u1: str,
        donor_attr_u2: str,
        donor_attr_ltt: str,
    ) -> None:
        runner = _load_closure_module(
            f"fx6_build_and_run_round_r14_ovl_{lang}", "build_and_run_round.py"
        )
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            parent_cpio = tmp_dir / "parent.cpio"
            init_body = (
                b"#!/bin/sh\n"
                b'LD_PRELOAD="$FX6_PRELOAD" /usr/bin/appfw-launch\n'
            )
            members = (
                ("init", init_body),
                ("usr/lib/libInfraSetupFile.so", b"SETUP"),
                ("usr/lib/libInfraMediaCommon.so", b"MCOMM"),
                ("usr/lib/libInfraMediaConfig.so", b"MCFG"),
                ("usr/lib/libInfraAppRemoteBoard.so", b"RBRD"),
                ("usr/lib/libfan.so", b"FAN"),
                ("usr/lib/appFw.so", b"APPFW"),
                ("usr/lib/libWlanResource.so", b"WLAN_DONOR_12345"),
                ("usr/kmod/upm.ko", b"UPMKO"),
                ("usr/share/app/image_00_169.uxc", b"uxd\x07" + b"C" * 32),
                (f"usr/share/app/{uxc1_name}", b"uxc\x07" + b"C1" * 16),
                (f"usr/share/app/{uxc2_name}", b"uxc\x07" + b"C2" * 16),
                (f"usr/share/app/{ltt_name}", b"LTT\n" + b"CL" * 16),
                (
                    "usr/share/app/fontlist.dat",
                    f"{fontlist_key}\t/usr/share/app/{ltt_name}\t0\t0\n".encode("ascii"),
                ),
            )
            archive = b"".join(
                runner.make_cpio_member(name, body, ino=idx + 1, mode=0o100755)
                for idx, (name, body) in enumerate(members)
            ) + runner.make_cpio_member("TRAILER!!!", b"", ino=0, mode=0)
            parent_cpio.write_bytes(archive)

            class _FakeRes:
                def __init__(self, site_id: str) -> None:
                    self.site_id = site_id

            class _FakeReceipt:
                def __init__(self, before: bytes, after: bytes, sites: list) -> None:
                    self.before_sha256 = hashlib.sha256(before).hexdigest()
                    self.after_sha256 = hashlib.sha256(after).hexdigest()
                    self.changed_byte_count = 8
                    self.resolutions = [_FakeRes(s.site_id) for s in sites]

            class _FakePatcher:
                P1_P4_P8_APPFW_COMBINED_SPEC = mock.Mock(
                    library_name="appFw.so",
                    expected_size=5,
                    donor_sha256="0" * 64,
                    sites=(mock.Mock(site_id="p1"),),
                    elf_kind="so",
                    source_domain="fx6",
                )
                P1_LIB_INFRA_SETUP_FILE_SPEC = mock.Mock(spec_id="P1_s", library_name="s", sites=[mock.Mock(site_id="s1")])
                P1_LIB_INFRA_MEDIA_COMMON_SPEC = mock.Mock(spec_id="P1_c", library_name="c", sites=[mock.Mock(site_id="c1")])
                P1_LIB_INFRA_MEDIA_CONFIG_SPEC = mock.Mock(spec_id="P1_g", library_name="g", sites=[mock.Mock(site_id="g1")])
                P3_LIB_INFRA_APP_REMOTE_BOARD_SPEC = mock.Mock(spec_id="P3_r", library_name="r", sites=[mock.Mock(site_id="r1")])
                FAN_LIBFAN_SPEC = mock.Mock(spec_id="Fan_f", library_name="f", sites=[mock.Mock(site_id="f1")])
                P9_UPM_KO_SPEC = mock.Mock(spec_id="P9_u", library_name="upm.ko", sites=[mock.Mock(site_id="u1")])
                LibraryPatchSpec = lambda **kw: type("FakeSpec", (), kw)()
                PatchSiteSpec = object
                PF_R = 4

                @staticmethod
                def apply_patch_spec(data: bytes, spec: object, verify_donor_sha256: bool = True):
                    after = data + b"_P"
                    return after, _FakeReceipt(data, after, getattr(spec, "sites", []))

                @staticmethod
                def resolve_and_verify_sites(data: bytes, spec: object, expect_patched_state: bool = True):
                    return [_FakeRes("u1")]

            class _FakeVfat:
                @staticmethod
                def build_opelog_vfat_image(mode: str):
                    img = b"VFAT" * 16
                    receipt = mock.Mock(
                        mode=mode,
                        fat_type="FAT16",
                        total_bytes=len(img),
                        sha256=hashlib.sha256(img).hexdigest(),
                        precreated_dirs=("OPE", "OPE/00", "OPE/01"),
                    )
                    return img, receipt

                @staticmethod
                def verify_vfat_image(_img: bytes):
                    return mock.Mock(valid=True, errors=[])

            class _FakeBmtv:
                @staticmethod
                def build_canonical_fa0080_normal_boot_table(donor_seed_bk4_path=None):
                    return b"T"

                @staticmethod
                def synthesize_ram_shadow_bk4(**_kw):
                    bk = b"BK4\x00" + b"\x00" * 12
                    return mock.Mock(
                        bk4_bytes=bk,
                        total_bytes=len(bk),
                        sha256=hashlib.sha256(bk).hexdigest(),
                        flash_write_allowed=False,
                        active_byte8_selector=0,
                        synthesized_key_count=1,
                    )

            fake_p10 = type(
                "FakeP10",
                (),
                {
                    "spec_id": "P10_FX3_TO_FX6_KEYMAP_ADAPTER",
                    "library_name": "appFw.so",
                    "sites": (mock.Mock(site_id="p10_fn", size=4),),
                },
            )()
            fake_p12 = type(
                "FakeP12",
                (),
                {
                    "spec_id": "P12_libWlanResource_fatal_guard",
                    "library_name": "libWlanResource.so",
                    "sites": (mock.Mock(site_id="p12_wlan", size=8),),
                },
            )()

            def _fake_subproc_run(cmd, **_kw):
                out_path = pathlib.Path(cmd[-1])
                out_path.write_bytes(b"ELF_VERIFY_14")
                return mock.Mock(returncode=0, stderr="")

            donor_u1 = tmp_dir / "donor_u1.uxc"
            donor_u2 = tmp_dir / "donor_u2.uxc"
            donor_ltt = tmp_dir / "donor_font.ltt"
            donor_uxc = tmp_dir / "donor_img.uxc"
            donor_u1.write_bytes(b"uxc\x07" + b"D1" * 16)
            donor_u2.write_bytes(b"uxc\x07" + b"D2" * 16)
            donor_ltt.write_bytes(b"LTT\n" + b"FD" * 16)
            donor_uxc.write_bytes(b"uxd\x07" + b"D" * 32)
            build_dir = tmp_dir / "build"

            with mock.patch.object(
                runner, "_import_stage_a_modules", return_value=(_FakePatcher, _FakeVfat, _FakeBmtv)
            ), mock.patch.object(
                runner, "_load_p10_keymap_spec", return_value=fake_p10
            ), mock.patch.object(
                runner, "_load_p12_wlan_spec", return_value=fake_p12
            ), mock.patch.object(
                runner, "DONOR_IMAGE_00_169_UXC", donor_uxc
            ), mock.patch.object(
                runner, donor_attr_u1, donor_u1
            ), mock.patch.object(
                runner, donor_attr_u2, donor_u2
            ), mock.patch.object(
                runner, donor_attr_ltt, donor_ltt
            ), mock.patch.object(
                runner, "FX3_UPM_KO", tmp_dir / "absent_upm.ko"
            ), mock.patch.object(
                runner, "FX3_SEED_BK4", tmp_dir / "absent_seed.bin"
            ), mock.patch.object(
                runner.subprocess, "run", side_effect=_fake_subproc_run
            ):
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
                    rep, add, meta = runner.build_stage_a_overlay(
                        build_dir,
                        parent_cpio,
                        b"BK4_NTSC",
                        enable_p10=True,
                        enable_r10=True,
                        enable_p12=True,
                        enable_r12=True,
                        enable_r13=True,
                        enable_r14=True,
                        lang=lang,
                        shim_bytes=b"SHIM14",
                    )
                self.assertEqual(meta["manifest_count"], 13)
                self.assertTrue(meta["r13_enabled"])
                self.assertTrue(meta["r14_enabled"])
                self.assertEqual(meta["lang"], lang)
                self.assertIn("etc/fx6_stage_r14", add)
                self.assertIn(f"statuscheck_4lang=1\nlang={lang}\n".encode("utf-8"), add["etc/fx6_stage_r14"][0])
                self.assertEqual(meta["lang_assets"][asset_key_u1]["source"], "cpio_preloaded")
                self.assertEqual(meta["lang_assets"][asset_key_ltt]["source"], "cpio_preloaded")
                self.assertEqual(meta["lang_assets"]["fontlist_dat"]["fontlist_key"], fontlist_key)
                self.assertEqual(rep[f"usr/share/app/{uxc2_name}"], b"uxc\x07" + b"C2" * 16)

                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "0"}):
                    rep2, add2, meta2 = runner.build_stage_a_overlay(
                        build_dir,
                        parent_cpio,
                        b"BK4_NTSC",
                        enable_p10=True,
                        enable_r10=True,
                        enable_p12=True,
                        enable_r12=True,
                        enable_r13=True,
                        enable_r14=True,
                        lang=lang,
                        shim_bytes=b"SHIM14",
                    )
                self.assertTrue(meta2["r14_enabled"])
                self.assertIn("etc/fx6_stage_r14", add2)
                self.assertEqual(meta2["lang_assets"][asset_key_u1]["source"], "donor_o_rdonly")
                self.assertEqual(rep2[f"usr/share/app/{ltt_name}"], b"LTT\n" + b"FD" * 16)

    def test_round14_stage_a_overlay_japanese_dual_mode(self) -> None:
        self._assert_r14_overlay_dual_mode(
            lang="japanese",
            uxc1_name="string_japanese.uxc",
            uxc2_name="string_japanese_2.uxc",
            ltt_name="HeiseiKakuGothW5-SJ_wIcon.ltt",
            fontlist_key="FONT_JAPANESE",
            asset_key_u1="string_japanese",
            asset_key_ltt="font_japanese_ltt",
            donor_attr_u1="DONOR_STRING_JAPANESE_UXC",
            donor_attr_u2="DONOR_STRING_JAPANESE_2_UXC",
            donor_attr_ltt="DONOR_FONT_JAPANESE_LTT",
        )

    def test_round14_stage_a_overlay_tchinese_and_english_dual_mode(self) -> None:
        self._assert_r14_overlay_dual_mode(
            lang="tchinese",
            uxc1_name="string_traditionalchinese.uxc",
            uxc2_name="string_traditionalchinese_2.uxc",
            ltt_name="MYingHeiC-Big5HKSCS-SJ_wIcon.ltt",
            fontlist_key="FONT_T_CHINESE",
            asset_key_u1="string_traditionalchinese",
            asset_key_ltt="font_big5hkscs_ltt",
            donor_attr_u1="DONOR_STRING_TCHINESE_UXC",
            donor_attr_u2="DONOR_STRING_TCHINESE_2_UXC",
            donor_attr_ltt="DONOR_FONT_TCHINESE_LTT",
        )
        self._assert_r14_overlay_dual_mode(
            lang="english",
            uxc1_name="string_english.uxc",
            uxc2_name="string_english_2.uxc",
            ltt_name="UniversOTS-SJ_wIcon.ltt",
            fontlist_key="FONT_UNIVERS",
            asset_key_u1="string_english",
            asset_key_ltt="font_univers_ltt",
            donor_attr_u1="DONOR_STRING_ENGLISH_UXC",
            donor_attr_u2="DONOR_STRING_ENGLISH_2_UXC",
            donor_attr_ltt="DONOR_FONT_ENGLISH_LTT",
        )

    def test_round14_extract_milestones_lang_telemetry_parser(self) -> None:
        runner = _load_closure_module(
            "fx6_build_and_run_round_r14_ms", "build_and_run_round.py"
        )
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_STAGE_B_R14_VERIFY_PASS count=13 stage_b=1 p10_keymap=1 p11_uipc=1 p12_wlan=1 p4_nd_clear=1 uxc=1 statuscheck_4lang=1 lang=japanese",
                "FX6_STAGE_B_R14_BRIDGE round=14 faithful=1 nop_count=0 p12_wlan=1 p10_keymap=1 p4_nd_clear=1 p11_xlr_h1=1 lang=japanese bk4_lang=0x01 enum=0x2b30_LANGUAGE_JAPANESE font_bank=1 str_bank=12 statuscheck_4lang_matrix=1",
                "FX6_R14_LANG_TELEMETRY reason=pump lang=japanese bk4_lang_id=0x02cf019c bk4_lang_val=0x01 lang_enum=0x2b30_LANGUAGE_JAPANESE font_bank=1 str_bank=12 lang_bk4_hits=3 airplane_bk4_hits=0 p4_nd_clear=1 p10_keymap=1 p11_xlr_h1=1 p12_wlan=1 font_create=31481 glyph_blits=16741 icon_blits=8127 gpe_alloc=101 gpe_fb=0 statuscheck_matrix=1 subst_color=0 subst_image=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        self.assertEqual(ms["prefix_counts"]["FX6_R14_"], 1)
        r14 = ms["r14_telemetry"]
        self.assertIsNotNone(r14)
        self.assertEqual(r14["lang"], "japanese")
        self.assertEqual(r14["bk4_lang_val"], "0x01")
        self.assertEqual(r14["font_bank"], 1)
        self.assertEqual(r14["str_bank"], 12)
        self.assertEqual(r14["gpe_alloc"], 101)
        self.assertEqual(r14["gpe_fb"], 0)
        self.assertEqual(r14["statuscheck_matrix"], 1)
        self.assertEqual(r14["subst_color"], 0)
        self.assertEqual(r14["subst_image"], 0)

    def test_round14_report_and_summary_json_invariants(self) -> None:
        self.assertTrue((ROUND14_REPORT_DIR / "README.md").is_file())
        summary_path = ROUND14_REPORT_DIR / "summary.json"
        self.assertTrue(summary_path.is_file())
        raw_text = summary_path.read_text(encoding="utf-8")
        for forbidden in ("/Volumes/KAFU2T", "/private/tmp", "/Users/"):
            self.assertNotIn(forbidden, raw_text)
        data = json.loads(raw_text)
        self.assertEqual(data["schema"], "fx6-on-fx3-round14-statuscheck-4lang-matrix-v1")
        self.assertIn("Linux version 4.9.337-scel+", data["kernel_version"])
        self.assertEqual(set(data["languages"].keys()), {"en", "tchinese", "japanese", "schinese"})

        runs = data["runs"]
        self.assertEqual(set(runs.keys()), set(self.EXPECTED_RUN_KEYS))
        expectations = {
            "r14a_status_check_japanese": ("japanese", "0x2f", "0x01", 1, 12, 437883, 85, 237),
            "r14b_status_check_tchinese": ("tchinese", "0x2f", "0x18", 27, 22, 437883, 85, 237),
            "r14c_status_check_english": ("english", "0x2f", "0x00", 0, 4, 437883, 83, 272),
        }
        for key, (lang, sid, bk4_val, font_b, str_b, exp_px, exp_col, exp_amber) in expectations.items():
            run = runs[key]
            self.assertEqual(run["round"], 14)
            self.assertEqual(run["lang"], lang)
            self.assertEqual(run["target_sid"], sid)
            self.assertEqual(run["target_presenter"], "34procam_touch_status_main_presenter")
            self.assertEqual(run["status_check_controller"], "35procam_touch_status_main_controller")
            self.assertEqual(run["status_check_infra_key"], "0x7052")
            self.assertEqual(run["nop_count"], 0)
            self.assertEqual(run["crashes"], 0)
            self.assertGreater(run["ldec103_ioctl_count"], 40)
            self.assertGreaterEqual(run["total_threads_seen"], 161)
            self.assertEqual(
                run["faithful_invariants"],
                {
                    "FX6_NATIVE_FAITHFUL": 1,
                    "subst_color": 0,
                    "subst_image": 0,
                    "forced_render": 0,
                    "skipped_node": 0,
                    "lock_bypass": 0,
                },
            )
            sb = run["stage_b"]
            self.assertTrue(sb["r13_enabled"])
            self.assertTrue(sb["r14_enabled"])
            self.assertEqual(sb["manifest_count"], 13)
            markers = "\n".join(sb["guest_boot_markers"])
            self.assertIn("FX6_STAGE_A_VERIFY_PASS count=13", markers)
            self.assertIn(f"FX6_STAGE_B_R14_VERIFY_PASS count=13 stage_b=1 p10_keymap=1 p11_uipc=1 p12_wlan=1 p4_nd_clear=1 uxc=1 statuscheck_4lang=1 lang={lang}", markers)
            self.assertIn("FX6_STAGE_B_R14_BRIDGE round=14 faithful=1 nop_count=0", markers)
            self.assertIn("FX6_STAGE_B_P4_ND_CLEAR_CHECK ok=1 nd_mode=0xd503201f nd_val=0x1400001b", markers)
            telem = run["r14_telemetry"]
            self.assertEqual(telem["lang"], lang)
            self.assertEqual(telem["bk4_lang_val"], bk4_val)
            self.assertEqual(telem["font_bank"], font_b)
            self.assertEqual(telem["str_bank"], str_b)
            self.assertEqual(telem["airplane_bk4_hits"], 0)
            self.assertEqual(telem["p12_wlan"], 1)
            self.assertEqual(telem["gpe_fb"], 0)
            self.assertEqual(telem["statuscheck_matrix"], 1)
            self.assertEqual(telem["subst_color"], 0)
            self.assertEqual(telem["subst_image"], 0)
            self.assertEqual(run["gpe0_readback"]["nonzero_pixels"], exp_px)
            self.assertEqual(run["gpe0_readback"]["unique_colors"], exp_col)
            self.assertEqual(run["amber_0xffffaa00_pixels"], exp_amber)

    def test_round14_stage_b_manifest_13_sha256_integrity(self) -> None:
        data = json.loads((ROUND14_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        shared_by_path: Dict[str, str] = {}
        for key in self.EXPECTED_RUN_KEYS:
            items = data["runs"][key]["stage_b"]["manifest_items"]
            self.assertEqual(len(items), 13)
            for item in items:
                gpath = item["guest_path"]
                digest = item["sha256"]
                self.assertEqual(len(digest), 64)
                int(digest, 16)
                if gpath == "/usr/lib/libgrm-fbinit9.so":
                    continue
                if gpath in shared_by_path:
                    self.assertEqual(shared_by_path[gpath], digest, f"SHA mismatch on {gpath}")
                else:
                    shared_by_path[gpath] = digest
        self.assertEqual(len(shared_by_path), 12)

    def test_round14_3surface_4lang_18pair_matrix_and_switchbank(self) -> None:
        data = json.loads((ROUND14_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        audit = data["r14d_3surface_4lang_matrix_audit"]
        self.assertEqual(audit["languages_verified"], ["en", "schinese", "tchinese", "japanese"])
        self.assertEqual(audit["surfaces_verified"], ["big6_home", "full_menu", "status_check"])
        self.assertEqual(audit["total_surfaces"], 3)
        self.assertEqual(audit["pairs_per_surface"], 6)
        self.assertEqual(audit["total_matrix_pairs"], 18)
        self.assertEqual(audit["positive_matrix_pairs"], 18)
        self.assertTrue(audit["all_18_pairs_strictly_positive"])
        self.assertTrue(audit["all_6_pairs_strictly_positive_big6"])
        self.assertTrue(audit["all_6_pairs_strictly_positive_menu"])
        self.assertTrue(audit["all_6_pairs_strictly_positive_status_check"])

        sw = audit["switch_bank_matrix"]
        self.assertEqual(sw["en"]["uxc_banks"], {"font": 0, "ns1_string": 4, "ns2_string": 4})
        self.assertEqual(sw["schinese"]["uxc_banks"], {"font": 23, "ns1_string": 19, "ns2_string": 19})
        self.assertEqual(sw["tchinese"]["uxc_banks"], {"font": 27, "ns1_string": 22, "ns2_string": 22})
        self.assertEqual(sw["japanese"]["uxc_banks"], {"font": 1, "ns1_string": 12, "ns2_string": 12})

        for section in ("big6_home_6pair_deltas", "full_menu_6pair_deltas", "status_check_6pair_deltas"):
            pairs = audit[section]
            self.assertEqual(len(pairs), 6)
            for pair_info in pairs.values():
                self.assertTrue(pair_info["strictly_positive"])
                self.assertGreater(pair_info["diff_pixels"], 0)
                self.assertTrue((REPO_ROOT / pair_info["png_a"]).is_file())
                self.assertTrue((REPO_ROOT / pair_info["png_b"]).is_file())

        for closure_key in (
            "four_lang_status_check_closure",
            "four_lang_3layer_menu_parity_closure",
            "four_lang_big6_home_closure",
        ):
            self.assertEqual(
                set(audit[closure_key].keys()),
                {"en", "schinese", "tchinese", "japanese"},
            )
            for lang_entry in audit[closure_key].values():
                self.assertTrue((REPO_ROOT / lang_entry["png_alpha"]).is_file())

    def test_round14_png_receipts_valid_under_85kib_and_amber(self) -> None:
        self.assertTrue(ROUND14_ASSETS_DIR.is_dir())
        alpha_digests: Dict[str, str] = {}
        comp_digests: Dict[str, str] = {}
        for stem in self.EXPECTED_STEMS:
            for variant, bucket in (("alpha", alpha_digests), ("composited", comp_digests)):
                png_path = ROUND14_ASSETS_DIR / f"{stem}-{variant}.png"
                self.assertTrue(png_path.is_file(), f"Missing Round 14 PNG: {png_path}")
                raw = png_path.read_bytes()
                self.assertLess(len(raw), 85 * 1024, f"PNG exceeds 85 KiB: {png_path}")
                w, h, _ = _parse_and_validate_png(raw)
                self.assertEqual((w, h), (1024, 540))
                bucket[stem] = hashlib.sha256(raw).hexdigest()
        self.assertEqual(len(set(alpha_digests.values())), len(self.EXPECTED_STEMS))
        self.assertEqual(len(set(comp_digests.values())), len(self.EXPECTED_STEMS))

        for stem, exp_amber in (
            ("r14a-status-check-japanese", 237),
            ("r14b-status-check-tchinese", 237),
            ("r14c-status-check-english", 272),
        ):
            _, _, rows = _decode_png_rgba_rows((ROUND14_ASSETS_DIR / f"{stem}-alpha.png").read_bytes())
            self.assertEqual(_count_amber_u32(rows), exp_amber)

    def test_round14_status_check_6pair_pixel_diffs_exact(self) -> None:
        status_pngs = {
            "en": ROUND14_ASSETS_DIR / "r14c-status-check-english-alpha.png",
            "schinese": ROUND13_ASSETS_DIR / "r13a-status-check-schinese-alpha.png",
            "tchinese": ROUND14_ASSETS_DIR / "r14b-status-check-tchinese-alpha.png",
            "japanese": ROUND14_ASSETS_DIR / "r14a-status-check-japanese-alpha.png",
        }
        decoded = {k: _decode_png_rgba_rows(p.read_bytes())[2] for k, p in status_pngs.items()}
        expected_pairs = (
            ("en", "schinese", 52819),
            ("en", "tchinese", 54998),
            ("en", "japanese", 47569),
            ("schinese", "tchinese", 22055),
            ("schinese", "japanese", 41484),
            ("tchinese", "japanese", 43856),
        )
        for la, lb, exp_diff in expected_pairs:
            diff = _diff_rows_u32(decoded[la], decoded[lb])
            self.assertGreater(diff, 0)
            self.assertEqual(diff, exp_diff)

    def test_round14_readme_and_no_tmp_scratch_residue(self) -> None:
        closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn("2026-11-14-round14-fx6-on-fx3-statuscheck-4lang-matrix", closure_readme)
        r14_readme = (ROUND14_REPORT_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn("18/18", r14_readme)
        self.assertIn("0x2f", r14_readme)
        for forbidden in ("/Volumes/KAFU2T", "/Users/"):
            self.assertNotIn(forbidden, r14_readme)
        tmp_matches = list(pathlib.Path("/private/tmp").glob("fx6-r14*"))
        self.assertEqual(tmp_matches, [], f"Leftover scratch dirs in /private/tmp: {tmp_matches}")


class TestRound15MultiTabStatusCheckAndMonitoring(unittest.TestCase):
    EXPECTED_STEMS = (
        "r15a-status-tab2-schinese",
        "r15b-status-tab3-schinese",
        "r15c-menu-3layer-monitoring-schinese",
        "r15d-status-tab2-japanese",
    )
    EXPECTED_RUN_KEYS = (
        "r15a_status_tab2_schinese",
        "r15b_status_tab3_schinese",
        "r15c_menu_3layer_monitoring_schinese",
        "r15d_status_tab2_japanese",
    )

    def test_round15_c_source_guards_and_runner_support(self) -> None:
        shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")

        self.assertIn("#if FX6_ROUND >= 15", shim_src)
        for token in (
            "FX6_R15_LANG_TELEMETRY",
            "FX6_STAGE_B_R15_BRIDGE",
            "multitab_status_monitoring=1",
            "statuscheck_multitab=1",
            "monitoring_3layer=1",
        ):
            self.assertIn(token, shim_src)

        for token in (
            "/etc/fx6_stage_r15",
            "FX6_STAGE_B_R15_VERIFY_PASS",
            "statuscheck_multitab=1",
            "monitoring_3layer=1",
        ):
            self.assertIn(token, verify_src)

        for token in (
            "enable_r15",
            "etc/fx6_stage_r15",
            '"r15_telemetry"',
            '"fx6-r15"',
            "choices=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]",
        ):
            self.assertIn(token, runner_src)

    def _assert_r15_overlay_dual_mode(
        self,
        lang: str,
        uxc1_name: str,
        uxc2_name: str,
        ltt_name: str,
        fontlist_key: str,
        asset_key_u1: str,
        asset_key_ltt: str,
        donor_attr_u1: str,
        donor_attr_u2: str,
        donor_attr_ltt: str,
    ) -> None:
        runner = _load_closure_module(
            f"fx6_build_and_run_round_r15_ovl_{lang}", "build_and_run_round.py"
        )
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            parent_cpio = tmp_dir / "parent.cpio"
            init_body = (
                b"#!/bin/sh\n"
                b'LD_PRELOAD="$FX6_PRELOAD" /usr/bin/appfw-launch\n'
            )
            members = (
                ("init", init_body),
                ("usr/lib/libInfraSetupFile.so", b"SETUP"),
                ("usr/lib/libInfraMediaCommon.so", b"MCOMM"),
                ("usr/lib/libInfraMediaConfig.so", b"MCFG"),
                ("usr/lib/libInfraAppRemoteBoard.so", b"RBRD"),
                ("usr/lib/libfan.so", b"FAN"),
                ("usr/lib/appFw.so", b"APPFW"),
                ("usr/lib/libWlanResource.so", b"WLAN_DONOR_12345"),
                ("usr/kmod/upm.ko", b"UPMKO"),
                ("usr/share/app/image_00_169.uxc", b"uxd\x07" + b"C" * 32),
                (f"usr/share/app/{uxc1_name}", b"uxc\x07" + b"C1" * 16),
                (f"usr/share/app/{uxc2_name}", b"uxc\x07" + b"C2" * 16),
                (f"usr/share/app/{ltt_name}", b"LTT\n" + b"CL" * 16),
                (
                    "usr/share/app/fontlist.dat",
                    f"{fontlist_key}\t/usr/share/app/{ltt_name}\t0\t0\n".encode("ascii"),
                ),
            )
            archive = b"".join(
                runner.make_cpio_member(name, body, ino=idx + 1, mode=0o100755)
                for idx, (name, body) in enumerate(members)
            ) + runner.make_cpio_member("TRAILER!!!", b"", ino=0, mode=0)
            parent_cpio.write_bytes(archive)

            class _FakeRes:
                def __init__(self, site_id: str) -> None:
                    self.site_id = site_id

            class _FakeReceipt:
                def __init__(self, before: bytes, after: bytes, sites: list) -> None:
                    self.before_sha256 = hashlib.sha256(before).hexdigest()
                    self.after_sha256 = hashlib.sha256(after).hexdigest()
                    self.changed_byte_count = 8
                    self.resolutions = [_FakeRes(s.site_id) for s in sites]

            class _FakePatcher:
                P1_P4_P8_APPFW_COMBINED_SPEC = mock.Mock(
                    library_name="appFw.so",
                    expected_size=5,
                    donor_sha256="0" * 64,
                    sites=(mock.Mock(site_id="p1"),),
                    elf_kind="so",
                    source_domain="fx6",
                )
                P1_LIB_INFRA_SETUP_FILE_SPEC = mock.Mock(spec_id="P1_s", library_name="s", sites=[mock.Mock(site_id="s1")])
                P1_LIB_INFRA_MEDIA_COMMON_SPEC = mock.Mock(spec_id="P1_c", library_name="c", sites=[mock.Mock(site_id="c1")])
                P1_LIB_INFRA_MEDIA_CONFIG_SPEC = mock.Mock(spec_id="P1_g", library_name="g", sites=[mock.Mock(site_id="g1")])
                P3_LIB_INFRA_APP_REMOTE_BOARD_SPEC = mock.Mock(spec_id="P3_r", library_name="r", sites=[mock.Mock(site_id="r1")])
                FAN_LIBFAN_SPEC = mock.Mock(spec_id="Fan_f", library_name="f", sites=[mock.Mock(site_id="f1")])
                P9_UPM_KO_SPEC = mock.Mock(spec_id="P9_u", library_name="upm.ko", sites=[mock.Mock(site_id="u1")])
                LibraryPatchSpec = lambda **kw: type("FakeSpec", (), kw)()
                PatchSiteSpec = object
                PF_R = 4

                @staticmethod
                def apply_patch_spec(data: bytes, spec: object, verify_donor_sha256: bool = True):
                    after = data + b"_P"
                    return after, _FakeReceipt(data, after, getattr(spec, "sites", []))

                @staticmethod
                def resolve_and_verify_sites(data: bytes, spec: object, expect_patched_state: bool = True):
                    return [_FakeRes("u1")]

            class _FakeVfat:
                @staticmethod
                def build_opelog_vfat_image(mode: str):
                    img = b"VFAT" * 16
                    receipt = mock.Mock(
                        mode=mode,
                        fat_type="FAT16",
                        total_bytes=len(img),
                        sha256=hashlib.sha256(img).hexdigest(),
                        precreated_dirs=("OPE", "OPE/00", "OPE/01"),
                    )
                    return img, receipt

                @staticmethod
                def verify_vfat_image(_img: bytes):
                    return mock.Mock(valid=True, errors=[])

            class _FakeBmtv:
                @staticmethod
                def build_canonical_fa0080_normal_boot_table(donor_seed_bk4_path=None):
                    return b"T"

                @staticmethod
                def synthesize_ram_shadow_bk4(**_kw):
                    bk = b"BK4\x00" + b"\x00" * 12
                    return mock.Mock(
                        bk4_bytes=bk,
                        total_bytes=len(bk),
                        sha256=hashlib.sha256(bk).hexdigest(),
                        flash_write_allowed=False,
                        active_byte8_selector=0,
                        synthesized_key_count=1,
                    )

            fake_p10 = type(
                "FakeP10",
                (),
                {
                    "spec_id": "P10_FX3_TO_FX6_KEYMAP_ADAPTER",
                    "library_name": "appFw.so",
                    "sites": (mock.Mock(site_id="p10_fn", size=4),),
                },
            )()
            fake_p12 = type(
                "FakeP12",
                (),
                {
                    "spec_id": "P12_libWlanResource_fatal_guard",
                    "library_name": "libWlanResource.so",
                    "sites": (mock.Mock(site_id="p12_wlan", size=8),),
                },
            )()

            def _fake_subproc_run(cmd, **_kw):
                out_path = pathlib.Path(cmd[-1])
                out_path.write_bytes(b"ELF_VERIFY_15")
                return mock.Mock(returncode=0, stderr="")

            donor_u1 = tmp_dir / "donor_u1.uxc"
            donor_u2 = tmp_dir / "donor_u2.uxc"
            donor_ltt = tmp_dir / "donor_font.ltt"
            donor_uxc = tmp_dir / "donor_img.uxc"
            donor_u1.write_bytes(b"uxc\x07" + b"D1" * 16)
            donor_u2.write_bytes(b"uxc\x07" + b"D2" * 16)
            donor_ltt.write_bytes(b"LTT\n" + b"FD" * 16)
            donor_uxc.write_bytes(b"uxd\x07" + b"D" * 32)
            build_dir = tmp_dir / "build"

            with mock.patch.object(
                runner, "_import_stage_a_modules", return_value=(_FakePatcher, _FakeVfat, _FakeBmtv)
            ), mock.patch.object(
                runner, "_load_p10_keymap_spec", return_value=fake_p10
            ), mock.patch.object(
                runner, "_load_p12_wlan_spec", return_value=fake_p12
            ), mock.patch.object(
                runner, "DONOR_IMAGE_00_169_UXC", donor_uxc
            ), mock.patch.object(
                runner, donor_attr_u1, donor_u1
            ), mock.patch.object(
                runner, donor_attr_u2, donor_u2
            ), mock.patch.object(
                runner, donor_attr_ltt, donor_ltt
            ), mock.patch.object(
                runner, "FX3_UPM_KO", tmp_dir / "absent_upm.ko"
            ), mock.patch.object(
                runner, "FX3_SEED_BK4", tmp_dir / "absent_seed.bin"
            ), mock.patch.object(
                runner.subprocess, "run", side_effect=_fake_subproc_run
            ):
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
                    rep, add, meta = runner.build_stage_a_overlay(
                        build_dir,
                        parent_cpio,
                        b"BK4_NTSC",
                        enable_p10=True,
                        enable_r10=True,
                        enable_p12=True,
                        enable_r12=True,
                        enable_r13=True,
                        enable_r14=True,
                        enable_r15=True,
                        lang=lang,
                        shim_bytes=b"SHIM15",
                    )
                self.assertEqual(meta["manifest_count"], 13)
                self.assertTrue(meta["r14_enabled"])
                self.assertTrue(meta["r15_enabled"])
                self.assertEqual(meta["lang"], lang)
                self.assertIn("etc/fx6_stage_r15", add)
                self.assertIn(
                    f"statuscheck_multitab=1\nmonitoring_3layer=1\nlang={lang}\n".encode("utf-8"),
                    add["etc/fx6_stage_r15"][0],
                )
                self.assertEqual(meta["lang_assets"][asset_key_u1]["source"], "cpio_preloaded")
                self.assertEqual(meta["lang_assets"][asset_key_ltt]["source"], "cpio_preloaded")
                self.assertEqual(meta["lang_assets"]["fontlist_dat"]["fontlist_key"], fontlist_key)
                self.assertEqual(rep[f"usr/share/app/{uxc2_name}"], b"uxc\x07" + b"C2" * 16)

                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "0"}):
                    rep2, add2, meta2 = runner.build_stage_a_overlay(
                        build_dir,
                        parent_cpio,
                        b"BK4_NTSC",
                        enable_p10=True,
                        enable_r10=True,
                        enable_p12=True,
                        enable_r12=True,
                        enable_r13=True,
                        enable_r14=True,
                        enable_r15=True,
                        lang=lang,
                        shim_bytes=b"SHIM15",
                    )
                self.assertTrue(meta2["r15_enabled"])
                self.assertIn("etc/fx6_stage_r15", add2)
                self.assertEqual(meta2["lang_assets"][asset_key_u1]["source"], "donor_o_rdonly")
                self.assertEqual(rep2[f"usr/share/app/{ltt_name}"], b"LTT\n" + b"FD" * 16)

    def test_round15_stage_a_overlay_schinese_dual_mode(self) -> None:
        self._assert_r15_overlay_dual_mode(
            lang="schinese",
            uxc1_name="string_simplifiedchinese.uxc",
            uxc2_name="string_simplifiedchinese_2.uxc",
            ltt_name="MYingHeiC-GB18030-SJ_wIcon.ltt",
            fontlist_key="FONT_S_CHINESE",
            asset_key_u1="string_simplifiedchinese",
            asset_key_ltt="font_gb18030_ltt",
            donor_attr_u1="DONOR_STRING_SCHINESE_UXC",
            donor_attr_u2="DONOR_STRING_SCHINESE_2_UXC",
            donor_attr_ltt="DONOR_FONT_SCHINESE_LTT",
        )

    def test_round15_stage_a_overlay_japanese_dual_mode(self) -> None:
        self._assert_r15_overlay_dual_mode(
            lang="japanese",
            uxc1_name="string_japanese.uxc",
            uxc2_name="string_japanese_2.uxc",
            ltt_name="HeiseiKakuGothW5-SJ_wIcon.ltt",
            fontlist_key="FONT_JAPANESE",
            asset_key_u1="string_japanese",
            asset_key_ltt="font_japanese_ltt",
            donor_attr_u1="DONOR_STRING_JAPANESE_UXC",
            donor_attr_u2="DONOR_STRING_JAPANESE_2_UXC",
            donor_attr_ltt="DONOR_FONT_JAPANESE_LTT",
        )

    def test_round15_extract_milestones_telemetry_parser(self) -> None:
        runner = _load_closure_module(
            "fx6_build_and_run_round_r15_ms", "build_and_run_round.py"
        )
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_STAGE_B_R15_VERIFY_PASS count=13 stage_b=1 p10_keymap=1 p11_uipc=1 p12_wlan=1 p4_nd_clear=1 uxc=1 statuscheck_multitab=1 monitoring_3layer=1 lang=schinese",
                "FX6_STAGE_B_R15_BRIDGE round=15 faithful=1 nop_count=0 p12_wlan=1 p10_keymap=1 p4_nd_clear=1 p11_xlr_h1=1 lang=schinese bk4_lang=0x19 enum=0x2b45_CHINESE_SIMPLIFIED font_bank=23 str_bank=19 multitab_status_monitoring=1",
                "FX6_R15_LANG_TELEMETRY reason=pump lang=schinese bk4_lang_id=0x02cf019c bk4_lang_val=0x19 lang_enum=0x2b45_CHINESE_SIMPLIFIED font_bank=23 str_bank=19 lang_bk4_hits=3 airplane_bk4_hits=0 p4_nd_clear=1 p10_keymap=1 p11_xlr_h1=1 p12_wlan=1 font_create=19534 glyph_blits=9204 icon_blits=7501 gpe_alloc=144 gpe_fb=0 statuscheck_multitab=1 monitoring_3layer=1 subst_color=0 subst_image=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        self.assertEqual(ms["prefix_counts"]["FX6_R15_"], 1)
        r15 = ms["r15_telemetry"]
        self.assertIsNotNone(r15)
        self.assertEqual(r15["lang"], "schinese")
        self.assertEqual(r15["bk4_lang_val"], "0x19")
        self.assertEqual(r15["font_bank"], 23)
        self.assertEqual(r15["str_bank"], 19)
        self.assertEqual(r15["gpe_alloc"], 144)
        self.assertEqual(r15["gpe_fb"], 0)
        self.assertEqual(r15["statuscheck_multitab"], 1)
        self.assertEqual(r15["monitoring_3layer"], 1)
        self.assertEqual(r15["subst_color"], 0)
        self.assertEqual(r15["subst_image"], 0)

    def test_round15_report_and_summary_json_invariants(self) -> None:
        self.assertTrue((ROUND15_REPORT_DIR / "README.md").is_file())
        summary_path = ROUND15_REPORT_DIR / "summary.json"
        self.assertTrue(summary_path.is_file())
        raw_text = summary_path.read_text(encoding="utf-8")
        for forbidden in ("/Volumes/KAFU2T", "/private/tmp", "/Users/"):
            self.assertNotIn(forbidden, raw_text)
        data = json.loads(raw_text)
        self.assertEqual(data["schema"], "fx6-on-fx3-round15-multitab-status-monitoring-v1")
        self.assertIn("Linux version 4.9.337-scel+", data["kernel_version"])
        self.assertEqual(set(data["languages"].keys()), {"en", "tchinese", "japanese", "schinese"})

        runs = data["runs"]
        self.assertEqual(set(runs.keys()), set(self.EXPECTED_RUN_KEYS))
        expectations = {
            "r15a_status_tab2_schinese": (
                "schinese", "0x30", "36procam_touch_status_camera_presenter", "0x19", 23, 19, 437883, 80, 260,
            ),
            "r15b_status_tab3_schinese": (
                "schinese", "0x31", "35procam_touch_status_audio_presenter", "0x19", 23, 19, 437883, 114, 404,
            ),
            "r15c_menu_3layer_monitoring_schinese": (
                "schinese", "0x11", "31procam_menu_layer_3rd_presenter", "0x19", 23, 19, 437095, 218, 232,
            ),
            "r15d_status_tab2_japanese": (
                "japanese", "0x30", "36procam_touch_status_camera_presenter", "0x01", 1, 12, 437883, 80, 260,
            ),
        }
        for key, (lang, sid, presenter, bk4_val, font_b, str_b, exp_px, exp_col, exp_amber) in expectations.items():
            run = runs[key]
            self.assertEqual(run["round"], 15)
            self.assertEqual(run["lang"], lang)
            self.assertEqual(run["target_sid"], sid)
            self.assertEqual(run["target_presenter"], presenter)
            self.assertEqual(run["nop_count"], 0)
            self.assertEqual(run["crashes"], 0)
            self.assertGreater(run["ldec103_ioctl_count"], 40)
            self.assertGreaterEqual(run["total_threads_seen"], 161)
            self.assertEqual(
                run["faithful_invariants"],
                {
                    "FX6_NATIVE_FAITHFUL": 1,
                    "subst_color": 0,
                    "subst_image": 0,
                    "forced_render": 0,
                    "skipped_node": 0,
                    "lock_bypass": 0,
                },
            )
            sb = run["stage_b"]
            self.assertTrue(sb["r14_enabled"])
            self.assertTrue(sb["r15_enabled"])
            self.assertEqual(sb["manifest_count"], 13)
            markers = "\n".join(sb["guest_boot_markers"])
            self.assertIn("FX6_STAGE_A_VERIFY_PASS count=13", markers)
            self.assertIn(
                f"FX6_STAGE_B_R15_VERIFY_PASS count=13 stage_b=1 p10_keymap=1 p11_uipc=1 p12_wlan=1 p4_nd_clear=1 uxc=1 statuscheck_multitab=1 monitoring_3layer=1 lang={lang}",
                markers,
            )
            self.assertIn("FX6_STAGE_B_R15_BRIDGE round=15 faithful=1 nop_count=0", markers)
            self.assertIn("FX6_STAGE_B_P4_ND_CLEAR_CHECK ok=1 nd_mode=0xd503201f nd_val=0x1400001b", markers)
            telem = run["r15_telemetry"]
            self.assertEqual(telem["lang"], lang)
            self.assertEqual(telem["bk4_lang_val"], bk4_val)
            self.assertEqual(telem["font_bank"], font_b)
            self.assertEqual(telem["str_bank"], str_b)
            self.assertEqual(telem["airplane_bk4_hits"], 0)
            self.assertEqual(telem["p12_wlan"], 1)
            self.assertEqual(telem["gpe_fb"], 0)
            self.assertEqual(telem["statuscheck_multitab"], 1)
            self.assertEqual(telem["monitoring_3layer"], 1)
            self.assertEqual(telem["subst_color"], 0)
            self.assertEqual(telem["subst_image"], 0)
            self.assertEqual(run["gpe0_readback"]["nonzero_pixels"], exp_px)
            self.assertEqual(run["gpe0_readback"]["unique_colors"], exp_col)
            self.assertEqual(run["amber_0xffffaa00_pixels"], exp_amber)

    def test_round15_stage_b_manifest_13_sha256_integrity(self) -> None:
        data = json.loads((ROUND15_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        shared_by_path: Dict[str, str] = {}
        for key in self.EXPECTED_RUN_KEYS:
            items = data["runs"][key]["stage_b"]["manifest_items"]
            self.assertEqual(len(items), 13)
            for item in items:
                gpath = item["guest_path"]
                digest = item["sha256"]
                self.assertEqual(len(digest), 64)
                int(digest, 16)
                if gpath == "/usr/lib/libgrm-fbinit9.so":
                    continue
                if gpath in shared_by_path:
                    self.assertEqual(shared_by_path[gpath], digest, f"SHA mismatch on {gpath}")
                else:
                    shared_by_path[gpath] = digest
        self.assertEqual(len(shared_by_path), 12)

    @staticmethod
    def _diff_rows(ra: List[bytes], rb: List[bytes]) -> int:
        import operator
        ne = operator.ne
        return sum(
            sum(map(ne, memoryview(ya).cast("I"), memoryview(yb).cast("I")))
            for ya, yb in zip(ra, rb)
            if ya != yb
        )

    @staticmethod
    def _count_amber(rows: List[bytes]) -> int:
        amber_word = int.from_bytes(b"\xff\xaa\x00\xff", sys.byteorder)
        return sum(
            sum(1 for px in memoryview(row).cast("I") if px == amber_word)
            for row in rows
            if b"\xff\xaa\x00\xff" in row
        )

    def test_round15_multitab_statuscheck_pairwise_pixel_deltas_exact(self) -> None:
        data = json.loads((ROUND15_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        mt = data["r15_multitab_and_category_audit"]["status_check_multitab_stepping_schinese"]
        self.assertTrue(mt["all_3_tab_pairs_strictly_positive"])

        p13a = ROUND13_ASSETS_DIR / "r13a-status-check-schinese-alpha.png"
        p15a = ROUND15_ASSETS_DIR / "r15a-status-tab2-schinese-alpha.png"
        p15b = ROUND15_ASSETS_DIR / "r15b-status-tab3-schinese-alpha.png"
        rows = {
            "tab1": _decode_png_rgba_rows(p13a.read_bytes())[2],
            "tab2": _decode_png_rgba_rows(p15a.read_bytes())[2],
            "tab3": _decode_png_rgba_rows(p15b.read_bytes())[2],
        }
        for key_name, a_key, b_key, exp_diff in (
            ("tab1_vs_tab2", "tab1", "tab2", 69094),
            ("tab2_vs_tab3", "tab2", "tab3", 125103),
            ("tab1_vs_tab3", "tab1", "tab3", 130085),
        ):
            self.assertEqual(mt[key_name]["diff_pixels"], exp_diff)
            self.assertTrue(mt[key_name]["strictly_positive"])
            diff = self._diff_rows(rows[a_key], rows[b_key])
            self.assertGreater(diff, 0)
            self.assertEqual(diff, exp_diff)

    def test_round15_monitoring_3layer_category_pixel_deltas_exact(self) -> None:
        data = json.loads((ROUND15_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        cat = data["r15_multitab_and_category_audit"]["menu_3layer_category_navigation_schinese"]
        self.assertTrue(cat["all_category_deltas_strictly_positive"])

        p11d = ROUND11_ASSETS_DIR / "r11d-c2-menu-3layer-schinese-alpha.png"
        p13c = ROUND13_ASSETS_DIR / "r13c-menu-3layer-paintlook-schinese-alpha.png"
        p15c = ROUND15_ASSETS_DIR / "r15c-menu-3layer-monitoring-schinese-alpha.png"
        rows_15c = _decode_png_rgba_rows(p15c.read_bytes())[2]
        for entry_key, other_path, exp_diff in (
            ("monitoring_vs_shooting_r11d", p11d, 124819),
            ("monitoring_vs_paintlook_r13c", p13c, 31140),
        ):
            self.assertEqual(cat[entry_key]["diff_pixels"], exp_diff)
            self.assertTrue(cat[entry_key]["strictly_positive"])
            rows_other = _decode_png_rgba_rows(other_path.read_bytes())[2]
            diff = self._diff_rows(rows_15c, rows_other)
            self.assertGreater(diff, 0)
            self.assertEqual(diff, exp_diff)

    def test_round15_cjk_cross_engine_tab2_pixel_deltas_exact(self) -> None:
        data = json.loads((ROUND15_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        cjk = data["r15_multitab_and_category_audit"]["cjk_cross_engine_tab2_audit"]

        p14a = ROUND14_ASSETS_DIR / "r14a-status-check-japanese-alpha.png"
        p15a = ROUND15_ASSETS_DIR / "r15a-status-tab2-schinese-alpha.png"
        p15d = ROUND15_ASSETS_DIR / "r15d-status-tab2-japanese-alpha.png"
        rows_15d = _decode_png_rgba_rows(p15d.read_bytes())[2]
        for entry_key, other_path, exp_diff in (
            ("japanese_tab1_vs_tab2", p14a, 62815),
            ("schinese_tab2_vs_japanese_tab2", p15a, 33462),
        ):
            self.assertEqual(cjk[entry_key]["diff_pixels"], exp_diff)
            self.assertTrue(cjk[entry_key]["strictly_positive"])
            rows_other = _decode_png_rgba_rows(other_path.read_bytes())[2]
            diff = self._diff_rows(rows_15d, rows_other)
            self.assertGreater(diff, 0)
            self.assertEqual(diff, exp_diff)

    def test_round15_png_receipts_valid_under_85kib_and_amber(self) -> None:
        self.assertTrue(ROUND15_ASSETS_DIR.is_dir())
        alpha_digests: Dict[str, str] = {}
        comp_digests: Dict[str, str] = {}
        for stem in self.EXPECTED_STEMS:
            for variant, bucket in (("alpha", alpha_digests), ("composited", comp_digests)):
                png_path = ROUND15_ASSETS_DIR / f"{stem}-{variant}.png"
                self.assertTrue(png_path.is_file(), f"Missing Round 15 PNG: {png_path}")
                raw = png_path.read_bytes()
                self.assertLess(len(raw), 85 * 1024, f"PNG exceeds 85 KiB: {png_path}")
                w, h, _ = _parse_and_validate_png(raw)
                self.assertEqual((w, h), (1024, 540))
                bucket[stem] = hashlib.sha256(raw).hexdigest()
        self.assertEqual(len(set(alpha_digests.values())), len(self.EXPECTED_STEMS))
        self.assertEqual(len(set(comp_digests.values())), len(self.EXPECTED_STEMS))

        for stem, exp_amber in (
            ("r15a-status-tab2-schinese", 260),
            ("r15b-status-tab3-schinese", 404),
            ("r15c-menu-3layer-monitoring-schinese", 232),
            ("r15d-status-tab2-japanese", 260),
        ):
            _, _, rows = _decode_png_rgba_rows((ROUND15_ASSETS_DIR / f"{stem}-alpha.png").read_bytes())
            self.assertEqual(self._count_amber(rows), exp_amber)

    def test_round15_readme_and_no_tmp_scratch_residue(self) -> None:
        closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn("2026-11-14-round15-fx6-on-fx3-multitab-status-monitoring", closure_readme)
        r15_readme = (ROUND15_REPORT_DIR / "README.md").read_text(encoding="utf-8")
        for tok in ("0x2f", "0x30", "0x31", "0x11", "Monitoring"):
            self.assertIn(tok, r15_readme)
        for forbidden in ("/Volumes/KAFU2T", "/Users/"):
            self.assertNotIn(forbidden, r15_readme)
        tmp_matches = list(pathlib.Path("/private/tmp").glob("fx6-r15*"))
        self.assertEqual(tmp_matches, [], f"Leftover scratch dirs in /private/tmp: {tmp_matches}")


class TestRound16StatusTabs45AndTcMedia(unittest.TestCase):
    """Round 16 dual-mode contracts: FX3 7.02 Status Check Tabs 4&5 + TChinese TC/Media & Japanese Monitoring."""

    EXPECTED_RUN_KEYS = (
        "r16a_status_tab4_schinese",
        "r16b_status_tab5_schinese",
        "r16c_menu_3layer_tcmedia_tchinese",
        "r16d_menu_3layer_monitoring_japanese",
    )
    EXPECTED_STEMS = (
        "r16a-status-tab4-schinese",
        "r16b-status-tab5-schinese",
        "r16c-menu-3layer-tcmedia-tchinese",
        "r16d-menu-3layer-monitoring-japanese",
    )

    def test_round16_c_and_runner_contracts(self) -> None:
        shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")

        for token in (
            "FX6_R16_LANG_TELEMETRY",
            "FX6_STAGE_B_R16_BRIDGE",
            "statuscheck_tabs45=1",
            "tcmedia_3layer=1",
        ):
            self.assertIn(token, shim_src)

        for token in (
            "/etc/fx6_stage_r16",
            "FX6_STAGE_B_R16_VERIFY_PASS",
            "statuscheck_tabs45=1",
            "tcmedia_3layer=1",
        ):
            self.assertIn(token, verify_src)

        for token in (
            "enable_r16",
            "etc/fx6_stage_r16",
            '"r16_telemetry"',
            '"fx6-r16"',
            "choices=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]",
        ):
            self.assertIn(token, runner_src)

    def _assert_r16_overlay_dual_mode(
        self,
        lang: str,
        uxc1_name: str,
        uxc2_name: str,
        ltt_name: str,
        fontlist_key: str,
        asset_key_u1: str,
        asset_key_ltt: str,
        donor_attr_u1: str,
        donor_attr_u2: str,
        donor_attr_ltt: str,
    ) -> None:
        runner = _load_closure_module(
            f"fx6_build_and_run_round_r16_ovl_{lang}", "build_and_run_round.py"
        )
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            parent_cpio = tmp_dir / "parent.cpio"
            init_body = (
                b"#!/bin/sh\n"
                b'LD_PRELOAD="$FX6_PRELOAD" /usr/bin/appfw-launch\n'
            )
            members = (
                ("init", init_body),
                ("usr/lib/libInfraSetupFile.so", b"SETUP"),
                ("usr/lib/libInfraMediaCommon.so", b"MCOMM"),
                ("usr/lib/libInfraMediaConfig.so", b"MCFG"),
                ("usr/lib/libInfraAppRemoteBoard.so", b"RBRD"),
                ("usr/lib/libfan.so", b"FAN"),
                ("usr/lib/appFw.so", b"APPFW"),
                ("usr/lib/libWlanResource.so", b"WLAN_DONOR_12345"),
                ("usr/kmod/upm.ko", b"UPMKO"),
                ("usr/share/app/image_00_169.uxc", b"uxd\x07" + b"C" * 32),
                (f"usr/share/app/{uxc1_name}", b"uxc\x07" + b"C1" * 16),
                (f"usr/share/app/{uxc2_name}", b"uxc\x07" + b"C2" * 16),
                (f"usr/share/app/{ltt_name}", b"LTT\n" + b"CL" * 16),
                (
                    "usr/share/app/fontlist.dat",
                    f"{fontlist_key}\t/usr/share/app/{ltt_name}\t0\t0\n".encode("ascii"),
                ),
            )
            archive = b"".join(
                runner.make_cpio_member(name, body, ino=idx + 1, mode=0o100755)
                for idx, (name, body) in enumerate(members)
            ) + runner.make_cpio_member("TRAILER!!!", b"", ino=0, mode=0)
            parent_cpio.write_bytes(archive)

            class _FakeRes:
                def __init__(self, site_id: str) -> None:
                    self.site_id = site_id

            class _FakeReceipt:
                def __init__(self, before: bytes, after: bytes, sites: list) -> None:
                    self.before_sha256 = hashlib.sha256(before).hexdigest()
                    self.after_sha256 = hashlib.sha256(after).hexdigest()
                    self.changed_byte_count = 8
                    self.resolutions = [_FakeRes(s.site_id) for s in sites]

            class _FakePatcher:
                P1_P4_P8_APPFW_COMBINED_SPEC = mock.Mock(
                    library_name="appFw.so",
                    expected_size=5,
                    donor_sha256="0" * 64,
                    sites=(mock.Mock(site_id="p1"),),
                    elf_kind="so",
                    source_domain="fx6",
                )
                P1_LIB_INFRA_SETUP_FILE_SPEC = mock.Mock(spec_id="P1_s", library_name="s", sites=[mock.Mock(site_id="s1")])
                P1_LIB_INFRA_MEDIA_COMMON_SPEC = mock.Mock(spec_id="P1_c", library_name="c", sites=[mock.Mock(site_id="c1")])
                P1_LIB_INFRA_MEDIA_CONFIG_SPEC = mock.Mock(spec_id="P1_g", library_name="g", sites=[mock.Mock(site_id="g1")])
                P3_LIB_INFRA_APP_REMOTE_BOARD_SPEC = mock.Mock(spec_id="P3_r", library_name="r", sites=[mock.Mock(site_id="r1")])
                FAN_LIBFAN_SPEC = mock.Mock(spec_id="Fan_f", library_name="f", sites=[mock.Mock(site_id="f1")])
                P9_UPM_KO_SPEC = mock.Mock(spec_id="P9_u", library_name="upm.ko", sites=[mock.Mock(site_id="u1")])
                LibraryPatchSpec = lambda **kw: type("FakeSpec", (), kw)()
                PatchSiteSpec = object
                PF_R = 4

                @staticmethod
                def apply_patch_spec(data: bytes, spec: object, verify_donor_sha256: bool = True):
                    after = data + b"_P"
                    return after, _FakeReceipt(data, after, getattr(spec, "sites", []))

                @staticmethod
                def resolve_and_verify_sites(data: bytes, spec: object, expect_patched_state: bool = True):
                    return [_FakeRes("u1")]

            class _FakeVfat:
                @staticmethod
                def build_opelog_vfat_image(mode: str):
                    img = b"VFAT" * 16
                    receipt = mock.Mock(
                        mode=mode,
                        fat_type="FAT16",
                        total_bytes=len(img),
                        sha256=hashlib.sha256(img).hexdigest(),
                        precreated_dirs=("OPE", "OPE/00", "OPE/01"),
                    )
                    return img, receipt

                @staticmethod
                def verify_vfat_image(_img: bytes):
                    return mock.Mock(valid=True, errors=[])

            class _FakeBmtv:
                @staticmethod
                def build_canonical_fa0080_normal_boot_table(donor_seed_bk4_path=None):
                    return b"T"

                @staticmethod
                def synthesize_ram_shadow_bk4(**_kw):
                    bk = b"BK4\x00" + b"\x00" * 12
                    return mock.Mock(
                        bk4_bytes=bk,
                        total_bytes=len(bk),
                        sha256=hashlib.sha256(bk).hexdigest(),
                        flash_write_allowed=False,
                        active_byte8_selector=0,
                        synthesized_key_count=1,
                    )

            fake_p10 = type(
                "FakeP10",
                (),
                {
                    "spec_id": "P10_FX3_TO_FX6_KEYMAP_ADAPTER",
                    "library_name": "appFw.so",
                    "sites": (mock.Mock(site_id="p10_fn", size=4),),
                },
            )()
            fake_p12 = type(
                "FakeP12",
                (),
                {
                    "spec_id": "P12_libWlanResource_fatal_guard",
                    "library_name": "libWlanResource.so",
                    "sites": (mock.Mock(site_id="p12_wlan", size=8),),
                },
            )()

            def _fake_subproc_run(cmd, **_kw):
                out_path = pathlib.Path(cmd[-1])
                out_path.write_bytes(b"ELF_VERIFY_16")
                return mock.Mock(returncode=0, stderr="")

            donor_u1 = tmp_dir / "donor_u1.uxc"
            donor_u2 = tmp_dir / "donor_u2.uxc"
            donor_ltt = tmp_dir / "donor_font.ltt"
            donor_uxc = tmp_dir / "donor_img.uxc"
            donor_u1.write_bytes(b"uxc\x07" + b"D1" * 16)
            donor_u2.write_bytes(b"uxc\x07" + b"D2" * 16)
            donor_ltt.write_bytes(b"LTT\n" + b"FD" * 16)
            donor_uxc.write_bytes(b"uxd\x07" + b"D" * 32)
            build_dir = tmp_dir / "build"

            with mock.patch.object(
                runner, "_import_stage_a_modules", return_value=(_FakePatcher, _FakeVfat, _FakeBmtv)
            ), mock.patch.object(
                runner, "_load_p10_keymap_spec", return_value=fake_p10
            ), mock.patch.object(
                runner, "_load_p12_wlan_spec", return_value=fake_p12
            ), mock.patch.object(
                runner, "DONOR_IMAGE_00_169_UXC", donor_uxc
            ), mock.patch.object(
                runner, donor_attr_u1, donor_u1
            ), mock.patch.object(
                runner, donor_attr_u2, donor_u2
            ), mock.patch.object(
                runner, donor_attr_ltt, donor_ltt
            ), mock.patch.object(
                runner, "FX3_UPM_KO", tmp_dir / "absent_upm.ko"
            ), mock.patch.object(
                runner, "FX3_SEED_BK4", tmp_dir / "absent_seed.bin"
            ), mock.patch.object(
                runner.subprocess, "run", side_effect=_fake_subproc_run
            ):
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
                    rep, add, meta = runner.build_stage_a_overlay(
                        build_dir,
                        parent_cpio,
                        b"BK4_NTSC",
                        enable_p10=True,
                        enable_r10=True,
                        enable_p12=True,
                        enable_r12=True,
                        enable_r13=True,
                        enable_r14=True,
                        enable_r15=True,
                        enable_r16=True,
                        lang=lang,
                        shim_bytes=b"SHIM16",
                    )
                self.assertEqual(meta["manifest_count"], 13)
                self.assertTrue(meta["r15_enabled"])
                self.assertTrue(meta["r16_enabled"])
                self.assertEqual(meta["lang"], lang)
                self.assertIn("etc/fx6_stage_r16", add)
                self.assertIn(
                    f"statuscheck_tabs45=1\ntcmedia_3layer=1\nlang={lang}\n".encode("utf-8"),
                    add["etc/fx6_stage_r16"][0],
                )
                self.assertEqual(meta["lang_assets"][asset_key_u1]["source"], "cpio_preloaded")
                self.assertEqual(meta["lang_assets"][asset_key_ltt]["source"], "cpio_preloaded")
                self.assertEqual(meta["lang_assets"]["fontlist_dat"]["fontlist_key"], fontlist_key)
                self.assertEqual(rep[f"usr/share/app/{uxc2_name}"], b"uxc\x07" + b"C2" * 16)

                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "0"}):
                    rep2, add2, meta2 = runner.build_stage_a_overlay(
                        build_dir,
                        parent_cpio,
                        b"BK4_NTSC",
                        enable_p10=True,
                        enable_r10=True,
                        enable_p12=True,
                        enable_r12=True,
                        enable_r13=True,
                        enable_r14=True,
                        enable_r15=True,
                        enable_r16=True,
                        lang=lang,
                        shim_bytes=b"SHIM16",
                    )
                self.assertTrue(meta2["r16_enabled"])
                self.assertIn("etc/fx6_stage_r16", add2)
                self.assertEqual(meta2["lang_assets"][asset_key_u1]["source"], "donor_o_rdonly")
                self.assertEqual(rep2[f"usr/share/app/{ltt_name}"], b"LTT\n" + b"FD" * 16)

    def test_round16_stage_a_overlay_tchinese_dual_mode(self) -> None:
        self._assert_r16_overlay_dual_mode(
            lang="tchinese",
            uxc1_name="string_traditionalchinese.uxc",
            uxc2_name="string_traditionalchinese_2.uxc",
            ltt_name="MYingHeiC-Big5HKSCS-SJ_wIcon.ltt",
            fontlist_key="FONT_T_CHINESE",
            asset_key_u1="string_traditionalchinese",
            asset_key_ltt="font_big5hkscs_ltt",
            donor_attr_u1="DONOR_STRING_TCHINESE_UXC",
            donor_attr_u2="DONOR_STRING_TCHINESE_2_UXC",
            donor_attr_ltt="DONOR_FONT_TCHINESE_LTT",
        )

    def test_round16_stage_a_overlay_schinese_dual_mode(self) -> None:
        self._assert_r16_overlay_dual_mode(
            lang="schinese",
            uxc1_name="string_simplifiedchinese.uxc",
            uxc2_name="string_simplifiedchinese_2.uxc",
            ltt_name="MYingHeiC-GB18030-SJ_wIcon.ltt",
            fontlist_key="FONT_S_CHINESE",
            asset_key_u1="string_simplifiedchinese",
            asset_key_ltt="font_gb18030_ltt",
            donor_attr_u1="DONOR_STRING_SCHINESE_UXC",
            donor_attr_u2="DONOR_STRING_SCHINESE_2_UXC",
            donor_attr_ltt="DONOR_FONT_SCHINESE_LTT",
        )

    def test_round16_stage_a_overlay_japanese_dual_mode(self) -> None:
        self._assert_r16_overlay_dual_mode(
            lang="japanese",
            uxc1_name="string_japanese.uxc",
            uxc2_name="string_japanese_2.uxc",
            ltt_name="HeiseiKakuGothW5-SJ_wIcon.ltt",
            fontlist_key="FONT_JAPANESE",
            asset_key_u1="string_japanese",
            asset_key_ltt="font_japanese_ltt",
            donor_attr_u1="DONOR_STRING_JAPANESE_UXC",
            donor_attr_u2="DONOR_STRING_JAPANESE_2_UXC",
            donor_attr_ltt="DONOR_FONT_JAPANESE_LTT",
        )

    def test_round16_extract_milestones_telemetry_parser(self) -> None:
        runner = _load_closure_module(
            "fx6_build_and_run_round_r16_ms", "build_and_run_round.py"
        )
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_STAGE_B_R16_VERIFY_PASS count=13 stage_b=1 p10_keymap=1 p11_uipc=1 p12_wlan=1 p4_nd_clear=1 uxc=1 statuscheck_tabs45=1 tcmedia_3layer=1 lang=tchinese",
                "FX6_STAGE_B_R16_BRIDGE round=16 faithful=1 nop_count=0 p12_wlan=1 p10_keymap=1 p4_nd_clear=1 p11_xlr_h1=1 lang=tchinese bk4_lang=0x18 enum=0x2b44_LANGUAGE_CHINESE_TRADITIONAL font_bank=27 str_bank=22 statuscheck_tabs45=1 tcmedia_3layer=1",
                "FX6_R16_LANG_TELEMETRY reason=pump lang=tchinese bk4_lang_id=0x02cf019c bk4_lang_val=0x18 lang_enum=0x2b44_LANGUAGE_CHINESE_TRADITIONAL font_bank=27 str_bank=22 lang_bk4_hits=3 airplane_bk4_hits=0 p4_nd_clear=1 p10_keymap=1 p11_xlr_h1=1 p12_wlan=1 font_create=21422 glyph_blits=13499 icon_blits=14622 gpe_alloc=181 gpe_fb=0 statuscheck_tabs45=1 tcmedia_3layer=1 subst_color=0 subst_image=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        self.assertEqual(ms["prefix_counts"]["FX6_R16_"], 1)
        r16 = ms["r16_telemetry"]
        self.assertIsNotNone(r16)
        self.assertEqual(r16["lang"], "tchinese")
        self.assertEqual(r16["bk4_lang_val"], "0x18")
        self.assertEqual(r16["font_bank"], 27)
        self.assertEqual(r16["str_bank"], 22)
        self.assertEqual(r16["gpe_alloc"], 181)
        self.assertEqual(r16["gpe_fb"], 0)
        self.assertEqual(r16["statuscheck_tabs45"], 1)
        self.assertEqual(r16["tcmedia_3layer"], 1)
        self.assertEqual(r16["subst_color"], 0)
        self.assertEqual(r16["subst_image"], 0)

    def test_round16_report_and_summary_json_invariants(self) -> None:
        self.assertTrue((ROUND16_REPORT_DIR / "README.md").is_file())
        summary_path = ROUND16_REPORT_DIR / "summary.json"
        self.assertTrue(summary_path.is_file())
        raw_text = summary_path.read_text(encoding="utf-8")
        for forbidden in ("/Volumes/KAFU2T", "/private/tmp", "/Users/"):
            self.assertNotIn(forbidden, raw_text)
        data = json.loads(raw_text)
        self.assertEqual(data["schema"], "fx6-on-fx3-round16-status-tabs45-tcmedia-v1")
        self.assertIn("Linux version 4.9.337-scel+", data["kernel_version"])
        self.assertEqual(set(data["languages"].keys()), {"en", "tchinese", "japanese", "schinese"})
        self.assertEqual(len(data["status_check_multitab_contract"]["tabs_verified"]), 5)

        runs = data["runs"]
        self.assertEqual(set(runs.keys()), set(self.EXPECTED_RUN_KEYS))
        expectations = {
            "r16a_status_tab4_schinese": (
                "schinese", "0x32", "37procam_touch_status_project_presenter", "0x19", 23, 19, 437403, 85, 270,
            ),
            "r16b_status_tab5_schinese": (
                "schinese", "0x33", "40procam_touch_status_monitoring_presenter", "0x19", 23, 19, 437883, 106, 266,
            ),
            "r16c_menu_3layer_tcmedia_tchinese": (
                "tchinese", "0x11", "31procam_menu_layer_3rd_presenter", "0x18", 27, 22, 437095, 250, 2440,
            ),
            "r16d_menu_3layer_monitoring_japanese": (
                "japanese", "0x11", "31procam_menu_layer_3rd_presenter", "0x01", 1, 12, 437575, 220, 209,
            ),
        }
        for key, (lang, sid, presenter, bk4_val, font_b, str_b, exp_px, exp_col, exp_amber) in expectations.items():
            run = runs[key]
            self.assertEqual(run["round"], 16)
            self.assertEqual(run["lang"], lang)
            self.assertEqual(run["target_sid"], sid)
            self.assertEqual(run["target_presenter"], presenter)
            self.assertEqual(run["nop_count"], 0)
            self.assertEqual(run["crashes"], 0)
            self.assertGreater(run["ldec103_ioctl_count"], 45)
            self.assertGreaterEqual(run["total_threads_seen"], 161)
            self.assertEqual(
                run["faithful_invariants"],
                {
                    "FX6_NATIVE_FAITHFUL": 1,
                    "subst_color": 0,
                    "subst_image": 0,
                    "forced_render": 0,
                    "skipped_node": 0,
                    "lock_bypass": 0,
                },
            )
            sb = run["stage_b"]
            self.assertTrue(sb["r15_enabled"])
            self.assertTrue(sb["r16_enabled"])
            self.assertEqual(sb["lang"], lang)
            self.assertEqual(sb["manifest_count"], 13)
            self.assertEqual(len(sb["verify_bin_sha256"]), 64)
            self.assertIn("P12_libWlanResource_fatal_guard", sb["patches"])
            self.assertIn("P10_FX3_TO_FX6_KEYMAP_ADAPTER", sb["patches"])
            self.assertIn(
                "P4_appfw_set_nd_filter_mode_clear",
                sb["patches"]["P1_P4_P8_P10_appFw_combined"]["sites"],
            )
            self.assertGreaterEqual(run["prefix_counts"]["FX6_STAGE_A_"], 21)
            self.assertGreaterEqual(run["prefix_counts"]["FX6_STAGE_B_"], 24)
            self.assertGreaterEqual(run["prefix_counts"]["FX6_R16_"], 180)
            telem = run["r16_telemetry"]
            self.assertEqual(telem["p4_nd_clear"], 1)
            self.assertEqual(telem["p10_keymap"], 1)
            self.assertEqual(telem["p11_xlr_h1"], 1)
            self.assertEqual(telem["lang"], lang)
            self.assertEqual(telem["bk4_lang_val"], bk4_val)
            self.assertEqual(telem["font_bank"], font_b)
            self.assertEqual(telem["str_bank"], str_b)
            self.assertEqual(telem["airplane_bk4_hits"], 0)
            self.assertEqual(telem["p12_wlan"], 1)
            self.assertEqual(telem["gpe_fb"], 0)
            self.assertEqual(telem["statuscheck_tabs45"], 1)
            self.assertEqual(telem["tcmedia_3layer"], 1)
            self.assertEqual(telem["subst_color"], 0)
            self.assertEqual(telem["subst_image"], 0)
            self.assertEqual(run["gpe0_readback"]["nonzero_pixels"], exp_px)
            self.assertEqual(run["gpe0_readback"]["unique_colors"], exp_col)
            self.assertEqual(run["amber_0xffffaa00_pixels"], exp_amber)

    def test_round16_stage_b_manifest_13_sha256_integrity(self) -> None:
        data = json.loads((ROUND16_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        shared_by_path: Dict[str, str] = {}
        for key in self.EXPECTED_RUN_KEYS:
            items = data["runs"][key]["stage_b"]["manifest_items"]
            self.assertEqual(len(items), 13)
            for item in items:
                gpath = item["guest_path"]
                digest = item["sha256"]
                self.assertEqual(len(digest), 64)
                int(digest, 16)
                if gpath == "/usr/lib/libgrm-fbinit9.so":
                    continue
                if gpath in shared_by_path:
                    self.assertEqual(shared_by_path[gpath], digest, f"SHA mismatch on {gpath}")
                else:
                    shared_by_path[gpath] = digest
        self.assertEqual(len(shared_by_path), 12)

    @staticmethod
    def _diff_rows(ra: List[bytes], rb: List[bytes]) -> int:
        import operator
        ne = operator.ne
        return sum(
            sum(map(ne, memoryview(ya).cast("I"), memoryview(yb).cast("I")))
            for ya, yb in zip(ra, rb)
            if ya != yb
        )

    @staticmethod
    def _count_amber(rows: List[bytes]) -> int:
        amber_word = int.from_bytes(b"\xff\xaa\x00\xff", sys.byteorder)
        return sum(
            sum(1 for px in memoryview(row).cast("I") if px == amber_word)
            for row in rows
            if b"\xff\xaa\x00\xff" in row
        )

    def test_round16_statuscheck_5tabs_10pairs_pixel_deltas_exact(self) -> None:
        data = json.loads((ROUND16_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        audit = data["r16_status5_and_tcmedia_audit"]["status_check_5tab_pairwise_schinese"]
        self.assertEqual(audit["pair_count"], 10)
        self.assertTrue(audit["all_10_tab_pairs_strictly_positive"])

        rows = {
            "tab1": _decode_png_rgba_rows((ROUND13_ASSETS_DIR / "r13a-status-check-schinese-alpha.png").read_bytes())[2],
            "tab2": _decode_png_rgba_rows((ROUND15_ASSETS_DIR / "r15a-status-tab2-schinese-alpha.png").read_bytes())[2],
            "tab3": _decode_png_rgba_rows((ROUND15_ASSETS_DIR / "r15b-status-tab3-schinese-alpha.png").read_bytes())[2],
            "tab4": _decode_png_rgba_rows((ROUND16_ASSETS_DIR / "r16a-status-tab4-schinese-alpha.png").read_bytes())[2],
            "tab5": _decode_png_rgba_rows((ROUND16_ASSETS_DIR / "r16b-status-tab5-schinese-alpha.png").read_bytes())[2],
        }
        expected_pairs = (
            ("tab1_vs_tab2", "tab1", "tab2", 69094),
            ("tab1_vs_tab3", "tab1", "tab3", 130085),
            ("tab1_vs_tab4", "tab1", "tab4", 63255),
            ("tab1_vs_tab5", "tab1", "tab5", 87492),
            ("tab2_vs_tab3", "tab2", "tab3", 125103),
            ("tab2_vs_tab4", "tab2", "tab4", 60513),
            ("tab2_vs_tab5", "tab2", "tab5", 80436),
            ("tab3_vs_tab4", "tab3", "tab4", 128493),
            ("tab3_vs_tab5", "tab3", "tab5", 91456),
            ("tab4_vs_tab5", "tab4", "tab5", 87504),
        )
        for pair_key, a_key, b_key, exp_diff in expected_pairs:
            self.assertEqual(audit[pair_key]["diff_pixels"], exp_diff)
            self.assertTrue(audit[pair_key]["strictly_positive"])
            diff = self._diff_rows(rows[a_key], rows[b_key])
            self.assertGreater(diff, 0)
            self.assertEqual(diff, exp_diff)

    def test_round16_tcmedia_tchinese_and_monitoring_japanese_pixel_deltas_exact(self) -> None:
        data = json.loads((ROUND16_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        tc_audit = data["r16_status5_and_tcmedia_audit"]["menu_3layer_tcmedia_tchinese"]
        ja_audit = data["r16_status5_and_tcmedia_audit"]["menu_3layer_monitoring_japanese"]
        self.assertTrue(tc_audit["all_tchinese_deltas_strictly_positive"])
        self.assertTrue(ja_audit["all_japanese_deltas_strictly_positive"])

        rows_16c = _decode_png_rgba_rows((ROUND16_ASSETS_DIR / "r16c-menu-3layer-tcmedia-tchinese-alpha.png").read_bytes())[2]
        rows_16d = _decode_png_rgba_rows((ROUND16_ASSETS_DIR / "r16d-menu-3layer-monitoring-japanese-alpha.png").read_bytes())[2]
        rows_13b = _decode_png_rgba_rows((ROUND13_ASSETS_DIR / "r13b-menu-3layer-tchinese-alpha.png").read_bytes())[2]
        rows_15c = _decode_png_rgba_rows((ROUND15_ASSETS_DIR / "r15c-menu-3layer-monitoring-schinese-alpha.png").read_bytes())[2]
        rows_12d = _decode_png_rgba_rows((ROUND12_ASSETS_DIR / "r12d-c2-menu-3layer-japanese-alpha.png").read_bytes())[2]

        for entry, rows_a, rows_b, exp_diff in (
            (tc_audit["tcmedia_vs_shooting_r13b"], rows_16c, rows_13b, 35765),
            (tc_audit["tcmedia_vs_monitoring_r15c"], rows_16c, rows_15c, 19082),
            (ja_audit["monitoring_vs_shooting_r12d"], rows_16d, rows_12d, 24616),
            (ja_audit["monitoring_japanese_vs_schinese_r15c"], rows_16d, rows_15c, 8114),
            (ja_audit["monitoring_japanese_vs_tcmedia_tchinese_r16c"], rows_16d, rows_16c, 20779),
        ):
            self.assertEqual(entry["diff_pixels"], exp_diff)
            self.assertTrue(entry["strictly_positive"])
            diff = self._diff_rows(rows_a, rows_b)
            self.assertGreater(diff, 0)
            self.assertEqual(diff, exp_diff)

    def test_round16_png_receipts_valid_under_85kib_and_amber(self) -> None:
        self.assertTrue(ROUND16_ASSETS_DIR.is_dir())
        alpha_digests: Dict[str, str] = {}
        comp_digests: Dict[str, str] = {}
        for stem in self.EXPECTED_STEMS:
            for variant, bucket in (("alpha", alpha_digests), ("composited", comp_digests)):
                png_path = ROUND16_ASSETS_DIR / f"{stem}-{variant}.png"
                self.assertTrue(png_path.is_file(), f"Missing Round 16 PNG: {png_path}")
                raw = png_path.read_bytes()
                self.assertLess(len(raw), 85 * 1024, f"PNG exceeds 85 KiB: {png_path}")
                w, h, _ = _decode_png_rgba_rows(raw)
                self.assertEqual((w, h), (1024, 540))
                bucket[stem] = hashlib.sha256(raw).hexdigest()
        self.assertEqual(len(set(alpha_digests.values())), len(self.EXPECTED_STEMS))
        self.assertEqual(len(set(comp_digests.values())), len(self.EXPECTED_STEMS))

        for stem, exp_amber in (
            ("r16a-status-tab4-schinese", 270),
            ("r16b-status-tab5-schinese", 266),
            ("r16c-menu-3layer-tcmedia-tchinese", 2440),
            ("r16d-menu-3layer-monitoring-japanese", 209),
        ):
            _, _, rows = _decode_png_rgba_rows((ROUND16_ASSETS_DIR / f"{stem}-alpha.png").read_bytes())
            self.assertEqual(self._count_amber(rows), exp_amber)

    def test_round16_readme_and_no_tmp_scratch_residue(self) -> None:
        closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn("2026-11-14-round16-fx6-on-fx3-status-tabs45-tcmedia", closure_readme)
        r16_readme = (ROUND16_REPORT_DIR / "README.md").read_text(encoding="utf-8")
        for tok in ("0x32", "0x33", "0x11", "TC/Media", "Monitoring"):
            self.assertIn(tok, r16_readme)
        for forbidden in ("/Volumes/KAFU2T", "/Users/"):
            self.assertNotIn(forbidden, r16_readme)
        tmp_matches = list(pathlib.Path("/private/tmp").glob("fx6-r16*"))
        self.assertEqual(tmp_matches, [], f"Leftover scratch dirs in /private/tmp: {tmp_matches}")


class TestRound17StatusFullSweepAndAudio3Layer(unittest.TestCase):
    """Round 17 dual-mode contracts: FX3 7.02 Status Check Tabs 6-10 + Wrap-Around + Network WF-12 + Audio 3-Layer Menu."""

    EXPECTED_RUN_KEYS = (
        "r17a_status_tab6_schinese",
        "r17b_status_tab7_schinese",
        "r17c_status_tab8_schinese",
        "r17d_menu_3layer_audio_schinese",
        "r17e_status_tab9_network_schinese",
        "r17f_status_tab10_filetransfer_schinese",
        "r17g_status_wraparound_tab1_schinese",
    )
    EXPECTED_STEMS = (
        "r17a-status-tab6-schinese",
        "r17b-status-tab7-schinese",
        "r17c-status-tab8-schinese",
        "r17d-menu-3layer-audio-schinese",
        "r17e-status-tab9-network-schinese",
        "r17f-status-tab10-filetransfer-schinese",
        "r17g-status-wraparound-tab1-schinese",
    )

    def test_round17_c_and_runner_contracts(self) -> None:
        shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")

        for token in (
            "FX6_R17_LANG_TELEMETRY",
            "FX6_STAGE_B_R17_BRIDGE",
            "wf12_00342260_immune=1",
            "statuscheck_fullsweep=1",
            "audio_3layer=1",
        ):
            self.assertIn(token, shim_src)

        for token in (
            "/etc/fx6_stage_r17",
            "FX6_STAGE_B_R17_VERIFY_PASS",
            "statuscheck_fullsweep=1",
            "audio_3layer=1",
        ):
            self.assertIn(token, verify_src)

        for token in (
            "enable_r17",
            "etc/fx6_stage_r17",
            '"r17_telemetry"',
            '"fx6-r17"',
            "choices=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]",
        ):
            self.assertIn(token, runner_src)

    def _assert_r17_overlay_dual_mode(
        self,
        lang: str,
        uxc1_name: str,
        uxc2_name: str,
        ltt_name: str,
        fontlist_key: str,
        asset_key_u1: str,
        asset_key_ltt: str,
        donor_attr_u1: str,
        donor_attr_u2: str,
        donor_attr_ltt: str,
    ) -> None:
        runner = _load_closure_module(
            f"fx6_build_and_run_round_r17_ovl_{lang}", "build_and_run_round.py"
        )
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            parent_cpio = tmp_dir / "parent.cpio"
            init_body = (
                b"#!/bin/sh\n"
                b'LD_PRELOAD="$FX6_PRELOAD" /usr/bin/appfw-launch\n'
            )
            members = (
                ("init", init_body),
                ("usr/lib/libInfraSetupFile.so", b"SETUP"),
                ("usr/lib/libInfraMediaCommon.so", b"MCOMM"),
                ("usr/lib/libInfraMediaConfig.so", b"MCFG"),
                ("usr/lib/libInfraAppRemoteBoard.so", b"RBRD"),
                ("usr/lib/libfan.so", b"FAN"),
                ("usr/lib/appFw.so", b"APPFW"),
                ("usr/lib/libWlanResource.so", b"WLAN_DONOR_12345"),
                ("usr/kmod/upm.ko", b"UPMKO"),
                ("usr/share/app/image_00_169.uxc", b"uxd\x07" + b"C" * 32),
                (f"usr/share/app/{uxc1_name}", b"uxc\x07" + b"C1" * 16),
                (f"usr/share/app/{uxc2_name}", b"uxc\x07" + b"C2" * 16),
                (f"usr/share/app/{ltt_name}", b"LTT\n" + b"CL" * 16),
                (
                    "usr/share/app/fontlist.dat",
                    f"{fontlist_key}\t/usr/share/app/{ltt_name}\t0\t0\n".encode("ascii"),
                ),
            )
            archive = b"".join(
                runner.make_cpio_member(name, body, ino=idx + 1, mode=0o100755)
                for idx, (name, body) in enumerate(members)
            ) + runner.make_cpio_member("TRAILER!!!", b"", ino=0, mode=0)
            parent_cpio.write_bytes(archive)

            class _FakeRes:
                def __init__(self, site_id: str) -> None:
                    self.site_id = site_id

            class _FakeReceipt:
                def __init__(self, before: bytes, after: bytes, sites: list) -> None:
                    self.before_sha256 = hashlib.sha256(before).hexdigest()
                    self.after_sha256 = hashlib.sha256(after).hexdigest()
                    self.changed_byte_count = 8
                    self.resolutions = [_FakeRes(s.site_id) for s in sites]

            class _FakePatcher:
                P1_P4_P8_APPFW_COMBINED_SPEC = mock.Mock(
                    library_name="appFw.so",
                    expected_size=5,
                    donor_sha256="0" * 64,
                    sites=(mock.Mock(site_id="p1"),),
                    elf_kind="so",
                    source_domain="fx6",
                )
                P1_LIB_INFRA_SETUP_FILE_SPEC = mock.Mock(spec_id="P1_s", library_name="s", sites=[mock.Mock(site_id="s1")])
                P1_LIB_INFRA_MEDIA_COMMON_SPEC = mock.Mock(spec_id="P1_c", library_name="c", sites=[mock.Mock(site_id="c1")])
                P1_LIB_INFRA_MEDIA_CONFIG_SPEC = mock.Mock(spec_id="P1_g", library_name="g", sites=[mock.Mock(site_id="g1")])
                P3_LIB_INFRA_APP_REMOTE_BOARD_SPEC = mock.Mock(spec_id="P3_r", library_name="r", sites=[mock.Mock(site_id="r1")])
                FAN_LIBFAN_SPEC = mock.Mock(spec_id="Fan_f", library_name="f", sites=[mock.Mock(site_id="f1")])
                P9_UPM_KO_SPEC = mock.Mock(spec_id="P9_u", library_name="upm.ko", sites=[mock.Mock(site_id="u1")])
                LibraryPatchSpec = lambda **kw: type("FakeSpec", (), kw)()
                PatchSiteSpec = object
                PF_R = 4

                @staticmethod
                def apply_patch_spec(data: bytes, spec: object, verify_donor_sha256: bool = True):
                    after = data + b"_P"
                    return after, _FakeReceipt(data, after, getattr(spec, "sites", []))

                @staticmethod
                def resolve_and_verify_sites(data: bytes, spec: object, expect_patched_state: bool = True):
                    return [_FakeRes("u1")]

            class _FakeVfat:
                @staticmethod
                def build_opelog_vfat_image(mode: str):
                    img = b"VFAT" * 16
                    receipt = mock.Mock(
                        mode=mode,
                        fat_type="FAT16",
                        total_bytes=len(img),
                        sha256=hashlib.sha256(img).hexdigest(),
                        precreated_dirs=("OPE", "OPE/00", "OPE/01"),
                    )
                    return img, receipt

                @staticmethod
                def verify_vfat_image(_img: bytes):
                    return mock.Mock(valid=True, errors=[])

            class _FakeBmtv:
                @staticmethod
                def build_canonical_fa0080_normal_boot_table(donor_seed_bk4_path=None):
                    return b"T"

                @staticmethod
                def synthesize_ram_shadow_bk4(**_kw):
                    bk = b"BK4\x00" + b"\x00" * 12
                    return mock.Mock(
                        bk4_bytes=bk,
                        total_bytes=len(bk),
                        sha256=hashlib.sha256(bk).hexdigest(),
                        flash_write_allowed=False,
                        active_byte8_selector=0,
                        synthesized_key_count=1,
                    )

            fake_p10 = type(
                "FakeP10",
                (),
                {
                    "spec_id": "P10_FX3_TO_FX6_KEYMAP_ADAPTER",
                    "library_name": "appFw.so",
                    "sites": (mock.Mock(site_id="p10_fn", size=4),),
                },
            )()
            fake_p12 = type(
                "FakeP12",
                (),
                {
                    "spec_id": "P12_libWlanResource_fatal_guard",
                    "library_name": "libWlanResource.so",
                    "sites": (mock.Mock(site_id="p12_wlan", size=8),),
                },
            )()

            def _fake_subproc_run(cmd, **_kw):
                out_path = pathlib.Path(cmd[-1])
                out_path.write_bytes(b"ELF_VERIFY_17")
                return mock.Mock(returncode=0, stderr="")

            donor_u1 = tmp_dir / "donor_u1.uxc"
            donor_u2 = tmp_dir / "donor_u2.uxc"
            donor_ltt = tmp_dir / "donor_font.ltt"
            donor_uxc = tmp_dir / "donor_img.uxc"
            donor_u1.write_bytes(b"uxc\x07" + b"D1" * 16)
            donor_u2.write_bytes(b"uxc\x07" + b"D2" * 16)
            donor_ltt.write_bytes(b"LTT\n" + b"FD" * 16)
            donor_uxc.write_bytes(b"uxd\x07" + b"D" * 32)
            build_dir = tmp_dir / "build"

            with mock.patch.object(
                runner, "_import_stage_a_modules", return_value=(_FakePatcher, _FakeVfat, _FakeBmtv)
            ), mock.patch.object(
                runner, "_load_p10_keymap_spec", return_value=fake_p10
            ), mock.patch.object(
                runner, "_load_p12_wlan_spec", return_value=fake_p12
            ), mock.patch.object(
                runner, "DONOR_IMAGE_00_169_UXC", donor_uxc
            ), mock.patch.object(
                runner, donor_attr_u1, donor_u1
            ), mock.patch.object(
                runner, donor_attr_u2, donor_u2
            ), mock.patch.object(
                runner, donor_attr_ltt, donor_ltt
            ), mock.patch.object(
                runner, "FX3_UPM_KO", tmp_dir / "absent_upm.ko"
            ), mock.patch.object(
                runner, "FX3_SEED_BK4", tmp_dir / "absent_seed.bin"
            ), mock.patch.object(
                runner.subprocess, "run", side_effect=_fake_subproc_run
            ):
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
                    rep, add, meta = runner.build_stage_a_overlay(
                        build_dir,
                        parent_cpio,
                        b"BK4_NTSC",
                        enable_p10=True,
                        enable_r10=True,
                        enable_p12=True,
                        enable_r12=True,
                        enable_r13=True,
                        enable_r14=True,
                        enable_r15=True,
                        enable_r16=True,
                        enable_r17=True,
                        lang=lang,
                        shim_bytes=b"SHIM17",
                    )
                self.assertEqual(meta["manifest_count"], 13)
                self.assertTrue(meta["r16_enabled"])
                self.assertTrue(meta["r17_enabled"])
                self.assertEqual(meta["lang"], lang)
                self.assertIn("etc/fx6_stage_r17", add)
                self.assertIn(
                    f"statuscheck_fullsweep=1\naudio_3layer=1\nlang={lang}\n".encode("utf-8"),
                    add["etc/fx6_stage_r17"][0],
                )
                self.assertEqual(meta["lang_assets"][asset_key_u1]["source"], "cpio_preloaded")
                self.assertEqual(meta["lang_assets"][asset_key_ltt]["source"], "cpio_preloaded")
                self.assertEqual(meta["lang_assets"]["fontlist_dat"]["fontlist_key"], fontlist_key)
                self.assertEqual(rep[f"usr/share/app/{uxc2_name}"], b"uxc\x07" + b"C2" * 16)

                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "0"}):
                    rep2, add2, meta2 = runner.build_stage_a_overlay(
                        build_dir,
                        parent_cpio,
                        b"BK4_NTSC",
                        enable_p10=True,
                        enable_r10=True,
                        enable_p12=True,
                        enable_r12=True,
                        enable_r13=True,
                        enable_r14=True,
                        enable_r15=True,
                        enable_r16=True,
                        enable_r17=True,
                        lang=lang,
                        shim_bytes=b"SHIM17",
                    )
                self.assertTrue(meta2["r17_enabled"])
                self.assertIn("etc/fx6_stage_r17", add2)
                self.assertEqual(meta2["lang_assets"][asset_key_u1]["source"], "donor_o_rdonly")
                self.assertEqual(rep2[f"usr/share/app/{ltt_name}"], b"LTT\n" + b"FD" * 16)

    def test_round17_stage_a_overlay_schinese_dual_mode(self) -> None:
        self._assert_r17_overlay_dual_mode(
            lang="schinese",
            uxc1_name="string_simplifiedchinese.uxc",
            uxc2_name="string_simplifiedchinese_2.uxc",
            ltt_name="MYingHeiC-GB18030-SJ_wIcon.ltt",
            fontlist_key="FONT_S_CHINESE",
            asset_key_u1="string_simplifiedchinese",
            asset_key_ltt="font_gb18030_ltt",
            donor_attr_u1="DONOR_STRING_SCHINESE_UXC",
            donor_attr_u2="DONOR_STRING_SCHINESE_2_UXC",
            donor_attr_ltt="DONOR_FONT_SCHINESE_LTT",
        )

    def test_round17_stage_a_overlay_tchinese_dual_mode(self) -> None:
        self._assert_r17_overlay_dual_mode(
            lang="tchinese",
            uxc1_name="string_traditionalchinese.uxc",
            uxc2_name="string_traditionalchinese_2.uxc",
            ltt_name="MYingHeiC-Big5HKSCS-SJ_wIcon.ltt",
            fontlist_key="FONT_T_CHINESE",
            asset_key_u1="string_traditionalchinese",
            asset_key_ltt="font_big5hkscs_ltt",
            donor_attr_u1="DONOR_STRING_TCHINESE_UXC",
            donor_attr_u2="DONOR_STRING_TCHINESE_2_UXC",
            donor_attr_ltt="DONOR_FONT_TCHINESE_LTT",
        )

    def test_round17_stage_a_overlay_japanese_dual_mode(self) -> None:
        self._assert_r17_overlay_dual_mode(
            lang="japanese",
            uxc1_name="string_japanese.uxc",
            uxc2_name="string_japanese_2.uxc",
            ltt_name="HeiseiKakuGothW5-SJ_wIcon.ltt",
            fontlist_key="FONT_JAPANESE",
            asset_key_u1="string_japanese",
            asset_key_ltt="font_japanese_ltt",
            donor_attr_u1="DONOR_STRING_JAPANESE_UXC",
            donor_attr_u2="DONOR_STRING_JAPANESE_2_UXC",
            donor_attr_ltt="DONOR_FONT_JAPANESE_LTT",
        )

    def test_round17_extract_milestones_telemetry_parser(self) -> None:
        runner = _load_closure_module(
            "fx6_build_and_run_round_r17_ms", "build_and_run_round.py"
        )
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_STAGE_B_R17_VERIFY_PASS count=13 stage_b=1 p10_keymap=1 p11_uipc=1 p12_wlan=1 p4_nd_clear=1 uxc=1 statuscheck_fullsweep=1 audio_3layer=1 lang=schinese",
                "FX6_STAGE_B_R17_BRIDGE round=17 faithful=1 nop_count=0 p12_wlan=1 wf12_00342260_immune=1 p10_keymap=1 p4_nd_clear=1 p11_xlr_h1=1 lang=schinese bk4_lang=0x19 enum=0x2b45_CHINESE_SIMPLIFIED font_bank=23 str_bank=19 statuscheck_fullsweep=1 audio_3layer=1",
                "FX6_R17_LANG_TELEMETRY reason=pump lang=schinese bk4_lang_id=0x02cf019c bk4_lang_val=0x19 lang_enum=0x2b45_CHINESE_SIMPLIFIED font_bank=23 str_bank=19 lang_bk4_hits=3 airplane_bk4_hits=0 p4_nd_clear=1 p10_keymap=1 p11_xlr_h1=1 p12_wlan=1 wf12_00342260_immune=1 font_create=30916 glyph_blits=17407 icon_blits=9254 gpe_alloc=242 gpe_fb=0 statuscheck_fullsweep=1 audio_3layer=1 subst_color=0 subst_image=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        self.assertEqual(ms["prefix_counts"]["FX6_R17_"], 1)
        r17 = ms["r17_telemetry"]
        self.assertIsNotNone(r17)
        self.assertEqual(r17["lang"], "schinese")
        self.assertEqual(r17["bk4_lang_val"], "0x19")
        self.assertEqual(r17["font_bank"], 23)
        self.assertEqual(r17["str_bank"], 19)
        self.assertEqual(r17["p12_wlan"], 1)
        self.assertEqual(r17["wf12_00342260_immune"], 1)
        self.assertEqual(r17["gpe_alloc"], 242)
        self.assertEqual(r17["gpe_fb"], 0)
        self.assertEqual(r17["statuscheck_fullsweep"], 1)
        self.assertEqual(r17["audio_3layer"], 1)
        self.assertEqual(r17["subst_color"], 0)
        self.assertEqual(r17["subst_image"], 0)

    def test_round17_report_and_summary_json_invariants(self) -> None:
        self.assertTrue((ROUND17_REPORT_DIR / "README.md").is_file())
        summary_path = ROUND17_REPORT_DIR / "summary.json"
        self.assertTrue(summary_path.is_file())
        raw_text = summary_path.read_text(encoding="utf-8")
        for forbidden in ("/Volumes/KAFU2T", "/private/tmp", "/Users/"):
            self.assertNotIn(forbidden, raw_text)
        data = json.loads(raw_text)
        self.assertEqual(data["schema"], "fx6-on-fx3-round17-status-fullsweep-audio-v1")
        self.assertIn("Linux version 4.9.337-scel+", data["kernel_version"])
        self.assertEqual(set(data["languages"].keys()), {"en", "tchinese", "japanese", "schinese"})
        contract = data["status_check_multitab_contract"]
        self.assertEqual(contract["carousel_tab_count"], 10)
        self.assertEqual(contract["wrap_around_step_count"], 10)
        self.assertTrue(contract["wrap_around_verified"])
        self.assertEqual(len(contract["tabs_verified"]), 10)

        runs = data["runs"]
        self.assertEqual(set(runs.keys()), set(self.EXPECTED_RUN_KEYS))
        expectations = {
            "r17a_status_tab6_schinese": (
                "0x34", "47procam_touch_status_assignable_button_presenter", 437403, 80, 278,
            ),
            "r17b_status_tab7_schinese": (
                "0x35", "37procam_touch_status_battery_presenter", 437883, 80, 249,
            ),
            "r17c_status_tab8_schinese": (
                "0x36", "35procam_touch_status_media_presenter", 437403, 92, 288,
            ),
            "r17d_menu_3layer_audio_schinese": (
                "0x11", "31procam_menu_layer_3rd_presenter", 437575, 265, 5639,
            ),
            "r17e_status_tab9_network_schinese": (
                "0x37", "37procam_touch_status_network_presenter", 437883, 92, 273,
            ),
            "r17f_status_tab10_filetransfer_schinese": (
                "0x39", "43procam_touch_status_file_transfer_presenter", 437403, 80, 332,
            ),
            "r17g_status_wraparound_tab1_schinese": (
                "0x2f", "34procam_touch_status_main_presenter", 437883, 85, 237,
            ),
        }
        for key, (sid, presenter, exp_px, exp_col, exp_amber) in expectations.items():
            run = runs[key]
            self.assertEqual(run["round"], 17)
            self.assertEqual(run["lang"], "schinese")
            self.assertEqual(run["target_sid"], sid)
            self.assertEqual(run["target_presenter"], presenter)
            self.assertEqual(run["nop_count"], 0)
            self.assertEqual(run["crashes"], 0)
            self.assertGreaterEqual(run["ldec103_ioctl_count"], 60)
            self.assertGreaterEqual(run["total_threads_seen"], 161)
            self.assertEqual(
                run["faithful_invariants"],
                {
                    "FX6_NATIVE_FAITHFUL": 1,
                    "subst_color": 0,
                    "subst_image": 0,
                    "forced_render": 0,
                    "skipped_node": 0,
                    "lock_bypass": 0,
                },
            )
            sb = run["stage_b"]
            self.assertTrue(sb["r16_enabled"])
            self.assertTrue(sb["r17_enabled"])
            self.assertEqual(sb["lang"], "schinese")
            self.assertEqual(sb["manifest_count"], 13)
            self.assertEqual(len(sb["verify_bin_sha256"]), 64)
            self.assertIn("P12_libWlanResource_fatal_guard", sb["patches"])
            self.assertIn("P10_FX3_TO_FX6_KEYMAP_ADAPTER", sb["patches"])
            self.assertIn(
                "P4_appfw_set_nd_filter_mode_clear",
                sb["patches"]["P1_P4_P8_P10_appFw_combined"]["sites"],
            )
            self.assertGreaterEqual(run["prefix_counts"]["FX6_STAGE_A_"], 21)
            self.assertGreaterEqual(run["prefix_counts"]["FX6_STAGE_B_"], 26)
            self.assertGreaterEqual(run["prefix_counts"]["FX6_R17_"], 180)
            telem = run["r17_telemetry"]
            self.assertEqual(telem["p4_nd_clear"], 1)
            self.assertEqual(telem["p10_keymap"], 1)
            self.assertEqual(telem["p11_xlr_h1"], 1)
            self.assertEqual(telem["lang"], "schinese")
            self.assertEqual(telem["bk4_lang_val"], "0x19")
            self.assertEqual(telem["font_bank"], 23)
            self.assertEqual(telem["str_bank"], 19)
            self.assertEqual(telem["airplane_bk4_hits"], 0)
            self.assertEqual(telem["p12_wlan"], 1)
            self.assertEqual(telem["wf12_00342260_immune"], 1)
            self.assertEqual(telem["gpe_fb"], 0)
            self.assertEqual(telem["statuscheck_fullsweep"], 1)
            self.assertEqual(telem["audio_3layer"], 1)
            self.assertEqual(telem["subst_color"], 0)
            self.assertEqual(telem["subst_image"], 0)
            self.assertEqual(run["gpe0_readback"]["nonzero_pixels"], exp_px)
            self.assertEqual(run["gpe0_readback"]["unique_colors"], exp_col)
            self.assertEqual(run["amber_0xffffaa00_pixels"], exp_amber)

    def test_round17_stage_b_manifest_13_sha256_integrity(self) -> None:
        data = json.loads((ROUND17_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        shared_by_path: Dict[str, str] = {}
        for key in self.EXPECTED_RUN_KEYS:
            items = data["runs"][key]["stage_b"]["manifest_items"]
            self.assertEqual(len(items), 13)
            for item in items:
                gpath = item["guest_path"]
                digest = item["sha256"]
                self.assertEqual(len(digest), 64)
                int(digest, 16)
                if gpath == "/usr/lib/libgrm-fbinit9.so":
                    continue
                if gpath in shared_by_path:
                    self.assertEqual(shared_by_path[gpath], digest, f"SHA mismatch on {gpath}")
                else:
                    shared_by_path[gpath] = digest
        self.assertEqual(len(shared_by_path), 12)

    def test_round17_wf12_00342260_network_tab_immunity(self) -> None:
        data = json.loads((ROUND17_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        wf12 = data["r17_status_fullsweep_and_audio_audit"]["wf12_00342260_network_tab_immunity"]
        self.assertEqual(wf12["run_key"], "r17e_status_tab9_network_schinese")
        self.assertEqual(wf12["target_sid"], "0x37")
        self.assertEqual(wf12["target_presenter"], "37procam_touch_status_network_presenter")
        self.assertEqual(wf12["p12_wlan"], 1)
        self.assertEqual(wf12["wf12_00342260_immune"], 1)
        self.assertEqual(wf12["airplane_bk4_hits"], 0)
        self.assertEqual(wf12["nop_count"], 0)
        self.assertEqual(wf12["crashes"], 0)
        self.assertEqual(wf12["gpe_fb"], 0)

    @staticmethod
    def _diff_rows(ra: List[bytes], rb: List[bytes]) -> int:
        import operator
        ne = operator.ne
        return sum(
            sum(map(ne, memoryview(ya).cast("I"), memoryview(yb).cast("I")))
            for ya, yb in zip(ra, rb)
            if ya != yb
        )

    @staticmethod
    def _count_amber(rows: List[bytes]) -> int:
        amber_word = int.from_bytes(b"\xff\xaa\x00\xff", sys.byteorder)
        return sum(
            sum(1 for px in memoryview(row).cast("I") if px == amber_word)
            for row in rows
            if b"\xff\xaa\x00\xff" in row
        )

    def test_round17_statuscheck_10tabs_45pairs_pixel_deltas_exact(self) -> None:
        data = json.loads((ROUND17_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        audit = data["r17_status_fullsweep_and_audio_audit"]["status_check_10tab_pairwise_schinese"]
        self.assertEqual(audit["tab_count"], 10)
        self.assertEqual(audit["pair_count"], 45)
        self.assertTrue(audit["all_45_tab_pairs_strictly_positive"])
        self.assertEqual(audit["min_diff_pixels"], 39489)
        self.assertEqual(audit["max_diff_pixels"], 130085)

        tab_paths = {
            "tab1": ROUND13_ASSETS_DIR / "r13a-status-check-schinese-alpha.png",
            "tab2": ROUND15_ASSETS_DIR / "r15a-status-tab2-schinese-alpha.png",
            "tab3": ROUND15_ASSETS_DIR / "r15b-status-tab3-schinese-alpha.png",
            "tab4": ROUND16_ASSETS_DIR / "r16a-status-tab4-schinese-alpha.png",
            "tab5": ROUND16_ASSETS_DIR / "r16b-status-tab5-schinese-alpha.png",
            "tab6": ROUND17_ASSETS_DIR / "r17a-status-tab6-schinese-alpha.png",
            "tab7": ROUND17_ASSETS_DIR / "r17b-status-tab7-schinese-alpha.png",
            "tab8": ROUND17_ASSETS_DIR / "r17c-status-tab8-schinese-alpha.png",
            "tab9": ROUND17_ASSETS_DIR / "r17e-status-tab9-network-schinese-alpha.png",
            "tab10": ROUND17_ASSETS_DIR / "r17f-status-tab10-filetransfer-schinese-alpha.png",
        }
        rows = {k: _decode_png_rgba_rows(p.read_bytes())[2] for k, p in tab_paths.items()}
        pairs = audit["pairs"]
        self.assertEqual(len(pairs), 45)
        for i in range(1, 11):
            for j in range(i + 1, 11):
                pkey = f"tab{i}_vs_tab{j}"
                entry = pairs[pkey]
                self.assertTrue(entry["strictly_positive"])
                diff = self._diff_rows(rows[f"tab{i}"], rows[f"tab{j}"])
                self.assertGreater(diff, 0)
                self.assertEqual(diff, entry["diff_pixels"])

    def test_round17_statuscheck_10tab_wraparound_to_tab1_proof(self) -> None:
        data = json.loads((ROUND17_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        wrap = data["r17_status_fullsweep_and_audio_audit"]["status_check_wraparound_proof"]
        self.assertEqual(wrap["step_count_down"], 10)
        self.assertEqual(wrap["target_sid"], "0x2f")
        self.assertEqual(wrap["target_presenter"], "34procam_touch_status_main_presenter")
        self.assertEqual(wrap["diff_vs_r13a_tab1_pixels"], 480)
        self.assertTrue(wrap["all_non_tab1_diffs_strictly_positive"])

        rows_wrap = _decode_png_rgba_rows(
            (ROUND17_ASSETS_DIR / "r17g-status-wraparound-tab1-schinese-alpha.png").read_bytes()
        )[2]
        rows_tab1 = _decode_png_rgba_rows(
            (ROUND13_ASSETS_DIR / "r13a-status-check-schinese-alpha.png").read_bytes()
        )[2]
        rows_tab10 = _decode_png_rgba_rows(
            (ROUND17_ASSETS_DIR / "r17f-status-tab10-filetransfer-schinese-alpha.png").read_bytes()
        )[2]
        self.assertEqual(self._diff_rows(rows_wrap, rows_tab1), 480)
        self.assertEqual(self._diff_rows(rows_wrap, rows_tab10), 87314)
        for k, v in wrap["wrap_diffs_vs_tabs1_to_10"].items():
            if k != "wrap_vs_tab1":
                self.assertGreater(v, 50000)

    def test_round17_menu_3layer_4cat_schinese_6pairs_pixel_deltas_exact(self) -> None:
        data = json.loads((ROUND17_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        audit = data["r17_status_fullsweep_and_audio_audit"]["menu_3layer_4cat_schinese_pairwise"]
        self.assertEqual(audit["category_count"], 4)
        self.assertEqual(audit["pair_count"], 6)
        self.assertTrue(audit["all_6_category_pairs_strictly_positive"])

        cat_rows = {
            "shooting": _decode_png_rgba_rows((ROUND11_ASSETS_DIR / "r11d-c2-menu-3layer-schinese-alpha.png").read_bytes())[2],
            "paint_look": _decode_png_rgba_rows((ROUND13_ASSETS_DIR / "r13c-menu-3layer-paintlook-schinese-alpha.png").read_bytes())[2],
            "monitoring": _decode_png_rgba_rows((ROUND15_ASSETS_DIR / "r15c-menu-3layer-monitoring-schinese-alpha.png").read_bytes())[2],
            "audio": _decode_png_rgba_rows((ROUND17_ASSETS_DIR / "r17d-menu-3layer-audio-schinese-alpha.png").read_bytes())[2],
        }
        expected_pairs = (
            ("shooting_vs_paint_look", "shooting", "paint_look", 138994),
            ("shooting_vs_monitoring", "shooting", "monitoring", 124819),
            ("shooting_vs_audio", "shooting", "audio", 146605),
            ("paint_look_vs_monitoring", "paint_look", "monitoring", 31140),
            ("paint_look_vs_audio", "paint_look", "audio", 57384),
            ("monitoring_vs_audio", "monitoring", "audio", 42677),
        )
        for pkey, a_key, b_key, exp_diff in expected_pairs:
            entry = audit["pairs"][pkey]
            self.assertEqual(entry["diff_pixels"], exp_diff)
            self.assertTrue(entry["strictly_positive"])
            diff = self._diff_rows(cat_rows[a_key], cat_rows[b_key])
            self.assertGreater(diff, 0)
            self.assertEqual(diff, exp_diff)

    def test_round17_png_receipts_valid_under_85kib_and_amber(self) -> None:
        self.assertTrue(ROUND17_ASSETS_DIR.is_dir())
        alpha_digests: Dict[str, str] = {}
        comp_digests: Dict[str, str] = {}
        for stem in self.EXPECTED_STEMS:
            for variant, bucket in (("alpha", alpha_digests), ("composited", comp_digests)):
                png_path = ROUND17_ASSETS_DIR / f"{stem}-{variant}.png"
                self.assertTrue(png_path.is_file(), f"Missing Round 17 PNG: {png_path}")
                raw = png_path.read_bytes()
                self.assertLess(len(raw), 85 * 1024, f"PNG exceeds 85 KiB: {png_path}")
                w, h, _ = _decode_png_rgba_rows(raw)
                self.assertEqual((w, h), (1024, 540))
                bucket[stem] = hashlib.sha256(raw).hexdigest()
        self.assertEqual(len(set(alpha_digests.values())), len(self.EXPECTED_STEMS))
        self.assertEqual(len(set(comp_digests.values())), len(self.EXPECTED_STEMS))

        for stem, exp_amber in (
            ("r17a-status-tab6-schinese", 278),
            ("r17b-status-tab7-schinese", 249),
            ("r17c-status-tab8-schinese", 288),
            ("r17d-menu-3layer-audio-schinese", 5639),
            ("r17e-status-tab9-network-schinese", 273),
            ("r17f-status-tab10-filetransfer-schinese", 332),
            ("r17g-status-wraparound-tab1-schinese", 237),
        ):
            _, _, rows = _decode_png_rgba_rows((ROUND17_ASSETS_DIR / f"{stem}-alpha.png").read_bytes())
            self.assertEqual(self._count_amber(rows), exp_amber)

    def test_round17_readme_and_no_tmp_scratch_residue(self) -> None:
        closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn("2026-11-14-round17-fx6-on-fx3-status-fullsweep-audio", closure_readme)
        r17_readme = (ROUND17_REPORT_DIR / "README.md").read_text(encoding="utf-8")
        for tok in ("0x34", "0x35", "0x36", "0x37", "0x39", "0x2f", "0x11", "Audio", "Network", "WF-12"):
            self.assertIn(tok, r17_readme)
        for forbidden in ("/Volumes/KAFU2T", "/Users/"):
            self.assertNotIn(forbidden, r17_readme)
        tmp_matches = list(pathlib.Path("/private/tmp").glob("fx6-r17*"))
        self.assertEqual(tmp_matches, [], f"Leftover scratch dirs in /private/tmp: {tmp_matches}")


class TestRound18Menu8CategorySChineseClosure(unittest.TestCase):
    EXPECTED_STEMS = (
        "r18a-menu-3layer-project-schinese",
        "r18b-menu-3layer-tcmedia-schinese",
        "r18c-menu-3layer-network-schinese",
        "r18d-menu-3layer-maintenance-schinese",
    )
    EXPECTED_RUN_KEYS = (
        "r18a_menu_3layer_project_schinese",
        "r18b_menu_3layer_tcmedia_schinese",
        "r18c_menu_3layer_network_schinese",
        "r18d_menu_3layer_maintenance_schinese",
    )

    def test_round18_c_source_guards_and_runner_support(self) -> None:
        shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")

        self.assertIn("#if FX6_ROUND >= 18", shim_src)
        for token in (
            "FX6_R18_LANG_TELEMETRY",
            "FX6_STAGE_B_R18_BRIDGE",
            "menu_8cat_closure=1",
            "wf12_00342260_immune=1",
        ):
            self.assertIn(token, shim_src)

        for token in (
            "/etc/fx6_stage_r18",
            "FX6_STAGE_B_R18_VERIFY_PASS",
            "menu_8cat_closure=1",
            "wf12_00342260_immune=1",
        ):
            self.assertIn(token, verify_src)

        for token in (
            "enable_r18",
            "etc/fx6_stage_r18",
            '"r18_telemetry"',
            '"fx6-r18"',
            "choices=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]",
        ):
            self.assertIn(token, runner_src)

    def _assert_r18_overlay_dual_mode(
        self,
        lang: str,
        uxc1_name: str,
        uxc2_name: str,
        ltt_name: str,
        fontlist_key: str,
        asset_key_u1: str,
        asset_key_ltt: str,
        donor_attr_u1: str,
        donor_attr_u2: str,
        donor_attr_ltt: str,
    ) -> None:
        runner = _load_closure_module(
            f"fx6_build_and_run_round_r18_ovl_{lang}", "build_and_run_round.py"
        )
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            parent_cpio = tmp_dir / "parent.cpio"
            init_body = (
                b"#!/bin/sh\n"
                b'LD_PRELOAD="$FX6_PRELOAD" /usr/bin/appfw-launch\n'
            )
            members = (
                ("init", init_body),
                ("usr/lib/libInfraSetupFile.so", b"SETUP"),
                ("usr/lib/libInfraMediaCommon.so", b"MCOMM"),
                ("usr/lib/libInfraMediaConfig.so", b"MCFG"),
                ("usr/lib/libInfraAppRemoteBoard.so", b"RBRD"),
                ("usr/lib/libfan.so", b"FAN"),
                ("usr/lib/appFw.so", b"APPFW"),
                ("usr/lib/libWlanResource.so", b"WLAN_DONOR_12345"),
                ("usr/kmod/upm.ko", b"UPMKO"),
                ("usr/share/app/image_00_169.uxc", b"uxd\x07" + b"C" * 32),
                (f"usr/share/app/{uxc1_name}", b"uxc\x07" + b"C1" * 16),
                (f"usr/share/app/{uxc2_name}", b"uxc\x07" + b"C2" * 16),
                (f"usr/share/app/{ltt_name}", b"LTT\n" + b"CL" * 16),
                (
                    "usr/share/app/fontlist.dat",
                    f"{fontlist_key}\t/usr/share/app/{ltt_name}\t0\t0\n".encode("ascii"),
                ),
            )
            archive = b"".join(
                runner.make_cpio_member(name, body, ino=idx + 1, mode=0o100755)
                for idx, (name, body) in enumerate(members)
            ) + runner.make_cpio_member("TRAILER!!!", b"", ino=0, mode=0)
            parent_cpio.write_bytes(archive)

            class _FakeRes:
                def __init__(self, site_id: str) -> None:
                    self.site_id = site_id

            class _FakeReceipt:
                def __init__(self, before: bytes, after: bytes, sites: list) -> None:
                    self.before_sha256 = hashlib.sha256(before).hexdigest()
                    self.after_sha256 = hashlib.sha256(after).hexdigest()
                    self.changed_byte_count = 8
                    self.resolutions = [_FakeRes(s.site_id) for s in sites]

            class _FakePatcher:
                P1_P4_P8_APPFW_COMBINED_SPEC = mock.Mock(
                    library_name="appFw.so",
                    expected_size=5,
                    donor_sha256="0" * 64,
                    sites=(mock.Mock(site_id="p1"),),
                    elf_kind="so",
                    source_domain="fx6",
                )
                P1_LIB_INFRA_SETUP_FILE_SPEC = mock.Mock(spec_id="P1_s", library_name="s", sites=[mock.Mock(site_id="s1")])
                P1_LIB_INFRA_MEDIA_COMMON_SPEC = mock.Mock(spec_id="P1_c", library_name="c", sites=[mock.Mock(site_id="c1")])
                P1_LIB_INFRA_MEDIA_CONFIG_SPEC = mock.Mock(spec_id="P1_g", library_name="g", sites=[mock.Mock(site_id="g1")])
                P3_LIB_INFRA_APP_REMOTE_BOARD_SPEC = mock.Mock(spec_id="P3_r", library_name="r", sites=[mock.Mock(site_id="r1")])
                FAN_LIBFAN_SPEC = mock.Mock(spec_id="Fan_f", library_name="f", sites=[mock.Mock(site_id="f1")])
                P9_UPM_KO_SPEC = mock.Mock(spec_id="P9_u", library_name="upm.ko", sites=[mock.Mock(site_id="u1")])
                LibraryPatchSpec = lambda **kw: type("FakeSpec", (), kw)()
                PatchSiteSpec = object
                PF_R = 4

                @staticmethod
                def apply_patch_spec(data: bytes, spec: object, verify_donor_sha256: bool = True):
                    after = data + b"_P"
                    return after, _FakeReceipt(data, after, getattr(spec, "sites", []))

                @staticmethod
                def resolve_and_verify_sites(data: bytes, spec: object, expect_patched_state: bool = True):
                    return [_FakeRes("u1")]

            class _FakeVfat:
                @staticmethod
                def build_opelog_vfat_image(mode: str):
                    img = b"VFAT" * 16
                    receipt = mock.Mock(
                        mode=mode,
                        fat_type="FAT16",
                        total_bytes=len(img),
                        sha256=hashlib.sha256(img).hexdigest(),
                        precreated_dirs=("OPE", "OPE/00", "OPE/01"),
                    )
                    return img, receipt

                @staticmethod
                def verify_vfat_image(_img: bytes):
                    return mock.Mock(valid=True, errors=[])

            class _FakeBmtv:
                @staticmethod
                def build_canonical_fa0080_normal_boot_table(donor_seed_bk4_path=None):
                    return b"T"

                @staticmethod
                def synthesize_ram_shadow_bk4(**_kw):
                    bk = b"BK4\x00" + b"\x00" * 12
                    return mock.Mock(
                        bk4_bytes=bk,
                        total_bytes=len(bk),
                        sha256=hashlib.sha256(bk).hexdigest(),
                        flash_write_allowed=False,
                        active_byte8_selector=0,
                        synthesized_key_count=1,
                    )

            fake_p10 = type(
                "FakeP10",
                (),
                {
                    "spec_id": "P10_FX3_TO_FX6_KEYMAP_ADAPTER",
                    "library_name": "appFw.so",
                    "sites": (mock.Mock(site_id="p10_fn", size=4),),
                },
            )()
            fake_p12 = type(
                "FakeP12",
                (),
                {
                    "spec_id": "P12_libWlanResource_fatal_guard",
                    "library_name": "libWlanResource.so",
                    "sites": (mock.Mock(site_id="p12_wlan", size=8),),
                },
            )()

            def _fake_subproc_run(cmd, **_kw):
                out_path = pathlib.Path(cmd[-1])
                out_path.write_bytes(b"ELF_VERIFY_18")
                return mock.Mock(returncode=0, stderr="")

            donor_u1 = tmp_dir / "donor_u1.uxc"
            donor_u2 = tmp_dir / "donor_u2.uxc"
            donor_ltt = tmp_dir / "donor_font.ltt"
            donor_uxc = tmp_dir / "donor_img.uxc"
            donor_u1.write_bytes(b"uxc\x07" + b"D1" * 16)
            donor_u2.write_bytes(b"uxc\x07" + b"D2" * 16)
            donor_ltt.write_bytes(b"LTT\n" + b"FD" * 16)
            donor_uxc.write_bytes(b"uxd\x07" + b"D" * 32)
            build_dir = tmp_dir / "build"

            with mock.patch.object(
                runner, "_import_stage_a_modules", return_value=(_FakePatcher, _FakeVfat, _FakeBmtv)
            ), mock.patch.object(
                runner, "_load_p10_keymap_spec", return_value=fake_p10
            ), mock.patch.object(
                runner, "_load_p12_wlan_spec", return_value=fake_p12
            ), mock.patch.object(
                runner, "DONOR_IMAGE_00_169_UXC", donor_uxc
            ), mock.patch.object(
                runner, donor_attr_u1, donor_u1
            ), mock.patch.object(
                runner, donor_attr_u2, donor_u2
            ), mock.patch.object(
                runner, donor_attr_ltt, donor_ltt
            ), mock.patch.object(
                runner, "FX3_UPM_KO", tmp_dir / "absent_upm.ko"
            ), mock.patch.object(
                runner, "FX3_SEED_BK4", tmp_dir / "absent_seed.bin"
            ), mock.patch.object(
                runner.subprocess, "run", side_effect=_fake_subproc_run
            ):
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
                    rep, add, meta = runner.build_stage_a_overlay(
                        build_dir,
                        parent_cpio,
                        b"BK4_NTSC",
                        enable_p10=True,
                        enable_r10=True,
                        enable_p12=True,
                        enable_r12=True,
                        enable_r13=True,
                        enable_r14=True,
                        enable_r15=True,
                        enable_r16=True,
                        enable_r17=True,
                        enable_r18=True,
                        lang=lang,
                        shim_bytes=b"SHIM18",
                    )
                self.assertEqual(meta["manifest_count"], 13)
                self.assertTrue(meta["r17_enabled"])
                self.assertTrue(meta["r18_enabled"])
                self.assertEqual(meta["lang"], lang)
                self.assertIn("etc/fx6_stage_r18", add)
                self.assertIn(
                    f"menu_8cat_closure=1\nlang={lang}\n".encode("utf-8"),
                    add["etc/fx6_stage_r18"][0],
                )
                self.assertEqual(meta["lang_assets"][asset_key_u1]["source"], "cpio_preloaded")
                self.assertEqual(meta["lang_assets"][asset_key_ltt]["source"], "cpio_preloaded")
                self.assertEqual(meta["lang_assets"]["fontlist_dat"]["fontlist_key"], fontlist_key)
                self.assertEqual(rep[f"usr/share/app/{uxc2_name}"], b"uxc\x07" + b"C2" * 16)

                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "0"}):
                    rep2, add2, meta2 = runner.build_stage_a_overlay(
                        build_dir,
                        parent_cpio,
                        b"BK4_NTSC",
                        enable_p10=True,
                        enable_r10=True,
                        enable_p12=True,
                        enable_r12=True,
                        enable_r13=True,
                        enable_r14=True,
                        enable_r15=True,
                        enable_r16=True,
                        enable_r17=True,
                        enable_r18=True,
                        lang=lang,
                        shim_bytes=b"SHIM18",
                    )
                self.assertTrue(meta2["r18_enabled"])
                self.assertIn("etc/fx6_stage_r18", add2)
                self.assertEqual(meta2["lang_assets"][asset_key_u1]["source"], "donor_o_rdonly")
                self.assertEqual(rep2[f"usr/share/app/{ltt_name}"], b"LTT\n" + b"FD" * 16)

    def test_round18_stage_a_overlay_schinese_dual_mode(self) -> None:
        self._assert_r18_overlay_dual_mode(
            lang="schinese",
            uxc1_name="string_simplifiedchinese.uxc",
            uxc2_name="string_simplifiedchinese_2.uxc",
            ltt_name="MYingHeiC-GB18030-SJ_wIcon.ltt",
            fontlist_key="FONT_S_CHINESE",
            asset_key_u1="string_simplifiedchinese",
            asset_key_ltt="font_gb18030_ltt",
            donor_attr_u1="DONOR_STRING_SCHINESE_UXC",
            donor_attr_u2="DONOR_STRING_SCHINESE_2_UXC",
            donor_attr_ltt="DONOR_FONT_SCHINESE_LTT",
        )

    def test_round18_stage_a_overlay_tchinese_dual_mode(self) -> None:
        self._assert_r18_overlay_dual_mode(
            lang="tchinese",
            uxc1_name="string_traditionalchinese.uxc",
            uxc2_name="string_traditionalchinese_2.uxc",
            ltt_name="MYingHeiC-Big5HKSCS-SJ_wIcon.ltt",
            fontlist_key="FONT_T_CHINESE",
            asset_key_u1="string_traditionalchinese",
            asset_key_ltt="font_big5hkscs_ltt",
            donor_attr_u1="DONOR_STRING_TCHINESE_UXC",
            donor_attr_u2="DONOR_STRING_TCHINESE_2_UXC",
            donor_attr_ltt="DONOR_FONT_TCHINESE_LTT",
        )

    def test_round18_stage_a_overlay_japanese_dual_mode(self) -> None:
        self._assert_r18_overlay_dual_mode(
            lang="japanese",
            uxc1_name="string_japanese.uxc",
            uxc2_name="string_japanese_2.uxc",
            ltt_name="HeiseiKakuGothW5-SJ_wIcon.ltt",
            fontlist_key="FONT_JAPANESE",
            asset_key_u1="string_japanese",
            asset_key_ltt="font_japanese_ltt",
            donor_attr_u1="DONOR_STRING_JAPANESE_UXC",
            donor_attr_u2="DONOR_STRING_JAPANESE_2_UXC",
            donor_attr_ltt="DONOR_FONT_JAPANESE_LTT",
        )

    def test_round18_stage_a_overlay_english_dual_mode(self) -> None:
        self._assert_r18_overlay_dual_mode(
            lang="english",
            uxc1_name="string_english.uxc",
            uxc2_name="string_english_2.uxc",
            ltt_name="UniversOTS-SJ_wIcon.ltt",
            fontlist_key="FONT_UNIVERS",
            asset_key_u1="string_english",
            asset_key_ltt="font_univers_ltt",
            donor_attr_u1="DONOR_STRING_ENGLISH_UXC",
            donor_attr_u2="DONOR_STRING_ENGLISH_2_UXC",
            donor_attr_ltt="DONOR_FONT_ENGLISH_LTT",
        )

    def test_round18_extract_milestones_telemetry_parser(self) -> None:
        runner = _load_closure_module(
            "fx6_build_and_run_round_r18_ms", "build_and_run_round.py"
        )
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_STAGE_B_R18_VERIFY_PASS count=13 stage_b=1 p10_keymap=1 p11_uipc=1 p12_wlan=1 p4_nd_clear=1 uxc=1 menu_8cat_closure=1 wf12_00342260_immune=1 lang=schinese",
                "FX6_STAGE_B_R18_BRIDGE round=18 faithful=1 nop_count=0 p12_wlan=1 wf12_00342260_immune=1 p10_keymap=1 p4_nd_clear=1 p11_xlr_h1=1 lang=schinese bk4_lang=0x19 enum=0x2b45_CHINESE_SIMPLIFIED font_bank=23 str_bank=19 menu_8cat_closure=1",
                "FX6_R18_LANG_TELEMETRY reason=pump lang=schinese bk4_lang_id=0x02cf019c bk4_lang_val=0x19 lang_enum=0x2b45_CHINESE_SIMPLIFIED font_bank=23 str_bank=19 lang_bk4_hits=3 airplane_bk4_hits=0 p4_nd_clear=1 p10_keymap=1 p11_xlr_h1=1 p12_wlan=1 wf12_00342260_immune=1 font_create=18823 glyph_blits=10579 icon_blits=14916 gpe_alloc=223 gpe_fb=0 menu_8cat_closure=1 subst_color=0 subst_image=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        self.assertEqual(ms["prefix_counts"]["FX6_R18_"], 1)
        r18 = ms["r18_telemetry"]
        self.assertIsNotNone(r18)
        self.assertEqual(r18["lang"], "schinese")
        self.assertEqual(r18["bk4_lang_val"], "0x19")
        self.assertEqual(r18["font_bank"], 23)
        self.assertEqual(r18["str_bank"], 19)
        self.assertEqual(r18["p12_wlan"], 1)
        self.assertEqual(r18["wf12_00342260_immune"], 1)
        self.assertEqual(r18["airplane_bk4_hits"], 0)
        self.assertEqual(r18["gpe_alloc"], 223)
        self.assertEqual(r18["gpe_fb"], 0)
        self.assertEqual(r18["menu_8cat_closure"], 1)
        self.assertEqual(r18["subst_color"], 0)
        self.assertEqual(r18["subst_image"], 0)

    def test_round18_report_and_summary_json_invariants(self) -> None:
        self.assertTrue((ROUND18_REPORT_DIR / "README.md").is_file())
        summary_path = ROUND18_REPORT_DIR / "summary.json"
        self.assertTrue(summary_path.is_file())
        raw_text = summary_path.read_text(encoding="utf-8")
        for forbidden in ("/Volumes/KAFU2T", "/private/tmp", "/Users/"):
            self.assertNotIn(forbidden, raw_text)
        data = json.loads(raw_text)
        self.assertEqual(data["schema"], "fx6-on-fx3-round18-menu-8category-closure-v1")
        self.assertIn("Linux version 4.9.337-scel+", data["kernel_version"])
        self.assertEqual(set(data["languages"].keys()), {"en", "tchinese", "japanese", "schinese"})

        runs = data["runs"]
        self.assertEqual(set(runs.keys()), set(self.EXPECTED_RUN_KEYS))
        expectations = {
            "r18a_menu_3layer_project_schinese": ("Project", 2, 437575, 253, 1074),
            "r18b_menu_3layer_tcmedia_schinese": ("TC/Media", 4, 437575, 245, 2430),
            "r18c_menu_3layer_network_schinese": ("Network", 9, 437575, 273, 0),
            "r18d_menu_3layer_maintenance_schinese": ("Maintenance", 10, 437095, 238, 0),
        }
        for key, (cat, steps, exp_px, exp_col, exp_amber) in expectations.items():
            run = runs[key]
            self.assertEqual(run["round"], 18)
            self.assertEqual(run["lang"], "schinese")
            self.assertEqual(run["menu_category"], cat)
            self.assertEqual(run["rail_down_steps"], steps)
            self.assertEqual(run["target_sid"], "0x11")
            self.assertEqual(run["target_presenter"], "31procam_menu_layer_3rd_presenter")
            self.assertEqual(run["target_controller"], "32procam_menu_layer_3rd_controller")
            self.assertEqual(run["nop_count"], 0)
            self.assertEqual(run["crashes"], 0)
            self.assertGreaterEqual(run["ldec103_ioctl_count"], 80)
            self.assertGreaterEqual(run["total_threads_seen"], 161)
            self.assertEqual(
                run["faithful_invariants"],
                {
                    "FX6_NATIVE_FAITHFUL": 1,
                    "subst_color": 0,
                    "subst_image": 0,
                    "forced_render": 0,
                    "skipped_node": 0,
                    "lock_bypass": 0,
                },
            )
            sb = run["stage_b"]
            self.assertTrue(sb["r17_enabled"])
            self.assertTrue(sb["r18_enabled"])
            self.assertEqual(sb["lang"], "schinese")
            self.assertEqual(sb["manifest_count"], 13)
            self.assertEqual(len(sb["verify_bin_sha256"]), 64)
            self.assertIn("P12_libWlanResource_fatal_guard", sb["patches"])
            self.assertIn("P10_FX3_TO_FX6_KEYMAP_ADAPTER", sb["patches"])
            self.assertIn(
                "P4_appfw_set_nd_filter_mode_clear",
                sb["patches"]["P1_P4_P8_P10_appFw_combined"]["sites"],
            )
            self.assertGreaterEqual(run["prefix_counts"]["FX6_STAGE_A_"], 21)
            self.assertGreaterEqual(run["prefix_counts"]["FX6_STAGE_B_"], 26)
            self.assertGreaterEqual(run["prefix_counts"]["FX6_R18_"], 180)
            telem = run["r18_telemetry"]
            self.assertEqual(telem["p4_nd_clear"], 1)
            self.assertEqual(telem["p10_keymap"], 1)
            self.assertEqual(telem["p11_xlr_h1"], 1)
            self.assertEqual(telem["lang"], "schinese")
            self.assertEqual(telem["bk4_lang_val"], "0x19")
            self.assertEqual(telem["font_bank"], 23)
            self.assertEqual(telem["str_bank"], 19)
            self.assertEqual(telem["airplane_bk4_hits"], 0)
            self.assertEqual(telem["p12_wlan"], 1)
            self.assertEqual(telem["wf12_00342260_immune"], 1)
            self.assertEqual(telem["gpe_fb"], 0)
            self.assertEqual(telem["menu_8cat_closure"], 1)
            self.assertEqual(telem["subst_color"], 0)
            self.assertEqual(telem["subst_image"], 0)
            self.assertEqual(run["gpe0_readback"]["nonzero_pixels"], exp_px)
            self.assertEqual(run["gpe0_readback"]["unique_colors"], exp_col)
            self.assertEqual(run["amber_0xffffaa00_pixels"], exp_amber)

    def test_round18_stage_b_manifest_13_sha256_integrity(self) -> None:
        data = json.loads((ROUND18_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        shared_by_path: Dict[str, str] = {}
        for key in self.EXPECTED_RUN_KEYS:
            items = data["runs"][key]["stage_b"]["manifest_items"]
            self.assertEqual(len(items), 13)
            for item in items:
                gpath = item["guest_path"]
                digest = item["sha256"]
                self.assertEqual(len(digest), 64)
                int(digest, 16)
                if gpath == "/usr/lib/libgrm-fbinit9.so":
                    continue
                if gpath in shared_by_path:
                    self.assertEqual(shared_by_path[gpath], digest, f"SHA mismatch on {gpath}")
                else:
                    shared_by_path[gpath] = digest
        self.assertEqual(len(shared_by_path), 12)

    def test_round18_full_menu_l1_rail_contract(self) -> None:
        data = json.loads((ROUND18_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        rail = data["full_menu_l1_rail_contract"]
        self.assertEqual(rail["table_offset"], "appFw.so+0x2924180")
        self.assertEqual(rail["entry_stride_bytes"], 48)
        cats = rail["rail_categories_visible_in_shooting_mode"]
        self.assertEqual(len(cats), 11)
        by_name = {c["category"]: c for c in cats}
        self.assertEqual(by_name["Shooting"]["down_steps"], 1)
        self.assertEqual(by_name["Project"]["down_steps"], 2)
        self.assertEqual(by_name["Paint/Look"]["down_steps"], 3)
        self.assertEqual(by_name["TC/Media"]["down_steps"], 4)
        self.assertEqual(by_name["Monitoring"]["down_steps"], 5)
        self.assertEqual(by_name["Audio"]["down_steps"], 6)
        self.assertEqual(by_name["Network"]["down_steps"], 9)
        self.assertEqual(by_name["Maintenance"]["down_steps"], 10)
        skipped = {c["category"] for c in rail["skipped_categories_in_shooting_mode"]}
        self.assertEqual(skipped, {"Pan-Tilt", "Service"})

    def test_round18_wf12_00342260_network_menu_immunity(self) -> None:
        data = json.loads((ROUND18_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        wf12 = data["r18_menu_8category_closure_audit"]["wf12_00342260_network_menu_immunity"]
        self.assertEqual(wf12["run_key"], "r18c_menu_3layer_network_schinese")
        self.assertEqual(wf12["target_sid"], "0x11")
        self.assertEqual(wf12["target_presenter"], "31procam_menu_layer_3rd_presenter")
        self.assertEqual(wf12["menu_category"], "Network")
        self.assertEqual(wf12["p12_wlan"], 1)
        self.assertEqual(wf12["wf12_00342260_immune"], 1)
        self.assertEqual(wf12["airplane_bk4_hits"], 0)
        self.assertEqual(wf12["nop_count"], 0)
        self.assertEqual(wf12["crashes"], 0)
        self.assertEqual(wf12["gpe_fb"], 0)

    @staticmethod
    def _diff_rows(ra: List[bytes], rb: List[bytes]) -> int:
        import operator
        ne = operator.ne
        return sum(
            sum(map(ne, memoryview(ya).cast("I"), memoryview(yb).cast("I")))
            for ya, yb in zip(ra, rb)
            if ya != yb
        )

    @staticmethod
    def _count_amber(rows: List[bytes]) -> int:
        amber_word = int.from_bytes(b"\xff\xaa\x00\xff", sys.byteorder)
        return sum(
            sum(1 for px in memoryview(row).cast("I") if px == amber_word)
            for row in rows
            if b"\xff\xaa\x00\xff" in row
        )

    def test_round18_menu_3layer_8cat_schinese_28pairs_pixel_deltas_exact(self) -> None:
        data = json.loads((ROUND18_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        audit = data["r18_menu_8category_closure_audit"]["menu_3layer_8cat_schinese_pairwise"]
        self.assertEqual(audit["category_count"], 8)
        self.assertEqual(audit["pair_count"], 28)
        self.assertTrue(audit["all_28_category_pairs_strictly_positive"])
        self.assertEqual(audit["min_diff_pixels"], 8755)
        self.assertEqual(audit["max_diff_pixels"], 146605)

        cat_paths = {
            "shooting": ROUND11_ASSETS_DIR / "r11d-c2-menu-3layer-schinese-alpha.png",
            "project": ROUND18_ASSETS_DIR / "r18a-menu-3layer-project-schinese-alpha.png",
            "paint_look": ROUND13_ASSETS_DIR / "r13c-menu-3layer-paintlook-schinese-alpha.png",
            "tc_media": ROUND18_ASSETS_DIR / "r18b-menu-3layer-tcmedia-schinese-alpha.png",
            "monitoring": ROUND15_ASSETS_DIR / "r15c-menu-3layer-monitoring-schinese-alpha.png",
            "audio": ROUND17_ASSETS_DIR / "r17d-menu-3layer-audio-schinese-alpha.png",
            "network": ROUND18_ASSETS_DIR / "r18c-menu-3layer-network-schinese-alpha.png",
            "maintenance": ROUND18_ASSETS_DIR / "r18d-menu-3layer-maintenance-schinese-alpha.png",
        }
        rows = {k: _decode_png_rgba_rows(p.read_bytes())[2] for k, p in cat_paths.items()}
        cat_keys = list(cat_paths.keys())
        pairs = audit["pairs"]
        self.assertEqual(len(pairs), 28)
        for i in range(len(cat_keys)):
            for j in range(i + 1, len(cat_keys)):
                ka, kb = cat_keys[i], cat_keys[j]
                pkey = f"{ka}_vs_{kb}"
                entry = pairs[pkey]
                self.assertTrue(entry["strictly_positive"])
                diff = self._diff_rows(rows[ka], rows[kb])
                self.assertGreater(diff, 0)
                self.assertEqual(diff, entry["diff_pixels"])

    def test_round18_tcmedia_schinese_vs_tchinese_delta_exact(self) -> None:
        data = json.loads((ROUND18_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        cross = data["r18_menu_8category_closure_audit"]["tcmedia_schinese_vs_tchinese_delta"]
        self.assertTrue(cross["strictly_positive"])
        self.assertEqual(cross["diff_pixels"], 12853)
        rows_sc = _decode_png_rgba_rows(
            (ROUND18_ASSETS_DIR / "r18b-menu-3layer-tcmedia-schinese-alpha.png").read_bytes()
        )[2]
        rows_tc = _decode_png_rgba_rows(
            (ROUND16_ASSETS_DIR / "r16c-menu-3layer-tcmedia-tchinese-alpha.png").read_bytes()
        )[2]
        diff = self._diff_rows(rows_sc, rows_tc)
        self.assertGreater(diff, 0)
        self.assertEqual(diff, 12853)

    def test_round18_png_receipts_valid_under_85kib_and_amber(self) -> None:
        self.assertTrue(ROUND18_ASSETS_DIR.is_dir())
        alpha_digests: Dict[str, str] = {}
        comp_digests: Dict[str, str] = {}
        for stem in self.EXPECTED_STEMS:
            for variant, bucket in (("alpha", alpha_digests), ("composited", comp_digests)):
                png_path = ROUND18_ASSETS_DIR / f"{stem}-{variant}.png"
                self.assertTrue(png_path.is_file(), f"Missing Round 18 PNG: {png_path}")
                raw = png_path.read_bytes()
                self.assertLess(len(raw), 85 * 1024, f"PNG exceeds 85 KiB: {png_path}")
                w, h, _ = _decode_png_rgba_rows(raw)
                self.assertEqual((w, h), (1024, 540))
                bucket[stem] = hashlib.sha256(raw).hexdigest()
        self.assertEqual(len(set(alpha_digests.values())), len(self.EXPECTED_STEMS))
        self.assertEqual(len(set(comp_digests.values())), len(self.EXPECTED_STEMS))

        for stem, exp_amber in (
            ("r18a-menu-3layer-project-schinese", 1074),
            ("r18b-menu-3layer-tcmedia-schinese", 2430),
            ("r18c-menu-3layer-network-schinese", 0),
            ("r18d-menu-3layer-maintenance-schinese", 0),
        ):
            _, _, rows = _decode_png_rgba_rows((ROUND18_ASSETS_DIR / f"{stem}-alpha.png").read_bytes())
            self.assertEqual(self._count_amber(rows), exp_amber)

    def test_round18_readme_and_no_tmp_scratch_residue(self) -> None:
        closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn("2026-11-14-round18-fx6-on-fx3-menu-8category-closure", closure_readme)
        r18_readme = (ROUND18_REPORT_DIR / "README.md").read_text(encoding="utf-8")
        for tok in ("0x11", "Project", "TC/Media", "Network", "Maintenance", "WF-12", "28/28"):
            self.assertIn(tok, r18_readme)
        for forbidden in ("/Volumes/KAFU2T", "/Users/"):
            self.assertNotIn(forbidden, r18_readme)
        tmp_matches = list(pathlib.Path("/private/tmp").glob("fx6-r18*"))
        self.assertEqual(tmp_matches, [], f"Leftover scratch dirs in /private/tmp: {tmp_matches}")


class TestRound19Menu11CategoryFullSweepClosure(unittest.TestCase):
    EXPECTED_STEMS = (
        "r19a-menu-3layer-user-schinese",
        "r19b-menu-3layer-thumbnail-schinese",
        "r19c-menu-3layer-technical-schinese",
        "r19d-menu-3layer-wraparound-user-schinese",
        "r19e-menu-3layer-network-tchinese",
    )
    EXPECTED_RUN_KEYS = (
        "r19a_menu_3layer_user_schinese",
        "r19b_menu_3layer_thumbnail_schinese",
        "r19c_menu_3layer_technical_schinese",
        "r19d_menu_3layer_wraparound_user_schinese",
        "r19e_menu_3layer_network_tchinese",
    )

    def test_round19_c_source_guards_and_runner_support(self) -> None:
        shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")

        self.assertIn("#if FX6_ROUND >= 19", shim_src)
        for token in (
            "FX6_R19_LANG_TELEMETRY",
            "FX6_STAGE_B_R19_BRIDGE",
            "menu_11cat_fullsweep=1",
            "wf12_00342260_immune=1",
        ):
            self.assertIn(token, shim_src)

        for token in (
            "/etc/fx6_stage_r19",
            "FX6_STAGE_B_R19_VERIFY_PASS",
            "menu_11cat_fullsweep=1",
            "wf12_00342260_immune=1",
        ):
            self.assertIn(token, verify_src)

        for token in (
            "enable_r19",
            "etc/fx6_stage_r19",
            '"r19_telemetry"',
            '"fx6-r19"',
            "choices=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]",
        ):
            self.assertIn(token, runner_src)

    def _assert_r19_overlay_dual_mode(
        self,
        lang: str,
        uxc1_name: str,
        uxc2_name: str,
        ltt_name: str,
        fontlist_key: str,
        asset_key_u1: str,
        asset_key_ltt: str,
        donor_attr_u1: str,
        donor_attr_u2: str,
        donor_attr_ltt: str,
    ) -> None:
        runner = _load_closure_module(
            f"fx6_build_and_run_round_r19_ovl_{lang}", "build_and_run_round.py"
        )
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            parent_cpio = tmp_dir / "parent.cpio"
            init_body = (
                b"#!/bin/sh\n"
                b'LD_PRELOAD="$FX6_PRELOAD" /usr/bin/appfw-launch\n'
            )
            members = (
                ("init", init_body),
                ("usr/lib/libInfraSetupFile.so", b"SETUP"),
                ("usr/lib/libInfraMediaCommon.so", b"MCOMM"),
                ("usr/lib/libInfraMediaConfig.so", b"MCFG"),
                ("usr/lib/libInfraAppRemoteBoard.so", b"RBRD"),
                ("usr/lib/libfan.so", b"FAN"),
                ("usr/lib/appFw.so", b"APPFW"),
                ("usr/lib/libWlanResource.so", b"WLAN_DONOR_12345"),
                ("usr/kmod/upm.ko", b"UPMKO"),
                ("usr/share/app/image_00_169.uxc", b"uxd\x07" + b"C" * 32),
                (f"usr/share/app/{uxc1_name}", b"uxc\x07" + b"C1" * 16),
                (f"usr/share/app/{uxc2_name}", b"uxc\x07" + b"C2" * 16),
                (f"usr/share/app/{ltt_name}", b"LTT\n" + b"CL" * 16),
                (
                    "usr/share/app/fontlist.dat",
                    f"{fontlist_key}\t/usr/share/app/{ltt_name}\t0\t0\n".encode("ascii"),
                ),
            )
            archive = b"".join(
                runner.make_cpio_member(name, body, ino=idx + 1, mode=0o100755)
                for idx, (name, body) in enumerate(members)
            ) + runner.make_cpio_member("TRAILER!!!", b"", ino=0, mode=0)
            parent_cpio.write_bytes(archive)

            class _FakeRes:
                def __init__(self, site_id: str) -> None:
                    self.site_id = site_id

            class _FakeReceipt:
                def __init__(self, before: bytes, after: bytes, sites: list) -> None:
                    self.before_sha256 = hashlib.sha256(before).hexdigest()
                    self.after_sha256 = hashlib.sha256(after).hexdigest()
                    self.changed_byte_count = 8
                    self.resolutions = [_FakeRes(s.site_id) for s in sites]

            class _FakePatcher:
                P1_P4_P8_APPFW_COMBINED_SPEC = mock.Mock(
                    library_name="appFw.so",
                    expected_size=5,
                    donor_sha256="0" * 64,
                    sites=(mock.Mock(site_id="p1"),),
                    elf_kind="so",
                    source_domain="fx6",
                )
                P1_LIB_INFRA_SETUP_FILE_SPEC = mock.Mock(spec_id="P1_s", library_name="s", sites=[mock.Mock(site_id="s1")])
                P1_LIB_INFRA_MEDIA_COMMON_SPEC = mock.Mock(spec_id="P1_c", library_name="c", sites=[mock.Mock(site_id="c1")])
                P1_LIB_INFRA_MEDIA_CONFIG_SPEC = mock.Mock(spec_id="P1_g", library_name="g", sites=[mock.Mock(site_id="g1")])
                P3_LIB_INFRA_APP_REMOTE_BOARD_SPEC = mock.Mock(spec_id="P3_r", library_name="r", sites=[mock.Mock(site_id="r1")])
                FAN_LIBFAN_SPEC = mock.Mock(spec_id="Fan_f", library_name="f", sites=[mock.Mock(site_id="f1")])
                P9_UPM_KO_SPEC = mock.Mock(spec_id="P9_u", library_name="upm.ko", sites=[mock.Mock(site_id="u1")])
                LibraryPatchSpec = lambda **kw: type("FakeSpec", (), kw)()
                PatchSiteSpec = object
                PF_R = 4

                @staticmethod
                def apply_patch_spec(data: bytes, spec: object, verify_donor_sha256: bool = True):
                    after = data + b"_P"
                    return after, _FakeReceipt(data, after, getattr(spec, "sites", []))

                @staticmethod
                def resolve_and_verify_sites(data: bytes, spec: object, expect_patched_state: bool = True):
                    return [_FakeRes("u1")]

            class _FakeVfat:
                @staticmethod
                def build_opelog_vfat_image(mode: str):
                    img = b"VFAT" * 16
                    receipt = mock.Mock(
                        mode=mode,
                        fat_type="FAT16",
                        total_bytes=len(img),
                        sha256=hashlib.sha256(img).hexdigest(),
                        precreated_dirs=("OPE", "OPE/00", "OPE/01"),
                    )
                    return img, receipt

                @staticmethod
                def verify_vfat_image(_img: bytes):
                    return mock.Mock(valid=True, errors=[])

            class _FakeBmtv:
                @staticmethod
                def build_canonical_fa0080_normal_boot_table(donor_seed_bk4_path=None):
                    return b"T"

                @staticmethod
                def synthesize_ram_shadow_bk4(**_kw):
                    bk = b"BK4\x00" + b"\x00" * 12
                    return mock.Mock(
                        bk4_bytes=bk,
                        total_bytes=len(bk),
                        sha256=hashlib.sha256(bk).hexdigest(),
                        flash_write_allowed=False,
                        active_byte8_selector=0,
                        synthesized_key_count=1,
                    )

            fake_p10 = type(
                "FakeP10",
                (),
                {
                    "spec_id": "P10_FX3_TO_FX6_KEYMAP_ADAPTER",
                    "library_name": "appFw.so",
                    "sites": (mock.Mock(site_id="p10_fn", size=4),),
                },
            )()
            fake_p12 = type(
                "FakeP12",
                (),
                {
                    "spec_id": "P12_libWlanResource_fatal_guard",
                    "library_name": "libWlanResource.so",
                    "sites": (mock.Mock(site_id="p12_wlan", size=8),),
                },
            )()

            def _fake_subproc_run(cmd, **_kw):
                out_path = pathlib.Path(cmd[-1])
                out_path.write_bytes(b"ELF_VERIFY_19")
                return mock.Mock(returncode=0, stderr="")

            donor_u1 = tmp_dir / "donor_u1.uxc"
            donor_u2 = tmp_dir / "donor_u2.uxc"
            donor_ltt = tmp_dir / "donor_font.ltt"
            donor_uxc = tmp_dir / "donor_img.uxc"
            donor_u1.write_bytes(b"uxc\x07" + b"D1" * 16)
            donor_u2.write_bytes(b"uxc\x07" + b"D2" * 16)
            donor_ltt.write_bytes(b"LTT\n" + b"FD" * 16)
            donor_uxc.write_bytes(b"uxd\x07" + b"D" * 32)
            build_dir = tmp_dir / "build"

            with mock.patch.object(
                runner, "_import_stage_a_modules", return_value=(_FakePatcher, _FakeVfat, _FakeBmtv)
            ), mock.patch.object(
                runner, "_load_p10_keymap_spec", return_value=fake_p10
            ), mock.patch.object(
                runner, "_load_p12_wlan_spec", return_value=fake_p12
            ), mock.patch.object(
                runner, "DONOR_IMAGE_00_169_UXC", donor_uxc
            ), mock.patch.object(
                runner, donor_attr_u1, donor_u1
            ), mock.patch.object(
                runner, donor_attr_u2, donor_u2
            ), mock.patch.object(
                runner, donor_attr_ltt, donor_ltt
            ), mock.patch.object(
                runner, "FX3_UPM_KO", tmp_dir / "absent_upm.ko"
            ), mock.patch.object(
                runner, "FX3_SEED_BK4", tmp_dir / "absent_seed.bin"
            ), mock.patch.object(
                runner.subprocess, "run", side_effect=_fake_subproc_run
            ):
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
                    rep, add, meta = runner.build_stage_a_overlay(
                        build_dir,
                        parent_cpio,
                        b"BK4_NTSC",
                        enable_p10=True,
                        enable_r10=True,
                        enable_p12=True,
                        enable_r12=True,
                        enable_r13=True,
                        enable_r14=True,
                        enable_r15=True,
                        enable_r16=True,
                        enable_r17=True,
                        enable_r18=True,
                        enable_r19=True,
                        lang=lang,
                        shim_bytes=b"SHIM19",
                    )
                self.assertEqual(meta["manifest_count"], 13)
                self.assertTrue(meta["r18_enabled"])
                self.assertTrue(meta["r19_enabled"])
                self.assertEqual(meta["lang"], lang)
                self.assertIn("etc/fx6_stage_r19", add)
                self.assertIn(
                    f"menu_11cat_fullsweep=1\nlang={lang}\n".encode("utf-8"),
                    add["etc/fx6_stage_r19"][0],
                )
                self.assertEqual(meta["lang_assets"][asset_key_u1]["source"], "cpio_preloaded")
                self.assertEqual(meta["lang_assets"][asset_key_ltt]["source"], "cpio_preloaded")
                self.assertEqual(meta["lang_assets"]["fontlist_dat"]["fontlist_key"], fontlist_key)
                self.assertEqual(rep[f"usr/share/app/{uxc2_name}"], b"uxc\x07" + b"C2" * 16)

                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "0"}):
                    rep2, add2, meta2 = runner.build_stage_a_overlay(
                        build_dir,
                        parent_cpio,
                        b"BK4_NTSC",
                        enable_p10=True,
                        enable_r10=True,
                        enable_p12=True,
                        enable_r12=True,
                        enable_r13=True,
                        enable_r14=True,
                        enable_r15=True,
                        enable_r16=True,
                        enable_r17=True,
                        enable_r18=True,
                        enable_r19=True,
                        lang=lang,
                        shim_bytes=b"SHIM19",
                    )
                self.assertTrue(meta2["r19_enabled"])
                self.assertIn("etc/fx6_stage_r19", add2)
                self.assertEqual(meta2["lang_assets"][asset_key_u1]["source"], "donor_o_rdonly")
                self.assertEqual(rep2[f"usr/share/app/{ltt_name}"], b"LTT\n" + b"FD" * 16)

    def test_round19_stage_a_overlay_schinese_dual_mode(self) -> None:
        self._assert_r19_overlay_dual_mode(
            lang="schinese",
            uxc1_name="string_simplifiedchinese.uxc",
            uxc2_name="string_simplifiedchinese_2.uxc",
            ltt_name="MYingHeiC-GB18030-SJ_wIcon.ltt",
            fontlist_key="FONT_S_CHINESE",
            asset_key_u1="string_simplifiedchinese",
            asset_key_ltt="font_gb18030_ltt",
            donor_attr_u1="DONOR_STRING_SCHINESE_UXC",
            donor_attr_u2="DONOR_STRING_SCHINESE_2_UXC",
            donor_attr_ltt="DONOR_FONT_SCHINESE_LTT",
        )

    def test_round19_stage_a_overlay_tchinese_dual_mode(self) -> None:
        self._assert_r19_overlay_dual_mode(
            lang="tchinese",
            uxc1_name="string_traditionalchinese.uxc",
            uxc2_name="string_traditionalchinese_2.uxc",
            ltt_name="MYingHeiC-Big5HKSCS-SJ_wIcon.ltt",
            fontlist_key="FONT_T_CHINESE",
            asset_key_u1="string_traditionalchinese",
            asset_key_ltt="font_big5hkscs_ltt",
            donor_attr_u1="DONOR_STRING_TCHINESE_UXC",
            donor_attr_u2="DONOR_STRING_TCHINESE_2_UXC",
            donor_attr_ltt="DONOR_FONT_TCHINESE_LTT",
        )

    def test_round19_stage_a_overlay_japanese_dual_mode(self) -> None:
        self._assert_r19_overlay_dual_mode(
            lang="japanese",
            uxc1_name="string_japanese.uxc",
            uxc2_name="string_japanese_2.uxc",
            ltt_name="HeiseiKakuGothW5-SJ_wIcon.ltt",
            fontlist_key="FONT_JAPANESE",
            asset_key_u1="string_japanese",
            asset_key_ltt="font_japanese_ltt",
            donor_attr_u1="DONOR_STRING_JAPANESE_UXC",
            donor_attr_u2="DONOR_STRING_JAPANESE_2_UXC",
            donor_attr_ltt="DONOR_FONT_JAPANESE_LTT",
        )

    def test_round19_stage_a_overlay_english_dual_mode(self) -> None:
        self._assert_r19_overlay_dual_mode(
            lang="english",
            uxc1_name="string_english.uxc",
            uxc2_name="string_english_2.uxc",
            ltt_name="UniversOTS-SJ_wIcon.ltt",
            fontlist_key="FONT_UNIVERS",
            asset_key_u1="string_english",
            asset_key_ltt="font_univers_ltt",
            donor_attr_u1="DONOR_STRING_ENGLISH_UXC",
            donor_attr_u2="DONOR_STRING_ENGLISH_2_UXC",
            donor_attr_ltt="DONOR_FONT_ENGLISH_LTT",
        )

    def test_round19_extract_milestones_telemetry_parser(self) -> None:
        runner = _load_closure_module(
            "fx6_build_and_run_round_r19_ms", "build_and_run_round.py"
        )
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_STAGE_B_R19_VERIFY_PASS count=13 stage_b=1 p10_keymap=1 p11_uipc=1 p12_wlan=1 p4_nd_clear=1 uxc=1 menu_11cat_fullsweep=1 wf12_00342260_immune=1 lang=tchinese",
                "FX6_STAGE_B_R19_BRIDGE round=19 faithful=1 nop_count=0 p12_wlan=1 wf12_00342260_immune=1 p10_keymap=1 p4_nd_clear=1 p11_xlr_h1=1 lang=tchinese bk4_lang=0x18 enum=0x2b44_LANGUAGE_CHINESE_TRADITIONAL font_bank=27 str_bank=22 menu_11cat_fullsweep=1",
                "FX6_R19_LANG_TELEMETRY reason=pump lang=tchinese bk4_lang_id=0x02cf019c bk4_lang_val=0x18 lang_enum=0x2b44_LANGUAGE_CHINESE_TRADITIONAL font_bank=27 str_bank=22 lang_bk4_hits=3 airplane_bk4_hits=0 p4_nd_clear=1 p10_keymap=1 p11_xlr_h1=1 p12_wlan=1 wf12_00342260_immune=1 font_create=18801 glyph_blits=10648 icon_blits=14987 gpe_alloc=223 gpe_fb=0 menu_11cat_fullsweep=1 subst_color=0 subst_image=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        self.assertEqual(ms["prefix_counts"]["FX6_R19_"], 1)
        r19 = ms["r19_telemetry"]
        self.assertIsNotNone(r19)
        self.assertEqual(r19["lang"], "tchinese")
        self.assertEqual(r19["bk4_lang_val"], "0x18")
        self.assertEqual(r19["font_bank"], 27)
        self.assertEqual(r19["str_bank"], 22)
        self.assertEqual(r19["p12_wlan"], 1)
        self.assertEqual(r19["wf12_00342260_immune"], 1)
        self.assertEqual(r19["airplane_bk4_hits"], 0)
        self.assertEqual(r19["gpe_alloc"], 223)
        self.assertEqual(r19["gpe_fb"], 0)
        self.assertEqual(r19["menu_11cat_fullsweep"], 1)
        self.assertEqual(r19["subst_color"], 0)
        self.assertEqual(r19["subst_image"], 0)

    def test_round19_report_and_summary_json_invariants(self) -> None:
        self.assertTrue((ROUND19_REPORT_DIR / "README.md").is_file())
        summary_path = ROUND19_REPORT_DIR / "summary.json"
        self.assertTrue(summary_path.is_file())
        raw_text = summary_path.read_text(encoding="utf-8")
        for forbidden in ("/Volumes/KAFU2T", "/private/tmp", "/Users/"):
            self.assertNotIn(forbidden, raw_text)
        data = json.loads(raw_text)
        self.assertEqual(data["schema"], "fx6-on-fx3-round19-menu-11cat-fullsweep-v1")
        self.assertIn("Linux version 4.9.337-scel+", data["kernel_version"])
        self.assertEqual(set(data["languages"].keys()), {"en", "tchinese", "japanese", "schinese"})

        runs = data["runs"]
        self.assertEqual(set(runs.keys()), set(self.EXPECTED_RUN_KEYS))
        expectations = {
            "r19a_menu_3layer_user_schinese": ("schinese", "0x19", 23, 19, "User", 8, 0, "0x11", "31procam_menu_layer_3rd_presenter", "32procam_menu_layer_3rd_controller", 437575, 254, 1074),
            "r19b_menu_3layer_thumbnail_schinese": ("schinese", "0x19", 23, 19, "Thumbnail", 15, 7, "0x0f", "31procam_menu_layer_1st_presenter", "32procam_menu_layer_1st_controller", 437095, 254, 0),
            "r19c_menu_3layer_technical_schinese": ("schinese", "0x19", 23, 19, "Technical", 16, 8, "0x11", "31procam_menu_layer_3rd_presenter", "32procam_menu_layer_3rd_controller", 437095, 237, 471),
            "r19d_menu_3layer_wraparound_user_schinese": ("schinese", "0x19", 23, 19, "User (Wrap-Around)", 8, 11, "0x11", "31procam_menu_layer_3rd_presenter", "32procam_menu_layer_3rd_controller", 437095, 254, 1074),
            "r19e_menu_3layer_network_tchinese": ("tchinese", "0x18", 27, 22, "Network (Traditional Chinese)", 6, 9, "0x11", "31procam_menu_layer_3rd_presenter", "32procam_menu_layer_3rd_controller", 437575, 265, 0),
        }
        for key, (lang, bk4_val, fbank, sbank, cat, cid, steps, sid, pres, ctrl, exp_px, exp_col, exp_amber) in expectations.items():
            run = runs[key]
            self.assertEqual(run["round"], 19)
            self.assertEqual(run["lang"], lang)
            self.assertEqual(run["menu_category"], cat)
            self.assertEqual(run["cat_id"], cid)
            self.assertEqual(run["rail_down_steps"], steps)
            self.assertEqual(run["target_sid"], sid)
            self.assertEqual(run["target_presenter"], pres)
            self.assertEqual(run["target_controller"], ctrl)
            self.assertEqual(run["nop_count"], 0)
            self.assertEqual(run["crashes"], 0)
            self.assertGreaterEqual(run["ldec103_ioctl_count"], 75)
            self.assertGreaterEqual(run["total_threads_seen"], 161)
            self.assertEqual(
                run["faithful_invariants"],
                {
                    "FX6_NATIVE_FAITHFUL": 1,
                    "subst_color": 0,
                    "subst_image": 0,
                    "forced_render": 0,
                    "skipped_node": 0,
                    "lock_bypass": 0,
                },
            )
            sb = run["stage_b"]
            self.assertTrue(sb["r18_enabled"])
            self.assertTrue(sb["r19_enabled"])
            self.assertEqual(sb["lang"], lang)
            self.assertEqual(sb["manifest_count"], 13)
            self.assertEqual(len(sb["verify_bin_sha256"]), 64)
            self.assertIn("P12_libWlanResource_fatal_guard", sb["patches"])
            self.assertIn("P10_FX3_TO_FX6_KEYMAP_ADAPTER", sb["patches"])
            self.assertIn(
                "P4_appfw_set_nd_filter_mode_clear",
                sb["patches"]["P1_P4_P8_P10_appFw_combined"]["sites"],
            )
            self.assertGreaterEqual(run["prefix_counts"]["FX6_STAGE_A_"], 21)
            self.assertGreaterEqual(run["prefix_counts"]["FX6_STAGE_B_"], 26)
            self.assertGreaterEqual(run["prefix_counts"]["FX6_R19_"], 180)
            telem = run["r19_telemetry"]
            self.assertEqual(telem["p4_nd_clear"], 1)
            self.assertEqual(telem["p10_keymap"], 1)
            self.assertEqual(telem["p11_xlr_h1"], 1)
            self.assertEqual(telem["lang"], lang)
            self.assertEqual(telem["bk4_lang_val"], bk4_val)
            self.assertEqual(telem["font_bank"], fbank)
            self.assertEqual(telem["str_bank"], sbank)
            self.assertEqual(telem["airplane_bk4_hits"], 0)
            self.assertEqual(telem["p12_wlan"], 1)
            self.assertEqual(telem["wf12_00342260_immune"], 1)
            self.assertEqual(telem["gpe_fb"], 0)
            self.assertEqual(telem["menu_11cat_fullsweep"], 1)
            self.assertEqual(telem["subst_color"], 0)
            self.assertEqual(telem["subst_image"], 0)
            self.assertEqual(run["gpe0_readback"]["nonzero_pixels"], exp_px)
            self.assertEqual(run["gpe0_readback"]["unique_colors"], exp_col)
            self.assertEqual(run["amber_0xffffaa00_pixels"], exp_amber)

    def test_round19_stage_b_manifest_13_sha256_integrity(self) -> None:
        data = json.loads((ROUND19_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        shared_by_path: Dict[str, str] = {}
        for key in self.EXPECTED_RUN_KEYS:
            items = data["runs"][key]["stage_b"]["manifest_items"]
            self.assertEqual(len(items), 13)
            for item in items:
                gpath = item["guest_path"]
                digest = item["sha256"]
                self.assertEqual(len(digest), 64)
                int(digest, 16)
                if gpath == "/usr/lib/libgrm-fbinit9.so":
                    continue
                if gpath in shared_by_path:
                    self.assertEqual(shared_by_path[gpath], digest, f"SHA mismatch on {gpath}")
                else:
                    shared_by_path[gpath] = digest
        self.assertEqual(len(shared_by_path), 12)

    def test_round19_full_menu_l1_rail_11cat_contract(self) -> None:
        data = json.loads((ROUND19_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        rail = data["full_menu_l1_rail_contract"]
        self.assertEqual(rail["table_offset"], "appFw.so+0x2924180")
        self.assertEqual(rail["entry_stride_bytes"], 48)
        cats = rail["rail_categories_visible_in_shooting_mode"]
        self.assertEqual(len(cats), 11)
        for c in cats:
            self.assertIn("verified_run", c)
            self.assertNotEqual(c["verified_run"], "r11d_entry")
        by_name = {c["category"]: c for c in cats}
        self.assertEqual(by_name["User"]["verified_run"], "r19a-menu-3layer-user-schinese")
        self.assertEqual(by_name["User"]["wraparound_verified_run"], "r19d-menu-3layer-wraparound-user-schinese")
        self.assertEqual(by_name["Thumbnail"]["verified_run"], "r19b-menu-3layer-thumbnail-schinese")
        self.assertEqual(by_name["Technical"]["verified_run"], "r19c-menu-3layer-technical-schinese")
        self.assertEqual(by_name["Network"]["tchinese_verified_run"], "r19e-menu-3layer-network-tchinese")

    @staticmethod
    def _diff_rows(ra: List[bytes], rb: List[bytes]) -> int:
        import operator
        ne = operator.ne
        return sum(
            sum(map(ne, memoryview(ya).cast("I"), memoryview(yb).cast("I")))
            for ya, yb in zip(ra, rb)
            if ya != yb
        )

    @staticmethod
    def _count_amber(rows: List[bytes]) -> int:
        amber_word = int.from_bytes(b"\xff\xaa\x00\xff", sys.byteorder)
        return sum(
            sum(1 for px in memoryview(row).cast("I") if px == amber_word)
            for row in rows
            if b"\xff\xaa\x00\xff" in row
        )

    def test_round19_menu_11cat_schinese_55pairs_pixel_deltas_exact(self) -> None:
        data = json.loads((ROUND19_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        audit = data["r19_menu_11cat_fullsweep_audit"]["menu_11cat_schinese_pairwise"]
        self.assertEqual(audit["category_count"], 11)
        self.assertEqual(audit["pair_count"], 55)
        self.assertTrue(audit["all_55_category_pairs_strictly_positive"])
        self.assertEqual(audit["min_diff_pixels"], 1552)
        self.assertEqual(audit["max_diff_pixels"], 177650)

        cat_paths = {
            "user": ROUND19_ASSETS_DIR / "r19a-menu-3layer-user-schinese-alpha.png",
            "shooting": ROUND11_ASSETS_DIR / "r11d-c2-menu-3layer-schinese-alpha.png",
            "project": ROUND18_ASSETS_DIR / "r18a-menu-3layer-project-schinese-alpha.png",
            "paint_look": ROUND13_ASSETS_DIR / "r13c-menu-3layer-paintlook-schinese-alpha.png",
            "tc_media": ROUND18_ASSETS_DIR / "r18b-menu-3layer-tcmedia-schinese-alpha.png",
            "monitoring": ROUND15_ASSETS_DIR / "r15c-menu-3layer-monitoring-schinese-alpha.png",
            "audio": ROUND17_ASSETS_DIR / "r17d-menu-3layer-audio-schinese-alpha.png",
            "thumbnail": ROUND19_ASSETS_DIR / "r19b-menu-3layer-thumbnail-schinese-alpha.png",
            "technical": ROUND19_ASSETS_DIR / "r19c-menu-3layer-technical-schinese-alpha.png",
            "network": ROUND18_ASSETS_DIR / "r18c-menu-3layer-network-schinese-alpha.png",
            "maintenance": ROUND18_ASSETS_DIR / "r18d-menu-3layer-maintenance-schinese-alpha.png",
        }
        rows = {k: _decode_png_rgba_rows(p.read_bytes())[2] for k, p in cat_paths.items()}
        cat_keys = list(cat_paths.keys())
        pairs = audit["pairs"]
        self.assertEqual(len(pairs), 55)
        for i in range(len(cat_keys)):
            for j in range(i + 1, len(cat_keys)):
                ka, kb = cat_keys[i], cat_keys[j]
                pkey = f"{ka}_vs_{kb}"
                entry = pairs[pkey]
                self.assertTrue(entry["strictly_positive"])
                diff = self._diff_rows(rows[ka], rows[kb])
                self.assertGreater(diff, 0)
                self.assertEqual(diff, entry["diff_pixels"])

    def test_round19_menu_11down_wraparound_to_user_proof(self) -> None:
        data = json.loads((ROUND19_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        wrap = data["r19_menu_11cat_fullsweep_audit"]["menu_11down_wraparound_proof"]
        self.assertEqual(wrap["run_key"], "r19d_menu_3layer_wraparound_user_schinese")
        self.assertEqual(wrap["step_count_down"], 11)
        self.assertEqual(wrap["cat_id"], 8)
        self.assertEqual(wrap["target_sid"], "0x11")
        self.assertEqual(wrap["target_presenter"], "31procam_menu_layer_3rd_presenter")
        self.assertEqual(wrap["diff_vs_r19a_user_pixels"], 480)
        self.assertTrue(wrap["all_non_user_diffs_strictly_positive"])

        rows_wrap = _decode_png_rgba_rows(
            (ROUND19_ASSETS_DIR / "r19d-menu-3layer-wraparound-user-schinese-alpha.png").read_bytes()
        )[2]
        cat_paths = {
            "user": ROUND19_ASSETS_DIR / "r19a-menu-3layer-user-schinese-alpha.png",
            "shooting": ROUND11_ASSETS_DIR / "r11d-c2-menu-3layer-schinese-alpha.png",
            "project": ROUND18_ASSETS_DIR / "r18a-menu-3layer-project-schinese-alpha.png",
            "paint_look": ROUND13_ASSETS_DIR / "r13c-menu-3layer-paintlook-schinese-alpha.png",
            "tc_media": ROUND18_ASSETS_DIR / "r18b-menu-3layer-tcmedia-schinese-alpha.png",
            "monitoring": ROUND15_ASSETS_DIR / "r15c-menu-3layer-monitoring-schinese-alpha.png",
            "audio": ROUND17_ASSETS_DIR / "r17d-menu-3layer-audio-schinese-alpha.png",
            "thumbnail": ROUND19_ASSETS_DIR / "r19b-menu-3layer-thumbnail-schinese-alpha.png",
            "technical": ROUND19_ASSETS_DIR / "r19c-menu-3layer-technical-schinese-alpha.png",
            "network": ROUND18_ASSETS_DIR / "r18c-menu-3layer-network-schinese-alpha.png",
            "maintenance": ROUND18_ASSETS_DIR / "r18d-menu-3layer-maintenance-schinese-alpha.png",
        }
        wdict = wrap["wrap_diffs_vs_all_11_categories"]
        self.assertEqual(len(wdict), 11)
        for k, p in cat_paths.items():
            diff = self._diff_rows(rows_wrap, _decode_png_rgba_rows(p.read_bytes())[2])
            self.assertEqual(diff, wdict[f"wrap_vs_{k}"])
            if k != "user":
                self.assertGreater(diff, 0)

    def test_round19_network_tchinese_vs_schinese_delta_exact(self) -> None:
        data = json.loads((ROUND19_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        cross = data["r19_menu_11cat_fullsweep_audit"]["network_tchinese_vs_schinese_delta"]
        self.assertTrue(cross["strictly_positive"])
        self.assertEqual(cross["diff_pixels"], 19652)
        rows_tc = _decode_png_rgba_rows(
            (ROUND19_ASSETS_DIR / "r19e-menu-3layer-network-tchinese-alpha.png").read_bytes()
        )[2]
        rows_sc = _decode_png_rgba_rows(
            (ROUND18_ASSETS_DIR / "r18c-menu-3layer-network-schinese-alpha.png").read_bytes()
        )[2]
        diff = self._diff_rows(rows_tc, rows_sc)
        self.assertGreater(diff, 0)
        self.assertEqual(diff, 19652)

    def test_round19_wf12_00342260_network_tchinese_immunity(self) -> None:
        data = json.loads((ROUND19_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        wf12 = data["r19_menu_11cat_fullsweep_audit"]["wf12_00342260_network_tchinese_immunity"]
        self.assertEqual(wf12["run_key"], "r19e_menu_3layer_network_tchinese")
        self.assertEqual(wf12["lang"], "tchinese")
        self.assertEqual(wf12["bk4_lang_val"], "0x18")
        self.assertEqual(wf12["font_bank"], 27)
        self.assertEqual(wf12["str_bank"], 22)
        self.assertEqual(wf12["target_sid"], "0x11")
        self.assertEqual(wf12["target_presenter"], "31procam_menu_layer_3rd_presenter")
        self.assertEqual(wf12["menu_category"], "Network")
        self.assertEqual(wf12["p12_wlan"], 1)
        self.assertEqual(wf12["wf12_00342260_immune"], 1)
        self.assertEqual(wf12["airplane_bk4_hits"], 0)
        self.assertEqual(wf12["nop_count"], 0)
        self.assertEqual(wf12["crashes"], 0)
        self.assertEqual(wf12["gpe_fb"], 0)

    def test_round19_png_receipts_valid_under_85kib_and_amber(self) -> None:
        self.assertTrue(ROUND19_ASSETS_DIR.is_dir())
        alpha_digests: Dict[str, str] = {}
        comp_digests: Dict[str, str] = {}
        for stem in self.EXPECTED_STEMS:
            for variant, bucket in (("alpha", alpha_digests), ("composited", comp_digests)):
                png_path = ROUND19_ASSETS_DIR / f"{stem}-{variant}.png"
                self.assertTrue(png_path.is_file(), f"Missing Round 19 PNG: {png_path}")
                raw = png_path.read_bytes()
                self.assertLess(len(raw), 85 * 1024, f"PNG exceeds 85 KiB: {png_path}")
                w, h, _ = _decode_png_rgba_rows(raw)
                self.assertEqual((w, h), (1024, 540))
                bucket[stem] = hashlib.sha256(raw).hexdigest()
        self.assertEqual(len(set(alpha_digests.values())), len(self.EXPECTED_STEMS))
        self.assertEqual(len(set(comp_digests.values())), len(self.EXPECTED_STEMS))

        for stem, exp_amber in (
            ("r19a-menu-3layer-user-schinese", 1074),
            ("r19b-menu-3layer-thumbnail-schinese", 0),
            ("r19c-menu-3layer-technical-schinese", 471),
            ("r19d-menu-3layer-wraparound-user-schinese", 1074),
            ("r19e-menu-3layer-network-tchinese", 0),
        ):
            _, _, rows = _decode_png_rgba_rows((ROUND19_ASSETS_DIR / f"{stem}-alpha.png").read_bytes())
            self.assertEqual(self._count_amber(rows), exp_amber)

    def test_round19_readme_and_no_tmp_scratch_residue(self) -> None:
        closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn("2026-11-14-round19-fx6-on-fx3-menu-11cat-fullsweep", closure_readme)
        r19_readme = (ROUND19_REPORT_DIR / "README.md").read_text(encoding="utf-8")
        for tok in ("0x11", "User", "Thumbnail", "Technical", "Network", "WF-12", "55/55"):
            self.assertIn(tok, r19_readme)
        for forbidden in ("/Volumes/KAFU2T", "/Users/"):
            self.assertNotIn(forbidden, r19_readme)
        tmp_matches = list(pathlib.Path("/private/tmp").glob("fx6-r19*"))
        self.assertEqual(tmp_matches, [], f"Leftover scratch dirs in /private/tmp: {tmp_matches}")


class TestRound20Network4LangWF12Closure(unittest.TestCase):
    EXPECTED_STEMS = (
        "r20a-menu-3layer-network-english",
        "r20b-menu-3layer-network-japanese",
        "r20c-status-tab9-network-english",
        "r20d-status-tab9-network-japanese",
        "r20e-status-tab9-network-tchinese",
    )
    EXPECTED_RUN_KEYS = (
        "r20a_menu_3layer_network_english",
        "r20b_menu_3layer_network_japanese",
        "r20c_status_tab9_network_english",
        "r20d_status_tab9_network_japanese",
        "r20e_status_tab9_network_tchinese",
    )

    def test_round20_c_source_guards_and_runner_support(self) -> None:
        shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")

        self.assertIn("#if FX6_ROUND >= 20", shim_src)
        for token in (
            "FX6_R20_LANG_TELEMETRY",
            "FX6_STAGE_B_R20_BRIDGE",
            "network_4lang_wf12_closure=1",
            "wf12_00342260_immune=1",
        ):
            self.assertIn(token, shim_src)

        for token in (
            "/etc/fx6_stage_r20",
            "FX6_STAGE_B_R20_VERIFY_PASS",
            "network_4lang_wf12_closure=1",
            "wf12_00342260_immune=1",
        ):
            self.assertIn(token, verify_src)

        for token in (
            "enable_r20",
            "etc/fx6_stage_r20",
            '"r20_telemetry"',
            '"fx6-r20"',
            "choices=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]",
        ):
            self.assertIn(token, runner_src)

    def _assert_r20_overlay_dual_mode(
        self,
        lang: str,
        uxc1_name: str,
        uxc2_name: str,
        ltt_name: str,
        fontlist_key: str,
        asset_key_u1: str,
        asset_key_ltt: str,
        donor_attr_u1: str,
        donor_attr_u2: str,
        donor_attr_ltt: str,
    ) -> None:
        runner = _load_closure_module(
            f"fx6_build_and_run_round_r20_ovl_{lang}", "build_and_run_round.py"
        )
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            parent_cpio = tmp_dir / "parent.cpio"
            init_body = (
                b"#!/bin/sh\n"
                b'LD_PRELOAD="$FX6_PRELOAD" /usr/bin/appfw-launch\n'
            )
            members = (
                ("init", init_body),
                ("usr/lib/libInfraSetupFile.so", b"SETUP"),
                ("usr/lib/libInfraMediaCommon.so", b"MCOMM"),
                ("usr/lib/libInfraMediaConfig.so", b"MCFG"),
                ("usr/lib/libInfraAppRemoteBoard.so", b"RBRD"),
                ("usr/lib/libfan.so", b"FAN"),
                ("usr/lib/appFw.so", b"APPFW"),
                ("usr/lib/libWlanResource.so", b"WLAN_DONOR_12345"),
                ("usr/kmod/upm.ko", b"UPMKO"),
                ("usr/share/app/image_00_169.uxc", b"uxd\x07" + b"C" * 32),
                (f"usr/share/app/{uxc1_name}", b"uxc\x07" + b"C1" * 16),
                (f"usr/share/app/{uxc2_name}", b"uxc\x07" + b"C2" * 16),
                (f"usr/share/app/{ltt_name}", b"LTT\n" + b"CL" * 16),
                (
                    "usr/share/app/fontlist.dat",
                    f"{fontlist_key}\t/usr/share/app/{ltt_name}\t0\t0\n".encode("ascii"),
                ),
            )
            archive = b"".join(
                runner.make_cpio_member(name, body, ino=idx + 1, mode=0o100755)
                for idx, (name, body) in enumerate(members)
            ) + runner.make_cpio_member("TRAILER!!!", b"", ino=0, mode=0)
            parent_cpio.write_bytes(archive)

            class _FakeRes:
                def __init__(self, site_id: str) -> None:
                    self.site_id = site_id

            class _FakeReceipt:
                def __init__(self, before: bytes, after: bytes, sites: list) -> None:
                    self.before_sha256 = hashlib.sha256(before).hexdigest()
                    self.after_sha256 = hashlib.sha256(after).hexdigest()
                    self.changed_byte_count = 8
                    self.resolutions = [_FakeRes(s.site_id) for s in sites]

            class _FakePatcher:
                P1_P4_P8_APPFW_COMBINED_SPEC = mock.Mock(
                    library_name="appFw.so",
                    expected_size=5,
                    donor_sha256="0" * 64,
                    sites=(mock.Mock(site_id="p1"),),
                    elf_kind="so",
                    source_domain="fx6",
                )
                P1_LIB_INFRA_SETUP_FILE_SPEC = mock.Mock(spec_id="P1_s", library_name="s", sites=[mock.Mock(site_id="s1")])
                P1_LIB_INFRA_MEDIA_COMMON_SPEC = mock.Mock(spec_id="P1_c", library_name="c", sites=[mock.Mock(site_id="c1")])
                P1_LIB_INFRA_MEDIA_CONFIG_SPEC = mock.Mock(spec_id="P1_g", library_name="g", sites=[mock.Mock(site_id="g1")])
                P3_LIB_INFRA_APP_REMOTE_BOARD_SPEC = mock.Mock(spec_id="P3_r", library_name="r", sites=[mock.Mock(site_id="r1")])
                FAN_LIBFAN_SPEC = mock.Mock(spec_id="Fan_f", library_name="f", sites=[mock.Mock(site_id="f1")])
                P9_UPM_KO_SPEC = mock.Mock(spec_id="P9_u", library_name="upm.ko", sites=[mock.Mock(site_id="u1")])
                LibraryPatchSpec = lambda **kw: type("FakeSpec", (), kw)()
                PatchSiteSpec = object
                PF_R = 4

                @staticmethod
                def apply_patch_spec(data: bytes, spec: object, verify_donor_sha256: bool = True):
                    after = data + b"_P"
                    return after, _FakeReceipt(data, after, getattr(spec, "sites", []))

                @staticmethod
                def resolve_and_verify_sites(data: bytes, spec: object, expect_patched_state: bool = True):
                    return [_FakeRes("u1")]

            class _FakeVfat:
                @staticmethod
                def build_opelog_vfat_image(mode: str):
                    img = b"VFAT" * 16
                    receipt = mock.Mock(
                        mode=mode,
                        fat_type="FAT16",
                        total_bytes=len(img),
                        sha256=hashlib.sha256(img).hexdigest(),
                        precreated_dirs=("OPE", "OPE/00", "OPE/01"),
                    )
                    return img, receipt

                @staticmethod
                def verify_vfat_image(_img: bytes):
                    return mock.Mock(valid=True, errors=[])

            class _FakeBmtv:
                @staticmethod
                def build_canonical_fa0080_normal_boot_table(donor_seed_bk4_path=None):
                    return b"T"

                @staticmethod
                def synthesize_ram_shadow_bk4(**_kw):
                    bk = b"BK4\x00" + b"\x00" * 12
                    return mock.Mock(
                        bk4_bytes=bk,
                        total_bytes=len(bk),
                        sha256=hashlib.sha256(bk).hexdigest(),
                        flash_write_allowed=False,
                        active_byte8_selector=0,
                        synthesized_key_count=1,
                    )

            fake_p10 = type(
                "FakeP10",
                (),
                {
                    "spec_id": "P10_FX3_TO_FX6_KEYMAP_ADAPTER",
                    "library_name": "appFw.so",
                    "sites": (mock.Mock(site_id="p10_fn", size=4),),
                },
            )()
            fake_p12 = type(
                "FakeP12",
                (),
                {
                    "spec_id": "P12_libWlanResource_fatal_guard",
                    "library_name": "libWlanResource.so",
                    "sites": (mock.Mock(site_id="p12_wlan", size=8),),
                },
            )()

            def _fake_subproc_run(cmd, **_kw):
                out_path = pathlib.Path(cmd[-1])
                out_path.write_bytes(b"ELF_VERIFY_20")
                return mock.Mock(returncode=0, stderr="")

            donor_u1 = tmp_dir / "donor_u1.uxc"
            donor_u2 = tmp_dir / "donor_u2.uxc"
            donor_ltt = tmp_dir / "donor_font.ltt"
            donor_uxc = tmp_dir / "donor_img.uxc"
            donor_u1.write_bytes(b"uxc\x07" + b"D1" * 16)
            donor_u2.write_bytes(b"uxc\x07" + b"D2" * 16)
            donor_ltt.write_bytes(b"LTT\n" + b"FD" * 16)
            donor_uxc.write_bytes(b"uxd\x07" + b"D" * 32)
            build_dir = tmp_dir / "build"

            with mock.patch.object(
                runner, "_import_stage_a_modules", return_value=(_FakePatcher, _FakeVfat, _FakeBmtv)
            ), mock.patch.object(
                runner, "_load_p10_keymap_spec", return_value=fake_p10
            ), mock.patch.object(
                runner, "_load_p12_wlan_spec", return_value=fake_p12
            ), mock.patch.object(
                runner, "DONOR_IMAGE_00_169_UXC", donor_uxc
            ), mock.patch.object(
                runner, donor_attr_u1, donor_u1
            ), mock.patch.object(
                runner, donor_attr_u2, donor_u2
            ), mock.patch.object(
                runner, donor_attr_ltt, donor_ltt
            ), mock.patch.object(
                runner, "FX3_UPM_KO", tmp_dir / "absent_upm.ko"
            ), mock.patch.object(
                runner, "FX3_SEED_BK4", tmp_dir / "absent_seed.bin"
            ), mock.patch.object(
                runner.subprocess, "run", side_effect=_fake_subproc_run
            ):
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
                    rep, add, meta = runner.build_stage_a_overlay(
                        build_dir,
                        parent_cpio,
                        b"BK4_NTSC",
                        enable_p10=True,
                        enable_r10=True,
                        enable_p12=True,
                        enable_r12=True,
                        enable_r13=True,
                        enable_r14=True,
                        enable_r15=True,
                        enable_r16=True,
                        enable_r17=True,
                        enable_r18=True,
                        enable_r19=True,
                        enable_r20=True,
                        lang=lang,
                        shim_bytes=b"SHIM20",
                    )
                self.assertEqual(meta["manifest_count"], 13)
                self.assertTrue(meta["r19_enabled"])
                self.assertTrue(meta["r20_enabled"])
                self.assertEqual(meta["lang"], lang)
                self.assertIn("etc/fx6_stage_r20", add)
                self.assertIn(
                    f"network_4lang_wf12_closure=1\nlang={lang}\n".encode("utf-8"),
                    add["etc/fx6_stage_r20"][0],
                )
                self.assertEqual(meta["lang_assets"][asset_key_u1]["source"], "cpio_preloaded")
                self.assertEqual(meta["lang_assets"][asset_key_ltt]["source"], "cpio_preloaded")
                self.assertEqual(meta["image_00_169_uxc"]["source"], "cpio_preloaded")
                self.assertEqual(meta["lang_assets"]["fontlist_dat"]["fontlist_key"], fontlist_key)
                self.assertEqual(rep[f"usr/share/app/{uxc2_name}"], b"uxc\x07" + b"C2" * 16)

                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "0"}):
                    rep2, add2, meta2 = runner.build_stage_a_overlay(
                        build_dir,
                        parent_cpio,
                        b"BK4_NTSC",
                        enable_p10=True,
                        enable_r10=True,
                        enable_p12=True,
                        enable_r12=True,
                        enable_r13=True,
                        enable_r14=True,
                        enable_r15=True,
                        enable_r16=True,
                        enable_r17=True,
                        enable_r18=True,
                        enable_r19=True,
                        enable_r20=True,
                        lang=lang,
                        shim_bytes=b"SHIM20",
                    )
                self.assertTrue(meta2["r20_enabled"])
                self.assertIn("etc/fx6_stage_r20", add2)
                self.assertEqual(meta2["lang_assets"][asset_key_u1]["source"], "donor_o_rdonly")
                self.assertEqual(meta2["image_00_169_uxc"]["source"], "donor_o_rdonly")
                self.assertEqual(rep2[f"usr/share/app/{ltt_name}"], b"LTT\n" + b"FD" * 16)

    def test_round20_stage_a_overlay_schinese_dual_mode(self) -> None:
        self._assert_r20_overlay_dual_mode(
            lang="schinese",
            uxc1_name="string_simplifiedchinese.uxc",
            uxc2_name="string_simplifiedchinese_2.uxc",
            ltt_name="MYingHeiC-GB18030-SJ_wIcon.ltt",
            fontlist_key="FONT_S_CHINESE",
            asset_key_u1="string_simplifiedchinese",
            asset_key_ltt="font_gb18030_ltt",
            donor_attr_u1="DONOR_STRING_SCHINESE_UXC",
            donor_attr_u2="DONOR_STRING_SCHINESE_2_UXC",
            donor_attr_ltt="DONOR_FONT_SCHINESE_LTT",
        )

    def test_round20_stage_a_overlay_tchinese_dual_mode(self) -> None:
        self._assert_r20_overlay_dual_mode(
            lang="tchinese",
            uxc1_name="string_traditionalchinese.uxc",
            uxc2_name="string_traditionalchinese_2.uxc",
            ltt_name="MYingHeiC-Big5HKSCS-SJ_wIcon.ltt",
            fontlist_key="FONT_T_CHINESE",
            asset_key_u1="string_traditionalchinese",
            asset_key_ltt="font_big5hkscs_ltt",
            donor_attr_u1="DONOR_STRING_TCHINESE_UXC",
            donor_attr_u2="DONOR_STRING_TCHINESE_2_UXC",
            donor_attr_ltt="DONOR_FONT_TCHINESE_LTT",
        )

    def test_round20_stage_a_overlay_japanese_dual_mode(self) -> None:
        self._assert_r20_overlay_dual_mode(
            lang="japanese",
            uxc1_name="string_japanese.uxc",
            uxc2_name="string_japanese_2.uxc",
            ltt_name="HeiseiKakuGothW5-SJ_wIcon.ltt",
            fontlist_key="FONT_JAPANESE",
            asset_key_u1="string_japanese",
            asset_key_ltt="font_japanese_ltt",
            donor_attr_u1="DONOR_STRING_JAPANESE_UXC",
            donor_attr_u2="DONOR_STRING_JAPANESE_2_UXC",
            donor_attr_ltt="DONOR_FONT_JAPANESE_LTT",
        )

    def test_round20_stage_a_overlay_english_dual_mode(self) -> None:
        self._assert_r20_overlay_dual_mode(
            lang="english",
            uxc1_name="string_english.uxc",
            uxc2_name="string_english_2.uxc",
            ltt_name="UniversOTS-SJ_wIcon.ltt",
            fontlist_key="FONT_UNIVERS",
            asset_key_u1="string_english",
            asset_key_ltt="font_univers_ltt",
            donor_attr_u1="DONOR_STRING_ENGLISH_UXC",
            donor_attr_u2="DONOR_STRING_ENGLISH_2_UXC",
            donor_attr_ltt="DONOR_FONT_ENGLISH_LTT",
        )

    def test_round20_extract_milestones_telemetry_parser(self) -> None:
        runner = _load_closure_module(
            "fx6_build_and_run_round_r20_ms", "build_and_run_round.py"
        )
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_STAGE_B_R20_VERIFY_PASS count=13 stage_b=1 p10_keymap=1 p11_uipc=1 p12_wlan=1 p4_nd_clear=1 uxc=1 network_4lang_wf12_closure=1 wf12_00342260_immune=1 lang=english",
                "FX6_STAGE_B_R20_BRIDGE round=20 faithful=1 nop_count=0 p12_wlan=1 wf12_00342260_immune=1 p10_keymap=1 p4_nd_clear=1 p11_xlr_h1=1 lang=english bk4_lang=0x00 enum=0x2b2f_LANGUAGE_ENGLISH font_bank=0 str_bank=4 network_4lang_wf12_closure=1",
                "FX6_R20_LANG_TELEMETRY reason=pump lang=english bk4_lang_id=0x02cf019c bk4_lang_val=0x00 lang_enum=0x2b2f_LANGUAGE_ENGLISH font_bank=0 str_bank=4 lang_bk4_hits=3 airplane_bk4_hits=0 p4_nd_clear=1 p10_keymap=1 p11_xlr_h1=1 p12_wlan=1 wf12_00342260_immune=1 font_create=19459 glyph_blits=10783 icon_blits=15201 gpe_alloc=223 gpe_fb=0 network_4lang_wf12_closure=1 subst_color=0 subst_image=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        self.assertEqual(ms["prefix_counts"]["FX6_R20_"], 1)
        r20 = ms["r20_telemetry"]
        self.assertIsNotNone(r20)
        self.assertEqual(r20["lang"], "english")
        self.assertEqual(r20["bk4_lang_val"], "0x00")
        self.assertEqual(r20["font_bank"], 0)
        self.assertEqual(r20["str_bank"], 4)
        self.assertEqual(r20["p12_wlan"], 1)
        self.assertEqual(r20["wf12_00342260_immune"], 1)
        self.assertEqual(r20["airplane_bk4_hits"], 0)
        self.assertEqual(r20["gpe_alloc"], 223)
        self.assertEqual(r20["gpe_fb"], 0)
        self.assertEqual(r20["network_4lang_wf12_closure"], 1)
        self.assertEqual(r20["subst_color"], 0)
        self.assertEqual(r20["subst_image"], 0)

    def test_round20_report_and_summary_json_invariants(self) -> None:
        self.assertTrue((ROUND20_REPORT_DIR / "README.md").is_file())
        summary_path = ROUND20_REPORT_DIR / "summary.json"
        self.assertTrue(summary_path.is_file())
        raw_text = summary_path.read_text(encoding="utf-8")
        for forbidden in ("/Volumes/KAFU2T", "/private/tmp", "/Users/"):
            self.assertNotIn(forbidden, raw_text)
        data = json.loads(raw_text)
        self.assertEqual(data["schema"], "fx6-on-fx3-round20-network-4lang-wf12-closure-v1")
        self.assertIn("Linux version 4.9.337-scel+", data["kernel_version"])
        self.assertEqual(set(data["languages"].keys()), {"en", "tchinese", "japanese", "schinese"})

        runs = data["runs"]
        self.assertEqual(set(runs.keys()), set(self.EXPECTED_RUN_KEYS))
        expectations = {
            "r20a_menu_3layer_network_english": ("english", "0x00", 0, 4, "network_3layer_menu", "0x11", "31procam_menu_layer_3rd_presenter", "32procam_menu_layer_3rd_controller", 437095, 237, 0),
            "r20b_menu_3layer_network_japanese": ("japanese", "0x01", 1, 12, "network_3layer_menu", "0x11", "31procam_menu_layer_3rd_presenter", "32procam_menu_layer_3rd_controller", 437095, 250, 0),
            "r20c_status_tab9_network_english": ("english", "0x00", 0, 4, "status_check_tab9_network", "0x37", "37procam_touch_status_network_presenter", "38procam_touch_status_network_controller", 437403, 92, 324),
            "r20d_status_tab9_network_japanese": ("japanese", "0x01", 1, 12, "status_check_tab9_network", "0x37", "37procam_touch_status_network_presenter", "38procam_touch_status_network_controller", 437403, 92, 273),
            "r20e_status_tab9_network_tchinese": ("tchinese", "0x18", 27, 22, "status_check_tab9_network", "0x37", "37procam_touch_status_network_presenter", "38procam_touch_status_network_controller", 437883, 92, 273),
        }
        for key, (lang, bk4_val, fbank, sbank, surf, sid, pres, ctrl, exp_px, exp_col, exp_amber) in expectations.items():
            run = runs[key]
            self.assertEqual(run["round"], 20)
            self.assertEqual(run["lang"], lang)
            self.assertEqual(run["surface"], surf)
            self.assertEqual(run["target_sid"], sid)
            self.assertEqual(run["target_presenter"], pres)
            self.assertEqual(run["target_controller"], ctrl)
            self.assertEqual(run["nop_count"], 0)
            self.assertEqual(run["crashes"], 0)
            self.assertGreaterEqual(run["ldec103_ioctl_count"], 60)
            self.assertGreaterEqual(run["total_threads_seen"], 161)
            self.assertEqual(
                run["faithful_invariants"],
                {
                    "FX6_NATIVE_FAITHFUL": 1,
                    "subst_color": 0,
                    "subst_image": 0,
                    "forced_render": 0,
                    "skipped_node": 0,
                    "lock_bypass": 0,
                },
            )
            sb = run["stage_b"]
            self.assertTrue(sb["r19_enabled"])
            self.assertTrue(sb["r20_enabled"])
            self.assertEqual(sb["lang"], lang)
            self.assertEqual(sb["manifest_count"], 13)
            self.assertEqual(len(sb["verify_bin_sha256"]), 64)
            self.assertIn("P12_libWlanResource_fatal_guard", sb["patches"])
            self.assertIn("P10_FX3_TO_FX6_KEYMAP_ADAPTER", sb["patches"])
            self.assertIn(
                "P4_appfw_set_nd_filter_mode_clear",
                sb["patches"]["P1_P4_P8_P10_appFw_combined"]["sites"],
            )
            self.assertGreaterEqual(run["prefix_counts"]["FX6_STAGE_A_"], 21)
            self.assertGreaterEqual(run["prefix_counts"]["FX6_STAGE_B_"], 26)
            self.assertGreaterEqual(run["prefix_counts"]["FX6_R20_"], 200)
            telem = run["r20_telemetry"]
            self.assertEqual(telem["p4_nd_clear"], 1)
            self.assertEqual(telem["p10_keymap"], 1)
            self.assertEqual(telem["p11_xlr_h1"], 1)
            self.assertEqual(telem["lang"], lang)
            self.assertEqual(telem["bk4_lang_val"], bk4_val)
            self.assertEqual(telem["font_bank"], fbank)
            self.assertEqual(telem["str_bank"], sbank)
            self.assertEqual(telem["airplane_bk4_hits"], 0)
            self.assertEqual(telem["p12_wlan"], 1)
            self.assertEqual(telem["wf12_00342260_immune"], 1)
            self.assertEqual(telem["gpe_fb"], 0)
            self.assertEqual(telem["network_4lang_wf12_closure"], 1)
            self.assertEqual(telem["subst_color"], 0)
            self.assertEqual(telem["subst_image"], 0)
            self.assertEqual(run["gpe0_readback"]["nonzero_pixels"], exp_px)
            self.assertEqual(run["gpe0_readback"]["unique_colors"], exp_col)
            self.assertEqual(run["amber_0xffffaa00_pixels"], exp_amber)

    def test_round20_stage_b_manifest_13_sha256_integrity(self) -> None:
        data = json.loads((ROUND20_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        shared_by_path: Dict[str, str] = {}
        for key in self.EXPECTED_RUN_KEYS:
            items = data["runs"][key]["stage_b"]["manifest_items"]
            self.assertEqual(len(items), 13)
            for item in items:
                gpath = item["guest_path"]
                digest = item["sha256"]
                self.assertEqual(len(digest), 64)
                int(digest, 16)
                if gpath == "/usr/lib/libgrm-fbinit9.so":
                    continue
                if gpath in shared_by_path:
                    self.assertEqual(shared_by_path[gpath], digest, f"SHA mismatch on {gpath}")
                else:
                    shared_by_path[gpath] = digest
        self.assertEqual(len(shared_by_path), 12)

    @staticmethod
    def _diff_rows(ra: List[bytes], rb: List[bytes]) -> int:
        import operator
        ne = operator.ne
        return sum(
            sum(map(ne, memoryview(ya).cast("I"), memoryview(yb).cast("I")))
            for ya, yb in zip(ra, rb)
            if ya != yb
        )

    @staticmethod
    def _count_amber(rows: List[bytes]) -> int:
        amber_word = int.from_bytes(b"\xff\xaa\x00\xff", sys.byteorder)
        return sum(
            sum(1 for px in memoryview(row).cast("I") if px == amber_word)
            for row in rows
            if b"\xff\xaa\x00\xff" in row
        )

    def test_round20_network_3layer_menu_4lang_6pairs_pixel_deltas_exact(self) -> None:
        data = json.loads((ROUND20_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        pw = data["r20_network_4lang_wf12_closure_audit"]["network_3layer_menu_4lang_pairwise"]
        self.assertEqual(pw["language_count"], 4)
        self.assertEqual(pw["pair_count"], 6)
        self.assertTrue(pw["all_6_pairs_strictly_positive"])
        self.assertEqual(pw["min_diff_pixels"], 19652)
        self.assertEqual(pw["max_diff_pixels"], 24770)

        lang_paths = {
            "english": ROUND20_ASSETS_DIR / "r20a-menu-3layer-network-english-alpha.png",
            "japanese": ROUND20_ASSETS_DIR / "r20b-menu-3layer-network-japanese-alpha.png",
            "schinese": ROUND18_ASSETS_DIR / "r18c-menu-3layer-network-schinese-alpha.png",
            "tchinese": ROUND19_ASSETS_DIR / "r19e-menu-3layer-network-tchinese-alpha.png",
        }
        rows = {k: _decode_png_rgba_rows(p.read_bytes())[2] for k, p in lang_paths.items()}
        keys = list(lang_paths.keys())
        pairs = pw["pairs"]
        self.assertEqual(len(pairs), 6)
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                ka, kb = keys[i], keys[j]
                entry = pairs[f"{ka}_vs_{kb}"]
                self.assertTrue(entry["strictly_positive"])
                diff = self._diff_rows(rows[ka], rows[kb])
                self.assertGreater(diff, 0)
                self.assertEqual(diff, entry["diff_pixels"])

    def test_round20_status_tab9_network_4lang_6pairs_pixel_deltas_exact(self) -> None:
        data = json.loads((ROUND20_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        pw = data["r20_network_4lang_wf12_closure_audit"]["status_tab9_network_4lang_pairwise"]
        self.assertEqual(pw["language_count"], 4)
        self.assertEqual(pw["pair_count"], 6)
        self.assertTrue(pw["all_6_pairs_strictly_positive"])
        self.assertEqual(pw["min_diff_pixels"], 11066)
        self.assertEqual(pw["max_diff_pixels"], 20970)

        lang_paths = {
            "english": ROUND20_ASSETS_DIR / "r20c-status-tab9-network-english-alpha.png",
            "japanese": ROUND20_ASSETS_DIR / "r20d-status-tab9-network-japanese-alpha.png",
            "schinese": ROUND17_ASSETS_DIR / "r17e-status-tab9-network-schinese-alpha.png",
            "tchinese": ROUND20_ASSETS_DIR / "r20e-status-tab9-network-tchinese-alpha.png",
        }
        rows = {k: _decode_png_rgba_rows(p.read_bytes())[2] for k, p in lang_paths.items()}
        keys = list(lang_paths.keys())
        pairs = pw["pairs"]
        self.assertEqual(len(pairs), 6)
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                ka, kb = keys[i], keys[j]
                entry = pairs[f"{ka}_vs_{kb}"]
                self.assertTrue(entry["strictly_positive"])
                diff = self._diff_rows(rows[ka], rows[kb])
                self.assertGreater(diff, 0)
                self.assertEqual(diff, entry["diff_pixels"])

    def test_round20_complete_12of12_multilingual_network_audit(self) -> None:
        data = json.loads((ROUND20_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        audit = data["r20_network_4lang_wf12_closure_audit"]
        self.assertEqual(audit["audit_id"], "r20-network-4lang-wf12-12pair-closure")
        self.assertEqual(audit["total_surfaces"], 2)
        self.assertEqual(audit["total_languages"], 4)
        self.assertEqual(audit["total_matrix_cells"], 8)
        self.assertEqual(audit["total_multilingual_pairs"], 12)
        self.assertTrue(audit["all_8_cells_wf12_immune"])
        self.assertTrue(audit["all_12_network_pairs_strictly_positive"])

    def test_round20_wf12_00342260_8cell_immunity_matrix(self) -> None:
        data = json.loads((ROUND20_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        cells = data["r20_network_4lang_wf12_closure_audit"]["wf12_00342260_8cell_immunity_matrix"]
        self.assertEqual(len(cells), 8)
        seen = set()
        expected_lang_params = {
            "english": ("0x00", 0, 4),
            "japanese": ("0x01", 1, 12),
            "schinese": ("0x19", 23, 19),
            "tchinese": ("0x18", 27, 22),
        }
        for c in cells:
            seen.add((c["surface"], c["lang"]))
            bk4_val, fbank, sbank = expected_lang_params[c["lang"]]
            self.assertEqual(c["bk4_lang_val"], bk4_val)
            self.assertEqual(c["font_bank"], fbank)
            self.assertEqual(c["str_bank"], sbank)
            self.assertEqual(c["p12_wlan"], 1)
            self.assertEqual(c["wf12_00342260_immune"], 1)
            self.assertEqual(c["airplane_bk4_hits"], 0)
            self.assertEqual(c["nop_count"], 0)
            self.assertEqual(c["crashes"], 0)
            self.assertEqual(c["gpe_fb"], 0)
            self.assertEqual(c["stage_b_manifest_count"], 13)
        self.assertEqual(len(seen), 8)

    def test_round20_png_receipts_valid_under_85kib_and_amber(self) -> None:
        self.assertTrue(ROUND20_ASSETS_DIR.is_dir())
        alpha_digests: Dict[str, str] = {}
        comp_digests: Dict[str, str] = {}
        for stem in self.EXPECTED_STEMS:
            for variant, bucket in (("alpha", alpha_digests), ("composited", comp_digests)):
                png_path = ROUND20_ASSETS_DIR / f"{stem}-{variant}.png"
                self.assertTrue(png_path.is_file(), f"Missing Round 20 PNG: {png_path}")
                raw = png_path.read_bytes()
                self.assertLess(len(raw), 85 * 1024, f"PNG exceeds 85 KiB: {png_path}")
                w, h, _ = _decode_png_rgba_rows(raw)
                self.assertEqual((w, h), (1024, 540))
                bucket[stem] = hashlib.sha256(raw).hexdigest()
        self.assertEqual(len(set(alpha_digests.values())), len(self.EXPECTED_STEMS))
        self.assertEqual(len(set(comp_digests.values())), len(self.EXPECTED_STEMS))

        for stem, exp_amber in (
            ("r20a-menu-3layer-network-english", 0),
            ("r20b-menu-3layer-network-japanese", 0),
            ("r20c-status-tab9-network-english", 324),
            ("r20d-status-tab9-network-japanese", 273),
            ("r20e-status-tab9-network-tchinese", 273),
        ):
            _, _, rows = _decode_png_rgba_rows((ROUND20_ASSETS_DIR / f"{stem}-alpha.png").read_bytes())
            self.assertEqual(self._count_amber(rows), exp_amber)

    def test_round20_readme_and_no_tmp_scratch_residue(self) -> None:
        closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn("2026-11-14-round20-fx6-on-fx3-network-4lang-wf12-closure", closure_readme)
        r20_readme = (ROUND20_REPORT_DIR / "README.md").read_text(encoding="utf-8")
        for tok in ("0x11", "0x37", "Network", "WF-12", "12/12", "8/8"):
            self.assertIn(tok, r20_readme)
        for forbidden in ("/Volumes/KAFU2T", "/Users/"):
            self.assertNotIn(forbidden, r20_readme)
        tmp_matches = list(pathlib.Path("/private/tmp").glob("fx6-r20*"))
        self.assertEqual(tmp_matches, [], f"Leftover scratch dirs in /private/tmp: {tmp_matches}")


class TestRound21Audio4LangDualSurfaceClosure(unittest.TestCase):
    EXPECTED_STEMS = (
        "r21a-menu-3layer-audio-english",
        "r21b-menu-3layer-audio-japanese",
        "r21c-menu-3layer-audio-tchinese",
        "r21d-status-tab3-audio-english",
        "r21e-status-tab3-audio-japanese",
        "r21f-status-tab3-audio-tchinese",
    )
    EXPECTED_RUN_KEYS = (
        "r21a_menu_3layer_audio_english",
        "r21b_menu_3layer_audio_japanese",
        "r21c_menu_3layer_audio_tchinese",
        "r21d_status_tab3_audio_english",
        "r21e_status_tab3_audio_japanese",
        "r21f_status_tab3_audio_tchinese",
    )

    def test_round21_c_source_guards_and_runner_support(self) -> None:
        shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")

        self.assertIn("#if FX6_ROUND >= 21", shim_src)
        for token in (
            "FX6_R21_LANG_TELEMETRY",
            "FX6_STAGE_B_R21_BRIDGE",
            "audio_4lang_dualsurface=1",
            "wf12_00342260_immune=1",
        ):
            self.assertIn(token, shim_src)

        for token in (
            "/etc/fx6_stage_r21",
            "FX6_STAGE_B_R21_VERIFY_PASS",
            "audio_4lang_dualsurface=1",
            "wf12_00342260_immune=1",
        ):
            self.assertIn(token, verify_src)

        for token in (
            "enable_r21",
            "etc/fx6_stage_r21",
            '"r21_telemetry"',
            '"fx6-r21"',
            "audio_4lang_dualsurface=1",
            "choices=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]",
        ):
            self.assertIn(token, runner_src)

    def _assert_r21_overlay_dual_mode(
        self,
        lang: str,
        uxc1_name: str,
        uxc2_name: str,
        ltt_name: str,
        fontlist_key: str,
        asset_key_u1: str,
        asset_key_ltt: str,
        donor_attr_u1: str,
        donor_attr_u2: str,
        donor_attr_ltt: str,
    ) -> None:
        runner = _load_closure_module(
            f"fx6_build_and_run_round_r21_ovl_{lang}", "build_and_run_round.py"
        )
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            parent_cpio = tmp_dir / "parent.cpio"
            init_body = (
                b"#!/bin/sh\n"
                b'LD_PRELOAD="$FX6_PRELOAD" /usr/bin/appfw-launch\n'
            )
            members = (
                ("init", init_body),
                ("usr/lib/libInfraSetupFile.so", b"SETUP"),
                ("usr/lib/libInfraMediaCommon.so", b"MCOMM"),
                ("usr/lib/libInfraMediaConfig.so", b"MCFG"),
                ("usr/lib/libInfraAppRemoteBoard.so", b"RBRD"),
                ("usr/lib/libfan.so", b"FAN"),
                ("usr/lib/appFw.so", b"APPFW"),
                ("usr/lib/libWlanResource.so", b"WLAN_DONOR_12345"),
                ("usr/kmod/upm.ko", b"UPMKO"),
                ("usr/share/app/image_00_169.uxc", b"uxd\x07" + b"C" * 32),
                (f"usr/share/app/{uxc1_name}", b"uxc\x07" + b"C1" * 16),
                (f"usr/share/app/{uxc2_name}", b"uxc\x07" + b"C2" * 16),
                (f"usr/share/app/{ltt_name}", b"LTT\n" + b"CL" * 16),
                (
                    "usr/share/app/fontlist.dat",
                    f"{fontlist_key}\t/usr/share/app/{ltt_name}\t0\t0\n".encode("ascii"),
                ),
            )
            archive = b"".join(
                runner.make_cpio_member(name, body, ino=idx + 1, mode=0o100755)
                for idx, (name, body) in enumerate(members)
            ) + runner.make_cpio_member("TRAILER!!!", b"", ino=0, mode=0)
            parent_cpio.write_bytes(archive)

            class _FakeRes:
                def __init__(self, site_id: str) -> None:
                    self.site_id = site_id

            class _FakeReceipt:
                def __init__(self, before: bytes, after: bytes, sites: list) -> None:
                    self.before_sha256 = hashlib.sha256(before).hexdigest()
                    self.after_sha256 = hashlib.sha256(after).hexdigest()
                    self.changed_byte_count = 8
                    self.resolutions = [_FakeRes(s.site_id) for s in sites]

            class _FakePatcher:
                P1_P4_P8_APPFW_COMBINED_SPEC = mock.Mock(
                    library_name="appFw.so",
                    expected_size=5,
                    donor_sha256="0" * 64,
                    sites=(mock.Mock(site_id="p1"),),
                    elf_kind="so",
                    source_domain="fx6",
                )
                P1_LIB_INFRA_SETUP_FILE_SPEC = mock.Mock(spec_id="P1_s", library_name="s", sites=[mock.Mock(site_id="s1")])
                P1_LIB_INFRA_MEDIA_COMMON_SPEC = mock.Mock(spec_id="P1_c", library_name="c", sites=[mock.Mock(site_id="c1")])
                P1_LIB_INFRA_MEDIA_CONFIG_SPEC = mock.Mock(spec_id="P1_g", library_name="g", sites=[mock.Mock(site_id="g1")])
                P3_LIB_INFRA_APP_REMOTE_BOARD_SPEC = mock.Mock(spec_id="P3_r", library_name="r", sites=[mock.Mock(site_id="r1")])
                FAN_LIBFAN_SPEC = mock.Mock(spec_id="Fan_f", library_name="f", sites=[mock.Mock(site_id="f1")])
                P9_UPM_KO_SPEC = mock.Mock(spec_id="P9_u", library_name="upm.ko", sites=[mock.Mock(site_id="u1")])
                LibraryPatchSpec = lambda **kw: type("FakeSpec", (), kw)()
                PatchSiteSpec = object
                PF_R = 4

                @staticmethod
                def apply_patch_spec(data: bytes, spec: object, verify_donor_sha256: bool = True):
                    after = data + b"_P"
                    return after, _FakeReceipt(data, after, getattr(spec, "sites", []))

                @staticmethod
                def resolve_and_verify_sites(data: bytes, spec: object, expect_patched_state: bool = True):
                    return [_FakeRes("u1")]

            class _FakeVfat:
                @staticmethod
                def build_opelog_vfat_image(mode: str):
                    img = b"VFAT" * 16
                    receipt = mock.Mock(
                        mode=mode,
                        fat_type="FAT16",
                        total_bytes=len(img),
                        sha256=hashlib.sha256(img).hexdigest(),
                        precreated_dirs=("OPE", "OPE/00", "OPE/01"),
                    )
                    return img, receipt

                @staticmethod
                def verify_vfat_image(_img: bytes):
                    return mock.Mock(valid=True, errors=[])

            class _FakeBmtv:
                @staticmethod
                def build_canonical_fa0080_normal_boot_table(donor_seed_bk4_path=None):
                    return b"T"

                @staticmethod
                def synthesize_ram_shadow_bk4(**_kw):
                    bk = b"BK4\x00" + b"\x00" * 12
                    return mock.Mock(
                        bk4_bytes=bk,
                        total_bytes=len(bk),
                        sha256=hashlib.sha256(bk).hexdigest(),
                        flash_write_allowed=False,
                        active_byte8_selector=0,
                        synthesized_key_count=1,
                    )

            fake_p10 = type(
                "FakeP10",
                (),
                {
                    "spec_id": "P10_FX3_TO_FX6_KEYMAP_ADAPTER",
                    "library_name": "appFw.so",
                    "sites": (mock.Mock(site_id="p10_fn", size=4),),
                },
            )()
            fake_p12 = type(
                "FakeP12",
                (),
                {
                    "spec_id": "P12_libWlanResource_fatal_guard",
                    "library_name": "libWlanResource.so",
                    "sites": (mock.Mock(site_id="p12_wlan", size=8),),
                },
            )()

            def _fake_subproc_run(cmd, **_kw):
                out_path = pathlib.Path(cmd[-1])
                out_path.write_bytes(b"ELF_VERIFY_21")
                return mock.Mock(returncode=0, stderr="")

            donor_u1 = tmp_dir / "donor_u1.uxc"
            donor_u2 = tmp_dir / "donor_u2.uxc"
            donor_ltt = tmp_dir / "donor_font.ltt"
            donor_uxc = tmp_dir / "donor_img.uxc"
            donor_u1.write_bytes(b"uxc\x07" + b"D1" * 16)
            donor_u2.write_bytes(b"uxc\x07" + b"D2" * 16)
            donor_ltt.write_bytes(b"LTT\n" + b"FD" * 16)
            donor_uxc.write_bytes(b"uxd\x07" + b"D" * 32)
            build_dir = tmp_dir / "build"

            with mock.patch.object(
                runner, "_import_stage_a_modules", return_value=(_FakePatcher, _FakeVfat, _FakeBmtv)
            ), mock.patch.object(
                runner, "_load_p10_keymap_spec", return_value=fake_p10
            ), mock.patch.object(
                runner, "_load_p12_wlan_spec", return_value=fake_p12
            ), mock.patch.object(
                runner, "DONOR_IMAGE_00_169_UXC", donor_uxc
            ), mock.patch.object(
                runner, donor_attr_u1, donor_u1
            ), mock.patch.object(
                runner, donor_attr_u2, donor_u2
            ), mock.patch.object(
                runner, donor_attr_ltt, donor_ltt
            ), mock.patch.object(
                runner, "FX3_UPM_KO", tmp_dir / "absent_upm.ko"
            ), mock.patch.object(
                runner, "FX3_SEED_BK4", tmp_dir / "absent_seed.bin"
            ), mock.patch.object(
                runner.subprocess, "run", side_effect=_fake_subproc_run
            ):
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
                    rep, add, meta = runner.build_stage_a_overlay(
                        build_dir,
                        parent_cpio,
                        b"BK4_NTSC",
                        enable_p10=True,
                        enable_r10=True,
                        enable_p12=True,
                        enable_r12=True,
                        enable_r13=True,
                        enable_r14=True,
                        enable_r15=True,
                        enable_r16=True,
                        enable_r17=True,
                        enable_r18=True,
                        enable_r19=True,
                        enable_r20=True,
                        enable_r21=True,
                        lang=lang,
                        shim_bytes=b"SHIM21",
                    )
                self.assertEqual(meta["manifest_count"], 13)
                self.assertTrue(meta["r20_enabled"])
                self.assertTrue(meta["r21_enabled"])
                self.assertEqual(meta["lang"], lang)
                self.assertIn("etc/fx6_stage_r21", add)
                self.assertIn(
                    f"audio_4lang_dualsurface=1\nlang={lang}\n".encode("utf-8"),
                    add["etc/fx6_stage_r21"][0],
                )
                self.assertEqual(meta["lang_assets"][asset_key_u1]["source"], "cpio_preloaded")
                self.assertEqual(meta["lang_assets"][asset_key_ltt]["source"], "cpio_preloaded")
                self.assertEqual(meta["image_00_169_uxc"]["source"], "cpio_preloaded")
                self.assertEqual(meta["lang_assets"]["fontlist_dat"]["fontlist_key"], fontlist_key)
                self.assertEqual(rep[f"usr/share/app/{uxc2_name}"], b"uxc\x07" + b"C2" * 16)

                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "0"}):
                    rep2, add2, meta2 = runner.build_stage_a_overlay(
                        build_dir,
                        parent_cpio,
                        b"BK4_NTSC",
                        enable_p10=True,
                        enable_r10=True,
                        enable_p12=True,
                        enable_r12=True,
                        enable_r13=True,
                        enable_r14=True,
                        enable_r15=True,
                        enable_r16=True,
                        enable_r17=True,
                        enable_r18=True,
                        enable_r19=True,
                        enable_r20=True,
                        enable_r21=True,
                        lang=lang,
                        shim_bytes=b"SHIM21",
                    )
                self.assertTrue(meta2["r21_enabled"])
                self.assertIn("etc/fx6_stage_r21", add2)
                self.assertEqual(meta2["lang_assets"][asset_key_u1]["source"], "donor_o_rdonly")
                self.assertEqual(meta2["image_00_169_uxc"]["source"], "donor_o_rdonly")
                self.assertEqual(rep2[f"usr/share/app/{ltt_name}"], b"LTT\n" + b"FD" * 16)

    def test_round21_stage_a_overlay_schinese_dual_mode(self) -> None:
        self._assert_r21_overlay_dual_mode(
            lang="schinese",
            uxc1_name="string_simplifiedchinese.uxc",
            uxc2_name="string_simplifiedchinese_2.uxc",
            ltt_name="MYingHeiC-GB18030-SJ_wIcon.ltt",
            fontlist_key="FONT_S_CHINESE",
            asset_key_u1="string_simplifiedchinese",
            asset_key_ltt="font_gb18030_ltt",
            donor_attr_u1="DONOR_STRING_SCHINESE_UXC",
            donor_attr_u2="DONOR_STRING_SCHINESE_2_UXC",
            donor_attr_ltt="DONOR_FONT_SCHINESE_LTT",
        )

    def test_round21_stage_a_overlay_tchinese_dual_mode(self) -> None:
        self._assert_r21_overlay_dual_mode(
            lang="tchinese",
            uxc1_name="string_traditionalchinese.uxc",
            uxc2_name="string_traditionalchinese_2.uxc",
            ltt_name="MYingHeiC-Big5HKSCS-SJ_wIcon.ltt",
            fontlist_key="FONT_T_CHINESE",
            asset_key_u1="string_traditionalchinese",
            asset_key_ltt="font_big5hkscs_ltt",
            donor_attr_u1="DONOR_STRING_TCHINESE_UXC",
            donor_attr_u2="DONOR_STRING_TCHINESE_2_UXC",
            donor_attr_ltt="DONOR_FONT_TCHINESE_LTT",
        )

    def test_round21_stage_a_overlay_japanese_dual_mode(self) -> None:
        self._assert_r21_overlay_dual_mode(
            lang="japanese",
            uxc1_name="string_japanese.uxc",
            uxc2_name="string_japanese_2.uxc",
            ltt_name="HeiseiKakuGothW5-SJ_wIcon.ltt",
            fontlist_key="FONT_JAPANESE",
            asset_key_u1="string_japanese",
            asset_key_ltt="font_japanese_ltt",
            donor_attr_u1="DONOR_STRING_JAPANESE_UXC",
            donor_attr_u2="DONOR_STRING_JAPANESE_2_UXC",
            donor_attr_ltt="DONOR_FONT_JAPANESE_LTT",
        )

    def test_round21_stage_a_overlay_english_dual_mode(self) -> None:
        self._assert_r21_overlay_dual_mode(
            lang="english",
            uxc1_name="string_english.uxc",
            uxc2_name="string_english_2.uxc",
            ltt_name="UniversOTS-SJ_wIcon.ltt",
            fontlist_key="FONT_UNIVERS",
            asset_key_u1="string_english",
            asset_key_ltt="font_univers_ltt",
            donor_attr_u1="DONOR_STRING_ENGLISH_UXC",
            donor_attr_u2="DONOR_STRING_ENGLISH_2_UXC",
            donor_attr_ltt="DONOR_FONT_ENGLISH_LTT",
        )

    def test_round21_extract_milestones_telemetry_parser(self) -> None:
        runner = _load_closure_module(
            "fx6_build_and_run_round_r21_ms", "build_and_run_round.py"
        )
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_STAGE_B_R21_VERIFY_PASS count=13 stage_b=1 p10_keymap=1 p11_uipc=1 p12_wlan=1 p4_nd_clear=1 uxc=1 audio_4lang_dualsurface=1 wf12_00342260_immune=1 lang=tchinese",
                "FX6_STAGE_B_R21_BRIDGE round=21 faithful=1 nop_count=0 p12_wlan=1 wf12_00342260_immune=1 p10_keymap=1 p4_nd_clear=1 p11_xlr_h1=1 lang=tchinese bk4_lang=0x18 enum=0x2b44_LANGUAGE_CHINESE_TRADITIONAL font_bank=27 str_bank=22 audio_4lang_dualsurface=1",
                "FX6_R21_LANG_TELEMETRY reason=pump lang=tchinese bk4_lang_id=0x02cf019c bk4_lang_val=0x18 lang_enum=0x2b44_LANGUAGE_CHINESE_TRADITIONAL font_bank=27 str_bank=22 lang_bk4_hits=3 airplane_bk4_hits=0 p4_nd_clear=1 p10_keymap=1 p11_xlr_h1=1 p12_wlan=1 wf12_00342260_immune=1 font_create=26980 glyph_blits=16547 icon_blits=14517 gpe_alloc=215 gpe_fb=0 audio_4lang_dualsurface=1 subst_color=0 subst_image=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        self.assertEqual(ms["prefix_counts"]["FX6_R21_"], 1)
        r21 = ms["r21_telemetry"]
        self.assertIsNotNone(r21)
        self.assertEqual(r21["lang"], "tchinese")
        self.assertEqual(r21["bk4_lang_val"], "0x18")
        self.assertEqual(r21["font_bank"], 27)
        self.assertEqual(r21["str_bank"], 22)
        self.assertEqual(r21["p11_xlr_h1"], 1)
        self.assertEqual(r21["p12_wlan"], 1)
        self.assertEqual(r21["wf12_00342260_immune"], 1)
        self.assertEqual(r21["airplane_bk4_hits"], 0)
        self.assertEqual(r21["gpe_alloc"], 215)
        self.assertEqual(r21["gpe_fb"], 0)
        self.assertEqual(r21["audio_4lang_dualsurface"], 1)
        self.assertEqual(r21["subst_color"], 0)
        self.assertEqual(r21["subst_image"], 0)

    def test_round21_report_and_summary_json_invariants(self) -> None:
        self.assertTrue((ROUND21_REPORT_DIR / "README.md").is_file())
        summary_path = ROUND21_REPORT_DIR / "summary.json"
        self.assertTrue(summary_path.is_file())
        raw_text = summary_path.read_text(encoding="utf-8")
        for forbidden in ("/Volumes/KAFU2T", "/private/tmp", "/Users/"):
            self.assertNotIn(forbidden, raw_text)
        data = json.loads(raw_text)
        self.assertEqual(data["schema"], "fx6-on-fx3-round21-audio-4lang-dualsurface-closure-v1")
        self.assertIn("Linux version 4.9.337-scel+", data["kernel_version"])
        self.assertEqual(set(data["languages"].keys()), {"en", "tchinese", "japanese", "schinese"})

        runs = data["runs"]
        self.assertEqual(set(runs.keys()), set(self.EXPECTED_RUN_KEYS))
        expectations = {
            "r21a_menu_3layer_audio_english": ("english", "0x00", 0, 4, "audio_3layer_menu", "0x11", "31procam_menu_layer_3rd_presenter", "32procam_menu_layer_3rd_controller", 437095, 235, 5352),
            "r21b_menu_3layer_audio_japanese": ("japanese", "0x01", 1, 12, "audio_3layer_menu", "0x11", "31procam_menu_layer_3rd_presenter", "32procam_menu_layer_3rd_controller", 437095, 250, 4670),
            "r21c_menu_3layer_audio_tchinese": ("tchinese", "0x18", 27, 22, "audio_3layer_menu", "0x11", "31procam_menu_layer_3rd_presenter", "32procam_menu_layer_3rd_controller", 437575, 265, 5930),
            "r21d_status_tab3_audio_english": ("english", "0x00", 0, 4, "status_check_tab3_audio", "0x31", "35procam_touch_status_audio_presenter", "36procam_touch_status_audio_controller", 437403, 112, 452),
            "r21e_status_tab3_audio_japanese": ("japanese", "0x01", 1, 12, "status_check_tab3_audio", "0x31", "35procam_touch_status_audio_presenter", "36procam_touch_status_audio_controller", 437883, 114, 404),
            "r21f_status_tab3_audio_tchinese": ("tchinese", "0x18", 27, 22, "status_check_tab3_audio", "0x31", "35procam_touch_status_audio_presenter", "36procam_touch_status_audio_controller", 437883, 114, 404),
        }
        for key, (lang, bk4_val, fbank, sbank, surf, sid, pres, ctrl, exp_px, exp_col, exp_amber) in expectations.items():
            run = runs[key]
            self.assertEqual(run["round"], 21)
            self.assertEqual(run["lang"], lang)
            self.assertEqual(run["surface"], surf)
            self.assertEqual(run["target_sid"], sid)
            self.assertEqual(run["target_presenter"], pres)
            self.assertEqual(run["target_controller"], ctrl)
            self.assertEqual(run["nop_count"], 0)
            self.assertEqual(run["crashes"], 0)
            self.assertGreaterEqual(run["ldec103_ioctl_count"], 55)
            self.assertGreaterEqual(run["total_threads_seen"], 161)
            self.assertEqual(
                run["faithful_invariants"],
                {
                    "FX6_NATIVE_FAITHFUL": 1,
                    "subst_color": 0,
                    "subst_image": 0,
                    "forced_render": 0,
                    "skipped_node": 0,
                    "lock_bypass": 0,
                },
            )
            sb = run["stage_b"]
            self.assertTrue(sb["r20_enabled"])
            self.assertTrue(sb["r21_enabled"])
            self.assertEqual(sb["lang"], lang)
            self.assertEqual(sb["manifest_count"], 13)
            self.assertEqual(len(sb["verify_bin_sha256"]), 64)
            self.assertIn("P12_libWlanResource_fatal_guard", sb["patches"])
            self.assertIn("P10_FX3_TO_FX6_KEYMAP_ADAPTER", sb["patches"])
            self.assertIn(
                "P4_appfw_set_nd_filter_mode_clear",
                sb["patches"]["P1_P4_P8_P10_appFw_combined"]["sites"],
            )
            self.assertGreaterEqual(run["prefix_counts"]["FX6_STAGE_A_"], 21)
            self.assertGreaterEqual(run["prefix_counts"]["FX6_STAGE_B_"], 34)
            self.assertGreaterEqual(run["prefix_counts"]["FX6_R21_"], 150)
            telem = run["r21_telemetry"]
            self.assertEqual(telem["p4_nd_clear"], 1)
            self.assertEqual(telem["p10_keymap"], 1)
            self.assertEqual(telem["p11_xlr_h1"], 1)
            self.assertEqual(telem["lang"], lang)
            self.assertEqual(telem["bk4_lang_val"], bk4_val)
            self.assertEqual(telem["font_bank"], fbank)
            self.assertEqual(telem["str_bank"], sbank)
            self.assertEqual(telem["airplane_bk4_hits"], 0)
            self.assertEqual(telem["p12_wlan"], 1)
            self.assertEqual(telem["wf12_00342260_immune"], 1)
            self.assertEqual(telem["gpe_fb"], 0)
            self.assertEqual(telem["audio_4lang_dualsurface"], 1)
            self.assertEqual(telem["subst_color"], 0)
            self.assertEqual(telem["subst_image"], 0)
            self.assertEqual(run["gpe0_readback"]["nonzero_pixels"], exp_px)
            self.assertEqual(run["gpe0_readback"]["unique_colors"], exp_col)
            self.assertEqual(run["amber_0xffffaa00_pixels"], exp_amber)

    def test_round21_stage_b_manifest_13_sha256_integrity(self) -> None:
        data = json.loads((ROUND21_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        shared_by_path: Dict[str, str] = {}
        for key in self.EXPECTED_RUN_KEYS:
            items = data["runs"][key]["stage_b"]["manifest_items"]
            self.assertEqual(len(items), 13)
            for item in items:
                gpath = item["guest_path"]
                digest = item["sha256"]
                self.assertEqual(len(digest), 64)
                int(digest, 16)
                if gpath == "/usr/lib/libgrm-fbinit9.so":
                    continue
                if gpath in shared_by_path:
                    self.assertEqual(shared_by_path[gpath], digest, f"SHA mismatch on {gpath}")
                else:
                    shared_by_path[gpath] = digest
        self.assertEqual(len(shared_by_path), 12)

    @staticmethod
    def _diff_rows(ra: List[bytes], rb: List[bytes]) -> int:
        import operator
        ne = operator.ne
        return sum(
            sum(map(ne, memoryview(ya).cast("I"), memoryview(yb).cast("I")))
            for ya, yb in zip(ra, rb)
            if ya != yb
        )

    @staticmethod
    def _count_amber(rows: List[bytes]) -> int:
        amber_word = int.from_bytes(b"\xff\xaa\x00\xff", sys.byteorder)
        return sum(
            sum(1 for px in memoryview(row).cast("I") if px == amber_word)
            for row in rows
            if b"\xff\xaa\x00\xff" in row
        )

    def test_round21_audio_3layer_menu_4lang_6pairs_pixel_deltas_exact(self) -> None:
        data = json.loads((ROUND21_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        pw = data["r21_audio_4lang_dualsurface_audit"]["audio_3layer_menu_4lang_pairwise"]
        self.assertEqual(pw["language_count"], 4)
        self.assertEqual(pw["pair_count"], 6)
        self.assertTrue(pw["all_6_pairs_strictly_positive"])
        self.assertEqual(pw["min_diff_pixels"], 31658)
        self.assertEqual(pw["max_diff_pixels"], 59200)

        lang_paths = {
            "english": ROUND21_ASSETS_DIR / "r21a-menu-3layer-audio-english-alpha.png",
            "japanese": ROUND21_ASSETS_DIR / "r21b-menu-3layer-audio-japanese-alpha.png",
            "schinese": ROUND17_ASSETS_DIR / "r17d-menu-3layer-audio-schinese-alpha.png",
            "tchinese": ROUND21_ASSETS_DIR / "r21c-menu-3layer-audio-tchinese-alpha.png",
        }
        rows = {k: _decode_png_rgba_rows(p.read_bytes())[2] for k, p in lang_paths.items()}
        keys = list(lang_paths.keys())
        pairs = pw["pairs"]
        self.assertEqual(len(pairs), 6)
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                ka, kb = keys[i], keys[j]
                entry = pairs[f"{ka}_vs_{kb}"]
                self.assertTrue(entry["strictly_positive"])
                diff = self._diff_rows(rows[ka], rows[kb])
                self.assertGreater(diff, 0)
                self.assertEqual(diff, entry["diff_pixels"])

    def test_round21_status_tab3_audio_4lang_6pairs_pixel_deltas_exact(self) -> None:
        data = json.loads((ROUND21_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        pw = data["r21_audio_4lang_dualsurface_audit"]["status_tab3_audio_4lang_pairwise"]
        self.assertEqual(pw["language_count"], 4)
        self.assertEqual(pw["pair_count"], 6)
        self.assertTrue(pw["all_6_pairs_strictly_positive"])
        self.assertEqual(pw["min_diff_pixels"], 22447)
        self.assertEqual(pw["max_diff_pixels"], 39282)

        lang_paths = {
            "english": ROUND21_ASSETS_DIR / "r21d-status-tab3-audio-english-alpha.png",
            "japanese": ROUND21_ASSETS_DIR / "r21e-status-tab3-audio-japanese-alpha.png",
            "schinese": ROUND15_ASSETS_DIR / "r15b-status-tab3-schinese-alpha.png",
            "tchinese": ROUND21_ASSETS_DIR / "r21f-status-tab3-audio-tchinese-alpha.png",
        }
        rows = {k: _decode_png_rgba_rows(p.read_bytes())[2] for k, p in lang_paths.items()}
        keys = list(lang_paths.keys())
        pairs = pw["pairs"]
        self.assertEqual(len(pairs), 6)
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                ka, kb = keys[i], keys[j]
                entry = pairs[f"{ka}_vs_{kb}"]
                self.assertTrue(entry["strictly_positive"])
                diff = self._diff_rows(rows[ka], rows[kb])
                self.assertGreater(diff, 0)
                self.assertEqual(diff, entry["diff_pixels"])

    def test_round21_complete_12of12_multilingual_audio_audit(self) -> None:
        data = json.loads((ROUND21_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        audit = data["r21_audio_4lang_dualsurface_audit"]
        self.assertEqual(audit["audit_id"], "r21-audio-4lang-dualsurface-12pair-closure")
        self.assertEqual(audit["total_surfaces"], 2)
        self.assertEqual(audit["total_languages"], 4)
        self.assertEqual(audit["total_matrix_cells"], 8)
        self.assertEqual(audit["total_multilingual_pairs"], 12)
        self.assertTrue(audit["all_8_cells_stage_b_green"])
        self.assertTrue(audit["all_12_audio_pairs_strictly_positive"])

    def test_round21_audio_8cell_matrix_invariants(self) -> None:
        data = json.loads((ROUND21_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        cells = data["r21_audio_4lang_dualsurface_audit"]["audio_8cell_matrix"]
        self.assertEqual(len(cells), 8)
        seen = set()
        expected_lang_params = {
            "english": ("0x00", 0, 4),
            "japanese": ("0x01", 1, 12),
            "schinese": ("0x19", 23, 19),
            "tchinese": ("0x18", 27, 22),
        }
        for c in cells:
            seen.add((c["surface"], c["lang"]))
            bk4_val, fbank, sbank = expected_lang_params[c["lang"]]
            self.assertEqual(c["bk4_lang_val"], bk4_val)
            self.assertEqual(c["font_bank"], fbank)
            self.assertEqual(c["str_bank"], sbank)
            self.assertEqual(c["p12_wlan"], 1)
            self.assertEqual(c["wf12_00342260_immune"], 1)
            self.assertEqual(c["airplane_bk4_hits"], 0)
            self.assertEqual(c["nop_count"], 0)
            self.assertEqual(c["crashes"], 0)
            self.assertEqual(c["gpe_fb"], 0)
            self.assertEqual(c["stage_b_manifest_count"], 13)
        self.assertEqual(len(seen), 8)

    def test_round21_png_receipts_valid_under_85kib_and_amber(self) -> None:
        self.assertTrue(ROUND21_ASSETS_DIR.is_dir())
        alpha_digests: Dict[str, str] = {}
        comp_digests: Dict[str, str] = {}
        for stem in self.EXPECTED_STEMS:
            for variant, bucket in (("alpha", alpha_digests), ("composited", comp_digests)):
                png_path = ROUND21_ASSETS_DIR / f"{stem}-{variant}.png"
                self.assertTrue(png_path.is_file(), f"Missing Round 21 PNG: {png_path}")
                raw = png_path.read_bytes()
                self.assertLess(len(raw), 85 * 1024, f"PNG exceeds 85 KiB: {png_path}")
                w, h, _ = _decode_png_rgba_rows(raw)
                self.assertEqual((w, h), (1024, 540))
                bucket[stem] = hashlib.sha256(raw).hexdigest()
        self.assertEqual(len(set(alpha_digests.values())), len(self.EXPECTED_STEMS))
        self.assertEqual(len(set(comp_digests.values())), len(self.EXPECTED_STEMS))

        for stem, exp_amber in (
            ("r21a-menu-3layer-audio-english", 5352),
            ("r21b-menu-3layer-audio-japanese", 4670),
            ("r21c-menu-3layer-audio-tchinese", 5930),
            ("r21d-status-tab3-audio-english", 452),
            ("r21e-status-tab3-audio-japanese", 404),
            ("r21f-status-tab3-audio-tchinese", 404),
        ):
            _, _, rows = _decode_png_rgba_rows((ROUND21_ASSETS_DIR / f"{stem}-alpha.png").read_bytes())
            self.assertEqual(self._count_amber(rows), exp_amber)

    def test_round21_readme_and_no_tmp_scratch_residue(self) -> None:
        closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn("2026-11-14-round21-fx6-on-fx3-audio-4lang-dualsurface-closure", closure_readme)
        r21_readme = (ROUND21_REPORT_DIR / "README.md").read_text(encoding="utf-8")
        for tok in ("0x11", "0x31", "Audio", "12/12", "8/8"):
            self.assertIn(tok, r21_readme)
        for forbidden in ("/Volumes/KAFU2T", "/Users/"):
            self.assertNotIn(forbidden, r21_readme)
        tmp_matches = list(pathlib.Path("/private/tmp").glob("fx6-r21*"))
        self.assertEqual(tmp_matches, [], f"Leftover scratch dirs in /private/tmp: {tmp_matches}")


class TestRound22PaintLookCamTab24LangClosure(unittest.TestCase):
    EXPECTED_STEMS = (
        "r22a-menu-3layer-paintlook-english",
        "r22b-menu-3layer-paintlook-japanese",
        "r22c-menu-3layer-paintlook-tchinese",
        "r22d-status-tab2-camera-english",
        "r22e-status-tab2-camera-tchinese",
    )
    EXPECTED_RUN_KEYS = (
        "r22a_menu_3layer_paintlook_english",
        "r22b_menu_3layer_paintlook_japanese",
        "r22c_menu_3layer_paintlook_tchinese",
        "r22d_status_tab2_camera_english",
        "r22e_status_tab2_camera_tchinese",
    )

    def test_round22_c_source_guards_and_runner_support(self) -> None:
        shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")

        self.assertIn("#if FX6_ROUND >= 22", shim_src)
        for token in (
            "FX6_R22_LANG_TELEMETRY",
            "FX6_STAGE_B_R22_BRIDGE",
            "paintlook_camtab2_4lang_dualsurface=1",
            "wf12_00342260_immune=1",
        ):
            self.assertIn(token, shim_src)

        for token in (
            "/etc/fx6_stage_r22",
            "FX6_STAGE_B_R22_VERIFY_PASS",
            "paintlook_camtab2_4lang_dualsurface=1",
            "wf12_00342260_immune=1",
        ):
            self.assertIn(token, verify_src)

        for token in (
            "enable_r22",
            "etc/fx6_stage_r22",
            '"r22_telemetry"',
            '"fx6-r22"',
            "paintlook_camtab2_4lang_dualsurface=1",
            "choices=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]",
        ):
            self.assertIn(token, runner_src)

    def _assert_r22_overlay_dual_mode(
        self,
        lang: str,
        uxc1_name: str,
        uxc2_name: str,
        ltt_name: str,
        fontlist_key: str,
        asset_key_u1: str,
        asset_key_ltt: str,
        donor_attr_u1: str,
        donor_attr_u2: str,
        donor_attr_ltt: str,
    ) -> None:
        runner = _load_closure_module(
            f"fx6_build_and_run_round_r22_ovl_{lang}", "build_and_run_round.py"
        )
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            parent_cpio = tmp_dir / "parent.cpio"
            init_body = (
                b"#!/bin/sh\n"
                b'LD_PRELOAD="$FX6_PRELOAD" /usr/bin/appfw-launch\n'
            )
            members = (
                ("init", init_body),
                ("usr/lib/libInfraSetupFile.so", b"SETUP"),
                ("usr/lib/libInfraMediaCommon.so", b"MCOMM"),
                ("usr/lib/libInfraMediaConfig.so", b"MCFG"),
                ("usr/lib/libInfraAppRemoteBoard.so", b"RBRD"),
                ("usr/lib/libfan.so", b"FAN"),
                ("usr/lib/appFw.so", b"APPFW"),
                ("usr/lib/libWlanResource.so", b"WLAN_DONOR_12345"),
                ("usr/kmod/upm.ko", b"UPMKO"),
                ("usr/share/app/image_00_169.uxc", b"uxd\x07" + b"C" * 32),
                (f"usr/share/app/{uxc1_name}", b"uxc\x07" + b"C1" * 16),
                (f"usr/share/app/{uxc2_name}", b"uxc\x07" + b"C2" * 16),
                (f"usr/share/app/{ltt_name}", b"LTT\n" + b"CL" * 16),
                (
                    "usr/share/app/fontlist.dat",
                    f"{fontlist_key}\t/usr/share/app/{ltt_name}\t0\t0\n".encode("ascii"),
                ),
            )
            archive = b"".join(
                runner.make_cpio_member(name, body, ino=idx + 1, mode=0o100755)
                for idx, (name, body) in enumerate(members)
            ) + runner.make_cpio_member("TRAILER!!!", b"", ino=0, mode=0)
            parent_cpio.write_bytes(archive)

            class _FakeRes:
                def __init__(self, site_id: str) -> None:
                    self.site_id = site_id

            class _FakeReceipt:
                def __init__(self, before: bytes, after: bytes, sites: list) -> None:
                    self.before_sha256 = hashlib.sha256(before).hexdigest()
                    self.after_sha256 = hashlib.sha256(after).hexdigest()
                    self.changed_byte_count = 8
                    self.resolutions = [_FakeRes(s.site_id) for s in sites]

            class _FakePatcher:
                P1_P4_P8_APPFW_COMBINED_SPEC = mock.Mock(
                    library_name="appFw.so",
                    expected_size=5,
                    donor_sha256="0" * 64,
                    sites=(mock.Mock(site_id="p1"),),
                    elf_kind="so",
                    source_domain="fx6",
                )
                P1_LIB_INFRA_SETUP_FILE_SPEC = mock.Mock(spec_id="P1_s", library_name="s", sites=[mock.Mock(site_id="s1")])
                P1_LIB_INFRA_MEDIA_COMMON_SPEC = mock.Mock(spec_id="P1_c", library_name="c", sites=[mock.Mock(site_id="c1")])
                P1_LIB_INFRA_MEDIA_CONFIG_SPEC = mock.Mock(spec_id="P1_g", library_name="g", sites=[mock.Mock(site_id="g1")])
                P3_LIB_INFRA_APP_REMOTE_BOARD_SPEC = mock.Mock(spec_id="P3_r", library_name="r", sites=[mock.Mock(site_id="r1")])
                FAN_LIBFAN_SPEC = mock.Mock(spec_id="Fan_f", library_name="f", sites=[mock.Mock(site_id="f1")])
                P9_UPM_KO_SPEC = mock.Mock(spec_id="P9_u", library_name="upm.ko", sites=[mock.Mock(site_id="u1")])
                LibraryPatchSpec = lambda **kw: type("FakeSpec", (), kw)()
                PatchSiteSpec = object
                PF_R = 4

                @staticmethod
                def apply_patch_spec(data: bytes, spec: object, verify_donor_sha256: bool = True):
                    after = data + b"_P"
                    return after, _FakeReceipt(data, after, getattr(spec, "sites", []))

                @staticmethod
                def resolve_and_verify_sites(data: bytes, spec: object, expect_patched_state: bool = True):
                    return [_FakeRes("u1")]

            class _FakeVfat:
                @staticmethod
                def build_opelog_vfat_image(mode: str):
                    img = b"VFAT" * 16
                    receipt = mock.Mock(
                        mode=mode,
                        fat_type="FAT16",
                        total_bytes=len(img),
                        sha256=hashlib.sha256(img).hexdigest(),
                        precreated_dirs=("OPE", "OPE/00", "OPE/01"),
                    )
                    return img, receipt

                @staticmethod
                def verify_vfat_image(_img: bytes):
                    return mock.Mock(valid=True, errors=[])

            class _FakeBmtv:
                @staticmethod
                def build_canonical_fa0080_normal_boot_table(donor_seed_bk4_path=None):
                    return b"T"

                @staticmethod
                def synthesize_ram_shadow_bk4(**_kw):
                    bk = b"BK4\x00" + b"\x00" * 12
                    return mock.Mock(
                        bk4_bytes=bk,
                        total_bytes=len(bk),
                        sha256=hashlib.sha256(bk).hexdigest(),
                        flash_write_allowed=False,
                        active_byte8_selector=0,
                        synthesized_key_count=1,
                    )

            fake_p10 = type(
                "FakeP10",
                (),
                {
                    "spec_id": "P10_FX3_TO_FX6_KEYMAP_ADAPTER",
                    "library_name": "appFw.so",
                    "sites": (mock.Mock(site_id="p10_fn", size=4),),
                },
            )()
            fake_p12 = type(
                "FakeP12",
                (),
                {
                    "spec_id": "P12_libWlanResource_fatal_guard",
                    "library_name": "libWlanResource.so",
                    "sites": (mock.Mock(site_id="p12_wlan", size=8),),
                },
            )()

            def _fake_subproc_run(cmd, **_kw):
                out_path = pathlib.Path(cmd[-1])
                out_path.write_bytes(b"ELF_VERIFY_22")
                return mock.Mock(returncode=0, stderr="")

            donor_u1 = tmp_dir / "donor_u1.uxc"
            donor_u2 = tmp_dir / "donor_u2.uxc"
            donor_ltt = tmp_dir / "donor_font.ltt"
            donor_uxc = tmp_dir / "donor_img.uxc"
            donor_u1.write_bytes(b"uxc\x07" + b"D1" * 16)
            donor_u2.write_bytes(b"uxc\x07" + b"D2" * 16)
            donor_ltt.write_bytes(b"LTT\n" + b"FD" * 16)
            donor_uxc.write_bytes(b"uxd\x07" + b"D" * 32)
            build_dir = tmp_dir / "build"

            with mock.patch.object(
                runner, "_import_stage_a_modules", return_value=(_FakePatcher, _FakeVfat, _FakeBmtv)
            ), mock.patch.object(
                runner, "_load_p10_keymap_spec", return_value=fake_p10
            ), mock.patch.object(
                runner, "_load_p12_wlan_spec", return_value=fake_p12
            ), mock.patch.object(
                runner, "DONOR_IMAGE_00_169_UXC", donor_uxc
            ), mock.patch.object(
                runner, donor_attr_u1, donor_u1
            ), mock.patch.object(
                runner, donor_attr_u2, donor_u2
            ), mock.patch.object(
                runner, donor_attr_ltt, donor_ltt
            ), mock.patch.object(
                runner, "FX3_UPM_KO", tmp_dir / "absent_upm.ko"
            ), mock.patch.object(
                runner, "FX3_SEED_BK4", tmp_dir / "absent_seed.bin"
            ), mock.patch.object(
                runner.subprocess, "run", side_effect=_fake_subproc_run
            ):
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
                    rep, add, meta = runner.build_stage_a_overlay(
                        build_dir,
                        parent_cpio,
                        b"BK4_NTSC",
                        enable_p10=True,
                        enable_r10=True,
                        enable_p12=True,
                        enable_r12=True,
                        enable_r13=True,
                        enable_r14=True,
                        enable_r15=True,
                        enable_r16=True,
                        enable_r17=True,
                        enable_r18=True,
                        enable_r19=True,
                        enable_r20=True,
                        enable_r21=True,
                        enable_r22=True,
                        lang=lang,
                        shim_bytes=b"SHIM22",
                    )
                self.assertEqual(meta["manifest_count"], 13)
                self.assertTrue(meta["r21_enabled"])
                self.assertTrue(meta["r22_enabled"])
                self.assertEqual(meta["lang"], lang)
                self.assertIn("etc/fx6_stage_r22", add)
                self.assertIn(
                    f"paintlook_camtab2_4lang_dualsurface=1\nlang={lang}\n".encode("utf-8"),
                    add["etc/fx6_stage_r22"][0],
                )
                self.assertEqual(meta["lang_assets"][asset_key_u1]["source"], "cpio_preloaded")
                self.assertEqual(meta["lang_assets"][asset_key_ltt]["source"], "cpio_preloaded")
                self.assertEqual(meta["image_00_169_uxc"]["source"], "cpio_preloaded")
                self.assertEqual(meta["lang_assets"]["fontlist_dat"]["fontlist_key"], fontlist_key)
                self.assertEqual(rep[f"usr/share/app/{uxc2_name}"], b"uxc\x07" + b"C2" * 16)

                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "0"}):
                    rep2, add2, meta2 = runner.build_stage_a_overlay(
                        build_dir,
                        parent_cpio,
                        b"BK4_NTSC",
                        enable_p10=True,
                        enable_r10=True,
                        enable_p12=True,
                        enable_r12=True,
                        enable_r13=True,
                        enable_r14=True,
                        enable_r15=True,
                        enable_r16=True,
                        enable_r17=True,
                        enable_r18=True,
                        enable_r19=True,
                        enable_r20=True,
                        enable_r21=True,
                        enable_r22=True,
                        lang=lang,
                        shim_bytes=b"SHIM22",
                    )
                self.assertTrue(meta2["r22_enabled"])
                self.assertIn("etc/fx6_stage_r22", add2)
                self.assertEqual(meta2["lang_assets"][asset_key_u1]["source"], "donor_o_rdonly")
                self.assertEqual(meta2["image_00_169_uxc"]["source"], "donor_o_rdonly")
                self.assertEqual(rep2[f"usr/share/app/{ltt_name}"], b"LTT\n" + b"FD" * 16)

    def test_round22_stage_a_overlay_schinese_dual_mode(self) -> None:
        self._assert_r22_overlay_dual_mode(
            lang="schinese",
            uxc1_name="string_simplifiedchinese.uxc",
            uxc2_name="string_simplifiedchinese_2.uxc",
            ltt_name="MYingHeiC-GB18030-SJ_wIcon.ltt",
            fontlist_key="FONT_S_CHINESE",
            asset_key_u1="string_simplifiedchinese",
            asset_key_ltt="font_gb18030_ltt",
            donor_attr_u1="DONOR_STRING_SCHINESE_UXC",
            donor_attr_u2="DONOR_STRING_SCHINESE_2_UXC",
            donor_attr_ltt="DONOR_FONT_SCHINESE_LTT",
        )

    def test_round22_stage_a_overlay_tchinese_dual_mode(self) -> None:
        self._assert_r22_overlay_dual_mode(
            lang="tchinese",
            uxc1_name="string_traditionalchinese.uxc",
            uxc2_name="string_traditionalchinese_2.uxc",
            ltt_name="MYingHeiC-Big5HKSCS-SJ_wIcon.ltt",
            fontlist_key="FONT_T_CHINESE",
            asset_key_u1="string_traditionalchinese",
            asset_key_ltt="font_big5hkscs_ltt",
            donor_attr_u1="DONOR_STRING_TCHINESE_UXC",
            donor_attr_u2="DONOR_STRING_TCHINESE_2_UXC",
            donor_attr_ltt="DONOR_FONT_TCHINESE_LTT",
        )

    def test_round22_stage_a_overlay_japanese_dual_mode(self) -> None:
        self._assert_r22_overlay_dual_mode(
            lang="japanese",
            uxc1_name="string_japanese.uxc",
            uxc2_name="string_japanese_2.uxc",
            ltt_name="HeiseiKakuGothW5-SJ_wIcon.ltt",
            fontlist_key="FONT_JAPANESE",
            asset_key_u1="string_japanese",
            asset_key_ltt="font_japanese_ltt",
            donor_attr_u1="DONOR_STRING_JAPANESE_UXC",
            donor_attr_u2="DONOR_STRING_JAPANESE_2_UXC",
            donor_attr_ltt="DONOR_FONT_JAPANESE_LTT",
        )

    def test_round22_stage_a_overlay_english_dual_mode(self) -> None:
        self._assert_r22_overlay_dual_mode(
            lang="english",
            uxc1_name="string_english.uxc",
            uxc2_name="string_english_2.uxc",
            ltt_name="UniversOTS-SJ_wIcon.ltt",
            fontlist_key="FONT_UNIVERS",
            asset_key_u1="string_english",
            asset_key_ltt="font_univers_ltt",
            donor_attr_u1="DONOR_STRING_ENGLISH_UXC",
            donor_attr_u2="DONOR_STRING_ENGLISH_2_UXC",
            donor_attr_ltt="DONOR_FONT_ENGLISH_LTT",
        )

    def test_round22_extract_milestones_telemetry_parser(self) -> None:
        runner = _load_closure_module(
            "fx6_build_and_run_round_r22_ms", "build_and_run_round.py"
        )
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_STAGE_B_R22_VERIFY_PASS count=13 stage_b=1 p10_keymap=1 p11_uipc=1 p12_wlan=1 p4_nd_clear=1 uxc=1 paintlook_camtab2_4lang_dualsurface=1 wf12_00342260_immune=1 lang=japanese",
                "FX6_STAGE_B_R22_BRIDGE round=22 faithful=1 nop_count=0 p12_wlan=1 wf12_00342260_immune=1 p10_keymap=1 p4_nd_clear=1 p11_xlr_h1=1 lang=japanese bk4_lang=0x01 enum=0x2b30_LANGUAGE_JAPANESE font_bank=1 str_bank=12 paintlook_camtab2_4lang_dualsurface=1",
                "FX6_R22_LANG_TELEMETRY reason=pump lang=japanese bk4_lang_id=0x02cf019c bk4_lang_val=0x01 lang_enum=0x2b30_LANGUAGE_JAPANESE font_bank=1 str_bank=12 lang_bk4_hits=3 airplane_bk4_hits=0 p4_nd_clear=1 p10_keymap=1 p11_xlr_h1=1 p12_wlan=1 wf12_00342260_immune=1 font_create=20789 glyph_blits=12817 icon_blits=14679 gpe_alloc=170 gpe_fb=0 paintlook_camtab2_4lang_dualsurface=1 subst_color=0 subst_image=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        self.assertEqual(ms["prefix_counts"]["FX6_R22_"], 1)
        r22 = ms["r22_telemetry"]
        self.assertIsNotNone(r22)
        self.assertEqual(r22["lang"], "japanese")
        self.assertEqual(r22["bk4_lang_val"], "0x01")
        self.assertEqual(r22["font_bank"], 1)
        self.assertEqual(r22["str_bank"], 12)
        self.assertEqual(r22["p11_xlr_h1"], 1)
        self.assertEqual(r22["p12_wlan"], 1)
        self.assertEqual(r22["wf12_00342260_immune"], 1)
        self.assertEqual(r22["airplane_bk4_hits"], 0)
        self.assertEqual(r22["gpe_alloc"], 170)
        self.assertEqual(r22["gpe_fb"], 0)
        self.assertEqual(r22["paintlook_camtab2_4lang_dualsurface"], 1)
        self.assertEqual(r22["subst_color"], 0)
        self.assertEqual(r22["subst_image"], 0)

    def test_round22_report_and_summary_json_invariants(self) -> None:
        self.assertTrue((ROUND22_REPORT_DIR / "README.md").is_file())
        summary_path = ROUND22_REPORT_DIR / "summary.json"
        self.assertTrue(summary_path.is_file())
        raw_text = summary_path.read_text(encoding="utf-8")
        for forbidden in ("/Volumes/KAFU2T", "/private/tmp", "/Users/"):
            self.assertNotIn(forbidden, raw_text)
        data = json.loads(raw_text)
        self.assertEqual(data["schema"], "fx6-on-fx3-round22-paintlook-camera-4lang-closure-v1")
        self.assertIn("Linux version 4.9.337-scel+", data["kernel_version"])
        self.assertEqual(set(data["languages"].keys()), {"en", "tchinese", "japanese", "schinese"})

        runs = data["runs"]
        self.assertEqual(set(runs.keys()), set(self.EXPECTED_RUN_KEYS))
        expectations = {
            "r22a_menu_3layer_paintlook_english": ("english", "0x00", 0, 4, "paintlook_3layer_menu", "0x11", "31procam_menu_layer_3rd_presenter", "32procam_menu_layer_3rd_controller", 437575, 241, 993),
            "r22b_menu_3layer_paintlook_japanese": ("japanese", "0x01", 1, 12, "paintlook_3layer_menu", "0x11", "31procam_menu_layer_3rd_presenter", "32procam_menu_layer_3rd_controller", 437095, 254, 804),
            "r22c_menu_3layer_paintlook_tchinese": ("tchinese", "0x18", 27, 22, "paintlook_3layer_menu", "0x11", "31procam_menu_layer_3rd_presenter", "32procam_menu_layer_3rd_controller", 437575, 269, 804),
            "r22d_status_tab2_camera_english": ("english", "0x00", 0, 4, "status_check_tab2_camera", "0x30", "36procam_touch_status_camera_presenter", "37procam_touch_status_camera_controller", 437883, 80, 311),
            "r22e_status_tab2_camera_tchinese": ("tchinese", "0x18", 27, 22, "status_check_tab2_camera", "0x30", "36procam_touch_status_camera_presenter", "37procam_touch_status_camera_controller", 437883, 80, 260),
        }
        for key, (lang, bk4_val, fbank, sbank, surf, sid, pres, ctrl, exp_px, exp_col, exp_amber) in expectations.items():
            run = runs[key]
            self.assertEqual(run["round"], 22)
            self.assertEqual(run["lang"], lang)
            self.assertEqual(run["surface"], surf)
            self.assertEqual(run["target_sid"], sid)
            self.assertEqual(run["target_presenter"], pres)
            self.assertEqual(run["target_controller"], ctrl)
            self.assertEqual(run["nop_count"], 0)
            self.assertEqual(run["crashes"], 0)
            self.assertGreaterEqual(run["ldec103_ioctl_count"], 55)
            self.assertGreaterEqual(run["total_threads_seen"], 161)
            self.assertEqual(
                run["faithful_invariants"],
                {
                    "FX6_NATIVE_FAITHFUL": 1,
                    "subst_color": 0,
                    "subst_image": 0,
                    "forced_render": 0,
                    "skipped_node": 0,
                    "lock_bypass": 0,
                },
            )
            sb = run["stage_b"]
            self.assertTrue(sb["r21_enabled"])
            self.assertTrue(sb["r22_enabled"])
            self.assertEqual(sb["lang"], lang)
            self.assertEqual(sb["manifest_count"], 13)
            self.assertEqual(len(sb["verify_bin_sha256"]), 64)
            self.assertIn("P12_libWlanResource_fatal_guard", sb["patches"])
            self.assertIn("P10_FX3_TO_FX6_KEYMAP_ADAPTER", sb["patches"])
            self.assertIn(
                "P4_appfw_set_nd_filter_mode_clear",
                sb["patches"]["P1_P4_P8_P10_appFw_combined"]["sites"],
            )
            self.assertGreaterEqual(run["prefix_counts"]["FX6_STAGE_A_"], 21)
            self.assertGreaterEqual(run["prefix_counts"]["FX6_STAGE_B_"], 36)
            self.assertGreaterEqual(run["prefix_counts"]["FX6_R22_"], 150)
            telem = run["r22_telemetry"]
            self.assertEqual(telem["p4_nd_clear"], 1)
            self.assertEqual(telem["p10_keymap"], 1)
            self.assertEqual(telem["p11_xlr_h1"], 1)
            self.assertEqual(telem["lang"], lang)
            self.assertEqual(telem["bk4_lang_val"], bk4_val)
            self.assertEqual(telem["font_bank"], fbank)
            self.assertEqual(telem["str_bank"], sbank)
            self.assertEqual(telem["airplane_bk4_hits"], 0)
            self.assertEqual(telem["p12_wlan"], 1)
            self.assertEqual(telem["wf12_00342260_immune"], 1)
            self.assertEqual(telem["gpe_fb"], 0)
            self.assertEqual(telem["paintlook_camtab2_4lang_dualsurface"], 1)
            self.assertEqual(telem["subst_color"], 0)
            self.assertEqual(telem["subst_image"], 0)
            self.assertEqual(run["gpe0_readback"]["nonzero_pixels"], exp_px)
            self.assertEqual(run["gpe0_readback"]["unique_colors"], exp_col)
            self.assertEqual(run["amber_0xffffaa00_pixels"], exp_amber)

    def test_round22_stage_b_manifest_13_sha256_integrity(self) -> None:
        data = json.loads((ROUND22_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        shared_by_path: Dict[str, str] = {}
        for key in self.EXPECTED_RUN_KEYS:
            items = data["runs"][key]["stage_b"]["manifest_items"]
            self.assertEqual(len(items), 13)
            for item in items:
                gpath = item["guest_path"]
                digest = item["sha256"]
                self.assertEqual(len(digest), 64)
                int(digest, 16)
                if gpath == "/usr/lib/libgrm-fbinit9.so":
                    continue
                if gpath in shared_by_path:
                    self.assertEqual(shared_by_path[gpath], digest, f"SHA mismatch on {gpath}")
                else:
                    shared_by_path[gpath] = digest
        self.assertEqual(len(shared_by_path), 12)

    @staticmethod
    def _diff_rows(ra: List[bytes], rb: List[bytes]) -> int:
        import operator
        ne = operator.ne
        return sum(
            sum(map(ne, memoryview(ya).cast("I"), memoryview(yb).cast("I")))
            for ya, yb in zip(ra, rb)
            if ya != yb
        )

    @staticmethod
    def _count_amber(rows: List[bytes]) -> int:
        amber_word = int.from_bytes(b"\xff\xaa\x00\xff", sys.byteorder)
        return sum(
            sum(1 for px in memoryview(row).cast("I") if px == amber_word)
            for row in rows
            if b"\xff\xaa\x00\xff" in row
        )

    def test_round22_paintlook_3layer_menu_4lang_6pairs_pixel_deltas_exact(self) -> None:
        data = json.loads((ROUND22_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        pw = data["r22_paintlook_camtab2_4lang_dualsurface_audit"]["paintlook_3layer_menu_4lang_pairwise"]
        self.assertEqual(pw["language_count"], 4)
        self.assertEqual(pw["pair_count"], 6)
        self.assertTrue(pw["all_6_pairs_strictly_positive"])
        self.assertEqual(pw["min_diff_pixels"], 29243)
        self.assertEqual(pw["max_diff_pixels"], 45413)

        lang_paths = {
            "english": ROUND22_ASSETS_DIR / "r22a-menu-3layer-paintlook-english-alpha.png",
            "japanese": ROUND22_ASSETS_DIR / "r22b-menu-3layer-paintlook-japanese-alpha.png",
            "schinese": ROUND13_ASSETS_DIR / "r13c-menu-3layer-paintlook-schinese-alpha.png",
            "tchinese": ROUND22_ASSETS_DIR / "r22c-menu-3layer-paintlook-tchinese-alpha.png",
        }
        rows = {k: _decode_png_rgba_rows(p.read_bytes())[2] for k, p in lang_paths.items()}
        keys = list(lang_paths.keys())
        pairs = pw["pairs"]
        self.assertEqual(len(pairs), 6)
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                ka, kb = keys[i], keys[j]
                entry = pairs[f"{ka}_vs_{kb}"]
                self.assertTrue(entry["strictly_positive"])
                diff = self._diff_rows(rows[ka], rows[kb])
                self.assertGreater(diff, 0)
                self.assertEqual(diff, entry["diff_pixels"])

    def test_round22_status_tab2_camera_4lang_6pairs_pixel_deltas_exact(self) -> None:
        data = json.loads((ROUND22_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        pw = data["r22_paintlook_camtab2_4lang_dualsurface_audit"]["status_tab2_camera_4lang_pairwise"]
        self.assertEqual(pw["language_count"], 4)
        self.assertEqual(pw["pair_count"], 6)
        self.assertTrue(pw["all_6_pairs_strictly_positive"])
        self.assertEqual(pw["min_diff_pixels"], 19103)
        self.assertEqual(pw["max_diff_pixels"], 42855)

        lang_paths = {
            "english": ROUND22_ASSETS_DIR / "r22d-status-tab2-camera-english-alpha.png",
            "japanese": ROUND15_ASSETS_DIR / "r15d-status-tab2-japanese-alpha.png",
            "schinese": ROUND15_ASSETS_DIR / "r15a-status-tab2-schinese-alpha.png",
            "tchinese": ROUND22_ASSETS_DIR / "r22e-status-tab2-camera-tchinese-alpha.png",
        }
        rows = {k: _decode_png_rgba_rows(p.read_bytes())[2] for k, p in lang_paths.items()}
        keys = list(lang_paths.keys())
        pairs = pw["pairs"]
        self.assertEqual(len(pairs), 6)
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                ka, kb = keys[i], keys[j]
                entry = pairs[f"{ka}_vs_{kb}"]
                self.assertTrue(entry["strictly_positive"])
                diff = self._diff_rows(rows[ka], rows[kb])
                self.assertGreater(diff, 0)
                self.assertEqual(diff, entry["diff_pixels"])

    def test_round22_complete_12of12_multilingual_paintlook_camtab2_audit(self) -> None:
        data = json.loads((ROUND22_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        audit = data["r22_paintlook_camtab2_4lang_dualsurface_audit"]
        self.assertEqual(audit["audit_id"], "r22-paintlook-camtab2-4lang-dualsurface-12pair-closure")
        self.assertEqual(audit["total_surfaces"], 2)
        self.assertEqual(audit["total_languages"], 4)
        self.assertEqual(audit["total_matrix_cells"], 8)
        self.assertEqual(audit["total_multilingual_pairs"], 12)
        self.assertTrue(audit["all_8_cells_stage_b_green"])
        self.assertTrue(audit["all_12_paintlook_camtab2_pairs_strictly_positive"])

    def test_round22_paintlook_camtab2_8cell_matrix_invariants(self) -> None:
        data = json.loads((ROUND22_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        cells = data["r22_paintlook_camtab2_4lang_dualsurface_audit"]["paintlook_camtab2_8cell_matrix"]
        self.assertEqual(len(cells), 8)
        seen = set()
        expected_lang_params = {
            "english": ("0x00", 0, 4),
            "japanese": ("0x01", 1, 12),
            "schinese": ("0x19", 23, 19),
            "tchinese": ("0x18", 27, 22),
        }
        for c in cells:
            seen.add((c["surface"], c["lang"]))
            bk4_val, fbank, sbank = expected_lang_params[c["lang"]]
            self.assertEqual(c["bk4_lang_val"], bk4_val)
            self.assertEqual(c["font_bank"], fbank)
            self.assertEqual(c["str_bank"], sbank)
            self.assertEqual(c["p12_wlan"], 1)
            self.assertEqual(c["wf12_00342260_immune"], 1)
            self.assertEqual(c["airplane_bk4_hits"], 0)
            self.assertEqual(c["nop_count"], 0)
            self.assertEqual(c["crashes"], 0)
            self.assertEqual(c["gpe_fb"], 0)
            self.assertEqual(c["stage_b_manifest_count"], 13)
        self.assertEqual(len(seen), 8)

    def test_round22_png_receipts_valid_under_85kib_and_amber(self) -> None:
        self.assertTrue(ROUND22_ASSETS_DIR.is_dir())
        alpha_digests: Dict[str, str] = {}
        comp_digests: Dict[str, str] = {}
        for stem in self.EXPECTED_STEMS:
            for variant, bucket in (("alpha", alpha_digests), ("composited", comp_digests)):
                png_path = ROUND22_ASSETS_DIR / f"{stem}-{variant}.png"
                self.assertTrue(png_path.is_file(), f"Missing Round 22 PNG: {png_path}")
                raw = png_path.read_bytes()
                self.assertLess(len(raw), 85 * 1024, f"PNG exceeds 85 KiB: {png_path}")
                w, h, _ = _decode_png_rgba_rows(raw)
                self.assertEqual((w, h), (1024, 540))
                bucket[stem] = hashlib.sha256(raw).hexdigest()
        self.assertEqual(len(set(alpha_digests.values())), len(self.EXPECTED_STEMS))
        self.assertEqual(len(set(comp_digests.values())), len(self.EXPECTED_STEMS))

        for stem, exp_amber in (
            ("r22a-menu-3layer-paintlook-english", 993),
            ("r22b-menu-3layer-paintlook-japanese", 804),
            ("r22c-menu-3layer-paintlook-tchinese", 804),
            ("r22d-status-tab2-camera-english", 311),
            ("r22e-status-tab2-camera-tchinese", 260),
        ):
            _, _, rows = _decode_png_rgba_rows((ROUND22_ASSETS_DIR / f"{stem}-alpha.png").read_bytes())
            self.assertEqual(self._count_amber(rows), exp_amber)

    def test_round22_cross_surface_paintlook_vs_camtab2_strictly_positive(self) -> None:
        cross_pairs = (
            (
                ROUND22_ASSETS_DIR / "r22a-menu-3layer-paintlook-english-alpha.png",
                ROUND22_ASSETS_DIR / "r22d-status-tab2-camera-english-alpha.png",
            ),
            (
                ROUND22_ASSETS_DIR / "r22b-menu-3layer-paintlook-japanese-alpha.png",
                ROUND15_ASSETS_DIR / "r15d-status-tab2-japanese-alpha.png",
            ),
            (
                ROUND13_ASSETS_DIR / "r13c-menu-3layer-paintlook-schinese-alpha.png",
                ROUND15_ASSETS_DIR / "r15a-status-tab2-schinese-alpha.png",
            ),
            (
                ROUND22_ASSETS_DIR / "r22c-menu-3layer-paintlook-tchinese-alpha.png",
                ROUND22_ASSETS_DIR / "r22e-status-tab2-camera-tchinese-alpha.png",
            ),
        )
        for p_menu, p_cam in cross_pairs:
            _, _, r_menu = _decode_png_rgba_rows(p_menu.read_bytes())
            _, _, r_cam = _decode_png_rgba_rows(p_cam.read_bytes())
            diff = self._diff_rows(r_menu, r_cam)
            self.assertGreater(diff, 100000)

    def test_round22_readme_and_no_tmp_scratch_residue(self) -> None:
        closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn("2026-11-14-round22-fx6-on-fx3-paintlook-camera-4lang-closure", closure_readme)
        r22_readme = (ROUND22_REPORT_DIR / "README.md").read_text(encoding="utf-8")
        for tok in ("0x11", "0x30", "Paint/Look", "Camera", "12/12", "8/8"):
            self.assertIn(tok, r22_readme)
        for forbidden in ("/Volumes/KAFU2T", "/Users/"):
            self.assertNotIn(forbidden, r22_readme)
        tmp_matches = list(pathlib.Path("/private/tmp").glob("fx6-r22*"))
        self.assertEqual(tmp_matches, [], f"Leftover scratch dirs in /private/tmp: {tmp_matches}")


class TestRound23MonitoringTab54LangClosure(unittest.TestCase):
    EXPECTED_STEMS = (
        "r23a-menu-3layer-monitoring-english",
        "r23b-menu-3layer-monitoring-tchinese",
        "r23c-status-tab5-monitoring-english",
        "r23d-status-tab5-monitoring-japanese",
        "r23e-status-tab5-monitoring-tchinese",
    )
    EXPECTED_RUN_KEYS = (
        "r23a_menu_3layer_monitoring_english",
        "r23b_menu_3layer_monitoring_tchinese",
        "r23c_status_tab5_monitoring_english",
        "r23d_status_tab5_monitoring_japanese",
        "r23e_status_tab5_monitoring_tchinese",
    )

    def test_round23_c_source_guards_and_runner_support(self) -> None:
        shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")

        self.assertIn("#if FX6_ROUND >= 23", shim_src)
        for token in (
            "FX6_R23_LANG_TELEMETRY",
            "FX6_STAGE_B_R23_BRIDGE",
            "monitoring_tab5_4lang_dualsurface=1",
            "wf12_00342260_immune=1",
        ):
            self.assertIn(token, shim_src)

        for token in (
            "/etc/fx6_stage_r23",
            "FX6_STAGE_B_R23_VERIFY_PASS",
            "monitoring_tab5_4lang_dualsurface=1",
            "wf12_00342260_immune=1",
        ):
            self.assertIn(token, verify_src)

        for token in (
            "enable_r23",
            "etc/fx6_stage_r23",
            '"r23_telemetry"',
            '"fx6-r23"',
            "monitoring_tab5_4lang_dualsurface=1",
            "choices=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]",
        ):
            self.assertIn(token, runner_src)

    def _assert_r23_overlay_dual_mode(
        self,
        lang: str,
        uxc1_name: str,
        uxc2_name: str,
        ltt_name: str,
        fontlist_key: str,
        asset_key_u1: str,
        asset_key_ltt: str,
        donor_attr_u1: str,
        donor_attr_u2: str,
        donor_attr_ltt: str,
    ) -> None:
        runner = _load_closure_module(
            f"fx6_build_and_run_round_r23_ovl_{lang}", "build_and_run_round.py"
        )
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            parent_cpio = tmp_dir / "parent.cpio"
            init_body = (
                b"#!/bin/sh\n"
                b'LD_PRELOAD="$FX6_PRELOAD" /usr/bin/appfw-launch\n'
            )
            members = (
                ("init", init_body),
                ("usr/lib/libInfraSetupFile.so", b"SETUP"),
                ("usr/lib/libInfraMediaCommon.so", b"MCOMM"),
                ("usr/lib/libInfraMediaConfig.so", b"MCFG"),
                ("usr/lib/libInfraAppRemoteBoard.so", b"RBRD"),
                ("usr/lib/libfan.so", b"FAN"),
                ("usr/lib/appFw.so", b"APPFW"),
                ("usr/lib/libWlanResource.so", b"WLAN_DONOR_12345"),
                ("usr/kmod/upm.ko", b"UPMKO"),
                ("usr/share/app/image_00_169.uxc", b"uxd\x07" + b"C" * 32),
                (f"usr/share/app/{uxc1_name}", b"uxc\x07" + b"C1" * 16),
                (f"usr/share/app/{uxc2_name}", b"uxc\x07" + b"C2" * 16),
                (f"usr/share/app/{ltt_name}", b"LTT\n" + b"CL" * 16),
                (
                    "usr/share/app/fontlist.dat",
                    f"{fontlist_key}\t/usr/share/app/{ltt_name}\t0\t0\n".encode("ascii"),
                ),
            )
            archive = b"".join(
                runner.make_cpio_member(name, body, ino=idx + 1, mode=0o100755)
                for idx, (name, body) in enumerate(members)
            ) + runner.make_cpio_member("TRAILER!!!", b"", ino=0, mode=0)
            parent_cpio.write_bytes(archive)

            class _FakeRes:
                def __init__(self, site_id: str) -> None:
                    self.site_id = site_id

            class _FakeReceipt:
                def __init__(self, before: bytes, after: bytes, sites: list) -> None:
                    self.before_sha256 = hashlib.sha256(before).hexdigest()
                    self.after_sha256 = hashlib.sha256(after).hexdigest()
                    self.changed_byte_count = 8
                    self.resolutions = [_FakeRes(s.site_id) for s in sites]

            class _FakePatcher:
                P1_P4_P8_APPFW_COMBINED_SPEC = mock.Mock(
                    library_name="appFw.so",
                    expected_size=5,
                    donor_sha256="0" * 64,
                    sites=(mock.Mock(site_id="p1"),),
                    elf_kind="so",
                    source_domain="fx6",
                )
                P1_LIB_INFRA_SETUP_FILE_SPEC = mock.Mock(spec_id="P1_s", library_name="s", sites=[mock.Mock(site_id="s1")])
                P1_LIB_INFRA_MEDIA_COMMON_SPEC = mock.Mock(spec_id="P1_c", library_name="c", sites=[mock.Mock(site_id="c1")])
                P1_LIB_INFRA_MEDIA_CONFIG_SPEC = mock.Mock(spec_id="P1_g", library_name="g", sites=[mock.Mock(site_id="g1")])
                P3_LIB_INFRA_APP_REMOTE_BOARD_SPEC = mock.Mock(spec_id="P3_r", library_name="r", sites=[mock.Mock(site_id="r1")])
                FAN_LIBFAN_SPEC = mock.Mock(spec_id="Fan_f", library_name="f", sites=[mock.Mock(site_id="f1")])
                P9_UPM_KO_SPEC = mock.Mock(spec_id="P9_u", library_name="upm.ko", sites=[mock.Mock(site_id="u1")])
                LibraryPatchSpec = lambda **kw: type("FakeSpec", (), kw)()
                PatchSiteSpec = object
                PF_R = 4

                @staticmethod
                def apply_patch_spec(data: bytes, spec: object, verify_donor_sha256: bool = True):
                    after = data + b"_P"
                    return after, _FakeReceipt(data, after, getattr(spec, "sites", []))

                @staticmethod
                def resolve_and_verify_sites(data: bytes, spec: object, expect_patched_state: bool = True):
                    return [_FakeRes("u1")]

            class _FakeVfat:
                @staticmethod
                def build_opelog_vfat_image(mode: str):
                    img = b"VFAT" * 16
                    receipt = mock.Mock(
                        mode=mode,
                        fat_type="FAT16",
                        total_bytes=len(img),
                        sha256=hashlib.sha256(img).hexdigest(),
                        precreated_dirs=("OPE", "OPE/00", "OPE/01"),
                    )
                    return img, receipt

                @staticmethod
                def verify_vfat_image(_img: bytes):
                    return mock.Mock(valid=True, errors=[])

            class _FakeBmtv:
                @staticmethod
                def build_canonical_fa0080_normal_boot_table(donor_seed_bk4_path=None):
                    return b"T"

                @staticmethod
                def synthesize_ram_shadow_bk4(**_kw):
                    bk = b"BK4\x00" + b"\x00" * 12
                    return mock.Mock(
                        bk4_bytes=bk,
                        total_bytes=len(bk),
                        sha256=hashlib.sha256(bk).hexdigest(),
                        flash_write_allowed=False,
                        active_byte8_selector=0,
                        synthesized_key_count=1,
                    )

            fake_p10 = type(
                "FakeP10",
                (),
                {
                    "spec_id": "P10_FX3_TO_FX6_KEYMAP_ADAPTER",
                    "library_name": "appFw.so",
                    "sites": (mock.Mock(site_id="p10_fn", size=4),),
                },
            )()
            fake_p12 = type(
                "FakeP12",
                (),
                {
                    "spec_id": "P12_libWlanResource_fatal_guard",
                    "library_name": "libWlanResource.so",
                    "sites": (mock.Mock(site_id="p12_wlan", size=8),),
                },
            )()

            def _fake_subproc_run(cmd, **_kw):
                out_path = pathlib.Path(cmd[-1])
                out_path.write_bytes(b"ELF_VERIFY_23")
                return mock.Mock(returncode=0, stderr="")

            donor_u1 = tmp_dir / "donor_u1.uxc"
            donor_u2 = tmp_dir / "donor_u2.uxc"
            donor_ltt = tmp_dir / "donor_font.ltt"
            donor_uxc = tmp_dir / "donor_img.uxc"
            donor_u1.write_bytes(b"uxc\x07" + b"D1" * 16)
            donor_u2.write_bytes(b"uxc\x07" + b"D2" * 16)
            donor_ltt.write_bytes(b"LTT\n" + b"FD" * 16)
            donor_uxc.write_bytes(b"uxd\x07" + b"D" * 32)
            build_dir = tmp_dir / "build"

            with mock.patch.object(
                runner, "_import_stage_a_modules", return_value=(_FakePatcher, _FakeVfat, _FakeBmtv)
            ), mock.patch.object(
                runner, "_load_p10_keymap_spec", return_value=fake_p10
            ), mock.patch.object(
                runner, "_load_p12_wlan_spec", return_value=fake_p12
            ), mock.patch.object(
                runner, "DONOR_IMAGE_00_169_UXC", donor_uxc
            ), mock.patch.object(
                runner, donor_attr_u1, donor_u1
            ), mock.patch.object(
                runner, donor_attr_u2, donor_u2
            ), mock.patch.object(
                runner, donor_attr_ltt, donor_ltt
            ), mock.patch.object(
                runner, "FX3_UPM_KO", tmp_dir / "absent_upm.ko"
            ), mock.patch.object(
                runner, "FX3_SEED_BK4", tmp_dir / "absent_seed.bin"
            ), mock.patch.object(
                runner.subprocess, "run", side_effect=_fake_subproc_run
            ):
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
                    rep, add, meta = runner.build_stage_a_overlay(
                        build_dir,
                        parent_cpio,
                        b"BK4_NTSC",
                        enable_p10=True,
                        enable_r10=True,
                        enable_p12=True,
                        enable_r12=True,
                        enable_r13=True,
                        enable_r14=True,
                        enable_r15=True,
                        enable_r16=True,
                        enable_r17=True,
                        enable_r18=True,
                        enable_r19=True,
                        enable_r20=True,
                        enable_r21=True,
                        enable_r22=True,
                        enable_r23=True,
                        lang=lang,
                        shim_bytes=b"SHIM23",
                    )
                self.assertEqual(meta["manifest_count"], 13)
                self.assertTrue(meta["r22_enabled"])
                self.assertTrue(meta["r23_enabled"])
                self.assertEqual(meta["lang"], lang)
                self.assertIn("etc/fx6_stage_r23", add)
                self.assertIn(
                    f"monitoring_tab5_4lang_dualsurface=1\nlang={lang}\n".encode("utf-8"),
                    add["etc/fx6_stage_r23"][0],
                )
                self.assertEqual(meta["lang_assets"][asset_key_u1]["source"], "cpio_preloaded")
                self.assertEqual(meta["lang_assets"][asset_key_ltt]["source"], "cpio_preloaded")
                self.assertEqual(meta["image_00_169_uxc"]["source"], "cpio_preloaded")
                self.assertEqual(meta["lang_assets"]["fontlist_dat"]["fontlist_key"], fontlist_key)
                self.assertEqual(rep[f"usr/share/app/{uxc2_name}"], b"uxc\x07" + b"C2" * 16)

                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "0"}):
                    rep2, add2, meta2 = runner.build_stage_a_overlay(
                        build_dir,
                        parent_cpio,
                        b"BK4_NTSC",
                        enable_p10=True,
                        enable_r10=True,
                        enable_p12=True,
                        enable_r12=True,
                        enable_r13=True,
                        enable_r14=True,
                        enable_r15=True,
                        enable_r16=True,
                        enable_r17=True,
                        enable_r18=True,
                        enable_r19=True,
                        enable_r20=True,
                        enable_r21=True,
                        enable_r22=True,
                        enable_r23=True,
                        lang=lang,
                        shim_bytes=b"SHIM23",
                    )
                self.assertTrue(meta2["r23_enabled"])
                self.assertIn("etc/fx6_stage_r23", add2)
                self.assertEqual(meta2["lang_assets"][asset_key_u1]["source"], "donor_o_rdonly")
                self.assertEqual(meta2["image_00_169_uxc"]["source"], "donor_o_rdonly")
                self.assertEqual(rep2[f"usr/share/app/{ltt_name}"], b"LTT\n" + b"FD" * 16)

    def test_round23_stage_a_overlay_schinese_dual_mode(self) -> None:
        self._assert_r23_overlay_dual_mode(
            lang="schinese",
            uxc1_name="string_simplifiedchinese.uxc",
            uxc2_name="string_simplifiedchinese_2.uxc",
            ltt_name="MYingHeiC-GB18030-SJ_wIcon.ltt",
            fontlist_key="FONT_S_CHINESE",
            asset_key_u1="string_simplifiedchinese",
            asset_key_ltt="font_gb18030_ltt",
            donor_attr_u1="DONOR_STRING_SCHINESE_UXC",
            donor_attr_u2="DONOR_STRING_SCHINESE_2_UXC",
            donor_attr_ltt="DONOR_FONT_SCHINESE_LTT",
        )

    def test_round23_stage_a_overlay_tchinese_dual_mode(self) -> None:
        self._assert_r23_overlay_dual_mode(
            lang="tchinese",
            uxc1_name="string_traditionalchinese.uxc",
            uxc2_name="string_traditionalchinese_2.uxc",
            ltt_name="MYingHeiC-Big5HKSCS-SJ_wIcon.ltt",
            fontlist_key="FONT_T_CHINESE",
            asset_key_u1="string_traditionalchinese",
            asset_key_ltt="font_big5hkscs_ltt",
            donor_attr_u1="DONOR_STRING_TCHINESE_UXC",
            donor_attr_u2="DONOR_STRING_TCHINESE_2_UXC",
            donor_attr_ltt="DONOR_FONT_TCHINESE_LTT",
        )

    def test_round23_stage_a_overlay_japanese_dual_mode(self) -> None:
        self._assert_r23_overlay_dual_mode(
            lang="japanese",
            uxc1_name="string_japanese.uxc",
            uxc2_name="string_japanese_2.uxc",
            ltt_name="HeiseiKakuGothW5-SJ_wIcon.ltt",
            fontlist_key="FONT_JAPANESE",
            asset_key_u1="string_japanese",
            asset_key_ltt="font_japanese_ltt",
            donor_attr_u1="DONOR_STRING_JAPANESE_UXC",
            donor_attr_u2="DONOR_STRING_JAPANESE_2_UXC",
            donor_attr_ltt="DONOR_FONT_JAPANESE_LTT",
        )

    def test_round23_stage_a_overlay_english_dual_mode(self) -> None:
        self._assert_r23_overlay_dual_mode(
            lang="english",
            uxc1_name="string_english.uxc",
            uxc2_name="string_english_2.uxc",
            ltt_name="UniversOTS-SJ_wIcon.ltt",
            fontlist_key="FONT_UNIVERS",
            asset_key_u1="string_english",
            asset_key_ltt="font_univers_ltt",
            donor_attr_u1="DONOR_STRING_ENGLISH_UXC",
            donor_attr_u2="DONOR_STRING_ENGLISH_2_UXC",
            donor_attr_ltt="DONOR_FONT_ENGLISH_LTT",
        )

    def test_round23_extract_milestones_telemetry_parser(self) -> None:
        runner = _load_closure_module(
            "fx6_build_and_run_round_r23_ms", "build_and_run_round.py"
        )
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_STAGE_B_R23_VERIFY_PASS count=13 stage_b=1 p10_keymap=1 p11_uipc=1 p12_wlan=1 p4_nd_clear=1 uxc=1 monitoring_tab5_4lang_dualsurface=1 wf12_00342260_immune=1 lang=japanese",
                "FX6_STAGE_B_R23_BRIDGE round=23 faithful=1 nop_count=0 p12_wlan=1 wf12_00342260_immune=1 p10_keymap=1 p4_nd_clear=1 p11_xlr_h1=1 lang=japanese bk4_lang=0x01 enum=0x2b30_LANGUAGE_JAPANESE font_bank=1 str_bank=12 monitoring_tab5_4lang_dualsurface=1",
                "FX6_R23_LANG_TELEMETRY reason=pump lang=japanese bk4_lang_id=0x02cf019c bk4_lang_val=0x01 lang_enum=0x2b30_LANGUAGE_JAPANESE font_bank=1 str_bank=12 lang_bk4_hits=3 airplane_bk4_hits=0 p4_nd_clear=1 p10_keymap=1 p11_xlr_h1=1 p12_wlan=1 wf12_00342260_immune=1 font_create=28393 glyph_blits=15389 icon_blits=8206 gpe_alloc=178 gpe_fb=0 monitoring_tab5_4lang_dualsurface=1 subst_color=0 subst_image=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        self.assertEqual(ms["prefix_counts"]["FX6_R23_"], 1)
        r23 = ms["r23_telemetry"]
        self.assertIsNotNone(r23)
        self.assertEqual(r23["lang"], "japanese")
        self.assertEqual(r23["bk4_lang_val"], "0x01")
        self.assertEqual(r23["font_bank"], 1)
        self.assertEqual(r23["str_bank"], 12)
        self.assertEqual(r23["p11_xlr_h1"], 1)
        self.assertEqual(r23["p12_wlan"], 1)
        self.assertEqual(r23["wf12_00342260_immune"], 1)
        self.assertEqual(r23["airplane_bk4_hits"], 0)
        self.assertEqual(r23["gpe_alloc"], 178)
        self.assertEqual(r23["gpe_fb"], 0)
        self.assertEqual(r23["monitoring_tab5_4lang_dualsurface"], 1)
        self.assertEqual(r23["subst_color"], 0)
        self.assertEqual(r23["subst_image"], 0)

    def test_round23_report_and_summary_json_invariants(self) -> None:
        self.assertTrue((ROUND23_REPORT_DIR / "README.md").is_file())
        summary_path = ROUND23_REPORT_DIR / "summary.json"
        self.assertTrue(summary_path.is_file())
        raw_text = summary_path.read_text(encoding="utf-8")
        for forbidden in ("/Volumes/KAFU2T", "/private/tmp", "/Users/"):
            self.assertNotIn(forbidden, raw_text)
        data = json.loads(raw_text)
        self.assertEqual(data["schema"], "fx6-on-fx3-round23-monitoring-tab5-4lang-dualsurface-closure-v1")
        self.assertIn("Linux version 4.9.337-scel+", data["kernel_version"])
        self.assertEqual(set(data["languages"].keys()), {"en", "tchinese", "japanese", "schinese"})

        runs = data["runs"]
        self.assertEqual(set(runs.keys()), set(self.EXPECTED_RUN_KEYS))
        expectations = {
            "r23a_menu_3layer_monitoring_english": ("english", "0x00", 0, 4, "monitoring_3layer_menu", "0x11", "31procam_menu_layer_3rd_presenter", "32procam_menu_layer_3rd_controller", 437575, 220, 290),
            "r23b_menu_3layer_monitoring_tchinese": ("tchinese", "0x18", 27, 22, "monitoring_3layer_menu", "0x11", "31procam_menu_layer_3rd_presenter", "32procam_menu_layer_3rd_controller", 437575, 223, 309),
            "r23c_status_tab5_monitoring_english": ("english", "0x00", 0, 4, "status_check_tab5_monitoring", "0x33", "40procam_touch_status_monitoring_presenter", "41procam_touch_status_monitoring_controller", 437883, 106, 323),
            "r23d_status_tab5_monitoring_japanese": ("japanese", "0x01", 1, 12, "status_check_tab5_monitoring", "0x33", "40procam_touch_status_monitoring_presenter", "41procam_touch_status_monitoring_controller", 437403, 106, 266),
            "r23e_status_tab5_monitoring_tchinese": ("tchinese", "0x18", 27, 22, "status_check_tab5_monitoring", "0x33", "40procam_touch_status_monitoring_presenter", "41procam_touch_status_monitoring_controller", 437403, 106, 266),
        }
        for key, (lang, bk4_val, fbank, sbank, surf, sid, pres, ctrl, exp_px, exp_col, exp_amber) in expectations.items():
            run = runs[key]
            self.assertEqual(run["round"], 23)
            self.assertEqual(run["lang"], lang)
            self.assertEqual(run["surface"], surf)
            self.assertEqual(run["target_sid"], sid)
            self.assertEqual(run["target_presenter"], pres)
            self.assertEqual(run["target_controller"], ctrl)
            self.assertEqual(run["nop_count"], 0)
            self.assertEqual(run["crashes"], 0)
            self.assertGreaterEqual(run["ldec103_ioctl_count"], 55)
            self.assertGreaterEqual(run["total_threads_seen"], 161)
            self.assertEqual(
                run["faithful_invariants"],
                {
                    "FX6_NATIVE_FAITHFUL": 1,
                    "subst_color": 0,
                    "subst_image": 0,
                    "forced_render": 0,
                    "skipped_node": 0,
                    "lock_bypass": 0,
                },
            )
            sb = run["stage_b"]
            self.assertTrue(sb["r22_enabled"])
            self.assertTrue(sb["r23_enabled"])
            self.assertEqual(sb["lang"], lang)
            self.assertEqual(sb["manifest_count"], 13)
            self.assertEqual(len(sb["verify_bin_sha256"]), 64)
            self.assertIn("P12_libWlanResource_fatal_guard", sb["patches"])
            self.assertIn("P10_FX3_TO_FX6_KEYMAP_ADAPTER", sb["patches"])
            self.assertIn(
                "P4_appfw_set_nd_filter_mode_clear",
                sb["patches"]["P1_P4_P8_P10_appFw_combined"]["sites"],
            )
            self.assertGreaterEqual(run["prefix_counts"]["FX6_STAGE_A_"], 21)
            self.assertGreaterEqual(run["prefix_counts"]["FX6_STAGE_B_"], 38)
            self.assertGreaterEqual(run["prefix_counts"]["FX6_R23_"], 150)
            telem = run["r23_telemetry"]
            self.assertEqual(telem["p4_nd_clear"], 1)
            self.assertEqual(telem["p10_keymap"], 1)
            self.assertEqual(telem["p11_xlr_h1"], 1)
            self.assertEqual(telem["lang"], lang)
            self.assertEqual(telem["bk4_lang_val"], bk4_val)
            self.assertEqual(telem["font_bank"], fbank)
            self.assertEqual(telem["str_bank"], sbank)
            self.assertEqual(telem["airplane_bk4_hits"], 0)
            self.assertEqual(telem["p12_wlan"], 1)
            self.assertEqual(telem["wf12_00342260_immune"], 1)
            self.assertEqual(telem["gpe_fb"], 0)
            self.assertEqual(telem["monitoring_tab5_4lang_dualsurface"], 1)
            self.assertEqual(telem["subst_color"], 0)
            self.assertEqual(telem["subst_image"], 0)
            self.assertEqual(run["gpe0_readback"]["nonzero_pixels"], exp_px)
            self.assertEqual(run["gpe0_readback"]["unique_colors"], exp_col)
            self.assertEqual(run["amber_0xffffaa00_pixels"], exp_amber)

    def test_round23_stage_b_manifest_13_sha256_integrity(self) -> None:
        data = json.loads((ROUND23_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        shared_by_path: Dict[str, str] = {}
        for key in self.EXPECTED_RUN_KEYS:
            items = data["runs"][key]["stage_b"]["manifest_items"]
            self.assertEqual(len(items), 13)
            for item in items:
                gpath = item["guest_path"]
                digest = item["sha256"]
                self.assertEqual(len(digest), 64)
                int(digest, 16)
                if gpath == "/usr/lib/libgrm-fbinit9.so":
                    continue
                if gpath in shared_by_path:
                    self.assertEqual(shared_by_path[gpath], digest, f"SHA mismatch on {gpath}")
                else:
                    shared_by_path[gpath] = digest
        self.assertEqual(len(shared_by_path), 12)

    @staticmethod
    def _diff_rows(ra: List[bytes], rb: List[bytes]) -> int:
        import operator
        ne = operator.ne
        return sum(
            sum(map(ne, memoryview(ya).cast("I"), memoryview(yb).cast("I")))
            for ya, yb in zip(ra, rb)
            if ya != yb
        )

    @staticmethod
    def _count_amber(rows: List[bytes]) -> int:
        amber_word = int.from_bytes(b"\xff\xaa\x00\xff", sys.byteorder)
        return sum(
            sum(1 for px in memoryview(row).cast("I") if px == amber_word)
            for row in rows
            if b"\xff\xaa\x00\xff" in row
        )

    def test_round23_monitoring_3layer_menu_4lang_6pairs_pixel_deltas_exact(self) -> None:
        data = json.loads((ROUND23_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        pw = data["r23_monitoring_tab5_4lang_dualsurface_audit"]["monitoring_3layer_menu_4lang_pairwise"]
        self.assertEqual(pw["language_count"], 4)
        self.assertEqual(pw["pair_count"], 6)
        self.assertTrue(pw["all_6_pairs_strictly_positive"])
        self.assertEqual(pw["min_diff_pixels"], 5728)
        self.assertEqual(pw["max_diff_pixels"], 11028)

        lang_paths = {
            "english": ROUND23_ASSETS_DIR / "r23a-menu-3layer-monitoring-english-alpha.png",
            "japanese": ROUND16_ASSETS_DIR / "r16d-menu-3layer-monitoring-japanese-alpha.png",
            "schinese": ROUND15_ASSETS_DIR / "r15c-menu-3layer-monitoring-schinese-alpha.png",
            "tchinese": ROUND23_ASSETS_DIR / "r23b-menu-3layer-monitoring-tchinese-alpha.png",
        }
        rows = {k: _decode_png_rgba_rows(p.read_bytes())[2] for k, p in lang_paths.items()}
        keys = list(lang_paths.keys())
        pairs = pw["pairs"]
        self.assertEqual(len(pairs), 6)
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                ka, kb = keys[i], keys[j]
                entry = pairs[f"{ka}_vs_{kb}"]
                self.assertTrue(entry["strictly_positive"])
                diff = self._diff_rows(rows[ka], rows[kb])
                self.assertGreater(diff, 0)
                self.assertEqual(diff, entry["diff_pixels"])

    def test_round23_status_tab5_monitoring_4lang_6pairs_pixel_deltas_exact(self) -> None:
        data = json.loads((ROUND23_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        pw = data["r23_monitoring_tab5_4lang_dualsurface_audit"]["status_tab5_monitoring_4lang_pairwise"]
        self.assertEqual(pw["language_count"], 4)
        self.assertEqual(pw["pair_count"], 6)
        self.assertTrue(pw["all_6_pairs_strictly_positive"])
        self.assertEqual(pw["min_diff_pixels"], 11755)
        self.assertEqual(pw["max_diff_pixels"], 27821)

        lang_paths = {
            "english": ROUND23_ASSETS_DIR / "r23c-status-tab5-monitoring-english-alpha.png",
            "japanese": ROUND23_ASSETS_DIR / "r23d-status-tab5-monitoring-japanese-alpha.png",
            "schinese": ROUND16_ASSETS_DIR / "r16b-status-tab5-schinese-alpha.png",
            "tchinese": ROUND23_ASSETS_DIR / "r23e-status-tab5-monitoring-tchinese-alpha.png",
        }
        rows = {k: _decode_png_rgba_rows(p.read_bytes())[2] for k, p in lang_paths.items()}
        keys = list(lang_paths.keys())
        pairs = pw["pairs"]
        self.assertEqual(len(pairs), 6)
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                ka, kb = keys[i], keys[j]
                entry = pairs[f"{ka}_vs_{kb}"]
                self.assertTrue(entry["strictly_positive"])
                diff = self._diff_rows(rows[ka], rows[kb])
                self.assertGreater(diff, 0)
                self.assertEqual(diff, entry["diff_pixels"])

    def test_round23_complete_12of12_multilingual_monitoring_tab5_audit(self) -> None:
        data = json.loads((ROUND23_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        audit = data["r23_monitoring_tab5_4lang_dualsurface_audit"]
        self.assertEqual(audit["audit_id"], "r23-monitoring-tab5-4lang-dualsurface-12pair-closure")
        self.assertEqual(audit["total_surfaces"], 2)
        self.assertEqual(audit["total_languages"], 4)
        self.assertEqual(audit["total_matrix_cells"], 8)
        self.assertEqual(audit["total_multilingual_pairs"], 12)
        self.assertTrue(audit["all_8_cells_stage_b_green"])
        self.assertTrue(audit["all_12_monitoring_tab5_pairs_strictly_positive"])

    def test_round23_monitoring_tab5_8cell_matrix_invariants(self) -> None:
        data = json.loads((ROUND23_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        cells = data["r23_monitoring_tab5_4lang_dualsurface_audit"]["monitoring_tab5_8cell_matrix"]
        self.assertEqual(len(cells), 8)
        seen = set()
        expected_lang_params = {
            "english": ("0x00", 0, 4),
            "japanese": ("0x01", 1, 12),
            "schinese": ("0x19", 23, 19),
            "tchinese": ("0x18", 27, 22),
        }
        for c in cells:
            seen.add((c["surface"], c["lang"]))
            bk4_val, fbank, sbank = expected_lang_params[c["lang"]]
            self.assertEqual(c["bk4_lang_val"], bk4_val)
            self.assertEqual(c["font_bank"], fbank)
            self.assertEqual(c["str_bank"], sbank)
            self.assertEqual(c["p12_wlan"], 1)
            self.assertEqual(c["wf12_00342260_immune"], 1)
            self.assertEqual(c["airplane_bk4_hits"], 0)
            self.assertEqual(c["nop_count"], 0)
            self.assertEqual(c["crashes"], 0)
            self.assertEqual(c["gpe_fb"], 0)
            self.assertEqual(c["stage_b_manifest_count"], 13)
        self.assertEqual(len(seen), 8)

    def test_round23_png_receipts_valid_under_85kib_and_amber(self) -> None:
        self.assertTrue(ROUND23_ASSETS_DIR.is_dir())
        alpha_digests: Dict[str, str] = {}
        comp_digests: Dict[str, str] = {}
        for stem in self.EXPECTED_STEMS:
            for variant, bucket in (("alpha", alpha_digests), ("composited", comp_digests)):
                png_path = ROUND23_ASSETS_DIR / f"{stem}-{variant}.png"
                self.assertTrue(png_path.is_file(), f"Missing Round 23 PNG: {png_path}")
                raw = png_path.read_bytes()
                self.assertLess(len(raw), 85 * 1024, f"PNG exceeds 85 KiB: {png_path}")
                w, h, _ = _decode_png_rgba_rows(raw)
                self.assertEqual((w, h), (1024, 540))
                bucket[stem] = hashlib.sha256(raw).hexdigest()
        self.assertEqual(len(set(alpha_digests.values())), len(self.EXPECTED_STEMS))
        self.assertEqual(len(set(comp_digests.values())), len(self.EXPECTED_STEMS))

        for stem, exp_amber in (
            ("r23a-menu-3layer-monitoring-english", 290),
            ("r23b-menu-3layer-monitoring-tchinese", 309),
            ("r23c-status-tab5-monitoring-english", 323),
            ("r23d-status-tab5-monitoring-japanese", 266),
            ("r23e-status-tab5-monitoring-tchinese", 266),
        ):
            _, _, rows = _decode_png_rgba_rows((ROUND23_ASSETS_DIR / f"{stem}-alpha.png").read_bytes())
            self.assertEqual(self._count_amber(rows), exp_amber)

    def test_round23_cross_surface_monitoring_vs_tab5_strictly_positive(self) -> None:
        cross_pairs = (
            (
                ROUND23_ASSETS_DIR / "r23a-menu-3layer-monitoring-english-alpha.png",
                ROUND23_ASSETS_DIR / "r23c-status-tab5-monitoring-english-alpha.png",
            ),
            (
                ROUND16_ASSETS_DIR / "r16d-menu-3layer-monitoring-japanese-alpha.png",
                ROUND23_ASSETS_DIR / "r23d-status-tab5-monitoring-japanese-alpha.png",
            ),
            (
                ROUND15_ASSETS_DIR / "r15c-menu-3layer-monitoring-schinese-alpha.png",
                ROUND16_ASSETS_DIR / "r16b-status-tab5-schinese-alpha.png",
            ),
            (
                ROUND23_ASSETS_DIR / "r23b-menu-3layer-monitoring-tchinese-alpha.png",
                ROUND23_ASSETS_DIR / "r23e-status-tab5-monitoring-tchinese-alpha.png",
            ),
        )
        for p_menu, p_tab5 in cross_pairs:
            _, _, r_menu = _decode_png_rgba_rows(p_menu.read_bytes())
            _, _, r_tab5 = _decode_png_rgba_rows(p_tab5.read_bytes())
            diff = self._diff_rows(r_menu, r_tab5)
            self.assertGreater(diff, 100000)

    def test_round23_readme_and_no_tmp_scratch_residue(self) -> None:
        closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn("2026-11-14-round23-fx6-on-fx3-monitoring-4lang-dualsurface-closure", closure_readme)
        r23_readme = (ROUND23_REPORT_DIR / "README.md").read_text(encoding="utf-8")
        for tok in ("0x11", "0x33", "Monitoring", "Tab 5", "12/12", "8/8"):
            self.assertIn(tok, r23_readme)
        for forbidden in ("/Volumes/KAFU2T", "/Users/"):
            self.assertNotIn(forbidden, r23_readme)
        tmp_matches = list(pathlib.Path("/private/tmp").glob("fx6-r23*"))
        self.assertEqual(tmp_matches, [], f"Leftover scratch dirs in /private/tmp: {tmp_matches}")


if __name__ == "__main__":
    unittest.main()


