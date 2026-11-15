#!/usr/bin/env python3
"""Offline dual-mode unit tests for FX6-on-FX3 Round 44 (Wave-30 Live FX3 7.02 QEMU Rehearsal)."""
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
ROUND44_REPORT_DIR = (
    REPO_ROOT
    / "reports"
    / "2026-11-15-round44-realhw-pixelmap-ntscpal-gammaassist-displaylut-qemu"
)


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

    class _FakeBmtvHex:
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
    return parent_cpio, _FakePatcher, _FakeVfat, _FakeBmtvHex, fake_subproc_run, fake_jit_meta


def _build_overlay_for_r44(runner, tmp_dir: pathlib.Path, work: pathlib.Path, r44_mode: str, lang: str = "schinese"):
    parent_cpio, fp, fv, fb, fake_run, jit_meta = _build_mock_cpio_and_fakes(runner, tmp_dir)
    with mock.patch.object(runner, "_import_stage_a_modules", return_value=(fp, fv, fb)), \
         mock.patch.object(runner, "_load_p10_keymap_spec", return_value=mock.Mock(spec_id="P10_k", library_name="appFw.so", sites=(mock.Mock(site_id="p10", size=4),))), \
         mock.patch.object(runner, "_load_p12_wlan_spec", return_value=mock.Mock(spec_id="P12_w", library_name="libWlanResource.so", sites=(mock.Mock(site_id="p12", size=8),))), \
         mock.patch.object(runner, "build_hardened_libjit_so", return_value=(b"\x7fELF_JIT", dict(jit_meta))), \
         mock.patch.object(runner, "build_r30_tier0_libjit_so", return_value=(b"\x7fELF_R30_JIT", dict(jit_meta))), \
         mock.patch.object(runner.subprocess, "run", side_effect=fake_run):
        return runner.build_stage_a_overlay(
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
            enable_r39=True, r39_mode="fan_pwm_offinrec_big6",
            enable_r40=True, r40_mode="big6_home_noend_big6",
            enable_r41=True, r41_mode="desqueeze_165x_4locks_big6",
            enable_r42=True, r42_mode="hdmi_log1080_hdmionly_4k_big6",
            enable_r43=True, r43_mode="filesettings_shotmark_big6",
            enable_r44=True, r44_mode=r44_mode,
            sd_manifest_mode="valid", lang=lang, shim_bytes=b"SHIM",
        )


