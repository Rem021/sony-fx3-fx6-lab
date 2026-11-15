#!/usr/bin/env python3
"""Offline dual-mode unit tests for FX6-on-FX3 Round 45 (45th Milestone / Wave-31 Live FX3 7.02 QEMU Rehearsal)."""
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
ROUND45_REPORT_DIR = (
    REPO_ROOT
    / "reports"
    / "2026-11-15-round45-realhw-steadyshot-ciz-powersave-autotemp-qemu"
)
WAVE31_SPEC_PATH = (
    REPO_ROOT
    / "reports"
    / "2026-11-15-global-sony-wave31-steadyshot-active-raw-hfr-ciz-center-af-powersave-9cond-temp-high-intel"
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


def _build_overlay_for_r45(
    runner,
    tmp_dir: pathlib.Path,
    work: pathlib.Path,
    r45_mode: str,
    lang: str = "schinese",
    enable_r45: bool = True,
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
            enable_r45=enable_r45, r45_mode=r45_mode,
            sd_manifest_mode="valid", lang=lang, shim_bytes=b"SHIM",
        )


def _load_r45_summary() -> dict:
    return json.loads((ROUND45_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))


class TestRound45RealHwSteadyShotCizPowerSaveAutoTemp(unittest.TestCase):
    EXPECTED_RUN_KEYS = (
        "r45a_steadyshot_active_cutoffs_big6_schinese",
        "r45b_ciz_4locks_hfr_raw_cutoffs",
        "r45c_powersave_9cond_autotemp_h0_h3",
    )

    def test_01_round45_c_and_python_source_contracts(self) -> None:
        shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")

        self.assertIn("#if FX6_ROUND >= 45", shim_src)
        for token in (
            "FX6_R45_STEADYSHOT_ACTIVE_BRIDGE",
            "FX6_R45_CIZ_4LOCKS_BRIDGE",
            "FX6_R45_POWERSAVE_AUTOTEMP_BRIDGE",
            "FX6_R45_LANG_TELEMETRY",
            "FX6_STAGE_B_R45_BRIDGE",
            "round45_realhw_steadyshot_ciz_powersave_autotemp=1",
        ):
            self.assertIn(token, shim_src)

        for token in (
            "r45_steadyshot_active_disqualified",
            "r45_recompute_steadyshot",
            "r45_set_steadyshot_mode",
            "r45_set_steadyshot_exposure_env",
            "setup_r45_steadyshot_active_cutoffs_probe",
            "r45_ciz_non_optical_disqualified",
            "r45_ciz_apply_4locks",
            "r45_ciz_set_zoom",
            "r45_ciz_set_focus_area",
            "r45_ciz_set_metering_mode",
            "r45_ciz_set_face_eye_af",
            "r45_ciz_set_face_multi_metering",
            "r45_ciz_set_realtime_tracking",
            "run_r45_ciz_4locks_probe",
            "r45_powersave_menu_label",
            "r45_set_power_save_start_time",
            "r45_is_power_save_timer_armed",
            "r45_preflight_airgapped_p3_cold_dump",
            "r45_set_auto_power_off_temp",
            "run_r45_powersave_autotemp_probe",
            "--r45-ciz-4locks",
            "--r45-powersave-autotemp",
            "/etc/fx6_stage_r45",
            "FX6_R45_STEADYSHOT_ACTIVE_INIT",
            "FX6_R45_CIZ_4LOCKS",
            "FX6_R45_POWERSAVE_AUTOTEMP",
        ):
            self.assertIn(token, verify_src)

        for token in (
            "enable_r45",
            "r45_mode",
            "--r45-mode",
            "steadyshot_active_cutoffs_big6",
            "ciz_4locks_hfr_raw_cutoffs",
            "powersave_9cond_autotemp_h0_h3",
            "etc/fx6_stage_r45",
            "FX6_R45_CIZ_4LOCKS_EXIT",
            "FX6_R45_POWERSAVE_AUTOTEMP_EXIT",
            '"r45_telemetry"',
            "choices=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46]",
        ):
            self.assertIn(token, runner_src)

    def test_02_round45_native_verify_c_compiles_with_zig_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r45_verc", "build_and_run_round.py")
        if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1" and not runner.ZIG.is_file():
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertTrue(runner.ZIG.is_file(), f"Missing zig compiler at {runner.ZIG}")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            cache_dir = tmp_dir / "zig-cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            for clean_flag in ("0", "1"):
                out_bin = tmp_dir / f"fx6-stage-a-verify-r45-{clean_flag}"
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

    def test_03_round45_build_binaries_compiles_shim_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r45_shimc", "build_and_run_round.py")
        if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1" and not runner.ZIG.is_file():
            self.skipTest("Clean-room fallback without local zig binary")
        with tempfile.TemporaryDirectory() as tmp:
            for clean_flag in ("0", "1"):
                work = pathlib.Path(tmp) / f"shim_{clean_flag}"
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                    launcher_b, shim_b, meta = runner.build_binaries(
                        work,
                        fx6_round=45,
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
                self.assertIn(b"FX6_R45_STEADYSHOT_ACTIVE_BRIDGE", shim_b)
                self.assertIn(b"FX6_R45_CIZ_4LOCKS_BRIDGE", shim_b)
                self.assertIn(b"FX6_R45_POWERSAVE_AUTOTEMP_BRIDGE", shim_b)
                self.assertGreater(meta["shim_bytes"], 10000)

    def test_04_round45_extract_milestones_r45a_steadyshot_and_bridges(self) -> None:
        runner = _load_closure_module("fx6_brr_r45_msa", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R45_STEADYSHOT_ACTIVE_INIT steadyshot_3modes_verified=3 active_crop_x100=110 narrower_aov_active=1 invalid_ss_reject_rc=-22 normal_le60p_allowed=5 normal_11988p_100p_cutoff_ok=1 normal_hfr_active_reject_rc=-22 sq_60fps_active_allowed=1 sq_ge100_cutoffs_verified=4 sq_hfr_active_reject_rc=-22 hdmi_raw_active_reject_rc=-16 raw_off_restores_active_ok=1 p2_write_blocked_rc=-30 p2_sha256_match=1 appfw_present=1 shim_present=1 emmc_write_count=0 r45_init_ok=1 verify_us=702667",
                "FX6_R45_STEADYSHOT_ACTIVE_BRIDGE steadyshot_3modes_verified=3 active_crop_x100=110 narrower_aov_active=1 normal_hfr_active_reject_rc=-22 sq_ge100_cutoffs_verified=4 sq_hfr_active_reject_rc=-22 hdmi_raw_active_reject_rc=-16 steadyshot_active_ok=1 emmc_write_count=0 r45_bridge_ok=1",
                "FX6_R45_CIZ_4LOCKS_BRIDGE raw_3formats_ciz_blocked=3 normal_11988p_100p_ciz_blocked=2 sq_100_120_200_240_ciz_blocked=4 focus_area_locked_rc=-16 center_priority_af_active=1 metering_locked_multi_ok=1 non_multi_metering_reject_rc=-16 face_eye_af_reject_rc=-95 face_multi_metering_reject_rc=-95 realtime_tracking_reject_rc=-95 ciz_4locks_ok=1 emmc_write_count=0 p2_setting_writes=0",
                "FX6_R45_POWERSAVE_AUTOTEMP_BRIDGE exact_menu_label_ok=1 default_5min_sec=300 powersave_9conds_deactivated=9 airgapped_5min_vault_reject_rc=-16 airgapped_off_or_30min_vault_ok=1 handheld_high_temp_reject_rc=-1 tripod_high_temp_coupled_fan_ok=1 powersave_autotemp_ok=1 emmc_write_count=0",
                "FX6_STAGE_B_R45_BRIDGE round=45 faithful=1 nop_count=0 p12_wlan=1 wf12_00342260_immune=1 p10_keymap=1 p4_nd_clear=1 p11_xlr_h1=1 lang=schinese bk4_lang=0x19 enum=0x2b45_CHINESE_SIMPLIFIED font_bank=23 str_bank=19 steadyshot_active_3cutoffs_110crop=1 ciz_4locks_hfr_raw_cutoffs=1 powersave_9cond_autotemp_high_tripod=1 emmc_write_count=0",
                "FX6_R45_LANG_TELEMETRY reason=gpermDrawFlush lang=schinese bk4_lang_id=0x02cf019c bk4_lang_val=0x19 gpe_fb=0 steadyshot_active_ok=1 ciz_4locks_ok=1 powersave_autotemp_ok=1 r45_bridge_ok=1 round45_realhw_steadyshot_ciz_powersave_autotemp=1 emmc_write_count=0 subst_color=0 subst_image=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        r45 = ms["r45_telemetry"]
        self.assertIsNotNone(r45)
        self.assertEqual(r45["steadyshot_active_init"]["active_crop_x100"], 110)
        self.assertEqual(r45["steadyshot_active_init"]["hdmi_raw_active_reject_rc"], -16)
        self.assertEqual(r45["steadyshot_active_init"]["r45_init_ok"], 1)
        self.assertEqual(r45["steadyshot_active_bridge"]["r45_bridge_ok"], 1)
        self.assertEqual(r45["ciz_4locks_bridge"]["ciz_4locks_ok"], 1)
        self.assertEqual(r45["powersave_autotemp_bridge"]["powersave_9conds_deactivated"], 9)
        self.assertEqual(r45["stage_b_bridge"]["round"], 45)
        self.assertEqual(r45["lang_telemetry"]["gpe_fb"], 0)

    def test_05_round45_extract_milestones_r45b_ciz_4locks(self) -> None:
        runner = _load_closure_module("fx6_brr_r45_msb", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R45_CIZ_4LOCKS jpeg_heif_ciz_allowed=2 raw_3formats_ciz_blocked=3 raw_format_zoom_reject_rc=-22 invalid_zoom_mode_reject_rc=-22 normal_11988p_100p_ciz_blocked=2 normal_hfr_zoom_reject_rc=-22 sq_60fps_ciz_allowed=1 sq_100_120_200_240_ciz_blocked=4 sq_hfr_zoom_reject_rc=-22 center_priority_af_active=1 focus_area_locked_rc=-16 metering_locked_multi_ok=1 non_multi_metering_reject_rc=-16 face_eye_af_reject_rc=-95 face_multi_metering_reject_rc=-95 realtime_tracking_reject_rc=-95 digital_zoom_4locks_ok=1 optical_zoom_unlocks_all_4_ok=1 p2_write_blocked_rc=-30 p2_setting_sha256_match=1 appfw_ok=1 shim_elf_ok=1 emmc_write_count=0 r45b_ok=1 verify_us=605468",
                "FX6_R45_CIZ_4LOCKS_RC=0",
                "FX6_R45_CIZ_4LOCKS_EXIT rc=0 emmc_write_count=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        r45 = ms["r45_telemetry"]
        self.assertIsNotNone(r45)
        self.assertEqual(r45["ciz_4locks_rc"], 0)
        b = r45["ciz_4locks"]
        self.assertEqual(b["raw_3formats_ciz_blocked"], 3)
        self.assertEqual(b["sq_100_120_200_240_ciz_blocked"], 4)
        self.assertEqual(b["focus_area_locked_rc"], -16)
        self.assertEqual(b["realtime_tracking_reject_rc"], -95)
        self.assertEqual(b["r45b_ok"], 1)

    def test_06_round45_extract_milestones_r45c_powersave_autotemp(self) -> None:
        runner = _load_closure_module("fx6_brr_r45_msc", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R45_POWERSAVE_AUTOTEMP exact_menu_label_ok=1 default_5min_sec=300 invalid_timer_reject_rc=-22 idle_airgapped_sleep_armed=1 powersave_9conds_deactivated=9 rearmed_after_9conds_clear_ok=1 airgapped_5min_vault_reject_rc=-16 airgapped_off_or_30min_vault_ok=1 p3_cold_dump_mib=75 default_autotemp_standard=1 invalid_autotemp_reject_rc=-22 handheld_high_temp_reject_rc=-1 fan_always_off_high_temp_reject_rc=-16 tripod_high_temp_coupled_fan_ok=1 p2_write_blocked_rc=-30 dlopen_ok=1 surfaces_verified=16 surfaces_h0_eq_h3=16 drift_bits=0 emmc_write_count=0 r45c_ok=1 verify_us=3734",
                "FX6_R45_POWERSAVE_AUTOTEMP_RC=0",
                "FX6_R45_POWERSAVE_AUTOTEMP_EXIT rc=0 emmc_write_count=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        r45 = ms["r45_telemetry"]
        self.assertIsNotNone(r45)
        self.assertEqual(r45["powersave_autotemp_rc"], 0)
        c = r45["powersave_autotemp"]
        self.assertEqual(c["exact_menu_label_ok"], 1)
        self.assertEqual(c["default_5min_sec"], 300)
        self.assertEqual(c["powersave_9conds_deactivated"], 9)
        self.assertEqual(c["handheld_high_temp_reject_rc"], -1)
        self.assertEqual(c["surfaces_h0_eq_h3"], 16)
        self.assertEqual(c["r45c_ok"], 1)

    def test_07_round45_extract_milestones_returns_none_when_no_r45_lines(self) -> None:
        runner = _load_closure_module("fx6_brr_r45_msnone", "build_and_run_round.py")
        ms = runner.extract_milestones("Linux version 4.9.337-scel+ #1 SMP PREEMPT\n")
        self.assertIsNone(ms["r45_telemetry"])

    def test_08_round45_stage_a_overlay_r45a_steadyshot_mocked_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r45_ovl_a", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            for clean_flag in ("0", "1"):
                work = tmp_dir / f"r45_a_{clean_flag}"
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                    rep, add, meta = _build_overlay_for_r45(
                        runner, tmp_dir, work, "steadyshot_active_cutoffs_big6", lang="schinese"
                    )
                init_out = rep["init"].decode("utf-8")
                self.assertNotIn("--r45-ciz-4locks", init_out)
                self.assertNotIn("--r45-powersave-autotemp", init_out)
                self.assertIn("--sd-gate", init_out)
                self.assertIn("etc/fx6_stage_r45", add)
                self.assertIn("r45_mode=steadyshot_active_cutoffs_big6", add["etc/fx6_stage_r45"][0].decode("utf-8"))
                self.assertTrue(meta["r45_enabled"])
                self.assertEqual(meta["r45"]["r45_mode"], "steadyshot_active_cutoffs_big6")
                self.assertEqual(meta["r45"]["steadyshot_active_crop_x100"], 110)
                self.assertEqual(meta["r45"]["steadyshot_hdmi_raw_reject_rc"], -16)

    def test_09_round45_stage_a_overlay_r45b_and_r45c_mocked_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r45_ovl_bc", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            for clean_flag in ("0", "1"):
                work_b = tmp_dir / f"r45_b_{clean_flag}"
                work_c = tmp_dir / f"r45_c_{clean_flag}"
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                    rep_b, _, meta_b = _build_overlay_for_r45(
                        runner, tmp_dir, work_b, "ciz_4locks_hfr_raw_cutoffs", lang="en"
                    )
                    rep_c, _, meta_c = _build_overlay_for_r45(
                        runner, tmp_dir, work_c, "powersave_9cond_autotemp_h0_h3", lang="en"
                    )
                init_b = rep_b["init"].decode("utf-8")
                init_c = rep_c["init"].decode("utf-8")
                self.assertIn("/usr/bin/fx6-stage-a-verify --r45-ciz-4locks", init_b)
                self.assertIn("FX6_R45_CIZ_4LOCKS_EXIT", init_b)
                self.assertEqual(meta_b["r45"]["r45_mode"], "ciz_4locks_hfr_raw_cutoffs")
                self.assertIn("/usr/bin/fx6-stage-a-verify --r45-powersave-autotemp", init_c)
                self.assertIn("FX6_R45_POWERSAVE_AUTOTEMP_EXIT", init_c)
                self.assertEqual(meta_c["r45"]["r45_mode"], "powersave_9cond_autotemp_h0_h3")

    def test_10_round45_stage_a_overlay_rejects_invalid_mode_and_honors_disabled_flag(self) -> None:
        runner = _load_closure_module("fx6_brr_r45_badmode", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            with self.assertRaises(ValueError):
                _build_overlay_for_r45(
                    runner, tmp_dir, tmp_dir / "bad_r45", "invalid_r45_mode", lang="schinese"
                )
            _, add_off, meta_off = _build_overlay_for_r45(
                runner, tmp_dir, tmp_dir / "off_r45", "steadyshot_active_cutoffs_big6", enable_r45=False
            )
            self.assertFalse(meta_off["r45_enabled"])
            self.assertNotIn("r45", meta_off)
            self.assertNotIn("etc/fx6_stage_r45", add_off)

    def test_11_round45_summary_json_schema_sanitization_and_audit_flags(self) -> None:
        summary_path = ROUND45_REPORT_DIR / "summary.json"
        self.assertTrue(summary_path.is_file())
        raw = summary_path.read_text(encoding="utf-8")
        for forbidden in ("/Users/", "/Volumes/KAFU2T", "/private/tmp"):
            self.assertNotIn(forbidden, raw)
        data = json.loads(raw)
        self.assertEqual(
            data["schema"],
            "fx6-on-fx3-round45-realhw-steadyshot-ciz-powersave-autotemp-qemu-v1",
        )
        self.assertEqual(data["round"], 45)
        self.assertEqual(data["raw_firmware_bytes_leaked"], 0)
        self.assertIn("Linux version 4.9.337-scel+", data["kernel_version"])
        self.assertEqual(set(data["runs"].keys()), set(self.EXPECTED_RUN_KEYS))
        audit = data["r45_realhw_steadyshot_ciz_powersave_autotemp_audit"]
        self.assertEqual(audit["round"], 45)
        self.assertEqual(audit["milestone"], 45)
        self.assertEqual(audit["total_runs"], 3)
        for k in (
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "r45a_steadyshot_active_110crop_and_3_hard_cutoffs_verified",
            "r45a_hdmi_raw_suppression_and_restore_verified",
            "r45a_stageb_big6_sid_0a_over_340k_pixels_verified",
            "r45b_ciz_digital_zoom_raw_and_hfr_cutoffs_verified",
            "r45b_ciz_beyond_optical_4_camera_state_locks_and_unlock_verified",
            "r45c_powersave_exact_label_5min_default_and_9cond_bypass_verified",
            "r45c_airgapped_75mib_p3_vault_lock_autotemp_tripod_and_16_h0_eq_h3_verified",
        ):
            self.assertTrue(audit[k], f"Audit flag {k} must be True")

    def test_12_round45_r45a_steadyshot_3modes_and_110_crop_aov(self) -> None:
        data = _load_r45_summary()
        init = data["runs"]["r45a_steadyshot_active_cutoffs_big6_schinese"]["r45_telemetry"]["steadyshot_active_init"]
        r45_meta = data["runs"]["r45a_steadyshot_active_cutoffs_big6_schinese"]["stage_b"]["r45"]
        self.assertEqual(r45_meta["steadyshot_movie_modes"], ["Off", "Standard", "Active"])
        self.assertEqual(init["steadyshot_3modes_verified"], 3)
        self.assertEqual(init["active_crop_x100"], 110)
        self.assertEqual(init["narrower_aov_active"], 1)
        self.assertEqual(init["invalid_ss_reject_rc"], -22)

    def test_13_round45_r45a_steadyshot_normal_le60p_allowed_vs_11988p_100p_cutoff(self) -> None:
        data = _load_r45_summary()
        init = data["runs"]["r45a_steadyshot_active_cutoffs_big6_schinese"]["r45_telemetry"]["steadyshot_active_init"]
        r45_meta = data["runs"]["r45a_steadyshot_active_cutoffs_big6_schinese"]["stage_b"]["r45"]
        self.assertEqual(init["normal_le60p_allowed"], 5)
        self.assertEqual(init["normal_11988p_100p_cutoff_ok"], 1)
        self.assertEqual(init["normal_hfr_active_reject_rc"], -22)
        self.assertEqual(r45_meta["steadyshot_normal_hfr_reject_rc"], -22)
        self.assertIn("119.88p/100p", r45_meta["steadyshot_active_3_cutoffs"][0])

    def test_14_round45_r45a_steadyshot_sq_60fps_allowed_vs_ge100fps_cutoffs(self) -> None:
        data = _load_r45_summary()
        init = data["runs"]["r45a_steadyshot_active_cutoffs_big6_schinese"]["r45_telemetry"]["steadyshot_active_init"]
        r45_meta = data["runs"]["r45a_steadyshot_active_cutoffs_big6_schinese"]["stage_b"]["r45"]
        self.assertEqual(init["sq_60fps_active_allowed"], 1)
        self.assertEqual(init["sq_ge100_cutoffs_verified"], 4)
        self.assertEqual(init["sq_hfr_active_reject_rc"], -22)
        self.assertEqual(r45_meta["steadyshot_sq_hfr_reject_rc"], -22)
        self.assertIn("100/120/200/240fps", r45_meta["steadyshot_active_3_cutoffs"][1])

    def test_15_round45_r45a_steadyshot_hdmi_raw_output_cutoff_and_restore(self) -> None:
        data = _load_r45_summary()
        init = data["runs"]["r45a_steadyshot_active_cutoffs_big6_schinese"]["r45_telemetry"]["steadyshot_active_init"]
        self.assertEqual(init["hdmi_raw_active_reject_rc"], -16)
        self.assertEqual(init["raw_off_restores_active_ok"], 1)

    def test_16_round45_r45a_p2_ro_firewall_and_elf_token_presence(self) -> None:
        data = _load_r45_summary()
        init = data["runs"]["r45a_steadyshot_active_cutoffs_big6_schinese"]["r45_telemetry"]["steadyshot_active_init"]
        self.assertEqual(init["p2_write_blocked_rc"], -30)
        self.assertEqual(init["p2_sha256_match"], 1)
        self.assertEqual(init["appfw_present"], 1)
        self.assertEqual(init["shim_present"], 1)
        self.assertEqual(init["emmc_write_count"], 0)
        self.assertEqual(init["r45_init_ok"], 1)

    def test_17_round45_r45a_stage_b_13_sha256_locks_and_manifest_integrity(self) -> None:
        data = _load_r45_summary()
        r45a = data["runs"]["r45a_steadyshot_active_cutoffs_big6_schinese"]
        self.assertEqual(r45a["stage_b"]["manifest_count"], 13)
        self.assertEqual(len(r45a["stage_b"]["manifest_items"]), 13)
        seen_paths = set()
        for item in r45a["stage_b"]["manifest_items"]:
            seen_paths.add(item["guest_path"])
            self.assertEqual(len(item["sha256"]), 64)
            int(item["sha256"], 16)
        self.assertIn("/usr/lib/appFw.so", seen_paths)
        self.assertIn("/usr/lib/libgrm-fbinit9.so", seen_paths)

    def test_18_round45_r45a_big6_home_schinese_render_invariants(self) -> None:
        data = _load_r45_summary()
        r45a = data["runs"]["r45a_steadyshot_active_cutoffs_big6_schinese"]
        self.assertEqual(r45a["round"], 45)
        self.assertEqual(r45a["lang"], "schinese")
        self.assertEqual(r45a["r45_mode"], "steadyshot_active_cutoffs_big6")
        self.assertEqual(r45a["target_presenter"], "31procam_big6_menu_home_presenter")
        self.assertEqual(r45a["target_sid"], "0x0a")
        self.assertEqual(r45a["nop_count"], 0)
        self.assertEqual(r45a["crashes"], 0)
        self.assertEqual(r45a["emmc_write_count"], 0)
        self.assertGreaterEqual(r45a["total_threads_seen"], 160)
        fi = r45a["faithful_invariants"]
        self.assertEqual(fi["FX6_NATIVE_FAITHFUL"], 1)
        self.assertEqual(fi["subst_color"], 0)
        self.assertEqual(fi["subst_image"], 0)
        self.assertEqual(fi["forced_render"], 0)
        self.assertEqual(fi["skipped_node"], 0)
        self.assertEqual(fi["lock_bypass"], 0)

    def test_19_round45_r45a_gpe0_framebuffer_readback_over_340k_pixels(self) -> None:
        data = _load_r45_summary()
        gpe = data["runs"]["r45a_steadyshot_active_cutoffs_big6_schinese"]["gpe0_readback"]
        lt = data["runs"]["r45a_steadyshot_active_cutoffs_big6_schinese"]["r45_telemetry"]["lang_telemetry"]
        self.assertTrue(gpe["present"])
        self.assertEqual(gpe["bytes"], 2211840)
        self.assertEqual(gpe["total_pixels"], 552960)
        self.assertEqual(gpe["nonzero_pixels"], 346206)
        self.assertGreaterEqual(gpe["unique_colors"], 80)
        self.assertEqual(lt["gpe_fb"], 0)
        self.assertEqual(lt["font_bank"], 23)
        self.assertEqual(lt["str_bank"], 19)

    def test_20_round45_r45a_alpha_png_under_50kib_crc_and_sha256(self) -> None:
        data = _load_r45_summary()
        ap = data["runs"]["r45a_steadyshot_active_cutoffs_big6_schinese"]["png_exports"]["alpha_png"]
        p = REPO_ROOT / ap["path"]
        self.assertTrue(p.is_file(), f"Missing alpha PNG: {p}")
        raw = p.read_bytes()
        self.assertLess(len(raw), 50 * 1024)
        self.assertLess(len(raw), 28 * 1024)
        self.assertEqual(len(raw), ap["bytes"])
        self.assertEqual(hashlib.sha256(raw).hexdigest(), ap["sha256"])
        w, h, rows = _decode_png_rgba_rows(raw)
        self.assertEqual((w, h, len(rows)), (1024, 540, 540))

    def test_21_round45_r45a_composited_png_under_50kib_crc_and_sha256(self) -> None:
        data = _load_r45_summary()
        cp = data["runs"]["r45a_steadyshot_active_cutoffs_big6_schinese"]["png_exports"]["composited_png"]
        p = REPO_ROOT / cp["path"]
        self.assertTrue(p.is_file(), f"Missing composited PNG: {p}")
        raw = p.read_bytes()
        self.assertLess(len(raw), 50 * 1024)
        self.assertLess(len(raw), 28 * 1024)
        self.assertEqual(len(raw), cp["bytes"])
        self.assertEqual(hashlib.sha256(raw).hexdigest(), cp["sha256"])
        w, h, rows = _decode_png_rgba_rows(raw)
        self.assertEqual((w, h, len(rows)), (1024, 540, 540))

    def test_22_round45_r45a_alpha_vs_composited_backdrop_pixel_consistency(self) -> None:
        data = _load_r45_summary()
        exp = data["runs"]["r45a_steadyshot_active_cutoffs_big6_schinese"]["png_exports"]
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

    def test_23_round45_r45a_stage_b_bridge_telemetry_flags(self) -> None:
        data = _load_r45_summary()
        sb_bridge = data["runs"]["r45a_steadyshot_active_cutoffs_big6_schinese"]["r45_telemetry"]["stage_b_bridge"]
        lt = data["runs"]["r45a_steadyshot_active_cutoffs_big6_schinese"]["r45_telemetry"]["lang_telemetry"]
        self.assertEqual(sb_bridge["round"], 45)
        self.assertEqual(sb_bridge["steadyshot_active_3cutoffs_110crop"], 1)
        self.assertEqual(sb_bridge["ciz_4locks_hfr_raw_cutoffs"], 1)
        self.assertEqual(sb_bridge["powersave_9cond_autotemp_high_tripod"], 1)
        self.assertEqual(lt["round45_realhw_steadyshot_ciz_powersave_autotemp"], 1)
        self.assertEqual(lt["r45_bridge_ok"], 1)

    def test_24_round45_r45a_prefix_counts_include_r45_and_osd_flush(self) -> None:
        data = _load_r45_summary()
        counts = data["runs"]["r45a_steadyshot_active_cutoffs_big6_schinese"]["prefix_counts"]
        self.assertGreater(counts["FX6_R45_"], 100)
        self.assertGreater(counts["FX6_OSD_FLUSH"], 100)
        self.assertEqual(counts.get("APPFW_SEGV", 0), 0)
        self.assertEqual(counts.get("FX6_ABORT_", 0), 0)

    def test_25_round45_r45b_still_jpeg_heif_allowed_vs_raw_3formats_blocked(self) -> None:
        data = _load_r45_summary()
        r45b = data["runs"]["r45b_ciz_4locks_hfr_raw_cutoffs"]
        ciz = r45b["r45_telemetry"]["ciz_4locks"]
        r45_meta = r45b["stage_b"]["r45"]
        self.assertEqual(r45b["r45_telemetry"]["ciz_4locks_rc"], 0)
        self.assertEqual(ciz["jpeg_heif_ciz_allowed"], 2)
        self.assertEqual(ciz["raw_3formats_ciz_blocked"], 3)
        self.assertEqual(ciz["raw_format_zoom_reject_rc"], -22)
        self.assertEqual(ciz["invalid_zoom_mode_reject_rc"], -22)
        self.assertEqual(r45_meta["zoom_unavailable_raw_formats"], ["RAW", "RAW & JPEG", "RAW & HEIF"])

    def test_26_round45_r45b_normal_11988p_100p_ciz_and_digital_zoom_cutoff(self) -> None:
        data = _load_r45_summary()
        ciz = data["runs"]["r45b_ciz_4locks_hfr_raw_cutoffs"]["r45_telemetry"]["ciz_4locks"]
        r45_meta = data["runs"]["r45b_ciz_4locks_hfr_raw_cutoffs"]["stage_b"]["r45"]
        self.assertEqual(ciz["normal_11988p_100p_ciz_blocked"], 2)
        self.assertEqual(ciz["normal_hfr_zoom_reject_rc"], -22)
        self.assertEqual(r45_meta["zoom_unavailable_normal_rates"], ["119.88p", "100p"])

    def test_27_round45_r45b_sq_60fps_allowed_vs_100_120_200_240_blocked(self) -> None:
        data = _load_r45_summary()
        ciz = data["runs"]["r45b_ciz_4locks_hfr_raw_cutoffs"]["r45_telemetry"]["ciz_4locks"]
        r45_meta = data["runs"]["r45b_ciz_4locks_hfr_raw_cutoffs"]["stage_b"]["r45"]
        self.assertEqual(ciz["sq_60fps_ciz_allowed"], 1)
        self.assertEqual(ciz["sq_100_120_200_240_ciz_blocked"], 4)
        self.assertEqual(ciz["sq_hfr_zoom_reject_rc"], -22)
        self.assertEqual(r45_meta["zoom_unavailable_sq_rates"], ["100fps", "120fps", "200fps", "240fps"])

    def test_28_round45_r45b_lock1_focus_area_disabled_center_priority_af(self) -> None:
        data = _load_r45_summary()
        ciz = data["runs"]["r45b_ciz_4locks_hfr_raw_cutoffs"]["r45_telemetry"]["ciz_4locks"]
        self.assertEqual(ciz["center_priority_af_active"], 1)
        self.assertEqual(ciz["focus_area_locked_rc"], -16)

    def test_29_round45_r45b_lock2_metering_mode_locked_to_multi(self) -> None:
        data = _load_r45_summary()
        ciz = data["runs"]["r45b_ciz_4locks_hfr_raw_cutoffs"]["r45_telemetry"]["ciz_4locks"]
        self.assertEqual(ciz["metering_locked_multi_ok"], 1)
        self.assertEqual(ciz["non_multi_metering_reject_rc"], -16)

    def test_30_round45_r45b_lock3_face_eye_af_and_face_priority_multi_metering_unavailable(self) -> None:
        data = _load_r45_summary()
        ciz = data["runs"]["r45b_ciz_4locks_hfr_raw_cutoffs"]["r45_telemetry"]["ciz_4locks"]
        self.assertEqual(ciz["face_eye_af_reject_rc"], -95)
        self.assertEqual(ciz["face_multi_metering_reject_rc"], -95)

    def test_31_round45_r45b_lock4_realtime_tracking_unavailable(self) -> None:
        data = _load_r45_summary()
        ciz = data["runs"]["r45b_ciz_4locks_hfr_raw_cutoffs"]["r45_telemetry"]["ciz_4locks"]
        self.assertEqual(ciz["realtime_tracking_reject_rc"], -95)

    def test_32_round45_r45b_digital_zoom_4locks_and_optical_1x_clean_unlock(self) -> None:
        data = _load_r45_summary()
        ciz = data["runs"]["r45b_ciz_4locks_hfr_raw_cutoffs"]["r45_telemetry"]["ciz_4locks"]
        self.assertEqual(ciz["digital_zoom_4locks_ok"], 1)
        self.assertEqual(ciz["optical_zoom_unlocks_all_4_ok"], 1)

    def test_33_round45_r45b_4_camera_state_locks_metadata_table(self) -> None:
        data = _load_r45_summary()
        locks = data["runs"]["r45b_ciz_4locks_hfr_raw_cutoffs"]["stage_b"]["r45"]["ciz_4_camera_state_locks"]
        self.assertEqual(len(locks), 4)
        self.assertIn("Focus Area", locks[0])
        self.assertIn("Metering Mode", locks[1])
        self.assertIn("Face/Eye Prior. in AF", locks[2])
        self.assertIn("Real-time Tracking", locks[3])

    def test_34_round45_r45b_p2_ro_protection_and_early_exit_readback_skip(self) -> None:
        data = _load_r45_summary()
        r45b = data["runs"]["r45b_ciz_4locks_hfr_raw_cutoffs"]
        ciz = r45b["r45_telemetry"]["ciz_4locks"]
        self.assertEqual(ciz["p2_write_blocked_rc"], -30)
        self.assertEqual(ciz["p2_setting_sha256_match"], 1)
        self.assertEqual(ciz["appfw_ok"], 1)
        self.assertEqual(ciz["shim_elf_ok"], 1)
        self.assertEqual(ciz["emmc_write_count"], 0)
        self.assertEqual(ciz["r45b_ok"], 1)
        self.assertFalse(r45b["gpe0_readback"]["present"])
        self.assertTrue(r45b["gpe0_readback"]["skipped_stock_fx3_mode"])

    def test_35_round45_r45b_c_source_enforces_ciz_max_200_and_digital_max_400(self) -> None:
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        self.assertIn("scale_x100 < 100 || scale_x100 > 400", verify_src)
        self.assertIn("zoom_mode == R45_ZOOM_CLEAR_IMAGE && scale_x100 > 200", verify_src)
        self.assertIn("zoom_mode == R45_ZOOM_OPTICAL_ONLY && scale_x100 > 100", verify_src)

    def test_36_round45_r45c_exact_menu_label_power_save_start_time_and_5min_default(self) -> None:
        data = _load_r45_summary()
        r45c = data["runs"]["r45c_powersave_9cond_autotemp_h0_h3"]
        ps = r45c["r45_telemetry"]["powersave_autotemp"]
        r45_meta = r45c["stage_b"]["r45"]
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        self.assertEqual(r45_meta["power_save_menu_string"], "Power Save Start Time")
        self.assertEqual(r45_meta["power_save_default"], "5 Min")
        self.assertEqual(r45_meta["power_save_default_sec"], 300)
        self.assertEqual(ps["exact_menu_label_ok"], 1)
        self.assertEqual(ps["default_5min_sec"], 300)
        self.assertEqual(ps["invalid_timer_reject_rc"], -22)
        self.assertIn('return "Power Save Start Time";', verify_src)

    def test_37_round45_r45c_all_9_bypass_conditions_enumerated_and_verified(self) -> None:
        data = _load_r45_summary()
        r45c = data["runs"]["r45c_powersave_9cond_autotemp_h0_h3"]
        ps = r45c["r45_telemetry"]["powersave_autotemp"]
        conds = r45c["stage_b"]["r45"]["power_save_9_deactivation_conditions"]
        self.assertEqual(len(conds), 9)
        self.assertEqual(
            conds,
            [
                "USB power supply",
                "slideshow playback",
                "FTP transfer",
                "movie recording",
                "computer connection",
                "TV / HDMI connection",
                "IR Remote Ctrl=On",
                "Bluetooth Rmt Ctrl=On",
                "streaming or Creators' Cloud upload",
            ],
        )
        self.assertEqual(ps["idle_airgapped_sleep_armed"], 1)
        self.assertEqual(ps["powersave_9conds_deactivated"], 9)
        self.assertEqual(ps["rearmed_after_9conds_clear_ok"], 1)

    def test_38_round45_r45c_c_source_9bit_bypass_mask_completeness(self) -> None:
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        for bit_idx, sym in enumerate(
            (
                "R45_PS_BYPASS_USB_POWER",
                "R45_PS_BYPASS_SLIDESHOW",
                "R45_PS_BYPASS_FTP_TRANSFER",
                "R45_PS_BYPASS_MOVIE_REC",
                "R45_PS_BYPASS_PC_CONN",
                "R45_PS_BYPASS_TV_HDMI",
                "R45_PS_BYPASS_IR_REMOTE_ON",
                "R45_PS_BYPASS_BT_REMOTE_ON",
                "R45_PS_BYPASS_STREAM_CLOUD",
            )
        ):
            self.assertIn(f"{sym}", verify_src)
            self.assertIn(f"(1U << {bit_idx})", verify_src)
        self.assertIn("#define R45_PS_ALL_9_MASK 0x1ffU", verify_src)

    def test_39_round45_r45c_airgapped_np_fz100_75mib_p3_cold_dump_vault_lock(self) -> None:
        data = _load_r45_summary()
        r45c = data["runs"]["r45c_powersave_9cond_autotemp_h0_h3"]
        ps = r45c["r45_telemetry"]["powersave_autotemp"]
        r45_meta = r45c["stage_b"]["r45"]
        self.assertEqual(ps["p3_cold_dump_mib"], 75)
        self.assertEqual(ps["airgapped_5min_vault_reject_rc"], -16)
        self.assertEqual(ps["airgapped_off_or_30min_vault_ok"], 1)
        self.assertEqual(r45_meta["airgapped_p3_75mib_allowed_power_save"], ["Off", "30 Min"])

    def test_40_round45_r45c_auto_power_off_temp_standard_default_and_invalid_reject(self) -> None:
        data = _load_r45_summary()
        r45c = data["runs"]["r45c_powersave_9cond_autotemp_h0_h3"]
        ps = r45c["r45_telemetry"]["powersave_autotemp"]
        r45_meta = r45c["stage_b"]["r45"]
        self.assertEqual(r45_meta["auto_power_off_temp_modes"], ["Standard", "High"])
        self.assertEqual(ps["default_autotemp_standard"], 1)
        self.assertEqual(ps["invalid_autotemp_reject_rc"], -22)

    def test_41_round45_r45c_auto_power_off_temp_high_handheld_burn_reject_eperm(self) -> None:
        data = _load_r45_summary()
        r45c = data["runs"]["r45c_powersave_9cond_autotemp_h0_h3"]
        ps = r45c["r45_telemetry"]["powersave_autotemp"]
        r45_meta = r45c["stage_b"]["r45"]
        self.assertTrue(r45_meta["auto_power_off_temp_high_requires_tripod"])
        self.assertEqual(ps["handheld_high_temp_reject_rc"], -1)
        self.assertEqual(r45_meta["auto_power_off_temp_handheld_reject_rc"], -1)

    def test_42_round45_r45c_auto_power_off_temp_high_fan_always_off_interlock(self) -> None:
        data = _load_r45_summary()
        ps = data["runs"]["r45c_powersave_9cond_autotemp_h0_h3"]["r45_telemetry"]["powersave_autotemp"]
        self.assertEqual(ps["fan_always_off_high_temp_reject_rc"], -16)
        self.assertEqual(ps["tripod_high_temp_coupled_fan_ok"], 1)

    def test_43_round45_r45c_guest_dlopen_libjit_and_16_of_16_h0_eq_h3(self) -> None:
        data = _load_r45_summary()
        r45c = data["runs"]["r45c_powersave_9cond_autotemp_h0_h3"]
        ps = r45c["r45_telemetry"]["powersave_autotemp"]
        self.assertEqual(r45c["r45_telemetry"]["powersave_autotemp_rc"], 0)
        self.assertEqual(ps["p2_write_blocked_rc"], -30)
        self.assertEqual(ps["dlopen_ok"], 1)
        self.assertEqual(ps["surfaces_verified"], 16)
        self.assertEqual(ps["surfaces_h0_eq_h3"], 16)
        self.assertEqual(ps["drift_bits"], 0)
        self.assertEqual(ps["emmc_write_count"], 0)
        self.assertEqual(ps["r45c_ok"], 1)

    def test_44_round45_cross_run_bridge_telemetry_matches_r45a_r45b_r45c(self) -> None:
        data = _load_r45_summary()
        ta = data["runs"]["r45a_steadyshot_active_cutoffs_big6_schinese"]["r45_telemetry"]
        r45b = data["runs"]["r45b_ciz_4locks_hfr_raw_cutoffs"]["r45_telemetry"]["ciz_4locks"]
        r45c = data["runs"]["r45c_powersave_9cond_autotemp_h0_h3"]["r45_telemetry"]["powersave_autotemp"]

        ssb = ta["steadyshot_active_bridge"]
        ssi = ta["steadyshot_active_init"]
        self.assertEqual(ssb["steadyshot_3modes_verified"], ssi["steadyshot_3modes_verified"])
        self.assertEqual(ssb["active_crop_x100"], ssi["active_crop_x100"])
        self.assertEqual(ssb["normal_hfr_active_reject_rc"], ssi["normal_hfr_active_reject_rc"])
        self.assertEqual(ssb["sq_ge100_cutoffs_verified"], ssi["sq_ge100_cutoffs_verified"])
        self.assertEqual(ssb["hdmi_raw_active_reject_rc"], ssi["hdmi_raw_active_reject_rc"])
        self.assertEqual(ssb["steadyshot_active_ok"], 1)

        czb = ta["ciz_4locks_bridge"]
        self.assertEqual(czb["raw_3formats_ciz_blocked"], r45b["raw_3formats_ciz_blocked"])
        self.assertEqual(czb["normal_11988p_100p_ciz_blocked"], r45b["normal_11988p_100p_ciz_blocked"])
        self.assertEqual(czb["sq_100_120_200_240_ciz_blocked"], r45b["sq_100_120_200_240_ciz_blocked"])
        self.assertEqual(czb["focus_area_locked_rc"], r45b["focus_area_locked_rc"])
        self.assertEqual(czb["non_multi_metering_reject_rc"], r45b["non_multi_metering_reject_rc"])
        self.assertEqual(czb["face_eye_af_reject_rc"], r45b["face_eye_af_reject_rc"])
        self.assertEqual(czb["realtime_tracking_reject_rc"], r45b["realtime_tracking_reject_rc"])
        self.assertEqual(czb["ciz_4locks_ok"], 1)

        psb = ta["powersave_autotemp_bridge"]
        self.assertEqual(psb["exact_menu_label_ok"], r45c["exact_menu_label_ok"])
        self.assertEqual(psb["default_5min_sec"], r45c["default_5min_sec"])
        self.assertEqual(psb["powersave_9conds_deactivated"], r45c["powersave_9conds_deactivated"])
        self.assertEqual(psb["airgapped_5min_vault_reject_rc"], r45c["airgapped_5min_vault_reject_rc"])
        self.assertEqual(psb["handheld_high_temp_reject_rc"], r45c["handheld_high_temp_reject_rc"])
        self.assertEqual(psb["powersave_autotemp_ok"], 1)

    def test_45_round45_realhw_mechanisms_verified_top_level_completeness(self) -> None:
        data = _load_r45_summary()
        rm = data["realhw_mechanisms_verified"]
        for key in (
            "steadyshot_active_110crop_and_3_hard_cutoffs_init",
            "steadyshot_active_stage_b_bridge",
            "ciz_4locks_stage_b_bridge",
            "powersave_autotemp_stage_b_bridge",
            "ciz_digital_zoom_raw_hfr_cutoffs_and_4_camera_state_locks",
            "powersave_9cond_bypass_airgapped_p3_vault_lock_autotemp_high_and_h0_h3",
        ):
            self.assertIn(key, rm)
            self.assertTrue(rm[key], f"Top-level mechanism {key} must be non-empty")

    def test_46_round45_unexecuted_physical_camera_bench_boundaries_documented(self) -> None:
        data = _load_r45_summary()
        bounds = data["unexecuted_physical_camera_bench_boundaries"]
        self.assertEqual(len(bounds), 3)
        joined = " ".join(bounds)
        for token in ("SteadyShot", "Clear Image Zoom", "Auto Power OFF Temp.", "unexecuted"):
            self.assertIn(token, joined)

    def test_47_round45_report_readme_exists_sanitized_and_links_assets(self) -> None:
        readme_path = ROUND45_REPORT_DIR / "README.md"
        self.assertTrue(readme_path.is_file())
        txt = readme_path.read_text(encoding="utf-8")
        for forbidden in ("/Users/", "/Volumes/KAFU2T", "/private/tmp"):
            self.assertNotIn(forbidden, txt)
        for token in (
            "Round 45",
            "45th Milestone",
            "Wave-31",
            "Linux version 4.9.337-scel+",
            "r45a-steadyshot-ciz-powersave-big6-schinese-alpha.png",
            "r45a-steadyshot-ciz-powersave-big6-schinese-composited.png",
            "Power Save Start Time",
            "Auto Power OFF Temp.",
            "Clear Image Zoom",
            "SteadyShot",
            "16/16 H0 == H3",
            "summary.json",
        ):
            self.assertIn(token, txt)

    def test_48_round45_closure_readme_section_45_present_and_sanitized(self) -> None:
        closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")
        for forbidden in ("/Users/", "/Volumes/KAFU2T"):
            self.assertNotIn(forbidden, closure_readme)
        marker = "## 45. Round 45 (`45th Milestone` / Wave-31)"
        self.assertIn(marker, closure_readme)
        sec45 = closure_readme.split(marker, 1)[1]
        for forbidden in ("/Users/", "/Volumes/KAFU2T", "/private/tmp"):
            self.assertNotIn(forbidden, sec45)
        for token in (
            "--round 45 --r45-mode",
            "round45-steadyshot-ciz-powersave-big6",
            "round45-ciz-4locks",
            "round45-powersave-autotemp",
            "2026-11-15-round45-realhw-steadyshot-ciz-powersave-autotemp-qemu/README.md",
        ):
            self.assertIn(token, sec45)

    def test_49_round45_wave31_primary_spec_alignment(self) -> None:
        self.assertTrue(WAVE31_SPEC_PATH.is_file())
        spec_txt = WAVE31_SPEC_PATH.read_text(encoding="utf-8")
        data = _load_r45_summary()
        r45_meta = data["runs"]["r45a_steadyshot_active_cutoffs_big6_schinese"]["stage_b"]["r45"]
        self.assertIn("Power Save Start Time", spec_txt)
        self.assertEqual(r45_meta["power_save_menu_string"], "Power Save Start Time")
        self.assertIn("Auto Power OFF Temp.", spec_txt)
        self.assertIn("Clear Image Zoom", spec_txt)

    def test_50_round45_cli_parser_accepts_all_3_r45_modes_and_rejects_unknown(self) -> None:
        runner = _load_closure_module("fx6_brr_r45_cli", "build_and_run_round.py")
        for mode in (
            "steadyshot_active_cutoffs_big6",
            "ciz_4locks_hfr_raw_cutoffs",
            "powersave_9cond_autotemp_h0_h3",
        ):
            with mock.patch.object(runner, "run_once", return_value=0) as m_run, \
                 mock.patch.object(
                     sys,
                     "argv",
                     ["build_and_run_round.py", "--run-id", "t45", "--round", "45", "--r45-mode", mode],
                 ):
                rc = runner.main()
                self.assertEqual(rc, 0)
                parsed_args = m_run.call_args[0][0]
                self.assertEqual(parsed_args.round, 45)
                self.assertEqual(parsed_args.r45_mode, mode)
                self.assertEqual(parsed_args.restore_infra70, 1)
                self.assertEqual(parsed_args.reply_all_200d, 1)

        with mock.patch.object(
            sys,
            "argv",
            ["build_and_run_round.py", "--run-id", "t45", "--round", "45", "--r45-mode", "bogus"],
        ):
            with self.assertRaises(SystemExit):
                runner.main()

    def test_51_round45_cli_default_r45_mode_is_steadyshot_active_cutoffs_big6(self) -> None:
        runner = _load_closure_module("fx6_brr_r45_clidef", "build_and_run_round.py")
        with mock.patch.object(runner, "run_once", return_value=0) as m_run, \
             mock.patch.object(
                 sys,
                 "argv",
                 ["build_and_run_round.py", "--run-id", "t45def", "--round", "45"],
             ):
            self.assertEqual(runner.main(), 0)
            self.assertEqual(m_run.call_args[0][0].r45_mode, "steadyshot_active_cutoffs_big6")

    def test_52_round45_extract_milestones_nonzero_failure_rc_propagated(self) -> None:
        runner = _load_closure_module("fx6_brr_r45_msfail", "build_and_run_round.py")
        serial = "\n".join(
            [
                "FX6_R45_CIZ_4LOCKS r45b_ok=0",
                "FX6_R45_CIZ_4LOCKS_RC=237",
                "FX6_R45_POWERSAVE_AUTOTEMP r45c_ok=0",
                "FX6_R45_POWERSAVE_AUTOTEMP_RC=238",
            ]
        )
        r45 = runner.extract_milestones(serial)["r45_telemetry"]
        self.assertEqual(r45["ciz_4locks_rc"], 237)
        self.assertEqual(r45["powersave_autotemp_rc"], 238)
        self.assertEqual(r45["ciz_4locks"]["r45b_ok"], 0)
        self.assertEqual(r45["powersave_autotemp"]["r45c_ok"], 0)

    def test_53_round45_no_forbidden_binaries_or_oversized_assets_in_report_dir(self) -> None:
        forbidden_exts = {".cpio", ".so", ".o", ".img", ".qcow2", ".pyc", ".raw", ".bin"}
        files = [p for p in ROUND45_REPORT_DIR.rglob("*") if p.is_file()]
        self.assertEqual(len(files), 4)
        for p in files:
            self.assertNotIn(p.suffix.lower(), forbidden_exts, f"Forbidden artifact {p}")
            if p.suffix.lower() == ".png":
                self.assertLess(p.stat().st_size, 50 * 1024, f"Oversized PNG {p}")

    def test_54_round45_prior_round44_summary_contract_untouched(self) -> None:
        r44_summary = (
            REPO_ROOT
            / "reports"
            / "2026-11-15-round44-realhw-pixelmap-ntscpal-gammaassist-displaylut-qemu"
            / "summary.json"
        )
        self.assertTrue(r44_summary.is_file())
        d44 = json.loads(r44_summary.read_text(encoding="utf-8"))
        self.assertEqual(d44["round"], 44)
        self.assertEqual(d44["raw_firmware_bytes_leaked"], 0)


if __name__ == "__main__":
    unittest.main()
