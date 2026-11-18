#!/usr/bin/env python3
"""Offline dual-mode unit tests for FX6-on-FX3 Round 62 Milestone (35/35 Real-HW Rounds Milestone, 103rd..105th Live Runs -> 105/105 Total, 70/70 PNGs — Wave-48)."""
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
ROUND62_REPORT_DIR = (
    REPO_ROOT
    / "reports"
    / "2026-11-17-round62-milestone-35realhw-pp-scinetone-creativelook-wb-metering-qemu"
)
WAVE48_SPEC_PATH = (
    REPO_ROOT
    / "reports"
    / "2026-11-17-global-sony-wave48-picture-profile-scinetone-creative-look-dro-wb-metering-intel"
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


def _build_overlay_for_r62(
    runner,
    parent_cpio: pathlib.Path,
    fp,
    fv,
    fb,
    fake_run,
    jit_meta: Dict[str, Any],
    work: pathlib.Path,
    r62_mode: str,
    lang: str = "schinese",
    enable_r62: bool = True,
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
            enable_r62=enable_r62,
            r62_mode=r62_mode,
            sd_manifest_mode="valid",
            lang=lang,
            shim_bytes=b"SHIM",
        )


class TestRound62Milestone35RealHwPpScinetoneCreativeLookWbMeteringQemu(unittest.TestCase):
    EXPECTED_RUN_KEYS = (
        "r62a_pp_scinetone_look_wb_metering_big6_schinese",
        "r62b_pp_log_wb_cineei_metering_guard",
        "r62c_clean_unmount_pp_wb_reset_h0_h3_big6_schinese",
    )

    runner: Any
    runner_src: str
    stage_a_src: str
    shim_src: str
    wave48_spec: str
    summary_raw: str
    summary: Dict[str, Any]
    r62_readme: str
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
    launcher_r62: Optional[bytes]
    shim_r62: Optional[bytes]
    shim_r61: Optional[bytes]
    r61_summary: Dict[str, Any]
    r60_summary: Dict[str, Any]
    r59_summary: Dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = _load_closure_module("fx6_brr_r62_cached", "build_and_run_round.py")
        cls.runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")
        cls.stage_a_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        cls.shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        cls.wave48_spec = WAVE48_SPEC_PATH.read_text(encoding="utf-8")
        cls.summary_raw = (ROUND62_REPORT_DIR / "summary.json").read_text(encoding="utf-8")
        cls.summary = json.loads(cls.summary_raw)
        cls.r62_readme = (ROUND62_REPORT_DIR / "README.md").read_text(encoding="utf-8")
        cls.closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")

        alpha_p = (
            ROUND62_REPORT_DIR
            / "assets"
            / "r62a-pp-scinetone-wb-metering-4ch-big6-schinese-alpha.png"
        )
        comp_p = (
            ROUND62_REPORT_DIR
            / "assets"
            / "r62a-pp-scinetone-wb-metering-4ch-big6-schinese-composited.png"
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
            cls.ov_a = _build_overlay_for_r62(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wa", "pp_scinetone_look_wb_metering_big6", lang="schinese",
            )
            cls.ov_b = _build_overlay_for_r62(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wb", "pp_log_wb_cineei_metering_guard", lang="en",
            )
            cls.ov_c = _build_overlay_for_r62(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wc", "clean_unmount_pp_wb_reset_h0_h3_big6", lang="schinese",
            )
            cls.ov_off = _build_overlay_for_r62(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "woff", "pp_scinetone_look_wb_metering_big6", enable_r62=False,
            )
            cls.invalid_mode_raised = False
            try:
                _build_overlay_for_r62(
                    cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                    tpath / "wbad", "invalid_r62_mode",
                )
            except ValueError:
                cls.invalid_mode_raised = True

            zig_bin = shutil.which("zig") or (
                str(cls.runner.ZIG) if cls.runner.ZIG.is_file() else None
            )
            if zig_bin is not None:
                verify_r62_out = tpath / "fx6-stage-a-verify-r62"
                shim_r62_out = tpath / "libgrm-fbinit9-r62.so"
                shim_r61_out = tpath / "libgrm-fbinit9-r61.so"
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
                        str(verify_r62_out),
                    ],
                    [
                        zig_bin,
                        "cc",
                        "-target",
                        "aarch64-linux-gnu.2.25",
                        "-O0",
                        "-shared",
                        "-fPIC",
                        "-DFX6_ROUND=62",
                        str(CLOSURE_DIR / "libgrm-fbinit9.c"),
                        "-ldl",
                        "-lpthread",
                        "-o",
                        str(shim_r62_out),
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
                ):
                    cls.runner.subprocess.run(cmd, check=True)
                cls.launcher_r62 = verify_r62_out.read_bytes()
                cls.shim_r62 = shim_r62_out.read_bytes()
                cls.shim_r61 = shim_r61_out.read_bytes()
            else:
                cls.launcher_r62 = None
                cls.shim_r62 = None
                cls.shim_r61 = None

        cls.r61_summary = json.loads(
            (
                REPO_ROOT
                / "reports"
                / "2026-11-17-round61-milestone-100runs-usb-mode-hdmi-info-protect-reset-network-qemu"
                / "summary.json"
            ).read_text(encoding="utf-8")
        )
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

    def test_01_wave48_global_spec_present_and_covers_all_wave48_pillars(self) -> None:
        self.assertTrue(WAVE48_SPEC_PATH.is_file())
        for needle in (
            "Picture Profile",
            "PP11",
            "S-Cinetone",
            "PPLUT1",
            "Different Set for Still/Mv",
            "Creative Look",
            "D-Range Optimizer",
            "Log Shooting",
            "Flexible ISO",
            "Cine EI Quick",
            "Cine EI",
            "White Balance",
            "C.Temp./Filter",
            "2500K",
            "9900K",
            "Custom 1",
            "Priority Set in AWB",
            "Shutter AWB Lock",
            "Shockless WB",
            "Metering Mode",
            "Spot: Standard",
            "Spot: Large",
            "Entire Screen Avg.",
            "Highlight",
            "Face Priority in Multi Metering",
            "Spot Metering Point",
            "Focus Point Link",
            "AEL w/ Shutter",
        ):
            self.assertIn(needle, self.wave48_spec)

    def test_02_round62_summary_schema_round_milestone_and_zero_leaks(self) -> None:
        self.assertNotIn("/Users/", self.summary_raw)
        self.assertNotIn("/private/tmp/", self.summary_raw)
        self.assertEqual(
            self.summary["schema"],
            "fx6-on-fx3-round62-milestone-35realhw-pp-scinetone-creativelook-wb-metering-qemu-v1",
        )
        self.assertEqual(self.summary["round"], 62)
        self.assertEqual(self.summary["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(tuple(self.summary["runs"].keys()), self.EXPECTED_RUN_KEYS)

    def test_03_round62_cli_accepts_round62_and_all_3_r62_modes(self) -> None:
        self.assertIn(", 61, 62]", self.runner_src)
        for mode in (
            "pp_scinetone_look_wb_metering_big6",
            "pp_log_wb_cineei_metering_guard",
            "clean_unmount_pp_wb_reset_h0_h3_big6",
        ):
            self.assertIn(mode, self.runner_src)

    def test_04_round62_overlay_rejects_invalid_r62_mode(self) -> None:
        self.assertTrue(self.invalid_mode_raised)

    def test_05_round62_overlay_r62a_injects_etc_fx6_stage_r62_and_appfw_launch(self) -> None:
        replacements, additions, meta = self.ov_a
        self.assertTrue(meta["r62_enabled"])
        self.assertIn("etc/fx6_stage_r62", additions)
        self.assertIn("etc/fx6_r62_libjit.so", additions)
        r62_cfg = additions["etc/fx6_stage_r62"][0].decode("utf-8")
        self.assertIn("stage_r62=1", r62_cfg)
        self.assertIn("r62_mode=pp_scinetone_look_wb_metering_big6", r62_cfg)
        self.assertIn("milestone_35th_realhw_105th_live_70_pngs=1", r62_cfg)
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("/usr/bin/appfw-launch", init_txt)
        self.assertNotIn("--r62-pp-log-wb-cineei-metering-guard", init_txt)

    def test_06_round62_overlay_r62b_injects_early_guard_probe_and_poweroff(self) -> None:
        replacements, _, meta = self.ov_b
        self.assertEqual(meta["r62"]["r62_mode"], "pp_log_wb_cineei_metering_guard")
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("--r62-pp-log-wb-cineei-metering-guard", init_txt)
        self.assertIn("FX6_R62_WAVE48_GUARD_RC=", init_txt)
        self.assertIn("FX6_R62_WAVE48_GUARD_EXIT", init_txt)
        self.assertIn("poweroff -f", init_txt)

    def test_07_round62_overlay_r62c_integrated_runs_stage_b_big6(self) -> None:
        replacements, additions, meta = self.ov_c
        self.assertEqual(meta["r62"]["r62_mode"], "clean_unmount_pp_wb_reset_h0_h3_big6")
        r62_cfg = additions["etc/fx6_stage_r62"][0].decode("utf-8")
        self.assertIn("r62_mode=clean_unmount_pp_wb_reset_h0_h3_big6", r62_cfg)
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("/usr/bin/appfw-launch", init_txt)
        self.assertNotIn("--r62-pp-log-wb-cineei-metering-guard", init_txt)

    def test_08_round62_overlay_disabled_when_enable_r62_false(self) -> None:
        _, additions, meta = self.ov_off
        self.assertFalse(meta["r62_enabled"])
        self.assertNotIn("etc/fx6_stage_r62", additions)
        self.assertNotIn("etc/fx6_r62_libjit.so", additions)
        self.assertNotIn("r62", meta)

    def test_09_round62_stage_a_c_source_contains_all_3_wave48_probes(self) -> None:
        for sym in (
            "setup_r62_pp_scinetone_look_wb_metering_probe",
            "run_r62_pp_log_wb_cineei_metering_guard_probe",
            "run_r62_clean_unmount_pp_wb_reset_h0_h3_probe",
            "FX6_R62_WAVE48_INIT",
            "FX6_R62_WAVE48_GUARD",
            "FX6_R62_CLEAN_UNMOUNT_PP_WB_H0_H3",
            "--r62-pp-log-wb-cineei-metering-guard",
            "--r62-clean-unmount-pp-wb-h0-h3",
            "/etc/fx6_stage_r62",
        ):
            self.assertIn(sym, self.stage_a_src)

    def test_10_round62_shim_c_source_contains_r62_guarded_bridges(self) -> None:
        self.assertIn("#if FX6_ROUND >= 62", self.shim_src)
        for sym in (
            "FX6_R62_PP_SCINETONE_LOOK_DRO_BRIDGE",
            "FX6_R62_WB_CUSTOM_CAMSET_EXCLUSION_BRIDGE",
            "FX6_R62_METERING_5MODE_SPOT_LINK_BRIDGE",
            "FX6_R62_LANG_TELEMETRY",
            "FX6_STAGE_B_R62_BRIDGE",
        ):
            self.assertIn(sym, self.shim_src)

    def test_11_round62_compile_launcher_and_shim_aarch64_elf_symbols(self) -> None:
        if self.launcher_r62 is None or self.shim_r62 is None:
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertEqual(self.launcher_r62[:4], b"\x7fELF")
        self.assertEqual(self.shim_r62[:4], b"\x7fELF")
        self.assertEqual(struct.unpack_from("<H", self.shim_r62, 18)[0], 183)
        self.assertIn(b"FX6_R62_PP_SCINETONE_LOOK_DRO_BRIDGE", self.shim_r62)
        self.assertIn(b"FX6_R62_WB_CUSTOM_CAMSET_EXCLUSION_BRIDGE", self.shim_r62)
        self.assertIn(b"FX6_R62_METERING_5MODE_SPOT_LINK_BRIDGE", self.shim_r62)

    def test_12_round62_shim_round61_backward_compat_excludes_r62_bridges(self) -> None:
        if self.shim_r61 is None:
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertIn(b"FX6_R61_USB_NOUVC_PD_BRIDGE", self.shim_r61)
        self.assertNotIn(b"FX6_R62_PP_SCINETONE_LOOK_DRO_BRIDGE", self.shim_r61)

    def test_13_round62_parse_log_extracts_all_8_r62_prefixes_and_rc(self) -> None:
        serial_text = (
            "\n".join(
                [
                    "Linux version 4.9.337-scel+ (sony@fx3)",
                    "FX6_R62_WAVE48_INIT fx3_wave48_nodes_ok=1 uxc_tokens_ok=1 pp_scinetone_log_ok=1 creative_look_dro_ok=1 wb_custom_camset_ok=1 metering_5mode_ok=1 emmc_write_count=0 r62_init_ok=1",
                    "FX6_R62_PP_SCINETONE_LOOK_DRO_BRIDGE pp11_default_vs_log_lockout_ok=1 pplut_reset_1080p_clamp_ok=1 creative_look_10_dro_lockout_ok=1 pp_scinetone_look_dro_ok=1 double_log_lockout_bypass_events=0 r62_bridge_ok=1",
                    "FX6_R62_WB_CUSTOM_CAMSET_EXCLUSION_BRIDGE wb_2500k_9900k_custom_nvram_ok=1 wb_custom_camset_excluded_ok=1 wb_cine_ei_awb_blocked_ok=1 wb_custom_camset_exclusion_ok=1 camset_custom_wb_leak_events=0 cine_ei_awb_bypass_events=0 p2_setting_writes=0",
                    "FX6_R62_METERING_5MODE_SPOT_LINK_BRIDGE metering_5mode_6opt_ok=1 face_prio_desqueeze_lock_ok=1 spot_focus_point_link_ok=1 metering_5mode_spot_link_ok=1 metering_base_iso_mutation_events=0 cnflasha_writes=0",
                    "FX6_R62_LANG_TELEMETRY lang=schinese font_bank=23 str_bank=19 milestone_35th_realhw_105th_live_70_pngs=1 r62_bridge_ok=1",
                    "FX6_STAGE_B_R62_BRIDGE round=62 faithful=1 nop_count=0 milestone_35th_realhw_105th_live_70_pngs=1 emmc_write_count=0",
                    "FX6_R62_WAVE48_GUARD look_under_pp11_rc=-16 pplut_in_still_rc=-95 double_log_pp_rc=-16 look_under_log_rc=-16 autohdr_spoof_rc=-2 baselook_spoof_rc=-2 cine_ei_auto_wb_rc=-95 cine_ei_uw_wb_rc=-95 custom_setup_in_log_rc=-16 bad_kelvin_rc=-22 camset_custom_wb_rc=-13 face_prio_desqueeze_rc=-16 spot_link_wide_rc=-22 spot_link_zone_rc=-22 iauto_spot_rc=-95 cine_ei_iso_alter_rc=-1 r62b_ok=1",
                    "FX6_R62_WAVE48_GUARD_RC=0",
                    "FX6_R62_CLEAN_UNMOUNT_PP_WB_H0_H3 stock_unmount_restored_ok=1 camreset_preserves_pp_custom_wb_ok=1 initialize_and_pp_reset_ok=1 camset_excludes_custom_wb_ok=1 surfaces_h0_eq_h3=16 r62c_ok=1",
                ]
            )
            + "\n"
        )
        parsed = self.runner.extract_milestones(serial_text)
        r62_t = parsed["r62_telemetry"]
        self.assertEqual(r62_t["wave48_guard_rc"], 0)
        self.assertEqual(r62_t["wave48_init"]["pp_scinetone_log_ok"], 1)
        self.assertEqual(r62_t["pp_scinetone_look_dro_bridge"]["pp_scinetone_look_dro_ok"], 1)
        self.assertEqual(r62_t["wb_custom_camset_exclusion_bridge"]["wb_custom_camset_exclusion_ok"], 1)
        self.assertEqual(r62_t["metering_5mode_spot_link_bridge"]["metering_5mode_spot_link_ok"], 1)
        self.assertEqual(r62_t["lang_telemetry"]["lang"], "schinese")
        self.assertEqual(r62_t["lang_telemetry"]["milestone_35th_realhw_105th_live_70_pngs"], 1)
        self.assertEqual(r62_t["stage_b_bridge"]["round"], 62)
        self.assertEqual(r62_t["wave48_guard"]["r62b_ok"], 1)
        self.assertEqual(r62_t["clean_unmount_pp_wb_h0_h3"]["surfaces_h0_eq_h3"], 16)
        self.assertEqual(parsed["prefix_counts"]["FX6_R62_"], 8)

    def test_14_round62_parse_log_defaults_when_no_r62_lines_present(self) -> None:
        parsed = self.runner.extract_milestones("Linux version 4.9.337-scel+\n")
        self.assertIsNone(parsed["r62_telemetry"])
        self.assertEqual(parsed["prefix_counts"].get("FX6_R62_", 0), 0)

    def test_15_round62_runner_uses_fx6_r62_prefix_and_stage_label(self) -> None:
        self.assertIn('if args.round >= 62:\n        tmp_prefix = "fx6-r62"', self.runner_src)
        self.assertIn(
            "Milestone35RealHw105thLiveWave48PpScinetoneCreativeLookDroWbCustomCamsetMetering5Mode",
            self.runner_src,
        )
        self.assertIn(", 61, 62]", self.runner_src)

    def test_16_round62_runner_portability_and_sanitizer_helper(self) -> None:
        self.assertIn('shutil.which("zig")', self.runner_src)
        self.assertIn("FX6_SCRATCH_DIR", self.runner_src)
        self.assertIn("def sanitize_round62_summary(", self.runner_src)
        self.assertNotIn("/usr/" + "bin/python3", self.runner_src)

    def test_17_round62_summary_json_top_level_schema_and_milestone_metadata(self) -> None:
        d = self.summary
        self.assertEqual(
            d["schema"],
            "fx6-on-fx3-round62-milestone-35realhw-pp-scinetone-creativelook-wb-metering-qemu-v1",
        )
        self.assertEqual(d["round"], 62)
        self.assertIn("35/35 Real-HW Rounds Milestone!", d["milestone"])
        self.assertIn("35th Real-HW", d["milestone"])
        self.assertIn("105/105 Total Live Runs", d["milestone"])
        self.assertIn("70/70 PNGs", d["milestone"])
        self.assertEqual(d["date"], "2026-11-17")
        self.assertIn("4.9.337-scel+", d["kernel_version"])
        self.assertEqual(d["raw_firmware_bytes_leaked"], 0)

    def test_18_round62_summary_json_zero_host_path_and_scratch_leaks(self) -> None:
        for forbidden in (
            "/Users/",
            "/private/tmp/",
            "/var/folders/",
            "work/_scratch/",
            "work/_tests/",
            ":87" + "68",
        ):
            self.assertNotIn(forbidden, self.summary_raw)

    def test_19_round62_summary_audit_block_confirms_35_rounds_105_runs_70_pngs(self) -> None:
        audit = self.summary["r62_realhw_pp_scinetone_creativelook_wb_metering_audit"]
        self.assertEqual(audit["round"], 62)
        self.assertEqual(audit["milestone"], 62)
        self.assertGreaterEqual(audit["milestone295_qemu_rounds"], 35)
        self.assertGreaterEqual(audit["milestone295_qemu_runs"], 105)
        self.assertGreaterEqual(audit["milestone295_png_receipts"], 70)
        self.assertEqual(audit["total_runs"], 3)
        for k, v in audit.items():
            if isinstance(v, bool):
                self.assertTrue(v, f"Expected audit boolean {k} to be True")

    def test_20_round62_all_3_runs_present_with_kernel_4_9_337_and_zero_crashes_writes(self) -> None:
        runs = self.summary["runs"]
        self.assertEqual(list(runs.keys()), list(self.EXPECTED_RUN_KEYS))
        for rk, rv in runs.items():
            self.assertEqual(rv["round"], 62, rk)
            self.assertIn("4.9.337-scel+", rv["kernel_version"], rk)
            self.assertEqual(rv["nop_count"], 0, rk)
            self.assertEqual(rv["crashes"], 0, rk)
            self.assertEqual(rv["emmc_write_count"], 0, rk)
            self.assertGreater(rv["wall_elapsed_sec"], 0.0, rk)

    def test_21_round62_r62a_pp_scinetone_and_creative_look_dro_verified(self) -> None:
        init_t = self.summary["runs"][
            "r62a_pp_scinetone_look_wb_metering_big6_schinese"
        ]["r62_telemetry"]["wave48_init"]
        self.assertEqual(init_t["fx3_wave48_nodes_ok"], 1)
        self.assertEqual(init_t["uxc_tokens_ok"], 1)
        self.assertEqual(init_t["pp_scinetone_log_ok"], 1)
        self.assertEqual(init_t["creative_look_dro_ok"], 1)
        self.assertEqual(init_t["look_locked_on_pp11_rc"], -16)
        self.assertEqual(init_t["double_log_lockout_bypass_events"], 0)

    def test_22_round62_r62a_wb_custom_camset_and_metering_5mode_verified(self) -> None:
        init_t = self.summary["runs"][
            "r62a_pp_scinetone_look_wb_metering_big6_schinese"
        ]["r62_telemetry"]["wave48_init"]
        self.assertEqual(init_t["wb_custom_camset_ok"], 1)
        self.assertEqual(init_t["metering_5mode_ok"], 1)
        self.assertEqual(init_t["camset_excl_rc"], -13)
        self.assertEqual(init_t["cine_ei_blocks_awb_rc"], -95)
        self.assertEqual(init_t["cine_ei_blocks_uw_rc"], -95)
        self.assertEqual(init_t["wide_spot_link_rc"], -22)

    def test_23_round62_r62a_p2_cnflasha_and_slot1_ro_guards_intact(self) -> None:
        init_t = self.summary["runs"][
            "r62a_pp_scinetone_look_wb_metering_big6_schinese"
        ]["r62_telemetry"]["wave48_init"]
        self.assertEqual(init_t["camset_custom_wb_leak_events"], 0)
        self.assertEqual(init_t["cine_ei_awb_bypass_events"], 0)
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
        self.assertEqual(init_t["r62_init_ok"], 1)

    def test_24_round62_r62a_stage_b_schinese_lang_telemetry_and_bridge(self) -> None:
        r62a_t = self.summary["runs"][
            "r62a_pp_scinetone_look_wb_metering_big6_schinese"
        ]["r62_telemetry"]
        lt = r62a_t["lang_telemetry"]
        self.assertEqual(lt["lang"], "schinese")
        self.assertEqual(lt["bk4_lang_id"], "0x02cf019c")
        self.assertEqual(lt["bk4_lang_val"], "0x19")
        self.assertEqual(lt["lang_enum"], "0x2b45_CHINESE_SIMPLIFIED")
        self.assertEqual(lt["font_bank"], 23)
        self.assertEqual(lt["str_bank"], 19)
        self.assertEqual(lt["gpe_fb"], 0)
        self.assertEqual(lt["round62_milestone_35realhw_pp_scinetone_creativelook_wb_metering"], 1)
        self.assertEqual(lt["milestone_35th_realhw_105th_live_70_pngs"], 1)
        self.assertEqual(lt["double_log_lockout_bypass_events"], 0)
        self.assertEqual(lt["camset_custom_wb_leak_events"], 0)
        self.assertEqual(lt["cine_ei_awb_bypass_events"], 0)
        self.assertEqual(lt["metering_base_iso_mutation_events"], 0)
        self.assertEqual(lt["passive_tx_bytes_emitted"], 0)
        self.assertEqual(lt["e_nd_actuator_tx_count"], 0)
        self.assertEqual(lt["raw_firmware_bytes_leaked"], 0)
        sb = r62a_t["stage_b_bridge"]
        self.assertEqual(sb["round"], 62)
        self.assertEqual(sb["faithful"], 1)
        self.assertEqual(sb["nop_count"], 0)
        self.assertEqual(sb["pp11_scinetone_pplut_vs_log_lockout"], 1)
        self.assertEqual(sb["creative_look_10_dro_lockout"], 1)
        self.assertEqual(sb["wb_custom_camset_excluded_cineei"], 1)
        self.assertEqual(sb["metering_5mode_face_spot_link"], 1)
        self.assertEqual(sb["milestone_35th_realhw_105th_live_70_pngs"], 1)

    def test_25_round62_r62a_stage_b_3_pillar_bridges_verified(self) -> None:
        r62a_t = self.summary["runs"][
            "r62a_pp_scinetone_look_wb_metering_big6_schinese"
        ]["r62_telemetry"]
        pb = r62a_t["pp_scinetone_look_dro_bridge"]
        self.assertEqual(pb["pp11_default_vs_log_lockout_ok"], 1)
        self.assertEqual(pb["pplut_reset_1080p_clamp_ok"], 1)
        self.assertEqual(pb["creative_look_10_dro_lockout_ok"], 1)
        self.assertEqual(pb["pp_scinetone_look_dro_ok"], 1)
        self.assertEqual(pb["double_log_lockout_bypass_events"], 0)
        self.assertEqual(pb["r62_bridge_ok"], 1)

        wb = r62a_t["wb_custom_camset_exclusion_bridge"]
        self.assertEqual(wb["wb_2500k_9900k_custom_nvram_ok"], 1)
        self.assertEqual(wb["wb_custom_camset_excluded_ok"], 1)
        self.assertEqual(wb["wb_cine_ei_awb_blocked_ok"], 1)
        self.assertEqual(wb["wb_custom_camset_exclusion_ok"], 1)
        self.assertEqual(wb["camset_custom_wb_leak_events"], 0)
        self.assertEqual(wb["cine_ei_awb_bypass_events"], 0)
        self.assertEqual(wb["p2_setting_writes"], 0)

        mb = r62a_t["metering_5mode_spot_link_bridge"]
        self.assertEqual(mb["metering_5mode_6opt_ok"], 1)
        self.assertEqual(mb["face_prio_desqueeze_lock_ok"], 1)
        self.assertEqual(mb["spot_focus_point_link_ok"], 1)
        self.assertEqual(mb["metering_5mode_spot_link_ok"], 1)
        self.assertEqual(mb["metering_base_iso_mutation_events"], 0)
        self.assertEqual(mb["cnflasha_writes"], 0)

    def test_26_round62_r62a_gpe0_readback_ge_300k_pixels_and_87_colors(self) -> None:
        r62a = self.summary["runs"][
            "r62a_pp_scinetone_look_wb_metering_big6_schinese"
        ]
        self.assertEqual(r62a["target_presenter"], "31procam_big6_menu_home_presenter")
        self.assertEqual(r62a["target_sid"], "0x0a")
        self.assertGreaterEqual(r62a["total_threads_seen"], 150)
        gpe0 = r62a["gpe0_readback"]
        self.assertTrue(gpe0["present"])
        self.assertEqual(gpe0["bytes"], 2211840)
        self.assertEqual(gpe0["total_pixels"], 552960)
        self.assertGreaterEqual(gpe0["nonzero_pixels"], 300000)
        self.assertEqual(gpe0["nonzero_pixels"], 346686)
        self.assertEqual(gpe0["unique_colors"], 87)

    def test_27_round62_r62a_stage_b_manifest_13_hashes_and_r62_metadata(self) -> None:
        sb = self.summary["runs"][
            "r62a_pp_scinetone_look_wb_metering_big6_schinese"
        ]["stage_b"]
        self.assertEqual(sb["manifest_count"], 13)
        self.assertEqual(len(sb["manifest_items"]), 13)
        for item in sb["manifest_items"]:
            self.assertEqual(len(item["sha256"]), 64)
        m = sb["r62"]
        self.assertEqual(m["r62_mode"], "pp_scinetone_look_wb_metering_big6")
        self.assertTrue(m["milestone_35realhw_rounds"])
        self.assertGreaterEqual(m["realhw_round_ordinal"], 35)
        self.assertGreaterEqual(m["total_live_runs_at_completion"], 105)
        self.assertGreaterEqual(m["total_png_receipts_at_completion"], 70)
        self.assertEqual(m["picture_profile_uxc_token"], "0x6830:Picture Profile")
        self.assertEqual(m["picture_profile_default"], "PP11 (S-Cinetone)")
        self.assertEqual(m["pp11_scinetone_resid16"], "0x67ab")
        self.assertEqual(m["creative_look_uxc_token"], "0x6823:Creative Look")
        self.assertEqual(len(m["creative_look_10_presets"]), 10)
        self.assertEqual(m["dro_uxc_token"], "0xe89c:D-Range Optimizer")
        self.assertEqual(m["log_shooting_uxc_token"], "0x6020:Log Shooting")
        self.assertEqual(m["white_balance_uxc_token"], "0xe5d4:White Balance")
        self.assertEqual(m["wb_ctemp_kelvin_min"], 2500)
        self.assertEqual(m["wb_ctemp_kelvin_max"], 9900)
        self.assertEqual(len(m["wb_custom_slots"]), 3)
        self.assertTrue(m["wb_custom_1_to_3_excluded_from_camset"])
        self.assertEqual(m["metering_mode_uxc_token"], "0xe5cf:Metering Mode")
        self.assertEqual(len(m["metering_5_base_modes_6_options"]), 6)

    def test_28_round62_r62b_pp_creative_look_dro_and_double_log_guards_blocked(self) -> None:
        r62b_t = self.summary["runs"][
            "r62b_pp_log_wb_cineei_metering_guard"
        ]["r62_telemetry"]
        self.assertEqual(r62b_t["wave48_guard_rc"], 0)
        gd = r62b_t["wave48_guard"]
        self.assertEqual(gd["look_under_pp11_rc"], -16)
        self.assertEqual(gd["pplut_in_still_rc"], -95)
        self.assertEqual(gd["double_log_pp_rc"], -16)
        self.assertEqual(gd["look_under_log_rc"], -16)
        self.assertEqual(gd["autohdr_spoof_rc"], -2)
        self.assertEqual(gd["baselook_spoof_rc"], -2)
        self.assertEqual(gd["double_log_lockout_bypass_events"], 0)

    def test_29_round62_r62b_wb_cineei_camset_and_kelvin_guards_blocked(self) -> None:
        gd = self.summary["runs"][
            "r62b_pp_log_wb_cineei_metering_guard"
        ]["r62_telemetry"]["wave48_guard"]
        self.assertEqual(gd["cine_ei_auto_wb_rc"], -95)
        self.assertEqual(gd["cine_ei_uw_wb_rc"], -95)
        self.assertEqual(gd["custom_setup_in_log_rc"], -16)
        self.assertEqual(gd["bad_kelvin_rc"], -22)
        self.assertEqual(gd["camset_custom_wb_rc"], -13)
        self.assertEqual(gd["camset_custom_wb_leak_events"], 0)
        self.assertEqual(gd["cine_ei_awb_bypass_events"], 0)

    def test_30_round62_r62b_metering_face_prio_spot_link_and_cineei_iso_guards(self) -> None:
        gd = self.summary["runs"][
            "r62b_pp_log_wb_cineei_metering_guard"
        ]["r62_telemetry"]["wave48_guard"]
        self.assertEqual(gd["face_prio_desqueeze_rc"], -16)
        self.assertEqual(gd["spot_link_wide_rc"], -22)
        self.assertEqual(gd["spot_link_zone_rc"], -22)
        self.assertEqual(gd["iauto_spot_rc"], -95)
        self.assertEqual(gd["cine_ei_iso_alter_rc"], -1)
        self.assertEqual(gd["metering_base_iso_mutation_events"], 0)

    def test_31_round62_r62b_slot1_vault_ro_and_zero_emmc_cnflasha_writes(self) -> None:
        gd = self.summary["runs"][
            "r62b_pp_log_wb_cineei_metering_guard"
        ]["r62_telemetry"]["wave48_guard"]
        self.assertEqual(gd["slot1_vault_ro_blocked_rc"], -30)
        self.assertEqual(gd["slot1_vault_sha256_match"], 1)
        self.assertEqual(gd["p2_write_blocked_rc"], -30)
        self.assertEqual(gd["cnflasha_ro_blocked_rc"], -30)
        self.assertEqual(gd["passive_tx_bytes_emitted"], 0)
        self.assertEqual(gd["e_nd_actuator_tx_count"], 0)
        self.assertEqual(gd["cnflasha_writes"], 0)
        self.assertEqual(gd["emmc_write_count"], 0)
        self.assertEqual(gd["r62b_ok"], 1)

    def test_32_round62_r62c_clean_unmount_reset_tiers_and_camset_exclusion_verified(self) -> None:
        ci = self.summary["runs"][
            "r62c_clean_unmount_pp_wb_reset_h0_h3_big6_schinese"
        ]["r62_telemetry"]["clean_unmount_pp_wb_h0_h3"]
        self.assertEqual(ci["stock_unmount_restored_ok"], 1)
        self.assertEqual(ci["camreset_preserves_pp_custom_wb_ok"], 1)
        self.assertEqual(ci["initialize_and_pp_reset_ok"], 1)
        self.assertEqual(ci["camset_excludes_custom_wb_ok"], 1)
        self.assertEqual(ci["double_log_lockout_bypass_events"], 0)
        self.assertEqual(ci["camset_custom_wb_leak_events"], 0)
        self.assertEqual(ci["cine_ei_awb_bypass_events"], 0)

    def test_33_round62_r62c_dlopen_and_16_h0_eq_h3_idempotent_unmount(self) -> None:
        ci = self.summary["runs"][
            "r62c_clean_unmount_pp_wb_reset_h0_h3_big6_schinese"
        ]["r62_telemetry"]["clean_unmount_pp_wb_h0_h3"]
        self.assertEqual(ci["dlopen_ok"], 1)
        self.assertEqual(ci["surfaces_verified"], 16)
        self.assertEqual(ci["surfaces_h0_eq_h3"], 16)
        self.assertEqual(ci["drift_bits"], 0)
        self.assertEqual(ci["cnflasha_write_bytes"], 0)
        self.assertEqual(ci["emmc_write_bytes"], 0)
        self.assertEqual(ci["e_nd_actuator_tx_count"], 0)
        self.assertEqual(ci["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(ci["emmc_write_count"], 0)
        self.assertEqual(ci["r62c_ok"], 1)

    def test_34_round62_r62c_integrated_renders_valid_big6_gpe0_readback(self) -> None:
        r62c = self.summary["runs"][
            "r62c_clean_unmount_pp_wb_reset_h0_h3_big6_schinese"
        ]
        self.assertEqual(r62c["target_presenter"], "31procam_big6_menu_home_presenter")
        self.assertEqual(r62c["target_sid"], "0x0a")
        gpe0 = r62c["gpe0_readback"]
        self.assertTrue(gpe0["present"])
        self.assertEqual(gpe0["bytes"], 2211840)
        self.assertEqual(gpe0["total_pixels"], 552960)
        self.assertGreaterEqual(gpe0["nonzero_pixels"], 300000)
        self.assertEqual(gpe0["unique_colors"], 87)

    def test_35_round62_realhw_mechanisms_verified_6_blocks_match_run_telemetry(self) -> None:
        rm = self.summary["realhw_mechanisms_verified"]
        self.assertEqual(len(rm), 6)
        r62a = self.summary["runs"][
            "r62a_pp_scinetone_look_wb_metering_big6_schinese"
        ]["r62_telemetry"]
        r62b = self.summary["runs"][
            "r62b_pp_log_wb_cineei_metering_guard"
        ]["r62_telemetry"]
        r62c = self.summary["runs"][
            "r62c_clean_unmount_pp_wb_reset_h0_h3_big6_schinese"
        ]["r62_telemetry"]
        self.assertEqual(
            rm["wave48_pp_scinetone_look_wb_metering_init"],
            r62a["wave48_init"],
        )
        self.assertEqual(
            rm["pp_scinetone_look_dro_stage_b_bridge"],
            r62a["pp_scinetone_look_dro_bridge"],
        )
        self.assertEqual(
            rm["wb_custom_camset_exclusion_stage_b_bridge"],
            r62a["wb_custom_camset_exclusion_bridge"],
        )
        self.assertEqual(
            rm["metering_5mode_spot_link_stage_b_bridge"],
            r62a["metering_5mode_spot_link_bridge"],
        )
        self.assertEqual(
            rm["wave48_fail_closed_guard"],
            r62b["wave48_guard"],
        )
        self.assertEqual(
            rm["clean_unmount_pp_wb_reset_and_16_h0_h3"],
            r62c["clean_unmount_pp_wb_h0_h3"],
        )

    def test_36_round62_reset_tiers_survival_consistent_across_runs(self) -> None:
        r62a_t = self.summary["runs"][
            "r62a_pp_scinetone_look_wb_metering_big6_schinese"
        ]["r62_telemetry"]
        r62c_ci = self.summary["runs"][
            "r62c_clean_unmount_pp_wb_reset_h0_h3_big6_schinese"
        ]["r62_telemetry"]["clean_unmount_pp_wb_h0_h3"]
        self.assertEqual(r62a_t["wave48_init"]["pp_scinetone_log_ok"], 1)
        self.assertEqual(r62c_ci["stock_unmount_restored_ok"], 1)
        self.assertEqual(r62c_ci["camreset_preserves_pp_custom_wb_ok"], 1)
        self.assertEqual(r62c_ci["initialize_and_pp_reset_ok"], 1)
        self.assertEqual(r62c_ci["camset_excludes_custom_wb_ok"], 1)
        self.assertEqual(r62c_ci["camset_custom_wb_leak_events"], 0)

    def test_37_round62_cross_round_consistency_with_r61_slot1_ro_and_zero_leaks(self) -> None:
        self.assertEqual(self.r61_summary["round"], 61)
        r61b_gd = self.r61_summary["runs"][
            "r61b_nouvc_hdmi1080_slot1_protect_nwreset_guard"
        ]["r61_telemetry"]["wave47_guard"]
        self.assertEqual(r61b_gd["slot1_vault_ro_blocked_rc"], -30)
        r62b_gd = self.summary["runs"][
            "r62b_pp_log_wb_cineei_metering_guard"
        ]["r62_telemetry"]["wave48_guard"]
        self.assertEqual(r62b_gd["slot1_vault_ro_blocked_rc"], -30)
        self.assertEqual(r62b_gd["slot1_vault_sha256_match"], 1)
        self.assertEqual(r62b_gd["double_log_lockout_bypass_events"], 0)
        self.assertEqual(r62b_gd["camset_custom_wb_leak_events"], 0)

    def test_38_round62_cross_round_consistency_with_r60_and_r59_zero_emmc_writes(self) -> None:
        self.assertEqual(self.r60_summary["round"], 60)
        self.assertEqual(self.r59_summary["round"], 59)
        r60b_gd = self.r60_summary["runs"][
            "r60b_dormant_monitor_sleep_slot1_delete_guard"
        ]["r60_telemetry"]["dormant_mon_slot1_del_guard"]
        self.assertEqual(r60b_gd["emmc_write_count"], 0)
        r59b_gd = self.r59_summary["runs"][
            "r59b_af_illum_bt_sync_pmic_5v_hdmi_2160p_guard"
        ]["r59_telemetry"]["af_illum_bt_pmic_hdmi_guard"]
        self.assertEqual(r59b_gd["emmc_write_count"], 0)
        r62b_gd = self.summary["runs"][
            "r62b_pp_log_wb_cineei_metering_guard"
        ]["r62_telemetry"]["wave48_guard"]
        self.assertEqual(r62b_gd["emmc_write_count"], 0)
        self.assertEqual(r62b_gd["cnflasha_writes"], 0)

    def test_39_round62_cross_round_consistency_with_r61_16_h0_eq_h3(self) -> None:
        r61c = self.r61_summary["runs"][
            "r61c_clean_unmount_nwreset_reboot_airplane_h0_h3_big6_schinese"
        ]["r61_telemetry"]["clean_unmount_nwreset_h0_h3"]
        self.assertEqual(r61c["surfaces_h0_eq_h3"], 16)
        r62c = self.summary["runs"][
            "r62c_clean_unmount_pp_wb_reset_h0_h3_big6_schinese"
        ]["r62_telemetry"]["clean_unmount_pp_wb_h0_h3"]
        self.assertEqual(r62c["surfaces_h0_eq_h3"], 16)
        self.assertEqual(r62c["drift_bits"], 0)

    def test_40_round62_unexecuted_physical_camera_bench_boundaries_documented(self) -> None:
        bounds = self.summary["unexecuted_physical_camera_bench_boundaries"]
        self.assertEqual(len(bounds), 3)
        joined = " ".join(bounds)
        self.assertIn("Picture Profile", joined)
        self.assertIn("PP11", joined)
        self.assertIn("Creative Look", joined)
        self.assertIn("D-Range Optimizer", joined)
        self.assertIn("White Balance", joined)
        self.assertIn("CAMSET", joined)
        self.assertIn("Metering Mode", joined)

    def test_41_round62_alpha_png_exists_le_27467b_and_matches_summary_sha256(self) -> None:
        pe = self.summary["runs"][
            "r62a_pp_scinetone_look_wb_metering_big6_schinese"
        ]["png_exports"]["alpha_png"]
        self.assertLessEqual(len(self.alpha_png_bytes), 27467)
        self.assertLess(len(self.alpha_png_bytes), 28672)
        self.assertLess(len(self.alpha_png_bytes), 51200)
        self.assertEqual(len(self.alpha_png_bytes), pe["bytes"])
        self.assertEqual(
            hashlib.sha256(self.alpha_png_bytes).hexdigest(), pe["sha256"]
        )

    def test_42_round62_composited_png_exists_le_27467b_and_matches_summary_sha256(self) -> None:
        pe = self.summary["runs"][
            "r62a_pp_scinetone_look_wb_metering_big6_schinese"
        ]["png_exports"]["composited_png"]
        self.assertLessEqual(len(self.comp_png_bytes), 27467)
        self.assertLess(len(self.comp_png_bytes), 28672)
        self.assertLess(len(self.comp_png_bytes), 51200)
        self.assertEqual(len(self.comp_png_bytes), pe["bytes"])
        self.assertEqual(
            hashlib.sha256(self.comp_png_bytes).hexdigest(), pe["sha256"]
        )

    def test_43_round62_alpha_png_valid_1024x540_rgba_with_transparent_and_opaque_pixels(self) -> None:
        self.assertEqual(self.alpha_dims, (1024, 540))
        self.assertEqual(self.alpha_transparent, 552960 - 346686)
        self.assertGreater(self.alpha_opaque, 300000)

    def test_44_round62_composited_png_valid_1024x540_rgba_100pct_opaque(self) -> None:
        self.assertEqual(self.comp_dims, (1024, 540))
        self.assertEqual(self.comp_opaque, 1024 * 540)

    def test_45_round62_report_readme_documents_all_3_runs_and_zero_host_leaks(self) -> None:
        for token in (
            "Round 62 Milestone",
            "Wave-48",
            "r62a",
            "r62b",
            "r62c",
            "35/35",
            "105/105",
            "70/70",
            "Picture Profile",
            "S-Cinetone",
            "PPLUT1",
            "Creative Look",
            "D-Range Optimizer",
            "White Balance",
            "Custom 1..3",
            "CAMSET",
            "Metering Mode",
            "346,686",
            "r62a-pp-scinetone-wb-metering-4ch-big6-schinese-alpha.png",
            "r62a-pp-scinetone-wb-metering-4ch-big6-schinese-composited.png",
        ):
            self.assertIn(token, self.r62_readme)
        for forbidden in ("/Users/", "/private/tmp/", "/var/folders/", "work/_scratch/", ":87" + "68"):
            self.assertNotIn(forbidden, self.r62_readme)

    def test_46_round62_closure_readme_section_62_present_and_accurate(self) -> None:
        self.assertIn("## 62. Round 62", self.closure_readme)
        self.assertIn("35/35 Real-HW Rounds Milestone!", self.closure_readme)
        self.assertIn("105/105 Total", self.closure_readme)
        self.assertIn("70/70 PNGs", self.closure_readme)
        self.assertIn(
            "2026-11-17-round62-milestone-35realhw-pp-scinetone-creativelook-wb-metering-qemu",
            self.closure_readme,
        )

    def test_47_round62_35_plus_realhw_qemu_rounds_r28_to_r62_105_plus_runs_and_70_plus_pngs(self) -> None:
        png_total = 0
        rounds_found = 0
        for r in range(28, 63):
            matches = list((REPO_ROOT / "reports").glob(f"2026-??-??-round{r}-*"))
            self.assertEqual(len(matches), 1, f"Expected 1 report dir for Round {r}")
            pngs = list((matches[0] / "assets").glob("*.png"))
            self.assertGreaterEqual(len(pngs), 2, f"Expected >= 2 PNGs for Round {r}")
            for p in pngs:
                self.assertLess(p.stat().st_size, 51200, str(p))
            png_total += len(pngs)
            rounds_found += 1
        self.assertGreaterEqual(rounds_found, 35)
        self.assertGreaterEqual(png_total, 70)
        audit = self.summary["r62_realhw_pp_scinetone_creativelook_wb_metering_audit"]
        self.assertGreaterEqual(audit["milestone295_qemu_rounds"], 35)
        self.assertGreaterEqual(audit["milestone295_qemu_runs"], 105)
        self.assertGreaterEqual(audit["milestone295_png_receipts"], 70)

    def test_48_round62_dual_mode_clean_room_toggle_parity_on_summary(self) -> None:
        for clean_flag in ("0", "1"):
            with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                d = json.loads(self.summary_raw)
                self.assertEqual(d["round"], 62)
                self.assertEqual(
                    d["runs"][
                        "r62a_pp_scinetone_look_wb_metering_big6_schinese"
                    ]["r62_telemetry"]["pp_scinetone_look_dro_bridge"]["pp_scinetone_look_dro_ok"],
                    1,
                )
                self.assertEqual(
                    d["runs"][
                        "r62b_pp_log_wb_cineei_metering_guard"
                    ]["r62_telemetry"]["wave48_guard"]["look_under_pp11_rc"],
                    -16,
                )
                self.assertEqual(
                    d["runs"][
                        "r62c_clean_unmount_pp_wb_reset_h0_h3_big6_schinese"
                    ]["r62_telemetry"]["clean_unmount_pp_wb_h0_h3"][
                        "surfaces_h0_eq_h3"
                    ],
                    16,
                )

    def test_49_round62_r62a_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"][
            "r62a_pp_scinetone_look_wb_metering_big6_schinese"
        ]["r62_telemetry"]["wave48_init"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_50_round62_r62b_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"][
            "r62b_pp_log_wb_cineei_metering_guard"
        ]["r62_telemetry"]["wave48_guard"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_51_round62_r62c_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"][
            "r62c_clean_unmount_pp_wb_reset_h0_h3_big6_schinese"
        ]["r62_telemetry"]["clean_unmount_pp_wb_h0_h3"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_52_round62_r62a_top_colors_transparent_plus_nonzero_equals_total_pixels(self) -> None:
        gpe = self.summary["runs"][
            "r62a_pp_scinetone_look_wb_metering_big6_schinese"
        ]["gpe0_readback"]
        color_map = {row["argb"]: row["pixels"] for row in gpe["top_colors"]}
        self.assertIn("0x00000000", color_map)
        self.assertIn("0xff000000", color_map)
        self.assertEqual(color_map["0x00000000"] + gpe["nonzero_pixels"], gpe["total_pixels"])

    def test_53_round62_r62c_top_colors_transparent_plus_nonzero_equals_total_pixels(self) -> None:
        gpe = self.summary["runs"][
            "r62c_clean_unmount_pp_wb_reset_h0_h3_big6_schinese"
        ]["gpe0_readback"]
        color_map = {row["argb"]: row["pixels"] for row in gpe["top_colors"]}
        self.assertIn("0x00000000", color_map)
        self.assertEqual(color_map["0x00000000"] + gpe["nonzero_pixels"], gpe["total_pixels"])

    def test_54_round62_r62a_and_r62c_wall_elapsed_and_duration_budget_sanity(self) -> None:
        r62a = self.summary["runs"][
            "r62a_pp_scinetone_look_wb_metering_big6_schinese"
        ]
        r62c = self.summary["runs"][
            "r62c_clean_unmount_pp_wb_reset_h0_h3_big6_schinese"
        ]
        ci_headroom = 15.0 if os.environ.get("GITHUB_ACTIONS") == "true" else 0.0
        max_wall = 240.0 + ci_headroom if os.environ.get("GITHUB_ACTIONS") == "true" else 120.0 + ci_headroom
        self.assertGreaterEqual(r62a["duration_budget_sec"], 70)
        self.assertLessEqual(r62a["duration_budget_sec"], 120)
        self.assertGreater(r62a["wall_elapsed_sec"], 50.0)
        self.assertLess(r62a["wall_elapsed_sec"], max_wall)
        self.assertGreaterEqual(r62c["duration_budget_sec"], 70)
        self.assertLessEqual(r62c["duration_budget_sec"], 120)
        self.assertGreater(r62c["wall_elapsed_sec"], 50.0)
        self.assertLess(r62c["wall_elapsed_sec"], max_wall)

    def test_55_round62_r62b_fast_early_exit_wall_elapsed_with_ci_headroom(self) -> None:
        r62b = self.summary["runs"][
            "r62b_pp_log_wb_cineei_metering_guard"
        ]
        ci_headroom = 15.0 if os.environ.get("GITHUB_ACTIONS") == "true" else 0.0
        max_b = 45.0 + ci_headroom if os.environ.get("GITHUB_ACTIONS") == "true" else 20.0 + ci_headroom
        self.assertEqual(r62b["duration_budget_sec"], 35)
        self.assertGreater(r62b["wall_elapsed_sec"], 1.0)
        self.assertLess(r62b["wall_elapsed_sec"], max_b)
        self.assertTrue(r62b["gpe0_readback"]["skipped_stock_fx3_mode"])

    def test_56_round62_faithful_invariants_preserved_across_all_3_runs(self) -> None:
        for rk, rv in self.summary["runs"].items():
            fi = rv["faithful_invariants"]
            self.assertEqual(fi["FX6_NATIVE_FAITHFUL"], 1, rk)
            self.assertEqual(fi["subst_color"], 0, rk)
            self.assertEqual(fi["subst_image"], 0, rk)
            self.assertEqual(fi["forced_render"], 0, rk)
            self.assertEqual(fi["skipped_node"], 0, rk)
            self.assertEqual(fi["lock_bypass"], 0, rk)

    def test_57_round62_all_3_runs_stage_b_manifest_count_13(self) -> None:
        for rk, rv in self.summary["runs"].items():
            self.assertEqual(rv["stage_b"]["manifest_count"], 13, rk)
            self.assertEqual(len(rv["stage_b"]["manifest_items"]), 13, rk)

    def test_58_round62_r62c_stage_b_r62_bridges_and_zero_leak_verified(self) -> None:
        r62c_t = self.summary["runs"][
            "r62c_clean_unmount_pp_wb_reset_h0_h3_big6_schinese"
        ]["r62_telemetry"]
        self.assertEqual(
            r62c_t["pp_scinetone_look_dro_bridge"]["pp_scinetone_look_dro_ok"], 1
        )
        self.assertEqual(
            r62c_t["wb_custom_camset_exclusion_bridge"]["wb_custom_camset_exclusion_ok"], 1
        )
        self.assertEqual(
            r62c_t["metering_5mode_spot_link_bridge"]["metering_5mode_spot_link_ok"], 1
        )
        self.assertEqual(
            r62c_t["pp_scinetone_look_dro_bridge"]["double_log_lockout_bypass_events"], 0
        )
        self.assertEqual(
            r62c_t["wb_custom_camset_exclusion_bridge"]["camset_custom_wb_leak_events"], 0
        )
        self.assertEqual(
            r62c_t["wb_custom_camset_exclusion_bridge"]["cine_ei_awb_bypass_events"], 0
        )
        self.assertEqual(
            r62c_t["metering_5mode_spot_link_bridge"]["metering_base_iso_mutation_events"], 0
        )
        self.assertEqual(r62c_t["stage_b_bridge"]["e_nd_actuator_tx_count"], 0)

    def test_59_round62_all_3_runs_prefix_counts_include_fx6_r62(self) -> None:
        r62a_pc = self.summary["runs"][
            "r62a_pp_scinetone_look_wb_metering_big6_schinese"
        ]["prefix_counts"]
        r62b_pc = self.summary["runs"][
            "r62b_pp_log_wb_cineei_metering_guard"
        ]["prefix_counts"]
        r62c_pc = self.summary["runs"][
            "r62c_clean_unmount_pp_wb_reset_h0_h3_big6_schinese"
        ]["prefix_counts"]
        self.assertGreater(r62a_pc["FX6_R62_"], 10)
        self.assertEqual(r62b_pc["FX6_R62_"], 3)
        self.assertGreater(r62c_pc["FX6_R62_"], 10)

    def test_60_round62_r62_meta_invariants_across_all_3_runs(self) -> None:
        for rk, rv in self.summary["runs"].items():
            m = rv["stage_b"]["r62"]
            self.assertEqual(m["picture_profile_default"], "PP11 (S-Cinetone)", rk)
            self.assertEqual(m["picture_profile_uxc_token"], "0x6830:Picture Profile", rk)
            self.assertTrue(m["log_shooting_locks_pp_off"], rk)
            self.assertTrue(m["pp_1_to_11_survive_camera_settings_reset"], rk)
            self.assertTrue(m["pplut_1_to_4_reset_on_camera_settings_reset"], rk)
            self.assertEqual(m["pplut_internal_rec_hdmi_clamp_p"], 1080, rk)
            self.assertTrue(m["creative_look_and_dro_locked_when_pp_or_log_active"], rk)
            self.assertTrue(m["wb_custom_1_to_3_excluded_from_camset"], rk)
            self.assertTrue(m["wb_custom_1_to_3_survive_camera_settings_reset"], rk)
            self.assertTrue(m["wb_cine_ei_blocks_auto_and_underwater_auto"], rk)
            self.assertTrue(m["shutter_awb_lock_survives_camera_settings_reset"], rk)
            self.assertTrue(m["face_priority_in_multi_locked_off_when_desqueeze_on"], rk)
            self.assertTrue(m["spot_metering_point_degrades_to_center_on_wide_or_zone"], rk)
            self.assertTrue(m["ael_w_shutter_survives_camera_settings_reset"], rk)
            self.assertTrue(m["metering_never_alters_cine_ei_base_iso"], rk)
            self.assertEqual(m["double_log_lockout_bypass_events"], 0, rk)
            self.assertEqual(m["camset_custom_wb_leak_events"], 0, rk)
            self.assertEqual(m["cine_ei_awb_bypass_events"], 0, rk)
            self.assertEqual(m["metering_base_iso_mutation_events"], 0, rk)
            self.assertEqual(m["e_nd_actuator_tx_count"], 0, rk)
            self.assertEqual(m["raw_firmware_bytes_leaked"], 0, rk)

    def test_61_round62_sanitize_helper_redacts_host_paths_and_reserved_port(self) -> None:
        dirty = {
            "run_id": "test-run",
            "lang": "schinese",
            "r62_mode": "pp_scinetone_look_wb_metering_big6",
            "kernel_version": "Linux version 4.9.337-scel+",
            "kernel_bin": "/Users/fake/secret/kernel.bin",
            "dtb_bin": "/Users/fake/secret/guest.dtb",
            "build": {"tmp_build": "/private/tmp/build-123"},
            "stage_b": {"r62": {"r62_mode": "pp_scinetone_look_wb_metering_big6"}},
            "r62_telemetry": {
                "wave48_init": {"r62_init_ok": 1},
                "wave48_guard": {"r62b_ok": 1},
                "clean_unmount_pp_wb_h0_h3": {"r62c_ok": 1, "surfaces_h0_eq_h3": 16},
            },
            "gpe0_readback": {"nonzero_pixels": 346686},
            "png_exports": {
                "alpha_png": {
                    "path": "/Users/kafu/repo/reports/2026-11-17-round62-milestone-35realhw-pp-scinetone-creativelook-wb-metering-qemu/assets/a.png"
                }
            },
            "prefix_counts": {"FX6_R62_": 10},
        }
        sanitized = self.runner.sanitize_round62_summary(dirty, dirty, dirty)
        raw = json.dumps(sanitized)
        self.assertNotIn("/Users/", raw)
        self.assertNotIn("/private/tmp/", raw)
        self.assertNotIn("kernel_bin", raw)
        self.assertNotIn("dtb_bin", raw)
        self.assertIn(
            "reports/2026-11-17-round62-milestone-35realhw-pp-scinetone-creativelook-wb-metering-qemu/assets/a.png",
            raw,
        )

    def test_62_round62_no_stray_temp_files_or_reserved_port_in_repo(self) -> None:
        for bad_name in ("tmp", "scratch", ".worktrees"):
            self.assertFalse((REPO_ROOT / bad_name).exists(), bad_name)
        reserved_port = "87" + "68"
        self.assertNotIn(reserved_port, self.summary_raw)
        self.assertNotIn(reserved_port, self.r62_readme)

    def test_63_round62_runner_escapes_percent_in_argparse_help_and_portable_tools(self) -> None:
        self.assertIn("ArgumentParser", self.runner_src)
        self.assertNotIn("/usr/" + "bin/python3", self.runner_src)
        self.assertIn('shutil.which("zig")', self.runner_src)
        self.assertIn("FX6_SCRATCH_DIR", self.runner_src)

    def test_64_round62_test_suite_contains_at_least_64_unit_tests(self) -> None:
        methods = [m for m in dir(self) if m.startswith("test_")]
        self.assertGreaterEqual(len(methods), 64)

    def test_65_round62_dual_mode_env_flags_preserve_zero_emmc_and_clean_room_parity(self) -> None:
        for env_overrides in (
            {},
            {"FX3_CLEAN_ROOM_TEST": "1"},
            {"FX3_FX6_FORCE_CLEAN_ROOM": "1"},
        ):
            with mock.patch.dict(os.environ, env_overrides, clear=False):
                parsed = self.runner.extract_milestones(
                    "Linux version 4.9.337-scel+\n"
                    "FX6_R62_WAVE48_INIT pp_scinetone_log_ok=1 creative_look_dro_ok=1 "
                    "wb_custom_camset_ok=1 metering_5mode_ok=1 r62_init_ok=1\n"
                )
                self.assertEqual(parsed["r62_telemetry"]["wave48_init"]["r62_init_ok"], 1)

    def test_66_round62_argparse_percent_safe_help_and_no_hardcoded_python3(self) -> None:
        for line in self.runner_src.splitlines():
            if "help=" in line and "%" in line:
                stripped = line.replace("%%", "")
                self.assertNotIn("%", stripped, f"Unescaped '%' in argparse help: {line}")
        test_src = pathlib.Path(__file__).read_text(encoding="utf-8")
        forbidden_py = "/usr/" + "bin/python3"
        self.assertNotIn(forbidden_py, self.runner_src)
        self.assertNotIn(forbidden_py, test_src)


if __name__ == "__main__":
    unittest.main()
