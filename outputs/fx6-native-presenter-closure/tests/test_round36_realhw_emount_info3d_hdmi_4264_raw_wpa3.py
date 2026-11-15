#!/usr/bin/env python3
"""Offline dual-mode unit tests for FX6-on-FX3 Round 36 real-hardware QEMU rehearsal."""
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
ROUND36_REPORT_DIR = (
    REPO_ROOT / "reports" / "2026-11-15-round36-realhw-emount-info3d-hdmi-4264-raw-wpa3-qemu"
)
ROUND36_ASSETS_DIR = ROUND36_REPORT_DIR / "assets"


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

    class _FakeBmtv:
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
    return parent_cpio, _FakePatcher, _FakeVfat, _FakeBmtv, fake_subproc_run, fake_jit_meta


class TestRound36RealHwEmountInfo3dHdmi4264RawWpa3(unittest.TestCase):
    EXPECTED_RUN_KEYS = (
        "r36a_emount_info3d_big6_schinese",
        "r36b_hdmi_4264_raw_prores_braw",
        "r36c_wpa2_wpa3_focusmap_bridge",
    )

    def test_01_round36_c_and_python_source_contracts(self) -> None:
        shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")

        self.assertIn("#if FX6_ROUND >= 36", shim_src)
        for token in (
            "FX6_R36_EMOUNT_INFO3D_BRIDGE",
            "FX6_R36_LANG_TELEMETRY",
            "FX6_STAGE_B_R36_BRIDGE",
            "0x02cf0232U",
            "g_r36_breathing_bk4_hits",
            "realhw_emount_info3d_hdmi_4264_raw_wpa3=1",
        ):
            self.assertIn(token, shim_src)

        for token in (
            "setup_r36_emount_info3d_probe",
            "r36_is_sony_emount_lens",
            "r36_eval_breathing_comp",
            "r36_cinealta_lensfile_write_gate",
            "r36_hdmi_edid_vsif_negotiate",
            "r36_eval_simultaneous_rec_stream",
            "run_r36_hdmi_4264_raw_probe",
            "r36_wlan_sanitizer_gate",
            "run_r36_wpa3_focusmap_probe",
            "--r36-hdmi-4264-raw",
            "--r36-wpa3-focusmap",
            "/etc/fx6_stage_r36",
            "FX6_R36_EMOUNT_INFO3D_INIT",
            "FX6_R36_HDMI_4264_RAW",
            "FX6_R36_WPA3_FOCUSMAP",
        ):
            self.assertIn(token, verify_src)

        for token in (
            "enable_r36",
            "r36_mode",
            "--r36-mode",
            "emount_info3d_big6",
            "hdmi_4264_raw_prores_braw",
            "wpa2_wpa3_focusmap_bridge",
            "etc/fx6_stage_r36",
            "FX6_R36_HDMI_4264_RAW_EXIT",
            "FX6_R36_WPA3_FOCUSMAP_EXIT",
            '"r36_telemetry"',
            "choices=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39]",
        ):
            self.assertIn(token, runner_src)

    def test_02_round36_native_verify_c_compiles_with_zig_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r36_verc", "build_and_run_round.py")
        self.assertTrue(runner.ZIG.is_file(), f"Missing zig compiler at {runner.ZIG}")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            cache_dir = tmp_dir / "zig-cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            for clean_flag in ("0", "1"):
                out_bin = tmp_dir / f"fx6-stage-a-verify-r36-{clean_flag}"
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

    def test_03_round36_build_binaries_compiles_shim_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r36_shimc", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            for clean_flag in ("0", "1"):
                work = pathlib.Path(tmp) / f"shim_{clean_flag}"
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                    launcher_b, shim_b, meta = runner.build_binaries(
                        work,
                        fx6_round=36,
                        restore_infra70=1,
                        restore_all_early=0,
                        reply_all_200d=1,
                        initial_setting_done=1,
                        key_seq="0x7028:120:5500",
                        key_settle_ms=5500,
                        lang="schinese",
                    )
                self.assertEqual(launcher_b[:4], b"\x7fELF")
                self.assertEqual(shim_b[:4], b"\x7fELF")
                self.assertGreater(meta["shim_bytes"], 10000)

    def test_04_round36_extract_milestones_r36a_emount_info3d_and_bridge(self) -> None:
        runner = _load_closure_module("fx6_brr_r36_msa", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R36_EMOUNT_INFO3D_INIT p18_lensfile=/mnt/r36_p18/lens/LENSFILE.BIN p18_lensfile_erofs=1 p18_lensfile_errno=30 p18_r30_lens_erofs=1 lensfile_sha256_before=aaa lensfile_sha256_after=aaa lensfile_sha256_match=1 cinealta_lensfile_write_rc=-30 cinealta_slot_blocked=1 lensfile_writes=0 info7_ok=1 info8_ok=1 info3d_ok=1 bkid_breathing=0x02cf0232 sony_lens_id=0xC123 sony_0xc123_shift14_eq3=1 sony_0xc123_breathing_on=1 sony_crop_permille=1085 thirdparty_lens_id=0x4123 thirdparty_0x4123_shift14_eq3=0 thirdparty_0x4123_gated_off=1 manual_lens_id=0xFFFF manual_0xffff_gated_off=1 appfw_present=1 emmc_write_count=0 r36_init_ok=1 verify_us=656452",
                "FX6_R36_EMOUNT_INFO3D_BRIDGE p18_lensfile_erofs_ok=1 lensfile_ro_ok=1 sony_0xc123_breathing_on=1 thirdparty_0x4123_gated_off=1 manual_0xffff_gated_off=1 bkid_02cf0232_val=0x01 sdi_mmio_probes=0 raw_clean_master=1 wpa2_wpa3_sanitizer=1 focusmap_ro_bridge=1 emmc_write_count=0 r36_bridge_ok=1",
                "FX6_STAGE_B_R36_BRIDGE round=36 faithful=1 nop_count=0 p12_wlan=1 wf12_00342260_immune=1 p10_keymap=1 p4_nd_clear=1 p11_xlr_h1=1 lang=schinese bk4_lang=0x19 enum=0x2b45_CHINESE_SIMPLIFIED font_bank=23 str_bank=19 emount_info3d_breathing=1 p18_lensfile_erofs=1 hdmi_4264_raw_prores_braw=1 sdi_mmio_masked=1 wpa2_wpa3_sanitizer=1 focusmap_ro_bridge=1 emmc_write_count=0",
                "FX6_R36_LANG_TELEMETRY reason=pump lang=schinese bk4_lang_id=0x02cf019c bk4_lang_val=0x19 gpe_fb=0 p18_lensfile_erofs_ok=1 lensfile_ro_ok=1 sony_0xc123_breathing_on=1 r36_bridge_ok=1 realhw_emount_info3d_hdmi_4264_raw_wpa3=1 sdi_mmio_probes=0 emmc_write_count=0 subst_color=0 subst_image=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        r36 = ms["r36_telemetry"]
        self.assertIsNotNone(r36)
        self.assertEqual(r36["emount_info3d_init"]["p18_lensfile_erofs"], 1)
        self.assertEqual(r36["emount_info3d_init"]["p18_lensfile_errno"], 30)
        self.assertEqual(r36["emount_info3d_init"]["cinealta_lensfile_write_rc"], -30)
        self.assertEqual(r36["emount_info3d_init"]["sony_0xc123_breathing_on"], 1)
        self.assertEqual(r36["emount_info3d_init"]["thirdparty_0x4123_gated_off"], 1)
        self.assertEqual(r36["emount_info3d_init"]["manual_0xffff_gated_off"], 1)
        self.assertEqual(r36["emount_info3d_bridge"]["r36_bridge_ok"], 1)
        self.assertEqual(r36["stage_b_bridge"]["round"], 36)
        self.assertEqual(r36["lang_telemetry"]["gpe_fb"], 0)

    def test_05_round36_extract_milestones_r36b_hdmi_4264_raw(self) -> None:
        runner = _load_closure_module("fx6_brr_r36_msb", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R36_HDMI_4264_RAW hdmi_port=TypeA raw_width=4264 raw_height=2408 raw_fps=60 raw_bit_depth=16 va12g_braw_rc=0 va12g_braw_ok=1 braw_iso_locked=1 va3g_rejected=1 va3g_reject_rc=-95 atomos_ninja_rc=0 atomos_ninja_ok=1 prores_wb_kelvin=5600 prores_tint=-2 prores_iso_offset_ev=1 prores_wb_iso_meta_ok=1 internal_xavc_si_proxy_ok=1 mpr_dlopen_ok=1 mpr_syms_resolved=6 anamorphic_15x_nonbake=1 anamorphic_16x_nonbake=1 mlut_nonbake=1 raw_clean_master=1 sdi_raw_masked=1 sdi_raw_mask_rc=-19 sdi_mmio_probes=0 emmc_write_count=0 r36b_ok=1 verify_us=24272",
                "FX6_R36_HDMI_RAW_RC=0",
                "FX6_R36_HDMI_4264_RAW_EXIT rc=0 emmc_write_count=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        r36 = ms["r36_telemetry"]
        self.assertIsNotNone(r36)
        self.assertEqual(r36["hdmi_raw_rc"], 0)
        b = r36["hdmi_4264_raw"]
        self.assertEqual(b["raw_width"], 4264)
        self.assertEqual(b["raw_height"], 2408)
        self.assertEqual(b["raw_fps"], 60)
        self.assertEqual(b["raw_bit_depth"], 16)
        self.assertEqual(b["va12g_braw_ok"], 1)
        self.assertEqual(b["va3g_reject_rc"], -95)
        self.assertEqual(b["atomos_ninja_ok"], 1)
        self.assertEqual(b["raw_clean_master"], 1)
        self.assertEqual(b["sdi_mmio_probes"], 0)
        self.assertEqual(b["r36b_ok"], 1)

    def test_06_round36_extract_milestones_r36c_wpa2_wpa3_focusmap(self) -> None:
        runner = _load_closure_module("fx6_brr_r36_msc", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R36_WPA3_FOCUSMAP wep_rc=-22 wpa1_tkip_rc=-22 ipsec_rc=-22 wpa2_ccmp_rc=0 wpa3_sae_rc=0 legacy_wlan_rejected=1 wpa2_wpa3_accepted=1 rejected_before_supplicant=3 supplicant_legacy_hits=0 wlan_libs_ok=1 mc_client_min_ver=2.1.0 focus_map_frames=12 focus_map_bytes=384 focus_map_tmpfs_ok=1 backup_bin_erofs=1 backup_bin_errno=30 backup_sha256_before=bbb backup_sha256_after=bbb backup_sha256_match=1 backup_writes=0 emmc_write_count=0 r36c_ok=1 verify_us=2816",
                "FX6_R36_WPA3_FOCUSMAP_RC=0",
                "FX6_R36_WPA3_FOCUSMAP_EXIT rc=0 emmc_write_count=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        r36 = ms["r36_telemetry"]
        self.assertIsNotNone(r36)
        self.assertEqual(r36["wpa3_focusmap_rc"], 0)
        c = r36["wpa3_focusmap"]
        self.assertEqual(c["wep_rc"], -22)
        self.assertEqual(c["wpa1_tkip_rc"], -22)
        self.assertEqual(c["ipsec_rc"], -22)
        self.assertEqual(c["wpa2_ccmp_rc"], 0)
        self.assertEqual(c["wpa3_sae_rc"], 0)
        self.assertEqual(c["rejected_before_supplicant"], 3)
        self.assertEqual(c["supplicant_legacy_hits"], 0)
        self.assertEqual(c["focus_map_frames"], 12)
        self.assertEqual(c["backup_bin_errno"], 30)
        self.assertEqual(c["r36c_ok"], 1)

    def test_07_round36_stage_a_overlay_emount_info3d_big6_mocked_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r36_ovl_a", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            parent_cpio, fp, fv, fb, fake_run, jit_meta = _build_mock_cpio_and_fakes(runner, tmp_dir)
            for clean_flag in ("0", "1"):
                work = tmp_dir / f"r36_a_{clean_flag}"
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}), \
                     mock.patch.object(runner, "_import_stage_a_modules", return_value=(fp, fv, fb)), \
                     mock.patch.object(runner, "_load_p10_keymap_spec", return_value=mock.Mock(spec_id="P10_k", library_name="appFw.so", sites=(mock.Mock(site_id="p10", size=4),))), \
                     mock.patch.object(runner, "_load_p12_wlan_spec", return_value=mock.Mock(spec_id="P12_w", library_name="libWlanResource.so", sites=(mock.Mock(site_id="p12", size=8),))), \
                     mock.patch.object(runner, "build_hardened_libjit_so", return_value=(b"\x7fELF_JIT", dict(jit_meta))), \
                     mock.patch.object(runner, "build_r30_tier0_libjit_so", return_value=(b"\x7fELF_R30_JIT", dict(jit_meta))), \
                     mock.patch.object(runner.subprocess, "run", side_effect=fake_run):
                    rep, add, meta = runner.build_stage_a_overlay(
                        work, parent_cpio, b"BK4NTSC",
                        enable_p10=True, enable_r10=True, enable_p12=True, enable_r28=True,
                        enable_r30=True, r30_mode="peripheral_big6",
                        enable_r31=True, r31_mode="keymap_big6",
                        enable_r32=True, r32_mode="imx510_cube_big6",
                        enable_r33=True, r33_mode="cfexpress_rsv_big6",
                        enable_r34=True, r34_mode="c2pa_tc_gyro_big6",
                        enable_r35=True, r35_mode="ssboot_wbi2_big6",
                        enable_r36=True, r36_mode="emount_info3d_big6",
                        sd_manifest_mode="valid", lang="schinese", shim_bytes=b"SHIM",
                    )
                init_out = rep["init"].decode("utf-8")
                self.assertNotIn("--r36-hdmi-4264-raw", init_out)
                self.assertNotIn("--r36-wpa3-focusmap", init_out)
                self.assertIn("--sd-gate", init_out)
                self.assertIn("etc/fx6_stage_r36", add)
                self.assertIn("r36_mode=emount_info3d_big6", add["etc/fx6_stage_r36"][0].decode("utf-8"))
                self.assertTrue(meta["r36_enabled"])
                self.assertEqual(meta["r36"]["r36_mode"], "emount_info3d_big6")
                self.assertEqual(meta["r36"]["p18_lensfile_path"], "p18:/lens/LENSFILE.BIN")
                self.assertEqual(meta["r36"]["bkid_breathing_hex"], "0x02cf0232")
                self.assertEqual(meta["r36"]["emount_packets"], ["info7", "info8", "info3D"])

    def test_08_round36_stage_a_overlay_hdmi_4264_raw_mocked_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r36_ovl_b", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            parent_cpio, fp, fv, fb, fake_run, jit_meta = _build_mock_cpio_and_fakes(runner, tmp_dir)
            for clean_flag in ("0", "1"):
                work = tmp_dir / f"r36_b_{clean_flag}"
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}), \
                     mock.patch.object(runner, "_import_stage_a_modules", return_value=(fp, fv, fb)), \
                     mock.patch.object(runner, "_load_p10_keymap_spec", return_value=mock.Mock(spec_id="P10_k", library_name="appFw.so", sites=(mock.Mock(site_id="p10", size=4),))), \
                     mock.patch.object(runner, "_load_p12_wlan_spec", return_value=mock.Mock(spec_id="P12_w", library_name="libWlanResource.so", sites=(mock.Mock(site_id="p12", size=8),))), \
                     mock.patch.object(runner, "build_hardened_libjit_so", return_value=(b"\x7fELF_JIT", dict(jit_meta))), \
                     mock.patch.object(runner, "build_r30_tier0_libjit_so", return_value=(b"\x7fELF_R30_JIT", dict(jit_meta))), \
                     mock.patch.object(runner.subprocess, "run", side_effect=fake_run):
                    rep, add, meta = runner.build_stage_a_overlay(
                        work, parent_cpio, b"BK4NTSC",
                        enable_p10=True, enable_r10=True, enable_p12=True, enable_r28=True,
                        enable_r30=True, r30_mode="peripheral_big6",
                        enable_r31=True, r31_mode="keymap_big6",
                        enable_r32=True, r32_mode="imx510_cube_big6",
                        enable_r33=True, r33_mode="cfexpress_rsv_big6",
                        enable_r34=True, r34_mode="c2pa_tc_gyro_big6",
                        enable_r35=True, r35_mode="ssboot_wbi2_big6",
                        enable_r36=True, r36_mode="hdmi_4264_raw_prores_braw",
                        sd_manifest_mode="valid", lang="en", shim_bytes=b"SHIM",
                    )
                init_out = rep["init"].decode("utf-8")
                self.assertIn("/usr/bin/fx6-stage-a-verify --r36-hdmi-4264-raw", init_out)
                self.assertIn("FX6_R36_HDMI_4264_RAW_EXIT", init_out)
                self.assertEqual(meta["r36"]["r36_mode"], "hdmi_4264_raw_prores_braw")
                self.assertEqual(meta["r36"]["hdmi_raw_resolution"], "4264x2408")
                self.assertEqual(meta["r36"]["hdmi_raw_fps"], 60)
                self.assertEqual(meta["r36"]["hdmi_raw_bit_depth"], 16)

    def test_09_round36_stage_a_overlay_wpa2_wpa3_focusmap_mocked_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r36_ovl_c", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            parent_cpio, fp, fv, fb, fake_run, jit_meta = _build_mock_cpio_and_fakes(runner, tmp_dir)
            for clean_flag in ("0", "1"):
                work = tmp_dir / f"r36_c_{clean_flag}"
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}), \
                     mock.patch.object(runner, "_import_stage_a_modules", return_value=(fp, fv, fb)), \
                     mock.patch.object(runner, "_load_p10_keymap_spec", return_value=mock.Mock(spec_id="P10_k", library_name="appFw.so", sites=(mock.Mock(site_id="p10", size=4),))), \
                     mock.patch.object(runner, "_load_p12_wlan_spec", return_value=mock.Mock(spec_id="P12_w", library_name="libWlanResource.so", sites=(mock.Mock(site_id="p12", size=8),))), \
                     mock.patch.object(runner, "build_hardened_libjit_so", return_value=(b"\x7fELF_JIT", dict(jit_meta))), \
                     mock.patch.object(runner, "build_r30_tier0_libjit_so", return_value=(b"\x7fELF_R30_JIT", dict(jit_meta))), \
                     mock.patch.object(runner.subprocess, "run", side_effect=fake_run):
                    rep, add, meta = runner.build_stage_a_overlay(
                        work, parent_cpio, b"BK4NTSC",
                        enable_p10=True, enable_r10=True, enable_p12=True, enable_r28=True,
                        enable_r30=True, r30_mode="peripheral_big6",
                        enable_r31=True, r31_mode="keymap_big6",
                        enable_r32=True, r32_mode="imx510_cube_big6",
                        enable_r33=True, r33_mode="cfexpress_rsv_big6",
                        enable_r34=True, r34_mode="c2pa_tc_gyro_big6",
                        enable_r35=True, r35_mode="ssboot_wbi2_big6",
                        enable_r36=True, r36_mode="wpa2_wpa3_focusmap_bridge",
                        sd_manifest_mode="valid", lang="en", shim_bytes=b"SHIM",
                    )
                init_out = rep["init"].decode("utf-8")
                self.assertIn("/usr/bin/fx6-stage-a-verify --r36-wpa3-focusmap", init_out)
                self.assertIn("FX6_R36_WPA3_FOCUSMAP_EXIT", init_out)
                self.assertEqual(meta["r36"]["r36_mode"], "wpa2_wpa3_focusmap_bridge")
                self.assertTrue(meta["r36"]["wpa2_wpa3_only"])
                self.assertEqual(meta["r36"]["mc_client_min_version"], "2.1.0")
                self.assertEqual(meta["r36"]["backup_ro_path"], "p2:/setting/Backup.bin")

    def test_10_round36_stage_a_overlay_rejects_invalid_r36_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r36_badmode", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            parent_cpio, fp, fv, fb, fake_run, jit_meta = _build_mock_cpio_and_fakes(runner, tmp_dir)
            with mock.patch.object(runner, "_import_stage_a_modules", return_value=(fp, fv, fb)), \
                 mock.patch.object(runner, "_load_p10_keymap_spec", return_value=mock.Mock(spec_id="P10_k", library_name="appFw.so", sites=(mock.Mock(site_id="p10", size=4),))), \
                 mock.patch.object(runner, "_load_p12_wlan_spec", return_value=mock.Mock(spec_id="P12_w", library_name="libWlanResource.so", sites=(mock.Mock(site_id="p12", size=8),))), \
                 mock.patch.object(runner, "build_hardened_libjit_so", return_value=(b"\x7fELF_JIT", dict(jit_meta))), \
                 mock.patch.object(runner, "build_r30_tier0_libjit_so", return_value=(b"\x7fELF_R30_JIT", dict(jit_meta))), \
                 mock.patch.object(runner.subprocess, "run", side_effect=fake_run):
                with self.assertRaises(ValueError):
                    runner.build_stage_a_overlay(
                        tmp_dir / "bad_r36", parent_cpio, b"BK4NTSC",
                        enable_p10=True, enable_r10=True, enable_p12=True, enable_r28=True,
                        enable_r30=True, r30_mode="peripheral_big6",
                        enable_r31=True, r31_mode="keymap_big6",
                        enable_r32=True, r32_mode="imx510_cube_big6",
                        enable_r33=True, r33_mode="cfexpress_rsv_big6",
                        enable_r34=True, r34_mode="c2pa_tc_gyro_big6",
                        enable_r35=True, r35_mode="ssboot_wbi2_big6",
                        enable_r36=True, r36_mode="invalid_r36_mode",
                        lang="schinese", shim_bytes=b"SHIM",
                    )

    def test_11_round36_summary_json_schema_sanitization_and_audit_flags(self) -> None:
        summary_path = ROUND36_REPORT_DIR / "summary.json"
        self.assertTrue(summary_path.is_file())
        raw = summary_path.read_text(encoding="utf-8")
        for forbidden in ("/Users/", "/Volumes/KAFU2T", "/private/tmp"):
            self.assertNotIn(forbidden, raw)
        data = json.loads(raw)
        self.assertEqual(data["schema"], "fx6-on-fx3-round36-realhw-emount-info3d-hdmi-4264-raw-wpa3-qemu-v1")
        self.assertIn("Linux version 4.9.337-scel+", data["kernel_version"])
        self.assertEqual(set(data["runs"].keys()), set(self.EXPECTED_RUN_KEYS))
        audit = data["r36_realhw_emount_info3d_hdmi_4264_raw_wpa3_audit"]
        self.assertEqual(audit["total_runs"], 3)
        for k in (
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "r36a_p18_lensfile_erofs_and_emount_info3d_breathing_verified",
            "r36a_stageb_big6_sid_0a_over_340k_pixels_verified",
            "r36b_hdmi_4264x2408_braw_prores_and_va3g_reject_verified",
            "r36b_anamorphic_nonbake_and_masked_sdi_mmio_zero_verified",
            "r36c_wpa2_wpa3_sanitizer_rejects_legacy_before_supplicant_verified",
            "r36c_mc210_focusmap_tmpfs_bridge_and_backup_erofs_verified",
        ):
            self.assertTrue(audit[k], f"Audit flag {k} must be True")

    def test_12_round36_r36a_p18_lensfile_erofs_and_cinealta_slot_blocked(self) -> None:
        data = json.loads((ROUND36_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        init = data["runs"]["r36a_emount_info3d_big6_schinese"]["r36_telemetry"]["emount_info3d_init"]
        self.assertEqual(init["p18_lensfile"], "/mnt/r36_p18/lens/LENSFILE.BIN")
        self.assertEqual(init["p18_lensfile_erofs"], 1)
        self.assertEqual(init["p18_lensfile_errno"], 30)
        self.assertEqual(init["p18_r30_lens_erofs"], 1)
        self.assertEqual(len(init["lensfile_sha256_before"]), 64)
        self.assertEqual(init["lensfile_sha256_before"], init["lensfile_sha256_after"])
        self.assertEqual(init["lensfile_sha256_match"], 1)
        self.assertEqual(init["cinealta_lensfile_write_rc"], -30)
        self.assertEqual(init["cinealta_slot_blocked"], 1)
        self.assertEqual(init["lensfile_writes"], 0)
        self.assertEqual(init["emmc_write_count"], 0)

    def test_13_round36_r36a_emount_info7_info8_info3d_and_sony_lens_filter_02cf0232(self) -> None:
        data = json.loads((ROUND36_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        telem = data["runs"]["r36a_emount_info3d_big6_schinese"]["r36_telemetry"]
        init = telem["emount_info3d_init"]
        br = telem["emount_info3d_bridge"]
        self.assertEqual(init["info7_ok"], 1)
        self.assertEqual(init["info8_ok"], 1)
        self.assertEqual(init["info3d_ok"], 1)
        self.assertEqual(init["bkid_breathing"], "0x02cf0232")
        self.assertEqual(init["sony_lens_id"], "0xC123")
        self.assertEqual(init["sony_0xc123_shift14_eq3"], 1)
        self.assertEqual(init["sony_0xc123_breathing_on"], 1)
        self.assertEqual(init["sony_crop_permille"], 1085)
        self.assertEqual(init["thirdparty_lens_id"], "0x4123")
        self.assertEqual(init["thirdparty_0x4123_shift14_eq3"], 0)
        self.assertEqual(init["thirdparty_0x4123_gated_off"], 1)
        self.assertEqual(init["manual_lens_id"], "0xFFFF")
        self.assertEqual(init["manual_0xffff_gated_off"], 1)
        self.assertEqual(init["appfw_present"], 1)
        self.assertEqual(init["r36_init_ok"], 1)
        self.assertEqual(br["bkid_02cf0232_val"], "0x01")
        self.assertEqual(br["r36_bridge_ok"], 1)

    def test_14_round36_r36a_stage_b_13_sha256_and_big6_render_invariants(self) -> None:
        data = json.loads((ROUND36_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        r36a = data["runs"]["r36a_emount_info3d_big6_schinese"]
        self.assertEqual(r36a["round"], 36)
        self.assertEqual(r36a["r36_mode"], "emount_info3d_big6")
        self.assertEqual(r36a["target_presenter"], "31procam_big6_menu_home_presenter")
        self.assertEqual(r36a["target_sid"], "0x0a")
        self.assertEqual(r36a["nop_count"], 0)
        self.assertEqual(r36a["crashes"], 0)
        self.assertEqual(r36a["emmc_write_count"], 0)
        self.assertGreaterEqual(r36a["total_threads_seen"], 160)
        self.assertEqual(r36a["faithful_invariants"]["FX6_NATIVE_FAITHFUL"], 1)
        self.assertEqual(r36a["stage_b"]["manifest_count"], 13)
        self.assertEqual(len(r36a["stage_b"]["manifest_items"]), 13)
        for item in r36a["stage_b"]["manifest_items"]:
            self.assertEqual(len(item["sha256"]), 64)
            int(item["sha256"], 16)
        lt = r36a["r36_telemetry"]["lang_telemetry"]
        self.assertEqual(lt["gpe_fb"], 0)
        self.assertEqual(lt["subst_color"], 0)
        self.assertEqual(lt["subst_image"], 0)
        self.assertEqual(lt["breathing_bk4_hits"], 2)
        self.assertEqual(lt["r36_bridge_ok"], 1)
        self.assertGreater(r36a["gpe0_readback"]["nonzero_pixels"], 340000)

    def test_15_round36_r36a_png_receipts_under_28kib_and_dimensions(self) -> None:
        data = json.loads((ROUND36_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        exports = data["runs"]["r36a_emount_info3d_big6_schinese"]["png_exports"]
        for key in ("alpha_png", "composited_png"):
            p = REPO_ROOT / exports[key]["path"]
            self.assertTrue(p.is_file(), f"Missing Round 36 PNG: {p}")
            raw = p.read_bytes()
            self.assertLess(len(raw), 28 * 1024, f"PNG exceeds 28 KiB: {p} ({len(raw)} bytes)")
            self.assertEqual(len(raw), exports[key]["bytes"])
            self.assertEqual(hashlib.sha256(raw).hexdigest(), exports[key]["sha256"])
            w, h, rows = _decode_png_rgba_rows(raw)
            self.assertEqual((w, h), (1024, 540))
            if key == "alpha_png":
                nonzero_alpha = sum(
                    sum(1 for a in row[3::4] if a != 0)
                    for row in rows
                )
                self.assertGreater(nonzero_alpha, 340000)

    def test_16_round36_r36b_hdmi_4264x2408_60p_16bit_braw_and_va3g_eopnotsupp(self) -> None:
        data = json.loads((ROUND36_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        r36b = data["runs"]["r36b_hdmi_4264_raw_prores_braw"]
        self.assertEqual(r36b["round"], 36)
        self.assertEqual(r36b["r36_mode"], "hdmi_4264_raw_prores_braw")
        self.assertEqual(r36b["crashes"], 0)
        self.assertEqual(r36b["emmc_write_count"], 0)
        self.assertTrue(r36b["gpe0_readback"]["skipped_stock_fx3_mode"])
        self.assertEqual(r36b["r36_telemetry"]["hdmi_raw_rc"], 0)
        b = r36b["r36_telemetry"]["hdmi_4264_raw"]
        self.assertEqual(b["hdmi_port"], "TypeA")
        self.assertEqual(b["raw_width"], 4264)
        self.assertEqual(b["raw_height"], 2408)
        self.assertEqual(b["raw_fps"], 60)
        self.assertEqual(b["raw_bit_depth"], 16)
        self.assertEqual(b["va12g_braw_rc"], 0)
        self.assertEqual(b["va12g_braw_ok"], 1)
        self.assertEqual(b["braw_iso_locked"], 1)
        self.assertEqual(b["va3g_rejected"], 1)
        self.assertEqual(b["va3g_reject_rc"], -95)
        self.assertEqual(b["r36b_ok"], 1)

    def test_17_round36_r36b_atomos_ninja_prores_raw_wb_iso_metadata_and_mpr(self) -> None:
        data = json.loads((ROUND36_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        b = data["runs"]["r36b_hdmi_4264_raw_prores_braw"]["r36_telemetry"]["hdmi_4264_raw"]
        self.assertEqual(b["atomos_ninja_rc"], 0)
        self.assertEqual(b["atomos_ninja_ok"], 1)
        self.assertEqual(b["prores_wb_kelvin"], 5600)
        self.assertEqual(b["prores_tint"], -2)
        self.assertEqual(b["prores_iso_offset_ev"], 1)
        self.assertEqual(b["prores_wb_iso_meta_ok"], 1)
        self.assertEqual(b["internal_xavc_si_proxy_ok"], 1)
        self.assertEqual(b["mpr_dlopen_ok"], 1)
        self.assertEqual(b["mpr_syms_resolved"], 6)

    def test_18_round36_r36b_anamorphic_15x_16x_mlut_nonbake_and_sdi_masked_zero_mmio(self) -> None:
        data = json.loads((ROUND36_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        b = data["runs"]["r36b_hdmi_4264_raw_prores_braw"]["r36_telemetry"]["hdmi_4264_raw"]
        self.assertEqual(b["anamorphic_15x_nonbake"], 1)
        self.assertEqual(b["anamorphic_16x_nonbake"], 1)
        self.assertEqual(b["mlut_nonbake"], 1)
        self.assertEqual(b["raw_clean_master"], 1)
        self.assertEqual(b["sdi_raw_masked"], 1)
        self.assertEqual(b["sdi_raw_mask_rc"], -19)
        self.assertEqual(b["sdi_mmio_probes"], 0)
        self.assertEqual(b["emmc_write_count"], 0)

    def test_19_round36_r36c_wlan_sanitizer_rejects_wep_wpa1_ipsec_before_supplicant(self) -> None:
        data = json.loads((ROUND36_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        r36c = data["runs"]["r36c_wpa2_wpa3_focusmap_bridge"]
        self.assertEqual(r36c["round"], 36)
        self.assertEqual(r36c["r36_mode"], "wpa2_wpa3_focusmap_bridge")
        self.assertEqual(r36c["crashes"], 0)
        self.assertEqual(r36c["emmc_write_count"], 0)
        self.assertTrue(r36c["gpe0_readback"]["skipped_stock_fx3_mode"])
        self.assertEqual(r36c["r36_telemetry"]["wpa3_focusmap_rc"], 0)
        c = r36c["r36_telemetry"]["wpa3_focusmap"]
        self.assertEqual(c["wep_rc"], -22)
        self.assertEqual(c["wpa1_tkip_rc"], -22)
        self.assertEqual(c["ipsec_rc"], -22)
        self.assertEqual(c["legacy_wlan_rejected"], 1)
        self.assertEqual(c["rejected_before_supplicant"], 3)
        self.assertEqual(c["supplicant_legacy_hits"], 0)
        self.assertEqual(c["r36c_ok"], 1)

    def test_20_round36_r36c_wpa2_ccmp_wpa3_sae_accepted_and_wlan_libs_verified(self) -> None:
        data = json.loads((ROUND36_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        c = data["runs"]["r36c_wpa2_wpa3_focusmap_bridge"]["r36_telemetry"]["wpa3_focusmap"]
        self.assertEqual(c["wpa2_ccmp_rc"], 0)
        self.assertEqual(c["wpa3_sae_rc"], 0)
        self.assertEqual(c["wpa2_wpa3_accepted"], 1)
        self.assertEqual(c["wlan_libs_ok"], 1)

    def test_21_round36_r36c_mc210_focusmap_tmpfs_bridge_without_emmc_writes(self) -> None:
        data = json.loads((ROUND36_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        c = data["runs"]["r36c_wpa2_wpa3_focusmap_bridge"]["r36_telemetry"]["wpa3_focusmap"]
        self.assertEqual(c["mc_client_min_ver"], "2.1.0")
        self.assertEqual(c["focus_map_frames"], 12)
        self.assertEqual(c["focus_map_bytes"], 384)
        self.assertEqual(c["focus_map_tmpfs_ok"], 1)
        self.assertEqual(c["emmc_write_count"], 0)

    def test_22_round36_r36c_p2_backup_bin_erofs_sha256_immutable(self) -> None:
        data = json.loads((ROUND36_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        c = data["runs"]["r36c_wpa2_wpa3_focusmap_bridge"]["r36_telemetry"]["wpa3_focusmap"]
        self.assertEqual(c["backup_bin_erofs"], 1)
        self.assertEqual(c["backup_bin_errno"], 30)
        self.assertEqual(len(c["backup_sha256_before"]), 64)
        self.assertEqual(c["backup_sha256_before"], c["backup_sha256_after"])
        self.assertEqual(c["backup_sha256_match"], 1)
        self.assertEqual(c["backup_writes"], 0)

    def test_23_round36_stage_b_bridge_mechanisms_and_bench_boundaries(self) -> None:
        data = json.loads((ROUND36_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        mech = data["realhw_mechanisms_verified"]
        self.assertEqual(mech["emount_info3d_breathing_and_p18_erofs"]["r36_init_ok"], 1)
        self.assertEqual(mech["emount_info3d_stage_b_bridge"]["r36_bridge_ok"], 1)
        self.assertEqual(mech["hdmi_type_a_4264x2408_16bit_raw_braw_prores"]["r36b_ok"], 1)
        self.assertEqual(mech["wpa2_wpa3_sanitizer_and_focusmap_ro_bridge"]["r36c_ok"], 1)

        br = data["runs"]["r36a_emount_info3d_big6_schinese"]["r36_telemetry"]["stage_b_bridge"]
        for key in (
            "faithful",
            "p12_wlan",
            "wf12_00342260_immune",
            "p10_keymap",
            "p4_nd_clear",
            "p11_xlr_h1",
            "emount_info3d_breathing",
            "p18_lensfile_erofs",
            "hdmi_4264_raw_prores_braw",
            "sdi_mmio_masked",
            "wpa2_wpa3_sanitizer",
            "focusmap_ro_bridge",
        ):
            self.assertEqual(br[key], 1, f"Expected stage_b_bridge[{key}]==1")
        self.assertEqual(br["round"], 36)
        self.assertEqual(br["nop_count"], 0)
        self.assertEqual(br["emmc_write_count"], 0)
        self.assertEqual(len(data["unexecuted_physical_camera_bench_boundaries"]), 3)

    def test_24_round36_readme_sanitization_and_no_tmp_or_binary_residue(self) -> None:
        closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn("2026-11-15-round36-realhw-emount-info3d-hdmi-4264-raw-wpa3-qemu", closure_readme)
        self.assertIn("`24` New Round 36 Dual-Mode Unit Tests (`450` Total)", closure_readme)
        r36_readme = (ROUND36_REPORT_DIR / "README.md").read_text(encoding="utf-8")
        for tok in (
            "MIRA_CETUS2",
            "info7/info8/info3D",
            "0x02cf0232",
            "LENSFILE.BIN",
            "0xC123",
            "4264x2408",
            "Video Assist 12G",
            "Atomos Ninja",
            "12G-SDI",
            "WPA2/WPA3",
            "Monitor & Control 2.1.0+",
            "r36a-emount-info3d-big6-schinese",
            "r36b-hdmi-4264-raw-prores-braw",
            "r36c-wpa2-wpa3-focusmap-bridge",
        ):
            self.assertIn(tok, r36_readme)
        for forbidden in ("/Users/", "/Volumes/KAFU2T", "/private/tmp"):
            self.assertNotIn(forbidden, r36_readme)
        for folder in (CLOSURE_DIR, ROUND36_REPORT_DIR):
            for p in folder.rglob("*"):
                if p.is_file():
                    self.assertNotIn(p.suffix, {".cpio", ".so", ".o", ".img", ".qcow2", ".pyc"})


if __name__ == "__main__":
    unittest.main()
