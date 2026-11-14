#!/usr/bin/env python3
"""Offline clean-room unit tests for FX6 native presenter closure (Rounds 1-10)."""
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


def _decode_png_rgba_rows(png_bytes: bytes) -> Tuple[int, int, List[bytes]]:
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
    return width, height, rows


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
        self.assertIn("choices=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]", runner_src)
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
            r'tmp_prefix\s*=\s*\(\s*"fx6-r10"\s+if\s+args\.round\s*>=\s*10\s+else\s+\("fx6-r9"\s+if\s+args\.round\s*>=\s*9',
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
            "choices=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]",
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


if __name__ == "__main__":
    unittest.main()
