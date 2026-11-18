#!/usr/bin/env python3
"""Offline dual-mode unit tests for FX6-on-FX3 Round 70 Milestone (70th Round Milestone, 43/43 Real-HW Rounds R28..R70, 127th..129th Live Runs -> 129/129 Total, 86/86 PNGs <= 27,467 B — Wave-56)."""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import hashlib
import importlib.util
import json
import os
import pathlib
import shutil
import struct
import subprocess
import tempfile
import unittest
import zlib
from typing import Any, Dict, List, Optional, Tuple
from unittest import mock

TESTS_DIR = pathlib.Path(__file__).resolve().parent
CLOSURE_DIR = TESTS_DIR.parent
REPO_ROOT = CLOSURE_DIR.parent.parent
ROUND70_REPORT_DIR = (
    REPO_ROOT
    / "reports"
    / "2026-11-17-round70-milestone-dial-customize-mydial-fn12x2-liveview-lut-embed-qemu"
)
WAVE56_SPEC_PATH = (
    REPO_ROOT
    / "reports"
    / "2026-11-17-global-sony-wave56-dial-wheel-setup-mydial-fn-menu-liveview-lut-embed-intel"
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


def _build_overlay_for_r70(
    runner,
    parent_cpio: pathlib.Path,
    fp,
    fv,
    fb,
    fake_run,
    jit_meta: Dict[str, Any],
    work: pathlib.Path,
    r70_mode: str,
    lang: str = "schinese",
    enable_r70: bool = True,
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
            enable_r66=True,
            r66_mode="cleaning_evcomp_focusmode_rotate_big6",
            enable_r67=True,
            r67_mode="lens_comp_af_illum_init5_rating_big6",
            enable_r68=True,
            r68_mode="switch_vh_af_limit14_stdadj_tc_copy_big6",
            enable_r69=True,
            r69_mode="touch4_disp_flash_reset_interval_edit_big6",
            enable_r70=enable_r70,
            r70_mode=r70_mode,
            sd_manifest_mode="valid",
            lang=lang,
            shim_bytes=b"SHIM",
        )


class TestRound70MilestoneDialCustomizeMyDialFn12x2LiveViewLutEmbedQemu(unittest.TestCase):
    EXPECTED_RUN_KEYS = (
        "r70a_dial_mydial_fn12x2_liveview_lut_big6_schinese",
        "r70b_wave56_dial_mydial_fn_liveview_lut_erofs_guard",
        "r70c_clean_unmount_wave56_reset_h0_h3_big6_schinese",
    )

    runner: Any
    runner_src: str
    stage_a_src: str
    shim_src: str
    wave56_spec: str
    summary_raw: str
    summary: Dict[str, Any]
    r70_readme: str
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
    launcher_r70: Optional[bytes]
    shim_r70: Optional[bytes]
    shim_r69: Optional[bytes]
    r69_summary: Dict[str, Any]
    r68_summary: Dict[str, Any]
    r67_summary: Dict[str, Any]
    r66_summary: Dict[str, Any]
    r65_summary: Dict[str, Any]
    r64_summary: Dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = _load_closure_module("fx6_brr_r70_cached", "build_and_run_round.py")
        cls.runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")
        cls.stage_a_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        cls.shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        cls.wave56_spec = WAVE56_SPEC_PATH.read_text(encoding="utf-8")
        cls.summary_raw = (ROUND70_REPORT_DIR / "summary.json").read_text(encoding="utf-8")
        cls.summary = json.loads(cls.summary_raw)
        cls.r70_readme = (ROUND70_REPORT_DIR / "README.md").read_text(encoding="utf-8")
        cls.closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")

        alpha_p = (
            ROUND70_REPORT_DIR
            / "assets"
            / "r70a-dial-mydial-fn12x2-liveview-lut-4ch-big6-schinese-alpha.png"
        )
        comp_p = (
            ROUND70_REPORT_DIR
            / "assets"
            / "r70a-dial-mydial-fn12x2-liveview-lut-4ch-big6-schinese-composited.png"
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
            cls.ov_a = _build_overlay_for_r70(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wa", "dial_mydial_fn12x2_liveview_lut_big6", lang="schinese",
            )
            cls.ov_b = _build_overlay_for_r70(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wb", "wave56_dial_mydial_fn_liveview_lut_erofs_guard", lang="en",
            )
            cls.ov_c = _build_overlay_for_r70(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wc", "clean_unmount_wave56_reset_h0_h3_big6", lang="schinese",
            )
            cls.ov_off = _build_overlay_for_r70(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "woff", "dial_mydial_fn12x2_liveview_lut_big6", enable_r70=False,
            )
            cls.invalid_mode_raised = False
            try:
                _build_overlay_for_r70(
                    cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                    tpath / "wbad", "invalid_r70_mode",
                )
            except ValueError:
                cls.invalid_mode_raised = True

            zig_bin = shutil.which("zig") or (
                str(cls.runner.ZIG) if cls.runner.ZIG.is_file() else None
            )
            if zig_bin is not None:
                verify_r70_out = tpath / "fx6-stage-a-verify-r70"
                shim_r70_out = tpath / "libgrm-fbinit9-r70.so"
                shim_r69_out = tpath / "libgrm-fbinit9-r69.so"
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
                        str(verify_r70_out),
                    ],
                    [
                        zig_bin,
                        "cc",
                        "-target",
                        "aarch64-linux-gnu.2.25",
                        "-O0",
                        "-shared",
                        "-fPIC",
                        "-DFX6_ROUND=70",
                        str(CLOSURE_DIR / "libgrm-fbinit9.c"),
                        "-ldl",
                        "-lpthread",
                        "-o",
                        str(shim_r70_out),
                    ],
                    [
                        zig_bin,
                        "cc",
                        "-target",
                        "aarch64-linux-gnu.2.25",
                        "-O0",
                        "-shared",
                        "-fPIC",
                        "-DFX6_ROUND=69",
                        str(CLOSURE_DIR / "libgrm-fbinit9.c"),
                        "-ldl",
                        "-lpthread",
                        "-o",
                        str(shim_r69_out),
                    ],
                ):
                    cls.runner.subprocess.run(cmd, check=True)
                cls.launcher_r70 = verify_r70_out.read_bytes()
                cls.shim_r70 = shim_r70_out.read_bytes()
                cls.shim_r69 = shim_r69_out.read_bytes()
            else:
                cls.launcher_r70 = None
                cls.shim_r70 = None
                cls.shim_r69 = None

        cls.r69_summary = json.loads(
            (
                REPO_ROOT
                / "reports"
                / "2026-11-17-round69-touch-4item-disp-zero-evf-flash-reset-interval-pb-edit-erofs-qemu"
                / "summary.json"
            ).read_text(encoding="utf-8")
        )
        cls.r68_summary = json.loads(
            (
                REPO_ROOT
                / "reports"
                / "2026-11-17-round68-switch-vh-af-limit14-exp-stdadj-tc-format-copy-reverse-qemu"
                / "summary.json"
            ).read_text(encoding="utf-8")
        )
        cls.r67_summary = json.loads(
            (
                REPO_ROOT
                / "reports"
                / "2026-11-17-round67-milestone40-lens-comp-af-illuminator-init5-folder-rating-qemu"
                / "summary.json"
            ).read_text(encoding="utf-8")
        )
        cls.r66_summary = json.loads(
            (
                REPO_ROOT
                / "reports"
                / "2026-11-17-round66-sensor-cleaning-ev-comp-cineei-focus-mode-index-rotate-qemu"
                / "summary.json"
            ).read_text(encoding="utf-8")
        )
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

    def test_01_wave56_global_spec_present_and_covers_all_wave56_pillars(self) -> None:
        self.assertTrue(WAVE56_SPEC_PATH.is_file())
        for needle in (
            "Dial Customize",
            "Custom Key/Dial Set.",
            "My Dial Settings",
            "Av/Tv Rotate",
            "Function Ring(Lens)",
            "Lock Operation Parts",
            "Dial Setup",
            "Dial / Wheel Lock",
            "Rear Dial L",
            "Rear Dial R",
            "Multi Function Dial",
            "Front Dial",
            "Rear Dial",
            "Control Wheel",
            "Fn Menu Settings",
            "Live View Display Set.",
            "Live View Display",
            "Bright Monitoring",
            "Exposure Effect",
            "Frame Rate Low Limit",
            "Grid Line Display",
            "Grid Line Type",
            "Rule of 3rds Grid",
            "Square Grid",
            "Diag. + Square Grid",
            "Manage User LUTs",
            "Select LUT",
            "Embed LUT File",
            "PPLUT",
            "/Private/Sony/PRO/LUT",
            "/Sony/PRO/LUT",
            "EROFS",
        ):
            self.assertIn(needle, self.wave56_spec)

    def test_02_round70_summary_schema_round_milestone_and_zero_leaks(self) -> None:
        self.assertNotIn("/Users/", self.summary_raw)
        self.assertNotIn("/private/tmp/", self.summary_raw)
        self.assertEqual(
            self.summary["schema"],
            "fx6-on-fx3-round70-milestone-dial-customize-mydial-fn12x2-liveview-lut-embed-qemu-v1",
        )
        self.assertEqual(self.summary["round"], 70)
        self.assertIn("70th Round Milestone!", self.summary["milestone"])
        self.assertIn("43/43 Real-HW Rounds", self.summary["milestone"])
        self.assertIn("129/129 Live Runs", self.summary["milestone"])
        self.assertIn("86/86 PNGs <= 27,467 B", self.summary["milestone"])
        self.assertEqual(self.summary["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(tuple(self.summary["runs"].keys()), self.EXPECTED_RUN_KEYS)

    def test_03_round70_cli_accepts_round70_and_all_3_r70_modes(self) -> None:
        self.assertIn(", 64, 65, 66, 67, 68, 69, 70]", self.runner_src)
        for mode in (
            "dial_mydial_fn12x2_liveview_lut_big6",
            "wave56_dial_mydial_fn_liveview_lut_erofs_guard",
            "clean_unmount_wave56_reset_h0_h3_big6",
        ):
            self.assertIn(mode, self.runner_src)

    def test_04_round70_overlay_rejects_invalid_r70_mode(self) -> None:
        self.assertTrue(self.invalid_mode_raised)

    def test_05_round70_overlay_r70a_injects_etc_fx6_stage_r70_and_appfw_launch(self) -> None:
        replacements, additions, meta = self.ov_a
        self.assertTrue(meta["r70_enabled"])
        self.assertIn("etc/fx6_stage_r70", additions)
        self.assertIn("etc/fx6_r70_libjit.so", additions)
        r70_cfg = additions["etc/fx6_stage_r70"][0].decode("utf-8")
        self.assertIn("stage_r70=1", r70_cfg)
        self.assertIn("r70_mode=dial_mydial_fn12x2_liveview_lut_big6", r70_cfg)
        self.assertIn("milestone_70th_round_43rd_realhw_129th_live_86_pngs=1", r70_cfg)
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("/usr/bin/appfw-launch", init_txt)
        self.assertNotIn("--r70-wave56-guard", init_txt)

    def test_06_round70_overlay_r70b_injects_early_guard_probe_and_poweroff(self) -> None:
        replacements, _, meta = self.ov_b
        self.assertEqual(
            meta["r70"]["r70_mode"],
            "wave56_dial_mydial_fn_liveview_lut_erofs_guard",
        )
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("--r70-wave56-guard", init_txt)
        self.assertIn("FX6_R70_WAVE56_GUARD_RC=", init_txt)
        self.assertIn("FX6_R70_WAVE56_GUARD_EXIT", init_txt)
        self.assertIn("poweroff -f", init_txt)

    def test_07_round70_overlay_r70c_integrated_runs_stage_b_big6(self) -> None:
        replacements, additions, meta = self.ov_c
        self.assertEqual(meta["r70"]["r70_mode"], "clean_unmount_wave56_reset_h0_h3_big6")
        r70_cfg = additions["etc/fx6_stage_r70"][0].decode("utf-8")
        self.assertIn("r70_mode=clean_unmount_wave56_reset_h0_h3_big6", r70_cfg)
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("/usr/bin/appfw-launch", init_txt)
        self.assertNotIn("--r70-wave56-guard", init_txt)

    def test_08_round70_overlay_disabled_when_enable_r70_false(self) -> None:
        _, additions, meta = self.ov_off
        self.assertFalse(meta["r70_enabled"])
        self.assertNotIn("etc/fx6_stage_r70", additions)
        self.assertNotIn("etc/fx6_r70_libjit.so", additions)
        self.assertNotIn("r70", meta)

    def test_09_round70_stage_a_c_source_contains_all_3_wave56_probes(self) -> None:
        for sym in (
            "setup_r70_dial_mydial_fn_liveview_lut_probe",
            "run_r70_wave56_guard_probe",
            "run_r70_clean_unmount_wave56_h0_h3_probe",
            "FX6_R70_WAVE56_INIT",
            "FX6_R70_WAVE56_GUARD",
            "FX6_R70_CLEAN_UNMOUNT_WAVE56_H0_H3",
            "--r70-wave56-guard",
            "--r70-clean-unmount-wave56-h0-h3",
            "/etc/fx6_stage_r70",
        ):
            self.assertIn(sym, self.stage_a_src)

    def test_10_round70_shim_c_source_contains_r70_guarded_bridges(self) -> None:
        self.assertIn("#if FX6_ROUND >= 70", self.shim_src)
        for sym in (
            "FX6_R70_DIAL_CUSTOMIZE_DORMANT_BRIDGE",
            "FX6_R70_MYDIAL3_FN12X2_SPLIT_BRIDGE",
            "FX6_R70_LIVEVIEW_GRID_HDMI_BRIDGE",
            "FX6_R70_LUT_IMPORT_EMBED_EROFS_BRIDGE",
            "FX6_R70_LANG_TELEMETRY",
            "FX6_STAGE_B_R70_BRIDGE",
        ):
            self.assertIn(sym, self.shim_src)

    def test_11_round70_compile_launcher_and_shim_aarch64_elf_symbols(self) -> None:
        if self.launcher_r70 is None or self.shim_r70 is None:
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertEqual(self.launcher_r70[:4], b"\x7fELF")
        self.assertEqual(self.shim_r70[:4], b"\x7fELF")
        self.assertEqual(struct.unpack_from("<H", self.shim_r70, 18)[0], 183)
        self.assertIn(b"FX6_R70_DIAL_CUSTOMIZE_DORMANT_BRIDGE", self.shim_r70)
        self.assertIn(b"FX6_R70_MYDIAL3_FN12X2_SPLIT_BRIDGE", self.shim_r70)
        self.assertIn(b"FX6_R70_LIVEVIEW_GRID_HDMI_BRIDGE", self.shim_r70)
        self.assertIn(b"FX6_R70_LUT_IMPORT_EMBED_EROFS_BRIDGE", self.shim_r70)

    def test_12_round70_shim_round69_backward_compat_excludes_r70_bridges(self) -> None:
        if self.shim_r69 is None:
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertIn(b"FX6_R69_TOUCH4_DORMANT_GUARD_BRIDGE", self.shim_r69)
        self.assertNotIn(b"FX6_R70_DIAL_CUSTOMIZE_DORMANT_BRIDGE", self.shim_r69)

    def test_13_round70_parse_log_extracts_all_9_r70_prefixes_and_rc(self) -> None:
        serial_text = (
            "\n".join(
                [
                    "Linux version 4.9.337-scel+ (sony@fx3)",
                    "FX6_R70_WAVE56_INIT fx3_wave56_nodes_ok=1 uxc_tokens_ok=1 dial_tree_ok=1 mydial_fn12x2_ok=1 liveview_grid_ok=1 lut_embed_erofs_ok=1 emmc_write_count=0 r70_init_ok=1",
                    "FX6_R70_DIAL_CUSTOMIZE_DORMANT_BRIDGE dial_5item_initonly_vs_fx6_ok=1 dormant_dial_setup_lock_rear_lr_rejected_ok=1 fx6_mfd_grip_iris_nd_hold_ok=1 dial_customize_dormant_guard_ok=1 dormant_dial_bypass_events=0 emmc_write_count=0 r70_bridge_ok=1",
                    "FX6_R70_MYDIAL3_FN12X2_SPLIT_BRIDGE three_dial_mydial123_skip_lock_override_ok=1 fn_menu_12still_12movie_0x6220_guard_ok=1 fx6_status_screens_direct_menu_ok=1 mydial3_fn12x2_split_ok=1 mydial_lock_override_breach=0 fn_empty_bypass_events=0 emmc_write_count=0 p2_setting_writes=0",
                    "FX6_R70_LIVEVIEW_GRID_HDMI_BRIDGE still_liveview_3item_asymmetric_reset_ok=1 bright_monitoring_setting_effect_off_lock_ok=1 grid_3pattern_clean_hdmi_isolated_ok=1 liveview_grid_hdmi_ok=1 hdmi_clean_feed_grid_baked_pixels=0 cnflasha_writes=0 emmc_write_count=0",
                    "FX6_R70_LUT_IMPORT_EMBED_EROFS_BRIDGE manage_user_luts_1to16_ro_import_ok=1 embed_lut_container_vs_pplut14_bake_ok=1 slot1_lut_tier0_erofs30_ok=1 lut_import_embed_erofs_ok=1 external_cube_sidecar_files=0 slot1_avf_info_mutated=0 slot1_data_sector_writes=0 cnflasha_writes=0 emmc_write_count=0",
                    "FX6_R70_LANG_TELEMETRY lang=schinese font_bank=23 str_bank=19 milestone_70th_round_43rd_realhw_129th_live_86_pngs=1 r70_bridge_ok=1",
                    "FX6_STAGE_B_R70_BRIDGE round=70 faithful=1 nop_count=0 milestone_70th_round_43rd_realhw_129th_live_86_pngs=1 emmc_write_count=0",
                    "FX6_R70_WAVE56_GUARD dial_setup_rc=-95 rear_dial_r_rc=-95 fn_movie_all_notset_rc=-22 bright_mon_on_rc=-16 custom_grid_dormant_rc=-95 lut_65pt_rc=-22 slot1_embed_erofs_rc=-30 r70b_ok=1",
                    "FX6_R70_WAVE56_GUARD_RC=0",
                    "FX6_R70_CLEAN_UNMOUNT_WAVE56_H0_H3 stock_unmount_restored_ok=1 camreset_preserves_wave56_survivors_ok=1 initialize_restores_wave56_defaults_ok=1 surfaces_h0_eq_h3=16 r70c_ok=1",
                ]
            )
            + "\n"
        )
        parsed = self.runner.extract_milestones(serial_text)
        r70_t = parsed["r70_telemetry"]
        self.assertEqual(r70_t["wave56_guard_rc"], 0)
        self.assertEqual(r70_t["wave56_init"]["dial_tree_ok"], 1)
        self.assertEqual(r70_t["dial_customize_dormant_guard_bridge"]["dial_customize_dormant_guard_ok"], 1)
        self.assertEqual(r70_t["mydial3_fn12x2_split_bridge"]["mydial3_fn12x2_split_ok"], 1)
        self.assertEqual(r70_t["liveview_grid_hdmi_bridge"]["liveview_grid_hdmi_ok"], 1)
        self.assertEqual(r70_t["lut_import_embed_erofs_bridge"]["lut_import_embed_erofs_ok"], 1)
        self.assertEqual(r70_t["lang_telemetry"]["lang"], "schinese")
        self.assertEqual(r70_t["lang_telemetry"]["milestone_70th_round_43rd_realhw_129th_live_86_pngs"], 1)
        self.assertEqual(r70_t["stage_b_bridge"]["round"], 70)
        self.assertEqual(r70_t["wave56_guard"]["r70b_ok"], 1)
        self.assertEqual(r70_t["clean_unmount_wave56_h0_h3"]["surfaces_h0_eq_h3"], 16)
        self.assertEqual(parsed["prefix_counts"]["FX6_R70_"], 9)

    def test_14_round70_parse_log_defaults_when_no_r70_lines_present(self) -> None:
        parsed = self.runner.extract_milestones("Linux version 4.9.337-scel+\n")
        self.assertIsNone(parsed["r70_telemetry"])
        self.assertEqual(parsed["prefix_counts"].get("FX6_R70_", 0), 0)

    def test_15_round70_runner_preserves_r69_prefix_and_uses_r70_stage_label(self) -> None:
        self.assertIn('if args.round >= 69:\n        tmp_prefix = "fx6-r69"', self.runner_src)
        self.assertIn('if args.round >= 70:\n        tmp_prefix = "fx6-r70"', self.runner_src)
        self.assertIn(
            "Milestone70thRound43RealHw129thLiveWave56DialCustomizeMyDialFn12x2LiveViewLutEmbedErofs",
            self.runner_src,
        )
        self.assertIn(", 64, 65, 66, 67, 68, 69, 70]", self.runner_src)

    def test_16_round70_runner_portability_and_sanitizer_helper(self) -> None:
        self.assertIn('shutil.which("zig")', self.runner_src)
        self.assertIn("FX6_SCRATCH_DIR", self.runner_src)
        self.assertIn("def sanitize_round70_summary(", self.runner_src)
        self.assertNotIn("/usr/" + "bin/python3", self.runner_src)

    def test_17_round70_summary_json_top_level_schema_and_milestone_metadata(self) -> None:
        d = self.summary
        self.assertEqual(
            d["schema"],
            "fx6-on-fx3-round70-milestone-dial-customize-mydial-fn12x2-liveview-lut-embed-qemu-v1",
        )
        self.assertEqual(d["round"], 70)
        self.assertIn("70th Round Milestone!", d["milestone"])
        self.assertIn("43/43 Real-HW Rounds", d["milestone"])
        self.assertIn("129/129 Live Runs", d["milestone"])
        self.assertIn("86/86 PNGs <= 27,467 B", d["milestone"])
        self.assertEqual(d["date"], "2026-11-17")
        self.assertIn("4.9.337-scel+", d["kernel_version"])
        self.assertEqual(d["raw_firmware_bytes_leaked"], 0)

    def test_18_round70_summary_json_zero_host_path_and_scratch_leaks(self) -> None:
        for forbidden in (
            "/Users/",
            "/private/tmp/",
            "/var/folders/",
            "work/_scratch/",
            "work/_tests/",
            ":87" + "68",
        ):
            self.assertNotIn(forbidden, self.summary_raw)

    def test_19_round70_summary_audit_block_confirms_43_rounds_129_runs_86_pngs(self) -> None:
        audit = self.summary["r70_dial_customize_mydial_fn12x2_liveview_lut_embed_audit"]
        self.assertEqual(audit["round"], 70)
        self.assertGreaterEqual(audit["realhw_rounds_count"], 43)
        self.assertGreaterEqual(audit["total_live_runs"], 129)
        self.assertGreaterEqual(audit["total_png_receipts"], 86)
        self.assertGreaterEqual(audit["milestone324_qemu_rounds"], 43)
        self.assertGreaterEqual(audit["milestone324_qemu_runs"], 129)
        self.assertGreaterEqual(audit["milestone324_png_receipts"], 86)
        self.assertEqual(audit["total_runs"], 3)
        for k, v in audit.items():
            if isinstance(v, bool):
                self.assertTrue(v, f"Expected audit boolean {k} to be True")

    def test_20_round70_all_3_runs_present_with_kernel_4_9_337_and_zero_crashes_writes(self) -> None:
        runs = self.summary["runs"]
        self.assertEqual(list(runs.keys()), list(self.EXPECTED_RUN_KEYS))
        for rk, rv in runs.items():
            self.assertEqual(rv["round"], 70, rk)
            self.assertIn("4.9.337-scel+", rv["kernel_version"], rk)
            self.assertEqual(rv["nop_count"], 0, rk)
            self.assertEqual(rv["crashes"], 0, rk)
            self.assertEqual(rv["emmc_write_count"], 0, rk)
            self.assertGreater(rv["wall_elapsed_sec"], 0.0, rk)

    def test_21_round70_r70a_dial_customize_5item_and_dormant_dial_setup_lock_rear_lr_verified(self) -> None:
        init_t = self.summary["runs"][
            "r70a_dial_mydial_fn12x2_liveview_lut_big6_schinese"
        ]["r70_telemetry"]["wave56_init"]
        self.assertEqual(init_t["fx3_wave56_nodes_ok"], 1)
        self.assertEqual(init_t["uxc_tokens_ok"], 1)
        self.assertEqual(init_t["dial_tree_ok"], 1)
        self.assertEqual(init_t["dormant_dial_setup_rc"], -95)
        self.assertEqual(init_t["dormant_dial_wheel_lock_rc"], -95)
        self.assertEqual(init_t["dormant_rear_dial_r_rc"], -95)
        self.assertEqual(init_t["func_ring_invalid_rc"], -22)
        self.assertEqual(init_t["dormant_dial_bypass_events"], 0)

    def test_22_round70_r70a_mydial_fn12x2_liveview_grid_lut_embed_erofs_verified(self) -> None:
        init_t = self.summary["runs"][
            "r70a_dial_mydial_fn12x2_liveview_lut_big6_schinese"
        ]["r70_telemetry"]["wave56_init"]
        self.assertEqual(init_t["mydial_fn12x2_ok"], 1)
        self.assertEqual(init_t["liveview_grid_ok"], 1)
        self.assertEqual(init_t["lut_embed_erofs_ok"], 1)
        self.assertEqual(init_t["fn_all_notset_rc"], -22)
        self.assertEqual(init_t["bright_mon_lock_rc"], -16)
        self.assertEqual(init_t["lv_movie_ebusy_rc"], -16)
        self.assertEqual(init_t["slot1_mkdir_erofs_rc"], -30)
        self.assertEqual(init_t["lut_oob_rc"], -22)
        self.assertEqual(init_t["slot1_embed_erofs_rc"], -30)
        self.assertEqual(init_t["slot1_pplut_erofs_rc"], -30)
        self.assertEqual(init_t["mydial_lock_override_breach"], 0)
        self.assertEqual(init_t["fn_empty_bypass_events"], 0)
        self.assertEqual(init_t["hdmi_clean_feed_grid_baked_pixels"], 0)
        self.assertEqual(init_t["external_cube_sidecar_files"], 0)

    def test_23_round70_r70a_p2_cnflasha_and_slot1_ro_guards_intact(self) -> None:
        init_t = self.summary["runs"][
            "r70a_dial_mydial_fn12x2_liveview_lut_big6_schinese"
        ]["r70_telemetry"]["wave56_init"]
        self.assertEqual(init_t["p2_write_blocked_rc"], -30)
        self.assertEqual(init_t["p2_sha256_match"], 1)
        self.assertEqual(init_t["cnflasha_sha256_match"], 1)
        self.assertEqual(init_t["slot1_vault_sha256_match"], 1)
        self.assertEqual(init_t["slot1_avf_info_mutated"], 0)
        self.assertEqual(init_t["slot1_data_sector_writes"], 0)
        self.assertEqual(init_t["passive_tx_bytes_emitted"], 0)
        self.assertEqual(init_t["e_nd_actuator_tx_count"], 0)
        self.assertEqual(init_t["cnflasha_writes"], 0)
        self.assertEqual(init_t["appfw_present"], 1)
        self.assertEqual(init_t["shim_present"], 1)
        self.assertEqual(init_t["emmc_write_count"], 0)
        self.assertEqual(init_t["r70_init_ok"], 1)

    def test_24_round70_r70a_stage_b_schinese_lang_telemetry_and_bridge(self) -> None:
        r70a_t = self.summary["runs"][
            "r70a_dial_mydial_fn12x2_liveview_lut_big6_schinese"
        ]["r70_telemetry"]
        lt = r70a_t["lang_telemetry"]
        self.assertEqual(lt["lang"], "schinese")
        self.assertEqual(lt["bk4_lang_id"], "0x02cf019c")
        self.assertEqual(lt["bk4_lang_val"], "0x19")
        self.assertEqual(lt["lang_enum"], "0x2b45_CHINESE_SIMPLIFIED")
        self.assertEqual(lt["font_bank"], 23)
        self.assertEqual(lt["str_bank"], 19)
        self.assertEqual(lt["gpe_fb"], 0)
        self.assertEqual(lt["round70_43realhw_wave56_dial_mydial_fn12x2_liveview_lut_embed_erofs"], 1)
        self.assertEqual(lt["milestone_70th_round_43rd_realhw_129th_live_86_pngs"], 1)
        self.assertEqual(lt["dormant_dial_bypass_events"], 0)
        self.assertEqual(lt["mydial_lock_override_breach"], 0)
        self.assertEqual(lt["fn_empty_bypass_events"], 0)
        self.assertEqual(lt["hdmi_clean_feed_grid_baked_pixels"], 0)
        self.assertEqual(lt["external_cube_sidecar_files"], 0)
        self.assertEqual(lt["slot1_avf_info_mutated"], 0)
        self.assertEqual(lt["slot1_data_sector_writes"], 0)
        self.assertEqual(lt["raw_firmware_bytes_leaked"], 0)

        sb = r70a_t["stage_b_bridge"]
        self.assertEqual(sb["round"], 70)
        self.assertEqual(sb["faithful"], 1)
        self.assertEqual(sb["nop_count"], 0)
        self.assertEqual(sb["dial5_initonly_vs_dormant_rear_lr"], 1)
        self.assertEqual(sb["mydial3_lock_override_fn12x2_split"], 1)
        self.assertEqual(sb["liveview_3item_asymmetric_reset_grid3_clean_hdmi"], 1)
        self.assertEqual(sb["userlut16_ro_embed_vs_pplut4_erofs30"], 1)
        self.assertEqual(sb["milestone_70th_round_43rd_realhw_129th_live_86_pngs"], 1)

    def test_25_round70_r70a_stage_b_4_pillar_bridges_verified(self) -> None:
        r70a_t = self.summary["runs"][
            "r70a_dial_mydial_fn12x2_liveview_lut_big6_schinese"
        ]["r70_telemetry"]
        pb1 = r70a_t["dial_customize_dormant_guard_bridge"]
        self.assertEqual(pb1["dial_5item_initonly_vs_fx6_ok"], 1)
        self.assertEqual(pb1["dormant_dial_setup_lock_rear_lr_rejected_ok"], 1)
        self.assertEqual(pb1["fx6_mfd_grip_iris_nd_hold_ok"], 1)
        self.assertEqual(pb1["dial_customize_dormant_guard_ok"], 1)
        self.assertEqual(pb1["dormant_dial_bypass_events"], 0)
        self.assertEqual(pb1["r70_bridge_ok"], 1)

        pb2 = r70a_t["mydial3_fn12x2_split_bridge"]
        self.assertEqual(pb2["three_dial_mydial123_skip_lock_override_ok"], 1)
        self.assertEqual(pb2["fn_menu_12still_12movie_0x6220_guard_ok"], 1)
        self.assertEqual(pb2["fx6_status_screens_direct_menu_ok"], 1)
        self.assertEqual(pb2["mydial3_fn12x2_split_ok"], 1)
        self.assertEqual(pb2["mydial_lock_override_breach"], 0)
        self.assertEqual(pb2["fn_empty_bypass_events"], 0)
        self.assertEqual(pb2["p2_setting_writes"], 0)

        pb3 = r70a_t["liveview_grid_hdmi_bridge"]
        self.assertEqual(pb3["still_liveview_3item_asymmetric_reset_ok"], 1)
        self.assertEqual(pb3["bright_monitoring_setting_effect_off_lock_ok"], 1)
        self.assertEqual(pb3["grid_3pattern_clean_hdmi_isolated_ok"], 1)
        self.assertEqual(pb3["liveview_grid_hdmi_ok"], 1)
        self.assertEqual(pb3["hdmi_clean_feed_grid_baked_pixels"], 0)
        self.assertEqual(pb3["cnflasha_writes"], 0)

        pb4 = r70a_t["lut_import_embed_erofs_bridge"]
        self.assertEqual(pb4["manage_user_luts_1to16_ro_import_ok"], 1)
        self.assertEqual(pb4["embed_lut_container_vs_pplut14_bake_ok"], 1)
        self.assertEqual(pb4["slot1_lut_tier0_erofs30_ok"], 1)
        self.assertEqual(pb4["lut_import_embed_erofs_ok"], 1)
        self.assertEqual(pb4["external_cube_sidecar_files"], 0)
        self.assertEqual(pb4["slot1_avf_info_mutated"], 0)
        self.assertEqual(pb4["slot1_data_sector_writes"], 0)
        self.assertEqual(pb4["cnflasha_writes"], 0)

    def test_26_round70_r70a_gpe0_readback_ge_300k_pixels_and_87_colors(self) -> None:
        r70a = self.summary["runs"][
            "r70a_dial_mydial_fn12x2_liveview_lut_big6_schinese"
        ]
        self.assertEqual(r70a["target_presenter"], "31procam_big6_menu_home_presenter")
        self.assertEqual(r70a["target_sid"], "0x0a")
        self.assertGreaterEqual(r70a["total_threads_seen"], 149)
        gpe0 = r70a["gpe0_readback"]
        self.assertTrue(gpe0["present"])
        self.assertEqual(gpe0["bytes"], 2211840)
        self.assertEqual(gpe0["total_pixels"], 552960)
        self.assertGreaterEqual(gpe0["nonzero_pixels"], 300000)
        self.assertEqual(gpe0["nonzero_pixels"], 346206)
        self.assertEqual(gpe0["unique_colors"], 87)

    def test_27_round70_r70a_stage_b_manifest_13_hashes_and_r70_metadata(self) -> None:
        sb = self.summary["runs"][
            "r70a_dial_mydial_fn12x2_liveview_lut_big6_schinese"
        ]["stage_b"]
        self.assertEqual(sb["manifest_count"], 13)
        self.assertEqual(len(sb["manifest_items"]), 13)
        for item in sb["manifest_items"]:
            self.assertEqual(len(item["sha256"]), 64)
        m = sb["r70"]
        self.assertEqual(m["r70_mode"], "dial_mydial_fn12x2_liveview_lut_big6")
        self.assertEqual(m["milestone_round_ordinal"], 70)
        self.assertEqual(m["realhw_round_ordinal"], 43)
        self.assertEqual(m["total_live_runs_at_completion"], 129)
        self.assertEqual(m["total_png_receipts_at_completion"], 86)
        self.assertEqual(len(m["dial_customize_5_items_initialize_only"]), 5)
        self.assertEqual(m["dial_dormant_rejected_eopnotsupp"], 95)
        self.assertEqual(len(m["dial_dormant_items"]), 5)
        self.assertEqual(len(m["physical_3_dials"]), 3)
        self.assertTrue(m["mydial_auto_skip_empty_and_lock_override"])
        self.assertEqual(m["fn_menu_12plus12_split"]["still_slots"], 12)
        self.assertEqual(m["fn_menu_12plus12_split"]["movie_slots"], 12)
        self.assertEqual(m["fn_menu_12plus12_split"]["all_empty_prompt_0x6220_einval"], -22)
        lv = m["live_view_display_set_still_only_asymmetric_reset"]
        self.assertEqual(len(lv["initialize_only_items"]), 2)
        self.assertIn("Frame Rate Low Limit", lv["camera_settings_reset_only_item"])
        self.assertEqual(len(m["grid_line_3_patterns_clean_hdmi_isolated"]), 3)
        lut = m["user_lut_workflow"]
        self.assertEqual(lut["sdxc_lut_dir"], "/Private/Sony/PRO/LUT")
        self.assertEqual(lut["cfexpress_lut_dir"], "/Sony/PRO/LUT")
        self.assertEqual(lut["import_read_only_slot1_writes"], 0)
        self.assertEqual(m["slot1_lut_tier0_erofs"], 30)

    def test_28_round70_r70b_dial_customize_and_dormant_rear_lr_guards_blocked(self) -> None:
        r70b_t = self.summary["runs"][
            "r70b_wave56_dial_mydial_fn_liveview_lut_erofs_guard"
        ]["r70_telemetry"]
        self.assertEqual(r70b_t["wave56_guard_rc"], 0)
        gd = r70b_t["wave56_guard"]
        self.assertEqual(gd["dial_setup_rc"], -95)
        self.assertEqual(gd["dial_wheel_setup_rc"], -95)
        self.assertEqual(gd["dial_wheel_lock_rc"], -95)
        self.assertEqual(gd["rear_dial_l_rc"], -95)
        self.assertEqual(gd["rear_dial_r_rc"], -95)
        self.assertEqual(gd["func_ring_invalid_rc"], -22)
        self.assertEqual(gd["fx6_avtv_rc"], -2)
        self.assertEqual(gd["fx6_lock_rc"], -2)
        self.assertEqual(gd["fx6_mfd_ok_rc"], 0)
        self.assertEqual(gd["dormant_dial_bypass_events"], 0)

    def test_29_round70_r70b_mydial_empty_fn_0x6220_and_fx6_guards_blocked(self) -> None:
        gd = self.summary["runs"][
            "r70b_wave56_dial_mydial_fn_liveview_lut_erofs_guard"
        ]["r70_telemetry"]["wave56_guard"]
        self.assertEqual(gd["mydial_empty_hold_rc"], -22)
        self.assertEqual(gd["fn_movie_all_notset_rc"], -22)
        self.assertEqual(gd["fn_slot_oob_rc"], -22)
        self.assertEqual(gd["fx6_mydial_rc"], -2)
        self.assertEqual(gd["fx6_fn_rc"], -2)
        self.assertEqual(gd["fx6_direct_menu_ok_rc"], 0)
        self.assertEqual(gd["mydial_lock_override_breach"], 0)
        self.assertEqual(gd["fn_empty_bypass_events"], 0)

    def test_30_round70_r70b_liveview_sq_bright_mon_and_dormant_grid_guards(self) -> None:
        gd = self.summary["runs"][
            "r70b_wave56_dial_mydial_fn_liveview_lut_erofs_guard"
        ]["r70_telemetry"]["wave56_guard"]
        self.assertEqual(gd["sq_lv_disp_rc"], -16)
        self.assertEqual(gd["sq_exp_eff_rc"], -16)
        self.assertEqual(gd["sq_fr_low_rc"], -16)
        self.assertEqual(gd["bright_mon_on_rc"], -16)
        self.assertEqual(gd["grid_oob_rc"], -22)
        self.assertEqual(gd["custom_grid_dormant_rc"], -95)
        self.assertEqual(gd["golden_grid_dormant_rc"], -95)
        self.assertEqual(gd["fx6_marker_ok_rc"], 0)
        self.assertEqual(gd["hdmi_clean_feed_grid_baked_pixels"], 0)

    def test_31_round70_r70b_lut_oob_sdhc_embed_and_slot1_erofs_firewall(self) -> None:
        gd = self.summary["runs"][
            "r70b_wave56_dial_mydial_fn_liveview_lut_erofs_guard"
        ]["r70_telemetry"]["wave56_guard"]
        self.assertEqual(gd["lut_slot17_rc"], -22)
        self.assertEqual(gd["lut_name64_rc"], -22)
        self.assertEqual(gd["lut_65pt_rc"], -22)
        self.assertEqual(gd["lut_bad_path_rc"], -2)
        self.assertEqual(gd["sdhc_embed_locked_rc"], -16)
        self.assertEqual(gd["pplut_unimported_rc"], -2)
        self.assertEqual(gd["slot1_mkdir_erofs_rc"], -30)
        self.assertEqual(gd["slot1_embed_erofs_rc"], -30)
        self.assertEqual(gd["slot1_pplut_erofs_rc"], -30)
        self.assertEqual(gd["slot1_wave56_erofs_rc"], -30)
        self.assertEqual(gd["slot1_avf_ro_blocked_rc"], -30)
        self.assertEqual(gd["slot1_vault_sha256_match"], 1)
        self.assertEqual(gd["p2_write_blocked_rc"], -30)
        self.assertEqual(gd["cnflasha_ro_blocked_rc"], -30)
        self.assertEqual(gd["external_cube_sidecar_files"], 0)
        self.assertEqual(gd["slot1_avf_info_mutated"], 0)
        self.assertEqual(gd["slot1_data_sector_writes"], 0)
        self.assertEqual(gd["passive_tx_bytes_emitted"], 0)
        self.assertEqual(gd["e_nd_actuator_tx_count"], 0)
        self.assertEqual(gd["appfw_ok"], 1)
        self.assertEqual(gd["shim_elf_ok"], 1)
        self.assertEqual(gd["cnflasha_writes"], 0)
        self.assertEqual(gd["emmc_write_count"], 0)
        self.assertEqual(gd["r70b_ok"], 1)

    def test_32_round70_r70c_clean_unmount_and_wave56_asymmetric_reset_tiers(self) -> None:
        ci = self.summary["runs"][
            "r70c_clean_unmount_wave56_reset_h0_h3_big6_schinese"
        ]["r70_telemetry"]["clean_unmount_wave56_h0_h3"]
        self.assertEqual(ci["stock_unmount_restored_ok"], 1)
        self.assertEqual(ci["camreset_preserves_wave56_survivors_ok"], 1)
        self.assertEqual(ci["initialize_restores_wave56_defaults_ok"], 1)
        self.assertEqual(ci["dormant_dial_bypass_events"], 0)
        self.assertEqual(ci["mydial_lock_override_breach"], 0)
        self.assertEqual(ci["fn_empty_bypass_events"], 0)
        self.assertEqual(ci["hdmi_clean_feed_grid_baked_pixels"], 0)
        self.assertEqual(ci["external_cube_sidecar_files"], 0)
        self.assertEqual(ci["slot1_avf_info_mutated"], 0)
        self.assertEqual(ci["slot1_data_sector_writes"], 0)

    def test_33_round70_r70c_dlopen_and_16_h0_eq_h3_idempotent_unmount(self) -> None:
        ci = self.summary["runs"][
            "r70c_clean_unmount_wave56_reset_h0_h3_big6_schinese"
        ]["r70_telemetry"]["clean_unmount_wave56_h0_h3"]
        self.assertEqual(ci["dlopen_ok"], 1)
        self.assertEqual(ci["surfaces_verified"], 16)
        self.assertEqual(ci["surfaces_h0_eq_h3"], 16)
        self.assertEqual(ci["drift_bits"], 0)
        self.assertEqual(ci["slot1_vault_ro_blocked_rc"], -30)
        self.assertEqual(ci["slot1_vault_sha256_match"], 1)
        self.assertEqual(ci["p2_write_blocked_rc"], -30)
        self.assertEqual(ci["cnflasha_ro_blocked_rc"], -30)
        self.assertEqual(ci["cnflasha_write_bytes"], 0)
        self.assertEqual(ci["emmc_write_bytes"], 0)
        self.assertEqual(ci["e_nd_actuator_tx_count"], 0)
        self.assertEqual(ci["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(ci["emmc_write_count"], 0)
        self.assertEqual(ci["r70c_ok"], 1)

    def test_34_round70_r70c_integrated_renders_valid_big6_gpe0_readback(self) -> None:
        r70c = self.summary["runs"][
            "r70c_clean_unmount_wave56_reset_h0_h3_big6_schinese"
        ]
        self.assertEqual(r70c["target_presenter"], "31procam_big6_menu_home_presenter")
        self.assertEqual(r70c["target_sid"], "0x0a")
        gpe0 = r70c["gpe0_readback"]
        self.assertTrue(gpe0["present"])
        self.assertEqual(gpe0["bytes"], 2211840)
        self.assertEqual(gpe0["total_pixels"], 552960)
        self.assertGreaterEqual(gpe0["nonzero_pixels"], 300000)
        self.assertEqual(gpe0["nonzero_pixels"], 346686)
        self.assertEqual(gpe0["unique_colors"], 87)

    def test_35_round70_realhw_mechanisms_verified_7_blocks_match_run_telemetry(self) -> None:
        rm = self.summary["realhw_mechanisms_verified"]
        self.assertEqual(len(rm), 7)
        r70a = self.summary["runs"][
            "r70a_dial_mydial_fn12x2_liveview_lut_big6_schinese"
        ]["r70_telemetry"]
        r70b = self.summary["runs"][
            "r70b_wave56_dial_mydial_fn_liveview_lut_erofs_guard"
        ]["r70_telemetry"]
        r70c = self.summary["runs"][
            "r70c_clean_unmount_wave56_reset_h0_h3_big6_schinese"
        ]["r70_telemetry"]
        self.assertEqual(rm["wave56_dial_mydial_fn_liveview_lut_init"], r70a["wave56_init"])
        self.assertEqual(rm["dial_customize_dormant_guard_stage_b_bridge"], r70a["dial_customize_dormant_guard_bridge"])
        self.assertEqual(rm["mydial3_fn12x2_split_stage_b_bridge"], r70a["mydial3_fn12x2_split_bridge"])
        self.assertEqual(rm["liveview_grid_hdmi_stage_b_bridge"], r70a["liveview_grid_hdmi_bridge"])
        self.assertEqual(rm["lut_import_embed_erofs_stage_b_bridge"], r70a["lut_import_embed_erofs_bridge"])
        self.assertEqual(rm["wave56_fail_closed_guard"], r70b["wave56_guard"])
        self.assertEqual(rm["clean_unmount_wave56_reset_and_16_h0_h3"], r70c["clean_unmount_wave56_h0_h3"])

    def test_36_round70_reset_tiers_survival_consistent_across_runs(self) -> None:
        r70a_t = self.summary["runs"][
            "r70a_dial_mydial_fn12x2_liveview_lut_big6_schinese"
        ]["r70_telemetry"]
        r70c_ci = self.summary["runs"][
            "r70c_clean_unmount_wave56_reset_h0_h3_big6_schinese"
        ]["r70_telemetry"]["clean_unmount_wave56_h0_h3"]
        self.assertEqual(r70a_t["wave56_init"]["dial_tree_ok"], 1)
        self.assertEqual(r70a_t["wave56_init"]["lut_embed_erofs_ok"], 1)
        self.assertEqual(r70c_ci["stock_unmount_restored_ok"], 1)
        self.assertEqual(r70c_ci["camreset_preserves_wave56_survivors_ok"], 1)
        self.assertEqual(r70c_ci["initialize_restores_wave56_defaults_ok"], 1)

    def test_37_round70_cross_round_consistency_with_r69_r68_r67_r66_slot1_ro_and_zero_leaks(self) -> None:
        self.assertEqual(self.r69_summary["round"], 69)
        self.assertEqual(self.r68_summary["round"], 68)
        self.assertEqual(self.r67_summary["round"], 67)
        self.assertEqual(self.r66_summary["round"], 66)
        r69b_gd = self.r69_summary["runs"][
            "r69b_wave55_touch4_disp_zero_evf_flash_interval_erofs_guard"
        ]["r69_telemetry"]["wave55_guard"]
        self.assertEqual(r69b_gd["slot1_wave55_erofs_rc"], -30)
        r70b_gd = self.summary["runs"][
            "r70b_wave56_dial_mydial_fn_liveview_lut_erofs_guard"
        ]["r70_telemetry"]["wave56_guard"]
        self.assertEqual(r70b_gd["slot1_mkdir_erofs_rc"], -30)
        self.assertEqual(r70b_gd["slot1_embed_erofs_rc"], -30)
        self.assertEqual(r70b_gd["slot1_pplut_erofs_rc"], -30)
        self.assertEqual(r70b_gd["slot1_wave56_erofs_rc"], -30)
        self.assertEqual(r70b_gd["slot1_avf_ro_blocked_rc"], -30)
        self.assertEqual(r70b_gd["slot1_vault_sha256_match"], 1)
        self.assertEqual(r70b_gd["slot1_data_sector_writes"], 0)

    def test_38_round70_cross_round_consistency_with_r65_r64_zero_emmc_writes(self) -> None:
        self.assertEqual(self.r65_summary["round"], 65)
        self.assertEqual(self.r64_summary["round"], 64)
        self.assertEqual(
            self.r65_summary["runs"]["r65b_wave51_dci4k_aspect_camset_photocap_guard"]["r65_telemetry"]["wave51_guard"]["emmc_write_count"],
            0,
        )
        self.assertEqual(
            self.r64_summary["runs"]["r64b_wave50_focus_zoom_iso_flash_guard"]["r64_telemetry"]["wave50_guard"]["emmc_write_count"],
            0,
        )
        r70b_gd = self.summary["runs"][
            "r70b_wave56_dial_mydial_fn_liveview_lut_erofs_guard"
        ]["r70_telemetry"]["wave56_guard"]
        self.assertEqual(r70b_gd["emmc_write_count"], 0)
        self.assertEqual(r70b_gd["cnflasha_writes"], 0)

    def test_39_round70_cross_round_consistency_with_r69_16_h0_eq_h3(self) -> None:
        r69c = self.r69_summary["runs"][
            "r69c_clean_unmount_wave55_reset_h0_h3_big6_schinese"
        ]["r69_telemetry"]["clean_unmount_wave55_h0_h3"]
        self.assertEqual(r69c["surfaces_h0_eq_h3"], 16)
        r70c = self.summary["runs"][
            "r70c_clean_unmount_wave56_reset_h0_h3_big6_schinese"
        ]["r70_telemetry"]["clean_unmount_wave56_h0_h3"]
        self.assertEqual(r70c["surfaces_h0_eq_h3"], 16)
        self.assertEqual(r70c["drift_bits"], 0)

    def test_40_round70_unexecuted_physical_camera_bench_boundaries_documented(self) -> None:
        bounds = self.summary["unexecuted_physical_camera_bench_boundaries"]
        self.assertEqual(len(bounds), 3)
        joined = " ".join(bounds)
        self.assertIn("Front Dial", joined)
        self.assertIn("My Dial", joined)
        self.assertIn("Lock Operation Parts", joined)
        self.assertIn("Live View Display Set.", joined)
        self.assertIn("Bright Monitoring", joined)
        self.assertIn("Grid Line Type", joined)
        self.assertIn("User LUT", joined)
        self.assertIn("Embed LUT File", joined)
        self.assertIn("PPLUT1..4", joined)

    def test_41_round70_alpha_png_exists_le_27467b_and_matches_summary_sha256(self) -> None:
        pe = self.summary["runs"][
            "r70a_dial_mydial_fn12x2_liveview_lut_big6_schinese"
        ]["png_exports"]["alpha_png"]
        self.assertLessEqual(len(self.alpha_png_bytes), 27467)
        self.assertLess(len(self.alpha_png_bytes), 51200)
        self.assertEqual(len(self.alpha_png_bytes), pe["bytes"])
        self.assertEqual(
            hashlib.sha256(self.alpha_png_bytes).hexdigest(), pe["sha256"]
        )

    def test_42_round70_composited_png_exists_le_27467b_and_matches_summary_sha256(self) -> None:
        pe = self.summary["runs"][
            "r70a_dial_mydial_fn12x2_liveview_lut_big6_schinese"
        ]["png_exports"]["composited_png"]
        self.assertLessEqual(len(self.comp_png_bytes), 27467)
        self.assertLess(len(self.comp_png_bytes), 51200)
        self.assertEqual(len(self.comp_png_bytes), pe["bytes"])
        self.assertEqual(
            hashlib.sha256(self.comp_png_bytes).hexdigest(), pe["sha256"]
        )

    def test_43_round70_alpha_png_valid_1024x540_rgba_with_transparent_and_opaque_pixels(self) -> None:
        self.assertEqual(self.alpha_dims, (1024, 540))
        r70a = self.summary["runs"][
            "r70a_dial_mydial_fn12x2_liveview_lut_big6_schinese"
        ]
        r70a_nz = r70a["gpe0_readback"]["nonzero_pixels"]
        self.assertEqual(self.alpha_transparent, 552960 - r70a_nz)
        self.assertEqual(r70a["png_exports"]["transparent_pixels"], 208034)
        self.assertGreater(self.alpha_opaque, 300000)

    def test_44_round70_composited_png_valid_1024x540_rgba_100pct_opaque(self) -> None:
        self.assertEqual(self.comp_dims, (1024, 540))
        self.assertEqual(self.comp_opaque, 1024 * 540)

    def test_45_round70_report_readme_documents_all_3_runs_and_zero_host_leaks(self) -> None:
        for token in (
            "Round 70 Milestone",
            "Wave-56",
            "r70a",
            "r70b",
            "r70c",
            "43/43",
            "129/129",
            "86/86",
            "Dial Customize",
            "Custom Key/Dial Set.",
            "My Dial Settings",
            "Av/Tv Rotate",
            "Function Ring(Lens)",
            "Lock Operation Parts",
            "Rear Dial L/R",
            "Fn Menu Settings",
            "Live View Display Set.",
            "Bright Monitoring",
            "Frame Rate Low Limit",
            "Grid Line Type",
            "Manage User LUTs",
            "Embed LUT File",
            "PPLUT1..4",
            "EROFS=30",
            "Slot-1",
            "346,206",
            "346,686",
            "r70a-dial-mydial-fn12x2-liveview-lut-4ch-big6-schinese-alpha.png",
            "r70a-dial-mydial-fn12x2-liveview-lut-4ch-big6-schinese-composited.png",
        ):
            self.assertIn(token, self.r70_readme)
        for forbidden in ("/Users/", "/private/tmp/", "/var/folders/", "work/_scratch/", ":87" + "68"):
            self.assertNotIn(forbidden, self.r70_readme)

    def test_46_round70_closure_readme_section_70_present_and_accurate(self) -> None:
        self.assertIn("## 70. Round 70 Milestone", self.closure_readme)
        self.assertIn("43/43` Real-HW Rounds", self.closure_readme)
        self.assertIn("`129/129` Total", self.closure_readme)
        self.assertIn("`86/86` PNGs `<= 27,467 B`", self.closure_readme)
        self.assertIn(
            "2026-11-17-round70-milestone-dial-customize-mydial-fn12x2-liveview-lut-embed-qemu",
            self.closure_readme,
        )

    def test_47_round70_43_realhw_qemu_rounds_r28_to_r70_129_runs_and_86_pngs(self) -> None:
        png_total = 0
        rounds_found = 0
        for r in range(28, 71):
            matches = list((REPO_ROOT / "reports").glob(f"2026-??-??-round{r}-*"))
            self.assertEqual(len(matches), 1, f"Expected 1 report dir for Round {r}")
            pngs = list((matches[0] / "assets").glob("*.png"))
            self.assertGreaterEqual(len(pngs), 2, f"Expected >= 2 PNGs for Round {r}")
            for p in pngs:
                self.assertLessEqual(p.stat().st_size, 27467, str(p))
            png_total += len(pngs)
            rounds_found += 1
        self.assertGreaterEqual(rounds_found, 43)
        self.assertGreaterEqual(png_total, 86)
        audit = self.summary["r70_dial_customize_mydial_fn12x2_liveview_lut_embed_audit"]
        self.assertGreaterEqual(audit["realhw_rounds_count"], 43)
        self.assertGreaterEqual(audit["total_live_runs"], 129)
        self.assertGreaterEqual(audit["total_png_receipts"], 86)

    def test_48_round70_dual_mode_clean_room_toggle_parity_on_summary(self) -> None:
        for clean_flag in ("0", "1"):
            with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                d = json.loads(self.summary_raw)
                self.assertEqual(d["round"], 70)
                self.assertEqual(
                    d["runs"][
                        "r70a_dial_mydial_fn12x2_liveview_lut_big6_schinese"
                    ]["r70_telemetry"]["dial_customize_dormant_guard_bridge"]["dial_customize_dormant_guard_ok"],
                    1,
                )
                self.assertEqual(
                    d["runs"][
                        "r70b_wave56_dial_mydial_fn_liveview_lut_erofs_guard"
                    ]["r70_telemetry"]["wave56_guard"]["slot1_embed_erofs_rc"],
                    -30,
                )
                self.assertEqual(
                    d["runs"][
                        "r70c_clean_unmount_wave56_reset_h0_h3_big6_schinese"
                    ]["r70_telemetry"]["clean_unmount_wave56_h0_h3"]["surfaces_h0_eq_h3"],
                    16,
                )

    def test_49_round70_r70a_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"][
            "r70a_dial_mydial_fn12x2_liveview_lut_big6_schinese"
        ]["r70_telemetry"]["wave56_init"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_50_round70_r70b_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"][
            "r70b_wave56_dial_mydial_fn_liveview_lut_erofs_guard"
        ]["r70_telemetry"]["wave56_guard"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_51_round70_r70c_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"][
            "r70c_clean_unmount_wave56_reset_h0_h3_big6_schinese"
        ]["r70_telemetry"]["clean_unmount_wave56_h0_h3"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_52_round70_r70a_top_colors_transparent_plus_nonzero_equals_total_pixels(self) -> None:
        gpe = self.summary["runs"][
            "r70a_dial_mydial_fn12x2_liveview_lut_big6_schinese"
        ]["gpe0_readback"]
        color_map = {row["argb"]: row["pixels"] for row in gpe["top_colors"]}
        self.assertIn("0x00000000", color_map)
        self.assertIn("0xff000000", color_map)
        self.assertEqual(color_map["0x00000000"] + gpe["nonzero_pixels"], gpe["total_pixels"])

    def test_53_round70_r70c_top_colors_transparent_plus_nonzero_equals_total_pixels(self) -> None:
        gpe = self.summary["runs"][
            "r70c_clean_unmount_wave56_reset_h0_h3_big6_schinese"
        ]["gpe0_readback"]
        color_map = {row["argb"]: row["pixels"] for row in gpe["top_colors"]}
        self.assertIn("0x00000000", color_map)
        self.assertEqual(color_map["0x00000000"] + gpe["nonzero_pixels"], gpe["total_pixels"])

    def test_54_round70_r70a_and_r70c_wall_elapsed_and_duration_budget_sanity(self) -> None:
        r70a = self.summary["runs"][
            "r70a_dial_mydial_fn12x2_liveview_lut_big6_schinese"
        ]
        r70c = self.summary["runs"][
            "r70c_clean_unmount_wave56_reset_h0_h3_big6_schinese"
        ]
        ci_headroom = 15.0 if os.environ.get("GITHUB_ACTIONS") == "true" else 0.0
        max_wall = 240.0 + ci_headroom if os.environ.get("GITHUB_ACTIONS") == "true" else 120.0 + ci_headroom
        self.assertGreaterEqual(r70a["duration_budget_sec"], 70)
        self.assertLessEqual(r70a["duration_budget_sec"], 120)
        self.assertGreater(r70a["wall_elapsed_sec"], 50.0)
        self.assertLess(r70a["wall_elapsed_sec"], max_wall)
        self.assertGreaterEqual(r70c["duration_budget_sec"], 70)
        self.assertLessEqual(r70c["duration_budget_sec"], 120)
        self.assertGreater(r70c["wall_elapsed_sec"], 50.0)
        self.assertLess(r70c["wall_elapsed_sec"], max_wall)

    def test_55_round70_r70b_fast_early_exit_wall_elapsed_with_ci_headroom(self) -> None:
        r70b = self.summary["runs"][
            "r70b_wave56_dial_mydial_fn_liveview_lut_erofs_guard"
        ]
        ci_headroom = 15.0 if os.environ.get("GITHUB_ACTIONS") == "true" else 0.0
        max_b = 45.0 + ci_headroom if os.environ.get("GITHUB_ACTIONS") == "true" else 20.0 + ci_headroom
        self.assertEqual(r70b["duration_budget_sec"], 35)
        self.assertGreater(r70b["wall_elapsed_sec"], 1.0)
        self.assertLess(r70b["wall_elapsed_sec"], max_b)
        self.assertTrue(r70b["gpe0_readback"]["skipped_stock_fx3_mode"])

    def test_56_round70_faithful_invariants_preserved_across_all_3_runs(self) -> None:
        for rk, rv in self.summary["runs"].items():
            fi = rv["faithful_invariants"]
            self.assertEqual(fi["FX6_NATIVE_FAITHFUL"], 1, rk)
            self.assertEqual(fi["subst_color"], 0, rk)
            self.assertEqual(fi["subst_image"], 0, rk)
            self.assertEqual(fi["forced_render"], 0, rk)
            self.assertEqual(fi["skipped_node"], 0, rk)
            self.assertEqual(fi["lock_bypass"], 0, rk)

    def test_57_round70_all_3_runs_stage_b_manifest_count_13(self) -> None:
        for rk, rv in self.summary["runs"].items():
            self.assertEqual(rv["stage_b"]["manifest_count"], 13, rk)
            self.assertEqual(len(rv["stage_b"]["manifest_items"]), 13, rk)

    def test_58_round70_r70c_stage_b_r70_bridges_and_zero_leak_verified(self) -> None:
        r70c_t = self.summary["runs"][
            "r70c_clean_unmount_wave56_reset_h0_h3_big6_schinese"
        ]["r70_telemetry"]
        self.assertEqual(r70c_t["dial_customize_dormant_guard_bridge"]["dial_customize_dormant_guard_ok"], 1)
        self.assertEqual(r70c_t["mydial3_fn12x2_split_bridge"]["mydial3_fn12x2_split_ok"], 1)
        self.assertEqual(r70c_t["liveview_grid_hdmi_bridge"]["liveview_grid_hdmi_ok"], 1)
        self.assertEqual(r70c_t["lut_import_embed_erofs_bridge"]["lut_import_embed_erofs_ok"], 1)
        self.assertEqual(r70c_t["dial_customize_dormant_guard_bridge"]["dormant_dial_bypass_events"], 0)
        self.assertEqual(r70c_t["mydial3_fn12x2_split_bridge"]["mydial_lock_override_breach"], 0)
        self.assertEqual(r70c_t["mydial3_fn12x2_split_bridge"]["fn_empty_bypass_events"], 0)
        self.assertEqual(r70c_t["liveview_grid_hdmi_bridge"]["hdmi_clean_feed_grid_baked_pixels"], 0)
        self.assertEqual(r70c_t["lut_import_embed_erofs_bridge"]["external_cube_sidecar_files"], 0)
        self.assertEqual(r70c_t["lut_import_embed_erofs_bridge"]["slot1_avf_info_mutated"], 0)
        self.assertEqual(r70c_t["lut_import_embed_erofs_bridge"]["slot1_data_sector_writes"], 0)
        self.assertEqual(r70c_t["stage_b_bridge"]["e_nd_actuator_tx_count"], 0)

    def test_59_round70_all_3_runs_prefix_counts_include_fx6_r70(self) -> None:
        r70a_pc = self.summary["runs"][
            "r70a_dial_mydial_fn12x2_liveview_lut_big6_schinese"
        ]["prefix_counts"]
        r70b_pc = self.summary["runs"][
            "r70b_wave56_dial_mydial_fn_liveview_lut_erofs_guard"
        ]["prefix_counts"]
        r70c_pc = self.summary["runs"][
            "r70c_clean_unmount_wave56_reset_h0_h3_big6_schinese"
        ]["prefix_counts"]
        self.assertGreater(r70a_pc["FX6_R70_"], 10)
        self.assertEqual(r70b_pc["FX6_R70_"], 3)
        self.assertGreater(r70c_pc["FX6_R70_"], 10)

    def test_60_round70_r70_meta_invariants_across_all_3_runs(self) -> None:
        for rk, rv in self.summary["runs"].items():
            m = rv["stage_b"]["r70"]
            self.assertEqual(m["milestone_round_ordinal"], 70, rk)
            self.assertEqual(m["realhw_round_ordinal"], 43, rk)
            self.assertEqual(m["total_live_runs_at_completion"], 129, rk)
            self.assertEqual(m["total_png_receipts_at_completion"], 86, rk)
            self.assertEqual(len(m["dial_customize_5_items_initialize_only"]), 5, rk)
            self.assertEqual(m["dial_dormant_rejected_eopnotsupp"], 95, rk)
            self.assertEqual(
                m["dial_dormant_items"],
                [
                    "Dial Setup",
                    "Dial/Wheel Setup (_f 0x6a89)",
                    "Dial / Wheel Lock (base 0xe352)",
                    "Rear Dial L (_f 0x6a5c)",
                    "Rear Dial R (_f 0x680d)",
                ],
                rk,
            )
            self.assertEqual(len(m["physical_3_dials"]), 3, rk)
            self.assertTrue(m["mydial_auto_skip_empty_and_lock_override"], rk)
            self.assertEqual(m["fn_menu_12plus12_split"]["still_slots"], 12, rk)
            self.assertEqual(m["fn_menu_12plus12_split"]["movie_slots"], 12, rk)
            self.assertEqual(m["fn_menu_12plus12_split"]["all_empty_prompt_0x6220_einval"], -22, rk)
            lv = m["live_view_display_set_still_only_asymmetric_reset"]
            self.assertEqual(len(lv["initialize_only_items"]), 2, rk)
            self.assertEqual(lv["camera_settings_reset_only_item"], "Frame Rate Low Limit (On / Off [def])", rk)
            self.assertEqual(len(m["grid_line_3_patterns_clean_hdmi_isolated"]), 3, rk)
            self.assertEqual(m["user_lut_workflow"]["sdxc_lut_dir"], "/Private/Sony/PRO/LUT", rk)
            self.assertEqual(m["user_lut_workflow"]["cfexpress_lut_dir"], "/Sony/PRO/LUT", rk)
            self.assertEqual(m["user_lut_workflow"]["import_read_only_slot1_writes"], 0, rk)
            self.assertEqual(m["slot1_lut_tier0_erofs"], 30, rk)
            self.assertEqual(m["dormant_dial_bypass_events"], 0, rk)
            self.assertEqual(m["mydial_lock_override_breach"], 0, rk)
            self.assertEqual(m["fn_empty_bypass_events"], 0, rk)
            self.assertEqual(m["hdmi_clean_feed_grid_baked_pixels"], 0, rk)
            self.assertEqual(m["external_cube_sidecar_files"], 0, rk)
            self.assertEqual(m["slot1_data_sector_writes"], 0, rk)
            self.assertFalse(m["slot1_avf_info_mutated"], rk)
            self.assertEqual(m["passive_tx_bytes_emitted"], 0, rk)
            self.assertEqual(m["raw_firmware_bytes_leaked"], 0, rk)
            self.assertEqual(m["cnflasha_writes"], 0, rk)
            self.assertEqual(m["emmc_write_count"], 0, rk)
            self.assertEqual(m["p2_setting_writes"], 0, rk)

    def test_61_round70_sanitize_helper_redacts_host_paths_and_reserved_port(self) -> None:
        dirty = {
            "run_id": "test-run",
            "lang": "schinese",
            "r70_mode": "dial_mydial_fn12x2_liveview_lut_big6",
            "kernel_version": "Linux version 4.9.337-scel+",
            "kernel_bin": "/Users/fake/secret/kernel.bin",
            "dtb_bin": "/Users/fake/secret/guest.dtb",
            "build": {"tmp_build": "/private/tmp/build-123"},
            "stage_b": {"r70": {"r70_mode": "dial_mydial_fn12x2_liveview_lut_big6"}},
            "r70_telemetry": {
                "wave56_init": {"r70_init_ok": 1},
                "wave56_guard": {"r70b_ok": 1},
                "clean_unmount_wave56_h0_h3": {"r70c_ok": 1, "surfaces_h0_eq_h3": 16},
            },
            "gpe0_readback": {"nonzero_pixels": 346206},
            "png_exports": {
                "alpha_png": {
                    "path": "/Users/kafu/repo/reports/2026-11-17-round70-milestone-dial-customize-mydial-fn12x2-liveview-lut-embed-qemu/assets/a.png"
                }
            },
            "prefix_counts": {"FX6_R70_": 10},
        }
        sanitized = self.runner.sanitize_round70_summary(dirty, dirty, dirty)
        raw = json.dumps(sanitized)
        self.assertNotIn("/Users/", raw)
        self.assertNotIn("/private/tmp/", raw)
        self.assertNotIn("kernel_bin", raw)
        self.assertNotIn("dtb_bin", raw)
        self.assertIn(
            "reports/2026-11-17-round70-milestone-dial-customize-mydial-fn12x2-liveview-lut-embed-qemu/assets/a.png",
            raw,
        )

    def test_62_round70_no_stray_temp_files_or_reserved_port_in_repo(self) -> None:
        for bad_name in ("tmp", "scratch", ".worktrees"):
            self.assertFalse((REPO_ROOT / bad_name).exists(), bad_name)
        reserved_port = "87" + "68"
        self.assertNotIn(reserved_port, self.summary_raw)
        self.assertNotIn(reserved_port, self.r70_readme)

    def test_63_round70_runner_escapes_percent_in_argparse_help_and_portable_tools(self) -> None:
        self.assertIn("ArgumentParser", self.runner_src)
        self.assertNotIn("/usr/" + "bin/python3", self.runner_src)
        self.assertIn('shutil.which("zig")', self.runner_src)
        self.assertIn("FX6_SCRATCH_DIR", self.runner_src)

    def test_64_round70_test_suite_contains_at_least_70_unit_tests(self) -> None:
        methods = [m for m in dir(self) if m.startswith("test_")]
        self.assertGreaterEqual(len(methods), 70)

    def test_65_round70_dual_mode_env_flags_preserve_zero_emmc_and_clean_room_parity(self) -> None:
        for env_overrides in (
            {},
            {"FX3_CLEAN_ROOM_TEST": "1"},
            {"FX3_FX6_FORCE_CLEAN_ROOM": "1"},
        ):
            with mock.patch.dict(os.environ, env_overrides, clear=False):
                parsed = self.runner.extract_milestones(
                    "Linux version 4.9.337-scel+\n"
                    "FX6_R70_WAVE56_INIT dial_tree_ok=1 mydial_fn12x2_ok=1 "
                    "liveview_grid_ok=1 lut_embed_erofs_ok=1 r70_init_ok=1\n"
                )
                self.assertEqual(parsed["r70_telemetry"]["wave56_init"]["r70_init_ok"], 1)

    def test_66_round70_mocked_donorless_work_root_none_fallback(self) -> None:
        closure_pkg_dir = REPO_ROOT / "outputs" / "fx6-on-fx3-closure"
        safety_dir = REPO_ROOT / "outputs" / "fx3-safety"
        recovery_dir = REPO_ROOT / "outputs" / "fx3-recovery-adapter"
        firmware_lab_dir = REPO_ROOT / "outputs" / "fx3-firmware-lab"
        vm_dir = REPO_ROOT / "outputs" / "fx3-vm"
        added = [str(p) for p in (closure_pkg_dir, safety_dir, recovery_dir, firmware_lab_dir, vm_dir) if str(p) not in sys.path]
        for p in added:
            sys.path.insert(0, p)
        try:
            from fx6_closure.realhw_rec_media_autoswitch_proxy_cloud_mymenu_and_ftpes_verifier import (
                inspect_phase321_donors_bounded,
            )
            from fx6_closure.realhw_milestone324_master_gate import (
                evaluate_realhw_milestone324_master_gate,
            )

            with mock.patch(
                "fx6_closure.realhw_rec_media_autoswitch_proxy_cloud_mymenu_and_ftpes_verifier._resolve_work_root_or_none",
                return_value=None,
            ):
                donor_ci = inspect_phase321_donors_bounded(
                    force_clean_room=False,
                    work_root=None,
                    fx6_lib_dir=None,
                    fx3_modules_dir=None,
                )
                self.assertEqual(donor_ci.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertEqual(donor_ci.bytes_read_total, 0)
                self.assertEqual(donor_ci.raw_firmware_bytes_leaked, 0)

            with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
                report = evaluate_realhw_milestone324_master_gate(
                    repo_root=REPO_ROOT,
                    force_clean_room=True,
                    simulate_bench_dry_run=False,
                )
                self.assertEqual(report.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertTrue(report.all_pillars_milestone_ready)
                self.assertEqual(report.raw_firmware_bytes_leaked, 0)
                self.assertGreaterEqual(report.qemu_rounds_verified, 43)
                self.assertGreaterEqual(report.qemu_runs_verified, 129)
                self.assertGreaterEqual(report.qemu_png_receipts_verified, 86)
        finally:
            for p in added:
                if p in sys.path:
                    sys.path.remove(p)

    def test_67_round70_argparse_percent_safe_help_and_no_hardcoded_python3(self) -> None:
        for line in self.runner_src.splitlines():
            if "help=" in line and "%" in line:
                stripped = line.replace("%%", "")
                self.assertNotIn("%", stripped, f"Unescaped '%' in argparse help: {line}")
        test_src = pathlib.Path(__file__).read_text(encoding="utf-8")
        forbidden_py = "/usr/" + "bin/python3"
        self.assertNotIn(forbidden_py, self.runner_src)
        self.assertNotIn(forbidden_py, test_src)

    def test_68_round70_all_86_milestone_pngs_under_27467b_and_clean_room_safe(self) -> None:
        assets_pngs = sorted(
            p for p in (REPO_ROOT / "reports").glob("2026-??-??-round*/assets/*.png")
            if int(p.parts[-3].split("-round")[1].split("-")[0]) >= 28
        )
        self.assertGreaterEqual(len(assets_pngs), 86)
        for p in assets_pngs:
            self.assertLessEqual(p.stat().st_size, 27467, str(p))

    def test_69_round70_cli_help_subprocess_smoke(self) -> None:
        res = subprocess.run(
            [sys.executable, "-B", str(CLOSURE_DIR / "build_and_run_round.py"), "--help"],
            capture_output=True,
            text=True,
            check=True,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        self.assertIn("--r70-mode", res.stdout)
        self.assertIn("dial_mydial_fn12x2_liveview_lut_big6", res.stdout)

    def test_70_round70_pillar1_dial_customize_5item_tree_and_dormant_rear_dial_lr(self) -> None:
        r70a_meta = self.summary["runs"][
            "r70a_dial_mydial_fn12x2_liveview_lut_big6_schinese"
        ]["stage_b"]["r70"]
        self.assertEqual(len(r70a_meta["dial_customize_5_items_initialize_only"]), 5)
        self.assertIn("Custom Key/Dial Set.", r70a_meta["dial_customize_5_items_initialize_only"][0])
        self.assertIn("My Dial Settings", r70a_meta["dial_customize_5_items_initialize_only"][1])
        self.assertIn("Av/Tv Rotate", r70a_meta["dial_customize_5_items_initialize_only"][2])
        self.assertIn("Function Ring(Lens)", r70a_meta["dial_customize_5_items_initialize_only"][3])
        self.assertIn("Lock Operation Parts", r70a_meta["dial_customize_5_items_initialize_only"][4])
        self.assertIn("Dial Setup", r70a_meta["dial_dormant_items"])
        self.assertIn("Dial / Wheel Lock (base 0xe352)", r70a_meta["dial_dormant_items"])
        self.assertIn("Rear Dial R (_f 0x680d)", r70a_meta["dial_dormant_items"])
        self.assertEqual(r70a_meta["dial_dormant_rejected_eopnotsupp"], 95)

    def test_71_round70_pillar2_3_physical_dials_mydial_lock_override_and_fn12x2_split(self) -> None:
        r70a_meta = self.summary["runs"][
            "r70a_dial_mydial_fn12x2_liveview_lut_big6_schinese"
        ]["stage_b"]["r70"]
        self.assertEqual(len(r70a_meta["physical_3_dials"]), 3)
        self.assertIn("Front Dial", r70a_meta["physical_3_dials"][0])
        self.assertIn("Rear Dial (single", r70a_meta["physical_3_dials"][1])
        self.assertIn("Control Wheel", r70a_meta["physical_3_dials"][2])
        self.assertTrue(r70a_meta["mydial_auto_skip_empty_and_lock_override"])
        fn = r70a_meta["fn_menu_12plus12_split"]
        self.assertEqual(fn["still_slots"], 12)
        self.assertEqual(fn["movie_slots"], 12)
        self.assertEqual(fn["empty_slot_0xe0ac"], "Not set")
        self.assertEqual(fn["all_empty_prompt_0x6220_einval"], -22)

    def test_72_round70_pillar3_still_liveview_3item_asymmetric_reset_and_grid_clean_hdmi(self) -> None:
        r70a_meta = self.summary["runs"][
            "r70a_dial_mydial_fn12x2_liveview_lut_big6_schinese"
        ]["stage_b"]["r70"]
        lv = r70a_meta["live_view_display_set_still_only_asymmetric_reset"]
        self.assertEqual(len(lv["initialize_only_items"]), 2)
        self.assertIn("Bright Monitoring", lv["initialize_only_items"][0])
        self.assertIn("Exposure Effect", lv["initialize_only_items"][1])
        self.assertEqual(lv["camera_settings_reset_only_item"], "Frame Rate Low Limit (On / Off [def])")
        self.assertEqual(len(r70a_meta["grid_line_3_patterns_clean_hdmi_isolated"]), 3)
        self.assertEqual(r70a_meta["hdmi_clean_feed_grid_baked_pixels"], 0)

    def test_73_round70_pillar4_user_lut16_ro_import_embed_vs_pplut_bake_and_slot1_erofs30(self) -> None:
        r70a_meta = self.summary["runs"][
            "r70a_dial_mydial_fn12x2_liveview_lut_big6_schinese"
        ]["stage_b"]["r70"]
        lut = r70a_meta["user_lut_workflow"]
        self.assertIn("User1..User16", lut["manage_user_luts_slots"])
        self.assertEqual(lut["sdxc_lut_dir"], "/Private/Sony/PRO/LUT")
        self.assertEqual(lut["cfexpress_lut_dir"], "/Sony/PRO/LUT")
        self.assertEqual(lut["import_read_only_slot1_writes"], 0)
        self.assertEqual(lut["select_lut_default"], "s709 (Resettable)")
        self.assertIn("locked Off on SD/SDHC", lut["embed_lut_file"])
        self.assertIn("Resettable unlike PP1..11", lut["pplut1_to_4"])
        self.assertEqual(r70a_meta["slot1_lut_tier0_erofs"], 30)
        self.assertEqual(r70a_meta["external_cube_sidecar_files"], 0)

    def test_74_round70_stage_a_and_shim_c_sources_pass_fx6_round70_macros(self) -> None:
        self.assertIn("r70_wave56_cfg_t", self.stage_a_src)
        self.assertIn("r70_wave56_initialize", self.stage_a_src)
        self.assertIn("r70_wave56_camera_settings_reset", self.stage_a_src)
        self.assertIn("FX6_ROUND >= 70", self.shim_src)
        self.assertIn("FX6_STAGE_B_R70_BRIDGE", self.shim_src)


if __name__ == "__main__":
    unittest.main()
