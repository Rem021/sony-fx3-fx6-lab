#!/usr/bin/env python3
"""Offline dual-mode unit tests for FX6-on-FX3 Round 46 (46th Milestone / Wave-32 Live FX3 7.02 QEMU Rehearsal)."""
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
ROUND46_REPORT_DIR = (
    REPO_ROOT
    / "reports"
    / "2026-11-15-round46-realhw-sq-fixedvar-zebra-peaking-fullformat-qemu"
)
WAVE32_SPEC_PATH = (
    REPO_ROOT
    / "reports"
    / "2026-11-15-global-sony-wave32-sq-fixed-variable-fps-zebra-peaking-hdmi-isolation-full-format-chord-intel"
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


def _build_overlay_for_r46(
    runner,
    tmp_dir: pathlib.Path,
    work: pathlib.Path,
    r46_mode: str,
    lang: str = "schinese",
    enable_r46: bool = True,
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
            enable_r46=enable_r46, r46_mode=r46_mode,
            sd_manifest_mode="valid", lang=lang, shim_bytes=b"SHIM",
        )


def _load_r46_summary() -> dict:
    return json.loads((ROUND46_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))


class TestRound46RealHwSqFixedVarZebraPeakingFullFormat(unittest.TestCase):
    EXPECTED_RUN_KEYS = (
        "r46a_sq_fixedvar_6locks_big6_schinese",
        "r46b_zebra_persist_peaking_hdmi_isolation",
        "r46c_slot1_fullformat_chord_vault_h0_h3",
    )

    def test_01_round46_c_and_python_source_contracts(self) -> None:
        shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")

        self.assertIn("#if FX6_ROUND >= 46", shim_src)
        for token in (
            "FX6_R46_SQ_FIXEDVAR_BRIDGE",
            "FX6_R46_ZEBRA_PEAKING_BRIDGE",
            "FX6_R46_FULLFORMAT_VAULT_BRIDGE",
            "FX6_R46_LANG_TELEMETRY",
            "FX6_STAGE_B_R46_BRIDGE",
            "round46_realhw_sq_fixedvar_zebra_peaking_fullformat=1",
        ):
            self.assertIn(token, shim_src)

        for token in (
            "r46_set_mode_settings",
            "r46_open_legacy_sq_settings_menu",
            "r46_set_direct_fps_home",
            "r46_enable_audio_capture_channels",
            "r46_set_audio_out_timing",
            "r46_set_tc_run",
            "r46_set_tc_output",
            "r46_set_proxy_recording",
            "setup_r46_sq_fixedvar_6locks_probe",
            "r46_assist_initialize_defaults",
            "r46_camera_settings_reset",
            "r46_wheel_left_toggle_zebra",
            "r46_set_zebra_display",
            "r46_set_zebra_preset",
            "r46_set_zebra_custom1_std_range",
            "r46_set_zebra_custom2_lower_limit",
            "r46_set_peaking_config",
            "r46_render_lcd_vs_hdmi_assist_planes",
            "run_r46_zebra_peaking_hdmi_probe",
            "r46_slot1_vault_firewall_check",
            "r46_open_format_dialog",
            "r46_dialog_press_delete_key_toggle",
            "r46_execute_slot_format",
            "r46_shooting_menu_plus_delete_chord",
            "run_r46_fullformat_chord_vault_probe",
            "--r46-zebra-peaking-hdmi",
            "--r46-fullformat-chord-vault",
            "/etc/fx6_stage_r46",
            "FX6_R46_SQ_FIXEDVAR_INIT",
            "FX6_R46_ZEBRA_PEAKING_HDMI",
            "FX6_R46_FULLFORMAT_CHORD_VAULT",
        ):
            self.assertIn(token, verify_src)

        for token in (
            "enable_r46",
            "r46_mode",
            "--r46-mode",
            "sq_fixedvar_6locks_big6",
            "zebra_persist_peaking_hdmi_isolation",
            "slot1_fullformat_chord_vault_h0_h3",
            "etc/fx6_stage_r46",
            "FX6_R46_ZEBRA_PEAKING_HDMI_EXIT",
            "FX6_R46_FULLFORMAT_CHORD_VAULT_EXIT",
            '"r46_telemetry"',
            "choices=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47]",
        ):
            self.assertIn(token, runner_src)

    def test_02_round46_native_verify_c_compiles_with_zig_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r46_verc", "build_and_run_round.py")
        if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1" and not runner.ZIG.is_file():
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertTrue(runner.ZIG.is_file(), f"Missing zig compiler at {runner.ZIG}")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            cache_dir = tmp_dir / "zig-cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            for clean_flag in ("0", "1"):
                out_bin = tmp_dir / f"fx6-stage-a-verify-r46-{clean_flag}"
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

    def test_03_round46_build_binaries_compiles_shim_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r46_shimc", "build_and_run_round.py")
        if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1" and not runner.ZIG.is_file():
            self.skipTest("Clean-room fallback without local zig binary")
        with tempfile.TemporaryDirectory() as tmp:
            for clean_flag in ("0", "1"):
                work = pathlib.Path(tmp) / f"shim_{clean_flag}"
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                    launcher_b, shim_b, meta = runner.build_binaries(
                        work,
                        fx6_round=46,
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
                self.assertIn(b"FX6_R46_SQ_FIXEDVAR_BRIDGE", shim_b)
                self.assertIn(b"FX6_R46_ZEBRA_PEAKING_BRIDGE", shim_b)
                self.assertIn(b"FX6_R46_FULLFORMAT_VAULT_BRIDGE", shim_b)
                self.assertGreater(meta["shim_bytes"], 10000)

    def test_04_round46_extract_milestones_r46a_sq_fixedvar_and_bridges(self) -> None:
        runner = _load_closure_module("fx6_brr_r46_msa", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R46_SQ_FIXEDVAR_INIT fixed_variable_locks_sq_settings_rc=-16 legacy_sq_settings_unlocked_ok=1 invalid_mode_settings_reject_rc=-22 direct_fps_home_control_ok=1 codec_follows_movie_settings_ok=1 sq_6locks_verified=6 sq_audio_channels=0 sq_audio_rec_reject_rc=-95 normal_audio_out_timing_2modes_ok=2 invalid_audio_timing_reject_rc=-22 sq_audio_out_timing_reject_rc=-95 sq_tc_run_reject_rc=-95 sq_tc_output_reject_rc=-95 sq_240_200_4k_blocked=4 sq_240_200_hd_allowed=2 sq_240_200_4k_reject_rc=-22 sq_120_100_dci4k_blocked=2 sq_120_100_uhd4k_allowed=3 sq_120_100_dci4k_reject_rc=-22 sq_proxy_le60_allowed=1 sq_proxy_rec119_100_blocked=2 sq_proxy_fps_ge100_blocked=4 sq_proxy_cutoff_reject_rc=-22 p2_write_blocked_rc=-30 p2_sha256_match=1 appfw_present=1 shim_present=1 emmc_write_count=0 r46_init_ok=1 verify_us=705830",
                "FX6_R46_SQ_FIXEDVAR_BRIDGE fixed_variable_locks_sq_settings_rc=-16 direct_fps_home_control_ok=1 sq_6locks_verified=6 sq_audio_channels=0 sq_audio_out_timing_reject_rc=-95 sq_tc_run_output_reject_rc=-95 sq_240_200_4k_blocked=4 sq_120_100_dci4k_blocked=2 sq_proxy_rec119_100_blocked=2 sq_proxy_fps_ge100_blocked=4 sq_proxy_cutoff_reject_rc=-22 sq_fixedvar_ok=1 emmc_write_count=0 r46_bridge_ok=1",
                "FX6_R46_ZEBRA_PEAKING_BRIDGE wheel_left_zebra_select_ok=1 zebra_8presets_verified=8 zebra_custom1_std_range_ok=1 zebra_custom2_lower_limit_ok=1 zebra_survives_cam_settings_reset_ok=1 initialize_resets_zebra_off_70_ok=1 peaking_3levels_verified=3 peaking_4colors_verified=4 hdmi_info_display_on=1 hdmi_zebra_overlay_px=0 hdmi_peaking_overlay_px=0 zebra_peaking_hdmi_ok=1 emmc_write_count=0 p2_setting_writes=0",
                "FX6_R46_FULLFORMAT_VAULT_BRIDGE delete_key_toggles_full_format_ok=1 mid_cancel_erases_data_card_usable_ok=1 slot1_vault_quick_format_reject_rc=-16 slot1_vault_full_format_reject_rc=-16 slot1_vault_wp_format_reject_rc=-13 slot1_chord_2000ms_vault_reject_rc=-16 slot1_chord_2000ms_wp_reject_rc=-13 slot1_format_writes=0 fullformat_vault_ok=1 emmc_write_count=0",
                "FX6_STAGE_B_R46_BRIDGE round=46 faithful=1 nop_count=0 p12_wlan=1 wf12_00342260_immune=1 p10_keymap=1 p4_nd_clear=1 p11_xlr_h1=1 lang=schinese bk4_lang=0x19 enum=0x2b45_CHINESE_SIMPLIFIED font_bank=23 str_bank=19 sq_fixedvar_6locks=1 zebra_camreset_peaking_hdmi_zero=1 slot1_fullformat_chord_vault_firewall=1 emmc_write_count=0",
                "FX6_R46_LANG_TELEMETRY reason=gpermDrawFlush lang=schinese bk4_lang_id=0x02cf019c bk4_lang_val=0x19 gpe_fb=0 sq_fixedvar_ok=1 zebra_peaking_hdmi_ok=1 fullformat_vault_ok=1 r46_bridge_ok=1 round46_realhw_sq_fixedvar_zebra_peaking_fullformat=1 emmc_write_count=0 subst_color=0 subst_image=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        r46 = ms["r46_telemetry"]
        self.assertIsNotNone(r46)
        self.assertEqual(r46["sq_fixedvar_init"]["fixed_variable_locks_sq_settings_rc"], -16)
        self.assertEqual(r46["sq_fixedvar_init"]["sq_6locks_verified"], 6)
        self.assertEqual(r46["sq_fixedvar_init"]["r46_init_ok"], 1)
        self.assertEqual(r46["sq_fixedvar_bridge"]["r46_bridge_ok"], 1)
        self.assertEqual(r46["zebra_peaking_bridge"]["hdmi_zebra_overlay_px"], 0)
        self.assertEqual(r46["fullformat_vault_bridge"]["slot1_format_writes"], 0)
        self.assertEqual(r46["stage_b_bridge"]["round"], 46)
        self.assertEqual(r46["lang_telemetry"]["gpe_fb"], 0)

    def test_05_round46_extract_milestones_r46b_zebra_peaking_hdmi(self) -> None:
        runner = _load_closure_module("fx6_brr_r46_msb", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R46_ZEBRA_PEAKING_HDMI zebra_defaults_off_70_ok=1 wheel_left_zebra_select_ok=1 invalid_zebra_disp_reject_rc=-22 zebra_8presets_verified=8 invalid_zebra_level_reject_rc=-22 zebra_custom1_std_range_ok=1 zebra_custom2_lower_limit_ok=1 zebra_survives_cam_settings_reset_ok=1 initialize_resets_zebra_off_70_ok=1 peaking_defaults_off_mid_white_ok=1 invalid_peaking_reject_rc=-22 peaking_3levels_verified=3 peaking_4colors_verified=4 hdmi_info_display_on=1 lcd_zebra_overlay_px=20736 lcd_peaking_overlay_px=12992 hdmi_zebra_overlay_px=0 hdmi_peaking_overlay_px=0 hdmi_clean_feed_combos_verified=22 hdmi_info_on_zero_assist_ok=1 p2_write_blocked_rc=-30 p2_setting_sha256_match=1 appfw_ok=1 shim_elf_ok=1 emmc_write_count=0 r46b_ok=1 verify_us=679916",
                "FX6_R46_ZEBRA_PEAKING_HDMI_RC=0",
                "FX6_R46_ZEBRA_PEAKING_HDMI_EXIT rc=0 emmc_write_count=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        r46 = ms["r46_telemetry"]
        self.assertIsNotNone(r46)
        self.assertEqual(r46["zebra_peaking_hdmi_rc"], 0)
        b = r46["zebra_peaking_hdmi"]
        self.assertEqual(b["zebra_8presets_verified"], 8)
        self.assertEqual(b["zebra_survives_cam_settings_reset_ok"], 1)
        self.assertEqual(b["hdmi_zebra_overlay_px"], 0)
        self.assertEqual(b["hdmi_peaking_overlay_px"], 0)
        self.assertEqual(b["hdmi_clean_feed_combos_verified"], 22)
        self.assertEqual(b["r46b_ok"], 1)

    def test_06_round46_extract_milestones_r46c_fullformat_chord_vault(self) -> None:
        runner = _load_closure_module("fx6_brr_r46_msc", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R46_FULLFORMAT_CHORD_VAULT invalid_fmt_mode_reject_rc=-22 slot2_quick_format_meta_only_ok=1 delete_key_toggles_full_format_ok=1 slot2_full_format_all_blocks_ok=1 mid_cancel_erases_data_card_usable_ok=1 chord_threshold_ms=2000 chord_sub2s_ignored_ok=1 non_vault_chord_2000ms_dialog_ok=1 vault_3artifacts_guarded=3 slot1_vault_quick_format_reject_rc=-16 slot1_vault_full_format_reject_rc=-16 slot1_vault_mid_cancel_reject_rc=-16 slot1_chord_2000ms_vault_reject_rc=-16 slot1_vault_wp_format_reject_rc=-13 slot1_chord_2000ms_wp_reject_rc=-13 slot1_format_writes=0 slot1_vault_sha256_intact=1 verified_swapped_nonvault_unlock_ok=1 p2_write_blocked_rc=-30 dlopen_ok=1 surfaces_verified=16 surfaces_h0_eq_h3=16 drift_bits=0 emmc_write_count=0 r46c_ok=1 verify_us=273182",
                "FX6_R46_FULLFORMAT_CHORD_VAULT_RC=0",
                "FX6_R46_FULLFORMAT_CHORD_VAULT_EXIT rc=0 emmc_write_count=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        r46 = ms["r46_telemetry"]
        self.assertIsNotNone(r46)
        self.assertEqual(r46["fullformat_chord_vault_rc"], 0)
        c = r46["fullformat_chord_vault"]
        self.assertEqual(c["vault_3artifacts_guarded"], 3)
        self.assertEqual(c["slot1_vault_full_format_reject_rc"], -16)
        self.assertEqual(c["slot1_vault_wp_format_reject_rc"], -13)
        self.assertEqual(c["slot1_format_writes"], 0)
        self.assertEqual(c["surfaces_h0_eq_h3"], 16)
        self.assertEqual(c["r46c_ok"], 1)

    def test_07_round46_extract_milestones_returns_none_when_no_r46_lines(self) -> None:
        runner = _load_closure_module("fx6_brr_r46_msnone", "build_and_run_round.py")
        ms = runner.extract_milestones("Linux version 4.9.337-scel+ #1 SMP PREEMPT\n")
        self.assertIsNone(ms["r46_telemetry"])

    def test_08_round46_stage_a_overlay_r46a_sq_fixedvar_mocked_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r46_ovl_a", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            for clean_flag in ("0", "1"):
                work = tmp_dir / f"r46_a_{clean_flag}"
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                    rep, add, meta = _build_overlay_for_r46(
                        runner, tmp_dir, work, "sq_fixedvar_6locks_big6", lang="schinese"
                    )
                init_out = rep["init"].decode("utf-8")
                self.assertNotIn("--r46-zebra-peaking-hdmi", init_out)
                self.assertNotIn("--r46-fullformat-chord-vault", init_out)
                self.assertIn("--sd-gate", init_out)
                self.assertIn("etc/fx6_stage_r46", add)
                self.assertIn("r46_mode=sq_fixedvar_6locks_big6", add["etc/fx6_stage_r46"][0].decode("utf-8"))
                self.assertTrue(meta["r46_enabled"])
                self.assertEqual(meta["r46"]["r46_mode"], "sq_fixedvar_6locks_big6")
                self.assertEqual(meta["r46"]["mode_settings_locks_sq_settings_rc"], -16)
                self.assertEqual(meta["r46"]["hdmi_zebra_overlay_pixels"], 0)
                self.assertEqual(meta["r46"]["slot1_format_writes"], 0)

    def test_09_round46_stage_a_overlay_r46b_and_r46c_mocked_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r46_ovl_bc", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            for clean_flag in ("0", "1"):
                work_b = tmp_dir / f"r46_b_{clean_flag}"
                work_c = tmp_dir / f"r46_c_{clean_flag}"
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                    rep_b, _, meta_b = _build_overlay_for_r46(
                        runner, tmp_dir, work_b, "zebra_persist_peaking_hdmi_isolation", lang="en"
                    )
                    rep_c, _, meta_c = _build_overlay_for_r46(
                        runner, tmp_dir, work_c, "slot1_fullformat_chord_vault_h0_h3", lang="en"
                    )
                init_b = rep_b["init"].decode("utf-8")
                init_c = rep_c["init"].decode("utf-8")
                self.assertIn("/usr/bin/fx6-stage-a-verify --r46-zebra-peaking-hdmi", init_b)
                self.assertIn("FX6_R46_ZEBRA_PEAKING_HDMI_EXIT", init_b)
                self.assertEqual(meta_b["r46"]["r46_mode"], "zebra_persist_peaking_hdmi_isolation")
                self.assertIn("/usr/bin/fx6-stage-a-verify --r46-fullformat-chord-vault", init_c)
                self.assertIn("FX6_R46_FULLFORMAT_CHORD_VAULT_EXIT", init_c)
                self.assertEqual(meta_c["r46"]["r46_mode"], "slot1_fullformat_chord_vault_h0_h3")

    def test_10_round46_stage_a_overlay_rejects_invalid_mode_and_honors_disabled_flag(self) -> None:
        runner = _load_closure_module("fx6_brr_r46_badmode", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            with self.assertRaises(ValueError):
                _build_overlay_for_r46(
                    runner, tmp_dir, tmp_dir / "bad_r46", "invalid_r46_mode", lang="schinese"
                )
            _, add_off, meta_off = _build_overlay_for_r46(
                runner, tmp_dir, tmp_dir / "off_r46", "sq_fixedvar_6locks_big6", enable_r46=False
            )
            self.assertFalse(meta_off["r46_enabled"])
            self.assertNotIn("r46", meta_off)
            self.assertNotIn("etc/fx6_stage_r46", add_off)

    def test_11_round46_summary_json_schema_sanitization_and_audit_flags(self) -> None:
        summary_path = ROUND46_REPORT_DIR / "summary.json"
        self.assertTrue(summary_path.is_file())
        raw = summary_path.read_text(encoding="utf-8")
        for forbidden in ("/Users/", "/Volumes/KAFU2T", "/private/tmp"):
            self.assertNotIn(forbidden, raw)
        data = json.loads(raw)
        self.assertEqual(
            data["schema"],
            "fx6-on-fx3-round46-realhw-sq-fixedvar-zebra-peaking-fullformat-qemu-v1",
        )
        self.assertEqual(data["round"], 46)
        self.assertEqual(data["raw_firmware_bytes_leaked"], 0)
        self.assertIn("Linux version 4.9.337-scel+", data["kernel_version"])
        self.assertEqual(set(data["runs"].keys()), set(self.EXPECTED_RUN_KEYS))
        audit = data["r46_realhw_sq_fixedvar_zebra_peaking_fullformat_audit"]
        self.assertEqual(audit["round"], 46)
        self.assertEqual(audit["milestone"], 46)
        self.assertEqual(audit["total_runs"], 3)
        for k in (
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "r46a_mode_settings_fixed_variable_locks_sq_settings_verified",
            "r46a_sq_all_6_disqualification_locks_verified",
            "r46a_stageb_big6_sid_0a_over_340k_pixels_verified",
            "r46b_zebra_camera_settings_reset_survival_and_initialize_reset_verified",
            "r46b_zebra_and_peaking_zero_hdmi_overlay_pixels_when_hdmi_info_on_verified",
            "r46c_quick_vs_delete_fullformat_and_midcancel_erasure_verified",
            "r46c_slot1_tier0_vault_and_menu_delete_2s_chord_lockout_and_16_h0_eq_h3_verified",
        ):
            self.assertTrue(audit[k], f"Audit flag {k} must be True")

    def test_12_round46_r46a_mode_settings_fixed_variable_locks_sq_settings(self) -> None:
        data = _load_r46_summary()
        init = data["runs"]["r46a_sq_fixedvar_6locks_big6_schinese"]["r46_telemetry"]["sq_fixedvar_init"]
        r46_meta = data["runs"]["r46a_sq_fixedvar_6locks_big6_schinese"]["stage_b"]["r46"]
        self.assertEqual(r46_meta["mode_settings_fixed_variable"], "Fixed/Variable")
        self.assertEqual(r46_meta["direct_fps_controls"], ["FPS", "Home (FPS)"])
        self.assertEqual(init["fixed_variable_locks_sq_settings_rc"], -16)
        self.assertEqual(init["legacy_sq_settings_unlocked_ok"], 1)
        self.assertEqual(init["invalid_mode_settings_reject_rc"], -22)
        self.assertEqual(init["direct_fps_home_control_ok"], 1)
        self.assertEqual(init["codec_follows_movie_settings_ok"], 1)

    def test_13_round46_r46a_sq_lock1_zero_audio_channels_recorded(self) -> None:
        data = _load_r46_summary()
        init = data["runs"]["r46a_sq_fixedvar_6locks_big6_schinese"]["r46_telemetry"]["sq_fixedvar_init"]
        r46_meta = data["runs"]["r46a_sq_fixedvar_6locks_big6_schinese"]["stage_b"]["r46"]
        self.assertEqual(init["sq_6locks_verified"], 6)
        self.assertEqual(init["sq_audio_channels"], 0)
        self.assertEqual(init["sq_audio_rec_reject_rc"], -95)
        self.assertIn("0ch no sound recorded", r46_meta["sq_6_hard_lockouts"][0])

    def test_14_round46_r46a_sq_lock2_audio_out_timing_live_lipsync_disabled_in_sq(self) -> None:
        data = _load_r46_summary()
        init = data["runs"]["r46a_sq_fixedvar_6locks_big6_schinese"]["r46_telemetry"]["sq_fixedvar_init"]
        r46_meta = data["runs"]["r46a_sq_fixedvar_6locks_big6_schinese"]["stage_b"]["r46"]
        self.assertEqual(r46_meta["audio_out_timing_modes"], ["Live", "Lip Sync"])
        self.assertEqual(init["normal_audio_out_timing_2modes_ok"], 2)
        self.assertEqual(init["invalid_audio_timing_reject_rc"], -22)
        self.assertEqual(init["sq_audio_out_timing_reject_rc"], -95)
        self.assertIn("[Audio Out Timing]", r46_meta["sq_6_hard_lockouts"][1])

    def test_15_round46_r46a_sq_lock3_timecode_run_and_output_unavailable(self) -> None:
        data = _load_r46_summary()
        init = data["runs"]["r46a_sq_fixedvar_6locks_big6_schinese"]["r46_telemetry"]["sq_fixedvar_init"]
        r46_meta = data["runs"]["r46a_sq_fixedvar_6locks_big6_schinese"]["stage_b"]["r46"]
        self.assertEqual(init["sq_tc_run_reject_rc"], -95)
        self.assertEqual(init["sq_tc_output_reject_rc"], -95)
        self.assertIn("[Time Code Run]", r46_meta["sq_6_hard_lockouts"][2])
        self.assertIn("[Time Code Output]", r46_meta["sq_6_hard_lockouts"][2])

    def test_16_round46_r46a_sq_lock4_240_200fps_blocked_on_all_4_4k_formats_allowed_on_hd(self) -> None:
        data = _load_r46_summary()
        init = data["runs"]["r46a_sq_fixedvar_6locks_big6_schinese"]["r46_telemetry"]["sq_fixedvar_init"]
        r46_meta = data["runs"]["r46a_sq_fixedvar_6locks_big6_schinese"]["stage_b"]["r46"]
        self.assertEqual(
            r46_meta["sq_240_200_blocked_4k_formats"],
            ["XAVC HS 4K", "XAVC S 4K", "XAVC S-I 4K", "XAVC S-I DCI 4K"],
        )
        self.assertEqual(init["sq_240_200_4k_blocked"], 4)
        self.assertEqual(init["sq_240_200_hd_allowed"], 2)
        self.assertEqual(init["sq_240_200_4k_reject_rc"], -22)

    def test_17_round46_r46a_sq_lock5_120_100fps_blocked_on_xavc_si_dci_4k_allowed_on_uhd(self) -> None:
        data = _load_r46_summary()
        init = data["runs"]["r46a_sq_fixedvar_6locks_big6_schinese"]["r46_telemetry"]["sq_fixedvar_init"]
        r46_meta = data["runs"]["r46a_sq_fixedvar_6locks_big6_schinese"]["stage_b"]["r46"]
        self.assertEqual(r46_meta["sq_120_100_blocked_dci_format"], "XAVC S-I DCI 4K")
        self.assertEqual(init["sq_120_100_dci4k_blocked"], 2)
        self.assertEqual(init["sq_120_100_uhd4k_allowed"], 3)
        self.assertEqual(init["sq_120_100_dci4k_reject_rc"], -22)

    def test_18_round46_r46a_sq_lock6_proxy_recording_blocked_at_rec_119_100p_or_fps_ge100(self) -> None:
        data = _load_r46_summary()
        init = data["runs"]["r46a_sq_fixedvar_6locks_big6_schinese"]["r46_telemetry"]["sq_fixedvar_init"]
        r46_meta = data["runs"]["r46a_sq_fixedvar_6locks_big6_schinese"]["stage_b"]["r46"]
        self.assertEqual(init["sq_proxy_le60_allowed"], 1)
        self.assertEqual(init["sq_proxy_rec119_100_blocked"], 2)
        self.assertEqual(init["sq_proxy_fps_ge100_blocked"], 4)
        self.assertEqual(init["sq_proxy_cutoff_reject_rc"], -22)
        self.assertIn("[Proxy Recording]", r46_meta["sq_6_hard_lockouts"][5])

    def test_19_round46_r46a_p2_ro_firewall_and_elf_token_presence(self) -> None:
        data = _load_r46_summary()
        init = data["runs"]["r46a_sq_fixedvar_6locks_big6_schinese"]["r46_telemetry"]["sq_fixedvar_init"]
        self.assertEqual(init["p2_write_blocked_rc"], -30)
        self.assertEqual(init["p2_sha256_match"], 1)
        self.assertEqual(init["appfw_present"], 1)
        self.assertEqual(init["shim_present"], 1)
        self.assertEqual(init["emmc_write_count"], 0)
        self.assertEqual(init["r46_init_ok"], 1)

    def test_20_round46_r46a_stage_b_13_sha256_locks_and_manifest_integrity(self) -> None:
        data = _load_r46_summary()
        r46a = data["runs"]["r46a_sq_fixedvar_6locks_big6_schinese"]
        self.assertEqual(r46a["stage_b"]["manifest_count"], 13)
        self.assertEqual(len(r46a["stage_b"]["manifest_items"]), 13)
        seen_paths = set()
        for item in r46a["stage_b"]["manifest_items"]:
            seen_paths.add(item["guest_path"])
            self.assertEqual(len(item["sha256"]), 64)
            int(item["sha256"], 16)
        self.assertIn("/usr/lib/appFw.so", seen_paths)
        self.assertIn("/usr/lib/libgrm-fbinit9.so", seen_paths)

    def test_21_round46_r46a_big6_home_schinese_render_invariants(self) -> None:
        data = _load_r46_summary()
        r46a = data["runs"]["r46a_sq_fixedvar_6locks_big6_schinese"]
        self.assertEqual(r46a["round"], 46)
        self.assertEqual(r46a["lang"], "schinese")
        self.assertEqual(r46a["r46_mode"], "sq_fixedvar_6locks_big6")
        self.assertEqual(r46a["target_presenter"], "31procam_big6_menu_home_presenter")
        self.assertEqual(r46a["target_sid"], "0x0a")
        self.assertEqual(r46a["nop_count"], 0)
        self.assertEqual(r46a["crashes"], 0)
        self.assertEqual(r46a["emmc_write_count"], 0)
        self.assertGreaterEqual(r46a["total_threads_seen"], 160)
        fi = r46a["faithful_invariants"]
        self.assertEqual(fi["FX6_NATIVE_FAITHFUL"], 1)
        self.assertEqual(fi["subst_color"], 0)
        self.assertEqual(fi["subst_image"], 0)
        self.assertEqual(fi["forced_render"], 0)
        self.assertEqual(fi["skipped_node"], 0)
        self.assertEqual(fi["lock_bypass"], 0)

    def test_22_round46_r46a_gpe0_framebuffer_readback_over_340k_pixels(self) -> None:
        data = _load_r46_summary()
        gpe = data["runs"]["r46a_sq_fixedvar_6locks_big6_schinese"]["gpe0_readback"]
        lt = data["runs"]["r46a_sq_fixedvar_6locks_big6_schinese"]["r46_telemetry"]["lang_telemetry"]
        self.assertTrue(gpe["present"])
        self.assertEqual(gpe["bytes"], 2211840)
        self.assertEqual(gpe["total_pixels"], 552960)
        self.assertEqual(gpe["nonzero_pixels"], 346206)
        self.assertGreaterEqual(gpe["unique_colors"], 80)
        self.assertEqual(lt["gpe_fb"], 0)
        self.assertEqual(lt["font_bank"], 23)
        self.assertEqual(lt["str_bank"], 19)

    def test_23_round46_r46a_alpha_png_under_50kib_crc_and_sha256(self) -> None:
        data = _load_r46_summary()
        ap = data["runs"]["r46a_sq_fixedvar_6locks_big6_schinese"]["png_exports"]["alpha_png"]
        p = REPO_ROOT / ap["path"]
        self.assertTrue(p.is_file(), f"Missing alpha PNG: {p}")
        raw = p.read_bytes()
        self.assertLess(len(raw), 50 * 1024)
        self.assertLess(len(raw), 28 * 1024)
        self.assertEqual(len(raw), ap["bytes"])
        self.assertEqual(hashlib.sha256(raw).hexdigest(), ap["sha256"])
        w, h, rows = _decode_png_rgba_rows(raw)
        self.assertEqual((w, h, len(rows)), (1024, 540, 540))

    def test_24_round46_r46a_composited_png_under_50kib_crc_and_sha256(self) -> None:
        data = _load_r46_summary()
        cp = data["runs"]["r46a_sq_fixedvar_6locks_big6_schinese"]["png_exports"]["composited_png"]
        p = REPO_ROOT / cp["path"]
        self.assertTrue(p.is_file(), f"Missing composited PNG: {p}")
        raw = p.read_bytes()
        self.assertLess(len(raw), 50 * 1024)
        self.assertLess(len(raw), 28 * 1024)
        self.assertEqual(len(raw), cp["bytes"])
        self.assertEqual(hashlib.sha256(raw).hexdigest(), cp["sha256"])
        w, h, rows = _decode_png_rgba_rows(raw)
        self.assertEqual((w, h, len(rows)), (1024, 540, 540))

    def test_25_round46_r46a_alpha_vs_composited_backdrop_pixel_consistency(self) -> None:
        data = _load_r46_summary()
        exp = data["runs"]["r46a_sq_fixedvar_6locks_big6_schinese"]["png_exports"]
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

    def test_26_round46_r46a_stage_b_bridge_telemetry_flags(self) -> None:
        data = _load_r46_summary()
        sb_bridge = data["runs"]["r46a_sq_fixedvar_6locks_big6_schinese"]["r46_telemetry"]["stage_b_bridge"]
        lt = data["runs"]["r46a_sq_fixedvar_6locks_big6_schinese"]["r46_telemetry"]["lang_telemetry"]
        self.assertEqual(sb_bridge["round"], 46)
        self.assertEqual(sb_bridge["sq_fixedvar_6locks"], 1)
        self.assertEqual(sb_bridge["zebra_camreset_peaking_hdmi_zero"], 1)
        self.assertEqual(sb_bridge["slot1_fullformat_chord_vault_firewall"], 1)
        self.assertEqual(lt["round46_realhw_sq_fixedvar_zebra_peaking_fullformat"], 1)
        self.assertEqual(lt["r46_bridge_ok"], 1)

    def test_27_round46_r46a_prefix_counts_include_r46_and_osd_flush(self) -> None:
        data = _load_r46_summary()
        counts = data["runs"]["r46a_sq_fixedvar_6locks_big6_schinese"]["prefix_counts"]
        self.assertGreater(counts["FX6_R46_"], 100)
        self.assertGreater(counts["FX6_OSD_FLUSH"], 100)
        self.assertEqual(counts.get("APPFW_SEGV", 0), 0)
        self.assertEqual(counts.get("FX6_ABORT_", 0), 0)

    def test_28_round46_r46b_zebra_defaults_and_wheel_left_select_toggle(self) -> None:
        data = _load_r46_summary()
        r46b = data["runs"]["r46b_zebra_persist_peaking_hdmi_isolation"]
        zb = r46b["r46_telemetry"]["zebra_peaking_hdmi"]
        r46_meta = r46b["stage_b"]["r46"]
        self.assertEqual(r46b["r46_telemetry"]["zebra_peaking_hdmi_rc"], 0)
        self.assertEqual(r46_meta["zebra_display_modes"], ["Off", "On"])
        self.assertEqual(r46_meta["zebra_wheel_left_default"], "Zebra Display Select")
        self.assertEqual(zb["zebra_defaults_off_70_ok"], 1)
        self.assertEqual(zb["wheel_left_zebra_select_ok"], 1)
        self.assertEqual(zb["invalid_zebra_disp_reject_rc"], -22)

    def test_29_round46_r46b_zebra_8_preset_levels_verified(self) -> None:
        data = _load_r46_summary()
        r46b = data["runs"]["r46b_zebra_persist_peaking_hdmi_isolation"]
        zb = r46b["r46_telemetry"]["zebra_peaking_hdmi"]
        r46_meta = r46b["stage_b"]["r46"]
        self.assertEqual(
            r46_meta["zebra_8_preset_levels"],
            ["70", "75", "80", "85", "90", "95", "100", "100+"],
        )
        self.assertEqual(zb["zebra_8presets_verified"], 8)
        self.assertEqual(zb["invalid_zebra_level_reject_rc"], -22)

    def test_30_round46_r46b_zebra_custom1_std_range_and_custom2_lower_limit(self) -> None:
        data = _load_r46_summary()
        r46b = data["runs"]["r46b_zebra_persist_peaking_hdmi_isolation"]
        zb = r46b["r46_telemetry"]["zebra_peaking_hdmi"]
        r46_meta = r46b["stage_b"]["r46"]
        self.assertEqual(
            r46_meta["zebra_custom_levels"],
            ["Custom 1 (Standard+Range)", "Custom 2 (Minimum/Lower-Limit)"],
        )
        self.assertEqual(zb["zebra_custom1_std_range_ok"], 1)
        self.assertEqual(zb["zebra_custom2_lower_limit_ok"], 1)

    def test_31_round46_r46b_zebra_survives_camera_settings_reset_cleared_only_by_initialize(self) -> None:
        data = _load_r46_summary()
        r46b = data["runs"]["r46b_zebra_persist_peaking_hdmi_isolation"]
        zb = r46b["r46_telemetry"]["zebra_peaking_hdmi"]
        r46_meta = r46b["stage_b"]["r46"]
        self.assertTrue(r46_meta["zebra_survives_camera_settings_reset"])
        self.assertTrue(r46_meta["zebra_reset_only_by_initialize"])
        self.assertEqual(zb["zebra_survives_cam_settings_reset_ok"], 1)
        self.assertEqual(zb["initialize_resets_zebra_off_70_ok"], 1)

    def test_32_round46_r46b_peaking_3_levels_and_4_colors_verified(self) -> None:
        data = _load_r46_summary()
        r46b = data["runs"]["r46b_zebra_persist_peaking_hdmi_isolation"]
        zb = r46b["r46_telemetry"]["zebra_peaking_hdmi"]
        r46_meta = r46b["stage_b"]["r46"]
        self.assertEqual(r46_meta["peaking_levels"], ["High", "Mid", "Low"])
        self.assertEqual(r46_meta["peaking_colors"], ["Red", "Yellow", "Blue", "White"])
        self.assertEqual(zb["peaking_defaults_off_mid_white_ok"], 1)
        self.assertEqual(zb["invalid_peaking_reject_rc"], -22)
        self.assertEqual(zb["peaking_3levels_verified"], 3)
        self.assertEqual(zb["peaking_4colors_verified"], 4)

    def test_33_round46_r46b_zero_hdmi_overlay_pixels_for_zebra_and_peaking_even_when_hdmi_info_on(self) -> None:
        data = _load_r46_summary()
        zb = data["runs"]["r46b_zebra_persist_peaking_hdmi_isolation"]["r46_telemetry"]["zebra_peaking_hdmi"]
        self.assertEqual(zb["hdmi_info_display_on"], 1)
        self.assertGreater(zb["lcd_zebra_overlay_px"], 0)
        self.assertGreater(zb["lcd_peaking_overlay_px"], 0)
        self.assertEqual(zb["hdmi_zebra_overlay_px"], 0)
        self.assertEqual(zb["hdmi_peaking_overlay_px"], 0)
        self.assertEqual(zb["hdmi_clean_feed_combos_verified"], 22)
        self.assertEqual(zb["hdmi_info_on_zero_assist_ok"], 1)

    def test_34_round46_r46b_p2_ro_protection_and_early_exit_readback_skip(self) -> None:
        data = _load_r46_summary()
        r46b = data["runs"]["r46b_zebra_persist_peaking_hdmi_isolation"]
        zb = r46b["r46_telemetry"]["zebra_peaking_hdmi"]
        self.assertEqual(zb["p2_write_blocked_rc"], -30)
        self.assertEqual(zb["p2_setting_sha256_match"], 1)
        self.assertEqual(zb["appfw_ok"], 1)
        self.assertEqual(zb["shim_elf_ok"], 1)
        self.assertEqual(zb["emmc_write_count"], 0)
        self.assertEqual(zb["r46b_ok"], 1)
        self.assertFalse(r46b["gpe0_readback"]["present"])
        self.assertTrue(r46b["gpe0_readback"]["skipped_stock_fx3_mode"])

    def test_35_round46_r46b_c_source_enforces_zero_hdmi_zebra_and_peaking_pixels(self) -> None:
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        self.assertIn("*out_hdmi_zebra_px = 0U;", verify_src)
        self.assertIn("*out_hdmi_peaking_px = 0U;", verify_src)

    def test_36_round46_r46c_quick_format_vs_delete_toggled_full_format(self) -> None:
        data = _load_r46_summary()
        r46c = data["runs"]["r46c_slot1_fullformat_chord_vault_h0_h3"]
        ff = r46c["r46_telemetry"]["fullformat_chord_vault"]
        r46_meta = r46c["stage_b"]["r46"]
        self.assertEqual(r46_meta["format_modes"], ["Quick Format", "Full Format"])
        self.assertEqual(r46_meta["full_format_toggle_key"], "(Delete)")
        self.assertEqual(ff["invalid_fmt_mode_reject_rc"], -22)
        self.assertEqual(ff["slot2_quick_format_meta_only_ok"], 1)
        self.assertEqual(ff["delete_key_toggles_full_format_ok"], 1)
        self.assertEqual(ff["slot2_full_format_all_blocks_ok"], 1)

    def test_37_round46_r46c_mid_cancel_full_format_erases_data_card_stays_usable(self) -> None:
        data = _load_r46_summary()
        ff = data["runs"]["r46c_slot1_fullformat_chord_vault_h0_h3"]["r46_telemetry"]["fullformat_chord_vault"]
        self.assertEqual(ff["mid_cancel_erases_data_card_usable_ok"], 1)

    def test_38_round46_r46c_menu_plus_delete_2000ms_chord_threshold(self) -> None:
        data = _load_r46_summary()
        r46c = data["runs"]["r46c_slot1_fullformat_chord_vault_h0_h3"]
        ff = r46c["r46_telemetry"]["fullformat_chord_vault"]
        r46_meta = r46c["stage_b"]["r46"]
        self.assertEqual(r46_meta["menu_delete_chord_hold_ms"], 2000)
        self.assertEqual(ff["chord_threshold_ms"], 2000)
        self.assertEqual(ff["chord_sub2s_ignored_ok"], 1)
        self.assertEqual(ff["non_vault_chord_2000ms_dialog_ok"], 1)

    def test_39_round46_r46c_tier0_vault_3_artifacts_enumerated_and_guarded(self) -> None:
        data = _load_r46_summary()
        r46c = data["runs"]["r46c_slot1_fullformat_chord_vault_h0_h3"]
        ff = r46c["r46_telemetry"]["fullformat_chord_vault"]
        r46_meta = r46c["stage_b"]["r46"]
        self.assertEqual(
            r46_meta["slot1_tier0_vault_artifacts"],
            ["pnflasha", "cnflasha", "CAMSET01.DAT"],
        )
        self.assertEqual(ff["vault_3artifacts_guarded"], 3)

    def test_40_round46_r46c_slot1_active_vault_ebusy_lockout_across_all_format_paths(self) -> None:
        data = _load_r46_summary()
        r46c = data["runs"]["r46c_slot1_fullformat_chord_vault_h0_h3"]
        ff = r46c["r46_telemetry"]["fullformat_chord_vault"]
        r46_meta = r46c["stage_b"]["r46"]
        self.assertEqual(r46_meta["slot1_vault_active_reject_rc"], -16)
        self.assertEqual(ff["slot1_vault_quick_format_reject_rc"], -16)
        self.assertEqual(ff["slot1_vault_full_format_reject_rc"], -16)
        self.assertEqual(ff["slot1_vault_mid_cancel_reject_rc"], -16)
        self.assertEqual(ff["slot1_chord_2000ms_vault_reject_rc"], -16)

    def test_41_round46_r46c_slot1_write_protect_switch_eacces_lockout(self) -> None:
        data = _load_r46_summary()
        r46c = data["runs"]["r46c_slot1_fullformat_chord_vault_h0_h3"]
        ff = r46c["r46_telemetry"]["fullformat_chord_vault"]
        r46_meta = r46c["stage_b"]["r46"]
        self.assertEqual(r46_meta["slot1_vault_wp_reject_rc"], -13)
        self.assertEqual(ff["slot1_vault_wp_format_reject_rc"], -13)
        self.assertEqual(ff["slot1_chord_2000ms_wp_reject_rc"], -13)

    def test_42_round46_r46c_slot1_zero_format_writes_sha256_intact_and_post_swap_unlock(self) -> None:
        data = _load_r46_summary()
        ff = data["runs"]["r46c_slot1_fullformat_chord_vault_h0_h3"]["r46_telemetry"]["fullformat_chord_vault"]
        self.assertEqual(ff["slot1_format_writes"], 0)
        self.assertEqual(ff["slot1_vault_sha256_intact"], 1)
        self.assertEqual(ff["verified_swapped_nonvault_unlock_ok"], 1)

    def test_43_round46_r46c_c_source_vault_artifact_bits_and_chord_2000ms_constant(self) -> None:
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        for sym in (
            "R46_VAULT_PNFLASHA",
            "R46_VAULT_CNFLASHA",
            "R46_VAULT_CAMSET01",
            "#define R46_CHORD_HOLD_THRESHOLD_MS 2000",
        ):
            self.assertIn(sym, verify_src)

    def test_44_round46_r46c_guest_dlopen_libjit_and_16_of_16_h0_eq_h3(self) -> None:
        data = _load_r46_summary()
        r46c = data["runs"]["r46c_slot1_fullformat_chord_vault_h0_h3"]
        ff = r46c["r46_telemetry"]["fullformat_chord_vault"]
        self.assertEqual(r46c["r46_telemetry"]["fullformat_chord_vault_rc"], 0)
        self.assertEqual(ff["p2_write_blocked_rc"], -30)
        self.assertEqual(ff["dlopen_ok"], 1)
        self.assertEqual(ff["surfaces_verified"], 16)
        self.assertEqual(ff["surfaces_h0_eq_h3"], 16)
        self.assertEqual(ff["drift_bits"], 0)
        self.assertEqual(ff["emmc_write_count"], 0)
        self.assertEqual(ff["r46c_ok"], 1)

    def test_45_round46_cross_run_bridge_telemetry_matches_r46a_r46b_r46c(self) -> None:
        data = _load_r46_summary()
        ta = data["runs"]["r46a_sq_fixedvar_6locks_big6_schinese"]["r46_telemetry"]
        r46b = data["runs"]["r46b_zebra_persist_peaking_hdmi_isolation"]["r46_telemetry"]["zebra_peaking_hdmi"]
        r46c = data["runs"]["r46c_slot1_fullformat_chord_vault_h0_h3"]["r46_telemetry"]["fullformat_chord_vault"]

        sqb = ta["sq_fixedvar_bridge"]
        sqi = ta["sq_fixedvar_init"]
        self.assertEqual(sqb["fixed_variable_locks_sq_settings_rc"], sqi["fixed_variable_locks_sq_settings_rc"])
        self.assertEqual(sqb["sq_6locks_verified"], sqi["sq_6locks_verified"])
        self.assertEqual(sqb["sq_audio_channels"], sqi["sq_audio_channels"])
        self.assertEqual(sqb["sq_240_200_4k_blocked"], sqi["sq_240_200_4k_blocked"])
        self.assertEqual(sqb["sq_120_100_dci4k_blocked"], sqi["sq_120_100_dci4k_blocked"])
        self.assertEqual(sqb["sq_proxy_fps_ge100_blocked"], sqi["sq_proxy_fps_ge100_blocked"])
        self.assertEqual(sqb["sq_fixedvar_ok"], 1)

        zpb = ta["zebra_peaking_bridge"]
        self.assertEqual(zpb["zebra_8presets_verified"], r46b["zebra_8presets_verified"])
        self.assertEqual(zpb["zebra_survives_cam_settings_reset_ok"], r46b["zebra_survives_cam_settings_reset_ok"])
        self.assertEqual(zpb["hdmi_zebra_overlay_px"], r46b["hdmi_zebra_overlay_px"])
        self.assertEqual(zpb["hdmi_peaking_overlay_px"], r46b["hdmi_peaking_overlay_px"])
        self.assertEqual(zpb["zebra_peaking_hdmi_ok"], 1)

        ffb = ta["fullformat_vault_bridge"]
        self.assertEqual(ffb["delete_key_toggles_full_format_ok"], r46c["delete_key_toggles_full_format_ok"])
        self.assertEqual(ffb["mid_cancel_erases_data_card_usable_ok"], r46c["mid_cancel_erases_data_card_usable_ok"])
        self.assertEqual(ffb["slot1_vault_full_format_reject_rc"], r46c["slot1_vault_full_format_reject_rc"])
        self.assertEqual(ffb["slot1_vault_wp_format_reject_rc"], r46c["slot1_vault_wp_format_reject_rc"])
        self.assertEqual(ffb["slot1_format_writes"], r46c["slot1_format_writes"])
        self.assertEqual(ffb["fullformat_vault_ok"], 1)

    def test_46_round46_realhw_mechanisms_verified_top_level_completeness(self) -> None:
        data = _load_r46_summary()
        rm = data["realhw_mechanisms_verified"]
        for key in (
            "sq_fixedvar_mode_settings_and_6_hard_lockouts_init",
            "sq_fixedvar_stage_b_bridge",
            "zebra_peaking_hdmi_stage_b_bridge",
            "fullformat_chord_vault_stage_b_bridge",
            "zebra_camera_reset_persistence_and_peaking_hdmi_clean_feed_isolation",
            "slot1_quick_vs_delete_fullformat_midcancel_and_menu_delete_2s_chord_vault_lockout_h0_h3",
        ):
            self.assertIn(key, rm)
            self.assertTrue(rm[key], f"Top-level mechanism {key} must be non-empty")

    def test_47_round46_unexecuted_physical_camera_bench_boundaries_documented(self) -> None:
        data = _load_r46_summary()
        bounds = data["unexecuted_physical_camera_bench_boundaries"]
        self.assertEqual(len(bounds), 3)
        joined = " ".join(bounds)
        for token in ("Fixed/Variable", "Zebra", "Full Format", "unexecuted"):
            self.assertIn(token, joined)

    def test_48_round46_report_readme_exists_sanitized_and_links_assets(self) -> None:
        readme_path = ROUND46_REPORT_DIR / "README.md"
        self.assertTrue(readme_path.is_file())
        txt = readme_path.read_text(encoding="utf-8")
        for forbidden in ("/Users/", "/Volumes/KAFU2T", "/private/tmp"):
            self.assertNotIn(forbidden, txt)
        for token in (
            "Round 46",
            "46th Milestone",
            "Wave-32",
            "Linux version 4.9.337-scel+",
            "r46a-sq-fixedvar-zebra-big6-schinese-alpha.png",
            "r46a-sq-fixedvar-zebra-big6-schinese-composited.png",
            "Fixed/Variable",
            "Zebra Display",
            "Peaking Display",
            "Full Format",
            "16/16 H0 == H3",
            "summary.json",
        ):
            self.assertIn(token, txt)

    def test_49_round46_closure_readme_section_46_present_and_sanitized(self) -> None:
        closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")
        for forbidden in ("/Users/", "/Volumes/KAFU2T"):
            self.assertNotIn(forbidden, closure_readme)
        marker = "## 46. Round 46 (`46th Milestone` / Wave-32)"
        self.assertIn(marker, closure_readme)
        sec46 = closure_readme.split(marker, 1)[1]
        for forbidden in ("/Users/", "/Volumes/KAFU2T", "/private/tmp"):
            self.assertNotIn(forbidden, sec46)
        for token in (
            "--round 46 --r46-mode",
            "round46-sq-fixedvar-zebra-big6",
            "round46-zebra-peaking-hdmi",
            "round46-fullformat-chord-vault",
            "2026-11-15-round46-realhw-sq-fixedvar-zebra-peaking-fullformat-qemu/README.md",
        ):
            self.assertIn(token, sec46)

    def test_50_round46_wave32_primary_spec_alignment(self) -> None:
        self.assertTrue(WAVE32_SPEC_PATH.is_file())
        spec_txt = WAVE32_SPEC_PATH.read_text(encoding="utf-8")
        data = _load_r46_summary()
        r46_meta = data["runs"]["r46a_sq_fixedvar_6locks_big6_schinese"]["stage_b"]["r46"]
        self.assertIn("Fixed/Variable", spec_txt)
        self.assertEqual(r46_meta["mode_settings_fixed_variable"], "Fixed/Variable")
        self.assertIn("Zebra Display", spec_txt)
        self.assertIn("Peaking Display", spec_txt)
        self.assertIn("Full Format", spec_txt)

    def test_51_round46_cli_parser_accepts_all_3_r46_modes_and_rejects_unknown(self) -> None:
        runner = _load_closure_module("fx6_brr_r46_cli", "build_and_run_round.py")
        for mode in (
            "sq_fixedvar_6locks_big6",
            "zebra_persist_peaking_hdmi_isolation",
            "slot1_fullformat_chord_vault_h0_h3",
        ):
            with mock.patch.object(runner, "run_once", return_value=0) as m_run, \
                 mock.patch.object(
                     sys,
                     "argv",
                     ["build_and_run_round.py", "--run-id", "t46", "--round", "46", "--r46-mode", mode],
                 ):
                rc = runner.main()
                self.assertEqual(rc, 0)
                parsed_args = m_run.call_args[0][0]
                self.assertEqual(parsed_args.round, 46)
                self.assertEqual(parsed_args.r46_mode, mode)
                self.assertEqual(parsed_args.restore_infra70, 1)
                self.assertEqual(parsed_args.reply_all_200d, 1)

        with mock.patch.object(
            sys,
            "argv",
            ["build_and_run_round.py", "--run-id", "t46", "--round", "46", "--r46-mode", "bogus"],
        ):
            with self.assertRaises(SystemExit):
                runner.main()

    def test_52_round46_cli_default_r46_mode_is_sq_fixedvar_6locks_big6(self) -> None:
        runner = _load_closure_module("fx6_brr_r46_clidef", "build_and_run_round.py")
        with mock.patch.object(runner, "run_once", return_value=0) as m_run, \
             mock.patch.object(
                 sys,
                 "argv",
                 ["build_and_run_round.py", "--run-id", "t46def", "--round", "46"],
             ):
            self.assertEqual(runner.main(), 0)
            self.assertEqual(m_run.call_args[0][0].r46_mode, "sq_fixedvar_6locks_big6")

    def test_53_round46_extract_milestones_nonzero_failure_rc_propagated(self) -> None:
        runner = _load_closure_module("fx6_brr_r46_msfail", "build_and_run_round.py")
        serial = "\n".join(
            [
                "FX6_R46_ZEBRA_PEAKING_HDMI r46b_ok=0",
                "FX6_R46_ZEBRA_PEAKING_HDMI_RC=239",
                "FX6_R46_FULLFORMAT_CHORD_VAULT r46c_ok=0",
                "FX6_R46_FULLFORMAT_CHORD_VAULT_RC=240",
            ]
        )
        r46 = runner.extract_milestones(serial)["r46_telemetry"]
        self.assertEqual(r46["zebra_peaking_hdmi_rc"], 239)
        self.assertEqual(r46["fullformat_chord_vault_rc"], 240)
        self.assertEqual(r46["zebra_peaking_hdmi"]["r46b_ok"], 0)
        self.assertEqual(r46["fullformat_chord_vault"]["r46c_ok"], 0)

    def test_54_round46_no_forbidden_binaries_or_oversized_assets_in_report_dir(self) -> None:
        forbidden_exts = {".cpio", ".so", ".o", ".img", ".qcow2", ".pyc", ".raw", ".bin"}
        files = [p for p in ROUND46_REPORT_DIR.rglob("*") if p.is_file()]
        self.assertEqual(len(files), 4)
        for p in files:
            self.assertNotIn(p.suffix.lower(), forbidden_exts, f"Forbidden artifact {p}")
            if p.suffix.lower() == ".png":
                self.assertLess(p.stat().st_size, 50 * 1024, f"Oversized PNG {p}")

    def test_55_round46_prior_round45_summary_contract_untouched(self) -> None:
        r45_summary = (
            REPO_ROOT
            / "reports"
            / "2026-11-15-round45-realhw-steadyshot-ciz-powersave-autotemp-qemu"
            / "summary.json"
        )
        self.assertTrue(r45_summary.is_file())
        d45 = json.loads(r45_summary.read_text(encoding="utf-8"))
        self.assertEqual(d45["round"], 45)
        self.assertEqual(d45["raw_firmware_bytes_leaked"], 0)

    def test_56_round46_dual_mode_clean_room_toggle_parity_on_summary_and_overlay(self) -> None:
        for clean_flag in ("0", "1"):
            with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                data = _load_r46_summary()
                self.assertEqual(data["round"], 46)
                self.assertEqual(
                    data["runs"]["r46a_sq_fixedvar_6locks_big6_schinese"]["r46_telemetry"]["sq_fixedvar_init"]["sq_6locks_verified"],
                    6,
                )
                self.assertEqual(
                    data["runs"]["r46b_zebra_persist_peaking_hdmi_isolation"]["r46_telemetry"]["zebra_peaking_hdmi"]["hdmi_zebra_overlay_px"],
                    0,
                )
                self.assertEqual(
                    data["runs"]["r46c_slot1_fullformat_chord_vault_h0_h3"]["r46_telemetry"]["fullformat_chord_vault"]["slot1_format_writes"],
                    0,
                )


if __name__ == "__main__":
    unittest.main()
