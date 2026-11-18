#!/usr/bin/env python3
"""Offline four-mode unit tests for FX6-on-FX3 Round 75 (48/48 Real-HW Rounds R28..R75, 142nd..144th Live Runs -> 144/144 Total, 96/96 PNGs <= 27,467 B — Wave-61)."""
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
ROUND75_REPORT_DIR = (
    REPO_ROOT
    / "reports"
    / "2026-11-18-round75-milestone-ftp-ftpes-customwb-afspeed-focusmap-marker-peaking-qemu"
)
WAVE61_SPEC_PATH = (
    REPO_ROOT
    / "reports"
    / "2026-11-17-global-sony-wave61-ftp-ftps-customwb-af-speed-focusmap-marker-intel"
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


def _build_overlay_for_r75(
    runner,
    parent_cpio: pathlib.Path,
    fp,
    fv,
    fb,
    fake_run,
    jit_meta: Dict[str, Any],
    work: pathlib.Path,
    r75_mode: str,
    lang: str = "schinese",
    enable_r75: bool = True,
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
            enable_r75=enable_r75,
            r75_mode=r75_mode,
            sd_manifest_mode="valid",
            lang=lang,
            shim_bytes=b"SHIM",
        )


class TestRound75FtpFtpesCustomWbAfSpeedFocusMapMarkerPeakingQemu(unittest.TestCase):
    EXPECTED_RUN_KEYS = (
        "r75a_ftp_ftpes_customwb_afspeed_focusmap_marker_big6_schinese",
        "r75b_wave61_ftp_usblan_customwb_focusmap_marker_erofs_guard",
        "r75c_clean_unmount_wave61_reset_h0_h3_big6_schinese",
    )

    runner: Any
    runner_src: str
    stage_a_src: str
    shim_src: str
    wave61_spec: str
    summary_raw: str
    summary: Dict[str, Any]
    r75_readme: str
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
    launcher_r75: Optional[bytes]
    shim_r75: Optional[bytes]
    shim_r74: Optional[bytes]
    r74_summary: Dict[str, Any]
    r73_summary: Dict[str, Any]
    r72_summary: Dict[str, Any]
    r71_summary: Dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = _load_closure_module("fx6_brr_r75_cached", "build_and_run_round.py")
        cls.runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")
        cls.stage_a_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        cls.shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        cls.wave61_spec = WAVE61_SPEC_PATH.read_text(encoding="utf-8")
        cls.summary_raw = (ROUND75_REPORT_DIR / "summary.json").read_text(encoding="utf-8")
        cls.summary = json.loads(cls.summary_raw)
        cls.r75_readme = (ROUND75_REPORT_DIR / "README.md").read_text(encoding="utf-8")
        cls.closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")

        alpha_p = (
            ROUND75_REPORT_DIR
            / "assets"
            / "r75a-ftp-ftpes-customwb-afspeed-focusmap-marker-big6-schinese-alpha.png"
        )
        comp_p = (
            ROUND75_REPORT_DIR
            / "assets"
            / "r75a-ftp-ftpes-customwb-afspeed-focusmap-marker-big6-schinese-composited.png"
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
            cls.ov_a = _build_overlay_for_r75(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wa", "ftp_ftpes_customwb_afspeed_focusmap_marker_big6", lang="schinese",
            )
            cls.ov_b = _build_overlay_for_r75(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wb", "wave61_ftp_usblan_customwb_focusmap_marker_erofs_guard", lang="en",
            )
            cls.ov_c = _build_overlay_for_r75(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wc", "clean_unmount_wave61_reset_h0_h3_big6", lang="schinese",
            )
            cls.ov_off = _build_overlay_for_r75(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "woff", "ftp_ftpes_customwb_afspeed_focusmap_marker_big6", enable_r75=False,
            )
            cls.invalid_mode_raised = False
            try:
                _build_overlay_for_r75(
                    cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                    tpath / "wbad", "invalid_r75_mode",
                )
            except ValueError:
                cls.invalid_mode_raised = True

            zig_bin = shutil.which("zig") or (
                str(cls.runner.ZIG) if cls.runner.ZIG.is_file() else None
            )
            if zig_bin is not None:
                verify_r75_out = tpath / "fx6-stage-a-verify-r75"
                shim_r75_out = tpath / "libgrm-fbinit9-r75.so"
                shim_r74_out = tpath / "libgrm-fbinit9-r74.so"
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
                        str(verify_r75_out),
                    ],
                    [
                        zig_bin,
                        "cc",
                        "-target",
                        "aarch64-linux-gnu.2.25",
                        "-O0",
                        "-shared",
                        "-fPIC",
                        "-DFX6_ROUND=75",
                        str(CLOSURE_DIR / "libgrm-fbinit9.c"),
                        "-ldl",
                        "-lpthread",
                        "-o",
                        str(shim_r75_out),
                    ],
                    [
                        zig_bin,
                        "cc",
                        "-target",
                        "aarch64-linux-gnu.2.25",
                        "-O0",
                        "-shared",
                        "-fPIC",
                        "-DFX6_ROUND=74",
                        str(CLOSURE_DIR / "libgrm-fbinit9.c"),
                        "-ldl",
                        "-lpthread",
                        "-o",
                        str(shim_r74_out),
                    ],
                ):
                    cls.runner.subprocess.run(cmd, check=True)
                cls.launcher_r75 = verify_r75_out.read_bytes()
                cls.shim_r75 = shim_r75_out.read_bytes()
                cls.shim_r74 = shim_r74_out.read_bytes()
            else:
                cls.launcher_r75 = None
                cls.shim_r75 = None
                cls.shim_r74 = None

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
        cls.r72_summary = json.loads(
            (
                REPO_ROOT
                / "reports"
                / "2026-11-18-round72-milestone-bright-mon-shotmark-usblan-bulb-dormant-qemu"
                / "summary.json"
            ).read_text(encoding="utf-8")
        )
        cls.r71_summary = json.loads(
            (
                REPO_ROOT
                / "reports"
                / "2026-11-17-round71-steadyshot-47focal-selftimer-zebra-streaming-erofs-qemu"
                / "summary.json"
            ).read_text(encoding="utf-8")
        )

    def test_01_wave61_global_spec_present_and_covers_all_4_pillars(self) -> None:
        self.assertTrue(WAVE61_SPEC_PATH.is_file())
        for needle in (
            "FTP Transfer Func.",
            "BKID_APP_ftp_server_settings_*0..8",
            "SET_SERVER_SECURE_PROTOCOL_{OFF,ON}",
            "FTPES",
            "cacert.pem",
            "certification.pem",
            "Transfer JPEG Size",
            "CONTENT_INFO_FTP_TRANS_STAT",
            "USB-LAN",
            "White Balance",
            "2500K",
            "9900K",
            "Priority Set in AWB",
            "Shutter AWB Lock",
            "Shockless WB",
            "Cine EI",
            "AF Transition Speed",
            "AF Subj. Shift Sensitivity",
            "MOVIE_AF_SUBJ_SHIFT_SENS_5_RESPONSICE",
            "AF Assist",
            "Focus Map",
            "Monitor & Control",
            ">= 150 fps",
            "Marker Display",
            "Aspect Marker",
            "Peaking Display",
            "User Box",
        ):
            self.assertIn(needle, self.wave61_spec)

    def test_02_round75_summary_schema_milestone_and_zero_leaks(self) -> None:
        self.assertNotIn("/Users/", self.summary_raw)
        self.assertNotIn("/private/tmp/", self.summary_raw)
        self.assertEqual(
            self.summary["schema"],
            "fx6-on-fx3-round75-ftp-ftpes-customwb-afspeed-focusmap-marker-peaking-qemu-v1",
        )
        self.assertEqual(self.summary["round"], 75)
        self.assertIn("48/48 Real-HW Rounds", self.summary["milestone"])
        self.assertIn("144/144 Live Runs", self.summary["milestone"])
        self.assertIn("96/96 PNGs <= 27,467 B", self.summary["milestone"])
        self.assertEqual(self.summary["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(tuple(self.summary["runs"].keys()), self.EXPECTED_RUN_KEYS)

    def test_03_round75_cli_accepts_round75_and_all_3_r75_modes(self) -> None:
        self.assertIn(", 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75]", self.runner_src)
        for mode in (
            "ftp_ftpes_customwb_afspeed_focusmap_marker_big6",
            "wave61_ftp_usblan_customwb_focusmap_marker_erofs_guard",
            "clean_unmount_wave61_reset_h0_h3_big6",
        ):
            self.assertIn(mode, self.runner_src)

    def test_04_round75_overlay_rejects_invalid_r75_mode(self) -> None:
        self.assertTrue(self.invalid_mode_raised)

    def test_05_round75_overlay_r75a_injects_etc_fx6_stage_r75_and_appfw_launch(self) -> None:
        replacements, additions, meta = self.ov_a
        self.assertTrue(meta["r75_enabled"])
        self.assertIn("etc/fx6_stage_r75", additions)
        self.assertIn("etc/fx6_r75_libjit.so", additions)
        r75_cfg = additions["etc/fx6_stage_r75"][0].decode("utf-8")
        self.assertIn("stage_r75=1", r75_cfg)
        self.assertIn("r75_mode=ftp_ftpes_customwb_afspeed_focusmap_marker_big6", r75_cfg)
        self.assertIn("milestone_48th_realhw_144th_live_96_pngs=1", r75_cfg)
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("/usr/bin/appfw-launch", init_txt)
        self.assertNotIn("--r75-wave61-guard", init_txt)

    def test_06_round75_overlay_r75b_injects_early_guard_probe_and_poweroff(self) -> None:
        replacements, _, meta = self.ov_b
        self.assertEqual(
            meta["r75"]["r75_mode"],
            "wave61_ftp_usblan_customwb_focusmap_marker_erofs_guard",
        )
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("--r75-wave61-guard", init_txt)
        self.assertIn("FX6_R75_WAVE61_GUARD_RC=", init_txt)
        self.assertIn("FX6_R75_WAVE61_GUARD_EXIT", init_txt)
        self.assertIn("poweroff -f", init_txt)

    def test_07_round75_overlay_r75c_integrated_runs_stage_b_big6(self) -> None:
        replacements, additions, meta = self.ov_c
        self.assertEqual(meta["r75"]["r75_mode"], "clean_unmount_wave61_reset_h0_h3_big6")
        r75_cfg = additions["etc/fx6_stage_r75"][0].decode("utf-8")
        self.assertIn("r75_mode=clean_unmount_wave61_reset_h0_h3_big6", r75_cfg)
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("/usr/bin/appfw-launch", init_txt)
        self.assertNotIn("--r75-wave61-guard", init_txt)

    def test_08_round75_overlay_disabled_when_enable_r75_false(self) -> None:
        _, additions, meta = self.ov_off
        self.assertFalse(meta["r75_enabled"])
        self.assertNotIn("etc/fx6_stage_r75", additions)
        self.assertNotIn("etc/fx6_r75_libjit.so", additions)
        self.assertNotIn("r75", meta)

    def test_09_round75_stage_a_c_source_contains_all_3_wave61_probes(self) -> None:
        for sym in (
            "setup_r75_ftp_ftpes_customwb_afspeed_focusmap_marker_probe",
            "run_r75_wave61_guard_probe",
            "run_r75_clean_unmount_wave61_h0_h3_probe",
            "r75_wave61_initialize",
            "r75_wave61_zero_init",
            "r75_wave61_camera_settings_reset",
            "r75_wave61_reset_network_settings",
            "r75_configure_ftp_and_zerorf",
            "r75_configure_white_balance",
            "r75_configure_movie_af_and_focusmap",
            "r75_configure_marker_and_peaking",
            "FX6_R75_WAVE61_INIT",
            "FX6_R75_WAVE61_GUARD",
            "FX6_R75_CLEAN_UNMOUNT_WAVE61_H0_H3",
            "--r75-wave61-guard",
            "--r75-clean-unmount-wave61-h0-h3",
            "/etc/fx6_stage_r75",
        ):
            self.assertIn(sym, self.stage_a_src)

    def test_10_round75_shim_c_source_contains_r75_guarded_bridges(self) -> None:
        self.assertIn("#if FX6_ROUND >= 75", self.shim_src)
        for sym in (
            "FX6_R75_FTP_FTPES_ZERORF_EROFS_BRIDGE",
            "FX6_R75_CUSTOMWB_AWBLOCK_SHOCKLESS_CINEEI_BRIDGE",
            "FX6_R75_AF_SPEED_SENS_FOCUSMAP_APP_BRIDGE",
            "FX6_R75_MARKER15_PEAKING4_CLEAN_HDMI_BRIDGE",
            "FX6_R75_LANG_TELEMETRY",
            "FX6_STAGE_B_R75_BRIDGE",
        ):
            self.assertIn(sym, self.shim_src)

    def test_11_round75_compile_launcher_and_shim_aarch64_elf_symbols(self) -> None:
        if self.launcher_r75 is None or self.shim_r75 is None:
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertEqual(self.launcher_r75[:4], b"\x7fELF")
        self.assertEqual(self.shim_r75[:4], b"\x7fELF")
        self.assertEqual(struct.unpack_from("<H", self.shim_r75, 18)[0], 183)
        self.assertIn(b"FX6_R75_FTP_FTPES_ZERORF_EROFS_BRIDGE", self.shim_r75)
        self.assertIn(b"FX6_R75_CUSTOMWB_AWBLOCK_SHOCKLESS_CINEEI_BRIDGE", self.shim_r75)
        self.assertIn(b"FX6_R75_AF_SPEED_SENS_FOCUSMAP_APP_BRIDGE", self.shim_r75)
        self.assertIn(b"FX6_R75_MARKER15_PEAKING4_CLEAN_HDMI_BRIDGE", self.shim_r75)

    def test_12_round75_shim_round74_backward_compat_excludes_r75_bridges(self) -> None:
        if self.shim_r74 is None:
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertIn(b"FX6_R74_MYMENU42_FX6_LOCK_BRIDGE", self.shim_r74)
        self.assertNotIn(b"FX6_R75_FTP_FTPES_ZERORF_EROFS_BRIDGE", self.shim_r74)

    def test_13_round75_parse_log_extracts_all_10_r75_prefixes_and_rc(self) -> None:
        serial_text = (
            "\n".join(
                [
                    "Linux version 4.9.337-scel+ (sony@fx3)",
                    "FX6_R75_WAVE61_INIT fx3_wave61_nodes_ok=1 uxc_tokens_ok=1 ftp_ftpes_zerorf_erofs_ok=1 customwb_awblock_shockless_cineei_ok=1 af_speed_sens_focusmap_app_ok=1 marker15_peaking4_clean_hdmi_ok=1 emmc_write_count=0 r75_init_ok=1",
                    "FX6_R75_FTP_FTPES_ZERORF_EROFS_BRIDGE ftp_9servers_ftpes_passive_only_ok=1 slot1_avf_erofs_and_usblan_zerorf_ok=1 ftp_ftpes_zerorf_erofs_ok=1 rf_tx_packets=0 usb_lan_tx_packets=0 emmc_write_count=0 r75_bridge_ok=1",
                    "FX6_R75_CUSTOMWB_AWBLOCK_SHOCKLESS_CINEEI_BRIDGE customwb_2500_9900k_camset_excl_ok=1 awblock_reset_immune_shockless_cineei_ok=1 customwb_awblock_shockless_cineei_ok=1 cnflasha_writes=0 emmc_write_count=0",
                    "FX6_R75_AF_SPEED_SENS_FOCUSMAP_APP_BRIDGE af_speed_1_7_sens_1_5_shared_ok=1 focusmap_mc_app_only_150fps_cutoff_ok=1 af_speed_sens_focusmap_app_ok=1 dormant_inbody_focus_map_bypass_events=0 cnflasha_writes=0 emmc_write_count=0",
                    "FX6_R75_MARKER15_PEAKING4_CLEAN_HDMI_BRIDGE marker_15_ratio_8_reset_immune_ok=1 peaking_4color_clean_hdmi_0px_ok=1 marker15_peaking4_clean_hdmi_ok=1 hdmi_marker_baked_pixels=0 hdmi_peaking_baked_pixels=0 emmc_write_count=0",
                    "FX6_R75_LANG_TELEMETRY lang=schinese font_bank=23 str_bank=19 milestone_48th_realhw_144th_live_96_pngs=1 r75_bridge_ok=1",
                    "FX6_STAGE_B_R75_BRIDGE round=75 faithful=1 nop_count=0 milestone_48th_realhw_144th_live_96_pngs=1 emmc_write_count=0",
                    "FX6_R75_WAVE61_GUARD ftp_sftp_dormant_rc=-95 ftp_slot1_avf_erofs_rc=-30 ftp_zerorf_tx_rc=-100 wb_custom_camset_excl_rc=-95 af_shift_7_fx6_rc=-95 fx6_userbox_fx3_rc=-95 r75b_ok=1",
                    "FX6_R75_WAVE61_GUARD_RC=0",
                    "FX6_R75_CLEAN_UNMOUNT_WAVE61_H0_H3 stock_unmount_restored_ok=1 camreset_resets_wb_af_focusmap_preserves_shutterlock_8markerpeak_ftp_ok=1 nwreset_clears_ftp9_cacert_preserves_marker8_shutterlock_airplane_ok=1 initialize_clears_shutterlock_customwb_8markerpeak_preserves_airplane_ok=1 surfaces_h0_eq_h3=16 r75c_ok=1",
                ]
            )
            + "\n"
        )
        parsed = self.runner.extract_milestones(serial_text)
        r75_t = parsed["r75_telemetry"]
        self.assertEqual(r75_t["wave61_guard_rc"], 0)
        self.assertEqual(r75_t["wave61_init"]["ftp_ftpes_zerorf_erofs_ok"], 1)
        self.assertEqual(r75_t["ftp_ftpes_zerorf_erofs_bridge"]["ftp_ftpes_zerorf_erofs_ok"], 1)
        self.assertEqual(r75_t["customwb_awblock_shockless_cineei_bridge"]["customwb_awblock_shockless_cineei_ok"], 1)
        self.assertEqual(r75_t["af_speed_sens_focusmap_app_bridge"]["af_speed_sens_focusmap_app_ok"], 1)
        self.assertEqual(r75_t["marker15_peaking4_clean_hdmi_bridge"]["marker15_peaking4_clean_hdmi_ok"], 1)
        self.assertEqual(r75_t["lang_telemetry"]["lang"], "schinese")
        self.assertEqual(r75_t["lang_telemetry"]["milestone_48th_realhw_144th_live_96_pngs"], 1)
        self.assertEqual(r75_t["stage_b_bridge"]["round"], 75)
        self.assertEqual(r75_t["wave61_guard"]["r75b_ok"], 1)
        self.assertEqual(r75_t["clean_unmount_wave61_h0_h3"]["surfaces_h0_eq_h3"], 16)
        self.assertEqual(parsed["prefix_counts"]["FX6_R75_"], 9)

    def test_14_round75_parse_log_defaults_when_no_r75_lines_present(self) -> None:
        parsed = self.runner.extract_milestones("Linux version 4.9.337-scel+\n")
        self.assertIsNone(parsed["r75_telemetry"])
        self.assertEqual(parsed["prefix_counts"].get("FX6_R75_", 0), 0)

    def test_15_round75_runner_preserves_r74_prefix_and_uses_r75_stage_label(self) -> None:
        self.assertIn('if args.round >= 74:\n        tmp_prefix = "fx6-r74"', self.runner_src)
        self.assertIn('if args.round >= 75:\n        tmp_prefix = "fx6-r75"', self.runner_src)
        self.assertIn(
            "Milestone48RealHw144thLiveWave61FtpFtpesCustomWbAfSpeedFocusMapMarkerPeaking",
            self.runner_src,
        )
        self.assertIn(", 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75]", self.runner_src)

    def test_16_round75_runner_portability_and_sanitizer_helper(self) -> None:
        self.assertIn('shutil.which("zig")', self.runner_src)
        self.assertIn("FX6_SCRATCH_DIR", self.runner_src)
        self.assertIn("def sanitize_round75_summary(", self.runner_src)
        self.assertNotIn("/usr/" + "bin/python3", self.runner_src)

    def test_17_round75_summary_json_top_level_schema_and_milestone_metadata(self) -> None:
        d = self.summary
        self.assertEqual(
            d["schema"],
            "fx6-on-fx3-round75-ftp-ftpes-customwb-afspeed-focusmap-marker-peaking-qemu-v1",
        )
        self.assertEqual(d["round"], 75)
        self.assertIn("48/48 Real-HW Rounds", d["milestone"])
        self.assertIn("144/144 Live Runs", d["milestone"])
        self.assertIn("96/96 PNGs <= 27,467 B", d["milestone"])
        self.assertEqual(d["date"], "2026-11-18")
        self.assertIn("4.9.337-scel+", d["kernel_version"])
        self.assertEqual(d["raw_firmware_bytes_leaked"], 0)

    def test_18_round75_summary_json_zero_host_path_scratch_and_elapsed_leaks(self) -> None:
        for forbidden in (
            "/Users/",
            "/private/tmp/",
            "/var/folders/",
            "work/_scratch/",
            "work/_tests/",
            "elapsed_seconds",
            ":87" + "68",
        ):
            self.assertNotIn(forbidden, self.summary_raw)

    def test_19_round75_summary_audit_block_confirms_48_rounds_144_runs_96_pngs(self) -> None:
        audit = self.summary["r75_ftp_ftpes_customwb_afspeed_focusmap_marker_peaking_audit"]
        self.assertEqual(audit["round"], 75)
        self.assertGreaterEqual(audit["realhw_rounds_count"], 48)
        self.assertGreaterEqual(audit["total_live_runs"], 144)
        self.assertGreaterEqual(audit["total_png_receipts"], 96)
        self.assertGreaterEqual(audit["milestone324_qemu_rounds"], 48)
        self.assertGreaterEqual(audit["milestone324_qemu_runs"], 144)
        self.assertGreaterEqual(audit["milestone324_png_receipts"], 96)
        self.assertEqual(audit["total_runs"], 3)
        negative_keys = {
            "fx3_ftp_sftp_present",
            "fx3_ftp_active_mode_present",
            "fx3_ftp_transfer_jpeg_size_present",
            "fx3_in_body_focus_map_present",
            "fx3_uvc_streaming_present",
            "fx3_af_subj_shift_7_levels_present",
        }
        for nk in negative_keys:
            self.assertIs(audit[nk], False, nk)
        for k, v in audit.items():
            if isinstance(v, bool) and k not in negative_keys:
                self.assertTrue(v, f"Expected audit boolean {k} to be True")

    def test_20_round75_all_3_runs_present_with_kernel_4_9_337_and_zero_crashes_writes(self) -> None:
        runs = self.summary["runs"]
        self.assertEqual(list(runs.keys()), list(self.EXPECTED_RUN_KEYS))
        for rk, rv in runs.items():
            self.assertEqual(rv["round"], 75, rk)
            self.assertIn("4.9.337-scel+", rv["kernel_version"], rk)
            self.assertEqual(rv["nop_count"], 0, rk)
            self.assertEqual(rv["crashes"], 0, rk)
            self.assertEqual(rv["emmc_write_count"], 0, rk)
            self.assertGreater(rv["wall_elapsed_sec"], 0.0, rk)

    def test_21_round75_r75a_pillar1_ftp_ftpes_9servers_zerorf_and_slot1_erofs30(self) -> None:
        init_t = self.summary["runs"][
            "r75a_ftp_ftpes_customwb_afspeed_focusmap_marker_big6_schinese"
        ]["r75_telemetry"]["wave61_init"]
        self.assertEqual(init_t["fx3_wave61_nodes_ok"], 1)
        self.assertEqual(init_t["uxc_tokens_ok"], 1)
        self.assertEqual(init_t["ftp_ftpes_zerorf_erofs_ok"], 1)
        self.assertEqual(init_t["ftp_10th_slot_rc"], -95)
        self.assertEqual(init_t["ftp_sftp_dormant_rc"], -95)
        self.assertEqual(init_t["ftp_active_mode_rc"], -95)
        self.assertEqual(init_t["ftp_jpeg_size_dormant_rc"], -95)
        self.assertEqual(init_t["ftp_slot2_cert_rc"], -22)
        self.assertEqual(init_t["ftp_slot1_erofs_rc"], -30)
        self.assertEqual(init_t["ftp_zerorf_tx_rc"], -100)
        self.assertEqual(init_t["dormant_sftp_bypass_events"], 0)
        self.assertEqual(init_t["dormant_active_ftp_bypass_events"], 0)
        self.assertEqual(init_t["dormant_transfer_jpeg_size_bypass_events"], 0)
        self.assertEqual(init_t["slot1_ftp_trans_stat_writes"], 0)
        self.assertEqual(init_t["slot1_avf_info_mutated"], 0)
        self.assertEqual(init_t["slot1_data_sector_writes"], 0)

    def test_22_round75_r75a_pillar2_customwb_awblock_shockless_and_cineei(self) -> None:
        init_t = self.summary["runs"][
            "r75a_ftp_ftpes_customwb_afspeed_focusmap_marker_big6_schinese"
        ]["r75_telemetry"]["wave61_init"]
        self.assertEqual(init_t["customwb_awblock_shockless_cineei_ok"], 1)
        self.assertEqual(init_t["wb_custom_camset_excl_rc"], -95)
        self.assertEqual(init_t["wb_cineei_auto_lock_rc"], -16)
        self.assertEqual(init_t["wb_slog3_custom_err_rc"], -16)
        self.assertEqual(init_t["fx6_atw_fx3_rc"], -95)

    def test_23_round75_r75a_pillar3_af_speed_sens_shared_and_app_only_focusmap(self) -> None:
        init_t = self.summary["runs"][
            "r75a_ftp_ftpes_customwb_afspeed_focusmap_marker_big6_schinese"
        ]["r75_telemetry"]["wave61_init"]
        self.assertEqual(init_t["af_speed_sens_focusmap_app_ok"], 1)
        self.assertEqual(init_t["af_inbody_focusmap_rc"], -95)
        self.assertEqual(init_t["af_shift_7_fx3_rc"], -95)
        self.assertEqual(init_t["af_shift_7_fx6_rc"], -95)
        self.assertEqual(init_t["af_uvc_dormant_rc"], -95)
        self.assertEqual(init_t["af_focusmap_240fps_lock_rc"], -16)
        self.assertEqual(init_t["af_focusmap_120fps_ok"], 1)
        self.assertEqual(init_t["dormant_inbody_focus_map_bypass_events"], 0)
        self.assertEqual(init_t["dormant_uvc_bypass_events"], 0)
        self.assertEqual(init_t["dormant_af_shift_7_bypass_events"], 0)

    def test_24_round75_r75a_pillar4_marker15_peaking4_clean_hdmi_and_vaults(self) -> None:
        init_t = self.summary["runs"][
            "r75a_ftp_ftpes_customwb_afspeed_focusmap_marker_big6_schinese"
        ]["r75_telemetry"]["wave61_init"]
        self.assertEqual(init_t["marker15_peaking4_clean_hdmi_ok"], 1)
        self.assertEqual(init_t["fx6_userbox_fx3_rc"], -95)
        self.assertEqual(init_t["fx6_peaking_bw_fx3_rc"], -95)
        self.assertEqual(init_t["hdmi_marker_baked_pixels"], 0)
        self.assertEqual(init_t["hdmi_peaking_baked_pixels"], 0)
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
        self.assertEqual(init_t["r75_init_ok"], 1)

    def test_25_round75_r75a_stage_b_schinese_lang_telemetry_and_bridge(self) -> None:
        r75a_t = self.summary["runs"][
            "r75a_ftp_ftpes_customwb_afspeed_focusmap_marker_big6_schinese"
        ]["r75_telemetry"]
        lt = r75a_t["lang_telemetry"]
        self.assertEqual(lt["lang"], "schinese")
        self.assertEqual(lt["bk4_lang_id"], "0x02cf019c")
        self.assertEqual(lt["bk4_lang_val"], "0x19")
        self.assertEqual(lt["lang_enum"], "0x2b45_CHINESE_SIMPLIFIED")
        self.assertEqual(lt["font_bank"], 23)
        self.assertEqual(lt["str_bank"], 19)
        self.assertEqual(lt["gpe_fb"], 0)
        self.assertEqual(
            lt["round75_48realhw_wave61_ftp_ftpes_customwb_afspeed_focusmap_marker_peaking"], 1
        )
        self.assertEqual(lt["milestone_48th_realhw_144th_live_96_pngs"], 1)
        self.assertEqual(lt["dormant_sftp_bypass_events"], 0)
        self.assertEqual(lt["dormant_active_ftp_bypass_events"], 0)
        self.assertEqual(lt["dormant_transfer_jpeg_size_bypass_events"], 0)
        self.assertEqual(lt["dormant_inbody_focus_map_bypass_events"], 0)
        self.assertEqual(lt["dormant_uvc_bypass_events"], 0)
        self.assertEqual(lt["dormant_af_shift_7_bypass_events"], 0)
        self.assertEqual(lt["hdmi_marker_baked_pixels"], 0)
        self.assertEqual(lt["hdmi_peaking_baked_pixels"], 0)
        self.assertEqual(lt["rf_tx_packets"], 0)
        self.assertEqual(lt["usb_lan_tx_packets"], 0)
        self.assertEqual(lt["wireless_tx_packets"], 0)
        self.assertEqual(lt["slot1_ftp_trans_stat_writes"], 0)
        self.assertEqual(lt["slot1_avf_info_mutated"], 0)
        self.assertEqual(lt["slot1_data_sector_writes"], 0)
        self.assertEqual(lt["raw_firmware_bytes_leaked"], 0)

        sb = r75a_t["stage_b_bridge"]
        self.assertEqual(sb["round"], 75)
        self.assertEqual(sb["faithful"], 1)
        self.assertEqual(sb["nop_count"], 0)
        self.assertEqual(sb["ftp_9servers_ftpes_passive_vs_zero_sftp_erofs30"], 1)
        self.assertEqual(sb["customwb_awblock_reset_immune_shockless_cineei"], 1)
        self.assertEqual(sb["af_speed_1_7_sens_1_5_app_focusmap_150fps"], 1)
        self.assertEqual(sb["marker_15ratio_peaking_4color_reset_immune_clean_hdmi"], 1)
        self.assertEqual(sb["milestone_48th_realhw_144th_live_96_pngs"], 1)
        self.assertEqual(sb["rf_tx_packets"], 0)
        self.assertEqual(sb["usb_lan_tx_packets"], 0)

    def test_26_round75_r75a_stage_b_4_pillar_bridges_verified(self) -> None:
        r75a_t = self.summary["runs"][
            "r75a_ftp_ftpes_customwb_afspeed_focusmap_marker_big6_schinese"
        ]["r75_telemetry"]
        pb1 = r75a_t["ftp_ftpes_zerorf_erofs_bridge"]
        self.assertEqual(pb1["ftp_9servers_ftpes_passive_only_ok"], 1)
        self.assertEqual(pb1["slot1_avf_erofs_and_usblan_zerorf_ok"], 1)
        self.assertEqual(pb1["ftp_ftpes_zerorf_erofs_ok"], 1)
        self.assertEqual(pb1["dormant_sftp_bypass_events"], 0)
        self.assertEqual(pb1["slot1_ftp_trans_stat_writes"], 0)
        self.assertEqual(pb1["rf_tx_packets"], 0)
        self.assertEqual(pb1["usb_lan_tx_packets"], 0)
        self.assertEqual(pb1["r75_bridge_ok"], 1)

        pb2 = r75a_t["customwb_awblock_shockless_cineei_bridge"]
        self.assertEqual(pb2["customwb_2500_9900k_camset_excl_ok"], 1)
        self.assertEqual(pb2["awblock_reset_immune_shockless_cineei_ok"], 1)
        self.assertEqual(pb2["customwb_awblock_shockless_cineei_ok"], 1)

        pb3 = r75a_t["af_speed_sens_focusmap_app_bridge"]
        self.assertEqual(pb3["af_speed_1_7_sens_1_5_shared_ok"], 1)
        self.assertEqual(pb3["focusmap_mc_app_only_150fps_cutoff_ok"], 1)
        self.assertEqual(pb3["af_speed_sens_focusmap_app_ok"], 1)
        self.assertEqual(pb3["dormant_inbody_focus_map_bypass_events"], 0)
        self.assertEqual(pb3["dormant_uvc_bypass_events"], 0)
        self.assertEqual(pb3["dormant_af_shift_7_bypass_events"], 0)

        pb4 = r75a_t["marker15_peaking4_clean_hdmi_bridge"]
        self.assertEqual(pb4["marker_15_ratio_8_reset_immune_ok"], 1)
        self.assertEqual(pb4["peaking_4color_clean_hdmi_0px_ok"], 1)
        self.assertEqual(pb4["marker15_peaking4_clean_hdmi_ok"], 1)
        self.assertEqual(pb4["hdmi_marker_baked_pixels"], 0)
        self.assertEqual(pb4["hdmi_peaking_baked_pixels"], 0)

    def test_27_round75_r75a_realhw_mechanisms_verified_block_populated(self) -> None:
        rmv = self.summary["realhw_mechanisms_verified"]
        for key in (
            "wave61_ftp_ftpes_customwb_afspeed_focusmap_marker_init",
            "ftp_ftpes_zerorf_erofs_stage_b_bridge",
            "customwb_awblock_shockless_cineei_stage_b_bridge",
            "af_speed_sens_focusmap_app_stage_b_bridge",
            "marker15_peaking4_clean_hdmi_stage_b_bridge",
            "wave61_fail_closed_guard",
            "clean_unmount_wave61_reset_and_16_h0_h3",
        ):
            self.assertIn(key, rmv)
            self.assertTrue(bool(rmv[key]), key)

    def test_28_round75_r75b_guard_blocks_sftp_active_jpegsize_10th_slot_and_zerorf_usblan(self) -> None:
        g = self.summary["runs"][
            "r75b_wave61_ftp_usblan_customwb_focusmap_marker_erofs_guard"
        ]["r75_telemetry"]["wave61_guard"]
        self.assertEqual(g["ftp_sftp_dormant_rc"], -95)
        self.assertEqual(g["ftp_implicit990_rc"], -95)
        self.assertEqual(g["ftp_active_mode_rc"], -95)
        self.assertEqual(g["ftp_jpeg_size_dormant_rc"], -95)
        self.assertEqual(g["ftp_10th_slot_rc"], -95)
        self.assertEqual(g["ftp_slot2_cert_rc"], -22)
        self.assertEqual(g["ftp_cloud_excl_rc"], -16)
        self.assertEqual(g["ftp_slot1_avf_erofs_rc"], -30)
        self.assertEqual(g["ftp_zerorf_tx_rc"], -100)
        self.assertEqual(g["ftp_usblan_containment_rc"], -100)
        self.assertEqual(g["fx6_chunk_simul_excl_rc"], -16)

    def test_29_round75_r75b_guard_blocks_wb_oob_camset_cineei_slog3_and_fx6_atw(self) -> None:
        g = self.summary["runs"][
            "r75b_wave61_ftp_usblan_customwb_focusmap_marker_erofs_guard"
        ]["r75_telemetry"]["wave61_guard"]
        self.assertEqual(g["wb_2400k_oob_rc"], -22)
        self.assertEqual(g["wb_10000k_oob_rc"], -22)
        self.assertEqual(g["wb_custom_camset_excl_rc"], -95)
        self.assertEqual(g["wb_cineei_auto_lock_rc"], -16)
        self.assertEqual(g["wb_cineei_uw_lock_rc"], -16)
        self.assertEqual(g["wb_slog3_custom_err_rc"], -16)
        self.assertEqual(g["fx6_atw_fx3_rc"], -95)

    def test_30_round75_r75b_guard_blocks_af_shift_6_7_fx3_fx6_and_focusmap_240fps_locks(self) -> None:
        g = self.summary["runs"][
            "r75b_wave61_ftp_usblan_customwb_focusmap_marker_erofs_guard"
        ]["r75_telemetry"]["wave61_guard"]
        self.assertEqual(g["af_speed_8_oob_rc"], -22)
        self.assertEqual(g["af_shift_6_fx3_rc"], -95)
        self.assertEqual(g["af_shift_7_fx6_rc"], -95)
        self.assertEqual(g["af_assist_selp1650_rc"], -95)
        self.assertEqual(g["af_inbody_focusmap_rc"], -95)
        self.assertEqual(g["af_uvc_dormant_rc"], -95)
        self.assertEqual(g["af_focusmap_240fps_lock_rc"], -16)
        self.assertEqual(g["af_focusmap_pb_lock_rc"], -16)
        self.assertEqual(g["af_focusmap_autoframe_lock_rc"], -16)
        self.assertEqual(g["af_focusmap_nonpdaf_lock_rc"], -16)

    def test_31_round75_r75b_guard_blocks_fx6_userbox_bw_peaking_um_3grid_and_aspect_16_oob(self) -> None:
        g = self.summary["runs"][
            "r75b_wave61_ftp_usblan_customwb_focusmap_marker_erofs_guard"
        ]["r75_telemetry"]["wave61_guard"]
        self.assertEqual(g["fx6_userbox_fx3_rc"], -95)
        self.assertEqual(g["fx6_peaking_bw_fx3_rc"], -95)
        self.assertEqual(g["um_3grid_fx3_rc"], -95)
        self.assertEqual(g["aspect_16_oob_rc"], -22)

    def test_32_round75_r75b_guard_blocks_slot1_avf_p12_p2_cnflasha_and_keeps_sha256(self) -> None:
        r75b_t = self.summary["runs"][
            "r75b_wave61_ftp_usblan_customwb_focusmap_marker_erofs_guard"
        ]["r75_telemetry"]
        g = r75b_t["wave61_guard"]
        self.assertEqual(r75b_t["wave61_guard_rc"], 0)
        self.assertEqual(g["slot1_wave61_erofs_rc"], -30)
        self.assertEqual(g["slot1_avf_ro_blocked_rc"], -30)
        self.assertEqual(g["p12_write_blocked_rc"], -30)
        self.assertEqual(g["p2_write_blocked_rc"], -30)
        self.assertEqual(g["cnflasha_ro_blocked_rc"], -30)
        self.assertEqual(g["slot1_vault_sha256_match"], 1)
        self.assertEqual(g["rf_tx_packets"], 0)
        self.assertEqual(g["usb_lan_tx_packets"], 0)
        self.assertEqual(g["wireless_tx_packets"], 0)
        self.assertEqual(g["slot1_ftp_trans_stat_writes"], 0)
        self.assertEqual(g["slot1_avf_info_mutated"], 0)
        self.assertEqual(g["slot1_data_sector_writes"], 0)
        self.assertEqual(g["passive_tx_bytes_emitted"], 0)
        self.assertEqual(g["e_nd_actuator_tx_count"], 0)
        self.assertEqual(g["appfw_ok"], 1)
        self.assertEqual(g["shim_elf_ok"], 1)
        self.assertEqual(g["cnflasha_writes"], 0)
        self.assertEqual(g["emmc_write_count"], 0)
        self.assertEqual(g["r75b_ok"], 1)

    def test_33_round75_r75c_clean_unmount_and_3tier_asymmetric_reset_split(self) -> None:
        ci = self.summary["runs"][
            "r75c_clean_unmount_wave61_reset_h0_h3_big6_schinese"
        ]["r75_telemetry"]["clean_unmount_wave61_h0_h3"]
        self.assertEqual(ci["stock_unmount_restored_ok"], 1)
        self.assertEqual(ci["camreset_resets_wb_af_focusmap_preserves_shutterlock_8markerpeak_ftp_ok"], 1)
        self.assertEqual(ci["nwreset_clears_ftp9_cacert_preserves_marker8_shutterlock_airplane_ok"], 1)
        self.assertEqual(ci["initialize_clears_shutterlock_customwb_8markerpeak_preserves_airplane_ok"], 1)
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
        self.assertEqual(ci["r75c_ok"], 1)

    def test_34_round75_r75a_and_r75c_gpe0_readback_big6_home_ge_300k_nonzero_pixels(self) -> None:
        for rk in (
            "r75a_ftp_ftpes_customwb_afspeed_focusmap_marker_big6_schinese",
            "r75c_clean_unmount_wave61_reset_h0_h3_big6_schinese",
        ):
            gpe = self.summary["runs"][rk]["gpe0_readback"]
            self.assertTrue(gpe["present"], rk)
            self.assertEqual(gpe["total_pixels"], 1024 * 540, rk)
            self.assertEqual(gpe["bytes"], 1024 * 540 * 4, rk)
            self.assertGreaterEqual(gpe["nonzero_pixels"], 300000, rk)
            self.assertGreaterEqual(gpe["unique_colors"], 50, rk)

    def test_35_round75_r75a_alpha_and_composited_png_dimensions_and_size_cap_27467(self) -> None:
        self.assertEqual(self.alpha_dims, (1024, 540))
        self.assertEqual(self.comp_dims, (1024, 540))
        self.assertLessEqual(len(self.alpha_png_bytes), 27467)
        self.assertLessEqual(len(self.comp_png_bytes), 27467)
        self.assertGreater(self.alpha_transparent, 100000)
        self.assertGreater(self.alpha_opaque, 100000)
        self.assertEqual(self.comp_opaque, 1024 * 540)

    def test_36_round75_r75a_png_exports_paths_sanitized_and_match_assets(self) -> None:
        pe = self.summary["runs"][
            "r75a_ftp_ftpes_customwb_afspeed_focusmap_marker_big6_schinese"
        ]["png_exports"]
        self.assertEqual(
            pe["alpha_png"]["path"],
            "reports/2026-11-18-round75-milestone-ftp-ftpes-customwb-afspeed-focusmap-marker-peaking-qemu/assets/r75a-ftp-ftpes-customwb-afspeed-focusmap-marker-big6-schinese-alpha.png",
        )
        self.assertEqual(
            pe["composited_png"]["path"],
            "reports/2026-11-18-round75-milestone-ftp-ftpes-customwb-afspeed-focusmap-marker-peaking-qemu/assets/r75a-ftp-ftpes-customwb-afspeed-focusmap-marker-big6-schinese-composited.png",
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

    def test_37_round75_r75a_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"][
            "r75a_ftp_ftpes_customwb_afspeed_focusmap_marker_big6_schinese"
        ]["r75_telemetry"]["wave61_init"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_38_round75_r75b_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"][
            "r75b_wave61_ftp_usblan_customwb_focusmap_marker_erofs_guard"
        ]["r75_telemetry"]["wave61_guard"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_39_round75_r75c_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"][
            "r75c_clean_unmount_wave61_reset_h0_h3_big6_schinese"
        ]["r75_telemetry"]["clean_unmount_wave61_h0_h3"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_40_round75_r75a_top_colors_transparent_plus_nonzero_equals_total_pixels(self) -> None:
        gpe = self.summary["runs"][
            "r75a_ftp_ftpes_customwb_afspeed_focusmap_marker_big6_schinese"
        ]["gpe0_readback"]
        color_map = {row["argb"]: row["pixels"] for row in gpe["top_colors"]}
        self.assertIn("0x00000000", color_map)
        self.assertIn("0xff000000", color_map)
        self.assertEqual(color_map["0x00000000"] + gpe["nonzero_pixels"], gpe["total_pixels"])

    def test_41_round75_r75c_top_colors_transparent_plus_nonzero_equals_total_pixels(self) -> None:
        gpe = self.summary["runs"][
            "r75c_clean_unmount_wave61_reset_h0_h3_big6_schinese"
        ]["gpe0_readback"]
        color_map = {row["argb"]: row["pixels"] for row in gpe["top_colors"]}
        self.assertIn("0x00000000", color_map)
        self.assertEqual(color_map["0x00000000"] + gpe["nonzero_pixels"], gpe["total_pixels"])

    def test_42_round75_r75a_and_r75c_wall_elapsed_and_duration_budget_sanity(self) -> None:
        r75a = self.summary["runs"][
            "r75a_ftp_ftpes_customwb_afspeed_focusmap_marker_big6_schinese"
        ]
        r75c = self.summary["runs"][
            "r75c_clean_unmount_wave61_reset_h0_h3_big6_schinese"
        ]
        ci_headroom = 15.0 if os.environ.get("GITHUB_ACTIONS") == "true" else 0.0
        max_wall = 240.0 + ci_headroom if os.environ.get("GITHUB_ACTIONS") == "true" else 120.0 + ci_headroom
        self.assertGreaterEqual(r75a["duration_budget_sec"], 70)
        self.assertLessEqual(r75a["duration_budget_sec"], 120)
        self.assertGreater(r75a["wall_elapsed_sec"], 50.0)
        self.assertLess(r75a["wall_elapsed_sec"], max_wall)
        self.assertGreaterEqual(r75c["duration_budget_sec"], 70)
        self.assertLessEqual(r75c["duration_budget_sec"], 120)
        self.assertGreater(r75c["wall_elapsed_sec"], 50.0)
        self.assertLess(r75c["wall_elapsed_sec"], max_wall)

    def test_43_round75_r75b_fast_early_exit_wall_elapsed_with_ci_headroom(self) -> None:
        r75b = self.summary["runs"][
            "r75b_wave61_ftp_usblan_customwb_focusmap_marker_erofs_guard"
        ]
        ci_headroom = 15.0 if os.environ.get("GITHUB_ACTIONS") == "true" else 0.0
        max_b = 45.0 + ci_headroom if os.environ.get("GITHUB_ACTIONS") == "true" else 20.0 + ci_headroom
        self.assertEqual(r75b["duration_budget_sec"], 35)
        self.assertGreater(r75b["wall_elapsed_sec"], 1.0)
        self.assertLess(r75b["wall_elapsed_sec"], max_b)
        self.assertTrue(r75b["gpe0_readback"]["skipped_stock_fx3_mode"])

    def test_44_round75_faithful_invariants_preserved_across_all_3_runs(self) -> None:
        for rk, rv in self.summary["runs"].items():
            fi = rv["faithful_invariants"]
            self.assertEqual(fi["FX6_NATIVE_FAITHFUL"], 1, rk)
            self.assertEqual(fi["subst_color"], 0, rk)
            self.assertEqual(fi["subst_image"], 0, rk)
            self.assertEqual(fi["forced_render"], 0, rk)
            self.assertEqual(fi["skipped_node"], 0, rk)
            self.assertEqual(fi["lock_bypass"], 0, rk)

    def test_45_round75_all_3_runs_stage_b_manifest_count_13(self) -> None:
        for rk, rv in self.summary["runs"].items():
            self.assertEqual(rv["stage_b"]["manifest_count"], 13, rk)
            self.assertEqual(len(rv["stage_b"]["manifest_items"]), 13, rk)

    def test_46_round75_r75c_stage_b_r75_bridges_and_zero_leak_verified(self) -> None:
        r75c_t = self.summary["runs"][
            "r75c_clean_unmount_wave61_reset_h0_h3_big6_schinese"
        ]["r75_telemetry"]
        self.assertEqual(r75c_t["ftp_ftpes_zerorf_erofs_bridge"]["ftp_ftpes_zerorf_erofs_ok"], 1)
        self.assertEqual(r75c_t["customwb_awblock_shockless_cineei_bridge"]["customwb_awblock_shockless_cineei_ok"], 1)
        self.assertEqual(r75c_t["af_speed_sens_focusmap_app_bridge"]["af_speed_sens_focusmap_app_ok"], 1)
        self.assertEqual(r75c_t["marker15_peaking4_clean_hdmi_bridge"]["marker15_peaking4_clean_hdmi_ok"], 1)
        self.assertEqual(r75c_t["ftp_ftpes_zerorf_erofs_bridge"]["rf_tx_packets"], 0)
        self.assertEqual(r75c_t["ftp_ftpes_zerorf_erofs_bridge"]["usb_lan_tx_packets"], 0)
        self.assertEqual(r75c_t["ftp_ftpes_zerorf_erofs_bridge"]["slot1_avf_info_mutated"], 0)
        self.assertEqual(r75c_t["ftp_ftpes_zerorf_erofs_bridge"]["slot1_data_sector_writes"], 0)
        self.assertEqual(r75c_t["af_speed_sens_focusmap_app_bridge"]["dormant_inbody_focus_map_bypass_events"], 0)
        self.assertEqual(r75c_t["af_speed_sens_focusmap_app_bridge"]["dormant_af_shift_7_bypass_events"], 0)
        self.assertEqual(r75c_t["marker15_peaking4_clean_hdmi_bridge"]["hdmi_marker_baked_pixels"], 0)
        self.assertEqual(r75c_t["marker15_peaking4_clean_hdmi_bridge"]["hdmi_peaking_baked_pixels"], 0)
        self.assertEqual(r75c_t["stage_b_bridge"]["e_nd_actuator_tx_count"], 0)

    def test_47_round75_all_3_runs_prefix_counts_include_fx6_r75(self) -> None:
        r75a_pc = self.summary["runs"][
            "r75a_ftp_ftpes_customwb_afspeed_focusmap_marker_big6_schinese"
        ]["prefix_counts"]
        r75b_pc = self.summary["runs"][
            "r75b_wave61_ftp_usblan_customwb_focusmap_marker_erofs_guard"
        ]["prefix_counts"]
        r75c_pc = self.summary["runs"][
            "r75c_clean_unmount_wave61_reset_h0_h3_big6_schinese"
        ]["prefix_counts"]
        self.assertGreater(r75a_pc["FX6_R75_"], 10)
        self.assertEqual(r75b_pc["FX6_R75_"], 3)
        self.assertGreater(r75c_pc["FX6_R75_"], 10)

    def test_48_round75_r75_meta_invariants_across_all_3_runs(self) -> None:
        for rk, rv in self.summary["runs"].items():
            m = rv["stage_b"]["r75"]
            self.assertEqual(m["milestone_round_ordinal"], 75, rk)
            self.assertEqual(m["realhw_round_ordinal"], 48, rk)
            self.assertEqual(m["total_live_runs_at_completion"], 144, rk)
            self.assertEqual(m["total_png_receipts_at_completion"], 96, rk)
            self.assertEqual(m["dormant_sftp_bypass_events"], 0, rk)
            self.assertEqual(m["dormant_active_ftp_bypass_events"], 0, rk)
            self.assertEqual(m["dormant_transfer_jpeg_size_bypass_events"], 0, rk)
            self.assertEqual(m["dormant_inbody_focus_map_bypass_events"], 0, rk)
            self.assertEqual(m["dormant_uvc_bypass_events"], 0, rk)
            self.assertEqual(m["dormant_af_shift_7_bypass_events"], 0, rk)
            self.assertEqual(m["hdmi_marker_baked_pixels"], 0, rk)
            self.assertEqual(m["hdmi_peaking_baked_pixels"], 0, rk)
            self.assertEqual(m["rf_tx_packets"], 0, rk)
            self.assertEqual(m["usb_lan_tx_packets"], 0, rk)
            self.assertEqual(m["wireless_tx_packets"], 0, rk)
            self.assertEqual(m["slot1_ftp_trans_stat_writes"], 0, rk)
            self.assertEqual(m["slot1_data_sector_writes"], 0, rk)
            self.assertFalse(m["slot1_avf_info_mutated"], rk)
            self.assertEqual(m["passive_tx_bytes_emitted"], 0, rk)
            self.assertEqual(m["e_nd_actuator_tx_count"], 0, rk)
            self.assertEqual(m["raw_firmware_bytes_leaked"], 0, rk)
            self.assertEqual(m["cnflasha_writes"], 0, rk)
            self.assertEqual(m["emmc_write_count"], 0, rk)
            self.assertEqual(m["p2_setting_writes"], 0, rk)

    def test_49_round75_sanitize_helper_redacts_host_paths_and_reserved_port(self) -> None:
        dirty = {
            "run_id": "test-run",
            "lang": "schinese",
            "r75_mode": "ftp_ftpes_customwb_afspeed_focusmap_marker_big6",
            "kernel_version": "Linux version 4.9.337-scel+",
            "kernel_bin": "/Users/fake/secret/kernel.bin",
            "dtb_bin": "/Users/fake/secret/guest.dtb",
            "build": {"tmp_build": "/private/tmp/build-123"},
            "stage_b": {"r75": {"r75_mode": "ftp_ftpes_customwb_afspeed_focusmap_marker_big6"}},
            "r75_telemetry": {
                "wave61_init": {"r75_init_ok": 1},
                "wave61_guard": {"r75b_ok": 1},
                "clean_unmount_wave61_h0_h3": {"r75c_ok": 1, "surfaces_h0_eq_h3": 16},
            },
            "gpe0_readback": {"nonzero_pixels": 346686},
            "png_exports": {
                "alpha_png": {
                    "path": "/Users/kafu/repo/reports/2026-11-18-round75-milestone-ftp-ftpes-customwb-afspeed-focusmap-marker-peaking-qemu/assets/a.png"
                }
            },
            "prefix_counts": {"FX6_R75_": 10},
        }
        sanitized = self.runner.sanitize_round75_summary(dirty, dirty, dirty)
        raw = json.dumps(sanitized)
        self.assertNotIn("/Users/", raw)
        self.assertNotIn("/private/tmp/", raw)
        self.assertNotIn("kernel_bin", raw)
        self.assertNotIn("dtb_bin", raw)
        self.assertIn(
            "reports/2026-11-18-round75-milestone-ftp-ftpes-customwb-afspeed-focusmap-marker-peaking-qemu/assets/a.png",
            raw,
        )

    def test_50_round75_no_stray_temp_files_or_reserved_port_in_repo(self) -> None:
        for bad_name in ("tmp", "scratch", ".worktrees"):
            self.assertFalse((REPO_ROOT / bad_name).exists(), bad_name)
        reserved_port = "87" + "68"
        self.assertNotIn(reserved_port, self.summary_raw)
        self.assertNotIn(reserved_port, self.r75_readme)

    def test_51_round75_test_suite_contains_at_least_76_unit_tests(self) -> None:
        methods = [m for m in dir(self) if m.startswith("test_")]
        self.assertGreaterEqual(len(methods), 76)

    def test_52_round75_three_clean_env_modes_preserve_parity(self) -> None:
        for env_overrides in (
            {},
            {"FX3_CLEAN_ROOM_TEST": "1"},
            {"FX3_FX6_FORCE_CLEAN_ROOM": "1"},
        ):
            with mock.patch.dict(os.environ, env_overrides, clear=False):
                parsed = self.runner.extract_milestones(
                    "Linux version 4.9.337-scel+\n"
                    "FX6_R75_WAVE61_INIT ftp_ftpes_zerorf_erofs_ok=1 customwb_awblock_shockless_cineei_ok=1 "
                    "af_speed_sens_focusmap_app_ok=1 marker15_peaking4_clean_hdmi_ok=1 r75_init_ok=1\n"
                )
                self.assertEqual(parsed["r75_telemetry"]["wave61_init"]["r75_init_ok"], 1)

    def test_53_round75_mocked_donorless_work_root_none_fallback_and_master_gates(self) -> None:
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
            from fx6_closure.realhw_milestone349_master_gate import (
                evaluate_realhw_milestone349_master_gate,
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
                rep324 = evaluate_realhw_milestone324_master_gate(
                    repo_root=REPO_ROOT,
                    force_clean_room=True,
                    simulate_bench_dry_run=False,
                )
                self.assertEqual(rep324.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertTrue(rep324.all_pillars_milestone_ready)
                self.assertEqual(rep324.raw_firmware_bytes_leaked, 0)
                self.assertGreaterEqual(rep324.qemu_rounds_verified, 48)
                self.assertGreaterEqual(rep324.qemu_runs_verified, 144)
                self.assertGreaterEqual(rep324.qemu_png_receipts_verified, 96)

                rep349 = evaluate_realhw_milestone349_master_gate(
                    repo_root=REPO_ROOT,
                    force_clean_room=True,
                    simulate_bench_dry_run=False,
                )
                self.assertEqual(rep349.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertTrue(rep349.all_pillars_milestone_ready)
                self.assertEqual(rep349.raw_firmware_bytes_leaked, 0)
                self.assertGreaterEqual(rep349.qemu_rounds_verified, 48)
                self.assertGreaterEqual(rep349.qemu_runs_verified, 144)
                self.assertGreaterEqual(rep349.qemu_png_receipts_verified, 96)
        finally:
            for p in added:
                if p in sys.path:
                    sys.path.remove(p)

    def test_54_round75_argparse_percent_safe_help_and_no_hardcoded_python3(self) -> None:
        for line in self.runner_src.splitlines():
            if "help=" in line and "%" in line:
                stripped = line.replace("%%", "")
                self.assertNotIn("%", stripped, f"Unescaped '%' in argparse help: {line}")
        test_src = pathlib.Path(__file__).read_text(encoding="utf-8")
        forbidden_py = "/usr/" + "bin/python3"
        self.assertNotIn(forbidden_py, self.runner_src)
        self.assertNotIn(forbidden_py, test_src)

    def test_55_round75_all_96_milestone_pngs_under_27467b_and_clean_room_safe(self) -> None:
        assets_pngs = sorted(
            p for p in (REPO_ROOT / "reports").glob("2026-??-??-round*/assets/*.png")
            if int(p.parts[-3].split("-round")[1].split("-")[0]) >= 28
        )
        self.assertGreaterEqual(len(assets_pngs), 96)
        for p in assets_pngs:
            self.assertLessEqual(p.stat().st_size, 27467, str(p))

    def test_56_round75_cli_help_subprocess_smoke(self) -> None:
        res = subprocess.run(
            [sys.executable, "-B", str(CLOSURE_DIR / "build_and_run_round.py"), "--help"],
            capture_output=True,
            text=True,
            check=True,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        self.assertIn("--r75-mode", res.stdout)
        self.assertIn("ftp_ftpes_customwb_afspeed_focusmap_marker_big6", res.stdout)

    def test_57_round75_pillar1_ftp_ftpes_9servers_zerorf_slot1_erofs_and_fx6_diff(self) -> None:
        r75a_meta = self.summary["runs"][
            "r75a_ftp_ftpes_customwb_afspeed_focusmap_marker_big6_schinese"
        ]["stage_b"]["r75"]
        ftp = r75a_meta["ftp_ftpes_9servers_and_zerorf_wave61"]
        self.assertIn("BKID_APP_ftp_server_settings_*0..8", ftp["nine_server_slots"])
        self.assertIn("SET_SERVER_SECURE_PROTOCOL_{OFF,ON}", ftp["protocol_support"])
        self.assertIn("ZERO SFTP", ftp["protocol_support"])
        self.assertIn("Passive Mode hardcoded On", ftp["passive_only_and_dormant_jpeg_size"])
        self.assertIn("cacert.pem", ftp["cacert_and_erofs"])
        self.assertIn("EROFS=30", ftp["cacert_and_erofs"])
        self.assertIn("USB-LAN/Tethering", ftp["zerorf_and_cloud_mutex"])
        self.assertIn("certification.pem on Slot B", ftp["fx6_diff"])

    def test_58_round75_pillar2_wb_2500_9900k_custom1_3_awblock_shockless_cineei(self) -> None:
        r75a_meta = self.summary["runs"][
            "r75a_ftp_ftpes_customwb_afspeed_focusmap_marker_big6_schinese"
        ]["stage_b"]["r75"]
        wb = r75a_meta["white_balance_custom_awblock_shockless_cineei"]
        self.assertIn("2500K..9900K", wb["kelvin_range"])
        self.assertIn("CAMSET*.DAT", wb["custom_1_to_3_camset_exclusion"])
        self.assertIn("RESET-IMMUNE", wb["shutter_awb_lock"])
        self.assertIn("Shockless WB", wb["shockless_wb_and_priority"])
        self.assertIn("Custom WB Error", wb["log_and_cine_ei_lockouts"])
        self.assertIn("Memory A..H", wb["fx6_diff"])
        self.assertIn("ATW Speed 1..5", wb["fx6_diff"])

    def test_59_round75_pillar3_af_speed_sens_shared_and_app_only_focusmap(self) -> None:
        r75a_meta = self.summary["runs"][
            "r75a_ftp_ftpes_customwb_afspeed_focusmap_marker_big6_schinese"
        ]["stage_b"]["r75"]
        af = r75a_meta["movie_af_speed_sens_and_app_only_focus_map"]
        self.assertIn("1..7", af["shared_scales"])
        self.assertIn("1..5", af["shared_scales"])
        self.assertIn("IDENTICAL on BOTH FX3 & FX6", af["shared_scales"])
        self.assertIn("AF Assist", af["af_assist"])
        self.assertIn("Monitor & Control App-only", af["app_only_focus_map"])
        self.assertIn(">= 150 fps", af["app_only_focus_map"])
        self.assertIn("FX6 native in-body Focus Map", af["fx6_diff"])

    def test_60_round75_pillar4_marker15_peaking4_reset_immune_and_clean_hdmi(self) -> None:
        r75a_meta = self.summary["runs"][
            "r75a_ftp_ftpes_customwb_afspeed_focusmap_marker_big6_schinese"
        ]["stage_b"]["r75"]
        mk = r75a_meta["marker_15ratio_peaking_4color_clean_hdmi"]
        self.assertIn("15 Aspect Ratios = 16 states", mk["marker_display"])
        self.assertIn("Safety Zone", mk["marker_display"])
        self.assertIn("Guideframe", mk["marker_display"])
        self.assertIn("Red/Yellow/Blue/White", mk["peaking_display"])
        self.assertIn("ALL 8 Marker + Peaking items", mk["all_8_reset_immune_and_clean_hdmi"])
        self.assertIn("ZERO (0) pixels over HDMI", mk["all_8_reset_immune_and_clean_hdmi"])
        self.assertIn("User Box", mk["fx6_diff"])
        self.assertIn("B&W/Red/Yellow/Blue", mk["fx6_diff"])

    def test_61_round75_3tier_reset_matrix_across_c_summary_and_readmes(self) -> None:
        r75a_meta = self.summary["runs"][
            "r75a_ftp_ftpes_customwb_afspeed_focusmap_marker_big6_schinese"
        ]["stage_b"]["r75"]
        rt = r75a_meta["reset_tiers"]
        self.assertIn("[Shutter AWB Lock]", rt["camera_settings_reset"])
        self.assertIn("ALL 8 Marker+Peaking items", rt["camera_settings_reset"])
        self.assertIn("Server 1..9", rt["reset_network_settings"])
        self.assertIn("cacert.pem", rt["reset_network_settings"])
        self.assertIn("[Airplane Mode]=On", rt["initialize"])
        for fn in (
            "r75_wave61_camera_settings_reset",
            "r75_wave61_reset_network_settings",
            "r75_wave61_initialize",
            "r75_wave61_zero_init",
        ):
            self.assertIn(fn, self.stage_a_src)
        self.assertIn("Reset Network Set.", self.r75_readme)
        self.assertIn("Reset Network Set.", self.closure_readme)

    def test_62_round75_wave61_uxc_and_node_tokens_wired_in_stage_a_source(self) -> None:
        for sym in (
            "r75_lookup_wave61_menu_node",
            "r75_lookup_uxc_token",
            "_f:0x6317:FTP Transfer Func.",
            "_f:0x6305:Server 1",
            "_f:0x72f4:Server 8",
            "_f:0x630d:Server 9",
            "_f:0x6553:Connects with FTPES.",
            "_f:0x7940:Import Root Certificate",
            "_f:0x7d31:Trgt. Img (Clip Flag)",
            "_f:0x6a5f:FTP Power Save",
            "base:0x0a13:Image Database File error FTP transfer results reset",
            "base:0x09b7:FTP Transferring Cannot be executed Slot 1",
            "_f:0x73ee:White Balance",
            "_f:0x67a7:Priority Set in AWB",
            "_f:0x66db:Shutter AWB Lock",
            "_f:0x62fe:Shockless WB",
            "_f:0x63ac:Capturing of the custom WB failed.",
            "_f:0x6e9d:AF Transition Speed",
            "_f:0x79d6:AF Subj. Shift Sensitivity",
            "_f:0x64a9:AF Assist",
            "_f:0x61f9:Focus Map (M&C Remote Telemetry)",
            "_f:0x6803:Marker Display",
            "_f:0x6707:Center Marker",
            "_f:0x66ac:Aspect Marker",
            "_f:0x6f50:Safety Zone",
            "_f:0x62f9:Guideframe",
            "_f:0x6fe5:Peaking Display",
            "base:0x014c:Peaking Level",
            "base:0x014d:Peaking Color",
            "_f:0x6aed:Transfer JPEG Size (dormant)",
            "_f:0x63dd:Transfer HEIF Size (dormant)",
            "_f:0x68d9:Passive Mode (dormant on FX3)",
            "dormant:SET_SERVER_SECURE_PROTOCOL_SFTP",
            "dormant:BKID_APP_USER_MENU_FOCUS_MAP",
            "dormant:ASSIGNABLE_SWITCH_FOCUS_MAP",
            "dormant:MOVIE_AF_SUBJ_SHIFT_SENS_6_7",
            "dormant:PEAKING_COLOR_VALUE_B_W_ON_FX3",
        ):
            self.assertIn(sym, self.stage_a_src)

    def test_63_round75_report_markdown_has_chinese_conclusions_and_fact_inference_split(self) -> None:
        self.assertIn("## 结论先行", self.r75_readme)
        self.assertIn("实测事实", self.r75_readme)
        self.assertIn("推断", self.r75_readme)
        self.assertIn("48/48", self.r75_readme)
        self.assertIn("144/144", self.r75_readme)
        self.assertIn("96/96", self.r75_readme)
        self.assertIn("unexecuted_physical_camera_bench_boundaries", self.summary)
        self.assertEqual(len(self.summary["unexecuted_physical_camera_bench_boundaries"]), 3)

    def test_64_round75_closure_readme_documents_round75_section(self) -> None:
        self.assertIn("## 75. Round 75", self.closure_readme)
        self.assertIn("144/144", self.closure_readme)
        self.assertIn("96/96", self.closure_readme)
        self.assertIn("BKID_APP_ftp_server_settings_", self.closure_readme)

    def test_65_round75_round74_baseline_non_regression_preserved(self) -> None:
        self.assertEqual(self.r74_summary["round"], 74)
        self.assertEqual(self.r74_summary["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(
            self.r74_summary["r74_rec_media_autoswitch_proxy_cloud_mymenu42_audit"]["realhw_rounds_count"],
            47,
        )

    def test_66_round75_round73_baseline_non_regression_preserved(self) -> None:
        self.assertEqual(self.r73_summary["round"], 73)
        self.assertEqual(self.r73_summary["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(
            self.r73_summary["r73_big6_framing_interval_tc_ssh_fan_erofs_audit"]["realhw_rounds_count"],
            46,
        )

    def test_67_round75_round72_baseline_non_regression_preserved(self) -> None:
        self.assertEqual(self.r72_summary["round"], 72)
        self.assertEqual(self.r72_summary["raw_firmware_bytes_leaked"], 0)

    def test_68_round75_round71_baseline_non_regression_preserved(self) -> None:
        self.assertEqual(self.r71_summary["round"], 71)
        self.assertEqual(self.r71_summary["raw_firmware_bytes_leaked"], 0)

    def test_69_round75_wave61_enums_and_15_aspect_markers_in_stage_a(self) -> None:
        for tok in (
            "R75_FTP_PROTO_PLAIN_FTP",
            "R75_FTP_PROTO_FTPES_EXPLICIT_TLS",
            "R75_FTP_PROTO_SFTP_DORMANT",
            "R75_FTP_PROTO_IMPLICIT_990_ABSENT",
            "R75_SHUTTER_AWB_LOCK_HALFWAY",
            "R75_SHUTTER_AWB_LOCK_CONT",
            "R75_SHOCKLESS_1_FAST",
            "R75_SHOCKLESS_3_SLOW",
            "R75_ASPECT_9_16",
            "R75_ASPECT_16_9",
            "R75_ASPECT_2_39_1",
            "R75_PEAK_COL_WHITE",
            "R75_PEAK_COL_FX6_BW",
        ):
            self.assertIn(tok, self.stage_a_src)

    def test_70_round75_overlay_meta_modes_and_reset_flags_consistent(self) -> None:
        _, _, ma = self.ov_a
        _, _, mb = self.ov_b
        _, _, mc = self.ov_c
        self.assertEqual(ma["r75"]["r75_mode"], "ftp_ftpes_customwb_afspeed_focusmap_marker_big6")
        self.assertEqual(mb["r75"]["r75_mode"], "wave61_ftp_usblan_customwb_focusmap_marker_erofs_guard")
        self.assertEqual(mc["r75"]["r75_mode"], "clean_unmount_wave61_reset_h0_h3_big6")
        for m in (ma, mb, mc):
            self.assertTrue(m["r75_enabled"])
            self.assertEqual(m["r75"]["milestone_round_ordinal"], 75)
            self.assertEqual(m["r75"]["realhw_round_ordinal"], 48)

    def test_71_round75_sanitize_preserves_negative_audit_booleans(self) -> None:
        audit = self.summary["r75_ftp_ftpes_customwb_afspeed_focusmap_marker_peaking_audit"]
        self.assertIs(audit["fx3_ftp_sftp_present"], False)
        self.assertIs(audit["fx3_ftp_active_mode_present"], False)
        self.assertIs(audit["fx3_ftp_transfer_jpeg_size_present"], False)
        self.assertIs(audit["fx3_in_body_focus_map_present"], False)
        self.assertIs(audit["fx3_uvc_streaming_present"], False)
        self.assertIs(audit["fx3_af_subj_shift_7_levels_present"], False)

    def test_72_round75_r75a_focusmap_120fps_allowed_while_240fps_locked(self) -> None:
        init_t = self.summary["runs"][
            "r75a_ftp_ftpes_customwb_afspeed_focusmap_marker_big6_schinese"
        ]["r75_telemetry"]["wave61_init"]
        self.assertEqual(init_t["af_focusmap_120fps_ok"], 1)
        self.assertEqual(init_t["af_focusmap_240fps_lock_rc"], -16)
        self.assertEqual(init_t["af_inbody_focusmap_rc"], -95)

    def test_73_round75_r75b_slot1_avf_erofs30_and_zero_data_writes(self) -> None:
        g = self.summary["runs"][
            "r75b_wave61_ftp_usblan_customwb_focusmap_marker_erofs_guard"
        ]["r75_telemetry"]["wave61_guard"]
        self.assertEqual(g["ftp_slot1_avf_erofs_rc"], -30)
        self.assertEqual(g["slot1_wave61_erofs_rc"], -30)
        self.assertEqual(g["slot1_avf_ro_blocked_rc"], -30)
        self.assertEqual(g["slot1_ftp_trans_stat_writes"], 0)
        self.assertEqual(g["slot1_avf_info_mutated"], 0)
        self.assertEqual(g["slot1_data_sector_writes"], 0)

    def test_74_round75_r75b_airplane_usblan_containment_zero_rf_and_wired_packets(self) -> None:
        g = self.summary["runs"][
            "r75b_wave61_ftp_usblan_customwb_focusmap_marker_erofs_guard"
        ]["r75_telemetry"]["wave61_guard"]
        self.assertEqual(g["ftp_zerorf_tx_rc"], -100)
        self.assertEqual(g["ftp_usblan_containment_rc"], -100)
        self.assertEqual(g["rf_tx_packets"], 0)
        self.assertEqual(g["usb_lan_tx_packets"], 0)
        self.assertEqual(g["wireless_tx_packets"], 0)

    def test_75_round75_r75c_shutter_awb_lock_and_8_marker_peaking_survive_reset(self) -> None:
        ci = self.summary["runs"][
            "r75c_clean_unmount_wave61_reset_h0_h3_big6_schinese"
        ]["r75_telemetry"]["clean_unmount_wave61_h0_h3"]
        self.assertEqual(ci["camreset_resets_wb_af_focusmap_preserves_shutterlock_8markerpeak_ftp_ok"], 1)
        self.assertEqual(ci["nwreset_clears_ftp9_cacert_preserves_marker8_shutterlock_airplane_ok"], 1)
        self.assertEqual(ci["initialize_clears_shutterlock_customwb_8markerpeak_preserves_airplane_ok"], 1)

    def test_76_round75_clean_unmount_checks_stock_restoration_and_zero_emmc(self) -> None:
        ci = self.summary["runs"][
            "r75c_clean_unmount_wave61_reset_h0_h3_big6_schinese"
        ]["r75_telemetry"]["clean_unmount_wave61_h0_h3"]
        self.assertEqual(ci["stock_unmount_restored_ok"], 1)
        self.assertEqual(ci["dlopen_ok"], 1)
        self.assertEqual(ci["surfaces_h0_eq_h3"], 16)
        self.assertEqual(ci["drift_bits"], 0)
        self.assertEqual(ci["emmc_write_count"], 0)
        self.assertEqual(ci["cnflasha_write_bytes"], 0)


if __name__ == "__main__":
    unittest.main()
