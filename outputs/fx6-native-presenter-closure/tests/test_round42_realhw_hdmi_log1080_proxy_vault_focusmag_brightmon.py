#!/usr/bin/env python3
"""Offline dual-mode unit tests for FX6-on-FX3 Round 42 (Live FX3 7.02 QEMU Rehearsal)."""
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
ROUND42_REPORT_DIR = (
    REPO_ROOT
    / "reports"
    / "2026-11-15-round42-realhw-hdmi-log1080-proxy-vault-focusmag-brightmon-qemu"
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


def _build_overlay_for_r42(runner, tmp_dir: pathlib.Path, work: pathlib.Path, r42_mode: str, lang: str = "schinese"):
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
            enable_r42=True, r42_mode=r42_mode,
            sd_manifest_mode="valid", lang=lang, shim_bytes=b"SHIM",
        )


class TestRound42RealHwHdmiLog1080ProxyVaultFocusMagBrightMon(unittest.TestCase):
    EXPECTED_RUN_KEYS = (
        "r42a_hdmi_log1080_hdmionly_4k_big6_schinese",
        "r42b_proxy_vault_119p_atomic_pair",
        "r42c_focusmag_brightmon_h0_h3",
    )

    def test_01_round42_c_and_python_source_contracts(self) -> None:
        shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")

        self.assertIn("#if FX6_ROUND >= 42", shim_src)
        for token in (
            "FX6_R42_HDMI_LOG1080_BRIDGE",
            "FX6_R42_PROXY_VAULT_BRIDGE",
            "FX6_R42_FOCUSMAG_BRIGHTMON_BRIDGE",
            "FX6_R42_LANG_TELEMETRY",
            "FX6_STAGE_B_R42_BRIDGE",
            "round42_realhw_hdmi_log1080_proxy_vault_focusmag_brightmon=1",
        ):
            self.assertIn(token, shim_src)

        for token in (
            "r42_hdmi_eval_pipeline",
            "r42_hdmi_select_4k_only_mode",
            "r42_hdmi_attempt_internal_rec",
            "setup_r42_hdmi_log1080_hdmionly_probe",
            "r42_proxy_eval_config",
            "r42_proxy_oncamera_playback",
            "r42_proxy_vault_op",
            "run_r42_proxy_vault_probe",
            "r42_set_initial_focus_mag",
            "r42_trigger_auto_mag_in_mf",
            "r42_toggle_bright_monitoring",
            "r42_apply_camera_event",
            "run_r42_focusmag_brightmon_probe",
            "--r42-proxy-vault",
            "--r42-focusmag-brightmon",
            "/etc/fx6_stage_r42",
            "FX6_R42_HDMI_LOG1080_INIT",
            "FX6_R42_PROXY_VAULT",
            "FX6_R42_FOCUSMAG_BRIGHTMON",
        ):
            self.assertIn(token, verify_src)

        for token in (
            "enable_r42",
            "r42_mode",
            "--r42-mode",
            "hdmi_log1080_hdmionly_4k_big6",
            "proxy_vault_119p_atomic_pair",
            "focusmag_brightmon_h0_h3",
            "etc/fx6_stage_r42",
            "FX6_R42_PROXY_VAULT_EXIT",
            "FX6_R42_FOCUSMAG_BRIGHTMON_EXIT",
            '"r42_telemetry"',
            "choices=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46]",
        ):
            self.assertIn(token, runner_src)

    def test_02_round42_native_verify_c_compiles_with_zig_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r42_verc", "build_and_run_round.py")
        if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1" and not runner.ZIG.is_file():
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertTrue(runner.ZIG.is_file(), f"Missing zig compiler at {runner.ZIG}")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            cache_dir = tmp_dir / "zig-cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            for clean_flag in ("0", "1"):
                out_bin = tmp_dir / f"fx6-stage-a-verify-r42-{clean_flag}"
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

    def test_03_round42_build_binaries_compiles_shim_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r42_shimc", "build_and_run_round.py")
        if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1" and not runner.ZIG.is_file():
            self.skipTest("Clean-room fallback without local zig binary")
        with tempfile.TemporaryDirectory() as tmp:
            for clean_flag in ("0", "1"):
                work = pathlib.Path(tmp) / f"shim_{clean_flag}"
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                    launcher_b, shim_b, meta = runner.build_binaries(
                        work,
                        fx6_round=42,
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

    def test_04_round42_extract_milestones_r42a_hdmi_log1080_and_bridges(self) -> None:
        runner = _load_closure_module("fx6_brr_r42_msa", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R42_HDMI_LOG1080_INIT baseline_4k_ok=1 log_3modes_1080p=3 pplut1_to_4_1080p=4 raw_on_4264_override_ok=1 locked_4k_mode_rc=-16 hdmi_only_6_4k_modes_verified=6 hdmi_only_width=3840 hdmi_only_height=2160 hdmi_only_bit_depth=10 invalid_4k_mode_reject_rc=-22 hdmi_only_internal_rec_reject_rc=-1 internal_card_recording_active=0 hdmi_only_forces_info_off=1 hdmi_only_suppresses_desqueeze=1 camera_lcd_blanked_when_info_on=1 emphasized_tally_on_hdmi=1 lcd_active_when_info_off=1 appfw_present=1 shim_present=1 emmc_write_count=0 r42_init_ok=1 verify_us=659806",
                "FX6_R42_HDMI_LOG1080_BRIDGE log_pplut_1080p_forced=1 hdmi_only_6_modes_4k10b=6 hdmi_only_internal_rec_rc=-1 hdmi_only_forces_info_off=1 hdmi_only_suppresses_desqueeze=1 hdmi_info_on_blanks_lcd=1 hdmi_log1080_ok=1 emmc_write_count=0 r42_bridge_ok=1",
                "FX6_R42_PROXY_VAULT_BRIDGE proxy_hs_1080p_16m_9m=1 proxy_s_720p_6m=1 proxy_11988p_cutoff_rc=-22 proxy_oncamera_playback_rc=-95 proxy_uncoupled_delete_rc=-18 proxy_atomic_vault_ok=1 emmc_write_count=0 p2_setting_writes=0",
                "FX6_R42_FOCUSMAG_BRIGHTMON_BRIDGE movie_mag_10_40=1 still_ff_21_apsc_15=1 automag_movie_reject_rc=-95 marker_suppressed_while_mag=1 brightmon_mag_lockout_rc=-16 brightmon_setting_effect_off=1 focusmag_brightmon_ok=1 emmc_write_count=0",
                "FX6_STAGE_B_R42_BRIDGE round=42 faithful=1 nop_count=0 p12_wlan=1 wf12_00342260_immune=1 p10_keymap=1 p4_nd_clear=1 p11_xlr_h1=1 lang=schinese bk4_lang=0x19 enum=0x2b45_CHINESE_SIMPLIFIED font_bank=23 str_bank=19 hdmi_log1080_hdmionly_4k10b=1 proxy_dualcodec_119p_atomic_vault=1 focusmag_automag_brightmon_lockout=1 emmc_write_count=0",
                "FX6_R42_LANG_TELEMETRY reason=gpermDrawFlush lang=schinese bk4_lang_id=0x02cf019c bk4_lang_val=0x19 gpe_fb=0 hdmi_log1080_ok=1 proxy_vault_ok=1 focusmag_brightmon_ok=1 r42_bridge_ok=1 round42_realhw_hdmi_log1080_proxy_vault_focusmag_brightmon=1 emmc_write_count=0 subst_color=0 subst_image=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        r42 = ms["r42_telemetry"]
        self.assertIsNotNone(r42)
        self.assertEqual(r42["hdmi_log1080_init"]["log_3modes_1080p"], 3)
        self.assertEqual(r42["hdmi_log1080_init"]["pplut1_to_4_1080p"], 4)
        self.assertEqual(r42["hdmi_log1080_init"]["hdmi_only_6_4k_modes_verified"], 6)
        self.assertEqual(r42["hdmi_log1080_init"]["r42_init_ok"], 1)
        self.assertEqual(r42["hdmi_log1080_bridge"]["r42_bridge_ok"], 1)
        self.assertEqual(r42["proxy_vault_bridge"]["proxy_atomic_vault_ok"], 1)
        self.assertEqual(r42["focusmag_brightmon_bridge"]["focusmag_brightmon_ok"], 1)
        self.assertEqual(r42["stage_b_bridge"]["round"], 42)
        self.assertEqual(r42["lang_telemetry"]["gpe_fb"], 0)

    def test_05_round42_extract_milestones_r42b_proxy_vault(self) -> None:
        runner = _load_closure_module("fx6_brr_r42_msb", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R42_PROXY_VAULT xavc_hs_hd_1080p_16m_9m_ok=1 xavc_s_hd_720p_6m_ok=1 s_16m_reject_rc=-22 normal_11988p_reject_rc=-22 normal_100p_reject_rc=-22 sq_11988p_reject_rc=-22 sq_100fps_reject_rc=-22 sq_120fps_reject_rc=-22 sq_200fps_reject_rc=-22 sq_240fps_reject_rc=-22 hdmi_only_rec_reject_rc=-1 hdmi_only_card_files=0 proxy_playback_reject_rc=-95 px_badge_on_main_only=1 slot1_pair_created=1 slot2_pair_created=1 uncoupled_delete_clip_only_rc=-18 uncoupled_delete_sub_only_rc=-18 uncoupled_protect_sub_only_rc=-1 coupled_protect_both_ok=1 protected_delete_reject_rc=-1 coupled_delete_both_ok=1 slot2_coupled_del_rc=0 orphan_files_remaining=0 p2_write_blocked_rc=-30 p2_setting_sha256_match=1 appfw_ok=1 shim_elf_ok=1 emmc_write_count=0 r42b_ok=1 verify_us=699180",
                "FX6_R42_PROXY_VAULT_RC=0",
                "FX6_R42_PROXY_VAULT_EXIT rc=0 emmc_write_count=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        r42 = ms["r42_telemetry"]
        self.assertIsNotNone(r42)
        self.assertEqual(r42["proxy_vault_rc"], 0)
        b = r42["proxy_vault"]
        self.assertEqual(b["xavc_hs_hd_1080p_16m_9m_ok"], 1)
        self.assertEqual(b["xavc_s_hd_720p_6m_ok"], 1)
        self.assertEqual(b["normal_11988p_reject_rc"], -22)
        self.assertEqual(b["sq_120fps_reject_rc"], -22)
        self.assertEqual(b["proxy_playback_reject_rc"], -95)
        self.assertEqual(b["uncoupled_delete_clip_only_rc"], -18)
        self.assertEqual(b["uncoupled_protect_sub_only_rc"], -1)
        self.assertEqual(b["orphan_files_remaining"], 0)
        self.assertEqual(b["r42b_ok"], 1)

    def test_06_round42_extract_milestones_r42c_focusmag_brightmon(self) -> None:
        runner = _load_closure_module("fx6_brr_r42_msc", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R42_FOCUSMAG_BRIGHTMON movie_mag_10_40_ok=1 movie_reject_21_rc=-22 movie_reject_15_rc=-22 still_ff_mag_21_ok=1 still_apsc_mag_15_ok=1 auto_mag_mf_movie_reject_rc=-95 auto_mag_mf_still_rc=0 brightmon_blocked_while_automag_rc=-16 marker_display_suppressed_while_mag=1 brightmon_blocked_while_focusmag_rc=-16 marker_display_restored_after_mag=1 brightmon_forces_setting_effect_off=1 brightmon_autocancel_non_pasm=1 brightmon_autocancel_non_mf=1 brightmon_autocancel_poweroff=1 p2_write_blocked_rc=-30 dlopen_ok=1 surfaces_verified=16 surfaces_h0_eq_h3=16 drift_bits=0 emmc_write_count=0 r42c_ok=1 verify_us=6554",
                "FX6_R42_FOCUSMAG_BRIGHTMON_RC=0",
                "FX6_R42_FOCUSMAG_BRIGHTMON_EXIT rc=0 emmc_write_count=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        r42 = ms["r42_telemetry"]
        self.assertIsNotNone(r42)
        self.assertEqual(r42["focusmag_brightmon_rc"], 0)
        c = r42["focusmag_brightmon"]
        self.assertEqual(c["movie_mag_10_40_ok"], 1)
        self.assertEqual(c["auto_mag_mf_movie_reject_rc"], -95)
        self.assertEqual(c["brightmon_blocked_while_focusmag_rc"], -16)
        self.assertEqual(c["brightmon_forces_setting_effect_off"], 1)
        self.assertEqual(c["surfaces_h0_eq_h3"], 16)
        self.assertEqual(c["drift_bits"], 0)
        self.assertEqual(c["r42c_ok"], 1)

    def test_07_round42_stage_a_overlay_r42a_hdmi_log1080_mocked_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r42_ovl_a", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            for clean_flag in ("0", "1"):
                work = tmp_dir / f"r42_a_{clean_flag}"
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                    rep, add, meta = _build_overlay_for_r42(
                        runner, tmp_dir, work, "hdmi_log1080_hdmionly_4k_big6", lang="schinese"
                    )
                init_out = rep["init"].decode("utf-8")
                self.assertNotIn("--r42-proxy-vault", init_out)
                self.assertNotIn("--r42-focusmag-brightmon", init_out)
                self.assertIn("--sd-gate", init_out)
                self.assertIn("etc/fx6_stage_r42", add)
                self.assertIn("r42_mode=hdmi_log1080_hdmionly_4k_big6", add["etc/fx6_stage_r42"][0].decode("utf-8"))
                self.assertTrue(meta["r42_enabled"])
                self.assertEqual(meta["r42"]["r42_mode"], "hdmi_log1080_hdmionly_4k_big6")
                self.assertEqual(meta["r42"]["hdmi_log_pplut_forced_resolution"], "1920x1080")
                self.assertEqual(len(meta["r42"]["hdmi_only_4k_modes"]), 6)
                self.assertEqual(meta["r42"]["hdmi_only_internal_rec_reject_rc"], -1)
                self.assertTrue(meta["r42"]["hdmi_only_forces_info_display_off"])
                self.assertTrue(meta["r42"]["hdmi_info_on_blanks_camera_lcd"])

    def test_08_round42_stage_a_overlay_r42b_proxy_vault_mocked_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r42_ovl_b", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            for clean_flag in ("0", "1"):
                work = tmp_dir / f"r42_b_{clean_flag}"
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                    rep, _, meta = _build_overlay_for_r42(
                        runner, tmp_dir, work, "proxy_vault_119p_atomic_pair", lang="en"
                    )
                init_out = rep["init"].decode("utf-8")
                self.assertIn("/usr/bin/fx6-stage-a-verify --r42-proxy-vault", init_out)
                self.assertIn("FX6_R42_PROXY_VAULT_EXIT", init_out)
                self.assertEqual(meta["r42"]["r42_mode"], "proxy_vault_119p_atomic_pair")
                self.assertEqual(meta["r42"]["proxy_11988p_100p_cutoff_rc"], -22)
                self.assertEqual(meta["r42"]["proxy_oncamera_playback_reject_rc"], -95)
                self.assertEqual(meta["r42"]["proxy_uncoupled_delete_reject_rc"], -18)
                self.assertEqual(meta["r42"]["proxy_uncoupled_protect_reject_rc"], -1)

    def test_09_round42_stage_a_overlay_r42c_focusmag_brightmon_mocked_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r42_ovl_c", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            for clean_flag in ("0", "1"):
                work = tmp_dir / f"r42_c_{clean_flag}"
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                    rep, _, meta = _build_overlay_for_r42(
                        runner, tmp_dir, work, "focusmag_brightmon_h0_h3", lang="en"
                    )
                init_out = rep["init"].decode("utf-8")
                self.assertIn("/usr/bin/fx6-stage-a-verify --r42-focusmag-brightmon", init_out)
                self.assertIn("FX6_R42_FOCUSMAG_BRIGHTMON_EXIT", init_out)
                self.assertEqual(meta["r42"]["r42_mode"], "focusmag_brightmon_h0_h3")
                self.assertEqual(meta["r42"]["focusmag_movie_scales"], ["x1.0", "x4.0"])
                self.assertEqual(meta["r42"]["focusmag_still_ff_scales"], ["x1.0", "x2.1"])
                self.assertEqual(meta["r42"]["focusmag_still_apsc_s35_scales"], ["x1.0", "x1.5"])
                self.assertEqual(meta["r42"]["automag_in_mf_movie_reject_rc"], -95)
                self.assertEqual(meta["r42"]["brightmon_lockout_while_mag_reject_rc"], -16)

    def test_10_round42_stage_a_overlay_rejects_invalid_r42_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r42_badmode", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            with self.assertRaises(ValueError):
                _build_overlay_for_r42(
                    runner, tmp_dir, tmp_dir / "bad_r42", "invalid_r42_mode", lang="schinese"
                )

    def test_11_round42_summary_json_schema_sanitization_and_audit_flags(self) -> None:
        summary_path = ROUND42_REPORT_DIR / "summary.json"
        self.assertTrue(summary_path.is_file())
        raw = summary_path.read_text(encoding="utf-8")
        for forbidden in ("/Users/", "/Volumes/KAFU2T", "/private/tmp"):
            self.assertNotIn(forbidden, raw)
        data = json.loads(raw)
        self.assertEqual(
            data["schema"],
            "fx6-on-fx3-round42-realhw-hdmi-log1080-proxy-vault-focusmag-brightmon-qemu-v1",
        )
        self.assertEqual(data["round"], 42)
        self.assertIn("Linux version 4.9.337-scel+", data["kernel_version"])
        self.assertEqual(set(data["runs"].keys()), set(self.EXPECTED_RUN_KEYS))
        audit = data["r42_realhw_hdmi_log1080_proxy_vault_focusmag_brightmon_audit"]
        self.assertEqual(audit["round"], 42)
        self.assertEqual(audit["total_runs"], 3)
        for k in (
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "r42a_log_pplut_1080p_downshift_and_raw_4k_override_verified",
            "r42a_hdmionly_6_modes_4k10bit_internal_rec_disabled_and_lcd_blank_verified",
            "r42a_stageb_big6_sid_0a_over_340k_pixels_verified",
            "r42b_proxy_dualcodec_119p_sq120fps_hdmionly_cutoffs_verified",
            "r42b_proxy_playback_enotsup_and_atomic_clip_sub_vault_verified",
            "r42c_focusmag_movie_x40_still_ff21_apsc15_and_automag_block_verified",
            "r42c_brightmon_mag_lockout_setting_effect_off_and_16_h0_eq_h3_verified",
        ):
            self.assertTrue(audit[k], f"Audit flag {k} must be True")

    def test_12_round42_r42a_hdmi_log_and_pplut_1080p_downshift_vs_raw_override(self) -> None:
        data = json.loads((ROUND42_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        init = data["runs"]["r42a_hdmi_log1080_hdmionly_4k_big6_schinese"]["r42_telemetry"]["hdmi_log1080_init"]
        self.assertEqual(init["baseline_4k_ok"], 1)
        self.assertEqual(init["log_3modes_1080p"], 3)
        self.assertEqual(init["pplut1_to_4_1080p"], 4)
        self.assertEqual(init["raw_on_4264_override_ok"], 1)
        self.assertEqual(init["locked_4k_mode_rc"], -16)

    def test_13_round42_r42a_hdmionly_6_modes_4k10bit_and_blank_lcd(self) -> None:
        data = json.loads((ROUND42_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        init = data["runs"]["r42a_hdmi_log1080_hdmionly_4k_big6_schinese"]["r42_telemetry"]["hdmi_log1080_init"]
        self.assertEqual(init["hdmi_only_6_4k_modes_verified"], 6)
        self.assertEqual(init["hdmi_only_width"], 3840)
        self.assertEqual(init["hdmi_only_height"], 2160)
        self.assertEqual(init["hdmi_only_bit_depth"], 10)
        self.assertEqual(init["invalid_4k_mode_reject_rc"], -22)
        self.assertEqual(init["hdmi_only_internal_rec_reject_rc"], -1)
        self.assertEqual(init["internal_card_recording_active"], 0)
        self.assertEqual(init["hdmi_only_forces_info_off"], 1)
        self.assertEqual(init["hdmi_only_suppresses_desqueeze"], 1)
        self.assertEqual(init["camera_lcd_blanked_when_info_on"], 1)
        self.assertEqual(init["emphasized_tally_on_hdmi"], 1)
        self.assertEqual(init["lcd_active_when_info_off"], 1)
        self.assertEqual(init["emmc_write_count"], 0)
        self.assertEqual(init["r42_init_ok"], 1)

    def test_14_round42_r42a_bridge_telemetry_consistent_with_r42b_and_r42c(self) -> None:
        data = json.loads((ROUND42_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        telem_a = data["runs"]["r42a_hdmi_log1080_hdmionly_4k_big6_schinese"]["r42_telemetry"]
        r42b = data["runs"]["r42b_proxy_vault_119p_atomic_pair"]["r42_telemetry"]["proxy_vault"]
        r42c = data["runs"]["r42c_focusmag_brightmon_h0_h3"]["r42_telemetry"]["focusmag_brightmon"]

        hb = telem_a["hdmi_log1080_bridge"]
        self.assertEqual(hb["log_pplut_1080p_forced"], 1)
        self.assertEqual(hb["hdmi_only_6_modes_4k10b"], 6)
        self.assertEqual(hb["hdmi_only_internal_rec_rc"], -1)
        self.assertEqual(hb["hdmi_only_forces_info_off"], 1)
        self.assertEqual(hb["hdmi_only_suppresses_desqueeze"], 1)
        self.assertEqual(hb["hdmi_info_on_blanks_lcd"], 1)
        self.assertEqual(hb["hdmi_log1080_ok"], 1)
        self.assertEqual(hb["r42_bridge_ok"], 1)

        pb = telem_a["proxy_vault_bridge"]
        self.assertEqual(pb["proxy_hs_1080p_16m_9m"], r42b["xavc_hs_hd_1080p_16m_9m_ok"])
        self.assertEqual(pb["proxy_s_720p_6m"], r42b["xavc_s_hd_720p_6m_ok"])
        self.assertEqual(pb["proxy_11988p_cutoff_rc"], r42b["normal_11988p_reject_rc"])
        self.assertEqual(pb["proxy_oncamera_playback_rc"], r42b["proxy_playback_reject_rc"])
        self.assertEqual(pb["proxy_uncoupled_delete_rc"], r42b["uncoupled_delete_clip_only_rc"])
        self.assertEqual(pb["proxy_atomic_vault_ok"], 1)

        fb = telem_a["focusmag_brightmon_bridge"]
        self.assertEqual(fb["movie_mag_10_40"], r42c["movie_mag_10_40_ok"])
        self.assertEqual(fb["automag_movie_reject_rc"], r42c["auto_mag_mf_movie_reject_rc"])
        self.assertEqual(fb["marker_suppressed_while_mag"], r42c["marker_display_suppressed_while_mag"])
        self.assertEqual(fb["brightmon_mag_lockout_rc"], r42c["brightmon_blocked_while_focusmag_rc"])
        self.assertEqual(fb["brightmon_setting_effect_off"], r42c["brightmon_forces_setting_effect_off"])
        self.assertEqual(fb["focusmag_brightmon_ok"], 1)

    def test_15_round42_r42a_stage_b_13_sha256_and_big6_render_invariants(self) -> None:
        data = json.loads((ROUND42_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        r42a = data["runs"]["r42a_hdmi_log1080_hdmionly_4k_big6_schinese"]
        self.assertEqual(r42a["round"], 42)
        self.assertEqual(r42a["r42_mode"], "hdmi_log1080_hdmionly_4k_big6")
        self.assertEqual(r42a["target_presenter"], "31procam_big6_menu_home_presenter")
        self.assertEqual(r42a["target_sid"], "0x0a")
        self.assertEqual(r42a["nop_count"], 0)
        self.assertEqual(r42a["crashes"], 0)
        self.assertEqual(r42a["emmc_write_count"], 0)
        self.assertGreaterEqual(r42a["total_threads_seen"], 160)
        self.assertEqual(r42a["faithful_invariants"]["FX6_NATIVE_FAITHFUL"], 1)
        self.assertEqual(r42a["stage_b"]["manifest_count"], 13)
        self.assertEqual(len(r42a["stage_b"]["manifest_items"]), 13)
        for item in r42a["stage_b"]["manifest_items"]:
            self.assertEqual(len(item["sha256"]), 64)
            int(item["sha256"], 16)
        lt = r42a["r42_telemetry"]["lang_telemetry"]
        self.assertEqual(lt["gpe_fb"], 0)
        self.assertEqual(lt["subst_color"], 0)
        self.assertEqual(lt["subst_image"], 0)
        self.assertEqual(lt["r42_bridge_ok"], 1)
        self.assertEqual(lt["round42_realhw_hdmi_log1080_proxy_vault_focusmag_brightmon"], 1)
        self.assertGreater(r42a["gpe0_readback"]["nonzero_pixels"], 340000)

    def test_16_round42_r42a_png_receipts_under_28kib_and_dimensions(self) -> None:
        data = json.loads((ROUND42_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        exports = data["runs"]["r42a_hdmi_log1080_hdmionly_4k_big6_schinese"]["png_exports"]
        for key in ("alpha_png", "composited_png"):
            p = REPO_ROOT / exports[key]["path"]
            self.assertTrue(p.is_file(), f"Missing Round 42 PNG: {p}")
            raw = p.read_bytes()
            self.assertLess(len(raw), 28 * 1024, f"PNG exceeds 28 KiB: {p} ({len(raw)} bytes)")
            self.assertEqual(len(raw), exports[key]["bytes"])
            self.assertEqual(hashlib.sha256(raw).hexdigest(), exports[key]["sha256"])
            w, h, rows = _decode_png_rgba_rows(raw)
            self.assertEqual((w, h), (1024, 540))
            if key == "alpha_png":
                nonzero_alpha = sum(sum(1 for a in row[3::4] if a != 0) for row in rows)
                self.assertGreater(nonzero_alpha, 340000)

    def test_17_round42_r42b_proxy_dual_codec_matrix_and_rate_cutoffs(self) -> None:
        data = json.loads((ROUND42_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        r42b = data["runs"]["r42b_proxy_vault_119p_atomic_pair"]
        self.assertEqual(r42b["round"], 42)
        self.assertEqual(r42b["r42_mode"], "proxy_vault_119p_atomic_pair")
        self.assertEqual(r42b["crashes"], 0)
        self.assertEqual(r42b["emmc_write_count"], 0)
        self.assertTrue(r42b["gpe0_readback"]["skipped_stock_fx3_mode"])
        self.assertEqual(r42b["r42_telemetry"]["proxy_vault_rc"], 0)
        b = r42b["r42_telemetry"]["proxy_vault"]
        self.assertEqual(b["xavc_hs_hd_1080p_16m_9m_ok"], 1)
        self.assertEqual(b["xavc_s_hd_720p_6m_ok"], 1)
        self.assertEqual(b["s_16m_reject_rc"], -22)
        for key in (
            "normal_11988p_reject_rc",
            "normal_100p_reject_rc",
            "sq_11988p_reject_rc",
            "sq_100fps_reject_rc",
            "sq_120fps_reject_rc",
            "sq_200fps_reject_rc",
            "sq_240fps_reject_rc",
        ):
            self.assertEqual(b[key], -22, f"Expected {key} == -22")
        self.assertEqual(b["hdmi_only_rec_reject_rc"], -1)
        self.assertEqual(b["hdmi_only_card_files"], 0)
        self.assertEqual(b["r42b_ok"], 1)

    def test_18_round42_r42b_proxy_playback_exclusion_and_atomic_clip_sub_vault(self) -> None:
        data = json.loads((ROUND42_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        b = data["runs"]["r42b_proxy_vault_119p_atomic_pair"]["r42_telemetry"]["proxy_vault"]
        self.assertEqual(b["proxy_playback_reject_rc"], -95)
        self.assertEqual(b["px_badge_on_main_only"], 1)
        self.assertEqual(b["slot1_pair_created"], 1)
        self.assertEqual(b["slot2_pair_created"], 1)
        self.assertEqual(b["uncoupled_delete_clip_only_rc"], -18)
        self.assertEqual(b["uncoupled_delete_sub_only_rc"], -18)
        self.assertEqual(b["uncoupled_protect_sub_only_rc"], -1)
        self.assertEqual(b["coupled_protect_both_ok"], 1)
        self.assertEqual(b["protected_delete_reject_rc"], -1)
        self.assertEqual(b["coupled_delete_both_ok"], 1)
        self.assertEqual(b["slot2_coupled_del_rc"], 0)
        self.assertEqual(b["orphan_files_remaining"], 0)
        self.assertEqual(b["p2_write_blocked_rc"], -30)
        self.assertEqual(b["p2_setting_sha256_match"], 1)
        self.assertEqual(b["appfw_ok"], 1)
        self.assertEqual(b["shim_elf_ok"], 1)
        self.assertEqual(b["emmc_write_count"], 0)

    def test_19_round42_r42c_focusmag_movie_vs_still_and_automag_block(self) -> None:
        data = json.loads((ROUND42_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        r42c = data["runs"]["r42c_focusmag_brightmon_h0_h3"]
        self.assertEqual(r42c["round"], 42)
        self.assertEqual(r42c["r42_mode"], "focusmag_brightmon_h0_h3")
        self.assertEqual(r42c["crashes"], 0)
        self.assertEqual(r42c["emmc_write_count"], 0)
        self.assertTrue(r42c["gpe0_readback"]["skipped_stock_fx3_mode"])
        self.assertEqual(r42c["r42_telemetry"]["focusmag_brightmon_rc"], 0)
        c = r42c["r42_telemetry"]["focusmag_brightmon"]
        self.assertEqual(c["movie_mag_10_40_ok"], 1)
        self.assertEqual(c["movie_reject_21_rc"], -22)
        self.assertEqual(c["movie_reject_15_rc"], -22)
        self.assertEqual(c["still_ff_mag_21_ok"], 1)
        self.assertEqual(c["still_apsc_mag_15_ok"], 1)
        self.assertEqual(c["auto_mag_mf_movie_reject_rc"], -95)
        self.assertEqual(c["auto_mag_mf_still_rc"], 0)
        self.assertEqual(c["marker_display_suppressed_while_mag"], 1)
        self.assertEqual(c["marker_display_restored_after_mag"], 1)
        self.assertEqual(c["r42c_ok"], 1)

    def test_20_round42_r42c_brightmon_lockout_setting_effect_off_and_autocancel(self) -> None:
        data = json.loads((ROUND42_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        c = data["runs"]["r42c_focusmag_brightmon_h0_h3"]["r42_telemetry"]["focusmag_brightmon"]
        self.assertEqual(c["brightmon_blocked_while_automag_rc"], -16)
        self.assertEqual(c["brightmon_blocked_while_focusmag_rc"], -16)
        self.assertEqual(c["brightmon_forces_setting_effect_off"], 1)
        self.assertEqual(c["brightmon_autocancel_non_pasm"], 1)
        self.assertEqual(c["brightmon_autocancel_non_mf"], 1)
        self.assertEqual(c["brightmon_autocancel_poweroff"], 1)
        self.assertEqual(c["p2_write_blocked_rc"], -30)

    def test_21_round42_r42c_16_surfaces_h0_eq_h3_zero_drift_and_dlopen_ok(self) -> None:
        data = json.loads((ROUND42_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        c = data["runs"]["r42c_focusmag_brightmon_h0_h3"]["r42_telemetry"]["focusmag_brightmon"]
        self.assertEqual(c["dlopen_ok"], 1)
        self.assertEqual(c["surfaces_verified"], 16)
        self.assertEqual(c["surfaces_h0_eq_h3"], 16)
        self.assertEqual(c["drift_bits"], 0)
        self.assertEqual(c["emmc_write_count"], 0)

    def test_22_round42_stage_b_bridge_mechanisms_and_bench_boundaries(self) -> None:
        data = json.loads((ROUND42_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        mech = data["realhw_mechanisms_verified"]
        self.assertEqual(mech["hdmi_log_1080p_downshift_vs_hdmionly_4k10bit_and_blank_lcd_init"]["r42_init_ok"], 1)
        self.assertEqual(mech["hdmi_log_1080p_hdmionly_stage_b_bridge"]["r42_bridge_ok"], 1)
        self.assertEqual(mech["proxy_vault_stage_b_bridge"]["proxy_atomic_vault_ok"], 1)
        self.assertEqual(mech["focusmag_brightmon_stage_b_bridge"]["focusmag_brightmon_ok"], 1)
        self.assertEqual(mech["proxy_dualcodec_119p_sq120fps_cutoff_and_atomic_clip_sub_vault"]["r42b_ok"], 1)
        self.assertEqual(mech["focusmag_movie_x40_vs_still_automag_block_brightmon_lockout_h0_h3"]["r42c_ok"], 1)

        br = data["runs"]["r42a_hdmi_log1080_hdmionly_4k_big6_schinese"]["r42_telemetry"]["stage_b_bridge"]
        for key in (
            "faithful",
            "p12_wlan",
            "wf12_00342260_immune",
            "p10_keymap",
            "p4_nd_clear",
            "p11_xlr_h1",
            "hdmi_log1080_hdmionly_4k10b",
            "proxy_dualcodec_119p_atomic_vault",
            "focusmag_automag_brightmon_lockout",
        ):
            self.assertEqual(br[key], 1, f"Expected stage_b_bridge[{key}]==1")
        self.assertEqual(br["round"], 42)
        self.assertEqual(br["nop_count"], 0)
        self.assertEqual(br["emmc_write_count"], 0)
        self.assertEqual(len(data["unexecuted_physical_camera_bench_boundaries"]), 3)

    def test_23_round42_stage_b_r42_meta_parity_across_all_3_runs(self) -> None:
        data = json.loads((ROUND42_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        for rk, expected_mode in (
            ("r42a_hdmi_log1080_hdmionly_4k_big6_schinese", "hdmi_log1080_hdmionly_4k_big6"),
            ("r42b_proxy_vault_119p_atomic_pair", "proxy_vault_119p_atomic_pair"),
            ("r42c_focusmag_brightmon_h0_h3", "focusmag_brightmon_h0_h3"),
        ):
            r42_meta = data["runs"][rk]["stage_b"]["r42"]
            self.assertEqual(r42_meta["r42_mode"], expected_mode)
            self.assertEqual(r42_meta["hdmi_log_pplut_forced_resolution"], "1920x1080")
            self.assertEqual(len(r42_meta["hdmi_only_4k_modes"]), 6)
            self.assertEqual(r42_meta["proxy_11988p_100p_cutoff_rc"], -22)
            self.assertEqual(r42_meta["proxy_oncamera_playback_reject_rc"], -95)
            self.assertEqual(r42_meta["proxy_uncoupled_delete_reject_rc"], -18)
            self.assertEqual(r42_meta["automag_in_mf_movie_reject_rc"], -95)
            self.assertEqual(r42_meta["brightmon_lockout_while_mag_reject_rc"], -16)
            self.assertEqual(r42_meta["p2_setting_writes"], 0)

    def test_24_round42_readme_sanitization_and_no_tmp_or_binary_residue(self) -> None:
        closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn("2026-11-15-round42-realhw-hdmi-log1080-proxy-vault-focusmag-brightmon-qemu", closure_readme)
        self.assertIn("`24` New Round 42 Dual-Mode Unit Tests (`594` Total)", closure_readme)
        r42_readme = (ROUND42_REPORT_DIR / "README.md").read_text(encoding="utf-8")
        for tok in (
            "Round 42",
            "HDMI Output Settings",
            "Log Shooting",
            "PPLUT1",
            "Off(HDMI Only)",
            "1080p",
            "Proxy Settings",
            "XAVC HS HD",
            "XAVC S HD",
            "Focus Magnifier",
            "Auto Magnifier in MF",
            "Bright Monitoring",
            "Setting Effect OFF",
            "round42-hdmi-log1080-big6",
            "round42-proxy-vault",
            "round42-focusmag-brightmon",
        ):
            self.assertIn(tok, r42_readme)
        for forbidden in ("/Users/", "/Volumes/KAFU2T", "/private/tmp"):
            self.assertNotIn(forbidden, r42_readme)
        for folder in (CLOSURE_DIR, ROUND42_REPORT_DIR):
            for p in folder.rglob("*"):
                if p.is_file():
                    self.assertNotIn(p.suffix, {".cpio", ".so", ".o", ".img", ".qcow2", ".pyc"})


if __name__ == "__main__":
    unittest.main()
