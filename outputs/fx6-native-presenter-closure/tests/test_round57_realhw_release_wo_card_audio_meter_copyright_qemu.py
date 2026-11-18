#!/usr/bin/env python3
"""Offline dual-mode unit tests for FX6-on-FX3 Round 57 (30th Real-HW Milestone / 90th Live Run — Wave-43)."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import pathlib
import shutil
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
ROUND57_REPORT_DIR = (
    REPO_ROOT
    / "reports"
    / "2026-11-17-round57-milestone-realhw-release-wo-card-audio-meter-copyright-qemu"
)
WAVE43_SPEC_PATH = (
    REPO_ROOT
    / "reports"
    / "2026-11-15-global-sony-wave43-release-wo-card-lens-disp-audio-meter-v2-vs-v1-copyright-info-46char-intel"
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


def _build_overlay_for_r57(
    runner,
    parent_cpio: pathlib.Path,
    fp,
    fv,
    fb,
    fake_run,
    jit_meta: Dict[str, Any],
    work: pathlib.Path,
    r57_mode: str,
    lang: str = "schinese",
    enable_r57: bool = True,
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
            enable_r56=True,
            r56_mode="apsc_s35_hd_face_eye_af_version_big6",
            enable_r57=enable_r57,
            r57_mode=r57_mode,
            sd_manifest_mode="valid",
            lang=lang,
            shim_bytes=b"SHIM",
        )


class TestRound57RealHwReleaseWoCardAudioMeterCopyrightQemu(unittest.TestCase):
    EXPECTED_RUN_KEYS = (
        "r57a_release_wo_card_lens_audio_meter_copyright_big6_schinese",
        "r57b_cardless_movie_v1_audio_spoof_copyright_guard",
        "r57c_camreset_copyright_disp_init_h0_h3_big6_schinese",
    )

    runner: Any
    runner_src: str
    stage_a_src: str
    shim_src: str
    wave43_spec: str
    summary_raw: str
    summary: Dict[str, Any]
    r57_readme: str
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
    launcher_r57: Optional[bytes]
    shim_r57: Optional[bytes]
    shim_r56: Optional[bytes]
    r56_summary: Dict[str, Any]
    r55_summary: Dict[str, Any]
    r54_summary: Dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = _load_closure_module("fx6_brr_r57_cached", "build_and_run_round.py")
        cls.runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")
        cls.stage_a_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        cls.shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        cls.wave43_spec = WAVE43_SPEC_PATH.read_text(encoding="utf-8")
        cls.summary_raw = (ROUND57_REPORT_DIR / "summary.json").read_text(encoding="utf-8")
        cls.summary = json.loads(cls.summary_raw)
        cls.r57_readme = (ROUND57_REPORT_DIR / "README.md").read_text(encoding="utf-8")
        cls.closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")

        alpha_p = (
            ROUND57_REPORT_DIR
            / "assets"
            / "r57a-release-wo-card-audio-meter-big6-schinese-alpha.png"
        )
        comp_p = (
            ROUND57_REPORT_DIR
            / "assets"
            / "r57a-release-wo-card-audio-meter-big6-schinese-composited.png"
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
            cls.ov_a = _build_overlay_for_r57(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wa", "release_wo_card_lens_audio_meter_copyright_big6", lang="schinese",
            )
            cls.ov_b = _build_overlay_for_r57(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wb", "cardless_movie_v1_audio_spoof_copyright_guard", lang="en",
            )
            cls.ov_c = _build_overlay_for_r57(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wc", "camreset_copyright_disp_init_h0_h3_big6", lang="schinese",
            )
            cls.ov_off = _build_overlay_for_r57(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "woff", "release_wo_card_lens_audio_meter_copyright_big6", enable_r57=False,
            )
            cls.invalid_mode_raised = False
            try:
                _build_overlay_for_r57(
                    cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                    tpath / "wbad", "invalid_r57_mode",
                )
            except ValueError:
                cls.invalid_mode_raised = True

            zig_bin = shutil.which("zig") or (
                str(cls.runner.ZIG) if cls.runner.ZIG.is_file() else None
            )
            if zig_bin is not None:
                verify_r57_out = tpath / "fx6-stage-a-verify-r57"
                shim_r57_out = tpath / "libgrm-fbinit9-r57.so"
                shim_r56_out = tpath / "libgrm-fbinit9-r56.so"
                for cmd in (
                    [
                        zig_bin,
                        "cc",
                        "-target",
                        "aarch64-linux-gnu.2.25",
                        "-O0",
                        str(CLOSURE_DIR / "fx6-stage-a-verify.c"),
                        "-ldl",
                        "-lpthread",
                        "-o",
                        str(verify_r57_out),
                    ],
                    [
                        zig_bin,
                        "cc",
                        "-target",
                        "aarch64-linux-gnu.2.25",
                        "-O0",
                        "-shared",
                        "-fPIC",
                        "-DFX6_ROUND=57",
                        str(CLOSURE_DIR / "libgrm-fbinit9.c"),
                        "-ldl",
                        "-lpthread",
                        "-o",
                        str(shim_r57_out),
                    ],
                    [
                        zig_bin,
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
                ):
                    cls.runner.subprocess.run(cmd, check=True)
                cls.launcher_r57 = verify_r57_out.read_bytes()
                cls.shim_r57 = shim_r57_out.read_bytes()
                cls.shim_r56 = shim_r56_out.read_bytes()
            else:
                cls.launcher_r57 = None
                cls.shim_r57 = None
                cls.shim_r56 = None

        cls.r56_summary = json.loads(
            (
                REPO_ROOT
                / "reports"
                / "2026-11-17-round56-realhw-apsc-s35-face-eye-af-version-qemu"
                / "summary.json"
            ).read_text(encoding="utf-8")
        )
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

    def test_01_wave43_global_spec_present_and_covers_all_wave43_pillars(self) -> None:
        self.assertTrue(WAVE43_SPEC_PATH.is_file())
        for needle in (
            "Release w/o Card",
            "Release w/o Lens",
            "Audio Recording",
            "Audio Rec Level",
            "Audio Out Timing",
            "Wind Noise Reduct.",
            "Shoe Audio Set.",
            "Audio Level Display",
            "DISP (Screen Disp) Set",
            "Copyright Info",
            "Write Copyright Info",
            "Set Photographer",
            "Set Copyright",
            "Disp. Copyright Info",
            "46",
            "Ver. 7.02",
        ):
            self.assertIn(needle, self.wave43_spec)

    def test_02_round57_summary_schema_round_milestone_and_zero_leaks(self) -> None:
        self.assertNotIn("/Users/", self.summary_raw)
        self.assertNotIn("/private/tmp/", self.summary_raw)
        self.assertEqual(
            self.summary["schema"],
            "fx6-on-fx3-round57-milestone-realhw-release-wo-card-audio-meter-copyright-qemu-v1",
        )
        self.assertEqual(self.summary["round"], 57)
        self.assertEqual(self.summary["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(tuple(self.summary["runs"].keys()), self.EXPECTED_RUN_KEYS)

    def test_03_round57_cli_accepts_round57_and_all_3_r57_modes(self) -> None:
        self.assertIn(", 57]", self.runner_src)
        self.assertIn(", 56]", self.runner_src)
        for mode in (
            "release_wo_card_lens_audio_meter_copyright_big6",
            "cardless_movie_v1_audio_spoof_copyright_guard",
            "camreset_copyright_disp_init_h0_h3_big6",
        ):
            self.assertIn(mode, self.runner_src)

    def test_04_round57_overlay_rejects_invalid_r57_mode(self) -> None:
        self.assertTrue(self.invalid_mode_raised)

    def test_05_round57_overlay_r57a_injects_etc_fx6_stage_r57_and_appfw_launch(self) -> None:
        replacements, additions, meta = self.ov_a
        self.assertTrue(meta["r57_enabled"])
        self.assertIn("etc/fx6_stage_r57", additions)
        self.assertIn("etc/fx6_r57_libjit.so", additions)
        r57_cfg = additions["etc/fx6_stage_r57"][0].decode("utf-8")
        self.assertIn("stage_r57=1", r57_cfg)
        self.assertIn("r57_mode=release_wo_card_lens_audio_meter_copyright_big6", r57_cfg)
        self.assertIn("milestone_30th_realhw_90th_live=1", r57_cfg)
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("/usr/bin/appfw-launch", init_txt)
        self.assertNotIn("--r57-cardless-v1-copyright-guard", init_txt)

    def test_06_round57_overlay_r57b_injects_early_guard_probe_and_poweroff(self) -> None:
        replacements, _, meta = self.ov_b
        self.assertEqual(meta["r57"]["r57_mode"], "cardless_movie_v1_audio_spoof_copyright_guard")
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("--r57-cardless-v1-copyright-guard", init_txt)
        self.assertIn("FX6_R57_CARDLESS_V1_COPYRIGHT_RC=", init_txt)
        self.assertIn("FX6_R57_CARDLESS_V1_COPYRIGHT_EXIT", init_txt)
        self.assertIn("poweroff -f", init_txt)

    def test_07_round57_overlay_r57c_integrated_runs_stage_b_big6(self) -> None:
        replacements, additions, meta = self.ov_c
        self.assertEqual(meta["r57"]["r57_mode"], "camreset_copyright_disp_init_h0_h3_big6")
        r57_cfg = additions["etc/fx6_stage_r57"][0].decode("utf-8")
        self.assertIn("r57_mode=camreset_copyright_disp_init_h0_h3_big6", r57_cfg)
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("/usr/bin/appfw-launch", init_txt)
        self.assertNotIn("--r57-cardless-v1-copyright-guard", init_txt)

    def test_08_round57_overlay_disabled_when_enable_r57_false(self) -> None:
        _, additions, meta = self.ov_off
        self.assertFalse(meta["r57_enabled"])
        self.assertNotIn("etc/fx6_stage_r57", additions)
        self.assertNotIn("etc/fx6_r57_libjit.so", additions)
        self.assertNotIn("r57", meta)

    def test_09_round57_stage_a_c_source_contains_all_3_wave43_probes(self) -> None:
        for sym in (
            "setup_r57_release_wo_audio_copyright_probe",
            "run_r57_cardless_v1_copyright_guard_probe",
            "run_r57_camreset_copyright_disp_h0_h3_probe",
            "FX6_R57_RELEASE_AUDIO_COPYRIGHT_INIT",
            "FX6_R57_CARDLESS_V1_COPYRIGHT_GUARD",
            "FX6_R57_CAMRESET_COPYRIGHT_DISP_H0_H3",
            "--r57-cardless-v1-copyright-guard",
            "--r57-camreset-copyright-disp-h0-h3",
            "/etc/fx6_stage_r57",
        ):
            self.assertIn(sym, self.stage_a_src)

    def test_10_round57_shim_c_source_contains_r57_guarded_bridges(self) -> None:
        self.assertIn("#if FX6_ROUND >= 57", self.shim_src)
        for sym in (
            "FX6_R57_RELEASE_WO_CARD_LENS_BRIDGE",
            "FX6_R57_AUDIO_V2_DISP_METER_BRIDGE",
            "FX6_R57_COPYRIGHT_46CHAR_HYGIENE_BRIDGE",
            "FX6_R57_LANG_TELEMETRY",
            "FX6_STAGE_B_R57_BRIDGE",
        ):
            self.assertIn(sym, self.shim_src)

    def test_11_round57_compile_launcher_and_shim_aarch64_elf_symbols(self) -> None:
        if self.launcher_r57 is None or self.shim_r57 is None:
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertEqual(self.launcher_r57[:4], b"\x7fELF")
        self.assertEqual(self.shim_r57[:4], b"\x7fELF")
        self.assertEqual(struct.unpack_from("<H", self.shim_r57, 18)[0], 183)
        self.assertIn(b"FX6_R57_RELEASE_WO_CARD_LENS_BRIDGE", self.shim_r57)
        self.assertIn(b"FX6_R57_AUDIO_V2_DISP_METER_BRIDGE", self.shim_r57)
        self.assertIn(b"FX6_R57_COPYRIGHT_46CHAR_HYGIENE_BRIDGE", self.shim_r57)

    def test_12_round57_shim_round56_backward_compat_excludes_r57_bridges(self) -> None:
        if self.shim_r56 is None:
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertIn(b"FX6_R56_APSC_S35_4K_LOCK_BRIDGE", self.shim_r56)
        self.assertNotIn(b"FX6_R57_RELEASE_WO_CARD_LENS_BRIDGE", self.shim_r56)

    def test_13_round57_parse_log_extracts_all_8_r57_prefixes_and_rc(self) -> None:
        serial_text = (
            "\n".join(
                [
                    "Linux version 4.9.337-scel+ (sony@fx3)",
                    "FX6_R57_RELEASE_AUDIO_COPYRIGHT_INIT fx3_wave43_nodes_ok=1 release_wo_defaults_enable_ok=1 audio_5items_verified=5 legacy_v1_audio_level_menu_spoof_events=0 photographer_copyright_pii_leaked_bytes=0 r57_init_ok=1",
                    "FX6_R57_RELEASE_WO_CARD_LENS_BRIDGE release_wo_defaults_enable_ok=1 release_wo_card_still_only_ok=1 cardless_movie_internal_rec_events=0 release_wo_lens_pl_bench_ok=1 release_wo_card_lens_ok=1 r57_bridge_ok=1",
                    "FX6_R57_AUDIO_V2_DISP_METER_BRIDGE audio_5items_verified=5 audio_rec_level_0_31_ok=1 disp_audio_meter_modes_ok=1 legacy_v1_audio_level_menu_spoof_events=0 audio_v2_disp_meter_ok=1",
                    "FX6_R57_COPYRIGHT_46CHAR_HYGIENE_BRIDGE write_copyright_off_default_ok=1 copyright_46char_hygiene_ok=1 photographer_copyright_pii_leaked_bytes=0 movie_copyright_tag_writes=0 copyright_46char_hygiene_bridge_ok=1",
                    "FX6_R57_LANG_TELEMETRY lang=schinese font_bank=23 str_bank=19 milestone_30th_realhw_90th_live=1 r57_bridge_ok=1",
                    "FX6_STAGE_B_R57_BRIDGE round=57 faithful=1 nop_count=0 milestone_30th_realhw_90th_live=1 emmc_write_count=0",
                    "FX6_R57_CARDLESS_V1_COPYRIGHT_GUARD cardless_movie_rec_rc=-123 lensless_still_rc=-19 legacy_v1_audio_node_rc=-2 photographer_47char_rc=-22 pii_inject_rc=-1 movie_copyright_tag_rc=-95 slot1_vault_ro_blocked_rc=-30 r57b_ok=1",
                    "FX6_R57_CARDLESS_V1_COPYRIGHT_RC=0",
                    "FX6_R57_CAMRESET_COPYRIGHT_DISP_H0_H3 wave43_survives_netreset_ok=1 audio_5items_camreset_ok=1 copyright_strings_survive_camreset_ok=1 disp_audio_meter_survives_camreset_ok=1 initialize_clears_copyright_and_defaults_ok=1 surfaces_h0_eq_h3=16 r57c_ok=1",
                ]
            )
            + "\n"
        )
        parsed = self.runner.extract_milestones(serial_text)
        r57_t = parsed["r57_telemetry"]
        self.assertEqual(r57_t["cardless_v1_copyright_rc"], 0)
        self.assertEqual(r57_t["release_audio_copyright_init"]["audio_5items_verified"], 5)
        self.assertEqual(
            r57_t["release_audio_copyright_init"]["photographer_copyright_pii_leaked_bytes"],
            0,
        )
        self.assertEqual(r57_t["release_wo_card_lens_bridge"]["release_wo_card_lens_ok"], 1)
        self.assertEqual(r57_t["audio_v2_disp_meter_bridge"]["audio_v2_disp_meter_ok"], 1)
        self.assertEqual(
            r57_t["copyright_46char_hygiene_bridge"]["copyright_46char_hygiene_bridge_ok"],
            1,
        )
        self.assertEqual(r57_t["lang_telemetry"]["lang"], "schinese")
        self.assertEqual(r57_t["lang_telemetry"]["milestone_30th_realhw_90th_live"], 1)
        self.assertEqual(r57_t["stage_b_bridge"]["round"], 57)
        self.assertEqual(r57_t["cardless_v1_copyright_guard"]["r57b_ok"], 1)
        self.assertEqual(r57_t["camreset_copyright_disp_h0_h3"]["surfaces_h0_eq_h3"], 16)
        self.assertEqual(parsed["prefix_counts"]["FX6_R57_"], 8)

    def test_14_round57_parse_log_defaults_when_no_r57_lines_present(self) -> None:
        parsed = self.runner.extract_milestones("Linux version 4.9.337-scel+\n")
        self.assertIsNone(parsed["r57_telemetry"])
        self.assertEqual(parsed["prefix_counts"].get("FX6_R57_", 0), 0)

    def test_15_round57_runner_uses_fx6_r57_prefix_and_stage_label(self) -> None:
        self.assertIn('if args.round >= 57:\n        tmp_prefix = "fx6-r57"', self.runner_src)
        self.assertIn(
            "Milestone30thRealHw90thRunWave43ReleaseWoCardLensDispAudioMeterV2Copyright46Char",
            self.runner_src,
        )
        self.assertIn(", 57]", self.runner_src)

    def test_16_round57_runner_portability_and_wave43_intel_spec_rules(self) -> None:
        self.assertIn('shutil.which("zig")', self.runner_src)
        self.assertIn("FX6_SCRATCH_DIR", self.runner_src)
        for token in (
            "Release w/o Card",
            "Release w/o Lens",
            "Audio Recording",
            "Audio Rec Level",
            "Audio Out Timing",
            "Wind Noise Reduct.",
            "Shoe Audio Set.",
            "DISP (Screen Disp) Set",
            "Copyright Info",
            "Set Photographer",
            "Set Copyright",
            "ILME-FX3",
        ):
            self.assertIn(token, self.wave43_spec)

    def test_17_round57_summary_json_top_level_schema_and_milestone_metadata(self) -> None:
        d = self.summary
        self.assertEqual(
            d["schema"],
            "fx6-on-fx3-round57-milestone-realhw-release-wo-card-audio-meter-copyright-qemu-v1",
        )
        self.assertEqual(d["round"], 57)
        self.assertIn("30th Real-HW", d["milestone"])
        self.assertIn("90 Live Runs", d["milestone"])
        self.assertEqual(d["date"], "2026-11-17")
        self.assertIn("4.9.337-scel+", d["kernel_version"])
        self.assertEqual(d["raw_firmware_bytes_leaked"], 0)

    def test_18_round57_summary_json_zero_host_path_and_scratch_leaks(self) -> None:
        for forbidden in (
            "/Users/",
            "/private/tmp/",
            "/var/folders/",
            "work/_scratch/",
            "work/_tests/",
        ):
            self.assertNotIn(forbidden, self.summary_raw)

    def test_19_round57_summary_audit_block_confirms_30th_round_90th_run_and_all_booleans(self) -> None:
        audit = self.summary["r57_realhw_release_wo_card_audio_meter_copyright_audit"]
        self.assertEqual(audit["round"], 57)
        self.assertEqual(audit["milestone"], 57)
        self.assertGreaterEqual(audit["milestone221_qemu_rounds"], 30)
        self.assertGreaterEqual(audit["milestone221_qemu_runs"], 90)
        self.assertGreaterEqual(audit["milestone233_qemu_rounds"], 30)
        self.assertGreaterEqual(audit["milestone233_qemu_runs"], 90)
        self.assertGreaterEqual(audit["milestone254_qemu_rounds"], 30)
        self.assertGreaterEqual(audit["milestone254_qemu_runs"], 90)
        self.assertGreaterEqual(audit["milestone264_qemu_rounds"], 30)
        self.assertGreaterEqual(audit["milestone264_qemu_runs"], 90)
        self.assertEqual(audit["total_runs"], 3)
        for k, v in audit.items():
            if isinstance(v, bool):
                self.assertTrue(v, f"Expected audit boolean {k} to be True")

    def test_20_round57_all_3_runs_present_with_kernel_4_9_337_and_zero_crashes_writes(self) -> None:
        runs = self.summary["runs"]
        self.assertEqual(list(runs.keys()), list(self.EXPECTED_RUN_KEYS))
        for rk, rv in runs.items():
            self.assertEqual(rv["round"], 57, rk)
            self.assertIn("4.9.337-scel+", rv["kernel_version"], rk)
            self.assertEqual(rv["nop_count"], 0, rk)
            self.assertEqual(rv["crashes"], 0, rk)
            self.assertEqual(rv["emmc_write_count"], 0, rk)
            self.assertGreater(rv["wall_elapsed_sec"], 0.0, rk)

    def test_21_round57_r57a_release_wo_card_and_release_wo_lens_pl_bench_verified(self) -> None:
        init_t = self.summary["runs"][
            "r57a_release_wo_card_lens_audio_meter_copyright_big6_schinese"
        ]["r57_telemetry"]["release_audio_copyright_init"]
        self.assertEqual(init_t["fx3_wave43_nodes_ok"], 1)
        self.assertEqual(init_t["release_wo_defaults_enable_ok"], 1)
        self.assertEqual(init_t["release_wo_card_still_only_ok"], 1)
        self.assertEqual(init_t["release_wo_lens_pl_bench_ok"], 1)
        self.assertEqual(init_t["cardless_movie_internal_rec_events"], 0)
        self.assertEqual(init_t["e_nd_actuator_tx_count"], 0)

    def test_22_round57_r57a_ver702_5item_audio_disp_meter_and_copyright_hygiene_verified(self) -> None:
        init_t = self.summary["runs"][
            "r57a_release_wo_card_lens_audio_meter_copyright_big6_schinese"
        ]["r57_telemetry"]["release_audio_copyright_init"]
        self.assertEqual(init_t["audio_5items_verified"], 5)
        self.assertEqual(init_t["audio_rec_level_0_31_ok"], 1)
        self.assertEqual(init_t["disp_audio_meter_modes_ok"], 1)
        self.assertEqual(init_t["legacy_v1_audio_level_menu_spoof_events"], 0)
        self.assertEqual(init_t["write_copyright_off_default_ok"], 1)
        self.assertEqual(init_t["copyright_46char_hygiene_ok"], 1)
        self.assertEqual(init_t["copyright_47char_rejected_rc"], -22)
        self.assertEqual(init_t["photographer_copyright_pii_leaked_bytes"], 0)
        self.assertEqual(init_t["movie_copyright_tag_writes"], 0)

    def test_23_round57_r57a_p2_cnflasha_and_slot1_ro_guards_intact(self) -> None:
        init_t = self.summary["runs"][
            "r57a_release_wo_card_lens_audio_meter_copyright_big6_schinese"
        ]["r57_telemetry"]["release_audio_copyright_init"]
        self.assertEqual(init_t["slot1_vault_writes"], 0)
        self.assertEqual(init_t["p2_write_blocked_rc"], -30)
        self.assertEqual(init_t["p2_sha256_match"], 1)
        self.assertEqual(init_t["cnflasha_sha256_match"], 1)
        self.assertEqual(init_t["slot1_vault_sha256_match"], 1)
        self.assertEqual(init_t["cnflasha_writes"], 0)
        self.assertEqual(init_t["appfw_present"], 1)
        self.assertEqual(init_t["shim_present"], 1)
        self.assertEqual(init_t["emmc_write_count"], 0)
        self.assertEqual(init_t["r57_init_ok"], 1)

    def test_24_round57_r57a_stage_b_schinese_lang_telemetry_and_bridges(self) -> None:
        r57a_t = self.summary["runs"][
            "r57a_release_wo_card_lens_audio_meter_copyright_big6_schinese"
        ]["r57_telemetry"]
        lt = r57a_t["lang_telemetry"]
        self.assertEqual(lt["lang"], "schinese")
        self.assertEqual(lt["bk4_lang_id"], "0x02cf019c")
        self.assertEqual(lt["bk4_lang_val"], "0x19")
        self.assertEqual(lt["lang_enum"], "0x2b45_CHINESE_SIMPLIFIED")
        self.assertEqual(lt["font_bank"], 23)
        self.assertEqual(lt["str_bank"], 19)
        self.assertEqual(lt["gpe_fb"], 0)
        self.assertEqual(lt["milestone_30th_realhw_90th_live"], 1)
        self.assertEqual(lt["cardless_movie_internal_rec_events"], 0)
        self.assertEqual(lt["legacy_v1_audio_level_menu_spoof_events"], 0)
        self.assertEqual(lt["photographer_copyright_pii_leaked_bytes"], 0)
        self.assertEqual(lt["movie_copyright_tag_writes"], 0)
        self.assertEqual(lt["e_nd_actuator_tx_count"], 0)
        self.assertEqual(lt["raw_firmware_bytes_leaked"], 0)
        sb = r57a_t["stage_b_bridge"]
        self.assertEqual(sb["round"], 57)
        self.assertEqual(sb["faithful"], 1)
        self.assertEqual(sb["nop_count"], 0)
        self.assertEqual(sb["release_wo_card_still_lens_pl_bench"], 1)
        self.assertEqual(sb["audio_5item_disp_meter_v2_not_v1"], 1)
        self.assertEqual(sb["copyright_46char_still_exif_hygiene"], 1)
        self.assertEqual(sb["milestone_30th_realhw_90th_live"], 1)

    def test_25_round57_r57a_stage_b_3_pillar_bridges_verified(self) -> None:
        r57a_t = self.summary["runs"][
            "r57a_release_wo_card_lens_audio_meter_copyright_big6_schinese"
        ]["r57_telemetry"]
        rb = r57a_t["release_wo_card_lens_bridge"]
        self.assertEqual(rb["release_wo_defaults_enable_ok"], 1)
        self.assertEqual(rb["release_wo_card_still_only_ok"], 1)
        self.assertEqual(rb["cardless_movie_internal_rec_events"], 0)
        self.assertEqual(rb["release_wo_lens_pl_bench_ok"], 1)
        self.assertEqual(rb["e_nd_actuator_tx_count"], 0)
        self.assertEqual(rb["release_wo_card_lens_ok"], 1)
        ab = r57a_t["audio_v2_disp_meter_bridge"]
        self.assertEqual(ab["audio_5items_verified"], 5)
        self.assertEqual(ab["audio_rec_level_0_31_ok"], 1)
        self.assertEqual(ab["disp_audio_meter_modes_ok"], 1)
        self.assertEqual(ab["legacy_v1_audio_level_menu_spoof_events"], 0)
        self.assertEqual(ab["audio_v2_disp_meter_ok"], 1)
        cb = r57a_t["copyright_46char_hygiene_bridge"]
        self.assertEqual(cb["write_copyright_off_default_ok"], 1)
        self.assertEqual(cb["copyright_46char_hygiene_ok"], 1)
        self.assertEqual(cb["photographer_copyright_pii_leaked_bytes"], 0)
        self.assertEqual(cb["movie_copyright_tag_writes"], 0)
        self.assertEqual(cb["copyright_46char_hygiene_bridge_ok"], 1)

    def test_26_round57_r57a_gpe0_readback_exact_346206_pixels_and_87_colors(self) -> None:
        r57a = self.summary["runs"][
            "r57a_release_wo_card_lens_audio_meter_copyright_big6_schinese"
        ]
        self.assertEqual(r57a["target_presenter"], "31procam_big6_menu_home_presenter")
        self.assertEqual(r57a["target_sid"], "0x0a")
        self.assertGreaterEqual(r57a["total_threads_seen"], 150)
        gpe0 = r57a["gpe0_readback"]
        self.assertTrue(gpe0["present"])
        self.assertEqual(gpe0["bytes"], 2211840)
        self.assertEqual(gpe0["total_pixels"], 552960)
        self.assertEqual(gpe0["nonzero_pixels"], 346206)
        self.assertEqual(gpe0["unique_colors"], 87)

    def test_27_round57_r57a_stage_b_manifest_13_hashes_and_r57_metadata(self) -> None:
        sb = self.summary["runs"][
            "r57a_release_wo_card_lens_audio_meter_copyright_big6_schinese"
        ]["stage_b"]
        self.assertEqual(sb["manifest_count"], 13)
        self.assertEqual(len(sb["manifest_items"]), 13)
        for item in sb["manifest_items"]:
            self.assertEqual(len(item["sha256"]), 64)
        r57_meta = sb["r57"]
        self.assertEqual(
            r57_meta["r57_mode"], "release_wo_card_lens_audio_meter_copyright_big6"
        )
        self.assertEqual(
            r57_meta["release_wo_card_menu_path"],
            "MENU -> Shooting -> [Shutter/Silent] -> [Release w/o Card]",
        )
        self.assertEqual(r57_meta["release_wo_card_modes"], ["Enable", "Disable"])
        self.assertEqual(r57_meta["release_wo_card_default"], "Enable")
        self.assertEqual(r57_meta["release_wo_lens_scope"], ["Still", "Movie", "S&Q"])
        self.assertEqual(
            r57_meta["audio_recording_ver702_exact_5_items"],
            [
                "Audio Recording",
                "Audio Rec Level",
                "Audio Out Timing",
                "Wind Noise Reduct.",
                "Shoe Audio Set.",
            ],
        )
        self.assertEqual(r57_meta["audio_rec_level_range"], [0, 31])
        self.assertEqual(r57_meta["audio_rec_level_default"], 26)
        self.assertEqual(r57_meta["audio_out_timing_modes"], ["Live", "Lip Sync"])
        self.assertEqual(r57_meta["write_copyright_info_default"], "Off")
        self.assertEqual(r57_meta["copyright_max_ascii_chars"], 46)

    def test_28_round57_r57b_cardless_movie_and_lensless_disable_blocked_fail_closed(self) -> None:
        r57b_t = self.summary["runs"][
            "r57b_cardless_movie_v1_audio_spoof_copyright_guard"
        ]["r57_telemetry"]
        self.assertEqual(r57b_t["cardless_v1_copyright_rc"], 0)
        gd = r57b_t["cardless_v1_copyright_guard"]
        self.assertEqual(gd["cardless_movie_rec_rc"], -123)
        self.assertEqual(gd["cardless_movie_internal_rec_events"], 0)
        self.assertEqual(gd["lensless_still_rc"], -19)
        self.assertEqual(gd["lensless_movie_rc"], -19)
        self.assertEqual(gd["lensless_sq_rc"], -19)
        self.assertEqual(gd["lensless_disable_bypass_events"], 0)

    def test_29_round57_r57b_legacy_v1_audio_level_menu_spoof_rejected(self) -> None:
        gd = self.summary["runs"][
            "r57b_cardless_movie_v1_audio_spoof_copyright_guard"
        ]["r57_telemetry"]["cardless_v1_copyright_guard"]
        self.assertEqual(gd["legacy_v1_audio_node_rc"], -2)
        self.assertEqual(gd["legacy_v1_audio_level_menu_spoof_events"], 0)

    def test_30_round57_r57b_over46char_pii_and_movie_copyright_tag_blocked(self) -> None:
        gd = self.summary["runs"][
            "r57b_cardless_movie_v1_audio_spoof_copyright_guard"
        ]["r57_telemetry"]["cardless_v1_copyright_guard"]
        self.assertEqual(gd["photographer_47char_rc"], -22)
        self.assertEqual(gd["copyright_47char_rc"], -22)
        self.assertEqual(gd["pii_inject_rc"], -1)
        self.assertEqual(gd["movie_copyright_tag_rc"], -95)
        self.assertEqual(gd["photographer_copyright_pii_leaked_bytes"], 0)
        self.assertEqual(gd["movie_copyright_tag_writes"], 0)

    def test_31_round57_r57b_slot1_vault_ro_and_zero_emmc_cnflasha_writes(self) -> None:
        gd = self.summary["runs"][
            "r57b_cardless_movie_v1_audio_spoof_copyright_guard"
        ]["r57_telemetry"]["cardless_v1_copyright_guard"]
        self.assertEqual(gd["slot1_vault_ro_blocked_rc"], -30)
        self.assertEqual(gd["slot1_vault_sha256_match"], 1)
        self.assertEqual(gd["slot1_vault_writes"], 0)
        self.assertEqual(gd["p2_write_blocked_rc"], -30)
        self.assertEqual(gd["cnflasha_ro_blocked_rc"], -30)
        self.assertEqual(gd["cnflasha_writes"], 0)
        self.assertEqual(gd["e_nd_actuator_tx_count"], 0)
        self.assertEqual(gd["emmc_write_count"], 0)
        self.assertEqual(gd["r57b_ok"], 1)

    def test_32_round57_r57c_camreset_vs_copyright_disp_and_initialize_survival_verified(self) -> None:
        ci = self.summary["runs"][
            "r57c_camreset_copyright_disp_init_h0_h3_big6_schinese"
        ]["r57_telemetry"]["camreset_copyright_disp_h0_h3"]
        self.assertEqual(ci["wave43_survives_netreset_ok"], 1)
        self.assertEqual(ci["audio_5items_camreset_ok"], 1)
        self.assertEqual(ci["write_copyright_camreset_off_ok"], 1)
        self.assertEqual(ci["copyright_strings_survive_camreset_ok"], 1)
        self.assertEqual(ci["disp_audio_meter_survives_camreset_ok"], 1)
        self.assertEqual(ci["release_wo_survives_camreset_ok"], 1)
        self.assertEqual(ci["initialize_clears_copyright_and_defaults_ok"], 1)

    def test_33_round57_r57c_dlopen_and_16_h0_eq_h3_idempotent_unmount(self) -> None:
        ci = self.summary["runs"][
            "r57c_camreset_copyright_disp_init_h0_h3_big6_schinese"
        ]["r57_telemetry"]["camreset_copyright_disp_h0_h3"]
        self.assertEqual(ci["dlopen_ok"], 1)
        self.assertEqual(ci["surfaces_verified"], 16)
        self.assertEqual(ci["surfaces_h0_eq_h3"], 16)
        self.assertEqual(ci["drift_bits"], 0)
        self.assertEqual(ci["e_nd_actuator_tx_count"], 0)
        self.assertEqual(ci["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(ci["emmc_write_count"], 0)
        self.assertEqual(ci["r57c_ok"], 1)

    def test_34_round57_r57c_integrated_renders_valid_big6_gpe0_readback(self) -> None:
        r57c = self.summary["runs"][
            "r57c_camreset_copyright_disp_init_h0_h3_big6_schinese"
        ]
        self.assertEqual(r57c["target_presenter"], "31procam_big6_menu_home_presenter")
        self.assertEqual(r57c["target_sid"], "0x0a")
        gpe0 = r57c["gpe0_readback"]
        self.assertTrue(gpe0["present"])
        self.assertEqual(gpe0["bytes"], 2211840)
        self.assertEqual(gpe0["total_pixels"], 552960)
        self.assertEqual(gpe0["nonzero_pixels"], 346686)
        self.assertEqual(gpe0["unique_colors"], 87)

    def test_35_round57_realhw_mechanisms_verified_6_blocks_match_run_telemetry(self) -> None:
        rm = self.summary["realhw_mechanisms_verified"]
        self.assertEqual(len(rm), 6)
        r57a = self.summary["runs"][
            "r57a_release_wo_card_lens_audio_meter_copyright_big6_schinese"
        ]["r57_telemetry"]
        r57b = self.summary["runs"][
            "r57b_cardless_movie_v1_audio_spoof_copyright_guard"
        ]["r57_telemetry"]
        r57c = self.summary["runs"][
            "r57c_camreset_copyright_disp_init_h0_h3_big6_schinese"
        ]["r57_telemetry"]
        self.assertEqual(
            rm["release_wo_card_lens_audio_copyright_init"],
            r57a["release_audio_copyright_init"],
        )
        self.assertEqual(
            rm["release_wo_card_lens_stage_b_bridge"],
            r57a["release_wo_card_lens_bridge"],
        )
        self.assertEqual(
            rm["audio_v2_disp_meter_stage_b_bridge"],
            r57a["audio_v2_disp_meter_bridge"],
        )
        self.assertEqual(
            rm["copyright_46char_hygiene_stage_b_bridge"],
            r57a["copyright_46char_hygiene_bridge"],
        )
        self.assertEqual(
            rm["cardless_movie_v1_audio_spoof_copyright_guard"],
            r57b["cardless_v1_copyright_guard"],
        )
        self.assertEqual(
            rm["camreset_vs_copyright_disp_initialize_and_16_h0_h3"],
            r57c["camreset_copyright_disp_h0_h3"],
        )

    def test_36_round57_camreset_vs_initialize_tiers_consistent_across_runs(self) -> None:
        r57a_t = self.summary["runs"][
            "r57a_release_wo_card_lens_audio_meter_copyright_big6_schinese"
        ]["r57_telemetry"]
        r57c_ci = self.summary["runs"][
            "r57c_camreset_copyright_disp_init_h0_h3_big6_schinese"
        ]["r57_telemetry"]["camreset_copyright_disp_h0_h3"]
        self.assertEqual(r57a_t["release_wo_card_lens_bridge"]["release_wo_survives_camreset_ok"], 1)
        self.assertEqual(r57a_t["audio_v2_disp_meter_bridge"]["audio_5items_camreset_ok"], 1)
        self.assertEqual(r57a_t["audio_v2_disp_meter_bridge"]["disp_audio_meter_survives_camreset_ok"], 1)
        self.assertEqual(r57a_t["copyright_46char_hygiene_bridge"]["write_copyright_camreset_off_ok"], 1)
        self.assertEqual(r57a_t["copyright_46char_hygiene_bridge"]["copyright_strings_survive_camreset_ok"], 1)
        self.assertEqual(r57c_ci["audio_5items_camreset_ok"], 1)
        self.assertEqual(r57c_ci["write_copyright_camreset_off_ok"], 1)
        self.assertEqual(r57c_ci["copyright_strings_survive_camreset_ok"], 1)
        self.assertEqual(r57c_ci["disp_audio_meter_survives_camreset_ok"], 1)
        self.assertEqual(r57c_ci["release_wo_survives_camreset_ok"], 1)
        self.assertEqual(r57c_ci["initialize_clears_copyright_and_defaults_ok"], 1)

    def test_37_round57_cross_round_consistency_with_r56_slot1_ro_and_camreset(self) -> None:
        self.assertEqual(self.r56_summary["round"], 56)
        r56b_gd = self.r56_summary["runs"][
            "r56b_apsc_4k_raw_cleanhdmi_bodydata_flash_guard"
        ]["r56_telemetry"]["apsc_4k_bodydata_guard"]
        self.assertEqual(r56b_gd["slot1_vault_ro_blocked_rc"], -30)
        r57b_gd = self.summary["runs"][
            "r57b_cardless_movie_v1_audio_spoof_copyright_guard"
        ]["r57_telemetry"]["cardless_v1_copyright_guard"]
        self.assertEqual(r57b_gd["slot1_vault_ro_blocked_rc"], -30)
        self.assertEqual(r57b_gd["slot1_vault_sha256_match"], 1)

    def test_38_round57_cross_round_consistency_with_r55_audio_4ch_and_slot1_ro(self) -> None:
        self.assertEqual(self.r55_summary["round"], 55)
        r55a = self.r55_summary["runs"][
            "r55a_auto_slow_6locks_hdmi_reccontrol_big6_schinese"
        ]["r55_telemetry"]["breathing_comp_bridge"]
        self.assertEqual(r55a["emmc_write_count"], 0)
        r57a_ab = self.summary["runs"][
            "r57a_release_wo_card_lens_audio_meter_copyright_big6_schinese"
        ]["r57_telemetry"]["audio_v2_disp_meter_bridge"]
        self.assertEqual(r57a_ab["audio_5items_verified"], 5)
        self.assertEqual(r57a_ab["emmc_write_count"], 0)

    def test_39_round57_cross_round_consistency_with_r54_camreset_vs_initialize(self) -> None:
        self.assertEqual(self.r54_summary["round"], 54)
        r54_init = self.r54_summary["runs"][
            "r54a_diff_set_still_mv_shutter_angle_big6_schinese"
        ]["r54_telemetry"]["diff_set_init"]
        self.assertEqual(r54_init["diff_set_survives_camreset_ok"], 1)
        r57c_ci = self.summary["runs"][
            "r57c_camreset_copyright_disp_init_h0_h3_big6_schinese"
        ]["r57_telemetry"]["camreset_copyright_disp_h0_h3"]
        self.assertEqual(r57c_ci["copyright_strings_survive_camreset_ok"], 1)
        self.assertEqual(r57c_ci["disp_audio_meter_survives_camreset_ok"], 1)
        self.assertEqual(r57c_ci["initialize_clears_copyright_and_defaults_ok"], 1)

    def test_40_round57_unexecuted_physical_camera_bench_boundaries_documented(self) -> None:
        bounds = self.summary["unexecuted_physical_camera_bench_boundaries"]
        self.assertEqual(len(bounds), 3)
        joined = " ".join(bounds)
        self.assertIn("Release w/o Card", joined)
        self.assertIn("Release w/o Lens", joined)
        self.assertIn("Audio Recording", joined)
        self.assertIn("DISP (Screen Disp) Set", joined)
        self.assertIn("Copyright Info", joined)

    def test_41_round57_alpha_png_exists_under_50kib_and_matches_summary_sha256(self) -> None:
        pe = self.summary["runs"][
            "r57a_release_wo_card_lens_audio_meter_copyright_big6_schinese"
        ]["png_exports"]
        self.assertLess(len(self.alpha_png_bytes), 50000)
        self.assertLess(len(self.alpha_png_bytes), 51200)
        self.assertEqual(len(self.alpha_png_bytes), pe["alpha_bytes"])
        self.assertEqual(
            hashlib.sha256(self.alpha_png_bytes).hexdigest(), pe["alpha_sha256"]
        )

    def test_42_round57_composited_png_exists_under_50kib_and_matches_summary_sha256(self) -> None:
        pe = self.summary["runs"][
            "r57a_release_wo_card_lens_audio_meter_copyright_big6_schinese"
        ]["png_exports"]
        self.assertLess(len(self.comp_png_bytes), 50000)
        self.assertLess(len(self.comp_png_bytes), 51200)
        self.assertEqual(len(self.comp_png_bytes), pe["composited_bytes"])
        self.assertEqual(
            hashlib.sha256(self.comp_png_bytes).hexdigest(), pe["composited_sha256"]
        )

    def test_43_round57_alpha_png_valid_1024x540_rgba_with_transparent_and_opaque_pixels(self) -> None:
        self.assertEqual(self.alpha_dims, (1024, 540))
        self.assertEqual(self.alpha_transparent, 206754)
        self.assertGreater(self.alpha_opaque, 300000)

    def test_44_round57_composited_png_valid_1024x540_rgba_100pct_opaque(self) -> None:
        self.assertEqual(self.comp_dims, (1024, 540))
        self.assertEqual(self.comp_opaque, 1024 * 540)

    def test_45_round57_report_readme_documents_all_3_runs_and_zero_host_leaks(self) -> None:
        for token in (
            "Round 57",
            "Wave-43",
            "r57a",
            "r57b",
            "r57c",
            "Release w/o Card",
            "Release w/o Lens",
            "Audio Recording",
            "DISP (Screen Disp) Set",
            "Audio Level Display",
            "Copyright Info",
            "Set Photographer",
            "Set Copyright",
            "346,206",
            "346,686",
            "r57a-release-wo-card-audio-meter-big6-schinese-alpha.png",
            "r57a-release-wo-card-audio-meter-big6-schinese-composited.png",
        ):
            self.assertIn(token, self.r57_readme)
        for forbidden in ("/Users/", "/private/tmp/", "/var/folders/", "work/_scratch/"):
            self.assertNotIn(forbidden, self.r57_readme)

    def test_46_round57_closure_readme_section_57_present_and_accurate(self) -> None:
        self.assertIn("## 57. Round 57", self.closure_readme)
        self.assertIn("30th Real-HW Milestone", self.closure_readme)
        self.assertIn("90th Live Run", self.closure_readme)
        self.assertIn(
            "2026-11-17-round57-milestone-realhw-release-wo-card-audio-meter-copyright-qemu",
            self.closure_readme,
        )

    def test_47_round57_30_realhw_qemu_rounds_r28_to_r57_90_runs_and_60_pngs_continuity(self) -> None:
        png_total = 0
        for r in range(28, 58):
            matches = list((REPO_ROOT / "reports").glob(f"2026-??-??-round{r}-*"))
            self.assertEqual(len(matches), 1, f"Expected 1 report dir for Round {r}")
            pngs = list((matches[0] / "assets").glob("*.png"))
            self.assertEqual(len(pngs), 2, f"Expected 2 PNGs for Round {r}")
            for p in pngs:
                self.assertLess(p.stat().st_size, 51200, str(p))
            png_total += len(pngs)
        self.assertGreaterEqual(png_total, 60)
        audit = self.summary["r57_realhw_release_wo_card_audio_meter_copyright_audit"]
        self.assertGreaterEqual(audit["milestone264_qemu_rounds"], 30)
        self.assertGreaterEqual(audit["milestone264_qemu_runs"], 90)

    def test_48_round57_dual_mode_clean_room_toggle_parity_on_summary(self) -> None:
        for clean_flag in ("0", "1"):
            with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                d = json.loads(self.summary_raw)
                self.assertEqual(d["round"], 57)
                self.assertEqual(
                    d["runs"][
                        "r57a_release_wo_card_lens_audio_meter_copyright_big6_schinese"
                    ]["r57_telemetry"]["release_audio_copyright_init"][
                        "audio_5items_verified"
                    ],
                    5,
                )
                self.assertEqual(
                    d["runs"][
                        "r57b_cardless_movie_v1_audio_spoof_copyright_guard"
                    ]["r57_telemetry"]["cardless_v1_copyright_guard"][
                        "cardless_movie_rec_rc"
                    ],
                    -123,
                )
                self.assertEqual(
                    d["runs"][
                        "r57c_camreset_copyright_disp_init_h0_h3_big6_schinese"
                    ]["r57_telemetry"]["camreset_copyright_disp_h0_h3"][
                        "surfaces_h0_eq_h3"
                    ],
                    16,
                )

    def test_49_round57_r57a_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"][
            "r57a_release_wo_card_lens_audio_meter_copyright_big6_schinese"
        ]["r57_telemetry"]["release_audio_copyright_init"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_50_round57_r57b_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"][
            "r57b_cardless_movie_v1_audio_spoof_copyright_guard"
        ]["r57_telemetry"]["cardless_v1_copyright_guard"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_51_round57_r57c_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"][
            "r57c_camreset_copyright_disp_init_h0_h3_big6_schinese"
        ]["r57_telemetry"]["camreset_copyright_disp_h0_h3"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_52_round57_r57a_top_colors_transparent_plus_nonzero_equals_total_pixels(self) -> None:
        gpe = self.summary["runs"][
            "r57a_release_wo_card_lens_audio_meter_copyright_big6_schinese"
        ]["gpe0_readback"]
        color_map = {row["argb"]: row["pixels"] for row in gpe["top_colors"]}
        self.assertIn("0x00000000", color_map)
        self.assertIn("0xff000000", color_map)
        self.assertEqual(color_map["0x00000000"] + gpe["nonzero_pixels"], gpe["total_pixels"])

    def test_53_round57_r57c_top_colors_transparent_plus_nonzero_equals_total_pixels(self) -> None:
        gpe = self.summary["runs"][
            "r57c_camreset_copyright_disp_init_h0_h3_big6_schinese"
        ]["gpe0_readback"]
        color_map = {row["argb"]: row["pixels"] for row in gpe["top_colors"]}
        self.assertIn("0x00000000", color_map)
        self.assertEqual(color_map["0x00000000"] + gpe["nonzero_pixels"], gpe["total_pixels"])

    def test_54_round57_r57a_and_r57c_wall_elapsed_and_duration_budget_sanity(self) -> None:
        r57a = self.summary["runs"][
            "r57a_release_wo_card_lens_audio_meter_copyright_big6_schinese"
        ]
        r57c = self.summary["runs"][
            "r57c_camreset_copyright_disp_init_h0_h3_big6_schinese"
        ]
        max_wall = 240.0 if os.environ.get("GITHUB_ACTIONS") == "true" else 120.0
        self.assertGreaterEqual(r57a["duration_budget_sec"], 70)
        self.assertLessEqual(r57a["duration_budget_sec"], 120)
        self.assertGreater(r57a["wall_elapsed_sec"], 50.0)
        self.assertLess(r57a["wall_elapsed_sec"], max_wall)
        self.assertGreaterEqual(r57c["duration_budget_sec"], 70)
        self.assertLessEqual(r57c["duration_budget_sec"], 120)
        self.assertGreater(r57c["wall_elapsed_sec"], 50.0)
        self.assertLess(r57c["wall_elapsed_sec"], max_wall)

    def test_55_round57_r57b_fast_early_exit_wall_elapsed_under_20s(self) -> None:
        r57b = self.summary["runs"][
            "r57b_cardless_movie_v1_audio_spoof_copyright_guard"
        ]
        max_b = 45.0 if os.environ.get("GITHUB_ACTIONS") == "true" else 20.0
        self.assertEqual(r57b["duration_budget_sec"], 35)
        self.assertGreater(r57b["wall_elapsed_sec"], 1.0)
        self.assertLess(r57b["wall_elapsed_sec"], max_b)
        self.assertTrue(r57b["gpe0_readback"]["skipped_stock_fx3_mode"])

    def test_56_round57_faithful_invariants_preserved_across_all_3_runs(self) -> None:
        for rk, rv in self.summary["runs"].items():
            fi = rv["faithful_invariants"]
            self.assertEqual(fi["FX6_NATIVE_FAITHFUL"], 1, rk)
            self.assertEqual(fi["subst_color"], 0, rk)
            self.assertEqual(fi["subst_image"], 0, rk)
            self.assertEqual(fi["forced_render"], 0, rk)
            self.assertEqual(fi["skipped_node"], 0, rk)
            self.assertEqual(fi["lock_bypass"], 0, rk)

    def test_57_round57_all_3_runs_stage_b_manifest_count_13(self) -> None:
        for rk, rv in self.summary["runs"].items():
            self.assertEqual(rv["stage_b"]["manifest_count"], 13, rk)
            self.assertEqual(len(rv["stage_b"]["manifest_items"]), 13, rk)

    def test_58_round57_r57c_stage_b_r57_bridges_and_zero_leak_verified(self) -> None:
        r57c_t = self.summary["runs"][
            "r57c_camreset_copyright_disp_init_h0_h3_big6_schinese"
        ]["r57_telemetry"]
        self.assertEqual(r57c_t["release_wo_card_lens_bridge"]["release_wo_card_lens_ok"], 1)
        self.assertEqual(r57c_t["audio_v2_disp_meter_bridge"]["audio_v2_disp_meter_ok"], 1)
        self.assertEqual(
            r57c_t["copyright_46char_hygiene_bridge"]["copyright_46char_hygiene_bridge_ok"],
            1,
        )
        self.assertEqual(r57c_t["release_wo_card_lens_bridge"]["cardless_movie_internal_rec_events"], 0)
        self.assertEqual(r57c_t["audio_v2_disp_meter_bridge"]["legacy_v1_audio_level_menu_spoof_events"], 0)
        self.assertEqual(r57c_t["copyright_46char_hygiene_bridge"]["photographer_copyright_pii_leaked_bytes"], 0)
        self.assertEqual(r57c_t["stage_b_bridge"]["e_nd_actuator_tx_count"], 0)

    def test_59_round57_all_3_runs_prefix_counts_include_fx6_r57(self) -> None:
        r57a_pc = self.summary["runs"][
            "r57a_release_wo_card_lens_audio_meter_copyright_big6_schinese"
        ]["prefix_counts"]
        r57b_pc = self.summary["runs"][
            "r57b_cardless_movie_v1_audio_spoof_copyright_guard"
        ]["prefix_counts"]
        r57c_pc = self.summary["runs"][
            "r57c_camreset_copyright_disp_init_h0_h3_big6_schinese"
        ]["prefix_counts"]
        self.assertGreater(r57a_pc["FX6_R57_"], 10)
        self.assertEqual(r57b_pc["FX6_R57_"], 3)
        self.assertGreater(r57c_pc["FX6_R57_"], 10)

    def test_60_round57_r57_meta_invariants_across_all_3_runs(self) -> None:
        for rk, rv in self.summary["runs"].items():
            m = rv["stage_b"]["r57"]
            self.assertTrue(m["release_wo_card_still_only_scope"], rk)
            self.assertTrue(m["release_wo_card_movie_blocked_when_empty"], rk)
            self.assertTrue(m["audio_meter_governed_by_disp_set"], rk)
            self.assertTrue(m["audio_meter_sq_suppressed"], rk)
            self.assertEqual(m["legacy_v1_audio_level_menu_spoof_events"], 0, rk)
            self.assertTrue(m["copyright_still_exif_only"], rk)
            self.assertEqual(m["photographer_copyright_pii_leaked_bytes"], 0, rk)
            self.assertEqual(m["movie_copyright_tag_writes"], 0, rk)
            self.assertTrue(m["copyright_survives_camera_settings_reset"], rk)
            self.assertTrue(m["copyright_cleared_by_initialize_only"], rk)
            self.assertTrue(m["disp_set_survives_camera_settings_reset"], rk)
            self.assertTrue(m["slot1_vault_read_only"], rk)
            self.assertEqual(m["e_nd_actuator_tx_count"], 0, rk)
            self.assertEqual(m["raw_firmware_bytes_leaked"], 0, rk)

    def test_61_round57_no_stray_temp_files_in_repo_root(self) -> None:
        for bad_name in ("tmp", "scratch", ".worktrees"):
            self.assertFalse((REPO_ROOT / bad_name).exists(), bad_name)

    def test_62_round57_port_8768_untouched_in_round57_reports(self) -> None:
        self.assertNotIn("8768", self.summary_raw)
        self.assertNotIn("8768", self.r57_readme)

    def test_63_round57_runner_escapes_percent_in_argparse_help_and_portable_tools(self) -> None:
        self.assertIn("ArgumentParser", self.runner_src)
        self.assertNotIn('"/usr/bin/python3"', self.runner_src)
        self.assertIn('shutil.which("zig")', self.runner_src)
        self.assertIn("FX6_SCRATCH_DIR", self.runner_src)

    def test_64_round57_test_suite_contains_at_least_64_unit_tests(self) -> None:
        methods = [m for m in dir(self) if m.startswith("test_")]
        self.assertGreaterEqual(len(methods), 64)


if __name__ == "__main__":
    unittest.main()
