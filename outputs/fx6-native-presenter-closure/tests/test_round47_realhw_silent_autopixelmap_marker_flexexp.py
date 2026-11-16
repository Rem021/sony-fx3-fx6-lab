#!/usr/bin/env python3
"""Offline dual-mode unit tests for FX6-on-FX3 Round 47 (47th Milestone / Wave-33 Live FX3 7.02 QEMU Rehearsal)."""
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
ROUND47_REPORT_DIR = (
    REPO_ROOT
    / "reports"
    / "2026-11-15-round47-realhw-silent-autopixelmap-marker-flexexp-qemu"
)
WAVE33_SPEC_PATH = (
    REPO_ROOT
    / "reports"
    / "2026-11-15-global-sony-wave33-silent-mode-autopixelmap-no-pwrshutter-marker-hdmi-isolation-flexexp-intel"
    / "README.md"
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


def _build_overlay_for_r47(
    runner,
    tmp_dir: pathlib.Path,
    work: pathlib.Path,
    r47_mode: str,
    lang: str = "schinese",
    enable_r47: bool = True,
):
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
            enable_r44=True, r44_mode="pixelmap_reboot_cnflasha_big6",
            enable_r45=True, r45_mode="steadyshot_active_cutoffs_big6",
            enable_r46=True, r46_mode="sq_fixedvar_6locks_big6",
            enable_r47=enable_r47, r47_mode=r47_mode,
            sd_manifest_mode="valid", lang=lang, shim_bytes=b"SHIM",
        )


def _load_r47_summary() -> dict:
    return json.loads((ROUND47_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))


