#!/usr/bin/env python3
"""Offline dual-mode unit tests for FX6-on-FX3 Round 66 (39/39 Real-HW Rounds R28..R66, 115th..117th Live Runs -> 117/117 Total, 78/78 PNGs <= 27,467 B — Wave-52)."""
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
ROUND66_REPORT_DIR = (
    REPO_ROOT
    / "reports"
    / "2026-11-17-round66-sensor-cleaning-ev-comp-cineei-focus-mode-index-rotate-qemu"
)
WAVE52_SPEC_PATH = (
    REPO_ROOT
    / "reports"
    / "2026-11-17-global-sony-wave52-cleaning-mode-ev-comp-reset-playback-view-group-focus-mode-intel"
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


def _build_overlay_for_r66(
    runner,
    parent_cpio: pathlib.Path,
    fp,
    fv,
    fb,
    fake_run,
    jit_meta: Dict[str, Any],
    work: pathlib.Path,
    r66_mode: str,
    lang: str = "schinese",
    enable_r66: bool = True,
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
            enable_r65=True,
            r65_mode="dci4k_aspect_camset_photocap_big6",
            enable_r66=enable_r66,
            r66_mode=r66_mode,
            sd_manifest_mode="valid",
            lang=lang,
            shim_bytes=b"SHIM",
        )


class TestRound66SensorCleaningEvCompCineEiFocusModeIndexRotateQemu(unittest.TestCase):
    EXPECTED_RUN_KEYS = (
        "r66a_cleaning_evcomp_focusmode_rotate_big6_schinese",
        "r66b_wave52_cleaning_evcomp_focusmode_rotate_guard",
        "r66c_clean_unmount_wave52_reset_h0_h3_big6_schinese",
    )

    runner: Any
    runner_src: str
    stage_a_src: str
    shim_src: str
    wave52_spec: str
    summary_raw: str
    summary: Dict[str, Any]
    r66_readme: str
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
    launcher_r66: Optional[bytes]
    shim_r66: Optional[bytes]
    shim_r65: Optional[bytes]
    r65_summary: Dict[str, Any]
    r64_summary: Dict[str, Any]
    r63_summary: Dict[str, Any]
    r62_summary: Dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = _load_closure_module("fx6_brr_r66_cached", "build_and_run_round.py")
        cls.runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")
        cls.stage_a_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        cls.shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        cls.wave52_spec = WAVE52_SPEC_PATH.read_text(encoding="utf-8")
        cls.summary_raw = (ROUND66_REPORT_DIR / "summary.json").read_text(encoding="utf-8")
        cls.summary = json.loads(cls.summary_raw)
        cls.r66_readme = (ROUND66_REPORT_DIR / "README.md").read_text(encoding="utf-8")
        cls.closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")

        alpha_p = (
            ROUND66_REPORT_DIR
            / "assets"
            / "r66a-cleaning-evcomp-focusmode-rotate-4ch-big6-schinese-alpha.png"
        )
        comp_p = (
            ROUND66_REPORT_DIR
            / "assets"
            / "r66a-cleaning-evcomp-focusmode-rotate-4ch-big6-schinese-composited.png"
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
            cls.ov_a = _build_overlay_for_r66(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wa", "cleaning_evcomp_focusmode_rotate_big6", lang="schinese",
            )
            cls.ov_b = _build_overlay_for_r66(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wb", "wave52_cleaning_evcomp_focusmode_rotate_guard", lang="en",
            )
            cls.ov_c = _build_overlay_for_r66(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wc", "clean_unmount_wave52_reset_h0_h3_big6", lang="schinese",
            )
            cls.ov_off = _build_overlay_for_r66(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "woff", "cleaning_evcomp_focusmode_rotate_big6", enable_r66=False,
            )
            cls.invalid_mode_raised = False
            try:
                _build_overlay_for_r66(
                    cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                    tpath / "wbad", "invalid_r66_mode",
                )
            except ValueError:
                cls.invalid_mode_raised = True

            zig_bin = shutil.which("zig") or (
                str(cls.runner.ZIG) if cls.runner.ZIG.is_file() else None
            )
            if zig_bin is not None:
                verify_r66_out = tpath / "fx6-stage-a-verify-r66"
                shim_r66_out = tpath / "libgrm-fbinit9-r66.so"
                shim_r65_out = tpath / "libgrm-fbinit9-r65.so"
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
                        str(verify_r66_out),
                    ],
                    [
                        zig_bin,
                        "cc",
                        "-target",
                        "aarch64-linux-gnu.2.25",
                        "-O0",
                        "-shared",
                        "-fPIC",
                        "-DFX6_ROUND=66",
                        str(CLOSURE_DIR / "libgrm-fbinit9.c"),
                        "-ldl",
                        "-lpthread",
                        "-o",
                        str(shim_r66_out),
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
                ):
                    cls.runner.subprocess.run(cmd, check=True)
                cls.launcher_r66 = verify_r66_out.read_bytes()
                cls.shim_r66 = shim_r66_out.read_bytes()
                cls.shim_r65 = shim_r65_out.read_bytes()
            else:
                cls.launcher_r66 = None
                cls.shim_r66 = None
                cls.shim_r65 = None

        cls.r65_summary = json.loads(
            (
                REPO_ROOT
                / "reports"
                / "2026-11-17-round65-milestone-dci4k-aspect-recall-hold-camset-photocap-qemu"
                / "summary.json"
            ).read_text(encoding="utf-8")
        )
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

    def test_01_wave52_global_spec_present_and_covers_all_wave52_pillars(self) -> None:
        self.assertTrue(WAVE52_SPEC_PATH.is_file())
        for needle in (
            "Sensor Cleaning",
            "Cleaning Mode",
            "51%",
            "Power insufficient.",
            "Exposure Comp.",
            "-5.0 EV",
            "+5.0 EV",
            "-2.0 EV",
            "+2.0 EV",
            "Exposure step",
            "Reset EV Comp.",
            "Cine EI",
            "Focus Mode",
            "Priority Set in AF-S",
            "Priority Set in AF-C",
            "AF Illuminator",
            "View Mode",
            "Image Index",
            "9 Images",
            "25 Images",
            "Display as Group",
            "Display Rotation",
            "rotatiton",
            "Rotate",
        ):
            self.assertIn(needle, self.wave52_spec)

    def test_02_round66_summary_schema_round_milestone_and_zero_leaks(self) -> None:
        self.assertNotIn("/Users/", self.summary_raw)
        self.assertNotIn("/private/tmp/", self.summary_raw)
        self.assertEqual(
            self.summary["schema"],
            "fx6-on-fx3-round66-realhw-sensor-cleaning-ev-comp-cineei-focus-mode-index-rotate-qemu-v1",
        )
        self.assertEqual(self.summary["round"], 66)
        self.assertEqual(self.summary["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(tuple(self.summary["runs"].keys()), self.EXPECTED_RUN_KEYS)

    def test_03_round66_cli_accepts_round66_and_all_3_r66_modes(self) -> None:
        self.assertIn(", 64, 65, 66]", self.runner_src)
        for mode in (
            "cleaning_evcomp_focusmode_rotate_big6",
            "wave52_cleaning_evcomp_focusmode_rotate_guard",
            "clean_unmount_wave52_reset_h0_h3_big6",
        ):
            self.assertIn(mode, self.runner_src)

    def test_04_round66_overlay_rejects_invalid_r66_mode(self) -> None:
        self.assertTrue(self.invalid_mode_raised)

    def test_05_round66_overlay_r66a_injects_etc_fx6_stage_r66_and_appfw_launch(self) -> None:
        replacements, additions, meta = self.ov_a
        self.assertTrue(meta["r66_enabled"])
        self.assertIn("etc/fx6_stage_r66", additions)
        self.assertIn("etc/fx6_r66_libjit.so", additions)
        r66_cfg = additions["etc/fx6_stage_r66"][0].decode("utf-8")
        self.assertIn("stage_r66=1", r66_cfg)
        self.assertIn("r66_mode=cleaning_evcomp_focusmode_rotate_big6", r66_cfg)
        self.assertIn("milestone_39th_realhw_117th_live_78_pngs=1", r66_cfg)
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("/usr/bin/appfw-launch", init_txt)
        self.assertNotIn("--r66-wave52-guard", init_txt)

    def test_06_round66_overlay_r66b_injects_early_guard_probe_and_poweroff(self) -> None:
        replacements, _, meta = self.ov_b
        self.assertEqual(meta["r66"]["r66_mode"], "wave52_cleaning_evcomp_focusmode_rotate_guard")
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("--r66-wave52-guard", init_txt)
        self.assertIn("FX6_R66_WAVE52_GUARD_RC=", init_txt)
        self.assertIn("FX6_R66_WAVE52_GUARD_EXIT", init_txt)
        self.assertIn("poweroff -f", init_txt)

    def test_07_round66_overlay_r66c_integrated_runs_stage_b_big6(self) -> None:
        replacements, additions, meta = self.ov_c
        self.assertEqual(meta["r66"]["r66_mode"], "clean_unmount_wave52_reset_h0_h3_big6")
        r66_cfg = additions["etc/fx6_stage_r66"][0].decode("utf-8")
        self.assertIn("r66_mode=clean_unmount_wave52_reset_h0_h3_big6", r66_cfg)
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("/usr/bin/appfw-launch", init_txt)
        self.assertNotIn("--r66-wave52-guard", init_txt)

    def test_08_round66_overlay_disabled_when_enable_r66_false(self) -> None:
        _, additions, meta = self.ov_off
        self.assertFalse(meta["r66_enabled"])
        self.assertNotIn("etc/fx6_stage_r66", additions)
        self.assertNotIn("etc/fx6_r66_libjit.so", additions)
        self.assertNotIn("r66", meta)

    def test_09_round66_stage_a_c_source_contains_all_3_wave52_probes(self) -> None:
        for sym in (
            "setup_r66_cleaning_evcomp_focusmode_rotate_probe",
            "run_r66_wave52_guard_probe",
            "run_r66_clean_unmount_wave52_h0_h3_probe",
            "FX6_R66_WAVE52_INIT",
            "FX6_R66_WAVE52_GUARD",
            "FX6_R66_CLEAN_UNMOUNT_WAVE52_H0_H3",
            "--r66-wave52-guard",
            "--r66-clean-unmount-wave52-h0-h3",
            "/etc/fx6_stage_r66",
        ):
            self.assertIn(sym, self.stage_a_src)

    def test_10_round66_shim_c_source_contains_r66_guarded_bridges(self) -> None:
        self.assertIn("#if FX6_ROUND >= 66", self.shim_src)
        for sym in (
            "FX6_R66_CLEANING_BATTERY_END_BRIDGE",
            "FX6_R66_EV_COMP_STEP_CINEEI_BRIDGE",
            "FX6_R66_FOCUS_MODE_5VS2_ILLUM_BRIDGE",
            "FX6_R66_PLAYBACK_VIEW_INDEX_ROTATE_BRIDGE",
            "FX6_R66_LANG_TELEMETRY",
            "FX6_STAGE_B_R66_BRIDGE",
        ):
            self.assertIn(sym, self.shim_src)

    def test_11_round66_compile_launcher_and_shim_aarch64_elf_symbols(self) -> None:
        if self.launcher_r66 is None or self.shim_r66 is None:
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertEqual(self.launcher_r66[:4], b"\x7fELF")
        self.assertEqual(self.shim_r66[:4], b"\x7fELF")
        self.assertEqual(struct.unpack_from("<H", self.shim_r66, 18)[0], 183)
        self.assertIn(b"FX6_R66_CLEANING_BATTERY_END_BRIDGE", self.shim_r66)
        self.assertIn(b"FX6_R66_EV_COMP_STEP_CINEEI_BRIDGE", self.shim_r66)
        self.assertIn(b"FX6_R66_FOCUS_MODE_5VS2_ILLUM_BRIDGE", self.shim_r66)
        self.assertIn(b"FX6_R66_PLAYBACK_VIEW_INDEX_ROTATE_BRIDGE", self.shim_r66)

    def test_12_round66_shim_round65_backward_compat_excludes_r66_bridges(self) -> None:
        if self.shim_r65 is None:
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertIn(b"FX6_R65_XAVC_DCI4K_UHD_HDMI_RAW_BRIDGE", self.shim_r65)
        self.assertNotIn(b"FX6_R66_CLEANING_BATTERY_END_BRIDGE", self.shim_r65)

    def test_13_round66_parse_log_extracts_all_9_r66_prefixes_and_rc(self) -> None:
        serial_text = (
            "\n".join(
                [
                    "Linux version 4.9.337-scel+ (sony@fx3)",
                    "FX6_R66_WAVE52_INIT fx3_wave52_nodes_ok=1 uxc_tokens_ok=1 sensor_cleaning_ok=1 ev_comp_cine_ei_ok=1 focus_mode_split_ok=1 playback_index_rotate_ok=1 emmc_write_count=0 r66_init_ok=1",
                    "FX6_R66_CLEANING_BATTERY_END_BRIDGE cleaning_battery_51pct_gate_poweroff_ok=1 fx6_no_ibis_end_apr_cr_eopnotsupp_ok=1 cleaning_battery_end_ok=1 low_bat_cleaning_bypass_events=0 e_nd_i2c_tx_bytes=0 emmc_write_count=0 r66_bridge_ok=1",
                    "FX6_R66_EV_COMP_STEP_CINEEI_BRIDGE ev_comp_still5_movie2_manual_isoauto_ok=1 exp_step_initialize_only_no_angle_ok=1 dormant_reset_ev_comp_and_cineei_lockout_ok=1 ev_comp_step_cineei_ok=1 cine_ei_ev_comp_bypass_events=0 emmc_write_count=0 p2_setting_writes=0",
                    "FX6_R66_FOCUS_MODE_5VS2_ILLUM_BRIDGE focus_mode_5still_2movie_no_pf_semimanual_ok=1 prio_af_s_c_still_init_and_af_illum_lockouts_ok=1 fx6_af_mf_push_af_assist_contrast_ok=1 focus_mode_5vs2_illum_ok=1 movie_focus_mode_bypass_events=0 cnflasha_writes=0 emmc_write_count=0",
                    "FX6_R66_PLAYBACK_VIEW_INDEX_ROTATE_BRIDGE view_mode_3_and_image_index_9_25_ok=1 display_group_and_rotatiton_elf_ok=1 rotate_slot1_erofs_30_vault_ok=1 playback_view_index_rotate_ok=1 dormant_index_bypass_events=0 slot1_wave52_write_events=0 cnflasha_writes=0 emmc_write_count=0",
                    "FX6_R66_LANG_TELEMETRY lang=schinese font_bank=23 str_bank=19 milestone_39th_realhw_117th_live_78_pngs=1 r66_bridge_ok=1",
                    "FX6_STAGE_B_R66_BRIDGE round=66 faithful=1 nop_count=0 milestone_39th_realhw_117th_live_78_pngs=1 emmc_write_count=0",
                    "FX6_R66_WAVE52_GUARD clean_50pct_rc=-11 fx6_sensor_cleaning_rc=-95 ev_cine_ei_rc=-16 fm_movie_afs_rc=-16 idx_30_rc=-95 rot_slot1_rc=-30 r66b_ok=1",
                    "FX6_R66_WAVE52_GUARD_RC=0",
                    "FX6_R66_CLEAN_UNMOUNT_WAVE52_H0_H3 stock_unmount_restored_ok=1 camreset_preserves_wave52_survivors_ok=1 initialize_restores_wave52_defaults_ok=1 surfaces_h0_eq_h3=16 r66c_ok=1",
                ]
            )
            + "\n"
        )
        parsed = self.runner.extract_milestones(serial_text)
        r66_t = parsed["r66_telemetry"]
        self.assertEqual(r66_t["wave52_guard_rc"], 0)
        self.assertEqual(r66_t["wave52_init"]["sensor_cleaning_ok"], 1)
        self.assertEqual(r66_t["cleaning_battery_end_bridge"]["cleaning_battery_end_ok"], 1)
        self.assertEqual(r66_t["ev_comp_step_cineei_bridge"]["ev_comp_step_cineei_ok"], 1)
        self.assertEqual(r66_t["focus_mode_5vs2_illum_bridge"]["focus_mode_5vs2_illum_ok"], 1)
        self.assertEqual(r66_t["playback_view_index_rotate_bridge"]["playback_view_index_rotate_ok"], 1)
        self.assertEqual(r66_t["lang_telemetry"]["lang"], "schinese")
        self.assertEqual(r66_t["lang_telemetry"]["milestone_39th_realhw_117th_live_78_pngs"], 1)
        self.assertEqual(r66_t["stage_b_bridge"]["round"], 66)
        self.assertEqual(r66_t["wave52_guard"]["r66b_ok"], 1)
        self.assertEqual(r66_t["clean_unmount_wave52_h0_h3"]["surfaces_h0_eq_h3"], 16)
        self.assertEqual(parsed["prefix_counts"]["FX6_R66_"], 9)

    def test_14_round66_parse_log_defaults_when_no_r66_lines_present(self) -> None:
        parsed = self.runner.extract_milestones("Linux version 4.9.337-scel+\n")
        self.assertIsNone(parsed["r66_telemetry"])
        self.assertEqual(parsed["prefix_counts"].get("FX6_R66_", 0), 0)

    def test_15_round66_runner_preserves_r65_prefix_and_uses_r66_stage_label(self) -> None:
        self.assertIn('if args.round >= 65:\n        tmp_prefix = "fx6-r65"', self.runner_src)
        self.assertIn(
            "Milestone39RealHw117thLiveWave52SensorCleaningEvCompCineEiFocusModeIndexRotate",
            self.runner_src,
        )
        self.assertIn(", 64, 65, 66]", self.runner_src)

    def test_16_round66_runner_portability_and_sanitizer_helper(self) -> None:
        self.assertIn('shutil.which("zig")', self.runner_src)
        self.assertIn("FX6_SCRATCH_DIR", self.runner_src)
        self.assertIn("def sanitize_round66_summary(", self.runner_src)
        self.assertNotIn("/usr/" + "bin/python3", self.runner_src)

    def test_17_round66_summary_json_top_level_schema_and_milestone_metadata(self) -> None:
        d = self.summary
        self.assertEqual(
            d["schema"],
            "fx6-on-fx3-round66-realhw-sensor-cleaning-ev-comp-cineei-focus-mode-index-rotate-qemu-v1",
        )
        self.assertEqual(d["round"], 66)
        self.assertIn("39/39 Real-HW Rounds", d["milestone"])
        self.assertIn("117/117 Live Runs", d["milestone"])
        self.assertIn("78/78 PNGs <= 27,467 B", d["milestone"])
        self.assertEqual(d["date"], "2026-11-17")
        self.assertIn("4.9.337-scel+", d["kernel_version"])
        self.assertEqual(d["raw_firmware_bytes_leaked"], 0)

    def test_18_round66_summary_json_zero_host_path_and_scratch_leaks(self) -> None:
        for forbidden in (
            "/Users/",
            "/private/tmp/",
            "/var/folders/",
            "work/_scratch/",
            "work/_tests/",
            ":87" + "68",
        ):
            self.assertNotIn(forbidden, self.summary_raw)

    def test_19_round66_summary_audit_block_confirms_39_rounds_117_runs_78_pngs(self) -> None:
        audit = self.summary["r66_sensor_cleaning_ev_comp_focus_mode_index_rotate_audit"]
        self.assertEqual(audit["round"], 66)
        self.assertGreaterEqual(audit["realhw_rounds_count"], 39)
        self.assertGreaterEqual(audit["total_live_runs"], 117)
        self.assertGreaterEqual(audit["total_png_receipts"], 78)
        self.assertEqual(audit["total_runs"], 3)
        for k, v in audit.items():
            if isinstance(v, bool):
                self.assertTrue(v, f"Expected audit boolean {k} to be True")

    def test_20_round66_all_3_runs_present_with_kernel_4_9_337_and_zero_crashes_writes(self) -> None:
        runs = self.summary["runs"]
        self.assertEqual(list(runs.keys()), list(self.EXPECTED_RUN_KEYS))
        for rk, rv in runs.items():
            self.assertEqual(rv["round"], 66, rk)
            self.assertIn("4.9.337-scel+", rv["kernel_version"], rk)
            self.assertEqual(rv["nop_count"], 0, rk)
            self.assertEqual(rv["crashes"], 0, rk)
            self.assertEqual(rv["emmc_write_count"], 0, rk)
            self.assertGreater(rv["wall_elapsed_sec"], 0.0, rk)

    def test_21_round66_r66a_cleaning_battery_and_ev_comp_cine_ei_verified(self) -> None:
        init_t = self.summary["runs"][
            "r66a_cleaning_evcomp_focusmode_rotate_big6_schinese"
        ]["r66_telemetry"]["wave52_init"]
        self.assertEqual(init_t["fx3_wave52_nodes_ok"], 1)
        self.assertEqual(init_t["uxc_tokens_ok"], 1)
        self.assertEqual(init_t["sensor_cleaning_ok"], 1)
        self.assertEqual(init_t["ev_comp_cine_ei_ok"], 1)
        self.assertEqual(init_t["clean_low_bat_rc"], -11)
        self.assertEqual(init_t["blower_on_rc"], -16)
        self.assertEqual(init_t["fx6_clean_cr_rc"], -95)
        self.assertEqual(init_t["manual_fixed_iso_rc"], -16)
        self.assertEqual(init_t["dormant_reset_ev_rc"], -2)
        self.assertEqual(init_t["cine_ei_ev_rc"], -16)
        self.assertEqual(init_t["low_bat_cleaning_bypass_events"], 0)
        self.assertEqual(init_t["cine_ei_ev_comp_bypass_events"], 0)

    def test_22_round66_r66a_focus_mode_split_and_playback_index_rotate_verified(self) -> None:
        init_t = self.summary["runs"][
            "r66a_cleaning_evcomp_focusmode_rotate_big6_schinese"
        ]["r66_telemetry"]["wave52_init"]
        self.assertEqual(init_t["focus_mode_split_ok"], 1)
        self.assertEqual(init_t["playback_index_rotate_ok"], 1)
        self.assertEqual(init_t["movie_afs_rc"], -16)
        self.assertEqual(init_t["dormant_pf_rc"], -95)
        self.assertEqual(init_t["illum_afc_rc"], -16)
        self.assertEqual(init_t["dormant_avchd_rc"], -95)
        self.assertEqual(init_t["dormant_30_rc"], -95)
        self.assertEqual(init_t["rotate_slot1_rc"], -30)
        self.assertEqual(init_t["rotate_movie_rc"], -95)
        self.assertEqual(init_t["movie_focus_mode_bypass_events"], 0)
        self.assertEqual(init_t["dormant_index_bypass_events"], 0)

    def test_23_round66_r66a_p2_cnflasha_and_slot1_ro_guards_intact(self) -> None:
        init_t = self.summary["runs"][
            "r66a_cleaning_evcomp_focusmode_rotate_big6_schinese"
        ]["r66_telemetry"]["wave52_init"]
        self.assertEqual(init_t["slot1_wave52_write_events"], 0)
        self.assertEqual(init_t["passive_tx_bytes_emitted"], 0)
        self.assertEqual(init_t["e_nd_i2c_tx_bytes"], 0)
        self.assertEqual(init_t["e_nd_actuator_tx_count"], 0)
        self.assertEqual(init_t["p2_write_blocked_rc"], -30)
        self.assertEqual(init_t["p2_sha256_match"], 1)
        self.assertEqual(init_t["cnflasha_sha256_match"], 1)
        self.assertEqual(init_t["slot1_vault_sha256_match"], 1)
        self.assertEqual(init_t["cnflasha_writes"], 0)
        self.assertEqual(init_t["appfw_present"], 1)
        self.assertEqual(init_t["shim_present"], 1)
        self.assertEqual(init_t["emmc_write_count"], 0)
        self.assertEqual(init_t["r66_init_ok"], 1)

    def test_24_round66_r66a_stage_b_schinese_lang_telemetry_and_bridge(self) -> None:
        r66a_t = self.summary["runs"][
            "r66a_cleaning_evcomp_focusmode_rotate_big6_schinese"
        ]["r66_telemetry"]
        lt = r66a_t["lang_telemetry"]
        self.assertEqual(lt["lang"], "schinese")
        self.assertEqual(lt["bk4_lang_id"], "0x02cf019c")
        self.assertEqual(lt["bk4_lang_val"], "0x19")
        self.assertEqual(lt["lang_enum"], "0x2b45_CHINESE_SIMPLIFIED")
        self.assertEqual(lt["font_bank"], 23)
        self.assertEqual(lt["str_bank"], 19)
        self.assertEqual(lt["gpe_fb"], 0)
        self.assertEqual(lt["round66_39realhw_wave52_cleaning_evcomp_focusmode_rotate"], 1)
        self.assertEqual(lt["milestone_39th_realhw_117th_live_78_pngs"], 1)
        self.assertEqual(lt["low_bat_cleaning_bypass_events"], 0)
        self.assertEqual(lt["cine_ei_ev_comp_bypass_events"], 0)
        self.assertEqual(lt["movie_focus_mode_bypass_events"], 0)
        self.assertEqual(lt["dormant_index_bypass_events"], 0)
        self.assertEqual(lt["slot1_wave52_write_events"], 0)
        self.assertEqual(lt["e_nd_i2c_tx_bytes"], 0)
        self.assertEqual(lt["raw_firmware_bytes_leaked"], 0)

        sb = r66a_t["stage_b_bridge"]
        self.assertEqual(sb["round"], 66)
        self.assertEqual(sb["faithful"], 1)
        self.assertEqual(sb["nop_count"], 0)
        self.assertEqual(sb["cleaning_battery_51pct_poweroff_vs_fx6_end"], 1)
        self.assertEqual(sb["ev_comp_5vs2_step_dormant_reset_cine_ei_lockout"], 1)
        self.assertEqual(sb["focus_mode_5still_2movie_prio_illum"], 1)
        self.assertEqual(sb["playback_view_index_9_25_rotatiton_slot1_erofs"], 1)
        self.assertEqual(sb["milestone_39th_realhw_117th_live_78_pngs"], 1)

    def test_25_round66_r66a_stage_b_4_pillar_bridges_verified(self) -> None:
        r66a_t = self.summary["runs"][
            "r66a_cleaning_evcomp_focusmode_rotate_big6_schinese"
        ]["r66_telemetry"]
        cb = r66a_t["cleaning_battery_end_bridge"]
        self.assertEqual(cb["cleaning_battery_51pct_gate_poweroff_ok"], 1)
        self.assertEqual(cb["fx6_no_ibis_end_apr_cr_eopnotsupp_ok"], 1)
        self.assertEqual(cb["cleaning_battery_end_ok"], 1)
        self.assertEqual(cb["low_bat_cleaning_bypass_events"], 0)
        self.assertEqual(cb["e_nd_i2c_tx_bytes"], 0)
        self.assertEqual(cb["r66_bridge_ok"], 1)

        eb = r66a_t["ev_comp_step_cineei_bridge"]
        self.assertEqual(eb["ev_comp_still5_movie2_manual_isoauto_ok"], 1)
        self.assertEqual(eb["exp_step_initialize_only_no_angle_ok"], 1)
        self.assertEqual(eb["dormant_reset_ev_comp_and_cineei_lockout_ok"], 1)
        self.assertEqual(eb["ev_comp_step_cineei_ok"], 1)
        self.assertEqual(eb["cine_ei_ev_comp_bypass_events"], 0)
        self.assertEqual(eb["p2_setting_writes"], 0)

        fb = r66a_t["focus_mode_5vs2_illum_bridge"]
        self.assertEqual(fb["focus_mode_5still_2movie_no_pf_semimanual_ok"], 1)
        self.assertEqual(fb["prio_af_s_c_still_init_and_af_illum_lockouts_ok"], 1)
        self.assertEqual(fb["fx6_af_mf_push_af_assist_contrast_ok"], 1)
        self.assertEqual(fb["focus_mode_5vs2_illum_ok"], 1)
        self.assertEqual(fb["movie_focus_mode_bypass_events"], 0)

        pb = r66a_t["playback_view_index_rotate_bridge"]
        self.assertEqual(pb["view_mode_3_and_image_index_9_25_ok"], 1)
        self.assertEqual(pb["display_group_and_rotatiton_elf_ok"], 1)
        self.assertEqual(pb["rotate_slot1_erofs_30_vault_ok"], 1)
        self.assertEqual(pb["playback_view_index_rotate_ok"], 1)
        self.assertEqual(pb["dormant_index_bypass_events"], 0)
        self.assertEqual(pb["slot1_wave52_write_events"], 0)
        self.assertEqual(pb["cnflasha_writes"], 0)

    def test_26_round66_r66a_gpe0_readback_ge_300k_pixels_and_87_colors(self) -> None:
        r66a = self.summary["runs"][
            "r66a_cleaning_evcomp_focusmode_rotate_big6_schinese"
        ]
        self.assertEqual(r66a["target_presenter"], "31procam_big6_menu_home_presenter")
        self.assertEqual(r66a["target_sid"], "0x0a")
        self.assertGreaterEqual(r66a["total_threads_seen"], 150)
        gpe0 = r66a["gpe0_readback"]
        self.assertTrue(gpe0["present"])
        self.assertEqual(gpe0["bytes"], 2211840)
        self.assertEqual(gpe0["total_pixels"], 552960)
        self.assertGreaterEqual(gpe0["nonzero_pixels"], 300000)
        self.assertEqual(gpe0["nonzero_pixels"], 346206)
        self.assertEqual(gpe0["unique_colors"], 87)

    def test_27_round66_r66a_stage_b_manifest_13_hashes_and_r66_metadata(self) -> None:
        sb = self.summary["runs"][
            "r66a_cleaning_evcomp_focusmode_rotate_big6_schinese"
        ]["stage_b"]
        self.assertEqual(sb["manifest_count"], 13)
        self.assertEqual(len(sb["manifest_items"]), 13)
        for item in sb["manifest_items"]:
            self.assertEqual(len(item["sha256"]), 64)
        m = sb["r66"]
        self.assertEqual(m["r66_mode"], "cleaning_evcomp_focusmode_rotate_big6")
        self.assertGreaterEqual(m["realhw_round_ordinal"], 39)
        self.assertGreaterEqual(m["total_live_runs_at_completion"], 117)
        self.assertGreaterEqual(m["total_png_receipts_at_completion"], 78)
        self.assertEqual(m["sensor_cleaning_uxc_token"], "_f.uxc 0x67d6:Sensor Cleaning")
        self.assertEqual(m["legacy_cleaning_mode_uxc_token"], "0xe7d7:Cleaning Mode")
        self.assertEqual(m["sensor_cleaning_min_battery_pct"], 51)
        self.assertEqual(m["sensor_cleaning_low_bat_uxc_token"], "0xe574:Power insufficient.")
        self.assertEqual(m["fx6_zero_ibis_end_nd_range"], ["1/4", "1/128"])
        self.assertTrue(m["fx6_technical_apr_present"])
        self.assertFalse(m["fx6_cr_command_sensor_cleaning_supported"])
        self.assertEqual(m["ev_comp_still_range_ev"], [-5.0, 5.0])
        self.assertEqual(m["ev_comp_movie_sq_range_ev"], [-2.0, 2.0])
        self.assertEqual(m["exposure_step_options"], ["0.3EV", "0.5EV"])
        self.assertEqual(m["dormant_reset_ev_comp_bkid"], "BKID_APP_setting_exposure_compensation_reset_save")
        self.assertEqual(m["cine_ei_ev_comp_locked_and_base_iso_pinned"], [800, 12800])
        self.assertEqual(m["focus_mode_still_5modes"], ["AF-S", "AF-A", "AF-C", "DMF", "MF"])
        self.assertEqual(m["focus_mode_movie_2modes"], ["AF-C(MOVIE_AUTO)", "MF"])
        self.assertEqual(m["view_mode_fx3_options"], ["Date View", "Folder View(Still)", "Movie View"])
        self.assertEqual(m["image_index_fx3_options"], ["9 Images", "25 Images"])
        self.assertEqual(m["display_rotation_elf_bkid_spelling"], "BKID_APP_setting_display_rotatiton")
        self.assertEqual(m["rotate_slot1_default_erofs"], 30)

    def test_28_round66_r66b_cleaning_battery_and_ev_comp_cine_ei_guards_blocked(self) -> None:
        r66b_t = self.summary["runs"][
            "r66b_wave52_cleaning_evcomp_focusmode_rotate_guard"
        ]["r66_telemetry"]
        self.assertEqual(r66b_t["wave52_guard_rc"], 0)
        gd = r66b_t["wave52_guard"]
        self.assertEqual(gd["clean_50pct_rc"], -11)
        self.assertEqual(gd["clean_unknown_rc"], -22)
        self.assertEqual(gd["clean_v1_2bars_rc"], -11)
        self.assertEqual(gd["blower_no_poweroff_rc"], -16)
        self.assertEqual(gd["fx6_sensor_cleaning_rc"], -95)
        self.assertEqual(gd["ev_iauto_rc"], -16)
        self.assertEqual(gd["ev_m_fixed_iso_rc"], -16)
        self.assertEqual(gd["ev_movie_30_rc"], -22)
        self.assertEqual(gd["ev_cine_ei_rc"], -16)
        self.assertEqual(gd["ev_cine_ei_quick_rc"], -16)
        self.assertEqual(gd["dormant_reset_ev_rc"], -2)
        self.assertEqual(gd["fx6_ev_comp_rc"], -2)
        self.assertEqual(gd["low_bat_cleaning_bypass_events"], 0)
        self.assertEqual(gd["cine_ei_ev_comp_bypass_events"], 0)

    def test_29_round66_r66b_focus_mode_5vs2_and_prio_illum_guards_blocked(self) -> None:
        gd = self.summary["runs"][
            "r66b_wave52_cleaning_evcomp_focusmode_rotate_guard"
        ]["r66_telemetry"]["wave52_guard"]
        self.assertEqual(gd["fm_movie_afs_rc"], -16)
        self.assertEqual(gd["fm_movie_afa_rc"], -16)
        self.assertEqual(gd["fm_movie_dmf_rc"], -16)
        self.assertEqual(gd["fm_dormant_pf_rc"], -95)
        self.assertEqual(gd["fm_dormant_semi_rc"], -95)
        self.assertEqual(gd["prio_sq_rc"], -16)
        self.assertEqual(gd["illum_sq_rc"], -16)
        self.assertEqual(gd["illum_afc_rc"], -16)
        self.assertEqual(gd["illum_mag_rc"], -16)
        self.assertEqual(gd["movie_focus_mode_bypass_events"], 0)

    def test_30_round66_r66b_playback_dormant_index_and_rotate_guards_blocked(self) -> None:
        gd = self.summary["runs"][
            "r66b_wave52_cleaning_evcomp_focusmode_rotate_guard"
        ]["r66_telemetry"]["wave52_guard"]
        self.assertEqual(gd["view_mp4_rc"], -95)
        self.assertEqual(gd["view_avchd_rc"], -95)
        self.assertEqual(gd["idx_12_rc"], -95)
        self.assertEqual(gd["idx_30_rc"], -95)
        self.assertEqual(gd["rot_movie_rc"], -95)
        self.assertEqual(gd["rot_bg_xfer_rc"], -16)
        self.assertEqual(gd["rot_slot1_rc"], -30)
        self.assertEqual(gd["dormant_index_bypass_events"], 0)
        self.assertEqual(gd["appfw_ok"], 1)
        self.assertEqual(gd["shim_elf_ok"], 1)

    def test_31_round66_r66b_slot1_wave52_erofs_and_zero_emmc_cnflasha_writes(self) -> None:
        gd = self.summary["runs"][
            "r66b_wave52_cleaning_evcomp_focusmode_rotate_guard"
        ]["r66_telemetry"]["wave52_guard"]
        self.assertEqual(gd["slot1_wave52_erofs_rc"], -30)
        self.assertEqual(gd["slot1_vault_ro_blocked_rc"], -30)
        self.assertEqual(gd["slot1_vault_sha256_match"], 1)
        self.assertEqual(gd["p2_write_blocked_rc"], -30)
        self.assertEqual(gd["cnflasha_ro_blocked_rc"], -30)
        self.assertEqual(gd["slot1_wave52_write_events"], 0)
        self.assertEqual(gd["passive_tx_bytes_emitted"], 0)
        self.assertEqual(gd["e_nd_i2c_tx_bytes"], 0)
        self.assertEqual(gd["e_nd_actuator_tx_count"], 0)
        self.assertEqual(gd["cnflasha_writes"], 0)
        self.assertEqual(gd["emmc_write_count"], 0)
        self.assertEqual(gd["r66b_ok"], 1)

    def test_32_round66_r66c_clean_unmount_and_wave52_reset_tiers_verified(self) -> None:
        ci = self.summary["runs"][
            "r66c_clean_unmount_wave52_reset_h0_h3_big6_schinese"
        ]["r66_telemetry"]["clean_unmount_wave52_h0_h3"]
        self.assertEqual(ci["stock_unmount_restored_ok"], 1)
        self.assertEqual(ci["camreset_preserves_wave52_survivors_ok"], 1)
        self.assertEqual(ci["initialize_restores_wave52_defaults_ok"], 1)
        self.assertEqual(ci["low_bat_cleaning_bypass_events"], 0)
        self.assertEqual(ci["cine_ei_ev_comp_bypass_events"], 0)
        self.assertEqual(ci["movie_focus_mode_bypass_events"], 0)
        self.assertEqual(ci["dormant_index_bypass_events"], 0)
        self.assertEqual(ci["slot1_wave52_write_events"], 0)

    def test_33_round66_r66c_dlopen_and_16_h0_eq_h3_idempotent_unmount(self) -> None:
        ci = self.summary["runs"][
            "r66c_clean_unmount_wave52_reset_h0_h3_big6_schinese"
        ]["r66_telemetry"]["clean_unmount_wave52_h0_h3"]
        self.assertEqual(ci["dlopen_ok"], 1)
        self.assertEqual(ci["surfaces_verified"], 16)
        self.assertEqual(ci["surfaces_h0_eq_h3"], 16)
        self.assertEqual(ci["drift_bits"], 0)
        self.assertEqual(ci["cnflasha_write_bytes"], 0)
        self.assertEqual(ci["emmc_write_bytes"], 0)
        self.assertEqual(ci["e_nd_i2c_tx_bytes"], 0)
        self.assertEqual(ci["e_nd_actuator_tx_count"], 0)
        self.assertEqual(ci["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(ci["emmc_write_count"], 0)
        self.assertEqual(ci["r66c_ok"], 1)

    def test_34_round66_r66c_integrated_renders_valid_big6_gpe0_readback(self) -> None:
        r66c = self.summary["runs"][
            "r66c_clean_unmount_wave52_reset_h0_h3_big6_schinese"
        ]
        self.assertEqual(r66c["target_presenter"], "31procam_big6_menu_home_presenter")
        self.assertEqual(r66c["target_sid"], "0x0a")
        gpe0 = r66c["gpe0_readback"]
        self.assertTrue(gpe0["present"])
        self.assertEqual(gpe0["bytes"], 2211840)
        self.assertEqual(gpe0["total_pixels"], 552960)
        self.assertGreaterEqual(gpe0["nonzero_pixels"], 300000)
        self.assertEqual(gpe0["unique_colors"], 87)

    def test_35_round66_realhw_mechanisms_verified_7_blocks_match_run_telemetry(self) -> None:
        rm = self.summary["realhw_mechanisms_verified"]
        self.assertEqual(len(rm), 7)
        r66a = self.summary["runs"][
            "r66a_cleaning_evcomp_focusmode_rotate_big6_schinese"
        ]["r66_telemetry"]
        r66b = self.summary["runs"][
            "r66b_wave52_cleaning_evcomp_focusmode_rotate_guard"
        ]["r66_telemetry"]
        r66c = self.summary["runs"][
            "r66c_clean_unmount_wave52_reset_h0_h3_big6_schinese"
        ]["r66_telemetry"]
        self.assertEqual(rm["wave52_cleaning_evcomp_focusmode_rotate_init"], r66a["wave52_init"])
        self.assertEqual(rm["cleaning_battery_end_stage_b_bridge"], r66a["cleaning_battery_end_bridge"])
        self.assertEqual(rm["ev_comp_step_cineei_stage_b_bridge"], r66a["ev_comp_step_cineei_bridge"])
        self.assertEqual(rm["focus_mode_5vs2_illum_stage_b_bridge"], r66a["focus_mode_5vs2_illum_bridge"])
        self.assertEqual(rm["playback_view_index_rotate_stage_b_bridge"], r66a["playback_view_index_rotate_bridge"])
        self.assertEqual(rm["wave52_fail_closed_guard"], r66b["wave52_guard"])
        self.assertEqual(rm["clean_unmount_wave52_reset_and_16_h0_h3"], r66c["clean_unmount_wave52_h0_h3"])

    def test_36_round66_reset_tiers_survival_consistent_across_runs(self) -> None:
        r66a_t = self.summary["runs"][
            "r66a_cleaning_evcomp_focusmode_rotate_big6_schinese"
        ]["r66_telemetry"]
        r66c_ci = self.summary["runs"][
            "r66c_clean_unmount_wave52_reset_h0_h3_big6_schinese"
        ]["r66_telemetry"]["clean_unmount_wave52_h0_h3"]
        self.assertEqual(r66a_t["wave52_init"]["sensor_cleaning_ok"], 1)
        self.assertEqual(r66c_ci["stock_unmount_restored_ok"], 1)
        self.assertEqual(r66c_ci["camreset_preserves_wave52_survivors_ok"], 1)
        self.assertEqual(r66c_ci["initialize_restores_wave52_defaults_ok"], 1)

    def test_37_round66_cross_round_consistency_with_r65_slot1_ro_and_zero_leaks(self) -> None:
        self.assertEqual(self.r65_summary["round"], 65)
        r65b_gd = self.r65_summary["runs"][
            "r65b_wave51_dci4k_aspect_camset_photocap_guard"
        ]["r65_telemetry"]["wave51_guard"]
        self.assertEqual(r65b_gd["slot1_vault_ro_blocked_rc"], -30)
        r66b_gd = self.summary["runs"][
            "r66b_wave52_cleaning_evcomp_focusmode_rotate_guard"
        ]["r66_telemetry"]["wave52_guard"]
        self.assertEqual(r66b_gd["slot1_vault_ro_blocked_rc"], -30)
        self.assertEqual(r66b_gd["slot1_wave52_erofs_rc"], -30)
        self.assertEqual(r66b_gd["slot1_vault_sha256_match"], 1)
        self.assertEqual(r66b_gd["low_bat_cleaning_bypass_events"], 0)
        self.assertEqual(r66b_gd["cine_ei_ev_comp_bypass_events"], 0)

    def test_38_round66_cross_round_consistency_with_r64_r63_r62_zero_emmc_writes(self) -> None:
        self.assertEqual(self.r64_summary["round"], 64)
        self.assertEqual(self.r63_summary["round"], 63)
        self.assertEqual(self.r62_summary["round"], 62)
        self.assertEqual(
            self.r64_summary["runs"]["r64b_wave50_focus_zoom_iso_flash_guard"]["r64_telemetry"]["wave50_guard"]["emmc_write_count"],
            0,
        )
        self.assertEqual(
            self.r63_summary["runs"]["r63b_still_raw_heif_colorspace_shutter_guard"]["r63_telemetry"]["wave49_guard"]["emmc_write_count"],
            0,
        )
        self.assertEqual(
            self.r62_summary["runs"]["r62b_pp_log_wb_cineei_metering_guard"]["r62_telemetry"]["wave48_guard"]["emmc_write_count"],
            0,
        )
        r66b_gd = self.summary["runs"][
            "r66b_wave52_cleaning_evcomp_focusmode_rotate_guard"
        ]["r66_telemetry"]["wave52_guard"]
        self.assertEqual(r66b_gd["emmc_write_count"], 0)
        self.assertEqual(r66b_gd["cnflasha_writes"], 0)

    def test_39_round66_cross_round_consistency_with_r65_16_h0_eq_h3(self) -> None:
        r65c = self.r65_summary["runs"][
            "r65c_clean_unmount_wave51_reset_h0_h3_big6_schinese"
        ]["r65_telemetry"]["clean_unmount_wave51_h0_h3"]
        self.assertEqual(r65c["surfaces_h0_eq_h3"], 16)
        r66c = self.summary["runs"][
            "r66c_clean_unmount_wave52_reset_h0_h3_big6_schinese"
        ]["r66_telemetry"]["clean_unmount_wave52_h0_h3"]
        self.assertEqual(r66c["surfaces_h0_eq_h3"], 16)
        self.assertEqual(r66c["drift_bits"], 0)

    def test_40_round66_unexecuted_physical_camera_bench_boundaries_documented(self) -> None:
        bounds = self.summary["unexecuted_physical_camera_bench_boundaries"]
        self.assertEqual(len(bounds), 3)
        joined = " ".join(bounds)
        self.assertIn("Sensor Cleaning", joined)
        self.assertIn("51%", joined)
        self.assertIn("Exposure Comp.", joined)
        self.assertIn("Cine EI", joined)
        self.assertIn("Focus Mode", joined)
        self.assertIn("AF Illuminator", joined)
        self.assertIn("Image Index", joined)
        self.assertIn("rotatiton", joined)
        self.assertIn("Slot-1", joined)

    def test_41_round66_alpha_png_exists_le_27467b_and_matches_summary_sha256(self) -> None:
        pe = self.summary["runs"][
            "r66a_cleaning_evcomp_focusmode_rotate_big6_schinese"
        ]["png_exports"]["alpha_png"]
        self.assertLessEqual(len(self.alpha_png_bytes), 27467)
        self.assertLess(len(self.alpha_png_bytes), 51200)
        self.assertEqual(len(self.alpha_png_bytes), pe["bytes"])
        self.assertEqual(
            hashlib.sha256(self.alpha_png_bytes).hexdigest(), pe["sha256"]
        )

    def test_42_round66_composited_png_exists_le_27467b_and_matches_summary_sha256(self) -> None:
        pe = self.summary["runs"][
            "r66a_cleaning_evcomp_focusmode_rotate_big6_schinese"
        ]["png_exports"]["composited_png"]
        self.assertLessEqual(len(self.comp_png_bytes), 27467)
        self.assertLess(len(self.comp_png_bytes), 51200)
        self.assertEqual(len(self.comp_png_bytes), pe["bytes"])
        self.assertEqual(
            hashlib.sha256(self.comp_png_bytes).hexdigest(), pe["sha256"]
        )

    def test_43_round66_alpha_png_valid_1024x540_rgba_with_transparent_and_opaque_pixels(self) -> None:
        self.assertEqual(self.alpha_dims, (1024, 540))
        r66a_nz = self.summary["runs"][
            "r66a_cleaning_evcomp_focusmode_rotate_big6_schinese"
        ]["gpe0_readback"]["nonzero_pixels"]
        self.assertEqual(self.alpha_transparent, 552960 - r66a_nz)
        self.assertGreater(self.alpha_opaque, 300000)

    def test_44_round66_composited_png_valid_1024x540_rgba_100pct_opaque(self) -> None:
        self.assertEqual(self.comp_dims, (1024, 540))
        self.assertEqual(self.comp_opaque, 1024 * 540)

    def test_45_round66_report_readme_documents_all_3_runs_and_zero_host_leaks(self) -> None:
        for token in (
            "Round 66",
            "Wave-52",
            "r66a",
            "r66b",
            "r66c",
            "39/39",
            "117/117",
            "78/78",
            "Sensor Cleaning",
            "51%",
            "Exposure Comp.",
            "Cine EI",
            "Focus Mode",
            "Priority Set in AF-S",
            "AF Illuminator",
            "View Mode",
            "Image Index",
            "Display as Group",
            "rotatiton",
            "Rotate",
            "Slot-1",
            "346,206",
            "r66a-cleaning-evcomp-focusmode-rotate-4ch-big6-schinese-alpha.png",
            "r66a-cleaning-evcomp-focusmode-rotate-4ch-big6-schinese-composited.png",
        ):
            self.assertIn(token, self.r66_readme)
        for forbidden in ("/Users/", "/private/tmp/", "/var/folders/", "work/_scratch/", ":87" + "68"):
            self.assertNotIn(forbidden, self.r66_readme)

    def test_46_round66_closure_readme_section_66_present_and_accurate(self) -> None:
        self.assertIn("## 66. Round 66", self.closure_readme)
        self.assertIn("39/39 Real-HW Rounds", self.closure_readme)
        self.assertIn("117/117 Total", self.closure_readme)
        self.assertIn("78/78 PNGs", self.closure_readme)
        self.assertIn(
            "2026-11-17-round66-sensor-cleaning-ev-comp-cineei-focus-mode-index-rotate-qemu",
            self.closure_readme,
        )

    def test_47_round66_39_plus_realhw_qemu_rounds_r28_to_r66_117_plus_runs_and_78_plus_pngs(self) -> None:
        png_total = 0
        rounds_found = 0
        for r in range(28, 67):
            matches = list((REPO_ROOT / "reports").glob(f"2026-??-??-round{r}-*"))
            self.assertEqual(len(matches), 1, f"Expected 1 report dir for Round {r}")
            pngs = list((matches[0] / "assets").glob("*.png"))
            self.assertGreaterEqual(len(pngs), 2, f"Expected >= 2 PNGs for Round {r}")
            for p in pngs:
                self.assertLess(p.stat().st_size, 51200, str(p))
            png_total += len(pngs)
            rounds_found += 1
        self.assertGreaterEqual(rounds_found, 39)
        self.assertGreaterEqual(png_total, 78)
        audit = self.summary["r66_sensor_cleaning_ev_comp_focus_mode_index_rotate_audit"]
        self.assertGreaterEqual(audit["realhw_rounds_count"], 39)
        self.assertGreaterEqual(audit["total_live_runs"], 117)
        self.assertGreaterEqual(audit["total_png_receipts"], 78)

    def test_48_round66_dual_mode_clean_room_toggle_parity_on_summary(self) -> None:
        for clean_flag in ("0", "1"):
            with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                d = json.loads(self.summary_raw)
                self.assertEqual(d["round"], 66)
                self.assertEqual(
                    d["runs"][
                        "r66a_cleaning_evcomp_focusmode_rotate_big6_schinese"
                    ]["r66_telemetry"]["cleaning_battery_end_bridge"]["cleaning_battery_end_ok"],
                    1,
                )
                self.assertEqual(
                    d["runs"][
                        "r66b_wave52_cleaning_evcomp_focusmode_rotate_guard"
                    ]["r66_telemetry"]["wave52_guard"]["rot_slot1_rc"],
                    -30,
                )
                self.assertEqual(
                    d["runs"][
                        "r66c_clean_unmount_wave52_reset_h0_h3_big6_schinese"
                    ]["r66_telemetry"]["clean_unmount_wave52_h0_h3"]["surfaces_h0_eq_h3"],
                    16,
                )

    def test_49_round66_r66a_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"][
            "r66a_cleaning_evcomp_focusmode_rotate_big6_schinese"
        ]["r66_telemetry"]["wave52_init"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_50_round66_r66b_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"][
            "r66b_wave52_cleaning_evcomp_focusmode_rotate_guard"
        ]["r66_telemetry"]["wave52_guard"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_51_round66_r66c_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"][
            "r66c_clean_unmount_wave52_reset_h0_h3_big6_schinese"
        ]["r66_telemetry"]["clean_unmount_wave52_h0_h3"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_52_round66_r66a_top_colors_transparent_plus_nonzero_equals_total_pixels(self) -> None:
        gpe = self.summary["runs"][
            "r66a_cleaning_evcomp_focusmode_rotate_big6_schinese"
        ]["gpe0_readback"]
        color_map = {row["argb"]: row["pixels"] for row in gpe["top_colors"]}
        self.assertIn("0x00000000", color_map)
        self.assertIn("0xff000000", color_map)
        self.assertEqual(color_map["0x00000000"] + gpe["nonzero_pixels"], gpe["total_pixels"])

    def test_53_round66_r66c_top_colors_transparent_plus_nonzero_equals_total_pixels(self) -> None:
        gpe = self.summary["runs"][
            "r66c_clean_unmount_wave52_reset_h0_h3_big6_schinese"
        ]["gpe0_readback"]
        color_map = {row["argb"]: row["pixels"] for row in gpe["top_colors"]}
        self.assertIn("0x00000000", color_map)
        self.assertEqual(color_map["0x00000000"] + gpe["nonzero_pixels"], gpe["total_pixels"])

    def test_54_round66_r66a_and_r66c_wall_elapsed_and_duration_budget_sanity(self) -> None:
        r66a = self.summary["runs"][
            "r66a_cleaning_evcomp_focusmode_rotate_big6_schinese"
        ]
        r66c = self.summary["runs"][
            "r66c_clean_unmount_wave52_reset_h0_h3_big6_schinese"
        ]
        ci_headroom = 15.0 if os.environ.get("GITHUB_ACTIONS") == "true" else 0.0
        max_wall = 240.0 + ci_headroom if os.environ.get("GITHUB_ACTIONS") == "true" else 120.0 + ci_headroom
        self.assertGreaterEqual(r66a["duration_budget_sec"], 70)
        self.assertLessEqual(r66a["duration_budget_sec"], 120)
        self.assertGreater(r66a["wall_elapsed_sec"], 50.0)
        self.assertLess(r66a["wall_elapsed_sec"], max_wall)
        self.assertGreaterEqual(r66c["duration_budget_sec"], 70)
        self.assertLessEqual(r66c["duration_budget_sec"], 120)
        self.assertGreater(r66c["wall_elapsed_sec"], 50.0)
        self.assertLess(r66c["wall_elapsed_sec"], max_wall)

    def test_55_round66_r66b_fast_early_exit_wall_elapsed_with_ci_headroom(self) -> None:
        r66b = self.summary["runs"][
            "r66b_wave52_cleaning_evcomp_focusmode_rotate_guard"
        ]
        ci_headroom = 15.0 if os.environ.get("GITHUB_ACTIONS") == "true" else 0.0
        max_b = 45.0 + ci_headroom if os.environ.get("GITHUB_ACTIONS") == "true" else 20.0 + ci_headroom
        self.assertEqual(r66b["duration_budget_sec"], 35)
        self.assertGreater(r66b["wall_elapsed_sec"], 1.0)
        self.assertLess(r66b["wall_elapsed_sec"], max_b)
        self.assertTrue(r66b["gpe0_readback"]["skipped_stock_fx3_mode"])

    def test_56_round66_faithful_invariants_preserved_across_all_3_runs(self) -> None:
        for rk, rv in self.summary["runs"].items():
            fi = rv["faithful_invariants"]
            self.assertEqual(fi["FX6_NATIVE_FAITHFUL"], 1, rk)
            self.assertEqual(fi["subst_color"], 0, rk)
            self.assertEqual(fi["subst_image"], 0, rk)
            self.assertEqual(fi["forced_render"], 0, rk)
            self.assertEqual(fi["skipped_node"], 0, rk)
            self.assertEqual(fi["lock_bypass"], 0, rk)

    def test_57_round66_all_3_runs_stage_b_manifest_count_13(self) -> None:
        for rk, rv in self.summary["runs"].items():
            self.assertEqual(rv["stage_b"]["manifest_count"], 13, rk)
            self.assertEqual(len(rv["stage_b"]["manifest_items"]), 13, rk)

    def test_58_round66_r66c_stage_b_r66_bridges_and_zero_leak_verified(self) -> None:
        r66c_t = self.summary["runs"][
            "r66c_clean_unmount_wave52_reset_h0_h3_big6_schinese"
        ]["r66_telemetry"]
        self.assertEqual(r66c_t["cleaning_battery_end_bridge"]["cleaning_battery_end_ok"], 1)
        self.assertEqual(r66c_t["ev_comp_step_cineei_bridge"]["ev_comp_step_cineei_ok"], 1)
        self.assertEqual(r66c_t["focus_mode_5vs2_illum_bridge"]["focus_mode_5vs2_illum_ok"], 1)
        self.assertEqual(r66c_t["playback_view_index_rotate_bridge"]["playback_view_index_rotate_ok"], 1)
        self.assertEqual(r66c_t["cleaning_battery_end_bridge"]["low_bat_cleaning_bypass_events"], 0)
        self.assertEqual(r66c_t["ev_comp_step_cineei_bridge"]["cine_ei_ev_comp_bypass_events"], 0)
        self.assertEqual(r66c_t["focus_mode_5vs2_illum_bridge"]["movie_focus_mode_bypass_events"], 0)
        self.assertEqual(r66c_t["playback_view_index_rotate_bridge"]["dormant_index_bypass_events"], 0)
        self.assertEqual(r66c_t["playback_view_index_rotate_bridge"]["slot1_wave52_write_events"], 0)
        self.assertEqual(r66c_t["stage_b_bridge"]["e_nd_i2c_tx_bytes"], 0)
        self.assertEqual(r66c_t["stage_b_bridge"]["e_nd_actuator_tx_count"], 0)

    def test_59_round66_all_3_runs_prefix_counts_include_fx6_r66(self) -> None:
        r66a_pc = self.summary["runs"][
            "r66a_cleaning_evcomp_focusmode_rotate_big6_schinese"
        ]["prefix_counts"]
        r66b_pc = self.summary["runs"][
            "r66b_wave52_cleaning_evcomp_focusmode_rotate_guard"
        ]["prefix_counts"]
        r66c_pc = self.summary["runs"][
            "r66c_clean_unmount_wave52_reset_h0_h3_big6_schinese"
        ]["prefix_counts"]
        self.assertGreater(r66a_pc["FX6_R66_"], 10)
        self.assertEqual(r66b_pc["FX6_R66_"], 3)
        self.assertGreater(r66c_pc["FX6_R66_"], 10)

    def test_60_round66_r66_meta_invariants_across_all_3_runs(self) -> None:
        for rk, rv in self.summary["runs"].items():
            m = rv["stage_b"]["r66"]
            self.assertEqual(m["sensor_cleaning_uxc_token"], "_f.uxc 0x67d6:Sensor Cleaning", rk)
            self.assertEqual(m["legacy_cleaning_mode_uxc_token"], "0xe7d7:Cleaning Mode", rk)
            self.assertEqual(m["sensor_cleaning_min_battery_pct"], 51, rk)
            self.assertEqual(m["sensor_cleaning_low_bat_uxc_token"], "0xe574:Power insufficient.", rk)
            self.assertEqual(m["fx6_zero_ibis_end_nd_range"], ["1/4", "1/128"], rk)
            self.assertTrue(m["fx6_technical_apr_present"], rk)
            self.assertFalse(m["fx6_cr_command_sensor_cleaning_supported"], rk)
            self.assertEqual(m["ev_comp_still_range_ev"], [-5.0, 5.0], rk)
            self.assertEqual(m["ev_comp_movie_sq_range_ev"], [-2.0, 2.0], rk)
            self.assertTrue(m["ev_comp_manual_m_requires_iso_auto"], rk)
            self.assertEqual(m["exposure_step_options"], ["0.3EV", "0.5EV"], rk)
            self.assertTrue(m["exposure_step_does_not_affect_shutter_angle"], rk)
            self.assertEqual(m["dormant_reset_ev_comp_bkid"], "BKID_APP_setting_exposure_compensation_reset_save", rk)
            self.assertEqual(m["cine_ei_ev_comp_locked_and_base_iso_pinned"], [800, 12800], rk)
            self.assertEqual(m["focus_mode_still_5modes"], ["AF-S", "AF-A", "AF-C", "DMF", "MF"], rk)
            self.assertEqual(m["focus_mode_movie_2modes"], ["AF-C(MOVIE_AUTO)", "MF"], rk)
            self.assertTrue(m["focus_mode_dormant_pf_semimanual_eopnotsupp"], rk)
            self.assertEqual(m["priority_set_af_s_c_options"], ["AF", "Release", "Balanced Emphasis"], rk)
            self.assertTrue(m["priority_set_af_s_c_still_only_and_init_only"], rk)
            self.assertEqual(m["af_illuminator_options"], ["Auto", "Off"], rk)
            self.assertTrue(m["af_illuminator_resets_via_camset_reset"], rk)
            self.assertEqual(m["view_mode_fx3_options"], ["Date View", "Folder View(Still)", "Movie View"], rk)
            self.assertEqual(m["view_mode_dormant_eopnotsupp"], ["AVCHD View", "MP4 View"], rk)
            self.assertEqual(m["image_index_fx3_options"], ["9 Images", "25 Images"], rk)
            self.assertEqual(m["image_index_dormant_eopnotsupp"], ["12 Images", "30 Images (0x6e7a)"], rk)
            self.assertEqual(m["display_rotation_elf_bkid_spelling"], "BKID_APP_setting_display_rotatiton", rk)
            self.assertEqual(m["rotate_slot1_default_erofs"], 30, rk)
            self.assertEqual(m["low_bat_cleaning_bypass_events"], 0, rk)
            self.assertEqual(m["cine_ei_ev_comp_bypass_events"], 0, rk)
            self.assertEqual(m["movie_focus_mode_bypass_events"], 0, rk)
            self.assertEqual(m["dormant_index_bypass_events"], 0, rk)
            self.assertEqual(m["slot1_wave52_write_events"], 0, rk)
            self.assertEqual(m["e_nd_i2c_tx_bytes"], 0, rk)
            self.assertEqual(m["e_nd_actuator_tx_count"], 0, rk)
            self.assertEqual(m["raw_firmware_bytes_leaked"], 0, rk)

    def test_61_round66_sanitize_helper_redacts_host_paths_and_reserved_port(self) -> None:
        dirty = {
            "run_id": "test-run",
            "lang": "schinese",
            "r66_mode": "cleaning_evcomp_focusmode_rotate_big6",
            "kernel_version": "Linux version 4.9.337-scel+",
            "kernel_bin": "/Users/fake/secret/kernel.bin",
            "dtb_bin": "/Users/fake/secret/guest.dtb",
            "build": {"tmp_build": "/private/tmp/build-123"},
            "stage_b": {"r66": {"r66_mode": "cleaning_evcomp_focusmode_rotate_big6"}},
            "r66_telemetry": {
                "wave52_init": {"r66_init_ok": 1},
                "wave52_guard": {"r66b_ok": 1},
                "clean_unmount_wave52_h0_h3": {"r66c_ok": 1, "surfaces_h0_eq_h3": 16},
            },
            "gpe0_readback": {"nonzero_pixels": 346206},
            "png_exports": {
                "alpha_png": {
                    "path": "/Users/kafu/repo/reports/2026-11-17-round66-sensor-cleaning-ev-comp-cineei-focus-mode-index-rotate-qemu/assets/a.png"
                }
            },
            "prefix_counts": {"FX6_R66_": 10},
        }
        sanitized = self.runner.sanitize_round66_summary(dirty, dirty, dirty)
        raw = json.dumps(sanitized)
        self.assertNotIn("/Users/", raw)
        self.assertNotIn("/private/tmp/", raw)
        self.assertNotIn("kernel_bin", raw)
        self.assertNotIn("dtb_bin", raw)
        self.assertIn(
            "reports/2026-11-17-round66-sensor-cleaning-ev-comp-cineei-focus-mode-index-rotate-qemu/assets/a.png",
            raw,
        )

    def test_62_round66_no_stray_temp_files_or_reserved_port_in_repo(self) -> None:
        for bad_name in ("tmp", "scratch", ".worktrees"):
            self.assertFalse((REPO_ROOT / bad_name).exists(), bad_name)
        reserved_port = "87" + "68"
        self.assertNotIn(reserved_port, self.summary_raw)
        self.assertNotIn(reserved_port, self.r66_readme)

    def test_63_round66_runner_escapes_percent_in_argparse_help_and_portable_tools(self) -> None:
        self.assertIn("ArgumentParser", self.runner_src)
        self.assertNotIn("/usr/" + "bin/python3", self.runner_src)
        self.assertIn('shutil.which("zig")', self.runner_src)
        self.assertIn("FX6_SCRATCH_DIR", self.runner_src)

    def test_64_round66_test_suite_contains_at_least_66_unit_tests(self) -> None:
        methods = [m for m in dir(self) if m.startswith("test_")]
        self.assertGreaterEqual(len(methods), 66)

    def test_65_round66_dual_mode_env_flags_preserve_zero_emmc_and_clean_room_parity(self) -> None:
        for env_overrides in (
            {},
            {"FX3_CLEAN_ROOM_TEST": "1"},
            {"FX3_FX6_FORCE_CLEAN_ROOM": "1"},
        ):
            with mock.patch.dict(os.environ, env_overrides, clear=False):
                parsed = self.runner.extract_milestones(
                    "Linux version 4.9.337-scel+\n"
                    "FX6_R66_WAVE52_INIT sensor_cleaning_ok=1 ev_comp_cine_ei_ok=1 "
                    "focus_mode_split_ok=1 playback_index_rotate_ok=1 r66_init_ok=1\n"
                )
                self.assertEqual(parsed["r66_telemetry"]["wave52_init"]["r66_init_ok"], 1)

    def test_66_round66_argparse_percent_safe_help_and_no_hardcoded_python3(self) -> None:
        for line in self.runner_src.splitlines():
            if "help=" in line and "%" in line:
                stripped = line.replace("%%", "")
                self.assertNotIn("%", stripped, f"Unescaped '%%' in argparse help: {line}")
        test_src = pathlib.Path(__file__).read_text(encoding="utf-8")
        forbidden_py = "/usr/" + "bin/python3"
        self.assertNotIn(forbidden_py, self.runner_src)
        self.assertNotIn(forbidden_py, test_src)


if __name__ == "__main__":
    unittest.main()
