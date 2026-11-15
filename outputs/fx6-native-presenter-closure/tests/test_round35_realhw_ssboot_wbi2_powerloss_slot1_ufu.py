#!/usr/bin/env python3
"""Offline dual-mode unit tests for FX6-on-FX3 Round 35 real-hardware QEMU rehearsal."""
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
ROUND35_REPORT_DIR = (
    REPO_ROOT / "reports" / "2026-11-15-round35-realhw-ssboot-wbi2-powerloss-slot1-ufu-qemu"
)
ROUND35_ASSETS_DIR = ROUND35_REPORT_DIR / "assets"


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


class TestRound35RealHwSsbootWbi2PowerLossSlot1Ufu(unittest.TestCase):
    EXPECTED_RUN_KEYS = (
        "r35a_ssboot_wbi2_big6_schinese",
        "r35b_powerloss_100cycle_rsv",
        "r35c_slot1_ufu_c2pa_ceiling",
    )

    def test_01_round35_c_and_python_source_contracts(self) -> None:
        shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        verify_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")

        self.assertIn("#if FX6_ROUND >= 35", shim_src)
        for token in (
            "FX6_R35_SSBOOT_WBI2_BRIDGE",
            "FX6_R35_LANG_TELEMETRY",
            "FX6_STAGE_B_R35_BRIDGE",
            "/dev/nflasha5",
            "/dev/pnflasha5",
            "/mnt/r35_tier0/FX3RCPT1.bin",
            "realhw_ssboot_wbi2_powerloss_slot1_ufu=1",
        ):
            self.assertIn(token, shim_src)

        for token in (
            "setup_r35_ssboot_wbi2_probe",
            "r35_bind_ro_loop_dev",
            "r35_ssboot_suspend_disk_gate",
            "r35_build_wbi2_image",
            "run_r35_powerloss_100cycle_probe",
            "run_r35_slot1_ufu_c2pa_probe",
            "r35_bodydata_precheck_gate",
            "r35_c2pa_license_bundle_gate",
            "r35_wlan_security_gate",
            "--r35-powerloss-100cycle",
            "--r35-slot1-ufu-c2pa",
            "/etc/fx6_stage_r35",
            "FX6_R35_SSBOOT_WBI2_INIT",
            "FX6_R35_POWERLOSS_100CYCLE",
            "FX6_R35_SLOT1_UFU_C2PA",
        ):
            self.assertIn(token, verify_src)

        for token in (
            "enable_r35",
            "r35_mode",
            "--r35-mode",
            "ssboot_wbi2_big6",
            "powerloss_100cycle_rsv",
            "slot1_ufu_c2pa_ceiling",
            "etc/fx6_stage_r35",
            "FX6_R35_POWERLOSS_100CYCLE_EXIT",
            "FX6_R35_SLOT1_UFU_C2PA_EXIT",
            '"r35_telemetry"',
            "choices=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36]",
        ):
            self.assertIn(token, runner_src)

    def test_02_round35_native_verify_c_compiles_with_zig_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r35_verc", "build_and_run_round.py")
        self.assertTrue(runner.ZIG.is_file(), f"Missing zig compiler at {runner.ZIG}")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            cache_dir = tmp_dir / "zig-cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            for clean_flag in ("0", "1"):
                out_bin = tmp_dir / f"fx6-stage-a-verify-r35-{clean_flag}"
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

    def test_03_round35_build_binaries_compiles_shim_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r35_shimc", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            for clean_flag in ("0", "1"):
                work = pathlib.Path(tmp) / f"shim_{clean_flag}"
                with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                    launcher_b, shim_b, meta = runner.build_binaries(
                        work,
                        fx6_round=35,
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

    def test_04_round35_extract_milestones_r35a_ssboot_wbi2_and_bridge(self) -> None:
        runner = _load_closure_module("fx6_brr_r35_msa", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R35_SSBOOT_WBI2_INIT wbi2_magic=WBI2 wbi2_magic_hex=5742493200000000 wbi2_magic_ok=1 wbi2_sections=1399 fx3_rcpt1_magic=FX3RCPT1 fx3_rcpt1_bytes=528 fx3_rcpt1_ok=1 wbi2_hdr_sha256=aaa wbi2_part_sha256=bbb wbi2_sha256_match=1 wbi_resume_bypassed=1 cold_boot_init_verified=1 nflasha5_blkroset=1 pnflasha5_blkroset=1 nflasha5_open_errno=30 pnflasha5_open_errno=30 wbi_erofs_enforced=1 wbi_persistent_writes=0 pm_suspend_disk_rc=-1 proc_udm_write_rc=-30 ssboot_disk_intercepted=1 emmc_write_count=0 r35_init_ok=1 verify_us=156644",
                "FX6_R35_SSBOOT_WBI2_BRIDGE wbi2_magic_ok=1 nflasha5_erofs_ok=1 pnflasha5_erofs_ok=1 fx3_rcpt1_ok=1 wbi_resume_bypassed=1 ssboot_disk_intercepted=1 wbi_persistent_writes=0 emmc_write_count=0 r35_bridge_ok=1",
                "FX6_STAGE_B_R35_BRIDGE round=35 faithful=1 nop_count=0 p12_wlan=1 wf12_00342260_immune=1 p10_keymap=1 p4_nd_clear=1 p11_xlr_h1=1 lang=schinese bk4_lang=0x19 enum=0x2b45_CHINESE_SIMPLIFIED font_bank=23 str_bank=19 ssboot_wbi2_ro_lock=1 blkroset_nflasha5=1 powerloss_100cycle_rsv=1 slot1_bodydata_204_floor=1 c2pa_100_ceiling=1 wpa2_wpa3_enforced=1 emmc_write_count=0",
                "FX6_R35_LANG_TELEMETRY reason=pump lang=schinese bk4_lang_id=0x02cf019c bk4_lang_val=0x19 gpe_fb=0 wbi2_magic_ok=1 nflasha5_erofs_ok=1 pnflasha5_erofs_ok=1 fx3_rcpt1_ok=1 r35_bridge_ok=1 realhw_ssboot_wbi2_powerloss_slot1_ufu=1 emmc_write_count=0 subst_color=0 subst_image=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        r35 = ms["r35_telemetry"]
        self.assertIsNotNone(r35)
        self.assertEqual(r35["ssboot_wbi2_init"]["wbi2_magic_ok"], 1)
        self.assertEqual(r35["ssboot_wbi2_init"]["nflasha5_open_errno"], 30)
        self.assertEqual(r35["ssboot_wbi2_init"]["pnflasha5_open_errno"], 30)
        self.assertEqual(r35["ssboot_wbi2_init"]["pm_suspend_disk_rc"], -1)
        self.assertEqual(r35["ssboot_wbi2_bridge"]["r35_bridge_ok"], 1)
        self.assertEqual(r35["stage_b_bridge"]["round"], 35)
        self.assertEqual(r35["lang_telemetry"]["gpe_fb"], 0)

    def test_05_round35_extract_milestones_r35b_powerloss_100cycle(self) -> None:
        runner = _load_closure_module("fx6_brr_r35_msb", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R35_POWERLOSS_100CYCLE encwfistop_sym_ok=1 cycles_completed=100 cycles_passed=100 rsv_salvaged_cycles=100 tmpfs_evaporated_cycles=100 eh1_under_50us_cycles=100 eh1_avg_ns=7669 eh1_max_ns=14992 eh1_max_us=15 brownout_mv=6300 brownout_threshold_mv=6350 rsv_clip=C0003.RSV mxf_clip=C0003.MXF mediapro_xml_ok=1 h0_wbi_sha256=ccc h3_wbi_sha256=ccc wbi2_h0_eq_h3=1 h0_im_sha256=ddd h3_im_sha256=ddd h3_surfaces_matched=16 h3_surfaces_total=16 h0_eq_h3=1 drift_bits=0 orig_residual_count=0 p15_ro_erofs=1 emmc_write_count=0 r35b_ok=1 verify_us=32075716",
                "FX6_R35_POWERLOSS_RC=0",
                "FX6_R35_POWERLOSS_100CYCLE_EXIT rc=0 emmc_write_count=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        r35 = ms["r35_telemetry"]
        self.assertIsNotNone(r35)
        self.assertEqual(r35["powerloss_rc"], 0)
        b = r35["powerloss_100cycle"]
        self.assertEqual(b["cycles_passed"], 100)
        self.assertEqual(b["rsv_salvaged_cycles"], 100)
        self.assertEqual(b["tmpfs_evaporated_cycles"], 100)
        self.assertEqual(b["eh1_under_50us_cycles"], 100)
        self.assertLess(b["eh1_max_us"], 50)
        self.assertEqual(b["h3_surfaces_matched"], 16)
        self.assertEqual(b["wbi2_h0_eq_h3"], 1)
        self.assertEqual(b["drift_bits"], 0)
        self.assertEqual(b["r35b_ok"], 1)

    def test_06_round35_extract_milestones_r35c_slot1_ufu_c2pa_ceiling(self) -> None:
        runner = _load_closure_module("fx6_brr_r35_msc", "build_and_run_round.py")
        serial = "\n".join(
            [
                "Linux version 4.9.337-scel+ #1 SMP PREEMPT",
                "FX6_R35_SLOT1_UFU_C2PA bodydata_path=/mnt/sd/BODYDATA.DAT bodydata_expected_bytes=811876768 ufu_magic_ok=1 stage_b_aborted=1 stock_fx3_booted=1 bypass_ns=34000 bypass_us=34 bypass_budget_us=100 bypass_under_100us=1 fx3_expected_model_id=0x91030080 fx3_0x91030080_valid=1 ver_202_rejected=1 ver_202_reject_rc=-22 led_7l_7s_prevented=1 ver_204_floor_ok=1 slot2_rejected=1 slot2_reject_rc=-18 dup_bodydata_rejected=1 dup_bodydata_reject_rc=-17 c2pa_100_accepted=1 c2pa_100_count=100 c2pa_100_rc=0 c2pa_101_rejected=1 c2pa_101_count=101 c2pa_101_rc=-7 p12_cert_erofs=1 p12_cert_errno=30 c2pa_sha256_before=eee c2pa_sha256_after=eee c2pa_sha256_match=1 c2pa_cert_writes=0 wep_rc=-93 wpa1_rc=-93 ipsec_rc=-93 wpa2_rc=0 wpa3_rc=0 deprecated_wlan_blocked=1 wpa2_wpa3_enforced=1 emmc_write_count=0 r35c_ok=1 verify_us=5452",
                "FX6_R35_SLOT1_UFU_RC=0",
                "FX6_R35_SLOT1_UFU_C2PA_EXIT rc=0 emmc_write_count=0",
            ]
        )
        ms = runner.extract_milestones(serial)
        r35 = ms["r35_telemetry"]
        self.assertIsNotNone(r35)
        self.assertEqual(r35["slot1_ufu_rc"], 0)
        c = r35["slot1_ufu_c2pa"]
        self.assertEqual(c["ver_202_reject_rc"], -22)
        self.assertEqual(c["slot2_reject_rc"], -18)
        self.assertEqual(c["dup_bodydata_reject_rc"], -17)
        self.assertEqual(c["bypass_under_100us"], 1)
        self.assertEqual(c["c2pa_100_accepted"], 1)
        self.assertEqual(c["c2pa_101_rejected"], 1)
        self.assertEqual(c["c2pa_101_rc"], -7)
        self.assertEqual(c["wpa2_wpa3_enforced"], 1)
        self.assertEqual(c["r35c_ok"], 1)

    def test_07_round35_stage_a_overlay_ssboot_wbi2_big6_mocked_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r35_ovl_a", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            parent_cpio, fp, fv, fb, fake_run, jit_meta = _build_mock_cpio_and_fakes(runner, tmp_dir)
            for clean_flag in ("0", "1"):
                work = tmp_dir / f"r35_a_{clean_flag}"
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
                        sd_manifest_mode="valid", lang="schinese", shim_bytes=b"SHIM",
                    )
                init_out = rep["init"].decode("utf-8")
                self.assertNotIn("--r35-powerloss-100cycle", init_out)
                self.assertNotIn("--r35-slot1-ufu-c2pa", init_out)
                self.assertIn("--sd-gate", init_out)
                self.assertIn("etc/fx6_stage_r35", add)
                self.assertIn("r35_mode=ssboot_wbi2_big6", add["etc/fx6_stage_r35"][0].decode("utf-8"))
                self.assertTrue(meta["r35_enabled"])
                self.assertEqual(meta["r35"]["r35_mode"], "ssboot_wbi2_big6")
                self.assertEqual(meta["r35"]["wbi2_partition"], "/dev/nflasha5")
                self.assertEqual(meta["r35"]["wbi2_magic_hex"], "5742493200000000")
                self.assertEqual(meta["r35"]["wbi2_sections"], 1399)

    def test_08_round35_stage_a_overlay_powerloss_100cycle_mocked_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r35_ovl_b", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            parent_cpio, fp, fv, fb, fake_run, jit_meta = _build_mock_cpio_and_fakes(runner, tmp_dir)
            for clean_flag in ("0", "1"):
                work = tmp_dir / f"r35_b_{clean_flag}"
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
                        enable_r35=True, r35_mode="powerloss_100cycle_rsv",
                        sd_manifest_mode="valid", lang="en", shim_bytes=b"SHIM",
                    )
                init_out = rep["init"].decode("utf-8")
                self.assertIn("/usr/bin/fx6-stage-a-verify --r35-powerloss-100cycle", init_out)
                self.assertIn("FX6_R35_POWERLOSS_100CYCLE_EXIT", init_out)
                self.assertEqual(meta["r35"]["r35_mode"], "powerloss_100cycle_rsv")
                self.assertEqual(meta["r35"]["powerloss_cycles"], 100)
                self.assertEqual(meta["r35"]["brownout_mv"], 6300)

    def test_09_round35_stage_a_overlay_slot1_ufu_c2pa_mocked_dual_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r35_ovl_c", "build_and_run_round.py")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            parent_cpio, fp, fv, fb, fake_run, jit_meta = _build_mock_cpio_and_fakes(runner, tmp_dir)
            for clean_flag in ("0", "1"):
                work = tmp_dir / f"r35_c_{clean_flag}"
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
                        enable_r35=True, r35_mode="slot1_ufu_c2pa_ceiling",
                        sd_manifest_mode="valid", lang="en", shim_bytes=b"SHIM",
                    )
                init_out = rep["init"].decode("utf-8")
                self.assertIn("/usr/bin/fx6-stage-a-verify --r35-slot1-ufu-c2pa", init_out)
                self.assertIn("FX6_R35_SLOT1_UFU_C2PA_EXIT", init_out)
                self.assertEqual(meta["r35"]["r35_mode"], "slot1_ufu_c2pa_ceiling")
                self.assertEqual(meta["r35"]["bodydata_min_version"], "2.04")
                self.assertEqual(meta["r35"]["c2pa_max_licenses"], 100)

    def test_10_round35_stage_a_overlay_rejects_invalid_r35_mode(self) -> None:
        runner = _load_closure_module("fx6_brr_r35_badmode", "build_and_run_round.py")
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
                        tmp_dir / "bad_r35", parent_cpio, b"BK4NTSC",
                        enable_p10=True, enable_r10=True, enable_p12=True, enable_r28=True,
                        enable_r30=True, r30_mode="peripheral_big6",
                        enable_r31=True, r31_mode="keymap_big6",
                        enable_r32=True, r32_mode="imx510_cube_big6",
                        enable_r33=True, r33_mode="cfexpress_rsv_big6",
                        enable_r34=True, r34_mode="c2pa_tc_gyro_big6",
                        enable_r35=True, r35_mode="invalid_r35_mode",
                        lang="schinese", shim_bytes=b"SHIM",
                    )

    def test_11_round35_summary_json_schema_sanitization_and_audit_flags(self) -> None:
        summary_path = ROUND35_REPORT_DIR / "summary.json"
        self.assertTrue(summary_path.is_file())
        raw = summary_path.read_text(encoding="utf-8")
        for forbidden in ("/Users/", "/Volumes/KAFU2T", "/private/tmp"):
            self.assertNotIn(forbidden, raw)
        data = json.loads(raw)
        self.assertEqual(data["schema"], "fx6-on-fx3-round35-realhw-ssboot-wbi2-powerloss-slot1-ufu-qemu-v1")
        self.assertIn("Linux version 4.9.337-scel+", data["kernel_version"])
        self.assertEqual(set(data["runs"].keys()), set(self.EXPECTED_RUN_KEYS))
        audit = data["r35_realhw_ssboot_wbi2_powerloss_slot1_ufu_audit"]
        self.assertEqual(audit["total_runs"], 3)
        for k in (
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "r35a_wbi2_nflasha5_blkroset_erofs_and_suspend_disk_intercept_verified",
            "r35a_stageb_big6_sid_0a_over_340k_pixels_verified",
            "r35b_100cycle_powerloss_rsv_to_mxf_salvage_verified",
            "r35b_16_of_16_h0_eq_h3_wbi2_zero_drift_verified",
            "r35c_bodydata_204_floor_slot1_uniqueness_and_under_100us_bypass_verified",
            "r35c_c2pa_100_ceiling_and_wpa2_wpa3_enforced_verified",
        ):
            self.assertTrue(audit[k], f"Audit flag {k} must be True")

    def test_12_round35_r35a_ssboot_wbi2_magic_tier0_receipt_and_cold_boot(self) -> None:
        data = json.loads((ROUND35_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        init = data["runs"]["r35a_ssboot_wbi2_big6_schinese"]["r35_telemetry"]["ssboot_wbi2_init"]
        self.assertEqual(init["wbi2_magic"], "WBI2")
        self.assertEqual(str(init["wbi2_magic_hex"]), "5742493200000000")
        self.assertEqual(init["wbi2_magic_ok"], 1)
        self.assertEqual(init["wbi2_sections"], 1399)
        self.assertEqual(init["fx3_rcpt1_magic"], "FX3RCPT1")
        self.assertEqual(init["fx3_rcpt1_bytes"], 528)
        self.assertEqual(init["fx3_rcpt1_ok"], 1)
        self.assertEqual(init["wbi2_sha256_match"], 1)
        self.assertEqual(init["wbi_resume_bypassed"], 1)
        self.assertEqual(init["cold_boot_init_verified"], 1)

    def test_13_round35_r35a_blkroset_erofs_and_suspend_disk_intercept(self) -> None:
        data = json.loads((ROUND35_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        telem = data["runs"]["r35a_ssboot_wbi2_big6_schinese"]["r35_telemetry"]
        init = telem["ssboot_wbi2_init"]
        br = telem["ssboot_wbi2_bridge"]
        self.assertEqual(init["nflasha5_blkroset"], 1)
        self.assertEqual(init["pnflasha5_blkroset"], 1)
        self.assertEqual(init["nflasha5_open_errno"], 30)
        self.assertEqual(init["pnflasha5_open_errno"], 30)
        self.assertEqual(init["wbi_erofs_enforced"], 1)
        self.assertEqual(init["wbi_persistent_writes"], 0)
        self.assertEqual(init["pm_suspend_disk_rc"], -1)
        self.assertEqual(init["proc_udm_write_rc"], -30)
        self.assertEqual(init["ssboot_disk_intercepted"], 1)
        self.assertEqual(init["emmc_write_count"], 0)
        self.assertEqual(init["r35_init_ok"], 1)
        self.assertEqual(br["wbi2_magic_ok"], 1)
        self.assertEqual(br["nflasha5_erofs_ok"], 1)
        self.assertEqual(br["pnflasha5_erofs_ok"], 1)
        self.assertEqual(br["fx3_rcpt1_ok"], 1)
        self.assertEqual(br["r35_bridge_ok"], 1)

    def test_14_round35_r35a_stage_b_13_sha256_and_big6_render_invariants(self) -> None:
        data = json.loads((ROUND35_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        r35a = data["runs"]["r35a_ssboot_wbi2_big6_schinese"]
        self.assertEqual(r35a["round"], 35)
        self.assertEqual(r35a["r35_mode"], "ssboot_wbi2_big6")
        self.assertEqual(r35a["target_presenter"], "31procam_big6_menu_home_presenter")
        self.assertEqual(r35a["target_sid"], "0x0a")
        self.assertEqual(r35a["nop_count"], 0)
        self.assertEqual(r35a["crashes"], 0)
        self.assertEqual(r35a["emmc_write_count"], 0)
        self.assertGreaterEqual(r35a["total_threads_seen"], 160)
        self.assertEqual(r35a["faithful_invariants"]["FX6_NATIVE_FAITHFUL"], 1)
        self.assertEqual(r35a["stage_b"]["manifest_count"], 13)
        self.assertEqual(len(r35a["stage_b"]["manifest_items"]), 13)
        for item in r35a["stage_b"]["manifest_items"]:
            self.assertEqual(len(item["sha256"]), 64)
            int(item["sha256"], 16)
        lt = r35a["r35_telemetry"]["lang_telemetry"]
        self.assertEqual(lt["gpe_fb"], 0)
        self.assertEqual(lt["subst_color"], 0)
        self.assertEqual(lt["subst_image"], 0)
        self.assertEqual(lt["r35_bridge_ok"], 1)
        self.assertGreater(r35a["gpe0_readback"]["nonzero_pixels"], 340000)

    def test_15_round35_r35a_png_receipts_under_28kib_and_dimensions(self) -> None:
        data = json.loads((ROUND35_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        exports = data["runs"]["r35a_ssboot_wbi2_big6_schinese"]["png_exports"]
        for key in ("alpha_png", "composited_png"):
            p = REPO_ROOT / exports[key]["path"]
            self.assertTrue(p.is_file(), f"Missing Round 35 PNG: {p}")
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

    def test_16_round35_r35b_100cycle_lifecycle_and_tmpfs_evaporation(self) -> None:
        data = json.loads((ROUND35_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        r35b = data["runs"]["r35b_powerloss_100cycle_rsv"]
        self.assertEqual(r35b["round"], 35)
        self.assertEqual(r35b["r35_mode"], "powerloss_100cycle_rsv")
        self.assertEqual(r35b["crashes"], 0)
        self.assertEqual(r35b["emmc_write_count"], 0)
        self.assertTrue(r35b["gpe0_readback"]["skipped_stock_fx3_mode"])
        self.assertEqual(r35b["r35_telemetry"]["powerloss_rc"], 0)
        b = r35b["r35_telemetry"]["powerloss_100cycle"]
        self.assertEqual(b["encwfistop_sym_ok"], 1)
        self.assertEqual(b["cycles_completed"], 100)
        self.assertEqual(b["cycles_passed"], 100)
        self.assertEqual(b["tmpfs_evaporated_cycles"], 100)
        self.assertEqual(b["r35b_ok"], 1)

    def test_17_round35_r35b_6v3_brownout_rsv_to_mxf_salvage_and_eh1_under_50us(self) -> None:
        data = json.loads((ROUND35_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        b = data["runs"]["r35b_powerloss_100cycle_rsv"]["r35_telemetry"]["powerloss_100cycle"]
        self.assertEqual(b["brownout_mv"], 6300)
        self.assertLessEqual(b["brownout_mv"], b["brownout_threshold_mv"])
        self.assertEqual(b["rsv_clip"], "C0003.RSV")
        self.assertEqual(b["mxf_clip"], "C0003.MXF")
        self.assertEqual(b["rsv_salvaged_cycles"], 100)
        self.assertEqual(b["mediapro_xml_ok"], 1)
        self.assertEqual(b["eh1_under_50us_cycles"], 100)
        self.assertLess(b["eh1_max_us"], 50)

    def test_18_round35_r35b_16_of_16_h0_eq_h3_wbi2_zero_drift_seal(self) -> None:
        data = json.loads((ROUND35_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        b = data["runs"]["r35b_powerloss_100cycle_rsv"]["r35_telemetry"]["powerloss_100cycle"]
        self.assertEqual(len(b["h0_wbi_sha256"]), 64)
        self.assertEqual(b["h0_wbi_sha256"], b["h3_wbi_sha256"])
        self.assertEqual(b["wbi2_h0_eq_h3"], 1)
        self.assertEqual(len(b["h0_im_sha256"]), 64)
        self.assertEqual(b["h0_im_sha256"], b["h3_im_sha256"])
        self.assertEqual(b["h3_surfaces_matched"], 16)
        self.assertEqual(b["h3_surfaces_total"], 16)
        self.assertEqual(b["h0_eq_h3"], 1)
        self.assertEqual(b["drift_bits"], 0)
        self.assertEqual(b["orig_residual_count"], 0)
        self.assertEqual(b["p15_ro_erofs"], 1)
        self.assertEqual(b["emmc_write_count"], 0)

    def test_19_round35_r35c_bodydata_204_floor_and_202_reject(self) -> None:
        data = json.loads((ROUND35_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        r35c = data["runs"]["r35c_slot1_ufu_c2pa_ceiling"]
        self.assertEqual(r35c["round"], 35)
        self.assertEqual(r35c["r35_mode"], "slot1_ufu_c2pa_ceiling")
        self.assertEqual(r35c["crashes"], 0)
        self.assertEqual(r35c["emmc_write_count"], 0)
        self.assertTrue(r35c["gpe0_readback"]["skipped_stock_fx3_mode"])
        self.assertEqual(r35c["r35_telemetry"]["slot1_ufu_rc"], 0)
        c = r35c["r35_telemetry"]["slot1_ufu_c2pa"]
        self.assertEqual(c["ver_202_rejected"], 1)
        self.assertEqual(c["ver_202_reject_rc"], -22)
        self.assertEqual(c["led_7l_7s_prevented"], 1)
        self.assertEqual(c["ver_204_floor_ok"], 1)
        self.assertEqual(c["r35c_ok"], 1)

    def test_20_round35_r35c_slot1_uniqueness_and_under_100us_ufu_bypass(self) -> None:
        data = json.loads((ROUND35_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        c = data["runs"]["r35c_slot1_ufu_c2pa_ceiling"]["r35_telemetry"]["slot1_ufu_c2pa"]
        self.assertEqual(c["bodydata_path"], "/mnt/sd/BODYDATA.DAT")
        self.assertEqual(c["bodydata_expected_bytes"], 811876768)
        self.assertEqual(c["ufu_magic_ok"], 1)
        self.assertEqual(c["stage_b_aborted"], 1)
        self.assertEqual(c["stock_fx3_booted"], 1)
        self.assertEqual(c["bypass_under_100us"], 1)
        self.assertLess(c["bypass_us"], 100)
        self.assertEqual(c["fx3_expected_model_id"], "0x91030080")
        self.assertEqual(c["fx3_0x91030080_valid"], 1)
        self.assertEqual(c["slot2_rejected"], 1)
        self.assertEqual(c["slot2_reject_rc"], -18)
        self.assertEqual(c["dup_bodydata_rejected"], 1)
        self.assertEqual(c["dup_bodydata_reject_rc"], -17)

    def test_21_round35_r35c_c2pa_100_license_ceiling_and_p12_erofs(self) -> None:
        data = json.loads((ROUND35_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        c = data["runs"]["r35c_slot1_ufu_c2pa_ceiling"]["r35_telemetry"]["slot1_ufu_c2pa"]
        self.assertEqual(c["c2pa_100_accepted"], 1)
        self.assertEqual(c["c2pa_100_count"], 100)
        self.assertEqual(c["c2pa_100_rc"], 0)
        self.assertEqual(c["c2pa_101_rejected"], 1)
        self.assertEqual(c["c2pa_101_count"], 101)
        self.assertEqual(c["c2pa_101_rc"], -7)
        self.assertEqual(c["p12_cert_erofs"], 1)
        self.assertEqual(c["p12_cert_errno"], 30)
        self.assertEqual(c["c2pa_sha256_before"], c["c2pa_sha256_after"])
        self.assertEqual(c["c2pa_sha256_match"], 1)
        self.assertEqual(c["c2pa_cert_writes"], 0)

    def test_22_round35_r35c_deprecated_wlan_security_blocked(self) -> None:
        data = json.loads((ROUND35_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        c = data["runs"]["r35c_slot1_ufu_c2pa_ceiling"]["r35_telemetry"]["slot1_ufu_c2pa"]
        self.assertLess(c["wep_rc"], 0)
        self.assertLess(c["wpa1_rc"], 0)
        self.assertLess(c["ipsec_rc"], 0)
        self.assertEqual(c["wpa2_rc"], 0)
        self.assertEqual(c["wpa3_rc"], 0)
        self.assertEqual(c["deprecated_wlan_blocked"], 1)
        self.assertEqual(c["wpa2_wpa3_enforced"], 1)
        self.assertEqual(c["emmc_write_count"], 0)

    def test_23_round35_stage_b_bridge_mechanisms_and_bench_boundaries(self) -> None:
        data = json.loads((ROUND35_REPORT_DIR / "summary.json").read_text(encoding="utf-8"))
        mech = data["realhw_mechanisms_verified"]
        self.assertEqual(mech["ssboot_wbi2_coldboot_and_erofs_lock"]["r35_init_ok"], 1)
        self.assertEqual(mech["ssboot_wbi2_stage_b_bridge"]["r35_bridge_ok"], 1)
        self.assertEqual(mech["powerloss_100cycle_rsv_salvage_and_h0_eq_h3"]["r35b_ok"], 1)
        self.assertEqual(mech["slot1_ufu_204_floor_and_c2pa_100_ceiling"]["r35c_ok"], 1)

        br = data["runs"]["r35a_ssboot_wbi2_big6_schinese"]["r35_telemetry"]["stage_b_bridge"]
        for key in (
            "faithful",
            "p12_wlan",
            "wf12_00342260_immune",
            "p10_keymap",
            "p4_nd_clear",
            "p11_xlr_h1",
            "ssboot_wbi2_ro_lock",
            "blkroset_nflasha5",
            "powerloss_100cycle_rsv",
            "slot1_bodydata_204_floor",
            "c2pa_100_ceiling",
            "wpa2_wpa3_enforced",
        ):
            self.assertEqual(br[key], 1, f"Expected stage_b_bridge[{key}]==1")
        self.assertEqual(br["round"], 35)
        self.assertEqual(br["nop_count"], 0)
        self.assertEqual(br["emmc_write_count"], 0)
        self.assertEqual(len(data["unexecuted_physical_camera_bench_boundaries"]), 3)

    def test_24_round35_readme_sanitization_and_no_tmp_or_binary_residue(self) -> None:
        closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn("2026-11-15-round35-realhw-ssboot-wbi2-powerloss-slot1-ufu-qemu", closure_readme)
        self.assertIn("`24` New Round 35 Dual-Mode Unit Tests (`426` Total)", closure_readme)
        r35_readme = (ROUND35_REPORT_DIR / "README.md").read_text(encoding="utf-8")
        for tok in (
            "WBI2",
            "nflasha5",
            "BLKROSET=1",
            "PM_SUSPEND_DISK",
            "C0003.RSV",
            "C0003.MXF",
            "16/16",
            "BODYDATA.DAT",
            ">=2.04",
            "C2PA",
            "WPA2/WPA3",
            "r35a-ssboot-wbi2-big6-schinese",
            "r35b-powerloss-100cycle-rsv",
            "r35c-slot1-ufu-c2pa-ceiling",
        ):
            self.assertIn(tok, r35_readme)
        for forbidden in ("/Users/", "/Volumes/KAFU2T", "/private/tmp"):
            self.assertNotIn(forbidden, r35_readme)
        for folder in (CLOSURE_DIR, ROUND35_REPORT_DIR):
            for p in folder.rglob("*"):
                if p.is_file():
                    self.assertNotIn(p.suffix, {".cpio", ".so", ".o", ".img", ".qcow2", ".pyc"})


if __name__ == "__main__":
    unittest.main()