class TestRound47RealHwSilentAutoPixelMapMarkerFlexExp(unittest.TestCase):
    EXPECTED_RUN_KEYS = (
        "r47a_silent_autopixelmap_5locks_big6_schinese",
        "r47b_marker_15ratio_persist_hdmi_isolation",
        "r47c_flexexp_avtviso_autoslowshutter_h0_h3",
    )
    EXPECTED_15_RATIOS = [
        "9:16",
        "4:5",
        "1:1",
        "4:3",
        "13:9",
        "14:9",
        "15:9",
        "16:9",
        "17:9",
        "1.66:1",
        "1.85:1",
        "1.91:1",
        "2:1",
        "2.35:1",
        "2.39:1",
    ]

    def test_01_round47_c_and_python_source_contracts(self) -> None:
        shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")

        self.assertIn("#if FX6_ROUND >= 47", shim_src)
        for token in (
            "FX6_R47_SILENT_AUTOPIXELMAP_BRIDGE",
            "FX6_R47_MARKER_15RATIO_BRIDGE",
            "FX6_R47_FLEXEXP_RESET_BRIDGE",
            "FX6_R47_LANG_TELEMETRY",
            "FX6_STAGE_B_R47_BRIDGE",
            "round47_realhw_silent_autopixelmap_marker_flexexp=1",
        ):
            self.assertIn(token, shim_src)

        for token in (
            "r47_silent_initialize_defaults",
            "r47_set_silent_mode",
            "r47_set_shutter_type",
            "r47_set_interval_shutter_type",
            "r47_set_audio_signals",
            "r47_set_flash_shooting",
            "r47_set_long_exposure_nr",
            "r47_set_efront_curtain_shutter",
            "r47_set_bulb_shooting",
            "r47_set_antiflicker_shoot",
            "r47_set_target_aperture_drive_af",
            "r47_set_target_autopixelmap",
            "r47_query_fx3_sensor_menu_item",
            "setup_r47_silent_autopixelmap_5locks_probe",
            "r47_marker_initialize_defaults",
            "r47_marker_camera_settings_reset",
            "r47_set_marker_display",
            "r47_set_center_marker",
            "r47_set_aspect_marker",
            "r47_set_safety_zone",
            "r47_set_guideframe",
            "r47_render_lcd_vs_hdmi_marker_planes",
            "run_r47_marker_15ratio_hdmi_probe",
            "r47_flexexp_initialize_all",
            "r47_flexexp_camera_settings_reset",
            "r47_set_exposure_ctrl_type",
            "r47_set_pasm_submode",
            "r47_set_flexible_av_tv_iso_switch",
            "r47_set_auto_slow_shutter",
            "run_r47_flexexp_reset_split_probe",
            "--r47-marker-15ratio-hdmi",
            "--r47-flexexp-reset-split",
            "/etc/fx6_stage_r47",
            "FX6_R47_SILENT_AUTOPIXELMAP_INIT",
            "FX6_R47_MARKER_15RATIO_HDMI",
            "FX6_R47_FLEXEXP_RESET_SPLIT",
        ):
            self.assertIn(token, verify_src)

        for token in (
            "enable_r47",
            "r47_mode",
            "--r47-mode",
            "silent_autopixelmap_5locks_big6",
            "marker_15ratio_persist_hdmi_isolation",
            "flexexp_avtviso_autoslowshutter_h0_h3",
            "etc/fx6_stage_r47",
            "FX6_R47_MARKER_15RATIO_HDMI_EXIT",
            "FX6_R47_FLEXEXP_RESET_SPLIT_EXIT",
            '"r47_telemetry"',
            "choices=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47]",
        ):
            self.assertIn(token, runner_src)

    def test_02_round47_native_verify_c_compiles_with_zig_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r47_verc", "build_and_run_round.py")
        if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1" and not runner.ZIG.is_file():
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertTrue(runner.ZIG.is_file(), f"Missing zig compiler at {runner.ZIG}")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            cache_dir = tmp_dir / "zig-cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            for clean_flag in ("0", "1"):
                out_bin = tmp_dir / f"fx6-stage-a-verify-r47-{clean_flag}"
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

    def test_03_round47_build_binaries_compiles_shim_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r47_shimc", "build_and_run_round.py")
        if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1" and not runner.ZIG.is_file():
            self.skipTest("Clean-room fallback without local zig binary")
        with tempfile.TemporaryDirectory() as tmp:
            for clean_flag in ("0", "1"):
                work = pathlib.Path(tmp) / f"shim_{clean_flag}"
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                    launcher_b, shim_b, meta = runner.build_binaries(
                        work,
                        fx6_round=47,
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
                self.assertIn(b"FX6_R47_SILENT_AUTOPIXELMAP_BRIDGE", shim_b)
                self.assertIn(b"FX6_R47_MARKER_15RATIO_BRIDGE", shim_b)
                self.assertIn(b"FX6_R47_FLEXEXP_RESET_BRIDGE", shim_b)
                self.assertGreater(meta["shim_bytes"], 10000)

    def test_04_round47_extract_milestones_r47a_silent_autopixelmap_and_bridges(self) -> None:
        runner = _load_closure_module("fx6_brr_r47_msa", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R47_SILENT_AUTOPIXELMAP_INIT invalid_silent_reject_rc=-22 normal_5funcs_unlocked_ok=1 auto_locks_electronic_and_audio_off_ok=1 silent_locks_shutter_type_rc=-16 silent_locks_interval_shutter_rc=-16 silent_locks_audio_signals_rc=-16 silent_5disabled_verified=5 dis_flash_rc=-95 dis_lenr_rc=-95 dis_efcs_rc=-95 dis_bulb_rc=-95 dis_antiflicker_rc=-95 target_aperture_drive_af_ok=1 autopixelmap_not_target_retains_ok=1 target_autopixelmap_suppresses_pwroff_cal_ok=1 silent_off_restores_autopixelmap_ok=1 pwroff_mech_shutter_actuations=0 pwroff_cnflasha_touches=0 valid_fx3_sensor_items_ok=3 shutter_when_pwroff_setup_reject_rc=-2 shutter_when_pwroff_target_reject_rc=-2 p2_write_blocked_rc=-30 p2_sha256_match=1 cnflasha_sha256_match=1 appfw_present=1 shim_present=1 emmc_write_count=0 r47_init_ok=1 verify_us=909100",
                "FX6_R47_SILENT_AUTOPIXELMAP_BRIDGE silent_locks_shutter_type_rc=-16 silent_locks_interval_shutter_rc=-16 silent_locks_audio_signals_rc=-16 silent_5disabled_verified=5 target_aperture_drive_af_ok=1 target_autopixelmap_suppresses_pwroff_cal_ok=1 autopixelmap_not_target_retains_ok=1 pwroff_cnflasha_touches=0 shutter_when_pwroff_reject_rc=-2 silent_autopixelmap_ok=1 emmc_write_count=0 r47_bridge_ok=1",
                "FX6_R47_MARKER_15RATIO_BRIDGE marker_defaults_off_ok=1 aspect_marker_15ratios_verified=15 ver300_16_9_ratio_verified=1 safety_zone_3modes_verified=3 guideframe_2modes_verified=2 marker_survives_cam_settings_reset_ok=1 initialize_resets_marker_all_off_ok=1 hdmi_info_display_on=1 hdmi_marker_overlay_px=0 marker_15ratio_hdmi_ok=1 emmc_write_count=0 p2_setting_writes=0",
                "FX6_R47_FLEXEXP_RESET_BRIDGE exp_ctrl_2types_verified=2 pasm_4submodes_verified=4 av_tv_iso_defaults_manual_ok=1 av_tv_iso_8combos_verified=8 auto_slow_shutter_default_on_ok=1 cam_reset_restores_av_tv_iso_manual_ok=1 cam_reset_restores_auto_slow_shutter_on_ok=1 cam_reset_preserves_marker_zebra_ntscpal_ok=1 flexexp_reset_split_ok=1 emmc_write_count=0",
                "FX6_STAGE_B_R47_BRIDGE round=47 faithful=1 nop_count=0 p12_wlan=1 wf12_00342260_immune=1 p10_keymap=1 p4_nd_clear=1 p11_xlr_h1=1 lang=schinese bk4_lang=0x19 enum=0x2b45_CHINESE_SIMPLIFIED font_bank=23 str_bank=19 silent_autopixelmap_no_pwrshutter=1 marker_15ratio_camreset_hdmi_zero=1 flexexp_avtviso_autoslowshutter_split=1 emmc_write_count=0",
                "FX6_R47_LANG_TELEMETRY reason=gpermDrawFlush lang=schinese bk4_lang_id=0x02cf019c bk4_lang_val=0x19 gpe_fb=0 silent_autopixelmap_ok=1 marker_15ratio_hdmi_ok=1 flexexp_reset_split_ok=1 r47_bridge_ok=1 round47_realhw_silent_autopixelmap_marker_flexexp=1 emmc_write_count=0 subst_color=0 subst_image=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        r47 = ms["r47_telemetry"]
        self.assertIsNotNone(r47)
        self.assertEqual(r47["silent_autopixelmap_init"]["silent_locks_shutter_type_rc"], -16)
        self.assertEqual(r47["silent_autopixelmap_init"]["silent_5disabled_verified"], 5)
        self.assertEqual(r47["silent_autopixelmap_init"]["shutter_when_pwroff_setup_reject_rc"], -2)
        self.assertEqual(r47["silent_autopixelmap_init"]["r47_init_ok"], 1)
        self.assertEqual(r47["silent_autopixelmap_bridge"]["r47_bridge_ok"], 1)
        self.assertEqual(r47["marker_15ratio_bridge"]["hdmi_marker_overlay_px"], 0)
        self.assertEqual(r47["flexexp_reset_bridge"]["av_tv_iso_8combos_verified"], 8)
        self.assertEqual(r47["stage_b_bridge"]["round"], 47)
        self.assertEqual(r47["lang_telemetry"]["gpe_fb"], 0)

    def test_05_round47_extract_milestones_r47b_marker_15ratio_hdmi(self) -> None:
        runner = _load_closure_module("fx6_brr_r47_msb", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R47_MARKER_15RATIO_HDMI marker_defaults_off_ok=1 invalid_marker_disp_reject_rc=-22 invalid_center_reject_rc=-22 invalid_aspect_reject_rc=-22 invalid_safety_reject_rc=-22 invalid_guideframe_reject_rc=-22 center_marker_2modes_verified=2 aspect_marker_off_plus_15ratios_verified=16 aspect_marker_15ratios_verified=15 ver300_16_9_ratio_verified=1 safety_zone_3modes_verified=3 guideframe_2modes_verified=2 marker_15ratios_survive_cam_reset=15 marker_survives_cam_settings_reset_ok=1 initialize_resets_marker_all_off_ok=1 hdmi_info_display_on=1 lcd_marker_overlay_px=16256 hdmi_marker_overlay_px=0 hdmi_clean_feed_combos_verified=32 hdmi_info_on_zero_marker_ok=1 p2_write_blocked_rc=-30 p2_setting_sha256_match=1 appfw_ok=1 shim_elf_ok=1 emmc_write_count=0 r47b_ok=1 verify_us=723491",
                "FX6_R47_MARKER_15RATIO_HDMI_RC=0",
                "FX6_R47_MARKER_15RATIO_HDMI_EXIT rc=0 emmc_write_count=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        r47 = ms["r47_telemetry"]
        self.assertIsNotNone(r47)
        self.assertEqual(r47["marker_15ratio_hdmi_rc"], 0)
        b = r47["marker_15ratio_hdmi"]
        self.assertEqual(b["aspect_marker_15ratios_verified"], 15)
        self.assertEqual(b["marker_survives_cam_settings_reset_ok"], 1)
        self.assertEqual(b["hdmi_marker_overlay_px"], 0)
        self.assertEqual(b["hdmi_clean_feed_combos_verified"], 32)
        self.assertEqual(b["r47b_ok"], 1)

    def test_06_round47_extract_milestones_r47c_flexexp_reset_split(self) -> None:
        runner = _load_closure_module("fx6_brr_r47_msc", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R47_FLEXEXP_RESET_SPLIT av_tv_iso_defaults_manual_ok=1 auto_slow_shutter_default_on_ok=1 invalid_exp_ctrl_reject_rc=-22 exp_ctrl_2types_verified=2 pasm_4submodes_verified=4 flex_sw_in_pasm_reject_rc=-95 pasm_submode_in_flex_reject_rc=-16 invalid_av_tv_iso_reject_rc=-22 invalid_auto_slow_shutter_reject_rc=-22 av_tv_iso_8combos_verified=8 cam_reset_restores_av_tv_iso_manual_ok=1 cam_reset_restores_auto_slow_shutter_on_ok=1 cam_reset_preserves_marker_zebra_ntscpal_ok=1 initialize_resets_all_ok=1 p2_write_blocked_rc=-30 dlopen_ok=1 surfaces_verified=16 surfaces_h0_eq_h3=16 drift_bits=0 emmc_write_count=0 r47c_ok=1 verify_us=153838",
                "FX6_R47_FLEXEXP_RESET_SPLIT_RC=0",
                "FX6_R47_FLEXEXP_RESET_SPLIT_EXIT rc=0 emmc_write_count=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        r47 = ms["r47_telemetry"]
        self.assertIsNotNone(r47)
        self.assertEqual(r47["flexexp_reset_split_rc"], 0)
        c = r47["flexexp_reset_split"]
        self.assertEqual(c["exp_ctrl_2types_verified"], 2)
        self.assertEqual(c["av_tv_iso_8combos_verified"], 8)
        self.assertEqual(c["cam_reset_restores_av_tv_iso_manual_ok"], 1)
        self.assertEqual(c["surfaces_h0_eq_h3"], 16)
        self.assertEqual(c["r47c_ok"], 1)

    def test_07_round47_extract_milestones_returns_none_when_no_r47_lines(self) -> None:
        runner = _load_closure_module("fx6_brr_r47_msnone", "build_and_run_round.py")
        ms = runner.extract_milestones("Linux version 4.9.337-scel+ #1 SMP PREEMPT\n")
        self.assertIsNone(ms["r47_telemetry"])

    def test_08_round47_stage_a_overlay_r47a_silent_autopixelmap_mocked_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r47_ovl_a", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            for clean_flag in ("0", "1"):
                work = tmp_dir / f"r47_a_{clean_flag}"
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                    rep, add, meta = _build_overlay_for_r47(
                        runner, tmp_dir, work, "silent_autopixelmap_5locks_big6", lang="schinese"
                    )
                init_out = rep["init"].decode("utf-8")
                self.assertNotIn("--r47-marker-15ratio-hdmi", init_out)
                self.assertNotIn("--r47-flexexp-reset-split", init_out)
                self.assertIn("--sd-gate", init_out)
                self.assertIn("etc/fx6_stage_r47", add)
                self.assertIn("r47_mode=silent_autopixelmap_5locks_big6", add["etc/fx6_stage_r47"][0].decode("utf-8"))
                self.assertTrue(meta["r47_enabled"])
                self.assertEqual(meta["r47"]["r47_mode"], "silent_autopixelmap_5locks_big6")
                self.assertEqual(meta["r47"]["shutter_when_pwroff_reject_rc"], -2)
                self.assertEqual(meta["r47"]["hdmi_marker_overlay_pixels"], 0)
                self.assertEqual(meta["r47"]["p2_setting_writes"], 0)

    def test_09_round47_stage_a_overlay_r47b_and_r47c_mocked_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r47_ovl_bc", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            for clean_flag in ("0", "1"):
                work_b = tmp_dir / f"r47_b_{clean_flag}"
                work_c = tmp_dir / f"r47_c_{clean_flag}"
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                    rep_b, _, meta_b = _build_overlay_for_r47(
                        runner, tmp_dir, work_b, "marker_15ratio_persist_hdmi_isolation", lang="en"
                    )
                    rep_c, _, meta_c = _build_overlay_for_r47(
                        runner, tmp_dir, work_c, "flexexp_avtviso_autoslowshutter_h0_h3", lang="en"
                    )
                init_b = rep_b["init"].decode("utf-8")
                init_c = rep_c["init"].decode("utf-8")
                self.assertIn("/usr/bin/fx6-stage-a-verify --r47-marker-15ratio-hdmi", init_b)
                self.assertIn("FX6_R47_MARKER_15RATIO_HDMI_EXIT", init_b)
                self.assertEqual(meta_b["r47"]["r47_mode"], "marker_15ratio_persist_hdmi_isolation")
                self.assertIn("/usr/bin/fx6-stage-a-verify --r47-flexexp-reset-split", init_c)
                self.assertIn("FX6_R47_FLEXEXP_RESET_SPLIT_EXIT", init_c)
                self.assertEqual(meta_c["r47"]["r47_mode"], "flexexp_avtviso_autoslowshutter_h0_h3")

    def test_10_round47_stage_a_overlay_rejects_invalid_mode_and_honors_disabled_flag(self) -> None:
        runner = _load_closure_module("fx6_brr_r47_badmode", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            with self.assertRaises(ValueError):
                _build_overlay_for_r47(
                    runner, tmp_dir, tmp_dir / "bad_r47", "invalid_r47_mode", lang="schinese"
                )
            _, add_off, meta_off = _build_overlay_for_r47(
                runner, tmp_dir, tmp_dir / "off_r47", "silent_autopixelmap_5locks_big6", enable_r47=False
            )
            self.assertFalse(meta_off["r47_enabled"])
            self.assertNotIn("r47", meta_off)
            self.assertNotIn("etc/fx6_stage_r47", add_off)

    def test_11_round47_summary_json_schema_sanitization_and_audit_flags(self) -> None:
        summary_path = ROUND47_REPORT_DIR / "summary.json"
        self.assertTrue(summary_path.is_file())
        raw = summary_path.read_text(encoding="utf-8")
        for forbidden in ("/Users/", "/Volumes/KAFU2T", "/private/tmp"):
            self.assertNotIn(forbidden, raw)
        data = json.loads(raw)
        self.assertEqual(
            data["schema"],
            "fx6-on-fx3-round47-realhw-silent-autopixelmap-marker-flexexp-qemu-v1",
        )
        self.assertEqual(data["round"], 47)
        self.assertEqual(data["raw_firmware_bytes_leaked"], 0)
        self.assertIn("Linux version 4.9.337-scel+", data["kernel_version"])
        self.assertEqual(set(data["runs"].keys()), set(self.EXPECTED_RUN_KEYS))
        audit = data["r47_realhw_silent_autopixelmap_marker_flexexp_audit"]
        self.assertEqual(audit["round"], 47)
        self.assertEqual(audit["milestone"], 47)
        self.assertEqual(audit["total_runs"], 3)
        for k in (
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "r47a_silent_mode_shutter_audio_and_5_disabled_functions_verified",
            "r47a_target_function_settings_autopixelmap_suppression_and_no_pwrshutter_enoent_verified",
            "r47a_stageb_big6_sid_0a_over_340k_pixels_verified",
            "r47b_marker_display_15_ratios_camera_settings_reset_survival_and_initialize_reset_verified",
            "r47b_marker_display_zero_hdmi_overlay_pixels_when_hdmi_info_on_verified",
            "r47c_exposure_ctrl_type_flexible_exp_and_av_tv_iso_auto_slow_shutter_reset_split_verified",
            "r47c_dlopen_libjit_and_16_h0_eq_h3_rollback_verified",
        ):
            self.assertTrue(audit[k], f"Audit flag {k} must be True")

    def test_12_round47_r47a_silent_mode_locks_shutter_interval_shutter_and_audio_signals(self) -> None:
        data = _load_r47_summary()
        init = data["runs"]["r47a_silent_autopixelmap_5locks_big6_schinese"]["r47_telemetry"]["silent_autopixelmap_init"]
        r47_meta = data["runs"]["r47a_silent_autopixelmap_5locks_big6_schinese"]["stage_b"]["r47"]
        locks = r47_meta["silent_mode_locks"]
        self.assertEqual(locks["Shutter Type"], "Electronic Shutter")
        self.assertEqual(locks["Shutter Type in Interval"], "Electronic Shutter")
        self.assertEqual(locks["Audio signals"], "Off")
        self.assertEqual(r47_meta["silent_locks_reject_rc"], -16)
        self.assertEqual(init["invalid_silent_reject_rc"], -22)
        self.assertEqual(init["auto_locks_electronic_and_audio_off_ok"], 1)
        self.assertEqual(init["silent_locks_shutter_type_rc"], -16)
        self.assertEqual(init["silent_locks_interval_shutter_rc"], -16)
        self.assertEqual(init["silent_locks_audio_signals_rc"], -16)

    def test_13_round47_r47a_silent_mode_5_disabled_functions_enforced_and_restored(self) -> None:
        data = _load_r47_summary()
        init = data["runs"]["r47a_silent_autopixelmap_5locks_big6_schinese"]["r47_telemetry"]["silent_autopixelmap_init"]
        r47_meta = data["runs"]["r47a_silent_autopixelmap_5locks_big6_schinese"]["stage_b"]["r47"]
        self.assertEqual(
            r47_meta["silent_5_disabled_functions"],
            [
                "Flash",
                "Long Exposure NR",
                "e-Front Curtain Shut.",
                "BULB",
                "Anti-flicker Shoot.",
            ],
        )
        self.assertEqual(r47_meta["silent_disabled_reject_rc"], -95)
        self.assertEqual(init["normal_5funcs_unlocked_ok"], 1)
        self.assertEqual(init["silent_5disabled_verified"], 5)
        for k in ("dis_flash_rc", "dis_lenr_rc", "dis_efcs_rc", "dis_bulb_rc", "dis_antiflicker_rc"):
            self.assertEqual(init[k], -95, f"Expected EOPNOTSUPP (-95) for {k}")

    def test_14_round47_r47a_target_function_settings_aperture_drive_in_af(self) -> None:
        data = _load_r47_summary()
        init = data["runs"]["r47a_silent_autopixelmap_5locks_big6_schinese"]["r47_telemetry"]["silent_autopixelmap_init"]
        r47_meta = data["runs"]["r47a_silent_autopixelmap_5locks_big6_schinese"]["stage_b"]["r47"]
        self.assertEqual(
            r47_meta["target_function_settings"],
            ["Aperture Drive in AF", "Auto Pixel Mapping"],
        )
        self.assertEqual(init["target_aperture_drive_af_ok"], 1)

    def test_15_round47_r47a_target_function_settings_auto_pixel_mapping_suppresses_poweroff_calibration(self) -> None:
        data = _load_r47_summary()
        init = data["runs"]["r47a_silent_autopixelmap_5locks_big6_schinese"]["r47_telemetry"]["silent_autopixelmap_init"]
        r47_meta = data["runs"]["r47a_silent_autopixelmap_5locks_big6_schinese"]["stage_b"]["r47"]
        self.assertTrue(r47_meta["autopixelmap_targeted_suppresses_pwroff_cal"])
        self.assertTrue(r47_meta["autopixelmap_not_target_retains_setting"])
        self.assertEqual(r47_meta["pwroff_cnflasha_touches"], 0)
        self.assertEqual(init["autopixelmap_not_target_retains_ok"], 1)
        self.assertEqual(init["target_autopixelmap_suppresses_pwroff_cal_ok"], 1)
        self.assertEqual(init["silent_off_restores_autopixelmap_ok"], 1)
        self.assertEqual(init["pwroff_mech_shutter_actuations"], 0)
        self.assertEqual(init["pwroff_cnflasha_touches"], 0)

    def test_16_round47_r47a_fx3_702_rejects_nonexistent_shutter_when_pwr_off_with_enoent(self) -> None:
        data = _load_r47_summary()
        init = data["runs"]["r47a_silent_autopixelmap_5locks_big6_schinese"]["r47_telemetry"]["silent_autopixelmap_init"]
        r47_meta = data["runs"]["r47a_silent_autopixelmap_5locks_big6_schinese"]["stage_b"]["r47"]
        self.assertEqual(
            r47_meta["fx3_sensor_items_present"],
            ["Sensor Cleaning", "Auto Pixel Mapping", "Pixel Mapping"],
        )
        self.assertEqual(r47_meta["fx3_absent_menu_item"], "Shutter When Pwr OFF")
        self.assertEqual(r47_meta["shutter_when_pwroff_reject_rc"], -2)
        self.assertEqual(init["valid_fx3_sensor_items_ok"], 3)
        self.assertEqual(init["shutter_when_pwroff_setup_reject_rc"], -2)
        self.assertEqual(init["shutter_when_pwroff_target_reject_rc"], -2)

    def test_17_round47_r47a_c_source_rejects_shutter_when_pwr_off_with_enoent(self) -> None:
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        self.assertIn("R47_SENSOR_ITEM_SHUTTER_WHEN_PWROFF", verify_src)
        self.assertIn("return -ENOENT;", verify_src)

    def test_18_round47_r47a_p2_and_cnflasha_ro_firewall_and_elf_presence(self) -> None:
        data = _load_r47_summary()
        init = data["runs"]["r47a_silent_autopixelmap_5locks_big6_schinese"]["r47_telemetry"]["silent_autopixelmap_init"]
        self.assertEqual(init["p2_write_blocked_rc"], -30)
        self.assertEqual(init["p2_sha256_match"], 1)
        self.assertEqual(init["cnflasha_sha256_match"], 1)
        self.assertEqual(init["appfw_present"], 1)
        self.assertEqual(init["shim_present"], 1)
        self.assertEqual(init["emmc_write_count"], 0)
        self.assertEqual(init["r47_init_ok"], 1)

    def test_19_round47_r47a_stage_b_13_sha256_locks_and_manifest_integrity(self) -> None:
        data = _load_r47_summary()
        r47a = data["runs"]["r47a_silent_autopixelmap_5locks_big6_schinese"]
        self.assertEqual(r47a["stage_b"]["manifest_count"], 13)
        self.assertEqual(len(r47a["stage_b"]["manifest_items"]), 13)
        seen_paths = set()
        for item in r47a["stage_b"]["manifest_items"]:
            seen_paths.add(item["guest_path"])
            self.assertEqual(len(item["sha256"]), 64)
            int(item["sha256"], 16)
        self.assertIn("/usr/lib/appFw.so", seen_paths)
        self.assertIn("/usr/lib/libgrm-fbinit9.so", seen_paths)

    def test_20_round47_r47a_big6_home_schinese_render_invariants(self) -> None:
        data = _load_r47_summary()
        r47a = data["runs"]["r47a_silent_autopixelmap_5locks_big6_schinese"]
        self.assertEqual(r47a["round"], 47)
        self.assertEqual(r47a["lang"], "schinese")
        self.assertEqual(r47a["r47_mode"], "silent_autopixelmap_5locks_big6")
        self.assertEqual(r47a["target_presenter"], "31procam_big6_menu_home_presenter")
        self.assertEqual(r47a["target_sid"], "0x0a")
        self.assertEqual(r47a["nop_count"], 0)
        self.assertEqual(r47a["crashes"], 0)
        self.assertEqual(r47a["emmc_write_count"], 0)
        self.assertGreaterEqual(r47a["total_threads_seen"], 160)
        fi = r47a["faithful_invariants"]
        self.assertEqual(fi["FX6_NATIVE_FAITHFUL"], 1)
        self.assertEqual(fi["subst_color"], 0)
        self.assertEqual(fi["subst_image"], 0)
        self.assertEqual(fi["forced_render"], 0)
        self.assertEqual(fi["skipped_node"], 0)
        self.assertEqual(fi["lock_bypass"], 0)

    def test_21_round47_r47a_gpe0_framebuffer_readback_over_340k_pixels(self) -> None:
        data = _load_r47_summary()
        gpe = data["runs"]["r47a_silent_autopixelmap_5locks_big6_schinese"]["gpe0_readback"]
        lt = data["runs"]["r47a_silent_autopixelmap_5locks_big6_schinese"]["r47_telemetry"]["lang_telemetry"]
        self.assertTrue(gpe["present"])
        self.assertEqual(gpe["bytes"], 2211840)
        self.assertEqual(gpe["total_pixels"], 552960)
        self.assertGreaterEqual(gpe["nonzero_pixels"], 346000)
        self.assertGreaterEqual(gpe["unique_colors"], 80)
        self.assertEqual(lt["gpe_fb"], 0)
        self.assertEqual(lt["font_bank"], 23)
        self.assertEqual(lt["str_bank"], 19)

    def test_22_round47_r47a_alpha_png_under_50kib_crc_and_sha256(self) -> None:
        data = _load_r47_summary()
        ap = data["runs"]["r47a_silent_autopixelmap_5locks_big6_schinese"]["png_exports"]["alpha_png"]
        p = REPO_ROOT / ap["path"]
        self.assertTrue(p.is_file(), f"Missing alpha PNG: {p}")
        raw = p.read_bytes()
        self.assertLess(len(raw), 50 * 1024)
        self.assertLess(len(raw), 28 * 1024)
        self.assertEqual(len(raw), ap["bytes"])
        self.assertEqual(hashlib.sha256(raw).hexdigest(), ap["sha256"])
        w, h, rows = _decode_png_rgba_rows(raw)
        self.assertEqual((w, h, len(rows)), (1024, 540, 540))

    def test_23_round47_r47a_composited_png_under_50kib_crc_and_sha256(self) -> None:
        data = _load_r47_summary()
        cp = data["runs"]["r47a_silent_autopixelmap_5locks_big6_schinese"]["png_exports"]["composited_png"]
        p = REPO_ROOT / cp["path"]
        self.assertTrue(p.is_file(), f"Missing composited PNG: {p}")
        raw = p.read_bytes()
        self.assertLess(len(raw), 50 * 1024)
        self.assertLess(len(raw), 28 * 1024)
        self.assertEqual(len(raw), cp["bytes"])
        self.assertEqual(hashlib.sha256(raw).hexdigest(), cp["sha256"])
        w, h, rows = _decode_png_rgba_rows(raw)
        self.assertEqual((w, h, len(rows)), (1024, 540, 540))

    def test_24_round47_r47a_alpha_vs_composited_backdrop_pixel_consistency(self) -> None:
        data = _load_r47_summary()
        exp = data["runs"]["r47a_silent_autopixelmap_5locks_big6_schinese"]["png_exports"]
        self.assertEqual(exp["backdrop_rgb"], "#161a20")
        _, _, a_rows = _decode_png_rgba_rows((REPO_ROOT / exp["alpha_png"]["path"]).read_bytes())
        _, _, c_rows = _decode_png_rgba_rows((REPO_ROOT / exp["composited_png"]["path"]).read_bytes())
        transparent_px = 0
        opaque_px = 0
        for ar, cr in zip(a_rows, c_rows):
            for x in range(0, 1024 * 4, 4):
                if ar[x + 3] == 0:
                    transparent_px += 1
                    self.assertEqual((cr[x], cr[x + 1], cr[x + 2], cr[x + 3]), (0x16, 0x1A, 0x20, 0xFF))
                elif ar[x + 3] == 0xFF:
                    opaque_px += 1
                    self.assertEqual(ar[x : x + 4], cr[x : x + 4])
        self.assertGreater(transparent_px, 200000)
        self.assertGreater(opaque_px, 340000)

    def test_25_round47_r47a_stage_b_bridge_telemetry_flags(self) -> None:
        data = _load_r47_summary()
        sb_bridge = data["runs"]["r47a_silent_autopixelmap_5locks_big6_schinese"]["r47_telemetry"]["stage_b_bridge"]
        lt = data["runs"]["r47a_silent_autopixelmap_5locks_big6_schinese"]["r47_telemetry"]["lang_telemetry"]
        self.assertEqual(sb_bridge["round"], 47)
        self.assertEqual(sb_bridge["silent_autopixelmap_no_pwrshutter"], 1)
        self.assertEqual(sb_bridge["marker_15ratio_camreset_hdmi_zero"], 1)
        self.assertEqual(sb_bridge["flexexp_avtviso_autoslowshutter_split"], 1)
        self.assertEqual(lt["round47_realhw_silent_autopixelmap_marker_flexexp"], 1)
        self.assertEqual(lt["r47_bridge_ok"], 1)

    def test_26_round47_r47a_prefix_counts_include_r47_and_osd_flush(self) -> None:
        data = _load_r47_summary()
        counts = data["runs"]["r47a_silent_autopixelmap_5locks_big6_schinese"]["prefix_counts"]
        self.assertGreater(counts["FX6_R47_"], 100)
        self.assertGreater(counts["FX6_OSD_FLUSH"], 100)
        self.assertEqual(counts.get("APPFW_SEGV", 0), 0)
        self.assertEqual(counts.get("FX6_ABORT_", 0), 0)

    def test_27_round47_r47b_marker_display_defaults_and_center_marker(self) -> None:
        data = _load_r47_summary()
        r47b = data["runs"]["r47b_marker_15ratio_persist_hdmi_isolation"]
        mk = r47b["r47_telemetry"]["marker_15ratio_hdmi"]
        r47_meta = r47b["stage_b"]["r47"]
        self.assertEqual(r47b["r47_telemetry"]["marker_15ratio_hdmi_rc"], 0)
        self.assertEqual(
            r47_meta["marker_display_subitems"],
            ["Marker Display", "Center Marker", "Aspect Marker", "Safety Zone", "Guideframe"],
        )
        self.assertEqual(mk["marker_defaults_off_ok"], 1)
        self.assertEqual(mk["center_marker_2modes_verified"], 2)
        self.assertEqual(mk["invalid_marker_disp_reject_rc"], -22)
        self.assertEqual(mk["invalid_center_reject_rc"], -22)

    def test_28_round47_r47b_aspect_marker_all_15_ratios_including_ver300_16_9(self) -> None:
        data = _load_r47_summary()
        r47b = data["runs"]["r47b_marker_15ratio_persist_hdmi_isolation"]
        mk = r47b["r47_telemetry"]["marker_15ratio_hdmi"]
        r47_meta = r47b["stage_b"]["r47"]
        self.assertEqual(r47_meta["aspect_marker_15_ratios"], self.EXPECTED_15_RATIOS)
        self.assertEqual(len(r47_meta["aspect_marker_15_ratios"]), 15)
        self.assertIn("16:9", r47_meta["aspect_marker_15_ratios"])
        self.assertEqual(r47_meta["ver300_added_aspect_ratio"], "16:9")
        self.assertEqual(mk["aspect_marker_off_plus_15ratios_verified"], 16)
        self.assertEqual(mk["aspect_marker_15ratios_verified"], 15)
        self.assertEqual(mk["ver300_16_9_ratio_verified"], 1)
        self.assertEqual(mk["invalid_aspect_reject_rc"], -22)

    def test_29_round47_r47b_safety_zone_80_90_and_guideframe_modes(self) -> None:
        data = _load_r47_summary()
        r47b = data["runs"]["r47b_marker_15ratio_persist_hdmi_isolation"]
        mk = r47b["r47_telemetry"]["marker_15ratio_hdmi"]
        r47_meta = r47b["stage_b"]["r47"]
        self.assertEqual(r47_meta["safety_zone_modes"], ["Off", "80%", "90%"])
        self.assertEqual(r47_meta["guideframe_modes"], ["Off", "On"])
        self.assertEqual(mk["safety_zone_3modes_verified"], 3)
        self.assertEqual(mk["guideframe_2modes_verified"], 2)
        self.assertEqual(mk["invalid_safety_reject_rc"], -22)
        self.assertEqual(mk["invalid_guideframe_reject_rc"], -22)

    def test_30_round47_r47b_marker_15_ratios_survive_camera_settings_reset_cleared_only_by_initialize(self) -> None:
        data = _load_r47_summary()
        r47b = data["runs"]["r47b_marker_15ratio_persist_hdmi_isolation"]
        mk = r47b["r47_telemetry"]["marker_15ratio_hdmi"]
        r47_meta = r47b["stage_b"]["r47"]
        self.assertTrue(r47_meta["marker_survives_camera_settings_reset"])
        self.assertTrue(r47_meta["marker_reset_only_by_initialize"])
        self.assertEqual(mk["marker_15ratios_survive_cam_reset"], 15)
        self.assertEqual(mk["marker_survives_cam_settings_reset_ok"], 1)
        self.assertEqual(mk["initialize_resets_marker_all_off_ok"], 1)

    def test_31_round47_r47b_zero_hdmi_marker_overlay_pixels_even_when_hdmi_info_display_on(self) -> None:
        data = _load_r47_summary()
        mk = data["runs"]["r47b_marker_15ratio_persist_hdmi_isolation"]["r47_telemetry"]["marker_15ratio_hdmi"]
        self.assertEqual(mk["hdmi_info_display_on"], 1)
        self.assertGreater(mk["lcd_marker_overlay_px"], 0)
        self.assertEqual(mk["hdmi_marker_overlay_px"], 0)
        self.assertEqual(mk["hdmi_clean_feed_combos_verified"], 32)
        self.assertEqual(mk["hdmi_info_on_zero_marker_ok"], 1)

    def test_32_round47_r47b_p2_ro_protection_and_early_exit_readback_skip(self) -> None:
        data = _load_r47_summary()
        r47b = data["runs"]["r47b_marker_15ratio_persist_hdmi_isolation"]
        mk = r47b["r47_telemetry"]["marker_15ratio_hdmi"]
        self.assertEqual(mk["p2_write_blocked_rc"], -30)
        self.assertEqual(mk["p2_setting_sha256_match"], 1)
        self.assertEqual(mk["appfw_ok"], 1)
        self.assertEqual(mk["shim_elf_ok"], 1)
        self.assertEqual(mk["emmc_write_count"], 0)
        self.assertEqual(mk["r47b_ok"], 1)
        self.assertFalse(r47b["gpe0_readback"]["present"])
        self.assertTrue(r47b["gpe0_readback"]["skipped_stock_fx3_mode"])

    def test_33_round47_r47b_c_source_enforces_zero_hdmi_marker_pixels_and_15_ratios_table(self) -> None:
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        self.assertIn("*out_hdmi_marker_px = 0U;", verify_src)
        for ratio in self.EXPECTED_15_RATIOS:
            self.assertIn(f'"{ratio}"', verify_src)

    def test_34_round47_r47c_exposure_ctrl_type_pasm_4_submodes_vs_flexible_exp_mode(self) -> None:
        data = _load_r47_summary()
        r47c = data["runs"]["r47c_flexexp_avtviso_autoslowshutter_h0_h3"]
        fx = r47c["r47_telemetry"]["flexexp_reset_split"]
        r47_meta = r47c["stage_b"]["r47"]
        self.assertEqual(
            r47_meta["exposure_ctrl_types"],
            ["P/A/S/M Mode", "Flexible Exp. Mode"],
        )
        self.assertEqual(
            r47_meta["pasm_submodes"],
            ["Program Auto", "Aperture Priority", "Shutter Priority", "Manual Exposure"],
        )
        self.assertEqual(fx["invalid_exp_ctrl_reject_rc"], -22)
        self.assertEqual(fx["exp_ctrl_2types_verified"], 2)
        self.assertEqual(fx["pasm_4submodes_verified"], 4)

    def test_35_round47_r47c_pasm_vs_flexible_exp_cross_mode_interlock_rejections(self) -> None:
        data = _load_r47_summary()
        fx = data["runs"]["r47c_flexexp_avtviso_autoslowshutter_h0_h3"]["r47_telemetry"]["flexexp_reset_split"]
        self.assertEqual(fx["flex_sw_in_pasm_reject_rc"], -95)
        self.assertEqual(fx["pasm_submode_in_flex_reject_rc"], -16)

    def test_36_round47_r47c_av_tv_iso_auto_manual_switches_default_manual_and_8_combinations(self) -> None:
        data = _load_r47_summary()
        r47c = data["runs"]["r47c_flexexp_avtviso_autoslowshutter_h0_h3"]
        fx = r47c["r47_telemetry"]["flexexp_reset_split"]
        r47_meta = r47c["stage_b"]["r47"]
        self.assertEqual(
            r47_meta["auto_manual_swt_set_channels"],
            ["Av Auto/Manual Switch", "Tv Auto/Manual Switch", "ISO Auto/Manual Set"],
        )
        self.assertEqual(r47_meta["auto_manual_swt_set_default"], "Manual")
        self.assertEqual(fx["av_tv_iso_defaults_manual_ok"], 1)
        self.assertEqual(fx["invalid_av_tv_iso_reject_rc"], -22)
        self.assertEqual(fx["av_tv_iso_8combos_verified"], 8)

    def test_37_round47_r47c_auto_slow_shutter_default_on_and_invalid_reject(self) -> None:
        data = _load_r47_summary()
        r47c = data["runs"]["r47c_flexexp_avtviso_autoslowshutter_h0_h3"]
        fx = r47c["r47_telemetry"]["flexexp_reset_split"]
        r47_meta = r47c["stage_b"]["r47"]
        self.assertEqual(r47_meta["auto_slow_shutter_default"], "On")
        self.assertEqual(fx["auto_slow_shutter_default_on_ok"], 1)
        self.assertEqual(fx["invalid_auto_slow_shutter_reject_rc"], -22)

    def test_38_round47_r47c_camera_settings_reset_restores_av_tv_iso_manual_and_auto_slow_shutter_on(self) -> None:
        data = _load_r47_summary()
        r47c = data["runs"]["r47c_flexexp_avtviso_autoslowshutter_h0_h3"]
        fx = r47c["r47_telemetry"]["flexexp_reset_split"]
        r47_meta = r47c["stage_b"]["r47"]
        self.assertTrue(r47_meta["camera_settings_reset_restores_av_tv_iso_manual"])
        self.assertTrue(r47_meta["camera_settings_reset_restores_auto_slow_shutter_on"])
        self.assertEqual(fx["cam_reset_restores_av_tv_iso_manual_ok"], 1)
        self.assertEqual(fx["cam_reset_restores_auto_slow_shutter_on_ok"], 1)

    def test_39_round47_r47c_camera_settings_reset_preserves_marker_zebra_ntscpal_while_initialize_resets_all(self) -> None:
        data = _load_r47_summary()
        fx = data["runs"]["r47c_flexexp_avtviso_autoslowshutter_h0_h3"]["r47_telemetry"]["flexexp_reset_split"]
        self.assertEqual(fx["cam_reset_preserves_marker_zebra_ntscpal_ok"], 1)
        self.assertEqual(fx["initialize_resets_all_ok"], 1)

    def test_40_round47_r47c_guest_dlopen_libjit_and_16_of_16_h0_eq_h3(self) -> None:
        data = _load_r47_summary()
        r47c = data["runs"]["r47c_flexexp_avtviso_autoslowshutter_h0_h3"]
        fx = r47c["r47_telemetry"]["flexexp_reset_split"]
        self.assertEqual(r47c["r47_telemetry"]["flexexp_reset_split_rc"], 0)
        self.assertEqual(fx["p2_write_blocked_rc"], -30)
        self.assertEqual(fx["dlopen_ok"], 1)
        self.assertEqual(fx["surfaces_verified"], 16)
        self.assertEqual(fx["surfaces_h0_eq_h3"], 16)
        self.assertEqual(fx["drift_bits"], 0)
        self.assertEqual(fx["emmc_write_count"], 0)
        self.assertEqual(fx["r47c_ok"], 1)
        self.assertFalse(r47c["gpe0_readback"]["present"])
        self.assertTrue(r47c["gpe0_readback"]["skipped_stock_fx3_mode"])

    def test_41_round47_r47c_c_source_enum_and_reset_split_constants(self) -> None:
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        for sym in (
            "R47_EXP_CTRL_PASM",
            "R47_EXP_CTRL_FLEXIBLE",
            "R47_SW_MANUAL",
            "R47_SW_AUTO",
            "R47_ASPECT_16_9",
            "R47_ASPECT_2_39_1",
        ):
            self.assertIn(sym, verify_src)

    def test_42_round47_cross_run_bridge_telemetry_matches_r47a_r47b_r47c(self) -> None:
        data = _load_r47_summary()
        ta = data["runs"]["r47a_silent_autopixelmap_5locks_big6_schinese"]["r47_telemetry"]
        r47b = data["runs"]["r47b_marker_15ratio_persist_hdmi_isolation"]["r47_telemetry"]["marker_15ratio_hdmi"]
        r47c = data["runs"]["r47c_flexexp_avtviso_autoslowshutter_h0_h3"]["r47_telemetry"]["flexexp_reset_split"]

        sab = ta["silent_autopixelmap_bridge"]
        sai = ta["silent_autopixelmap_init"]
        self.assertEqual(sab["silent_locks_shutter_type_rc"], sai["silent_locks_shutter_type_rc"])
        self.assertEqual(sab["silent_locks_interval_shutter_rc"], sai["silent_locks_interval_shutter_rc"])
        self.assertEqual(sab["silent_locks_audio_signals_rc"], sai["silent_locks_audio_signals_rc"])
        self.assertEqual(sab["silent_5disabled_verified"], sai["silent_5disabled_verified"])
        self.assertEqual(sab["pwroff_cnflasha_touches"], sai["pwroff_cnflasha_touches"])
        self.assertEqual(sab["shutter_when_pwroff_reject_rc"], sai["shutter_when_pwroff_setup_reject_rc"])
        self.assertEqual(sab["silent_autopixelmap_ok"], 1)

        mkb = ta["marker_15ratio_bridge"]
        self.assertEqual(mkb["aspect_marker_15ratios_verified"], r47b["aspect_marker_15ratios_verified"])
        self.assertEqual(mkb["marker_survives_cam_settings_reset_ok"], r47b["marker_survives_cam_settings_reset_ok"])
        self.assertEqual(mkb["hdmi_marker_overlay_px"], r47b["hdmi_marker_overlay_px"])
        self.assertEqual(mkb["marker_15ratio_hdmi_ok"], 1)

        fxb = ta["flexexp_reset_bridge"]
        self.assertEqual(fxb["exp_ctrl_2types_verified"], r47c["exp_ctrl_2types_verified"])
        self.assertEqual(fxb["av_tv_iso_8combos_verified"], r47c["av_tv_iso_8combos_verified"])
        self.assertEqual(fxb["cam_reset_restores_av_tv_iso_manual_ok"], r47c["cam_reset_restores_av_tv_iso_manual_ok"])
        self.assertEqual(fxb["cam_reset_restores_auto_slow_shutter_on_ok"], r47c["cam_reset_restores_auto_slow_shutter_on_ok"])
        self.assertEqual(fxb["flexexp_reset_split_ok"], 1)

    def test_43_round47_realhw_mechanisms_verified_top_level_completeness(self) -> None:
        data = _load_r47_summary()
        rm = data["realhw_mechanisms_verified"]
        for key in (
            "silent_mode_autopixelmap_target_5locks_and_no_pwrshutter_init",
            "silent_mode_autopixelmap_stage_b_bridge",
            "marker_15ratio_hdmi_stage_b_bridge",
            "flexexp_reset_split_stage_b_bridge",
            "marker_display_15ratio_camera_reset_persistence_and_hdmi_clean_feed_isolation",
            "exposure_ctrl_type_flexible_exp_av_tv_iso_auto_slow_shutter_reset_split_h0_h3",
        ):
            self.assertIn(key, rm)
            self.assertTrue(rm[key], f"Top-level mechanism {key} must be non-empty")

    def test_44_round47_unexecuted_physical_camera_bench_boundaries_documented(self) -> None:
        data = _load_r47_summary()
        bounds = data["unexecuted_physical_camera_bench_boundaries"]
        self.assertEqual(len(bounds), 3)
        joined = " ".join(bounds)
        for token in (
            "Silent Mode",
            "Auto Pixel Mapping",
            "Shutter When Pwr OFF",
            "Marker Display",
            "Flexible Exp. Mode",
            "unexecuted",
        ):
            self.assertIn(token, joined)

    def test_45_round47_report_readme_exists_sanitized_and_links_assets(self) -> None:
        readme_path = ROUND47_REPORT_DIR / "README.md"
        self.assertTrue(readme_path.is_file())
        txt = readme_path.read_text(encoding="utf-8")
        for forbidden in ("/Users/", "/Volumes/KAFU2T", "/private/tmp"):
            self.assertNotIn(forbidden, txt)
        for token in (
            "Round 47",
            "47th Milestone",
            "Wave-33",
            "Linux version 4.9.337-scel+",
            "r47a-silent-autopixelmap-marker-big6-schinese-alpha.png",
            "r47a-silent-autopixelmap-marker-big6-schinese-composited.png",
            "Silent Mode Settings",
            "Auto Pixel Mapping",
            "Shutter When Pwr OFF",
            "Marker Display",
            "2.39:1",
            "Flexible Exp. Mode",
            "Auto Slow Shutter",
            "16/16 H0 == H3",
            "summary.json",
        ):
            self.assertIn(token, txt)

    def test_46_round47_closure_readme_section_47_present_and_sanitized(self) -> None:
        closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")
        for forbidden in ("/Users/", "/Volumes/KAFU2T"):
            self.assertNotIn(forbidden, closure_readme)
        marker = "## 47. Round 47 (`47th Milestone` / Wave-33)"
        self.assertIn(marker, closure_readme)
        sec47 = closure_readme.split(marker, 1)[1]
        for forbidden in ("/Users/", "/Volumes/KAFU2T", "/private/tmp"):
            self.assertNotIn(forbidden, sec47)
        for token in (
            "--round 47 --r47-mode",
            "round47-silent-autopixelmap-marker-big6",
            "round47-marker-15ratio-hdmi",
            "round47-flexexp-reset-split",
            "2026-11-15-round47-realhw-silent-autopixelmap-marker-flexexp-qemu/README.md",
        ):
            self.assertIn(token, sec47)

    def test_47_round47_wave33_primary_spec_alignment(self) -> None:
        self.assertTrue(WAVE33_SPEC_PATH.is_file())
        spec_txt = WAVE33_SPEC_PATH.read_text(encoding="utf-8")
        data = _load_r47_summary()
        r47_meta = data["runs"]["r47a_silent_autopixelmap_5locks_big6_schinese"]["stage_b"]["r47"]
        for term in (
            "Silent Mode Settings",
            "Auto Pixel Mapping",
            "Aperture Drive in AF",
            "Shutter When Pwr OFF",
            "Marker Display",
            "2.39:1",
            "Flexible Exp. Mode",
            "Auto Slow Shutter",
        ):
            self.assertIn(term, spec_txt)
        self.assertEqual(r47_meta["aspect_marker_15_ratios"], self.EXPECTED_15_RATIOS)
        self.assertEqual(r47_meta["fx3_absent_menu_item"], "Shutter When Pwr OFF")

    def test_48_round47_cli_parser_accepts_all_3_r47_modes_and_rejects_unknown(self) -> None:
        runner = _load_closure_module("fx6_brr_r47_cli", "build_and_run_round.py")
        for mode in (
            "silent_autopixelmap_5locks_big6",
            "marker_15ratio_persist_hdmi_isolation",
            "flexexp_avtviso_autoslowshutter_h0_h3",
        ):
            with mock.patch.object(runner, "run_once", return_value=0) as m_run, \
                 mock.patch.object(
                     sys,
                     "argv",
                     ["build_and_run_round.py", "--run-id", "t47", "--round", "47", "--r47-mode", mode],
                 ):
                rc = runner.main()
                self.assertEqual(rc, 0)
                parsed_args = m_run.call_args[0][0]
                self.assertEqual(parsed_args.round, 47)
                self.assertEqual(parsed_args.r47_mode, mode)
                self.assertEqual(parsed_args.restore_infra70, 1)
                self.assertEqual(parsed_args.reply_all_200d, 1)

        with mock.patch.object(
            sys,
            "argv",
            ["build_and_run_round.py", "--run-id", "t47", "--round", "47", "--r47-mode", "bogus"],
        ):
            with self.assertRaises(SystemExit):
                runner.main()

    def test_49_round47_cli_default_r47_mode_is_silent_autopixelmap_5locks_big6(self) -> None:
        runner = _load_closure_module("fx6_brr_r47_clidef", "build_and_run_round.py")
        with mock.patch.object(runner, "run_once", return_value=0) as m_run, \
             mock.patch.object(
                 sys,
                 "argv",
                 ["build_and_run_round.py", "--run-id", "t47def", "--round", "47"],
             ):
            self.assertEqual(runner.main(), 0)
            self.assertEqual(m_run.call_args[0][0].r47_mode, "silent_autopixelmap_5locks_big6")

    def test_50_round47_extract_milestones_nonzero_failure_rc_propagated(self) -> None:
        runner = _load_closure_module("fx6_brr_r47_msfail", "build_and_run_round.py")
        serial = "\n".join(
            [
                "FX6_R47_MARKER_15RATIO_HDMI r47b_ok=0",
                "FX6_R47_MARKER_15RATIO_HDMI_RC=241",
                "FX6_R47_FLEXEXP_RESET_SPLIT r47c_ok=0",
                "FX6_R47_FLEXEXP_RESET_SPLIT_RC=242",
            ]
        )
        r47 = runner.extract_milestones(serial)["r47_telemetry"]
        self.assertEqual(r47["marker_15ratio_hdmi_rc"], 241)
        self.assertEqual(r47["flexexp_reset_split_rc"], 242)
        self.assertEqual(r47["marker_15ratio_hdmi"]["r47b_ok"], 0)
        self.assertEqual(r47["flexexp_reset_split"]["r47c_ok"], 0)

    def test_51_round47_no_forbidden_binaries_or_oversized_assets_in_report_dir(self) -> None:
        forbidden_exts = {".cpio", ".so", ".o", ".img", ".qcow2", ".pyc", ".raw", ".bin"}
        files = [p for p in ROUND47_REPORT_DIR.rglob("*") if p.is_file()]
        self.assertEqual(len(files), 4)
        for p in files:
            self.assertNotIn(p.suffix.lower(), forbidden_exts, f"Forbidden artifact {p}")
            if p.suffix.lower() == ".png":
                self.assertLess(p.stat().st_size, 50 * 1024, f"Oversized PNG {p}")

    def test_52_round47_prior_round46_summary_contract_untouched(self) -> None:
        r46_summary = (
            REPO_ROOT
            / "reports"
            / "2026-11-15-round46-realhw-sq-fixedvar-zebra-peaking-fullformat-qemu"
            / "summary.json"
        )
        self.assertTrue(r46_summary.is_file())
        d46 = json.loads(r46_summary.read_text(encoding="utf-8"))
        self.assertEqual(d46["round"], 46)
        self.assertEqual(d46["raw_firmware_bytes_leaked"], 0)

    def test_53_round47_prior_round44_pixelmap_consistency_with_wave33_target_override(self) -> None:
        r44_summary = (
            REPO_ROOT
            / "reports"
            / "2026-11-15-round44-realhw-pixelmap-ntscpal-gammaassist-displaylut-qemu"
            / "summary.json"
        )
        self.assertTrue(r44_summary.is_file())
        d44 = json.loads(r44_summary.read_text(encoding="utf-8"))
        self.assertEqual(d44["round"], 44)
        d47 = _load_r47_summary()
        init47 = d47["runs"]["r47a_silent_autopixelmap_5locks_big6_schinese"]["r47_telemetry"]["silent_autopixelmap_init"]
        self.assertEqual(init47["autopixelmap_not_target_retains_ok"], 1)
        self.assertEqual(init47["target_autopixelmap_suppresses_pwroff_cal_ok"], 1)

    def test_54_round47_all_3_runs_zero_crashes_and_zero_emmc_writes(self) -> None:
        data = _load_r47_summary()
        for run_key in self.EXPECTED_RUN_KEYS:
            run_obj = data["runs"][run_key]
            self.assertEqual(run_obj["round"], 47)
            self.assertEqual(run_obj["crashes"], 0)
            self.assertEqual(run_obj["emmc_write_count"], 0)
            self.assertEqual(run_obj["stage_b"]["r47"]["p2_setting_writes"], 0)
            self.assertEqual(run_obj["stage_b"]["r47"]["pwroff_cnflasha_touches"], 0)

    def test_55_round47_stage_label_and_tmp_prefix_wiring_in_runner(self) -> None:
        runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")
        self.assertIn(
            'Milestone47Wave33RealHwSilentAutoPixelMapNoPwrShutterMarker15RatioHdmiFlexExp+r47_mode={r47_mode}+lang={lang}',
            runner_src,
        )
        self.assertIn('if args.round >= 47:\n        tmp_prefix = "fx6-r47"', runner_src)

    def test_56_round47_dual_mode_clean_room_toggle_parity_on_summary_and_overlay(self) -> None:
        for clean_flag in ("0", "1"):
            with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                data = _load_r47_summary()
                self.assertEqual(data["round"], 47)
                self.assertEqual(
                    data["runs"]["r47a_silent_autopixelmap_5locks_big6_schinese"]["r47_telemetry"]["silent_autopixelmap_init"]["silent_5disabled_verified"],
                    5,
                )
                self.assertEqual(
                    data["runs"]["r47b_marker_15ratio_persist_hdmi_isolation"]["r47_telemetry"]["marker_15ratio_hdmi"]["hdmi_marker_overlay_px"],
                    0,
                )
                self.assertEqual(
                    data["runs"]["r47c_flexexp_avtviso_autoslowshutter_h0_h3"]["r47_telemetry"]["flexexp_reset_split"]["surfaces_h0_eq_h3"],
                    16,
                )


if __name__ == "__main__":
    unittest.main()
