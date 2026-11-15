#!/usr/bin/env python3
"""Offline dual-mode unit tests for FX6-on-FX3 Round 50 (50th Grand Milestone! / Wave-36 Live FX3 7.02 QEMU Rehearsal)."""
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
ROUND50_REPORT_DIR = (
    REPO_ROOT
    / "reports"
    / "2026-11-15-round50-milestone-realhw-shoe-audio-4ch-wind-saveload-c3-qemu"
)
WAVE36_SPEC_PATH = (
    REPO_ROOT
    / "reports"
    / "2026-11-15-global-sony-wave36-shoe-audio-4ch-wind-noise-builtin-only-saveload-c3-exclusions-intel"
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


def _build_overlay_for_r50(
    runner,
    tmp_dir: pathlib.Path,
    work: pathlib.Path,
    r50_mode: str,
    lang: str = "schinese",
    enable_r50: bool = True,
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
            enable_r49=True, r49_mode="emphasized_rec_grid_hdmi_big6",
            enable_r50=enable_r50, r50_mode=r50_mode,
            sd_manifest_mode="valid", lang=lang, shim_bytes=b"SHIM",
        )


def _load_r50_summary() -> dict:
    return json.loads((ROUND50_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))


class TestRound50MilestoneRealHwShoeAudio4chWindSaveLoadC3Qemu(unittest.TestCase):
    EXPECTED_RUN_KEYS = (
        "r50a_shoe_audio_4ch_osd_big6_schinese",
        "r50b_wind_noise_builtin_only_guard",
        "r50c_saveload_camset_c3_vault_h0_h3",
    )
    EXPECTED_SHOE_AUDIO_MODES = [
        "48kHz/16bit 2ch",
        "48kHz/24bit 2ch",
        "48kHz/24bit 4ch",
    ]
    EXPECTED_WIND_NOISE_MODES = [
        "Off",
        "On",
    ]
    EXPECTED_CLOUD_TARGETS = [
        "Cloud(Private)",
        "Cloud(Share)",
    ]
    EXPECTED_EXCLUDED_8_CATEGORIES = [
        "IPTC Information",
        "Copyright Info",
        "Custom White Balance (Custom 1/2/3)",
        "Face Memory",
        "FTP Transfer Func. Credentials",
        "Streaming RTMP/SRT Keys",
        "Wi-Fi SSID/Passphrases & Static IP",
        "Imported Root/Client TLS Certificates",
    ]

    def test_01_round50_c_and_python_source_contracts(self) -> None:
        shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")

        self.assertIn("#if FX6_ROUND >= 50", shim_src)
        for token in (
            "FX6_R50_SHOE_AUDIO_4CH_BRIDGE",
            "FX6_R50_WIND_NOISE_BRIDGE",
            "FX6_R50_SAVELOAD_C3_BRIDGE",
            "FX6_R50_LANG_TELEMETRY",
            "FX6_STAGE_B_R50_BRIDGE",
            "round50_milestone_realhw_shoe_audio_4ch_wind_saveload_c3=1",
        ):
            self.assertIn(token, shim_src)

        for token in (
            "r50_shoe_audio_initialize_defaults",
            "r50_shoe_audio_camera_settings_reset",
            "r50_set_shoe_audio_mode",
            "r50_eval_shoe_audio_routing_and_osd",
            "setup_r50_shoe_audio_4ch_osd_probe",
            "r50_wind_initialize_defaults",
            "r50_wind_camera_settings_reset",
            "r50_set_wind_noise_reduct",
            "r50_eval_body_wind_hpf_active",
            "run_r50_wind_noise_builtin_guard_probe",
            "r50_save_settings_to_target",
            "r50_load_settings_from_file",
            "run_r50_saveload_c3_vault_probe",
            "--r50-wind-noise-builtin-guard",
            "--r50-saveload-c3-vault-h0-h3",
            "/etc/fx6_stage_r50",
            "FX6_R50_SHOE_AUDIO_4CH_INIT",
            "FX6_R50_WIND_NOISE_GUARD",
            "FX6_R50_SAVELOAD_C3_VAULT",
        ):
            self.assertIn(token, verify_src)

        for token in (
            "enable_r50",
            "r50_mode",
            "--r50-mode",
            "shoe_audio_4ch_osd_big6",
            "wind_noise_builtin_only_guard",
            "saveload_camset_c3_vault_h0_h3",
            "etc/fx6_stage_r50",
            "FX6_R50_WIND_NOISE_GUARD_EXIT",
            "FX6_R50_SAVELOAD_C3_VAULT_EXIT",
            '"r50_telemetry"',
            "choices=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50]",
        ):
            self.assertIn(token, runner_src)

    def test_02_round50_native_verify_c_compiles_with_zig_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r50_verc", "build_and_run_round.py")
        if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1" and not runner.ZIG.is_file():
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertTrue(runner.ZIG.is_file(), f"Missing zig compiler at {runner.ZIG}")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            cache_dir = tmp_dir / "zig-cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            for clean_flag in ("0", "1"):
                out_bin = tmp_dir / f"fx6-stage-a-verify-r50-{clean_flag}"
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

    def test_03_round50_build_binaries_compiles_shim_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r50_shimc", "build_and_run_round.py")
        if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1" and not runner.ZIG.is_file():
            self.skipTest("Clean-room fallback without local zig binary")
        with tempfile.TemporaryDirectory() as tmp:
            for clean_flag in ("0", "1"):
                work = pathlib.Path(tmp) / f"shim_{clean_flag}"
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                    launcher_b, shim_b, meta = runner.build_binaries(
                        work,
                        fx6_round=50,
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
                self.assertIn(b"FX6_R50_SHOE_AUDIO_4CH_BRIDGE", shim_b)
                self.assertIn(b"FX6_R50_WIND_NOISE_BRIDGE", shim_b)
                self.assertIn(b"FX6_R50_SAVELOAD_C3_BRIDGE", shim_b)
                self.assertGreater(meta["shim_bytes"], 10000)

    def test_04_round50_extract_milestones_r50a_shoe_audio_4ch_and_stageb_bridges(self) -> None:
        runner = _load_closure_module("fx6_brr_r50_msa", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R50_SHOE_AUDIO_4CH_INIT shoe_audio_default_16b_2ch_ok=1 invalid_shoe_mode_reject_rc=-22 shoe_audio_3modes_verified=3 shoe_audio_camreset_restores_16b_2ch_ok=1 initialize_restores_16b_2ch_ok=1 lpcm_4ch_24bit_active_ok=1 osd_4ch_meter_channels=4 osd_2ch_meter_channels=2 osd_4ch_meter_bars_px=4096 osd_4ch_meter_ch1_to_ch4_ok=1 audio_off_lock_rc=-16 sq_motion_lock_rc=-16 sq_audio_tracks=0 audio_off_tracks=0 jack_35mm_shoe_set_lock_rc=-16 jack_35mm_override_channels=2 jack_35mm_override_bits=16 xlrh1_analog_24bit_4ch_reject_rc=-22 xlrh1_analog_override_channels=2 xlrh1_analog_override_bits=16 disqualified_4ch_active_leaks=0 p2_write_blocked_rc=-30 p2_sha256_match=1 cnflasha_sha256_match=1 cnflasha_writes=0 appfw_present=1 shim_present=1 emmc_write_count=0 r50_init_ok=1 verify_us=885578",
                "FX6_R50_SHOE_AUDIO_4CH_BRIDGE shoe_audio_default_16b_2ch_ok=1 shoe_audio_3modes_verified=3 shoe_audio_camreset_restores_16b_2ch_ok=1 osd_4ch_meter_channels=4 osd_2ch_meter_channels=2 osd_4ch_meter_bars_px=4096 osd_4ch_meter_ch1_to_ch4_ok=1 sq_audio_tracks=0 audio_off_tracks=0 sq_and_audio_off_0tracks_lock_ok=1 jack_35mm_override_channels=2 jack_35mm_2ch_override_lock_ok=1 xlrh1_analog_override_channels=2 xlrh1_analog_override_bits=16 xlrh1_analog_2ch_16b_override_ok=1 shoe_audio_4ch_osd_ok=1 emmc_write_count=0 r50_bridge_ok=1",
                "FX6_R50_WIND_NOISE_BRIDGE wind_noise_default_off_ok=1 wind_noise_2modes_verified=2 wind_camreset_restores_off_ok=1 builtin_mic_hpf_active_ok=1 ext_mic_sources_bypassed=4 external_mic_wind_reduct_active=0 indoor_low_wind_clamped_off_ok=1 sq_and_audio_off_lock_ok=1 wind_noise_builtin_ok=1 emmc_write_count=0 p2_setting_writes=0",
                "FX6_R50_SAVELOAD_C3_BRIDGE camset_10slots_verified=10 fx6_cross_model_reject_rc=-22 cloud_private_and_share_verified=2 excluded_8categories_verified=8 excluded_leaks=0 slot1_save_blocked_rc=-13 slot1_camset_writes=0 slot1_readonly_load_ok=1 saveload_c3_vault_ok=1 cnflasha_writes=0 emmc_write_count=0",
                "FX6_STAGE_B_R50_BRIDGE round=50 faithful=1 nop_count=0 p12_wlan=1 wf12_00342260_immune=1 p10_keymap=1 p4_nd_clear=1 p11_xlr_h1=1 lang=schinese bk4_lang=0x19 enum=0x2b45_CHINESE_SIMPLIFIED font_bank=23 str_bank=19 shoe_audio_4ch_osd_3locks=1 wind_noise_builtin_only_guard=1 saveload_camset_c3_8excl_slot1_vault=1 milestone_50=1 cnflasha_writes=0 emmc_write_count=0",
                "FX6_R50_LANG_TELEMETRY reason=gpermDrawFlush lang=schinese bk4_lang_id=0x02cf019c bk4_lang_val=0x19 gpe_fb=0 shoe_audio_4ch_osd_ok=1 wind_noise_builtin_ok=1 saveload_c3_vault_ok=1 r50_bridge_ok=1 round50_milestone_realhw_shoe_audio_4ch_wind_saveload_c3=1 cnflasha_writes=0 emmc_write_count=0 subst_color=0 subst_image=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        r50 = ms["r50_telemetry"]
        self.assertIsNotNone(r50)
        self.assertEqual(r50["shoe_audio_4ch_init"]["osd_4ch_meter_channels"], 4)
        self.assertEqual(r50["shoe_audio_4ch_init"]["disqualified_4ch_active_leaks"], 0)
        self.assertEqual(r50["shoe_audio_4ch_init"]["r50_init_ok"], 1)
        self.assertEqual(r50["shoe_audio_4ch_bridge"]["r50_bridge_ok"], 1)
        self.assertEqual(r50["wind_noise_bridge"]["external_mic_wind_reduct_active"], 0)
        self.assertEqual(r50["saveload_c3_bridge"]["camset_10slots_verified"], 10)
        self.assertEqual(r50["stage_b_bridge"]["round"], 50)
        self.assertEqual(r50["stage_b_bridge"]["milestone_50"], 1)
        self.assertEqual(r50["lang_telemetry"]["gpe_fb"], 0)

    def test_05_round50_extract_milestones_r50b_wind_noise_guard(self) -> None:
        runner = _load_closure_module("fx6_brr_r50_msb", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R50_WIND_NOISE_GUARD wind_noise_default_off_ok=1 invalid_wind_mode_reject_rc=-22 wind_noise_2modes_verified=2 wind_camreset_restores_off_ok=1 initialize_restores_off_ok=1 builtin_mic_hpf_active_ok=1 ext_sources_tested=4 ext_sources_bypassed=4 external_mic_wind_reduct_active=0 xlrh1_hw_lowcut_3positions_verified=3 outdoor_high_wind_hpf_allowed_ok=1 indoor_rehearsal_cycles=32 indoor_clamped_to_off_ok=1 indoor_low_freq_attenuation_events=0 audio_off_wind_lock_rc=-16 sq_wind_lock_rc=-16 p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30 appfw_ok=1 shim_elf_ok=1 cnflasha_writes=0 emmc_write_count=0 r50b_ok=1 verify_us=898595",
                "FX6_R50_WIND_NOISE_GUARD_RC=0",
                "FX6_R50_WIND_NOISE_GUARD_EXIT rc=0 emmc_write_count=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        r50 = ms["r50_telemetry"]
        self.assertIsNotNone(r50)
        self.assertEqual(r50["wind_noise_guard_rc"], 0)
        b = r50["wind_noise_guard"]
        self.assertEqual(b["ext_sources_bypassed"], 4)
        self.assertEqual(b["external_mic_wind_reduct_active"], 0)
        self.assertEqual(b["indoor_low_freq_attenuation_events"], 0)
        self.assertEqual(b["r50b_ok"], 1)

    def test_06_round50_extract_milestones_r50c_saveload_c3_vault(self) -> None:
        runner = _load_closure_module("fx6_brr_r50_msc", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R50_SAVELOAD_C3_VAULT camset_10slots_verified=10 invalid_camset_slot_reject_rc=-22 fx6_dat_reject_rc=-22 fx30_dat_reject_rc=-22 cross_model_loads_accepted=0 cloud_2targets_verified=2 allowed_regs_roundtrip_ok=1 excluded_8categories_verified=8 custom_wb_3regs_preserved=3 saved_payload_secret_hits=0 loaded_excluded_overwrites=0 excluded_leaks=0 slot1_save_blocked_rc=-13 slot1_ro_kernel_rc=-30 slot1_camset_writes=0 slot1_vault_sha256_match=1 slot1_readonly_load_rc=0 slot1_readonly_load_ok=1 slot2_scratch_camset_ok=1 p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30 cnflasha_writes=0 dlopen_ok=1 surfaces_verified=16 surfaces_h0_eq_h3=16 drift_bits=0 emmc_write_count=0 r50c_ok=1 verify_us=409844",
                "FX6_R50_SAVELOAD_C3_VAULT_RC=0",
                "FX6_R50_SAVELOAD_C3_VAULT_EXIT rc=0 emmc_write_count=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        r50 = ms["r50_telemetry"]
        self.assertIsNotNone(r50)
        self.assertEqual(r50["saveload_c3_vault_rc"], 0)
        c = r50["saveload_c3_vault"]
        self.assertEqual(c["camset_10slots_verified"], 10)
        self.assertEqual(c["excluded_leaks"], 0)
        self.assertEqual(c["slot1_camset_writes"], 0)
        self.assertEqual(c["surfaces_h0_eq_h3"], 16)
        self.assertEqual(c["r50c_ok"], 1)

    def test_07_round50_extract_milestones_returns_none_when_no_r50_lines(self) -> None:
        runner = _load_closure_module("fx6_brr_r50_msnone", "build_and_run_round.py")
        ms = runner.extract_milestones("Linux version 4.9.337-scel+ #1 SMP PREEMPT\n")
        self.assertIsNone(ms["r50_telemetry"])

    def test_08_round50_stage_a_overlay_r50a_shoe_audio_4ch_big6_mocked_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r50_ovl_a", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            for clean_flag in ("0", "1"):
                work = tmp_dir / f"r50_a_{clean_flag}"
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                    rep, add, meta = _build_overlay_for_r50(
                        runner, tmp_dir, work, "shoe_audio_4ch_osd_big6", lang="schinese"
                    )
                init_out = rep["init"].decode("utf-8")
                self.assertNotIn("--r50-wind-noise-builtin-guard", init_out)
                self.assertNotIn("--r50-saveload-c3-vault-h0-h3", init_out)
                self.assertIn("--sd-gate", init_out)
                self.assertIn("etc/fx6_stage_r50", add)
                self.assertIn("r50_mode=shoe_audio_4ch_osd_big6", add["etc/fx6_stage_r50"][0].decode("utf-8"))
                self.assertTrue(meta["r50_enabled"])
                self.assertEqual(meta["r50"]["r50_mode"], "shoe_audio_4ch_osd_big6")
                self.assertEqual(meta["r50"]["audio_level_display_4ch_osd_meters"], ["CH1", "CH2", "CH3", "CH4"])
                self.assertEqual(meta["r50"]["disqualified_4ch_active_leaks"], 0)
                self.assertEqual(meta["r50"]["external_mic_wind_reduct_active"], 0)
                self.assertEqual(meta["r50"]["excluded_leaks"], 0)
                self.assertEqual(meta["r50"]["slot1_camset_writes"], 0)

    def test_09_round50_stage_a_overlay_r50b_and_r50c_early_hooks_mocked_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r50_ovl_bc", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            for clean_flag in ("0", "1"):
                work_b = tmp_dir / f"r50_b_{clean_flag}"
                work_c = tmp_dir / f"r50_c_{clean_flag}"
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                    rep_b, _, meta_b = _build_overlay_for_r50(
                        runner, tmp_dir, work_b, "wind_noise_builtin_only_guard", lang="en"
                    )
                    rep_c, _, meta_c = _build_overlay_for_r50(
                        runner, tmp_dir, work_c, "saveload_camset_c3_vault_h0_h3", lang="en"
                    )
                init_b = rep_b["init"].decode("utf-8")
                init_c = rep_c["init"].decode("utf-8")
                self.assertIn("/usr/bin/fx6-stage-a-verify --r50-wind-noise-builtin-guard", init_b)
                self.assertIn("FX6_R50_WIND_NOISE_GUARD_EXIT", init_b)
                self.assertEqual(meta_b["r50"]["r50_mode"], "wind_noise_builtin_only_guard")
                self.assertIn("/usr/bin/fx6-stage-a-verify --r50-saveload-c3-vault-h0-h3", init_c)
                self.assertIn("FX6_R50_SAVELOAD_C3_VAULT_EXIT", init_c)
                self.assertEqual(meta_c["r50"]["r50_mode"], "saveload_camset_c3_vault_h0_h3")

    def test_10_round50_stage_a_overlay_rejects_invalid_mode_and_honors_disabled_flag(self) -> None:
        runner = _load_closure_module("fx6_brr_r50_badmode", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            with self.assertRaises(ValueError):
                _build_overlay_for_r50(
                    runner, tmp_dir, tmp_dir / "bad_r50", "invalid_r50_mode", lang="schinese"
                )
            _, add_off, meta_off = _build_overlay_for_r50(
                runner, tmp_dir, tmp_dir / "off_r50", "shoe_audio_4ch_osd_big6", enable_r50=False
            )
            self.assertFalse(meta_off["r50_enabled"])
            self.assertNotIn("r50", meta_off)
            self.assertNotIn("etc/fx6_stage_r50", add_off)

    def test_11_round50_summary_json_schema_sanitization_and_audit_flags(self) -> None:
        summary_path = ROUND50_REPORT_DIR / "summary.json"
        self.assertTrue(summary_path.is_file())
        raw = summary_path.read_text(encoding="utf-8")
        for forbidden in ("/Users/", "/Volumes/KAFU2T", "/private/tmp"):
            self.assertNotIn(forbidden, raw)
        data = json.loads(raw)
        self.assertEqual(
            data["schema"],
            "fx6-on-fx3-round50-milestone-realhw-shoe-audio-4ch-wind-saveload-c3-qemu-v1",
        )
        self.assertEqual(data["round"], 50)
        self.assertEqual(data["raw_firmware_bytes_leaked"], 0)
        self.assertIn("50th Grand Milestone", data["milestone"])
        self.assertIn("Linux version 4.9.337-scel+", data["kernel_version"])
        self.assertEqual(set(data["runs"].keys()), set(self.EXPECTED_RUN_KEYS))
        audit = data["r50_milestone_realhw_shoe_audio_4ch_wind_saveload_c3_audit"]
        self.assertEqual(audit["round"], 50)
        self.assertEqual(audit["milestone"], 50)
        self.assertEqual(audit["realhw_qemu_round_ordinal"], 22)
        self.assertEqual(audit["cumulative_realhw_qemu_runs"], 66)
        self.assertEqual(audit["total_runs"], 3)
        for k in (
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "all_3_runs_cnflasha_write_zero",
            "r50a_shoe_audio_4ch_osd_meter_and_3_disqualification_locks_verified",
            "r50a_stageb_big6_sid_0a_over_340k_pixels_verified",
            "r50b_wind_noise_builtin_only_and_indoor_low_cut_guard_verified",
            "r50c_saveload_camset_c3_8excl_firewall_and_slot1_vault_verified",
            "r50c_dlopen_libjit_and_16_h0_eq_h3_rollback_verified",
        ):
            self.assertTrue(audit[k], f"Audit flag {k} must be True")

    def test_12_round50_r50a_shoe_audio_3modes_default_16b_2ch_and_camera_settings_reset(self) -> None:
        data = _load_r50_summary()
        r50a = data["runs"]["r50a_shoe_audio_4ch_osd_big6_schinese"]
        si = r50a["r50_telemetry"]["shoe_audio_4ch_init"]
        r50_meta = r50a["stage_b"]["r50"]
        self.assertEqual(r50_meta["shoe_audio_set_menu_item"], "Shoe Audio Set.")
        self.assertEqual(r50_meta["shoe_audio_set_3_modes"], self.EXPECTED_SHOE_AUDIO_MODES)
        self.assertEqual(r50_meta["shoe_audio_set_default"], "48kHz/16bit 2ch")
        self.assertTrue(r50_meta["shoe_audio_set_reset_by_camera_settings_reset"])
        self.assertEqual(si["shoe_audio_default_16b_2ch_ok"], 1)
        self.assertEqual(si["invalid_shoe_mode_reject_rc"], -22)
        self.assertEqual(si["shoe_audio_3modes_verified"], 3)
        self.assertEqual(si["shoe_audio_camreset_restores_16b_2ch_ok"], 1)
        self.assertEqual(si["initialize_restores_16b_2ch_ok"], 1)

    def test_13_round50_r50a_48khz_24bit_4ch_digital_xlrh1_expands_osd_meter_to_ch1_ch4(self) -> None:
        data = _load_r50_summary()
        r50a = data["runs"]["r50a_shoe_audio_4ch_osd_big6_schinese"]
        si = r50a["r50_telemetry"]["shoe_audio_4ch_init"]
        sb = r50a["r50_telemetry"]["shoe_audio_4ch_bridge"]
        self.assertEqual(si["lpcm_4ch_24bit_active_ok"], 1)
        self.assertEqual(si["osd_4ch_meter_channels"], 4)
        self.assertEqual(si["osd_2ch_meter_channels"], 2)
        self.assertEqual(si["osd_4ch_meter_bars_px"], 4096)
        self.assertEqual(si["osd_4ch_meter_ch1_to_ch4_ok"], 1)
        self.assertEqual(sb["osd_4ch_meter_channels"], 4)
        self.assertEqual(sb["osd_4ch_meter_ch1_to_ch4_ok"], 1)

    def test_14_round50_r50a_disqualification_1_sq_motion_and_audio_off_force_zero_tracks_ebusy(self) -> None:
        data = _load_r50_summary()
        r50a = data["runs"]["r50a_shoe_audio_4ch_osd_big6_schinese"]
        si = r50a["r50_telemetry"]["shoe_audio_4ch_init"]
        sb = r50a["r50_telemetry"]["shoe_audio_4ch_bridge"]
        r50_meta = r50a["stage_b"]["r50"]
        self.assertEqual(len(r50_meta["shoe_audio_3_disqualifications"]), 3)
        self.assertIn("S&Q Motion", r50_meta["shoe_audio_3_disqualifications"][0])
        self.assertEqual(si["audio_off_lock_rc"], -16)
        self.assertEqual(si["sq_motion_lock_rc"], -16)
        self.assertEqual(si["sq_audio_tracks"], 0)
        self.assertEqual(si["audio_off_tracks"], 0)
        self.assertEqual(sb["sq_and_audio_off_0tracks_lock_ok"], 1)

    def test_15_round50_r50a_disqualification_2_35mm_mic_plug_overrides_mi_shoe_to_2ch_16b_adc(self) -> None:
        data = _load_r50_summary()
        r50a = data["runs"]["r50a_shoe_audio_4ch_osd_big6_schinese"]
        si = r50a["r50_telemetry"]["shoe_audio_4ch_init"]
        sb = r50a["r50_telemetry"]["shoe_audio_4ch_bridge"]
        r50_meta = r50a["stage_b"]["r50"]
        self.assertIn("3.5mm MIC", r50_meta["shoe_audio_3_disqualifications"][1])
        self.assertEqual(si["jack_35mm_shoe_set_lock_rc"], -16)
        self.assertEqual(si["jack_35mm_override_channels"], 2)
        self.assertEqual(si["jack_35mm_override_bits"], 16)
        self.assertEqual(sb["jack_35mm_2ch_override_lock_ok"], 1)

    def test_16_round50_r50a_disqualification_3_xlrh1_analog_switch_forces_2ch_16bit_einval(self) -> None:
        data = _load_r50_summary()
        r50a = data["runs"]["r50a_shoe_audio_4ch_osd_big6_schinese"]
        si = r50a["r50_telemetry"]["shoe_audio_4ch_init"]
        sb = r50a["r50_telemetry"]["shoe_audio_4ch_bridge"]
        r50_meta = r50a["stage_b"]["r50"]
        self.assertIn("XLR-H1 ANALOG", r50_meta["shoe_audio_3_disqualifications"][2])
        self.assertEqual(si["xlrh1_analog_24bit_4ch_reject_rc"], -22)
        self.assertEqual(si["xlrh1_analog_override_channels"], 2)
        self.assertEqual(si["xlrh1_analog_override_bits"], 16)
        self.assertEqual(si["disqualified_4ch_active_leaks"], 0)
        self.assertEqual(sb["xlrh1_analog_2ch_16b_override_ok"], 1)

    def test_17_round50_r50a_p2_setting_and_cnflasha_erofs_protection(self) -> None:
        data = _load_r50_summary()
        si = data["runs"]["r50a_shoe_audio_4ch_osd_big6_schinese"]["r50_telemetry"]["shoe_audio_4ch_init"]
        self.assertEqual(si["p2_write_blocked_rc"], -30)
        self.assertEqual(si["p2_sha256_match"], 1)
        self.assertEqual(si["cnflasha_sha256_match"], 1)
        self.assertEqual(si["cnflasha_writes"], 0)
        self.assertEqual(si["appfw_present"], 1)
        self.assertEqual(si["shim_present"], 1)
        self.assertEqual(si["emmc_write_count"], 0)
        self.assertEqual(si["r50_init_ok"], 1)

    def test_18_round50_r50a_stageb_shim_bridges_and_schinese_lang_telemetry(self) -> None:
        data = _load_r50_summary()
        rt = data["runs"]["r50a_shoe_audio_4ch_osd_big6_schinese"]["r50_telemetry"]
        self.assertEqual(rt["shoe_audio_4ch_bridge"]["shoe_audio_4ch_osd_ok"], 1)
        self.assertEqual(rt["shoe_audio_4ch_bridge"]["r50_bridge_ok"], 1)
        self.assertEqual(rt["wind_noise_bridge"]["wind_noise_builtin_ok"], 1)
        self.assertEqual(rt["wind_noise_bridge"]["external_mic_wind_reduct_active"], 0)
        self.assertEqual(rt["saveload_c3_bridge"]["saveload_c3_vault_ok"], 1)
        self.assertEqual(rt["saveload_c3_bridge"]["excluded_leaks"], 0)
        self.assertEqual(rt["saveload_c3_bridge"]["slot1_camset_writes"], 0)
        lt = rt["lang_telemetry"]
        self.assertEqual(lt["lang"], "schinese")
        self.assertEqual(lt["bk4_lang_val"], "0x19")
        self.assertEqual(lt["lang_enum"], "0x2b45_CHINESE_SIMPLIFIED")
        self.assertEqual(lt["font_bank"], 23)
        self.assertEqual(lt["str_bank"], 19)
        self.assertEqual(lt["gpe_fb"], 0)
        self.assertEqual(lt["round50_milestone_realhw_shoe_audio_4ch_wind_saveload_c3"], 1)
        self.assertEqual(lt["subst_color"], 0)
        self.assertEqual(lt["subst_image"], 0)
        sb = rt["stage_b_bridge"]
        self.assertEqual(sb["round"], 50)
        self.assertEqual(sb["milestone_50"], 1)
        self.assertEqual(sb["faithful"], 1)
        self.assertEqual(sb["nop_count"], 0)

    def test_19_round50_r50a_big6_home_presenter_gpe0_readback_and_13_manifest_locks(self) -> None:
        data = _load_r50_summary()
        r50a = data["runs"]["r50a_shoe_audio_4ch_osd_big6_schinese"]
        self.assertEqual(r50a["target_presenter"], "31procam_big6_menu_home_presenter")
        self.assertEqual(r50a["target_sid"], "0x0a")
        self.assertEqual(r50a["nop_count"], 0)
        self.assertGreaterEqual(r50a["total_threads_seen"], 150)
        self.assertEqual(r50a["stage_b"]["manifest_count"], 13)
        self.assertEqual(len(r50a["stage_b"]["manifest_items"]), 13)
        gpe0 = r50a["gpe0_readback"]
        self.assertTrue(gpe0["present"])
        self.assertEqual(gpe0["bytes"], 2211840)
        self.assertEqual(gpe0["total_pixels"], 552960)
        self.assertGreaterEqual(gpe0["nonzero_pixels"], 340000)
        self.assertGreaterEqual(gpe0["unique_colors"], 80)
        self.assertGreaterEqual(r50a["prefix_counts"]["FX6_OSD_FLUSH"], 100)
        self.assertGreaterEqual(r50a["prefix_counts"]["FX6_R50_"], 150)

    def test_20_round50_r50a_alpha_and_composited_pngs_under_50kib_and_sha256_match(self) -> None:
        data = _load_r50_summary()
        pngs = data["runs"]["r50a_shoe_audio_4ch_osd_big6_schinese"]["png_exports"]
        for key in ("alpha_png", "composited_png"):
            meta = pngs[key]
            p = REPO_ROOT / meta["path"]
            self.assertTrue(p.is_file(), f"Missing PNG {p}")
            raw = p.read_bytes()
            self.assertEqual(len(raw), meta["bytes"])
            self.assertLess(len(raw), 50 * 1024)
            self.assertGreater(len(raw), 10 * 1024)
            self.assertEqual(hashlib.sha256(raw).hexdigest(), meta["sha256"])

    def test_21_round50_r50a_png_rgba_dimensions_1024x540_and_crc_integrity(self) -> None:
        data = _load_r50_summary()
        pngs = data["runs"]["r50a_shoe_audio_4ch_osd_big6_schinese"]["png_exports"]
        alpha_bytes = (REPO_ROOT / pngs["alpha_png"]["path"]).read_bytes()
        comp_bytes = (REPO_ROOT / pngs["composited_png"]["path"]).read_bytes()
        wa, ha, rows_a = _decode_png_rgba_rows(alpha_bytes)
        wc, hc, rows_c = _decode_png_rgba_rows(comp_bytes)
        self.assertEqual((wa, ha), (1024, 540))
        self.assertEqual((wc, hc), (1024, 540))
        self.assertEqual(len(rows_a), 540)
        self.assertEqual(len(rows_c), 540)
        transparent_a = sum(
            1 for row in rows_a for x in range(3, 1024 * 4, 4) if row[x] < 255
        )
        opaque_c = sum(
            1 for row in rows_c for x in range(3, 1024 * 4, 4) if row[x] == 255
        )
        self.assertEqual(transparent_a, pngs["transparent_pixels"])
        self.assertEqual(opaque_c, 1024 * 540)

    def test_22_round50_r50a_faithful_invariants_strictly_enforced(self) -> None:
        data = _load_r50_summary()
        fi = data["runs"]["r50a_shoe_audio_4ch_osd_big6_schinese"]["faithful_invariants"]
        self.assertEqual(fi["FX6_NATIVE_FAITHFUL"], 1)
        for zero_key in ("subst_color", "subst_image", "forced_render", "skipped_node", "lock_bypass"):
            self.assertEqual(fi[zero_key], 0)

    def test_23_round50_r50b_wind_noise_default_off_2modes_and_camera_settings_reset(self) -> None:
        data = _load_r50_summary()
        r50b = data["runs"]["r50b_wind_noise_builtin_only_guard"]
        self.assertEqual(r50b["r50_telemetry"]["wind_noise_guard_rc"], 0)
        wg = r50b["r50_telemetry"]["wind_noise_guard"]
        r50_meta = r50b["stage_b"]["r50"]
        self.assertEqual(r50_meta["wind_noise_reduct_menu_item"], "Wind Noise Reduct.")
        self.assertEqual(r50_meta["wind_noise_reduct_modes"], self.EXPECTED_WIND_NOISE_MODES)
        self.assertEqual(r50_meta["wind_noise_reduct_default"], "Off")
        self.assertTrue(r50_meta["wind_noise_reduct_reset_by_camera_settings_reset"])
        self.assertEqual(wg["wind_noise_default_off_ok"], 1)
        self.assertEqual(wg["invalid_wind_mode_reject_rc"], -22)
        self.assertEqual(wg["wind_noise_2modes_verified"], 2)
        self.assertEqual(wg["wind_camreset_restores_off_ok"], 1)
        self.assertEqual(wg["initialize_restores_off_ok"], 1)

    def test_24_round50_r50b_builtin_stereo_mic_exclusivity_and_4_external_mic_bypasses(self) -> None:
        data = _load_r50_summary()
        r50b = data["runs"]["r50b_wind_noise_builtin_only_guard"]
        wg = r50b["r50_telemetry"]["wind_noise_guard"]
        r50_meta = r50b["stage_b"]["r50"]
        self.assertTrue(r50_meta["wind_noise_reduct_builtin_stereo_mic_only"])
        self.assertEqual(r50_meta["external_mic_wind_reduct_active"], 0)
        self.assertEqual(r50_meta["xlrh1_hardware_lowcut_positions"], ["Off", "100Hz", "300Hz"])
        self.assertEqual(wg["builtin_mic_hpf_active_ok"], 1)
        self.assertEqual(wg["ext_sources_tested"], 4)
        self.assertEqual(wg["ext_sources_bypassed"], 4)
        self.assertEqual(wg["external_mic_wind_reduct_active"], 0)
        self.assertEqual(wg["xlrh1_hw_lowcut_3positions_verified"], 3)

    def test_25_round50_r50b_indoor_low_wind_bench_32_cycles_clamp_and_zero_attenuation(self) -> None:
        data = _load_r50_summary()
        r50b = data["runs"]["r50b_wind_noise_builtin_only_guard"]
        wg = r50b["r50_telemetry"]["wind_noise_guard"]
        r50_meta = r50b["stage_b"]["r50"]
        self.assertTrue(r50_meta["indoor_low_wind_clamped_to_off"])
        self.assertEqual(r50_meta["indoor_low_freq_attenuation_events"], 0)
        self.assertEqual(wg["outdoor_high_wind_hpf_allowed_ok"], 1)
        self.assertEqual(wg["indoor_rehearsal_cycles"], 32)
        self.assertEqual(wg["indoor_clamped_to_off_ok"], 1)
        self.assertEqual(wg["indoor_low_freq_attenuation_events"], 0)

    def test_26_round50_r50b_sq_and_audio_off_ebusy_locks_and_ro_guards(self) -> None:
        data = _load_r50_summary()
        wg = data["runs"]["r50b_wind_noise_builtin_only_guard"]["r50_telemetry"]["wind_noise_guard"]
        self.assertEqual(wg["audio_off_wind_lock_rc"], -16)
        self.assertEqual(wg["sq_wind_lock_rc"], -16)
        self.assertEqual(wg["p2_write_blocked_rc"], -30)
        self.assertEqual(wg["cnflasha_ro_blocked_rc"], -30)
        self.assertEqual(wg["appfw_ok"], 1)
        self.assertEqual(wg["shim_elf_ok"], 1)
        self.assertEqual(wg["cnflasha_writes"], 0)
        self.assertEqual(wg["emmc_write_count"], 0)
        self.assertEqual(wg["r50b_ok"], 1)

    def test_27_round50_r50c_camset01_to_10_slots_and_same_model_ilme_fx3_lock(self) -> None:
        data = _load_r50_summary()
        r50c = data["runs"]["r50c_saveload_camset_c3_vault_h0_h3"]
        self.assertEqual(r50c["r50_telemetry"]["saveload_c3_vault_rc"], 0)
        sv = r50c["r50_telemetry"]["saveload_c3_vault"]
        r50_meta = r50c["stage_b"]["r50"]
        self.assertEqual(r50_meta["save_load_settings_menu_item"], "Save/Load Settings")
        self.assertEqual(r50_meta["camset_max_files_per_card"], 10)
        self.assertEqual(r50_meta["camset_file_range"], ["CAMSET01.DAT", "CAMSET10.DAT"])
        self.assertEqual(r50_meta["camset_model_lock"], "ILME-FX3")
        self.assertEqual(r50_meta["fx6_cross_model_dat_reject_rc"], -22)
        self.assertEqual(sv["camset_10slots_verified"], 10)
        self.assertEqual(sv["invalid_camset_slot_reject_rc"], -22)
        self.assertEqual(sv["fx6_dat_reject_rc"], -22)
        self.assertEqual(sv["fx30_dat_reject_rc"], -22)
        self.assertEqual(sv["cross_model_loads_accepted"], 0)

    def test_28_round50_r50c_c3_portal_cloud_private_and_share_ver400_plus_roundtrip(self) -> None:
        data = _load_r50_summary()
        r50c = data["runs"]["r50c_saveload_camset_c3_vault_h0_h3"]
        sv = r50c["r50_telemetry"]["saveload_c3_vault"]
        r50_meta = r50c["stage_b"]["r50"]
        self.assertEqual(r50_meta["c3_portal_cloud_targets"], self.EXPECTED_CLOUD_TARGETS)
        self.assertEqual(sv["cloud_2targets_verified"], 2)
        self.assertEqual(sv["allowed_regs_roundtrip_ok"], 1)
        self.assertEqual(sv["slot2_scratch_camset_ok"], 1)

    def test_29_round50_r50c_excluded_8_categories_zero_export_and_zero_overwrite(self) -> None:
        data = _load_r50_summary()
        r50c = data["runs"]["r50c_saveload_camset_c3_vault_h0_h3"]
        sv = r50c["r50_telemetry"]["saveload_c3_vault"]
        r50_meta = r50c["stage_b"]["r50"]
        self.assertEqual(r50_meta["excluded_8_register_categories"], self.EXPECTED_EXCLUDED_8_CATEGORIES)
        self.assertEqual(r50_meta["excluded_leaks"], 0)
        self.assertEqual(sv["excluded_8categories_verified"], 8)
        self.assertEqual(sv["custom_wb_3regs_preserved"], 3)
        self.assertEqual(sv["saved_payload_secret_hits"], 0)
        self.assertEqual(sv["loaded_excluded_overwrites"], 0)
        self.assertEqual(sv["excluded_leaks"], 0)

    def test_30_round50_r50c_slot1_tier0_vault_write_block_eacces_erofs_and_readonly_load(self) -> None:
        data = _load_r50_summary()
        r50c = data["runs"]["r50c_saveload_camset_c3_vault_h0_h3"]
        sv = r50c["r50_telemetry"]["saveload_c3_vault"]
        r50_meta = r50c["stage_b"]["r50"]
        self.assertEqual(r50_meta["slot1_tier0_vault_save_blocked_rc"], -13)
        self.assertTrue(r50_meta["slot1_readonly_load_allowed"])
        self.assertEqual(r50_meta["slot1_camset_writes"], 0)
        self.assertEqual(sv["slot1_save_blocked_rc"], -13)
        self.assertEqual(sv["slot1_ro_kernel_rc"], -30)
        self.assertEqual(sv["slot1_camset_writes"], 0)
        self.assertEqual(sv["slot1_vault_sha256_match"], 1)
        self.assertEqual(sv["slot1_readonly_load_rc"], 0)
        self.assertEqual(sv["slot1_readonly_load_ok"], 1)

    def test_31_round50_r50c_dlopen_libjit_and_16_of_16_h0_eq_h3_invariance(self) -> None:
        data = _load_r50_summary()
        sv = data["runs"]["r50c_saveload_camset_c3_vault_h0_h3"]["r50_telemetry"]["saveload_c3_vault"]
        self.assertEqual(sv["p2_write_blocked_rc"], -30)
        self.assertEqual(sv["cnflasha_ro_blocked_rc"], -30)
        self.assertEqual(sv["cnflasha_writes"], 0)
        self.assertEqual(sv["dlopen_ok"], 1)
        self.assertEqual(sv["surfaces_verified"], 16)
        self.assertEqual(sv["surfaces_h0_eq_h3"], 16)
        self.assertEqual(sv["drift_bits"], 0)
        self.assertEqual(sv["emmc_write_count"], 0)
        self.assertEqual(sv["r50c_ok"], 1)

    def test_32_round50_realhw_mechanisms_verified_top_level_summary_mirrors_run_telemetry(self) -> None:
        data = _load_r50_summary()
        rm = data["realhw_mechanisms_verified"]
        self.assertEqual(
            rm["shoe_audio_set_48khz_24bit_4ch_osd_meter_vs_35mm_xlrh1_analog_and_sq_lockouts_init"],
            data["runs"]["r50a_shoe_audio_4ch_osd_big6_schinese"]["r50_telemetry"]["shoe_audio_4ch_init"],
        )
        self.assertEqual(
            rm["wind_noise_reduct_builtin_stereo_mic_exclusivity_and_indoor_low_cut_attenuation_guard"],
            data["runs"]["r50b_wind_noise_builtin_only_guard"]["r50_telemetry"]["wind_noise_guard"],
        )
        self.assertEqual(
            rm["saveload_settings_camset01_to_10_c3_excluded_items_firewall_slot1_vault_and_16_h0_h3"],
            data["runs"]["r50c_saveload_camset_c3_vault_h0_h3"]["r50_telemetry"]["saveload_c3_vault"],
        )

    def test_33_round50_unexecuted_physical_camera_bench_boundaries_explicitly_declared(self) -> None:
        data = _load_r50_summary()
        bounds = data["unexecuted_physical_camera_bench_boundaries"]
        self.assertEqual(len(bounds), 3)
        joined = " ".join(bounds)
        for keyword in ("XLR-H1", "Wind Noise Reduct.", "CAMSET01..10.DAT", "C3 Portal", "unexecuted"):
            self.assertIn(keyword, joined)

    def test_34_round50_wave36_authoritative_spec_alignment(self) -> None:
        self.assertTrue(WAVE36_SPEC_PATH.is_file())
        spec_md = WAVE36_SPEC_PATH.read_text(encoding="utf-8")
        for term in (
            "Shoe Audio Set.",
            "48kHz/24bit 4ch",
            "Wind Noise Reduct.",
            "Save/Load Settings",
            "CAMSET01.DAT",
            "CAMSET10.DAT",
            "Cloud(Private)",
            "Cloud(Share)",
        ):
            self.assertIn(term, spec_md)

    def test_35_round50_report_readme_completeness_and_zero_host_path_leakage(self) -> None:
        readme_path = ROUND50_REPORT_DIR / "README.md"
        self.assertTrue(readme_path.is_file())
        md = readme_path.read_text(encoding="utf-8")
        for forbidden in ("/Users/", "/Volumes/KAFU2T", "/private/tmp"):
            self.assertNotIn(forbidden, md)
        for required in (
            "50th Grand Milestone",
            "Wave-36",
            "4.9.337-scel+",
            "round50-shoe-audio-4ch-osd-big6",
            "round50-wind-noise-builtin-guard",
            "round50-saveload-camset-c3-vault-h0-h3",
            "r50a-shoe-audio-4ch-osd-big6-schinese-alpha.png",
            "r50a-shoe-audio-4ch-osd-big6-schinese-composited.png",
            "尚未执行的真实物理相机台架测试边界",
        ):
            self.assertIn(required, md)

    def test_36_round50_report_directory_contains_strictly_4_clean_files_zero_donor_binaries(self) -> None:
        files = sorted(
            str(p.relative_to(ROUND50_REPORT_DIR))
            for p in ROUND50_REPORT_DIR.rglob("*")
            if p.is_file()
        )
        self.assertEqual(
            files,
            [
                "README.md",
                "assets/r50a-shoe-audio-4ch-osd-big6-schinese-alpha.png",
                "assets/r50a-shoe-audio-4ch-osd-big6-schinese-composited.png",
                "summary.json",
            ],
        )
        for p in ROUND50_REPORT_DIR.rglob("*"):
            if p.is_file():
                self.assertNotIn(p.suffix, {".cpio", ".qcow2", ".img", ".so", ".bin", ".pyc"})

    def test_37_round50_closure_readme_documents_round50_milestone(self) -> None:
        closure_md = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn("Round 50 (`50th Grand Milestone!` / Wave-36)", closure_md)
        self.assertIn("2026-11-15-round50-milestone-realhw-shoe-audio-4ch-wind-saveload-c3-qemu", closure_md)
        self.assertIn("shoe_audio_4ch_osd_big6", closure_md)
        self.assertIn("wind_noise_builtin_only_guard", closure_md)
        self.assertIn("saveload_camset_c3_vault_h0_h3", closure_md)

    def test_38_round50_cli_parser_accepts_round50_and_all_3_r50_modes(self) -> None:
        runner = _load_closure_module("fx6_brr_r50_cli", "build_and_run_round.py")
        for mode in (
            "shoe_audio_4ch_osd_big6",
            "wind_noise_builtin_only_guard",
            "saveload_camset_c3_vault_h0_h3",
        ):
            with mock.patch.object(
                sys,
                "argv",
                ["build_and_run_round.py", "--round", "50", "--r50-mode", mode, "--run-id", f"t-{mode}"],
            ):
                # Parse via argparse inspection without running QEMU
                src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")
                self.assertIn(f'"{mode}"', src)
        self.assertTrue(hasattr(runner, "build_stage_a_overlay"))

    def test_39_round50_c_probe_rc_codes_69_247_248_contract_in_verify_c(self) -> None:
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        self.assertIn("return 69;", verify_src)
        self.assertIn("return ok ? 0 : 247;", verify_src)
        self.assertIn("return ok ? 0 : 248;", verify_src)

    def test_40_round50_c_probe_camset_header_magic_ilme_fx3_vs_fx6_fx30_rejection_in_verify_c(self) -> None:
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        self.assertIn('"SONYDAT"', verify_src)
        self.assertIn('"ILME-FX3"', verify_src)
        self.assertIn('"ILME-FX6"', verify_src)
        self.assertIn('"ILME-FX30"', verify_src)
        self.assertIn("CAMSET%02u.DAT", verify_src)

    def test_41_round50_c_probe_excluded_secret_sentinels_never_serialized_in_verify_c(self) -> None:
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        for sentinel in (
            "IPTC_BODY_UNIT_01",
            "COPYRIGHT_STUDIO_A",
            "FTP_SECRET_TOKEN_X9",
            "RTMPS_LIVE_KEY_Z7",
            "WPA3_PSK_CREW_NET",
            "TLS_CERT_FINGERPRINT_Q4",
        ):
            self.assertIn(sentinel, verify_src)

    def test_42_round50_c_probe_custom_wb_1_to_3_kelvin_preservation_in_verify_c(self) -> None:
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        self.assertIn("custom_wb_kelvin[0] = 3200U", verify_src)
        self.assertIn("custom_wb_kelvin[1] = 4300U", verify_src)
        self.assertIn("custom_wb_kelvin[2] = 5600U", verify_src)
        self.assertIn("custom_wb_3regs_preserved == 3", verify_src)

    def test_43_round50_c_probe_shoe_audio_3_modes_and_osd_4ch_bars_in_verify_c(self) -> None:
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        self.assertIn("R50_SHOE_AUDIO_48K_16BIT_2CH", verify_src)
        self.assertIn("R50_SHOE_AUDIO_48K_24BIT_2CH", verify_src)
        self.assertIn("R50_SHOE_AUDIO_48K_24BIT_4CH", verify_src)
        self.assertIn("4096U", verify_src)

    def test_44_round50_c_probe_wind_noise_4_external_mic_sources_and_xlrh1_3pos_lowcut_in_verify_c(self) -> None:
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        for tok in (
            "R50_AUDIO_SRC_BUILTIN_STEREO_MIC",
            "R50_AUDIO_SRC_EXT_35MM_MIC",
            "R50_AUDIO_SRC_EXT_MISHOE_ECM_M1",
            "R50_AUDIO_SRC_EXT_XLRH1_DIGITAL",
            "R50_AUDIO_SRC_EXT_XLRH1_ANALOG",
            "R50_XLRH1_LOWCUT_OFF",
            "R50_XLRH1_LOWCUT_100HZ",
            "R50_XLRH1_LOWCUT_300HZ",
        ):
            self.assertIn(tok, verify_src)

    def test_45_round50_early_exit_detector_in_runner_covers_both_r50b_and_r50c(self) -> None:
        runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")
        self.assertIn("FX6_R50_WIND_NOISE_GUARD_EXIT", runner_src)
        self.assertIn("FX6_R50_SAVELOAD_C3_VAULT_EXIT", runner_src)

    def test_46_round50_prior_round49_report_and_summary_remain_intact(self) -> None:
        r49_summary = (
            REPO_ROOT
            / "reports"
            / "2026-11-15-round49-realhw-emphasized-rec-grid-hdmi-touch-sunny-qemu"
            / "summary.json"
        )
        self.assertTrue(r49_summary.is_file())
        d49 = json.loads(r49_summary.read_text(encoding="utf-8"))
        self.assertEqual(d49["round"], 49)
        self.assertEqual(d49["raw_firmware_bytes_leaked"], 0)

    def test_47_round50_prior_round46_sq_0ch_audio_consistent_with_r50a_and_r50b_sq_locks(self) -> None:
        r46_summary = (
            REPO_ROOT
            / "reports"
            / "2026-11-15-round46-realhw-sq-fixedvar-zebra-peaking-fullformat-qemu"
            / "summary.json"
        )
        self.assertTrue(r46_summary.is_file())
        d46 = json.loads(r46_summary.read_text(encoding="utf-8"))
        self.assertEqual(d46["round"], 46)
        d50 = _load_r50_summary()
        si = d50["runs"]["r50a_shoe_audio_4ch_osd_big6_schinese"]["r50_telemetry"]["shoe_audio_4ch_init"]
        wg = d50["runs"]["r50b_wind_noise_builtin_only_guard"]["r50_telemetry"]["wind_noise_guard"]
        self.assertEqual(si["sq_audio_tracks"], 0)
        self.assertEqual(si["sq_motion_lock_rc"], -16)
        self.assertEqual(wg["sq_wind_lock_rc"], -16)

    def test_48_round50_prior_round46_slot1_vault_consistent_with_r50c_slot1_camset_firewall(self) -> None:
        d50 = _load_r50_summary()
        sv = d50["runs"]["r50c_saveload_camset_c3_vault_h0_h3"]["r50_telemetry"]["saveload_c3_vault"]
        self.assertEqual(sv["slot1_save_blocked_rc"], -13)
        self.assertEqual(sv["slot1_camset_writes"], 0)
        self.assertEqual(sv["slot1_readonly_load_ok"], 1)

    def test_49_round50_all_3_runs_zero_crashes_zero_emmc_and_zero_cnflasha_writes(self) -> None:
        data = _load_r50_summary()
        for run_key in self.EXPECTED_RUN_KEYS:
            run_obj = data["runs"][run_key]
            self.assertEqual(run_obj["round"], 50)
            self.assertEqual(run_obj["crashes"], 0)
            self.assertEqual(run_obj["emmc_write_count"], 0)
            self.assertEqual(run_obj["stage_b"]["r50"]["p2_setting_writes"], 0)
            self.assertEqual(run_obj["stage_b"]["r50"]["cnflasha_writes"], 0)
            self.assertEqual(run_obj["stage_b"]["r50"]["slot1_camset_writes"], 0)
            self.assertEqual(run_obj["stage_b"]["r50"]["excluded_leaks"], 0)

    def test_50_round50_stage_label_and_tmp_prefix_wiring_in_runner(self) -> None:
        runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")
        self.assertIn(
            "Milestone50Wave36RealHwShoeAudio4chWindNoiseBuiltinOnlySaveLoadC3Vault+r50_mode={r50_mode}+lang={lang}",
            runner_src,
        )
        self.assertIn('if args.round >= 50:\n        tmp_prefix = "fx6-r50"', runner_src)

    def test_51_round50_dual_mode_clean_room_toggle_parity_on_summary(self) -> None:
        for clean_flag in ("0", "1"):
            with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                data = _load_r50_summary()
                self.assertEqual(data["round"], 50)
                self.assertEqual(
                    data["runs"]["r50a_shoe_audio_4ch_osd_big6_schinese"]["r50_telemetry"]["shoe_audio_4ch_init"]["disqualified_4ch_active_leaks"],
                    0,
                )
                self.assertEqual(
                    data["runs"]["r50b_wind_noise_builtin_only_guard"]["r50_telemetry"]["wind_noise_guard"]["external_mic_wind_reduct_active"],
                    0,
                )
                self.assertEqual(
                    data["runs"]["r50c_saveload_camset_c3_vault_h0_h3"]["r50_telemetry"]["saveload_c3_vault"]["surfaces_h0_eq_h3"],
                    16,
                )

    def test_52_round50_50th_grand_milestone_22nd_realhw_qemu_round_66_live_runs_continuity(self) -> None:
        for r in range(28, 51):
            matches = list((REPO_ROOT / "reports").glob(f"*round{r}-*"))
            self.assertTrue(matches, f"Missing live QEMU report directory for Round {r}")
        data = _load_r50_summary()
        audit = data["r50_milestone_realhw_shoe_audio_4ch_wind_saveload_c3_audit"]
        self.assertEqual(audit["milestone"], 50)
        self.assertEqual(audit["realhw_qemu_round_ordinal"], 22)
        self.assertEqual(audit["cumulative_realhw_qemu_runs"], 66)

    def test_53_round50_r50a_verify_us_positive_under_2_seconds(self) -> None:
        data = _load_r50_summary()
        us = data["runs"]["r50a_shoe_audio_4ch_osd_big6_schinese"]["r50_telemetry"]["shoe_audio_4ch_init"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_54_round50_r50b_verify_us_positive_under_2_seconds(self) -> None:
        data = _load_r50_summary()
        us = data["runs"]["r50b_wind_noise_builtin_only_guard"]["r50_telemetry"]["wind_noise_guard"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_55_round50_r50c_verify_us_positive_under_2_seconds(self) -> None:
        data = _load_r50_summary()
        us = data["runs"]["r50c_saveload_camset_c3_vault_h0_h3"]["r50_telemetry"]["saveload_c3_vault"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_56_round50_r50a_stage_b_manifest_matches_r50b_and_r50c_non_shim_digests(self) -> None:
        data = _load_r50_summary()
        ma = {x["guest_path"]: x["sha256"] for x in data["runs"]["r50a_shoe_audio_4ch_osd_big6_schinese"]["stage_b"]["manifest_items"]}
        mb = {x["guest_path"]: x["sha256"] for x in data["runs"]["r50b_wind_noise_builtin_only_guard"]["stage_b"]["manifest_items"]}
        mc = {x["guest_path"]: x["sha256"] for x in data["runs"]["r50c_saveload_camset_c3_vault_h0_h3"]["stage_b"]["manifest_items"]}
        for gpath in (
            "/usr/lib/appFw.so",
            "/usr/lib/libfan.so",
            "/usr/kmod/upm.ko",
            "/usr/lib/libWlanResource.so",
        ):
            self.assertEqual(ma[gpath], mb[gpath])
            self.assertEqual(mb[gpath], mc[gpath])

    def test_57_round50_r50a_top_colors_include_transparent_and_dark_ui_surfaces(self) -> None:
        data = _load_r50_summary()
        top = data["runs"]["r50a_shoe_audio_4ch_osd_big6_schinese"]["gpe0_readback"]["top_colors"]
        self.assertGreaterEqual(len(top), 5)
        argbs = {row["argb"] for row in top}
        self.assertIn("0x00000000", argbs)
        self.assertIn("0xff000000", argbs)

    def test_58_round50_r50a_wall_elapsed_and_duration_budget_sanity(self) -> None:
        data = _load_r50_summary()
        r50a = data["runs"]["r50a_shoe_audio_4ch_osd_big6_schinese"]
        self.assertEqual(r50a["duration_budget_sec"], 71)
        self.assertGreater(r50a["wall_elapsed_sec"], 50.0)
        self.assertLess(r50a["wall_elapsed_sec"], 120.0)

    def test_59_round50_r50b_and_r50c_fast_early_exit_wall_elapsed_under_20s(self) -> None:
        data = _load_r50_summary()
        r50b = data["runs"]["r50b_wind_noise_builtin_only_guard"]
        r50c = data["runs"]["r50c_saveload_camset_c3_vault_h0_h3"]
        self.assertEqual(r50b["duration_budget_sec"], 35)
        self.assertEqual(r50c["duration_budget_sec"], 35)
        self.assertGreater(r50b["wall_elapsed_sec"], 1.0)
        self.assertLess(r50b["wall_elapsed_sec"], 20.0)
        self.assertGreater(r50c["wall_elapsed_sec"], 1.0)
        self.assertLess(r50c["wall_elapsed_sec"], 20.0)

    def test_60_round50_shim_round49_backward_compat_preserved_when_built_for_round49(self) -> None:
        runner = _load_closure_module("fx6_brr_r50_r49compat", "build_and_run_round.py")
        if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1" and not runner.ZIG.is_file():
            self.skipTest("Clean-room fallback without local zig binary")
        with tempfile.TemporaryDirectory() as tmp:
            _, shim_r49, _ = runner.build_binaries(
                pathlib.Path(tmp) / "r49_compat",
                fx6_round=49,
                restore_infra70=1,
                restore_all_early=0,
                reply_all_200d=1,
                initial_setting_done=1,
                key_seq="0x7028:120:5500",
                key_settle_ms=1500,
                lang="schinese",
            )
            self.assertIn(b"FX6_R49_EMPH_REC_GRID_HDMI_BRIDGE", shim_r49)
            self.assertNotIn(b"FX6_R50_SHOE_AUDIO_4CH_BRIDGE", shim_r49)


if __name__ == "__main__":
    unittest.main()
