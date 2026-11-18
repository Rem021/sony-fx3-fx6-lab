#!/usr/bin/env python3
"""Offline four-mode unit tests for FX6-on-FX3 Round 74 (47/47 Real-HW Rounds R28..R74, 139th..141st Live Runs -> 141/141 Total, 94/94 PNGs <= 27,467 B — Wave-60)."""
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
ROUND74_REPORT_DIR = (
    REPO_ROOT
    / "reports"
    / "2026-11-18-round74-rec-media-autoswitch-proxy-cloud-mymenu42-qemu"
)
WAVE60_SPEC_PATH = (
    REPO_ROOT
    / "reports"
    / "2026-11-17-global-sony-wave60-milestone-rec-media-auto-switch-proxy-cloud-mymenu-intel"
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


def _build_overlay_for_r74(
    runner,
    parent_cpio: pathlib.Path,
    fp,
    fv,
    fb,
    fake_run,
    jit_meta: Dict[str, Any],
    work: pathlib.Path,
    r74_mode: str,
    lang: str = "schinese",
    enable_r74: bool = True,
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
            enable_r74=enable_r74,
            r74_mode=r74_mode,
            sd_manifest_mode="valid",
            lang=lang,
            shim_bytes=b"SHIM",
        )


class TestRound74RecMediaAutoswitchProxyCloudMymenu42Qemu(unittest.TestCase):
    EXPECTED_RUN_KEYS = (
        "r74a_rec_media_autoswitch_proxy_cloud_mymenu42_big6_schinese",
        "r74b_wave60_rec_media_proxy_poweroff_ble_mymenu_erofs_guard",
        "r74c_clean_unmount_wave60_reset_h0_h3_big6_schinese",
    )

    runner: Any
    runner_src: str
    stage_a_src: str
    shim_src: str
    wave60_spec: str
    summary_raw: str
    summary: Dict[str, Any]
    r74_readme: str
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
    launcher_r74: Optional[bytes]
    shim_r74: Optional[bytes]
    shim_r73: Optional[bytes]
    r73_summary: Dict[str, Any]
    r72_summary: Dict[str, Any]
    r71_summary: Dict[str, Any]
    r70_summary: Dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = _load_closure_module("fx6_brr_r74_cached", "build_and_run_round.py")
        cls.runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")
        cls.stage_a_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        cls.shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        cls.wave60_spec = WAVE60_SPEC_PATH.read_text(encoding="utf-8")
        cls.summary_raw = (ROUND74_REPORT_DIR / "summary.json").read_text(encoding="utf-8")
        cls.summary = json.loads(cls.summary_raw)
        cls.r74_readme = (ROUND74_REPORT_DIR / "README.md").read_text(encoding="utf-8")
        cls.closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")

        alpha_p = (
            ROUND74_REPORT_DIR
            / "assets"
            / "r74a-recmedia-autoswitch-proxy-cloud-mymenu42-big6-schinese-alpha.png"
        )
        comp_p = (
            ROUND74_REPORT_DIR
            / "assets"
            / "r74a-recmedia-autoswitch-proxy-cloud-mymenu42-big6-schinese-composited.png"
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
            cls.ov_a = _build_overlay_for_r74(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wa", "rec_media_autoswitch_proxy_cloud_mymenu42_big6", lang="schinese",
            )
            cls.ov_b = _build_overlay_for_r74(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wb", "wave60_rec_media_proxy_poweroff_ble_mymenu_erofs_guard", lang="en",
            )
            cls.ov_c = _build_overlay_for_r74(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wc", "clean_unmount_wave60_reset_h0_h3_big6", lang="schinese",
            )
            cls.ov_off = _build_overlay_for_r74(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "woff", "rec_media_autoswitch_proxy_cloud_mymenu42_big6", enable_r74=False,
            )
            cls.invalid_mode_raised = False
            try:
                _build_overlay_for_r74(
                    cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                    tpath / "wbad", "invalid_r74_mode",
                )
            except ValueError:
                cls.invalid_mode_raised = True

            zig_bin = shutil.which("zig") or (
                str(cls.runner.ZIG) if cls.runner.ZIG.is_file() else None
            )
            if zig_bin is not None:
                verify_r74_out = tpath / "fx6-stage-a-verify-r74"
                shim_r74_out = tpath / "libgrm-fbinit9-r74.so"
                shim_r73_out = tpath / "libgrm-fbinit9-r73.so"
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
                        str(verify_r74_out),
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
                    [
                        zig_bin,
                        "cc",
                        "-target",
                        "aarch64-linux-gnu.2.25",
                        "-O0",
                        "-shared",
                        "-fPIC",
                        "-DFX6_ROUND=73",
                        str(CLOSURE_DIR / "libgrm-fbinit9.c"),
                        "-ldl",
                        "-lpthread",
                        "-o",
                        str(shim_r73_out),
                    ],
                ):
                    cls.runner.subprocess.run(cmd, check=True)
                cls.launcher_r74 = verify_r74_out.read_bytes()
                cls.shim_r74 = shim_r74_out.read_bytes()
                cls.shim_r73 = shim_r73_out.read_bytes()
            else:
                cls.launcher_r74 = None
                cls.shim_r74 = None
                cls.shim_r73 = None

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
        cls.r70_summary = json.loads(
            (
                REPO_ROOT
                / "reports"
                / "2026-11-17-round70-milestone-dial-customize-mydial-fn12x2-liveview-lut-embed-qemu"
                / "summary.json"
            ).read_text(encoding="utf-8")
        )

    def test_01_wave60_global_spec_present_and_covers_all_wave60_pillars(self) -> None:
        self.assertTrue(WAVE60_SPEC_PATH.is_file())
        for needle in (
            "Prioritize Rec. Media",
            "Recording Media",
            "BKID_APP_setting_still_recording_media",
            "BKID_APP_setting_movie_recording_media",
            "Auto Switch Media",
            "BKID_APP_setting_relay_rec",
            "VPG200",
            "VPG400",
            "Simul Rec",
            "Proxy Settings",
            "sq_proxy",
            "XAVC HS HD",
            "XAVC S HD",
            "XAVC S-I DCI 4K",
            "M4ROOT/SUB/",
            "S03.MP4",
            "Creators' Cloud",
            "Cloud Connection",
            "Cloud Information",
            "Cnct. while Power OFF",
            "BKID_APP_extern_menu_cnct_while_power_off",
            "UIBIZ_KEY_BLUETOOTH_LOWENERGY_POWER",
            "My Menu",
            "BKID_APP_mymenu_group",
            "User Menu with Lock",
            "EROFS",
        ):
            self.assertIn(needle, self.wave60_spec)

    def test_02_round74_summary_schema_milestone_and_zero_leaks(self) -> None:
        self.assertNotIn("/Users/", self.summary_raw)
        self.assertNotIn("/private/tmp/", self.summary_raw)
        self.assertEqual(
            self.summary["schema"],
            "fx6-on-fx3-round74-rec-media-autoswitch-proxy-cloud-mymenu42-qemu-v1",
        )
        self.assertEqual(self.summary["round"], 74)
        self.assertIn("47/47 Real-HW Rounds", self.summary["milestone"])
        self.assertIn("141/141 Live Runs", self.summary["milestone"])
        self.assertIn("94/94 PNGs <= 27,467 B", self.summary["milestone"])
        self.assertEqual(self.summary["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(tuple(self.summary["runs"].keys()), self.EXPECTED_RUN_KEYS)

    def test_03_round74_cli_accepts_round74_and_all_3_r74_modes(self) -> None:
        self.assertIn(", 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74]", self.runner_src)
        for mode in (
            "rec_media_autoswitch_proxy_cloud_mymenu42_big6",
            "wave60_rec_media_proxy_poweroff_ble_mymenu_erofs_guard",
            "clean_unmount_wave60_reset_h0_h3_big6",
        ):
            self.assertIn(mode, self.runner_src)

    def test_04_round74_overlay_rejects_invalid_r74_mode(self) -> None:
        self.assertTrue(self.invalid_mode_raised)

    def test_05_round74_overlay_r74a_injects_etc_fx6_stage_r74_and_appfw_launch(self) -> None:
        replacements, additions, meta = self.ov_a
        self.assertTrue(meta["r74_enabled"])
        self.assertIn("etc/fx6_stage_r74", additions)
        self.assertIn("etc/fx6_r74_libjit.so", additions)
        r74_cfg = additions["etc/fx6_stage_r74"][0].decode("utf-8")
        self.assertIn("stage_r74=1", r74_cfg)
        self.assertIn("r74_mode=rec_media_autoswitch_proxy_cloud_mymenu42_big6", r74_cfg)
        self.assertIn("milestone_47th_realhw_141st_live_94_pngs=1", r74_cfg)
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("/usr/bin/appfw-launch", init_txt)
        self.assertNotIn("--r74-wave60-guard", init_txt)

    def test_06_round74_overlay_r74b_injects_early_guard_probe_and_poweroff(self) -> None:
        replacements, _, meta = self.ov_b
        self.assertEqual(
            meta["r74"]["r74_mode"],
            "wave60_rec_media_proxy_poweroff_ble_mymenu_erofs_guard",
        )
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("--r74-wave60-guard", init_txt)
        self.assertIn("FX6_R74_WAVE60_GUARD_RC=", init_txt)
        self.assertIn("FX6_R74_WAVE60_GUARD_EXIT", init_txt)
        self.assertIn("poweroff -f", init_txt)

    def test_07_round74_overlay_r74c_integrated_runs_stage_b_big6(self) -> None:
        replacements, additions, meta = self.ov_c
        self.assertEqual(meta["r74"]["r74_mode"], "clean_unmount_wave60_reset_h0_h3_big6")
        r74_cfg = additions["etc/fx6_stage_r74"][0].decode("utf-8")
        self.assertIn("r74_mode=clean_unmount_wave60_reset_h0_h3_big6", r74_cfg)
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("/usr/bin/appfw-launch", init_txt)
        self.assertNotIn("--r74-wave60-guard", init_txt)

    def test_08_round74_overlay_disabled_when_enable_r74_false(self) -> None:
        _, additions, meta = self.ov_off
        self.assertFalse(meta["r74_enabled"])
        self.assertNotIn("etc/fx6_stage_r74", additions)
        self.assertNotIn("etc/fx6_r74_libjit.so", additions)
        self.assertNotIn("r74", meta)

    def test_09_round74_stage_a_c_source_contains_all_3_wave60_probes(self) -> None:
        for sym in (
            "setup_r74_rec_media_autoswitch_proxy_cloud_mymenu42_probe",
            "run_r74_wave60_guard_probe",
            "run_r74_clean_unmount_wave60_h0_h3_probe",
            "r74_wave60_camera_settings_reset",
            "r74_wave60_reset_network_settings",
            "r74_wave60_initialize",
            "r74_wave60_clear_cloud_account",
            "r74_configure_rec_media_and_vpg",
            "r74_trigger_slot1_media_or_proxy_write",
            "r74_configure_proxy_settings",
            "r74_configure_cloud_and_poweroff_ble",
            "r74_configure_mymenu_42_or_fx6_lock",
            "FX6_R74_WAVE60_INIT",
            "FX6_R74_WAVE60_GUARD",
            "FX6_R74_CLEAN_UNMOUNT_WAVE60_H0_H3",
            "--r74-wave60-guard",
            "--r74-clean-unmount-wave60-h0-h3",
            "/etc/fx6_stage_r74",
        ):
            self.assertIn(sym, self.stage_a_src)

    def test_10_round74_shim_c_source_contains_r74_guarded_bridges(self) -> None:
        self.assertIn("#if FX6_ROUND >= 74", self.shim_src)
        for sym in (
            "FX6_R74_REC_MEDIA_AUTOSWITCH_VPG_BRIDGE",
            "FX6_R74_PROXY_SQ_M4ROOT_SUB_EROFS_BRIDGE",
            "FX6_R74_CLOUD_STAR_POWEROFF_BLE_ZERORF_BRIDGE",
            "FX6_R74_MYMENU42_FX6_LOCK_BRIDGE",
            "FX6_R74_LANG_TELEMETRY",
            "FX6_STAGE_B_R74_BRIDGE",
        ):
            self.assertIn(sym, self.shim_src)

    def test_11_round74_compile_launcher_and_shim_aarch64_elf_symbols(self) -> None:
        if self.launcher_r74 is None or self.shim_r74 is None:
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertEqual(self.launcher_r74[:4], b"\x7fELF")
        self.assertEqual(self.shim_r74[:4], b"\x7fELF")
        self.assertEqual(struct.unpack_from("<H", self.shim_r74, 18)[0], 183)
        self.assertIn(b"FX6_R74_REC_MEDIA_AUTOSWITCH_VPG_BRIDGE", self.shim_r74)
        self.assertIn(b"FX6_R74_PROXY_SQ_M4ROOT_SUB_EROFS_BRIDGE", self.shim_r74)
        self.assertIn(b"FX6_R74_CLOUD_STAR_POWEROFF_BLE_ZERORF_BRIDGE", self.shim_r74)
        self.assertIn(b"FX6_R74_MYMENU42_FX6_LOCK_BRIDGE", self.shim_r74)

    def test_12_round74_shim_round73_backward_compat_excludes_r74_bridges(self) -> None:
        if self.shim_r73 is None:
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertIn(b"FX6_R73_BIG6_HOME_FRAMING_DORMANT_BRIDGE", self.shim_r73)
        self.assertNotIn(b"FX6_R74_REC_MEDIA_AUTOSWITCH_VPG_BRIDGE", self.shim_r73)

    def test_13_round74_parse_log_extracts_all_10_r74_prefixes_and_rc(self) -> None:
        serial_text = (
            "\n".join(
                [
                    "Linux version 4.9.337-scel+ (sony@fx3)",
                    "FX6_R74_WAVE60_INIT fx3_wave60_nodes_ok=1 uxc_tokens_ok=1 rec_media_autoswitch_vpg_ok=1 proxy_sq_m4root_sub_ok=1 cloud_star_poweroff_ble_ok=1 mymenu42_fx6_lock_ok=1 emmc_write_count=0 r74_init_ok=1",
                    "FX6_R74_REC_MEDIA_AUTOSWITCH_VPG_BRIDGE split_rec_media_vs_dormant_prioritize_ok=1 auto_switch_slot1_spillover_vpg_gates_ok=1 rec_media_autoswitch_vpg_ok=1 dormant_prioritize_bypass_events=0 slot1_spillover_events=0 emmc_write_count=0 r74_bridge_ok=1",
                    "FX6_R74_PROXY_SQ_M4ROOT_SUB_EROFS_BRIDGE proxy_sq_dci4k_vs_120p_lockout_ok=1 proxy_m4root_sub_s03_erofs30_ok=1 proxy_sq_m4root_sub_erofs_ok=1 dormant_prm_haita_proxy_bypass_events=0 slot1_avf_info_mutated=0 slot1_data_sector_writes=0 cnflasha_writes=0 emmc_write_count=0",
                    "FX6_R74_CLOUD_STAR_POWEROFF_BLE_ZERORF_BRIDGE cloud_star_init_persistence_ok=1 poweroff_ble_zerorf_containment_ok=1 cloud_star_poweroff_ble_zerorf_ok=1 poweroff_ble_rf_tx_packets=0 rf_tx_packets=0 wireless_tx_packets=0 cnflasha_writes=0 emmc_write_count=0",
                    "FX6_R74_MYMENU42_FX6_LOCK_BRIDGE mymenu_6x7_42_slots_nvram_ok=1 fx6_20_user_menu_lock_diff_ok=1 mymenu42_fx6_lock_ok=1 dormant_mymenu_oob_bypass_events=0 cnflasha_writes=0 emmc_write_count=0",
                    "FX6_R74_LANG_TELEMETRY lang=schinese font_bank=23 str_bank=19 milestone_47th_realhw_141st_live_94_pngs=1 r74_bridge_ok=1",
                    "FX6_STAGE_B_R74_BRIDGE round=74 faithful=1 nop_count=0 milestone_47th_realhw_141st_live_94_pngs=1 emmc_write_count=0",
                    "FX6_R74_WAVE60_GUARD prioritize_dormant_rc=-95 slot1_spillover_erofs_rc=-30 proxy_slot1_s03_erofs_rc=-30 poweroff_ble_zerorf_tx_rc=-100 mymenu_group7_oob_rc=-95 mymenu_43rd_enospc_rc=-28 r74b_ok=1",
                    "FX6_R74_WAVE60_GUARD_RC=0",
                    "FX6_R74_CLEAN_UNMOUNT_WAVE60_H0_H3 stock_unmount_restored_ok=1 camreset_resets_proxy_preserves_media_ble_mymenu_cloud_ok=1 nwreset_clears_poweroff_ble_preserves_cloud_star_and_airplane_ok=1 initialize_clears_media_mymenu42_preserves_cloud_star_ok=1 explicit_cloud_unlink_clears_star_ok=1 surfaces_h0_eq_h3=16 r74c_ok=1",
                ]
            )
            + "\n"
        )
        parsed = self.runner.extract_milestones(serial_text)
        r74_t = parsed["r74_telemetry"]
        self.assertEqual(r74_t["wave60_guard_rc"], 0)
        self.assertEqual(r74_t["wave60_init"]["rec_media_autoswitch_vpg_ok"], 1)
        self.assertEqual(r74_t["rec_media_autoswitch_vpg_bridge"]["rec_media_autoswitch_vpg_ok"], 1)
        self.assertEqual(r74_t["proxy_sq_m4root_sub_erofs_bridge"]["proxy_sq_m4root_sub_erofs_ok"], 1)
        self.assertEqual(r74_t["cloud_star_poweroff_ble_zerorf_bridge"]["cloud_star_poweroff_ble_zerorf_ok"], 1)
        self.assertEqual(r74_t["mymenu42_fx6_lock_bridge"]["mymenu42_fx6_lock_ok"], 1)
        self.assertEqual(r74_t["lang_telemetry"]["lang"], "schinese")
        self.assertEqual(r74_t["lang_telemetry"]["milestone_47th_realhw_141st_live_94_pngs"], 1)
        self.assertEqual(r74_t["stage_b_bridge"]["round"], 74)
        self.assertEqual(r74_t["wave60_guard"]["r74b_ok"], 1)
        self.assertEqual(r74_t["clean_unmount_wave60_h0_h3"]["surfaces_h0_eq_h3"], 16)
        self.assertEqual(parsed["prefix_counts"]["FX6_R74_"], 9)

    def test_14_round74_parse_log_defaults_when_no_r74_lines_present(self) -> None:
        parsed = self.runner.extract_milestones("Linux version 4.9.337-scel+\n")
        self.assertIsNone(parsed["r74_telemetry"])
        self.assertEqual(parsed["prefix_counts"].get("FX6_R74_", 0), 0)

    def test_15_round74_runner_preserves_r73_prefix_and_uses_r74_stage_label(self) -> None:
        self.assertIn('if args.round >= 73:\n        tmp_prefix = "fx6-r73"', self.runner_src)
        self.assertIn('if args.round >= 74:\n        tmp_prefix = "fx6-r74"', self.runner_src)
        self.assertIn(
            "Milestone47RealHw141stLiveWave60RecMediaAutoSwitchProxyCloudPowerOffBleMyMenu42Erofs",
            self.runner_src,
        )
        self.assertIn(", 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74]", self.runner_src)

    def test_16_round74_runner_portability_and_sanitizer_helper(self) -> None:
        self.assertIn('shutil.which("zig")', self.runner_src)
        self.assertIn("FX6_SCRATCH_DIR", self.runner_src)
        self.assertIn("def sanitize_round74_summary(", self.runner_src)
        self.assertNotIn("/usr/" + "bin/python3", self.runner_src)

    def test_17_round74_summary_json_top_level_schema_and_milestone_metadata(self) -> None:
        d = self.summary
        self.assertEqual(
            d["schema"],
            "fx6-on-fx3-round74-rec-media-autoswitch-proxy-cloud-mymenu42-qemu-v1",
        )
        self.assertEqual(d["round"], 74)
        self.assertIn("47/47 Real-HW Rounds", d["milestone"])
        self.assertIn("141/141 Live Runs", d["milestone"])
        self.assertIn("94/94 PNGs <= 27,467 B", d["milestone"])
        self.assertEqual(d["date"], "2026-11-18")
        self.assertIn("4.9.337-scel+", d["kernel_version"])
        self.assertEqual(d["raw_firmware_bytes_leaked"], 0)

    def test_18_round74_summary_json_zero_host_path_and_scratch_leaks(self) -> None:
        for forbidden in (
            "/Users/",
            "/private/tmp/",
            "/var/folders/",
            "work/_scratch/",
            "work/_tests/",
            ":87" + "68",
        ):
            self.assertNotIn(forbidden, self.summary_raw)

    def test_19_round74_summary_audit_block_confirms_47_rounds_141_runs_94_pngs(self) -> None:
        audit = self.summary["r74_rec_media_autoswitch_proxy_cloud_mymenu42_audit"]
        self.assertEqual(audit["round"], 74)
        self.assertGreaterEqual(audit["realhw_rounds_count"], 47)
        self.assertGreaterEqual(audit["total_live_runs"], 141)
        self.assertGreaterEqual(audit["total_png_receipts"], 94)
        self.assertGreaterEqual(audit["milestone324_qemu_rounds"], 47)
        self.assertGreaterEqual(audit["milestone324_qemu_runs"], 141)
        self.assertGreaterEqual(audit["milestone324_png_receipts"], 94)
        self.assertEqual(audit["total_runs"], 3)
        negative_keys = {
            "fx3_prioritize_rec_media_present",
            "fx3_movie_sort_recording_present",
            "fx3_mymenu_30_or_36_slots_only",
        }
        for nk in negative_keys:
            self.assertIs(audit[nk], False, nk)
        for k, v in audit.items():
            if isinstance(v, bool) and k not in negative_keys:
                self.assertTrue(v, f"Expected audit boolean {k} to be True")

    def test_20_round74_all_3_runs_present_with_kernel_4_9_337_and_zero_crashes_writes(self) -> None:
        runs = self.summary["runs"]
        self.assertEqual(list(runs.keys()), list(self.EXPECTED_RUN_KEYS))
        for rk, rv in runs.items():
            self.assertEqual(rv["round"], 74, rk)
            self.assertIn("4.9.337-scel+", rv["kernel_version"], rk)
            self.assertEqual(rv["nop_count"], 0, rk)
            self.assertEqual(rv["crashes"], 0, rk)
            self.assertEqual(rv["emmc_write_count"], 0, rk)
            self.assertGreater(rv["wall_elapsed_sec"], 0.0, rk)

    def test_21_round74_r74a_pillar1_rec_media_split_autoswitch_vpg_vs_dormant_prioritize(self) -> None:
        init_t = self.summary["runs"][
            "r74a_rec_media_autoswitch_proxy_cloud_mymenu42_big6_schinese"
        ]["r74_telemetry"]["wave60_init"]
        self.assertEqual(init_t["fx3_wave60_nodes_ok"], 1)
        self.assertEqual(init_t["uxc_tokens_ok"], 1)
        self.assertEqual(init_t["rec_media_autoswitch_vpg_ok"], 1)
        self.assertEqual(init_t["prioritize_dormant_rc"], -95)
        self.assertEqual(init_t["movie_sort_absent_rc"], -95)
        self.assertEqual(init_t["simult_mixed_fs_rc"], -22)
        self.assertEqual(init_t["slot1_spillover_erofs_rc"], -30)
        self.assertEqual(init_t["vpg200_sdxc_sq_lock_rc"], -16)
        self.assertEqual(init_t["vpg400_proxy_lock_rc"], -16)
        self.assertEqual(init_t["cfex_b_dormant_rc"], -95)
        self.assertEqual(init_t["dormant_prioritize_bypass_events"], 0)
        self.assertEqual(init_t["slot1_spillover_events"], 0)

    def test_22_round74_r74a_pillar2_proxy_sq_dci4k_vs_120p_and_m4root_sub_erofs30(self) -> None:
        init_t = self.summary["runs"][
            "r74a_rec_media_autoswitch_proxy_cloud_mymenu42_big6_schinese"
        ]["r74_telemetry"]["wave60_init"]
        self.assertEqual(init_t["proxy_sq_m4root_sub_ok"], 1)
        self.assertEqual(init_t["proxy_120p_lock_rc"], -16)
        self.assertEqual(init_t["proxy_sq_120fps_lock_rc"], -16)
        self.assertEqual(init_t["proxy_dci4k_ok_rc"], 0)
        self.assertEqual(init_t["proxy_prm_haita_dormant_rc"], -95)
        self.assertEqual(init_t["proxy_16m_8bit_dormant_rc"], -95)
        self.assertEqual(init_t["proxy_slot1_s03_erofs_rc"], -30)
        self.assertEqual(init_t["dormant_prm_haita_proxy_bypass_events"], 0)
        self.assertEqual(init_t["slot1_avf_info_mutated"], 0)
        self.assertEqual(init_t["slot1_data_sector_writes"], 0)

    def test_23_round74_r74a_pillar3_cloud_star_poweroff_ble_zerorf_vs_fx6(self) -> None:
        init_t = self.summary["runs"][
            "r74a_rec_media_autoswitch_proxy_cloud_mymenu42_big6_schinese"
        ]["r74_telemetry"]["wave60_init"]
        self.assertEqual(init_t["cloud_star_poweroff_ble_ok"], 1)
        self.assertEqual(init_t["cloud_ftp_excl_rc"], -16)
        self.assertEqual(init_t["poweroff_ble_zerorf_tx_rc"], -100)
        self.assertEqual(init_t["fx6_bt_dormant_rc"], -95)
        self.assertEqual(init_t["poweroff_ble_rf_tx_packets"], 0)
        self.assertEqual(init_t["rf_tx_packets"], 0)
        self.assertEqual(init_t["wireless_tx_packets"], 0)

    def test_24_round74_r74a_pillar4_mymenu42_vs_fx6_user_menu_lock_and_vaults(self) -> None:
        init_t = self.summary["runs"][
            "r74a_rec_media_autoswitch_proxy_cloud_mymenu42_big6_schinese"
        ]["r74_telemetry"]["wave60_init"]
        self.assertEqual(init_t["mymenu42_fx6_lock_ok"], 1)
        self.assertEqual(init_t["mymenu_group0_rc"], -95)
        self.assertEqual(init_t["mymenu_group7_rc"], -95)
        self.assertEqual(init_t["mymenu_list7_rc"], -95)
        self.assertEqual(init_t["mymenu_43rd_full_rc"], -28)
        self.assertEqual(init_t["mymenu_playback_item_rc"], -95)
        self.assertEqual(init_t["fx6_user_menu_lock_pin_rc"], -95)
        self.assertEqual(init_t["dormant_mymenu_oob_bypass_events"], 0)
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
        self.assertEqual(init_t["r74_init_ok"], 1)

    def test_25_round74_r74a_stage_b_schinese_lang_telemetry_and_bridge(self) -> None:
        r74a_t = self.summary["runs"][
            "r74a_rec_media_autoswitch_proxy_cloud_mymenu42_big6_schinese"
        ]["r74_telemetry"]
        lt = r74a_t["lang_telemetry"]
        self.assertEqual(lt["lang"], "schinese")
        self.assertEqual(lt["bk4_lang_id"], "0x02cf019c")
        self.assertEqual(lt["bk4_lang_val"], "0x19")
        self.assertEqual(lt["lang_enum"], "0x2b45_CHINESE_SIMPLIFIED")
        self.assertEqual(lt["font_bank"], 23)
        self.assertEqual(lt["str_bank"], 19)
        self.assertEqual(lt["gpe_fb"], 0)
        self.assertEqual(lt["round74_47realhw_wave60_rec_media_autoswitch_proxy_cloud_mymenu42"], 1)
        self.assertEqual(lt["milestone_47th_realhw_141st_live_94_pngs"], 1)
        self.assertEqual(lt["dormant_prioritize_bypass_events"], 0)
        self.assertEqual(lt["dormant_prm_haita_proxy_bypass_events"], 0)
        self.assertEqual(lt["dormant_mymenu_oob_bypass_events"], 0)
        self.assertEqual(lt["slot1_spillover_events"], 0)
        self.assertEqual(lt["poweroff_ble_rf_tx_packets"], 0)
        self.assertEqual(lt["rf_tx_packets"], 0)
        self.assertEqual(lt["wireless_tx_packets"], 0)
        self.assertEqual(lt["slot1_avf_info_mutated"], 0)
        self.assertEqual(lt["slot1_data_sector_writes"], 0)
        self.assertEqual(lt["raw_firmware_bytes_leaked"], 0)

        sb = r74a_t["stage_b_bridge"]
        self.assertEqual(sb["round"], 74)
        self.assertEqual(sb["faithful"], 1)
        self.assertEqual(sb["nop_count"], 0)
        self.assertEqual(sb["rec_media_split_vs_dormant_prioritize_autoswitch_vpg"], 1)
        self.assertEqual(sb["proxy_sq_dci4k_vs_120p_m4root_sub_erofs30"], 1)
        self.assertEqual(sb["creators_cloud_star_init_persist_poweroff_ble_zerorf"], 1)
        self.assertEqual(sb["mymenu_6x7_42_slots_vs_fx6_20_user_menu_lock"], 1)
        self.assertEqual(sb["milestone_47th_realhw_141st_live_94_pngs"], 1)
        self.assertEqual(sb["poweroff_ble_rf_tx_packets"], 0)
        self.assertEqual(sb["slot1_spillover_events"], 0)

    def test_26_round74_r74a_stage_b_4_pillar_bridges_verified(self) -> None:
        r74a_t = self.summary["runs"][
            "r74a_rec_media_autoswitch_proxy_cloud_mymenu42_big6_schinese"
        ]["r74_telemetry"]
        pb1 = r74a_t["rec_media_autoswitch_vpg_bridge"]
        self.assertEqual(pb1["split_rec_media_vs_dormant_prioritize_ok"], 1)
        self.assertEqual(pb1["auto_switch_slot1_spillover_vpg_gates_ok"], 1)
        self.assertEqual(pb1["rec_media_autoswitch_vpg_ok"], 1)
        self.assertEqual(pb1["dormant_prioritize_bypass_events"], 0)
        self.assertEqual(pb1["slot1_spillover_events"], 0)
        self.assertEqual(pb1["r74_bridge_ok"], 1)

        pb2 = r74a_t["proxy_sq_m4root_sub_erofs_bridge"]
        self.assertEqual(pb2["proxy_sq_dci4k_vs_120p_lockout_ok"], 1)
        self.assertEqual(pb2["proxy_m4root_sub_s03_erofs30_ok"], 1)
        self.assertEqual(pb2["proxy_sq_m4root_sub_erofs_ok"], 1)
        self.assertEqual(pb2["dormant_prm_haita_proxy_bypass_events"], 0)
        self.assertEqual(pb2["slot1_avf_info_mutated"], 0)
        self.assertEqual(pb2["slot1_data_sector_writes"], 0)

        pb3 = r74a_t["cloud_star_poweroff_ble_zerorf_bridge"]
        self.assertEqual(pb3["cloud_star_init_persistence_ok"], 1)
        self.assertEqual(pb3["poweroff_ble_zerorf_containment_ok"], 1)
        self.assertEqual(pb3["cloud_star_poweroff_ble_zerorf_ok"], 1)
        self.assertEqual(pb3["poweroff_ble_rf_tx_packets"], 0)
        self.assertEqual(pb3["rf_tx_packets"], 0)

        pb4 = r74a_t["mymenu42_fx6_lock_bridge"]
        self.assertEqual(pb4["mymenu_6x7_42_slots_nvram_ok"], 1)
        self.assertEqual(pb4["fx6_20_user_menu_lock_diff_ok"], 1)
        self.assertEqual(pb4["mymenu42_fx6_lock_ok"], 1)
        self.assertEqual(pb4["dormant_mymenu_oob_bypass_events"], 0)

    def test_27_round74_r74a_realhw_mechanisms_verified_block_populated(self) -> None:
        rmv = self.summary["realhw_mechanisms_verified"]
        for key in (
            "wave60_rec_media_autoswitch_proxy_cloud_mymenu42_init",
            "rec_media_autoswitch_vpg_stage_b_bridge",
            "proxy_sq_m4root_sub_erofs_stage_b_bridge",
            "cloud_star_poweroff_ble_zerorf_stage_b_bridge",
            "mymenu42_fx6_lock_stage_b_bridge",
            "wave60_fail_closed_guard",
            "clean_unmount_wave60_reset_and_16_h0_h3",
        ):
            self.assertIn(key, rmv)
            self.assertTrue(bool(rmv[key]), key)

    def test_28_round74_r74b_guard_blocks_prioritize_movie_sort_and_spillover_erofs30(self) -> None:
        g = self.summary["runs"][
            "r74b_wave60_rec_media_proxy_poweroff_ble_mymenu_erofs_guard"
        ]["r74_telemetry"]["wave60_guard"]
        self.assertEqual(g["prioritize_dormant_rc"], -95)
        self.assertEqual(g["movie_sort_absent_rc"], -95)
        self.assertEqual(g["simult_exfat_fat32_mix_rc"], -22)
        self.assertEqual(g["slot1_spillover_erofs_rc"], -30)
        self.assertEqual(g["simult_erofs_rc"], -30)
        self.assertEqual(g["sq_1200m_sdxc_vpg_rc"], -16)
        self.assertEqual(g["proxy_600m_vpg400_lock_rc"], -16)
        self.assertEqual(g["cfex_b_dormant_rc"], -95)

    def test_29_round74_r74b_guard_blocks_proxy_120p_dormant_enums_and_s03_erofs30(self) -> None:
        g = self.summary["runs"][
            "r74b_wave60_rec_media_proxy_poweroff_ble_mymenu_erofs_guard"
        ]["r74_telemetry"]["wave60_guard"]
        self.assertEqual(g["proxy_120p_lock_rc"], -16)
        self.assertEqual(g["proxy_sq_120fps_lock_rc"], -16)
        self.assertEqual(g["proxy_16m_8bit_dormant_rc"], -95)
        self.assertEqual(g["proxy_9m_8bit_dormant_rc"], -95)
        self.assertEqual(g["proxy_prm_haita_dormant_rc"], -95)
        self.assertEqual(g["proxy_playback_in_cam_rc"], -95)
        self.assertEqual(g["proxy_slot1_s03_erofs_rc"], -30)
        self.assertEqual(g["proxy_slot1_coupled_del_erofs_rc"], -30)
        self.assertEqual(g["fx6_simul_proxy_excl_rc"], -16)

    def test_30_round74_r74b_guard_blocks_cloud_ftp_poweroff_ble_zerorf_and_fx6_bt(self) -> None:
        g = self.summary["runs"][
            "r74b_wave60_rec_media_proxy_poweroff_ble_mymenu_erofs_guard"
        ]["r74_telemetry"]["wave60_guard"]
        self.assertEqual(g["cloud_ftp_excl_rc"], -16)
        self.assertEqual(g["poweroff_ble_zerorf_tx_rc"], -100)
        self.assertEqual(g["poweroff_ble_containment_tx_rc"], -100)
        self.assertEqual(g["fx6_bt_dormant_rc"], -95)
        self.assertEqual(g["poweroff_ble_rf_tx_packets"], 0)
        self.assertEqual(g["rf_tx_packets"], 0)
        self.assertEqual(g["wireless_tx_packets"], 0)

    def test_31_round74_r74b_guard_blocks_mymenu_oob_43rd_enospc_playback_and_fx6_lock(self) -> None:
        g = self.summary["runs"][
            "r74b_wave60_rec_media_proxy_poweroff_ble_mymenu_erofs_guard"
        ]["r74_telemetry"]["wave60_guard"]
        self.assertEqual(g["mymenu_group0_oob_rc"], -95)
        self.assertEqual(g["mymenu_group7_oob_rc"], -95)
        self.assertEqual(g["mymenu_list7_oob_rc"], -95)
        self.assertEqual(g["mymenu_43rd_enospc_rc"], -28)
        self.assertEqual(g["mymenu_playback_disallowed_rc"], -95)
        self.assertEqual(g["fx6_user_menu_lock_pin_rc"], -95)
        self.assertEqual(g["fx6_user_menu_21st_enospc_rc"], -28)

    def test_32_round74_r74b_guard_blocks_slot1_avf_p12_p2_cnflasha_and_keeps_sha256(self) -> None:
        r74b_t = self.summary["runs"][
            "r74b_wave60_rec_media_proxy_poweroff_ble_mymenu_erofs_guard"
        ]["r74_telemetry"]
        g = r74b_t["wave60_guard"]
        self.assertEqual(r74b_t["wave60_guard_rc"], 0)
        self.assertEqual(g["slot1_wave60_erofs_rc"], -30)
        self.assertEqual(g["slot1_avf_ro_blocked_rc"], -30)
        self.assertEqual(g["p12_write_blocked_rc"], -30)
        self.assertEqual(g["p2_write_blocked_rc"], -30)
        self.assertEqual(g["cnflasha_ro_blocked_rc"], -30)
        self.assertEqual(g["slot1_vault_sha256_match"], 1)
        self.assertEqual(g["slot1_spillover_events"], 0)
        self.assertEqual(g["slot1_avf_info_mutated"], 0)
        self.assertEqual(g["slot1_data_sector_writes"], 0)
        self.assertEqual(g["dormant_prioritize_bypass_events"], 0)
        self.assertEqual(g["dormant_prm_haita_proxy_bypass_events"], 0)
        self.assertEqual(g["dormant_mymenu_oob_bypass_events"], 0)
        self.assertEqual(g["passive_tx_bytes_emitted"], 0)
        self.assertEqual(g["e_nd_actuator_tx_count"], 0)
        self.assertEqual(g["appfw_ok"], 1)
        self.assertEqual(g["shim_elf_ok"], 1)
        self.assertEqual(g["cnflasha_writes"], 0)
        self.assertEqual(g["emmc_write_count"], 0)
        self.assertEqual(g["r74b_ok"], 1)

    def test_33_round74_r74c_clean_unmount_and_3tier_persistence_with_cloud_star(self) -> None:
        ci = self.summary["runs"][
            "r74c_clean_unmount_wave60_reset_h0_h3_big6_schinese"
        ]["r74_telemetry"]["clean_unmount_wave60_h0_h3"]
        self.assertEqual(ci["stock_unmount_restored_ok"], 1)
        self.assertEqual(ci["camreset_resets_proxy_preserves_media_ble_mymenu_cloud_ok"], 1)
        self.assertEqual(ci["nwreset_clears_poweroff_ble_preserves_cloud_star_and_airplane_ok"], 1)
        self.assertEqual(ci["initialize_clears_media_mymenu42_preserves_cloud_star_ok"], 1)
        self.assertEqual(ci["explicit_cloud_unlink_clears_star_ok"], 1)
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
        self.assertEqual(ci["r74c_ok"], 1)

    def test_34_round74_r74a_and_r74c_gpe0_readback_big6_home_ge_300k_nonzero_pixels(self) -> None:
        for rk in (
            "r74a_rec_media_autoswitch_proxy_cloud_mymenu42_big6_schinese",
            "r74c_clean_unmount_wave60_reset_h0_h3_big6_schinese",
        ):
            gpe = self.summary["runs"][rk]["gpe0_readback"]
            self.assertTrue(gpe["present"], rk)
            self.assertEqual(gpe["total_pixels"], 1024 * 540, rk)
            self.assertEqual(gpe["bytes"], 1024 * 540 * 4, rk)
            self.assertGreaterEqual(gpe["nonzero_pixels"], 300000, rk)
            self.assertGreaterEqual(gpe["unique_colors"], 50, rk)

    def test_35_round74_r74a_alpha_and_composited_png_dimensions_and_size_cap_27467(self) -> None:
        self.assertEqual(self.alpha_dims, (1024, 540))
        self.assertEqual(self.comp_dims, (1024, 540))
        self.assertLessEqual(len(self.alpha_png_bytes), 27467)
        self.assertLessEqual(len(self.comp_png_bytes), 27467)
        self.assertGreater(self.alpha_transparent, 100000)
        self.assertGreater(self.alpha_opaque, 100000)
        self.assertEqual(self.comp_opaque, 1024 * 540)

    def test_36_round74_r74a_png_exports_paths_sanitized_and_match_assets(self) -> None:
        pe = self.summary["runs"][
            "r74a_rec_media_autoswitch_proxy_cloud_mymenu42_big6_schinese"
        ]["png_exports"]
        self.assertEqual(
            pe["alpha_png"]["path"],
            "reports/2026-11-18-round74-rec-media-autoswitch-proxy-cloud-mymenu42-qemu/assets/r74a-recmedia-autoswitch-proxy-cloud-mymenu42-big6-schinese-alpha.png",
        )
        self.assertEqual(
            pe["composited_png"]["path"],
            "reports/2026-11-18-round74-rec-media-autoswitch-proxy-cloud-mymenu42-qemu/assets/r74a-recmedia-autoswitch-proxy-cloud-mymenu42-big6-schinese-composited.png",
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

    def test_37_round74_r74a_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"][
            "r74a_rec_media_autoswitch_proxy_cloud_mymenu42_big6_schinese"
        ]["r74_telemetry"]["wave60_init"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_38_round74_r74b_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"][
            "r74b_wave60_rec_media_proxy_poweroff_ble_mymenu_erofs_guard"
        ]["r74_telemetry"]["wave60_guard"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_39_round74_r74c_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"][
            "r74c_clean_unmount_wave60_reset_h0_h3_big6_schinese"
        ]["r74_telemetry"]["clean_unmount_wave60_h0_h3"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_40_round74_r74a_top_colors_transparent_plus_nonzero_equals_total_pixels(self) -> None:
        gpe = self.summary["runs"][
            "r74a_rec_media_autoswitch_proxy_cloud_mymenu42_big6_schinese"
        ]["gpe0_readback"]
        color_map = {row["argb"]: row["pixels"] for row in gpe["top_colors"]}
        self.assertIn("0x00000000", color_map)
        self.assertIn("0xff000000", color_map)
        self.assertEqual(color_map["0x00000000"] + gpe["nonzero_pixels"], gpe["total_pixels"])

    def test_41_round74_r74c_top_colors_transparent_plus_nonzero_equals_total_pixels(self) -> None:
        gpe = self.summary["runs"][
            "r74c_clean_unmount_wave60_reset_h0_h3_big6_schinese"
        ]["gpe0_readback"]
        color_map = {row["argb"]: row["pixels"] for row in gpe["top_colors"]}
        self.assertIn("0x00000000", color_map)
        self.assertEqual(color_map["0x00000000"] + gpe["nonzero_pixels"], gpe["total_pixels"])

    def test_42_round74_r74a_and_r74c_wall_elapsed_and_duration_budget_sanity(self) -> None:
        r74a = self.summary["runs"][
            "r74a_rec_media_autoswitch_proxy_cloud_mymenu42_big6_schinese"
        ]
        r74c = self.summary["runs"][
            "r74c_clean_unmount_wave60_reset_h0_h3_big6_schinese"
        ]
        ci_headroom = 15.0 if os.environ.get("GITHUB_ACTIONS") == "true" else 0.0
        max_wall = 240.0 + ci_headroom if os.environ.get("GITHUB_ACTIONS") == "true" else 120.0 + ci_headroom
        self.assertGreaterEqual(r74a["duration_budget_sec"], 70)
        self.assertLessEqual(r74a["duration_budget_sec"], 120)
        self.assertGreater(r74a["wall_elapsed_sec"], 50.0)
        self.assertLess(r74a["wall_elapsed_sec"], max_wall)
        self.assertGreaterEqual(r74c["duration_budget_sec"], 70)
        self.assertLessEqual(r74c["duration_budget_sec"], 120)
        self.assertGreater(r74c["wall_elapsed_sec"], 50.0)
        self.assertLess(r74c["wall_elapsed_sec"], max_wall)

    def test_43_round74_r74b_fast_early_exit_wall_elapsed_with_ci_headroom(self) -> None:
        r74b = self.summary["runs"][
            "r74b_wave60_rec_media_proxy_poweroff_ble_mymenu_erofs_guard"
        ]
        ci_headroom = 15.0 if os.environ.get("GITHUB_ACTIONS") == "true" else 0.0
        max_b = 45.0 + ci_headroom if os.environ.get("GITHUB_ACTIONS") == "true" else 20.0 + ci_headroom
        self.assertEqual(r74b["duration_budget_sec"], 35)
        self.assertGreater(r74b["wall_elapsed_sec"], 1.0)
        self.assertLess(r74b["wall_elapsed_sec"], max_b)
        self.assertTrue(r74b["gpe0_readback"]["skipped_stock_fx3_mode"])

    def test_44_round74_faithful_invariants_preserved_across_all_3_runs(self) -> None:
        for rk, rv in self.summary["runs"].items():
            fi = rv["faithful_invariants"]
            self.assertEqual(fi["FX6_NATIVE_FAITHFUL"], 1, rk)
            self.assertEqual(fi["subst_color"], 0, rk)
            self.assertEqual(fi["subst_image"], 0, rk)
            self.assertEqual(fi["forced_render"], 0, rk)
            self.assertEqual(fi["skipped_node"], 0, rk)
            self.assertEqual(fi["lock_bypass"], 0, rk)

    def test_45_round74_all_3_runs_stage_b_manifest_count_13(self) -> None:
        for rk, rv in self.summary["runs"].items():
            self.assertEqual(rv["stage_b"]["manifest_count"], 13, rk)
            self.assertEqual(len(rv["stage_b"]["manifest_items"]), 13, rk)

    def test_46_round74_r74c_stage_b_r74_bridges_and_zero_leak_verified(self) -> None:
        r74c_t = self.summary["runs"][
            "r74c_clean_unmount_wave60_reset_h0_h3_big6_schinese"
        ]["r74_telemetry"]
        self.assertEqual(r74c_t["rec_media_autoswitch_vpg_bridge"]["rec_media_autoswitch_vpg_ok"], 1)
        self.assertEqual(r74c_t["proxy_sq_m4root_sub_erofs_bridge"]["proxy_sq_m4root_sub_erofs_ok"], 1)
        self.assertEqual(r74c_t["cloud_star_poweroff_ble_zerorf_bridge"]["cloud_star_poweroff_ble_zerorf_ok"], 1)
        self.assertEqual(r74c_t["mymenu42_fx6_lock_bridge"]["mymenu42_fx6_lock_ok"], 1)
        self.assertEqual(r74c_t["rec_media_autoswitch_vpg_bridge"]["dormant_prioritize_bypass_events"], 0)
        self.assertEqual(r74c_t["rec_media_autoswitch_vpg_bridge"]["slot1_spillover_events"], 0)
        self.assertEqual(r74c_t["proxy_sq_m4root_sub_erofs_bridge"]["slot1_avf_info_mutated"], 0)
        self.assertEqual(r74c_t["proxy_sq_m4root_sub_erofs_bridge"]["slot1_data_sector_writes"], 0)
        self.assertEqual(r74c_t["cloud_star_poweroff_ble_zerorf_bridge"]["poweroff_ble_rf_tx_packets"], 0)
        self.assertEqual(r74c_t["cloud_star_poweroff_ble_zerorf_bridge"]["rf_tx_packets"], 0)
        self.assertEqual(r74c_t["mymenu42_fx6_lock_bridge"]["dormant_mymenu_oob_bypass_events"], 0)
        self.assertEqual(r74c_t["stage_b_bridge"]["e_nd_actuator_tx_count"], 0)

    def test_47_round74_all_3_runs_prefix_counts_include_fx6_r74(self) -> None:
        r74a_pc = self.summary["runs"][
            "r74a_rec_media_autoswitch_proxy_cloud_mymenu42_big6_schinese"
        ]["prefix_counts"]
        r74b_pc = self.summary["runs"][
            "r74b_wave60_rec_media_proxy_poweroff_ble_mymenu_erofs_guard"
        ]["prefix_counts"]
        r74c_pc = self.summary["runs"][
            "r74c_clean_unmount_wave60_reset_h0_h3_big6_schinese"
        ]["prefix_counts"]
        self.assertGreater(r74a_pc["FX6_R74_"], 10)
        self.assertEqual(r74b_pc["FX6_R74_"], 3)
        self.assertGreater(r74c_pc["FX6_R74_"], 10)

    def test_48_round74_r74_meta_invariants_across_all_3_runs(self) -> None:
        for rk, rv in self.summary["runs"].items():
            m = rv["stage_b"]["r74"]
            self.assertEqual(m["milestone_round_ordinal"], 74, rk)
            self.assertEqual(m["realhw_round_ordinal"], 47, rk)
            self.assertEqual(m["total_live_runs_at_completion"], 141, rk)
            self.assertEqual(m["total_png_receipts_at_completion"], 94, rk)
            self.assertEqual(m["dormant_prioritize_bypass_events"], 0, rk)
            self.assertEqual(m["dormant_prm_haita_proxy_bypass_events"], 0, rk)
            self.assertEqual(m["dormant_mymenu_oob_bypass_events"], 0, rk)
            self.assertEqual(m["slot1_spillover_events"], 0, rk)
            self.assertEqual(m["poweroff_ble_rf_tx_packets"], 0, rk)
            self.assertEqual(m["rf_tx_packets"], 0, rk)
            self.assertEqual(m["wireless_tx_packets"], 0, rk)
            self.assertEqual(m["slot1_data_sector_writes"], 0, rk)
            self.assertFalse(m["slot1_avf_info_mutated"], rk)
            self.assertEqual(m["passive_tx_bytes_emitted"], 0, rk)
            self.assertEqual(m["e_nd_actuator_tx_count"], 0, rk)
            self.assertEqual(m["raw_firmware_bytes_leaked"], 0, rk)
            self.assertEqual(m["cnflasha_writes"], 0, rk)
            self.assertEqual(m["emmc_write_count"], 0, rk)
            self.assertEqual(m["p2_setting_writes"], 0, rk)

    def test_49_round74_sanitize_helper_redacts_host_paths_and_reserved_port(self) -> None:
        dirty = {
            "run_id": "test-run",
            "lang": "schinese",
            "r74_mode": "rec_media_autoswitch_proxy_cloud_mymenu42_big6",
            "kernel_version": "Linux version 4.9.337-scel+",
            "kernel_bin": "/Users/fake/secret/kernel.bin",
            "dtb_bin": "/Users/fake/secret/guest.dtb",
            "build": {"tmp_build": "/private/tmp/build-123"},
            "stage_b": {"r74": {"r74_mode": "rec_media_autoswitch_proxy_cloud_mymenu42_big6"}},
            "r74_telemetry": {
                "wave60_init": {"r74_init_ok": 1},
                "wave60_guard": {"r74b_ok": 1},
                "clean_unmount_wave60_h0_h3": {"r74c_ok": 1, "surfaces_h0_eq_h3": 16},
            },
            "gpe0_readback": {"nonzero_pixels": 346686},
            "png_exports": {
                "alpha_png": {
                    "path": "/Users/kafu/repo/reports/2026-11-18-round74-rec-media-autoswitch-proxy-cloud-mymenu42-qemu/assets/a.png"
                }
            },
            "prefix_counts": {"FX6_R74_": 10},
        }
        sanitized = self.runner.sanitize_round74_summary(dirty, dirty, dirty)
        raw = json.dumps(sanitized)
        self.assertNotIn("/Users/", raw)
        self.assertNotIn("/private/tmp/", raw)
        self.assertNotIn("kernel_bin", raw)
        self.assertNotIn("dtb_bin", raw)
        self.assertIn(
            "reports/2026-11-18-round74-rec-media-autoswitch-proxy-cloud-mymenu42-qemu/assets/a.png",
            raw,
        )

    def test_50_round74_no_stray_temp_files_or_reserved_port_in_repo(self) -> None:
        for bad_name in ("tmp", "scratch", ".worktrees"):
            self.assertFalse((REPO_ROOT / bad_name).exists(), bad_name)
        reserved_port = "87" + "68"
        self.assertNotIn(reserved_port, self.summary_raw)
        self.assertNotIn(reserved_port, self.r74_readme)

    def test_51_round74_test_suite_contains_at_least_76_unit_tests(self) -> None:
        methods = [m for m in dir(self) if m.startswith("test_")]
        self.assertGreaterEqual(len(methods), 76)

    def test_52_round74_three_clean_env_modes_preserve_parity(self) -> None:
        for env_overrides in (
            {},
            {"FX3_CLEAN_ROOM_TEST": "1"},
            {"FX3_FX6_FORCE_CLEAN_ROOM": "1"},
        ):
            with mock.patch.dict(os.environ, env_overrides, clear=False):
                parsed = self.runner.extract_milestones(
                    "Linux version 4.9.337-scel+\n"
                    "FX6_R74_WAVE60_INIT rec_media_autoswitch_vpg_ok=1 proxy_sq_m4root_sub_ok=1 "
                    "cloud_star_poweroff_ble_ok=1 mymenu42_fx6_lock_ok=1 r74_init_ok=1\n"
                )
                self.assertEqual(parsed["r74_telemetry"]["wave60_init"]["r74_init_ok"], 1)

    def test_53_round74_mocked_donorless_work_root_none_fallback_and_master_gate(self) -> None:
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
                self.assertGreaterEqual(report.qemu_rounds_verified, 47)
                self.assertGreaterEqual(report.qemu_runs_verified, 141)
                self.assertGreaterEqual(report.qemu_png_receipts_verified, 94)
        finally:
            for p in added:
                if p in sys.path:
                    sys.path.remove(p)

    def test_54_round74_argparse_percent_safe_help_and_no_hardcoded_python3(self) -> None:
        for line in self.runner_src.splitlines():
            if "help=" in line and "%" in line:
                stripped = line.replace("%%", "")
                self.assertNotIn("%", stripped, f"Unescaped '%' in argparse help: {line}")
        test_src = pathlib.Path(__file__).read_text(encoding="utf-8")
        forbidden_py = "/usr/" + "bin/python3"
        self.assertNotIn(forbidden_py, self.runner_src)
        self.assertNotIn(forbidden_py, test_src)

    def test_55_round74_all_94_milestone_pngs_under_27467b_and_clean_room_safe(self) -> None:
        assets_pngs = sorted(
            p for p in (REPO_ROOT / "reports").glob("2026-??-??-round*/assets/*.png")
            if int(p.parts[-3].split("-round")[1].split("-")[0]) >= 28
        )
        self.assertGreaterEqual(len(assets_pngs), 94)
        for p in assets_pngs:
            self.assertLessEqual(p.stat().st_size, 27467, str(p))

    def test_56_round74_cli_help_subprocess_smoke(self) -> None:
        res = subprocess.run(
            [sys.executable, "-B", str(CLOSURE_DIR / "build_and_run_round.py"), "--help"],
            capture_output=True,
            text=True,
            check=True,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        self.assertIn("--r74-mode", res.stdout)
        self.assertIn("rec_media_autoswitch_proxy_cloud_mymenu42_big6", res.stdout)

    def test_57_round74_pillar1_rec_media_split_autoswitch_vpg200_vpg400_and_fx6_simul_diff(self) -> None:
        r74a_meta = self.summary["runs"][
            "r74a_rec_media_autoswitch_proxy_cloud_mymenu42_big6_schinese"
        ]["stage_b"]["r74"]
        rm = r74a_meta["rec_media_autoswitch_and_vpg_wave60"]
        self.assertIn("_f 0x719e Prioritize Rec. Media", rm["dormant_prioritize_rec_media"])
        self.assertIn("0 hits prioritize", rm["dormant_prioritize_rec_media"])
        self.assertIn("BKID_APP_setting_still_recording_media", rm["still_recording_media"])
        self.assertIn("Sort Recording", rm["still_recording_media"])
        self.assertIn("BKID_APP_setting_movie_recording_media", rm["movie_recording_media"])
        self.assertIn("ZERO Movie Sort Recording", rm["movie_recording_media"])
        self.assertIn("BKID_APP_setting_relay_rec", rm["auto_switch_media"])
        self.assertIn("EROFS=30", rm["auto_switch_media"])
        self.assertIn("base 0xe228 (CFexpress VPG200)", rm["card_speed_gates"])
        self.assertIn("CFexpress VPG400", rm["card_speed_gates"])
        self.assertIn("BKID_APP_SETTING_SIMUL_REC", rm["fx6_diff"])

    def test_58_round74_pillar2_proxy_sq_proxy_dci4k_vs_120p_and_m4root_sub_s03(self) -> None:
        r74a_meta = self.summary["runs"][
            "r74a_rec_media_autoswitch_proxy_cloud_mymenu42_big6_schinese"
        ]["stage_b"]["r74"]
        px = r74a_meta["proxy_settings_sq_proxy_and_m4root_sub"]
        self.assertIn("BKID_APP_setting_sq_proxy", px["elf_prefix_truth"])
        self.assertIn("0 hits PRM_HAITA_*proxy*", px["elf_prefix_truth"])
        self.assertIn("XAVC S HD (def", px["formats_and_defaults"])
        self.assertIn("XAVC HS HD", px["formats_and_defaults"])
        self.assertIn("XAVC S-I DCI 4K (max 59.94p/50p) IS ALLOWED", px["exact_lockout_vs_dci4k"])
        self.assertIn("119.88p/100p", px["exact_lockout_vs_dci4k"])
        self.assertIn("/M4ROOT/SUB/<Clip>S03.MP4", px["file_layout_and_erofs"])
        self.assertIn("EROFS=30", px["file_layout_and_erofs"])
        self.assertIn("Slot B", px["fx6_diff"])

    def test_59_round74_pillar3_creators_cloud_star_and_poweroff_ble_zerorf_vs_fx6(self) -> None:
        r74a_meta = self.summary["runs"][
            "r74a_rec_media_autoswitch_proxy_cloud_mymenu42_big6_schinese"
        ]["stage_b"]["r74"]
        cl = r74a_meta["creators_cloud_star_and_poweroff_ble_hazard"]
        self.assertIn("BKID_APP_setting_cloud_connection", cl["cloud_suite"])
        self.assertIn("SURVIVE", cl["star_initialize_persistence"])
        self.assertIn("EVEN [Initialize]", cl["star_initialize_persistence"])
        self.assertIn("BKID_APP_extern_menu_cnct_while_power_off", cl["cnct_while_power_off_ble_hazard"])
        self.assertIn("UIBIZ_KEY_BLUETOOTH_LOWENERGY_POWER", cl["cnct_while_power_off_ble_hazard"])
        self.assertIn("Airplane Mode=On", cl["cnct_while_power_off_ble_hazard"])
        self.assertIn("NO Bluetooth hardware", cl["fx6_diff"])

    def test_60_round74_pillar4_mymenu_6x7_42_nvram_slots_vs_fx6_20_item_user_menu_lock(self) -> None:
        r74a_meta = self.summary["runs"][
            "r74a_rec_media_autoswitch_proxy_cloud_mymenu42_big6_schinese"
        ]["stage_b"]["r74"]
        mm = r74a_meta["mymenu_42_slots_vs_fx6_user_menu_lock"]
        self.assertIn("6x7=42 NVRAM slots", mm["exact_capacity"])
        self.assertIn("0 hits group0/group7/list7", mm["exact_capacity"])
        self.assertIn("NOT 30 or 36", mm["exact_capacity"])
        self.assertIn("Add Item (_f 0x7122)", mm["six_ops_and_exclusions"])
        self.assertIn("Playback items disallowed", mm["six_ops_and_exclusions"])
        self.assertIn("FX6 20-item [User Menu]", mm["fx6_diff"])
        self.assertIn("User Menu with Lock", mm["fx6_diff"])

    def test_61_round74_3tier_persistence_and_cloud_star_matrix_across_c_summary_and_readmes(self) -> None:
        r74a_meta = self.summary["runs"][
            "r74a_rec_media_autoswitch_proxy_cloud_mymenu42_big6_schinese"
        ]["stage_b"]["r74"]
        rt = r74a_meta["reset_tiers"]
        self.assertIn("[Proxy Settings]", rt["camera_settings_reset"])
        self.assertIn("[Auto Switch Media]", rt["camera_settings_reset"])
        self.assertIn("[Cnct. while Power OFF]", rt["reset_network_settings"])
        self.assertIn("SURVIVE EVEN [Initialize]", rt["initialize"])
        for fn in (
            "r74_wave60_camera_settings_reset",
            "r74_wave60_reset_network_settings",
            "r74_wave60_initialize",
            "r74_wave60_clear_cloud_account",
        ):
            self.assertIn(fn, self.stage_a_src)
        self.assertIn("Reset Network Set.", self.r74_readme)
        self.assertIn("Reset Network Set.", self.closure_readme)

    def test_62_round74_wave60_uxc_and_node_tokens_wired_in_stage_a_source(self) -> None:
        for sym in (
            "r74_lookup_wave60_menu_node",
            "r74_lookup_uxc_token",
            "_f:0x749d:Rec. Media Settings",
            "_f:0x78be:Recording Media",
            "_f:0x7505:Simult. Recording",
            "_f:0x7916:Sort Recording",
            "_f:0x6dd9:Auto Switch Media",
            "base:0xe228:CFexpress VPG200",
            "base:0xe224:CFexpress VPG400",
            "_f:0x6e3f:Proxy Settings",
            "_f:0x7aff:Proxy Recording",
            "_f:0x764c:6M 4:2:0 8bit",
            "_f:0x611c:9M 4:2:0 10bit",
            "_f:0x62a6:16M 4:2:0 10bit",
            "_f:0x6ab3:Cnct. while Power OFF",
            "_f:0x6833:Always Connected",
            "_f:0x7122:Add Item",
            "_f:0x7a11:Sort Item",
            "_f:0x698d:Delete Item",
            "_f:0x6b7c:Delete Page",
            "_f:0x6226:Delete All",
            "_f:0x64f6:Display From My Menu",
            "BKID_APP_setting_relay_rec",
            "BKID_APP_setting_sq_proxy_recording",
            "BKID_APP_setting_sq_proxy_file_format",
            "BKID_APP_setting_sq_proxy_record_setting",
            "BKID_APP_extern_menu_cnct_while_power_off",
            "BKID_APP_SETTING_BLUETOOTH_FUNCTION",
            "_f:0x719e:Prioritize Rec. Media (dormant)",
            "_f:0x710d:Sort(RAW/JPEG) (dormant)",
            "_f:0x765b:Sort(JPEG/RAW) (dormant)",
            "_f:0x6b8f:16M 4:2:0 8bit (dormant)",
            "dormant:PRM_HAITA_*proxy*",
            "dormant:BKID_APP_mymenu_group0",
            "dormant:BKID_APP_mymenu_group7",
            "dormant:BKID_APP_mymenu_list7",
        ):
            self.assertIn(sym, self.stage_a_src)

    def test_63_round74_report_markdown_has_chinese_conclusions_and_fact_inference_split(self) -> None:
        self.assertIn("## 结论先行", self.r74_readme)
        self.assertIn("实测事实", self.r74_readme)
        self.assertIn("推断", self.r74_readme)
        self.assertIn("47/47", self.r74_readme)
        self.assertIn("141/141", self.r74_readme)
        self.assertIn("94/94", self.r74_readme)
        self.assertIn("unexecuted_physical_camera_bench_boundaries", self.summary)
        self.assertEqual(len(self.summary["unexecuted_physical_camera_bench_boundaries"]), 3)

    def test_64_round74_closure_readme_documents_round74_section(self) -> None:
        self.assertIn("## 74. Round 74", self.closure_readme)
        self.assertIn("141/141", self.closure_readme)
        self.assertIn("94/94", self.closure_readme)
        self.assertIn("BKID_APP_mymenu_group", self.closure_readme)

    def test_65_round74_round73_baseline_non_regression_preserved(self) -> None:
        self.assertEqual(self.r73_summary["round"], 73)
        self.assertEqual(self.r73_summary["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(
            self.r73_summary["r73_big6_framing_interval_tc_ssh_fan_erofs_audit"]["realhw_rounds_count"],
            46,
        )

    def test_66_round74_round72_baseline_non_regression_preserved(self) -> None:
        self.assertEqual(self.r72_summary["round"], 72)
        self.assertEqual(self.r72_summary["raw_firmware_bytes_leaked"], 0)

    def test_67_round74_round71_baseline_non_regression_preserved(self) -> None:
        self.assertEqual(self.r71_summary["round"], 71)
        self.assertEqual(self.r71_summary["raw_firmware_bytes_leaked"], 0)

    def test_68_round74_round70_baseline_non_regression_preserved(self) -> None:
        self.assertEqual(self.r70_summary["round"], 70)
        self.assertEqual(self.r70_summary["raw_firmware_bytes_leaked"], 0)

    def test_69_round74_vpg200_vpg400_uxc_and_codec_gates_in_stage_a(self) -> None:
        for tok in (
            "R74_CARD_CFEX_A_VPG400",
            "R74_CARD_CFEX_A_VPG200",
            "R74_CARD_CFEX_B_DORMANT",
            "R74_CODEC_SQ_XAVC_SI_4K_1200M",
            "R74_CODEC_XAVC_SI_DCI4K_600M",
            "R74_MEDIA_SORT_RAW_SLOT1_JPEG_SLOT2",
        ):
            self.assertIn(tok, self.stage_a_src)

    def test_70_round74_overlay_meta_modes_and_reset_flags_consistent(self) -> None:
        _, _, ma = self.ov_a
        _, _, mb = self.ov_b
        _, _, mc = self.ov_c
        self.assertEqual(ma["r74"]["r74_mode"], "rec_media_autoswitch_proxy_cloud_mymenu42_big6")
        self.assertEqual(mb["r74"]["r74_mode"], "wave60_rec_media_proxy_poweroff_ble_mymenu_erofs_guard")
        self.assertEqual(mc["r74"]["r74_mode"], "clean_unmount_wave60_reset_h0_h3_big6")
        for m in (ma, mb, mc):
            self.assertTrue(m["r74_enabled"])
            self.assertEqual(m["r74"]["milestone_round_ordinal"], 74)
            self.assertEqual(m["r74"]["realhw_round_ordinal"], 47)

    def test_71_round74_sanitize_preserves_negative_audit_booleans(self) -> None:
        audit = self.summary["r74_rec_media_autoswitch_proxy_cloud_mymenu42_audit"]
        self.assertIs(audit["fx3_prioritize_rec_media_present"], False)
        self.assertIs(audit["fx3_movie_sort_recording_present"], False)
        self.assertIs(audit["fx3_mymenu_30_or_36_slots_only"], False)

    def test_72_round74_r74a_proxy_dci4k_allowed_while_120p_locked(self) -> None:
        init_t = self.summary["runs"][
            "r74a_rec_media_autoswitch_proxy_cloud_mymenu42_big6_schinese"
        ]["r74_telemetry"]["wave60_init"]
        self.assertEqual(init_t["proxy_dci4k_ok_rc"], 0)
        self.assertEqual(init_t["proxy_120p_lock_rc"], -16)
        self.assertEqual(init_t["proxy_sq_120fps_lock_rc"], -16)

    def test_73_round74_r74b_slot1_s03_write_and_coupled_delete_both_erofs30(self) -> None:
        g = self.summary["runs"][
            "r74b_wave60_rec_media_proxy_poweroff_ble_mymenu_erofs_guard"
        ]["r74_telemetry"]["wave60_guard"]
        self.assertEqual(g["proxy_slot1_s03_erofs_rc"], -30)
        self.assertEqual(g["proxy_slot1_coupled_del_erofs_rc"], -30)
        self.assertEqual(g["slot1_data_sector_writes"], 0)
        self.assertEqual(g["slot1_avf_info_mutated"], 0)

    def test_74_round74_r74b_poweroff_ble_containment_zero_rf_packets(self) -> None:
        g = self.summary["runs"][
            "r74b_wave60_rec_media_proxy_poweroff_ble_mymenu_erofs_guard"
        ]["r74_telemetry"]["wave60_guard"]
        self.assertEqual(g["poweroff_ble_zerorf_tx_rc"], -100)
        self.assertEqual(g["poweroff_ble_containment_tx_rc"], -100)
        self.assertEqual(g["poweroff_ble_rf_tx_packets"], 0)
        self.assertEqual(g["rf_tx_packets"], 0)
        self.assertEqual(g["wireless_tx_packets"], 0)

    def test_75_round74_r74c_cloud_star_survives_initialize_until_explicit_unlink(self) -> None:
        ci = self.summary["runs"][
            "r74c_clean_unmount_wave60_reset_h0_h3_big6_schinese"
        ]["r74_telemetry"]["clean_unmount_wave60_h0_h3"]
        self.assertEqual(ci["camreset_resets_proxy_preserves_media_ble_mymenu_cloud_ok"], 1)
        self.assertEqual(ci["nwreset_clears_poweroff_ble_preserves_cloud_star_and_airplane_ok"], 1)
        self.assertEqual(ci["initialize_clears_media_mymenu42_preserves_cloud_star_ok"], 1)
        self.assertEqual(ci["explicit_cloud_unlink_clears_star_ok"], 1)

    def test_76_round74_clean_unmount_checks_stock_restoration_and_zero_emmc(self) -> None:
        ci = self.summary["runs"][
            "r74c_clean_unmount_wave60_reset_h0_h3_big6_schinese"
        ]["r74_telemetry"]["clean_unmount_wave60_h0_h3"]
        self.assertEqual(ci["stock_unmount_restored_ok"], 1)
        self.assertEqual(ci["dlopen_ok"], 1)
        self.assertEqual(ci["surfaces_h0_eq_h3"], 16)
        self.assertEqual(ci["drift_bits"], 0)
        self.assertEqual(ci["emmc_write_count"], 0)
        self.assertEqual(ci["cnflasha_write_bytes"], 0)


if __name__ == "__main__":
    unittest.main()
