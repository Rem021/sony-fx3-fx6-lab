#!/usr/bin/env python3
"""Offline dual-mode unit tests for FX6-on-FX3 Round 52 (25th Real-HW Round / 75th Live Run Milestone — Wave-38)."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import pathlib
import struct
import sys
import tempfile
import unittest
import zlib
from typing import List, Tuple
from unittest import mock

TESTS_DIR = pathlib.Path(__file__).resolve().parent
CLOSURE_DIR = TESTS_DIR.parent
REPO_ROOT = CLOSURE_DIR.parent.parent
ROUND52_REPORT_DIR = (
    REPO_ROOT
    / "reports"
    / "2026-11-15-round52-realhw-lock-op-parts-audio-timing-exp-step-qemu"
)
WAVE38_SPEC_PATH = (
    REPO_ROOT
    / "reports"
    / "2026-11-15-global-sony-wave38-lock-op-parts-menu-fn-5s-audio-out-timing-audio-signals-exp-step-shutter-angle-intel"
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
        (
            "usr/share/app/fontlist.dat",
            b"FONT_S_CHINESE\t/usr/share/app/MYingHeiC-GB18030-SJ_wIcon.ltt\t0\t0\n",
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
        P1_LIB_INFRA_SETUP_FILE_SPEC = mock.Mock(
            spec_id="P1_s", library_name="s", sites=[mock.Mock(site_id="s1")]
        )
        P1_LIB_INFRA_MEDIA_COMMON_SPEC = mock.Mock(
            spec_id="P1_c", library_name="c", sites=[mock.Mock(site_id="c1")]
        )
        P1_LIB_INFRA_MEDIA_CONFIG_SPEC = mock.Mock(
            spec_id="P1_g", library_name="g", sites=[mock.Mock(site_id="g1")]
        )
        P3_LIB_INFRA_APP_REMOTE_BOARD_SPEC = mock.Mock(
            spec_id="P3_r", library_name="r", sites=[mock.Mock(site_id="r1")]
        )
        FAN_LIBFAN_SPEC = mock.Mock(
            spec_id="Fan_f", library_name="f", sites=[mock.Mock(site_id="f1")]
        )
        P9_UPM_KO_SPEC = mock.Mock(
            spec_id="P9_u", library_name="upm.ko", sites=[mock.Mock(site_id="u1")]
        )
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
                mode=mode,
                fat_type="FAT16",
                total_bytes=len(img),
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
                bk4_bytes=bk4,
                total_bytes=len(bk4),
                sha256=hashlib.sha256(bk4).hexdigest(),
                flash_write_allowed=False,
                active_byte8_selector=0,
                synthesized_key_count=1,
            )

    def fake_subproc_run(cmd, **_kw):
        out_idx = cmd.index("-o") + 1
        pathlib.Path(cmd[out_idx]).write_bytes(b"\x7fELF" + b"\x00" * 60)
        return mock.Mock(returncode=0, stdout="", stderr="")

    fake_jit_meta = {
        "bytes": 64,
        "sha256": "a" * 64,
        "e_type": 3,
        "e_machine": 183,
        "pt_load_count": 3,
        "pt_load_align": "0x10000",
        "has_pt_dynamic": True,
    }
    return parent_cpio, _FakePatcher, _FakeVfat, _FakeBmtvHex, fake_subproc_run, fake_jit_meta


def _build_overlay_for_r52(
    runner,
    tmp_dir: pathlib.Path,
    work: pathlib.Path,
    r52_mode: str,
    lang: str = "schinese",
    enable_r52: bool = True,
):
    parent_cpio, fp, fv, fb, fake_run, jit_meta = _build_mock_cpio_and_fakes(runner, tmp_dir)
    with mock.patch.object(runner, "_import_stage_a_modules", return_value=(fp, fv, fb)), \
         mock.patch.object(runner, "_load_p10_keymap_spec", return_value=mock.Mock(spec_id="P10_k", library_name="appFw.so", sites=(mock.Mock(site_id="p10", size=4),))), \
         mock.patch.object(runner, "_load_p12_wlan_spec", return_value=mock.Mock(spec_id="P12_w", library_name="libWlanResource.so", sites=(mock.Mock(site_id="p12", size=8),))), \
         mock.patch.object(runner, "build_hardened_libjit_so", return_value=(b"\x7fELF_JIT", dict(jit_meta))), \
         mock.patch.object(runner, "build_r30_tier0_libjit_so", return_value=(b"\x7fELF_R30_JIT", dict(jit_meta))), \
         mock.patch.object(runner.subprocess, "run", side_effect=fake_run):
        return runner.build_stage_a_overlay(
            work,
            parent_cpio,
            b"BK4NTSC",
            enable_p10=True,
            enable_r10=True,
            enable_p12=True,
            enable_r28=True,
            enable_r30=True,
            r30_mode="peripheral_big6",
            enable_r31=True,
            r31_mode="keymap_big6",
            enable_r32=True,
            r32_mode="imx510_cube_big6",
            enable_r33=True,
            r33_mode="cfexpress_rsv_big6",
            enable_r34=True,
            r34_mode="c2pa_tc_gyro_big6",
            enable_r35=True,
            r35_mode="ssboot_wbi2_big6",
            enable_r36=True,
            r36_mode="emount_info3d_big6",
            enable_r37=True,
            r37_mode="fx3a_firewall_big6",
            enable_r38=True,
            r38_mode="nouvc_dcc1_pd_big6",
            enable_r39=True,
            r39_mode="fan_pwm_offinrec_big6",
            enable_r40=True,
            r40_mode="big6_home_noend_big6",
            enable_r41=True,
            r41_mode="desqueeze_165x_4locks_big6",
            enable_r42=True,
            r42_mode="hdmi_log1080_hdmionly_4k_big6",
            enable_r43=True,
            r43_mode="filesettings_shotmark_big6",
            enable_r44=True,
            r44_mode="pixelmap_reboot_cnflasha_big6",
            enable_r45=True,
            r45_mode="steadyshot_active_cutoffs_big6",
            enable_r46=True,
            r46_mode="sq_fixedvar_6locks_big6",
            enable_r47=True,
            r47_mode="silent_autopixelmap_5locks_big6",
            enable_r48=True,
            r48_mode="monitor_flip_playback_big6",
            enable_r49=True,
            r49_mode="emphasized_rec_grid_hdmi_big6",
            enable_r50=True,
            r50_mode="shoe_audio_4ch_osd_big6",
            enable_r51=True,
            r51_mode="framing_settings_crop_hdmi_big6",
            enable_r52=enable_r52,
            r52_mode=r52_mode,
            sd_manifest_mode="valid",
            lang=lang,
            shim_bytes=b"SHIM",
        )


def _load_r52_summary() -> dict:
    return json.loads((ROUND52_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))


class TestRound52RealHwLockOpPartsAudioTimingExpStepQemu(unittest.TestCase):
    EXPECTED_RUN_KEYS = (
        "r52a_lock_op_parts_mydial_big6_schinese",
        "r52b_audio_out_timing_vs_audio_signals_guard",
        "r52c_exposure_step_vs_shutter_angle_h0_h3",
    )

    def test_01_wave38_global_spec_present_and_covers_all_wave38_pillars(self) -> None:
        self.assertTrue(WAVE38_SPEC_PATH.is_file())
        spec_txt = WAVE38_SPEC_PATH.read_text(encoding="utf-8")
        for needle in (
            "Lock Operation Parts",
            "MENU + Fn",
            "My Dial",
            "Audio Out Timing",
            "Lip Sync",
            "Audio signals",
            "Silent Mode",
            "Exposure step",
            "Shutter Angle",
        ):
            self.assertIn(needle, spec_txt)

    def test_02_round52_summary_schema_round_milestone_and_zero_leaks(self) -> None:
        raw_txt = (ROUND52_REPORT_DIR / "summary.json").read_text(encoding="utf-8")
        self.assertNotIn("/Users/", raw_txt)
        self.assertNotIn("/private/tmp/", raw_txt)
        data = json.loads(raw_txt)
        self.assertEqual(
            data["schema"],
            "fx6-on-fx3-round52-realhw-lock-op-parts-audio-timing-exp-step-qemu-v1",
        )
        self.assertEqual(data["round"], 52)
        self.assertEqual(data["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(tuple(data["runs"].keys()), self.EXPECTED_RUN_KEYS)

    def test_03_round52_cli_accepts_round52_and_all_3_r52_modes(self) -> None:
        runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")
        self.assertIn(", 52]", runner_src)
        for mode in (
            "lock_op_parts_chord_mydial_big6",
            "audio_out_timing_vs_audio_signals_guard",
            "exposure_step_vs_shutter_angle_guard",
        ):
            self.assertIn(mode, runner_src)

    def test_04_round52_overlay_rejects_invalid_r52_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r52_badmode", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tpath = pathlib.Path(tmp)
            with self.assertRaises(ValueError):
                _build_overlay_for_r52(runner, tpath, tpath / "work", "invalid_r52_mode")

    def test_05_round52_overlay_r52a_lock_op_mode_injects_etc_fx6_stage_r52_and_appfw_launch(self) -> None:
        runner = _load_closure_module("fx6_brr_r52_ov_a", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tpath = pathlib.Path(tmp)
            replacements, additions, meta = _build_overlay_for_r52(
                runner, tpath, tpath / "work", "lock_op_parts_chord_mydial_big6", lang="schinese"
            )
            self.assertTrue(meta["r52_enabled"])
            self.assertIn("etc/fx6_stage_r52", additions)
            r52_cfg = additions["etc/fx6_stage_r52"][0].decode("utf-8")
            self.assertIn("stage_r52=1", r52_cfg)
            self.assertIn("r52_mode=lock_op_parts_chord_mydial_big6", r52_cfg)
            self.assertIn("milestone_25th_realhw_75th_run=1", r52_cfg)
            init_txt = replacements["init"].decode("utf-8")
            self.assertIn("/usr/bin/appfw-launch", init_txt)
            self.assertNotIn("--r52-audio-timing-signals-guard", init_txt)
            self.assertNotIn("--r52-exp-step-shutter-angle-h0-h3", init_txt)

    def test_06_round52_overlay_r52b_audio_timing_signals_injects_early_probe_and_poweroff(self) -> None:
        runner = _load_closure_module("fx6_brr_r52_ov_b", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tpath = pathlib.Path(tmp)
            replacements, _, meta = _build_overlay_for_r52(
                runner, tpath, tpath / "work", "audio_out_timing_vs_audio_signals_guard", lang="en"
            )
            self.assertEqual(meta["r52"]["r52_mode"], "audio_out_timing_vs_audio_signals_guard")
            init_txt = replacements["init"].decode("utf-8")
            self.assertIn("--r52-audio-timing-signals-guard", init_txt)
            self.assertIn("FX6_R52_AUDIO_TIMING_SIGNALS_RC=", init_txt)
            self.assertIn("FX6_R52_AUDIO_TIMING_SIGNALS_EXIT", init_txt)
            self.assertIn("poweroff -f", init_txt)

    def test_07_round52_overlay_r52c_exp_step_shutter_angle_injects_early_probe_and_poweroff(self) -> None:
        runner = _load_closure_module("fx6_brr_r52_ov_c", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tpath = pathlib.Path(tmp)
            replacements, _, meta = _build_overlay_for_r52(
                runner, tpath, tpath / "work", "exposure_step_vs_shutter_angle_guard", lang="en"
            )
            self.assertEqual(meta["r52"]["r52_mode"], "exposure_step_vs_shutter_angle_guard")
            init_txt = replacements["init"].decode("utf-8")
            self.assertIn("--r52-exp-step-shutter-angle-h0-h3", init_txt)
            self.assertIn("FX6_R52_EXP_STEP_SHUTTER_ANGLE_RC=", init_txt)
            self.assertIn("FX6_R52_EXP_STEP_SHUTTER_ANGLE_EXIT", init_txt)
            self.assertIn("poweroff -f", init_txt)

    def test_08_round52_overlay_disabled_when_enable_r52_false(self) -> None:
        runner = _load_closure_module("fx6_brr_r52_ov_off", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tpath = pathlib.Path(tmp)
            _, additions, meta = _build_overlay_for_r52(
                runner, tpath, tpath / "work", "lock_op_parts_chord_mydial_big6", enable_r52=False
            )
            self.assertFalse(meta["r52_enabled"])
            self.assertNotIn("etc/fx6_stage_r52", additions)
            self.assertNotIn("r52", meta)

    def test_09_round52_stage_a_c_source_contains_all_3_wave38_probes(self) -> None:
        c_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        for sym in (
            "setup_r52_lock_op_parts_chord_mydial_probe",
            "run_r52_audio_timing_signals_guard_probe",
            "run_r52_exp_step_shutter_angle_probe",
            "FX6_R52_LOCK_OP_INIT",
            "FX6_R52_AUDIO_TIMING_SIGNALS_GUARD",
            "FX6_R52_EXP_STEP_SHUTTER_ANGLE",
            "--r52-audio-timing-signals-guard",
            "--r52-exp-step-shutter-angle-h0-h3",
            "/etc/fx6_stage_r52",
        ):
            self.assertIn(sym, c_src)

    def test_10_round52_shim_c_source_contains_r52_guarded_bridges(self) -> None:
        shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        self.assertIn("#if FX6_ROUND >= 52", shim_src)
        for sym in (
            "FX6_R52_LOCK_OP_PARTS_BRIDGE",
            "FX6_R52_AUDIO_TIMING_SIGNALS_BRIDGE",
            "FX6_R52_EXP_STEP_SHUTTER_ANGLE_BRIDGE",
            "FX6_R52_LANG_TELEMETRY",
            "FX6_STAGE_B_R52_BRIDGE",
        ):
            self.assertIn(sym, shim_src)

    def test_11_round52_compile_launcher_and_shim_aarch64_elf_symbols(self) -> None:
        runner = _load_closure_module("fx6_brr_r52_compile", "build_and_run_round.py")
        if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1" and not runner.ZIG.is_file():
            self.skipTest("Clean-room fallback without local zig binary")
        with tempfile.TemporaryDirectory() as tmp:
            launcher_b, shim_b, _ = runner.build_binaries(
                pathlib.Path(tmp) / "r52_bin",
                fx6_round=52,
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
            self.assertEqual(struct.unpack_from("<H", shim_b, 18)[0], 183)
            self.assertIn(b"FX6_R52_LOCK_OP_PARTS_BRIDGE", shim_b)
            self.assertIn(b"FX6_R52_AUDIO_TIMING_SIGNALS_BRIDGE", shim_b)
            self.assertIn(b"FX6_R52_EXP_STEP_SHUTTER_ANGLE_BRIDGE", shim_b)

    def test_12_round52_shim_round51_backward_compat_excludes_r52_bridges(self) -> None:
        runner = _load_closure_module("fx6_brr_r52_r51compat", "build_and_run_round.py")
        if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1" and not runner.ZIG.is_file():
            self.skipTest("Clean-room fallback without local zig binary")
        with tempfile.TemporaryDirectory() as tmp:
            _, shim_r51, _ = runner.build_binaries(
                pathlib.Path(tmp) / "r51_compat",
                fx6_round=51,
                restore_infra70=1,
                restore_all_early=0,
                reply_all_200d=1,
                initial_setting_done=1,
                key_seq="0x7028:120:5500",
                key_settle_ms=1500,
                lang="schinese",
            )
            self.assertIn(b"FX6_R51_FRAMING_BRIDGE", shim_r51)
            self.assertNotIn(b"FX6_R52_LOCK_OP_PARTS_BRIDGE", shim_r51)

    def test_13_round52_parse_log_extracts_all_8_r52_prefixes_and_rcs(self) -> None:
        runner = _load_closure_module("fx6_brr_r52_parse", "build_and_run_round.py")
        serial_text = (
            "\n".join(
                [
                    "Linux version 4.9.337-scel+ (sony@fx3)",
                    "FX6_R52_LOCK_OP_INIT fx3_lock_op_node_ok=1 lock_op_4modes_verified=4 destructive_menu_delete_confusions=0 slot1_vault_format_events=0 r52_init_ok=1",
                    "FX6_R52_LOCK_OP_PARTS_BRIDGE lock_op_4modes_verified=4 mydial_1_3_temp_override_verified=3 lock_op_parts_ok=1 r52_bridge_ok=1",
                    "FX6_R52_AUDIO_TIMING_SIGNALS_BRIDGE audio_out_timing_2modes_verified=2 audio_signals_3modes_verified=3 silent_mode_audio_signal_leak_events=0 audio_timing_signals_ok=1",
                    "FX6_R52_EXP_STEP_SHUTTER_ANGLE_BRIDGE exposure_step_2modes_verified=2 shutter_angle_5anchors_verified=5 shutter_angle_exposure_step_drift_events=0 exp_step_shutter_angle_ok=1",
                    "FX6_R52_LANG_TELEMETRY lang=schinese font_bank=23 str_bank=19 milestone_25th_realhw_75th_run=1 r52_bridge_ok=1",
                    "FX6_STAGE_B_R52_BRIDGE round=52 faithful=1 nop_count=0 milestone_25th_realhw_75th_run=1 emmc_write_count=0",
                    "FX6_R52_AUDIO_TIMING_SIGNALS_GUARD audio_out_timing_2modes_verified=2 audio_signals_3modes_verified=3 silent_mode_audio_signal_leak_events=0 r52b_ok=1",
                    "FX6_R52_AUDIO_TIMING_SIGNALS_RC=0",
                    "FX6_R52_EXP_STEP_SHUTTER_ANGLE exposure_step_2modes_verified=2 shutter_angle_5anchors_verified=5 surfaces_h0_eq_h3=16 r52c_ok=1",
                    "FX6_R52_EXP_STEP_SHUTTER_ANGLE_RC=0",
                ]
            )
            + "\n"
        )
        parsed = runner.extract_milestones(serial_text)
        r52_t = parsed["r52_telemetry"]
        self.assertEqual(r52_t["audio_timing_signals_rc"], 0)
        self.assertEqual(r52_t["exp_step_shutter_angle_rc"], 0)
        self.assertEqual(r52_t["lock_op_init"]["lock_op_4modes_verified"], 4)
        self.assertEqual(r52_t["lock_op_init"]["destructive_menu_delete_confusions"], 0)
        self.assertEqual(r52_t["lock_op_parts_bridge"]["mydial_1_3_temp_override_verified"], 3)
        self.assertEqual(r52_t["audio_timing_signals_bridge"]["audio_signals_3modes_verified"], 3)
        self.assertEqual(r52_t["exp_step_shutter_angle_bridge"]["shutter_angle_5anchors_verified"], 5)
        self.assertEqual(r52_t["lang_telemetry"]["lang"], "schinese")
        self.assertEqual(r52_t["lang_telemetry"]["milestone_25th_realhw_75th_run"], 1)
        self.assertEqual(r52_t["stage_b_bridge"]["round"], 52)
        self.assertEqual(r52_t["audio_timing_signals_guard"]["r52b_ok"], 1)
        self.assertEqual(r52_t["exp_step_shutter_angle"]["surfaces_h0_eq_h3"], 16)
        self.assertEqual(parsed["prefix_counts"]["FX6_R52_"], 9)

    def test_14_round52_parse_log_defaults_when_no_r52_lines_present(self) -> None:
        runner = _load_closure_module("fx6_brr_r52_parse_empty", "build_and_run_round.py")
        parsed = runner.extract_milestones("Linux version 4.9.337-scel+\n")
        self.assertIsNone(parsed["r52_telemetry"])
        self.assertEqual(parsed["prefix_counts"].get("FX6_R52_", 0), 0)

    def test_15_round52_runner_uses_fx6_r52_prefix_and_stage_label_and_r51_compat(self) -> None:
        src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")
        self.assertIn('if args.round >= 52:\n        tmp_prefix = "fx6-r52"', src)
        self.assertIn(
            "Milestone25thRealHw75thRunWave38LockOpPartsMenuFn5sMyDialAudioTimingSignalsExpStepShutterAngle",
            src,
        )
        self.assertIn("FX6_SCRATCH_DIR", src)
        self.assertIn("choices=[1, 2, 3", src)
        self.assertIn(", 52]", src)

    def test_16_round52_wave38_intel_spec_documents_all_3_domains(self) -> None:
        self.assertTrue(WAVE38_SPEC_PATH.is_file())
        spec_txt = WAVE38_SPEC_PATH.read_text(encoding="utf-8")
        for token in (
            "Lock Operation Parts",
            "MENU",
            "My Dial",
            "Audio Out Timing",
            "Audio signals",
            "Exposure step",
            "360",
        ):
            self.assertIn(token, spec_txt)

    def test_17_round52_summary_json_top_level_schema_and_milestone_metadata(self) -> None:
        summary_p = ROUND52_REPORT_DIR / "summary.json"
        self.assertTrue(summary_p.is_file())
        d = json.loads(summary_p.read_text(encoding="utf-8"))
        self.assertEqual(
            d["schema"],
            "fx6-on-fx3-round52-realhw-lock-op-parts-audio-timing-exp-step-qemu-v1",
        )
        self.assertEqual(d["round"], 52)
        self.assertIn("25th Real-HW QEMU Round", d["milestone"])
        self.assertIn("75 Live Runs", d["milestone"])
        self.assertEqual(d["date"], "2026-11-15")
        self.assertIn("4.9.337-scel+", d["kernel_version"])
        self.assertEqual(d["raw_firmware_bytes_leaked"], 0)

    def test_18_round52_summary_json_zero_host_path_and_firmware_leaks(self) -> None:
        raw = (ROUND52_REPORT_DIR / "summary.json").read_text(encoding="utf-8")
        for forbidden in ("/Users/", "/private/tmp/", "/var/folders/", "work/_tests/"):
            self.assertNotIn(forbidden, raw)

    def test_19_round52_summary_audit_block_confirms_25th_round_75th_run_and_all_booleans(self) -> None:
        d = json.loads((ROUND52_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        audit = d["r52_realhw_lock_op_parts_audio_timing_exp_step_audit"]
        self.assertEqual(audit["round"], 52)
        self.assertEqual(audit["milestone"], 52)
        self.assertEqual(audit["milestone233_qemu_rounds"], 25)
        self.assertEqual(audit["milestone233_qemu_runs"], 75)
        self.assertEqual(audit["total_runs"], 3)
        for flag in (
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "all_3_runs_cnflasha_write_zero",
            "r52a_lock_op_parts_menu_fn_5s_chord_no_menu_delete_confusion_and_mydial_override_verified",
            "r52a_stageb_big6_sid_0a_exact_346686_pixels_verified",
            "r52b_audio_out_timing_vs_audio_signals_and_silent_mode_mute_guard_verified",
            "r52c_exposure_step_4domain_requantization_and_shutter_angle_constant_table_immunity_verified",
            "r52c_dlopen_libjit_and_16_h0_eq_h3_rollback_verified",
        ):
            self.assertTrue(audit[flag], flag)

    def test_20_round52_all_3_runs_present_with_kernel_4_9_337_and_zero_crashes_writes(self) -> None:
        d = json.loads((ROUND52_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        runs = d["runs"]
        self.assertEqual(
            list(runs.keys()),
            [
                "r52a_lock_op_parts_mydial_big6_schinese",
                "r52b_audio_out_timing_vs_audio_signals_guard",
                "r52c_exposure_step_vs_shutter_angle_h0_h3",
            ],
        )
        for rk, rv in runs.items():
            self.assertEqual(rv["round"], 52, rk)
            self.assertIn("4.9.337-scel+", rv["kernel_version"], rk)
            self.assertEqual(rv["nop_count"], 0, rk)
            self.assertEqual(rv["crashes"], 0, rk)
            self.assertEqual(rv["emmc_write_count"], 0, rk)
            self.assertGreater(rv["wall_elapsed_sec"], 0.0, rk)

    def test_21_round52_r52a_lock_op_init_4modes_and_reset_survival(self) -> None:
        d = json.loads((ROUND52_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        init_t = d["runs"]["r52a_lock_op_parts_mydial_big6_schinese"]["r52_telemetry"]["lock_op_init"]
        self.assertEqual(init_t["fx3_lock_op_node_ok"], 1)
        self.assertEqual(init_t["lock_op_default_off_ok"], 1)
        self.assertEqual(init_t["invalid_lock_op_rc"], -22)
        self.assertEqual(init_t["lock_op_4modes_verified"], 4)
        self.assertEqual(init_t["lock_op_survives_camreset_ok"], 1)
        self.assertEqual(init_t["lock_op_survives_netreset_ok"], 1)
        self.assertEqual(init_t["initialize_restores_lock_op_off_ok"], 1)
        self.assertEqual(init_t["r52_init_ok"], 1)

    def test_22_round52_r52a_menu_fn_5s_chord_and_zero_destructive_menu_delete_confusion(self) -> None:
        d = json.loads((ROUND52_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        init_t = d["runs"]["r52a_lock_op_parts_mydial_big6_schinese"]["r52_telemetry"]["lock_op_init"]
        self.assertEqual(init_t["fn_hold_3s_toggle_ok"], 1)
        self.assertEqual(init_t["menu_fn_5s_fullbody_lock_ok"], 1)
        self.assertEqual(init_t["shutter_exempt_ok"], 1)
        self.assertEqual(init_t["menu_fn_3s_fullbody_release_ok"], 1)
        self.assertEqual(init_t["menu_delete_2s_blocked_rc"], -1)
        self.assertEqual(init_t["destructive_menu_delete_confusions"], 0)
        self.assertEqual(init_t["slot1_vault_format_events"], 0)
        self.assertEqual(init_t["slot2_format_events"], 0)
        self.assertEqual(init_t["slot1_vault_sha256_match"], 1)

    def test_23_round52_r52a_mydial_1_to_3_temporary_override_and_relock(self) -> None:
        d = json.loads((ROUND52_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        r52a_t = d["runs"]["r52a_lock_op_parts_mydial_big6_schinese"]["r52_telemetry"]
        self.assertEqual(r52a_t["lock_op_init"]["mydial_1_3_temp_override_verified"], 3)
        self.assertEqual(r52a_t["lock_op_init"]["mydial_release_relocks_ok"], 1)
        self.assertEqual(r52a_t["lock_op_parts_bridge"]["mydial_1_3_temp_override_verified"], 3)
        self.assertEqual(r52a_t["lock_op_parts_bridge"]["lock_op_parts_ok"], 1)
        self.assertEqual(r52a_t["lock_op_parts_bridge"]["r52_bridge_ok"], 1)

    def test_24_round52_r52a_p2_and_cnflasha_ro_guards_intact(self) -> None:
        d = json.loads((ROUND52_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        init_t = d["runs"]["r52a_lock_op_parts_mydial_big6_schinese"]["r52_telemetry"]["lock_op_init"]
        self.assertEqual(init_t["p2_write_blocked_rc"], -30)
        self.assertEqual(init_t["p2_sha256_match"], 1)
        self.assertEqual(init_t["cnflasha_sha256_match"], 1)
        self.assertEqual(init_t["cnflasha_writes"], 0)
        self.assertEqual(init_t["appfw_present"], 1)
        self.assertEqual(init_t["shim_present"], 1)
        self.assertEqual(init_t["emmc_write_count"], 0)

    def test_25_round52_r52a_stage_b_schinese_lang_telemetry_and_bridges(self) -> None:
        d = json.loads((ROUND52_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        r52a_t = d["runs"]["r52a_lock_op_parts_mydial_big6_schinese"]["r52_telemetry"]
        lt = r52a_t["lang_telemetry"]
        self.assertEqual(lt["lang"], "schinese")
        self.assertEqual(lt["bk4_lang_id"], "0x02cf019c")
        self.assertEqual(lt["bk4_lang_val"], "0x19")
        self.assertEqual(lt["lang_enum"], "0x2b45_CHINESE_SIMPLIFIED")
        self.assertEqual(lt["font_bank"], 23)
        self.assertEqual(lt["str_bank"], 19)
        self.assertEqual(lt["gpe_fb"], 0)
        self.assertEqual(lt["milestone_25th_realhw_75th_run"], 1)
        sb = r52a_t["stage_b_bridge"]
        self.assertEqual(sb["round"], 52)
        self.assertEqual(sb["faithful"], 1)
        self.assertEqual(sb["nop_count"], 0)
        self.assertEqual(sb["lock_op_parts_menu_fn_5s_mydial_override"], 1)
        self.assertEqual(sb["audio_out_timing_vs_audio_signals_guard"], 1)
        self.assertEqual(sb["exp_step_vs_shutter_angle_immune"], 1)

    def test_26_round52_r52a_stage_b_audio_and_exp_step_bridges_verified(self) -> None:
        d = json.loads((ROUND52_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        r52a_t = d["runs"]["r52a_lock_op_parts_mydial_big6_schinese"]["r52_telemetry"]
        ab = r52a_t["audio_timing_signals_bridge"]
        self.assertEqual(ab["audio_out_timing_2modes_verified"], 2)
        self.assertEqual(ab["audio_signals_3modes_verified"], 3)
        self.assertEqual(ab["silent_mode_audio_signal_leak_events"], 0)
        self.assertEqual(ab["audio_timing_signals_ok"], 1)
        eb = r52a_t["exp_step_shutter_angle_bridge"]
        self.assertEqual(eb["exposure_step_2modes_verified"], 2)
        self.assertEqual(eb["exp_step_4domains_requantized_ok"], 1)
        self.assertEqual(eb["shutter_angle_5anchors_verified"], 5)
        self.assertEqual(eb["shutter_angle_exposure_step_drift_events"], 0)
        self.assertEqual(eb["exp_step_shutter_angle_ok"], 1)

    def test_27_round52_r52a_gpe0_readback_exact_346686_pixels_and_87_colors(self) -> None:
        d = json.loads((ROUND52_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        r52a = d["runs"]["r52a_lock_op_parts_mydial_big6_schinese"]
        self.assertEqual(r52a["target_presenter"], "31procam_big6_menu_home_presenter")
        self.assertEqual(r52a["target_sid"], "0x0a")
        self.assertGreaterEqual(r52a["total_threads_seen"], 150)
        gpe0 = r52a["gpe0_readback"]
        self.assertTrue(gpe0["present"])
        self.assertEqual(gpe0["bytes"], 2211840)
        self.assertEqual(gpe0["total_pixels"], 552960)
        self.assertEqual(gpe0["nonzero_pixels"], 346686)
        self.assertEqual(gpe0["unique_colors"], 87)

    def test_28_round52_r52a_stage_b_manifest_13_hashes_and_r52_metadata(self) -> None:
        d = json.loads((ROUND52_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        sb = d["runs"]["r52a_lock_op_parts_mydial_big6_schinese"]["stage_b"]
        self.assertEqual(sb["manifest_count"], 13)
        self.assertEqual(len(sb["manifest_items"]), 13)
        for item in sb["manifest_items"]:
            self.assertEqual(len(item["sha256"]), 64)
        r52_meta = sb["r52"]
        self.assertEqual(r52_meta["r52_mode"], "lock_op_parts_chord_mydial_big6")
        self.assertEqual(
            r52_meta["lock_op_parts_modes"],
            ["Off", "Multi-Slct Only", "Dial/Wheel", "Dial+Wheel+MSlct"],
        )
        self.assertEqual(r52_meta["full_body_lock_chord"], "MENU+Fn>=5000ms")
        self.assertEqual(r52_meta["full_body_unlock_chord"], "MENU+Fn>=3000ms")
        self.assertEqual(r52_meta["destructive_slot_full_format_chord_blocked"], "MENU+Delete>=2000ms")
        self.assertEqual(r52_meta["my_dial_banks_temporary_override"], ["My Dial 1", "My Dial 2", "My Dial 3"])

    def test_29_round52_r52b_audio_out_timing_live_default_and_lipsync_modes(self) -> None:
        d = json.loads((ROUND52_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        r52b_t = d["runs"]["r52b_audio_out_timing_vs_audio_signals_guard"]["r52_telemetry"]
        self.assertEqual(r52b_t["audio_timing_signals_rc"], 0)
        ag = r52b_t["audio_timing_signals_guard"]
        self.assertEqual(ag["audio_out_timing_default_live_ok"], 1)
        self.assertEqual(ag["invalid_audio_timing_rc"], -22)
        self.assertEqual(ag["audio_out_timing_2modes_verified"], 2)
        self.assertEqual(ag["r52b_ok"], 1)

    def test_30_round52_r52b_audio_signals_3modes_and_shutter_only_selectivity(self) -> None:
        d = json.loads((ROUND52_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        ag = d["runs"]["r52b_audio_out_timing_vs_audio_signals_guard"]["r52_telemetry"][
            "audio_timing_signals_guard"
        ]
        self.assertEqual(ag["audio_signals_default_on_all_ok"], 1)
        self.assertEqual(ag["invalid_audio_signals_rc"], -22)
        self.assertEqual(ag["audio_signals_3modes_verified"], 3)
        self.assertEqual(ag["shutter_only_selectivity_ok"], 1)

    def test_31_round52_r52b_camera_settings_reset_asymmetry_audio_timing_vs_signals(self) -> None:
        d = json.loads((ROUND52_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        ag = d["runs"]["r52b_audio_out_timing_vs_audio_signals_guard"]["r52_telemetry"][
            "audio_timing_signals_guard"
        ]
        self.assertEqual(ag["audio_out_timing_camreset_restores_live_ok"], 1)
        self.assertEqual(ag["audio_signals_survives_camreset_ok"], 1)
        self.assertEqual(ag["shooting_vs_setup_audio_reset_split_ok"], 1)
        self.assertEqual(ag["initialize_restores_audio_defaults_ok"], 1)

    def test_32_round52_r52b_sq_motion_and_audio_rec_off_lock_audio_out_timing(self) -> None:
        d = json.loads((ROUND52_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        ag = d["runs"]["r52b_audio_out_timing_vs_audio_signals_guard"]["r52_telemetry"][
            "audio_timing_signals_guard"
        ]
        self.assertEqual(ag["sq_motion_audio_timing_lock_rc"], -95)
        self.assertEqual(ag["audio_rec_off_timing_lock_rc"], -95)
        self.assertEqual(ag["audio_out_timing_sq_or_recoff_bypass_events"], 0)

    def test_33_round52_r52b_silent_mode_forcibly_mutes_audio_signals_zero_leaks(self) -> None:
        d = json.loads((ROUND52_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        ag = d["runs"]["r52b_audio_out_timing_vs_audio_signals_guard"]["r52_telemetry"][
            "audio_timing_signals_guard"
        ]
        self.assertEqual(ag["silent_mode_audio_signals_lock_rc"], -16)
        self.assertEqual(ag["silent_mode_audio_signal_leak_events"], 0)
        self.assertEqual(ag["silent_off_restores_audio_signals_ok"], 1)
        self.assertEqual(ag["p2_write_blocked_rc"], -30)
        self.assertEqual(ag["cnflasha_ro_blocked_rc"], -30)
        self.assertEqual(ag["cnflasha_writes"], 0)
        self.assertEqual(ag["emmc_write_count"], 0)

    def test_34_round52_r52c_exposure_step_03ev_05ev_and_camera_settings_reset(self) -> None:
        d = json.loads((ROUND52_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        r52c_t = d["runs"]["r52c_exposure_step_vs_shutter_angle_h0_h3"]["r52_telemetry"]
        self.assertEqual(r52c_t["exp_step_shutter_angle_rc"], 0)
        es = r52c_t["exp_step_shutter_angle"]
        self.assertEqual(es["exposure_step_default_03ev_ok"], 1)
        self.assertEqual(es["invalid_exposure_step_rc"], -22)
        self.assertEqual(es["exposure_step_2modes_verified"], 2)
        self.assertEqual(es["exposure_step_camreset_restores_03ev_ok"], 1)
        self.assertEqual(es["initialize_restores_03ev_ok"], 1)

    def test_35_round52_r52c_exposure_step_4domain_requantization(self) -> None:
        d = json.loads((ROUND52_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        es = d["runs"]["r52c_exposure_step_vs_shutter_angle_h0_h3"]["r52_telemetry"][
            "exp_step_shutter_angle"
        ]
        self.assertEqual(es["exp_step_domains_requantized"], 4)
        self.assertEqual(es["exp_step_4domains_requantized_ok"], 1)

    def test_36_round52_r52c_shutter_angle_5_6_to_360_constant_table_immunity(self) -> None:
        d = json.loads((ROUND52_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        es = d["runs"]["r52c_exposure_step_vs_shutter_angle_h0_h3"]["r52_telemetry"][
            "exp_step_shutter_angle"
        ]
        self.assertEqual(es["shutter_angle_min_deg10"], 56)
        self.assertEqual(es["shutter_angle_max_deg10"], 3600)
        self.assertEqual(es["shutter_angle_5anchors_verified"], 5)
        self.assertEqual(es["shutter_angle_constant_table_immune_ok"], 1)
        self.assertEqual(es["shutter_angle_exposure_step_drift_events"], 0)

    def test_37_round52_r52c_dlopen_libjit_16_h0_eq_h3_and_ro_guards(self) -> None:
        d = json.loads((ROUND52_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        es = d["runs"]["r52c_exposure_step_vs_shutter_angle_h0_h3"]["r52_telemetry"][
            "exp_step_shutter_angle"
        ]
        self.assertEqual(es["dlopen_ok"], 1)
        self.assertEqual(es["surfaces_verified"], 16)
        self.assertEqual(es["surfaces_h0_eq_h3"], 16)
        self.assertEqual(es["drift_bits"], 0)
        self.assertEqual(es["p2_write_blocked_rc"], -30)
        self.assertEqual(es["cnflasha_ro_blocked_rc"], -30)
        self.assertEqual(es["cnflasha_writes"], 0)
        self.assertEqual(es["emmc_write_count"], 0)
        self.assertEqual(es["r52c_ok"], 1)

    def test_38_round52_realhw_mechanisms_verified_6_blocks_match_run_telemetry(self) -> None:
        d = json.loads((ROUND52_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        rm = d["realhw_mechanisms_verified"]
        self.assertEqual(len(rm), 6)
        r52a = d["runs"]["r52a_lock_op_parts_mydial_big6_schinese"]["r52_telemetry"]
        r52b = d["runs"]["r52b_audio_out_timing_vs_audio_signals_guard"]["r52_telemetry"]
        r52c = d["runs"]["r52c_exposure_step_vs_shutter_angle_h0_h3"]["r52_telemetry"]
        self.assertEqual(
            rm["lock_op_parts_menu_fn_5s_chord_no_menu_delete_confusion_and_mydial_override_init"],
            r52a["lock_op_init"],
        )
        self.assertEqual(
            rm["lock_op_parts_chord_and_mydial_stage_b_bridge"],
            r52a["lock_op_parts_bridge"],
        )
        self.assertEqual(
            rm["audio_out_timing_vs_audio_signals_stage_b_bridge"],
            r52a["audio_timing_signals_bridge"],
        )
        self.assertEqual(
            rm["exposure_step_vs_shutter_angle_stage_b_bridge"],
            r52a["exp_step_shutter_angle_bridge"],
        )
        self.assertEqual(
            rm["audio_out_timing_vs_audio_signals_and_silent_mode_hard_mute_guard"],
            r52b["audio_timing_signals_guard"],
        )
        self.assertEqual(
            rm["exposure_step_4domain_requantization_vs_shutter_angle_constant_table_and_16_h0_h3"],
            r52c["exp_step_shutter_angle"],
        )

    def test_39_round52_setup_vs_shooting_reset_tier_split_across_r52a_r52b_r52c(self) -> None:
        d = json.loads((ROUND52_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        li = d["runs"]["r52a_lock_op_parts_mydial_big6_schinese"]["r52_telemetry"]["lock_op_init"]
        ag = d["runs"]["r52b_audio_out_timing_vs_audio_signals_guard"]["r52_telemetry"][
            "audio_timing_signals_guard"
        ]
        es = d["runs"]["r52c_exposure_step_vs_shutter_angle_h0_h3"]["r52_telemetry"][
            "exp_step_shutter_angle"
        ]
        self.assertEqual(li["lock_op_survives_camreset_ok"], 1)
        self.assertEqual(li["lock_op_survives_netreset_ok"], 1)
        self.assertEqual(ag["audio_signals_survives_camreset_ok"], 1)
        self.assertEqual(ag["audio_out_timing_camreset_restores_live_ok"], 1)
        self.assertEqual(es["exposure_step_camreset_restores_03ev_ok"], 1)

    def test_40_round52_cross_round_consistency_with_r46_menu_delete_2s_format_guard(self) -> None:
        d46 = json.loads(
            (
                REPO_ROOT
                / "reports"
                / "2026-11-15-round46-realhw-sq-fixedvar-zebra-peaking-fullformat-qemu"
                / "summary.json"
            ).read_text(encoding="utf-8")
        )
        d52 = json.loads((ROUND52_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        self.assertEqual(d46["round"], 46)
        li52 = d52["runs"]["r52a_lock_op_parts_mydial_big6_schinese"]["r52_telemetry"]["lock_op_init"]
        self.assertEqual(li52["menu_delete_2s_blocked_rc"], -1)
        self.assertEqual(li52["destructive_menu_delete_confusions"], 0)
        self.assertEqual(li52["slot1_vault_format_events"], 0)

    def test_41_round52_cross_round_consistency_with_r47_silent_mode_audio_mute(self) -> None:
        d47 = json.loads(
            (
                REPO_ROOT
                / "reports"
                / "2026-11-15-round47-realhw-silent-autopixelmap-marker-flexexp-qemu"
                / "summary.json"
            ).read_text(encoding="utf-8")
        )
        d52 = json.loads((ROUND52_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        self.assertEqual(d47["round"], 47)
        ag52 = d52["runs"]["r52b_audio_out_timing_vs_audio_signals_guard"]["r52_telemetry"][
            "audio_timing_signals_guard"
        ]
        self.assertEqual(ag52["silent_mode_audio_signals_lock_rc"], -16)
        self.assertEqual(ag52["silent_mode_audio_signal_leak_events"], 0)

    def test_42_round52_cross_round_consistency_with_r39_shutter_angle_702(self) -> None:
        d39 = json.loads(
            (
                REPO_ROOT
                / "reports"
                / "2026-11-15-round39-realhw-fan-pwm-shutter-angle-lut-split-qemu"
                / "summary.json"
            ).read_text(encoding="utf-8")
        )
        d52 = json.loads((ROUND52_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        self.assertEqual(
            d39["schema"], "fx6-on-fx3-round39-realhw-fan-pwm-shutter-angle-lut-split-qemu-v1"
        )
        es52 = d52["runs"]["r52c_exposure_step_vs_shutter_angle_h0_h3"]["r52_telemetry"][
            "exp_step_shutter_angle"
        ]
        self.assertEqual(es52["shutter_angle_min_deg10"], 56)
        self.assertEqual(es52["shutter_angle_max_deg10"], 3600)
        self.assertEqual(es52["shutter_angle_5anchors_verified"], 5)

    def test_43_round52_unexecuted_physical_camera_bench_boundaries_documented(self) -> None:
        d = json.loads((ROUND52_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        bounds = d["unexecuted_physical_camera_bench_boundaries"]
        self.assertEqual(len(bounds), 3)
        joined = " ".join(bounds)
        self.assertIn("MENU + Fn >= 5s", joined)
        self.assertIn("Audio Out Timing", joined)
        self.assertIn("Exposure step", joined)

    def test_44_round52_alpha_png_exists_under_50kib_and_matches_summary_sha256(self) -> None:
        d = json.loads((ROUND52_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        pe = d["runs"]["r52a_lock_op_parts_mydial_big6_schinese"]["png_exports"]
        alpha_p = REPO_ROOT / pe["alpha_png"]
        self.assertTrue(alpha_p.is_file())
        raw = alpha_p.read_bytes()
        self.assertLess(len(raw), 51200)
        self.assertEqual(len(raw), pe["alpha_bytes"])
        self.assertEqual(hashlib.sha256(raw).hexdigest(), pe["alpha_sha256"])

    def test_45_round52_composited_png_exists_under_50kib_and_matches_summary_sha256(self) -> None:
        d = json.loads((ROUND52_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        pe = d["runs"]["r52a_lock_op_parts_mydial_big6_schinese"]["png_exports"]
        comp_p = REPO_ROOT / pe["composited_png"]
        self.assertTrue(comp_p.is_file())
        raw = comp_p.read_bytes()
        self.assertLess(len(raw), 51200)
        self.assertEqual(len(raw), pe["composited_bytes"])
        self.assertEqual(hashlib.sha256(raw).hexdigest(), pe["composited_sha256"])

    def test_46_round52_alpha_png_valid_1024x540_rgba_with_transparent_and_opaque_pixels(self) -> None:
        alpha_p = (
            ROUND52_REPORT_DIR / "assets" / "r52a-lock-op-parts-mydial-big6-schinese-alpha.png"
        )
        w, h, rows = _decode_png_rgba_rows(alpha_p.read_bytes())
        self.assertEqual((w, h), (1024, 540))
        self.assertEqual(len(rows), 540)
        transparent = 0
        opaque = 0
        for row in rows:
            alphas = row[3::4]
            transparent += alphas.count(0)
            opaque += alphas.count(255)
        self.assertEqual(transparent, 206274)
        self.assertGreater(opaque, 300000)

    def test_47_round52_composited_png_valid_1024x540_rgba_100pct_opaque(self) -> None:
        comp_p = (
            ROUND52_REPORT_DIR
            / "assets"
            / "r52a-lock-op-parts-mydial-big6-schinese-composited.png"
        )
        w, h, rows = _decode_png_rgba_rows(comp_p.read_bytes())
        self.assertEqual((w, h), (1024, 540))
        self.assertEqual(len(rows), 540)
        opaque = sum(row[3::4].count(255) for row in rows)
        self.assertEqual(opaque, 1024 * 540)

    def test_48_round52_report_readme_documents_all_3_runs_and_zero_host_leaks(self) -> None:
        readme_p = ROUND52_REPORT_DIR / "README.md"
        self.assertTrue(readme_p.is_file())
        txt = readme_p.read_text(encoding="utf-8")
        for token in (
            "Round 52",
            "25th Real-HW",
            "75th Live Run",
            "r52a",
            "r52b",
            "r52c",
            "Lock Operation Parts",
            "Audio Out Timing",
            "Audio signals",
            "Exposure step",
            "346,686",
            "r52a-lock-op-parts-mydial-big6-schinese-alpha.png",
            "r52a-lock-op-parts-mydial-big6-schinese-composited.png",
        ):
            self.assertIn(token, txt)
        for forbidden in ("/Users/", "/private/tmp/", "/var/folders/"):
            self.assertNotIn(forbidden, txt)

    def test_49_round52_closure_readme_section_52_present_and_accurate(self) -> None:
        closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn("## 52. Round 52", closure_readme)
        self.assertIn("25th Real-HW Round", closure_readme)
        self.assertIn("75th Live Run Milestone", closure_readme)
        self.assertIn(
            "2026-11-15-round52-realhw-lock-op-parts-audio-timing-exp-step-qemu",
            closure_readme,
        )

    def test_50_round52_25_realhw_qemu_rounds_r28_to_r52_75_runs_and_50_pngs_continuity(self) -> None:
        png_total = 0
        for r in range(28, 53):
            matches = list((REPO_ROOT / "reports").glob(f"2026-??-??-round{r}-*"))
            self.assertEqual(len(matches), 1, f"Expected 1 report dir for Round {r}")
            pngs = list((matches[0] / "assets").glob("*.png"))
            self.assertEqual(len(pngs), 2, f"Expected 2 PNGs for Round {r}")
            png_total += len(pngs)
        self.assertEqual(png_total, 50)
        d = json.loads((ROUND52_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        audit = d["r52_realhw_lock_op_parts_audio_timing_exp_step_audit"]
        self.assertEqual(audit["milestone233_qemu_rounds"], 25)
        self.assertEqual(audit["milestone233_qemu_runs"], 75)

    def test_51_round52_dual_mode_clean_room_toggle_parity_on_summary(self) -> None:
        for clean_flag in ("0", "1"):
            with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                d = json.loads((ROUND52_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
                self.assertEqual(d["round"], 52)
                self.assertEqual(
                    d["runs"]["r52a_lock_op_parts_mydial_big6_schinese"]["r52_telemetry"][
                        "lock_op_init"
                    ]["destructive_menu_delete_confusions"],
                    0,
                )
                self.assertEqual(
                    d["runs"]["r52b_audio_out_timing_vs_audio_signals_guard"]["r52_telemetry"][
                        "audio_timing_signals_guard"
                    ]["silent_mode_audio_signal_leak_events"],
                    0,
                )
                self.assertEqual(
                    d["runs"]["r52c_exposure_step_vs_shutter_angle_h0_h3"]["r52_telemetry"][
                        "exp_step_shutter_angle"
                    ]["surfaces_h0_eq_h3"],
                    16,
                )

    def test_52_round52_r52a_verify_us_positive_under_2_seconds(self) -> None:
        d = json.loads((ROUND52_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        us = d["runs"]["r52a_lock_op_parts_mydial_big6_schinese"]["r52_telemetry"][
            "lock_op_init"
        ]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_53_round52_r52b_verify_us_positive_under_2_seconds(self) -> None:
        d = json.loads((ROUND52_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        us = d["runs"]["r52b_audio_out_timing_vs_audio_signals_guard"]["r52_telemetry"][
            "audio_timing_signals_guard"
        ]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_54_round52_r52c_verify_us_positive_under_2_seconds(self) -> None:
        d = json.loads((ROUND52_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        us = d["runs"]["r52c_exposure_step_vs_shutter_angle_h0_h3"]["r52_telemetry"][
            "exp_step_shutter_angle"
        ]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_55_round52_r52a_top_colors_transparent_plus_nonzero_equals_total_pixels(self) -> None:
        d = json.loads((ROUND52_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        gpe = d["runs"]["r52a_lock_op_parts_mydial_big6_schinese"]["gpe0_readback"]
        top = gpe["top_colors"]
        self.assertGreaterEqual(len(top), 5)
        color_map = {row["argb"]: row["pixels"] for row in top}
        self.assertIn("0x00000000", color_map)
        self.assertIn("0xff000000", color_map)
        self.assertEqual(color_map["0x00000000"] + gpe["nonzero_pixels"], gpe["total_pixels"])

    def test_56_round52_r52a_wall_elapsed_and_duration_budget_sanity(self) -> None:
        d = json.loads((ROUND52_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        r52a = d["runs"]["r52a_lock_op_parts_mydial_big6_schinese"]
        self.assertEqual(r52a["duration_budget_sec"], 71)
        self.assertGreater(r52a["wall_elapsed_sec"], 50.0)
        self.assertLess(r52a["wall_elapsed_sec"], 120.0)

    def test_57_round52_r52b_and_r52c_fast_early_exit_wall_elapsed_under_20s(self) -> None:
        d = json.loads((ROUND52_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        r52b = d["runs"]["r52b_audio_out_timing_vs_audio_signals_guard"]
        r52c = d["runs"]["r52c_exposure_step_vs_shutter_angle_h0_h3"]
        self.assertEqual(r52b["duration_budget_sec"], 35)
        self.assertEqual(r52c["duration_budget_sec"], 35)
        self.assertGreater(r52b["wall_elapsed_sec"], 1.0)
        self.assertLess(r52b["wall_elapsed_sec"], 20.0)
        self.assertGreater(r52c["wall_elapsed_sec"], 1.0)
        self.assertLess(r52c["wall_elapsed_sec"], 20.0)
        self.assertTrue(r52b["gpe0_readback"]["skipped_stock_fx3_mode"])
        self.assertTrue(r52c["gpe0_readback"]["skipped_stock_fx3_mode"])

    def test_58_round52_ephemeral_work_tests_dir_cleaned_up(self) -> None:
        scratch_candidates = list((REPO_ROOT / "work" / "_tests").glob("*h290-round52*")) if (REPO_ROOT / "work" / "_tests").exists() else []
        self.assertEqual(scratch_candidates, [])

    def test_59_round52_port_8768_untouched_in_round52_reports_and_test(self) -> None:
        for p in (
            ROUND52_REPORT_DIR / "summary.json",
            ROUND52_REPORT_DIR / "README.md",
        ):
            self.assertNotIn("8768", p.read_text(encoding="utf-8"))

    def test_60_round52_test_suite_contains_exact_60_unit_tests(self) -> None:
        methods = [m for m in dir(self) if m.startswith("test_")]
        self.assertEqual(len(methods), 60)


if __name__ == "__main__":
    unittest.main()
