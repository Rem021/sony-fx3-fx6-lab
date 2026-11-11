#!/usr/bin/env python3
"""Offline Automated Verification Suite for Track 1A (`outputs/fx3-vm-trial`) & Track 2 (`outputs/fx3-vm`).

Strictly offline & clean-room safe:
- Never spawns any `qemu-system-*` or `qemu-gpio5` process and never signals host processes.
- Never modifies live VM directories, `.run.lock`, `.cpio` archives, or `.so` binaries.
- Unconditionally verifies all pure-source logic (compiled C scanline packer vs pure-Python
  reference, PNG RGBA/CRC-32/IDAT encoder, SVR4 `cpio newc` parser/updater/concatenation,
  `fx6_live_guest.c` memory/dlsym/bounds invariants, CXD90057 QEMU unified diff patch,
  Mach-O `@loader_path` / `LC_RPATH` relocation provenance, and `run_probe.py` AST contracts),
  while gracefully skipping optional read-only local BYOF binary SHA checks on clean clones.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import ast
import ctypes
import hashlib
import json
import mmap
import os
import re
import shutil
import struct
import subprocess
import tempfile
import unittest
import zlib
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

TRIAL_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = TRIAL_DIR.parents[1]
FX3_VM_DIR = REPO_ROOT / "outputs" / "fx3-vm"

if str(TRIAL_DIR) not in sys.path:
    sys.path.insert(0, str(TRIAL_DIR))

import build_live700  # noqa: E402
import run_fx6_menu_trial  # noqa: E402

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file_ro(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _py_reference_pack_scanlines(raw: bytes, width: int, height: int) -> Tuple[bytes, int]:
    """Pure-Python reference implementation of `fx6_pack_scanlines`."""
    expected_bytes = width * height * 4
    if len(raw) < expected_bytes:
        raise ValueError(f"raw buffer too small: {len(raw)} < {expected_bytes}")
    row_stride = 1 + width * 4
    bg_row = b"\x00" + b"\x0e\x10\x14\xff" * width
    out = bytearray(bg_row * height)
    nz = 0
    words = struct.unpack_from(f"<{width * height}I", raw, 0)
    for idx, v in enumerate(words):
        if v != 0:
            nz += 1
            y, x = divmod(idx, width)
            off = y * row_stride + 1 + x * 4
            out[off] = (v >> 16) & 0xFF
            out[off + 1] = (v >> 8) & 0xFF
            out[off + 2] = v & 0xFF
            out[off + 3] = 0xFF
    return bytes(out), nz


def _parse_png_chunks(png_bytes: bytes) -> List[Tuple[bytes, bytes, int, int]]:
    """Return list of `(chunk_type, payload, stored_crc, computed_crc)` from a PNG stream."""
    if not png_bytes.startswith(PNG_MAGIC):
        raise ValueError("missing PNG signature")
    pos = len(PNG_MAGIC)
    total = len(png_bytes)
    chunks: List[Tuple[bytes, bytes, int, int]] = []
    while pos < total:
        if pos + 12 > total:
            raise ValueError(f"truncated PNG chunk header/CRC at {pos}")
        (length,) = struct.unpack_from(">I", png_bytes, pos)
        ctype = png_bytes[pos + 4 : pos + 8]
        data_start = pos + 8
        data_end = data_start + length
        if data_end + 4 > total:
            raise ValueError(f"truncated PNG chunk {ctype!r} payload at {pos}")
        payload = png_bytes[data_start:data_end]
        (stored_crc,) = struct.unpack_from(">I", png_bytes, data_end)
        computed_crc = zlib.crc32(ctype + payload) & 0xFFFFFFFF
        chunks.append((ctype, payload, stored_crc, computed_crc))
        pos = data_end + 4
        if ctype == b"IEND":
            if pos != total:
                raise ValueError(f"trailing bytes ({total - pos}) after IEND")
            break
    return chunks


def _pack_newc_entry(
    name: str,
    payload: bytes,
    *,
    ino: int = 1,
    mode: int = 0o100644,
    uid: int = 0,
    gid: int = 0,
    nlink: int = 1,
    mtime: int = 1700000000,
    devmajor: int = 0,
    devminor: int = 1,
    rdevmajor: int = 0,
    rdevminor: int = 0,
    magic: bytes = b"070701",
) -> bytes:
    """Build a single 4-byte-aligned SVR4 `cpio newc` (`070701`) member record."""
    name_bytes = name.encode("utf-8") + b"\x00"
    hdr = (
        magic.decode("ascii")
        + f"{ino:08x}"
        + f"{mode:08x}"
        + f"{uid:08x}"
        + f"{gid:08x}"
        + f"{nlink:08x}"
        + f"{mtime:08x}"
        + f"{len(payload):08x}"
        + f"{devmajor:08x}"
        + f"{devminor:08x}"
        + f"{rdevmajor:08x}"
        + f"{rdevminor:08x}"
        + f"{len(name_bytes):08x}"
        + f"{0:08x}"
    ).encode("ascii")
    assert len(hdr) == 110
    head_and_name = hdr + name_bytes
    name_pad = b"\x00" * ((-len(head_and_name)) % 4)
    data_pad = b"\x00" * ((-len(payload)) % 4)
    return head_and_name + name_pad + payload + data_pad


def _build_newc_archive(entries: Sequence[Tuple[str, bytes, Dict[str, int]]]) -> bytes:
    parts: List[bytes] = []
    for idx, (name, payload, meta) in enumerate(entries, start=1):
        kw = {"ino": idx}
        kw.update(meta)
        parts.append(_pack_newc_entry(name, payload, **kw))
    parts.append(
        _pack_newc_entry(
            "TRAILER!!!",
            b"",
            ino=0,
            mode=0,
            uid=0,
            gid=0,
            nlink=1,
            mtime=0,
            devmajor=0,
            devminor=0,
        )
    )
    return b"".join(parts)


def _strip_c_comments(source: str) -> str:
    no_block = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", "", no_block)


def _extract_c_function_body(source: str, func_name: str) -> str:
    pattern = re.compile(rf"\b{re.escape(func_name)}\s*\([^;{{}}]*\)\s*\{{")
    match = pattern.search(source)
    if not match:
        raise AssertionError(f"C function {func_name!r} not found")
    brace_start = match.end() - 1
    depth = 0
    for idx in range(brace_start, len(source)):
        ch = source[idx]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return source[brace_start : idx + 1]
    raise AssertionError(f"Unbalanced braces in C function {func_name!r}")


class TestScanlinePackerAndPngEncoder(unittest.TestCase):
    """Verify `run_fx6_menu_trial.py` C scanline packer and PNG encoder offline."""

    def _build_synthetic_bgra(self, width: int, height: int) -> bytes:
        edge_lanes = (0x00, 0x01, 0x7F, 0x80, 0xFE, 0xFF)
        words: List[int] = []
        n_edge = len(edge_lanes)
        for y in range(height):
            for x in range(width):
                if (x + y) % 11 == 0:
                    words.append(0x00000000)
                elif (x + y) % 7 == 0:
                    a = edge_lanes[(x + y) % n_edge]
                    r = edge_lanes[(x * 3 + y) % n_edge]
                    g = edge_lanes[(x + y * 5) % n_edge]
                    b = edge_lanes[(x * 7 + y * 2) % n_edge]
                    words.append((a << 24) | (r << 16) | (g << 8) | b)
                else:
                    a = (x * 13 + y * 29) & 0xFF
                    r = (x * 255 // max(width - 1, 1)) & 0xFF
                    g = (y * 255 // max(height - 1, 1)) & 0xFF
                    b = ((x ^ y) * 3) & 0xFF
                    val = (a << 24) | (r << 16) | (g << 8) | b
                    words.append(val if val != 0 else 0x00000001)
        return struct.pack(f"<{width * height}I", *words)

    def test_safe_import_and_mailbox_geometry_constants(self) -> None:
        self.assertEqual(run_fx6_menu_trial.GPE0_PHYS, 0x41E001000)
        self.assertEqual(run_fx6_menu_trial.GPE0_W, 1024)
        self.assertEqual(run_fx6_menu_trial.GPE0_H, 540)
        self.assertEqual(run_fx6_menu_trial.GPE0_BYTES, 1024 * 540 * 4)
        self.assertEqual(run_fx6_menu_trial.KEY_MB_PHYS, 0x41DF00000)
        self.assertEqual(run_fx6_menu_trial.CTRL_MB_PHYS, 0x41E000E00)
        self.assertEqual(run_fx6_menu_trial.CTRL_MAGIC, 0x4658364C)
        self.assertEqual(set(run_fx6_menu_trial.PAGE_NAMES.keys()), set(range(25)))
        if (REPO_ROOT / "reports" / "2026-11-07-fx6-uxengine-init-assist" / "artifacts" / "fx6_menu_items_assist.h").is_file():
            self.assertEqual(len(run_fx6_menu_trial.ALL_128_PAGES), 128)
            self.assertEqual([p["idx"] for p in run_fx6_menu_trial.ALL_128_PAGES], list(range(128)))
            self.assertEqual(sum(p["rows"] for p in run_fx6_menu_trial.ALL_128_PAGES), 2224)

    def test_c_scanline_packer_compiles_in_tempdir_and_matches_odd_17x9(self) -> None:
        fn_src = inspect.getsource(run_fx6_menu_trial._get_fast_gpe0_fn) if "inspect" in globals() else (TRIAL_DIR / "run_fx6_menu_trial.py").read_text(encoding="utf-8")
        c_match = re.search(
            r'c_src\s*=\s*\(\s*((?:"[^"]*"\s*)+)\)',
            fn_src,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(c_match, "Embedded C scanline packer source must be extractable")
        c_code = ast.literal_eval("(" + c_match.group(1) + ")")
        self.assertIn("uint32_t fx6_pack_scanlines(", c_code)

        xcrun = Path("/usr/bin/xcrun")
        if not xcrun.is_file():
            self.skipTest("/usr/bin/xcrun not present on host")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            c_file = tmp_dir / "fx6_scanline_test.c"
            dylib_file = tmp_dir / "fx6_scanline_test.dylib"
            c_file.write_text(c_code, encoding="utf-8")
            proc = subprocess.run(
                [str(xcrun), "clang", "-O3", "-Wall", "-Wextra", "-Werror", "-dynamiclib", str(c_file), "-o", str(dylib_file)],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, msg=f"clang failed: {proc.stderr}")
            lib = ctypes.CDLL(str(dylib_file))
            pack_fn = lib.fx6_pack_scanlines
            pack_fn.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32]
            pack_fn.restype = ctypes.c_uint32

            for w, h in ((17, 9), (1, 1), (31, 5)):
                raw = self._build_synthetic_bgra(w, h)
                expected_scanlines, expected_nz = _py_reference_pack_scanlines(raw, w, h)
                dst = (ctypes.c_uint8 * (h * (1 + w * 4)))()
                src = (ctypes.c_char * len(raw)).from_buffer_copy(raw)
                actual_nz = int(pack_fn(ctypes.addressof(src), ctypes.addressof(dst), w, h))
                self.assertEqual(actual_nz, expected_nz)
                self.assertEqual(bytes(dst), expected_scanlines)

            # Explicit edge-value pixel vector (0x00, 0x7f, 0x80, 0xff across all 4 bytes)
            edge_words = [
                0x00000000,  # zero -> dark UI background (14, 16, 20, 255)
                0x007F80FF,  # alpha=0x00, R=0x7f, G=0x80, B=0xff (nonzero word -> opaque RGBA)
                0x7F80FF00,  # alpha=0x7f, R=0x80, G=0xff, B=0x00
                0x80FF007F,  # alpha=0x80, R=0xff, G=0x00, B=0x7f
                0xFF000000,  # alpha-only nonzero word -> R=0, G=0, B=0, A=255
                0xFFFFFFFF,  # all 0xff
            ]
            edge_raw = struct.pack("<6I", *edge_words)
            exp_edge, exp_edge_nz = _py_reference_pack_scanlines(edge_raw, 3, 2)
            dst_edge = (ctypes.c_uint8 * (2 * (1 + 3 * 4)))()
            src_edge = (ctypes.c_char * len(edge_raw)).from_buffer_copy(edge_raw)
            act_edge_nz = int(pack_fn(ctypes.addressof(src_edge), ctypes.addressof(dst_edge), 3, 2))
            self.assertEqual(act_edge_nz, 5)
            self.assertEqual(act_edge_nz, exp_edge_nz)
            self.assertEqual(bytes(dst_edge), exp_edge)

    def test_c_fastpath_and_python_reference_bit_identical_on_1024x540(self) -> None:
        fast = run_fx6_menu_trial._get_fast_gpe0_fn()
        self.assertIsNotNone(fast, "_get_fast_gpe0_fn() should compile or load C dylib on macOS")
        ctypes_mod, fn = fast

        w, h = run_fx6_menu_trial.GPE0_W, run_fx6_menu_trial.GPE0_H
        raw = self._build_synthetic_bgra(w, h)
        expected_scanlines, expected_nz = _py_reference_pack_scanlines(raw, w, h)
        self.assertEqual(len(expected_scanlines), h * (1 + w * 4))

        dst = (ctypes_mod.c_uint8 * (h * (1 + w * 4)))()
        src = (ctypes_mod.c_char * len(raw)).from_buffer_copy(raw)
        actual_nz = int(fn(ctypes_mod.addressof(src), ctypes_mod.addressof(dst), w, h))
        self.assertEqual(actual_nz, expected_nz)
        self.assertEqual(bytes(dst), expected_scanlines)

    def test_gpe0_raw_to_png_spec_compliance_crc32_and_stdlib_fallback_parity(self) -> None:
        w, h = run_fx6_menu_trial.GPE0_W, run_fx6_menu_trial.GPE0_H
        raw = self._build_synthetic_bgra(w, h)
        expected_scanlines, expected_nz = _py_reference_pack_scanlines(raw, w, h)

        png_c, nz_c = run_fx6_menu_trial.gpe0_raw_to_png(raw)
        self.assertEqual(nz_c, expected_nz)
        self.assertTrue(png_c.startswith(PNG_MAGIC))

        chunks = _parse_png_chunks(png_c)
        self.assertEqual([c[0] for c in chunks], [b"IHDR", b"IDAT", b"IEND"])
        for ctype, _payload, stored_crc, computed_crc in chunks:
            self.assertEqual(stored_crc, computed_crc, msg=f"CRC-32 mismatch in PNG chunk {ctype!r}")

        ihdr_w, ihdr_h, bit_depth, color_type, comp, filt, interlace = struct.unpack(">IIBBBBB", chunks[0][1])
        self.assertEqual((ihdr_w, ihdr_h), (1024, 540))
        self.assertEqual((bit_depth, color_type, comp, filt, interlace), (8, 6, 0, 0, 0))
        self.assertEqual(chunks[2][1], b"")

        decompressed = zlib.decompress(chunks[1][1])
        self.assertEqual(decompressed, expected_scanlines)

        # Force pure-Python stdlib fallback and assert 100% byte-identical PNG output
        orig_tried = run_fx6_menu_trial._FAST_GPE_TRIED
        orig_fn = run_fx6_menu_trial._FAST_GPE_FN
        try:
            run_fx6_menu_trial._FAST_GPE_TRIED = True
            run_fx6_menu_trial._FAST_GPE_FN = None
            png_py, nz_py = run_fx6_menu_trial.gpe0_raw_to_png(raw)
        finally:
            run_fx6_menu_trial._FAST_GPE_TRIED = orig_tried
            run_fx6_menu_trial._FAST_GPE_FN = orig_fn

        self.assertEqual(nz_py, nz_c)
        self.assertEqual(png_py, png_c)

    def test_gpe0_raw_to_png_rejects_short_and_blank_buffers(self) -> None:
        self.assertEqual(run_fx6_menu_trial.gpe0_raw_to_png(b""), (b"", 0))
        self.assertEqual(run_fx6_menu_trial.gpe0_raw_to_png(b"\xff" * (run_fx6_menu_trial.GPE0_BYTES - 4)), (b"", 0))
        blank = b"\x00" * run_fx6_menu_trial.GPE0_BYTES
        self.assertEqual(run_fx6_menu_trial.gpe0_raw_to_png(blank), (b"", 0))


class TestSvr4CpioBuilderAndTrialManifests(unittest.TestCase):
    """Verify `build_live700.py` SVR4 `cpio newc` builder/scanner and trial JSON manifests."""

    def test_newc_roundtrip_member_replacement_and_mode_uid_gid_preservation(self) -> None:
        orig_shim = b"\x7fELF\x02\x01\x01-original-shim-odd-31b!!"
        self.assertEqual(len(orig_shim), 31)
        entries = [
            ("usr", b"", {"mode": 0o040755, "uid": 0, "gid": 0, "nlink": 2}),
            ("usr/lib", b"", {"mode": 0o040755, "uid": 0, "gid": 0, "nlink": 2}),
            ("sbin/init", b"#!/bin/sh\nexit 0\n", {"mode": 0o100755, "uid": 0, "gid": 0}),
            ("usr/lib/liblink.so", b"libgrm-fbinit9.so", {"mode": 0o120777, "uid": 1000, "gid": 1000}),
            ("usr/lib/libgrm-fbinit9.so", orig_shim, {"mode": 0o100755, "uid": 501, "gid": 20, "mtime": 1762625132}),
            ("etc/flag1", b"1", {"mode": 0o100644, "uid": 33, "gid": 33}),
        ]
        initial_archive = _build_newc_archive(entries)
        initial_sha = _sha256_bytes(initial_archive)

        rows = build_live700.scan_newc_cpio(initial_archive)
        self.assertEqual(
            [r["name"] for r in rows],
            ["usr", "usr/lib", "sbin/init", "usr/lib/liblink.so", "usr/lib/libgrm-fbinit9.so", "etc/flag1", "TRAILER!!!"],
        )
        for r in rows:
            self.assertEqual(r["header"] % 4, 0)
            self.assertEqual(r["offset"] % 4, 0)
            self.assertEqual(r["end"] % 4, 0)
            self.assertEqual(initial_archive[r["header"] : r["header"] + 6], b"070701")

        target_before = next(r for r in rows if r["name"] == "usr/lib/libgrm-fbinit9.so")
        hdr_before = initial_archive[target_before["header"] : target_before["header"] + 110]

        with tempfile.TemporaryDirectory() as tmp:
            cpio_file = Path(tmp) / "synthetic-live700.cpio"
            cpio_file.write_bytes(initial_archive)

            # Replace member with larger odd-sized payload (137 bytes)
            new_shim = b"\x7fELF\x02\x01\x01" + bytes(range(130))
            self.assertEqual(len(new_shim), 137)
            res_new = build_live700.update_cpio_member(cpio_file, "usr/lib/libgrm-fbinit9.so", new_shim)
            self.assertEqual(res_new["members"], 7)
            self.assertEqual(res_new["sha256"], build_live700.sha256_file(cpio_file))

            updated_bytes = cpio_file.read_bytes()
            rows_after = build_live700.scan_newc_cpio(updated_bytes)
            target_after = next(r for r in rows_after if r["name"] == "usr/lib/libgrm-fbinit9.so")
            hdr_after = updated_bytes[target_after["header"] : target_after["header"] + 110]

            # Magic, ino, mode, uid, gid, nlink, mtime (bytes 0..54) and dev/namesize/check (bytes 62..110) must be untouched
            self.assertEqual(hdr_after[:54], hdr_before[:54])
            self.assertEqual(hdr_after[62:], hdr_before[62:])
            self.assertEqual(int(hdr_after[14:22].decode("ascii"), 16), 0o100755)
            self.assertEqual(int(hdr_after[22:30].decode("ascii"), 16), 501)
            self.assertEqual(int(hdr_after[30:38].decode("ascii"), 16), 20)
            self.assertEqual(int(hdr_after[54:62].decode("ascii"), 16), 137)
            self.assertEqual(updated_bytes[target_after["offset"] : target_after["offset"] + target_after["bytes"]], new_shim)

            # Replace back with original 31-byte payload -> 100% deterministic SHA-256 round-trip
            res_roundtrip = build_live700.update_cpio_member(cpio_file, "usr/lib/libgrm-fbinit9.so", orig_shim)
            self.assertEqual(res_roundtrip["sha256"], initial_sha)
            self.assertEqual(cpio_file.read_bytes(), initial_archive)

    def test_concatenated_cpio_member_addition_and_update(self) -> None:
        base_archive = _build_newc_archive(
            [
                ("sbin", b"", {"mode": 0o040755, "nlink": 2}),
                ("sbin/init", b"#!/bin/sh\nexec /sbin/init2\n", {"mode": 0o100755}),
            ]
        )
        pad_512 = b"\x00" * ((-len(base_archive)) % 512)
        overlay_archive = _build_newc_archive(
            [
                ("usr/lib/extra_added.so", b"INITIAL_ADDED_MEMBER_19", {"mode": 0o100755, "uid": 0, "gid": 0}),
            ]
        )
        combined = base_archive + pad_512 + overlay_archive

        with tempfile.TemporaryDirectory() as tmp:
            cpio_path = Path(tmp) / "concat.cpio"
            cpio_path.write_bytes(combined)
            with cpio_path.open("rb") as fh, mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                scanned = build_live700.scan_newc_cpio(mm)
            self.assertEqual(
                [r["name"] for r in scanned],
                ["sbin", "sbin/init", "TRAILER!!!", "usr/lib/extra_added.so", "TRAILER!!!"],
            )

            replacement = b"UPDATED_ADDED_MEMBER_PAYLOAD_33B!"
            info = build_live700.update_cpio_member(cpio_path, "usr/lib/extra_added.so", replacement)
            self.assertEqual(info["members"], 5)
            re_scanned = build_live700.scan_newc_cpio(cpio_path.read_bytes())
            added_row = next(r for r in re_scanned if r["name"] == "usr/lib/extra_added.so")
            self.assertEqual(cpio_path.read_bytes()[added_row["offset"] : added_row["offset"] + added_row["bytes"]], replacement)

    def test_cpio_corrupt_header_and_duplicate_or_missing_member_guards(self) -> None:
        with self.assertRaisesRegex(ValueError, "unexpected CPIO header magic"):
            build_live700.scan_newc_cpio(b"070799" + b"0" * 120)

        bad_name = bytearray(_pack_newc_entry("abc", b"1234"))
        bad_name[110 + 3] = ord("X")  # overwrite NUL terminator
        with self.assertRaisesRegex(ValueError, "corrupt CPIO entry name"):
            build_live700.scan_newc_cpio(bytes(bad_name))

        truncated = _pack_newc_entry("sbin/init", b"0123456789")[:-4]
        with self.assertRaisesRegex(ValueError, "truncated CPIO member"):
            build_live700.scan_newc_cpio(truncated)

        with tempfile.TemporaryDirectory() as tmp:
            missing_file = Path(tmp) / "does-not-exist.cpio"
            with self.assertRaises(FileNotFoundError):
                build_live700.update_cpio_member(missing_file, "usr/lib/libgrm-fbinit9.so", b"x")

            dup_cpio = Path(tmp) / "dup.cpio"
            dup_cpio.write_bytes(
                _build_newc_archive(
                    [
                        ("usr/lib/libgrm-fbinit9.so", b"one", {"mode": 0o100755}),
                        ("usr/lib/libgrm-fbinit9.so", b"two", {"mode": 0o100755}),
                    ]
                )
            )
            with self.assertRaisesRegex(ValueError, "expected exactly 1"):
                build_live700.update_cpio_member(dup_cpio, "usr/lib/libgrm-fbinit9.so", b"three")

            with self.assertRaisesRegex(ValueError, "expected exactly 1"):
                build_live700.update_cpio_member(dup_cpio, "usr/lib/absent.so", b"three")

    def test_sync_manifest_and_trial_json_schemas(self) -> None:
        manifest_path = TRIAL_DIR / "vm-candidate-gpecap25-live700.json"
        r10_path = TRIAL_DIR / "r10-deployment.json"
        self.assertTrue(manifest_path.is_file())
        self.assertTrue(r10_path.is_file())

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema"], "fx6-hybrid-fx3kernel-gpecap25-vm-candidate-v1")
        plat = manifest["fx3_platform"]
        self.assertEqual(plat["machine"], "virt,gic-version=2,secure=off")
        self.assertEqual(plat["cpu"], "cortex-a35")
        self.assertEqual(plat["memory_mib"], 5120)
        self.assertEqual(plat["initrd_load_address"], "0x440000000")
        self.assertEqual(plat["dtb_load_address"], "0x400002000")
        self.assertEqual(
            set(manifest["model_env"].items()),
            {
                ("FX3_VM_ESRAM_RAM", "1"),
                ("FX3_VM_HIGH_DDR", "1"),
                ("FX3_VM_SONY_TIMER", "1"),
                ("FX3_VM_SCU_REQUEST", "1"),
                ("FX3_VM_GPIO_BANK5", "1"),
            },
        )
        for key in (
            "owner_baseline",
            "kernel",
            "initrd",
            "dtb",
            "backup",
            "hybrid_source",
            "capid_preinit",
            "real_libgrm",
            "fx6_remote_board",
            "fx6_libra",
            "fx6_libstella",
            "fx6_grm_ma",
            "grm_fbinit",
            "backup_bug_skip",
            "appfw_future_skip",
            "upm_callsite_skip",
        ):
            self.assertIn(key, manifest)
            self.assertRegex(manifest[key]["sha256"], SHA256_RE, msg=f"Invalid SHA-256 in {key}")

        self.assertEqual(manifest["kernel"]["sha256"], "da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c")
        self.assertEqual(manifest["kernel"]["bytes"], 6610952)
        self.assertEqual(manifest["initrd"]["bytes"], manifest["initrd"]["size_bytes"])
        self.assertEqual(manifest["grm_fbinit"]["ux_screen_default"], "1024x540")

        # Test `sync_manifest` inside TemporaryDirectory without touching tracked manifest
        with tempfile.TemporaryDirectory() as tmp:
            copied_manifest = Path(tmp) / "vm-candidate.json"
            shutil.copyfile(manifest_path, copied_manifest)
            fake_shim_sha = "a" * 64
            fake_cpio_sha = "b" * 64
            build_live700.sync_manifest(
                copied_manifest,
                fake_shim_sha,
                {"path": "/tmp/fake.cpio", "sha256": fake_cpio_sha, "bytes": 123456},
            )
            synced = json.loads(copied_manifest.read_text(encoding="utf-8"))
            self.assertEqual(synced["initrd"]["sha256"], fake_cpio_sha)
            self.assertEqual(synced["initrd"]["bytes"], 123456)
            self.assertEqual(synced["initrd"]["size_bytes"], 123456)
            self.assertEqual(synced["grm_fbinit"]["sha256"], fake_shim_sha)
            self.assertEqual(synced["kernel"]["sha256"], manifest["kernel"]["sha256"])

        # Optional read-only check on local BYOF `libgrm-fbinit25-live700.so` when present on disk
        local_shim = TRIAL_DIR / "libgrm-fbinit25-live700.so"
        if local_shim.is_file():
            with local_shim.open("rb") as fh:
                elf_hdr = fh.read(20)
            self.assertEqual(elf_hdr[:6], b"\x7fELF\x02\x01")
            (e_type, e_machine) = struct.unpack_from("<HH", elf_hdr, 16)
            self.assertEqual((e_type, e_machine), (3, 183))  # ET_DYN, EM_AARCH64
            self.assertEqual(_sha256_file_ro(local_shim), manifest["grm_fbinit"]["sha256"])

        # Validate `r10-deployment.json`
        r10 = json.loads(r10_path.read_text(encoding="utf-8"))
        self.assertTrue(r10["source_candidate_exact_copy"])
        self.assertTrue(r10["syntax_check"])
        self.assertTrue(r10["check_only_pass"])
        self.assertFalse(r10["FX6_boot_verified"])
        self.assertEqual(set(r10["files_sha256"].keys()), {"FX3菜单.command", "使用说明.md", "新版验收记录.md", "README.md"})
        for fname, digest in r10["files_sha256"].items():
            self.assertRegex(digest, SHA256_RE)
            self.assertTrue((TRIAL_DIR / fname).is_file(), msg=f"Missing r10 file: {fname}")
        for frozen_name in ("FX3菜单.command", "使用说明.md"):
            self.assertEqual(_sha256_file_ro(TRIAL_DIR / frozen_name), r10["files_sha256"][frozen_name])


class TestCGuestShimSourceInvariants(unittest.TestCase):
    """Static regression audit of `outputs/fx3-vm-trial/src/fx6_live_guest.c` and `Makefile`."""

    def setUp(self) -> None:
        self.src_dir = TRIAL_DIR / "src"
        self.guest_c = (self.src_dir / "fx6_live_guest.c").read_text(encoding="utf-8")
        self.guest_code = _strip_c_comments(self.guest_c)

    def test_all_shim_sources_headers_and_makefile_targets_exist(self) -> None:
        for src_name in build_live700.SOURCES:
            p = self.src_dir / src_name
            self.assertTrue(p.is_file(), msg=f"Missing shim source: {src_name}")
            self.assertGreater(p.stat().st_size, 100)
        for hdr_name in ("fx6_static_assist.h", "fx6_menu_tree_builder.h", "fx6_native_menu_tables.h"):
            self.assertTrue((self.src_dir / hdr_name).is_file(), msg=f"Missing header: {hdr_name}")

        makefile_txt = (TRIAL_DIR / "Makefile").read_text(encoding="utf-8")
        self.assertIn(".PHONY: all shim clean-cache", makefile_txt)
        for target in ("all:", "shim:", "clean-cache:"):
            self.assertIn(target, makefile_txt)
        self.assertIn("$(PYTHON) -B build_live700.py", makefile_txt)
        self.assertIn("$(PYTHON) -B build_live700.py --compile-only", makefile_txt)

    def test_disp_key_bounds_and_zero_disp_cycle_oob_regression(self) -> None:
        # Ensure historical OOB `disp_cycle[12]` lookup is completely absent across `src/`
        for path in sorted(self.src_dir.iterdir()):
            if path.suffix in (".c", ".h"):
                code_only = _strip_c_comments(path.read_text(encoding="utf-8", errors="replace"))
                self.assertNotIn("disp_cycle[", code_only, msg=f"OOB disp_cycle indexing found in {path.name}")

        apply_key_body = _extract_c_function_body(self.guest_code, "fx6_apply_key")
        self.assertIn("uint32_t page       = mb[3] % FX6_NUM_PAGES;", apply_key_body)
        self.assertIn("uint32_t menu_cat   = mb[5] % 11u;", apply_key_body)
        self.assertRegex(apply_key_body, r"case\s+9\s*:\s*page\s*=\s*\(\s*page\s*\+\s*1u\s*\)\s*%\s*24u\s*;")

    def test_cached_dlsym_table_and_static_scratch_buffers_prevent_frame_leaks(self) -> None:
        # Verify cached `fx6_syms_t g_syms` resolved once in `fx6_init_syms`
        self.assertIn("typedef struct {", self.guest_code)
        self.assertIn("static fx6_syms_t g_syms;", self.guest_code)
        init_syms_body = _extract_c_function_body(self.guest_code, "fx6_init_syms")
        self.assertIn("if (g_syms.ready) return;", init_syms_body)
        self.assertIn("g_syms.ready = 1;", init_syms_body)
        self.assertGreaterEqual(init_syms_body.count("dlsym("), 12)

        # Verify 16-byte aligned static scratch buffers + in-place vtable D1Ev destruction
        for buf_decl in (
            "static unsigned char s_vs_buf[0x1400] __attribute__((aligned(16)));",
            "static unsigned char s_vf_buf[0x1180] __attribute__((aligned(16)));",
            "static unsigned char s_ic_buf[0x700]  __attribute__((aligned(16)));",
            "static unsigned char s_dict_buf[0x80] __attribute__((aligned(16)));",
        ):
            self.assertIn(buf_decl, self.guest_code)

        dtor_body = _extract_c_function_body(self.guest_code, "fx6_destroy_widget_inplace")
        self.assertIn("vt[0]", dtor_body)

        # Per-widget renderers must NOT call dlsym() or malloc()/calloc() per draw
        for fn_name in (
            "fx6_blit_imagedata_to_osd",
            "fx6_text_of",
            "fx6_render_string_rid",
            "fx6_render_string_desc",
            "fx6_fill_rect",
            "fx6_icon_blit",
        ):
            body = _extract_c_function_body(self.guest_code, fn_name)
            self.assertNotIn("dlsym(", body, msg=f"Uncached dlsym() inside {fn_name}")
            self.assertNotIn("calloc(", body, msg=f"Per-widget calloc() leak inside {fn_name}")
            self.assertNotIn("malloc(", body, msg=f"Per-widget malloc() leak inside {fn_name}")


class TestTrack2MinimalCxd90057VmAndProvenance(unittest.TestCase):
    """Offline verification of Track 2 (`outputs/fx3-vm/`) patch, provenance, and Mach-O relocation."""

    def test_qemu_esram_high_ddr_unified_diff_and_gpl_license(self) -> None:
        patch_path = FX3_VM_DIR / "source-patches" / "fx3-esram-high-ddr.patch"
        copying_path = FX3_VM_DIR / "COPYING-QEMU"
        self.assertTrue(patch_path.is_file())
        self.assertTrue(copying_path.is_file())

        copying_txt = copying_path.read_text(encoding="utf-8")
        self.assertIn("GNU GENERAL PUBLIC LICENSE", copying_txt)
        self.assertIn("Version 2, June 1991", copying_txt)
        self.assertEqual(copying_path.stat().st_size, 17880)

        lines = patch_path.read_text(encoding="utf-8").splitlines()
        self.assertGreaterEqual(len(lines), 10)
        self.assertEqual(lines[0], "--- a/hw/arm/virt.c")
        self.assertEqual(lines[1], "+++ b/hw/arm/virt.c")

        hunk_re = re.compile(r"^@@ -(\d+),(\d+) \+(\d+),(\d+) @@$")
        idx = 2
        hunk_count = 0
        added_lines: List[str] = []
        while idx < len(lines):
            m = hunk_re.match(lines[idx])
            self.assertIsNotNone(m, msg=f"Expected unified diff hunk header at line {idx + 1}: {lines[idx]!r}")
            old_expected = int(m.group(2))
            new_expected = int(m.group(4))
            hunk_count += 1
            idx += 1
            old_seen = 0
            new_seen = 0
            while idx < len(lines) and not lines[idx].startswith("@@ "):
                ln = lines[idx]
                if ln == "":
                    # Empty context line without trailing space is non-standard unless EOF; handle strictly
                    self.fail(f"Unexpected bare empty line inside diff hunk at line {idx + 1}")
                prefix = ln[0]
                self.assertIn(prefix, (" ", "+", "-"), msg=f"Invalid diff prefix {prefix!r} at line {idx + 1}")
                if prefix in (" ", "-"):
                    old_seen += 1
                if prefix in (" ", "+"):
                    new_seen += 1
                if prefix == "+":
                    added_lines.append(ln[1:])
                idx += 1
            self.assertEqual(old_seen, old_expected, msg=f"Hunk #{hunk_count} old line count mismatch")
            self.assertEqual(new_seen, new_expected, msg=f"Hunk #{hunk_count} new line count mismatch")

        self.assertEqual(hunk_count, 2)
        added_blob = "\n".join(added_lines)
        self.assertIn('g_getenv("FX3_VM_HIGH_DDR")', added_blob)
        self.assertIn("0x400000000ULL", added_blob)
        self.assertIn('g_getenv("FX3_VM_ESRAM_RAM")', added_blob)
        self.assertIn('"fx3.esram-mailbox-probe"', added_blob)
        self.assertIn("0x00001000", added_blob)
        self.assertIn("0xfe005000", added_blob)

    def test_manifest_and_all_six_metadata_provenance_and_rpath_cleanliness(self) -> None:
        manifest = json.loads((FX3_VM_DIR / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema"], "fx3-mac-vm-minimal-research-v1")
        self.assertEqual(manifest["memory_mib"], 2048)
        self.assertEqual(manifest["model_env"], {"FX3_VM_ESRAM_RAM": "1", "FX3_VM_HIGH_DDR": "1"})
        self.assertEqual(manifest["kernel"]["sha256"], "da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c")
        self.assertFalse(manifest["kernel"]["modified"])
        self.assertEqual(len(manifest["disabled_initcalls"]), 7)
        self.assertEqual(set(manifest["profiles"].keys()), {"minimal-linux", "app-loader"})
        for claim_name, claim_val in manifest["claims"].items():
            self.assertFalse(claim_val, msg=f"Research claim {claim_name!r} must remain False")

        rt_sha = manifest["runtime_sha256"]
        self.assertEqual(len(rt_sha), 8)
        for rel_path, digest in rt_sha.items():
            self.assertRegex(digest, SHA256_RE, msg=f"Invalid digest for {rel_path}")
            cand = FX3_VM_DIR / rel_path
            if cand.is_file():
                self.assertEqual(_sha256_file_ro(cand), digest, msg=f"Local runtime binary/share mismatch: {rel_path}")

        meta_dir = FX3_VM_DIR / "metadata"
        expected_meta_files = (
            "build-provenance.json",
            "file-manifest.json",
            "final-runtime-validation.json",
            "rpath-removal.json",
            "runtime-relocation-before-rpath-removal.json",
            "runtime-relocation.json",
        )
        meta: Dict[str, object] = {}
        for fn in expected_meta_files:
            p = meta_dir / fn
            self.assertTrue(p.is_file(), msg=f"Missing metadata file: {fn}")
            meta[fn] = json.loads(p.read_text(encoding="utf-8"))

        # 1. build-provenance.json
        bp = meta["build-provenance.json"]
        assert isinstance(bp, dict)
        self.assertTrue(bp["no_original_ELF_modified"])
        self.assertTrue(bp["not_a_full_signed_firmware_package"])
        self.assertEqual(bp["models"], "source-patches/fx3-esram-high-ddr.patch")
        self.assertEqual(bp["runtime_relocation"], "metadata/runtime-relocation.json")
        self.assertEqual(len(bp["qemu_source"]["records"]), 5)
        for rec in bp["qemu_source"]["records"]:
            self.assertRegex(rec["sha256"], SHA256_RE)

        # 2. rpath-removal.json + before/after runtime-relocation.json chain
        rr = meta["rpath-removal.json"]
        reloc_before = meta["runtime-relocation-before-rpath-removal.json"]
        reloc_final = meta["runtime-relocation.json"]
        assert isinstance(rr, dict) and isinstance(reloc_before, list) and isinstance(reloc_final, list)
        self.assertEqual(len(reloc_before), 4)
        self.assertEqual(len(reloc_final), 4)
        self.assertEqual(reloc_final[0]["output"], "bin/qemu-system-aarch64")
        self.assertEqual(rr["before_sha256"], reloc_before[0]["output_sha256"])
        self.assertEqual(rr["before_sha256"], reloc_final[0]["after_relative_link_before_rpath_removal_sha256"])
        self.assertEqual(rr["after_sha256"], reloc_final[0]["output_sha256"])
        self.assertEqual(rr["after_sha256"], rt_sha["bin/qemu-system-aarch64"])
        self.assertIsNone(rr["source_entitlements"])
        self.assertIsNone(rr["final_entitlements"])
        self.assertEqual(len(rr["removed"]), 2)
        self.assertEqual(rr["removed"], reloc_final[0]["removed_LC_RPATH"])

        allowed_dep_prefixes = ("@loader_path/", "/usr/lib/", "/System/Library/")
        leaked_host_prefixes = ("/Volumes/", "/Users/", "/opt/homebrew/", "/usr/local/")
        for item in reloc_final:
            out_rel = item["output"]
            self.assertEqual(item["output_sha256"], rt_sha[out_rel])
            self.assertIsNone(item["entitlements"])
            self.assertEqual(item.get("LC_RPATH_entries", []), [])
            for chg in item["changes"]:
                self.assertTrue(chg["new"].startswith("@loader_path/"), msg=f"Non-relative rewrite: {chg}")
            otool_lines = [ln.strip() for ln in item["otool_final"].splitlines() if ln.strip()]
            # Line 0 is `<binary_path>:`; every linked dependency line after line 0 must be clean
            self.assertGreaterEqual(len(otool_lines), 2)
            for dep_line in otool_lines[1:]:
                dep_path = dep_line.split(" (", 1)[0].strip()
                self.assertTrue(
                    dep_path.startswith(allowed_dep_prefixes),
                    msg=f"Unexpected dependency path in {out_rel}: {dep_path!r}",
                )
                self.assertFalse(
                    dep_path.startswith(leaked_host_prefixes),
                    msg=f"Machine-specific path leaked in {out_rel}: {dep_path!r}",
                )

        # 3. final-runtime-validation.json
        frv = meta["final-runtime-validation.json"]
        assert isinstance(frv, dict)
        self.assertEqual(frv["status"], "FINAL_NATIVE_RUNTIME_CORE_AND_LOADER_PASSED")
        self.assertEqual(frv["qemu_sha256"], rt_sha["bin/qemu-system-aarch64"])
        self.assertEqual(len(frv["runtime_binary_checks"]), 4)
        for chk in frv["runtime_binary_checks"]:
            self.assertEqual(chk["sha256"], rt_sha[chk["path"]])
            self.assertTrue(chk["codesign_valid"])
            self.assertFalse(chk["absolute_non_system_load_paths"])
            self.assertFalse(chk["LC_RPATH"])
        for run_rec in frv["end_to_end_runs"]:
            self.assertTrue(run_rec["same_input_hashes_verified_after_run"])
            self.assertTrue(run_rec["process_reaped"])

        # 4. file-manifest.json
        fm = meta["file-manifest.json"]
        assert isinstance(fm, dict)
        self.assertTrue(fm["runtime_frozen"])
        self.assertEqual(fm["runtime_qemu_sha256"], rt_sha["bin/qemu-system-aarch64"])
        self.assertEqual(fm["task_qemu_processes_remaining"], [])
        fm_map = {entry["path"]: entry for entry in fm["files"]}
        self.assertEqual(len(fm_map), 19)
        for rel_p, entry in fm_map.items():
            self.assertRegex(entry["sha256"], SHA256_RE)
            self.assertGreater(entry["bytes"], 0)
            if rel_p in rt_sha:
                self.assertEqual(entry["sha256"], rt_sha[rel_p])
            elif rel_p != "README.md":
                on_disk = FX3_VM_DIR / rel_p
                self.assertTrue(on_disk.is_file(), msg=f"Missing tracked file in fx3-vm: {rel_p}")
                self.assertEqual(_sha256_file_ro(on_disk), entry["sha256"], msg=f"SHA-256 drift on {rel_p}")

    def test_run_probe_ast_syntax_and_isolation_guards(self) -> None:
        probe_path = FX3_VM_DIR / "run_probe.py"
        src = probe_path.read_text(encoding="utf-8")
        tree = ast.parse(src, filename=str(probe_path))
        self.assertEqual(ast.get_docstring(tree), "Bounded local FX3 kernel/userland research VM. No camera/device access.")

        fn_names = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
        self.assertIn("digest", fn_names)
        self.assertIn("main", fn_names)

        # Static safety & isolation contracts in `run_probe.py`
        self.assertIn("'minimal-linux'", src)
        self.assertIn("'app-loader'", src)
        self.assertIn("'--self-check'", src)
        self.assertIn("1<=ns.seconds<=30", src)
        self.assertIn("fcntl.LOCK_EX|fcntl.LOCK_NB", src)
        for flag in ("'-display','none'", "'-nodefaults'", "'-nic','none'", "'-no-reboot'"):
            self.assertIn(flag, src)

    def test_command_launchers_zsh_syntax_check(self) -> None:
        zsh_bin = Path("/bin/zsh")
        if not zsh_bin.is_file():
            self.skipTest("/bin/zsh not available")
        launchers = (
            TRIAL_DIR / "FX6菜单.command",
            TRIAL_DIR / "FX3菜单.command",
            FX3_VM_DIR / "启动FX3最小研究虚拟机.command",
        )
        for launcher in launchers:
            self.assertTrue(launcher.is_file(), msg=f"Missing launcher: {launcher}")
            proc = subprocess.run(
                [str(zsh_bin), "-n", str(launcher)],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, msg=f"zsh -n failed for {launcher.name}: {proc.stderr}")


if __name__ == "__main__":
    unittest.main()
