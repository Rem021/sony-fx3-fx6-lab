#!/usr/bin/env python3
"""Offline dual-mode unit tests for FX6-on-FX3 Round 51 (Wave-37 Live FX3 7.02 QEMU Rehearsal)."""
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
ROUND51_REPORT_DIR = (
    REPO_ROOT
    / "reports"
    / "2026-11-15-round51-realhw-framing-usbpower-lun-antiflicker-qemu"
)
WAVE37_SPEC_PATH = (
    REPO_ROOT
    / "reports"
    / "2026-11-15-global-sony-wave37-framing-settings-crop-full-usb-power-battery-lun-antiflicker-novarshutter-intel"
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


def _build_overlay_for_r51(
    runner,
    tmp_dir: pathlib.Path,
    work: pathlib.Path,
    r51_mode: str,
    lang: str = "schinese",
    enable_r51: bool = True,
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
            enable_r50=True, r50_mode="shoe_audio_4ch_osd_big6",
            enable_r51=enable_r51, r51_mode=r51_mode,
            sd_manifest_mode="valid", lang=lang, shim_bytes=b"SHIM",
        )


def _load_r51_summary() -> dict:
    return json.loads((ROUND51_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))


class TestRound51RealHwFramingUsbPowerLunAntiFlickerQemu(unittest.TestCase):
    EXPECTED_RUN_KEYS = (
        "r51a_framing_crop_hdmi_big6_schinese",
        "r51b_usb_power_npfz100_and_usb_lun_guard",
        "r51c_antiflicker_mech_still_no_var_shutter_h0_h3",
    )

    def test_01_wave37_global_spec_present_and_covers_all_4_pillars(self) -> None:
        self.assertTrue(WAVE37_SPEC_PATH.is_file())
        spec_txt = WAVE37_SPEC_PATH.read_text(encoding="utf-8")
        for needle in (
            "Framing Settings",
            "Autoframing Settings",
            "USB Power Supply",
            "NP-FZ100",
            "USB LUN Setting",
            "Anti-flicker Shoot.",
            "Var. Shutter",
        ):
            self.assertIn(needle, spec_txt)

    def test_02_round51_summary_schema_round_and_zero_leaks(self) -> None:
        raw_txt = (ROUND51_REPORT_DIR / "summary.json").read_text(encoding="utf-8")
        self.assertNotIn("/Users/", raw_txt)
        self.assertNotIn("/private/tmp/", raw_txt)
        data = json.loads(raw_txt)
        self.assertEqual(data["schema"], "fx6-on-fx3-round51-realhw-framing-usbpower-lun-antiflicker-qemu-v1")
        self.assertEqual(data["round"], 51)
        self.assertEqual(data["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(tuple(data["runs"].keys()), self.EXPECTED_RUN_KEYS)

    def test_03_round51_cli_accepts_round51_and_all_3_r51_modes(self) -> None:
        runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")
        self.assertIn(", 51]", runner_src)
        for mode in (
            "framing_settings_crop_hdmi_big6",
            "usb_power_npfz100_and_usb_lun_guard",
            "antiflicker_mech_still_no_var_shutter_guard",
        ):
            self.assertIn(mode, runner_src)

    def test_04_round51_overlay_rejects_invalid_r51_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r51_badmode", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tpath = pathlib.Path(tmp)
            with self.assertRaises(ValueError):
                _build_overlay_for_r51(runner, tpath, tpath / "work", "invalid_r51_mode")

    def test_05_round51_overlay_r51a_framing_mode_injects_etc_fx6_stage_r51_and_appfw_launch(self) -> None:
        runner = _load_closure_module("fx6_brr_r51_ov_a", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tpath = pathlib.Path(tmp)
            replacements, additions, meta = _build_overlay_for_r51(
                runner, tpath, tpath / "work", "framing_settings_crop_hdmi_big6", lang="schinese"
            )
            self.assertTrue(meta["r51_enabled"])
            self.assertIn("etc/fx6_stage_r51", additions)
            r51_cfg = additions["etc/fx6_stage_r51"][0].decode("utf-8")
            self.assertIn("stage_r51=1", r51_cfg)
            self.assertIn("r51_mode=framing_settings_crop_hdmi_big6", r51_cfg)
            init_txt = replacements["init"].decode("utf-8")
            self.assertIn("/usr/bin/appfw-launch", init_txt)
            self.assertNotIn("--r51-usb-power-lun-guard", init_txt)
            self.assertNotIn("--r51-antiflicker-no-var-shutter-h0-h3", init_txt)

    def test_06_round51_overlay_r51b_usb_power_lun_injects_early_probe_and_poweroff(self) -> None:
        runner = _load_closure_module("fx6_brr_r51_ov_b", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tpath = pathlib.Path(tmp)
            replacements, _, meta = _build_overlay_for_r51(
                runner, tpath, tpath / "work", "usb_power_npfz100_and_usb_lun_guard", lang="en"
            )
            self.assertEqual(meta["r51"]["r51_mode"], "usb_power_npfz100_and_usb_lun_guard")
            init_txt = replacements["init"].decode("utf-8")
            self.assertIn("--r51-usb-power-lun-guard", init_txt)
            self.assertIn("FX6_R51_USB_POWER_LUN_RC=", init_txt)
            self.assertLess(init_txt.index("--r51-usb-power-lun-guard"), init_txt.index("/usr/bin/appfw-launch"))

    def test_07_round51_overlay_r51c_antiflicker_no_var_injects_early_probe_and_poweroff(self) -> None:
        runner = _load_closure_module("fx6_brr_r51_ov_c", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tpath = pathlib.Path(tmp)
            replacements, _, meta = _build_overlay_for_r51(
                runner, tpath, tpath / "work", "antiflicker_mech_still_no_var_shutter_guard", lang="en"
            )
            self.assertEqual(meta["r51"]["r51_mode"], "antiflicker_mech_still_no_var_shutter_guard")
            init_txt = replacements["init"].decode("utf-8")
            self.assertIn("--r51-antiflicker-no-var-shutter-h0-h3", init_txt)
            self.assertIn("FX6_R51_ANTIFLICKER_NO_VAR_RC=", init_txt)
            self.assertLess(
                init_txt.index("--r51-antiflicker-no-var-shutter-h0-h3"),
                init_txt.index("/usr/bin/appfw-launch"),
            )

    def test_08_round51_overlay_disabled_when_enable_r51_false(self) -> None:
        runner = _load_closure_module("fx6_brr_r51_ov_off", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tpath = pathlib.Path(tmp)
            _, additions, meta = _build_overlay_for_r51(
                runner, tpath, tpath / "work", "framing_settings_crop_hdmi_big6", enable_r51=False
            )
            self.assertFalse(meta["r51_enabled"])
            self.assertNotIn("etc/fx6_stage_r51", additions)
            self.assertNotIn("r51", meta)

    def test_09_round51_stage_a_c_source_contains_all_3_wave37_probes(self) -> None:
        c_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        for sym in (
            "setup_r51_framing_settings_crop_hdmi_probe",
            "run_r51_usb_power_lun_guard_probe",
            "run_r51_antiflicker_no_var_shutter_probe",
            "--r51-usb-power-lun-guard",
            "--r51-antiflicker-no-var-shutter-h0-h3",
            "FX6_R51_FRAMING_INIT",
            "FX6_R51_USB_POWER_LUN_GUARD",
            "FX6_R51_ANTIFLICKER_NO_VAR",
        ):
            self.assertIn(sym, c_src)

    def test_10_round51_shim_c_source_contains_r51_guarded_bridges(self) -> None:
        shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        for sym in (
            "#if FX6_ROUND >= 51",
            "FX6_R51_FRAMING_BRIDGE",
            "FX6_R51_USB_POWER_LUN_BRIDGE",
            "FX6_R51_ANTIFLICKER_BRIDGE",
            "FX6_R51_LANG_TELEMETRY",
            "FX6_STAGE_B_R51_BRIDGE",
        ):
            self.assertIn(sym, shim_src)

    def test_11_round51_compile_launcher_and_shim_aarch64_elf_symbols(self) -> None:
        runner = _load_closure_module("fx6_brr_r51_compile", "build_and_run_round.py")
        if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1" and not runner.ZIG.is_file():
            self.skipTest("Clean-room fallback without local zig binary")
        with tempfile.TemporaryDirectory() as tmp:
            launcher_b, shim_b, _ = runner.build_binaries(
                pathlib.Path(tmp) / "r51_bin",
                fx6_round=51,
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
            self.assertIn(b"FX6_R51_FRAMING_BRIDGE", shim_b)
            self.assertIn(b"FX6_R51_USB_POWER_LUN_BRIDGE", shim_b)
            self.assertIn(b"FX6_R51_ANTIFLICKER_BRIDGE", shim_b)

    def test_12_round51_shim_round50_backward_compat_excludes_r51_bridges(self) -> None:
        runner = _load_closure_module("fx6_brr_r51_r50compat", "build_and_run_round.py")
        if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1" and not runner.ZIG.is_file():
            self.skipTest("Clean-room fallback without local zig binary")
        with tempfile.TemporaryDirectory() as tmp:
            _, shim_r50, _ = runner.build_binaries(
                pathlib.Path(tmp) / "r50_compat",
                fx6_round=50,
                restore_infra70=1,
                restore_all_early=0,
                reply_all_200d=1,
                initial_setting_done=1,
                key_seq="0x7028:120:5500",
                key_settle_ms=1500,
                lang="schinese",
            )
            self.assertIn(b"FX6_R50_SHOE_AUDIO_4CH_BRIDGE", shim_r50)
            self.assertNotIn(b"FX6_R51_FRAMING_BRIDGE", shim_r50)

    def test_13_round51_r51a_live_kernel_and_big6_presenter_sid_0a(self) -> None:
        data = _load_r51_summary()
        r51a = data["runs"]["r51a_framing_crop_hdmi_big6_schinese"]
        self.assertIn("Linux version 4.9.337-scel+", r51a["kernel_version"])
        self.assertEqual(r51a["target_presenter"], "31procam_big6_menu_home_presenter")
        self.assertEqual(r51a["target_sid"], "0x0a")
        self.assertEqual(r51a["lang"], "schinese")
        self.assertGreaterEqual(r51a["total_threads_seen"], 150)

    def test_14_round51_r51a_exact_346686_gpe0_pixels_87_colors_and_faithful_invariants(self) -> None:
        data = _load_r51_summary()
        r51a = data["runs"]["r51a_framing_crop_hdmi_big6_schinese"]
        gpe = r51a["gpe0_readback"]
        self.assertTrue(gpe["present"])
        self.assertEqual(gpe["bytes"], 2211840)
        self.assertEqual(gpe["total_pixels"], 552960)
        self.assertEqual(gpe["nonzero_pixels"], 346686)
        self.assertEqual(gpe["unique_colors"], 87)
        self.assertEqual(r51a["nop_count"], 0)
        fi = r51a["faithful_invariants"]
        self.assertEqual(fi["FX6_NATIVE_FAITHFUL"], 1)
        self.assertEqual(fi["subst_color"], 0)
        self.assertEqual(fi["subst_image"], 0)
        self.assertEqual(fi["forced_render"], 0)
        self.assertEqual(fi["skipped_node"], 0)
        self.assertEqual(fi["lock_bypass"], 0)

    def test_15_round51_r51a_png_assets_exist_under_50kib_and_valid_1024x540_rgba(self) -> None:
        alpha_p = ROUND51_REPORT_DIR / "assets" / "r51a-framing-crop-hdmi-big6-schinese-alpha.png"
        comp_p = ROUND51_REPORT_DIR / "assets" / "r51a-framing-crop-hdmi-big6-schinese-composited.png"
        for p in (alpha_p, comp_p):
            self.assertTrue(p.is_file())
            self.assertGreater(p.stat().st_size, 1024)
            self.assertLess(p.stat().st_size, 51200)
        wa, ha, rows_a = _decode_png_rgba_rows(alpha_p.read_bytes())
        wc, hc, rows_c = _decode_png_rgba_rows(comp_p.read_bytes())
        self.assertEqual((wa, ha), (1024, 540))
        self.assertEqual((wc, hc), (1024, 540))
        self.assertTrue(any(row[x + 3] == 0 for row in rows_a for x in range(0, 4096, 64)))
        self.assertTrue(all(row[x + 3] == 255 for row in rows_c for x in range(0, 4096, 64)))

    def test_16_round51_r51a_menu_hierarchy_not_zve1_autoframing(self) -> None:
        data = _load_r51_summary()
        r51a = data["runs"]["r51a_framing_crop_hdmi_big6_schinese"]
        meta_r51 = r51a["stage_b"]["r51"]
        fi = r51a["r51_telemetry"]["framing_init"]
        self.assertEqual(
            meta_r51["framing_settings_menu_path"],
            "MENU -> Shooting -> [Image Stabilization] -> [Framing Stabilizer] -> [Framing Settings]",
        )
        self.assertTrue(meta_r51["framing_settings_not_zve1_autoframing"])
        self.assertEqual(fi["fx3_framing_node_ok"], 1)
        self.assertEqual(fi["zve1_autoframing_reject_rc"], -2)
        self.assertEqual(fi["zve1_autoframing_conflation_events"], 0)

    def test_17_round51_r51a_asymmetric_defaults_full_rec_vs_crop_hdmi(self) -> None:
        data = _load_r51_summary()
        r51a = data["runs"]["r51a_framing_crop_hdmi_big6_schinese"]
        meta_r51 = r51a["stage_b"]["r51"]
        fi = r51a["r51_telemetry"]["framing_init"]
        self.assertEqual(meta_r51["framing_default"], "Off")
        self.assertEqual(meta_r51["recording_streaming_default"], "Full")
        self.assertEqual(meta_r51["hdmi_default"], "Crop")
        self.assertEqual(fi["framing_default_off_ok"], 1)
        self.assertEqual(fi["invalid_framing_enum_reject_rc"], -22)
        self.assertEqual(fi["asymmetric_full_rec_crop_hdmi_ok"], 1)

    def test_18_round51_r51a_all_4_full_crop_routing_combinations_verified(self) -> None:
        data = _load_r51_summary()
        r51a = data["runs"]["r51a_framing_crop_hdmi_big6_schinese"]
        self.assertEqual(
            r51a["stage_b"]["r51"]["framing_4_routing_combinations"],
            ["Full/Full", "Full/Crop", "Crop/Full", "Crop/Crop"],
        )
        self.assertEqual(r51a["r51_telemetry"]["framing_init"]["framing_4routing_combos_verified"], 4)

    def test_19_round51_r51a_camera_settings_reset_and_initialize_restore_framing_defaults(self) -> None:
        data = _load_r51_summary()
        r51a = data["runs"]["r51a_framing_crop_hdmi_big6_schinese"]
        fi = r51a["r51_telemetry"]["framing_init"]
        self.assertTrue(r51a["stage_b"]["r51"]["framing_reset_by_camera_settings_reset"])
        self.assertEqual(fi["framing_camreset_restores_defaults_ok"], 1)
        self.assertEqual(fi["initialize_restores_defaults_ok"], 1)

    def test_20_round51_r51a_hdmi_raw_output_clamps_and_locks_framing_settings(self) -> None:
        data = _load_r51_summary()
        r51a = data["runs"]["r51a_framing_crop_hdmi_big6_schinese"]
        fi = r51a["r51_telemetry"]["framing_init"]
        self.assertTrue(r51a["stage_b"]["r51"]["hdmi_raw_output_locks_framing"])
        self.assertEqual(fi["raw_enable_clamps_framing_off_ok"], 1)
        self.assertEqual(fi["hdmi_raw_framing_lock_rc"], -16)
        self.assertEqual(fi["framing_raw_conflict_events"], 0)

    def test_21_round51_r51a_p2_setting_and_cnflasha_readonly_protection(self) -> None:
        data = _load_r51_summary()
        fi = data["runs"]["r51a_framing_crop_hdmi_big6_schinese"]["r51_telemetry"]["framing_init"]
        self.assertEqual(fi["p2_write_blocked_rc"], -30)
        self.assertEqual(fi["p2_sha256_match"], 1)
        self.assertEqual(fi["cnflasha_sha256_match"], 1)
        self.assertEqual(fi["cnflasha_writes"], 0)
        self.assertEqual(fi["appfw_present"], 1)
        self.assertEqual(fi["shim_present"], 1)
        self.assertEqual(fi["emmc_write_count"], 0)
        self.assertEqual(fi["r51_init_ok"], 1)

    def test_22_round51_r51a_stage_b_framing_bridge_parity(self) -> None:
        data = _load_r51_summary()
        fb = data["runs"]["r51a_framing_crop_hdmi_big6_schinese"]["r51_telemetry"]["framing_bridge"]
        self.assertEqual(fb["framing_default_off_ok"], 1)
        self.assertEqual(fb["rec_stream_default_full_ok"], 1)
        self.assertEqual(fb["hdmi_default_crop_ok"], 1)
        self.assertEqual(fb["asymmetric_full_rec_crop_hdmi_ok"], 1)
        self.assertEqual(fb["framing_4routing_combos_verified"], 4)
        self.assertEqual(fb["framing_camreset_restores_defaults_ok"], 1)
        self.assertEqual(fb["zve1_autoframing_conflation_events"], 0)
        self.assertEqual(fb["hdmi_raw_framing_lock_rc"], -16)
        self.assertEqual(fb["framing_raw_conflict_events"], 0)
        self.assertEqual(fb["framing_crop_hdmi_ok"], 1)
        self.assertEqual(fb["r51_bridge_ok"], 1)

    def test_23_round51_r51a_stage_b_usb_power_and_antiflicker_bridges_active(self) -> None:
        data = _load_r51_summary()
        tel = data["runs"]["r51a_framing_crop_hdmi_big6_schinese"]["r51_telemetry"]
        ub = tel["usb_power_lun_bridge"]
        ab = tel["antiflicker_bridge"]
        self.assertEqual(ub["usb_power_lun_ok"], 1)
        self.assertEqual(ub["unbuffered_battery_pull_events"], 0)
        self.assertEqual(ub["multi_micro_usb_power_bypass_events"], 0)
        self.assertEqual(ub["physical_usb_packets_emitted"], 0)
        self.assertEqual(ab["antiflicker_no_var_ok"], 1)
        self.assertEqual(ab["antiflicker_movie_or_eshutter_bypass_events"], 0)
        self.assertEqual(ab["fx3_has_var_shutter"], 0)
        self.assertEqual(ab["false_var_shutter_events"], 0)

    def test_24_round51_r51a_lang_telemetry_schinese_font_bank_23_str_bank_19(self) -> None:
        data = _load_r51_summary()
        lt = data["runs"]["r51a_framing_crop_hdmi_big6_schinese"]["r51_telemetry"]["lang_telemetry"]
        self.assertEqual(lt["lang"], "schinese")
        self.assertEqual(lt["bk4_lang_id"], "0x02cf019c")
        self.assertEqual(lt["bk4_lang_val"], "0x19")
        self.assertEqual(lt["lang_enum"], "0x2b45_CHINESE_SIMPLIFIED")
        self.assertEqual(lt["font_bank"], 23)
        self.assertEqual(lt["str_bank"], 19)
        self.assertEqual(lt["gpe_fb"], 0)
        self.assertEqual(lt["round51_realhw_framing_usbpower_lun_antiflicker"], 1)
        self.assertEqual(lt["emmc_write_count"], 0)

    def test_25_round51_r51a_stage_b_bridge_round_51_and_patch_invariants(self) -> None:
        data = _load_r51_summary()
        sb = data["runs"]["r51a_framing_crop_hdmi_big6_schinese"]["r51_telemetry"]["stage_b_bridge"]
        self.assertEqual(sb["round"], 51)
        self.assertEqual(sb["faithful"], 1)
        self.assertEqual(sb["nop_count"], 0)
        self.assertEqual(sb["p12_wlan"], 1)
        self.assertEqual(sb["wf12_00342260_immune"], 1)
        self.assertEqual(sb["p10_keymap"], 1)
        self.assertEqual(sb["p4_nd_clear"], 1)
        self.assertEqual(sb["p11_xlr_h1"], 1)
        self.assertEqual(sb["framing_crop_hdmi_no_autoframing"], 1)
        self.assertEqual(sb["usb_power_npfz100_typec_lun_persist"], 1)
        self.assertEqual(sb["antiflicker_mech_still_no_var_shutter"], 1)

    def test_26_round51_r51b_usb_power_supply_and_usb_lun_factory_defaults_and_modes(self) -> None:
        data = _load_r51_summary()
        r51b = data["runs"]["r51b_usb_power_npfz100_and_usb_lun_guard"]
        self.assertEqual(r51b["r51_telemetry"]["usb_power_lun_rc"], 0)
        self.assertIsNone(r51b["r51_telemetry"]["antiflicker_no_var_rc"])
        ug = r51b["r51_telemetry"]["usb_power_lun_guard"]
        self.assertEqual(ug["usb_power_default_on_ok"], 1)
        self.assertEqual(ug["usb_lun_default_multi_ok"], 1)
        self.assertEqual(ug["invalid_usb_power_rc"], -22)
        self.assertEqual(ug["invalid_usb_lun_rc"], -22)
        self.assertEqual(ug["usb_power_2modes_verified"], 2)
        self.assertEqual(ug["usb_lun_2modes_verified"], 2)

    def test_27_round51_r51b_usb_lun_multi_2_units_vs_single_1_unit_fallback(self) -> None:
        data = _load_r51_summary()
        r51b = data["runs"]["r51b_usb_power_npfz100_and_usb_lun_guard"]
        meta = r51b["stage_b"]["r51"]
        ug = r51b["r51_telemetry"]["usb_power_lun_guard"]
        self.assertEqual(meta["usb_lun_setting_menu_item"], "USB LUN Setting")
        self.assertEqual(meta["usb_lun_setting_modes"], ["Multi", "Single"])
        self.assertEqual(meta["usb_lun_setting_default"], "Multi")
        self.assertEqual(ug["lun_multi_exposed_units"], 2)
        self.assertEqual(ug["lun_single_exposed_units"], 1)

    def test_28_round51_r51b_np_fz100_or_dcc1_mandatory_and_battery_pull_firewall(self) -> None:
        data = _load_r51_summary()
        r51b = data["runs"]["r51b_usb_power_npfz100_and_usb_lun_guard"]
        ug = r51b["r51_telemetry"]["usb_power_lun_guard"]
        self.assertTrue(r51b["stage_b"]["r51"]["usb_power_requires_inserted_np_fz100_or_dcc1"])
        self.assertEqual(ug["dcc1_coupler_supported_ok"], 1)
        self.assertEqual(ug["poweron_without_battery_reject_rc"], -19)
        self.assertEqual(ug["raw_pull_causes_immediate_poweroff_ok"], 1)
        self.assertEqual(ug["live_battery_pull_guard_rc"], -16)
        self.assertEqual(ug["unbuffered_battery_pull_events"], 0)

    def test_29_round51_r51b_usb_type_c_exclusive_and_multi_micro_usb_rejected(self) -> None:
        data = _load_r51_summary()
        r51b = data["runs"]["r51b_usb_power_npfz100_and_usb_lun_guard"]
        ug = r51b["r51_telemetry"]["usb_power_lun_guard"]
        self.assertTrue(r51b["stage_b"]["r51"]["usb_power_exclusive_usb_type_c"])
        self.assertEqual(ug["usb_typec_pd_power_ok"], 1)
        self.assertEqual(ug["multi_micro_usb_power_reject_rc"], -95)
        self.assertEqual(ug["multi_micro_usb_power_bypass_events"], 0)
        self.assertEqual(ug["physical_usb_packets_emitted"], 0)

    def test_30_round51_r51b_usb_setup_survives_camera_settings_reset_cleared_only_by_initialize(self) -> None:
        data = _load_r51_summary()
        r51b = data["runs"]["r51b_usb_power_npfz100_and_usb_lun_guard"]
        meta = r51b["stage_b"]["r51"]
        ug = r51b["r51_telemetry"]["usb_power_lun_guard"]
        self.assertTrue(meta["usb_setup_survives_camera_settings_reset"])
        self.assertTrue(meta["usb_setup_reset_only_by_initialize"])
        self.assertEqual(ug["usb_power_survives_camreset_ok"], 1)
        self.assertEqual(ug["usb_lun_survives_camreset_ok"], 1)
        self.assertEqual(ug["shooting_tier_reset_split_ok"], 1)
        self.assertEqual(ug["initialize_restores_usb_defaults_ok"], 1)
        self.assertEqual(ug["r51b_ok"], 1)

    def test_31_round51_r51b_readonly_p2_and_cnflasha_guards(self) -> None:
        data = _load_r51_summary()
        ug = data["runs"]["r51b_usb_power_npfz100_and_usb_lun_guard"]["r51_telemetry"]["usb_power_lun_guard"]
        self.assertEqual(ug["p2_write_blocked_rc"], -30)
        self.assertEqual(ug["cnflasha_ro_blocked_rc"], -30)
        self.assertEqual(ug["appfw_ok"], 1)
        self.assertEqual(ug["shim_elf_ok"], 1)
        self.assertEqual(ug["cnflasha_writes"], 0)
        self.assertEqual(ug["emmc_write_count"], 0)

    def test_32_round51_r51c_antiflicker_shoot_defaults_modes_and_100_120hz(self) -> None:
        data = _load_r51_summary()
        r51c = data["runs"]["r51c_antiflicker_mech_still_no_var_shutter_h0_h3"]
        self.assertIsNone(r51c["r51_telemetry"]["usb_power_lun_rc"])
        self.assertEqual(r51c["r51_telemetry"]["antiflicker_no_var_rc"], 0)
        af = r51c["r51_telemetry"]["antiflicker_no_var"]
        self.assertEqual(r51c["stage_b"]["r51"]["antiflicker_shoot_menu_item"], "Anti-flicker Shoot.")
        self.assertEqual(r51c["stage_b"]["r51"]["antiflicker_flicker_hz"], [100, 120])
        self.assertEqual(af["antiflicker_default_off_ok"], 1)
        self.assertEqual(af["invalid_antiflicker_rc"], -22)
        self.assertEqual(af["antiflicker_2modes_verified"], 2)
        self.assertEqual(af["flicker_100hz_120hz_verified"], 2)
        self.assertEqual(af["mech_still_antiflicker_active_ok"], 1)

    def test_33_round51_r51c_antiflicker_reset_by_camera_settings_reset_and_initialize(self) -> None:
        data = _load_r51_summary()
        r51c = data["runs"]["r51c_antiflicker_mech_still_no_var_shutter_h0_h3"]
        af = r51c["r51_telemetry"]["antiflicker_no_var"]
        self.assertTrue(r51c["stage_b"]["r51"]["antiflicker_shoot_reset_by_camera_settings_reset"])
        self.assertEqual(af["antiflicker_camreset_restores_off_ok"], 1)
        self.assertEqual(af["initialize_restores_off_ok"], 1)

    def test_34_round51_r51c_movie_sq_and_silent_eshutter_hard_lockouts(self) -> None:
        data = _load_r51_summary()
        r51c = data["runs"]["r51c_antiflicker_mech_still_no_var_shutter_h0_h3"]
        af = r51c["r51_telemetry"]["antiflicker_no_var"]
        self.assertTrue(r51c["stage_b"]["r51"]["antiflicker_mechanical_shutter_still_only"])
        self.assertEqual(af["movie_mode_lock_rc"], -95)
        self.assertEqual(af["sq_mode_lock_rc"], -95)
        self.assertEqual(af["silent_eshutter_lock_rc"], -95)
        self.assertEqual(af["antiflicker_movie_or_eshutter_bypass_events"], 0)

    def test_35_round51_r51c_ilme_fx3_has_no_var_shutter_or_ecs_menu(self) -> None:
        data = _load_r51_summary()
        r51c = data["runs"]["r51c_antiflicker_mech_still_no_var_shutter_h0_h3"]
        af = r51c["r51_telemetry"]["antiflicker_no_var"]
        self.assertEqual(r51c["stage_b"]["r51"]["fx3_has_var_shutter"], 0)
        self.assertEqual(r51c["stage_b"]["r51"]["false_var_shutter_events"], 0)
        self.assertEqual(af["var_shutter_lookup_rc"], -2)
        self.assertEqual(af["fx6_ecs_lookup_rc"], -2)
        self.assertEqual(af["fx3_has_var_shutter"], 0)
        self.assertEqual(af["false_var_shutter_events"], 0)
        self.assertEqual(af["cross_model_var_shutter_contrast_ok"], 1)

    def test_36_round51_r51c_guest_dlopen_libjit_and_16_of_16_h0_eq_h3(self) -> None:
        data = _load_r51_summary()
        af = data["runs"]["r51c_antiflicker_mech_still_no_var_shutter_h0_h3"]["r51_telemetry"]["antiflicker_no_var"]
        self.assertEqual(af["dlopen_ok"], 1)
        self.assertEqual(af["surfaces_verified"], 16)
        self.assertEqual(af["surfaces_h0_eq_h3"], 16)
        self.assertEqual(af["drift_bits"], 0)
        self.assertEqual(af["r51c_ok"], 1)

    def test_37_round51_r51c_readonly_p2_and_cnflasha_guards(self) -> None:
        data = _load_r51_summary()
        af = data["runs"]["r51c_antiflicker_mech_still_no_var_shutter_h0_h3"]["r51_telemetry"]["antiflicker_no_var"]
        self.assertEqual(af["p2_write_blocked_rc"], -30)
        self.assertEqual(af["cnflasha_ro_blocked_rc"], -30)
        self.assertEqual(af["cnflasha_writes"], 0)
        self.assertEqual(af["emmc_write_count"], 0)

    def test_38_round51_serial_parser_extracts_all_r51_telemetry_lines(self) -> None:
        runner = _load_closure_module("fx6_brr_r51_parse", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R51_FRAMING_INIT fx3_framing_node_ok=1 zve1_autoframing_conflation_events=0 framing_raw_conflict_events=0 r51_init_ok=1",
                "FX6_R51_FRAMING_BRIDGE framing_crop_hdmi_ok=1 r51_bridge_ok=1",
                "FX6_R51_USB_POWER_LUN_BRIDGE usb_power_lun_ok=1 unbuffered_battery_pull_events=0",
                "FX6_R51_ANTIFLICKER_BRIDGE antiflicker_no_var_ok=1 fx3_has_var_shutter=0",
                "FX6_R51_USB_POWER_LUN_GUARD r51b_ok=1 multi_micro_usb_power_bypass_events=0",
                "FX6_R51_USB_POWER_LUN_RC=0",
                "FX6_R51_ANTIFLICKER_NO_VAR r51c_ok=1 surfaces_h0_eq_h3=16",
                "FX6_R51_ANTIFLICKER_NO_VAR_RC=0",
                "FX6_R51_LANG_TELEMETRY lang=schinese font_bank=23 str_bank=19",
                "FX6_STAGE_B_R51_BRIDGE round=51 faithful=1 nop_count=0",
            ]
        )
        m = runner.extract_milestones(serial)
        t51 = m["r51_telemetry"]
        self.assertEqual(t51["usb_power_lun_rc"], 0)
        self.assertEqual(t51["antiflicker_no_var_rc"], 0)
        self.assertEqual(t51["framing_init"]["r51_init_ok"], 1)
        self.assertEqual(t51["framing_bridge"]["framing_crop_hdmi_ok"], 1)
        self.assertEqual(t51["usb_power_lun_bridge"]["usb_power_lun_ok"], 1)
        self.assertEqual(t51["antiflicker_bridge"]["fx3_has_var_shutter"], 0)
        self.assertEqual(t51["usb_power_lun_guard"]["r51b_ok"], 1)
        self.assertEqual(t51["antiflicker_no_var"]["surfaces_h0_eq_h3"], 16)
        self.assertEqual(t51["lang_telemetry"]["font_bank"], 23)
        self.assertEqual(t51["stage_b_bridge"]["round"], 51)

    def test_39_round51_all_3_runs_13_stage_b_manifest_items_sha256_valid(self) -> None:
        data = _load_r51_summary()
        for run_key in self.EXPECTED_RUN_KEYS:
            sb = data["runs"][run_key]["stage_b"]
            self.assertEqual(sb["manifest_count"], 13)
            self.assertEqual(len(sb["manifest_items"]), 13)
            for item in sb["manifest_items"]:
                self.assertTrue(item["guest_path"].startswith("/"))
                self.assertEqual(len(item["sha256"]), 64)
                int(item["sha256"], 16)

    def test_40_round51_r51a_r51b_r51c_non_shim_donor_digests_identical(self) -> None:
        data = _load_r51_summary()
        ma = {x["guest_path"]: x["sha256"] for x in data["runs"]["r51a_framing_crop_hdmi_big6_schinese"]["stage_b"]["manifest_items"]}
        mb = {x["guest_path"]: x["sha256"] for x in data["runs"]["r51b_usb_power_npfz100_and_usb_lun_guard"]["stage_b"]["manifest_items"]}
        mc = {x["guest_path"]: x["sha256"] for x in data["runs"]["r51c_antiflicker_mech_still_no_var_shutter_h0_h3"]["stage_b"]["manifest_items"]}
        for gpath in (
            "/usr/lib/appFw.so",
            "/usr/lib/libfan.so",
            "/usr/kmod/upm.ko",
            "/usr/lib/libWlanResource.so",
        ):
            self.assertEqual(ma[gpath], mb[gpath])
            self.assertEqual(mb[gpath], mc[gpath])

    def test_41_round51_all_3_runs_zero_crashes_zero_emmc_zero_cnflasha_and_zero_usb_packets(self) -> None:
        data = _load_r51_summary()
        for run_key in self.EXPECTED_RUN_KEYS:
            run_obj = data["runs"][run_key]
            self.assertEqual(run_obj["round"], 51)
            self.assertEqual(run_obj["crashes"], 0)
            self.assertEqual(run_obj["emmc_write_count"], 0)
            self.assertEqual(run_obj["stage_b"]["r51"]["p2_setting_writes"], 0)
            self.assertEqual(run_obj["stage_b"]["r51"]["cnflasha_writes"], 0)
            self.assertEqual(run_obj["stage_b"]["r51"]["physical_usb_packets_emitted"], 0)

    def test_42_round51_audit_block_all_booleans_true_for_milestone233_gate(self) -> None:
        data = _load_r51_summary()
        audit = data["r51_realhw_framing_usbpower_lun_antiflicker_audit"]
        self.assertEqual(audit["round"], 51)
        self.assertEqual(audit["milestone"], 51)
        self.assertEqual(audit["milestone233_qemu_rounds"], 24)
        self.assertEqual(audit["milestone233_qemu_runs"], 72)
        self.assertEqual(audit["total_runs"], 3)
        bool_entries = {k: v for k, v in audit.items() if isinstance(v, bool)}
        self.assertGreaterEqual(len(bool_entries), 8)
        for k, v in bool_entries.items():
            self.assertTrue(v, f"Audit boolean {k} must be True")

    def test_43_round51_unexecuted_physical_camera_bench_boundaries_documented(self) -> None:
        data = _load_r51_summary()
        bounds = data["unexecuted_physical_camera_bench_boundaries"]
        self.assertEqual(len(bounds), 3)
        joined = " ".join(bounds)
        for kw in ("Framing Settings", "HDMI RAW", "NP-FZ100", "USB LUN Setting", "Anti-flicker Shoot."):
            self.assertIn(kw, joined)

    def test_44_round51_report_readme_documents_all_3_runs_pngs_and_physical_boundaries(self) -> None:
        readme = (ROUND51_REPORT_DIR / "README.md").read_text(encoding="utf-8")
        for needle in (
            "round51-framing-crop-hdmi-big6",
            "round51-usb-power-npfz100-lun-guard",
            "round51-antiflicker-no-var-shutter-h0-h3",
            "346,686",
            "Autoframing Settings",
            "NP-FZ100",
            "USB LUN Setting",
            "Var. Shutter",
            "16/16 H0 == H3",
            "r51a-framing-crop-hdmi-big6-schinese-alpha.png",
            "r51a-framing-crop-hdmi-big6-schinese-composited.png",
        ):
            self.assertIn(needle, readme)

    def test_45_round51_presenter_closure_readme_documents_section_51(self) -> None:
        closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn("## 51. Round 51", closure_readme)
        self.assertIn("2026-11-15-round51-realhw-framing-usbpower-lun-antiflicker-qemu/README.md", closure_readme)
        self.assertIn("framing_settings_crop_hdmi_big6", closure_readme)
        self.assertIn("usb_power_npfz100_and_usb_lun_guard", closure_readme)
        self.assertIn("antiflicker_mech_still_no_var_shutter_guard", closure_readme)

    def test_46_round51_cross_round_consistency_with_r45_hdmi_raw_steadyshot_cutoff(self) -> None:
        d45 = json.loads(
            (REPO_ROOT / "reports" / "2026-11-15-round45-realhw-steadyshot-ciz-powersave-autotemp-qemu" / "summary.json").read_text(encoding="utf-8")
        )
        d51 = _load_r51_summary()
        r45_raw_rc = d45["runs"]["r45a_steadyshot_active_cutoffs_big6_schinese"]["r45_telemetry"]["steadyshot_active_init"]["hdmi_raw_active_reject_rc"]
        r51_raw_rc = d51["runs"]["r51a_framing_crop_hdmi_big6_schinese"]["r51_telemetry"]["framing_init"]["hdmi_raw_framing_lock_rc"]
        self.assertEqual(r45_raw_rc, -16)
        self.assertEqual(r51_raw_rc, -16)

    def test_47_round51_cross_round_consistency_with_r47_silent_mode_antiflicker_lock(self) -> None:
        d47 = json.loads(
            (REPO_ROOT / "reports" / "2026-11-15-round47-realhw-silent-autopixelmap-marker-flexexp-qemu" / "summary.json").read_text(encoding="utf-8")
        )
        d51 = _load_r51_summary()
        r47_af_rc = d47["runs"]["r47a_silent_autopixelmap_5locks_big6_schinese"]["r47_telemetry"]["silent_autopixelmap_init"]["dis_antiflicker_rc"]
        r51_af_rc = d51["runs"]["r51c_antiflicker_mech_still_no_var_shutter_h0_h3"]["r51_telemetry"]["antiflicker_no_var"]["silent_eshutter_lock_rc"]
        self.assertEqual(r47_af_rc, -95)
        self.assertEqual(r51_af_rc, -95)

    def test_48_round51_cross_round_consistency_with_r38_dcc1_usb_pd_power_guard(self) -> None:
        d38 = json.loads(
            (REPO_ROOT / "reports" / "2026-11-15-round38-realhw-nouvc-dcc1-lut-path-cineei-qemu" / "summary.json").read_text(encoding="utf-8")
        )
        d51 = _load_r51_summary()
        i38 = d38["runs"]["r38a_nouvc_dcc1_pd_big6_schinese"]["r38_telemetry"]["nouvc_dcc1_pd_init"]
        g51 = d51["runs"]["r51b_usb_power_npfz100_and_usb_lun_guard"]["r51_telemetry"]["usb_power_lun_guard"]
        self.assertEqual(i38["body_pd_no_fz100_rc"], g51["poweron_without_battery_reject_rc"])
        self.assertEqual(i38["micro_usb_power_rc"], g51["multi_micro_usb_power_reject_rc"])
        self.assertEqual(i38["dcc1_65w_5a_rc"], 0)
        self.assertEqual(g51["dcc1_coupler_supported_ok"], 1)

    def test_49_round51_setup_vs_shooting_reset_tier_split_across_r51a_r51b_r51c(self) -> None:
        d51 = _load_r51_summary()
        fi = d51["runs"]["r51a_framing_crop_hdmi_big6_schinese"]["r51_telemetry"]["framing_init"]
        ug = d51["runs"]["r51b_usb_power_npfz100_and_usb_lun_guard"]["r51_telemetry"]["usb_power_lun_guard"]
        af = d51["runs"]["r51c_antiflicker_mech_still_no_var_shutter_h0_h3"]["r51_telemetry"]["antiflicker_no_var"]
        self.assertEqual(fi["framing_camreset_restores_defaults_ok"], 1)
        self.assertEqual(af["antiflicker_camreset_restores_off_ok"], 1)
        self.assertEqual(ug["usb_power_survives_camreset_ok"], 1)
        self.assertEqual(ug["usb_lun_survives_camreset_ok"], 1)
        self.assertEqual(ug["initialize_restores_usb_defaults_ok"], 1)

    def test_50_round51_stage_label_and_tmp_prefix_wiring_in_runner(self) -> None:
        runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")
        self.assertIn(
            "Wave37RealHwFramingCropHdmiUsbPowerNpFz100LunAntiFlickerNoVarShutter+r51_mode={r51_mode}+lang={lang}",
            runner_src,
        )
        self.assertIn('if args.round >= 51:\n        tmp_prefix = "fx6-r51"', runner_src)

    def test_51_round51_dual_mode_clean_room_toggle_parity_on_summary(self) -> None:
        for clean_flag in ("0", "1"):
            with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                data = _load_r51_summary()
                self.assertEqual(data["round"], 51)
                self.assertEqual(
                    data["runs"]["r51a_framing_crop_hdmi_big6_schinese"]["r51_telemetry"]["framing_init"]["zve1_autoframing_conflation_events"],
                    0,
                )
                self.assertEqual(
                    data["runs"]["r51b_usb_power_npfz100_and_usb_lun_guard"]["r51_telemetry"]["usb_power_lun_guard"]["unbuffered_battery_pull_events"],
                    0,
                )
                self.assertEqual(
                    data["runs"]["r51c_antiflicker_mech_still_no_var_shutter_h0_h3"]["r51_telemetry"]["antiflicker_no_var"]["surfaces_h0_eq_h3"],
                    16,
                )

    def test_52_round51_24_realhw_qemu_rounds_r28_to_r51_72_runs_continuity(self) -> None:
        for r in range(28, 52):
            matches = list((REPO_ROOT / "reports").glob(f"*round{r}-*"))
            self.assertTrue(matches, f"Missing live QEMU report directory for Round {r}")
        data = _load_r51_summary()
        audit = data["r51_realhw_framing_usbpower_lun_antiflicker_audit"]
        self.assertEqual(audit["milestone233_qemu_rounds"], 24)
        self.assertEqual(audit["milestone233_qemu_runs"], 72)

    def test_53_round51_r51a_verify_us_positive_under_2_seconds(self) -> None:
        data = _load_r51_summary()
        us = data["runs"]["r51a_framing_crop_hdmi_big6_schinese"]["r51_telemetry"]["framing_init"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_54_round51_r51b_verify_us_positive_under_2_seconds(self) -> None:
        data = _load_r51_summary()
        us = data["runs"]["r51b_usb_power_npfz100_and_usb_lun_guard"]["r51_telemetry"]["usb_power_lun_guard"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_55_round51_r51c_verify_us_positive_under_2_seconds(self) -> None:
        data = _load_r51_summary()
        us = data["runs"]["r51c_antiflicker_mech_still_no_var_shutter_h0_h3"]["r51_telemetry"]["antiflicker_no_var"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_56_round51_realhw_mechanisms_verified_top_level_6_blocks_match_run_telemetry(self) -> None:
        data = _load_r51_summary()
        rm = data["realhw_mechanisms_verified"]
        self.assertEqual(len(rm), 6)
        r51a = data["runs"]["r51a_framing_crop_hdmi_big6_schinese"]["r51_telemetry"]
        r51b = data["runs"]["r51b_usb_power_npfz100_and_usb_lun_guard"]["r51_telemetry"]
        r51c = data["runs"]["r51c_antiflicker_mech_still_no_var_shutter_h0_h3"]["r51_telemetry"]
        self.assertEqual(rm["framing_settings_full_rec_crop_hdmi_no_zve1_autoframing_and_raw_lockout_init"], r51a["framing_init"])
        self.assertEqual(rm["framing_settings_crop_hdmi_and_raw_lockout_stage_b_bridge"], r51a["framing_bridge"])
        self.assertEqual(rm["usb_power_npfz100_typec_and_usb_lun_persist_stage_b_bridge"], r51a["usb_power_lun_bridge"])
        self.assertEqual(rm["antiflicker_mech_still_no_var_shutter_stage_b_bridge"], r51a["antiflicker_bridge"])
        self.assertEqual(rm["usb_power_supply_npfz100_mandatory_typec_exclusive_and_usb_lun_camreset_survival_guard"], r51b["usb_power_lun_guard"])
        self.assertEqual(rm["antiflicker_shoot_mech_still_only_no_var_shutter_and_16_h0_h3"], r51c["antiflicker_no_var"])

    def test_57_round51_r51a_top_colors_include_transparent_and_dark_ui_surfaces(self) -> None:
        data = _load_r51_summary()
        gpe = data["runs"]["r51a_framing_crop_hdmi_big6_schinese"]["gpe0_readback"]
        top = gpe["top_colors"]
        self.assertGreaterEqual(len(top), 5)
        color_map = {row["argb"]: row["pixels"] for row in top}
        self.assertIn("0x00000000", color_map)
        self.assertIn("0xff000000", color_map)
        self.assertEqual(color_map["0x00000000"] + gpe["nonzero_pixels"], gpe["total_pixels"])

    def test_58_round51_r51a_wall_elapsed_and_duration_budget_sanity(self) -> None:
        data = _load_r51_summary()
        r51a = data["runs"]["r51a_framing_crop_hdmi_big6_schinese"]
        self.assertEqual(r51a["duration_budget_sec"], 71)
        self.assertGreater(r51a["wall_elapsed_sec"], 50.0)
        self.assertLess(r51a["wall_elapsed_sec"], 120.0)

    def test_59_round51_r51b_and_r51c_fast_early_exit_wall_elapsed_under_20s(self) -> None:
        data = _load_r51_summary()
        r51b = data["runs"]["r51b_usb_power_npfz100_and_usb_lun_guard"]
        r51c = data["runs"]["r51c_antiflicker_mech_still_no_var_shutter_h0_h3"]
        self.assertEqual(r51b["duration_budget_sec"], 35)
        self.assertEqual(r51c["duration_budget_sec"], 35)
        self.assertGreater(r51b["wall_elapsed_sec"], 1.0)
        self.assertLess(r51b["wall_elapsed_sec"], 20.0)
        self.assertGreater(r51c["wall_elapsed_sec"], 1.0)
        self.assertLess(r51c["wall_elapsed_sec"], 20.0)
        self.assertTrue(r51b["gpe0_readback"]["skipped_stock_fx3_mode"])
        self.assertTrue(r51c["gpe0_readback"]["skipped_stock_fx3_mode"])

    def test_60_round51_port_8768_untouched_in_round51_sources_and_reports(self) -> None:
        for p in (
            ROUND51_REPORT_DIR / "summary.json",
            ROUND51_REPORT_DIR / "README.md",
            CLOSURE_DIR / "fx6-stage-a-verify.c",
            CLOSURE_DIR / "libgrm-fbinit9.c",
            CLOSURE_DIR / "build_and_run_round.py",
        ):
            self.assertNotIn("8768", p.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
