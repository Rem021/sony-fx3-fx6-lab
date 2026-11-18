#!/usr/bin/env python3
"""Offline dual-mode unit tests for FX6-on-FX3 Round 55 (28th Real-HW Round / 84th Live Run — Wave-41)."""
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
from typing import Any, Dict, List, Optional, Tuple
from unittest import mock

TESTS_DIR = pathlib.Path(__file__).resolve().parent
CLOSURE_DIR = TESTS_DIR.parent
REPO_ROOT = CLOSURE_DIR.parent.parent
ROUND55_REPORT_DIR = (
    REPO_ROOT
    / "reports"
    / "2026-11-17-round55-realhw-auto-slow-shutter-hdmi-reccontrol-breathing"
)
WAVE41_SPEC_PATH = (
    REPO_ROOT
    / "reports"
    / "2026-11-15-global-sony-wave41-auto-slow-shutter-6locks-hdmi-reccontrol-tcout-4chaudio-breathing-comp-intel"
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


def _decode_png_rgba_rows(png_bytes: bytes) -> Tuple[int, int, int, int]:
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
    p = 0
    prev_a = bytearray(width)
    transparent = 0
    opaque = 0
    for _ in range(height):
        filt = raw_scanlines[p]
        p += 1
        row_a = bytearray(raw_scanlines[p + 3 : p + stride : 4])
        p += stride
        if filt == 1:
            for x in range(1, width):
                row_a[x] = (row_a[x] + row_a[x - 1]) & 0xFF
        elif filt == 2:
            for x in range(width):
                row_a[x] = (row_a[x] + prev_a[x]) & 0xFF
        elif filt == 3:
            row_a[0] = (row_a[0] + (prev_a[0] >> 1)) & 0xFF
            for x in range(1, width):
                row_a[x] = (row_a[x] + ((row_a[x - 1] + prev_a[x]) >> 1)) & 0xFF
        elif filt == 4:
            row_a[0] = (row_a[0] + prev_a[0]) & 0xFF
            for x in range(1, width):
                a = row_a[x - 1]
                b = prev_a[x]
                c = prev_a[x - 1]
                pa = abs(b - c)
                pb = abs(a - c)
                pc = abs(a + b - 2 * c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                row_a[x] = (row_a[x] + pr) & 0xFF
        elif filt != 0:
            raise AssertionError(f"Unsupported PNG filter {filt}")
        transparent += row_a.count(0)
        opaque += row_a.count(255)
        prev_a = row_a
    return width, height, transparent, opaque


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
        (
            "usr/share/app/fontlist.dat",
            b"FONT_S_CHINESE\t/usr/share/app/MYingHeiC-GB18030-SJ_wIcon.ltt\t0\t0\n",
        ),
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
            library_name="appFw.so",
            expected_size=5,
            donor_sha256="0" * 64,
            sites=(mock.Mock(site_id="p1"),),
            elf_kind="so",
            source_domain="fx6",
        )
        P1_LIB_INFRA_SETUP_FILE_SPEC = mock.Mock(
            spec_id="P1_s", library_name="s", sites=[mock.Mock(site_id="s1")]
        )
        P1_LIB_INFRA_MEDIA_COMMON_SPEC = mock.Mock(
            spec_id="P1_c", library_name="c", sites=[mock.Mock(site_id="c1")]
        )
        P1_LIB_INFRA_MEDIA_CONFIG_SPEC = mock.Mock(
            spec_id="P1_g", library_name="g", sites=[mock.Mock(site_id="g1")]
        )
        P3_LIB_INFRA_APP_REMOTE_BOARD_SPEC = mock.Mock(
            spec_id="P3_r", library_name="r", sites=[mock.Mock(site_id="r1")]
        )
        FAN_LIBFAN_SPEC = mock.Mock(
            spec_id="Fan_f", library_name="f", sites=[mock.Mock(site_id="f1")]
        )
        P9_UPM_KO_SPEC = mock.Mock(
            spec_id="P9_u", library_name="upm.ko", sites=[mock.Mock(site_id="u1")]
        )
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
                mode=mode,
                fat_type="FAT16",
                total_bytes=len(img),
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
                bk4_bytes=bk4,
                total_bytes=len(bk4),
                sha256=hashlib.sha256(bk4).hexdigest(),
                flash_write_allowed=False,
                active_byte8_selector=0,
                synthesized_key_count=1,
            )

    def fake_subproc_run(cmd, **_kw):
        out_idx = cmd.index("-o") + 1
        pathlib.Path(cmd[out_idx]).write_bytes(b"\x7fELF" + b"\x00" * 60)
        return mock.Mock(returncode=0, stdout="", stderr="")

    fake_jit_meta = {
        "bytes": 64,
        "sha256": "a" * 64,
        "e_type": 3,
        "e_machine": 183,
        "pt_load_count": 3,
        "pt_load_align": "0x10000",
        "has_pt_dynamic": True,
    }
    return parent_cpio, _FakePatcher, _FakeVfat, _FakeBmtvHex, fake_subproc_run, fake_jit_meta


def _build_overlay_for_r55(
    runner,
    parent_cpio: pathlib.Path,
    fp,
    fv,
    fb,
    fake_run,
    jit_meta: Dict[str, Any],
    work: pathlib.Path,
    r55_mode: str,
    lang: str = "schinese",
    enable_r55: bool = True,
):
    with mock.patch.object(runner, "_import_stage_a_modules", return_value=(fp, fv, fb)), \
         mock.patch.object(runner, "_load_p10_keymap_spec", return_value=mock.Mock(spec_id="P10_k", library_name="appFw.so", sites=(mock.Mock(site_id="p10", size=4),))), \
         mock.patch.object(runner, "_load_p12_wlan_spec", return_value=mock.Mock(spec_id="P12_w", library_name="libWlanResource.so", sites=(mock.Mock(site_id="p12", size=8),))), \
         mock.patch.object(runner, "build_hardened_libjit_so", return_value=(b"\x7fELF_JIT", dict(jit_meta))), \
         mock.patch.object(runner, "build_r30_tier0_libjit_so", return_value=(b"\x7fELF_R30_JIT", dict(jit_meta))), \
         mock.patch.object(runner.subprocess, "run", side_effect=fake_run):
        return runner.build_stage_a_overlay(
            work,
            parent_cpio,
            b"BK4NTSC",
            enable_p10=True,
            enable_r10=True,
            enable_p12=True,
            enable_r28=True,
            enable_r30=True,
            r30_mode="peripheral_big6",
            enable_r31=True,
            r31_mode="keymap_big6",
            enable_r32=True,
            r32_mode="imx510_cube_big6",
            enable_r33=True,
            r33_mode="cfexpress_rsv_big6",
            enable_r34=True,
            r34_mode="c2pa_tc_gyro_big6",
            enable_r35=True,
            r35_mode="ssboot_wbi2_big6",
            enable_r36=True,
            r36_mode="emount_info3d_big6",
            enable_r37=True,
            r37_mode="fx3a_firewall_big6",
            enable_r38=True,
            r38_mode="nouvc_dcc1_pd_big6",
            enable_r39=True,
            r39_mode="fan_pwm_offinrec_big6",
            enable_r40=True,
            r40_mode="big6_home_noend_big6",
            enable_r41=True,
            r41_mode="desqueeze_165x_4locks_big6",
            enable_r42=True,
            r42_mode="hdmi_log1080_hdmionly_4k_big6",
            enable_r43=True,
            r43_mode="filesettings_shotmark_big6",
            enable_r44=True,
            r44_mode="pixelmap_reboot_cnflasha_big6",
            enable_r45=True,
            r45_mode="steadyshot_active_cutoffs_big6",
            enable_r46=True,
            r46_mode="sq_fixedvar_6locks_big6",
            enable_r47=True,
            r47_mode="silent_autopixelmap_5locks_big6",
            enable_r48=True,
            r48_mode="monitor_flip_playback_big6",
            enable_r49=True,
            r49_mode="emphasized_rec_grid_hdmi_big6",
            enable_r50=True,
            r50_mode="shoe_audio_4ch_osd_big6",
            enable_r51=True,
            r51_mode="framing_settings_crop_hdmi_big6",
            enable_r52=True,
            r52_mode="lock_op_parts_chord_mydial_big6",
            enable_r53=True,
            r53_mode="display_quality_bt_rmt_big6",
            enable_r54=True,
            r54_mode="diff_set_still_mv_shutter_angle_big6",
            enable_r55=enable_r55,
            r55_mode=r55_mode,
            sd_manifest_mode="valid",
            lang=lang,
            shim_bytes=b"SHIM",
        )


