#!/usr/bin/env python3
"""Offline dual-mode unit tests for FX6-on-FX3 Round 43 (Live FX3 7.02 QEMU Rehearsal)."""
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
ROUND43_REPORT_DIR = (
    REPO_ROOT
    / "reports"
    / "2026-11-15-round43-realhw-filesettings-shotmark-tcregen-reclamp-qemu"
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


def _build_overlay_for_r43(runner, tmp_dir: pathlib.Path, work: pathlib.Path, r43_mode: str, lang: str = "schinese"):
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
            enable_r43=True, r43_mode=r43_mode,
            sd_manifest_mode="valid", lang=lang, shim_bytes=b"SHIM",
        )


class TestRound43RealHwFileSettingsShotMarkTcRegenRecLamp(unittest.TestCase):
    EXPECTED_RUN_KEYS = (
        "r43a_filesettings_shotmark_big6_schinese",
        "r43b_tc_regenerate_slot1_extlk",
        "r43c_reclamp_coupled_tally_h0_h3",
    )

    def test_01_round43_c_and_python_source_contracts(self) -> None:
        shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")

        self.assertIn("#if FX6_ROUND >= 43", shim_src)
        for token in (
            "FX6_R43_FILESETTINGS_SHOTMARK_BRIDGE",
            "FX6_R43_TC_REGENERATE_BRIDGE",
            "FX6_R43_RECLAMP_SILENT_BRIDGE",
            "FX6_R43_LANG_TELEMETRY",
            "FX6_STAGE_B_R43_BRIDGE",
            "round43_realhw_filesettings_shotmark_tcregen_reclamp=1",
        ):
            self.assertIn(token, shim_src)

        for token in (
            "r43_is_allowed_title_char",
            "r43_set_title_name",
            "r43_set_file_name_format",
            "r43_customize_movie_folder",
            "r43_record_clip_with_shotmarks",
            "r43_playback_toggle_shotmark",
            "r43_eval_image_jump_and_ftp",
            "setup_r43_filesettings_shotmark_probe",
            "r43_tc_engage_ext_lk",
            "r43_tc_set_make",
            "r43_tc_set_run",
            "r43_tc_set_hdmi_output",
            "r43_tc_resolve_start_frames",
            "run_r43_tc_regenerate_probe",
            "r43_set_rec_lamp_mode",
            "r43_eval_rec_lamp_and_hdmi_tally",
            "r43_set_silent_mode",
            "r43_set_audio_signals",
            "run_r43_reclamp_silent_probe",
            "--r43-tc-regenerate",
            "--r43-reclamp-silent",
            "/etc/fx6_stage_r43",
            "FX6_R43_FILESETTINGS_SHOTMARK_INIT",
            "FX6_R43_TC_REGENERATE",
            "FX6_R43_RECLAMP_SILENT",
        ):
            self.assertIn(token, verify_src)

        for token in (
            "enable_r43",
            "r43_mode",
            "--r43-mode",
            "filesettings_shotmark_big6",
            "tc_regenerate_slot1_extlk",
            "reclamp_coupled_tally_h0_h3",
            "etc/fx6_stage_r43",
            "FX6_R43_TC_REGENERATE_EXIT",
            "FX6_R43_RECLAMP_SILENT_EXIT",
            '"r43_telemetry"',
            "choices=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47]",
        ):
            self.assertIn(token, runner_src)

    def test_02_round43_native_verify_c_compiles_with_zig_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r43_verc", "build_and_run_round.py")
        if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1" and not runner.ZIG.is_file():
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertTrue(runner.ZIG.is_file(), f"Missing zig compiler at {runner.ZIG}")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            cache_dir = tmp_dir / "zig-cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            for clean_flag in ("0", "1"):
                out_bin = tmp_dir / f"fx6-stage-a-verify-r43-{clean_flag}"
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

    def test_03_round43_build_binaries_compiles_shim_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r43_shimc", "build_and_run_round.py")
        if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1" and not runner.ZIG.is_file():
            self.skipTest("Clean-room fallback without local zig binary")
        with tempfile.TemporaryDirectory() as tmp:
            for clean_flag in ("0", "1"):
                work = pathlib.Path(tmp) / f"shim_{clean_flag}"
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                    launcher_b, shim_b, meta = runner.build_binaries(
                        work,
                        fx6_round=43,
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

    def test_04_round43_extract_milestones_r43a_filesettings_shotmark_and_bridges(self) -> None:
        runner = _load_closure_module("fx6_brr_r43_msa", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R43_FILESETTINGS_SHOTMARK_INIT fnf_5modes_verified=5 invalid_fnf_mode_reject_rc=-22 title_37char_max_ok=1 title_38char_reject_rc=-22 title_illegal_char_reject_rc=-22 prior_clip_untouched_ok=1 series_persist_ok=1 reset_per_card_ok=1 sdhc_forces_standard_ok=1 sdhc_non_standard_reject_rc=-22 custom_movie_folder_reject_rc=-1 shotmark_rec_pb_xml_ok=1 image_jump_4modes_ok=4 invalid_jump_reject_rc=-22 ftp_only_shotmark_mov=3 ftp_only_shotmark_filter_ok=1 appfw_present=1 shim_present=1 emmc_write_count=0 r43_init_ok=1 verify_us=788992",
                "FX6_R43_FILESETTINGS_SHOTMARK_BRIDGE fnf_5modes_verified=5 title_37char_max_ok=1 title_38char_reject_rc=-22 sdhc_forces_standard=1 custom_folder_reject_rc=-1 shotmark_xml_jump_ftp_ok=1 filesettings_shotmark_ok=1 emmc_write_count=0 r43_bridge_ok=1",
                "FX6_R43_TC_REGENERATE_BRIDGE simult_slot1_master_read=1 regen_forced_rec_run=1 ext_lk_released_on_regen_or_run=1 sq_tc_run_reject_rc=-95 sq_hdmi_tc_output_reject_rc=-95 tc_regenerate_ok=1 emmc_write_count=0 p2_setting_writes=0",
                "FX6_R43_RECLAMP_SILENT_BRIDGE reclamp_3states_verified=3 only_front_off_rear_top_coupled=1 uncoupled_split_reject_rc=-22 emphasized_rec_hdmi_independent=1 silent_forces_audio_signals_off=1 audio_signals_locked_rc=-16 reclamp_silent_ok=1 emmc_write_count=0",
                "FX6_STAGE_B_R43_BRIDGE round=43 faithful=1 nop_count=0 p12_wlan=1 wf12_00342260_immune=1 p10_keymap=1 p4_nd_clear=1 p11_xlr_h1=1 lang=schinese bk4_lang=0x19 enum=0x2b45_CHINESE_SIMPLIFIED font_bank=23 str_bank=19 filesettings_37char_sdhc_shotmark=1 tc_regenerate_slot1_extlk_release=1 reclamp_coupled_rear_top_silent_lock=1 emmc_write_count=0",
                "FX6_R43_LANG_TELEMETRY reason=gpermDrawFlush lang=schinese bk4_lang_id=0x02cf019c bk4_lang_val=0x19 gpe_fb=0 filesettings_shotmark_ok=1 tc_regenerate_ok=1 reclamp_silent_ok=1 r43_bridge_ok=1 round43_realhw_filesettings_shotmark_tcregen_reclamp=1 emmc_write_count=0 subst_color=0 subst_image=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        r43 = ms["r43_telemetry"]
        self.assertIsNotNone(r43)
        self.assertEqual(r43["filesettings_shotmark_init"]["fnf_5modes_verified"], 5)
        self.assertEqual(r43["filesettings_shotmark_init"]["title_37char_max_ok"], 1)
        self.assertEqual(r43["filesettings_shotmark_init"]["sdhc_forces_standard_ok"], 1)
        self.assertEqual(r43["filesettings_shotmark_init"]["r43_init_ok"], 1)
        self.assertEqual(r43["filesettings_shotmark_bridge"]["r43_bridge_ok"], 1)
        self.assertEqual(r43["tc_regenerate_bridge"]["tc_regenerate_ok"], 1)
        self.assertEqual(r43["reclamp_silent_bridge"]["reclamp_silent_ok"], 1)
        self.assertEqual(r43["stage_b_bridge"]["round"], 43)
        self.assertEqual(r43["lang_telemetry"]["gpe_fb"], 0)

    def test_05_round43_extract_milestones_r43b_tc_regenerate(self) -> None:
        runner = _load_closure_module("fx6_brr_r43_msb", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R43_TC_REGENERATE hdmi_tc_output_default_off=1 regen_single_slot1_ok=1 regen_single_slot2_ok=1 simult_reads_slot1_only_ok=1 simult_slot2_ignored=1 standby_ticks_advanced=0 rec_ticks_advanced=24 regen_forced_rec_run_ok=1 ext_lk_locked_ok=1 ext_lk_dropped_on_regen=1 ext_lk_active_after_regen=0 ext_lk_dropped_on_tc_run_change=1 ext_lk_reject_when_regen_rc=-22 movie_hdmi_tc_out_on_rc=0 invalid_hdmi_tc_out_rc=-22 sq_tc_run_reject_rc=-95 sq_hdmi_tc_output_reject_rc=-95 p2_write_blocked_rc=-30 p2_setting_sha256_match=1 appfw_ok=1 shim_elf_ok=1 emmc_write_count=0 r43b_ok=1 verify_us=679276",
                "FX6_R43_TC_REGENERATE_RC=0",
                "FX6_R43_TC_REGENERATE_EXIT rc=0 emmc_write_count=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        r43 = ms["r43_telemetry"]
        self.assertIsNotNone(r43)
        self.assertEqual(r43["tc_regenerate_rc"], 0)
        b = r43["tc_regenerate"]
        self.assertEqual(b["simult_reads_slot1_only_ok"], 1)
        self.assertEqual(b["simult_slot2_ignored"], 1)
        self.assertEqual(b["regen_forced_rec_run_ok"], 1)
        self.assertEqual(b["ext_lk_dropped_on_regen"], 1)
        self.assertEqual(b["ext_lk_dropped_on_tc_run_change"], 1)
        self.assertEqual(b["sq_tc_run_reject_rc"], -95)
        self.assertEqual(b["sq_hdmi_tc_output_reject_rc"], -95)
        self.assertEqual(b["r43b_ok"], 1)

    def test_06_round43_extract_milestones_r43c_reclamp_silent(self) -> None:
        runner = _load_closure_module("fx6_brr_r43_msc", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R43_RECLAMP_SILENT standby_leds_off_ok=1 reclamp_all_on_111_ok=1 only_front_off_011_coupled_ok=1 reclamp_all_off_000_ok=1 emphasized_rec_hdmi_independent_ok=1 uncoupled_split_reject_rc=-22 silent_forces_audio_signals_off=1 audio_signals_locked_while_silent_rc=-16 audio_signals_restored_when_silent_off=1 p2_write_blocked_rc=-30 dlopen_ok=1 surfaces_verified=16 surfaces_h0_eq_h3=16 drift_bits=0 emmc_write_count=0 r43c_ok=1 verify_us=5097",
                "FX6_R43_RECLAMP_SILENT_RC=0",
                "FX6_R43_RECLAMP_SILENT_EXIT rc=0 emmc_write_count=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        r43 = ms["r43_telemetry"]
        self.assertIsNotNone(r43)
        self.assertEqual(r43["reclamp_silent_rc"], 0)
        c = r43["reclamp_silent"]
        self.assertEqual(c["only_front_off_011_coupled_ok"], 1)
        self.assertEqual(c["emphasized_rec_hdmi_independent_ok"], 1)
        self.assertEqual(c["uncoupled_split_reject_rc"], -22)
        self.assertEqual(c["silent_forces_audio_signals_off"], 1)
        self.assertEqual(c["audio_signals_locked_while_silent_rc"], -16)
        self.assertEqual(c["surfaces_h0_eq_h3"], 16)
        self.assertEqual(c["drift_bits"], 0)
        self.assertEqual(c["r43c_ok"], 1)

    def test_07_round43_stage_a_overlay_r43a_filesettings_shotmark_mocked_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r43_ovl_a", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            for clean_flag in ("0", "1"):
                work = tmp_dir / f"r43_a_{clean_flag}"
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                    rep, add, meta = _build_overlay_for_r43(
                        runner, tmp_dir, work, "filesettings_shotmark_big6", lang="schinese"
                    )
                init_out = rep["init"].decode("utf-8")
                self.assertNotIn("--r43-tc-regenerate", init_out)
                self.assertNotIn("--r43-reclamp-silent", init_out)
                self.assertIn("--sd-gate", init_out)
                self.assertIn("etc/fx6_stage_r43", add)
                self.assertIn("r43_mode=filesettings_shotmark_big6", add["etc/fx6_stage_r43"][0].decode("utf-8"))
                self.assertTrue(meta["r43_enabled"])
                self.assertEqual(meta["r43"]["r43_mode"], "filesettings_shotmark_big6")
                self.assertEqual(len(meta["r43"]["file_name_formats"]), 5)
                self.assertEqual(meta["r43"]["title_name_max_ascii_chars"], 37)
                self.assertEqual(meta["r43"]["sdhc_fat32_forced_format"], "Standard")
                self.assertEqual(meta["r43"]["custom_movie_folder_reject_rc"], -1)

    def test_08_round43_stage_a_overlay_r43b_tc_regenerate_mocked_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r43_ovl_b", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            for clean_flag in ("0", "1"):
                work = tmp_dir / f"r43_b_{clean_flag}"
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                    rep, _, meta = _build_overlay_for_r43(
                        runner, tmp_dir, work, "tc_regenerate_slot1_extlk", lang="en"
                    )
                init_out = rep["init"].decode("utf-8")
                self.assertIn("/usr/bin/fx6-stage-a-verify --r43-tc-regenerate", init_out)
                self.assertIn("FX6_R43_TC_REGENERATE_EXIT", init_out)
                self.assertEqual(meta["r43"]["r43_mode"], "tc_regenerate_slot1_extlk")
                self.assertEqual(meta["r43"]["tc_regenerate_simult_source"], "Slot 1")
                self.assertEqual(meta["r43"]["tc_regenerate_forced_run_mode"], "Rec Run")
                self.assertTrue(meta["r43"]["ext_lk_drops_on_tc_make_or_run_change"])
                self.assertEqual(meta["r43"]["sq_hdmi_tc_output_reject_rc"], -95)

    def test_09_round43_stage_a_overlay_r43c_reclamp_silent_mocked_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r43_ovl_c", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            for clean_flag in ("0", "1"):
                work = tmp_dir / f"r43_c_{clean_flag}"
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                    rep, _, meta = _build_overlay_for_r43(
                        runner, tmp_dir, work, "reclamp_coupled_tally_h0_h3", lang="en"
                    )
                init_out = rep["init"].decode("utf-8")
                self.assertIn("/usr/bin/fx6-stage-a-verify --r43-reclamp-silent", init_out)
                self.assertIn("FX6_R43_RECLAMP_SILENT_EXIT", init_out)
                self.assertEqual(meta["r43"]["r43_mode"], "reclamp_coupled_tally_h0_h3")
                self.assertEqual(meta["r43"]["rec_lamp_states"], ["All On", "Only Front Off", "All Off"])
                self.assertTrue(meta["r43"]["rec_lamp_rear_top_button_coupled"])
                self.assertEqual(meta["r43"]["rec_lamp_uncoupled_split_reject_rc"], -22)
                self.assertTrue(meta["r43"]["silent_mode_forces_audio_signals_off"])
                self.assertEqual(meta["r43"]["audio_signals_locked_while_silent_rc"], -16)

    def test_10_round43_stage_a_overlay_rejects_invalid_r43_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r43_badmode", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            with self.assertRaises(ValueError):
                _build_overlay_for_r43(
                    runner, tmp_dir, tmp_dir / "bad_r43", "invalid_r43_mode", lang="schinese"
                )

    def test_11_round43_summary_json_schema_sanitization_and_audit_flags(self) -> None:
        summary_path = ROUND43_REPORT_DIR / "summary.json"
        self.assertTrue(summary_path.is_file())
        raw = summary_path.read_text(encoding="utf-8")
        for forbidden in ("/Users/", "/Volumes/KAFU2T", "/private/tmp"):
            self.assertNotIn(forbidden, raw)
        data = json.loads(raw)
        self.assertEqual(
            data["schema"],
            "fx6-on-fx3-round43-realhw-filesettings-shotmark-tcregen-reclamp-qemu-v1",
        )
        self.assertEqual(data["round"], 43)
        self.assertEqual(data["raw_firmware_bytes_leaked"], 0)
        self.assertIn("Linux version 4.9.337-scel+", data["kernel_version"])
        self.assertEqual(set(data["runs"].keys()), set(self.EXPECTED_RUN_KEYS))
        audit = data["r43_realhw_filesettings_shotmark_tcregen_reclamp_audit"]
        self.assertEqual(audit["round"], 43)
        self.assertEqual(audit["total_runs"], 3)
        for k in (
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "r43a_file_settings_5modes_37char_sdhc_lock_and_folder_block_verified",
            "r43a_shotmark12_xml_sidecar_image_jump_and_ftp_filter_verified",
            "r43a_stageb_big6_sid_0a_over_340k_pixels_verified",
            "r43b_tc_regenerate_slot1_master_and_forced_rec_run_verified",
            "r43b_ext_lk_release_on_regen_or_tc_run_and_sq_hdmi_tcout_block_verified",
            "r43c_reclamp_3state_coupled_rear_top_and_hdmi_tally_independence_verified",
            "r43c_silent_mode_audio_signals_lock_and_16_h0_eq_h3_verified",
        ):
            self.assertTrue(audit[k], f"Audit flag {k} must be True")

    def test_12_round43_r43a_file_name_5modes_37char_title_and_sdhc_lock(self) -> None:
        data = json.loads((ROUND43_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        init = data["runs"]["r43a_filesettings_shotmark_big6_schinese"]["r43_telemetry"]["filesettings_shotmark_init"]
        self.assertEqual(init["fnf_5modes_verified"], 5)
        self.assertEqual(init["invalid_fnf_mode_reject_rc"], -22)
        self.assertEqual(init["title_37char_max_ok"], 1)
        self.assertEqual(init["title_38char_reject_rc"], -22)
        self.assertEqual(init["title_illegal_char_reject_rc"], -22)
        self.assertEqual(init["prior_clip_untouched_ok"], 1)
        self.assertEqual(init["series_persist_ok"], 1)
        self.assertEqual(init["reset_per_card_ok"], 1)
        self.assertEqual(init["sdhc_forces_standard_ok"], 1)
        self.assertEqual(init["sdhc_non_standard_reject_rc"], -22)
        self.assertEqual(init["custom_movie_folder_reject_rc"], -1)

    def test_13_round43_r43a_shotmark12_xml_image_jump_and_ftp_filter(self) -> None:
        data = json.loads((ROUND43_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        init = data["runs"]["r43a_filesettings_shotmark_big6_schinese"]["r43_telemetry"]["filesettings_shotmark_init"]
        self.assertEqual(init["shotmark_rec_pb_xml_ok"], 1)
        self.assertEqual(init["image_jump_4modes_ok"], 4)
        self.assertEqual(init["invalid_jump_reject_rc"], -22)
        self.assertEqual(init["ftp_only_shotmark_mov"], 3)
        self.assertEqual(init["ftp_only_shotmark_filter_ok"], 1)
        self.assertEqual(init["appfw_present"], 1)
        self.assertEqual(init["shim_present"], 1)
        self.assertEqual(init["emmc_write_count"], 0)
        self.assertEqual(init["r43_init_ok"], 1)

    def test_14_round43_r43a_bridge_telemetry_consistent_with_r43b_and_r43c(self) -> None:
        data = json.loads((ROUND43_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        telem_a = data["runs"]["r43a_filesettings_shotmark_big6_schinese"]["r43_telemetry"]
        r43b = data["runs"]["r43b_tc_regenerate_slot1_extlk"]["r43_telemetry"]["tc_regenerate"]
        r43c = data["runs"]["r43c_reclamp_coupled_tally_h0_h3"]["r43_telemetry"]["reclamp_silent"]

        fsb = telem_a["filesettings_shotmark_bridge"]
        self.assertEqual(fsb["fnf_5modes_verified"], 5)
        self.assertEqual(fsb["title_37char_max_ok"], 1)
        self.assertEqual(fsb["title_38char_reject_rc"], -22)
        self.assertEqual(fsb["sdhc_forces_standard"], 1)
        self.assertEqual(fsb["custom_folder_reject_rc"], -1)
        self.assertEqual(fsb["shotmark_xml_jump_ftp_ok"], 1)
        self.assertEqual(fsb["filesettings_shotmark_ok"], 1)
        self.assertEqual(fsb["r43_bridge_ok"], 1)

        tcb = telem_a["tc_regenerate_bridge"]
        self.assertEqual(tcb["simult_slot1_master_read"], r43b["simult_reads_slot1_only_ok"])
        self.assertEqual(tcb["regen_forced_rec_run"], r43b["regen_forced_rec_run_ok"])
        self.assertEqual(tcb["ext_lk_released_on_regen_or_run"], r43b["ext_lk_dropped_on_regen"])
        self.assertEqual(tcb["sq_tc_run_reject_rc"], r43b["sq_tc_run_reject_rc"])
        self.assertEqual(tcb["sq_hdmi_tc_output_reject_rc"], r43b["sq_hdmi_tc_output_reject_rc"])
        self.assertEqual(tcb["tc_regenerate_ok"], 1)

        rlb = telem_a["reclamp_silent_bridge"]
        self.assertEqual(rlb["reclamp_3states_verified"], 3)
        self.assertEqual(rlb["only_front_off_rear_top_coupled"], r43c["only_front_off_011_coupled_ok"])
        self.assertEqual(rlb["uncoupled_split_reject_rc"], r43c["uncoupled_split_reject_rc"])
        self.assertEqual(rlb["emphasized_rec_hdmi_independent"], r43c["emphasized_rec_hdmi_independent_ok"])
        self.assertEqual(rlb["silent_forces_audio_signals_off"], r43c["silent_forces_audio_signals_off"])
        self.assertEqual(rlb["audio_signals_locked_rc"], r43c["audio_signals_locked_while_silent_rc"])
        self.assertEqual(rlb["reclamp_silent_ok"], 1)

    def test_15_round43_r43a_stage_b_13_sha256_and_big6_render_invariants(self) -> None:
        data = json.loads((ROUND43_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        r43a = data["runs"]["r43a_filesettings_shotmark_big6_schinese"]
        self.assertEqual(r43a["round"], 43)
        self.assertEqual(r43a["r43_mode"], "filesettings_shotmark_big6")
        self.assertEqual(r43a["target_presenter"], "31procam_big6_menu_home_presenter")
        self.assertEqual(r43a["target_sid"], "0x0a")
        self.assertEqual(r43a["nop_count"], 0)
        self.assertEqual(r43a["crashes"], 0)
        self.assertEqual(r43a["emmc_write_count"], 0)
        self.assertGreaterEqual(r43a["total_threads_seen"], 160)
        self.assertEqual(r43a["faithful_invariants"]["FX6_NATIVE_FAITHFUL"], 1)
        self.assertEqual(r43a["stage_b"]["manifest_count"], 13)
        self.assertEqual(len(r43a["stage_b"]["manifest_items"]), 13)
        for item in r43a["stage_b"]["manifest_items"]:
            self.assertEqual(len(item["sha256"]), 64)
            int(item["sha256"], 16)
        lt = r43a["r43_telemetry"]["lang_telemetry"]
        self.assertEqual(lt["gpe_fb"], 0)
        self.assertEqual(lt["subst_color"], 0)
        self.assertEqual(lt["subst_image"], 0)
        self.assertEqual(lt["r43_bridge_ok"], 1)
        self.assertEqual(lt["round43_realhw_filesettings_shotmark_tcregen_reclamp"], 1)
        self.assertEqual(r43a["gpe0_readback"]["nonzero_pixels"], 346206)

    def test_16_round43_r43a_png_receipts_under_28kib_and_dimensions(self) -> None:
        data = json.loads((ROUND43_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        exports = data["runs"]["r43a_filesettings_shotmark_big6_schinese"]["png_exports"]
        for key in ("alpha_png", "composited_png"):
            p = REPO_ROOT / exports[key]["path"]
            self.assertTrue(p.is_file(), f"Missing Round 43 PNG: {p}")
            raw = p.read_bytes()
            self.assertLess(len(raw), 28 * 1024, f"PNG exceeds 28 KiB: {p} ({len(raw)} bytes)")
            self.assertEqual(len(raw), exports[key]["bytes"])
            self.assertEqual(hashlib.sha256(raw).hexdigest(), exports[key]["sha256"])
            w, h, rows = _decode_png_rgba_rows(raw)
            self.assertEqual((w, h), (1024, 540))
            if key == "alpha_png":
                nonzero_alpha = sum(sum(1 for a in row[3::4] if a != 0) for row in rows)
                self.assertGreater(nonzero_alpha, 340000)

    def test_17_round43_r43b_tc_regenerate_slot1_master_and_forced_rec_run(self) -> None:
        data = json.loads((ROUND43_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        r43b = data["runs"]["r43b_tc_regenerate_slot1_extlk"]
        self.assertEqual(r43b["round"], 43)
        self.assertEqual(r43b["r43_mode"], "tc_regenerate_slot1_extlk")
        self.assertEqual(r43b["crashes"], 0)
        self.assertEqual(r43b["emmc_write_count"], 0)
        self.assertTrue(r43b["gpe0_readback"]["skipped_stock_fx3_mode"])
        self.assertEqual(r43b["r43_telemetry"]["tc_regenerate_rc"], 0)
        b = r43b["r43_telemetry"]["tc_regenerate"]
        self.assertEqual(b["hdmi_tc_output_default_off"], 1)
        self.assertEqual(b["regen_single_slot1_ok"], 1)
        self.assertEqual(b["regen_single_slot2_ok"], 1)
        self.assertEqual(b["simult_reads_slot1_only_ok"], 1)
        self.assertEqual(b["simult_slot2_ignored"], 1)
        self.assertEqual(b["standby_ticks_advanced"], 0)
        self.assertEqual(b["rec_ticks_advanced"], 24)
        self.assertEqual(b["regen_forced_rec_run_ok"], 1)
        self.assertEqual(b["r43b_ok"], 1)

    def test_18_round43_r43b_ext_lk_release_and_sq_hdmi_tcout_block(self) -> None:
        data = json.loads((ROUND43_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        b = data["runs"]["r43b_tc_regenerate_slot1_extlk"]["r43_telemetry"]["tc_regenerate"]
        self.assertEqual(b["ext_lk_locked_ok"], 1)
        self.assertEqual(b["ext_lk_dropped_on_regen"], 1)
        self.assertEqual(b["ext_lk_active_after_regen"], 0)
        self.assertEqual(b["ext_lk_dropped_on_tc_run_change"], 1)
        self.assertEqual(b["ext_lk_reject_when_regen_rc"], -22)
        self.assertEqual(b["movie_hdmi_tc_out_on_rc"], 0)
        self.assertEqual(b["invalid_hdmi_tc_out_rc"], -22)
        self.assertEqual(b["sq_tc_run_reject_rc"], -95)
        self.assertEqual(b["sq_hdmi_tc_output_reject_rc"], -95)
        self.assertEqual(b["p2_write_blocked_rc"], -30)
        self.assertEqual(b["p2_setting_sha256_match"], 1)
        self.assertEqual(b["appfw_ok"], 1)
        self.assertEqual(b["shim_elf_ok"], 1)
        self.assertEqual(b["emmc_write_count"], 0)

    def test_19_round43_r43c_reclamp_3state_coupled_rear_top_and_hdmi_tally(self) -> None:
        data = json.loads((ROUND43_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        r43c = data["runs"]["r43c_reclamp_coupled_tally_h0_h3"]
        self.assertEqual(r43c["round"], 43)
        self.assertEqual(r43c["r43_mode"], "reclamp_coupled_tally_h0_h3")
        self.assertEqual(r43c["crashes"], 0)
        self.assertEqual(r43c["emmc_write_count"], 0)
        self.assertTrue(r43c["gpe0_readback"]["skipped_stock_fx3_mode"])
        self.assertEqual(r43c["r43_telemetry"]["reclamp_silent_rc"], 0)
        c = r43c["r43_telemetry"]["reclamp_silent"]
        self.assertEqual(c["standby_leds_off_ok"], 1)
        self.assertEqual(c["reclamp_all_on_111_ok"], 1)
        self.assertEqual(c["only_front_off_011_coupled_ok"], 1)
        self.assertEqual(c["reclamp_all_off_000_ok"], 1)
        self.assertEqual(c["emphasized_rec_hdmi_independent_ok"], 1)
        self.assertEqual(c["uncoupled_split_reject_rc"], -22)
        self.assertEqual(c["r43c_ok"], 1)

    def test_20_round43_r43c_silent_mode_audio_signals_lock_and_restore(self) -> None:
        data = json.loads((ROUND43_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        c = data["runs"]["r43c_reclamp_coupled_tally_h0_h3"]["r43_telemetry"]["reclamp_silent"]
        self.assertEqual(c["silent_forces_audio_signals_off"], 1)
        self.assertEqual(c["audio_signals_locked_while_silent_rc"], -16)
        self.assertEqual(c["audio_signals_restored_when_silent_off"], 1)
        self.assertEqual(c["p2_write_blocked_rc"], -30)

    def test_21_round43_r43c_16_surfaces_h0_eq_h3_zero_drift_and_dlopen_ok(self) -> None:
        data = json.loads((ROUND43_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        c = data["runs"]["r43c_reclamp_coupled_tally_h0_h3"]["r43_telemetry"]["reclamp_silent"]
        self.assertEqual(c["dlopen_ok"], 1)
        self.assertEqual(c["surfaces_verified"], 16)
        self.assertEqual(c["surfaces_h0_eq_h3"], 16)
        self.assertEqual(c["drift_bits"], 0)
        self.assertEqual(c["emmc_write_count"], 0)

    def test_22_round43_stage_b_bridge_mechanisms_and_bench_boundaries(self) -> None:
        data = json.loads((ROUND43_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        mech = data["realhw_mechanisms_verified"]
        self.assertEqual(mech["file_settings_5mode_37char_sdhc_lock_and_shotmark12_xml_init"]["r43_init_ok"], 1)
        self.assertEqual(mech["file_settings_shotmark_stage_b_bridge"]["r43_bridge_ok"], 1)
        self.assertEqual(mech["tc_regenerate_slot1_extlk_stage_b_bridge"]["tc_regenerate_ok"], 1)
        self.assertEqual(mech["reclamp_coupled_tally_silent_stage_b_bridge"]["reclamp_silent_ok"], 1)
        self.assertEqual(mech["tc_regenerate_slot1_master_forced_rec_run_extlk_drop_and_sq_block"]["r43b_ok"], 1)
        self.assertEqual(mech["reclamp_3state_coupled_rear_top_tally_silent_audio_lock_and_h0_h3"]["r43c_ok"], 1)

        br = data["runs"]["r43a_filesettings_shotmark_big6_schinese"]["r43_telemetry"]["stage_b_bridge"]
        for key in (
            "faithful",
            "p12_wlan",
            "wf12_00342260_immune",
            "p10_keymap",
            "p4_nd_clear",
            "p11_xlr_h1",
            "filesettings_37char_sdhc_shotmark",
            "tc_regenerate_slot1_extlk_release",
            "reclamp_coupled_rear_top_silent_lock",
        ):
            self.assertEqual(br[key], 1, f"Expected stage_b_bridge[{key}]==1")
        self.assertEqual(br["round"], 43)
        self.assertEqual(br["nop_count"], 0)
        self.assertEqual(br["emmc_write_count"], 0)
        self.assertEqual(len(data["unexecuted_physical_camera_bench_boundaries"]), 3)

    def test_23_round43_stage_b_r43_meta_parity_across_all_3_runs(self) -> None:
        data = json.loads((ROUND43_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        for rk, expected_mode in (
            ("r43a_filesettings_shotmark_big6_schinese", "filesettings_shotmark_big6"),
            ("r43b_tc_regenerate_slot1_extlk", "tc_regenerate_slot1_extlk"),
            ("r43c_reclamp_coupled_tally_h0_h3", "reclamp_coupled_tally_h0_h3"),
        ):
            r43_meta = data["runs"][rk]["stage_b"]["r43"]
            self.assertEqual(r43_meta["r43_mode"], expected_mode)
            self.assertEqual(len(r43_meta["file_name_formats"]), 5)
            self.assertEqual(r43_meta["title_name_max_ascii_chars"], 37)
            self.assertEqual(r43_meta["sdhc_fat32_forced_format"], "Standard")
            self.assertEqual(r43_meta["custom_movie_folder_reject_rc"], -1)
            self.assertEqual(r43_meta["tc_regenerate_simult_source"], "Slot 1")
            self.assertEqual(r43_meta["tc_regenerate_forced_run_mode"], "Rec Run")
            self.assertEqual(r43_meta["sq_hdmi_tc_output_reject_rc"], -95)
            self.assertTrue(r43_meta["rec_lamp_rear_top_button_coupled"])
            self.assertEqual(r43_meta["rec_lamp_uncoupled_split_reject_rc"], -22)
            self.assertEqual(r43_meta["audio_signals_locked_while_silent_rc"], -16)
            self.assertEqual(r43_meta["p2_setting_writes"], 0)

    def test_24_round43_readme_sanitization_and_no_tmp_or_binary_residue(self) -> None:
        closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn("2026-11-15-round43-realhw-filesettings-shotmark-tcregen-reclamp-qemu", closure_readme)
        self.assertIn("`24` New Round 43 Dual-Mode Unit Tests (`618` Total)", closure_readme)
        r43_readme = (ROUND43_REPORT_DIR / "README.md").read_text(encoding="utf-8")
        for tok in (
            "Round 43",
            "File Settings",
            "File Name Format",
            "Title Name Settings",
            "SDHC",
            "Shot Mark1",
            "Shot Mark2",
            "Regenerate",
            "EXT-LK",
            "REC Lamp",
            "Only Front Off",
            "Silent Mode",
            "Audio signals",
            "round43-filesettings-shotmark-big6",
            "round43-tc-regenerate",
            "round43-reclamp-silent",
        ):
            self.assertIn(tok, r43_readme)
        for forbidden in ("/Users/", "/Volumes/KAFU2T", "/private/tmp"):
            self.assertNotIn(forbidden, r43_readme)
        for folder in (CLOSURE_DIR, ROUND43_REPORT_DIR):
            for p in folder.rglob("*"):
                if p.is_file():
                    self.assertNotIn(p.suffix, {".cpio", ".so", ".o", ".img", ".qcow2", ".pyc"})


if __name__ == "__main__":
    unittest.main()
