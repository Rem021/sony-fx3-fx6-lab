#!/usr/bin/env python3
"""Offline dual-mode unit tests for FX6-on-FX3 Round 54 (27th Real-HW Round / 81st Live Run — Wave-40)."""
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
ROUND54_REPORT_DIR = (
    REPO_ROOT
    / "reports"
    / "2026-11-15-round54-realhw-diff-set-still-mv-custom-key-remain-shoot-qemu"
)
WAVE40_SPEC_PATH = (
    REPO_ROOT
    / "reports"
    / "2026-11-15-global-sony-wave40-milestone-diff-set-still-mv-8items-shutter-angle-custom-key-dial-remain-shoot-intel"
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


def _build_overlay_for_r54(
    runner,
    parent_cpio: pathlib.Path,
    fp,
    fv,
    fb,
    fake_run,
    jit_meta: Dict[str, Any],
    work: pathlib.Path,
    r54_mode: str,
    lang: str = "schinese",
    enable_r54: bool = True,
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
            enable_r54=enable_r54,
            r54_mode=r54_mode,
            sd_manifest_mode="valid",
            lang=lang,
            shim_bytes=b"SHIM",
        )


class TestRound54RealHwDiffSetStillMvCustomKeyRemainShootQemu(unittest.TestCase):
    EXPECTED_RUN_KEYS = (
        "r54a_diff_set_still_mv_shutter_angle_big6_schinese",
        "r54b_custom_key_dial_iso_ei_camset_persist_guard",
        "r54c_remain_shoot_evf_less_integrated_big6_schinese",
    )

    runner: Any
    runner_src: str
    stage_a_src: str
    shim_src: str
    wave40_spec: str
    summary_raw: str
    summary: Dict[str, Any]
    r54_readme: str
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
    launcher_r54: Optional[bytes]
    shim_r54: Optional[bytes]
    shim_r53: Optional[bytes]
    r53_summary: Dict[str, Any]
    r52_summary: Dict[str, Any]
    r50_summary: Dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = _load_closure_module("fx6_brr_r54_cached", "build_and_run_round.py")
        cls.runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")
        cls.stage_a_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        cls.shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        cls.wave40_spec = WAVE40_SPEC_PATH.read_text(encoding="utf-8")
        cls.summary_raw = (ROUND54_REPORT_DIR / "summary.json").read_text(encoding="utf-8")
        cls.summary = json.loads(cls.summary_raw)
        cls.r54_readme = (ROUND54_REPORT_DIR / "README.md").read_text(encoding="utf-8")
        cls.closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")

        alpha_p = (
            ROUND54_REPORT_DIR
            / "assets"
            / "r54a-diff-set-customkey-big6-schinese-alpha.png"
        )
        comp_p = (
            ROUND54_REPORT_DIR
            / "assets"
            / "r54a-diff-set-customkey-big6-schinese-composited.png"
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
            cls.ov_a = _build_overlay_for_r54(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wa", "diff_set_still_mv_shutter_angle_big6", lang="schinese",
            )
            cls.ov_b = _build_overlay_for_r54(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wb", "custom_key_dial_iso_ei_camset_persist_guard", lang="en",
            )
            cls.ov_c = _build_overlay_for_r54(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wc", "remain_shoot_evf_less_integrated_big6", lang="schinese",
            )
            cls.ov_off = _build_overlay_for_r54(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "woff", "diff_set_still_mv_shutter_angle_big6", enable_r54=False,
            )
            cls.invalid_mode_raised = False
            try:
                _build_overlay_for_r54(
                    cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                    tpath / "wbad", "invalid_r54_mode",
                )
            except ValueError:
                cls.invalid_mode_raised = True

            if cls.runner.ZIG.is_file():
                verify_r54_out = tpath / "fx6-stage-a-verify-r54"
                shim_r54_out = tpath / "libgrm-fbinit9-r54.so"
                shim_r53_out = tpath / "libgrm-fbinit9-r53.so"
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
                        str(verify_r54_out),
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
                    [
                        str(cls.runner.ZIG),
                        "cc",
                        "-target",
                        "aarch64-linux-gnu.2.25",
                        "-O0",
                        "-shared",
                        "-fPIC",
                        "-DFX6_ROUND=53",
                        str(CLOSURE_DIR / "libgrm-fbinit9.c"),
                        "-ldl",
                        "-lpthread",
                        "-o",
                        str(shim_r53_out),
                    ],
                ):
                    cls.runner.subprocess.run(cmd, check=True)
                cls.launcher_r54 = verify_r54_out.read_bytes()
                cls.shim_r54 = shim_r54_out.read_bytes()
                cls.shim_r53 = shim_r53_out.read_bytes()
            else:
                cls.launcher_r54 = None
                cls.shim_r54 = None
                cls.shim_r53 = None

        cls.r53_summary = json.loads(
            (
                REPO_ROOT
                / "reports"
                / "2026-11-15-round53-realhw-display-quality-bt-rmt-mymenu-qemu"
                / "summary.json"
            ).read_text(encoding="utf-8")
        )
        cls.r52_summary = json.loads(
            (
                REPO_ROOT
                / "reports"
                / "2026-11-15-round52-realhw-lock-op-parts-audio-timing-exp-step-qemu"
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

    def test_01_wave40_global_spec_present_and_covers_all_wave40_pillars(self) -> None:
        self.assertTrue(WAVE40_SPEC_PATH.is_file())
        for needle in (
            "Different Set for Still/Mv",
            "Aperture",
            "Shutter Speed",
            "Custom White Balance",
            "Shutter Mode",
            "Angle",
            "Custom Key/Dial Set.",
            "ISO/EI",
            "Follow Custom",
            "My Dial 1",
            "Recall Custom hold 1",
            "Remain Shoot Display",
            "Not Displayed",
            "Always Display",
            "Shoot-Only Display",
            "Finder/Monitor",
            "no built-in EVF",
        ):
            self.assertIn(needle, self.wave40_spec)

    def test_02_round54_summary_schema_round_milestone_and_zero_leaks(self) -> None:
        self.assertNotIn("/Users/", self.summary_raw)
        self.assertNotIn("/private/tmp/", self.summary_raw)
        self.assertEqual(
            self.summary["schema"],
            "fx6-on-fx3-round54-realhw-diff-set-still-mv-custom-key-remain-shoot-qemu-v1",
        )
        self.assertEqual(self.summary["round"], 54)
        self.assertEqual(self.summary["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(tuple(self.summary["runs"].keys()), self.EXPECTED_RUN_KEYS)

    def test_03_round54_cli_accepts_round54_and_all_3_r54_modes(self) -> None:
        self.assertIn(", 54]", self.runner_src)
        self.assertIn(", 53]", self.runner_src)
        for mode in (
            "diff_set_still_mv_shutter_angle_big6",
            "custom_key_dial_iso_ei_camset_persist_guard",
            "remain_shoot_evf_less_integrated_big6",
        ):
            self.assertIn(mode, self.runner_src)

    def test_04_round54_overlay_rejects_invalid_r54_mode(self) -> None:
        self.assertTrue(self.invalid_mode_raised)

    def test_05_round54_overlay_r54a_diff_set_injects_etc_fx6_stage_r54_and_appfw_launch(self) -> None:
        replacements, additions, meta = self.ov_a
        self.assertTrue(meta["r54_enabled"])
        self.assertIn("etc/fx6_stage_r54", additions)
        self.assertIn("etc/fx6_r54_libjit.so", additions)
        r54_cfg = additions["etc/fx6_stage_r54"][0].decode("utf-8")
        self.assertIn("stage_r54=1", r54_cfg)
        self.assertIn("r54_mode=diff_set_still_mv_shutter_angle_big6", r54_cfg)
        self.assertIn("run_27th_realhw_81st_live=1", r54_cfg)
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("/usr/bin/appfw-launch", init_txt)
        self.assertNotIn("--r54-custom-key-dial-camset-persist", init_txt)

    def test_06_round54_overlay_r54b_custom_key_dial_injects_early_probe_and_poweroff(self) -> None:
        replacements, _, meta = self.ov_b
        self.assertEqual(meta["r54"]["r54_mode"], "custom_key_dial_iso_ei_camset_persist_guard")
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("--r54-custom-key-dial-camset-persist", init_txt)
        self.assertIn("FX6_R54_CUSTOM_KEY_DIAL_RC=", init_txt)
        self.assertIn("FX6_R54_CUSTOM_KEY_DIAL_EXIT", init_txt)
        self.assertIn("poweroff -f", init_txt)

    def test_07_round54_overlay_r54c_remain_shoot_integrated_runs_stage_b_big6(self) -> None:
        replacements, additions, meta = self.ov_c
        self.assertEqual(meta["r54"]["r54_mode"], "remain_shoot_evf_less_integrated_big6")
        r54_cfg = additions["etc/fx6_stage_r54"][0].decode("utf-8")
        self.assertIn("r54_mode=remain_shoot_evf_less_integrated_big6", r54_cfg)
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("/usr/bin/appfw-launch", init_txt)
        self.assertNotIn("--r54-custom-key-dial-camset-persist", init_txt)

    def test_08_round54_overlay_disabled_when_enable_r54_false(self) -> None:
        _, additions, meta = self.ov_off
        self.assertFalse(meta["r54_enabled"])
        self.assertNotIn("etc/fx6_stage_r54", additions)
        self.assertNotIn("etc/fx6_r54_libjit.so", additions)
        self.assertNotIn("r54", meta)

    def test_09_round54_stage_a_c_source_contains_all_3_wave40_probes(self) -> None:
        for sym in (
            "setup_r54_diff_set_still_mv_shutter_angle_probe",
            "run_r54_custom_key_dial_camset_persist_probe",
            "run_r54_remain_shoot_evf_less_integrated_probe",
            "FX6_R54_DIFF_SET_STILL_MV_INIT",
            "FX6_R54_CUSTOM_KEY_DIAL_PERSIST",
            "FX6_R54_REMAIN_SHOOT_EVF_INTEGRATED",
            "--r54-custom-key-dial-camset-persist",
            "--r54-remain-shoot-evf-less-integrated",
            "/etc/fx6_stage_r54",
        ):
            self.assertIn(sym, self.stage_a_src)

    def test_10_round54_shim_c_source_contains_r54_guarded_bridges(self) -> None:
        self.assertIn("#if FX6_ROUND >= 54", self.shim_src)
        for sym in (
            "FX6_R54_DIFF_SET_STILL_MV_BRIDGE",
            "FX6_R54_CUSTOM_KEY_DIAL_BRIDGE",
            "FX6_R54_REMAIN_SHOOT_EVF_BRIDGE",
            "FX6_R54_LANG_TELEMETRY",
            "FX6_STAGE_B_R54_BRIDGE",
        ):
            self.assertIn(sym, self.shim_src)

    def test_11_round54_compile_launcher_and_shim_aarch64_elf_symbols(self) -> None:
        if self.launcher_r54 is None or self.shim_r54 is None:
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertEqual(self.launcher_r54[:4], b"\x7fELF")
        self.assertEqual(self.shim_r54[:4], b"\x7fELF")
        self.assertEqual(struct.unpack_from("<H", self.shim_r54, 18)[0], 183)
        self.assertIn(b"FX6_R54_DIFF_SET_STILL_MV_BRIDGE", self.shim_r54)
        self.assertIn(b"FX6_R54_CUSTOM_KEY_DIAL_BRIDGE", self.shim_r54)
        self.assertIn(b"FX6_R54_REMAIN_SHOOT_EVF_BRIDGE", self.shim_r54)

    def test_12_round54_shim_round53_backward_compat_excludes_r54_bridges(self) -> None:
        if self.shim_r53 is None:
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertIn(b"FX6_R53_DISPQUAL_BTRMT_BRIDGE", self.shim_r53)
        self.assertNotIn(b"FX6_R54_DIFF_SET_STILL_MV_BRIDGE", self.shim_r53)

    def test_13_round54_parse_log_extracts_all_8_r54_prefixes_and_rc(self) -> None:
        serial_text = (
            "\n".join(
                [
                    "Linux version 4.9.337-scel+ (sony@fx3)",
                    "FX6_R54_DIFF_SET_STILL_MV_INIT fx3_diff_set_node_ok=1 diff_set_8items_verified=8 common_to_separate_custom_wb_still_only_ok=1 separate_to_common_3exceptions_retain_still_ok=1 shutter_angle_unchecked_common_independent_ok=1 r54_init_ok=1",
                    "FX6_R54_DIFF_SET_STILL_MV_BRIDGE diff_set_8items_verified=8 shutter_angle_unchecked_common_independent_ok=1 diff_set_ok=1 r54_bridge_ok=1",
                    "FX6_R54_CUSTOM_KEY_DIAL_BRIDGE front_dial_aperture_ok=1 rear_dial_iso_ei_ok=1 control_wheel_shutter_speed_ok=1 custom_key_dial_ok=1",
                    "FX6_R54_REMAIN_SHOOT_EVF_BRIDGE remain_shoot_default_not_displayed_ok=1 remain_shoot_3modes_verified=3 fx3_has_builtin_evf=0 remain_shoot_evf_ok=1",
                    "FX6_R54_LANG_TELEMETRY lang=schinese font_bank=23 str_bank=19 run_27th_realhw_81st_live=1 r54_bridge_ok=1",
                    "FX6_STAGE_B_R54_BRIDGE round=54 faithful=1 nop_count=0 run_27th_realhw_81st_live=1 emmc_write_count=0",
                    "FX6_R54_CUSTOM_KEY_DIAL_PERSIST rear_dial_iso_ei_cine_ei_adapt_ok=1 custom_key_3domains_verified=3 slot1_vault_writes=0 r54b_ok=1",
                    "FX6_R54_CUSTOM_KEY_DIAL_RC=0",
                    "FX6_R54_REMAIN_SHOOT_EVF_INTEGRATED remain_shoot_3modes_verified=3 fx3_has_builtin_evf=0 surfaces_h0_eq_h3=16 e_nd_actuator_tx_count=0 raw_firmware_bytes_leaked=0 r54c_ok=1",
                ]
            )
            + "\n"
        )
        parsed = self.runner.extract_milestones(serial_text)
        r54_t = parsed["r54_telemetry"]
        self.assertEqual(r54_t["custom_key_dial_rc"], 0)
        self.assertEqual(r54_t["diff_set_init"]["diff_set_8items_verified"], 8)
        self.assertEqual(r54_t["diff_set_init"]["shutter_angle_unchecked_common_independent_ok"], 1)
        self.assertEqual(r54_t["diff_set_bridge"]["diff_set_ok"], 1)
        self.assertEqual(r54_t["custom_key_dial_bridge"]["rear_dial_iso_ei_ok"], 1)
        self.assertEqual(r54_t["remain_shoot_evf_bridge"]["fx3_has_builtin_evf"], 0)
        self.assertEqual(r54_t["lang_telemetry"]["lang"], "schinese")
        self.assertEqual(r54_t["lang_telemetry"]["run_27th_realhw_81st_live"], 1)
        self.assertEqual(r54_t["stage_b_bridge"]["round"], 54)
        self.assertEqual(r54_t["custom_key_dial_persist"]["r54b_ok"], 1)
        self.assertEqual(r54_t["remain_shoot_integrated"]["surfaces_h0_eq_h3"], 16)
        self.assertEqual(parsed["prefix_counts"]["FX6_R54_"], 8)

    def test_14_round54_parse_log_defaults_when_no_r54_lines_present(self) -> None:
        parsed = self.runner.extract_milestones("Linux version 4.9.337-scel+\n")
        self.assertIsNone(parsed["r54_telemetry"])
        self.assertEqual(parsed["prefix_counts"].get("FX6_R54_", 0), 0)

    def test_15_round54_runner_uses_fx6_r54_prefix_and_stage_label_and_r53_compat(self) -> None:
        self.assertIn('if args.round >= 54:\n        tmp_prefix = "fx6-r54"', self.runner_src)
        self.assertIn(
            "Milestone27thRealHw81stRunWave40DiffSetStillMv8ItemsShutterAngleCustomKeyDialIsoEiRemainShootEvfLess",
            self.runner_src,
        )
        self.assertIn("FX6_SCRATCH_DIR", self.runner_src)
        self.assertIn("# r53_test_compat:", self.runner_src)
        self.assertIn(", 54]", self.runner_src)

    def test_16_round54_wave40_intel_spec_documents_exact_3way_transitions_and_rules(self) -> None:
        for token in (
            "Different Set for Still/Mv",
            "Exposure Comp.",
            "Metering Mode",
            "White Balance",
            "Picture Profile",
            "Focus Mode",
            "Common -> Separate",
            "Separate -> Common",
            "Front dial",
            "Rear dial",
            "Control Wheel",
            "CAMSET01.DAT",
            "Remain Shoot Display",
            "ILME-FX3",
        ):
            self.assertIn(token, self.wave40_spec)

    def test_17_round54_summary_json_top_level_schema_and_milestone_metadata(self) -> None:
        d = self.summary
        self.assertEqual(
            d["schema"],
            "fx6-on-fx3-round54-realhw-diff-set-still-mv-custom-key-remain-shoot-qemu-v1",
        )
        self.assertEqual(d["round"], 54)
        self.assertIn("27th Real-HW QEMU Round", d["milestone"])
        self.assertIn("81 Live Runs", d["milestone"])
        self.assertEqual(d["date"], "2026-11-15")
        self.assertIn("4.9.337-scel+", d["kernel_version"])
        self.assertEqual(d["raw_firmware_bytes_leaked"], 0)

    def test_18_round54_summary_json_zero_host_path_and_scratch_leaks(self) -> None:
        for forbidden in (
            "/Users/",
            "/private/tmp/",
            "/var/folders/",
            "work/_scratch/",
            "work/_tests/",
        ):
            self.assertNotIn(forbidden, self.summary_raw)

    def test_19_round54_summary_audit_block_confirms_27th_round_81st_run_and_all_booleans(self) -> None:
        audit = self.summary["r54_realhw_diff_set_still_mv_custom_key_remain_shoot_audit"]
        self.assertEqual(audit["round"], 54)
        self.assertEqual(audit["milestone"], 54)
        self.assertEqual(audit["milestone221_qemu_rounds"], 27)
        self.assertEqual(audit["milestone221_qemu_runs"], 81)
        self.assertEqual(audit["milestone233_qemu_rounds"], 27)
        self.assertEqual(audit["milestone233_qemu_runs"], 81)
        self.assertEqual(audit["milestone254_qemu_rounds"], 27)
        self.assertEqual(audit["milestone254_qemu_runs"], 81)
        self.assertEqual(audit["total_runs"], 3)
        for k, v in audit.items():
            if isinstance(v, bool):
                self.assertTrue(v, f"Expected audit boolean {k} to be True")

    def test_20_round54_all_3_runs_present_with_kernel_4_9_337_and_zero_crashes_writes(self) -> None:
        runs = self.summary["runs"]
        self.assertEqual(list(runs.keys()), list(self.EXPECTED_RUN_KEYS))
        for rk, rv in runs.items():
            self.assertEqual(rv["round"], 54, rk)
            self.assertIn("4.9.337-scel+", rv["kernel_version"], rk)
            self.assertEqual(rv["nop_count"], 0, rk)
            self.assertEqual(rv["crashes"], 0, rk)
            self.assertEqual(rv["emmc_write_count"], 0, rk)
            self.assertGreater(rv["wall_elapsed_sec"], 0.0, rk)

    def test_21_round54_r54a_diff_set_8items_and_common_to_separate_custom_wb_exception(self) -> None:
        init_t = self.summary["runs"]["r54a_diff_set_still_mv_shutter_angle_big6_schinese"][
            "r54_telemetry"
        ]["diff_set_init"]
        self.assertEqual(init_t["fx3_diff_set_node_ok"], 1)
        self.assertEqual(init_t["diff_set_default_unchecked_ok"], 1)
        self.assertEqual(init_t["invalid_diff_item_rc"], -22)
        self.assertEqual(init_t["diff_set_8items_verified"], 8)
        self.assertEqual(init_t["common_to_separate_8items_copy_ok"], 1)
        self.assertEqual(init_t["common_to_separate_custom_wb_still_only_ok"], 1)
        self.assertEqual(init_t["diff_set_transition_corruption_events"], 0)

    def test_22_round54_r54a_diff_set_separate_to_common_5_resets_and_3_still_exceptions(self) -> None:
        init_t = self.summary["runs"]["r54a_diff_set_still_mv_shutter_angle_big6_schinese"][
            "r54_telemetry"
        ]["diff_set_init"]
        self.assertEqual(init_t["separate_to_common_5items_reset_defaults_ok"], 1)
        self.assertEqual(init_t["separate_to_common_3exceptions_retain_still_ok"], 1)
        self.assertEqual(init_t["diff_set_survives_camreset_ok"], 1)
        self.assertEqual(init_t["diff_set_survives_netreset_ok"], 1)
        self.assertEqual(init_t["initialize_restores_diff_set_defaults_ok"], 1)

    def test_23_round54_r54a_shutter_mode_angle_override_independent_when_common(self) -> None:
        init_t = self.summary["runs"]["r54a_diff_set_still_mv_shutter_angle_big6_schinese"][
            "r54_telemetry"
        ]["diff_set_init"]
        self.assertEqual(init_t["shutter_angle_unchecked_common_independent_ok"], 1)
        self.assertEqual(init_t["shutter_angle_common_bleed_events"], 0)

    def test_24_round54_r54a_p2_cnflasha_and_slot1_ro_guards_intact(self) -> None:
        init_t = self.summary["runs"]["r54a_diff_set_still_mv_shutter_angle_big6_schinese"][
            "r54_telemetry"
        ]["diff_set_init"]
        self.assertEqual(init_t["p2_write_blocked_rc"], -30)
        self.assertEqual(init_t["p2_sha256_match"], 1)
        self.assertEqual(init_t["cnflasha_sha256_match"], 1)
        self.assertEqual(init_t["slot1_vault_sha256_match"], 1)
        self.assertEqual(init_t["cnflasha_writes"], 0)
        self.assertEqual(init_t["appfw_present"], 1)
        self.assertEqual(init_t["shim_present"], 1)
        self.assertEqual(init_t["emmc_write_count"], 0)
        self.assertEqual(init_t["r54_init_ok"], 1)

    def test_25_round54_r54a_stage_b_schinese_lang_telemetry_and_bridges(self) -> None:
        r54a_t = self.summary["runs"]["r54a_diff_set_still_mv_shutter_angle_big6_schinese"][
            "r54_telemetry"
        ]
        lt = r54a_t["lang_telemetry"]
        self.assertEqual(lt["lang"], "schinese")
        self.assertEqual(lt["bk4_lang_id"], "0x02cf019c")
        self.assertEqual(lt["bk4_lang_val"], "0x19")
        self.assertEqual(lt["lang_enum"], "0x2b45_CHINESE_SIMPLIFIED")
        self.assertEqual(lt["font_bank"], 23)
        self.assertEqual(lt["str_bank"], 19)
        self.assertEqual(lt["gpe_fb"], 0)
        self.assertEqual(lt["run_27th_realhw_81st_live"], 1)
        self.assertEqual(lt["fx3_has_builtin_evf"], 0)
        self.assertEqual(lt["finder_monitor_eye_sensor_spoof_events"], 0)
        self.assertEqual(lt["e_nd_actuator_tx_count"], 0)
        self.assertEqual(lt["raw_firmware_bytes_leaked"], 0)
        sb = r54a_t["stage_b_bridge"]
        self.assertEqual(sb["round"], 54)
        self.assertEqual(sb["faithful"], 1)
        self.assertEqual(sb["nop_count"], 0)
        self.assertEqual(sb["diff_set_8items_shutter_angle_override"], 1)
        self.assertEqual(sb["custom_key_dial_iso_ei_persist"], 1)
        self.assertEqual(sb["remain_shoot_still_buffer_evf_less"], 1)

    def test_26_round54_r54a_stage_b_diff_set_custom_key_and_remain_shoot_bridges(self) -> None:
        r54a_t = self.summary["runs"]["r54a_diff_set_still_mv_shutter_angle_big6_schinese"][
            "r54_telemetry"
        ]
        db = r54a_t["diff_set_bridge"]
        self.assertEqual(db["diff_set_8items_verified"], 8)
        self.assertEqual(db["common_to_separate_custom_wb_still_only_ok"], 1)
        self.assertEqual(db["separate_to_common_3exceptions_retain_still_ok"], 1)
        self.assertEqual(db["shutter_angle_unchecked_common_independent_ok"], 1)
        self.assertEqual(db["diff_set_ok"], 1)
        cb = r54a_t["custom_key_dial_bridge"]
        self.assertEqual(cb["front_dial_aperture_ok"], 1)
        self.assertEqual(cb["rear_dial_iso_ei_ok"], 1)
        self.assertEqual(cb["control_wheel_shutter_speed_ok"], 1)
        self.assertEqual(cb["mydial_1_3_verified"], 3)
        self.assertEqual(cb["recall_custom_hold_1_3_verified"], 3)
        self.assertEqual(cb["custom_key_dial_ok"], 1)
        rb = r54a_t["remain_shoot_evf_bridge"]
        self.assertEqual(rb["remain_shoot_default_not_displayed_ok"], 1)
        self.assertEqual(rb["remain_shoot_3modes_verified"], 3)
        self.assertEqual(rb["remain_shoot_still_buffer_only_ok"], 1)
        self.assertEqual(rb["remain_shoot_movie_card_time_spoof_events"], 0)
        self.assertEqual(rb["fx3_has_builtin_evf"], 0)
        self.assertEqual(rb["remain_shoot_evf_ok"], 1)

    def test_27_round54_r54a_gpe0_readback_exact_346686_pixels_and_87_colors(self) -> None:
        r54a = self.summary["runs"]["r54a_diff_set_still_mv_shutter_angle_big6_schinese"]
        self.assertEqual(r54a["target_presenter"], "31procam_big6_menu_home_presenter")
        self.assertEqual(r54a["target_sid"], "0x0a")
        self.assertGreaterEqual(r54a["total_threads_seen"], 150)
        gpe0 = r54a["gpe0_readback"]
        self.assertTrue(gpe0["present"])
        self.assertEqual(gpe0["bytes"], 2211840)
        self.assertEqual(gpe0["total_pixels"], 552960)
        self.assertEqual(gpe0["nonzero_pixels"], 346686)
        self.assertEqual(gpe0["unique_colors"], 87)

    def test_28_round54_r54a_stage_b_manifest_13_hashes_and_r54_metadata(self) -> None:
        sb = self.summary["runs"]["r54a_diff_set_still_mv_shutter_angle_big6_schinese"]["stage_b"]
        self.assertEqual(sb["manifest_count"], 13)
        self.assertEqual(len(sb["manifest_items"]), 13)
        for item in sb["manifest_items"]:
            self.assertEqual(len(item["sha256"]), 64)
        r54_meta = sb["r54"]
        self.assertEqual(r54_meta["r54_mode"], "diff_set_still_mv_shutter_angle_big6")
        self.assertEqual(
            r54_meta["diff_set_8_items"],
            [
                "Aperture",
                "Shutter Speed",
                "ISO",
                "Exposure Comp.",
                "Metering Mode",
                "White Balance",
                "Picture Profile",
                "Focus Mode",
            ],
        )
        self.assertEqual(
            r54_meta["diff_set_separate_to_common_retains_still_exceptions"],
            ["Aperture", "Shutter Speed", "Custom White Balance"],
        )
        self.assertEqual(r54_meta["front_dial_default"], "Aperture")
        self.assertEqual(r54_meta["rear_dial_default"], "ISO/EI")
        self.assertEqual(r54_meta["control_wheel_default"], "Shutter Speed")
        self.assertEqual(
            r54_meta["remain_shoot_display_modes"],
            ["Not Displayed", "Always Display", "Shoot-Only Display"],
        )

    def test_29_round54_r54b_custom_key_dial_defaults_iso_ei_and_3domains(self) -> None:
        r54b_t = self.summary["runs"]["r54b_custom_key_dial_iso_ei_camset_persist_guard"][
            "r54_telemetry"
        ]
        self.assertEqual(r54b_t["custom_key_dial_rc"], 0)
        ck = r54b_t["custom_key_dial_persist"]
        self.assertEqual(ck["fx3_custom_key_dial_node_ok"], 1)
        self.assertEqual(ck["front_dial_aperture_default_ok"], 1)
        self.assertEqual(ck["rear_dial_iso_ei_default_ok"], 1)
        self.assertEqual(ck["control_wheel_shutter_speed_default_ok"], 1)
        self.assertEqual(ck["rear_dial_iso_ei_cine_ei_adapt_ok"], 1)
        self.assertEqual(ck["custom_key_3domains_verified"], 3)

    def test_30_round54_r54b_follow_custom_mydial_1_3_and_recall_custom_hold_1_3(self) -> None:
        ck = self.summary["runs"]["r54b_custom_key_dial_iso_ei_camset_persist_guard"][
            "r54_telemetry"
        ]["custom_key_dial_persist"]
        self.assertEqual(ck["follow_custom_movie_inherits_still_ok"], 1)
        self.assertEqual(ck["mydial_1_3_slots_verified"], 3)
        self.assertEqual(ck["mydial_release_restores_base_dials_ok"], 1)
        self.assertEqual(ck["recall_custom_hold_1_3_verified"], 3)

    def test_31_round54_r54b_custom_key_dial_survives_camreset_netreset_cleared_by_init(self) -> None:
        ck = self.summary["runs"]["r54b_custom_key_dial_iso_ei_camset_persist_guard"][
            "r54_telemetry"
        ]["custom_key_dial_persist"]
        self.assertEqual(ck["custom_key_dial_survives_camreset_ok"], 1)
        self.assertEqual(ck["custom_key_dial_survives_netreset_ok"], 1)
        self.assertEqual(ck["initialize_restores_custom_key_dial_defaults_ok"], 1)

    def test_32_round54_r54b_camset01_roundtrip_and_slot1_vault_read_only(self) -> None:
        ck = self.summary["runs"]["r54b_custom_key_dial_iso_ei_camset_persist_guard"][
            "r54_telemetry"
        ]["custom_key_dial_persist"]
        self.assertEqual(ck["camset01_custom_key_dial_roundtrip_ok"], 1)
        self.assertEqual(ck["slot1_vault_ro_blocked_rc"], -30)
        self.assertEqual(ck["slot1_vault_sha256_match"], 1)
        self.assertEqual(ck["slot1_vault_writes"], 0)
        self.assertEqual(ck["p2_write_blocked_rc"], -30)
        self.assertEqual(ck["cnflasha_ro_blocked_rc"], -30)
        self.assertEqual(ck["cnflasha_writes"], 0)
        self.assertEqual(ck["emmc_write_count"], 0)
        self.assertEqual(ck["r54b_ok"], 1)

    def test_33_round54_r54c_remain_shoot_display_modes_and_still_buffer_scope_only(self) -> None:
        rs = self.summary["runs"]["r54c_remain_shoot_evf_less_integrated_big6_schinese"][
            "r54_telemetry"
        ]["remain_shoot_integrated"]
        self.assertEqual(rs["fx3_remain_shoot_node_ok"], 1)
        self.assertEqual(rs["remain_shoot_default_not_displayed_ok"], 1)
        self.assertEqual(rs["invalid_remain_shoot_rc"], -22)
        self.assertEqual(rs["remain_shoot_3modes_verified"], 3)
        self.assertEqual(rs["remain_shoot_still_buffer_scope_ok"], 1)
        self.assertEqual(rs["remain_shoot_movie_card_time_spoof_events"], 0)
        self.assertEqual(rs["remain_shoot_survives_camreset_netreset_ok"], 1)

    def test_34_round54_r54c_evf_less_topology_zero_spoofing_and_16_h0_eq_h3(self) -> None:
        rs = self.summary["runs"]["r54c_remain_shoot_evf_less_integrated_big6_schinese"][
            "r54_telemetry"
        ]["remain_shoot_integrated"]
        self.assertEqual(rs["fx3_has_builtin_evf"], 0)
        self.assertEqual(rs["finder_monitor_rejected_rc"], -95)
        self.assertEqual(rs["finder_monitor_eye_sensor_spoof_events"], 0)
        self.assertEqual(rs["evf_less_fx3_topology_ok"], 1)
        self.assertEqual(rs["wave40_3pillars_integrated_ok"], 1)
        self.assertEqual(rs["dlopen_ok"], 1)
        self.assertEqual(rs["surfaces_verified"], 16)
        self.assertEqual(rs["surfaces_h0_eq_h3"], 16)
        self.assertEqual(rs["drift_bits"], 0)
        self.assertEqual(rs["e_nd_actuator_tx_count"], 0)
        self.assertEqual(rs["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(rs["emmc_write_count"], 0)
        self.assertEqual(rs["r54c_ok"], 1)

    def test_35_round54_r54c_integrated_renders_valid_big6_gpe0_readback(self) -> None:
        r54c = self.summary["runs"]["r54c_remain_shoot_evf_less_integrated_big6_schinese"]
        self.assertEqual(r54c["target_presenter"], "31procam_big6_menu_home_presenter")
        self.assertEqual(r54c["target_sid"], "0x0a")
        gpe0 = r54c["gpe0_readback"]
        self.assertTrue(gpe0["present"])
        self.assertEqual(gpe0["bytes"], 2211840)
        self.assertEqual(gpe0["total_pixels"], 552960)
        self.assertEqual(gpe0["nonzero_pixels"], 346206)
        self.assertGreaterEqual(gpe0["nonzero_pixels"], 346000)
        self.assertEqual(gpe0["unique_colors"], 87)

    def test_36_round54_realhw_mechanisms_verified_6_blocks_match_run_telemetry(self) -> None:
        rm = self.summary["realhw_mechanisms_verified"]
        self.assertEqual(len(rm), 6)
        r54a = self.summary["runs"]["r54a_diff_set_still_mv_shutter_angle_big6_schinese"][
            "r54_telemetry"
        ]
        r54b = self.summary["runs"]["r54b_custom_key_dial_iso_ei_camset_persist_guard"][
            "r54_telemetry"
        ]
        r54c = self.summary["runs"]["r54c_remain_shoot_evf_less_integrated_big6_schinese"][
            "r54_telemetry"
        ]
        self.assertEqual(
            rm["diff_set_still_mv_8items_asymmetric_and_shutter_angle_init"],
            r54a["diff_set_init"],
        )
        self.assertEqual(rm["diff_set_still_mv_stage_b_bridge"], r54a["diff_set_bridge"])
        self.assertEqual(
            rm["custom_key_dial_iso_ei_stage_b_bridge"], r54a["custom_key_dial_bridge"]
        )
        self.assertEqual(
            rm["remain_shoot_evf_less_stage_b_bridge"], r54a["remain_shoot_evf_bridge"]
        )
        self.assertEqual(
            rm["custom_key_dial_iso_ei_camset01_persist_guard"],
            r54b["custom_key_dial_persist"],
        )
        self.assertEqual(
            rm["remain_shoot_evf_less_integrated_and_16_h0_h3"],
            r54c["remain_shoot_integrated"],
        )

    def test_37_round54_all_3_setup_features_survive_camreset_and_netreset(self) -> None:
        init_a = self.summary["runs"]["r54a_diff_set_still_mv_shutter_angle_big6_schinese"][
            "r54_telemetry"
        ]["diff_set_init"]
        ck_b = self.summary["runs"]["r54b_custom_key_dial_iso_ei_camset_persist_guard"][
            "r54_telemetry"
        ]["custom_key_dial_persist"]
        rs_c = self.summary["runs"]["r54c_remain_shoot_evf_less_integrated_big6_schinese"][
            "r54_telemetry"
        ]["remain_shoot_integrated"]
        self.assertEqual(init_a["diff_set_survives_camreset_ok"], 1)
        self.assertEqual(init_a["diff_set_survives_netreset_ok"], 1)
        self.assertEqual(ck_b["custom_key_dial_survives_camreset_ok"], 1)
        self.assertEqual(ck_b["custom_key_dial_survives_netreset_ok"], 1)
        self.assertEqual(rs_c["remain_shoot_survives_camreset_netreset_ok"], 1)

    def test_38_round54_cross_round_consistency_with_r53_setup_vs_netreset_split(self) -> None:
        self.assertEqual(self.r53_summary["round"], 53)
        r53_init = self.r53_summary["runs"]["r53a_display_quality_bt_rmt_big6_schinese"][
            "r53_telemetry"
        ]["dispqual_btrmt_init"]
        r54_init = self.summary["runs"]["r54a_diff_set_still_mv_shutter_angle_big6_schinese"][
            "r54_telemetry"
        ]["diff_set_init"]
        self.assertEqual(r53_init["display_quality_survives_camreset_ok"], 1)
        self.assertEqual(r53_init["display_quality_survives_netreset_ok"], 1)
        self.assertEqual(r54_init["diff_set_survives_camreset_ok"], 1)
        self.assertEqual(r54_init["diff_set_survives_netreset_ok"], 1)

    def test_39_round54_cross_round_consistency_with_r52_my_dial_and_shutter_angle(self) -> None:
        self.assertEqual(self.r52_summary["round"], 52)
        li52 = self.r52_summary["runs"]["r52a_lock_op_parts_mydial_big6_schinese"][
            "r52_telemetry"
        ]["lock_op_init"]
        ck54 = self.summary["runs"]["r54b_custom_key_dial_iso_ei_camset_persist_guard"][
            "r54_telemetry"
        ]["custom_key_dial_persist"]
        self.assertEqual(li52["mydial_1_3_temp_override_verified"], 3)
        self.assertEqual(ck54["mydial_1_3_slots_verified"], 3)
        init54 = self.summary["runs"]["r54a_diff_set_still_mv_shutter_angle_big6_schinese"][
            "r54_telemetry"
        ]["diff_set_init"]
        self.assertEqual(init54["shutter_angle_unchecked_common_independent_ok"], 1)

    def test_40_round54_cross_round_consistency_with_r50_camset01_custom_wb_and_slot1_ro(self) -> None:
        self.assertEqual(self.r50_summary["round"], 50)
        ck54 = self.summary["runs"]["r54b_custom_key_dial_iso_ei_camset_persist_guard"][
            "r54_telemetry"
        ]["custom_key_dial_persist"]
        self.assertEqual(ck54["camset01_custom_key_dial_roundtrip_ok"], 1)
        self.assertEqual(ck54["slot1_vault_ro_blocked_rc"], -30)
        self.assertEqual(ck54["slot1_vault_writes"], 0)
        diff54 = self.summary["runs"]["r54a_diff_set_still_mv_shutter_angle_big6_schinese"][
            "r54_telemetry"
        ]["diff_set_init"]
        self.assertEqual(diff54["common_to_separate_custom_wb_still_only_ok"], 1)

    def test_41_round54_unexecuted_physical_camera_bench_boundaries_documented(self) -> None:
        bounds = self.summary["unexecuted_physical_camera_bench_boundaries"]
        self.assertEqual(len(bounds), 3)
        joined = " ".join(bounds)
        self.assertIn("Different Set for Still/Mv", joined)
        self.assertIn("Custom Key/Dial Set.", joined)
        self.assertIn("Remain Shoot Display", joined)

    def test_42_round54_alpha_png_exists_under_50kib_and_matches_summary_sha256(self) -> None:
        pe = self.summary["runs"]["r54a_diff_set_still_mv_shutter_angle_big6_schinese"][
            "png_exports"
        ]
        self.assertLess(len(self.alpha_png_bytes), 50000)
        self.assertLess(len(self.alpha_png_bytes), 51200)
        self.assertEqual(len(self.alpha_png_bytes), pe["alpha_bytes"])
        self.assertEqual(
            hashlib.sha256(self.alpha_png_bytes).hexdigest(), pe["alpha_sha256"]
        )

    def test_43_round54_composited_png_exists_under_50kib_and_matches_summary_sha256(self) -> None:
        pe = self.summary["runs"]["r54a_diff_set_still_mv_shutter_angle_big6_schinese"][
            "png_exports"
        ]
        self.assertLess(len(self.comp_png_bytes), 50000)
        self.assertLess(len(self.comp_png_bytes), 51200)
        self.assertEqual(len(self.comp_png_bytes), pe["composited_bytes"])
        self.assertEqual(
            hashlib.sha256(self.comp_png_bytes).hexdigest(), pe["composited_sha256"]
        )

    def test_44_round54_alpha_png_valid_1024x540_rgba_with_transparent_and_opaque_pixels(self) -> None:
        self.assertEqual(self.alpha_dims, (1024, 540))
        self.assertEqual(self.alpha_transparent, 206274)
        self.assertGreater(self.alpha_opaque, 300000)

    def test_45_round54_composited_png_valid_1024x540_rgba_100pct_opaque(self) -> None:
        self.assertEqual(self.comp_dims, (1024, 540))
        self.assertEqual(self.comp_opaque, 1024 * 540)

    def test_46_round54_report_readme_documents_all_3_runs_and_zero_host_leaks(self) -> None:
        for token in (
            "Round 54",
            "27th Real-HW",
            "81st Live Run",
            "r54a",
            "r54b",
            "r54c",
            "Different Set for Still/Mv",
            "Custom Key/Dial Set.",
            "Remain Shoot Display",
            "346,686",
            "346,206",
            "r54a-diff-set-customkey-big6-schinese-alpha.png",
            "r54a-diff-set-customkey-big6-schinese-composited.png",
        ):
            self.assertIn(token, self.r54_readme)
        for forbidden in ("/Users/", "/private/tmp/", "/var/folders/", "work/_scratch/"):
            self.assertNotIn(forbidden, self.r54_readme)

    def test_47_round54_closure_readme_section_54_present_and_accurate(self) -> None:
        self.assertIn("## 54. Round 54", self.closure_readme)
        self.assertIn("27th Real-HW Round", self.closure_readme)
        self.assertIn("81st Live Run", self.closure_readme)
        self.assertIn(
            "2026-11-15-round54-realhw-diff-set-still-mv-custom-key-remain-shoot-qemu",
            self.closure_readme,
        )

    def test_48_round54_27_realhw_qemu_rounds_r28_to_r54_81_runs_and_54_pngs_continuity(self) -> None:
        png_total = 0
        for r in range(28, 55):
            matches = list((REPO_ROOT / "reports").glob(f"2026-??-??-round{r}-*"))
            self.assertEqual(len(matches), 1, f"Expected 1 report dir for Round {r}")
            pngs = list((matches[0] / "assets").glob("*.png"))
            self.assertEqual(len(pngs), 2, f"Expected 2 PNGs for Round {r}")
            for p in pngs:
                self.assertLess(p.stat().st_size, 51200, str(p))
            png_total += len(pngs)
        self.assertEqual(png_total, 54)
        audit = self.summary["r54_realhw_diff_set_still_mv_custom_key_remain_shoot_audit"]
        self.assertEqual(audit["milestone233_qemu_rounds"], 27)
        self.assertEqual(audit["milestone233_qemu_runs"], 81)

    def test_49_round54_dual_mode_clean_room_toggle_parity_on_summary(self) -> None:
        for clean_flag in ("0", "1"):
            with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                d = json.loads(self.summary_raw)
                self.assertEqual(d["round"], 54)
                self.assertEqual(
                    d["runs"]["r54a_diff_set_still_mv_shutter_angle_big6_schinese"][
                        "r54_telemetry"
                    ]["diff_set_init"]["diff_set_8items_verified"],
                    8,
                )
                self.assertEqual(
                    d["runs"]["r54b_custom_key_dial_iso_ei_camset_persist_guard"][
                        "r54_telemetry"
                    ]["custom_key_dial_persist"]["custom_key_3domains_verified"],
                    3,
                )
                self.assertEqual(
                    d["runs"]["r54c_remain_shoot_evf_less_integrated_big6_schinese"][
                        "r54_telemetry"
                    ]["remain_shoot_integrated"]["surfaces_h0_eq_h3"],
                    16,
                )

    def test_50_round54_r54a_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"]["r54a_diff_set_still_mv_shutter_angle_big6_schinese"][
            "r54_telemetry"
        ]["diff_set_init"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_51_round54_r54b_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"]["r54b_custom_key_dial_iso_ei_camset_persist_guard"][
            "r54_telemetry"
        ]["custom_key_dial_persist"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_52_round54_r54c_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"]["r54c_remain_shoot_evf_less_integrated_big6_schinese"][
            "r54_telemetry"
        ]["remain_shoot_integrated"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_53_round54_r54a_top_colors_transparent_plus_nonzero_equals_total_pixels(self) -> None:
        gpe = self.summary["runs"]["r54a_diff_set_still_mv_shutter_angle_big6_schinese"][
            "gpe0_readback"
        ]
        color_map = {row["argb"]: row["pixels"] for row in gpe["top_colors"]}
        self.assertIn("0x00000000", color_map)
        self.assertIn("0xff000000", color_map)
        self.assertEqual(color_map["0x00000000"] + gpe["nonzero_pixels"], gpe["total_pixels"])

    def test_54_round54_r54c_top_colors_transparent_plus_nonzero_equals_total_pixels(self) -> None:
        gpe = self.summary["runs"]["r54c_remain_shoot_evf_less_integrated_big6_schinese"][
            "gpe0_readback"
        ]
        color_map = {row["argb"]: row["pixels"] for row in gpe["top_colors"]}
        self.assertIn("0x00000000", color_map)
        self.assertEqual(color_map["0x00000000"] + gpe["nonzero_pixels"], gpe["total_pixels"])

    def test_55_round54_r54a_and_r54c_wall_elapsed_and_duration_budget_sanity(self) -> None:
        r54a = self.summary["runs"]["r54a_diff_set_still_mv_shutter_angle_big6_schinese"]
        r54c = self.summary["runs"]["r54c_remain_shoot_evf_less_integrated_big6_schinese"]
        self.assertGreaterEqual(r54a["duration_budget_sec"], 70)
        self.assertLessEqual(r54a["duration_budget_sec"], 120)
        self.assertGreater(r54a["wall_elapsed_sec"], 50.0)
        self.assertLess(r54a["wall_elapsed_sec"], 120.0)
        self.assertGreaterEqual(r54c["duration_budget_sec"], 70)
        self.assertLessEqual(r54c["duration_budget_sec"], 120)
        self.assertGreater(r54c["wall_elapsed_sec"], 50.0)
        self.assertLess(r54c["wall_elapsed_sec"], 120.0)

    def test_56_round54_r54b_fast_early_exit_wall_elapsed_under_20s(self) -> None:
        r54b = self.summary["runs"]["r54b_custom_key_dial_iso_ei_camset_persist_guard"]
        self.assertEqual(r54b["duration_budget_sec"], 35)
        self.assertGreater(r54b["wall_elapsed_sec"], 1.0)
        self.assertLess(r54b["wall_elapsed_sec"], 20.0)
        self.assertTrue(r54b["gpe0_readback"]["skipped_stock_fx3_mode"])

    def test_57_round54_faithful_invariants_preserved_across_all_3_runs(self) -> None:
        for rk, rv in self.summary["runs"].items():
            fi = rv["faithful_invariants"]
            self.assertEqual(fi["FX6_NATIVE_FAITHFUL"], 1, rk)
            self.assertEqual(fi["subst_color"], 0, rk)
            self.assertEqual(fi["subst_image"], 0, rk)
            self.assertEqual(fi["forced_render"], 0, rk)
            self.assertEqual(fi["skipped_node"], 0, rk)
            self.assertEqual(fi["lock_bypass"], 0, rk)

    def test_58_round54_all_3_runs_stage_b_manifest_count_13(self) -> None:
        for rk, rv in self.summary["runs"].items():
            self.assertEqual(rv["stage_b"]["manifest_count"], 13, rk)
            self.assertEqual(len(rv["stage_b"]["manifest_items"]), 13, rk)

    def test_59_round54_r54c_stage_b_r54_bridges_and_zero_evf_spoof_verified(self) -> None:
        r54c_t = self.summary["runs"]["r54c_remain_shoot_evf_less_integrated_big6_schinese"][
            "r54_telemetry"
        ]
        self.assertEqual(r54c_t["diff_set_bridge"]["diff_set_ok"], 1)
        self.assertEqual(r54c_t["custom_key_dial_bridge"]["custom_key_dial_ok"], 1)
        self.assertEqual(r54c_t["remain_shoot_evf_bridge"]["remain_shoot_evf_ok"], 1)
        self.assertEqual(
            r54c_t["remain_shoot_evf_bridge"]["finder_monitor_eye_sensor_spoof_events"], 0
        )
        self.assertEqual(r54c_t["stage_b_bridge"]["e_nd_actuator_tx_count"], 0)

    def test_60_round54_all_3_runs_prefix_counts_include_fx6_r54(self) -> None:
        r54a_pc = self.summary["runs"]["r54a_diff_set_still_mv_shutter_angle_big6_schinese"][
            "prefix_counts"
        ]
        r54b_pc = self.summary["runs"]["r54b_custom_key_dial_iso_ei_camset_persist_guard"][
            "prefix_counts"
        ]
        r54c_pc = self.summary["runs"]["r54c_remain_shoot_evf_less_integrated_big6_schinese"][
            "prefix_counts"
        ]
        self.assertGreater(r54a_pc["FX6_R54_"], 10)
        self.assertEqual(r54b_pc["FX6_R54_"], 3)
        self.assertGreater(r54c_pc["FX6_R54_"], 10)

    def test_61_round54_r54_meta_invariants_across_all_3_runs(self) -> None:
        for rk, rv in self.summary["runs"].items():
            m = rv["stage_b"]["r54"]
            self.assertTrue(m["diff_set_common_to_separate_custom_wb_still_only"], rk)
            self.assertTrue(
                m["shutter_mode_angle_independent_when_shutter_speed_unchecked_common"], rk
            )
            self.assertEqual(m["shutter_angle_common_bleed_events"], 0, rk)
            self.assertTrue(m["remain_shoot_still_continuous_buffer_scope_only"], rk)
            self.assertFalse(m["displays_movie_card_remaining_time"], rk)
            self.assertEqual(m["remain_shoot_movie_card_time_spoof_events"], 0, rk)
            self.assertFalse(m["fx3_has_builtin_evf"], rk)
            self.assertFalse(m["finder_monitor_eye_sensor_present"], rk)
            self.assertEqual(m["finder_monitor_eye_sensor_spoof_events"], 0, rk)
            self.assertEqual(m["e_nd_actuator_tx_count"], 0, rk)
            self.assertEqual(m["raw_firmware_bytes_leaked"], 0, rk)

    def test_62_round54_no_stray_temp_files_in_repo_root(self) -> None:
        for bad_name in ("tmp", "scratch", ".worktrees"):
            self.assertFalse((REPO_ROOT / bad_name).exists(), bad_name)

    def test_63_round54_port_8768_untouched_in_round54_reports(self) -> None:
        self.assertNotIn("8768", self.summary_raw)
        self.assertNotIn("8768", self.r54_readme)

    def test_64_round54_test_suite_contains_at_least_60_unit_tests(self) -> None:
        methods = [m for m in dir(self) if m.startswith("test_")]
        self.assertEqual(len(methods), 64)


if __name__ == "__main__":
    unittest.main()
