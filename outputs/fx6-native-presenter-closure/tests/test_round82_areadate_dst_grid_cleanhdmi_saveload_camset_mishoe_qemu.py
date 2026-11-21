#!/usr/bin/env python3
"""Offline four-mode unit tests for FX6-on-FX3 Round 82 (55/55 Real-HW Rounds R28..R82, 163rd..165th Live Runs -> 165/165 Total, 110/110 PNGs <= 27,467 B — Wave-68)."""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import copy
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
ROUND82_REPORT_DIR = (
    REPO_ROOT
    / "reports"
    / "2026-11-21-round82-areadate-dst-grid-cleanhdmi-saveload-camset-mishoe-qemu"
)
WAVE68_SPEC_PATH = (
    REPO_ROOT
    / "reports"
    / "2026-11-17-global-sony-wave68-area-date-dst-grid-line-cleanhdmi-saveload-camset-mishoe-flashsync-intel"
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


def _strip_volatile_timing(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {
            k: _strip_volatile_timing(v)
            for k, v in obj.items()
            if k not in ("elapsed_seconds", "elapsed_ms", "wall_elapsed_sec", "verify_us")
        }
    if isinstance(obj, list):
        return [_strip_volatile_timing(v) for v in obj]
    return obj


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


def _build_overlay_for_r82(
    runner,
    parent_cpio: pathlib.Path,
    fp,
    fv,
    fb,
    fake_run,
    jit_meta: Dict[str, Any],
    work: pathlib.Path,
    r82_mode: str,
    lang: str = "schinese",
    enable_r82: bool = True,
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
            enable_r81=True,
            r81_mode="pixelmap_monitor_recallhold_hdmi_recctrl_big6",
            enable_r82=enable_r82,
            r82_mode=r82_mode,
            sd_manifest_mode="valid",
            lang=lang,
            shim_bytes=b"SHIM",
        )


class TestRound82AreaDateDstGridCleanHdmiSaveLoadCamsetMiShoeQemu(unittest.TestCase):
    EXPECTED_RUN_KEYS = (
        "r82a_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_big6_schinese",
        "r82b_wave68_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_guard",
        "r82c_clean_unmount_wave68_reset_h0_h3_big6_schinese",
    )

    runner: Any
    runner_src: str
    stage_a_src: str
    shim_src: str
    wave68_spec: str
    summary_raw: str
    summary: Dict[str, Any]
    r82_readme: str
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
    launcher_r82: Optional[bytes]
    shim_r82: Optional[bytes]
    shim_r81: Optional[bytes]
    r81_summary: Dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = _load_closure_module("fx6_brr_r82_cached", "build_and_run_round.py")
        cls.runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")
        cls.stage_a_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        cls.shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        cls.wave68_spec = WAVE68_SPEC_PATH.read_text(encoding="utf-8")
        cls.summary_raw = (ROUND82_REPORT_DIR / "summary.json").read_text(encoding="utf-8")
        cls.summary = json.loads(cls.summary_raw)
        cls.r82_readme = (ROUND82_REPORT_DIR / "README.md").read_text(encoding="utf-8")
        cls.closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")

        alpha_p = ROUND82_REPORT_DIR / "r82_saveload_camset10_mishoe_xlrh1_sync_debunk_slot1_erofs_preview.png"
        comp_p = ROUND82_REPORT_DIR / "r82_areadate30_dst_grid3_cleanhdmi_marker_isolation_preview.png"
        cls.alpha_png_bytes = alpha_p.read_bytes()
        aw, ah, cls.alpha_transparent, cls.alpha_opaque = _decode_png_rgba_rows(cls.alpha_png_bytes)
        cls.alpha_dims = (aw, ah)

        cls.comp_png_bytes = comp_p.read_bytes()
        cw, ch, _, cls.comp_opaque = _decode_png_rgba_rows(cls.comp_png_bytes)
        cls.comp_dims = (cw, ch)

        with tempfile.TemporaryDirectory() as tmp:
            tpath = pathlib.Path(tmp)
            parent_cpio, fp, fv, fb, fake_run, jit_meta = _build_mock_cpio_and_fakes(
                cls.runner, tpath
            )
            cls.ov_a = _build_overlay_for_r82(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wa", "areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_big6", lang="schinese",
            )
            cls.ov_b = _build_overlay_for_r82(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wb", "wave68_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_guard", lang="en",
            )
            cls.ov_c = _build_overlay_for_r82(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wc", "clean_unmount_wave68_reset_h0_h3_big6", lang="schinese",
            )
            cls.ov_off = _build_overlay_for_r82(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "woff", "areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_big6", enable_r82=False,
            )
            cls.invalid_mode_raised = False
            try:
                _build_overlay_for_r82(
                    cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                    tpath / "wbad", "invalid_r82_mode",
                )
            except ValueError:
                cls.invalid_mode_raised = True

            zig_bin = shutil.which("zig") or (
                str(cls.runner.ZIG) if cls.runner.ZIG.is_file() else None
            )
            if zig_bin is not None:
                verify_r82_out = tpath / "fx6-stage-a-verify-r82"
                shim_r82_out = tpath / "libgrm-fbinit9-r82.so"
                shim_r81_out = tpath / "libgrm-fbinit9-r81.so"
                for cmd in (
                    [
                        zig_bin, "cc", "-target", "aarch64-linux-gnu.2.25", "-O0",
                        str(CLOSURE_DIR / "fx6-stage-a-verify.c"),
                        "-ldl", "-lpthread", "-o", str(verify_r82_out),
                    ],
                    [
                        zig_bin, "cc", "-target", "aarch64-linux-gnu.2.25", "-O0",
                        "-shared", "-fPIC", "-DFX6_ROUND=82",
                        str(CLOSURE_DIR / "libgrm-fbinit9.c"),
                        "-ldl", "-lpthread", "-o", str(shim_r82_out),
                    ],
                    [
                        zig_bin, "cc", "-target", "aarch64-linux-gnu.2.25", "-O0",
                        "-shared", "-fPIC", "-DFX6_ROUND=81",
                        str(CLOSURE_DIR / "libgrm-fbinit9.c"),
                        "-ldl", "-lpthread", "-o", str(shim_r81_out),
                    ],
                ):
                    cls.runner.subprocess.run(cmd, check=True, timeout=120)
                cls.launcher_r82 = verify_r82_out.read_bytes()
                cls.shim_r82 = shim_r82_out.read_bytes()
                cls.shim_r81 = shim_r81_out.read_bytes()
            else:
                cls.launcher_r82 = None
                cls.shim_r82 = None
                cls.shim_r81 = None

        cls.r81_summary = json.loads(
            (
                REPO_ROOT
                / "reports"
                / "2026-11-21-round81-pixelmap-monitor-recallhold-hdmi-recctrl-qemu"
                / "summary.json"
            ).read_text(encoding="utf-8")
        )

    def test_01_wave68_global_spec_present_and_covers_all_4_pillars(self) -> None:
        self.assertTrue(WAVE68_SPEC_PATH.is_file())
        for needle in (
            "Area/Date/Time Setting",
            "AREA_GMT_",
            "convert_setting_daylight_saving_to_saylight_saving",
            "Date Format",
            "24 hours",
            "Clock Set",
            "Backup Battery End",
            "Grid Line Display",
            "Grid Line Type",
            "Rule of 3rds Grid",
            "Diag. + Square Grid",
            "Marker Display",
            "Guideframe",
            "Save/Load Settings",
            "libSaveLoadSettings.so",
            "SONY/SETTING/%s/CAMSET/%s.DAT",
            "CAMPR%02d%c.DAT",
            "FTPSET/%s.DAT",
            "Memory/Recall Media",
            "All File",
            "Reference File",
            "SYNCHRO_TERMINAL",
            "Flash Sync Spd. Prty.",
            "External Flash Set.",
            "Video Light Mode",
            "HVL-LBPC",
            "XLR-H1",
            "GENLOCK",
        ):
            self.assertIn(needle, self.wave68_spec)

    def test_02_round82_summary_schema_milestone_and_zero_leaks(self) -> None:
        self.assertNotIn("/Users/", self.summary_raw)
        self.assertNotIn("/private/tmp/", self.summary_raw)
        self.assertNotIn("/tmp/round82", self.summary_raw)
        self.assertEqual(
            self.summary["schema"],
            "fx6-on-fx3-round82-areadate-dst-grid-cleanhdmi-saveload-camset-mishoe-qemu-v1",
        )
        self.assertEqual(self.summary["round"], 82)
        self.assertEqual(self.summary["overall_status"], "PASS")
        self.assertIs(self.summary["synthetic_fallback"], False)
        self.assertIn("55/55 Real-HW Rounds", self.summary["milestone"])
        self.assertIn("165/165 Live Runs", self.summary["milestone"])
        self.assertIn("110/110 PNGs <= 27,467 B", self.summary["milestone"])
        self.assertEqual(self.summary["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(self.summary["usb_tx"], 0)
        self.assertEqual(self.summary["usb_tx_bytes"], 0)
        self.assertEqual(self.summary["emmc_writes"], 0)
        self.assertEqual(self.summary["slot1_writes"], 0)
        self.assertEqual(self.summary["slot1_data_sector_writes"], 0)
        self.assertEqual(tuple(self.summary["runs"].keys()), self.EXPECTED_RUN_KEYS)

    def test_03_round82_hardware_safety_locks_all_false_and_zero(self) -> None:
        locks = self.summary["hardware_safety_locks"]
        self.assertIs(locks["hardware_live_attachment_authorized"], False)
        self.assertIs(locks["persistent_emmc_writes_authorized"], False)
        self.assertIs(locks["cross_model_flash_authorized"], False)
        self.assertIs(locks["spi_nor_write_authorized"], False)
        self.assertIs(locks["el3_payload_transmit_authorized"], False)
        self.assertEqual(locks["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(locks["usb_tx"], 0)
        self.assertEqual(locks["usb_tx_bytes"], 0)
        self.assertEqual(locks["emmc_writes"], 0)
        self.assertEqual(locks["slot1_writes"], 0)
        self.assertEqual(locks["slot1_data_sector_writes"], 0)

    def test_04_round82_cli_accepts_round82_and_all_3_r82_modes(self) -> None:
        self.assertIn(", 78, 79, 80, 81, 82]", self.runner_src)
        for mode in (
            "areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_big6",
            "wave68_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_guard",
            "clean_unmount_wave68_reset_h0_h3_big6",
        ):
            self.assertIn(mode, self.runner_src)

    def test_05_round82_overlay_rejects_invalid_r82_mode(self) -> None:
        self.assertTrue(self.invalid_mode_raised)

    def test_06_round82_overlay_r82a_injects_etc_fx6_stage_r82_and_appfw_launch(self) -> None:
        replacements, additions, meta = self.ov_a
        self.assertTrue(meta["r82_enabled"])
        self.assertIn("etc/fx6_stage_r82", additions)
        self.assertIn("etc/fx6_r82_libjit.so", additions)
        r82_cfg = additions["etc/fx6_stage_r82"][0].decode("utf-8")
        self.assertIn("stage_r82=1", r82_cfg)
        self.assertIn("r82_mode=areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_big6", r82_cfg)
        self.assertIn("milestone_55th_realhw_165th_live_110_pngs=1", r82_cfg)
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("/usr/bin/appfw-launch", init_txt)
        self.assertNotIn("--r82-wave68-guard", init_txt)

    def test_07_round82_overlay_r82b_injects_early_guard_probe_and_poweroff(self) -> None:
        replacements, _, meta = self.ov_b
        self.assertEqual(
            meta["r82"]["r82_mode"],
            "wave68_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_guard",
        )
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("--r82-wave68-guard", init_txt)
        self.assertIn("FX6_R82_WAVE68_GUARD_RC=", init_txt)
        self.assertIn("FX6_R82_WAVE68_GUARD_EXIT", init_txt)
        self.assertIn("poweroff -f", init_txt)

    def test_08_round82_overlay_r82c_integrated_runs_stage_b_big6(self) -> None:
        replacements, additions, meta = self.ov_c
        self.assertEqual(meta["r82"]["r82_mode"], "clean_unmount_wave68_reset_h0_h3_big6")
        r82_cfg = additions["etc/fx6_stage_r82"][0].decode("utf-8")
        self.assertIn("r82_mode=clean_unmount_wave68_reset_h0_h3_big6", r82_cfg)
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("/usr/bin/appfw-launch", init_txt)
        self.assertNotIn("--r82-wave68-guard", init_txt)

    def test_09_round82_overlay_disabled_when_enable_r82_false(self) -> None:
        _, additions, meta = self.ov_off
        self.assertFalse(meta["r82_enabled"])
        self.assertNotIn("etc/fx6_stage_r82", additions)
        self.assertNotIn("etc/fx6_r82_libjit.so", additions)
        self.assertNotIn("r82", meta)

    def test_10_round82_stage_a_c_source_contains_all_wave68_probes(self) -> None:
        for sym in (
            "setup_r82_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_probe",
            "run_r82_wave68_guard_probe",
            "run_r82_clean_unmount_wave68_h0_h3_probe",
            "r82_wave68_initialize",
            "r82_wave68_zero_init",
            "r82_wave68_camera_settings_reset",
            "r82_wave68_reset_network_settings",
            "r82_eval_areadate_dst_rtc_and_clockset",
            "r82_eval_grid_line_and_marker_cleanhdmi",
            "r82_eval_saveload_camset_memory_and_allfile",
            "r82_eval_sync_debunk_mishoe_xlrh1_and_genlock",
            "FX6_R82_WAVE68_INIT",
            "FX6_R82_WAVE68_GUARD",
            "FX6_R82_CLEAN_UNMOUNT_WAVE68_H0_H3",
            "--r82-wave68-guard",
            "--r82-clean-unmount-wave68-h0-h3",
            "/etc/fx6_stage_r82",
        ):
            self.assertIn(sym, self.stage_a_src)

    def test_11_round82_shim_c_source_contains_r82_guarded_bridges(self) -> None:
        self.assertIn("#if FX6_ROUND >= 82", self.shim_src)
        for sym in (
            "FX6_R82_AREADATE30_DST_CLOCKSET_BRIDGE",
            "FX6_R82_GRID3_CLEANHDMI_MARKER_BRIDGE",
            "FX6_R82_SAVELOAD_CAMSET10_EROFS_BRIDGE",
            "FX6_R82_SYNC_DEBUNK_MISHOE_XLRH1_BRIDGE",
            "FX6_R82_LANG_TELEMETRY",
            "FX6_STAGE_B_R82_BRIDGE",
        ):
            self.assertIn(sym, self.shim_src)

    def test_12_round82_compile_launcher_and_shim_aarch64_elf_symbols(self) -> None:
        if self.launcher_r82 is None or self.shim_r82 is None:
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertEqual(self.launcher_r82[:4], b"\x7fELF")
        self.assertEqual(self.shim_r82[:4], b"\x7fELF")
        self.assertEqual(struct.unpack_from("<H", self.shim_r82, 18)[0], 183)
        self.assertIn(b"FX6_R82_AREADATE30_DST_CLOCKSET_BRIDGE", self.shim_r82)
        self.assertIn(b"FX6_R82_GRID3_CLEANHDMI_MARKER_BRIDGE", self.shim_r82)
        self.assertIn(b"FX6_R82_SAVELOAD_CAMSET10_EROFS_BRIDGE", self.shim_r82)
        self.assertIn(b"FX6_R82_SYNC_DEBUNK_MISHOE_XLRH1_BRIDGE", self.shim_r82)

    def test_13_round82_shim_round81_backward_compat_excludes_r82_bridges(self) -> None:
        if self.shim_r81 is None:
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertIn(b"FX6_R81_PIXELMAP_APR_BRIDGE", self.shim_r81)
        self.assertNotIn(b"FX6_R82_AREADATE30_DST_CLOCKSET_BRIDGE", self.shim_r81)

    def test_14_round82_parse_log_extracts_all_r82_prefixes_and_rc(self) -> None:
        serial_text = "\n".join(
            [
                "Linux version 4.9.337-scel+ (sony@fx3)",
                "FX6_R82_WAVE68_INIT fx3_wave68_nodes_ok=1 uxc_tokens_ok=1 areadate30_dst_clockset_ok=1 grid3_cleanhdmi_marker_ok=1 saveload_camset10_erofs_ok=1 sync_debunk_mishoe_xlrh1_ok=1 usb_tx=0 slot1_writes=0 emmc_write_count=0 r82_init_ok=1",
                "FX6_R82_AREADATE30_DST_CLOCKSET_BRIDGE areadate_30zones_dst_anti_reset_ok=1 rtc_24h_zero_cr2032_init_wizard_ok=1 fx6_clockset_utc_zero_dst_ok=1 areadate30_dst_clockset_ok=1 r82_bridge_ok=1",
                "FX6_R82_GRID3_CLEANHDMI_MARKER_BRIDGE grid3_unified_hdmi_cleanfeed_ok=1 marker5_anti_reset_zero_hdmi_ok=1 fx6_marker_zero_grid3_ui_ok=1 grid3_cleanhdmi_marker_ok=1",
                "FX6_R82_SAVELOAD_CAMSET10_EROFS_BRIDGE camset10_slot1_only_exclusions_ok=1 cam_set_memory_body3_card_m4_ok=1 slot1_saveload_camset_erofs30_ok=1 fx6_allfile64_zero_reffile_ok=1 saveload_camset10_erofs_ok=1",
                "FX6_R82_SYNC_DEBUNK_MISHOE_XLRH1_BRIDGE sync_terminal_debunk_flash250_ok=1 mishoe_vlight4_xlrh1_mutex_pmic900_ok=1 fx6_vlight3_tcbnc_zero_genlock_ok=1 sync_debunk_mishoe_xlrh1_ok=1 usb_tx=0 slot1_writes=0",
                "FX6_R82_LANG_TELEMETRY lang=schinese font_bank=23 str_bank=19 milestone_55th_realhw_165th_live_110_pngs=1 usb_tx=0 slot1_writes=0 r82_bridge_ok=1",
                "FX6_STAGE_B_R82_BRIDGE round=82 faithful=1 nop_count=0 milestone_55th_realhw_165th_live_110_pngs=1 usb_tx=0 slot1_writes=0 emmc_write_count=0",
                "FX6_R82_WAVE68_GUARD fx3_cr2032_rc=-95 fx6_dst_ui_rc=-95 fx3_marker_hdmi_rc=-95 camset_slot1_save_rc=-30 fx3_sync_term_rc=-95 fx6_genlock_bnc_rc=-95 live_attach_eperm_rc=-1 r82b_ok=1",
                "FX6_R82_WAVE68_GUARD_RC=0",
                "FX6_R82_CLEAN_UNMOUNT_WAVE68_H0_H3 stock_unmount_restored_ok=1 surfaces_h0_eq_h3=16 usb_tx=0 slot1_writes=0 r82c_ok=1",
            ]
        ) + "\n"
        parsed = self.runner.extract_milestones(serial_text)
        r82_t = parsed["r82_telemetry"]
        self.assertEqual(r82_t["wave68_guard_rc"], 0)
        self.assertEqual(r82_t["wave68_init"]["areadate30_dst_clockset_ok"], 1)
        self.assertEqual(r82_t["areadate30_dst_clockset_bridge"]["areadate30_dst_clockset_ok"], 1)
        self.assertEqual(r82_t["grid3_cleanhdmi_marker_bridge"]["grid3_cleanhdmi_marker_ok"], 1)
        self.assertEqual(r82_t["saveload_camset10_erofs_bridge"]["saveload_camset10_erofs_ok"], 1)
        self.assertEqual(r82_t["sync_debunk_mishoe_xlrh1_bridge"]["sync_debunk_mishoe_xlrh1_ok"], 1)
        self.assertEqual(r82_t["lang_telemetry"]["milestone_55th_realhw_165th_live_110_pngs"], 1)
        self.assertEqual(r82_t["stage_b_bridge"]["round"], 82)
        self.assertEqual(r82_t["wave68_guard"]["r82b_ok"], 1)
        self.assertEqual(r82_t["clean_unmount_wave68_h0_h3"]["surfaces_h0_eq_h3"], 16)
        self.assertEqual(parsed["prefix_counts"]["FX6_R82_"], 9)

    def test_15_round82_parse_log_defaults_when_no_r82_lines_present(self) -> None:
        parsed = self.runner.extract_milestones("Linux version 4.9.337-scel+\n")
        self.assertIsNone(parsed["r82_telemetry"])
        self.assertEqual(parsed["prefix_counts"].get("FX6_R82_", 0), 0)

    def test_16_round82_runner_preserves_r81_prefix_and_uses_r82_stage_label(self) -> None:
        self.assertIn('if args.round >= 81:\n        tmp_prefix = "fx6-r81"', self.runner_src)
        self.assertIn('if args.round >= 82:\n        tmp_prefix = "fx6-r82"', self.runner_src)
        self.assertIn(
            "55RealHw165thLiveWave68AreaDateDstGridCleanHdmiSaveLoadCamsetMiShoeErofs30",
            self.runner_src,
        )

    def test_17_round82_runner_portability_and_sanitizer_helper(self) -> None:
        self.assertIn('shutil.which("zig")', self.runner_src)
        self.assertIn("FX6_SCRATCH_DIR", self.runner_src)
        self.assertIn("def sanitize_round82_summary(", self.runner_src)
        self.assertNotIn("/usr/" + "bin/python3", self.runner_src)

    def test_18_round82_summary_json_zero_host_path_scratch_and_elapsed_leaks(self) -> None:
        for forbidden in (
            "/Users/",
            "/private/tmp/",
            "/var/folders/",
            "/tmp/round82",
            "work/_scratch/",
            "work/_tests/",
            "elapsed_seconds",
            "elapsed_ms",
            ":87" + "68",
        ):
            self.assertNotIn(forbidden, self.summary_raw)

    def test_19_round82_summary_audit_block_confirms_55_rounds_165_runs_110_pngs(self) -> None:
        audit = self.summary["r82_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_audit"]
        self.assertEqual(audit["round"], 82)
        self.assertGreaterEqual(audit["realhw_rounds_count"], 55)
        self.assertGreaterEqual(audit["total_live_runs"], 165)
        self.assertGreaterEqual(audit["total_png_receipts"], 110)
        self.assertGreaterEqual(audit["milestone324_qemu_rounds"], 55)
        self.assertGreaterEqual(audit["milestone324_qemu_runs"], 165)
        self.assertGreaterEqual(audit["milestone324_png_receipts"], 110)
        self.assertGreaterEqual(audit["milestone364_qemu_rounds"], 55)
        self.assertGreaterEqual(audit["milestone364_qemu_runs"], 165)
        self.assertGreaterEqual(audit["milestone364_png_receipts"], 110)
        self.assertGreaterEqual(audit["milestone375_qemu_rounds"], 55)
        self.assertGreaterEqual(audit["milestone375_qemu_runs"], 165)
        self.assertGreaterEqual(audit["milestone375_png_receipts"], 110)
        self.assertEqual(audit["total_runs"], 3)
        negative_keys = {
            "fx3_user_cr2032_slot_present",
            "fx6_dst_ui_toggle_exposed",
            "fx3_marker_hdmi_output_supported",
            "fx6_grid_3pattern_ui_exposed",
            "fx3_camset_pro_camera_path_present",
            "fx3_saveload_slot2_supported",
            "fx6_reference_file_exposed",
            "fx3_physical_sync_terminal_present",
            "fx3_flash_sync_spd_prty_exposed",
            "fx3_xlrh1_passive_shoe_mishoe_supported",
            "fx6_video_light_auto_mode_exposed",
            "fx6_physical_genlock_bnc_present",
        }
        for nk in negative_keys:
            self.assertIs(audit[nk], False, nk)
        for k, v in audit.items():
            if isinstance(v, bool) and k not in negative_keys:
                self.assertTrue(v, f"Expected audit boolean {k} to be True")

    def test_20_round82_all_3_runs_present_with_kernel_4_9_337_and_zero_crashes_writes(self) -> None:
        runs = self.summary["runs"]
        self.assertEqual(list(runs.keys()), list(self.EXPECTED_RUN_KEYS))
        for rk, rv in runs.items():
            self.assertEqual(rv["round"], 82, rk)
            self.assertIn("4.9.337-scel+", rv["kernel_version"], rk)
            self.assertEqual(rv["nop_count"], 0, rk)
            self.assertEqual(rv["crashes"], 0, rk)
            self.assertEqual(rv["emmc_write_count"], 0, rk)
            self.assertGreater(rv["wall_elapsed_sec"], 0.0, rk)

    def test_21_round82_r82a_pillar_a_areadate30_dst_rtc24h_and_fx6_clockset(self) -> None:
        init_t = self.summary["runs"][
            "r82a_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_big6_schinese"
        ]["r82_telemetry"]["wave68_init"]
        self.assertEqual(init_t["fx3_wave68_nodes_ok"], 1)
        self.assertEqual(init_t["uxc_tokens_ok"], 1)
        self.assertEqual(init_t["areadate30_dst_clockset_ok"], 1)
        self.assertEqual(init_t["fx3_zone_oob_rc"], -22)
        self.assertEqual(init_t["fx3_cr2032_rc"], -95)
        self.assertEqual(init_t["fx3_rtc_under24h_rc"], -11)
        self.assertEqual(init_t["fx6_dst_dormant_rc"], -95)
        self.assertEqual(init_t["fx6_rtc_end_rc"], -16)
        self.assertEqual(init_t["dormant_fx3_cr2032_events"], 0)
        self.assertEqual(init_t["dormant_fx6_dst_ui_events"], 0)

    def test_22_round82_r82a_pillar_b_grid3_cleanhdmi_and_marker_zero_hdmi_isolation(self) -> None:
        init_t = self.summary["runs"][
            "r82a_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_big6_schinese"
        ]["r82_telemetry"]["wave68_init"]
        self.assertEqual(init_t["grid3_cleanhdmi_marker_ok"], 1)
        self.assertEqual(init_t["marker_still_rc"], -95)
        self.assertEqual(init_t["marker_hdmi_rc"], -95)
        self.assertEqual(init_t["fx6_grid3_dormant_rc"], -95)
        self.assertEqual(init_t["marker_hdmi_pixels_injected"], 0)
        self.assertEqual(init_t["dormant_fx6_grid3_ui_events"], 0)

    def test_23_round82_r82a_pillar_c_saveload_camset10_slot1_only_erofs30_and_allfile(self) -> None:
        init_t = self.summary["runs"][
            "r82a_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_big6_schinese"
        ]["r82_telemetry"]["wave68_init"]
        self.assertEqual(init_t["saveload_camset10_erofs_ok"], 1)
        self.assertEqual(init_t["camset_slot1_save_erofs_rc"], -30)
        self.assertEqual(init_t["camset_slot1_del_erofs_rc"], -30)
        self.assertEqual(init_t["camset_slot2_blocked_rc"], -95)
        self.assertEqual(init_t["camset_pro_camera_rc"], -95)
        self.assertEqual(init_t["camset_over10_rc"], -28)
        self.assertEqual(init_t["camset_excl_rc"], -95)
        self.assertEqual(init_t["camset_fw_v1_rc"], -22)
        self.assertEqual(init_t["campr_slot1_erofs_rc"], -30)
        self.assertEqual(init_t["fx6_ref_file_dormant_rc"], -95)
        self.assertEqual(init_t["camset_excluded_leaked_count"], 0)
        self.assertEqual(init_t["dormant_fx3_pro_camera_events"], 0)
        self.assertEqual(init_t["dormant_fx6_ref_file_events"], 0)

    def test_24_round82_r82a_pillar_d_sync_debunk_mishoe_xlrh1_genlock_and_vfs_erofs30(self) -> None:
        init_t = self.summary["runs"][
            "r82a_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_big6_schinese"
        ]["r82_telemetry"]["wave68_init"]
        self.assertEqual(init_t["sync_debunk_mishoe_xlrh1_ok"], 1)
        self.assertEqual(init_t["fx3_sync_debunk_rc"], -95)
        self.assertEqual(init_t["fx3_xlrh1_mutex_rc"], -16)
        self.assertEqual(init_t["fx3_pmic_over900_rc"], -16)
        self.assertEqual(init_t["fx3_hv_flash_rc"], -1)
        self.assertEqual(init_t["fx6_vlight_auto_rc"], -95)
        self.assertEqual(init_t["fx6_genlock_dormant_rc"], -95)
        self.assertEqual(init_t["slot1_vfs_camset_erofs_rc"], -30)
        self.assertEqual(init_t["slot1_vfs_camset_unlink_erofs_rc"], -30)
        self.assertEqual(init_t["slot1_vfs_campr_erofs_rc"], -30)
        self.assertEqual(init_t["p2_write_blocked_rc"], -30)
        self.assertEqual(init_t["p2_sha256_match"], 1)
        self.assertEqual(init_t["p12_sha256_match"], 1)
        self.assertEqual(init_t["cnflasha_sha256_match"], 1)
        self.assertEqual(init_t["slot1_vault_sha256_match"], 1)
        self.assertEqual(init_t["usb_tx"], 0)
        self.assertEqual(init_t["slot1_writes"], 0)
        self.assertEqual(init_t["slot1_data_sector_writes"], 0)
        self.assertEqual(init_t["slot1_avf_info_mutated"], 0)
        self.assertEqual(init_t["emmc_write_count"], 0)
        self.assertEqual(init_t["r82_init_ok"], 1)

    def test_25_round82_r82a_stage_b_schinese_lang_telemetry_and_bridge(self) -> None:
        r82a_t = self.summary["runs"][
            "r82a_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_big6_schinese"
        ]["r82_telemetry"]
        lt = r82a_t["lang_telemetry"]
        self.assertEqual(lt["lang"], "schinese")
        self.assertEqual(lt["bk4_lang_id"], "0x02cf019c")
        self.assertEqual(lt["bk4_lang_val"], "0x19")
        self.assertEqual(lt["lang_enum"], "0x2b45_CHINESE_SIMPLIFIED")
        self.assertEqual(lt["font_bank"], 23)
        self.assertEqual(lt["str_bank"], 19)
        self.assertEqual(lt["gpe_fb"], 0)
        self.assertEqual(lt["milestone_55th_realhw_165th_live_110_pngs"], 1)
        self.assertEqual(lt["usb_tx"], 0)
        self.assertEqual(lt["slot1_writes"], 0)
        self.assertEqual(lt["raw_firmware_bytes_leaked"], 0)

        sb = r82a_t["stage_b_bridge"]
        self.assertEqual(sb["round"], 82)
        self.assertEqual(sb["faithful"], 1)
        self.assertEqual(sb["nop_count"], 0)
        self.assertEqual(sb["areadate30_dst_rtc24h_clockset_ok"], 1)
        self.assertEqual(sb["grid3_cleanhdmi_marker5_zero_hdmi_ok"], 1)
        self.assertEqual(sb["saveload_camset10_slot1_only_erofs30_allfile64_ok"], 1)
        self.assertEqual(sb["sync_debunk_mishoe_vlight4_xlrh1_mutex_zero_genlock_ok"], 1)
        self.assertEqual(sb["milestone_55th_realhw_165th_live_110_pngs"], 1)

    def test_26_round82_r82a_stage_b_4_pillar_bridges_verified(self) -> None:
        r82a_t = self.summary["runs"][
            "r82a_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_big6_schinese"
        ]["r82_telemetry"]
        pb1 = r82a_t["areadate30_dst_clockset_bridge"]
        self.assertEqual(pb1["areadate_30zones_dst_anti_reset_ok"], 1)
        self.assertEqual(pb1["rtc_24h_zero_cr2032_init_wizard_ok"], 1)
        self.assertEqual(pb1["fx6_clockset_utc_zero_dst_ok"], 1)
        self.assertEqual(pb1["areadate30_dst_clockset_ok"], 1)
        self.assertEqual(pb1["dormant_fx3_cr2032_events"], 0)
        self.assertEqual(pb1["dormant_fx6_dst_ui_events"], 0)
        self.assertEqual(pb1["r82_bridge_ok"], 1)

        pb2 = r82a_t["grid3_cleanhdmi_marker_bridge"]
        self.assertEqual(pb2["grid3_unified_hdmi_cleanfeed_ok"], 1)
        self.assertEqual(pb2["marker5_anti_reset_zero_hdmi_ok"], 1)
        self.assertEqual(pb2["fx6_marker_zero_grid3_ui_ok"], 1)
        self.assertEqual(pb2["grid3_cleanhdmi_marker_ok"], 1)
        self.assertEqual(pb2["marker_hdmi_pixels_injected"], 0)
        self.assertEqual(pb2["dormant_fx6_grid3_ui_events"], 0)

        pb3 = r82a_t["saveload_camset10_erofs_bridge"]
        self.assertEqual(pb3["camset10_slot1_only_exclusions_ok"], 1)
        self.assertEqual(pb3["cam_set_memory_body3_card_m4_ok"], 1)
        self.assertEqual(pb3["slot1_saveload_camset_erofs30_ok"], 1)
        self.assertEqual(pb3["fx6_allfile64_zero_reffile_ok"], 1)
        self.assertEqual(pb3["saveload_camset10_erofs_ok"], 1)
        self.assertEqual(pb3["camset_excluded_leaked_count"], 0)
        self.assertEqual(pb3["dormant_fx3_pro_camera_events"], 0)
        self.assertEqual(pb3["dormant_fx6_ref_file_events"], 0)

        pb4 = r82a_t["sync_debunk_mishoe_xlrh1_bridge"]
        self.assertEqual(pb4["sync_terminal_debunk_flash250_ok"], 1)
        self.assertEqual(pb4["mishoe_vlight4_xlrh1_mutex_pmic900_ok"], 1)
        self.assertEqual(pb4["fx6_vlight3_tcbnc_zero_genlock_ok"], 1)
        self.assertEqual(pb4["sync_debunk_mishoe_xlrh1_ok"], 1)
        self.assertEqual(pb4["dormant_fx3_sync_terminal_events"], 0)
        self.assertEqual(pb4["dormant_fx6_genlock_events"], 0)
        self.assertEqual(pb4["xlrh1_mishoe_mutex_violations"], 0)
        self.assertEqual(pb4["usb_tx"], 0)
        self.assertEqual(pb4["slot1_writes"], 0)
        self.assertEqual(pb4["slot1_data_sector_writes"], 0)
        self.assertEqual(pb4["slot1_avf_info_mutated"], 0)

    def test_27_round82_r82a_realhw_mechanisms_verified_block_populated(self) -> None:
        rmv = self.summary["realhw_mechanisms_verified"]
        for key in (
            "wave68_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_init",
            "areadate30_dst_clockset_stage_b_bridge",
            "grid3_cleanhdmi_marker_stage_b_bridge",
            "saveload_camset10_erofs_stage_b_bridge",
            "sync_debunk_mishoe_xlrh1_stage_b_bridge",
            "wave68_fail_closed_guard",
            "clean_unmount_wave68_reset_and_16_h0_h3",
        ):
            self.assertIn(key, rmv)
            self.assertTrue(bool(rmv[key]), key)

    def test_28_round82_r82b_guard_blocks_pillar_a_areadate30_cr2032_rtc24h_fx6_dst(self) -> None:
        g = self.summary["runs"][
            "r82b_wave68_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_guard"
        ]["r82_telemetry"]["wave68_guard"]
        self.assertEqual(g["fx3_zone_neg_rc"], -22)
        self.assertEqual(g["fx3_zone_30_rc"], -22)
        self.assertEqual(g["fx3_datefmt_oob_rc"], -22)
        self.assertEqual(g["fx3_cr2032_rc"], -95)
        self.assertEqual(g["fx3_rtc_23h_rc"], -11)
        self.assertEqual(g["fx3_rtc_depleted_rc"], -11)
        self.assertEqual(g["fx3_unset_ts_op_rc"], -11)
        self.assertEqual(g["fx6_tz_oob_rc"], -22)
        self.assertEqual(g["fx6_dst_ui_rc"], -95)
        self.assertEqual(g["fx6_cr2032_rc"], -95)
        self.assertEqual(g["fx6_rtc_end_rc"], -16)

    def test_29_round82_r82b_guard_blocks_pillar_b_grid_cleanhdmi_and_marker_isolation(self) -> None:
        g = self.summary["runs"][
            "r82b_wave68_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_guard"
        ]["r82_telemetry"]["wave68_guard"]
        self.assertEqual(g["fx3_grid_golden_rc"], -95)
        self.assertEqual(g["fx3_grid_clean_hdmionly_rc"], -16)
        self.assertEqual(g["fx3_grid_clean_raw_rc"], -16)
        self.assertEqual(g["fx3_marker_still_rc"], -95)
        self.assertEqual(g["fx3_marker_hdmi_rc"], -95)
        self.assertEqual(g["fx3_marker_focusmag_rc"], -16)
        self.assertEqual(g["fx3_aspect_oob_rc"], -22)
        self.assertEqual(g["fx3_safety_oob_rc"], -22)
        self.assertEqual(g["fx6_grid3_ui_rc"], -95)
        self.assertEqual(g["fx6_center_oob_rc"], -22)

    def test_30_round82_r82b_guard_blocks_pillar_c_saveload_camset10_exclusions_and_erofs30(self) -> None:
        g = self.summary["runs"][
            "r82b_wave68_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_guard"
        ]["r82_telemetry"]["wave68_guard"]
        self.assertEqual(g["camset_pro_camera_rc"], -95)
        self.assertEqual(g["camset_slot2_rc"], -95)
        self.assertEqual(g["camset_over10_rc"], -28)
        self.assertEqual(g["camset_mr_busy_rc"], -16)
        self.assertEqual(g["camset_xmodel_rc"], -22)
        self.assertEqual(g["camset_v101_rc"], -22)
        self.assertEqual(g["camset_excl_iptc_rc"], -95)
        self.assertEqual(g["camset_excl_net_rc"], -95)
        self.assertEqual(g["camset_excl_areadate_rc"], -95)
        self.assertEqual(g["camset_slot1_save_rc"], -30)
        self.assertEqual(g["camset_slot1_del_rc"], -30)
        self.assertEqual(g["campr_slot1_erofs_rc"], -30)
        self.assertEqual(g["ftpset_slot1_erofs_rc"], -30)
        self.assertEqual(g["mem_customkey_rc"], -95)
        self.assertEqual(g["fx6_ref_file_rc"], -95)
        self.assertEqual(g["fx6_allfile_over64_rc"], -28)
        self.assertEqual(g["fx6_allfile_slot1_erofs_rc"], -30)

    def test_31_round82_r82b_guard_blocks_pillar_d_sync_debunk_xlrh1_mutex_pmic_and_genlock(self) -> None:
        g = self.summary["runs"][
            "r82b_wave68_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_guard"
        ]["r82_telemetry"]["wave68_guard"]
        self.assertEqual(g["fx3_sync_term_rc"], -95)
        self.assertEqual(g["fx3_genlock_rc"], -95)
        self.assertEqual(g["fx3_tc_bnc_rc"], -95)
        self.assertEqual(g["fx3_flash_movie_rc"], -95)
        self.assertEqual(g["fx3_flash_eshut_rc"], -16)
        self.assertEqual(g["fx3_flash_over250_rc"], -16)
        self.assertEqual(g["fx3_flash_hv250v_rc"], -1)
        self.assertEqual(g["fx3_flash_revpol_rc"], -1)
        self.assertEqual(g["fx3_xlrh1_mutex_rc"], -16)
        self.assertEqual(g["fx3_pmic_901ma_rc"], -16)
        self.assertEqual(g["fx6_vlight_auto_rc"], -95)
        self.assertEqual(g["fx6_still_flash_rc"], -95)
        self.assertEqual(g["fx6_genlock_bnc_rc"], -95)

    def test_32_round82_r82b_guard_blocks_vfs_camset_campr_ftpset_p12_p2_cnflasha(self) -> None:
        r82b_t = self.summary["runs"][
            "r82b_wave68_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_guard"
        ]["r82_telemetry"]
        g = r82b_t["wave68_guard"]
        self.assertEqual(r82b_t["wave68_guard_rc"], 0)
        self.assertEqual(g["null_cfg_einval_rc"], -22)
        self.assertEqual(g["live_attach_eperm_rc"], -1)
        self.assertEqual(g["slot1_camset_vfs_erofs_rc"], -30)
        self.assertEqual(g["slot1_camset_del_vfs_erofs_rc"], -30)
        self.assertEqual(g["slot1_campr_vfs_erofs_rc"], -30)
        self.assertEqual(g["slot1_ftpset_vfs_erofs_rc"], -30)
        self.assertEqual(g["p12_write_blocked_rc"], -30)
        self.assertEqual(g["p2_write_blocked_rc"], -30)
        self.assertEqual(g["cnflasha_ro_blocked_rc"], -30)
        self.assertEqual(g["slot1_vault_sha256_match"], 1)
        self.assertEqual(g["usb_tx"], 0)
        self.assertEqual(g["slot1_writes"], 0)
        self.assertEqual(g["slot1_data_sector_writes"], 0)
        self.assertEqual(g["slot1_avf_info_mutated"], 0)
        self.assertEqual(g["rf_tx_packets"], 0)
        self.assertEqual(g["appfw_ok"], 1)
        self.assertEqual(g["shim_elf_ok"], 1)
        self.assertEqual(g["cnflasha_writes"], 0)
        self.assertEqual(g["emmc_write_count"], 0)
        self.assertEqual(g["r82b_ok"], 1)

    def test_33_round82_r82c_clean_unmount_wave68_3tier_reset_and_16_h0_h3(self) -> None:
        ci = self.summary["runs"][
            "r82c_clean_unmount_wave68_reset_h0_h3_big6_schinese"
        ]["r82_telemetry"]["clean_unmount_wave68_h0_h3"]
        self.assertEqual(ci["stock_unmount_restored_ok"], 1)
        self.assertEqual(
            ci["camreset_resets_flash_preserves_areadate_grid_marker5_mem_vlight_airplane_ok"],
            1,
        )
        self.assertEqual(
            ci["nwreset_clears_netcreds_preserves_wave68_setup_grid_marker5_mem_airplane_ok"],
            1,
        )
        self.assertEqual(
            ci["initialize_restores_wave68_defaults_rearms_wizard_preserves_rtc_slot2_airplane_ok"],
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
        self.assertEqual(ci["usb_tx"], 0)
        self.assertEqual(ci["slot1_writes"], 0)
        self.assertEqual(ci["slot1_data_sector_writes"], 0)
        self.assertEqual(ci["slot1_avf_info_mutated"], 0)
        self.assertEqual(ci["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(ci["emmc_write_count"], 0)
        self.assertEqual(ci["r82c_ok"], 1)

    def test_34_round82_r82a_and_r82c_gpe0_readback_big6_home_ge_300k_nonzero_pixels(self) -> None:
        for rk in (
            "r82a_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_big6_schinese",
            "r82c_clean_unmount_wave68_reset_h0_h3_big6_schinese",
        ):
            gpe = self.summary["runs"][rk]["gpe0_readback"]
            self.assertTrue(gpe["present"], rk)
            self.assertEqual(gpe["total_pixels"], 1024 * 540, rk)
            self.assertEqual(gpe["bytes"], 1024 * 540 * 4, rk)
            self.assertGreaterEqual(gpe["nonzero_pixels"], 300000, rk)
            self.assertGreaterEqual(gpe["unique_colors"], 50, rk)

    def test_35_round82_r82a_alpha_and_composited_png_dimensions_and_size_cap_27467(self) -> None:
        self.assertEqual(self.alpha_dims, (1024, 540))
        self.assertEqual(self.comp_dims, (1024, 540))
        self.assertLessEqual(len(self.alpha_png_bytes), 27467)
        self.assertLessEqual(len(self.comp_png_bytes), 27467)
        self.assertGreater(len(self.alpha_png_bytes), 10000)
        self.assertGreater(len(self.comp_png_bytes), 10000)
        self.assertGreater(self.alpha_transparent, 100000)
        self.assertGreater(self.alpha_opaque, 100000)
        self.assertEqual(self.comp_opaque, 1024 * 540)

    def test_36_round82_r82a_png_exports_paths_sanitized_and_match_assets(self) -> None:
        pe = self.summary["runs"][
            "r82a_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_big6_schinese"
        ]["png_exports"]
        self.assertEqual(
            pe["alpha_png"]["path"],
            "reports/2026-11-21-round82-areadate-dst-grid-cleanhdmi-saveload-camset-mishoe-qemu/r82_saveload_camset10_mishoe_xlrh1_sync_debunk_slot1_erofs_preview.png",
        )
        self.assertEqual(
            pe["composited_png"]["path"],
            "reports/2026-11-21-round82-areadate-dst-grid-cleanhdmi-saveload-camset-mishoe-qemu/r82_areadate30_dst_grid3_cleanhdmi_marker_isolation_preview.png",
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

    def test_37_round82_deterministic_payload_hash_ignoring_volatile_timing(self) -> None:
        a = copy.deepcopy(self.summary)
        b = copy.deepcopy(self.summary)
        b["runs"]["r82a_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_big6_schinese"]["wall_elapsed_sec"] = 999.99
        b["runs"]["r82a_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_big6_schinese"]["r82_telemetry"]["wave68_init"]["verify_us"] = 12345
        ha = hashlib.sha256(json.dumps(_strip_volatile_timing(a), sort_keys=True).encode("utf-8")).hexdigest()
        hb = hashlib.sha256(json.dumps(_strip_volatile_timing(b), sort_keys=True).encode("utf-8")).hexdigest()
        self.assertEqual(ha, hb)

    def test_38_round82_verify_us_positive_under_3_seconds_across_all_3_runs(self) -> None:
        us_a = self.summary["runs"]["r82a_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_big6_schinese"]["r82_telemetry"]["wave68_init"]["verify_us"]
        us_b = self.summary["runs"]["r82b_wave68_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_guard"]["r82_telemetry"]["wave68_guard"]["verify_us"]
        us_c = self.summary["runs"]["r82c_clean_unmount_wave68_reset_h0_h3_big6_schinese"]["r82_telemetry"]["clean_unmount_wave68_h0_h3"]["verify_us"]
        for us in (us_a, us_b, us_c):
            self.assertGreater(us, 0)
            self.assertLess(us, 3_000_000)

    def test_39_round82_top_colors_transparent_plus_nonzero_equals_total_pixels(self) -> None:
        for rk in (
            "r82a_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_big6_schinese",
            "r82c_clean_unmount_wave68_reset_h0_h3_big6_schinese",
        ):
            gpe = self.summary["runs"][rk]["gpe0_readback"]
            color_map = {row["argb"]: row["pixels"] for row in gpe["top_colors"]}
            self.assertIn("0x00000000", color_map)
            self.assertEqual(color_map["0x00000000"] + gpe["nonzero_pixels"], gpe["total_pixels"])

    def test_40_round82_r82b_fast_early_exit_and_skipped_gpe0(self) -> None:
        r82b = self.summary["runs"]["r82b_wave68_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_guard"]
        self.assertEqual(r82b["duration_budget_sec"], 35)
        self.assertGreater(r82b["wall_elapsed_sec"], 1.0)
        self.assertLess(r82b["wall_elapsed_sec"], 60.0)
        self.assertTrue(r82b["gpe0_readback"]["skipped_stock_fx3_mode"])

    def test_41_round82_faithful_invariants_preserved_across_all_3_runs(self) -> None:
        for rk, rv in self.summary["runs"].items():
            fi = rv["faithful_invariants"]
            self.assertEqual(fi["FX6_NATIVE_FAITHFUL"], 1, rk)
            self.assertEqual(fi["subst_color"], 0, rk)
            self.assertEqual(fi["subst_image"], 0, rk)
            self.assertEqual(fi["forced_render"], 0, rk)
            self.assertEqual(fi["skipped_node"], 0, rk)
            self.assertEqual(fi["lock_bypass"], 0, rk)

    def test_42_round82_all_3_runs_stage_b_manifest_count_13(self) -> None:
        for rk, rv in self.summary["runs"].items():
            self.assertEqual(rv["stage_b"]["manifest_count"], 13, rk)
            self.assertEqual(len(rv["stage_b"]["manifest_items"]), 13, rk)

    def test_43_round82_all_3_runs_prefix_counts_include_fx6_r82(self) -> None:
        r82a_pc = self.summary["runs"]["r82a_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_big6_schinese"]["prefix_counts"]
        r82b_pc = self.summary["runs"]["r82b_wave68_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_guard"]["prefix_counts"]
        r82c_pc = self.summary["runs"]["r82c_clean_unmount_wave68_reset_h0_h3_big6_schinese"]["prefix_counts"]
        self.assertGreater(r82a_pc["FX6_R82_"], 10)
        self.assertEqual(r82b_pc["FX6_R82_"], 3)
        self.assertGreater(r82c_pc["FX6_R82_"], 10)

    def test_44_round82_r82_meta_invariants_across_all_3_runs(self) -> None:
        for rk, rv in self.summary["runs"].items():
            m = rv["stage_b"]["r82"]
            self.assertEqual(m["milestone_round_ordinal"], 82, rk)
            self.assertEqual(m["realhw_round_ordinal"], 55, rk)
            self.assertEqual(m["total_live_runs_at_completion"], 165, rk)
            self.assertEqual(m["total_png_receipts_at_completion"], 110, rk)
            self.assertEqual(m["marker_hdmi_pixels_injected"], 0, rk)
            self.assertEqual(m["camset_excluded_leaked_count"], 0, rk)
            self.assertEqual(m["dormant_fx3_cr2032_events"], 0, rk)
            self.assertEqual(m["dormant_fx6_dst_ui_events"], 0, rk)
            self.assertEqual(m["dormant_fx6_grid3_ui_events"], 0, rk)
            self.assertEqual(m["dormant_fx3_pro_camera_events"], 0, rk)
            self.assertEqual(m["dormant_fx6_ref_file_events"], 0, rk)
            self.assertEqual(m["dormant_fx3_sync_terminal_events"], 0, rk)
            self.assertEqual(m["dormant_fx6_genlock_events"], 0, rk)
            self.assertEqual(m["xlrh1_mishoe_mutex_violations"], 0, rk)
            self.assertEqual(m["usb_tx"], 0, rk)
            self.assertEqual(m["slot1_writes"], 0, rk)
            self.assertEqual(m["slot1_data_sector_writes"], 0, rk)
            self.assertEqual(m["slot1_avf_info_mutated"], 0, rk)
            self.assertEqual(m["raw_firmware_bytes_leaked"], 0, rk)
            self.assertEqual(m["emmc_write_count"], 0, rk)

    def test_45_round82_sanitize_helper_redacts_host_paths_and_reserved_port(self) -> None:
        dirty = {
            "run_id": "test-run",
            "lang": "schinese",
            "r82_mode": "areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_big6",
            "kernel_version": "Linux version 4.9.337-scel+",
            "kernel_bin": "/Users/fake/secret/kernel.bin",
            "dtb_bin": "/Users/fake/secret/guest.dtb",
            "build": {"tmp_build": "/private/tmp/build-123"},
            "stage_b": {"r82": {"r82_mode": "areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_big6"}},
            "r82_telemetry": {
                "wave68_init": {"r82_init_ok": 1},
                "wave68_guard": {"r82b_ok": 1},
                "clean_unmount_wave68_h0_h3": {"r82c_ok": 1, "surfaces_h0_eq_h3": 16},
            },
            "gpe0_readback": {"nonzero_pixels": 346686},
            "png_exports": {
                "alpha_png": {
                    "path": "/Users/kafu/repo/reports/2026-11-21-round82-areadate-dst-grid-cleanhdmi-saveload-camset-mishoe-qemu/r82_saveload_camset10_mishoe_xlrh1_sync_debunk_slot1_erofs_preview.png"
                }
            },
            "prefix_counts": {"FX6_R82_": 10},
        }
        sanitized = self.runner.sanitize_round82_summary(dirty, dirty, dirty)
        raw = json.dumps(sanitized)
        self.assertNotIn("/Users/", raw)
        self.assertNotIn("/private/tmp/", raw)
        self.assertNotIn("kernel_bin", raw)
        self.assertNotIn("dtb_bin", raw)
        self.assertIn(
            "reports/2026-11-21-round82-areadate-dst-grid-cleanhdmi-saveload-camset-mishoe-qemu/r82_saveload_camset10_mishoe_xlrh1_sync_debunk_slot1_erofs_preview.png",
            raw,
        )

    def test_46_round82_four_modes_and_mocked_donorless_work_root_none_master_gates(self) -> None:
        for env_overrides in (
            {},
            {"FX3_CLEAN_ROOM_TEST": "1"},
            {"FX3_FX6_FORCE_CLEAN_ROOM": "1"},
        ):
            with mock.patch.dict(os.environ, env_overrides, clear=False):
                parsed = self.runner.extract_milestones(
                    "Linux version 4.9.337-scel+\n"
                    "FX6_R82_WAVE68_INIT areadate30_dst_clockset_ok=1 grid3_cleanhdmi_marker_ok=1 "
                    "saveload_camset10_erofs_ok=1 sync_debunk_mishoe_xlrh1_ok=1 usb_tx=0 slot1_writes=0 r82_init_ok=1\n"
                )
                self.assertEqual(parsed["r82_telemetry"]["wave68_init"]["r82_init_ok"], 1)

        closure_pkg_dir = REPO_ROOT / "outputs" / "fx6-on-fx3-closure"
        safety_dir = REPO_ROOT / "outputs" / "fx3-safety"
        recovery_dir = REPO_ROOT / "outputs" / "fx3-recovery-adapter"
        firmware_lab_dir = REPO_ROOT / "outputs" / "fx3-firmware-lab"
        vm_dir = REPO_ROOT / "outputs" / "fx3-vm"
        added = [str(p) for p in (closure_pkg_dir, safety_dir, recovery_dir, firmware_lab_dir, vm_dir) if str(p) not in sys.path]
        for p in added:
            sys.path.insert(0, p)
        try:
            from fx6_closure.realhw_milestone364_master_gate import (
                evaluate_realhw_milestone364_master_gate,
            )
            from fx6_closure.realhw_milestone375_master_gate import (
                evaluate_realhw_milestone375_master_gate,
            )

            with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
                rep364 = evaluate_realhw_milestone364_master_gate(
                    repo_root=REPO_ROOT,
                    force_clean_room=True,
                    simulate_bench_dry_run=False,
                )
                self.assertEqual(rep364.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertTrue(rep364.all_pillars_milestone_ready)
                self.assertEqual(rep364.raw_firmware_bytes_leaked, 0)
                self.assertGreaterEqual(rep364.qemu_rounds_verified, 55)
                self.assertGreaterEqual(rep364.qemu_runs_verified, 165)
                self.assertGreaterEqual(rep364.qemu_png_receipts_verified, 110)

                rep375 = evaluate_realhw_milestone375_master_gate(
                    repo_root=REPO_ROOT,
                    force_clean_room=True,
                    simulate_bench_dry_run=False,
                )
                self.assertEqual(rep375.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertTrue(rep375.all_pillars_milestone_ready)
                self.assertEqual(rep375.raw_firmware_bytes_leaked, 0)
                self.assertGreaterEqual(rep375.qemu_rounds_verified, 55)
                self.assertGreaterEqual(rep375.qemu_runs_verified, 165)
                self.assertGreaterEqual(rep375.qemu_png_receipts_verified, 110)
        finally:
            for p in added:
                if p in sys.path:
                    sys.path.remove(p)

    def test_47_round82_argparse_percent_safe_help_and_no_hardcoded_python3(self) -> None:
        for line in self.runner_src.splitlines():
            if "help=" in line and "%" in line:
                stripped = line.replace("%%", "")
                self.assertNotIn("%", stripped, f"Unescaped '%' in argparse help: {line}")
        test_src = pathlib.Path(__file__).read_text(encoding="utf-8")
        forbidden_py = "/usr/" + "bin/python3"
        self.assertNotIn(forbidden_py, self.runner_src)
        self.assertNotIn(forbidden_py, test_src)

    def test_48_round82_all_110_pngs_under_27467b_and_clean_room_safe(self) -> None:
        round_dirs = [
            d for d in (REPO_ROOT / "reports").glob("2026-??-??-round*")
            if d.is_dir() and int(d.name.split("-round")[1].split("-")[0]) >= 28
        ]
        all_pngs = sorted(p for d in round_dirs for p in d.rglob("*.png") if p.is_file())
        self.assertGreaterEqual(len(all_pngs), 110)
        for p in all_pngs:
            self.assertLessEqual(p.stat().st_size, 27467, str(p))

    def test_49_round82_cli_help_subprocess_smoke_timeout_60(self) -> None:
        res = subprocess.run(
            [sys.executable, "-B", str(CLOSURE_DIR / "build_and_run_round.py"), "--help"],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        self.assertIn("--r82-mode", res.stdout)
        self.assertIn("areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_big6", res.stdout)

    def test_50_round82_wave68_uxc_and_node_tokens_wired_in_stage_a_source(self) -> None:
        for sym in (
            "r82_lookup_wave68_menu_node",
            "r82_lookup_uxc_token",
            "_f:0x6a9c:Area/Date/Time Setting",
            "base:0xe91a:Area Setting",
            "base:0xe917:Daylight Savings",
            "convert_setting_daylight_saving_to_saylight_saving",
            "_f:0x670d:Date Format",
            "37dlg_rec203_initial_setting_controller",
            "ns2:0x426c:Clock Set",
            "ns2:0x411f:Backup Battery End",
            "_f:0x6f9d:Grid Line Display",
            "_f:0x69c9:Grid Line Type",
            "_f:0x70c5:Grid Line Display Select",
            "BKID_APP_deleted_setting_grid_line_display_movie",
            "_f:0x61b2:Marker Display",
            "_f:0x62f9:Guideframe",
            "ns2:0x450a:Center Marker",
            "ns2:0x4520:Guide Frame",
            "_f:0x6254:Save/Load Settings",
            "%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT",
            "libSaveLoadSettings.so",
            "%c:%s/SONY/SETTING/%s/CAMPR%02d%c.DAT",
            "_f:0x763c:Memory/Recall Media",
            "_f:0x71ae:Save/Load FTP Settings",
            "%c:%s/SONY/PRO/CAMERA/%s/%s.ALL",
            "_f:0x6b31:Flash Sync Spd. Prty. (dormant on FX3 7.02)",
            "_g:0x645e:SYNCHRO_TERMINAL_OUTPUT_SET_ON (dormant on FX3 7.02)",
            "_f:0x6771:External Flash Set.",
            "_f:0x6211:Video Light Mode",
            "VIDEO_LIGHT_SET_AUTO_LOW_LIGHT",
        ):
            self.assertIn(sym, self.stage_a_src)

    def test_51_round82_report_markdown_has_chinese_conclusions_links_and_fact_inference_split(self) -> None:
        self.assertIn("## 结论先行", self.r82_readme)
        self.assertIn("实测事实", self.r82_readme)
        self.assertIn("推断", self.r82_readme)
        self.assertIn("file://", self.r82_readme)
        self.assertIn("55/55", self.r82_readme)
        self.assertIn("165/165", self.r82_readme)
        self.assertIn("110/110", self.r82_readme)
        self.assertIn("r82_areadate30_dst_grid3_cleanhdmi_marker_isolation_preview.png", self.r82_readme)
        self.assertIn("r82_saveload_camset10_mishoe_xlrh1_sync_debunk_slot1_erofs_preview.png", self.r82_readme)

    def test_52_round82_closure_readme_documents_round82_55_rounds_165_runs_110_pngs(self) -> None:
        self.assertIn("## 82. Round 82", self.closure_readme)
        self.assertIn("55/55", self.closure_readme)
        self.assertIn("165/165", self.closure_readme)
        self.assertIn("110/110", self.closure_readme)
        self.assertIn("r82a", self.closure_readme)
        self.assertIn("r82b", self.closure_readme)
        self.assertIn("r82c", self.closure_readme)

    def test_53_round82_continuity_from_round81(self) -> None:
        self.assertEqual(self.r81_summary["round"], 81)
        self.assertEqual(self.summary["round"], self.r81_summary["round"] + 1)
        self.assertEqual(self.summary["raw_firmware_bytes_leaked"], 0)

    def test_54_round82_no_stray_temp_files_or_pyc_in_closure_dir(self) -> None:
        for bad_name in ("tmp", "scratch", ".worktrees"):
            self.assertFalse((REPO_ROOT / bad_name).exists(), bad_name)
        pyc_files = list(CLOSURE_DIR.rglob("*.pyc"))
        self.assertEqual(pyc_files, [])

    def test_55_round82_no_artifacts_subdir_under_closure(self) -> None:
        self.assertFalse((CLOSURE_DIR / "artifacts").exists())

    def test_56_round82_wave68_constants_and_zero_dormant_events_across_all_runs(self) -> None:
        self.assertIn("#define R82_FX3_AREA_ZONE_COUNT          30", self.stage_a_src)
        self.assertIn("#define R82_CAMSET_EXCL_ALL_MASK         0x00FFU", self.stage_a_src)
        self.assertIn("#define R82_PMIC_5V_MAX_MA               900", self.stage_a_src)
        self.assertIn("#define R82_FX6_DORMANT_GENLOCK_SYMS     107", self.stage_a_src)
        for rk in self.EXPECTED_RUN_KEYS:
            rv = self.summary["runs"][rk]
            t = rv["r82_telemetry"]
            for sec_name in ("wave68_init", "wave68_guard", "clean_unmount_wave68_h0_h3"):
                sec = t.get(sec_name)
                if sec:
                    for key in (
                        "marker_hdmi_pixels_injected",
                        "camset_excluded_leaked_count",
                        "dormant_fx3_cr2032_events",
                        "dormant_fx6_dst_ui_events",
                        "dormant_fx6_grid3_ui_events",
                        "dormant_fx3_pro_camera_events",
                        "dormant_fx6_ref_file_events",
                        "dormant_fx3_sync_terminal_events",
                        "dormant_fx6_genlock_events",
                        "xlrh1_mishoe_mutex_violations",
                    ):
                        self.assertEqual(sec.get(key, 0), 0, f"{rk}:{sec_name}:{key}")


if __name__ == "__main__":
    unittest.main()
