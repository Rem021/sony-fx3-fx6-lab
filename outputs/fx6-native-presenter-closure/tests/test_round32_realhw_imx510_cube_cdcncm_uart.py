#!/usr/bin/env python3
"""Offline dual-mode unit tests for FX6-on-FX3 Round 32 real-hardware QEMU rehearsal."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import pathlib
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from typing import Dict, List, Tuple
from unittest import mock

TESTS_DIR = pathlib.Path(__file__).resolve().parent
CLOSURE_DIR = TESTS_DIR.parent
REPO_ROOT = CLOSURE_DIR.parent.parent
ROUND32_REPORT_DIR = (
    REPO_ROOT / "reports" / "2026-11-15-round32-realhw-imx510-cube-cdcncm-uart-qemu"
)
ROUND32_ASSETS_DIR = ROUND32_REPORT_DIR / "assets"


def _load_closure_module(module_name: str, filename: str):
    path = CLOSURE_DIR / filename
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


def _decode_png_rgba_rows(png_bytes: bytes) -> Tuple[int, int, List[bytes]]:
    if png_bytes[:8] != b"\x89PNG\r\n\x1a\n":
        raise AssertionError("Invalid PNG signature")
    pos = 8
    width = 0
    height = 0
    seen_ihdr = False
    seen_iend = False
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
                    f"Unexpected PNG mode {(bit_depth, color_type, comp, filt, interlace)}"
                )
            seen_ihdr = True
        elif ctype == b"IDAT":
            idat_parts.append(payload)
        elif ctype == b"IEND":
            seen_iend = True
        pos = crc_end
    if not seen_ihdr or not seen_iend:
        raise AssertionError("Missing IHDR or IEND chunk")
    raw_scanlines = zlib.decompress(b"".join(idat_parts))
    stride = width * 4
    rows: List[bytes] = []
    p = 0
    prev = bytearray(stride)
    for _ in range(height):
        filt = raw_scanlines[p]
        p += 1
        row = bytearray(raw_scanlines[p : p + stride])
        p += stride
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


def _build_mock_cpio_and_fakes(runner, tmp_dir: pathlib.Path):
    parent_cpio = tmp_dir / "parent.cpio"
    init_body = (
        b"#!/bin/sh\n"
        b"mount -t devtmpfs devtmpfs /dev\n"
        b"echo FX3_DEVTMPFS_RC=$?\n"
        b'LD_PRELOAD="$FX6_PRELOAD" /usr/bin/appfw-launch\n'
    )
    members = (
        ("init", init_body),
        ("usr/bin/im.elf", b"\x7fELF" + b"STOCK_IM_ELF_BYTES" * 16),
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
            library_name="appFw.so", expected_size=5, donor_sha256="0" * 64,
            sites=(mock.Mock(site_id="p1"),), elf_kind="so", source_domain="fx6",
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
            return img, mock.Mock(
                mode=mode, fat_type="FAT16", total_bytes=len(img),
                sha256=hashlib.sha256(img).hexdigest(),
                precreated_dirs=("OPE", "OPE/00", "OPE/01"),
            )

        @staticmethod
        def verify_vfat_image(_img: bytes):
            return mock.Mock(valid=True, errors=[])

    class _FakeBmtv:
        @staticmethod
        def build_canonical_fa0080_normal_boot_table(donor_seed_bk4_path=None):
            return b"T"

        @staticmethod
        def synthesize_ram_shadow_bk4(**_kw):
            bk4 = b"BK4" * 16
            return mock.Mock(
                bk4_bytes=bk4, total_bytes=len(bk4),
                sha256=hashlib.sha256(bk4).hexdigest(),
                flash_write_allowed=False, active_byte8_selector=0, synthesized_key_count=1,
            )

    def fake_subproc_run(cmd, **_kw):
        out_idx = cmd.index("-o") + 1
        pathlib.Path(cmd[out_idx]).write_bytes(b"\x7fELF" + b"\x00" * 60)
        return mock.Mock(returncode=0, stdout="", stderr="")

    fake_jit_meta = {
        "bytes": 64, "sha256": "a" * 64, "e_type": 3, "e_machine": 183,
        "pt_load_count": 3, "pt_load_align": "0x10000", "has_pt_dynamic": True,
    }
    return parent_cpio, _FakePatcher, _FakeVfat, _FakeBmtv, fake_subproc_run, fake_jit_meta


class TestRound32RealHwImx510CubeCdcncmUart(unittest.TestCase):
    EXPECTED_RUN_KEYS = (
        "r32a_imx510_cube_big6_schinese",
        "r32b_cdcncm_usb_0da1",
        "r32c_uart_6stage_triage",
    )

    def test_01_round32_c_and_python_source_contracts(self) -> None:
        shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")

        self.assertIn("#if FX6_ROUND >= 32", shim_src)
        for token in (
            "FX6_R32_IMX510_CUBE_BRIDGE",
            "FX6_R32_UART_CP stage=6",
            "FX6_R32_LANG_TELEMETRY",
            "FX6_STAGE_B_R32_BRIDGE",
            "/mnt/r32_p2/setting/psd.bin",
            "/mnt/r32_p2/setting/defdet.bin",
            "/usr/lib/libsencore.so",
            "/tmp/mlut_slot0.bin",
            "mlut_baked_into_master=",
        ):
            self.assertIn(token, shim_src)

        for token in (
            "r32_is_nonfinite_token",
            "r32_parse_and_load_cube",
            "setup_r32_imx510_cube_probe",
            "run_r32_cdcncm_usb_0da1_probe",
            "r32_uart_preflight_gate",
            "run_r32_uart_6stage_triage_probe",
            "--r32-cdcncm-usb-0da1",
            "--r32-uart-6stage",
            "/etc/fx6_stage_r32",
            "FX6_R32_IMX510_CUBE_INIT",
            "FX6_R32_CDCNCM_USB_0DA1",
            "FX6_R32_UART_6STAGE",
        ):
            self.assertIn(token, verify_src)

        for token in (
            "enable_r32",
            "r32_mode",
            "--r32-mode",
            "imx510_cube_big6",
            "cdcncm_usb_0da1",
            "uart_6stage_triage",
            "etc/fx6_stage_r32",
            "FX6_R32_CDCNCM_EXIT",
            "FX6_R32_UART_EXIT",
            '"r32_telemetry"',
            "choices=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43]",
        ):
            self.assertIn(token, runner_src)

    def test_02_round32_native_verify_c_compiles_with_zig_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r32_verc", "build_and_run_round.py")
        self.assertTrue(runner.ZIG.is_file(), f"Missing zig compiler at {runner.ZIG}")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            cache_dir = tmp_dir / "zig-cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            for clean_flag in ("0", "1"):
                out_bin = tmp_dir / f"fx6-stage-a-verify-r32-{clean_flag}"
                env = os.environ.copy()
                env["FX3_FX6_FORCE_CLEAN_ROOM"] = clean_flag
                env["ZIG_LOCAL_CACHE_DIR"] = str(cache_dir / "local")
                env["ZIG_GLOBAL_CACHE_DIR"] = str(cache_dir / "global")
                res = subprocess.run(
                    [
                        str(runner.ZIG), "cc", "-target", "aarch64-linux-gnu.2.17",
                        "-std=gnu11", "-no-pie", "-fno-sanitize=all", "-fno-stack-protector",
                        "-O2", "-Wall", "-Wextra", "-Werror",
                        str(CLOSURE_DIR / "fx6-stage-a-verify.c"), "-ldl", "-o", str(out_bin),
                    ],
                    env=env, capture_output=True, text=True,
                )
                self.assertEqual(res.returncode, 0, f"zig cc failed in clean_room={clean_flag}:\n{res.stderr}")
                self.assertTrue(out_bin.is_file())
                self.assertEqual(out_bin.read_bytes()[:4], b"\x7fELF")

    def test_03_round32_build_binaries_compiles_shim_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r32_shimc", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            for clean_flag in ("0", "1"):
                work = pathlib.Path(tmp) / f"shim_{clean_flag}"
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                    launcher_b, shim_b, meta = runner.build_binaries(
                        work,
                        fx6_round=32,
                        restore_infra70=1,
                        restore_all_early=0,
                        reply_all_200d=1,
                        initial_setting_done=1,
                        key_seq="0x7028:120:5500",
                        key_settle_ms=5500,
                        lang="schinese",
                    )
                self.assertEqual(launcher_b[:4], b"\x7fELF")
                self.assertEqual(shim_b[:4], b"\x7fELF")
                self.assertGreater(meta["shim_bytes"], 10000)

    def test_04_round32_extract_milestones_r32a_imx510_cube_and_bridge(self) -> None:
        runner = _load_closure_module("fx6_brr_r32_msa", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R32_IMX510_CUBE_INIT psd_erofs=1 psd_errno=30 defdet_erofs=1 defdet_errno=30 sensor_cal_sha256_before=aaa sensor_cal_sha256_after=aaa sensor_cal_sha256_match=1 mlut_lut_size=17 mlut_entries=4913 mlut_slot0_loaded=1 mlut_slot0_bytes=58972 mlut_slot0_sha256=bbb mlut_baked_into_master=0 bad_cube_nan_detected=1 bad_cube_rejected=1 slot0_untouched_on_bad_cube=1 sencore_elf_ok=1 appfw_elf_ok=1 emmc_write_count=0 r32_init_ok=1 verify_us=793999",
                "FX6_R32_UART_CP stage=4 name=STAGE_A_47US_DLOPEN baud=460800 framing=8N1 logic_mv=1800",
                "FX6_R32_UART_CP stage=5 name=STRATEGY_A_MOUNT ro_guards=1 baud=460800 framing=8N1 logic_mv=1800",
                "FX6_R32_IMX510_CUBE_BRIDGE sensor=IMX510 imx510_lcg_iso=800 imx510_hcg_iso=12800 imx510_readout_us=8700 imx510_dual_base_ok=1 sencore_dlopen_ok=1 sencore_dlsym_ok=1 p2_psd_erofs=1 p2_defdet_erofs=1 sensor_cal_erofs_ok=1 mlut_slot0_active=1 mlut_lut_size=17 mlut_baked_into_master=0 slog3_xavc_master_clean=1 emmc_write_count=0 r32_bridge_ok=1",
                "FX6_R32_UART_CP stage=6 name=STAGE_B_APPFW_BIG6 baud=460800 framing=8N1 logic_mv=1800 sid=0x0a emmc_write_count=0",
                "FX6_STAGE_B_R32_BRIDGE round=32 faithful=1 nop_count=0 p12_wlan=1 wf12_00342260_immune=1 p10_keymap=1 p4_nd_clear=1 p11_xlr_h1=1 lang=schinese bk4_lang=0x19 enum=0x2b45_CHINESE_SIMPLIFIED font_bank=23 str_bank=19 imx510_dual_base=1 p2_psd_defdet_erofs=1 cube_3d_mlut_non_bake=1 zero_diff_libs_dlopen=1 cdcncm_0da1_intact=1 ttyama0_6stage_1v8=1 emmc_write_count=0",
                "FX6_R32_LANG_TELEMETRY reason=pump lang=schinese gpe_fb=0 imx510_dual_base_ok=1 p2_psd_erofs=1 p2_defdet_erofs=1 mlut_slot0_active=1 mlut_baked_into_master=0 r32_bridge_ok=1 realhw_imx510_cube_cdcncm_uart=1 emmc_write_count=0 subst_color=0 subst_image=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        r32 = ms["r32_telemetry"]
        self.assertIsNotNone(r32)
        self.assertEqual(r32["imx510_cube_init"]["psd_errno"], 30)
        self.assertEqual(r32["imx510_cube_init"]["bad_cube_rejected"], 1)
        self.assertEqual(r32["imx510_cube_bridge"]["imx510_lcg_iso"], 800)
        self.assertEqual(r32["imx510_cube_bridge"]["imx510_hcg_iso"], 12800)
        self.assertEqual(r32["imx510_cube_bridge"]["mlut_baked_into_master"], 0)
        self.assertEqual(len(r32["uart_checkpoints"]), 3)
        self.assertEqual(r32["stage_b_bridge"]["round"], 32)
        self.assertEqual(r32["lang_telemetry"]["gpe_fb"], 0)

    def test_05_round32_extract_milestones_r32b_cdcncm_usb_0da1(self) -> None:
        runner = _load_closure_module("fx6_brr_r32_msb", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R32_CDCNCM_USB_0DA1 dlopen_libs_ok=4 dlsym_resolved=8 zero_diff_libs_ok=1 rf_nvs_erofs_ok=1 rf_nvs_writes=0 rf_nvs_p12_errno=30 rf_nvs_p13_errno=30 bt_ttyama3_masked=1 bt_wait_ms=0 bt_probe_us=23 usb_cdcncm_link_mbps=1000 usb_ptp_ip_port=15740 usb_cdcncm_tested=1 usb_vid=0x054c usb_msc_pid=0x0da1 usb_service_pid=0x0336 usb_0da1_intact=1 usb_0336_preserved=1 emmc_write_count=0 r32b_ok=1 verify_us=15002",
                "FX6_R32_CDCNCM_RC=0",
                "FX6_R32_CDCNCM_EXIT rc=0 emmc_write_count=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        r32 = ms["r32_telemetry"]
        self.assertIsNotNone(r32)
        self.assertEqual(r32["cdcncm_rc"], 0)
        c = r32["cdcncm_usb_0da1"]
        self.assertEqual(c["dlopen_libs_ok"], 4)
        self.assertEqual(c["dlsym_resolved"], 8)
        self.assertEqual(c["rf_nvs_erofs_ok"], 1)
        self.assertEqual(c["bt_wait_ms"], 0)
        self.assertEqual(c["usb_0da1_intact"], 1)
        self.assertEqual(c["r32b_ok"], 1)

    def test_06_round32_extract_milestones_r32c_uart_6stage_triage(self) -> None:
        runner = _load_closure_module("fx6_brr_r32_msc", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R32_UART_CP stage=1 name=IPL_BL2 baud=460800 framing=8N1 logic_mv=1800",
                "FX6_R32_UART_CP stage=2 name=KERNEL_4_9_337_SCEL release=4.9.337-scel+ baud=460800 framing=8N1 logic_mv=1800",
                "FX6_R32_UART_CP stage=3 name=SETUP_NFLASH devtmpfs_rc=0 baud=460800 framing=8N1 logic_mv=1800",
                "FX6_R32_UART_CP stage=4 name=STAGE_A_47US_DLOPEN trigger_us=47 baud=460800 framing=8N1 logic_mv=1800",
                "FX6_R32_UART_CP stage=5 name=STRATEGY_A_MOUNT ro_guards=1 baud=460800 framing=8N1 logic_mv=1800",
                "FX6_R32_UART_CP stage=6 name=STAGE_B_APPFW_BIG6 sid=0x0a baud=460800 framing=8N1 logic_mv=1800",
                "FX6_R32_UART_6STAGE kernel_release_ok=1 cmdline_ttyama0_ok=1 uart_device=/dev/ttyAMA0 uart_baud=460800 uart_framing=8N1 uart_logic_mv=1800 uart_max_safe_mv=1950 checkpoints_passed=6 uart_nominal_ok=1 vmc_bncm1_contention_aborted=1 vmc_bncm1_abort_rc=-16 uart_overvoltage_injected_mv=3300 uart_overvoltage_aborted=1 uart_overvoltage_abort_rc=-34 emmc_write_count=0 r32c_ok=1 verify_us=1536",
                "FX6_R32_UART_RC=0",
                "FX6_R32_UART_EXIT rc=0 emmc_write_count=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        r32 = ms["r32_telemetry"]
        self.assertIsNotNone(r32)
        self.assertEqual(r32["uart_rc"], 0)
        self.assertEqual(len(r32["uart_checkpoints"]), 6)
        u = r32["uart_6stage"]
        self.assertEqual(u["checkpoints_passed"], 6)
        self.assertEqual(u["vmc_bncm1_contention_aborted"], 1)
        self.assertEqual(u["vmc_bncm1_abort_rc"], -16)
        self.assertEqual(u["uart_overvoltage_aborted"], 1)
        self.assertEqual(u["uart_overvoltage_abort_rc"], -34)
        self.assertEqual(u["r32c_ok"], 1)

    def test_07_round32_stage_a_overlay_imx510_cube_big6_mocked_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r32_ovl_a", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            parent_cpio, fp, fv, fb, fake_run, jit_meta = _build_mock_cpio_and_fakes(runner, tmp_dir)
            for clean_flag in ("0", "1"):
                work = tmp_dir / f"r32_a_{clean_flag}"
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}), \
                     mock.patch.object(runner, "_import_stage_a_modules", return_value=(fp, fv, fb)), \
                     mock.patch.object(runner, "_load_p10_keymap_spec", return_value=mock.Mock(spec_id="P10_k", library_name="appFw.so", sites=(mock.Mock(site_id="p10", size=4),))), \
                     mock.patch.object(runner, "_load_p12_wlan_spec", return_value=mock.Mock(spec_id="P12_w", library_name="libWlanResource.so", sites=(mock.Mock(site_id="p12", size=8),))), \
                     mock.patch.object(runner, "build_hardened_libjit_so", return_value=(b"\x7fELF_JIT", dict(jit_meta))), \
                     mock.patch.object(runner, "build_r30_tier0_libjit_so", return_value=(b"\x7fELF_R30_JIT", dict(jit_meta))), \
                     mock.patch.object(runner.subprocess, "run", side_effect=fake_run):
                    rep, add, meta = runner.build_stage_a_overlay(
                        work, parent_cpio, b"BK4NTSC",
                        enable_p10=True, enable_r10=True, enable_p12=True, enable_r28=True,
                        enable_r30=True, r30_mode="peripheral_big6",
                        enable_r31=True, r31_mode="keymap_big6",
                        enable_r32=True, r32_mode="imx510_cube_big6",
                        sd_manifest_mode="valid", lang="schinese", shim_bytes=b"SHIM",
                    )
                init_out = rep["init"].decode("utf-8")
                self.assertNotIn("--r32-cdcncm-usb-0da1", init_out)
                self.assertNotIn("--r32-uart-6stage", init_out)
                self.assertIn("--sd-gate", init_out)
                self.assertIn("etc/fx6_stage_r32", add)
                self.assertIn("r32_mode=imx510_cube_big6", add["etc/fx6_stage_r32"][0].decode("utf-8"))
                self.assertTrue(meta["r32_enabled"])
                self.assertEqual(meta["r32"]["r32_mode"], "imx510_cube_big6")
                self.assertEqual(meta["r32"]["dual_base_iso_lcg"], 800)
                self.assertEqual(meta["r32"]["dual_base_iso_hcg"], 12800)
                self.assertEqual(meta["r32"]["mlut_baked_into_master"], 0)

    def test_08_round32_stage_a_overlay_cdcncm_usb_0da1_mocked_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r32_ovl_b", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            parent_cpio, fp, fv, fb, fake_run, jit_meta = _build_mock_cpio_and_fakes(runner, tmp_dir)
            for clean_flag in ("0", "1"):
                work = tmp_dir / f"r32_b_{clean_flag}"
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}), \
                     mock.patch.object(runner, "_import_stage_a_modules", return_value=(fp, fv, fb)), \
                     mock.patch.object(runner, "_load_p10_keymap_spec", return_value=mock.Mock(spec_id="P10_k", library_name="appFw.so", sites=(mock.Mock(site_id="p10", size=4),))), \
                     mock.patch.object(runner, "_load_p12_wlan_spec", return_value=mock.Mock(spec_id="P12_w", library_name="libWlanResource.so", sites=(mock.Mock(site_id="p12", size=8),))), \
                     mock.patch.object(runner, "build_hardened_libjit_so", return_value=(b"\x7fELF_JIT", dict(jit_meta))), \
                     mock.patch.object(runner, "build_r30_tier0_libjit_so", return_value=(b"\x7fELF_R30_JIT", dict(jit_meta))), \
                     mock.patch.object(runner.subprocess, "run", side_effect=fake_run):
                    rep, add, meta = runner.build_stage_a_overlay(
                        work, parent_cpio, b"BK4NTSC",
                        enable_p10=True, enable_r10=True, enable_p12=True, enable_r28=True,
                        enable_r30=True, r30_mode="peripheral_big6",
                        enable_r31=True, r31_mode="keymap_big6",
                        enable_r32=True, r32_mode="cdcncm_usb_0da1",
                        sd_manifest_mode="valid", lang="en", shim_bytes=b"SHIM",
                    )
                init_out = rep["init"].decode("utf-8")
                self.assertIn("LD_LIBRARY_PATH=/usr/lib:/lib /usr/bin/fx6-stage-a-verify --r32-cdcncm-usb-0da1", init_out)
                self.assertIn("FX6_R32_CDCNCM_EXIT", init_out)
                self.assertEqual(meta["r32"]["r32_mode"], "cdcncm_usb_0da1")
                self.assertEqual(len(meta["r32"]["zero_diff_libs"]), 4)
                self.assertEqual(meta["r32"]["usb_msc_vid_pid"], "054C:0DA1")

    def test_09_round32_stage_a_overlay_uart_6stage_triage_mocked_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r32_ovl_c", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            parent_cpio, fp, fv, fb, fake_run, jit_meta = _build_mock_cpio_and_fakes(runner, tmp_dir)
            for clean_flag in ("0", "1"):
                work = tmp_dir / f"r32_c_{clean_flag}"
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}), \
                     mock.patch.object(runner, "_import_stage_a_modules", return_value=(fp, fv, fb)), \
                     mock.patch.object(runner, "_load_p10_keymap_spec", return_value=mock.Mock(spec_id="P10_k", library_name="appFw.so", sites=(mock.Mock(site_id="p10", size=4),))), \
                     mock.patch.object(runner, "_load_p12_wlan_spec", return_value=mock.Mock(spec_id="P12_w", library_name="libWlanResource.so", sites=(mock.Mock(site_id="p12", size=8),))), \
                     mock.patch.object(runner, "build_hardened_libjit_so", return_value=(b"\x7fELF_JIT", dict(jit_meta))), \
                     mock.patch.object(runner, "build_r30_tier0_libjit_so", return_value=(b"\x7fELF_R30_JIT", dict(jit_meta))), \
                     mock.patch.object(runner.subprocess, "run", side_effect=fake_run):
                    rep, add, meta = runner.build_stage_a_overlay(
                        work, parent_cpio, b"BK4NTSC",
                        enable_p10=True, enable_r10=True, enable_p12=True, enable_r28=True,
                        enable_r30=True, r30_mode="peripheral_big6",
                        enable_r31=True, r31_mode="keymap_big6",
                        enable_r32=True, r32_mode="uart_6stage_triage",
                        sd_manifest_mode="valid", lang="en", shim_bytes=b"SHIM",
                    )
                init_out = rep["init"].decode("utf-8")
                self.assertIn("/usr/bin/fx6-stage-a-verify --r32-uart-6stage", init_out)
                self.assertIn("FX6_R32_UART_EXIT", init_out)
                self.assertEqual(meta["r32"]["r32_mode"], "uart_6stage_triage")
                self.assertEqual(meta["r32"]["uart_baud_framing"], "460800 8N1")
                self.assertEqual(meta["r32"]["uart_logic_mv"], 1800)
                self.assertEqual(meta["r32"]["uart_max_safe_mv"], 1950)

    def test_10_round32_stage_a_overlay_rejects_invalid_r32_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r32_badmode", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            parent_cpio, fp, fv, fb, fake_run, jit_meta = _build_mock_cpio_and_fakes(runner, tmp_dir)
            with mock.patch.object(runner, "_import_stage_a_modules", return_value=(fp, fv, fb)), \
                 mock.patch.object(runner, "_load_p10_keymap_spec", return_value=mock.Mock(spec_id="P10_k", library_name="appFw.so", sites=(mock.Mock(site_id="p10", size=4),))), \
                 mock.patch.object(runner, "_load_p12_wlan_spec", return_value=mock.Mock(spec_id="P12_w", library_name="libWlanResource.so", sites=(mock.Mock(site_id="p12", size=8),))), \
                 mock.patch.object(runner, "build_hardened_libjit_so", return_value=(b"\x7fELF_JIT", dict(jit_meta))), \
                 mock.patch.object(runner, "build_r30_tier0_libjit_so", return_value=(b"\x7fELF_R30_JIT", dict(jit_meta))), \
                 mock.patch.object(runner.subprocess, "run", side_effect=fake_run):
                with self.assertRaises(ValueError):
                    runner.build_stage_a_overlay(
                        tmp_dir / "bad_r32", parent_cpio, b"BK4NTSC",
                        enable_p10=True, enable_r10=True, enable_p12=True, enable_r28=True,
                        enable_r30=True, r30_mode="peripheral_big6",
                        enable_r31=True, r31_mode="keymap_big6",
                        enable_r32=True, r32_mode="invalid_r32_mode",
                        lang="schinese", shim_bytes=b"SHIM",
                    )

    def test_11_round32_summary_json_schema_sanitization_and_audit_flags(self) -> None:
        summary_path = ROUND32_REPORT_DIR / "summary.json"
        self.assertTrue(summary_path.is_file())
        raw = summary_path.read_text(encoding="utf-8")
        for forbidden in ("/Users/", "/Volumes/KAFU2T", "/private/tmp"):
            self.assertNotIn(forbidden, raw)
        data = json.loads(raw)
        self.assertEqual(data["schema"], "fx6-on-fx3-round32-realhw-imx510-cube-cdcncm-uart-qemu-v1")
        self.assertIn("Linux version 4.9.337-scel+", data["kernel_version"])
        self.assertEqual(set(data["runs"].keys()), set(self.EXPECTED_RUN_KEYS))
        audit = data["r32_realhw_imx510_cube_cdcncm_uart_audit"]
        self.assertEqual(audit["total_runs"], 3)
        for k in (
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "r32a_p2_psd_defdet_erofs_verified",
            "r32a_imx510_dual_base_800_12800_verified",
            "r32a_cube_3d_mlut_non_bake_and_nan_reject_verified",
            "r32a_stageb_big6_13_of_13_verified",
            "r32b_zero_diff_4libs_dlopen_dlsym_verified",
            "r32b_rf_nvs_erofs_and_zero_ttyama3_hang_verified",
            "r32b_cdcncm_to_054c_0da1_recovery_verified",
            "r32c_ttyama0_1v8_6stage_telemetry_verified",
            "r32c_vmc_bncm1_contention_and_overvoltage_abort_verified",
        ):
            self.assertTrue(audit[k], f"Audit flag {k} must be True")

    def test_12_round32_r32a_p2_psd_and_defdet_erofs_immutability(self) -> None:
        data = json.loads((ROUND32_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        telem = data["runs"]["r32a_imx510_cube_big6_schinese"]["r32_telemetry"]
        init = telem["imx510_cube_init"]
        br = telem["imx510_cube_bridge"]
        self.assertEqual(init["psd_erofs"], 1)
        self.assertEqual(init["psd_errno"], 30)
        self.assertEqual(init["defdet_erofs"], 1)
        self.assertEqual(init["defdet_errno"], 30)
        self.assertEqual(init["sensor_cal_sha256_before"], init["sensor_cal_sha256_after"])
        self.assertEqual(len(init["sensor_cal_sha256_before"]), 64)
        self.assertEqual(init["sensor_cal_sha256_match"], 1)
        self.assertEqual(br["p2_psd_erofs"], 1)
        self.assertEqual(br["p2_defdet_erofs"], 1)
        self.assertEqual(br["sensor_cal_erofs_ok"], 1)

    def test_13_round32_r32a_imx510_dual_base_800_12800_sencore_bridge(self) -> None:
        data = json.loads((ROUND32_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        telem = data["runs"]["r32a_imx510_cube_big6_schinese"]["r32_telemetry"]
        init = telem["imx510_cube_init"]
        br = telem["imx510_cube_bridge"]
        self.assertEqual(init["sencore_elf_ok"], 1)
        self.assertEqual(init["appfw_elf_ok"], 1)
        self.assertEqual(init["r32_init_ok"], 1)
        self.assertEqual(br["sensor"], "IMX510")
        self.assertEqual(br["imx510_lcg_iso"], 800)
        self.assertEqual(br["imx510_hcg_iso"], 12800)
        self.assertEqual(br["imx510_readout_us"], 8700)
        self.assertEqual(br["sencore_dlopen_ok"], 1)
        self.assertEqual(br["sencore_dlsym_ok"], 1)
        self.assertEqual(br["imx510_dual_base_ok"], 1)
        self.assertEqual(br["r32_bridge_ok"], 1)

    def test_14_round32_r32a_cube_17x17x17_volatile_slot0_and_non_bake(self) -> None:
        data = json.loads((ROUND32_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        telem = data["runs"]["r32a_imx510_cube_big6_schinese"]["r32_telemetry"]
        init = telem["imx510_cube_init"]
        br = telem["imx510_cube_bridge"]
        self.assertEqual(init["mlut_lut_size"], 17)
        self.assertEqual(init["mlut_entries"], 17 ** 3)
        self.assertEqual(init["mlut_slot0_loaded"], 1)
        self.assertEqual(init["mlut_slot0_bytes"], 58972)
        self.assertEqual(len(init["mlut_slot0_sha256"]), 64)
        self.assertEqual(init["mlut_baked_into_master"], 0)
        self.assertEqual(br["mlut_slot0_active"], 1)
        self.assertEqual(br["mlut_lut_size"], 17)
        self.assertEqual(br["mlut_baked_into_master"], 0)
        self.assertEqual(br["slog3_xavc_master_clean"], 1)

    def test_15_round32_r32a_malformed_nan_cube_fail_closed_rejection(self) -> None:
        data = json.loads((ROUND32_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        init = data["runs"]["r32a_imx510_cube_big6_schinese"]["r32_telemetry"]["imx510_cube_init"]
        self.assertEqual(init["bad_cube_nan_detected"], 1)
        self.assertEqual(init["bad_cube_rejected"], 1)
        self.assertEqual(init["slot0_untouched_on_bad_cube"], 1)
        self.assertEqual(init["emmc_write_count"], 0)

    def test_16_round32_r32a_stage_b_13_sha256_and_big6_render_invariants(self) -> None:
        data = json.loads((ROUND32_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        r32a = data["runs"]["r32a_imx510_cube_big6_schinese"]
        self.assertEqual(r32a["round"], 32)
        self.assertEqual(r32a["r32_mode"], "imx510_cube_big6")
        self.assertEqual(r32a["target_presenter"], "31procam_big6_menu_home_presenter")
        self.assertEqual(r32a["target_sid"], "0x0a")
        self.assertEqual(r32a["nop_count"], 0)
        self.assertEqual(r32a["crashes"], 0)
        self.assertEqual(r32a["emmc_write_count"], 0)
        self.assertGreaterEqual(r32a["total_threads_seen"], 160)
        self.assertEqual(r32a["faithful_invariants"]["FX6_NATIVE_FAITHFUL"], 1)
        self.assertEqual(r32a["stage_b"]["manifest_count"], 13)
        self.assertEqual(len(r32a["stage_b"]["manifest_items"]), 13)
        for item in r32a["stage_b"]["manifest_items"]:
            self.assertEqual(len(item["sha256"]), 64)
            int(item["sha256"], 16)
        lt = r32a["r32_telemetry"]["lang_telemetry"]
        self.assertEqual(lt["gpe_fb"], 0)
        self.assertEqual(lt["subst_color"], 0)
        self.assertEqual(lt["subst_image"], 0)
        self.assertEqual(lt["r32_bridge_ok"], 1)
        self.assertGreater(r32a["gpe0_readback"]["nonzero_pixels"], 300000)

    def test_17_round32_r32a_png_receipts_under_28kib_and_dimensions(self) -> None:
        data = json.loads((ROUND32_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        exports = data["runs"]["r32a_imx510_cube_big6_schinese"]["png_exports"]
        for key in ("alpha_png", "composited_png"):
            p = REPO_ROOT / exports[key]["path"]
            self.assertTrue(p.is_file(), f"Missing Round 32 PNG: {p}")
            raw = p.read_bytes()
            self.assertLess(len(raw), 28 * 1024, f"PNG exceeds 28 KiB: {p} ({len(raw)} bytes)")
            self.assertEqual(len(raw), exports[key]["bytes"])
            self.assertEqual(hashlib.sha256(raw).hexdigest(), exports[key]["sha256"])
            w, h, rows = _decode_png_rgba_rows(raw)
            self.assertEqual((w, h), (1024, 540))
            if key == "alpha_png":
                nonzero_alpha = sum(
                    sum(1 for a in row[3::4] if a != 0)
                    for row in rows
                )
                self.assertGreater(nonzero_alpha, 300000)

    def test_18_round32_r32b_zero_diff_4_libs_dlopen_dlsym_and_rf_nvs_erofs(self) -> None:
        data = json.loads((ROUND32_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        r32b = data["runs"]["r32b_cdcncm_usb_0da1"]
        self.assertEqual(r32b["round"], 32)
        self.assertEqual(r32b["r32_mode"], "cdcncm_usb_0da1")
        self.assertEqual(r32b["crashes"], 0)
        self.assertEqual(r32b["emmc_write_count"], 0)
        self.assertTrue(r32b["gpe0_readback"]["skipped_stock_fx3_mode"])
        self.assertEqual(r32b["r32_telemetry"]["cdcncm_rc"], 0)
        c = r32b["r32_telemetry"]["cdcncm_usb_0da1"]
        self.assertEqual(c["dlopen_libs_ok"], 4)
        self.assertEqual(c["dlsym_resolved"], 8)
        self.assertEqual(c["zero_diff_libs_ok"], 1)
        self.assertEqual(c["rf_nvs_erofs_ok"], 1)
        self.assertEqual(c["rf_nvs_writes"], 0)
        self.assertEqual(c["rf_nvs_p12_errno"], 30)
        self.assertEqual(c["rf_nvs_p13_errno"], 30)

    def test_19_round32_r32b_zero_ttyama3_hang_and_cdcncm_054c_0da1_recovery(self) -> None:
        data = json.loads((ROUND32_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        r32b = data["runs"]["r32b_cdcncm_usb_0da1"]
        self.assertEqual(
            r32b["stage_b"]["r32"]["zero_diff_libs"],
            [
                "/usr/lib/libInfraMscServer.so",
                "/usr/lib/libUsbControl.so",
                "/usr/lib/libWlanAdjust.so",
                "/usr/lib/libWlanResource.so",
            ],
        )
        c = r32b["r32_telemetry"]["cdcncm_usb_0da1"]
        self.assertEqual(c["bt_ttyama3_masked"], 1)
        self.assertEqual(c["bt_wait_ms"], 0)
        self.assertEqual(c["usb_cdcncm_link_mbps"], 1000)
        self.assertEqual(c["usb_ptp_ip_port"], 15740)
        self.assertEqual(c["usb_cdcncm_tested"], 1)
        self.assertEqual(c["usb_vid"], "0x054c")
        self.assertEqual(c["usb_msc_pid"], "0x0da1")
        self.assertEqual(c["usb_service_pid"], "0x0336")
        self.assertEqual(c["usb_0da1_intact"], 1)
        self.assertEqual(c["usb_0336_preserved"], 1)
        self.assertEqual(c["emmc_write_count"], 0)
        self.assertEqual(c["r32b_ok"], 1)

    def test_20_round32_r32c_ttyama0_1v8_6stage_boot_checkpoints(self) -> None:
        data = json.loads((ROUND32_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        r32c = data["runs"]["r32c_uart_6stage_triage"]
        self.assertEqual(r32c["round"], 32)
        self.assertEqual(r32c["r32_mode"], "uart_6stage_triage")
        self.assertEqual(r32c["crashes"], 0)
        self.assertEqual(r32c["emmc_write_count"], 0)
        self.assertTrue(r32c["gpe0_readback"]["skipped_stock_fx3_mode"])
        self.assertEqual(r32c["r32_telemetry"]["uart_rc"], 0)
        u = r32c["r32_telemetry"]["uart_6stage"]
        cps = r32c["r32_telemetry"]["uart_checkpoints"]
        self.assertEqual(u["kernel_release_ok"], 1)
        self.assertEqual(u["cmdline_ttyama0_ok"], 1)
        self.assertEqual(u["uart_device"], "/dev/ttyAMA0")
        self.assertEqual(u["uart_baud"], 460800)
        self.assertEqual(u["uart_framing"], "8N1")
        self.assertEqual(u["uart_logic_mv"], 1800)
        self.assertEqual(u["uart_max_safe_mv"], 1950)
        self.assertEqual(u["checkpoints_passed"], 6)
        self.assertEqual(len(cps), 6)
        self.assertEqual(
            [cp["name"] for cp in cps],
            [
                "IPL_BL2",
                "KERNEL_4_9_337_SCEL",
                "SETUP_NFLASH",
                "STAGE_A_47US_DLOPEN",
                "STRATEGY_A_MOUNT",
                "STAGE_B_APPFW_BIG6",
            ],
        )

    def test_21_round32_r32c_vmc_bncm1_contention_and_overvoltage_fail_closed_aborts(self) -> None:
        data = json.loads((ROUND32_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        u = data["runs"]["r32c_uart_6stage_triage"]["r32_telemetry"]["uart_6stage"]
        self.assertEqual(u["uart_nominal_ok"], 1)
        self.assertEqual(u["vmc_bncm1_contention_aborted"], 1)
        self.assertEqual(u["vmc_bncm1_abort_rc"], -16)
        self.assertEqual(u["uart_overvoltage_injected_mv"], 3300)
        self.assertEqual(u["uart_overvoltage_aborted"], 1)
        self.assertEqual(u["uart_overvoltage_abort_rc"], -34)
        self.assertEqual(u["emmc_write_count"], 0)
        self.assertEqual(u["r32c_ok"], 1)

    def test_22_round32_top_level_realhw_mechanisms_and_bench_boundaries(self) -> None:
        data = json.loads((ROUND32_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        mech = data["realhw_mechanisms_verified"]
        a = mech["imx510_dual_base_and_p2_erofs_and_cube_mlut"]
        b = mech["zero_diff_libs_cdcncm_and_054c_0da1_recovery"]
        c = mech["ttyama0_1v8_6stage_and_vmc_bncm1_guard"]
        self.assertEqual(a["r32_bridge_ok"], 1)
        self.assertEqual(a["imx510_dual_base_ok"], 1)
        self.assertEqual(a["psd_erofs"], 1)
        self.assertEqual(a["defdet_erofs"], 1)
        self.assertEqual(a["mlut_baked_into_master"], 0)
        self.assertEqual(a["bad_cube_rejected"], 1)
        self.assertEqual(b["r32b_ok"], 1)
        self.assertEqual(b["dlopen_libs_ok"], 4)
        self.assertEqual(b["dlsym_resolved"], 8)
        self.assertEqual(b["bt_wait_ms"], 0)
        self.assertEqual(b["usb_0da1_intact"], 1)
        self.assertEqual(c["r32c_ok"], 1)
        self.assertEqual(c["checkpoints_passed"], 6)
        self.assertEqual(c["vmc_bncm1_contention_aborted"], 1)
        self.assertEqual(c["uart_overvoltage_aborted"], 1)
        boundaries = data["unexecuted_physical_camera_bench_boundaries"]
        self.assertEqual(len(boundaries), 3)

    def test_23_round32_stage_b_r32_bridge_invariants_in_r32a(self) -> None:
        data = json.loads((ROUND32_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        br = data["runs"]["r32a_imx510_cube_big6_schinese"]["r32_telemetry"]["stage_b_bridge"]
        for key in (
            "faithful",
            "p12_wlan",
            "wf12_00342260_immune",
            "p10_keymap",
            "p4_nd_clear",
            "p11_xlr_h1",
            "imx510_dual_base",
            "p2_psd_defdet_erofs",
            "cube_3d_mlut_non_bake",
            "zero_diff_libs_dlopen",
            "cdcncm_0da1_intact",
            "ttyama0_6stage_1v8",
        ):
            self.assertEqual(br[key], 1, f"Expected stage_b_bridge[{key}]==1")
        self.assertEqual(br["round"], 32)
        self.assertEqual(br["nop_count"], 0)
        self.assertEqual(br["emmc_write_count"], 0)

    def test_24_round32_readme_sanitization_and_no_tmp_or_binary_residue(self) -> None:
        closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn("2026-11-15-round32-realhw-imx510-cube-cdcncm-uart-qemu", closure_readme)
        self.assertIn("`24` New Round 32 Dual-Mode Unit Tests (`354` Total)", closure_readme)
        r32_readme = (ROUND32_REPORT_DIR / "README.md").read_text(encoding="utf-8")
        for tok in (
            "IMX510",
            "800/12800",
            "psd.bin",
            "defdet.bin",
            "EROFS",
            "mlut_baked_into_master=0",
            "libInfraMscServer.so",
            "054C:0DA1",
            "460800 8N1",
            "VMC-BNCM1",
            "13/13",
        ):
            self.assertIn(tok, r32_readme)
        for forbidden in ("/Volumes/KAFU2T", "/Users/", "/private/tmp"):
            self.assertNotIn(forbidden, r32_readme)
        tmp_matches = list(pathlib.Path("/private/tmp").glob("fx6-r32*"))
        self.assertEqual(tmp_matches, [], f"Leftover scratch dirs in /private/tmp: {tmp_matches}")
        for tree in (CLOSURE_DIR, ROUND32_REPORT_DIR):
            for ext in ("*.so", "*.elf", "*.o", "*.cpio", "*.vfat", "*.raw", "*.pyc"):
                hits = list(tree.rglob(ext))
                self.assertEqual(hits, [], f"Unexpected binary residue {ext} in {tree}: {hits}")


if __name__ == "__main__":
    unittest.main()
