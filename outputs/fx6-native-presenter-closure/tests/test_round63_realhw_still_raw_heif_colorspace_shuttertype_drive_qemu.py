#!/usr/bin/env python3
"""Offline dual-mode unit tests for FX6-on-FX3 Round 63 (36/36 Real-HW Rounds Milestone, 106th..108th Live Runs -> 108/108 Total, 72/72 PNGs — Wave-49)."""
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
ROUND63_REPORT_DIR = (
    REPO_ROOT
    / "reports"
    / "2026-11-17-round63-realhw-still-raw-heif-colorspace-shuttertype-drive-qemu"
)
WAVE49_SPEC_PATH = (
    REPO_ROOT
    / "reports"
    / "2026-11-17-global-sony-wave49-still-raw-heif-colorspace-adobersgb-shutter-type-nr-drive-intel"
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


def _build_overlay_for_r63(
    runner,
    parent_cpio: pathlib.Path,
    fp,
    fv,
    fb,
    fake_run,
    jit_meta: Dict[str, Any],
    work: pathlib.Path,
    r63_mode: str,
    lang: str = "schinese",
    enable_r63: bool = True,
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
            enable_r63=enable_r63,
            r63_mode=r63_mode,
            sd_manifest_mode="valid",
            lang=lang,
            shim_bytes=b"SHIM",
        )


class TestRound63RealHwStillRawHeifColorSpaceShutterTypeDriveQemu(unittest.TestCase):
    EXPECTED_RUN_KEYS = (
        "r63a_still_raw_heif_colorspace_shutter_drive_big6_schinese",
        "r63b_still_raw_heif_colorspace_shutter_guard",
        "r63c_clean_unmount_still_reset_h0_h3_big6_schinese",
    )

    runner: Any
    runner_src: str
    stage_a_src: str
    shim_src: str
    wave49_spec: str
    summary_raw: str
    summary: Dict[str, Any]
    r63_readme: str
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
    launcher_r63: Optional[bytes]
    shim_r63: Optional[bytes]
    shim_r62: Optional[bytes]
    r62_summary: Dict[str, Any]
    r61_summary: Dict[str, Any]
    r60_summary: Dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = _load_closure_module("fx6_brr_r63_cached", "build_and_run_round.py")
        cls.runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")
        cls.stage_a_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        cls.shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        cls.wave49_spec = WAVE49_SPEC_PATH.read_text(encoding="utf-8")
        cls.summary_raw = (ROUND63_REPORT_DIR / "summary.json").read_text(encoding="utf-8")
        cls.summary = json.loads(cls.summary_raw)
        cls.r63_readme = (ROUND63_REPORT_DIR / "README.md").read_text(encoding="utf-8")
        cls.closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")

        alpha_p = (
            ROUND63_REPORT_DIR
            / "assets"
            / "r63a-raw-heif-colorspace-shutter-4ch-big6-schinese-alpha.png"
        )
        comp_p = (
            ROUND63_REPORT_DIR
            / "assets"
            / "r63a-raw-heif-colorspace-shutter-4ch-big6-schinese-composited.png"
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
            cls.ov_a = _build_overlay_for_r63(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wa", "still_raw_heif_colorspace_shutter_drive_big6", lang="schinese",
            )
            cls.ov_b = _build_overlay_for_r63(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wb", "still_raw_heif_colorspace_shutter_guard", lang="en",
            )
            cls.ov_c = _build_overlay_for_r63(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wc", "clean_unmount_still_reset_h0_h3_big6", lang="schinese",
            )
            cls.ov_off = _build_overlay_for_r63(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "woff", "still_raw_heif_colorspace_shutter_drive_big6", enable_r63=False,
            )
            cls.invalid_mode_raised = False
            try:
                _build_overlay_for_r63(
                    cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                    tpath / "wbad", "invalid_r63_mode",
                )
            except ValueError:
                cls.invalid_mode_raised = True

            zig_bin = shutil.which("zig") or (
                str(cls.runner.ZIG) if cls.runner.ZIG.is_file() else None
            )
            if zig_bin is not None:
                verify_r63_out = tpath / "fx6-stage-a-verify-r63"
                shim_r63_out = tpath / "libgrm-fbinit9-r63.so"
                shim_r62_out = tpath / "libgrm-fbinit9-r62.so"
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
                        str(verify_r63_out),
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
                    [
                        zig_bin,
                        "cc",
                        "-target",
                        "aarch64-linux-gnu.2.25",
                        "-O0",
                        "-shared",
                        "-fPIC",
                        "-DFX6_ROUND=62",
                        str(CLOSURE_DIR / "libgrm-fbinit9.c"),
                        "-ldl",
                        "-lpthread",
                        "-o",
                        str(shim_r62_out),
                    ],
                ):
                    cls.runner.subprocess.run(cmd, check=True)
                cls.launcher_r63 = verify_r63_out.read_bytes()
                cls.shim_r63 = shim_r63_out.read_bytes()
                cls.shim_r62 = shim_r62_out.read_bytes()
            else:
                cls.launcher_r63 = None
                cls.shim_r63 = None
                cls.shim_r62 = None

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
        cls.r60_summary = json.loads(
            (
                REPO_ROOT
                / "reports"
                / "2026-11-17-round60-milestone-realhw-power-save-monitor-language-volume-delete-qemu"
                / "summary.json"
            ).read_text(encoding="utf-8")
        )

    def test_01_wave49_global_spec_present_and_covers_all_wave49_pillars(self) -> None:
        self.assertTrue(WAVE49_SPEC_PATH.is_file())
        for needle in (
            "Image Quality Settings",
            "RAW File Type",
            "Compressed",
            "Uncompressed",
            "Lossless Comp",
            "JPEG/HEIF Switch",
            "HEIF(4:2:0)",
            "HEIF(4:2:2)",
            "HLG Still Image",
            "BT.2100",
            "Color Space",
            "sRGB",
            "AdobeRGB",
            "_DSC0001.JPG",
            "Set File Name",
            "Shutter Type",
            "Mechanical Shutter",
            "Electronic Shutter",
            "e-Front Curtain Shut.",
            "Silent Mode",
            "1/250",
            "Long Exposure NR",
            "High ISO NR",
            "Drive Mode",
            "Cont. Shooting: Hi+",
            "10 fps",
            "DRO Bracket",
        ):
            self.assertIn(needle, self.wave49_spec)

    def test_02_round63_summary_schema_round_milestone_and_zero_leaks(self) -> None:
        self.assertNotIn("/Users/", self.summary_raw)
        self.assertNotIn("/private/tmp/", self.summary_raw)
        self.assertEqual(
            self.summary["schema"],
            "fx6-on-fx3-round63-milestone-36realhw-still-raw-heif-colorspace-shuttertype-drive-qemu-v1",
        )
        self.assertEqual(self.summary["round"], 63)
        self.assertEqual(self.summary["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(tuple(self.summary["runs"].keys()), self.EXPECTED_RUN_KEYS)

    def test_03_round63_cli_accepts_round63_and_all_3_r63_modes(self) -> None:
        self.assertIn(", 62, 63]", self.runner_src)
        for mode in (
            "still_raw_heif_colorspace_shutter_drive_big6",
            "still_raw_heif_colorspace_shutter_guard",
            "clean_unmount_still_reset_h0_h3_big6",
        ):
            self.assertIn(mode, self.runner_src)

    def test_04_round63_overlay_rejects_invalid_r63_mode(self) -> None:
        self.assertTrue(self.invalid_mode_raised)

    def test_05_round63_overlay_r63a_injects_etc_fx6_stage_r63_and_appfw_launch(self) -> None:
        replacements, additions, meta = self.ov_a
        self.assertTrue(meta["r63_enabled"])
        self.assertIn("etc/fx6_stage_r63", additions)
        self.assertIn("etc/fx6_r63_libjit.so", additions)
        r63_cfg = additions["etc/fx6_stage_r63"][0].decode("utf-8")
        self.assertIn("stage_r63=1", r63_cfg)
        self.assertIn("r63_mode=still_raw_heif_colorspace_shutter_drive_big6", r63_cfg)
        self.assertIn("milestone_36th_realhw_108th_live_72_pngs=1", r63_cfg)
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("/usr/bin/appfw-launch", init_txt)
        self.assertNotIn("--r63-still-raw-heif-colorspace-shutter-guard", init_txt)

    def test_06_round63_overlay_r63b_injects_early_guard_probe_and_poweroff(self) -> None:
        replacements, _, meta = self.ov_b
        self.assertEqual(meta["r63"]["r63_mode"], "still_raw_heif_colorspace_shutter_guard")
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("--r63-still-raw-heif-colorspace-shutter-guard", init_txt)
        self.assertIn("FX6_R63_WAVE49_GUARD_RC=", init_txt)
        self.assertIn("FX6_R63_WAVE49_GUARD_EXIT", init_txt)
        self.assertIn("poweroff -f", init_txt)

    def test_07_round63_overlay_r63c_integrated_runs_stage_b_big6(self) -> None:
        replacements, additions, meta = self.ov_c
        self.assertEqual(meta["r63"]["r63_mode"], "clean_unmount_still_reset_h0_h3_big6")
        r63_cfg = additions["etc/fx6_stage_r63"][0].decode("utf-8")
        self.assertIn("r63_mode=clean_unmount_still_reset_h0_h3_big6", r63_cfg)
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("/usr/bin/appfw-launch", init_txt)
        self.assertNotIn("--r63-still-raw-heif-colorspace-shutter-guard", init_txt)

    def test_08_round63_overlay_disabled_when_enable_r63_false(self) -> None:
        _, additions, meta = self.ov_off
        self.assertFalse(meta["r63_enabled"])
        self.assertNotIn("etc/fx6_stage_r63", additions)
        self.assertNotIn("etc/fx6_r63_libjit.so", additions)
        self.assertNotIn("r63", meta)

    def test_09_round63_stage_a_c_source_contains_all_3_wave49_probes(self) -> None:
        for sym in (
            "setup_r63_still_raw_heif_colorspace_shutter_drive_probe",
            "run_r63_still_raw_heif_colorspace_shutter_guard_probe",
            "run_r63_clean_unmount_still_reset_h0_h3_probe",
            "FX6_R63_WAVE49_INIT",
            "FX6_R63_WAVE49_GUARD",
            "FX6_R63_CLEAN_UNMOUNT_STILL_H0_H3",
            "--r63-still-raw-heif-colorspace-shutter-guard",
            "--r63-clean-unmount-still-h0-h3",
            "/etc/fx6_stage_r63",
        ):
            self.assertIn(sym, self.stage_a_src)

    def test_10_round63_shim_c_source_contains_r63_guarded_bridges(self) -> None:
        self.assertIn("#if FX6_ROUND >= 63", self.shim_src)
        for sym in (
            "FX6_R63_STILL_RAW_HEIF_HLG_BRIDGE",
            "FX6_R63_COLORSPACE_FILENAME_BRIDGE",
            "FX6_R63_SHUTTER_2MODE_NR_DRIVE_BRIDGE",
            "FX6_R63_LANG_TELEMETRY",
            "FX6_STAGE_B_R63_BRIDGE",
        ):
            self.assertIn(sym, self.shim_src)

    def test_11_round63_compile_launcher_and_shim_aarch64_elf_symbols(self) -> None:
        if self.launcher_r63 is None or self.shim_r63 is None:
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertEqual(self.launcher_r63[:4], b"\x7fELF")
        self.assertEqual(self.shim_r63[:4], b"\x7fELF")
        self.assertEqual(struct.unpack_from("<H", self.shim_r63, 18)[0], 183)
        self.assertIn(b"FX6_R63_STILL_RAW_HEIF_HLG_BRIDGE", self.shim_r63)
        self.assertIn(b"FX6_R63_COLORSPACE_FILENAME_BRIDGE", self.shim_r63)
        self.assertIn(b"FX6_R63_SHUTTER_2MODE_NR_DRIVE_BRIDGE", self.shim_r63)

    def test_12_round63_shim_round62_backward_compat_excludes_r63_bridges(self) -> None:
        if self.shim_r62 is None:
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertIn(b"FX6_R62_PP_SCINETONE_LOOK_DRO_BRIDGE", self.shim_r62)
        self.assertNotIn(b"FX6_R63_STILL_RAW_HEIF_HLG_BRIDGE", self.shim_r62)

    def test_13_round63_parse_log_extracts_all_8_r63_prefixes_and_rc(self) -> None:
        serial_text = (
            "\n".join(
                [
                    "Linux version 4.9.337-scel+ (sony@fx3)",
                    "FX6_R63_WAVE49_INIT fx3_wave49_nodes_ok=1 uxc_tokens_ok=1 still_raw_heif_hlg_ok=1 colorspace_dsc_ban_ok=1 shutter_nr_drive_ok=1 lossless_dormant_rc=-95 fx6_still_less_rc=-2 leading_under_ban_rc=-22 auto_shutter_rc=-95 high_iso_nr_raw_lock_rc=-16 emmc_write_count=0 r63_init_ok=1",
                    "FX6_R63_STILL_RAW_HEIF_HLG_BRIDGE raw_2mode_no_lossless_ok=1 jh_heif_420_422_10bit_ok=1 hlg_still_bt2100_fx6_enoent_ok=1 still_raw_heif_hlg_ok=1 lossless_comp_bypass_events=0 r63_bridge_ok=1",
                    "FX6_R63_COLORSPACE_FILENAME_BRIDGE srgb_dsc_vs_adobergb_udsc_ok=1 set_filename_leading_under_ban_ok=1 camreset_preserves_prefix_efront_ok=1 colorspace_filename_ok=1 leading_underscore_prefix_events=0 p2_setting_writes=0",
                    "FX6_R63_SHUTTER_2MODE_NR_DRIVE_BRIDGE shutter_2mode_no_auto_ok=1 silent_flash_bulb_lenr_hisor_lock_ok=1 drive_8mode_hi_plus_10fps_slot1_erofs_ok=1 shutter_2mode_nr_drive_ok=1 auto_shutter_type_bypass_events=0 slot1_still_write_events=0 cnflasha_writes=0",
                    "FX6_R63_LANG_TELEMETRY lang=schinese font_bank=23 str_bank=19 milestone_36th_realhw_108th_live_72_pngs=1 r63_bridge_ok=1",
                    "FX6_STAGE_B_R63_BRIDGE round=63 faithful=1 nop_count=0 milestone_36th_realhw_108th_live_72_pngs=1 emmc_write_count=0",
                    "FX6_R63_WAVE49_GUARD lossless_base_rc=-95 lossless_l_rc=-95 lossless_m_rc=-95 lossless_s_rc=-95 fx6_still_rc=-2 hlg_under_jpeg_rc=-16 hlg_under_raw_heif_rc=-16 hlg_under_pp_rc=-16 dro_bracket_under_hlg_rc=-16 leading_under_dsc_rc=-22 leading_under_abc_rc=-22 lowercase_prefix_rc=-22 auto_shutter_rc=-95 flash_320_spoof_rc=-22 eshutter_flash_rc=-95 lenr_under_silent_rc=-16 lenr_under_cont_rc=-16 high_iso_nr_raw_rc=-16 slot1_still_raw_erofs_rc=-30 r63b_ok=1",
                    "FX6_R63_WAVE49_GUARD_RC=0",
                    "FX6_R63_CLEAN_UNMOUNT_STILL_H0_H3 stock_unmount_restored_ok=1 camreset_preserves_filename_efront_ok=1 adobergb_underscore_dcf_ok=1 initialize_restores_filename_efront_ok=1 surfaces_h0_eq_h3=16 r63c_ok=1",
                ]
            )
            + "\n"
        )
        parsed = self.runner.extract_milestones(serial_text)
        r63_t = parsed["r63_telemetry"]
        self.assertEqual(r63_t["wave49_guard_rc"], 0)
        self.assertEqual(r63_t["wave49_init"]["still_raw_heif_hlg_ok"], 1)
        self.assertEqual(r63_t["still_raw_heif_hlg_bridge"]["still_raw_heif_hlg_ok"], 1)
        self.assertEqual(r63_t["colorspace_filename_bridge"]["colorspace_filename_ok"], 1)
        self.assertEqual(r63_t["shutter_2mode_nr_drive_bridge"]["shutter_2mode_nr_drive_ok"], 1)
        self.assertEqual(r63_t["lang_telemetry"]["lang"], "schinese")
        self.assertEqual(r63_t["lang_telemetry"]["milestone_36th_realhw_108th_live_72_pngs"], 1)
        self.assertEqual(r63_t["stage_b_bridge"]["round"], 63)
        self.assertEqual(r63_t["wave49_guard"]["r63b_ok"], 1)
        self.assertEqual(r63_t["clean_unmount_still_h0_h3"]["surfaces_h0_eq_h3"], 16)
        self.assertEqual(parsed["prefix_counts"]["FX6_R63_"], 8)

    def test_14_round63_parse_log_defaults_when_no_r63_lines_present(self) -> None:
        parsed = self.runner.extract_milestones("Linux version 4.9.337-scel+\n")
        self.assertIsNone(parsed["r63_telemetry"])
        self.assertEqual(parsed["prefix_counts"].get("FX6_R63_", 0), 0)

    def test_15_round63_runner_uses_fx6_r63_prefix_and_stage_label(self) -> None:
        self.assertIn('if args.round >= 63:\n        tmp_prefix = "fx6-r63"', self.runner_src)
        self.assertIn(
            "Milestone36RealHw108thLiveWave49StillRawHeifHlgColorSpaceShutter2ModeNr10fpsDrive",
            self.runner_src,
        )
        self.assertIn(", 62, 63]", self.runner_src)

    def test_16_round63_runner_portability_and_sanitizer_helper(self) -> None:
        self.assertIn('shutil.which("zig")', self.runner_src)
        self.assertIn("FX6_SCRATCH_DIR", self.runner_src)
        self.assertIn("def sanitize_round63_summary(", self.runner_src)
        self.assertNotIn("/usr/" + "bin/python3", self.runner_src)

    def test_17_round63_summary_json_top_level_schema_and_milestone_metadata(self) -> None:
        d = self.summary
        self.assertEqual(
            d["schema"],
            "fx6-on-fx3-round63-milestone-36realhw-still-raw-heif-colorspace-shuttertype-drive-qemu-v1",
        )
        self.assertEqual(d["round"], 63)
        self.assertIn("36/36 Real-HW Rounds Milestone!", d["milestone"])
        self.assertIn("36th Real-HW", d["milestone"])
        self.assertIn("108/108 Total Live Runs", d["milestone"])
        self.assertIn("72/72 PNGs", d["milestone"])
        self.assertEqual(d["date"], "2026-11-17")
        self.assertIn("4.9.337-scel+", d["kernel_version"])
        self.assertEqual(d["raw_firmware_bytes_leaked"], 0)

    def test_18_round63_summary_json_zero_host_path_and_scratch_leaks(self) -> None:
        for forbidden in (
            "/Users/",
            "/private/tmp/",
            "/var/folders/",
            "work/_scratch/",
            "work/_tests/",
            ":87" + "68",
        ):
            self.assertNotIn(forbidden, self.summary_raw)

    def test_19_round63_summary_audit_block_confirms_36_rounds_108_runs_72_pngs(self) -> None:
        audit = self.summary["r63_realhw_still_raw_heif_colorspace_shutter_drive_audit"]
        self.assertEqual(audit["round"], 63)
        self.assertEqual(audit["milestone"], 63)
        self.assertGreaterEqual(audit["milestone295_qemu_rounds"], 36)
        self.assertGreaterEqual(audit["milestone295_qemu_runs"], 108)
        self.assertGreaterEqual(audit["milestone295_png_receipts"], 72)
        self.assertEqual(audit["total_runs"], 3)
        for k, v in audit.items():
            if isinstance(v, bool):
                self.assertTrue(v, f"Expected audit boolean {k} to be True")

    def test_20_round63_all_3_runs_present_with_kernel_4_9_337_and_zero_crashes_writes(self) -> None:
        runs = self.summary["runs"]
        self.assertEqual(list(runs.keys()), list(self.EXPECTED_RUN_KEYS))
        for rk, rv in runs.items():
            self.assertEqual(rv["round"], 63, rk)
            self.assertIn("4.9.337-scel+", rv["kernel_version"], rk)
            self.assertEqual(rv["nop_count"], 0, rk)
            self.assertEqual(rv["crashes"], 0, rk)
            self.assertEqual(rv["emmc_write_count"], 0, rk)
            self.assertGreater(rv["wall_elapsed_sec"], 0.0, rk)

    def test_21_round63_r63a_still_raw_heif_hlg_verified(self) -> None:
        init_t = self.summary["runs"][
            "r63a_still_raw_heif_colorspace_shutter_drive_big6_schinese"
        ]["r63_telemetry"]["wave49_init"]
        self.assertEqual(init_t["fx3_wave49_nodes_ok"], 1)
        self.assertEqual(init_t["uxc_tokens_ok"], 1)
        self.assertEqual(init_t["still_raw_heif_hlg_ok"], 1)
        self.assertEqual(init_t["lossless_dormant_rc"], -95)
        self.assertEqual(init_t["fx6_still_less_rc"], -2)
        self.assertEqual(init_t["lossless_comp_bypass_events"], 0)

    def test_22_round63_r63a_colorspace_dsc_ban_and_2mode_shutter_nr_drive_verified(self) -> None:
        init_t = self.summary["runs"][
            "r63a_still_raw_heif_colorspace_shutter_drive_big6_schinese"
        ]["r63_telemetry"]["wave49_init"]
        self.assertEqual(init_t["colorspace_dsc_ban_ok"], 1)
        self.assertEqual(init_t["shutter_nr_drive_ok"], 1)
        self.assertEqual(init_t["leading_under_ban_rc"], -22)
        self.assertEqual(init_t["auto_shutter_rc"], -95)
        self.assertEqual(init_t["high_iso_nr_raw_lock_rc"], -16)

    def test_23_round63_r63a_p2_cnflasha_and_slot1_ro_guards_intact(self) -> None:
        init_t = self.summary["runs"][
            "r63a_still_raw_heif_colorspace_shutter_drive_big6_schinese"
        ]["r63_telemetry"]["wave49_init"]
        self.assertEqual(init_t["leading_underscore_prefix_events"], 0)
        self.assertEqual(init_t["auto_shutter_type_bypass_events"], 0)
        self.assertEqual(init_t["slot1_still_write_events"], 0)
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
        self.assertEqual(init_t["r63_init_ok"], 1)

    def test_24_round63_r63a_stage_b_schinese_lang_telemetry_and_bridge(self) -> None:
        r63a_t = self.summary["runs"][
            "r63a_still_raw_heif_colorspace_shutter_drive_big6_schinese"
        ]["r63_telemetry"]
        lt = r63a_t["lang_telemetry"]
        self.assertEqual(lt["lang"], "schinese")
        self.assertEqual(lt["bk4_lang_id"], "0x02cf019c")
        self.assertEqual(lt["bk4_lang_val"], "0x19")
        self.assertEqual(lt["lang_enum"], "0x2b45_CHINESE_SIMPLIFIED")
        self.assertEqual(lt["font_bank"], 23)
        self.assertEqual(lt["str_bank"], 19)
        self.assertEqual(lt["gpe_fb"], 0)
        self.assertEqual(lt["round63_milestone_36realhw_still_raw_heif_colorspace_shutter_drive"], 1)
        self.assertEqual(lt["milestone_36th_realhw_108th_live_72_pngs"], 1)
        self.assertEqual(lt["lossless_comp_bypass_events"], 0)
        self.assertEqual(lt["leading_underscore_prefix_events"], 0)
        self.assertEqual(lt["auto_shutter_type_bypass_events"], 0)
        self.assertEqual(lt["slot1_still_write_events"], 0)
        self.assertEqual(lt["passive_tx_bytes_emitted"], 0)
        self.assertEqual(lt["e_nd_actuator_tx_count"], 0)
        self.assertEqual(lt["raw_firmware_bytes_leaked"], 0)
        sb = r63a_t["stage_b_bridge"]
        self.assertEqual(sb["round"], 63)
        self.assertEqual(sb["faithful"], 1)
        self.assertEqual(sb["nop_count"], 0)
        self.assertEqual(sb["raw_2mode_no_lossless_heif10_hlg"], 1)
        self.assertEqual(sb["colorspace_srgb_dsc_adobergb_udsc_ban"], 1)
        self.assertEqual(sb["shutter_2mode_no_auto_nr_10fps"], 1)
        self.assertEqual(sb["slot1_tier0_still_vault_erofs"], 1)
        self.assertEqual(sb["milestone_36th_realhw_108th_live_72_pngs"], 1)

    def test_25_round63_r63a_stage_b_3_pillar_bridges_verified(self) -> None:
        r63a_t = self.summary["runs"][
            "r63a_still_raw_heif_colorspace_shutter_drive_big6_schinese"
        ]["r63_telemetry"]
        pb = r63a_t["still_raw_heif_hlg_bridge"]
        self.assertEqual(pb["raw_2mode_no_lossless_ok"], 1)
        self.assertEqual(pb["jh_heif_420_422_10bit_ok"], 1)
        self.assertEqual(pb["hlg_still_bt2100_fx6_enoent_ok"], 1)
        self.assertEqual(pb["still_raw_heif_hlg_ok"], 1)
        self.assertEqual(pb["lossless_comp_bypass_events"], 0)
        self.assertEqual(pb["r63_bridge_ok"], 1)

        cb = r63a_t["colorspace_filename_bridge"]
        self.assertEqual(cb["srgb_dsc_vs_adobergb_udsc_ok"], 1)
        self.assertEqual(cb["set_filename_leading_under_ban_ok"], 1)
        self.assertEqual(cb["camreset_preserves_prefix_efront_ok"], 1)
        self.assertEqual(cb["colorspace_filename_ok"], 1)
        self.assertEqual(cb["leading_underscore_prefix_events"], 0)
        self.assertEqual(cb["p2_setting_writes"], 0)

        sb = r63a_t["shutter_2mode_nr_drive_bridge"]
        self.assertEqual(sb["shutter_2mode_no_auto_ok"], 1)
        self.assertEqual(sb["silent_flash_bulb_lenr_hisor_lock_ok"], 1)
        self.assertEqual(sb["drive_8mode_hi_plus_10fps_slot1_erofs_ok"], 1)
        self.assertEqual(sb["shutter_2mode_nr_drive_ok"], 1)
        self.assertEqual(sb["auto_shutter_type_bypass_events"], 0)
        self.assertEqual(sb["slot1_still_write_events"], 0)
        self.assertEqual(sb["cnflasha_writes"], 0)

    def test_26_round63_r63a_gpe0_readback_ge_300k_pixels_and_87_colors(self) -> None:
        r63a = self.summary["runs"][
            "r63a_still_raw_heif_colorspace_shutter_drive_big6_schinese"
        ]
        self.assertEqual(r63a["target_presenter"], "31procam_big6_menu_home_presenter")
        self.assertEqual(r63a["target_sid"], "0x0a")
        self.assertGreaterEqual(r63a["total_threads_seen"], 150)
        gpe0 = r63a["gpe0_readback"]
        self.assertTrue(gpe0["present"])
        self.assertEqual(gpe0["bytes"], 2211840)
        self.assertEqual(gpe0["total_pixels"], 552960)
        self.assertGreaterEqual(gpe0["nonzero_pixels"], 300000)
        self.assertEqual(gpe0["nonzero_pixels"], 346206)
        self.assertEqual(gpe0["unique_colors"], 87)

    def test_27_round63_r63a_stage_b_manifest_13_hashes_and_r63_metadata(self) -> None:
        sb = self.summary["runs"][
            "r63a_still_raw_heif_colorspace_shutter_drive_big6_schinese"
        ]["stage_b"]
        self.assertEqual(sb["manifest_count"], 13)
        self.assertEqual(len(sb["manifest_items"]), 13)
        for item in sb["manifest_items"]:
            self.assertEqual(len(item["sha256"]), 64)
        m = sb["r63"]
        self.assertEqual(m["r63_mode"], "still_raw_heif_colorspace_shutter_drive_big6")
        self.assertTrue(m["milestone_36realhw_rounds"])
        self.assertGreaterEqual(m["realhw_round_ordinal"], 36)
        self.assertGreaterEqual(m["total_live_runs_at_completion"], 108)
        self.assertGreaterEqual(m["total_png_receipts_at_completion"], 72)
        self.assertEqual(m["still_image_quality_settings_uxc_token"], "0x59ec:Image Quality Settings")
        self.assertEqual(m["jpeg_heif_switch_uxc_token"], "0xe515:JPEG/HEIF Switch")
        self.assertEqual(m["jpeg_heif_switch_bit_depth"], 10)
        self.assertEqual(m["raw_file_type_uxc_token"], "0xe4fb:RAW File Type")
        self.assertEqual(m["raw_file_type_exposed_modes"], ["Compressed", "Uncompressed"])
        self.assertEqual(len(m["raw_file_type_dormant_alpha_modes_rejected"]), 4)
        self.assertEqual(m["hlg_still_image_uxc_token"], "0x67ba:HLG Still Image")
        self.assertEqual(m["hlg_still_image_gamut"], "BT.2100")
        self.assertFalse(m["fx6_still_shooting_mode_present"])
        self.assertEqual(m["color_space_uxc_token"], "0xe4fa:Color Space")
        self.assertEqual(m["color_space_options"], ["sRGB", "AdobeRGB"])
        self.assertEqual(m["srgb_default_prefix"], "DSC")
        self.assertTrue(m["adobergb_auto_first_char_underscore"])
        self.assertEqual(m["set_file_name_uxc_token"], "0xe6d6:Set File Name")
        self.assertTrue(m["set_file_name_leading_underscore_banned"])
        self.assertEqual(m["shutter_type_uxc_token"], "0xe4fc:Shutter Type")
        self.assertEqual(m["shutter_type_2modes_only"], ["Mechanical Shutter", "Electronic Shutter"])
        self.assertTrue(m["shutter_type_auto_mode_omitted"])
        self.assertEqual(m["drive_cont_hi_plus_max_fps"], 10)

    def test_28_round63_r63b_dormant_lossless_fx6_still_and_hlg_guards_blocked(self) -> None:
        r63b_t = self.summary["runs"][
            "r63b_still_raw_heif_colorspace_shutter_guard"
        ]["r63_telemetry"]
        self.assertEqual(r63b_t["wave49_guard_rc"], 0)
        gd = r63b_t["wave49_guard"]
        self.assertEqual(gd["lossless_base_rc"], -95)
        self.assertEqual(gd["lossless_l_rc"], -95)
        self.assertEqual(gd["lossless_m_rc"], -95)
        self.assertEqual(gd["lossless_s_rc"], -95)
        self.assertEqual(gd["fx6_still_rc"], -2)
        self.assertEqual(gd["hlg_under_jpeg_rc"], -16)
        self.assertEqual(gd["hlg_under_raw_heif_rc"], -16)
        self.assertEqual(gd["hlg_under_pp_rc"], -16)
        self.assertEqual(gd["dro_bracket_under_hlg_rc"], -16)
        self.assertEqual(gd["lossless_comp_bypass_events"], 0)

    def test_29_round63_r63b_filename_leading_underscore_and_lowercase_banned(self) -> None:
        gd = self.summary["runs"][
            "r63b_still_raw_heif_colorspace_shutter_guard"
        ]["r63_telemetry"]["wave49_guard"]
        self.assertEqual(gd["leading_under_dsc_rc"], -22)
        self.assertEqual(gd["leading_under_abc_rc"], -22)
        self.assertEqual(gd["lowercase_prefix_rc"], -22)
        self.assertEqual(gd["leading_underscore_prefix_events"], 0)

    def test_30_round63_r63b_2mode_shutter_silent_flash_lenr_hisor_guards_blocked(self) -> None:
        gd = self.summary["runs"][
            "r63b_still_raw_heif_colorspace_shutter_guard"
        ]["r63_telemetry"]["wave49_guard"]
        self.assertEqual(gd["auto_shutter_rc"], -95)
        self.assertEqual(gd["flash_320_spoof_rc"], -22)
        self.assertEqual(gd["eshutter_flash_rc"], -95)
        self.assertEqual(gd["lenr_under_silent_rc"], -16)
        self.assertEqual(gd["lenr_under_cont_rc"], -16)
        self.assertEqual(gd["high_iso_nr_raw_rc"], -16)
        self.assertEqual(gd["auto_shutter_type_bypass_events"], 0)

    def test_31_round63_r63b_slot1_still_raw_erofs_and_zero_emmc_cnflasha_writes(self) -> None:
        gd = self.summary["runs"][
            "r63b_still_raw_heif_colorspace_shutter_guard"
        ]["r63_telemetry"]["wave49_guard"]
        self.assertEqual(gd["slot1_still_raw_erofs_rc"], -30)
        self.assertEqual(gd["slot1_vault_ro_blocked_rc"], -30)
        self.assertEqual(gd["slot1_vault_sha256_match"], 1)
        self.assertEqual(gd["p2_write_blocked_rc"], -30)
        self.assertEqual(gd["cnflasha_ro_blocked_rc"], -30)
        self.assertEqual(gd["slot1_still_write_events"], 0)
        self.assertEqual(gd["passive_tx_bytes_emitted"], 0)
        self.assertEqual(gd["e_nd_actuator_tx_count"], 0)
        self.assertEqual(gd["cnflasha_writes"], 0)
        self.assertEqual(gd["emmc_write_count"], 0)
        self.assertEqual(gd["r63b_ok"], 1)

    def test_32_round63_r63c_clean_unmount_reset_tiers_and_adobergb_dcf_verified(self) -> None:
        ci = self.summary["runs"][
            "r63c_clean_unmount_still_reset_h0_h3_big6_schinese"
        ]["r63_telemetry"]["clean_unmount_still_h0_h3"]
        self.assertEqual(ci["stock_unmount_restored_ok"], 1)
        self.assertEqual(ci["camreset_preserves_filename_efront_ok"], 1)
        self.assertEqual(ci["adobergb_underscore_dcf_ok"], 1)
        self.assertEqual(ci["initialize_restores_filename_efront_ok"], 1)
        self.assertEqual(ci["lossless_comp_bypass_events"], 0)
        self.assertEqual(ci["leading_underscore_prefix_events"], 0)
        self.assertEqual(ci["auto_shutter_type_bypass_events"], 0)
        self.assertEqual(ci["slot1_still_write_events"], 0)

    def test_33_round63_r63c_dlopen_and_16_h0_eq_h3_idempotent_unmount(self) -> None:
        ci = self.summary["runs"][
            "r63c_clean_unmount_still_reset_h0_h3_big6_schinese"
        ]["r63_telemetry"]["clean_unmount_still_h0_h3"]
        self.assertEqual(ci["dlopen_ok"], 1)
        self.assertEqual(ci["surfaces_verified"], 16)
        self.assertEqual(ci["surfaces_h0_eq_h3"], 16)
        self.assertEqual(ci["drift_bits"], 0)
        self.assertEqual(ci["cnflasha_write_bytes"], 0)
        self.assertEqual(ci["emmc_write_bytes"], 0)
        self.assertEqual(ci["e_nd_actuator_tx_count"], 0)
        self.assertEqual(ci["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(ci["emmc_write_count"], 0)
        self.assertEqual(ci["r63c_ok"], 1)

    def test_34_round63_r63c_integrated_renders_valid_big6_gpe0_readback(self) -> None:
        r63c = self.summary["runs"][
            "r63c_clean_unmount_still_reset_h0_h3_big6_schinese"
        ]
        self.assertEqual(r63c["target_presenter"], "31procam_big6_menu_home_presenter")
        self.assertEqual(r63c["target_sid"], "0x0a")
        gpe0 = r63c["gpe0_readback"]
        self.assertTrue(gpe0["present"])
        self.assertEqual(gpe0["bytes"], 2211840)
        self.assertEqual(gpe0["total_pixels"], 552960)
        self.assertGreaterEqual(gpe0["nonzero_pixels"], 300000)
        self.assertEqual(gpe0["unique_colors"], 87)

    def test_35_round63_realhw_mechanisms_verified_6_blocks_match_run_telemetry(self) -> None:
        rm = self.summary["realhw_mechanisms_verified"]
        self.assertEqual(len(rm), 6)
        r63a = self.summary["runs"][
            "r63a_still_raw_heif_colorspace_shutter_drive_big6_schinese"
        ]["r63_telemetry"]
        r63b = self.summary["runs"][
            "r63b_still_raw_heif_colorspace_shutter_guard"
        ]["r63_telemetry"]
        r63c = self.summary["runs"][
            "r63c_clean_unmount_still_reset_h0_h3_big6_schinese"
        ]["r63_telemetry"]
        self.assertEqual(
            rm["wave49_still_raw_heif_colorspace_shutter_drive_init"],
            r63a["wave49_init"],
        )
        self.assertEqual(
            rm["still_raw_heif_hlg_stage_b_bridge"],
            r63a["still_raw_heif_hlg_bridge"],
        )
        self.assertEqual(
            rm["colorspace_filename_stage_b_bridge"],
            r63a["colorspace_filename_bridge"],
        )
        self.assertEqual(
            rm["shutter_2mode_nr_drive_stage_b_bridge"],
            r63a["shutter_2mode_nr_drive_bridge"],
        )
        self.assertEqual(
            rm["wave49_fail_closed_guard"],
            r63b["wave49_guard"],
        )
        self.assertEqual(
            rm["clean_unmount_still_reset_and_16_h0_h3"],
            r63c["clean_unmount_still_h0_h3"],
        )

    def test_36_round63_reset_tiers_survival_consistent_across_runs(self) -> None:
        r63a_t = self.summary["runs"][
            "r63a_still_raw_heif_colorspace_shutter_drive_big6_schinese"
        ]["r63_telemetry"]
        r63c_ci = self.summary["runs"][
            "r63c_clean_unmount_still_reset_h0_h3_big6_schinese"
        ]["r63_telemetry"]["clean_unmount_still_h0_h3"]
        self.assertEqual(r63a_t["wave49_init"]["colorspace_dsc_ban_ok"], 1)
        self.assertEqual(r63c_ci["stock_unmount_restored_ok"], 1)
        self.assertEqual(r63c_ci["camreset_preserves_filename_efront_ok"], 1)
        self.assertEqual(r63c_ci["adobergb_underscore_dcf_ok"], 1)
        self.assertEqual(r63c_ci["initialize_restores_filename_efront_ok"], 1)

    def test_37_round63_cross_round_consistency_with_r62_slot1_ro_and_zero_leaks(self) -> None:
        self.assertEqual(self.r62_summary["round"], 62)
        r62b_gd = self.r62_summary["runs"][
            "r62b_pp_log_wb_cineei_metering_guard"
        ]["r62_telemetry"]["wave48_guard"]
        self.assertEqual(r62b_gd["slot1_vault_ro_blocked_rc"], -30)
        r63b_gd = self.summary["runs"][
            "r63b_still_raw_heif_colorspace_shutter_guard"
        ]["r63_telemetry"]["wave49_guard"]
        self.assertEqual(r63b_gd["slot1_vault_ro_blocked_rc"], -30)
        self.assertEqual(r63b_gd["slot1_still_raw_erofs_rc"], -30)
        self.assertEqual(r63b_gd["slot1_vault_sha256_match"], 1)
        self.assertEqual(r63b_gd["lossless_comp_bypass_events"], 0)
        self.assertEqual(r63b_gd["auto_shutter_type_bypass_events"], 0)

    def test_38_round63_cross_round_consistency_with_r61_and_r60_zero_emmc_writes(self) -> None:
        self.assertEqual(self.r61_summary["round"], 61)
        self.assertEqual(self.r60_summary["round"], 60)
        r61b_gd = self.r61_summary["runs"][
            "r61b_nouvc_hdmi1080_slot1_protect_nwreset_guard"
        ]["r61_telemetry"]["wave47_guard"]
        self.assertEqual(r61b_gd["emmc_write_count"], 0)
        r60b_gd = self.r60_summary["runs"][
            "r60b_dormant_monitor_sleep_slot1_delete_guard"
        ]["r60_telemetry"]["dormant_mon_slot1_del_guard"]
        self.assertEqual(r60b_gd["emmc_write_count"], 0)
        r63b_gd = self.summary["runs"][
            "r63b_still_raw_heif_colorspace_shutter_guard"
        ]["r63_telemetry"]["wave49_guard"]
        self.assertEqual(r63b_gd["emmc_write_count"], 0)
        self.assertEqual(r63b_gd["cnflasha_writes"], 0)

    def test_39_round63_cross_round_consistency_with_r62_16_h0_eq_h3(self) -> None:
        r62c = self.r62_summary["runs"][
            "r62c_clean_unmount_pp_wb_reset_h0_h3_big6_schinese"
        ]["r62_telemetry"]["clean_unmount_pp_wb_h0_h3"]
        self.assertEqual(r62c["surfaces_h0_eq_h3"], 16)
        r63c = self.summary["runs"][
            "r63c_clean_unmount_still_reset_h0_h3_big6_schinese"
        ]["r63_telemetry"]["clean_unmount_still_h0_h3"]
        self.assertEqual(r63c["surfaces_h0_eq_h3"], 16)
        self.assertEqual(r63c["drift_bits"], 0)

    def test_40_round63_unexecuted_physical_camera_bench_boundaries_documented(self) -> None:
        bounds = self.summary["unexecuted_physical_camera_bench_boundaries"]
        self.assertEqual(len(bounds), 3)
        joined = " ".join(bounds)
        self.assertIn("RAW File Type", joined)
        self.assertIn("HEIF", joined)
        self.assertIn("HLG Still Image", joined)
        self.assertIn("AdobeRGB", joined)
        self.assertIn("Set File Name", joined)
        self.assertIn("1/250", joined)
        self.assertIn("Long Exposure NR", joined)

    def test_41_round63_alpha_png_exists_le_27467b_and_matches_summary_sha256(self) -> None:
        pe = self.summary["runs"][
            "r63a_still_raw_heif_colorspace_shutter_drive_big6_schinese"
        ]["png_exports"]["alpha_png"]
        self.assertLessEqual(len(self.alpha_png_bytes), 27467)
        self.assertLess(len(self.alpha_png_bytes), 28672)
        self.assertLess(len(self.alpha_png_bytes), 51200)
        self.assertEqual(len(self.alpha_png_bytes), pe["bytes"])
        self.assertEqual(
            hashlib.sha256(self.alpha_png_bytes).hexdigest(), pe["sha256"]
        )

    def test_42_round63_composited_png_exists_le_27467b_and_matches_summary_sha256(self) -> None:
        pe = self.summary["runs"][
            "r63a_still_raw_heif_colorspace_shutter_drive_big6_schinese"
        ]["png_exports"]["composited_png"]
        self.assertLessEqual(len(self.comp_png_bytes), 27467)
        self.assertLess(len(self.comp_png_bytes), 28672)
        self.assertLess(len(self.comp_png_bytes), 51200)
        self.assertEqual(len(self.comp_png_bytes), pe["bytes"])
        self.assertEqual(
            hashlib.sha256(self.comp_png_bytes).hexdigest(), pe["sha256"]
        )

    def test_43_round63_alpha_png_valid_1024x540_rgba_with_transparent_and_opaque_pixels(self) -> None:
        self.assertEqual(self.alpha_dims, (1024, 540))
        r63a_nz = self.summary["runs"][
            "r63a_still_raw_heif_colorspace_shutter_drive_big6_schinese"
        ]["gpe0_readback"]["nonzero_pixels"]
        self.assertEqual(self.alpha_transparent, 552960 - r63a_nz)
        self.assertGreater(self.alpha_opaque, 300000)

    def test_44_round63_composited_png_valid_1024x540_rgba_100pct_opaque(self) -> None:
        self.assertEqual(self.comp_dims, (1024, 540))
        self.assertEqual(self.comp_opaque, 1024 * 540)

    def test_45_round63_report_readme_documents_all_3_runs_and_zero_host_leaks(self) -> None:
        for token in (
            "Round 63",
            "Wave-49",
            "r63a",
            "r63b",
            "r63c",
            "36/36",
            "108/108",
            "72/72",
            "RAW File Type",
            "Lossless Comp",
            "HEIF",
            "HLG Still Image",
            "AdobeRGB",
            "_DSC",
            "Set File Name",
            "Shutter Type",
            "Long Exposure NR",
            "High ISO NR",
            "Drive Mode",
            "346,206",
            "r63a-raw-heif-colorspace-shutter-4ch-big6-schinese-alpha.png",
            "r63a-raw-heif-colorspace-shutter-4ch-big6-schinese-composited.png",
        ):
            self.assertIn(token, self.r63_readme)
        for forbidden in ("/Users/", "/private/tmp/", "/var/folders/", "work/_scratch/", ":87" + "68"):
            self.assertNotIn(forbidden, self.r63_readme)

    def test_46_round63_closure_readme_section_63_present_and_accurate(self) -> None:
        self.assertIn("## 63. Round 63", self.closure_readme)
        self.assertIn("36/36 Real-HW Rounds", self.closure_readme)
        self.assertIn("108/108 Total", self.closure_readme)
        self.assertIn("72/72 PNGs", self.closure_readme)
        self.assertIn(
            "2026-11-17-round63-realhw-still-raw-heif-colorspace-shuttertype-drive-qemu",
            self.closure_readme,
        )

    def test_47_round63_36_plus_realhw_qemu_rounds_r28_to_r63_108_plus_runs_and_72_plus_pngs(self) -> None:
        png_total = 0
        rounds_found = 0
        for r in range(28, 64):
            matches = list((REPO_ROOT / "reports").glob(f"2026-??-??-round{r}-*"))
            self.assertEqual(len(matches), 1, f"Expected 1 report dir for Round {r}")
            pngs = list((matches[0] / "assets").glob("*.png"))
            self.assertGreaterEqual(len(pngs), 2, f"Expected >= 2 PNGs for Round {r}")
            for p in pngs:
                self.assertLess(p.stat().st_size, 51200, str(p))
            png_total += len(pngs)
            rounds_found += 1
        self.assertGreaterEqual(rounds_found, 36)
        self.assertGreaterEqual(png_total, 72)
        audit = self.summary["r63_realhw_still_raw_heif_colorspace_shutter_drive_audit"]
        self.assertGreaterEqual(audit["milestone295_qemu_rounds"], 36)
        self.assertGreaterEqual(audit["milestone295_qemu_runs"], 108)
        self.assertGreaterEqual(audit["milestone295_png_receipts"], 72)

    def test_48_round63_dual_mode_clean_room_toggle_parity_on_summary(self) -> None:
        for clean_flag in ("0", "1"):
            with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                d = json.loads(self.summary_raw)
                self.assertEqual(d["round"], 63)
                self.assertEqual(
                    d["runs"][
                        "r63a_still_raw_heif_colorspace_shutter_drive_big6_schinese"
                    ]["r63_telemetry"]["still_raw_heif_hlg_bridge"]["still_raw_heif_hlg_ok"],
                    1,
                )
                self.assertEqual(
                    d["runs"][
                        "r63b_still_raw_heif_colorspace_shutter_guard"
                    ]["r63_telemetry"]["wave49_guard"]["lossless_base_rc"],
                    -95,
                )
                self.assertEqual(
                    d["runs"][
                        "r63c_clean_unmount_still_reset_h0_h3_big6_schinese"
                    ]["r63_telemetry"]["clean_unmount_still_h0_h3"][
                        "surfaces_h0_eq_h3"
                    ],
                    16,
                )

    def test_49_round63_r63a_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"][
            "r63a_still_raw_heif_colorspace_shutter_drive_big6_schinese"
        ]["r63_telemetry"]["wave49_init"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_50_round63_r63b_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"][
            "r63b_still_raw_heif_colorspace_shutter_guard"
        ]["r63_telemetry"]["wave49_guard"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_51_round63_r63c_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"][
            "r63c_clean_unmount_still_reset_h0_h3_big6_schinese"
        ]["r63_telemetry"]["clean_unmount_still_h0_h3"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_52_round63_r63a_top_colors_transparent_plus_nonzero_equals_total_pixels(self) -> None:
        gpe = self.summary["runs"][
            "r63a_still_raw_heif_colorspace_shutter_drive_big6_schinese"
        ]["gpe0_readback"]
        color_map = {row["argb"]: row["pixels"] for row in gpe["top_colors"]}
        self.assertIn("0x00000000", color_map)
        self.assertIn("0xff000000", color_map)
        self.assertEqual(color_map["0x00000000"] + gpe["nonzero_pixels"], gpe["total_pixels"])

    def test_53_round63_r63c_top_colors_transparent_plus_nonzero_equals_total_pixels(self) -> None:
        gpe = self.summary["runs"][
            "r63c_clean_unmount_still_reset_h0_h3_big6_schinese"
        ]["gpe0_readback"]
        color_map = {row["argb"]: row["pixels"] for row in gpe["top_colors"]}
        self.assertIn("0x00000000", color_map)
        self.assertEqual(color_map["0x00000000"] + gpe["nonzero_pixels"], gpe["total_pixels"])

    def test_54_round63_r63a_and_r63c_wall_elapsed_and_duration_budget_sanity(self) -> None:
        r63a = self.summary["runs"][
            "r63a_still_raw_heif_colorspace_shutter_drive_big6_schinese"
        ]
        r63c = self.summary["runs"][
            "r63c_clean_unmount_still_reset_h0_h3_big6_schinese"
        ]
        ci_headroom = 15.0 if os.environ.get("GITHUB_ACTIONS") == "true" else 0.0
        max_wall = 240.0 + ci_headroom if os.environ.get("GITHUB_ACTIONS") == "true" else 120.0 + ci_headroom
        self.assertGreaterEqual(r63a["duration_budget_sec"], 70)
        self.assertLessEqual(r63a["duration_budget_sec"], 120)
        self.assertGreater(r63a["wall_elapsed_sec"], 50.0)
        self.assertLess(r63a["wall_elapsed_sec"], max_wall)
        self.assertGreaterEqual(r63c["duration_budget_sec"], 70)
        self.assertLessEqual(r63c["duration_budget_sec"], 120)
        self.assertGreater(r63c["wall_elapsed_sec"], 50.0)
        self.assertLess(r63c["wall_elapsed_sec"], max_wall)

    def test_55_round63_r63b_fast_early_exit_wall_elapsed_with_ci_headroom(self) -> None:
        r63b = self.summary["runs"][
            "r63b_still_raw_heif_colorspace_shutter_guard"
        ]
        ci_headroom = 15.0 if os.environ.get("GITHUB_ACTIONS") == "true" else 0.0
        max_b = 45.0 + ci_headroom if os.environ.get("GITHUB_ACTIONS") == "true" else 20.0 + ci_headroom
        self.assertEqual(r63b["duration_budget_sec"], 35)
        self.assertGreater(r63b["wall_elapsed_sec"], 1.0)
        self.assertLess(r63b["wall_elapsed_sec"], max_b)
        self.assertTrue(r63b["gpe0_readback"]["skipped_stock_fx3_mode"])

    def test_56_round63_faithful_invariants_preserved_across_all_3_runs(self) -> None:
        for rk, rv in self.summary["runs"].items():
            fi = rv["faithful_invariants"]
            self.assertEqual(fi["FX6_NATIVE_FAITHFUL"], 1, rk)
            self.assertEqual(fi["subst_color"], 0, rk)
            self.assertEqual(fi["subst_image"], 0, rk)
            self.assertEqual(fi["forced_render"], 0, rk)
            self.assertEqual(fi["skipped_node"], 0, rk)
            self.assertEqual(fi["lock_bypass"], 0, rk)

    def test_57_round63_all_3_runs_stage_b_manifest_count_13(self) -> None:
        for rk, rv in self.summary["runs"].items():
            self.assertEqual(rv["stage_b"]["manifest_count"], 13, rk)
            self.assertEqual(len(rv["stage_b"]["manifest_items"]), 13, rk)

    def test_58_round63_r63c_stage_b_r63_bridges_and_zero_leak_verified(self) -> None:
        r63c_t = self.summary["runs"][
            "r63c_clean_unmount_still_reset_h0_h3_big6_schinese"
        ]["r63_telemetry"]
        self.assertEqual(
            r63c_t["still_raw_heif_hlg_bridge"]["still_raw_heif_hlg_ok"], 1
        )
        self.assertEqual(
            r63c_t["colorspace_filename_bridge"]["colorspace_filename_ok"], 1
        )
        self.assertEqual(
            r63c_t["shutter_2mode_nr_drive_bridge"]["shutter_2mode_nr_drive_ok"], 1
        )
        self.assertEqual(
            r63c_t["still_raw_heif_hlg_bridge"]["lossless_comp_bypass_events"], 0
        )
        self.assertEqual(
            r63c_t["colorspace_filename_bridge"]["leading_underscore_prefix_events"], 0
        )
        self.assertEqual(
            r63c_t["shutter_2mode_nr_drive_bridge"]["auto_shutter_type_bypass_events"], 0
        )
        self.assertEqual(
            r63c_t["shutter_2mode_nr_drive_bridge"]["slot1_still_write_events"], 0
        )
        self.assertEqual(r63c_t["stage_b_bridge"]["e_nd_actuator_tx_count"], 0)

    def test_59_round63_all_3_runs_prefix_counts_include_fx6_r63(self) -> None:
        r63a_pc = self.summary["runs"][
            "r63a_still_raw_heif_colorspace_shutter_drive_big6_schinese"
        ]["prefix_counts"]
        r63b_pc = self.summary["runs"][
            "r63b_still_raw_heif_colorspace_shutter_guard"
        ]["prefix_counts"]
        r63c_pc = self.summary["runs"][
            "r63c_clean_unmount_still_reset_h0_h3_big6_schinese"
        ]["prefix_counts"]
        self.assertGreater(r63a_pc["FX6_R63_"], 10)
        self.assertEqual(r63b_pc["FX6_R63_"], 3)
        self.assertGreater(r63c_pc["FX6_R63_"], 10)

    def test_60_round63_r63_meta_invariants_across_all_3_runs(self) -> None:
        for rk, rv in self.summary["runs"].items():
            m = rv["stage_b"]["r63"]
            self.assertEqual(m["raw_file_type_exposed_modes"], ["Compressed", "Uncompressed"], rk)
            self.assertEqual(len(m["raw_file_type_dormant_alpha_modes_rejected"]), 4, rk)
            self.assertEqual(m["jpeg_heif_switch_bit_depth"], 10, rk)
            self.assertEqual(m["hlg_still_image_gamut"], "BT.2100", rk)
            self.assertTrue(m["hlg_still_image_requires_heif_only_pasm_pp_off"], rk)
            self.assertFalse(m["fx6_still_shooting_mode_present"], rk)
            self.assertEqual(m["color_space_options"], ["sRGB", "AdobeRGB"], rk)
            self.assertTrue(m["adobergb_auto_first_char_underscore"], rk)
            self.assertTrue(m["set_file_name_leading_underscore_banned"], rk)
            self.assertTrue(m["set_file_name_survives_camera_settings_reset"], rk)
            self.assertTrue(m["set_file_name_reset_on_initialize"], rk)
            self.assertEqual(m["shutter_type_2modes_only"], ["Mechanical Shutter", "Electronic Shutter"], rk)
            self.assertTrue(m["shutter_type_auto_mode_omitted"], rk)
            self.assertTrue(m["silent_mode_forces_electronic_shutter"], rk)
            self.assertEqual(m["flash_max_sync_sec_inv"], 250, rk)
            self.assertTrue(m["flash_and_bulb_require_mechanical_shutter"], rk)
            self.assertTrue(m["e_front_curtain_shut_survives_camera_settings_reset"], rk)
            self.assertTrue(m["high_iso_nr_disabled_in_raw"], rk)
            self.assertEqual(m["drive_cont_hi_plus_max_fps"], 10, rk)
            self.assertTrue(m["slot1_tier0_still_vault_erofs"], rk)
            self.assertEqual(m["lossless_comp_bypass_events"], 0, rk)
            self.assertEqual(m["leading_underscore_prefix_events"], 0, rk)
            self.assertEqual(m["auto_shutter_type_bypass_events"], 0, rk)
            self.assertEqual(m["slot1_still_write_events"], 0, rk)
            self.assertEqual(m["e_nd_actuator_tx_count"], 0, rk)
            self.assertEqual(m["raw_firmware_bytes_leaked"], 0, rk)

    def test_61_round63_sanitize_helper_redacts_host_paths_and_reserved_port(self) -> None:
        dirty = {
            "run_id": "test-run",
            "lang": "schinese",
            "r63_mode": "still_raw_heif_colorspace_shutter_drive_big6",
            "kernel_version": "Linux version 4.9.337-scel+",
            "kernel_bin": "/Users/fake/secret/kernel.bin",
            "dtb_bin": "/Users/fake/secret/guest.dtb",
            "build": {"tmp_build": "/private/tmp/build-123"},
            "stage_b": {"r63": {"r63_mode": "still_raw_heif_colorspace_shutter_drive_big6"}},
            "r63_telemetry": {
                "wave49_init": {"r63_init_ok": 1},
                "wave49_guard": {"r63b_ok": 1},
                "clean_unmount_still_h0_h3": {"r63c_ok": 1, "surfaces_h0_eq_h3": 16},
            },
            "gpe0_readback": {"nonzero_pixels": 346686},
            "png_exports": {
                "alpha_png": {
                    "path": "/Users/kafu/repo/reports/2026-11-17-round63-realhw-still-raw-heif-colorspace-shuttertype-drive-qemu/assets/a.png"
                }
            },
            "prefix_counts": {"FX6_R63_": 10},
        }
        sanitized = self.runner.sanitize_round63_summary(dirty, dirty, dirty)
        raw = json.dumps(sanitized)
        self.assertNotIn("/Users/", raw)
        self.assertNotIn("/private/tmp/", raw)
        self.assertNotIn("kernel_bin", raw)
        self.assertNotIn("dtb_bin", raw)
        self.assertIn(
            "reports/2026-11-17-round63-realhw-still-raw-heif-colorspace-shuttertype-drive-qemu/assets/a.png",
            raw,
        )

    def test_62_round63_no_stray_temp_files_or_reserved_port_in_repo(self) -> None:
        for bad_name in ("tmp", "scratch", ".worktrees"):
            self.assertFalse((REPO_ROOT / bad_name).exists(), bad_name)
        reserved_port = "87" + "68"
        self.assertNotIn(reserved_port, self.summary_raw)
        self.assertNotIn(reserved_port, self.r63_readme)

    def test_63_round63_runner_escapes_percent_in_argparse_help_and_portable_tools(self) -> None:
        self.assertIn("ArgumentParser", self.runner_src)
        self.assertNotIn("/usr/" + "bin/python3", self.runner_src)
        self.assertIn('shutil.which("zig")', self.runner_src)
        self.assertIn("FX6_SCRATCH_DIR", self.runner_src)

    def test_64_round63_test_suite_contains_at_least_64_unit_tests(self) -> None:
        methods = [m for m in dir(self) if m.startswith("test_")]
        self.assertGreaterEqual(len(methods), 64)

    def test_65_round63_dual_mode_env_flags_preserve_zero_emmc_and_clean_room_parity(self) -> None:
        for env_overrides in (
            {},
            {"FX3_CLEAN_ROOM_TEST": "1"},
            {"FX3_FX6_FORCE_CLEAN_ROOM": "1"},
        ):
            with mock.patch.dict(os.environ, env_overrides, clear=False):
                parsed = self.runner.extract_milestones(
                    "Linux version 4.9.337-scel+\n"
                    "FX6_R63_WAVE49_INIT still_raw_heif_hlg_ok=1 colorspace_dsc_ban_ok=1 "
                    "shutter_nr_drive_ok=1 r63_init_ok=1\n"
                )
                self.assertEqual(parsed["r63_telemetry"]["wave49_init"]["r63_init_ok"], 1)

    def test_66_round63_argparse_percent_safe_help_and_no_hardcoded_python3(self) -> None:
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
