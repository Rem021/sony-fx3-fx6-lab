#!/usr/bin/env python3
"""Offline dual-mode unit tests for FX6-on-FX3 Round 37 real-hardware QEMU rehearsal."""
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
ROUND37_REPORT_DIR = (
    REPO_ROOT / "reports" / "2026-11-15-round37-realhw-fx3a-firewall-xlrh1-4ch-fx3bndl1-qemu"
)
ROUND37_ASSETS_DIR = ROUND37_REPORT_DIR / "assets"


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


class TestRound37RealHwFx3aFirewallXlrh14chFx3bndl1(unittest.TestCase):
    EXPECTED_RUN_KEYS = (
        "r37a_fx3a_firewall_big6_schinese",
        "r37b_xlrh1_4ch_override",
        "r37c_fx3bndl1_serial_appledouble",
    )

    def test_01_round37_c_and_python_source_contracts(self) -> None:
        shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")

        self.assertIn("#if FX6_ROUND >= 37", shim_src)
        for token in (
            "FX6_R37_XLRH1_4CH_BRIDGE",
            "FX6_R37_FX3A_FIREWALL_BRIDGE",
            "FX6_R37_LANG_TELEMETRY",
            "FX6_STAGE_B_R37_BRIDGE",
            "realhw_fx3a_firewall_xlrh1_4ch_fx3bndl1=1",
        ):
            self.assertIn(token, shim_src)

        for token in (
            "setup_r37_fx3a_firewall_probe",
            "r37_fx3a_hw_identity_gate",
            "r37_cross_branch_import_gate",
            "FAIL_CLOSED_FX3A_BRANCH_MISMATCH",
            "r37_xlrh1_audio_route_eval",
            "run_r37_xlrh1_4ch_probe",
            "r37_is_macos_clutter_name",
            "run_r37_fx3bndl1_serial_probe",
            "--r37-xlrh1-4ch",
            "--r37-fx3bndl1-serial",
            "/etc/fx6_stage_r37",
            "FX6_R37_FX3A_FIREWALL_INIT",
            "FX6_R37_XLRH1_4CH",
            "FX6_R37_FX3BNDL1_SERIAL",
        ):
            self.assertIn(token, verify_src)

        for token in (
            "enable_r37",
            "r37_mode",
            "--r37-mode",
            "fx3a_firewall_big6",
            "xlrh1_4ch_override",
            "fx3bndl1_serial_appledouble",
            "etc/fx6_stage_r37",
            "FX6_R37_XLRH1_4CH_EXIT",
            "FX6_R37_FX3BNDL1_SERIAL_EXIT",
            '"r37_telemetry"',
            "choices=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44]",
        ):
            self.assertIn(token, runner_src)

    def test_02_round37_native_verify_c_compiles_with_zig_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r37_verc", "build_and_run_round.py")
        self.assertTrue(runner.ZIG.is_file(), f"Missing zig compiler at {runner.ZIG}")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            cache_dir = tmp_dir / "zig-cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            for clean_flag in ("0", "1"):
                out_bin = tmp_dir / f"fx6-stage-a-verify-r37-{clean_flag}"
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

    def test_03_round37_build_binaries_compiles_shim_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r37_shimc", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            for clean_flag in ("0", "1"):
                work = pathlib.Path(tmp) / f"shim_{clean_flag}"
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                    launcher_b, shim_b, meta = runner.build_binaries(
                        work,
                        fx6_round=37,
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

    def test_04_round37_extract_milestones_r37a_fx3a_firewall_and_bridge(self) -> None:
        runner = _load_closure_module("fx6_brr_r37_msa", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R37_FX3A_FIREWALL_INIT fx3a_reject_rc=-22 fx3a_reason=FAIL_CLOSED_FX3A_BRANCH_MISMATCH fx3a_gate_ns=34000 fx3a_gate_us=34 fx3a_under_50us=1 fx3a_stageb_mounted=0 fx3a_fallback=FAIL_CLOSED_STOCK_FX3A fx3a_bodydata_reject_rc=-79 fx3a_camset_reject_rc=-79 fx3_camset_accept_rc=0 fx3_model_id=0x91030080 fx3_fw_ver=7.02 fx3_lcd_dots=1440000 fx3_nfc=1 fx3_ir=1 fx3_pass_rc=0 fx3_reason=PASS_ILME_FX3_702_144M appfw_present=1 emmc_write_count=0 r37_init_ok=1 verify_us=664122",
                "FX6_R37_FX3A_FIREWALL_BRIDGE fx3a_reject_rc=-22 fx3a_camset_rc=-79 fx3_pass_rc=0 fx3_model_id=0x91030080 fx3_lcd_dots=1440000 fx3a_rejected_ok=1 fx3a_camset_blocked_ok=1 fx3_702_pass_ok=1 xlrh1_4ch_ok=1 body35_override_ok=1 sq_mute_ok=1 fx3bndl1_serial_ok=1 transplant_reject_rc=-13 emmc_write_count=0 r37_bridge_ok=1",
                "FX6_R37_XLRH1_4CH_BRIDGE sr=48000 bits=24 ch=4 monitor=CH1+3_CH2+4 mishoe_locked_by_body_35mm=1 sq_audio_muted=1 xlrh1_4ch_ok=1 body35_override_ok=1 sq_mute_ok=1 emmc_write_count=0",
                "FX6_STAGE_B_R37_BRIDGE round=37 faithful=1 nop_count=0 p12_wlan=1 wf12_00342260_immune=1 p10_keymap=1 p4_nd_clear=1 p11_xlr_h1=1 lang=schinese bk4_lang=0x19 enum=0x2b45_CHINESE_SIMPLIFIED font_bank=23 str_bank=19 fx3a_firewall_50us=1 fx3a_camset_blocked=1 xlrh1_4ch_mishoe=1 body35_override_sq_mute=1 fx3bndl1_serial_appledouble=1 emmc_write_count=0",
                "FX6_R37_LANG_TELEMETRY reason=pump lang=schinese bk4_lang_id=0x02cf019c bk4_lang_val=0x19 gpe_fb=0 fx3a_rejected_ok=1 fx3_702_pass_ok=1 xlrh1_4ch_ok=1 fx3bndl1_serial_ok=1 r37_bridge_ok=1 realhw_fx3a_firewall_xlrh1_4ch_fx3bndl1=1 emmc_write_count=0 subst_color=0 subst_image=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        r37 = ms["r37_telemetry"]
        self.assertIsNotNone(r37)
        self.assertEqual(r37["fx3a_firewall_init"]["fx3a_reject_rc"], -22)
        self.assertLess(r37["fx3a_firewall_init"]["fx3a_gate_us"], 50)
        self.assertEqual(r37["fx3a_firewall_init"]["fx3a_bodydata_reject_rc"], -79)
        self.assertEqual(r37["fx3a_firewall_init"]["fx3a_camset_reject_rc"], -79)
        self.assertEqual(r37["fx3a_firewall_init"]["fx3_pass_rc"], 0)
        self.assertEqual(r37["fx3a_firewall_bridge"]["r37_bridge_ok"], 1)
        self.assertEqual(r37["xlrh1_4ch_bridge"]["mishoe_locked_by_body_35mm"], 1)
        self.assertEqual(r37["stage_b_bridge"]["round"], 37)
        self.assertEqual(r37["lang_telemetry"]["gpe_fb"], 0)

    def test_05_round37_extract_milestones_r37b_xlrh1_4ch_override(self) -> None:
        runner = _load_closure_module("fx6_brr_r37_msb", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R37_XLRH1_4CH sample_rate_hz=48000 bit_depth=24 channels=4 ch_map=IN1_CH1,IN2_CH2,IN3L_CH3,IN3R_CH4 monitor_matrix=CH1+3_CH2+4 hp_mix_left_mask=0x5 hp_mix_right_mask=0xa modes_supported=3 body35_inserted_override=1 mishoe_locked_by_body_35mm=1 mishoe_when_body35_rc=-16 active_source_on_body35=BODY_35MM body35_removed_restored=1 sq_mode_active=1 sq_audio_muted=1 upgrade_reset_default=48kHz_16bit_2ch pre_upgrade_snapshot_saved=1 audio_scn_ok=1 shim_elf_ok=1 emmc_write_count=0 r37b_ok=1 verify_us=731",
                "FX6_R37_XLRH1_RC=0",
                "FX6_R37_XLRH1_4CH_EXIT rc=0 emmc_write_count=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        r37 = ms["r37_telemetry"]
        self.assertIsNotNone(r37)
        self.assertEqual(r37["xlrh1_rc"], 0)
        b = r37["xlrh1_4ch"]
        self.assertEqual(b["sample_rate_hz"], 48000)
        self.assertEqual(b["bit_depth"], 24)
        self.assertEqual(b["channels"], 4)
        self.assertEqual(b["mishoe_locked_by_body_35mm"], 1)
        self.assertEqual(b["mishoe_when_body35_rc"], -16)
        self.assertEqual(b["sq_audio_muted"], 1)
        self.assertEqual(b["r37b_ok"], 1)

    def test_06_round37_extract_milestones_r37c_fx3bndl1_serial_appledouble(self) -> None:
        runner = _load_closure_module("fx6_brr_r37_msc", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R37_FX3BNDL1_SERIAL host_serial=FX3-091030080-A001 foreign_serial=FX3-091030080-B999 host_serial_bind_rc=0 transplant_reject_rc=-13 split_pair_reject_rc=-13 transplant_rejected=1 bndl_magic=FX3BNDL1 rcpt_magic=FX3RCPT1 rcpt_bytes=528 appledouble_elf_rejected=1 appledouble_stripped=2 ds_store_stripped=1 dot_underscore_dlopen_attempted=0 dot_underscore_remaining=0 dlopen_ok=1 dlopen_failures=0 surfaces_verified=16 surfaces_h0_eq_h3=16 drift_bits=0 emmc_write_count=0 r37c_ok=1 verify_us=5370",
                "FX6_R37_FX3BNDL1_RC=0",
                "FX6_R37_FX3BNDL1_SERIAL_EXIT rc=0 emmc_write_count=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        r37 = ms["r37_telemetry"]
        self.assertIsNotNone(r37)
        self.assertEqual(r37["fx3bndl1_rc"], 0)
        c = r37["fx3bndl1_serial"]
        self.assertEqual(c["host_serial_bind_rc"], 0)
        self.assertEqual(c["transplant_reject_rc"], -13)
        self.assertEqual(c["split_pair_reject_rc"], -13)
        self.assertEqual(c["appledouble_stripped"], 2)
        self.assertEqual(c["ds_store_stripped"], 1)
        self.assertEqual(c["dot_underscore_dlopen_attempted"], 0)
        self.assertEqual(c["dlopen_ok"], 1)
        self.assertEqual(c["surfaces_h0_eq_h3"], 16)
        self.assertEqual(c["r37c_ok"], 1)

    def test_07_round37_stage_a_overlay_fx3a_firewall_big6_mocked_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r37_ovl_a", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            parent_cpio, fp, fv, fb, fake_run, jit_meta = _build_mock_cpio_and_fakes(runner, tmp_dir)
            for clean_flag in ("0", "1"):
                work = tmp_dir / f"r37_a_{clean_flag}"
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
                        sd_manifest_mode="valid", lang="schinese", shim_bytes=b"SHIM",
                    )
                init_out = rep["init"].decode("utf-8")
                self.assertNotIn("--r37-xlrh1-4ch", init_out)
                self.assertNotIn("--r37-fx3bndl1-serial", init_out)
                self.assertIn("--sd-gate", init_out)
                self.assertIn("etc/fx6_stage_r37", add)
                self.assertIn("r37_mode=fx3a_firewall_big6", add["etc/fx6_stage_r37"][0].decode("utf-8"))
                self.assertTrue(meta["r37_enabled"])
                self.assertEqual(meta["r37"]["r37_mode"], "fx3a_firewall_big6")
                self.assertEqual(meta["r37"]["fx3_model_id"], "0x91030080")
                self.assertEqual(meta["r37"]["fx3_lcd_dots"], 1440000)
                self.assertEqual(meta["r37"]["fx3a_lcd_dots"], 2359296)
                self.assertEqual(meta["r37"]["fx3a_gate_budget_us"], 50)

    def test_08_round37_stage_a_overlay_xlrh1_4ch_mocked_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r37_ovl_b", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            parent_cpio, fp, fv, fb, fake_run, jit_meta = _build_mock_cpio_and_fakes(runner, tmp_dir)
            for clean_flag in ("0", "1"):
                work = tmp_dir / f"r37_b_{clean_flag}"
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
                        enable_r37=True, r37_mode="xlrh1_4ch_override",
                        sd_manifest_mode="valid", lang="en", shim_bytes=b"SHIM",
                    )
                init_out = rep["init"].decode("utf-8")
                self.assertIn("/usr/bin/fx6-stage-a-verify --r37-xlrh1-4ch", init_out)
                self.assertIn("FX6_R37_XLRH1_4CH_EXIT", init_out)
                self.assertEqual(meta["r37"]["r37_mode"], "xlrh1_4ch_override")
                self.assertEqual(meta["r37"]["xlrh1_sample_rate_hz"], 48000)
                self.assertEqual(meta["r37"]["xlrh1_bit_depth"], 24)
                self.assertEqual(meta["r37"]["xlrh1_channels"], 4)

    def test_09_round37_stage_a_overlay_fx3bndl1_serial_mocked_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r37_ovl_c", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            parent_cpio, fp, fv, fb, fake_run, jit_meta = _build_mock_cpio_and_fakes(runner, tmp_dir)
            for clean_flag in ("0", "1"):
                work = tmp_dir / f"r37_c_{clean_flag}"
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
                        enable_r37=True, r37_mode="fx3bndl1_serial_appledouble",
                        sd_manifest_mode="valid", lang="en", shim_bytes=b"SHIM",
                    )
                init_out = rep["init"].decode("utf-8")
                self.assertIn("/usr/bin/fx6-stage-a-verify --r37-fx3bndl1-serial", init_out)
                self.assertIn("FX6_R37_FX3BNDL1_SERIAL_EXIT", init_out)
                self.assertEqual(meta["r37"]["r37_mode"], "fx3bndl1_serial_appledouble")
                self.assertEqual(meta["r37"]["fx3bndl1_magic"], "FX3BNDL1")
                self.assertEqual(meta["r37"]["fx3rcpt1_magic"], "FX3RCPT1")
                self.assertEqual(meta["r37"]["transplant_reject_rc"], -13)
                self.assertTrue(meta["r37"]["appledouble_clutter_stripped"])

    def test_10_round37_stage_a_overlay_rejects_invalid_r37_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r37_badmode", "build_and_run_round.py")
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
                        tmp_dir / "bad_r37", parent_cpio, b"BK4NTSC",
                        enable_p10=True, enable_r10=True, enable_p12=True, enable_r28=True,
                        enable_r30=True, r30_mode="peripheral_big6",
                        enable_r31=True, r31_mode="keymap_big6",
                        enable_r32=True, r32_mode="imx510_cube_big6",
                        enable_r33=True, r33_mode="cfexpress_rsv_big6",
                        enable_r34=True, r34_mode="c2pa_tc_gyro_big6",
                        enable_r35=True, r35_mode="ssboot_wbi2_big6",
                        enable_r36=True, r36_mode="emount_info3d_big6",
                        enable_r37=True, r37_mode="invalid_r37_mode",
                        lang="schinese", shim_bytes=b"SHIM",
                    )

    def test_11_round37_summary_json_schema_sanitization_and_audit_flags(self) -> None:
        summary_path = ROUND37_REPORT_DIR / "summary.json"
        self.assertTrue(summary_path.is_file())
        raw = summary_path.read_text(encoding="utf-8")
        for forbidden in ("/Users/", "/Volumes/KAFU2T", "/private/tmp"):
            self.assertNotIn(forbidden, raw)
        data = json.loads(raw)
        self.assertEqual(data["schema"], "fx6-on-fx3-round37-realhw-fx3a-firewall-xlrh1-4ch-fx3bndl1-qemu-v1")
        self.assertIn("Linux version 4.9.337-scel+", data["kernel_version"])
        self.assertEqual(set(data["runs"].keys()), set(self.EXPECTED_RUN_KEYS))
        audit = data["r37_realhw_fx3a_firewall_xlrh1_4ch_fx3bndl1_audit"]
        self.assertEqual(audit["total_runs"], 3)
        for k in (
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "r37a_fx3a_rejected_under_50us_rc_minus_22_verified",
            "r37a_fx3a_bodydata_and_camset_blocked_rc_minus_79_verified",
            "r37a_fx3_702_144m_stageb_big6_sid_0a_over_340k_pixels_verified",
            "r37b_xlrh1_48khz_24bit_4ch_and_monitor_matrix_verified",
            "r37b_body35_override_and_sq_mute_verified",
            "r37c_fx3bndl1_foreign_serial_transplant_rejected_rc_minus_13_verified",
            "r37c_appledouble_stripped_dlopen_ok_and_16_h0_eq_h3_verified",
        ):
            self.assertTrue(audit[k], f"Audit flag {k} must be True")

    def test_12_round37_r37a_fx3a_rejected_under_50us_fail_closed(self) -> None:
        data = json.loads((ROUND37_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        init = data["runs"]["r37a_fx3a_firewall_big6_schinese"]["r37_telemetry"]["fx3a_firewall_init"]
        self.assertEqual(init["fx3a_reject_rc"], -22)
        self.assertEqual(init["fx3a_reason"], "FAIL_CLOSED_FX3A_BRANCH_MISMATCH")
        self.assertEqual(init["fx3a_fallback"], "FAIL_CLOSED_STOCK_FX3A")
        self.assertEqual(init["fx3a_stageb_mounted"], 0)
        self.assertLess(init["fx3a_gate_us"], 50)
        self.assertEqual(init["fx3a_under_50us"], 1)
        self.assertEqual(init["emmc_write_count"], 0)

    def test_13_round37_r37a_camset_and_bodydata_cross_branch_blocked(self) -> None:
        data = json.loads((ROUND37_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        init = data["runs"]["r37a_fx3a_firewall_big6_schinese"]["r37_telemetry"]["fx3a_firewall_init"]
        self.assertEqual(init["fx3a_bodydata_reject_rc"], -79)
        self.assertEqual(init["fx3a_camset_reject_rc"], -79)
        self.assertEqual(init["fx3_camset_accept_rc"], 0)

    def test_14_round37_r37a_genuine_ilme_fx3_702_pass_and_bridge(self) -> None:
        data = json.loads((ROUND37_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        telem = data["runs"]["r37a_fx3a_firewall_big6_schinese"]["r37_telemetry"]
        init = telem["fx3a_firewall_init"]
        br = telem["fx3a_firewall_bridge"]
        self.assertEqual(init["fx3_model_id"], "0x91030080")
        self.assertEqual(init["fx3_fw_ver"], "7.02")
        self.assertEqual(init["fx3_lcd_dots"], 1440000)
        self.assertEqual(init["fx3_nfc"], 1)
        self.assertEqual(init["fx3_ir"], 1)
        self.assertEqual(init["fx3_pass_rc"], 0)
        self.assertEqual(init["fx3_reason"], "PASS_ILME_FX3_702_144M")
        self.assertEqual(init["appfw_present"], 1)
        self.assertEqual(init["r37_init_ok"], 1)
        self.assertEqual(br["r37_bridge_ok"], 1)
        self.assertEqual(br["fx3a_rejected_ok"], 1)
        self.assertEqual(br["fx3a_camset_blocked_ok"], 1)
        self.assertEqual(br["fx3_702_pass_ok"], 1)

    def test_15_round37_r37a_stage_b_13_sha256_and_big6_render_invariants(self) -> None:
        data = json.loads((ROUND37_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        r37a = data["runs"]["r37a_fx3a_firewall_big6_schinese"]
        self.assertEqual(r37a["round"], 37)
        self.assertEqual(r37a["r37_mode"], "fx3a_firewall_big6")
        self.assertEqual(r37a["target_presenter"], "31procam_big6_menu_home_presenter")
        self.assertEqual(r37a["target_sid"], "0x0a")
        self.assertEqual(r37a["nop_count"], 0)
        self.assertEqual(r37a["crashes"], 0)
        self.assertEqual(r37a["emmc_write_count"], 0)
        self.assertGreaterEqual(r37a["total_threads_seen"], 160)
        self.assertEqual(r37a["faithful_invariants"]["FX6_NATIVE_FAITHFUL"], 1)
        self.assertEqual(r37a["stage_b"]["manifest_count"], 13)
        self.assertEqual(len(r37a["stage_b"]["manifest_items"]), 13)
        for item in r37a["stage_b"]["manifest_items"]:
            self.assertEqual(len(item["sha256"]), 64)
            int(item["sha256"], 16)
        lt = r37a["r37_telemetry"]["lang_telemetry"]
        self.assertEqual(lt["gpe_fb"], 0)
        self.assertEqual(lt["subst_color"], 0)
        self.assertEqual(lt["subst_image"], 0)
        self.assertEqual(lt["r37_bridge_ok"], 1)
        self.assertGreater(r37a["gpe0_readback"]["nonzero_pixels"], 340000)

    def test_16_round37_r37a_png_receipts_under_28kib_and_dimensions(self) -> None:
        data = json.loads((ROUND37_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        exports = data["runs"]["r37a_fx3a_firewall_big6_schinese"]["png_exports"]
        for key in ("alpha_png", "composited_png"):
            p = REPO_ROOT / exports[key]["path"]
            self.assertTrue(p.is_file(), f"Missing Round 37 PNG: {p}")
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

    def test_17_round37_r37b_xlrh1_48khz_24bit_4ch_and_monitor_matrix(self) -> None:
        data = json.loads((ROUND37_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        r37b = data["runs"]["r37b_xlrh1_4ch_override"]
        self.assertEqual(r37b["round"], 37)
        self.assertEqual(r37b["r37_mode"], "xlrh1_4ch_override")
        self.assertEqual(r37b["crashes"], 0)
        self.assertEqual(r37b["emmc_write_count"], 0)
        self.assertTrue(r37b["gpe0_readback"]["skipped_stock_fx3_mode"])
        self.assertEqual(r37b["r37_telemetry"]["xlrh1_rc"], 0)
        b = r37b["r37_telemetry"]["xlrh1_4ch"]
        self.assertEqual(b["sample_rate_hz"], 48000)
        self.assertEqual(b["bit_depth"], 24)
        self.assertEqual(b["channels"], 4)
        self.assertEqual(b["ch_map"], "IN1_CH1,IN2_CH2,IN3L_CH3,IN3R_CH4")
        self.assertEqual(b["monitor_matrix"], "CH1+3_CH2+4")
        self.assertEqual(b["hp_mix_left_mask"], "0x5")
        self.assertEqual(b["hp_mix_right_mask"], "0xa")
        self.assertEqual(b["modes_supported"], 3)
        self.assertEqual(b["r37b_ok"], 1)

    def test_18_round37_r37b_body_35mm_override_unplug_restore_and_sq_mute(self) -> None:
        data = json.loads((ROUND37_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        b = data["runs"]["r37b_xlrh1_4ch_override"]["r37_telemetry"]["xlrh1_4ch"]
        self.assertEqual(b["body35_inserted_override"], 1)
        self.assertEqual(b["mishoe_locked_by_body_35mm"], 1)
        self.assertEqual(b["mishoe_when_body35_rc"], -16)
        self.assertEqual(b["active_source_on_body35"], "BODY_35MM")
        self.assertEqual(b["body35_removed_restored"], 1)
        self.assertEqual(b["sq_mode_active"], 1)
        self.assertEqual(b["sq_audio_muted"], 1)
        self.assertEqual(b["upgrade_reset_default"], "48kHz_16bit_2ch")
        self.assertEqual(b["pre_upgrade_snapshot_saved"], 1)
        self.assertEqual(b["audio_scn_ok"], 1)
        self.assertEqual(b["shim_elf_ok"], 1)
        self.assertEqual(b["emmc_write_count"], 0)

    def test_19_round37_r37c_fx3bndl1_serial_binding_and_transplant_rejection(self) -> None:
        data = json.loads((ROUND37_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        r37c = data["runs"]["r37c_fx3bndl1_serial_appledouble"]
        self.assertEqual(r37c["round"], 37)
        self.assertEqual(r37c["r37_mode"], "fx3bndl1_serial_appledouble")
        self.assertEqual(r37c["crashes"], 0)
        self.assertEqual(r37c["emmc_write_count"], 0)
        self.assertTrue(r37c["gpe0_readback"]["skipped_stock_fx3_mode"])
        self.assertEqual(r37c["r37_telemetry"]["fx3bndl1_rc"], 0)
        c = r37c["r37_telemetry"]["fx3bndl1_serial"]
        self.assertEqual(c["host_serial"], "FX3-091030080-A001")
        self.assertEqual(c["foreign_serial"], "FX3-091030080-B999")
        self.assertEqual(c["host_serial_bind_rc"], 0)
        self.assertEqual(c["transplant_reject_rc"], -13)
        self.assertEqual(c["split_pair_reject_rc"], -13)
        self.assertEqual(c["transplant_rejected"], 1)
        self.assertEqual(c["bndl_magic"], "FX3BNDL1")
        self.assertEqual(c["rcpt_magic"], "FX3RCPT1")
        self.assertEqual(c["rcpt_bytes"], 528)
        self.assertEqual(c["r37c_ok"], 1)

    def test_20_round37_r37c_appledouble_ds_store_hygiene_and_dlopen_ok(self) -> None:
        data = json.loads((ROUND37_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        c = data["runs"]["r37c_fx3bndl1_serial_appledouble"]["r37_telemetry"]["fx3bndl1_serial"]
        self.assertEqual(c["appledouble_elf_rejected"], 1)
        self.assertEqual(c["appledouble_stripped"], 2)
        self.assertEqual(c["ds_store_stripped"], 1)
        self.assertEqual(c["dot_underscore_dlopen_attempted"], 0)
        self.assertEqual(c["dot_underscore_remaining"], 0)
        self.assertEqual(c["dlopen_ok"], 1)
        self.assertEqual(c["dlopen_failures"], 0)

    def test_21_round37_r37c_16_surfaces_h0_eq_h3_zero_drift(self) -> None:
        data = json.loads((ROUND37_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        c = data["runs"]["r37c_fx3bndl1_serial_appledouble"]["r37_telemetry"]["fx3bndl1_serial"]
        self.assertEqual(c["surfaces_verified"], 16)
        self.assertEqual(c["surfaces_h0_eq_h3"], 16)
        self.assertEqual(c["drift_bits"], 0)
        self.assertEqual(c["emmc_write_count"], 0)

    def test_22_round37_stage_b_bridge_mechanisms_and_bench_boundaries(self) -> None:
        data = json.loads((ROUND37_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        mech = data["realhw_mechanisms_verified"]
        self.assertEqual(mech["fx3a_vs_fx3_hardware_identity_firewall"]["r37_init_ok"], 1)
        self.assertEqual(mech["fx3a_firewall_stage_b_bridge"]["r37_bridge_ok"], 1)
        self.assertEqual(mech["xlrh1_mishoe_4ch_and_body35_sq_override"]["r37b_ok"], 1)
        self.assertEqual(mech["airgapped_fx3bndl1_serial_and_appledouble_hygiene"]["r37c_ok"], 1)

        br = data["runs"]["r37a_fx3a_firewall_big6_schinese"]["r37_telemetry"]["stage_b_bridge"]
        for key in (
            "faithful",
            "p12_wlan",
            "wf12_00342260_immune",
            "p10_keymap",
            "p4_nd_clear",
            "p11_xlr_h1",
            "fx3a_firewall_50us",
            "fx3a_camset_blocked",
            "xlrh1_4ch_mishoe",
            "body35_override_sq_mute",
            "fx3bndl1_serial_appledouble",
        ):
            self.assertEqual(br[key], 1, f"Expected stage_b_bridge[{key}]==1")
        self.assertEqual(br["round"], 37)
        self.assertEqual(br["nop_count"], 0)
        self.assertEqual(br["emmc_write_count"], 0)
        self.assertEqual(len(data["unexecuted_physical_camera_bench_boundaries"]), 3)

    def test_23_round37_r37a_xlrh1_bridge_telemetry_consistent_with_r37b(self) -> None:
        data = json.loads((ROUND37_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        br_xlr = data["runs"]["r37a_fx3a_firewall_big6_schinese"]["r37_telemetry"]["xlrh1_4ch_bridge"]
        r37b_xlr = data["runs"]["r37b_xlrh1_4ch_override"]["r37_telemetry"]["xlrh1_4ch"]
        self.assertEqual(br_xlr["sr"], r37b_xlr["sample_rate_hz"])
        self.assertEqual(br_xlr["bits"], r37b_xlr["bit_depth"])
        self.assertEqual(br_xlr["ch"], r37b_xlr["channels"])
        self.assertEqual(br_xlr["monitor"], r37b_xlr["monitor_matrix"])
        self.assertEqual(br_xlr["mishoe_locked_by_body_35mm"], 1)
        self.assertEqual(br_xlr["sq_audio_muted"], 1)
        self.assertEqual(br_xlr["emmc_write_count"], 0)

    def test_24_round37_readme_sanitization_and_no_tmp_or_binary_residue(self) -> None:
        closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn("2026-11-15-round37-realhw-fx3a-firewall-xlrh1-4ch-fx3bndl1-qemu", closure_readme)
        self.assertIn("`24` New Round 37 Dual-Mode Unit Tests (`474` Total)", closure_readme)
        r37_readme = (ROUND37_REPORT_DIR / "README.md").read_text(encoding="utf-8")
        for tok in (
            "ILME-FX3",
            "ILME-FX3A",
            "FAIL_CLOSED_FX3A_BRANCH_MISMATCH",
            "CAMSET",
            "BODYDATA.DAT",
            "XLR-H1",
            "48kHz/24bit 4ch",
            "CH1+3/CH2+4",
            "S&Q",
            "FX3BNDL1",
            "FX3RCPT1",
            "AppleDouble",
            "r37a-fx3a-firewall-big6-schinese",
            "r37b-xlrh1-4ch-override",
            "r37c-fx3bndl1-serial-appledouble",
        ):
            self.assertIn(tok, r37_readme)
        for forbidden in ("/Users/", "/Volumes/KAFU2T", "/private/tmp"):
            self.assertNotIn(forbidden, r37_readme)
        for folder in (CLOSURE_DIR, ROUND37_REPORT_DIR):
            for p in folder.rglob("*"):
                if p.is_file():
                    self.assertNotIn(p.suffix, {".cpio", ".so", ".o", ".img", ".qcow2", ".pyc"})


if __name__ == "__main__":
    unittest.main()
