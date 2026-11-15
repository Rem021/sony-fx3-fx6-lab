#!/usr/bin/env python3
"""Offline dual-mode unit tests for FX6-on-FX3 Round 33 real-hardware QEMU rehearsal."""
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
ROUND33_REPORT_DIR = (
    REPO_ROOT / "reports" / "2026-11-15-round33-realhw-cfexpress-rsv-ufu-5tier-qemu"
)
ROUND33_ASSETS_DIR = ROUND33_REPORT_DIR / "assets"


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


class TestRound33RealHwCfexpressRsvUfu5Tier(unittest.TestCase):
    EXPECTED_RUN_KEYS = (
        "r33a_cfexpress_rsv_big6_schinese",
        "r33b_bodydata_ufu_bypass",
        "r33c_recovery_5tier",
    )

    def test_01_round33_c_and_python_source_contracts(self) -> None:
        shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")

        self.assertIn("#if FX6_ROUND >= 33", shim_src)
        for token in (
            "FX6_R33_CFEXPRESS_RSV_BRIDGE",
            "FX6_R33_LANG_TELEMETRY",
            "FX6_STAGE_B_R33_BRIDGE",
            "/mnt/sd/PRIVATE/M4ROOT/CLIP/C0001.MP4",
            "/mnt/sd/XDROOT/Clip/A001C001.MXF",
            "/mnt/sd2/XDROOT/Clip/C0002.MXF",
            "/mnt/sd2/XDROOT/Clip/C0002.RSV",
            "/mnt/sd2/PRIVATE/M4ROOT/MEDIAPRO.XML",
            "/mnt/sd/PRIVATE/M4ROOT/CLIP/C0001_FLUSH.MP4",
        ):
            self.assertIn(token, shim_src)

        for token in (
            "setup_r33_cfexpress_rsv_probe",
            "r33_stage_a_bodydata_fast_check",
            "r33_ufu_validate_model",
            "r33_arm_p1_update_gate",
            "run_r33_bodydata_ufu_bypass_probe",
            "r33_tier5_isp_write_gate",
            "run_r33_recovery_5tier_probe",
            "--r33-bodydata-ufu-bypass",
            "--r33-recovery-5tier",
            "/etc/fx6_stage_r33",
            "FX6_R33_CFEXPRESS_RSV_INIT",
            "FX6_R33_BODYDATA_UFU_BYPASS",
            "FX6_R33_5TIER_RECOVERY",
        ):
            self.assertIn(token, verify_src)

        for token in (
            "enable_r33",
            "r33_mode",
            "--r33-mode",
            "cfexpress_rsv_big6",
            "bodydata_ufu_bypass",
            "recovery_5tier",
            "etc/fx6_stage_r33",
            "FX6_R33_UFU_BYPASS_EXIT",
            "FX6_R33_5TIER_EXIT",
            '"r33_telemetry"',
            "choices=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33]",
        ):
            self.assertIn(token, runner_src)

    def test_02_round33_native_verify_c_compiles_with_zig_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r33_verc", "build_and_run_round.py")
        self.assertTrue(runner.ZIG.is_file(), f"Missing zig compiler at {runner.ZIG}")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            cache_dir = tmp_dir / "zig-cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            for clean_flag in ("0", "1"):
                out_bin = tmp_dir / f"fx6-stage-a-verify-r33-{clean_flag}"
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

    def test_03_round33_build_binaries_compiles_shim_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r33_shimc", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            for clean_flag in ("0", "1"):
                work = pathlib.Path(tmp) / f"shim_{clean_flag}"
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                    launcher_b, shim_b, meta = runner.build_binaries(
                        work,
                        fx6_round=33,
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

    def test_04_round33_extract_milestones_r33a_cfexpress_rsv_and_bridge(self) -> None:
        runner = _load_closure_module("fx6_brr_r33_msa", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R33_CFEXPRESS_RSV_INIT slot_a_mounted=1 slot_b_mounted=1 user_clips_preserved=1 clip_m4root_sha256_match=1 clip_xdroot_sha256_match=1 dual_slot_relay_ok=1 admit_cfexpress_600m=1 admit_v90_600m=1 v30_600m_rejected=1 v30_reject_rc=-22 door_flush_ok=1 door_gpio_irq_ms=1 door_flush_ms=4 cap_hold_ms=15 unflushed_bytes=0 rsv_salvaged=1 rsv_size_bytes=8192 mxf_size_bytes=8256 mediapro_xml_updated=1 tiny_rsv_rejected=1 mpr_elf_ok=1 sencore_elf_ok=1 emmc_write_count=0 r33_init_ok=1 verify_us=9666",
                "FX6_R33_CFEXPRESS_RSV_BRIDGE slot_a_cfexpress=1 slot_b_sdxc_v90=1 user_clips_preserved=1 dual_slot_relay_ok=1 admit_600mbps_ok=1 v30_600m_rejected=1 door_flush_ok=1 unflushed_bytes=0 rsv_salvaged=1 mediapro_xml_updated=1 sencore_ok=1 emmc_write_count=0 r33_bridge_ok=1",
                "FX6_STAGE_B_R33_BRIDGE round=33 faithful=1 nop_count=0 p12_wlan=1 wf12_00342260_immune=1 p10_keymap=1 p4_nd_clear=1 p11_xlr_h1=1 lang=schinese bk4_lang=0x19 enum=0x2b45_CHINESE_SIMPLIFIED font_bank=23 str_bank=19 dual_slot_exfat_relay=1 speed_class_600m_gate=1 card_door_gpio_flush=1 rsv_mxf_salvage=1 bodydata_ufu_100us_bypass=1 recovery_5tier_lock=1 emmc_write_count=0",
                "FX6_R33_LANG_TELEMETRY reason=pump lang=schinese gpe_fb=0 user_clips_preserved=1 rsv_salvaged=1 door_flush_ok=1 unflushed_bytes=0 r33_bridge_ok=1 realhw_cfexpress_rsv_ufu_5tier=1 emmc_write_count=0 subst_color=0 subst_image=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        r33 = ms["r33_telemetry"]
        self.assertIsNotNone(r33)
        self.assertEqual(r33["cfexpress_rsv_init"]["user_clips_preserved"], 1)
        self.assertEqual(r33["cfexpress_rsv_init"]["v30_reject_rc"], -22)
        self.assertEqual(r33["cfexpress_rsv_init"]["unflushed_bytes"], 0)
        self.assertEqual(r33["cfexpress_rsv_init"]["rsv_salvaged"], 1)
        self.assertEqual(r33["cfexpress_rsv_bridge"]["r33_bridge_ok"], 1)
        self.assertEqual(r33["stage_b_bridge"]["round"], 33)
        self.assertEqual(r33["lang_telemetry"]["gpe_fb"], 0)

    def test_05_round33_extract_milestones_r33b_bodydata_ufu_bypass(self) -> None:
        runner = _load_closure_module("fx6_brr_r33_msb", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R33_BODYDATA_UFU_BYPASS bypass_mode=BODYDATA_UFU_STOCK_BYPASS bodydata_path=/mnt/sd/BODYDATA.DAT ufu_magic_ok=1 stage_b_aborted=1 stock_fx3_booted=1 bypass_ns=48000 bypass_us=48 bypass_budget_us=100 bypass_under_100us=1 fx3_expected_model_id=0x91030080 fx3_0x91030080_valid=1 fx30_observed_model_id=0x91030084 fx30_rejected=1 fx30_reject_rc=-22 fx30_stage_b_aborted=1 5l6s_brick_guard=1 p1_arm_blocked_dirty=1 p1_arm_blocked_rc=-16 mode_files_while_dirty=0 p15_orig_h0_sha256=aaa p15_orig_h3_sha256=aaa h0_eq_h3=1 p15_residual_files=0 p15_ro_erofs=1 p1_arm_allowed_clean=1 emmc_write_count=0 r33b_ok=1 verify_us=7554",
                "FX6_R33_UFU_BYPASS_RC=0",
                "FX6_R33_UFU_BYPASS_EXIT rc=0 emmc_write_count=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        r33 = ms["r33_telemetry"]
        self.assertIsNotNone(r33)
        self.assertEqual(r33["ufu_bypass_rc"], 0)
        b = r33["bodydata_ufu_bypass"]
        self.assertEqual(b["bypass_mode"], "BODYDATA_UFU_STOCK_BYPASS")
        self.assertEqual(b["bypass_under_100us"], 1)
        self.assertLess(b["bypass_us"], 100)
        self.assertEqual(b["fx30_rejected"], 1)
        self.assertEqual(b["h0_eq_h3"], 1)
        self.assertEqual(b["r33b_ok"], 1)

    def test_06_round33_extract_milestones_r33c_recovery_5tier(self) -> None:
        runner = _load_closure_module("fx6_brr_r33_msc", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R33_TIER_STEP tier=1 name=TIER_1_EH1_47US_SD_BYPASS eh1_budget_us=47 measured_us=26 stock_fallback=1 el3_payload_tx=0 spi_nor_writes=0 emmc_write_count=0 tier_ok=1",
                "FX6_R33_TIER_STEP tier=2 name=TIER_2_P15_ORIG_RESTORE_H0_EQ_H3 h0_eq_h3=1 p15_ro_erofs=1 residual_files=0 el3_payload_tx=0 spi_nor_writes=0 emmc_write_count=0 tier_ok=1",
                "FX6_R33_TIER_STEP tier=3 name=TIER_3_P1_MODE_CLEAR_LINE1 mode_before=2 mode_after=0 exec_rc=0 p3_ro_erofs=1 el3_payload_tx=0 spi_nor_writes=0 emmc_write_count=0 tier_ok=1",
                "FX6_R33_TIER_STEP tier=4 name=TIER_4_UART_460800_1V8_PASSIVE_TRIAGE kernel_ok=1 uart_logic_mv=1800 uart_tx_bytes=0 ov_abort_rc=-34 vmc_abort_rc=-16 el3_payload_tx=0 spi_nor_writes=0 emmc_write_count=0 tier_ok=1",
                "FX6_R33_TIER_STEP tier=5 name=TIER_5_EL3_ISP_READ_ONLY_LOCK mtd_dump_ok=1 mtd_dump_bytes=16384 mtd_rw_errno=30 el3_gate_rc=-1 otp_gate_rc=-1 mtd0_gate_rc=-13 pnflasha_gate_rc=-13 el3_payload_tx=0 spi_nor_writes=0 otp_writes=0 emmc_write_count=0 tier_ok=1",
                "FX6_R33_5TIER_RECOVERY tiers_passed=5 tiers_total=5 t1_eh1_47us_ok=1 t2_p15_orig_h0_eq_h3_ok=1 t3_p1_mode_clear_ok=1 t4_uart_passive_triage_ok=1 t5_el3_isp_ro_lock_ok=1 uart_tx_bytes=0 otp_writes=0 el3_payload_tx=0 spi_nor_writes=0 emmc_write_count=0 r33c_ok=1 verify_us=18488",
                "FX6_R33_5TIER_RC=0",
                "FX6_R33_5TIER_EXIT rc=0 emmc_write_count=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        r33 = ms["r33_telemetry"]
        self.assertIsNotNone(r33)
        self.assertEqual(r33["recovery_5tier_rc"], 0)
        self.assertEqual(len(r33["recovery_tier_steps"]), 5)
        rec = r33["recovery_5tier"]
        self.assertEqual(rec["tiers_passed"], 5)
        self.assertEqual(rec["el3_payload_tx"], 0)
        self.assertEqual(rec["spi_nor_writes"], 0)
        self.assertEqual(rec["emmc_write_count"], 0)
        self.assertEqual(rec["r33c_ok"], 1)

    def test_07_round33_stage_a_overlay_cfexpress_rsv_big6_mocked_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r33_ovl_a", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            parent_cpio, fp, fv, fb, fake_run, jit_meta = _build_mock_cpio_and_fakes(runner, tmp_dir)
            for clean_flag in ("0", "1"):
                work = tmp_dir / f"r33_a_{clean_flag}"
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
                        sd_manifest_mode="valid", lang="schinese", shim_bytes=b"SHIM",
                    )
                init_out = rep["init"].decode("utf-8")
                self.assertNotIn("--r33-bodydata-ufu-bypass", init_out)
                self.assertNotIn("--r33-recovery-5tier", init_out)
                self.assertIn("--sd-gate", init_out)
                self.assertIn("etc/fx6_stage_r33", add)
                self.assertIn("r33_mode=cfexpress_rsv_big6", add["etc/fx6_stage_r33"][0].decode("utf-8"))
                self.assertTrue(meta["r33_enabled"])
                self.assertEqual(meta["r33"]["r33_mode"], "cfexpress_rsv_big6")
                self.assertEqual(meta["r33"]["bitrate_admission_mbps"], 600)
                self.assertEqual(meta["r33"]["card_door_cap_hold_ms"], 15)

    def test_08_round33_stage_a_overlay_bodydata_ufu_bypass_mocked_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r33_ovl_b", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            parent_cpio, fp, fv, fb, fake_run, jit_meta = _build_mock_cpio_and_fakes(runner, tmp_dir)
            for clean_flag in ("0", "1"):
                work = tmp_dir / f"r33_b_{clean_flag}"
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
                        enable_r33=True, r33_mode="bodydata_ufu_bypass",
                        sd_manifest_mode="valid", lang="en", shim_bytes=b"SHIM",
                    )
                init_out = rep["init"].decode("utf-8")
                self.assertIn("/usr/bin/fx6-stage-a-verify --r33-bodydata-ufu-bypass", init_out)
                self.assertIn("FX6_R33_UFU_BYPASS_EXIT", init_out)
                self.assertEqual(meta["r33"]["r33_mode"], "bodydata_ufu_bypass")
                self.assertEqual(meta["r33"]["bodydata_bypass_budget_us"], 100)
                self.assertEqual(meta["r33"]["fx3_expected_model_id"], "0x91030080")
                self.assertEqual(meta["r33"]["fx30_rejected_model_id"], "0x91030084")

    def test_09_round33_stage_a_overlay_recovery_5tier_mocked_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r33_ovl_c", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            parent_cpio, fp, fv, fb, fake_run, jit_meta = _build_mock_cpio_and_fakes(runner, tmp_dir)
            for clean_flag in ("0", "1"):
                work = tmp_dir / f"r33_c_{clean_flag}"
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
                        enable_r33=True, r33_mode="recovery_5tier",
                        sd_manifest_mode="valid", lang="en", shim_bytes=b"SHIM",
                    )
                init_out = rep["init"].decode("utf-8")
                self.assertIn("/usr/bin/fx6-stage-a-verify --r33-recovery-5tier", init_out)
                self.assertIn("FX6_R33_5TIER_EXIT", init_out)
                self.assertEqual(meta["r33"]["r33_mode"], "recovery_5tier")
                self.assertEqual(len(meta["r33"]["recovery_5tier_ladder"]), 5)

    def test_10_round33_stage_a_overlay_rejects_invalid_r33_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r33_badmode", "build_and_run_round.py")
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
                        tmp_dir / "bad_r33", parent_cpio, b"BK4NTSC",
                        enable_p10=True, enable_r10=True, enable_p12=True, enable_r28=True,
                        enable_r30=True, r30_mode="peripheral_big6",
                        enable_r31=True, r31_mode="keymap_big6",
                        enable_r32=True, r32_mode="imx510_cube_big6",
                        enable_r33=True, r33_mode="invalid_r33_mode",
                        lang="schinese", shim_bytes=b"SHIM",
                    )

    def test_11_round33_summary_json_schema_sanitization_and_audit_flags(self) -> None:
        summary_path = ROUND33_REPORT_DIR / "summary.json"
        self.assertTrue(summary_path.is_file())
        raw = summary_path.read_text(encoding="utf-8")
        for forbidden in ("/Users/", "/Volumes/KAFU2T", "/private/tmp"):
            self.assertNotIn(forbidden, raw)
        data = json.loads(raw)
        self.assertEqual(data["schema"], "fx6-on-fx3-round33-realhw-cfexpress-rsv-ufu-5tier-qemu-v1")
        self.assertIn("Linux version 4.9.337-scel+", data["kernel_version"])
        self.assertEqual(set(data["runs"].keys()), set(self.EXPECTED_RUN_KEYS))
        audit = data["r33_realhw_cfexpress_rsv_ufu_5tier_audit"]
        self.assertEqual(audit["total_runs"], 3)
        for k in (
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "r33a_dual_slot_user_clips_preserved_verified",
            "r33a_600mbps_cfexpress_v90_admit_v30_reject_verified",
            "r33a_card_door_gpio_fifo_flush_zero_unflushed_verified",
            "r33a_rsv_to_mxf_salvage_and_mediapro_xml_verified",
            "r33a_stageb_big6_sid_0a_over_300k_pixels_verified",
            "r33b_bodydata_ufu_under_100us_stock_bypass_verified",
            "r33b_cross_model_fx30_rejected_verified",
            "r33b_p1_arm_blocked_until_h0_eq_h3_verified",
            "r33c_5tier_recovery_escalation_5_of_5_verified",
            "r33c_el3_tx_zero_and_spi_nor_writes_zero_verified",
        ):
            self.assertTrue(audit[k], f"Audit flag {k} must be True")

    def test_12_round33_r33a_dual_slot_user_clips_preserved_and_600m_gate(self) -> None:
        data = json.loads((ROUND33_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        telem = data["runs"]["r33a_cfexpress_rsv_big6_schinese"]["r33_telemetry"]
        init = telem["cfexpress_rsv_init"]
        br = telem["cfexpress_rsv_bridge"]
        self.assertEqual(init["slot_a_mounted"], 1)
        self.assertEqual(init["slot_b_mounted"], 1)
        self.assertEqual(init["user_clips_preserved"], 1)
        self.assertEqual(init["clip_m4root_sha256_match"], 1)
        self.assertEqual(init["clip_xdroot_sha256_match"], 1)
        self.assertEqual(init["dual_slot_relay_ok"], 1)
        self.assertEqual(init["admit_cfexpress_600m"], 1)
        self.assertEqual(init["admit_v90_600m"], 1)
        self.assertEqual(init["v30_600m_rejected"], 1)
        self.assertEqual(init["v30_reject_rc"], -22)
        self.assertEqual(br["slot_a_cfexpress"], 1)
        self.assertEqual(br["slot_b_sdxc_v90"], 1)
        self.assertEqual(br["admit_600mbps_ok"], 1)

    def test_13_round33_r33a_card_door_gpio_fifo_flush_within_15ms(self) -> None:
        data = json.loads((ROUND33_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        telem = data["runs"]["r33a_cfexpress_rsv_big6_schinese"]["r33_telemetry"]
        init = telem["cfexpress_rsv_init"]
        br = telem["cfexpress_rsv_bridge"]
        self.assertEqual(init["door_flush_ok"], 1)
        self.assertEqual(init["unflushed_bytes"], 0)
        self.assertEqual(init["cap_hold_ms"], 15)
        self.assertLess(init["door_gpio_irq_ms"] + init["door_flush_ms"], init["cap_hold_ms"])
        self.assertEqual(br["door_flush_ok"], 1)
        self.assertEqual(br["unflushed_bytes"], 0)

    def test_14_round33_r33a_rsv_salvage_mediapro_xml_and_tiny_rsv_reject(self) -> None:
        data = json.loads((ROUND33_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        telem = data["runs"]["r33a_cfexpress_rsv_big6_schinese"]["r33_telemetry"]
        init = telem["cfexpress_rsv_init"]
        br = telem["cfexpress_rsv_bridge"]
        self.assertEqual(init["rsv_salvaged"], 1)
        self.assertEqual(init["rsv_size_bytes"], 8192)
        self.assertEqual(init["mxf_size_bytes"], 8256)
        self.assertEqual(init["mediapro_xml_updated"], 1)
        self.assertEqual(init["tiny_rsv_rejected"], 1)
        self.assertEqual(init["mpr_elf_ok"], 1)
        self.assertEqual(init["sencore_elf_ok"], 1)
        self.assertEqual(br["rsv_salvaged"], 1)
        self.assertEqual(br["mediapro_xml_updated"], 1)
        self.assertEqual(br["sencore_ok"], 1)
        self.assertEqual(br["r33_bridge_ok"], 1)

    def test_15_round33_r33a_stage_b_13_sha256_and_big6_render_invariants(self) -> None:
        data = json.loads((ROUND33_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        r33a = data["runs"]["r33a_cfexpress_rsv_big6_schinese"]
        self.assertEqual(r33a["round"], 33)
        self.assertEqual(r33a["r33_mode"], "cfexpress_rsv_big6")
        self.assertEqual(r33a["target_presenter"], "31procam_big6_menu_home_presenter")
        self.assertEqual(r33a["target_sid"], "0x0a")
        self.assertEqual(r33a["nop_count"], 0)
        self.assertEqual(r33a["crashes"], 0)
        self.assertEqual(r33a["emmc_write_count"], 0)
        self.assertGreaterEqual(r33a["total_threads_seen"], 160)
        self.assertEqual(r33a["faithful_invariants"]["FX6_NATIVE_FAITHFUL"], 1)
        self.assertEqual(r33a["stage_b"]["manifest_count"], 13)
        self.assertEqual(len(r33a["stage_b"]["manifest_items"]), 13)
        for item in r33a["stage_b"]["manifest_items"]:
            self.assertEqual(len(item["sha256"]), 64)
            int(item["sha256"], 16)
        lt = r33a["r33_telemetry"]["lang_telemetry"]
        self.assertEqual(lt["gpe_fb"], 0)
        self.assertEqual(lt["subst_color"], 0)
        self.assertEqual(lt["subst_image"], 0)
        self.assertEqual(lt["r33_bridge_ok"], 1)
        self.assertGreater(r33a["gpe0_readback"]["nonzero_pixels"], 300000)

    def test_16_round33_r33a_png_receipts_under_28kib_and_dimensions(self) -> None:
        data = json.loads((ROUND33_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        exports = data["runs"]["r33a_cfexpress_rsv_big6_schinese"]["png_exports"]
        for key in ("alpha_png", "composited_png"):
            p = REPO_ROOT / exports[key]["path"]
            self.assertTrue(p.is_file(), f"Missing Round 33 PNG: {p}")
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
                self.assertGreater(nonzero_alpha, 300000)

    def test_17_round33_r33b_bodydata_ufu_under_100us_stock_bypass(self) -> None:
        data = json.loads((ROUND33_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        r33b = data["runs"]["r33b_bodydata_ufu_bypass"]
        self.assertEqual(r33b["round"], 33)
        self.assertEqual(r33b["r33_mode"], "bodydata_ufu_bypass")
        self.assertEqual(r33b["crashes"], 0)
        self.assertEqual(r33b["emmc_write_count"], 0)
        self.assertTrue(r33b["gpe0_readback"]["skipped_stock_fx3_mode"])
        self.assertEqual(r33b["r33_telemetry"]["ufu_bypass_rc"], 0)
        b = r33b["r33_telemetry"]["bodydata_ufu_bypass"]
        self.assertEqual(b["bypass_mode"], "BODYDATA_UFU_STOCK_BYPASS")
        self.assertEqual(b["bodydata_path"], "/mnt/sd/BODYDATA.DAT")
        self.assertEqual(b["ufu_magic_ok"], 1)
        self.assertEqual(b["stage_b_aborted"], 1)
        self.assertEqual(b["stock_fx3_booted"], 1)
        self.assertEqual(b["bypass_budget_us"], 100)
        self.assertEqual(b["bypass_under_100us"], 1)
        self.assertLess(b["bypass_us"], 100)
        self.assertEqual(b["r33b_ok"], 1)

    def test_18_round33_r33b_cross_model_ilme_fx30_rejected(self) -> None:
        data = json.loads((ROUND33_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        b = data["runs"]["r33b_bodydata_ufu_bypass"]["r33_telemetry"]["bodydata_ufu_bypass"]
        self.assertEqual(b["fx3_expected_model_id"], "0x91030080")
        self.assertEqual(b["fx3_0x91030080_valid"], 1)
        self.assertEqual(b["fx30_observed_model_id"], "0x91030084")
        self.assertEqual(b["fx30_rejected"], 1)
        self.assertEqual(b["fx30_reject_rc"], -22)
        self.assertEqual(b["fx30_stage_b_aborted"], 1)
        self.assertEqual(b["5l6s_brick_guard"], 1)

    def test_19_round33_r33b_p1_arm_blocked_until_p15_orig_h0_eq_h3(self) -> None:
        data = json.loads((ROUND33_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        b = data["runs"]["r33b_bodydata_ufu_bypass"]["r33_telemetry"]["bodydata_ufu_bypass"]
        self.assertEqual(b["p1_arm_blocked_dirty"], 1)
        self.assertEqual(b["p1_arm_blocked_rc"], -16)
        self.assertEqual(b["mode_files_while_dirty"], 0)
        self.assertEqual(len(b["p15_orig_h0_sha256"]), 64)
        self.assertEqual(b["p15_orig_h0_sha256"], b["p15_orig_h3_sha256"])
        self.assertEqual(b["h0_eq_h3"], 1)
        self.assertEqual(b["p15_residual_files"], 0)
        self.assertEqual(b["p15_ro_erofs"], 1)
        self.assertEqual(b["p1_arm_allowed_clean"], 1)
        self.assertEqual(b["emmc_write_count"], 0)

    def test_20_round33_r33c_5tier_recovery_escalation_ladder(self) -> None:
        data = json.loads((ROUND33_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        r33c = data["runs"]["r33c_recovery_5tier"]
        self.assertEqual(r33c["round"], 33)
        self.assertEqual(r33c["r33_mode"], "recovery_5tier")
        self.assertEqual(r33c["crashes"], 0)
        self.assertEqual(r33c["emmc_write_count"], 0)
        self.assertTrue(r33c["gpe0_readback"]["skipped_stock_fx3_mode"])
        self.assertEqual(r33c["r33_telemetry"]["recovery_5tier_rc"], 0)
        rec = r33c["r33_telemetry"]["recovery_5tier"]
        steps = r33c["r33_telemetry"]["recovery_tier_steps"]
        self.assertEqual(rec["tiers_passed"], 5)
        self.assertEqual(rec["tiers_total"], 5)
        self.assertEqual(len(steps), 5)
        self.assertEqual(
            [s["name"] for s in steps],
            [
                "TIER_1_EH1_47US_SD_BYPASS",
                "TIER_2_P15_ORIG_RESTORE_H0_EQ_H3",
                "TIER_3_P1_MODE_CLEAR_LINE1",
                "TIER_4_UART_460800_1V8_PASSIVE_TRIAGE",
                "TIER_5_EL3_ISP_READ_ONLY_LOCK",
            ],
        )
        for s in steps:
            self.assertEqual(s["tier_ok"], 1)
            self.assertEqual(s["el3_payload_tx"], 0)
            self.assertEqual(s["spi_nor_writes"], 0)
            self.assertEqual(s["emmc_write_count"], 0)

    def test_21_round33_r33c_zero_el3_spi_otp_and_mtdro_guards(self) -> None:
        data = json.loads((ROUND33_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        rec = data["runs"]["r33c_recovery_5tier"]["r33_telemetry"]["recovery_5tier"]
        steps = data["runs"]["r33c_recovery_5tier"]["r33_telemetry"]["recovery_tier_steps"]
        self.assertEqual(rec["uart_tx_bytes"], 0)
        self.assertEqual(rec["otp_writes"], 0)
        self.assertEqual(rec["el3_payload_tx"], 0)
        self.assertEqual(rec["spi_nor_writes"], 0)
        self.assertEqual(rec["emmc_write_count"], 0)
        self.assertEqual(rec["r33c_ok"], 1)
        self.assertLess(steps[0]["measured_us"], 47)
        self.assertEqual(steps[4]["mtd_dump_ok"], 1)
        self.assertEqual(steps[4]["mtd_rw_errno"], 30)
        self.assertEqual(steps[4]["el3_gate_rc"], -1)
        self.assertEqual(steps[4]["otp_gate_rc"], -1)
        self.assertEqual(steps[4]["mtd0_gate_rc"], -13)
        self.assertEqual(steps[4]["pnflasha_gate_rc"], -13)

    def test_22_round33_top_level_realhw_mechanisms_and_bench_boundaries(self) -> None:
        data = json.loads((ROUND33_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        mech = data["realhw_mechanisms_verified"]
        a = mech["cfexpress_sdxc_v90_relay_door_flush_and_rsv_salvage"]
        b = mech["bodydata_ufu_100us_bypass_and_fx30_reject_and_p1_guard"]
        c = mech["recovery_5tier_escalation_read_only_lock"]
        self.assertEqual(a["r33_bridge_ok"], 1)
        self.assertEqual(a["user_clips_preserved"], 1)
        self.assertEqual(a["unflushed_bytes"], 0)
        self.assertEqual(a["rsv_salvaged"], 1)
        self.assertEqual(b["r33b_ok"], 1)
        self.assertEqual(b["bypass_under_100us"], 1)
        self.assertEqual(b["fx30_rejected"], 1)
        self.assertEqual(b["h0_eq_h3"], 1)
        self.assertEqual(c["r33c_ok"], 1)
        self.assertEqual(c["tiers_passed"], 5)
        self.assertEqual(c["el3_payload_tx"], 0)
        self.assertEqual(c["spi_nor_writes"], 0)
        boundaries = data["unexecuted_physical_camera_bench_boundaries"]
        self.assertEqual(len(boundaries), 3)

    def test_23_round33_stage_b_r33_bridge_invariants_in_r33a(self) -> None:
        data = json.loads((ROUND33_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        br = data["runs"]["r33a_cfexpress_rsv_big6_schinese"]["r33_telemetry"]["stage_b_bridge"]
        for key in (
            "faithful",
            "p12_wlan",
            "wf12_00342260_immune",
            "p10_keymap",
            "p4_nd_clear",
            "p11_xlr_h1",
            "dual_slot_exfat_relay",
            "speed_class_600m_gate",
            "card_door_gpio_flush",
            "rsv_mxf_salvage",
            "bodydata_ufu_100us_bypass",
            "recovery_5tier_lock",
        ):
            self.assertEqual(br[key], 1, f"Expected stage_b_bridge[{key}]==1")
        self.assertEqual(br["round"], 33)
        self.assertEqual(br["nop_count"], 0)
        self.assertEqual(br["emmc_write_count"], 0)

    def test_24_round33_readme_sanitization_and_no_tmp_or_binary_residue(self) -> None:
        closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn("2026-11-15-round33-realhw-cfexpress-rsv-ufu-5tier-qemu", closure_readme)
        self.assertIn("`24` New Round 33 Dual-Mode Unit Tests (`378` Total)", closure_readme)
        r33_readme = (ROUND33_REPORT_DIR / "README.md").read_text(encoding="utf-8")
        for tok in (
            "CFexpress Type A",
            "SDXC",
            "V90",
            "600 Mbps",
            "C0002.RSV",
            "C0002.MXF",
            "MEDIAPRO.XML",
            "BODYDATA.DAT",
            "BODYDATA_UFU_STOCK_BYPASS",
            "0x91030080",
            "ILME-FX30",
            "EH1",
            "13/13",
        ):
            self.assertIn(tok, r33_readme)
        for forbidden in ("/Volumes/KAFU2T", "/Users/", "/private/tmp"):
            self.assertNotIn(forbidden, r33_readme)
        tmp_matches = list(pathlib.Path("/private/tmp").glob("fx6-r33*"))
        self.assertEqual(tmp_matches, [], f"Leftover scratch dirs in /private/tmp: {tmp_matches}")
        for tree in (CLOSURE_DIR, ROUND33_REPORT_DIR):
            for ext in ("*.so", "*.elf", "*.o", "*.cpio", "*.vfat", "*.raw", "*.pyc"):
                hits = list(tree.rglob(ext))
                self.assertEqual(hits, [], f"Unexpected binary residue {ext} in {tree}: {hits}")


if __name__ == "__main__":
    unittest.main()
