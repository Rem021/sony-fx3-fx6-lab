#!/usr/bin/env python3
"""Offline four-mode unit tests for FX6-on-FX3 Round 73 (46/46 Real-HW Rounds R28..R73, 136th..138th Live Runs -> 138/138 Total, 92/92 PNGs <= 27,467 B — Wave-59)."""
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
ROUND73_REPORT_DIR = (
    REPO_ROOT
    / "reports"
    / "2026-11-18-round73-big6-home-framing-interval-tc-make-ssh-auth-fan-qemu"
)
WAVE59_SPEC_PATH = (
    REPO_ROOT
    / "reports"
    / "2026-11-17-global-sony-wave59-big6-home-framing-interval-shoot-tc-make-run-auth-intel"
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


def _build_overlay_for_r73(
    runner,
    parent_cpio: pathlib.Path,
    fp,
    fv,
    fb,
    fake_run,
    jit_meta: Dict[str, Any],
    work: pathlib.Path,
    r73_mode: str,
    lang: str = "schinese",
    enable_r73: bool = True,
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
            enable_r73=enable_r73,
            r73_mode=r73_mode,
            sd_manifest_mode="valid",
            lang=lang,
            shim_bytes=b"SHIM",
        )


class TestRound73Big6HomeFramingIntervalTcMakeSshAuthFanQemu(unittest.TestCase):
    EXPECTED_RUN_KEYS = (
        "r73a_big6_framing_interval_tc_make_ssh_auth_fan_big6_schinese",
        "r73b_wave59_big6_framing_interval_tc_ssh_fan_erofs_guard",
        "r73c_clean_unmount_wave59_reset_h0_h3_big6_schinese",
    )

    runner: Any
    runner_src: str
    stage_a_src: str
    shim_src: str
    wave59_spec: str
    summary_raw: str
    summary: Dict[str, Any]
    r73_readme: str
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
    launcher_r73: Optional[bytes]
    shim_r73: Optional[bytes]
    shim_r72: Optional[bytes]
    r72_summary: Dict[str, Any]
    r71_summary: Dict[str, Any]
    r70_summary: Dict[str, Any]
    r69_summary: Dict[str, Any]
    r68_summary: Dict[str, Any]
    r67_summary: Dict[str, Any]
    r66_summary: Dict[str, Any]
    r65_summary: Dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = _load_closure_module("fx6_brr_r73_cached", "build_and_run_round.py")
        cls.runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")
        cls.stage_a_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        cls.shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        cls.wave59_spec = WAVE59_SPEC_PATH.read_text(encoding="utf-8")
        cls.summary_raw = (ROUND73_REPORT_DIR / "summary.json").read_text(encoding="utf-8")
        cls.summary = json.loads(cls.summary_raw)
        cls.r73_readme = (ROUND73_REPORT_DIR / "README.md").read_text(encoding="utf-8")
        cls.closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")

        alpha_p = (
            ROUND73_REPORT_DIR
            / "assets"
            / "r73a-big6-framing-interval-tc-ssh-fan-big6-schinese-alpha.png"
        )
        comp_p = (
            ROUND73_REPORT_DIR
            / "assets"
            / "r73a-big6-framing-interval-tc-ssh-fan-big6-schinese-composited.png"
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
            cls.ov_a = _build_overlay_for_r73(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wa", "big6_framing_interval_tc_make_ssh_auth_fan_big6", lang="schinese",
            )
            cls.ov_b = _build_overlay_for_r73(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wb", "wave59_big6_framing_interval_tc_ssh_fan_erofs_guard", lang="en",
            )
            cls.ov_c = _build_overlay_for_r73(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wc", "clean_unmount_wave59_reset_h0_h3_big6", lang="schinese",
            )
            cls.ov_off = _build_overlay_for_r73(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "woff", "big6_framing_interval_tc_make_ssh_auth_fan_big6", enable_r73=False,
            )
            cls.invalid_mode_raised = False
            try:
                _build_overlay_for_r73(
                    cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                    tpath / "wbad", "invalid_r73_mode",
                )
            except ValueError:
                cls.invalid_mode_raised = True

            zig_bin = shutil.which("zig") or (
                str(cls.runner.ZIG) if cls.runner.ZIG.is_file() else None
            )
            if zig_bin is not None:
                verify_r73_out = tpath / "fx6-stage-a-verify-r73"
                shim_r73_out = tpath / "libgrm-fbinit9-r73.so"
                shim_r72_out = tpath / "libgrm-fbinit9-r72.so"
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
                        str(verify_r73_out),
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
                    [
                        zig_bin,
                        "cc",
                        "-target",
                        "aarch64-linux-gnu.2.25",
                        "-O0",
                        "-shared",
                        "-fPIC",
                        "-DFX6_ROUND=72",
                        str(CLOSURE_DIR / "libgrm-fbinit9.c"),
                        "-ldl",
                        "-lpthread",
                        "-o",
                        str(shim_r72_out),
                    ],
                ):
                    cls.runner.subprocess.run(cmd, check=True)
                cls.launcher_r73 = verify_r73_out.read_bytes()
                cls.shim_r73 = shim_r73_out.read_bytes()
                cls.shim_r72 = shim_r72_out.read_bytes()
            else:
                cls.launcher_r73 = None
                cls.shim_r73 = None
                cls.shim_r72 = None

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

    def test_01_wave59_global_spec_present_and_covers_all_wave59_pillars(self) -> None:
        self.assertTrue(WAVE59_SPEC_PATH.is_file())
        for needle in (
            "Fixed/Variable",
            "BKID_APP_setting_fps_fixed_variable_select",
            "update_big6_item_iso_ei",
            "Home (Lower Left)",
            "ND Filter",
            "Select LUT",
            "Framing Settings",
            "TYPE_EFRAMING_SUPPORT_TYPE_MANUAL_ONLY",
            "Auto Framing",
            "AUTO_FRAMING_AFR",
            "Interval Shoot Func.",
            "Number of Shots",
            "Electronic Shutter",
            "Display as Group",
            "PB Speed for Interval",
            "Interval Rec",
            "MODEL_VALUE_CHANGED_BY_EXCLUSION_INTERVAL_REC",
            "Time Code Make",
            "Regenerate",
            "Time Code Run",
            "VMC-BNCM1",
            "EXT-LK",
            "HDMI Output Settings",
            "REC Control",
            "Time Code Output",
            "4ch Audio Output",
            "Access Authen.",
            "MSGID_SSHD_START_CMD",
            "HTTP_DIGEST",
            "Import Root Certificate",
            "Fan Control",
            "FAN_CONTROL_MAX",
            "Always Off",
            "Auto Power OFF Temp.",
            "EROFS",
        ):
            self.assertIn(needle, self.wave59_spec)

    def test_02_round73_summary_schema_milestone_and_zero_leaks(self) -> None:
        self.assertNotIn("/Users/", self.summary_raw)
        self.assertNotIn("/private/tmp/", self.summary_raw)
        self.assertEqual(
            self.summary["schema"],
            "fx6-on-fx3-round73-big6-home-framing-interval-tc-make-ssh-auth-fan-qemu-v1",
        )
        self.assertEqual(self.summary["round"], 73)
        self.assertIn("46/46 Real-HW Rounds", self.summary["milestone"])
        self.assertIn("138/138 Live Runs", self.summary["milestone"])
        self.assertIn("92/92 PNGs <= 27,467 B", self.summary["milestone"])
        self.assertEqual(self.summary["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(tuple(self.summary["runs"].keys()), self.EXPECTED_RUN_KEYS)

    def test_03_round73_cli_accepts_round73_and_all_3_r73_modes(self) -> None:
        self.assertIn(", 64, 65, 66, 67, 68, 69, 70, 71, 72, 73]", self.runner_src)
        for mode in (
            "big6_framing_interval_tc_make_ssh_auth_fan_big6",
            "wave59_big6_framing_interval_tc_ssh_fan_erofs_guard",
            "clean_unmount_wave59_reset_h0_h3_big6",
        ):
            self.assertIn(mode, self.runner_src)

    def test_04_round73_overlay_rejects_invalid_r73_mode(self) -> None:
        self.assertTrue(self.invalid_mode_raised)

    def test_05_round73_overlay_r73a_injects_etc_fx6_stage_r73_and_appfw_launch(self) -> None:
        replacements, additions, meta = self.ov_a
        self.assertTrue(meta["r73_enabled"])
        self.assertIn("etc/fx6_stage_r73", additions)
        self.assertIn("etc/fx6_r73_libjit.so", additions)
        r73_cfg = additions["etc/fx6_stage_r73"][0].decode("utf-8")
        self.assertIn("stage_r73=1", r73_cfg)
        self.assertIn("r73_mode=big6_framing_interval_tc_make_ssh_auth_fan_big6", r73_cfg)
        self.assertIn("milestone_46th_realhw_138th_live_92_pngs=1", r73_cfg)
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("/usr/bin/appfw-launch", init_txt)
        self.assertNotIn("--r73-wave59-guard", init_txt)

    def test_06_round73_overlay_r73b_injects_early_guard_probe_and_poweroff(self) -> None:
        replacements, _, meta = self.ov_b
        self.assertEqual(
            meta["r73"]["r73_mode"],
            "wave59_big6_framing_interval_tc_ssh_fan_erofs_guard",
        )
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("--r73-wave59-guard", init_txt)
        self.assertIn("FX6_R73_WAVE59_GUARD_RC=", init_txt)
        self.assertIn("FX6_R73_WAVE59_GUARD_EXIT", init_txt)
        self.assertIn("poweroff -f", init_txt)

    def test_07_round73_overlay_r73c_integrated_runs_stage_b_big6(self) -> None:
        replacements, additions, meta = self.ov_c
        self.assertEqual(meta["r73"]["r73_mode"], "clean_unmount_wave59_reset_h0_h3_big6")
        r73_cfg = additions["etc/fx6_stage_r73"][0].decode("utf-8")
        self.assertIn("r73_mode=clean_unmount_wave59_reset_h0_h3_big6", r73_cfg)
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("/usr/bin/appfw-launch", init_txt)
        self.assertNotIn("--r73-wave59-guard", init_txt)

    def test_08_round73_overlay_disabled_when_enable_r73_false(self) -> None:
        _, additions, meta = self.ov_off
        self.assertFalse(meta["r73_enabled"])
        self.assertNotIn("etc/fx6_stage_r73", additions)
        self.assertNotIn("etc/fx6_r73_libjit.so", additions)
        self.assertNotIn("r73", meta)

    def test_09_round73_stage_a_c_source_contains_all_3_wave59_probes(self) -> None:
        for sym in (
            "setup_r73_big6_framing_interval_tc_ssh_fan_probe",
            "run_r73_wave59_guard_probe",
            "run_r73_clean_unmount_wave59_h0_h3_probe",
            "r73_wave59_camera_settings_reset",
            "r73_wave59_reset_network_settings",
            "r73_wave59_initialize",
            "r73_open_big6_home",
            "r73_configure_framing",
            "r73_configure_interval_shoot",
            "r73_trigger_interval_burst_write",
            "r73_configure_tc_and_hdmi",
            "r73_configure_access_auth_and_thermal",
            "FX6_R73_WAVE59_INIT",
            "FX6_R73_WAVE59_GUARD",
            "FX6_R73_CLEAN_UNMOUNT_WAVE59_H0_H3",
            "--r73-wave59-guard",
            "--r73-clean-unmount-wave59-h0-h3",
            "/etc/fx6_stage_r73",
        ):
            self.assertIn(sym, self.stage_a_src)

    def test_10_round73_shim_c_source_contains_r73_guarded_bridges(self) -> None:
        self.assertIn("#if FX6_ROUND >= 73", self.shim_src)
        for sym in (
            "FX6_R73_BIG6_HOME_FRAMING_DORMANT_BRIDGE",
            "FX6_R73_INTERVAL_SHOOT_9999_EROFS_BRIDGE",
            "FX6_R73_TC_MAKE_RUN_HDMI_4CH_BRIDGE",
            "FX6_R73_SSH_ACCESS_AUTH_FAN_TEMP_BRIDGE",
            "FX6_R73_LANG_TELEMETRY",
            "FX6_STAGE_B_R73_BRIDGE",
        ):
            self.assertIn(sym, self.shim_src)

    def test_11_round73_compile_launcher_and_shim_aarch64_elf_symbols(self) -> None:
        if self.launcher_r73 is None or self.shim_r73 is None:
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertEqual(self.launcher_r73[:4], b"\x7fELF")
        self.assertEqual(self.shim_r73[:4], b"\x7fELF")
        self.assertEqual(struct.unpack_from("<H", self.shim_r73, 18)[0], 183)
        self.assertIn(b"FX6_R73_BIG6_HOME_FRAMING_DORMANT_BRIDGE", self.shim_r73)
        self.assertIn(b"FX6_R73_INTERVAL_SHOOT_9999_EROFS_BRIDGE", self.shim_r73)
        self.assertIn(b"FX6_R73_TC_MAKE_RUN_HDMI_4CH_BRIDGE", self.shim_r73)
        self.assertIn(b"FX6_R73_SSH_ACCESS_AUTH_FAN_TEMP_BRIDGE", self.shim_r73)

    def test_12_round73_shim_round72_backward_compat_excludes_r73_bridges(self) -> None:
        if self.shim_r72 is None:
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertIn(b"FX6_R72_BRIGHT_MON_MAG_BRIGHTNESS_BRIDGE", self.shim_r72)
        self.assertNotIn(b"FX6_R73_BIG6_HOME_FRAMING_DORMANT_BRIDGE", self.shim_r72)

    def test_13_round73_parse_log_extracts_all_10_r73_prefixes_and_rc(self) -> None:
        serial_text = (
            "\n".join(
                [
                    "Linux version 4.9.337-scel+ (sony@fx3)",
                    "FX6_R73_WAVE59_INIT fx3_wave59_nodes_ok=1 uxc_tokens_ok=1 big6_framing_ok=1 interval_shoot_ok=1 tc_hdmi_ok=1 ssh_auth_fan_ok=1 emmc_write_count=0 r73_init_ok=1",
                    "FX6_R73_BIG6_HOME_FRAMING_DORMANT_BRIDGE big6_fixed_var_precond_home_lower_left_ok=1 manual_framing_rec_hdmi_vs_dormant_auto_framing_ok=1 big6_home_framing_dormant_ok=1 dormant_auto_framing_bypass_events=0 e_nd_actuator_tx_count=0 emmc_write_count=0 r73_bridge_ok=1",
                    "FX6_R73_INTERVAL_SHOOT_9999_EROFS_BRIDGE interval_shoot_7items_9999_eshutter_ok=1 fx3_still_seq_vs_fx6_mxf_interval_rec_ok=1 slot1_interval_burst_tier0_erofs30_ok=1 interval_shoot_9999_erofs_ok=1 slot1_avf_info_mutated=0 slot1_data_sector_writes=0 cnflasha_writes=0 emmc_write_count=0",
                    "FX6_R73_TC_MAKE_RUN_HDMI_4CH_BRIDGE tc_make_regen_recrun_vmc_ext_lk_ok=1 hdmi_rec_ctrl_tcout_on_and_4ch_audio_ok=1 tc_make_run_hdmi_4ch_ok=1 cnflasha_writes=0 emmc_write_count=0",
                    "FX6_R73_SSH_ACCESS_AUTH_FAN_TEMP_BRIDGE ssh_ptpip_access_auth_root_cert_zerorf_ok=1 fan_control_4mode_zero_max_auto_temp_ok=1 ssh_access_auth_fan_temp_ok=1 dormant_http_auth_bypass_events=0 dormant_fan_max_bypass_events=0 rf_tx_packets=0 wireless_tx_packets=0 cnflasha_writes=0 emmc_write_count=0",
                    "FX6_R73_LANG_TELEMETRY lang=schinese font_bank=23 str_bank=19 milestone_46th_realhw_138th_live_92_pngs=1 r73_bridge_ok=1",
                    "FX6_STAGE_B_R73_BRIDGE round=73 faithful=1 nop_count=0 milestone_46th_realhw_138th_live_92_pngs=1 emmc_write_count=0",
                    "FX6_R73_WAVE59_GUARD big6_no_fixvar_rc=-16 auto_framing_dormant_rc=-95 interval_slot1_burst_erofs_rc=-30 tc_clock_dormant_rc=-95 fan_max_dormant_rc=-95 airplane_rf_tx_rc=-100 r73b_ok=1",
                    "FX6_R73_WAVE59_GUARD_RC=0",
                    "FX6_R73_CLEAN_UNMOUNT_WAVE59_H0_H3 stock_unmount_restored_ok=1 camreset_preserves_wave59_survivors_ok=1 nwreset_clears_access_auth_preserves_airplane_ok=1 initialize_restores_wave59_defaults_ok=1 surfaces_h0_eq_h3=16 r73c_ok=1",
                ]
            )
            + "\n"
        )
        parsed = self.runner.extract_milestones(serial_text)
        r73_t = parsed["r73_telemetry"]
        self.assertEqual(r73_t["wave59_guard_rc"], 0)
        self.assertEqual(r73_t["wave59_init"]["big6_framing_ok"], 1)
        self.assertEqual(r73_t["big6_home_framing_dormant_bridge"]["big6_home_framing_dormant_ok"], 1)
        self.assertEqual(r73_t["interval_shoot_9999_erofs_bridge"]["interval_shoot_9999_erofs_ok"], 1)
        self.assertEqual(r73_t["tc_make_run_hdmi_4ch_bridge"]["tc_make_run_hdmi_4ch_ok"], 1)
        self.assertEqual(r73_t["ssh_access_auth_fan_temp_bridge"]["ssh_access_auth_fan_temp_ok"], 1)
        self.assertEqual(r73_t["lang_telemetry"]["lang"], "schinese")
        self.assertEqual(r73_t["lang_telemetry"]["milestone_46th_realhw_138th_live_92_pngs"], 1)
        self.assertEqual(r73_t["stage_b_bridge"]["round"], 73)
        self.assertEqual(r73_t["wave59_guard"]["r73b_ok"], 1)
        self.assertEqual(r73_t["clean_unmount_wave59_h0_h3"]["surfaces_h0_eq_h3"], 16)
        self.assertEqual(parsed["prefix_counts"]["FX6_R73_"], 9)

    def test_14_round73_parse_log_defaults_when_no_r73_lines_present(self) -> None:
        parsed = self.runner.extract_milestones("Linux version 4.9.337-scel+\n")
        self.assertIsNone(parsed["r73_telemetry"])
        self.assertEqual(parsed["prefix_counts"].get("FX6_R73_", 0), 0)

    def test_15_round73_runner_preserves_r72_prefix_and_uses_r73_stage_label(self) -> None:
        self.assertIn('if args.round >= 72:\n        tmp_prefix = "fx6-r72"', self.runner_src)
        self.assertIn('if args.round >= 73:\n        tmp_prefix = "fx6-r73"', self.runner_src)
        self.assertIn(
            "Milestone46RealHw138thLiveWave59Big6HomeFramingIntervalShootTcMakeSshAuthFanErofs",
            self.runner_src,
        )
        self.assertIn(", 64, 65, 66, 67, 68, 69, 70, 71, 72, 73]", self.runner_src)

    def test_16_round73_runner_portability_and_sanitizer_helper(self) -> None:
        self.assertIn('shutil.which("zig")', self.runner_src)
        self.assertIn("FX6_SCRATCH_DIR", self.runner_src)
        self.assertIn("def sanitize_round73_summary(", self.runner_src)
        self.assertNotIn("/usr/" + "bin/python3", self.runner_src)

    def test_17_round73_summary_json_top_level_schema_and_milestone_metadata(self) -> None:
        d = self.summary
        self.assertEqual(
            d["schema"],
            "fx6-on-fx3-round73-big6-home-framing-interval-tc-make-ssh-auth-fan-qemu-v1",
        )
        self.assertEqual(d["round"], 73)
        self.assertIn("46/46 Real-HW Rounds", d["milestone"])
        self.assertIn("138/138 Live Runs", d["milestone"])
        self.assertIn("92/92 PNGs <= 27,467 B", d["milestone"])
        self.assertEqual(d["date"], "2026-11-18")
        self.assertIn("4.9.337-scel+", d["kernel_version"])
        self.assertEqual(d["raw_firmware_bytes_leaked"], 0)

    def test_18_round73_summary_json_zero_host_path_and_scratch_leaks(self) -> None:
        for forbidden in (
            "/Users/",
            "/private/tmp/",
            "/var/folders/",
            "work/_scratch/",
            "work/_tests/",
            ":87" + "68",
        ):
            self.assertNotIn(forbidden, self.summary_raw)

    def test_19_round73_summary_audit_block_confirms_46_rounds_138_runs_92_pngs(self) -> None:
        audit = self.summary["r73_big6_framing_interval_tc_ssh_fan_erofs_audit"]
        self.assertEqual(audit["round"], 73)
        self.assertGreaterEqual(audit["realhw_rounds_count"], 46)
        self.assertGreaterEqual(audit["total_live_runs"], 138)
        self.assertGreaterEqual(audit["total_png_receipts"], 92)
        self.assertGreaterEqual(audit["milestone324_qemu_rounds"], 46)
        self.assertGreaterEqual(audit["milestone324_qemu_runs"], 138)
        self.assertGreaterEqual(audit["milestone324_png_receipts"], 92)
        self.assertEqual(audit["total_runs"], 3)
        for k, v in audit.items():
            if isinstance(v, bool):
                self.assertTrue(v, f"Expected audit boolean {k} to be True")

    def test_20_round73_all_3_runs_present_with_kernel_4_9_337_and_zero_crashes_writes(self) -> None:
        runs = self.summary["runs"]
        self.assertEqual(list(runs.keys()), list(self.EXPECTED_RUN_KEYS))
        for rk, rv in runs.items():
            self.assertEqual(rv["round"], 73, rk)
            self.assertIn("4.9.337-scel+", rv["kernel_version"], rk)
            self.assertEqual(rv["nop_count"], 0, rk)
            self.assertEqual(rv["crashes"], 0, rk)
            self.assertEqual(rv["emmc_write_count"], 0, rk)
            self.assertGreater(rv["wall_elapsed_sec"], 0.0, rk)

    def test_21_round73_r73a_pillar1_big6_home_and_manual_framing_vs_dormant_auto(self) -> None:
        init_t = self.summary["runs"][
            "r73a_big6_framing_interval_tc_make_ssh_auth_fan_big6_schinese"
        ]["r73_telemetry"]["wave59_init"]
        self.assertEqual(init_t["fx3_wave59_nodes_ok"], 1)
        self.assertEqual(init_t["uxc_tokens_ok"], 1)
        self.assertEqual(init_t["big6_framing_ok"], 1)
        self.assertEqual(init_t["big6_no_fixvar_rc"], -16)
        self.assertEqual(init_t["auto_framing_dormant_rc"], -95)
        self.assertEqual(init_t["fx6_auto_framing_dormant_rc"], -95)
        self.assertEqual(init_t["dormant_auto_framing_bypass_events"], 0)
        self.assertEqual(init_t["e_nd_actuator_tx_count"], 0)

    def test_22_round73_r73a_pillar2_interval_shoot_9999_vs_fx6_mxf_and_slot1_erofs30(self) -> None:
        init_t = self.summary["runs"][
            "r73a_big6_framing_interval_tc_make_ssh_auth_fan_big6_schinese"
        ]["r73_telemetry"]["wave59_init"]
        self.assertEqual(init_t["interval_shoot_ok"], 1)
        self.assertEqual(init_t["fx3_interval_rec_mxf_rc"], -2)
        self.assertEqual(init_t["interval_slot1_erofs_rc"], -30)
        self.assertEqual(init_t["interval_simult_erofs_rc"], -30)
        self.assertEqual(init_t["slot1_avf_info_mutated"], 0)
        self.assertEqual(init_t["slot1_data_sector_writes"], 0)

    def test_23_round73_r73a_pillar3_tc_make_run_regen_vmc_and_hdmi_rec_ctrl(self) -> None:
        init_t = self.summary["runs"][
            "r73a_big6_framing_interval_tc_make_ssh_auth_fan_big6_schinese"
        ]["r73_telemetry"]["wave59_init"]
        self.assertEqual(init_t["tc_hdmi_ok"], 1)
        self.assertEqual(init_t["tc_clock_dormant_rc"], -95)
        self.assertEqual(init_t["rec_ctrl_no_tcout_rc"], -16)

    def test_24_round73_r73a_pillar4_access_authen_ssh_4mode_fan_zero_max_and_vaults(self) -> None:
        init_t = self.summary["runs"][
            "r73a_big6_framing_interval_tc_make_ssh_auth_fan_big6_schinese"
        ]["r73_telemetry"]["wave59_init"]
        self.assertEqual(init_t["ssh_auth_fan_ok"], 1)
        self.assertEqual(init_t["removed_ipsec_rc"], -95)
        self.assertEqual(init_t["http_digest_dormant_rc"], -95)
        self.assertEqual(init_t["fan_max_dormant_rc"], -95)
        self.assertEqual(init_t["fx6_fan_max_dormant_rc"], -95)
        self.assertEqual(init_t["fx6_fan_always_off_dormant_rc"], -95)
        self.assertEqual(init_t["airplane_rf_blocked_rc"], -100)
        self.assertEqual(init_t["dormant_http_auth_bypass_events"], 0)
        self.assertEqual(init_t["dormant_fan_max_bypass_events"], 0)
        self.assertEqual(init_t["rf_tx_packets"], 0)
        self.assertEqual(init_t["wireless_tx_packets"], 0)
        self.assertEqual(init_t["passive_tx_bytes_emitted"], 0)
        self.assertEqual(init_t["p2_write_blocked_rc"], -30)
        self.assertEqual(init_t["p2_sha256_match"], 1)
        self.assertEqual(init_t["p12_sha256_match"], 1)
        self.assertEqual(init_t["cnflasha_sha256_match"], 1)
        self.assertEqual(init_t["slot1_vault_sha256_match"], 1)
        self.assertEqual(init_t["cnflasha_writes"], 0)
        self.assertEqual(init_t["appfw_present"], 1)
        self.assertEqual(init_t["shim_present"], 1)
        self.assertEqual(init_t["emmc_write_count"], 0)
        self.assertEqual(init_t["r73_init_ok"], 1)

    def test_25_round73_r73a_stage_b_schinese_lang_telemetry_and_bridge(self) -> None:
        r73a_t = self.summary["runs"][
            "r73a_big6_framing_interval_tc_make_ssh_auth_fan_big6_schinese"
        ]["r73_telemetry"]
        lt = r73a_t["lang_telemetry"]
        self.assertEqual(lt["lang"], "schinese")
        self.assertEqual(lt["bk4_lang_id"], "0x02cf019c")
        self.assertEqual(lt["bk4_lang_val"], "0x19")
        self.assertEqual(lt["lang_enum"], "0x2b45_CHINESE_SIMPLIFIED")
        self.assertEqual(lt["font_bank"], 23)
        self.assertEqual(lt["str_bank"], 19)
        self.assertEqual(lt["gpe_fb"], 0)
        self.assertEqual(lt["round73_46realhw_wave59_big6_framing_interval_tc_ssh_fan_erofs"], 1)
        self.assertEqual(lt["milestone_46th_realhw_138th_live_92_pngs"], 1)
        self.assertEqual(lt["dormant_auto_framing_bypass_events"], 0)
        self.assertEqual(lt["dormant_http_auth_bypass_events"], 0)
        self.assertEqual(lt["dormant_fan_max_bypass_events"], 0)
        self.assertEqual(lt["rf_tx_packets"], 0)
        self.assertEqual(lt["wireless_tx_packets"], 0)
        self.assertEqual(lt["slot1_avf_info_mutated"], 0)
        self.assertEqual(lt["slot1_data_sector_writes"], 0)
        self.assertEqual(lt["raw_firmware_bytes_leaked"], 0)

        sb = r73a_t["stage_b_bridge"]
        self.assertEqual(sb["round"], 73)
        self.assertEqual(sb["faithful"], 1)
        self.assertEqual(sb["nop_count"], 0)
        self.assertEqual(sb["big6_fixed_var_home_framing_vs_dormant_auto"], 1)
        self.assertEqual(sb["interval_shoot_9999_vs_fx6_mxf_erofs30"], 1)
        self.assertEqual(sb["reset_immune_tc_make_run_hdmi_recctrl_4ch"], 1)
        self.assertEqual(sb["ssh_access_auth_rootcert_4mode_fan_zeromax"], 1)
        self.assertEqual(sb["milestone_46th_realhw_138th_live_92_pngs"], 1)
        self.assertEqual(sb["dormant_auto_framing_bypass_events"], 0)
        self.assertEqual(sb["dormant_fan_max_bypass_events"], 0)

    def test_26_round73_r73a_stage_b_4_pillar_bridges_verified(self) -> None:
        r73a_t = self.summary["runs"][
            "r73a_big6_framing_interval_tc_make_ssh_auth_fan_big6_schinese"
        ]["r73_telemetry"]
        pb1 = r73a_t["big6_home_framing_dormant_bridge"]
        self.assertEqual(pb1["big6_fixed_var_precond_home_lower_left_ok"], 1)
        self.assertEqual(pb1["manual_framing_rec_hdmi_vs_dormant_auto_framing_ok"], 1)
        self.assertEqual(pb1["big6_home_framing_dormant_ok"], 1)
        self.assertEqual(pb1["dormant_auto_framing_bypass_events"], 0)
        self.assertEqual(pb1["e_nd_actuator_tx_count"], 0)
        self.assertEqual(pb1["r73_bridge_ok"], 1)

        pb2 = r73a_t["interval_shoot_9999_erofs_bridge"]
        self.assertEqual(pb2["interval_shoot_7items_9999_eshutter_ok"], 1)
        self.assertEqual(pb2["fx3_still_seq_vs_fx6_mxf_interval_rec_ok"], 1)
        self.assertEqual(pb2["slot1_interval_burst_tier0_erofs30_ok"], 1)
        self.assertEqual(pb2["interval_shoot_9999_erofs_ok"], 1)
        self.assertEqual(pb2["slot1_avf_info_mutated"], 0)
        self.assertEqual(pb2["slot1_data_sector_writes"], 0)

        pb3 = r73a_t["tc_make_run_hdmi_4ch_bridge"]
        self.assertEqual(pb3["tc_make_regen_recrun_vmc_ext_lk_ok"], 1)
        self.assertEqual(pb3["hdmi_rec_ctrl_tcout_on_and_4ch_audio_ok"], 1)
        self.assertEqual(pb3["tc_make_run_hdmi_4ch_ok"], 1)

        pb4 = r73a_t["ssh_access_auth_fan_temp_bridge"]
        self.assertEqual(pb4["ssh_ptpip_access_auth_root_cert_zerorf_ok"], 1)
        self.assertEqual(pb4["fan_control_4mode_zero_max_auto_temp_ok"], 1)
        self.assertEqual(pb4["ssh_access_auth_fan_temp_ok"], 1)
        self.assertEqual(pb4["dormant_http_auth_bypass_events"], 0)
        self.assertEqual(pb4["dormant_fan_max_bypass_events"], 0)
        self.assertEqual(pb4["rf_tx_packets"], 0)
        self.assertEqual(pb4["wireless_tx_packets"], 0)

    def test_27_round73_r73a_gpe0_readback_ge_300k_pixels_and_87_colors(self) -> None:
        r73a = self.summary["runs"][
            "r73a_big6_framing_interval_tc_make_ssh_auth_fan_big6_schinese"
        ]
        self.assertEqual(r73a["target_presenter"], "31procam_big6_menu_home_presenter")
        self.assertEqual(r73a["target_sid"], "0x0a")
        self.assertGreaterEqual(r73a["total_threads_seen"], 110)
        gpe0 = r73a["gpe0_readback"]
        self.assertTrue(gpe0["present"])
        self.assertEqual(gpe0["bytes"], 2211840)
        self.assertEqual(gpe0["total_pixels"], 552960)
        self.assertGreaterEqual(gpe0["nonzero_pixels"], 300000)
        self.assertEqual(gpe0["nonzero_pixels"], 346686)
        self.assertEqual(gpe0["unique_colors"], 87)

    def test_28_round73_r73a_stage_b_manifest_13_hashes_and_r73_metadata(self) -> None:
        sb = self.summary["runs"][
            "r73a_big6_framing_interval_tc_make_ssh_auth_fan_big6_schinese"
        ]["stage_b"]
        self.assertEqual(sb["manifest_count"], 13)
        self.assertEqual(len(sb["manifest_items"]), 13)
        for item in sb["manifest_items"]:
            self.assertEqual(len(item["sha256"]), 64)
        m = sb["r73"]
        self.assertEqual(m["r73_mode"], "big6_framing_interval_tc_make_ssh_auth_fan_big6")
        self.assertEqual(m["milestone_round_ordinal"], 73)
        self.assertEqual(m["realhw_round_ordinal"], 46)
        self.assertEqual(m["total_live_runs_at_completion"], 138)
        self.assertEqual(m["total_png_receipts_at_completion"], 92)
        bf = m["big6_home_and_manual_framing_wave59"]
        self.assertIn("Fixed/Variable", bf["mode_settings_precondition"])
        self.assertEqual(len(bf["big6_6_tiles"]), 6)
        self.assertIn("TYPE_EFRAMING_SUPPORT_TYPE_MANUAL_ONLY", bf["dormant_auto_framing"])
        iv = m["interval_shoot_func_vs_fx6_interval_rec"]
        self.assertEqual(len(iv["resettable_7_items"]), 7)
        self.assertEqual(len(iv["playback_pairing"]), 2)
        tc = m["timecode_make_run_and_hdmi_rec_control"]
        self.assertIn("Preset + Free Run", tc["vmc_bncm1_ext_lk"])
        self.assertIn("Reset-immune", tc["reset_immunity"])
        af = m["access_authen_and_fan_control"]
        self.assertEqual(af["ver700_removed_legacy_crypto"], ["WEP", "WPA-PSK", "Security(IPsec)"])
        self.assertEqual(len(af["fan_control_4modes"]), 4)
        self.assertIn("FAN_CONTROL_MAX has 0 hits on BOTH FX3 & FX6", af["fan_control_zero_max"])

    def test_29_round73_r73b_pillar1_big6_and_framing_guards(self) -> None:
        r73b_t = self.summary["runs"][
            "r73b_wave59_big6_framing_interval_tc_ssh_fan_erofs_guard"
        ]["r73_telemetry"]
        self.assertEqual(r73b_t["wave59_guard_rc"], 0)
        gd = r73b_t["wave59_guard"]
        self.assertEqual(gd["big6_no_fixvar_rc"], -16)
        self.assertEqual(gd["auto_framing_dormant_rc"], -95)
        self.assertEqual(gd["framing_100p_lock_rc"], -16)
        self.assertEqual(gd["framing_rec_lock_rc"], -16)
        self.assertEqual(gd["fx6_manual_framing_enoent_rc"], -2)
        self.assertEqual(gd["fx6_auto_framing_dormant_rc"], -95)
        self.assertEqual(gd["dormant_auto_framing_bypass_events"], 0)

    def test_30_round73_r73b_pillar2_interval_shoot_bounds_and_slot1_burst_erofs30(self) -> None:
        gd = self.summary["runs"][
            "r73b_wave59_big6_framing_interval_tc_ssh_fan_erofs_guard"
        ]["r73_telemetry"]["wave59_guard"]
        self.assertEqual(gd["interval_10000_oob_rc"], -22)
        self.assertEqual(gd["interval_61s_oob_rc"], -22)
        self.assertEqual(gd["interval_iauto_busy_rc"], -16)
        self.assertEqual(gd["fx3_interval_mxf_enoent_rc"], -2)
        self.assertEqual(gd["interval_slot1_burst_erofs_rc"], -30)
        self.assertEqual(gd["interval_simult_burst_erofs_rc"], -30)

    def test_31_round73_r73b_pillar3_tc_clock_vmc_invalid_and_hdmi_rec_ctrl_guards(self) -> None:
        gd = self.summary["runs"][
            "r73b_wave59_big6_framing_interval_tc_ssh_fan_erofs_guard"
        ]["r73_telemetry"]["wave59_guard"]
        self.assertEqual(gd["tc_clock_dormant_rc"], -95)
        self.assertEqual(gd["vmc_regen_invalid_rc"], -22)
        self.assertEqual(gd["vmc_recrun_invalid_rc"], -22)
        self.assertEqual(gd["hdmi_rec_ctrl_no_tcout_rc"], -16)
        self.assertEqual(gd["hdmi_rec_ctrl_sq_busy_rc"], -16)

    def test_32_round73_r73b_pillar4_dormant_crypto_fan_max_airplane_and_slot1_erofs_firewall(self) -> None:
        gd = self.summary["runs"][
            "r73b_wave59_big6_framing_interval_tc_ssh_fan_erofs_guard"
        ]["r73_telemetry"]["wave59_guard"]
        self.assertEqual(gd["wep_removed_rc"], -95)
        self.assertEqual(gd["ipsec_removed_rc"], -95)
        self.assertEqual(gd["http_digest_dormant_rc"], -95)
        self.assertEqual(gd["fan_max_dormant_rc"], -95)
        self.assertEqual(gd["airplane_rf_tx_rc"], -100)
        self.assertEqual(gd["fx6_fan_max_dormant_rc"], -95)
        self.assertEqual(gd["fx6_fan_always_off_rc"], -95)
        self.assertEqual(gd["slot1_wave59_erofs_rc"], -30)
        self.assertEqual(gd["slot1_avf_ro_blocked_rc"], -30)
        self.assertEqual(gd["p12_write_blocked_rc"], -30)
        self.assertEqual(gd["slot1_vault_sha256_match"], 1)
        self.assertEqual(gd["p2_write_blocked_rc"], -30)
        self.assertEqual(gd["cnflasha_ro_blocked_rc"], -30)
        self.assertEqual(gd["dormant_http_auth_bypass_events"], 0)
        self.assertEqual(gd["dormant_fan_max_bypass_events"], 0)
        self.assertEqual(gd["rf_tx_packets"], 0)
        self.assertEqual(gd["wireless_tx_packets"], 0)
        self.assertEqual(gd["slot1_avf_info_mutated"], 0)
        self.assertEqual(gd["slot1_data_sector_writes"], 0)
        self.assertEqual(gd["passive_tx_bytes_emitted"], 0)
        self.assertEqual(gd["e_nd_actuator_tx_count"], 0)
        self.assertEqual(gd["appfw_ok"], 1)
        self.assertEqual(gd["shim_elf_ok"], 1)
        self.assertEqual(gd["cnflasha_writes"], 0)
        self.assertEqual(gd["emmc_write_count"], 0)
        self.assertEqual(gd["r73b_ok"], 1)

    def test_33_round73_r73c_clean_unmount_and_wave59_3tier_asymmetric_reset(self) -> None:
        ci = self.summary["runs"][
            "r73c_clean_unmount_wave59_reset_h0_h3_big6_schinese"
        ]["r73_telemetry"]["clean_unmount_wave59_h0_h3"]
        self.assertEqual(ci["stock_unmount_restored_ok"], 1)
        self.assertEqual(ci["camreset_preserves_wave59_survivors_ok"], 1)
        self.assertEqual(ci["nwreset_clears_access_auth_preserves_airplane_ok"], 1)
        self.assertEqual(ci["initialize_restores_wave59_defaults_ok"], 1)
        self.assertEqual(ci["dormant_auto_framing_bypass_events"], 0)
        self.assertEqual(ci["dormant_http_auth_bypass_events"], 0)
        self.assertEqual(ci["dormant_fan_max_bypass_events"], 0)
        self.assertEqual(ci["rf_tx_packets"], 0)
        self.assertEqual(ci["wireless_tx_packets"], 0)
        self.assertEqual(ci["slot1_avf_info_mutated"], 0)
        self.assertEqual(ci["slot1_data_sector_writes"], 0)

    def test_34_round73_r73c_dlopen_and_16_h0_eq_h3_idempotent_unmount(self) -> None:
        ci = self.summary["runs"][
            "r73c_clean_unmount_wave59_reset_h0_h3_big6_schinese"
        ]["r73_telemetry"]["clean_unmount_wave59_h0_h3"]
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
        self.assertEqual(ci["e_nd_actuator_tx_count"], 0)
        self.assertEqual(ci["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(ci["emmc_write_count"], 0)
        self.assertEqual(ci["r73c_ok"], 1)

    def test_35_round73_r73c_integrated_renders_valid_big6_gpe0_readback(self) -> None:
        r73c = self.summary["runs"][
            "r73c_clean_unmount_wave59_reset_h0_h3_big6_schinese"
        ]
        self.assertEqual(r73c["target_presenter"], "31procam_big6_menu_home_presenter")
        self.assertEqual(r73c["target_sid"], "0x0a")
        gpe0 = r73c["gpe0_readback"]
        self.assertTrue(gpe0["present"])
        self.assertEqual(gpe0["bytes"], 2211840)
        self.assertEqual(gpe0["total_pixels"], 552960)
        self.assertGreaterEqual(gpe0["nonzero_pixels"], 300000)
        self.assertEqual(gpe0["nonzero_pixels"], 346686)
        self.assertEqual(gpe0["unique_colors"], 87)

    def test_36_round73_realhw_mechanisms_verified_7_blocks_match_run_telemetry(self) -> None:
        rm = self.summary["realhw_mechanisms_verified"]
        self.assertEqual(len(rm), 7)
        r73a = self.summary["runs"][
            "r73a_big6_framing_interval_tc_make_ssh_auth_fan_big6_schinese"
        ]["r73_telemetry"]
        r73b = self.summary["runs"][
            "r73b_wave59_big6_framing_interval_tc_ssh_fan_erofs_guard"
        ]["r73_telemetry"]
        r73c = self.summary["runs"][
            "r73c_clean_unmount_wave59_reset_h0_h3_big6_schinese"
        ]["r73_telemetry"]
        self.assertEqual(rm["wave59_big6_framing_interval_tc_ssh_fan_init"], r73a["wave59_init"])
        self.assertEqual(rm["big6_home_framing_dormant_stage_b_bridge"], r73a["big6_home_framing_dormant_bridge"])
        self.assertEqual(rm["interval_shoot_9999_erofs_stage_b_bridge"], r73a["interval_shoot_9999_erofs_bridge"])
        self.assertEqual(rm["tc_make_run_hdmi_4ch_stage_b_bridge"], r73a["tc_make_run_hdmi_4ch_bridge"])
        self.assertEqual(rm["ssh_access_auth_fan_temp_stage_b_bridge"], r73a["ssh_access_auth_fan_temp_bridge"])
        self.assertEqual(rm["wave59_fail_closed_guard"], r73b["wave59_guard"])
        self.assertEqual(rm["clean_unmount_wave59_reset_and_16_h0_h3"], r73c["clean_unmount_wave59_h0_h3"])

    def test_37_round73_reset_tiers_survival_consistent_across_runs(self) -> None:
        r73a_t = self.summary["runs"][
            "r73a_big6_framing_interval_tc_make_ssh_auth_fan_big6_schinese"
        ]["r73_telemetry"]
        r73c_ci = self.summary["runs"][
            "r73c_clean_unmount_wave59_reset_h0_h3_big6_schinese"
        ]["r73_telemetry"]["clean_unmount_wave59_h0_h3"]
        self.assertEqual(r73a_t["wave59_init"]["big6_framing_ok"], 1)
        self.assertEqual(r73a_t["wave59_init"]["ssh_auth_fan_ok"], 1)
        self.assertEqual(r73c_ci["stock_unmount_restored_ok"], 1)
        self.assertEqual(r73c_ci["camreset_preserves_wave59_survivors_ok"], 1)
        self.assertEqual(r73c_ci["nwreset_clears_access_auth_preserves_airplane_ok"], 1)
        self.assertEqual(r73c_ci["initialize_restores_wave59_defaults_ok"], 1)

    def test_38_round73_cross_round_consistency_with_r72_to_r66_slot1_ro_and_zero_leaks(self) -> None:
        self.assertEqual(self.r72_summary["round"], 72)
        self.assertEqual(self.r71_summary["round"], 71)
        self.assertEqual(self.r70_summary["round"], 70)
        self.assertEqual(self.r69_summary["round"], 69)
        self.assertEqual(self.r68_summary["round"], 68)
        self.assertEqual(self.r67_summary["round"], 67)
        self.assertEqual(self.r66_summary["round"], 66)
        r72b_gd = self.r72_summary["runs"][
            "r72b_wave58_bright_mon_shotmark_usblan_bulb_erofs_guard"
        ]["r72_telemetry"]["wave58_guard"]
        self.assertEqual(r72b_gd["slot1_wave58_erofs_rc"], -30)
        r73b_gd = self.summary["runs"][
            "r73b_wave59_big6_framing_interval_tc_ssh_fan_erofs_guard"
        ]["r73_telemetry"]["wave59_guard"]
        self.assertEqual(r73b_gd["interval_slot1_burst_erofs_rc"], -30)
        self.assertEqual(r73b_gd["interval_simult_burst_erofs_rc"], -30)
        self.assertEqual(r73b_gd["slot1_wave59_erofs_rc"], -30)
        self.assertEqual(r73b_gd["slot1_avf_ro_blocked_rc"], -30)
        self.assertEqual(r73b_gd["slot1_vault_sha256_match"], 1)
        self.assertEqual(r73b_gd["slot1_data_sector_writes"], 0)

    def test_39_round73_cross_round_consistency_with_r71_r65_zero_emmc_writes(self) -> None:
        self.assertEqual(self.r65_summary["round"], 65)
        self.assertEqual(
            self.r65_summary["runs"]["r65b_wave51_dci4k_aspect_camset_photocap_guard"]["r65_telemetry"]["wave51_guard"]["emmc_write_count"],
            0,
        )
        self.assertEqual(
            self.r71_summary["runs"]["r71b_wave57_steadyshot_selftimer_zebra_streaming_erofs_guard"]["r71_telemetry"]["wave57_guard"]["emmc_write_count"],
            0,
        )
        r73b_gd = self.summary["runs"][
            "r73b_wave59_big6_framing_interval_tc_ssh_fan_erofs_guard"
        ]["r73_telemetry"]["wave59_guard"]
        self.assertEqual(r73b_gd["emmc_write_count"], 0)
        self.assertEqual(r73b_gd["cnflasha_writes"], 0)

    def test_40_round73_cross_round_consistency_with_r72_16_h0_eq_h3(self) -> None:
        r72c = self.r72_summary["runs"][
            "r72c_clean_unmount_wave58_reset_h0_h3_big6_schinese"
        ]["r72_telemetry"]["clean_unmount_wave58_h0_h3"]
        self.assertEqual(r72c["surfaces_h0_eq_h3"], 16)
        r73c = self.summary["runs"][
            "r73c_clean_unmount_wave59_reset_h0_h3_big6_schinese"
        ]["r73_telemetry"]["clean_unmount_wave59_h0_h3"]
        self.assertEqual(r73c["surfaces_h0_eq_h3"], 16)
        self.assertEqual(r73c["drift_bits"], 0)

    def test_41_round73_unexecuted_physical_camera_bench_boundaries_documented(self) -> None:
        bounds = self.summary["unexecuted_physical_camera_bench_boundaries"]
        self.assertEqual(len(bounds), 3)
        joined = " ".join(bounds)
        self.assertIn("Fixed/Variable", joined)
        self.assertIn("Auto Framing", joined)
        self.assertIn("Interval Shoot Func.", joined)
        self.assertIn("Electronic Shutter", joined)
        self.assertIn("Slot-1", joined)
        self.assertIn("VMC-BNCM1", joined)
        self.assertIn("REC Control", joined)
        self.assertIn("OpenSSH", joined)
        self.assertIn("Fan Control", joined)
        self.assertIn("Auto Power OFF Temp.", joined)

    def test_42_round73_alpha_png_exists_le_27467b_and_matches_summary_sha256(self) -> None:
        pe = self.summary["runs"][
            "r73a_big6_framing_interval_tc_make_ssh_auth_fan_big6_schinese"
        ]["png_exports"]["alpha_png"]
        self.assertLessEqual(len(self.alpha_png_bytes), 27467)
        self.assertLess(len(self.alpha_png_bytes), 51200)
        self.assertEqual(len(self.alpha_png_bytes), pe["bytes"])
        self.assertEqual(
            hashlib.sha256(self.alpha_png_bytes).hexdigest(), pe["sha256"]
        )

    def test_43_round73_composited_png_exists_le_27467b_and_matches_summary_sha256(self) -> None:
        pe = self.summary["runs"][
            "r73a_big6_framing_interval_tc_make_ssh_auth_fan_big6_schinese"
        ]["png_exports"]["composited_png"]
        self.assertLessEqual(len(self.comp_png_bytes), 27467)
        self.assertLess(len(self.comp_png_bytes), 51200)
        self.assertEqual(len(self.comp_png_bytes), pe["bytes"])
        self.assertEqual(
            hashlib.sha256(self.comp_png_bytes).hexdigest(), pe["sha256"]
        )

    def test_44_round73_alpha_png_valid_1024x540_rgba_with_transparent_and_opaque_pixels(self) -> None:
        self.assertEqual(self.alpha_dims, (1024, 540))
        r73a = self.summary["runs"][
            "r73a_big6_framing_interval_tc_make_ssh_auth_fan_big6_schinese"
        ]
        r73a_nz = r73a["gpe0_readback"]["nonzero_pixels"]
        self.assertEqual(self.alpha_transparent, 552960 - r73a_nz)
        self.assertEqual(r73a["png_exports"]["transparent_pixels"], 207566)
        self.assertGreater(self.alpha_opaque, 300000)

    def test_45_round73_composited_png_valid_1024x540_rgba_100pct_opaque(self) -> None:
        self.assertEqual(self.comp_dims, (1024, 540))
        self.assertEqual(self.comp_opaque, 1024 * 540)

    def test_46_round73_report_readme_documents_all_3_runs_facts_inferences_and_zero_leaks(self) -> None:
        for token in (
            "Round 73",
            "Wave-59",
            "实测事实",
            "推断",
            "r73a",
            "r73b",
            "r73c",
            "46/46",
            "138/138",
            "92/92",
            "Fixed/Variable",
            "ND Filter",
            "Framing Settings",
            "Auto Framing",
            "Interval Shoot Func.",
            "Interval Rec",
            "Time Code Make",
            "Regenerate",
            "VMC-BNCM1",
            "REC Control",
            "4ch Audio Output",
            "Access Authen.",
            "MSGID_SSHD_START_CMD",
            "Import Root Certificate",
            "Fan Control",
            "Auto Power OFF Temp.",
            "Reset Network Set.",
            "EROFS=30",
            "Slot-1",
            "346,686",
            "27,132 B",
            "27,467 B",
            "r73a-big6-framing-interval-tc-ssh-fan-big6-schinese-alpha.png",
            "r73a-big6-framing-interval-tc-ssh-fan-big6-schinese-composited.png",
        ):
            self.assertIn(token, self.r73_readme)
        for forbidden in ("/Users/", "/private/tmp/", "/var/folders/", "work/_scratch/", ":87" + "68"):
            self.assertNotIn(forbidden, self.r73_readme)

    def test_47_round73_closure_readme_section_73_present_and_accurate(self) -> None:
        self.assertIn("## 73. Round 73", self.closure_readme)
        self.assertIn("46/46` Real-HW Rounds", self.closure_readme)
        self.assertIn("`138/138` Total", self.closure_readme)
        self.assertIn("`92/92` PNGs `<= 27,467 B`", self.closure_readme)
        self.assertIn(
            "2026-11-18-round73-big6-home-framing-interval-tc-make-ssh-auth-fan-qemu",
            self.closure_readme,
        )

    def test_48_round73_46_realhw_qemu_rounds_r28_to_r73_138_runs_and_92_pngs(self) -> None:
        png_total = 0
        rounds_found = 0
        for r in range(28, 74):
            matches = list((REPO_ROOT / "reports").glob(f"2026-??-??-round{r}-*"))
            self.assertEqual(len(matches), 1, f"Expected 1 report dir for Round {r}")
            pngs = list((matches[0] / "assets").glob("*.png"))
            self.assertGreaterEqual(len(pngs), 2, f"Expected >= 2 PNGs for Round {r}")
            for p in pngs:
                self.assertLessEqual(p.stat().st_size, 27467, str(p))
            png_total += len(pngs)
            rounds_found += 1
        self.assertGreaterEqual(rounds_found, 46)
        self.assertGreaterEqual(png_total, 92)
        audit = self.summary["r73_big6_framing_interval_tc_ssh_fan_erofs_audit"]
        self.assertGreaterEqual(audit["realhw_rounds_count"], 46)
        self.assertGreaterEqual(audit["total_live_runs"], 138)
        self.assertGreaterEqual(audit["total_png_receipts"], 92)

    def test_49_round73_dual_mode_clean_room_toggle_parity_on_summary(self) -> None:
        for clean_flag in ("0", "1"):
            with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                d = json.loads(self.summary_raw)
                self.assertEqual(d["round"], 73)
                self.assertEqual(
                    d["runs"][
                        "r73a_big6_framing_interval_tc_make_ssh_auth_fan_big6_schinese"
                    ]["r73_telemetry"]["big6_home_framing_dormant_bridge"]["big6_home_framing_dormant_ok"],
                    1,
                )
                self.assertEqual(
                    d["runs"][
                        "r73b_wave59_big6_framing_interval_tc_ssh_fan_erofs_guard"
                    ]["r73_telemetry"]["wave59_guard"]["interval_slot1_burst_erofs_rc"],
                    -30,
                )
                self.assertEqual(
                    d["runs"][
                        "r73c_clean_unmount_wave59_reset_h0_h3_big6_schinese"
                    ]["r73_telemetry"]["clean_unmount_wave59_h0_h3"]["surfaces_h0_eq_h3"],
                    16,
                )

    def test_50_round73_r73a_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"][
            "r73a_big6_framing_interval_tc_make_ssh_auth_fan_big6_schinese"
        ]["r73_telemetry"]["wave59_init"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_51_round73_r73b_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"][
            "r73b_wave59_big6_framing_interval_tc_ssh_fan_erofs_guard"
        ]["r73_telemetry"]["wave59_guard"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_52_round73_r73c_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"][
            "r73c_clean_unmount_wave59_reset_h0_h3_big6_schinese"
        ]["r73_telemetry"]["clean_unmount_wave59_h0_h3"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_53_round73_r73a_top_colors_transparent_plus_nonzero_equals_total_pixels(self) -> None:
        gpe = self.summary["runs"][
            "r73a_big6_framing_interval_tc_make_ssh_auth_fan_big6_schinese"
        ]["gpe0_readback"]
        color_map = {row["argb"]: row["pixels"] for row in gpe["top_colors"]}
        self.assertIn("0x00000000", color_map)
        self.assertIn("0xff000000", color_map)
        self.assertEqual(color_map["0x00000000"] + gpe["nonzero_pixels"], gpe["total_pixels"])

    def test_54_round73_r73c_top_colors_transparent_plus_nonzero_equals_total_pixels(self) -> None:
        gpe = self.summary["runs"][
            "r73c_clean_unmount_wave59_reset_h0_h3_big6_schinese"
        ]["gpe0_readback"]
        color_map = {row["argb"]: row["pixels"] for row in gpe["top_colors"]}
        self.assertIn("0x00000000", color_map)
        self.assertEqual(color_map["0x00000000"] + gpe["nonzero_pixels"], gpe["total_pixels"])

    def test_55_round73_r73a_and_r73c_wall_elapsed_and_duration_budget_sanity(self) -> None:
        r73a = self.summary["runs"][
            "r73a_big6_framing_interval_tc_make_ssh_auth_fan_big6_schinese"
        ]
        r73c = self.summary["runs"][
            "r73c_clean_unmount_wave59_reset_h0_h3_big6_schinese"
        ]
        ci_headroom = 15.0 if os.environ.get("GITHUB_ACTIONS") == "true" else 0.0
        max_wall = 240.0 + ci_headroom if os.environ.get("GITHUB_ACTIONS") == "true" else 120.0 + ci_headroom
        self.assertGreaterEqual(r73a["duration_budget_sec"], 70)
        self.assertLessEqual(r73a["duration_budget_sec"], 120)
        self.assertGreater(r73a["wall_elapsed_sec"], 50.0)
        self.assertLess(r73a["wall_elapsed_sec"], max_wall)
        self.assertGreaterEqual(r73c["duration_budget_sec"], 70)
        self.assertLessEqual(r73c["duration_budget_sec"], 120)
        self.assertGreater(r73c["wall_elapsed_sec"], 50.0)
        self.assertLess(r73c["wall_elapsed_sec"], max_wall)

    def test_56_round73_r73b_fast_early_exit_wall_elapsed_with_ci_headroom(self) -> None:
        r73b = self.summary["runs"][
            "r73b_wave59_big6_framing_interval_tc_ssh_fan_erofs_guard"
        ]
        ci_headroom = 15.0 if os.environ.get("GITHUB_ACTIONS") == "true" else 0.0
        max_b = 45.0 + ci_headroom if os.environ.get("GITHUB_ACTIONS") == "true" else 20.0 + ci_headroom
        self.assertEqual(r73b["duration_budget_sec"], 35)
        self.assertGreater(r73b["wall_elapsed_sec"], 1.0)
        self.assertLess(r73b["wall_elapsed_sec"], max_b)
        self.assertTrue(r73b["gpe0_readback"]["skipped_stock_fx3_mode"])

    def test_57_round73_faithful_invariants_preserved_across_all_3_runs(self) -> None:
        for rk, rv in self.summary["runs"].items():
            fi = rv["faithful_invariants"]
            self.assertEqual(fi["FX6_NATIVE_FAITHFUL"], 1, rk)
            self.assertEqual(fi["subst_color"], 0, rk)
            self.assertEqual(fi["subst_image"], 0, rk)
            self.assertEqual(fi["forced_render"], 0, rk)
            self.assertEqual(fi["skipped_node"], 0, rk)
            self.assertEqual(fi["lock_bypass"], 0, rk)

    def test_58_round73_all_3_runs_stage_b_manifest_count_13(self) -> None:
        for rk, rv in self.summary["runs"].items():
            self.assertEqual(rv["stage_b"]["manifest_count"], 13, rk)
            self.assertEqual(len(rv["stage_b"]["manifest_items"]), 13, rk)

    def test_59_round73_r73c_stage_b_r73_bridges_and_zero_leak_verified(self) -> None:
        r73c_t = self.summary["runs"][
            "r73c_clean_unmount_wave59_reset_h0_h3_big6_schinese"
        ]["r73_telemetry"]
        self.assertEqual(r73c_t["big6_home_framing_dormant_bridge"]["big6_home_framing_dormant_ok"], 1)
        self.assertEqual(r73c_t["interval_shoot_9999_erofs_bridge"]["interval_shoot_9999_erofs_ok"], 1)
        self.assertEqual(r73c_t["tc_make_run_hdmi_4ch_bridge"]["tc_make_run_hdmi_4ch_ok"], 1)
        self.assertEqual(r73c_t["ssh_access_auth_fan_temp_bridge"]["ssh_access_auth_fan_temp_ok"], 1)
        self.assertEqual(r73c_t["big6_home_framing_dormant_bridge"]["dormant_auto_framing_bypass_events"], 0)
        self.assertEqual(r73c_t["big6_home_framing_dormant_bridge"]["e_nd_actuator_tx_count"], 0)
        self.assertEqual(r73c_t["interval_shoot_9999_erofs_bridge"]["slot1_avf_info_mutated"], 0)
        self.assertEqual(r73c_t["interval_shoot_9999_erofs_bridge"]["slot1_data_sector_writes"], 0)
        self.assertEqual(r73c_t["ssh_access_auth_fan_temp_bridge"]["dormant_http_auth_bypass_events"], 0)
        self.assertEqual(r73c_t["ssh_access_auth_fan_temp_bridge"]["dormant_fan_max_bypass_events"], 0)
        self.assertEqual(r73c_t["ssh_access_auth_fan_temp_bridge"]["rf_tx_packets"], 0)
        self.assertEqual(r73c_t["ssh_access_auth_fan_temp_bridge"]["wireless_tx_packets"], 0)
        self.assertEqual(r73c_t["stage_b_bridge"]["e_nd_actuator_tx_count"], 0)

    def test_60_round73_all_3_runs_prefix_counts_include_fx6_r73(self) -> None:
        r73a_pc = self.summary["runs"][
            "r73a_big6_framing_interval_tc_make_ssh_auth_fan_big6_schinese"
        ]["prefix_counts"]
        r73b_pc = self.summary["runs"][
            "r73b_wave59_big6_framing_interval_tc_ssh_fan_erofs_guard"
        ]["prefix_counts"]
        r73c_pc = self.summary["runs"][
            "r73c_clean_unmount_wave59_reset_h0_h3_big6_schinese"
        ]["prefix_counts"]
        self.assertGreater(r73a_pc["FX6_R73_"], 10)
        self.assertEqual(r73b_pc["FX6_R73_"], 3)
        self.assertGreater(r73c_pc["FX6_R73_"], 10)

    def test_61_round73_r73_meta_invariants_across_all_3_runs(self) -> None:
        for rk, rv in self.summary["runs"].items():
            m = rv["stage_b"]["r73"]
            self.assertEqual(m["milestone_round_ordinal"], 73, rk)
            self.assertEqual(m["realhw_round_ordinal"], 46, rk)
            self.assertEqual(m["total_live_runs_at_completion"], 138, rk)
            self.assertEqual(m["total_png_receipts_at_completion"], 92, rk)
            self.assertEqual(m["dormant_auto_framing_bypass_events"], 0, rk)
            self.assertEqual(m["dormant_http_auth_bypass_events"], 0, rk)
            self.assertEqual(m["dormant_fan_max_bypass_events"], 0, rk)
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

    def test_62_round73_sanitize_helper_redacts_host_paths_and_reserved_port(self) -> None:
        dirty = {
            "run_id": "test-run",
            "lang": "schinese",
            "r73_mode": "big6_framing_interval_tc_make_ssh_auth_fan_big6",
            "kernel_version": "Linux version 4.9.337-scel+",
            "kernel_bin": "/Users/fake/secret/kernel.bin",
            "dtb_bin": "/Users/fake/secret/guest.dtb",
            "build": {"tmp_build": "/private/tmp/build-123"},
            "stage_b": {"r73": {"r73_mode": "big6_framing_interval_tc_make_ssh_auth_fan_big6"}},
            "r73_telemetry": {
                "wave59_init": {"r73_init_ok": 1},
                "wave59_guard": {"r73b_ok": 1},
                "clean_unmount_wave59_h0_h3": {"r73c_ok": 1, "surfaces_h0_eq_h3": 16},
            },
            "gpe0_readback": {"nonzero_pixels": 346686},
            "png_exports": {
                "alpha_png": {
                    "path": "/Users/kafu/repo/reports/2026-11-18-round73-big6-home-framing-interval-tc-make-ssh-auth-fan-qemu/assets/a.png"
                }
            },
            "prefix_counts": {"FX6_R73_": 10},
        }
        sanitized = self.runner.sanitize_round73_summary(dirty, dirty, dirty)
        raw = json.dumps(sanitized)
        self.assertNotIn("/Users/", raw)
        self.assertNotIn("/private/tmp/", raw)
        self.assertNotIn("kernel_bin", raw)
        self.assertNotIn("dtb_bin", raw)
        self.assertIn(
            "reports/2026-11-18-round73-big6-home-framing-interval-tc-make-ssh-auth-fan-qemu/assets/a.png",
            raw,
        )

    def test_63_round73_no_stray_temp_files_or_reserved_port_in_repo(self) -> None:
        for bad_name in ("tmp", "scratch", ".worktrees"):
            self.assertFalse((REPO_ROOT / bad_name).exists(), bad_name)
        reserved_port = "87" + "68"
        self.assertNotIn(reserved_port, self.summary_raw)
        self.assertNotIn(reserved_port, self.r73_readme)

    def test_64_round73_test_suite_contains_at_least_74_unit_tests(self) -> None:
        methods = [m for m in dir(self) if m.startswith("test_")]
        self.assertGreaterEqual(len(methods), 74)

    def test_65_round73_three_clean_env_modes_preserve_parity(self) -> None:
        for env_overrides in (
            {},
            {"FX3_CLEAN_ROOM_TEST": "1"},
            {"FX3_FX6_FORCE_CLEAN_ROOM": "1"},
        ):
            with mock.patch.dict(os.environ, env_overrides, clear=False):
                parsed = self.runner.extract_milestones(
                    "Linux version 4.9.337-scel+\n"
                    "FX6_R73_WAVE59_INIT big6_framing_ok=1 interval_shoot_ok=1 "
                    "tc_hdmi_ok=1 ssh_auth_fan_ok=1 r73_init_ok=1\n"
                )
                self.assertEqual(parsed["r73_telemetry"]["wave59_init"]["r73_init_ok"], 1)

    def test_66_round73_mocked_donorless_work_root_none_fallback_and_master_gate(self) -> None:
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
                self.assertGreaterEqual(report.qemu_rounds_verified, 46)
                self.assertGreaterEqual(report.qemu_runs_verified, 138)
                self.assertGreaterEqual(report.qemu_png_receipts_verified, 92)
        finally:
            for p in added:
                if p in sys.path:
                    sys.path.remove(p)

    def test_67_round73_argparse_percent_safe_help_and_no_hardcoded_python3(self) -> None:
        for line in self.runner_src.splitlines():
            if "help=" in line and "%" in line:
                stripped = line.replace("%%", "")
                self.assertNotIn("%", stripped, f"Unescaped '%' in argparse help: {line}")
        test_src = pathlib.Path(__file__).read_text(encoding="utf-8")
        forbidden_py = "/usr/" + "bin/python3"
        self.assertNotIn(forbidden_py, self.runner_src)
        self.assertNotIn(forbidden_py, test_src)

    def test_68_round73_all_92_milestone_pngs_under_27467b_and_clean_room_safe(self) -> None:
        assets_pngs = sorted(
            p for p in (REPO_ROOT / "reports").glob("2026-??-??-round*/assets/*.png")
            if int(p.parts[-3].split("-round")[1].split("-")[0]) >= 28
        )
        self.assertGreaterEqual(len(assets_pngs), 92)
        for p in assets_pngs:
            self.assertLessEqual(p.stat().st_size, 27467, str(p))

    def test_69_round73_cli_help_subprocess_smoke(self) -> None:
        res = subprocess.run(
            [sys.executable, "-B", str(CLOSURE_DIR / "build_and_run_round.py"), "--help"],
            capture_output=True,
            text=True,
            check=True,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        self.assertIn("--r73-mode", res.stdout)
        self.assertIn("big6_framing_interval_tc_make_ssh_auth_fan_big6", res.stdout)

    def test_70_round73_pillar1_big6_home_fixed_variable_and_manual_framing_vs_dormant_auto(self) -> None:
        r73a_meta = self.summary["runs"][
            "r73a_big6_framing_interval_tc_make_ssh_auth_fan_big6_schinese"
        ]["stage_b"]["r73"]
        bf = r73a_meta["big6_home_and_manual_framing_wave59"]
        self.assertIn("BKID_APP_setting_fps_fixed_variable_select", bf["mode_settings_precondition"])
        self.assertIn("[HOME] custom key (_f 0x7cad/0x7cb1)", bf["entry_methods"])
        self.assertEqual(bf["home_state_machine"], ["OFF", "ON_CURSOR_OFF", "ON_CURSOR_ON", "TEMP_OFF"])
        self.assertIn("update_big6_item_iso_ei", bf["big6_6_tiles"][1])
        self.assertIn("0 internal e-ND hardware", bf["big6_6_tiles"][3])
        self.assertIn("Recording/Streaming (Full def/Crop)", bf["manual_framing_settings"])
        self.assertIn("0 hits AUTO_FRAMING_AFR", bf["dormant_auto_framing"])

    def test_71_round73_pillar2_interval_shoot_func_7_items_9999_vs_fx6_mxf_and_erofs30(self) -> None:
        r73a_meta = self.summary["runs"][
            "r73a_big6_framing_interval_tc_make_ssh_auth_fan_big6_schinese"
        ]["stage_b"]["r73"]
        iv = r73a_meta["interval_shoot_func_vs_fx6_interval_rec"]
        self.assertIn("BKID_APP_setting_interval_shooting", iv["menu_path"])
        self.assertIn("Number of Shots (1..9999, def 30)", iv["resettable_7_items"])
        self.assertIn("Electronic Shutter [forced def]", iv["resettable_7_items"][5])
        self.assertIn("Display as Group (_f 0x6f26)", iv["playback_pairing"])
        self.assertIn("PB Speed for Interval (_f 0x72bd)", iv["playback_pairing"])
        self.assertIn("EROFS=30", iv["lockouts"])
        self.assertIn("single XAVC MXF clip", iv["fx6_diff"])

    def test_72_round73_pillar3_reset_immune_tc_make_run_vmc_and_hdmi_rec_control(self) -> None:
        r73a_meta = self.summary["runs"][
            "r73a_big6_framing_interval_tc_make_ssh_auth_fan_big6_schinese"
        ]["stage_b"]["r73"]
        tc = r73a_meta["timecode_make_run_and_hdmi_rec_control"]
        self.assertIn("NO Clock on FX3", tc["tc_make"])
        self.assertIn("Slot 1 in Simult. Recording", tc["regenerate_rule"])
        self.assertIn("Preset + Free Run", tc["vmc_bncm1_ext_lk"])
        self.assertIn("4ch Audio Output", tc["hdmi_output_settings"])
        self.assertIn("[Time Code Output]=On", tc["rec_control_rule"])
        self.assertIn("Off(HDMI Only)", tc["rec_control_rule"])
        self.assertIn("survive Camera Settings Reset", tc["reset_immunity"])

    def test_73_round73_pillar4_access_authen_ssh_rootcert_and_4mode_fan_zero_max(self) -> None:
        r73a_meta = self.summary["runs"][
            "r73a_big6_framing_interval_tc_make_ssh_auth_fan_big6_schinese"
        ]["stage_b"]["r73"]
        af = r73a_meta["access_authen_and_fan_control"]
        self.assertEqual(af["ver700_removed_legacy_crypto"], ["WEP", "WPA-PSK", "Security(IPsec)"])
        self.assertIn("SSH MSGID_SSHD_START_CMD + PTP-IP", af["active_crypto_and_auth"])
        self.assertIn("0 hits HTTP_DIGEST/BASIC_AUTH/HTTPS", af["active_crypto_and_auth"])
        self.assertIn("FTPS/RTMPS/Cloud TLS only", af["root_certificate"])
        self.assertEqual(af["fan_control_4modes"], ["Auto [def]", "Minimum", "Off in Rec", "Always Off"])
        self.assertIn("0 hits on BOTH FX3 & FX6", af["fan_control_zero_max"])
        self.assertIn("Standard [def] / High", af["auto_power_off_temp"])

    def test_74_round73_3tier_asymmetric_reset_matrix_across_c_summary_and_readmes(self) -> None:
        r73a_meta = self.summary["runs"][
            "r73a_big6_framing_interval_tc_make_ssh_auth_fan_big6_schinese"
        ]["stage_b"]["r73"]
        rt = r73a_meta["reset_tiers"]
        self.assertIn("Mode Settings", rt["camera_settings_reset"])
        self.assertIn("Interval Shoot Func.", rt["camera_settings_reset"])
        self.assertIn("Reset-immune TC Make/Run", rt["camera_settings_reset"])
        self.assertIn("Clears Access Authen. Settings", rt["reset_network_settings"])
        self.assertIn("Airplane Mode = On", rt["reset_network_settings"])
        self.assertIn("Airplane Mode = On", rt["initialize"])
        self.assertIn("r73_wave59_camera_settings_reset", self.stage_a_src)
        self.assertIn("r73_wave59_reset_network_settings", self.stage_a_src)
        self.assertIn("r73_wave59_initialize", self.stage_a_src)
        self.assertIn("Reset Network Set.", self.r73_readme)
        self.assertIn("Reset Network Set.", self.closure_readme)

    def test_75_round73_wave59_uxc_and_node_tokens_wired_in_stage_a_source(self) -> None:
        for sym in (
            "r73_lookup_wave59_menu_node",
            "r73_lookup_uxc_token",
            "_f:0x7d0d:Fixed/Variable",
            "_f:0x7cad:HOME",
            "_f:0x7cb1:Open Home Screen",
            "_f:0x7ce3:Home (Lower Left)",
            "_f:0x7cdd:Swipe Down Home",
            "_f:0x643e:Select LUT",
            "_f:0x78ce:Base ISO",
            "_f:0x7d18:Framing Settings",
            "_f:0x7d13:Recording/Streaming",
            "_f:0x7d0f:HDMI",
            "_f:0x7d1e:Switch Framing",
            "_f:0x7d25:Framing Stop (Full)",
            "_f:0x7027:Interval Shoot Func.",
            "_f:0x6b0a:Shooting Start Time",
            "_f:0x624c:Shooting Interval",
            "_f:0x71dd:Number of Shots",
            "_f:0x615b:AE Tracking Sensitivity",
            "_f:0x74c0:Shutter Type in Interval",
            "_f:0x6f69:Shoot Interval Priority",
            "_f:0x6f26:Display as Group",
            "_f:0x72bd:PB Speed for Interval",
            "_f:0x6b79:Time Code Make",
            "_f:0x7313:Time Code Run",
            "_f:0x6144:Rec. Media dur HDMI Output",
            "_f:0x72af:Time Code Output",
            "_f:0x76e1:REC Control",
            "_f:0x6aa0:4ch Audio Output",
            "_f:0x7ada:Access Authen. Settings",
            "_f:0x6b2b:Access Authen. Info",
            "_f:0x7940:Import Root Certificate",
            "_f:0x6e77:Fan Control",
            "_f:0x6811:Always Off",
            "_f:0x70f1:Auto Power OFF Temp.",
            "_f:0x6be6:Auto Framing Settings",
            "_f:0x79bc:Auto Framing",
            "_f:0x69aa:Security(IPsec)",
            "dormant:FAN_CONTROL_MAX",
        ):
            self.assertIn(sym, self.stage_a_src)

    def test_76_round73_clean_unmount_checks_stock_restoration_and_zero_emmc(self) -> None:
        ci = self.summary["runs"][
            "r73c_clean_unmount_wave59_reset_h0_h3_big6_schinese"
        ]["r73_telemetry"]["clean_unmount_wave59_h0_h3"]
        self.assertEqual(ci["stock_unmount_restored_ok"], 1)
        self.assertEqual(ci["dlopen_ok"], 1)
        self.assertEqual(ci["surfaces_h0_eq_h3"], 16)
        self.assertEqual(ci["drift_bits"], 0)
        self.assertEqual(ci["emmc_write_count"], 0)
        self.assertEqual(ci["cnflasha_write_bytes"], 0)


if __name__ == "__main__":
    unittest.main()
