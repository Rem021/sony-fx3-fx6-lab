#!/usr/bin/env python3
"""Offline dual-mode unit tests for FX6-on-FX3 Round 64 (64th Round Power-of-Two Grand Milestone, 37/37 Real-HW Rounds, 109th..111th Live Runs -> 111/111 Total, 74/74 PNGs — Wave-50)."""
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
ROUND64_REPORT_DIR = (
    REPO_ROOT
    / "reports"
    / "2026-11-17-round64-milestone-focus-area-zoom-lever-iso-minss-flash-qemu"
)
WAVE50_SPEC_PATH = (
    REPO_ROOT
    / "reports"
    / "2026-11-17-global-sony-wave50-milestone-focus-area-zoom-lever-speed-iso-auto-minss-flash-intel"
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


def _build_overlay_for_r64(
    runner,
    parent_cpio: pathlib.Path,
    fp,
    fv,
    fb,
    fake_run,
    jit_meta: Dict[str, Any],
    work: pathlib.Path,
    r64_mode: str,
    lang: str = "schinese",
    enable_r64: bool = True,
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
            enable_r57=True,
            r57_mode="release_wo_card_lens_audio_meter_copyright_big6",
            enable_r58=True,
            r58_mode="file_settings_camid_gamma_assist_tcub_big6",
            enable_r59=True,
            r59_mode="focus_mag_datetime_videolight_hdmires_big6",
            enable_r60=True,
            r60_mode="power_save_monitor_lang_vol_delete_big6",
            enable_r61=True,
            r61_mode="usb_hdmi_protect_netreset_big6",
            enable_r62=True,
            r62_mode="pp_scinetone_look_wb_metering_big6",
            enable_r63=True,
            r63_mode="still_raw_heif_colorspace_shutter_drive_big6",
            enable_r64=enable_r64,
            r64_mode=r64_mode,
            sd_manifest_mode="valid",
            lang=lang,
            shim_bytes=b"SHIM",
        )


class TestRound64MilestoneFocusAreaZoomLeverIsoMinssFlashQemu(unittest.TestCase):
    EXPECTED_RUN_KEYS = (
        "r64a_focus_area_zoom_iso_flash_big6_schinese",
        "r64b_wave50_focus_zoom_iso_flash_guard",
        "r64c_clean_unmount_wave50_reset_h0_h3_big6_schinese",
    )

    runner: Any
    runner_src: str
    stage_a_src: str
    shim_src: str
    wave50_spec: str
    summary_raw: str
    summary: Dict[str, Any]
    r64_readme: str
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
    launcher_r64: Optional[bytes]
    shim_r64: Optional[bytes]
    shim_r63: Optional[bytes]
    r63_summary: Dict[str, Any]
    r62_summary: Dict[str, Any]
    r61_summary: Dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = _load_closure_module("fx6_brr_r64_cached", "build_and_run_round.py")
        cls.runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")
        cls.stage_a_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        cls.shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        cls.wave50_spec = WAVE50_SPEC_PATH.read_text(encoding="utf-8")
        cls.summary_raw = (ROUND64_REPORT_DIR / "summary.json").read_text(encoding="utf-8")
        cls.summary = json.loads(cls.summary_raw)
        cls.r64_readme = (ROUND64_REPORT_DIR / "README.md").read_text(encoding="utf-8")
        cls.closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")

        alpha_p = (
            ROUND64_REPORT_DIR
            / "assets"
            / "r64a-focus-area-zoom-iso-flash-4ch-big6-schinese-alpha.png"
        )
        comp_p = (
            ROUND64_REPORT_DIR
            / "assets"
            / "r64a-focus-area-zoom-iso-flash-4ch-big6-schinese-composited.png"
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
            cls.ov_a = _build_overlay_for_r64(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wa", "focus_area_zoom_iso_flash_big6", lang="schinese",
            )
            cls.ov_b = _build_overlay_for_r64(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wb", "wave50_focus_zoom_iso_flash_guard", lang="en",
            )
            cls.ov_c = _build_overlay_for_r64(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wc", "clean_unmount_wave50_reset_h0_h3_big6", lang="schinese",
            )
            cls.ov_off = _build_overlay_for_r64(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "woff", "focus_area_zoom_iso_flash_big6", enable_r64=False,
            )
            cls.invalid_mode_raised = False
            try:
                _build_overlay_for_r64(
                    cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                    tpath / "wbad", "invalid_r64_mode",
                )
            except ValueError:
                cls.invalid_mode_raised = True

            zig_bin = shutil.which("zig") or (
                str(cls.runner.ZIG) if cls.runner.ZIG.is_file() else None
            )
            if zig_bin is not None:
                verify_r64_out = tpath / "fx6-stage-a-verify-r64"
                shim_r64_out = tpath / "libgrm-fbinit9-r64.so"
                shim_r63_out = tpath / "libgrm-fbinit9-r63.so"
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
                        str(verify_r64_out),
                    ],
                    [
                        zig_bin,
                        "cc",
                        "-target",
                        "aarch64-linux-gnu.2.25",
                        "-O0",
                        "-shared",
                        "-fPIC",
                        "-DFX6_ROUND=64",
                        str(CLOSURE_DIR / "libgrm-fbinit9.c"),
                        "-ldl",
                        "-lpthread",
                        "-o",
                        str(shim_r64_out),
                    ],
                    [
                        zig_bin,
                        "cc",
                        "-target",
                        "aarch64-linux-gnu.2.25",
                        "-O0",
                        "-shared",
                        "-fPIC",
                        "-DFX6_ROUND=63",
                        str(CLOSURE_DIR / "libgrm-fbinit9.c"),
                        "-ldl",
                        "-lpthread",
                        "-o",
                        str(shim_r63_out),
                    ],
                ):
                    cls.runner.subprocess.run(cmd, check=True)
                cls.launcher_r64 = verify_r64_out.read_bytes()
                cls.shim_r64 = shim_r64_out.read_bytes()
                cls.shim_r63 = shim_r63_out.read_bytes()
            else:
                cls.launcher_r64 = None
                cls.shim_r64 = None
                cls.shim_r63 = None

        cls.r63_summary = json.loads(
            (
                REPO_ROOT
                / "reports"
                / "2026-11-17-round63-realhw-still-raw-heif-colorspace-shuttertype-drive-qemu"
                / "summary.json"
            ).read_text(encoding="utf-8")
        )
        cls.r62_summary = json.loads(
            (
                REPO_ROOT
                / "reports"
                / "2026-11-17-round62-milestone-35realhw-pp-scinetone-creativelook-wb-metering-qemu"
                / "summary.json"
            ).read_text(encoding="utf-8")
        )
        cls.r61_summary = json.loads(
            (
                REPO_ROOT
                / "reports"
                / "2026-11-17-round61-milestone-100runs-usb-mode-hdmi-info-protect-reset-network-qemu"
                / "summary.json"
            ).read_text(encoding="utf-8")
        )

    def test_01_wave50_global_spec_present_and_covers_all_wave50_pillars(self) -> None:
        self.assertTrue(WAVE50_SPEC_PATH.is_file())
        for needle in (
            "Focus Area",
            "Tracking: Wide",
            "Focus Area Limit",
            "Focus Area Color",
            "Circ. of Focus Point",
            "AF Area Registration",
            "Zoom Lever Speed",
            "XLR-H1",
            "Handle Zoom",
            "Zoom Position Display",
            "ISO Range Limit",
            "ISO AUTO Min. SS",
            "Cine EI",
            "Flash Mode",
            "1/250",
            "Video Light Mode",
            "Power Link",
            "REC Link&STBY",
        ):
            self.assertIn(needle, self.wave50_spec)

    def test_02_round64_summary_schema_round_milestone_and_zero_leaks(self) -> None:
        self.assertNotIn("/Users/", self.summary_raw)
        self.assertNotIn("/private/tmp/", self.summary_raw)
        self.assertEqual(
            self.summary["schema"],
            "fx6-on-fx3-round64-milestone-37realhw-focus-area-zoom-lever-iso-minss-flash-qemu-v1",
        )
        self.assertEqual(self.summary["round"], 64)
        self.assertEqual(self.summary["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(tuple(self.summary["runs"].keys()), self.EXPECTED_RUN_KEYS)

    def test_03_round64_cli_accepts_round64_and_all_3_r64_modes(self) -> None:
        self.assertIn(", 63, 64]", self.runner_src)
        for mode in (
            "focus_area_zoom_iso_flash_big6",
            "wave50_focus_zoom_iso_flash_guard",
            "clean_unmount_wave50_reset_h0_h3_big6",
        ):
            self.assertIn(mode, self.runner_src)

    def test_04_round64_overlay_rejects_invalid_r64_mode(self) -> None:
        self.assertTrue(self.invalid_mode_raised)

    def test_05_round64_overlay_r64a_injects_etc_fx6_stage_r64_and_appfw_launch(self) -> None:
        replacements, additions, meta = self.ov_a
        self.assertTrue(meta["r64_enabled"])
        self.assertIn("etc/fx6_stage_r64", additions)
        self.assertIn("etc/fx6_r64_libjit.so", additions)
        r64_cfg = additions["etc/fx6_stage_r64"][0].decode("utf-8")
        self.assertIn("stage_r64=1", r64_cfg)
        self.assertIn("r64_mode=focus_area_zoom_iso_flash_big6", r64_cfg)
        self.assertIn("milestone_64th_round_37th_realhw_111th_live_74_pngs=1", r64_cfg)
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("/usr/bin/appfw-launch", init_txt)
        self.assertNotIn("--r64-wave50-guard", init_txt)

    def test_06_round64_overlay_r64b_injects_early_guard_probe_and_poweroff(self) -> None:
        replacements, _, meta = self.ov_b
        self.assertEqual(meta["r64"]["r64_mode"], "wave50_focus_zoom_iso_flash_guard")
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("--r64-wave50-guard", init_txt)
        self.assertIn("FX6_R64_WAVE50_GUARD_RC=", init_txt)
        self.assertIn("FX6_R64_WAVE50_GUARD_EXIT", init_txt)
        self.assertIn("poweroff -f", init_txt)

    def test_07_round64_overlay_r64c_integrated_runs_stage_b_big6(self) -> None:
        _, additions, meta = self.ov_c
        replacements, _, _ = self.ov_c
        self.assertEqual(meta["r64"]["r64_mode"], "clean_unmount_wave50_reset_h0_h3_big6")
        r64_cfg = additions["etc/fx6_stage_r64"][0].decode("utf-8")
        self.assertIn("r64_mode=clean_unmount_wave50_reset_h0_h3_big6", r64_cfg)
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("/usr/bin/appfw-launch", init_txt)
        self.assertNotIn("--r64-wave50-guard", init_txt)

    def test_08_round64_overlay_disabled_when_enable_r64_false(self) -> None:
        _, additions, meta = self.ov_off
        self.assertFalse(meta["r64_enabled"])
        self.assertNotIn("etc/fx6_stage_r64", additions)
        self.assertNotIn("etc/fx6_r64_libjit.so", additions)
        self.assertNotIn("r64", meta)

    def test_09_round64_stage_a_c_source_contains_all_3_wave50_probes(self) -> None:
        for sym in (
            "setup_r64_focus_zoom_iso_flash_probe",
            "run_r64_wave50_guard_probe",
            "run_r64_clean_unmount_wave50_h0_h3_probe",
            "FX6_R64_WAVE50_INIT",
            "FX6_R64_WAVE50_GUARD",
            "FX6_R64_CLEAN_UNMOUNT_WAVE50_H0_H3",
            "--r64-wave50-guard",
            "--r64-clean-unmount-wave50-h0-h3",
            "/etc/fx6_stage_r64",
        ):
            self.assertIn(sym, self.stage_a_src)

    def test_10_round64_shim_c_source_contains_r64_guarded_bridges(self) -> None:
        self.assertIn("#if FX6_ROUND >= 64", self.shim_src)
        for sym in (
            "FX6_R64_FOCUS_AREA_14MODE_LIMIT_REG_BRIDGE",
            "FX6_R64_ZOOM_LEVER_XLRH1_FX6_BRIDGE",
            "FX6_R64_ISO_LIMIT_MINSS_CINEEI_BRIDGE",
            "FX6_R64_FLASH_STILL_VIDEOLIGHT_PMIC_BRIDGE",
            "FX6_R64_LANG_TELEMETRY",
            "FX6_STAGE_B_R64_BRIDGE",
        ):
            self.assertIn(sym, self.shim_src)

    def test_11_round64_compile_launcher_and_shim_aarch64_elf_symbols(self) -> None:
        if self.launcher_r64 is None or self.shim_r64 is None:
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertEqual(self.launcher_r64[:4], b"\x7fELF")
        self.assertEqual(self.shim_r64[:4], b"\x7fELF")
        self.assertEqual(struct.unpack_from("<H", self.shim_r64, 18)[0], 183)
        self.assertIn(b"FX6_R64_FOCUS_AREA_14MODE_LIMIT_REG_BRIDGE", self.shim_r64)
        self.assertIn(b"FX6_R64_ZOOM_LEVER_XLRH1_FX6_BRIDGE", self.shim_r64)
        self.assertIn(b"FX6_R64_ISO_LIMIT_MINSS_CINEEI_BRIDGE", self.shim_r64)
        self.assertIn(b"FX6_R64_FLASH_STILL_VIDEOLIGHT_PMIC_BRIDGE", self.shim_r64)

    def test_12_round64_shim_round63_backward_compat_excludes_r64_bridges(self) -> None:
        if self.shim_r63 is None:
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertIn(b"FX6_R63_STILL_RAW_HEIF_HLG_BRIDGE", self.shim_r63)
        self.assertNotIn(b"FX6_R64_FOCUS_AREA_14MODE_LIMIT_REG_BRIDGE", self.shim_r63)

    def test_13_round64_parse_log_extracts_all_9_r64_prefixes_and_rc(self) -> None:
        serial_text = (
            "\n".join(
                [
                    "Linux version 4.9.337-scel+ (sony@fx3)",
                    "FX6_R64_WAVE50_INIT fx3_wave50_nodes_ok=1 uxc_tokens_ok=1 focus_area_14mode_ok=1 zoom_lever_xlrh1_fx6_ok=1 iso_limit_minss_cineei_ok=1 flash_still_videolight_ok=1 emmc_write_count=0 r64_init_ok=1",
                    "FX6_R64_FOCUS_AREA_14MODE_LIMIT_REG_BRIDGE focus_14area_still_afc_split_ok=1 focus_area_limit_ge2_color_circ_ok=1 af_area_reg_fx6_3area_enoent_ok=1 focus_area_14mode_ok=1 movie_tracking_focus_area_bypass_events=0 r64_bridge_ok=1",
                    "FX6_R64_ZOOM_LEVER_XLRH1_FX6_BRIDGE body_wt_zoom_lever_1st3_2nd8_ok=1 xlr_h1_zoom_less_enodev_ok=1 fx6_handle_zoom_1_8_pos_0_99_hold_ok=1 zoom_lever_xlrh1_fx6_ok=1 xlr_h1_zoom_spoof_events=0 p2_setting_writes=0",
                    "FX6_R64_ISO_LIMIT_MINSS_CINEEI_BRIDGE iso_range_limit_manual_hlg_ok=1 still_pa_iso_auto_min_ss_ok=1 cine_ei_base_iso_pin_lock_ok=1 iso_limit_minss_cineei_ok=1 cine_ei_gain_override_events=0",
                    "FX6_R64_FLASH_STILL_VIDEOLIGHT_PMIC_BRIDGE still_flash_mech_sync_250v_ok=1 dormant_adv_flash_wireless_guard_ok=1 video_light_4mode_5v_900ma_slot1_erofs_ok=1 flash_still_videolight_ok=1 still_flash_lockout_bypass_events=0 pmic_5v_overcurrent_events=0 slot1_wave50_write_events=0 cnflasha_writes=0",
                    "FX6_R64_LANG_TELEMETRY lang=schinese font_bank=23 str_bank=19 milestone_64th_round_37th_realhw_111th_live_74_pngs=1 r64_bridge_ok=1",
                    "FX6_STAGE_B_R64_BRIDGE round=64 faithful=1 nop_count=0 milestone_64th_round_37th_realhw_111th_live_74_pngs=1 emmc_write_count=0",
                    "FX6_R64_WAVE50_GUARD movie_tracking_wide_rc=-16 fa_limit_1_rc=-22 xlr_h1_zoom_spoof_rc=-19 fx6_speed_99_rc=-22 minss_movie_rc=-16 cineei_manual_iso_rc=-16 flash_movie_rc=-16 flash_eshutter_rc=-95 flash_sync320_rc=-22 flash_adv_dormant_rc=-95 flash_250v_rc=-75 videolight_950ma_rc=-75 slot1_wave50_erofs_rc=-30 r64b_ok=1",
                    "FX6_R64_WAVE50_GUARD_RC=0",
                    "FX6_R64_CLEAN_UNMOUNT_WAVE50_H0_H3 stock_unmount_restored_ok=1 camreset_preserves_wave50_survivors_ok=1 initialize_restores_wave50_defaults_ok=1 xlrh1_and_fx6_handle_hold_ok=1 surfaces_h0_eq_h3=16 r64c_ok=1",
                ]
            )
            + "\n"
        )
        parsed = self.runner.extract_milestones(serial_text)
        r64_t = parsed["r64_telemetry"]
        self.assertEqual(r64_t["wave50_guard_rc"], 0)
        self.assertEqual(r64_t["wave50_init"]["focus_area_14mode_ok"], 1)
        self.assertEqual(r64_t["focus_area_14mode_bridge"]["focus_area_14mode_ok"], 1)
        self.assertEqual(r64_t["zoom_lever_xlrh1_fx6_bridge"]["zoom_lever_xlrh1_fx6_ok"], 1)
        self.assertEqual(r64_t["iso_limit_minss_cineei_bridge"]["iso_limit_minss_cineei_ok"], 1)
        self.assertEqual(r64_t["flash_still_videolight_bridge"]["flash_still_videolight_ok"], 1)
        self.assertEqual(r64_t["lang_telemetry"]["lang"], "schinese")
        self.assertEqual(r64_t["lang_telemetry"]["milestone_64th_round_37th_realhw_111th_live_74_pngs"], 1)
        self.assertEqual(r64_t["stage_b_bridge"]["round"], 64)
        self.assertEqual(r64_t["wave50_guard"]["r64b_ok"], 1)
        self.assertEqual(r64_t["clean_unmount_wave50_h0_h3"]["surfaces_h0_eq_h3"], 16)
        self.assertEqual(parsed["prefix_counts"]["FX6_R64_"], 9)

    def test_14_round64_parse_log_defaults_when_no_r64_lines_present(self) -> None:
        parsed = self.runner.extract_milestones("Linux version 4.9.337-scel+\n")
        self.assertIsNone(parsed["r64_telemetry"])
        self.assertEqual(parsed["prefix_counts"].get("FX6_R64_", 0), 0)

    def test_15_round64_runner_uses_fx6_r64_prefix_and_stage_label(self) -> None:
        self.assertIn('if args.round >= 64:\n        tmp_prefix = "fx6-r64"', self.runner_src)
        self.assertIn(
            "Milestone64thRound37RealHw111thLiveWave50Focus14AreaZoomLeverXlrH1IsoMinSsCineEiMechFlashVideoLight",
            self.runner_src,
        )
        self.assertIn(", 63, 64]", self.runner_src)

    def test_16_round64_runner_portability_and_sanitizer_helper(self) -> None:
        self.assertIn('shutil.which("zig")', self.runner_src)
        self.assertIn("FX6_SCRATCH_DIR", self.runner_src)
        self.assertIn("def sanitize_round64_summary(", self.runner_src)
        self.assertNotIn("/usr/" + "bin/python3", self.runner_src)

    def test_17_round64_summary_json_top_level_schema_and_milestone_metadata(self) -> None:
        d = self.summary
        self.assertEqual(
            d["schema"],
            "fx6-on-fx3-round64-milestone-37realhw-focus-area-zoom-lever-iso-minss-flash-qemu-v1",
        )
        self.assertEqual(d["round"], 64)
        self.assertIn("64th Round Power-of-Two Grand Milestone!", d["milestone"])
        self.assertIn("37/37 Real-HW Rounds", d["milestone"])
        self.assertIn("111/111 Total Live Runs", d["milestone"])
        self.assertIn("74/74 PNGs", d["milestone"])
        self.assertEqual(d["date"], "2026-11-17")
        self.assertIn("4.9.337-scel+", d["kernel_version"])
        self.assertEqual(d["raw_firmware_bytes_leaked"], 0)

    def test_18_round64_summary_json_zero_host_path_and_scratch_leaks(self) -> None:
        for forbidden in (
            "/Users/",
            "/private/tmp/",
            "/var/folders/",
            "work/_scratch/",
            "work/_tests/",
            ":87" + "68",
        ):
            self.assertNotIn(forbidden, self.summary_raw)

    def test_19_round64_summary_audit_block_confirms_37_rounds_111_runs_74_pngs(self) -> None:
        audit = self.summary["r64_milestone_focus_area_zoom_lever_iso_minss_flash_audit"]
        self.assertEqual(audit["round"], 64)
        self.assertEqual(audit["milestone"], 64)
        self.assertTrue(audit["power_of_two_grand_milestone"])
        self.assertGreaterEqual(audit["milestone295_qemu_rounds"], 37)
        self.assertGreaterEqual(audit["milestone295_qemu_runs"], 111)
        self.assertGreaterEqual(audit["milestone295_png_receipts"], 74)
        self.assertEqual(audit["total_runs"], 3)
        for k, v in audit.items():
            if isinstance(v, bool):
                self.assertTrue(v, f"Expected audit boolean {k} to be True")

    def test_20_round64_all_3_runs_present_with_kernel_4_9_337_and_zero_crashes_writes(self) -> None:
        runs = self.summary["runs"]
        self.assertEqual(list(runs.keys()), list(self.EXPECTED_RUN_KEYS))
        for rk, rv in runs.items():
            self.assertEqual(rv["round"], 64, rk)
            self.assertIn("4.9.337-scel+", rv["kernel_version"], rk)
            self.assertEqual(rv["nop_count"], 0, rk)
            self.assertEqual(rv["crashes"], 0, rk)
            self.assertEqual(rv["emmc_write_count"], 0, rk)
            self.assertGreater(rv["wall_elapsed_sec"], 0.0, rk)

    def test_21_round64_r64a_focus_14area_and_zoom_lever_verified(self) -> None:
        init_t = self.summary["runs"][
            "r64a_focus_area_zoom_iso_flash_big6_schinese"
        ]["r64_telemetry"]["wave50_init"]
        self.assertEqual(init_t["fx3_wave50_nodes_ok"], 1)
        self.assertEqual(init_t["uxc_tokens_ok"], 1)
        self.assertEqual(init_t["focus_area_14mode_ok"], 1)
        self.assertEqual(init_t["zoom_lever_xlrh1_fx6_ok"], 1)
        self.assertEqual(init_t["movie_tracking_fa_rc"], -16)
        self.assertEqual(init_t["fa_limit_lt2_rc"], -22)
        self.assertEqual(init_t["xlr_h1_zoom_rc"], -19)
        self.assertEqual(init_t["fx6_zoom99_rc"], -22)
        self.assertEqual(init_t["movie_tracking_focus_area_bypass_events"], 0)
        self.assertEqual(init_t["xlr_h1_zoom_spoof_events"], 0)

    def test_22_round64_r64a_iso_minss_cineei_and_mech_flash_videolight_verified(self) -> None:
        init_t = self.summary["runs"][
            "r64a_focus_area_zoom_iso_flash_big6_schinese"
        ]["r64_telemetry"]["wave50_init"]
        self.assertEqual(init_t["iso_limit_minss_cineei_ok"], 1)
        self.assertEqual(init_t["flash_still_videolight_ok"], 1)
        self.assertEqual(init_t["movie_iso_minss_rc"], -16)
        self.assertEqual(init_t["cineei_gain_rc"], -16)
        self.assertEqual(init_t["flash_movie_rc"], -16)
        self.assertEqual(init_t["flash_eshutter_rc"], -95)
        self.assertEqual(init_t["flash_sync320_rc"], -22)
        self.assertEqual(init_t["flash_dormant_rc"], -95)
        self.assertEqual(init_t["flash_250v_rc"], -75)
        self.assertEqual(init_t["videolight_950ma_rc"], -75)
        self.assertEqual(init_t["fx6_still_flash_rc"], -2)

    def test_23_round64_r64a_p2_cnflasha_and_slot1_ro_guards_intact(self) -> None:
        init_t = self.summary["runs"][
            "r64a_focus_area_zoom_iso_flash_big6_schinese"
        ]["r64_telemetry"]["wave50_init"]
        self.assertEqual(init_t["cine_ei_gain_override_events"], 0)
        self.assertEqual(init_t["still_flash_lockout_bypass_events"], 0)
        self.assertEqual(init_t["pmic_5v_overcurrent_events"], 0)
        self.assertEqual(init_t["slot1_wave50_write_events"], 0)
        self.assertEqual(init_t["passive_tx_bytes_emitted"], 0)
        self.assertEqual(init_t["e_nd_actuator_tx_count"], 0)
        self.assertEqual(init_t["p2_write_blocked_rc"], -30)
        self.assertEqual(init_t["p2_sha256_match"], 1)
        self.assertEqual(init_t["cnflasha_sha256_match"], 1)
        self.assertEqual(init_t["slot1_vault_sha256_match"], 1)
        self.assertEqual(init_t["cnflasha_writes"], 0)
        self.assertEqual(init_t["appfw_present"], 1)
        self.assertEqual(init_t["shim_present"], 1)
        self.assertEqual(init_t["emmc_write_count"], 0)
        self.assertEqual(init_t["r64_init_ok"], 1)

    def test_24_round64_r64a_stage_b_schinese_lang_telemetry_and_bridge(self) -> None:
        r64a_t = self.summary["runs"][
            "r64a_focus_area_zoom_iso_flash_big6_schinese"
        ]["r64_telemetry"]
        lt = r64a_t["lang_telemetry"]
        self.assertEqual(lt["lang"], "schinese")
        self.assertEqual(lt["bk4_lang_id"], "0x02cf019c")
        self.assertEqual(lt["bk4_lang_val"], "0x19")
        self.assertEqual(lt["lang_enum"], "0x2b45_CHINESE_SIMPLIFIED")
        self.assertEqual(lt["font_bank"], 23)
        self.assertEqual(lt["str_bank"], 19)
        self.assertEqual(lt["gpe_fb"], 0)
        self.assertEqual(lt["round64_milestone_37realhw_wave50_focus_zoom_iso_flash"], 1)
        self.assertEqual(lt["milestone_64th_round_37th_realhw_111th_live_74_pngs"], 1)
        self.assertEqual(lt["movie_tracking_focus_area_bypass_events"], 0)
        self.assertEqual(lt["xlr_h1_zoom_spoof_events"], 0)
        self.assertEqual(lt["cine_ei_gain_override_events"], 0)
        self.assertEqual(lt["still_flash_lockout_bypass_events"], 0)
        self.assertEqual(lt["pmic_5v_overcurrent_events"], 0)
        self.assertEqual(lt["slot1_wave50_write_events"], 0)
        self.assertEqual(lt["raw_firmware_bytes_leaked"], 0)

        sb = r64a_t["stage_b_bridge"]
        self.assertEqual(sb["round"], 64)
        self.assertEqual(sb["faithful"], 1)
        self.assertEqual(sb["nop_count"], 0)
        self.assertEqual(sb["focus_14area_still_afc_limit_ge2_reg"], 1)
        self.assertEqual(sb["zoom_lever_wt_xlrh1_zoomless_fx6_handle_1_8"], 1)
        self.assertEqual(sb["iso_range_limit_still_pa_minss_cineei"], 1)
        self.assertEqual(sb["still_mech_flash_250v_videolight_900ma_slot1"], 1)
        self.assertEqual(sb["milestone_64th_round_37th_realhw_111th_live_74_pngs"], 1)

    def test_25_round64_r64a_stage_b_4_pillar_bridges_verified(self) -> None:
        r64a_t = self.summary["runs"][
            "r64a_focus_area_zoom_iso_flash_big6_schinese"
        ]["r64_telemetry"]
        fb = r64a_t["focus_area_14mode_bridge"]
        self.assertEqual(fb["focus_14area_still_afc_split_ok"], 1)
        self.assertEqual(fb["focus_area_limit_ge2_color_circ_ok"], 1)
        self.assertEqual(fb["af_area_reg_fx6_3area_enoent_ok"], 1)
        self.assertEqual(fb["focus_area_14mode_ok"], 1)
        self.assertEqual(fb["movie_tracking_focus_area_bypass_events"], 0)
        self.assertEqual(fb["r64_bridge_ok"], 1)

        zb = r64a_t["zoom_lever_xlrh1_fx6_bridge"]
        self.assertEqual(zb["body_wt_zoom_lever_1st3_2nd8_ok"], 1)
        self.assertEqual(zb["xlr_h1_zoom_less_enodev_ok"], 1)
        self.assertEqual(zb["fx6_handle_zoom_1_8_pos_0_99_hold_ok"], 1)
        self.assertEqual(zb["zoom_lever_xlrh1_fx6_ok"], 1)
        self.assertEqual(zb["xlr_h1_zoom_spoof_events"], 0)
        self.assertEqual(zb["p2_setting_writes"], 0)

        ib = r64a_t["iso_limit_minss_cineei_bridge"]
        self.assertEqual(ib["iso_range_limit_manual_hlg_ok"], 1)
        self.assertEqual(ib["still_pa_iso_auto_min_ss_ok"], 1)
        self.assertEqual(ib["cine_ei_base_iso_pin_lock_ok"], 1)
        self.assertEqual(ib["iso_limit_minss_cineei_ok"], 1)
        self.assertEqual(ib["cine_ei_gain_override_events"], 0)

        fl = r64a_t["flash_still_videolight_bridge"]
        self.assertEqual(fl["still_flash_mech_sync_250v_ok"], 1)
        self.assertEqual(fl["dormant_adv_flash_wireless_guard_ok"], 1)
        self.assertEqual(fl["video_light_4mode_5v_900ma_slot1_erofs_ok"], 1)
        self.assertEqual(fl["flash_still_videolight_ok"], 1)
        self.assertEqual(fl["still_flash_lockout_bypass_events"], 0)
        self.assertEqual(fl["pmic_5v_overcurrent_events"], 0)
        self.assertEqual(fl["slot1_wave50_write_events"], 0)
        self.assertEqual(fl["cnflasha_writes"], 0)

    def test_26_round64_r64a_gpe0_readback_ge_300k_pixels_and_87_colors(self) -> None:
        r64a = self.summary["runs"][
            "r64a_focus_area_zoom_iso_flash_big6_schinese"
        ]
        self.assertEqual(r64a["target_presenter"], "31procam_big6_menu_home_presenter")
        self.assertEqual(r64a["target_sid"], "0x0a")
        self.assertGreaterEqual(r64a["total_threads_seen"], 150)
        gpe0 = r64a["gpe0_readback"]
        self.assertTrue(gpe0["present"])
        self.assertEqual(gpe0["bytes"], 2211840)
        self.assertEqual(gpe0["total_pixels"], 552960)
        self.assertGreaterEqual(gpe0["nonzero_pixels"], 300000)
        self.assertEqual(gpe0["nonzero_pixels"], 346686)
        self.assertEqual(gpe0["unique_colors"], 87)

    def test_27_round64_r64a_stage_b_manifest_13_hashes_and_r64_metadata(self) -> None:
        sb = self.summary["runs"][
            "r64a_focus_area_zoom_iso_flash_big6_schinese"
        ]["stage_b"]
        self.assertEqual(sb["manifest_count"], 13)
        self.assertEqual(len(sb["manifest_items"]), 13)
        for item in sb["manifest_items"]:
            self.assertEqual(len(item["sha256"]), 64)
        m = sb["r64"]
        self.assertEqual(m["r64_mode"], "focus_area_zoom_iso_flash_big6")
        self.assertTrue(m["milestone_64th_round_power_of_two"])
        self.assertTrue(m["milestone_37realhw_rounds"])
        self.assertGreaterEqual(m["realhw_round_ordinal"], 37)
        self.assertGreaterEqual(m["total_live_runs_at_completion"], 111)
        self.assertGreaterEqual(m["total_png_receipts_at_completion"], 74)
        self.assertEqual(m["focus_area_uxc_token"], "0xe0ad:Focus Area")
        self.assertEqual(m["focus_area_total_count"], 14)
        self.assertEqual(m["focus_area_non_tracking_count"], 7)
        self.assertEqual(m["focus_area_tracking_still_afc_only_count"], 7)
        self.assertEqual(m["focus_area_limit_min_checked"], 2)
        self.assertEqual(m["fx6_chaplin_focus_area_count"], 3)
        self.assertEqual(m["zoom_lever_speed_defaults"], {"1st": 3, "2nd": 8})
        self.assertFalse(m["xlr_h1_zoom_lever_present"])
        self.assertFalse(m["xlr_h1_zoom_hold_switch_present"])
        self.assertEqual(m["fx6_handle_zoom_speed_range"], [1, 8])
        self.assertEqual(m["fx6_zoom_position_display_range"], [0, 99])
        self.assertEqual(m["cine_ei_base_iso_pin_values"], [800, 12800])
        self.assertEqual(m["flash_mechanical_sync_max_denom"], 250)
        self.assertEqual(m["flash_center_pin_max_volts_exclusive"], 250)
        self.assertEqual(m["mi_shoe_5v_budget_ma"], 900)

    def test_28_round64_r64b_focus_area_tracking_limit_and_fx6_3area_guards_blocked(self) -> None:
        r64b_t = self.summary["runs"][
            "r64b_wave50_focus_zoom_iso_flash_guard"
        ]["r64_telemetry"]
        self.assertEqual(r64b_t["wave50_guard_rc"], 0)
        gd = r64b_t["wave50_guard"]
        self.assertEqual(gd["movie_tracking_wide_rc"], -16)
        self.assertEqual(gd["movie_tracking_spot_rc"], -16)
        self.assertEqual(gd["sq_tracking_zone_rc"], -16)
        self.assertEqual(gd["fa_limit_1_rc"], -22)
        self.assertEqual(gd["fa_limit_0_rc"], -22)
        self.assertEqual(gd["fx6_tracking_rc"], -2)
        self.assertEqual(gd["fx6_fa_limit_rc"], -2)
        self.assertEqual(gd["fx6_af_reg_rc"], -2)
        self.assertEqual(gd["movie_tracking_focus_area_bypass_events"], 0)

    def test_29_round64_r64b_xlr_h1_zoom_spoof_fx6_speed99_and_ciz_guards_blocked(self) -> None:
        gd = self.summary["runs"][
            "r64b_wave50_focus_zoom_iso_flash_guard"
        ]["r64_telemetry"]["wave50_guard"]
        self.assertEqual(gd["xlr_h1_zoom_spoof_rc"], -19)
        self.assertEqual(gd["xlr_h1_hold_spoof_rc"], -19)
        self.assertEqual(gd["fx6_speed_99_rc"], -22)
        self.assertEqual(gd["ciz_raw_rc"], -16)
        self.assertEqual(gd["dig_119p_rc"], -16)
        self.assertEqual(gd["xlr_h1_zoom_spoof_events"], 0)

    def test_30_round64_r64b_iso_minss_cineei_and_flash_videolight_guards_blocked(self) -> None:
        gd = self.summary["runs"][
            "r64b_wave50_focus_zoom_iso_flash_guard"
        ]["r64_telemetry"]["wave50_guard"]
        self.assertEqual(gd["minss_movie_rc"], -16)
        self.assertEqual(gd["minss_sq_rc"], -16)
        self.assertEqual(gd["minss_still_s_rc"], -16)
        self.assertEqual(gd["minss_still_m_rc"], -16)
        self.assertEqual(gd["cineei_manual_iso_rc"], -16)
        self.assertEqual(gd["cineei_auto_iso_rc"], -16)
        self.assertEqual(gd["cineei_autoslow_rc"], -16)
        self.assertEqual(gd["fx6_minss_rc"], -2)
        self.assertEqual(gd["hlg_iso_50_rc"], -22)
        self.assertEqual(gd["flash_movie_rc"], -16)
        self.assertEqual(gd["flash_sq_rc"], -16)
        self.assertEqual(gd["flash_eshutter_rc"], -95)
        self.assertEqual(gd["flash_silent_rc"], -95)
        self.assertEqual(gd["flash_sync320_rc"], -22)
        self.assertEqual(gd["flash_adv_dormant_rc"], -95)
        self.assertEqual(gd["flash_wireless_dormant_rc"], -95)
        self.assertEqual(gd["flash_250v_rc"], -75)
        self.assertEqual(gd["flash_revpol_rc"], -75)
        self.assertEqual(gd["videolight_950ma_rc"], -75)
        self.assertEqual(gd["fx6_still_flash_rc"], -2)
        self.assertEqual(gd["cine_ei_gain_override_events"], 0)
        self.assertEqual(gd["still_flash_lockout_bypass_events"], 0)
        self.assertEqual(gd["pmic_5v_overcurrent_events"], 0)

    def test_31_round64_r64b_slot1_wave50_erofs_and_zero_emmc_cnflasha_writes(self) -> None:
        gd = self.summary["runs"][
            "r64b_wave50_focus_zoom_iso_flash_guard"
        ]["r64_telemetry"]["wave50_guard"]
        self.assertEqual(gd["slot1_wave50_erofs_rc"], -30)
        self.assertEqual(gd["slot1_vault_ro_blocked_rc"], -30)
        self.assertEqual(gd["slot1_vault_sha256_match"], 1)
        self.assertEqual(gd["p2_write_blocked_rc"], -30)
        self.assertEqual(gd["cnflasha_ro_blocked_rc"], -30)
        self.assertEqual(gd["slot1_wave50_write_events"], 0)
        self.assertEqual(gd["passive_tx_bytes_emitted"], 0)
        self.assertEqual(gd["e_nd_actuator_tx_count"], 0)
        self.assertEqual(gd["cnflasha_writes"], 0)
        self.assertEqual(gd["emmc_write_count"], 0)
        self.assertEqual(gd["r64b_ok"], 1)

    def test_32_round64_r64c_clean_unmount_reset_tiers_and_xlrh1_fx6_hold_verified(self) -> None:
        ci = self.summary["runs"][
            "r64c_clean_unmount_wave50_reset_h0_h3_big6_schinese"
        ]["r64_telemetry"]["clean_unmount_wave50_h0_h3"]
        self.assertEqual(ci["stock_unmount_restored_ok"], 1)
        self.assertEqual(ci["camreset_preserves_wave50_survivors_ok"], 1)
        self.assertEqual(ci["initialize_restores_wave50_defaults_ok"], 1)
        self.assertEqual(ci["xlrh1_and_fx6_handle_hold_ok"], 1)
        self.assertEqual(ci["movie_tracking_focus_area_bypass_events"], 0)
        self.assertEqual(ci["xlr_h1_zoom_spoof_events"], 0)
        self.assertEqual(ci["cine_ei_gain_override_events"], 0)
        self.assertEqual(ci["still_flash_lockout_bypass_events"], 0)
        self.assertEqual(ci["pmic_5v_overcurrent_events"], 0)
        self.assertEqual(ci["slot1_wave50_write_events"], 0)

    def test_33_round64_r64c_dlopen_and_16_h0_eq_h3_idempotent_unmount(self) -> None:
        ci = self.summary["runs"][
            "r64c_clean_unmount_wave50_reset_h0_h3_big6_schinese"
        ]["r64_telemetry"]["clean_unmount_wave50_h0_h3"]
        self.assertEqual(ci["dlopen_ok"], 1)
        self.assertEqual(ci["surfaces_verified"], 16)
        self.assertEqual(ci["surfaces_h0_eq_h3"], 16)
        self.assertEqual(ci["drift_bits"], 0)
        self.assertEqual(ci["cnflasha_write_bytes"], 0)
        self.assertEqual(ci["emmc_write_bytes"], 0)
        self.assertEqual(ci["e_nd_actuator_tx_count"], 0)
        self.assertEqual(ci["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(ci["emmc_write_count"], 0)
        self.assertEqual(ci["r64c_ok"], 1)

    def test_34_round64_r64c_integrated_renders_valid_big6_gpe0_readback(self) -> None:
        r64c = self.summary["runs"][
            "r64c_clean_unmount_wave50_reset_h0_h3_big6_schinese"
        ]
        self.assertEqual(r64c["target_presenter"], "31procam_big6_menu_home_presenter")
        self.assertEqual(r64c["target_sid"], "0x0a")
        gpe0 = r64c["gpe0_readback"]
        self.assertTrue(gpe0["present"])
        self.assertEqual(gpe0["bytes"], 2211840)
        self.assertEqual(gpe0["total_pixels"], 552960)
        self.assertGreaterEqual(gpe0["nonzero_pixels"], 300000)
        self.assertEqual(gpe0["unique_colors"], 87)

    def test_35_round64_realhw_mechanisms_verified_7_blocks_match_run_telemetry(self) -> None:
        rm = self.summary["realhw_mechanisms_verified"]
        self.assertEqual(len(rm), 7)
        r64a = self.summary["runs"][
            "r64a_focus_area_zoom_iso_flash_big6_schinese"
        ]["r64_telemetry"]
        r64b = self.summary["runs"][
            "r64b_wave50_focus_zoom_iso_flash_guard"
        ]["r64_telemetry"]
        r64c = self.summary["runs"][
            "r64c_clean_unmount_wave50_reset_h0_h3_big6_schinese"
        ]["r64_telemetry"]
        self.assertEqual(rm["wave50_focus_zoom_iso_flash_init"], r64a["wave50_init"])
        self.assertEqual(rm["focus_area_14mode_limit_reg_stage_b_bridge"], r64a["focus_area_14mode_bridge"])
        self.assertEqual(rm["zoom_lever_xlrh1_fx6_stage_b_bridge"], r64a["zoom_lever_xlrh1_fx6_bridge"])
        self.assertEqual(rm["iso_limit_minss_cineei_stage_b_bridge"], r64a["iso_limit_minss_cineei_bridge"])
        self.assertEqual(rm["flash_still_videolight_pmic_stage_b_bridge"], r64a["flash_still_videolight_bridge"])
        self.assertEqual(rm["wave50_fail_closed_guard"], r64b["wave50_guard"])
        self.assertEqual(rm["clean_unmount_wave50_reset_and_16_h0_h3"], r64c["clean_unmount_wave50_h0_h3"])

    def test_36_round64_reset_tiers_survival_consistent_across_runs(self) -> None:
        r64a_t = self.summary["runs"][
            "r64a_focus_area_zoom_iso_flash_big6_schinese"
        ]["r64_telemetry"]
        r64c_ci = self.summary["runs"][
            "r64c_clean_unmount_wave50_reset_h0_h3_big6_schinese"
        ]["r64_telemetry"]["clean_unmount_wave50_h0_h3"]
        self.assertEqual(r64a_t["wave50_init"]["focus_area_14mode_ok"], 1)
        self.assertEqual(r64c_ci["stock_unmount_restored_ok"], 1)
        self.assertEqual(r64c_ci["camreset_preserves_wave50_survivors_ok"], 1)
        self.assertEqual(r64c_ci["initialize_restores_wave50_defaults_ok"], 1)

    def test_37_round64_cross_round_consistency_with_r63_slot1_ro_and_zero_leaks(self) -> None:
        self.assertEqual(self.r63_summary["round"], 63)
        r63b_gd = self.r63_summary["runs"][
            "r63b_still_raw_heif_colorspace_shutter_guard"
        ]["r63_telemetry"]["wave49_guard"]
        self.assertEqual(r63b_gd["slot1_vault_ro_blocked_rc"], -30)
        r64b_gd = self.summary["runs"][
            "r64b_wave50_focus_zoom_iso_flash_guard"
        ]["r64_telemetry"]["wave50_guard"]
        self.assertEqual(r64b_gd["slot1_vault_ro_blocked_rc"], -30)
        self.assertEqual(r64b_gd["slot1_wave50_erofs_rc"], -30)
        self.assertEqual(r64b_gd["slot1_vault_sha256_match"], 1)
        self.assertEqual(r64b_gd["movie_tracking_focus_area_bypass_events"], 0)
        self.assertEqual(r64b_gd["xlr_h1_zoom_spoof_events"], 0)

    def test_38_round64_cross_round_consistency_with_r62_and_r61_zero_emmc_writes(self) -> None:
        self.assertEqual(self.r62_summary["round"], 62)
        self.assertEqual(self.r61_summary["round"], 61)
        r62b_gd = self.r62_summary["runs"][
            "r62b_pp_log_wb_cineei_metering_guard"
        ]["r62_telemetry"]["wave48_guard"]
        self.assertEqual(r62b_gd["emmc_write_count"], 0)
        r61b_gd = self.r61_summary["runs"][
            "r61b_nouvc_hdmi1080_slot1_protect_nwreset_guard"
        ]["r61_telemetry"]["wave47_guard"]
        self.assertEqual(r61b_gd["emmc_write_count"], 0)
        r64b_gd = self.summary["runs"][
            "r64b_wave50_focus_zoom_iso_flash_guard"
        ]["r64_telemetry"]["wave50_guard"]
        self.assertEqual(r64b_gd["emmc_write_count"], 0)
        self.assertEqual(r64b_gd["cnflasha_writes"], 0)

    def test_39_round64_cross_round_consistency_with_r63_16_h0_eq_h3(self) -> None:
        r63c = self.r63_summary["runs"][
            "r63c_clean_unmount_still_reset_h0_h3_big6_schinese"
        ]["r63_telemetry"]["clean_unmount_still_h0_h3"]
        self.assertEqual(r63c["surfaces_h0_eq_h3"], 16)
        r64c = self.summary["runs"][
            "r64c_clean_unmount_wave50_reset_h0_h3_big6_schinese"
        ]["r64_telemetry"]["clean_unmount_wave50_h0_h3"]
        self.assertEqual(r64c["surfaces_h0_eq_h3"], 16)
        self.assertEqual(r64c["drift_bits"], 0)

    def test_40_round64_unexecuted_physical_camera_bench_boundaries_documented(self) -> None:
        bounds = self.summary["unexecuted_physical_camera_bench_boundaries"]
        self.assertEqual(len(bounds), 3)
        joined = " ".join(bounds)
        self.assertIn("Focus Area", joined)
        self.assertIn("Focus Area Limit", joined)
        self.assertIn("XLR-H1", joined)
        self.assertIn("Zoom Lever Speed", joined)
        self.assertIn("ISO Range Limit", joined)
        self.assertIn("ISO AUTO Min. SS", joined)
        self.assertIn("1/250", joined)
        self.assertIn("Video Light Mode", joined)

    def test_41_round64_alpha_png_exists_le_27467b_and_matches_summary_sha256(self) -> None:
        pe = self.summary["runs"][
            "r64a_focus_area_zoom_iso_flash_big6_schinese"
        ]["png_exports"]["alpha_png"]
        self.assertLessEqual(len(self.alpha_png_bytes), 27467)
        self.assertLess(len(self.alpha_png_bytes), 28672)
        self.assertLess(len(self.alpha_png_bytes), 51200)
        self.assertEqual(len(self.alpha_png_bytes), pe["bytes"])
        self.assertEqual(
            hashlib.sha256(self.alpha_png_bytes).hexdigest(), pe["sha256"]
        )

    def test_42_round64_composited_png_exists_le_27467b_and_matches_summary_sha256(self) -> None:
        pe = self.summary["runs"][
            "r64a_focus_area_zoom_iso_flash_big6_schinese"
        ]["png_exports"]["composited_png"]
        self.assertLessEqual(len(self.comp_png_bytes), 27467)
        self.assertLess(len(self.comp_png_bytes), 28672)
        self.assertLess(len(self.comp_png_bytes), 51200)
        self.assertEqual(len(self.comp_png_bytes), pe["bytes"])
        self.assertEqual(
            hashlib.sha256(self.comp_png_bytes).hexdigest(), pe["sha256"]
        )

    def test_43_round64_alpha_png_valid_1024x540_rgba_with_transparent_and_opaque_pixels(self) -> None:
        self.assertEqual(self.alpha_dims, (1024, 540))
        r64a_nz = self.summary["runs"][
            "r64a_focus_area_zoom_iso_flash_big6_schinese"
        ]["gpe0_readback"]["nonzero_pixels"]
        self.assertEqual(self.alpha_transparent, 552960 - r64a_nz)
        self.assertGreater(self.alpha_opaque, 300000)

    def test_44_round64_composited_png_valid_1024x540_rgba_100pct_opaque(self) -> None:
        self.assertEqual(self.comp_dims, (1024, 540))
        self.assertEqual(self.comp_opaque, 1024 * 540)

    def test_45_round64_report_readme_documents_all_3_runs_and_zero_host_leaks(self) -> None:
        for token in (
            "Round 64",
            "Wave-50",
            "r64a",
            "r64b",
            "r64c",
            "37/37",
            "111/111",
            "74/74",
            "Focus Area",
            "Focus Area Limit",
            "AF Area Registration",
            "Zoom Lever Speed",
            "XLR-H1",
            "Handle Zoom",
            "ISO Range Limit",
            "ISO AUTO Min. SS",
            "Cine EI",
            "Flash Mode",
            "Video Light Mode",
            "346,686",
            "r64a-focus-area-zoom-iso-flash-4ch-big6-schinese-alpha.png",
            "r64a-focus-area-zoom-iso-flash-4ch-big6-schinese-composited.png",
        ):
            self.assertIn(token, self.r64_readme)
        for forbidden in ("/Users/", "/private/tmp/", "/var/folders/", "work/_scratch/", ":87" + "68"):
            self.assertNotIn(forbidden, self.r64_readme)

    def test_46_round64_closure_readme_section_64_present_and_accurate(self) -> None:
        self.assertIn("## 64. Round 64", self.closure_readme)
        self.assertIn("37/37 Real-HW Rounds", self.closure_readme)
        self.assertIn("111/111 Total", self.closure_readme)
        self.assertIn("74/74 PNGs", self.closure_readme)
        self.assertIn(
            "2026-11-17-round64-milestone-focus-area-zoom-lever-iso-minss-flash-qemu",
            self.closure_readme,
        )

    def test_47_round64_37_plus_realhw_qemu_rounds_r28_to_r64_111_plus_runs_and_74_plus_pngs(self) -> None:
        png_total = 0
        rounds_found = 0
        for r in range(28, 65):
            matches = list((REPO_ROOT / "reports").glob(f"2026-??-??-round{r}-*"))
            self.assertEqual(len(matches), 1, f"Expected 1 report dir for Round {r}")
            pngs = list((matches[0] / "assets").glob("*.png"))
            self.assertGreaterEqual(len(pngs), 2, f"Expected >= 2 PNGs for Round {r}")
            for p in pngs:
                self.assertLess(p.stat().st_size, 51200, str(p))
            png_total += len(pngs)
            rounds_found += 1
        self.assertGreaterEqual(rounds_found, 37)
        self.assertGreaterEqual(png_total, 74)
        audit = self.summary["r64_milestone_focus_area_zoom_lever_iso_minss_flash_audit"]
        self.assertGreaterEqual(audit["milestone295_qemu_rounds"], 37)
        self.assertGreaterEqual(audit["milestone295_qemu_runs"], 111)
        self.assertGreaterEqual(audit["milestone295_png_receipts"], 74)

    def test_48_round64_dual_mode_clean_room_toggle_parity_on_summary(self) -> None:
        for clean_flag in ("0", "1"):
            with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                d = json.loads(self.summary_raw)
                self.assertEqual(d["round"], 64)
                self.assertEqual(
                    d["runs"][
                        "r64a_focus_area_zoom_iso_flash_big6_schinese"
                    ]["r64_telemetry"]["focus_area_14mode_bridge"]["focus_area_14mode_ok"],
                    1,
                )
                self.assertEqual(
                    d["runs"][
                        "r64b_wave50_focus_zoom_iso_flash_guard"
                    ]["r64_telemetry"]["wave50_guard"]["xlr_h1_zoom_spoof_rc"],
                    -19,
                )
                self.assertEqual(
                    d["runs"][
                        "r64c_clean_unmount_wave50_reset_h0_h3_big6_schinese"
                    ]["r64_telemetry"]["clean_unmount_wave50_h0_h3"][
                        "surfaces_h0_eq_h3"
                    ],
                    16,
                )

    def test_49_round64_r64a_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"][
            "r64a_focus_area_zoom_iso_flash_big6_schinese"
        ]["r64_telemetry"]["wave50_init"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_50_round64_r64b_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"][
            "r64b_wave50_focus_zoom_iso_flash_guard"
        ]["r64_telemetry"]["wave50_guard"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_51_round64_r64c_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"][
            "r64c_clean_unmount_wave50_reset_h0_h3_big6_schinese"
        ]["r64_telemetry"]["clean_unmount_wave50_h0_h3"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_52_round64_r64a_top_colors_transparent_plus_nonzero_equals_total_pixels(self) -> None:
        gpe = self.summary["runs"][
            "r64a_focus_area_zoom_iso_flash_big6_schinese"
        ]["gpe0_readback"]
        color_map = {row["argb"]: row["pixels"] for row in gpe["top_colors"]}
        self.assertIn("0x00000000", color_map)
        self.assertIn("0xff000000", color_map)
        self.assertEqual(color_map["0x00000000"] + gpe["nonzero_pixels"], gpe["total_pixels"])

    def test_53_round64_r64c_top_colors_transparent_plus_nonzero_equals_total_pixels(self) -> None:
        gpe = self.summary["runs"][
            "r64c_clean_unmount_wave50_reset_h0_h3_big6_schinese"
        ]["gpe0_readback"]
        color_map = {row["argb"]: row["pixels"] for row in gpe["top_colors"]}
        self.assertIn("0x00000000", color_map)
        self.assertEqual(color_map["0x00000000"] + gpe["nonzero_pixels"], gpe["total_pixels"])

    def test_54_round64_r64a_and_r64c_wall_elapsed_and_duration_budget_sanity(self) -> None:
        r64a = self.summary["runs"][
            "r64a_focus_area_zoom_iso_flash_big6_schinese"
        ]
        r64c = self.summary["runs"][
            "r64c_clean_unmount_wave50_reset_h0_h3_big6_schinese"
        ]
        ci_headroom = 15.0 if os.environ.get("GITHUB_ACTIONS") == "true" else 0.0
        max_wall = 240.0 + ci_headroom if os.environ.get("GITHUB_ACTIONS") == "true" else 120.0 + ci_headroom
        self.assertGreaterEqual(r64a["duration_budget_sec"], 70)
        self.assertLessEqual(r64a["duration_budget_sec"], 120)
        self.assertGreater(r64a["wall_elapsed_sec"], 50.0)
        self.assertLess(r64a["wall_elapsed_sec"], max_wall)
        self.assertGreaterEqual(r64c["duration_budget_sec"], 70)
        self.assertLessEqual(r64c["duration_budget_sec"], 120)
        self.assertGreater(r64c["wall_elapsed_sec"], 50.0)
        self.assertLess(r64c["wall_elapsed_sec"], max_wall)

    def test_55_round64_r64b_fast_early_exit_wall_elapsed_with_ci_headroom(self) -> None:
        r64b = self.summary["runs"][
            "r64b_wave50_focus_zoom_iso_flash_guard"
        ]
        ci_headroom = 15.0 if os.environ.get("GITHUB_ACTIONS") == "true" else 0.0
        max_b = 45.0 + ci_headroom if os.environ.get("GITHUB_ACTIONS") == "true" else 20.0 + ci_headroom
        self.assertEqual(r64b["duration_budget_sec"], 35)
        self.assertGreater(r64b["wall_elapsed_sec"], 1.0)
        self.assertLess(r64b["wall_elapsed_sec"], max_b)
        self.assertTrue(r64b["gpe0_readback"]["skipped_stock_fx3_mode"])

    def test_56_round64_faithful_invariants_preserved_across_all_3_runs(self) -> None:
        for rk, rv in self.summary["runs"].items():
            fi = rv["faithful_invariants"]
            self.assertEqual(fi["FX6_NATIVE_FAITHFUL"], 1, rk)
            self.assertEqual(fi["subst_color"], 0, rk)
            self.assertEqual(fi["subst_image"], 0, rk)
            self.assertEqual(fi["forced_render"], 0, rk)
            self.assertEqual(fi["skipped_node"], 0, rk)
            self.assertEqual(fi["lock_bypass"], 0, rk)

    def test_57_round64_all_3_runs_stage_b_manifest_count_13(self) -> None:
        for rk, rv in self.summary["runs"].items():
            self.assertEqual(rv["stage_b"]["manifest_count"], 13, rk)
            self.assertEqual(len(rv["stage_b"]["manifest_items"]), 13, rk)

    def test_58_round64_r64c_stage_b_r64_bridges_and_zero_leak_verified(self) -> None:
        r64c_t = self.summary["runs"][
            "r64c_clean_unmount_wave50_reset_h0_h3_big6_schinese"
        ]["r64_telemetry"]
        self.assertEqual(r64c_t["focus_area_14mode_bridge"]["focus_area_14mode_ok"], 1)
        self.assertEqual(r64c_t["zoom_lever_xlrh1_fx6_bridge"]["zoom_lever_xlrh1_fx6_ok"], 1)
        self.assertEqual(r64c_t["iso_limit_minss_cineei_bridge"]["iso_limit_minss_cineei_ok"], 1)
        self.assertEqual(r64c_t["flash_still_videolight_bridge"]["flash_still_videolight_ok"], 1)
        self.assertEqual(r64c_t["focus_area_14mode_bridge"]["movie_tracking_focus_area_bypass_events"], 0)
        self.assertEqual(r64c_t["zoom_lever_xlrh1_fx6_bridge"]["xlr_h1_zoom_spoof_events"], 0)
        self.assertEqual(r64c_t["iso_limit_minss_cineei_bridge"]["cine_ei_gain_override_events"], 0)
        self.assertEqual(r64c_t["flash_still_videolight_bridge"]["still_flash_lockout_bypass_events"], 0)
        self.assertEqual(r64c_t["stage_b_bridge"]["e_nd_actuator_tx_count"], 0)

    def test_59_round64_all_3_runs_prefix_counts_include_fx6_r64(self) -> None:
        r64a_pc = self.summary["runs"][
            "r64a_focus_area_zoom_iso_flash_big6_schinese"
        ]["prefix_counts"]
        r64b_pc = self.summary["runs"][
            "r64b_wave50_focus_zoom_iso_flash_guard"
        ]["prefix_counts"]
        r64c_pc = self.summary["runs"][
            "r64c_clean_unmount_wave50_reset_h0_h3_big6_schinese"
        ]["prefix_counts"]
        self.assertGreater(r64a_pc["FX6_R64_"], 10)
        self.assertEqual(r64b_pc["FX6_R64_"], 3)
        self.assertGreater(r64c_pc["FX6_R64_"], 10)

    def test_60_round64_r64_meta_invariants_across_all_3_runs(self) -> None:
        for rk, rv in self.summary["runs"].items():
            m = rv["stage_b"]["r64"]
            self.assertEqual(m["focus_area_total_count"], 14, rk)
            self.assertEqual(m["focus_area_non_tracking_count"], 7, rk)
            self.assertEqual(m["focus_area_tracking_still_afc_only_count"], 7, rk)
            self.assertEqual(m["focus_area_limit_min_checked"], 2, rk)
            self.assertTrue(m["focus_area_color_survives_camera_settings_reset"], rk)
            self.assertTrue(m["af_area_registration_survives_camera_settings_reset"], rk)
            self.assertTrue(m["af_area_registration_locks_operation_parts_off"], rk)
            self.assertEqual(m["fx6_chaplin_focus_area_count"], 3, rk)
            self.assertFalse(m["xlr_h1_zoom_lever_present"], rk)
            self.assertFalse(m["xlr_h1_zoom_hold_switch_present"], rk)
            self.assertEqual(m["xlr_h1_zoom_spoof_errno"], -19, rk)
            self.assertTrue(m["zoom_range_survives_camera_settings_reset"], rk)
            self.assertEqual(m["fx6_handle_zoom_speed_range"], [1, 8], rk)
            self.assertEqual(m["fx6_zoom_position_display_range"], [0, 99], rk)
            self.assertTrue(m["fx6_handle_hold_rec_button_only_keeps_zoom"], rk)
            self.assertTrue(m["iso_range_limit_manual_iso_only"], rk)
            self.assertTrue(m["iso_range_limit_survives_camera_settings_reset"], rk)
            self.assertEqual(m["hlg_still_on_iso_floor"], 100, rk)
            self.assertTrue(m["iso_auto_min_ss_still_pa_only"], rk)
            self.assertEqual(m["cine_ei_base_iso_pin_values"], [800, 12800], rk)
            self.assertEqual(len(m["flash_mode_5_options"]), 5, rk)
            self.assertEqual(m["flash_mechanical_sync_max_denom"], 250, rk)
            self.assertEqual(m["flash_center_pin_max_volts_exclusive"], 250, rk)
            self.assertEqual(len(m["flash_dormant_enums_rejected"]), 2, rk)
            self.assertTrue(m["exp_comp_set_survives_camera_settings_reset"], rk)
            self.assertTrue(m["external_flash_set_survives_camera_settings_reset"], rk)
            self.assertEqual(len(m["video_light_4_modes"]), 4, rk)
            self.assertEqual(m["mi_shoe_5v_budget_ma"], 900, rk)
            self.assertTrue(m["slot1_tier0_vault_erofs"], rk)
            self.assertEqual(m["movie_tracking_focus_area_bypass_events"], 0, rk)
            self.assertEqual(m["xlr_h1_zoom_spoof_events"], 0, rk)
            self.assertEqual(m["cine_ei_gain_override_events"], 0, rk)
            self.assertEqual(m["still_flash_lockout_bypass_events"], 0, rk)
            self.assertEqual(m["pmic_5v_overcurrent_events"], 0, rk)
            self.assertEqual(m["slot1_wave50_write_events"], 0, rk)
            self.assertEqual(m["e_nd_actuator_tx_count"], 0, rk)
            self.assertEqual(m["raw_firmware_bytes_leaked"], 0, rk)

    def test_61_round64_sanitize_helper_redacts_host_paths_and_reserved_port(self) -> None:
        dirty = {
            "run_id": "test-run",
            "lang": "schinese",
            "r64_mode": "focus_area_zoom_iso_flash_big6",
            "kernel_version": "Linux version 4.9.337-scel+",
            "kernel_bin": "/Users/fake/secret/kernel.bin",
            "dtb_bin": "/Users/fake/secret/guest.dtb",
            "build": {"tmp_build": "/private/tmp/build-123"},
            "stage_b": {"r64": {"r64_mode": "focus_area_zoom_iso_flash_big6"}},
            "r64_telemetry": {
                "wave50_init": {"r64_init_ok": 1},
                "wave50_guard": {"r64b_ok": 1},
                "clean_unmount_wave50_h0_h3": {"r64c_ok": 1, "surfaces_h0_eq_h3": 16},
            },
            "gpe0_readback": {"nonzero_pixels": 346686},
            "png_exports": {
                "alpha_png": {
                    "path": "/Users/kafu/repo/reports/2026-11-17-round64-milestone-focus-area-zoom-lever-iso-minss-flash-qemu/assets/a.png"
                }
            },
            "prefix_counts": {"FX6_R64_": 10},
        }
        sanitized = self.runner.sanitize_round64_summary(dirty, dirty, dirty)
        raw = json.dumps(sanitized)
        self.assertNotIn("/Users/", raw)
        self.assertNotIn("/private/tmp/", raw)
        self.assertNotIn("kernel_bin", raw)
        self.assertNotIn("dtb_bin", raw)
        self.assertIn(
            "reports/2026-11-17-round64-milestone-focus-area-zoom-lever-iso-minss-flash-qemu/assets/a.png",
            raw,
        )

    def test_62_round64_no_stray_temp_files_or_reserved_port_in_repo(self) -> None:
        for bad_name in ("tmp", "scratch", ".worktrees"):
            self.assertFalse((REPO_ROOT / bad_name).exists(), bad_name)
        reserved_port = "87" + "68"
        self.assertNotIn(reserved_port, self.summary_raw)
        self.assertNotIn(reserved_port, self.r64_readme)

    def test_63_round64_runner_escapes_percent_in_argparse_help_and_portable_tools(self) -> None:
        self.assertIn("ArgumentParser", self.runner_src)
        self.assertNotIn("/usr/" + "bin/python3", self.runner_src)
        self.assertIn('shutil.which("zig")', self.runner_src)
        self.assertIn("FX6_SCRATCH_DIR", self.runner_src)

    def test_64_round64_test_suite_contains_at_least_66_unit_tests(self) -> None:
        methods = [m for m in dir(self) if m.startswith("test_")]
        self.assertGreaterEqual(len(methods), 66)

    def test_65_round64_dual_mode_env_flags_preserve_zero_emmc_and_clean_room_parity(self) -> None:
        for env_overrides in (
            {},
            {"FX3_CLEAN_ROOM_TEST": "1"},
            {"FX3_FX6_FORCE_CLEAN_ROOM": "1"},
        ):
            with mock.patch.dict(os.environ, env_overrides, clear=False):
                parsed = self.runner.extract_milestones(
                    "Linux version 4.9.337-scel+\n"
                    "FX6_R64_WAVE50_INIT focus_area_14mode_ok=1 zoom_lever_xlrh1_fx6_ok=1 "
                    "iso_limit_minss_cineei_ok=1 flash_still_videolight_ok=1 r64_init_ok=1\n"
                )
                self.assertEqual(parsed["r64_telemetry"]["wave50_init"]["r64_init_ok"], 1)

    def test_66_round64_argparse_percent_safe_help_and_no_hardcoded_python3(self) -> None:
        for line in self.runner_src.splitlines():
            if "help=" in line and "%" in line:
                stripped = line.replace("%%", "")
                self.assertNotIn("%", stripped, f"Unescaped '%' in argparse help: {line}")
        test_src = pathlib.Path(__file__).read_text(encoding="utf-8")
        forbidden_py = "/usr/" + "bin/python3"
        self.assertNotIn(forbidden_py, self.runner_src)
        self.assertNotIn(forbidden_py, test_src)


if __name__ == "__main__":
    unittest.main()