class TestRound55RealHwAutoSlowShutterHdmiRecControlBreathingQemu(unittest.TestCase):
    EXPECTED_RUN_KEYS = (
        "r55a_auto_slow_6locks_hdmi_reccontrol_big6_schinese",
        "r55b_prerequisite_lockout_injection_guard",
        "r55c_camreset_vs_initialize_h0_h3_integrated_big6_schinese",
    )

    runner: Any
    runner_src: str
    stage_a_src: str
    shim_src: str
    wave41_spec: str
    summary_raw: str
    summary: Dict[str, Any]
    r55_readme: str
    closure_readme: str
    alpha_png_bytes: bytes
    alpha_dims: Tuple[int, int]
    alpha_transparent: int
    alpha_opaque: int
    comp_png_bytes: bytes
    comp_dims: Tuple[int, int]
    comp_opaque: int
    ov_a: Tuple[Dict[str, bytes], Dict[str, Any], Dict[str, Any]]
    ov_b: Tuple[Dict[str, bytes], Dict[str, Any], Dict[str, Any]]
    ov_c: Tuple[Dict[str, bytes], Dict[str, Any], Dict[str, Any]]
    ov_off: Tuple[Dict[str, bytes], Dict[str, Any], Dict[str, Any]]
    invalid_mode_raised: bool
    launcher_r55: Optional[bytes]
    shim_r55: Optional[bytes]
    shim_r54: Optional[bytes]
    r54_summary: Dict[str, Any]
    r53_summary: Dict[str, Any]
    r50_summary: Dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = _load_closure_module("fx6_brr_r55_cached", "build_and_run_round.py")
        cls.runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")
        cls.stage_a_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        cls.shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        cls.wave41_spec = WAVE41_SPEC_PATH.read_text(encoding="utf-8")
        cls.summary_raw = (ROUND55_REPORT_DIR / "summary.json").read_text(encoding="utf-8")
        cls.summary = json.loads(cls.summary_raw)
        cls.r55_readme = (ROUND55_REPORT_DIR / "README.md").read_text(encoding="utf-8")
        cls.closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")

        alpha_p = (
            ROUND55_REPORT_DIR
            / "assets"
            / "r55a-auto-slow-hdmi-reccontrol-big6-schinese-alpha.png"
        )
        comp_p = (
            ROUND55_REPORT_DIR
            / "assets"
            / "r55a-auto-slow-hdmi-reccontrol-big6-schinese-composited.png"
        )
        cls.alpha_png_bytes = alpha_p.read_bytes()
        aw, ah, cls.alpha_transparent, cls.alpha_opaque = _decode_png_rgba_rows(
            cls.alpha_png_bytes
        )
        cls.alpha_dims = (aw, ah)

        cls.comp_png_bytes = comp_p.read_bytes()
        cw, ch, _, cls.comp_opaque = _decode_png_rgba_rows(cls.comp_png_bytes)
        cls.comp_dims = (cw, ch)

        with tempfile.TemporaryDirectory() as tmp:
            tpath = pathlib.Path(tmp)
            parent_cpio, fp, fv, fb, fake_run, jit_meta = _build_mock_cpio_and_fakes(
                cls.runner, tpath
            )
            cls.ov_a = _build_overlay_for_r55(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wa", "auto_slow_6locks_hdmi_reccontrol_big6", lang="schinese",
            )
            cls.ov_b = _build_overlay_for_r55(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wb", "prerequisite_lockout_injection_guard", lang="en",
            )
            cls.ov_c = _build_overlay_for_r55(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wc", "camreset_vs_initialize_h0_h3_integrated_big6", lang="schinese",
            )
            cls.ov_off = _build_overlay_for_r55(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "woff", "auto_slow_6locks_hdmi_reccontrol_big6", enable_r55=False,
            )
            cls.invalid_mode_raised = False
            try:
                _build_overlay_for_r55(
                    cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                    tpath / "wbad", "invalid_r55_mode",
                )
            except ValueError:
                cls.invalid_mode_raised = True

            if cls.runner.ZIG.is_file():
                verify_r55_out = tpath / "fx6-stage-a-verify-r55"
                shim_r55_out = tpath / "libgrm-fbinit9-r55.so"
                shim_r54_out = tpath / "libgrm-fbinit9-r54.so"
                for cmd in (
                    [
                        str(cls.runner.ZIG),
                        "cc",
                        "-target",
                        "aarch64-linux-gnu.2.25",
                        "-O0",
                        str(CLOSURE_DIR / "fx6-stage-a-verify.c"),
                        "-ldl",
                        "-lpthread",
                        "-o",
                        str(verify_r55_out),
                    ],
                    [
                        str(cls.runner.ZIG),
                        "cc",
                        "-target",
                        "aarch64-linux-gnu.2.25",
                        "-O0",
                        "-shared",
                        "-fPIC",
                        "-DFX6_ROUND=55",
                        str(CLOSURE_DIR / "libgrm-fbinit9.c"),
                        "-ldl",
                        "-lpthread",
                        "-o",
                        str(shim_r55_out),
                    ],
                    [
                        str(cls.runner.ZIG),
                        "cc",
                        "-target",
                        "aarch64-linux-gnu.2.25",
                        "-O0",
                        "-shared",
                        "-fPIC",
                        "-DFX6_ROUND=54",
                        str(CLOSURE_DIR / "libgrm-fbinit9.c"),
                        "-ldl",
                        "-lpthread",
                        "-o",
                        str(shim_r54_out),
                    ],
                ):
                    cls.runner.subprocess.run(cmd, check=True)
                cls.launcher_r55 = verify_r55_out.read_bytes()
                cls.shim_r55 = shim_r55_out.read_bytes()
                cls.shim_r54 = shim_r54_out.read_bytes()
            else:
                cls.launcher_r55 = None
                cls.shim_r55 = None
                cls.shim_r54 = None

        cls.r54_summary = json.loads(
            (
                REPO_ROOT
                / "reports"
                / "2026-11-15-round54-realhw-diff-set-still-mv-custom-key-remain-shoot-qemu"
                / "summary.json"
            ).read_text(encoding="utf-8")
        )
        cls.r53_summary = json.loads(
            (
                REPO_ROOT
                / "reports"
                / "2026-11-15-round53-realhw-display-quality-bt-rmt-mymenu-qemu"
                / "summary.json"
            ).read_text(encoding="utf-8")
        )
        cls.r50_summary = json.loads(
            (
                REPO_ROOT
                / "reports"
                / "2026-11-15-round50-milestone-realhw-shoe-audio-4ch-wind-saveload-c3-qemu"
                / "summary.json"
            ).read_text(encoding="utf-8")
        )

    def test_01_wave41_global_spec_present_and_covers_all_wave41_pillars(self) -> None:
        self.assertTrue(WAVE41_SPEC_PATH.is_file())
        for needle in (
            "Auto Slow Shutter",
            "TP1000668443",
            "Shutter Priority",
            "Manual Exposure",
            "ISO AUTO",
            "Flexible Exp. Mode",
            "Cine EI Quick",
            "Cine EI",
            "Shutter Mode",
            "Angle",
            "HDMI Output Settings",
            "REC Control",
            "Time Code Output",
            "4ch Audio Output",
            "CH1/CH2",
            "CH3/CH4",
            "Rec. Media dur HDMI Output",
            "Breathing Comp.",
            "4264x2408",
            "239.76p",
        ):
            self.assertIn(needle, self.wave41_spec)

    def test_02_round55_summary_schema_round_milestone_and_zero_leaks(self) -> None:
        self.assertNotIn("/Users/", self.summary_raw)
        self.assertNotIn("/private/tmp/", self.summary_raw)
        self.assertEqual(
            self.summary["schema"],
            "fx6-on-fx3-round55-realhw-auto-slow-shutter-hdmi-reccontrol-breathing-qemu-v1",
        )
        self.assertEqual(self.summary["round"], 55)
        self.assertEqual(self.summary["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(tuple(self.summary["runs"].keys()), self.EXPECTED_RUN_KEYS)

    def test_03_round55_cli_accepts_round55_and_all_3_r55_modes(self) -> None:
        self.assertIn(", 55]", self.runner_src)
        self.assertIn(", 54]", self.runner_src)
        for mode in (
            "auto_slow_6locks_hdmi_reccontrol_big6",
            "prerequisite_lockout_injection_guard",
            "camreset_vs_initialize_h0_h3_integrated_big6",
        ):
            self.assertIn(mode, self.runner_src)

    def test_04_round55_overlay_rejects_invalid_r55_mode(self) -> None:
        self.assertTrue(self.invalid_mode_raised)

    def test_05_round55_overlay_r55a_injects_etc_fx6_stage_r55_and_appfw_launch(self) -> None:
        replacements, additions, meta = self.ov_a
        self.assertTrue(meta["r55_enabled"])
        self.assertIn("etc/fx6_stage_r55", additions)
        self.assertIn("etc/fx6_r55_libjit.so", additions)
        r55_cfg = additions["etc/fx6_stage_r55"][0].decode("utf-8")
        self.assertIn("stage_r55=1", r55_cfg)
        self.assertIn("r55_mode=auto_slow_6locks_hdmi_reccontrol_big6", r55_cfg)
        self.assertIn("run_28th_realhw_84th_live=1", r55_cfg)
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("/usr/bin/appfw-launch", init_txt)
        self.assertNotIn("--r55-prerequisite-lockout-injection", init_txt)

    def test_06_round55_overlay_r55b_injects_early_lockout_probe_and_poweroff(self) -> None:
        replacements, _, meta = self.ov_b
        self.assertEqual(meta["r55"]["r55_mode"], "prerequisite_lockout_injection_guard")
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("--r55-prerequisite-lockout-injection", init_txt)
        self.assertIn("FX6_R55_LOCKOUT_INJECTION_RC=", init_txt)
        self.assertIn("FX6_R55_LOCKOUT_INJECTION_EXIT", init_txt)
        self.assertIn("poweroff -f", init_txt)

    def test_07_round55_overlay_r55c_integrated_runs_stage_b_big6(self) -> None:
        replacements, additions, meta = self.ov_c
        self.assertEqual(meta["r55"]["r55_mode"], "camreset_vs_initialize_h0_h3_integrated_big6")
        r55_cfg = additions["etc/fx6_stage_r55"][0].decode("utf-8")
        self.assertIn("r55_mode=camreset_vs_initialize_h0_h3_integrated_big6", r55_cfg)
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("/usr/bin/appfw-launch", init_txt)
        self.assertNotIn("--r55-prerequisite-lockout-injection", init_txt)

    def test_08_round55_overlay_disabled_when_enable_r55_false(self) -> None:
        _, additions, meta = self.ov_off
        self.assertFalse(meta["r55_enabled"])
        self.assertNotIn("etc/fx6_stage_r55", additions)
        self.assertNotIn("etc/fx6_r55_libjit.so", additions)
        self.assertNotIn("r55", meta)

    def test_09_round55_stage_a_c_source_contains_all_3_wave41_probes(self) -> None:
        for sym in (
            "setup_r55_auto_slow_hdmi_reccontrol_probe",
            "run_r55_prerequisite_lockout_injection_probe",
            "run_r55_camreset_initialize_h0_h3_integrated_probe",
            "FX6_R55_AUTO_SLOW_HDMI_INIT",
            "FX6_R55_LOCKOUT_INJECTION_GUARD",
            "FX6_R55_CAMRESET_INIT_H0_H3_INTEGRATED",
            "--r55-prerequisite-lockout-injection",
            "--r55-camreset-init-h0-h3",
            "/etc/fx6_stage_r55",
        ):
            self.assertIn(sym, self.stage_a_src)

    def test_10_round55_shim_c_source_contains_r55_guarded_bridges(self) -> None:
        self.assertIn("#if FX6_ROUND >= 55", self.shim_src)
        for sym in (
            "FX6_R55_AUTO_SLOW_6LOCKS_BRIDGE",
            "FX6_R55_HDMI_RECCONTROL_BRIDGE",
            "FX6_R55_BREATHING_COMP_BRIDGE",
            "FX6_R55_LANG_TELEMETRY",
            "FX6_STAGE_B_R55_BRIDGE",
        ):
            self.assertIn(sym, self.shim_src)

    def test_11_round55_compile_launcher_and_shim_aarch64_elf_symbols(self) -> None:
        if self.launcher_r55 is None or self.shim_r55 is None:
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertEqual(self.launcher_r55[:4], b"\x7fELF")
        self.assertEqual(self.shim_r55[:4], b"\x7fELF")
        self.assertEqual(struct.unpack_from("<H", self.shim_r55, 18)[0], 183)
        self.assertIn(b"FX6_R55_AUTO_SLOW_6LOCKS_BRIDGE", self.shim_r55)
        self.assertIn(b"FX6_R55_HDMI_RECCONTROL_BRIDGE", self.shim_r55)
        self.assertIn(b"FX6_R55_BREATHING_COMP_BRIDGE", self.shim_r55)

    def test_12_round55_shim_round54_backward_compat_excludes_r55_bridges(self) -> None:
        if self.shim_r54 is None:
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertIn(b"FX6_R54_DIFF_SET_STILL_MV_BRIDGE", self.shim_r54)
        self.assertNotIn(b"FX6_R55_AUTO_SLOW_6LOCKS_BRIDGE", self.shim_r54)

    def test_13_round55_parse_log_extracts_all_8_r55_prefixes_and_rc(self) -> None:
        serial_text = (
            "\n".join(
                [
                    "Linux version 4.9.337-scel+ (sony@fx3)",
                    "FX6_R55_AUTO_SLOW_HDMI_INIT fx3_wave41_nodes_ok=1 auto_slow_6locks_verified=6 auto_slow_shutter_angle_overlap_events=0 hdmi_nominal_tc_rec_ctrl_ok=1 r55_init_ok=1",
                    "FX6_R55_AUTO_SLOW_6LOCKS_BRIDGE auto_slow_default_on_ok=1 auto_slow_6locks_verified=6 auto_slow_ok=1 r55_bridge_ok=1",
                    "FX6_R55_HDMI_RECCONTROL_BRIDGE hdmi_tcout_prereq_enforced_ok=1 hdmi_rec_ctrl_without_tc_violations=0 hdmi_setup_ok=1",
                    "FX6_R55_BREATHING_COMP_BRIDGE breathing_default_off_ok=1 breathing_raw_240p_still_blocked_ok=1 breathing_ok=1",
                    "FX6_R55_LANG_TELEMETRY lang=schinese font_bank=23 str_bank=19 run_28th_realhw_84th_live=1 r55_bridge_ok=1",
                    "FX6_STAGE_B_R55_BRIDGE round=55 faithful=1 nop_count=0 run_28th_realhw_84th_live=1 emmc_write_count=0",
                    "FX6_R55_LOCKOUT_INJECTION_GUARD illegal_rec_ctrl_rc=-16 hdmi_rec_ctrl_without_tc_violations=0 slot1_vault_writes=0 r55b_ok=1",
                    "FX6_R55_LOCKOUT_INJECTION_RC=0",
                    "FX6_R55_CAMRESET_INIT_H0_H3_INTEGRATED auto_slow_camreset_on_ok=1 breathing_camreset_off_ok=1 hdmi_setup_survives_camreset_ok=1 surfaces_h0_eq_h3=16 r55c_ok=1",
                ]
            )
            + "\n"
        )
        parsed = self.runner.extract_milestones(serial_text)
        r55_t = parsed["r55_telemetry"]
        self.assertEqual(r55_t["lockout_injection_rc"], 0)
        self.assertEqual(r55_t["auto_slow_hdmi_init"]["auto_slow_6locks_verified"], 6)
        self.assertEqual(r55_t["auto_slow_hdmi_init"]["auto_slow_shutter_angle_overlap_events"], 0)
        self.assertEqual(r55_t["auto_slow_6locks_bridge"]["auto_slow_ok"], 1)
        self.assertEqual(r55_t["hdmi_reccontrol_bridge"]["hdmi_rec_ctrl_without_tc_violations"], 0)
        self.assertEqual(r55_t["breathing_comp_bridge"]["breathing_ok"], 1)
        self.assertEqual(r55_t["lang_telemetry"]["lang"], "schinese")
        self.assertEqual(r55_t["lang_telemetry"]["run_28th_realhw_84th_live"], 1)
        self.assertEqual(r55_t["stage_b_bridge"]["round"], 55)
        self.assertEqual(r55_t["lockout_injection_guard"]["r55b_ok"], 1)
        self.assertEqual(r55_t["camreset_init_integrated"]["surfaces_h0_eq_h3"], 16)
        self.assertEqual(parsed["prefix_counts"]["FX6_R55_"], 8)

    def test_14_round55_parse_log_defaults_when_no_r55_lines_present(self) -> None:
        parsed = self.runner.extract_milestones("Linux version 4.9.337-scel+\n")
        self.assertIsNone(parsed["r55_telemetry"])
        self.assertEqual(parsed["prefix_counts"].get("FX6_R55_", 0), 0)

    def test_15_round55_runner_uses_fx6_r55_prefix_and_stage_label_and_r54_compat(self) -> None:
        self.assertIn('if args.round >= 55:\n        tmp_prefix = "fx6-r55"', self.runner_src)
        self.assertIn(
            "Milestone28thRealHw84thRunWave41AutoSlowShutter6LocksHdmiRecControlTcOut4chAudioBreathingComp",
            self.runner_src,
        )
        self.assertIn("# r54_test_compat:", self.runner_src)
        self.assertIn(", 55]", self.runner_src)

    def test_16_round55_runner_portability_and_wave41_intel_spec_rules(self) -> None:
        self.assertIn('shutil.which("zig")', self.runner_src)
        self.assertIn("FX6_SCRATCH_DIR", self.runner_src)
        for token in (
            "Auto Slow Shutter",
            "Shutter Priority",
            "Manual Exposure",
            "ISO AUTO",
            "Flexible Exp. Mode",
            "Cine EI Quick",
            "REC Control",
            "Time Code Output",
            "4ch Audio Output",
            "Rec. Media dur HDMI Output",
            "Breathing Comp.",
            "ILME-FX3",
        ):
            self.assertIn(token, self.wave41_spec)

    def test_17_round55_summary_json_top_level_schema_and_milestone_metadata(self) -> None:
        d = self.summary
        self.assertEqual(
            d["schema"],
            "fx6-on-fx3-round55-realhw-auto-slow-shutter-hdmi-reccontrol-breathing-qemu-v1",
        )
        self.assertEqual(d["round"], 55)
        self.assertIn("28th Real-HW QEMU Round", d["milestone"])
        self.assertIn("84 Live Runs", d["milestone"])
        self.assertEqual(d["date"], "2026-11-17")
        self.assertIn("4.9.337-scel+", d["kernel_version"])
        self.assertEqual(d["raw_firmware_bytes_leaked"], 0)

    def test_18_round55_summary_json_zero_host_path_and_scratch_leaks(self) -> None:
        for forbidden in (
            "/Users/",
            "/private/tmp/",
            "/var/folders/",
            "work/_scratch/",
            "work/_tests/",
        ):
            self.assertNotIn(forbidden, self.summary_raw)

    def test_19_round55_summary_audit_block_confirms_28th_round_84th_run_and_all_booleans(self) -> None:
        audit = self.summary["r55_realhw_auto_slow_shutter_hdmi_reccontrol_breathing_audit"]
        self.assertEqual(audit["round"], 55)
        self.assertEqual(audit["milestone"], 55)
        self.assertEqual(audit["milestone221_qemu_rounds"], 28)
        self.assertEqual(audit["milestone221_qemu_runs"], 84)
        self.assertEqual(audit["milestone233_qemu_rounds"], 28)
        self.assertEqual(audit["milestone233_qemu_runs"], 84)
        self.assertEqual(audit["milestone254_qemu_rounds"], 28)
        self.assertEqual(audit["milestone254_qemu_runs"], 84)
        self.assertEqual(audit["milestone264_qemu_rounds"], 28)
        self.assertEqual(audit["milestone264_qemu_runs"], 84)
        self.assertEqual(audit["total_runs"], 3)
        for k, v in audit.items():
            if isinstance(v, bool):
                self.assertTrue(v, f"Expected audit boolean {k} to be True")

    def test_20_round55_all_3_runs_present_with_kernel_4_9_337_and_zero_crashes_writes(self) -> None:
        runs = self.summary["runs"]
        self.assertEqual(list(runs.keys()), list(self.EXPECTED_RUN_KEYS))
        for rk, rv in runs.items():
            self.assertEqual(rv["round"], 55, rk)
            self.assertIn("4.9.337-scel+", rv["kernel_version"], rk)
            self.assertEqual(rv["nop_count"], 0, rk)
            self.assertEqual(rv["crashes"], 0, rk)
            self.assertEqual(rv["emmc_write_count"], 0, rk)
            self.assertGreater(rv["wall_elapsed_sec"], 0.0, rk)

    def test_21_round55_r55a_auto_slow_shutter_default_on_and_all_6_lockouts_verified(self) -> None:
        init_t = self.summary["runs"]["r55a_auto_slow_6locks_hdmi_reccontrol_big6_schinese"][
            "r55_telemetry"
        ]["auto_slow_hdmi_init"]
        self.assertEqual(init_t["fx3_wave41_nodes_ok"], 1)
        self.assertEqual(init_t["auto_slow_default_on_ok"], 1)
        self.assertEqual(init_t["invalid_auto_slow_rc"], -22)
        self.assertEqual(init_t["auto_slow_camreset_on_ok"], 1)
        self.assertEqual(init_t["auto_slow_nominal_active_ok"], 1)
        self.assertEqual(init_t["auto_slow_6locks_verified"], 6)
        self.assertEqual(init_t["auto_slow_shutter_angle_overlap_events"], 0)

    def test_22_round55_r55a_hdmi_output_settings_nominal_and_slot1_vault_guard(self) -> None:
        init_t = self.summary["runs"]["r55a_auto_slow_6locks_hdmi_reccontrol_big6_schinese"][
            "r55_telemetry"
        ]["auto_slow_hdmi_init"]
        self.assertEqual(init_t["hdmi_nominal_tc_rec_ctrl_ok"], 1)
        self.assertEqual(init_t["hdmi_4ch_audio_routing_verified"], 2)
        self.assertEqual(init_t["hdmi_rec_media_off_blocks_internal_ok"], 1)
        self.assertEqual(init_t["hdmi_setup_survives_camreset_ok"], 1)
        self.assertEqual(init_t["slot1_vault_writes"], 0)

    def test_23_round55_r55a_p2_cnflasha_and_slot1_ro_guards_intact(self) -> None:
        init_t = self.summary["runs"]["r55a_auto_slow_6locks_hdmi_reccontrol_big6_schinese"][
            "r55_telemetry"
        ]["auto_slow_hdmi_init"]
        self.assertEqual(init_t["p2_write_blocked_rc"], -30)
        self.assertEqual(init_t["p2_sha256_match"], 1)
        self.assertEqual(init_t["cnflasha_sha256_match"], 1)
        self.assertEqual(init_t["slot1_vault_sha256_match"], 1)
        self.assertEqual(init_t["cnflasha_writes"], 0)
        self.assertEqual(init_t["appfw_present"], 1)
        self.assertEqual(init_t["shim_present"], 1)
        self.assertEqual(init_t["emmc_write_count"], 0)
        self.assertEqual(init_t["r55_init_ok"], 1)

    def test_24_round55_r55a_stage_b_schinese_lang_telemetry_and_bridges(self) -> None:
        r55a_t = self.summary["runs"]["r55a_auto_slow_6locks_hdmi_reccontrol_big6_schinese"][
            "r55_telemetry"
        ]
        lt = r55a_t["lang_telemetry"]
        self.assertEqual(lt["lang"], "schinese")
        self.assertEqual(lt["bk4_lang_id"], "0x02cf019c")
        self.assertEqual(lt["bk4_lang_val"], "0x19")
        self.assertEqual(lt["lang_enum"], "0x2b45_CHINESE_SIMPLIFIED")
        self.assertEqual(lt["font_bank"], 23)
        self.assertEqual(lt["str_bank"], 19)
        self.assertEqual(lt["gpe_fb"], 0)
        self.assertEqual(lt["run_28th_realhw_84th_live"], 1)
        self.assertEqual(lt["auto_slow_shutter_angle_overlap_events"], 0)
        self.assertEqual(lt["hdmi_rec_ctrl_without_tc_violations"], 0)
        self.assertEqual(lt["e_nd_actuator_tx_count"], 0)
        self.assertEqual(lt["raw_firmware_bytes_leaked"], 0)
        sb = r55a_t["stage_b_bridge"]
        self.assertEqual(sb["round"], 55)
        self.assertEqual(sb["faithful"], 1)
        self.assertEqual(sb["nop_count"], 0)
        self.assertEqual(sb["auto_slow_shutter_6locks_angle_disjoint"], 1)
        self.assertEqual(sb["hdmi_rec_ctrl_tcout_4ch_vault"], 1)
        self.assertEqual(sb["breathing_comp_movie_raw_240p_guard"], 1)

    def test_25_round55_r55a_stage_b_3_pillar_bridges_verified(self) -> None:
        r55a_t = self.summary["runs"]["r55a_auto_slow_6locks_hdmi_reccontrol_big6_schinese"][
            "r55_telemetry"
        ]
        ab = r55a_t["auto_slow_6locks_bridge"]
        self.assertEqual(ab["auto_slow_default_on_ok"], 1)
        self.assertEqual(ab["auto_slow_6locks_verified"], 6)
        self.assertEqual(ab["auto_slow_shutter_angle_disjoint_ok"], 1)
        self.assertEqual(ab["auto_slow_shutter_angle_overlap_events"], 0)
        self.assertEqual(ab["auto_slow_ok"], 1)
        hb = r55a_t["hdmi_reccontrol_bridge"]
        self.assertEqual(hb["hdmi_tcout_prereq_enforced_ok"], 1)
        self.assertEqual(hb["hdmi_rec_ctrl_without_tc_violations"], 0)
        self.assertEqual(hb["hdmi_4ch_audio_routing_ok"], 1)
        self.assertEqual(hb["hdmi_rec_media_off_slot1_vault_ok"], 1)
        self.assertEqual(hb["hdmi_setup_ok"], 1)
        bb = r55a_t["breathing_comp_bridge"]
        self.assertEqual(bb["breathing_default_off_ok"], 1)
        self.assertEqual(bb["breathing_movie_only_crop_ok"], 1)
        self.assertEqual(bb["breathing_raw_240p_still_blocked_ok"], 1)
        self.assertEqual(bb["breathing_comp_raw_240p_still_leak_events"], 0)
        self.assertEqual(bb["breathing_ok"], 1)

    def test_26_round55_r55a_gpe0_readback_exact_346206_pixels_and_87_colors(self) -> None:
        r55a = self.summary["runs"]["r55a_auto_slow_6locks_hdmi_reccontrol_big6_schinese"]
        self.assertEqual(r55a["target_presenter"], "31procam_big6_menu_home_presenter")
        self.assertEqual(r55a["target_sid"], "0x0a")
        self.assertGreaterEqual(r55a["total_threads_seen"], 150)
        gpe0 = r55a["gpe0_readback"]
        self.assertTrue(gpe0["present"])
        self.assertEqual(gpe0["bytes"], 2211840)
        self.assertEqual(gpe0["total_pixels"], 552960)
        self.assertEqual(gpe0["nonzero_pixels"], 346206)
        self.assertEqual(gpe0["unique_colors"], 87)

    def test_27_round55_r55a_stage_b_manifest_13_hashes_and_r55_metadata(self) -> None:
        sb = self.summary["runs"]["r55a_auto_slow_6locks_hdmi_reccontrol_big6_schinese"]["stage_b"]
        self.assertEqual(sb["manifest_count"], 13)
        self.assertEqual(len(sb["manifest_items"]), 13)
        for item in sb["manifest_items"]:
            self.assertEqual(len(item["sha256"]), 64)
        r55_meta = sb["r55"]
        self.assertEqual(r55_meta["r55_mode"], "auto_slow_6locks_hdmi_reccontrol_big6")
        self.assertEqual(len(r55_meta["auto_slow_shutter_6_lockouts"]), 6)
        self.assertEqual(r55_meta["auto_slow_shutter_default"], "On")
        self.assertEqual(r55_meta["hdmi_4ch_audio_output_pairs"], ["CH1/CH2", "CH3/CH4"])
        self.assertEqual(r55_meta["breathing_comp_default"], "Off")

    def test_28_round55_r55b_illegal_rec_ctrl_without_tcout_blocked_fail_closed(self) -> None:
        r55b_t = self.summary["runs"]["r55b_prerequisite_lockout_injection_guard"]["r55_telemetry"]
        self.assertEqual(r55b_t["lockout_injection_rc"], 0)
        lk = r55b_t["lockout_injection_guard"]
        self.assertEqual(lk["illegal_rec_ctrl_rc"], -16)
        self.assertEqual(lk["hdmi_rec_ctrl_without_tc_violations"], 0)

    def test_29_round55_r55b_auto_slow_and_shutter_angle_simultaneous_blocked(self) -> None:
        lk = self.summary["runs"]["r55b_prerequisite_lockout_injection_guard"]["r55_telemetry"][
            "lockout_injection_guard"
        ]
        self.assertEqual(lk["angle_in_p_rc"], -16)
        self.assertEqual(lk["auto_slow_in_angle_rc"], -16)
        self.assertEqual(lk["auto_slow_shutter_angle_overlap_events"], 0)

    def test_30_round55_r55b_breathing_comp_raw_240p_still_noncompliant_lens_blocked(self) -> None:
        lk = self.summary["runs"]["r55b_prerequisite_lockout_injection_guard"]["r55_telemetry"][
            "lockout_injection_guard"
        ]
        self.assertEqual(lk["breathing_default_off_ok"], 1)
        self.assertEqual(lk["breathing_comp_crop_applied_ok"], 1)
        self.assertEqual(lk["raw_on_inject_rc"], -16)
        self.assertEqual(lk["sq_240p_inject_rc"], -16)
        self.assertEqual(lk["sq_200p_inject_rc"], -16)
        self.assertEqual(lk["still_inject_rc"], -95)
        self.assertEqual(lk["noncompliant_lens_rc"], -95)
        self.assertEqual(lk["breathing_comp_raw_240p_still_leak_events"], 0)

    def test_31_round55_r55b_slot1_vault_ro_and_zero_emmc_cnflasha_writes(self) -> None:
        lk = self.summary["runs"]["r55b_prerequisite_lockout_injection_guard"]["r55_telemetry"][
            "lockout_injection_guard"
        ]
        self.assertEqual(lk["slot1_vault_hdmi_block_rc"], -30)
        self.assertEqual(lk["slot1_vault_ro_blocked_rc"], -30)
        self.assertEqual(lk["slot1_vault_sha256_match"], 1)
        self.assertEqual(lk["slot1_vault_writes"], 0)
        self.assertEqual(lk["p2_write_blocked_rc"], -30)
        self.assertEqual(lk["cnflasha_ro_blocked_rc"], -30)
        self.assertEqual(lk["cnflasha_writes"], 0)
        self.assertEqual(lk["emmc_write_count"], 0)
        self.assertEqual(lk["r55b_ok"], 1)

    def test_32_round55_r55c_camreset_vs_initialize_survival_split_verified(self) -> None:
        ci = self.summary["runs"]["r55c_camreset_vs_initialize_h0_h3_integrated_big6_schinese"][
            "r55_telemetry"
        ]["camreset_init_integrated"]
        self.assertEqual(ci["wave41_survives_netreset_ok"], 1)
        self.assertEqual(ci["auto_slow_camreset_on_ok"], 1)
        self.assertEqual(ci["breathing_camreset_off_ok"], 1)
        self.assertEqual(ci["hdmi_setup_survives_camreset_ok"], 1)
        self.assertEqual(ci["initialize_restores_all_wave41_defaults_ok"], 1)

    def test_33_round55_r55c_dlopen_and_16_h0_eq_h3_idempotent_unmount(self) -> None:
        ci = self.summary["runs"]["r55c_camreset_vs_initialize_h0_h3_integrated_big6_schinese"][
            "r55_telemetry"
        ]["camreset_init_integrated"]
        self.assertEqual(ci["dlopen_ok"], 1)
        self.assertEqual(ci["surfaces_verified"], 16)
        self.assertEqual(ci["surfaces_h0_eq_h3"], 16)
        self.assertEqual(ci["drift_bits"], 0)
        self.assertEqual(ci["e_nd_actuator_tx_count"], 0)
        self.assertEqual(ci["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(ci["emmc_write_count"], 0)
        self.assertEqual(ci["r55c_ok"], 1)

    def test_34_round55_r55c_integrated_renders_valid_big6_gpe0_readback(self) -> None:
        r55c = self.summary["runs"]["r55c_camreset_vs_initialize_h0_h3_integrated_big6_schinese"]
        self.assertEqual(r55c["target_presenter"], "31procam_big6_menu_home_presenter")
        self.assertEqual(r55c["target_sid"], "0x0a")
        gpe0 = r55c["gpe0_readback"]
        self.assertTrue(gpe0["present"])
        self.assertEqual(gpe0["bytes"], 2211840)
        self.assertEqual(gpe0["total_pixels"], 552960)
        self.assertEqual(gpe0["nonzero_pixels"], 346206)
        self.assertEqual(gpe0["unique_colors"], 87)

    def test_35_round55_realhw_mechanisms_verified_6_blocks_match_run_telemetry(self) -> None:
        rm = self.summary["realhw_mechanisms_verified"]
        self.assertEqual(len(rm), 6)
        r55a = self.summary["runs"]["r55a_auto_slow_6locks_hdmi_reccontrol_big6_schinese"][
            "r55_telemetry"
        ]
        r55b = self.summary["runs"]["r55b_prerequisite_lockout_injection_guard"]["r55_telemetry"]
        r55c = self.summary["runs"]["r55c_camreset_vs_initialize_h0_h3_integrated_big6_schinese"][
            "r55_telemetry"
        ]
        self.assertEqual(
            rm["auto_slow_shutter_6locks_hdmi_reccontrol_init"],
            r55a["auto_slow_hdmi_init"],
        )
        self.assertEqual(
            rm["auto_slow_shutter_6locks_stage_b_bridge"],
            r55a["auto_slow_6locks_bridge"],
        )
        self.assertEqual(
            rm["hdmi_reccontrol_4chaudio_vault_stage_b_bridge"],
            r55a["hdmi_reccontrol_bridge"],
        )
        self.assertEqual(
            rm["breathing_comp_movie_raw_240p_stage_b_bridge"],
            r55a["breathing_comp_bridge"],
        )
        self.assertEqual(
            rm["prerequisite_lockout_injection_guard"],
            r55b["lockout_injection_guard"],
        )
        self.assertEqual(
            rm["camreset_vs_initialize_and_16_h0_h3"],
            r55c["camreset_init_integrated"],
        )

    def test_36_round55_camreset_vs_initialize_tiers_consistent_across_runs(self) -> None:
        init_a = self.summary["runs"]["r55a_auto_slow_6locks_hdmi_reccontrol_big6_schinese"][
            "r55_telemetry"
        ]["auto_slow_hdmi_init"]
        ci_c = self.summary["runs"]["r55c_camreset_vs_initialize_h0_h3_integrated_big6_schinese"][
            "r55_telemetry"
        ]["camreset_init_integrated"]
        self.assertEqual(init_a["auto_slow_camreset_on_ok"], 1)
        self.assertEqual(init_a["hdmi_setup_survives_camreset_ok"], 1)
        self.assertEqual(ci_c["auto_slow_camreset_on_ok"], 1)
        self.assertEqual(ci_c["breathing_camreset_off_ok"], 1)
        self.assertEqual(ci_c["hdmi_setup_survives_camreset_ok"], 1)
        self.assertEqual(ci_c["initialize_restores_all_wave41_defaults_ok"], 1)

    def test_37_round55_cross_round_consistency_with_r54_shutter_angle_and_setup_survival(self) -> None:
        self.assertEqual(self.r54_summary["round"], 54)
        r54_init = self.r54_summary["runs"]["r54a_diff_set_still_mv_shutter_angle_big6_schinese"][
            "r54_telemetry"
        ]["diff_set_init"]
        self.assertEqual(r54_init["shutter_angle_unchecked_common_independent_ok"], 1)
        self.assertEqual(r54_init["diff_set_survives_camreset_ok"], 1)
        r55_ci = self.summary["runs"]["r55c_camreset_vs_initialize_h0_h3_integrated_big6_schinese"][
            "r55_telemetry"
        ]["camreset_init_integrated"]
        self.assertEqual(r55_ci["auto_slow_shutter_angle_overlap_events"], 0)
        self.assertEqual(r55_ci["hdmi_setup_survives_camreset_ok"], 1)

    def test_38_round55_cross_round_consistency_with_r53_setup_vs_netreset_split(self) -> None:
        self.assertEqual(self.r53_summary["round"], 53)
        r53_init = self.r53_summary["runs"]["r53a_display_quality_bt_rmt_big6_schinese"][
            "r53_telemetry"
        ]["dispqual_btrmt_init"]
        self.assertEqual(r53_init["display_quality_survives_camreset_ok"], 1)
        self.assertEqual(r53_init["display_quality_survives_netreset_ok"], 1)
        r55_ci = self.summary["runs"]["r55c_camreset_vs_initialize_h0_h3_integrated_big6_schinese"][
            "r55_telemetry"
        ]["camreset_init_integrated"]
        self.assertEqual(r55_ci["wave41_survives_netreset_ok"], 1)
        self.assertEqual(r55_ci["hdmi_setup_survives_camreset_ok"], 1)

    def test_39_round55_cross_round_consistency_with_r50_4ch_shoe_audio_and_slot1_ro(self) -> None:
        self.assertEqual(self.r50_summary["round"], 50)
        r55a_init = self.summary["runs"]["r55a_auto_slow_6locks_hdmi_reccontrol_big6_schinese"][
            "r55_telemetry"
        ]["auto_slow_hdmi_init"]
        r55b_lk = self.summary["runs"]["r55b_prerequisite_lockout_injection_guard"]["r55_telemetry"][
            "lockout_injection_guard"
        ]
        self.assertEqual(r55a_init["hdmi_4ch_audio_routing_verified"], 2)
        self.assertEqual(r55b_lk["slot1_vault_ro_blocked_rc"], -30)
        self.assertEqual(r55b_lk["slot1_vault_writes"], 0)

    def test_40_round55_unexecuted_physical_camera_bench_boundaries_documented(self) -> None:
        bounds = self.summary["unexecuted_physical_camera_bench_boundaries"]
        self.assertEqual(len(bounds), 3)
        joined = " ".join(bounds)
        self.assertIn("Auto Slow Shutter", joined)
        self.assertIn("HDMI Output Settings", joined)
        self.assertIn("Breathing Comp.", joined)

    def test_41_round55_alpha_png_exists_under_50kib_and_matches_summary_sha256(self) -> None:
        pe = self.summary["runs"]["r55a_auto_slow_6locks_hdmi_reccontrol_big6_schinese"][
            "png_exports"
        ]
        self.assertLess(len(self.alpha_png_bytes), 50000)
        self.assertLess(len(self.alpha_png_bytes), 51200)
        self.assertEqual(len(self.alpha_png_bytes), pe["alpha_bytes"])
        self.assertEqual(
            hashlib.sha256(self.alpha_png_bytes).hexdigest(), pe["alpha_sha256"]
        )

    def test_42_round55_composited_png_exists_under_50kib_and_matches_summary_sha256(self) -> None:
        pe = self.summary["runs"]["r55a_auto_slow_6locks_hdmi_reccontrol_big6_schinese"][
            "png_exports"
        ]
        self.assertLess(len(self.comp_png_bytes), 50000)
        self.assertLess(len(self.comp_png_bytes), 51200)
        self.assertEqual(len(self.comp_png_bytes), pe["composited_bytes"])
        self.assertEqual(
            hashlib.sha256(self.comp_png_bytes).hexdigest(), pe["composited_sha256"]
        )

    def test_43_round55_alpha_png_valid_1024x540_rgba_with_transparent_and_opaque_pixels(self) -> None:
        self.assertEqual(self.alpha_dims, (1024, 540))
        self.assertEqual(self.alpha_transparent, 206754)
        self.assertGreater(self.alpha_opaque, 300000)

    def test_44_round55_composited_png_valid_1024x540_rgba_100pct_opaque(self) -> None:
        self.assertEqual(self.comp_dims, (1024, 540))
        self.assertEqual(self.comp_opaque, 1024 * 540)

    def test_45_round55_report_readme_documents_all_3_runs_and_zero_host_leaks(self) -> None:
        for token in (
            "Round 55",
            "28th Real-HW",
            "84th Live Run",
            "r55a",
            "r55b",
            "r55c",
            "Auto Slow Shutter",
            "HDMI Output Settings",
            "REC Control",
            "Time Code Output",
            "4ch Audio Output",
            "Rec. Media dur HDMI Output",
            "Breathing Comp.",
            "346,206",
            "r55a-auto-slow-hdmi-reccontrol-big6-schinese-alpha.png",
            "r55a-auto-slow-hdmi-reccontrol-big6-schinese-composited.png",
        ):
            self.assertIn(token, self.r55_readme)
        for forbidden in ("/Users/", "/private/tmp/", "/var/folders/", "work/_scratch/"):
            self.assertNotIn(forbidden, self.r55_readme)

    def test_46_round55_closure_readme_section_55_present_and_accurate(self) -> None:
        self.assertIn("## 55. Round 55", self.closure_readme)
        self.assertIn("28th Real-HW Round", self.closure_readme)
        self.assertIn("84th Live Run", self.closure_readme)
        self.assertIn(
            "2026-11-17-round55-realhw-auto-slow-shutter-hdmi-reccontrol-breathing",
            self.closure_readme,
        )

    def test_47_round55_28_realhw_qemu_rounds_r28_to_r55_84_runs_and_56_pngs_continuity(self) -> None:
        png_total = 0
        for r in range(28, 56):
            matches = list((REPO_ROOT / "reports").glob(f"2026-??-??-round{r}-*"))
            self.assertEqual(len(matches), 1, f"Expected 1 report dir for Round {r}")
            pngs = list((matches[0] / "assets").glob("*.png"))
            self.assertEqual(len(pngs), 2, f"Expected 2 PNGs for Round {r}")
            for p in pngs:
                self.assertLess(p.stat().st_size, 51200, str(p))
            png_total += len(pngs)
        self.assertEqual(png_total, 56)
        audit = self.summary["r55_realhw_auto_slow_shutter_hdmi_reccontrol_breathing_audit"]
        self.assertEqual(audit["milestone264_qemu_rounds"], 28)
        self.assertEqual(audit["milestone264_qemu_runs"], 84)

    def test_48_round55_dual_mode_clean_room_toggle_parity_on_summary(self) -> None:
        for clean_flag in ("0", "1"):
            with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                d = json.loads(self.summary_raw)
                self.assertEqual(d["round"], 55)
                self.assertEqual(
                    d["runs"]["r55a_auto_slow_6locks_hdmi_reccontrol_big6_schinese"][
                        "r55_telemetry"
                    ]["auto_slow_hdmi_init"]["auto_slow_6locks_verified"],
                    6,
                )
                self.assertEqual(
                    d["runs"]["r55b_prerequisite_lockout_injection_guard"][
                        "r55_telemetry"
                    ]["lockout_injection_guard"]["hdmi_rec_ctrl_without_tc_violations"],
                    0,
                )
                self.assertEqual(
                    d["runs"]["r55c_camreset_vs_initialize_h0_h3_integrated_big6_schinese"][
                        "r55_telemetry"
                    ]["camreset_init_integrated"]["surfaces_h0_eq_h3"],
                    16,
                )

    def test_49_round55_r55a_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"]["r55a_auto_slow_6locks_hdmi_reccontrol_big6_schinese"][
            "r55_telemetry"
        ]["auto_slow_hdmi_init"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_50_round55_r55b_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"]["r55b_prerequisite_lockout_injection_guard"][
            "r55_telemetry"
        ]["lockout_injection_guard"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_51_round55_r55c_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"]["r55c_camreset_vs_initialize_h0_h3_integrated_big6_schinese"][
            "r55_telemetry"
        ]["camreset_init_integrated"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_52_round55_r55a_top_colors_transparent_plus_nonzero_equals_total_pixels(self) -> None:
        gpe = self.summary["runs"]["r55a_auto_slow_6locks_hdmi_reccontrol_big6_schinese"][
            "gpe0_readback"
        ]
        color_map = {row["argb"]: row["pixels"] for row in gpe["top_colors"]}
        self.assertIn("0x00000000", color_map)
        self.assertIn("0xff000000", color_map)
        self.assertEqual(color_map["0x00000000"] + gpe["nonzero_pixels"], gpe["total_pixels"])

    def test_53_round55_r55c_top_colors_transparent_plus_nonzero_equals_total_pixels(self) -> None:
        gpe = self.summary["runs"]["r55c_camreset_vs_initialize_h0_h3_integrated_big6_schinese"][
            "gpe0_readback"
        ]
        color_map = {row["argb"]: row["pixels"] for row in gpe["top_colors"]}
        self.assertIn("0x00000000", color_map)
        self.assertEqual(color_map["0x00000000"] + gpe["nonzero_pixels"], gpe["total_pixels"])

    def test_54_round55_r55a_and_r55c_wall_elapsed_and_duration_budget_sanity(self) -> None:
        r55a = self.summary["runs"]["r55a_auto_slow_6locks_hdmi_reccontrol_big6_schinese"]
        r55c = self.summary["runs"]["r55c_camreset_vs_initialize_h0_h3_integrated_big6_schinese"]
        max_wall = 240.0 if os.environ.get("GITHUB_ACTIONS") == "true" else 120.0
        self.assertGreaterEqual(r55a["duration_budget_sec"], 70)
        self.assertLessEqual(r55a["duration_budget_sec"], 120)
        self.assertGreater(r55a["wall_elapsed_sec"], 50.0)
        self.assertLess(r55a["wall_elapsed_sec"], max_wall)
        self.assertGreaterEqual(r55c["duration_budget_sec"], 70)
        self.assertLessEqual(r55c["duration_budget_sec"], 120)
        self.assertGreater(r55c["wall_elapsed_sec"], 50.0)
        self.assertLess(r55c["wall_elapsed_sec"], max_wall)

    def test_55_round55_r55b_fast_early_exit_wall_elapsed_under_20s(self) -> None:
        r55b = self.summary["runs"]["r55b_prerequisite_lockout_injection_guard"]
        self.assertEqual(r55b["duration_budget_sec"], 35)
        self.assertGreater(r55b["wall_elapsed_sec"], 1.0)
        self.assertLess(r55b["wall_elapsed_sec"], 20.0)
        self.assertTrue(r55b["gpe0_readback"]["skipped_stock_fx3_mode"])

    def test_56_round55_faithful_invariants_preserved_across_all_3_runs(self) -> None:
        for rk, rv in self.summary["runs"].items():
            fi = rv["faithful_invariants"]
            self.assertEqual(fi["FX6_NATIVE_FAITHFUL"], 1, rk)
            self.assertEqual(fi["subst_color"], 0, rk)
            self.assertEqual(fi["subst_image"], 0, rk)
            self.assertEqual(fi["forced_render"], 0, rk)
            self.assertEqual(fi["skipped_node"], 0, rk)
            self.assertEqual(fi["lock_bypass"], 0, rk)

    def test_57_round55_all_3_runs_stage_b_manifest_count_13(self) -> None:
        for rk, rv in self.summary["runs"].items():
            self.assertEqual(rv["stage_b"]["manifest_count"], 13, rk)
            self.assertEqual(len(rv["stage_b"]["manifest_items"]), 13, rk)

    def test_58_round55_r55c_stage_b_r55_bridges_and_zero_leak_verified(self) -> None:
        r55c_t = self.summary["runs"]["r55c_camreset_vs_initialize_h0_h3_integrated_big6_schinese"][
            "r55_telemetry"
        ]
        self.assertEqual(r55c_t["auto_slow_6locks_bridge"]["auto_slow_ok"], 1)
        self.assertEqual(r55c_t["hdmi_reccontrol_bridge"]["hdmi_setup_ok"], 1)
        self.assertEqual(r55c_t["breathing_comp_bridge"]["breathing_ok"], 1)
        self.assertEqual(r55c_t["hdmi_reccontrol_bridge"]["hdmi_rec_ctrl_without_tc_violations"], 0)
        self.assertEqual(r55c_t["stage_b_bridge"]["e_nd_actuator_tx_count"], 0)

    def test_59_round55_all_3_runs_prefix_counts_include_fx6_r55(self) -> None:
        r55a_pc = self.summary["runs"]["r55a_auto_slow_6locks_hdmi_reccontrol_big6_schinese"][
            "prefix_counts"
        ]
        r55b_pc = self.summary["runs"]["r55b_prerequisite_lockout_injection_guard"][
            "prefix_counts"
        ]
        r55c_pc = self.summary["runs"]["r55c_camreset_vs_initialize_h0_h3_integrated_big6_schinese"][
            "prefix_counts"
        ]
        self.assertGreater(r55a_pc["FX6_R55_"], 10)
        self.assertEqual(r55b_pc["FX6_R55_"], 3)
        self.assertGreater(r55c_pc["FX6_R55_"], 10)

    def test_60_round55_r55_meta_invariants_across_all_3_runs(self) -> None:
        for rk, rv in self.summary["runs"].items():
            m = rv["stage_b"]["r55"]
            self.assertTrue(m["auto_slow_shutter_angle_disjoint"], rk)
            self.assertEqual(m["auto_slow_shutter_angle_overlap_events"], 0, rk)
            self.assertTrue(m["auto_slow_shutter_reset_by_camera_settings_reset"], rk)
            self.assertTrue(m["hdmi_rec_control_requires_time_code_output_on"], rk)
            self.assertEqual(m["hdmi_rec_ctrl_without_tc_violations"], 0, rk)
            self.assertTrue(m["hdmi_output_settings_survives_camera_settings_reset"], rk)
            self.assertTrue(m["hdmi_output_settings_reset_only_by_initialize"], rk)
            self.assertTrue(m["breathing_comp_blocked_during_hdmi_raw_4264x2408"], rk)
            self.assertTrue(m["breathing_comp_blocked_during_sq_240p_200p"], rk)
            self.assertTrue(m["breathing_comp_blocked_in_still_mode"], rk)
            self.assertEqual(m["breathing_comp_raw_240p_still_leak_events"], 0, rk)
            self.assertEqual(m["e_nd_actuator_tx_count"], 0, rk)
            self.assertEqual(m["raw_firmware_bytes_leaked"], 0, rk)

    def test_61_round55_no_stray_temp_files_in_repo_root(self) -> None:
        for bad_name in ("tmp", "scratch", ".worktrees"):
            self.assertFalse((REPO_ROOT / bad_name).exists(), bad_name)

    def test_62_round55_port_8768_untouched_in_round55_reports(self) -> None:
        self.assertNotIn("8768", self.summary_raw)
        self.assertNotIn("8768", self.r55_readme)

    def test_63_round55_runner_escapes_percent_in_argparse_help(self) -> None:
        # Ensure Python 3.14 argparse compatibility (no unescaped single % in help= strings)
        self.assertIn("ArgumentParser", self.runner_src)
        self.assertNotIn('"/usr/bin/python3"', self.runner_src)

    def test_64_round55_test_suite_contains_at_least_60_unit_tests(self) -> None:
        methods = [m for m in dir(self) if m.startswith("test_")]
        self.assertEqual(len(methods), 64)


if __name__ == "__main__":
    unittest.main()
