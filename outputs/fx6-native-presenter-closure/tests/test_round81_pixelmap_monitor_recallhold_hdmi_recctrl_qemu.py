#!/usr/bin/env python3
"""Offline four-mode unit tests for FX6-on-FX3 Round 81 (54/54 Real-HW Rounds R28..R81, 160th..162nd Live Runs -> 162/162 Total, 108/108 PNGs <= 27,467 B — Wave-67)."""
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
ROUND81_REPORT_DIR = (
    REPO_ROOT
    / "reports"
    / "2026-11-21-round81-pixelmap-monitor-recallhold-hdmi-recctrl-qemu"
)
WAVE67_SPEC_PATH = (
    REPO_ROOT
    / "reports"
    / "2026-11-17-global-sony-wave67-pixelmap-apr-monitor-vfadjust-recall-custom-hold-hdmi-tc-recctrl-intel"
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


def _build_overlay_for_r81(
    runner,
    parent_cpio: pathlib.Path,
    fp,
    fv,
    fb,
    fake_run,
    jit_meta: Dict[str, Any],
    work: pathlib.Path,
    r81_mode: str,
    lang: str = "schinese",
    enable_r81: bool = True,
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
            enable_r80=True,
            r80_mode="drive_focusbracket_shutter_efcs_creativelook_recoverdb_big6",
            enable_r81=enable_r81,
            r81_mode=r81_mode,
            sd_manifest_mode="valid",
            lang=lang,
            shim_bytes=b"SHIM",
        )


class TestRound81PixelMapMonitorRecallHoldHdmiRecCtrlQemu(unittest.TestCase):
    EXPECTED_RUN_KEYS = (
        "r81a_pixelmap_monitor_recallhold_hdmi_recctrl_big6_schinese",
        "r81b_wave67_pixelmap_monitor_recallhold_hdmi_recctrl_guard",
        "r81c_clean_unmount_wave67_reset_h0_h3_big6_schinese",
    )

    runner: Any
    runner_src: str
    stage_a_src: str
    shim_src: str
    wave67_spec: str
    summary_raw: str
    summary: Dict[str, Any]
    r81_readme: str
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
    launcher_r81: Optional[bytes]
    shim_r81: Optional[bytes]
    shim_r80: Optional[bytes]
    r80_summary: Dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = _load_closure_module("fx6_brr_r81_cached", "build_and_run_round.py")
        cls.runner_src = (CLOSURE_DIR / "build_and_run_round.py").read_text(encoding="utf-8")
        cls.stage_a_src = (CLOSURE_DIR / "fx6-stage-a-verify.c").read_text(encoding="utf-8")
        cls.shim_src = (CLOSURE_DIR / "libgrm-fbinit9.c").read_text(encoding="utf-8")
        cls.wave67_spec = WAVE67_SPEC_PATH.read_text(encoding="utf-8")
        cls.summary_raw = (ROUND81_REPORT_DIR / "summary.json").read_text(encoding="utf-8")
        cls.summary = json.loads(cls.summary_raw)
        cls.r81_readme = (ROUND81_REPORT_DIR / "README.md").read_text(encoding="utf-8")
        cls.closure_readme = (CLOSURE_DIR / "README.md").read_text(encoding="utf-8")

        alpha_p = ROUND81_REPORT_DIR / "r81_hdmi_recmedia_tc_recctrl_24p_sdi_slot1_erofs_preview.png"
        comp_p = ROUND81_REPORT_DIR / "r81_pixelmap_apr_monitor3_evf_debunk_recallhold11_preview.png"
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
            cls.ov_a = _build_overlay_for_r81(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wa", "pixelmap_monitor_recallhold_hdmi_recctrl_big6", lang="schinese",
            )
            cls.ov_b = _build_overlay_for_r81(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wb", "wave67_pixelmap_monitor_recallhold_hdmi_recctrl_guard", lang="en",
            )
            cls.ov_c = _build_overlay_for_r81(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "wc", "clean_unmount_wave67_reset_h0_h3_big6", lang="schinese",
            )
            cls.ov_off = _build_overlay_for_r81(
                cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                tpath / "woff", "pixelmap_monitor_recallhold_hdmi_recctrl_big6", enable_r81=False,
            )
            cls.invalid_mode_raised = False
            try:
                _build_overlay_for_r81(
                    cls.runner, parent_cpio, fp, fv, fb, fake_run, jit_meta,
                    tpath / "wbad", "invalid_r81_mode",
                )
            except ValueError:
                cls.invalid_mode_raised = True

            zig_bin = shutil.which("zig") or (
                str(cls.runner.ZIG) if cls.runner.ZIG.is_file() else None
            )
            if zig_bin is not None:
                verify_r81_out = tpath / "fx6-stage-a-verify-r81"
                shim_r81_out = tpath / "libgrm-fbinit9-r81.so"
                shim_r80_out = tpath / "libgrm-fbinit9-r80.so"
                for cmd in (
                    [
                        zig_bin, "cc", "-target", "aarch64-linux-gnu.2.25", "-O0",
                        str(CLOSURE_DIR / "fx6-stage-a-verify.c"),
                        "-ldl", "-lpthread", "-o", str(verify_r81_out),
                    ],
                    [
                        zig_bin, "cc", "-target", "aarch64-linux-gnu.2.25", "-O0",
                        "-shared", "-fPIC", "-DFX6_ROUND=81",
                        str(CLOSURE_DIR / "libgrm-fbinit9.c"),
                        "-ldl", "-lpthread", "-o", str(shim_r81_out),
                    ],
                    [
                        zig_bin, "cc", "-target", "aarch64-linux-gnu.2.25", "-O0",
                        "-shared", "-fPIC", "-DFX6_ROUND=80",
                        str(CLOSURE_DIR / "libgrm-fbinit9.c"),
                        "-ldl", "-lpthread", "-o", str(shim_r80_out),
                    ],
                ):
                    cls.runner.subprocess.run(cmd, check=True, timeout=120)
                cls.launcher_r81 = verify_r81_out.read_bytes()
                cls.shim_r81 = shim_r81_out.read_bytes()
                cls.shim_r80 = shim_r80_out.read_bytes()
            else:
                cls.launcher_r81 = None
                cls.shim_r81 = None
                cls.shim_r80 = None

        cls.r80_summary = json.loads(
            (
                REPO_ROOT
                / "reports"
                / "2026-11-21-round80-milestone-drive-focusbracket-shutter-efcs-creativelook-recoverdb-qemu"
                / "summary.json"
            ).read_text(encoding="utf-8")
        )

    def test_01_wave67_global_spec_present_and_covers_all_4_pillars(self) -> None:
        self.assertTrue(WAVE67_SPEC_PATH.is_file())
        for needle in (
            "Auto Pixel Mapping",
            "Pixel Mapping",
            "pixel_mappinng",
            "excuted_status",
            "INFRA_NOTIFY_BATTERY_CHECK_FOR_PIXEL_MAPPING",
            "vdf_set_shutter_mute_by_pixel_mapping",
            "APR",
            "Setup -> [Monitor]",
            "Monitor Brightness",
            "Display Quality",
            "Monitor Flip Direction",
            "Finder/Monitor Sel.",
            "VF Setting",
            "VF Adjust",
            "Recall Custom hold 1",
            "is_checked_recall_custom_hold",
            "CAMSET",
            "Push AGC",
            "Push Auto Iris",
            "Rec. Media dur HDMI Output",
            "Time Code Output",
            "REC Control",
            "24.00p",
            "ctrl_for_hmdi",
            "outpute",
            "24p/60p Output",
            "4240",
        ):
            self.assertIn(needle, self.wave67_spec)

    def test_02_round81_summary_schema_milestone_and_zero_leaks(self) -> None:
        self.assertNotIn("/Users/", self.summary_raw)
        self.assertNotIn("/private/tmp/", self.summary_raw)
        self.assertNotIn("/tmp/round81", self.summary_raw)
        self.assertEqual(
            self.summary["schema"],
            "fx6-on-fx3-round81-pixelmap-monitor-recallhold-hdmi-recctrl-qemu-v1",
        )
        self.assertEqual(self.summary["round"], 81)
        self.assertEqual(self.summary["overall_status"], "PASS")
        self.assertIs(self.summary["synthetic_fallback"], False)
        self.assertIn("54/54 Real-HW Rounds", self.summary["milestone"])
        self.assertIn("162/162 Live Runs", self.summary["milestone"])
        self.assertIn("108/108 PNGs <= 27,467 B", self.summary["milestone"])
        self.assertEqual(self.summary["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(self.summary["usb_tx"], 0)
        self.assertEqual(self.summary["usb_tx_bytes"], 0)
        self.assertEqual(self.summary["emmc_writes"], 0)
        self.assertEqual(self.summary["slot1_writes"], 0)
        self.assertEqual(self.summary["slot1_data_sector_writes"], 0)
        self.assertEqual(tuple(self.summary["runs"].keys()), self.EXPECTED_RUN_KEYS)

    def test_03_round81_hardware_safety_locks_all_false_and_zero(self) -> None:
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

    def test_04_round81_cli_accepts_round81_and_all_3_r81_modes(self) -> None:
        self.assertIn(", 77, 78, 79, 80, 81]", self.runner_src)
        for mode in (
            "pixelmap_monitor_recallhold_hdmi_recctrl_big6",
            "wave67_pixelmap_monitor_recallhold_hdmi_recctrl_guard",
            "clean_unmount_wave67_reset_h0_h3_big6",
        ):
            self.assertIn(mode, self.runner_src)

    def test_05_round81_overlay_rejects_invalid_r81_mode(self) -> None:
        self.assertTrue(self.invalid_mode_raised)

    def test_06_round81_overlay_r81a_injects_etc_fx6_stage_r81_and_appfw_launch(self) -> None:
        replacements, additions, meta = self.ov_a
        self.assertTrue(meta["r81_enabled"])
        self.assertIn("etc/fx6_stage_r81", additions)
        self.assertIn("etc/fx6_r81_libjit.so", additions)
        r81_cfg = additions["etc/fx6_stage_r81"][0].decode("utf-8")
        self.assertIn("stage_r81=1", r81_cfg)
        self.assertIn("r81_mode=pixelmap_monitor_recallhold_hdmi_recctrl_big6", r81_cfg)
        self.assertIn("milestone_54th_realhw_162nd_live_108_pngs=1", r81_cfg)
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("/usr/bin/appfw-launch", init_txt)
        self.assertNotIn("--r81-wave67-guard", init_txt)

    def test_07_round81_overlay_r81b_injects_early_guard_probe_and_poweroff(self) -> None:
        replacements, _, meta = self.ov_b
        self.assertEqual(
            meta["r81"]["r81_mode"],
            "wave67_pixelmap_monitor_recallhold_hdmi_recctrl_guard",
        )
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("--r81-wave67-guard", init_txt)
        self.assertIn("FX6_R81_WAVE67_GUARD_RC=", init_txt)
        self.assertIn("FX6_R81_WAVE67_GUARD_EXIT", init_txt)
        self.assertIn("poweroff -f", init_txt)

    def test_08_round81_overlay_r81c_integrated_runs_stage_b_big6(self) -> None:
        replacements, additions, meta = self.ov_c
        self.assertEqual(meta["r81"]["r81_mode"], "clean_unmount_wave67_reset_h0_h3_big6")
        r81_cfg = additions["etc/fx6_stage_r81"][0].decode("utf-8")
        self.assertIn("r81_mode=clean_unmount_wave67_reset_h0_h3_big6", r81_cfg)
        init_txt = replacements["init"].decode("utf-8")
        self.assertIn("/usr/bin/appfw-launch", init_txt)
        self.assertNotIn("--r81-wave67-guard", init_txt)

    def test_09_round81_overlay_disabled_when_enable_r81_false(self) -> None:
        _, additions, meta = self.ov_off
        self.assertFalse(meta["r81_enabled"])
        self.assertNotIn("etc/fx6_stage_r81", additions)
        self.assertNotIn("etc/fx6_r81_libjit.so", additions)
        self.assertNotIn("r81", meta)

    def test_10_round81_stage_a_c_source_contains_all_wave67_probes(self) -> None:
        for sym in (
            "setup_r81_pixelmap_monitor_recallhold_hdmi_recctrl_probe",
            "run_r81_wave67_guard_probe",
            "run_r81_clean_unmount_wave67_h0_h3_probe",
            "r81_wave67_initialize",
            "r81_wave67_zero_init",
            "r81_wave67_camera_settings_reset",
            "r81_wave67_reset_network_settings",
            "r81_eval_pixel_mapping_and_apr",
            "r81_eval_monitor_and_evf_debunk",
            "r81_eval_hold_keys_and_recall_custom_hold",
            "r81_eval_external_output_hdmi_sdi_and_slot1",
            "FX6_R81_WAVE67_INIT",
            "FX6_R81_WAVE67_GUARD",
            "FX6_R81_CLEAN_UNMOUNT_WAVE67_H0_H3",
            "--r81-wave67-guard",
            "--r81-clean-unmount-wave67-h0-h3",
            "/etc/fx6_stage_r81",
        ):
            self.assertIn(sym, self.stage_a_src)

    def test_11_round81_shim_c_source_contains_r81_guarded_bridges(self) -> None:
        self.assertIn("#if FX6_ROUND >= 81", self.shim_src)
        for sym in (
            "FX6_R81_PIXELMAP_APR_BRIDGE",
            "FX6_R81_MONITOR3_EVF_DEBUNK_BRIDGE",
            "FX6_R81_RECALLHOLD11_PUSHAF_BRIDGE",
            "FX6_R81_HDMI_TC_RECCTRL_SDI_EROFS_BRIDGE",
            "FX6_R81_LANG_TELEMETRY",
            "FX6_STAGE_B_R81_BRIDGE",
        ):
            self.assertIn(sym, self.shim_src)

    def test_12_round81_compile_launcher_and_shim_aarch64_elf_symbols(self) -> None:
        if self.launcher_r81 is None or self.shim_r81 is None:
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertEqual(self.launcher_r81[:4], b"\x7fELF")
        self.assertEqual(self.shim_r81[:4], b"\x7fELF")
        self.assertEqual(struct.unpack_from("<H", self.shim_r81, 18)[0], 183)
        self.assertIn(b"FX6_R81_PIXELMAP_APR_BRIDGE", self.shim_r81)
        self.assertIn(b"FX6_R81_MONITOR3_EVF_DEBUNK_BRIDGE", self.shim_r81)
        self.assertIn(b"FX6_R81_RECALLHOLD11_PUSHAF_BRIDGE", self.shim_r81)
        self.assertIn(b"FX6_R81_HDMI_TC_RECCTRL_SDI_EROFS_BRIDGE", self.shim_r81)

    def test_13_round81_shim_round80_backward_compat_excludes_r81_bridges(self) -> None:
        if self.shim_r80 is None:
            self.skipTest("Clean-room fallback without local zig binary")
        self.assertIn(b"FX6_R80_DRIVE_10FPS_FOCUSBRACKET_BRIDGE", self.shim_r80)
        self.assertNotIn(b"FX6_R81_PIXELMAP_APR_BRIDGE", self.shim_r80)

    def test_14_round81_parse_log_extracts_all_r81_prefixes_and_rc(self) -> None:
        serial_text = "\n".join(
            [
                "Linux version 4.9.337-scel+ (sony@fx3)",
                "FX6_R81_WAVE67_INIT fx3_wave67_nodes_ok=1 uxc_tokens_ok=1 pixelmap_apr_ok=1 monitor3_evf_debunk_ok=1 recallhold11_pushaf_ok=1 hdmi_tc_recctrl_sdi_erofs_ok=1 usb_tx=0 slot1_writes=0 emmc_write_count=0 r81_init_ok=1",
                "FX6_R81_PIXELMAP_APR_BRIDGE auto_pixelmap_anti_reset_silent_target_ok=1 manual_pixelmap_dark_batt_reboot_ok=1 fx6_apr_zero_abb_ok=1 pixelmap_apr_ok=1 r81_bridge_ok=1",
                "FX6_R81_MONITOR3_EVF_DEBUNK_BRIDGE monitor_3item_group_anti_reset_ok=1 dormant_evf_4items_blocked_ok=1 fx6_vf_setting_adjust_mirror_diff_ok=1 monitor3_evf_debunk_ok=1",
                "FX6_R81_RECALLHOLD11_PUSHAF_BRIDGE hold_keys_and_recallhold_still_pasm_11bit_ok=1 recallhold_zero_wb_and_movie_blocked_ok=1 fx6_push_af_agc_iris_highlow_debunk_ok=1 recallhold11_pushaf_ok=1",
                "FX6_R81_HDMI_TC_RECCTRL_SDI_EROFS_BRIDGE hdmi_recmedia_tc_recctrl_24p_ok=1 dormant_4k2k_24p60p_blocked_ok=1 fx6_sdi_hdmi_dual_matrix_ok=1 slot1_hdmi_camset_erofs30_ok=1 hdmi_tc_recctrl_sdi_erofs_ok=1 usb_tx=0 slot1_writes=0",
                "FX6_R81_LANG_TELEMETRY lang=schinese font_bank=23 str_bank=19 milestone_54th_realhw_162nd_live_108_pngs=1 usb_tx=0 slot1_writes=0 r81_bridge_ok=1",
                "FX6_STAGE_B_R81_BRIDGE round=81 faithful=1 nop_count=0 milestone_54th_realhw_162nd_live_108_pngs=1 usb_tx=0 slot1_writes=0 emmc_write_count=0",
                "FX6_R81_WAVE67_GUARD fx6_abb_dormant_rc=-95 evf_group_rc=-95 recall_wb_bit_rc=-95 hdmi_4k2k_rc=-95 slot1_hdmi_rec_erofs_rc=-30 live_attach_eperm_rc=-1 r81b_ok=1",
                "FX6_R81_WAVE67_GUARD_RC=0",
                "FX6_R81_CLEAN_UNMOUNT_WAVE67_H0_H3 stock_unmount_restored_ok=1 surfaces_h0_eq_h3=16 usb_tx=0 slot1_writes=0 r81c_ok=1",
            ]
        ) + "\n"
        parsed = self.runner.extract_milestones(serial_text)
        r81_t = parsed["r81_telemetry"]
        self.assertEqual(r81_t["wave67_guard_rc"], 0)
        self.assertEqual(r81_t["wave67_init"]["pixelmap_apr_ok"], 1)
        self.assertEqual(r81_t["pixelmap_apr_bridge"]["pixelmap_apr_ok"], 1)
        self.assertEqual(r81_t["monitor3_evf_debunk_bridge"]["monitor3_evf_debunk_ok"], 1)
        self.assertEqual(r81_t["recallhold11_pushaf_bridge"]["recallhold11_pushaf_ok"], 1)
        self.assertEqual(r81_t["hdmi_tc_recctrl_sdi_erofs_bridge"]["hdmi_tc_recctrl_sdi_erofs_ok"], 1)
        self.assertEqual(r81_t["lang_telemetry"]["milestone_54th_realhw_162nd_live_108_pngs"], 1)
        self.assertEqual(r81_t["stage_b_bridge"]["round"], 81)
        self.assertEqual(r81_t["wave67_guard"]["r81b_ok"], 1)
        self.assertEqual(r81_t["clean_unmount_wave67_h0_h3"]["surfaces_h0_eq_h3"], 16)
        self.assertEqual(parsed["prefix_counts"]["FX6_R81_"], 9)

    def test_15_round81_parse_log_defaults_when_no_r81_lines_present(self) -> None:
        parsed = self.runner.extract_milestones("Linux version 4.9.337-scel+\n")
        self.assertIsNone(parsed["r81_telemetry"])
        self.assertEqual(parsed["prefix_counts"].get("FX6_R81_", 0), 0)

    def test_16_round81_runner_preserves_r80_prefix_and_uses_r81_stage_label(self) -> None:
        self.assertIn('if args.round >= 80:\n        tmp_prefix = "fx6-r80"', self.runner_src)
        self.assertIn('if args.round >= 81:\n        tmp_prefix = "fx6-r81"', self.runner_src)
        self.assertIn(
            "54RealHw162ndLiveWave67PixelMapMonitorRecallHoldHdmiRecCtrlSdiErofs30",
            self.runner_src,
        )

    def test_17_round81_runner_portability_and_sanitizer_helper(self) -> None:
        self.assertIn('shutil.which("zig")', self.runner_src)
        self.assertIn("FX6_SCRATCH_DIR", self.runner_src)
        self.assertIn("def sanitize_round81_summary(", self.runner_src)
        self.assertNotIn("/usr/" + "bin/python3", self.runner_src)

    def test_18_round81_summary_json_zero_host_path_scratch_and_elapsed_leaks(self) -> None:
        for forbidden in (
            "/Users/",
            "/private/tmp/",
            "/var/folders/",
            "/tmp/round81",
            "work/_scratch/",
            "work/_tests/",
            "elapsed_seconds",
            "elapsed_ms",
            ":87" + "68",
        ):
            self.assertNotIn(forbidden, self.summary_raw)

    def test_19_round81_summary_audit_block_confirms_54_rounds_162_runs_108_pngs(self) -> None:
        audit = self.summary["r81_pixelmap_monitor_recallhold_hdmi_recctrl_audit"]
        self.assertEqual(audit["round"], 81)
        self.assertGreaterEqual(audit["realhw_rounds_count"], 54)
        self.assertGreaterEqual(audit["total_live_runs"], 162)
        self.assertGreaterEqual(audit["total_png_receipts"], 108)
        self.assertGreaterEqual(audit["milestone324_qemu_rounds"], 54)
        self.assertGreaterEqual(audit["milestone324_qemu_runs"], 162)
        self.assertGreaterEqual(audit["milestone324_png_receipts"], 108)
        self.assertGreaterEqual(audit["milestone364_qemu_rounds"], 54)
        self.assertGreaterEqual(audit["milestone364_qemu_runs"], 162)
        self.assertGreaterEqual(audit["milestone364_png_receipts"], 108)
        self.assertGreaterEqual(audit["milestone375_qemu_rounds"], 54)
        self.assertGreaterEqual(audit["milestone375_qemu_runs"], 162)
        self.assertGreaterEqual(audit["milestone375_png_receipts"], 108)
        self.assertEqual(audit["total_runs"], 3)
        negative_keys = {
            "fx3_finder_monitor_group_present",
            "fx3_evf_4items_exposed",
            "fx6_abb_menu_exposed",
            "fx6_vf_4subitems_exposed",
            "fx3_recall_custom_hold_movie_supported",
            "fx3_recall_custom_hold_wb_bit_present",
            "fx6_high_low_key_exposed",
            "fx3_hdmi_4k_2k_output_exposed",
            "fx3_hdmi_24p_60p_output_exposed",
            "fx3_sdi_port_present",
        }
        for nk in negative_keys:
            self.assertIs(audit[nk], False, nk)
        for k, v in audit.items():
            if isinstance(v, bool) and k not in negative_keys:
                self.assertTrue(v, f"Expected audit boolean {k} to be True")

    def test_20_round81_all_3_runs_present_with_kernel_4_9_337_and_zero_crashes_writes(self) -> None:
        runs = self.summary["runs"]
        self.assertEqual(list(runs.keys()), list(self.EXPECTED_RUN_KEYS))
        for rk, rv in runs.items():
            self.assertEqual(rv["round"], 81, rk)
            self.assertIn("4.9.337-scel+", rv["kernel_version"], rk)
            self.assertEqual(rv["nop_count"], 0, rk)
            self.assertEqual(rv["crashes"], 0, rk)
            self.assertEqual(rv["emmc_write_count"], 0, rk)
            self.assertGreater(rv["wall_elapsed_sec"], 0.0, rk)

    def test_21_round81_r81a_pillar_a_pixelmap_autopixelmap_and_fx6_apr_zero_abb(self) -> None:
        init_t = self.summary["runs"][
            "r81a_pixelmap_monitor_recallhold_hdmi_recctrl_big6_schinese"
        ]["r81_telemetry"]["wave67_init"]
        self.assertEqual(init_t["fx3_wave67_nodes_ok"], 1)
        self.assertEqual(init_t["uxc_tokens_ok"], 1)
        self.assertEqual(init_t["pixelmap_apr_ok"], 1)
        self.assertEqual(init_t["pm_lowbatt_rc"], -11)
        self.assertEqual(init_t["pm_uncapped_rc"], -16)
        self.assertEqual(init_t["fx6_abb_dormant_rc"], -95)
        self.assertEqual(init_t["dormant_fx6_abb_events"], 0)

    def test_22_round81_r81a_pillar_b_monitor3_group_and_4_dormant_evf_debunk(self) -> None:
        init_t = self.summary["runs"][
            "r81a_pixelmap_monitor_recallhold_hdmi_recctrl_big6_schinese"
        ]["r81_telemetry"]["wave67_init"]
        self.assertEqual(init_t["monitor3_evf_debunk_ok"], 1)
        self.assertEqual(init_t["mon_thermal_lock_rc"], -16)
        self.assertEqual(init_t["evf_group_debunk_rc"], -95)
        self.assertEqual(init_t["evf_sel_dormant_rc"], -95)
        self.assertEqual(init_t["evf_bright_dormant_rc"], -95)
        self.assertEqual(init_t["evf_ctemp_dormant_rc"], -95)
        self.assertEqual(init_t["evf_fps_dormant_rc"], -95)
        self.assertEqual(init_t["fx6_vf_4sub_debunk_rc"], -95)
        self.assertEqual(init_t["dormant_fx3_evf_events"], 0)
        self.assertEqual(init_t["dormant_fx6_vf_4subitems_events"], 0)

    def test_23_round81_r81a_pillar_c_hold_keys_and_recall_custom_hold_11bit_zero_wb(self) -> None:
        init_t = self.summary["runs"][
            "r81a_pixelmap_monitor_recallhold_hdmi_recctrl_big6_schinese"
        ]["r81_telemetry"]["wave67_init"]
        self.assertEqual(init_t["recallhold11_pushaf_ok"], 1)
        self.assertEqual(init_t["recall_movie_rc"], -95)
        self.assertEqual(init_t["recall_sq_rc"], -95)
        self.assertEqual(init_t["recall_iauto_rc"], -95)
        self.assertEqual(init_t["recall_wb_debunk_rc"], -95)
        self.assertEqual(init_t["recall_camset_slot1_erofs_rc"], -30)
        self.assertEqual(init_t["fx6_highlow_dormant_rc"], -95)
        self.assertEqual(init_t["dormant_recallhold_movie_events"], 0)
        self.assertEqual(init_t["dormant_recallhold_wb_events"], 0)
        self.assertEqual(init_t["dormant_fx6_high_low_key_events"], 0)

    def test_24_round81_r81a_pillar_d_hdmi_recmedia_tc_recctrl_sdi_and_slot1_erofs30(self) -> None:
        init_t = self.summary["runs"][
            "r81a_pixelmap_monitor_recallhold_hdmi_recctrl_big6_schinese"
        ]["r81_telemetry"]["wave67_init"]
        self.assertEqual(init_t["hdmi_tc_recctrl_sdi_erofs_ok"], 1)
        self.assertEqual(init_t["rec_ctrl_no_tc_rc"], -16)
        self.assertEqual(init_t["hdmi_4k2k_dormant_rc"], -95)
        self.assertEqual(init_t["hdmi_24p60p_dormant_rc"], -95)
        self.assertEqual(init_t["slot1_hdmi_recmedia_erofs_rc"], -30)
        self.assertEqual(init_t["fx6_raw_hdmi_sdi1080_rc"], -16)
        self.assertEqual(init_t["fx6_sq_gt60_hdmi1080_rc"], -16)
        self.assertEqual(init_t["slot1_vfs_m4root_erofs_rc"], -30)
        self.assertEqual(init_t["slot1_vfs_camset_erofs_rc"], -30)
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
        self.assertEqual(init_t["r81_init_ok"], 1)

    def test_25_round81_r81a_stage_b_schinese_lang_telemetry_and_bridge(self) -> None:
        r81a_t = self.summary["runs"][
            "r81a_pixelmap_monitor_recallhold_hdmi_recctrl_big6_schinese"
        ]["r81_telemetry"]
        lt = r81a_t["lang_telemetry"]
        self.assertEqual(lt["lang"], "schinese")
        self.assertEqual(lt["bk4_lang_id"], "0x02cf019c")
        self.assertEqual(lt["bk4_lang_val"], "0x19")
        self.assertEqual(lt["lang_enum"], "0x2b45_CHINESE_SIMPLIFIED")
        self.assertEqual(lt["font_bank"], 23)
        self.assertEqual(lt["str_bank"], 19)
        self.assertEqual(lt["gpe_fb"], 0)
        self.assertEqual(lt["milestone_54th_realhw_162nd_live_108_pngs"], 1)
        self.assertEqual(lt["usb_tx"], 0)
        self.assertEqual(lt["slot1_writes"], 0)
        self.assertEqual(lt["raw_firmware_bytes_leaked"], 0)

        sb = r81a_t["stage_b_bridge"]
        self.assertEqual(sb["round"], 81)
        self.assertEqual(sb["faithful"], 1)
        self.assertEqual(sb["nop_count"], 0)
        self.assertEqual(sb["pixelmap_apr_zero_abb_ok"], 1)
        self.assertEqual(sb["monitor3_dormant_evf4_vfadjust_ok"], 1)
        self.assertEqual(sb["recallhold11_still_pasm_zero_wb_pushaf_ok"], 1)
        self.assertEqual(sb["hdmi_recmedia_tc_recctrl_24p_sdi_slot1_erofs30_ok"], 1)
        self.assertEqual(sb["milestone_54th_realhw_162nd_live_108_pngs"], 1)

    def test_26_round81_r81a_stage_b_4_pillar_bridges_verified(self) -> None:
        r81a_t = self.summary["runs"][
            "r81a_pixelmap_monitor_recallhold_hdmi_recctrl_big6_schinese"
        ]["r81_telemetry"]
        pb1 = r81a_t["pixelmap_apr_bridge"]
        self.assertEqual(pb1["auto_pixelmap_anti_reset_silent_target_ok"], 1)
        self.assertEqual(pb1["manual_pixelmap_dark_batt_reboot_ok"], 1)
        self.assertEqual(pb1["fx6_apr_zero_abb_ok"], 1)
        self.assertEqual(pb1["pixelmap_apr_ok"], 1)
        self.assertEqual(pb1["dormant_fx6_abb_events"], 0)
        self.assertEqual(pb1["r81_bridge_ok"], 1)

        pb2 = r81a_t["monitor3_evf_debunk_bridge"]
        self.assertEqual(pb2["monitor_3item_group_anti_reset_ok"], 1)
        self.assertEqual(pb2["dormant_evf_4items_blocked_ok"], 1)
        self.assertEqual(pb2["fx6_vf_setting_adjust_mirror_diff_ok"], 1)
        self.assertEqual(pb2["monitor3_evf_debunk_ok"], 1)
        self.assertEqual(pb2["dormant_fx3_evf_events"], 0)
        self.assertEqual(pb2["dormant_fx6_vf_4subitems_events"], 0)

        pb3 = r81a_t["recallhold11_pushaf_bridge"]
        self.assertEqual(pb3["hold_keys_and_recallhold_still_pasm_11bit_ok"], 1)
        self.assertEqual(pb3["recallhold_zero_wb_and_movie_blocked_ok"], 1)
        self.assertEqual(pb3["fx6_push_af_agc_iris_highlow_debunk_ok"], 1)
        self.assertEqual(pb3["recallhold11_pushaf_ok"], 1)
        self.assertEqual(pb3["dormant_recallhold_movie_events"], 0)
        self.assertEqual(pb3["dormant_recallhold_wb_events"], 0)
        self.assertEqual(pb3["dormant_fx6_high_low_key_events"], 0)

        pb4 = r81a_t["hdmi_tc_recctrl_sdi_erofs_bridge"]
        self.assertEqual(pb4["hdmi_recmedia_tc_recctrl_24p_ok"], 1)
        self.assertEqual(pb4["dormant_4k2k_24p60p_blocked_ok"], 1)
        self.assertEqual(pb4["fx6_sdi_hdmi_dual_matrix_ok"], 1)
        self.assertEqual(pb4["slot1_hdmi_camset_erofs30_ok"], 1)
        self.assertEqual(pb4["hdmi_tc_recctrl_sdi_erofs_ok"], 1)
        self.assertEqual(pb4["dormant_hdmi_4k2k_events"], 0)
        self.assertEqual(pb4["dormant_hdmi_24p60p_events"], 0)
        self.assertEqual(pb4["usb_tx"], 0)
        self.assertEqual(pb4["slot1_writes"], 0)
        self.assertEqual(pb4["slot1_data_sector_writes"], 0)
        self.assertEqual(pb4["slot1_avf_info_mutated"], 0)

    def test_27_round81_r81a_realhw_mechanisms_verified_block_populated(self) -> None:
        rmv = self.summary["realhw_mechanisms_verified"]
        for key in (
            "wave67_pixelmap_monitor_recallhold_hdmi_recctrl_init",
            "pixelmap_apr_stage_b_bridge",
            "monitor3_evf_debunk_stage_b_bridge",
            "recallhold11_pushaf_stage_b_bridge",
            "hdmi_tc_recctrl_sdi_erofs_stage_b_bridge",
            "wave67_fail_closed_guard",
            "clean_unmount_wave67_reset_and_16_h0_h3",
        ):
            self.assertIn(key, rmv)
            self.assertTrue(bool(rmv[key]), key)

    def test_28_round81_r81b_guard_blocks_pillar_a_pixelmap_apr_and_dormant_abb(self) -> None:
        g = self.summary["runs"][
            "r81b_wave67_pixelmap_monitor_recallhold_hdmi_recctrl_guard"
        ]["r81_telemetry"]["wave67_guard"]
        self.assertEqual(g["fx3_pm_lowbatt_rc"], -11)
        self.assertEqual(g["fx3_pm_uncapped_rc"], -16)
        self.assertEqual(g["fx3_abb_dormant_rc"], -95)
        self.assertEqual(g["fx6_abb_dormant_rc"], -95)
        self.assertEqual(g["fx6_apr_no_cloth_rc"], -16)
        self.assertEqual(g["fx6_apr_bad_temp_rc"], -11)

    def test_29_round81_r81b_guard_blocks_pillar_b_evf_4items_thermal_and_fx6_vf_4sub(self) -> None:
        g = self.summary["runs"][
            "r81b_wave67_pixelmap_monitor_recallhold_hdmi_recctrl_guard"
        ]["r81_telemetry"]["wave67_guard"]
        self.assertEqual(g["evf_group_rc"], -95)
        self.assertEqual(g["evf_sel_rc"], -95)
        self.assertEqual(g["evf_bright_rc"], -95)
        self.assertEqual(g["evf_ctemp_rc"], -95)
        self.assertEqual(g["evf_fps_rc"], -95)
        self.assertEqual(g["mon_bright_oob_rc"], -22)
        self.assertEqual(g["mon_disp_qual_heat_rc"], -16)
        self.assertEqual(g["fx6_vf_4sub_rc"], -95)
        self.assertEqual(g["fx6_vf_unconn_rc"], -19)
        self.assertEqual(g["fx6_vf_bright_oob_rc"], -22)

    def test_30_round81_r81b_guard_blocks_pillar_c_recallhold_movie_wb_and_fx6_push(self) -> None:
        g = self.summary["runs"][
            "r81b_wave67_pixelmap_monitor_recallhold_hdmi_recctrl_guard"
        ]["r81_telemetry"]["wave67_guard"]
        self.assertEqual(g["eye_af_sq_rc"], -16)
        self.assertEqual(g["track_movie_rc"], -95)
        self.assertEqual(g["track_non_afc_rc"], -16)
        self.assertEqual(g["recall_movie_rc"], -95)
        self.assertEqual(g["recall_sq_rc"], -95)
        self.assertEqual(g["recall_iauto_rc"], -95)
        self.assertEqual(g["recall_wb_bit_rc"], -95)
        self.assertEqual(g["recall_selftimer_rc"], -16)
        self.assertEqual(g["recall_camset_slot1_rc"], -30)
        self.assertEqual(g["fx6_recall_rc"], -95)
        self.assertEqual(g["fx6_push_af_desq_rc"], -16)
        self.assertEqual(g["fx6_push_agc_cineei_rc"], -16)
        self.assertEqual(g["fx6_push_agc_bokeh_rc"], -16)
        self.assertEqual(g["fx6_push_iris_manual_rc"], -16)
        self.assertEqual(g["fx6_push_iris_bokeh_rc"], -16)
        self.assertEqual(g["fx6_highlow_rc"], -95)

    def test_31_round81_r81b_guard_blocks_pillar_d_hdmi_4k2k_24p60p_tc_sdi_and_slot1(self) -> None:
        g = self.summary["runs"][
            "r81b_wave67_pixelmap_monitor_recallhold_hdmi_recctrl_guard"
        ]["r81_telemetry"]["wave67_guard"]
        self.assertEqual(g["fx3_sdi_port_rc"], -95)
        self.assertEqual(g["hdmi_4k2k_rc"], -95)
        self.assertEqual(g["hdmi_24p60p_rc"], -95)
        self.assertEqual(g["sq_hdmi_only_off_rc"], -16)
        self.assertEqual(g["sq_raw_hdmi_rc"], -16)
        self.assertEqual(g["sq_tc_out_rc"], -16)
        self.assertEqual(g["rec_ctrl_no_tc_rc"], -16)
        self.assertEqual(g["rec_ctrl_incompat_rc"], -16)
        self.assertEqual(g["slot1_hdmi_rec_erofs_rc"], -30)
        self.assertEqual(g["fx6_raw_hdmi_sdi4k_rc"], -16)
        self.assertEqual(g["fx6_sq_gt60_hdmi4k_rc"], -16)
        self.assertEqual(g["fx6_rec_ctrl_no_tc_rc"], -16)
        self.assertEqual(g["fx6_parallel_nocard_rc"], -2)
        self.assertEqual(g["fx6_parallel_slot1_erofs_rc"], -30)

    def test_32_round81_r81b_guard_blocks_vfs_m4root_avf_camset_p12_p2_cnflasha(self) -> None:
        r81b_t = self.summary["runs"][
            "r81b_wave67_pixelmap_monitor_recallhold_hdmi_recctrl_guard"
        ]["r81_telemetry"]
        g = r81b_t["wave67_guard"]
        self.assertEqual(r81b_t["wave67_guard_rc"], 0)
        self.assertEqual(g["null_cfg_einval_rc"], -22)
        self.assertEqual(g["live_attach_eperm_rc"], -1)
        self.assertEqual(g["slot1_m4root_erofs_rc"], -30)
        self.assertEqual(g["slot1_avf_erofs_rc"], -30)
        self.assertEqual(g["slot1_camset_vfs_erofs_rc"], -30)
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
        self.assertEqual(g["r81b_ok"], 1)

    def test_33_round81_r81c_clean_unmount_wave67_3tier_reset_and_16_h0_h3(self) -> None:
        ci = self.summary["runs"][
            "r81c_clean_unmount_wave67_reset_h0_h3_big6_schinese"
        ]["r81_telemetry"]["clean_unmount_wave67_h0_h3"]
        self.assertEqual(ci["stock_unmount_restored_ok"], 1)
        self.assertEqual(
            ci["camreset_resets_silent_target_preserves_autopm_monitor3_recallhold_hdmi_airplane_ok"],
            1,
        )
        self.assertEqual(
            ci["nwreset_preserves_wave67_all_setup_recallhold_hdmi_airplane_ok"],
            1,
        )
        self.assertEqual(
            ci["initialize_restores_wave67_defaults_preserves_pm_count_airplane_ok"],
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
        self.assertEqual(ci["r81c_ok"], 1)

    def test_34_round81_r81a_and_r81c_gpe0_readback_big6_home_ge_300k_nonzero_pixels(self) -> None:
        for rk in (
            "r81a_pixelmap_monitor_recallhold_hdmi_recctrl_big6_schinese",
            "r81c_clean_unmount_wave67_reset_h0_h3_big6_schinese",
        ):
            gpe = self.summary["runs"][rk]["gpe0_readback"]
            self.assertTrue(gpe["present"], rk)
            self.assertEqual(gpe["total_pixels"], 1024 * 540, rk)
            self.assertEqual(gpe["bytes"], 1024 * 540 * 4, rk)
            self.assertGreaterEqual(gpe["nonzero_pixels"], 300000, rk)
            self.assertGreaterEqual(gpe["unique_colors"], 50, rk)

    def test_35_round81_r81a_alpha_and_composited_png_dimensions_and_size_cap_27467(self) -> None:
        self.assertEqual(self.alpha_dims, (1024, 540))
        self.assertEqual(self.comp_dims, (1024, 540))
        self.assertLessEqual(len(self.alpha_png_bytes), 27467)
        self.assertLessEqual(len(self.comp_png_bytes), 27467)
        self.assertGreater(len(self.alpha_png_bytes), 10000)
        self.assertGreater(len(self.comp_png_bytes), 10000)
        self.assertGreater(self.alpha_transparent, 100000)
        self.assertGreater(self.alpha_opaque, 100000)
        self.assertEqual(self.comp_opaque, 1024 * 540)

    def test_36_round81_r81a_png_exports_paths_sanitized_and_match_assets(self) -> None:
        pe = self.summary["runs"][
            "r81a_pixelmap_monitor_recallhold_hdmi_recctrl_big6_schinese"
        ]["png_exports"]
        self.assertEqual(
            pe["alpha_png"]["path"],
            "reports/2026-11-21-round81-pixelmap-monitor-recallhold-hdmi-recctrl-qemu/r81_hdmi_recmedia_tc_recctrl_24p_sdi_slot1_erofs_preview.png",
        )
        self.assertEqual(
            pe["composited_png"]["path"],
            "reports/2026-11-21-round81-pixelmap-monitor-recallhold-hdmi-recctrl-qemu/r81_pixelmap_apr_monitor3_evf_debunk_recallhold11_preview.png",
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

    def test_37_round81_deterministic_payload_hash_ignoring_volatile_timing(self) -> None:
        a = copy.deepcopy(self.summary)
        b = copy.deepcopy(self.summary)
        b["runs"]["r81a_pixelmap_monitor_recallhold_hdmi_recctrl_big6_schinese"]["wall_elapsed_sec"] = 999.99
        b["runs"]["r81a_pixelmap_monitor_recallhold_hdmi_recctrl_big6_schinese"]["r81_telemetry"]["wave67_init"]["verify_us"] = 12345
        ha = hashlib.sha256(json.dumps(_strip_volatile_timing(a), sort_keys=True).encode("utf-8")).hexdigest()
        hb = hashlib.sha256(json.dumps(_strip_volatile_timing(b), sort_keys=True).encode("utf-8")).hexdigest()
        self.assertEqual(ha, hb)

    def test_38_round81_verify_us_positive_under_3_seconds_across_all_3_runs(self) -> None:
        us_a = self.summary["runs"]["r81a_pixelmap_monitor_recallhold_hdmi_recctrl_big6_schinese"]["r81_telemetry"]["wave67_init"]["verify_us"]
        us_b = self.summary["runs"]["r81b_wave67_pixelmap_monitor_recallhold_hdmi_recctrl_guard"]["r81_telemetry"]["wave67_guard"]["verify_us"]
        us_c = self.summary["runs"]["r81c_clean_unmount_wave67_reset_h0_h3_big6_schinese"]["r81_telemetry"]["clean_unmount_wave67_h0_h3"]["verify_us"]
        for us in (us_a, us_b, us_c):
            self.assertGreater(us, 0)
            self.assertLess(us, 3_000_000)

    def test_39_round81_top_colors_transparent_plus_nonzero_equals_total_pixels(self) -> None:
        for rk in (
            "r81a_pixelmap_monitor_recallhold_hdmi_recctrl_big6_schinese",
            "r81c_clean_unmount_wave67_reset_h0_h3_big6_schinese",
        ):
            gpe = self.summary["runs"][rk]["gpe0_readback"]
            color_map = {row["argb"]: row["pixels"] for row in gpe["top_colors"]}
            self.assertIn("0x00000000", color_map)
            self.assertEqual(color_map["0x00000000"] + gpe["nonzero_pixels"], gpe["total_pixels"])

    def test_40_round81_r81b_fast_early_exit_and_skipped_gpe0(self) -> None:
        r81b = self.summary["runs"]["r81b_wave67_pixelmap_monitor_recallhold_hdmi_recctrl_guard"]
        self.assertEqual(r81b["duration_budget_sec"], 35)
        self.assertGreater(r81b["wall_elapsed_sec"], 1.0)
        self.assertLess(r81b["wall_elapsed_sec"], 60.0)
        self.assertTrue(r81b["gpe0_readback"]["skipped_stock_fx3_mode"])

    def test_41_round81_faithful_invariants_preserved_across_all_3_runs(self) -> None:
        for rk, rv in self.summary["runs"].items():
            fi = rv["faithful_invariants"]
            self.assertEqual(fi["FX6_NATIVE_FAITHFUL"], 1, rk)
            self.assertEqual(fi["subst_color"], 0, rk)
            self.assertEqual(fi["subst_image"], 0, rk)
            self.assertEqual(fi["forced_render"], 0, rk)
            self.assertEqual(fi["skipped_node"], 0, rk)
            self.assertEqual(fi["lock_bypass"], 0, rk)

    def test_42_round81_all_3_runs_stage_b_manifest_count_13(self) -> None:
        for rk, rv in self.summary["runs"].items():
            self.assertEqual(rv["stage_b"]["manifest_count"], 13, rk)
            self.assertEqual(len(rv["stage_b"]["manifest_items"]), 13, rk)

    def test_43_round81_all_3_runs_prefix_counts_include_fx6_r81(self) -> None:
        r81a_pc = self.summary["runs"]["r81a_pixelmap_monitor_recallhold_hdmi_recctrl_big6_schinese"]["prefix_counts"]
        r81b_pc = self.summary["runs"]["r81b_wave67_pixelmap_monitor_recallhold_hdmi_recctrl_guard"]["prefix_counts"]
        r81c_pc = self.summary["runs"]["r81c_clean_unmount_wave67_reset_h0_h3_big6_schinese"]["prefix_counts"]
        self.assertGreater(r81a_pc["FX6_R81_"], 10)
        self.assertEqual(r81b_pc["FX6_R81_"], 3)
        self.assertGreater(r81c_pc["FX6_R81_"], 10)

    def test_44_round81_r81_meta_invariants_across_all_3_runs(self) -> None:
        for rk, rv in self.summary["runs"].items():
            m = rv["stage_b"]["r81"]
            self.assertEqual(m["milestone_round_ordinal"], 81, rk)
            self.assertEqual(m["realhw_round_ordinal"], 54, rk)
            self.assertEqual(m["total_live_runs_at_completion"], 162, rk)
            self.assertEqual(m["total_png_receipts_at_completion"], 108, rk)
            self.assertEqual(m["dormant_fx6_abb_events"], 0, rk)
            self.assertEqual(m["dormant_fx3_evf_events"], 0, rk)
            self.assertEqual(m["dormant_fx6_vf_4subitems_events"], 0, rk)
            self.assertEqual(m["dormant_recallhold_movie_events"], 0, rk)
            self.assertEqual(m["dormant_recallhold_wb_events"], 0, rk)
            self.assertEqual(m["dormant_fx6_high_low_key_events"], 0, rk)
            self.assertEqual(m["dormant_hdmi_4k2k_events"], 0, rk)
            self.assertEqual(m["dormant_hdmi_24p60p_events"], 0, rk)
            self.assertEqual(m["usb_tx"], 0, rk)
            self.assertEqual(m["slot1_writes"], 0, rk)
            self.assertEqual(m["slot1_data_sector_writes"], 0, rk)
            self.assertEqual(m["slot1_avf_info_mutated"], 0, rk)
            self.assertEqual(m["raw_firmware_bytes_leaked"], 0, rk)
            self.assertEqual(m["emmc_write_count"], 0, rk)

    def test_45_round81_sanitize_helper_redacts_host_paths_and_reserved_port(self) -> None:
        dirty = {
            "run_id": "test-run",
            "lang": "schinese",
            "r81_mode": "pixelmap_monitor_recallhold_hdmi_recctrl_big6",
            "kernel_version": "Linux version 4.9.337-scel+",
            "kernel_bin": "/Users/fake/secret/kernel.bin",
            "dtb_bin": "/Users/fake/secret/guest.dtb",
            "build": {"tmp_build": "/private/tmp/build-123"},
            "stage_b": {"r81": {"r81_mode": "pixelmap_monitor_recallhold_hdmi_recctrl_big6"}},
            "r81_telemetry": {
                "wave67_init": {"r81_init_ok": 1},
                "wave67_guard": {"r81b_ok": 1},
                "clean_unmount_wave67_h0_h3": {"r81c_ok": 1, "surfaces_h0_eq_h3": 16},
            },
            "gpe0_readback": {"nonzero_pixels": 346686},
            "png_exports": {
                "alpha_png": {
                    "path": "/Users/kafu/repo/reports/2026-11-21-round81-pixelmap-monitor-recallhold-hdmi-recctrl-qemu/r81_hdmi_recmedia_tc_recctrl_24p_sdi_slot1_erofs_preview.png"
                }
            },
            "prefix_counts": {"FX6_R81_": 10},
        }
        sanitized = self.runner.sanitize_round81_summary(dirty, dirty, dirty)
        raw = json.dumps(sanitized)
        self.assertNotIn("/Users/", raw)
        self.assertNotIn("/private/tmp/", raw)
        self.assertNotIn("kernel_bin", raw)
        self.assertNotIn("dtb_bin", raw)
        self.assertIn(
            "reports/2026-11-21-round81-pixelmap-monitor-recallhold-hdmi-recctrl-qemu/r81_hdmi_recmedia_tc_recctrl_24p_sdi_slot1_erofs_preview.png",
            raw,
        )

    def test_46_round81_four_modes_and_mocked_donorless_work_root_none_master_gates(self) -> None:
        for env_overrides in (
            {},
            {"FX3_CLEAN_ROOM_TEST": "1"},
            {"FX3_FX6_FORCE_CLEAN_ROOM": "1"},
        ):
            with mock.patch.dict(os.environ, env_overrides, clear=False):
                parsed = self.runner.extract_milestones(
                    "Linux version 4.9.337-scel+\n"
                    "FX6_R81_WAVE67_INIT pixelmap_apr_ok=1 monitor3_evf_debunk_ok=1 "
                    "recallhold11_pushaf_ok=1 hdmi_tc_recctrl_sdi_erofs_ok=1 usb_tx=0 slot1_writes=0 r81_init_ok=1\n"
                )
                self.assertEqual(parsed["r81_telemetry"]["wave67_init"]["r81_init_ok"], 1)

        closure_pkg_dir = REPO_ROOT / "outputs" / "fx6-on-fx3-closure"
        safety_dir = REPO_ROOT / "outputs" / "fx3-safety"
        recovery_dir = REPO_ROOT / "outputs" / "fx3-recovery-adapter"
        firmware_lab_dir = REPO_ROOT / "outputs" / "fx3-firmware-lab"
        vm_dir = REPO_ROOT / "outputs" / "fx3-vm"
        added = [str(p) for p in (closure_pkg_dir, safety_dir, recovery_dir, firmware_lab_dir, vm_dir) if str(p) not in sys.path]
        for p in added:
            sys.path.insert(0, p)
        try:
            from fx6_closure.realhw_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_and_hdmi_tc_verifier import (
                inspect_phase338_donors_bounded,
            )
            from fx6_closure.realhw_milestone364_master_gate import (
                evaluate_realhw_milestone364_master_gate,
            )
            from fx6_closure.realhw_milestone375_master_gate import (
                evaluate_realhw_milestone375_master_gate,
            )

            with mock.patch(
                "fx6_closure.realhw_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_and_hdmi_tc_verifier._resolve_work_root_or_none",
                return_value=None,
            ):
                donor_ci = inspect_phase338_donors_bounded(
                    force_clean_room=False,
                    work_root=None,
                    fx6_lib_dir=None,
                    fx3_modules_dir=None,
                )
                self.assertEqual(donor_ci.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertEqual(donor_ci.bytes_read_total, 0)
                self.assertEqual(donor_ci.raw_firmware_bytes_leaked, 0)

            with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
                rep364 = evaluate_realhw_milestone364_master_gate(
                    repo_root=REPO_ROOT,
                    force_clean_room=True,
                    simulate_bench_dry_run=False,
                )
                self.assertEqual(rep364.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertTrue(rep364.all_pillars_milestone_ready)
                self.assertEqual(rep364.raw_firmware_bytes_leaked, 0)
                self.assertGreaterEqual(rep364.qemu_rounds_verified, 54)
                self.assertGreaterEqual(rep364.qemu_runs_verified, 162)
                self.assertGreaterEqual(rep364.qemu_png_receipts_verified, 108)

                rep375 = evaluate_realhw_milestone375_master_gate(
                    repo_root=REPO_ROOT,
                    force_clean_room=True,
                    simulate_bench_dry_run=False,
                )
                self.assertEqual(rep375.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertTrue(rep375.all_pillars_milestone_ready)
                self.assertEqual(rep375.raw_firmware_bytes_leaked, 0)
                self.assertGreaterEqual(rep375.qemu_rounds_verified, 54)
                self.assertGreaterEqual(rep375.qemu_runs_verified, 162)
                self.assertGreaterEqual(rep375.qemu_png_receipts_verified, 108)
        finally:
            for p in added:
                if p in sys.path:
                    sys.path.remove(p)

    def test_47_round81_argparse_percent_safe_help_and_no_hardcoded_python3(self) -> None:
        for line in self.runner_src.splitlines():
            if "help=" in line and "%" in line:
                stripped = line.replace("%%", "")
                self.assertNotIn("%", stripped, f"Unescaped '%' in argparse help: {line}")
        test_src = pathlib.Path(__file__).read_text(encoding="utf-8")
        forbidden_py = "/usr/" + "bin/python3"
        self.assertNotIn(forbidden_py, self.runner_src)
        self.assertNotIn(forbidden_py, test_src)

    def test_48_round81_all_108_pngs_under_27467b_and_clean_room_safe(self) -> None:
        round_dirs = [
            d for d in (REPO_ROOT / "reports").glob("2026-??-??-round*")
            if d.is_dir() and int(d.name.split("-round")[1].split("-")[0]) >= 28
        ]
        all_pngs = sorted(p for d in round_dirs for p in d.rglob("*.png") if p.is_file())
        self.assertGreaterEqual(len(all_pngs), 108)
        for p in all_pngs:
            self.assertLessEqual(p.stat().st_size, 27467, str(p))

    def test_49_round81_cli_help_subprocess_smoke_timeout_60(self) -> None:
        res = subprocess.run(
            [sys.executable, "-B", str(CLOSURE_DIR / "build_and_run_round.py"), "--help"],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        self.assertIn("--r81-mode", res.stdout)
        self.assertIn("pixelmap_monitor_recallhold_hdmi_recctrl_big6", res.stdout)

    def test_50_round81_wave67_uxc_and_node_tokens_wired_in_stage_a_source(self) -> None:
        for sym in (
            "r81_lookup_wave67_menu_node",
            "r81_lookup_uxc_token",
            "_f:0x7734:Auto Pixel Mapping",
            "_f:0x61f7:Pixel Mapping",
            "_f:0x64e7:Not Target",
            "BKID_APP_setting_notification_for_pixel_mappinng",
            "BKID_APP_pixel_mapping_excuted_status",
            "INFRA_NOTIFY_BATTERY_CHECK_FOR_PIXEL_MAPPING",
            "vdf_set_shutter_mute_by_pixel_mapping",
            "base:0xe44b:Monitor Brightness",
            "_f:0x7a61:Sunny Weather",
            "_f:0x6c5e:Display Quality",
            "_f:0x6a24:Monitor Flip Direction",
            "_f:0x6daf:Finder/Monitor Sel. (dormant on FX3 7.02)",
            "_f:0x6935:Viewfinder Bright. (dormant on FX3 7.02)",
            "base:0xe38d:Viewfinder Color Temp. (dormant on FX3 7.02)",
            "_f:0x718c:Finder Frame Rate (dormant on FX3 7.02)",
            "_f:0x6df3:AF On",
            "_f:0x794d:Eye AF",
            "_f:0x7a60:Tracking On",
            "_f:0x6282:Reg. Custom Shoot Set",
            "_f:0x60b4:Recall Custom hold 1",
            "_f:0x6144:Rec. Media dur HDMI Output",
            "_f:0x74d7:4K Output Set.(HDMI Only)",
            "PRM_HAITA_hdmi_4k_outpute_apsc_restriction",
            "_f:0x72af:Time Code Output",
            "_f:0x76e1:REC Control",
            "BKID_APP_setting_ctrl_for_hmdi",
        ):
            self.assertIn(sym, self.stage_a_src)

    def test_51_round81_report_markdown_has_chinese_conclusions_links_and_fact_inference_split(self) -> None:
        self.assertIn("## 结论先行", self.r81_readme)
        self.assertIn("实测事实", self.r81_readme)
        self.assertIn("推断", self.r81_readme)
        self.assertIn("file://", self.r81_readme)
        self.assertIn("54/54", self.r81_readme)
        self.assertIn("162/162", self.r81_readme)
        self.assertIn("108/108", self.r81_readme)
        self.assertIn("r81_pixelmap_apr_monitor3_evf_debunk_recallhold11_preview.png", self.r81_readme)
        self.assertIn("r81_hdmi_recmedia_tc_recctrl_24p_sdi_slot1_erofs_preview.png", self.r81_readme)

    def test_52_round81_closure_readme_documents_round81_54_rounds_162_runs_108_pngs(self) -> None:
        self.assertIn("## 81. Round 81", self.closure_readme)
        self.assertIn("54/54", self.closure_readme)
        self.assertIn("162/162", self.closure_readme)
        self.assertIn("108/108", self.closure_readme)
        self.assertIn("r81a", self.closure_readme)
        self.assertIn("r81b", self.closure_readme)
        self.assertIn("r81c", self.closure_readme)

    def test_53_round81_continuity_from_round80(self) -> None:
        self.assertEqual(self.r80_summary["round"], 80)
        self.assertEqual(self.summary["round"], self.r80_summary["round"] + 1)
        self.assertEqual(self.summary["raw_firmware_bytes_leaked"], 0)

    def test_54_round81_no_stray_temp_files_or_pyc_in_closure_dir(self) -> None:
        for bad_name in ("tmp", "scratch", ".worktrees"):
            self.assertFalse((REPO_ROOT / bad_name).exists(), bad_name)
        pyc_files = list(CLOSURE_DIR.rglob("*.pyc"))
        self.assertEqual(pyc_files, [])

    def test_55_round81_no_artifacts_subdir_under_closure(self) -> None:
        self.assertFalse((CLOSURE_DIR / "artifacts").exists())

    def test_56_round81_exact_11bit_recall_mask_and_zero_dormant_events(self) -> None:
        self.assertIn("R81_RECALL_ALL_11_BITS_MASK       0x07FFU", self.stage_a_src)
        self.assertIn("R81_RECALL_DORMANT_WB_BIT         (1U << 11)", self.stage_a_src)
        for rk in self.EXPECTED_RUN_KEYS:
            rv = self.summary["runs"][rk]
            t = rv["r81_telemetry"]
            for sec_name in ("wave67_init", "wave67_guard", "clean_unmount_wave67_h0_h3"):
                sec = t.get(sec_name)
                if sec:
                    for key in (
                        "dormant_fx6_abb_events",
                        "dormant_fx3_evf_events",
                        "dormant_fx6_vf_4subitems_events",
                        "dormant_recallhold_movie_events",
                        "dormant_recallhold_wb_events",
                        "dormant_fx6_high_low_key_events",
                        "dormant_hdmi_4k2k_events",
                        "dormant_hdmi_24p60p_events",
                    ):
                        self.assertEqual(sec.get(key, 0), 0, f"{rk}:{sec_name}:{key}")


if __name__ == "__main__":
    unittest.main()
