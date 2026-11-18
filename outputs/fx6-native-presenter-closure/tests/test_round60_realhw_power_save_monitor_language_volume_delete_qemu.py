#!/usr/bin/env python3
"""Offline dual-mode unit tests for FX6-on-FX3 Round 60 Milestone (60th Round Milestone! / 33rd Real-HW Round / 99th Live Run — Wave-46)."""
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
ROUND60_REPORT_DIR = (
    REPO_ROOT
    / "reports"
    / "2026-11-17-round60-milestone-realhw-power-save-monitor-language-volume-delete-qemu"
)
WAVE46_SPEC_PATH = (
    REPO_ROOT
    / "reports"
    / "2026-11-17-global-sony-wave46-power-save-by-monitor-language-volume-delete-confirm-intel"
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


def _build_overlay_for_r60(
    runner,
    parent_cpio: pathlib.Path,
    fp,
    fv,
    fb,
    fake_run,
    jit_meta: Dict[str, Any],
    work: pathlib.Path,
    r60_mode: str,
    lang: str = "schinese",
    enable_r60: bool = True,
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
            enable_r60=enable_r60,
            r60_mode=r60_mode,
            sd_manifest_mode="valid",
            lang=lang,
            shim_bytes=b"SHIM",
        )


class TestRound60MilestoneRealHwPowerSaveMonitorLanguageVolumeDeleteQemu(unittest.TestCase):
    EXPECTED_RUN_KEYS = (
        "r60a_power_save_monitor_lang_vol_delete_big6_schinese",
        "r60b_dormant_monitor_sleep_slot1_delete_guard",
        "r60c_clean_unmount_reset_tiers_h0_h3_big6_schinese",
    )

    runner: Any
    runner_src: str
    stage_a_src: str
    shim_src: str
    wave46_spec: str
    summary_raw: str
    summary: Dict[str, Any]
    r60_readme: str
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
    launcher_r60: Optional[bytes]
    shim_r60: Optional[bytes]
    shim_r59: Optional[bytes]
    r59_summary: Dict[str, Any]
    r58_summary: Dict[str, Any]
    r57_summary: Dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = _load_closure_module("fx6_brr_r60_cached", "build_and_run_round.py")
        cls.runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")
        cls.stage_a_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        cls.shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        cls.wave46_spec = WAVE46_SPEC_PATH.read_text(encoding="utf-8")
        cls.summary_raw = (ROUND60_REPORT_DIR / "summary.json").read_text(encoding="utf-8")
        cls.summary = json.loads(cls.summary_raw)
        cls.r60_readme = (ROUND60_REPORT_DIR / "README.md").read_text(encoding="utf-8")
        cls.closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")

        alpha_p = (
            ROUND60_REPORT_DIR
            / "assets"
            / "r60a-language-volume-4ch-big6-schinese-alpha.png"
        )
        comp_p = (
            ROUND60_REPORT_DIR
            / "assets"
            / "r60a-language-volume-4ch-big6-schinese-composited.png"
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
            cls.ov_a = _build_overlay_for_r60(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wa", "power_save_monitor_lang_vol_delete_big6", lang="schinese",
            )
            cls.ov_b = _build_overlay_for_r60(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wb", "dormant_monitor_sleep_slot1_delete_guard", lang="en",
            )
            cls.ov_c = _build_overlay_for_r60(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wc", "clean_unmount_reset_tiers_h0_h3_big6", lang="schinese",
            )
            cls.ov_off = _build_overlay_for_r60(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "woff", "power_save_monitor_lang_vol_delete_big6", enable_r60=False,
            )
            cls.invalid_mode_raised = False
            try:
                _build_overlay_for_r60(
                    cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                    tpath / "wbad", "invalid_r60_mode",
                )
            except ValueError:
                cls.invalid_mode_raised = True

            zig_bin = shutil.which("zig") or (
                str(cls.runner.ZIG) if cls.runner.ZIG.is_file() else None
            )
            if zig_bin is not None:
                verify_r60_out = tpath / "fx6-stage-a-verify-r60"
                shim_r60_out = tpath / "libgrm-fbinit9-r60.so"
                shim_r59_out = tpath / "libgrm-fbinit9-r59.so"
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
                        str(verify_r60_out),
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
                    [
                        zig_bin,
                        "cc",
                        "-target",
                        "aarch64-linux-gnu.2.25",
                        "-O0",
                        "-shared",
                        "-fPIC",
                        "-DFX6_ROUND=59",
                        str(CLOSURE_DIR / "libgrm-fbinit9.c"),
                        "-ldl",
                        "-lpthread",
                        "-o",
                        str(shim_r59_out),
                    ],
                ):
                    cls.runner.subprocess.run(cmd, check=True)
                cls.launcher_r60 = verify_r60_out.read_bytes()
                cls.shim_r60 = shim_r60_out.read_bytes()
                cls.shim_r59 = shim_r59_out.read_bytes()
            else:
                cls.launcher_r60 = None
                cls.shim_r60 = None
                cls.shim_r59 = None

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
        cls.r57_summary = json.loads(
            (
                REPO_ROOT
                / "reports"
                / "2026-11-17-round57-milestone-realhw-release-wo-card-audio-meter-copyright-qemu"
                / "summary.json"
            ).read_text(encoding="utf-8")
        )

    def test_01_wave46_global_spec_present_and_covers_all_wave46_pillars(self) -> None:
        self.assertTrue(WAVE46_SPEC_PATH.is_file())
        for needle in (
            "Power Setting Option",
            "Power Save by Monitor",
            "0x60b9",
            "Both Linked",
            "Open: Return",
            "Close: Power Save",
            "Does Not Link",
            "Power Save Start Time",
            "Auto Power OFF Temp.",
            "Language",
            "0x02cf019c",
            "34",
            "29",
            "Volume Settings",
            "0..15",
            "4ch Audio Monitoring",
            "CH1+3/CH2+4",
            "Delete confirm.",
            "\"Cancel\" first",
            "\"Delete\" first",
            "Delete pressing twice",
            "slot1_vault_delete_events == 0",
        ):
            self.assertIn(needle, self.wave46_spec)

    def test_02_round60_summary_schema_round_milestone_and_zero_leaks(self) -> None:
        self.assertNotIn("/Users/", self.summary_raw)
        self.assertNotIn("/private/tmp/", self.summary_raw)
        self.assertEqual(
            self.summary["schema"],
            "fx6-on-fx3-round60-milestone-realhw-power-save-monitor-language-volume-delete-qemu-v1",
        )
        self.assertEqual(self.summary["round"], 60)
        self.assertEqual(self.summary["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(tuple(self.summary["runs"].keys()), self.EXPECTED_RUN_KEYS)

    def test_03_round60_cli_accepts_round60_and_all_3_r60_modes(self) -> None:
        self.assertIn(", 59, 60]", self.runner_src)
        for mode in (
            "power_save_monitor_lang_vol_delete_big6",
            "dormant_monitor_sleep_slot1_delete_guard",
            "clean_unmount_reset_tiers_h0_h3_big6",
        ):
            self.assertIn(mode, self.runner_src)

    def test_04_round60_overlay_rejects_invalid_r60_mode(self) -> None:
        self.assertTrue(self.invalid_mode_raised)

    def test_05_round60_overlay_r60a_injects_etc_fx6_stage_r60_and_appfw_launch(self) -> None:
        replacements, additions, meta = self.ov_a
        self.assertTrue(meta["r60_enabled"])
        self.assertIn("etc/fx6_stage_r60", additions)
        self.assertIn("etc/fx6_r60_libjit.so", additions)
        r60_cfg = additions["etc/fx6_stage_r60"][0].decode("utf-8")
        self.assertIn("stage_r60=1", r60_cfg)
        self.assertIn("r60_mode=power_save_monitor_lang_vol_delete_big6", r60_cfg)
        self.assertIn("milestone_60th_round_33rd_realhw_99th_live=1", r60_cfg)
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("/usr/bin/appfw-launch", init_txt)
        self.assertNotIn("--r60-dormant-monitor-slot1-delete-guard", init_txt)

    def test_06_round60_overlay_r60b_injects_early_guard_probe_and_poweroff(self) -> None:
        replacements, _, meta = self.ov_b
        self.assertEqual(meta["r60"]["r60_mode"], "dormant_monitor_sleep_slot1_delete_guard")
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("--r60-dormant-monitor-slot1-delete-guard", init_txt)
        self.assertIn("FX6_R60_DORMANT_MON_SLOT1_DEL_RC=", init_txt)
        self.assertIn("FX6_R60_DORMANT_MON_SLOT1_DEL_EXIT", init_txt)
        self.assertIn("poweroff -f", init_txt)

    def test_07_round60_overlay_r60c_integrated_runs_stage_b_big6(self) -> None:
        replacements, additions, meta = self.ov_c
        self.assertEqual(meta["r60"]["r60_mode"], "clean_unmount_reset_tiers_h0_h3_big6")
        r60_cfg = additions["etc/fx6_stage_r60"][0].decode("utf-8")
        self.assertIn("r60_mode=clean_unmount_reset_tiers_h0_h3_big6", r60_cfg)
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("/usr/bin/appfw-launch", init_txt)
        self.assertNotIn("--r60-dormant-monitor-slot1-delete-guard", init_txt)

    def test_08_round60_overlay_disabled_when_enable_r60_false(self) -> None:
        _, additions, meta = self.ov_off
        self.assertFalse(meta["r60_enabled"])
        self.assertNotIn("etc/fx6_stage_r60", additions)
        self.assertNotIn("etc/fx6_r60_libjit.so", additions)
        self.assertNotIn("r60", meta)

    def test_09_round60_stage_a_c_source_contains_all_3_wave46_probes(self) -> None:
        for sym in (
            "setup_r60_power_save_monitor_lang_vol_delete_probe",
            "run_r60_dormant_monitor_sleep_slot1_delete_guard_probe",
            "run_r60_clean_unmount_reset_tiers_h0_h3_probe",
            "FX6_R60_WAVE46_INIT",
            "FX6_R60_DORMANT_MON_SLOT1_DEL_GUARD",
            "FX6_R60_CLEAN_UNMOUNT_RESET_H0_H3",
            "--r60-dormant-monitor-slot1-delete-guard",
            "--r60-clean-unmount-reset-h0-h3",
            "/etc/fx6_stage_r60",
        ):
            self.assertIn(sym, self.stage_a_src)

    def test_10_round60_shim_c_source_contains_r60_guarded_bridges(self) -> None:
        self.assertIn("#if FX6_ROUND >= 60", self.shim_src)
        for sym in (
            "FX6_R60_POWERSAVE_REALITY_SPLIT_BRIDGE",
            "FX6_R60_LANG_34_29_PARITY_BRIDGE",
            "FX6_R60_VOL_4CH_DELETE_VAULT_BRIDGE",
            "FX6_R60_LANG_TELEMETRY",
            "FX6_STAGE_B_R60_BRIDGE",
        ):
            self.assertIn(sym, self.shim_src)

    def test_11_round60_compile_launcher_and_shim_aarch64_elf_symbols(self) -> None:
        if self.launcher_r60 is None or self.shim_r60 is None:
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertEqual(self.launcher_r60[:4], b"\x7fELF")
        self.assertEqual(self.shim_r60[:4], b"\x7fELF")
        self.assertEqual(struct.unpack_from("<H", self.shim_r60, 18)[0], 183)
        self.assertIn(b"FX6_R60_POWERSAVE_REALITY_SPLIT_BRIDGE", self.shim_r60)
        self.assertIn(b"FX6_R60_LANG_34_29_PARITY_BRIDGE", self.shim_r60)
        self.assertIn(b"FX6_R60_VOL_4CH_DELETE_VAULT_BRIDGE", self.shim_r60)

    def test_12_round60_shim_round59_backward_compat_excludes_r60_bridges(self) -> None:
        if self.shim_r59 is None:
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertIn(b"FX6_R59_FOCUS_ASSIST_PEAKING_BRIDGE", self.shim_r59)
        self.assertNotIn(b"FX6_R60_POWERSAVE_REALITY_SPLIT_BRIDGE", self.shim_r59)

    def test_13_round60_parse_log_extracts_all_8_r60_prefixes_and_rc(self) -> None:
        serial_text = (
            "\n".join(
                [
                    "Linux version 4.9.337-scel+ (sony@fx3)",
                    "FX6_R60_WAVE46_INIT fx3_wave46_nodes_ok=1 powersave_reality_split_ok=1 powersave_deactivation_9cond_ok=1 lang_bk_02cf019c_4lang_34vs29_ok=1 volume_0_15_4ch_5routes_ok=1 delete_confirm_cancel_first_vault_ok=1 setup_playback_survives_camreset_ok=1 emmc_write_count=0 r60_init_ok=1",
                    "FX6_R60_POWERSAVE_REALITY_SPLIT_BRIDGE ilc2210_2items_only_ok=1 dormant_monitor_4opts_appfw_ok=1 open_return_not_open_on_ok=1 sleep_deactivation_9cond_ok=1 tier0_p3_airgap_guard_ok=1 powersave_reality_split_ok=1 dormant_monitor_forced_sleep_events=0 r60_bridge_ok=1",
                    "FX6_R60_LANG_34_29_PARITY_BRIDGE bk_lang_02cf019c_4way_ok=1 fx3_34_vs_fx6_29_packs_ok=1 survives_camreset_netreset_ok=1 reset_on_initialize_only_ok=1 lang_34_29_parity_ok=1 emmc_write_count=0 p2_setting_writes=0",
                    "FX6_R60_VOL_4CH_DELETE_VAULT_BRIDGE volume_0_15_def7_ok=1 audio_4ch_5routes_ok=1 delete_confirm_cancel_first_ok=1 delete_twice_off_def_ok=1 slot1_vault_ro_blocked_ok=1 vol_4ch_delete_vault_ok=1 slot1_vault_delete_events=0",
                    "FX6_R60_LANG_TELEMETRY lang=schinese font_bank=23 str_bank=19 milestone_60th_round_33rd_realhw_99th_live=1 r60_bridge_ok=1",
                    "FX6_STAGE_B_R60_BRIDGE round=60 faithful=1 nop_count=0 milestone_60th_round_33rd_realhw_99th_live=1 emmc_write_count=0",
                    "FX6_R60_DORMANT_MON_SLOT1_DEL_GUARD dormant_mon_sleep_rc=-95 p3_airgap_5min_rc=-16 unexposed_mon_menu_rc=-2 hallucinated_open_on_rc=-2 vol_neg1_rc=-22 vol_16_rc=-22 slot1_del_first_rc=-30 slot1_del_twice_rc=-30 slot1_format_rc=-30 persistent_nvram_rc=-30 r60b_ok=1",
                    "FX6_R60_DORMANT_MON_SLOT1_DEL_RC=0",
                    "FX6_R60_CLEAN_UNMOUNT_RESET_H0_H3 stock_unmount_restored_ok=1 lang_4way_34vs29_ok=1 wave46_survives_netreset_ok=1 wave46_survives_camreset_ok=1 initialize_restores_all_wave46_defaults_ok=1 surfaces_h0_eq_h3=16 r60c_ok=1",
                ]
            )
            + "\n"
        )
        parsed = self.runner.extract_milestones(serial_text)
        r60_t = parsed["r60_telemetry"]
        self.assertEqual(r60_t["dormant_mon_slot1_del_rc"], 0)
        self.assertEqual(r60_t["wave46_init"]["powersave_reality_split_ok"], 1)
        self.assertEqual(r60_t["powersave_reality_split_bridge"]["open_return_not_open_on_ok"], 1)
        self.assertEqual(r60_t["lang_34_29_parity_bridge"]["lang_34_29_parity_ok"], 1)
        self.assertEqual(r60_t["vol_4ch_delete_vault_bridge"]["vol_4ch_delete_vault_ok"], 1)
        self.assertEqual(r60_t["lang_telemetry"]["lang"], "schinese")
        self.assertEqual(r60_t["lang_telemetry"]["milestone_60th_round_33rd_realhw_99th_live"], 1)
        self.assertEqual(r60_t["stage_b_bridge"]["round"], 60)
        self.assertEqual(r60_t["dormant_mon_slot1_del_guard"]["r60b_ok"], 1)
        self.assertEqual(r60_t["clean_unmount_reset_h0_h3"]["surfaces_h0_eq_h3"], 16)
        self.assertEqual(parsed["prefix_counts"]["FX6_R60_"], 8)

    def test_14_round60_parse_log_defaults_when_no_r60_lines_present(self) -> None:
        parsed = self.runner.extract_milestones("Linux version 4.9.337-scel+\n")
        self.assertIsNone(parsed["r60_telemetry"])
        self.assertEqual(parsed["prefix_counts"].get("FX6_R60_", 0), 0)

    def test_15_round60_runner_uses_fx6_r60_prefix_and_stage_label(self) -> None:
        self.assertIn('if args.round >= 60:\n        tmp_prefix = "fx6-r60"', self.runner_src)
        self.assertIn(
            "Milestone60thRealHw33rdRun99thLiveWave46PowerSaveMonitorSplitLang34vs29Vol015Audio4chDeleteVault",
            self.runner_src,
        )
        self.assertIn(", 59, 60]", self.runner_src)

    def test_16_round60_runner_portability_and_sanitizer_helper(self) -> None:
        self.assertIn('shutil.which("zig")', self.runner_src)
        self.assertIn("FX6_SCRATCH_DIR", self.runner_src)
        self.assertIn("def sanitize_round60_summary(", self.runner_src)
        self.assertNotIn('"/usr/bin/python3"', self.runner_src)

    def test_17_round60_summary_json_top_level_schema_and_milestone_metadata(self) -> None:
        d = self.summary
        self.assertEqual(
            d["schema"],
            "fx6-on-fx3-round60-milestone-realhw-power-save-monitor-language-volume-delete-qemu-v1",
        )
        self.assertEqual(d["round"], 60)
        self.assertIn("60th Round Milestone!", d["milestone"])
        self.assertIn("33rd Real-HW", d["milestone"])
        self.assertIn("99 Live Runs", d["milestone"])
        self.assertEqual(d["date"], "2026-11-17")
        self.assertIn("4.9.337-scel+", d["kernel_version"])
        self.assertEqual(d["raw_firmware_bytes_leaked"], 0)

    def test_18_round60_summary_json_zero_host_path_and_scratch_leaks(self) -> None:
        for forbidden in (
            "/Users/",
            "/private/tmp/",
            "/var/folders/",
            "work/_scratch/",
            "work/_tests/",
            ":8768",
        ):
            self.assertNotIn(forbidden, self.summary_raw)

    def test_19_round60_summary_audit_block_confirms_60th_round_33rd_realhw_99th_run(self) -> None:
        audit = self.summary["r60_realhw_power_save_monitor_lang_vol_delete_audit"]
        self.assertEqual(audit["round"], 60)
        self.assertEqual(audit["milestone"], 60)
        self.assertGreaterEqual(audit["milestone221_qemu_rounds"], 33)
        self.assertGreaterEqual(audit["milestone221_qemu_runs"], 99)
        self.assertGreaterEqual(audit["milestone233_qemu_rounds"], 33)
        self.assertGreaterEqual(audit["milestone233_qemu_runs"], 99)
        self.assertGreaterEqual(audit["milestone254_qemu_rounds"], 33)
        self.assertGreaterEqual(audit["milestone254_qemu_runs"], 99)
        self.assertGreaterEqual(audit["milestone264_qemu_rounds"], 33)
        self.assertGreaterEqual(audit["milestone264_qemu_runs"], 99)
        self.assertEqual(audit["total_runs"], 3)
        for k, v in audit.items():
            if isinstance(v, bool):
                self.assertTrue(v, f"Expected audit boolean {k} to be True")

    def test_20_round60_all_3_runs_present_with_kernel_4_9_337_and_zero_crashes_writes(self) -> None:
        runs = self.summary["runs"]
        self.assertEqual(list(runs.keys()), list(self.EXPECTED_RUN_KEYS))
        for rk, rv in runs.items():
            self.assertEqual(rv["round"], 60, rk)
            self.assertIn("4.9.337-scel+", rv["kernel_version"], rk)
            self.assertEqual(rv["nop_count"], 0, rk)
            self.assertEqual(rv["crashes"], 0, rk)
            self.assertEqual(rv["emmc_write_count"], 0, rk)
            self.assertGreater(rv["wall_elapsed_sec"], 0.0, rk)

    def test_21_round60_r60a_power_setting_reality_split_verified(self) -> None:
        init_t = self.summary["runs"][
            "r60a_power_save_monitor_lang_vol_delete_big6_schinese"
        ]["r60_telemetry"]["wave46_init"]
        self.assertEqual(init_t["fx3_wave46_nodes_ok"], 1)
        self.assertEqual(init_t["powersave_reality_split_ok"], 1)
        self.assertEqual(init_t["powersave_deactivation_9cond_ok"], 1)
        self.assertEqual(init_t["dormant_mon_sleep_blocked_rc"], -95)
        self.assertEqual(init_t["p3_5min_blocked_rc"], -16)
        self.assertEqual(init_t["dormant_monitor_forced_sleep_events"], 0)

    def test_22_round60_r60a_language_volume_4ch_delete_confirm_verified(self) -> None:
        init_t = self.summary["runs"][
            "r60a_power_save_monitor_lang_vol_delete_big6_schinese"
        ]["r60_telemetry"]["wave46_init"]
        self.assertEqual(init_t["lang_bk_02cf019c_4lang_34vs29_ok"], 1)
        self.assertEqual(init_t["volume_0_15_4ch_5routes_ok"], 1)
        self.assertEqual(init_t["delete_confirm_cancel_first_vault_ok"], 1)
        self.assertEqual(init_t["setup_playback_survives_camreset_ok"], 1)
        self.assertEqual(init_t["vol_oob_blocked_rc"], -22)
        self.assertEqual(init_t["slot1_del_first_rc"], -30)
        self.assertEqual(init_t["slot1_del_twice_rc"], -30)
        self.assertEqual(init_t["slot1_vault_delete_events"], 0)

    def test_23_round60_r60a_p2_cnflasha_and_slot1_ro_guards_intact(self) -> None:
        init_t = self.summary["runs"][
            "r60a_power_save_monitor_lang_vol_delete_big6_schinese"
        ]["r60_telemetry"]["wave46_init"]
        self.assertEqual(init_t["e_nd_actuator_tx_count"], 0)
        self.assertEqual(init_t["slot1_vault_writes"], 0)
        self.assertEqual(init_t["p2_write_blocked_rc"], -30)
        self.assertEqual(init_t["p2_sha256_match"], 1)
        self.assertEqual(init_t["cnflasha_sha256_match"], 1)
        self.assertEqual(init_t["slot1_vault_sha256_match"], 1)
        self.assertEqual(init_t["cnflasha_writes"], 0)
        self.assertEqual(init_t["appfw_present"], 1)
        self.assertEqual(init_t["shim_present"], 1)
        self.assertEqual(init_t["emmc_write_count"], 0)
        self.assertEqual(init_t["r60_init_ok"], 1)

    def test_24_round60_r60a_stage_b_schinese_lang_telemetry_and_bridge(self) -> None:
        r60a_t = self.summary["runs"][
            "r60a_power_save_monitor_lang_vol_delete_big6_schinese"
        ]["r60_telemetry"]
        lt = r60a_t["lang_telemetry"]
        self.assertEqual(lt["lang"], "schinese")
        self.assertEqual(lt["bk4_lang_id"], "0x02cf019c")
        self.assertEqual(lt["bk4_lang_val"], "0x19")
        self.assertEqual(lt["lang_enum"], "0x2b45_CHINESE_SIMPLIFIED")
        self.assertEqual(lt["font_bank"], 23)
        self.assertEqual(lt["str_bank"], 19)
        self.assertEqual(lt["gpe_fb"], 0)
        self.assertEqual(lt["milestone_60th_round_33rd_realhw_99th_live"], 1)
        self.assertEqual(lt["dormant_monitor_forced_sleep_events"], 0)
        self.assertEqual(lt["slot1_vault_delete_events"], 0)
        self.assertEqual(lt["unexposed_monitor_menu_spoof_events"], 0)
        self.assertEqual(lt["persistent_nvram_write_events"], 0)
        self.assertEqual(lt["e_nd_actuator_tx_count"], 0)
        self.assertEqual(lt["raw_firmware_bytes_leaked"], 0)
        sb = r60a_t["stage_b_bridge"]
        self.assertEqual(sb["round"], 60)
        self.assertEqual(sb["faithful"], 1)
        self.assertEqual(sb["nop_count"], 0)
        self.assertEqual(sb["powersave_2item_vs_4opt_dormant_9cond"], 1)
        self.assertEqual(sb["lang_bk_02cf019c_34_vs_29_4lang"], 1)
        self.assertEqual(sb["volume_0_15_4ch_5routes_delete_confirm_vault"], 1)
        self.assertEqual(sb["milestone_60th_round_33rd_realhw_99th_live"], 1)

    def test_25_round60_r60a_stage_b_3_pillar_bridges_verified(self) -> None:
        r60a_t = self.summary["runs"][
            "r60a_power_save_monitor_lang_vol_delete_big6_schinese"
        ]["r60_telemetry"]
        ps = r60a_t["powersave_reality_split_bridge"]
        self.assertEqual(ps["ilc2210_2items_only_ok"], 1)
        self.assertEqual(ps["dormant_monitor_4opts_appfw_ok"], 1)
        self.assertEqual(ps["open_return_not_open_on_ok"], 1)
        self.assertEqual(ps["sleep_deactivation_9cond_ok"], 1)
        self.assertEqual(ps["tier0_p3_airgap_guard_ok"], 1)
        self.assertEqual(ps["powersave_reality_split_ok"], 1)
        self.assertEqual(ps["dormant_monitor_forced_sleep_events"], 0)
        self.assertEqual(ps["r60_bridge_ok"], 1)

        lb = r60a_t["lang_34_29_parity_bridge"]
        self.assertEqual(lb["bk_lang_02cf019c_4way_ok"], 1)
        self.assertEqual(lb["fx3_34_vs_fx6_29_packs_ok"], 1)
        self.assertEqual(lb["survives_camreset_netreset_ok"], 1)
        self.assertEqual(lb["reset_on_initialize_only_ok"], 1)
        self.assertEqual(lb["lang_34_29_parity_ok"], 1)
        self.assertEqual(lb["p2_setting_writes"], 0)

        vb = r60a_t["vol_4ch_delete_vault_bridge"]
        self.assertEqual(vb["volume_0_15_def7_ok"], 1)
        self.assertEqual(vb["audio_4ch_5routes_ok"], 1)
        self.assertEqual(vb["delete_confirm_cancel_first_ok"], 1)
        self.assertEqual(vb["delete_twice_off_def_ok"], 1)
        self.assertEqual(vb["slot1_vault_ro_blocked_ok"], 1)
        self.assertEqual(vb["vol_4ch_delete_vault_ok"], 1)
        self.assertEqual(vb["slot1_vault_delete_events"], 0)

    def test_26_round60_r60a_gpe0_readback_ge_300k_pixels_and_87_colors(self) -> None:
        r60a = self.summary["runs"][
            "r60a_power_save_monitor_lang_vol_delete_big6_schinese"
        ]
        self.assertEqual(r60a["target_presenter"], "31procam_big6_menu_home_presenter")
        self.assertEqual(r60a["target_sid"], "0x0a")
        self.assertGreaterEqual(r60a["total_threads_seen"], 150)
        gpe0 = r60a["gpe0_readback"]
        self.assertTrue(gpe0["present"])
        self.assertEqual(gpe0["bytes"], 2211840)
        self.assertEqual(gpe0["total_pixels"], 552960)
        self.assertGreaterEqual(gpe0["nonzero_pixels"], 300000)
        self.assertEqual(gpe0["nonzero_pixels"], 346686)
        self.assertEqual(gpe0["unique_colors"], 87)

    def test_27_round60_r60a_stage_b_manifest_13_hashes_and_r60_metadata(self) -> None:
        sb = self.summary["runs"][
            "r60a_power_save_monitor_lang_vol_delete_big6_schinese"
        ]["stage_b"]
        self.assertEqual(sb["manifest_count"], 13)
        self.assertEqual(len(sb["manifest_items"]), 13)
        for item in sb["manifest_items"]:
            self.assertEqual(len(item["sha256"]), 64)
        m = sb["r60"]
        self.assertEqual(m["r60_mode"], "power_save_monitor_lang_vol_delete_big6")
        self.assertEqual(m["power_setting_option_menu_path"], "MENU -> Setup -> [Power Setting Option]")
        self.assertEqual(m["ilc2210_exposed_items"], ["Power Save Start Time", "Auto Power OFF Temp."])
        self.assertEqual(m["power_save_start_time_default"], "5 Min")
        self.assertEqual(m["auto_power_off_temp_default"], "Standard")
        self.assertFalse(m["power_save_by_monitor_exposed_in_fx3_702"])
        self.assertEqual(m["appfw_dormant_monitor_resid16"], "0x60b9")
        self.assertEqual(len(m["appfw_dormant_monitor_options"]), 4)
        self.assertEqual(len(m["sleep_deactivation_9_conditions"]), 9)
        self.assertEqual(m["language_bk_key"], "0x02cf019c")
        self.assertEqual(m["language_fx3_pack_count"], 34)
        self.assertEqual(m["language_fx6_pack_count"], 29)
        self.assertEqual(m["volume_settings_range"], [0, 15])
        self.assertEqual(m["volume_settings_default"], 7)
        self.assertEqual(
            m["audio_4ch_monitoring_routes"],
            ["CH1/CH2", "CH3/CH4", "CH1+3/CH2+4", "CH1/CH1", "CH2/CH2"],
        )
        self.assertEqual(m["audio_4ch_monitoring_default"], "CH1/CH2")
        self.assertEqual(m["headphone_35mm_max_channels"], 2)
        self.assertEqual(m["delete_confirm_default"], '"Cancel" first')
        self.assertEqual(m["delete_confirm_options"], ['"Cancel" first', '"Delete" first'])
        self.assertEqual(m["delete_pressing_twice_default"], "Off")

    def test_28_round60_r60b_dormant_monitor_sleep_and_p3_airgap_blocked(self) -> None:
        r60b_t = self.summary["runs"][
            "r60b_dormant_monitor_sleep_slot1_delete_guard"
        ]["r60_telemetry"]
        self.assertEqual(r60b_t["dormant_mon_slot1_del_rc"], 0)
        gd = r60b_t["dormant_mon_slot1_del_guard"]
        self.assertEqual(gd["dormant_mon_sleep_rc"], -95)
        self.assertEqual(gd["p3_airgap_5min_rc"], -16)
        self.assertEqual(gd["dormant_monitor_forced_sleep_events"], 0)

    def test_29_round60_r60b_unexposed_menu_hallucinated_open_on_and_vol_oob_blocked(self) -> None:
        gd = self.summary["runs"][
            "r60b_dormant_monitor_sleep_slot1_delete_guard"
        ]["r60_telemetry"]["dormant_mon_slot1_del_guard"]
        self.assertEqual(gd["unexposed_mon_menu_rc"], -2)
        self.assertEqual(gd["hallucinated_open_on_rc"], -2)
        self.assertEqual(gd["dormant_4opts_uxc_parity_ok"], 1)
        self.assertEqual(gd["vol_neg1_rc"], -22)
        self.assertEqual(gd["vol_16_rc"], -22)
        self.assertEqual(gd["headphone_4ch_bypass_events"], 0)

    def test_30_round60_r60b_slot1_delete_twice_first_format_and_nvram_blocked_erofs(self) -> None:
        gd = self.summary["runs"][
            "r60b_dormant_monitor_sleep_slot1_delete_guard"
        ]["r60_telemetry"]["dormant_mon_slot1_del_guard"]
        self.assertEqual(gd["slot1_del_first_rc"], -30)
        self.assertEqual(gd["slot1_del_twice_rc"], -30)
        self.assertEqual(gd["slot1_format_rc"], -30)
        self.assertEqual(gd["slot1_vault_delete_events"], 0)
        self.assertEqual(gd["persistent_nvram_rc"], -30)
        self.assertEqual(gd["persistent_nvram_write_events"], 0)

    def test_31_round60_r60b_slot1_vault_ro_and_zero_emmc_cnflasha_writes(self) -> None:
        gd = self.summary["runs"][
            "r60b_dormant_monitor_sleep_slot1_delete_guard"
        ]["r60_telemetry"]["dormant_mon_slot1_del_guard"]
        self.assertEqual(gd["slot1_vault_ro_blocked_rc"], -30)
        self.assertEqual(gd["slot1_vault_sha256_match"], 1)
        self.assertEqual(gd["slot1_vault_writes"], 0)
        self.assertEqual(gd["p2_write_blocked_rc"], -30)
        self.assertEqual(gd["cnflasha_ro_blocked_rc"], -30)
        self.assertEqual(gd["cnflasha_writes"], 0)
        self.assertEqual(gd["e_nd_actuator_tx_count"], 0)
        self.assertEqual(gd["emmc_write_count"], 0)
        self.assertEqual(gd["r60b_ok"], 1)

    def test_32_round60_r60c_clean_unmount_reset_tiers_verified(self) -> None:
        ci = self.summary["runs"][
            "r60c_clean_unmount_reset_tiers_h0_h3_big6_schinese"
        ]["r60_telemetry"]["clean_unmount_reset_h0_h3"]
        self.assertEqual(ci["stock_unmount_restored_ok"], 1)
        self.assertEqual(ci["lang_4way_34vs29_ok"], 1)
        self.assertEqual(ci["wave46_survives_netreset_ok"], 1)
        self.assertEqual(ci["wave46_survives_camreset_ok"], 1)
        self.assertEqual(ci["initialize_restores_all_wave46_defaults_ok"], 1)

    def test_33_round60_r60c_dlopen_and_16_h0_eq_h3_idempotent_unmount(self) -> None:
        ci = self.summary["runs"][
            "r60c_clean_unmount_reset_tiers_h0_h3_big6_schinese"
        ]["r60_telemetry"]["clean_unmount_reset_h0_h3"]
        self.assertEqual(ci["dlopen_ok"], 1)
        self.assertEqual(ci["surfaces_verified"], 16)
        self.assertEqual(ci["surfaces_h0_eq_h3"], 16)
        self.assertEqual(ci["drift_bits"], 0)
        self.assertEqual(ci["cnflasha_write_bytes"], 0)
        self.assertEqual(ci["emmc_write_bytes"], 0)
        self.assertEqual(ci["e_nd_actuator_tx_count"], 0)
        self.assertEqual(ci["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(ci["emmc_write_count"], 0)
        self.assertEqual(ci["r60c_ok"], 1)

    def test_34_round60_r60c_integrated_renders_valid_big6_gpe0_readback(self) -> None:
        r60c = self.summary["runs"][
            "r60c_clean_unmount_reset_tiers_h0_h3_big6_schinese"
        ]
        self.assertEqual(r60c["target_presenter"], "31procam_big6_menu_home_presenter")
        self.assertEqual(r60c["target_sid"], "0x0a")
        gpe0 = r60c["gpe0_readback"]
        self.assertTrue(gpe0["present"])
        self.assertEqual(gpe0["bytes"], 2211840)
        self.assertEqual(gpe0["total_pixels"], 552960)
        self.assertGreaterEqual(gpe0["nonzero_pixels"], 300000)
        self.assertEqual(gpe0["nonzero_pixels"], 346686)
        self.assertEqual(gpe0["unique_colors"], 87)

    def test_35_round60_realhw_mechanisms_verified_6_blocks_match_run_telemetry(self) -> None:
        rm = self.summary["realhw_mechanisms_verified"]
        self.assertEqual(len(rm), 6)
        r60a = self.summary["runs"][
            "r60a_power_save_monitor_lang_vol_delete_big6_schinese"
        ]["r60_telemetry"]
        r60b = self.summary["runs"][
            "r60b_dormant_monitor_sleep_slot1_delete_guard"
        ]["r60_telemetry"]
        r60c = self.summary["runs"][
            "r60c_clean_unmount_reset_tiers_h0_h3_big6_schinese"
        ]["r60_telemetry"]
        self.assertEqual(
            rm["power_save_monitor_lang_vol_delete_init"],
            r60a["wave46_init"],
        )
        self.assertEqual(
            rm["powersave_reality_split_stage_b_bridge"],
            r60a["powersave_reality_split_bridge"],
        )
        self.assertEqual(
            rm["lang_34_29_parity_stage_b_bridge"],
            r60a["lang_34_29_parity_bridge"],
        )
        self.assertEqual(
            rm["vol_4ch_delete_vault_stage_b_bridge"],
            r60a["vol_4ch_delete_vault_bridge"],
        )
        self.assertEqual(
            rm["dormant_monitor_sleep_slot1_delete_guard"],
            r60b["dormant_mon_slot1_del_guard"],
        )
        self.assertEqual(
            rm["clean_unmount_reset_tiers_and_16_h0_h3"],
            r60c["clean_unmount_reset_h0_h3"],
        )

    def test_36_round60_reset_tiers_survival_consistent_across_runs(self) -> None:
        r60a_t = self.summary["runs"][
            "r60a_power_save_monitor_lang_vol_delete_big6_schinese"
        ]["r60_telemetry"]
        r60c_ci = self.summary["runs"][
            "r60c_clean_unmount_reset_tiers_h0_h3_big6_schinese"
        ]["r60_telemetry"]["clean_unmount_reset_h0_h3"]
        self.assertEqual(r60a_t["wave46_init"]["setup_playback_survives_camreset_ok"], 1)
        self.assertEqual(r60a_t["lang_34_29_parity_bridge"]["survives_camreset_netreset_ok"], 1)
        self.assertEqual(r60a_t["lang_34_29_parity_bridge"]["reset_on_initialize_only_ok"], 1)
        self.assertEqual(r60c_ci["stock_unmount_restored_ok"], 1)
        self.assertEqual(r60c_ci["wave46_survives_netreset_ok"], 1)
        self.assertEqual(r60c_ci["wave46_survives_camreset_ok"], 1)
        self.assertEqual(r60c_ci["initialize_restores_all_wave46_defaults_ok"], 1)

    def test_37_round60_cross_round_consistency_with_r59_slot1_ro_and_zero_leaks(self) -> None:
        self.assertEqual(self.r59_summary["round"], 59)
        r59b_gd = self.r59_summary["runs"][
            "r59b_af_illum_bt_sync_pmic_5v_hdmi_2160p_guard"
        ]["r59_telemetry"]["af_illum_bt_pmic_hdmi_guard"]
        self.assertEqual(r59b_gd["slot1_vault_ro_blocked_rc"], -30)
        r60b_gd = self.summary["runs"][
            "r60b_dormant_monitor_sleep_slot1_delete_guard"
        ]["r60_telemetry"]["dormant_mon_slot1_del_guard"]
        self.assertEqual(r60b_gd["slot1_vault_ro_blocked_rc"], -30)
        self.assertEqual(r60b_gd["slot1_vault_sha256_match"], 1)
        self.assertEqual(r60b_gd["slot1_vault_delete_events"], 0)

    def test_38_round60_cross_round_consistency_with_r58_and_r57_zero_emmc_writes(self) -> None:
        self.assertEqual(self.r58_summary["round"], 58)
        self.assertEqual(self.r57_summary["round"], 57)
        r58b_gd = self.r58_summary["runs"][
            "r58b_slot1_dcim_prefix_log_gamma_assist_guard"
        ]["r58_telemetry"]["slot1_dcim_log_gamma_guard"]
        self.assertEqual(r58b_gd["emmc_write_count"], 0)
        r57a = self.r57_summary["runs"][
            "r57a_release_wo_card_lens_audio_meter_copyright_big6_schinese"
        ]["r57_telemetry"]["release_audio_copyright_init"]
        self.assertEqual(r57a["emmc_write_count"], 0)
        r60b_gd = self.summary["runs"][
            "r60b_dormant_monitor_sleep_slot1_delete_guard"
        ]["r60_telemetry"]["dormant_mon_slot1_del_guard"]
        self.assertEqual(r60b_gd["emmc_write_count"], 0)
        self.assertEqual(r60b_gd["persistent_nvram_write_events"], 0)

    def test_39_round60_cross_round_consistency_with_r59_16_h0_eq_h3(self) -> None:
        r59c = self.r59_summary["runs"][
            "r59c_clean_unmount_camreset_vs_init_h0_h3_big6_schinese"
        ]["r59_telemetry"]["clean_unmount_camreset_h0_h3"]
        self.assertEqual(r59c["surfaces_h0_eq_h3"], 16)
        r60c = self.summary["runs"][
            "r60c_clean_unmount_reset_tiers_h0_h3_big6_schinese"
        ]["r60_telemetry"]["clean_unmount_reset_h0_h3"]
        self.assertEqual(r60c["surfaces_h0_eq_h3"], 16)
        self.assertEqual(r60c["drift_bits"], 0)

    def test_40_round60_unexecuted_physical_camera_bench_boundaries_documented(self) -> None:
        bounds = self.summary["unexecuted_physical_camera_bench_boundaries"]
        self.assertEqual(len(bounds), 3)
        joined = " ".join(bounds)
        self.assertIn("Power Save by Monitor", joined)
        self.assertIn("Power Save Start Time", joined)
        self.assertIn("Language", joined)
        self.assertIn("0x02cf019c", joined)
        self.assertIn("Volume Settings", joined)
        self.assertIn("4ch Audio Monitoring", joined)
        self.assertIn("Delete confirm.", joined)

    def test_41_round60_alpha_png_exists_under_28kib_and_matches_summary_sha256(self) -> None:
        pe = self.summary["runs"][
            "r60a_power_save_monitor_lang_vol_delete_big6_schinese"
        ]["png_exports"]["alpha_png"]
        self.assertLess(len(self.alpha_png_bytes), 28672)
        self.assertLess(len(self.alpha_png_bytes), 51200)
        self.assertEqual(len(self.alpha_png_bytes), pe["bytes"])
        self.assertEqual(
            hashlib.sha256(self.alpha_png_bytes).hexdigest(), pe["sha256"]
        )

    def test_42_round60_composited_png_exists_under_28kib_and_matches_summary_sha256(self) -> None:
        pe = self.summary["runs"][
            "r60a_power_save_monitor_lang_vol_delete_big6_schinese"
        ]["png_exports"]["composited_png"]
        self.assertLess(len(self.comp_png_bytes), 28672)
        self.assertLess(len(self.comp_png_bytes), 51200)
        self.assertEqual(len(self.comp_png_bytes), pe["bytes"])
        self.assertEqual(
            hashlib.sha256(self.comp_png_bytes).hexdigest(), pe["sha256"]
        )

    def test_43_round60_alpha_png_valid_1024x540_rgba_with_transparent_and_opaque_pixels(self) -> None:
        self.assertEqual(self.alpha_dims, (1024, 540))
        self.assertEqual(self.alpha_transparent, 552960 - 346686)
        self.assertGreater(self.alpha_opaque, 300000)

    def test_44_round60_composited_png_valid_1024x540_rgba_100pct_opaque(self) -> None:
        self.assertEqual(self.comp_dims, (1024, 540))
        self.assertEqual(self.comp_opaque, 1024 * 540)

    def test_45_round60_report_readme_documents_all_3_runs_and_zero_host_leaks(self) -> None:
        for token in (
            "Round 60 Milestone",
            "Wave-46",
            "r60a",
            "r60b",
            "r60c",
            "Power Setting Option",
            "Power Save by Monitor",
            "0x02cf019c",
            "Volume Settings",
            "4ch Audio Monitoring",
            "Delete confirm.",
            "Slot-1",
            "346,686",
            "r60a-language-volume-4ch-big6-schinese-alpha.png",
            "r60a-language-volume-4ch-big6-schinese-composited.png",
        ):
            self.assertIn(token, self.r60_readme)
        for forbidden in ("/Users/", "/private/tmp/", "/var/folders/", "work/_scratch/", ":8768"):
            self.assertNotIn(forbidden, self.r60_readme)

    def test_46_round60_closure_readme_section_60_present_and_accurate(self) -> None:
        self.assertIn("## 60. Round 60", self.closure_readme)
        self.assertIn("60th Round Milestone!", self.closure_readme)
        self.assertIn("33rd Real-HW Round", self.closure_readme)
        self.assertIn("99th Live Run!", self.closure_readme)
        self.assertIn(
            "2026-11-17-round60-milestone-realhw-power-save-monitor-language-volume-delete-qemu",
            self.closure_readme,
        )

    def test_47_round60_33_plus_realhw_qemu_rounds_r28_to_r60_99_plus_runs_and_66_plus_pngs(self) -> None:
        png_total = 0
        for r in range(28, 61):
            matches = list((REPO_ROOT / "reports").glob(f"2026-??-??-round{r}-*"))
            self.assertEqual(len(matches), 1, f"Expected 1 report dir for Round {r}")
            pngs = list((matches[0] / "assets").glob("*.png"))
            self.assertEqual(len(pngs), 2, f"Expected 2 PNGs for Round {r}")
            for p in pngs:
                self.assertLess(p.stat().st_size, 51200, str(p))
            png_total += len(pngs)
        self.assertGreaterEqual(png_total, 66)
        audit = self.summary["r60_realhw_power_save_monitor_lang_vol_delete_audit"]
        self.assertGreaterEqual(audit["milestone264_qemu_rounds"], 33)
        self.assertGreaterEqual(audit["milestone264_qemu_runs"], 99)

    def test_48_round60_dual_mode_clean_room_toggle_parity_on_summary(self) -> None:
        for clean_flag in ("0", "1"):
            with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                d = json.loads(self.summary_raw)
                self.assertEqual(d["round"], 60)
                self.assertEqual(
                    d["runs"][
                        "r60a_power_save_monitor_lang_vol_delete_big6_schinese"
                    ]["r60_telemetry"]["powersave_reality_split_bridge"][
                        "powersave_reality_split_ok"
                    ],
                    1,
                )
                self.assertEqual(
                    d["runs"][
                        "r60b_dormant_monitor_sleep_slot1_delete_guard"
                    ]["r60_telemetry"]["dormant_mon_slot1_del_guard"][
                        "dormant_mon_sleep_rc"
                    ],
                    -95,
                )
                self.assertEqual(
                    d["runs"][
                        "r60c_clean_unmount_reset_tiers_h0_h3_big6_schinese"
                    ]["r60_telemetry"]["clean_unmount_reset_h0_h3"][
                        "surfaces_h0_eq_h3"
                    ],
                    16,
                )

    def test_49_round60_r60a_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"][
            "r60a_power_save_monitor_lang_vol_delete_big6_schinese"
        ]["r60_telemetry"]["wave46_init"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_50_round60_r60b_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"][
            "r60b_dormant_monitor_sleep_slot1_delete_guard"
        ]["r60_telemetry"]["dormant_mon_slot1_del_guard"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_51_round60_r60c_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"][
            "r60c_clean_unmount_reset_tiers_h0_h3_big6_schinese"
        ]["r60_telemetry"]["clean_unmount_reset_h0_h3"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_52_round60_r60a_top_colors_transparent_plus_nonzero_equals_total_pixels(self) -> None:
        gpe = self.summary["runs"][
            "r60a_power_save_monitor_lang_vol_delete_big6_schinese"
        ]["gpe0_readback"]
        color_map = {row["argb"]: row["pixels"] for row in gpe["top_colors"]}
        self.assertIn("0x00000000", color_map)
        self.assertIn("0xff000000", color_map)
        self.assertEqual(color_map["0x00000000"] + gpe["nonzero_pixels"], gpe["total_pixels"])

    def test_53_round60_r60c_top_colors_transparent_plus_nonzero_equals_total_pixels(self) -> None:
        gpe = self.summary["runs"][
            "r60c_clean_unmount_reset_tiers_h0_h3_big6_schinese"
        ]["gpe0_readback"]
        color_map = {row["argb"]: row["pixels"] for row in gpe["top_colors"]}
        self.assertIn("0x00000000", color_map)
        self.assertEqual(color_map["0x00000000"] + gpe["nonzero_pixels"], gpe["total_pixels"])

    def test_54_round60_r60a_and_r60c_wall_elapsed_and_duration_budget_sanity(self) -> None:
        r60a = self.summary["runs"][
            "r60a_power_save_monitor_lang_vol_delete_big6_schinese"
        ]
        r60c = self.summary["runs"][
            "r60c_clean_unmount_reset_tiers_h0_h3_big6_schinese"
        ]
        ci_headroom = 15.0 if os.environ.get("GITHUB_ACTIONS") == "true" else 0.0
        max_wall = 240.0 + ci_headroom if os.environ.get("GITHUB_ACTIONS") == "true" else 120.0
        self.assertGreaterEqual(r60a["duration_budget_sec"], 70)
        self.assertLessEqual(r60a["duration_budget_sec"], 120)
        self.assertGreater(r60a["wall_elapsed_sec"], 50.0)
        self.assertLess(r60a["wall_elapsed_sec"], max_wall)
        self.assertGreaterEqual(r60c["duration_budget_sec"], 70)
        self.assertLessEqual(r60c["duration_budget_sec"], 120)
        self.assertGreater(r60c["wall_elapsed_sec"], 50.0)
        self.assertLess(r60c["wall_elapsed_sec"], max_wall)

    def test_55_round60_r60b_fast_early_exit_wall_elapsed_under_20s(self) -> None:
        r60b = self.summary["runs"][
            "r60b_dormant_monitor_sleep_slot1_delete_guard"
        ]
        max_b = 45.0 + 15.0 if os.environ.get("GITHUB_ACTIONS") == "true" else 20.0
        self.assertEqual(r60b["duration_budget_sec"], 35)
        self.assertGreater(r60b["wall_elapsed_sec"], 1.0)
        self.assertLess(r60b["wall_elapsed_sec"], max_b)
        self.assertTrue(r60b["gpe0_readback"]["skipped_stock_fx3_mode"])

    def test_56_round60_faithful_invariants_preserved_across_all_3_runs(self) -> None:
        for rk, rv in self.summary["runs"].items():
            fi = rv["faithful_invariants"]
            self.assertEqual(fi["FX6_NATIVE_FAITHFUL"], 1, rk)
            self.assertEqual(fi["subst_color"], 0, rk)
            self.assertEqual(fi["subst_image"], 0, rk)
            self.assertEqual(fi["forced_render"], 0, rk)
            self.assertEqual(fi["skipped_node"], 0, rk)
            self.assertEqual(fi["lock_bypass"], 0, rk)

    def test_57_round60_all_3_runs_stage_b_manifest_count_13(self) -> None:
        for rk, rv in self.summary["runs"].items():
            self.assertEqual(rv["stage_b"]["manifest_count"], 13, rk)
            self.assertEqual(len(rv["stage_b"]["manifest_items"]), 13, rk)

    def test_58_round60_r60c_stage_b_r60_bridges_and_zero_leak_verified(self) -> None:
        r60c_t = self.summary["runs"][
            "r60c_clean_unmount_reset_tiers_h0_h3_big6_schinese"
        ]["r60_telemetry"]
        self.assertEqual(
            r60c_t["powersave_reality_split_bridge"]["powersave_reality_split_ok"], 1
        )
        self.assertEqual(
            r60c_t["lang_34_29_parity_bridge"]["lang_34_29_parity_ok"], 1
        )
        self.assertEqual(
            r60c_t["vol_4ch_delete_vault_bridge"]["vol_4ch_delete_vault_ok"], 1
        )
        self.assertEqual(
            r60c_t["powersave_reality_split_bridge"]["dormant_monitor_forced_sleep_events"],
            0,
        )
        self.assertEqual(
            r60c_t["vol_4ch_delete_vault_bridge"]["slot1_vault_delete_events"],
            0,
        )
        self.assertEqual(r60c_t["stage_b_bridge"]["e_nd_actuator_tx_count"], 0)

    def test_59_round60_all_3_runs_prefix_counts_include_fx6_r60(self) -> None:
        r60a_pc = self.summary["runs"][
            "r60a_power_save_monitor_lang_vol_delete_big6_schinese"
        ]["prefix_counts"]
        r60b_pc = self.summary["runs"][
            "r60b_dormant_monitor_sleep_slot1_delete_guard"
        ]["prefix_counts"]
        r60c_pc = self.summary["runs"][
            "r60c_clean_unmount_reset_tiers_h0_h3_big6_schinese"
        ]["prefix_counts"]
        self.assertGreater(r60a_pc["FX6_R60_"], 10)
        self.assertEqual(r60b_pc["FX6_R60_"], 3)
        self.assertGreater(r60c_pc["FX6_R60_"], 10)

    def test_60_round60_r60_meta_invariants_across_all_3_runs(self) -> None:
        for rk, rv in self.summary["runs"].items():
            m = rv["stage_b"]["r60"]
            self.assertFalse(m["power_save_by_monitor_exposed_in_fx3_702"], rk)
            self.assertEqual(m["appfw_dormant_monitor_resid16"], "0x60b9", rk)
            self.assertEqual(m["language_bk_key"], "0x02cf019c", rk)
            self.assertEqual(m["language_fx3_pack_count"], 34, rk)
            self.assertEqual(m["language_fx6_pack_count"], 29, rk)
            self.assertEqual(m["volume_settings_range"], [0, 15], rk)
            self.assertEqual(m["volume_settings_default"], 7, rk)
            self.assertEqual(m["headphone_35mm_max_channels"], 2, rk)
            self.assertEqual(m["delete_confirm_default"], '"Cancel" first', rk)
            self.assertTrue(m["wave46_survives_camera_settings_reset"], rk)
            self.assertTrue(m["wave46_survives_reset_network_set"], rk)
            self.assertTrue(m["wave46_restored_by_initialize_only"], rk)
            self.assertTrue(m["slot1_vault_read_only"], rk)
            self.assertEqual(m["slot1_vault_delete_events"], 0, rk)
            self.assertEqual(m["dormant_monitor_forced_sleep_events"], 0, rk)
            self.assertEqual(m["unexposed_monitor_menu_spoof_events"], 0, rk)
            self.assertEqual(m["persistent_nvram_write_events"], 0, rk)
            self.assertEqual(m["e_nd_actuator_tx_count"], 0, rk)
            self.assertEqual(m["raw_firmware_bytes_leaked"], 0, rk)

    def test_61_round60_sanitize_helper_redacts_host_paths_and_port_8768(self) -> None:
        dirty = {
            "run_id": "test-run",
            "lang": "schinese",
            "r60_mode": "power_save_monitor_lang_vol_delete_big6",
            "kernel_version": "Linux version 4.9.337-scel+",
            "kernel_bin": "/Users/fake/secret/kernel.bin",
            "dtb_bin": "/Users/fake/secret/guest.dtb",
            "build": {"tmp_build": "/private/tmp/build-123"},
            "stage_b": {"r60": {"r60_mode": "power_save_monitor_lang_vol_delete_big6"}},
            "r60_telemetry": {
                "wave46_init": {"r60_init_ok": 1},
                "dormant_mon_slot1_del_guard": {"r60b_ok": 1},
                "clean_unmount_reset_h0_h3": {"r60c_ok": 1, "surfaces_h0_eq_h3": 16},
            },
            "gpe0_readback": {"nonzero_pixels": 346686},
            "png_exports": {
                "alpha_png": {
                    "path": "/Users/kafu/repo/reports/2026-11-17-round60-milestone-realhw-power-save-monitor-language-volume-delete-qemu/assets/a.png"
                }
            },
            "prefix_counts": {"FX6_R60_": 10},
        }
        sanitized = self.runner.sanitize_round60_summary(dirty, dirty, dirty)
        raw = json.dumps(sanitized)
        self.assertNotIn("/Users/", raw)
        self.assertNotIn("/private/tmp/", raw)
        self.assertNotIn("kernel_bin", raw)
        self.assertNotIn("dtb_bin", raw)
        self.assertIn(
            "reports/2026-11-17-round60-milestone-realhw-power-save-monitor-language-volume-delete-qemu/assets/a.png",
            raw,
        )

    def test_62_round60_no_stray_temp_files_or_port_8768_in_repo(self) -> None:
        for bad_name in ("tmp", "scratch", ".worktrees"):
            self.assertFalse((REPO_ROOT / bad_name).exists(), bad_name)
        self.assertNotIn("8768", self.summary_raw)
        self.assertNotIn("8768", self.r60_readme)

    def test_63_round60_runner_escapes_percent_in_argparse_help_and_portable_tools(self) -> None:
        self.assertIn("ArgumentParser", self.runner_src)
        self.assertNotIn('"/usr/bin/python3"', self.runner_src)
        self.assertIn('shutil.which("zig")', self.runner_src)
        self.assertIn("FX6_SCRATCH_DIR", self.runner_src)

    def test_64_round60_test_suite_contains_at_least_64_unit_tests(self) -> None:
        methods = [m for m in dir(self) if m.startswith("test_")]
        self.assertGreaterEqual(len(methods), 64)


if __name__ == "__main__":
    unittest.main()
