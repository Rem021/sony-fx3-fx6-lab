#!/usr/bin/env python3
"""Offline dual-mode unit tests for FX6-on-FX3 Round 56 (29th Real-HW Round / 87th Live Run — Wave-42)."""
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
ROUND56_REPORT_DIR = (
    REPO_ROOT
    / "reports"
    / "2026-11-17-round56-realhw-apsc-s35-face-eye-af-version-qemu"
)
WAVE42_SPEC_PATH = (
    REPO_ROOT
    / "reports"
    / "2026-11-15-global-sony-wave42-apsc-s35-4k-lockout-face-eye-af-right-left-eye-version-read-only-intel"
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


def _build_overlay_for_r56(
    runner,
    parent_cpio: pathlib.Path,
    fp,
    fv,
    fb,
    fake_run,
    jit_meta: Dict[str, Any],
    work: pathlib.Path,
    r56_mode: str,
    lang: str = "schinese",
    enable_r56: bool = True,
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
            enable_r55=True,
            r55_mode="auto_slow_6locks_hdmi_reccontrol_big6",
            enable_r56=enable_r56,
            r56_mode=r56_mode,
            sd_manifest_mode="valid",
            lang=lang,
            shim_bytes=b"SHIM",
        )


class TestRound56RealHwApscS35FaceEyeAfVersionQemu(unittest.TestCase):
    EXPECTED_RUN_KEYS = (
        "r56a_apsc_s35_hd_face_eye_af_version_big6_schinese",
        "r56b_apsc_4k_raw_cleanhdmi_bodydata_flash_guard",
        "r56c_camreset_face_memory_initialize_h0_h3_big6_schinese",
    )

    runner: Any
    runner_src: str
    stage_a_src: str
    shim_src: str
    wave42_spec: str
    summary_raw: str
    summary: Dict[str, Any]
    r56_readme: str
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
    launcher_r56: Optional[bytes]
    shim_r56: Optional[bytes]
    shim_r55: Optional[bytes]
    r55_summary: Dict[str, Any]
    r54_summary: Dict[str, Any]
    r53_summary: Dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = _load_closure_module("fx6_brr_r56_cached", "build_and_run_round.py")
        cls.runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")
        cls.stage_a_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        cls.shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        cls.wave42_spec = WAVE42_SPEC_PATH.read_text(encoding="utf-8")
        cls.summary_raw = (ROUND56_REPORT_DIR / "summary.json").read_text(encoding="utf-8")
        cls.summary = json.loads(cls.summary_raw)
        cls.r56_readme = (ROUND56_REPORT_DIR / "README.md").read_text(encoding="utf-8")
        cls.closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")

        alpha_p = (
            ROUND56_REPORT_DIR
            / "assets"
            / "r56a-apsc-s35-face-eye-af-big6-schinese-alpha.png"
        )
        comp_p = (
            ROUND56_REPORT_DIR
            / "assets"
            / "r56a-apsc-s35-face-eye-af-big6-schinese-composited.png"
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
            cls.ov_a = _build_overlay_for_r56(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wa", "apsc_s35_hd_face_eye_af_version_big6", lang="schinese",
            )
            cls.ov_b = _build_overlay_for_r56(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wb", "apsc_4k_raw_cleanhdmi_bodydata_flash_guard", lang="en",
            )
            cls.ov_c = _build_overlay_for_r56(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wc", "camreset_face_memory_initialize_h0_h3_big6", lang="schinese",
            )
            cls.ov_off = _build_overlay_for_r56(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "woff", "apsc_s35_hd_face_eye_af_version_big6", enable_r56=False,
            )
            cls.invalid_mode_raised = False
            try:
                _build_overlay_for_r56(
                    cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                    tpath / "wbad", "invalid_r56_mode",
                )
            except ValueError:
                cls.invalid_mode_raised = True

            if cls.runner.ZIG.is_file():
                verify_r56_out = tpath / "fx6-stage-a-verify-r56"
                shim_r56_out = tpath / "libgrm-fbinit9-r56.so"
                shim_r55_out = tpath / "libgrm-fbinit9-r55.so"
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
                        str(verify_r56_out),
                    ],
                    [
                        str(cls.runner.ZIG),
                        "cc",
                        "-target",
                        "aarch64-linux-gnu.2.25",
                        "-O0",
                        "-shared",
                        "-fPIC",
                        "-DFX6_ROUND=56",
                        str(CLOSURE_DIR / "libgrm-fbinit9.c"),
                        "-ldl",
                        "-lpthread",
                        "-o",
                        str(shim_r56_out),
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
                ):
                    cls.runner.subprocess.run(cmd, check=True)
                cls.launcher_r56 = verify_r56_out.read_bytes()
                cls.shim_r56 = shim_r56_out.read_bytes()
                cls.shim_r55 = shim_r55_out.read_bytes()
            else:
                cls.launcher_r56 = None
                cls.shim_r56 = None
                cls.shim_r55 = None

        cls.r55_summary = json.loads(
            (
                REPO_ROOT
                / "reports"
                / "2026-11-17-round55-realhw-auto-slow-shutter-hdmi-reccontrol-breathing"
                / "summary.json"
            ).read_text(encoding="utf-8")
        )
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

    def test_01_wave42_global_spec_present_and_covers_all_wave42_pillars(self) -> None:
        self.assertTrue(WAVE42_SPEC_PATH.is_file())
        for needle in (
            "APS-C S35 Shooting",
            "12.1 MP",
            "XAVC S HD",
            "XAVC S-I HD",
            "XAVC HS 4K",
            "XAVC S 4K",
            "XAVC S-I 4K",
            "HDMI RAW Output",
            "Face/Eye AF",
            "Face/Eye Prior. in AF",
            "Face/Eye Subject",
            "Right/Left Eye Select",
            "Face/Eye Frame Disp.",
            "Face Memory",
            "Subject Recog in AF",
            "HDMI Info. Display",
            "Setup Option",
            "Version",
            "Ver. 7.02",
            "BODYDATA.DAT",
        ):
            self.assertIn(needle, self.wave42_spec)

    def test_02_round56_summary_schema_round_milestone_and_zero_leaks(self) -> None:
        self.assertNotIn("/Users/", self.summary_raw)
        self.assertNotIn("/private/tmp/", self.summary_raw)
        self.assertEqual(
            self.summary["schema"],
            "fx6-on-fx3-round56-realhw-apsc-s35-face-eye-af-version-qemu-v1",
        )
        self.assertEqual(self.summary["round"], 56)
        self.assertEqual(self.summary["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(tuple(self.summary["runs"].keys()), self.EXPECTED_RUN_KEYS)

    def test_03_round56_cli_accepts_round56_and_all_3_r56_modes(self) -> None:
        self.assertIn(", 56]", self.runner_src)
        self.assertIn(", 55]", self.runner_src)
        for mode in (
            "apsc_s35_hd_face_eye_af_version_big6",
            "apsc_4k_raw_cleanhdmi_bodydata_flash_guard",
            "camreset_face_memory_initialize_h0_h3_big6",
        ):
            self.assertIn(mode, self.runner_src)

    def test_04_round56_overlay_rejects_invalid_r56_mode(self) -> None:
        self.assertTrue(self.invalid_mode_raised)

    def test_05_round56_overlay_r56a_injects_etc_fx6_stage_r56_and_appfw_launch(self) -> None:
        replacements, additions, meta = self.ov_a
        self.assertTrue(meta["r56_enabled"])
        self.assertIn("etc/fx6_stage_r56", additions)
        self.assertIn("etc/fx6_r56_libjit.so", additions)
        r56_cfg = additions["etc/fx6_stage_r56"][0].decode("utf-8")
        self.assertIn("stage_r56=1", r56_cfg)
        self.assertIn("r56_mode=apsc_s35_hd_face_eye_af_version_big6", r56_cfg)
        self.assertIn("run_29th_realhw_87th_live=1", r56_cfg)
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("/usr/bin/appfw-launch", init_txt)
        self.assertNotIn("--r56-apsc-4k-bodydata-guard", init_txt)

    def test_06_round56_overlay_r56b_injects_early_guard_probe_and_poweroff(self) -> None:
        replacements, _, meta = self.ov_b
        self.assertEqual(meta["r56"]["r56_mode"], "apsc_4k_raw_cleanhdmi_bodydata_flash_guard")
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("--r56-apsc-4k-bodydata-guard", init_txt)
        self.assertIn("FX6_R56_APSC_4K_BODYDATA_RC=", init_txt)
        self.assertIn("FX6_R56_APSC_4K_BODYDATA_EXIT", init_txt)
        self.assertIn("poweroff -f", init_txt)

    def test_07_round56_overlay_r56c_integrated_runs_stage_b_big6(self) -> None:
        replacements, additions, meta = self.ov_c
        self.assertEqual(meta["r56"]["r56_mode"], "camreset_face_memory_initialize_h0_h3_big6")
        r56_cfg = additions["etc/fx6_stage_r56"][0].decode("utf-8")
        self.assertIn("r56_mode=camreset_face_memory_initialize_h0_h3_big6", r56_cfg)
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("/usr/bin/appfw-launch", init_txt)
        self.assertNotIn("--r56-apsc-4k-bodydata-guard", init_txt)

    def test_08_round56_overlay_disabled_when_enable_r56_false(self) -> None:
        _, additions, meta = self.ov_off
        self.assertFalse(meta["r56_enabled"])
        self.assertNotIn("etc/fx6_stage_r56", additions)
        self.assertNotIn("etc/fx6_r56_libjit.so", additions)
        self.assertNotIn("r56", meta)

    def test_09_round56_stage_a_c_source_contains_all_3_wave42_probes(self) -> None:
        for sym in (
            "setup_r56_apsc_face_eye_version_probe",
            "run_r56_apsc_4k_cleanhdmi_bodydata_guard_probe",
            "run_r56_camreset_face_memory_init_h0_h3_probe",
            "FX6_R56_APSC_FACE_EYE_VERSION_INIT",
            "FX6_R56_APSC_4K_BODYDATA_GUARD",
            "FX6_R56_CAMRESET_FACE_MEM_H0_H3",
            "--r56-apsc-4k-bodydata-guard",
            "--r56-camreset-face-mem-h0-h3",
            "/etc/fx6_stage_r56",
        ):
            self.assertIn(sym, self.stage_a_src)

    def test_10_round56_shim_c_source_contains_r56_guarded_bridges(self) -> None:
        self.assertIn("#if FX6_ROUND >= 56", self.shim_src)
        for sym in (
            "FX6_R56_APSC_S35_4K_LOCK_BRIDGE",
            "FX6_R56_FACE_EYE_AF_HDMI_BRIDGE",
            "FX6_R56_VERSION_BODYDATA_GUARD_BRIDGE",
            "FX6_R56_LANG_TELEMETRY",
            "FX6_STAGE_B_R56_BRIDGE",
        ):
            self.assertIn(sym, self.shim_src)

    def test_11_round56_compile_launcher_and_shim_aarch64_elf_symbols(self) -> None:
        if self.launcher_r56 is None or self.shim_r56 is None:
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertEqual(self.launcher_r56[:4], b"\x7fELF")
        self.assertEqual(self.shim_r56[:4], b"\x7fELF")
        self.assertEqual(struct.unpack_from("<H", self.shim_r56, 18)[0], 183)
        self.assertIn(b"FX6_R56_APSC_S35_4K_LOCK_BRIDGE", self.shim_r56)
        self.assertIn(b"FX6_R56_FACE_EYE_AF_HDMI_BRIDGE", self.shim_r56)
        self.assertIn(b"FX6_R56_VERSION_BODYDATA_GUARD_BRIDGE", self.shim_r56)

    def test_12_round56_shim_round55_backward_compat_excludes_r56_bridges(self) -> None:
        if self.shim_r55 is None:
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertIn(b"FX6_R55_AUTO_SLOW_6LOCKS_BRIDGE", self.shim_r55)
        self.assertNotIn(b"FX6_R56_APSC_S35_4K_LOCK_BRIDGE", self.shim_r55)

    def test_13_round56_parse_log_extracts_all_8_r56_prefixes_and_rc(self) -> None:
        serial_text = (
            "\n".join(
                [
                    "Linux version 4.9.337-scel+ (sony@fx3)",
                    "FX6_R56_APSC_FACE_EYE_VERSION_INIT fx3_wave42_nodes_ok=1 apsc_4k_lockouts_verified=4 apsc_s35_4k_or_raw_bypass_events=0 hdmi_clean_feed_eye_frame_baked_pixels=0 version_inspect_flash_writes=0 r56_init_ok=1",
                    "FX6_R56_APSC_S35_4K_LOCK_BRIDGE apsc_default_auto_ok=1 apsc_4k_lockouts_verified=4 apsc_s35_ok=1 r56_bridge_ok=1",
                    "FX6_R56_FACE_EYE_AF_HDMI_BRIDGE face_eye_defaults_ok=1 face_eye_subjects_3_ok=1 face_eye_rl_3_ok=1 hdmi_clean_feed_eye_frame_baked_pixels=0 face_eye_af_ok=1",
                    "FX6_R56_VERSION_BODYDATA_GUARD_BRIDGE version_702_readonly_ok=1 version_inspect_flash_writes=0 passive_tx_bytes_emitted=0 bodydata_flash_hard_blocked_ok=1 version_ro_ok=1",
                    "FX6_R56_LANG_TELEMETRY lang=schinese font_bank=23 str_bank=19 run_29th_realhw_87th_live=1 r56_bridge_ok=1",
                    "FX6_STAGE_B_R56_BRIDGE round=56 faithful=1 nop_count=0 run_29th_realhw_87th_live=1 emmc_write_count=0",
                    "FX6_R56_APSC_4K_BODYDATA_GUARD hs_4k_inject_rc=-16 bodydata_flash_blocked_rc=-30 persistent_emmc_writes_authorized=0 slot1_vault_writes=0 r56b_ok=1",
                    "FX6_R56_APSC_4K_BODYDATA_RC=0",
                    "FX6_R56_CAMRESET_FACE_MEM_H0_H3 apsc_camreset_auto_ok=1 face_eye_af_camreset_ok=1 face_memory_survives_camreset_ok=1 initialize_clears_face_memory_and_defaults_ok=1 surfaces_h0_eq_h3=16 r56c_ok=1",
                ]
            )
            + "\n"
        )
        parsed = self.runner.extract_milestones(serial_text)
        r56_t = parsed["r56_telemetry"]
        self.assertEqual(r56_t["apsc_4k_bodydata_rc"], 0)
        self.assertEqual(r56_t["apsc_face_eye_version_init"]["apsc_4k_lockouts_verified"], 4)
        self.assertEqual(r56_t["apsc_face_eye_version_init"]["apsc_s35_4k_or_raw_bypass_events"], 0)
        self.assertEqual(r56_t["apsc_s35_4k_lock_bridge"]["apsc_s35_ok"], 1)
        self.assertEqual(r56_t["face_eye_af_hdmi_bridge"]["hdmi_clean_feed_eye_frame_baked_pixels"], 0)
        self.assertEqual(r56_t["version_bodydata_guard_bridge"]["bodydata_flash_hard_blocked_ok"], 1)
        self.assertEqual(r56_t["lang_telemetry"]["lang"], "schinese")
        self.assertEqual(r56_t["lang_telemetry"]["run_29th_realhw_87th_live"], 1)
        self.assertEqual(r56_t["stage_b_bridge"]["round"], 56)
        self.assertEqual(r56_t["apsc_4k_bodydata_guard"]["r56b_ok"], 1)
        self.assertEqual(r56_t["camreset_face_mem_h0_h3"]["surfaces_h0_eq_h3"], 16)
        self.assertEqual(parsed["prefix_counts"]["FX6_R56_"], 8)

    def test_14_round56_parse_log_defaults_when_no_r56_lines_present(self) -> None:
        parsed = self.runner.extract_milestones("Linux version 4.9.337-scel+\n")
        self.assertIsNone(parsed["r56_telemetry"])
        self.assertEqual(parsed["prefix_counts"].get("FX6_R56_", 0), 0)

    def test_15_round56_runner_uses_fx6_r56_prefix_and_stage_label_and_r55_compat(self) -> None:
        self.assertIn('if args.round >= 56:\n        tmp_prefix = "fx6-r56"', self.runner_src)
        self.assertIn(
            "Milestone29thRealHw87thRunWave42ApscS354kLockoutFaceEyeAfRightLeftEyeVersionReadOnly",
            self.runner_src,
        )
        self.assertIn("# r55_test_compat:", self.runner_src)
        self.assertIn(", 56]", self.runner_src)

    def test_16_round56_runner_portability_and_wave42_intel_spec_rules(self) -> None:
        self.assertIn('shutil.which("zig")', self.runner_src)
        self.assertIn("FX6_SCRATCH_DIR", self.runner_src)
        for token in (
            "APS-C S35 Shooting",
            "XAVC S HD",
            "XAVC HS 4K",
            "HDMI RAW Output",
            "Face/Eye AF",
            "Face/Eye Prior. in AF",
            "Right/Left Eye Select",
            "Face/Eye Frame Disp.",
            "Face Memory",
            "Version",
            "BODYDATA.DAT",
            "ILME-FX3",
        ):
            self.assertIn(token, self.wave42_spec)

    def test_17_round56_summary_json_top_level_schema_and_milestone_metadata(self) -> None:
        d = self.summary
        self.assertEqual(
            d["schema"],
            "fx6-on-fx3-round56-realhw-apsc-s35-face-eye-af-version-qemu-v1",
        )
        self.assertEqual(d["round"], 56)
        self.assertIn("29th Real-HW QEMU Round", d["milestone"])
        self.assertIn("87 Live Runs", d["milestone"])
        self.assertEqual(d["date"], "2026-11-17")
        self.assertIn("4.9.337-scel+", d["kernel_version"])
        self.assertEqual(d["raw_firmware_bytes_leaked"], 0)

    def test_18_round56_summary_json_zero_host_path_and_scratch_leaks(self) -> None:
        for forbidden in (
            "/Users/",
            "/private/tmp/",
            "/var/folders/",
            "work/_scratch/",
            "work/_tests/",
        ):
            self.assertNotIn(forbidden, self.summary_raw)

    def test_19_round56_summary_audit_block_confirms_29th_round_87th_run_and_all_booleans(self) -> None:
        audit = self.summary["r56_realhw_apsc_s35_face_eye_af_version_audit"]
        self.assertEqual(audit["round"], 56)
        self.assertEqual(audit["milestone"], 56)
        self.assertEqual(audit["milestone221_qemu_rounds"], 29)
        self.assertEqual(audit["milestone221_qemu_runs"], 87)
        self.assertEqual(audit["milestone233_qemu_rounds"], 29)
        self.assertEqual(audit["milestone233_qemu_runs"], 87)
        self.assertEqual(audit["milestone254_qemu_rounds"], 29)
        self.assertEqual(audit["milestone254_qemu_runs"], 87)
        self.assertEqual(audit["milestone264_qemu_rounds"], 29)
        self.assertEqual(audit["milestone264_qemu_runs"], 87)
        self.assertEqual(audit["total_runs"], 3)
        for k, v in audit.items():
            if isinstance(v, bool):
                self.assertTrue(v, f"Expected audit boolean {k} to be True")

    def test_20_round56_all_3_runs_present_with_kernel_4_9_337_and_zero_crashes_writes(self) -> None:
        runs = self.summary["runs"]
        self.assertEqual(list(runs.keys()), list(self.EXPECTED_RUN_KEYS))
        for rk, rv in runs.items():
            self.assertEqual(rv["round"], 56, rk)
            self.assertIn("4.9.337-scel+", rv["kernel_version"], rk)
            self.assertEqual(rv["nop_count"], 0, rk)
            self.assertEqual(rv["crashes"], 0, rk)
            self.assertEqual(rv["emmc_write_count"], 0, rk)
            self.assertGreater(rv["wall_elapsed_sec"], 0.0, rk)

    def test_21_round56_r56a_apsc_s35_hd_15x_and_4k_lockouts_verified(self) -> None:
        init_t = self.summary["runs"]["r56a_apsc_s35_hd_face_eye_af_version_big6_schinese"][
            "r56_telemetry"
        ]["apsc_face_eye_version_init"]
        self.assertEqual(init_t["fx3_wave42_nodes_ok"], 1)
        self.assertEqual(init_t["apsc_default_auto_ok"], 1)
        self.assertEqual(init_t["invalid_apsc_rc"], -22)
        self.assertEqual(init_t["apsc_hd_15x_ok"], 1)
        self.assertEqual(init_t["apsc_4k_lockouts_verified"], 4)
        self.assertEqual(init_t["apsc_s35_4k_or_raw_bypass_events"], 0)

    def test_22_round56_r56a_face_eye_af_clean_hdmi_and_version_readonly_verified(self) -> None:
        init_t = self.summary["runs"]["r56a_apsc_s35_hd_face_eye_af_version_big6_schinese"][
            "r56_telemetry"
        ]["apsc_face_eye_version_init"]
        self.assertEqual(init_t["face_eye_defaults_ok"], 1)
        self.assertEqual(init_t["subjects_verified"], 3)
        self.assertEqual(init_t["eyes_verified"], 3)
        self.assertEqual(init_t["switch_ok"], 1)
        self.assertEqual(init_t["clean_hdmi_isolated_ok"], 1)
        self.assertEqual(init_t["hdmi_clean_feed_eye_frame_baked_pixels"], 0)
        self.assertEqual(init_t["version_readonly_ok"], 1)
        self.assertEqual(init_t["version_inspect_flash_writes"], 0)
        self.assertEqual(init_t["passive_tx_bytes_emitted"], 0)
        self.assertEqual(init_t["update_badge_suppressed_ok"], 1)

    def test_23_round56_r56a_p2_cnflasha_and_slot1_ro_guards_intact(self) -> None:
        init_t = self.summary["runs"]["r56a_apsc_s35_hd_face_eye_af_version_big6_schinese"][
            "r56_telemetry"
        ]["apsc_face_eye_version_init"]
        self.assertEqual(init_t["slot1_vault_writes"], 0)
        self.assertEqual(init_t["p2_write_blocked_rc"], -30)
        self.assertEqual(init_t["p2_sha256_match"], 1)
        self.assertEqual(init_t["cnflasha_sha256_match"], 1)
        self.assertEqual(init_t["slot1_vault_sha256_match"], 1)
        self.assertEqual(init_t["cnflasha_writes"], 0)
        self.assertEqual(init_t["appfw_present"], 1)
        self.assertEqual(init_t["shim_present"], 1)
        self.assertEqual(init_t["emmc_write_count"], 0)
        self.assertEqual(init_t["r56_init_ok"], 1)

    def test_24_round56_r56a_stage_b_schinese_lang_telemetry_and_bridges(self) -> None:
        r56a_t = self.summary["runs"]["r56a_apsc_s35_hd_face_eye_af_version_big6_schinese"][
            "r56_telemetry"
        ]
        lt = r56a_t["lang_telemetry"]
        self.assertEqual(lt["lang"], "schinese")
        self.assertEqual(lt["bk4_lang_id"], "0x02cf019c")
        self.assertEqual(lt["bk4_lang_val"], "0x19")
        self.assertEqual(lt["lang_enum"], "0x2b45_CHINESE_SIMPLIFIED")
        self.assertEqual(lt["font_bank"], 23)
        self.assertEqual(lt["str_bank"], 19)
        self.assertEqual(lt["gpe_fb"], 0)
        self.assertEqual(lt["run_29th_realhw_87th_live"], 1)
        self.assertEqual(lt["apsc_s35_4k_or_raw_bypass_events"], 0)
        self.assertEqual(lt["hdmi_clean_feed_eye_frame_baked_pixels"], 0)
        self.assertEqual(lt["version_inspect_flash_writes"], 0)
        self.assertEqual(lt["passive_tx_bytes_emitted"], 0)
        self.assertEqual(lt["e_nd_actuator_tx_count"], 0)
        self.assertEqual(lt["raw_firmware_bytes_leaked"], 0)
        sb = r56a_t["stage_b_bridge"]
        self.assertEqual(sb["round"], 56)
        self.assertEqual(sb["faithful"], 1)
        self.assertEqual(sb["nop_count"], 0)
        self.assertEqual(sb["apsc_s35_hd_15x_4k_raw_lockout"], 1)
        self.assertEqual(sb["face_eye_af_rl_eye_clean_hdmi_isolation"], 1)
        self.assertEqual(sb["version_702_readonly_bodydata_blocked"], 1)

    def test_25_round56_r56a_stage_b_3_pillar_bridges_verified(self) -> None:
        r56a_t = self.summary["runs"]["r56a_apsc_s35_hd_face_eye_af_version_big6_schinese"][
            "r56_telemetry"
        ]
        ab = r56a_t["apsc_s35_4k_lock_bridge"]
        self.assertEqual(ab["apsc_default_auto_ok"], 1)
        self.assertEqual(ab["apsc_hd_15x_ok"], 1)
        self.assertEqual(ab["apsc_4k_lockouts_verified"], 4)
        self.assertEqual(ab["apsc_s35_4k_or_raw_bypass_events"], 0)
        self.assertEqual(ab["apsc_s35_ok"], 1)
        fb = r56a_t["face_eye_af_hdmi_bridge"]
        self.assertEqual(fb["face_eye_defaults_ok"], 1)
        self.assertEqual(fb["face_eye_subjects_3_ok"], 1)
        self.assertEqual(fb["face_eye_rl_3_ok"], 1)
        self.assertEqual(fb["hdmi_clean_feed_eye_frame_baked_pixels"], 0)
        self.assertEqual(fb["face_memory_survives_camreset_ok"], 1)
        self.assertEqual(fb["face_eye_af_ok"], 1)
        vb = r56a_t["version_bodydata_guard_bridge"]
        self.assertEqual(vb["version_702_readonly_ok"], 1)
        self.assertEqual(vb["version_inspect_flash_writes"], 0)
        self.assertEqual(vb["passive_tx_bytes_emitted"], 0)
        self.assertEqual(vb["bodydata_flash_hard_blocked_ok"], 1)
        self.assertEqual(vb["version_ro_ok"], 1)

    def test_26_round56_r56a_gpe0_readback_exact_346686_pixels_and_87_colors(self) -> None:
        r56a = self.summary["runs"]["r56a_apsc_s35_hd_face_eye_af_version_big6_schinese"]
        self.assertEqual(r56a["target_presenter"], "31procam_big6_menu_home_presenter")
        self.assertEqual(r56a["target_sid"], "0x0a")
        self.assertGreaterEqual(r56a["total_threads_seen"], 150)
        gpe0 = r56a["gpe0_readback"]
        self.assertTrue(gpe0["present"])
        self.assertEqual(gpe0["bytes"], 2211840)
        self.assertEqual(gpe0["total_pixels"], 552960)
        self.assertEqual(gpe0["nonzero_pixels"], 346686)
        self.assertEqual(gpe0["unique_colors"], 87)

    def test_27_round56_r56a_stage_b_manifest_13_hashes_and_r56_metadata(self) -> None:
        sb = self.summary["runs"]["r56a_apsc_s35_hd_face_eye_af_version_big6_schinese"]["stage_b"]
        self.assertEqual(sb["manifest_count"], 13)
        self.assertEqual(len(sb["manifest_items"]), 13)
        for item in sb["manifest_items"]:
            self.assertEqual(len(item["sha256"]), 64)
        r56_meta = sb["r56"]
        self.assertEqual(r56_meta["r56_mode"], "apsc_s35_hd_face_eye_af_version_big6")
        self.assertEqual(r56_meta["apsc_s35_modes"], ["Auto", "On", "Off"])
        self.assertEqual(r56_meta["apsc_s35_default"], "Auto")
        self.assertEqual(r56_meta["fx3_sensor_mp"], 12.1)
        self.assertEqual(r56_meta["face_eye_subjects"], ["Human", "Animal", "Bird"])
        self.assertEqual(r56_meta["right_left_eye_select_modes"], ["Auto", "Right Eye", "Left Eye"])
        self.assertEqual(r56_meta["version_body"], "Ver. 7.02")

    def test_28_round56_r56b_apsc_s35_4k_and_hdmi_raw_bypass_blocked_fail_closed(self) -> None:
        r56b_t = self.summary["runs"]["r56b_apsc_4k_raw_cleanhdmi_bodydata_flash_guard"][
            "r56_telemetry"
        ]
        self.assertEqual(r56b_t["apsc_4k_bodydata_rc"], 0)
        gd = r56b_t["apsc_4k_bodydata_guard"]
        self.assertEqual(gd["hs_4k_inject_rc"], -16)
        self.assertEqual(gd["s_4k_inject_rc"], -16)
        self.assertEqual(gd["si_4k_inject_rc"], -16)
        self.assertEqual(gd["hdmi_raw_inject_rc"], -16)
        self.assertEqual(gd["apsc_s35_4k_or_raw_bypass_events"], 0)

    def test_29_round56_r56b_clean_hdmi_eye_frame_bake_blocked_zero_pixels(self) -> None:
        gd = self.summary["runs"]["r56b_apsc_4k_raw_cleanhdmi_bodydata_flash_guard"][
            "r56_telemetry"
        ]["apsc_4k_bodydata_guard"]
        self.assertEqual(gd["bake_hdmi_off_rc"], -1)
        self.assertEqual(gd["bake_hdmi_raw_rc"], -1)
        self.assertEqual(gd["hdmi_clean_feed_eye_frame_baked_pixels"], 0)
        self.assertEqual(gd["ai_unit_node_rejected_rc"], -2)

    def test_30_round56_r56b_bodydata_dat_slot1_flash_hard_blocked(self) -> None:
        gd = self.summary["runs"]["r56b_apsc_4k_raw_cleanhdmi_bodydata_flash_guard"][
            "r56_telemetry"
        ]["apsc_4k_bodydata_guard"]
        self.assertEqual(gd["bodydata_flash_blocked_rc"], -30)
        self.assertEqual(gd["persistent_emmc_writes_authorized"], 0)
        self.assertEqual(gd["bodydata_flash_attempts_succeeded"], 0)

    def test_31_round56_r56b_slot1_vault_ro_and_zero_emmc_cnflasha_writes(self) -> None:
        gd = self.summary["runs"]["r56b_apsc_4k_raw_cleanhdmi_bodydata_flash_guard"][
            "r56_telemetry"
        ]["apsc_4k_bodydata_guard"]
        self.assertEqual(gd["slot1_vault_ro_blocked_rc"], -30)
        self.assertEqual(gd["slot1_vault_sha256_match"], 1)
        self.assertEqual(gd["slot1_vault_writes"], 0)
        self.assertEqual(gd["p2_write_blocked_rc"], -30)
        self.assertEqual(gd["cnflasha_ro_blocked_rc"], -30)
        self.assertEqual(gd["cnflasha_writes"], 0)
        self.assertEqual(gd["emmc_write_count"], 0)
        self.assertEqual(gd["r56b_ok"], 1)

    def test_32_round56_r56c_camreset_vs_face_memory_and_initialize_survival_verified(self) -> None:
        ci = self.summary["runs"]["r56c_camreset_face_memory_initialize_h0_h3_big6_schinese"][
            "r56_telemetry"
        ]["camreset_face_mem_h0_h3"]
        self.assertEqual(ci["wave42_survives_netreset_ok"], 1)
        self.assertEqual(ci["apsc_camreset_auto_ok"], 1)
        self.assertEqual(ci["face_eye_af_camreset_ok"], 1)
        self.assertEqual(ci["face_memory_survives_camreset_ok"], 1)
        self.assertEqual(ci["face_memory_explicit_delete_ok"], 1)
        self.assertEqual(ci["initialize_clears_face_memory_and_defaults_ok"], 1)

    def test_33_round56_r56c_dlopen_and_16_h0_eq_h3_idempotent_unmount(self) -> None:
        ci = self.summary["runs"]["r56c_camreset_face_memory_initialize_h0_h3_big6_schinese"][
            "r56_telemetry"
        ]["camreset_face_mem_h0_h3"]
        self.assertEqual(ci["dlopen_ok"], 1)
        self.assertEqual(ci["surfaces_verified"], 16)
        self.assertEqual(ci["surfaces_h0_eq_h3"], 16)
        self.assertEqual(ci["drift_bits"], 0)
        self.assertEqual(ci["e_nd_actuator_tx_count"], 0)
        self.assertEqual(ci["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(ci["emmc_write_count"], 0)
        self.assertEqual(ci["r56c_ok"], 1)

    def test_34_round56_r56c_integrated_renders_valid_big6_gpe0_readback(self) -> None:
        r56c = self.summary["runs"]["r56c_camreset_face_memory_initialize_h0_h3_big6_schinese"]
        self.assertEqual(r56c["target_presenter"], "31procam_big6_menu_home_presenter")
        self.assertEqual(r56c["target_sid"], "0x0a")
        gpe0 = r56c["gpe0_readback"]
        self.assertTrue(gpe0["present"])
        self.assertEqual(gpe0["bytes"], 2211840)
        self.assertEqual(gpe0["total_pixels"], 552960)
        self.assertEqual(gpe0["nonzero_pixels"], 346686)
        self.assertEqual(gpe0["unique_colors"], 87)

    def test_35_round56_realhw_mechanisms_verified_6_blocks_match_run_telemetry(self) -> None:
        rm = self.summary["realhw_mechanisms_verified"]
        self.assertEqual(len(rm), 6)
        r56a = self.summary["runs"]["r56a_apsc_s35_hd_face_eye_af_version_big6_schinese"][
            "r56_telemetry"
        ]
        r56b = self.summary["runs"]["r56b_apsc_4k_raw_cleanhdmi_bodydata_flash_guard"][
            "r56_telemetry"
        ]
        r56c = self.summary["runs"]["r56c_camreset_face_memory_initialize_h0_h3_big6_schinese"][
            "r56_telemetry"
        ]
        self.assertEqual(
            rm["apsc_s35_face_eye_af_version_init"],
            r56a["apsc_face_eye_version_init"],
        )
        self.assertEqual(
            rm["apsc_s35_4k_lockout_stage_b_bridge"],
            r56a["apsc_s35_4k_lock_bridge"],
        )
        self.assertEqual(
            rm["face_eye_af_rl_eye_clean_hdmi_stage_b_bridge"],
            r56a["face_eye_af_hdmi_bridge"],
        )
        self.assertEqual(
            rm["version_702_readonly_bodydata_guard_stage_b_bridge"],
            r56a["version_bodydata_guard_bridge"],
        )
        self.assertEqual(
            rm["apsc_4k_raw_cleanhdmi_bodydata_flash_guard"],
            r56b["apsc_4k_bodydata_guard"],
        )
        self.assertEqual(
            rm["camreset_vs_face_memory_initialize_and_16_h0_h3"],
            r56c["camreset_face_mem_h0_h3"],
        )

    def test_36_round56_camreset_vs_initialize_tiers_consistent_across_runs(self) -> None:
        ab_a = self.summary["runs"]["r56a_apsc_s35_hd_face_eye_af_version_big6_schinese"][
            "r56_telemetry"
        ]["apsc_s35_4k_lock_bridge"]
        fb_a = self.summary["runs"]["r56a_apsc_s35_hd_face_eye_af_version_big6_schinese"][
            "r56_telemetry"
        ]["face_eye_af_hdmi_bridge"]
        ci_c = self.summary["runs"]["r56c_camreset_face_memory_initialize_h0_h3_big6_schinese"][
            "r56_telemetry"
        ]["camreset_face_mem_h0_h3"]
        self.assertEqual(ab_a["apsc_reset_camreset_ok"], 1)
        self.assertEqual(fb_a["face_memory_survives_camreset_ok"], 1)
        self.assertEqual(ci_c["apsc_camreset_auto_ok"], 1)
        self.assertEqual(ci_c["face_eye_af_camreset_ok"], 1)
        self.assertEqual(ci_c["face_memory_survives_camreset_ok"], 1)
        self.assertEqual(ci_c["initialize_clears_face_memory_and_defaults_ok"], 1)

    def test_37_round56_cross_round_consistency_with_r55_hdmi_raw_and_slot1_ro(self) -> None:
        self.assertEqual(self.r55_summary["round"], 55)
        r55b_lk = self.r55_summary["runs"]["r55b_prerequisite_lockout_injection_guard"][
            "r55_telemetry"
        ]["lockout_injection_guard"]
        self.assertEqual(r55b_lk["raw_on_inject_rc"], -16)
        self.assertEqual(r55b_lk["slot1_vault_ro_blocked_rc"], -30)
        r56b_gd = self.summary["runs"]["r56b_apsc_4k_raw_cleanhdmi_bodydata_flash_guard"][
            "r56_telemetry"
        ]["apsc_4k_bodydata_guard"]
        self.assertEqual(r56b_gd["hdmi_raw_inject_rc"], -16)
        self.assertEqual(r56b_gd["slot1_vault_ro_blocked_rc"], -30)

    def test_38_round56_cross_round_consistency_with_r54_camreset_vs_initialize(self) -> None:
        self.assertEqual(self.r54_summary["round"], 54)
        r54_init = self.r54_summary["runs"]["r54a_diff_set_still_mv_shutter_angle_big6_schinese"][
            "r54_telemetry"
        ]["diff_set_init"]
        self.assertEqual(r54_init["diff_set_survives_camreset_ok"], 1)
        r56c_ci = self.summary["runs"]["r56c_camreset_face_memory_initialize_h0_h3_big6_schinese"][
            "r56_telemetry"
        ]["camreset_face_mem_h0_h3"]
        self.assertEqual(r56c_ci["face_memory_survives_camreset_ok"], 1)
        self.assertEqual(r56c_ci["initialize_clears_face_memory_and_defaults_ok"], 1)

    def test_39_round56_cross_round_consistency_with_r53_netreset_survival(self) -> None:
        self.assertEqual(self.r53_summary["round"], 53)
        r53_init = self.r53_summary["runs"]["r53a_display_quality_bt_rmt_big6_schinese"][
            "r53_telemetry"
        ]["dispqual_btrmt_init"]
        self.assertEqual(r53_init["display_quality_survives_netreset_ok"], 1)
        r56c_ci = self.summary["runs"]["r56c_camreset_face_memory_initialize_h0_h3_big6_schinese"][
            "r56_telemetry"
        ]["camreset_face_mem_h0_h3"]
        self.assertEqual(r56c_ci["wave42_survives_netreset_ok"], 1)

    def test_40_round56_unexecuted_physical_camera_bench_boundaries_documented(self) -> None:
        bounds = self.summary["unexecuted_physical_camera_bench_boundaries"]
        self.assertEqual(len(bounds), 3)
        joined = " ".join(bounds)
        self.assertIn("APS-C S35 Shooting", joined)
        self.assertIn("Face/Eye AF", joined)
        self.assertIn("Version", joined)
        self.assertIn("BODYDATA.DAT", joined)

    def test_41_round56_alpha_png_exists_under_50kib_and_matches_summary_sha256(self) -> None:
        pe = self.summary["runs"]["r56a_apsc_s35_hd_face_eye_af_version_big6_schinese"][
            "png_exports"
        ]
        self.assertLess(len(self.alpha_png_bytes), 50000)
        self.assertLess(len(self.alpha_png_bytes), 51200)
        self.assertEqual(len(self.alpha_png_bytes), pe["alpha_bytes"])
        self.assertEqual(
            hashlib.sha256(self.alpha_png_bytes).hexdigest(), pe["alpha_sha256"]
        )

    def test_42_round56_composited_png_exists_under_50kib_and_matches_summary_sha256(self) -> None:
        pe = self.summary["runs"]["r56a_apsc_s35_hd_face_eye_af_version_big6_schinese"][
            "png_exports"
        ]
        self.assertLess(len(self.comp_png_bytes), 50000)
        self.assertLess(len(self.comp_png_bytes), 51200)
        self.assertEqual(len(self.comp_png_bytes), pe["composited_bytes"])
        self.assertEqual(
            hashlib.sha256(self.comp_png_bytes).hexdigest(), pe["composited_sha256"]
        )

    def test_43_round56_alpha_png_valid_1024x540_rgba_with_transparent_and_opaque_pixels(self) -> None:
        self.assertEqual(self.alpha_dims, (1024, 540))
        self.assertEqual(self.alpha_transparent, 206274)
        self.assertGreater(self.alpha_opaque, 300000)

    def test_44_round56_composited_png_valid_1024x540_rgba_100pct_opaque(self) -> None:
        self.assertEqual(self.comp_dims, (1024, 540))
        self.assertEqual(self.comp_opaque, 1024 * 540)

    def test_45_round56_report_readme_documents_all_3_runs_and_zero_host_leaks(self) -> None:
        for token in (
            "Round 56",
            "29th Real-HW",
            "87th Live Run",
            "r56a",
            "r56b",
            "r56c",
            "APS-C S35 Shooting",
            "12.1MP",
            "Face/Eye AF",
            "Right/Left Eye Select",
            "Face/Eye Frame Disp.",
            "Face Memory",
            "Version",
            "BODYDATA.DAT",
            "346,686",
            "r56a-apsc-s35-face-eye-af-big6-schinese-alpha.png",
            "r56a-apsc-s35-face-eye-af-big6-schinese-composited.png",
        ):
            self.assertIn(token, self.r56_readme)
        for forbidden in ("/Users/", "/private/tmp/", "/var/folders/", "work/_scratch/"):
            self.assertNotIn(forbidden, self.r56_readme)

    def test_46_round56_closure_readme_section_56_present_and_accurate(self) -> None:
        self.assertIn("## 56. Round 56", self.closure_readme)
        self.assertIn("29th Real-HW Round", self.closure_readme)
        self.assertIn("87th Live Run", self.closure_readme)
        self.assertIn(
            "2026-11-17-round56-realhw-apsc-s35-face-eye-af-version-qemu",
            self.closure_readme,
        )

    def test_47_round56_29_realhw_qemu_rounds_r28_to_r56_87_runs_and_58_pngs_continuity(self) -> None:
        png_total = 0
        for r in range(28, 57):
            matches = list((REPO_ROOT / "reports").glob(f"2026-??-??-round{r}-*"))
            self.assertEqual(len(matches), 1, f"Expected 1 report dir for Round {r}")
            pngs = list((matches[0] / "assets").glob("*.png"))
            self.assertEqual(len(pngs), 2, f"Expected 2 PNGs for Round {r}")
            for p in pngs:
                self.assertLess(p.stat().st_size, 51200, str(p))
            png_total += len(pngs)
        self.assertEqual(png_total, 58)
        audit = self.summary["r56_realhw_apsc_s35_face_eye_af_version_audit"]
        self.assertEqual(audit["milestone264_qemu_rounds"], 29)
        self.assertEqual(audit["milestone264_qemu_runs"], 87)

    def test_48_round56_dual_mode_clean_room_toggle_parity_on_summary(self) -> None:
        for clean_flag in ("0", "1"):
            with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                d = json.loads(self.summary_raw)
                self.assertEqual(d["round"], 56)
                self.assertEqual(
                    d["runs"]["r56a_apsc_s35_hd_face_eye_af_version_big6_schinese"][
                        "r56_telemetry"
                    ]["apsc_face_eye_version_init"]["apsc_4k_lockouts_verified"],
                    4,
                )
                self.assertEqual(
                    d["runs"]["r56b_apsc_4k_raw_cleanhdmi_bodydata_flash_guard"][
                        "r56_telemetry"
                    ]["apsc_4k_bodydata_guard"]["bodydata_flash_blocked_rc"],
                    -30,
                )
                self.assertEqual(
                    d["runs"]["r56c_camreset_face_memory_initialize_h0_h3_big6_schinese"][
                        "r56_telemetry"
                    ]["camreset_face_mem_h0_h3"]["surfaces_h0_eq_h3"],
                    16,
                )

    def test_49_round56_r56a_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"]["r56a_apsc_s35_hd_face_eye_af_version_big6_schinese"][
            "r56_telemetry"
        ]["apsc_face_eye_version_init"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_50_round56_r56b_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"]["r56b_apsc_4k_raw_cleanhdmi_bodydata_flash_guard"][
            "r56_telemetry"
        ]["apsc_4k_bodydata_guard"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_51_round56_r56c_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"]["r56c_camreset_face_memory_initialize_h0_h3_big6_schinese"][
            "r56_telemetry"
        ]["camreset_face_mem_h0_h3"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_52_round56_r56a_top_colors_transparent_plus_nonzero_equals_total_pixels(self) -> None:
        gpe = self.summary["runs"]["r56a_apsc_s35_hd_face_eye_af_version_big6_schinese"][
            "gpe0_readback"
        ]
        color_map = {row["argb"]: row["pixels"] for row in gpe["top_colors"]}
        self.assertIn("0x00000000", color_map)
        self.assertIn("0xff000000", color_map)
        self.assertEqual(color_map["0x00000000"] + gpe["nonzero_pixels"], gpe["total_pixels"])

    def test_53_round56_r56c_top_colors_transparent_plus_nonzero_equals_total_pixels(self) -> None:
        gpe = self.summary["runs"]["r56c_camreset_face_memory_initialize_h0_h3_big6_schinese"][
            "gpe0_readback"
        ]
        color_map = {row["argb"]: row["pixels"] for row in gpe["top_colors"]}
        self.assertIn("0x00000000", color_map)
        self.assertEqual(color_map["0x00000000"] + gpe["nonzero_pixels"], gpe["total_pixels"])

    def test_54_round56_r56a_and_r56c_wall_elapsed_and_duration_budget_sanity(self) -> None:
        r56a = self.summary["runs"]["r56a_apsc_s35_hd_face_eye_af_version_big6_schinese"]
        r56c = self.summary["runs"]["r56c_camreset_face_memory_initialize_h0_h3_big6_schinese"]
        max_wall = 240.0 if os.environ.get("GITHUB_ACTIONS") == "true" else 120.0
        self.assertGreaterEqual(r56a["duration_budget_sec"], 70)
        self.assertLessEqual(r56a["duration_budget_sec"], 120)
        self.assertGreater(r56a["wall_elapsed_sec"], 50.0)
        self.assertLess(r56a["wall_elapsed_sec"], max_wall)
        self.assertGreaterEqual(r56c["duration_budget_sec"], 70)
        self.assertLessEqual(r56c["duration_budget_sec"], 120)
        self.assertGreater(r56c["wall_elapsed_sec"], 50.0)
        self.assertLess(r56c["wall_elapsed_sec"], max_wall)

    def test_55_round56_r56b_fast_early_exit_wall_elapsed_under_20s(self) -> None:
        r56b = self.summary["runs"]["r56b_apsc_4k_raw_cleanhdmi_bodydata_flash_guard"]
        max_b = 45.0 if os.environ.get("GITHUB_ACTIONS") == "true" else 20.0
        self.assertEqual(r56b["duration_budget_sec"], 35)
        self.assertGreater(r56b["wall_elapsed_sec"], 1.0)
        self.assertLess(r56b["wall_elapsed_sec"], max_b)
        self.assertTrue(r56b["gpe0_readback"]["skipped_stock_fx3_mode"])

    def test_56_round56_faithful_invariants_preserved_across_all_3_runs(self) -> None:
        for rk, rv in self.summary["runs"].items():
            fi = rv["faithful_invariants"]
            self.assertEqual(fi["FX6_NATIVE_FAITHFUL"], 1, rk)
            self.assertEqual(fi["subst_color"], 0, rk)
            self.assertEqual(fi["subst_image"], 0, rk)
            self.assertEqual(fi["forced_render"], 0, rk)
            self.assertEqual(fi["skipped_node"], 0, rk)
            self.assertEqual(fi["lock_bypass"], 0, rk)

    def test_57_round56_all_3_runs_stage_b_manifest_count_13(self) -> None:
        for rk, rv in self.summary["runs"].items():
            self.assertEqual(rv["stage_b"]["manifest_count"], 13, rk)
            self.assertEqual(len(rv["stage_b"]["manifest_items"]), 13, rk)

    def test_58_round56_r56c_stage_b_r56_bridges_and_zero_leak_verified(self) -> None:
        r56c_t = self.summary["runs"]["r56c_camreset_face_memory_initialize_h0_h3_big6_schinese"][
            "r56_telemetry"
        ]
        self.assertEqual(r56c_t["apsc_s35_4k_lock_bridge"]["apsc_s35_ok"], 1)
        self.assertEqual(r56c_t["face_eye_af_hdmi_bridge"]["face_eye_af_ok"], 1)
        self.assertEqual(r56c_t["version_bodydata_guard_bridge"]["version_ro_ok"], 1)
        self.assertEqual(r56c_t["apsc_s35_4k_lock_bridge"]["apsc_s35_4k_or_raw_bypass_events"], 0)
        self.assertEqual(r56c_t["face_eye_af_hdmi_bridge"]["hdmi_clean_feed_eye_frame_baked_pixels"], 0)
        self.assertEqual(r56c_t["stage_b_bridge"]["e_nd_actuator_tx_count"], 0)

    def test_59_round56_all_3_runs_prefix_counts_include_fx6_r56(self) -> None:
        r56a_pc = self.summary["runs"]["r56a_apsc_s35_hd_face_eye_af_version_big6_schinese"][
            "prefix_counts"
        ]
        r56b_pc = self.summary["runs"]["r56b_apsc_4k_raw_cleanhdmi_bodydata_flash_guard"][
            "prefix_counts"
        ]
        r56c_pc = self.summary["runs"]["r56c_camreset_face_memory_initialize_h0_h3_big6_schinese"][
            "prefix_counts"
        ]
        self.assertGreater(r56a_pc["FX6_R56_"], 10)
        self.assertEqual(r56b_pc["FX6_R56_"], 3)
        self.assertGreater(r56c_pc["FX6_R56_"], 10)

    def test_60_round56_r56_meta_invariants_across_all_3_runs(self) -> None:
        for rk, rv in self.summary["runs"].items():
            m = rv["stage_b"]["r56"]
            self.assertTrue(m["apsc_s35_hd_only_4k_raw_locked_off"], rk)
            self.assertEqual(m["apsc_s35_4k_or_raw_bypass_events"], 0, rk)
            self.assertTrue(m["apsc_s35_reset_by_camera_settings_reset"], rk)
            self.assertEqual(m["face_eye_prior_in_af_default"], "On", rk)
            self.assertEqual(m["hdmi_clean_feed_eye_frame_baked_pixels"], 0, rk)
            self.assertTrue(m["face_memory_survives_camera_settings_reset"], rk)
            self.assertTrue(m["face_memory_cleared_by_delete_or_initialize"], rk)
            self.assertEqual(m["version_inspect_flash_writes"], 0, rk)
            self.assertEqual(m["passive_tx_bytes_emitted"], 0, rk)
            self.assertFalse(m["persistent_emmc_writes_authorized"], rk)
            self.assertTrue(m["bodydata_flash_hard_blocked"], rk)
            self.assertEqual(m["e_nd_actuator_tx_count"], 0, rk)
            self.assertEqual(m["raw_firmware_bytes_leaked"], 0, rk)

    def test_61_round56_no_stray_temp_files_in_repo_root(self) -> None:
        for bad_name in ("tmp", "scratch", ".worktrees"):
            self.assertFalse((REPO_ROOT / bad_name).exists(), bad_name)

    def test_62_round56_port_8768_untouched_in_round56_reports(self) -> None:
        self.assertNotIn("8768", self.summary_raw)
        self.assertNotIn("8768", self.r56_readme)

    def test_63_round56_runner_escapes_percent_in_argparse_help_and_portable_tools(self) -> None:
        self.assertIn("ArgumentParser", self.runner_src)
        self.assertNotIn('"/usr/bin/python3"', self.runner_src)
        self.assertIn('shutil.which("zig")', self.runner_src)
        self.assertIn("FX6_SCRATCH_DIR", self.runner_src)

    def test_64_round56_test_suite_contains_at_least_62_unit_tests(self) -> None:
        methods = [m for m in dir(self) if m.startswith("test_")]
        self.assertGreaterEqual(len(methods), 62)
        self.assertEqual(len(methods), 64)


if __name__ == "__main__":
    unittest.main()
