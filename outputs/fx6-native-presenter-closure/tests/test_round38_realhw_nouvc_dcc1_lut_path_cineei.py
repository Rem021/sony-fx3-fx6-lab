#!/usr/bin/env python3
"""Offline dual-mode unit tests for FX6-on-FX3 Round 38 real-hardware QEMU rehearsal."""
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
from typing import List, Tuple
from unittest import mock

TESTS_DIR = pathlib.Path(__file__).resolve().parent
CLOSURE_DIR = TESTS_DIR.parent
REPO_ROOT = CLOSURE_DIR.parent.parent
ROUND38_REPORT_DIR = (
    REPO_ROOT / "reports" / "2026-11-15-round38-realhw-nouvc-dcc1-lut-path-cineei-qemu"
)
ROUND38_ASSETS_DIR = ROUND38_REPORT_DIR / "assets"


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


class TestRound38RealHwNoUvcDcc1LutPathCineEi(unittest.TestCase):
    EXPECTED_RUN_KEYS = (
        "r38a_nouvc_dcc1_pd_big6_schinese",
        "r38b_lut_path_cineei",
        "r38c_rmtp1bt_clipflag_seal",
    )

    def test_01_round38_c_and_python_source_contracts(self) -> None:
        shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")

        self.assertIn("#if FX6_ROUND >= 38", shim_src)
        for token in (
            "FX6_R38_NOUVC_DCC1_PD_BRIDGE",
            "FX6_R38_LUT_CINEEI_BRIDGE",
            "FX6_R38_LANG_TELEMETRY",
            "FX6_STAGE_B_R38_BRIDGE",
            "realhw_nouvc_dcc1_lut_path_cineei=1",
        ):
            self.assertIn(token, shim_src)

        for token in (
            "r38_usb_gadget_gate",
            "r38_netstream_gate",
            "r38_power_interlock_gate",
            "setup_r38_nouvc_dcc1_pd_probe",
            "NO_UVC_FX3_702_HARDWARE_ABSENT",
            "r38_validate_cube_lut_file",
            "r38_cineei_eval",
            "run_r38_lut_path_cineei_probe",
            "r38_bt_rmt_eval",
            "run_r38_rmtp1bt_clipflag_probe",
            "--r38-lut-path-cineei",
            "--r38-rmtp1bt-clipflag",
            "/etc/fx6_stage_r38",
            "FX6_R38_NOUVC_DCC1_PD_INIT",
            "FX6_R38_LUT_PATH_CINEEI",
            "FX6_R38_RMTP1BT_CLIPFLAG",
        ):
            self.assertIn(token, verify_src)

        for token in (
            "enable_r38",
            "r38_mode",
            "--r38-mode",
            "nouvc_dcc1_pd_big6",
            "lut_path_cineei",
            "rmtp1bt_clipflag_seal",
            "etc/fx6_stage_r38",
            "FX6_R38_LUT_CINEEI_EXIT",
            "FX6_R38_RMTP1BT_CLIPFLAG_EXIT",
            '"r38_telemetry"',
            "choices=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45]",
        ):
            self.assertIn(token, runner_src)

    def test_02_round38_native_verify_c_compiles_with_zig_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r38_verc", "build_and_run_round.py")
        self.assertTrue(runner.ZIG.is_file(), f"Missing zig compiler at {runner.ZIG}")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            cache_dir = tmp_dir / "zig-cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            for clean_flag in ("0", "1"):
                out_bin = tmp_dir / f"fx6-stage-a-verify-r38-{clean_flag}"
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

    def test_03_round38_build_binaries_compiles_shim_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r38_shimc", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            for clean_flag in ("0", "1"):
                work = pathlib.Path(tmp) / f"shim_{clean_flag}"
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                    launcher_b, shim_b, meta = runner.build_binaries(
                        work,
                        fx6_round=38,
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

    def test_04_round38_extract_milestones_r38a_nouvc_dcc1_pd_and_bridge(self) -> None:
        runner = _load_closure_module("fx6_brr_r38_msa", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R38_NOUVC_DCC1_PD_INIT uvc_gadget_reject_rc=-95 uvc_reason=NO_UVC_FX3_702_HARDWARE_ABSENT usb_allowed_modes=5 msc_rc=0 mtp_rc=0 remote_shooting_rc=0 remote_webcam_cap=1024x576_no_audio usblan_rndis_ncm_rc=0 netstream_4k5994_38mbps_rc=0 netstream_over38_reject_rc=-22 body_pd_with_fz100_rc=0 body_pd_no_fz100_rc=-19 micro_usb_power_rc=-95 dcc1_65w_5a_rc=0 dcc1_under65w_reject_rc=-22 dcc1_non5a_reject_rc=-22 appfw_present=1 wlan_present=1 shim_present=1 emmc_write_count=0 r38_init_ok=1 verify_us=604952",
                "FX6_R38_NOUVC_DCC1_PD_BRIDGE uvc_gadget_reject_rc=-95 usblan_rc=0 netstream_4k5994_mbps=38 body_pd_no_batt_rc=-19 dcc1_65w_5a_rc=0 dcc1_under_rc=-22 nouvc_blocked_ok=1 usblan_netstream_ok=1 pd_dcc1_interlock_ok=1 emmc_write_count=0 r38_bridge_ok=1",
                "FX6_R38_LUT_CINEEI_BRIDGE sd_lut_prefix=/Private/Sony/PRO/LUT/ cfx_lut_prefix=/Sony/PRO/LUT/ max_name_bytes=63 lut_pts=17_33 cineei_bases=800_12800 ei_range=3200_51200 lut_path_asymmetry_ok=1 cineei_dualbase_ok=1 rmtp1bt_bt42_ir_gps_masked_ok=1 p2_setting_writes=0 emmc_write_count=0",
                "FX6_STAGE_B_R38_BRIDGE round=38 faithful=1 nop_count=0 p12_wlan=1 wf12_00342260_immune=1 p10_keymap=1 p4_nd_clear=1 p11_xlr_h1=1 lang=schinese bk4_lang=0x19 enum=0x2b45_CHINESE_SIMPLIFIED font_bank=23 str_bank=19 nouvc_gadget_firewall=1 usblan_netstream_38mbps=1 usbpd_fz100_dcc1_65w_5a=1 dualmedia_lut_path_asymmetry=1 cineei_800_12800=1 rmtp1bt_ir_gps_mutex=1 clipflag_ok_ng_keep_hygiene=1 emmc_write_count=0",
                "FX6_R38_LANG_TELEMETRY reason=pump lang=schinese bk4_lang_id=0x02cf019c bk4_lang_val=0x19 gpe_fb=0 nouvc_blocked_ok=1 pd_dcc1_interlock_ok=1 lut_path_asymmetry_ok=1 cineei_dualbase_ok=1 rmtp1bt_clipflag_ok=1 r38_bridge_ok=1 realhw_nouvc_dcc1_lut_path_cineei=1 emmc_write_count=0 subst_color=0 subst_image=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        r38 = ms["r38_telemetry"]
        self.assertIsNotNone(r38)
        self.assertEqual(r38["nouvc_dcc1_pd_init"]["uvc_gadget_reject_rc"], -95)
        self.assertEqual(r38["nouvc_dcc1_pd_init"]["body_pd_no_fz100_rc"], -19)
        self.assertEqual(r38["nouvc_dcc1_pd_init"]["dcc1_65w_5a_rc"], 0)
        self.assertEqual(r38["nouvc_dcc1_pd_init"]["dcc1_under65w_reject_rc"], -22)
        self.assertEqual(r38["nouvc_dcc1_pd_bridge"]["r38_bridge_ok"], 1)
        self.assertEqual(r38["lut_cineei_bridge"]["max_name_bytes"], 63)
        self.assertEqual(r38["stage_b_bridge"]["round"], 38)
        self.assertEqual(r38["lang_telemetry"]["gpe_fb"], 0)

    def test_05_round38_extract_milestones_r38b_lut_path_cineei(self) -> None:
        runner = _load_closure_module("fx6_brr_r38_msb", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R38_LUT_PATH_CINEEI sd_prefix=/Private/Sony/PRO/LUT/ cfx_prefix=/Sony/PRO/LUT/ sd_17pt_accept_rc=0 sd_33pt_accept_rc=0 cfx_33pt_accept_rc=0 sd_swapped_cfx_path_reject_rc=-22 cfx_swapped_sd_path_reject_rc=-22 lut_63b_name_accept_rc=0 lut_64b_name_reject_rc=-36 lut_65pt_reject_rc=-22 max_user_lut_slots=16 ae_offset_range=0EV_+2EV base_800_accept_rc=0 base_12800_3200ei_rc=0 base_12800_12800ei_rc=0 base_12800_51200ei_rc=0 invalid_base_1600_reject_rc=-22 ei_1600_under_12800_reject_rc=-34 ei_64000_over_12800_reject_rc=-34 sensor_gain_locked_dual_base=1 p2_setting_bytes_touched=0 p2_setting_sha256_match=1 p2_write_blocked_rc=0 appfw_cineei_ok=1 shim_elf_ok=1 emmc_write_count=0 r38b_ok=1 verify_us=612506",
                "FX6_R38_LUT_CINEEI_RC=0",
                "FX6_R38_LUT_CINEEI_EXIT rc=0 emmc_write_count=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        r38 = ms["r38_telemetry"]
        self.assertIsNotNone(r38)
        self.assertEqual(r38["lut_cineei_rc"], 0)
        b = r38["lut_path_cineei"]
        self.assertEqual(b["sd_prefix"], "/Private/Sony/PRO/LUT/")
        self.assertEqual(b["cfx_prefix"], "/Sony/PRO/LUT/")
        self.assertEqual(b["lut_63b_name_accept_rc"], 0)
        self.assertEqual(b["lut_64b_name_reject_rc"], -36)
        self.assertEqual(b["lut_65pt_reject_rc"], -22)
        self.assertEqual(b["sensor_gain_locked_dual_base"], 1)
        self.assertEqual(b["p2_setting_bytes_touched"], 0)
        self.assertEqual(b["r38b_ok"], 1)

    def test_06_round38_extract_milestones_r38c_rmtp1bt_clipflag_seal(self) -> None:
        runner = _load_closure_module("fx6_brr_r38_msc", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R38_RMTP1BT_CLIPFLAG bt_spec=4.2 rmtp1bt_bt42_cmd_rc=0 ir_when_bt_on_rc=-16 gps_when_bt_on_rc=-16 bt_when_off_rc=-19 ir_when_bt_off_rc=0 gps_when_bt_off_rc=0 ir_gps_masked_when_bt_on=1 ir_gps_restored_when_bt_off=1 clip_flags_staged=3 cloud_filter_ok_keep_count=2 nvs_writes_delta=0 p2_setting_writes=0 dlopen_ok=1 surfaces_verified=16 surfaces_h0_eq_h3=16 drift_bits=0 emmc_write_count=0 r38c_ok=1 verify_us=3804",
                "FX6_R38_RMTP1BT_RC=0",
                "FX6_R38_RMTP1BT_CLIPFLAG_EXIT rc=0 emmc_write_count=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        r38 = ms["r38_telemetry"]
        self.assertIsNotNone(r38)
        self.assertEqual(r38["rmtp1bt_rc"], 0)
        c = r38["rmtp1bt_clipflag"]
        self.assertEqual(c["bt_spec"], "4.2")
        self.assertEqual(c["rmtp1bt_bt42_cmd_rc"], 0)
        self.assertEqual(c["ir_when_bt_on_rc"], -16)
        self.assertEqual(c["gps_when_bt_on_rc"], -16)
        self.assertEqual(c["ir_gps_masked_when_bt_on"], 1)
        self.assertEqual(c["ir_gps_restored_when_bt_off"], 1)
        self.assertEqual(c["surfaces_h0_eq_h3"], 16)
        self.assertEqual(c["r38c_ok"], 1)

    def test_07_round38_stage_a_overlay_nouvc_dcc1_pd_big6_mocked_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r38_ovl_a", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            parent_cpio, fp, fv, fb, fake_run, jit_meta = _build_mock_cpio_and_fakes(runner, tmp_dir)
            for clean_flag in ("0", "1"):
                work = tmp_dir / f"r38_a_{clean_flag}"
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
                        enable_r33=True, r33_mode="cfexpress_rsv_big6",
                        enable_r34=True, r34_mode="c2pa_tc_gyro_big6",
                        enable_r35=True, r35_mode="ssboot_wbi2_big6",
                        enable_r36=True, r36_mode="emount_info3d_big6",
                        enable_r37=True, r37_mode="fx3a_firewall_big6",
                        enable_r38=True, r38_mode="nouvc_dcc1_pd_big6",
                        sd_manifest_mode="valid", lang="schinese", shim_bytes=b"SHIM",
                    )
                init_out = rep["init"].decode("utf-8")
                self.assertNotIn("--r38-lut-path-cineei", init_out)
                self.assertNotIn("--r38-rmtp1bt-clipflag", init_out)
                self.assertIn("--sd-gate", init_out)
                self.assertIn("etc/fx6_stage_r38", add)
                self.assertIn("r38_mode=nouvc_dcc1_pd_big6", add["etc/fx6_stage_r38"][0].decode("utf-8"))
                self.assertTrue(meta["r38_enabled"])
                self.assertEqual(meta["r38"]["r38_mode"], "nouvc_dcc1_pd_big6")
                self.assertEqual(meta["r38"]["uvc_gadget_reject_rc"], -95)
                self.assertEqual(meta["r38"]["dcc1_min_watts"], 65)
                self.assertEqual(meta["r38"]["dcc1_min_amps"], 5)
                self.assertTrue(meta["r38"]["body_pd_requires_fz100"])

    def test_08_round38_stage_a_overlay_lut_path_cineei_mocked_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r38_ovl_b", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            parent_cpio, fp, fv, fb, fake_run, jit_meta = _build_mock_cpio_and_fakes(runner, tmp_dir)
            for clean_flag in ("0", "1"):
                work = tmp_dir / f"r38_b_{clean_flag}"
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
                        enable_r33=True, r33_mode="cfexpress_rsv_big6",
                        enable_r34=True, r34_mode="c2pa_tc_gyro_big6",
                        enable_r35=True, r35_mode="ssboot_wbi2_big6",
                        enable_r36=True, r36_mode="emount_info3d_big6",
                        enable_r37=True, r37_mode="fx3a_firewall_big6",
                        enable_r38=True, r38_mode="lut_path_cineei",
                        sd_manifest_mode="valid", lang="en", shim_bytes=b"SHIM",
                    )
                init_out = rep["init"].decode("utf-8")
                self.assertIn("/usr/bin/fx6-stage-a-verify --r38-lut-path-cineei", init_out)
                self.assertIn("FX6_R38_LUT_CINEEI_EXIT", init_out)
                self.assertEqual(meta["r38"]["r38_mode"], "lut_path_cineei")
                self.assertEqual(meta["r38"]["sd_lut_prefix"], "/Private/Sony/PRO/LUT/")
                self.assertEqual(meta["r38"]["cfx_lut_prefix"], "/Sony/PRO/LUT/")
                self.assertEqual(meta["r38"]["cineei_base_isos"], [800, 12800])

    def test_09_round38_stage_a_overlay_rmtp1bt_clipflag_mocked_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r38_ovl_c", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            parent_cpio, fp, fv, fb, fake_run, jit_meta = _build_mock_cpio_and_fakes(runner, tmp_dir)
            for clean_flag in ("0", "1"):
                work = tmp_dir / f"r38_c_{clean_flag}"
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
                        enable_r33=True, r33_mode="cfexpress_rsv_big6",
                        enable_r34=True, r34_mode="c2pa_tc_gyro_big6",
                        enable_r35=True, r35_mode="ssboot_wbi2_big6",
                        enable_r36=True, r36_mode="emount_info3d_big6",
                        enable_r37=True, r37_mode="fx3a_firewall_big6",
                        enable_r38=True, r38_mode="rmtp1bt_clipflag_seal",
                        sd_manifest_mode="valid", lang="en", shim_bytes=b"SHIM",
                    )
                init_out = rep["init"].decode("utf-8")
                self.assertIn("/usr/bin/fx6-stage-a-verify --r38-rmtp1bt-clipflag", init_out)
                self.assertIn("FX6_R38_RMTP1BT_CLIPFLAG_EXIT", init_out)
                self.assertEqual(meta["r38"]["r38_mode"], "rmtp1bt_clipflag_seal")
                self.assertEqual(meta["r38"]["rmtp1bt_bt_spec"], "4.2")
                self.assertTrue(meta["r38"]["rmtp1bt_masks_ir_and_gps"])
                self.assertEqual(meta["r38"]["clip_flags_supported"], ["OK", "NG", "KEEP"])

    def test_10_round38_stage_a_overlay_rejects_invalid_r38_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r38_badmode", "build_and_run_round.py")
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
                        tmp_dir / "bad_r38", parent_cpio, b"BK4NTSC",
                        enable_p10=True, enable_r10=True, enable_p12=True, enable_r28=True,
                        enable_r30=True, r30_mode="peripheral_big6",
                        enable_r31=True, r31_mode="keymap_big6",
                        enable_r32=True, r32_mode="imx510_cube_big6",
                        enable_r33=True, r33_mode="cfexpress_rsv_big6",
                        enable_r34=True, r34_mode="c2pa_tc_gyro_big6",
                        enable_r35=True, r35_mode="ssboot_wbi2_big6",
                        enable_r36=True, r36_mode="emount_info3d_big6",
                        enable_r37=True, r37_mode="fx3a_firewall_big6",
                        enable_r38=True, r38_mode="invalid_r38_mode",
                        lang="schinese", shim_bytes=b"SHIM",
                    )

    def test_11_round38_summary_json_schema_sanitization_and_audit_flags(self) -> None:
        summary_path = ROUND38_REPORT_DIR / "summary.json"
        self.assertTrue(summary_path.is_file())
        raw = summary_path.read_text(encoding="utf-8")
        for forbidden in ("/Users/", "/Volumes/KAFU2T", "/private/tmp"):
            self.assertNotIn(forbidden, raw)
        data = json.loads(raw)
        self.assertEqual(data["schema"], "fx6-on-fx3-round38-realhw-nouvc-dcc1-lut-path-cineei-qemu-v1")
        self.assertIn("Linux version 4.9.337-scel+", data["kernel_version"])
        self.assertEqual(set(data["runs"].keys()), set(self.EXPECTED_RUN_KEYS))
        audit = data["r38_realhw_nouvc_dcc1_lut_path_cineei_audit"]
        self.assertEqual(audit["total_runs"], 3)
        for k in (
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "r38a_nouvc_gadget_blocked_rc_minus_95_and_usblan_netstream_38mbps_verified",
            "r38a_usbpd_fz100_and_dcc1_65w_5a_interlock_verified",
            "r38a_stageb_big6_sid_0a_over_340k_pixels_verified",
            "r38b_dual_media_cube_path_asymmetry_17_33pt_63b_verified",
            "r38b_cineei_dual_base_800_12800_and_p2_zero_writes_verified",
            "r38c_rmtp1bt_bt42_masks_ir_gps_and_restores_on_off_verified",
            "r38c_creators_cloud_clipflag_zero_nvs_and_16_h0_eq_h3_verified",
        ):
            self.assertTrue(audit[k], f"Audit flag {k} must be True")

    def test_12_round38_r38a_nouvc_usb_gadget_firewall_and_usblan_netstream(self) -> None:
        data = json.loads((ROUND38_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        init = data["runs"]["r38a_nouvc_dcc1_pd_big6_schinese"]["r38_telemetry"]["nouvc_dcc1_pd_init"]
        self.assertEqual(init["uvc_gadget_reject_rc"], -95)
        self.assertEqual(init["uvc_reason"], "NO_UVC_FX3_702_HARDWARE_ABSENT")
        self.assertEqual(init["usb_allowed_modes"], 5)
        self.assertEqual(init["msc_rc"], 0)
        self.assertEqual(init["mtp_rc"], 0)
        self.assertEqual(init["remote_shooting_rc"], 0)
        self.assertEqual(init["remote_webcam_cap"], "1024x576_no_audio")
        self.assertEqual(init["usblan_rndis_ncm_rc"], 0)
        self.assertEqual(init["netstream_4k5994_38mbps_rc"], 0)
        self.assertEqual(init["netstream_over38_reject_rc"], -22)

    def test_13_round38_r38a_usbpd_fz100_and_dcc1_65w_5a_interlock(self) -> None:
        data = json.loads((ROUND38_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        init = data["runs"]["r38a_nouvc_dcc1_pd_big6_schinese"]["r38_telemetry"]["nouvc_dcc1_pd_init"]
        self.assertEqual(init["body_pd_with_fz100_rc"], 0)
        self.assertEqual(init["body_pd_no_fz100_rc"], -19)
        self.assertEqual(init["micro_usb_power_rc"], -95)
        self.assertEqual(init["dcc1_65w_5a_rc"], 0)
        self.assertEqual(init["dcc1_under65w_reject_rc"], -22)
        self.assertEqual(init["dcc1_non5a_reject_rc"], -22)
        self.assertEqual(init["emmc_write_count"], 0)

    def test_14_round38_r38a_bridge_telemetry_verified(self) -> None:
        data = json.loads((ROUND38_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        telem = data["runs"]["r38a_nouvc_dcc1_pd_big6_schinese"]["r38_telemetry"]
        init = telem["nouvc_dcc1_pd_init"]
        br = telem["nouvc_dcc1_pd_bridge"]
        self.assertEqual(init["appfw_present"], 1)
        self.assertEqual(init["wlan_present"], 1)
        self.assertEqual(init["shim_present"], 1)
        self.assertEqual(init["r38_init_ok"], 1)
        self.assertEqual(br["uvc_gadget_reject_rc"], -95)
        self.assertEqual(br["usblan_rc"], 0)
        self.assertEqual(br["netstream_4k5994_mbps"], 38)
        self.assertEqual(br["body_pd_no_batt_rc"], -19)
        self.assertEqual(br["dcc1_65w_5a_rc"], 0)
        self.assertEqual(br["dcc1_under_rc"], -22)
        self.assertEqual(br["nouvc_blocked_ok"], 1)
        self.assertEqual(br["usblan_netstream_ok"], 1)
        self.assertEqual(br["pd_dcc1_interlock_ok"], 1)
        self.assertEqual(br["r38_bridge_ok"], 1)

    def test_15_round38_r38a_stage_b_13_sha256_and_big6_render_invariants(self) -> None:
        data = json.loads((ROUND38_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        r38a = data["runs"]["r38a_nouvc_dcc1_pd_big6_schinese"]
        self.assertEqual(r38a["round"], 38)
        self.assertEqual(r38a["r38_mode"], "nouvc_dcc1_pd_big6")
        self.assertEqual(r38a["target_presenter"], "31procam_big6_menu_home_presenter")
        self.assertEqual(r38a["target_sid"], "0x0a")
        self.assertEqual(r38a["nop_count"], 0)
        self.assertEqual(r38a["crashes"], 0)
        self.assertEqual(r38a["emmc_write_count"], 0)
        self.assertGreaterEqual(r38a["total_threads_seen"], 160)
        self.assertEqual(r38a["faithful_invariants"]["FX6_NATIVE_FAITHFUL"], 1)
        self.assertEqual(r38a["stage_b"]["manifest_count"], 13)
        self.assertEqual(len(r38a["stage_b"]["manifest_items"]), 13)
        for item in r38a["stage_b"]["manifest_items"]:
            self.assertEqual(len(item["sha256"]), 64)
            int(item["sha256"], 16)
        lt = r38a["r38_telemetry"]["lang_telemetry"]
        self.assertEqual(lt["gpe_fb"], 0)
        self.assertEqual(lt["subst_color"], 0)
        self.assertEqual(lt["subst_image"], 0)
        self.assertEqual(lt["r38_bridge_ok"], 1)
        self.assertGreater(r38a["gpe0_readback"]["nonzero_pixels"], 340000)

    def test_16_round38_r38a_png_receipts_under_28kib_and_dimensions(self) -> None:
        data = json.loads((ROUND38_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        exports = data["runs"]["r38a_nouvc_dcc1_pd_big6_schinese"]["png_exports"]
        for key in ("alpha_png", "composited_png"):
            p = REPO_ROOT / exports[key]["path"]
            self.assertTrue(p.is_file(), f"Missing Round 38 PNG: {p}")
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
                self.assertGreater(nonzero_alpha, 340000)

    def test_17_round38_r38b_dual_media_cube_lut_path_asymmetry_and_63b_boundary(self) -> None:
        data = json.loads((ROUND38_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        r38b = data["runs"]["r38b_lut_path_cineei"]
        self.assertEqual(r38b["round"], 38)
        self.assertEqual(r38b["r38_mode"], "lut_path_cineei")
        self.assertEqual(r38b["crashes"], 0)
        self.assertEqual(r38b["emmc_write_count"], 0)
        self.assertTrue(r38b["gpe0_readback"]["skipped_stock_fx3_mode"])
        self.assertEqual(r38b["r38_telemetry"]["lut_cineei_rc"], 0)
        b = r38b["r38_telemetry"]["lut_path_cineei"]
        self.assertEqual(b["sd_prefix"], "/Private/Sony/PRO/LUT/")
        self.assertEqual(b["cfx_prefix"], "/Sony/PRO/LUT/")
        self.assertEqual(b["sd_17pt_accept_rc"], 0)
        self.assertEqual(b["sd_33pt_accept_rc"], 0)
        self.assertEqual(b["cfx_33pt_accept_rc"], 0)
        self.assertEqual(b["sd_swapped_cfx_path_reject_rc"], -22)
        self.assertEqual(b["cfx_swapped_sd_path_reject_rc"], -22)
        self.assertEqual(b["lut_63b_name_accept_rc"], 0)
        self.assertEqual(b["lut_64b_name_reject_rc"], -36)
        self.assertEqual(b["lut_65pt_reject_rc"], -22)
        self.assertEqual(b["max_user_lut_slots"], 16)
        self.assertEqual(b["r38b_ok"], 1)

    def test_18_round38_r38b_cineei_dual_base_800_12800_and_p2_zero_writes(self) -> None:
        data = json.loads((ROUND38_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        b = data["runs"]["r38b_lut_path_cineei"]["r38_telemetry"]["lut_path_cineei"]
        self.assertEqual(b["base_800_accept_rc"], 0)
        self.assertEqual(b["base_12800_3200ei_rc"], 0)
        self.assertEqual(b["base_12800_12800ei_rc"], 0)
        self.assertEqual(b["base_12800_51200ei_rc"], 0)
        self.assertEqual(b["invalid_base_1600_reject_rc"], -22)
        self.assertEqual(b["ei_1600_under_12800_reject_rc"], -34)
        self.assertEqual(b["ei_64000_over_12800_reject_rc"], -34)
        self.assertEqual(b["sensor_gain_locked_dual_base"], 1)
        self.assertEqual(b["p2_setting_bytes_touched"], 0)
        self.assertEqual(b["p2_setting_sha256_match"], 1)
        self.assertEqual(b["p2_write_blocked_rc"], -30)
        self.assertEqual(b["appfw_cineei_ok"], 1)
        self.assertEqual(b["shim_elf_ok"], 1)
        self.assertEqual(b["emmc_write_count"], 0)

    def test_19_round38_r38c_rmtp1bt_bt42_masks_ir_and_gps_mutual_exclusion(self) -> None:
        data = json.loads((ROUND38_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        r38c = data["runs"]["r38c_rmtp1bt_clipflag_seal"]
        self.assertEqual(r38c["round"], 38)
        self.assertEqual(r38c["r38_mode"], "rmtp1bt_clipflag_seal")
        self.assertEqual(r38c["crashes"], 0)
        self.assertEqual(r38c["emmc_write_count"], 0)
        self.assertTrue(r38c["gpe0_readback"]["skipped_stock_fx3_mode"])
        self.assertEqual(r38c["r38_telemetry"]["rmtp1bt_rc"], 0)
        c = r38c["r38_telemetry"]["rmtp1bt_clipflag"]
        self.assertEqual(c["bt_spec"], "4.2")
        self.assertEqual(c["rmtp1bt_bt42_cmd_rc"], 0)
        self.assertEqual(c["ir_when_bt_on_rc"], -16)
        self.assertEqual(c["gps_when_bt_on_rc"], -16)
        self.assertEqual(c["bt_when_off_rc"], -19)
        self.assertEqual(c["ir_when_bt_off_rc"], 0)
        self.assertEqual(c["gps_when_bt_off_rc"], 0)
        self.assertEqual(c["ir_gps_masked_when_bt_on"], 1)
        self.assertEqual(c["ir_gps_restored_when_bt_off"], 1)
        self.assertEqual(c["r38c_ok"], 1)

    def test_20_round38_r38c_creators_cloud_clipflag_hygiene_and_dlopen_ok(self) -> None:
        data = json.loads((ROUND38_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        c = data["runs"]["r38c_rmtp1bt_clipflag_seal"]["r38_telemetry"]["rmtp1bt_clipflag"]
        self.assertEqual(c["clip_flags_staged"], 3)
        self.assertEqual(c["cloud_filter_ok_keep_count"], 2)
        self.assertEqual(c["nvs_writes_delta"], 0)
        self.assertEqual(c["p2_setting_writes"], 0)
        self.assertEqual(c["dlopen_ok"], 1)

    def test_21_round38_r38c_16_surfaces_h0_eq_h3_zero_drift(self) -> None:
        data = json.loads((ROUND38_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        c = data["runs"]["r38c_rmtp1bt_clipflag_seal"]["r38_telemetry"]["rmtp1bt_clipflag"]
        self.assertEqual(c["surfaces_verified"], 16)
        self.assertEqual(c["surfaces_h0_eq_h3"], 16)
        self.assertEqual(c["drift_bits"], 0)
        self.assertEqual(c["emmc_write_count"], 0)

    def test_22_round38_stage_b_bridge_mechanisms_and_bench_boundaries(self) -> None:
        data = json.loads((ROUND38_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        mech = data["realhw_mechanisms_verified"]
        self.assertEqual(mech["nouvc_usb_gadget_firewall_init"]["r38_init_ok"], 1)
        self.assertEqual(mech["nouvc_dcc1_pd_stage_b_bridge"]["r38_bridge_ok"], 1)
        self.assertEqual(mech["dual_media_cube_lut_path_asymmetry_and_cine_ei"]["r38b_ok"], 1)
        self.assertEqual(mech["rmtp1bt_bt_ir_mutex_and_clipflag_hygiene"]["r38c_ok"], 1)

        br = data["runs"]["r38a_nouvc_dcc1_pd_big6_schinese"]["r38_telemetry"]["stage_b_bridge"]
        for key in (
            "faithful",
            "p12_wlan",
            "wf12_00342260_immune",
            "p10_keymap",
            "p4_nd_clear",
            "p11_xlr_h1",
            "nouvc_gadget_firewall",
            "usblan_netstream_38mbps",
            "usbpd_fz100_dcc1_65w_5a",
            "dualmedia_lut_path_asymmetry",
            "cineei_800_12800",
            "rmtp1bt_ir_gps_mutex",
            "clipflag_ok_ng_keep_hygiene",
        ):
            self.assertEqual(br[key], 1, f"Expected stage_b_bridge[{key}]==1")
        self.assertEqual(br["round"], 38)
        self.assertEqual(br["nop_count"], 0)
        self.assertEqual(br["emmc_write_count"], 0)
        self.assertEqual(len(data["unexecuted_physical_camera_bench_boundaries"]), 3)

    def test_23_round38_r38a_lut_cineei_bridge_consistent_with_r38b(self) -> None:
        data = json.loads((ROUND38_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        br_lut = data["runs"]["r38a_nouvc_dcc1_pd_big6_schinese"]["r38_telemetry"]["lut_cineei_bridge"]
        r38b_lut = data["runs"]["r38b_lut_path_cineei"]["r38_telemetry"]["lut_path_cineei"]
        self.assertEqual(br_lut["sd_lut_prefix"], r38b_lut["sd_prefix"])
        self.assertEqual(br_lut["cfx_lut_prefix"], r38b_lut["cfx_prefix"])
        self.assertEqual(br_lut["max_name_bytes"], 63)
        self.assertEqual(br_lut["lut_pts"], "17_33")
        self.assertEqual(br_lut["cineei_bases"], "800_12800")
        self.assertEqual(br_lut["ei_range"], "3200_51200")
        self.assertEqual(br_lut["lut_path_asymmetry_ok"], 1)
        self.assertEqual(br_lut["cineei_dualbase_ok"], 1)
        self.assertEqual(br_lut["rmtp1bt_bt42_ir_gps_masked_ok"], 1)
        self.assertEqual(br_lut["p2_setting_writes"], 0)
        self.assertEqual(br_lut["emmc_write_count"], 0)

    def test_24_round38_readme_sanitization_and_no_tmp_or_binary_residue(self) -> None:
        closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn("2026-11-15-round38-realhw-nouvc-dcc1-lut-path-cineei-qemu", closure_readme)
        self.assertIn("`24` New Round 38 Dual-Mode Unit Tests (`498` Total)", closure_readme)
        r38_readme = (ROUND38_REPORT_DIR / "README.md").read_text(encoding="utf-8")
        for tok in (
            "No-UVC",
            "DC-C1",
            "NP-FZ100",
            "USB-LAN",
            "38 Mbps",
            "/Private/Sony/PRO/LUT/",
            "/Sony/PRO/LUT/",
            "17pt",
            "33pt",
            "Cine EI",
            "3200..51200 EI",
            "RMT-P1BT",
            "BT 4.2",
            "OK/NG/KEEP",
            "r38a-nouvc-dcc1-pd-big6-schinese",
            "r38b-lut-path-cineei",
            "r38c-rmtp1bt-clipflag-seal",
        ):
            self.assertIn(tok, r38_readme)
        for forbidden in ("/Users/", "/Volumes/KAFU2T", "/private/tmp"):
            self.assertNotIn(forbidden, r38_readme)
        for folder in (CLOSURE_DIR, ROUND38_REPORT_DIR):
            for p in folder.rglob("*"):
                if p.is_file():
                    self.assertNotIn(p.suffix, {".cpio", ".so", ".o", ".img", ".qcow2", ".pyc"})


if __name__ == "__main__":
    unittest.main()
