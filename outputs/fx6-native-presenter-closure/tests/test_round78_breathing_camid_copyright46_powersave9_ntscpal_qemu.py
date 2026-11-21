#!/usr/bin/env python3
"""Offline four-mode unit tests for FX6-on-FX3 Round 78 (51/51 Real-HW Rounds R28..R78, 151st..153rd Live Runs -> 153/153 Total, 102/102 PNGs <= 27,467 B — Wave-64)."""
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
ROUND78_REPORT_DIR = (
    REPO_ROOT
    / "reports"
    / "2026-11-18-round78-breathing-camid-copyright46-powersave9-ntscpal-qemu"
)
WAVE64_SPEC_PATH = (
    REPO_ROOT
    / "reports"
    / "2026-11-17-global-sony-wave64-milestone-breathing-camid-reel-copyright-46ch-powersave-ntscpal-intel"
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


def _build_overlay_for_r78(
    runner,
    parent_cpio: pathlib.Path,
    fp,
    fv,
    fb,
    fake_run,
    jit_meta: Dict[str, Any],
    work: pathlib.Path,
    r78_mode: str,
    lang: str = "schinese",
    enable_r78: bool = True,
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
            enable_r77=True,
            r77_mode="hdmi_raw_4264_desqueeze_reclamp_varshutter_apsc_big6",
            enable_r78=enable_r78,
            r78_mode=r78_mode,
            sd_manifest_mode="valid",
            lang=lang,
            shim_bytes=b"SHIM",
        )


class TestRound78BreathingCamidCopyright46Powersave9NtscpalQemu(unittest.TestCase):
    EXPECTED_RUN_KEYS = (
        "r78a_breathing_camid_copyright46_powersave9_ntscpal_big6_schinese",
        "r78b_wave64_breathing_camid_copyright46_powersave9_ntscpal_guard",
        "r78c_clean_unmount_wave64_reset_h0_h3_big6_schinese",
    )

    runner: Any
    runner_src: str
    stage_a_src: str
    shim_src: str
    wave64_spec: str
    summary_raw: str
    summary: Dict[str, Any]
    r78_readme: str
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
    launcher_r78: Optional[bytes]
    shim_r78: Optional[bytes]
    shim_r77: Optional[bytes]
    r77_summary: Dict[str, Any]
    r76_summary: Dict[str, Any]
    r75_summary: Dict[str, Any]
    r74_summary: Dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = _load_closure_module("fx6_brr_r78_cached", "build_and_run_round.py")
        cls.runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")
        cls.stage_a_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        cls.shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        cls.wave64_spec = WAVE64_SPEC_PATH.read_text(encoding="utf-8")
        cls.summary_raw = (ROUND78_REPORT_DIR / "summary.json").read_text(encoding="utf-8")
        cls.summary = json.loads(cls.summary_raw)
        cls.r78_readme = (ROUND78_REPORT_DIR / "README.md").read_text(encoding="utf-8")
        cls.closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")

        alpha_p = (
            ROUND78_REPORT_DIR
            / "r78_copyright46_serial_powersave9_ntscpal_erofs_preview.png"
        )
        comp_p = (
            ROUND78_REPORT_DIR
            / "r78_breathing_120p_camid_reel_37char_sdhc_preview.png"
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
            cls.ov_a = _build_overlay_for_r78(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wa", "breathing_camid_copyright46_powersave9_ntscpal_big6", lang="schinese",
            )
            cls.ov_b = _build_overlay_for_r78(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wb", "wave64_breathing_camid_copyright46_powersave9_ntscpal_guard", lang="en",
            )
            cls.ov_c = _build_overlay_for_r78(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wc", "clean_unmount_wave64_reset_h0_h3_big6", lang="schinese",
            )
            cls.ov_off = _build_overlay_for_r78(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "woff", "breathing_camid_copyright46_powersave9_ntscpal_big6", enable_r78=False,
            )
            cls.invalid_mode_raised = False
            try:
                _build_overlay_for_r78(
                    cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                    tpath / "wbad", "invalid_r78_mode",
                )
            except ValueError:
                cls.invalid_mode_raised = True

            zig_bin = shutil.which("zig") or (
                str(cls.runner.ZIG) if cls.runner.ZIG.is_file() else None
            )
            if zig_bin is not None:
                verify_r78_out = tpath / "fx6-stage-a-verify-r78"
                shim_r78_out = tpath / "libgrm-fbinit9-r78.so"
                shim_r77_out = tpath / "libgrm-fbinit9-r77.so"
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
                        str(verify_r78_out),
                    ],
                    [
                        zig_bin,
                        "cc",
                        "-target",
                        "aarch64-linux-gnu.2.25",
                        "-O0",
                        "-shared",
                        "-fPIC",
                        "-DFX6_ROUND=78",
                        str(CLOSURE_DIR / "libgrm-fbinit9.c"),
                        "-ldl",
                        "-lpthread",
                        "-o",
                        str(shim_r78_out),
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
                ):
                    cls.runner.subprocess.run(cmd, check=True, timeout=120)
                cls.launcher_r78 = verify_r78_out.read_bytes()
                cls.shim_r78 = shim_r78_out.read_bytes()
                cls.shim_r77 = shim_r77_out.read_bytes()
            else:
                cls.launcher_r78 = None
                cls.shim_r78 = None
                cls.shim_r77 = None

        cls.r77_summary = json.loads(
            (
                REPO_ROOT
                / "reports"
                / "2026-11-18-round77-milestone-hdmi-raw-desqueeze-reclamp-varshutter-apsc-qemu"
                / "summary.json"
            ).read_text(encoding="utf-8")
        )
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

    def test_01_wave64_global_spec_present_and_covers_all_4_pillars(self) -> None:
        self.assertTrue(WAVE64_SPEC_PATH.is_file())
        for needle in (
            "Breathing Comp.",
            "BKID_APP_setting_lens_comp_breathing",
            "SEL100F28GM",
            "SEL14TC",
            "SEL20TC",
            "Catalyst Prepare",
            "Catalyst Browse",
            "File Settings",
            "Cam ID + Reel#",
            "A001C001_230101AB",
            "C999 -> D001",
            "Title Name Settings",
            "SDHC",
            "4 GB",
            "TC/Media > Clip Name Format",
            "Copyright Info",
            "Write Copyright Info",
            "BKID_APP_setting_write_serial_number_still_movie",
            "CAMSET*.DAT",
            "Power Save Start Time",
            "Auto Power OFF Temp.",
            "Power Save by Monitor",
            "BKID_APP_setting_monitor_power_linkage",
            "NTSC/PAL Selector",
            "Running on PAL.",
        ):
            self.assertIn(needle, self.wave64_spec)

    def test_02_round78_summary_schema_milestone_and_zero_leaks(self) -> None:
        self.assertNotIn("/Users/", self.summary_raw)
        self.assertNotIn("/private/tmp/", self.summary_raw)
        self.assertNotIn("/tmp/round78", self.summary_raw)
        self.assertEqual(
            self.summary["schema"],
            "fx6-on-fx3-round78-breathing-camid-copyright46-powersave9-ntscpal-qemu-v1",
        )
        self.assertEqual(self.summary["round"], 78)
        self.assertIn("51/51 Real-HW Rounds", self.summary["milestone"])
        self.assertIn("153/153 Live Runs", self.summary["milestone"])
        self.assertIn("102/102 PNGs <= 27,467 B", self.summary["milestone"])
        self.assertEqual(self.summary["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(tuple(self.summary["runs"].keys()), self.EXPECTED_RUN_KEYS)

    def test_03_round78_cli_accepts_round78_and_all_3_r78_modes(self) -> None:
        self.assertIn(", 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78]", self.runner_src)
        for mode in (
            "breathing_camid_copyright46_powersave9_ntscpal_big6",
            "wave64_breathing_camid_copyright46_powersave9_ntscpal_guard",
            "clean_unmount_wave64_reset_h0_h3_big6",
        ):
            self.assertIn(mode, self.runner_src)

    def test_04_round78_overlay_rejects_invalid_r78_mode(self) -> None:
        self.assertTrue(self.invalid_mode_raised)

    def test_05_round78_overlay_r78a_injects_etc_fx6_stage_r78_and_appfw_launch(self) -> None:
        replacements, additions, meta = self.ov_a
        self.assertTrue(meta["r78_enabled"])
        self.assertIn("etc/fx6_stage_r78", additions)
        self.assertIn("etc/fx6_r78_libjit.so", additions)
        r78_cfg = additions["etc/fx6_stage_r78"][0].decode("utf-8")
        self.assertIn("stage_r78=1", r78_cfg)
        self.assertIn("r78_mode=breathing_camid_copyright46_powersave9_ntscpal_big6", r78_cfg)
        self.assertIn("milestone_51st_realhw_153rd_live_102_pngs=1", r78_cfg)
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("/usr/bin/appfw-launch", init_txt)
        self.assertNotIn("--r78-wave64-guard", init_txt)

    def test_06_round78_overlay_r78b_injects_early_guard_probe_and_poweroff(self) -> None:
        replacements, _, meta = self.ov_b
        self.assertEqual(
            meta["r78"]["r78_mode"],
            "wave64_breathing_camid_copyright46_powersave9_ntscpal_guard",
        )
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("--r78-wave64-guard", init_txt)
        self.assertIn("FX6_R78_WAVE64_GUARD_RC=", init_txt)
        self.assertIn("FX6_R78_WAVE64_GUARD_EXIT", init_txt)
        self.assertIn("poweroff -f", init_txt)

    def test_07_round78_overlay_r78c_integrated_runs_stage_b_big6(self) -> None:
        replacements, additions, meta = self.ov_c
        self.assertEqual(meta["r78"]["r78_mode"], "clean_unmount_wave64_reset_h0_h3_big6")
        r78_cfg = additions["etc/fx6_stage_r78"][0].decode("utf-8")
        self.assertIn("r78_mode=clean_unmount_wave64_reset_h0_h3_big6", r78_cfg)
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("/usr/bin/appfw-launch", init_txt)
        self.assertNotIn("--r78-wave64-guard", init_txt)

    def test_08_round78_overlay_disabled_when_enable_r78_false(self) -> None:
        _, additions, meta = self.ov_off
        self.assertFalse(meta["r78_enabled"])
        self.assertNotIn("etc/fx6_stage_r78", additions)
        self.assertNotIn("etc/fx6_r78_libjit.so", additions)
        self.assertNotIn("r78", meta)

    def test_09_round78_stage_a_c_source_contains_all_3_wave64_probes(self) -> None:
        for sym in (
            "setup_r78_breathing_camid_copyright46_powersave9_ntscpal_probe",
            "run_r78_wave64_guard_probe",
            "run_r78_clean_unmount_wave64_h0_h3_probe",
            "r78_wave64_initialize",
            "r78_wave64_zero_init",
            "r78_wave64_camera_settings_reset",
            "r78_wave64_reset_network_settings",
            "r78_configure_breathing_comp",
            "r78_evaluate_catalyst_breathing",
            "r78_configure_movie_file_settings",
            "r78_configure_copyright_and_serial",
            "r78_export_camset_dat",
            "r78_configure_power_save_and_ntsc_pal",
            "FX6_R78_WAVE64_INIT",
            "FX6_R78_WAVE64_GUARD",
            "FX6_R78_CLEAN_UNMOUNT_WAVE64_H0_H3",
            "--r78-wave64-guard",
            "--r78-clean-unmount-wave64-h0-h3",
            "/etc/fx6_stage_r78",
        ):
            self.assertIn(sym, self.stage_a_src)

    def test_10_round78_shim_c_source_contains_r78_guarded_bridges(self) -> None:
        self.assertIn("#if FX6_ROUND >= 78", self.shim_src)
        for sym in (
            "FX6_R78_BREATHING_120P_CATALYST_BRIDGE",
            "FX6_R78_CAMID_REEL_37CHAR_SDHC_BRIDGE",
            "FX6_R78_COPYRIGHT46_SERIAL_CAMSET_BRIDGE",
            "FX6_R78_POWERSAVE9_NTSCPAL_EROFS_BRIDGE",
            "FX6_R78_LANG_TELEMETRY",
            "FX6_STAGE_B_R78_BRIDGE",
        ):
            self.assertIn(sym, self.shim_src)

    def test_11_round78_compile_launcher_and_shim_aarch64_elf_symbols(self) -> None:
        if self.launcher_r78 is None or self.shim_r78 is None:
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertEqual(self.launcher_r78[:4], b"\x7fELF")
        self.assertEqual(self.shim_r78[:4], b"\x7fELF")
        self.assertEqual(struct.unpack_from("<H", self.shim_r78, 18)[0], 183)
        self.assertIn(b"FX6_R78_BREATHING_120P_CATALYST_BRIDGE", self.shim_r78)
        self.assertIn(b"FX6_R78_CAMID_REEL_37CHAR_SDHC_BRIDGE", self.shim_r78)
        self.assertIn(b"FX6_R78_COPYRIGHT46_SERIAL_CAMSET_BRIDGE", self.shim_r78)
        self.assertIn(b"FX6_R78_POWERSAVE9_NTSCPAL_EROFS_BRIDGE", self.shim_r78)

    def test_12_round78_shim_round77_backward_compat_excludes_r78_bridges(self) -> None:
        if self.shim_r77 is None:
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertIn(b"FX6_R77_HDMI_RAW_4264_RECMEDIA_BRIDGE", self.shim_r77)
        self.assertNotIn(b"FX6_R78_BREATHING_120P_CATALYST_BRIDGE", self.shim_r77)

    def test_13_round78_parse_log_extracts_all_10_r78_prefixes_and_rc(self) -> None:
        serial_text = (
            "\n".join(
                [
                    "Linux version 4.9.337-scel+ (sony@fx3)",
                    "FX6_R78_WAVE64_INIT fx3_wave64_nodes_ok=1 uxc_tokens_ok=1 breathing_120p_catalyst_ok=1 camid_reel_37char_sdhc_ok=1 copyright46_serial_camset_ok=1 powersave9_ntscpal_ok=1 emmc_write_count=0 r78_init_ok=1",
                    "FX6_R78_BREATHING_120P_CATALYST_BRIDGE breathing_resettable_100_120p_lock_ok=1 breathing_whitelist_macro_tc_ok=1 breathing_catalyst_prepare_boundary_ok=1 breathing_120p_catalyst_ok=1 cnflasha_writes=0 emmc_write_count=0 r78_bridge_ok=1",
                    "FX6_R78_CAMID_REEL_37CHAR_SDHC_BRIDGE camid_reel_c999_d001_rollover_ok=1 title37_sdhc_4gb_split_erofs_ok=1 camid_reel_37char_sdhc_ok=1 dormant_sdhc_camid_reel_bypass_events=0 cnflasha_writes=0 emmc_write_count=0",
                    "FX6_R78_COPYRIGHT46_SERIAL_CAMSET_BRIDGE copyright46_4items_reset_erratum_fixed_ok=1 serial_camset_allowed_copyright_excl_ok=1 copyright46_serial_camset_ok=1 dormant_copyright_camset_export_events=0 cnflasha_writes=0 emmc_write_count=0",
                    "FX6_R78_POWERSAVE9_NTSCPAL_EROFS_BRIDGE powersave_9bypasses_dormant_monitor_ok=1 ntsc_pal_reboot_slot1_erofs30_ok=1 powersave9_ntscpal_ok=1 dormant_power_save_by_monitor_bypass_events=0 cnflasha_writes=0 emmc_write_count=0",
                    "FX6_R78_LANG_TELEMETRY lang=schinese font_bank=23 str_bank=19 milestone_51st_realhw_153rd_live_102_pngs=1 r78_bridge_ok=1",
                    "FX6_STAGE_B_R78_BRIDGE round=78 faithful=1 nop_count=0 milestone_51st_realhw_153rd_live_102_pngs=1 emmc_write_count=0",
                    "FX6_R78_WAVE64_GUARD breathing_thirdparty_rc=-95 catalyst_browse_rc=-95 ps_monitor_dormant_rc=-95 slot1_ntsc_pal_erofs_rc=-30 live_attach_eperm_rc=-1 r78b_ok=1",
                    "FX6_R78_WAVE64_GUARD_RC=0",
                    "FX6_R78_CLEAN_UNMOUNT_WAVE64_H0_H3 stock_unmount_restored_ok=1 camreset_resets_breathing_preserves_lens3_fileset37_copyright46_serial_powersave_ntscpal_airplane_ok=1 nwreset_preserves_wave64_airplane_ok=1 initialize_restores_wave64_defaults_clears_pii_preserves_airplane_ok=1 surfaces_h0_eq_h3=16 r78c_ok=1",
                ]
            )
            + "\n"
        )
        parsed = self.runner.extract_milestones(serial_text)
        r78_t = parsed["r78_telemetry"]
        self.assertEqual(r78_t["wave64_guard_rc"], 0)
        self.assertEqual(r78_t["wave64_init"]["breathing_120p_catalyst_ok"], 1)
        self.assertEqual(r78_t["breathing_120p_catalyst_bridge"]["breathing_120p_catalyst_ok"], 1)
        self.assertEqual(r78_t["camid_reel_37char_sdhc_bridge"]["camid_reel_37char_sdhc_ok"], 1)
        self.assertEqual(r78_t["copyright46_serial_camset_bridge"]["copyright46_serial_camset_ok"], 1)
        self.assertEqual(r78_t["powersave9_ntscpal_erofs_bridge"]["powersave9_ntscpal_ok"], 1)
        self.assertEqual(r78_t["lang_telemetry"]["lang"], "schinese")
        self.assertEqual(r78_t["lang_telemetry"]["milestone_51st_realhw_153rd_live_102_pngs"], 1)
        self.assertEqual(r78_t["stage_b_bridge"]["round"], 78)
        self.assertEqual(r78_t["wave64_guard"]["r78b_ok"], 1)
        self.assertEqual(r78_t["clean_unmount_wave64_h0_h3"]["surfaces_h0_eq_h3"], 16)
        self.assertEqual(parsed["prefix_counts"]["FX6_R78_"], 9)

    def test_14_round78_parse_log_defaults_when_no_r78_lines_present(self) -> None:
        parsed = self.runner.extract_milestones("Linux version 4.9.337-scel+\n")
        self.assertIsNone(parsed["r78_telemetry"])
        self.assertEqual(parsed["prefix_counts"].get("FX6_R78_", 0), 0)

    def test_15_round78_runner_preserves_r77_prefix_and_uses_r78_stage_label(self) -> None:
        self.assertIn('if args.round >= 77:\n        tmp_prefix = "fx6-r77"', self.runner_src)
        self.assertIn('if args.round >= 78:\n        tmp_prefix = "fx6-r78"', self.runner_src)
        self.assertIn(
            "51RealHw153rdLiveWave64Breathing120pCamIdReel37CharCopyright46SerialPowerSave9NtscPalErofs30",
            self.runner_src,
        )
        self.assertIn(", 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78]", self.runner_src)

    def test_16_round78_runner_portability_and_sanitizer_helper(self) -> None:
        self.assertIn('shutil.which("zig")', self.runner_src)
        self.assertIn("FX6_SCRATCH_DIR", self.runner_src)
        self.assertIn("def sanitize_round78_summary(", self.runner_src)
        self.assertNotIn("/usr/" + "bin/python3", self.runner_src)

    def test_17_round78_summary_json_top_level_schema_and_milestone_metadata(self) -> None:
        d = self.summary
        self.assertEqual(
            d["schema"],
            "fx6-on-fx3-round78-breathing-camid-copyright46-powersave9-ntscpal-qemu-v1",
        )
        self.assertEqual(d["round"], 78)
        self.assertIn("51/51 Real-HW Rounds", d["milestone"])
        self.assertIn("153/153 Live Runs", d["milestone"])
        self.assertIn("102/102 PNGs <= 27,467 B", d["milestone"])
        self.assertEqual(d["date"], "2026-11-18")
        self.assertIn("4.9.337-scel+", d["kernel_version"])
        self.assertEqual(d["raw_firmware_bytes_leaked"], 0)

    def test_18_round78_summary_json_zero_host_path_scratch_and_elapsed_leaks(self) -> None:
        for forbidden in (
            "/Users/",
            "/private/tmp/",
            "/var/folders/",
            "/tmp/round78",
            "work/_scratch/",
            "work/_tests/",
            "elapsed_seconds",
            ":87" + "68",
        ):
            self.assertNotIn(forbidden, self.summary_raw)

    def test_19_round78_summary_audit_block_confirms_51_rounds_153_runs_102_pngs(self) -> None:
        audit = self.summary["r78_breathing_camid_copyright46_powersave9_ntscpal_audit"]
        self.assertEqual(audit["round"], 78)
        self.assertGreaterEqual(audit["realhw_rounds_count"], 51)
        self.assertGreaterEqual(audit["total_live_runs"], 153)
        self.assertGreaterEqual(audit["total_png_receipts"], 102)
        self.assertGreaterEqual(audit["milestone324_qemu_rounds"], 51)
        self.assertGreaterEqual(audit["milestone324_qemu_runs"], 153)
        self.assertGreaterEqual(audit["milestone324_png_receipts"], 102)
        self.assertEqual(audit["total_runs"], 3)
        negative_keys = {
            "fx3_catalyst_browse_breathing_supported",
            "fx3_sdhc_camid_reel_supported",
            "fx3_power_save_by_monitor_exposed",
            "fx3_powersave_20s_60m_240m_exposed",
            "fx6_exif_copyright_info_supported",
            "fx6_power_setting_option_menu_present",
        }
        for nk in negative_keys:
            self.assertIs(audit[nk], False, nk)
        for k, v in audit.items():
            if isinstance(v, bool) and k not in negative_keys:
                self.assertTrue(v, f"Expected audit boolean {k} to be True")

    def test_20_round78_all_3_runs_present_with_kernel_4_9_337_and_zero_crashes_writes(self) -> None:
        runs = self.summary["runs"]
        self.assertEqual(list(runs.keys()), list(self.EXPECTED_RUN_KEYS))
        for rk, rv in runs.items():
            self.assertEqual(rv["round"], 78, rk)
            self.assertIn("4.9.337-scel+", rv["kernel_version"], rk)
            self.assertEqual(rv["nop_count"], 0, rk)
            self.assertEqual(rv["crashes"], 0, rk)
            self.assertEqual(rv["emmc_write_count"], 0, rk)
            self.assertGreater(rv["wall_elapsed_sec"], 0.0, rk)

    def test_21_round78_r78a_pillar1_breathing_100_120p_macro_tc_and_catalyst_prepare(self) -> None:
        init_t = self.summary["runs"][
            "r78a_breathing_camid_copyright46_powersave9_ntscpal_big6_schinese"
        ]["r78_telemetry"]["wave64_init"]
        self.assertEqual(init_t["fx3_wave64_nodes_ok"], 1)
        self.assertEqual(init_t["uxc_tokens_ok"], 1)
        self.assertEqual(init_t["breathing_120p_catalyst_ok"], 1)
        self.assertEqual(init_t["breathing_120p_lock_rc"], -16)
        self.assertEqual(init_t["breathing_macro_lock_rc"], -16)
        self.assertEqual(init_t["catalyst_browse_rc"], -95)
        self.assertEqual(init_t["dormant_catalyst_browse_breathing_events"], 0)
        self.assertEqual(init_t["dormant_breathing_120p_bypass_events"], 0)

    def test_22_round78_r78a_pillar2_camid_reel_c999_d001_37char_sdhc_and_slot1_erofs(self) -> None:
        init_t = self.summary["runs"][
            "r78a_breathing_camid_copyright46_powersave9_ntscpal_big6_schinese"
        ]["r78_telemetry"]["wave64_init"]
        self.assertEqual(init_t["camid_reel_37char_sdhc_ok"], 1)
        self.assertEqual(init_t["sdhc_camid_lock_rc"], -16)
        self.assertEqual(init_t["slot1_reel_erofs_rc"], -30)
        self.assertEqual(init_t["dormant_sdhc_camid_reel_bypass_events"], 0)
        self.assertEqual(init_t["slot1_data_sector_writes"], 0)

    def test_23_round78_r78a_pillar3_copyright46_serial_still_movie_and_camset_exclusion(self) -> None:
        init_t = self.summary["runs"][
            "r78a_breathing_camid_copyright46_powersave9_ntscpal_big6_schinese"
        ]["r78_telemetry"]["wave64_init"]
        self.assertEqual(init_t["copyright46_serial_camset_ok"], 1)
        self.assertEqual(init_t["copyright_camset_excl_rc"], -95)
        self.assertEqual(init_t["dormant_copyright_camset_export_events"], 0)
        self.assertEqual(init_t["copyright_pii_leaked_bytes"], 0)

    def test_24_round78_r78a_pillar4_powersave9_dormant_monitor_ntscpal_and_vaults(self) -> None:
        init_t = self.summary["runs"][
            "r78a_breathing_camid_copyright46_powersave9_ntscpal_big6_schinese"
        ]["r78_telemetry"]["wave64_init"]
        self.assertEqual(init_t["powersave9_ntscpal_ok"], 1)
        self.assertEqual(init_t["ps_monitor_dormant_rc"], -95)
        self.assertEqual(init_t["slot1_ntsc_pal_erofs_rc"], -30)
        self.assertEqual(init_t["dormant_power_save_by_monitor_bypass_events"], 0)
        self.assertEqual(init_t["dormant_powersave_20s_60m_240m_bypass_events"], 0)
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
        self.assertEqual(init_t["r78_init_ok"], 1)

    def test_25_round78_r78a_stage_b_schinese_lang_telemetry_and_bridge(self) -> None:
        r78a_t = self.summary["runs"][
            "r78a_breathing_camid_copyright46_powersave9_ntscpal_big6_schinese"
        ]["r78_telemetry"]
        lt = r78a_t["lang_telemetry"]
        self.assertEqual(lt["lang"], "schinese")
        self.assertEqual(lt["bk4_lang_id"], "0x02cf019c")
        self.assertEqual(lt["bk4_lang_val"], "0x19")
        self.assertEqual(lt["lang_enum"], "0x2b45_CHINESE_SIMPLIFIED")
        self.assertEqual(lt["font_bank"], 23)
        self.assertEqual(lt["str_bank"], 19)
        self.assertEqual(lt["gpe_fb"], 0)
        self.assertEqual(
            lt["round78_51realhw_wave64_breathing_camid_copyright46_powersave9_ntscpal"], 1
        )
        self.assertEqual(lt["milestone_51st_realhw_153rd_live_102_pngs"], 1)
        self.assertEqual(lt["dormant_catalyst_browse_breathing_events"], 0)
        self.assertEqual(lt["dormant_breathing_120p_bypass_events"], 0)
        self.assertEqual(lt["dormant_sdhc_camid_reel_bypass_events"], 0)
        self.assertEqual(lt["dormant_copyright_camset_export_events"], 0)
        self.assertEqual(lt["dormant_power_save_by_monitor_bypass_events"], 0)
        self.assertEqual(lt["dormant_powersave_20s_60m_240m_bypass_events"], 0)
        self.assertEqual(lt["copyright_pii_leaked_bytes"], 0)
        self.assertEqual(lt["slot1_data_sector_writes"], 0)
        self.assertEqual(lt["rf_tx_packets"], 0)
        self.assertEqual(lt["raw_firmware_bytes_leaked"], 0)

        sb = r78a_t["stage_b_bridge"]
        self.assertEqual(sb["round"], 78)
        self.assertEqual(sb["faithful"], 1)
        self.assertEqual(sb["nop_count"], 0)
        self.assertEqual(sb["breathing_resettable_100_120p_sq_catalyst_prepare_ok"], 1)
        self.assertEqual(sb["camid_reel_c999_d001_37char_sdhc_4gb_split_ok"], 1)
        self.assertEqual(sb["copyright46_serial_r57_erratum_camset_excl_ok"], 1)
        self.assertEqual(sb["powersave_9bypasses_dormant_monitor_ntscpal_erofs30"], 1)
        self.assertEqual(sb["milestone_51st_realhw_153rd_live_102_pngs"], 1)

    def test_26_round78_r78a_stage_b_4_pillar_bridges_verified(self) -> None:
        r78a_t = self.summary["runs"][
            "r78a_breathing_camid_copyright46_powersave9_ntscpal_big6_schinese"
        ]["r78_telemetry"]
        pb1 = r78a_t["breathing_120p_catalyst_bridge"]
        self.assertEqual(pb1["breathing_resettable_100_120p_lock_ok"], 1)
        self.assertEqual(pb1["breathing_whitelist_macro_tc_ok"], 1)
        self.assertEqual(pb1["breathing_catalyst_prepare_boundary_ok"], 1)
        self.assertEqual(pb1["breathing_120p_catalyst_ok"], 1)
        self.assertEqual(pb1["dormant_catalyst_browse_breathing_events"], 0)
        self.assertEqual(pb1["dormant_breathing_120p_bypass_events"], 0)
        self.assertEqual(pb1["r78_bridge_ok"], 1)

        pb2 = r78a_t["camid_reel_37char_sdhc_bridge"]
        self.assertEqual(pb2["camid_reel_c999_d001_rollover_ok"], 1)
        self.assertEqual(pb2["title37_sdhc_4gb_split_erofs_ok"], 1)
        self.assertEqual(pb2["camid_reel_37char_sdhc_ok"], 1)
        self.assertEqual(pb2["dormant_sdhc_camid_reel_bypass_events"], 0)
        self.assertEqual(pb2["slot1_data_sector_writes"], 0)

        pb3 = r78a_t["copyright46_serial_camset_bridge"]
        self.assertEqual(pb3["copyright46_4items_reset_erratum_fixed_ok"], 1)
        self.assertEqual(pb3["serial_camset_allowed_copyright_excl_ok"], 1)
        self.assertEqual(pb3["copyright46_serial_camset_ok"], 1)
        self.assertEqual(pb3["dormant_copyright_camset_export_events"], 0)
        self.assertEqual(pb3["copyright_pii_leaked_bytes"], 0)

        pb4 = r78a_t["powersave9_ntscpal_erofs_bridge"]
        self.assertEqual(pb4["powersave_9bypasses_dormant_monitor_ok"], 1)
        self.assertEqual(pb4["ntsc_pal_reboot_slot1_erofs30_ok"], 1)
        self.assertEqual(pb4["powersave9_ntscpal_ok"], 1)
        self.assertEqual(pb4["dormant_power_save_by_monitor_bypass_events"], 0)
        self.assertEqual(pb4["dormant_powersave_20s_60m_240m_bypass_events"], 0)
        self.assertEqual(pb4["slot1_data_sector_writes"], 0)

    def test_27_round78_r78a_realhw_mechanisms_verified_block_populated(self) -> None:
        rmv = self.summary["realhw_mechanisms_verified"]
        for key in (
            "wave64_breathing_camid_copyright46_powersave9_ntscpal_init",
            "breathing_120p_catalyst_stage_b_bridge",
            "camid_reel_37char_sdhc_stage_b_bridge",
            "copyright46_serial_camset_stage_b_bridge",
            "powersave9_ntscpal_erofs_stage_b_bridge",
            "wave64_fail_closed_guard",
            "clean_unmount_wave64_reset_and_16_h0_h3",
        ):
            self.assertIn(key, rmv)
            self.assertTrue(bool(rmv[key]), key)

    def test_28_round78_r78b_guard_blocks_breathing_100_120p_sq_macro_tc_raw_ciz_catalyst(self) -> None:
        g = self.summary["runs"][
            "r78b_wave64_breathing_camid_copyright46_powersave9_ntscpal_guard"
        ]["r78_telemetry"]["wave64_guard"]
        self.assertEqual(g["breathing_thirdparty_rc"], -95)
        self.assertEqual(g["breathing_macro_lock_rc"], -16)
        self.assertEqual(g["breathing_tc_lock_rc"], -16)
        self.assertEqual(g["breathing_still_lock_rc"], -16)
        self.assertEqual(g["breathing_100p_lock_rc"], -16)
        self.assertEqual(g["breathing_120p_lock_rc"], -16)
        self.assertEqual(g["breathing_sq120_lock_rc"], -16)
        self.assertEqual(g["fx6_sq24_lock_rc"], -16)
        self.assertEqual(g["fx6_dist_off_lock_rc"], -16)
        self.assertEqual(g["breathing_raw_lock_rc"], -16)
        self.assertEqual(g["breathing_ciz_lock_rc"], -16)
        self.assertEqual(g["catalyst_browse_rc"], -95)
        self.assertEqual(g["catalyst_dist_off_rc"], -16)

    def test_29_round78_r78b_guard_blocks_sdhc_camid_mixed_simult_38char_fx6_and_slot1(self) -> None:
        g = self.summary["runs"][
            "r78b_wave64_breathing_camid_copyright46_powersave9_ntscpal_guard"
        ]["r78_telemetry"]["wave64_guard"]
        self.assertEqual(g["sdhc_camid_lock_rc"], -16)
        self.assertEqual(g["sdhc_mixed_simult_rc"], -16)
        self.assertEqual(g["title_38char_einval_rc"], -22)
        self.assertEqual(g["fx6_46ch_prefix_rc"], -95)
        self.assertEqual(g["fx6_date_title_rc"], -95)
        self.assertEqual(g["slot1_series_reset_erofs_rc"], -30)

    def test_30_round78_r78b_guard_blocks_copyright_47char_fx6_camset_pii_and_slot1(self) -> None:
        g = self.summary["runs"][
            "r78b_wave64_breathing_camid_copyright46_powersave9_ntscpal_guard"
        ]["r78_telemetry"]["wave64_guard"]
        self.assertEqual(g["copy_47char_einval_rc"], -22)
        self.assertEqual(g["fx6_copyright_absent_rc"], -95)
        self.assertEqual(g["copyright_camset_excl_rc"], -95)
        self.assertEqual(g["raw_serial_pii_eperm_rc"], -1)
        self.assertEqual(g["camset_slot1_erofs_rc"], -30)

    def test_31_round78_r78b_guard_blocks_dormant_monitor_timers_handheld_pal_and_slot1(self) -> None:
        g = self.summary["runs"][
            "r78b_wave64_breathing_camid_copyright46_powersave9_ntscpal_guard"
        ]["r78_telemetry"]["wave64_guard"]
        self.assertEqual(g["ps_monitor_dormant_rc"], -95)
        self.assertEqual(g["ps_20sec_dormant_rc"], -95)
        self.assertEqual(g["ps_60min_dormant_rc"], -95)
        self.assertEqual(g["ps_240min_dormant_rc"], -95)
        self.assertEqual(g["fx6_powersave_absent_rc"], -95)
        self.assertEqual(g["handheld_temp_high_rc"], -16)
        self.assertEqual(g["pal_2398p_lock_rc"], -16)
        self.assertEqual(g["pal_df_lock_rc"], -16)
        self.assertEqual(g["slot1_ntsc_pal_erofs_rc"], -30)

    def test_32_round78_r78b_guard_blocks_slot1_p12_p2_cnflasha_einval_eperm_and_keeps_sha256(self) -> None:
        r78b_t = self.summary["runs"][
            "r78b_wave64_breathing_camid_copyright46_powersave9_ntscpal_guard"
        ]["r78_telemetry"]
        g = r78b_t["wave64_guard"]
        self.assertEqual(r78b_t["wave64_guard_rc"], 0)
        self.assertEqual(g["null_cfg_einval_rc"], -22)
        self.assertEqual(g["live_attach_eperm_rc"], -1)
        self.assertEqual(g["slot1_wave64_erofs_rc"], -30)
        self.assertEqual(g["p12_write_blocked_rc"], -30)
        self.assertEqual(g["p2_write_blocked_rc"], -30)
        self.assertEqual(g["cnflasha_ro_blocked_rc"], -30)
        self.assertEqual(g["slot1_vault_sha256_match"], 1)
        self.assertEqual(g["copyright_pii_leaked_bytes"], 0)
        self.assertEqual(g["slot1_data_sector_writes"], 0)
        self.assertEqual(g["rf_tx_packets"], 0)
        self.assertEqual(g["passive_tx_bytes_emitted"], 0)
        self.assertEqual(g["e_nd_actuator_tx_count"], 0)
        self.assertEqual(g["appfw_ok"], 1)
        self.assertEqual(g["shim_elf_ok"], 1)
        self.assertEqual(g["cnflasha_writes"], 0)
        self.assertEqual(g["emmc_write_count"], 0)
        self.assertEqual(g["r78b_ok"], 1)

    def test_33_round78_r78c_clean_unmount_wave64_reset_r57_erratum_and_16_h0_h3(self) -> None:
        ci = self.summary["runs"][
            "r78c_clean_unmount_wave64_reset_h0_h3_big6_schinese"
        ]["r78_telemetry"]["clean_unmount_wave64_h0_h3"]
        self.assertEqual(ci["stock_unmount_restored_ok"], 1)
        self.assertEqual(
            ci["camreset_resets_breathing_preserves_lens3_fileset37_copyright46_serial_powersave_ntscpal_airplane_ok"],
            1,
        )
        self.assertEqual(ci["nwreset_preserves_wave64_airplane_ok"], 1)
        self.assertEqual(
            ci["initialize_restores_wave64_defaults_clears_pii_preserves_airplane_ok"],
            1,
        )
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
        self.assertEqual(ci["copyright_pii_leaked_bytes"], 0)
        self.assertEqual(ci["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(ci["emmc_write_count"], 0)
        self.assertEqual(ci["r78c_ok"], 1)

    def test_34_round78_r78a_and_r78c_gpe0_readback_big6_home_ge_300k_nonzero_pixels(self) -> None:
        for rk in (
            "r78a_breathing_camid_copyright46_powersave9_ntscpal_big6_schinese",
            "r78c_clean_unmount_wave64_reset_h0_h3_big6_schinese",
        ):
            gpe = self.summary["runs"][rk]["gpe0_readback"]
            self.assertTrue(gpe["present"], rk)
            self.assertEqual(gpe["total_pixels"], 1024 * 540, rk)
            self.assertEqual(gpe["bytes"], 1024 * 540 * 4, rk)
            self.assertGreaterEqual(gpe["nonzero_pixels"], 300000, rk)
            self.assertGreaterEqual(gpe["unique_colors"], 50, rk)

    def test_35_round78_r78a_alpha_and_composited_png_dimensions_and_size_cap_27467(self) -> None:
        self.assertEqual(self.alpha_dims, (1024, 540))
        self.assertEqual(self.comp_dims, (1024, 540))
        self.assertLessEqual(len(self.alpha_png_bytes), 27467)
        self.assertLessEqual(len(self.comp_png_bytes), 27467)
        self.assertGreater(len(self.alpha_png_bytes), 10000)
        self.assertGreater(len(self.comp_png_bytes), 10000)
        self.assertGreater(self.alpha_transparent, 100000)
        self.assertGreater(self.alpha_opaque, 100000)
        self.assertEqual(self.comp_opaque, 1024 * 540)

    def test_36_round78_r78a_png_exports_paths_sanitized_and_match_assets(self) -> None:
        pe = self.summary["runs"][
            "r78a_breathing_camid_copyright46_powersave9_ntscpal_big6_schinese"
        ]["png_exports"]
        self.assertEqual(
            pe["alpha_png"]["path"],
            "reports/2026-11-18-round78-breathing-camid-copyright46-powersave9-ntscpal-qemu/r78_copyright46_serial_powersave9_ntscpal_erofs_preview.png",
        )
        self.assertEqual(
            pe["composited_png"]["path"],
            "reports/2026-11-18-round78-breathing-camid-copyright46-powersave9-ntscpal-qemu/r78_breathing_120p_camid_reel_37char_sdhc_preview.png",
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

    def test_37_round78_r78a_verify_us_positive_under_3_seconds(self) -> None:
        us = self.summary["runs"][
            "r78a_breathing_camid_copyright46_powersave9_ntscpal_big6_schinese"
        ]["r78_telemetry"]["wave64_init"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 3_000_000)

    def test_38_round78_r78b_verify_us_positive_under_3_seconds(self) -> None:
        us = self.summary["runs"][
            "r78b_wave64_breathing_camid_copyright46_powersave9_ntscpal_guard"
        ]["r78_telemetry"]["wave64_guard"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 3_000_000)

    def test_39_round78_r78c_verify_us_positive_under_3_seconds(self) -> None:
        us = self.summary["runs"][
            "r78c_clean_unmount_wave64_reset_h0_h3_big6_schinese"
        ]["r78_telemetry"]["clean_unmount_wave64_h0_h3"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 3_000_000)

    def test_40_round78_r78a_top_colors_transparent_plus_nonzero_equals_total_pixels(self) -> None:
        gpe = self.summary["runs"][
            "r78a_breathing_camid_copyright46_powersave9_ntscpal_big6_schinese"
        ]["gpe0_readback"]
        color_map = {row["argb"]: row["pixels"] for row in gpe["top_colors"]}
        self.assertIn("0x00000000", color_map)
        self.assertIn("0xff000000", color_map)
        self.assertEqual(color_map["0x00000000"] + gpe["nonzero_pixels"], gpe["total_pixels"])

    def test_41_round78_r78c_top_colors_transparent_plus_nonzero_equals_total_pixels(self) -> None:
        gpe = self.summary["runs"][
            "r78c_clean_unmount_wave64_reset_h0_h3_big6_schinese"
        ]["gpe0_readback"]
        color_map = {row["argb"]: row["pixels"] for row in gpe["top_colors"]}
        self.assertIn("0x00000000", color_map)
        self.assertEqual(color_map["0x00000000"] + gpe["nonzero_pixels"], gpe["total_pixels"])

    def test_42_round78_r78a_and_r78c_wall_elapsed_and_duration_budget_sanity(self) -> None:
        r78a = self.summary["runs"][
            "r78a_breathing_camid_copyright46_powersave9_ntscpal_big6_schinese"
        ]
        r78c = self.summary["runs"][
            "r78c_clean_unmount_wave64_reset_h0_h3_big6_schinese"
        ]
        ci_headroom = 15.0 if os.environ.get("GITHUB_ACTIONS") == "true" else 0.0
        max_wall = 240.0 + ci_headroom if os.environ.get("GITHUB_ACTIONS") == "true" else 120.0 + ci_headroom
        self.assertGreaterEqual(r78a["duration_budget_sec"], 70)
        self.assertLessEqual(r78a["duration_budget_sec"], 120)
        self.assertGreater(r78a["wall_elapsed_sec"], 50.0)
        self.assertLess(r78a["wall_elapsed_sec"], max_wall)
        self.assertGreaterEqual(r78c["duration_budget_sec"], 70)
        self.assertLessEqual(r78c["duration_budget_sec"], 120)
        self.assertGreater(r78c["wall_elapsed_sec"], 50.0)
        self.assertLess(r78c["wall_elapsed_sec"], max_wall)

    def test_43_round78_r78b_fast_early_exit_wall_elapsed_with_ci_headroom(self) -> None:
        r78b = self.summary["runs"][
            "r78b_wave64_breathing_camid_copyright46_powersave9_ntscpal_guard"
        ]
        ci_headroom = 15.0 if os.environ.get("GITHUB_ACTIONS") == "true" else 0.0
        max_b = 45.0 + ci_headroom if os.environ.get("GITHUB_ACTIONS") == "true" else 25.0 + ci_headroom
        self.assertEqual(r78b["duration_budget_sec"], 35)
        self.assertGreater(r78b["wall_elapsed_sec"], 1.0)
        self.assertLess(r78b["wall_elapsed_sec"], max_b)
        self.assertTrue(r78b["gpe0_readback"]["skipped_stock_fx3_mode"])

    def test_44_round78_faithful_invariants_preserved_across_all_3_runs(self) -> None:
        for rk, rv in self.summary["runs"].items():
            fi = rv["faithful_invariants"]
            self.assertEqual(fi["FX6_NATIVE_FAITHFUL"], 1, rk)
            self.assertEqual(fi["subst_color"], 0, rk)
            self.assertEqual(fi["subst_image"], 0, rk)
            self.assertEqual(fi["forced_render"], 0, rk)
            self.assertEqual(fi["skipped_node"], 0, rk)
            self.assertEqual(fi["lock_bypass"], 0, rk)

    def test_45_round78_all_3_runs_stage_b_manifest_count_13(self) -> None:
        for rk, rv in self.summary["runs"].items():
            self.assertEqual(rv["stage_b"]["manifest_count"], 13, rk)
            self.assertEqual(len(rv["stage_b"]["manifest_items"]), 13, rk)

    def test_46_round78_r78c_stage_b_r78_bridges_and_zero_leak_verified(self) -> None:
        r78c_t = self.summary["runs"][
            "r78c_clean_unmount_wave64_reset_h0_h3_big6_schinese"
        ]["r78_telemetry"]
        self.assertEqual(r78c_t["breathing_120p_catalyst_bridge"]["breathing_120p_catalyst_ok"], 1)
        self.assertEqual(r78c_t["camid_reel_37char_sdhc_bridge"]["camid_reel_37char_sdhc_ok"], 1)
        self.assertEqual(r78c_t["copyright46_serial_camset_bridge"]["copyright46_serial_camset_ok"], 1)
        self.assertEqual(r78c_t["powersave9_ntscpal_erofs_bridge"]["powersave9_ntscpal_ok"], 1)
        self.assertEqual(r78c_t["breathing_120p_catalyst_bridge"]["dormant_catalyst_browse_breathing_events"], 0)
        self.assertEqual(r78c_t["camid_reel_37char_sdhc_bridge"]["dormant_sdhc_camid_reel_bypass_events"], 0)
        self.assertEqual(r78c_t["copyright46_serial_camset_bridge"]["dormant_copyright_camset_export_events"], 0)
        self.assertEqual(r78c_t["powersave9_ntscpal_erofs_bridge"]["dormant_power_save_by_monitor_bypass_events"], 0)
        self.assertEqual(r78c_t["stage_b_bridge"]["e_nd_actuator_tx_count"], 0)

    def test_47_round78_all_3_runs_prefix_counts_include_fx6_r78(self) -> None:
        r78a_pc = self.summary["runs"][
            "r78a_breathing_camid_copyright46_powersave9_ntscpal_big6_schinese"
        ]["prefix_counts"]
        r78b_pc = self.summary["runs"][
            "r78b_wave64_breathing_camid_copyright46_powersave9_ntscpal_guard"
        ]["prefix_counts"]
        r78c_pc = self.summary["runs"][
            "r78c_clean_unmount_wave64_reset_h0_h3_big6_schinese"
        ]["prefix_counts"]
        self.assertGreater(r78a_pc["FX6_R78_"], 10)
        self.assertEqual(r78b_pc["FX6_R78_"], 3)
        self.assertGreater(r78c_pc["FX6_R78_"], 10)

    def test_48_round78_r78_meta_invariants_across_all_3_runs(self) -> None:
        for rk, rv in self.summary["runs"].items():
            m = rv["stage_b"]["r78"]
            self.assertEqual(m["milestone_round_ordinal"], 78, rk)
            self.assertEqual(m["realhw_round_ordinal"], 51, rk)
            self.assertEqual(m["total_live_runs_at_completion"], 153, rk)
            self.assertEqual(m["total_png_receipts_at_completion"], 102, rk)
            self.assertEqual(m["dormant_catalyst_browse_breathing_events"], 0, rk)
            self.assertEqual(m["dormant_breathing_120p_bypass_events"], 0, rk)
            self.assertEqual(m["dormant_sdhc_camid_reel_bypass_events"], 0, rk)
            self.assertEqual(m["dormant_copyright_camset_export_events"], 0, rk)
            self.assertEqual(m["dormant_power_save_by_monitor_bypass_events"], 0, rk)
            self.assertEqual(m["dormant_powersave_20s_60m_240m_bypass_events"], 0, rk)
            self.assertEqual(m["copyright_pii_leaked_bytes"], 0, rk)
            self.assertEqual(m["slot1_data_sector_writes"], 0, rk)
            self.assertEqual(m["rf_tx_packets"], 0, rk)
            self.assertEqual(m["passive_tx_bytes_emitted"], 0, rk)
            self.assertEqual(m["e_nd_actuator_tx_count"], 0, rk)
            self.assertEqual(m["raw_firmware_bytes_leaked"], 0, rk)
            self.assertEqual(m["cnflasha_writes"], 0, rk)
            self.assertEqual(m["emmc_write_count"], 0, rk)
            self.assertEqual(m["p2_setting_writes"], 0, rk)

    def test_49_round78_sanitize_helper_redacts_host_paths_and_reserved_port(self) -> None:
        dirty = {
            "run_id": "test-run",
            "lang": "schinese",
            "r78_mode": "breathing_camid_copyright46_powersave9_ntscpal_big6",
            "kernel_version": "Linux version 4.9.337-scel+",
            "kernel_bin": "/Users/fake/secret/kernel.bin",
            "dtb_bin": "/Users/fake/secret/guest.dtb",
            "build": {"tmp_build": "/private/tmp/build-123"},
            "stage_b": {"r78": {"r78_mode": "breathing_camid_copyright46_powersave9_ntscpal_big6"}},
            "r78_telemetry": {
                "wave64_init": {"r78_init_ok": 1},
                "wave64_guard": {"r78b_ok": 1},
                "clean_unmount_wave64_h0_h3": {"r78c_ok": 1, "surfaces_h0_eq_h3": 16},
            },
            "gpe0_readback": {"nonzero_pixels": 346686},
            "png_exports": {
                "alpha_png": {
                    "path": "/Users/kafu/repo/reports/2026-11-18-round78-breathing-camid-copyright46-powersave9-ntscpal-qemu/r78_copyright46_serial_powersave9_ntscpal_erofs_preview.png"
                }
            },
            "prefix_counts": {"FX6_R78_": 10},
        }
        sanitized = self.runner.sanitize_round78_summary(dirty, dirty, dirty)
        raw = json.dumps(sanitized)
        self.assertNotIn("/Users/", raw)
        self.assertNotIn("/private/tmp/", raw)
        self.assertNotIn("kernel_bin", raw)
        self.assertNotIn("dtb_bin", raw)
        self.assertIn(
            "reports/2026-11-18-round78-breathing-camid-copyright46-powersave9-ntscpal-qemu/r78_copyright46_serial_powersave9_ntscpal_erofs_preview.png",
            raw,
        )

    def test_50_round78_no_stray_temp_files_or_reserved_port_in_repo(self) -> None:
        for bad_name in ("tmp", "scratch", ".worktrees"):
            self.assertFalse((REPO_ROOT / bad_name).exists(), bad_name)
        reserved_port = "87" + "68"
        self.assertNotIn(reserved_port, self.summary_raw)
        self.assertNotIn(reserved_port, self.r78_readme)

    def test_51_round78_test_suite_contains_at_least_76_unit_tests(self) -> None:
        methods = [m for m in dir(self) if m.startswith("test_")]
        self.assertGreaterEqual(len(methods), 76)

    def test_52_round78_three_clean_env_modes_preserve_parity(self) -> None:
        for env_overrides in (
            {},
            {"FX3_CLEAN_ROOM_TEST": "1"},
            {"FX3_FX6_FORCE_CLEAN_ROOM": "1"},
        ):
            with mock.patch.dict(os.environ, env_overrides, clear=False):
                parsed = self.runner.extract_milestones(
                    "Linux version 4.9.337-scel+\n"
                    "FX6_R78_WAVE64_INIT breathing_120p_catalyst_ok=1 camid_reel_37char_sdhc_ok=1 "
                    "copyright46_serial_camset_ok=1 powersave9_ntscpal_ok=1 r78_init_ok=1\n"
                )
                self.assertEqual(parsed["r78_telemetry"]["wave64_init"]["r78_init_ok"], 1)

    def test_53_round78_mocked_donorless_work_root_none_fallback_and_master_gates(self) -> None:
        closure_pkg_dir = REPO_ROOT / "outputs" / "fx6-on-fx3-closure"
        safety_dir = REPO_ROOT / "outputs" / "fx3-safety"
        recovery_dir = REPO_ROOT / "outputs" / "fx3-recovery-adapter"
        firmware_lab_dir = REPO_ROOT / "outputs" / "fx3-firmware-lab"
        vm_dir = REPO_ROOT / "outputs" / "fx3-vm"
        added = [str(p) for p in (closure_pkg_dir, safety_dir, recovery_dir, firmware_lab_dir, vm_dir) if str(p) not in sys.path]
        for p in added:
            sys.path.insert(0, p)
        try:
            from fx6_closure.realhw_breathing_camid_copyright_powersave_zoom_ciz_rawcomp_and_usblun_verifier import (
                inspect_phase334_donors_bounded,
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
                "fx6_closure.realhw_breathing_camid_copyright_powersave_zoom_ciz_rawcomp_and_usblun_verifier._resolve_work_root_or_none",
                return_value=None,
            ):
                donor_ci = inspect_phase334_donors_bounded(
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
                self.assertGreaterEqual(rep324.qemu_rounds_verified, 51)
                self.assertGreaterEqual(rep324.qemu_runs_verified, 153)
                self.assertGreaterEqual(rep324.qemu_png_receipts_verified, 102)

                rep349 = evaluate_realhw_milestone349_master_gate(
                    repo_root=REPO_ROOT,
                    force_clean_room=True,
                    simulate_bench_dry_run=False,
                )
                self.assertEqual(rep349.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertTrue(rep349.all_pillars_milestone_ready)
                self.assertEqual(rep349.raw_firmware_bytes_leaked, 0)
                self.assertGreaterEqual(rep349.qemu_rounds_verified, 51)
                self.assertGreaterEqual(rep349.qemu_runs_verified, 153)
                self.assertGreaterEqual(rep349.qemu_png_receipts_verified, 102)

                rep364 = evaluate_realhw_milestone364_master_gate(
                    repo_root=REPO_ROOT,
                    force_clean_room=True,
                    simulate_bench_dry_run=False,
                )
                self.assertEqual(rep364.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertTrue(rep364.all_pillars_milestone_ready)
                self.assertEqual(rep364.raw_firmware_bytes_leaked, 0)
                self.assertGreaterEqual(rep364.qemu_rounds_verified, 51)
                self.assertGreaterEqual(rep364.qemu_runs_verified, 153)
                self.assertGreaterEqual(rep364.qemu_png_receipts_verified, 102)
        finally:
            for p in added:
                if p in sys.path:
                    sys.path.remove(p)

    def test_54_round78_argparse_percent_safe_help_and_no_hardcoded_python3(self) -> None:
        for line in self.runner_src.splitlines():
            if "help=" in line and "%" in line:
                stripped = line.replace("%%", "")
                self.assertNotIn("%", stripped, f"Unescaped '%' in argparse help: {line}")
        test_src = pathlib.Path(__file__).read_text(encoding="utf-8")
        forbidden_py = "/usr/" + "bin/python3"
        self.assertNotIn(forbidden_py, self.runner_src)
        self.assertNotIn(forbidden_py, test_src)

    def test_55_round78_all_102_pngs_under_27467b_and_clean_room_safe(self) -> None:
        round_dirs = [
            d for d in (REPO_ROOT / "reports").glob("2026-??-??-round*")
            if d.is_dir() and int(d.name.split("-round")[1].split("-")[0]) >= 28
        ]
        all_pngs = sorted(p for d in round_dirs for p in d.rglob("*.png") if p.is_file())
        self.assertGreaterEqual(len(all_pngs), 102)
        for p in all_pngs:
            self.assertLessEqual(p.stat().st_size, 27467, str(p))

    def test_56_round78_cli_help_subprocess_smoke(self) -> None:
        res = subprocess.run(
            [sys.executable, "-B", str(CLOSURE_DIR / "build_and_run_round.py"), "--help"],
            capture_output=True,
            text=True,
            check=True,
            timeout=45,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        self.assertIn("--r78-mode", res.stdout)
        self.assertIn("breathing_camid_copyright46_powersave9_ntscpal_big6", res.stdout)

    def test_57_round78_pillar1_breathing_100_120p_catalyst_prepare_metadata(self) -> None:
        r78a_meta = self.summary["runs"][
            "r78a_breathing_camid_copyright46_powersave9_ntscpal_big6_schinese"
        ]["stage_b"]["r78"]
        bc = r78a_meta["breathing_comp_100_120p_and_catalyst_prepare_wave64"]
        self.assertIn("Shooting -> [Image Quality/Rec] -> [Lens Compensation] -> [Breathing Comp.]", bc["menu_path"])
        self.assertIn("Can be reset", bc["menu_path"])
        self.assertIn("SEL100F28GM", bc["lens_whitelist_and_exceptions"])
        self.assertIn("SEL14TC/SEL20TC", bc["lens_whitelist_and_exceptions"])
        self.assertIn("100p/119.88p", bc["mode_and_fps_lockouts"])
        self.assertIn("S&Q < 100fps allowed", bc["mode_and_fps_lockouts"])
        self.assertIn("Catalyst Prepare", bc["catalyst_prepare_boundary"])
        self.assertIn("Catalyst Browse", bc["catalyst_prepare_boundary"])
        self.assertIn("Technical > Lens > Breathing Compensation", bc["fx6_diff"])

    def test_58_round78_pillar2_camid_reel_37char_title_and_sdhc_4gb_metadata(self) -> None:
        r78a_meta = self.summary["runs"][
            "r78a_breathing_camid_copyright46_powersave9_ntscpal_big6_schinese"
        ]["stage_b"]["r78"]
        cr = r78a_meta["camid_reel_37char_title_and_sdhc_4gb_split_wave64"]
        self.assertIn("Shooting -> [File] -> [File Settings]", cr["menu_path"])
        self.assertIn("A001C001_230101AB", cr["file_number_vs_camera_id_reel"])
        self.assertIn("C999 -> D001", cr["file_number_vs_camera_id_reel"])
        self.assertIn("<= 37 ASCII chars", cr["title_name_37char_and_sdhc_4gb"])
        self.assertIn("4 GB FAT32 split", cr["title_name_37char_and_sdhc_4gb"])
        self.assertIn("TC/Media > Clip Name Format", cr["slot1_erofs_vs_fx6"])

    def test_59_round78_pillar3_copyright46_serial_camset_and_r57_erratum_metadata(self) -> None:
        r78a_meta = self.summary["runs"][
            "r78a_breathing_camid_copyright46_powersave9_ntscpal_big6_schinese"
        ]["stage_b"]["r78"]
        cp = r78a_meta["copyright46_serial_camset_and_r57_erratum_wave64"]
        self.assertIn("Shooting -> [File] -> [Copyright Info]", cp["menu_path"])
        self.assertIn("BKID_APP_setting_write_serial_number_still_movie", cp["menu_path"])
        self.assertIn("RESIST [Camera Settings Reset]", cp["round57_reset_erratum_closed"])
        self.assertIn("Round 57", cp["round57_reset_erratum_closed"])
        self.assertIn("CAMSET*.DAT", cp["camset_and_pii_exclusion"])
        self.assertIn("EXIF [Copyright Info]", cp["fx6_diff"])

    def test_60_round78_pillar4_powersave9_dormant_monitor_and_ntscpal_erofs_metadata(self) -> None:
        r78a_meta = self.summary["runs"][
            "r78a_breathing_camid_copyright46_powersave9_ntscpal_big6_schinese"
        ]["stage_b"]["r78"]
        ps = r78a_meta["powersave9_dormant_monitor_and_ntscpal_erofs30_wave64"]
        self.assertIn("Setup -> [Power Setting Option]", ps["power_setting_option"])
        self.assertIn("9 auto-bypass conditions", ps["power_setting_option"])
        self.assertIn("BKID_APP_setting_monitor_power_linkage", ps["dormant_monitor_and_timers"])
        self.assertIn("20SEC/60min/240min", ps["dormant_monitor_and_timers"])
        self.assertIn("[NTSC/PAL Selector]", ps["ntsc_pal_slot1_erofs30"])
        self.assertIn("-30 EROFS", ps["ntsc_pal_slot1_erofs30"])

    def test_61_round78_3tier_reset_matrix_and_r57_copyright_erratum_closure(self) -> None:
        for fn in (
            "r78_wave64_camera_settings_reset",
            "r78_wave64_reset_network_settings",
            "r78_wave64_initialize",
            "r78_wave64_zero_init",
        ):
            self.assertIn(fn, self.stage_a_src)
        self.assertIn("Reset Network Set.", self.r78_readme)
        self.assertIn("Reset Network Set.", self.closure_readme)
        self.assertIn("Round 57", self.r78_readme)
        self.assertIn("Round 57", self.closure_readme)

    def test_62_round78_wave64_uxc_and_node_tokens_wired_in_stage_a_source(self) -> None:
        for sym in (
            "r78_lookup_wave64_menu_node",
            "r78_lookup_uxc_token",
            "_f:0x73ea:Breathing Comp.",
            "_f:0x659d:Corrects the focus breathing phenomenon.",
            "_f:0x616b:Does not correct the focus breathing phenomenon.",
            "_f:0x61bc:File Settings",
            "_f:0x7821:File Name Format",
            "_f:0x7a28:Series Counter Reset",
            "_f:0x6a52:Resets the sequence number counter for movies",
            "_f:0x67ae:Cam ID + Reel#",
            "_f:0x72f1:Camera ID",
            "_f:0x726a:Reel Number",
            "_f:0x68c4:Camera Position",
            "_f:0x6fc6:Shoots with the file name in Cam ID+Reel no.+YYMMDD",
            "_f:0x6c14:Title Name Settings",
            "_f:0x6e91:YYYYMMDD format",
            "base:0xe1d8:Use an SDXC or CFexpress memory card",
            "_f:0x6d53:Copyright Info",
            "_f:0x7ae4:Write Copyright Info",
            "_f:0x7172:Set Photographer",
            "_f:0x612b:Set Copyright",
            "_f:0x611b:Disp. Copyright Info",
            "_f:0x7058:Write Serial Number",
            "_f:0x7953:Writes the device's serial number when shooting.",
            "_f:0x69b0:Power Save Start Time",
            "_f:0x70f1:Auto Power OFF Temp.",
            "_g:0x61a9:When shooting from a tripod",
            "_f:0x6b6f:NTSC/PAL Selector",
            "base:0xe77a:Running on NTSC.",
            "base:0xe0b6:Running on PAL.",
            "_g:0x61ca:Movies recorded while NTSC/PAL is operating cannot be played back",
            "_f:0x783f:Power Save by Monitor (dormant on FX3)",
            "_f:0x6db5:Both Linked (dormant)",
            "_f:0x60a8:Close: Power Save (dormant)",
            "dormant:POWERSAVE_20SEC_60MIN_240MIN",
            "dormant:CATALYST_BROWSE_BREATHING",
        ):
            self.assertIn(sym, self.stage_a_src)

    def test_63_round78_report_markdown_has_chinese_conclusions_and_fact_inference_split(self) -> None:
        self.assertIn("## 结论先行", self.r78_readme)
        self.assertIn("实测事实", self.r78_readme)
        self.assertIn("推断", self.r78_readme)
        self.assertIn("51/51", self.r78_readme)
        self.assertIn("153/153", self.r78_readme)
        self.assertIn("102/102", self.r78_readme)
        self.assertIn("unexecuted_physical_camera_bench_boundaries", self.summary)
        self.assertEqual(len(self.summary["unexecuted_physical_camera_bench_boundaries"]), 3)

    def test_64_round78_closure_readme_documents_round78_section(self) -> None:
        self.assertIn("## 78. Round 78", self.closure_readme)
        self.assertIn("153/153", self.closure_readme)
        self.assertIn("102/102", self.closure_readme)
        self.assertIn("Breathing Comp.", self.closure_readme)

    def test_65_round78_round77_baseline_non_regression_preserved(self) -> None:
        self.assertEqual(self.r77_summary["round"], 77)
        self.assertEqual(self.r77_summary["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(
            self.r77_summary["r77_hdmi_raw_desqueeze_reclamp_varshutter_apsc_audit"]["realhw_rounds_count"],
            50,
        )

    def test_66_round78_round76_baseline_non_regression_preserved(self) -> None:
        self.assertEqual(self.r76_summary["round"], 76)
        self.assertEqual(self.r76_summary["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(
            self.r76_summary["r76_shoe_audio_4ch_subject_recog_silent_target_bodydata_audit"]["realhw_rounds_count"],
            49,
        )

    def test_67_round78_round75_baseline_non_regression_preserved(self) -> None:
        self.assertEqual(self.r75_summary["round"], 75)
        self.assertEqual(self.r75_summary["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(
            self.r75_summary["r75_ftp_ftpes_customwb_afspeed_focusmap_marker_peaking_audit"]["realhw_rounds_count"],
            48,
        )

    def test_68_round78_round74_baseline_non_regression_preserved(self) -> None:
        self.assertEqual(self.r74_summary["round"], 74)
        self.assertEqual(self.r74_summary["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(
            self.r74_summary["r74_rec_media_autoswitch_proxy_cloud_mymenu42_audit"]["realhw_rounds_count"],
            47,
        )

    def test_69_round78_wave64_enums_and_structs_in_stage_a(self) -> None:
        for tok in (
            "R78_MODE_STILL",
            "R78_MODE_MOVIE",
            "R78_MODE_SQ",
            "R78_LENS_SEL24F14GM",
            "R78_LENS_SEL100F28GM_MACRO_057_100M",
            "R78_LENS_SEL14TC_OR_SEL20TC",
            "R78_LENS_THIRD_PARTY_UNSUPPORTED",
            "R78_FILENUM_SERIES",
            "R78_FILENUM_RESET",
            "R78_FILENAME_STANDARD",
            "R78_FILENAME_CAMID_REEL",
            "R78_CARD_SDHC_FAT32",
            "R78_PS_5MIN",
            "R78_PS_DORMANT_20SEC",
            "R78_PS_DORMANT_60MIN",
            "R78_PS_DORMANT_240MIN",
            "R78_TEMP_STANDARD",
            "R78_TEMP_HIGH",
            "R78_SYS_NTSC",
            "R78_SYS_PAL",
        ):
            self.assertIn(tok, self.stage_a_src)

    def test_70_round78_overlay_meta_modes_and_milestone_counts_consistent(self) -> None:
        _, _, ma = self.ov_a
        _, _, mb = self.ov_b
        _, _, mc = self.ov_c
        self.assertEqual(ma["r78"]["r78_mode"], "breathing_camid_copyright46_powersave9_ntscpal_big6")
        self.assertEqual(mb["r78"]["r78_mode"], "wave64_breathing_camid_copyright46_powersave9_ntscpal_guard")
        self.assertEqual(mc["r78"]["r78_mode"], "clean_unmount_wave64_reset_h0_h3_big6")
        for m in (ma, mb, mc):
            self.assertTrue(m["r78_enabled"])
            self.assertEqual(m["r78"]["milestone_round_ordinal"], 78)
            self.assertEqual(m["r78"]["realhw_round_ordinal"], 51)
            self.assertEqual(m["r78"]["total_live_runs_at_completion"], 153)
            self.assertEqual(m["r78"]["total_png_receipts_at_completion"], 102)

    def test_71_round78_sanitize_preserves_negative_audit_booleans(self) -> None:
        audit = self.summary["r78_breathing_camid_copyright46_powersave9_ntscpal_audit"]
        self.assertIs(audit["fx3_catalyst_browse_breathing_supported"], False)
        self.assertIs(audit["fx3_sdhc_camid_reel_supported"], False)
        self.assertIs(audit["fx3_power_save_by_monitor_exposed"], False)
        self.assertIs(audit["fx3_powersave_20s_60m_240m_exposed"], False)
        self.assertIs(audit["fx6_exif_copyright_info_supported"], False)
        self.assertIs(audit["fx6_power_setting_option_menu_present"], False)

    def test_72_round78_r78a_breathing_and_catalyst_prepare_enforced(self) -> None:
        init_t = self.summary["runs"][
            "r78a_breathing_camid_copyright46_powersave9_ntscpal_big6_schinese"
        ]["r78_telemetry"]["wave64_init"]
        self.assertEqual(init_t["breathing_120p_catalyst_ok"], 1)
        self.assertEqual(init_t["breathing_120p_lock_rc"], -16)
        self.assertEqual(init_t["breathing_macro_lock_rc"], -16)
        self.assertEqual(init_t["catalyst_browse_rc"], -95)

    def test_73_round78_r78b_camid_reel_sdhc_and_title_38char_enforced(self) -> None:
        g = self.summary["runs"][
            "r78b_wave64_breathing_camid_copyright46_powersave9_ntscpal_guard"
        ]["r78_telemetry"]["wave64_guard"]
        self.assertEqual(g["sdhc_camid_lock_rc"], -16)
        self.assertEqual(g["sdhc_mixed_simult_rc"], -16)
        self.assertEqual(g["title_38char_einval_rc"], -22)
        self.assertEqual(g["fx6_46ch_prefix_rc"], -95)
        self.assertEqual(g["fx6_date_title_rc"], -95)
        self.assertEqual(g["slot1_series_reset_erofs_rc"], -30)

    def test_74_round78_r78b_copyright46_camset_and_powersave_ntscpal_enforced(self) -> None:
        g = self.summary["runs"][
            "r78b_wave64_breathing_camid_copyright46_powersave9_ntscpal_guard"
        ]["r78_telemetry"]["wave64_guard"]
        self.assertEqual(g["copy_47char_einval_rc"], -22)
        self.assertEqual(g["fx6_copyright_absent_rc"], -95)
        self.assertEqual(g["copyright_camset_excl_rc"], -95)
        self.assertEqual(g["raw_serial_pii_eperm_rc"], -1)
        self.assertEqual(g["ps_monitor_dormant_rc"], -95)
        self.assertEqual(g["ps_20sec_dormant_rc"], -95)
        self.assertEqual(g["ps_60min_dormant_rc"], -95)
        self.assertEqual(g["ps_240min_dormant_rc"], -95)
        self.assertEqual(g["pal_2398p_lock_rc"], -16)
        self.assertEqual(g["pal_df_lock_rc"], -16)
        self.assertEqual(g["slot1_ntsc_pal_erofs_rc"], -30)

    def test_75_round78_r78c_round57_erratum_write_copyright_survives_camreset_clears_on_init(self) -> None:
        ci = self.summary["runs"][
            "r78c_clean_unmount_wave64_reset_h0_h3_big6_schinese"
        ]["r78_telemetry"]["clean_unmount_wave64_h0_h3"]
        self.assertEqual(
            ci["camreset_resets_breathing_preserves_lens3_fileset37_copyright46_serial_powersave_ntscpal_airplane_ok"],
            1,
        )
        self.assertEqual(ci["nwreset_preserves_wave64_airplane_ok"], 1)
        self.assertEqual(
            ci["initialize_restores_wave64_defaults_clears_pii_preserves_airplane_ok"],
            1,
        )

    def test_76_round78_clean_unmount_checks_stock_restoration_and_zero_emmc(self) -> None:
        ci = self.summary["runs"][
            "r78c_clean_unmount_wave64_reset_h0_h3_big6_schinese"
        ]["r78_telemetry"]["clean_unmount_wave64_h0_h3"]
        self.assertEqual(ci["stock_unmount_restored_ok"], 1)
        self.assertEqual(ci["dlopen_ok"], 1)
        self.assertEqual(ci["surfaces_h0_eq_h3"], 16)
        self.assertEqual(ci["drift_bits"], 0)
        self.assertEqual(ci["emmc_write_count"], 0)
        self.assertEqual(ci["cnflasha_write_bytes"], 0)

    def test_77_round78_r78b_fx6_vs_fx3_sq_and_distortion_lockout_parity(self) -> None:
        g = self.summary["runs"][
            "r78b_wave64_breathing_camid_copyright46_powersave9_ntscpal_guard"
        ]["r78_telemetry"]["wave64_guard"]
        self.assertEqual(g["breathing_sq120_lock_rc"], -16)
        self.assertEqual(g["fx6_sq24_lock_rc"], -16)
        self.assertEqual(g["fx6_dist_off_lock_rc"], -16)
        self.assertEqual(g["catalyst_dist_off_rc"], -16)

    def test_78_round78_zero_pii_and_zero_dormant_bypasses_in_all_3_runs(self) -> None:
        r78a_init = self.summary["runs"][
            "r78a_breathing_camid_copyright46_powersave9_ntscpal_big6_schinese"
        ]["r78_telemetry"]["wave64_init"]
        r78b_g = self.summary["runs"][
            "r78b_wave64_breathing_camid_copyright46_powersave9_ntscpal_guard"
        ]["r78_telemetry"]["wave64_guard"]
        r78c_ci = self.summary["runs"][
            "r78c_clean_unmount_wave64_reset_h0_h3_big6_schinese"
        ]["r78_telemetry"]["clean_unmount_wave64_h0_h3"]
        for rec in (r78a_init, r78b_g, r78c_ci):
            self.assertEqual(rec["copyright_pii_leaked_bytes"], 0)
            self.assertEqual(rec["dormant_catalyst_browse_breathing_events"], 0)
            self.assertEqual(rec["dormant_breathing_120p_bypass_events"], 0)
            self.assertEqual(rec["dormant_sdhc_camid_reel_bypass_events"], 0)
            self.assertEqual(rec["dormant_copyright_camset_export_events"], 0)
            self.assertEqual(rec["dormant_power_save_by_monitor_bypass_events"], 0)
            self.assertEqual(rec["dormant_powersave_20s_60m_240m_bypass_events"], 0)
            self.assertEqual(rec["slot1_data_sector_writes"], 0)


if __name__ == "__main__":
    unittest.main()
