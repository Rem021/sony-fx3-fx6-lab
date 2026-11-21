#!/usr/bin/env python3
"""Offline four-mode unit tests for FX6-on-FX3 Round 77 Milestone (50/50 Real-HW Rounds R28..R77, 148th..150th Live Runs -> 150/150 Total, 100/100 PNGs <= 27,467 B — Wave-63)."""
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
ROUND77_REPORT_DIR = (
    REPO_ROOT
    / "reports"
    / "2026-11-18-round77-milestone-hdmi-raw-desqueeze-reclamp-varshutter-apsc-qemu"
)
WAVE63_SPEC_PATH = (
    REPO_ROOT
    / "reports"
    / "2026-11-17-global-sony-wave63-hdmi-raw-desqueeze-tally-emph-rec-varshutter-apsc-intel"
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


def _build_overlay_for_r77(
    runner,
    parent_cpio: pathlib.Path,
    fp,
    fv,
    fb,
    fake_run,
    jit_meta: Dict[str, Any],
    work: pathlib.Path,
    r77_mode: str,
    lang: str = "schinese",
    enable_r77: bool = True,
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
            enable_r70=True,
            r70_mode="dial_mydial_fn12x2_liveview_lut_big6",
            enable_r71=True,
            r71_mode="steadyshot_47focal_selftimer_zebra_streaming_big6",
            enable_r72=True,
            r72_mode="bright_mon_shotmark_usblan_bulb_big6",
            enable_r73=True,
            r73_mode="big6_framing_interval_tc_make_ssh_auth_fan_big6",
            enable_r74=True,
            r74_mode="rec_media_autoswitch_proxy_cloud_mymenu42_big6",
            enable_r75=True,
            r75_mode="ftp_ftpes_customwb_afspeed_focusmap_marker_big6",
            enable_r76=True,
            r76_mode="shoe_audio_4ch_subject_recog_silent_version_big6",
            enable_r77=enable_r77,
            r77_mode=r77_mode,
            sd_manifest_mode="valid",
            lang=lang,
            shim_bytes=b"SHIM",
        )


class TestRound77MilestoneHdmiRawDesqueezeReclampVarshutterApscQemu(unittest.TestCase):
    EXPECTED_RUN_KEYS = (
        "r77a_hdmi_raw_4264_desqueeze_reclamp_varshutter_apsc_big6_schinese",
        "r77b_wave63_hdmi_raw_desqueeze_18x_reclamp_varshutter_apsc_guard",
        "r77c_clean_unmount_wave63_reset_h0_h3_big6_schinese",
    )

    runner: Any
    runner_src: str
    stage_a_src: str
    shim_src: str
    wave63_spec: str
    summary_raw: str
    summary: Dict[str, Any]
    r77_readme: str
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
    launcher_r77: Optional[bytes]
    shim_r77: Optional[bytes]
    shim_r76: Optional[bytes]
    r76_summary: Dict[str, Any]
    r75_summary: Dict[str, Any]
    r74_summary: Dict[str, Any]
    r73_summary: Dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = _load_closure_module("fx6_brr_r77_cached", "build_and_run_round.py")
        cls.runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")
        cls.stage_a_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        cls.shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        cls.wave63_spec = WAVE63_SPEC_PATH.read_text(encoding="utf-8")
        cls.summary_raw = (ROUND77_REPORT_DIR / "summary.json").read_text(encoding="utf-8")
        cls.summary = json.loads(cls.summary_raw)
        cls.r77_readme = (ROUND77_REPORT_DIR / "README.md").read_text(encoding="utf-8")
        cls.closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")

        alpha_p = (
            ROUND77_REPORT_DIR
            / "r77_reclamp_3led_emph_rec_varshutter_apsc_s35_preview.png"
        )
        comp_p = (
            ROUND77_REPORT_DIR
            / "r77_hdmi_raw_4264_recmedia_desqueeze_165x_preview.png"
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
            cls.ov_a = _build_overlay_for_r77(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wa", "hdmi_raw_4264_desqueeze_reclamp_varshutter_apsc_big6", lang="schinese",
            )
            cls.ov_b = _build_overlay_for_r77(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wb", "wave63_hdmi_raw_desqueeze_18x_reclamp_varshutter_apsc_guard", lang="en",
            )
            cls.ov_c = _build_overlay_for_r77(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wc", "clean_unmount_wave63_reset_h0_h3_big6", lang="schinese",
            )
            cls.ov_off = _build_overlay_for_r77(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "woff", "hdmi_raw_4264_desqueeze_reclamp_varshutter_apsc_big6", enable_r77=False,
            )
            cls.invalid_mode_raised = False
            try:
                _build_overlay_for_r77(
                    cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                    tpath / "wbad", "invalid_r77_mode",
                )
            except ValueError:
                cls.invalid_mode_raised = True

            zig_bin = shutil.which("zig") or (
                str(cls.runner.ZIG) if cls.runner.ZIG.is_file() else None
            )
            if zig_bin is not None:
                verify_r77_out = tpath / "fx6-stage-a-verify-r77"
                shim_r77_out = tpath / "libgrm-fbinit9-r77.so"
                shim_r76_out = tpath / "libgrm-fbinit9-r76.so"
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
                        str(verify_r77_out),
                    ],
                    [
                        zig_bin,
                        "cc",
                        "-target",
                        "aarch64-linux-gnu.2.25",
                        "-O0",
                        "-shared",
                        "-fPIC",
                        "-DFX6_ROUND=77",
                        str(CLOSURE_DIR / "libgrm-fbinit9.c"),
                        "-ldl",
                        "-lpthread",
                        "-o",
                        str(shim_r77_out),
                    ],
                    [
                        zig_bin,
                        "cc",
                        "-target",
                        "aarch64-linux-gnu.2.25",
                        "-O0",
                        "-shared",
                        "-fPIC",
                        "-DFX6_ROUND=76",
                        str(CLOSURE_DIR / "libgrm-fbinit9.c"),
                        "-ldl",
                        "-lpthread",
                        "-o",
                        str(shim_r76_out),
                    ],
                ):
                    cls.runner.subprocess.run(cmd, check=True, timeout=120)
                cls.launcher_r77 = verify_r77_out.read_bytes()
                cls.shim_r77 = shim_r77_out.read_bytes()
                cls.shim_r76 = shim_r76_out.read_bytes()
            else:
                cls.launcher_r77 = None
                cls.shim_r77 = None
                cls.shim_r76 = None

        cls.r76_summary = json.loads(
            (
                REPO_ROOT
                / "reports"
                / "2026-11-18-round76-shoe-audio-4ch-subject-recog-silent-target-bodydata-qemu"
                / "summary.json"
            ).read_text(encoding="utf-8")
        )
        cls.r75_summary = json.loads(
            (
                REPO_ROOT
                / "reports"
                / "2026-11-18-round75-milestone-ftp-ftpes-customwb-afspeed-focusmap-marker-peaking-qemu"
                / "summary.json"
            ).read_text(encoding="utf-8")
        )
        cls.r74_summary = json.loads(
            (
                REPO_ROOT
                / "reports"
                / "2026-11-18-round74-rec-media-autoswitch-proxy-cloud-mymenu42-qemu"
                / "summary.json"
            ).read_text(encoding="utf-8")
        )
        cls.r73_summary = json.loads(
            (
                REPO_ROOT
                / "reports"
                / "2026-11-18-round73-big6-home-framing-interval-tc-make-ssh-auth-fan-qemu"
                / "summary.json"
            ).read_text(encoding="utf-8")
        )

    def test_01_wave63_global_spec_present_and_covers_all_4_pillars(self) -> None:
        self.assertTrue(WAVE63_SPEC_PATH.is_file())
        for needle in (
            "HDMI Output Settings",
            "Rec. Media dur HDMI Output",
            "4K Output Set.(HDMI Only)",
            "Color Gamut for RAW Output",
            "BKID_APP_setting_color_gamut_for_raw_out",
            "Time Code Output",
            "REC Control",
            "4ch Audio Output",
            "De-Squeeze Display",
            "VAL_DE_SQUEEZE_DISP_1_65X",
            "1.8x",
            "Focus Magnifier",
            "Bright Monitoring",
            "REC Lamp",
            "REC_LAMP_LIGHT_UP_ONLY_ONE",
            "Emphasized REC Display",
            "Remain Shoot Display",
            "Auto Review",
            "Var. Shutter",
            "BKID_APP_setting_high_res_ss",
            "Anti-flicker Shoot.",
            "APS-C S35 Shooting",
            "Extended Clear Scan",
            "5.1M",
        ):
            self.assertIn(needle, self.wave63_spec)

    def test_02_round77_summary_schema_milestone_and_zero_leaks(self) -> None:
        self.assertNotIn("/Users/", self.summary_raw)
        self.assertNotIn("/private/tmp/", self.summary_raw)
        self.assertNotIn("/tmp/round77", self.summary_raw)
        self.assertEqual(
            self.summary["schema"],
            "fx6-on-fx3-round77-hdmi-raw-desqueeze-reclamp-varshutter-apsc-qemu-v1",
        )
        self.assertEqual(self.summary["round"], 77)
        self.assertIn("50/50 Real-HW Rounds", self.summary["milestone"])
        self.assertIn("150/150 Live Runs", self.summary["milestone"])
        self.assertIn("100/100 PNGs <= 27,467 B", self.summary["milestone"])
        self.assertEqual(self.summary["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(tuple(self.summary["runs"].keys()), self.EXPECTED_RUN_KEYS)

    def test_03_round77_cli_accepts_round77_and_all_3_r77_modes(self) -> None:
        self.assertIn(", 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77]", self.runner_src)
        for mode in (
            "hdmi_raw_4264_desqueeze_reclamp_varshutter_apsc_big6",
            "wave63_hdmi_raw_desqueeze_18x_reclamp_varshutter_apsc_guard",
            "clean_unmount_wave63_reset_h0_h3_big6",
        ):
            self.assertIn(mode, self.runner_src)

    def test_04_round77_overlay_rejects_invalid_r77_mode(self) -> None:
        self.assertTrue(self.invalid_mode_raised)

    def test_05_round77_overlay_r77a_injects_etc_fx6_stage_r77_and_appfw_launch(self) -> None:
        replacements, additions, meta = self.ov_a
        self.assertTrue(meta["r77_enabled"])
        self.assertIn("etc/fx6_stage_r77", additions)
        self.assertIn("etc/fx6_r77_libjit.so", additions)
        r77_cfg = additions["etc/fx6_stage_r77"][0].decode("utf-8")
        self.assertIn("stage_r77=1", r77_cfg)
        self.assertIn("r77_mode=hdmi_raw_4264_desqueeze_reclamp_varshutter_apsc_big6", r77_cfg)
        self.assertIn("milestone_50th_realhw_150th_live_100_pngs=1", r77_cfg)
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("/usr/bin/appfw-launch", init_txt)
        self.assertNotIn("--r77-wave63-guard", init_txt)

    def test_06_round77_overlay_r77b_injects_early_guard_probe_and_poweroff(self) -> None:
        replacements, _, meta = self.ov_b
        self.assertEqual(
            meta["r77"]["r77_mode"],
            "wave63_hdmi_raw_desqueeze_18x_reclamp_varshutter_apsc_guard",
        )
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("--r77-wave63-guard", init_txt)
        self.assertIn("FX6_R77_WAVE63_GUARD_RC=", init_txt)
        self.assertIn("FX6_R77_WAVE63_GUARD_EXIT", init_txt)
        self.assertIn("poweroff -f", init_txt)

    def test_07_round77_overlay_r77c_integrated_runs_stage_b_big6(self) -> None:
        replacements, additions, meta = self.ov_c
        self.assertEqual(meta["r77"]["r77_mode"], "clean_unmount_wave63_reset_h0_h3_big6")
        r77_cfg = additions["etc/fx6_stage_r77"][0].decode("utf-8")
        self.assertIn("r77_mode=clean_unmount_wave63_reset_h0_h3_big6", r77_cfg)
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("/usr/bin/appfw-launch", init_txt)
        self.assertNotIn("--r77-wave63-guard", init_txt)

    def test_08_round77_overlay_disabled_when_enable_r77_false(self) -> None:
        _, additions, meta = self.ov_off
        self.assertFalse(meta["r77_enabled"])
        self.assertNotIn("etc/fx6_stage_r77", additions)
        self.assertNotIn("etc/fx6_r77_libjit.so", additions)
        self.assertNotIn("r77", meta)

    def test_09_round77_stage_a_c_source_contains_all_3_wave63_probes(self) -> None:
        for sym in (
            "setup_r77_hdmi_raw_desqueeze_reclamp_varshutter_apsc_probe",
            "run_r77_wave63_guard_probe",
            "run_r77_clean_unmount_wave63_h0_h3_probe",
            "r77_wave63_initialize",
            "r77_wave63_zero_init",
            "r77_wave63_camera_settings_reset",
            "r77_wave63_reset_network_settings",
            "r77_configure_hdmi_raw_and_rec_media",
            "r77_configure_desqueeze_display",
            "r77_configure_reclamp_emph_remain_autoreview",
            "r77_configure_antiflicker_and_apsc_s35",
            "FX6_R77_WAVE63_INIT",
            "FX6_R77_WAVE63_GUARD",
            "FX6_R77_CLEAN_UNMOUNT_WAVE63_H0_H3",
            "--r77-wave63-guard",
            "--r77-clean-unmount-wave63-h0-h3",
            "/etc/fx6_stage_r77",
        ):
            self.assertIn(sym, self.stage_a_src)

    def test_10_round77_shim_c_source_contains_r77_guarded_bridges(self) -> None:
        self.assertIn("#if FX6_ROUND >= 77", self.shim_src)
        for sym in (
            "FX6_R77_HDMI_RAW_4264_RECMEDIA_BRIDGE",
            "FX6_R77_DESQUEEZE_165X_4LOCKS_BRIDGE",
            "FX6_R77_RECLAMP_3LED_EMPH_REC_AUTOREV_BRIDGE",
            "FX6_R77_ANTIFLICKER_NO_VARSHUTTER_APSC_BRIDGE",
            "FX6_R77_LANG_TELEMETRY",
            "FX6_STAGE_B_R77_BRIDGE",
        ):
            self.assertIn(sym, self.shim_src)

    def test_11_round77_compile_launcher_and_shim_aarch64_elf_symbols(self) -> None:
        if self.launcher_r77 is None or self.shim_r77 is None:
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertEqual(self.launcher_r77[:4], b"\x7fELF")
        self.assertEqual(self.shim_r77[:4], b"\x7fELF")
        self.assertEqual(struct.unpack_from("<H", self.shim_r77, 18)[0], 183)
        self.assertIn(b"FX6_R77_HDMI_RAW_4264_RECMEDIA_BRIDGE", self.shim_r77)
        self.assertIn(b"FX6_R77_DESQUEEZE_165X_4LOCKS_BRIDGE", self.shim_r77)
        self.assertIn(b"FX6_R77_RECLAMP_3LED_EMPH_REC_AUTOREV_BRIDGE", self.shim_r77)
        self.assertIn(b"FX6_R77_ANTIFLICKER_NO_VARSHUTTER_APSC_BRIDGE", self.shim_r77)

    def test_12_round77_shim_round76_backward_compat_excludes_r77_bridges(self) -> None:
        if self.shim_r76 is None:
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertIn(b"FX6_R76_SHOE_AUDIO_4CH_OUT_TIMING_BRIDGE", self.shim_r76)
        self.assertNotIn(b"FX6_R77_HDMI_RAW_4264_RECMEDIA_BRIDGE", self.shim_r76)

    def test_13_round77_parse_log_extracts_all_10_r77_prefixes_and_rc(self) -> None:
        serial_text = (
            "\n".join(
                [
                    "Linux version 4.9.337-scel+ (sony@fx3)",
                    "FX6_R77_WAVE63_INIT fx3_wave63_nodes_ok=1 uxc_tokens_ok=1 hdmi_raw_4264_recmedia_ok=1 desqueeze_165x_4locks_ok=1 reclamp_3led_emph_rec_autorev_ok=1 antiflicker_no_varshutter_apsc_ok=1 emmc_write_count=0 r77_init_ok=1",
                    "FX6_R77_HDMI_RAW_4264_RECMEDIA_BRIDGE hdmi_8items_4264_16bit_raw_ok=1 rec_media_hdmi_only_zero_write_vs_erofs30_ok=1 tc_out_prereq_and_2ch_audio_ok=1 hdmi_raw_4264_recmedia_ok=1 cnflasha_writes=0 emmc_write_count=0 r77_bridge_ok=1",
                    "FX6_R77_DESQUEEZE_165X_4LOCKS_BRIDGE desqueeze_5ratios_15x_165x_no_18x_ok=1 desqueeze_4lockouts_6bypasses_zero_card_mut_ok=1 desqueeze_165x_4locks_ok=1 dormant_desqueeze_18x_bypass_events=0 cnflasha_writes=0 emmc_write_count=0",
                    "FX6_R77_RECLAMP_3LED_EMPH_REC_AUTOREV_BRIDGE reclamp_3led_coupled_silent_decoupled_ok=1 emph_rec_clean_hdmi_remain_autorev_ok=1 reclamp_3led_emph_rec_autorev_ok=1 dormant_reclamp_only_one_bypass_events=0 cnflasha_writes=0 emmc_write_count=0",
                    "FX6_R77_ANTIFLICKER_NO_VARSHUTTER_APSC_BRIDGE antiflicker_still_mech_no_varshutter_ecs_ok=1 apsc_s35_4k_lockout_51m_reset_immune_ok=1 antiflicker_no_varshutter_apsc_ok=1 dormant_var_shutter_ecs_bypass_events=0 cnflasha_writes=0 emmc_write_count=0",
                    "FX6_R77_LANG_TELEMETRY lang=schinese font_bank=23 str_bank=19 milestone_50th_realhw_150th_live_100_pngs=1 r77_bridge_ok=1",
                    "FX6_STAGE_B_R77_BRIDGE round=77 faithful=1 nop_count=0 milestone_50th_realhw_150th_live_100_pngs=1 emmc_write_count=0",
                    "FX6_R77_WAVE63_GUARD raw_gamut_removed_rc=-95 desq_18x_absent_rc=-95 var_shutter_dormant_rc=-95 raw_recmedia_on_slot1_erofs_rc=-30 live_attach_eperm_rc=-1 r77b_ok=1",
                    "FX6_R77_WAVE63_GUARD_RC=0",
                    "FX6_R77_CLEAN_UNMOUNT_WAVE63_H0_H3 stock_unmount_restored_ok=1 camreset_resets_emph_rec_antiflicker_preserves_hdmi8_desq_reclamp_remain_autorev_apsc_airplane_ok=1 nwreset_preserves_wave63_apsc_airplane_ok=1 initialize_restores_wave63_defaults_preserves_airplane_ok=1 surfaces_h0_eq_h3=16 r77c_ok=1",
                ]
            )
            + "\n"
        )
        parsed = self.runner.extract_milestones(serial_text)
        r77_t = parsed["r77_telemetry"]
        self.assertEqual(r77_t["wave63_guard_rc"], 0)
        self.assertEqual(r77_t["wave63_init"]["hdmi_raw_4264_recmedia_ok"], 1)
        self.assertEqual(r77_t["hdmi_raw_4264_recmedia_bridge"]["hdmi_raw_4264_recmedia_ok"], 1)
        self.assertEqual(r77_t["desqueeze_165x_4locks_bridge"]["desqueeze_165x_4locks_ok"], 1)
        self.assertEqual(r77_t["reclamp_3led_emph_rec_autorev_bridge"]["reclamp_3led_emph_rec_autorev_ok"], 1)
        self.assertEqual(r77_t["antiflicker_no_varshutter_apsc_bridge"]["antiflicker_no_varshutter_apsc_ok"], 1)
        self.assertEqual(r77_t["lang_telemetry"]["lang"], "schinese")
        self.assertEqual(r77_t["lang_telemetry"]["milestone_50th_realhw_150th_live_100_pngs"], 1)
        self.assertEqual(r77_t["stage_b_bridge"]["round"], 77)
        self.assertEqual(r77_t["wave63_guard"]["r77b_ok"], 1)
        self.assertEqual(r77_t["clean_unmount_wave63_h0_h3"]["surfaces_h0_eq_h3"], 16)
        self.assertEqual(parsed["prefix_counts"]["FX6_R77_"], 9)

    def test_14_round77_parse_log_defaults_when_no_r77_lines_present(self) -> None:
        parsed = self.runner.extract_milestones("Linux version 4.9.337-scel+\n")
        self.assertIsNone(parsed["r77_telemetry"])
        self.assertEqual(parsed["prefix_counts"].get("FX6_R77_", 0), 0)

    def test_15_round77_runner_preserves_r76_prefix_and_uses_r77_stage_label(self) -> None:
        self.assertIn('if args.round >= 76:\n        tmp_prefix = "fx6-r76"', self.runner_src)
        self.assertIn('if args.round >= 77:\n        tmp_prefix = "fx6-r77"', self.runner_src)
        self.assertIn(
            "Milestone50RealHw150thLiveWave63HdmiRaw4264Desqueeze165xRecLamp3LedVarShutterApscS35",
            self.runner_src,
        )
        self.assertIn(", 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77]", self.runner_src)

    def test_16_round77_runner_portability_and_sanitizer_helper(self) -> None:
        self.assertIn('shutil.which("zig")', self.runner_src)
        self.assertIn("FX6_SCRATCH_DIR", self.runner_src)
        self.assertIn("def sanitize_round77_summary(", self.runner_src)
        self.assertNotIn("/usr/" + "bin/python3", self.runner_src)

    def test_17_round77_summary_json_top_level_schema_and_milestone_metadata(self) -> None:
        d = self.summary
        self.assertEqual(
            d["schema"],
            "fx6-on-fx3-round77-hdmi-raw-desqueeze-reclamp-varshutter-apsc-qemu-v1",
        )
        self.assertEqual(d["round"], 77)
        self.assertIn("50/50 Real-HW Rounds", d["milestone"])
        self.assertIn("150/150 Live Runs", d["milestone"])
        self.assertIn("100/100 PNGs <= 27,467 B", d["milestone"])
        self.assertEqual(d["date"], "2026-11-18")
        self.assertIn("4.9.337-scel+", d["kernel_version"])
        self.assertEqual(d["raw_firmware_bytes_leaked"], 0)

    def test_18_round77_summary_json_zero_host_path_scratch_and_elapsed_leaks(self) -> None:
        for forbidden in (
            "/Users/",
            "/private/tmp/",
            "/var/folders/",
            "/tmp/round77",
            "work/_scratch/",
            "work/_tests/",
            "elapsed_seconds",
            ":87" + "68",
        ):
            self.assertNotIn(forbidden, self.summary_raw)

    def test_19_round77_summary_audit_block_confirms_50_rounds_150_runs_100_pngs(self) -> None:
        audit = self.summary["r77_hdmi_raw_desqueeze_reclamp_varshutter_apsc_audit"]
        self.assertEqual(audit["round"], 77)
        self.assertGreaterEqual(audit["realhw_rounds_count"], 50)
        self.assertGreaterEqual(audit["total_live_runs"], 150)
        self.assertGreaterEqual(audit["total_png_receipts"], 100)
        self.assertGreaterEqual(audit["milestone324_qemu_rounds"], 50)
        self.assertGreaterEqual(audit["milestone324_qemu_runs"], 150)
        self.assertGreaterEqual(audit["milestone324_png_receipts"], 100)
        self.assertEqual(audit["total_runs"], 3)
        negative_keys = {
            "fx3_raw_color_gamut_standalone_menu_present",
            "fx3_hdmi_4k_24p_8bit_exposed",
            "fx6_24hz_hdmi_raw_supported",
            "fx3_desqueeze_18x_present",
            "fx6_desqueeze_165x_present",
            "fx6_sdi_desqueeze_supported",
            "fx3_tally_light_menu_present",
            "fx3_uncoupled_rear_top_rec_lamp_supported",
            "fx3_var_shutter_high_res_ss_exposed",
            "fx3_ecs_2399_8000hz_supported",
            "fx6_mechanical_shutter_present",
        }
        for nk in negative_keys:
            self.assertIs(audit[nk], False, nk)
        for k, v in audit.items():
            if isinstance(v, bool) and k not in negative_keys:
                self.assertTrue(v, f"Expected audit boolean {k} to be True")

    def test_20_round77_all_3_runs_present_with_kernel_4_9_337_and_zero_crashes_writes(self) -> None:
        runs = self.summary["runs"]
        self.assertEqual(list(runs.keys()), list(self.EXPECTED_RUN_KEYS))
        for rk, rv in runs.items():
            self.assertEqual(rv["round"], 77, rk)
            self.assertIn("4.9.337-scel+", rv["kernel_version"], rk)
            self.assertEqual(rv["nop_count"], 0, rk)
            self.assertEqual(rv["crashes"], 0, rk)
            self.assertEqual(rv["emmc_write_count"], 0, rk)
            self.assertGreater(rv["wall_elapsed_sec"], 0.0, rk)

    def test_21_round77_r77a_pillar1_hdmi_raw_4264_recmedia_tc_and_2ch_audio(self) -> None:
        init_t = self.summary["runs"][
            "r77a_hdmi_raw_4264_desqueeze_reclamp_varshutter_apsc_big6_schinese"
        ]["r77_telemetry"]["wave63_init"]
        self.assertEqual(init_t["fx3_wave63_nodes_ok"], 1)
        self.assertEqual(init_t["uxc_tokens_ok"], 1)
        self.assertEqual(init_t["hdmi_raw_4264_recmedia_ok"], 1)
        self.assertEqual(init_t["raw_gamut_removed_rc"], -95)
        self.assertEqual(init_t["rec_ctrl_no_tc_rc"], -16)
        self.assertEqual(init_t["raw_recmedia_on_slot1_erofs_rc"], -30)
        self.assertEqual(init_t["dormant_raw_gamut_bypass_events"], 0)
        self.assertEqual(init_t["dormant_24p_8bit_bypass_events"], 0)

    def test_22_round77_r77a_pillar2_desqueeze_15x_165x_no_18x_and_4locks(self) -> None:
        init_t = self.summary["runs"][
            "r77a_hdmi_raw_4264_desqueeze_reclamp_varshutter_apsc_big6_schinese"
        ]["r77_telemetry"]["wave63_init"]
        self.assertEqual(init_t["desqueeze_165x_4locks_ok"], 1)
        self.assertEqual(init_t["desq_18x_absent_rc"], -95)
        self.assertEqual(init_t["desq_steadyshot_lock_rc"], -16)
        self.assertEqual(init_t["dormant_desqueeze_18x_bypass_events"], 0)
        self.assertEqual(init_t["recorded_card_stream_altered"], 0)

    def test_23_round77_r77a_pillar3_reclamp_3led_emph_rec_remain_and_autoreview(self) -> None:
        init_t = self.summary["runs"][
            "r77a_hdmi_raw_4264_desqueeze_reclamp_varshutter_apsc_big6_schinese"
        ]["r77_telemetry"]["wave63_init"]
        self.assertEqual(init_t["reclamp_3led_emph_rec_autorev_ok"], 1)
        self.assertEqual(init_t["reclamp_only_one_rc"], -95)
        self.assertEqual(init_t["autorev_interval_rc"], -16)
        self.assertEqual(init_t["dormant_reclamp_only_one_bypass_events"], 0)
        self.assertEqual(init_t["clean_hdmi_emph_rec_baked_pixels"], 0)

    def test_24_round77_r77a_pillar4_antiflicker_no_varshutter_apsc_s35_and_vaults(self) -> None:
        init_t = self.summary["runs"][
            "r77a_hdmi_raw_4264_desqueeze_reclamp_varshutter_apsc_big6_schinese"
        ]["r77_telemetry"]["wave63_init"]
        self.assertEqual(init_t["antiflicker_no_varshutter_apsc_ok"], 1)
        self.assertEqual(init_t["var_shutter_dormant_rc"], -95)
        self.assertEqual(init_t["apsc_4k_lockout_rc"], -16)
        self.assertEqual(init_t["antiflicker_movie_rc"], -16)
        self.assertEqual(init_t["dormant_var_shutter_ecs_bypass_events"], 0)
        self.assertEqual(init_t["slot1_data_sector_writes"], 0)
        self.assertEqual(init_t["rf_tx_packets"], 0)
        self.assertEqual(init_t["passive_tx_bytes_emitted"], 0)
        self.assertEqual(init_t["e_nd_actuator_tx_count"], 0)
        self.assertEqual(init_t["p2_write_blocked_rc"], -30)
        self.assertEqual(init_t["p2_sha256_match"], 1)
        self.assertEqual(init_t["p12_sha256_match"], 1)
        self.assertEqual(init_t["cnflasha_sha256_match"], 1)
        self.assertEqual(init_t["slot1_vault_sha256_match"], 1)
        self.assertEqual(init_t["cnflasha_writes"], 0)
        self.assertEqual(init_t["appfw_present"], 1)
        self.assertEqual(init_t["shim_present"], 1)
        self.assertEqual(init_t["emmc_write_count"], 0)
        self.assertEqual(init_t["r77_init_ok"], 1)

    def test_25_round77_r77a_stage_b_schinese_lang_telemetry_and_bridge(self) -> None:
        r77a_t = self.summary["runs"][
            "r77a_hdmi_raw_4264_desqueeze_reclamp_varshutter_apsc_big6_schinese"
        ]["r77_telemetry"]
        lt = r77a_t["lang_telemetry"]
        self.assertEqual(lt["lang"], "schinese")
        self.assertEqual(lt["bk4_lang_id"], "0x02cf019c")
        self.assertEqual(lt["bk4_lang_val"], "0x19")
        self.assertEqual(lt["lang_enum"], "0x2b45_CHINESE_SIMPLIFIED")
        self.assertEqual(lt["font_bank"], 23)
        self.assertEqual(lt["str_bank"], 19)
        self.assertEqual(lt["gpe_fb"], 0)
        self.assertEqual(
            lt["round77_50realhw_wave63_hdmi_raw_desqueeze_reclamp_varshutter_apsc"], 1
        )
        self.assertEqual(lt["milestone_50th_realhw_150th_live_100_pngs"], 1)
        self.assertEqual(lt["dormant_raw_gamut_bypass_events"], 0)
        self.assertEqual(lt["dormant_24p_8bit_bypass_events"], 0)
        self.assertEqual(lt["dormant_desqueeze_18x_bypass_events"], 0)
        self.assertEqual(lt["dormant_reclamp_only_one_bypass_events"], 0)
        self.assertEqual(lt["dormant_var_shutter_ecs_bypass_events"], 0)
        self.assertEqual(lt["recorded_card_stream_altered"], 0)
        self.assertEqual(lt["clean_hdmi_emph_rec_baked_pixels"], 0)
        self.assertEqual(lt["slot1_data_sector_writes"], 0)
        self.assertEqual(lt["rf_tx_packets"], 0)
        self.assertEqual(lt["raw_firmware_bytes_leaked"], 0)

        sb = r77a_t["stage_b_bridge"]
        self.assertEqual(sb["round"], 77)
        self.assertEqual(sb["faithful"], 1)
        self.assertEqual(sb["nop_count"], 0)
        self.assertEqual(sb["hdmi_8items_4264_16bit_raw_recmedia_tc_2ch_audio"], 1)
        self.assertEqual(sb["desqueeze_5ratios_15x_165x_no_18x_4locks_6bypasses"], 1)
        self.assertEqual(sb["reclamp_3led_coupled_silent_decoupled_emph_rec_remain_autorev"], 1)
        self.assertEqual(sb["antiflicker_still_mech_no_varshutter_ecs_apsc_4k_lockout_reset_immune"], 1)
        self.assertEqual(sb["milestone_50th_realhw_150th_live_100_pngs"], 1)

    def test_26_round77_r77a_stage_b_4_pillar_bridges_verified(self) -> None:
        r77a_t = self.summary["runs"][
            "r77a_hdmi_raw_4264_desqueeze_reclamp_varshutter_apsc_big6_schinese"
        ]["r77_telemetry"]
        pb1 = r77a_t["hdmi_raw_4264_recmedia_bridge"]
        self.assertEqual(pb1["hdmi_8items_4264_16bit_raw_ok"], 1)
        self.assertEqual(pb1["rec_media_hdmi_only_zero_write_vs_erofs30_ok"], 1)
        self.assertEqual(pb1["tc_out_prereq_and_2ch_audio_ok"], 1)
        self.assertEqual(pb1["hdmi_raw_4264_recmedia_ok"], 1)
        self.assertEqual(pb1["dormant_raw_gamut_bypass_events"], 0)
        self.assertEqual(pb1["dormant_24p_8bit_bypass_events"], 0)
        self.assertEqual(pb1["slot1_data_sector_writes"], 0)
        self.assertEqual(pb1["r77_bridge_ok"], 1)

        pb2 = r77a_t["desqueeze_165x_4locks_bridge"]
        self.assertEqual(pb2["desqueeze_5ratios_15x_165x_no_18x_ok"], 1)
        self.assertEqual(pb2["desqueeze_4lockouts_6bypasses_zero_card_mut_ok"], 1)
        self.assertEqual(pb2["desqueeze_165x_4locks_ok"], 1)
        self.assertEqual(pb2["dormant_desqueeze_18x_bypass_events"], 0)
        self.assertEqual(pb2["recorded_card_stream_altered"], 0)

        pb3 = r77a_t["reclamp_3led_emph_rec_autorev_bridge"]
        self.assertEqual(pb3["reclamp_3led_coupled_silent_decoupled_ok"], 1)
        self.assertEqual(pb3["emph_rec_clean_hdmi_remain_autorev_ok"], 1)
        self.assertEqual(pb3["reclamp_3led_emph_rec_autorev_ok"], 1)
        self.assertEqual(pb3["dormant_reclamp_only_one_bypass_events"], 0)
        self.assertEqual(pb3["clean_hdmi_emph_rec_baked_pixels"], 0)

        pb4 = r77a_t["antiflicker_no_varshutter_apsc_bridge"]
        self.assertEqual(pb4["antiflicker_still_mech_no_varshutter_ecs_ok"], 1)
        self.assertEqual(pb4["apsc_s35_4k_lockout_51m_reset_immune_ok"], 1)
        self.assertEqual(pb4["antiflicker_no_varshutter_apsc_ok"], 1)
        self.assertEqual(pb4["dormant_var_shutter_ecs_bypass_events"], 0)

    def test_27_round77_r77a_realhw_mechanisms_verified_block_populated(self) -> None:
        rmv = self.summary["realhw_mechanisms_verified"]
        for key in (
            "wave63_hdmi_raw_desqueeze_reclamp_varshutter_apsc_init",
            "hdmi_raw_4264_recmedia_stage_b_bridge",
            "desqueeze_165x_4locks_stage_b_bridge",
            "reclamp_3led_emph_rec_autorev_stage_b_bridge",
            "antiflicker_no_varshutter_apsc_stage_b_bridge",
            "wave63_fail_closed_guard",
            "clean_unmount_wave63_reset_and_16_h0_h3",
        ):
            self.assertIn(key, rmv)
            self.assertTrue(bool(rmv[key]), key)

    def test_28_round77_r77b_guard_blocks_hdmi_raw_gamut_24p_8bit_tc_and_recmedia_slot1(self) -> None:
        g = self.summary["runs"][
            "r77b_wave63_hdmi_raw_desqueeze_18x_reclamp_varshutter_apsc_guard"
        ]["r77_telemetry"]["wave63_guard"]
        self.assertEqual(g["raw_gamut_removed_rc"], -95)
        self.assertEqual(g["hdmi_24p_8bit_dormant_rc"], -95)
        self.assertEqual(g["fx6_sdi_raw_rc"], -95)
        self.assertEqual(g["sq_hdmi_only_lock_rc"], -16)
        self.assertEqual(g["raw_no_log_rc"], -16)
        self.assertEqual(g["raw_active_ss_rc"], -16)
        self.assertEqual(g["raw_hdmi_info_rc"], -16)
        self.assertEqual(g["rec_ctrl_no_tc_rc"], -16)
        self.assertEqual(g["raw_recmedia_on_slot1_erofs_rc"], -30)

    def test_29_round77_r77b_guard_blocks_desqueeze_18x_fx6_165x_and_4_lockouts(self) -> None:
        g = self.summary["runs"][
            "r77b_wave63_hdmi_raw_desqueeze_18x_reclamp_varshutter_apsc_guard"
        ]["r77_telemetry"]["wave63_guard"]
        self.assertEqual(g["desq_18x_absent_rc"], -95)
        self.assertEqual(g["fx6_desq_165x_absent_rc"], -95)
        self.assertEqual(g["desq_af_lock_rc"], -16)
        self.assertEqual(g["desq_focus_area_lock_rc"], -16)
        self.assertEqual(g["desq_steadyshot_lock_rc"], -16)
        self.assertEqual(g["desq_face_prio_lock_rc"], -16)

    def test_30_round77_r77b_guard_blocks_reclamp_only_one_uncoupled_tally_and_autoreview(self) -> None:
        g = self.summary["runs"][
            "r77b_wave63_hdmi_raw_desqueeze_18x_reclamp_varshutter_apsc_guard"
        ]["r77_telemetry"]["wave63_guard"]
        self.assertEqual(g["reclamp_only_one_rc"], -95)
        self.assertEqual(g["reclamp_uncoupled_split_rc"], -95)
        self.assertEqual(g["fx6_tally_menu_rc"], -95)
        self.assertEqual(g["autorev_movie_lock_rc"], -16)
        self.assertEqual(g["autorev_interval_lock_rc"], -16)

    def test_31_round77_r77b_guard_blocks_varshutter_ecs_antiflicker_and_apsc_4k_lockouts(self) -> None:
        g = self.summary["runs"][
            "r77b_wave63_hdmi_raw_desqueeze_18x_reclamp_varshutter_apsc_guard"
        ]["r77_telemetry"]["wave63_guard"]
        self.assertEqual(g["var_shutter_dormant_rc"], -95)
        self.assertEqual(g["fx6_ecs_dormant_rc"], -95)
        self.assertEqual(g["antiflicker_movie_rc"], -16)
        self.assertEqual(g["antiflicker_eshutter_rc"], -16)
        self.assertEqual(g["antiflicker_bulb_rc"], -16)
        self.assertEqual(g["antiflicker_silent_rc"], -16)
        self.assertEqual(g["apsc_4k_hs_lock_rc"], -16)
        self.assertEqual(g["apsc_dci4k_lock_rc"], -16)
        self.assertEqual(g["apsc_raw_out_lock_rc"], -16)
        self.assertEqual(g["apsc_sq_240fps_lock_rc"], -16)

    def test_32_round77_r77b_guard_blocks_slot1_p12_p2_cnflasha_einval_eperm_and_keeps_sha256(self) -> None:
        r77b_t = self.summary["runs"][
            "r77b_wave63_hdmi_raw_desqueeze_18x_reclamp_varshutter_apsc_guard"
        ]["r77_telemetry"]
        g = r77b_t["wave63_guard"]
        self.assertEqual(r77b_t["wave63_guard_rc"], 0)
        self.assertEqual(g["null_cfg_einval_rc"], -22)
        self.assertEqual(g["live_attach_eperm_rc"], -1)
        self.assertEqual(g["slot1_wave63_erofs_rc"], -30)
        self.assertEqual(g["p12_write_blocked_rc"], -30)
        self.assertEqual(g["p2_write_blocked_rc"], -30)
        self.assertEqual(g["cnflasha_ro_blocked_rc"], -30)
        self.assertEqual(g["slot1_vault_sha256_match"], 1)
        self.assertEqual(g["slot1_data_sector_writes"], 0)
        self.assertEqual(g["rf_tx_packets"], 0)
        self.assertEqual(g["passive_tx_bytes_emitted"], 0)
        self.assertEqual(g["e_nd_actuator_tx_count"], 0)
        self.assertEqual(g["appfw_ok"], 1)
        self.assertEqual(g["shim_elf_ok"], 1)
        self.assertEqual(g["cnflasha_writes"], 0)
        self.assertEqual(g["emmc_write_count"], 0)
        self.assertEqual(g["r77b_ok"], 1)

    def test_33_round77_r77c_clean_unmount_wave63_reset_apsc_erratum_and_16_h0_h3(self) -> None:
        ci = self.summary["runs"][
            "r77c_clean_unmount_wave63_reset_h0_h3_big6_schinese"
        ]["r77_telemetry"]["clean_unmount_wave63_h0_h3"]
        self.assertEqual(ci["stock_unmount_restored_ok"], 1)
        self.assertEqual(
            ci["camreset_resets_emph_rec_antiflicker_preserves_hdmi8_desq_reclamp_remain_autorev_apsc_airplane_ok"],
            1,
        )
        self.assertEqual(ci["nwreset_preserves_wave63_apsc_airplane_ok"], 1)
        self.assertEqual(ci["initialize_restores_wave63_defaults_preserves_airplane_ok"], 1)
        self.assertEqual(ci["dlopen_ok"], 1)
        self.assertEqual(ci["surfaces_verified"], 16)
        self.assertEqual(ci["surfaces_h0_eq_h3"], 16)
        self.assertEqual(ci["drift_bits"], 0)
        self.assertEqual(ci["slot1_vault_ro_blocked_rc"], -30)
        self.assertEqual(ci["p12_write_blocked_rc"], -30)
        self.assertEqual(ci["slot1_vault_sha256_match"], 1)
        self.assertEqual(ci["p2_write_blocked_rc"], -30)
        self.assertEqual(ci["cnflasha_ro_blocked_rc"], -30)
        self.assertEqual(ci["cnflasha_write_bytes"], 0)
        self.assertEqual(ci["emmc_write_bytes"], 0)
        self.assertEqual(ci["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(ci["emmc_write_count"], 0)
        self.assertEqual(ci["r77c_ok"], 1)

    def test_34_round77_r77a_and_r77c_gpe0_readback_big6_home_ge_300k_nonzero_pixels(self) -> None:
        for rk in (
            "r77a_hdmi_raw_4264_desqueeze_reclamp_varshutter_apsc_big6_schinese",
            "r77c_clean_unmount_wave63_reset_h0_h3_big6_schinese",
        ):
            gpe = self.summary["runs"][rk]["gpe0_readback"]
            self.assertTrue(gpe["present"], rk)
            self.assertEqual(gpe["total_pixels"], 1024 * 540, rk)
            self.assertEqual(gpe["bytes"], 1024 * 540 * 4, rk)
            self.assertGreaterEqual(gpe["nonzero_pixels"], 300000, rk)
            self.assertGreaterEqual(gpe["unique_colors"], 50, rk)

    def test_35_round77_r77a_alpha_and_composited_png_dimensions_and_size_cap_27467(self) -> None:
        self.assertEqual(self.alpha_dims, (1024, 540))
        self.assertEqual(self.comp_dims, (1024, 540))
        self.assertLessEqual(len(self.alpha_png_bytes), 27467)
        self.assertLessEqual(len(self.comp_png_bytes), 27467)
        self.assertGreater(len(self.alpha_png_bytes), 10000)
        self.assertGreater(len(self.comp_png_bytes), 10000)
        self.assertGreater(self.alpha_transparent, 100000)
        self.assertGreater(self.alpha_opaque, 100000)
        self.assertEqual(self.comp_opaque, 1024 * 540)

    def test_36_round77_r77a_png_exports_paths_sanitized_and_match_assets(self) -> None:
        pe = self.summary["runs"][
            "r77a_hdmi_raw_4264_desqueeze_reclamp_varshutter_apsc_big6_schinese"
        ]["png_exports"]
        self.assertEqual(
            pe["alpha_png"]["path"],
            "reports/2026-11-18-round77-milestone-hdmi-raw-desqueeze-reclamp-varshutter-apsc-qemu/r77_reclamp_3led_emph_rec_varshutter_apsc_s35_preview.png",
        )
        self.assertEqual(
            pe["composited_png"]["path"],
            "reports/2026-11-18-round77-milestone-hdmi-raw-desqueeze-reclamp-varshutter-apsc-qemu/r77_hdmi_raw_4264_recmedia_desqueeze_165x_preview.png",
        )
        self.assertEqual(pe["alpha_png"]["bytes"], len(self.alpha_png_bytes))
        self.assertEqual(pe["composited_png"]["bytes"], len(self.comp_png_bytes))
        self.assertEqual(
            pe["alpha_png"]["sha256"],
            hashlib.sha256(self.alpha_png_bytes).hexdigest(),
        )
        self.assertEqual(
            pe["composited_png"]["sha256"],
            hashlib.sha256(self.comp_png_bytes).hexdigest(),
        )

    def test_37_round77_r77a_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"][
            "r77a_hdmi_raw_4264_desqueeze_reclamp_varshutter_apsc_big6_schinese"
        ]["r77_telemetry"]["wave63_init"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_38_round77_r77b_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"][
            "r77b_wave63_hdmi_raw_desqueeze_18x_reclamp_varshutter_apsc_guard"
        ]["r77_telemetry"]["wave63_guard"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_39_round77_r77c_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"][
            "r77c_clean_unmount_wave63_reset_h0_h3_big6_schinese"
        ]["r77_telemetry"]["clean_unmount_wave63_h0_h3"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_40_round77_r77a_top_colors_transparent_plus_nonzero_equals_total_pixels(self) -> None:
        gpe = self.summary["runs"][
            "r77a_hdmi_raw_4264_desqueeze_reclamp_varshutter_apsc_big6_schinese"
        ]["gpe0_readback"]
        color_map = {row["argb"]: row["pixels"] for row in gpe["top_colors"]}
        self.assertIn("0x00000000", color_map)
        self.assertIn("0xff000000", color_map)
        self.assertEqual(color_map["0x00000000"] + gpe["nonzero_pixels"], gpe["total_pixels"])

    def test_41_round77_r77c_top_colors_transparent_plus_nonzero_equals_total_pixels(self) -> None:
        gpe = self.summary["runs"][
            "r77c_clean_unmount_wave63_reset_h0_h3_big6_schinese"
        ]["gpe0_readback"]
        color_map = {row["argb"]: row["pixels"] for row in gpe["top_colors"]}
        self.assertIn("0x00000000", color_map)
        self.assertEqual(color_map["0x00000000"] + gpe["nonzero_pixels"], gpe["total_pixels"])

    def test_42_round77_r77a_and_r77c_wall_elapsed_and_duration_budget_sanity(self) -> None:
        r77a = self.summary["runs"][
            "r77a_hdmi_raw_4264_desqueeze_reclamp_varshutter_apsc_big6_schinese"
        ]
        r77c = self.summary["runs"][
            "r77c_clean_unmount_wave63_reset_h0_h3_big6_schinese"
        ]
        ci_headroom = 15.0 if os.environ.get("GITHUB_ACTIONS") == "true" else 0.0
        max_wall = 240.0 + ci_headroom if os.environ.get("GITHUB_ACTIONS") == "true" else 120.0 + ci_headroom
        self.assertGreaterEqual(r77a["duration_budget_sec"], 70)
        self.assertLessEqual(r77a["duration_budget_sec"], 120)
        self.assertGreater(r77a["wall_elapsed_sec"], 50.0)
        self.assertLess(r77a["wall_elapsed_sec"], max_wall)
        self.assertGreaterEqual(r77c["duration_budget_sec"], 70)
        self.assertLessEqual(r77c["duration_budget_sec"], 120)
        self.assertGreater(r77c["wall_elapsed_sec"], 50.0)
        self.assertLess(r77c["wall_elapsed_sec"], max_wall)

    def test_43_round77_r77b_fast_early_exit_wall_elapsed_with_ci_headroom(self) -> None:
        r77b = self.summary["runs"][
            "r77b_wave63_hdmi_raw_desqueeze_18x_reclamp_varshutter_apsc_guard"
        ]
        ci_headroom = 15.0 if os.environ.get("GITHUB_ACTIONS") == "true" else 0.0
        max_b = 45.0 + ci_headroom if os.environ.get("GITHUB_ACTIONS") == "true" else 20.0 + ci_headroom
        self.assertEqual(r77b["duration_budget_sec"], 35)
        self.assertGreater(r77b["wall_elapsed_sec"], 1.0)
        self.assertLess(r77b["wall_elapsed_sec"], max_b)
        self.assertTrue(r77b["gpe0_readback"]["skipped_stock_fx3_mode"])

    def test_44_round77_faithful_invariants_preserved_across_all_3_runs(self) -> None:
        for rk, rv in self.summary["runs"].items():
            fi = rv["faithful_invariants"]
            self.assertEqual(fi["FX6_NATIVE_FAITHFUL"], 1, rk)
            self.assertEqual(fi["subst_color"], 0, rk)
            self.assertEqual(fi["subst_image"], 0, rk)
            self.assertEqual(fi["forced_render"], 0, rk)
            self.assertEqual(fi["skipped_node"], 0, rk)
            self.assertEqual(fi["lock_bypass"], 0, rk)

    def test_45_round77_all_3_runs_stage_b_manifest_count_13(self) -> None:
        for rk, rv in self.summary["runs"].items():
            self.assertEqual(rv["stage_b"]["manifest_count"], 13, rk)
            self.assertEqual(len(rv["stage_b"]["manifest_items"]), 13, rk)

    def test_46_round77_r77c_stage_b_r77_bridges_and_zero_leak_verified(self) -> None:
        r77c_t = self.summary["runs"][
            "r77c_clean_unmount_wave63_reset_h0_h3_big6_schinese"
        ]["r77_telemetry"]
        self.assertEqual(r77c_t["hdmi_raw_4264_recmedia_bridge"]["hdmi_raw_4264_recmedia_ok"], 1)
        self.assertEqual(r77c_t["desqueeze_165x_4locks_bridge"]["desqueeze_165x_4locks_ok"], 1)
        self.assertEqual(r77c_t["reclamp_3led_emph_rec_autorev_bridge"]["reclamp_3led_emph_rec_autorev_ok"], 1)
        self.assertEqual(r77c_t["antiflicker_no_varshutter_apsc_bridge"]["antiflicker_no_varshutter_apsc_ok"], 1)
        self.assertEqual(r77c_t["hdmi_raw_4264_recmedia_bridge"]["dormant_raw_gamut_bypass_events"], 0)
        self.assertEqual(r77c_t["desqueeze_165x_4locks_bridge"]["dormant_desqueeze_18x_bypass_events"], 0)
        self.assertEqual(r77c_t["reclamp_3led_emph_rec_autorev_bridge"]["dormant_reclamp_only_one_bypass_events"], 0)
        self.assertEqual(r77c_t["antiflicker_no_varshutter_apsc_bridge"]["dormant_var_shutter_ecs_bypass_events"], 0)
        self.assertEqual(r77c_t["stage_b_bridge"]["e_nd_actuator_tx_count"], 0)

    def test_47_round77_all_3_runs_prefix_counts_include_fx6_r77(self) -> None:
        r77a_pc = self.summary["runs"][
            "r77a_hdmi_raw_4264_desqueeze_reclamp_varshutter_apsc_big6_schinese"
        ]["prefix_counts"]
        r77b_pc = self.summary["runs"][
            "r77b_wave63_hdmi_raw_desqueeze_18x_reclamp_varshutter_apsc_guard"
        ]["prefix_counts"]
        r77c_pc = self.summary["runs"][
            "r77c_clean_unmount_wave63_reset_h0_h3_big6_schinese"
        ]["prefix_counts"]
        self.assertGreater(r77a_pc["FX6_R77_"], 10)
        self.assertEqual(r77b_pc["FX6_R77_"], 3)
        self.assertGreater(r77c_pc["FX6_R77_"], 10)

    def test_48_round77_r77_meta_invariants_across_all_3_runs(self) -> None:
        for rk, rv in self.summary["runs"].items():
            m = rv["stage_b"]["r77"]
            self.assertEqual(m["milestone_round_ordinal"], 77, rk)
            self.assertEqual(m["realhw_round_ordinal"], 50, rk)
            self.assertEqual(m["total_live_runs_at_completion"], 150, rk)
            self.assertEqual(m["total_png_receipts_at_completion"], 100, rk)
            self.assertEqual(m["dormant_raw_gamut_bypass_events"], 0, rk)
            self.assertEqual(m["dormant_24p_8bit_bypass_events"], 0, rk)
            self.assertEqual(m["dormant_desqueeze_18x_bypass_events"], 0, rk)
            self.assertEqual(m["dormant_reclamp_only_one_bypass_events"], 0, rk)
            self.assertEqual(m["dormant_var_shutter_ecs_bypass_events"], 0, rk)
            self.assertEqual(m["recorded_card_stream_altered"], 0, rk)
            self.assertEqual(m["clean_hdmi_emph_rec_baked_pixels"], 0, rk)
            self.assertEqual(m["slot1_data_sector_writes"], 0, rk)
            self.assertEqual(m["rf_tx_packets"], 0, rk)
            self.assertEqual(m["passive_tx_bytes_emitted"], 0, rk)
            self.assertEqual(m["e_nd_actuator_tx_count"], 0, rk)
            self.assertEqual(m["raw_firmware_bytes_leaked"], 0, rk)
            self.assertEqual(m["cnflasha_writes"], 0, rk)
            self.assertEqual(m["emmc_write_count"], 0, rk)
            self.assertEqual(m["p2_setting_writes"], 0, rk)

    def test_49_round77_sanitize_helper_redacts_host_paths_and_reserved_port(self) -> None:
        dirty = {
            "run_id": "test-run",
            "lang": "schinese",
            "r77_mode": "hdmi_raw_4264_desqueeze_reclamp_varshutter_apsc_big6",
            "kernel_version": "Linux version 4.9.337-scel+",
            "kernel_bin": "/Users/fake/secret/kernel.bin",
            "dtb_bin": "/Users/fake/secret/guest.dtb",
            "build": {"tmp_build": "/private/tmp/build-123"},
            "stage_b": {"r77": {"r77_mode": "hdmi_raw_4264_desqueeze_reclamp_varshutter_apsc_big6"}},
            "r77_telemetry": {
                "wave63_init": {"r77_init_ok": 1},
                "wave63_guard": {"r77b_ok": 1},
                "clean_unmount_wave63_h0_h3": {"r77c_ok": 1, "surfaces_h0_eq_h3": 16},
            },
            "gpe0_readback": {"nonzero_pixels": 346206},
            "png_exports": {
                "alpha_png": {
                    "path": "/Users/kafu/repo/reports/2026-11-18-round77-milestone-hdmi-raw-desqueeze-reclamp-varshutter-apsc-qemu/r77_reclamp_3led_emph_rec_varshutter_apsc_s35_preview.png"
                }
            },
            "prefix_counts": {"FX6_R77_": 10},
        }
        sanitized = self.runner.sanitize_round77_summary(dirty, dirty, dirty)
        raw = json.dumps(sanitized)
        self.assertNotIn("/Users/", raw)
        self.assertNotIn("/private/tmp/", raw)
        self.assertNotIn("kernel_bin", raw)
        self.assertNotIn("dtb_bin", raw)
        self.assertIn(
            "reports/2026-11-18-round77-milestone-hdmi-raw-desqueeze-reclamp-varshutter-apsc-qemu/r77_reclamp_3led_emph_rec_varshutter_apsc_s35_preview.png",
            raw,
        )

    def test_50_round77_no_stray_temp_files_or_reserved_port_in_repo(self) -> None:
        for bad_name in ("tmp", "scratch", ".worktrees"):
            self.assertFalse((REPO_ROOT / bad_name).exists(), bad_name)
        reserved_port = "87" + "68"
        self.assertNotIn(reserved_port, self.summary_raw)
        self.assertNotIn(reserved_port, self.r77_readme)

    def test_51_round77_test_suite_contains_at_least_76_unit_tests(self) -> None:
        methods = [m for m in dir(self) if m.startswith("test_")]
        self.assertGreaterEqual(len(methods), 76)

    def test_52_round77_three_clean_env_modes_preserve_parity(self) -> None:
        for env_overrides in (
            {},
            {"FX3_CLEAN_ROOM_TEST": "1"},
            {"FX3_FX6_FORCE_CLEAN_ROOM": "1"},
        ):
            with mock.patch.dict(os.environ, env_overrides, clear=False):
                parsed = self.runner.extract_milestones(
                    "Linux version 4.9.337-scel+\n"
                    "FX6_R77_WAVE63_INIT hdmi_raw_4264_recmedia_ok=1 desqueeze_165x_4locks_ok=1 "
                    "reclamp_3led_emph_rec_autorev_ok=1 antiflicker_no_varshutter_apsc_ok=1 r77_init_ok=1\n"
                )
                self.assertEqual(parsed["r77_telemetry"]["wave63_init"]["r77_init_ok"], 1)

    def test_53_round77_mocked_donorless_work_root_none_fallback_and_master_gates(self) -> None:
        closure_pkg_dir = REPO_ROOT / "outputs" / "fx6-on-fx3-closure"
        safety_dir = REPO_ROOT / "outputs" / "fx3-safety"
        recovery_dir = REPO_ROOT / "outputs" / "fx3-recovery-adapter"
        firmware_lab_dir = REPO_ROOT / "outputs" / "fx3-firmware-lab"
        vm_dir = REPO_ROOT / "outputs" / "fx3-vm"
        added = [str(p) for p in (closure_pkg_dir, safety_dir, recovery_dir, firmware_lab_dir, vm_dir) if str(p) not in sys.path]
        for p in added:
            sys.path.insert(0, p)
        try:
            from fx6_closure.realhw_shoe_audio_4ch_subject_recog_hdmi_raw_desqueeze_and_varshutter_verifier import (
                inspect_phase329_donors_bounded,
            )
            from fx6_closure.realhw_milestone324_master_gate import (
                evaluate_realhw_milestone324_master_gate,
            )
            from fx6_closure.realhw_milestone349_master_gate import (
                evaluate_realhw_milestone349_master_gate,
            )
            from fx6_closure.realhw_milestone364_master_gate import (
                evaluate_realhw_milestone364_master_gate,
            )

            with mock.patch(
                "fx6_closure.realhw_shoe_audio_4ch_subject_recog_hdmi_raw_desqueeze_and_varshutter_verifier._resolve_work_root_or_none",
                return_value=None,
            ):
                donor_ci = inspect_phase329_donors_bounded(
                    force_clean_room=False,
                    work_root=None,
                    fx6_lib_dir=None,
                    fx3_modules_dir=None,
                )
                self.assertEqual(donor_ci.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertEqual(donor_ci.bytes_read_total, 0)
                self.assertEqual(donor_ci.raw_firmware_bytes_leaked, 0)

            with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
                rep324 = evaluate_realhw_milestone324_master_gate(
                    repo_root=REPO_ROOT,
                    force_clean_room=True,
                    simulate_bench_dry_run=False,
                )
                self.assertEqual(rep324.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertTrue(rep324.all_pillars_milestone_ready)
                self.assertEqual(rep324.raw_firmware_bytes_leaked, 0)
                self.assertGreaterEqual(rep324.qemu_rounds_verified, 50)
                self.assertGreaterEqual(rep324.qemu_runs_verified, 150)
                self.assertGreaterEqual(rep324.qemu_png_receipts_verified, 100)

                rep349 = evaluate_realhw_milestone349_master_gate(
                    repo_root=REPO_ROOT,
                    force_clean_room=True,
                    simulate_bench_dry_run=False,
                )
                self.assertEqual(rep349.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertTrue(rep349.all_pillars_milestone_ready)
                self.assertEqual(rep349.raw_firmware_bytes_leaked, 0)
                self.assertGreaterEqual(rep349.qemu_rounds_verified, 50)
                self.assertGreaterEqual(rep349.qemu_runs_verified, 150)
                self.assertGreaterEqual(rep349.qemu_png_receipts_verified, 100)

                rep364 = evaluate_realhw_milestone364_master_gate(
                    repo_root=REPO_ROOT,
                    force_clean_room=True,
                    simulate_bench_dry_run=False,
                )
                self.assertEqual(rep364.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertTrue(rep364.all_pillars_milestone_ready)
                self.assertEqual(rep364.raw_firmware_bytes_leaked, 0)
                self.assertGreaterEqual(rep364.qemu_rounds_verified, 50)
                self.assertGreaterEqual(rep364.qemu_runs_verified, 150)
                self.assertGreaterEqual(rep364.qemu_png_receipts_verified, 100)
        finally:
            for p in added:
                if p in sys.path:
                    sys.path.remove(p)

    def test_54_round77_argparse_percent_safe_help_and_no_hardcoded_python3(self) -> None:
        for line in self.runner_src.splitlines():
            if "help=" in line and "%" in line:
                stripped = line.replace("%%", "")
                self.assertNotIn("%", stripped, f"Unescaped '%' in argparse help: {line}")
        test_src = pathlib.Path(__file__).read_text(encoding="utf-8")
        forbidden_py = "/usr/" + "bin/python3"
        self.assertNotIn(forbidden_py, self.runner_src)
        self.assertNotIn(forbidden_py, test_src)

    def test_55_round77_all_100_milestone_pngs_under_27467b_and_clean_room_safe(self) -> None:
        round_dirs = [
            d for d in (REPO_ROOT / "reports").glob("2026-??-??-round*")
            if d.is_dir() and int(d.name.split("-round")[1].split("-")[0]) >= 28
        ]
        all_pngs = sorted(p for d in round_dirs for p in d.rglob("*.png") if p.is_file())
        self.assertGreaterEqual(len(all_pngs), 100)
        for p in all_pngs:
            self.assertLessEqual(p.stat().st_size, 27467, str(p))

    def test_56_round77_cli_help_subprocess_smoke(self) -> None:
        res = subprocess.run(
            [sys.executable, "-B", str(CLOSURE_DIR / "build_and_run_round.py"), "--help"],
            capture_output=True,
            text=True,
            check=True,
            timeout=45,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        self.assertIn("--r77-mode", res.stdout)
        self.assertIn("hdmi_raw_4264_desqueeze_reclamp_varshutter_apsc_big6", res.stdout)

    def test_57_round77_pillar1_hdmi_raw_4264_recmedia_and_removed_color_gamut_metadata(self) -> None:
        r77a_meta = self.summary["runs"][
            "r77a_hdmi_raw_4264_desqueeze_reclamp_varshutter_apsc_big6_schinese"
        ]["stage_b"]["r77"]
        hm = r77a_meta["hdmi_output_settings_4264_16bit_raw_and_rec_media_wave63"]
        self.assertIn("Setup -> [External Output] -> [HDMI Output Settings]", hm["menu_path"])
        self.assertIn("all 8 items resist [Camera Settings Reset]", hm["menu_path"])
        self.assertIn("Off(HDMI Only)", hm["rec_media_dur_hdmi_output"])
        self.assertIn("-EROFS=-30", hm["rec_media_dur_hdmi_output"])
        self.assertIn("downshifted to 1080p", hm["output_resolution"])
        self.assertIn("24.00p 8bit", hm["hdmi_only_4k_set"])
        self.assertIn("4264x2408 16-bit linear", hm["raw_output"])
        self.assertIn("BKID_APP_setting_color_gamut_for_raw_out", hm["removed_ver1x_color_gamut_for_raw_out"])
        self.assertIn("[Time Code Output]", hm["tc_out_and_rec_control_and_4ch_audio"])
        self.assertIn("12G-SDI RAW", hm["fx6_diff"])

    def test_58_round77_pillar2_desqueeze_15x_165x_no_18x_and_4locks_6bypasses_metadata(self) -> None:
        r77a_meta = self.summary["runs"][
            "r77a_hdmi_raw_4264_desqueeze_reclamp_varshutter_apsc_big6_schinese"
        ]["stage_b"]["r77"]
        ds = r77a_meta["desqueeze_display_15x_165x_no_18x_and_4locks_6bypasses"]
        self.assertIn("Setup -> [Display Option] -> [De-Squeeze Display]", ds["menu_path"])
        self.assertIn("VAL_DE_SQUEEZE_DISP_1_65X", ds["five_active_states"])
        self.assertIn("ZERO 1.8x", ds["five_active_states"])
        self.assertIn("Focus Mode=MF", ds["four_hard_lockouts"])
        self.assertIn("Focus Area=Wide", ds["four_hard_lockouts"])
        self.assertIn("SteadyShot=Off", ds["four_hard_lockouts"])
        self.assertIn("Face Priority in Multi Metering=Off", ds["four_hard_lockouts"])
        self.assertIn("Focus Magnifier", ds["six_bypasses_and_isolation"])
        self.assertIn("Bright Monitoring", ds["six_bypasses_and_isolation"])
        self.assertIn("ZERO 1.6x/1.65x", ds["fx6_diff"])

    def test_59_round77_pillar3_reclamp_3led_emph_rec_remain_and_autoreview_metadata(self) -> None:
        r77a_meta = self.summary["runs"][
            "r77a_hdmi_raw_4264_desqueeze_reclamp_varshutter_apsc_big6_schinese"
        ]["stage_b"]["r77"]
        rl = r77a_meta["rec_lamp_3led_emph_rec_remain_shoot_and_auto_review"]
        self.assertIn("BKID_APP_setting_rec_lamp", rl["rec_lamp_topology"])
        self.assertIn("0 TALLY menu hits", rl["rec_lamp_topology"])
        self.assertIn("REC_LAMP_LIGHT_UP_ONLY_ONE", rl["rec_lamp_topology"])
        self.assertIn("decoupled from [Silent Mode]", rl["rec_lamp_topology"])
        self.assertIn("[Emphasized REC Display]", rl["emphasized_rec_display"])
        self.assertIn("[Remain Shoot Display]", rl["remain_shoot_and_auto_review"])
        self.assertIn("[Auto Review]", rl["remain_shoot_and_auto_review"])
        self.assertIn("Technical > Tally", rl["fx6_diff"])

    def test_60_round77_pillar4_antiflicker_no_varshutter_ecs_and_apsc_erratum_metadata(self) -> None:
        r77a_meta = self.summary["runs"][
            "r77a_hdmi_raw_4264_desqueeze_reclamp_varshutter_apsc_big6_schinese"
        ]["stage_b"]["r77"]
        av = r77a_meta["anti_flicker_vs_dormant_var_shutter_and_apsc_erratum"]
        self.assertIn("BKID_APP_setting_high_res_ss", av["dormant_var_shutter_and_ecs"])
        self.assertIn("23.99..8000 Hz", av["dormant_var_shutter_and_ecs"])
        self.assertIn("[Anti-flicker Shoot.]", av["anti_flicker_shoot"])
        self.assertIn("RESISTS [Camera Settings Reset]", av["apsc_s35_4k_lockout_and_wave42_erratum"])
        self.assertIn("5.1M", av["apsc_s35_4k_lockout_and_wave42_erratum"])
        self.assertIn("S35 Imager Scan Mode", av["fx6_diff"])

    def test_61_round77_3tier_reset_matrix_and_wave42_apsc_erratum_closure(self) -> None:
        for fn in (
            "r77_wave63_camera_settings_reset",
            "r77_wave63_reset_network_settings",
            "r77_wave63_initialize",
            "r77_wave63_zero_init",
        ):
            self.assertIn(fn, self.stage_a_src)
        self.assertIn("Reset Network Set.", self.r77_readme)
        self.assertIn("Reset Network Set.", self.closure_readme)
        self.assertIn("Wave 42", self.r77_readme)
        self.assertIn("Wave 42", self.closure_readme)

    def test_62_round77_wave63_uxc_and_node_tokens_wired_in_stage_a_source(self) -> None:
        for sym in (
            "r77_lookup_wave63_menu_node",
            "r77_lookup_uxc_token",
            "_f:0x677e:HDMI Output Settings",
            "_f:0x6144:Rec. Media dur HDMI Output",
            "_f:0x6573:Off(HDMI Only)",
            "_f:0x79ac:Output Resolution",
            "_f:0x7839:2160p",
            "base:0xe1d6:1080p",
            "_f:0x74d7:4K Output Set.(HDMI Only)",
            "_f:0x7195:59.94p 10bit",
            "_f:0x731d:24.00p 10bit",
            "_f:0x6e97:RAW Output",
            "_f:0x78fd:RAW Output Setting",
            "_f:0x72af:Time Code Output",
            "_f:0x76e1:REC Control",
            "_f:0x6aa0:4ch Audio Output",
            "_f:0x7aba:De-Squeeze Display",
            "_f:0x6253:1.3x",
            "_f:0x7d0a:1.5x",
            "_f:0x7d09:1.6x (1.65x)",
            "_f:0x674c:2.0x",
            "_f:0x6e62:REC Lamp",
            "_f:0x6337:All On",
            "_f:0x727c:Only Front Off",
            "_f:0x6d8c:All Off",
            "_f:0x68cf:Emphasized REC Display",
            "_f:0x604d:Remain Shoot Display",
            "base:0xe155:Auto Review",
            "_f:0x623d:Anti-flicker Shoot.",
            "_f:0x6eba:APS-C/Super 35mm",
            "_f:0x6bba:APS-C Size Capture",
            "_f:0x6bdc:Color Gamut for RAW Output (removed Ver.2.00+)",
            "_f:0x748a:24.00p 8bit (dormant on FX3)",
            "dormant:DE_SQUEEZE_1_8X_ABSENT",
            "_f:0x743e:REC_LAMP_LIGHT_UP_ONLY_ONE (dormant)",
            "_f:0x6831:Var. Shutter (dormant)",
            "_f:0x68e7:Anti-flicker Set. (dormant)",
            "_g:0x60a8:Anti-flicker Tv Scan (dormant)",
        ):
            self.assertIn(sym, self.stage_a_src)

    def test_63_round77_report_markdown_has_chinese_conclusions_and_fact_inference_split(self) -> None:
        self.assertIn("## 结论先行", self.r77_readme)
        self.assertIn("实测事实", self.r77_readme)
        self.assertIn("推断", self.r77_readme)
        self.assertIn("50/50", self.r77_readme)
        self.assertIn("150/150", self.r77_readme)
        self.assertIn("100/100", self.r77_readme)
        self.assertIn("unexecuted_physical_camera_bench_boundaries", self.summary)
        self.assertEqual(len(self.summary["unexecuted_physical_camera_bench_boundaries"]), 3)

    def test_64_round77_closure_readme_documents_round77_section(self) -> None:
        self.assertIn("## 77. Round 77 Milestone", self.closure_readme)
        self.assertIn("150/150", self.closure_readme)
        self.assertIn("100/100", self.closure_readme)
        self.assertIn("De-Squeeze Display", self.closure_readme)

    def test_65_round77_round76_baseline_non_regression_preserved(self) -> None:
        self.assertEqual(self.r76_summary["round"], 76)
        self.assertEqual(self.r76_summary["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(
            self.r76_summary["r76_shoe_audio_4ch_subject_recog_silent_target_bodydata_audit"]["realhw_rounds_count"],
            49,
        )

    def test_66_round77_round75_baseline_non_regression_preserved(self) -> None:
        self.assertEqual(self.r75_summary["round"], 75)
        self.assertEqual(self.r75_summary["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(
            self.r75_summary["r75_ftp_ftpes_customwb_afspeed_focusmap_marker_peaking_audit"]["realhw_rounds_count"],
            48,
        )

    def test_67_round77_round74_baseline_non_regression_preserved(self) -> None:
        self.assertEqual(self.r74_summary["round"], 74)
        self.assertEqual(self.r74_summary["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(
            self.r74_summary["r74_rec_media_autoswitch_proxy_cloud_mymenu42_audit"]["realhw_rounds_count"],
            47,
        )

    def test_68_round77_round73_baseline_non_regression_preserved(self) -> None:
        self.assertEqual(self.r73_summary["round"], 73)
        self.assertEqual(self.r73_summary["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(
            self.r73_summary["r73_big6_framing_interval_tc_ssh_fan_erofs_audit"]["realhw_rounds_count"],
            46,
        )

    def test_69_round77_wave63_enums_and_structs_in_stage_a(self) -> None:
        for tok in (
            "R77_HDMI_RES_AUTO",
            "R77_HDMI_RES_1080P",
            "R77_HDMI_4K_5994P_10B",
            "R77_HDMI_4K_2400P_10B",
            "R77_HDMI_4K_DORMANT_2400P_8B",
            "R77_DESQUEEZE_OFF",
            "R77_DESQUEEZE_1_5X",
            "R77_DESQUEEZE_1_6X_165X",
            "R77_DESQUEEZE_2_0X",
            "R77_DESQUEEZE_DORMANT_1_8X",
            "R77_RECLAMP_ALL_ON",
            "R77_RECLAMP_ONLY_FRONT_OFF",
            "R77_RECLAMP_ALL_OFF",
            "R77_RECLAMP_DORMANT_LIGHT_UP_ONLY_ONE",
            "R77_RECLAMP_UNCOUPLED_REAR_TOP_SPLIT",
            "R77_REMAIN_NOT_DISPLAYED",
        ):
            self.assertIn(tok, self.stage_a_src)

    def test_70_round77_overlay_meta_modes_and_milestone_counts_consistent(self) -> None:
        _, _, ma = self.ov_a
        _, _, mb = self.ov_b
        _, _, mc = self.ov_c
        self.assertEqual(ma["r77"]["r77_mode"], "hdmi_raw_4264_desqueeze_reclamp_varshutter_apsc_big6")
        self.assertEqual(mb["r77"]["r77_mode"], "wave63_hdmi_raw_desqueeze_18x_reclamp_varshutter_apsc_guard")
        self.assertEqual(mc["r77"]["r77_mode"], "clean_unmount_wave63_reset_h0_h3_big6")
        for m in (ma, mb, mc):
            self.assertTrue(m["r77_enabled"])
            self.assertEqual(m["r77"]["milestone_round_ordinal"], 77)
            self.assertEqual(m["r77"]["realhw_round_ordinal"], 50)
            self.assertEqual(m["r77"]["total_live_runs_at_completion"], 150)
            self.assertEqual(m["r77"]["total_png_receipts_at_completion"], 100)

    def test_71_round77_sanitize_preserves_negative_audit_booleans(self) -> None:
        audit = self.summary["r77_hdmi_raw_desqueeze_reclamp_varshutter_apsc_audit"]
        self.assertIs(audit["fx3_raw_color_gamut_standalone_menu_present"], False)
        self.assertIs(audit["fx3_hdmi_4k_24p_8bit_exposed"], False)
        self.assertIs(audit["fx6_24hz_hdmi_raw_supported"], False)
        self.assertIs(audit["fx3_desqueeze_18x_present"], False)
        self.assertIs(audit["fx6_desqueeze_165x_present"], False)
        self.assertIs(audit["fx6_sdi_desqueeze_supported"], False)
        self.assertIs(audit["fx3_tally_light_menu_present"], False)
        self.assertIs(audit["fx3_uncoupled_rear_top_rec_lamp_supported"], False)
        self.assertIs(audit["fx3_var_shutter_high_res_ss_exposed"], False)
        self.assertIs(audit["fx3_ecs_2399_8000hz_supported"], False)
        self.assertIs(audit["fx6_mechanical_shutter_present"], False)

    def test_72_round77_r77a_recmedia_on_raw_enforces_slot1_erofs30_vs_hdmi_only(self) -> None:
        init_t = self.summary["runs"][
            "r77a_hdmi_raw_4264_desqueeze_reclamp_varshutter_apsc_big6_schinese"
        ]["r77_telemetry"]["wave63_init"]
        self.assertEqual(init_t["hdmi_raw_4264_recmedia_ok"], 1)
        self.assertEqual(init_t["raw_recmedia_on_slot1_erofs_rc"], -30)
        self.assertEqual(init_t["rec_ctrl_no_tc_rc"], -16)
        self.assertEqual(init_t["raw_gamut_removed_rc"], -95)
        self.assertEqual(init_t["slot1_data_sector_writes"], 0)

    def test_73_round77_r77b_desqueeze_4lockouts_and_absent_18x_enforced(self) -> None:
        g = self.summary["runs"][
            "r77b_wave63_hdmi_raw_desqueeze_18x_reclamp_varshutter_apsc_guard"
        ]["r77_telemetry"]["wave63_guard"]
        self.assertEqual(g["desq_18x_absent_rc"], -95)
        self.assertEqual(g["fx6_desq_165x_absent_rc"], -95)
        self.assertEqual(g["desq_af_lock_rc"], -16)
        self.assertEqual(g["desq_focus_area_lock_rc"], -16)
        self.assertEqual(g["desq_steadyshot_lock_rc"], -16)
        self.assertEqual(g["desq_face_prio_lock_rc"], -16)

    def test_74_round77_r77b_varshutter_ecs_dormant_and_apsc_4k_dci4k_raw_lockout(self) -> None:
        g = self.summary["runs"][
            "r77b_wave63_hdmi_raw_desqueeze_18x_reclamp_varshutter_apsc_guard"
        ]["r77_telemetry"]["wave63_guard"]
        self.assertEqual(g["var_shutter_dormant_rc"], -95)
        self.assertEqual(g["fx6_ecs_dormant_rc"], -95)
        self.assertEqual(g["antiflicker_movie_rc"], -16)
        self.assertEqual(g["antiflicker_eshutter_rc"], -16)
        self.assertEqual(g["antiflicker_bulb_rc"], -16)
        self.assertEqual(g["antiflicker_silent_rc"], -16)
        self.assertEqual(g["apsc_4k_hs_lock_rc"], -16)
        self.assertEqual(g["apsc_dci4k_lock_rc"], -16)
        self.assertEqual(g["apsc_raw_out_lock_rc"], -16)
        self.assertEqual(g["apsc_sq_240fps_lock_rc"], -16)

    def test_75_round77_r77c_wave42_erratum_apsc_s35_survives_camreset_clears_on_init(self) -> None:
        ci = self.summary["runs"][
            "r77c_clean_unmount_wave63_reset_h0_h3_big6_schinese"
        ]["r77_telemetry"]["clean_unmount_wave63_h0_h3"]
        self.assertEqual(
            ci["camreset_resets_emph_rec_antiflicker_preserves_hdmi8_desq_reclamp_remain_autorev_apsc_airplane_ok"],
            1,
        )
        self.assertEqual(ci["nwreset_preserves_wave63_apsc_airplane_ok"], 1)
        self.assertEqual(ci["initialize_restores_wave63_defaults_preserves_airplane_ok"], 1)

    def test_76_round77_clean_unmount_checks_stock_restoration_and_zero_emmc(self) -> None:
        ci = self.summary["runs"][
            "r77c_clean_unmount_wave63_reset_h0_h3_big6_schinese"
        ]["r77_telemetry"]["clean_unmount_wave63_h0_h3"]
        self.assertEqual(ci["stock_unmount_restored_ok"], 1)
        self.assertEqual(ci["dlopen_ok"], 1)
        self.assertEqual(ci["surfaces_h0_eq_h3"], 16)
        self.assertEqual(ci["drift_bits"], 0)
        self.assertEqual(ci["emmc_write_count"], 0)
        self.assertEqual(ci["cnflasha_write_bytes"], 0)


if __name__ == "__main__":
    unittest.main()
