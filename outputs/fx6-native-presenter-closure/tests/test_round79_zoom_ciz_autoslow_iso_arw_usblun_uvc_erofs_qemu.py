#!/usr/bin/env python3
"""Offline four-mode unit tests for FX6-on-FX3 Round 79 (52/52 Real-HW Rounds R28..R79, 154th..156th Live Runs -> 156/156 Total, 104/104 PNGs <= 27,467 B — Wave-65)."""
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
ROUND79_REPORT_DIR = (
    REPO_ROOT
    / "reports"
    / "2026-11-21-round79-zoom-ciz-autoslow-iso-arw-usblun-uvc-erofs-qemu"
)
WAVE65_SPEC_PATH = (
    REPO_ROOT
    / "reports"
    / "2026-11-17-global-sony-wave65-zoom-ciz-autoslow-iso-arw-rawcomp-usblun-uvc-intel"
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


def _build_overlay_for_r79(
    runner,
    parent_cpio: pathlib.Path,
    fp,
    fv,
    fb,
    fake_run,
    jit_meta: Dict[str, Any],
    work: pathlib.Path,
    r79_mode: str,
    lang: str = "schinese",
    enable_r79: bool = True,
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
            enable_r78=True,
            r78_mode="breathing_camid_copyright46_powersave9_ntscpal_big6",
            enable_r79=enable_r79,
            r79_mode=r79_mode,
            sd_manifest_mode="valid",
            lang=lang,
            shim_bytes=b"SHIM",
        )


class TestRound79ZoomCizAutoslowIsoArwUsblunUvcErofsQemu(unittest.TestCase):
    EXPECTED_RUN_KEYS = (
        "r79a_zoom_ciz_autoslow_iso_arw_usblun_uvc_erofs_big6_schinese",
        "r79b_wave65_zoom_ciz_autoslow_iso_arw_usblun_uvc_guard",
        "r79c_clean_unmount_wave65_reset_h0_h3_big6_schinese",
    )

    runner: Any
    runner_src: str
    stage_a_src: str
    shim_src: str
    wave65_spec: str
    summary_raw: str
    summary: Dict[str, Any]
    r79_readme: str
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
    launcher_r79: Optional[bytes]
    shim_r79: Optional[bytes]
    shim_r78: Optional[bytes]
    r78_summary: Dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = _load_closure_module("fx6_brr_r79_cached", "build_and_run_round.py")
        cls.runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")
        cls.stage_a_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        cls.shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        cls.wave65_spec = WAVE65_SPEC_PATH.read_text(encoding="utf-8")
        cls.summary_raw = (ROUND79_REPORT_DIR / "summary.json").read_text(encoding="utf-8")
        cls.summary = json.loads(cls.summary_raw)
        cls.r79_readme = (ROUND79_REPORT_DIR / "README.md").read_text(encoding="utf-8")
        cls.closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")

        alpha_p = ROUND79_REPORT_DIR / "r79_arw_lossless_hlg_usblun_pd_uvc_erofs_preview.png"
        comp_p = ROUND79_REPORT_DIR / "r79_zoom_ciz_autoslow_iso_dualbase_preview.png"
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
            cls.ov_a = _build_overlay_for_r79(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wa", "zoom_ciz_autoslow_iso_arw_usblun_uvc_erofs_big6", lang="schinese",
            )
            cls.ov_b = _build_overlay_for_r79(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wb", "wave65_zoom_ciz_autoslow_iso_arw_usblun_uvc_guard", lang="en",
            )
            cls.ov_c = _build_overlay_for_r79(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wc", "clean_unmount_wave65_reset_h0_h3_big6", lang="schinese",
            )
            cls.ov_off = _build_overlay_for_r79(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "woff", "zoom_ciz_autoslow_iso_arw_usblun_uvc_erofs_big6", enable_r79=False,
            )
            cls.invalid_mode_raised = False
            try:
                _build_overlay_for_r79(
                    cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                    tpath / "wbad", "invalid_r79_mode",
                )
            except ValueError:
                cls.invalid_mode_raised = True

            zig_bin = shutil.which("zig") or (
                str(cls.runner.ZIG) if cls.runner.ZIG.is_file() else None
            )
            if zig_bin is not None:
                verify_r79_out = tpath / "fx6-stage-a-verify-r79"
                shim_r79_out = tpath / "libgrm-fbinit9-r79.so"
                shim_r78_out = tpath / "libgrm-fbinit9-r78.so"
                for cmd in (
                    [
                        zig_bin, "cc", "-target", "aarch64-linux-gnu.2.25", "-O0",
                        str(CLOSURE_DIR / "fx6-stage-a-verify.c"),
                        "-ldl", "-lpthread", "-o", str(verify_r79_out),
                    ],
                    [
                        zig_bin, "cc", "-target", "aarch64-linux-gnu.2.25", "-O0",
                        "-shared", "-fPIC", "-DFX6_ROUND=79",
                        str(CLOSURE_DIR / "libgrm-fbinit9.c"),
                        "-ldl", "-lpthread", "-o", str(shim_r79_out),
                    ],
                    [
                        zig_bin, "cc", "-target", "aarch64-linux-gnu.2.25", "-O0",
                        "-shared", "-fPIC", "-DFX6_ROUND=78",
                        str(CLOSURE_DIR / "libgrm-fbinit9.c"),
                        "-ldl", "-lpthread", "-o", str(shim_r78_out),
                    ],
                ):
                    cls.runner.subprocess.run(cmd, check=True, timeout=120)
                cls.launcher_r79 = verify_r79_out.read_bytes()
                cls.shim_r79 = shim_r79_out.read_bytes()
                cls.shim_r78 = shim_r78_out.read_bytes()
            else:
                cls.launcher_r79 = None
                cls.shim_r79 = None
                cls.shim_r78 = None

        cls.r78_summary = json.loads(
            (
                REPO_ROOT
                / "reports"
                / "2026-11-18-round78-breathing-camid-copyright46-powersave9-ntscpal-qemu"
                / "summary.json"
            ).read_text(encoding="utf-8")
        )

    def test_01_wave65_global_spec_present_and_covers_all_4_pillars(self) -> None:
        self.assertTrue(WAVE65_SPEC_PATH.is_file())
        for needle in (
            "Zoom Range",
            "ClearImage Zoom",
            "Digital Zoom",
            "Zoom Lever Speed",
            "Zoom Ring Rotate",
            "Handle Zoom",
            "Auto Slow Shutter",
            "ISO Range Limit",
            "ISO AUTO Min. SS",
            "Base ISO",
            "RAW File Type",
            "Lossless Comp",
            "HLG Still Image",
            "STILL_HLD_PHOTO_",
            "Sort Recording",
            "USB Connection Mode",
            "USB LUN Setting",
            "USB Power Supply",
            "NP-FZ100",
            "DC-C1",
            "19.5V",
            "USB_STREAMING_PROCAM",
            "Movie Rec During Streaming",
            "Rec. Media dur HDMI Output",
        ):
            self.assertIn(needle, self.wave65_spec)

    def test_02_round79_summary_schema_milestone_and_zero_leaks(self) -> None:
        self.assertNotIn("/Users/", self.summary_raw)
        self.assertNotIn("/private/tmp/", self.summary_raw)
        self.assertNotIn("/tmp/round79", self.summary_raw)
        self.assertEqual(
            self.summary["schema"],
            "fx6-on-fx3-round79-zoom-ciz-autoslow-iso-arw-usblun-uvc-erofs-qemu-v1",
        )
        self.assertEqual(self.summary["round"], 79)
        self.assertIn("52/52 Real-HW Rounds", self.summary["milestone"])
        self.assertIn("156/156 Live Runs", self.summary["milestone"])
        self.assertIn("104/104 PNGs <= 27,467 B", self.summary["milestone"])
        self.assertEqual(self.summary["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(self.summary["usb_tx"], 0)
        self.assertEqual(self.summary["slot1_writes"], 0)
        self.assertEqual(tuple(self.summary["runs"].keys()), self.EXPECTED_RUN_KEYS)

    def test_03_round79_hardware_safety_locks_all_false_and_zero(self) -> None:
        locks = self.summary["hardware_safety_locks"]
        self.assertIs(locks["hardware_live_attachment_authorized"], False)
        self.assertIs(locks["persistent_emmc_writes_authorized"], False)
        self.assertIs(locks["cross_model_flash_authorized"], False)
        self.assertIs(locks["spi_nor_write_authorized"], False)
        self.assertIs(locks["el3_payload_transmit_authorized"], False)
        self.assertEqual(locks["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(locks["usb_tx"], 0)
        self.assertEqual(locks["slot1_writes"], 0)

    def test_04_round79_cli_accepts_round79_and_all_3_r79_modes(self) -> None:
        self.assertIn(", 75, 76, 77, 78, 79]", self.runner_src)
        for mode in (
            "zoom_ciz_autoslow_iso_arw_usblun_uvc_erofs_big6",
            "wave65_zoom_ciz_autoslow_iso_arw_usblun_uvc_guard",
            "clean_unmount_wave65_reset_h0_h3_big6",
        ):
            self.assertIn(mode, self.runner_src)

    def test_05_round79_overlay_rejects_invalid_r79_mode(self) -> None:
        self.assertTrue(self.invalid_mode_raised)

    def test_06_round79_overlay_r79a_injects_etc_fx6_stage_r79_and_appfw_launch(self) -> None:
        replacements, additions, meta = self.ov_a
        self.assertTrue(meta["r79_enabled"])
        self.assertIn("etc/fx6_stage_r79", additions)
        self.assertIn("etc/fx6_r79_libjit.so", additions)
        r79_cfg = additions["etc/fx6_stage_r79"][0].decode("utf-8")
        self.assertIn("stage_r79=1", r79_cfg)
        self.assertIn("r79_mode=zoom_ciz_autoslow_iso_arw_usblun_uvc_erofs_big6", r79_cfg)
        self.assertIn("milestone_52nd_realhw_156th_live_104_pngs=1", r79_cfg)
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("/usr/bin/appfw-launch", init_txt)
        self.assertNotIn("--r79-wave65-guard", init_txt)

    def test_07_round79_overlay_r79b_injects_early_guard_probe_and_poweroff(self) -> None:
        replacements, _, meta = self.ov_b
        self.assertEqual(
            meta["r79"]["r79_mode"],
            "wave65_zoom_ciz_autoslow_iso_arw_usblun_uvc_guard",
        )
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("--r79-wave65-guard", init_txt)
        self.assertIn("FX6_R79_WAVE65_GUARD_RC=", init_txt)
        self.assertIn("FX6_R79_WAVE65_GUARD_EXIT", init_txt)
        self.assertIn("poweroff -f", init_txt)

    def test_08_round79_overlay_r79c_integrated_runs_stage_b_big6(self) -> None:
        replacements, additions, meta = self.ov_c
        self.assertEqual(meta["r79"]["r79_mode"], "clean_unmount_wave65_reset_h0_h3_big6")
        r79_cfg = additions["etc/fx6_stage_r79"][0].decode("utf-8")
        self.assertIn("r79_mode=clean_unmount_wave65_reset_h0_h3_big6", r79_cfg)
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("/usr/bin/appfw-launch", init_txt)
        self.assertNotIn("--r79-wave65-guard", init_txt)

    def test_09_round79_overlay_disabled_when_enable_r79_false(self) -> None:
        _, additions, meta = self.ov_off
        self.assertFalse(meta["r79_enabled"])
        self.assertNotIn("etc/fx6_stage_r79", additions)
        self.assertNotIn("etc/fx6_r79_libjit.so", additions)
        self.assertNotIn("r79", meta)

    def test_10_round79_stage_a_c_source_contains_all_wave65_probes(self) -> None:
        for sym in (
            "setup_r79_zoom_ciz_autoslow_iso_arw_usblun_uvc_probe",
            "run_r79_wave65_guard_probe",
            "run_r79_clean_unmount_wave65_h0_h3_probe",
            "r79_wave65_initialize",
            "r79_wave65_zero_init",
            "r79_wave65_camera_settings_reset",
            "r79_wave65_reset_network_settings",
            "r79_configure_zoom_system",
            "r79_eval_dual_base_iso",
            "r79_configure_autoslow_iso_baseiso",
            "r79_configure_still_arw_hlg_sort_recording",
            "r79_configure_usb_lun_pd_uvc_streaming",
            "FX6_R79_WAVE65_INIT",
            "FX6_R79_WAVE65_GUARD",
            "FX6_R79_CLEAN_UNMOUNT_WAVE65_H0_H3",
            "--r79-wave65-guard",
            "--r79-clean-unmount-wave65-h0-h3",
            "/etc/fx6_stage_r79",
        ):
            self.assertIn(sym, self.stage_a_src)

    def test_11_round79_shim_c_source_contains_r79_guarded_bridges(self) -> None:
        self.assertIn("#if FX6_ROUND >= 79", self.shim_src)
        for sym in (
            "FX6_R79_ZOOM_CIZ_SPEED8_BRIDGE",
            "FX6_R79_AUTOSLOW6_ISO_BASEISO_BRIDGE",
            "FX6_R79_ARW_LOSSLESS_HLG_SORT_EROFS_BRIDGE",
            "FX6_R79_USBLUN_PD_UVC_STREAMING_EROFS_BRIDGE",
            "FX6_R79_LANG_TELEMETRY",
            "FX6_STAGE_B_R79_BRIDGE",
        ):
            self.assertIn(sym, self.shim_src)

    def test_12_round79_compile_launcher_and_shim_aarch64_elf_symbols(self) -> None:
        if self.launcher_r79 is None or self.shim_r79 is None:
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertEqual(self.launcher_r79[:4], b"\x7fELF")
        self.assertEqual(self.shim_r79[:4], b"\x7fELF")
        self.assertEqual(struct.unpack_from("<H", self.shim_r79, 18)[0], 183)
        self.assertIn(b"FX6_R79_ZOOM_CIZ_SPEED8_BRIDGE", self.shim_r79)
        self.assertIn(b"FX6_R79_AUTOSLOW6_ISO_BASEISO_BRIDGE", self.shim_r79)
        self.assertIn(b"FX6_R79_ARW_LOSSLESS_HLG_SORT_EROFS_BRIDGE", self.shim_r79)
        self.assertIn(b"FX6_R79_USBLUN_PD_UVC_STREAMING_EROFS_BRIDGE", self.shim_r79)

    def test_13_round79_shim_round78_backward_compat_excludes_r79_bridges(self) -> None:
        if self.shim_r78 is None:
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertIn(b"FX6_R78_BREATHING_120P_CATALYST_BRIDGE", self.shim_r78)
        self.assertNotIn(b"FX6_R79_ZOOM_CIZ_SPEED8_BRIDGE", self.shim_r78)

    def test_14_round79_parse_log_extracts_all_r79_prefixes_and_rc(self) -> None:
        serial_text = "\n".join(
            [
                "Linux version 4.9.337-scel+ (sony@fx3)",
                "FX6_R79_WAVE65_INIT fx3_wave65_nodes_ok=1 uxc_tokens_ok=1 zoom_ciz_speed8_ok=1 autoslow6_iso_baseiso_ok=1 arw_lossless_hlg_sort_ok=1 usblun_pd_uvc_streaming_ok=1 usb_tx=0 slot1_writes=0 emmc_write_count=0 r79_init_ok=1",
                "FX6_R79_ZOOM_CIZ_SPEED8_BRIDGE zoom_ciz_digital_reset_split_ok=1 zoom_non_optical_interlocks_ok=1 fx6_zero_digital_zoom_handle_ok=1 zoom_ciz_speed8_ok=1 r79_bridge_ok=1",
                "FX6_R79_AUTOSLOW6_ISO_BASEISO_BRIDGE autoslow_6way_angle_mutex_ok=1 iso_limit_still_min_ss_dualbase_ok=1 autoslow6_iso_baseiso_ok=1",
                "FX6_R79_ARW_LOSSLESS_HLG_SORT_EROFS_BRIDGE arw_comp_uncomp_dormant_lossless_ok=1 hlg_still_bt2100_sort_slot1_erofs30_ok=1 arw_lossless_hlg_sort_ok=1 slot1_writes=0",
                "FX6_R79_USBLUN_PD_UVC_STREAMING_EROFS_BRIDGE usb_mode4_lun_single_slot1_erofs30_ok=1 usb_pd_fz100_vs_fx6_19v5_dcin_ok=1 dual_fx3_fx6_uvc_debunk_streaming_erofs30_ok=1 usblun_pd_uvc_streaming_ok=1 usb_tx=0 slot1_writes=0",
                "FX6_R79_LANG_TELEMETRY lang=schinese font_bank=23 str_bank=19 milestone_52nd_realhw_156th_live_104_pngs=1 usb_tx=0 slot1_writes=0 r79_bridge_ok=1",
                "FX6_STAGE_B_R79_BRIDGE round=79 faithful=1 nop_count=0 milestone_52nd_realhw_156th_live_104_pngs=1 usb_tx=0 slot1_writes=0 emmc_write_count=0",
                "FX6_R79_WAVE65_GUARD fx6_digital_zoom_rc=-95 raw_lossless_rc=-95 fx3_uvc_dormant_rc=-95 fx6_uvc_dormant_rc=-95 lun_single_msc_slot1_erofs_rc=-30 live_attach_eperm_rc=-1 r79b_ok=1",
                "FX6_R79_WAVE65_GUARD_RC=0",
                "FX6_R79_CLEAN_UNMOUNT_WAVE65_H0_H3 stock_unmount_restored_ok=1 surfaces_h0_eq_h3=16 usb_tx=0 slot1_writes=0 r79c_ok=1",
            ]
        ) + "\n"
        parsed = self.runner.extract_milestones(serial_text)
        r79_t = parsed["r79_telemetry"]
        self.assertEqual(r79_t["wave65_guard_rc"], 0)
        self.assertEqual(r79_t["wave65_init"]["zoom_ciz_speed8_ok"], 1)
        self.assertEqual(r79_t["zoom_ciz_speed8_bridge"]["zoom_ciz_speed8_ok"], 1)
        self.assertEqual(r79_t["autoslow6_iso_baseiso_bridge"]["autoslow6_iso_baseiso_ok"], 1)
        self.assertEqual(r79_t["arw_lossless_hlg_sort_erofs_bridge"]["arw_lossless_hlg_sort_ok"], 1)
        self.assertEqual(r79_t["usblun_pd_uvc_streaming_erofs_bridge"]["usblun_pd_uvc_streaming_ok"], 1)
        self.assertEqual(r79_t["lang_telemetry"]["milestone_52nd_realhw_156th_live_104_pngs"], 1)
        self.assertEqual(r79_t["stage_b_bridge"]["round"], 79)
        self.assertEqual(r79_t["wave65_guard"]["r79b_ok"], 1)
        self.assertEqual(r79_t["clean_unmount_wave65_h0_h3"]["surfaces_h0_eq_h3"], 16)
        self.assertEqual(parsed["prefix_counts"]["FX6_R79_"], 9)

    def test_15_round79_parse_log_defaults_when_no_r79_lines_present(self) -> None:
        parsed = self.runner.extract_milestones("Linux version 4.9.337-scel+\n")
        self.assertIsNone(parsed["r79_telemetry"])
        self.assertEqual(parsed["prefix_counts"].get("FX6_R79_", 0), 0)

    def test_16_round79_runner_preserves_r78_prefix_and_uses_r79_stage_label(self) -> None:
        self.assertIn('if args.round >= 78:\n        tmp_prefix = "fx6-r78"', self.runner_src)
        self.assertIn('if args.round >= 79:\n        tmp_prefix = "fx6-r79"', self.runner_src)
        self.assertIn(
            "52RealHw156thLiveWave65ZoomCizAutoSlowIsoArwUsbLunUvcErofs30",
            self.runner_src,
        )

    def test_17_round79_runner_portability_and_sanitizer_helper(self) -> None:
        self.assertIn('shutil.which("zig")', self.runner_src)
        self.assertIn("FX6_SCRATCH_DIR", self.runner_src)
        self.assertIn("def sanitize_round79_summary(", self.runner_src)
        self.assertNotIn("/usr/" + "bin/python3", self.runner_src)

    def test_18_round79_summary_json_zero_host_path_scratch_and_elapsed_leaks(self) -> None:
        for forbidden in (
            "/Users/",
            "/private/tmp/",
            "/var/folders/",
            "/tmp/round79",
            "work/_scratch/",
            "work/_tests/",
            "elapsed_seconds",
            "elapsed_ms",
            ":87" + "68",
        ):
            self.assertNotIn(forbidden, self.summary_raw)

    def test_19_round79_summary_audit_block_confirms_52_rounds_156_runs_104_pngs(self) -> None:
        audit = self.summary["r79_zoom_ciz_autoslow_iso_arw_usblun_uvc_erofs_audit"]
        self.assertEqual(audit["round"], 79)
        self.assertGreaterEqual(audit["realhw_rounds_count"], 52)
        self.assertGreaterEqual(audit["total_live_runs"], 156)
        self.assertGreaterEqual(audit["total_png_receipts"], 104)
        self.assertGreaterEqual(audit["milestone324_qemu_rounds"], 52)
        self.assertGreaterEqual(audit["milestone324_qemu_runs"], 156)
        self.assertGreaterEqual(audit["milestone324_png_receipts"], 104)
        self.assertGreaterEqual(audit["milestone364_qemu_rounds"], 52)
        self.assertGreaterEqual(audit["milestone364_qemu_runs"], 156)
        self.assertGreaterEqual(audit["milestone364_png_receipts"], 104)
        self.assertEqual(audit["total_runs"], 3)
        negative_keys = {
            "fx6_digital_zoom_supported",
            "fx3_iso_auto_min_ss_movie_supported",
            "fx3_raw_lossless_comp_exposed",
            "fx6_still_arw_hlg_photo_supported",
            "fx3_native_uvc_usb_streaming_exposed",
            "fx6_native_uvc_usb_streaming_exposed",
            "fx3_usb_pd_battery_free_supported",
        }
        for nk in negative_keys:
            self.assertIs(audit[nk], False, nk)
        for k, v in audit.items():
            if isinstance(v, bool) and k not in negative_keys:
                self.assertTrue(v, f"Expected audit boolean {k} to be True")

    def test_20_round79_all_3_runs_present_with_kernel_4_9_337_and_zero_crashes_writes(self) -> None:
        runs = self.summary["runs"]
        self.assertEqual(list(runs.keys()), list(self.EXPECTED_RUN_KEYS))
        for rk, rv in runs.items():
            self.assertEqual(rv["round"], 79, rk)
            self.assertIn("4.9.337-scel+", rv["kernel_version"], rk)
            self.assertEqual(rv["nop_count"], 0, rk)
            self.assertEqual(rv["crashes"], 0, rk)
            self.assertEqual(rv["emmc_write_count"], 0, rk)
            self.assertGreater(rv["wall_elapsed_sec"], 0.0, rk)

    def test_21_round79_r79a_pillar1_zoom_ciz_digital_and_fx6_zero_digital(self) -> None:
        init_t = self.summary["runs"][
            "r79a_zoom_ciz_autoslow_iso_arw_usblun_uvc_erofs_big6_schinese"
        ]["r79_telemetry"]["wave65_init"]
        self.assertEqual(init_t["fx3_wave65_nodes_ok"], 1)
        self.assertEqual(init_t["uxc_tokens_ok"], 1)
        self.assertEqual(init_t["zoom_ciz_speed8_ok"], 1)
        self.assertEqual(init_t["fx6_digital_zoom_rc"], -95)
        self.assertEqual(init_t["ciz_120p_lock_rc"], -16)
        self.assertEqual(init_t["dormant_fx6_digital_zoom_events"], 0)

    def test_22_round79_r79a_pillar2_autoslow6_iso_limit_still_minss_dualbase(self) -> None:
        init_t = self.summary["runs"][
            "r79a_zoom_ciz_autoslow_iso_arw_usblun_uvc_erofs_big6_schinese"
        ]["r79_telemetry"]["wave65_init"]
        self.assertEqual(init_t["autoslow6_iso_baseiso_ok"], 1)
        self.assertEqual(init_t["autoslow_cineei_lock_rc"], -16)
        self.assertEqual(init_t["minss_movie_lock_rc"], -16)
        self.assertEqual(init_t["dormant_movie_iso_auto_min_ss_events"], 0)

    def test_23_round79_r79a_pillar3_arw_dormant_lossless_hlg_sort_erofs30(self) -> None:
        init_t = self.summary["runs"][
            "r79a_zoom_ciz_autoslow_iso_arw_usblun_uvc_erofs_big6_schinese"
        ]["r79_telemetry"]["wave65_init"]
        self.assertEqual(init_t["arw_lossless_hlg_sort_ok"], 1)
        self.assertEqual(init_t["raw_lossless_dormant_rc"], -95)
        self.assertEqual(init_t["sort_slot1_erofs_rc"], -30)
        self.assertEqual(init_t["dormant_raw_lossless_comp_events"], 0)
        self.assertEqual(init_t["slot1_writes"], 0)
        self.assertEqual(init_t["slot1_data_sector_writes"], 0)

    def test_24_round79_r79a_pillar4_usblun_single_pd_dual_uvc_streaming_erofs30(self) -> None:
        init_t = self.summary["runs"][
            "r79a_zoom_ciz_autoslow_iso_arw_usblun_uvc_erofs_big6_schinese"
        ]["r79_telemetry"]["wave65_init"]
        self.assertEqual(init_t["usblun_pd_uvc_streaming_ok"], 1)
        self.assertEqual(init_t["lun_single_slot1_erofs_rc"], -30)
        self.assertEqual(init_t["slot1_spotlight_erofs_rc"], -30)
        self.assertEqual(init_t["pd_no_fz100_ebusy_rc"], -16)
        self.assertEqual(init_t["fx3_uvc_dormant_rc"], -95)
        self.assertEqual(init_t["fx6_uvc_dormant_rc"], -95)
        self.assertEqual(init_t["stream_rec_slot1_erofs_rc"], -30)
        self.assertEqual(init_t["p2_write_blocked_rc"], -30)
        self.assertEqual(init_t["p2_sha256_match"], 1)
        self.assertEqual(init_t["p12_sha256_match"], 1)
        self.assertEqual(init_t["cnflasha_sha256_match"], 1)
        self.assertEqual(init_t["slot1_vault_sha256_match"], 1)
        self.assertEqual(init_t["dormant_uvc_fx3_events"], 0)
        self.assertEqual(init_t["dormant_uvc_fx6_events"], 0)
        self.assertEqual(init_t["usb_tx"], 0)
        self.assertEqual(init_t["slot1_writes"], 0)
        self.assertEqual(init_t["emmc_write_count"], 0)
        self.assertEqual(init_t["r79_init_ok"], 1)

    def test_25_round79_r79a_stage_b_schinese_lang_telemetry_and_bridge(self) -> None:
        r79a_t = self.summary["runs"][
            "r79a_zoom_ciz_autoslow_iso_arw_usblun_uvc_erofs_big6_schinese"
        ]["r79_telemetry"]
        lt = r79a_t["lang_telemetry"]
        self.assertEqual(lt["lang"], "schinese")
        self.assertEqual(lt["bk4_lang_id"], "0x02cf019c")
        self.assertEqual(lt["bk4_lang_val"], "0x19")
        self.assertEqual(lt["lang_enum"], "0x2b45_CHINESE_SIMPLIFIED")
        self.assertEqual(lt["font_bank"], 23)
        self.assertEqual(lt["str_bank"], 19)
        self.assertEqual(lt["gpe_fb"], 0)
        self.assertEqual(lt["milestone_52nd_realhw_156th_live_104_pngs"], 1)
        self.assertEqual(lt["usb_tx"], 0)
        self.assertEqual(lt["slot1_writes"], 0)
        self.assertEqual(lt["raw_firmware_bytes_leaked"], 0)

        sb = r79a_t["stage_b_bridge"]
        self.assertEqual(sb["round"], 79)
        self.assertEqual(sb["faithful"], 1)
        self.assertEqual(sb["nop_count"], 0)
        self.assertEqual(sb["zoom_ciz_15x_2x_digital_4x_fx6_zero_digital_ok"], 1)
        self.assertEqual(sb["autoslow_6way_iso_limit_still_min_ss_dualbase_ok"], 1)
        self.assertEqual(sb["arw_dormant_lossless_hlg_still_sort_erofs30_ok"], 1)
        self.assertEqual(sb["usb_mode4_lun_single_slot1_pd_fz100_dual_uvc_debunk_ok"], 1)
        self.assertEqual(sb["milestone_52nd_realhw_156th_live_104_pngs"], 1)

    def test_26_round79_r79a_stage_b_4_pillar_bridges_verified(self) -> None:
        r79a_t = self.summary["runs"][
            "r79a_zoom_ciz_autoslow_iso_arw_usblun_uvc_erofs_big6_schinese"
        ]["r79_telemetry"]
        pb1 = r79a_t["zoom_ciz_speed8_bridge"]
        self.assertEqual(pb1["zoom_ciz_digital_reset_split_ok"], 1)
        self.assertEqual(pb1["zoom_non_optical_interlocks_ok"], 1)
        self.assertEqual(pb1["fx6_zero_digital_zoom_handle_ok"], 1)
        self.assertEqual(pb1["zoom_ciz_speed8_ok"], 1)
        self.assertEqual(pb1["dormant_fx6_digital_zoom_events"], 0)
        self.assertEqual(pb1["r79_bridge_ok"], 1)

        pb2 = r79a_t["autoslow6_iso_baseiso_bridge"]
        self.assertEqual(pb2["autoslow_6way_angle_mutex_ok"], 1)
        self.assertEqual(pb2["iso_limit_still_min_ss_dualbase_ok"], 1)
        self.assertEqual(pb2["autoslow6_iso_baseiso_ok"], 1)
        self.assertEqual(pb2["dormant_movie_iso_auto_min_ss_events"], 0)

        pb3 = r79a_t["arw_lossless_hlg_sort_erofs_bridge"]
        self.assertEqual(pb3["arw_comp_uncomp_dormant_lossless_ok"], 1)
        self.assertEqual(pb3["hlg_still_bt2100_sort_slot1_erofs30_ok"], 1)
        self.assertEqual(pb3["arw_lossless_hlg_sort_ok"], 1)
        self.assertEqual(pb3["dormant_raw_lossless_comp_events"], 0)
        self.assertEqual(pb3["slot1_writes"], 0)

        pb4 = r79a_t["usblun_pd_uvc_streaming_erofs_bridge"]
        self.assertEqual(pb4["usb_mode4_lun_single_slot1_erofs30_ok"], 1)
        self.assertEqual(pb4["usb_pd_fz100_vs_fx6_19v5_dcin_ok"], 1)
        self.assertEqual(pb4["dual_fx3_fx6_uvc_debunk_streaming_erofs30_ok"], 1)
        self.assertEqual(pb4["usblun_pd_uvc_streaming_ok"], 1)
        self.assertEqual(pb4["dormant_uvc_fx3_events"], 0)
        self.assertEqual(pb4["dormant_uvc_fx6_events"], 0)
        self.assertEqual(pb4["usb_tx"], 0)
        self.assertEqual(pb4["slot1_writes"], 0)

    def test_27_round79_r79a_realhw_mechanisms_verified_block_populated(self) -> None:
        rmv = self.summary["realhw_mechanisms_verified"]
        for key in (
            "wave65_zoom_ciz_autoslow_iso_arw_usblun_uvc_init",
            "zoom_ciz_speed8_stage_b_bridge",
            "autoslow6_iso_baseiso_stage_b_bridge",
            "arw_lossless_hlg_sort_erofs_stage_b_bridge",
            "usblun_pd_uvc_streaming_erofs_stage_b_bridge",
            "wave65_fail_closed_guard",
            "clean_unmount_wave65_reset_and_16_h0_h3",
        ):
            self.assertIn(key, rmv)
            self.assertTrue(bool(rmv[key]), key)

    def test_28_round79_r79b_guard_blocks_pillar1_zoom_ciz_fx6_zero_digital(self) -> None:
        g = self.summary["runs"][
            "r79b_wave65_zoom_ciz_autoslow_iso_arw_usblun_uvc_guard"
        ]["r79_telemetry"]["wave65_guard"]
        self.assertEqual(g["fx6_digital_zoom_rc"], -95)
        self.assertEqual(g["fx3_ciz_still_raw_rc"], -16)
        self.assertEqual(g["fx3_ciz_120p_rc"], -16)
        self.assertEqual(g["fx3_dig_sq120_rc"], -16)
        self.assertEqual(g["fx6_ciz_sq120_rc"], -16)
        self.assertEqual(g["fx6_ciz_raw_rc"], -16)
        self.assertEqual(g["zoom_spd9_einval_rc"], -22)

    def test_29_round79_r79b_guard_blocks_pillar2_autoslow6_iso_limit_minss_baseiso(self) -> None:
        g = self.summary["runs"][
            "r79b_wave65_zoom_ciz_autoslow_iso_arw_usblun_uvc_guard"
        ]["r79_telemetry"]["wave65_guard"]
        self.assertEqual(g["as_sq_lock_rc"], -16)
        self.assertEqual(g["as_s_lock_rc"], -16)
        self.assertEqual(g["as_m_lock_rc"], -16)
        self.assertEqual(g["as_fixed_iso_lock_rc"], -16)
        self.assertEqual(g["as_flex_shutter_man_rc"], -16)
        self.assertEqual(g["as_cineei_lock_rc"], -16)
        self.assertEqual(g["as_angle_mutex_rc"], -16)
        self.assertEqual(g["iso_limit_auto_ebusy_rc"], -16)
        self.assertEqual(g["iso_limit_bounds_einval_rc"], -22)
        self.assertEqual(g["minss_movie_ebusy_rc"], -16)
        self.assertEqual(g["minss_sq_ebusy_rc"], -16)
        self.assertEqual(g["fx6_minss_absent_rc"], -95)
        self.assertEqual(g["non_cineei_baseiso_rc"], -16)

    def test_30_round79_r79b_guard_blocks_pillar3_dormant_lossless_hlg_sort_erofs30(self) -> None:
        g = self.summary["runs"][
            "r79b_wave65_zoom_ciz_autoslow_iso_arw_usblun_uvc_guard"
        ]["r79_telemetry"]["wave65_guard"]
        self.assertEqual(g["raw_lossless_rc"], -95)
        self.assertEqual(g["raw_lossless_l_rc"], -95)
        self.assertEqual(g["raw_lossless_m_rc"], -95)
        self.assertEqual(g["raw_lossless_s_rc"], -95)
        self.assertEqual(g["fx6_still_arw_rc"], -95)
        self.assertEqual(g["hlg_jpeg_lock_rc"], -16)
        self.assertEqual(g["hlg_raw_lock_rc"], -16)
        self.assertEqual(g["hlg_iauto_lock_rc"], -16)
        self.assertEqual(g["sort_slot1_erofs_rc"], -30)

    def test_31_round79_r79b_guard_blocks_pillar4_dual_uvc_lun_single_pd_streaming_erofs30(self) -> None:
        g = self.summary["runs"][
            "r79b_wave65_zoom_ciz_autoslow_iso_arw_usblun_uvc_guard"
        ]["r79_telemetry"]["wave65_guard"]
        self.assertEqual(g["fx3_uvc_dormant_rc"], -95)
        self.assertEqual(g["fx6_uvc_dormant_rc"], -95)
        self.assertEqual(g["micro_usb_pwr_rc"], -95)
        self.assertEqual(g["lun_single_msc_slot1_erofs_rc"], -30)
        self.assertEqual(g["mtp_slot1_erofs_rc"], -30)
        self.assertEqual(g["pd_no_fz100_ebusy_rc"], -16)
        self.assertEqual(g["dcc1_under65w_ebusy_rc"], -16)
        self.assertEqual(g["fx6_dcin_low_ebusy_rc"], -16)
        self.assertEqual(g["stream_rec_slot1_erofs_rc"], -30)
        self.assertEqual(g["hdmi_rec_slot1_erofs_rc"], -30)

    def test_32_round79_r79b_guard_blocks_macos_mds_fseventsd_p12_p2_cnflasha_and_keeps_sha256(self) -> None:
        r79b_t = self.summary["runs"][
            "r79b_wave65_zoom_ciz_autoslow_iso_arw_usblun_uvc_guard"
        ]["r79_telemetry"]
        g = r79b_t["wave65_guard"]
        self.assertEqual(r79b_t["wave65_guard_rc"], 0)
        self.assertEqual(g["null_cfg_einval_rc"], -22)
        self.assertEqual(g["live_attach_eperm_rc"], -1)
        self.assertEqual(g["slot1_mds_erofs_rc"], -30)
        self.assertEqual(g["slot1_fseventsd_erofs_rc"], -30)
        self.assertEqual(g["p12_write_blocked_rc"], -30)
        self.assertEqual(g["p2_write_blocked_rc"], -30)
        self.assertEqual(g["cnflasha_ro_blocked_rc"], -30)
        self.assertEqual(g["slot1_vault_sha256_match"], 1)
        self.assertEqual(g["usb_tx"], 0)
        self.assertEqual(g["slot1_writes"], 0)
        self.assertEqual(g["slot1_data_sector_writes"], 0)
        self.assertEqual(g["rf_tx_packets"], 0)
        self.assertEqual(g["appfw_ok"], 1)
        self.assertEqual(g["shim_elf_ok"], 1)
        self.assertEqual(g["cnflasha_writes"], 0)
        self.assertEqual(g["emmc_write_count"], 0)
        self.assertEqual(g["r79b_ok"], 1)

    def test_33_round79_r79c_clean_unmount_wave65_3tier_reset_and_16_h0_h3(self) -> None:
        ci = self.summary["runs"][
            "r79c_clean_unmount_wave65_reset_h0_h3_big6_schinese"
        ]["r79_telemetry"]["clean_unmount_wave65_h0_h3"]
        self.assertEqual(ci["stock_unmount_restored_ok"], 1)
        self.assertEqual(
            ci["camreset_resets_speeds_autoslow_minss_arw_hlg_preserves_zoomrange_ring_isolimit_sort_usb_airplane_ok"],
            1,
        )
        self.assertEqual(ci["nwreset_resets_streamrec_preserves_wave65_setup_airplane_ok"], 1)
        self.assertEqual(ci["initialize_restores_wave65_defaults_preserves_airplane_ok"], 1)
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
        self.assertEqual(ci["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(ci["emmc_write_count"], 0)
        self.assertEqual(ci["r79c_ok"], 1)

    def test_34_round79_r79a_and_r79c_gpe0_readback_big6_home_ge_300k_nonzero_pixels(self) -> None:
        for rk in (
            "r79a_zoom_ciz_autoslow_iso_arw_usblun_uvc_erofs_big6_schinese",
            "r79c_clean_unmount_wave65_reset_h0_h3_big6_schinese",
        ):
            gpe = self.summary["runs"][rk]["gpe0_readback"]
            self.assertTrue(gpe["present"], rk)
            self.assertEqual(gpe["total_pixels"], 1024 * 540, rk)
            self.assertEqual(gpe["bytes"], 1024 * 540 * 4, rk)
            self.assertGreaterEqual(gpe["nonzero_pixels"], 300000, rk)
            self.assertGreaterEqual(gpe["unique_colors"], 50, rk)

    def test_35_round79_r79a_alpha_and_composited_png_dimensions_and_size_cap_27467(self) -> None:
        self.assertEqual(self.alpha_dims, (1024, 540))
        self.assertEqual(self.comp_dims, (1024, 540))
        self.assertLessEqual(len(self.alpha_png_bytes), 27467)
        self.assertLessEqual(len(self.comp_png_bytes), 27467)
        self.assertGreater(len(self.alpha_png_bytes), 10000)
        self.assertGreater(len(self.comp_png_bytes), 10000)
        self.assertGreater(self.alpha_transparent, 100000)
        self.assertGreater(self.alpha_opaque, 100000)
        self.assertEqual(self.comp_opaque, 1024 * 540)

    def test_36_round79_r79a_png_exports_paths_sanitized_and_match_assets(self) -> None:
        pe = self.summary["runs"][
            "r79a_zoom_ciz_autoslow_iso_arw_usblun_uvc_erofs_big6_schinese"
        ]["png_exports"]
        self.assertEqual(
            pe["alpha_png"]["path"],
            "reports/2026-11-21-round79-zoom-ciz-autoslow-iso-arw-usblun-uvc-erofs-qemu/r79_arw_lossless_hlg_usblun_pd_uvc_erofs_preview.png",
        )
        self.assertEqual(
            pe["composited_png"]["path"],
            "reports/2026-11-21-round79-zoom-ciz-autoslow-iso-arw-usblun-uvc-erofs-qemu/r79_zoom_ciz_autoslow_iso_dualbase_preview.png",
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

    def test_37_round79_deterministic_payload_hash_ignoring_volatile_timing(self) -> None:
        a = copy.deepcopy(self.summary)
        b = copy.deepcopy(self.summary)
        b["runs"]["r79a_zoom_ciz_autoslow_iso_arw_usblun_uvc_erofs_big6_schinese"]["wall_elapsed_sec"] = 999.99
        b["runs"]["r79a_zoom_ciz_autoslow_iso_arw_usblun_uvc_erofs_big6_schinese"]["r79_telemetry"]["wave65_init"]["verify_us"] = 12345
        ha = hashlib.sha256(json.dumps(_strip_volatile_timing(a), sort_keys=True).encode("utf-8")).hexdigest()
        hb = hashlib.sha256(json.dumps(_strip_volatile_timing(b), sort_keys=True).encode("utf-8")).hexdigest()
        self.assertEqual(ha, hb)

    def test_38_round79_verify_us_positive_under_3_seconds_across_all_3_runs(self) -> None:
        us_a = self.summary["runs"]["r79a_zoom_ciz_autoslow_iso_arw_usblun_uvc_erofs_big6_schinese"]["r79_telemetry"]["wave65_init"]["verify_us"]
        us_b = self.summary["runs"]["r79b_wave65_zoom_ciz_autoslow_iso_arw_usblun_uvc_guard"]["r79_telemetry"]["wave65_guard"]["verify_us"]
        us_c = self.summary["runs"]["r79c_clean_unmount_wave65_reset_h0_h3_big6_schinese"]["r79_telemetry"]["clean_unmount_wave65_h0_h3"]["verify_us"]
        for us in (us_a, us_b, us_c):
            self.assertGreater(us, 0)
            self.assertLess(us, 3_000_000)

    def test_39_round79_top_colors_transparent_plus_nonzero_equals_total_pixels(self) -> None:
        for rk in (
            "r79a_zoom_ciz_autoslow_iso_arw_usblun_uvc_erofs_big6_schinese",
            "r79c_clean_unmount_wave65_reset_h0_h3_big6_schinese",
        ):
            gpe = self.summary["runs"][rk]["gpe0_readback"]
            color_map = {row["argb"]: row["pixels"] for row in gpe["top_colors"]}
            self.assertIn("0x00000000", color_map)
            self.assertEqual(color_map["0x00000000"] + gpe["nonzero_pixels"], gpe["total_pixels"])

    def test_40_round79_r79b_fast_early_exit_and_skipped_gpe0(self) -> None:
        r79b = self.summary["runs"]["r79b_wave65_zoom_ciz_autoslow_iso_arw_usblun_uvc_guard"]
        self.assertEqual(r79b["duration_budget_sec"], 35)
        self.assertGreater(r79b["wall_elapsed_sec"], 1.0)
        self.assertLess(r79b["wall_elapsed_sec"], 60.0)
        self.assertTrue(r79b["gpe0_readback"]["skipped_stock_fx3_mode"])

    def test_41_round79_faithful_invariants_preserved_across_all_3_runs(self) -> None:
        for rk, rv in self.summary["runs"].items():
            fi = rv["faithful_invariants"]
            self.assertEqual(fi["FX6_NATIVE_FAITHFUL"], 1, rk)
            self.assertEqual(fi["subst_color"], 0, rk)
            self.assertEqual(fi["subst_image"], 0, rk)
            self.assertEqual(fi["forced_render"], 0, rk)
            self.assertEqual(fi["skipped_node"], 0, rk)
            self.assertEqual(fi["lock_bypass"], 0, rk)

    def test_42_round79_all_3_runs_stage_b_manifest_count_13(self) -> None:
        for rk, rv in self.summary["runs"].items():
            self.assertEqual(rv["stage_b"]["manifest_count"], 13, rk)
            self.assertEqual(len(rv["stage_b"]["manifest_items"]), 13, rk)

    def test_43_round79_all_3_runs_prefix_counts_include_fx6_r79(self) -> None:
        r79a_pc = self.summary["runs"]["r79a_zoom_ciz_autoslow_iso_arw_usblun_uvc_erofs_big6_schinese"]["prefix_counts"]
        r79b_pc = self.summary["runs"]["r79b_wave65_zoom_ciz_autoslow_iso_arw_usblun_uvc_guard"]["prefix_counts"]
        r79c_pc = self.summary["runs"]["r79c_clean_unmount_wave65_reset_h0_h3_big6_schinese"]["prefix_counts"]
        self.assertGreater(r79a_pc["FX6_R79_"], 10)
        self.assertEqual(r79b_pc["FX6_R79_"], 3)
        self.assertGreater(r79c_pc["FX6_R79_"], 10)

    def test_44_round79_r79_meta_invariants_across_all_3_runs(self) -> None:
        for rk, rv in self.summary["runs"].items():
            m = rv["stage_b"]["r79"]
            self.assertEqual(m["milestone_round_ordinal"], 79, rk)
            self.assertEqual(m["realhw_round_ordinal"], 52, rk)
            self.assertEqual(m["total_live_runs_at_completion"], 156, rk)
            self.assertEqual(m["total_png_receipts_at_completion"], 104, rk)
            self.assertEqual(m["dormant_fx6_digital_zoom_events"], 0, rk)
            self.assertEqual(m["dormant_movie_iso_auto_min_ss_events"], 0, rk)
            self.assertEqual(m["dormant_raw_lossless_comp_events"], 0, rk)
            self.assertEqual(m["dormant_uvc_fx3_events"], 0, rk)
            self.assertEqual(m["dormant_uvc_fx6_events"], 0, rk)
            self.assertEqual(m["usb_tx"], 0, rk)
            self.assertEqual(m["slot1_writes"], 0, rk)
            self.assertEqual(m["slot1_data_sector_writes"], 0, rk)
            self.assertEqual(m["raw_firmware_bytes_leaked"], 0, rk)
            self.assertEqual(m["emmc_write_count"], 0, rk)

    def test_45_round79_sanitize_helper_redacts_host_paths_and_reserved_port(self) -> None:
        dirty = {
            "run_id": "test-run",
            "lang": "schinese",
            "r79_mode": "zoom_ciz_autoslow_iso_arw_usblun_uvc_erofs_big6",
            "kernel_version": "Linux version 4.9.337-scel+",
            "kernel_bin": "/Users/fake/secret/kernel.bin",
            "dtb_bin": "/Users/fake/secret/guest.dtb",
            "build": {"tmp_build": "/private/tmp/build-123"},
            "stage_b": {"r79": {"r79_mode": "zoom_ciz_autoslow_iso_arw_usblun_uvc_erofs_big6"}},
            "r79_telemetry": {
                "wave65_init": {"r79_init_ok": 1},
                "wave65_guard": {"r79b_ok": 1},
                "clean_unmount_wave65_h0_h3": {"r79c_ok": 1, "surfaces_h0_eq_h3": 16},
            },
            "gpe0_readback": {"nonzero_pixels": 346686},
            "png_exports": {
                "alpha_png": {
                    "path": "/Users/kafu/repo/reports/2026-11-21-round79-zoom-ciz-autoslow-iso-arw-usblun-uvc-erofs-qemu/r79_arw_lossless_hlg_usblun_pd_uvc_erofs_preview.png"
                }
            },
            "prefix_counts": {"FX6_R79_": 10},
        }
        sanitized = self.runner.sanitize_round79_summary(dirty, dirty, dirty)
        raw = json.dumps(sanitized)
        self.assertNotIn("/Users/", raw)
        self.assertNotIn("/private/tmp/", raw)
        self.assertNotIn("kernel_bin", raw)
        self.assertNotIn("dtb_bin", raw)
        self.assertIn(
            "reports/2026-11-21-round79-zoom-ciz-autoslow-iso-arw-usblun-uvc-erofs-qemu/r79_arw_lossless_hlg_usblun_pd_uvc_erofs_preview.png",
            raw,
        )

    def test_46_round79_four_modes_and_mocked_donorless_work_root_none_master_gates(self) -> None:
        # Modes 1-3: normal / FX3_CLEAN_ROOM_TEST=1 / FX3_FX6_FORCE_CLEAN_ROOM=1
        for env_overrides in (
            {},
            {"FX3_CLEAN_ROOM_TEST": "1"},
            {"FX3_FX6_FORCE_CLEAN_ROOM": "1"},
        ):
            with mock.patch.dict(os.environ, env_overrides, clear=False):
                parsed = self.runner.extract_milestones(
                    "Linux version 4.9.337-scel+\n"
                    "FX6_R79_WAVE65_INIT zoom_ciz_speed8_ok=1 autoslow6_iso_baseiso_ok=1 "
                    "arw_lossless_hlg_sort_ok=1 usblun_pd_uvc_streaming_ok=1 usb_tx=0 slot1_writes=0 r79_init_ok=1\n"
                )
                self.assertEqual(parsed["r79_telemetry"]["wave65_init"]["r79_init_ok"], 1)

        # Mode 4: mocked donorless work_root=None fallback + Master Gates 324 & 364
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
                self.assertGreaterEqual(rep324.qemu_rounds_verified, 52)
                self.assertGreaterEqual(rep324.qemu_runs_verified, 156)
                self.assertGreaterEqual(rep324.qemu_png_receipts_verified, 104)

                rep364 = evaluate_realhw_milestone364_master_gate(
                    repo_root=REPO_ROOT,
                    force_clean_room=True,
                    simulate_bench_dry_run=False,
                )
                self.assertEqual(rep364.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertTrue(rep364.all_pillars_milestone_ready)
                self.assertEqual(rep364.raw_firmware_bytes_leaked, 0)
                self.assertGreaterEqual(rep364.qemu_rounds_verified, 52)
                self.assertGreaterEqual(rep364.qemu_runs_verified, 156)
                self.assertGreaterEqual(rep364.qemu_png_receipts_verified, 104)
        finally:
            for p in added:
                if p in sys.path:
                    sys.path.remove(p)

    def test_47_round79_argparse_percent_safe_help_and_no_hardcoded_python3(self) -> None:
        for line in self.runner_src.splitlines():
            if "help=" in line and "%" in line:
                stripped = line.replace("%%", "")
                self.assertNotIn("%", stripped, f"Unescaped '%' in argparse help: {line}")
        test_src = pathlib.Path(__file__).read_text(encoding="utf-8")
        forbidden_py = "/usr/" + "bin/python3"
        self.assertNotIn(forbidden_py, self.runner_src)
        self.assertNotIn(forbidden_py, test_src)

    def test_48_round79_all_104_pngs_under_27467b_and_clean_room_safe(self) -> None:
        round_dirs = [
            d for d in (REPO_ROOT / "reports").glob("2026-??-??-round*")
            if d.is_dir() and int(d.name.split("-round")[1].split("-")[0]) >= 28
        ]
        all_pngs = sorted(p for d in round_dirs for p in d.rglob("*.png") if p.is_file())
        self.assertGreaterEqual(len(all_pngs), 104)
        for p in all_pngs:
            self.assertLessEqual(p.stat().st_size, 27467, str(p))

    def test_49_round79_cli_help_subprocess_smoke_timeout_60(self) -> None:
        res = subprocess.run(
            [sys.executable, "-B", str(CLOSURE_DIR / "build_and_run_round.py"), "--help"],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        self.assertIn("--r79-mode", res.stdout)
        self.assertIn("zoom_ciz_autoslow_iso_arw_usblun_uvc_erofs_big6", res.stdout)

    def test_50_round79_wave65_uxc_and_node_tokens_wired_in_stage_a_source(self) -> None:
        for sym in (
            "r79_lookup_wave65_menu_node",
            "r79_lookup_uxc_token",
            "_f:0x7164:Zoom Range",
            "_f:0x73f2:Optical zoom only",
            "_f:0x70e1:ClearImage Zoom",
            "_f:0x796c:Digital Zoom",
            "_f:0x6304:Zoom Lever Speed",
            "_f:0x6be7:Zoom Ring Rotate",
            "_f:0x76ee:Auto Slow Shutter",
            "_f:0x69cb:ISO Range Limit",
            "_f:0x778b:ISO AUTO Min. SS",
            "_f:0x78ce:Base ISO",
            "_f:0x6ff2:RAW File Type",
            "_f:0x6b56:Lossless Comp (dormant on FX3 7.02)",
            "_f:0x76c8:HLG Still Image",
            "_f:0x7916:Sort Recording",
            "_f:0x69a2:USB Connection Mode",
            "_f:0x6b19:USB LUN Setting",
            "_f:0x776d:Single",
            "_f:0x721e:USB Power Supply",
            "_f:0x6216:Live Stream(USB Streaming) (dormant on FX3 7.02)",
            "_f:0x79d5:Movie Rec During Streaming",
            "_f:0x6144:Rec. Media dur HDMI Output",
            "dormant:FX6_USB_STREAMING_PROCAM",
            "dormant:FX6_DIGITAL_ZOOM",
        ):
            self.assertIn(sym, self.stage_a_src)

    def test_51_round79_report_markdown_has_chinese_conclusions_links_and_fact_inference_split(self) -> None:
        self.assertIn("## 结论先行", self.r79_readme)
        self.assertIn("实测事实", self.r79_readme)
        self.assertIn("推断", self.r79_readme)
        self.assertIn("file://", self.r79_readme)
        self.assertIn("52/52", self.r79_readme)
        self.assertIn("156/156", self.r79_readme)
        self.assertIn("104/104", self.r79_readme)
        self.assertIn("r79_zoom_ciz_autoslow_iso_dualbase_preview.png", self.r79_readme)
        self.assertIn("r79_arw_lossless_hlg_usblun_pd_uvc_erofs_preview.png", self.r79_readme)

    def test_52_round79_closure_readme_documents_round79_52_rounds_156_runs_104_pngs(self) -> None:
        self.assertIn("## 79. Round 79", self.closure_readme)
        self.assertIn("52/52", self.closure_readme)
        self.assertIn("156/156", self.closure_readme)
        self.assertIn("104/104", self.closure_readme)
        self.assertIn("r79a", self.closure_readme)
        self.assertIn("r79b", self.closure_readme)
        self.assertIn("r79c", self.closure_readme)

    def test_53_round79_continuity_from_round78(self) -> None:
        self.assertEqual(self.r78_summary["round"], 78)
        self.assertEqual(self.summary["round"], self.r78_summary["round"] + 1)
        self.assertEqual(self.summary["raw_firmware_bytes_leaked"], 0)

    def test_54_round79_no_stray_temp_files_or_pyc_in_closure_dir(self) -> None:
        for bad_name in ("tmp", "scratch", ".worktrees"):
            self.assertFalse((REPO_ROOT / bad_name).exists(), bad_name)
        pyc_files = list(CLOSURE_DIR.rglob("*.pyc"))
        self.assertEqual(pyc_files, [])


if __name__ == "__main__":
    unittest.main()
