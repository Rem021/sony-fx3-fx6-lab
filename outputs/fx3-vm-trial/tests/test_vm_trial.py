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


def _force_clean_room() -> bool:
    return os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM", "").strip().lower() in ("1", "true", "yes")


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
        cc_bin = shutil.which("clang") or shutil.which("cc")
        if sys.platform == "darwin" and xcrun.is_file():
            shared_ext = ".dylib"
            cc_prefix = [str(xcrun), "clang", "-O3", "-Wall", "-Wextra", "-Werror", "-dynamiclib"]
        elif cc_bin:
            shared_ext = ".so"
            cc_prefix = [cc_bin, "-O3", "-Wall", "-Wextra", "-Werror", "-shared", "-fPIC"]
        else:
            self.skipTest("No host C compiler (/usr/bin/xcrun or clang/cc) available")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            c_file = tmp_dir / "fx6_scanline_test.c"
            dylib_file = tmp_dir / f"fx6_scanline_test{shared_ext}"
            c_file.write_text(c_code, encoding="utf-8")
            proc = subprocess.run(
                [*cc_prefix, str(c_file), "-o", str(dylib_file)],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, msg=f"C compiler failed: {proc.stderr}")
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
        if sys.platform != "darwin" or not Path("/usr/bin/xcrun").is_file():
            self.skipTest("macOS /usr/bin/xcrun dylib fastpath check skipped on non-macOS host")
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
        if not _force_clean_room() and local_shim.is_file():
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
        self.assertEqual(_sha256_file_ro(TRIAL_DIR / "使用说明.md"), r10["files_sha256"]["使用说明.md"])
        fx3_menu_src = (TRIAL_DIR / "FX3菜单.command").read_text(encoding="utf-8")
        self.assertIn("FX3_V25_RUNTIME_DIR", fx3_menu_src)
        self.assertIn("AI-Workspace/AI/Projects/Mac", fx3_menu_src)
        self.assertIn("FX3_PYTHON", fx3_menu_src)


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

        # Verify 16-byte aligned 32-slot static ring pools + in-place vtable D1Ev destruction
        self.assertIn("#define FX6_WIDGET_POOL_N 32u", self.guest_code)
        for buf_decl in (
            "static unsigned char s_vs_pool[FX6_WIDGET_POOL_N][0x1400] __attribute__((aligned(16)));",
            "static unsigned char s_vf_pool[FX6_WIDGET_POOL_N][0x1180] __attribute__((aligned(16)));",
            "static unsigned char s_ic_pool[FX6_WIDGET_POOL_N][0x700]  __attribute__((aligned(16)));",
            "static unsigned char s_dict_buf[0x80] __attribute__((aligned(16)));",
        ):
            self.assertIn(buf_decl, self.guest_code)

        dtor_body = _extract_c_function_body(self.guest_code, "fx6_destroy_widget_inplace")
        self.assertIn("vt[0]", dtor_body)

        # Per-widget renderers must NOT call dlsym() or malloc()/calloc() per draw
        for fn_name in (
            "fx6_blit_imagedata_rect_to_osd",
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

    def test_phase19_notify_interposer_and_icon_blitter_invariants(self) -> None:
        # 1) GenerateImageCommand::notify(bool) interposer + command drain before widget dtor
        notify_body = _extract_c_function_body(self.guest_code, "_ZN5libra20GenerateImageCommand6notifyEb")
        for sym in (
            "(char *)self + 0x28",
            "g_syms.removeFirst(list)",
            "g_syms.imageOnLoad(img)",
            "(uintptr_t)cb > 0x10000ULL",
            "g_syms.rmGetInstance()",
            "g_syms.rmGetAllocator(rm)",
            "avt[2]",
        ):
            self.assertIn(sym, notify_body)

        onload_body = _extract_c_function_body(self.guest_code, "_ZN5libra9ImageData6onLoadEv")
        self.assertIn("if (!self) return;", onload_body)

        for fn_name in ("fx6_render_string_rid", "fx6_render_string_desc", "fx6_fill_rect", "fx6_icon_blit"):
            body = _extract_c_function_body(self.guest_code, fn_name)
            self.assertIn("fx6_drain_commands(", body, msg=f"Missing fx6_drain_commands in {fn_name}")
            self.assertLess(
                body.index("fx6_drain_commands("),
                body.rindex("fx6_destroy_widget_inplace("),
                msg=f"{fn_name} must drain processCommands before destroying widget",
            )

        # 2) Multi-format RGBA4444 / RGBA8888 / A8 / ARGB4444 icon blitter & Big-6 per-cell RID table
        blit_body = _extract_c_function_body(self.guest_code, "fx6_blit_imagedata_rect_to_osd")
        for mode_tok in ("bmp_fmt == 2 || stella_fmt == 1", "bmp_fmt == 4 || stella_fmt == 8", "bmp_fmt == 3", "mode == 2", "mode == 3"):
            self.assertIn(mode_tok, blit_body)
        self.assertIn("0x23be8d8ULL", self.guest_code)
        self.assertIn("0x42d5800u", self.guest_code)



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
            if not _force_clean_room() and cand.is_file():
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
            elif rel_p not in {"README.md", "run_probe.py", "启动FX3最小研究虚拟机.command"}:
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
        self.assertIn("resolve_migrated_path", fn_names)
        self.assertIn("main", fn_names)

        # Static safety & isolation contracts in `run_probe.py`
        self.assertIn("'minimal-linux'", src)
        self.assertIn("'app-loader'", src)
        self.assertIn("'--self-check'", src)
        self.assertIn("1<=ns.seconds<=30", src)
        self.assertIn("fcntl.LOCK_EX|fcntl.LOCK_NB", src)
        self.assertIn("AI-Workspace", src)
        self.assertIn("startswith('/Volumes/KAFU2T')", src)
        for flag in ("'-display','none'", "'-nodefaults'", "'-nic','none'", "'-no-reboot'"):
            self.assertIn(flag, src)

    def test_internal_disk_dynamic_path_probing_across_trial_scripts(self) -> None:
        # build_live700.py must resolve Zig dynamically without failing in clean-room imports
        self.assertTrue(hasattr(build_live700, "resolve_default_zig"))
        zig_path = build_live700.resolve_default_zig()
        self.assertIsInstance(zig_path, Path)

        # run_fx6_menu_trial.py must relocate stale /Volumes/KAFU2T runner paths dynamically
        self.assertTrue(hasattr(run_fx6_menu_trial, "_relocate_migrated_path"))
        relocated = run_fx6_menu_trial._relocate_migrated_path(
            "/Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/outputs/fx3-vm-trial/build_live700.py"
        )
        self.assertTrue(Path(relocated).exists() or "AI-Workspace" in relocated or relocated.startswith(str(REPO_ROOT)))

    def test_command_launchers_zsh_syntax_check(self) -> None:
        zsh_str = "/bin/zsh" if Path("/bin/zsh").is_file() else shutil.which("zsh")
        if not zsh_str:
            self.skipTest("zsh not available")
        zsh_bin = Path(zsh_str)
        launchers = (
            TRIAL_DIR / "FX6菜单.command",
            TRIAL_DIR / "FX3菜单.command",
            TRIAL_DIR / "FX3菜单TRY2.command",
            FX3_VM_DIR / "启动FX3最小研究虚拟机.command",
        )
        for launcher in launchers:
            self.assertTrue(launcher.is_file(), msg=f"Missing launcher: {launcher}")
            txt = launcher.read_text(encoding="utf-8")
            self.assertIn("FX3_PYTHON", txt, msg=f"{launcher.name} missing dynamic Python 3 probe")
            if launcher.name in ("FX3菜单.command", "FX3菜单TRY2.command"):
                self.assertIn("AI-Workspace", txt, msg=f"{launcher.name} missing internal-disk AI-Workspace probe")
            proc = subprocess.run(
                [str(zsh_bin), "-n", str(launcher)],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, msg=f"zsh -n failed for {launcher.name}: {proc.stderr}")

        if not _force_clean_room():
            for launcher_name in ("FX3菜单.command", "FX6菜单.command"):
                proc = subprocess.run(
                    [str(TRIAL_DIR / launcher_name), "--check"],
                    capture_output=True,
                    text=True,
                    timeout=15,
                    check=False,
                )
                if proc.returncode != 0 and "找不到" in (proc.stdout + proc.stderr):
                    continue
                self.assertEqual(
                    proc.returncode,
                    0,
                    msg=f"{launcher_name} --check failed: {proc.stdout}\n{proc.stderr}",
                )


class TestPhase19LiveIconAndFreezeFixes(unittest.TestCase):
    """Offline tests for Phase 19 live icon blitting, LDEC GPE pool, GDB lock/resume, and APPFW_SEGV detection."""

    def test_ldec_gpe_pool_and_rb_channel_fix(self) -> None:
        grm_src = _strip_c_comments((TRIAL_DIR / "src" / "libgrm-fbinit25-542.c").read_text(encoding="utf-8"))
        for sym in (
            "#define FX6_GPE_POOL_PHYS_BASE 0x410524000UL",
            "#define FX6_GPE_POOL_BYTES     0x000940000UL",
            "gpe_zero_uc(",
            "gpe_pool_alloc(",
            "gpe_pool_free(",
            "_ZN3grm3bmp10BitmapImpl7destroyEi",
        ):
            self.assertIn(sym, grm_src)

        assist_src = _strip_c_comments((TRIAL_DIR / "src" / "fx6_next_stage_assist_log.c").read_text(encoding="utf-8"))
        px_body = _extract_c_function_body(assist_src, "fx6_px")
        self.assertIn("((uint32_t)c->b)", px_body)
        self.assertIn("((uint32_t)c->r << 16)", px_body)

    def test_gdb_lock_finally_continue_and_appfw_segv_status(self) -> None:
        runner_src = (TRIAL_DIR / "run_fx6_menu_trial.py").read_text(encoding="utf-8")
        for sym in (
            "self.gdb_lock = threading.Lock()",
            "def _gdb_pop_packets(",
            "def _gdb_drain_async(",
            "def _gdb_wait_stop_reply(",
            's.sendall(b"$c#63")',
            'stage = "CRASHED_APPFW_SEGV"',
        ):
            self.assertIn(sym, runner_src)

        # Verify _pack_newc_entry overlay round-trip without touching real donor CPIO
        payload = b"\x89UXC-ICON-TEST"
        overlay = (
            run_fx6_menu_trial._pack_newc_entry("usr/share/app/image_00_169.uxc", payload, mode=0o100644, ino=0x9001)
            + run_fx6_menu_trial._pack_newc_entry("TRAILER!!!", b"", mode=0, ino=0)
        )
        overlay += b"\x00" * ((-len(overlay)) % 512)
        with tempfile.TemporaryDirectory(prefix="fx6_phase19_test_") as td:
            wd = Path(td)
            cpio_path = wd / "overlay.cpio"
            cpio_path.write_bytes(overlay)
            with cpio_path.open("rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                recs = build_live700.scan_newc_cpio(mm)
            self.assertEqual([r["name"] for r in recs], ["usr/share/app/image_00_169.uxc", "TRAILER!!!"])
            r0 = recs[0]
            self.assertEqual(overlay[r0["offset"] : r0["offset"] + r0["bytes"]], payload)

            # Verify get_status() detects APPFW_SEGV and refuses to report LIVE_GPE0_READY
            sess = run_fx6_menu_trial.FX6LiveGpe0Session(wd / "sess")
            sess.live_ready = True
            sess.serial_log.write_text(
                "FX6_LIVE_READY seq=1 page=0 sel=5 cat=2 item=0 depth=0 nz=331776 text_ok=27 fill=38 icon=6\n"
                "APPFW_SEGV sig=11 addr=(nil) pc=0 sp=7f796d68b0\n",
                encoding="utf-8",
            )
            st = sess.get_status()
            self.assertFalse(st["live_ready"])
            self.assertTrue(st["crashed"])
            self.assertEqual(st["stage"], "CRASHED_APPFW_SEGV")
            self.assertIn("APPFW_SEGV sig=11", st["crash_reason"])


class TestPhase23MultilangFx3DeckAnd128Sweep(unittest.TestCase):
    """Phase 23 offline verification: port isolation, multi-lang .uxc packs, FX3 P10 deck, and 128-page sweep receipt."""

    def test_port_scoped_workdir_and_socket_isolation(self) -> None:
        default_wd = run_fx6_menu_trial.DEFAULT_WORKDIR
        self.assertEqual(run_fx6_menu_trial.resolve_port_scoped_workdir(8768, default_wd), default_wd)
        self.assertEqual(
            run_fx6_menu_trial.resolve_port_scoped_workdir(18770, default_wd),
            Path(f"{default_wd}-18770"),
        )
        custom_wd = Path("/tmp/custom-fx6-workdir")
        self.assertEqual(run_fx6_menu_trial.resolve_port_scoped_workdir(18770, custom_wd), custom_wd)

        with tempfile.TemporaryDirectory(prefix="fx6_port_iso_") as td:
            base_wd = Path(td) / "fx6-live-gpe0-run"
            s_8768 = run_fx6_menu_trial.FX6LiveGpe0Session(base_wd, port=8768)
            s_18770 = run_fx6_menu_trial.FX6LiveGpe0Session(base_wd, port=18770)
            self.assertEqual(s_8768.workdir, base_wd)
            self.assertEqual(s_18770.workdir, base_wd)
            self.assertNotEqual(s_8768.qmp_sock, s_18770.qmp_sock)
            self.assertNotEqual(s_8768.gdb_sock, s_18770.gdb_sock)
            self.assertIn("18770-", s_18770.qmp_sock.name)
            self.assertIn("18770-", s_18770.gdb_sock.name)

    def test_lang_pack_metadata_normalization_and_clean_room_discovery(self) -> None:
        self.assertEqual(set(run_fx6_menu_trial.LANG_PACKS.keys()), {"en", "zh", "ja"})
        self.assertEqual(run_fx6_menu_trial.LANG_PACKS["en"]["bank"], 4)
        self.assertEqual(run_fx6_menu_trial.LANG_PACKS["zh"]["bank"], 19)
        self.assertEqual(run_fx6_menu_trial.LANG_PACKS["ja"]["bank"], 12)
        self.assertEqual(run_fx6_menu_trial.LANG_PACKS["en"]["font_ns"], "0x0200a005")
        self.assertEqual(run_fx6_menu_trial.LANG_PACKS["zh"]["font_ns"], "0x0200a01c")
        self.assertEqual(run_fx6_menu_trial.LANG_PACKS["ja"]["font_ns"], "0x0200a006")

        norm = run_fx6_menu_trial.FX6LiveGpe0Session._normalize_lang
        for raw, exp in (
            ("en", "en"),
            ("English", "en"),
            ("0", "en"),
            ("zh", "zh"),
            ("zh-CN", "zh"),
            ("schinese", "zh"),
            ("simplifiedchinese", "zh"),
            ("1", "zh"),
            ("ja", "ja"),
            ("japanese", "ja"),
            ("2", "ja"),
        ):
            self.assertEqual(norm(raw), exp)
        self.assertIsNone(norm("klingon"))

        packs = run_fx6_menu_trial.discover_available_lang_packs()
        self.assertEqual(set(packs.keys()), {"en", "zh", "ja"})
        self.assertTrue(packs["en"]["available"])
        self.assertIsInstance(packs["zh"]["available"], bool)

    def test_donor_overlay_readonly_resolution_and_newc_staging_mock(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_donor_mock_") as td:
            donor_dir = Path(td) / "donor_app"
            donor_dir.mkdir(parents=True)
            sample_assets = {
                "image_00_169.uxc": b"UXC_ICON_MOCK_DATA",
                "string_simplifiedchinese_2.uxc": b"UXC_ZH_MOCK_DATA",
                "MYingHeiC-GB18030-SJ_wIcon.ltt": b"LTT_CJK_FONT_MOCK",
                "string_japanese_2.uxc": b"UXC_JA_MOCK_DATA",
            }
            for fname, payload in sample_assets.items():
                fp = donor_dir / fname
                fp.write_bytes(payload)
                os.chmod(fp, 0o444)

            orig_resolver = run_fx6_menu_trial._resolve_donor_app_dir
            try:
                run_fx6_menu_trial._resolve_donor_app_dir = lambda: donor_dir
                assets = run_fx6_menu_trial._resolve_donor_overlay_assets()
                self.assertEqual(
                    set(assets.keys()),
                    {
                        "usr/share/app/image_00_169.uxc",
                        "usr/share/app/string_simplifiedchinese_2.uxc",
                        "usr/share/app/MYingHeiC-GB18030-SJ_wIcon.ltt",
                        "usr/share/app/string_japanese_2.uxc",
                    },
                )
                packs = run_fx6_menu_trial.discover_available_lang_packs()
                self.assertTrue(packs["en"]["available"])
                self.assertTrue(packs["zh"]["available"])
                self.assertTrue(packs["ja"]["available"])
                for cpio_name, src_path in assets.items():
                    self.assertEqual(
                        run_fx6_menu_trial._read_file_readonly(src_path),
                        sample_assets[Path(cpio_name).name],
                    )
            finally:
                run_fx6_menu_trial._resolve_donor_app_dir = orig_resolver

    def test_guest_c_multilang_bank_switching_and_icon_cache_invariants(self) -> None:
        guest_code = _strip_c_comments((TRIAL_DIR / "src" / "fx6_live_guest.c").read_text(encoding="utf-8"))
        self.assertIn("switchBank", guest_code)
        self.assertIn("setFontNameWithNamespace", guest_code)
        self.assertIn("mb[16]", guest_code)
        self.assertIn("mb[17]", guest_code)
        self.assertIn("FX6_ICON_CACHE_MAX", guest_code)
        self.assertIn("FX6_ICON_SLAB_BYTES", guest_code)

        font_ns_body = _extract_c_function_body(guest_code, "fx6_font_ns_rid")
        self.assertIn("0x0200a01cU", font_ns_body)
        self.assertIn("0x0200a006U", font_ns_body)
        self.assertIn("0x0200a005U", font_ns_body)

        apply_lang_body = _extract_c_function_body(guest_code, "fx6_apply_lang")
        self.assertIn("bank = 19u;", apply_lang_body)
        self.assertIn("bank = 12u;", apply_lang_body)
        self.assertIn("g_syms.switchBank(1, bank);", apply_lang_body)
        self.assertIn("g_syms.switchBank(2, bank);", apply_lang_body)

        hash_body = _extract_c_function_body(guest_code, "fx6_state_hash")
        self.assertIn("(h ^ lang)", hash_body)

        # Ensure icon cache lookup runs inside fx6_icon_blit without per-draw calloc/malloc/dlsym
        icon_blit_body = _extract_c_function_body(guest_code, "fx6_icon_blit")
        self.assertIn("fx6_icon_cache_find(img)", icon_blit_body)
        self.assertIn("fx6_blit_cached_icon_to_osd(", icon_blit_body)
        for fn_name in ("fx6_icon_cache_find", "fx6_icon_cache_put", "fx6_blit_cached_icon_to_osd"):
            b = _extract_c_function_body(guest_code, fn_name)
            self.assertNotIn("calloc(", b)
            self.assertNotIn("malloc(", b)
            self.assertNotIn("dlsym(", b)

    def test_gpe_pool_lru_eviction_and_exception_monitor_crash_detection(self) -> None:
        grm_src = _strip_c_comments((TRIAL_DIR / "src" / "libgrm-fbinit25-542.c").read_text(encoding="utf-8"))
        for sym in (
            "gpe_coalesce_idx_locked(",
            "gpe_pool_alloc_for(",
            "gpe_pool_free_for(",
            "FX6_GPE_POOL_EVICT",
            "void *owner;",
        ):
            self.assertIn(sym, grm_src)

        with tempfile.TemporaryDirectory(prefix="fx6_exc_mon_") as td:
            sess = run_fx6_menu_trial.FX6LiveGpe0Session(Path(td) / "sess", port=18770)
            sess.live_ready = True
            sess.serial_log.write_text(
                "FX6_LIVE_FRAME seq=10 page=0 sel=5 cat=2 item=0 depth=0 nz=331776 text_ok=24 fill=38 icon=6 lang=0\n"
                "[Exception Syndrome]\n"
                "Abort (PC=0x7f8b31507c)\n"
                "Entering exception monitor.\n",
                encoding="utf-8",
            )
            st = sess.get_status()
            self.assertFalse(st["live_ready"])
            self.assertTrue(st["crashed"])
            self.assertEqual(st["stage"], "CRASHED_EXCEPTION_MONITOR")
            self.assertIn("Entering exception monitor", st["crash_reason"])

    def test_fx3_physical_button_deck_p10_mapping_and_transitions(self) -> None:
        btn_map = run_fx6_menu_trial.FX3_BUTTON_MAP
        expected_btns = {
            "FN", "MENU", "DISP", "C1", "C2", "C3", "C4", "C5", "C6",
            "WHEEL_UP", "WHEEL_DOWN", "WHEEL_SET", "BACK",
        }
        self.assertEqual(set(btn_map.keys()), expected_btns)
        for name, spec in btn_map.items():
            self.assertRegex(spec["phy_code"], r"^0x[0-9a-fA-F]{4}$", msg=name)
            self.assertRegex(spec["infra_code"], r"^0x[0-9a-fA-F]{4}$", msg=name)
            self.assertRegex(spec["p10_code"], r"^0x[0-9a-fA-F]{4}$", msg=name)
            self.assertTrue(spec["p10_symbol"], msg=name)

        with tempfile.TemporaryDirectory(prefix="fx6_btn_test_") as td:
            sess = run_fx6_menu_trial.FX6LiveGpe0Session(Path(td) / "sess", port=18770)
            # DISP cycles Viewfinder HUD p16 <-> HUD Strip p6
            r_disp1 = sess.press_fx3_button("DISP")
            self.assertTrue(r_disp1["ok"])
            self.assertEqual(sess.page, 16)
            self.assertEqual(r_disp1["p10_telemetry"]["phy_code"], "0x0025")
            self.assertEqual(r_disp1["p10_telemetry"]["infra_code"], "0x70ec")
            r_disp2 = sess.press_fx3_button("DISP")
            self.assertEqual(sess.page, 6)
            self.assertEqual(r_disp2["status"]["page"], 6)

            # C1 -> Base Look/LUT (Page 1, cat=4, depth=2)
            r_c1 = sess.press_fx3_button("C1")
            self.assertEqual((sess.page, sess.menu_cat, sess.menu_depth), (1, 4, 2))
            self.assertEqual(sess.last_p10_hwcode, (0x001D << 16) | 0x0066)
            self.assertEqual(r_c1["p10_telemetry"]["p10_symbol"], "PF_K_KURU_PON")

            # C2 -> WB/Setting Center, C3 -> p17, C4 -> p13, C5 -> p4, C6 -> p14, FN -> p0
            sess.press_fx3_button("C2")
            self.assertEqual((sess.page, sess.sel_box), (3, 5))
            for btn, exp_page in (("C3", 17), ("C4", 13), ("C5", 4), ("C6", 14), ("PLAY", 14), ("FN", 0)):
                res = sess.press_fx3_button(btn)
                self.assertTrue(res["ok"])
                self.assertEqual(sess.page, exp_page)

            # Invalid button returns ok=False cleanly
            bad = sess.press_fx3_button("NON_EXISTENT")
            self.assertFalse(bad["ok"])

    def test_http_api_routes_lang_and_fx3_button_and_ui_elements(self) -> None:
        import threading
        import urllib.error
        import urllib.request
        from http.server import ThreadingHTTPServer

        with tempfile.TemporaryDirectory(prefix="fx6_http_test_") as td:
            donor_dir = Path(td) / "donor_app"
            donor_dir.mkdir(parents=True)
            for fname in ("image_00_169.uxc", "string_simplifiedchinese_2.uxc", "MYingHeiC-GB18030-SJ_wIcon.ltt"):
                (donor_dir / fname).write_bytes(b"MOCK")

            orig_resolver = run_fx6_menu_trial._resolve_donor_app_dir
            run_fx6_menu_trial._resolve_donor_app_dir = lambda: donor_dir
            sess = run_fx6_menu_trial.FX6LiveGpe0Session(Path(td) / "sess", port=18770)
            srv = ThreadingHTTPServer(("127.0.0.1", 0), run_fx6_menu_trial.make_handler(sess))
            port = srv.server_address[1]
            t = threading.Thread(target=srv.serve_forever, daemon=True)
            t.start()
            try:
                base = f"http://127.0.0.1:{port}"
                html = urllib.request.urlopen(f"{base}/", timeout=5).read().decode("utf-8")
                self.assertIn("🌐 中文 / EN", html)
                self.assertIn("/api/lang", html)
                self.assertIn("/api/fx3_button", html)
                self.assertIn("ILME-FX3", html)

                gl = json.loads(urllib.request.urlopen(f"{base}/api/lang", timeout=5).read().decode("utf-8"))
                self.assertEqual(gl["current"], "en")
                self.assertIn("zh", gl["packs"])

                req_zh = urllib.request.Request(
                    f"{base}/api/lang",
                    data=json.dumps({"lang": "zh"}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                pl = json.loads(urllib.request.urlopen(req_zh, timeout=5).read().decode("utf-8"))
                self.assertTrue(pl["ok"])
                self.assertEqual(pl["lang"], "zh")
                self.assertEqual(pl["lang_id"], 1)

                req_btn = urllib.request.Request(
                    f"{base}/api/fx3_button",
                    data=json.dumps({"button": "C4"}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                pb = json.loads(urllib.request.urlopen(req_btn, timeout=5).read().decode("utf-8"))
                self.assertTrue(pb["ok"])
                self.assertEqual(pb["status"]["page"], 13)
                self.assertEqual(pb["p10_telemetry"]["phy_code"], "0x0026")

                req_bad = urllib.request.Request(
                    f"{base}/api/fx3_button",
                    data=json.dumps({"button": "BOGUS"}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with self.assertRaises(urllib.error.HTTPError) as ctx:
                    urllib.request.urlopen(req_bad, timeout=5)
                self.assertEqual(ctx.exception.code, 400)
            finally:
                srv.shutdown()
                srv.server_close()
                run_fx6_menu_trial._resolve_donor_app_dir = orig_resolver

    def test_mailbox_packing_contract_includes_lang_and_p10_telemetry(self) -> None:
        runner_src = (TRIAL_DIR / "run_fx6_menu_trial.py").read_text(encoding="utf-8")
        self.assertIn('struct.pack("<18I", *words)', runner_src)
        self.assertIn("self.lang_id,", runner_src)
        self.assertIn("self.last_p10_hwcode & 0xFFFFFFFF", runner_src)
        self.assertIn("signal.SIGTERM", runner_src)

    def test_phase23_128page_sweep_receipt_and_png_bounds(self) -> None:
        rep_dir = REPO_ROOT / "reports" / "2026-11-14-phase23-128page-multilang-fx3deck"
        receipt_path = rep_dir / "sweep_128_pages.json"
        if not receipt_path.is_file():
            self.skipTest("Phase 23 sweep receipt not yet generated")
        data = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(data["phase"], 23)
        self.assertEqual(data["port"], 18770)
        self.assertEqual(len(data["curated_24_pages"]), 24)
        self.assertGreaterEqual(len(data["lang_switches"]), 2)
        self.assertGreaterEqual(len(data["fx3_buttons"]), 13)
        self.assertEqual(len(data["pages_128"]), 128)
        self.assertEqual([p["idx"] for p in data["pages_128"]], list(range(128)))
        summary = data["summary"]
        self.assertEqual(summary["failures"], 0)
        self.assertFalse(summary["crashed"])
        self.assertTrue(summary["ack_matches_cmd"])
        self.assertEqual(summary["final_ack_seq"], summary["final_cmd_seq"])
        self.assertEqual(summary["nonzero_pages_128"], 128)
        self.assertGreaterEqual(summary["total_commands"], 155)
        self.assertTrue(any(ls.get("png_differs_from_en") for ls in data["lang_switches"]))

        pngs = sorted(rep_dir.glob("*.png"))
        self.assertLessEqual(len(pngs), 4)
        for png_p in pngs:
            raw = png_p.read_bytes()
            self.assertLess(len(raw), 300 * 1024, msg=f"PNG too large: {png_p.name}")
            chunks = _parse_png_chunks(raw)
            w, h = struct.unpack(">II", chunks[0][1][:8])
            self.assertEqual((w, h), (1024, 540), msg=f"Unexpected dimensions in {png_p.name}")


class TestPhase30CinemaLineParametersAndBridge(unittest.TestCase):
    def test_phase30_guest_c_cinema_line_specs_and_p4_nd_lock_invariants(self) -> None:
        guest_src = (TRIAL_DIR / "src" / "fx6_live_guest.c").read_text(encoding="utf-8")
        for token in (
            '"23.98p"',
            '"119.88p (S&Q)"',
            '"800 EI (800 Base)"',
            '"12800 EI (12800 Base)"',
            r'"180.0\xc2\xb0"',
            '"1/48"',
            '"Clear [FX3 P4 Locked]"',
            '"S-Cinetone"',
            '"S-Log3.Cine / S-Gamut3.Cine"',
            r'"User1 (33\xc2\xb3 .cube)"',
            '"5600K"',
            '"ATW"',
            "g_live_ibis_xlr",
            "fx6_render_string_text",
            "fx6_hud_live_str",
            "g_live_cells[3] = 0u;",
            "mb[18]",
        ):
            self.assertIn(token, guest_src, msg=f"Missing Phase 30 token in fx6_live_guest.c: {token}")
        # Ensure P4 ND lock on mb[11] does not corrupt Page 24 Universal dual-table slots
        self.assertIn("if ((page % FX6_NUM_PAGES) != 24u)", guest_src)
        self.assertIn("mb[8 + 3] = 0u;", guest_src)

    def test_phase30_cinema_param_presets_and_dual_base_iso_stepping(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p30_params_") as td:
            sess = run_fx6_menu_trial.FX6LiveGpe0Session(Path(td) / "sess", port=18771)
            cp0 = sess.get_cinema_params()
            self.assertEqual(cp0["base_iso"], "800")
            self.assertEqual(cp0["values"]["fps"], "23.98p")
            self.assertEqual(cp0["values"]["ei"], "800 EI (800 Base)")
            self.assertEqual(cp0["values"]["shutter"], "180.0°")
            self.assertEqual(cp0["values"]["lut"], "S-Cinetone")
            self.assertEqual(cp0["values"]["wb"], "5600K")

            # Step FPS to 119.88p (S&Q) and EI to 12800 Dual Base ISO
            r_fps = sess.set_cinema_param("fps", preset="119.88p (S&Q)")
            self.assertTrue(r_fps["ok"])
            self.assertEqual(r_fps["value"], "119.88p (S&Q)")
            self.assertEqual(sess.cell_vals[0], 6)

            r_ei = sess.set_cinema_param("ei", preset="12800 EI (12800 Base)")
            self.assertTrue(r_ei["ok"])
            self.assertEqual(r_ei["cinema_params"]["base_iso"], "12800")
            self.assertEqual(sess.cell_vals[1], 3)

            # Shutter angle -> 1/48
            r_sh = sess.set_cinema_param("shutter", preset="1/48")
            self.assertTrue(r_sh["ok"])
            self.assertEqual(r_sh["value"], "1/48")
            self.assertEqual(sess.cell_vals[2], 4)

            # LUT -> User1 (33³ .cube) via delta/preset
            r_lut = sess.set_cinema_param("lut", preset="User1 (33³ .cube)")
            self.assertTrue(r_lut["ok"])
            self.assertEqual(sess.cell_vals[4], 4)

            # WB -> ATW, then step backward with delta=-1 -> 3200K
            r_wb = sess.set_cinema_param("wb", preset="ATW")
            self.assertTrue(r_wb["ok"])
            r_wb_back = sess.set_cinema_param("wb", delta=-1)
            self.assertTrue(r_wb_back["ok"])
            self.assertEqual(r_wb_back["value"], "3200K")

            # IBIS & XLR cycling
            r_ibis = sess.set_cinema_param("ibis", delta=1)
            self.assertTrue(r_ibis["ok"])
            self.assertEqual(sess.ibis_idx, 1)
            r_xlr = sess.set_cinema_param("xlr", delta=2)
            self.assertTrue(r_xlr["ok"])
            self.assertEqual(sess.xlr_idx, 2)

            # Invalid param & preset fail cleanly
            self.assertFalse(sess.set_cinema_param("bogus_param")["ok"])
            self.assertFalse(sess.set_cinema_param("fps", preset="999p")["ok"])

    def test_phase30_p4_nd_clear_hardware_lock_enforcement(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p30_p4_") as td:
            sess = run_fx6_menu_trial.FX6LiveGpe0Session(Path(td) / "sess", port=18771)
            r1 = sess.set_cinema_param("nd", delta=1)
            self.assertTrue(r1["ok"])
            self.assertTrue(r1["locked"])
            self.assertEqual(r1["value"], "Clear [FX3 P4 Locked]")
            self.assertEqual(sess.cell_vals[3], 0)
            self.assertEqual(sess.p4_lock_attempts, 1)
            self.assertIn("P4", r1["toast"])
            self.assertIn("Clear", r1["toast"])

            # Attempt forcing non-Clear preset -> clamped to Clear
            r2 = sess.set_cinema_param("nd", preset="1/16 ND")
            self.assertTrue(r2["ok"])
            self.assertEqual(r2["value"], "Clear [FX3 P4 Locked]")
            self.assertEqual(sess.cell_vals[3], 0)
            self.assertEqual(sess.p4_lock_attempts, 2)

            # Pressing SET on Big-6 cell 3 (ND Filter) enforces P4 lock & triggers toast
            sess.apply_key_or_state({"page": 0, "sel_box": 3})
            r3 = sess.apply_key_or_state({"key": "SET"})
            self.assertTrue(r3["ok"])
            self.assertEqual(sess.cell_vals[3], 0)
            self.assertEqual(sess.p4_lock_attempts, 3)
            self.assertIn("P4", r3["status"]["last_toast"])

    def test_phase30_stage_b_telemetry_contract_p1_p4_p10_p11_p12(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p30_tel_") as td:
            sess = run_fx6_menu_trial.FX6LiveGpe0Session(Path(td) / "sess", port=18771)
            sess.set_cinema_param("ei", preset="12800 EI (12800 Base)")
            sess.set_cinema_param("lut", preset="S-Log3.Cine / S-Gamut3.Cine")
            sess.set_cinema_param("nd", delta=1)
            sess.press_fx3_button("C1")
            st = sess.get_status()
            sbt = st["stage_b_telemetry"]
            self.assertEqual(set(sbt.keys()), {"P1", "P4", "P10", "P11", "P12"})
            self.assertIn("P1 (/lut->p30)", sbt["P1"]["label"])
            self.assertTrue(sbt["P4"]["locked"])
            self.assertGreaterEqual(sbt["P4"]["attempts"], 1)
            self.assertEqual(sbt["P11"]["base_iso"], "12800")
            self.assertEqual(sbt["P11"]["xlr_handle"], "0x5d90")
            self.assertEqual(sbt["P11"]["lut_dma"], "0x0165/0x0166")
            self.assertTrue(sbt["P12"]["safe"])

    def test_phase30_http_api_cinema_param_and_web_telemetry_strip(self) -> None:
        import threading
        import urllib.error
        import urllib.request
        from http.server import ThreadingHTTPServer

        with tempfile.TemporaryDirectory(prefix="fx6_p30_http_") as td:
            sess = run_fx6_menu_trial.FX6LiveGpe0Session(Path(td) / "sess", port=18771)
            srv = ThreadingHTTPServer(("127.0.0.1", 0), run_fx6_menu_trial.make_handler(sess))
            port = srv.server_address[1]
            t = threading.Thread(target=srv.serve_forever, daemon=True)
            t.start()
            try:
                base = f"http://127.0.0.1:{port}"
                html = urllib.request.urlopen(f"{base}/", timeout=5).read().decode("utf-8")
                for ui_tok in (
                    "/api/cinema_param",
                    "P1 (/lut-&gt;p30)" if False else "P1 (/lut->p30)",
                    "P4 (ND=Clear)",
                    "P10 (FX3 Keys)",
                    "P11 (Base ISO 800/12800 + 33³ LUT + XLR-H1 + IBIS Lock)",
                    "P12 (WF-12 Safe)",
                    "param-toast",
                    "setLang('ja')",
                ):
                    self.assertIn(ui_tok, html)

                g0 = json.loads(urllib.request.urlopen(f"{base}/api/cinema_param", timeout=5).read().decode("utf-8"))
                self.assertTrue(g0["ok"])
                self.assertEqual(g0["cinema_params"]["values"]["ei"], "800 EI (800 Base)")

                req_post = urllib.request.Request(
                    f"{base}/api/cinema_param",
                    data=json.dumps({"param": "ei", "preset": "12800 EI (12800 Base)"}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                p_res = json.loads(urllib.request.urlopen(req_post, timeout=5).read().decode("utf-8"))
                self.assertTrue(p_res["ok"])
                self.assertEqual(p_res["cinema_params"]["base_iso"], "12800")

                # Query string support for quick curl/GET-style POST invocations
                req_qs = urllib.request.Request(
                    f"{base}/api/cinema_param?param=nd&delta=1",
                    data=b"{}",
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                nd_res = json.loads(urllib.request.urlopen(req_qs, timeout=5).read().decode("utf-8"))
                self.assertTrue(nd_res["ok"])
                self.assertTrue(nd_res["locked"])
                self.assertEqual(nd_res["value"], "Clear [FX3 P4 Locked]")

                req_bad = urllib.request.Request(
                    f"{base}/api/cinema_param",
                    data=json.dumps({"param": "invalid_param"}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with self.assertRaises(urllib.error.HTTPError) as ctx:
                    urllib.request.urlopen(req_bad, timeout=5)
                self.assertEqual(ctx.exception.code, 400)
            finally:
                srv.shutdown()
                srv.server_close()

    def test_phase30_mailbox_p11_word18_packing_and_p4_nd_guard(self) -> None:
        runner_src = (TRIAL_DIR / "run_fx6_menu_trial.py").read_text(encoding="utf-8")
        self.assertIn("p11_state_word = ((self.xlr_idx & 0x0F) << 4) | (self.ibis_idx & 0x0F)", runner_src)
        self.assertIn('struct.pack("<18I", *words) + struct.pack("<I", p11_state_word)', runner_src)
        self.assertIn("mb_vals[3] = 0", runner_src)

    def test_phase30_multilang_and_fx3_deck_cinema_param_sync(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p30_fx3deck_") as td:
            donor_dir = Path(td) / "donor_app"
            donor_dir.mkdir(parents=True)
            for fname in (
                "image_00_169.uxc",
                "string_simplifiedchinese_2.uxc",
                "string_japanese_2.uxc",
                "MYingHeiC-GB18030-SJ_wIcon.ltt",
                "TBGothicR_212_67_wIcon.ltt",
            ):
                (donor_dir / fname).write_bytes(b"MOCK")

            orig_resolver = run_fx6_menu_trial._resolve_donor_app_dir
            run_fx6_menu_trial._resolve_donor_app_dir = lambda: donor_dir
            try:
                sess = run_fx6_menu_trial.FX6LiveGpe0Session(Path(td) / "sess", port=18771)
                self.assertTrue(sess.set_lang("zh")["ok"])
                self.assertTrue(sess.set_lang("ja")["ok"])
                self.assertTrue(sess.set_lang("en")["ok"])

                # C1 enters Base Look / 3D LUT and steps cell_vals[4]
                sess.press_fx3_button("C1")
                self.assertEqual((sess.page, sess.menu_cat, sess.menu_depth), (1, 4, 2))
                sess.press_fx3_button("C1")
                self.assertEqual(sess.cell_vals[4], 1)

                # C2 jumps to Setting Center cell 5 (WB) and steps cell_vals[5]
                sess.press_fx3_button("C2")
                self.assertEqual((sess.page, sess.sel_box), (3, 5))
                sess.press_fx3_button("C2")
                self.assertEqual(sess.cell_vals[5], 1)

                # FN returns to Big-6 Home focused on Base Look / 3D LUT (cell 4)
                sess.press_fx3_button("FN")
                self.assertEqual((sess.page, sess.sel_box), (0, 4))
            finally:
                run_fx6_menu_trial._resolve_donor_app_dir = orig_resolver

    def test_phase30_stress_receipt_and_png_bounds(self) -> None:
        rep_dir = REPO_ROOT / "reports" / "2026-11-14-phase30-cineei-lut-nd-interactive-trial"
        receipt_path = rep_dir / "cinema_param_stress_receipt.json"
        if not receipt_path.is_file():
            self.skipTest("Phase 30 stress receipt not yet generated")
        data = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(data["phase"], 30)
        self.assertEqual(data["port"], 18771)
        summary = data["summary"]
        self.assertGreaterEqual(summary["total_commands"], 100)
        self.assertEqual(summary["failures"], 0)
        self.assertFalse(summary["crashed"])
        self.assertTrue(summary["ack_matches_cmd"])
        self.assertEqual(summary["final_ack_seq"], summary["final_cmd_seq"])
        self.assertTrue(summary["nd_locked"])
        self.assertGreaterEqual(summary["p4_lock_attempts"], 1)
        for diff_name, diff_ok in data["pixel_diffs"].items():
            self.assertTrue(diff_ok, msg=f"Expected real pixel diff for {diff_name}")

        pngs = sorted(rep_dir.glob("*.png"))
        self.assertGreaterEqual(len(pngs), 1)
        self.assertLessEqual(len(pngs), 4)
        for png_p in pngs:
            raw = png_p.read_bytes()
            self.assertLess(len(raw), 300 * 1024, msg=f"PNG too large: {png_p.name}")
            chunks = _parse_png_chunks(raw)
            w, h = struct.unpack(">II", chunks[0][1][:8])
            self.assertEqual((w, h), (1024, 540), msg=f"Unexpected dimensions in {png_p.name}")


class TestPhase40CubeLutXlrAudioAndCamset(unittest.TestCase):
    @staticmethod
    def _build_mini_cube(
        size: int = 2,
        *,
        r_bias: float = 0.0,
        g_bias: float = 0.0,
        b_bias: float = 0.0,
        title: str = "MiniTest",
        domain_min: str = "0.0 0.0 0.0",
        domain_max: str = "1.0 1.0 1.0",
    ) -> str:
        lines = [f'TITLE "{title}"', f"LUT_3D_SIZE {size}", f"DOMAIN_MIN {domain_min}", f"DOMAIN_MAX {domain_max}"]
        denom = max(1, size - 1)
        for b in range(size):
            fb = b / denom
            for g in range(size):
                fg = g / denom
                for r in range(size):
                    fr = r / denom
                    lines.append(f"{fr + r_bias:.6f} {fg + g_bias:.6f} {fb + b_bias:.6f}")
        return "\n".join(lines) + "\n"

    def test_p40_01_builtin_cube_presets_17_and_33_generate_and_sanitize(self) -> None:
        self.assertEqual(
            set(run_fx6_menu_trial.BUILTIN_CUBE_PRESETS.keys()),
            {"709_typeA", "teal_orange", "film_2383", "slog3_bypass"},
        )
        for pid in ("709_typeA", "teal_orange", "film_2383", "slog3_bypass"):
            cube17 = run_fx6_menu_trial.generate_builtin_cube_lut(pid, size=17)
            san17 = run_fx6_menu_trial.validate_and_sanitize_cube_lut(cube17, name=pid)
            self.assertTrue(san17["ok"], msg=f"{pid} 17^3 failed: {san17}")
            self.assertEqual(san17["size"], 17)
            self.assertEqual(san17["triplets"], 17 ** 3)
            self.assertEqual(len(san17["sha256"]), 64)
            self.assertRegex(san17["tint_hex"], r"^#[0-9a-f]{6}$")

        cube33 = run_fx6_menu_trial.generate_builtin_cube_lut("709_typeA", size=33)
        san33 = run_fx6_menu_trial.validate_and_sanitize_cube_lut(cube33, name="Sony709_33")
        self.assertTrue(san33["ok"])
        self.assertEqual(san33["size"], 33)
        self.assertEqual(san33["triplets"], 33 ** 3)

    def test_p40_02_allow_mini_grid_default_false_and_true(self) -> None:
        mini = self._build_mini_cube(size=2)
        rej = run_fx6_menu_trial.validate_and_sanitize_cube_lut(mini, name="Mini2")
        self.assertFalse(rej["ok"])
        self.assertEqual(rej["error"], "unsupported_lut_3d_size")

        ok = run_fx6_menu_trial.validate_and_sanitize_cube_lut(mini, name="Mini2", allow_mini_grid=True)
        self.assertTrue(ok["ok"])
        self.assertEqual(ok["size"], 2)
        self.assertEqual(ok["triplets"], 8)

    def test_p40_03_trilinear_mid_gray_interpolation_math(self) -> None:
        # Linear cube with all values in [0, 1] mapping midpoint (0.5, 0.5, 0.5) -> (0.70, 0.40, 0.55)
        lines = ['TITLE "LinearTint"', "LUT_3D_SIZE 2", "DOMAIN_MIN 0.0 0.0 0.0", "DOMAIN_MAX 1.0 1.0 1.0"]
        for bi in (0, 1):
            for gi in (0, 1):
                for ri in (0, 1):
                    lines.append(f"{0.40 + 0.60 * ri:.6f} {0.10 + 0.60 * gi:.6f} {0.25 + 0.60 * bi:.6f}")
        res = run_fx6_menu_trial.validate_and_sanitize_cube_lut("\n".join(lines), allow_mini_grid=True)
        self.assertTrue(res["ok"])
        mr, mg, mb = res["mid_gray_rgb"]
        self.assertAlmostEqual(mr, 0.70, places=3)
        self.assertAlmostEqual(mg, 0.40, places=3)
        self.assertAlmostEqual(mb, 0.55, places=3)
        self.assertEqual(res["tint_rgb8"], [round(0.70 * 255), round(0.40 * 255), round(0.55 * 255)])

    def test_p40_04_cube_rejects_nan_and_inf_fail_closed(self) -> None:
        base_lines = run_fx6_menu_trial.generate_builtin_cube_lut("slog3_bypass", size=17).splitlines()
        for bad_tok in ("NaN", "nan", "inf", "-Inf", "+Infinity"):
            corrupt = list(base_lines)
            corrupt[-1] = f"{bad_tok} 0.5 0.5"
            res = run_fx6_menu_trial.validate_and_sanitize_cube_lut("\n".join(corrupt))
            self.assertFalse(res["ok"], msg=f"Should reject {bad_tok}")
            self.assertEqual(res["error"], "nan_or_inf_triplet")

    def test_p40_05_cube_rejects_1d_and_unsupported_sizes(self) -> None:
        bad_1d = "LUT_1D_SIZE 17\n" + ("0.5 0.5 0.5\n" * 17)
        r1 = run_fx6_menu_trial.validate_and_sanitize_cube_lut(bad_1d)
        self.assertFalse(r1["ok"])
        self.assertEqual(r1["error"], "unsupported_lut_1d_size")

        bad_size = self._build_mini_cube(size=5)
        r2 = run_fx6_menu_trial.validate_and_sanitize_cube_lut(bad_size)
        self.assertFalse(r2["ok"])
        self.assertEqual(r2["error"], "unsupported_lut_3d_size")

        missing_size = "TITLE \"NoSize\"\n0.0 0.0 0.0\n"
        r3 = run_fx6_menu_trial.validate_and_sanitize_cube_lut(missing_size)
        self.assertFalse(r3["ok"])
        self.assertEqual(r3["error"], "missing_lut_3d_size")

    def test_p40_06_cube_rejects_wrong_triplet_count_and_bad_rows(self) -> None:
        lines = run_fx6_menu_trial.generate_builtin_cube_lut("slog3_bypass", size=17).splitlines()
        too_few = "\n".join(lines[:-1])
        r1 = run_fx6_menu_trial.validate_and_sanitize_cube_lut(too_few)
        self.assertFalse(r1["ok"])
        self.assertEqual(r1["error"], "triplet_count_mismatch")

        too_many = "\n".join(lines + ["0.5 0.5 0.5"])
        r2 = run_fx6_menu_trial.validate_and_sanitize_cube_lut(too_many)
        self.assertFalse(r2["ok"])
        self.assertEqual(r2["error"], "triplet_count_mismatch")

        bad_cols = "\n".join(lines[:-1] + ["0.5 0.5"])
        r3 = run_fx6_menu_trial.validate_and_sanitize_cube_lut(bad_cols)
        self.assertFalse(r3["ok"])
        self.assertEqual(r3["error"], "invalid_row_or_keyword")

        bad_num = "\n".join(lines[:-1] + ["0.5 abc 0.5"])
        r4 = run_fx6_menu_trial.validate_and_sanitize_cube_lut(bad_num)
        self.assertFalse(r4["ok"])
        self.assertEqual(r4["error"], "invalid_row_or_keyword")

    def test_p40_07_cube_rejects_invalid_domains_and_late_headers(self) -> None:
        bad_dom = "LUT_3D_SIZE 2\nDOMAIN_MIN 0.8 0.0 0.0\nDOMAIN_MAX 0.5 1.0 1.0\n" + ("0.5 0.5 0.5\n" * 8)
        r1 = run_fx6_menu_trial.validate_and_sanitize_cube_lut(bad_dom, allow_mini_grid=True)
        self.assertFalse(r1["ok"])
        self.assertEqual(r1["error"], "invalid_domain_bounds")

        late_hdr = "LUT_3D_SIZE 2\n0.0 0.0 0.0\nTITLE \"Late\"\n" + ("0.5 0.5 0.5\n" * 7)
        r2 = run_fx6_menu_trial.validate_and_sanitize_cube_lut(late_hdr, allow_mini_grid=True)
        self.assertFalse(r2["ok"])
        self.assertEqual(r2["error"], "header_after_data")

        unk_hdr = "LUT_3D_SIZE 2\nWEIRD_DIRECTIVE 1\n" + ("0.5 0.5 0.5\n" * 8)
        r3 = run_fx6_menu_trial.validate_and_sanitize_cube_lut(unk_hdr, allow_mini_grid=True)
        self.assertFalse(r3["ok"])
        self.assertEqual(r3["error"], "invalid_row_or_keyword")

    def test_p40_08_cube_rejects_control_chars_traversal_and_oversize_lines(self) -> None:
        mini = self._build_mini_cube(size=2)
        r_nul = run_fx6_menu_trial.validate_and_sanitize_cube_lut(mini + "\x00", allow_mini_grid=True)
        self.assertFalse(r_nul["ok"])
        self.assertEqual(r_nul["error"], "control_characters_forbidden")

        r_trav = run_fx6_menu_trial.validate_and_sanitize_cube_lut(mini, name="../etc/passwd", allow_mini_grid=True)
        self.assertFalse(r_trav["ok"])
        self.assertEqual(r_trav["error"], "unsafe_lut_name")

        r_big = run_fx6_menu_trial.validate_and_sanitize_cube_lut("LUT_3D_SIZE 33\n" + ("# c\n" * 40050))
        self.assertFalse(r_big["ok"])
        self.assertEqual(r_big["error"], "too_many_lines")

        r_type = run_fx6_menu_trial.validate_and_sanitize_cube_lut(12345)  # type: ignore[arg-type]
        self.assertFalse(r_type["ok"])
        self.assertEqual(r_type["error"], "invalid_cube_type")

    def test_p40_09_cube_clamps_out_of_range_finite_values_with_domain_normalization(self) -> None:
        lines = [
            'TITLE "DomainClamp"',
            "LUT_3D_SIZE 2",
            "DOMAIN_MIN 0.0 0.0 0.0",
            "DOMAIN_MAX 2.0 2.0 2.0",
            "-0.50 -0.25 0.00",
            "2.50 0.50 0.50",
            "0.50 2.50 0.50",
            "1.00 1.00 0.50",
            "0.50 0.50 2.50",
            "1.00 0.50 1.00",
            "0.50 1.00 1.00",
            "2.50 2.50 2.50",
        ]
        res = run_fx6_menu_trial.validate_and_sanitize_cube_lut("\n".join(lines), allow_mini_grid=True)
        self.assertTrue(res["ok"])
        self.assertGreater(res["clamped_components"], 0)
        for v in res["mid_gray_rgb"]:
            self.assertGreaterEqual(v, 0.0)
            self.assertLessEqual(v, 1.0)

    def test_p40_10_user_slots_1_to_4_upload_and_select_cell4(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p40_slots_") as td:
            sess = run_fx6_menu_trial.FX6LiveGpe0Session(Path(td) / "sess", port=18772)
            for idx, (slot, pid) in enumerate(
                [("User1", "709_typeA"), ("User2", "teal_orange"), ("User3", "film_2383"), ("User4", "slog3_bypass")]
            ):
                r = sess.upload_cube_lut({"slot": slot, "preset": pid, "name": f"Slot{idx + 1}_{pid}"})
                self.assertTrue(r["ok"], msg=f"Upload failed for {slot}: {r}")
                self.assertEqual(r["slot"], slot)
                self.assertEqual(sess.cell_vals[4], 4 + idx)
                self.assertEqual(r["cinema_params"]["active_user_lut"]["slot"], slot)
                self.assertTrue(sess.user_lut_slots[slot]["uploaded"])

            bad_slot = sess.upload_cube_lut({"slot": "User5", "preset": "teal_orange"})
            self.assertFalse(bad_slot["ok"])
            self.assertEqual(bad_slot["error"], "invalid_lut_slot")
            # Active slot remained User4
            self.assertEqual(sess.cell_vals[4], 7)

    def test_p40_11_mailbox_packing_phase40_words_19_to_27(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p40_mb_") as td:
            sess = run_fx6_menu_trial.FX6LiveGpe0Session(Path(td) / "sess", port=18772)
            sess.upload_cube_lut({"slot": "User2", "preset": "teal_orange", "name": "TealOrange17"})
            sess.set_cinema_param("", payload={"ch1_db": -6, "ch2_db": 6, "ch3_db": -24, "ch4_db": -60, "xlr_handle_attached": True, "xlr_phantom_48v": False, "rtmd_0xe304_ibis_lock": "OFF_CENTER_LOCKED"})

            raw = sess._pack_mailbox_bytes()
            self.assertEqual(len(raw), 28 * 4)
            words = struct.unpack("<28I", raw)
            self.assertEqual(words[3], 0)  # P4 ND=Clear invariant
            self.assertEqual((words[18] >> 4) & 0x0F, sess.xlr_idx)
            self.assertEqual(words[18] & 0x0F, sess.ibis_idx)
            tint_r, tint_g, tint_b = sess.user_lut_slots["User2"]["tint_rgb8"]
            expected_meta = (2 << 28) | (1 << 24) | (tint_r << 16) | (tint_g << 8) | tint_b
            self.assertEqual(words[19], expected_meta)
            name_bytes = struct.pack("<6I", *words[20:26]).split(b"\x00", 1)[0].decode("ascii")
            self.assertEqual(name_bytes, "TealOrange17")
            ch_unpacked = [b - 60 for b in struct.unpack("<4B", struct.pack("<I", words[26]))]
            self.assertEqual(ch_unpacked, [-6, 6, -24, -60])
            flags = words[27]
            self.assertEqual(flags & 0x01, 1)  # attached
            self.assertEqual((flags >> 1) & 0x01, 0)  # +48V OFF
            self.assertEqual((flags >> 4) & 0x03, 1)  # OFF_CENTER_LOCKED

    def test_p40_12_guest_c_phase40_hud_and_no_malloc_invariants(self) -> None:
        c_src = (TRIAL_DIR / "src" / "fx6_live_guest.c").read_text(encoding="utf-8")
        for sym in (
            "fx6_render_phase40_hud_strip",
            "g_live_lut_meta",
            "g_live_audio_packed",
            "g_live_p40_flags",
            "User3 (33",
            "User4 (33",
            "E304:5AX",
            "E304:LOCK",
            "E304:STD",
        ):
            self.assertIn(sym, c_src)
        idx = c_src.index("static void fx6_render_phase40_hud_strip")
        end_idx = c_src.index("static uint64_t fx6_state_hash", idx)
        helper_body = c_src[idx:end_idx]
        for forbidden in ("malloc(", "calloc(", "realloc(", "dlsym("):
            self.assertNotIn(forbidden, helper_body)

    def test_p40_13_audio_4ch_trim_clamping_and_validation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p40_aud_") as td:
            sess = run_fx6_menu_trial.FX6LiveGpe0Session(Path(td) / "sess", port=18772)
            r1 = sess.set_cinema_param("", payload={"ch1_db": -99, "ch2_db": 40, "ch3_db": -3, "ch4_db": 0})
            self.assertTrue(r1["ok"])
            self.assertEqual(sess.audio_ch_db, [-60, 12, -3, 0])

            r_bool = sess.set_cinema_param("", payload={"ch1_db": True})
            self.assertFalse(r_bool["ok"])
            self.assertEqual(r_bool["error"], "invalid_audio_db")

            r_nan = sess.set_cinema_param("", payload={"ch2_db": float("nan")})
            self.assertFalse(r_nan["ok"])
            self.assertEqual(r_nan["error"], "invalid_audio_db")
            self.assertEqual(sess.audio_ch_db, [-60, 12, -3, 0])

    def test_p40_14_xlr_h1_detach_p11_0x91db059b_internal_stereo_fallback(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p40_xlr_") as td:
            sess = run_fx6_menu_trial.FX6LiveGpe0Session(Path(td) / "sess", port=18772)
            self.assertTrue(sess.xlr_handle_attached)
            self.assertTrue(sess.xlr_phantom_48v)

            r_det = sess.set_cinema_param("", payload={"xlr_handle_attached": False})
            self.assertTrue(r_det["ok"])
            self.assertFalse(sess.xlr_handle_attached)
            self.assertEqual(sess.xlr_idx, 2)
            self.assertEqual(r_det["cinema_params"]["values"]["xlr"], "Internal Stereo Mic")
            self.assertEqual(r_det["cinema_params"]["audio_route"], "INTERNAL_STEREO_FALLBACK")
            self.assertIn("0x91db059b", r_det["cinema_params"]["ch1_ch2_source"])
            sbt = sess.get_stage_b_telemetry()
            self.assertEqual(sbt["P11"]["audio_route"], "INTERNAL_STEREO_FALLBACK")
            self.assertEqual(sbt["P11"]["xlr_handle"], "0x5d90")
            self.assertEqual(sbt["P11"]["xlr_fallback_contract"], "0x91db059b")
            self.assertIn("0x91db059b", r_det["toast"])

            # Attempting +48V while detached keeps Internal Stereo fallback without crashing
            r_step = sess.set_cinema_param("xlr", delta=1)
            self.assertTrue(r_step["ok"])
            self.assertEqual(sess.xlr_idx, 2)

            # Re-attach restores XLR-H1
            r_att = sess.set_cinema_param("", payload={"xlr_handle_attached": True, "xlr_phantom_48v": True})
            self.assertTrue(r_att["ok"])
            self.assertTrue(sess.xlr_handle_attached)
            self.assertEqual(sess.xlr_idx, 0)
            self.assertEqual(sess.get_stage_b_telemetry()["P11"]["audio_route"], "XLR_H1_48V")

    def test_p40_15_rtmd_0xe304_ibis_mode_bidirectional_sync(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p40_rtmd_") as td:
            sess = run_fx6_menu_trial.FX6LiveGpe0Session(Path(td) / "sess", port=18772)
            r1 = sess.set_cinema_param("", payload={"rtmd_0xe304_ibis_lock": "OFF_CENTER_LOCKED"})
            self.assertTrue(r1["ok"])
            self.assertEqual(sess.rtmd_0xe304_ibis_lock, "OFF_CENTER_LOCKED")
            self.assertEqual(sess.ibis_idx, 1)
            self.assertEqual(r1["cinema_params"]["values"]["ibis"], "Active Off")

            r2 = sess.set_cinema_param("ibis", preset="Active Standard")
            self.assertTrue(r2["ok"])
            self.assertEqual(sess.rtmd_0xe304_ibis_lock, "STANDARD")
            self.assertEqual(sess.ibis_idx, 2)
            self.assertEqual(sess.get_stage_b_telemetry()["P11"]["rtmd_0xe304_ibis_lock"], "STANDARD")

            r_bad = sess.set_cinema_param("", payload={"rtmd_0xe304_ibis_lock": "WARP_9"})
            self.assertFalse(r_bad["ok"])
            self.assertEqual(r_bad["error"], "invalid_rtmd_0xe304_ibis_lock")

    def test_p40_16_camset_export_deterministic_sha256_and_schema(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p40_exp_") as td:
            sess = run_fx6_menu_trial.FX6LiveGpe0Session(Path(td) / "sess", port=18772)
            e1 = sess.export_camset_preset()
            e2 = sess.export_camset_preset()
            self.assertTrue(e1["ok"])
            self.assertEqual(e1["schema"], "fx6_on_fx3_camset_v1")
            self.assertEqual(e1["preset_sha256"], e2["preset_sha256"])
            self.assertEqual(len(e1["preset_sha256"]), 64)
            self.assertTrue(e1["p12_bk4_airplane_mode_locked"])

            sess.set_cinema_param("", payload={"ch1_db": -3})
            e3 = sess.export_camset_preset()
            self.assertNotEqual(e1["preset_sha256"], e3["preset_sha256"])

    def test_p40_17_camset_import_roundtrip_restores_full_state(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p40_rt_") as td:
            sess = run_fx6_menu_trial.FX6LiveGpe0Session(Path(td) / "sess", port=18772)
            sess.set_cinema_param("fps", preset="59.94p")
            sess.set_cinema_param("ei", preset="12800 EI (12800 Base)")
            sess.set_cinema_param("shutter", preset="1/100")
            sess.set_cinema_param("wb", preset="3200K")
            sess.upload_cube_lut({"slot": "User3", "preset": "film_2383", "name": "Film2383_P40"})
            sess.set_cinema_param("", payload={
                "ch1_db": -8,
                "ch2_db": -10,
                "ch3_db": -22,
                "ch4_db": -30,
                "xlr_handle_attached": False,
                "rtmd_0xe304_ibis_lock": "OFF_CENTER_LOCKED",
            })
            exported = sess.export_camset_preset()

            # Mutate everything to other settings
            sess.set_cinema_param("fps", preset="23.98p")
            sess.set_cinema_param("ei", preset="800 EI (800 Base)")
            sess.set_cinema_param("wb", preset="ATW")
            sess.upload_cube_lut({"slot": "User1", "preset": "slog3_bypass", "name": "Bypass"})
            sess.set_cinema_param("", payload={
                "ch1_db": 0,
                "ch2_db": 0,
                "xlr_handle_attached": True,
                "rtmd_0xe304_ibis_lock": "STANDARD",
            })

            imp = sess.import_camset_preset(exported)
            self.assertTrue(imp["ok"], msg=f"Import failed: {imp}")
            self.assertFalse(imp["p4_nd_rejected"])
            cp = imp["cinema_params"]["values"]
            self.assertEqual(cp["fps"], "59.94p")
            self.assertEqual(cp["ei"], "12800 EI (12800 Base)")
            self.assertEqual(cp["shutter"], "1/100")
            self.assertEqual(cp["wb"], "3200K")
            self.assertEqual(cp["lut"], "User3 (33³ .cube)")
            self.assertEqual(sess.audio_ch_db, [-8, -10, -22, -30])
            self.assertFalse(sess.xlr_handle_attached)
            self.assertEqual(sess.rtmd_0xe304_ibis_lock, "OFF_CENTER_LOCKED")
            self.assertEqual(sess.user_lut_slots["User3"]["name"], "Film2383_P40")

    def test_p40_18_camset_import_enforces_p4_nd_lock_and_p12_bk4_shadow(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p40_p4tamper_") as td:
            sess = run_fx6_menu_trial.FX6LiveGpe0Session(Path(td) / "sess", port=18772)
            camset = sess.export_camset_preset()
            camset["cinema_params"]["nd"] = "1/16 ND"
            camset["p12_bk4_airplane_mode_locked"] = False

            imp = sess.import_camset_preset(camset)
            self.assertTrue(imp["ok"])
            self.assertTrue(imp["p4_nd_rejected"])
            self.assertTrue(imp["p4_nd_clamped"])
            self.assertEqual(imp["p4_nd_reject_count"], 1)
            self.assertEqual(sess.p4_nd_reject_count, 1)
            self.assertEqual(sess.cell_vals[3], 0)
            self.assertEqual(imp["cinema_params"]["values"]["nd"], "Clear [FX3 P4 Locked]")
            self.assertTrue(imp["p12_bk4_airplane_mode_locked"])
            self.assertTrue(imp["p12_bk4_clamped"])
            self.assertTrue(sess.get_stage_b_telemetry()["P12"]["bk4_airplane_mode_locked"])

    def test_p40_19_camset_import_rejects_bad_schema_or_corrupt_cube_without_mutating(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p40_badcamset_") as td:
            sess = run_fx6_menu_trial.FX6LiveGpe0Session(Path(td) / "sess", port=18772)
            sess.set_cinema_param("fps", preset="59.94p")

            r_bad_schema = sess.import_camset_preset({"schema": "wrong_v99", "cinema_params": {"fps": "23.98p"}})
            self.assertFalse(r_bad_schema["ok"])
            self.assertEqual(r_bad_schema["error"], "invalid_camset_schema")
            self.assertEqual(sess.cell_vals[0], 5)  # unchanged 59.94p

            camset = sess.export_camset_preset()
            camset["cinema_params"]["fps"] = "23.98p"
            camset["user_lut_slots"]["User1"]["cube_text"] = "LUT_3D_SIZE 17\nNaN 0.0 0.0\n"
            r_bad_cube = sess.import_camset_preset(camset)
            self.assertFalse(r_bad_cube["ok"])
            self.assertEqual(sess.cell_vals[0], 5)  # still unchanged!

    def test_p40_20_http_api_lut_upload_and_malformed_json_400(self) -> None:
        import threading
        import urllib.error
        import urllib.request
        from http.server import ThreadingHTTPServer

        with tempfile.TemporaryDirectory(prefix="fx6_p40_http_lut_") as td:
            sess = run_fx6_menu_trial.FX6LiveGpe0Session(Path(td) / "sess", port=18772)
            srv = ThreadingHTTPServer(("127.0.0.1", 0), run_fx6_menu_trial.make_handler(sess))
            port = srv.server_address[1]
            t = threading.Thread(target=srv.serve_forever, daemon=True)
            t.start()
            try:
                base = f"http://127.0.0.1:{port}"
                g_slots = json.loads(urllib.request.urlopen(f"{base}/api/lut_upload", timeout=5).read().decode("utf-8"))
                self.assertTrue(g_slots["ok"])
                self.assertEqual(set(g_slots["slots"].keys()), {"User1", "User2", "User3", "User4"})

                # Built-in preset upload -> 200
                req1 = urllib.request.Request(
                    f"{base}/api/lut_upload",
                    data=json.dumps({"slot": "User1", "preset": "teal_orange"}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                r1 = json.loads(urllib.request.urlopen(req1, timeout=5).read().decode("utf-8"))
                self.assertTrue(r1["ok"])
                self.assertEqual(r1["lut"]["size"], 17)

                # Raw custom 17^3 .cube upload -> 200
                raw_cube = run_fx6_menu_trial.generate_builtin_cube_lut("film_2383", size=17)
                req2 = urllib.request.Request(
                    f"{base}/api/lut_upload",
                    data=json.dumps({"slot": "User2", "name": "Custom2383", "cube_text": raw_cube}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                r2 = json.loads(urllib.request.urlopen(req2, timeout=5).read().decode("utf-8"))
                self.assertTrue(r2["ok"])
                self.assertEqual(r2["lut"]["name"], "Custom2383")

                # Malformed .cube -> 400 with structured error
                req_bad_cube = urllib.request.Request(
                    f"{base}/api/lut_upload",
                    data=json.dumps({"slot": "User1", "cube_text": "LUT_3D_SIZE 17\nNaN 0.1 0.2\n"}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with self.assertRaises(urllib.error.HTTPError) as ctx_cube:
                    urllib.request.urlopen(req_bad_cube, timeout=5)
                self.assertEqual(ctx_cube.exception.code, 400)
                err_payload = json.loads(ctx_cube.exception.read().decode("utf-8"))
                self.assertFalse(err_payload["ok"])
                self.assertEqual(err_payload["error"], "nan_or_inf_triplet")

                # Malformed JSON -> 400
                req_bad_json = urllib.request.Request(
                    f"{base}/api/lut_upload",
                    data=b"{not-valid-json",
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with self.assertRaises(urllib.error.HTTPError) as ctx_json:
                    urllib.request.urlopen(req_bad_json, timeout=5)
                self.assertEqual(ctx_json.exception.code, 400)
            finally:
                srv.shutdown()
                srv.server_close()

    def test_p40_21_http_api_cinema_param_audio_rtmd_and_camset_endpoints(self) -> None:
        import threading
        import urllib.request
        from http.server import ThreadingHTTPServer

        with tempfile.TemporaryDirectory(prefix="fx6_p40_http_cam_") as td:
            sess = run_fx6_menu_trial.FX6LiveGpe0Session(Path(td) / "sess", port=18772)
            srv = ThreadingHTTPServer(("127.0.0.1", 0), run_fx6_menu_trial.make_handler(sess))
            port = srv.server_address[1]
            t = threading.Thread(target=srv.serve_forever, daemon=True)
            t.start()
            try:
                base = f"http://127.0.0.1:{port}"
                html = urllib.request.urlopen(f"{base}/", timeout=5).read().decode("utf-8")
                for marker in (
                    "/api/lut_upload",
                    "/api/preset_export",
                    "/api/preset_import",
                    "audio-ch1",
                    "rtmd-ibis-select",
                    "camset-lock-badge",
                    "🌐 中文 / EN",
                    "ILME-FX3",
                ):
                    self.assertIn(marker, html)

                req_cp = urllib.request.Request(
                    f"{base}/api/cinema_param",
                    data=json.dumps({
                        "ch1_db": -9,
                        "ch2_db": -9,
                        "ch3_db": -20,
                        "ch4_db": -20,
                        "xlr_handle_attached": False,
                        "rtmd_0xe304_ibis_lock": "OFF_CENTER_LOCKED",
                    }).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                cp_res = json.loads(urllib.request.urlopen(req_cp, timeout=5).read().decode("utf-8"))
                self.assertTrue(cp_res["ok"])
                self.assertFalse(cp_res["status"]["xlr_handle_attached"])
                self.assertEqual(cp_res["status"]["rtmd_0xe304_ibis_lock"], "OFF_CENTER_LOCKED")

                camset = json.loads(urllib.request.urlopen(f"{base}/api/preset_export", timeout=5).read().decode("utf-8"))
                self.assertEqual(camset["schema"], "fx6_on_fx3_camset_v1")
                camset["cinema_params"]["nd"] = "1/64 ND"

                req_imp = urllib.request.Request(
                    f"{base}/api/preset_import",
                    data=json.dumps(camset).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                imp_res = json.loads(urllib.request.urlopen(req_imp, timeout=5).read().decode("utf-8"))
                self.assertTrue(imp_res["ok"])
                self.assertTrue(imp_res["p4_nd_rejected"])
                self.assertEqual(imp_res["p4_nd_reject_count"], 1)
                self.assertEqual(imp_res["cinema_params"]["values"]["nd"], "Clear [FX3 P4 Locked]")
            finally:
                srv.shutdown()
                srv.server_close()

    def test_p40_22_phase40_report_receipts_when_present(self) -> None:
        rep_dir = REPO_ROOT / "reports" / "2026-11-14-phase40-vm-trial-cube-lut-xlr-presets"
        readme = rep_dir / "README.md"
        if not readme.is_file():
            self.skipTest("Phase 40 report README/receipts not yet generated")
        text = readme.read_text(encoding="utf-8")
        self.assertIn("18772", text)
        pngs = sorted(rep_dir.glob("*.png"))
        self.assertGreaterEqual(len(pngs), 1)
        self.assertLessEqual(len(pngs), 3)
        for png_p in pngs:
            raw = png_p.read_bytes()
            self.assertLess(len(raw), 90 * 1024, msg=f"Phase 40 PNG >= 90 KiB: {png_p.name} ({len(raw)} B)")
            chunks = _parse_png_chunks(raw)
            w, h = struct.unpack(">II", chunks[0][1][:8])
            self.assertEqual((w, h), (1024, 540), msg=f"Unexpected PNG size in {png_p.name}")


if __name__ == "__main__":
    unittest.main()
