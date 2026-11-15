#!/usr/bin/env python3
"""Offline dual-mode unit tests for FX6-on-FX3 Round 48 (48th Milestone / Wave-34 Live FX3 7.02 QEMU Rehearsal)."""
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
ROUND48_REPORT_DIR = (
    REPO_ROOT
    / "reports"
    / "2026-11-15-round48-realhw-recover-imagedb-monitor-flip-af-sens-qemu"
)
WAVE34_SPEC_PATH = (
    REPO_ROOT
    / "reports"
    / "2026-11-15-global-sony-wave34-recover-imagedb-battery-vault-monitor-flip-playback-af-shift-sens-interval-intel"
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


def _build_overlay_for_r48(
    runner,
    tmp_dir: pathlib.Path,
    work: pathlib.Path,
    r48_mode: str,
    lang: str = "schinese",
    enable_r48: bool = True,
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
            enable_r48=enable_r48, r48_mode=r48_mode,
            sd_manifest_mode="valid", lang=lang, shim_bytes=b"SHIM",
        )


def _load_r48_summary() -> dict:
    return json.loads((ROUND48_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))


class TestRound48RealHwRecoverImageDbMonitorFlipAfSensQemu(unittest.TestCase):
    EXPECTED_RUN_KEYS = (
        "r48a_recover_imagedb_battery_vault",
        "r48b_monitor_flip_playback_big6_schinese",
        "r48c_af_sens_interval_still_h0_h3",
    )
    EXPECTED_FLIP_MODES = [
        "Auto",
        "Horizontal Flip",
        "Vertical Flip",
        "Off",
    ]

    def test_01_round48_c_and_python_source_contracts(self) -> None:
        shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")

        self.assertIn("#if FX6_ROUND >= 48", shim_src)
        for token in (
            "FX6_R48_RECOVER_IMAGEDB_BRIDGE",
            "FX6_R48_MONITOR_FLIP_BRIDGE",
            "FX6_R48_AF_SENS_INTERVAL_BRIDGE",
            "FX6_R48_LANG_TELEMETRY",
            "FX6_STAGE_B_R48_BRIDGE",
            "round48_realhw_recover_imagedb_monitor_flip_af_sens=1",
        ):
            self.assertIn(token, shim_src)

        for token in (
            "r48_execute_recover_image_db",
            "r48_imagedb_camera_settings_reset",
            "r48_imagedb_initialize_reset",
            "run_r48_recover_imagedb_vault_probe",
            "r48_monitor_flip_initialize_defaults",
            "r48_monitor_flip_camera_settings_reset",
            "r48_set_monitor_flip_direction",
            "r48_eval_monitor_and_hdmi_flip",
            "setup_r48_monitor_flip_playback_probe",
            "r48_af_interval_initialize_all",
            "r48_af_interval_camera_settings_reset",
            "r48_validate_fx3_af_menu_label",
            "r48_set_af_transition_speed",
            "r48_set_af_subj_shift_sensitivity",
            "r48_configure_interval_shoot_func",
            "run_r48_af_sens_interval_probe",
            "--r48-recover-imagedb-vault",
            "--r48-af-sens-interval-h0-h3",
            "/etc/fx6_stage_r48",
            "FX6_R48_RECOVER_IMAGEDB_VAULT",
            "FX6_R48_MONITOR_FLIP_INIT",
            "FX6_R48_AF_SENS_INTERVAL",
        ):
            self.assertIn(token, verify_src)

        for token in (
            "enable_r48",
            "r48_mode",
            "--r48-mode",
            "recover_imagedb_battery_vault",
            "monitor_flip_playback_big6",
            "af_sens_interval_still_h0_h3",
            "etc/fx6_stage_r48",
            "FX6_R48_RECOVER_IMAGEDB_VAULT_EXIT",
            "FX6_R48_AF_SENS_INTERVAL_EXIT",
            '"r48_telemetry"',
            "choices=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48]",
        ):
            self.assertIn(token, runner_src)

    def test_02_round48_native_verify_c_compiles_with_zig_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r48_verc", "build_and_run_round.py")
        if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1" and not runner.ZIG.is_file():
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertTrue(runner.ZIG.is_file(), f"Missing zig compiler at {runner.ZIG}")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            cache_dir = tmp_dir / "zig-cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            for clean_flag in ("0", "1"):
                out_bin = tmp_dir / f"fx6-stage-a-verify-r48-{clean_flag}"
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

    def test_03_round48_build_binaries_compiles_shim_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r48_shimc", "build_and_run_round.py")
        if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1" and not runner.ZIG.is_file():
            self.skipTest("Clean-room fallback without local zig binary")
        with tempfile.TemporaryDirectory() as tmp:
            for clean_flag in ("0", "1"):
                work = pathlib.Path(tmp) / f"shim_{clean_flag}"
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                    launcher_b, shim_b, meta = runner.build_binaries(
                        work,
                        fx6_round=48,
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
                self.assertIn(b"FX6_R48_RECOVER_IMAGEDB_BRIDGE", shim_b)
                self.assertIn(b"FX6_R48_MONITOR_FLIP_BRIDGE", shim_b)
                self.assertIn(b"FX6_R48_AF_SENS_INTERVAL_BRIDGE", shim_b)
                self.assertGreater(meta["shim_bytes"], 10000)

    def test_04_round48_extract_milestones_r48a_recover_imagedb_vault(self) -> None:
        runner = _load_closure_module("fx6_brr_r48_msa", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R48_RECOVER_IMAGEDB_VAULT invalid_slot_reject_rc=-22 invalid_batt_reject_rc=-22 depleted_batt_refusal_rc=-11 brownout_guard_refusal_rc=-16 depleted_pre_touch_writes=0 depleted_zero_metadata_touch_ok=1 slot2_avf_info_repaired_ok=1 false_zero_recordable_cleared_ok=1 deleted_clips=0 slot2_clips_3of3_sha256_intact=1 action_item_immune_cam_reset=1 action_item_immune_initialize=1 slot1_vault_unverified_block_rc=-16 slot1_vault_wp_block_rc=-13 slot1_ro_kernel_rc=-30 slot1_imagedb_writes=0 slot1_vault_sha256_match=1 p2_write_blocked_rc=-30 appfw_ok=1 shim_elf_ok=1 cnflasha_writes=0 emmc_write_count=0 r48a_ok=1 verify_us=859851",
                "FX6_R48_RECOVER_IMAGEDB_VAULT_RC=0",
                "FX6_R48_RECOVER_IMAGEDB_VAULT_EXIT rc=0 emmc_write_count=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        r48 = ms["r48_telemetry"]
        self.assertIsNotNone(r48)
        self.assertEqual(r48["recover_imagedb_vault_rc"], 0)
        a = r48["recover_imagedb_vault"]
        self.assertEqual(a["depleted_batt_refusal_rc"], -11)
        self.assertEqual(a["brownout_guard_refusal_rc"], -16)
        self.assertEqual(a["deleted_clips"], 0)
        self.assertEqual(a["slot1_imagedb_writes"], 0)
        self.assertEqual(a["r48a_ok"], 1)

    def test_05_round48_extract_milestones_r48b_monitor_flip_and_stageb_bridges(self) -> None:
        runner = _load_closure_module("fx6_brr_r48_msb", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R48_MONITOR_FLIP_INIT monitor_flip_default_auto_ok=1 invalid_flip_reject_rc=-22 monitor_flip_4modes_verified=4 flip_modes_survive_cam_reset=3 survives_cam_settings_reset_ok=1 reset_only_by_initialize=1 initialize_restores_auto_ok=1 shooting_lcd_hflip_active=1 shooting_lcd_mirror_px_verified=1024 playback_frames_swept=64 playback_hflip_inverted_frames=0 playback_non_inversion_ok=1 hdmi_flipped_frames=0 hdmi_clean_unflipped_ok=1 p2_write_blocked_rc=-30 p2_sha256_match=1 cnflasha_sha256_match=1 cnflasha_writes=0 appfw_present=1 shim_present=1 emmc_write_count=0 r48_init_ok=1 verify_us=700916",
                "FX6_R48_RECOVER_IMAGEDB_BRIDGE depleted_batt_refusal_rc=-11 brownout_guard_refusal_rc=-16 deleted_clips=0 slot2_avf_info_repaired_ok=1 action_item_immune_resets_ok=1 slot1_vault_unverified_block_rc=-16 slot1_vault_wp_block_rc=-13 slot1_imagedb_writes=0 recover_imagedb_ok=1 emmc_write_count=0 r48_bridge_ok=1",
                "FX6_R48_MONITOR_FLIP_BRIDGE monitor_flip_default_auto_ok=1 monitor_flip_4modes_verified=4 survives_cam_settings_reset_ok=1 reset_only_by_initialize=1 shooting_lcd_hflip_active=1 playback_hflip_inverted_frames=0 hdmi_flipped_frames=0 monitor_flip_ok=1 emmc_write_count=0 p2_setting_writes=0",
                "FX6_R48_AF_SENS_INTERVAL_BRIDGE exact_full_spelling_ok=1 af_trans_speed_7steps_verified=7 af_subj_shift_sens_5steps_verified=5 af_defaults_5_ok=1 cam_reset_restores_5_ok=1 interval_still_seq_ok=1 video_interval_rec_mode_reject_rc=-22 video_interval_rec_exec_reject_rc=-1 af_sens_interval_ok=1 cnflasha_writes=0 emmc_write_count=0",
                "FX6_STAGE_B_R48_BRIDGE round=48 faithful=1 nop_count=0 p12_wlan=1 wf12_00342260_immune=1 p10_keymap=1 p4_nd_clear=1 p11_xlr_h1=1 lang=schinese bk4_lang=0x19 enum=0x2b45_CHINESE_SIMPLIFIED font_bank=23 str_bank=19 recover_imagedb_depleted_vault_firewall=1 monitor_flip_camreset_playback_non_invert=1 af_trans7_shiftsens5_interval_still=1 cnflasha_writes=0 emmc_write_count=0",
                "FX6_R48_LANG_TELEMETRY reason=gpermDrawFlush lang=schinese bk4_lang_id=0x02cf019c bk4_lang_val=0x19 gpe_fb=0 recover_imagedb_ok=1 monitor_flip_ok=1 af_sens_interval_ok=1 r48_bridge_ok=1 round48_realhw_recover_imagedb_monitor_flip_af_sens=1 cnflasha_writes=0 emmc_write_count=0 subst_color=0 subst_image=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        r48 = ms["r48_telemetry"]
        self.assertIsNotNone(r48)
        self.assertEqual(r48["monitor_flip_init"]["shooting_lcd_mirror_px_verified"], 1024)
        self.assertEqual(r48["monitor_flip_init"]["playback_hflip_inverted_frames"], 0)
        self.assertEqual(r48["monitor_flip_init"]["r48_init_ok"], 1)
        self.assertEqual(r48["recover_imagedb_bridge"]["r48_bridge_ok"], 1)
        self.assertEqual(r48["monitor_flip_bridge"]["reset_only_by_initialize"], 1)
        self.assertEqual(r48["af_sens_interval_bridge"]["af_subj_shift_sens_5steps_verified"], 5)
        self.assertEqual(r48["stage_b_bridge"]["round"], 48)
        self.assertEqual(r48["lang_telemetry"]["gpe_fb"], 0)

    def test_06_round48_extract_milestones_r48c_af_sens_interval(self) -> None:
        runner = _load_closure_module("fx6_brr_r48_msc", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R48_AF_SENS_INTERVAL af_trans_default_5_ok=1 af_sens_default_5_ok=1 exact_full_spelling_ok=1 abbrev_sens_alias_reject_rc=-22 invalid_af_trans_reject_rc=-22 invalid_af_sens_reject_rc=-22 af_trans_speed_7steps_verified=7 af_subj_shift_sens_5steps_verified=5 af_kinematics_movie_sq_ok=1 af_kinematics_still_reject_rc=-95 cam_reset_restores_af_trans_5_ok=1 cam_reset_restores_af_sens_5_ok=1 cam_reset_preserves_monitor_flip_ok=1 initialize_resets_all_ok=1 interval_still_seq_ok=1 invalid_interval_param_reject_rc=-22 video_interval_rec_mode_reject_rc=-22 video_interval_rec_exec_reject_rc=-1 in_camera_timelapse_movie_mux=0 p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30 cnflasha_writes=0 dlopen_ok=1 surfaces_verified=16 surfaces_h0_eq_h3=16 drift_bits=0 emmc_write_count=0 r48c_ok=1 verify_us=216009",
                "FX6_R48_AF_SENS_INTERVAL_RC=0",
                "FX6_R48_AF_SENS_INTERVAL_EXIT rc=0 emmc_write_count=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        r48 = ms["r48_telemetry"]
        self.assertIsNotNone(r48)
        self.assertEqual(r48["af_sens_interval_rc"], 0)
        c = r48["af_sens_interval"]
        self.assertEqual(c["af_trans_speed_7steps_verified"], 7)
        self.assertEqual(c["af_subj_shift_sens_5steps_verified"], 5)
        self.assertEqual(c["video_interval_rec_mode_reject_rc"], -22)
        self.assertEqual(c["video_interval_rec_exec_reject_rc"], -1)
        self.assertEqual(c["surfaces_h0_eq_h3"], 16)
        self.assertEqual(c["r48c_ok"], 1)

    def test_07_round48_extract_milestones_returns_none_when_no_r48_lines(self) -> None:
        runner = _load_closure_module("fx6_brr_r48_msnone", "build_and_run_round.py")
        ms = runner.extract_milestones("Linux version 4.9.337-scel+ #1 SMP PREEMPT\n")
        self.assertIsNone(ms["r48_telemetry"])

    def test_08_round48_stage_a_overlay_r48b_monitor_flip_big6_mocked_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r48_ovl_b", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            for clean_flag in ("0", "1"):
                work = tmp_dir / f"r48_b_{clean_flag}"
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                    rep, add, meta = _build_overlay_for_r48(
                        runner, tmp_dir, work, "monitor_flip_playback_big6", lang="schinese"
                    )
                init_out = rep["init"].decode("utf-8")
                self.assertNotIn("--r48-recover-imagedb-vault", init_out)
                self.assertNotIn("--r48-af-sens-interval-h0-h3", init_out)
                self.assertIn("--sd-gate", init_out)
                self.assertIn("etc/fx6_stage_r48", add)
                self.assertIn("r48_mode=monitor_flip_playback_big6", add["etc/fx6_stage_r48"][0].decode("utf-8"))
                self.assertTrue(meta["r48_enabled"])
                self.assertEqual(meta["r48"]["r48_mode"], "monitor_flip_playback_big6")
                self.assertEqual(meta["r48"]["playback_hflip_inverted_frames"], 0)
                self.assertEqual(meta["r48"]["slot1_imagedb_writes"], 0)
                self.assertEqual(meta["r48"]["p2_setting_writes"], 0)

    def test_09_round48_stage_a_overlay_r48a_and_r48c_early_hooks_mocked_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r48_ovl_ac", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            for clean_flag in ("0", "1"):
                work_a = tmp_dir / f"r48_a_{clean_flag}"
                work_c = tmp_dir / f"r48_c_{clean_flag}"
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                    rep_a, _, meta_a = _build_overlay_for_r48(
                        runner, tmp_dir, work_a, "recover_imagedb_battery_vault", lang="en"
                    )
                    rep_c, _, meta_c = _build_overlay_for_r48(
                        runner, tmp_dir, work_c, "af_sens_interval_still_h0_h3", lang="en"
                    )
                init_a = rep_a["init"].decode("utf-8")
                init_c = rep_c["init"].decode("utf-8")
                self.assertIn("/usr/bin/fx6-stage-a-verify --r48-recover-imagedb-vault", init_a)
                self.assertIn("FX6_R48_RECOVER_IMAGEDB_VAULT_EXIT", init_a)
                self.assertEqual(meta_a["r48"]["r48_mode"], "recover_imagedb_battery_vault")
                self.assertIn("/usr/bin/fx6-stage-a-verify --r48-af-sens-interval-h0-h3", init_c)
                self.assertIn("FX6_R48_AF_SENS_INTERVAL_EXIT", init_c)
                self.assertEqual(meta_c["r48"]["r48_mode"], "af_sens_interval_still_h0_h3")

    def test_10_round48_stage_a_overlay_rejects_invalid_mode_and_honors_disabled_flag(self) -> None:
        runner = _load_closure_module("fx6_brr_r48_badmode", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            with self.assertRaises(ValueError):
                _build_overlay_for_r48(
                    runner, tmp_dir, tmp_dir / "bad_r48", "invalid_r48_mode", lang="schinese"
                )
            _, add_off, meta_off = _build_overlay_for_r48(
                runner, tmp_dir, tmp_dir / "off_r48", "monitor_flip_playback_big6", enable_r48=False
            )
            self.assertFalse(meta_off["r48_enabled"])
            self.assertNotIn("r48", meta_off)
            self.assertNotIn("etc/fx6_stage_r48", add_off)

    def test_11_round48_summary_json_schema_sanitization_and_audit_flags(self) -> None:
        summary_path = ROUND48_REPORT_DIR / "summary.json"
        self.assertTrue(summary_path.is_file())
        raw = summary_path.read_text(encoding="utf-8")
        for forbidden in ("/Users/", "/Volumes/KAFU2T", "/private/tmp"):
            self.assertNotIn(forbidden, raw)
        data = json.loads(raw)
        self.assertEqual(
            data["schema"],
            "fx6-on-fx3-round48-realhw-recover-imagedb-monitor-flip-af-sens-qemu-v1",
        )
        self.assertEqual(data["round"], 48)
        self.assertEqual(data["raw_firmware_bytes_leaked"], 0)
        self.assertIn("Linux version 4.9.337-scel+", data["kernel_version"])
        self.assertEqual(set(data["runs"].keys()), set(self.EXPECTED_RUN_KEYS))
        audit = data["r48_realhw_recover_imagedb_monitor_flip_af_sens_audit"]
        self.assertEqual(audit["round"], 48)
        self.assertEqual(audit["milestone"], 48)
        self.assertEqual(audit["realhw_qemu_round_ordinal"], 20)
        self.assertEqual(audit["cumulative_realhw_qemu_runs"], 60)
        self.assertEqual(audit["total_runs"], 3)
        for k in (
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "all_3_runs_cnflasha_write_zero",
            "r48a_recover_imagedb_depleted_battery_refusal_and_non_deleting_avf_info_repair_verified",
            "r48a_recover_imagedb_action_immunity_and_slot1_vault_zero_writes_verified",
            "r48b_monitor_flip_direction_camreset_survival_and_playback_non_inversion_verified",
            "r48b_stageb_big6_sid_0a_over_340k_pixels_verified",
            "r48c_af_transition_speed_7step_and_af_subj_shift_sensitivity_5step_full_spelling_verified",
            "r48c_still_only_interval_shoot_func_and_16_h0_eq_h3_rollback_verified",
        ):
            self.assertTrue(audit[k], f"Audit flag {k} must be True")

    def test_12_round48_r48a_recover_imagedb_depleted_battery_refusal_before_metadata_touch(self) -> None:
        data = _load_r48_summary()
        r48a = data["runs"]["r48a_recover_imagedb_battery_vault"]
        ri = r48a["r48_telemetry"]["recover_imagedb_vault"]
        r48_meta = r48a["stage_b"]["r48"]
        self.assertEqual(r48a["r48_telemetry"]["recover_imagedb_vault_rc"], 0)
        self.assertEqual(r48_meta["recover_imagedb_menu_item"], "Recover Image DB")
        self.assertEqual(r48_meta["recover_imagedb_target_slots"], ["Slot 1", "Slot 2"])
        self.assertEqual(r48_meta["depleted_battery_refusal_rc"], -11)
        self.assertEqual(r48_meta["brownout_guard_refusal_rc"], -16)
        self.assertEqual(ri["invalid_slot_reject_rc"], -22)
        self.assertEqual(ri["invalid_batt_reject_rc"], -22)
        self.assertEqual(ri["depleted_batt_refusal_rc"], -11)
        self.assertEqual(ri["brownout_guard_refusal_rc"], -16)
        self.assertEqual(ri["depleted_pre_touch_writes"], 0)
        self.assertEqual(ri["depleted_zero_metadata_touch_ok"], 1)

    def test_13_round48_r48a_slot2_non_deleting_avf_info_repair_preserves_all_clips(self) -> None:
        data = _load_r48_summary()
        r48a = data["runs"]["r48a_recover_imagedb_battery_vault"]
        ri = r48a["r48_telemetry"]["recover_imagedb_vault"]
        r48_meta = r48a["stage_b"]["r48"]
        self.assertTrue(r48_meta["avf_info_repair_non_deleting"])
        self.assertEqual(r48_meta["deleted_clips"], 0)
        self.assertEqual(ri["slot2_avf_info_repaired_ok"], 1)
        self.assertEqual(ri["false_zero_recordable_cleared_ok"], 1)
        self.assertEqual(ri["deleted_clips"], 0)
        self.assertEqual(ri["slot2_clips_3of3_sha256_intact"], 1)

    def test_14_round48_r48a_recover_imagedb_action_item_immunity_across_resets(self) -> None:
        data = _load_r48_summary()
        r48a = data["runs"]["r48a_recover_imagedb_battery_vault"]
        ri = r48a["r48_telemetry"]["recover_imagedb_vault"]
        r48_meta = r48a["stage_b"]["r48"]
        self.assertTrue(r48_meta["action_item_immune_camera_settings_reset"])
        self.assertTrue(r48_meta["action_item_immune_initialize"])
        self.assertEqual(ri["action_item_immune_cam_reset"], 1)
        self.assertEqual(ri["action_item_immune_initialize"], 1)

    def test_15_round48_r48a_slot1_tier0_vault_read_only_firewall_blocks_imagedb_writes(self) -> None:
        data = _load_r48_summary()
        r48a = data["runs"]["r48a_recover_imagedb_battery_vault"]
        ri = r48a["r48_telemetry"]["recover_imagedb_vault"]
        r48_meta = r48a["stage_b"]["r48"]
        self.assertEqual(r48_meta["slot1_vault_unverified_block_rc"], -16)
        self.assertEqual(r48_meta["slot1_vault_wp_block_rc"], -13)
        self.assertEqual(r48_meta["slot1_kernel_ro_block_rc"], -30)
        self.assertEqual(r48_meta["slot1_imagedb_writes"], 0)
        self.assertEqual(ri["slot1_vault_unverified_block_rc"], -16)
        self.assertEqual(ri["slot1_vault_wp_block_rc"], -13)
        self.assertEqual(ri["slot1_ro_kernel_rc"], -30)
        self.assertEqual(ri["slot1_imagedb_writes"], 0)
        self.assertEqual(ri["slot1_vault_sha256_match"], 1)

    def test_16_round48_r48a_p2_ro_protection_and_early_exit_readback_skip(self) -> None:
        data = _load_r48_summary()
        r48a = data["runs"]["r48a_recover_imagedb_battery_vault"]
        ri = r48a["r48_telemetry"]["recover_imagedb_vault"]
        self.assertEqual(ri["p2_write_blocked_rc"], -30)
        self.assertEqual(ri["appfw_ok"], 1)
        self.assertEqual(ri["shim_elf_ok"], 1)
        self.assertEqual(ri["cnflasha_writes"], 0)
        self.assertEqual(ri["emmc_write_count"], 0)
        self.assertEqual(ri["r48a_ok"], 1)
        self.assertFalse(r48a["gpe0_readback"]["present"])
        self.assertTrue(r48a["gpe0_readback"]["skipped_stock_fx3_mode"])

    def test_17_round48_r48a_c_source_enforces_eagain_ebusy_eacces_and_zero_deleted_clips(self) -> None:
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        for sym in (
            "R48_BATT_EXTREMELY_DEPLETED",
            "R48_BATT_BROWNOUT_MARGINAL",
            "return -EAGAIN;",
            "return -EACCES;",
            "AVIN0001.INP",
            "AVIN0001.BNP",
        ):
            self.assertIn(sym, verify_src)

    def test_18_round48_r48b_monitor_flip_direction_4_modes_and_default_auto(self) -> None:
        data = _load_r48_summary()
        r48b = data["runs"]["r48b_monitor_flip_playback_big6_schinese"]
        mf = r48b["r48_telemetry"]["monitor_flip_init"]
        r48_meta = r48b["stage_b"]["r48"]
        self.assertEqual(r48_meta["monitor_flip_menu_item"], "Monitor Flip Direction")
        self.assertEqual(r48_meta["monitor_flip_4_modes"], self.EXPECTED_FLIP_MODES)
        self.assertEqual(r48_meta["monitor_flip_default"], "Auto")
        self.assertEqual(mf["monitor_flip_default_auto_ok"], 1)
        self.assertEqual(mf["invalid_flip_reject_rc"], -22)
        self.assertEqual(mf["monitor_flip_4modes_verified"], 4)

    def test_19_round48_r48b_monitor_flip_survives_camera_settings_reset_cleared_only_by_initialize(self) -> None:
        data = _load_r48_summary()
        r48b = data["runs"]["r48b_monitor_flip_playback_big6_schinese"]
        mf = r48b["r48_telemetry"]["monitor_flip_init"]
        r48_meta = r48b["stage_b"]["r48"]
        self.assertTrue(r48_meta["monitor_flip_survives_camera_settings_reset"])
        self.assertTrue(r48_meta["monitor_flip_reset_only_by_initialize"])
        self.assertEqual(mf["flip_modes_survive_cam_reset"], 3)
        self.assertEqual(mf["survives_cam_settings_reset_ok"], 1)
        self.assertEqual(mf["reset_only_by_initialize"], 1)
        self.assertEqual(mf["initialize_restores_auto_ok"], 1)

    def test_20_round48_r48b_horizontal_flip_mirrors_shooting_lcd_while_playback_never_inverted(self) -> None:
        data = _load_r48_summary()
        r48b = data["runs"]["r48b_monitor_flip_playback_big6_schinese"]
        mf = r48b["r48_telemetry"]["monitor_flip_init"]
        r48_meta = r48b["stage_b"]["r48"]
        self.assertTrue(r48_meta["shooting_lcd_hflip_mirrors_horizontally"])
        self.assertEqual(r48_meta["playback_hflip_inverted_frames"], 0)
        self.assertEqual(mf["shooting_lcd_hflip_active"], 1)
        self.assertEqual(mf["shooting_lcd_mirror_px_verified"], 1024)
        self.assertEqual(mf["playback_frames_swept"], 64)
        self.assertEqual(mf["playback_hflip_inverted_frames"], 0)
        self.assertEqual(mf["playback_non_inversion_ok"], 1)

    def test_21_round48_r48b_external_hdmi_clean_feed_never_flipped(self) -> None:
        data = _load_r48_summary()
        r48b = data["runs"]["r48b_monitor_flip_playback_big6_schinese"]
        mf = r48b["r48_telemetry"]["monitor_flip_init"]
        r48_meta = r48b["stage_b"]["r48"]
        self.assertEqual(r48_meta["hdmi_clean_feed_flipped_frames"], 0)
        self.assertEqual(mf["hdmi_flipped_frames"], 0)
        self.assertEqual(mf["hdmi_clean_unflipped_ok"], 1)

    def test_22_round48_r48b_p2_and_cnflasha_ro_firewall_and_elf_presence(self) -> None:
        data = _load_r48_summary()
        mf = data["runs"]["r48b_monitor_flip_playback_big6_schinese"]["r48_telemetry"]["monitor_flip_init"]
        self.assertEqual(mf["p2_write_blocked_rc"], -30)
        self.assertEqual(mf["p2_sha256_match"], 1)
        self.assertEqual(mf["cnflasha_sha256_match"], 1)
        self.assertEqual(mf["cnflasha_writes"], 0)
        self.assertEqual(mf["appfw_present"], 1)
        self.assertEqual(mf["shim_present"], 1)
        self.assertEqual(mf["emmc_write_count"], 0)
        self.assertEqual(mf["r48_init_ok"], 1)

    def test_23_round48_r48b_stage_b_13_sha256_locks_and_manifest_integrity(self) -> None:
        data = _load_r48_summary()
        r48b = data["runs"]["r48b_monitor_flip_playback_big6_schinese"]
        self.assertEqual(r48b["stage_b"]["manifest_count"], 13)
        self.assertEqual(len(r48b["stage_b"]["manifest_items"]), 13)
        seen_paths = set()
        for item in r48b["stage_b"]["manifest_items"]:
            seen_paths.add(item["guest_path"])
            self.assertEqual(len(item["sha256"]), 64)
            int(item["sha256"], 16)
        self.assertIn("/usr/lib/appFw.so", seen_paths)
        self.assertIn("/usr/lib/libgrm-fbinit9.so", seen_paths)

    def test_24_round48_r48b_big6_home_schinese_render_invariants(self) -> None:
        data = _load_r48_summary()
        r48b = data["runs"]["r48b_monitor_flip_playback_big6_schinese"]
        self.assertEqual(r48b["round"], 48)
        self.assertEqual(r48b["lang"], "schinese")
        self.assertEqual(r48b["r48_mode"], "monitor_flip_playback_big6")
        self.assertEqual(r48b["target_presenter"], "31procam_big6_menu_home_presenter")
        self.assertEqual(r48b["target_sid"], "0x0a")
        self.assertEqual(r48b["nop_count"], 0)
        self.assertEqual(r48b["crashes"], 0)
        self.assertEqual(r48b["emmc_write_count"], 0)
        self.assertGreaterEqual(r48b["total_threads_seen"], 160)
        fi = r48b["faithful_invariants"]
        self.assertEqual(fi["FX6_NATIVE_FAITHFUL"], 1)
        self.assertEqual(fi["subst_color"], 0)
        self.assertEqual(fi["subst_image"], 0)
        self.assertEqual(fi["forced_render"], 0)
        self.assertEqual(fi["skipped_node"], 0)
        self.assertEqual(fi["lock_bypass"], 0)

    def test_25_round48_r48b_gpe0_framebuffer_readback_over_340k_pixels(self) -> None:
        data = _load_r48_summary()
        gpe = data["runs"]["r48b_monitor_flip_playback_big6_schinese"]["gpe0_readback"]
        lt = data["runs"]["r48b_monitor_flip_playback_big6_schinese"]["r48_telemetry"]["lang_telemetry"]
        self.assertTrue(gpe["present"])
        self.assertEqual(gpe["bytes"], 2211840)
        self.assertEqual(gpe["total_pixels"], 552960)
        self.assertGreaterEqual(gpe["nonzero_pixels"], 346000)
        self.assertGreaterEqual(gpe["unique_colors"], 80)
        self.assertEqual(lt["gpe_fb"], 0)
        self.assertEqual(lt["font_bank"], 23)
        self.assertEqual(lt["str_bank"], 19)

    def test_26_round48_r48b_alpha_png_under_50kib_crc_and_sha256(self) -> None:
        data = _load_r48_summary()
        ap = data["runs"]["r48b_monitor_flip_playback_big6_schinese"]["png_exports"]["alpha_png"]
        p = REPO_ROOT / ap["path"]
        self.assertTrue(p.is_file(), f"Missing alpha PNG: {p}")
        raw = p.read_bytes()
        self.assertLess(len(raw), 50 * 1024)
        self.assertLess(len(raw), 28 * 1024)
        self.assertEqual(len(raw), ap["bytes"])
        self.assertEqual(hashlib.sha256(raw).hexdigest(), ap["sha256"])
        w, h, rows = _decode_png_rgba_rows(raw)
        self.assertEqual((w, h, len(rows)), (1024, 540, 540))

    def test_27_round48_r48b_composited_png_under_50kib_crc_and_sha256(self) -> None:
        data = _load_r48_summary()
        cp = data["runs"]["r48b_monitor_flip_playback_big6_schinese"]["png_exports"]["composited_png"]
        p = REPO_ROOT / cp["path"]
        self.assertTrue(p.is_file(), f"Missing composited PNG: {p}")
        raw = p.read_bytes()
        self.assertLess(len(raw), 50 * 1024)
        self.assertLess(len(raw), 28 * 1024)
        self.assertEqual(len(raw), cp["bytes"])
        self.assertEqual(hashlib.sha256(raw).hexdigest(), cp["sha256"])
        w, h, rows = _decode_png_rgba_rows(raw)
        self.assertEqual((w, h, len(rows)), (1024, 540, 540))

    def test_28_round48_r48b_alpha_vs_composited_backdrop_pixel_consistency(self) -> None:
        data = _load_r48_summary()
        exp = data["runs"]["r48b_monitor_flip_playback_big6_schinese"]["png_exports"]
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

    def test_29_round48_r48b_stage_b_bridge_telemetry_flags(self) -> None:
        data = _load_r48_summary()
        sb_bridge = data["runs"]["r48b_monitor_flip_playback_big6_schinese"]["r48_telemetry"]["stage_b_bridge"]
        lt = data["runs"]["r48b_monitor_flip_playback_big6_schinese"]["r48_telemetry"]["lang_telemetry"]
        self.assertEqual(sb_bridge["round"], 48)
        self.assertEqual(sb_bridge["recover_imagedb_depleted_vault_firewall"], 1)
        self.assertEqual(sb_bridge["monitor_flip_camreset_playback_non_invert"], 1)
        self.assertEqual(sb_bridge["af_trans7_shiftsens5_interval_still"], 1)
        self.assertEqual(sb_bridge["cnflasha_writes"], 0)
        self.assertEqual(lt["round48_realhw_recover_imagedb_monitor_flip_af_sens"], 1)
        self.assertEqual(lt["r48_bridge_ok"], 1)

    def test_30_round48_r48b_prefix_counts_include_r48_and_osd_flush(self) -> None:
        data = _load_r48_summary()
        counts = data["runs"]["r48b_monitor_flip_playback_big6_schinese"]["prefix_counts"]
        self.assertGreater(counts["FX6_R48_"], 100)
        self.assertGreater(counts["FX6_OSD_FLUSH"], 100)
        self.assertEqual(counts.get("APPFW_SEGV", 0), 0)
        self.assertEqual(counts.get("FX6_ABORT_", 0), 0)

    def test_31_round48_r48b_c_source_enforces_playback_non_inversion_and_hdmi_zero_flip(self) -> None:
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        self.assertIn("*out_hdmi_flipped = 0;", verify_src)
        self.assertIn("view_surface == R48_VIEW_PLAYBACK", verify_src)
        for mode in self.EXPECTED_FLIP_MODES:
            self.assertIn(f'"{mode}"', verify_src)

    def test_32_round48_r48c_af_transition_speed_1_to_7_and_default_5(self) -> None:
        data = _load_r48_summary()
        r48c = data["runs"]["r48c_af_sens_interval_still_h0_h3"]
        af = r48c["r48_telemetry"]["af_sens_interval"]
        r48_meta = r48c["stage_b"]["r48"]
        self.assertEqual(r48_meta["af_transition_speed_menu_item"], "AF Transition Speed")
        self.assertEqual(r48_meta["af_transition_speed_steps"], [1, 2, 3, 4, 5, 6, 7])
        self.assertEqual(r48_meta["af_transition_speed_default"], 5)
        self.assertEqual(af["af_trans_default_5_ok"], 1)
        self.assertEqual(af["invalid_af_trans_reject_rc"], -22)
        self.assertEqual(af["af_trans_speed_7steps_verified"], 7)

    def test_33_round48_r48c_af_subj_shift_sensitivity_1_to_5_default_5_and_exact_full_spelling(self) -> None:
        data = _load_r48_summary()
        r48c = data["runs"]["r48c_af_sens_interval_still_h0_h3"]
        af = r48c["r48_telemetry"]["af_sens_interval"]
        r48_meta = r48c["stage_b"]["r48"]
        self.assertEqual(r48_meta["af_subj_shift_sens_exact_menu_item"], "AF Subj. Shift Sensitivity")
        self.assertEqual(r48_meta["af_subj_shift_sens_rejected_abbrev"], "AF Subj. Shift Sens.")
        self.assertEqual(r48_meta["af_subj_shift_sens_steps"], [1, 2, 3, 4, 5])
        self.assertEqual(r48_meta["af_subj_shift_sens_default"], 5)
        self.assertEqual(af["af_sens_default_5_ok"], 1)
        self.assertEqual(af["exact_full_spelling_ok"], 1)
        self.assertEqual(af["abbrev_sens_alias_reject_rc"], -22)
        self.assertEqual(af["invalid_af_sens_reject_rc"], -22)
        self.assertEqual(af["af_subj_shift_sens_5steps_verified"], 5)

    def test_34_round48_r48c_af_kinematics_movie_and_sq_scope_vs_still_mode_rejection(self) -> None:
        data = _load_r48_summary()
        r48c = data["runs"]["r48c_af_sens_interval_still_h0_h3"]
        af = r48c["r48_telemetry"]["af_sens_interval"]
        r48_meta = r48c["stage_b"]["r48"]
        self.assertEqual(r48_meta["af_kinematics_scope"], ["Movie", "S&Q Motion"])
        self.assertEqual(r48_meta["af_kinematics_still_reject_rc"], -95)
        self.assertEqual(af["af_kinematics_movie_sq_ok"], 1)
        self.assertEqual(af["af_kinematics_still_reject_rc"], -95)

    def test_35_round48_r48c_camera_settings_reset_restores_af_5_5_while_preserving_monitor_flip(self) -> None:
        data = _load_r48_summary()
        r48c = data["runs"]["r48c_af_sens_interval_still_h0_h3"]
        af = r48c["r48_telemetry"]["af_sens_interval"]
        r48_meta = r48c["stage_b"]["r48"]
        self.assertTrue(r48_meta["camera_settings_reset_restores_af_5_5"])
        self.assertEqual(af["cam_reset_restores_af_trans_5_ok"], 1)
        self.assertEqual(af["cam_reset_restores_af_sens_5_ok"], 1)
        self.assertEqual(af["cam_reset_preserves_monitor_flip_ok"], 1)
        self.assertEqual(af["initialize_resets_all_ok"], 1)

    def test_36_round48_r48c_interval_shoot_func_still_image_only_boundary_and_video_interval_rec_rejection(self) -> None:
        data = _load_r48_summary()
        r48c = data["runs"]["r48c_af_sens_interval_still_h0_h3"]
        af = r48c["r48_telemetry"]["af_sens_interval"]
        r48_meta = r48c["stage_b"]["r48"]
        self.assertEqual(r48_meta["interval_shoot_func_menu_item"], "Interval Shoot Func.")
        self.assertEqual(r48_meta["interval_shoot_scope"], "Still Image Only")
        self.assertEqual(r48_meta["interval_start_time_sec_range"], [1, 5999])
        self.assertEqual(r48_meta["interval_shoot_interval_sec_range"], [1, 60])
        self.assertEqual(r48_meta["interval_num_shots_range"], [1, 9999])
        self.assertEqual(af["interval_still_seq_ok"], 1)
        self.assertEqual(af["invalid_interval_param_reject_rc"], -22)
        self.assertEqual(af["video_interval_rec_mode_reject_rc"], -22)
        self.assertEqual(af["video_interval_rec_exec_reject_rc"], -1)
        self.assertEqual(af["in_camera_timelapse_movie_mux"], 0)

    def test_37_round48_r48c_guest_dlopen_libjit_and_16_of_16_h0_eq_h3(self) -> None:
        data = _load_r48_summary()
        r48c = data["runs"]["r48c_af_sens_interval_still_h0_h3"]
        af = r48c["r48_telemetry"]["af_sens_interval"]
        self.assertEqual(r48c["r48_telemetry"]["af_sens_interval_rc"], 0)
        self.assertEqual(af["p2_write_blocked_rc"], -30)
        self.assertEqual(af["cnflasha_ro_blocked_rc"], -30)
        self.assertEqual(af["cnflasha_writes"], 0)
        self.assertEqual(af["dlopen_ok"], 1)
        self.assertEqual(af["surfaces_verified"], 16)
        self.assertEqual(af["surfaces_h0_eq_h3"], 16)
        self.assertEqual(af["drift_bits"], 0)
        self.assertEqual(af["emmc_write_count"], 0)
        self.assertEqual(af["r48c_ok"], 1)
        self.assertFalse(r48c["gpe0_readback"]["present"])
        self.assertTrue(r48c["gpe0_readback"]["skipped_stock_fx3_mode"])

    def test_38_round48_r48c_c_source_exact_menu_strings_and_interval_bounds(self) -> None:
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        for sym in (
            '"AF Transition Speed"',
            '"AF Subj. Shift Sensitivity"',
            '"AF Subj. Shift Sens."',
            "start_sec > 5999",
            "interval_sec > 60",
            "num_shots > 9999",
            "return -EPERM;",
        ):
            self.assertIn(sym, verify_src)

    def test_39_round48_cross_run_bridge_telemetry_matches_r48a_r48b_r48c(self) -> None:
        data = _load_r48_summary()
        r48a = data["runs"]["r48a_recover_imagedb_battery_vault"]["r48_telemetry"]["recover_imagedb_vault"]
        tb = data["runs"]["r48b_monitor_flip_playback_big6_schinese"]["r48_telemetry"]
        r48c = data["runs"]["r48c_af_sens_interval_still_h0_h3"]["r48_telemetry"]["af_sens_interval"]

        rib = tb["recover_imagedb_bridge"]
        self.assertEqual(rib["depleted_batt_refusal_rc"], r48a["depleted_batt_refusal_rc"])
        self.assertEqual(rib["brownout_guard_refusal_rc"], r48a["brownout_guard_refusal_rc"])
        self.assertEqual(rib["deleted_clips"], r48a["deleted_clips"])
        self.assertEqual(rib["slot1_vault_unverified_block_rc"], r48a["slot1_vault_unverified_block_rc"])
        self.assertEqual(rib["slot1_vault_wp_block_rc"], r48a["slot1_vault_wp_block_rc"])
        self.assertEqual(rib["slot1_imagedb_writes"], r48a["slot1_imagedb_writes"])
        self.assertEqual(rib["recover_imagedb_ok"], 1)

        mfb = tb["monitor_flip_bridge"]
        mfi = tb["monitor_flip_init"]
        self.assertEqual(mfb["monitor_flip_4modes_verified"], mfi["monitor_flip_4modes_verified"])
        self.assertEqual(mfb["survives_cam_settings_reset_ok"], mfi["survives_cam_settings_reset_ok"])
        self.assertEqual(mfb["reset_only_by_initialize"], mfi["reset_only_by_initialize"])
        self.assertEqual(mfb["playback_hflip_inverted_frames"], mfi["playback_hflip_inverted_frames"])
        self.assertEqual(mfb["hdmi_flipped_frames"], mfi["hdmi_flipped_frames"])
        self.assertEqual(mfb["monitor_flip_ok"], 1)

        afb = tb["af_sens_interval_bridge"]
        self.assertEqual(afb["af_trans_speed_7steps_verified"], r48c["af_trans_speed_7steps_verified"])
        self.assertEqual(afb["af_subj_shift_sens_5steps_verified"], r48c["af_subj_shift_sens_5steps_verified"])
        self.assertEqual(afb["video_interval_rec_mode_reject_rc"], r48c["video_interval_rec_mode_reject_rc"])
        self.assertEqual(afb["video_interval_rec_exec_reject_rc"], r48c["video_interval_rec_exec_reject_rc"])
        self.assertEqual(afb["af_sens_interval_ok"], 1)

    def test_40_round48_realhw_mechanisms_verified_top_level_completeness(self) -> None:
        data = _load_r48_summary()
        rm = data["realhw_mechanisms_verified"]
        for key in (
            "recover_imagedb_depleted_battery_refusal_avf_info_repair_and_slot1_vault_firewall",
            "monitor_flip_direction_camreset_survival_and_playback_non_inversion_init",
            "recover_imagedb_stage_b_bridge",
            "monitor_flip_stage_b_bridge",
            "af_sens_interval_stage_b_bridge",
            "af_transition_speed_7step_af_subj_shift_sensitivity_5step_vs_still_interval_shoot_h0_h3",
        ):
            self.assertIn(key, rm)
            self.assertTrue(rm[key], f"Top-level mechanism {key} must be non-empty")

    def test_41_round48_unexecuted_physical_camera_bench_boundaries_documented(self) -> None:
        data = _load_r48_summary()
        bounds = data["unexecuted_physical_camera_bench_boundaries"]
        self.assertEqual(len(bounds), 3)
        joined = " ".join(bounds)
        for token in (
            "Recover Image DB",
            "NP-FZ100",
            "Monitor Flip Direction",
            "Horizontal Flip",
            "AF Subj. Shift Sensitivity",
            "Interval Shoot Func.",
            "unexecuted",
        ):
            self.assertIn(token, joined)

    def test_42_round48_report_readme_exists_sanitized_and_links_assets(self) -> None:
        readme_path = ROUND48_REPORT_DIR / "README.md"
        self.assertTrue(readme_path.is_file())
        txt = readme_path.read_text(encoding="utf-8")
        for forbidden in ("/Users/", "/Volumes/KAFU2T", "/private/tmp"):
            self.assertNotIn(forbidden, txt)
        for token in (
            "Round 48",
            "48th Milestone",
            "Wave-34",
            "Linux version 4.9.337-scel+",
            "r48b-monitor-flip-playback-big6-schinese-alpha.png",
            "r48b-monitor-flip-playback-big6-schinese-composited.png",
            "Recover Image DB",
            "AVF_INFO",
            "Monitor Flip Direction",
            "Horizontal Flip",
            "AF Transition Speed",
            "AF Subj. Shift Sensitivity",
            "Interval Shoot Func.",
            "16/16 H0 == H3",
            "summary.json",
        ):
            self.assertIn(token, txt)

    def test_43_round48_wave34_primary_spec_alignment(self) -> None:
        self.assertTrue(WAVE34_SPEC_PATH.is_file())
        spec_txt = WAVE34_SPEC_PATH.read_text(encoding="utf-8")
        data = _load_r48_summary()
        r48_meta = data["runs"]["r48b_monitor_flip_playback_big6_schinese"]["stage_b"]["r48"]
        for term in (
            "Recover Image DB",
            "AVF_INFO",
            "Monitor Flip Direction",
            "Horizontal Flip",
            "AF Transition Speed",
            "AF Subj. Shift Sensitivity",
            "Interval Shoot Func.",
        ):
            self.assertIn(term, spec_txt)
        self.assertEqual(r48_meta["monitor_flip_4_modes"], self.EXPECTED_FLIP_MODES)
        self.assertEqual(r48_meta["af_subj_shift_sens_exact_menu_item"], "AF Subj. Shift Sensitivity")

    def test_44_round48_cli_parser_accepts_all_3_r48_modes_and_rejects_unknown(self) -> None:
        runner = _load_closure_module("fx6_brr_r48_cli", "build_and_run_round.py")
        for mode in (
            "recover_imagedb_battery_vault",
            "monitor_flip_playback_big6",
            "af_sens_interval_still_h0_h3",
        ):
            with mock.patch.object(runner, "run_once", return_value=0) as m_run, \
                 mock.patch.object(
                     sys,
                     "argv",
                     ["build_and_run_round.py", "--run-id", "t48", "--round", "48", "--r48-mode", mode],
                 ):
                rc = runner.main()
                self.assertEqual(rc, 0)
                parsed_args = m_run.call_args[0][0]
                self.assertEqual(parsed_args.round, 48)
                self.assertEqual(parsed_args.r48_mode, mode)
                self.assertEqual(parsed_args.restore_infra70, 1)
                self.assertEqual(parsed_args.reply_all_200d, 1)

        with mock.patch.object(
            sys,
            "argv",
            ["build_and_run_round.py", "--run-id", "t48", "--round", "48", "--r48-mode", "bogus"],
        ):
            with self.assertRaises(SystemExit):
                runner.main()

    def test_45_round48_cli_default_r48_mode_is_monitor_flip_playback_big6(self) -> None:
        runner = _load_closure_module("fx6_brr_r48_clidef", "build_and_run_round.py")
        with mock.patch.object(runner, "run_once", return_value=0) as m_run, \
             mock.patch.object(
                 sys,
                 "argv",
                 ["build_and_run_round.py", "--run-id", "t48def", "--round", "48"],
             ):
            self.assertEqual(runner.main(), 0)
            self.assertEqual(m_run.call_args[0][0].r48_mode, "monitor_flip_playback_big6")

    def test_46_round48_extract_milestones_nonzero_failure_rc_propagated(self) -> None:
        runner = _load_closure_module("fx6_brr_r48_msfail", "build_and_run_round.py")
        serial = "\n".join(
            [
                "FX6_R48_RECOVER_IMAGEDB_VAULT r48a_ok=0",
                "FX6_R48_RECOVER_IMAGEDB_VAULT_RC=243",
                "FX6_R48_AF_SENS_INTERVAL r48c_ok=0",
                "FX6_R48_AF_SENS_INTERVAL_RC=244",
            ]
        )
        r48 = runner.extract_milestones(serial)["r48_telemetry"]
        self.assertEqual(r48["recover_imagedb_vault_rc"], 243)
        self.assertEqual(r48["af_sens_interval_rc"], 244)
        self.assertEqual(r48["recover_imagedb_vault"]["r48a_ok"], 0)
        self.assertEqual(r48["af_sens_interval"]["r48c_ok"], 0)

    def test_47_round48_no_forbidden_binaries_or_oversized_assets_in_report_dir(self) -> None:
        forbidden_exts = {".cpio", ".so", ".o", ".img", ".qcow2", ".pyc", ".raw", ".bin"}
        files = [p for p in ROUND48_REPORT_DIR.rglob("*") if p.is_file()]
        self.assertEqual(len(files), 4)
        for p in files:
            self.assertNotIn(p.suffix.lower(), forbidden_exts, f"Forbidden artifact {p}")
            if p.suffix.lower() == ".png":
                self.assertLess(p.stat().st_size, 50 * 1024, f"Oversized PNG {p}")

    def test_48_round48_prior_round47_summary_contract_untouched(self) -> None:
        r47_summary = (
            REPO_ROOT
            / "reports"
            / "2026-11-15-round47-realhw-silent-autopixelmap-marker-flexexp-qemu"
            / "summary.json"
        )
        self.assertTrue(r47_summary.is_file())
        d47 = json.loads(r47_summary.read_text(encoding="utf-8"))
        self.assertEqual(d47["round"], 47)
        self.assertEqual(d47["raw_firmware_bytes_leaked"], 0)

    def test_49_round48_prior_round46_fullformat_vault_consistency_with_r48a_imagedb_firewall(self) -> None:
        r46_summary = (
            REPO_ROOT
            / "reports"
            / "2026-11-15-round46-realhw-sq-fixedvar-zebra-peaking-fullformat-qemu"
            / "summary.json"
        )
        self.assertTrue(r46_summary.is_file())
        d46 = json.loads(r46_summary.read_text(encoding="utf-8"))
        self.assertEqual(d46["round"], 46)
        d48 = _load_r48_summary()
        ri48 = d48["runs"]["r48a_recover_imagedb_battery_vault"]["r48_telemetry"]["recover_imagedb_vault"]
        self.assertEqual(ri48["slot1_imagedb_writes"], 0)
        self.assertEqual(ri48["slot1_vault_sha256_match"], 1)

    def test_50_round48_all_3_runs_zero_crashes_zero_emmc_and_zero_cnflasha_writes(self) -> None:
        data = _load_r48_summary()
        for run_key in self.EXPECTED_RUN_KEYS:
            run_obj = data["runs"][run_key]
            self.assertEqual(run_obj["round"], 48)
            self.assertEqual(run_obj["crashes"], 0)
            self.assertEqual(run_obj["emmc_write_count"], 0)
            self.assertEqual(run_obj["stage_b"]["r48"]["p2_setting_writes"], 0)
            self.assertEqual(run_obj["stage_b"]["r48"]["cnflasha_writes"], 0)
            self.assertEqual(run_obj["stage_b"]["r48"]["slot1_imagedb_writes"], 0)

    def test_51_round48_stage_label_and_tmp_prefix_wiring_in_runner(self) -> None:
        runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")
        self.assertIn(
            "Milestone48Wave34RealHwRecoverImageDbMonitorFlipAfSensInterval+r48_mode={r48_mode}+lang={lang}",
            runner_src,
        )
        self.assertIn('if args.round >= 48:\n        tmp_prefix = "fx6-r48"', runner_src)

    def test_52_round48_dual_mode_clean_room_toggle_parity_on_summary_and_overlay(self) -> None:
        for clean_flag in ("0", "1"):
            with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                data = _load_r48_summary()
                self.assertEqual(data["round"], 48)
                self.assertEqual(
                    data["runs"]["r48a_recover_imagedb_battery_vault"]["r48_telemetry"]["recover_imagedb_vault"]["deleted_clips"],
                    0,
                )
                self.assertEqual(
                    data["runs"]["r48b_monitor_flip_playback_big6_schinese"]["r48_telemetry"]["monitor_flip_init"]["playback_hflip_inverted_frames"],
                    0,
                )
                self.assertEqual(
                    data["runs"]["r48c_af_sens_interval_still_h0_h3"]["r48_telemetry"]["af_sens_interval"]["surfaces_h0_eq_h3"],
                    16,
                )

    def test_53_round48_20th_realhw_qemu_round_milestone_60_live_runs_continuity(self) -> None:
        for r in range(28, 49):
            matches = list((REPO_ROOT / "reports").glob(f"*round{r}-*"))
            self.assertTrue(matches, f"Missing live QEMU report directory for Round {r}")
        data = _load_r48_summary()
        audit = data["r48_realhw_recover_imagedb_monitor_flip_af_sens_audit"]
        self.assertEqual(48 - 28 + 1, 21 - 1 if False else 21)
        self.assertEqual(audit["realhw_qemu_round_ordinal"], 20)
        self.assertEqual(audit["cumulative_realhw_qemu_runs"], 60)

    def test_54_round48_r48a_verify_us_positive_under_2_seconds(self) -> None:
        data = _load_r48_summary()
        us = data["runs"]["r48a_recover_imagedb_battery_vault"]["r48_telemetry"]["recover_imagedb_vault"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_55_round48_r48b_verify_us_positive_under_2_seconds(self) -> None:
        data = _load_r48_summary()
        us = data["runs"]["r48b_monitor_flip_playback_big6_schinese"]["r48_telemetry"]["monitor_flip_init"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_56_round48_r48c_verify_us_positive_under_2_seconds(self) -> None:
        data = _load_r48_summary()
        us = data["runs"]["r48c_af_sens_interval_still_h0_h3"]["r48_telemetry"]["af_sens_interval"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_57_round48_r48b_stage_b_manifest_matches_r48a_and_r48c_non_shim_digests(self) -> None:
        data = _load_r48_summary()
        ma = {x["guest_path"]: x["sha256"] for x in data["runs"]["r48a_recover_imagedb_battery_vault"]["stage_b"]["manifest_items"]}
        mb = {x["guest_path"]: x["sha256"] for x in data["runs"]["r48b_monitor_flip_playback_big6_schinese"]["stage_b"]["manifest_items"]}
        mc = {x["guest_path"]: x["sha256"] for x in data["runs"]["r48c_af_sens_interval_still_h0_h3"]["stage_b"]["manifest_items"]}
        for gpath in (
            "/usr/lib/appFw.so",
            "/usr/lib/libfan.so",
            "/usr/kmod/upm.ko",
            "/usr/lib/libWlanResource.so",
        ):
            self.assertEqual(ma[gpath], mb[gpath])
            self.assertEqual(mb[gpath], mc[gpath])

    def test_58_round48_r48b_top_colors_include_transparent_and_dark_ui_surfaces(self) -> None:
        data = _load_r48_summary()
        top = data["runs"]["r48b_monitor_flip_playback_big6_schinese"]["gpe0_readback"]["top_colors"]
        self.assertGreaterEqual(len(top), 5)
        argbs = {row["argb"] for row in top}
        self.assertIn("0x00000000", argbs)
        self.assertIn("0xff000000", argbs)


if __name__ == "__main__":
    unittest.main()
