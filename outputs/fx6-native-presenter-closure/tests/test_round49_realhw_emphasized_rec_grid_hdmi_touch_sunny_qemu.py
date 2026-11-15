#!/usr/bin/env python3
"""Offline dual-mode unit tests for FX6-on-FX3 Round 49 (49th Milestone / Wave-35 Live FX3 7.02 QEMU Rehearsal)."""
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
ROUND49_REPORT_DIR = (
    REPO_ROOT
    / "reports"
    / "2026-11-15-round49-realhw-emphasized-rec-grid-hdmi-touch-sunny-qemu"
)
WAVE35_SPEC_PATH = (
    REPO_ROOT
    / "reports"
    / "2026-11-15-global-sony-wave35-emphasized-rec-grid-hdmi-split-touch-op-reset-persist-sunny-weather-intel"
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
                sha256=hashlib.sha256(bk4),
                flash_write_allowed=False, active_byte8_selector=0, synthesized_key_count=1,
            )

    # Ensure sha256 string hex on synthesize_ram_shadow_bk4
    _FakeBmtvHex.synthesize_ram_shadow_bk4 = staticmethod(
        lambda **_kw: mock.Mock(
            bk4_bytes=b"BK4" * 16,
            total_bytes=48,
            sha256=hashlib.sha256(b"BK4" * 16).hexdigest(),
            flash_write_allowed=False,
            active_byte8_selector=0,
            synthesized_key_count=1,
        )
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


def _build_overlay_for_r49(
    runner,
    tmp_dir: pathlib.Path,
    work: pathlib.Path,
    r49_mode: str,
    lang: str = "schinese",
    enable_r49: bool = True,
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
            enable_r47=True, r47_mode="silent_autopixelmap_5locks_big6",
            enable_r48=True, r48_mode="monitor_flip_playback_big6",
            enable_r49=enable_r49, r49_mode=r49_mode,
            sd_manifest_mode="valid", lang=lang, shim_bytes=b"SHIM",
        )


def _load_r49_summary() -> dict:
    return json.loads((ROUND49_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))


class TestRound49RealHwEmphasizedRecGridHdmiTouchSunnyQemu(unittest.TestCase):
    EXPECTED_RUN_KEYS = (
        "r49a_emphasized_rec_grid_hdmi_big6_schinese",
        "r49b_touch_op_4item_reset_vault",
        "r49c_monitor_brightness_sunny_h0_h3",
    )
    EXPECTED_GRID_TYPES = [
        "Rule of 3rds Grid",
        "Square Grid",
        "Diag. + Square Grid",
    ]
    EXPECTED_TOUCH_4_ITEMS = [
        "Touch Operation",
        "Touch Sensitivity",
        "Swipe Up",
        "Touch Func. in Shooting",
    ]
    EXPECTED_TOUCH_OP_MODES = [
        "On",
        "On: Playback Only",
        "Off",
    ]
    EXPECTED_TOUCH_SENS_MODES = [
        "Standard",
        "Sensitive",
    ]
    EXPECTED_TOUCH_SHOOT_MODES = [
        "Touch Tracking",
        "Touch Focus",
        "Off",
    ]
    EXPECTED_MONITOR_BRIGHTNESS_MODES = [
        "Manual",
        "Sunny Weather",
    ]

    def test_01_round49_c_and_python_source_contracts(self) -> None:
        shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")

        self.assertIn("#if FX6_ROUND >= 49", shim_src)
        for token in (
            "FX6_R49_EMPH_REC_GRID_HDMI_BRIDGE",
            "FX6_R49_TOUCH_OP_BRIDGE",
            "FX6_R49_MONITOR_BRIGHTNESS_BRIDGE",
            "FX6_R49_LANG_TELEMETRY",
            "FX6_STAGE_B_R49_BRIDGE",
            "round49_realhw_emphasized_rec_grid_hdmi_touch_sunny=1",
        ):
            self.assertIn(token, shim_src)

        for token in (
            "r49_emph_grid_initialize_defaults",
            "r49_emph_grid_camera_settings_reset",
            "r49_eval_osd_and_hdmi_routing",
            "setup_r49_emphasized_rec_grid_hdmi_probe",
            "r49_touch_initialize_all",
            "r49_touch_camera_settings_reset",
            "r49_dispatch_capacitive_gesture",
            "run_r49_touch_op_reset_vault_probe",
            "r49_mon_bright_initialize_all",
            "r49_set_monitor_brightness",
            "r49_mon_bright_camera_settings_reset",
            "r49_apply_bench_indoor_brightness_guard",
            "run_r49_monitor_brightness_probe",
            "--r49-touch-op-reset-vault",
            "--r49-monitor-brightness-h0-h3",
            "/etc/fx6_stage_r49",
            "FX6_R49_EMPH_REC_GRID_HDMI_INIT",
            "FX6_R49_TOUCH_OP_VAULT",
            "FX6_R49_MONITOR_BRIGHTNESS",
        ):
            self.assertIn(token, verify_src)

        for token in (
            "enable_r49",
            "r49_mode",
            "--r49-mode",
            "emphasized_rec_grid_hdmi_big6",
            "touch_op_4item_reset_vault",
            "monitor_brightness_sunny_h0_h3",
            "etc/fx6_stage_r49",
            "FX6_R49_TOUCH_OP_VAULT_EXIT",
            "FX6_R49_MONITOR_BRIGHTNESS_EXIT",
            '"r49_telemetry"',
            "choices=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49]",
        ):
            self.assertIn(token, runner_src)

    def test_02_round49_native_verify_c_compiles_with_zig_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r49_verc", "build_and_run_round.py")
        if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1" and not runner.ZIG.is_file():
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertTrue(runner.ZIG.is_file(), f"Missing zig compiler at {runner.ZIG}")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            cache_dir = tmp_dir / "zig-cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            for clean_flag in ("0", "1"):
                out_bin = tmp_dir / f"fx6-stage-a-verify-r49-{clean_flag}"
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

    def test_03_round49_build_binaries_compiles_shim_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r49_shimc", "build_and_run_round.py")
        if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1" and not runner.ZIG.is_file():
            self.skipTest("Clean-room fallback without local zig binary")
        with tempfile.TemporaryDirectory() as tmp:
            for clean_flag in ("0", "1"):
                work = pathlib.Path(tmp) / f"shim_{clean_flag}"
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                    launcher_b, shim_b, meta = runner.build_binaries(
                        work,
                        fx6_round=49,
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
                self.assertIn(b"FX6_R49_EMPH_REC_GRID_HDMI_BRIDGE", shim_b)
                self.assertIn(b"FX6_R49_TOUCH_OP_BRIDGE", shim_b)
                self.assertIn(b"FX6_R49_MONITOR_BRIGHTNESS_BRIDGE", shim_b)
                self.assertGreater(meta["shim_bytes"], 10000)

    def test_04_round49_extract_milestones_r49a_emph_rec_grid_hdmi_and_stageb_bridges(self) -> None:
        runner = _load_closure_module("fx6_brr_r49_msa", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R49_EMPH_REC_GRID_HDMI_INIT emph_rec_default_on_ok=1 grid_default_off_ok=1 grid_default_rule_of_3rds_ok=1 invalid_emph_rec_reject_rc=-22 invalid_grid_type_reject_rc=-22 invalid_rec_media_hdmi_reject_rc=-22 grid_3types_verified=3 emph_rec_camreset_restores_on_ok=1 grid_types_survive_cam_reset=3 grid_survives_cam_settings_reset_ok=1 grid_reset_only_by_initialize=1 hdmi_info_on_recframe_px=24768 hdmi_info_on_grid_px=6837 hdmi_marker_zebra_peaking_px=0 hdmi_info_on_routes_recframe_and_grid_ok=1 local_lcd_blanked_when_hdmi_info_on=1 hdmi_only_forces_hdmi_info_off_ok=1 hdmi_raw_forces_hdmi_info_off_ok=1 hdmi_only_or_raw_baked_recframe_grid_pixels=0 p2_write_blocked_rc=-30 p2_sha256_match=1 cnflasha_sha256_match=1 cnflasha_writes=0 appfw_present=1 shim_present=1 emmc_write_count=0 r49_init_ok=1 verify_us=840568",
                "FX6_R49_EMPH_REC_GRID_HDMI_BRIDGE emph_rec_default_on_ok=1 emph_rec_camreset_restores_on_ok=1 grid_default_rule_of_3rds_ok=1 grid_3types_verified=3 grid_survives_cam_settings_reset_ok=1 grid_reset_only_by_initialize=1 hdmi_info_on_routes_recframe_and_grid_ok=1 local_lcd_blanked_when_hdmi_info_on=1 hdmi_only_forces_hdmi_info_off_ok=1 hdmi_raw_forces_hdmi_info_off_ok=1 hdmi_only_or_raw_baked_recframe_grid_pixels=0 emph_rec_grid_hdmi_ok=1 emmc_write_count=0 r49_bridge_ok=1",
                "FX6_R49_TOUCH_OP_BRIDGE touch_4items_verified=4 touch_op_3modes_verified=3 touch_sens_2modes_verified=2 swipe_up_default_open_fn_ok=1 touch_shoot_func_3modes_verified=3 survives_cam_settings_reset_ok=1 reset_only_by_initialize=1 bench_accidental_touch_events=0 touch_op_vault_ok=1 emmc_write_count=0 p2_setting_writes=0",
                "FX6_R49_MONITOR_BRIGHTNESS_BRIDGE monitor_bright_default_manual_0_ok=1 manual_5steps_verified=5 survives_cam_settings_reset_ok=1 reset_only_by_initialize=1 indoor_clamped_to_manual_0_ok=1 indoor_sunny_weather_unclamped=0 monitor_brightness_ok=1 cnflasha_writes=0 emmc_write_count=0",
                "FX6_STAGE_B_R49_BRIDGE round=49 faithful=1 nop_count=0 p12_wlan=1 wf12_00342260_immune=1 p10_keymap=1 p4_nd_clear=1 p11_xlr_h1=1 lang=schinese bk4_lang=0x19 enum=0x2b45_CHINESE_SIMPLIFIED font_bank=23 str_bank=19 emph_rec_grid_hdmi_clean_lock=1 touch_op_4item_camreset_vault_firewall=1 monitor_brightness_sunny_indoor_clamp=1 cnflasha_writes=0 emmc_write_count=0",
                "FX6_R49_LANG_TELEMETRY reason=gpermDrawFlush lang=schinese bk4_lang_id=0x02cf019c bk4_lang_val=0x19 gpe_fb=0 emph_rec_grid_hdmi_ok=1 touch_op_vault_ok=1 monitor_brightness_ok=1 r49_bridge_ok=1 round49_realhw_emphasized_rec_grid_hdmi_touch_sunny=1 cnflasha_writes=0 emmc_write_count=0 subst_color=0 subst_image=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        r49 = ms["r49_telemetry"]
        self.assertIsNotNone(r49)
        self.assertEqual(r49["emph_rec_grid_hdmi_init"]["hdmi_only_or_raw_baked_recframe_grid_pixels"], 0)
        self.assertEqual(r49["emph_rec_grid_hdmi_init"]["grid_3types_verified"], 3)
        self.assertEqual(r49["emph_rec_grid_hdmi_init"]["r49_init_ok"], 1)
        self.assertEqual(r49["emph_rec_grid_hdmi_bridge"]["r49_bridge_ok"], 1)
        self.assertEqual(r49["touch_op_bridge"]["touch_4items_verified"], 4)
        self.assertEqual(r49["monitor_brightness_bridge"]["manual_5steps_verified"], 5)
        self.assertEqual(r49["stage_b_bridge"]["round"], 49)
        self.assertEqual(r49["lang_telemetry"]["gpe_fb"], 0)

    def test_05_round49_extract_milestones_r49b_touch_op_vault(self) -> None:
        runner = _load_closure_module("fx6_brr_r49_msb", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R49_TOUCH_OP_VAULT touch_4defaults_ok=1 invalid_touch_op_reject_rc=-22 invalid_touch_sens_reject_rc=-22 invalid_swipe_up_reject_rc=-22 invalid_touch_shoot_reject_rc=-22 touch_4items_verified=4 touch_op_3modes_verified=3 touch_sens_2modes_verified=2 swipe_up_2modes_verified=2 touch_shoot_func_3modes_verified=3 touch_4items_survive_cam_reset=4 survives_cam_settings_reset_ok=1 initialize_restores_4defaults_ok=1 reset_only_by_initialize=1 active_touch_baseline_ok=1 playback_only_isolation_ok=1 gestures_injected=64 blocked_gestures=64 fn_menu_opened_during_vault=0 touch_tracking_during_vault=0 bench_accidental_touch_events=0 slot1_ro_kernel_rc=-30 slot1_vault_writes=0 slot1_vault_sha256_match=1 p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30 appfw_ok=1 shim_elf_ok=1 cnflasha_writes=0 emmc_write_count=0 r49b_ok=1 verify_us=928565",
                "FX6_R49_TOUCH_OP_VAULT_RC=0",
                "FX6_R49_TOUCH_OP_VAULT_EXIT rc=0 emmc_write_count=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        r49 = ms["r49_telemetry"]
        self.assertIsNotNone(r49)
        self.assertEqual(r49["touch_op_vault_rc"], 0)
        b = r49["touch_op_vault"]
        self.assertEqual(b["touch_4items_survive_cam_reset"], 4)
        self.assertEqual(b["reset_only_by_initialize"], 1)
        self.assertEqual(b["bench_accidental_touch_events"], 0)
        self.assertEqual(b["blocked_gestures"], 64)
        self.assertEqual(b["r49b_ok"], 1)

    def test_06_round49_extract_milestones_r49c_monitor_brightness(self) -> None:
        runner = _load_closure_module("fx6_brr_r49_msc", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R49_MONITOR_BRIGHTNESS monitor_bright_default_manual_0_ok=1 invalid_mode_reject_rc=-22 invalid_manual_step_reject_rc=-22 manual_5steps_verified=5 outdoor_sunny_weather_allowed_ok=1 survives_cam_settings_reset_ok=1 initialize_restores_manual_0_ok=1 reset_only_by_initialize=1 indoor_rehearsal_cycles=32 indoor_clamped_to_manual_0_ok=1 indoor_sunny_weather_unclamped=0 np_fz100_saved_mw=760 false_highlight_clip_skew_events=0 p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30 cnflasha_writes=0 dlopen_ok=1 surfaces_verified=16 surfaces_h0_eq_h3=16 drift_bits=0 emmc_write_count=0 r49c_ok=1 verify_us=176398",
                "FX6_R49_MONITOR_BRIGHTNESS_RC=0",
                "FX6_R49_MONITOR_BRIGHTNESS_EXIT rc=0 emmc_write_count=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        r49 = ms["r49_telemetry"]
        self.assertIsNotNone(r49)
        self.assertEqual(r49["monitor_brightness_rc"], 0)
        c = r49["monitor_brightness"]
        self.assertEqual(c["manual_5steps_verified"], 5)
        self.assertEqual(c["reset_only_by_initialize"], 1)
        self.assertEqual(c["indoor_sunny_weather_unclamped"], 0)
        self.assertEqual(c["surfaces_h0_eq_h3"], 16)
        self.assertEqual(c["r49c_ok"], 1)

    def test_07_round49_extract_milestones_returns_none_when_no_r49_lines(self) -> None:
        runner = _load_closure_module("fx6_brr_r49_msnone", "build_and_run_round.py")
        ms = runner.extract_milestones("Linux version 4.9.337-scel+ #1 SMP PREEMPT\n")
        self.assertIsNone(ms["r49_telemetry"])

    def test_08_round49_stage_a_overlay_r49a_emph_rec_grid_big6_mocked_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r49_ovl_a", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            for clean_flag in ("0", "1"):
                work = tmp_dir / f"r49_a_{clean_flag}"
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                    rep, add, meta = _build_overlay_for_r49(
                        runner, tmp_dir, work, "emphasized_rec_grid_hdmi_big6", lang="schinese"
                    )
                init_out = rep["init"].decode("utf-8")
                self.assertNotIn("--r49-touch-op-reset-vault", init_out)
                self.assertNotIn("--r49-monitor-brightness-h0-h3", init_out)
                self.assertIn("--sd-gate", init_out)
                self.assertIn("etc/fx6_stage_r49", add)
                self.assertIn("r49_mode=emphasized_rec_grid_hdmi_big6", add["etc/fx6_stage_r49"][0].decode("utf-8"))
                self.assertTrue(meta["r49_enabled"])
                self.assertEqual(meta["r49"]["r49_mode"], "emphasized_rec_grid_hdmi_big6")
                self.assertEqual(meta["r49"]["hdmi_only_or_raw_baked_recframe_grid_pixels"], 0)
                self.assertEqual(meta["r49"]["bench_accidental_touch_events"], 0)
                self.assertEqual(meta["r49"]["indoor_sunny_weather_unclamped"], 0)
                self.assertEqual(meta["r49"]["p2_setting_writes"], 0)

    def test_09_round49_stage_a_overlay_r49b_and_r49c_early_hooks_mocked_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r49_ovl_bc", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            for clean_flag in ("0", "1"):
                work_b = tmp_dir / f"r49_b_{clean_flag}"
                work_c = tmp_dir / f"r49_c_{clean_flag}"
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                    rep_b, _, meta_b = _build_overlay_for_r49(
                        runner, tmp_dir, work_b, "touch_op_4item_reset_vault", lang="en"
                    )
                    rep_c, _, meta_c = _build_overlay_for_r49(
                        runner, tmp_dir, work_c, "monitor_brightness_sunny_h0_h3", lang="en"
                    )
                init_b = rep_b["init"].decode("utf-8")
                init_c = rep_c["init"].decode("utf-8")
                self.assertIn("/usr/bin/fx6-stage-a-verify --r49-touch-op-reset-vault", init_b)
                self.assertIn("FX6_R49_TOUCH_OP_VAULT_EXIT", init_b)
                self.assertEqual(meta_b["r49"]["r49_mode"], "touch_op_4item_reset_vault")
                self.assertIn("/usr/bin/fx6-stage-a-verify --r49-monitor-brightness-h0-h3", init_c)
                self.assertIn("FX6_R49_MONITOR_BRIGHTNESS_EXIT", init_c)
                self.assertEqual(meta_c["r49"]["r49_mode"], "monitor_brightness_sunny_h0_h3")

    def test_10_round49_stage_a_overlay_rejects_invalid_mode_and_honors_disabled_flag(self) -> None:
        runner = _load_closure_module("fx6_brr_r49_badmode", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            with self.assertRaises(ValueError):
                _build_overlay_for_r49(
                    runner, tmp_dir, tmp_dir / "bad_r49", "invalid_r49_mode", lang="schinese"
                )
            _, add_off, meta_off = _build_overlay_for_r49(
                runner, tmp_dir, tmp_dir / "off_r49", "emphasized_rec_grid_hdmi_big6", enable_r49=False
            )
            self.assertFalse(meta_off["r49_enabled"])
            self.assertNotIn("r49", meta_off)
            self.assertNotIn("etc/fx6_stage_r49", add_off)

    def test_11_round49_summary_json_schema_sanitization_and_audit_flags(self) -> None:
        summary_path = ROUND49_REPORT_DIR / "summary.json"
        self.assertTrue(summary_path.is_file())
        raw = summary_path.read_text(encoding="utf-8")
        for forbidden in ("/Users/", "/Volumes/KAFU2T", "/private/tmp"):
            self.assertNotIn(forbidden, raw)
        data = json.loads(raw)
        self.assertEqual(
            data["schema"],
            "fx6-on-fx3-round49-realhw-emphasized-rec-grid-hdmi-touch-sunny-qemu-v1",
        )
        self.assertEqual(data["round"], 49)
        self.assertEqual(data["raw_firmware_bytes_leaked"], 0)
        self.assertIn("Linux version 4.9.337-scel+", data["kernel_version"])
        self.assertEqual(set(data["runs"].keys()), set(self.EXPECTED_RUN_KEYS))
        audit = data["r49_realhw_emphasized_rec_grid_hdmi_touch_sunny_audit"]
        self.assertEqual(audit["round"], 49)
        self.assertEqual(audit["milestone"], 49)
        self.assertEqual(audit["realhw_qemu_round_ordinal"], 21)
        self.assertEqual(audit["cumulative_realhw_qemu_runs"], 63)
        self.assertEqual(audit["total_runs"], 3)
        for k in (
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "all_3_runs_cnflasha_write_zero",
            "r49a_emphasized_rec_and_grid_hdmi_info_routing_and_clean_feed_lock_verified",
            "r49a_stageb_big6_sid_0a_over_340k_pixels_verified",
            "r49b_touch_operation_4item_camreset_survival_and_bench_tap_firewall_verified",
            "r49c_monitor_brightness_camreset_survival_and_indoor_sunny_weather_clamp_verified",
            "r49c_dlopen_libjit_and_16_h0_eq_h3_rollback_verified",
        ):
            self.assertTrue(audit[k], f"Audit flag {k} must be True")

    def test_12_round49_r49a_emphasized_rec_default_on_and_camera_settings_reset_restoration(self) -> None:
        data = _load_r49_summary()
        r49a = data["runs"]["r49a_emphasized_rec_grid_hdmi_big6_schinese"]
        ei = r49a["r49_telemetry"]["emph_rec_grid_hdmi_init"]
        r49_meta = r49a["stage_b"]["r49"]
        self.assertEqual(r49_meta["emphasized_rec_display_menu_item"], "Emphasized REC Display")
        self.assertEqual(r49_meta["emphasized_rec_display_default"], "On")
        self.assertTrue(r49_meta["emphasized_rec_display_reset_by_camera_settings_reset"])
        self.assertEqual(r49_meta["emphasized_rec_display_scope"], ["Movie", "S&Q Motion"])
        self.assertEqual(ei["emph_rec_default_on_ok"], 1)
        self.assertEqual(ei["invalid_emph_rec_reject_rc"], -22)
        self.assertEqual(ei["emph_rec_camreset_restores_on_ok"], 1)

    def test_13_round49_r49a_grid_line_3_types_survive_camera_settings_reset_cleared_only_by_initialize(self) -> None:
        data = _load_r49_summary()
        r49a = data["runs"]["r49a_emphasized_rec_grid_hdmi_big6_schinese"]
        ei = r49a["r49_telemetry"]["emph_rec_grid_hdmi_init"]
        r49_meta = r49a["stage_b"]["r49"]
        self.assertEqual(r49_meta["grid_line_display_menu_item"], "Grid Line Display")
        self.assertEqual(r49_meta["grid_line_type_menu_item"], "Grid Line Type")
        self.assertEqual(r49_meta["grid_line_3_types"], self.EXPECTED_GRID_TYPES)
        self.assertEqual(r49_meta["grid_line_type_default"], "Rule of 3rds Grid")
        self.assertTrue(r49_meta["grid_line_survives_camera_settings_reset"])
        self.assertTrue(r49_meta["grid_line_reset_only_by_initialize"])
        self.assertEqual(ei["grid_default_off_ok"], 1)
        self.assertEqual(ei["grid_default_rule_of_3rds_ok"], 1)
        self.assertEqual(ei["invalid_grid_type_reject_rc"], -22)
        self.assertEqual(ei["grid_3types_verified"], 3)
        self.assertEqual(ei["grid_types_survive_cam_reset"], 3)
        self.assertEqual(ei["grid_survives_cam_settings_reset_ok"], 1)
        self.assertEqual(ei["grid_reset_only_by_initialize"], 1)

    def test_14_round49_r49a_hdmi_info_display_on_routes_recframe_and_grid_while_blanking_local_lcd(self) -> None:
        data = _load_r49_summary()
        r49a = data["runs"]["r49a_emphasized_rec_grid_hdmi_big6_schinese"]
        ei = r49a["r49_telemetry"]["emph_rec_grid_hdmi_init"]
        r49_meta = r49a["stage_b"]["r49"]
        self.assertTrue(r49_meta["hdmi_info_display_on_routes_recframe_and_grid"])
        self.assertTrue(r49_meta["hdmi_info_display_on_blanks_local_lcd"])
        self.assertEqual(r49_meta["hdmi_marker_zebra_peaking_overlay_pixels"], 0)
        self.assertEqual(ei["hdmi_info_on_recframe_px"], 24768)
        self.assertEqual(ei["hdmi_info_on_grid_px"], 6837)
        self.assertEqual(ei["hdmi_marker_zebra_peaking_px"], 0)
        self.assertEqual(ei["hdmi_info_on_routes_recframe_and_grid_ok"], 1)
        self.assertEqual(ei["local_lcd_blanked_when_hdmi_info_on"], 1)

    def test_15_round49_r49a_off_hdmi_only_and_raw_auto_force_hdmi_info_off_clean_feed_lock(self) -> None:
        data = _load_r49_summary()
        r49a = data["runs"]["r49a_emphasized_rec_grid_hdmi_big6_schinese"]
        ei = r49a["r49_telemetry"]["emph_rec_grid_hdmi_init"]
        r49_meta = r49a["stage_b"]["r49"]
        self.assertTrue(r49_meta["rec_media_dur_hdmi_off_hdmi_only_forces_hdmi_info_off"])
        self.assertTrue(r49_meta["hdmi_raw_output_forces_hdmi_info_off"])
        self.assertEqual(r49_meta["hdmi_only_or_raw_baked_recframe_grid_pixels"], 0)
        self.assertEqual(ei["invalid_rec_media_hdmi_reject_rc"], -22)
        self.assertEqual(ei["hdmi_only_forces_hdmi_info_off_ok"], 1)
        self.assertEqual(ei["hdmi_raw_forces_hdmi_info_off_ok"], 1)
        self.assertEqual(ei["hdmi_only_or_raw_baked_recframe_grid_pixels"], 0)

    def test_16_round49_r49a_p2_and_cnflasha_ro_firewall_and_elf_presence(self) -> None:
        data = _load_r49_summary()
        ei = data["runs"]["r49a_emphasized_rec_grid_hdmi_big6_schinese"]["r49_telemetry"]["emph_rec_grid_hdmi_init"]
        self.assertEqual(ei["p2_write_blocked_rc"], -30)
        self.assertEqual(ei["p2_sha256_match"], 1)
        self.assertEqual(ei["cnflasha_sha256_match"], 1)
        self.assertEqual(ei["cnflasha_writes"], 0)
        self.assertEqual(ei["appfw_present"], 1)
        self.assertEqual(ei["shim_present"], 1)
        self.assertEqual(ei["emmc_write_count"], 0)
        self.assertEqual(ei["r49_init_ok"], 1)

    def test_17_round49_r49a_stage_b_13_sha256_locks_and_manifest_integrity(self) -> None:
        data = _load_r49_summary()
        r49a = data["runs"]["r49a_emphasized_rec_grid_hdmi_big6_schinese"]
        self.assertEqual(r49a["stage_b"]["manifest_count"], 13)
        self.assertEqual(len(r49a["stage_b"]["manifest_items"]), 13)
        seen_paths = set()
        for item in r49a["stage_b"]["manifest_items"]:
            seen_paths.add(item["guest_path"])
            self.assertEqual(len(item["sha256"]), 64)
            int(item["sha256"], 16)
        self.assertIn("/usr/lib/appFw.so", seen_paths)
        self.assertIn("/usr/lib/libgrm-fbinit9.so", seen_paths)

    def test_18_round49_r49a_big6_home_schinese_render_invariants(self) -> None:
        data = _load_r49_summary()
        r49a = data["runs"]["r49a_emphasized_rec_grid_hdmi_big6_schinese"]
        self.assertEqual(r49a["round"], 49)
        self.assertEqual(r49a["lang"], "schinese")
        self.assertEqual(r49a["r49_mode"], "emphasized_rec_grid_hdmi_big6")
        self.assertEqual(r49a["target_presenter"], "31procam_big6_menu_home_presenter")
        self.assertEqual(r49a["target_sid"], "0x0a")
        self.assertEqual(r49a["nop_count"], 0)
        self.assertEqual(r49a["crashes"], 0)
        self.assertEqual(r49a["emmc_write_count"], 0)
        self.assertGreaterEqual(r49a["total_threads_seen"], 160)
        fi = r49a["faithful_invariants"]
        self.assertEqual(fi["FX6_NATIVE_FAITHFUL"], 1)
        self.assertEqual(fi["subst_color"], 0)
        self.assertEqual(fi["subst_image"], 0)
        self.assertEqual(fi["forced_render"], 0)
        self.assertEqual(fi["skipped_node"], 0)
        self.assertEqual(fi["lock_bypass"], 0)

    def test_19_round49_r49a_gpe0_framebuffer_readback_over_340k_pixels(self) -> None:
        data = _load_r49_summary()
        gpe = data["runs"]["r49a_emphasized_rec_grid_hdmi_big6_schinese"]["gpe0_readback"]
        lt = data["runs"]["r49a_emphasized_rec_grid_hdmi_big6_schinese"]["r49_telemetry"]["lang_telemetry"]
        self.assertTrue(gpe["present"])
        self.assertEqual(gpe["bytes"], 2211840)
        self.assertEqual(gpe["total_pixels"], 552960)
        self.assertGreaterEqual(gpe["nonzero_pixels"], 346000)
        self.assertGreaterEqual(gpe["unique_colors"], 80)
        self.assertEqual(lt["gpe_fb"], 0)
        self.assertEqual(lt["font_bank"], 23)
        self.assertEqual(lt["str_bank"], 19)

    def test_20_round49_r49a_alpha_png_under_50kib_crc_and_sha256(self) -> None:
        data = _load_r49_summary()
        ap = data["runs"]["r49a_emphasized_rec_grid_hdmi_big6_schinese"]["png_exports"]["alpha_png"]
        p = REPO_ROOT / ap["path"]
        self.assertTrue(p.is_file(), f"Missing alpha PNG: {p}")
        raw = p.read_bytes()
        self.assertLess(len(raw), 50 * 1024)
        self.assertLess(len(raw), 28 * 1024)
        self.assertEqual(len(raw), ap["bytes"])
        self.assertEqual(hashlib.sha256(raw).hexdigest(), ap["sha256"])
        w, h, rows = _decode_png_rgba_rows(raw)
        self.assertEqual((w, h, len(rows)), (1024, 540, 540))

    def test_21_round49_r49a_composited_png_under_50kib_crc_and_sha256(self) -> None:
        data = _load_r49_summary()
        cp = data["runs"]["r49a_emphasized_rec_grid_hdmi_big6_schinese"]["png_exports"]["composited_png"]
        p = REPO_ROOT / cp["path"]
        self.assertTrue(p.is_file(), f"Missing composited PNG: {p}")
        raw = p.read_bytes()
        self.assertLess(len(raw), 50 * 1024)
        self.assertLess(len(raw), 28 * 1024)
        self.assertEqual(len(raw), cp["bytes"])
        self.assertEqual(hashlib.sha256(raw).hexdigest(), cp["sha256"])
        w, h, rows = _decode_png_rgba_rows(raw)
        self.assertEqual((w, h, len(rows)), (1024, 540, 540))

    def test_22_round49_r49a_alpha_vs_composited_backdrop_pixel_consistency(self) -> None:
        data = _load_r49_summary()
        exp = data["runs"]["r49a_emphasized_rec_grid_hdmi_big6_schinese"]["png_exports"]
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

    def test_23_round49_r49a_stage_b_bridge_telemetry_flags(self) -> None:
        data = _load_r49_summary()
        sb_bridge = data["runs"]["r49a_emphasized_rec_grid_hdmi_big6_schinese"]["r49_telemetry"]["stage_b_bridge"]
        lt = data["runs"]["r49a_emphasized_rec_grid_hdmi_big6_schinese"]["r49_telemetry"]["lang_telemetry"]
        self.assertEqual(sb_bridge["round"], 49)
        self.assertEqual(sb_bridge["emph_rec_grid_hdmi_clean_lock"], 1)
        self.assertEqual(sb_bridge["touch_op_4item_camreset_vault_firewall"], 1)
        self.assertEqual(sb_bridge["monitor_brightness_sunny_indoor_clamp"], 1)
        self.assertEqual(sb_bridge["cnflasha_writes"], 0)
        self.assertEqual(lt["round49_realhw_emphasized_rec_grid_hdmi_touch_sunny"], 1)
        self.assertEqual(lt["r49_bridge_ok"], 1)

    def test_24_round49_r49a_prefix_counts_include_r49_and_osd_flush(self) -> None:
        data = _load_r49_summary()
        counts = data["runs"]["r49a_emphasized_rec_grid_hdmi_big6_schinese"]["prefix_counts"]
        self.assertGreater(counts["FX6_R49_"], 100)
        self.assertGreater(counts["FX6_OSD_FLUSH"], 100)
        self.assertEqual(counts.get("APPFW_SEGV", 0), 0)
        self.assertEqual(counts.get("FX6_ABORT_", 0), 0)

    def test_25_round49_r49a_c_source_enforces_hdmi_clean_feed_clamps_and_grid_types(self) -> None:
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        self.assertIn("R49_REC_MEDIA_DUR_OFF_HDMI_ONLY", verify_src)
        self.assertIn("hdmi_raw_output_active", verify_src)
        self.assertIn('"Off(HDMI Only)"', verify_src)
        for gt in self.EXPECTED_GRID_TYPES:
            self.assertIn(f'"{gt}"', verify_src)

    def test_26_round49_r49b_touch_operation_4_items_and_enum_coverage(self) -> None:
        data = _load_r49_summary()
        r49b = data["runs"]["r49b_touch_op_4item_reset_vault"]
        tv = r49b["r49_telemetry"]["touch_op_vault"]
        r49_meta = r49b["stage_b"]["r49"]
        self.assertEqual(r49b["r49_telemetry"]["touch_op_vault_rc"], 0)
        self.assertEqual(r49_meta["touch_setup_4_items"], self.EXPECTED_TOUCH_4_ITEMS)
        self.assertEqual(r49_meta["touch_operation_3_modes"], self.EXPECTED_TOUCH_OP_MODES)
        self.assertEqual(r49_meta["touch_sensitivity_2_modes"], self.EXPECTED_TOUCH_SENS_MODES)
        self.assertEqual(r49_meta["swipe_up_default"], "Open the Fn Menu")
        self.assertEqual(r49_meta["touch_func_in_shooting_3_modes"], self.EXPECTED_TOUCH_SHOOT_MODES)
        self.assertEqual(tv["touch_4defaults_ok"], 1)
        self.assertEqual(tv["touch_4items_verified"], 4)
        self.assertEqual(tv["touch_op_3modes_verified"], 3)
        self.assertEqual(tv["touch_sens_2modes_verified"], 2)
        self.assertEqual(tv["swipe_up_2modes_verified"], 2)
        self.assertEqual(tv["touch_shoot_func_3modes_verified"], 3)

    def test_27_round49_r49b_touch_invalid_enum_rejections_return_einval(self) -> None:
        data = _load_r49_summary()
        tv = data["runs"]["r49b_touch_op_4item_reset_vault"]["r49_telemetry"]["touch_op_vault"]
        self.assertEqual(tv["invalid_touch_op_reject_rc"], -22)
        self.assertEqual(tv["invalid_touch_sens_reject_rc"], -22)
        self.assertEqual(tv["invalid_swipe_up_reject_rc"], -22)
        self.assertEqual(tv["invalid_touch_shoot_reject_rc"], -22)

    def test_28_round49_r49b_all_4_touch_items_survive_camera_settings_reset_cleared_only_by_initialize(self) -> None:
        data = _load_r49_summary()
        r49b = data["runs"]["r49b_touch_op_4item_reset_vault"]
        tv = r49b["r49_telemetry"]["touch_op_vault"]
        r49_meta = r49b["stage_b"]["r49"]
        self.assertTrue(r49_meta["touch_4_items_survive_camera_settings_reset"])
        self.assertTrue(r49_meta["touch_reset_only_by_initialize"])
        self.assertEqual(tv["touch_4items_survive_cam_reset"], 4)
        self.assertEqual(tv["survives_cam_settings_reset_ok"], 1)
        self.assertEqual(tv["initialize_restores_4defaults_ok"], 1)
        self.assertEqual(tv["reset_only_by_initialize"], 1)

    def test_29_round49_r49b_touch_operation_off_blocks_64_accidental_bench_gestures(self) -> None:
        data = _load_r49_summary()
        r49b = data["runs"]["r49b_touch_op_4item_reset_vault"]
        tv = r49b["r49_telemetry"]["touch_op_vault"]
        r49_meta = r49b["stage_b"]["r49"]
        self.assertEqual(r49_meta["bench_accidental_touch_events"], 0)
        self.assertEqual(tv["active_touch_baseline_ok"], 1)
        self.assertEqual(tv["playback_only_isolation_ok"], 1)
        self.assertEqual(tv["gestures_injected"], 64)
        self.assertEqual(tv["blocked_gestures"], 64)
        self.assertEqual(tv["fn_menu_opened_during_vault"], 0)
        self.assertEqual(tv["touch_tracking_during_vault"], 0)
        self.assertEqual(tv["bench_accidental_touch_events"], 0)

    def test_30_round49_r49b_slot1_tier0_vault_and_p2_ro_firewall(self) -> None:
        data = _load_r49_summary()
        r49b = data["runs"]["r49b_touch_op_4item_reset_vault"]
        tv = r49b["r49_telemetry"]["touch_op_vault"]
        self.assertEqual(tv["slot1_ro_kernel_rc"], -30)
        self.assertEqual(tv["slot1_vault_writes"], 0)
        self.assertEqual(tv["slot1_vault_sha256_match"], 1)
        self.assertEqual(tv["p2_write_blocked_rc"], -30)
        self.assertEqual(tv["cnflasha_ro_blocked_rc"], -30)
        self.assertEqual(tv["appfw_ok"], 1)
        self.assertEqual(tv["shim_elf_ok"], 1)
        self.assertEqual(tv["cnflasha_writes"], 0)
        self.assertEqual(tv["emmc_write_count"], 0)
        self.assertEqual(tv["r49b_ok"], 1)
        self.assertFalse(r49b["gpe0_readback"]["present"])
        self.assertTrue(r49b["gpe0_readback"]["skipped_stock_fx3_mode"])

    def test_31_round49_r49b_c_source_exact_touch_menu_labels_and_eperm_firewall(self) -> None:
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        for sym in (
            '"On: Playback Only"',
            '"Sensitive"',
            '"Open the Fn Menu"',
            '"Touch Tracking"',
            '"Touch Focus"',
            "R49_TOUCH_OP_OFF",
            "return -EPERM;",
        ):
            self.assertIn(sym, verify_src)

    def test_32_round49_r49c_monitor_brightness_manual_5_steps_and_sunny_weather_modes(self) -> None:
        data = _load_r49_summary()
        r49c = data["runs"]["r49c_monitor_brightness_sunny_h0_h3"]
        mb = r49c["r49_telemetry"]["monitor_brightness"]
        r49_meta = r49c["stage_b"]["r49"]
        self.assertEqual(r49_meta["monitor_brightness_menu_item"], "Monitor Brightness")
        self.assertEqual(r49_meta["monitor_brightness_modes"], self.EXPECTED_MONITOR_BRIGHTNESS_MODES)
        self.assertEqual(r49_meta["monitor_brightness_default_mode"], "Manual")
        self.assertEqual(r49_meta["monitor_brightness_manual_step_range"], [-2, -1, 0, 1, 2])
        self.assertEqual(r49_meta["monitor_brightness_default_step"], 0)
        self.assertEqual(mb["monitor_bright_default_manual_0_ok"], 1)
        self.assertEqual(mb["invalid_mode_reject_rc"], -22)
        self.assertEqual(mb["invalid_manual_step_reject_rc"], -22)
        self.assertEqual(mb["manual_5steps_verified"], 5)
        self.assertEqual(mb["outdoor_sunny_weather_allowed_ok"], 1)

    def test_33_round49_r49c_monitor_brightness_survives_camera_settings_reset_cleared_only_by_initialize(self) -> None:
        data = _load_r49_summary()
        r49c = data["runs"]["r49c_monitor_brightness_sunny_h0_h3"]
        mb = r49c["r49_telemetry"]["monitor_brightness"]
        r49_meta = r49c["stage_b"]["r49"]
        self.assertTrue(r49_meta["monitor_brightness_survives_camera_settings_reset"])
        self.assertTrue(r49_meta["monitor_brightness_reset_only_by_initialize"])
        self.assertEqual(mb["survives_cam_settings_reset_ok"], 1)
        self.assertEqual(mb["initialize_restores_manual_0_ok"], 1)
        self.assertEqual(mb["reset_only_by_initialize"], 1)

    def test_34_round49_r49c_indoor_bench_guard_clamps_sunny_weather_to_manual_0_and_saves_np_fz100_power(self) -> None:
        data = _load_r49_summary()
        r49c = data["runs"]["r49c_monitor_brightness_sunny_h0_h3"]
        mb = r49c["r49_telemetry"]["monitor_brightness"]
        r49_meta = r49c["stage_b"]["r49"]
        self.assertTrue(r49_meta["indoor_sunny_weather_clamped_to_manual_0"])
        self.assertEqual(r49_meta["indoor_sunny_weather_unclamped"], 0)
        self.assertEqual(mb["indoor_rehearsal_cycles"], 32)
        self.assertEqual(mb["indoor_clamped_to_manual_0_ok"], 1)
        self.assertEqual(mb["indoor_sunny_weather_unclamped"], 0)
        self.assertEqual(mb["np_fz100_saved_mw"], 760)
        self.assertEqual(mb["false_highlight_clip_skew_events"], 0)

    def test_35_round49_r49c_guest_dlopen_libjit_and_16_of_16_h0_eq_h3(self) -> None:
        data = _load_r49_summary()
        r49c = data["runs"]["r49c_monitor_brightness_sunny_h0_h3"]
        mb = r49c["r49_telemetry"]["monitor_brightness"]
        self.assertEqual(r49c["r49_telemetry"]["monitor_brightness_rc"], 0)
        self.assertEqual(mb["p2_write_blocked_rc"], -30)
        self.assertEqual(mb["cnflasha_ro_blocked_rc"], -30)
        self.assertEqual(mb["cnflasha_writes"], 0)
        self.assertEqual(mb["dlopen_ok"], 1)
        self.assertEqual(mb["surfaces_verified"], 16)
        self.assertEqual(mb["surfaces_h0_eq_h3"], 16)
        self.assertEqual(mb["drift_bits"], 0)
        self.assertEqual(mb["emmc_write_count"], 0)
        self.assertEqual(mb["r49c_ok"], 1)
        self.assertFalse(r49c["gpe0_readback"]["present"])
        self.assertTrue(r49c["gpe0_readback"]["skipped_stock_fx3_mode"])

    def test_36_round49_r49c_c_source_exact_monitor_brightness_strings_and_step_bounds(self) -> None:
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        for sym in (
            '"Manual"',
            '"Sunny Weather"',
            "manual_step < -2 || manual_step > 2",
            "R49_ENV_INDOOR_BENCH_GUARDED",
            "panel_mw = 1380U",
            "panel_mw = 620U",
        ):
            self.assertIn(sym, verify_src)

    def test_37_round49_cross_run_bridge_telemetry_matches_r49a_r49b_r49c(self) -> None:
        data = _load_r49_summary()
        ta = data["runs"]["r49a_emphasized_rec_grid_hdmi_big6_schinese"]["r49_telemetry"]
        r49b = data["runs"]["r49b_touch_op_4item_reset_vault"]["r49_telemetry"]["touch_op_vault"]
        r49c = data["runs"]["r49c_monitor_brightness_sunny_h0_h3"]["r49_telemetry"]["monitor_brightness"]

        eb = ta["emph_rec_grid_hdmi_bridge"]
        ei = ta["emph_rec_grid_hdmi_init"]
        self.assertEqual(eb["grid_3types_verified"], ei["grid_3types_verified"])
        self.assertEqual(eb["grid_reset_only_by_initialize"], ei["grid_reset_only_by_initialize"])
        self.assertEqual(
            eb["hdmi_only_or_raw_baked_recframe_grid_pixels"],
            ei["hdmi_only_or_raw_baked_recframe_grid_pixels"],
        )
        self.assertEqual(eb["emph_rec_grid_hdmi_ok"], 1)

        tb = ta["touch_op_bridge"]
        self.assertEqual(tb["touch_4items_verified"], r49b["touch_4items_verified"])
        self.assertEqual(tb["reset_only_by_initialize"], r49b["reset_only_by_initialize"])
        self.assertEqual(tb["bench_accidental_touch_events"], r49b["bench_accidental_touch_events"])
        self.assertEqual(tb["touch_op_vault_ok"], 1)

        mbb = ta["monitor_brightness_bridge"]
        self.assertEqual(mbb["manual_5steps_verified"], r49c["manual_5steps_verified"])
        self.assertEqual(mbb["reset_only_by_initialize"], r49c["reset_only_by_initialize"])
        self.assertEqual(mbb["indoor_sunny_weather_unclamped"], r49c["indoor_sunny_weather_unclamped"])
        self.assertEqual(mbb["monitor_brightness_ok"], 1)

    def test_38_round49_realhw_mechanisms_verified_top_level_completeness(self) -> None:
        data = _load_r49_summary()
        rm = data["realhw_mechanisms_verified"]
        for key in (
            "emphasized_rec_display_and_grid_line_display_hdmi_routing_vs_hdmi_only_raw_clean_feed_init",
            "emphasized_rec_and_grid_hdmi_stage_b_bridge",
            "touch_operation_stage_b_bridge",
            "monitor_brightness_stage_b_bridge",
            "touch_operation_4item_cam_settings_reset_survival_and_unattended_bench_tap_firewall",
            "monitor_brightness_manual_5step_vs_sunny_weather_indoor_clamp_and_16_h0_h3",
        ):
            self.assertIn(key, rm)
            self.assertTrue(rm[key], f"Top-level mechanism {key} must be non-empty")

    def test_39_round49_unexecuted_physical_camera_bench_boundaries_documented(self) -> None:
        data = _load_r49_summary()
        bounds = data["unexecuted_physical_camera_bench_boundaries"]
        self.assertEqual(len(bounds), 3)
        joined = " ".join(bounds)
        for token in (
            "Emphasized REC Display",
            "Grid Line Display",
            "Off(HDMI Only)",
            "Touch Operation",
            "Camera Settings Reset",
            "Monitor Brightness",
            "Sunny Weather",
            "NP-FZ100",
            "unexecuted",
        ):
            self.assertIn(token, joined)

    def test_40_round49_report_readme_exists_sanitized_and_links_assets(self) -> None:
        readme_path = ROUND49_REPORT_DIR / "README.md"
        self.assertTrue(readme_path.is_file())
        txt = readme_path.read_text(encoding="utf-8")
        for forbidden in ("/Users/", "/Volumes/KAFU2T", "/private/tmp"):
            self.assertNotIn(forbidden, txt)
        for token in (
            "Round 49",
            "49th Milestone",
            "Wave-35",
            "Linux version 4.9.337-scel+",
            "r49a-emphasized-rec-grid-hdmi-big6-schinese-alpha.png",
            "r49a-emphasized-rec-grid-hdmi-big6-schinese-composited.png",
            "Emphasized REC Display",
            "Grid Line Display",
            "Off(HDMI Only)",
            "Touch Operation",
            "Monitor Brightness",
            "Sunny Weather",
            "16/16 H0 == H3",
            "summary.json",
        ):
            self.assertIn(token, txt)

    def test_41_round49_wave35_primary_spec_alignment(self) -> None:
        self.assertTrue(WAVE35_SPEC_PATH.is_file())
        spec_txt = WAVE35_SPEC_PATH.read_text(encoding="utf-8")
        data = _load_r49_summary()
        r49_meta = data["runs"]["r49a_emphasized_rec_grid_hdmi_big6_schinese"]["stage_b"]["r49"]
        for term in (
            "Emphasized REC Display",
            "Grid Line Display",
            "Rule of 3rds Grid",
            "Square Grid",
            "Diag. + Square Grid",
            "Off(HDMI Only)",
            "HDMI Info. Display",
            "Touch Operation",
            "Touch Sensitivity",
            "Swipe Up",
            "Touch Func. in Shooting",
            "Monitor Brightness",
            "Sunny Weather",
        ):
            self.assertIn(term, spec_txt)
        self.assertEqual(r49_meta["grid_line_3_types"], self.EXPECTED_GRID_TYPES)
        self.assertEqual(r49_meta["touch_setup_4_items"], self.EXPECTED_TOUCH_4_ITEMS)
        self.assertEqual(r49_meta["monitor_brightness_modes"], self.EXPECTED_MONITOR_BRIGHTNESS_MODES)

    def test_42_round49_cli_parser_accepts_all_3_r49_modes_and_rejects_unknown(self) -> None:
        runner = _load_closure_module("fx6_brr_r49_cli", "build_and_run_round.py")
        for mode in (
            "emphasized_rec_grid_hdmi_big6",
            "touch_op_4item_reset_vault",
            "monitor_brightness_sunny_h0_h3",
        ):
            with mock.patch.object(runner, "run_once", return_value=0) as m_run, \
                 mock.patch.object(
                     sys,
                     "argv",
                     ["build_and_run_round.py", "--run-id", "t49", "--round", "49", "--r49-mode", mode],
                 ):
                rc = runner.main()
                self.assertEqual(rc, 0)
                parsed_args = m_run.call_args[0][0]
                self.assertEqual(parsed_args.round, 49)
                self.assertEqual(parsed_args.r49_mode, mode)
                self.assertEqual(parsed_args.restore_infra70, 1)
                self.assertEqual(parsed_args.reply_all_200d, 1)

        with mock.patch.object(
            sys,
            "argv",
            ["build_and_run_round.py", "--run-id", "t49", "--round", "49", "--r49-mode", "bogus"],
        ):
            with self.assertRaises(SystemExit):
                runner.main()

    def test_43_round49_cli_default_r49_mode_is_emphasized_rec_grid_hdmi_big6(self) -> None:
        runner = _load_closure_module("fx6_brr_r49_clidef", "build_and_run_round.py")
        with mock.patch.object(runner, "run_once", return_value=0) as m_run, \
             mock.patch.object(
                 sys,
                 "argv",
                 ["build_and_run_round.py", "--run-id", "t49def", "--round", "49"],
             ):
            self.assertEqual(runner.main(), 0)
            self.assertEqual(m_run.call_args[0][0].r49_mode, "emphasized_rec_grid_hdmi_big6")

    def test_44_round49_extract_milestones_nonzero_failure_rc_propagated(self) -> None:
        runner = _load_closure_module("fx6_brr_r49_msfail", "build_and_run_round.py")
        serial = "\n".join(
            [
                "FX6_R49_TOUCH_OP_VAULT r49b_ok=0",
                "FX6_R49_TOUCH_OP_VAULT_RC=245",
                "FX6_R49_MONITOR_BRIGHTNESS r49c_ok=0",
                "FX6_R49_MONITOR_BRIGHTNESS_RC=246",
            ]
        )
        r49 = runner.extract_milestones(serial)["r49_telemetry"]
        self.assertEqual(r49["touch_op_vault_rc"], 245)
        self.assertEqual(r49["monitor_brightness_rc"], 246)
        self.assertEqual(r49["touch_op_vault"]["r49b_ok"], 0)
        self.assertEqual(r49["monitor_brightness"]["r49c_ok"], 0)

    def test_45_round49_no_forbidden_binaries_or_oversized_assets_in_report_dir(self) -> None:
        forbidden_exts = {".cpio", ".so", ".o", ".img", ".qcow2", ".pyc", ".raw", ".bin"}
        files = [p for p in ROUND49_REPORT_DIR.rglob("*") if p.is_file()]
        self.assertEqual(len(files), 4)
        for p in files:
            self.assertNotIn(p.suffix.lower(), forbidden_exts, f"Forbidden artifact {p}")
            if p.suffix.lower() == ".png":
                self.assertLess(p.stat().st_size, 50 * 1024, f"Oversized PNG {p}")

    def test_46_round49_prior_round48_summary_contract_untouched(self) -> None:
        r48_summary = (
            REPO_ROOT
            / "reports"
            / "2026-11-15-round48-realhw-recover-imagedb-monitor-flip-af-sens-qemu"
            / "summary.json"
        )
        self.assertTrue(r48_summary.is_file())
        d48 = json.loads(r48_summary.read_text(encoding="utf-8"))
        self.assertEqual(d48["round"], 48)
        self.assertEqual(d48["raw_firmware_bytes_leaked"], 0)

    def test_47_round49_prior_round47_marker_hdmi_isolation_contrasted_with_r49a_recframe_grid_routing(self) -> None:
        r47_summary = (
            REPO_ROOT
            / "reports"
            / "2026-11-15-round47-realhw-silent-autopixelmap-marker-flexexp-qemu"
            / "summary.json"
        )
        self.assertTrue(r47_summary.is_file())
        d47 = json.loads(r47_summary.read_text(encoding="utf-8"))
        self.assertEqual(d47["round"], 47)
        d49 = _load_r49_summary()
        ei = d49["runs"]["r49a_emphasized_rec_grid_hdmi_big6_schinese"]["r49_telemetry"]["emph_rec_grid_hdmi_init"]
        self.assertEqual(ei["hdmi_marker_zebra_peaking_px"], 0)
        self.assertGreater(ei["hdmi_info_on_recframe_px"], 0)
        self.assertGreater(ei["hdmi_info_on_grid_px"], 0)

    def test_48_round49_prior_round46_zebra_peaking_hdmi_isolation_consistent_with_r49a(self) -> None:
        r46_summary = (
            REPO_ROOT
            / "reports"
            / "2026-11-15-round46-realhw-sq-fixedvar-zebra-peaking-fullformat-qemu"
            / "summary.json"
        )
        self.assertTrue(r46_summary.is_file())
        d46 = json.loads(r46_summary.read_text(encoding="utf-8"))
        self.assertEqual(d46["round"], 46)
        d49 = _load_r49_summary()
        ei = d49["runs"]["r49a_emphasized_rec_grid_hdmi_big6_schinese"]["r49_telemetry"]["emph_rec_grid_hdmi_init"]
        self.assertEqual(ei["hdmi_only_or_raw_baked_recframe_grid_pixels"], 0)

    def test_49_round49_all_3_runs_zero_crashes_zero_emmc_and_zero_cnflasha_writes(self) -> None:
        data = _load_r49_summary()
        for run_key in self.EXPECTED_RUN_KEYS:
            run_obj = data["runs"][run_key]
            self.assertEqual(run_obj["round"], 49)
            self.assertEqual(run_obj["crashes"], 0)
            self.assertEqual(run_obj["emmc_write_count"], 0)
            self.assertEqual(run_obj["stage_b"]["r49"]["p2_setting_writes"], 0)
            self.assertEqual(run_obj["stage_b"]["r49"]["cnflasha_writes"], 0)
            self.assertEqual(run_obj["stage_b"]["r49"]["slot1_vault_writes"], 0)

    def test_50_round49_stage_label_and_tmp_prefix_wiring_in_runner(self) -> None:
        runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")
        self.assertIn(
            "Milestone49Wave35RealHwEmphasizedRecGridHdmiTouchOpSunnyWeather+r49_mode={r49_mode}+lang={lang}",
            runner_src,
        )
        self.assertIn('if args.round >= 49:\n        tmp_prefix = "fx6-r49"', runner_src)

    def test_51_round49_dual_mode_clean_room_toggle_parity_on_summary(self) -> None:
        for clean_flag in ("0", "1"):
            with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                data = _load_r49_summary()
                self.assertEqual(data["round"], 49)
                self.assertEqual(
                    data["runs"]["r49a_emphasized_rec_grid_hdmi_big6_schinese"]["r49_telemetry"]["emph_rec_grid_hdmi_init"]["hdmi_only_or_raw_baked_recframe_grid_pixels"],
                    0,
                )
                self.assertEqual(
                    data["runs"]["r49b_touch_op_4item_reset_vault"]["r49_telemetry"]["touch_op_vault"]["bench_accidental_touch_events"],
                    0,
                )
                self.assertEqual(
                    data["runs"]["r49c_monitor_brightness_sunny_h0_h3"]["r49_telemetry"]["monitor_brightness"]["surfaces_h0_eq_h3"],
                    16,
                )

    def test_52_round49_21st_realhw_qemu_round_milestone_63_live_runs_continuity(self) -> None:
        for r in range(28, 50):
            matches = list((REPO_ROOT / "reports").glob(f"*round{r}-*"))
            self.assertTrue(matches, f"Missing live QEMU report directory for Round {r}")
        data = _load_r49_summary()
        audit = data["r49_realhw_emphasized_rec_grid_hdmi_touch_sunny_audit"]
        self.assertEqual(audit["realhw_qemu_round_ordinal"], 21)
        self.assertEqual(audit["cumulative_realhw_qemu_runs"], 63)

    def test_53_round49_r49a_verify_us_positive_under_2_seconds(self) -> None:
        data = _load_r49_summary()
        us = data["runs"]["r49a_emphasized_rec_grid_hdmi_big6_schinese"]["r49_telemetry"]["emph_rec_grid_hdmi_init"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_54_round49_r49b_verify_us_positive_under_2_seconds(self) -> None:
        data = _load_r49_summary()
        us = data["runs"]["r49b_touch_op_4item_reset_vault"]["r49_telemetry"]["touch_op_vault"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_55_round49_r49c_verify_us_positive_under_2_seconds(self) -> None:
        data = _load_r49_summary()
        us = data["runs"]["r49c_monitor_brightness_sunny_h0_h3"]["r49_telemetry"]["monitor_brightness"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_56_round49_r49a_stage_b_manifest_matches_r49b_and_r49c_non_shim_digests(self) -> None:
        data = _load_r49_summary()
        ma = {x["guest_path"]: x["sha256"] for x in data["runs"]["r49a_emphasized_rec_grid_hdmi_big6_schinese"]["stage_b"]["manifest_items"]}
        mb = {x["guest_path"]: x["sha256"] for x in data["runs"]["r49b_touch_op_4item_reset_vault"]["stage_b"]["manifest_items"]}
        mc = {x["guest_path"]: x["sha256"] for x in data["runs"]["r49c_monitor_brightness_sunny_h0_h3"]["stage_b"]["manifest_items"]}
        for gpath in (
            "/usr/lib/appFw.so",
            "/usr/lib/libfan.so",
            "/usr/kmod/upm.ko",
            "/usr/lib/libWlanResource.so",
        ):
            self.assertEqual(ma[gpath], mb[gpath])
            self.assertEqual(mb[gpath], mc[gpath])

    def test_57_round49_r49a_top_colors_include_transparent_and_dark_ui_surfaces(self) -> None:
        data = _load_r49_summary()
        top = data["runs"]["r49a_emphasized_rec_grid_hdmi_big6_schinese"]["gpe0_readback"]["top_colors"]
        self.assertGreaterEqual(len(top), 5)
        argbs = {row["argb"] for row in top}
        self.assertIn("0x00000000", argbs)
        self.assertIn("0xff000000", argbs)

    def test_58_round49_r49a_wall_elapsed_and_duration_budget_sanity(self) -> None:
        data = _load_r49_summary()
        r49a = data["runs"]["r49a_emphasized_rec_grid_hdmi_big6_schinese"]
        self.assertEqual(r49a["duration_budget_sec"], 71)
        self.assertGreater(r49a["wall_elapsed_sec"], 50.0)
        self.assertLess(r49a["wall_elapsed_sec"], 120.0)

    def test_59_round49_r49b_and_r49c_fast_early_exit_wall_elapsed_under_20s(self) -> None:
        data = _load_r49_summary()
        r49b = data["runs"]["r49b_touch_op_4item_reset_vault"]
        r49c = data["runs"]["r49c_monitor_brightness_sunny_h0_h3"]
        self.assertEqual(r49b["duration_budget_sec"], 35)
        self.assertEqual(r49c["duration_budget_sec"], 35)
        self.assertGreater(r49b["wall_elapsed_sec"], 1.0)
        self.assertLess(r49b["wall_elapsed_sec"], 20.0)
        self.assertGreater(r49c["wall_elapsed_sec"], 1.0)
        self.assertLess(r49c["wall_elapsed_sec"], 20.0)

    def test_60_round49_shim_round48_backward_compat_preserved_when_built_for_round48(self) -> None:
        runner = _load_closure_module("fx6_brr_r49_r48compat", "build_and_run_round.py")
        if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1" and not runner.ZIG.is_file():
            self.skipTest("Clean-room fallback without local zig binary")
        with tempfile.TemporaryDirectory() as tmp:
            _, shim_r48, _ = runner.build_binaries(
                pathlib.Path(tmp) / "r48_compat",
                fx6_round=48,
                restore_infra70=1,
                restore_all_early=0,
                reply_all_200d=1,
                initial_setting_done=1,
                key_seq="0x7028:120:5500",
                key_settle_ms=1500,
                lang="schinese",
            )
            self.assertIn(b"FX6_R48_MONITOR_FLIP_BRIDGE", shim_r48)
            self.assertNotIn(b"FX6_R49_EMPH_REC_GRID_HDMI_BRIDGE", shim_r48)


if __name__ == "__main__":
    unittest.main()
