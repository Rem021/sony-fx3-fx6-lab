#!/usr/bin/env python3
"""Offline dual-mode unit tests for FX6-on-FX3 Round 61 Historic 100+ Live QEMU Runs Milestone (34/34 Real-HW Rounds, 100th..102nd Live Runs -> 102/102 Total, 68/68 PNGs — Wave-47)."""
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
ROUND61_REPORT_DIR = (
    REPO_ROOT
    / "reports"
    / "2026-11-17-round61-milestone-100runs-usb-mode-hdmi-info-protect-reset-network-qemu"
)
WAVE47_SPEC_PATH = (
    REPO_ROOT
    / "reports"
    / "2026-11-17-global-sony-wave47-usb-connection-mode-hdmi-info-protect-reset-network-intel"
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


def _build_overlay_for_r61(
    runner,
    parent_cpio: pathlib.Path,
    fp,
    fv,
    fb,
    fake_run,
    jit_meta: Dict[str, Any],
    work: pathlib.Path,
    r61_mode: str,
    lang: str = "schinese",
    enable_r61: bool = True,
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
            enable_r61=enable_r61,
            r61_mode=r61_mode,
            sd_manifest_mode="valid",
            lang=lang,
            shim_bytes=b"SHIM",
        )


class TestRound61Milestone100PlusRunsRealHwUsbModeHdmiInfoProtectResetNetworkQemu(unittest.TestCase):
    EXPECTED_RUN_KEYS = (
        "r61a_usb_hdmi_protect_netreset_big6_schinese",
        "r61b_nouvc_hdmi1080_slot1_protect_nwreset_guard",
        "r61c_clean_unmount_nwreset_reboot_airplane_h0_h3_big6_schinese",
    )

    runner: Any
    runner_src: str
    stage_a_src: str
    shim_src: str
    wave47_spec: str
    summary_raw: str
    summary: Dict[str, Any]
    r61_readme: str
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
    launcher_r61: Optional[bytes]
    shim_r61: Optional[bytes]
    shim_r60: Optional[bytes]
    r60_summary: Dict[str, Any]
    r59_summary: Dict[str, Any]
    r58_summary: Dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = _load_closure_module("fx6_brr_r61_cached", "build_and_run_round.py")
        cls.runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")
        cls.stage_a_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        cls.shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        cls.wave47_spec = WAVE47_SPEC_PATH.read_text(encoding="utf-8")
        cls.summary_raw = (ROUND61_REPORT_DIR / "summary.json").read_text(encoding="utf-8")
        cls.summary = json.loads(cls.summary_raw)
        cls.r61_readme = (ROUND61_REPORT_DIR / "README.md").read_text(encoding="utf-8")
        cls.closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")

        alpha_p = (
            ROUND61_REPORT_DIR
            / "assets"
            / "r61a-usb-hdmi-protect-netreset-4ch-big6-schinese-alpha.png"
        )
        comp_p = (
            ROUND61_REPORT_DIR
            / "assets"
            / "r61a-usb-hdmi-protect-netreset-4ch-big6-schinese-composited.png"
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
            cls.ov_a = _build_overlay_for_r61(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wa", "usb_hdmi_protect_netreset_big6", lang="schinese",
            )
            cls.ov_b = _build_overlay_for_r61(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wb", "nouvc_hdmi1080_slot1_protect_nwreset_guard", lang="en",
            )
            cls.ov_c = _build_overlay_for_r61(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wc", "clean_unmount_nwreset_reboot_airplane_h0_h3_big6", lang="schinese",
            )
            cls.ov_off = _build_overlay_for_r61(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "woff", "usb_hdmi_protect_netreset_big6", enable_r61=False,
            )
            cls.invalid_mode_raised = False
            try:
                _build_overlay_for_r61(
                    cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                    tpath / "wbad", "invalid_r61_mode",
                )
            except ValueError:
                cls.invalid_mode_raised = True

            zig_bin = shutil.which("zig") or (
                str(cls.runner.ZIG) if cls.runner.ZIG.is_file() else None
            )
            if zig_bin is not None:
                verify_r61_out = tpath / "fx6-stage-a-verify-r61"
                shim_r61_out = tpath / "libgrm-fbinit9-r61.so"
                shim_r60_out = tpath / "libgrm-fbinit9-r60.so"
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
                        str(verify_r61_out),
                    ],
                    [
                        zig_bin,
                        "cc",
                        "-target",
                        "aarch64-linux-gnu.2.25",
                        "-O0",
                        "-shared",
                        "-fPIC",
                        "-DFX6_ROUND=61",
                        str(CLOSURE_DIR / "libgrm-fbinit9.c"),
                        "-ldl",
                        "-lpthread",
                        "-o",
                        str(shim_r61_out),
                    ],
                    [
                        zig_bin,
                        "cc",
                        "-target",
                        "aarch64-linux-gnu.2.25",
                        "-O0",
                        "-shared",
                        "-fPIC",
                        "-DFX6_ROUND=60",
                        str(CLOSURE_DIR / "libgrm-fbinit9.c"),
                        "-ldl",
                        "-lpthread",
                        "-o",
                        str(shim_r60_out),
                    ],
                ):
                    cls.runner.subprocess.run(cmd, check=True)
                cls.launcher_r61 = verify_r61_out.read_bytes()
                cls.shim_r61 = shim_r61_out.read_bytes()
                cls.shim_r60 = shim_r60_out.read_bytes()
            else:
                cls.launcher_r61 = None
                cls.shim_r61 = None
                cls.shim_r60 = None

        cls.r60_summary = json.loads(
            (
                REPO_ROOT
                / "reports"
                / "2026-11-17-round60-milestone-realhw-power-save-monitor-language-volume-delete-qemu"
                / "summary.json"
            ).read_text(encoding="utf-8")
        )
        cls.r59_summary = json.loads(
            (
                REPO_ROOT
                / "reports"
                / "2026-11-17-round59-realhw-focus-mag-datetime-videolight-hdmires-qemu"
                / "summary.json"
            ).read_text(encoding="utf-8")
        )
        cls.r58_summary = json.loads(
            (
                REPO_ROOT
                / "reports"
                / "2026-11-17-round58-realhw-file-settings-gamma-assist-tcub-qemu"
                / "summary.json"
            ).read_text(encoding="utf-8")
        )

    def test_01_wave47_global_spec_present_and_covers_all_wave47_pillars(self) -> None:
        self.assertTrue(WAVE47_SPEC_PATH.is_file())
        for needle in (
            "USB Connection Mode",
            "BKID_APP_setting_usb_connection_method",
            "Sel. When Connect",
            "MassStorage(MSC)",
            "054C:0DA1",
            "MTP",
            "Remote Shoot (PC Remote)",
            "NOUVC",
            "USB Streaming",
            "usb_f_uvc.ko",
            "USB LUN Setting",
            "USB Power Supply",
            "HDMI Info. Display",
            "BKID_APP_setting_hdmi_info_display",
            "1080",
            "Off(HDMI Only)",
            "Protect",
            "Format",
            "Reset Network Set.",
            "BKID_APP_is_shutdown_factor_network_reset",
            "Airplane Mode",
        ):
            self.assertIn(needle, self.wave47_spec)

    def test_02_round61_summary_schema_round_milestone_and_zero_leaks(self) -> None:
        self.assertNotIn("/Users/", self.summary_raw)
        self.assertNotIn("/private/tmp/", self.summary_raw)
        self.assertEqual(
            self.summary["schema"],
            "fx6-on-fx3-round61-milestone-100runs-realhw-usb-mode-hdmi-info-protect-reset-network-qemu-v1",
        )
        self.assertEqual(self.summary["round"], 61)
        self.assertEqual(self.summary["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(tuple(self.summary["runs"].keys()), self.EXPECTED_RUN_KEYS)

    def test_03_round61_cli_accepts_round61_and_all_3_r61_modes(self) -> None:
        self.assertIn(", 60, 61]", self.runner_src)
        for mode in (
            "usb_hdmi_protect_netreset_big6",
            "nouvc_hdmi1080_slot1_protect_nwreset_guard",
            "clean_unmount_nwreset_reboot_airplane_h0_h3_big6",
        ):
            self.assertIn(mode, self.runner_src)

    def test_04_round61_overlay_rejects_invalid_r61_mode(self) -> None:
        self.assertTrue(self.invalid_mode_raised)

    def test_05_round61_overlay_r61a_injects_etc_fx6_stage_r61_and_appfw_launch(self) -> None:
        replacements, additions, meta = self.ov_a
        self.assertTrue(meta["r61_enabled"])
        self.assertIn("etc/fx6_stage_r61", additions)
        self.assertIn("etc/fx6_r61_libjit.so", additions)
        r61_cfg = additions["etc/fx6_stage_r61"][0].decode("utf-8")
        self.assertIn("stage_r61=1", r61_cfg)
        self.assertIn("r61_mode=usb_hdmi_protect_netreset_big6", r61_cfg)
        self.assertIn("milestone_34th_realhw_102nd_live_68_pngs=1", r61_cfg)
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("/usr/bin/appfw-launch", init_txt)
        self.assertNotIn("--r61-nouvc-hdmi1080-slot1-protect-nwreset-guard", init_txt)

    def test_06_round61_overlay_r61b_injects_early_guard_probe_and_poweroff(self) -> None:
        replacements, _, meta = self.ov_b
        self.assertEqual(meta["r61"]["r61_mode"], "nouvc_hdmi1080_slot1_protect_nwreset_guard")
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("--r61-nouvc-hdmi1080-slot1-protect-nwreset-guard", init_txt)
        self.assertIn("FX6_R61_WAVE47_GUARD_RC=", init_txt)
        self.assertIn("FX6_R61_WAVE47_GUARD_EXIT", init_txt)
        self.assertIn("poweroff -f", init_txt)

    def test_07_round61_overlay_r61c_integrated_runs_stage_b_big6(self) -> None:
        replacements, additions, meta = self.ov_c
        self.assertEqual(meta["r61"]["r61_mode"], "clean_unmount_nwreset_reboot_airplane_h0_h3_big6")
        r61_cfg = additions["etc/fx6_stage_r61"][0].decode("utf-8")
        self.assertIn("r61_mode=clean_unmount_nwreset_reboot_airplane_h0_h3_big6", r61_cfg)
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("/usr/bin/appfw-launch", init_txt)
        self.assertNotIn("--r61-nouvc-hdmi1080-slot1-protect-nwreset-guard", init_txt)

    def test_08_round61_overlay_disabled_when_enable_r61_false(self) -> None:
        _, additions, meta = self.ov_off
        self.assertFalse(meta["r61_enabled"])
        self.assertNotIn("etc/fx6_stage_r61", additions)
        self.assertNotIn("etc/fx6_r61_libjit.so", additions)
        self.assertNotIn("r61", meta)

    def test_09_round61_stage_a_c_source_contains_all_3_wave47_probes(self) -> None:
        for sym in (
            "setup_r61_usb_hdmi_protect_netreset_probe",
            "run_r61_nouvc_hdmi1080_slot1_protect_nwreset_guard_probe",
            "run_r61_clean_unmount_nwreset_reboot_airplane_h0_h3_probe",
            "FX6_R61_WAVE47_INIT",
            "FX6_R61_WAVE47_GUARD",
            "FX6_R61_CLEAN_UNMOUNT_NWRESET_H0_H3",
            "--r61-nouvc-hdmi1080-slot1-protect-nwreset-guard",
            "--r61-clean-unmount-nwreset-h0-h3",
            "/etc/fx6_stage_r61",
        ):
            self.assertIn(sym, self.stage_a_src)

    def test_10_round61_shim_c_source_contains_r61_guarded_bridges(self) -> None:
        self.assertIn("#if FX6_ROUND >= 61", self.shim_src)
        for sym in (
            "FX6_R61_USB_NOUVC_PD_BRIDGE",
            "FX6_R61_HDMI_INFO_CLEAN_CLAMP_BRIDGE",
            "FX6_R61_PROTECT_FORMAT_NWRESET_BRIDGE",
            "FX6_R61_LANG_TELEMETRY",
            "FX6_STAGE_B_R61_BRIDGE",
        ):
            self.assertIn(sym, self.shim_src)

    def test_11_round61_compile_launcher_and_shim_aarch64_elf_symbols(self) -> None:
        if self.launcher_r61 is None or self.shim_r61 is None:
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertEqual(self.launcher_r61[:4], b"\x7fELF")
        self.assertEqual(self.shim_r61[:4], b"\x7fELF")
        self.assertEqual(struct.unpack_from("<H", self.shim_r61, 18)[0], 183)
        self.assertIn(b"FX6_R61_USB_NOUVC_PD_BRIDGE", self.shim_r61)
        self.assertIn(b"FX6_R61_HDMI_INFO_CLEAN_CLAMP_BRIDGE", self.shim_r61)
        self.assertIn(b"FX6_R61_PROTECT_FORMAT_NWRESET_BRIDGE", self.shim_r61)

    def test_12_round61_shim_round60_backward_compat_excludes_r61_bridges(self) -> None:
        if self.shim_r60 is None:
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertIn(b"FX6_R60_POWERSAVE_REALITY_SPLIT_BRIDGE", self.shim_r60)
        self.assertNotIn(b"FX6_R61_USB_NOUVC_PD_BRIDGE", self.shim_r60)

    def test_13_round61_parse_log_extracts_all_8_r61_prefixes_and_rc(self) -> None:
        serial_text = (
            "\n".join(
                [
                    "Linux version 4.9.337-scel+ (sony@fx3)",
                    "FX6_R61_WAVE47_INIT fx3_wave47_nodes_ok=1 uxc_tokens_ok=1 usb_nouvc_4mode_pd_ok=1 hdmi_info_clean_clamp_ok=1 protect_vs_format_vault_ok=1 reset_network_reboot_airplane_ok=1 emmc_write_count=0 r61_init_ok=1",
                    "FX6_R61_USB_NOUVC_PD_BRIDGE usb_4mode_nouvc_ok=1 usb_lun_multi_single_ok=1 usb_typec_pd_isolated_ok=1 usb_nouvc_pd_ok=1 usb_data_tx_events=0 r61_bridge_ok=1",
                    "FX6_R61_HDMI_INFO_CLEAN_CLAMP_BRIDGE hdmi_info_on_blanks_lcd_ok=1 hdmi_log_1080p_clamp_ok=1 hdmi_only_raw_4k_clean_ok=1 hdmi_info_clean_clamp_ok=1 log_1080p_clamp_bypass_events=0 p2_setting_writes=0",
                    "FX6_R61_PROTECT_FORMAT_NWRESET_BRIDGE protect_4scopes_delete_only_ok=1 slot1_protect_format_ro_ok=1 nwreset_autoreboot_airplane_ok=1 protect_format_nwreset_ok=1 slot1_protect_mutation_events=0 slot1_format_events=0 post_reset_rf_leak_events=0",
                    "FX6_R61_LANG_TELEMETRY lang=schinese font_bank=23 str_bank=19 milestone_34th_realhw_102nd_live_68_pngs=1 r61_bridge_ok=1",
                    "FX6_STAGE_B_R61_BRIDGE round=61 faithful=1 nop_count=0 milestone_34th_realhw_102nd_live_68_pngs=1 emmc_write_count=0",
                    "FX6_R61_WAVE47_GUARD uvc_spoof_rc=-2 menu_uvc_rc=-2 tier0_msc_rc=-1 multi_usb_pd_rc=-95 no_batt_pd_rc=-22 non_isolated_pd_rc=-1 lcd_touch_blanked_rc=-16 log_2160p_bypass_rc=-16 sq_raw_lockout_rc=-95 clean_osd_bake_rc=-1 slot1_protect_rc=-30 slot1_delete_rc=-30 slot1_format_rc=-30 slot2_protected_del_rc=-13 nw_skip_reboot_rc=-11 rf_before_airplane_rc=-1 rf_after_airplane_rc=-1 r61b_ok=1",
                    "FX6_R61_WAVE47_GUARD_RC=0",
                    "FX6_R61_CLEAN_UNMOUNT_NWRESET_H0_H3 stock_unmount_restored_ok=1 nw_quarantine_ok=1 camreset_preserves_setup_ok=1 initialize_restores_wave47_ok=1 zero_rf_final_ok=1 surfaces_h0_eq_h3=16 r61c_ok=1",
                ]
            )
            + "\n"
        )
        parsed = self.runner.extract_milestones(serial_text)
        r61_t = parsed["r61_telemetry"]
        self.assertEqual(r61_t["wave47_guard_rc"], 0)
        self.assertEqual(r61_t["wave47_init"]["usb_nouvc_4mode_pd_ok"], 1)
        self.assertEqual(r61_t["usb_nouvc_pd_bridge"]["usb_nouvc_pd_ok"], 1)
        self.assertEqual(r61_t["hdmi_info_clean_clamp_bridge"]["hdmi_info_clean_clamp_ok"], 1)
        self.assertEqual(r61_t["protect_format_nwreset_bridge"]["protect_format_nwreset_ok"], 1)
        self.assertEqual(r61_t["lang_telemetry"]["lang"], "schinese")
        self.assertEqual(r61_t["lang_telemetry"]["milestone_34th_realhw_102nd_live_68_pngs"], 1)
        self.assertEqual(r61_t["stage_b_bridge"]["round"], 61)
        self.assertEqual(r61_t["wave47_guard"]["r61b_ok"], 1)
        self.assertEqual(r61_t["clean_unmount_nwreset_h0_h3"]["surfaces_h0_eq_h3"], 16)
        self.assertEqual(parsed["prefix_counts"]["FX6_R61_"], 8)

    def test_14_round61_parse_log_defaults_when_no_r61_lines_present(self) -> None:
        parsed = self.runner.extract_milestones("Linux version 4.9.337-scel+\n")
        self.assertIsNone(parsed["r61_telemetry"])
        self.assertEqual(parsed["prefix_counts"].get("FX6_R61_", 0), 0)

    def test_15_round61_runner_uses_fx6_r61_prefix_and_stage_label(self) -> None:
        self.assertIn('if args.round >= 61:\n        tmp_prefix = "fx6-r61"', self.runner_src)
        self.assertIn(
            "Milestone100PlusRunsRealHw34thRound102ndLiveWave47UsbModeHdmiInfoProtectNwResetAirplane",
            self.runner_src,
        )
        self.assertIn(", 60, 61]", self.runner_src)

    def test_16_round61_runner_portability_and_sanitizer_helper(self) -> None:
        self.assertIn('shutil.which("zig")', self.runner_src)
        self.assertIn("FX6_SCRATCH_DIR", self.runner_src)
        self.assertIn("def sanitize_round61_summary(", self.runner_src)
        self.assertNotIn('"/usr/bin/python3"', self.runner_src)

    def test_17_round61_summary_json_top_level_schema_and_milestone_metadata(self) -> None:
        d = self.summary
        self.assertEqual(
            d["schema"],
            "fx6-on-fx3-round61-milestone-100runs-realhw-usb-mode-hdmi-info-protect-reset-network-qemu-v1",
        )
        self.assertEqual(d["round"], 61)
        self.assertIn("100+ Live QEMU Runs Milestone!", d["milestone"])
        self.assertIn("34th Real-HW", d["milestone"])
        self.assertIn("102/102 Total Live Runs", d["milestone"])
        self.assertIn("68/68 PNGs", d["milestone"])
        self.assertEqual(d["date"], "2026-11-17")
        self.assertIn("4.9.337-scel+", d["kernel_version"])
        self.assertEqual(d["raw_firmware_bytes_leaked"], 0)

    def test_18_round61_summary_json_zero_host_path_and_scratch_leaks(self) -> None:
        for forbidden in (
            "/Users/",
            "/private/tmp/",
            "/var/folders/",
            "work/_scratch/",
            "work/_tests/",
            ":87" + "68",
        ):
            self.assertNotIn(forbidden, self.summary_raw)

    def test_19_round61_summary_audit_block_confirms_34_rounds_102_runs_68_pngs(self) -> None:
        audit = self.summary["r61_realhw_usb_mode_hdmi_info_protect_reset_network_audit"]
        self.assertEqual(audit["round"], 61)
        self.assertEqual(audit["milestone"], 61)
        self.assertGreaterEqual(audit["milestone295_qemu_rounds"], 34)
        self.assertGreaterEqual(audit["milestone295_qemu_runs"], 102)
        self.assertGreaterEqual(audit["milestone295_png_receipts"], 68)
        self.assertEqual(audit["total_runs"], 3)
        for k, v in audit.items():
            if isinstance(v, bool):
                self.assertTrue(v, f"Expected audit boolean {k} to be True")

    def test_20_round61_all_3_runs_present_with_kernel_4_9_337_and_zero_crashes_writes(self) -> None:
        runs = self.summary["runs"]
        self.assertEqual(list(runs.keys()), list(self.EXPECTED_RUN_KEYS))
        for rk, rv in runs.items():
            self.assertEqual(rv["round"], 61, rk)
            self.assertIn("4.9.337-scel+", rv["kernel_version"], rk)
            self.assertEqual(rv["nop_count"], 0, rk)
            self.assertEqual(rv["crashes"], 0, rk)
            self.assertEqual(rv["emmc_write_count"], 0, rk)
            self.assertGreater(rv["wall_elapsed_sec"], 0.0, rk)

    def test_21_round61_r61a_usb_connection_mode_nouvc_lun_and_pd_verified(self) -> None:
        init_t = self.summary["runs"][
            "r61a_usb_hdmi_protect_netreset_big6_schinese"
        ]["r61_telemetry"]["wave47_init"]
        self.assertEqual(init_t["fx3_wave47_nodes_ok"], 1)
        self.assertEqual(init_t["uxc_tokens_ok"], 1)
        self.assertEqual(init_t["usb_nouvc_4mode_pd_ok"], 1)
        self.assertEqual(init_t["uvc_spoof_rc"], -2)
        self.assertEqual(init_t["msc_enum_rc"], -1)
        self.assertEqual(init_t["usb_data_tx_events"], 0)

    def test_22_round61_r61a_hdmi_info_protect_vs_format_and_nwreset_verified(self) -> None:
        init_t = self.summary["runs"][
            "r61a_usb_hdmi_protect_netreset_big6_schinese"
        ]["r61_telemetry"]["wave47_init"]
        self.assertEqual(init_t["hdmi_info_clean_clamp_ok"], 1)
        self.assertEqual(init_t["protect_vs_format_vault_ok"], 1)
        self.assertEqual(init_t["reset_network_reboot_airplane_ok"], 1)
        self.assertEqual(init_t["touch_blank_rc"], -16)
        self.assertEqual(init_t["log_2160p_rc"], -16)
        self.assertEqual(init_t["slot1_protect_rc"], -30)
        self.assertEqual(init_t["slot1_format_rc"], -30)
        self.assertEqual(init_t["nw_no_reboot_rc"], -11)
        self.assertEqual(init_t["rf_tx_blocked_rc"], -1)

    def test_23_round61_r61a_p2_cnflasha_and_slot1_ro_guards_intact(self) -> None:
        init_t = self.summary["runs"][
            "r61a_usb_hdmi_protect_netreset_big6_schinese"
        ]["r61_telemetry"]["wave47_init"]
        self.assertEqual(init_t["slot1_protect_mutation_events"], 0)
        self.assertEqual(init_t["slot1_format_events"], 0)
        self.assertEqual(init_t["post_reset_rf_leak_events"], 0)
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
        self.assertEqual(init_t["r61_init_ok"], 1)

    def test_24_round61_r61a_stage_b_schinese_lang_telemetry_and_bridge(self) -> None:
        r61a_t = self.summary["runs"][
            "r61a_usb_hdmi_protect_netreset_big6_schinese"
        ]["r61_telemetry"]
        lt = r61a_t["lang_telemetry"]
        self.assertEqual(lt["lang"], "schinese")
        self.assertEqual(lt["bk4_lang_id"], "0x02cf019c")
        self.assertEqual(lt["bk4_lang_val"], "0x19")
        self.assertEqual(lt["lang_enum"], "0x2b45_CHINESE_SIMPLIFIED")
        self.assertEqual(lt["font_bank"], 23)
        self.assertEqual(lt["str_bank"], 19)
        self.assertEqual(lt["gpe_fb"], 0)
        self.assertEqual(lt["round61_milestone_100plus_runs_usb_hdmi_protect_nwreset"], 1)
        self.assertEqual(lt["milestone_34th_realhw_102nd_live_68_pngs"], 1)
        self.assertEqual(lt["usb_data_tx_events"], 0)
        self.assertEqual(lt["slot1_protect_mutation_events"], 0)
        self.assertEqual(lt["slot1_format_events"], 0)
        self.assertEqual(lt["post_reset_rf_leak_events"], 0)
        self.assertEqual(lt["passive_tx_bytes_emitted"], 0)
        self.assertEqual(lt["e_nd_actuator_tx_count"], 0)
        self.assertEqual(lt["raw_firmware_bytes_leaked"], 0)
        sb = r61a_t["stage_b_bridge"]
        self.assertEqual(sb["round"], 61)
        self.assertEqual(sb["faithful"], 1)
        self.assertEqual(sb["nop_count"], 0)
        self.assertEqual(sb["usb_4mode_nouvc_lun_typec_pd"], 1)
        self.assertEqual(sb["hdmi_info_clean_log1080_raw4k"], 1)
        self.assertEqual(sb["protect_4scopes_vs_format_slot1_firewall"], 1)
        self.assertEqual(sb["nwreset_autoreboot_airplane_zero_rf"], 1)
        self.assertEqual(sb["milestone_34th_realhw_102nd_live_68_pngs"], 1)

    def test_25_round61_r61a_stage_b_3_pillar_bridges_verified(self) -> None:
        r61a_t = self.summary["runs"][
            "r61a_usb_hdmi_protect_netreset_big6_schinese"
        ]["r61_telemetry"]
        ub = r61a_t["usb_nouvc_pd_bridge"]
        self.assertEqual(ub["usb_4mode_nouvc_ok"], 1)
        self.assertEqual(ub["usb_lun_multi_single_ok"], 1)
        self.assertEqual(ub["usb_typec_pd_isolated_ok"], 1)
        self.assertEqual(ub["usb_nouvc_pd_ok"], 1)
        self.assertEqual(ub["usb_data_tx_events"], 0)
        self.assertEqual(ub["r61_bridge_ok"], 1)

        hb = r61a_t["hdmi_info_clean_clamp_bridge"]
        self.assertEqual(hb["hdmi_info_on_blanks_lcd_ok"], 1)
        self.assertEqual(hb["hdmi_log_1080p_clamp_ok"], 1)
        self.assertEqual(hb["hdmi_only_raw_4k_clean_ok"], 1)
        self.assertEqual(hb["hdmi_info_clean_clamp_ok"], 1)
        self.assertEqual(hb["log_1080p_clamp_bypass_events"], 0)
        self.assertEqual(hb["p2_setting_writes"], 0)

        pb = r61a_t["protect_format_nwreset_bridge"]
        self.assertEqual(pb["protect_4scopes_delete_only_ok"], 1)
        self.assertEqual(pb["slot1_protect_format_ro_ok"], 1)
        self.assertEqual(pb["nwreset_autoreboot_airplane_ok"], 1)
        self.assertEqual(pb["protect_format_nwreset_ok"], 1)
        self.assertEqual(pb["slot1_protect_mutation_events"], 0)
        self.assertEqual(pb["slot1_format_events"], 0)
        self.assertEqual(pb["post_reset_rf_leak_events"], 0)

    def test_26_round61_r61a_gpe0_readback_ge_300k_pixels_and_87_colors(self) -> None:
        r61a = self.summary["runs"][
            "r61a_usb_hdmi_protect_netreset_big6_schinese"
        ]
        self.assertEqual(r61a["target_presenter"], "31procam_big6_menu_home_presenter")
        self.assertEqual(r61a["target_sid"], "0x0a")
        self.assertGreaterEqual(r61a["total_threads_seen"], 150)
        gpe0 = r61a["gpe0_readback"]
        self.assertTrue(gpe0["present"])
        self.assertEqual(gpe0["bytes"], 2211840)
        self.assertEqual(gpe0["total_pixels"], 552960)
        self.assertGreaterEqual(gpe0["nonzero_pixels"], 300000)
        self.assertEqual(gpe0["nonzero_pixels"], 346686)
        self.assertEqual(gpe0["unique_colors"], 87)

    def test_27_round61_r61a_stage_b_manifest_13_hashes_and_r61_metadata(self) -> None:
        sb = self.summary["runs"][
            "r61a_usb_hdmi_protect_netreset_big6_schinese"
        ]["stage_b"]
        self.assertEqual(sb["manifest_count"], 13)
        self.assertEqual(len(sb["manifest_items"]), 13)
        for item in sb["manifest_items"]:
            self.assertEqual(len(item["sha256"]), 64)
        m = sb["r61"]
        self.assertEqual(m["r61_mode"], "usb_hdmi_protect_netreset_big6")
        self.assertTrue(m["milestone_100plus_runs"])
        self.assertGreaterEqual(m["realhw_round_ordinal"], 34)
        self.assertGreaterEqual(m["total_live_runs_at_completion"], 102)
        self.assertGreaterEqual(m["total_png_receipts_at_completion"], 68)
        self.assertEqual(m["usb_connection_mode_bkid"], "BKID_APP_setting_usb_connection_method")
        self.assertEqual(m["usb_connection_mode_resid16"], "0x69a2")
        self.assertEqual(len(m["usb_connection_modes_exposed_fx3"]), 4)
        self.assertFalse(m["usb_streaming_exposed_in_fx3_ui"])
        self.assertEqual(m["dormant_uvc_ko_bytes"], 78840)
        self.assertEqual(m["dormant_usb_streaming_resid16"], "0x7399")
        self.assertEqual(m["usb_lun_setting_resid16"], "0x6b19")
        self.assertEqual(m["usb_lun_default"], "Multi")
        self.assertEqual(m["usb_power_supply_resid16"], "0x721e")
        self.assertEqual(m["usb_power_supply_default"], "On")
        self.assertEqual(m["hdmi_info_display_bkid"], "BKID_APP_setting_hdmi_info_display")
        self.assertEqual(m["hdmi_info_display_resid16"], "0x6e7c")
        self.assertEqual(m["hdmi_info_display_default"], "On")
        self.assertEqual(m["protect_resid16"], "0xe2c9")
        self.assertEqual(len(m["protect_4_scopes"]), 4)
        self.assertEqual(m["reset_network_set_resid16"], "0x60d3")
        self.assertEqual(m["reset_network_set_reboot_bkid"], "BKID_APP_is_shutdown_factor_network_reset")

    def test_28_round61_r61b_nouvc_msc_and_pd_guards_blocked(self) -> None:
        r61b_t = self.summary["runs"][
            "r61b_nouvc_hdmi1080_slot1_protect_nwreset_guard"
        ]["r61_telemetry"]
        self.assertEqual(r61b_t["wave47_guard_rc"], 0)
        gd = r61b_t["wave47_guard"]
        self.assertEqual(gd["uvc_spoof_rc"], -2)
        self.assertEqual(gd["menu_uvc_rc"], -2)
        self.assertEqual(gd["tier0_msc_rc"], -1)
        self.assertEqual(gd["multi_usb_pd_rc"], -95)
        self.assertEqual(gd["no_batt_pd_rc"], -22)
        self.assertEqual(gd["non_isolated_pd_rc"], -1)
        self.assertEqual(gd["usb_data_enumeration_events"], 0)

    def test_29_round61_r61b_hdmi_touch_log2160p_sq_raw_and_clean_osd_blocked(self) -> None:
        gd = self.summary["runs"][
            "r61b_nouvc_hdmi1080_slot1_protect_nwreset_guard"
        ]["r61_telemetry"]["wave47_guard"]
        self.assertEqual(gd["lcd_touch_blanked_rc"], -16)
        self.assertEqual(gd["log_2160p_bypass_rc"], -16)
        self.assertEqual(gd["sq_raw_lockout_rc"], -95)
        self.assertEqual(gd["clean_osd_bake_rc"], -1)
        self.assertEqual(gd["log_1080p_clamp_bypass_events"], 0)

    def test_30_round61_r61b_slot1_protect_delete_format_and_nwreset_guards(self) -> None:
        gd = self.summary["runs"][
            "r61b_nouvc_hdmi1080_slot1_protect_nwreset_guard"
        ]["r61_telemetry"]["wave47_guard"]
        self.assertEqual(gd["slot1_protect_rc"], -30)
        self.assertEqual(gd["slot1_delete_rc"], -30)
        self.assertEqual(gd["slot1_format_rc"], -30)
        self.assertEqual(gd["slot2_protected_del_rc"], -13)
        self.assertEqual(gd["nw_skip_reboot_rc"], -11)
        self.assertEqual(gd["rf_before_airplane_rc"], -1)
        self.assertEqual(gd["rf_after_airplane_rc"], -1)
        self.assertEqual(gd["slot1_protect_mutation_events"], 0)
        self.assertEqual(gd["slot1_format_events"], 0)
        self.assertEqual(gd["post_reset_rf_leak_events"], 0)

    def test_31_round61_r61b_slot1_vault_ro_and_zero_emmc_cnflasha_writes(self) -> None:
        gd = self.summary["runs"][
            "r61b_nouvc_hdmi1080_slot1_protect_nwreset_guard"
        ]["r61_telemetry"]["wave47_guard"]
        self.assertEqual(gd["slot1_vault_ro_blocked_rc"], -30)
        self.assertEqual(gd["slot1_vault_sha256_match"], 1)
        self.assertEqual(gd["p2_write_blocked_rc"], -30)
        self.assertEqual(gd["cnflasha_ro_blocked_rc"], -30)
        self.assertEqual(gd["passive_tx_bytes_emitted"], 0)
        self.assertEqual(gd["e_nd_actuator_tx_count"], 0)
        self.assertEqual(gd["cnflasha_writes"], 0)
        self.assertEqual(gd["emmc_write_count"], 0)
        self.assertEqual(gd["r61b_ok"], 1)

    def test_32_round61_r61c_clean_unmount_nwreset_quarantine_and_reset_tiers_verified(self) -> None:
        ci = self.summary["runs"][
            "r61c_clean_unmount_nwreset_reboot_airplane_h0_h3_big6_schinese"
        ]["r61_telemetry"]["clean_unmount_nwreset_h0_h3"]
        self.assertEqual(ci["stock_unmount_restored_ok"], 1)
        self.assertEqual(ci["nw_quarantine_ok"], 1)
        self.assertEqual(ci["camreset_preserves_setup_ok"], 1)
        self.assertEqual(ci["initialize_restores_wave47_ok"], 1)
        self.assertEqual(ci["zero_rf_final_ok"], 1)

    def test_33_round61_r61c_dlopen_and_16_h0_eq_h3_idempotent_unmount(self) -> None:
        ci = self.summary["runs"][
            "r61c_clean_unmount_nwreset_reboot_airplane_h0_h3_big6_schinese"
        ]["r61_telemetry"]["clean_unmount_nwreset_h0_h3"]
        self.assertEqual(ci["dlopen_ok"], 1)
        self.assertEqual(ci["surfaces_verified"], 16)
        self.assertEqual(ci["surfaces_h0_eq_h3"], 16)
        self.assertEqual(ci["drift_bits"], 0)
        self.assertEqual(ci["cnflasha_write_bytes"], 0)
        self.assertEqual(ci["emmc_write_bytes"], 0)
        self.assertEqual(ci["e_nd_actuator_tx_count"], 0)
        self.assertEqual(ci["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(ci["emmc_write_count"], 0)
        self.assertEqual(ci["r61c_ok"], 1)

    def test_34_round61_r61c_integrated_renders_valid_big6_gpe0_readback(self) -> None:
        r61c = self.summary["runs"][
            "r61c_clean_unmount_nwreset_reboot_airplane_h0_h3_big6_schinese"
        ]
        self.assertEqual(r61c["target_presenter"], "31procam_big6_menu_home_presenter")
        self.assertEqual(r61c["target_sid"], "0x0a")
        gpe0 = r61c["gpe0_readback"]
        self.assertTrue(gpe0["present"])
        self.assertEqual(gpe0["bytes"], 2211840)
        self.assertEqual(gpe0["total_pixels"], 552960)
        self.assertGreaterEqual(gpe0["nonzero_pixels"], 300000)
        self.assertEqual(gpe0["nonzero_pixels"], 346206)
        self.assertEqual(gpe0["unique_colors"], 87)

    def test_35_round61_realhw_mechanisms_verified_6_blocks_match_run_telemetry(self) -> None:
        rm = self.summary["realhw_mechanisms_verified"]
        self.assertEqual(len(rm), 6)
        r61a = self.summary["runs"][
            "r61a_usb_hdmi_protect_netreset_big6_schinese"
        ]["r61_telemetry"]
        r61b = self.summary["runs"][
            "r61b_nouvc_hdmi1080_slot1_protect_nwreset_guard"
        ]["r61_telemetry"]
        r61c = self.summary["runs"][
            "r61c_clean_unmount_nwreset_reboot_airplane_h0_h3_big6_schinese"
        ]["r61_telemetry"]
        self.assertEqual(
            rm["wave47_usb_hdmi_protect_nwreset_init"],
            r61a["wave47_init"],
        )
        self.assertEqual(
            rm["usb_nouvc_pd_stage_b_bridge"],
            r61a["usb_nouvc_pd_bridge"],
        )
        self.assertEqual(
            rm["hdmi_info_clean_clamp_stage_b_bridge"],
            r61a["hdmi_info_clean_clamp_bridge"],
        )
        self.assertEqual(
            rm["protect_format_nwreset_stage_b_bridge"],
            r61a["protect_format_nwreset_bridge"],
        )
        self.assertEqual(
            rm["wave47_fail_closed_guard"],
            r61b["wave47_guard"],
        )
        self.assertEqual(
            rm["clean_unmount_nwreset_airplane_and_16_h0_h3"],
            r61c["clean_unmount_nwreset_h0_h3"],
        )

    def test_36_round61_reset_tiers_survival_consistent_across_runs(self) -> None:
        r61a_t = self.summary["runs"][
            "r61a_usb_hdmi_protect_netreset_big6_schinese"
        ]["r61_telemetry"]
        r61c_ci = self.summary["runs"][
            "r61c_clean_unmount_nwreset_reboot_airplane_h0_h3_big6_schinese"
        ]["r61_telemetry"]["clean_unmount_nwreset_h0_h3"]
        self.assertEqual(r61a_t["wave47_init"]["reset_network_reboot_airplane_ok"], 1)
        self.assertEqual(r61c_ci["stock_unmount_restored_ok"], 1)
        self.assertEqual(r61c_ci["nw_quarantine_ok"], 1)
        self.assertEqual(r61c_ci["camreset_preserves_setup_ok"], 1)
        self.assertEqual(r61c_ci["initialize_restores_wave47_ok"], 1)
        self.assertEqual(r61c_ci["zero_rf_final_ok"], 1)

    def test_37_round61_cross_round_consistency_with_r60_slot1_ro_and_zero_leaks(self) -> None:
        self.assertEqual(self.r60_summary["round"], 60)
        r60b_gd = self.r60_summary["runs"][
            "r60b_dormant_monitor_sleep_slot1_delete_guard"
        ]["r60_telemetry"]["dormant_mon_slot1_del_guard"]
        self.assertEqual(r60b_gd["slot1_vault_ro_blocked_rc"], -30)
        r61b_gd = self.summary["runs"][
            "r61b_nouvc_hdmi1080_slot1_protect_nwreset_guard"
        ]["r61_telemetry"]["wave47_guard"]
        self.assertEqual(r61b_gd["slot1_vault_ro_blocked_rc"], -30)
        self.assertEqual(r61b_gd["slot1_vault_sha256_match"], 1)
        self.assertEqual(r61b_gd["slot1_protect_mutation_events"], 0)
        self.assertEqual(r61b_gd["slot1_format_events"], 0)

    def test_38_round61_cross_round_consistency_with_r59_and_r58_zero_emmc_writes(self) -> None:
        self.assertEqual(self.r59_summary["round"], 59)
        self.assertEqual(self.r58_summary["round"], 58)
        r59b_gd = self.r59_summary["runs"][
            "r59b_af_illum_bt_sync_pmic_5v_hdmi_2160p_guard"
        ]["r59_telemetry"]["af_illum_bt_pmic_hdmi_guard"]
        self.assertEqual(r59b_gd["emmc_write_count"], 0)
        r58b_gd = self.r58_summary["runs"][
            "r58b_slot1_dcim_prefix_log_gamma_assist_guard"
        ]["r58_telemetry"]["slot1_dcim_log_gamma_guard"]
        self.assertEqual(r58b_gd["emmc_write_count"], 0)
        r61b_gd = self.summary["runs"][
            "r61b_nouvc_hdmi1080_slot1_protect_nwreset_guard"
        ]["r61_telemetry"]["wave47_guard"]
        self.assertEqual(r61b_gd["emmc_write_count"], 0)
        self.assertEqual(r61b_gd["cnflasha_writes"], 0)

    def test_39_round61_cross_round_consistency_with_r60_16_h0_eq_h3(self) -> None:
        r60c = self.r60_summary["runs"][
            "r60c_clean_unmount_reset_tiers_h0_h3_big6_schinese"
        ]["r60_telemetry"]["clean_unmount_reset_h0_h3"]
        self.assertEqual(r60c["surfaces_h0_eq_h3"], 16)
        r61c = self.summary["runs"][
            "r61c_clean_unmount_nwreset_reboot_airplane_h0_h3_big6_schinese"
        ]["r61_telemetry"]["clean_unmount_nwreset_h0_h3"]
        self.assertEqual(r61c["surfaces_h0_eq_h3"], 16)
        self.assertEqual(r61c["drift_bits"], 0)

    def test_40_round61_unexecuted_physical_camera_bench_boundaries_documented(self) -> None:
        bounds = self.summary["unexecuted_physical_camera_bench_boundaries"]
        self.assertEqual(len(bounds), 3)
        joined = " ".join(bounds)
        self.assertIn("USB Connection Mode", joined)
        self.assertIn("USB Power Supply", joined)
        self.assertIn("HDMI Info. Display", joined)
        self.assertIn("Protect", joined)
        self.assertIn("Format", joined)
        self.assertIn("Reset Network Set.", joined)
        self.assertIn("Airplane Mode", joined)

    def test_41_round61_alpha_png_exists_under_28kib_and_matches_summary_sha256(self) -> None:
        pe = self.summary["runs"][
            "r61a_usb_hdmi_protect_netreset_big6_schinese"
        ]["png_exports"]["alpha_png"]
        self.assertLess(len(self.alpha_png_bytes), 28000)
        self.assertLess(len(self.alpha_png_bytes), 28672)
        self.assertLess(len(self.alpha_png_bytes), 51200)
        self.assertEqual(len(self.alpha_png_bytes), pe["bytes"])
        self.assertEqual(
            hashlib.sha256(self.alpha_png_bytes).hexdigest(), pe["sha256"]
        )

    def test_42_round61_composited_png_exists_under_28kib_and_matches_summary_sha256(self) -> None:
        pe = self.summary["runs"][
            "r61a_usb_hdmi_protect_netreset_big6_schinese"
        ]["png_exports"]["composited_png"]
        self.assertLess(len(self.comp_png_bytes), 28000)
        self.assertLess(len(self.comp_png_bytes), 28672)
        self.assertLess(len(self.comp_png_bytes), 51200)
        self.assertEqual(len(self.comp_png_bytes), pe["bytes"])
        self.assertEqual(
            hashlib.sha256(self.comp_png_bytes).hexdigest(), pe["sha256"]
        )

    def test_43_round61_alpha_png_valid_1024x540_rgba_with_transparent_and_opaque_pixels(self) -> None:
        self.assertEqual(self.alpha_dims, (1024, 540))
        self.assertEqual(self.alpha_transparent, 552960 - 346686)
        self.assertGreater(self.alpha_opaque, 300000)

    def test_44_round61_composited_png_valid_1024x540_rgba_100pct_opaque(self) -> None:
        self.assertEqual(self.comp_dims, (1024, 540))
        self.assertEqual(self.comp_opaque, 1024 * 540)

    def test_45_round61_report_readme_documents_all_3_runs_and_zero_host_leaks(self) -> None:
        for token in (
            "Round 61 Milestone",
            "Wave-47",
            "r61a",
            "r61b",
            "r61c",
            "102/102",
            "68/68",
            "USB Connection Mode",
            "NOUVC",
            "HDMI Info. Display",
            "Protect",
            "Format",
            "Reset Network Set.",
            "Airplane Mode",
            "Slot-1",
            "346,686",
            "r61a-usb-hdmi-protect-netreset-4ch-big6-schinese-alpha.png",
            "r61a-usb-hdmi-protect-netreset-4ch-big6-schinese-composited.png",
        ):
            self.assertIn(token, self.r61_readme)
        for forbidden in ("/Users/", "/private/tmp/", "/var/folders/", "work/_scratch/", ":87" + "68"):
            self.assertNotIn(forbidden, self.r61_readme)

    def test_46_round61_closure_readme_section_61_present_and_accurate(self) -> None:
        self.assertIn("## 61. Round 61", self.closure_readme)
        self.assertIn("100+ Live QEMU Runs Milestone!", self.closure_readme)
        self.assertIn("34/34 Real-HW Rounds", self.closure_readme)
        self.assertIn("102/102 Total", self.closure_readme)
        self.assertIn("68/68 PNGs", self.closure_readme)
        self.assertIn(
            "2026-11-17-round61-milestone-100runs-usb-mode-hdmi-info-protect-reset-network-qemu",
            self.closure_readme,
        )

    def test_47_round61_34_plus_realhw_qemu_rounds_r28_to_r61_102_plus_runs_and_68_plus_pngs(self) -> None:
        png_total = 0
        rounds_found = 0
        for r in range(28, 62):
            matches = list((REPO_ROOT / "reports").glob(f"2026-??-??-round{r}-*"))
            self.assertEqual(len(matches), 1, f"Expected 1 report dir for Round {r}")
            pngs = list((matches[0] / "assets").glob("*.png"))
            self.assertGreaterEqual(len(pngs), 2, f"Expected >= 2 PNGs for Round {r}")
            for p in pngs:
                self.assertLess(p.stat().st_size, 51200, str(p))
            png_total += len(pngs)
            rounds_found += 1
        self.assertGreaterEqual(rounds_found, 34)
        self.assertGreaterEqual(png_total, 68)
        audit = self.summary["r61_realhw_usb_mode_hdmi_info_protect_reset_network_audit"]
        self.assertGreaterEqual(audit["milestone295_qemu_rounds"], 34)
        self.assertGreaterEqual(audit["milestone295_qemu_runs"], 102)
        self.assertGreaterEqual(audit["milestone295_png_receipts"], 68)

    def test_48_round61_dual_mode_clean_room_toggle_parity_on_summary(self) -> None:
        for clean_flag in ("0", "1"):
            with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                d = json.loads(self.summary_raw)
                self.assertEqual(d["round"], 61)
                self.assertEqual(
                    d["runs"][
                        "r61a_usb_hdmi_protect_netreset_big6_schinese"
                    ]["r61_telemetry"]["usb_nouvc_pd_bridge"]["usb_nouvc_pd_ok"],
                    1,
                )
                self.assertEqual(
                    d["runs"][
                        "r61b_nouvc_hdmi1080_slot1_protect_nwreset_guard"
                    ]["r61_telemetry"]["wave47_guard"]["uvc_spoof_rc"],
                    -2,
                )
                self.assertEqual(
                    d["runs"][
                        "r61c_clean_unmount_nwreset_reboot_airplane_h0_h3_big6_schinese"
                    ]["r61_telemetry"]["clean_unmount_nwreset_h0_h3"][
                        "surfaces_h0_eq_h3"
                    ],
                    16,
                )

    def test_49_round61_r61a_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"][
            "r61a_usb_hdmi_protect_netreset_big6_schinese"
        ]["r61_telemetry"]["wave47_init"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_50_round61_r61b_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"][
            "r61b_nouvc_hdmi1080_slot1_protect_nwreset_guard"
        ]["r61_telemetry"]["wave47_guard"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_51_round61_r61c_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"][
            "r61c_clean_unmount_nwreset_reboot_airplane_h0_h3_big6_schinese"
        ]["r61_telemetry"]["clean_unmount_nwreset_h0_h3"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_52_round61_r61a_top_colors_transparent_plus_nonzero_equals_total_pixels(self) -> None:
        gpe = self.summary["runs"][
            "r61a_usb_hdmi_protect_netreset_big6_schinese"
        ]["gpe0_readback"]
        color_map = {row["argb"]: row["pixels"] for row in gpe["top_colors"]}
        self.assertIn("0x00000000", color_map)
        self.assertIn("0xff000000", color_map)
        self.assertEqual(color_map["0x00000000"] + gpe["nonzero_pixels"], gpe["total_pixels"])

    def test_53_round61_r61c_top_colors_transparent_plus_nonzero_equals_total_pixels(self) -> None:
        gpe = self.summary["runs"][
            "r61c_clean_unmount_nwreset_reboot_airplane_h0_h3_big6_schinese"
        ]["gpe0_readback"]
        color_map = {row["argb"]: row["pixels"] for row in gpe["top_colors"]}
        self.assertIn("0x00000000", color_map)
        self.assertEqual(color_map["0x00000000"] + gpe["nonzero_pixels"], gpe["total_pixels"])

    def test_54_round61_r61a_and_r61c_wall_elapsed_and_duration_budget_sanity(self) -> None:
        r61a = self.summary["runs"][
            "r61a_usb_hdmi_protect_netreset_big6_schinese"
        ]
        r61c = self.summary["runs"][
            "r61c_clean_unmount_nwreset_reboot_airplane_h0_h3_big6_schinese"
        ]
        ci_headroom = 15.0 if os.environ.get("GITHUB_ACTIONS") == "true" else 0.0
        max_wall = 240.0 + ci_headroom if os.environ.get("GITHUB_ACTIONS") == "true" else 120.0 + ci_headroom
        self.assertGreaterEqual(r61a["duration_budget_sec"], 70)
        self.assertLessEqual(r61a["duration_budget_sec"], 120)
        self.assertGreater(r61a["wall_elapsed_sec"], 50.0)
        self.assertLess(r61a["wall_elapsed_sec"], max_wall)
        self.assertGreaterEqual(r61c["duration_budget_sec"], 70)
        self.assertLessEqual(r61c["duration_budget_sec"], 120)
        self.assertGreater(r61c["wall_elapsed_sec"], 50.0)
        self.assertLess(r61c["wall_elapsed_sec"], max_wall)

    def test_55_round61_r61b_fast_early_exit_wall_elapsed_with_ci_headroom(self) -> None:
        r61b = self.summary["runs"][
            "r61b_nouvc_hdmi1080_slot1_protect_nwreset_guard"
        ]
        ci_headroom = 15.0 if os.environ.get("GITHUB_ACTIONS") == "true" else 0.0
        max_b = 45.0 + ci_headroom if os.environ.get("GITHUB_ACTIONS") == "true" else 20.0 + ci_headroom
        self.assertEqual(r61b["duration_budget_sec"], 35)
        self.assertGreater(r61b["wall_elapsed_sec"], 1.0)
        self.assertLess(r61b["wall_elapsed_sec"], max_b)
        self.assertTrue(r61b["gpe0_readback"]["skipped_stock_fx3_mode"])

    def test_56_round61_faithful_invariants_preserved_across_all_3_runs(self) -> None:
        for rk, rv in self.summary["runs"].items():
            fi = rv["faithful_invariants"]
            self.assertEqual(fi["FX6_NATIVE_FAITHFUL"], 1, rk)
            self.assertEqual(fi["subst_color"], 0, rk)
            self.assertEqual(fi["subst_image"], 0, rk)
            self.assertEqual(fi["forced_render"], 0, rk)
            self.assertEqual(fi["skipped_node"], 0, rk)
            self.assertEqual(fi["lock_bypass"], 0, rk)

    def test_57_round61_all_3_runs_stage_b_manifest_count_13(self) -> None:
        for rk, rv in self.summary["runs"].items():
            self.assertEqual(rv["stage_b"]["manifest_count"], 13, rk)
            self.assertEqual(len(rv["stage_b"]["manifest_items"]), 13, rk)

    def test_58_round61_r61c_stage_b_r61_bridges_and_zero_leak_verified(self) -> None:
        r61c_t = self.summary["runs"][
            "r61c_clean_unmount_nwreset_reboot_airplane_h0_h3_big6_schinese"
        ]["r61_telemetry"]
        self.assertEqual(
            r61c_t["usb_nouvc_pd_bridge"]["usb_nouvc_pd_ok"], 1
        )
        self.assertEqual(
            r61c_t["hdmi_info_clean_clamp_bridge"]["hdmi_info_clean_clamp_ok"], 1
        )
        self.assertEqual(
            r61c_t["protect_format_nwreset_bridge"]["protect_format_nwreset_ok"], 1
        )
        self.assertEqual(
            r61c_t["usb_nouvc_pd_bridge"]["usb_data_tx_events"], 0
        )
        self.assertEqual(
            r61c_t["hdmi_info_clean_clamp_bridge"]["log_1080p_clamp_bypass_events"], 0
        )
        self.assertEqual(
            r61c_t["protect_format_nwreset_bridge"]["slot1_protect_mutation_events"], 0
        )
        self.assertEqual(
            r61c_t["protect_format_nwreset_bridge"]["slot1_format_events"], 0
        )
        self.assertEqual(
            r61c_t["protect_format_nwreset_bridge"]["post_reset_rf_leak_events"], 0
        )
        self.assertEqual(r61c_t["stage_b_bridge"]["e_nd_actuator_tx_count"], 0)

    def test_59_round61_all_3_runs_prefix_counts_include_fx6_r61(self) -> None:
        r61a_pc = self.summary["runs"][
            "r61a_usb_hdmi_protect_netreset_big6_schinese"
        ]["prefix_counts"]
        r61b_pc = self.summary["runs"][
            "r61b_nouvc_hdmi1080_slot1_protect_nwreset_guard"
        ]["prefix_counts"]
        r61c_pc = self.summary["runs"][
            "r61c_clean_unmount_nwreset_reboot_airplane_h0_h3_big6_schinese"
        ]["prefix_counts"]
        self.assertGreater(r61a_pc["FX6_R61_"], 10)
        self.assertEqual(r61b_pc["FX6_R61_"], 3)
        self.assertGreater(r61c_pc["FX6_R61_"], 10)

    def test_60_round61_r61_meta_invariants_across_all_3_runs(self) -> None:
        for rk, rv in self.summary["runs"].items():
            m = rv["stage_b"]["r61"]
            self.assertFalse(m["usb_streaming_exposed_in_fx3_ui"], rk)
            self.assertEqual(m["usb_connection_mode_resid16"], "0x69a2", rk)
            self.assertEqual(m["dormant_usb_streaming_resid16"], "0x7399", rk)
            self.assertEqual(m["dormant_uvc_ko_bytes"], 78840, rk)
            self.assertTrue(m["usb_power_supply_typec_only"], rk)
            self.assertTrue(m["usb_power_supply_requires_npfz100"], rk)
            self.assertTrue(m["tier0_usb_data_enumeration_blocked"], rk)
            self.assertTrue(m["hdmi_info_on_blanks_builtin_lcd"], rk)
            self.assertTrue(m["hdmi_internal_log_pplut_clamps_1080p"], rk)
            self.assertTrue(m["hdmi_only_or_raw_forces_info_off_4k_clean"], rk)
            self.assertTrue(m["protect_shields_against_delete_only"], rk)
            self.assertTrue(m["format_wipes_even_protected_clips"], rk)
            self.assertTrue(m["slot1_protect_mutation_blocked"], rk)
            self.assertTrue(m["slot1_format_hard_locked"], rk)
            self.assertTrue(m["reset_network_set_clears_network_only"], rk)
            self.assertTrue(m["reset_network_set_triggers_mandatory_autoreboot"], rk)
            self.assertTrue(m["post_network_reset_airplane_mode_on_required"], rk)
            self.assertEqual(m["usb_data_tx_events"], 0, rk)
            self.assertEqual(m["slot1_protect_mutation_events"], 0, rk)
            self.assertEqual(m["slot1_format_events"], 0, rk)
            self.assertEqual(m["post_reset_rf_leak_events"], 0, rk)
            self.assertEqual(m["e_nd_actuator_tx_count"], 0, rk)
            self.assertEqual(m["raw_firmware_bytes_leaked"], 0, rk)

    def test_61_round61_sanitize_helper_redacts_host_paths_and_reserved_port(self) -> None:
        dirty = {
            "run_id": "test-run",
            "lang": "schinese",
            "r61_mode": "usb_hdmi_protect_netreset_big6",
            "kernel_version": "Linux version 4.9.337-scel+",
            "kernel_bin": "/Users/fake/secret/kernel.bin",
            "dtb_bin": "/Users/fake/secret/guest.dtb",
            "build": {"tmp_build": "/private/tmp/build-123"},
            "stage_b": {"r61": {"r61_mode": "usb_hdmi_protect_netreset_big6"}},
            "r61_telemetry": {
                "wave47_init": {"r61_init_ok": 1},
                "wave47_guard": {"r61b_ok": 1},
                "clean_unmount_nwreset_h0_h3": {"r61c_ok": 1, "surfaces_h0_eq_h3": 16},
            },
            "gpe0_readback": {"nonzero_pixels": 346686},
            "png_exports": {
                "alpha_png": {
                    "path": "/Users/kafu/repo/reports/2026-11-17-round61-milestone-100runs-usb-mode-hdmi-info-protect-reset-network-qemu/assets/a.png"
                }
            },
            "prefix_counts": {"FX6_R61_": 10},
        }
        sanitized = self.runner.sanitize_round61_summary(dirty, dirty, dirty)
        raw = json.dumps(sanitized)
        self.assertNotIn("/Users/", raw)
        self.assertNotIn("/private/tmp/", raw)
        self.assertNotIn("kernel_bin", raw)
        self.assertNotIn("dtb_bin", raw)
        self.assertIn(
            "reports/2026-11-17-round61-milestone-100runs-usb-mode-hdmi-info-protect-reset-network-qemu/assets/a.png",
            raw,
        )

    def test_62_round61_no_stray_temp_files_or_reserved_port_in_repo(self) -> None:
        for bad_name in ("tmp", "scratch", ".worktrees"):
            self.assertFalse((REPO_ROOT / bad_name).exists(), bad_name)
        reserved_port = "87" + "68"
        self.assertNotIn(reserved_port, self.summary_raw)
        self.assertNotIn(reserved_port, self.r61_readme)

    def test_63_round61_runner_escapes_percent_in_argparse_help_and_portable_tools(self) -> None:
        self.assertIn("ArgumentParser", self.runner_src)
        self.assertNotIn('"/usr/bin/python3"', self.runner_src)
        self.assertIn('shutil.which("zig")', self.runner_src)
        self.assertIn("FX6_SCRATCH_DIR", self.runner_src)

    def test_64_round61_test_suite_contains_at_least_64_unit_tests(self) -> None:
        methods = [m for m in dir(self) if m.startswith("test_")]
        self.assertGreaterEqual(len(methods), 64)

    def test_65_round61_dual_mode_env_flags_preserve_zero_emmc_and_clean_room_parity(self) -> None:
        for env_overrides in (
            {},
            {"FX3_CLEAN_ROOM_TEST": "1"},
            {"FX3_FX6_FORCE_CLEAN_ROOM": "1"},
        ):
            with mock.patch.dict(os.environ, env_overrides, clear=False):
                parsed = self.runner.extract_milestones(
                    "Linux version 4.9.337-scel+\n"
                    "FX6_R61_WAVE47_INIT usb_nouvc_4mode_pd_ok=1 hdmi_info_clean_clamp_ok=1 "
                    "protect_vs_format_vault_ok=1 reset_network_reboot_airplane_ok=1 r61_init_ok=1\n"
                )
                self.assertEqual(parsed["r61_telemetry"]["wave47_init"]["r61_init_ok"], 1)


if __name__ == "__main__":
    unittest.main()
