#!/usr/bin/env python3
"""Offline four-mode unit tests for FX6-on-FX3 Round 76 (49/49 Real-HW Rounds R28..R76, 145th..147th Live Runs -> 147/147 Total, 98/98 PNGs <= 27,467 B — Wave-62)."""
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
ROUND76_REPORT_DIR = (
    REPO_ROOT
    / "reports"
    / "2026-11-18-round76-shoe-audio-4ch-subject-recog-silent-target-bodydata-qemu"
)
WAVE62_SPEC_PATH = (
    REPO_ROOT
    / "reports"
    / "2026-11-17-global-sony-wave62-shoe-audio-4ch-subject-recog-silent-target-lens-fw-intel"
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


def _build_overlay_for_r76(
    runner,
    parent_cpio: pathlib.Path,
    fp,
    fv,
    fb,
    fake_run,
    jit_meta: Dict[str, Any],
    work: pathlib.Path,
    r76_mode: str,
    lang: str = "schinese",
    enable_r76: bool = True,
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
            enable_r76=enable_r76,
            r76_mode=r76_mode,
            sd_manifest_mode="valid",
            lang=lang,
            shim_bytes=b"SHIM",
        )


class TestRound76ShoeAudio4chSubjectRecogSilentTargetBodydataQemu(unittest.TestCase):
    EXPECTED_RUN_KEYS = (
        "r76a_shoe_audio_4ch_subject_recog_silent_version_big6_schinese",
        "r76b_wave62_shoe_audio_subject_bird_silent_bodydata_nogo_guard",
        "r76c_clean_unmount_wave62_reset_h0_h3_big6_schinese",
    )

    runner: Any
    runner_src: str
    stage_a_src: str
    shim_src: str
    wave62_spec: str
    summary_raw: str
    summary: Dict[str, Any]
    r76_readme: str
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
    launcher_r76: Optional[bytes]
    shim_r76: Optional[bytes]
    shim_r75: Optional[bytes]
    r75_summary: Dict[str, Any]
    r74_summary: Dict[str, Any]
    r73_summary: Dict[str, Any]
    r72_summary: Dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = _load_closure_module("fx6_brr_r76_cached", "build_and_run_round.py")
        cls.runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")
        cls.stage_a_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        cls.shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        cls.wave62_spec = WAVE62_SPEC_PATH.read_text(encoding="utf-8")
        cls.summary_raw = (ROUND76_REPORT_DIR / "summary.json").read_text(encoding="utf-8")
        cls.summary = json.loads(cls.summary_raw)
        cls.r76_readme = (ROUND76_REPORT_DIR / "README.md").read_text(encoding="utf-8")
        cls.closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")

        alpha_p = (
            ROUND76_REPORT_DIR
            / "r76_silent_target_2items_version_bodydata_nogo_preview.png"
        )
        comp_p = (
            ROUND76_REPORT_DIR
            / "r76_shoe_audio_4ch_subject_recog_human_animal_preview.png"
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
            cls.ov_a = _build_overlay_for_r76(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wa", "shoe_audio_4ch_subject_recog_silent_version_big6", lang="schinese",
            )
            cls.ov_b = _build_overlay_for_r76(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wb", "wave62_shoe_audio_subject_bird_silent_bodydata_nogo_guard", lang="en",
            )
            cls.ov_c = _build_overlay_for_r76(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wc", "clean_unmount_wave62_reset_h0_h3_big6", lang="schinese",
            )
            cls.ov_off = _build_overlay_for_r76(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "woff", "shoe_audio_4ch_subject_recog_silent_version_big6", enable_r76=False,
            )
            cls.invalid_mode_raised = False
            try:
                _build_overlay_for_r76(
                    cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                    tpath / "wbad", "invalid_r76_mode",
                )
            except ValueError:
                cls.invalid_mode_raised = True

            zig_bin = shutil.which("zig") or (
                str(cls.runner.ZIG) if cls.runner.ZIG.is_file() else None
            )
            if zig_bin is not None:
                verify_r76_out = tpath / "fx6-stage-a-verify-r76"
                shim_r76_out = tpath / "libgrm-fbinit9-r76.so"
                shim_r75_out = tpath / "libgrm-fbinit9-r75.so"
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
                        str(verify_r76_out),
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
                ):
                    cls.runner.subprocess.run(cmd, check=True)
                cls.launcher_r76 = verify_r76_out.read_bytes()
                cls.shim_r76 = shim_r76_out.read_bytes()
                cls.shim_r75 = shim_r75_out.read_bytes()
            else:
                cls.launcher_r76 = None
                cls.shim_r76 = None
                cls.shim_r75 = None

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
        cls.r72_summary = json.loads(
            (
                REPO_ROOT
                / "reports"
                / "2026-11-18-round72-milestone-bright-mon-shotmark-usblan-bulb-dormant-qemu"
                / "summary.json"
            ).read_text(encoding="utf-8")
        )

    def test_01_wave62_global_spec_present_and_covers_all_4_pillars(self) -> None:
        self.assertTrue(WAVE62_SPEC_PATH.is_file())
        for needle in (
            "Shoe Audio Set.",
            "Audio Out Timing",
            "Audio Level Display",
            "Audio Rec Level",
            "4ch Audio Monitoring",
            "XLR-H1",
            "Wind Noise Reduct.",
            "Face/Eye Subject",
            "Face Memory",
            "TYPE_ANIMAL_EYE_AF_IN_MOVIE_NOT_SUPPORT",
            "Right/Left Eye Select",
            "Face/Eye Frame Disp.",
            "Silent Mode Settings",
            "Target Function Settings",
            "Aperture Drive in AF",
            "Auto Pixel Mapping",
            "Shutter When Pwr OFF",
            "image_sensor_barrier",
            "BODYDATA.DAT",
            "Slot 1",
            "Slot B",
            "AC Adaptor",
            "NP-FZ100",
        ):
            self.assertIn(needle, self.wave62_spec)

    def test_02_round76_summary_schema_milestone_and_zero_leaks(self) -> None:
        self.assertNotIn("/Users/", self.summary_raw)
        self.assertNotIn("/private/tmp/", self.summary_raw)
        self.assertNotIn("/tmp/round76", self.summary_raw)
        self.assertEqual(
            self.summary["schema"],
            "fx6-on-fx3-round76-shoe-audio-4ch-subject-recog-silent-target-bodydata-qemu-v1",
        )
        self.assertEqual(self.summary["round"], 76)
        self.assertIn("49/49 Real-HW Rounds", self.summary["milestone"])
        self.assertIn("147/147 Live Runs", self.summary["milestone"])
        self.assertIn("98/98 PNGs <= 27,467 B", self.summary["milestone"])
        self.assertEqual(self.summary["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(tuple(self.summary["runs"].keys()), self.EXPECTED_RUN_KEYS)

    def test_03_round76_cli_accepts_round76_and_all_3_r76_modes(self) -> None:
        self.assertIn(", 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76]", self.runner_src)
        for mode in (
            "shoe_audio_4ch_subject_recog_silent_version_big6",
            "wave62_shoe_audio_subject_bird_silent_bodydata_nogo_guard",
            "clean_unmount_wave62_reset_h0_h3_big6",
        ):
            self.assertIn(mode, self.runner_src)

    def test_04_round76_overlay_rejects_invalid_r76_mode(self) -> None:
        self.assertTrue(self.invalid_mode_raised)

    def test_05_round76_overlay_r76a_injects_etc_fx6_stage_r76_and_appfw_launch(self) -> None:
        replacements, additions, meta = self.ov_a
        self.assertTrue(meta["r76_enabled"])
        self.assertIn("etc/fx6_stage_r76", additions)
        self.assertIn("etc/fx6_r76_libjit.so", additions)
        r76_cfg = additions["etc/fx6_stage_r76"][0].decode("utf-8")
        self.assertIn("stage_r76=1", r76_cfg)
        self.assertIn("r76_mode=shoe_audio_4ch_subject_recog_silent_version_big6", r76_cfg)
        self.assertIn("milestone_49th_realhw_147th_live_98_pngs=1", r76_cfg)
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("/usr/bin/appfw-launch", init_txt)
        self.assertNotIn("--r76-wave62-guard", init_txt)

    def test_06_round76_overlay_r76b_injects_early_guard_probe_and_poweroff(self) -> None:
        replacements, _, meta = self.ov_b
        self.assertEqual(
            meta["r76"]["r76_mode"],
            "wave62_shoe_audio_subject_bird_silent_bodydata_nogo_guard",
        )
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("--r76-wave62-guard", init_txt)
        self.assertIn("FX6_R76_WAVE62_GUARD_RC=", init_txt)
        self.assertIn("FX6_R76_WAVE62_GUARD_EXIT", init_txt)
        self.assertIn("poweroff -f", init_txt)

    def test_07_round76_overlay_r76c_integrated_runs_stage_b_big6(self) -> None:
        replacements, additions, meta = self.ov_c
        self.assertEqual(meta["r76"]["r76_mode"], "clean_unmount_wave62_reset_h0_h3_big6")
        r76_cfg = additions["etc/fx6_stage_r76"][0].decode("utf-8")
        self.assertIn("r76_mode=clean_unmount_wave62_reset_h0_h3_big6", r76_cfg)
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("/usr/bin/appfw-launch", init_txt)
        self.assertNotIn("--r76-wave62-guard", init_txt)

    def test_08_round76_overlay_disabled_when_enable_r76_false(self) -> None:
        _, additions, meta = self.ov_off
        self.assertFalse(meta["r76_enabled"])
        self.assertNotIn("etc/fx6_stage_r76", additions)
        self.assertNotIn("etc/fx6_r76_libjit.so", additions)
        self.assertNotIn("r76", meta)

    def test_09_round76_stage_a_c_source_contains_all_3_wave62_probes(self) -> None:
        for sym in (
            "setup_r76_shoe_audio_subject_silent_version_probe",
            "run_r76_wave62_guard_probe",
            "run_r76_clean_unmount_wave62_h0_h3_probe",
            "r76_wave62_initialize",
            "r76_wave62_zero_init",
            "r76_wave62_camera_settings_reset",
            "r76_wave62_reset_network_settings",
            "r76_configure_shoe_audio_4ch_and_timing",
            "r76_configure_face_eye_subject_and_memory",
            "r76_configure_silent_target_and_pwr_shutter",
            "r76_configure_version_and_bodydata_nogo",
            "FX6_R76_WAVE62_INIT",
            "FX6_R76_WAVE62_GUARD",
            "FX6_R76_CLEAN_UNMOUNT_WAVE62_H0_H3",
            "--r76-wave62-guard",
            "--r76-clean-unmount-wave62-h0-h3",
            "/etc/fx6_stage_r76",
        ):
            self.assertIn(sym, self.stage_a_src)

    def test_10_round76_shim_c_source_contains_r76_guarded_bridges(self) -> None:
        self.assertIn("#if FX6_ROUND >= 76", self.shim_src)
        for sym in (
            "FX6_R76_SHOE_AUDIO_4CH_OUT_TIMING_BRIDGE",
            "FX6_R76_SUBJECT_RECOG_HUMAN_ANIMAL_FACEMEM_BRIDGE",
            "FX6_R76_SILENT_TARGET_2ITEMS_NO_PWRSHUTTER_BRIDGE",
            "FX6_R76_VERSION_SLOT1_BODYDATA_NOGO_BRIDGE",
            "FX6_R76_LANG_TELEMETRY",
            "FX6_STAGE_B_R76_BRIDGE",
        ):
            self.assertIn(sym, self.shim_src)

    def test_11_round76_compile_launcher_and_shim_aarch64_elf_symbols(self) -> None:
        if self.launcher_r76 is None or self.shim_r76 is None:
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertEqual(self.launcher_r76[:4], b"\x7fELF")
        self.assertEqual(self.shim_r76[:4], b"\x7fELF")
        self.assertEqual(struct.unpack_from("<H", self.shim_r76, 18)[0], 183)
        self.assertIn(b"FX6_R76_SHOE_AUDIO_4CH_OUT_TIMING_BRIDGE", self.shim_r76)
        self.assertIn(b"FX6_R76_SUBJECT_RECOG_HUMAN_ANIMAL_FACEMEM_BRIDGE", self.shim_r76)
        self.assertIn(b"FX6_R76_SILENT_TARGET_2ITEMS_NO_PWRSHUTTER_BRIDGE", self.shim_r76)
        self.assertIn(b"FX6_R76_VERSION_SLOT1_BODYDATA_NOGO_BRIDGE", self.shim_r76)

    def test_12_round76_shim_round75_backward_compat_excludes_r76_bridges(self) -> None:
        if self.shim_r75 is None:
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertIn(b"FX6_R75_MARKER15_PEAKING4_CLEAN_HDMI_BRIDGE", self.shim_r75)
        self.assertNotIn(b"FX6_R76_SHOE_AUDIO_4CH_OUT_TIMING_BRIDGE", self.shim_r75)

    def test_13_round76_parse_log_extracts_all_10_r76_prefixes_and_rc(self) -> None:
        serial_text = (
            "\n".join(
                [
                    "Linux version 4.9.337-scel+ (sony@fx3)",
                    "FX6_R76_WAVE62_INIT fx3_wave62_nodes_ok=1 uxc_tokens_ok=1 shoe_audio_4ch_out_timing_ok=1 subject_recog_human_animal_facemem_ok=1 silent_target_2items_no_pwrshutter_ok=1 version_slot1_bodydata_nogo_ok=1 emmc_write_count=0 r76_init_ok=1",
                    "FX6_R76_SHOE_AUDIO_4CH_OUT_TIMING_BRIDGE shoe_audio_4ch_24bit_xlrh1_ok=1 audio_out_timing_shooting_no_level_disp_ok=1 audio_rec_level_26_limiter_on_ok=1 shoe_audio_4ch_out_timing_ok=1 cnflasha_writes=0 emmc_write_count=0 r76_bridge_ok=1",
                    "FX6_R76_SUBJECT_RECOG_HUMAN_ANIMAL_FACEMEM_BRIDGE face_eye_human_animal_only_zero_bird_ok=1 animal_eye_still_only_8slot_facemem_ok=1 subject_recog_human_animal_facemem_ok=1 dormant_bird_subject_bypass_events=0 cnflasha_writes=0 emmc_write_count=0",
                    "FX6_R76_SILENT_TARGET_2ITEMS_NO_PWRSHUTTER_BRIDGE silent_mode_5lockouts_2target_items_ok=1 dormant_shutter_when_pwr_off_zero_cnflasha_ok=1 silent_target_2items_no_pwrshutter_ok=1 dormant_shutter_when_pwr_off_bypass_events=0 cnflasha_writes=0 emmc_write_count=0",
                    "FX6_R76_VERSION_SLOT1_BODYDATA_NOGO_BRIDGE version_readonly_airplane_badge_silenced_ok=1 bodydata_slot1_nogo_firewall_armed_ok=1 version_slot1_bodydata_nogo_ok=1 bodydata_slot1_flash_attempts_blocked=0 slot1_data_sector_writes=0 emmc_write_count=0",
                    "FX6_R76_LANG_TELEMETRY lang=schinese font_bank=23 str_bank=19 milestone_49th_realhw_147th_live_98_pngs=1 r76_bridge_ok=1",
                    "FX6_STAGE_B_R76_BRIDGE round=76 faithful=1 nop_count=0 milestone_49th_realhw_147th_live_98_pngs=1 emmc_write_count=0",
                    "FX6_R76_WAVE62_GUARD audio_level_disp_removed_rc=-95 subj_bird_rc=-95 shutter_pwr_off_rc=-95 bodydata_slot1_write_erofs_rc=-30 bodydata_exec_eperm_rc=-1 r76b_ok=1",
                    "FX6_R76_WAVE62_GUARD_RC=0",
                    "FX6_R76_CLEAN_UNMOUNT_WAVE62_H0_H3 stock_unmount_restored_ok=1 camreset_resets_audio_silent_subject_preserves_8facemem_airplane_ok=1 nwreset_preserves_8facemem_airplane_ok=1 initialize_clears_8facemem_preserves_airplane_ok=1 surfaces_h0_eq_h3=16 r76c_ok=1",
                ]
            )
            + "\n"
        )
        parsed = self.runner.extract_milestones(serial_text)
        r76_t = parsed["r76_telemetry"]
        self.assertEqual(r76_t["wave62_guard_rc"], 0)
        self.assertEqual(r76_t["wave62_init"]["shoe_audio_4ch_out_timing_ok"], 1)
        self.assertEqual(r76_t["shoe_audio_4ch_out_timing_bridge"]["shoe_audio_4ch_out_timing_ok"], 1)
        self.assertEqual(r76_t["subject_recog_human_animal_facemem_bridge"]["subject_recog_human_animal_facemem_ok"], 1)
        self.assertEqual(r76_t["silent_target_2items_no_pwrshutter_bridge"]["silent_target_2items_no_pwrshutter_ok"], 1)
        self.assertEqual(r76_t["version_slot1_bodydata_nogo_bridge"]["version_slot1_bodydata_nogo_ok"], 1)
        self.assertEqual(r76_t["lang_telemetry"]["lang"], "schinese")
        self.assertEqual(r76_t["lang_telemetry"]["milestone_49th_realhw_147th_live_98_pngs"], 1)
        self.assertEqual(r76_t["stage_b_bridge"]["round"], 76)
        self.assertEqual(r76_t["wave62_guard"]["r76b_ok"], 1)
        self.assertEqual(r76_t["clean_unmount_wave62_h0_h3"]["surfaces_h0_eq_h3"], 16)
        self.assertEqual(parsed["prefix_counts"]["FX6_R76_"], 9)

    def test_14_round76_parse_log_defaults_when_no_r76_lines_present(self) -> None:
        parsed = self.runner.extract_milestones("Linux version 4.9.337-scel+\n")
        self.assertIsNone(parsed["r76_telemetry"])
        self.assertEqual(parsed["prefix_counts"].get("FX6_R76_", 0), 0)

    def test_15_round76_runner_preserves_r75_prefix_and_uses_r76_stage_label(self) -> None:
        self.assertIn('if args.round >= 75:\n        tmp_prefix = "fx6-r75"', self.runner_src)
        self.assertIn('if args.round >= 76:\n        tmp_prefix = "fx6-r76"', self.runner_src)
        self.assertIn(
            "Milestone49RealHw147thLiveWave62ShoeAudio4chSubjectRecogSilentTargetBodydataNogo",
            self.runner_src,
        )
        self.assertIn(", 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76]", self.runner_src)

    def test_16_round76_runner_portability_and_sanitizer_helper(self) -> None:
        self.assertIn('shutil.which("zig")', self.runner_src)
        self.assertIn("FX6_SCRATCH_DIR", self.runner_src)
        self.assertIn("def sanitize_round76_summary(", self.runner_src)
        self.assertNotIn("/usr/" + "bin/python3", self.runner_src)

    def test_17_round76_summary_json_top_level_schema_and_milestone_metadata(self) -> None:
        d = self.summary
        self.assertEqual(
            d["schema"],
            "fx6-on-fx3-round76-shoe-audio-4ch-subject-recog-silent-target-bodydata-qemu-v1",
        )
        self.assertEqual(d["round"], 76)
        self.assertIn("49/49 Real-HW Rounds", d["milestone"])
        self.assertIn("147/147 Live Runs", d["milestone"])
        self.assertIn("98/98 PNGs <= 27,467 B", d["milestone"])
        self.assertEqual(d["date"], "2026-11-18")
        self.assertIn("4.9.337-scel+", d["kernel_version"])
        self.assertEqual(d["raw_firmware_bytes_leaked"], 0)

    def test_18_round76_summary_json_zero_host_path_scratch_and_elapsed_leaks(self) -> None:
        for forbidden in (
            "/Users/",
            "/private/tmp/",
            "/var/folders/",
            "/tmp/round76",
            "work/_scratch/",
            "work/_tests/",
            "elapsed_seconds",
            ":87" + "68",
        ):
            self.assertNotIn(forbidden, self.summary_raw)

    def test_19_round76_summary_audit_block_confirms_49_rounds_147_runs_98_pngs(self) -> None:
        audit = self.summary["r76_shoe_audio_4ch_subject_recog_silent_target_bodydata_audit"]
        self.assertEqual(audit["round"], 76)
        self.assertGreaterEqual(audit["realhw_rounds_count"], 49)
        self.assertGreaterEqual(audit["total_live_runs"], 147)
        self.assertGreaterEqual(audit["total_png_receipts"], 98)
        self.assertGreaterEqual(audit["milestone324_qemu_rounds"], 49)
        self.assertGreaterEqual(audit["milestone324_qemu_runs"], 147)
        self.assertGreaterEqual(audit["milestone324_png_receipts"], 98)
        self.assertEqual(audit["total_runs"], 3)
        negative_keys = {
            "fx3_audio_level_display_menu_present",
            "fx3_audio_out_timing_in_setup_present",
            "fx6_32bit_float_4ch_exposed",
            "fx3_bird_subject_supported",
            "fx3_insect_car_airplane_supported",
            "fx3_animal_eye_af_movie_supported",
            "fx6_animal_subject_supported",
            "fx6_eight_slot_face_memory_present",
            "fx3_shutter_when_pwr_off_exposed",
            "fx3_target_function_3rd_item_present",
            "fx6_mechanical_shutter_present",
        }
        for nk in negative_keys:
            self.assertIs(audit[nk], False, nk)
        for k, v in audit.items():
            if isinstance(v, bool) and k not in negative_keys:
                self.assertTrue(v, f"Expected audit boolean {k} to be True")

    def test_20_round76_all_3_runs_present_with_kernel_4_9_337_and_zero_crashes_writes(self) -> None:
        runs = self.summary["runs"]
        self.assertEqual(list(runs.keys()), list(self.EXPECTED_RUN_KEYS))
        for rk, rv in runs.items():
            self.assertEqual(rv["round"], 76, rk)
            self.assertIn("4.9.337-scel+", rv["kernel_version"], rk)
            self.assertEqual(rv["nop_count"], 0, rk)
            self.assertEqual(rv["crashes"], 0, rk)
            self.assertEqual(rv["emmc_write_count"], 0, rk)
            self.assertGreater(rv["wall_elapsed_sec"], 0.0, rk)

    def test_21_round76_r76a_pillar1_shoe_audio_4ch_preemption_and_audio_out_timing(self) -> None:
        init_t = self.summary["runs"][
            "r76a_shoe_audio_4ch_subject_recog_silent_version_big6_schinese"
        ]["r76_telemetry"]["wave62_init"]
        self.assertEqual(init_t["fx3_wave62_nodes_ok"], 1)
        self.assertEqual(init_t["uxc_tokens_ok"], 1)
        self.assertEqual(init_t["shoe_audio_4ch_out_timing_ok"], 1)
        self.assertEqual(init_t["audio_35mm_preempt_rc"], -16)
        self.assertEqual(init_t["audio_level_disp_removed_rc"], -95)
        self.assertEqual(init_t["audio_timing_setup_err_rc"], -95)
        self.assertEqual(init_t["dormant_audio_level_display_bypass_events"], 0)
        self.assertEqual(init_t["dormant_fx6_32bit_float_bypass_events"], 0)

    def test_22_round76_r76a_pillar2_subject_recog_human_animal_only_and_8slot_facemem(self) -> None:
        init_t = self.summary["runs"][
            "r76a_shoe_audio_4ch_subject_recog_silent_version_big6_schinese"
        ]["r76_telemetry"]["wave62_init"]
        self.assertEqual(init_t["subject_recog_human_animal_facemem_ok"], 1)
        self.assertEqual(init_t["facemem_9th_slot_rc"], -28)
        self.assertEqual(init_t["subj_bird_dormant_rc"], -95)
        self.assertEqual(init_t["animal_eye_movie_rc"], -95)
        self.assertEqual(init_t["dormant_bird_subject_bypass_events"], 0)
        self.assertEqual(init_t["dormant_insect_car_airplane_bypass_events"], 0)
        self.assertEqual(init_t["hdmi_eye_frame_baked_pixels"], 0)

    def test_23_round76_r76a_pillar3_silent_mode_2target_items_and_dormant_pwr_shutter(self) -> None:
        init_t = self.summary["runs"][
            "r76a_shoe_audio_4ch_subject_recog_silent_version_big6_schinese"
        ]["r76_telemetry"]["wave62_init"]
        self.assertEqual(init_t["silent_target_2items_no_pwrshutter_ok"], 1)
        self.assertEqual(init_t["shutter_pwr_off_dormant_rc"], -95)
        self.assertEqual(init_t["target_3rd_item_rc"], -95)
        self.assertEqual(init_t["silent_flash_lock_rc"], -16)
        self.assertEqual(init_t["dormant_shutter_when_pwr_off_bypass_events"], 0)
        self.assertEqual(init_t["target_function_3rd_item_bypass_events"], 0)

    def test_24_round76_r76a_pillar4_version_readonly_bodydata_nogo_and_vaults(self) -> None:
        init_t = self.summary["runs"][
            "r76a_shoe_audio_4ch_subject_recog_silent_version_big6_schinese"
        ]["r76_telemetry"]["wave62_init"]
        self.assertEqual(init_t["version_slot1_bodydata_nogo_ok"], 1)
        self.assertEqual(init_t["bodydata_slot1_erofs_rc"], -30)
        self.assertEqual(init_t["bodydata_exec_nogo_rc"], -1)
        self.assertEqual(init_t["cross_model_flash_rc"], -1)
        self.assertEqual(init_t["bodydata_slot1_write_count"], 0)
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
        self.assertEqual(init_t["r76_init_ok"], 1)

    def test_25_round76_r76a_stage_b_schinese_lang_telemetry_and_bridge(self) -> None:
        r76a_t = self.summary["runs"][
            "r76a_shoe_audio_4ch_subject_recog_silent_version_big6_schinese"
        ]["r76_telemetry"]
        lt = r76a_t["lang_telemetry"]
        self.assertEqual(lt["lang"], "schinese")
        self.assertEqual(lt["bk4_lang_id"], "0x02cf019c")
        self.assertEqual(lt["bk4_lang_val"], "0x19")
        self.assertEqual(lt["lang_enum"], "0x2b45_CHINESE_SIMPLIFIED")
        self.assertEqual(lt["font_bank"], 23)
        self.assertEqual(lt["str_bank"], 19)
        self.assertEqual(lt["gpe_fb"], 0)
        self.assertEqual(
            lt["round76_49realhw_wave62_shoe_audio_4ch_subject_recog_silent_bodydata"], 1
        )
        self.assertEqual(lt["milestone_49th_realhw_147th_live_98_pngs"], 1)
        self.assertEqual(lt["dormant_audio_level_display_bypass_events"], 0)
        self.assertEqual(lt["dormant_fx6_32bit_float_bypass_events"], 0)
        self.assertEqual(lt["dormant_bird_subject_bypass_events"], 0)
        self.assertEqual(lt["dormant_insect_car_airplane_bypass_events"], 0)
        self.assertEqual(lt["dormant_shutter_when_pwr_off_bypass_events"], 0)
        self.assertEqual(lt["target_function_3rd_item_bypass_events"], 0)
        self.assertEqual(lt["hdmi_eye_frame_baked_pixels"], 0)
        self.assertEqual(lt["bodydata_slot1_flash_attempts_blocked"], 0)
        self.assertEqual(lt["cross_model_flash_attempts_blocked"], 0)
        self.assertEqual(lt["slot1_data_sector_writes"], 0)
        self.assertEqual(lt["rf_tx_packets"], 0)
        self.assertEqual(lt["raw_firmware_bytes_leaked"], 0)

        sb = r76a_t["stage_b_bridge"]
        self.assertEqual(sb["round"], 76)
        self.assertEqual(sb["faithful"], 1)
        self.assertEqual(sb["nop_count"], 0)
        self.assertEqual(sb["shoe_audio_4ch_24bit_out_timing_shooting_no_level_disp"], 1)
        self.assertEqual(sb["subject_recog_human_animal_only_zero_bird_movie_lockout_8slot_facemem"], 1)
        self.assertEqual(sb["silent_mode_5locks_2target_items_no_pwr_off_shutter"], 1)
        self.assertEqual(sb["version_readonly_bodydata_slot1_nogo_firewall"], 1)
        self.assertEqual(sb["milestone_49th_realhw_147th_live_98_pngs"], 1)

    def test_26_round76_r76a_stage_b_4_pillar_bridges_verified(self) -> None:
        r76a_t = self.summary["runs"][
            "r76a_shoe_audio_4ch_subject_recog_silent_version_big6_schinese"
        ]["r76_telemetry"]
        pb1 = r76a_t["shoe_audio_4ch_out_timing_bridge"]
        self.assertEqual(pb1["shoe_audio_4ch_24bit_xlrh1_ok"], 1)
        self.assertEqual(pb1["audio_out_timing_shooting_no_level_disp_ok"], 1)
        self.assertEqual(pb1["audio_rec_level_26_limiter_on_ok"], 1)
        self.assertEqual(pb1["shoe_audio_4ch_out_timing_ok"], 1)
        self.assertEqual(pb1["dormant_audio_level_display_bypass_events"], 0)
        self.assertEqual(pb1["dormant_fx6_32bit_float_bypass_events"], 0)
        self.assertEqual(pb1["proxy_4ch_leak_events"], 0)
        self.assertEqual(pb1["r76_bridge_ok"], 1)

        pb2 = r76a_t["subject_recog_human_animal_facemem_bridge"]
        self.assertEqual(pb2["face_eye_human_animal_only_zero_bird_ok"], 1)
        self.assertEqual(pb2["animal_eye_still_only_8slot_facemem_ok"], 1)
        self.assertEqual(pb2["subject_recog_human_animal_facemem_ok"], 1)
        self.assertEqual(pb2["dormant_bird_subject_bypass_events"], 0)
        self.assertEqual(pb2["hdmi_eye_frame_baked_pixels"], 0)

        pb3 = r76a_t["silent_target_2items_no_pwrshutter_bridge"]
        self.assertEqual(pb3["silent_mode_5lockouts_2target_items_ok"], 1)
        self.assertEqual(pb3["dormant_shutter_when_pwr_off_zero_cnflasha_ok"], 1)
        self.assertEqual(pb3["silent_target_2items_no_pwrshutter_ok"], 1)
        self.assertEqual(pb3["dormant_shutter_when_pwr_off_bypass_events"], 0)
        self.assertEqual(pb3["target_function_3rd_item_bypass_events"], 0)

        pb4 = r76a_t["version_slot1_bodydata_nogo_bridge"]
        self.assertEqual(pb4["version_readonly_airplane_badge_silenced_ok"], 1)
        self.assertEqual(pb4["bodydata_slot1_nogo_firewall_armed_ok"], 1)
        self.assertEqual(pb4["version_slot1_bodydata_nogo_ok"], 1)
        self.assertEqual(pb4["slot1_data_sector_writes"], 0)

    def test_27_round76_r76a_realhw_mechanisms_verified_block_populated(self) -> None:
        rmv = self.summary["realhw_mechanisms_verified"]
        for key in (
            "wave62_shoe_audio_subject_recog_silent_bodydata_init",
            "shoe_audio_4ch_out_timing_stage_b_bridge",
            "subject_recog_human_animal_facemem_stage_b_bridge",
            "silent_target_2items_no_pwrshutter_stage_b_bridge",
            "version_slot1_bodydata_nogo_stage_b_bridge",
            "wave62_fail_closed_guard",
            "clean_unmount_wave62_reset_and_16_h0_h3",
        ):
            self.assertIn(key, rmv)
            self.assertTrue(bool(rmv[key]), key)

    def test_28_round76_r76b_guard_blocks_removed_audio_disp_32float_and_preemption(self) -> None:
        g = self.summary["runs"][
            "r76b_wave62_shoe_audio_subject_bird_silent_bodydata_nogo_guard"
        ]["r76_telemetry"]["wave62_guard"]
        self.assertEqual(g["audio_level_disp_removed_rc"], -95)
        self.assertEqual(g["audio_32bit_float_rc"], -95)
        self.assertEqual(g["audio_timing_setup_err_rc"], -95)
        self.assertEqual(g["audio_limiter_off_rc"], -95)
        self.assertEqual(g["audio_level_32_oob_rc"], -22)
        self.assertEqual(g["audio_35mm_preempt_rc"], -16)
        self.assertEqual(g["audio_xlr_handle_off_rc"], -16)
        self.assertEqual(g["audio_xlr_analog_cap_rc"], -16)
        self.assertEqual(g["audio_wind_ext_mic_rc"], -16)
        self.assertEqual(g["audio_sq_lock_rc"], -16)
        self.assertEqual(g["audio_proxy_4ch_rc"], -95)
        self.assertEqual(g["audio_proxy_120p_rc"], -16)

    def test_29_round76_r76b_guard_blocks_bird_insect_car_airplane_and_movie_animal_eye(self) -> None:
        g = self.summary["runs"][
            "r76b_wave62_shoe_audio_subject_bird_silent_bodydata_nogo_guard"
        ]["r76_telemetry"]["wave62_guard"]
        self.assertEqual(g["subj_bird_rc"], -95)
        self.assertEqual(g["subj_animal_bird_rc"], -95)
        self.assertEqual(g["subj_insect_rc"], -95)
        self.assertEqual(g["subj_car_train_rc"], -95)
        self.assertEqual(g["subj_airplane_rc"], -95)
        self.assertEqual(g["animal_eye_movie_rc"], -95)
        self.assertEqual(g["animal_regist_prio_rc"], -16)
        self.assertEqual(g["facemem_camset_excl_rc"], -95)
        self.assertEqual(g["fx6_animal_rc"], -95)
        self.assertEqual(g["fx6_facemem_rc"], -95)

    def test_30_round76_r76b_guard_blocks_silent_5lockouts_3rd_target_and_pwr_shutter(self) -> None:
        g = self.summary["runs"][
            "r76b_wave62_shoe_audio_subject_bird_silent_bodydata_nogo_guard"
        ]["r76_telemetry"]["wave62_guard"]
        self.assertEqual(g["shutter_pwr_off_rc"], -95)
        self.assertEqual(g["antidust_dormant_rc"], -95)
        self.assertEqual(g["target_3rd_item_rc"], -95)
        self.assertEqual(g["silent_movie_lock_rc"], -16)
        self.assertEqual(g["silent_flash_lock_rc"], -16)
        self.assertEqual(g["silent_bulb_lock_rc"], -16)
        self.assertEqual(g["silent_signals_unmute_rc"], -16)
        self.assertEqual(g["fx6_mech_shutter_rc"], -95)

    def test_31_round76_r76b_guard_blocks_bodydata_slot1_low_batt_202_and_cross_model(self) -> None:
        g = self.summary["runs"][
            "r76b_wave62_shoe_audio_subject_bird_silent_bodydata_nogo_guard"
        ]["r76_telemetry"]["wave62_guard"]
        self.assertEqual(g["bodydata_slot1_write_erofs_rc"], -30)
        self.assertEqual(g["bodydata_slot2_reject_rc"], -22)
        self.assertEqual(g["bodydata_low_batt_rc"], -11)
        self.assertEqual(g["bodydata_202_no_step_rc"], -22)
        self.assertEqual(g["bodydata_exec_eperm_rc"], -1)
        self.assertEqual(g["cross_model_flash_eperm_rc"], -1)

    def test_32_round76_r76b_guard_blocks_slot1_bodydata_p12_p2_cnflasha_and_keeps_sha256(self) -> None:
        r76b_t = self.summary["runs"][
            "r76b_wave62_shoe_audio_subject_bird_silent_bodydata_nogo_guard"
        ]["r76_telemetry"]
        g = r76b_t["wave62_guard"]
        self.assertEqual(r76b_t["wave62_guard_rc"], 0)
        self.assertEqual(g["slot1_wave62_erofs_rc"], -30)
        self.assertEqual(g["slot1_bodydata_ro_blocked_rc"], -30)
        self.assertEqual(g["p12_write_blocked_rc"], -30)
        self.assertEqual(g["p2_write_blocked_rc"], -30)
        self.assertEqual(g["cnflasha_ro_blocked_rc"], -30)
        self.assertEqual(g["slot1_vault_sha256_match"], 1)
        self.assertEqual(g["bodydata_slot1_write_count"], 0)
        self.assertEqual(g["slot1_data_sector_writes"], 0)
        self.assertEqual(g["rf_tx_packets"], 0)
        self.assertEqual(g["passive_tx_bytes_emitted"], 0)
        self.assertEqual(g["e_nd_actuator_tx_count"], 0)
        self.assertEqual(g["appfw_ok"], 1)
        self.assertEqual(g["shim_elf_ok"], 1)
        self.assertEqual(g["cnflasha_writes"], 0)
        self.assertEqual(g["emmc_write_count"], 0)
        self.assertEqual(g["r76b_ok"], 1)

    def test_33_round76_r76c_clean_unmount_and_3tier_asymmetric_reset_split(self) -> None:
        ci = self.summary["runs"][
            "r76c_clean_unmount_wave62_reset_h0_h3_big6_schinese"
        ]["r76_telemetry"]["clean_unmount_wave62_h0_h3"]
        self.assertEqual(ci["stock_unmount_restored_ok"], 1)
        self.assertEqual(ci["camreset_resets_audio_silent_subject_preserves_8facemem_airplane_ok"], 1)
        self.assertEqual(ci["nwreset_preserves_8facemem_airplane_ok"], 1)
        self.assertEqual(ci["initialize_clears_8facemem_preserves_airplane_ok"], 1)
        self.assertEqual(ci["dlopen_ok"], 1)
        self.assertEqual(ci["surfaces_verified"], 16)
        self.assertEqual(ci["surfaces_h0_eq_h3"], 16)
        self.assertEqual(ci["drift_bits"], 0)
        self.assertEqual(ci["slot1_vault_ro_blocked_rc"], -30)
        self.assertEqual(ci["slot1_bodydata_ro_blocked_rc"], -30)
        self.assertEqual(ci["p12_write_blocked_rc"], -30)
        self.assertEqual(ci["slot1_vault_sha256_match"], 1)
        self.assertEqual(ci["p2_write_blocked_rc"], -30)
        self.assertEqual(ci["cnflasha_ro_blocked_rc"], -30)
        self.assertEqual(ci["cnflasha_write_bytes"], 0)
        self.assertEqual(ci["emmc_write_bytes"], 0)
        self.assertEqual(ci["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(ci["emmc_write_count"], 0)
        self.assertEqual(ci["r76c_ok"], 1)

    def test_34_round76_r76a_and_r76c_gpe0_readback_big6_home_ge_300k_nonzero_pixels(self) -> None:
        for rk in (
            "r76a_shoe_audio_4ch_subject_recog_silent_version_big6_schinese",
            "r76c_clean_unmount_wave62_reset_h0_h3_big6_schinese",
        ):
            gpe = self.summary["runs"][rk]["gpe0_readback"]
            self.assertTrue(gpe["present"], rk)
            self.assertEqual(gpe["total_pixels"], 1024 * 540, rk)
            self.assertEqual(gpe["bytes"], 1024 * 540 * 4, rk)
            self.assertGreaterEqual(gpe["nonzero_pixels"], 300000, rk)
            self.assertGreaterEqual(gpe["unique_colors"], 50, rk)

    def test_35_round76_r76a_alpha_and_composited_png_dimensions_and_size_cap_27467(self) -> None:
        self.assertEqual(self.alpha_dims, (1024, 540))
        self.assertEqual(self.comp_dims, (1024, 540))
        self.assertLessEqual(len(self.alpha_png_bytes), 27467)
        self.assertLessEqual(len(self.comp_png_bytes), 27467)
        self.assertGreater(self.alpha_transparent, 100000)
        self.assertGreater(self.alpha_opaque, 100000)
        self.assertEqual(self.comp_opaque, 1024 * 540)

    def test_36_round76_r76a_png_exports_paths_sanitized_and_match_assets(self) -> None:
        pe = self.summary["runs"][
            "r76a_shoe_audio_4ch_subject_recog_silent_version_big6_schinese"
        ]["png_exports"]
        self.assertEqual(
            pe["alpha_png"]["path"],
            "reports/2026-11-18-round76-shoe-audio-4ch-subject-recog-silent-target-bodydata-qemu/r76_silent_target_2items_version_bodydata_nogo_preview.png",
        )
        self.assertEqual(
            pe["composited_png"]["path"],
            "reports/2026-11-18-round76-shoe-audio-4ch-subject-recog-silent-target-bodydata-qemu/r76_shoe_audio_4ch_subject_recog_human_animal_preview.png",
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

    def test_37_round76_r76a_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"][
            "r76a_shoe_audio_4ch_subject_recog_silent_version_big6_schinese"
        ]["r76_telemetry"]["wave62_init"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_38_round76_r76b_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"][
            "r76b_wave62_shoe_audio_subject_bird_silent_bodydata_nogo_guard"
        ]["r76_telemetry"]["wave62_guard"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_39_round76_r76c_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"][
            "r76c_clean_unmount_wave62_reset_h0_h3_big6_schinese"
        ]["r76_telemetry"]["clean_unmount_wave62_h0_h3"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_40_round76_r76a_top_colors_transparent_plus_nonzero_equals_total_pixels(self) -> None:
        gpe = self.summary["runs"][
            "r76a_shoe_audio_4ch_subject_recog_silent_version_big6_schinese"
        ]["gpe0_readback"]
        color_map = {row["argb"]: row["pixels"] for row in gpe["top_colors"]}
        self.assertIn("0x00000000", color_map)
        self.assertIn("0xff000000", color_map)
        self.assertEqual(color_map["0x00000000"] + gpe["nonzero_pixels"], gpe["total_pixels"])

    def test_41_round76_r76c_top_colors_transparent_plus_nonzero_equals_total_pixels(self) -> None:
        gpe = self.summary["runs"][
            "r76c_clean_unmount_wave62_reset_h0_h3_big6_schinese"
        ]["gpe0_readback"]
        color_map = {row["argb"]: row["pixels"] for row in gpe["top_colors"]}
        self.assertIn("0x00000000", color_map)
        self.assertEqual(color_map["0x00000000"] + gpe["nonzero_pixels"], gpe["total_pixels"])

    def test_42_round76_r76a_and_r76c_wall_elapsed_and_duration_budget_sanity(self) -> None:
        r76a = self.summary["runs"][
            "r76a_shoe_audio_4ch_subject_recog_silent_version_big6_schinese"
        ]
        r76c = self.summary["runs"][
            "r76c_clean_unmount_wave62_reset_h0_h3_big6_schinese"
        ]
        ci_headroom = 15.0 if os.environ.get("GITHUB_ACTIONS") == "true" else 0.0
        max_wall = 240.0 + ci_headroom if os.environ.get("GITHUB_ACTIONS") == "true" else 120.0 + ci_headroom
        self.assertGreaterEqual(r76a["duration_budget_sec"], 70)
        self.assertLessEqual(r76a["duration_budget_sec"], 120)
        self.assertGreater(r76a["wall_elapsed_sec"], 50.0)
        self.assertLess(r76a["wall_elapsed_sec"], max_wall)
        self.assertGreaterEqual(r76c["duration_budget_sec"], 70)
        self.assertLessEqual(r76c["duration_budget_sec"], 120)
        self.assertGreater(r76c["wall_elapsed_sec"], 50.0)
        self.assertLess(r76c["wall_elapsed_sec"], max_wall)

    def test_43_round76_r76b_fast_early_exit_wall_elapsed_with_ci_headroom(self) -> None:
        r76b = self.summary["runs"][
            "r76b_wave62_shoe_audio_subject_bird_silent_bodydata_nogo_guard"
        ]
        ci_headroom = 15.0 if os.environ.get("GITHUB_ACTIONS") == "true" else 0.0
        max_b = 45.0 + ci_headroom if os.environ.get("GITHUB_ACTIONS") == "true" else 20.0 + ci_headroom
        self.assertEqual(r76b["duration_budget_sec"], 35)
        self.assertGreater(r76b["wall_elapsed_sec"], 1.0)
        self.assertLess(r76b["wall_elapsed_sec"], max_b)
        self.assertTrue(r76b["gpe0_readback"]["skipped_stock_fx3_mode"])

    def test_44_round76_faithful_invariants_preserved_across_all_3_runs(self) -> None:
        for rk, rv in self.summary["runs"].items():
            fi = rv["faithful_invariants"]
            self.assertEqual(fi["FX6_NATIVE_FAITHFUL"], 1, rk)
            self.assertEqual(fi["subst_color"], 0, rk)
            self.assertEqual(fi["subst_image"], 0, rk)
            self.assertEqual(fi["forced_render"], 0, rk)
            self.assertEqual(fi["skipped_node"], 0, rk)
            self.assertEqual(fi["lock_bypass"], 0, rk)

    def test_45_round76_all_3_runs_stage_b_manifest_count_13(self) -> None:
        for rk, rv in self.summary["runs"].items():
            self.assertEqual(rv["stage_b"]["manifest_count"], 13, rk)
            self.assertEqual(len(rv["stage_b"]["manifest_items"]), 13, rk)

    def test_46_round76_r76c_stage_b_r76_bridges_and_zero_leak_verified(self) -> None:
        r76c_t = self.summary["runs"][
            "r76c_clean_unmount_wave62_reset_h0_h3_big6_schinese"
        ]["r76_telemetry"]
        self.assertEqual(r76c_t["shoe_audio_4ch_out_timing_bridge"]["shoe_audio_4ch_out_timing_ok"], 1)
        self.assertEqual(r76c_t["subject_recog_human_animal_facemem_bridge"]["subject_recog_human_animal_facemem_ok"], 1)
        self.assertEqual(r76c_t["silent_target_2items_no_pwrshutter_bridge"]["silent_target_2items_no_pwrshutter_ok"], 1)
        self.assertEqual(r76c_t["version_slot1_bodydata_nogo_bridge"]["version_slot1_bodydata_nogo_ok"], 1)
        self.assertEqual(r76c_t["shoe_audio_4ch_out_timing_bridge"]["dormant_audio_level_display_bypass_events"], 0)
        self.assertEqual(r76c_t["subject_recog_human_animal_facemem_bridge"]["dormant_bird_subject_bypass_events"], 0)
        self.assertEqual(r76c_t["silent_target_2items_no_pwrshutter_bridge"]["dormant_shutter_when_pwr_off_bypass_events"], 0)
        self.assertEqual(r76c_t["version_slot1_bodydata_nogo_bridge"]["slot1_data_sector_writes"], 0)
        self.assertEqual(r76c_t["stage_b_bridge"]["e_nd_actuator_tx_count"], 0)

    def test_47_round76_all_3_runs_prefix_counts_include_fx6_r76(self) -> None:
        r76a_pc = self.summary["runs"][
            "r76a_shoe_audio_4ch_subject_recog_silent_version_big6_schinese"
        ]["prefix_counts"]
        r76b_pc = self.summary["runs"][
            "r76b_wave62_shoe_audio_subject_bird_silent_bodydata_nogo_guard"
        ]["prefix_counts"]
        r76c_pc = self.summary["runs"][
            "r76c_clean_unmount_wave62_reset_h0_h3_big6_schinese"
        ]["prefix_counts"]
        self.assertGreater(r76a_pc["FX6_R76_"], 10)
        self.assertEqual(r76b_pc["FX6_R76_"], 3)
        self.assertGreater(r76c_pc["FX6_R76_"], 10)

    def test_48_round76_r76_meta_invariants_across_all_3_runs(self) -> None:
        for rk, rv in self.summary["runs"].items():
            m = rv["stage_b"]["r76"]
            self.assertEqual(m["milestone_round_ordinal"], 76, rk)
            self.assertEqual(m["realhw_round_ordinal"], 49, rk)
            self.assertEqual(m["total_live_runs_at_completion"], 147, rk)
            self.assertEqual(m["total_png_receipts_at_completion"], 98, rk)
            self.assertEqual(m["dormant_audio_level_display_bypass_events"], 0, rk)
            self.assertEqual(m["dormant_fx6_32bit_float_bypass_events"], 0, rk)
            self.assertEqual(m["dormant_bird_subject_bypass_events"], 0, rk)
            self.assertEqual(m["dormant_insect_car_airplane_bypass_events"], 0, rk)
            self.assertEqual(m["dormant_shutter_when_pwr_off_bypass_events"], 0, rk)
            self.assertEqual(m["target_function_3rd_item_bypass_events"], 0, rk)
            self.assertEqual(m["hdmi_eye_frame_baked_pixels"], 0, rk)
            self.assertEqual(m["bodydata_slot1_write_count"], 0, rk)
            self.assertEqual(m["slot1_data_sector_writes"], 0, rk)
            self.assertEqual(m["rf_tx_packets"], 0, rk)
            self.assertEqual(m["passive_tx_bytes_emitted"], 0, rk)
            self.assertEqual(m["e_nd_actuator_tx_count"], 0, rk)
            self.assertEqual(m["raw_firmware_bytes_leaked"], 0, rk)
            self.assertEqual(m["cnflasha_writes"], 0, rk)
            self.assertEqual(m["emmc_write_count"], 0, rk)
            self.assertEqual(m["p2_setting_writes"], 0, rk)

    def test_49_round76_sanitize_helper_redacts_host_paths_and_reserved_port(self) -> None:
        dirty = {
            "run_id": "test-run",
            "lang": "schinese",
            "r76_mode": "shoe_audio_4ch_subject_recog_silent_version_big6",
            "kernel_version": "Linux version 4.9.337-scel+",
            "kernel_bin": "/Users/fake/secret/kernel.bin",
            "dtb_bin": "/Users/fake/secret/guest.dtb",
            "build": {"tmp_build": "/private/tmp/build-123"},
            "stage_b": {"r76": {"r76_mode": "shoe_audio_4ch_subject_recog_silent_version_big6"}},
            "r76_telemetry": {
                "wave62_init": {"r76_init_ok": 1},
                "wave62_guard": {"r76b_ok": 1},
                "clean_unmount_wave62_h0_h3": {"r76c_ok": 1, "surfaces_h0_eq_h3": 16},
            },
            "gpe0_readback": {"nonzero_pixels": 346206},
            "png_exports": {
                "alpha_png": {
                    "path": "/Users/kafu/repo/reports/2026-11-18-round76-shoe-audio-4ch-subject-recog-silent-target-bodydata-qemu/r76_silent_target_2items_version_bodydata_nogo_preview.png"
                }
            },
            "prefix_counts": {"FX6_R76_": 10},
        }
        sanitized = self.runner.sanitize_round76_summary(dirty, dirty, dirty)
        raw = json.dumps(sanitized)
        self.assertNotIn("/Users/", raw)
        self.assertNotIn("/private/tmp/", raw)
        self.assertNotIn("kernel_bin", raw)
        self.assertNotIn("dtb_bin", raw)
        self.assertIn(
            "reports/2026-11-18-round76-shoe-audio-4ch-subject-recog-silent-target-bodydata-qemu/r76_silent_target_2items_version_bodydata_nogo_preview.png",
            raw,
        )

    def test_50_round76_no_stray_temp_files_or_reserved_port_in_repo(self) -> None:
        for bad_name in ("tmp", "scratch", ".worktrees"):
            self.assertFalse((REPO_ROOT / bad_name).exists(), bad_name)
        reserved_port = "87" + "68"
        self.assertNotIn(reserved_port, self.summary_raw)
        self.assertNotIn(reserved_port, self.r76_readme)

    def test_51_round76_test_suite_contains_at_least_72_unit_tests(self) -> None:
        methods = [m for m in dir(self) if m.startswith("test_")]
        self.assertGreaterEqual(len(methods), 72)

    def test_52_round76_three_clean_env_modes_preserve_parity(self) -> None:
        for env_overrides in (
            {},
            {"FX3_CLEAN_ROOM_TEST": "1"},
            {"FX3_FX6_FORCE_CLEAN_ROOM": "1"},
        ):
            with mock.patch.dict(os.environ, env_overrides, clear=False):
                parsed = self.runner.extract_milestones(
                    "Linux version 4.9.337-scel+\n"
                    "FX6_R76_WAVE62_INIT shoe_audio_4ch_out_timing_ok=1 subject_recog_human_animal_facemem_ok=1 "
                    "silent_target_2items_no_pwrshutter_ok=1 version_slot1_bodydata_nogo_ok=1 r76_init_ok=1\n"
                )
                self.assertEqual(parsed["r76_telemetry"]["wave62_init"]["r76_init_ok"], 1)

    def test_53_round76_mocked_donorless_work_root_none_fallback_and_master_gates(self) -> None:
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
                self.assertGreaterEqual(rep324.qemu_rounds_verified, 49)
                self.assertGreaterEqual(rep324.qemu_runs_verified, 147)
                self.assertGreaterEqual(rep324.qemu_png_receipts_verified, 98)

                rep349 = evaluate_realhw_milestone349_master_gate(
                    repo_root=REPO_ROOT,
                    force_clean_room=True,
                    simulate_bench_dry_run=False,
                )
                self.assertEqual(rep349.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertTrue(rep349.all_pillars_milestone_ready)
                self.assertEqual(rep349.raw_firmware_bytes_leaked, 0)
                self.assertGreaterEqual(rep349.qemu_rounds_verified, 49)
                self.assertGreaterEqual(rep349.qemu_runs_verified, 147)
                self.assertGreaterEqual(rep349.qemu_png_receipts_verified, 98)
        finally:
            for p in added:
                if p in sys.path:
                    sys.path.remove(p)

    def test_54_round76_argparse_percent_safe_help_and_no_hardcoded_python3(self) -> None:
        for line in self.runner_src.splitlines():
            if "help=" in line and "%" in line:
                stripped = line.replace("%%", "")
                self.assertNotIn("%", stripped, f"Unescaped '%' in argparse help: {line}")
        test_src = pathlib.Path(__file__).read_text(encoding="utf-8")
        forbidden_py = "/usr/" + "bin/python3"
        self.assertNotIn(forbidden_py, self.runner_src)
        self.assertNotIn(forbidden_py, test_src)

    def test_55_round76_all_98_milestone_pngs_under_27467b_and_clean_room_safe(self) -> None:
        round_dirs = [
            d for d in (REPO_ROOT / "reports").glob("2026-??-??-round*")
            if d.is_dir() and int(d.name.split("-round")[1].split("-")[0]) >= 28
        ]
        all_pngs = sorted(p for d in round_dirs for p in d.rglob("*.png") if p.is_file())
        self.assertGreaterEqual(len(all_pngs), 98)
        for p in all_pngs:
            self.assertLessEqual(p.stat().st_size, 27467, str(p))

    def test_56_round76_cli_help_subprocess_smoke(self) -> None:
        res = subprocess.run(
            [sys.executable, "-B", str(CLOSURE_DIR / "build_and_run_round.py"), "--help"],
            capture_output=True,
            text=True,
            check=True,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        self.assertIn("--r76-mode", res.stdout)
        self.assertIn("shoe_audio_4ch_subject_recog_silent_version_big6", res.stdout)

    def test_57_round76_pillar1_shoe_audio_4ch_xlrh1_and_audio_out_timing_metadata(self) -> None:
        r76a_meta = self.summary["runs"][
            "r76a_shoe_audio_4ch_subject_recog_silent_version_big6_schinese"
        ]["stage_b"]["r76"]
        au = r76a_meta["shoe_audio_4ch_xlrh1_and_audio_out_timing_wave62"]
        self.assertIn("Shooting -> [Audio Recording] -> [Audio Out Timing]", au["audio_out_timing_path"])
        self.assertIn("_f 0x7a36", au["audio_level_display_removed"])
        self.assertIn("0..31 factory default 26", au["audio_rec_level"])
        self.assertIn("adj_audio_rec_level_defult", au["audio_rec_level"])
        self.assertIn("48kHz/24bit 4ch", au["shoe_audio_set"])
        self.assertIn("3.5mm MIC", au["preemption_and_lockouts"])
        self.assertIn("32bit float", au["fx6_diff"])

    def test_58_round76_pillar2_subject_recog_human_animal_only_and_8slot_facemem_metadata(self) -> None:
        r76a_meta = self.summary["runs"][
            "r76a_shoe_audio_4ch_subject_recog_silent_version_big6_schinese"
        ]["stage_b"]["r76"]
        sr = r76a_meta["face_eye_subject_human_animal_only_and_8slot_facemem"]
        self.assertIn("ONLY Human", sr["fx3_subject_options"])
        self.assertIn("ZERO Bird", sr["wave42_erratum_busted"])
        self.assertIn("TYPE_ANIMAL_EYE_AF_IN_MOVIE_NOT_SUPPORT", sr["still_only_animal_eye_af"])
        self.assertIn("0 HDMI/RAW pixels", sr["eye_select_and_clean_hdmi"])
        self.assertIn("8 slots", sr["eight_slot_face_memory"])
        self.assertIn("CAMSET*.DAT", sr["eight_slot_face_memory"])
        self.assertIn("Saved Tracking Face", sr["fx6_diff"])

    def test_59_round76_pillar3_silent_mode_2target_items_and_dormant_pwr_shutter_metadata(self) -> None:
        r76a_meta = self.summary["runs"][
            "r76a_shoe_audio_4ch_subject_recog_silent_version_big6_schinese"
        ]["stage_b"]["r76"]
        sl = r76a_meta["silent_mode_2target_items_and_dormant_pwr_shutter"]
        self.assertIn("[Target Function Settings]", sl["two_level_menu"])
        self.assertIn("5 features", sl["five_hard_lockouts"])
        self.assertIn("ONLY 2 items", sl["two_target_items_only"])
        self.assertIn("Aperture Drive in AF", sl["two_target_items_only"])
        self.assertIn("Auto Pixel Mapping", sl["two_target_items_only"])
        self.assertIn("Shutter When Pwr OFF", sl["dormant_shutter_when_pwr_off"])
        self.assertIn("Auto Pixel Restore", sl["fx6_diff"])

    def test_60_round76_pillar4_version_readonly_and_slot1_bodydata_nogo_metadata(self) -> None:
        r76a_meta = self.summary["runs"][
            "r76a_shoe_audio_4ch_subject_recog_silent_version_big6_schinese"
        ]["stage_b"]["r76"]
        vr = r76a_meta["version_readonly_and_slot1_bodydata_nogo_firewall"]
        self.assertIn("Ver. 7.02", vr["version_modal"])
        self.assertIn("BODYDATA.DAT on Slot 1 root", vr["bodydata_requirements"])
        self.assertIn("51%", vr["bodydata_requirements"])
        self.assertIn("Ver. 2.04/2.05", vr["bodydata_requirements"])
        self.assertIn("NO-GO", vr["hard_blocked_nogo_redline"])
        self.assertIn("Slot B + mandatory AC Adaptor", vr["fx6_diff"])

    def test_61_round76_3tier_reset_matrix_across_c_summary_and_readmes(self) -> None:
        r76a_meta = self.summary["runs"][
            "r76a_shoe_audio_4ch_subject_recog_silent_version_big6_schinese"
        ]["stage_b"]["r76"]
        rt = r76a_meta["reset_tiers"]
        self.assertIn("ALL 8 [Face Memory] slots", rt["camera_settings_reset"])
        self.assertIn("ALL 8 [Face Memory] slots", rt["reset_network_settings"])
        self.assertIn("Clears ALL 8 [Face Memory] slots", rt["initialize"])
        self.assertIn("[Airplane Mode]=On", rt["initialize"])
        for fn in (
            "r76_wave62_camera_settings_reset",
            "r76_wave62_reset_network_settings",
            "r76_wave62_initialize",
            "r76_wave62_zero_init",
        ):
            self.assertIn(fn, self.stage_a_src)
        self.assertIn("Reset Network Set.", self.r76_readme)
        self.assertIn("Reset Network Set.", self.closure_readme)

    def test_62_round76_wave62_uxc_and_node_tokens_wired_in_stage_a_source(self) -> None:
        for sym in (
            "r76_lookup_wave62_menu_node",
            "r76_lookup_uxc_token",
            "_f:0x77f6:Shoe Audio Set.",
            "_f:0x6195:48kHz/24bit 4ch",
            "_f:0x70bc:48kHz/24bit 2ch",
            "_f:0x6dde:48kHz/16bit 2ch",
            "_f:0x6bc2:Audio Out Timing",
            "_f:0x753d:Live",
            "_f:0x6066:Lip Sync",
            "_f:0x63b9:Audio Rec Level",
            "base:0xe4b1:Wind Noise Reduct.",
            "_f:0x70dd:4ch Audio Monitoring",
            "_f:0x70fa:Face/Eye Subject",
            "_f:0x763f:Human",
            "_f:0x6511:Animal",
            "_f:0x63a5:Right/Left Eye Select",
            "_f:0x7183:Face/Eye Frame Disp.",
            "_f:0x6533:Face Memory",
            "_f:0x629c:Regist. Faces Priority",
            "_f:0x655f:Silent Mode Settings",
            "_f:0x7046:Silent Mode",
            "_f:0x79c0:Target Function Settings",
            "_f:0x61b5:Aperture Drive in AF",
            "_f:0x7734:Auto Pixel Mapping",
            "base:0xe396:Version",
            "_f:0x6fd6:Software Update",
            "_g:0x6516:Latest SW badge",
            "_g:0x6517:Lens Ver.",
            "_f:0x7a36:Audio Level Display (removed Ver.2.00+)",
            "_f:0x6cb1:Bird (dormant on FX3)",
            "_f:0x6957:Animal/Bird (dormant on FX3)",
            "_f:0x6996:Insect (dormant on FX3)",
            "_f:0x674e:Car/Train (dormant on FX3)",
            "_f:0x7440:Airplane (dormant on FX3)",
            "dormant:TYPE_ANIMAL_EYE_AF_IN_MOVIE_NOT_SUPPORT",
            "_f:0x709f:Shutter When Pwr OFF (dormant)",
            "_f:0x7495:Anti-dust Function (dormant)",
            "dormant:FX6_32BIT_FLOAT_4CH",
        ):
            self.assertIn(sym, self.stage_a_src)

    def test_63_round76_report_markdown_has_chinese_conclusions_and_fact_inference_split(self) -> None:
        self.assertIn("## 结论先行", self.r76_readme)
        self.assertIn("实测事实", self.r76_readme)
        self.assertIn("推断", self.r76_readme)
        self.assertIn("49/49", self.r76_readme)
        self.assertIn("147/147", self.r76_readme)
        self.assertIn("98/98", self.r76_readme)
        self.assertIn("unexecuted_physical_camera_bench_boundaries", self.summary)
        self.assertEqual(len(self.summary["unexecuted_physical_camera_bench_boundaries"]), 3)

    def test_64_round76_closure_readme_documents_round76_section(self) -> None:
        self.assertIn("## 76. Round 76", self.closure_readme)
        self.assertIn("147/147", self.closure_readme)
        self.assertIn("98/98", self.closure_readme)
        self.assertIn("BODYDATA.DAT", self.closure_readme)

    def test_65_round76_round75_baseline_non_regression_preserved(self) -> None:
        self.assertEqual(self.r75_summary["round"], 75)
        self.assertEqual(self.r75_summary["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(
            self.r75_summary["r75_ftp_ftpes_customwb_afspeed_focusmap_marker_peaking_audit"]["realhw_rounds_count"],
            48,
        )

    def test_66_round76_round74_baseline_non_regression_preserved(self) -> None:
        self.assertEqual(self.r74_summary["round"], 74)
        self.assertEqual(self.r74_summary["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(
            self.r74_summary["r74_rec_media_autoswitch_proxy_cloud_mymenu42_audit"]["realhw_rounds_count"],
            47,
        )

    def test_67_round76_round73_baseline_non_regression_preserved(self) -> None:
        self.assertEqual(self.r73_summary["round"], 73)
        self.assertEqual(self.r73_summary["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(
            self.r73_summary["r73_big6_framing_interval_tc_ssh_fan_erofs_audit"]["realhw_rounds_count"],
            46,
        )

    def test_68_round76_round72_baseline_non_regression_preserved(self) -> None:
        self.assertEqual(self.r72_summary["round"], 72)
        self.assertEqual(self.r72_summary["raw_firmware_bytes_leaked"], 0)

    def test_69_round76_wave62_enums_and_structs_in_stage_a(self) -> None:
        for tok in (
            "R76_SHOE_48K_16B_2CH",
            "R76_SHOE_48K_24B_2CH",
            "R76_SHOE_48K_24B_4CH",
            "R76_FX6_DORMANT_32B_FLOAT_4CH",
            "R76_OUT_TIMING_LIVE",
            "R76_OUT_TIMING_LIP_SYNC",
            "R76_SUBJ_HUMAN",
            "R76_SUBJ_ANIMAL",
            "R76_SUBJ_BIRD",
            "R76_SUBJ_INSECT",
            "R76_SUBJ_CAR_TRAIN",
            "R76_SUBJ_AIRPLANE",
            "R76_AP_DRIVE_SILENT_PRIORITY",
            "R76_PIXMAP_OFF",
        ):
            self.assertIn(tok, self.stage_a_src)

    def test_70_round76_overlay_meta_modes_and_reset_flags_consistent(self) -> None:
        _, _, ma = self.ov_a
        _, _, mb = self.ov_b
        _, _, mc = self.ov_c
        self.assertEqual(ma["r76"]["r76_mode"], "shoe_audio_4ch_subject_recog_silent_version_big6")
        self.assertEqual(mb["r76"]["r76_mode"], "wave62_shoe_audio_subject_bird_silent_bodydata_nogo_guard")
        self.assertEqual(mc["r76"]["r76_mode"], "clean_unmount_wave62_reset_h0_h3_big6")
        for m in (ma, mb, mc):
            self.assertTrue(m["r76_enabled"])
            self.assertEqual(m["r76"]["milestone_round_ordinal"], 76)
            self.assertEqual(m["r76"]["realhw_round_ordinal"], 49)

    def test_71_round76_sanitize_preserves_negative_audit_booleans(self) -> None:
        audit = self.summary["r76_shoe_audio_4ch_subject_recog_silent_target_bodydata_audit"]
        self.assertIs(audit["fx3_audio_level_display_menu_present"], False)
        self.assertIs(audit["fx3_audio_out_timing_in_setup_present"], False)
        self.assertIs(audit["fx6_32bit_float_4ch_exposed"], False)
        self.assertIs(audit["fx3_bird_subject_supported"], False)
        self.assertIs(audit["fx3_insect_car_airplane_supported"], False)
        self.assertIs(audit["fx3_animal_eye_af_movie_supported"], False)
        self.assertIs(audit["fx6_animal_subject_supported"], False)
        self.assertIs(audit["fx6_eight_slot_face_memory_present"], False)
        self.assertIs(audit["fx3_shutter_when_pwr_off_exposed"], False)
        self.assertIs(audit["fx3_target_function_3rd_item_present"], False)
        self.assertIs(audit["fx6_mechanical_shutter_present"], False)

    def test_72_round76_r76a_animal_eye_af_still_allowed_while_movie_and_bird_blocked(self) -> None:
        init_t = self.summary["runs"][
            "r76a_shoe_audio_4ch_subject_recog_silent_version_big6_schinese"
        ]["r76_telemetry"]["wave62_init"]
        self.assertEqual(init_t["subject_recog_human_animal_facemem_ok"], 1)
        self.assertEqual(init_t["subj_bird_dormant_rc"], -95)
        self.assertEqual(init_t["animal_eye_movie_rc"], -95)
        self.assertEqual(init_t["facemem_9th_slot_rc"], -28)

    def test_73_round76_r76b_slot1_bodydata_erofs30_and_zero_data_writes(self) -> None:
        g = self.summary["runs"][
            "r76b_wave62_shoe_audio_subject_bird_silent_bodydata_nogo_guard"
        ]["r76_telemetry"]["wave62_guard"]
        self.assertEqual(g["bodydata_slot1_write_erofs_rc"], -30)
        self.assertEqual(g["slot1_wave62_erofs_rc"], -30)
        self.assertEqual(g["slot1_bodydata_ro_blocked_rc"], -30)
        self.assertEqual(g["bodydata_exec_eperm_rc"], -1)
        self.assertEqual(g["cross_model_flash_eperm_rc"], -1)
        self.assertEqual(g["bodydata_slot1_write_count"], 0)
        self.assertEqual(g["slot1_data_sector_writes"], 0)

    def test_74_round76_r76b_audio_level_display_removed_and_35mm_preemption(self) -> None:
        g = self.summary["runs"][
            "r76b_wave62_shoe_audio_subject_bird_silent_bodydata_nogo_guard"
        ]["r76_telemetry"]["wave62_guard"]
        self.assertEqual(g["audio_level_disp_removed_rc"], -95)
        self.assertEqual(g["audio_timing_setup_err_rc"], -95)
        self.assertEqual(g["audio_35mm_preempt_rc"], -16)
        self.assertEqual(g["audio_xlr_handle_off_rc"], -16)
        self.assertEqual(g["audio_xlr_analog_cap_rc"], -16)
        self.assertEqual(g["audio_proxy_120p_rc"], -16)

    def test_75_round76_r76c_8slot_face_memory_survives_reset_cleared_only_by_initialize(self) -> None:
        ci = self.summary["runs"][
            "r76c_clean_unmount_wave62_reset_h0_h3_big6_schinese"
        ]["r76_telemetry"]["clean_unmount_wave62_h0_h3"]
        self.assertEqual(ci["camreset_resets_audio_silent_subject_preserves_8facemem_airplane_ok"], 1)
        self.assertEqual(ci["nwreset_preserves_8facemem_airplane_ok"], 1)
        self.assertEqual(ci["initialize_clears_8facemem_preserves_airplane_ok"], 1)

    def test_76_round76_clean_unmount_checks_stock_restoration_and_zero_emmc(self) -> None:
        ci = self.summary["runs"][
            "r76c_clean_unmount_wave62_reset_h0_h3_big6_schinese"
        ]["r76_telemetry"]["clean_unmount_wave62_h0_h3"]
        self.assertEqual(ci["stock_unmount_restored_ok"], 1)
        self.assertEqual(ci["dlopen_ok"], 1)
        self.assertEqual(ci["surfaces_h0_eq_h3"], 16)
        self.assertEqual(ci["drift_bits"], 0)
        self.assertEqual(ci["emmc_write_count"], 0)
        self.assertEqual(ci["cnflasha_write_bytes"], 0)


if __name__ == "__main__":
    unittest.main()