class TestRound44RealHwPixelMapNtscPalGammaAssistDisplayLut(unittest.TestCase):
    EXPECTED_RUN_KEYS = (
        "r44a_pixelmap_cnflasha_big6_schinese",
        "r44b_ntscpal_dfn_camreset_persist",
        "r44c_gammaassist_displaylut_h0_h3",
    )

    def test_01_round44_c_and_python_source_contracts(self) -> None:
        shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")

        self.assertIn("#if FX6_ROUND >= 44", shim_src)
        for token in (
            "FX6_R44_PIXELMAP_CNFLASHA_BRIDGE",
            "FX6_R44_NTSCPAL_CAMRESET_BRIDGE",
            "FX6_R44_GAMMAASSIST_DISPLAYLUT_BRIDGE",
            "FX6_R44_LANG_TELEMETRY",
            "FX6_STAGE_B_R44_BRIDGE",
            "round44_realhw_pixelmap_ntscpal_gammaassist_displaylut=1",
        ):
            self.assertIn(token, shim_src)

        for token in (
            "r44_eval_auto_pixel_mapping_poweroff",
            "r44_operator_input_during_pixelmap",
            "r44_cnflasha_userspace_write",
            "r44_exec_manual_pixel_mapping",
            "setup_r44_pixelmap_cnflasha_probe",
            "r44_ntscpal_set_selector",
            "r44_ntscpal_set_framerate",
            "r44_ntscpal_set_tc_format",
            "r44_ntscpal_startup_banner",
            "r44_camera_settings_reset",
            "r44_full_initialize",
            "r44_check_slot_media_db",
            "run_r44_ntscpal_camreset_probe",
            "r44_set_gamma_disp_assist_type",
            "r44_set_gamma_display_assist",
            "r44_set_log_shooting_mode",
            "r44_set_display_lut",
            "r44_custom_key_display_lut_switch",
            "r44_eval_monitor_gamma_assist_scope",
            "run_r44_gammaassist_displaylut_probe",
            "--r44-ntscpal-camreset",
            "--r44-gammaassist-displaylut",
            "/etc/fx6_stage_r44",
            "FX6_R44_PIXELMAP_CNFLASHA_INIT",
            "FX6_R44_NTSCPAL_CAMRESET",
            "FX6_R44_GAMMAASSIST_DISPLAYLUT",
        ):
            self.assertIn(token, verify_src)

        for token in (
            "enable_r44",
            "r44_mode",
            "--r44-mode",
            "pixelmap_reboot_cnflasha_big6",
            "ntscpal_dfn_camreset_persist",
            "gammaassist_displaylut_h0_h3",
            "etc/fx6_stage_r44",
            "FX6_R44_NTSCPAL_CAMRESET_EXIT",
            "FX6_R44_GAMMAASSIST_DISPLAYLUT_EXIT",
            '"r44_telemetry"',
            "choices=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45]",
        ):
            self.assertIn(token, runner_src)

    def test_02_round44_native_verify_c_compiles_with_zig_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r44_verc", "build_and_run_round.py")
        if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1" and not runner.ZIG.is_file():
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertTrue(runner.ZIG.is_file(), f"Missing zig compiler at {runner.ZIG}")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            cache_dir = tmp_dir / "zig-cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            for clean_flag in ("0", "1"):
                out_bin = tmp_dir / f"fx6-stage-a-verify-r44-{clean_flag}"
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

    def test_03_round44_build_binaries_compiles_shim_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r44_shimc", "build_and_run_round.py")
        if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1" and not runner.ZIG.is_file():
            self.skipTest("Clean-room fallback without local zig binary")
        with tempfile.TemporaryDirectory() as tmp:
            for clean_flag in ("0", "1"):
                work = pathlib.Path(tmp) / f"shim_{clean_flag}"
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                    launcher_b, shim_b, meta = runner.build_binaries(
                        work,
                        fx6_round=44,
                        restore_infra70=1,
                        restore_all_early=0,
                        reply_all_200d=1,
                        initial_setting_done=1,
                        key_seq="0x7028:120:5500",
                        key_settle_ms=1500,
                        lang="schinese",
                    )
                self.assertEqual(launcher_b[:4], b"\x7fELF")
                self.assertEqual(shim_b[:4], b"\x7fELF")
                self.assertGreater(meta["shim_bytes"], 10000)

    def test_04_round44_extract_milestones_r44a_pixelmap_cnflasha_and_bridges(self) -> None:
        runner = _load_closure_module("fx6_brr_r44_msa", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R44_PIXELMAP_CNFLASHA_INIT auto_pixel_map_default_on=1 silent_mode_poweroff_shutter_ok=1 auto_off_3day_warn_ok=1 low_battery_reject_rc=-11 op_lockout_during_cal_rc=-16 auto_restart_triggered=1 auto_restart_tmp_wiped_ok=1 stock_h0_eq_h2_ok=1 cnflasha_ro_open_rc=-30 cnflasha_userspace_firewall_rc=-1 cnflasha_sha256_match=1 cnflasha_write_count=0 appfw_present=1 shim_present=1 emmc_write_count=0 r44_init_ok=1 verify_us=994466",
                "FX6_R44_PIXELMAP_CNFLASHA_BRIDGE auto_pixel_map_default_on=1 silent_poweroff_shutter_ok=1 auto_off_3day_warn_days=3 low_battery_reject_rc=-11 op_lockout_during_cal_rc=-16 auto_restart_tmp_wiped_h0_eq_h2=1 cnflasha_ro_reject_rc=-30 cnflasha_firewall_rc=-1 cnflasha_write_count=0 pixelmap_cnflasha_ok=1 emmc_write_count=0 r44_bridge_ok=1",
                "FX6_R44_NTSCPAL_CAMRESET_BRIDGE ntsc_rates_verified=4 pal_rates_verified=3 pal_2398p_reject_rc=-22 pal_tc_df_ndf_reject_rc=-95 startup_banner_ntsc_pal_ok=1 ntsc_pal_survived_camera_reset=1 initialize_restores_default=1 dual_slot_m4root_avchd_sep_ok=1 ntscpal_camreset_ok=1 emmc_write_count=0 p2_setting_writes=0",
                "FX6_R44_GAMMAASSIST_DISPLAYLUT_BRIDGE gamma_assist_4modes_verified=4 slog2_assist_reject_rc=-22 log_3modes_force_assist_off=3 gamma_assist_locked_in_log_rc=-16 display_lut_delegated_ok=1 lcd_gamma_assist_applied=1 hdmi_gamma_assist_applied=0 gammaassist_displaylut_ok=1 emmc_write_count=0",
                "FX6_STAGE_B_R44_BRIDGE round=44 faithful=1 nop_count=0 p12_wlan=1 wf12_00342260_immune=1 p10_keymap=1 p4_nd_clear=1 p11_xlr_h1=1 lang=schinese bk4_lang=0x19 enum=0x2b45_CHINESE_SIMPLIFIED font_bank=23 str_bank=19 pixelmap_autorestart_cnflasha_ro=1 ntscpal_dfn_camreset_survival=1 gammaassist_4mode_displaylut_split=1 emmc_write_count=0",
                "FX6_R44_LANG_TELEMETRY reason=gpermDrawFlush lang=schinese bk4_lang_id=0x02cf019c bk4_lang_val=0x19 gpe_fb=0 pixelmap_cnflasha_ok=1 ntscpal_camreset_ok=1 gammaassist_displaylut_ok=1 r44_bridge_ok=1 round44_realhw_pixelmap_ntscpal_gammaassist_displaylut=1 emmc_write_count=0 subst_color=0 subst_image=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        r44 = ms["r44_telemetry"]
        self.assertIsNotNone(r44)
        self.assertEqual(r44["pixelmap_cnflasha_init"]["auto_pixel_map_default_on"], 1)
        self.assertEqual(r44["pixelmap_cnflasha_init"]["low_battery_reject_rc"], -11)
        self.assertEqual(r44["pixelmap_cnflasha_init"]["stock_h0_eq_h2_ok"], 1)
        self.assertEqual(r44["pixelmap_cnflasha_init"]["cnflasha_write_count"], 0)
        self.assertEqual(r44["pixelmap_cnflasha_init"]["r44_init_ok"], 1)
        self.assertEqual(r44["pixelmap_cnflasha_bridge"]["r44_bridge_ok"], 1)
        self.assertEqual(r44["ntscpal_camreset_bridge"]["ntscpal_camreset_ok"], 1)
        self.assertEqual(r44["gammaassist_displaylut_bridge"]["gammaassist_displaylut_ok"], 1)
        self.assertEqual(r44["stage_b_bridge"]["round"], 44)
        self.assertEqual(r44["lang_telemetry"]["gpe_fb"], 0)

    def test_05_round44_extract_milestones_r44b_ntscpal_camreset(self) -> None:
        runner = _load_closure_module("fx6_brr_r44_msb", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R44_NTSCPAL_CAMRESET ntsc_rates_verified=4 ntsc_2398p_exclusive_ok=1 ntsc_pal_25p_reject_rc=-22 ntsc_tc_df_ndf_ok=1 invalid_tc_fmt_reject_rc=-22 pal_rates_verified=3 pal_2398p_reject_rc=-22 pal_2997p_reject_rc=-22 pal_tc_df_ndf_reject_rc=-95 default_banner_suppressed_ok=1 running_on_pal_banner_ok=1 running_on_ntsc_banner_ok=1 ntsc_pal_survived_camera_reset=1 initialize_restored_default_ok=1 cross_region_db_mismatch_rc=-16 dual_slot_m4root_avchd_sep_ok=1 p2_write_blocked_rc=-30 p2_setting_sha256_match=1 appfw_ok=1 shim_elf_ok=1 emmc_write_count=0 r44b_ok=1 verify_us=659645",
                "FX6_R44_NTSCPAL_CAMRESET_RC=0",
                "FX6_R44_NTSCPAL_CAMRESET_EXIT rc=0 emmc_write_count=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        r44 = ms["r44_telemetry"]
        self.assertIsNotNone(r44)
        self.assertEqual(r44["ntscpal_camreset_rc"], 0)
        b = r44["ntscpal_camreset"]
        self.assertEqual(b["ntsc_rates_verified"], 4)
        self.assertEqual(b["pal_rates_verified"], 3)
        self.assertEqual(b["pal_2398p_reject_rc"], -22)
        self.assertEqual(b["pal_tc_df_ndf_reject_rc"], -95)
        self.assertEqual(b["ntsc_pal_survived_camera_reset"], 1)
        self.assertEqual(b["initialize_restored_default_ok"], 1)
        self.assertEqual(b["dual_slot_m4root_avchd_sep_ok"], 1)
        self.assertEqual(b["r44b_ok"], 1)

    def test_06_round44_extract_milestones_r44c_gammaassist_displaylut(self) -> None:
        runner = _load_closure_module("fx6_brr_r44_msc", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R44_GAMMAASSIST_DISPLAYLUT gamma_assist_4modes_verified=4 slog2_assist_reject_rc=-22 pp_shoot_pb_hlg_still_ok=1 lcd_gamma_assist_applied=1 hdmi_gamma_assist_applied=0 lcd_only_zero_hdmi_scope_ok=1 log_3modes_force_assist_off_ok=3 gamma_assist_locked_in_log_rc=-16 display_lut_on_off_switch_ok=1 display_lut_reject_when_log_off_rc=-95 gamma_assist_unlocked_when_log_off_ok=1 p2_write_blocked_rc=-30 dlopen_ok=1 surfaces_verified=16 surfaces_h0_eq_h3=16 drift_bits=0 emmc_write_count=0 r44c_ok=1 verify_us=4898",
                "FX6_R44_GAMMAASSIST_DISPLAYLUT_RC=0",
                "FX6_R44_GAMMAASSIST_DISPLAYLUT_EXIT rc=0 emmc_write_count=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        r44 = ms["r44_telemetry"]
        self.assertIsNotNone(r44)
        self.assertEqual(r44["gammaassist_displaylut_rc"], 0)
        c = r44["gammaassist_displaylut"]
        self.assertEqual(c["gamma_assist_4modes_verified"], 4)
        self.assertEqual(c["slog2_assist_reject_rc"], -22)
        self.assertEqual(c["hdmi_gamma_assist_applied"], 0)
        self.assertEqual(c["log_3modes_force_assist_off_ok"], 3)
        self.assertEqual(c["gamma_assist_locked_in_log_rc"], -16)
        self.assertEqual(c["surfaces_h0_eq_h3"], 16)
        self.assertEqual(c["drift_bits"], 0)
        self.assertEqual(c["r44c_ok"], 1)

    def test_07_round44_stage_a_overlay_r44a_pixelmap_cnflasha_mocked_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r44_ovl_a", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            for clean_flag in ("0", "1"):
                work = tmp_dir / f"r44_a_{clean_flag}"
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                    rep, add, meta = _build_overlay_for_r44(
                        runner, tmp_dir, work, "pixelmap_reboot_cnflasha_big6", lang="schinese"
                    )
                init_out = rep["init"].decode("utf-8")
                self.assertNotIn("--r44-ntscpal-camreset", init_out)
                self.assertNotIn("--r44-gammaassist-displaylut", init_out)
                self.assertIn("--sd-gate", init_out)
                self.assertIn("etc/fx6_stage_r44", add)
                self.assertIn("r44_mode=pixelmap_reboot_cnflasha_big6", add["etc/fx6_stage_r44"][0].decode("utf-8"))
                self.assertTrue(meta["r44_enabled"])
                self.assertEqual(meta["r44"]["r44_mode"], "pixelmap_reboot_cnflasha_big6")
                self.assertEqual(meta["r44"]["auto_pixel_mapping_default"], "On")
                self.assertEqual(meta["r44"]["auto_pixel_mapping_off_manual_cadence_days"], 3)
                self.assertEqual(meta["r44"]["manual_pixel_mapping_low_battery_reject_rc"], -11)
                self.assertEqual(meta["r44"]["cnflasha_ro_open_reject_rc"], -30)
                self.assertEqual(meta["r44"]["cnflasha_write_count"], 0)

    def test_08_round44_stage_a_overlay_r44b_ntscpal_camreset_mocked_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r44_ovl_b", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            for clean_flag in ("0", "1"):
                work = tmp_dir / f"r44_b_{clean_flag}"
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                    rep, _, meta = _build_overlay_for_r44(
                        runner, tmp_dir, work, "ntscpal_dfn_camreset_persist", lang="en"
                    )
                init_out = rep["init"].decode("utf-8")
                self.assertIn("/usr/bin/fx6-stage-a-verify --r44-ntscpal-camreset", init_out)
                self.assertIn("FX6_R44_NTSCPAL_CAMRESET_EXIT", init_out)
                self.assertEqual(meta["r44"]["r44_mode"], "ntscpal_dfn_camreset_persist")
                self.assertEqual(meta["r44"]["ntsc_frame_rates"], ["23.98p", "29.97p", "59.94p", "119.88p"])
                self.assertEqual(meta["r44"]["pal_frame_rates"], ["25p", "50p", "100p"])
                self.assertEqual(meta["r44"]["pal_2398p_reject_rc"], -22)
                self.assertEqual(meta["r44"]["pal_tc_df_ndf_reject_rc"], -95)
                self.assertTrue(meta["r44"]["ntsc_pal_survives_camera_settings_reset"])

    def test_09_round44_stage_a_overlay_r44c_gammaassist_displaylut_mocked_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r44_ovl_c", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            for clean_flag in ("0", "1"):
                work = tmp_dir / f"r44_c_{clean_flag}"
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                    rep, _, meta = _build_overlay_for_r44(
                        runner, tmp_dir, work, "gammaassist_displaylut_h0_h3", lang="en"
                    )
                init_out = rep["init"].decode("utf-8")
                self.assertIn("/usr/bin/fx6-stage-a-verify --r44-gammaassist-displaylut", init_out)
                self.assertIn("FX6_R44_GAMMAASSIST_DISPLAYLUT_EXIT", init_out)
                self.assertEqual(meta["r44"]["r44_mode"], "gammaassist_displaylut_h0_h3")
                self.assertEqual(
                    meta["r44"]["gamma_disp_assist_types"],
                    ["Auto", "S-Log3->709(800%)", "HLG(BT.2020)", "HLG(709)"],
                )
                self.assertEqual(meta["r44"]["slog2_assist_reject_rc"], -22)
                self.assertEqual(meta["r44"]["log_shooting_locks_gamma_assist_off_rc"], -16)
                self.assertEqual(meta["r44"]["gamma_assist_hdmi_applied"], 0)

    def test_10_round44_stage_a_overlay_rejects_invalid_r44_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r44_badmode", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            with self.assertRaises(ValueError):
                _build_overlay_for_r44(
                    runner, tmp_dir, tmp_dir / "bad_r44", "invalid_r44_mode", lang="schinese"
                )

    def test_11_round44_summary_json_schema_sanitization_and_audit_flags(self) -> None:
        summary_path = ROUND44_REPORT_DIR / "summary.json"
        self.assertTrue(summary_path.is_file())
        raw = summary_path.read_text(encoding="utf-8")
        for forbidden in ("/Users/", "/Volumes/KAFU2T", "/private/tmp"):
            self.assertNotIn(forbidden, raw)
        data = json.loads(raw)
        self.assertEqual(
            data["schema"],
            "fx6-on-fx3-round44-realhw-pixelmap-ntscpal-gammaassist-displaylut-qemu-v1",
        )
        self.assertEqual(data["round"], 44)
        self.assertEqual(data["raw_firmware_bytes_leaked"], 0)
        self.assertIn("Linux version 4.9.337-scel+", data["kernel_version"])
        self.assertEqual(set(data["runs"].keys()), set(self.EXPECTED_RUN_KEYS))
        audit = data["r44_realhw_pixelmap_ntscpal_gammaassist_displaylut_audit"]
        self.assertEqual(audit["round"], 44)
        self.assertEqual(audit["total_runs"], 3)
        for k in (
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "r44a_auto_pixelmap_silent_shutter_lowbatt_and_op_lockout_verified",
            "r44a_auto_restart_tmp_wipe_h0_eq_h2_and_cnflasha_ro_firewall_verified",
            "r44a_stageb_big6_sid_0a_over_340k_pixels_verified",
            "r44b_ntsc_pal_exclusive_rates_and_df_ndf_lockout_verified",
            "r44b_startup_banner_camera_reset_survival_and_dual_slot_db_sep_verified",
            "r44c_gamma_assist_4mode_slog2_reject_and_zero_hdmi_scope_verified",
            "r44c_log_shooting_display_lut_lockout_and_16_h0_eq_h3_verified",
        ):
            self.assertTrue(audit[k], f"Audit flag {k} must be True")

    def test_12_round44_r44a_auto_pixelmap_silent_shutter_lowbatt_and_lockout(self) -> None:
        data = json.loads((ROUND44_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        init = data["runs"]["r44a_pixelmap_cnflasha_big6_schinese"]["r44_telemetry"]["pixelmap_cnflasha_init"]
        self.assertEqual(init["auto_pixel_map_default_on"], 1)
        self.assertEqual(init["silent_mode_poweroff_shutter_ok"], 1)
        self.assertEqual(init["auto_off_3day_warn_ok"], 1)
        self.assertEqual(init["low_battery_reject_rc"], -11)
        self.assertEqual(init["op_lockout_during_cal_rc"], -16)

    def test_13_round44_r44a_auto_restart_tmp_wipe_h0_eq_h2_and_cnflasha_ro_firewall(self) -> None:
        data = json.loads((ROUND44_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        init = data["runs"]["r44a_pixelmap_cnflasha_big6_schinese"]["r44_telemetry"]["pixelmap_cnflasha_init"]
        self.assertEqual(init["auto_restart_triggered"], 1)
        self.assertEqual(init["auto_restart_tmp_wiped_ok"], 1)
        self.assertEqual(init["stock_h0_eq_h2_ok"], 1)
        self.assertEqual(init["cnflasha_ro_open_rc"], -30)
        self.assertEqual(init["cnflasha_userspace_firewall_rc"], -1)
        self.assertEqual(init["cnflasha_sha256_match"], 1)
        self.assertEqual(init["cnflasha_write_count"], 0)
        self.assertEqual(init["appfw_present"], 1)
        self.assertEqual(init["shim_present"], 1)
        self.assertEqual(init["emmc_write_count"], 0)
        self.assertEqual(init["r44_init_ok"], 1)

    def test_14_round44_r44a_bridge_telemetry_consistent_with_r44b_and_r44c(self) -> None:
        data = json.loads((ROUND44_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        telem_a = data["runs"]["r44a_pixelmap_cnflasha_big6_schinese"]["r44_telemetry"]
        r44b = data["runs"]["r44b_ntscpal_dfn_camreset_persist"]["r44_telemetry"]["ntscpal_camreset"]
        r44c = data["runs"]["r44c_gammaassist_displaylut_h0_h3"]["r44_telemetry"]["gammaassist_displaylut"]

        pmb = telem_a["pixelmap_cnflasha_bridge"]
        self.assertEqual(pmb["auto_pixel_map_default_on"], 1)
        self.assertEqual(pmb["silent_poweroff_shutter_ok"], 1)
        self.assertEqual(pmb["auto_off_3day_warn_days"], 3)
        self.assertEqual(pmb["low_battery_reject_rc"], -11)
        self.assertEqual(pmb["op_lockout_during_cal_rc"], -16)
        self.assertEqual(pmb["auto_restart_tmp_wiped_h0_eq_h2"], 1)
        self.assertEqual(pmb["cnflasha_ro_reject_rc"], -30)
        self.assertEqual(pmb["cnflasha_firewall_rc"], -1)
        self.assertEqual(pmb["cnflasha_write_count"], 0)
        self.assertEqual(pmb["pixelmap_cnflasha_ok"], 1)
        self.assertEqual(pmb["r44_bridge_ok"], 1)

        npb = telem_a["ntscpal_camreset_bridge"]
        self.assertEqual(npb["ntsc_rates_verified"], r44b["ntsc_rates_verified"])
        self.assertEqual(npb["pal_rates_verified"], r44b["pal_rates_verified"])
        self.assertEqual(npb["pal_2398p_reject_rc"], r44b["pal_2398p_reject_rc"])
        self.assertEqual(npb["pal_tc_df_ndf_reject_rc"], r44b["pal_tc_df_ndf_reject_rc"])
        self.assertEqual(npb["ntsc_pal_survived_camera_reset"], r44b["ntsc_pal_survived_camera_reset"])
        self.assertEqual(npb["dual_slot_m4root_avchd_sep_ok"], r44b["dual_slot_m4root_avchd_sep_ok"])
        self.assertEqual(npb["ntscpal_camreset_ok"], 1)

        gab = telem_a["gammaassist_displaylut_bridge"]
        self.assertEqual(gab["gamma_assist_4modes_verified"], r44c["gamma_assist_4modes_verified"])
        self.assertEqual(gab["slog2_assist_reject_rc"], r44c["slog2_assist_reject_rc"])
        self.assertEqual(gab["log_3modes_force_assist_off"], r44c["log_3modes_force_assist_off_ok"])
        self.assertEqual(gab["gamma_assist_locked_in_log_rc"], r44c["gamma_assist_locked_in_log_rc"])
        self.assertEqual(gab["lcd_gamma_assist_applied"], r44c["lcd_gamma_assist_applied"])
        self.assertEqual(gab["hdmi_gamma_assist_applied"], r44c["hdmi_gamma_assist_applied"])
        self.assertEqual(gab["gammaassist_displaylut_ok"], 1)

    def test_15_round44_r44a_stage_b_13_sha256_and_big6_render_invariants(self) -> None:
        data = json.loads((ROUND44_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        r44a = data["runs"]["r44a_pixelmap_cnflasha_big6_schinese"]
        self.assertEqual(r44a["round"], 44)
        self.assertEqual(r44a["r44_mode"], "pixelmap_reboot_cnflasha_big6")
        self.assertEqual(r44a["target_presenter"], "31procam_big6_menu_home_presenter")
        self.assertEqual(r44a["target_sid"], "0x0a")
        self.assertEqual(r44a["nop_count"], 0)
        self.assertEqual(r44a["crashes"], 0)
        self.assertEqual(r44a["emmc_write_count"], 0)
        self.assertGreaterEqual(r44a["total_threads_seen"], 160)
        self.assertEqual(r44a["faithful_invariants"]["FX6_NATIVE_FAITHFUL"], 1)
        self.assertEqual(r44a["stage_b"]["manifest_count"], 13)
        self.assertEqual(len(r44a["stage_b"]["manifest_items"]), 13)
        for item in r44a["stage_b"]["manifest_items"]:
            self.assertEqual(len(item["sha256"]), 64)
            int(item["sha256"], 16)
        lt = r44a["r44_telemetry"]["lang_telemetry"]
        self.assertEqual(lt["gpe_fb"], 0)
        self.assertEqual(lt["subst_color"], 0)
        self.assertEqual(lt["subst_image"], 0)
        self.assertEqual(lt["r44_bridge_ok"], 1)
        self.assertEqual(lt["round44_realhw_pixelmap_ntscpal_gammaassist_displaylut"], 1)
        self.assertEqual(r44a["gpe0_readback"]["nonzero_pixels"], 346206)

    def test_16_round44_r44a_png_receipts_under_28kib_and_dimensions(self) -> None:
        data = json.loads((ROUND44_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        exports = data["runs"]["r44a_pixelmap_cnflasha_big6_schinese"]["png_exports"]
        for key in ("alpha_png", "composited_png"):
            p = REPO_ROOT / exports[key]["path"]
            self.assertTrue(p.is_file(), f"Missing Round 44 PNG: {p}")
            raw = p.read_bytes()
            self.assertLess(len(raw), 28 * 1024, f"PNG exceeds 28 KiB: {p} ({len(raw)} bytes)")
            self.assertEqual(len(raw), exports[key]["bytes"])
            self.assertEqual(hashlib.sha256(raw).hexdigest(), exports[key]["sha256"])
            w, h, rows = _decode_png_rgba_rows(raw)
            self.assertEqual((w, h), (1024, 540))
            if key == "alpha_png":
                nonzero_alpha = sum(sum(1 for a in row[3::4] if a != 0) for row in rows)
                self.assertGreater(nonzero_alpha, 340000)

    def test_17_round44_r44b_ntsc_pal_exclusive_frame_rates_and_df_ndf_table(self) -> None:
        data = json.loads((ROUND44_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        r44b = data["runs"]["r44b_ntscpal_dfn_camreset_persist"]
        self.assertEqual(r44b["round"], 44)
        self.assertEqual(r44b["r44_mode"], "ntscpal_dfn_camreset_persist")
        self.assertEqual(r44b["crashes"], 0)
        self.assertEqual(r44b["emmc_write_count"], 0)
        self.assertTrue(r44b["gpe0_readback"]["skipped_stock_fx3_mode"])
        self.assertEqual(r44b["r44_telemetry"]["ntscpal_camreset_rc"], 0)
        b = r44b["r44_telemetry"]["ntscpal_camreset"]
        self.assertEqual(b["ntsc_rates_verified"], 4)
        self.assertEqual(b["ntsc_2398p_exclusive_ok"], 1)
        self.assertEqual(b["ntsc_pal_25p_reject_rc"], -22)
        self.assertEqual(b["ntsc_tc_df_ndf_ok"], 1)
        self.assertEqual(b["invalid_tc_fmt_reject_rc"], -22)
        self.assertEqual(b["pal_rates_verified"], 3)
        self.assertEqual(b["pal_2398p_reject_rc"], -22)
        self.assertEqual(b["pal_2997p_reject_rc"], -22)
        self.assertEqual(b["pal_tc_df_ndf_reject_rc"], -95)
        self.assertEqual(b["r44b_ok"], 1)

    def test_18_round44_r44b_startup_banner_camera_reset_survival_and_dual_slot_db(self) -> None:
        data = json.loads((ROUND44_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        b = data["runs"]["r44b_ntscpal_dfn_camreset_persist"]["r44_telemetry"]["ntscpal_camreset"]
        self.assertEqual(b["default_banner_suppressed_ok"], 1)
        self.assertEqual(b["running_on_pal_banner_ok"], 1)
        self.assertEqual(b["running_on_ntsc_banner_ok"], 1)
        self.assertEqual(b["ntsc_pal_survived_camera_reset"], 1)
        self.assertEqual(b["initialize_restored_default_ok"], 1)
        self.assertEqual(b["cross_region_db_mismatch_rc"], -16)
        self.assertEqual(b["dual_slot_m4root_avchd_sep_ok"], 1)
        self.assertEqual(b["p2_write_blocked_rc"], -30)
        self.assertEqual(b["p2_setting_sha256_match"], 1)
        self.assertEqual(b["appfw_ok"], 1)
        self.assertEqual(b["shim_elf_ok"], 1)
        self.assertEqual(b["emmc_write_count"], 0)

    def test_19_round44_r44c_gamma_assist_4mode_slog2_reject_and_zero_hdmi_scope(self) -> None:
        data = json.loads((ROUND44_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        r44c = data["runs"]["r44c_gammaassist_displaylut_h0_h3"]
        self.assertEqual(r44c["round"], 44)
        self.assertEqual(r44c["r44_mode"], "gammaassist_displaylut_h0_h3")
        self.assertEqual(r44c["crashes"], 0)
        self.assertEqual(r44c["emmc_write_count"], 0)
        self.assertTrue(r44c["gpe0_readback"]["skipped_stock_fx3_mode"])
        self.assertEqual(r44c["r44_telemetry"]["gammaassist_displaylut_rc"], 0)
        c = r44c["r44_telemetry"]["gammaassist_displaylut"]
        self.assertEqual(c["gamma_assist_4modes_verified"], 4)
        self.assertEqual(c["slog2_assist_reject_rc"], -22)
        self.assertEqual(c["pp_shoot_pb_hlg_still_ok"], 1)
        self.assertEqual(c["lcd_gamma_assist_applied"], 1)
        self.assertEqual(c["hdmi_gamma_assist_applied"], 0)
        self.assertEqual(c["lcd_only_zero_hdmi_scope_ok"], 1)
        self.assertEqual(c["r44c_ok"], 1)

    def test_20_round44_r44c_log_shooting_locks_gamma_assist_off_and_delegates_display_lut(self) -> None:
        data = json.loads((ROUND44_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        c = data["runs"]["r44c_gammaassist_displaylut_h0_h3"]["r44_telemetry"]["gammaassist_displaylut"]
        self.assertEqual(c["log_3modes_force_assist_off_ok"], 3)
        self.assertEqual(c["gamma_assist_locked_in_log_rc"], -16)
        self.assertEqual(c["display_lut_on_off_switch_ok"], 1)
        self.assertEqual(c["display_lut_reject_when_log_off_rc"], -95)
        self.assertEqual(c["gamma_assist_unlocked_when_log_off_ok"], 1)
        self.assertEqual(c["p2_write_blocked_rc"], -30)

    def test_21_round44_r44c_16_surfaces_h0_eq_h3_zero_drift_and_dlopen_ok(self) -> None:
        data = json.loads((ROUND44_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        c = data["runs"]["r44c_gammaassist_displaylut_h0_h3"]["r44_telemetry"]["gammaassist_displaylut"]
        self.assertEqual(c["dlopen_ok"], 1)
        self.assertEqual(c["surfaces_verified"], 16)
        self.assertEqual(c["surfaces_h0_eq_h3"], 16)
        self.assertEqual(c["drift_bits"], 0)
        self.assertEqual(c["emmc_write_count"], 0)

    def test_22_round44_stage_b_bridge_mechanisms_and_bench_boundaries(self) -> None:
        data = json.loads((ROUND44_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        mech = data["realhw_mechanisms_verified"]
        self.assertEqual(mech["auto_pixelmap_lowbatt_autorestart_tmp_wipe_and_cnflasha_ro_init"]["r44_init_ok"], 1)
        self.assertEqual(mech["pixelmap_cnflasha_stage_b_bridge"]["r44_bridge_ok"], 1)
        self.assertEqual(mech["ntscpal_camreset_stage_b_bridge"]["ntscpal_camreset_ok"], 1)
        self.assertEqual(mech["gammaassist_displaylut_stage_b_bridge"]["gammaassist_displaylut_ok"], 1)
        self.assertEqual(mech["ntsc_pal_exclusive_rates_df_ndf_banner_and_camera_reset_survival"]["r44b_ok"], 1)
        self.assertEqual(mech["gamma_assist_4mode_log_displaylut_lockout_zero_hdmi_and_h0_h3"]["r44c_ok"], 1)

        br = data["runs"]["r44a_pixelmap_cnflasha_big6_schinese"]["r44_telemetry"]["stage_b_bridge"]
        for key in (
            "faithful",
            "p12_wlan",
            "wf12_00342260_immune",
            "p10_keymap",
            "p4_nd_clear",
            "p11_xlr_h1",
            "pixelmap_autorestart_cnflasha_ro",
            "ntscpal_dfn_camreset_survival",
            "gammaassist_4mode_displaylut_split",
        ):
            self.assertEqual(br[key], 1, f"Expected stage_b_bridge[{key}]==1")
        self.assertEqual(br["round"], 44)
        self.assertEqual(br["nop_count"], 0)
        self.assertEqual(br["emmc_write_count"], 0)
        self.assertEqual(len(data["unexecuted_physical_camera_bench_boundaries"]), 3)

    def test_23_round44_stage_b_r44_meta_parity_across_all_3_runs(self) -> None:
        data = json.loads((ROUND44_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        for rk, expected_mode in (
            ("r44a_pixelmap_cnflasha_big6_schinese", "pixelmap_reboot_cnflasha_big6"),
            ("r44b_ntscpal_dfn_camreset_persist", "ntscpal_dfn_camreset_persist"),
            ("r44c_gammaassist_displaylut_h0_h3", "gammaassist_displaylut_h0_h3"),
        ):
            r44_meta = data["runs"][rk]["stage_b"]["r44"]
            self.assertEqual(r44_meta["r44_mode"], expected_mode)
            self.assertEqual(r44_meta["auto_pixel_mapping_default"], "On")
            self.assertTrue(r44_meta["auto_pixel_mapping_poweroff_shutter_in_silent_mode"])
            self.assertEqual(r44_meta["auto_pixel_mapping_off_manual_cadence_days"], 3)
            self.assertEqual(r44_meta["manual_pixel_mapping_low_battery_reject_rc"], -11)
            self.assertEqual(r44_meta["cnflasha_ro_open_reject_rc"], -30)
            self.assertEqual(r44_meta["cnflasha_write_count"], 0)
            self.assertEqual(r44_meta["ntsc_frame_rates"], ["23.98p", "29.97p", "59.94p", "119.88p"])
            self.assertEqual(r44_meta["pal_frame_rates"], ["25p", "50p", "100p"])
            self.assertEqual(r44_meta["pal_2398p_reject_rc"], -22)
            self.assertEqual(r44_meta["pal_tc_df_ndf_reject_rc"], -95)
            self.assertTrue(r44_meta["ntsc_pal_survives_camera_settings_reset"])
            self.assertEqual(len(r44_meta["gamma_disp_assist_types"]), 4)
            self.assertEqual(r44_meta["slog2_assist_reject_rc"], -22)
            self.assertEqual(r44_meta["log_shooting_locks_gamma_assist_off_rc"], -16)
            self.assertEqual(r44_meta["gamma_assist_hdmi_applied"], 0)
            self.assertEqual(r44_meta["p2_setting_writes"], 0)

    def test_24_round44_readme_sanitization_and_no_tmp_or_binary_residue(self) -> None:
        closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn("2026-11-15-round44-realhw-pixelmap-ntscpal-gammaassist-displaylut-qemu", closure_readme)
        self.assertIn("`24` New Round 44 Dual-Mode Unit Tests (`642` Total)", closure_readme)
        r44_readme = (ROUND44_REPORT_DIR / "README.md").read_text(encoding="utf-8")
        for tok in (
            "Round 44",
            "Auto Pixel Mapping",
            "Pixel Mapping",
            "cnflasha",
            "NTSC/PAL Selector",
            "Running on NTSC.",
            "Running on PAL.",
            "Camera Settings Reset",
            "Gamma Display Assist",
            "S-Log3->709(800%)",
            "Display LUT",
            "round44-pixelmap-cnflasha-big6",
            "round44-ntscpal-camreset",
            "round44-gammaassist-displaylut",
        ):
            self.assertIn(tok, r44_readme)
        for forbidden in ("/Users/", "/Volumes/KAFU2T", "/private/tmp"):
            self.assertNotIn(forbidden, r44_readme)
        for folder in (CLOSURE_DIR, ROUND44_REPORT_DIR):
            for p in folder.rglob("*"):
                if p.is_file():
                    self.assertNotIn(p.suffix, {".cpio", ".so", ".o", ".img", ".qcow2", ".pyc"})


if __name__ == "__main__":
    unittest.main()
