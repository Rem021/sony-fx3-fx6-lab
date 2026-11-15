#!/usr/bin/env python3
"""Offline dual-mode unit tests for FX6-on-FX3 Round 41 (Live FX3 7.02 QEMU Rehearsal)."""
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
ROUND41_REPORT_DIR = (
    REPO_ROOT
    / "reports"
    / "2026-11-15-round41-realhw-desqueeze-165x-focusmap-simult-shocklesswb-qemu"
)
ROUND41_ASSETS_DIR = ROUND41_REPORT_DIR / "assets"


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


class TestRound41RealHwDesqueezeFocusMapSimultShocklessWb(unittest.TestCase):
    EXPECTED_RUN_KEYS = (
        "r41a_desqueeze_165x_4locks_big6_schinese",
        "r41b_external_focusmap_150fps_cutoff",
        "r41c_simult_autoswitch_shocklesswb",
    )

    def test_01_round41_c_and_python_source_contracts(self) -> None:
        shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")

        self.assertIn("#if FX6_ROUND >= 41", shim_src)
        for token in (
            "FX6_R41_DESQUEEZE_BRIDGE",
            "FX6_R41_FOCUSMAP_SIMULT_WB_BRIDGE",
            "FX6_R41_LANG_TELEMETRY",
            "FX6_STAGE_B_R41_BRIDGE",
            "round41_realhw_desqueeze_focusmap_simult_shocklesswb=1",
        ):
            self.assertIn(token, shim_src)

        for token in (
            "r41_desqueeze_set_ratio",
            "r41_desqueeze_mutate_camera_param",
            "r41_desqueeze_eval_effective_scale",
            "setup_r41_desqueeze_165x_4locks_probe",
            "r41_fx3_inbody_focusmap_menu_toggle",
            "r41_mc_external_focusmap_eval",
            "r41_fx6_ref_focusmap_fps_gate",
            "run_r41_focusmap_150fps_probe",
            "r41_simult_eval_dual_slot",
            "r41_shockless_wb_eval_transition",
            "run_r41_simult_shocklesswb_probe",
            "--r41-focusmap-150fps",
            "--r41-simult-shocklesswb",
            "/etc/fx6_stage_r41",
            "FX6_R41_DESQUEEZE_165X_INIT",
            "FX6_R41_EXTERNAL_FOCUSMAP_150FPS",
            "FX6_R41_SIMULT_SHOCKLESSWB",
        ):
            self.assertIn(token, verify_src)

        for token in (
            "enable_r41",
            "r41_mode",
            "--r41-mode",
            "desqueeze_165x_4locks_big6",
            "external_focusmap_150fps_cutoff",
            "simult_autoswitch_shocklesswb",
            "etc/fx6_stage_r41",
            "FX6_R41_FOCUSMAP_150FPS_EXIT",
            "FX6_R41_SIMULT_SHOCKLESSWB_EXIT",
            '"r41_telemetry"',
            "choices=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46]",
        ):
            self.assertIn(token, runner_src)

    def test_02_round41_native_verify_c_compiles_with_zig_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r41_verc", "build_and_run_round.py")
        if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1" and not runner.ZIG.is_file():
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertTrue(runner.ZIG.is_file(), f"Missing zig compiler at {runner.ZIG}")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            cache_dir = tmp_dir / "zig-cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            for clean_flag in ("0", "1"):
                out_bin = tmp_dir / f"fx6-stage-a-verify-r41-{clean_flag}"
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

    def test_03_round41_build_binaries_compiles_shim_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r41_shimc", "build_and_run_round.py")
        if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1" and not runner.ZIG.is_file():
            self.skipTest("Clean-room fallback without local zig binary")
        with tempfile.TemporaryDirectory() as tmp:
            for clean_flag in ("0", "1"):
                work = pathlib.Path(tmp) / f"shim_{clean_flag}"
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                    launcher_b, shim_b, meta = runner.build_binaries(
                        work,
                        fx6_round=41,
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

    def test_04_round41_extract_milestones_r41a_desqueeze_and_bridge(self) -> None:
        runner = _load_closure_module("fx6_brr_r41_msa", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R41_DESQUEEZE_165X_INIT ratios_verified=5 off_centi=100 r13x_centi=130 r20x_centi=200 r15x_centi=150 r16x_actual_centi=165 cinemascope_aspect=2.39:1 invalid_ratio_reject_rc=-22 focus_mode_locked_mf=1 focus_area_locked_wide=1 steadyshot_locked_off=1 face_priority_metering_locked_off=1 af_mut_reject_rc=-16 area_mut_reject_rc=-16 ibis_mut_reject_rc=-16 face_mut_reject_rc=-16 hard_locks_enforced=4 unlocked_when_off_ok=1 raw_output_on_suppressed=1 hdmi_only_suppressed=1 hdmi_only_forces_info_off=1 log_shooting_off_suppressed=1 remote_shooting_suppressed=1 photo_mode_suppressed=1 appfw_present=1 shim_present=1 emmc_write_count=0 r41_init_ok=1 verify_us=575584",
                "FX6_R41_DESQUEEZE_BRIDGE ratios_supported=5 ratio_1_6x_centi=165 cinemascope_target=2.39:1 hard_locks_enforced=4 focus_mode_lock=MF focus_area_lock=Wide steadyshot_lock=Off face_priority_metering_lock=Off raw_output_suppress=1 hdmi_only_forces_info_off=1 log_off_suppress=1 remote_shooting_suppress=1 desqueeze_state_ok=1 emmc_write_count=0 r41_bridge_ok=1",
                "FX6_R41_FOCUSMAP_SIMULT_WB_BRIDGE inbody_focusmap_reject_rc=-95 external_mc_only=1 focusmap_cutoff_fps=150 sq_200_240_reject_rc=-22 fx3_low_fps_1_to_6_allowed=1 adapter_nonpdaf_reject_rc=-19 playback_reject_rc=-16 simult_autoswitch_on_single_cont=1 simult_autoswitch_off_halt_rc=-28 shockless_wb_fps_max=240 ctemp_kelvin_grid_transition_frames=0 focusmap_mc_ok=1 simult_autoswitch_ok=1 shockless_wb_ok=1 p2_setting_writes=0 emmc_write_count=0",
                "FX6_STAGE_B_R41_BRIDGE round=41 faithful=1 nop_count=0 p12_wlan=1 wf12_00342260_immune=1 p10_keymap=1 p4_nd_clear=1 p11_xlr_h1=1 lang=schinese bk4_lang=0x19 enum=0x2b45_CHINESE_SIMPLIFIED font_bank=23 str_bank=19 desqueeze_165x_4locks=1 external_mc_focusmap_150fps=1 simult_autoswitch_single_cont=1 shockless_wb_kelvin_grid_bypass=1 emmc_write_count=0",
                "FX6_R41_LANG_TELEMETRY reason=pump lang=schinese bk4_lang_id=0x02cf019c bk4_lang_val=0x19 gpe_fb=0 desqueeze_state_ok=1 focusmap_mc_ok=1 simult_autoswitch_ok=1 shockless_wb_ok=1 r41_bridge_ok=1 round41_realhw_desqueeze_focusmap_simult_shocklesswb=1 emmc_write_count=0 subst_color=0 subst_image=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        r41 = ms["r41_telemetry"]
        self.assertIsNotNone(r41)
        self.assertEqual(r41["desqueeze_165x_init"]["ratios_verified"], 5)
        self.assertEqual(r41["desqueeze_165x_init"]["r16x_actual_centi"], 165)
        self.assertEqual(r41["desqueeze_165x_init"]["hard_locks_enforced"], 4)
        self.assertEqual(r41["desqueeze_165x_init"]["r41_init_ok"], 1)
        self.assertEqual(r41["desqueeze_bridge"]["r41_bridge_ok"], 1)
        self.assertEqual(r41["focusmap_simult_wb_bridge"]["focusmap_cutoff_fps"], 150)
        self.assertEqual(r41["stage_b_bridge"]["round"], 41)
        self.assertEqual(r41["lang_telemetry"]["gpe_fb"], 0)

    def test_05_round41_extract_milestones_r41b_external_focusmap_150fps(self) -> None:
        runner = _load_closure_module("fx6_brr_r41_msb", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R41_EXTERNAL_FOCUSMAP_150FPS body_model=ILME-FX3 fw_ver=7.02 external_app=Monitor_and_Control inbody_menu_toggle_reject_rc=-95 stageb_local_overlay_guard_rc=-95 local_lcd_overlay_draws=0 fps_1_sq_rc=0 fx3_1fps_allowed=1 fps_6_sq_rc=0 fx3_6fps_allowed=1 fx6_ref_6fps_reject_rc=-22 fps_24_rc=0 fps_60_rc=0 fps_120_rc=0 fps_149_boundary_rc=0 sub_150fps_stream_active=1 fps_150_cutoff_rc=-22 sq_200fps_reject_rc=-22 sq_240fps_reject_rc=-22 sq_200fps_stream_active=0 sq_240fps_stream_active=0 mount_adapter_reject_rc=-19 non_pdaf_lens_reject_rc=-19 no_lens_reject_rc=-19 playback_reject_rc=-16 p2_write_blocked_rc=-30 p2_setting_sha256_match=1 appfw_ok=1 shim_elf_ok=1 emmc_write_count=0 r41b_ok=1 verify_us=589696",
                "FX6_R41_FOCUSMAP_RC=0",
                "FX6_R41_FOCUSMAP_150FPS_EXIT rc=0 emmc_write_count=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        r41 = ms["r41_telemetry"]
        self.assertIsNotNone(r41)
        self.assertEqual(r41["focusmap_rc"], 0)
        b = r41["external_focusmap_150fps"]
        self.assertEqual(b["inbody_menu_toggle_reject_rc"], -95)
        self.assertEqual(b["fx3_1fps_allowed"], 1)
        self.assertEqual(b["fx3_6fps_allowed"], 1)
        self.assertEqual(b["fx6_ref_6fps_reject_rc"], -22)
        self.assertEqual(b["fps_150_cutoff_rc"], -22)
        self.assertEqual(b["sq_240fps_reject_rc"], -22)
        self.assertEqual(b["mount_adapter_reject_rc"], -19)
        self.assertEqual(b["playback_reject_rc"], -16)
        self.assertEqual(b["r41b_ok"], 1)

    def test_06_round41_extract_milestones_r41c_simult_shocklesswb(self) -> None:
        runner = _load_closure_module("fx6_brr_r41_msc", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R41_SIMULT_SHOCKLESSWB dual_initial_mask=3 autoswitch_on_slot1_full_rc=0 single_slot_cont_active=1 cont_slot_mask=2 cont_dropped_frames=0 card_swap_dual_resume_rc=0 resumed_slot_mask=3 dual_slot_resumed=1 both_slots_full_rc=-28 autoswitch_off_slot1_full_rc=-28 autoswitch_off_halted=1 autoswitch_off_slot_mask=0 fps_sweep_verified=6 preset_24p_1_frames=12 preset_24p_2_frames=24 preset_24p_3_frames=48 preset_240fps_3_frames=480 invalid_shockless_mode_rc=-22 ctemp_kelvin_transition_frames=0 ctemp_kelvin_immediate_bypass=1 ab_gm_grid_transition_frames=0 ab_gm_grid_immediate_bypass=1 p2_write_blocked_rc=-30 dlopen_ok=1 surfaces_verified=16 surfaces_h0_eq_h3=16 drift_bits=0 emmc_write_count=0 r41c_ok=1 verify_us=4466",
                "FX6_R41_SIMULT_WB_RC=0",
                "FX6_R41_SIMULT_SHOCKLESSWB_EXIT rc=0 emmc_write_count=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        r41 = ms["r41_telemetry"]
        self.assertIsNotNone(r41)
        self.assertEqual(r41["simult_wb_rc"], 0)
        c = r41["simult_shocklesswb"]
        self.assertEqual(c["dual_initial_mask"], 3)
        self.assertEqual(c["single_slot_cont_active"], 1)
        self.assertEqual(c["dual_slot_resumed"], 1)
        self.assertEqual(c["autoswitch_off_slot1_full_rc"], -28)
        self.assertEqual(c["ctemp_kelvin_transition_frames"], 0)
        self.assertEqual(c["ab_gm_grid_transition_frames"], 0)
        self.assertEqual(c["surfaces_h0_eq_h3"], 16)
        self.assertEqual(c["r41c_ok"], 1)

    def test_07_round41_stage_a_overlay_desqueeze_165x_4locks_big6_mocked_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r41_ovl_a", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            parent_cpio, fp, fv, fb, fake_run, jit_meta = _build_mock_cpio_and_fakes(runner, tmp_dir)
            for clean_flag in ("0", "1"):
                work = tmp_dir / f"r41_a_{clean_flag}"
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
                        enable_r41=True, r41_mode="desqueeze_165x_4locks_big6",
                        sd_manifest_mode="valid", lang="schinese", shim_bytes=b"SHIM",
                    )
                init_out = rep["init"].decode("utf-8")
                self.assertNotIn("--r41-focusmap-150fps", init_out)
                self.assertNotIn("--r41-simult-shocklesswb", init_out)
                self.assertIn("--sd-gate", init_out)
                self.assertIn("etc/fx6_stage_r41", add)
                self.assertIn("r41_mode=desqueeze_165x_4locks_big6", add["etc/fx6_stage_r41"][0].decode("utf-8"))
                self.assertTrue(meta["r41_enabled"])
                self.assertEqual(meta["r41"]["r41_mode"], "desqueeze_165x_4locks_big6")
                self.assertEqual(meta["r41"]["desqueeze_1_6x_actual_factor"], 1.65)
                self.assertEqual(meta["r41"]["desqueeze_1_6x_target_aspect"], "2.39:1")
                self.assertEqual(len(meta["r41"]["desqueeze_ratios"]), 5)
                self.assertEqual(len(meta["r41"]["desqueeze_hard_locked_settings"]), 4)
                self.assertTrue(meta["r41"]["hdmi_only_forces_info_display_off"])

    def test_08_round41_stage_a_overlay_external_focusmap_150fps_cutoff_mocked_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r41_ovl_b", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            parent_cpio, fp, fv, fb, fake_run, jit_meta = _build_mock_cpio_and_fakes(runner, tmp_dir)
            for clean_flag in ("0", "1"):
                work = tmp_dir / f"r41_b_{clean_flag}"
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
                        enable_r41=True, r41_mode="external_focusmap_150fps_cutoff",
                        sd_manifest_mode="valid", lang="en", shim_bytes=b"SHIM",
                    )
                init_out = rep["init"].decode("utf-8")
                self.assertIn("/usr/bin/fx6-stage-a-verify --r41-focusmap-150fps", init_out)
                self.assertIn("FX6_R41_FOCUSMAP_150FPS_EXIT", init_out)
                self.assertEqual(meta["r41"]["r41_mode"], "external_focusmap_150fps_cutoff")
                self.assertFalse(meta["r41"]["inbody_focusmap_menu_present"])
                self.assertEqual(meta["r41"]["inbody_focusmap_reject_rc"], -95)
                self.assertEqual(meta["r41"]["external_focusmap_cutoff_fps"], 150)
                self.assertTrue(meta["r41"]["fx3_focusmap_low_fps_1_to_6_allowed"])
                self.assertEqual(meta["r41"]["focusmap_adapter_nonpdaf_reject_rc"], -19)
                self.assertEqual(meta["r41"]["focusmap_playback_reject_rc"], -16)

    def test_09_round41_stage_a_overlay_simult_autoswitch_shocklesswb_mocked_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r41_ovl_c", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            parent_cpio, fp, fv, fb, fake_run, jit_meta = _build_mock_cpio_and_fakes(runner, tmp_dir)
            for clean_flag in ("0", "1"):
                work = tmp_dir / f"r41_c_{clean_flag}"
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
                        enable_r41=True, r41_mode="simult_autoswitch_shocklesswb",
                        sd_manifest_mode="valid", lang="en", shim_bytes=b"SHIM",
                    )
                init_out = rep["init"].decode("utf-8")
                self.assertIn("/usr/bin/fx6-stage-a-verify --r41-simult-shocklesswb", init_out)
                self.assertIn("FX6_R41_SIMULT_SHOCKLESSWB_EXIT", init_out)
                self.assertEqual(meta["r41"]["r41_mode"], "simult_autoswitch_shocklesswb")
                self.assertTrue(meta["r41"]["simult_autoswitch_on_single_card_continuation"])
                self.assertEqual(meta["r41"]["simult_autoswitch_off_strict_parity_halt_rc"], -28)
                self.assertEqual(meta["r41"]["shockless_wb_ctemp_kelvin_transition_frames"], 0)
                self.assertEqual(meta["r41"]["shockless_wb_ab_gm_grid_transition_frames"], 0)

    def test_10_round41_stage_a_overlay_rejects_invalid_r41_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r41_badmode", "build_and_run_round.py")
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
                        tmp_dir / "bad_r41", parent_cpio, b"BK4NTSC",
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
                        enable_r41=True, r41_mode="invalid_r41_mode",
                        lang="schinese", shim_bytes=b"SHIM",
                    )

    def test_11_round41_summary_json_schema_sanitization_and_audit_flags(self) -> None:
        summary_path = ROUND41_REPORT_DIR / "summary.json"
        self.assertTrue(summary_path.is_file())
        raw = summary_path.read_text(encoding="utf-8")
        for forbidden in ("/Users/", "/Volumes/KAFU2T", "/private/tmp"):
            self.assertNotIn(forbidden, raw)
        data = json.loads(raw)
        self.assertEqual(data["schema"], "fx6-on-fx3-round41-realhw-desqueeze-165x-focusmap-simult-shocklesswb-qemu-v1")
        self.assertEqual(data["round"], 41)
        self.assertIn("Linux version 4.9.337-scel+", data["kernel_version"])
        self.assertEqual(set(data["runs"].keys()), set(self.EXPECTED_RUN_KEYS))
        audit = data["r41_realhw_desqueeze_focusmap_simult_shocklesswb_audit"]
        self.assertEqual(audit["round"], 41)
        self.assertEqual(audit["total_runs"], 3)
        for k in (
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "r41a_desqueeze_5ratios_165x_and_4hardlocks_verified",
            "r41a_hdmi_raw_clean_hdmi_log_remote_suppression_verified",
            "r41a_stageb_big6_sid_0a_over_340k_pixels_verified",
            "r41b_inbody_focusmap_rejected_and_sub150fps_1fps_6fps_verified",
            "r41b_150fps_200_240fps_cutoff_and_adapter_playback_blocks_verified",
            "r41c_simult_autoswitch_continuation_and_cardswap_resume_verified",
            "r41c_shockless_wb_preset_vs_kelvin_grid_0frame_and_16_h0_eq_h3_verified",
        ):
            self.assertTrue(audit[k], f"Audit flag {k} must be True")

    def test_12_round41_r41a_desqueeze_5ratios_165x_and_4hardlocks(self) -> None:
        data = json.loads((ROUND41_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        init = data["runs"]["r41a_desqueeze_165x_4locks_big6_schinese"]["r41_telemetry"]["desqueeze_165x_init"]
        self.assertEqual(init["ratios_verified"], 5)
        self.assertEqual(init["off_centi"], 100)
        self.assertEqual(init["r13x_centi"], 130)
        self.assertEqual(init["r20x_centi"], 200)
        self.assertEqual(init["r15x_centi"], 150)
        self.assertEqual(init["r16x_actual_centi"], 165)
        self.assertEqual(init["cinemascope_aspect"], "2.39:1")
        self.assertEqual(init["invalid_ratio_reject_rc"], -22)
        self.assertEqual(init["focus_mode_locked_mf"], 1)
        self.assertEqual(init["focus_area_locked_wide"], 1)
        self.assertEqual(init["steadyshot_locked_off"], 1)
        self.assertEqual(init["face_priority_metering_locked_off"], 1)
        self.assertEqual(init["af_mut_reject_rc"], -16)
        self.assertEqual(init["area_mut_reject_rc"], -16)
        self.assertEqual(init["ibis_mut_reject_rc"], -16)
        self.assertEqual(init["face_mut_reject_rc"], -16)
        self.assertEqual(init["hard_locks_enforced"], 4)
        self.assertEqual(init["unlocked_when_off_ok"], 1)

    def test_13_round41_r41a_hdmi_raw_clean_hdmi_log_remote_suppression(self) -> None:
        data = json.loads((ROUND41_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        init = data["runs"]["r41a_desqueeze_165x_4locks_big6_schinese"]["r41_telemetry"]["desqueeze_165x_init"]
        self.assertEqual(init["raw_output_on_suppressed"], 1)
        self.assertEqual(init["hdmi_only_suppressed"], 1)
        self.assertEqual(init["hdmi_only_forces_info_off"], 1)
        self.assertEqual(init["log_shooting_off_suppressed"], 1)
        self.assertEqual(init["remote_shooting_suppressed"], 1)
        self.assertEqual(init["photo_mode_suppressed"], 1)
        self.assertEqual(init["emmc_write_count"], 0)
        self.assertEqual(init["r41_init_ok"], 1)

    def test_14_round41_r41a_bridge_telemetry_verified(self) -> None:
        data = json.loads((ROUND41_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        telem = data["runs"]["r41a_desqueeze_165x_4locks_big6_schinese"]["r41_telemetry"]
        init = telem["desqueeze_165x_init"]
        br = telem["desqueeze_bridge"]
        self.assertEqual(init["appfw_present"], 1)
        self.assertEqual(init["shim_present"], 1)
        self.assertEqual(br["ratios_supported"], 5)
        self.assertEqual(br["ratio_1_6x_centi"], 165)
        self.assertEqual(br["cinemascope_target"], "2.39:1")
        self.assertEqual(br["hard_locks_enforced"], 4)
        self.assertEqual(br["focus_mode_lock"], "MF")
        self.assertEqual(br["focus_area_lock"], "Wide")
        self.assertEqual(br["steadyshot_lock"], "Off")
        self.assertEqual(br["face_priority_metering_lock"], "Off")
        self.assertEqual(br["raw_output_suppress"], 1)
        self.assertEqual(br["hdmi_only_forces_info_off"], 1)
        self.assertEqual(br["log_off_suppress"], 1)
        self.assertEqual(br["remote_shooting_suppress"], 1)
        self.assertEqual(br["desqueeze_state_ok"], 1)
        self.assertEqual(br["r41_bridge_ok"], 1)

    def test_15_round41_r41a_stage_b_13_sha256_and_big6_render_invariants(self) -> None:
        data = json.loads((ROUND41_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        r41a = data["runs"]["r41a_desqueeze_165x_4locks_big6_schinese"]
        self.assertEqual(r41a["round"], 41)
        self.assertEqual(r41a["r41_mode"], "desqueeze_165x_4locks_big6")
        self.assertEqual(r41a["target_presenter"], "31procam_big6_menu_home_presenter")
        self.assertEqual(r41a["target_sid"], "0x0a")
        self.assertEqual(r41a["nop_count"], 0)
        self.assertEqual(r41a["crashes"], 0)
        self.assertEqual(r41a["emmc_write_count"], 0)
        self.assertGreaterEqual(r41a["total_threads_seen"], 160)
        self.assertEqual(r41a["faithful_invariants"]["FX6_NATIVE_FAITHFUL"], 1)
        self.assertEqual(r41a["stage_b"]["manifest_count"], 13)
        self.assertEqual(len(r41a["stage_b"]["manifest_items"]), 13)
        for item in r41a["stage_b"]["manifest_items"]:
            self.assertEqual(len(item["sha256"]), 64)
            int(item["sha256"], 16)
        lt = r41a["r41_telemetry"]["lang_telemetry"]
        self.assertEqual(lt["gpe_fb"], 0)
        self.assertEqual(lt["subst_color"], 0)
        self.assertEqual(lt["subst_image"], 0)
        self.assertEqual(lt["r41_bridge_ok"], 1)
        self.assertEqual(lt["round41_realhw_desqueeze_focusmap_simult_shocklesswb"], 1)
        self.assertGreater(r41a["gpe0_readback"]["nonzero_pixels"], 340000)

    def test_16_round41_r41a_png_receipts_under_28kib_and_dimensions(self) -> None:
        data = json.loads((ROUND41_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        exports = data["runs"]["r41a_desqueeze_165x_4locks_big6_schinese"]["png_exports"]
        for key in ("alpha_png", "composited_png"):
            p = REPO_ROOT / exports[key]["path"]
            self.assertTrue(p.is_file(), f"Missing Round 41 PNG: {p}")
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

    def test_17_round41_r41b_external_only_focusmap_sub150fps_and_fx3_sub6fps_allowance(self) -> None:
        data = json.loads((ROUND41_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        r41b = data["runs"]["r41b_external_focusmap_150fps_cutoff"]
        self.assertEqual(r41b["round"], 41)
        self.assertEqual(r41b["r41_mode"], "external_focusmap_150fps_cutoff")
        self.assertEqual(r41b["crashes"], 0)
        self.assertEqual(r41b["emmc_write_count"], 0)
        self.assertTrue(r41b["gpe0_readback"]["skipped_stock_fx3_mode"])
        self.assertEqual(r41b["r41_telemetry"]["focusmap_rc"], 0)
        b = r41b["r41_telemetry"]["external_focusmap_150fps"]
        self.assertEqual(b["body_model"], "ILME-FX3")
        self.assertEqual(b["fw_ver"], "7.02")
        self.assertEqual(b["external_app"], "Monitor_and_Control")
        self.assertEqual(b["inbody_menu_toggle_reject_rc"], -95)
        self.assertEqual(b["stageb_local_overlay_guard_rc"], -95)
        self.assertEqual(b["local_lcd_overlay_draws"], 0)
        self.assertEqual(b["fps_1_sq_rc"], 0)
        self.assertEqual(b["fx3_1fps_allowed"], 1)
        self.assertEqual(b["fps_6_sq_rc"], 0)
        self.assertEqual(b["fx3_6fps_allowed"], 1)
        self.assertEqual(b["fx6_ref_6fps_reject_rc"], -22)
        self.assertEqual(b["fps_24_rc"], 0)
        self.assertEqual(b["fps_60_rc"], 0)
        self.assertEqual(b["fps_120_rc"], 0)
        self.assertEqual(b["fps_149_boundary_rc"], 0)
        self.assertEqual(b["sub_150fps_stream_active"], 1)
        self.assertEqual(b["r41b_ok"], 1)

    def test_18_round41_r41b_150fps_200_240fps_cutoff_and_lens_playback_guards(self) -> None:
        data = json.loads((ROUND41_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        b = data["runs"]["r41b_external_focusmap_150fps_cutoff"]["r41_telemetry"]["external_focusmap_150fps"]
        self.assertEqual(b["fps_150_cutoff_rc"], -22)
        self.assertEqual(b["sq_200fps_reject_rc"], -22)
        self.assertEqual(b["sq_240fps_reject_rc"], -22)
        self.assertEqual(b["sq_200fps_stream_active"], 0)
        self.assertEqual(b["sq_240fps_stream_active"], 0)
        self.assertEqual(b["mount_adapter_reject_rc"], -19)
        self.assertEqual(b["non_pdaf_lens_reject_rc"], -19)
        self.assertEqual(b["no_lens_reject_rc"], -19)
        self.assertEqual(b["playback_reject_rc"], -16)
        self.assertEqual(b["p2_write_blocked_rc"], -30)
        self.assertEqual(b["p2_setting_sha256_match"], 1)
        self.assertEqual(b["appfw_ok"], 1)
        self.assertEqual(b["shim_elf_ok"], 1)
        self.assertEqual(b["emmc_write_count"], 0)

    def test_19_round41_r41c_simult_autoswitch_continuation_vs_off_parity_halt(self) -> None:
        data = json.loads((ROUND41_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        r41c = data["runs"]["r41c_simult_autoswitch_shocklesswb"]
        self.assertEqual(r41c["round"], 41)
        self.assertEqual(r41c["r41_mode"], "simult_autoswitch_shocklesswb")
        self.assertEqual(r41c["crashes"], 0)
        self.assertEqual(r41c["emmc_write_count"], 0)
        self.assertTrue(r41c["gpe0_readback"]["skipped_stock_fx3_mode"])
        self.assertEqual(r41c["r41_telemetry"]["simult_wb_rc"], 0)
        c = r41c["r41_telemetry"]["simult_shocklesswb"]
        self.assertEqual(c["dual_initial_mask"], 3)
        self.assertEqual(c["autoswitch_on_slot1_full_rc"], 0)
        self.assertEqual(c["single_slot_cont_active"], 1)
        self.assertEqual(c["cont_slot_mask"], 2)
        self.assertEqual(c["cont_dropped_frames"], 0)
        self.assertEqual(c["card_swap_dual_resume_rc"], 0)
        self.assertEqual(c["resumed_slot_mask"], 3)
        self.assertEqual(c["dual_slot_resumed"], 1)
        self.assertEqual(c["both_slots_full_rc"], -28)
        self.assertEqual(c["autoswitch_off_slot1_full_rc"], -28)
        self.assertEqual(c["autoswitch_off_halted"], 1)
        self.assertEqual(c["autoswitch_off_slot_mask"], 0)
        self.assertEqual(c["r41c_ok"], 1)

    def test_20_round41_r41c_shockless_wb_preset_scaling_vs_kelvin_grid_0frame_bypass(self) -> None:
        data = json.loads((ROUND41_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        c = data["runs"]["r41c_simult_autoswitch_shocklesswb"]["r41_telemetry"]["simult_shocklesswb"]
        self.assertEqual(c["fps_sweep_verified"], 6)
        self.assertEqual(c["preset_24p_1_frames"], 12)
        self.assertEqual(c["preset_24p_2_frames"], 24)
        self.assertEqual(c["preset_24p_3_frames"], 48)
        self.assertEqual(c["preset_240fps_3_frames"], 480)
        self.assertEqual(c["invalid_shockless_mode_rc"], -22)
        self.assertEqual(c["ctemp_kelvin_transition_frames"], 0)
        self.assertEqual(c["ctemp_kelvin_immediate_bypass"], 1)
        self.assertEqual(c["ab_gm_grid_transition_frames"], 0)
        self.assertEqual(c["ab_gm_grid_immediate_bypass"], 1)
        self.assertEqual(c["p2_write_blocked_rc"], -30)

    def test_21_round41_r41c_16_surfaces_h0_eq_h3_zero_drift_and_dlopen_ok(self) -> None:
        data = json.loads((ROUND41_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        c = data["runs"]["r41c_simult_autoswitch_shocklesswb"]["r41_telemetry"]["simult_shocklesswb"]
        self.assertEqual(c["dlopen_ok"], 1)
        self.assertEqual(c["surfaces_verified"], 16)
        self.assertEqual(c["surfaces_h0_eq_h3"], 16)
        self.assertEqual(c["drift_bits"], 0)
        self.assertEqual(c["emmc_write_count"], 0)

    def test_22_round41_stage_b_bridge_mechanisms_and_bench_boundaries(self) -> None:
        data = json.loads((ROUND41_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        mech = data["realhw_mechanisms_verified"]
        self.assertEqual(mech["desqueeze_display_5ratio_165x_4hardlocks_and_hdmi_raw_bypass_init"]["r41_init_ok"], 1)
        self.assertEqual(mech["desqueeze_display_stage_b_bridge"]["r41_bridge_ok"], 1)
        self.assertEqual(mech["external_only_mc_focus_map_150fps_cutoff_and_fx3_sub6fps_allowance"]["r41b_ok"], 1)
        self.assertEqual(mech["dual_slot_simult_autoswitch_continuation_and_shockless_wb_kelvin_grid_bypass"]["r41c_ok"], 1)

        br = data["runs"]["r41a_desqueeze_165x_4locks_big6_schinese"]["r41_telemetry"]["stage_b_bridge"]
        for key in (
            "faithful",
            "p12_wlan",
            "wf12_00342260_immune",
            "p10_keymap",
            "p4_nd_clear",
            "p11_xlr_h1",
            "desqueeze_165x_4locks",
            "external_mc_focusmap_150fps",
            "simult_autoswitch_single_cont",
            "shockless_wb_kelvin_grid_bypass",
        ):
            self.assertEqual(br[key], 1, f"Expected stage_b_bridge[{key}]==1")
        self.assertEqual(br["round"], 41)
        self.assertEqual(br["nop_count"], 0)
        self.assertEqual(br["emmc_write_count"], 0)
        self.assertEqual(len(data["unexecuted_physical_camera_bench_boundaries"]), 3)

    def test_23_round41_r41a_focusmap_simult_wb_bridge_consistent_with_r41b_and_r41c(self) -> None:
        data = json.loads((ROUND41_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        br_fs = data["runs"]["r41a_desqueeze_165x_4locks_big6_schinese"]["r41_telemetry"]["focusmap_simult_wb_bridge"]
        r41b = data["runs"]["r41b_external_focusmap_150fps_cutoff"]["r41_telemetry"]["external_focusmap_150fps"]
        r41c = data["runs"]["r41c_simult_autoswitch_shocklesswb"]["r41_telemetry"]["simult_shocklesswb"]
        self.assertEqual(br_fs["inbody_focusmap_reject_rc"], r41b["inbody_menu_toggle_reject_rc"])
        self.assertEqual(br_fs["external_mc_only"], 1)
        self.assertEqual(br_fs["focusmap_cutoff_fps"], 150)
        self.assertEqual(br_fs["sq_200_240_reject_rc"], r41b["sq_240fps_reject_rc"])
        self.assertEqual(br_fs["fx3_low_fps_1_to_6_allowed"], r41b["fx3_6fps_allowed"])
        self.assertEqual(br_fs["adapter_nonpdaf_reject_rc"], r41b["mount_adapter_reject_rc"])
        self.assertEqual(br_fs["playback_reject_rc"], r41b["playback_reject_rc"])
        self.assertEqual(br_fs["simult_autoswitch_on_single_cont"], r41c["single_slot_cont_active"])
        self.assertEqual(br_fs["simult_autoswitch_off_halt_rc"], r41c["autoswitch_off_slot1_full_rc"])
        self.assertEqual(br_fs["shockless_wb_fps_max"], 240)
        self.assertEqual(br_fs["ctemp_kelvin_grid_transition_frames"], r41c["ctemp_kelvin_transition_frames"])
        self.assertEqual(br_fs["focusmap_mc_ok"], 1)
        self.assertEqual(br_fs["simult_autoswitch_ok"], 1)
        self.assertEqual(br_fs["shockless_wb_ok"], 1)
        self.assertEqual(br_fs["p2_setting_writes"], 0)
        self.assertEqual(br_fs["emmc_write_count"], 0)

    def test_24_round41_readme_sanitization_and_no_tmp_or_binary_residue(self) -> None:
        closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn("2026-11-15-round41-realhw-desqueeze-165x-focusmap-simult-shocklesswb-qemu", closure_readme)
        self.assertIn("`24` New Round 41 Dual-Mode Unit Tests (`570` Total)", closure_readme)
        r41_readme = (ROUND41_REPORT_DIR / "README.md").read_text(encoding="utf-8")
        for tok in (
            "Round 41",
            "De-Squeeze Display",
            "1.65x",
            "2.39:1",
            "Monitor & Control",
            "150fps",
            "Simult. Recording",
            "Auto Switch Media",
            "Shockless WB",
            "r41a-desqueeze-165x-big6-schinese",
            "r41b-external-focusmap-150fps",
            "r41c-simult-shocklesswb",
        ):
            self.assertIn(tok, r41_readme)
        for forbidden in ("/Users/", "/Volumes/KAFU2T", "/private/tmp"):
            self.assertNotIn(forbidden, r41_readme)
        for folder in (CLOSURE_DIR, ROUND41_REPORT_DIR):
            for p in folder.rglob("*"):
                if p.is_file():
                    self.assertNotIn(p.suffix, {".cpio", ".so", ".o", ".img", ".qcow2", ".pyc"})


if __name__ == "__main__":
    unittest.main()
