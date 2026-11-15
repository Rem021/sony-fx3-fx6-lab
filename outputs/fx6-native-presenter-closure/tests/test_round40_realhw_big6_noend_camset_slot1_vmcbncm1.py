#!/usr/bin/env python3
"""Offline dual-mode unit tests for FX6-on-FX3 Round 40 (40th Milestone QEMU Rehearsal)."""
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
ROUND40_REPORT_DIR = (
    REPO_ROOT / "reports" / "2026-11-15-round40-realhw-big6-noend-camset-slot1-vmcbncm1-tcin-qemu"
)
ROUND40_ASSETS_DIR = ROUND40_REPORT_DIR / "assets"


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
                sha256=hashlib.sha256(bk4),
                flash_write_allowed=False, active_byte8_selector=0, synthesized_key_count=1,
            )

    # Ensure sha256 string matches build_stage_a_overlay expectations
    class _FakeBmtvHex(_FakeBmtv):
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


class TestRound40RealHwBig6NoEndCamsetSlot1VmcBncm1(unittest.TestCase):
    EXPECTED_RUN_KEYS = (
        "r40a_big6_home_noend_schinese",
        "r40b_camset_slot1_dualmedia_split",
        "r40c_vmcbncm1_tcin_hdmi_tcout",
    )

    def test_01_round40_c_and_python_source_contracts(self) -> None:
        shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")

        self.assertIn("#if FX6_ROUND >= 40", shim_src)
        for token in (
            "FX6_R40_BIG6_NOEND_BRIDGE",
            "FX6_R40_CAMSET_TC_BRIDGE",
            "FX6_R40_LANG_TELEMETRY",
            "FX6_STAGE_B_R40_BRIDGE",
            "milestone_round40_realhw_big6_noend_camset_vmcbncm1=1",
        ):
            self.assertIn(token, shim_src)

        for token in (
            "r40_big6_init_state",
            "r40_big6_enter_home",
            "r40_big6_set_lower_left_mode",
            "r40_big6_cp_end_actuator_firewall",
            "r40_big6_set_emount_aperture",
            "r40_big6_set_virtual_nd_display",
            "setup_r40_big6_home_noend_probe",
            "r40_camset_resolve_slot1_dir",
            "r40_camset_save_or_load_gate",
            "r40_camset_stage_b_sandbox_save",
            "run_r40_camset_slot1_split_probe",
            "r40_vmcbncm1_eval_tcin",
            "r40_hdmi_eval_digital_tcout",
            "run_r40_vmcbncm1_tcin_hdmi_probe",
            "--r40-camset-slot1-split",
            "--r40-vmcbncm1-tcin-hdmi",
            "/etc/fx6_stage_r40",
            "FX6_R40_BIG6_NOEND_INIT",
            "FX6_R40_CAMSET_SLOT1_SPLIT",
            "FX6_R40_VMCBNCM1_TCIN_HDMI",
        ):
            self.assertIn(token, verify_src)

        for token in (
            "enable_r40",
            "r40_mode",
            "--r40-mode",
            "big6_home_noend_big6",
            "camset_slot1_dualmedia_split",
            "vmcbncm1_tcin_hdmi_tcout",
            "etc/fx6_stage_r40",
            "FX6_R40_CAMSET_SLOT1_SPLIT_EXIT",
            "FX6_R40_VMCBNCM1_TCIN_HDMI_EXIT",
            '"r40_telemetry"',
            "choices=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40]",
        ):
            self.assertIn(token, runner_src)

    def test_02_round40_native_verify_c_compiles_with_zig_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r40_verc", "build_and_run_round.py")
        if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1" and not runner.ZIG.is_file():
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertTrue(runner.ZIG.is_file(), f"Missing zig compiler at {runner.ZIG}")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            cache_dir = tmp_dir / "zig-cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            for clean_flag in ("0", "1"):
                out_bin = tmp_dir / f"fx6-stage-a-verify-r40-{clean_flag}"
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

    def test_03_round40_build_binaries_compiles_shim_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r40_shimc", "build_and_run_round.py")
        if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1" and not runner.ZIG.is_file():
            self.skipTest("Clean-room fallback without local zig binary")
        with tempfile.TemporaryDirectory() as tmp:
            for clean_flag in ("0", "1"):
                work = pathlib.Path(tmp) / f"shim_{clean_flag}"
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                    launcher_b, shim_b, meta = runner.build_binaries(
                        work,
                        fx6_round=40,
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

    def test_04_round40_extract_milestones_r40a_big6_noend_and_bridge(self) -> None:
        runner = _load_closure_module("fx6_brr_r40_msa", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R40_BIG6_NOEND_INIT mode_settings=Fixed_Variable home_key_bound=1 not_fixed_var_reject_rc=-22 no_home_key_reject_rc=-22 home_enter_rc=0 big6_tile_count=6 status_bar_zone=1 tiles_verified=6 default_lower_left=Aperture toggle_nd_filter_rc=0 toggle_aperture_rc=0 invalid_ll_reject_rc=-22 emount_aperture_rc=0 virtual_nd_display_rc=0 virtual_nd_range_reject_rc=-34 end_1_4_reject_rc=-95 end_1_128_reject_rc=-95 end_stops_blocked=6 e_nd_actuator_tx_count=0 appfw_present=1 shim_present=1 emmc_write_count=0 r40_init_ok=1 verify_us=586254",
                "FX6_R40_BIG6_NOEND_BRIDGE big6_tiles=6 mode_settings=Fixed_Variable lower_left_modes=Aperture_NDFilter end_actuator_reject_rc=-95 e_nd_actuator_tx_count=0 virtual_nd_metadata_only=1 big6_topology_ok=1 no_end_firewall_ok=1 emmc_write_count=0 r40_bridge_ok=1",
                "FX6_R40_CAMSET_TC_BRIDGE camset_slot1_only=1 camset_max_profiles=10 sd_camset_dir=/PRIVATE/SONY/SETTING/FX3/CAMSET/ cfx_camset_dir=/SONY/SETTING/FX3/CAMSET/ slot2_reject_rc=-22 save_11th_reject_rc=-28 mr_mode_lock_rc=-16 cross_model_dat_reject_rc=-79 camset_overlay_dir=/tmp/fx6_camset_overlay vmcbncm1_body_tcin_only=1 ext_lk_holdover_min_ms=10000 handle_usb_reject_rc=-19 bnc_tcout_reject_rc=-95 hdmi_tcout_movie_only=1 camset_split_ok=1 vmcbncm1_tc_ok=1 p2_setting_writes=0 emmc_write_count=0",
                "FX6_STAGE_B_R40_BRIDGE round=40 faithful=1 nop_count=0 p12_wlan=1 wf12_00342260_immune=1 p10_keymap=1 p4_nd_clear=1 p11_xlr_h1=1 lang=schinese bk4_lang=0x19 enum=0x2b45_CHINESE_SIMPLIFIED font_bank=23 str_bank=19 big6_home_6tile_no_end=1 lower_left_aperture_nd_toggle=1 camset_slot1_dualmedia_split=1 vmcbncm1_body_tcin_hdmi_tcout=1 emmc_write_count=0",
                "FX6_R40_LANG_TELEMETRY reason=pump lang=schinese bk4_lang_id=0x02cf019c bk4_lang_val=0x19 gpe_fb=0 big6_topology_ok=1 no_end_firewall_ok=1 camset_split_ok=1 vmcbncm1_tc_ok=1 r40_bridge_ok=1 milestone_round40_realhw_big6_noend_camset_vmcbncm1=1 emmc_write_count=0 subst_color=0 subst_image=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        r40 = ms["r40_telemetry"]
        self.assertIsNotNone(r40)
        self.assertEqual(r40["big6_noend_init"]["big6_tile_count"], 6)
        self.assertEqual(r40["big6_noend_init"]["end_1_4_reject_rc"], -95)
        self.assertEqual(r40["big6_noend_init"]["e_nd_actuator_tx_count"], 0)
        self.assertEqual(r40["big6_noend_init"]["r40_init_ok"], 1)
        self.assertEqual(r40["big6_noend_bridge"]["r40_bridge_ok"], 1)
        self.assertEqual(r40["camset_tc_bridge"]["camset_overlay_dir"], "/tmp/fx6_camset_overlay")
        self.assertEqual(r40["stage_b_bridge"]["round"], 40)
        self.assertEqual(r40["lang_telemetry"]["gpe_fb"], 0)

    def test_05_round40_extract_milestones_r40b_camset_slot1_split(self) -> None:
        runner = _load_closure_module("fx6_brr_r40_msb", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R40_CAMSET_SLOT1_SPLIT sd_camset_dir=/PRIVATE/SONY/SETTING/FX3/CAMSET/ cfx_camset_dir=/SONY/SETTING/FX3/CAMSET/ sd_saved_count=10 sd_loaded_count=10 cfx_saved_count=10 cfx_loaded_count=10 sd_save_11th_reject_rc=-28 cfx_save_11th_reject_rc=-28 overwrite_existing_slot_rc=0 slot2_save_reject_rc=-22 slot2_load_reject_rc=-22 mr_mode_save_reject_rc=-16 mr_mode_load_reject_rc=-16 wrong_prefix_on_sd_rc=-22 wrong_prefix_on_cfx_rc=-22 fx3a_dat_reject_rc=-79 fx6_dat_reject_rc=-79 excluded_machine_bound_fields=5 stageb_overlay_dir=/tmp/fx6_camset_overlay stageb_overlay_saved=10 p2_write_blocked_rc=-30 p2_setting_sha256_match=1 slot1_fx3_camset_intact=10 appfw_camset_ok=1 shim_elf_ok=1 emmc_write_count=0 r40b_ok=1 verify_us=599200",
                "FX6_R40_CAMSET_RC=0",
                "FX6_R40_CAMSET_SLOT1_SPLIT_EXIT rc=0 emmc_write_count=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        r40 = ms["r40_telemetry"]
        self.assertIsNotNone(r40)
        self.assertEqual(r40["camset_rc"], 0)
        b = r40["camset_slot1_split"]
        self.assertEqual(b["sd_camset_dir"], "/PRIVATE/SONY/SETTING/FX3/CAMSET/")
        self.assertEqual(b["cfx_camset_dir"], "/SONY/SETTING/FX3/CAMSET/")
        self.assertEqual(b["sd_saved_count"], 10)
        self.assertEqual(b["cfx_saved_count"], 10)
        self.assertEqual(b["sd_save_11th_reject_rc"], -28)
        self.assertEqual(b["slot2_save_reject_rc"], -22)
        self.assertEqual(b["mr_mode_save_reject_rc"], -16)
        self.assertEqual(b["fx3a_dat_reject_rc"], -79)
        self.assertEqual(b["fx6_dat_reject_rc"], -79)
        self.assertEqual(b["r40b_ok"], 1)

    def test_06_round40_extract_milestones_r40c_vmcbncm1_tcin_hdmi(self) -> None:
        runner = _load_closure_module("fx6_brr_r40_msc", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R40_VMCBNCM1_TCIN_HDMI adapter_model=VMC-BNCM1 part_no=A-5051-506-A cable_len_cm=20 body_usb_port=Multi_Micro_USB pre_10s_9999ms_rc=-11 body_movie_preset_freerun_10s_rc=0 ext_lk_locked=1 holdover_active=1 release_on_sq_locked=0 release_on_tcmake_regen_locked=0 release_on_tcrun_recrun_locked=0 release_on_tcpreset_edit_locked=0 xlrh1_handle_usb_reject_rc=-19 bnc_tcout_reject_rc=-95 bnc_tcout_tx_count=0 hdmi_type_a_movie_tcout_rc=0 hdmi_movie_tcout_active=1 hdmi_sq_tcout_reject_rc=-95 hdmi_sq_tcout_active=0 hdmi_sq_tcout_disabled=1 p2_write_blocked_rc=-30 dlopen_ok=1 surfaces_verified=16 surfaces_h0_eq_h3=16 drift_bits=0 emmc_write_count=0 r40c_ok=1 verify_us=6296",
                "FX6_R40_VMCBNCM1_RC=0",
                "FX6_R40_VMCBNCM1_TCIN_HDMI_EXIT rc=0 emmc_write_count=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        r40 = ms["r40_telemetry"]
        self.assertIsNotNone(r40)
        self.assertEqual(r40["vmcbncm1_rc"], 0)
        c = r40["vmcbncm1_tcin_hdmi"]
        self.assertEqual(c["adapter_model"], "VMC-BNCM1")
        self.assertEqual(c["part_no"], "A-5051-506-A")
        self.assertEqual(c["ext_lk_locked"], 1)
        self.assertEqual(c["xlrh1_handle_usb_reject_rc"], -19)
        self.assertEqual(c["bnc_tcout_reject_rc"], -95)
        self.assertEqual(c["hdmi_movie_tcout_active"], 1)
        self.assertEqual(c["hdmi_sq_tcout_disabled"], 1)
        self.assertEqual(c["surfaces_h0_eq_h3"], 16)
        self.assertEqual(c["r40c_ok"], 1)

    def test_07_round40_stage_a_overlay_big6_home_noend_big6_mocked_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r40_ovl_a", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            parent_cpio, fp, fv, fb, fake_run, jit_meta = _build_mock_cpio_and_fakes(runner, tmp_dir)
            for clean_flag in ("0", "1"):
                work = tmp_dir / f"r40_a_{clean_flag}"
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
                        enable_r37=True, r37_mode="fx3a_firewall_big6",
                        enable_r38=True, r38_mode="nouvc_dcc1_pd_big6",
                        enable_r39=True, r39_mode="fan_pwm_offinrec_big6",
                        enable_r40=True, r40_mode="big6_home_noend_big6",
                        sd_manifest_mode="valid", lang="schinese", shim_bytes=b"SHIM",
                    )
                init_out = rep["init"].decode("utf-8")
                self.assertNotIn("--r40-camset-slot1-split", init_out)
                self.assertNotIn("--r40-vmcbncm1-tcin-hdmi", init_out)
                self.assertIn("--sd-gate", init_out)
                self.assertIn("etc/fx6_stage_r40", add)
                self.assertIn("r40_mode=big6_home_noend_big6", add["etc/fx6_stage_r40"][0].decode("utf-8"))
                self.assertTrue(meta["r40_enabled"])
                self.assertEqual(meta["r40"]["r40_mode"], "big6_home_noend_big6")
                self.assertEqual(meta["r40"]["big6_mode_settings_prerequisite"], "Fixed/Variable")
                self.assertEqual(len(meta["r40"]["big6_tiles"]), 6)
                self.assertEqual(meta["r40"]["big6_lower_left_modes"], ["Aperture", "ND Filter"])
                self.assertEqual(meta["r40"]["e_nd_actuator_reject_rc"], -95)
                self.assertEqual(meta["r40"]["e_nd_actuator_tx_count"], 0)

    def test_08_round40_stage_a_overlay_camset_slot1_dualmedia_split_mocked_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r40_ovl_b", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            parent_cpio, fp, fv, fb, fake_run, jit_meta = _build_mock_cpio_and_fakes(runner, tmp_dir)
            for clean_flag in ("0", "1"):
                work = tmp_dir / f"r40_b_{clean_flag}"
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
                        enable_r37=True, r37_mode="fx3a_firewall_big6",
                        enable_r38=True, r38_mode="nouvc_dcc1_pd_big6",
                        enable_r39=True, r39_mode="fan_pwm_offinrec_big6",
                        enable_r40=True, r40_mode="camset_slot1_dualmedia_split",
                        sd_manifest_mode="valid", lang="en", shim_bytes=b"SHIM",
                    )
                init_out = rep["init"].decode("utf-8")
                self.assertIn("/usr/bin/fx6-stage-a-verify --r40-camset-slot1-split", init_out)
                self.assertIn("FX6_R40_CAMSET_SLOT1_SPLIT_EXIT", init_out)
                self.assertEqual(meta["r40"]["r40_mode"], "camset_slot1_dualmedia_split")
                self.assertEqual(meta["r40"]["camset_allowed_slot"], 1)
                self.assertEqual(meta["r40"]["camset_max_profiles"], 10)
                self.assertEqual(meta["r40"]["sd_camset_dir"], "/PRIVATE/SONY/SETTING/FX3/CAMSET/")
                self.assertEqual(meta["r40"]["cfx_camset_dir"], "/SONY/SETTING/FX3/CAMSET/")
                self.assertEqual(meta["r40"]["camset_cross_model_reject_rc"], -79)

    def test_09_round40_stage_a_overlay_vmcbncm1_tcin_hdmi_tcout_mocked_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r40_ovl_c", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            parent_cpio, fp, fv, fb, fake_run, jit_meta = _build_mock_cpio_and_fakes(runner, tmp_dir)
            for clean_flag in ("0", "1"):
                work = tmp_dir / f"r40_c_{clean_flag}"
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
                        enable_r37=True, r37_mode="fx3a_firewall_big6",
                        enable_r38=True, r38_mode="nouvc_dcc1_pd_big6",
                        enable_r39=True, r39_mode="fan_pwm_offinrec_big6",
                        enable_r40=True, r40_mode="vmcbncm1_tcin_hdmi_tcout",
                        sd_manifest_mode="valid", lang="en", shim_bytes=b"SHIM",
                    )
                init_out = rep["init"].decode("utf-8")
                self.assertIn("/usr/bin/fx6-stage-a-verify --r40-vmcbncm1-tcin-hdmi", init_out)
                self.assertIn("FX6_R40_VMCBNCM1_TCIN_HDMI_EXIT", init_out)
                self.assertEqual(meta["r40"]["r40_mode"], "vmcbncm1_tcin_hdmi_tcout")
                self.assertEqual(meta["r40"]["vmcbncm1_part_no"], "A-5051-506-A")
                self.assertEqual(meta["r40"]["vmcbncm1_ext_lk_min_ms"], 10000)
                self.assertEqual(meta["r40"]["vmcbncm1_handle_usb_reject_rc"], -19)
                self.assertEqual(meta["r40"]["vmcbncm1_bnc_tcout_reject_rc"], -95)
                self.assertEqual(meta["r40"]["hdmi_digital_tcout_port"], "Type-A HDMI")
                self.assertTrue(meta["r40"]["hdmi_tcout_sq_disabled"])

    def test_10_round40_stage_a_overlay_rejects_invalid_r40_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r40_badmode", "build_and_run_round.py")
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
                        tmp_dir / "bad_r40", parent_cpio, b"BK4NTSC",
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
                        enable_r40=True, r40_mode="invalid_r40_mode",
                        lang="schinese", shim_bytes=b"SHIM",
                    )

    def test_11_round40_summary_json_schema_sanitization_and_audit_flags(self) -> None:
        summary_path = ROUND40_REPORT_DIR / "summary.json"
        self.assertTrue(summary_path.is_file())
        raw = summary_path.read_text(encoding="utf-8")
        for forbidden in ("/Users/", "/Volumes/KAFU2T", "/private/tmp"):
            self.assertNotIn(forbidden, raw)
        data = json.loads(raw)
        self.assertEqual(data["schema"], "fx6-on-fx3-round40-realhw-big6-noend-camset-slot1-vmcbncm1-tcin-qemu-v1")
        self.assertEqual(data["milestone"], 40)
        self.assertIn("Linux version 4.9.337-scel+", data["kernel_version"])
        self.assertEqual(set(data["runs"].keys()), set(self.EXPECTED_RUN_KEYS))
        audit = data["r40_realhw_big6_noend_camset_slot1_vmcbncm1_audit"]
        self.assertEqual(audit["milestone_round"], 40)
        self.assertEqual(audit["total_runs"], 3)
        for k in (
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "r40a_big6_6tile_and_home_lower_left_aperture_nd_verified",
            "r40a_zero_e_nd_actuator_tx_firewall_verified",
            "r40a_stageb_big6_sid_0a_over_340k_pixels_verified",
            "r40b_slot1_only_camset_10slot_dualmedia_path_split_verified",
            "r40b_mr_lockout_and_cross_model_dat_firewall_verified",
            "r40c_vmcbncm1_body_only_tcin_10s_ext_lk_and_xlrh1_bnc_blocks_verified",
            "r40c_hdmi_movie_tcout_sq_disabled_and_16_h0_eq_h3_verified",
        ):
            self.assertTrue(audit[k], f"Audit flag {k} must be True")

    def test_12_round40_r40a_big6_6tile_topology_and_home_lower_left_toggle(self) -> None:
        data = json.loads((ROUND40_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        init = data["runs"]["r40a_big6_home_noend_schinese"]["r40_telemetry"]["big6_noend_init"]
        self.assertEqual(init["mode_settings"], "Fixed_Variable")
        self.assertEqual(init["home_key_bound"], 1)
        self.assertEqual(init["not_fixed_var_reject_rc"], -22)
        self.assertEqual(init["no_home_key_reject_rc"], -22)
        self.assertEqual(init["home_enter_rc"], 0)
        self.assertEqual(init["big6_tile_count"], 6)
        self.assertEqual(init["status_bar_zone"], 1)
        self.assertEqual(init["tiles_verified"], 6)
        self.assertEqual(init["default_lower_left"], "Aperture")
        self.assertEqual(init["toggle_nd_filter_rc"], 0)
        self.assertEqual(init["toggle_aperture_rc"], 0)
        self.assertEqual(init["invalid_ll_reject_rc"], -22)

    def test_13_round40_r40a_zero_e_nd_actuator_firewall(self) -> None:
        data = json.loads((ROUND40_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        init = data["runs"]["r40a_big6_home_noend_schinese"]["r40_telemetry"]["big6_noend_init"]
        self.assertEqual(init["emount_aperture_rc"], 0)
        self.assertEqual(init["virtual_nd_display_rc"], 0)
        self.assertEqual(init["virtual_nd_range_reject_rc"], -34)
        self.assertEqual(init["end_1_4_reject_rc"], -95)
        self.assertEqual(init["end_1_128_reject_rc"], -95)
        self.assertEqual(init["end_stops_blocked"], 6)
        self.assertEqual(init["e_nd_actuator_tx_count"], 0)
        self.assertEqual(init["emmc_write_count"], 0)

    def test_14_round40_r40a_bridge_telemetry_verified(self) -> None:
        data = json.loads((ROUND40_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        telem = data["runs"]["r40a_big6_home_noend_schinese"]["r40_telemetry"]
        init = telem["big6_noend_init"]
        br = telem["big6_noend_bridge"]
        self.assertEqual(init["appfw_present"], 1)
        self.assertEqual(init["shim_present"], 1)
        self.assertEqual(init["r40_init_ok"], 1)
        self.assertEqual(br["big6_tiles"], 6)
        self.assertEqual(br["mode_settings"], "Fixed_Variable")
        self.assertEqual(br["lower_left_modes"], "Aperture_NDFilter")
        self.assertEqual(br["end_actuator_reject_rc"], -95)
        self.assertEqual(br["e_nd_actuator_tx_count"], 0)
        self.assertEqual(br["virtual_nd_metadata_only"], 1)
        self.assertEqual(br["big6_topology_ok"], 1)
        self.assertEqual(br["no_end_firewall_ok"], 1)
        self.assertEqual(br["r40_bridge_ok"], 1)

    def test_15_round40_r40a_stage_b_13_sha256_and_big6_render_invariants(self) -> None:
        data = json.loads((ROUND40_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        r40a = data["runs"]["r40a_big6_home_noend_schinese"]
        self.assertEqual(r40a["round"], 40)
        self.assertEqual(r40a["r40_mode"], "big6_home_noend_big6")
        self.assertEqual(r40a["target_presenter"], "31procam_big6_menu_home_presenter")
        self.assertEqual(r40a["target_sid"], "0x0a")
        self.assertEqual(r40a["nop_count"], 0)
        self.assertEqual(r40a["crashes"], 0)
        self.assertEqual(r40a["emmc_write_count"], 0)
        self.assertGreaterEqual(r40a["total_threads_seen"], 160)
        self.assertEqual(r40a["faithful_invariants"]["FX6_NATIVE_FAITHFUL"], 1)
        self.assertEqual(r40a["stage_b"]["manifest_count"], 13)
        self.assertEqual(len(r40a["stage_b"]["manifest_items"]), 13)
        for item in r40a["stage_b"]["manifest_items"]:
            self.assertEqual(len(item["sha256"]), 64)
            int(item["sha256"], 16)
        lt = r40a["r40_telemetry"]["lang_telemetry"]
        self.assertEqual(lt["gpe_fb"], 0)
        self.assertEqual(lt["subst_color"], 0)
        self.assertEqual(lt["subst_image"], 0)
        self.assertEqual(lt["r40_bridge_ok"], 1)
        self.assertEqual(lt["milestone_round40_realhw_big6_noend_camset_vmcbncm1"], 1)
        self.assertGreater(r40a["gpe0_readback"]["nonzero_pixels"], 340000)

    def test_16_round40_r40a_png_receipts_under_28kib_and_dimensions(self) -> None:
        data = json.loads((ROUND40_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        exports = data["runs"]["r40a_big6_home_noend_schinese"]["png_exports"]
        for key in ("alpha_png", "composited_png"):
            p = REPO_ROOT / exports[key]["path"]
            self.assertTrue(p.is_file(), f"Missing Round 40 PNG: {p}")
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

    def test_17_round40_r40b_slot1_only_10slot_camset_dual_media_path_split(self) -> None:
        data = json.loads((ROUND40_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        r40b = data["runs"]["r40b_camset_slot1_dualmedia_split"]
        self.assertEqual(r40b["round"], 40)
        self.assertEqual(r40b["r40_mode"], "camset_slot1_dualmedia_split")
        self.assertEqual(r40b["crashes"], 0)
        self.assertEqual(r40b["emmc_write_count"], 0)
        self.assertTrue(r40b["gpe0_readback"]["skipped_stock_fx3_mode"])
        self.assertEqual(r40b["r40_telemetry"]["camset_rc"], 0)
        b = r40b["r40_telemetry"]["camset_slot1_split"]
        self.assertEqual(b["sd_camset_dir"], "/PRIVATE/SONY/SETTING/FX3/CAMSET/")
        self.assertEqual(b["cfx_camset_dir"], "/SONY/SETTING/FX3/CAMSET/")
        self.assertEqual(b["sd_saved_count"], 10)
        self.assertEqual(b["sd_loaded_count"], 10)
        self.assertEqual(b["cfx_saved_count"], 10)
        self.assertEqual(b["cfx_loaded_count"], 10)
        self.assertEqual(b["sd_save_11th_reject_rc"], -28)
        self.assertEqual(b["cfx_save_11th_reject_rc"], -28)
        self.assertEqual(b["overwrite_existing_slot_rc"], 0)
        self.assertEqual(b["slot2_save_reject_rc"], -22)
        self.assertEqual(b["slot2_load_reject_rc"], -22)
        self.assertEqual(b["wrong_prefix_on_sd_rc"], -22)
        self.assertEqual(b["wrong_prefix_on_cfx_rc"], -22)
        self.assertEqual(b["r40b_ok"], 1)

    def test_18_round40_r40b_mr_lockout_cross_model_dat_firewall_and_tmp_overlay(self) -> None:
        data = json.loads((ROUND40_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        b = data["runs"]["r40b_camset_slot1_dualmedia_split"]["r40_telemetry"]["camset_slot1_split"]
        self.assertEqual(b["mr_mode_save_reject_rc"], -16)
        self.assertEqual(b["mr_mode_load_reject_rc"], -16)
        self.assertEqual(b["fx3a_dat_reject_rc"], -79)
        self.assertEqual(b["fx6_dat_reject_rc"], -79)
        self.assertEqual(b["excluded_machine_bound_fields"], 5)
        self.assertEqual(b["stageb_overlay_dir"], "/tmp/fx6_camset_overlay")
        self.assertEqual(b["stageb_overlay_saved"], 10)
        self.assertEqual(b["p2_write_blocked_rc"], -30)
        self.assertEqual(b["p2_setting_sha256_match"], 1)
        self.assertEqual(b["slot1_fx3_camset_intact"], 10)
        self.assertEqual(b["appfw_camset_ok"], 1)
        self.assertEqual(b["shim_elf_ok"], 1)
        self.assertEqual(b["emmc_write_count"], 0)

    def test_19_round40_r40c_vmcbncm1_body_only_tcin_10s_ext_lk_and_release_rules(self) -> None:
        data = json.loads((ROUND40_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        r40c = data["runs"]["r40c_vmcbncm1_tcin_hdmi_tcout"]
        self.assertEqual(r40c["round"], 40)
        self.assertEqual(r40c["r40_mode"], "vmcbncm1_tcin_hdmi_tcout")
        self.assertEqual(r40c["crashes"], 0)
        self.assertEqual(r40c["emmc_write_count"], 0)
        self.assertTrue(r40c["gpe0_readback"]["skipped_stock_fx3_mode"])
        self.assertEqual(r40c["r40_telemetry"]["vmcbncm1_rc"], 0)
        c = r40c["r40_telemetry"]["vmcbncm1_tcin_hdmi"]
        self.assertEqual(c["adapter_model"], "VMC-BNCM1")
        self.assertEqual(c["part_no"], "A-5051-506-A")
        self.assertEqual(c["cable_len_cm"], 20)
        self.assertEqual(c["body_usb_port"], "Multi_Micro_USB")
        self.assertEqual(c["pre_10s_9999ms_rc"], -11)
        self.assertEqual(c["body_movie_preset_freerun_10s_rc"], 0)
        self.assertEqual(c["ext_lk_locked"], 1)
        self.assertEqual(c["holdover_active"], 1)
        self.assertEqual(c["release_on_sq_locked"], 0)
        self.assertEqual(c["release_on_tcmake_regen_locked"], 0)
        self.assertEqual(c["release_on_tcrun_recrun_locked"], 0)
        self.assertEqual(c["release_on_tcpreset_edit_locked"], 0)
        self.assertEqual(c["r40c_ok"], 1)

    def test_20_round40_r40c_xlrh1_usb_block_bnc_tcout_block_and_hdmi_digital_tcout(self) -> None:
        data = json.loads((ROUND40_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        c = data["runs"]["r40c_vmcbncm1_tcin_hdmi_tcout"]["r40_telemetry"]["vmcbncm1_tcin_hdmi"]
        self.assertEqual(c["xlrh1_handle_usb_reject_rc"], -19)
        self.assertEqual(c["bnc_tcout_reject_rc"], -95)
        self.assertEqual(c["bnc_tcout_tx_count"], 0)
        self.assertEqual(c["hdmi_type_a_movie_tcout_rc"], 0)
        self.assertEqual(c["hdmi_movie_tcout_active"], 1)
        self.assertEqual(c["hdmi_sq_tcout_reject_rc"], -95)
        self.assertEqual(c["hdmi_sq_tcout_active"], 0)
        self.assertEqual(c["hdmi_sq_tcout_disabled"], 1)
        self.assertEqual(c["p2_write_blocked_rc"], -30)

    def test_21_round40_r40c_16_surfaces_h0_eq_h3_zero_drift_and_dlopen_ok(self) -> None:
        data = json.loads((ROUND40_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        c = data["runs"]["r40c_vmcbncm1_tcin_hdmi_tcout"]["r40_telemetry"]["vmcbncm1_tcin_hdmi"]
        self.assertEqual(c["dlopen_ok"], 1)
        self.assertEqual(c["surfaces_verified"], 16)
        self.assertEqual(c["surfaces_h0_eq_h3"], 16)
        self.assertEqual(c["drift_bits"], 0)
        self.assertEqual(c["emmc_write_count"], 0)

    def test_22_round40_stage_b_bridge_mechanisms_and_bench_boundaries(self) -> None:
        data = json.loads((ROUND40_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        mech = data["realhw_mechanisms_verified"]
        self.assertEqual(mech["big6_6tile_home_lower_left_aperture_nd_and_zero_end_actuator_init"]["r40_init_ok"], 1)
        self.assertEqual(mech["big6_home_zero_end_actuator_stage_b_bridge"]["r40_bridge_ok"], 1)
        self.assertEqual(mech["slot1_only_camset_10slot_dualmedia_path_split_and_mr_fx3a_firewall"]["r40b_ok"], 1)
        self.assertEqual(mech["vmc_bncm1_body_only_tcin_10s_holdover_and_hdmi_digital_tcout"]["r40c_ok"], 1)

        br = data["runs"]["r40a_big6_home_noend_schinese"]["r40_telemetry"]["stage_b_bridge"]
        for key in (
            "faithful",
            "p12_wlan",
            "wf12_00342260_immune",
            "p10_keymap",
            "p4_nd_clear",
            "p11_xlr_h1",
            "big6_home_6tile_no_end",
            "lower_left_aperture_nd_toggle",
            "camset_slot1_dualmedia_split",
            "vmcbncm1_body_tcin_hdmi_tcout",
        ):
            self.assertEqual(br[key], 1, f"Expected stage_b_bridge[{key}]==1")
        self.assertEqual(br["round"], 40)
        self.assertEqual(br["nop_count"], 0)
        self.assertEqual(br["emmc_write_count"], 0)
        self.assertEqual(len(data["unexecuted_physical_camera_bench_boundaries"]), 3)

    def test_23_round40_r40a_camset_tc_bridge_consistent_with_r40b_and_r40c(self) -> None:
        data = json.loads((ROUND40_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        br_ct = data["runs"]["r40a_big6_home_noend_schinese"]["r40_telemetry"]["camset_tc_bridge"]
        r40b = data["runs"]["r40b_camset_slot1_dualmedia_split"]["r40_telemetry"]["camset_slot1_split"]
        r40c = data["runs"]["r40c_vmcbncm1_tcin_hdmi_tcout"]["r40_telemetry"]["vmcbncm1_tcin_hdmi"]
        self.assertEqual(br_ct["camset_slot1_only"], 1)
        self.assertEqual(br_ct["camset_max_profiles"], 10)
        self.assertEqual(br_ct["sd_camset_dir"], r40b["sd_camset_dir"])
        self.assertEqual(br_ct["cfx_camset_dir"], r40b["cfx_camset_dir"])
        self.assertEqual(br_ct["slot2_reject_rc"], r40b["slot2_save_reject_rc"])
        self.assertEqual(br_ct["save_11th_reject_rc"], r40b["sd_save_11th_reject_rc"])
        self.assertEqual(br_ct["mr_mode_lock_rc"], r40b["mr_mode_save_reject_rc"])
        self.assertEqual(br_ct["cross_model_dat_reject_rc"], r40b["fx3a_dat_reject_rc"])
        self.assertEqual(br_ct["camset_overlay_dir"], r40b["stageb_overlay_dir"])
        self.assertEqual(br_ct["vmcbncm1_body_tcin_only"], 1)
        self.assertEqual(br_ct["ext_lk_holdover_min_ms"], 10000)
        self.assertEqual(br_ct["handle_usb_reject_rc"], r40c["xlrh1_handle_usb_reject_rc"])
        self.assertEqual(br_ct["bnc_tcout_reject_rc"], r40c["bnc_tcout_reject_rc"])
        self.assertEqual(br_ct["hdmi_tcout_movie_only"], r40c["hdmi_movie_tcout_active"])
        self.assertEqual(br_ct["camset_split_ok"], 1)
        self.assertEqual(br_ct["vmcbncm1_tc_ok"], 1)
        self.assertEqual(br_ct["p2_setting_writes"], 0)
        self.assertEqual(br_ct["emmc_write_count"], 0)

    def test_24_round40_readme_sanitization_and_no_tmp_or_binary_residue(self) -> None:
        closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn("2026-11-15-round40-realhw-big6-noend-camset-slot1-vmcbncm1-tcin-qemu", closure_readme)
        self.assertIn("`24` New Round 40 Dual-Mode Unit Tests (`546` Total)", closure_readme)
        r40_readme = (ROUND40_REPORT_DIR / "README.md").read_text(encoding="utf-8")
        for tok in (
            "40th Milestone QEMU Rehearsal",
            "BIG6",
            "Home (Lower Left)",
            "e_nd_actuator_tx_count=0",
            "/PRIVATE/SONY/SETTING/FX3/CAMSET/",
            "/SONY/SETTING/FX3/CAMSET/",
            "/tmp/fx6_camset_overlay",
            "VMC-BNCM1",
            "A-5051-506-A",
            "EXT-LK",
            "r40a-big6-noend-schinese",
            "r40b-camset-slot1-split",
            "r40c-vmcbncm1-tcin-hdmi",
        ):
            self.assertIn(tok, r40_readme)
        for forbidden in ("/Users/", "/Volumes/KAFU2T", "/private/tmp"):
            self.assertNotIn(forbidden, r40_readme)
        for folder in (CLOSURE_DIR, ROUND40_REPORT_DIR):
            for p in folder.rglob("*"):
                if p.is_file():
                    self.assertNotIn(p.suffix, {".cpio", ".so", ".o", ".img", ".qcow2", ".pyc"})


if __name__ == "__main__":
    unittest.main()
