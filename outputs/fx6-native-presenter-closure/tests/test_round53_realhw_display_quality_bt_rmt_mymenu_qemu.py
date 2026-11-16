#!/usr/bin/env python3
"""Offline dual-mode unit tests for FX6-on-FX3 Round 53 (26th Real-HW Round / 78th Live Run — Wave-39)."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import pathlib
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
ROUND53_REPORT_DIR = (
    REPO_ROOT
    / "reports"
    / "2026-11-15-round53-realhw-display-quality-bt-rmt-mymenu-qemu"
)
WAVE39_SPEC_PATH = (
    REPO_ROOT
    / "reports"
    / "2026-11-15-global-sony-wave39-display-quality-battery-bt-rmt-ctrl-ir-lockout-network-reset-mymenu-persist-intel"
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


def _decode_png_rgba_rows(png_bytes: bytes) -> Tuple[int, int, List[bytes]]:
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


def _build_overlay_for_r53(
    runner,
    parent_cpio: pathlib.Path,
    fp,
    fv,
    fb,
    fake_run,
    jit_meta: Dict[str, Any],
    work: pathlib.Path,
    r53_mode: str,
    lang: str = "schinese",
    enable_r53: bool = True,
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
            enable_r53=enable_r53,
            r53_mode=r53_mode,
            sd_manifest_mode="valid",
            lang=lang,
            shim_bytes=b"SHIM",
        )


class TestRound53RealHwDisplayQualityBtRmtMyMenuQemu(unittest.TestCase):
    EXPECTED_RUN_KEYS = (
        "r53a_display_quality_bt_rmt_big6_schinese",
        "r53b_mymenu_6ops_camset_persist_guard",
        "r53c_wave39_integrated_stress_big6_schinese",
    )

    runner: Any
    runner_src: str
    stage_a_src: str
    shim_src: str
    wave39_spec: str
    summary_raw: str
    summary: Dict[str, Any]
    r53_readme: str
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
    launcher_r53: Optional[bytes]
    shim_r53: Optional[bytes]
    shim_r52: Optional[bytes]
    r52_summary: Dict[str, Any]
    r50_summary: Dict[str, Any]
    r49_summary: Dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = _load_closure_module("fx6_brr_r53_cached", "build_and_run_round.py")
        cls.runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")
        cls.stage_a_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        cls.shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        cls.wave39_spec = WAVE39_SPEC_PATH.read_text(encoding="utf-8")
        cls.summary_raw = (ROUND53_REPORT_DIR / "summary.json").read_text(encoding="utf-8")
        cls.summary = json.loads(cls.summary_raw)
        cls.r53_readme = (ROUND53_REPORT_DIR / "README.md").read_text(encoding="utf-8")
        cls.closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")

        alpha_p = (
            ROUND53_REPORT_DIR
            / "assets"
            / "r53a-display-quality-btrmt-big6-schinese-alpha.png"
        )
        comp_p = (
            ROUND53_REPORT_DIR
            / "assets"
            / "r53a-display-quality-btrmt-big6-schinese-composited.png"
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
            cls.ov_a = _build_overlay_for_r53(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wa", "display_quality_bt_rmt_big6", lang="schinese",
            )
            cls.ov_b = _build_overlay_for_r53(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wb", "mymenu_6ops_camset_persist_guard", lang="en",
            )
            cls.ov_c = _build_overlay_for_r53(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wc", "wave39_integrated_stress_big6", lang="schinese",
            )
            cls.ov_off = _build_overlay_for_r53(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "woff", "display_quality_bt_rmt_big6", enable_r53=False,
            )
            cls.invalid_mode_raised = False
            try:
                _build_overlay_for_r53(
                    cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                    tpath / "wbad", "invalid_r53_mode",
                )
            except ValueError:
                cls.invalid_mode_raised = True

            if cls.runner.ZIG.is_file():
                verify_r53_out = tpath / "fx6-stage-a-verify-r53"
                shim_r53_out = tpath / "libgrm-fbinit9-r53.so"
                shim_r52_out = tpath / "libgrm-fbinit9-r52.so"
                for cmd in (
                    [
                        str(cls.runner.ZIG),
                        "cc",
                        "-target",
                        "aarch64-linux-gnu.2.25",
                        "-O0",
                        str(CLOSURE_DIR / "fx6-stage-a-verify.c"),
                        "-ldl",
                        "-lpthread",
                        "-o",
                        str(verify_r53_out),
                    ],
                    [
                        str(cls.runner.ZIG),
                        "cc",
                        "-target",
                        "aarch64-linux-gnu.2.25",
                        "-O0",
                        "-shared",
                        "-fPIC",
                        "-DFX6_ROUND=53",
                        str(CLOSURE_DIR / "libgrm-fbinit9.c"),
                        "-ldl",
                        "-lpthread",
                        "-o",
                        str(shim_r53_out),
                    ],
                    [
                        str(cls.runner.ZIG),
                        "cc",
                        "-target",
                        "aarch64-linux-gnu.2.25",
                        "-O0",
                        "-shared",
                        "-fPIC",
                        "-DFX6_ROUND=52",
                        str(CLOSURE_DIR / "libgrm-fbinit9.c"),
                        "-ldl",
                        "-lpthread",
                        "-o",
                        str(shim_r52_out),
                    ],
                ):
                    cls.runner.subprocess.run(cmd, check=True)
                cls.launcher_r53 = verify_r53_out.read_bytes()
                cls.shim_r53 = shim_r53_out.read_bytes()
                cls.shim_r52 = shim_r52_out.read_bytes()
            else:
                cls.launcher_r53 = None
                cls.shim_r53 = None
                cls.shim_r52 = None

        cls.r52_summary = json.loads(
            (
                REPO_ROOT
                / "reports"
                / "2026-11-15-round52-realhw-lock-op-parts-audio-timing-exp-step-qemu"
                / "summary.json"
            ).read_text(encoding="utf-8")
        )
        cls.r50_summary = json.loads(
            (
                REPO_ROOT
                / "reports"
                / "2026-11-15-round50-milestone-realhw-shoe-audio-4ch-wind-saveload-c3-qemu"
                / "summary.json"
            ).read_text(encoding="utf-8")
        )
        cls.r49_summary = json.loads(
            (
                REPO_ROOT
                / "reports"
                / "2026-11-15-round49-realhw-emphasized-rec-grid-hdmi-touch-sunny-qemu"
                / "summary.json"
            ).read_text(encoding="utf-8")
        )

    def test_01_wave39_global_spec_present_and_covers_all_wave39_pillars(self) -> None:
        self.assertTrue(WAVE39_SPEC_PATH.is_file())
        for needle in (
            "Display Quality",
            "Standard",
            "High",
            "NP-FZ100",
            "Bluetooth Rmt Ctrl",
            "Bluetooth Function",
            "Airplane Mode",
            "infrared remote commander",
            "Reset Network Set.",
            "My Menu Setting",
            "Display From My Menu",
            "CAMSET01.DAT",
        ):
            self.assertIn(needle, self.wave39_spec)

    def test_02_round53_summary_schema_round_milestone_and_zero_leaks(self) -> None:
        self.assertNotIn("/Users/", self.summary_raw)
        self.assertNotIn("/private/tmp/", self.summary_raw)
        self.assertEqual(
            self.summary["schema"],
            "fx6-on-fx3-round53-realhw-display-quality-bt-rmt-mymenu-qemu-v1",
        )
        self.assertEqual(self.summary["round"], 53)
        self.assertEqual(self.summary["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(tuple(self.summary["runs"].keys()), self.EXPECTED_RUN_KEYS)

    def test_03_round53_cli_accepts_round53_and_all_3_r53_modes(self) -> None:
        self.assertIn(", 53]", self.runner_src)
        self.assertIn(", 52]", self.runner_src)
        for mode in (
            "display_quality_bt_rmt_big6",
            "mymenu_6ops_camset_persist_guard",
            "wave39_integrated_stress_big6",
        ):
            self.assertIn(mode, self.runner_src)

    def test_04_round53_overlay_rejects_invalid_r53_mode(self) -> None:
        self.assertTrue(self.invalid_mode_raised)

    def test_05_round53_overlay_r53a_dispqual_btrmt_injects_etc_fx6_stage_r53_and_appfw_launch(self) -> None:
        replacements, additions, meta = self.ov_a
        self.assertTrue(meta["r53_enabled"])
        self.assertIn("etc/fx6_stage_r53", additions)
        self.assertIn("etc/fx6_r53_libjit.so", additions)
        r53_cfg = additions["etc/fx6_stage_r53"][0].decode("utf-8")
        self.assertIn("stage_r53=1", r53_cfg)
        self.assertIn("r53_mode=display_quality_bt_rmt_big6", r53_cfg)
        self.assertIn("run_26th_realhw_78th_live=1", r53_cfg)
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("/usr/bin/appfw-launch", init_txt)
        self.assertNotIn("--r53-mymenu-6ops-camset-persist", init_txt)

    def test_06_round53_overlay_r53b_mymenu_6ops_injects_early_probe_and_poweroff(self) -> None:
        replacements, _, meta = self.ov_b
        self.assertEqual(meta["r53"]["r53_mode"], "mymenu_6ops_camset_persist_guard")
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("--r53-mymenu-6ops-camset-persist", init_txt)
        self.assertIn("FX6_R53_MYMENU_6OPS_RC=", init_txt)
        self.assertIn("FX6_R53_MYMENU_6OPS_EXIT", init_txt)
        self.assertIn("poweroff -f", init_txt)

    def test_07_round53_overlay_r53c_wave39_integrated_stress_runs_stage_b_big6(self) -> None:
        replacements, additions, meta = self.ov_c
        self.assertEqual(meta["r53"]["r53_mode"], "wave39_integrated_stress_big6")
        r53_cfg = additions["etc/fx6_stage_r53"][0].decode("utf-8")
        self.assertIn("r53_mode=wave39_integrated_stress_big6", r53_cfg)
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("/usr/bin/appfw-launch", init_txt)
        self.assertNotIn("--r53-mymenu-6ops-camset-persist", init_txt)

    def test_08_round53_overlay_disabled_when_enable_r53_false(self) -> None:
        _, additions, meta = self.ov_off
        self.assertFalse(meta["r53_enabled"])
        self.assertNotIn("etc/fx6_stage_r53", additions)
        self.assertNotIn("etc/fx6_r53_libjit.so", additions)
        self.assertNotIn("r53", meta)

    def test_09_round53_stage_a_c_source_contains_all_3_wave39_probes(self) -> None:
        for sym in (
            "setup_r53_display_quality_bt_rmt_probe",
            "run_r53_mymenu_6ops_camset_persist_probe",
            "run_r53_wave39_integrated_stress_probe",
            "FX6_R53_DISPQUAL_BTRMT_INIT",
            "FX6_R53_MYMENU_6OPS_PERSIST",
            "FX6_R53_INTEGRATED_STRESS",
            "--r53-mymenu-6ops-camset-persist",
            "--r53-wave39-integrated-stress",
            "/etc/fx6_stage_r53",
        ):
            self.assertIn(sym, self.stage_a_src)

    def test_10_round53_shim_c_source_contains_r53_guarded_bridges(self) -> None:
        self.assertIn("#if FX6_ROUND >= 53", self.shim_src)
        for sym in (
            "FX6_R53_DISPQUAL_BTRMT_BRIDGE",
            "FX6_R53_BTRMT_IR_NETRESET_BRIDGE",
            "FX6_R53_MYMENU_6OPS_PERSIST_BRIDGE",
            "FX6_R53_LANG_TELEMETRY",
            "FX6_STAGE_B_R53_BRIDGE",
        ):
            self.assertIn(sym, self.shim_src)

    def test_11_round53_compile_launcher_and_shim_aarch64_elf_symbols(self) -> None:
        if self.launcher_r53 is None or self.shim_r53 is None:
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertEqual(self.launcher_r53[:4], b"\x7fELF")
        self.assertEqual(self.shim_r53[:4], b"\x7fELF")
        self.assertEqual(struct.unpack_from("<H", self.shim_r53, 18)[0], 183)
        self.assertIn(b"FX6_R53_DISPQUAL_BTRMT_BRIDGE", self.shim_r53)
        self.assertIn(b"FX6_R53_BTRMT_IR_NETRESET_BRIDGE", self.shim_r53)
        self.assertIn(b"FX6_R53_MYMENU_6OPS_PERSIST_BRIDGE", self.shim_r53)

    def test_12_round53_shim_round52_backward_compat_excludes_r53_bridges(self) -> None:
        if self.shim_r52 is None:
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertIn(b"FX6_R52_LOCK_OP_PARTS_BRIDGE", self.shim_r52)
        self.assertNotIn(b"FX6_R53_DISPQUAL_BTRMT_BRIDGE", self.shim_r52)

    def test_13_round53_parse_log_extracts_all_8_r53_prefixes_and_rc(self) -> None:
        serial_text = (
            "\n".join(
                [
                    "Linux version 4.9.337-scel+ (sony@fx3)",
                    "FX6_R53_DISPQUAL_BTRMT_INIT fx3_display_quality_node_ok=1 display_quality_2modes_verified=2 bt_rmt_2modes_verified=2 passive_tx_bytes_emitted=0 setup_vs_network_reset_split_ok=1 r53_init_ok=1",
                    "FX6_R53_DISPQUAL_BTRMT_BRIDGE display_quality_2modes_verified=2 high_increases_npfz100_drain_ok=1 dispqual_ok=1 r53_bridge_ok=1",
                    "FX6_R53_BTRMT_IR_NETRESET_BRIDGE bt_rmt_2modes_verified=2 passive_tx_bytes_emitted=0 bt_rmt_on_locks_out_ir_sircs_ok=1 bt_rmt_reset_by_netreset_ok=1 bt_rmt_ir_netreset_ok=1",
                    "FX6_R53_MYMENU_6OPS_PERSIST_BRIDGE mymenu_6ops_verified=6 mymenu_max_30_items_ok=1 camset01_mymenu_roundtrip_ok=1 mymenu_persist_ok=1",
                    "FX6_R53_LANG_TELEMETRY lang=schinese font_bank=23 str_bank=19 run_26th_realhw_78th_live=1 r53_bridge_ok=1",
                    "FX6_STAGE_B_R53_BRIDGE round=53 faithful=1 nop_count=0 run_26th_realhw_78th_live=1 emmc_write_count=0",
                    "FX6_R53_MYMENU_6OPS_PERSIST mymenu_6ops_verified=6 mymenu_max_30_items_ok=1 slot1_vault_writes=0 r53b_ok=1",
                    "FX6_R53_MYMENU_6OPS_RC=0",
                    "FX6_R53_INTEGRATED_STRESS tier0_standard_low_power_ok=1 passive_tx_bytes_emitted=0 surfaces_h0_eq_h3=16 e_nd_actuator_tx_count=0 raw_firmware_bytes_leaked=0 r53c_ok=1",
                ]
            )
            + "\n"
        )
        parsed = self.runner.extract_milestones(serial_text)
        r53_t = parsed["r53_telemetry"]
        self.assertEqual(r53_t["mymenu_6ops_rc"], 0)
        self.assertEqual(r53_t["dispqual_btrmt_init"]["display_quality_2modes_verified"], 2)
        self.assertEqual(r53_t["dispqual_btrmt_init"]["setup_vs_network_reset_split_ok"], 1)
        self.assertEqual(r53_t["dispqual_btrmt_bridge"]["high_increases_npfz100_drain_ok"], 1)
        self.assertEqual(r53_t["btrmt_ir_netreset_bridge"]["bt_rmt_reset_by_netreset_ok"], 1)
        self.assertEqual(r53_t["mymenu_persist_bridge"]["mymenu_6ops_verified"], 6)
        self.assertEqual(r53_t["lang_telemetry"]["lang"], "schinese")
        self.assertEqual(r53_t["lang_telemetry"]["run_26th_realhw_78th_live"], 1)
        self.assertEqual(r53_t["stage_b_bridge"]["round"], 53)
        self.assertEqual(r53_t["mymenu_6ops_persist"]["r53b_ok"], 1)
        self.assertEqual(r53_t["integrated_stress"]["surfaces_h0_eq_h3"], 16)
        self.assertEqual(parsed["prefix_counts"]["FX6_R53_"], 8)

    def test_14_round53_parse_log_defaults_when_no_r53_lines_present(self) -> None:
        parsed = self.runner.extract_milestones("Linux version 4.9.337-scel+\n")
        self.assertIsNone(parsed["r53_telemetry"])
        self.assertEqual(parsed["prefix_counts"].get("FX6_R53_", 0), 0)

    def test_15_round53_runner_uses_fx6_r53_prefix_and_stage_label_and_r52_compat(self) -> None:
        self.assertIn('if args.round >= 53:\n        tmp_prefix = "fx6-r53"', self.runner_src)
        self.assertIn(
            "Milestone26thRealHw78thRunWave39DisplayQualityBtRmtCtrlIrLockoutNetResetMyMenu6OpsPersist",
            self.runner_src,
        )
        self.assertIn("FX6_SCRATCH_DIR", self.runner_src)
        self.assertIn("# r52_test_compat:", self.runner_src)
        self.assertIn(", 53]", self.runner_src)

    def test_16_round53_wave39_intel_spec_documents_exact_3way_reset_matrix(self) -> None:
        for token in (
            "Camera Settings Reset",
            "Reset Network Set.",
            "Initialize",
            "Delete All",
            "Delete Page",
            "Sort Item",
            "Add Item",
            "Delete Item",
        ):
            self.assertIn(token, self.wave39_spec)

    def test_17_round53_summary_json_top_level_schema_and_milestone_metadata(self) -> None:
        d = self.summary
        self.assertEqual(
            d["schema"],
            "fx6-on-fx3-round53-realhw-display-quality-bt-rmt-mymenu-qemu-v1",
        )
        self.assertEqual(d["round"], 53)
        self.assertIn("26th Real-HW QEMU Round", d["milestone"])
        self.assertIn("78 Live Runs", d["milestone"])
        self.assertEqual(d["date"], "2026-11-15")
        self.assertIn("4.9.337-scel+", d["kernel_version"])
        self.assertEqual(d["raw_firmware_bytes_leaked"], 0)

    def test_18_round53_summary_json_zero_host_path_and_scratch_leaks(self) -> None:
        for forbidden in (
            "/Users/",
            "/private/tmp/",
            "/var/folders/",
            "work/_scratch/",
            "work/_tests/",
        ):
            self.assertNotIn(forbidden, self.summary_raw)

    def test_19_round53_summary_audit_block_confirms_26th_round_78th_run_and_all_booleans(self) -> None:
        audit = self.summary["r53_realhw_display_quality_bt_rmt_mymenu_audit"]
        self.assertEqual(audit["round"], 53)
        self.assertEqual(audit["milestone"], 53)
        self.assertEqual(audit["milestone233_qemu_rounds"], 26)
        self.assertEqual(audit["milestone233_qemu_runs"], 78)
        self.assertEqual(audit["milestone254_qemu_rounds"], 26)
        self.assertEqual(audit["milestone254_qemu_runs"], 78)
        self.assertEqual(audit["total_runs"], 3)
        for k, v in audit.items():
            if isinstance(v, bool):
                self.assertTrue(v, f"Expected audit boolean {k} to be True")

    def test_20_round53_all_3_runs_present_with_kernel_4_9_337_and_zero_crashes_writes(self) -> None:
        runs = self.summary["runs"]
        self.assertEqual(list(runs.keys()), list(self.EXPECTED_RUN_KEYS))
        for rk, rv in runs.items():
            self.assertEqual(rv["round"], 53, rk)
            self.assertIn("4.9.337-scel+", rv["kernel_version"], rk)
            self.assertEqual(rv["nop_count"], 0, rk)
            self.assertEqual(rv["crashes"], 0, rk)
            self.assertEqual(rv["emmc_write_count"], 0, rk)
            self.assertGreater(rv["wall_elapsed_sec"], 0.0, rk)

    def test_21_round53_r53a_display_quality_standard_vs_high_battery_and_setup_survival(self) -> None:
        init_t = self.summary["runs"]["r53a_display_quality_bt_rmt_big6_schinese"][
            "r53_telemetry"
        ]["dispqual_btrmt_init"]
        self.assertEqual(init_t["fx3_display_quality_node_ok"], 1)
        self.assertEqual(init_t["display_quality_default_standard_ok"], 1)
        self.assertEqual(init_t["invalid_display_quality_rc"], -22)
        self.assertEqual(init_t["display_quality_2modes_verified"], 2)
        self.assertEqual(init_t["high_increases_npfz100_drain_ok"], 1)
        self.assertEqual(init_t["tier0_bench_standard_low_power_ok"], 1)
        self.assertEqual(init_t["display_quality_survives_camreset_ok"], 1)
        self.assertEqual(init_t["display_quality_survives_netreset_ok"], 1)
        self.assertEqual(init_t["initialize_restores_display_quality_standard_ok"], 1)

    def test_22_round53_r53a_bt_rmt_ctrl_prerequisites_and_airplane_mode_zero_rf_suppression(self) -> None:
        init_t = self.summary["runs"]["r53a_display_quality_bt_rmt_big6_schinese"][
            "r53_telemetry"
        ]["dispqual_btrmt_init"]
        self.assertEqual(init_t["fx3_bt_rmt_ctrl_node_ok"], 1)
        self.assertEqual(init_t["bt_rmt_default_off_ok"], 1)
        self.assertEqual(init_t["invalid_bt_rmt_rc"], -22)
        self.assertEqual(init_t["bt_rmt_2modes_verified"], 2)
        self.assertEqual(init_t["bt_func_off_prerequisite_rc"], -95)
        self.assertEqual(init_t["airplane_on_bt_rmt_suppressed_ok"], 1)
        self.assertEqual(init_t["passive_tx_bytes_emitted"], 0)

    def test_23_round53_r53a_bt_rmt_ctrl_ir_sircs_lockout_and_network_reset_split(self) -> None:
        init_t = self.summary["runs"]["r53a_display_quality_bt_rmt_big6_schinese"][
            "r53_telemetry"
        ]["dispqual_btrmt_init"]
        self.assertEqual(init_t["bt_rmt_on_locks_out_ir_sircs_rc"], -16)
        self.assertEqual(init_t["ir_sircs_usable_when_bt_rmt_off_ok"], 1)
        self.assertEqual(init_t["ir_sircs_bt_rmt_conflict_events"], 0)
        self.assertEqual(init_t["bt_rmt_survives_camreset_ok"], 1)
        self.assertEqual(init_t["bt_rmt_reset_by_netreset_ok"], 1)
        self.assertEqual(init_t["initialize_restores_bt_rmt_off_ok"], 1)
        self.assertEqual(init_t["setup_vs_network_reset_split_ok"], 1)

    def test_24_round53_r53a_p2_cnflasha_and_slot1_ro_guards_intact(self) -> None:
        init_t = self.summary["runs"]["r53a_display_quality_bt_rmt_big6_schinese"][
            "r53_telemetry"
        ]["dispqual_btrmt_init"]
        self.assertEqual(init_t["p2_write_blocked_rc"], -30)
        self.assertEqual(init_t["p2_sha256_match"], 1)
        self.assertEqual(init_t["cnflasha_sha256_match"], 1)
        self.assertEqual(init_t["slot1_vault_sha256_match"], 1)
        self.assertEqual(init_t["cnflasha_writes"], 0)
        self.assertEqual(init_t["appfw_present"], 1)
        self.assertEqual(init_t["shim_present"], 1)
        self.assertEqual(init_t["emmc_write_count"], 0)
        self.assertEqual(init_t["r53_init_ok"], 1)

    def test_25_round53_r53a_stage_b_schinese_lang_telemetry_and_bridges(self) -> None:
        r53a_t = self.summary["runs"]["r53a_display_quality_bt_rmt_big6_schinese"]["r53_telemetry"]
        lt = r53a_t["lang_telemetry"]
        self.assertEqual(lt["lang"], "schinese")
        self.assertEqual(lt["bk4_lang_id"], "0x02cf019c")
        self.assertEqual(lt["bk4_lang_val"], "0x19")
        self.assertEqual(lt["lang_enum"], "0x2b45_CHINESE_SIMPLIFIED")
        self.assertEqual(lt["font_bank"], 23)
        self.assertEqual(lt["str_bank"], 19)
        self.assertEqual(lt["gpe_fb"], 0)
        self.assertEqual(lt["run_26th_realhw_78th_live"], 1)
        self.assertEqual(lt["passive_tx_bytes_emitted"], 0)
        self.assertEqual(lt["e_nd_actuator_tx_count"], 0)
        self.assertEqual(lt["raw_firmware_bytes_leaked"], 0)
        sb = r53a_t["stage_b_bridge"]
        self.assertEqual(sb["round"], 53)
        self.assertEqual(sb["faithful"], 1)
        self.assertEqual(sb["nop_count"], 0)
        self.assertEqual(sb["display_quality_standard_high_persist"], 1)
        self.assertEqual(sb["bt_rmt_ctrl_ir_lockout_netreset_split"], 1)
        self.assertEqual(sb["mymenu_6ops_camset_persist"], 1)

    def test_26_round53_r53a_stage_b_dispqual_btrmt_and_mymenu_bridges_verified(self) -> None:
        r53a_t = self.summary["runs"]["r53a_display_quality_bt_rmt_big6_schinese"]["r53_telemetry"]
        db = r53a_t["dispqual_btrmt_bridge"]
        self.assertEqual(db["display_quality_2modes_verified"], 2)
        self.assertEqual(db["high_increases_npfz100_drain_ok"], 1)
        self.assertEqual(db["display_quality_survives_camreset_netreset_ok"], 1)
        self.assertEqual(db["dispqual_ok"], 1)
        bb = r53a_t["btrmt_ir_netreset_bridge"]
        self.assertEqual(bb["bt_rmt_2modes_verified"], 2)
        self.assertEqual(bb["passive_tx_bytes_emitted"], 0)
        self.assertEqual(bb["bt_rmt_on_locks_out_ir_sircs_ok"], 1)
        self.assertEqual(bb["bt_rmt_reset_by_netreset_ok"], 1)
        mb = r53a_t["mymenu_persist_bridge"]
        self.assertEqual(mb["mymenu_6ops_verified"], 6)
        self.assertEqual(mb["mymenu_max_30_items_ok"], 1)
        self.assertEqual(mb["camset01_mymenu_roundtrip_ok"], 1)

    def test_27_round53_r53a_gpe0_readback_exact_346686_pixels_and_87_colors(self) -> None:
        r53a = self.summary["runs"]["r53a_display_quality_bt_rmt_big6_schinese"]
        self.assertEqual(r53a["target_presenter"], "31procam_big6_menu_home_presenter")
        self.assertEqual(r53a["target_sid"], "0x0a")
        self.assertGreaterEqual(r53a["total_threads_seen"], 150)
        gpe0 = r53a["gpe0_readback"]
        self.assertTrue(gpe0["present"])
        self.assertEqual(gpe0["bytes"], 2211840)
        self.assertEqual(gpe0["total_pixels"], 552960)
        self.assertEqual(gpe0["nonzero_pixels"], 346686)
        self.assertEqual(gpe0["unique_colors"], 87)

    def test_28_round53_r53a_stage_b_manifest_13_hashes_and_r53_metadata(self) -> None:
        sb = self.summary["runs"]["r53a_display_quality_bt_rmt_big6_schinese"]["stage_b"]
        self.assertEqual(sb["manifest_count"], 13)
        self.assertEqual(len(sb["manifest_items"]), 13)
        for item in sb["manifest_items"]:
            self.assertEqual(len(item["sha256"]), 64)
        r53_meta = sb["r53"]
        self.assertEqual(r53_meta["r53_mode"], "display_quality_bt_rmt_big6")
        self.assertEqual(r53_meta["display_quality_modes"], ["Standard", "High"])
        self.assertEqual(r53_meta["bt_rmt_ctrl_modes"], ["Off", "On"])
        self.assertEqual(
            r53_meta["my_menu_6_operations"],
            [
                "Add Item",
                "Sort Item",
                "Delete Item",
                "Delete Page",
                "Delete All",
                "Display From My Menu",
            ],
        )
        self.assertEqual(r53_meta["my_menu_max_total_items"], 30)

    def test_29_round53_r53b_mymenu_6_operations_and_30_item_capacity(self) -> None:
        r53b_t = self.summary["runs"]["r53b_mymenu_6ops_camset_persist_guard"]["r53_telemetry"]
        self.assertEqual(r53b_t["mymenu_6ops_rc"], 0)
        mm = r53b_t["mymenu_6ops_persist"]
        self.assertEqual(mm["fx3_mymenu_node_ok"], 1)
        self.assertEqual(mm["mymenu_6ops_verified"], 6)
        self.assertEqual(mm["mymenu_max_pages"], 5)
        self.assertEqual(mm["mymenu_max_items_per_page"], 6)
        self.assertEqual(mm["mymenu_max_30_items_ok"], 1)
        self.assertEqual(mm["mymenu_duplicate_item_rc"], -17)
        self.assertEqual(mm["mymenu_31st_item_overflow_rc"], -28)
        self.assertEqual(mm["mymenu_sort_item_ok"], 1)
        self.assertEqual(mm["mymenu_delete_item_ok"], 1)
        self.assertEqual(mm["mymenu_delete_page_ok"], 1)
        self.assertEqual(mm["mymenu_delete_all_ok"], 1)

    def test_30_round53_r53b_display_from_mymenu_off_default_and_menu_press_routing(self) -> None:
        mm = self.summary["runs"]["r53b_mymenu_6ops_camset_persist_guard"]["r53_telemetry"][
            "mymenu_6ops_persist"
        ]
        self.assertEqual(mm["display_from_mymenu_default_off_ok"], 1)
        self.assertEqual(mm["invalid_display_from_mymenu_rc"], -22)
        self.assertEqual(mm["display_from_mymenu_2modes_verified"], 2)
        self.assertEqual(mm["menu_press_target_tab_routing_ok"], 1)

    def test_31_round53_r53b_mymenu_survives_camera_and_network_reset_cleared_by_initialize(self) -> None:
        mm = self.summary["runs"]["r53b_mymenu_6ops_camset_persist_guard"]["r53_telemetry"][
            "mymenu_6ops_persist"
        ]
        self.assertEqual(mm["mymenu_survives_camreset_ok"], 1)
        self.assertEqual(mm["mymenu_survives_netreset_ok"], 1)
        self.assertEqual(mm["initialize_clears_mymenu_and_display_from_mymenu_ok"], 1)

    def test_32_round53_r53b_camset01_roundtrip_and_slot1_vault_read_only(self) -> None:
        mm = self.summary["runs"]["r53b_mymenu_6ops_camset_persist_guard"]["r53_telemetry"][
            "mymenu_6ops_persist"
        ]
        self.assertEqual(mm["camset01_mymenu_roundtrip_ok"], 1)
        self.assertEqual(mm["slot1_vault_ro_blocked_rc"], -30)
        self.assertEqual(mm["slot1_vault_sha256_match"], 1)
        self.assertEqual(mm["slot1_vault_writes"], 0)
        self.assertEqual(mm["p2_write_blocked_rc"], -30)
        self.assertEqual(mm["cnflasha_ro_blocked_rc"], -30)
        self.assertEqual(mm["cnflasha_writes"], 0)
        self.assertEqual(mm["emmc_write_count"], 0)
        self.assertEqual(mm["r53b_ok"], 1)

    def test_33_round53_r53c_integrated_stress_tier0_low_power_and_airplane_bt_ir_determinism(self) -> None:
        st = self.summary["runs"]["r53c_wave39_integrated_stress_big6_schinese"]["r53_telemetry"][
            "integrated_stress"
        ]
        self.assertEqual(st["tier0_standard_low_power_ok"], 1)
        self.assertEqual(st["bt_rmt_suppressed_airplane_on_ok"], 1)
        self.assertEqual(st["passive_tx_bytes_emitted"], 0)
        self.assertEqual(st["ir_remote_state_deterministic_ok"], 1)
        self.assertEqual(st["ir_sircs_bt_rmt_conflict_events"], 0)
        self.assertEqual(st["reset_3way_matrix_ok"], 1)
        self.assertEqual(st["mymenu_persistence_ok"], 1)

    def test_34_round53_r53c_integrated_stress_dlopen_16_h0_eq_h3_and_zero_end_tx(self) -> None:
        st = self.summary["runs"]["r53c_wave39_integrated_stress_big6_schinese"]["r53_telemetry"][
            "integrated_stress"
        ]
        self.assertEqual(st["dlopen_ok"], 1)
        self.assertEqual(st["surfaces_verified"], 16)
        self.assertEqual(st["surfaces_h0_eq_h3"], 16)
        self.assertEqual(st["drift_bits"], 0)
        self.assertEqual(st["e_nd_actuator_tx_count"], 0)
        self.assertEqual(st["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(st["emmc_write_count"], 0)
        self.assertEqual(st["slot1_vault_ro_blocked_rc"], -30)
        self.assertEqual(st["slot1_vault_sha256_match"], 1)
        self.assertEqual(st["p2_write_blocked_rc"], -30)
        self.assertEqual(st["cnflasha_ro_blocked_rc"], -30)
        self.assertEqual(st["r53c_ok"], 1)

    def test_35_round53_r53c_integrated_stress_renders_346686_gpe0_pixels(self) -> None:
        r53c = self.summary["runs"]["r53c_wave39_integrated_stress_big6_schinese"]
        self.assertEqual(r53c["target_presenter"], "31procam_big6_menu_home_presenter")
        self.assertEqual(r53c["target_sid"], "0x0a")
        gpe0 = r53c["gpe0_readback"]
        self.assertTrue(gpe0["present"])
        self.assertEqual(gpe0["bytes"], 2211840)
        self.assertEqual(gpe0["total_pixels"], 552960)
        self.assertEqual(gpe0["nonzero_pixels"], 346686)
        self.assertEqual(gpe0["unique_colors"], 87)

    def test_36_round53_realhw_mechanisms_verified_6_blocks_match_run_telemetry(self) -> None:
        rm = self.summary["realhw_mechanisms_verified"]
        self.assertEqual(len(rm), 6)
        r53a = self.summary["runs"]["r53a_display_quality_bt_rmt_big6_schinese"]["r53_telemetry"]
        r53b = self.summary["runs"]["r53b_mymenu_6ops_camset_persist_guard"]["r53_telemetry"]
        r53c = self.summary["runs"]["r53c_wave39_integrated_stress_big6_schinese"]["r53_telemetry"]
        self.assertEqual(
            rm["display_quality_battery_and_bt_rmt_ctrl_ir_lockout_netreset_init"],
            r53a["dispqual_btrmt_init"],
        )
        self.assertEqual(
            rm["display_quality_stage_b_bridge"],
            r53a["dispqual_btrmt_bridge"],
        )
        self.assertEqual(
            rm["bt_rmt_ctrl_ir_lockout_and_network_reset_stage_b_bridge"],
            r53a["btrmt_ir_netreset_bridge"],
        )
        self.assertEqual(
            rm["mymenu_6ops_camset_persist_stage_b_bridge"],
            r53a["mymenu_persist_bridge"],
        )
        self.assertEqual(
            rm["mymenu_6ops_and_display_from_mymenu_camset01_persist_guard"],
            r53b["mymenu_6ops_persist"],
        )
        self.assertEqual(
            rm["wave39_integrated_stress_tier0_airplane_mymenu_and_16_h0_h3"],
            r53c["integrated_stress"],
        )

    def test_37_round53_exact_3_reset_domain_split_setup_vs_network_vs_mymenu(self) -> None:
        init_a = self.summary["runs"]["r53a_display_quality_bt_rmt_big6_schinese"][
            "r53_telemetry"
        ]["dispqual_btrmt_init"]
        mm_b = self.summary["runs"]["r53b_mymenu_6ops_camset_persist_guard"]["r53_telemetry"][
            "mymenu_6ops_persist"
        ]
        self.assertEqual(init_a["display_quality_survives_camreset_ok"], 1)
        self.assertEqual(init_a["display_quality_survives_netreset_ok"], 1)
        self.assertEqual(init_a["bt_rmt_survives_camreset_ok"], 1)
        self.assertEqual(init_a["bt_rmt_reset_by_netreset_ok"], 1)
        self.assertEqual(mm_b["mymenu_survives_camreset_ok"], 1)
        self.assertEqual(mm_b["mymenu_survives_netreset_ok"], 1)

    def test_38_round53_cross_round_consistency_with_r52_lock_op_parts_setup_survival(self) -> None:
        self.assertEqual(self.r52_summary["round"], 52)
        li52 = self.r52_summary["runs"]["r52a_lock_op_parts_mydial_big6_schinese"][
            "r52_telemetry"
        ]["lock_op_init"]
        init53 = self.summary["runs"]["r53a_display_quality_bt_rmt_big6_schinese"][
            "r53_telemetry"
        ]["dispqual_btrmt_init"]
        self.assertEqual(li52["lock_op_survives_netreset_ok"], 1)
        self.assertEqual(init53["display_quality_survives_netreset_ok"], 1)
        self.assertEqual(init53["bt_rmt_reset_by_netreset_ok"], 1)

    def test_39_round53_cross_round_consistency_with_r50_camset01_slot1_vault_ro(self) -> None:
        self.assertEqual(self.r50_summary["round"], 50)
        mm53 = self.summary["runs"]["r53b_mymenu_6ops_camset_persist_guard"]["r53_telemetry"][
            "mymenu_6ops_persist"
        ]
        self.assertEqual(mm53["camset01_mymenu_roundtrip_ok"], 1)
        self.assertEqual(mm53["slot1_vault_ro_blocked_rc"], -30)
        self.assertEqual(mm53["slot1_vault_writes"], 0)

    def test_40_round53_cross_round_consistency_with_r49_monitor_brightness_manual_0(self) -> None:
        self.assertEqual(self.r49_summary["round"], 49)
        st53 = self.summary["runs"]["r53c_wave39_integrated_stress_big6_schinese"][
            "r53_telemetry"
        ]["integrated_stress"]
        self.assertEqual(st53["tier0_standard_low_power_ok"], 1)

    def test_41_round53_unexecuted_physical_camera_bench_boundaries_documented(self) -> None:
        bounds = self.summary["unexecuted_physical_camera_bench_boundaries"]
        self.assertEqual(len(bounds), 3)
        joined = " ".join(bounds)
        self.assertIn("Display Quality", joined)
        self.assertIn("Bluetooth Rmt Ctrl", joined)
        self.assertIn("My Menu", joined)

    def test_42_round53_alpha_png_exists_under_50kib_and_matches_summary_sha256(self) -> None:
        pe = self.summary["runs"]["r53a_display_quality_bt_rmt_big6_schinese"]["png_exports"]
        self.assertLess(len(self.alpha_png_bytes), 50000)
        self.assertLess(len(self.alpha_png_bytes), 51200)
        self.assertEqual(len(self.alpha_png_bytes), pe["alpha_bytes"])
        self.assertEqual(
            hashlib.sha256(self.alpha_png_bytes).hexdigest(), pe["alpha_sha256"]
        )

    def test_43_round53_composited_png_exists_under_50kib_and_matches_summary_sha256(self) -> None:
        pe = self.summary["runs"]["r53a_display_quality_bt_rmt_big6_schinese"]["png_exports"]
        self.assertLess(len(self.comp_png_bytes), 50000)
        self.assertLess(len(self.comp_png_bytes), 51200)
        self.assertEqual(len(self.comp_png_bytes), pe["composited_bytes"])
        self.assertEqual(
            hashlib.sha256(self.comp_png_bytes).hexdigest(), pe["composited_sha256"]
        )

    def test_44_round53_alpha_png_valid_1024x540_rgba_with_transparent_and_opaque_pixels(self) -> None:
        self.assertEqual(self.alpha_dims, (1024, 540))
        self.assertEqual(self.alpha_transparent, 206274)
        self.assertGreater(self.alpha_opaque, 300000)

    def test_45_round53_composited_png_valid_1024x540_rgba_100pct_opaque(self) -> None:
        self.assertEqual(self.comp_dims, (1024, 540))
        self.assertEqual(self.comp_opaque, 1024 * 540)

    def test_46_round53_report_readme_documents_all_3_runs_and_zero_host_leaks(self) -> None:
        for token in (
            "Round 53",
            "26th Real-HW",
            "78th Live Run",
            "r53a",
            "r53b",
            "r53c",
            "Display Quality",
            "Bluetooth Rmt Ctrl",
            "My Menu Setting",
            "Display From My Menu",
            "346,686",
            "r53a-display-quality-btrmt-big6-schinese-alpha.png",
            "r53a-display-quality-btrmt-big6-schinese-composited.png",
        ):
            self.assertIn(token, self.r53_readme)
        for forbidden in ("/Users/", "/private/tmp/", "/var/folders/", "work/_scratch/"):
            self.assertNotIn(forbidden, self.r53_readme)

    def test_47_round53_closure_readme_section_53_present_and_accurate(self) -> None:
        self.assertIn("## 53. Round 53", self.closure_readme)
        self.assertIn("26th Real-HW Round", self.closure_readme)
        self.assertIn("78th Live Run", self.closure_readme)
        self.assertIn(
            "2026-11-15-round53-realhw-display-quality-bt-rmt-mymenu-qemu",
            self.closure_readme,
        )

    def test_48_round53_26_realhw_qemu_rounds_r28_to_r53_78_runs_and_52_pngs_continuity(self) -> None:
        png_total = 0
        for r in range(28, 54):
            matches = list((REPO_ROOT / "reports").glob(f"2026-??-??-round{r}-*"))
            self.assertEqual(len(matches), 1, f"Expected 1 report dir for Round {r}")
            pngs = list((matches[0] / "assets").glob("*.png"))
            self.assertEqual(len(pngs), 2, f"Expected 2 PNGs for Round {r}")
            for p in pngs:
                self.assertLess(p.stat().st_size, 51200, str(p))
            png_total += len(pngs)
        self.assertEqual(png_total, 52)
        audit = self.summary["r53_realhw_display_quality_bt_rmt_mymenu_audit"]
        self.assertEqual(audit["milestone233_qemu_rounds"], 26)
        self.assertEqual(audit["milestone233_qemu_runs"], 78)

    def test_49_round53_dual_mode_clean_room_toggle_parity_on_summary(self) -> None:
        for clean_flag in ("0", "1"):
            with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": clean_flag}):
                d = json.loads(self.summary_raw)
                self.assertEqual(d["round"], 53)
                self.assertEqual(
                    d["runs"]["r53a_display_quality_bt_rmt_big6_schinese"]["r53_telemetry"][
                        "dispqual_btrmt_init"
                    ]["passive_tx_bytes_emitted"],
                    0,
                )
                self.assertEqual(
                    d["runs"]["r53b_mymenu_6ops_camset_persist_guard"]["r53_telemetry"][
                        "mymenu_6ops_persist"
                    ]["mymenu_6ops_verified"],
                    6,
                )
                self.assertEqual(
                    d["runs"]["r53c_wave39_integrated_stress_big6_schinese"]["r53_telemetry"][
                        "integrated_stress"
                    ]["surfaces_h0_eq_h3"],
                    16,
                )

    def test_50_round53_r53a_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"]["r53a_display_quality_bt_rmt_big6_schinese"][
            "r53_telemetry"
        ]["dispqual_btrmt_init"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_51_round53_r53b_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"]["r53b_mymenu_6ops_camset_persist_guard"]["r53_telemetry"][
            "mymenu_6ops_persist"
        ]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_52_round53_r53c_verify_us_positive_under_2_seconds(self) -> None:
        us = self.summary["runs"]["r53c_wave39_integrated_stress_big6_schinese"][
            "r53_telemetry"
        ]["integrated_stress"]["verify_us"]
        self.assertGreater(us, 0)
        self.assertLess(us, 2_000_000)

    def test_53_round53_r53a_top_colors_transparent_plus_nonzero_equals_total_pixels(self) -> None:
        gpe = self.summary["runs"]["r53a_display_quality_bt_rmt_big6_schinese"]["gpe0_readback"]
        color_map = {row["argb"]: row["pixels"] for row in gpe["top_colors"]}
        self.assertIn("0x00000000", color_map)
        self.assertIn("0xff000000", color_map)
        self.assertEqual(color_map["0x00000000"] + gpe["nonzero_pixels"], gpe["total_pixels"])

    def test_54_round53_r53c_top_colors_transparent_plus_nonzero_equals_total_pixels(self) -> None:
        gpe = self.summary["runs"]["r53c_wave39_integrated_stress_big6_schinese"]["gpe0_readback"]
        color_map = {row["argb"]: row["pixels"] for row in gpe["top_colors"]}
        self.assertIn("0x00000000", color_map)
        self.assertEqual(color_map["0x00000000"] + gpe["nonzero_pixels"], gpe["total_pixels"])

    def test_55_round53_r53a_and_r53c_wall_elapsed_and_duration_budget_sanity(self) -> None:
        r53a = self.summary["runs"]["r53a_display_quality_bt_rmt_big6_schinese"]
        r53c = self.summary["runs"]["r53c_wave39_integrated_stress_big6_schinese"]
        self.assertGreaterEqual(r53a["duration_budget_sec"], 70)
        self.assertLessEqual(r53a["duration_budget_sec"], 120)
        self.assertGreater(r53a["wall_elapsed_sec"], 50.0)
        self.assertLess(r53a["wall_elapsed_sec"], 120.0)
        self.assertGreaterEqual(r53c["duration_budget_sec"], 70)
        self.assertLessEqual(r53c["duration_budget_sec"], 120)
        self.assertGreater(r53c["wall_elapsed_sec"], 50.0)
        self.assertLess(r53c["wall_elapsed_sec"], 120.0)

    def test_56_round53_r53b_fast_early_exit_wall_elapsed_under_20s(self) -> None:
        r53b = self.summary["runs"]["r53b_mymenu_6ops_camset_persist_guard"]
        self.assertEqual(r53b["duration_budget_sec"], 35)
        self.assertGreater(r53b["wall_elapsed_sec"], 1.0)
        self.assertLess(r53b["wall_elapsed_sec"], 20.0)
        self.assertTrue(r53b["gpe0_readback"]["skipped_stock_fx3_mode"])

    def test_57_round53_faithful_invariants_preserved_across_all_3_runs(self) -> None:
        for rk, rv in self.summary["runs"].items():
            fi = rv["faithful_invariants"]
            self.assertEqual(fi["FX6_NATIVE_FAITHFUL"], 1, rk)
            self.assertEqual(fi["subst_color"], 0, rk)
            self.assertEqual(fi["subst_image"], 0, rk)
            self.assertEqual(fi["forced_render"], 0, rk)
            self.assertEqual(fi["skipped_node"], 0, rk)
            self.assertEqual(fi["lock_bypass"], 0, rk)

    def test_58_round53_all_3_runs_stage_b_manifest_count_13(self) -> None:
        for rk, rv in self.summary["runs"].items():
            self.assertEqual(rv["stage_b"]["manifest_count"], 13, rk)
            self.assertEqual(len(rv["stage_b"]["manifest_items"]), 13, rk)

    def test_59_round53_r53c_stage_b_r53_bridges_and_zero_passive_tx_verified(self) -> None:
        r53c_t = self.summary["runs"]["r53c_wave39_integrated_stress_big6_schinese"][
            "r53_telemetry"
        ]
        self.assertEqual(r53c_t["dispqual_btrmt_bridge"]["dispqual_ok"], 1)
        self.assertEqual(r53c_t["btrmt_ir_netreset_bridge"]["bt_rmt_ir_netreset_ok"], 1)
        self.assertEqual(r53c_t["btrmt_ir_netreset_bridge"]["passive_tx_bytes_emitted"], 0)
        self.assertEqual(r53c_t["mymenu_persist_bridge"]["mymenu_persist_ok"], 1)
        self.assertEqual(r53c_t["stage_b_bridge"]["e_nd_actuator_tx_count"], 0)

    def test_60_round53_r53a_and_r53c_prefix_counts_include_fx6_r53(self) -> None:
        r53a_pc = self.summary["runs"]["r53a_display_quality_bt_rmt_big6_schinese"]["prefix_counts"]
        r53b_pc = self.summary["runs"]["r53b_mymenu_6ops_camset_persist_guard"]["prefix_counts"]
        r53c_pc = self.summary["runs"]["r53c_wave39_integrated_stress_big6_schinese"]["prefix_counts"]
        self.assertGreater(r53a_pc["FX6_R53_"], 10)
        self.assertEqual(r53b_pc["FX6_R53_"], 3)
        self.assertGreater(r53c_pc["FX6_R53_"], 10)

    def test_61_round53_r53_meta_invariants_across_all_3_runs(self) -> None:
        for rk, rv in self.summary["runs"].items():
            m = rv["stage_b"]["r53"]
            self.assertTrue(m["display_quality_high_increases_npfz100_battery_consumption"], rk)
            self.assertTrue(m["bt_rmt_ctrl_on_locks_out_ir_sircs_remote"], rk)
            self.assertTrue(m["bt_rmt_ctrl_reset_by_reset_network_settings"], rk)
            self.assertTrue(m["my_menu_survives_reset_network_settings"], rk)
            self.assertEqual(m["passive_tx_bytes_emitted"], 0, rk)
            self.assertEqual(m["e_nd_actuator_tx_count"], 0, rk)
            self.assertEqual(m["raw_firmware_bytes_leaked"], 0, rk)

    def test_62_round53_no_stray_temp_files_in_repo_root(self) -> None:
        for bad_name in ("tmp", "scratch", ".worktrees"):
            self.assertFalse((REPO_ROOT / bad_name).exists(), bad_name)

    def test_63_round53_port_8768_untouched_in_round53_reports(self) -> None:
        self.assertNotIn("8768", self.summary_raw)
        self.assertNotIn("8768", self.r53_readme)

    def test_64_round53_test_suite_contains_at_least_60_unit_tests(self) -> None:
        methods = [m for m in dir(self) if m.startswith("test_")]
        self.assertEqual(len(methods), 64)


if __name__ == "__main__":
    unittest.main()
