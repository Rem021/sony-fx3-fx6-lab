#!/usr/bin/env python3
"""Offline dual-mode unit tests for FX6-on-FX3 Round 65 (65th Round Milestone, 38/38 Real-HW Rounds R28..R65, 112th..114th Live Runs -> 114/114 Total, 76/76 PNGs <= 27,467 B — Wave-51)."""
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
ROUND65_REPORT_DIR = (
    REPO_ROOT
    / "reports"
    / "2026-11-17-round65-milestone-dci4k-aspect-recall-hold-camset-photocap-qemu"
)
WAVE51_SPEC_PATH = (
    REPO_ROOT
    / "reports"
    / "2026-11-17-global-sony-wave51-uhd-vs-dci4k-aspect-ratio-recall-custom-hold-camset-memory-photo-capture-intel"
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


def _build_overlay_for_r65(
    runner,
    parent_cpio: pathlib.Path,
    fp,
    fv,
    fb,
    fake_run,
    jit_meta: Dict[str, Any],
    work: pathlib.Path,
    r65_mode: str,
    lang: str = "schinese",
    enable_r65: bool = True,
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
            enable_r64=True,
            r64_mode="focus_area_zoom_iso_flash_big6",
            enable_r65=enable_r65,
            r65_mode=r65_mode,
            sd_manifest_mode="valid",
            lang=lang,
            shim_bytes=b"SHIM",
        )


class TestRound65MilestoneDci4kAspectRecallHoldCamsetPhotocapQemu(unittest.TestCase):
    EXPECTED_RUN_KEYS = (
        "r65a_dci4k_aspect_camset_photocap_big6_schinese",
        "r65b_wave51_dci4k_aspect_camset_photocap_guard",
        "r65c_clean_unmount_wave51_reset_h0_h3_big6_schinese",
    )

    runner: Any
    runner_src: str
    stage_a_src: str
    shim_src: str
    wave51_spec: str
    summary_raw: str
    summary: Dict[str, Any]
    r65_readme: str
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
    launcher_r65: Optional[bytes]
    shim_r65: Optional[bytes]
    shim_r64: Optional[bytes]
    r64_summary: Dict[str, Any]
    r63_summary: Dict[str, Any]
    r62_summary: Dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = _load_closure_module("fx6_brr_r65_cached", "build_and_run_round.py")
        cls.runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")
        cls.stage_a_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        cls.shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        cls.wave51_spec = WAVE51_SPEC_PATH.read_text(encoding="utf-8")
        cls.summary_raw = (ROUND65_REPORT_DIR / "summary.json").read_text(encoding="utf-8")
        cls.summary = json.loads(cls.summary_raw)
        cls.r65_readme = (ROUND65_REPORT_DIR / "README.md").read_text(encoding="utf-8")
        cls.closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")

        alpha_p = (
            ROUND65_REPORT_DIR
            / "assets"
            / "r65a-dci4k-aspect-camset-photocap-4ch-big6-schinese-alpha.png"
        )
        comp_p = (
            ROUND65_REPORT_DIR
            / "assets"
            / "r65a-dci4k-aspect-camset-photocap-4ch-big6-schinese-composited.png"
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
            cls.ov_a = _build_overlay_for_r65(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wa", "dci4k_aspect_camset_photocap_big6", lang="schinese",
            )
            cls.ov_b = _build_overlay_for_r65(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wb", "wave51_dci4k_aspect_camset_photocap_guard", lang="en",
            )
            cls.ov_c = _build_overlay_for_r65(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wc", "clean_unmount_wave51_reset_h0_h3_big6", lang="schinese",
            )
            cls.ov_off = _build_overlay_for_r65(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "woff", "dci4k_aspect_camset_photocap_big6", enable_r65=False,
            )
            cls.invalid_mode_raised = False
            try:
                _build_overlay_for_r65(
                    cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                    tpath / "wbad", "invalid_r65_mode",
                )
            except ValueError:
                cls.invalid_mode_raised = True

            zig_bin = shutil.which("zig") or (
                str(cls.runner.ZIG) if cls.runner.ZIG.is_file() else None
            )
            if zig_bin is not None:
                verify_r65_out = tpath / "fx6-stage-a-verify-r65"
                shim_r65_out = tpath / "libgrm-fbinit9-r65.so"
                shim_r64_out = tpath / "libgrm-fbinit9-r64.so"
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
                        str(verify_r65_out),
                    ],
                    [
                        zig_bin,
                        "cc",
                        "-target",
                        "aarch64-linux-gnu.2.25",
                        "-O0",
                        "-shared",
                        "-fPIC",
                        "-DFX6_ROUND=65",
                        str(CLOSURE_DIR / "libgrm-fbinit9.c"),
                        "-ldl",
                        "-lpthread",
                        "-o",
                        str(shim_r65_out),
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
                ):
                    cls.runner.subprocess.run(cmd, check=True)
                cls.launcher_r65 = verify_r65_out.read_bytes()
                cls.shim_r65 = shim_r65_out.read_bytes()
                cls.shim_r64 = shim_r64_out.read_bytes()
            else:
                cls.launcher_r65 = None
                cls.shim_r65 = None
                cls.shim_r64 = None

        cls.r64_summary = json.loads(
            (
                REPO_ROOT
                / "reports"
                / "2026-11-17-round64-milestone-focus-area-zoom-lever-iso-minss-flash-qemu"
                / "summary.json"
            ).read_text(encoding="utf-8")
        )
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

    def test_01_wave51_global_spec_present_and_covers_all_wave51_pillars(self) -> None:
        self.assertTrue(WAVE51_SPEC_PATH.is_file())
        for needle in (
            "XAVC S-I DCI 4K",
            "4096",
            "24.00p",
            "XAVC HS 4K",
            "XAVC S 4K",
            "4264",
            "Aspect Ratio",
            "3:2",
            "4:3",
            "16:9",
            "1:1",
            "Reg. Custom Shoot Set",
            "Recall Custom hold 1",
            "Camera Set. Memory",
            "CAMPR%02d%c.DAT",
            "SONY/SETTING/",
            "SONY/PRO/CAMERA/",
            "Photo Capture",
            "Enlarge Image",
            "Enlarge Initial Mag.",
            "Enlarge Initial Position",
        ):
            self.assertIn(needle, self.wave51_spec)

    def test_02_round65_summary_schema_round_milestone_and_zero_leaks(self) -> None:
        self.assertNotIn("/Users/", self.summary_raw)
        self.assertNotIn("/private/tmp/", self.summary_raw)
        self.assertEqual(
            self.summary["schema"],
            "fx6-on-fx3-round65-milestone-38realhw-dci4k-aspect-recall-hold-camset-photocap-qemu-v1",
        )
        self.assertEqual(self.summary["round"], 65)
        self.assertEqual(self.summary["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(tuple(self.summary["runs"].keys()), self.EXPECTED_RUN_KEYS)

    def test_03_round65_cli_accepts_round65_and_all_3_r65_modes(self) -> None:
        self.assertIn(", 64, 65]", self.runner_src)
        for mode in (
            "dci4k_aspect_camset_photocap_big6",
            "wave51_dci4k_aspect_camset_photocap_guard",
            "clean_unmount_wave51_reset_h0_h3_big6",
        ):
            self.assertIn(mode, self.runner_src)

    def test_04_round65_overlay_rejects_invalid_r65_mode(self) -> None:
        self.assertTrue(self.invalid_mode_raised)

    def test_05_round65_overlay_r65a_injects_etc_fx6_stage_r65_and_appfw_launch(self) -> None:
        replacements, additions, meta = self.ov_a
        self.assertTrue(meta["r65_enabled"])
        self.assertIn("etc/fx6_stage_r65", additions)
        self.assertIn("etc/fx6_r65_libjit.so", additions)
        r65_cfg = additions["etc/fx6_stage_r65"][0].decode("utf-8")
        self.assertIn("stage_r65=1", r65_cfg)
        self.assertIn("r65_mode=dci4k_aspect_camset_photocap_big6", r65_cfg)
        self.assertIn("milestone_65th_round_38th_realhw_114th_live_76_pngs=1", r65_cfg)
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("/usr/bin/appfw-launch", init_txt)
        self.assertNotIn("--r65-wave51-guard", init_txt)

    def test_06_round65_overlay_r65b_injects_early_guard_probe_and_poweroff(self) -> None:
        replacements, _, meta = self.ov_b
        self.assertEqual(meta["r65"]["r65_mode"], "wave51_dci4k_aspect_camset_photocap_guard")
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("--r65-wave51-guard", init_txt)
        self.assertIn("FX6_R65_WAVE51_GUARD_RC=", init_txt)
        self.assertIn("FX6_R65_WAVE51_GUARD_EXIT", init_txt)
        self.assertIn("poweroff -f", init_txt)

    def test_07_round65_overlay_r65c_integrated_runs_stage_b_big6(self) -> None:
        replacements, additions, meta = self.ov_c
        self.assertEqual(meta["r65"]["r65_mode"], "clean_unmount_wave51_reset_h0_h3_big6")
        r65_cfg = additions["etc/fx6_stage_r65"][0].decode("utf-8")
        self.assertIn("r65_mode=clean_unmount_wave51_reset_h0_h3_big6", r65_cfg)
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("/usr/bin/appfw-launch", init_txt)
        self.assertNotIn("--r65-wave51-guard", init_txt)

    def test_08_round65_overlay_disabled_when_enable_r65_false(self) -> None:
        _, additions, meta = self.ov_off
        self.assertFalse(meta["r65_enabled"])
        self.assertNotIn("etc/fx6_stage_r65", additions)
        self.assertNotIn("etc/fx6_r65_libjit.so", additions)
        self.assertNotIn("r65", meta)

    def test_09_round65_stage_a_c_source_contains_all_3_wave51_probes(self) -> None:
        for sym in (
            "setup_r65_dci4k_aspect_camset_photocap_probe",
            "run_r65_wave51_guard_probe",
            "run_r65_clean_unmount_wave51_h0_h3_probe",
            "FX6_R65_WAVE51_INIT",
            "FX6_R65_WAVE51_GUARD",
            "FX6_R65_CLEAN_UNMOUNT_WAVE51_H0_H3",
            "--r65-wave51-guard",
            "--r65-clean-unmount-wave51-h0-h3",
            "/etc/fx6_stage_r65",
        ):
            self.assertIn(sym, self.stage_a_src)

    def test_10_round65_shim_c_source_contains_r65_guarded_bridges(self) -> None:
        self.assertIn("#if FX6_ROUND >= 65", self.shim_src)
        for sym in (
            "FX6_R65_XAVC_DCI4K_UHD_HDMI_RAW_BRIDGE",
            "FX6_R65_STILL_ASPECT_RATIO_FX6_BRIDGE",
            "FX6_R65_RECALL_HOLD_11CHK_CAMSET_BRIDGE",
            "FX6_R65_PHOTOCAP_ENLARGE_SLOT1_VAULT_BRIDGE",
            "FX6_R65_LANG_TELEMETRY",
            "FX6_STAGE_B_R65_BRIDGE",
        ):
            self.assertIn(sym, self.shim_src)

    def test_11_round65_compile_launcher_and_shim_aarch64_elf_symbols(self) -> None:
        if self.launcher_r65 is None or self.shim_r65 is None:
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertEqual(self.launcher_r65[:4], b"\x7fELF")
        self.assertEqual(self.shim_r65[:4], b"\x7fELF")
        self.assertEqual(struct.unpack_from("<H", self.shim_r65, 18)[0], 183)
        self.assertIn(b"FX6_R65_XAVC_DCI4K_UHD_HDMI_RAW_BRIDGE", self.shim_r65)
        self.assertIn(b"FX6_R65_STILL_ASPECT_RATIO_FX6_BRIDGE", self.shim_r65)
        self.assertIn(b"FX6_R65_RECALL_HOLD_11CHK_CAMSET_BRIDGE", self.shim_r65)
        self.assertIn(b"FX6_R65_PHOTOCAP_ENLARGE_SLOT1_VAULT_BRIDGE", self.shim_r65)

    def test_12_round65_shim_round64_backward_compat_excludes_r65_bridges(self) -> None:
        if self.shim_r64 is None:
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertIn(b"FX6_R64_FOCUS_AREA_14MODE_LIMIT_REG_BRIDGE", self.shim_r64)
        self.assertNotIn(b"FX6_R65_XAVC_DCI4K_UHD_HDMI_RAW_BRIDGE", self.shim_r64)

    def test_13_round65_parse_log_extracts_all_9_r65_prefixes_and_rc(self) -> None:
        serial_text = (
            "\n".join(
                [
                    "Linux version 4.9.337-scel+ (sony@fx3)",
                    "FX6_R65_WAVE51_INIT fx3_wave51_nodes_ok=1 uxc_tokens_ok=1 dci4k_uhd_hdmi_raw_ok=1 still_aspect_ratio_ok=1 recall_hold_camset_ok=1 photocap_enlarge_slot1_ok=1 emmc_write_count=0 r65_init_ok=1",
                    "FX6_R65_XAVC_DCI4K_UHD_HDMI_RAW_BRIDGE xavc_si_dci4k_24p_reboot_59p_ok=1 long_gop_uhd_only_4264_hdmi_raw_slog3_ok=1 shutter_angle_5_6_to_360_2f_64f_ok=1 xavc_dci4k_uhd_hdmi_raw_ok=1 long_gop_dci4k_bypass_events=0 emmc_write_count=0 r65_bridge_ok=1",
                    "FX6_R65_STILL_ASPECT_RATIO_FX6_BRIDGE still_aspect_4ratio_raw_crop_ok=1 apsc_s35_l_to_m_clamp_ok=1 fx6_still_aspect_enoent_ok=1 still_aspect_ratio_fx6_ok=1 fx6_still_aspect_spoof_events=0 emmc_write_count=0 p2_setting_writes=0",
                    "FX6_R65_RECALL_HOLD_11CHK_CAMSET_BRIDGE reg_custom_shoot_11chk_still_pasm_ok=1 body_1_3_card_m1_m4_campr_camset_ok=1 fx6_pro_camera_enoent_ok=1 recall_hold_11chk_camset_ok=1 movie_recall_hold_bypass_events=0 fx6_pro_camera_spoof_events=0 cnflasha_writes=0 emmc_write_count=0",
                    "FX6_R65_PHOTOCAP_ENLARGE_SLOT1_VAULT_BRIDGE photocap_83m_21m_dci4k_lockout_ok=1 enlarge_image_mag_pos_split_ok=1 slot1_tier0_vault_erofs_ok=1 photocap_enlarge_slot1_ok=1 dci4k_photocap_bypass_events=0 slot1_wave51_write_events=0 cnflasha_writes=0 emmc_write_count=0",
                    "FX6_R65_LANG_TELEMETRY lang=schinese font_bank=23 str_bank=19 milestone_65th_round_38th_realhw_114th_live_76_pngs=1 r65_bridge_ok=1",
                    "FX6_STAGE_B_R65_BRIDGE round=65 faithful=1 nop_count=0 milestone_65th_round_38th_realhw_114th_live_76_pngs=1 emmc_write_count=0",
                    "FX6_R65_WAVE51_GUARD long_gop_dci4k_rc=-95 dci4k_120p_rc=-22 fx6_still_aspect_rc=-2 recall_movie_rc=-16 fx6_pro_camera_rc=-2 pcap_dci4k_rc=-95 slot1_wave51_erofs_rc=-30 r65b_ok=1",
                    "FX6_R65_WAVE51_GUARD_RC=0",
                    "FX6_R65_CLEAN_UNMOUNT_WAVE51_H0_H3 stock_unmount_restored_ok=1 camreset_preserves_wave51_survivors_ok=1 card_format_preserves_body_ok=1 initialize_restores_wave51_defaults_ok=1 surfaces_h0_eq_h3=16 r65c_ok=1",
                ]
            )
            + "\n"
        )
        parsed = self.runner.extract_milestones(serial_text)
        r65_t = parsed["r65_telemetry"]
        self.assertEqual(r65_t["wave51_guard_rc"], 0)
        self.assertEqual(r65_t["wave51_init"]["dci4k_uhd_hdmi_raw_ok"], 1)
        self.assertEqual(r65_t["xavc_dci4k_uhd_hdmi_raw_bridge"]["xavc_dci4k_uhd_hdmi_raw_ok"], 1)
        self.assertEqual(r65_t["still_aspect_ratio_fx6_bridge"]["still_aspect_ratio_fx6_ok"], 1)
        self.assertEqual(r65_t["recall_hold_11chk_camset_bridge"]["recall_hold_11chk_camset_ok"], 1)
        self.assertEqual(r65_t["photocap_enlarge_slot1_bridge"]["photocap_enlarge_slot1_ok"], 1)
        self.assertEqual(r65_t["lang_telemetry"]["lang"], "schinese")
        self.assertEqual(r65_t["lang_telemetry"]["milestone_65th_round_38th_realhw_114th_live_76_pngs"], 1)
        self.assertEqual(r65_t["stage_b_bridge"]["round"], 65)
        self.assertEqual(r65_t["wave51_guard"]["r65b_ok"], 1)
        self.assertEqual(r65_t["clean_unmount_wave51_h0_h3"]["surfaces_h0_eq_h3"], 16)
        self.assertEqual(parsed["prefix_counts"]["FX6_R65_"], 9)

    def test_14_round65_parse_log_defaults_when_no_r65_lines_present(self) -> None:
        parsed = self.runner.extract_milestones("Linux version 4.9.337-scel+\n")
        self.assertIsNone(parsed["r65_telemetry"])
        self.assertEqual(parsed["prefix_counts"].get("FX6_R65_", 0), 0)

    def test_15_round65_runner_uses_fx6_r65_prefix_and_stage_label(self) -> None:
        self.assertIn('if args.round >= 65:\n        tmp_prefix = "fx6-r65"', self.runner_src)
        self.assertIn(
            "Milestone65thRound38RealHw114thLiveWave51Dci4kAspectRecallHoldCamsetPhotoCap",
            self.runner_src,
        )
        self.assertIn(", 64, 65]", self.runner_src)

    def test_16_round65_runner_portability_and_sanitizer_helper(self) -> None:
        self.assertIn('shutil.which("zig")', self.runner_src)
        self.assertIn("FX6_SCRATCH_DIR", self.runner_src)
        self.assertIn("def sanitize_round65_summary(", self.runner_src)
        self.assertNotIn("/usr/" + "bin/python3", self.runner_src)

    def test_17_round65_summary_json_top_level_schema_and_milestone_metadata(self) -> None:
        d = self.summary
        self.assertEqual(
            d["schema"],
            "fx6-on-fx3-round65-milestone-38realhw-dci4k-aspect-recall-hold-camset-photocap-qemu-v1",
        )
        self.assertEqual(d["round"], 65)
        self.assertIn("65th Round Grand Milestone!", d["milestone"])
        self.assertIn("38/38 Real-HW Rounds", d["milestone"])
        self.assertIn("114/114 Total Live Runs", d["milestone"])
        self.assertIn("76/76 PNGs <= 27,467 B", d["milestone"])
        self.assertEqual(d["date"], "2026-11-17")
        self.assertIn("4.9.337-scel+", d["kernel_version"])
        self.assertEqual(d["raw_firmware_bytes_leaked"], 0)

    def test_18_round65_summary_json_zero_host_path_and_scratch_leaks(self) -> None:
        for forbidden in (
            "/Users/",
            "/private/tmp/",
            "/var/folders/",
            "work/_scratch/",
            "work/_tests/",
            ":87" + "68",
        ):
            self.assertNotIn(forbidden, self.summary_raw)

    def test_19_round65_summary_audit_block_confirms_38_rounds_114_runs_76_pngs(self) -> None:
        audit = self.summary["r65_milestone_dci4k_aspect_recall_hold_camset_photocap_audit"]
        self.assertEqual(audit["round"], 65)
        self.assertEqual(audit["milestone"], 65)
        self.assertGreaterEqual(audit["milestone295_qemu_rounds"], 38)
        self.assertGreaterEqual(audit["milestone295_qemu_runs"], 114)
        self.assertGreaterEqual(audit["milestone295_png_receipts"], 76)
        self.assertEqual(audit["total_runs"], 3)
        for k, v in audit.items():
            if isinstance(v, bool):
                self.assertTrue(v, f"Expected audit boolean {k} to be True")

    def test_20_round65_all_3_runs_present_with_kernel_4_9_337_and_zero_crashes_writes(self) -> None:
        runs = self.summary["runs"]
        self.assertEqual(list(runs.keys()), list(self.EXPECTED_RUN_KEYS))
        for rk, rv in runs.items():
            self.assertEqual(rv["round"], 65, rk)
            self.assertIn("4.9.337-scel+", rv["kernel_version"], rk)
            self.assertEqual(rv["nop_count"], 0, rk)
            self.assertEqual(rv["crashes"], 0, rk)
            self.assertEqual(rv["emmc_write_count"], 0, rk)
            self.assertGreater(rv["wall_elapsed_sec"], 0.0, rk)

    def test_21_round65_r65a_dci4k_uhd_hdmi_raw_and_still_aspect_ratio_verified(self) -> None:
        init_t = self.summary["runs"][
            "r65a_dci4k_aspect_camset_photocap_big6_schinese"
        ]["r65_telemetry"]["wave51_init"]
        self.assertEqual(init_t["fx3_wave51_nodes_ok"], 1)
        self.assertEqual(init_t["uxc_tokens_ok"], 1)
        self.assertEqual(init_t["dci4k_uhd_hdmi_raw_ok"], 1)
        self.assertEqual(init_t["still_aspect_ratio_ok"], 1)
        self.assertEqual(init_t["dci4k_119p_rc"], -22)
        self.assertEqual(init_t["long_gop_dci4k_rc"], -95)
        self.assertEqual(init_t["dormant_8k_rc"], -95)
        self.assertEqual(init_t["hdmi_raw_no_log_rc"], -16)
        self.assertEqual(init_t["fx6_still_aspect_rc"], -2)
        self.assertEqual(init_t["long_gop_dci4k_bypass_events"], 0)
        self.assertEqual(init_t["fx6_still_aspect_spoof_events"], 0)

    def test_22_round65_r65a_recall_hold_camset_and_photocap_enlarge_verified(self) -> None:
        init_t = self.summary["runs"][
            "r65a_dci4k_aspect_camset_photocap_big6_schinese"
        ]["r65_telemetry"]["wave51_init"]
        self.assertEqual(init_t["recall_hold_camset_ok"], 1)
        self.assertEqual(init_t["photocap_enlarge_slot1_ok"], 1)
        self.assertEqual(init_t["movie_recall_hold_rc"], -16)
        self.assertEqual(init_t["fx6_pro_cam_spoof_rc"], -2)
        self.assertEqual(init_t["pcap_dci4k_rc"], -95)
        self.assertEqual(init_t["pcap_slot1_rc"], -30)
        self.assertEqual(init_t["movie_recall_hold_bypass_events"], 0)
        self.assertEqual(init_t["fx6_pro_camera_spoof_events"], 0)
        self.assertEqual(init_t["dci4k_photocap_bypass_events"], 0)

    def test_23_round65_r65a_p2_cnflasha_and_slot1_ro_guards_intact(self) -> None:
        init_t = self.summary["runs"][
            "r65a_dci4k_aspect_camset_photocap_big6_schinese"
        ]["r65_telemetry"]["wave51_init"]
        self.assertEqual(init_t["slot1_wave51_write_events"], 0)
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
        self.assertEqual(init_t["r65_init_ok"], 1)

    def test_24_round65_r65a_stage_b_schinese_lang_telemetry_and_bridge(self) -> None:
        r65a_t = self.summary["runs"][
            "r65a_dci4k_aspect_camset_photocap_big6_schinese"
        ]["r65_telemetry"]
        lt = r65a_t["lang_telemetry"]
        self.assertEqual(lt["lang"], "schinese")
        self.assertEqual(lt["bk4_lang_id"], "0x02cf019c")
        self.assertEqual(lt["bk4_lang_val"], "0x19")
        self.assertEqual(lt["lang_enum"], "0x2b45_CHINESE_SIMPLIFIED")
        self.assertEqual(lt["font_bank"], 23)
        self.assertEqual(lt["str_bank"], 19)
        self.assertEqual(lt["gpe_fb"], 0)
        self.assertEqual(lt["round65_milestone_38realhw_wave51_dci4k_aspect_recall_camset_photocap"], 1)
        self.assertEqual(lt["milestone_65th_round_38th_realhw_114th_live_76_pngs"], 1)
        self.assertEqual(lt["long_gop_dci4k_bypass_events"], 0)
        self.assertEqual(lt["fx6_still_aspect_spoof_events"], 0)
        self.assertEqual(lt["movie_recall_hold_bypass_events"], 0)
        self.assertEqual(lt["fx6_pro_camera_spoof_events"], 0)
        self.assertEqual(lt["dci4k_photocap_bypass_events"], 0)
        self.assertEqual(lt["slot1_wave51_write_events"], 0)
        self.assertEqual(lt["raw_firmware_bytes_leaked"], 0)

        sb = r65a_t["stage_b_bridge"]
        self.assertEqual(sb["round"], 65)
        self.assertEqual(sb["faithful"], 1)
        self.assertEqual(sb["nop_count"], 0)
        self.assertEqual(sb["xavc_dci4k_24p_reboot_59p_hdmi_raw_angle"], 1)
        self.assertEqual(sb["still_aspect_ratio_4mode_apsc_vs_fx6"], 1)
        self.assertEqual(sb["recall_hold_11chk_campr_camset_vs_pro_camera"], 1)
        self.assertEqual(sb["photocap_dci4k_lockout_enlarge_slot1_vault"], 1)
        self.assertEqual(sb["milestone_65th_round_38th_realhw_114th_live_76_pngs"], 1)

    def test_25_round65_r65a_stage_b_4_pillar_bridges_verified(self) -> None:
        r65a_t = self.summary["runs"][
            "r65a_dci4k_aspect_camset_photocap_big6_schinese"
        ]["r65_telemetry"]
        xb = r65a_t["xavc_dci4k_uhd_hdmi_raw_bridge"]
        self.assertEqual(xb["xavc_si_dci4k_24p_reboot_59p_ok"], 1)
        self.assertEqual(xb["long_gop_uhd_only_4264_hdmi_raw_slog3_ok"], 1)
        self.assertEqual(xb["shutter_angle_5_6_to_360_2f_64f_ok"], 1)
        self.assertEqual(xb["xavc_dci4k_uhd_hdmi_raw_ok"], 1)
        self.assertEqual(xb["long_gop_dci4k_bypass_events"], 0)
        self.assertEqual(xb["r65_bridge_ok"], 1)

        ab = r65a_t["still_aspect_ratio_fx6_bridge"]
        self.assertEqual(ab["still_aspect_4ratio_raw_crop_ok"], 1)
        self.assertEqual(ab["apsc_s35_l_to_m_clamp_ok"], 1)
        self.assertEqual(ab["fx6_still_aspect_enoent_ok"], 1)
        self.assertEqual(ab["still_aspect_ratio_fx6_ok"], 1)
        self.assertEqual(ab["fx6_still_aspect_spoof_events"], 0)
        self.assertEqual(ab["p2_setting_writes"], 0)

        rb = r65a_t["recall_hold_11chk_camset_bridge"]
        self.assertEqual(rb["reg_custom_shoot_11chk_still_pasm_ok"], 1)
        self.assertEqual(rb["body_1_3_card_m1_m4_campr_camset_ok"], 1)
        self.assertEqual(rb["fx6_pro_camera_enoent_ok"], 1)
        self.assertEqual(rb["recall_hold_11chk_camset_ok"], 1)
        self.assertEqual(rb["movie_recall_hold_bypass_events"], 0)
        self.assertEqual(rb["fx6_pro_camera_spoof_events"], 0)

        pb = r65a_t["photocap_enlarge_slot1_bridge"]
        self.assertEqual(pb["photocap_83m_21m_dci4k_lockout_ok"], 1)
        self.assertEqual(pb["enlarge_image_mag_pos_split_ok"], 1)
        self.assertEqual(pb["slot1_tier0_vault_erofs_ok"], 1)
        self.assertEqual(pb["photocap_enlarge_slot1_ok"], 1)
        self.assertEqual(pb["dci4k_photocap_bypass_events"], 0)
        self.assertEqual(pb["slot1_wave51_write_events"], 0)
        self.assertEqual(pb["cnflasha_writes"], 0)

    def test_26_round65_r65a_gpe0_readback_ge_300k_pixels_and_87_colors(self) -> None:
        r65a = self.summary["runs"][
            "r65a_dci4k_aspect_camset_photocap_big6_schinese"
        ]
        self.assertEqual(r65a["target_presenter"], "31procam_big6_menu_home_presenter")
        self.assertEqual(r65a["target_sid"], "0x0a")
        self.assertGreaterEqual(r65a["total_threads_seen"], 150)
        gpe0 = r65a["gpe0_readback"]
        self.assertTrue(gpe0["present"])
        self.assertEqual(gpe0["bytes"], 2211840)
        self.assertEqual(gpe0["total_pixels"], 552960)
        self.assertGreaterEqual(gpe0["nonzero_pixels"], 300000)
        self.assertEqual(gpe0["nonzero_pixels"], 346206)
        self.assertEqual(gpe0["unique_colors"], 87)

    def test_27_round65_r65a_stage_b_manifest_13_hashes_and_r65_metadata(self) -> None:
        sb = self.summary["runs"][
            "r65a_dci4k_aspect_camset_photocap_big6_schinese"
        ]["stage_b"]
        self.assertEqual(sb["manifest_count"], 13)
        self.assertEqual(len(sb["manifest_items"]), 13)
        for item in sb["manifest_items"]:
            self.assertEqual(len(item["sha256"]), 64)
        m = sb["r65"]
        self.assertEqual(m["r65_mode"], "dci4k_aspect_camset_photocap_big6")
        self.assertTrue(m["milestone_65th_round_38realhw_rounds"])
        self.assertGreaterEqual(m["realhw_round_ordinal"], 38)
        self.assertGreaterEqual(m["total_live_runs_at_completion"], 114)
        self.assertGreaterEqual(m["total_png_receipts_at_completion"], 76)
        self.assertEqual(m["xavc_si_dci4k_uxc_token"], "0x7336:XAVC S-I DCI 4K")
        self.assertEqual(m["xavc_si_dci4k_resolution"], "4096x2160")
        self.assertEqual(m["xavc_si_dci4k_aspect"], "17:9")
        self.assertEqual(m["xavc_si_dci4k_sq_fps_supported"], [1, 2, 3, 6, 12, 24, 48])
        self.assertEqual(m["hdmi_raw_output_resolution"], "4264x2408")
        self.assertEqual(m["shutter_mode_angle_range_deg"], [5.6, 360.0])
        self.assertEqual(m["shutter_mode_angle_frames_range"], [2, 64])
        self.assertEqual(m["still_aspect_ratio_uxc_token"], "0x757c:Aspect Ratio")
        self.assertEqual(m["still_aspect_ratio_default"], "3:2")
        self.assertFalse(m["fx6_still_aspect_ratio_present"])
        self.assertEqual(m["reg_custom_shoot_set_uxc_token"], "0x7631:Reg. Custom Shoot Set")
        self.assertEqual(m["reg_custom_shoot_set_checkbox_count"], 11)
        self.assertEqual(m["camera_set_memory_body_banks"], [1, 2, 3])
        self.assertEqual(m["camera_set_memory_card_banks"], ["M1", "M2", "M3", "M4"])
        self.assertEqual(m["fx3_card_campr_sd_path_fmt"], "/PRIVATE/SONY/SETTING/FX3/CAMPR%02d%c.DAT")
        self.assertFalse(m["fx3_sony_pro_camera_present"])
        self.assertEqual(m["photo_capture_uxc_token"], "0x6856:Photo Capture")
        self.assertEqual(m["photo_capture_mp"], {"4K": "8.3M", "HD": "2.1M"})
        self.assertEqual(m["photo_capture_dci4k_lockout_uxc_token"], "_g.uxc 0x60ce")

    def test_28_round65_r65b_dci4k_long_gop_120p_8k_and_hdmi_raw_guards_blocked(self) -> None:
        r65b_t = self.summary["runs"][
            "r65b_wave51_dci4k_aspect_camset_photocap_guard"
        ]["r65_telemetry"]
        self.assertEqual(r65b_t["wave51_guard_rc"], 0)
        gd = r65b_t["wave51_guard"]
        self.assertEqual(gd["long_gop_dci4k_rc"], -95)
        self.assertEqual(gd["long_gop_24_00p_rc"], -95)
        self.assertEqual(gd["dci4k_120p_rc"], -22)
        self.assertEqual(gd["dci4k_sq_120fps_rc"], -22)
        self.assertEqual(gd["dormant_8k_rc"], -95)
        self.assertEqual(gd["hdmi_raw_no_log_rc"], -16)
        self.assertEqual(gd["angle_out_of_range_rc"], -22)
        self.assertEqual(gd["long_gop_dci4k_bypass_events"], 0)

    def test_29_round65_r65b_fx6_aspect_recall_hold_and_pro_camera_guards_blocked(self) -> None:
        gd = self.summary["runs"][
            "r65b_wave51_dci4k_aspect_camset_photocap_guard"
        ]["r65_telemetry"]["wave51_guard"]
        self.assertEqual(gd["fx6_still_aspect_rc"], -2)
        self.assertEqual(gd["recall_movie_rc"], -16)
        self.assertEqual(gd["recall_sq_rc"], -16)
        self.assertEqual(gd["recall_iauto_rc"], -16)
        self.assertEqual(gd["recall_mr_rc"], -16)
        self.assertEqual(gd["recall_selftimer_rc"], -22)
        self.assertEqual(gd["recall_12chk_rc"], -22)
        self.assertEqual(gd["fx6_pro_camera_rc"], -2)
        self.assertEqual(gd["camset_slot2_rc"], -13)
        self.assertEqual(gd["fx6_still_aspect_spoof_events"], 0)
        self.assertEqual(gd["movie_recall_hold_bypass_events"], 0)
        self.assertEqual(gd["fx6_pro_camera_spoof_events"], 0)

    def test_30_round65_r65b_photocap_dci4k_lockout_and_enlarge_movie_blocked(self) -> None:
        gd = self.summary["runs"][
            "r65b_wave51_dci4k_aspect_camset_photocap_guard"
        ]["r65_telemetry"]["wave51_guard"]
        self.assertEqual(gd["pcap_dci4k_rc"], -95)
        self.assertEqual(gd["pcap_slot1_rc"], -30)
        self.assertEqual(gd["enlarge_movie_rc"], -16)
        self.assertEqual(gd["dci4k_photocap_bypass_events"], 0)
        self.assertEqual(gd["appfw_ok"], 1)
        self.assertEqual(gd["shim_elf_ok"], 1)

    def test_31_round65_r65b_slot1_wave51_erofs_and_zero_emmc_cnflasha_writes(self) -> None:
        gd = self.summary["runs"][
            "r65b_wave51_dci4k_aspect_camset_photocap_guard"
        ]["r65_telemetry"]["wave51_guard"]
        self.assertEqual(gd["slot1_wave51_erofs_rc"], -30)
        self.assertEqual(gd["slot1_vault_ro_blocked_rc"], -30)
        self.assertEqual(gd["slot1_vault_sha256_match"], 1)
        self.assertEqual(gd["p2_write_blocked_rc"], -30)
        self.assertEqual(gd["cnflasha_ro_blocked_rc"], -30)
        self.assertEqual(gd["slot1_wave51_write_events"], 0)
        self.assertEqual(gd["passive_tx_bytes_emitted"], 0)
        self.assertEqual(gd["e_nd_actuator_tx_count"], 0)
        self.assertEqual(gd["cnflasha_writes"], 0)
        self.assertEqual(gd["emmc_write_count"], 0)
        self.assertEqual(gd["r65b_ok"], 1)

    def test_32_round65_r65c_clean_unmount_reset_tiers_and_card_format_verified(self) -> None:
        ci = self.summary["runs"][
            "r65c_clean_unmount_wave51_reset_h0_h3_big6_schinese"
        ]["r65_telemetry"]["clean_unmount_wave51_h0_h3"]
        self.assertEqual(ci["stock_unmount_restored_ok"], 1)
        self.assertEqual(ci["camreset_preserves_wave51_survivors_ok"], 1)
        self.assertEqual(ci["card_format_preserves_body_ok"], 1)
        self.assertEqual(ci["initialize_restores_wave51_defaults_ok"], 1)
        self.assertEqual(ci["long_gop_dci4k_bypass_events"], 0)
        self.assertEqual(ci["fx6_still_aspect_spoof_events"], 0)
        self.assertEqual(ci["movie_recall_hold_bypass_events"], 0)
        self.assertEqual(ci["fx6_pro_camera_spoof_events"], 0)
        self.assertEqual(ci["dci4k_photocap_bypass_events"], 0)
        self.assertEqual(ci["slot1_wave51_write_events"], 0)

    def test_33_round65_r65c_dlopen_and_16_h0_eq_h3_idempotent_unmount(self) -> None:
        ci = self.summary["runs"][
            "r65c_clean_unmount_wave51_reset_h0_h3_big6_schinese"
        ]["r65_telemetry"]["clean_unmount_wave51_h0_h3"]
        self.assertEqual(ci["dlopen_ok"], 1)
        self.assertEqual(ci["surfaces_verified"], 16)
        self.assertEqual(ci["surfaces_h0_eq_h3"], 16)
        self.assertEqual(ci["drift_bits"], 0)
        self.assertEqual(ci["cnflasha_write_bytes"], 0)
        self.assertEqual(ci["emmc_write_bytes"], 0)
        self.assertEqual(ci["e_nd_actuator_tx_count"], 0)
        self.assertEqual(ci["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(ci["emmc_write_count"], 0)
        self.assertEqual(ci["r65c_ok"], 1)

    def test_34_round65_r65c_integrated_renders_valid_big6_gpe0_readback(self) -> None:
        r65c = self.summary["runs"][
            "r65c_clean_unmount_wave51_reset_h0_h3_big6_schinese"
        ]
        self.assertEqual(r65c["target_presenter"], "31procam_big6_menu_home_presenter")
        self.assertEqual(r65c["target_sid"], "0x0a")
        gpe0 = r65c["gpe0_readback"]
        self.assertTrue(gpe0["present"])
        self.assertEqual(gpe0["bytes"], 2211840)
        self.assertEqual(gpe0["total_pixels"], 552960)
        self.assertGreaterEqual(gpe0["nonzero_pixels"], 300000)
        self.assertEqual(gpe0["unique_colors"], 87)

    def test_35_round65_realhw_mechanisms_verified_7_blocks_match_run_telemetry(self) -> None:
        rm = self.summary["realhw_mechanisms_verified"]
        self.assertEqual(len(rm), 7)
        r65a = self.summary["runs"][
            "r65a_dci4k_aspect_camset_photocap_big6_schinese"
        ]["r65_telemetry"]
        r65b = self.summary["runs"][
            "r65b_wave51_dci4k_aspect_camset_photocap_guard"
        ]["r65_telemetry"]
        r65c = self.summary["runs"][
            "r65c_clean_unmount_wave51_reset_h0_h3_big6_schinese"
        ]["r65_telemetry"]
        self.assertEqual(rm["wave51_dci4k_aspect_camset_photocap_init"], r65a["wave51_init"])
        self.assertEqual(rm["xavc_dci4k_uhd_hdmi_raw_stage_b_bridge"], r65a["xavc_dci4k_uhd_hdmi_raw_bridge"])
        self.assertEqual(rm["still_aspect_ratio_fx6_stage_b_bridge"], r65a["still_aspect_ratio_fx6_bridge"])
        self.assertEqual(rm["recall_hold_11chk_camset_stage_b_bridge"], r65a["recall_hold_11chk_camset_bridge"])
        self.assertEqual(rm["photocap_enlarge_slot1_vault_stage_b_bridge"], r65a["photocap_enlarge_slot1_bridge"])
        self.assertEqual(rm["wave51_fail_closed_guard"], r65b["wave51_guard"])
        self.assertEqual(rm["clean_unmount_wave51_reset_and_16_h0_h3"], r65c["clean_unmount_wave51_h0_h3"])

    def test_36_round65_reset_tiers_survival_consistent_across_runs(self) -> None:
        r65a_t = self.summary["runs"][
            "r65a_dci4k_aspect_camset_photocap_big6_schinese"
        ]["r65_telemetry"]
        r65c_ci = self.summary["runs"][
            "r65c_clean_unmount_wave51_reset_h0_h3_big6_schinese"
        ]["r65_telemetry"]["clean_unmount_wave51_h0_h3"]
        self.assertEqual(r65a_t["wave51_init"]["dci4k_uhd_hdmi_raw_ok"], 1)
        self.assertEqual(r65c_ci["stock_unmount_restored_ok"], 1)
        self.assertEqual(r65c_ci["camreset_preserves_wave51_survivors_ok"], 1)
        self.assertEqual(r65c_ci["card_format_preserves_body_ok"], 1)
        self.assertEqual(r65c_ci["initialize_restores_wave51_defaults_ok"], 1)

    def test_37_round65_cross_round_consistency_with_r64_slot1_ro_and_zero_leaks(self) -> None:
        self.assertEqual(self.r64_summary["round"], 64)
        r64b_gd = self.r64_summary["runs"][
            "r64b_wave50_focus_zoom_iso_flash_guard"
        ]["r64_telemetry"]["wave50_guard"]
        self.assertEqual(r64b_gd["slot1_vault_ro_blocked_rc"], -30)
        r65b_gd = self.summary["runs"][
            "r65b_wave51_dci4k_aspect_camset_photocap_guard"
        ]["r65_telemetry"]["wave51_guard"]
        self.assertEqual(r65b_gd["slot1_vault_ro_blocked_rc"], -30)
        self.assertEqual(r65b_gd["slot1_wave51_erofs_rc"], -30)
        self.assertEqual(r65b_gd["slot1_vault_sha256_match"], 1)
        self.assertEqual(r65b_gd["long_gop_dci4k_bypass_events"], 0)
        self.assertEqual(r65b_gd["fx6_pro_camera_spoof_events"], 0)

    def test_38_round65_cross_round_consistency_with_r63_and_r62_zero_emmc_writes(self) -> None:
        self.assertEqual(self.r63_summary["round"], 63)
        self.assertEqual(self.r62_summary["round"], 62)
        r63b_gd = self.r63_summary["runs"][
            "r63b_still_raw_heif_colorspace_shutter_guard"
        ]["r63_telemetry"]["wave49_guard"]
        self.assertEqual(r63b_gd["emmc_write_count"], 0)
        r62b_gd = self.r62_summary["runs"][
            "r62b_pp_log_wb_cineei_metering_guard"
        ]["r62_telemetry"]["wave48_guard"]
        self.assertEqual(r62b_gd["emmc_write_count"], 0)
        r65b_gd = self.summary["runs"][
            "r65b_wave51_dci4k_aspect_camset_photocap_guard"
        ]["r65_telemetry"]["wave51_guard"]
        self.assertEqual(r65b_gd["emmc_write_count"], 0)
        self.assertEqual(r65b_gd["cnflasha_writes"], 0)

    def test_39_round65_cross_round_consistency_with_r64_16_h0_eq_h3(self) -> None:
        r64c = self.r64_summary["runs"][
            "r64c_clean_unmount_wave50_reset_h0_h3_big6_schinese"
        ]["r64_telemetry"]["clean_unmount_wave50_h0_h3"]
        self.assertEqual(r64c["surfaces_h0_eq_h3"], 16)
        r65c = self.summary["runs"][
            "r65c_clean_unmount_wave51_reset_h0_h3_big6_schinese"
        ]["r65_telemetry"]["clean_unmount_wave51_h0_h3"]
        self.assertEqual(r65c["surfaces_h0_eq_h3"], 16)
        self.assertEqual(r65c["drift_bits"], 0)

    def test_40_round65_unexecuted_physical_camera_bench_boundaries_documented(self) -> None:
        bounds = self.summary["unexecuted_physical_camera_bench_boundaries"]
        self.assertEqual(len(bounds), 3)
        joined = " ".join(bounds)
        self.assertIn("XAVC S-I DCI 4K", joined)
        self.assertIn("4264x2408", joined)
        self.assertIn("Aspect Ratio", joined)
        self.assertIn("Reg. Custom Shoot Set", joined)
        self.assertIn("CAMSET01..10.DAT", joined)
        self.assertIn("Photo Capture", joined)
        self.assertIn("Enlarge Image", joined)
        self.assertIn("Slot-1", joined)

    def test_41_round65_alpha_png_exists_le_27467b_and_matches_summary_sha256(self) -> None:
        pe = self.summary["runs"][
            "r65a_dci4k_aspect_camset_photocap_big6_schinese"
        ]["png_exports"]["alpha_png"]
        self.assertLessEqual(len(self.alpha_png_bytes), 27467)
        self.assertLess(len(self.alpha_png_bytes), 28672)
        self.assertLess(len(self.alpha_png_bytes), 51200)
        self.assertEqual(len(self.alpha_png_bytes), pe["bytes"])
        self.assertEqual(
            hashlib.sha256(self.alpha_png_bytes).hexdigest(), pe["sha256"]
        )

    def test_42_round65_composited_png_exists_le_27467b_and_matches_summary_sha256(self) -> None:
        pe = self.summary["runs"][
            "r65a_dci4k_aspect_camset_photocap_big6_schinese"
        ]["png_exports"]["composited_png"]
        self.assertLessEqual(len(self.comp_png_bytes), 27467)
        self.assertLess(len(self.comp_png_bytes), 28672)
        self.assertLess(len(self.comp_png_bytes), 51200)
        self.assertEqual(len(self.comp_png_bytes), pe["bytes"])
        self.assertEqual(
            hashlib.sha256(self.comp_png_bytes).hexdigest(), pe["sha256"]
        )

    def test_43_round65_alpha_png_valid_1024x540_rgba_with_transparent_and_opaque_pixels(self) -> None:
        self.assertEqual(self.alpha_dims, (1024, 540))
        r65a_nz = self.summary["runs"][
            "r65a_dci4k_aspect_camset_photocap_big6_schinese"
        ]["gpe0_readback"]["nonzero_pixels"]
        self.assertEqual(self.alpha_transparent, 552960 - r65a_nz)
        self.assertGreater(self.alpha_opaque, 300000)

    def test_44_round65_composited_png_valid_1024x540_rgba_100pct_opaque(self) -> None:
        self.assertEqual(self.comp_dims, (1024, 540))
        self.assertEqual(self.comp_opaque, 1024 * 540)

    def test_45_round65_report_readme_documents_all_3_runs_and_zero_host_leaks(self) -> None:
        for token in (
            "Round 65",
            "Wave-51",
            "r65a",
            "r65b",
            "r65c",
            "38/38",
            "114/114",
            "76/76",
            "XAVC S-I DCI 4K",
            "4096",
            "24.00p",
            "4264",
            "Aspect Ratio",
            "Reg. Custom Shoot Set",
            "Recall Custom hold 1..3",
            "SONY/SETTING/FX3/CAMPR",
            "SONY/PRO/CAMERA",
            "Photo Capture",
            "Enlarge Image",
            "Slot-1",
            "346,206",
            "r65a-dci4k-aspect-camset-photocap-4ch-big6-schinese-alpha.png",
            "r65a-dci4k-aspect-camset-photocap-4ch-big6-schinese-composited.png",
        ):
            self.assertIn(token, self.r65_readme)
        for forbidden in ("/Users/", "/private/tmp/", "/var/folders/", "work/_scratch/", ":87" + "68"):
            self.assertNotIn(forbidden, self.r65_readme)

    def test_46_round65_closure_readme_section_65_present_and_accurate(self) -> None:
        self.assertIn("## 65. Round 65", self.closure_readme)
        self.assertIn("38/38 Real-HW Rounds", self.closure_readme)
        self.assertIn("114/114 Total", self.closure_readme)
        self.assertIn("76/76 PNGs", self.closure_readme)
        self.assertIn(
            "2026-11-17-round65-milestone-dci4k-aspect-recall-hold-camset-photocap-qemu",
            self.closure_readme,
        )

    def test_47_round65_38_plus_realhw_qemu_rounds_r28_to_r65_114_plus_runs_and_76_plus_pngs(self) -> None:
        png_total = 0
        rounds_found = 0
        for r in range(28, 66):
            matches = list((REPO_ROOT / "reports").glob(f"2026-??-??-round{r}-*"))
            self.assertEqual(len(matches), 1, f"Expected 1 report dir for Round {r}")
            pngs = list((matches[0] / "assets").glob("*.png"))
            self.assertGreaterEqual(len(pngs), 2, f"Expected >= 2 PNGs for Round {r}")
            for p in pngs:
                self.assertLess(p.stat().st_size, 51200, str(p))
            png_total += len(pngs)
            rounds_found += 1
        self.assertGreaterEqual(rounds_found, 38)
        self.assertGreaterEqual(png_total, 76)
        audit = self.summary["r65_milestone_dci4k_aspect_recall_hold_camset_photocap_audit"]
        self.assertGreaterEqual(audit["milestone295_qemu_rounds"], 38)
        self.assertGreaterEqual(audit["milestone295_qemu_runs"], 114)
        self.assertGreaterEqual(audit["milestone295_png_receipts"], 76)

    def test_48_round65_dual_mode_clean_room_toggle_parity_on_summary(self) -> None:
        for clean_flag in ("0", "1"):
            with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                d = json.loads(self.summary_raw)
                self.assertEqual(d["round"], 65)
                self.assertEqual(
                    d["runs"][
                        "r65a_dci4k_aspect_camset_photocap_big6_schinese"
                    ]["r65_telemetry"]["xavc_dci4k_uhd_hdmi_raw_bridge"]["xavc_dci4k_uhd_hdmi_raw_ok"],
                    1,
                )
                self.assertEqual(
                    d["runs"][
                        "r65b_wave51_dci4k_aspect_camset_photocap_guard"
                    ]["r65_telemetry"]["wave51_guard"]["fx6_pro_camera_rc"],
                    -2,
                )
                self.assertEqual(
                    d["runs"][
                        "r65c_clean_unmount_wave51_reset_h0_h3_big6_schinese"
                    ]["r65_telemetry"]["clean_unmount_wave51_h0_h3"][
                        "surfaces_h0_eq_h3"
                    ],
                    16,
                )

    def test_49_round65_r65a_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"][
            "r65a_dci4k_aspect_camset_photocap_big6_schinese"
        ]["r65_telemetry"]["wave51_init"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_50_round65_r65b_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"][
            "r65b_wave51_dci4k_aspect_camset_photocap_guard"
        ]["r65_telemetry"]["wave51_guard"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_51_round65_r65c_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"][
            "r65c_clean_unmount_wave51_reset_h0_h3_big6_schinese"
        ]["r65_telemetry"]["clean_unmount_wave51_h0_h3"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_52_round65_r65a_top_colors_transparent_plus_nonzero_equals_total_pixels(self) -> None:
        gpe = self.summary["runs"][
            "r65a_dci4k_aspect_camset_photocap_big6_schinese"
        ]["gpe0_readback"]
        color_map = {row["argb"]: row["pixels"] for row in gpe["top_colors"]}
        self.assertIn("0x00000000", color_map)
        self.assertIn("0xff000000", color_map)
        self.assertEqual(color_map["0x00000000"] + gpe["nonzero_pixels"], gpe["total_pixels"])

    def test_53_round65_r65c_top_colors_transparent_plus_nonzero_equals_total_pixels(self) -> None:
        gpe = self.summary["runs"][
            "r65c_clean_unmount_wave51_reset_h0_h3_big6_schinese"
        ]["gpe0_readback"]
        color_map = {row["argb"]: row["pixels"] for row in gpe["top_colors"]}
        self.assertIn("0x00000000", color_map)
        self.assertEqual(color_map["0x00000000"] + gpe["nonzero_pixels"], gpe["total_pixels"])

    def test_54_round65_r65a_and_r65c_wall_elapsed_and_duration_budget_sanity(self) -> None:
        r65a = self.summary["runs"][
            "r65a_dci4k_aspect_camset_photocap_big6_schinese"
        ]
        r65c = self.summary["runs"][
            "r65c_clean_unmount_wave51_reset_h0_h3_big6_schinese"
        ]
        ci_headroom = 15.0 if os.environ.get("GITHUB_ACTIONS") == "true" else 0.0
        max_wall = 240.0 + ci_headroom if os.environ.get("GITHUB_ACTIONS") == "true" else 120.0 + ci_headroom
        self.assertGreaterEqual(r65a["duration_budget_sec"], 70)
        self.assertLessEqual(r65a["duration_budget_sec"], 120)
        self.assertGreater(r65a["wall_elapsed_sec"], 50.0)
        self.assertLess(r65a["wall_elapsed_sec"], max_wall)
        self.assertGreaterEqual(r65c["duration_budget_sec"], 70)
        self.assertLessEqual(r65c["duration_budget_sec"], 120)
        self.assertGreater(r65c["wall_elapsed_sec"], 50.0)
        self.assertLess(r65c["wall_elapsed_sec"], max_wall)

    def test_55_round65_r65b_fast_early_exit_wall_elapsed_with_ci_headroom(self) -> None:
        r65b = self.summary["runs"][
            "r65b_wave51_dci4k_aspect_camset_photocap_guard"
        ]
        ci_headroom = 15.0 if os.environ.get("GITHUB_ACTIONS") == "true" else 0.0
        max_b = 45.0 + ci_headroom if os.environ.get("GITHUB_ACTIONS") == "true" else 20.0 + ci_headroom
        self.assertEqual(r65b["duration_budget_sec"], 35)
        self.assertGreater(r65b["wall_elapsed_sec"], 1.0)
        self.assertLess(r65b["wall_elapsed_sec"], max_b)
        self.assertTrue(r65b["gpe0_readback"]["skipped_stock_fx3_mode"])

    def test_56_round65_faithful_invariants_preserved_across_all_3_runs(self) -> None:
        for rk, rv in self.summary["runs"].items():
            fi = rv["faithful_invariants"]
            self.assertEqual(fi["FX6_NATIVE_FAITHFUL"], 1, rk)
            self.assertEqual(fi["subst_color"], 0, rk)
            self.assertEqual(fi["subst_image"], 0, rk)
            self.assertEqual(fi["forced_render"], 0, rk)
            self.assertEqual(fi["skipped_node"], 0, rk)
            self.assertEqual(fi["lock_bypass"], 0, rk)

    def test_57_round65_all_3_runs_stage_b_manifest_count_13(self) -> None:
        for rk, rv in self.summary["runs"].items():
            self.assertEqual(rv["stage_b"]["manifest_count"], 13, rk)
            self.assertEqual(len(rv["stage_b"]["manifest_items"]), 13, rk)

    def test_58_round65_r65c_stage_b_r65_bridges_and_zero_leak_verified(self) -> None:
        r65c_t = self.summary["runs"][
            "r65c_clean_unmount_wave51_reset_h0_h3_big6_schinese"
        ]["r65_telemetry"]
        self.assertEqual(r65c_t["xavc_dci4k_uhd_hdmi_raw_bridge"]["xavc_dci4k_uhd_hdmi_raw_ok"], 1)
        self.assertEqual(r65c_t["still_aspect_ratio_fx6_bridge"]["still_aspect_ratio_fx6_ok"], 1)
        self.assertEqual(r65c_t["recall_hold_11chk_camset_bridge"]["recall_hold_11chk_camset_ok"], 1)
        self.assertEqual(r65c_t["photocap_enlarge_slot1_bridge"]["photocap_enlarge_slot1_ok"], 1)
        self.assertEqual(r65c_t["xavc_dci4k_uhd_hdmi_raw_bridge"]["long_gop_dci4k_bypass_events"], 0)
        self.assertEqual(r65c_t["still_aspect_ratio_fx6_bridge"]["fx6_still_aspect_spoof_events"], 0)
        self.assertEqual(r65c_t["recall_hold_11chk_camset_bridge"]["movie_recall_hold_bypass_events"], 0)
        self.assertEqual(r65c_t["recall_hold_11chk_camset_bridge"]["fx6_pro_camera_spoof_events"], 0)
        self.assertEqual(r65c_t["photocap_enlarge_slot1_bridge"]["dci4k_photocap_bypass_events"], 0)
        self.assertEqual(r65c_t["photocap_enlarge_slot1_bridge"]["slot1_wave51_write_events"], 0)
        self.assertEqual(r65c_t["stage_b_bridge"]["e_nd_actuator_tx_count"], 0)

    def test_59_round65_all_3_runs_prefix_counts_include_fx6_r65(self) -> None:
        r65a_pc = self.summary["runs"][
            "r65a_dci4k_aspect_camset_photocap_big6_schinese"
        ]["prefix_counts"]
        r65b_pc = self.summary["runs"][
            "r65b_wave51_dci4k_aspect_camset_photocap_guard"
        ]["prefix_counts"]
        r65c_pc = self.summary["runs"][
            "r65c_clean_unmount_wave51_reset_h0_h3_big6_schinese"
        ]["prefix_counts"]
        self.assertGreater(r65a_pc["FX6_R65_"], 10)
        self.assertEqual(r65b_pc["FX6_R65_"], 3)
        self.assertGreater(r65c_pc["FX6_R65_"], 10)

    def test_60_round65_r65_meta_invariants_across_all_3_runs(self) -> None:
        for rk, rv in self.summary["runs"].items():
            m = rv["stage_b"]["r65"]
            self.assertEqual(m["xavc_si_dci4k_resolution"], "4096x2160", rk)
            self.assertEqual(m["xavc_si_dci4k_aspect"], "17:9", rk)
            self.assertEqual(m["xavc_si_dci4k_fw_added"], "Ver. 3.00+", rk)
            self.assertEqual(len(m["xavc_si_dci4k_fps_supported"]), 6, rk)
            self.assertTrue(m["xavc_si_dci4k_24_00p_requires_reboot_and_isolates_playback"], rk)
            self.assertEqual(m["xavc_si_dci4k_sq_fps_supported"], [1, 2, 3, 6, 12, 24, 48], rk)
            self.assertTrue(m["xavc_si_dci4k_100_120fps_rejected"], rk)
            self.assertTrue(m["long_gop_4k_uhd_only_3840x2160"], rk)
            self.assertTrue(m["dormant_8k_24p_rejected_eopnotsupp"], rk)
            self.assertEqual(m["hdmi_raw_output_resolution"], "4264x2408", rk)
            self.assertTrue(m["hdmi_raw_requires_log_and_locks_slog3"], rk)
            self.assertEqual(m["shutter_mode_angle_range_deg"], [5.6, 360.0], rk)
            self.assertEqual(m["shutter_mode_angle_frames_range"], [2, 64], rk)
            self.assertEqual(len(m["still_aspect_ratio_options_mp"]), 4, rk)
            self.assertEqual(m["still_aspect_ratio_default"], "3:2", rk)
            self.assertTrue(m["still_aspect_ratio_raw_full_3_2_with_crop_meta"], rk)
            self.assertTrue(m["apsc_s35_on_clamps_jpeg_size_l_to_m"], rk)
            self.assertFalse(m["fx6_still_aspect_ratio_present"], rk)
            self.assertEqual(len(m["reg_custom_shoot_set_hold_slots"]), 3, rk)
            self.assertEqual(m["reg_custom_shoot_set_checkbox_count"], 11, rk)
            self.assertTrue(m["reg_custom_shoot_set_still_pasm_only"], rk)
            self.assertTrue(m["reg_custom_shoot_set_excludes_self_timer"], rk)
            self.assertTrue(m["reg_custom_shoot_set_forces_hlg_still_off_on_iso_dro_hold"], rk)
            self.assertTrue(m["reg_custom_shoot_set_survives_camera_settings_reset"], rk)
            self.assertEqual(m["camera_set_memory_body_banks"], [1, 2, 3], rk)
            self.assertEqual(m["camera_set_memory_card_banks"], ["M1", "M2", "M3", "M4"], rk)
            self.assertFalse(m["fx3_sony_pro_camera_present"], rk)
            self.assertTrue(m["memory_recall_media_resets_to_slot1_on_camreset"], rk)
            self.assertEqual(m["photo_capture_mp"], {"4K": "8.3M", "HD": "2.1M"}, rk)
            self.assertEqual(m["photo_capture_file_types"], ["JPEG", "HEIF(4:2:0)", "HEIF(4:2:2)"], rk)
            self.assertEqual(m["photo_capture_dci4k_lockout_uxc_token"], "_g.uxc 0x60ce", rk)
            self.assertTrue(m["enlarge_image_still_playback_only"], rk)
            self.assertEqual(m["enlarge_initial_mag_options"], ["Standard. Mag.", "Previous Mag."], rk)
            self.assertEqual(m["enlarge_initial_pos_options"], ["Focused Position", "Center"], rk)
            self.assertTrue(m["slot1_tier0_vault_erofs"], rk)
            self.assertEqual(m["long_gop_dci4k_bypass_events"], 0, rk)
            self.assertEqual(m["fx6_still_aspect_spoof_events"], 0, rk)
            self.assertEqual(m["movie_recall_hold_bypass_events"], 0, rk)
            self.assertEqual(m["fx6_pro_camera_spoof_events"], 0, rk)
            self.assertEqual(m["dci4k_photocap_bypass_events"], 0, rk)
            self.assertEqual(m["slot1_wave51_write_events"], 0, rk)
            self.assertEqual(m["e_nd_actuator_tx_count"], 0, rk)
            self.assertEqual(m["raw_firmware_bytes_leaked"], 0, rk)

    def test_61_round65_sanitize_helper_redacts_host_paths_and_reserved_port(self) -> None:
        dirty = {
            "run_id": "test-run",
            "lang": "schinese",
            "r65_mode": "dci4k_aspect_camset_photocap_big6",
            "kernel_version": "Linux version 4.9.337-scel+",
            "kernel_bin": "/Users/fake/secret/kernel.bin",
            "dtb_bin": "/Users/fake/secret/guest.dtb",
            "build": {"tmp_build": "/private/tmp/build-123"},
            "stage_b": {"r65": {"r65_mode": "dci4k_aspect_camset_photocap_big6"}},
            "r65_telemetry": {
                "wave51_init": {"r65_init_ok": 1},
                "wave51_guard": {"r65b_ok": 1},
                "clean_unmount_wave51_h0_h3": {"r65c_ok": 1, "surfaces_h0_eq_h3": 16},
            },
            "gpe0_readback": {"nonzero_pixels": 346206},
            "png_exports": {
                "alpha_png": {
                    "path": "/Users/kafu/repo/reports/2026-11-17-round65-milestone-dci4k-aspect-recall-hold-camset-photocap-qemu/assets/a.png"
                }
            },
            "prefix_counts": {"FX6_R65_": 10},
        }
        sanitized = self.runner.sanitize_round65_summary(dirty, dirty, dirty)
        raw = json.dumps(sanitized)
        self.assertNotIn("/Users/", raw)
        self.assertNotIn("/private/tmp/", raw)
        self.assertNotIn("kernel_bin", raw)
        self.assertNotIn("dtb_bin", raw)
        self.assertIn(
            "reports/2026-11-17-round65-milestone-dci4k-aspect-recall-hold-camset-photocap-qemu/assets/a.png",
            raw,
        )

    def test_62_round65_no_stray_temp_files_or_reserved_port_in_repo(self) -> None:
        for bad_name in ("tmp", "scratch", ".worktrees"):
            self.assertFalse((REPO_ROOT / bad_name).exists(), bad_name)
        reserved_port = "87" + "68"
        self.assertNotIn(reserved_port, self.summary_raw)
        self.assertNotIn(reserved_port, self.r65_readme)

    def test_63_round65_runner_escapes_percent_in_argparse_help_and_portable_tools(self) -> None:
        self.assertIn("ArgumentParser", self.runner_src)
        self.assertNotIn("/usr/" + "bin/python3", self.runner_src)
        self.assertIn('shutil.which("zig")', self.runner_src)
        self.assertIn("FX6_SCRATCH_DIR", self.runner_src)

    def test_64_round65_test_suite_contains_at_least_66_unit_tests(self) -> None:
        methods = [m for m in dir(self) if m.startswith("test_")]
        self.assertGreaterEqual(len(methods), 66)

    def test_65_round65_dual_mode_env_flags_preserve_zero_emmc_and_clean_room_parity(self) -> None:
        for env_overrides in (
            {},
            {"FX3_CLEAN_ROOM_TEST": "1"},
            {"FX3_FX6_FORCE_CLEAN_ROOM": "1"},
        ):
            with mock.patch.dict(os.environ, env_overrides, clear=False):
                parsed = self.runner.extract_milestones(
                    "Linux version 4.9.337-scel+\n"
                    "FX6_R65_WAVE51_INIT dci4k_uhd_hdmi_raw_ok=1 still_aspect_ratio_ok=1 "
                    "recall_hold_camset_ok=1 photocap_enlarge_slot1_ok=1 r65_init_ok=1\n"
                )
                self.assertEqual(parsed["r65_telemetry"]["wave51_init"]["r65_init_ok"], 1)

    def test_66_round65_argparse_percent_safe_help_and_no_hardcoded_python3(self) -> None:
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
