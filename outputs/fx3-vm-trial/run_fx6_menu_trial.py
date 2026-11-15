#!/usr/bin/env python3
"""
Sony FX6 Authentic In-Guest Native GPE0 Menu Runner (Port 8768)
===============================================================
100% real in-guest rendering:
- Boots the FX3 QEMU ARM64 VM with the FX6 donor userland (`appFw.so` +
  `libuxengine.so` + `libgemini-grm.so` + `global.xdb` + `string_english_2.uxc`).
- All UI pages (Big-6 Home, Three-Layer Menu across all 11 categories,
  Setting Main, Setting Center, Assignable Button Page 110, Network Status,
  Viewfinder HUD Strip, Clip/Playback, Status/Grid) are rendered INSIDE the
  QEMU guest by `fx6_live_guest.c` into physical `0x41e001000` (`gpe0`).
- Zero fake Python/PIL UI drawing. Every frame displayed in the browser is a
  raw `0x41e001000` (`gpe0`, 1024x540x4) physical memory dump captured via QMP
  `pmemsave`.
"""

from __future__ import annotations

import argparse
import copy
import errno
import hashlib
import io
import json
import math
import os
import re
import signal
import socket
import struct
import subprocess
import sys
import threading
import time
import urllib.parse
import webbrowser
import xml.etree.ElementTree as ET
import zlib
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
TRIAL_DIR = REPO_ROOT / "outputs" / "fx3-vm-trial"
MANIFEST_PATH = TRIAL_DIR / "vm-candidate-gpecap25-live700.json"
FALLBACK_GPE0_PNG = REPO_ROOT / "reports" / "2026-11-08-fx6-native-text-gpe0" / "menu-677-big6-framed.png"
DEFAULT_PORT = 8768
DEFAULT_WORKDIR = Path("/private/tmp/fx6-live-gpe0-run")

GPE0_PHYS = 0x41E001000
GPE0_BYTES = 0x21C000  # 1024 * 540 * 4
GPE0_W = 1024
GPE0_H = 540

KEY_MB_PHYS = 0x41DF00000
CTRL_MB_PHYS = 0x41E000E00
CTRL_MAGIC = 0x4658364C  # 'FX6L'

KEY_CODES = {
    "UP": 1,
    "DOWN": 2,
    "LEFT": 3,
    "RIGHT": 4,
    "SET": 5,
    "ENTER": 5,
    "BACK": 6,
    "CANCEL": 6,
    "MENU": 7,
    "HOME": 8,
    "DISP": 9,
}

LANG_PACKS: dict[str, dict[str, Any]] = {
    "en": {
        "id": 0,
        "code": "en",
        "label": "English",
        "short": "EN",
        "bank": 4,
        "font_ns": "0x0200a005",
        "font_name": "FONT_UNIVERS",
        "uxc_files": ("string_english.uxc", "string_english_2.uxc"),
        "required_donor_files": (),
    },
    "zh": {
        "id": 1,
        "code": "zh",
        "label": "简体中文",
        "short": "中文",
        "bank": 19,
        "font_ns": "0x0200a01c",
        "font_name": "FONT_S_CHINESE",
        "uxc_files": ("string_simplifiedchinese.uxc", "string_simplifiedchinese_2.uxc"),
        "required_donor_files": (
            "string_simplifiedchinese_2.uxc",
            "MYingHeiC-GB18030-SJ_wIcon.ltt",
        ),
    },
    "ja": {
        "id": 2,
        "code": "ja",
        "label": "日本語",
        "short": "JA",
        "bank": 12,
        "font_ns": "0x0200a006",
        "font_name": "FONT_JAPANESE",
        "uxc_files": ("string_japanese.uxc", "string_japanese_2.uxc"),
        "required_donor_files": (
            "string_japanese_2.uxc",
        ),
    },
}

FX3_BUTTON_MAP: dict[str, dict[str, Any]] = {
    "FN": {
        "button": "FN",
        "label": "Fn -> Big-6 Home",
        "phy_code": "0x0013",
        "infra_code": "0x7095",
        "p10_code": "0x0184",
        "p10_symbol": "PF_K_HOME",
        "kind": "home",
    },
    "MENU": {
        "button": "MENU",
        "label": "MENU -> 3-Layer Menu",
        "phy_code": "0x0011",
        "infra_code": "0x01ab",
        "p10_code": "0x01ab",
        "p10_symbol": "UIBIZ_KEY_TACT_MENU",
        "kind": "key",
        "key": "MENU",
    },
    "DISP": {
        "button": "DISP",
        "label": "DISP -> Viewfinder p16/p6 Cycle",
        "phy_code": "0x0025",
        "infra_code": "0x70ec",
        "p10_code": "0x0199",
        "p10_symbol": "PF_K_DISP_SEL",
        "kind": "disp_cycle",
    },
    "C1": {
        "button": "C1",
        "label": "C1 -> Base Look / LUT",
        "phy_code": "0x001d",
        "infra_code": "0x0066",
        "p10_code": "0x0029",
        "p10_symbol": "PF_K_KURU_PON",
        "kind": "c1_baselook",
    },
    "C2": {
        "button": "C2",
        "label": "C2 -> White Balance / Setting",
        "phy_code": "0x0024",
        "infra_code": "0x70e7",
        "p10_code": "0x0192",
        "p10_symbol": "PF_K_MENU_CANCEL",
        "kind": "c2_wb",
    },
    "C3": {
        "button": "C3",
        "label": "C3 -> Audio / TC Status p17",
        "phy_code": "0x0025",
        "infra_code": "0x70ec",
        "p10_code": "0x0199",
        "p10_symbol": "PF_K_DISP_SEL",
        "kind": "page",
        "page": 17,
    },
    "C4": {
        "button": "C4",
        "label": "C4 -> Media Status SSA/SSB p13",
        "phy_code": "0x0026",
        "infra_code": "0x70ed",
        "p10_code": "0x018a",
        "p10_symbol": "PF_K_SLOT_SEL",
        "kind": "page",
        "page": 13,
    },
    "C5": {
        "button": "C5",
        "label": "C5 -> Assignable p4",
        "phy_code": "0x000c",
        "infra_code": "0x01f8",
        "p10_code": "0x0185",
        "p10_symbol": "PF_K_USER",
        "kind": "page",
        "page": 4,
    },
    "C6": {
        "button": "C6",
        "label": "C6 / PLAY -> Clip Browser p14",
        "phy_code": "0x000b",
        "infra_code": "0x01f7",
        "p10_code": "0x0183",
        "p10_symbol": "PF_K_THUMBNAIL",
        "kind": "page",
        "page": 14,
    },
    "WHEEL_UP": {
        "button": "WHEEL_UP",
        "label": "WHEEL UP",
        "phy_code": "0x0003",
        "infra_code": "0x7081",
        "p10_code": "0x0171",
        "p10_symbol": "PF_K_UP",
        "kind": "key",
        "key": "UP",
    },
    "WHEEL_DOWN": {
        "button": "WHEEL_DOWN",
        "label": "WHEEL DOWN",
        "phy_code": "0x0030",
        "infra_code": "0x7082",
        "p10_code": "0x0172",
        "p10_symbol": "PF_K_DOWN",
        "kind": "key",
        "key": "DOWN",
    },
    "WHEEL_SET": {
        "button": "WHEEL_SET",
        "label": "WHEEL SET",
        "phy_code": "0x001c",
        "infra_code": "0x01ac",
        "p10_code": "0x01ac",
        "p10_symbol": "PF_K_SET",
        "kind": "key",
        "key": "SET",
    },
    "BACK": {
        "button": "BACK",
        "label": "BACK / CANCEL",
        "phy_code": "0x0024",
        "infra_code": "0x70e7",
        "p10_code": "0x0192",
        "p10_symbol": "PF_K_MENU_CANCEL",
        "kind": "key",
        "key": "BACK",
    },
}

FX3_BUTTON_ALIASES = {
    "CANCEL": "BACK",
    "PLAY": "C6",
    "DEL": "C5",
    "SET": "WHEEL_SET",
    "UP": "WHEEL_UP",
    "DOWN": "WHEEL_DOWN",
}

PAGE_NAMES = {
    0: "Big-6 Home (0x2e9e210, 98 rows)",
    1: "Three-Layer Menu (0x2ea02f8, 11 categories)",
    2: "Setting Main (0x2ea3e50, 10 rows)",
    3: "Setting Center (0x2eaf208, 17 rows)",
    4: "Assignable Button p110 (0x2eb75f0, 54 rows)",
    5: "Network Status / 176 (0x2ead870 + 0x2ea7648)",
    6: "Viewfinder HUD Strip (0x2e957b0 + 0x2e96608)",
    7: "Clip / Playback (0x2eb2ad8 + 0x2eb1890)",
    8: "Status / Setting Grid 69 (0x2eb36a8 + 0x2ea0d18)",
    9: "Thumbnail Properties p18 (0x2e9cef0, 46 rows Full-Screen)",
    10: "Touch Menu + Touch List (0x2ea6b08 + 0x2eb4e00)",
    11: "Settings Subpage 26 + Toast + Gamma (0x2ead0d8 + 0x2e917d8)",
    12: "Paint / Keyboard Overlay p4 (0x2e92c18, 102 rows)",
    13: "Media Status SSA/SSB/SSP p58 (0x2eaad68, 48 rows)",
    14: "Clip Thumbnail Browser 4x3 Grid p12 (0x2e9b798, 39 rows)",
    15: "Status Icon / Date Picker / HUD Tracking (0x2eb44b8 + 0x2ea2e48 + 0x2e95cc0)",
    16: "Full 253-Row Main Viewfinder HUD p10 (0x2e96608, 253 rows)",
    17: "TC / Audio Level Meter / 6-Btn Status p11 (0x2e9ad78, 35 rows)",
    18: "6-Line Change Message Dialog p81 (0x2eb2d60, 10 rows)",
    19: "Wireless LAN / SSID Scan List p43 (0x2ea5560, 11 rows)",
    20: "3-Col Setting List p66 / p73 (0x2eacdc0 + 0x2eafac0)",
    21: "OK/Cancel Confirm Dialog p72 / p93 (0x2eaf7a8 + 0x2eb4a58)",
    22: "Split-Pane Setting + 2nd-Layer Banner p77 / p112 (0x2eb1530 + 0x2eb8760)",
    23: "15-Btn 3x5 Menu Grid p64 / 10-Btn Media Grid p57 (0x2eac280 + 0x2eaa810)",
    24: "Universal 128-Page Descriptor Table Mode (fx6_all_pages[0..127])",
}


def _load_all_128_pages() -> list[dict[str, Any]]:
    hdr_path = REPO_ROOT / "reports" / "2026-11-07-fx6-uxengine-init-assist" / "artifacts" / "fx6_menu_items_assist.h"
    if not hdr_path.exists():
        return []
    txt = hdr_path.read_text(errors="replace")
    pages: list[dict[str, Any]] = []
    for m in re.finditer(
        r"\{\s*(\d+),\s*(\d+),\s*(0x[0-9a-fA-F]+)u,\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*\"([^\"]*)\"\s*\}",
        txt,
    ):
        pidx, _, off_hex, rows, _, _, _, _, first_name = m.groups()
        pages.append({
            "idx": int(pidx),
            "off": int(off_hex, 16),
            "off_hex": off_hex,
            "rows": int(rows),
            "first_name": first_name,
        })
    return pages


ALL_128_PAGES = _load_all_128_pages()

LEGACY_PAGE_MAP = {
    "home": 0,
    "big6": 0,
    "menu": 1,
    "setting_main": 2,
    "setting_center": 3,
    "assignable": 4,
    "network": 5,
    "hud": 6,
    "clip": 7,
    "playback": 7,
    "status": 8,
    "grid": 8,
    "thumbnail_props": 9,
    "touch": 10,
    "subpage": 11,
    "paint_overlay": 12,
    "media_status": 13,
    "clip_grid": 14,
    "status_icon": 15,
}

CAT_NAMES = [
    "User",
    "Edit User Menu",
    "Shooting",
    "Project",
    "Paint/Look",
    "TC/Media",
    "Monitoring",
    "Audio",
    "Thumbnail",
    "Technical",
    "Maintenance",
]

CLIENT_DISCONNECT_ERRNOS = frozenset(
    getattr(errno, name)
    for name in ("EPIPE", "ECONNRESET", "ECONNABORTED", "ETIMEDOUT", "ENOTCONN", "ESHUTDOWN")
    if hasattr(errno, name)
)


def _is_client_disconnect_exc(exc: BaseException) -> bool:
    """Return True for benign client socket resets, broken pipes, or timeouts."""
    if isinstance(exc, (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, TimeoutError, socket.timeout)):
        return True
    if isinstance(exc, OSError) and exc.errno in CLIENT_DISCONNECT_ERRNOS:
        return True
    return False


class HardenedThreadingHTTPServer(ThreadingHTTPServer):
    """ThreadingHTTPServer that suppresses noisy tracebacks on client socket disconnects."""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, server_address: tuple[str, int], RequestHandlerClass: type[BaseHTTPRequestHandler]) -> None:
        self.client_disconnects = 0
        super().__init__(server_address, RequestHandlerClass)

    def handle_error(self, request: Any, client_address: Any) -> None:
        _, exc, _ = sys.exc_info()
        if exc is not None and _is_client_disconnect_exc(exc):
            self.client_disconnects += 1
            return
        super().handle_error(request, client_address)


def compute_gpe0_frame_diff(raw_a: bytes, raw_b: bytes) -> dict[str, int]:
    """Compute exact byte-level and 32-bit pixel-level diff between two GPE0 buffers."""
    n_bytes = min(len(raw_a), len(raw_b))
    if len(raw_a) != len(raw_b):
        raise ValueError(f"Frame size mismatch: {len(raw_a)} vs {len(raw_b)}")
    if n_bytes == 0:
        return {"diff_bytes": 0, "diff_pixels": 0, "total_bytes": 0, "total_pixels": 0}
    total_pixels = n_bytes // 4
    if raw_a == raw_b:
        return {
            "diff_bytes": 0,
            "diff_pixels": 0,
            "total_bytes": n_bytes,
            "total_pixels": total_pixels,
        }
    diff_bytes = 0
    diff_pixels = 0
    aligned_q = (n_bytes // 8) * 8
    qa = memoryview(raw_a)[:aligned_q].cast("Q")
    qb = memoryview(raw_b)[:aligned_q].cast("Q")
    for qi in range(len(qa)):
        if qa[qi] == qb[qi]:
            continue
        base = qi * 8
        for p_off in (base, base + 4):
            b_diff = (
                (1 if raw_a[p_off] != raw_b[p_off] else 0)
                + (1 if raw_a[p_off + 1] != raw_b[p_off + 1] else 0)
                + (1 if raw_a[p_off + 2] != raw_b[p_off + 2] else 0)
                + (1 if raw_a[p_off + 3] != raw_b[p_off + 3] else 0)
            )
            if b_diff:
                diff_pixels += 1
                diff_bytes += b_diff
    for pos in range(aligned_q, n_bytes):
        if raw_a[pos] != raw_b[pos]:
            diff_bytes += 1
    return {
        "diff_bytes": diff_bytes,
        "diff_pixels": diff_pixels,
        "total_bytes": n_bytes,
        "total_pixels": total_pixels,
    }


_FAST_SCOPE_FN = None
_FAST_SCOPE_TRIED = False
_FALLBACK_RAW_CACHE: bytes | None = None


def _get_fast_scope_fn():
    """Compile once into /private/tmp for sub-ms GPE0 32-col waveform & 16-bin RGB/Luma histogram."""
    global _FAST_SCOPE_FN, _FAST_SCOPE_TRIED
    if _FAST_SCOPE_TRIED:
        return _FAST_SCOPE_FN
    _FAST_SCOPE_TRIED = True
    scope_kernel = (
        "#include <stddef.h>\n"
        "#include <stdint.h>\n"
        "void fx6_compute_scope_stats(const uint32_t *src, uint32_t w, uint32_t h, uint32_t *out) {\n"
        "    for (uint32_t i = 0; i < 196u; i++) out[i] = 0u;\n"
        "    for (uint32_t c = 0; c < 32u; c++) out[c * 4u] = 255u;\n"
        "    uint32_t total_nz = 0u, hi_px = 0u, amber_px = 0u, active_px = 0u;\n"
        "    for (uint32_t y = 0; y < h; y++) {\n"
        "        const uint32_t *row = src + (size_t)y * w;\n"
        "        for (uint32_t x = 0; x < w; x++) {\n"
        "            uint32_t v = row[x];\n"
        "            uint32_t col = (x * 32u) / w;\n"
        "            if (col > 31u) col = 31u;\n"
        "            uint32_t cbase = col * 4u;\n"
        "            if (v == 0u) {\n"
        "                out[cbase] = 0u;\n"
        "                out[128u + 0u]++;\n"
        "                out[144u + 0u]++;\n"
        "                out[160u + 0u]++;\n"
        "                out[176u + 0u]++;\n"
        "            } else {\n"
        "                total_nz++;\n"
        "                out[cbase + 3u]++;\n"
        "                uint32_t r = (v >> 16) & 0xffu;\n"
        "                uint32_t g = (v >> 8) & 0xffu;\n"
        "                uint32_t b = v & 0xffu;\n"
        "                uint32_t luma = (54u * r + 183u * g + 19u * b) >> 8;\n"
        "                out[128u + (r >> 4)]++;\n"
        "                out[144u + (g >> 4)]++;\n"
        "                out[160u + (b >> 4)]++;\n"
        "                out[176u + (luma >> 4)]++;\n"
        "                out[cbase + 1u] += luma;\n"
        "                if (luma < out[cbase]) out[cbase] = luma;\n"
        "                if (luma > out[cbase + 2u]) out[cbase + 2u] = luma;\n"
        "                uint32_t is_hi = (luma >= 178u) ? 1u : 0u;\n"
        "                uint32_t is_amb = (r >= 160u && g >= 70u && r > b + 60u && g > b + 20u) ? 1u : 0u;\n"
        "                hi_px += is_hi;\n"
        "                amber_px += is_amb;\n"
        "                if (is_hi || is_amb) active_px++;\n"
        "            }\n"
        "        }\n"
        "    }\n"
        "    out[192] = total_nz;\n"
        "    out[193] = hi_px;\n"
        "    out[194] = amber_px;\n"
        "    out[195] = active_px;\n"
        "}\n"
    )
    try:
        import ctypes
        tag = hashlib.sha256(scope_kernel.encode()).hexdigest()[:12]
        dylib = Path("/private/tmp") / f"fx6_gpe0_scope_{tag}.dylib"
        if not dylib.is_file():
            src_file = Path("/private/tmp") / f"fx6_gpe0_scope_{tag}.c"
            tmp_dylib = Path("/private/tmp") / f"fx6_gpe0_scope_{tag}.{os.getpid()}.dylib"
            src_file.write_text(scope_kernel)
            done = subprocess.run(
                ["/usr/bin/xcrun", "clang", "-O3", "-dynamiclib", str(src_file), "-o", str(tmp_dylib)],
                capture_output=True,
                timeout=10,
            )
            if done.returncode == 0:
                os.replace(tmp_dylib, dylib)
        if dylib.is_file():
            lib = ctypes.CDLL(str(dylib))
            fn = lib.fx6_compute_scope_stats
            fn.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p]
            fn.restype = None
            _FAST_SCOPE_FN = (ctypes, fn)
    except Exception:
        _FAST_SCOPE_FN = None
    return _FAST_SCOPE_FN


def _luma8_to_ire(val: float) -> float:
    return round((float(val) * 109.0) / 255.0, 2)


def _format_scope_stats(
    stats_words: list[int] | tuple[int, ...],
    frame_sha256: str,
    width: int = GPE0_W,
    height: int = GPE0_H,
) -> dict[str, Any]:
    total_pixels = width * height
    col_pixels = max(1, (width // 32) * height)
    waveform: list[dict[str, Any]] = []
    for c in range(32):
        base = c * 4
        c_min = stats_words[base]
        c_sum = stats_words[base + 1]
        c_max = stats_words[base + 2]
        c_nz = stats_words[base + 3]
        waveform.append({
            "col": c,
            "min_ire": _luma8_to_ire(c_min),
            "avg_ire": _luma8_to_ire(c_sum / float(col_pixels)),
            "max_ire": _luma8_to_ire(c_max),
            "nonzero_px": int(c_nz),
        })
    hist_r = [int(stats_words[128 + i]) for i in range(16)]
    hist_g = [int(stats_words[144 + i]) for i in range(16)]
    hist_b = [int(stats_words[160 + i]) for i in range(16)]
    hist_l = [int(stats_words[176 + i]) for i in range(16)]
    total_nz = int(stats_words[192])
    hi_px = int(stats_words[193])
    amber_px = int(stats_words[194])
    active_px = int(stats_words[195])
    return {
        "ok": True,
        "width": width,
        "height": height,
        "total_pixels": total_pixels,
        "nonzero_pixels": total_nz,
        "nonzero_ratio": round(total_nz / float(total_pixels), 6) if total_pixels else 0.0,
        "highlight_pixels": hi_px,
        "amber_pixels": amber_px,
        "active_highlight_amber_pixels": active_px,
        "waveform_columns": 32,
        "waveform": waveform,
        "histogram_bins": 16,
        "histograms": {
            "r": hist_r,
            "g": hist_g,
            "b": hist_b,
            "luma": hist_l,
        },
        "ire_range": [0.0, 109.0],
        "frame_sha256": frame_sha256,
    }


def _py_compute_scope_stats(raw: bytes, width: int = GPE0_W, height: int = GPE0_H) -> dict[str, Any]:
    expected = width * height * 4
    if len(raw) < expected:
        raise ValueError(f"GPE0 buffer too small for scope stats: {len(raw)} < {expected}")
    u32_list = memoryview(raw)[:expected].cast("I")
    col_min = [255] * 32
    col_sum = [0] * 32
    col_max = [0] * 32
    col_nz = [0] * 32
    hist_r = [0] * 16
    hist_g = [0] * 16
    hist_b = [0] * 16
    hist_l = [0] * 16
    total_nz = 0
    hi_px = 0
    amber_px = 0
    active_px = 0
    for idx, v in enumerate(u32_list):
        col = ((idx % width) * 32) // width
        if col > 31:
            col = 31
        if v == 0:
            col_min[col] = 0
            hist_r[0] += 1
            hist_g[0] += 1
            hist_b[0] += 1
            hist_l[0] += 1
        else:
            total_nz += 1
            col_nz[col] += 1
            r = (v >> 16) & 0xFF
            g = (v >> 8) & 0xFF
            b = v & 0xFF
            luma = (54 * r + 183 * g + 19 * b) >> 8
            hist_r[r >> 4] += 1
            hist_g[g >> 4] += 1
            hist_b[b >> 4] += 1
            hist_l[luma >> 4] += 1
            col_sum[col] += luma
            if luma < col_min[col]:
                col_min[col] = luma
            if luma > col_max[col]:
                col_max[col] = luma
            is_hi = luma >= 178
            is_amb = (r >= 160 and g >= 70 and r > b + 60 and g > b + 20)
            if is_hi:
                hi_px += 1
            if is_amb:
                amber_px += 1
            if is_hi or is_amb:
                active_px += 1
    words: list[int] = []
    for c in range(32):
        words.extend([col_min[c], col_sum[c], col_max[c], col_nz[c]])
    words.extend(hist_r)
    words.extend(hist_g)
    words.extend(hist_b)
    words.extend(hist_l)
    words.extend([total_nz, hi_px, amber_px, active_px])
    digest = hashlib.sha256(raw[:expected]).hexdigest()
    return _format_scope_stats(words, digest, width=width, height=height)


def compute_gpe0_scope_stats(raw: bytes, *, use_fast: bool = True) -> dict[str, Any]:
    """Compute 32-col IRE waveform (0..109%), 16-bin RGB/Luma histograms, NZ ratio & highlight/amber counts."""
    if len(raw) < GPE0_BYTES:
        raise ValueError(f"GPE0 buffer too small for scope stats: {len(raw)} < {GPE0_BYTES}")
    fast = _get_fast_scope_fn() if use_fast else None
    if fast is not None:
        ctypes_mod, fn = fast
        src_buf = (ctypes_mod.c_char * GPE0_BYTES).from_buffer_copy(raw, 0)
        out_arr = (ctypes_mod.c_uint32 * 196)()
        fn(ctypes_mod.addressof(src_buf), GPE0_W, GPE0_H, ctypes_mod.addressof(out_arr))
        digest = hashlib.sha256(raw[:GPE0_BYTES]).hexdigest()
        return _format_scope_stats(list(out_arr), digest, width=GPE0_W, height=GPE0_H)
    return _py_compute_scope_stats(raw, width=GPE0_W, height=GPE0_H)


def _png_to_raw_gpe0(png_bytes: bytes) -> bytes:
    """Decode an 8-bit RGB/RGBA PNG (1024x540) into raw GPE0 little-endian 0xAARRGGBB uint32 buffer."""
    if not png_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return b""
    pos = 8
    w = h = bd = ct = 0
    idat = bytearray()
    total = len(png_bytes)
    while pos + 12 <= total:
        ln = struct.unpack_from(">I", png_bytes, pos)[0]
        tag = png_bytes[pos + 4 : pos + 8]
        payload = png_bytes[pos + 8 : pos + 8 + ln]
        if len(payload) < ln:
            break
        if tag == b"IHDR" and len(payload) >= 13:
            w, h, bd, ct = struct.unpack_from(">IIBB", payload, 0)
        elif tag == b"IDAT":
            idat.extend(payload)
        elif tag == b"IEND":
            break
        pos += 12 + ln
    if w != GPE0_W or h != GPE0_H or bd != 8 or ct not in (2, 6):
        return b""
    bpp = 4 if ct == 6 else 3
    stride = w * bpp
    raw_scan = zlib.decompress(bytes(idat))
    if len(raw_scan) < h * (1 + stride):
        return b""
    prev_row = bytearray(stride)
    out = bytearray(GPE0_BYTES)
    out_u32 = memoryview(out).cast("I")
    for y in range(h):
        row_off = y * (1 + stride)
        ftype = raw_scan[row_off]
        cur = bytearray(raw_scan[row_off + 1 : row_off + 1 + stride])
        if ftype == 1:
            for i in range(bpp, stride):
                cur[i] = (cur[i] + cur[i - bpp]) & 0xFF
        elif ftype == 2:
            for i in range(stride):
                cur[i] = (cur[i] + prev_row[i]) & 0xFF
        elif ftype == 3:
            for i in range(stride):
                left = cur[i - bpp] if i >= bpp else 0
                cur[i] = (cur[i] + ((left + prev_row[i]) >> 1)) & 0xFF
        elif ftype == 4:
            for i in range(stride):
                a = cur[i - bpp] if i >= bpp else 0
                b = prev_row[i]
                c = prev_row[i - bpp] if i >= bpp else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                cur[i] = (cur[i] + pr) & 0xFF
        row_base = y * w
        for x in range(w):
            o = x * bpp
            r, g, b = cur[o], cur[o + 1], cur[o + 2]
            if r == 14 and g == 16 and b == 20:
                out_u32[row_base + x] = 0
            else:
                out_u32[row_base + x] = 0xFF000000 | (r << 16) | (g << 8) | b
        prev_row = cur
    return bytes(out)


def _synthetic_fallback_gpe0_raw() -> bytes:
    """Deterministic fallback 1024x540x4 GPE0 frame when offline PNG is absent."""
    out = bytearray(GPE0_BYTES)
    u32 = memoryview(out).cast("I")
    for y in range(GPE0_H):
        if 40 <= y < 480:
            row_base = y * GPE0_W
            for x in range(GPE0_W):
                if 32 <= x < 992:
                    if y < 120:
                        u32[row_base + x] = 0xFFF59E0B  # amber header highlight
                    elif x < 340:
                        u32[row_base + x] = 0xFF22D3EE  # cyan UI column
                    elif x < 680:
                        u32[row_base + x] = 0xFF94A3B8  # mid-gray cell
                    else:
                        u32[row_base + x] = 0xFFF8FAFC  # crisp white highlight text
    return bytes(out)


def _get_fallback_gpe0_raw(last_png: bytes = b"") -> tuple[bytes, str]:
    global _FALLBACK_RAW_CACHE
    if last_png:
        decoded = _png_to_raw_gpe0(last_png)
        if len(decoded) == GPE0_BYTES:
            return decoded, "fallback_png"
    if _FALLBACK_RAW_CACHE is None and FALLBACK_GPE0_PNG.is_file():
        decoded = _png_to_raw_gpe0(FALLBACK_GPE0_PNG.read_bytes())
        if len(decoded) == GPE0_BYTES:
            _FALLBACK_RAW_CACHE = decoded
    if _FALLBACK_RAW_CACHE is not None:
        return _FALLBACK_RAW_CACHE, "fallback_png"
    return _synthetic_fallback_gpe0_raw(), "synthetic_fallback"


MENU_CATEGORIES_BILINGUAL: list[dict[str, Any]] = [
    {
        "cat_idx": 0,
        "page_id": "cat_0_user",
        "category": "User",
        "category_zh": "用户菜单",
        "zh_title": "1. 用户菜单 (User Menu 自定义常用项)",
        "en_title": "User -> Custom Menu Shortcuts",
        "macro": {"page": 1, "menu_cat": 0, "menu_item": 0, "menu_depth": 1},
        "fx3_bridge_note": "Stage-B P10: Maps FX3 Fn/My Menu slots onto FX6 User Menu bank",
        "keywords": ["user", "custom", "my menu", "用户菜单", "自定义"],
    },
    {
        "cat_idx": 1,
        "page_id": "cat_1_edit_user",
        "category": "Edit User Menu",
        "category_zh": "编辑用户菜单",
        "zh_title": "2. 编辑用户菜单 (Edit User Menu)",
        "en_title": "Edit User Menu -> Pin & Reorder",
        "macro": {"page": 1, "menu_cat": 1, "menu_item": 0, "menu_depth": 1},
        "fx3_bridge_note": "Stage-B P10: User Menu slot editor via FX3 Rear Wheel / SET",
        "keywords": ["edit user", "pin", "reorder", "编辑用户菜单"],
    },
    {
        "cat_idx": 2,
        "page_id": "cat_2_shooting",
        "category": "Shooting",
        "category_zh": "拍摄",
        "zh_title": "3. 拍摄菜单 -> Cine EI / S&Q 升格 / 快门角",
        "en_title": "Shooting -> Cine EI / S&Q / Shutter",
        "macro": {"page": 1, "menu_cat": 2, "menu_item": 0, "menu_depth": 1},
        "fx3_bridge_note": "P11 Dual Base ISO 800/12800 + BK4 Shutter Angle (0x02cf1702/04)",
        "keywords": ["shooting", "cine ei", "s&q", "iso", "base iso", "shutter", "拍摄", "升格", "快门", "双原生"],
    },
    {
        "cat_idx": 3,
        "page_id": "cat_3_project",
        "category": "Project",
        "category_zh": "工程",
        "zh_title": "4. 工程菜单 -> Base Look / 录制格式 (Rec Format)",
        "en_title": "Project -> Base Look / Rec Format",
        "macro": {"page": 1, "menu_cat": 3, "menu_item": 1, "menu_depth": 1},
        "fx3_bridge_note": "P1 /dev/nflasha30 + XAVC S-I / Long GOP Project Frame Rate",
        "keywords": ["project", "base look", "rec format", "xavc", "fps", "工程", "录制格式", "帧率"],
    },
    {
        "cat_idx": 4,
        "page_id": "cat_4_paint_look",
        "category": "Paint/Look",
        "category_zh": "画质/风格",
        "zh_title": "5. 画质/风格 -> User 3D LUT (33³ .cube 调色导入)",
        "en_title": "Paint/Look -> User 3D LUT",
        "macro": {"page": 1, "menu_cat": 4, "menu_item": 1, "menu_depth": 2},
        "fx3_bridge_note": "P1 /lut->p30 + P11 33^3 3D LUT DMA (0x0165/0x0166) + libmpr SetLutData Guard",
        "keywords": ["paint", "look", "lut", "3d lut", "user lut", "cube", "s-cinetone", "slog3", "画质", "风格", "调色"],
    },
    {
        "cat_idx": 5,
        "page_id": "cat_5_tc_media",
        "category": "TC/Media",
        "category_zh": "时间码/媒体",
        "zh_title": "6. 时间码/媒体 -> 双 CFexpress 卡槽 (SSA/SSB)",
        "en_title": "TC/Media -> Dual CFexpress Slot",
        "macro": {"page": 1, "menu_cat": 5, "menu_item": 0, "menu_depth": 1},
        "fx3_bridge_note": "FX3 Dual CFexpress Type A / SD UHS-II Slot A/B Telemetry & Format Guard",
        "keywords": ["tc", "media", "cfexpress", "slot", "card", "timecode", "format", "时间码", "媒体", "卡槽", "双卡"],
    },
    {
        "cat_idx": 6,
        "page_id": "cat_6_monitoring",
        "category": "Monitoring",
        "category_zh": "监看",
        "zh_title": "7. 监看菜单 -> 输出 / 屏幕显示叠加 (Output / Display)",
        "en_title": "Monitoring -> Output / Display",
        "macro": {"page": 1, "menu_cat": 6, "menu_item": 0, "menu_depth": 1},
        "fx3_bridge_note": "HDMI/SDI Display Assist + Gamma Display Assist + Viewfinder OSD GPE0",
        "keywords": ["monitoring", "output", "display", "hud", "osd", "vf", "hdmi", "监看", "输出", "显示"],
    },
    {
        "cat_idx": 7,
        "page_id": "cat_7_audio",
        "category": "Audio",
        "category_zh": "音频",
        "zh_title": "8. 音频菜单 -> XLR-H1 4通道输入 (+48V / 0x5d90)",
        "en_title": "Audio -> XLR-H1 4ch",
        "macro": {"page": 1, "menu_cat": 7, "menu_item": 0, "menu_depth": 1},
        "fx3_bridge_note": "P11 XLR-H1 MI-Shoe 0x5d90 4-Ch +48V / 0x91db059b Internal Stereo Fallback",
        "keywords": ["audio", "xlr", "xlr-h1", "4ch", "48v", "mic", "vu", "音频", "声道", "麦克风"],
    },
    {
        "cat_idx": 8,
        "page_id": "cat_8_thumbnail",
        "category": "Thumbnail",
        "category_zh": "缩略图",
        "zh_title": "9. 缩略图菜单 -> 素材剪辑与属性 (Thumbnail)",
        "en_title": "Thumbnail -> Clip Index & Playback",
        "macro": {"page": 1, "menu_cat": 8, "menu_item": 0, "menu_depth": 1},
        "fx3_bridge_note": "Stage-B P10 C6/PLAY (0x000b -> PF_K_THUMBNAIL) -> 4x3 Clip Grid",
        "keywords": ["thumbnail", "clip", "playback", "browse", "缩略图", "回放", "素材"],
    },
    {
        "cat_idx": 9,
        "page_id": "cat_9_technical",
        "category": "Technical",
        "category_zh": "技术",
        "zh_title": "10. 技术菜单 -> P4 ND 锁定 / 5轴防抖 IBIS",
        "en_title": "Technical -> P4 ND Lock / IBIS",
        "macro": {"page": 1, "menu_cat": 9, "menu_item": 0, "menu_depth": 1},
        "fx3_bridge_note": "P4 ND=Clear Hardware Lock + P11 RTMD 0xE304 5-Axis IBIS Center Lock",
        "keywords": ["technical", "nd", "p4", "ibis", "steadyshot", "rtmd", "0xe304", "技术", "防抖", "锁定"],
    },
    {
        "cat_idx": 10,
        "page_id": "cat_10_maintenance",
        "category": "Maintenance",
        "category_zh": "维护",
        "zh_title": "11. 维护菜单 -> 固件版本与硬件校准 (Version)",
        "en_title": "Maintenance -> Version",
        "macro": {"page": 1, "menu_cat": 10, "menu_item": 0, "menu_depth": 1},
        "fx3_bridge_note": "P12 WF-12 Safe O_RDONLY / LRU Pool + BK4 Airplane-Mode Shadow Lock",
        "keywords": ["maintenance", "version", "firmware", "reset", "clock", "维护", "版本", "固件", "校准"],
    },
]

FLAGSHIP_MENU_CATALOG: list[dict[str, Any]] = [
    {
        "page_id": "big6_home",
        "id": "big6_home",
        "kind": "flagship",
        "zh_title": "Big-6 电影机主界面 (FPS / EI / 快门 / ND / LUT / 白平衡)",
        "en_title": "Big-6 Home",
        "category": "Shooting",
        "category_zh": "主控面板",
        "macro": {"page": 0, "sel_box": 4, "menu_depth": 0},
        "idx128": 21,
        "fx3_bridge_note": "P11 Dual Base ISO + 33^3 LUT + P4 ND=Clear Lock (Fn -> Big-6)",
        "keywords": ["big6", "big-6", "home", "fps", "ei", "shutter", "nd", "lut", "wb", "主界面", "首页"],
    },
    {
        "page_id": "three_layer_menu",
        "id": "three_layer_menu",
        "kind": "flagship",
        "zh_title": "FX6 三层完整主菜单 (11大分类)",
        "en_title": "Three-Layer Menu (11 Categories)",
        "category": "User",
        "category_zh": "系统菜单",
        "macro": {"page": 1, "menu_cat": 2, "menu_item": 0, "menu_depth": 0},
        "idx128": 24,
        "fx3_bridge_note": "Stage-B P10 MENU (0x0011 -> UIBIZ_KEY_TACT_MENU) 3-Layer Navigation",
        "keywords": ["menu", "three layer", "categories", "三层菜单", "总菜单"],
    },
    {
        "page_id": "setting_main",
        "id": "setting_main",
        "kind": "flagship",
        "zh_title": "Setting Main 快速设置列表",
        "en_title": "Setting Main (0x2ea3e50)",
        "category": "Project",
        "category_zh": "快速设置",
        "macro": {"page": 2, "sel_box": 0, "menu_depth": 0},
        "idx128": 36,
        "fx3_bridge_note": "Live Base Look / Project Setting Main view",
        "keywords": ["setting main", "settings", "设置主页"],
    },
    {
        "page_id": "setting_center",
        "id": "setting_center",
        "kind": "flagship",
        "zh_title": "Setting Center 居中参数六宫格",
        "en_title": "Setting Center (0x2eaf208)",
        "category": "Shooting",
        "category_zh": "参数调节",
        "macro": {"page": 3, "sel_box": 4, "menu_depth": 0},
        "idx128": 70,
        "fx3_bridge_note": "Stage-B P10 C2 -> White Balance / Center 6-Cell Quick Edit",
        "keywords": ["setting center", "wb", "white balance", "居中设置", "白平衡"],
    },
    {
        "page_id": "assignable_p110",
        "id": "assignable_p110",
        "kind": "flagship",
        "zh_title": "自定义按键分配页 Page 110 (Assignable Buttons 30键)",
        "en_title": "Assignable Buttons Page 110",
        "category": "Technical",
        "category_zh": "按键映射",
        "macro": {"page": 4, "sel_box": 0, "menu_depth": 0},
        "idx128": 110,
        "fx3_bridge_note": "Stage-B P10 Physical FX3 C1..C6 / Fn / Rear Dial -> FX6 Assignable Map",
        "keywords": ["assignable", "buttons", "p110", "page 110", "110", "c1", "c5", "自定义按键", "功能键"],
    },
    {
        "page_id": "network_p12_guard",
        "id": "network_p12_guard",
        "kind": "flagship",
        "zh_title": "网络状态页 -> P12 飞行模式安全锁 (Network / BK4 Guard)",
        "en_title": "Network -> P12 Airplane Guard",
        "category": "Technical",
        "category_zh": "网络与安全",
        "macro": {"page": 5, "sel_box": 0, "menu_depth": 0},
        "idx128": 68,
        "fx3_bridge_note": "P12 BK4 Airplane-Mode Shadow Lock (WF-12 Safe, RF disabled in FX3 bridge)",
        "keywords": ["network", "airplane", "p12", "bk4", "wifi", "wf-12", "网络", "飞行模式", "安全锁"],
    },
    {
        "page_id": "monitoring_hud_strip",
        "id": "monitoring_hud_strip",
        "kind": "flagship",
        "zh_title": "监看取景器 HUD 状态条 (Viewfinder Strip)",
        "en_title": "Monitoring -> Viewfinder HUD Strip",
        "category": "Monitoring",
        "category_zh": "监看",
        "macro": {"page": 6, "sel_box": 0, "menu_depth": 0},
        "idx128": 6,
        "fx3_bridge_note": "DISP Cycle Viewfinder Strip + Audio Meter + P11 Live Badges",
        "keywords": ["hud strip", "viewfinder", "disp", "取景器", "状态条"],
    },
    {
        "page_id": "clip_playback",
        "id": "clip_playback",
        "kind": "flagship",
        "zh_title": "素材回放控制页 (Clip / Playback)",
        "en_title": "Thumbnail -> Clip / Playback",
        "category": "Thumbnail",
        "category_zh": "缩略图",
        "macro": {"page": 7, "sel_box": 0, "menu_depth": 0},
        "idx128": 78,
        "fx3_bridge_note": "FX6 Playback Transport & Clip Review Overlay",
        "keywords": ["clip", "playback", "transport", "回放", "播放"],
    },
    {
        "page_id": "status_grid_69",
        "id": "status_grid_69",
        "kind": "flagship",
        "zh_title": "相机全参数状态网格 Status Grid 69",
        "en_title": "Monitoring -> Status / Setting Grid 69",
        "category": "Monitoring",
        "category_zh": "监看",
        "macro": {"page": 8, "sel_box": 0, "menu_depth": 0},
        "idx128": 25,
        "fx3_bridge_note": "FX6 Camera Status / System Info Summary Matrix",
        "keywords": ["status", "grid", "69", "状态页", "参数总览"],
    },
    {
        "page_id": "thumbnail_props_p18",
        "id": "thumbnail_props_p18",
        "kind": "flagship",
        "zh_title": "缩略图素材属性全屏页 p18 (Clip Properties)",
        "en_title": "Thumbnail -> Clip Properties p18",
        "category": "Thumbnail",
        "category_zh": "缩略图",
        "macro": {"page": 9, "sel_box": 0, "menu_depth": 0},
        "idx128": 18,
        "fx3_bridge_note": "RTMD 0xE304 + Clip Codec / Resolution / LUT Metadata Properties",
        "keywords": ["thumbnail properties", "clip properties", "metadata", "p18", "素材属性"],
    },
    {
        "page_id": "media_dual_cfexpress",
        "id": "media_dual_cfexpress",
        "kind": "flagship",
        "zh_title": "媒体状态 -> 双 CFexpress 卡槽 (SSA/SSB p58)",
        "en_title": "TC/Media -> Dual CFexpress Slot (SSA/SSB)",
        "category": "TC/Media",
        "category_zh": "时间码/媒体",
        "macro": {"page": 13, "sel_box": 0, "menu_depth": 0},
        "idx128": 58,
        "fx3_bridge_note": "Stage-B P10 C4 (PF_K_SLOT_SEL 0x018a) -> Dual CFexpress Slot A/B Status",
        "keywords": ["media status", "cfexpress", "ssa", "ssb", "slot", "c4", "双卡槽", "媒体状态"],
    },
    {
        "page_id": "clip_thumbnail_browser",
        "id": "clip_thumbnail_browser",
        "kind": "flagship",
        "zh_title": "缩略图 4x3 剪辑浏览器 (Clip Browser p12)",
        "en_title": "Thumbnail -> 4x3 Clip Browser p12",
        "category": "Thumbnail",
        "category_zh": "缩略图",
        "macro": {"page": 14, "sel_box": 0, "menu_depth": 0},
        "idx128": 12,
        "fx3_bridge_note": "Stage-B P10 C6/PLAY (0x000b) -> 4x3 Clip Thumbnail Grid",
        "keywords": ["clip browser", "4x3", "thumbnail grid", "c6", "play", "剪辑浏览器", "缩略图网格"],
    },
    {
        "page_id": "full_hud_253",
        "id": "full_hud_253",
        "kind": "flagship",
        "zh_title": "监看 253 行完整取景器 HUD (Main Viewfinder p10)",
        "en_title": "Monitoring -> Full 253-Row Viewfinder HUD",
        "category": "Monitoring",
        "category_zh": "监看",
        "macro": {"page": 16, "sel_box": 0, "menu_depth": 0},
        "idx128": 10,
        "fx3_bridge_note": "Full Cinema Line HUD: FPS / EI / Shutter / P4 ND=Clear / 33^3 LUT / XLR-H1 / RTMD 0xE304",
        "keywords": ["full hud", "253", "viewfinder", "osd", "disp", "取景器主界面", "全屏hud"],
    },
    {
        "page_id": "tc_audio_meter_4ch",
        "id": "tc_audio_meter_4ch",
        "kind": "flagship",
        "zh_title": "音频与时间码 -> XLR-H1 4通道电平表 (TC / Audio Meter p11)",
        "en_title": "Audio -> XLR-H1 4ch Level Meter & TC Status",
        "category": "Audio",
        "category_zh": "音频",
        "macro": {"page": 17, "sel_box": 0, "menu_depth": 0},
        "idx128": 11,
        "fx3_bridge_note": "P11 XLR-H1 0x5d90 4-Ch VU + 0x91db059b Internal Stereo Fallback (C3)",
        "keywords": ["audio meter", "xlr-h1", "tc", "4ch", "c3", "level meter", "电平表", "4通道音频"],
    },
    {
        "page_id": "wlan_ssid_p12_guard",
        "id": "wlan_ssid_p12_guard",
        "kind": "flagship",
        "zh_title": "Wi-Fi SSID 扫描列表 (P12 飞行模式锁保护 p43)",
        "en_title": "Network -> Wireless LAN SSID Scan (P12 Guarded)",
        "category": "Technical",
        "category_zh": "网络与安全",
        "macro": {"page": 19, "sel_box": 0, "menu_depth": 0},
        "idx128": 43,
        "fx3_bridge_note": "P12 BK4 Airplane-Mode Shadow Lock prevents live RF activation on FX3 bridge",
        "keywords": ["wlan", "ssid", "wifi", "airplane", "p12", "无线", "扫描"],
    },
]

_PAGE128_CURATED_META: dict[int, tuple[str, str, str, str]] = {
    0: ("基础触控遮罩 (No33_touch)", "Base Touch Overlay (No33_touch)", "Monitoring", "Touch hit-box & GPE0 safe area"),
    1: ("4通道音频电平条 (Audio Level Meter)", "Audio Level Meter Bar", "Audio", "P11 XLR-H1 0x5d90 4-Ch meter overlay"),
    2: ("图像尺寸选择器 (Picture Size)", "Picture Size Selector", "Project", "Recording frame geometry descriptor"),
    3: ("Gamma 显示辅助 (Gamma Display Assist)", "Gamma Display Assist", "Monitoring", "S-Log3 -> Rec.709 monitoring assist"),
    4: ("Paint / 键盘文本输入浮层 (102行)", "Paint / On-Screen Keyboard Overlay (102 rows)", "Paint/Look", "User LUT / Scene label text input"),
    5: ("直达主菜单剪辑区 (Home Clip Area)", "Direct Home Menu Clip Area", "User", "Quick clip/menu strip"),
    6: ("视频信号监看波形条 (Video Signal Monitor)", "Video Signal Monitor Strip", "Monitoring", "Waveform / vector / exposure HUD"),
    7: ("Base Look 快速预览栏 (base_look)", "Base Look Quick Overlay", "Paint/Look", "P1 /dev/nflasha30 Base Look preview"),
    8: ("追踪对焦取消按键 (Tracking Cancel)", "AF Tracking Cancel Button", "Shooting", "FX3 Hybrid AF tracking HUD overlay"),
    9: ("分辨率标识浮层 (Resolution)", "Resolution Overlay", "Project", "4K DCI / QFHD / HD descriptor"),
    10: ("完整 253 行电影机取景器 HUD", "Full 253-Row Main Viewfinder HUD", "Monitoring", "Full OSD + P4 ND=Clear + P11 IBIS/XLR"),
    11: ("时间码与 4通道音频状态弹窗", "TC & 4-Ch Audio Level Status Dialog", "Audio", "XLR-H1 4ch + Timecode status"),
    12: ("4x3 素材缩略图网格浏览器", "4x3 Clip Thumbnail Browser Grid", "Thumbnail", "C6/PLAY Clip browser"),
    18: ("缩略图素材属性全屏页 (p18)", "Thumbnail Clip Properties Full-Screen (p18)", "Thumbnail", "Clip codec & RTMD metadata"),
    21: ("Big-6 电影机主界面 (98行描述符)", "Big-6 Home Screen (98-row descriptor)", "Shooting", "Big-6 Home: FPS / EI / Shutter / ND / LUT / WB"),
    24: ("三层主菜单框架 (11大分类)", "Three-Layer Menu Frame (11 Categories)", "User", "FX6 11-category master menu tree"),
    25: ("全参数相机状态矩阵 (69行)", "Status / Setting Grid (69 rows)", "Monitoring", "Camera status matrix"),
    36: ("Setting Main 主设置列表", "Setting Main List", "Project", "Quick main settings"),
    43: ("Wi-Fi SSID 扫描列表 (P12 飞行锁)", "Wireless LAN SSID Scan (P12 Guarded)", "Technical", "P12 BK4 Airplane-Mode Shadow Lock"),
    52: ("Touch 触控菜单浮层 (26_TOUCH)", "Touch Menu Overlay", "User", "Touch shortcut panel"),
    56: ("网络状态 176 行详细配置页", "Network Status 176-Row Detail Page", "Technical", "P12 BK4 Airplane-Mode Lock enforced"),
    57: ("媒体 10 键功能网格 (2x5)", "Media 10-Button Grid (2x5)", "TC/Media", "Dual CFexpress media actions"),
    58: ("双 CFexpress 卡槽媒体状态 (SSA/SSB)", "Dual CFexpress Media Status (SSA/SSB)", "TC/Media", "Dual CFexpress slot A/B capacity"),
    60: ("执行中提示弹窗 (EXECUTING)", "Executing Progress Dialog", "Maintenance", "Non-blocking progress modal"),
    64: ("15 键 3x5 快捷菜单网格", "15-Button 3x5 Menu Grid", "User", "Quick 3x5 touch grid"),
    66: ("3 列参数设置列表 (p66)", "3-Column Setting List (p66)", "Project", "Multi-column parameter table"),
    67: ("设置子页与弹窗面板 (p67)", "Settings Subpage Panel (p67)", "Shooting", "Shooting / Technical subpage"),
    68: ("网络状态主界面 (55行 P12保护)", "Network Status Summary (55 rows, P12 Guard)", "Technical", "P12 BK4 Airplane-Mode Guard"),
    69: ("Setting Grid 69 参数矩阵", "Setting Grid 69 Matrix", "Monitoring", "Parameter overview grid"),
    70: ("Setting Center 居中六宫格", "Setting Center 6-Cell Panel", "Shooting", "Center Big-6 quick edit"),
    72: ("确认 / 取消对话框 (OK/Cancel)", "OK / Cancel Confirmation Dialog", "Maintenance", "Safe modal confirmation"),
    73: ("编号参数设置列表 (p73)", "Numbered Setting List (p73)", "Project", "Indexed setting rows"),
    77: ("分栏设置与辅助信息面板 (p77)", "Split-Pane Setting + Aux Info (p77)", "Technical", "Split parameter + help note"),
    78: ("素材播放与时间轴控制 (Playback)", "Clip Playback Control (54 rows)", "Thumbnail", "Playback transport & marker UI"),
    81: ("6 行固件变更通知对话框 (p81)", "6-Line Firmware Change Notice Dialog", "Maintenance", "Version / notice prompt"),
    86: ("系统状态辅助页 (p86)", "System Status Aux Page (p86)", "Monitoring", "Status icons & indicators"),
    91: ("设置列表背景模板 (p91)", "Setting List Background (p91)", "Maintenance", "Shared list frame"),
    92: ("状态图标与指示器集合 (p92)", "Status Icon Set (p92)", "Monitoring", "Recording / battery / media icons"),
    93: ("执行确认弹窗 (Execute/Cancel)", "Execute / Cancel Dialog (p93)", "Maintenance", "Destructive-action confirm guard"),
    94: ("Touch 列表滚动面板 (30_TOUCH)", "Touch Scroll List Panel (p94)", "User", "Touch list container"),
    110: ("自定义功能键分配页 Page 110 (54行)", "Assignable Buttons Page 110 (54 rows)", "Technical", "Stage-B P10 FX3 C1..C6 / Fn / Wheel Map"),
    112: ("二级菜单横幅面板 (p112)", "2nd-Layer Setting Banner (p112)", "Maintenance", "Section header banner"),
}

_CAT_ZH_MAP: dict[str, str] = {c["category"]: c["category_zh"] for c in MENU_CATEGORIES_BILINGUAL}


def _classify_page128(p: dict[str, Any]) -> dict[str, Any]:
    idx = int(p["idx"])
    off_hex = str(p["off_hex"])
    rows = int(p["rows"])
    first_name = str(p["first_name"])
    if idx in _PAGE128_CURATED_META:
        zh_t, en_t, cat, note = _PAGE128_CURATED_META[idx]
    else:
        low = first_name.lower()
        if "audio" in low:
            cat, zh_kind, en_kind = "Audio", "音频设置描述符页", "Audio Descriptor Page"
        elif "gamma" in low or "look" in low:
            cat, zh_kind, en_kind = "Paint/Look", "画质/Look 描述符页", "Paint/Look Descriptor Page"
        elif "rec" in low or "picture" in low or "resolution" in low:
            cat, zh_kind, en_kind = "Project", "工程/录制描述符页", "Project Descriptor Page"
        elif "yuv" in low or "thumb" in low or "clip" in low:
            cat, zh_kind, en_kind = "Thumbnail", "缩略图/素材描述符页", "Thumbnail Descriptor Page"
        elif "executing" in low or "setting_list" in low or "button" in low:
            cat, zh_kind, en_kind = "Maintenance", "系统弹窗/控件描述符页", "Maintenance/Dialog Descriptor Page"
        elif "block_touch" in low:
            cat, zh_kind, en_kind = "Shooting", "区块触控参数页", "Block Touch Parameter Page"
        elif "touch_screen" in low:
            cat, zh_kind, en_kind = "User", "触控菜单页", "Touch Menu Screen Page"
        elif "bg" in low or "ninepatch" in low:
            cat, zh_kind, en_kind = "Monitoring", "背景/叠层框架页", "Display Background/Frame Page"
        else:
            cat, zh_kind, en_kind = "Technical", "FX6 原生 UI 描述符页", "FX6 Native Descriptor Page"
        zh_t = f"#{idx:03d} {zh_kind} ({first_name}, {rows}行)"
        en_t = f"#{idx:03d} {en_kind} ({first_name}, {rows} rows)"
        note = f"Universal Descriptor Table {off_hex} ({rows} rows) via appFw.so"

    return {
        "page_id": f"p128_{idx:03d}",
        "id": f"p128_{idx:03d}",
        "kind": "page128",
        "idx128": idx,
        "off": int(p["off"]),
        "off_hex": off_hex,
        "rows": rows,
        "first_name": first_name,
        "zh_title": f"#{idx:03d} {zh_t}" if not zh_t.startswith("#") else zh_t,
        "en_title": f"#{idx:03d} {en_t}" if not en_t.startswith("#") else en_t,
        "category": cat,
        "category_zh": _CAT_ZH_MAP.get(cat, cat),
        "macro": {
            "page": 24,
            "table_off": int(p["off"]),
            "table_rows": rows,
            "table_off2": 0,
            "table_rows2": 0,
            "idx128": idx,
        },
        "fx3_bridge_note": note,
        "keywords": [
            f"p{idx}",
            f"page {idx}",
            f"#{idx:03d}",
            off_hex.lower(),
            first_name.lower(),
            cat.lower(),
            zh_t.lower(),
            en_t.lower(),
        ],
    }


_CATALOG_CACHE: dict[str, Any] | None = None


def build_menu_catalog() -> dict[str, Any]:
    """Return the complete 11-category + flagship + 128-page bilingual FX6 menu catalog."""
    global _CATALOG_CACHE
    if _CATALOG_CACHE is None:
        items: list[dict[str, Any]] = []
        for entry in FLAGSHIP_MENU_CATALOG:
            rec = dict(entry)
            rec["macro"] = dict(entry["macro"])
            rec["keywords"] = list(entry.get("keywords", []))
            items.append(rec)
        for cat in MENU_CATEGORIES_BILINGUAL:
            items.append({
                "page_id": cat["page_id"],
                "id": cat["page_id"],
                "kind": "category",
                "cat_idx": cat["cat_idx"],
                "zh_title": cat["zh_title"],
                "en_title": cat["en_title"],
                "category": cat["category"],
                "category_zh": cat["category_zh"],
                "macro": dict(cat["macro"]),
                "fx3_bridge_note": cat["fx3_bridge_note"],
                "keywords": list(cat["keywords"]),
            })
        pages128_entries = [_classify_page128(p) for p in ALL_128_PAGES]
        items.extend(pages128_entries)

        quick_pill_ids = [
            "big6_home",
            "cat_0_user",
            "cat_1_edit_user",
            "cat_2_shooting",
            "cat_3_project",
            "cat_4_paint_look",
            "cat_5_tc_media",
            "cat_6_monitoring",
            "cat_7_audio",
            "cat_8_thumbnail",
            "cat_9_technical",
            "network_p12_guard",
            "cat_10_maintenance",
            "assignable_p110",
        ]
        by_id = {it["page_id"]: it for it in items}
        quick_pills = [
            {
                "page_id": by_id[pid]["page_id"],
                "zh_title": by_id[pid]["zh_title"],
                "en_title": by_id[pid]["en_title"],
                "category": by_id[pid]["category"],
                "fx3_bridge_note": by_id[pid]["fx3_bridge_note"],
                "macro": dict(by_id[pid]["macro"]),
            }
            for pid in quick_pill_ids
            if pid in by_id
        ]
        _CATALOG_CACHE = {
            "ok": True,
            "total_categories": len(MENU_CATEGORIES_BILINGUAL),
            "total_pages_128": len(pages128_entries),
            "total_entries": len(items),
            "categories": [
                {
                    "cat_idx": c["cat_idx"],
                    "page_id": c["page_id"],
                    "category": c["category"],
                    "category_zh": c["category_zh"],
                    "zh_title": c["zh_title"],
                    "en_title": c["en_title"],
                    "fx3_bridge_note": c["fx3_bridge_note"],
                    "macro": dict(c["macro"]),
                }
                for c in MENU_CATEGORIES_BILINGUAL
            ],
            "quick_jump_pills": quick_pills,
            "items": items,
        }
    return {
        "ok": True,
        "total_categories": _CATALOG_CACHE["total_categories"],
        "total_pages_128": _CATALOG_CACHE["total_pages_128"],
        "total_entries": _CATALOG_CACHE["total_entries"],
        "categories": list(_CATALOG_CACHE["categories"]),
        "quick_jump_pills": list(_CATALOG_CACHE["quick_jump_pills"]),
        "items": list(_CATALOG_CACHE["items"]),
    }


def search_menu_catalog(query: str = "", category: str = "") -> dict[str, Any]:
    """Filter the bilingual 11-category / 128-page catalog by search query and/or category."""
    cat_norm = str(category or "").strip().lower()
    q_norm = str(query or "").strip().lower()
    catalog = build_menu_catalog()
    items = catalog["items"]
    if cat_norm and cat_norm not in ("all", "*"):
        items = [
            it for it in items
            if it["category"].lower() == cat_norm
            or it.get("category_zh", "").lower() == cat_norm
            or cat_norm in it["category"].lower()
        ]
    if q_norm:
        tokens = [tok for tok in q_norm.split() if tok]
        scored: list[tuple[int, int, dict[str, Any]]] = []
        for idx, it in enumerate(items):
            title_hay = " ".join([
                str(it.get("page_id", "")),
                str(it.get("zh_title", "")),
                str(it.get("en_title", "")),
                str(it.get("first_name", "")),
                str(it.get("off_hex", "")),
            ]).lower()
            hay = " ".join([
                title_hay,
                str(it.get("category", "")),
                str(it.get("category_zh", "")),
                str(it.get("fx3_bridge_note", "")),
                " ".join(str(k) for k in it.get("keywords", [])),
            ]).lower()
            if all(tok in hay for tok in tokens):
                rank = 0 if all(tok in title_hay for tok in tokens) else 1
                scored.append((rank, idx, it))
        scored.sort(key=lambda t: (t[0], t[1]))
        items = [t[2] for t in scored]
    catalog["items"] = items
    catalog["filtered_count"] = len(items)
    catalog["query"] = query
    catalog["category_filter"] = category
    return catalog

CELL_NAMES = ["FPS", "EI / Base ISO", "Shutter", "ND Filter", "Base Look / 3D LUT", "White Balance"]
CELL_N_VALS = [7, 6, 7, 1, 8, 6]

USER_LUT_SLOTS = ("User1", "User2", "User3", "User4")
USER_LUT_SLOT_TO_CELL_IDX: dict[str, int] = {
    "User1": 4,
    "User2": 5,
    "User3": 6,
    "User4": 7,
}
RTMD_0XE304_MODES = ("ACTIVE_5AXIS", "OFF_CENTER_LOCKED", "STANDARD")
RTMD_0XE304_ALIASES: dict[str, str] = {
    "active_5axis": "ACTIVE_5AXIS",
    "5axis": "ACTIVE_5AXIS",
    "5-axis": "ACTIVE_5AXIS",
    "center_lock": "ACTIVE_5AXIS",
    "active": "ACTIVE_5AXIS",
    "0": "ACTIVE_5AXIS",
    "off_center_locked": "OFF_CENTER_LOCKED",
    "off": "OFF_CENTER_LOCKED",
    "locked": "OFF_CENTER_LOCKED",
    "active_off": "OFF_CENTER_LOCKED",
    "1": "OFF_CENTER_LOCKED",
    "standard": "STANDARD",
    "active_standard": "STANDARD",
    "std": "STANDARD",
    "2": "STANDARD",
}

BUILTIN_CUBE_PRESETS: dict[str, dict[str, Any]] = {
    "709_typeA": {
        "id": "709_typeA",
        "name": "709 Type-A",
        "title": "Sony_709_TypeA_SLog3",
        "size": 17,
        "description": "Sony LC-709TypeA filmic highlight roll-off for S-Log3",
    },
    "teal_orange": {
        "id": "teal_orange",
        "name": "Teal & Orange",
        "title": "Cinema_Teal_Orange_Grade",
        "size": 17,
        "description": "Split-tone cool cyan shadows with warm amber midtones/highlights",
    },
    "film_2383": {
        "id": "film_2383",
        "name": "Film 2383",
        "title": "Print_Film_2383_D65",
        "size": 17,
        "description": "2383 print-stock S-curve with rich emerald-teal density",
    },
    "slog3_bypass": {
        "id": "slog3_bypass",
        "name": "S-Log3 Bypass",
        "title": "SLog3_SGamut3Cine_Bypass",
        "size": 17,
        "description": "1:1 neutral identity S-Log3 monitoring bypass cube",
    },
}

ASSIST_TOOLS_SPECS: dict[str, dict[str, Any]] = {
    "aspect_marker": {
        "key": "aspect_marker",
        "label": "Aspect Marker",
        "choices": ("Off", "2.39:1", "1.85:1", "17:9", "9:16", "CenterCross"),
        "default": "Off",
    },
    "zebra_mode": {
        "key": "zebra_mode",
        "label": "Zebra",
        "choices": ("Off", "70%", "94%_SLog3", "100%"),
        "default": "Off",
    },
    "peaking_mode": {
        "key": "peaking_mode",
        "label": "Focus Peaking",
        "choices": ("Off", "Red", "Yellow", "White"),
        "default": "Off",
    },
    "desqueeze": {
        "key": "desqueeze",
        "label": "Anamorphic Desqueeze",
        "choices": ("1.0x", "1.33x", "2.0x"),
        "default": "1.0x",
    },
}

_ASSIST_ALIASES: dict[str, dict[str, str]] = {
    "aspect_marker": {
        "off": "Off",
        "2.39:1": "2.39:1",
        "2.39": "2.39:1",
        "scope": "2.39:1",
        "1.85:1": "1.85:1",
        "1.85": "1.85:1",
        "17:9": "17:9",
        "dci": "17:9",
        "9:16": "9:16",
        "vertical": "9:16",
        "centercross": "CenterCross",
        "center_cross": "CenterCross",
        "center": "CenterCross",
    },
    "zebra_mode": {
        "off": "Off",
        "70%": "70%",
        "70": "70%",
        "94%_slog3": "94%_SLog3",
        "94%": "94%_SLog3",
        "94% slog3": "94%_SLog3",
        "slog3": "94%_SLog3",
        "100%": "100%",
        "100": "100%",
    },
    "peaking_mode": {
        "off": "Off",
        "red": "Red",
        "yellow": "Yellow",
        "white": "White",
    },
    "desqueeze": {
        "1.0x": "1.0x",
        "1x": "1.0x",
        "1.0": "1.0x",
        "off": "1.0x",
        "1.3x": "1.33x",
        "1.33x": "1.33x",
        "1.33": "1.33x",
        "2.0x": "2.0x",
        "2x": "2.0x",
        "2.0": "2.0x",
    },
}


def normalize_assist_field(field: str, value: Any) -> str | None:
    if field not in ASSIST_TOOLS_SPECS:
        return None
    if isinstance(value, bool) or value is None:
        return None
    if not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw:
        return None
    low = raw.lower()
    alias_map = _ASSIST_ALIASES.get(field, {})
    if low in alias_map:
        return alias_map[low]
    for ch in ASSIST_TOOLS_SPECS[field]["choices"]:
        if ch.lower() == low:
            return ch
    return None


def validate_assist_tools_patch(body: Any) -> tuple[bool, dict[str, str], dict[str, Any] | None]:
    if not isinstance(body, dict):
        return False, {}, {"ok": False, "error": "invalid_assist_tools", "message": "assist_tools payload must be a JSON object"}
    updates: dict[str, str] = {}
    if body.get("reset") is True:
        for k, spec in ASSIST_TOOLS_SPECS.items():
            updates[k] = str(spec["default"])
    for key, spec in ASSIST_TOOLS_SPECS.items():
        if key in body:
            norm = normalize_assist_field(key, body[key])
            if norm is None:
                return (
                    False,
                    {},
                    {
                        "ok": False,
                        "error": f"invalid_{key}",
                        "message": f"Unsupported {key}: {body[key]!r}",
                        "allowed": list(spec["choices"]),
                    },
                )
            updates[key] = norm
    return True, updates, None


CINE_EI_BASE_VALUES: tuple[str, ...] = ("800", "12800")
CINE_EI_STEPS: dict[str, tuple[int, ...]] = {
    "800": (200, 250, 320, 400, 500, 640, 800, 1000, 1250, 1600, 2000, 2500, 3200),
    "12800": (3200, 4000, 5000, 6400, 8000, 10000, 12800, 16000, 20000, 25600, 32000, 40000, 51200),
}
SHUTTER_MODES: tuple[str, ...] = ("angle", "speed", "ecs")
SHUTTER_ANGLE_PRESETS: tuple[float, ...] = (180.0, 172.8, 90.0, 45.0, 360.0)
SHUTTER_ANGLE_MIN: float = 5.6
SHUTTER_ANGLE_MAX: float = 360.0
SHUTTER_SPEED_MIN: int = 24
SHUTTER_SPEED_MAX: int = 8000
ECS_FREQ_MIN: float = 23.98
ECS_FREQ_MAX: float = 7900.0
ECS_FREQ_PRESETS: tuple[float, ...] = (50.0, 60.0, 100.2, 120.0)
SQ_BASE_FPS_VALUES: tuple[float, ...] = (23.98, 24.0, 25.0, 29.97, 50.0, 59.94)
SQ_FPS_MIN: int = 1
SQ_FPS_MAX: int = 240
REC_STATES: tuple[str, ...] = ("STBY", "REC")
TALLY_LAMP_MODES: tuple[str, ...] = ("on", "front_only", "rear_only", "off")
WIRED_IO_MODES: tuple[str, ...] = ("off", "usblan_ptpip", "hdmi_raw16")

CINE_EXPOSURE_DEFAULTS: dict[str, Any] = {
    "cine_ei_base": "800",
    "ei_index": 800,
    "shutter_mode": "angle",
    "shutter_angle_deg": 180.0,
    "shutter_speed_denom": 48,
    "ecs_freq_hz": 60.0,
    "sq_enabled": False,
    "base_fps": 23.98,
    "sq_fps": 24,
    "rec_state": "STBY",
    "tally_lamp_mode": "on",
    "wired_io_mode": "off",
    "nd_preset": "Clear",
}

CINE_EXPOSURE_SPECS: dict[str, Any] = {
    "cine_ei_base": list(CINE_EI_BASE_VALUES),
    "ei_steps": {k: list(v) for k, v in CINE_EI_STEPS.items()},
    "shutter_modes": list(SHUTTER_MODES),
    "shutter_angle_range": [SHUTTER_ANGLE_MIN, SHUTTER_ANGLE_MAX],
    "shutter_angle_presets": list(SHUTTER_ANGLE_PRESETS),
    "shutter_speed_denom_range": [SHUTTER_SPEED_MIN, SHUTTER_SPEED_MAX],
    "ecs_freq_hz_range": [ECS_FREQ_MIN, ECS_FREQ_MAX],
    "ecs_freq_presets": list(ECS_FREQ_PRESETS),
    "sq_base_fps_values": list(SQ_BASE_FPS_VALUES),
    "sq_fps_range": [SQ_FPS_MIN, SQ_FPS_MAX],
    "rec_states": list(REC_STATES),
    "tally_lamp_modes": list(TALLY_LAMP_MODES),
    "wired_io_modes": list(WIRED_IO_MODES),
    "p4_nd_hardware_absent": True,
    "p12_bk4_airplane_mode_locked": True,
}


def compute_cine_ei_latitude(cine_ei_base: str, ei_index: int) -> dict[str, Any]:
    """Compute exact 14.0-stop Cine EI latitude (+over/-under) centered on +6.0/-8.0 at Base ISO."""
    steps = CINE_EI_STEPS[cine_ei_base]
    step_idx = steps.index(int(ei_index))
    offset_stops = round((step_idx - 6) / 3.0, 2)
    over_stops = round(6.0 + (step_idx - 6) / 3.0, 2)
    under_stops = round(14.0 - over_stops, 2)
    return {
        "ei_step_idx": step_idx,
        "offset_stops": offset_stops,
        "over_stops": over_stops,
        "under_stops": under_stops,
        "total_stops": 14.0,
        "latitude_label": f"+{over_stops:g} / -{under_stops:g}",
    }


def compute_sq_motion_metrics(sq_enabled: bool, base_fps: float, sq_fps: int) -> dict[str, Any]:
    """Compute S&Q motion ratio (sq_fps / base_fps) and FX6/FX3 S&Q audio mute invariant."""
    raw_ratio = round(float(sq_fps) / float(base_fps), 2)
    motion_ratio = raw_ratio if sq_enabled else 1.0
    if sq_enabled:
        if float(sq_fps) > float(base_fps) + 0.05:
            motion_label = f"{raw_ratio:.2f}x Slow"
        elif float(sq_fps) < float(base_fps) - 0.05:
            motion_label = f"{raw_ratio:.2f}x Quick"
        else:
            motion_label = "1.00x Normal"
    else:
        motion_label = "1.00x Normal"
    return {
        "motion_ratio": motion_ratio,
        "sq_preview_ratio": raw_ratio,
        "motion_label": motion_label,
        "audio_rec_muted_by_sq": bool(sq_enabled),
        "effective_fps": float(sq_fps) if sq_enabled else float(base_fps),
    }


def build_wired_io_detail(wired_io_mode: str) -> dict[str, Any]:
    """Return P12 Airplane-Mode-safe wired I/O descriptor for USB-LAN PTP-IP or HDMI 16-bit RAW."""
    if wired_io_mode == "usblan_ptpip":
        return {
            "mode": "usblan_ptpip",
            "protocol": "USB CDC-NCM + PTP-IP 15740",
            "usb_class": "CDC-NCM",
            "ptpip_port": 15740,
            "wifi_off": True,
            "bt_off": True,
            "p12_safe": True,
        }
    if wired_io_mode == "hdmi_raw16":
        return {
            "mode": "hdmi_raw16",
            "protocol": "HDMI 16-bit Linear RAW",
            "resolution": "4264x2408",
            "bit_depth": 16,
            "edid_target": "Atomos Ninja/Shogun",
            "mlut_clean_feed": True,
            "wifi_off": True,
            "bt_off": True,
            "p12_safe": True,
        }
    return {
        "mode": "off",
        "protocol": "Off",
        "wifi_off": True,
        "bt_off": True,
        "p12_safe": True,
    }


def format_cine_exp_command(state: dict[str, Any]) -> str:
    """Format deterministic Phase 64 CINE_EXP host<->guest serial/mailbox protocol string."""
    shutter_mode = state["shutter_mode"]
    if shutter_mode == "speed":
        sh_tok = f"speed:1/{state['shutter_speed_denom']}"
    elif shutter_mode == "ecs":
        sh_tok = f"ecs:{state['ecs_freq_hz']:.2f}Hz"
    else:
        sh_tok = f"angle:{state['shutter_angle_deg']:.1f}deg"
    return (
        f"CINE_EXP base={state['cine_ei_base']} ei={state['ei_index']} "
        f"lat={state['latitude_label'].replace(' ', '')} shutter={sh_tok} "
        f"sq={1 if state['sq_enabled'] else 0}:{state['base_fps']:.2f}:{state['sq_fps']} "
        f"rec={state['rec_state']} tally={state['tally_lamp_mode']} "
        f"io={state['wired_io_mode']} nd=Clear p12=1"
    )


def validate_cine_exposure_patch(
    body: Any,
    current_state: dict[str, Any] | None = None,
) -> tuple[bool, dict[str, Any], dict[str, Any] | None]:
    """Validate and normalize Phase 64 Cine Exposure, Shutter/ECS, S&Q, Tally & Wired I/O updates."""
    if not isinstance(body, dict):
        return (
            False,
            {},
            {
                "ok": False,
                "error": "invalid_cine_exposure",
                "message": "cine_exposure payload must be a JSON object",
            },
        )

    cur = dict(CINE_EXPOSURE_DEFAULTS)
    if current_state:
        cur.update(current_state)

    updates: dict[str, Any] = {}
    if body.get("reset") is True:
        updates.update(CINE_EXPOSURE_DEFAULTS)
        cur.update(CINE_EXPOSURE_DEFAULTS)

    # P4 Electronic Variable ND hardware-absence lock
    if "nd_preset" in body and body["nd_preset"] is not None:
        raw_nd = body["nd_preset"]
        if isinstance(raw_nd, bool) or not isinstance(raw_nd, str):
            return (
                False,
                {},
                {
                    "ok": False,
                    "error": "p4_nd_hardware_absent",
                    "p4_nd_hardware_absent": True,
                    "nd_preset": "Clear",
                    "message": "Stage-B P4 ND=Clear lock: invalid nd_preset type; FX3 body lacks physical variable ND",
                },
            )
        nd_low = raw_nd.strip().lower()
        if nd_low not in ("clear", "clear [fx3 p4 locked]"):
            return (
                False,
                {},
                {
                    "ok": False,
                    "error": "p4_nd_hardware_absent",
                    "p4_nd_hardware_absent": True,
                    "nd_preset": "Clear",
                    "rejected_nd": raw_nd,
                    "message": (
                        f"Stage-B P4 Hardware Lock: FX3 body lacks electronic variable ND; "
                        f"rejected nd_preset={raw_nd!r} and locked to 'Clear'"
                    ),
                },
            )
        updates["nd_preset"] = "Clear"

    # P12 Airplane-Mode RF-OFF lock
    if (
        body.get("wifi_enabled") is True
        or body.get("bt_enabled") is True
        or body.get("wifi_bt_rf_disabled") is False
        or body.get("p12_bk4_airplane_mode_locked") is False
    ):
        return (
            False,
            {},
            {
                "ok": False,
                "error": "p12_airplane_mode_locked",
                "wifi_bt_rf_disabled": True,
                "p12_bk4_airplane_mode_locked": True,
                "message": "Stage-B P12 BK4 Airplane-Mode invariant: Wi-Fi/BT RF cannot be enabled",
            },
        )

    eff_base = str(cur.get("cine_ei_base", "800"))
    if "cine_ei_base" in body and body["cine_ei_base"] is not None:
        raw_base = body["cine_ei_base"]
        if isinstance(raw_base, bool) or not isinstance(raw_base, (str, int)):
            return (
                False,
                {},
                {"ok": False, "error": "invalid_cine_ei_base", "message": f"Invalid cine_ei_base: {raw_base!r}"},
            )
        norm_base = str(raw_base).strip()
        if norm_base not in CINE_EI_BASE_VALUES:
            return (
                False,
                {},
                {
                    "ok": False,
                    "error": "invalid_cine_ei_base",
                    "message": f"Unsupported cine_ei_base: {raw_base!r}",
                    "allowed": list(CINE_EI_BASE_VALUES),
                },
            )
        eff_base = norm_base
        updates["cine_ei_base"] = eff_base

    if "ei_index" in body and body["ei_index"] is not None:
        raw_ei = body["ei_index"]
        if isinstance(raw_ei, bool):
            return False, {}, {"ok": False, "error": "invalid_ei_index", "message": "ei_index cannot be bool"}
        if isinstance(raw_ei, float):
            if not math.isfinite(raw_ei) or not raw_ei.is_integer():
                return False, {}, {"ok": False, "error": "invalid_ei_index", "message": f"ei_index must be integer: {raw_ei!r}"}
            ei_val = int(raw_ei)
        elif isinstance(raw_ei, int):
            ei_val = raw_ei
        elif isinstance(raw_ei, str) and raw_ei.strip().isdigit():
            ei_val = int(raw_ei.strip())
        else:
            return False, {}, {"ok": False, "error": "invalid_ei_index", "message": f"Invalid ei_index: {raw_ei!r}"}
        allowed_ei = CINE_EI_STEPS[eff_base]
        if ei_val not in allowed_ei:
            return (
                False,
                {},
                {
                    "ok": False,
                    "error": "invalid_ei_index",
                    "message": f"EI {ei_val} is invalid for Base {eff_base}",
                    "allowed": list(allowed_ei),
                },
            )
        updates["ei_index"] = ei_val
    elif "cine_ei_base" in updates:
        cur_ei = int(cur.get("ei_index", 800))
        if cur_ei not in CINE_EI_STEPS[eff_base]:
            updates["ei_index"] = int(eff_base)

    if "shutter_mode" in body and body["shutter_mode"] is not None:
        raw_sm = body["shutter_mode"]
        if isinstance(raw_sm, bool) or not isinstance(raw_sm, str):
            return False, {}, {"ok": False, "error": "invalid_shutter_mode", "message": f"Invalid shutter_mode: {raw_sm!r}"}
        sm_low = raw_sm.strip().lower()
        if sm_low not in SHUTTER_MODES:
            return (
                False,
                {},
                {
                    "ok": False,
                    "error": "invalid_shutter_mode",
                    "message": f"Unsupported shutter_mode: {raw_sm!r}",
                    "allowed": list(SHUTTER_MODES),
                },
            )
        updates["shutter_mode"] = sm_low

    if "shutter_angle_deg" in body and body["shutter_angle_deg"] is not None:
        raw_ang = body["shutter_angle_deg"]
        if isinstance(raw_ang, bool):
            return False, {}, {"ok": False, "error": "invalid_shutter_angle_deg", "message": "shutter_angle_deg cannot be bool"}
        try:
            ang = float(raw_ang)
        except (TypeError, ValueError):
            return False, {}, {"ok": False, "error": "invalid_shutter_angle_deg", "message": f"Non-numeric shutter_angle_deg: {raw_ang!r}"}
        if not math.isfinite(ang) or ang < SHUTTER_ANGLE_MIN or ang > SHUTTER_ANGLE_MAX:
            return (
                False,
                {},
                {
                    "ok": False,
                    "error": "invalid_shutter_angle_deg",
                    "message": f"shutter_angle_deg must be in [{SHUTTER_ANGLE_MIN}, {SHUTTER_ANGLE_MAX}], got {ang!r}",
                },
            )
        updates["shutter_angle_deg"] = round(ang, 1)

    if "shutter_speed_denom" in body and body["shutter_speed_denom"] is not None:
        raw_den = body["shutter_speed_denom"]
        if isinstance(raw_den, bool):
            return False, {}, {"ok": False, "error": "invalid_shutter_speed_denom", "message": "shutter_speed_denom cannot be bool"}
        if isinstance(raw_den, float):
            if not math.isfinite(raw_den) or not raw_den.is_integer():
                return False, {}, {"ok": False, "error": "invalid_shutter_speed_denom", "message": f"shutter_speed_denom must be int: {raw_den!r}"}
            den = int(raw_den)
        elif isinstance(raw_den, int):
            den = raw_den
        elif isinstance(raw_den, str) and raw_den.strip().isdigit():
            den = int(raw_den.strip())
        else:
            return False, {}, {"ok": False, "error": "invalid_shutter_speed_denom", "message": f"Invalid shutter_speed_denom: {raw_den!r}"}
        if den < SHUTTER_SPEED_MIN or den > SHUTTER_SPEED_MAX:
            return (
                False,
                {},
                {
                    "ok": False,
                    "error": "invalid_shutter_speed_denom",
                    "message": f"shutter_speed_denom must be in [{SHUTTER_SPEED_MIN}, {SHUTTER_SPEED_MAX}], got {den}",
                },
            )
        updates["shutter_speed_denom"] = den

    if "ecs_freq_hz" in body and body["ecs_freq_hz"] is not None:
        raw_ecs = body["ecs_freq_hz"]
        if isinstance(raw_ecs, bool):
            return False, {}, {"ok": False, "error": "invalid_ecs_freq_hz", "message": "ecs_freq_hz cannot be bool"}
        try:
            ecs = float(raw_ecs)
        except (TypeError, ValueError):
            return False, {}, {"ok": False, "error": "invalid_ecs_freq_hz", "message": f"Non-numeric ecs_freq_hz: {raw_ecs!r}"}
        if not math.isfinite(ecs) or ecs < ECS_FREQ_MIN or ecs > ECS_FREQ_MAX:
            return (
                False,
                {},
                {
                    "ok": False,
                    "error": "invalid_ecs_freq_hz",
                    "message": f"ecs_freq_hz must be in [{ECS_FREQ_MIN}, {ECS_FREQ_MAX}], got {ecs!r}",
                },
            )
        updates["ecs_freq_hz"] = round(ecs, 2)

    if "sq_enabled" in body and body["sq_enabled"] is not None:
        raw_sq = body["sq_enabled"]
        if not isinstance(raw_sq, bool):
            return False, {}, {"ok": False, "error": "invalid_sq_enabled", "message": f"sq_enabled must be bool, got {raw_sq!r}"}
        updates["sq_enabled"] = raw_sq

    if "base_fps" in body and body["base_fps"] is not None:
        raw_bf = body["base_fps"]
        if isinstance(raw_bf, bool):
            return False, {}, {"ok": False, "error": "invalid_base_fps", "message": "base_fps cannot be bool"}
        try:
            bf = float(raw_bf)
        except (TypeError, ValueError):
            return False, {}, {"ok": False, "error": "invalid_base_fps", "message": f"Invalid base_fps: {raw_bf!r}"}
        if not math.isfinite(bf):
            return False, {}, {"ok": False, "error": "invalid_base_fps", "message": "base_fps must be finite"}
        matched_bf = next((cand for cand in SQ_BASE_FPS_VALUES if abs(cand - bf) < 1e-3), None)
        if matched_bf is None:
            return (
                False,
                {},
                {
                    "ok": False,
                    "error": "invalid_base_fps",
                    "message": f"Unsupported base_fps: {raw_bf!r}",
                    "allowed": list(SQ_BASE_FPS_VALUES),
                },
            )
        updates["base_fps"] = matched_bf

    if "sq_fps" in body and body["sq_fps"] is not None:
        raw_sf = body["sq_fps"]
        if isinstance(raw_sf, bool):
            return False, {}, {"ok": False, "error": "invalid_sq_fps", "message": "sq_fps cannot be bool"}
        if isinstance(raw_sf, float):
            if not math.isfinite(raw_sf) or not raw_sf.is_integer():
                return False, {}, {"ok": False, "error": "invalid_sq_fps", "message": f"sq_fps must be integer 1..240, got {raw_sf!r}"}
            sf = int(raw_sf)
        elif isinstance(raw_sf, int):
            sf = raw_sf
        elif isinstance(raw_sf, str) and raw_sf.strip().isdigit():
            sf = int(raw_sf.strip())
        else:
            return False, {}, {"ok": False, "error": "invalid_sq_fps", "message": f"Invalid sq_fps: {raw_sf!r}"}
        if sf < SQ_FPS_MIN or sf > SQ_FPS_MAX:
            return (
                False,
                {},
                {
                    "ok": False,
                    "error": "invalid_sq_fps",
                    "message": f"sq_fps must be in [{SQ_FPS_MIN}, {SQ_FPS_MAX}], got {sf}",
                },
            )
        updates["sq_fps"] = sf

    if "rec_state" in body and body["rec_state"] is not None:
        raw_rs = body["rec_state"]
        if isinstance(raw_rs, bool) or not isinstance(raw_rs, str):
            return False, {}, {"ok": False, "error": "invalid_rec_state", "message": f"Invalid rec_state: {raw_rs!r}"}
        rs_up = raw_rs.strip().upper()
        if rs_up not in REC_STATES:
            return (
                False,
                {},
                {
                    "ok": False,
                    "error": "invalid_rec_state",
                    "message": f"Unsupported rec_state: {raw_rs!r}",
                    "allowed": list(REC_STATES),
                },
            )
        updates["rec_state"] = rs_up

    if "tally_lamp_mode" in body and body["tally_lamp_mode"] is not None:
        raw_tl = body["tally_lamp_mode"]
        if isinstance(raw_tl, bool) or not isinstance(raw_tl, str):
            return False, {}, {"ok": False, "error": "invalid_tally_lamp_mode", "message": f"Invalid tally_lamp_mode: {raw_tl!r}"}
        tl_low = raw_tl.strip().lower()
        if tl_low not in TALLY_LAMP_MODES:
            return (
                False,
                {},
                {
                    "ok": False,
                    "error": "invalid_tally_lamp_mode",
                    "message": f"Unsupported tally_lamp_mode: {raw_tl!r}",
                    "allowed": list(TALLY_LAMP_MODES),
                },
            )
        updates["tally_lamp_mode"] = tl_low

    if "wired_io_mode" in body and body["wired_io_mode"] is not None:
        raw_io = body["wired_io_mode"]
        if isinstance(raw_io, bool) or not isinstance(raw_io, str):
            return False, {}, {"ok": False, "error": "invalid_wired_io_mode", "message": f"Invalid wired_io_mode: {raw_io!r}"}
        io_low = raw_io.strip().lower()
        if io_low not in WIRED_IO_MODES:
            return (
                False,
                {},
                {
                    "ok": False,
                    "error": "invalid_wired_io_mode",
                    "message": f"Unsupported wired_io_mode: {raw_io!r}",
                    "allowed": list(WIRED_IO_MODES),
                },
            )
        updates["wired_io_mode"] = io_low

    return True, updates, None


WB_MODES: tuple[str, ...] = (
    "preset_3200k",
    "preset_4300k",
    "preset_5600k",
    "mem_a",
    "mem_b",
    "atw",
)
WB_PRESET_KELVIN: dict[str, int] = {
    "preset_3200k": 3200,
    "preset_4300k": 4300,
    "preset_5600k": 5600,
}
WB_KELVIN_MIN: int = 2000
WB_KELVIN_MAX: int = 15000
WB_KELVIN_STEP: int = 50
WB_TINT_MIN: int = -99
WB_TINT_MAX: int = 99
SHOCKLESS_WB_MODES: tuple[str, ...] = ("off", "1", "2", "3")
SHOCKLESS_WB_TAU_SEC: dict[str, float] = {"off": 0.0, "1": 0.65, "2": 1.60, "3": 3.20}

BASE_LOOK_VALUES: tuple[str, ...] = (
    "S-Cinetone",
    "S-Log3 / S-Gamut3.Cine",
    "S-Log3 / S-Gamut3",
    "ITU709",
    "709(800%)",
    "HLG Live",
    "User 3D LUT",
)
BASE_LOOK_NLE_TAGS: dict[str, dict[str, Any]] = {
    "S-Cinetone": {
        "capture_gamma_equation": "s-cinetone",
        "capture_color_primaries": "rec709",
        "cell_lut_idx": 0,
        "guest_idx": 0,
    },
    "S-Log3 / S-Gamut3.Cine": {
        "capture_gamma_equation": "s-log3-cine",
        "capture_color_primaries": "s-gamut3-cine",
        "cell_lut_idx": 1,
        "guest_idx": 1,
    },
    "S-Log3 / S-Gamut3": {
        "capture_gamma_equation": "s-log3",
        "capture_color_primaries": "s-gamut3",
        "cell_lut_idx": 1,
        "guest_idx": 2,
    },
    "ITU709": {
        "capture_gamma_equation": "rec709",
        "capture_color_primaries": "rec709",
        "cell_lut_idx": 2,
        "guest_idx": 3,
    },
    "709(800%)": {
        "capture_gamma_equation": "rec709-800",
        "capture_color_primaries": "rec709",
        "cell_lut_idx": 3,
        "guest_idx": 4,
    },
    "HLG Live": {
        "capture_gamma_equation": "rec2100-hlg",
        "capture_color_primaries": "rec2020",
        "cell_lut_idx": 2,
        "guest_idx": 5,
    },
    "User 3D LUT": {
        "capture_gamma_equation": "s-log3-cine",
        "capture_color_primaries": "s-gamut3-cine",
        "cell_lut_idx": 4,
        "guest_idx": 6,
    },
}
_BASE_LOOK_ALIASES: dict[str, str] = {
    "s-cinetone": "S-Cinetone",
    "scinetone": "S-Cinetone",
    "s-log3 / s-gamut3.cine": "S-Log3 / S-Gamut3.Cine",
    "s-log3.cine / s-gamut3.cine": "S-Log3 / S-Gamut3.Cine",
    "s-log3.cine": "S-Log3 / S-Gamut3.Cine",
    "slog3.cine": "S-Log3 / S-Gamut3.Cine",
    "s-log3 / s-gamut3": "S-Log3 / S-Gamut3",
    "s-log3": "S-Log3 / S-Gamut3",
    "slog3": "S-Log3 / S-Gamut3",
    "itu709": "ITU709",
    "s709": "ITU709",
    "709(800%)": "709(800%)",
    "r709 (800%)": "709(800%)",
    "709_800": "709(800%)",
    "hlg live": "HLG Live",
    "hlg_live": "HLG Live",
    "user 3d lut": "User 3D LUT",
    "user_3d_lut": "User 3D LUT",
    "user lut": "User 3D LUT",
}

CAM_POS_VALUES: tuple[str, ...] = ("C", "L", "R")
DUAL_SLOT_MODES: tuple[str, ...] = ("simul", "relay", "sort_main_proxy", "single_slot_a")
PROXY_MODES: tuple[str, ...] = (
    "xavc_hs_1080p_16m",
    "xavc_hs_1080p_9m",
    "xavc_s_720p_6m",
    "off",
)
PROXY_MODE_DETAILS: dict[str, dict[str, Any]] = {
    "xavc_hs_1080p_16m": {"codec": "XAVC HS (HEVC)", "resolution": "1920x1080", "bit_depth": 10, "bitrate_mbps": 16.0},
    "xavc_hs_1080p_9m": {"codec": "XAVC HS (HEVC)", "resolution": "1920x1080", "bit_depth": 10, "bitrate_mbps": 9.0},
    "xavc_s_720p_6m": {"codec": "XAVC S (H.264)", "resolution": "1280x720", "bit_depth": 8, "bitrate_mbps": 6.0},
    "off": {"codec": "Off", "resolution": None, "bit_depth": None, "bitrate_mbps": 0.0},
}
DEFAULT_CLIP_DATE_YYMMDD: str = "261114"
DEFAULT_CLIP_CAM_UID: str = "FX3B"
NRTM_NAMESPACE_V220: str = "urn:schemas-professionalDisc:nonRealTimeMeta:ver.2.20"
NRTM_LIB_NAMESPACE_V220: str = "urn:schemas-professionalDisc:lib:ver.2.20"

COLOR_AND_MEDIA_DEFAULTS: dict[str, Any] = {
    "wb_mode": "preset_5600k",
    "kelvin": 5600,
    "tint_gm": 0,
    "shockless_wb": "off",
    "base_look": "S-Cinetone",
    "cam_id": "A",
    "reel_num": 1,
    "cam_pos": "C",
    "clip_seq": 1,
    "dual_slot_mode": "simul",
    "proxy_mode": "xavc_hs_1080p_16m",
}

COLOR_AND_MEDIA_SPECS: dict[str, Any] = {
    "wb_modes": list(WB_MODES),
    "wb_preset_kelvin": dict(WB_PRESET_KELVIN),
    "kelvin_range": [WB_KELVIN_MIN, WB_KELVIN_MAX],
    "kelvin_step": WB_KELVIN_STEP,
    "tint_gm_range": [WB_TINT_MIN, WB_TINT_MAX],
    "shockless_wb_modes": list(SHOCKLESS_WB_MODES),
    "shockless_wb_tau_sec": dict(SHOCKLESS_WB_TAU_SEC),
    "fx3_wb_switch_soft_mapped": True,
    "base_looks": list(BASE_LOOK_VALUES),
    "base_look_nle_tags": {
        k: {
            "capture_gamma_equation": v["capture_gamma_equation"],
            "capture_color_primaries": v["capture_color_primaries"],
        }
        for k, v in BASE_LOOK_NLE_TAGS.items()
    },
    "cam_id_range": ["A", "Z"],
    "reel_num_range": [1, 999],
    "cam_pos_values": list(CAM_POS_VALUES),
    "clip_seq_range": [1, 999],
    "dual_slot_modes": list(DUAL_SLOT_MODES),
    "proxy_modes": list(PROXY_MODES),
    "nrtm_namespace": NRTM_NAMESPACE_V220,
}


def compute_color_and_media_derived(
    state: dict[str, Any],
    *,
    sq_enabled: bool = False,
    active_user_lut: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute NLE color tags, Cinema Line clip/proxy names, and S&Q proxy suspension."""
    wb_mode = str(state["wb_mode"])
    kelvin = WB_PRESET_KELVIN[wb_mode] if wb_mode in WB_PRESET_KELVIN else int(state["kelvin"])
    tint_gm = int(state["tint_gm"])
    shockless_wb = str(state["shockless_wb"])
    base_look = str(state["base_look"])
    look_meta = BASE_LOOK_NLE_TAGS[base_look]

    cam_id = str(state["cam_id"])
    reel_num = int(state["reel_num"])
    cam_pos = str(state["cam_pos"])
    clip_seq = int(state["clip_seq"])
    dual_slot_mode = str(state["dual_slot_mode"])
    proxy_mode = str(state["proxy_mode"])

    clip_id = f"{cam_id}{reel_num:03d}{cam_pos}{clip_seq:03d}"
    clip_basename = f"{clip_id}_{DEFAULT_CLIP_DATE_YYMMDD}_{DEFAULT_CLIP_CAM_UID}"
    main_clip_name = f"{clip_basename}.MP4"
    proxy_clip_name = f"{clip_basename}S03.MP4"
    sidecar_xml_name = f"{clip_basename}M01.XML"

    proxy_requested = proxy_mode != "off"
    proxy_auto_suspended_by_sq = bool(sq_enabled)
    proxy_effective_active = bool(proxy_requested and not sq_enabled)

    return {
        "wb_mode": wb_mode,
        "kelvin": kelvin,
        "kelvin_locked": wb_mode in WB_PRESET_KELVIN,
        "tint_gm": tint_gm,
        "wb_display": f"{kelvin}K{tint_gm:+d}",
        "shockless_wb": shockless_wb,
        "shockless_tau_sec": SHOCKLESS_WB_TAU_SEC[shockless_wb],
        "fx3_wb_switch_soft_mapped": True,
        "base_look": base_look,
        "capture_gamma_equation": look_meta["capture_gamma_equation"],
        "capture_color_primaries": look_meta["capture_color_primaries"],
        "active_user_lut_slot": active_user_lut.get("slot") if (base_look == "User 3D LUT" and active_user_lut) else None,
        "active_user_lut": dict(active_user_lut) if (base_look == "User 3D LUT" and active_user_lut) else None,
        "cam_id": cam_id,
        "reel_num": reel_num,
        "cam_pos": cam_pos,
        "clip_seq": clip_seq,
        "clip_id": clip_id,
        "clip_basename": clip_basename,
        "main_clip_name": main_clip_name,
        "proxy_clip_name": proxy_clip_name,
        "proxy_active_clip_name": proxy_clip_name if proxy_effective_active else None,
        "sidecar_xml_name": sidecar_xml_name,
        "main_relpath": f"M4ROOT/CLIP/{main_clip_name}",
        "proxy_relpath": f"M4ROOT/SUB/{proxy_clip_name}" if proxy_effective_active else None,
        "sidecar_xml_relpath": f"M4ROOT/CLIP/{sidecar_xml_name}",
        "dual_slot_mode": dual_slot_mode,
        "proxy_mode": proxy_mode,
        "proxy_detail": dict(PROXY_MODE_DETAILS[proxy_mode]),
        "proxy_requested": proxy_requested,
        "proxy_effective_active": proxy_effective_active,
        "proxy_auto_suspended_by_sq": proxy_auto_suspended_by_sq,
    }


def format_wb_media_command(state: dict[str, Any]) -> str:
    """Format deterministic Phase 73 WB_MEDIA host<->guest protocol string."""
    return (
        f"WB_MEDIA wb={state['wb_mode']}:{state['kelvin']}K:{state['tint_gm']:+d} "
        f"shockless={state['shockless_wb']} look=\"{state['base_look']}\" "
        f"gamma={state['capture_gamma_equation']} primaries={state['capture_color_primaries']} "
        f"clip={state['main_clip_name']} slot={state['dual_slot_mode']} "
        f"proxy={state['proxy_mode']} eff={1 if state['proxy_effective_active'] else 0} "
        f"sq_susp={1 if state['proxy_auto_suspended_by_sq'] else 0}"
    )


def _parse_strict_int(raw: Any) -> int | None:
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw
    if isinstance(raw, float):
        if not math.isfinite(raw) or not raw.is_integer():
            return None
        return int(raw)
    if isinstance(raw, str):
        s = raw.strip()
        if not s:
            return None
        if s[0] in ("+", "-"):
            if len(s) > 1 and s[1:].isdigit():
                return int(s)
            return None
        if s.isdigit():
            return int(s)
    return None


def validate_color_and_media_patch(
    body: Any,
    current_state: dict[str, Any] | None = None,
) -> tuple[bool, dict[str, Any], dict[str, Any] | None]:
    """Validate and normalize Phase 73 White Balance, Base Look, CamID/Reel & Dual-Slot updates."""
    if not isinstance(body, dict):
        return (
            False,
            {},
            {
                "ok": False,
                "error": "invalid_color_and_media",
                "message": "color_and_media payload must be a JSON object",
            },
        )

    cur = dict(COLOR_AND_MEDIA_DEFAULTS)
    if current_state:
        cur.update(current_state)

    updates: dict[str, Any] = {}
    if body.get("reset") is True:
        updates.update(COLOR_AND_MEDIA_DEFAULTS)
        cur.update(COLOR_AND_MEDIA_DEFAULTS)

    eff_wb_mode = str(cur.get("wb_mode", "preset_5600k"))
    if "wb_mode" in body and body["wb_mode"] is not None:
        raw_wb = body["wb_mode"]
        if isinstance(raw_wb, bool) or not isinstance(raw_wb, str):
            return False, {}, {"ok": False, "error": "invalid_wb_mode", "message": f"Invalid wb_mode: {raw_wb!r}"}
        wb_low = raw_wb.strip().lower()
        if wb_low not in WB_MODES:
            return (
                False,
                {},
                {
                    "ok": False,
                    "error": "invalid_wb_mode",
                    "message": f"Unsupported wb_mode: {raw_wb!r}",
                    "allowed": list(WB_MODES),
                },
            )
        eff_wb_mode = wb_low
        updates["wb_mode"] = eff_wb_mode

    if "kelvin" in body and body["kelvin"] is not None:
        k_val = _parse_strict_int(body["kelvin"])
        if k_val is None or k_val < WB_KELVIN_MIN or k_val > WB_KELVIN_MAX:
            return (
                False,
                {},
                {
                    "ok": False,
                    "error": "invalid_kelvin",
                    "message": f"kelvin must be an integer in [{WB_KELVIN_MIN}, {WB_KELVIN_MAX}], got {body['kelvin']!r}",
                },
            )
        if eff_wb_mode in WB_PRESET_KELVIN:
            updates["kelvin"] = WB_PRESET_KELVIN[eff_wb_mode]
        else:
            snapped = int(round(float(k_val) / float(WB_KELVIN_STEP))) * WB_KELVIN_STEP
            updates["kelvin"] = max(WB_KELVIN_MIN, min(WB_KELVIN_MAX, snapped))
    elif eff_wb_mode in WB_PRESET_KELVIN:
        updates["kelvin"] = WB_PRESET_KELVIN[eff_wb_mode]

    if "tint_gm" in body and body["tint_gm"] is not None:
        t_val = _parse_strict_int(body["tint_gm"])
        if t_val is None or t_val < WB_TINT_MIN or t_val > WB_TINT_MAX:
            return (
                False,
                {},
                {
                    "ok": False,
                    "error": "invalid_tint_gm",
                    "message": f"tint_gm must be an integer in [{WB_TINT_MIN}, {WB_TINT_MAX}], got {body['tint_gm']!r}",
                },
            )
        updates["tint_gm"] = t_val

    if "shockless_wb" in body and body["shockless_wb"] is not None:
        raw_sl = body["shockless_wb"]
        if isinstance(raw_sl, bool):
            return False, {}, {"ok": False, "error": "invalid_shockless_wb", "message": "shockless_wb cannot be bool"}
        if isinstance(raw_sl, int) and raw_sl in (1, 2, 3):
            sl_norm = str(raw_sl)
        elif isinstance(raw_sl, str):
            sl_norm = raw_sl.strip().lower()
        else:
            sl_norm = ""
        if sl_norm not in SHOCKLESS_WB_MODES:
            return (
                False,
                {},
                {
                    "ok": False,
                    "error": "invalid_shockless_wb",
                    "message": f"Unsupported shockless_wb: {raw_sl!r}",
                    "allowed": list(SHOCKLESS_WB_MODES),
                },
            )
        updates["shockless_wb"] = sl_norm

    if "base_look" in body and body["base_look"] is not None:
        raw_lk = body["base_look"]
        if isinstance(raw_lk, bool) or not isinstance(raw_lk, str):
            return False, {}, {"ok": False, "error": "invalid_base_look", "message": f"Invalid base_look: {raw_lk!r}"}
        lk_key = raw_lk.strip().lower()
        lk_norm = _BASE_LOOK_ALIASES.get(lk_key)
        if lk_norm is None:
            for cand in BASE_LOOK_VALUES:
                if cand.lower() == lk_key:
                    lk_norm = cand
                    break
        if lk_norm is None:
            return (
                False,
                {},
                {
                    "ok": False,
                    "error": "invalid_base_look",
                    "message": f"Unsupported base_look: {raw_lk!r}",
                    "allowed": list(BASE_LOOK_VALUES),
                },
            )
        updates["base_look"] = lk_norm

    if "user_lut_slot" in body and body["user_lut_slot"] is not None:
        raw_us = body["user_lut_slot"]
        if isinstance(raw_us, bool) or not isinstance(raw_us, str):
            return False, {}, {"ok": False, "error": "invalid_user_lut_slot", "message": f"Invalid user_lut_slot: {raw_us!r}"}
        norm_us = FX6LiveGpe0Session._normalize_lut_slot(raw_us)
        if norm_us is None:
            return (
                False,
                {},
                {
                    "ok": False,
                    "error": "invalid_user_lut_slot",
                    "message": f"Unsupported user_lut_slot: {raw_us!r} (expected User1..User4)",
                },
            )
        updates["user_lut_slot"] = norm_us
        if "base_look" not in updates:
            updates["base_look"] = "User 3D LUT"

    if "cam_id" in body and body["cam_id"] is not None:
        raw_cid = body["cam_id"]
        if isinstance(raw_cid, bool) or not isinstance(raw_cid, str):
            return False, {}, {"ok": False, "error": "invalid_cam_id", "message": f"Invalid cam_id: {raw_cid!r}"}
        cid = raw_cid.strip().upper()
        if len(cid) != 1 or not ("A" <= cid <= "Z"):
            return (
                False,
                {},
                {"ok": False, "error": "invalid_cam_id", "message": f"cam_id must be a single letter A..Z, got {raw_cid!r}"},
            )
        updates["cam_id"] = cid

    if "reel_num" in body and body["reel_num"] is not None:
        r_val = _parse_strict_int(body["reel_num"])
        if r_val is None or r_val < 1 or r_val > 999:
            return (
                False,
                {},
                {"ok": False, "error": "invalid_reel_num", "message": f"reel_num must be in [1, 999], got {body['reel_num']!r}"},
            )
        updates["reel_num"] = r_val

    if "cam_pos" in body and body["cam_pos"] is not None:
        raw_cp = body["cam_pos"]
        if isinstance(raw_cp, bool) or not isinstance(raw_cp, str):
            return False, {}, {"ok": False, "error": "invalid_cam_pos", "message": f"Invalid cam_pos: {raw_cp!r}"}
        cp_up = raw_cp.strip().upper()
        if cp_up not in CAM_POS_VALUES:
            return (
                False,
                {},
                {"ok": False, "error": "invalid_cam_pos", "message": f"cam_pos must be one of {CAM_POS_VALUES}, got {raw_cp!r}"},
            )
        updates["cam_pos"] = cp_up

    if "clip_seq" in body and body["clip_seq"] is not None:
        c_val = _parse_strict_int(body["clip_seq"])
        if c_val is None or c_val < 1 or c_val > 999:
            return (
                False,
                {},
                {"ok": False, "error": "invalid_clip_seq", "message": f"clip_seq must be in [1, 999], got {body['clip_seq']!r}"},
            )
        updates["clip_seq"] = c_val

    if "dual_slot_mode" in body and body["dual_slot_mode"] is not None:
        raw_ds = body["dual_slot_mode"]
        if isinstance(raw_ds, bool) or not isinstance(raw_ds, str):
            return False, {}, {"ok": False, "error": "invalid_dual_slot_mode", "message": f"Invalid dual_slot_mode: {raw_ds!r}"}
        ds_low = raw_ds.strip().lower()
        if ds_low not in DUAL_SLOT_MODES:
            return (
                False,
                {},
                {
                    "ok": False,
                    "error": "invalid_dual_slot_mode",
                    "message": f"Unsupported dual_slot_mode: {raw_ds!r}",
                    "allowed": list(DUAL_SLOT_MODES),
                },
            )
        updates["dual_slot_mode"] = ds_low

    if "proxy_mode" in body and body["proxy_mode"] is not None:
        raw_pm = body["proxy_mode"]
        if isinstance(raw_pm, bool) or not isinstance(raw_pm, str):
            return False, {}, {"ok": False, "error": "invalid_proxy_mode", "message": f"Invalid proxy_mode: {raw_pm!r}"}
        pm_low = raw_pm.strip().lower()
        if pm_low not in PROXY_MODES:
            return (
                False,
                {},
                {
                    "ok": False,
                    "error": "invalid_proxy_mode",
                    "message": f"Unsupported proxy_mode: {raw_pm!r}",
                    "allowed": list(PROXY_MODES),
                },
            )
        updates["proxy_mode"] = pm_low

    return True, updates, None


def build_nrtm_xml_sidecar(
    cine_exposure: dict[str, Any],
    color_and_media: dict[str, Any],
    *,
    active_user_lut: dict[str, Any] | None = None,
    shotmark_and_iris: dict[str, Any] | None = None,
    gyroflow_anamorphic: dict[str, Any] | None = None,
    interval_cache_lut_ftp: dict[str, Any] | None = None,
    mc_fleet_sdi_c2pa: dict[str, Any] | None = None,
    hdr_hlg_raw_breathing: dict[str, Any] | None = None,
    uvc_srt_crsdk_ptp: dict[str, Any] | None = None,
) -> str:
    """Build deterministic Sony NonRealTimeMeta v2.20 (*M01.XML) reflecting live FX6-on-FX3 RAM state."""
    ET.register_namespace("", NRTM_NAMESPACE_V220)
    ET.register_namespace("lib", NRTM_LIB_NAMESPACE_V220)

    def _q(tag: str) -> str:
        return f"{{{NRTM_NAMESPACE_V220}}}{tag}"

    shotmarks_list = list(shotmark_and_iris.get("shotmarks", [])) if shotmark_and_iris else []
    max_mark_frame = max((int(m.get("frame", 0)) + 1 for m in shotmarks_list), default=0)

    clip_id = str(color_and_media.get("clip_id", "A001C001"))
    umid_ref = f"060A2B340101010501010D4313000000{clip_id}{DEFAULT_CLIP_DATE_YYMMDD}FX"
    creation_ts = "2026-11-14T16:00:00-08:00"
    duration_frames = max(240, int(cine_exposure.get("rec_tc_frames", 0)), max_mark_frame)

    base_fps = float(cine_exposure.get("base_fps", 23.98))
    eff_fps = float(cine_exposure.get("effective_fps", base_fps))
    fmt_fps_str = f"{base_fps:.2f}p"
    cap_fps_str = f"{eff_fps:.2f}p"

    ei_index = int(cine_exposure.get("ei_index", 800))
    cine_ei_base = int(cine_exposure.get("cine_ei_base", "800"))
    ei_offset_stops = round(math.log2(float(ei_index) / float(cine_ei_base)), 4)

    gamma_eq = str(color_and_media.get("capture_gamma_equation", "s-cinetone"))
    primaries = str(color_and_media.get("capture_color_primaries", "rec709"))
    base_look = str(color_and_media.get("base_look", "S-Cinetone"))
    if hdr_hlg_raw_breathing:
        if str(hdr_hlg_raw_breathing.get("hlg_profile", "OFF")) != "OFF":
            gamma_eq = str(hdr_hlg_raw_breathing.get("capture_gamma_equation", "rec2100-hlg"))
        if str(hdr_hlg_raw_breathing.get("color_gamut", "BT.709")) == "BT.2020":
            primaries = "rec2020"

    if base_look == "User 3D LUT" and active_user_lut:
        lut_slot = str(active_user_lut.get("slot", "User1"))
        monitoring_lut_cube = f"{lut_slot}.cube"
        monitoring_lut_name = str(active_user_lut.get("name", monitoring_lut_cube))
        monitoring_lut_title = str(active_user_lut.get("title") or monitoring_lut_name)
        monitoring_lut_sha = str(active_user_lut.get("sha256") or "none")
        monitoring_lut_res33_sha = str(active_user_lut.get("resampled_33_sha256") or monitoring_lut_sha)
    elif active_user_lut and active_user_lut.get("uploaded"):
        lut_slot = str(active_user_lut.get("slot", "User1"))
        monitoring_lut_cube = f"{lut_slot}.cube"
        monitoring_lut_name = str(active_user_lut.get("name", monitoring_lut_cube))
        monitoring_lut_title = str(active_user_lut.get("title") or monitoring_lut_name)
        monitoring_lut_sha = str(active_user_lut.get("sha256") or "none")
        monitoring_lut_res33_sha = str(active_user_lut.get("resampled_33_sha256") or monitoring_lut_sha)
    else:
        monitoring_lut_cube = "S709.cube" if gamma_eq.startswith("s-log3") else "R709.cube"
        monitoring_lut_name = base_look
        monitoring_lut_title = base_look
        monitoring_lut_sha = "none"
        monitoring_lut_res33_sha = "none"

    root = ET.Element(_q("NonRealTimeMeta"), {"lastUpdate": creation_ts})
    ET.SubElement(root, _q("TargetMaterial"), {"umidRef": umid_ref})
    ET.SubElement(root, _q("Duration"), {"value": str(duration_frames)})
    ET.SubElement(root, _q("CreationDate"), {"value": creation_ts})

    vfmt = ET.SubElement(root, _q("VideoFormat"))
    ET.SubElement(vfmt, _q("VideoRecPort"), {"port": "DIRECT"})
    ET.SubElement(
        vfmt,
        _q("VideoFrame"),
        {"videoCodec": "XAVC_S_4K", "captureFps": cap_fps_str, "formatFps": fmt_fps_str},
    )
    ET.SubElement(
        vfmt,
        _q("VideoLayout"),
        {"pixel": "3840", "numOfVerticalLine": "2160", "aspectRatio": "16:9"},
    )

    ET.SubElement(
        root,
        _q("Device"),
        {
            "manufacturer": "Sony",
            "modelName": "ILME-FX3",
            "serialNo": "00000000",
            "ver": "7.02-stageB-ram-overlay",
        },
    )

    if gyroflow_anamorphic:
        sq_factor = float(gyroflow_anamorphic.get("squeeze_factor", 1.0))
        lenses_el = ET.SubElement(root, _q("Lenses"))
        ET.SubElement(
            lenses_el,
            _q("Lens"),
            {
                "modelName": "E-Mount Anamorphic" if sq_factor > 1.0 else "FE 35mm F1.4 GM",
                "anamorphicSqueezeFactor": f"{sq_factor:.2f}",
                "desqueezeDisplay": str(gyroflow_anamorphic.get("squeeze_display", f"{sq_factor:.2f}x")),
                "desqueezedAspectRatio": str(gyroflow_anamorphic.get("desqueezed_aspect_ratio", "1.78:1")),
                "irisFstop": str(shotmark_and_iris.get("iris_display", "F2.8")) if shotmark_and_iris else "F2.8",
            },
        )

    acq = ET.SubElement(root, _q("AcquisitionRecord"))

    cam_grp = ET.SubElement(acq, _q("Group"), {"name": "CameraUnitMetadataSet"})
    ET.SubElement(cam_grp, _q("Item"), {"name": "CaptureGammaEquation", "value": gamma_eq})
    ET.SubElement(cam_grp, _q("Item"), {"name": "CaptureColorPrimaries", "value": primaries})
    ET.SubElement(cam_grp, _q("Item"), {"name": "ExposureIndexOfPhotoMeter", "value": str(ei_index)})
    ET.SubElement(cam_grp, _q("Item"), {"name": "BaseLook", "value": base_look})
    ET.SubElement(
        cam_grp,
        _q("Item"),
        {"name": "WhiteBalance", "value": f"{color_and_media['wb_mode']}:{color_and_media['kelvin']}K"},
    )
    ET.SubElement(cam_grp, _q("Item"), {"name": "WhiteBalanceColorTemperature", "value": str(color_and_media["kelvin"])})
    ET.SubElement(cam_grp, _q("Item"), {"name": "WhiteBalanceTint", "value": f"{int(color_and_media['tint_gm']):+d}"})
    ET.SubElement(cam_grp, _q("Item"), {"name": "ShocklessWhiteBalance", "value": str(color_and_media["shockless_wb"])})
    ET.SubElement(cam_grp, _q("Item"), {"name": "ShutterMode", "value": str(cine_exposure.get("shutter_mode", "angle"))})
    ET.SubElement(cam_grp, _q("Item"), {"name": "ShutterDisplay", "value": str(cine_exposure.get("shutter_display", "180.0°"))})
    ET.SubElement(
        cam_grp,
        _q("Item"),
        {
            "name": "SlowAndQuickMotion",
            "value": f"{'on' if cine_exposure.get('sq_enabled') else 'off'}:{base_fps:.2f}->{cine_exposure.get('sq_fps', 24)}fps",
        },
    )
    ET.SubElement(cam_grp, _q("Item"), {"name": "DualSlotMode", "value": str(color_and_media["dual_slot_mode"])})
    ET.SubElement(
        cam_grp,
        _q("Item"),
        {
            "name": "ProxyRecording",
            "value": f"{color_and_media['proxy_mode']}:effective={str(bool(color_and_media['proxy_effective_active'])).lower()}",
        },
    )
    if shotmark_and_iris:
        ET.SubElement(cam_grp, _q("Item"), {"name": "IrisFstop", "value": str(shotmark_and_iris.get("iris_display", "F2.8"))})
        ET.SubElement(cam_grp, _q("Item"), {"name": "AutoIrisMeteringMode", "value": str(shotmark_and_iris.get("metering_mode", "multi"))})
        ET.SubElement(cam_grp, _q("Item"), {"name": "Ch34SafetyPadDb", "value": str(shotmark_and_iris.get("ch34_safety_pad_db", 0))})

    mon_grp = ET.SubElement(acq, _q("Group"), {"name": "MonitoringDescriptions"})
    ET.SubElement(mon_grp, _q("Item"), {"name": "MonitoringBaseCurve", "value": gamma_eq})
    ET.SubElement(mon_grp, _q("Item"), {"name": "MonitoringDescription", "value": monitoring_lut_cube})
    ET.SubElement(mon_grp, _q("Item"), {"name": "MonitoringLutName", "value": monitoring_lut_name})
    ET.SubElement(mon_grp, _q("Item"), {"name": "MonitoringLutTitle", "value": monitoring_lut_title})
    ET.SubElement(mon_grp, _q("Item"), {"name": "MonitoringLutSha256", "value": monitoring_lut_sha})
    ET.SubElement(mon_grp, _q("Item"), {"name": "MonitoringLutResampled33Sha256", "value": monitoring_lut_res33_sha})

    media_grp = ET.SubElement(acq, _q("Group"), {"name": "ClipMediaIdentity"})
    ET.SubElement(media_grp, _q("Item"), {"name": "CamID", "value": str(color_and_media["cam_id"])})
    ET.SubElement(media_grp, _q("Item"), {"name": "ReelNumber", "value": f"{int(color_and_media['reel_num']):03d}"})
    ET.SubElement(media_grp, _q("Item"), {"name": "CameraPosition", "value": str(color_and_media["cam_pos"])})
    ET.SubElement(media_grp, _q("Item"), {"name": "ClipSequence", "value": f"{int(color_and_media['clip_seq']):03d}"})
    ET.SubElement(media_grp, _q("Item"), {"name": "MainClipName", "value": str(color_and_media["main_clip_name"])})
    ET.SubElement(media_grp, _q("Item"), {"name": "ProxyClipName", "value": str(color_and_media["proxy_clip_name"])})
    ET.SubElement(media_grp, _q("Item"), {"name": "SidecarFileName", "value": str(color_and_media["sidecar_xml_name"])})
    if shotmark_and_iris:
        ET.SubElement(
            media_grp,
            _q("Item"),
            {"name": "Smpte12mUserBits", "value": str(shotmark_and_iris.get("user_bits_effective", "A0:01:00:01"))},
        )

    if gyroflow_anamorphic:
        gyro_grp = ET.SubElement(acq, _q("Group"), {"name": "AnamorphicGyroflowRtmd"})
        ET.SubElement(gyro_grp, _q("Item"), {"name": "AnamorphicSqueezeFactor", "value": f"{float(gyroflow_anamorphic['squeeze_factor']):.2f}"})
        ET.SubElement(gyro_grp, _q("Item"), {"name": "IbisRequestedMode", "value": str(gyroflow_anamorphic["ibis_mode"])})
        ET.SubElement(gyro_grp, _q("Item"), {"name": "IbisEffectiveMode", "value": str(gyroflow_anamorphic["effective_ibis_mode"])})
        ET.SubElement(gyro_grp, _q("Item"), {"name": "IbisArbitrated", "value": str(bool(gyroflow_anamorphic["ibis_arbitrated"])).lower()})
        ET.SubElement(gyro_grp, _q("Item"), {"name": "IbisHorizontalYawGain", "value": f"{float(gyroflow_anamorphic['horizontal_yaw_gain']):.4f}"})
        ET.SubElement(gyro_grp, _q("Item"), {"name": "IbisVerticalPitchGain", "value": f"{float(gyroflow_anamorphic['vertical_pitch_gain']):.4f}"})
        ET.SubElement(gyro_grp, _q("Item"), {"name": "IbisCenterLock0x0400", "value": str(bool(gyroflow_anamorphic["center_lock_0x0400"])).lower()})
        ET.SubElement(gyro_grp, _q("Item"), {"name": "ImuSampleRateHz", "value": str(int(gyroflow_anamorphic["imu_rate_hz"]))})
        ET.SubElement(gyro_grp, _q("Item"), {"name": "ImuSamplesPerFrame", "value": f"{float(gyroflow_anamorphic['imu_samples_per_frame']):.1f}"})
        ET.SubElement(gyro_grp, _q("Item"), {"name": "Imx510ReadoutSkewMs", "value": f"{float(gyroflow_anamorphic['rolling_shutter_skew_ms']):.1f}"})
        ET.SubElement(gyro_grp, _q("Item"), {"name": "GyroflowRtmdStatus", "value": str(gyroflow_anamorphic["rtmd_status"])})
        ET.SubElement(gyro_grp, _q("Item"), {"name": "GyroflowRtmdReady", "value": str(bool(gyroflow_anamorphic["gyroflow_ready"])).lower()})
        ET.SubElement(gyro_grp, _q("Item"), {"name": "TouchAfInverseDesqueezeScale", "value": f"{float(gyroflow_anamorphic['touch_af_inverse_desqueeze_scale']):.4f}"})

        aud_grp = ET.SubElement(acq, _q("Group"), {"name": "AudioReferenceAndLimiter"})
        ET.SubElement(aud_grp, _q("Item"), {"name": "ReferenceToneEnabled", "value": str(bool(gyroflow_anamorphic["ref_tone_enabled"])).lower()})
        ET.SubElement(aud_grp, _q("Item"), {"name": "ReferenceToneEffectiveActive", "value": str(bool(gyroflow_anamorphic["ref_tone_effective_active"])).lower()})
        ET.SubElement(aud_grp, _q("Item"), {"name": "ReferenceToneInhibitedByRec", "value": str(bool(gyroflow_anamorphic["ref_tone_inhibited_by_rec"])).lower()})
        ET.SubElement(aud_grp, _q("Item"), {"name": "ReferenceToneFreqHz", "value": str(int(gyroflow_anamorphic["ref_tone_freq_hz"]))})
        ET.SubElement(aud_grp, _q("Item"), {"name": "ReferenceToneLevelDbfs", "value": f"{float(gyroflow_anamorphic['ref_tone_level_dbfs']):.1f}"})
        ET.SubElement(aud_grp, _q("Item"), {"name": "SmpteColorBarsEffective", "value": str(bool(gyroflow_anamorphic["color_bars_effective_active"])).lower()})
        ET.SubElement(aud_grp, _q("Item"), {"name": "PeakLimiterEnabled", "value": str(bool(gyroflow_anamorphic["limiter_enabled"])).lower()})
        ET.SubElement(aud_grp, _q("Item"), {"name": "PeakLimiterCeilingDbfs", "value": f"{float(gyroflow_anamorphic['limiter_ceiling_dbfs']):.1f}"})
        ET.SubElement(aud_grp, _q("Item"), {"name": "PeakLimiterEngaging", "value": str(bool(gyroflow_anamorphic["limiter_engaging"])).lower()})

    if interval_cache_lut_ftp:
        p102_grp = ET.SubElement(acq, _q("Group"), {"name": "PictureCacheIntervalCubeFtps"})
        ET.SubElement(p102_grp, _q("Item"), {"name": "PictureCacheRequestedSec", "value": str(int(interval_cache_lut_ftp["cache_seconds"]))})
        ET.SubElement(p102_grp, _q("Item"), {"name": "PictureCacheEffectiveSec", "value": str(int(interval_cache_lut_ftp["effective_cache_seconds"]))})
        ET.SubElement(p102_grp, _q("Item"), {"name": "PictureCacheDdrMib", "value": f"{float(interval_cache_lut_ftp['allocated_ddr_mib']):.2f}"})
        ET.SubElement(p102_grp, _q("Item"), {"name": "PictureCacheDdrBudgetMib", "value": f"{float(interval_cache_lut_ftp['ddr_budget_mib']):.2f}"})
        ET.SubElement(p102_grp, _q("Item"), {"name": "PictureCacheSuspended", "value": str(bool(interval_cache_lut_ftp["picture_cache_suspended"])).lower()})
        ET.SubElement(p102_grp, _q("Item"), {"name": "PictureCacheSuspensionReason", "value": str(interval_cache_lut_ftp.get("picture_cache_suspension_reason") or "none")})
        ET.SubElement(p102_grp, _q("Item"), {"name": "IntervalRecEnabled", "value": str(bool(interval_cache_lut_ftp["interval_rec_enabled"])).lower()})
        ET.SubElement(p102_grp, _q("Item"), {"name": "IntervalSec", "value": str(int(interval_cache_lut_ftp["interval_sec"]))})
        ET.SubElement(p102_grp, _q("Item"), {"name": "IntervalTargetShots", "value": str(int(interval_cache_lut_ftp["target_shots"]))})
        ET.SubElement(p102_grp, _q("Item"), {"name": "IntervalShotsTaken", "value": str(int(interval_cache_lut_ftp["shots_taken"]))})
        ET.SubElement(p102_grp, _q("Item"), {"name": "IntervalAeTracking", "value": str(interval_cache_lut_ftp["ae_tracking"])})
        ET.SubElement(p102_grp, _q("Item"), {"name": "ElectronicShutterEnforced", "value": str(bool(interval_cache_lut_ftp["electronic_shutter_enforced"])).lower()})
        ET.SubElement(p102_grp, _q("Item"), {"name": "MechanicalCurtainActuations", "value": str(int(interval_cache_lut_ftp["mechanical_curtain_actuations"]))})
        ET.SubElement(p102_grp, _q("Item"), {"name": "UserLutTitle", "value": str(interval_cache_lut_ftp.get("active_user_lut_title") or "none")})
        ET.SubElement(p102_grp, _q("Item"), {"name": "UserLutResampled33Sha256", "value": str(interval_cache_lut_ftp.get("active_user_lut_resampled_33_sha256") or "none")})
        ET.SubElement(p102_grp, _q("Item"), {"name": "UserLutSourceGridSize", "value": str(int(interval_cache_lut_ftp.get("active_user_lut_source_size", 0)))})
        ET.SubElement(p102_grp, _q("Item"), {"name": "UserLutTargetGridSize", "value": str(int(interval_cache_lut_ftp.get("active_user_lut_target_size", 0)))})
        ET.SubElement(p102_grp, _q("Item"), {"name": "UserLutVolatileRamOnly", "value": "true"})
        ET.SubElement(p102_grp, _q("Item"), {"name": "FtpsMode", "value": str(interval_cache_lut_ftp["ftps_mode"])})
        ET.SubElement(p102_grp, _q("Item"), {"name": "FtpsTransport", "value": str(interval_cache_lut_ftp["ftps_transport"])})
        ET.SubElement(p102_grp, _q("Item"), {"name": "FtpsQueuedCount", "value": str(int(interval_cache_lut_ftp["ftps_queued_count"]))})
        ET.SubElement(p102_grp, _q("Item"), {"name": "FtpsCompletedCount", "value": str(int(interval_cache_lut_ftp["ftps_completed_count"]))})
        ET.SubElement(p102_grp, _q("Item"), {"name": "FtpsBlockedTraversalCount", "value": str(int(interval_cache_lut_ftp["ftps_blocked_traversal_count"]))})
        ET.SubElement(p102_grp, _q("Item"), {"name": "P12RfOffEnforced", "value": "true"})
        ET.SubElement(p102_grp, _q("Item"), {"name": "Wf12Calls", "value": str(int(interval_cache_lut_ftp["wf12_00342260_hits"]))})

    if mc_fleet_sdi_c2pa:
        p109_grp = ET.SubElement(acq, _q("Group"), {"name": "McFleetSdiAndC2paProvenance"})
        ET.SubElement(p109_grp, _q("Item"), {"name": "FleetRole", "value": str(mc_fleet_sdi_c2pa["fleet_role"])})
        ET.SubElement(p109_grp, _q("Item"), {"name": "FleetCamerasOnline", "value": str(int(mc_fleet_sdi_c2pa["fleet_cams_online"]))})
        ET.SubElement(p109_grp, _q("Item"), {"name": "FleetTransport", "value": str(mc_fleet_sdi_c2pa["fleet_transport"])})
        ET.SubElement(p109_grp, _q("Item"), {"name": "GangRecTrigger", "value": str(bool(mc_fleet_sdi_c2pa["gang_rec_trigger"])).lower()})
        ET.SubElement(p109_grp, _q("Item"), {"name": "P12RfOffEnforced", "value": "true"})
        ET.SubElement(p109_grp, _q("Item"), {"name": "Wf12Calls", "value": str(int(mc_fleet_sdi_c2pa["wf12_00342260_hits"]))})
        ET.SubElement(p109_grp, _q("Item"), {"name": "HdmiAviInfoFrameHex", "value": str(mc_fleet_sdi_c2pa["avi_infoframe_hex"])})
        ET.SubElement(p109_grp, _q("Item"), {"name": "HdmiAviChecksumValid", "value": str(bool(mc_fleet_sdi_c2pa["avi_checksum_valid"])).lower()})
        ET.SubElement(p109_grp, _q("Item"), {"name": "HdmiAviSignalRangeMode", "value": str(mc_fleet_sdi_c2pa["avi_signal_range_mode"])})
        ET.SubElement(p109_grp, _q("Item"), {"name": "HdmiAviQuantizationRange", "value": str(mc_fleet_sdi_c2pa["avi_quantization_range"])})
        ET.SubElement(p109_grp, _q("Item"), {"name": "HdmiSdiConverterBridge", "value": str(mc_fleet_sdi_c2pa["sdi_bridge_converter"])})
        ET.SubElement(p109_grp, _q("Item"), {"name": "SmpteRp188RecTriggerBit", "value": str(int(mc_fleet_sdi_c2pa["rp188_rec_trigger_bit"]))})
        ET.SubElement(p109_grp, _q("Item"), {"name": "SmpteRp188AtcDidSdid", "value": f"{mc_fleet_sdi_c2pa['rp188_atc_did']}/{mc_fleet_sdi_c2pa['rp188_atc_sdid']}"})
        ET.SubElement(p109_grp, _q("Item"), {"name": "LensMountType", "value": str(mc_fleet_sdi_c2pa["mount_type"])})
        ET.SubElement(p109_grp, _q("Item"), {"name": "ElectronicPinsActive", "value": str(int(mc_fleet_sdi_c2pa["electronic_pins_active"]))})
        ET.SubElement(p109_grp, _q("Item"), {"name": "ShadingIdentityReset", "value": str(bool(mc_fleet_sdi_c2pa["shading_identity_reset"])).lower()})
        ET.SubElement(p109_grp, _q("Item"), {"name": "ShadingCornerGain", "value": f"{float(mc_fleet_sdi_c2pa['vignetting_comp_gain']):.4f}"})
        ET.SubElement(p109_grp, _q("Item"), {"name": "LensWeightKg", "value": f"{float(mc_fleet_sdi_c2pa['lens_kg']):.2f}"})
        ET.SubElement(p109_grp, _q("Item"), {"name": "G31LwsSupportWarning", "value": str(bool(mc_fleet_sdi_c2pa["g31_15mm_lws_warning"])).lower()})
        ET.SubElement(p109_grp, _q("Item"), {"name": "C2paSpecVersion", "value": str(mc_fleet_sdi_c2pa["c2pa_spec_version"])})
        ET.SubElement(p109_grp, _q("Item"), {"name": "C2paVaultStatus", "value": str(mc_fleet_sdi_c2pa["c2pa_vault_status"])})
        ET.SubElement(p109_grp, _q("Item"), {"name": "C2paProvenanceMode", "value": str(mc_fleet_sdi_c2pa["c2pa_provenance_mode"])})
        ET.SubElement(p109_grp, _q("Item"), {"name": "C2paClaimGenerator", "value": str(mc_fleet_sdi_c2pa["c2pa_claim_generator"])})
        ET.SubElement(p109_grp, _q("Item"), {"name": "PrivateKeyReads", "value": str(int(mc_fleet_sdi_c2pa["private_key_reads"]))})
        ET.SubElement(p109_grp, _q("Item"), {"name": "CnflashaWrites", "value": str(int(mc_fleet_sdi_c2pa["cnflasha_writes"]))})
        ET.SubElement(p109_grp, _q("Item"), {"name": "HardwareAttestationClaimed", "value": "false"})

    if hdr_hlg_raw_breathing:
        p116_grp = ET.SubElement(acq, _q("Group"), {"name": "HlgBt2100AssistRawBreathing"})
        ET.SubElement(p116_grp, _q("Item"), {"name": "HlgProfile", "value": str(hdr_hlg_raw_breathing["hlg_profile"])})
        ET.SubElement(p116_grp, _q("Item"), {"name": "HlgColorGamut", "value": str(hdr_hlg_raw_breathing["color_gamut"])})
        ET.SubElement(p116_grp, _q("Item"), {"name": "HlgKneePercent", "value": f"{float(hdr_hlg_raw_breathing['knee_pct']):.1f}"})
        ET.SubElement(p116_grp, _q("Item"), {"name": "HlgPeakLuminanceNits", "value": str(int(hdr_hlg_raw_breathing["peak_nits"]))})
        ET.SubElement(p116_grp, _q("Item"), {"name": "HlgDetailLevel", "value": f"{int(hdr_hlg_raw_breathing['detail_level']):+d}"})
        ET.SubElement(p116_grp, _q("Item"), {"name": "Cta8613HdrInfoFrameHex", "value": str(hdr_hlg_raw_breathing["cta_infoframe_hex"])})
        ET.SubElement(p116_grp, _q("Item"), {"name": "Cta8613Eotf", "value": str(int(hdr_hlg_raw_breathing["cta_eotf"]))})
        ET.SubElement(p116_grp, _q("Item"), {"name": "Cta8613ChecksumValid", "value": str(bool(hdr_hlg_raw_breathing["cta_checksum_valid"])).lower()})
        ET.SubElement(p116_grp, _q("Item"), {"name": "GammaDisplayAssistRequested", "value": str(hdr_hlg_raw_breathing["display_assist_mode"])})
        ET.SubElement(p116_grp, _q("Item"), {"name": "GammaDisplayAssistResolved", "value": str(hdr_hlg_raw_breathing["resolved_assist_mode"])})
        ET.SubElement(p116_grp, _q("Item"), {"name": "CleanHdmiSdiUnassisted", "value": "true"})
        ET.SubElement(p116_grp, _q("Item"), {"name": "XavcInternalUnassisted", "value": "true"})
        ET.SubElement(p116_grp, _q("Item"), {"name": "ExternalRawOutputMode", "value": str(hdr_hlg_raw_breathing["ext_raw_mode"])})
        ET.SubElement(p116_grp, _q("Item"), {"name": "ExternalRawBitPacking", "value": f"{int(hdr_hlg_raw_breathing['raw_bit_depth_in'])}to{int(hdr_hlg_raw_breathing['raw_bit_depth_packed'])}Log"})
        ET.SubElement(p116_grp, _q("Item"), {"name": "ExternalRawBaseIso", "value": str(int(hdr_hlg_raw_breathing["raw_base_iso"]))})
        ET.SubElement(p116_grp, _q("Item"), {"name": "ExternalRawKelvin", "value": str(int(hdr_hlg_raw_breathing["raw_kelvin"]))})
        ET.SubElement(p116_grp, _q("Item"), {"name": "FocusBreathingCompRequested", "value": str(hdr_hlg_raw_breathing["breathing_comp_mode"])})
        ET.SubElement(p116_grp, _q("Item"), {"name": "FocusBreathingCompEffective", "value": str(bool(hdr_hlg_raw_breathing["breathing_effective_active"])).lower()})
        ET.SubElement(p116_grp, _q("Item"), {"name": "FocusBreathingCropFactor", "value": f"{float(hdr_hlg_raw_breathing['breathing_crop_factor']):.2f}x"})
        ET.SubElement(p116_grp, _q("Item"), {"name": "FocusBreathingBypassReason", "value": str(hdr_hlg_raw_breathing["breathing_bypass_reason"])})

    if uvc_srt_crsdk_ptp:
        p123_grp = ET.SubElement(acq, _q("Group"), {"name": "UvcSrtRtmpsAndCrsdkPtpFirewall"})
        ET.SubElement(p123_grp, _q("Item"), {"name": "UvcRequestedMode", "value": str(uvc_srt_crsdk_ptp["uvc_mode"])})
        ET.SubElement(p123_grp, _q("Item"), {"name": "UvcEffectiveMode", "value": str(uvc_srt_crsdk_ptp["effective_uvc_mode"])})
        ET.SubElement(p123_grp, _q("Item"), {"name": "UsbLinkSpeed", "value": str(uvc_srt_crsdk_ptp["usb_link_speed"])})
        ET.SubElement(p123_grp, _q("Item"), {"name": "UvcUsb2StepdownActive", "value": str(bool(uvc_srt_crsdk_ptp["uvc_usb2_stepdown_active"])).lower()})
        ET.SubElement(p123_grp, _q("Item"), {"name": "UacAudioSpec", "value": str(uvc_srt_crsdk_ptp["uac_audio_spec"])})
        ET.SubElement(p123_grp, _q("Item"), {"name": "UvcCleanFeedNoOsd", "value": "true"})
        ET.SubElement(p123_grp, _q("Item"), {"name": "SrtMode", "value": str(uvc_srt_crsdk_ptp["srt_mode"])})
        ET.SubElement(p123_grp, _q("Item"), {"name": "SrtPbKeyLen", "value": str(uvc_srt_crsdk_ptp["srt_pbkeylen"])})
        ET.SubElement(p123_grp, _q("Item"), {"name": "SrtArqLatencyMs", "value": str(int(uvc_srt_crsdk_ptp["srt_latency_ms"]))})
        ET.SubElement(p123_grp, _q("Item"), {"name": "RtmpsMode", "value": str(uvc_srt_crsdk_ptp["rtmps_mode"])})
        ET.SubElement(p123_grp, _q("Item"), {"name": "StreamTransport", "value": str(uvc_srt_crsdk_ptp["stream_transport"])})
        ET.SubElement(p123_grp, _q("Item"), {"name": "P12WlanOff", "value": "true"})
        ET.SubElement(p123_grp, _q("Item"), {"name": "Wf12Calls", "value": "0"})
        ET.SubElement(p123_grp, _q("Item"), {"name": "CrsdkPtpMode", "value": str(uvc_srt_crsdk_ptp["crsdk_ptp_mode"])})
        ET.SubElement(p123_grp, _q("Item"), {"name": "CrsdkUsbVid", "value": str(uvc_srt_crsdk_ptp["crsdk_usb_vid"])})
        ET.SubElement(p123_grp, _q("Item"), {"name": "PtpFlashOpcodesBlocked", "value": "true"})
        ET.SubElement(p123_grp, _q("Item"), {"name": "EmmcMutationBytes", "value": "0"})
        ET.SubElement(p123_grp, _q("Item"), {"name": "BlockedFlashOpcodeCount", "value": str(int(uvc_srt_crsdk_ptp["blocked_flash_opcode_count"]))})
        ET.SubElement(p123_grp, _q("Item"), {"name": "P4NdClearEnforced", "value": "true"})

    prov_grp = ET.SubElement(acq, _q("Group"), {"name": "StageBProvenance"})
    ET.SubElement(prov_grp, _q("Item"), {"name": "BaseISO", "value": str(cine_ei_base)})
    ET.SubElement(prov_grp, _q("Item"), {"name": "ExposureIndexOffsetStops", "value": f"{ei_offset_stops:+.4f}"})
    ET.SubElement(prov_grp, _q("Item"), {"name": "OverlayMode", "value": "FX6_STAGE_B_RAM_SHADOW"})
    ET.SubElement(prov_grp, _q("Item"), {"name": "VolatileRamProvenance", "value": "true"})
    ET.SubElement(prov_grp, _q("Item"), {"name": "PersistentEmmcWritesAuthorized", "value": "false"})
    ET.SubElement(prov_grp, _q("Item"), {"name": "C2PASpoofAttempted", "value": "false"})
    ET.SubElement(prov_grp, _q("Item"), {"name": "RqLicPreserved", "value": "true"})

    if shotmarks_list:
        klv_table = ET.SubElement(root, _q("KlvPacketTable"))
        for mark in shotmarks_list:
            m_type = str(mark.get("type", "ShotMark1"))
            em_name = f"_{m_type}"
            frame_str = str(int(mark.get("frame", 0)))
            tc_str = str(mark.get("tc", "00:00:00:00"))
            lbl_str = str(mark.get("label", "OK" if m_type == "ShotMark1" else "KEEP"))
            pkt = ET.SubElement(
                klv_table,
                _q("KlvPacket"),
                {
                    "key": "060E2B34010101010104020100000000",
                    "frameCount": "1",
                    "status": "spot",
                    "start": frame_str,
                    "length": "1",
                },
            )
            ET.SubElement(
                pkt,
                _q("EssenceMark"),
                {
                    "name": em_name,
                    "start": frame_str,
                    "tc": tc_str,
                    "value": lbl_str,
                },
            )

    ET.indent(root, space="  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode") + "\n"


TOUCH_AF_MODES: tuple[str, ...] = ("off", "touch_focus", "touch_tracking")
TOUCH_X_MIN = 0
TOUCH_X_MAX = 959
TOUCH_Y_MIN = 0
TOUCH_Y_MAX = 539
PDAF_COLS = 33
PDAF_ROWS = 19
PDAF_TOTAL_POINTS = PDAF_COLS * PDAF_ROWS  # 627
FOCUS_MAG_MODES: tuple[str, ...] = ("1.0x", "2.0x", "4.0x")
FOCUS_MAG_FACTORS: dict[str, float] = {"1.0x": 1.0, "2.0x": 2.0, "4.0x": 4.0}
FALSE_COLOR_MODES: tuple[str, ...] = ("off", "slog3_ire", "el_zone")
CIZ_RES_MODES: tuple[str, ...] = ("4K", "FHD")
CIZ_RES_MAX_SCALE: dict[str, float] = {"4K": 1.50, "FHD": 2.00}
CIZ_SCALE_MIN = 1.00
CIZ_SCALE_MAX = 2.00
ZOOM_ROCKER_SPEED_MIN = 1
ZOOM_ROCKER_SPEED_MAX = 8

SLOG3_IRE_LANDMARKS: dict[str, dict[str, Any]] = {
    "black_clip": {
        "ire": 3.5,
        "label": "3.5% Black Clip (黑位裁切)",
        "color": "purple",
        "hex": "#7E22CE",
    },
    "middle_grey": {
        "ire": 41.0,
        "label": "41.0% (18% Middle-Grey / 18%中灰)",
        "color": "green",
        "hex": "#22C55E",
    },
    "skin_plus1ev": {
        "ire": 52.0,
        "label": "52.0% (+1EV Skin / 肤色+1EV)",
        "color": "pink",
        "hex": "#F472B6",
    },
    "sensor_clip": {
        "ire": 94.0,
        "label": "94.0% Sensor Clip (传感器高光裁切)",
        "color": "red",
        "hex": "#EF4444",
    },
}

EL_ZONE_STOPS: tuple[dict[str, Any], ...] = (
    {"ev": "-5EV", "ire": 3.5, "color": "purple", "hex": "#6D28D9"},
    {"ev": "-3EV", "ire": 12.0, "color": "blue", "hex": "#0284C7"},
    {"ev": "-1EV", "ire": 31.0, "color": "cyan", "hex": "#06B6D4"},
    {"ev": "0EV (18% Grey)", "ire": 41.0, "color": "green", "hex": "#16A34A"},
    {"ev": "+1EV (Skin)", "ire": 52.0, "color": "pink", "hex": "#EC4899"},
    {"ev": "+3EV", "ire": 74.0, "color": "yellow", "hex": "#F59E0B"},
    {"ev": "+5EV+ (Clip)", "ire": 94.0, "color": "red", "hex": "#DC2626"},
)

TOUCH_FOCUS_CIZ_DEFAULTS: dict[str, Any] = {
    "touch_af_mode": "off",
    "touch_x": 480,
    "touch_y": 270,
    "focus_mag": "1.0x",
    "false_color_mode": "off",
    "ciz_scale": 1.00,
    "ciz_res_mode": "4K",
    "zoom_rocker_speed": 4,
}

TOUCH_FOCUS_CIZ_SPECS: dict[str, Any] = {
    "touch_af_modes": list(TOUCH_AF_MODES),
    "touch_x_range": [TOUCH_X_MIN, TOUCH_X_MAX],
    "touch_y_range": [TOUCH_Y_MIN, TOUCH_Y_MAX],
    "pdaf_cols": PDAF_COLS,
    "pdaf_rows": PDAF_ROWS,
    "pdaf_total_points": PDAF_TOTAL_POINTS,
    "focus_mag_modes": list(FOCUS_MAG_MODES),
    "clean_hdmi_unmagnified": True,
    "false_color_modes": list(FALSE_COLOR_MODES),
    "slog3_ire_landmarks": dict(SLOG3_IRE_LANDMARKS),
    "el_zone_stops": list(EL_ZONE_STOPS),
    "ciz_res_modes": list(CIZ_RES_MODES),
    "ciz_res_max_scale": dict(CIZ_RES_MAX_SCALE),
    "ciz_scale_range": [CIZ_SCALE_MIN, CIZ_SCALE_MAX],
    "zoom_rocker_speed_range": [ZOOM_ROCKER_SPEED_MIN, ZOOM_ROCKER_SPEED_MAX],
}

_TOUCH_AF_ALIASES: dict[str, str] = {
    "off": "off",
    "none": "off",
    "touch_focus": "touch_focus",
    "focus": "touch_focus",
    "spot": "touch_focus",
    "touch_tracking": "touch_tracking",
    "tracking": "touch_tracking",
    "real-time tracking af": "touch_tracking",
    "realtime_tracking": "touch_tracking",
}

_FOCUS_MAG_ALIASES: dict[str, str] = {
    "1.0x": "1.0x",
    "1x": "1.0x",
    "1.0": "1.0x",
    "1": "1.0x",
    "off": "1.0x",
    "2.0x": "2.0x",
    "2x": "2.0x",
    "2.0": "2.0x",
    "2": "2.0x",
    "4.0x": "4.0x",
    "4x": "4.0x",
    "4.0": "4.0x",
    "4": "4.0x",
}

_FALSE_COLOR_ALIASES: dict[str, str] = {
    "off": "off",
    "none": "off",
    "slog3_ire": "slog3_ire",
    "slog3": "slog3_ire",
    "ire": "slog3_ire",
    "el_zone": "el_zone",
    "el-zone": "el_zone",
    "elzone": "el_zone",
}

_CIZ_RES_ALIASES: dict[str, str] = {
    "4k": "4K",
    "uhd": "4K",
    "qfhd": "4K",
    "dci": "4K",
    "fhd": "FHD",
    "1080p": "FHD",
    "hd": "FHD",
}


def compute_imx510_pdaf_cell(touch_x: int, touch_y: int) -> dict[str, int]:
    """Map 960x540 sensor preview coordinates to exact IMX510 33x19 = 627-pt PDAF cell."""
    cx = max(TOUCH_X_MIN, min(TOUCH_X_MAX, int(touch_x)))
    cy = max(TOUCH_Y_MIN, min(TOUCH_Y_MAX, int(touch_y)))
    col = min(PDAF_COLS - 1, (cx * PDAF_COLS) // (TOUCH_X_MAX + 1))
    row = min(PDAF_ROWS - 1, (cy * PDAF_ROWS) // (TOUCH_Y_MAX + 1))
    idx = row * PDAF_COLS + col
    return {"pdaf_col": col, "pdaf_row": row, "pdaf_index": idx}


def _parse_desqueeze_factor_from_str(desqueeze: str | float | None) -> float:
    if isinstance(desqueeze, (int, float)) and not isinstance(desqueeze, bool):
        val = float(desqueeze)
        return val if val > 1.0 else 1.0
    s = str(desqueeze or "1.0x").strip().lower().rstrip("x")
    try:
        val = float(s)
        if math.isfinite(val) and val >= 1.0:
            return val
    except ValueError:
        pass
    return 1.0


def inverse_desqueeze_touch_x(desqueezed_x: int | float, squeeze_factor: float) -> int:
    """Map an on-screen de-squeezed X coordinate back into [0..959] 16:9 sensor space."""
    sq = max(1.0, float(squeeze_factor))
    return max(TOUCH_X_MIN, min(TOUCH_X_MAX, int(round(float(desqueezed_x) / sq))))


def compute_active_sensor_rect(aspect_marker: str = "Off", desqueeze: str = "1.0x") -> dict[str, Any]:
    """Compute active 960x540 sensor image bounds accounting for aspect-guide mattes and anamorphic desqueeze."""
    x_min, x_max = TOUCH_X_MIN, TOUCH_X_MAX
    y_min, y_max = TOUCH_Y_MIN, TOUCH_Y_MAX

    asp = str(aspect_marker or "Off").strip()
    dsq = str(desqueeze or "1.0x").strip().lower()

    if asp == "2.39:1":
        y_min = max(y_min, 56)
        y_max = min(y_max, 483)
    elif asp == "1.85:1":
        x_min = max(x_min, 11)
        x_max = min(x_max, 948)
    elif asp == "9:16":
        x_min = max(x_min, 341)
        x_max = min(x_max, 618)

    if dsq in ("1.3x", "1.30x", "1.33x"):
        y_min = max(y_min, 68)
        y_max = min(y_max, 471)
    elif dsq in ("1.5x", "1.50x"):
        y_min = max(y_min, 90)
        y_max = min(y_max, 449)
    elif dsq in ("1.8x", "1.80x"):
        y_min = max(y_min, 120)
        y_max = min(y_max, 419)
    elif dsq in ("2.0x", "2.00x"):
        y_min = max(y_min, 135)
        y_max = min(y_max, 404)

    has_letterbox = (x_min > TOUCH_X_MIN) or (x_max < TOUCH_X_MAX) or (y_min > TOUCH_Y_MIN) or (y_max < TOUCH_Y_MAX)
    return {
        "x_min": x_min,
        "x_max": x_max,
        "y_min": y_min,
        "y_max": y_max,
        "has_letterbox": has_letterbox,
    }


def compute_touch_focus_ciz_derived(
    state: dict[str, Any],
    *,
    aspect_marker: str = "Off",
    desqueeze: str = "1.0x",
    squeeze_factor: float | None = None,
    zebra_mode: str = "Off",
    base_look: str = "S-Cinetone",
    wired_io_mode: str = "off",
    sq_enabled: bool = False,
    sq_fps: int = 24,
    letterbox_ignored: bool = False,
) -> dict[str, Any]:
    """Compute Phase 81 PDAF cell, Focus Mag ROI, S-Log3 False Color / Zebra warning, CIZ & Phase 95 inverse desqueeze sync."""
    touch_af_mode = str(state.get("touch_af_mode", "off"))
    touch_x = max(TOUCH_X_MIN, min(TOUCH_X_MAX, int(state.get("touch_x", 480))))
    touch_y = max(TOUCH_Y_MIN, min(TOUCH_Y_MAX, int(state.get("touch_y", 270))))
    focus_mag = str(state.get("focus_mag", "1.0x"))
    false_color_mode = str(state.get("false_color_mode", "off"))
    ciz_res_mode = str(state.get("ciz_res_mode", "4K"))
    ciz_scale = round(max(CIZ_SCALE_MIN, min(CIZ_SCALE_MAX, float(state.get("ciz_scale", 1.00)))), 2)
    zoom_rocker_speed = max(ZOOM_ROCKER_SPEED_MIN, min(ZOOM_ROCKER_SPEED_MAX, int(state.get("zoom_rocker_speed", 4))))

    eff_sq_factor = float(squeeze_factor) if (squeeze_factor is not None and float(squeeze_factor) >= 1.0) else _parse_desqueeze_factor_from_str(desqueeze)
    desqueezed_width = int(round(960.0 * eff_sq_factor))
    desqueezed_touch_x = int(round(float(touch_x) * eff_sq_factor))
    touch_af_inverse_desqueeze_scale = round(1.0 / eff_sq_factor, 4)
    touch_af_desqueeze_synced = bool(eff_sq_factor > 1.0)

    pdaf = compute_imx510_pdaf_cell(touch_x, touch_y)
    active_rect = compute_active_sensor_rect(aspect_marker=aspect_marker, desqueeze=desqueeze)

    mag_factor = FOCUS_MAG_FACTORS.get(focus_mag, 1.0)
    roi_w = max(1, int(round(960.0 / mag_factor)))
    roi_h = max(1, int(round(540.0 / mag_factor)))
    roi_x = max(0, min(960 - roi_w, touch_x - roi_w // 2))
    roi_y = max(0, min(540 - roi_h, touch_y - roi_h // 2))

    slog3_active = str(base_look or "").startswith("S-Log3")
    slog3_zebra100_clip_warning = bool(slog3_active and str(zebra_mode or "Off") == "100%")
    slog3_zebra100_warning_message = (
        "Warning: S-Log3 clips at 94% IRE; Zebra 100% will miss highlight saturation! "
        "(警告：S-Log3 在 94% IRE 即达传感器裁切点，斑马线设为 100% 将漏报高光过曝！)"
        if slog3_zebra100_clip_warning
        else None
    )

    ciz_max_scale = CIZ_RES_MAX_SCALE.get(ciz_res_mode, 1.50)
    excl_reasons: list[str] = []
    if str(wired_io_mode or "off") == "hdmi_raw16":
        excl_reasons.append("hdmi_raw16")
    if bool(sq_enabled) and int(sq_fps) >= 120:
        excl_reasons.append("sq_120fps_plus")

    ciz_clamped_by_exclusion = len(excl_reasons) > 0
    if ciz_clamped_by_exclusion:
        effective_ciz_scale = 1.00
        ciz_clamped_by_res_limit = False
        reason_parts_en: list[str] = []
        reason_parts_zh: list[str] = []
        if "hdmi_raw16" in excl_reasons:
            reason_parts_en.append("HDMI 16-bit Linear RAW (4264x2408) requires 1:1 sensor readout")
            reason_parts_zh.append("HDMI 16-bit RAW 输出需 1:1 传感器全幅读取")
        if "sq_120fps_plus" in excl_reasons:
            reason_parts_en.append(f"S&Q {int(sq_fps)}fps (>=120fps) disables Clear Image Zoom")
            reason_parts_zh.append(f"S&Q {int(sq_fps)}fps (>=120fps) 高帧率模式自动禁用清晰影像缩放")
        ciz_exclusion_reason = f"{'; '.join(reason_parts_en)} ({'；'.join(reason_parts_zh)})"
    else:
        ciz_clamped_by_res_limit = ciz_scale > ciz_max_scale + 1e-9
        effective_ciz_scale = round(min(ciz_scale, ciz_max_scale), 2)
        ciz_exclusion_reason = None

    return {
        "touch_af_mode": touch_af_mode,
        "touch_x": touch_x,
        "touch_y": touch_y,
        "squeeze_factor": eff_sq_factor,
        "desqueezed_width": desqueezed_width,
        "desqueezed_touch_x": desqueezed_touch_x,
        "touch_af_inverse_desqueeze_scale": touch_af_inverse_desqueeze_scale,
        "touch_af_desqueeze_synced": touch_af_desqueeze_synced,
        "pdaf_col": pdaf["pdaf_col"],
        "pdaf_row": pdaf["pdaf_row"],
        "pdaf_index": pdaf["pdaf_index"],
        "pdaf_grid": "33x19 (627-pt)",
        "active_sensor_rect": active_rect,
        "letterbox_ignored": bool(letterbox_ignored),
        "focus_mag": focus_mag,
        "focus_mag_factor": mag_factor,
        "focus_mag_center": {"x": touch_x, "y": touch_y},
        "focus_mag_roi": {"x": roi_x, "y": roi_y, "w": roi_w, "h": roi_h},
        "clean_hdmi_unmagnified": True,
        "false_color_mode": false_color_mode,
        "slog3_ire_landmarks": {k: dict(v) for k, v in SLOG3_IRE_LANDMARKS.items()},
        "el_zone_stops": [dict(s) for s in EL_ZONE_STOPS],
        "slog3_zebra100_clip_warning": slog3_zebra100_clip_warning,
        "slog3_zebra100_warning_message": slog3_zebra100_warning_message,
        "ciz_res_mode": ciz_res_mode,
        "ciz_max_scale": ciz_max_scale,
        "ciz_scale": ciz_scale,
        "effective_ciz_scale": effective_ciz_scale,
        "ciz_clamped_by_res_limit": ciz_clamped_by_res_limit,
        "ciz_clamped_by_exclusion": ciz_clamped_by_exclusion,
        "ciz_exclusion_reasons": excl_reasons,
        "ciz_exclusion_reason": ciz_exclusion_reason,
        "zoom_rocker_speed": zoom_rocker_speed,
    }


def format_touch_focus_ciz_command(state: dict[str, Any]) -> str:
    """Format deterministic Phase 81 TOUCH_CIZ host<->guest protocol string."""
    return (
        f"TOUCH_CIZ af={state['touch_af_mode']}@({state['touch_x']},{state['touch_y']})"
        f"[col={state['pdaf_col']},row={state['pdaf_row']},idx={state['pdaf_index']}] "
        f"mag={state['focus_mag']}(hdmi=1.0x) fc={state['false_color_mode']} "
        f"ciz={state['ciz_scale']:.2f}x(eff={state['effective_ciz_scale']:.2f}x,"
        f"res={state['ciz_res_mode']},spd={state['zoom_rocker_speed']}) "
        f"excl={1 if state['ciz_clamped_by_exclusion'] else 0} "
        f"zeb100_warn={1 if state['slog3_zebra100_clip_warning'] else 0}"
    )


def validate_touch_focus_ciz_patch(
    body: Any,
    current_state: dict[str, Any] | None = None,
    *,
    aspect_marker: str = "Off",
    desqueeze: str = "1.0x",
    squeeze_factor: float | None = None,
) -> tuple[bool, dict[str, Any], dict[str, Any] | None]:
    """Validate and normalize Phase 81 Touch-AF, Focus Mag, False Color & CIZ updates (with Phase 95 inverse desqueeze X)."""
    if not isinstance(body, dict):
        return (
            False,
            {},
            {
                "ok": False,
                "error": "invalid_touch_focus_ciz",
                "message": "touch_focus_ciz payload must be a JSON object",
            },
        )

    cur = dict(TOUCH_FOCUS_CIZ_DEFAULTS)
    if current_state:
        cur.update(current_state)

    eff_sq = float(squeeze_factor) if (squeeze_factor is not None and float(squeeze_factor) >= 1.0) else _parse_desqueeze_factor_from_str(desqueeze)
    max_desq_x = max(TOUCH_X_MAX, int(round(960.0 * eff_sq)) - 1)

    updates: dict[str, Any] = {}
    if body.get("reset") is True:
        updates.update(TOUCH_FOCUS_CIZ_DEFAULTS)
        cur.update(TOUCH_FOCUS_CIZ_DEFAULTS)

    if "touch_af_mode" in body and body["touch_af_mode"] is not None:
        raw_af = body["touch_af_mode"]
        if isinstance(raw_af, bool) or not isinstance(raw_af, str):
            return False, {}, {"ok": False, "error": "invalid_touch_af_mode", "message": f"Invalid touch_af_mode: {raw_af!r}"}
        af_norm = _TOUCH_AF_ALIASES.get(raw_af.strip().lower())
        if af_norm is None:
            return (
                False,
                {},
                {
                    "ok": False,
                    "error": "invalid_touch_af_mode",
                    "message": f"Unsupported touch_af_mode: {raw_af!r}",
                    "allowed": list(TOUCH_AF_MODES),
                },
            )
        updates["touch_af_mode"] = af_norm

    coord_space = str(body.get("coordinate_space") or "sensor").strip().lower()
    if coord_space not in ("sensor", "desqueezed"):
        return (
            False,
            {},
            {
                "ok": False,
                "error": "invalid_coordinate_space",
                "message": f"Unsupported coordinate_space: {body.get('coordinate_space')!r} (expected 'sensor' or 'desqueezed')",
            },
        )

    touch_coord_sent = False
    if "desqueezed_touch_x" in body and body["desqueezed_touch_x"] is not None:
        dtx = _parse_strict_int(body["desqueezed_touch_x"])
        if dtx is None or dtx < TOUCH_X_MIN or dtx > max_desq_x:
            return (
                False,
                {},
                {
                    "ok": False,
                    "error": "invalid_desqueezed_touch_x",
                    "message": f"desqueezed_touch_x must be an integer in [{TOUCH_X_MIN}, {max_desq_x}], got {body['desqueezed_touch_x']!r}",
                },
            )
        updates["touch_x"] = inverse_desqueeze_touch_x(dtx, eff_sq)
        touch_coord_sent = True
    elif "touch_x" in body and body["touch_x"] is not None:
        tx = _parse_strict_int(body["touch_x"])
        x_lim = max_desq_x if coord_space == "desqueezed" else TOUCH_X_MAX
        if tx is None or tx < TOUCH_X_MIN or tx > x_lim:
            return (
                False,
                {},
                {
                    "ok": False,
                    "error": "invalid_touch_x",
                    "message": f"touch_x must be an integer in [{TOUCH_X_MIN}, {x_lim}], got {body['touch_x']!r}",
                },
            )
        updates["touch_x"] = inverse_desqueeze_touch_x(tx, eff_sq) if coord_space == "desqueezed" else tx
        touch_coord_sent = True

    if "touch_y" in body and body["touch_y"] is not None:
        ty = _parse_strict_int(body["touch_y"])
        if ty is None or ty < TOUCH_Y_MIN or ty > TOUCH_Y_MAX:
            return (
                False,
                {},
                {
                    "ok": False,
                    "error": "invalid_touch_y",
                    "message": f"touch_y must be an integer in [{TOUCH_Y_MIN}, {TOUCH_Y_MAX}], got {body['touch_y']!r}",
                },
            )
        updates["touch_y"] = ty
        touch_coord_sent = True

    if "focus_mag" in body and body["focus_mag"] is not None:
        raw_mag = body["focus_mag"]
        if isinstance(raw_mag, bool):
            return False, {}, {"ok": False, "error": "invalid_focus_mag", "message": "focus_mag cannot be bool"}
        if isinstance(raw_mag, (int, float)) and not math.isfinite(float(raw_mag)):
            return False, {}, {"ok": False, "error": "invalid_focus_mag", "message": "focus_mag must be finite"}
        mag_key = str(raw_mag).strip().lower()
        mag_norm = _FOCUS_MAG_ALIASES.get(mag_key)
        if mag_norm is None:
            return (
                False,
                {},
                {
                    "ok": False,
                    "error": "invalid_focus_mag",
                    "message": f"Unsupported focus_mag: {raw_mag!r}",
                    "allowed": list(FOCUS_MAG_MODES),
                },
            )
        updates["focus_mag"] = mag_norm

    if "false_color_mode" in body and body["false_color_mode"] is not None:
        raw_fc = body["false_color_mode"]
        if isinstance(raw_fc, bool) or not isinstance(raw_fc, str):
            return False, {}, {"ok": False, "error": "invalid_false_color_mode", "message": f"Invalid false_color_mode: {raw_fc!r}"}
        fc_norm = _FALSE_COLOR_ALIASES.get(raw_fc.strip().lower())
        if fc_norm is None:
            return (
                False,
                {},
                {
                    "ok": False,
                    "error": "invalid_false_color_mode",
                    "message": f"Unsupported false_color_mode: {raw_fc!r}",
                    "allowed": list(FALSE_COLOR_MODES),
                },
            )
        updates["false_color_mode"] = fc_norm

    if "ciz_res_mode" in body and body["ciz_res_mode"] is not None:
        raw_res = body["ciz_res_mode"]
        if isinstance(raw_res, bool) or not isinstance(raw_res, str):
            return False, {}, {"ok": False, "error": "invalid_ciz_res_mode", "message": f"Invalid ciz_res_mode: {raw_res!r}"}
        res_norm = _CIZ_RES_ALIASES.get(raw_res.strip().lower())
        if res_norm is None:
            return (
                False,
                {},
                {
                    "ok": False,
                    "error": "invalid_ciz_res_mode",
                    "message": f"Unsupported ciz_res_mode: {raw_res!r}",
                    "allowed": list(CIZ_RES_MODES),
                },
            )
        updates["ciz_res_mode"] = res_norm

    if "ciz_scale" in body and body["ciz_scale"] is not None:
        raw_ciz = body["ciz_scale"]
        if isinstance(raw_ciz, bool):
            return False, {}, {"ok": False, "error": "invalid_ciz_scale", "message": "ciz_scale cannot be bool"}
        try:
            f_ciz = float(raw_ciz)
        except (TypeError, ValueError):
            return False, {}, {"ok": False, "error": "invalid_ciz_scale", "message": f"Invalid ciz_scale: {raw_ciz!r}"}
        if not math.isfinite(f_ciz) or f_ciz < CIZ_SCALE_MIN - 1e-9 or f_ciz > CIZ_SCALE_MAX + 1e-9:
            return (
                False,
                {},
                {
                    "ok": False,
                    "error": "invalid_ciz_scale",
                    "message": f"ciz_scale must be in [{CIZ_SCALE_MIN:.2f}, {CIZ_SCALE_MAX:.2f}], got {raw_ciz!r}",
                },
            )
        updates["ciz_scale"] = round(max(CIZ_SCALE_MIN, min(CIZ_SCALE_MAX, f_ciz)), 2)

    if "zoom_rocker_speed" in body and body["zoom_rocker_speed"] is not None:
        spd = _parse_strict_int(body["zoom_rocker_speed"])
        if spd is None or spd < ZOOM_ROCKER_SPEED_MIN or spd > ZOOM_ROCKER_SPEED_MAX:
            return (
                False,
                {},
                {
                    "ok": False,
                    "error": "invalid_zoom_rocker_speed",
                    "message": f"zoom_rocker_speed must be an integer in [{ZOOM_ROCKER_SPEED_MIN}, {ZOOM_ROCKER_SPEED_MAX}], got {body['zoom_rocker_speed']!r}",
                },
            )
        updates["zoom_rocker_speed"] = spd

    # Letterbox / Anamorphic matte bar awareness: ignore clicks outside active sensor area
    letterbox_ignored = False
    if touch_coord_sent and body.get("reset") is not True:
        cand_x = int(updates.get("touch_x", cur.get("touch_x", 480)))
        cand_y = int(updates.get("touch_y", cur.get("touch_y", 270)))
        eff_dsq_label = f"{eff_sq:.2f}x" if squeeze_factor is not None else desqueeze
        rect = compute_active_sensor_rect(aspect_marker=aspect_marker, desqueeze=eff_dsq_label)
        if cand_x < rect["x_min"] or cand_x > rect["x_max"] or cand_y < rect["y_min"] or cand_y > rect["y_max"]:
            letterbox_ignored = True
            updates.pop("touch_x", None)
            updates.pop("touch_y", None)
            if updates.get("touch_af_mode") in ("touch_focus", "touch_tracking"):
                updates.pop("touch_af_mode", None)
    updates["_letterbox_ignored"] = letterbox_ignored

    return True, updates, None


SHOTMARK_MAX_PER_CLIP: int = 64
SHOTMARK_TYPES: tuple[str, ...] = ("ShotMark1", "ShotMark2")
SHOTMARK_DEFAULT_LABELS: dict[str, str] = {"ShotMark1": "OK", "ShotMark2": "KEEP"}
IRIS_FSTOP_MIN: float = 1.4
IRIS_FSTOP_MAX: float = 22.0
AE_SHIFT_EV_MIN: float = -2.0
AE_SHIFT_EV_MAX: float = 2.0
METERING_MODES: tuple[str, ...] = ("multi", "center", "spot", "highlight")
SCENE_EV_MIN: float = 0.0
SCENE_EV_MAX: float = 18.0
SCENE_EV_DEFAULT: float = 12.0
CH34_SAFETY_PAD_ALLOWED: tuple[int, ...] = (0, -20)

_EMOUNT_CANON_STOPS: dict[int, float] = {
    8: 1.4,
    16: 2.0,
    24: 2.8,
    32: 4.0,
    40: 5.6,
    48: 8.0,
    56: 11.0,
    64: 16.0,
    72: 22.0,
}
EMOUNT_1_8_STOP_TABLE: tuple[float, ...] = tuple(
    _EMOUNT_CANON_STOPS.get(k, round(2.0 ** (k / 16.0), 2)) for k in range(8, 73)
)

SHOTMARK_IRIS_DEFAULTS: dict[str, Any] = {
    "shotmarks": [],
    "iris_fstop": 2.8,
    "ae_shift_ev": 0.0,
    "metering_mode": "multi",
    "ch34_safety_pad_db": 0,
    "user_bits_hex": "auto_camid_reel",
    "push_auto_iris_active": False,
    "last_scene_ev": SCENE_EV_DEFAULT,
}

SHOTMARK_IRIS_SPECS: dict[str, Any] = {
    "shotmark_types": list(SHOTMARK_TYPES),
    "shotmark_default_labels": dict(SHOTMARK_DEFAULT_LABELS),
    "shotmark_max_per_clip": SHOTMARK_MAX_PER_CLIP,
    "iris_fstop_range": [IRIS_FSTOP_MIN, IRIS_FSTOP_MAX],
    "iris_1_8_stop_table": list(EMOUNT_1_8_STOP_TABLE),
    "ae_shift_ev_range": [AE_SHIFT_EV_MIN, AE_SHIFT_EV_MAX],
    "metering_modes": list(METERING_MODES),
    "scene_ev_range": [SCENE_EV_MIN, SCENE_EV_MAX],
    "scene_ev_default": SCENE_EV_DEFAULT,
    "target_ire": 41.0,
    "highlight_ceiling_ire": 94.0,
    "slog3_highlight_ceiling_ire": 94.0,
    "ch34_safety_pad_allowed": list(CH34_SAFETY_PAD_ALLOWED),
    "audio_bit_depth": 24,
    "audio_channels": 4,
    "user_bits_auto_token": "auto_camid_reel",
}

_SHOTMARK_TYPE_ALIASES: dict[str, str] = {
    "shotmark1": "ShotMark1",
    "_shotmark1": "ShotMark1",
    "m1": "ShotMark1",
    "1": "ShotMark1",
    "ok": "ShotMark1",
    "shotmark2": "ShotMark2",
    "_shotmark2": "ShotMark2",
    "m2": "ShotMark2",
    "2": "ShotMark2",
    "keep": "ShotMark2",
}

_METERING_MODE_ALIASES: dict[str, str] = {
    "multi": "multi",
    "multi-segment": "multi",
    "center": "center",
    "center-weighted": "center",
    "spot": "spot",
    "highlight": "highlight",
    "highlight-weighted": "highlight",
    "hi-light": "highlight",
}

_SHOTMARK_ACTIONS: tuple[str, ...] = (
    "add_shotmark1",
    "add_shotmark2",
    "clear_shotmarks",
    "push_auto_iris",
)


def format_smpte_tc_from_frames(frame: int, base_fps: float = 23.98) -> str:
    """Format non-negative frame index as deterministic SMPTE HH:MM:SS:FF."""
    f_rate = 25 if float(base_fps) in (25.0, 50.0) else 24
    tot = max(0, int(frame))
    ff = tot % f_rate
    tot_s = tot // f_rate
    ss = tot_s % 60
    mm = (tot_s // 60) % 60
    hh = (tot_s // 3600) % 24
    return f"{hh:02d}:{mm:02d}:{ss:02d}:{ff:02d}"


def format_auto_user_bits(cam_id: str = "A", reel_num: int = 1, clip_seq: int = 1) -> str:
    """Auto-format SMPTE 12M User-Bits (e.g. A0:01:00:01) from Phase 73 cam_id, reel_num & clip_seq."""
    cid = str(cam_id or "A").strip().upper()[:1] or "A"
    cam_nib = cid if cid in "ABCDEF" else f"{(ord(cid) - ord('A')) % 16:X}"
    reel = max(1, min(999, int(reel_num)))
    cseq = max(1, min(999, int(clip_seq)))
    b0 = f"{cam_nib}{(reel // 100) % 10}"
    b1 = f"{reel % 100:02d}"
    b2 = f"{(cseq // 100) % 100:02d}"
    b3 = f"{cseq % 100:02d}"
    return f"{b0}:{b1}:{b2}:{b3}"


def parse_user_bits_hex(raw: Any) -> str | None:
    """Validate and normalize SMPTE 12M User-Bits ('auto_camid_reel' or 'AA:BB:CC:DD')."""
    if isinstance(raw, bool) or not isinstance(raw, str):
        return None
    s = raw.strip()
    if s.lower() == "auto_camid_reel":
        return "auto_camid_reel"
    cleaned = s.replace(":", "").replace("-", "").replace(" ", "").upper()
    if len(cleaned) != 8 or any(ch not in "0123456789ABCDEF" for ch in cleaned):
        return None
    return f"{cleaned[0:2]}:{cleaned[2:4]}:{cleaned[4:6]}:{cleaned[6:8]}"


def user_bits_to_uint32(ub_str: str) -> int:
    """Convert normalized 'AA:BB:CC:DD' SMPTE 12M User-Bits string to uint32."""
    cleaned = str(ub_str or "A0:01:00:01").replace(":", "").strip().upper()
    if len(cleaned) != 8 or any(ch not in "0123456789ABCDEF" for ch in cleaned):
        return 0xA0010001
    return int(cleaned, 16)


def slog3_reflectance_to_ire(reflectance: float) -> float:
    """Convert scene linear reflectance R (18% middle grey = 0.18) to Sony S-Log3 IRE (0..109%)."""
    r = max(0.0, float(reflectance))
    if r >= 0.01125:
        code10 = 420.0 + math.log10((r + 0.01) / 0.19) * 261.5
    else:
        code10 = 95.0 + (r * (171.2102946929 - 95.0)) / 0.01125
    ire = 41.0 + (code10 - 420.0) / 8.80
    return round(max(0.0, min(109.0, ire)), 2)


def _nearest_1_8_stop_index(iris_fstop: float) -> int:
    """Return 0..64 index in EMOUNT_1_8_STOP_TABLE closest to iris_fstop."""
    val = max(IRIS_FSTOP_MIN, min(IRIS_FSTOP_MAX, float(iris_fstop)))
    best_idx = 0
    best_diff = abs(EMOUNT_1_8_STOP_TABLE[0] - val)
    for idx, cand in enumerate(EMOUNT_1_8_STOP_TABLE):
        d = abs(cand - val)
        if d < best_diff:
            best_diff = d
            best_idx = idx
    return best_idx


def _format_iris_display(iris_fstop: float) -> str:
    val = round(float(iris_fstop), 2)
    if abs(val * 10.0 - round(val * 10.0)) < 1e-6:
        return f"F{val:.1f}"
    return f"F{val:.2f}"


def _effective_shutter_seconds(
    *,
    shutter_mode: str = "angle",
    shutter_angle_deg: float = 180.0,
    shutter_speed_denom: int = 48,
    ecs_freq_hz: float = 60.0,
    effective_fps: float = 23.98,
) -> float:
    if shutter_mode == "speed":
        return 1.0 / max(1.0, float(shutter_speed_denom))
    if shutter_mode == "ecs":
        return 1.0 / max(1.0, float(ecs_freq_hz))
    fps = max(1.0, float(effective_fps))
    ang = max(1.0, float(shutter_angle_deg))
    return (ang / 360.0) / fps


def compute_push_auto_iris(
    scene_ev: float,
    *,
    ei_index: int = 800,
    shutter_mode: str = "angle",
    shutter_angle_deg: float = 180.0,
    shutter_speed_denom: int = 48,
    ecs_freq_hz: float = 60.0,
    effective_fps: float = 23.98,
    ae_shift_ev: float = 0.0,
    metering_mode: str = "multi",
) -> dict[str, Any]:
    """Compute E-Mount 1/8-stop iris_fstop landing 18% grey at 41.0% IRE (or protecting <94% IRE highlights)."""
    t_sec = _effective_shutter_seconds(
        shutter_mode=shutter_mode,
        shutter_angle_deg=shutter_angle_deg,
        shutter_speed_denom=shutter_speed_denom,
        ecs_freq_hz=ecs_freq_hz,
        effective_fps=effective_fps,
    )
    tv = math.log2(1.0 / max(1e-6, t_sec))
    sv = math.log2(max(100.0, float(ei_index)) / 800.0)
    highlight_bias_ev = 1.0 if metering_mode == "highlight" else 0.0
    desired_av = float(scene_ev) + sv - tv - float(ae_shift_ev) + highlight_bias_ev

    raw_k = int(round(desired_av * 8.0))
    clamped_k = max(8, min(72, raw_k))
    iris_clamped = (raw_k < 8) or (raw_k > 72)
    iris_fstop = EMOUNT_1_8_STOP_TABLE[clamped_k - 8]
    actual_av = clamped_k / 8.0

    ev_delta = (float(scene_ev) + sv - tv) - actual_av
    grey_ire = slog3_reflectance_to_ire(0.18 * (2.0 ** ev_delta))
    hl_ire = slog3_reflectance_to_ire(0.18 * (2.0 ** (ev_delta + 6.5)))

    return {
        "iris_fstop": iris_fstop,
        "iris_1_8_stop_index": clamped_k - 8,
        "iris_clamped": iris_clamped,
        "target_ire": 41.0,
        "highlight_ceiling_ire": 94.0,
        "estimated_grey_ire": grey_ire,
        "estimated_highlight_ire": hl_ire,
        "p4_nd_motor_faults": 0,
    }


def compute_shotmark_and_iris_derived(
    state: dict[str, Any],
    *,
    cam_id: str = "A",
    reel_num: int = 1,
    clip_seq: int = 1,
    ei_index: int = 800,
    shutter_mode: str = "angle",
    shutter_angle_deg: float = 180.0,
    shutter_speed_denom: int = 48,
    ecs_freq_hz: float = 60.0,
    effective_fps: float = 23.98,
    audio_ch_db: Sequence[int] = (-12, -12, -18, -18),
) -> dict[str, Any]:
    """Compute derived Phase 88 ShotMark1/2, Push Auto Iris, 24-bit Safety Audio & SMPTE 12M User-Bits state."""
    marks = [dict(m) for m in state.get("shotmarks", [])][:SHOTMARK_MAX_PER_CLIP]
    sm1_count = sum(1 for m in marks if m.get("type") == "ShotMark1")
    sm2_count = sum(1 for m in marks if m.get("type") == "ShotMark2")
    latest = dict(marks[-1]) if marks else None

    iris_fstop = round(max(IRIS_FSTOP_MIN, min(IRIS_FSTOP_MAX, float(state.get("iris_fstop", 2.8)))), 2)
    ae_shift_ev = round(max(AE_SHIFT_EV_MIN, min(AE_SHIFT_EV_MAX, float(state.get("ae_shift_ev", 0.0)))), 2)
    metering_mode = str(state.get("metering_mode", "multi"))
    if metering_mode not in METERING_MODES:
        metering_mode = "multi"
    ch34_pad = int(state.get("ch34_safety_pad_db", 0))
    if ch34_pad not in CH34_SAFETY_PAD_ALLOWED:
        ch34_pad = 0
    push_active = bool(state.get("push_auto_iris_active", False))
    last_scene_ev = round(max(SCENE_EV_MIN, min(SCENE_EV_MAX, float(state.get("last_scene_ev", SCENE_EV_DEFAULT)))), 2)

    ub_raw = str(state.get("user_bits_hex", "auto_camid_reel"))
    if ub_raw == "auto_camid_reel":
        ub_mode = "auto_camid_reel"
        ub_eff = format_auto_user_bits(cam_id=cam_id, reel_num=reel_num, clip_seq=clip_seq)
    else:
        ub_mode = "manual"
        parsed_ub = parse_user_bits_hex(ub_raw)
        ub_eff = parsed_ub if (parsed_ub and parsed_ub != "auto_camid_reel") else format_auto_user_bits(
            cam_id=cam_id, reel_num=reel_num, clip_seq=clip_seq
        )

    stop_idx = _nearest_1_8_stop_index(iris_fstop)
    actual_av = (stop_idx + 8) / 8.0
    t_sec = _effective_shutter_seconds(
        shutter_mode=shutter_mode,
        shutter_angle_deg=shutter_angle_deg,
        shutter_speed_denom=shutter_speed_denom,
        ecs_freq_hz=ecs_freq_hz,
        effective_fps=effective_fps,
    )
    tv = math.log2(1.0 / max(1e-6, t_sec))
    sv = math.log2(max(100.0, float(ei_index)) / 800.0)
    ev_delta = (last_scene_ev + sv - tv) - actual_av
    est_grey_ire = slog3_reflectance_to_ire(0.18 * (2.0 ** ev_delta))
    est_hl_ire = slog3_reflectance_to_ire(0.18 * (2.0 ** (ev_delta + 6.5)))

    ch3_base = int(audio_ch_db[2]) if len(audio_ch_db) >= 3 else -18
    ch4_base = int(audio_ch_db[3]) if len(audio_ch_db) >= 4 else -18

    return {
        "shotmarks": marks,
        "shotmark_count": len(marks),
        "shotmark1_count": sm1_count,
        "shotmark2_count": sm2_count,
        "latest_shotmark": latest,
        "shotmark_max_per_clip": SHOTMARK_MAX_PER_CLIP,
        "iris_fstop": iris_fstop,
        "iris_display": _format_iris_display(iris_fstop),
        "iris_1_8_stop_index": stop_idx,
        "ae_shift_ev": ae_shift_ev,
        "metering_mode": metering_mode,
        "push_auto_iris_active": push_active,
        "last_scene_ev": last_scene_ev,
        "target_ire": 41.0,
        "highlight_ceiling_ire": 94.0,
        "estimated_grey_ire": est_grey_ire,
        "estimated_highlight_ire": est_hl_ire,
        "p4_nd_motor_faults": 0,
        "p4_nd_preset": "Clear",
        "ch34_safety_pad_db": ch34_pad,
        "audio_bit_depth": 24,
        "audio_channels": 4,
        "ch3_effective_db": max(-60, ch3_base + ch34_pad),
        "ch4_effective_db": max(-60, ch4_base + ch34_pad),
        "user_bits_hex": ub_raw,
        "user_bits_mode": ub_mode,
        "user_bits_effective": ub_eff,
    }


def format_shotmark_iris_command(state: dict[str, Any]) -> str:
    """Format deterministic Phase 88 SMRK_IRIS host<->guest protocol string."""
    return (
        f"SMRK_IRIS m1={state['shotmark1_count']} m2={state['shotmark2_count']} "
        f"iris={state['iris_display']}({state['metering_mode']},ae={state['ae_shift_ev']:+.2f}EV) "
        f"ire={state['target_ire']:.1f} pad={state['ch34_safety_pad_db']}dB "
        f"ub={state['user_bits_effective']} p4_nd_faults=0"
    )


def _normalize_shotmark_entry(
    raw: Any,
    *,
    base_fps: float = 23.98,
    default_frame: int = 0,
) -> tuple[bool, dict[str, Any] | None, dict[str, Any] | None]:
    if not isinstance(raw, dict):
        return False, None, {"ok": False, "error": "invalid_shotmarks", "message": "Each shotmark entry must be a JSON object"}

    raw_type = raw.get("type")
    if isinstance(raw_type, bool) or not isinstance(raw_type, str):
        return False, None, {"ok": False, "error": "invalid_shotmark_type", "message": f"Invalid shotmark type: {raw_type!r}"}
    m_type = _SHOTMARK_TYPE_ALIASES.get(raw_type.strip().lower())
    if m_type is None:
        return (
            False,
            None,
            {
                "ok": False,
                "error": "invalid_shotmark_type",
                "message": f"Unsupported shotmark type: {raw_type!r}",
                "allowed": list(SHOTMARK_TYPES),
            },
        )

    if "frame" in raw and raw["frame"] is not None:
        frame_val = _parse_strict_int(raw["frame"])
        if frame_val is None or frame_val < 0:
            return (
                False,
                None,
                {"ok": False, "error": "invalid_shotmark_frame", "message": f"frame must be non-negative int, got {raw['frame']!r}"},
            )
    else:
        frame_val = max(0, int(default_frame))

    if "tc" in raw and raw["tc"] is not None:
        raw_tc = raw["tc"]
        if isinstance(raw_tc, bool) or not isinstance(raw_tc, str) or not re.fullmatch(r"\d{2}:\d{2}:\d{2}:\d{2}", raw_tc.strip()):
            return (
                False,
                None,
                {"ok": False, "error": "invalid_shotmark_tc", "message": f"tc must match HH:MM:SS:FF, got {raw_tc!r}"},
            )
        tc_val = raw_tc.strip()
    else:
        tc_val = format_smpte_tc_from_frames(frame_val, base_fps=base_fps)

    default_lbl = SHOTMARK_DEFAULT_LABELS[m_type]
    if "label" in raw and raw["label"] is not None:
        if isinstance(raw["label"], bool) or not isinstance(raw["label"], str):
            return False, None, {"ok": False, "error": "invalid_shotmark_label", "message": "label must be a string"}
        lbl_val = raw["label"].strip()[:32] or default_lbl
    else:
        lbl_val = default_lbl

    return True, {"type": m_type, "frame": frame_val, "tc": tc_val, "label": lbl_val}, None


def _dedup_and_cap_shotmarks(entries: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, int]] = set()
    out: list[dict[str, Any]] = []
    for item in entries:
        key = (str(item["type"]), int(item["frame"]))
        if key in seen:
            continue
        seen.add(key)
        out.append(dict(item))
        if len(out) >= SHOTMARK_MAX_PER_CLIP:
            break
    return out


def validate_shotmark_and_iris_patch(
    body: Any,
    current_state: dict[str, Any] | None = None,
    *,
    rec_tc_frames: int = 0,
    ei_index: int = 800,
    shutter_mode: str = "angle",
    shutter_angle_deg: float = 180.0,
    shutter_speed_denom: int = 48,
    ecs_freq_hz: float = 60.0,
    effective_fps: float = 23.98,
    base_fps: float = 23.98,
) -> tuple[bool, dict[str, Any], dict[str, Any] | None]:
    """Validate and normalize Phase 88 ShotMark1/2, Push Auto Iris, Safety Pad & SMPTE 12M User-Bits updates."""
    if not isinstance(body, dict):
        return (
            False,
            {},
            {
                "ok": False,
                "error": "invalid_shotmark_and_iris",
                "message": "shotmark_and_iris payload must be a JSON object",
            },
        )

    cur = {
        **SHOTMARK_IRIS_DEFAULTS,
        "shotmarks": [],
    }
    if current_state:
        cur.update(current_state)
        cur["shotmarks"] = [dict(m) for m in current_state.get("shotmarks", [])]

    updates: dict[str, Any] = {}
    if body.get("reset") is True:
        updates.update({**SHOTMARK_IRIS_DEFAULTS, "shotmarks": []})
        cur.update({**SHOTMARK_IRIS_DEFAULTS, "shotmarks": []})

    if "iris_fstop" in body and body["iris_fstop"] is not None:
        raw_iris = body["iris_fstop"]
        if isinstance(raw_iris, bool):
            return False, {}, {"ok": False, "error": "invalid_iris_fstop", "message": "iris_fstop cannot be bool"}
        try:
            f_iris = float(raw_iris)
        except (TypeError, ValueError):
            return False, {}, {"ok": False, "error": "invalid_iris_fstop", "message": f"Invalid iris_fstop: {raw_iris!r}"}
        if not math.isfinite(f_iris) or f_iris < IRIS_FSTOP_MIN - 1e-9 or f_iris > IRIS_FSTOP_MAX + 1e-9:
            return (
                False,
                {},
                {
                    "ok": False,
                    "error": "invalid_iris_fstop",
                    "message": f"iris_fstop must be in [{IRIS_FSTOP_MIN}, {IRIS_FSTOP_MAX}], got {raw_iris!r}",
                },
            )
        updates["iris_fstop"] = round(max(IRIS_FSTOP_MIN, min(IRIS_FSTOP_MAX, f_iris)), 2)

    if "ae_shift_ev" in body and body["ae_shift_ev"] is not None:
        raw_ae = body["ae_shift_ev"]
        if isinstance(raw_ae, bool):
            return False, {}, {"ok": False, "error": "invalid_ae_shift_ev", "message": "ae_shift_ev cannot be bool"}
        try:
            f_ae = float(raw_ae)
        except (TypeError, ValueError):
            return False, {}, {"ok": False, "error": "invalid_ae_shift_ev", "message": f"Invalid ae_shift_ev: {raw_ae!r}"}
        if not math.isfinite(f_ae) or f_ae < AE_SHIFT_EV_MIN - 1e-9 or f_ae > AE_SHIFT_EV_MAX + 1e-9:
            return (
                False,
                {},
                {
                    "ok": False,
                    "error": "invalid_ae_shift_ev",
                    "message": f"ae_shift_ev must be in [{AE_SHIFT_EV_MIN}, {AE_SHIFT_EV_MAX}], got {raw_ae!r}",
                },
            )
        updates["ae_shift_ev"] = round(max(AE_SHIFT_EV_MIN, min(AE_SHIFT_EV_MAX, f_ae)), 2)

    if "metering_mode" in body and body["metering_mode"] is not None:
        raw_m = body["metering_mode"]
        if isinstance(raw_m, bool) or not isinstance(raw_m, str):
            return False, {}, {"ok": False, "error": "invalid_metering_mode", "message": f"Invalid metering_mode: {raw_m!r}"}
        m_norm = _METERING_MODE_ALIASES.get(raw_m.strip().lower())
        if m_norm is None:
            return (
                False,
                {},
                {
                    "ok": False,
                    "error": "invalid_metering_mode",
                    "message": f"Unsupported metering_mode: {raw_m!r}",
                    "allowed": list(METERING_MODES),
                },
            )
        updates["metering_mode"] = m_norm

    if "ch34_safety_pad_db" in body and body["ch34_safety_pad_db"] is not None:
        pad_val = _parse_strict_int(body["ch34_safety_pad_db"])
        if pad_val is None or pad_val not in CH34_SAFETY_PAD_ALLOWED:
            return (
                False,
                {},
                {
                    "ok": False,
                    "error": "invalid_ch34_safety_pad_db",
                    "message": f"ch34_safety_pad_db must be 0 or -20, got {body['ch34_safety_pad_db']!r}",
                    "allowed": list(CH34_SAFETY_PAD_ALLOWED),
                },
            )
        updates["ch34_safety_pad_db"] = pad_val

    if "user_bits_hex" in body and body["user_bits_hex"] is not None:
        ub_norm = parse_user_bits_hex(body["user_bits_hex"])
        if ub_norm is None:
            return (
                False,
                {},
                {
                    "ok": False,
                    "error": "invalid_user_bits_hex",
                    "message": f"user_bits_hex must be 'auto_camid_reel' or 'AA:BB:CC:DD', got {body['user_bits_hex']!r}",
                },
            )
        updates["user_bits_hex"] = ub_norm

    if "push_auto_iris_active" in body and body["push_auto_iris_active"] is not None:
        if not isinstance(body["push_auto_iris_active"], bool):
            return False, {}, {"ok": False, "error": "invalid_push_auto_iris_active", "message": "push_auto_iris_active must be bool"}
        updates["push_auto_iris_active"] = body["push_auto_iris_active"]

    if "last_scene_ev" in body and body["last_scene_ev"] is not None:
        raw_sev = body["last_scene_ev"]
        if isinstance(raw_sev, bool):
            return False, {}, {"ok": False, "error": "invalid_scene_ev", "message": "last_scene_ev cannot be bool"}
        try:
            f_sev = float(raw_sev)
        except (TypeError, ValueError):
            return False, {}, {"ok": False, "error": "invalid_scene_ev", "message": f"Invalid last_scene_ev: {raw_sev!r}"}
        if not math.isfinite(f_sev) or f_sev < SCENE_EV_MIN - 1e-9 or f_sev > SCENE_EV_MAX + 1e-9:
            return False, {}, {"ok": False, "error": "invalid_scene_ev", "message": f"scene_ev must be in [0.0, 18.0], got {raw_sev!r}"}
        updates["last_scene_ev"] = round(f_sev, 2)

    marks_working = [dict(m) for m in cur.get("shotmarks", [])]
    marks_dirty = body.get("reset") is True

    if "shotmarks" in body and body["shotmarks"] is not None:
        raw_list = body["shotmarks"]
        if not isinstance(raw_list, list):
            return False, {}, {"ok": False, "error": "invalid_shotmarks", "message": "shotmarks must be a JSON array"}
        parsed_list: list[dict[str, Any]] = []
        for entry in raw_list:
            ok_m, norm_m, err_m = _normalize_shotmark_entry(entry, base_fps=base_fps, default_frame=rec_tc_frames)
            if not ok_m or norm_m is None:
                return False, {}, err_m or {"ok": False, "error": "invalid_shotmarks"}
            parsed_list.append(norm_m)
        marks_working = _dedup_and_cap_shotmarks(parsed_list)
        marks_dirty = True

    if "action" in body and body["action"] is not None:
        raw_act = body["action"]
        if isinstance(raw_act, bool) or not isinstance(raw_act, str):
            return False, {}, {"ok": False, "error": "invalid_action", "message": f"Invalid action: {raw_act!r}"}
        act = raw_act.strip().lower()
        if act not in _SHOTMARK_ACTIONS:
            return (
                False,
                {},
                {
                    "ok": False,
                    "error": "invalid_action",
                    "message": f"Unsupported action: {raw_act!r}",
                    "allowed": list(_SHOTMARK_ACTIONS),
                },
            )
        if act == "clear_shotmarks":
            marks_working = []
            marks_dirty = True
        elif act in ("add_shotmark1", "add_shotmark2"):
            m_type = "ShotMark1" if act == "add_shotmark1" else "ShotMark2"
            add_entry = {
                "type": m_type,
                "frame": body.get("frame", rec_tc_frames),
                "tc": body.get("tc"),
                "label": body.get("label"),
            }
            ok_m, norm_m, err_m = _normalize_shotmark_entry(add_entry, base_fps=base_fps, default_frame=rec_tc_frames)
            if not ok_m or norm_m is None:
                return False, {}, err_m or {"ok": False, "error": "invalid_shotmark"}
            marks_working = _dedup_and_cap_shotmarks([*marks_working, norm_m])
            marks_dirty = True
        elif act == "push_auto_iris":
            if "scene_ev" in body and body["scene_ev"] is not None:
                raw_ev = body["scene_ev"]
                if isinstance(raw_ev, bool):
                    return False, {}, {"ok": False, "error": "invalid_scene_ev", "message": "scene_ev cannot be bool"}
                try:
                    scene_ev = float(raw_ev)
                except (TypeError, ValueError):
                    return False, {}, {"ok": False, "error": "invalid_scene_ev", "message": f"Invalid scene_ev: {raw_ev!r}"}
                if not math.isfinite(scene_ev) or scene_ev < SCENE_EV_MIN - 1e-9 or scene_ev > SCENE_EV_MAX + 1e-9:
                    return (
                        False,
                        {},
                        {
                            "ok": False,
                            "error": "invalid_scene_ev",
                            "message": f"scene_ev must be in [{SCENE_EV_MIN}, {SCENE_EV_MAX}], got {raw_ev!r}",
                        },
                    )
            else:
                scene_ev = SCENE_EV_DEFAULT

            eff_ae = float(updates.get("ae_shift_ev", cur.get("ae_shift_ev", 0.0)))
            eff_meter = str(updates.get("metering_mode", cur.get("metering_mode", "multi")))
            iris_res = compute_push_auto_iris(
                scene_ev,
                ei_index=ei_index,
                shutter_mode=shutter_mode,
                shutter_angle_deg=shutter_angle_deg,
                shutter_speed_denom=shutter_speed_denom,
                ecs_freq_hz=ecs_freq_hz,
                effective_fps=effective_fps,
                ae_shift_ev=eff_ae,
                metering_mode=eff_meter,
            )
            if "iris_fstop" not in updates:
                updates["iris_fstop"] = iris_res["iris_fstop"]
            updates["push_auto_iris_active"] = True
            updates["last_scene_ev"] = round(scene_ev, 2)

    if marks_dirty:
        updates["shotmarks"] = marks_working

    return True, updates, None


FX6_ONLY_CAMSET_KEYS: tuple[str, ...] = (
    "fx6_nd_preset",
    "sdi_12g_out",
    "sdi_out",
    "wifi_ap_enabled",
    "vf_peaking",
    "vf_zebra",
    "vf_markers",
    "timecode_bnc_in",
    "genlock_in",
    "grip_zoom_rocker",
    "nd_auto_mode",
    "multi_interface_shoe_fx6",
)


def detect_fx6_fleet_camset(payload: dict[str, Any]) -> bool:
    """Return True if CAMSET payload originates from A-Cam ILME-FX6 or requests fleet sanitization."""
    if payload.get("sanitize_fx6_fleet") is True:
        return True
    if str(payload.get("source_model", "")).strip().upper() == "ILME-FX6":
        return True
    for k in FX6_ONLY_CAMSET_KEYS:
        if k in payload:
            return True
    ce = payload.get("cine_exposure")
    if isinstance(ce, dict):
        for k in FX6_ONLY_CAMSET_KEYS:
            if k in ce:
                return True
    cp = payload.get("cinema_params")
    if isinstance(cp, dict):
        for k in FX6_ONLY_CAMSET_KEYS:
            if k in cp:
                return True
    return False


def sanitize_fx6_fleet_camset_payload(
    payload: dict[str, Any],
) -> tuple[dict[str, Any], list[str], dict[str, dict[str, Any]]]:
    """Scrub/clamp A-Cam ILME-FX6 hardware-only keys cleanly for B-Cam ILME-FX3."""
    clean = copy.deepcopy(payload)
    sanitized_fields: list[str] = []
    details: dict[str, dict[str, Any]] = {}

    def _record(field: str, orig: Any, clamped: Any) -> None:
        if field not in sanitized_fields:
            sanitized_fields.append(field)
        details[field] = {"original": orig, "clamped_to": clamped}

    # 1. FX6 internal electronic VND -> Clear (P4 hardware absent on FX3)
    for k in ("fx6_nd_preset", "nd_auto_mode", "nd_preset", "nd", "nd_filter", "variable_nd"):
        if k in clean and clean[k] is not None:
            orig = clean.pop(k)
            if str(orig).strip().lower() not in ("", "clear", "clear [fx3 p4 locked]", "off", "0", "false"):
                _record(k, orig, "Clear")
            elif k in ("fx6_nd_preset", "nd_auto_mode"):
                _record(k, orig, "Clear")

    cparams = clean.get("cinema_params")
    if isinstance(cparams, dict):
        for k in ("fx6_nd_preset", "nd_auto_mode", "sdi_12g_out", "sdi_out"):
            if k in cparams:
                orig = cparams.pop(k)
                _record(k, orig, "Clear" if "nd" in k else "CONTAINED_DISABLED")
        if "nd" in cparams and str(cparams["nd"]).strip().lower() not in ("", "clear", "clear [fx3 p4 locked]"):
            _record("cinema_params.nd", cparams["nd"], "Clear [FX3 P4 Locked]")
            cparams["nd"] = "Clear [FX3 P4 Locked]"

    ce = clean.get("cine_exposure")
    if isinstance(ce, dict):
        for k in ("fx6_nd_preset", "nd_auto_mode"):
            if k in ce:
                _record(k, ce.pop(k), "Clear")
        if "nd_preset" in ce and str(ce["nd_preset"]).strip().lower() not in ("", "clear"):
            _record("nd_preset", ce["nd_preset"], "Clear")
            ce["nd_preset"] = "Clear"

    # 2. FX6 12G-SDI out -> CONTAINED_DISABLED (no SDI BNC on FX3)
    for container, prefix in ((clean, ""), (ce, "cine_exposure.") if isinstance(ce, dict) else (None, "")):
        if not isinstance(container, dict):
            continue
        for k in ("sdi_12g_out", "sdi_out"):
            if k in container:
                orig = container.pop(k)
                _record(k if not prefix else k, orig, "CONTAINED_DISABLED")

    # 3. FX6 Wi-Fi AP / RF flags -> P12 BK4 Airplane-Mode locked (wifi_bt_rf_disabled=True)
    for k in ("wifi_ap_enabled", "wifi_enabled", "bt_enabled"):
        if k in clean:
            orig = clean.pop(k)
            if orig is not False:
                _record(k, orig, False)
    if clean.get("wifi_bt_rf_disabled") is False:
        _record("wifi_bt_rf_disabled", False, True)
        clean["wifi_bt_rf_disabled"] = True
    if clean.get("p12_bk4_airplane_mode_locked") is False:
        _record("p12_bk4_airplane_mode_locked", False, True)
        clean["p12_bk4_airplane_mode_locked"] = True
    if isinstance(ce, dict):
        for k in ("wifi_ap_enabled", "wifi_enabled", "bt_enabled"):
            if k in ce:
                orig = ce.pop(k)
                if orig is not False:
                    _record(k, orig, False)
        if ce.get("wifi_bt_rf_disabled") is False:
            _record("wifi_bt_rf_disabled", False, True)
            ce["wifi_bt_rf_disabled"] = True

    # 4. FX6 smart EVF / BNC / handle rocker keys -> safely contained/scrubbed
    for k in ("vf_peaking", "vf_zebra", "vf_markers", "timecode_bnc_in", "genlock_in", "grip_zoom_rocker", "multi_interface_shoe_fx6"):
        if k in clean:
            orig = clean.pop(k)
            _record(k, orig, "CONTAINED_DISABLED")
        if isinstance(ce, dict) and k in ce:
            orig = ce.pop(k)
            _record(k, orig, "CONTAINED_DISABLED")
        if isinstance(cparams, dict) and k in cparams:
            orig = cparams.pop(k)
            _record(k, orig, "CONTAINED_DISABLED")

    return clean, sanitized_fields, details


# ---------------- Phase 95: Anamorphic IBIS Arbitrator, Gyroflow 2000Hz RTMD & 1kHz Ref Tone / Limiter ----------------
ANAMORPHIC_SQUEEZE_FACTORS: tuple[float, ...] = (1.0, 1.3, 1.33, 1.5, 1.8, 2.0)
_SQUEEZE_FACTOR_ALIASES: dict[str, float] = {
    "1": 1.0,
    "1.0": 1.0,
    "1.0x": 1.0,
    "1.00x": 1.0,
    "off": 1.0,
    "spherical": 1.0,
    "1.3": 1.3,
    "1.30": 1.3,
    "1.3x": 1.3,
    "1.30x": 1.3,
    "1.33": 1.33,
    "1.33x": 1.33,
    "1.5": 1.5,
    "1.50": 1.5,
    "1.5x": 1.5,
    "1.50x": 1.5,
    "1.8": 1.8,
    "1.80": 1.8,
    "1.8x": 1.8,
    "1.80x": 1.8,
    "2": 2.0,
    "2.0": 2.0,
    "2.0x": 2.0,
    "2.00x": 2.0,
}

IBIS_ARBITRATOR_MODES: tuple[str, ...] = (
    "Off",
    "Standard",
    "Active",
    "Anamorphic_Asymmetric",
    "Center_Lock_Gyroflow",
)
_IBIS_ARBITRATOR_ALIASES: dict[str, str] = {
    "off": "Off",
    "disabled": "Off",
    "standard": "Standard",
    "std": "Standard",
    "active": "Active",
    "act": "Active",
    "active_5axis": "Active",
    "anamorphic_asymmetric": "Anamorphic_Asymmetric",
    "anamorphic": "Anamorphic_Asymmetric",
    "asymmetric": "Anamorphic_Asymmetric",
    "asym": "Anamorphic_Asymmetric",
    "center_lock_gyroflow": "Center_Lock_Gyroflow",
    "center_lock": "Center_Lock_Gyroflow",
    "center-lock": "Center_Lock_Gyroflow",
    "gyroflow": "Center_Lock_Gyroflow",
    "0x0400": "Center_Lock_Gyroflow",
    "off_center_locked": "Center_Lock_Gyroflow",
}
ANAMORPHIC_FALLBACK_MODES: tuple[str, ...] = (
    "Anamorphic_Asymmetric",
    "Center_Lock_Gyroflow",
)

GYRO_IMU_HZ: int = 2000
IMX510_SKEW_FF_4K_MS: float = 8.7
IMX510_SKEW_4K120_MS: float = 4.3
REF_TONE_FREQ_HZ: int = 1000
REF_TONE_LEVEL_DBFS: float = -20.0
LIMITER_CEILING_DBFS: float = -3.0

GYROFLOW_ANAMORPHIC_DEFAULTS: dict[str, Any] = {
    "squeeze_factor": 1.0,
    "ibis_mode": "Standard",
    "anamorphic_fallback_mode": "Anamorphic_Asymmetric",
    "ref_tone_enabled": False,
    "color_bars_enabled": False,
    "limiter_enabled": False,
}

GYROFLOW_ANAMORPHIC_SPECS: dict[str, Any] = {
    "squeeze_factors": list(ANAMORPHIC_SQUEEZE_FACTORS),
    "ibis_modes": list(IBIS_ARBITRATOR_MODES),
    "anamorphic_fallback_modes": list(ANAMORPHIC_FALLBACK_MODES),
    "imu_rate_hz": GYRO_IMU_HZ,
    "imu_axes": 6,
    "rolling_shutter_skew_ff_4k_ms": IMX510_SKEW_FF_4K_MS,
    "rolling_shutter_skew_4k120_ms": IMX510_SKEW_4K120_MS,
    "ref_tone_freq_hz": REF_TONE_FREQ_HZ,
    "ref_tone_level_dbfs": REF_TONE_LEVEL_DBFS,
    "limiter_ceiling_dbfs": LIMITER_CEILING_DBFS,
    "audio_bit_depth": 24,
    "audio_channels": 4,
    "center_lock_code": "0x0400",
    "mailbox_magic": "0x4759524F",
    "mailbox_slots": "mb[44..47]",
    "supported_langs": ["en", "zh-CN", "zh-TW", "ja"],
}


def normalize_squeeze_factor(val: Any) -> float | None:
    """Strictly normalize supported anamorphic squeeze factors (1.0, 1.3, 1.33, 1.5, 1.8, 2.0)."""
    if isinstance(val, bool) or val is None:
        return None
    if isinstance(val, (int, float)):
        fval = float(val)
        if not math.isfinite(fval):
            return None
        for cand in ANAMORPHIC_SQUEEZE_FACTORS:
            if abs(fval - cand) < 1e-6:
                return cand
        return None
    if isinstance(val, str):
        return _SQUEEZE_FACTOR_ALIASES.get(val.strip().lower())
    return None


def squeeze_factor_to_assist_desqueeze(squeeze_factor: float) -> str:
    """Map Phase 95 squeeze factor to Phase 56/81 ASSIST_TOOLS_SPECS['desqueeze'] choices ('1.0x', '1.33x', '2.0x')."""
    if squeeze_factor <= 1.05:
        return "1.0x"
    if squeeze_factor <= 1.55:
        return "1.33x"
    return "2.0x"


def compute_gyroflow_anamorphic_derived(
    state: dict[str, Any],
    *,
    base_fps: float = 23.98,
    sq_enabled: bool = False,
    sq_fps: int = 24,
    rec_state: str = "STBY",
    touch_x: int = 480,
    touch_y: int = 270,
    audio_ch_db: list[int] | tuple[int, ...] = (-12, -12, -18, -18),
) -> dict[str, Any]:
    """Compute Phase 95 Anamorphic IBIS Arbitrator, Gyroflow 2000Hz RTMD telemetry, & 1kHz -20dBFS Tone / Limiter."""
    sq = normalize_squeeze_factor(state.get("squeeze_factor", 1.0))
    if sq is None:
        sq = 1.0
    req_ibis = str(state.get("ibis_mode", "Standard"))
    if req_ibis not in IBIS_ARBITRATOR_MODES:
        req_ibis = "Standard"
    fallback_mode = str(state.get("anamorphic_fallback_mode", "Anamorphic_Asymmetric"))
    if fallback_mode not in ANAMORPHIC_FALLBACK_MODES:
        fallback_mode = "Anamorphic_Asymmetric"

    ibis_arbitrated = bool(sq > 1.0 and req_ibis == "Active")
    effective_ibis_mode = fallback_mode if ibis_arbitrated else req_ibis
    center_lock_0x0400 = bool(effective_ibis_mode == "Center_Lock_Gyroflow")
    anamorphic_edge_wobble_prevented = bool(sq > 1.0 and effective_ibis_mode != "Active")

    if effective_ibis_mode in ("Off", "Center_Lock_Gyroflow"):
        horizontal_yaw_gain = 0.0
        vertical_pitch_gain = 0.0
    elif effective_ibis_mode == "Anamorphic_Asymmetric":
        horizontal_yaw_gain = round(1.0 / sq, 4)
        vertical_pitch_gain = 1.0
    else:
        horizontal_yaw_gain = 1.0
        vertical_pitch_gain = 1.0

    if ibis_arbitrated:
        if fallback_mode == "Center_Lock_Gyroflow":
            arbitration_reason = (
                f"Spherical Active IBIS clamped to 0x0400 Center-Lock for {sq:.2f}x anamorphic Gyroflow post-stab "
                f"({sq:.2f}x 变形镜头下已将球面 Active 防抖自动仲裁为 0x0400 中心锁定以供 Gyroflow 后期增稳)"
            )
        else:
            arbitration_reason = (
                f"Spherical Active IBIS arbitrated to Anamorphic_Asymmetric (yaw_gain={horizontal_yaw_gain:.4f}) for {sq:.2f}x lens "
                f"({sq:.2f}x 变形镜头下已将 Active 防抖自动仲裁为水平偏航增益={horizontal_yaw_gain:.4f}，消除边缘果冻晃动)"
            )
    else:
        arbitration_reason = None

    eff_fps = float(sq_fps) if bool(sq_enabled) else float(base_fps)
    eff_fps = max(1.0, eff_fps)
    imu_samples_per_frame = round(float(GYRO_IMU_HZ) / eff_fps, 1)
    rolling_shutter_skew_ms = IMX510_SKEW_4K120_MS if eff_fps >= 100.0 else IMX510_SKEW_FF_4K_MS
    rtmd_suspended_by_sq = bool(sq_enabled)
    gyroflow_ready = not rtmd_suspended_by_sq
    if rtmd_suspended_by_sq:
        rtmd_status = "RTMD_SUSPENDED_BY_SQ"
        rtmd_suspension_reason = (
            f"2000Hz Gyro RTMD suspended while S&Q VFR ({int(sq_fps)}fps) is active (Sony FX3/FX6 hardware behavior) "
            f"(S&Q 变速帧率 {int(sq_fps)}fps 激活时 2000Hz 陀螺仪 RTMD 自动暂停记录)"
        )
    elif center_lock_0x0400:
        rtmd_status = "RTMD_CENTER_LOCKED"
        rtmd_suspension_reason = None
    else:
        rtmd_status = "RTMD_READY"
        rtmd_suspension_reason = None

    # Touch-AF X coordinate synchronization with Phase 81
    clamped_tx = max(TOUCH_X_MIN, min(TOUCH_X_MAX, int(touch_x)))
    clamped_ty = max(TOUCH_Y_MIN, min(TOUCH_Y_MAX, int(touch_y)))
    desqueezed_width = int(round(960.0 * sq))
    desqueezed_touch_x = int(round(float(clamped_tx) * sq))
    touch_af_inverse_desqueeze_scale = round(1.0 / sq, 4)
    touch_af_desqueeze_synced = bool(sq > 1.0)

    # Audio 1kHz -20.0 dBFS Reference Tone & -3.0 dBFS Soft-Knee Limiter
    rec_on = str(rec_state or "STBY").upper() == "REC"
    ref_tone_enabled = bool(state.get("ref_tone_enabled", False))
    color_bars_enabled = bool(state.get("color_bars_enabled", False))
    limiter_enabled = bool(state.get("limiter_enabled", False))

    ref_tone_inhibited_by_rec = bool(ref_tone_enabled and rec_on)
    ref_tone_effective_active = bool(ref_tone_enabled and not rec_on)
    color_bars_inhibited_by_rec = bool(color_bars_enabled and rec_on)
    color_bars_effective_active = bool(color_bars_enabled and not rec_on)

    raw_ch = [int(audio_ch_db[i]) if i < len(audio_ch_db) else -12 for i in range(4)]
    effective_ch_db: list[float] = []
    clamped_flags: list[bool] = []
    ch_clamped_mask = 0
    for idx, lvl in enumerate(raw_ch):
        if limiter_enabled and float(lvl) > LIMITER_CEILING_DBFS:
            # Soft-knee limiter compresses above -3.0 dBFS ceiling toward -3.0 dBFS
            effective_ch_db.append(LIMITER_CEILING_DBFS)
            clamped_flags.append(True)
            ch_clamped_mask |= (1 << idx)
        else:
            effective_ch_db.append(float(lvl))
            clamped_flags.append(False)
    limiter_engaging = any(clamped_flags)

    desqueezed_ratio_num = round((16.0 / 9.0) * sq, 2)
    desqueezed_aspect_ratio = f"{desqueezed_ratio_num:.2f}:1"
    squeeze_display = f"{sq:.2f}x" if abs(sq - 1.33) < 1e-4 else f"{sq:.2f}x"

    return {
        "squeeze_factor": sq,
        "squeeze_display": squeeze_display,
        "assist_desqueeze_mapped": squeeze_factor_to_assist_desqueeze(sq),
        "desqueezed_aspect_ratio": desqueezed_aspect_ratio,
        "ibis_mode": req_ibis,
        "anamorphic_fallback_mode": fallback_mode,
        "effective_ibis_mode": effective_ibis_mode,
        "ibis_arbitrated": ibis_arbitrated,
        "arbitration_reason": arbitration_reason,
        "center_lock_0x0400": center_lock_0x0400,
        "anamorphic_edge_wobble_prevented": anamorphic_edge_wobble_prevented,
        "horizontal_yaw_gain": horizontal_yaw_gain,
        "vertical_pitch_gain": vertical_pitch_gain,
        "touch_x": clamped_tx,
        "touch_y": clamped_ty,
        "desqueezed_width": desqueezed_width,
        "desqueezed_touch_x": desqueezed_touch_x,
        "touch_af_inverse_desqueeze_scale": touch_af_inverse_desqueeze_scale,
        "touch_af_desqueeze_synced": touch_af_desqueeze_synced,
        "imu_rate_hz": GYRO_IMU_HZ,
        "effective_fps": round(eff_fps, 2),
        "imu_samples_per_frame": imu_samples_per_frame,
        "rolling_shutter_skew_ms": rolling_shutter_skew_ms,
        "rtmd_status": rtmd_status,
        "rtmd_suspended_by_sq": rtmd_suspended_by_sq,
        "rtmd_suspension_reason": rtmd_suspension_reason,
        "gyroflow_ready": gyroflow_ready,
        "rec_state": "REC" if rec_on else "STBY",
        "ref_tone_enabled": ref_tone_enabled,
        "ref_tone_effective_active": ref_tone_effective_active,
        "ref_tone_inhibited_by_rec": ref_tone_inhibited_by_rec,
        "ref_tone_freq_hz": REF_TONE_FREQ_HZ,
        "ref_tone_level_dbfs": REF_TONE_LEVEL_DBFS,
        "color_bars_enabled": color_bars_enabled,
        "color_bars_effective_active": color_bars_effective_active,
        "color_bars_inhibited_by_rec": color_bars_inhibited_by_rec,
        "limiter_enabled": limiter_enabled,
        "limiter_ceiling_dbfs": LIMITER_CEILING_DBFS,
        "limiter_engaging": limiter_engaging,
        "ch_clamped_mask": ch_clamped_mask,
        "ch_clamped": clamped_flags,
        "raw_ch_db": raw_ch,
        "effective_ch_db": effective_ch_db,
        "audio_bit_depth": 24,
        "audio_channels": 4,
    }


def format_gyroflow_anamorphic_command(state: dict[str, Any]) -> str:
    """Format deterministic Phase 95 GYRO_ANA host<->guest protocol string."""
    return (
        f"GYRO_ANA sq={state['squeeze_factor']:.2f}x ibis={state['ibis_mode']}->{state['effective_ibis_mode']} "
        f"yaw={state['horizontal_yaw_gain']:.2f} ctr={1 if state['center_lock_0x0400'] else 0} "
        f"imu={state['imu_samples_per_frame']:.1f}/f skew={state['rolling_shutter_skew_ms']:.1f}ms "
        f"rtmd={state['rtmd_status']} tone={1 if state['ref_tone_effective_active'] else 0}"
        f"(inhib={1 if state['ref_tone_inhibited_by_rec'] else 0}) "
        f"bars={1 if state['color_bars_effective_active'] else 0} "
        f"lim={1 if state['limiter_enabled'] else 0}(eng={1 if state['limiter_engaging'] else 0})"
    )


def validate_gyroflow_anamorphic_patch(
    body: Any,
    current_state: dict[str, Any] | None = None,
) -> tuple[bool, dict[str, Any], dict[str, Any] | None]:
    """Validate and normalize Phase 95 Anamorphic IBIS, Gyroflow RTMD & Audio Tone/Limiter updates."""
    if not isinstance(body, dict):
        return (
            False,
            {},
            {
                "ok": False,
                "error": "invalid_gyroflow_anamorphic",
                "message": "gyroflow_anamorphic payload must be a JSON object",
            },
        )

    cur = dict(GYROFLOW_ANAMORPHIC_DEFAULTS)
    if current_state:
        cur.update(current_state)

    updates: dict[str, Any] = {}
    if body.get("reset") is True:
        updates.update(GYROFLOW_ANAMORPHIC_DEFAULTS)

    if "squeeze_factor" in body and body["squeeze_factor"] is not None:
        sq = normalize_squeeze_factor(body["squeeze_factor"])
        if sq is None:
            return (
                False,
                {},
                {
                    "ok": False,
                    "error": "invalid_squeeze_factor",
                    "message": f"Unsupported squeeze_factor: {body['squeeze_factor']!r}",
                    "allowed": list(ANAMORPHIC_SQUEEZE_FACTORS),
                },
            )
        updates["squeeze_factor"] = sq

    if "ibis_mode" in body and body["ibis_mode"] is not None:
        raw_ibis = body["ibis_mode"]
        if isinstance(raw_ibis, bool) or not isinstance(raw_ibis, str):
            return False, {}, {"ok": False, "error": "invalid_ibis_mode", "message": f"Invalid ibis_mode: {raw_ibis!r}"}
        ibis_norm = _IBIS_ARBITRATOR_ALIASES.get(raw_ibis.strip().lower())
        if ibis_norm is None:
            return (
                False,
                {},
                {
                    "ok": False,
                    "error": "invalid_ibis_mode",
                    "message": f"Unsupported ibis_mode: {raw_ibis!r}",
                    "allowed": list(IBIS_ARBITRATOR_MODES),
                },
            )
        updates["ibis_mode"] = ibis_norm

    if "anamorphic_fallback_mode" in body and body["anamorphic_fallback_mode"] is not None:
        raw_fb = body["anamorphic_fallback_mode"]
        if isinstance(raw_fb, bool) or not isinstance(raw_fb, str):
            return (
                False,
                {},
                {
                    "ok": False,
                    "error": "invalid_anamorphic_fallback_mode",
                    "message": f"Invalid anamorphic_fallback_mode: {raw_fb!r}",
                },
            )
        fb_norm = _IBIS_ARBITRATOR_ALIASES.get(raw_fb.strip().lower())
        if fb_norm not in ANAMORPHIC_FALLBACK_MODES:
            return (
                False,
                {},
                {
                    "ok": False,
                    "error": "invalid_anamorphic_fallback_mode",
                    "message": f"Unsupported anamorphic_fallback_mode: {raw_fb!r}",
                    "allowed": list(ANAMORPHIC_FALLBACK_MODES),
                },
            )
        updates["anamorphic_fallback_mode"] = fb_norm

    for bool_key in ("ref_tone_enabled", "color_bars_enabled", "limiter_enabled"):
        if bool_key in body and body[bool_key] is not None:
            raw_b = body[bool_key]
            if isinstance(raw_b, bool):
                updates[bool_key] = raw_b
            elif isinstance(raw_b, int) and raw_b in (0, 1):
                updates[bool_key] = bool(raw_b)
            elif isinstance(raw_b, str) and raw_b.strip().lower() in ("true", "1", "on", "yes", "false", "0", "off", "no"):
                updates[bool_key] = raw_b.strip().lower() in ("true", "1", "on", "yes")
            else:
                return (
                    False,
                    {},
                    {
                        "ok": False,
                        "error": f"invalid_{bool_key}",
                        "message": f"{bool_key} must be a boolean, got {raw_b!r}",
                    },
                )

    return True, updates, None


CINEMA_PARAM_SPECS: dict[str, dict[str, Any]] = {
    "fps": {
        "key": "fps",
        "label": "FPS",
        "cell_idx": 0,
        "presets": ["23.98p", "24.00p", "25.00p", "29.97p", "50.00p", "59.94p", "119.88p (S&Q)"],
        "locked": False,
        "contract": "S&Q / Project Frame Rate",
    },
    "ei": {
        "key": "ei",
        "label": "EI / Base ISO",
        "cell_idx": 1,
        "presets": [
            "800 EI (800 Base)",
            "400 EI (800 Base)",
            "1600 EI (800 Base)",
            "12800 EI (12800 Base)",
            "6400 EI (12800 Base)",
            "25600 EI (12800 Base)",
        ],
        "locked": False,
        "contract": "P11 Dual Base ISO 800/12800",
    },
    "shutter": {
        "key": "shutter",
        "label": "Shutter",
        "cell_idx": 2,
        "presets": ["180.0°", "90.0°", "45.0°", "360.0°", "1/48", "1/50", "1/100"],
        "locked": False,
        "contract": "BK4 0x02cf1702 (Angle) / 0x02cf1704 (Speed)",
    },
    "nd": {
        "key": "nd",
        "label": "ND Filter",
        "cell_idx": 3,
        "presets": ["Clear [FX3 P4 Locked]"],
        "locked": True,
        "lock_reason": (
            "Stage-B P4 Hardware Contract: ILME-FX3 sensor body lacks an internal physical electronic "
            "variable ND filter; set_nd_filter_mode_i is hardware-locked to Clear."
        ),
        "contract": "P4 ND=Clear Hardware Lock",
    },
    "lut": {
        "key": "lut",
        "label": "Base Look / 3D LUT",
        "cell_idx": 4,
        "presets": [
            "S-Cinetone",
            "S-Log3.Cine / S-Gamut3.Cine",
            "s709",
            "R709 (800%)",
            "User1 (33³ .cube)",
            "User2 (33³ .cube)",
            "User3 (33³ .cube)",
            "User4 (33³ .cube)",
        ],
        "locked": False,
        "contract": "P1 /dev/nflasha30 + P11 33³ 3D LUT DMA (0x0165/0x0166)",
    },
    "wb": {
        "key": "wb",
        "label": "White Balance",
        "cell_idx": 5,
        "presets": ["5600K", "4300K", "3200K", "ATW", "Mem A", "Mem B"],
        "locked": False,
        "contract": "FX6 White Balance / Preset / ATW",
    },
    "ibis": {
        "key": "ibis",
        "label": "5-Axis IBIS",
        "cell_idx": None,
        "presets": ["5-Axis Center Lock (P11)", "Active Off", "Active Standard"],
        "locked": False,
        "contract": "P11 5-Axis IBIS Center-Lock (RTMD 0xE304)",
    },
    "xlr": {
        "key": "xlr",
        "label": "XLR-H1 Audio",
        "cell_idx": None,
        "presets": ["XLR-H1 Ch1/2 +48V (0x5d90)", "XLR-H1 Line In (0x5d90)", "Internal Stereo Mic"],
        "locked": False,
        "contract": "P11 XLR-H1 Audio Handle 0x5d90 / 0x91db059b Fallback",
    },
}

CINEMA_PARAM_ALIASES: dict[str, str] = {
    "fps": "fps",
    "framerate": "fps",
    "frame_rate": "fps",
    "cell0": "fps",
    "ei": "ei",
    "iso": "ei",
    "base_iso": "ei",
    "gain": "ei",
    "cell1": "ei",
    "shutter": "shutter",
    "shutter_angle": "shutter",
    "shutter_speed": "shutter",
    "cell2": "shutter",
    "nd": "nd",
    "nd_filter": "nd",
    "cell3": "nd",
    "lut": "lut",
    "baselook": "lut",
    "base_look": "lut",
    "3d_lut": "lut",
    "cell4": "lut",
    "wb": "wb",
    "white_balance": "wb",
    "cell5": "wb",
    "ibis": "ibis",
    "steady_shot": "ibis",
    "xlr": "xlr",
    "xlr_h1": "xlr",
    "audio": "xlr",
}

AUDIO_PARAM_KEYS = ("ch1_db", "ch2_db", "ch3_db", "ch4_db", "xlr_phantom_48v", "xlr_handle_attached", "rtmd_0xe304_ibis_lock")


def _clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def _eval_builtin_cube_rgb(preset_id: str, r: float, g: float, b: float) -> tuple[float, float, float]:
    if preset_id == "slog3_bypass":
        return (_clamp01(r), _clamp01(g), _clamp01(b))
    if preset_id == "709_typeA":
        # Warm cinema Rec.709 roll-off: gently lifts warm mids and softens blue highlights
        ro = _clamp01(0.02 + 1.12 * r - 0.14 * r * r + 0.02 * g)
        go = _clamp01(0.01 + 1.04 * g - 0.06 * g * g)
        bo = _clamp01(0.90 * b - 0.04 * b * b + 0.02 * g)
        return (ro, go, bo)
    if preset_id == "teal_orange":
        # Distinct split-tone orange-amber mid/high + teal shadows
        ro = _clamp01(0.14 + 1.15 * r - 0.16 * b + 0.10 * g)
        go = _clamp01(0.06 + 0.94 * g + 0.03 * r - 0.04 * b)
        bo = _clamp01(0.22 + 0.62 * b - 0.24 * r + 0.08 * (1.0 - r))
        return (ro, go, bo)
    if preset_id == "film_2383":
        # Kodak 2383 emerald-cool density curve
        ro = _clamp01(0.03 + 0.72 * r + 0.04 * g - 0.05 * b)
        go = _clamp01(0.08 + 1.16 * g - 0.04 * r + 0.05 * b)
        bo = _clamp01(0.07 + 1.02 * b + 0.04 * g - 0.03 * r)
        return (ro, go, bo)
    raise ValueError(f"Unknown built-in .cube preset: {preset_id!r}")


def generate_builtin_cube_lut(preset_id: str, size: int = 17) -> str:
    """Generate a deterministic, standard R-fastest Adobe .cube 3D LUT string (2^3/17^3/33^3/65^3)."""
    key = str(preset_id or "").strip()
    if key not in BUILTIN_CUBE_PRESETS:
        raise ValueError(f"Unknown built-in .cube preset: {preset_id!r}")
    n = int(size)
    if n not in (2, 17, 33, 65):
        raise ValueError(f"Unsupported .cube size: {size!r}")
    meta = BUILTIN_CUBE_PRESETS[key]
    lines = [
        f'# {meta["description"]}',
        f'TITLE "{meta["title"]}"',
        f"LUT_3D_SIZE {n}",
        "DOMAIN_MIN 0.0 0.0 0.0",
        "DOMAIN_MAX 1.0 1.0 1.0",
    ]
    denom = float(n - 1)
    for bi in range(n):
        b = bi / denom
        for gi in range(n):
            g = gi / denom
            for ri in range(n):
                r = ri / denom
                ro, go, bo = _eval_builtin_cube_rgb(key, r, g, b)
                lines.append(f"{ro:.6f} {go:.6f} {bo:.6f}")
    return "\n".join(lines) + "\n"


def _trilinear_cube_sample(
    triplets: list[tuple[float, float, float]],
    size: int,
    r_in: float,
    g_in: float,
    b_in: float,
) -> tuple[float, float, float]:
    """Sample an R-fastest `.cube` 3D LUT table using exact trilinear interpolation."""
    n = size
    rf = _clamp01(r_in) * (n - 1)
    gf = _clamp01(g_in) * (n - 1)
    bf = _clamp01(b_in) * (n - 1)
    r0 = min(n - 2, int(math.floor(rf)))
    g0 = min(n - 2, int(math.floor(gf)))
    b0 = min(n - 2, int(math.floor(bf)))
    r1 = r0 + 1
    g1 = g0 + 1
    b1 = b0 + 1
    dr = rf - r0
    dg = gf - g0
    db = bf - b0

    def at(ri: int, gi: int, bi: int) -> tuple[float, float, float]:
        return triplets[(bi * n + gi) * n + ri]

    c000 = at(r0, g0, b0)
    c100 = at(r1, g0, b0)
    c010 = at(r0, g1, b0)
    c110 = at(r1, g1, b0)
    c001 = at(r0, g0, b1)
    c101 = at(r1, g0, b1)
    c011 = at(r0, g1, b1)
    c111 = at(r1, g1, b1)

    out: list[float] = []
    for k in range(3):
        c00 = c000[k] * (1.0 - dr) + c100[k] * dr
        c10 = c010[k] * (1.0 - dr) + c110[k] * dr
        c01 = c001[k] * (1.0 - dr) + c101[k] * dr
        c11 = c011[k] * (1.0 - dr) + c111[k] * dr
        c0 = c00 * (1.0 - dg) + c10 * dg
        c1 = c01 * (1.0 - dg) + c11 * dg
        out.append(_clamp01(c0 * (1.0 - db) + c1 * db))
    return (out[0], out[1], out[2])


def _tetrahedral_cube_sample(
    triplets: Sequence[tuple[float, float, float]],
    size: int,
    r_in: float,
    g_in: float,
    b_in: float,
) -> tuple[float, float, float]:
    """Sample an R-fastest `.cube` 3D LUT table using exact 6-tetrahedra Sakamoto interpolation."""
    n = size
    rf = _clamp01(r_in) * (n - 1)
    gf = _clamp01(g_in) * (n - 1)
    bf = _clamp01(b_in) * (n - 1)
    r0 = min(n - 2, int(math.floor(rf)))
    g0 = min(n - 2, int(math.floor(gf)))
    b0 = min(n - 2, int(math.floor(bf)))
    r1 = r0 + 1
    g1 = g0 + 1
    b1 = b0 + 1
    dr = rf - r0
    dg = gf - g0
    db = bf - b0

    n2 = n * n
    b0_off = b0 * n2
    b1_off = b1 * n2
    g0_off = g0 * n
    g1_off = g1 * n

    c000 = triplets[b0_off + g0_off + r0]
    c111 = triplets[b1_off + g1_off + r1]

    if dr >= dg:
        if dg >= db:
            c100 = triplets[b0_off + g0_off + r1]
            c110 = triplets[b0_off + g1_off + r1]
            return (
                _clamp01(c000[0] + dr * (c100[0] - c000[0]) + dg * (c110[0] - c100[0]) + db * (c111[0] - c110[0])),
                _clamp01(c000[1] + dr * (c100[1] - c000[1]) + dg * (c110[1] - c100[1]) + db * (c111[1] - c110[1])),
                _clamp01(c000[2] + dr * (c100[2] - c000[2]) + dg * (c110[2] - c100[2]) + db * (c111[2] - c110[2])),
            )
        if dr >= db:
            c100 = triplets[b0_off + g0_off + r1]
            c101 = triplets[b1_off + g0_off + r1]
            return (
                _clamp01(c000[0] + dr * (c100[0] - c000[0]) + db * (c101[0] - c100[0]) + dg * (c111[0] - c101[0])),
                _clamp01(c000[1] + dr * (c100[1] - c000[1]) + db * (c101[1] - c100[1]) + dg * (c111[1] - c101[1])),
                _clamp01(c000[2] + dr * (c100[2] - c000[2]) + db * (c101[2] - c100[2]) + dg * (c111[2] - c101[2])),
            )
        c001 = triplets[b1_off + g0_off + r0]
        c101 = triplets[b1_off + g0_off + r1]
        return (
            _clamp01(c000[0] + db * (c001[0] - c000[0]) + dr * (c101[0] - c001[0]) + dg * (c111[0] - c101[0])),
            _clamp01(c000[1] + db * (c001[1] - c000[1]) + dr * (c101[1] - c001[1]) + dg * (c111[1] - c101[1])),
            _clamp01(c000[2] + db * (c001[2] - c000[2]) + dr * (c101[2] - c001[2]) + dg * (c111[2] - c101[2])),
        )
    else:
        if dr >= db:
            c010 = triplets[b0_off + g1_off + r0]
            c110 = triplets[b0_off + g1_off + r1]
            return (
                _clamp01(c000[0] + dg * (c010[0] - c000[0]) + dr * (c110[0] - c010[0]) + db * (c111[0] - c110[0])),
                _clamp01(c000[1] + dg * (c010[1] - c000[1]) + dr * (c110[1] - c010[1]) + db * (c111[1] - c110[1])),
                _clamp01(c000[2] + dg * (c010[2] - c000[2]) + dr * (c110[2] - c010[2]) + db * (c111[2] - c110[2])),
            )
        if dg >= db:
            c010 = triplets[b0_off + g1_off + r0]
            c011 = triplets[b1_off + g1_off + r0]
            return (
                _clamp01(c000[0] + dg * (c010[0] - c000[0]) + db * (c011[0] - c010[0]) + dr * (c111[0] - c011[0])),
                _clamp01(c000[1] + dg * (c010[1] - c000[1]) + db * (c011[1] - c010[1]) + dr * (c111[1] - c011[1])),
                _clamp01(c000[2] + dg * (c010[2] - c000[2]) + db * (c011[2] - c010[2]) + dr * (c111[2] - c011[2])),
            )
        c001 = triplets[b1_off + g0_off + r0]
        c011 = triplets[b1_off + g1_off + r0]
        return (
            _clamp01(c000[0] + db * (c001[0] - c000[0]) + dg * (c011[0] - c001[0]) + dr * (c111[0] - c011[0])),
            _clamp01(c000[1] + db * (c001[1] - c000[1]) + dg * (c011[1] - c001[1]) + dr * (c111[1] - c011[1])),
            _clamp01(c000[2] + db * (c001[2] - c000[2]) + dg * (c011[2] - c001[2]) + dr * (c111[2] - c011[2])),
        )


def resample_cube_tetrahedral_33(
    triplets: Sequence[tuple[float, float, float]],
    src_size: int,
    domain_min: Sequence[float] = (0.0, 0.0, 0.0),
    domain_max: Sequence[float] = (1.0, 1.0, 1.0),
) -> tuple[tuple[float, float, float], ...]:
    """Resample any 17^3/33^3/65^3 (or 2^3) R-fastest .cube LUT to 33^3 (35,937) via tetrahedral interpolation in volatile RAM."""
    is_unit_domain = (
        abs(domain_min[0]) < 1e-9
        and abs(domain_min[1]) < 1e-9
        and abs(domain_min[2]) < 1e-9
        and abs(domain_max[0] - 1.0) < 1e-9
        and abs(domain_max[1] - 1.0) < 1e-9
        and abs(domain_max[2] - 1.0) < 1e-9
    )
    if src_size == 33 and is_unit_domain and len(triplets) == 33 ** 3:
        return tuple(triplets)
    if src_size == 65 and is_unit_domain and len(triplets) == 65 ** 3:
        out_fast: list[tuple[float, float, float]] = []
        n2 = 65 * 65
        for bi in range(33):
            b_off = (bi * 2) * n2
            for gi in range(33):
                g_off = b_off + (gi * 2) * 65
                for ri in range(33):
                    out_fast.append(triplets[g_off + ri * 2])
        return tuple(out_fast)

    span_r = domain_max[0] - domain_min[0]
    span_g = domain_max[1] - domain_min[1]
    span_b = domain_max[2] - domain_min[2]
    u_r = [_clamp01((i / 32.0 - domain_min[0]) / span_r) for i in range(33)]
    u_g = [_clamp01((i / 32.0 - domain_min[1]) / span_g) for i in range(33)]
    u_b = [_clamp01((i / 32.0 - domain_min[2]) / span_b) for i in range(33)]
    out: list[tuple[float, float, float]] = []
    for bi in range(33):
        wb = u_b[bi]
        for gi in range(33):
            vg = u_g[gi]
            for ri in range(33):
                out.append(_tetrahedral_cube_sample(triplets, src_size, u_r[ri], vg, wb))
    return tuple(out)


def _is_unsafe_lut_label(raw: str) -> bool:
    if "\x00" in raw:
        return True
    if any(ord(c) < 32 or ord(c) == 127 for c in raw):
        return True
    if ".." in raw or "/" in raw or "\\" in raw:
        return True
    return False


def validate_and_sanitize_cube_lut(
    cube_text: Any,
    *,
    name: str = "",
    allow_mini_grid: bool = False,
    include_33_table: bool = False,
) -> dict[str, Any]:
    """Strictly validate, sanitize, and tetrahedrally resample Adobe `.cube` 3D LUT (17^3/33^3/65^3 -> 33^3) in volatile RAM."""
    if not isinstance(cube_text, str):
        return {"ok": False, "error": "invalid_cube_type", "message": "cube_text must be a UTF-8 string"}
    if not cube_text.strip():
        return {"ok": False, "error": "empty_cube_payload", "message": "Empty .cube payload"}
    if "\x00" in cube_text or any((ord(c) < 32 and c not in "\n\r\t") or ord(c) == 127 for c in cube_text):
        return {"ok": False, "error": "control_characters_forbidden", "message": "Control or NUL bytes in .cube payload"}
    raw_bytes = cube_text.encode("utf-8", errors="strict")
    header_probe = cube_text[:4096].upper()
    has_65_header = bool(re.search(r"(?:^|\n)\s*LUT_3D_SIZE\s+65\b", header_probe))
    max_bytes = (16 * 1024 * 1024) if has_65_header else (2 * 1024 * 1024)
    if len(raw_bytes) > max_bytes:
        return {"ok": False, "error": "cube_payload_too_large", "message": f".cube payload exceeds {max_bytes // (1024 * 1024)} MiB safety limit"}

    req_name = str(name or "").strip()
    if req_name and _is_unsafe_lut_label(req_name):
        return {"ok": False, "error": "unsafe_lut_name", "message": "LUT name contains forbidden path/control characters"}

    lines = cube_text.splitlines()
    max_lines = 290000 if has_65_header else 40000
    if len(lines) > max_lines:
        return {"ok": False, "error": "too_many_lines", "message": f".cube exceeds {max_lines} lines safety limit"}

    allowed_sizes = {17, 33, 65}
    if allow_mini_grid:
        allowed_sizes.add(2)

    lut_size: int | None = None
    domain_min: list[float] | None = None
    domain_max: list[float] | None = None
    title = ""
    triplets: list[tuple[float, float, float]] = []
    clamped_components = 0
    comment_or_blank_lines = 0
    seen_data = False

    for line_no, raw_ln in enumerate(lines, start=1):
        ln = raw_ln.strip()
        if not ln or ln.startswith("#"):
            comment_or_blank_lines += 1
            if comment_or_blank_lines > 40000:
                return {"ok": False, "error": "too_many_lines", "message": ".cube exceeds 40,000 comment/blank lines safety limit"}
            continue
        if "#" in ln:
            ln = ln.split("#", 1)[0].strip()
            if not ln:
                comment_or_blank_lines += 1
                continue

        parts = ln.split()
        head = parts[0].upper()

        if head == "LUT_1D_SIZE":
            return {"ok": False, "error": "unsupported_lut_1d_size", "message": f"Line {line_no}: LUT_1D_SIZE is rejected; 3D LUT required"}
        if head == "TITLE":
            if seen_data:
                return {"ok": False, "error": "header_after_data", "message": f"Line {line_no}: TITLE after LUT data"}
            t_raw = ln[len(parts[0]):].strip()
            if len(t_raw) >= 2 and ((t_raw[0] == '"' and t_raw[-1] == '"') or (t_raw[0] == "'" and t_raw[-1] == "'")):
                t_raw = t_raw[1:-1].strip()
            if _is_unsafe_lut_label(t_raw):
                return {"ok": False, "error": "unsafe_title", "message": f"Line {line_no}: TITLE contains unsafe path/control characters"}
            title = t_raw
            continue
        if head == "LUT_3D_SIZE":
            if seen_data:
                return {"ok": False, "error": "header_after_data", "message": f"Line {line_no}: LUT_3D_SIZE after LUT data"}
            if lut_size is not None:
                return {"ok": False, "error": "duplicate_lut_3d_size", "message": f"Line {line_no}: duplicate LUT_3D_SIZE"}
            if len(parts) != 2:
                return {"ok": False, "error": "invalid_lut_3d_size", "message": f"Line {line_no}: expected 'LUT_3D_SIZE <N>'"}
            try:
                lut_size = int(parts[1])
            except ValueError:
                return {"ok": False, "error": "invalid_lut_3d_size", "message": f"Line {line_no}: non-integer LUT_3D_SIZE"}
            if lut_size not in allowed_sizes:
                return {
                    "ok": False,
                    "error": "unsupported_lut_3d_size",
                    "message": f"LUT_3D_SIZE={lut_size} unsupported (allowed: {sorted(allowed_sizes)})",
                }
            continue
        if head in ("DOMAIN_MIN", "DOMAIN_MAX"):
            if seen_data:
                return {"ok": False, "error": "header_after_data", "message": f"Line {line_no}: {head} after LUT data"}
            if len(parts) != 4:
                return {"ok": False, "error": f"invalid_{head.lower()}", "message": f"Line {line_no}: {head} requires 3 floats"}
            try:
                vec = [float(parts[1]), float(parts[2]), float(parts[3])]
            except ValueError:
                return {"ok": False, "error": f"invalid_{head.lower()}", "message": f"Line {line_no}: non-numeric {head}"}
            if not all(math.isfinite(v) for v in vec):
                return {"ok": False, "error": "non_finite_domain", "message": f"Line {line_no}: NaN/Inf in {head}"}
            if head == "DOMAIN_MIN":
                if domain_min is not None:
                    return {"ok": False, "error": "duplicate_domain_min", "message": f"Line {line_no}: duplicate DOMAIN_MIN"}
                domain_min = vec
            else:
                if domain_max is not None:
                    return {"ok": False, "error": "duplicate_domain_max", "message": f"Line {line_no}: duplicate DOMAIN_MAX"}
                domain_max = vec
            continue

        # Must be an RGB triplet data line
        if len(parts) != 3:
            return {
                "ok": False,
                "error": "invalid_row_or_keyword",
                "message": f"Line {line_no}: expected 3 numeric RGB values, got {len(parts)} tokens ({parts[0]!r})",
            }
        try:
            r_v, g_v, b_v = float(parts[0]), float(parts[1]), float(parts[2])
        except ValueError:
            return {
                "ok": False,
                "error": "invalid_row_or_keyword",
                "message": f"Line {line_no}: non-numeric token {parts[0]!r}",
            }
        if not (math.isfinite(r_v) and math.isfinite(g_v) and math.isfinite(b_v)):
            return {
                "ok": False,
                "error": "nan_or_inf_triplet",
                "message": f"Line {line_no}: NaN/Inf forbidden in 3D LUT triplet",
            }
        seen_data = True
        cr = 0.0 if r_v < 0.0 else (1.0 if r_v > 1.0 else r_v)
        cg = 0.0 if g_v < 0.0 else (1.0 if g_v > 1.0 else g_v)
        cb = 0.0 if b_v < 0.0 else (1.0 if b_v > 1.0 else b_v)
        if cr != r_v:
            clamped_components += 1
        if cg != g_v:
            clamped_components += 1
        if cb != b_v:
            clamped_components += 1
        triplets.append((cr, cg, cb))
        if lut_size is not None and len(triplets) > lut_size ** 3:
            return {
                "ok": False,
                "error": "triplet_count_mismatch",
                "message": f"Too many RGB triplets: exceeds {lut_size}^3 ({lut_size ** 3})",
            }

    if lut_size is None:
        return {"ok": False, "error": "missing_lut_3d_size", "message": "Missing required LUT_3D_SIZE header"}

    dmin = domain_min if domain_min is not None else [0.0, 0.0, 0.0]
    dmax = domain_max if domain_max is not None else [1.0, 1.0, 1.0]
    for c in range(3):
        if not (dmin[c] < dmax[c]):
            return {
                "ok": False,
                "error": "invalid_domain_bounds",
                "message": f"Invalid domain on channel {c}: DOMAIN_MIN={dmin[c]} >= DOMAIN_MAX={dmax[c]}",
            }

    expected = lut_size ** 3
    if len(triplets) != expected:
        return {
            "ok": False,
            "error": "triplet_count_mismatch",
            "message": f"Expected {expected} ({lut_size}^3) RGB triplets, found {len(triplets)}",
        }

    safe_name = (req_name or title or f"Custom {lut_size}^3")[:23]
    safe_name = "".join(ch if 32 <= ord(ch) < 127 else "_" for ch in safe_name).strip() or f"Custom {lut_size}^3"

    src_hasher = hashlib.sha256()
    src_hasher.update(
        (
            f'TITLE "{safe_name}"\n'
            f"LUT_3D_SIZE {lut_size}\n"
            f"DOMAIN_MIN {dmin[0]:.6f} {dmin[1]:.6f} {dmin[2]:.6f}\n"
            f"DOMAIN_MAX {dmax[0]:.6f} {dmax[1]:.6f} {dmax[2]:.6f}\n"
        ).encode("utf-8")
    )
    if lut_size <= 33:
        src_hasher.update(("\n".join(f"{r:.6f} {g:.6f} {b:.6f}" for (r, g, b) in triplets) + "\n").encode("utf-8"))
    else:
        chunk: list[str] = []
        for idx, (r, g, b) in enumerate(triplets, start=1):
            chunk.append(f"{r:.6f} {g:.6f} {b:.6f}")
            if (idx & 4095) == 0:
                src_hasher.update(("\n".join(chunk) + "\n").encode("utf-8"))
                chunk.clear()
        if chunk:
            src_hasher.update(("\n".join(chunk) + "\n").encode("utf-8"))
    sha256 = src_hasher.hexdigest()

    table_33 = resample_cube_tetrahedral_33(triplets, lut_size, dmin, dmax)
    res_hasher = hashlib.sha256()
    res_hasher.update(
        (
            f'TITLE "{safe_name}"\n'
            f"LUT_3D_SIZE 33\n"
            f"DOMAIN_MIN 0.000000 0.000000 0.000000\n"
            f"DOMAIN_MAX 1.000000 1.000000 1.000000\n"
        ).encode("utf-8")
    )
    res_hasher.update(("\n".join(f"{r:.6f} {g:.6f} {b:.6f}" for (r, g, b) in table_33) + "\n").encode("utf-8"))
    resampled_33_sha256 = res_hasher.hexdigest()

    mr, mg, mb = _tetrahedral_cube_sample(table_33, 33, 0.5, 0.5, 0.5)
    sr, sg, sb = _tetrahedral_cube_sample(table_33, 33, 0.15, 0.15, 0.15)
    hr, hg, hb = _tetrahedral_cube_sample(table_33, 33, 0.85, 0.85, 0.85)
    lo_r, lo_g, lo_b = _tetrahedral_cube_sample(table_33, 33, 0.05, 0.05, 0.05)
    hi_r, hi_g, hi_b = _tetrahedral_cube_sample(table_33, 33, 0.95, 0.95, 0.95)
    luma_lo = 0.2126 * lo_r + 0.7152 * lo_g + 0.0722 * lo_b
    luma_hi = 0.2126 * hi_r + 0.7152 * hi_g + 0.0722 * hi_b
    contrast_signature = round(max(0.25, min(2.50, (luma_hi - luma_lo) / 0.90)), 4)

    r8 = max(0, min(255, int(round(mr * 255.0))))
    g8 = max(0, min(255, int(round(mg * 255.0))))
    b8 = max(0, min(255, int(round(mb * 255.0))))

    res: dict[str, Any] = {
        "ok": True,
        "name": safe_name,
        "title": title or safe_name,
        "size": lut_size,
        "source_grid_size": lut_size,
        "target_grid_size": 33,
        "triplets": expected,
        "resampled_33_triplets": 33 ** 3,
        "resampling_method": "tetrahedral",
        "clamped_components": clamped_components,
        "domain_min": dmin,
        "domain_max": dmax,
        "sha256": sha256,
        "resampled_33_sha256": resampled_33_sha256,
        "mid_gray_rgb": [round(mr, 6), round(mg, 6), round(mb, 6)],
        "tint_rgb8": [r8, g8, b8],
        "tint_hex": f"#{r8:02x}{g8:02x}{b8:02x}",
        "shadow_tint_rgb8": [
            max(0, min(255, int(round(sr * 255.0)))),
            max(0, min(255, int(round(sg * 255.0)))),
            max(0, min(255, int(round(sb * 255.0)))),
        ],
        "highlight_tint_rgb8": [
            max(0, min(255, int(round(hr * 255.0)))),
            max(0, min(255, int(round(hg * 255.0)))),
            max(0, min(255, int(round(hb * 255.0)))),
        ],
        "contrast_signature": contrast_signature,
        "volatile_ram_only": True,
        "persistent_emmc_writes_authorized": False,
        "emmc_mutation_bytes": 0,
    }
    if include_33_table:
        res["_table_33"] = table_33
    return res


# ---------------------------------------------------------------------------
# Phase 102 — Picture Cache DDR Ring-Buffer, Interval Rec E-Shutter,
#             .cube 33^3 Tetrahedral LUT & Wired USB-LAN FTPS Queue
# ---------------------------------------------------------------------------

FX3_TOTAL_AP_DRAM_MIB: float = 2048.0
FX3_PICTURE_CACHE_DDR_BUDGET_MIB: float = 384.0
PICTURE_CACHE_ALLOWED_SECONDS: tuple[int, ...] = (0, 2, 4, 8, 16)
PICTURE_CACHE_CODEC_PROFILES: dict[str, dict[str, Any]] = {
    "XAVC_I_4K60": {"codec": "XAVC-I 4K 59.94p", "bitrate_mbps": 600.0, "mib_per_sec": 75.0, "fps": 59.94},
    "XAVC_I_4K24": {"codec": "XAVC-I 4K 23.98p", "bitrate_mbps": 240.0, "mib_per_sec": 30.0, "fps": 23.98},
    "XAVC_L_4K60": {"codec": "XAVC-L 4K 59.94p", "bitrate_mbps": 200.0, "mib_per_sec": 25.0, "fps": 59.94},
    "XAVC_L_4K30": {"codec": "XAVC-L 4K 29.97p", "bitrate_mbps": 100.0, "mib_per_sec": 12.5, "fps": 29.97},
    "XAVC_I_FHD60": {"codec": "XAVC-I FHD 59.94p", "bitrate_mbps": 222.0, "mib_per_sec": 27.75, "fps": 59.94},
    "XAVC_L_FHD60": {"codec": "XAVC-L FHD 59.94p", "bitrate_mbps": 50.0, "mib_per_sec": 6.25, "fps": 59.94},
    "XAVC_HS_4K60": {"codec": "XAVC HS 4K 59.94p", "bitrate_mbps": 200.0, "mib_per_sec": 25.0, "fps": 59.94},
}
INTERVAL_SEC_MIN: int = 1
INTERVAL_SEC_MAX: int = 60
INTERVAL_TARGET_SHOTS_MIN: int = 1
INTERVAL_TARGET_SHOTS_MAX: int = 9999
INTERVAL_AE_TRACKING_MODES: tuple[str, ...] = ("High", "Mid", "Low", "Lock")
_INTERVAL_AE_ALIASES: dict[str, str] = {m.lower(): m for m in INTERVAL_AE_TRACKING_MODES}
INTERVAL_AE_SLEW_ALPHA: dict[str, float] = {"High": 0.65, "Mid": 0.30, "Low": 0.10, "Lock": 0.0}

FTPS_MODES: tuple[str, ...] = ("Off", "Proxy_Only", "Original_And_Proxy")
_FTPS_MODE_ALIASES: dict[str, str] = {
    "off": "Off",
    "0": "Off",
    "none": "Off",
    "proxy_only": "Proxy_Only",
    "proxy": "Proxy_Only",
    "original_and_proxy": "Original_And_Proxy",
    "proxy_and_original": "Original_And_Proxy",
    "both": "Original_And_Proxy",
    "orig_and_proxy": "Original_And_Proxy",
}
ALLOWED_FTPS_WIRED_NICS: tuple[str, ...] = ("CDC_NCM_RTL8153", "CDC_NCM_AX88179")
ALLOWED_FTPS_MEDIA_ROOTS: tuple[str, ...] = (
    "/mnt/sd",
    "/mnt/slot_a",
    "/mnt/slot_b",
    "/mnt/cfexpress_a",
    "/mnt/cfexpress_b",
)
_FORBIDDEN_EMMC_PATH_RE = re.compile(
    r"(?:^|/)(?:p(?:[1-9]|1[0-5])|nflasha\d*|cnflasha\d*|mmcblk0(?:p\d+)?|mtdblock\d*)(?:/|$)",
    re.IGNORECASE,
)
_FORBIDDEN_FTPS_SYS_PREFIXES: tuple[str, ...] = (
    "/etc",
    "/lib",
    "/usr",
    "/bin",
    "/sbin",
    "/boot",
    "/dev",
    "/proc",
    "/sys",
    "/root",
    "/var",
    "/nvram",
)

INTERVAL_CACHE_LUT_FTP_DEFAULTS: dict[str, Any] = {
    "cache_seconds": 0,
    "codec_profile": "auto",
    "interval_rec_enabled": False,
    "interval_sec": 5,
    "target_shots": 120,
    "shots_taken": 0,
    "ae_tracking": "Mid",
    "ftps_mode": "Off",
    "ftps_nic_driver": "CDC_NCM_RTL8153",
    "ftps_tls_version": "FTPES_TLS13",
    "ftps_data_mode": "PASV",
}

INTERVAL_CACHE_LUT_FTP_SPECS: dict[str, Any] = {
    "cache_seconds_choices": list(PICTURE_CACHE_ALLOWED_SECONDS),
    "fx3_total_dram_mib": FX3_TOTAL_AP_DRAM_MIB,
    "ddr_budget_mib": FX3_PICTURE_CACHE_DDR_BUDGET_MIB,
    "cache_ddr_budget_mib": FX3_PICTURE_CACHE_DDR_BUDGET_MIB,
    "codec_profiles": {k: dict(v) for k, v in PICTURE_CACHE_CODEC_PROFILES.items()},
    "interval_sec_range": [INTERVAL_SEC_MIN, INTERVAL_SEC_MAX],
    "target_shots_range": [INTERVAL_TARGET_SHOTS_MIN, INTERVAL_TARGET_SHOTS_MAX],
    "ae_tracking_modes": list(INTERVAL_AE_TRACKING_MODES),
    "electronic_shutter_enforced": True,
    "mechanical_curtain_actuations_locked": 0,
    "cube_supported_sizes": [17, 33, 65],
    "cube_target_size": 33,
    "cube_resampling_method": "tetrahedral",
    "ftps_modes": list(FTPS_MODES),
    "ftps_wired_nics": list(ALLOWED_FTPS_WIRED_NICS),
    "ftps_allowed_media_roots": list(ALLOWED_FTPS_MEDIA_ROOTS),
    "p12_rf_off_enforced": True,
    "wf12_00342260_hits_locked": 0,
    "mailbox_magic": "0x49434C46",
    "mailbox_slots": "mb[48..51]",
    "supported_langs": ["en", "zh-CN", "zh-TW", "ja"],
}


def resolve_effective_cache_codec_profile(
    codec_profile: str = "auto",
    *,
    base_fps: float = 23.98,
    rec_fmt_idx: int = 0,
) -> tuple[str, dict[str, Any]]:
    """Resolve active Picture Cache codec/bitrate profile from explicit selection or active rec_fmt/fps."""
    if codec_profile in PICTURE_CACHE_CODEC_PROFILES:
        return codec_profile, PICTURE_CACHE_CODEC_PROFILES[codec_profile]
    idx = int(rec_fmt_idx) % 5
    if idx == 1:
        key = "XAVC_L_4K30"
    elif idx == 2:
        key = "XAVC_I_FHD60"
    elif idx == 3:
        key = "XAVC_L_FHD60"
    elif idx == 4:
        key = "XAVC_HS_4K60"
    else:
        key = "XAVC_I_4K60" if float(base_fps) >= 49.0 else "XAVC_I_4K24"
    return key, PICTURE_CACHE_CODEC_PROFILES[key]


def validate_ftps_media_path(raw_path: Any) -> tuple[bool, str, str | None, str | None]:
    """Validate FTPS path strictly against removable media roots and block all eMMC p1..p15 traversal."""
    import posixpath

    if not isinstance(raw_path, str) or not raw_path.strip():
        return False, "", "invalid_ftps_path", "FTPS target path must be a non-empty string"
    s = raw_path.strip()
    if "\x00" in s or any(ord(c) < 32 or ord(c) == 127 for c in s):
        return False, "", "emmc_path_traversal_blocked", "Control or NUL bytes forbidden in FTPS path"
    if "\\" in s or ".." in s.split("/"):
        return False, "", "emmc_path_traversal_blocked", f"Path traversal blocked in FTPS path: {s!r}"
    if ".." in s:
        return False, "", "emmc_path_traversal_blocked", f"Parent traversal '..' blocked in FTPS path: {s!r}"

    if not s.startswith("/"):
        low_s = s.lower()
        if _FORBIDDEN_EMMC_PATH_RE.search(low_s) or any(tok in low_s for tok in ("nflasha", "mmcblk", "mtdblock", "backup.bin", "psd.bin")):
            return False, "", "emmc_path_traversal_blocked", f"eMMC/NVRAM target blocked in FTPS path: {s!r}"
        s = f"/mnt/slot_a/PRIVATE/M4ROOT/CLIP/{s}"

    norm = posixpath.normpath(s)
    if _FORBIDDEN_EMMC_PATH_RE.search(norm) or any(tok in norm.lower() for tok in ("nflasha", "cnflasha", "mmcblk", "mtdblock", "backup.bin", "psd.bin")):
        return False, "", "emmc_path_traversal_blocked", f"Internal eMMC partition p1..p15 traversal blocked: {norm!r}"
    if any(norm == pref or norm.startswith(pref + "/") for pref in _FORBIDDEN_FTPS_SYS_PREFIXES):
        return False, "", "emmc_path_traversal_blocked", f"System/eMMC path blocked for FTPS: {norm!r}"
    if not any(norm == root or norm.startswith(root + "/") for root in ALLOWED_FTPS_MEDIA_ROOTS):
        return False, "", "emmc_path_traversal_blocked", f"FTPS path {norm!r} outside removable media roots {ALLOWED_FTPS_MEDIA_ROOTS}"
    return True, norm, None, None


def compute_interval_cache_lut_ftp_derived(
    state: dict[str, Any],
    *,
    base_fps: float = 23.98,
    rec_fmt_idx: int = 0,
    sq_enabled: bool = False,
    wired_io_mode: str = "off",
    active_user_lut: dict[str, Any] | None = None,
    ftps_queue: Sequence[dict[str, Any]] = (),
    ftps_completed: Sequence[dict[str, Any]] = (),
    ftps_blocked_traversal_count: int = 0,
    ftps_last_blocked_path: str | None = None,
    wf12_00342260_hits: int = 0,
    mechanical_curtain_actuations: int = 0,
) -> dict[str, Any]:
    """Compute Phase 102 Picture Cache DDR budget, Interval Rec E-Shutter state, 3D LUT 33^3 status, & Wired FTPS state."""
    req_cache_sec = int(state.get("cache_seconds", 0))
    if req_cache_sec not in PICTURE_CACHE_ALLOWED_SECONDS:
        req_cache_sec = 0
    codec_req = str(state.get("codec_profile", "auto"))
    eff_profile, prof_meta = resolve_effective_cache_codec_profile(
        codec_req, base_fps=base_fps, rec_fmt_idx=rec_fmt_idx
    )
    mib_per_sec = float(prof_meta["mib_per_sec"])
    max_safe_sec = min(16, int(FX3_PICTURE_CACHE_DDR_BUDGET_MIB // mib_per_sec))
    requested_ddr_mib = round(req_cache_sec * mib_per_sec, 2)

    interval_en = bool(state.get("interval_rec_enabled", False)) and not bool(sq_enabled)
    interval_sec = max(INTERVAL_SEC_MIN, min(INTERVAL_SEC_MAX, int(state.get("interval_sec", 5))))
    target_shots = max(INTERVAL_TARGET_SHOTS_MIN, min(INTERVAL_TARGET_SHOTS_MAX, int(state.get("target_shots", 120))))
    shots_taken = max(0, min(target_shots, int(state.get("shots_taken", 0))))
    ae_tracking = str(state.get("ae_tracking", "Mid"))
    if ae_tracking not in INTERVAL_AE_TRACKING_MODES:
        ae_tracking = "Mid"

    suspension_reason: str | None = None
    if bool(sq_enabled):
        suspension_reason = "S&Q_VFR_ACTIVE"
    elif interval_en:
        suspension_reason = "INTERVAL_REC_ACTIVE"
    elif str(wired_io_mode or "off").lower() == "hdmi_raw16":
        suspension_reason = "HDMI_RAW16_ACTIVE"

    picture_cache_suspended = bool(req_cache_sec > 0 and suspension_reason is not None)
    if req_cache_sec == 0 or suspension_reason is not None:
        eff_cache_sec = 0
        allocated_ddr_mib = 0.0
        clamped_by_ddr = False
        picture_cache_active = False
    else:
        clamped_by_ddr = requested_ddr_mib > FX3_PICTURE_CACHE_DDR_BUDGET_MIB
        eff_cache_sec = min(req_cache_sec, max_safe_sec)
        allocated_ddr_mib = round(min(FX3_PICTURE_CACHE_DDR_BUDGET_MIB, eff_cache_sec * mib_per_sec), 2)
        picture_cache_active = eff_cache_sec > 0

    remaining_ddr_mib = round(FX3_PICTURE_CACHE_DDR_BUDGET_MIB - allocated_ddr_mib, 2)

    ftps_mode = str(state.get("ftps_mode", "Off"))
    if ftps_mode not in FTPS_MODES:
        ftps_mode = "Off"
    ftps_nic = str(state.get("ftps_nic_driver", "CDC_NCM_RTL8153"))
    if ftps_nic not in ALLOWED_FTPS_WIRED_NICS:
        ftps_nic = "CDC_NCM_RTL8153"

    lut_uploaded = bool(active_user_lut and active_user_lut.get("uploaded"))
    lut_slot = str(active_user_lut.get("slot")) if active_user_lut and lut_uploaded else None
    lut_title = str(active_user_lut.get("title") or active_user_lut.get("name")) if active_user_lut and lut_uploaded else None
    lut_sha = str(active_user_lut.get("sha256")) if active_user_lut and active_user_lut.get("sha256") else None
    lut_res33_sha = (
        str(active_user_lut.get("resampled_33_sha256"))
        if active_user_lut and active_user_lut.get("resampled_33_sha256")
        else lut_sha
    )
    lut_src_size = int(active_user_lut.get("source_grid_size", active_user_lut.get("size", 33))) if active_user_lut and lut_uploaded else 0
    lut_contrast = float(active_user_lut.get("contrast_signature", 1.0)) if active_user_lut and lut_uploaded else 1.0

    return {
        "cache_seconds": req_cache_sec,
        "effective_cache_seconds": eff_cache_sec,
        "max_safe_cache_seconds": max_safe_sec,
        "codec_profile": codec_req,
        "effective_codec_profile": eff_profile,
        "codec_label": prof_meta["codec"],
        "bitrate_mbps": float(prof_meta["bitrate_mbps"]),
        "mib_per_sec": mib_per_sec,
        "requested_ddr_mib": requested_ddr_mib,
        "allocated_ddr_mib": allocated_ddr_mib,
        "ddr_budget_mib": FX3_PICTURE_CACHE_DDR_BUDGET_MIB,
        "remaining_ddr_headroom_mib": remaining_ddr_mib,
        "fx3_total_dram_mib": FX3_TOTAL_AP_DRAM_MIB,
        "clamped_by_ddr_budget": clamped_by_ddr,
        "picture_cache_active": picture_cache_active,
        "picture_cache_suspended": picture_cache_suspended,
        "picture_cache_suspension_reason": suspension_reason,
        "timecode_forced_free_run": bool(picture_cache_active),
        "interval_rec_enabled": interval_en,
        "interval_sec": interval_sec,
        "target_shots": target_shots,
        "shots_taken": shots_taken,
        "ae_tracking": ae_tracking,
        "ae_slew_alpha": INTERVAL_AE_SLEW_ALPHA[ae_tracking],
        "shutter_type": "ELECTRONIC",
        "electronic_shutter_enforced": True,
        "mechanical_curtain_actuations": int(mechanical_curtain_actuations),
        "estimated_capture_wall_sec": interval_sec * target_shots,
        "packed_clip_duration_sec": round(float(target_shots) / max(1.0, float(base_fps)), 2),
        "mutually_excludes_sq_and_cache": True,
        "active_user_lut_uploaded": lut_uploaded,
        "active_user_lut_slot": lut_slot,
        "active_user_lut_title": lut_title,
        "active_user_lut_sha256": lut_sha,
        "active_user_lut_resampled_33_sha256": lut_res33_sha,
        "active_user_lut_source_size": lut_src_size,
        "active_user_lut_target_size": 33 if lut_uploaded else 0,
        "active_user_lut_resampling_method": "tetrahedral" if lut_uploaded else None,
        "active_user_lut_contrast_signature": lut_contrast,
        "active_user_lut_tint_hex": active_user_lut.get("tint_hex", "#808080") if active_user_lut and lut_uploaded else "#808080",
        "volatile_ram_only": True,
        "ftps_mode": ftps_mode,
        "ftps_transport": f"USB_LAN_{ftps_nic}",
        "ftps_nic_driver": ftps_nic,
        "ftps_tls_version": str(state.get("ftps_tls_version", "FTPES_TLS13")),
        "ftps_data_mode": "PASV",
        "ftps_active": ftps_mode != "Off",
        "ftps_queued_count": len(ftps_queue),
        "ftps_completed_count": len(ftps_completed),
        "ftps_queue": [dict(j) for j in ftps_queue[-16:]],
        "ftps_completed": [dict(j) for j in ftps_completed[-16:]],
        "ftps_blocked_traversal_count": int(ftps_blocked_traversal_count),
        "ftps_last_blocked_path": ftps_last_blocked_path,
        "p12_rf_off_enforced": True,
        "wifi_bt_rf_disabled": True,
        "wf12_00342260_hits": int(wf12_00342260_hits),
        "persistent_emmc_writes_authorized": False,
        "emmc_mutation_bytes": 0,
    }


def format_interval_cache_lut_ftp_command(state: dict[str, Any]) -> str:
    """Format deterministic Phase 102 ICLF host<->guest protocol telemetry line."""
    return (
        f"ICLF cache={state['effective_cache_seconds']}/{state['cache_seconds']}s"
        f"({state['allocated_ddr_mib']:.1f}/384MiB,susp={1 if state['picture_cache_suspended'] else 0}) "
        f"intvl={'ON' if state['interval_rec_enabled'] else 'OFF'}"
        f"({state['shots_taken']}/{state['target_shots']}@{state['interval_sec']}s,{state['ae_tracking']},MECH=0) "
        f"lut={state['active_user_lut_slot'] or 'none'} "
        f"ftps={state['ftps_mode']}(Q={state['ftps_queued_count']}/D={state['ftps_completed_count']},wf12={state['wf12_00342260_hits']})"
    )


def validate_interval_cache_lut_ftp_patch(
    body: Any,
    current_state: dict[str, Any] | None = None,
) -> tuple[bool, dict[str, Any], dict[str, Any] | None]:
    """Validate and normalize Phase 102 Picture Cache, Interval Rec, and Wired USB-LAN FTPS updates fail-closed."""
    if not isinstance(body, dict):
        return (
            False,
            {},
            {"ok": False, "error": "invalid_interval_cache_lut_ftp", "message": "Payload must be a JSON object"},
        )

    updates: dict[str, Any] = {}
    if body.get("reset") is True:
        updates.update(INTERVAL_CACHE_LUT_FTP_DEFAULTS)

    # Reject mechanical shutter tampering in Interval Recording
    if body.get("mechanical_shutter") is True or (
        "shutter_type" in body
        and body["shutter_type"] is not None
        and str(body["shutter_type"]).strip().upper() not in ("", "ELECTRONIC", "E-SHUTTER", "ESHUT")
    ):
        return (
            False,
            {},
            {
                "ok": False,
                "error": "mechanical_shutter_forbidden_in_interval_rec",
                "message": "Interval Recording strictly enforces Electronic Shutter (mechanical_curtain_actuations == 0) to protect FX3 shutter curtain",
            },
        )

    # Reject P12 Wi-Fi/BT RF-on tampering for FTPS
    if (
        body.get("wifi_enabled") is True
        or body.get("bt_enabled") is True
        or body.get("wifi_bt_rf_disabled") is False
        or body.get("p12_rf_off_enforced") is False
        or (
            "ftps_transport" in body
            and body["ftps_transport"] is not None
            and any(tok in str(body["ftps_transport"]).lower() for tok in ("wifi", "wlan", "bt", "bluetooth"))
        )
        or (
            "ftps_nic_driver" in body
            and body["ftps_nic_driver"] is not None
            and str(body["ftps_nic_driver"]).strip().upper() not in ("", "CDC_NCM_RTL8153", "CDC_NCM_AX88179")
        )
    ):
        return (
            False,
            {},
            {
                "ok": False,
                "error": "p12_rf_off_violation",
                "message": "P12 BK4 Airplane-Mode enforces Wi-Fi/BT RF-OFF (wf12_00342260_hits == 0); FTPS permitted strictly over wired USB-LAN (CDC-NCM / RTL8153)",
                "wf12_00342260_hits": 0,
            },
        )

    # Picture Cache seconds (0, 2, 4, 8, 16)
    if "cache_seconds" in body and body["cache_seconds"] is not None:
        raw_cs = body["cache_seconds"]
        if isinstance(raw_cs, bool):
            return False, {}, {"ok": False, "error": "invalid_cache_seconds", "message": "cache_seconds cannot be bool"}
        if isinstance(raw_cs, str):
            s_cs = raw_cs.strip().lower().rstrip("s")
            if s_cs == "off":
                s_cs = "0"
            try:
                cs_val = int(s_cs)
            except ValueError:
                return False, {}, {"ok": False, "error": "invalid_cache_seconds", "message": f"Invalid cache_seconds: {raw_cs!r}"}
        elif isinstance(raw_cs, (int, float)):
            if not math.isfinite(float(raw_cs)) or float(raw_cs) != float(int(raw_cs)):
                return False, {}, {"ok": False, "error": "invalid_cache_seconds", "message": f"Invalid cache_seconds: {raw_cs!r}"}
            cs_val = int(raw_cs)
        else:
            return False, {}, {"ok": False, "error": "invalid_cache_seconds", "message": f"Invalid cache_seconds: {raw_cs!r}"}
        if cs_val not in PICTURE_CACHE_ALLOWED_SECONDS:
            return (
                False,
                {},
                {
                    "ok": False,
                    "error": "invalid_cache_seconds",
                    "message": f"Unsupported cache_seconds={cs_val} (allowed: {list(PICTURE_CACHE_ALLOWED_SECONDS)})",
                    "allowed": list(PICTURE_CACHE_ALLOWED_SECONDS),
                },
            )
        updates["cache_seconds"] = cs_val

    if "codec_profile" in body and body["codec_profile"] is not None:
        cp_raw = str(body["codec_profile"]).strip()
        if cp_raw != "auto" and cp_raw not in PICTURE_CACHE_CODEC_PROFILES:
            return (
                False,
                {},
                {
                    "ok": False,
                    "error": "invalid_codec_profile",
                    "message": f"Unsupported codec_profile: {cp_raw!r}",
                    "allowed": ["auto"] + list(PICTURE_CACHE_CODEC_PROFILES.keys()),
                },
            )
        updates["codec_profile"] = cp_raw

    # Interval Recording fields
    if "interval_rec_enabled" in body and body["interval_rec_enabled"] is not None:
        raw_ie = body["interval_rec_enabled"]
        if isinstance(raw_ie, bool):
            updates["interval_rec_enabled"] = raw_ie
        elif isinstance(raw_ie, int) and raw_ie in (0, 1):
            updates["interval_rec_enabled"] = bool(raw_ie)
        elif isinstance(raw_ie, str) and raw_ie.strip().lower() in ("true", "1", "on", "yes", "false", "0", "off", "no"):
            updates["interval_rec_enabled"] = raw_ie.strip().lower() in ("true", "1", "on", "yes")
        else:
            return False, {}, {"ok": False, "error": "invalid_interval_rec_enabled", "message": f"Invalid interval_rec_enabled: {raw_ie!r}"}

    if "interval_sec" in body and body["interval_sec"] is not None:
        raw_is = body["interval_sec"]
        if isinstance(raw_is, bool) or not isinstance(raw_is, (int, float, str)):
            return False, {}, {"ok": False, "error": "invalid_interval_sec", "message": f"Invalid interval_sec: {raw_is!r}"}
        try:
            f_is = float(raw_is)
        except ValueError:
            return False, {}, {"ok": False, "error": "invalid_interval_sec", "message": f"Invalid interval_sec: {raw_is!r}"}
        if not math.isfinite(f_is) or int(f_is) < INTERVAL_SEC_MIN or int(f_is) > INTERVAL_SEC_MAX or f_is != float(int(f_is)):
            return (
                False,
                {},
                {"ok": False, "error": "invalid_interval_sec", "message": f"interval_sec must be integer in [{INTERVAL_SEC_MIN}, {INTERVAL_SEC_MAX}]"},
            )
        updates["interval_sec"] = int(f_is)

    if "target_shots" in body and body["target_shots"] is not None:
        raw_ts = body["target_shots"]
        if isinstance(raw_ts, bool) or not isinstance(raw_ts, (int, float, str)):
            return False, {}, {"ok": False, "error": "invalid_target_shots", "message": f"Invalid target_shots: {raw_ts!r}"}
        try:
            f_ts = float(raw_ts)
        except ValueError:
            return False, {}, {"ok": False, "error": "invalid_target_shots", "message": f"Invalid target_shots: {raw_ts!r}"}
        if not math.isfinite(f_ts) or int(f_ts) < INTERVAL_TARGET_SHOTS_MIN or int(f_ts) > INTERVAL_TARGET_SHOTS_MAX or f_ts != float(int(f_ts)):
            return (
                False,
                {},
                {"ok": False, "error": "invalid_target_shots", "message": f"target_shots must be integer in [{INTERVAL_TARGET_SHOTS_MIN}, {INTERVAL_TARGET_SHOTS_MAX}]"},
            )
        updates["target_shots"] = int(f_ts)

    if "ae_tracking" in body and body["ae_tracking"] is not None:
        raw_ae = body["ae_tracking"]
        if isinstance(raw_ae, bool) or not isinstance(raw_ae, str):
            return False, {}, {"ok": False, "error": "invalid_ae_tracking", "message": f"Invalid ae_tracking: {raw_ae!r}"}
        ae_norm = _INTERVAL_AE_ALIASES.get(raw_ae.strip().lower())
        if ae_norm is None:
            return (
                False,
                {},
                {
                    "ok": False,
                    "error": "invalid_ae_tracking",
                    "message": f"Unsupported ae_tracking: {raw_ae!r}",
                    "allowed": list(INTERVAL_AE_TRACKING_MODES),
                },
            )
        updates["ae_tracking"] = ae_norm

    if "ftps_mode" in body and body["ftps_mode"] is not None:
        raw_fm = body["ftps_mode"]
        if isinstance(raw_fm, bool) or not isinstance(raw_fm, str):
            return False, {}, {"ok": False, "error": "invalid_ftps_mode", "message": f"Invalid ftps_mode: {raw_fm!r}"}
        fm_norm = _FTPS_MODE_ALIASES.get(raw_fm.strip().lower())
        if fm_norm is None:
            return (
                False,
                {},
                {
                    "ok": False,
                    "error": "invalid_ftps_mode",
                    "message": f"Unsupported ftps_mode: {raw_fm!r}",
                    "allowed": list(FTPS_MODES),
                },
            )
        updates["ftps_mode"] = fm_norm

    if "ftps_nic_driver" in body and body["ftps_nic_driver"] is not None:
        nic_norm = str(body["ftps_nic_driver"]).strip().upper()
        if nic_norm in ALLOWED_FTPS_WIRED_NICS:
            updates["ftps_nic_driver"] = nic_norm

    if "ftps_data_mode" in body and body["ftps_data_mode"] is not None:
        dm = str(body["ftps_data_mode"]).strip().upper()
        if dm != "PASV":
            return (
                False,
                {},
                {"ok": False, "error": "invalid_ftps_data_mode", "message": "FTPS requires passive PASV mode; Active PORT rejected"},
            )

    if "advance_shots" in body and body["advance_shots"] is not None:
        raw_adv = body["advance_shots"]
        if isinstance(raw_adv, bool) or not isinstance(raw_adv, int) or raw_adv < 0 or raw_adv > 9999:
            return False, {}, {"ok": False, "error": "invalid_advance_shots", "message": "advance_shots must be int in [0, 9999]"}
        updates["advance_shots"] = raw_adv

    if body.get("trigger_shot") is True:
        updates["advance_shots"] = int(updates.get("advance_shots", 0)) + 1
    if body.get("reset_shots") is True:
        updates["reset_shots"] = True

    enqueue_path = body.get("enqueue_path") or body.get("ftp_path") or body.get("target_path")
    if enqueue_path is not None:
        ok_p, norm_p, err_code, err_msg = validate_ftps_media_path(enqueue_path)
        if not ok_p:
            return (
                False,
                {},
                {
                    "ok": False,
                    "error": err_code or "emmc_path_traversal_blocked",
                    "message": err_msg or "eMMC path traversal blocked",
                    "blocked_emmc_partition": True,
                    "blocked_path": str(enqueue_path),
                    "wf12_00342260_hits": 0,
                },
            )
        updates["enqueue_path"] = norm_p

    for flag_key in ("enqueue_current_clip", "process_next_job", "advance_queue", "clear_queue"):
        if body.get(flag_key) is True:
            updates[flag_key] = True

    return True, updates, None


# ---------------------------------------------------------------------------
# Phase 109: M&C 4-Cam Wired Fleet, HDMI->12G-SDI AVI/RP188, E/PL Shading, C2PA
# ---------------------------------------------------------------------------

MC_FLEET_ROLES: tuple[str, ...] = (
    "Solo",
    "A_Cam_Master",
    "B_Cam_Follower",
    "C_Cam_Follower",
    "D_Cam_Follower",
)
_MC_FLEET_ROLE_TO_IDX: dict[str, int] = {r: i for i, r in enumerate(MC_FLEET_ROLES)}
_MC_FLEET_ROLE_ALIASES: dict[str, str] = {
    "solo": "Solo",
    "a_cam_master": "A_Cam_Master",
    "a_master": "A_Cam_Master",
    "a": "A_Cam_Master",
    "b_cam_follower": "B_Cam_Follower",
    "b_follower": "B_Cam_Follower",
    "b": "B_Cam_Follower",
    "c_cam_follower": "C_Cam_Follower",
    "c_follower": "C_Cam_Follower",
    "c": "C_Cam_Follower",
    "d_cam_follower": "D_Cam_Follower",
    "d_follower": "D_Cam_Follower",
    "d": "D_Cam_Follower",
}

SDI_BRIDGE_CONVERTERS: tuple[str, ...] = (
    "BMD_Micro_Converter_12G",
    "Teradek_Bolt_HDMI_SDI",
    "Atomos_Connect_12G",
    "Off",
)
_SDI_BRIDGE_TO_IDX: dict[str, int] = {c: i for i, c in enumerate(SDI_BRIDGE_CONVERTERS)}
_SDI_BRIDGE_ALIASES: dict[str, str] = {
    "bmd_micro_converter_12g": "BMD_Micro_Converter_12G",
    "bmd_12g": "BMD_Micro_Converter_12G",
    "bmd": "BMD_Micro_Converter_12G",
    "teradek_bolt_hdmi_sdi": "Teradek_Bolt_HDMI_SDI",
    "teradek": "Teradek_Bolt_HDMI_SDI",
    "atomos_connect_12g": "Atomos_Connect_12G",
    "atomos": "Atomos_Connect_12G",
    "off": "Off",
    "none": "Off",
}

LENS_MOUNT_TYPES: tuple[str, ...] = (
    "Sony_EMount_12Pin_GM",
    "Manual_PL_Adapter_Unchipped",
)
_LENS_MOUNT_ALIASES: dict[str, str] = {
    "sony_emount_12pin_gm": "Sony_EMount_12Pin_GM",
    "e_mount_12pin": "Sony_EMount_12Pin_GM",
    "emount": "Sony_EMount_12Pin_GM",
    "gm": "Sony_EMount_12Pin_GM",
    "manual_pl_adapter_unchipped": "Manual_PL_Adapter_Unchipped",
    "pl_to_e_unchipped": "Manual_PL_Adapter_Unchipped",
    "manual_pl": "Manual_PL_Adapter_Unchipped",
    "pl": "Manual_PL_Adapter_Unchipped",
}

G31_15MM_LWS_WEIGHT_THRESHOLD_KG = 1.2
C2PA_VAULT_STATUS_LOCKED = "CNFLASHA_RDONLY_ZERO_TOUCH"
C2PA_PHASE109_SPEC_VERSION = "2.1"
C2PA_PHASE109_PROVENANCE_MODE = "CLEAN_ROOM_RESEARCH_UNATTESTED"
C2PA_PHASE109_CLAIM_GENERATOR = "FX3-VM-CleanRoom-Research/Phase109-MCFleet-SDI-C2PA"

CEA861_AVI_PACKET_TYPE = 0x82
CEA861_AVI_VERSION = 0x02
CEA861_AVI_PAYLOAD_LEN = 13
CEA861_AVI_TOTAL_BYTES = 17
SMPTE_RP188_ATC_DID = 0x60
SMPTE_RP188_ATC_SDID = 0x60

_AVI_Y_CODES: dict[str, int] = {"RGB": 0b00, "YCBCR_422": 0b01, "YCBCR_444": 0b10, "YCBCR_420": 0b11}
_AVI_Q_CODES: dict[str, int] = {"DEFAULT": 0b00, "LIMITED": 0b01, "FULL": 0b10}
_AVI_YQ_CODES: dict[str, int] = {"LIMITED": 0b00, "FULL": 0b01}

_FORBIDDEN_C2PA_VAULT_TOKENS: tuple[str, ...] = (
    "/dev/cnflasha",
    "cnflasha://",
    "/dev/mmcblk0rpmb",
    "rpmb://",
    "/dev/spacc",
    "rq_lic.dat",
    "device_priv.key",
    "/cert/",
    "0xf7fc0000",
)

MC_FLEET_SDI_C2PA_DEFAULTS: dict[str, Any] = {
    "fleet_role": "Solo",
    "fleet_cams_online": 1,
    "fleet_nic_driver": "CDC_NCM_RTL8153",
    "gang_rec_trigger": False,
    "sdi_bridge_converter": "BMD_Micro_Converter_12G",
    "hdmi_rec_control_enabled": True,
    "hdmi_tc_output_enabled": True,
    "recorder_range_expectation": "AUTO_MATCH",
    "mount_type": "Sony_EMount_12Pin_GM",
    "lens_model": "SEL2470GM2 (FE 24-70mm F2.8 GM II)",
    "lens_kg": 0.695,
    "focal_length_mm": 24,
    "rod_support_15mm_lws": False,
}

MC_FLEET_SDI_C2PA_SPECS: dict[str, Any] = {
    "fleet_roles": list(MC_FLEET_ROLES),
    "fleet_cams_range": [1, 4],
    "fleet_wired_nics": ["CDC_NCM_RTL8153", "CDC_NCM_AX88179"],
    "ptp_ip_port": 15740,
    "p12_rf_off_enforced": True,
    "wf12_00342260_hits_locked": 0,
    "sdi_bridge_converters": list(SDI_BRIDGE_CONVERTERS),
    "avi_infoframe_bytes": CEA861_AVI_TOTAL_BYTES,
    "rp188_atc_did": f"0x{SMPTE_RP188_ATC_DID:02x}",
    "rp188_atc_sdid": f"0x{SMPTE_RP188_ATC_SDID:02x}",
    "mount_types": list(LENS_MOUNT_TYPES),
    "g31_15mm_lws_threshold_kg": G31_15MM_LWS_WEIGHT_THRESHOLD_KG,
    "c2pa_vault_status_locked": C2PA_VAULT_STATUS_LOCKED,
    "c2pa_spec_version": C2PA_PHASE109_SPEC_VERSION,
    "private_key_reads_locked": 0,
    "cnflasha_writes_locked": 0,
    "mailbox_magic": "0x4D43464C",
    "mailbox_slots": "mb[52..55]",
    "supported_langs": ["en", "zh-CN", "zh-TW", "ja"],
}


def build_cea861_avi_infoframe(
    *,
    colorspace: str = "YCBCR_422",
    rgb_quantization: str = "DEFAULT",
    ycc_quantization: str = "LIMITED",
    vic: int = 97,
) -> dict[str, Any]:
    """Build exact 17-byte CEA-861-G HDMI AVI InfoFrame with 0x100 - sum == 0 checksum parity."""
    cs_u = colorspace.upper()
    q_u = rgb_quantization.upper()
    yq_u = ycc_quantization.upper()
    y_code = _AVI_Y_CODES.get(cs_u, 0b01)
    q_code = _AVI_Q_CODES.get(q_u, 0b00)
    yq_code = _AVI_YQ_CODES.get(yq_u, 0b00)

    hb = bytes((CEA861_AVI_PACKET_TYPE, CEA861_AVI_VERSION, CEA861_AVI_PAYLOAD_LEN))
    pb = bytearray(CEA861_AVI_PAYLOAD_LEN)
    pb[0] = (y_code & 0x03) << 5      # PB1: Y1:Y0 in bits 6:5
    pb[1] = 0x28                      # PB2: M1:M0=10 (16:9), R3:R0=1000
    pb[2] = (q_code & 0x03) << 2      # PB3: Q1:Q0 in bits 3:2
    pb[3] = int(vic) & 0x7F           # PB4: VIC
    pb[4] = (yq_code & 0x03) << 6     # PB5: YQ1:YQ0 in bits 7:6

    body_sum = sum(hb) + sum(pb)
    checksum = (0x100 - (body_sum & 0xFF)) & 0xFF
    pkt = hb + bytes((checksum,)) + bytes(pb)
    total_mod256 = sum(pkt) & 0xFF
    return {
        "packet_bytes": len(pkt),
        "packet_hex": pkt.hex().upper(),
        "checksum_byte": checksum,
        "checksum_hex": f"0x{checksum:02X}",
        "checksum_zero_mod256": total_mod256,
        "checksum_valid": total_mod256 == 0,
        "colorspace": cs_u,
        "rgb_quantization": q_u,
        "ycc_quantization": yq_u,
        "vic": int(vic) & 0x7F,
    }


def pack_smpte_rp188_atc_packet(
    *,
    rec_tc: str = "00:00:00:00",
    drop_frame: bool = False,
    rec_trigger_bit: int = 0,
) -> dict[str, Any]:
    """Pack and verify SMPTE ST 12-2 / RP 188 8-nibble BCD timecode + DBB REC-trigger bit."""
    parts = [int(p) for p in rec_tc.replace(";", ":").split(":")]
    if len(parts) != 4:
        parts = [0, 0, 0, 0]
    hh, mm, ss, ff = [max(0, v) for v in parts]
    hh %= 24
    mm %= 60
    ss %= 60
    ff %= 60
    f_t, f_o = divmod(ff, 10)
    s_t, s_o = divmod(ss, 10)
    m_t, m_o = divmod(mm, 10)
    h_t, h_o = divmod(hh, 10)
    df_flag = 1 if drop_frame else 0
    tc_word = (
        (f_o & 0x0F)
        | ((f_t & 0x03) << 4)
        | (df_flag << 6)
        | ((s_o & 0x0F) << 8)
        | ((s_t & 0x07) << 12)
        | ((m_o & 0x0F) << 16)
        | ((m_t & 0x07) << 20)
        | ((h_o & 0x0F) << 24)
        | ((h_t & 0x03) << 28)
    )
    dbb_word = ((int(rec_trigger_bit) & 0x01) << 7) | (SMPTE_RP188_ATC_SDID & 0x7F)
    unpacked_rec = (dbb_word >> 7) & 0x01
    u_ff = (tc_word & 0x0F) + (((tc_word >> 4) & 0x03) * 10)
    u_ss = ((tc_word >> 8) & 0x0F) + (((tc_word >> 12) & 0x07) * 10)
    u_mm = ((tc_word >> 16) & 0x0F) + (((tc_word >> 20) & 0x07) * 10)
    u_hh = ((tc_word >> 24) & 0x0F) + (((tc_word >> 28) & 0x03) * 10)
    sep = ";" if ((tc_word >> 6) & 0x01) else ":"
    unpacked_tc = f"{u_hh:02d}:{u_mm:02d}:{u_ss:02d}{sep}{u_ff:02d}"
    return {
        "atc_did": f"0x{SMPTE_RP188_ATC_DID:02x}",
        "atc_sdid": f"0x{SMPTE_RP188_ATC_SDID:02x}",
        "tc_word_hex": f"0x{tc_word:08X}",
        "dbb_word_hex": f"0x{dbb_word:02X}",
        "rec_trigger_bit": int(rec_trigger_bit) & 0x01,
        "unpacked_rec_bit": unpacked_rec,
        "unpacked_tc": unpacked_tc,
        "parity_ok": (unpacked_rec == (int(rec_trigger_bit) & 0x01)) and (unpacked_tc == f"{hh:02d}:{mm:02d}:{ss:02d}{sep}{ff:02d}"),
    }


def compute_mc_fleet_sdi_c2pa_derived(
    state: dict[str, Any],
    *,
    rec_state: str = "STBY",
    rec_tc: str = "00:00:00:00",
    base_fps: float = 23.98,
    base_look: str = "S-Cinetone",
    wired_io_mode: str = "off",
    c2pa_blocked_attempts: int = 0,
    c2pa_last_blocked_reason: str | None = None,
    wf12_00342260_hits: int = 0,
) -> dict[str, Any]:
    """Compute Phase 109 M&C 4-Cam Fleet, HDMI->12G-SDI AVI/RP188, E-Mount/PL Shading & C2PA state."""
    fleet_role = str(state.get("fleet_role", "Solo"))
    if fleet_role not in MC_FLEET_ROLES:
        fleet_role = "Solo"
    cams_online = max(1, min(4, int(state.get("fleet_cams_online", 1))))
    nic_driver = str(state.get("fleet_nic_driver", "CDC_NCM_RTL8153"))
    if nic_driver not in ("CDC_NCM_RTL8153", "CDC_NCM_AX88179"):
        nic_driver = "CDC_NCM_RTL8153"

    rec_on = (str(rec_state).upper() == "REC")
    gang_rec_req = bool(state.get("gang_rec_trigger", False))
    gang_rec_eff = bool(gang_rec_req or (rec_on and fleet_role != "Solo"))

    ptp_offsets_us = [0.0, 42.0, 58.0, 64.0]
    cam_labels = ("A-Cam", "B-Cam", "C-Cam", "D-Cam")
    role_to_cam_idx = {
        "Solo": 0,
        "A_Cam_Master": 0,
        "B_Cam_Follower": 1,
        "C_Cam_Follower": 2,
        "D_Cam_Follower": 3,
    }
    self_idx = role_to_cam_idx.get(fleet_role, 0)
    fleet_nodes: list[dict[str, Any]] = []
    for idx in range(4):
        online = idx < cams_online
        node_rec = bool(online and (gang_rec_eff or (idx == self_idx and rec_on)))
        fleet_nodes.append({
            "cam_slot": cam_labels[idx],
            "body_profile": "FX6_MASTER" if idx == 0 else "FX6_ON_FX3",
            "ip_addr": f"192.168.10.{101 + idx}",
            "online": online,
            "is_local_node": idx == self_idx,
            "nic_driver": nic_driver,
            "link_speed_mbps": 1000 if online else 0,
            "ptp_offset_us": ptp_offsets_us[idx] if online else 0.0,
            "rec_tally": "REC" if node_rec else ("STBY" if online else "OFFLINE"),
            "p12_rf_off_enforced": True,
            "wf12_00342260_hits": 0,
        })
    max_skew_us = max((n["ptp_offset_us"] for n in fleet_nodes if n["online"]), default=0.0)
    gang_skew_ms = round((max_skew_us / 1000.0) + 0.14, 3) if cams_online > 1 else 0.0

    # HDMI AVI InfoFrame + HDMI->12G-SDI RP 188 Bridge
    sdi_conv = str(state.get("sdi_bridge_converter", "BMD_Micro_Converter_12G"))
    if sdi_conv not in SDI_BRIDGE_CONVERTERS:
        sdi_conv = "BMD_Micro_Converter_12G"
    sdi_active = (sdi_conv != "Off")
    hdmi_rec_ctrl = bool(state.get("hdmi_rec_control_enabled", True))
    hdmi_tc_out = bool(state.get("hdmi_tc_output_enabled", True))

    look_l = str(base_look or "").lower()
    if str(wired_io_mode or "off").lower() == "hdmi_raw16":
        sig_mode = "HDMI_RAW16_LINEAR"
        avi_cs = "RGB"
        avi_q = "FULL"
        avi_yq = "LIMITED"
        quant_range = "FULL_0_1023_RAW16"
    elif "s-log3" in look_l or "slog3" in look_l:
        sig_mode = "SLOG3_EXTENDED_64_1019"
        avi_cs = "YCBCR_422"
        avi_q = "DEFAULT"
        avi_yq = "LIMITED"
        quant_range = "EXTENDED_64_1019"
    elif "cinetone" in look_l:
        sig_mode = "SCINETONE_LEGAL_64_940"
        avi_cs = "YCBCR_422"
        avi_q = "DEFAULT"
        avi_yq = "LIMITED"
        quant_range = "LEGAL_64_940"
    else:
        sig_mode = "REC709_LEGAL_64_940"
        avi_cs = "YCBCR_422"
        avi_q = "DEFAULT"
        avi_yq = "LIMITED"
        quant_range = "LEGAL_64_940"

    vic = 97 if float(base_fps) >= 49.0 else 93  # 3840x2160p59.94 vs 2160p23.98
    avi = build_cea861_avi_infoframe(
        colorspace=avi_cs,
        rgb_quantization=avi_q,
        ycc_quantization=avi_yq,
        vic=vic,
    )
    rp188_bit = 1 if (rec_on and sdi_active and hdmi_rec_ctrl and hdmi_tc_out) else 0
    df = round(float(base_fps), 2) in (29.97, 59.94)
    rp188 = pack_smpte_rp188_atc_packet(rec_tc=rec_tc, drop_frame=df, rec_trigger_bit=rp188_bit)

    # E-Mount 12-Pin vs Manual-PL Hot-Swap Shading Arbitrator + G31 LWS Warning
    mount_type = str(state.get("mount_type", "Sony_EMount_12Pin_GM"))
    if mount_type not in LENS_MOUNT_TYPES:
        mount_type = "Sony_EMount_12Pin_GM"
    is_pl = (mount_type == "Manual_PL_Adapter_Unchipped")
    lens_model = str(state.get("lens_model") or (
        "Atlas Orion 40mm 2x PL (Unchipped)" if is_pl else "SEL2470GM2 (FE 24-70mm F2.8 GM II)"
    ))
    lens_kg = round(max(0.1, min(10.0, float(state.get("lens_kg", 0.695)))), 3)
    focal_mm = max(10, min(250, int(state.get("focal_length_mm", 40 if is_pl else 24))))
    rod_lws = bool(state.get("rod_support_15mm_lws", False))
    lws_required = bool(lens_kg > G31_15MM_LWS_WEIGHT_THRESHOLD_KG)
    g31_lws_warning = bool(lws_required and not rod_lws)

    if is_pl:
        e_pins = 0
        uart_active = False
        vignetting_gain = 1.0
        ca_r_scale = 1.0
        ca_b_scale = 1.0
        distortion_k1 = 0.0
        breathing_scale = 1.0
        shading_identity_reset = True
        reset_latency_ms = 0.42
    else:
        e_pins = 12
        uart_active = True
        vignetting_gain = 1.318
        ca_r_scale = 1.0015
        ca_b_scale = 0.9986
        distortion_k1 = -0.042
        breathing_scale = 1.045
        shading_identity_reset = False
        reset_latency_ms = 2.15

    frame_period_ms = round(1001.0 / 60.0, 4)

    return {
        "fleet_role": fleet_role,
        "fleet_cams_online": cams_online,
        "fleet_nic_driver": nic_driver,
        "fleet_transport": f"USB_LAN_{nic_driver}",
        "ptp_ip_port": 15740,
        "ptp_max_clock_skew_us": max_skew_us,
        "gang_rec_trigger": gang_rec_eff,
        "gang_rec_skew_ms": gang_skew_ms,
        "fleet_nodes": fleet_nodes,
        "p12_rf_off_enforced": True,
        "wifi_bt_rf_disabled": True,
        "wf12_00342260_hits": int(wf12_00342260_hits),
        "sdi_bridge_converter": sdi_conv,
        "sdi_bridge_active": sdi_active,
        "hdmi_rec_control_enabled": hdmi_rec_ctrl,
        "hdmi_tc_output_enabled": hdmi_tc_out,
        "recorder_range_expectation": str(state.get("recorder_range_expectation", "AUTO_MATCH")),
        "avi_signal_range_mode": sig_mode,
        "avi_quantization_range": quant_range,
        "avi_colorspace": avi["colorspace"],
        "avi_ycc_quantization": avi["ycc_quantization"],
        "avi_rgb_quantization": avi["rgb_quantization"],
        "avi_vic": avi["vic"],
        "avi_infoframe_bytes": avi["packet_bytes"],
        "avi_infoframe_hex": avi["packet_hex"],
        "avi_checksum_byte": avi["checksum_byte"],
        "avi_checksum_hex": avi["checksum_hex"],
        "avi_checksum_zero_mod256": avi["checksum_zero_mod256"],
        "avi_checksum_valid": avi["checksum_valid"],
        "shadow_crush_prevented": True,
        "slog3_black_0pct_code10": 95,
        "slog3_grey_18pct_code10": 420,
        "slog3_white_90pct_code10": 598,
        "rp188_atc_did": rp188["atc_did"],
        "rp188_atc_sdid": rp188["atc_sdid"],
        "rp188_rec_trigger_bit": rp188["rec_trigger_bit"],
        "rp188_tc_word_hex": rp188["tc_word_hex"],
        "rp188_dbb_word_hex": rp188["dbb_word_hex"],
        "rp188_parity_ok": rp188["parity_ok"],
        "physical_12g_sdi_bnc_present": False,
        "ghost_sdi_bnc_hw_faults": 0,
        "mount_type": mount_type,
        "lens_model": lens_model,
        "lens_kg": lens_kg,
        "focal_length_mm": focal_mm,
        "electronic_pins_active": e_pins,
        "lens_uart_active": uart_active,
        "vignetting_comp_gain": vignetting_gain,
        "ca_r_scale": ca_r_scale,
        "ca_b_scale": ca_b_scale,
        "distortion_k1": distortion_k1,
        "breathing_scale": breathing_scale,
        "shading_identity_reset": shading_identity_reset,
        "reset_latency_ms": reset_latency_ms,
        "frame_period_ms": frame_period_ms,
        "reset_under_one_frame": bool(reset_latency_ms < frame_period_ms),
        "stale_gm_frames_leaked": 0,
        "rod_support_15mm_lws": rod_lws,
        "g31_15mm_lws_threshold_kg": G31_15MM_LWS_WEIGHT_THRESHOLD_KG,
        "g31_15mm_lws_support_required": lws_required,
        "g31_15mm_lws_warning": g31_lws_warning,
        "g31_15mm_lws_message": (
            f"G31 WARNING: lens_kg={lens_kg:.2f}kg > 1.2kg without 15mm LWS rod support!"
            if g31_lws_warning
            else (
                f"G31 OK: 15mm LWS rod support engaged ({lens_kg:.2f}kg)"
                if (lws_required and rod_lws)
                else f"E-Mount flange nominal ({lens_kg:.2f}kg <= 1.2kg)"
            )
        ),
        "c2pa_spec_version": C2PA_PHASE109_SPEC_VERSION,
        "c2pa_vault_status": C2PA_VAULT_STATUS_LOCKED,
        "c2pa_provenance_mode": C2PA_PHASE109_PROVENANCE_MODE,
        "c2pa_claim_generator": C2PA_PHASE109_CLAIM_GENERATOR,
        "private_key_reads": 0,
        "private_key_exports": 0,
        "cnflasha_writes": 0,
        "cnflasha_mutation_bytes": 0,
        "rpmb_writes": 0,
        "hardware_attestation_claimed": False,
        "c2pa_spoofed": False,
        "c2pa_blocked_attempts": int(c2pa_blocked_attempts),
        "c2pa_last_blocked_reason": c2pa_last_blocked_reason,
        "persistent_emmc_writes_authorized": False,
    }


def format_mc_fleet_sdi_c2pa_command(state: dict[str, Any]) -> str:
    """Format deterministic Phase 109 MCFL host<->guest protocol telemetry line."""
    return (
        f"MCFL role={state['fleet_role']}({state['fleet_cams_online']}/4,"
        f"gang={1 if state['gang_rec_trigger'] else 0},wf12={state['wf12_00342260_hits']}) "
        f"sdi={state['sdi_bridge_converter']}(rp188={state['rp188_rec_trigger_bit']},"
        f"avi_cs={state['avi_checksum_hex']},rng={state['avi_quantization_range']}) "
        f"mount={state['mount_type']}(pins={state['electronic_pins_active']},"
        f"shd={state['vignetting_comp_gain']:.2f}x,kg={state['lens_kg']:.2f},lws_warn={1 if state['g31_15mm_lws_warning'] else 0}) "
        f"c2pa={state['c2pa_vault_status']}(kr=0,cw=0)"
    )


def validate_mc_fleet_sdi_c2pa_patch(
    body: Any,
    current_state: dict[str, Any] | None = None,
    *,
    base_look: str = "S-Cinetone",
    wired_io_mode: str = "off",
) -> tuple[bool, dict[str, Any], dict[str, Any] | None]:
    """Validate and normalize Phase 109 M&C Fleet, HDMI->12G-SDI, Mount Shading & C2PA updates fail-closed."""
    if not isinstance(body, dict):
        return False, {}, {"ok": False, "error": "invalid_mc_fleet_sdi_c2pa", "message": "Payload must be a JSON object"}

    updates: dict[str, Any] = {}
    if body.get("reset") is True:
        updates.update(MC_FLEET_SDI_C2PA_DEFAULTS)

    # 1. C2PA 2.1 / cnflasha Zero-Touch Guard (fail-closed)
    c2pa_op = str(body.get("c2pa_operation") or "").strip().upper()
    c2pa_path = str(body.get("c2pa_target_path") or body.get("target_path") or "").strip().lower()
    if (
        c2pa_op in ("READ_KEY", "EXPORT_KEY", "WRITE_VAULT", "MOUNT_RW", "SPOOF_CERT")
        or body.get("claim_hardware_attestation") is True
        or body.get("hardware_attestation_claimed") is True
        or body.get("c2pa_spoof") is True
        or body.get("c2pa_spoofed") is True
        or (body.get("c2pa_vault_status") not in (None, "", C2PA_VAULT_STATUS_LOCKED))
        or (body.get("private_key_reads") not in (None, 0))
        or (body.get("cnflasha_writes") not in (None, 0))
        or any(tok in c2pa_path for tok in _FORBIDDEN_C2PA_VAULT_TOKENS)
    ):
        return (
            False,
            {},
            {
                "ok": False,
                "error": "c2pa_cnflasha_zero_touch_blocked",
                "message": "C2PA 2.1 cnflasha key-vault is strictly CNFLASHA_RDONLY_ZERO_TOUCH (private_key_reads=0, cnflasha_writes=0, no spoofed attestation)",
                "c2pa_vault_status": C2PA_VAULT_STATUS_LOCKED,
                "private_key_reads": 0,
                "cnflasha_writes": 0,
            },
        )

    # 2. P12 Wi-Fi/BT RF-Off Guard (fail-closed)
    if (
        body.get("wifi_enabled") is True
        or body.get("bt_enabled") is True
        or body.get("wifi_bt_rf_disabled") is False
        or body.get("p12_rf_off_enforced") is False
        or (body.get("wf12_00342260_hits") not in (None, 0))
        or (
            "fleet_transport" in body
            and body["fleet_transport"] is not None
            and any(tok in str(body["fleet_transport"]).lower() for tok in ("wifi", "wlan", "bt", "bluetooth"))
        )
        or (
            "fleet_nic_driver" in body
            and body["fleet_nic_driver"] is not None
            and str(body["fleet_nic_driver"]).strip().upper() not in ("", "CDC_NCM_RTL8153", "CDC_NCM_AX88179")
        )
    ):
        return (
            False,
            {},
            {
                "ok": False,
                "error": "p12_rf_off_violation",
                "message": "P12 BK4 Airplane-Mode enforces Wi-Fi/BT RF-OFF (wf12_00342260_hits == 0); M&C fleet uses wired Gigabit USB-LAN only",
                "wf12_00342260_hits": 0,
            },
        )

    # 3. Fleet Role / Cams Online / Gang REC
    if "fleet_role" in body and body["fleet_role"] is not None:
        raw_role = body["fleet_role"]
        if not isinstance(raw_role, str):
            return False, {}, {"ok": False, "error": "invalid_fleet_role", "message": f"Invalid fleet_role: {raw_role!r}"}
        role_norm = _MC_FLEET_ROLE_ALIASES.get(raw_role.strip().lower())
        if role_norm is None:
            return (
                False,
                {},
                {"ok": False, "error": "invalid_fleet_role", "message": f"Unsupported fleet_role: {raw_role!r}", "allowed": list(MC_FLEET_ROLES)},
            )
        updates["fleet_role"] = role_norm

    if "fleet_cams_online" in body and body["fleet_cams_online"] is not None:
        raw_co = body["fleet_cams_online"]
        if isinstance(raw_co, bool) or not isinstance(raw_co, (int, float, str)):
            return False, {}, {"ok": False, "error": "invalid_fleet_cams_online", "message": f"Invalid fleet_cams_online: {raw_co!r}"}
        try:
            f_co = float(raw_co)
        except ValueError:
            return False, {}, {"ok": False, "error": "invalid_fleet_cams_online", "message": f"Invalid fleet_cams_online: {raw_co!r}"}
        if not math.isfinite(f_co) or f_co != float(int(f_co)) or int(f_co) < 1 or int(f_co) > 4:
            return False, {}, {"ok": False, "error": "invalid_fleet_cams_online", "message": "fleet_cams_online must be integer in [1, 4]"}
        updates["fleet_cams_online"] = int(f_co)

    if "fleet_nic_driver" in body and body["fleet_nic_driver"] is not None:
        nic_u = str(body["fleet_nic_driver"]).strip().upper()
        if nic_u:
            updates["fleet_nic_driver"] = nic_u

    if "gang_rec_trigger" in body and body["gang_rec_trigger"] is not None:
        raw_gr = body["gang_rec_trigger"]
        if isinstance(raw_gr, bool):
            updates["gang_rec_trigger"] = raw_gr
        elif isinstance(raw_gr, int) and raw_gr in (0, 1):
            updates["gang_rec_trigger"] = bool(raw_gr)
        else:
            return False, {}, {"ok": False, "error": "invalid_gang_rec_trigger", "message": f"Invalid gang_rec_trigger: {raw_gr!r}"}

    # 4. HDMI AVI InfoFrame + HDMI->12G-SDI Bridge
    if "sdi_bridge_converter" in body and body["sdi_bridge_converter"] is not None:
        raw_sb = body["sdi_bridge_converter"]
        if not isinstance(raw_sb, str):
            return False, {}, {"ok": False, "error": "invalid_sdi_bridge_converter", "message": f"Invalid sdi_bridge_converter: {raw_sb!r}"}
        sb_low = raw_sb.strip().lower()
        if sb_low in ("fx6_native_12g_bnc", "native_sdi_bnc"):
            return (
                False,
                {},
                {
                    "ok": False,
                    "error": "fx3_missing_sdi_bnc_hardware",
                    "message": "ILME-FX3 lacks physical 12G-SDI BNC; use active HDMI->12G-SDI converter bridge",
                    "ghost_sdi_bnc_hw_faults": 0,
                },
            )
        sb_norm = _SDI_BRIDGE_ALIASES.get(sb_low)
        if sb_norm is None:
            return (
                False,
                {},
                {"ok": False, "error": "invalid_sdi_bridge_converter", "message": f"Unsupported sdi_bridge_converter: {raw_sb!r}", "allowed": list(SDI_BRIDGE_CONVERTERS)},
            )
        updates["sdi_bridge_converter"] = sb_norm

    for bkey in ("hdmi_rec_control_enabled", "hdmi_tc_output_enabled", "rod_support_15mm_lws"):
        if bkey in body and body[bkey] is not None:
            raw_bv = body[bkey]
            if isinstance(raw_bv, bool):
                updates[bkey] = raw_bv
            elif isinstance(raw_bv, int) and raw_bv in (0, 1):
                updates[bkey] = bool(raw_bv)
            else:
                return False, {}, {"ok": False, "error": f"invalid_{bkey}", "message": f"Invalid {bkey}: {raw_bv!r}"}

    # Block S-Log3 / S-Cinetone legal-to-full double-scaling shadow crush
    rec_exp = str(body.get("recorder_range_expectation") or "").strip().upper()
    if rec_exp:
        if rec_exp not in ("AUTO_MATCH", "LEGAL_OR_EXTENDED", "FULL_RANGE"):
            return False, {}, {"ok": False, "error": "invalid_recorder_range_expectation", "message": f"Invalid recorder_range_expectation: {rec_exp!r}"}
        if rec_exp == "FULL_RANGE" and str(wired_io_mode or "off").lower() != "hdmi_raw16":
            return (
                False,
                {},
                {
                    "ok": False,
                    "error": "avi_shadow_crush_blocked",
                    "message": "Blocked legal-to-full external recorder double-scaling shadow crush (S-Log3 0% black code 95 -> 36, -59 codes)",
                    "shadow_crush_delta_codes": -59,
                },
            )
        updates["recorder_range_expectation"] = rec_exp

    if body.get("force_avi_full_range") is True and str(wired_io_mode or "off").lower() != "hdmi_raw16":
        return (
            False,
            {},
            {
                "ok": False,
                "error": "avi_shadow_crush_blocked",
                "message": "Blocked AVI YQ=FULL mismatch on S-Log3/S-Cinetone YCbCr422 output (prevents shadow crush)",
                "shadow_crush_delta_codes": -59,
            },
        )

    # 5. E-Mount 12-Pin vs Manual PL Hot-Swap Shading Arbitrator
    eff_mount = str((current_state or {}).get("mount_type", "Sony_EMount_12Pin_GM"))
    if "mount_type" in body and body["mount_type"] is not None:
        raw_mt = body["mount_type"]
        if not isinstance(raw_mt, str):
            return False, {}, {"ok": False, "error": "invalid_mount_type", "message": f"Invalid mount_type: {raw_mt!r}"}
        mt_norm = _LENS_MOUNT_ALIASES.get(raw_mt.strip().lower())
        if mt_norm is None:
            return (
                False,
                {},
                {"ok": False, "error": "invalid_mount_type", "message": f"Unsupported mount_type: {raw_mt!r}", "allowed": list(LENS_MOUNT_TYPES)},
            )
        updates["mount_type"] = mt_norm
        eff_mount = mt_norm
        if "lens_model" not in body:
            updates["lens_model"] = (
                "Atlas Orion 40mm 2x PL (Unchipped)"
                if mt_norm == "Manual_PL_Adapter_Unchipped"
                else "SEL2470GM2 (FE 24-70mm F2.8 GM II)"
            )
        if "focal_length_mm" not in body:
            updates["focal_length_mm"] = 40 if mt_norm == "Manual_PL_Adapter_Unchipped" else 24

    if eff_mount == "Manual_PL_Adapter_Unchipped" and body.get("inject_stale_gm_shading") is True:
        return (
            False,
            {},
            {
                "ok": False,
                "error": "stale_gm_shading_blocked_on_pl",
                "message": "Blocked stale 12-pin GM shading/CA/breathing coefficients on Manual_PL_Adapter_Unchipped; 1.0x identity enforced",
            },
        )

    if "lens_model" in body and body["lens_model"] is not None:
        lm = str(body["lens_model"]).strip()
        if not lm or len(lm) > 64:
            return False, {}, {"ok": False, "error": "invalid_lens_model", "message": "lens_model must be 1..64 chars"}
        updates["lens_model"] = lm

    if "lens_kg" in body and body["lens_kg"] is not None:
        raw_kg = body["lens_kg"]
        if isinstance(raw_kg, bool) or not isinstance(raw_kg, (int, float, str)):
            return False, {}, {"ok": False, "error": "invalid_lens_kg", "message": f"Invalid lens_kg: {raw_kg!r}"}
        try:
            f_kg = float(raw_kg)
        except ValueError:
            return False, {}, {"ok": False, "error": "invalid_lens_kg", "message": f"Invalid lens_kg: {raw_kg!r}"}
        if not math.isfinite(f_kg) or f_kg < 0.1 or f_kg > 10.0:
            return False, {}, {"ok": False, "error": "invalid_lens_kg", "message": "lens_kg must be finite in [0.1, 10.0]"}
        updates["lens_kg"] = round(f_kg, 3)

    if "focal_length_mm" in body and body["focal_length_mm"] is not None:
        raw_fl = body["focal_length_mm"]
        if isinstance(raw_fl, bool) or not isinstance(raw_fl, (int, float, str)):
            return False, {}, {"ok": False, "error": "invalid_focal_length_mm", "message": f"Invalid focal_length_mm: {raw_fl!r}"}
        try:
            f_fl = float(raw_fl)
        except ValueError:
            return False, {}, {"ok": False, "error": "invalid_focal_length_mm", "message": f"Invalid focal_length_mm: {raw_fl!r}"}
        if not math.isfinite(f_fl) or f_fl < 10.0 or f_fl > 250.0:
            return False, {}, {"ok": False, "error": "invalid_focal_length_mm", "message": "focal_length_mm must be in [10, 250]"}
        updates["focal_length_mm"] = int(round(f_fl))

    return True, updates, None


# ---------------------------------------------------------------------------
# Phase 116: HLG1/HLG2/HLG3 BT.2100 / ARIB STD-B67, Gamma Display Assist
# Isolation, CTA-861.3 (0x87) HDR InfoFrame, External ProRes RAW / BRAW
# 16->12-bit Log & Focus Breathing Compensation ('HLGA' mb[56..59])
# ---------------------------------------------------------------------------

HLG_PROFILES = ("OFF", "HLG1", "HLG2", "HLG3", "FX6_HLG_LIVE", "FX6_HLG_NATURAL")
_HLG_PROFILE_TO_IDX: dict[str, int] = {
    "OFF": 0,
    "HLG1": 1,
    "HLG2": 2,
    "HLG3": 3,
    "FX6_HLG_LIVE": 4,
    "FX6_HLG_NATURAL": 5,
}
_HLG_PROFILE_ALIASES: dict[str, str] = {
    "off": "OFF",
    "sdr": "OFF",
    "none": "OFF",
    "hlg1": "HLG1",
    "hlg_1": "HLG1",
    "hlg1_87": "HLG1",
    "hlg2": "HLG2",
    "hlg_2": "HLG2",
    "hlg2_95": "HLG2",
    "hlg3": "HLG3",
    "hlg_3": "HLG3",
    "hlg3_100": "HLG3",
    "fx6_hlg_live": "FX6_HLG_LIVE",
    "hlg_live": "FX6_HLG_LIVE",
    "hlg live": "FX6_HLG_LIVE",
    "fx6_hlg_natural": "FX6_HLG_NATURAL",
    "hlg_natural": "FX6_HLG_NATURAL",
    "hlg natural": "FX6_HLG_NATURAL",
}

HLG_PROFILE_SPECS: dict[str, dict[str, Any]] = {
    "OFF": {
        "eotf": "SDR_OR_SLOG",
        "cta_eotf": 0,
        "knee_pct": 100.0,
        "peak_nits": 100,
        "noise_floor_ire": 0.0,
        "dr_stops": 10.0,
        "description": "SDR / Cinema Base Look (HLG bypassed)",
    },
    "HLG1": {
        "eotf": "ARIB_STD_B67_BT2100",
        "cta_eotf": 3,
        "knee_pct": 87.0,
        "peak_nits": 925,
        "noise_floor_ire": 4.2,
        "dr_stops": 11.8,
        "description": "HLG1 (87% ~925 nit low-noise, BT.709 compat)",
    },
    "HLG2": {
        "eotf": "ARIB_STD_B67_BT2100",
        "cta_eotf": 3,
        "knee_pct": 95.0,
        "peak_nits": 1000,
        "noise_floor_ire": 5.0,
        "dr_stops": 12.6,
        "description": "HLG2 (95% ~1000 nit balanced HDR)",
    },
    "HLG3": {
        "eotf": "ARIB_STD_B67_BT2100",
        "cta_eotf": 3,
        "knee_pct": 100.0,
        "peak_nits": 1090,
        "noise_floor_ire": 5.8,
        "dr_stops": 13.4,
        "description": "HLG3 (100% ~1090 nit wide-DR ARIB STD-B67)",
    },
    "FX6_HLG_LIVE": {
        "eotf": "ARIB_STD_B67_BT2100",
        "cta_eotf": 3,
        "knee_pct": 96.0,
        "peak_nits": 1000,
        "noise_floor_ire": 5.0,
        "dr_stops": 12.6,
        "description": "FX6 HLG Live (broadcast BT.2100)",
    },
    "FX6_HLG_NATURAL": {
        "eotf": "ARIB_STD_B67_BT2100",
        "cta_eotf": 3,
        "knee_pct": 100.0,
        "peak_nits": 1090,
        "noise_floor_ire": 5.6,
        "dr_stops": 13.2,
        "description": "FX6 HLG Natural (cinema BT.2100)",
    },
}

HLG_COLOR_GAMUTS = ("BT.709", "BT.2020", "S-Gamut3.Cine")
_HLG_GAMUT_TO_IDX: dict[str, int] = {"BT.709": 0, "BT.2020": 1, "S-Gamut3.Cine": 2}
_HLG_GAMUT_ALIASES: dict[str, str] = {
    "bt.709": "BT.709",
    "bt709": "BT.709",
    "rec709": "BT.709",
    "rec.709": "BT.709",
    "itu709": "BT.709",
    "bt.2020": "BT.2020",
    "bt2020": "BT.2020",
    "rec2020": "BT.2020",
    "rec.2020": "BT.2020",
    "s-gamut3.cine": "S-Gamut3.Cine",
    "sgamut3.cine": "S-Gamut3.Cine",
    "sg3c": "S-Gamut3.Cine",
}

HLG_KNEE_MODES = ("Auto", "87%", "95%", "100%")
_HLG_KNEE_TO_IDX: dict[str, int] = {"Auto": 0, "87%": 1, "95%": 2, "100%": 3}
_HLG_KNEE_ALIASES: dict[str, str] = {
    "auto": "Auto",
    "87": "87%",
    "87%": "87%",
    "95": "95%",
    "95%": "95%",
    "100": "100%",
    "100%": "100%",
}

DISPLAY_ASSIST_MODES = (
    "OFF",
    "AUTO",
    "S-Log3->709(800%)",
    "HLG->709(BT.2020)",
    "HLG->709(709)",
)
_DISPLAY_ASSIST_TO_IDX: dict[str, int] = {
    "OFF": 0,
    "AUTO": 1,
    "S-Log3->709(800%)": 2,
    "HLG->709(BT.2020)": 3,
    "HLG->709(709)": 4,
}
_DISPLAY_ASSIST_ALIASES: dict[str, str] = {
    "off": "OFF",
    "auto": "AUTO",
    "s-log3->709(800%)": "S-Log3->709(800%)",
    "slog3->709(800%)": "S-Log3->709(800%)",
    "slog3_to_709_800pct": "S-Log3->709(800%)",
    "slog3->709": "S-Log3->709(800%)",
    "hlg->709(bt.2020)": "HLG->709(BT.2020)",
    "hlg_bt2020_to_709": "HLG->709(BT.2020)",
    "hlg->709(2020)": "HLG->709(BT.2020)",
    "hlg->709(709)": "HLG->709(709)",
    "hlg_bt709_to_709": "HLG->709(709)",
}

EXT_RAW_OUTPUT_MODES = (
    "OFF",
    "Atomos_ProRes_RAW_16_12L",
    "Blackmagic_BRAW_16_12L",
)
_EXT_RAW_TO_IDX: dict[str, int] = {
    "OFF": 0,
    "Atomos_ProRes_RAW_16_12L": 1,
    "Blackmagic_BRAW_16_12L": 2,
}
_EXT_RAW_ALIASES: dict[str, str] = {
    "off": "OFF",
    "none": "OFF",
    "xavc": "OFF",
    "atomos_prores_raw_16_12l": "Atomos_ProRes_RAW_16_12L",
    "prores_raw": "Atomos_ProRes_RAW_16_12L",
    "prores raw": "Atomos_ProRes_RAW_16_12L",
    "prores": "Atomos_ProRes_RAW_16_12L",
    "atomos": "Atomos_ProRes_RAW_16_12L",
    "blackmagic_braw_16_12l": "Blackmagic_BRAW_16_12L",
    "braw": "Blackmagic_BRAW_16_12L",
    "blackmagic_braw": "Blackmagic_BRAW_16_12L",
}

FOCUS_BREATHING_MODES = ("OFF", "AUTO")
_FOCUS_BREATHING_ALIASES: dict[str, str] = {
    "off": "OFF",
    "0": "OFF",
    "false": "OFF",
    "auto": "AUTO",
    "on": "AUTO",
    "1": "AUTO",
    "true": "AUTO",
}

# CTA-861.3 Dynamic Range and Mastering InfoFrame (0x87)
CTA861_3_HDR_INFOFRAME_TYPE = 0x87
CTA861_3_HDR_INFOFRAME_VERSION = 0x01
CTA861_3_HDR_INFOFRAME_PAYLOAD_LEN = 26
CTA861_3_HDR_INFOFRAME_TOTAL_LEN = 30
_BT2020_CTA_PRIMARIES = ((8500, 39850), (6550, 2300), (35400, 14600))
_BT709_CTA_PRIMARIES = ((15000, 30000), (7500, 3000), (32000, 16500))
_D65_CTA_WHITEPOINT = (15635, 16450)

# E-Mount 12-pin dynamic Focus Breathing Compensation FOV crop lookup (focal_mm ceiling -> crop factor)
FOCUS_BREATHING_EMOUNT_CROP_TABLE: tuple[tuple[int, float], ...] = (
    (20, 1.02),
    (35, 1.04),
    (55, 1.06),
    (85, 1.07),
    (250, 1.08),
)

HDR_HLG_RAW_BREATHING_DEFAULTS: dict[str, Any] = {
    "hlg_profile": "OFF",
    "color_gamut": "BT.709",
    "knee_mode": "Auto",
    "detail_level": 0,
    "display_assist_mode": "OFF",
    "ext_raw_mode": "OFF",
    "breathing_comp_mode": "OFF",
}

HDR_HLG_RAW_BREATHING_SPECS: dict[str, Any] = {
    "hlg_profiles": list(HLG_PROFILES),
    "hlg_profile_specs": HLG_PROFILE_SPECS,
    "color_gamuts": list(HLG_COLOR_GAMUTS),
    "knee_modes": list(HLG_KNEE_MODES),
    "detail_level_range": [-7, 7],
    "display_assist_modes": list(DISPLAY_ASSIST_MODES),
    "ext_raw_modes": list(EXT_RAW_OUTPUT_MODES),
    "breathing_comp_modes": list(FOCUS_BREATHING_MODES),
    "breathing_emount_crop_range": [1.00, 1.08],
    "cta861_3_infoframe_type": "0x87",
    "cta861_3_infoframe_bytes": CTA861_3_HDR_INFOFRAME_TOTAL_LEN,
    "clean_hdmi_sdi_isolation_enforced": True,
    "mailbox_magic": "0x484C4741",
    "mailbox_slots": "mb[56..59]",
    "supported_langs": ["en", "zh-CN", "zh-TW", "ja"],
}


def build_cta861_3_hdr_infoframe(
    *,
    eotf: int = 3,
    use_bt2020_primaries: bool = True,
    max_mastering_nits: int = 1000,
    min_mastering_0001_nits: int = 50,
    max_cll_nits: int = 1000,
    max_fall_nits: int = 400,
) -> dict[str, Any]:
    """Build deterministic 30-byte CTA-861.3 (0x87) HDR Static Metadata InfoFrame with (sum % 256) == 0."""
    eotf_i = int(eotf) & 0xFF
    primaries = _BT2020_CTA_PRIMARIES if use_bt2020_primaries else _BT709_CTA_PRIMARIES
    header = bytes((
        CTA861_3_HDR_INFOFRAME_TYPE,
        CTA861_3_HDR_INFOFRAME_VERSION,
        CTA861_3_HDR_INFOFRAME_PAYLOAD_LEN,
    ))
    payload = struct.pack(
        "<BB12H",
        eotf_i,
        0x00,
        primaries[0][0],
        primaries[0][1],
        primaries[1][0],
        primaries[1][1],
        primaries[2][0],
        primaries[2][1],
        _D65_CTA_WHITEPOINT[0],
        _D65_CTA_WHITEPOINT[1],
        max(0, min(65535, int(max_mastering_nits))),
        max(0, min(65535, int(min_mastering_0001_nits))),
        max(0, min(65535, int(max_cll_nits))),
        max(0, min(65535, int(max_fall_nits))),
    )
    checksum = (0x100 - ((sum(header) + sum(payload)) & 0xFF)) & 0xFF
    packet = header + bytes((checksum,)) + payload
    total_mod256 = sum(packet) & 0xFF
    eotf_labels = {
        0: "SDR_TRADITIONAL_GAMMA",
        1: "HDR_TRADITIONAL_GAMMA",
        2: "SMPTE_ST2084_PQ",
        3: "HLG_ITU_R_BT2100",
    }
    return {
        "packet_bytes": len(packet),
        "packet_hex": packet.hex().upper(),
        "infoframe_type": f"0x{CTA861_3_HDR_INFOFRAME_TYPE:02X}",
        "infoframe_version": CTA861_3_HDR_INFOFRAME_VERSION,
        "payload_length": CTA861_3_HDR_INFOFRAME_PAYLOAD_LEN,
        "checksum_byte": checksum,
        "checksum_hex": f"0x{checksum:02X}",
        "checksum_zero_mod256": total_mod256,
        "checksum_valid": total_mod256 == 0,
        "eotf": eotf_i,
        "eotf_label": eotf_labels.get(eotf_i, f"RESERVED_0x{eotf_i:02X}"),
        "gamut_primaries_standard": "BT.2020" if use_bt2020_primaries else "BT.709",
        "max_mastering_luminance_nits": int(max_mastering_nits),
        "max_cll_nits": int(max_cll_nits),
        "max_fall_nits": int(max_fall_nits),
    }


def _lookup_emount_breathing_crop(focal_length_mm: int) -> float:
    fl = max(10, min(250, int(focal_length_mm)))
    for max_fl, factor in FOCUS_BREATHING_EMOUNT_CROP_TABLE:
        if fl <= max_fl:
            return round(factor, 2)
    return 1.08


def compute_hdr_hlg_raw_breathing_derived(
    state: dict[str, Any],
    *,
    base_look: str = "S-Cinetone",
    cine_ei_base: str = "800",
    kelvin: int = 5600,
    base_fps: float = 23.98,
    wired_io_mode: str = "off",
    mount_type: str = "Sony_EMount_12Pin_GM",
    lens_model: str = "SEL2470GM2 (FE 24-70mm F2.8 GM II)",
    focal_length_mm: int = 24,
    iris_fstop: float = 2.8,
    assist_leak_blocked_count: int = 0,
    bt2020_in_bt709_blocked_count: int = 0,
) -> dict[str, Any]:
    """Compute Phase 116 HLG BT.2100/STD-B67, Display Assist Isolation, ProRes RAW/BRAW & Focus Breathing state."""
    hlg_profile = str(state.get("hlg_profile", "OFF"))
    if hlg_profile not in HLG_PROFILES:
        hlg_profile = "OFF"
    spec = HLG_PROFILE_SPECS[hlg_profile]

    color_gamut = str(state.get("color_gamut", "BT.709"))
    if color_gamut not in HLG_COLOR_GAMUTS:
        color_gamut = "BT.709"

    knee_mode = str(state.get("knee_mode", "Auto"))
    if knee_mode not in HLG_KNEE_MODES:
        knee_mode = "Auto"
    if knee_mode == "Auto":
        eff_knee_pct = float(spec["knee_pct"])
    else:
        eff_knee_pct = float(knee_mode.rstrip("%"))

    detail_level = max(-7, min(7, int(state.get("detail_level", 0))))
    peak_nits = int(spec["peak_nits"])
    cta_eotf = int(spec["cta_eotf"])
    is_hlg = (hlg_profile != "OFF")
    use_bt2020 = (color_gamut == "BT.2020")
    cta = build_cta861_3_hdr_infoframe(
        eotf=cta_eotf,
        use_bt2020_primaries=use_bt2020,
        max_mastering_nits=peak_nits if is_hlg else 100,
        min_mastering_0001_nits=50 if is_hlg else 1000,
        max_cll_nits=peak_nits if is_hlg else 0,
        max_fall_nits=400 if is_hlg else 0,
    )

    assist_req = str(state.get("display_assist_mode", "OFF"))
    if assist_req not in DISPLAY_ASSIST_MODES:
        assist_req = "OFF"
    look_l = str(base_look or "").lower()
    if assist_req == "AUTO":
        if is_hlg:
            assist_resolved = "HLG->709(BT.2020)" if color_gamut == "BT.2020" else "HLG->709(709)"
        elif "s-log3" in look_l or "slog3" in look_l:
            assist_resolved = "S-Log3->709(800%)"
        else:
            assist_resolved = "OFF"
    else:
        assist_resolved = assist_req
    evf_lcd_assist_active = (assist_resolved != "OFF")

    ext_raw_mode = str(state.get("ext_raw_mode", "OFF"))
    if ext_raw_mode not in EXT_RAW_OUTPUT_MODES:
        ext_raw_mode = "OFF"
    raw_active = (ext_raw_mode != "OFF")
    hdmi_raw_any = raw_active or (str(wired_io_mode or "off").lower() == "hdmi_raw16")

    raw_base_iso = 12800 if str(cine_ei_base) == "12800" else 800
    raw_kelvin = max(2000, min(15000, int(kelvin)))
    is_pl = (str(mount_type) == "Manual_PL_Adapter_Unchipped")
    e_pins = 0 if is_pl else 12
    focal_mm = max(10, min(250, int(focal_length_mm)))

    breath_req = str(state.get("breathing_comp_mode", "OFF"))
    if breath_req not in FOCUS_BREATHING_MODES:
        breath_req = "OFF"
    bypass_pl = bool(breath_req == "AUTO" and is_pl)
    bypass_raw = bool(breath_req == "AUTO" and hdmi_raw_any)
    if breath_req == "AUTO" and not bypass_pl and not bypass_raw:
        breath_eff = True
        crop_factor = _lookup_emount_breathing_crop(focal_mm)
        bypass_reason = "NONE_EMOUNT_12PIN_ACTIVE"
    else:
        breath_eff = False
        crop_factor = 1.00
        if bypass_pl and bypass_raw:
            bypass_reason = "PL_UNCHIPPED_AND_HDMI_RAW"
        elif bypass_pl:
            bypass_reason = "PL_UNCHIPPED_0PIN_IDENTITY"
        elif bypass_raw:
            bypass_reason = "HDMI_RAW_FULL_SENSOR_NO_CROP"
        else:
            bypass_reason = "USER_OFF"

    if is_hlg:
        cap_gamma = "rec2100-hlg"
    elif "s-log3" in look_l or "slog3" in look_l:
        cap_gamma = "s-log3"
    elif "cinetone" in look_l:
        cap_gamma = "s-cinetone"
    else:
        cap_gamma = "rec709"
    cap_primaries = "rec2020" if color_gamut == "BT.2020" else ("s-gamut3.cine" if color_gamut == "S-Gamut3.Cine" else "rec709")

    if raw_active:
        vendor = "Atomos_Ninja" if ext_raw_mode == "Atomos_ProRes_RAW_16_12L" else "Blackmagic_VideoAssist"
        raw_summary = f"{vendor} 16->12L Base{raw_base_iso} {raw_kelvin}K {focal_mm}mm {'E12P' if not is_pl else 'PL0P'}"
    else:
        raw_summary = "Internal XAVC (Ext RAW OFF)"

    waveform_peak_ire = int(round(eff_knee_pct)) if is_hlg else 41

    return {
        "hlg_profile": hlg_profile,
        "hlg_eotf": spec["eotf"],
        "hlg_description": spec["description"],
        "color_gamut": color_gamut,
        "knee_mode": knee_mode,
        "knee_pct": eff_knee_pct,
        "peak_nits": peak_nits,
        "noise_floor_ire": float(spec["noise_floor_ire"]),
        "dynamic_range_stops": float(spec["dr_stops"]),
        "detail_level": detail_level,
        "capture_gamma_equation": cap_gamma,
        "capture_color_primaries": cap_primaries,
        "cicp_color_primaries": 9 if color_gamut == "BT.2020" else 1,
        "cicp_transfer_characteristics": 18 if is_hlg else 1,
        "cicp_matrix_coefficients": 9 if color_gamut == "BT.2020" else 1,
        "cta_infoframe_type": cta["infoframe_type"],
        "cta_infoframe_bytes": cta["packet_bytes"],
        "cta_infoframe_hex": cta["packet_hex"],
        "cta_checksum_byte": cta["checksum_byte"],
        "cta_checksum_hex": cta["checksum_hex"],
        "cta_checksum_zero_mod256": cta["checksum_zero_mod256"],
        "cta_checksum_valid": cta["checksum_valid"],
        "cta_eotf": cta["eotf"],
        "cta_eotf_label": cta["eotf_label"],
        "cta_gamut_primaries_standard": cta["gamut_primaries_standard"],
        "display_assist_mode": assist_req,
        "resolved_assist_mode": assist_resolved,
        "evf_lcd_assist_active": evf_lcd_assist_active,
        "vf_nit_ceiling": 100,
        "waveform_peak_ire": waveform_peak_ire,
        "clean_hdmi_sdi_unassisted": True,
        "xavc_internal_unassisted": True,
        "external_output_assist_leak_px": 0,
        "assist_leak_blocked_count": int(assist_leak_blocked_count),
        "bt2020_in_bt709_blocked_count": int(bt2020_in_bt709_blocked_count),
        "ext_raw_mode": ext_raw_mode,
        "ext_raw_active": raw_active,
        "raw_bit_depth_in": 16 if raw_active else 10,
        "raw_bit_depth_packed": 12 if raw_active else 10,
        "raw_transfer_curve": "16bit_Linear_to_12bit_Log_Packing" if raw_active else "XAVC_Normal",
        "raw_base_iso": raw_base_iso,
        "raw_kelvin": raw_kelvin,
        "raw_fps": float(base_fps),
        "raw_lens_metadata": {
            "mount_type": mount_type,
            "lens_model": lens_model,
            "focal_length_mm": focal_mm,
            "iris_fstop": round(float(iris_fstop), 1),
            "electronic_pins": e_pins,
            "attached": not is_pl,
        },
        "raw_hdmi_packet_summary": raw_summary,
        "breathing_comp_mode": breath_req,
        "breathing_effective_active": breath_eff,
        "breathing_crop_factor": crop_factor,
        "breathing_bypassed_by_pl_mount": bypass_pl,
        "breathing_bypassed_by_raw": bypass_raw,
        "breathing_bypass_reason": bypass_reason,
        "persistent_emmc_writes_authorized": False,
    }


def format_hdr_hlg_raw_breathing_command(state: dict[str, Any]) -> str:
    """Format deterministic Phase 116 HLGA host<->guest protocol telemetry line."""
    return (
        f"HLGA hlg={state['hlg_profile']}({state['color_gamut']},{state['peak_nits']}nit,kn={state['knee_pct']:.0f}%,det={state['detail_level']:+d}) "
        f"cta87=(eotf={state['cta_eotf']},cs={state['cta_checksum_hex']},ok=1) "
        f"assist={state['resolved_assist_mode']}(clean_out=1,leak=0,blk={state['assist_leak_blocked_count']}) "
        f"raw={state['ext_raw_mode']}(16->12L,B{state['raw_base_iso']},{state['raw_kelvin']}K) "
        f"fbc={state['breathing_comp_mode']}->{'ON' if state['breathing_effective_active'] else 'BYP'}({state['breathing_crop_factor']:.2f}x)"
    )


def validate_hdr_hlg_raw_breathing_patch(
    body: Any,
    current_state: dict[str, Any] | None = None,
    *,
    mount_type: str = "Sony_EMount_12Pin_GM",
    wired_io_mode: str = "off",
) -> tuple[bool, dict[str, Any], dict[str, Any] | None]:
    """Validate and normalize Phase 116 HLG BT.2100, Display Assist, External RAW & Focus Breathing updates fail-closed."""
    if not isinstance(body, dict):
        return False, {}, {"ok": False, "error": "invalid_hdr_hlg_raw_breathing", "message": "Payload must be a JSON object"}

    updates: dict[str, Any] = {}
    if body.get("reset") is True:
        updates.update(HDR_HLG_RAW_BREATHING_DEFAULTS)

    # 1. Clean HDMI/SDI Display Assist isolation guard (fail-closed)
    if (
        body.get("apply_assist_to_hdmi") is True
        or body.get("apply_assist_to_sdi") is True
        or body.get("bake_assist_into_hdmi") is True
        or body.get("bake_assist_into_xavc") is True
        or body.get("clean_hdmi_sdi_unassisted") is False
        or body.get("xavc_internal_unassisted") is False
    ):
        return (
            False,
            {},
            {
                "ok": False,
                "error": "display_assist_clean_feed_leak_blocked",
                "message": "Gamma Display Assist is strictly isolated to EVF/LCD; Clean HDMI/SDI & internal XAVC burn-in blocked",
                "clean_hdmi_sdi_unassisted": True,
                "xavc_internal_unassisted": True,
                "external_output_assist_leak_px": 0,
            },
        )

    # 2. Focus Breathing interlock guard (cannot force crop on PL unchipped or HDMI RAW)
    cur_raw = str((current_state or {}).get("ext_raw_mode", "OFF"))
    if body.get("force_breathing_on_pl") is True:
        return (
            False,
            {},
            {
                "ok": False,
                "error": "focus_breathing_interlock_blocked",
                "message": "Manual PL unchipped lens has 0 E-Mount pins; Focus Breathing Compensation enforces 1.00x bypass",
                "breathing_crop_factor": 1.00,
            },
        )
    if body.get("force_breathing_in_raw") is True:
        return (
            False,
            {},
            {
                "ok": False,
                "error": "focus_breathing_interlock_blocked",
                "message": "External HDMI 16->12-bit RAW output requires full-sensor readout; Focus Breathing Compensation enforces 1.00x bypass",
                "breathing_crop_factor": 1.00,
            },
        )

    # 3. HLG profile
    eff_hlg = str((current_state or {}).get("hlg_profile", "OFF"))
    if "hlg_profile" in body and body["hlg_profile"] is not None:
        raw_hp = body["hlg_profile"]
        if not isinstance(raw_hp, str):
            return False, {}, {"ok": False, "error": "invalid_hlg_profile", "message": f"Invalid hlg_profile: {raw_hp!r}"}
        hp_norm = _HLG_PROFILE_ALIASES.get(raw_hp.strip().lower())
        if hp_norm is None:
            return (
                False,
                {},
                {"ok": False, "error": "invalid_hlg_profile", "message": f"Unsupported hlg_profile: {raw_hp!r}", "allowed": list(HLG_PROFILES)},
            )
        updates["hlg_profile"] = hp_norm
        eff_hlg = hp_norm
        if "color_gamut" not in body:
            if hp_norm != "OFF" and str((current_state or {}).get("color_gamut", "BT.709")) == "BT.709":
                updates["color_gamut"] = "BT.2020"
            elif hp_norm == "OFF" and str((current_state or {}).get("color_gamut", "BT.709")) == "BT.2020":
                updates["color_gamut"] = "BT.709"

    # 4. Color Gamut & BT.2020-in-BT.709 container guard
    eff_gamut = str(updates.get("color_gamut", (current_state or {}).get("color_gamut", "BT.709")))
    if "color_gamut" in body and body["color_gamut"] is not None:
        raw_cg = body["color_gamut"]
        if not isinstance(raw_cg, str):
            return False, {}, {"ok": False, "error": "invalid_color_gamut", "message": f"Invalid color_gamut: {raw_cg!r}"}
        cg_norm = _HLG_GAMUT_ALIASES.get(raw_cg.strip().lower())
        if cg_norm is None:
            return (
                False,
                {},
                {"ok": False, "error": "invalid_color_gamut", "message": f"Unsupported color_gamut: {raw_cg!r}", "allowed": list(HLG_COLOR_GAMUTS)},
            )
        updates["color_gamut"] = cg_norm
        eff_gamut = cg_norm

    container_tag = str(body.get("container_colorimetry") or "").strip().upper()
    if (body.get("force_bt2020_in_bt709") is True) or (
        eff_gamut == "BT.2020" and container_tag in ("BT709", "BT.709", "REC709")
    ):
        return (
            False,
            {},
            {
                "ok": False,
                "error": "bt2020_in_bt709_container_blocked",
                "message": "Blocked mismatched BT.2020 signal packaged inside BT.709 container tags (CICP 9/18/9 required)",
            },
        )

    # 5. Knee & Detail Level
    if "knee_mode" in body and body["knee_mode"] is not None:
        raw_km = body["knee_mode"]
        if not isinstance(raw_km, str):
            return False, {}, {"ok": False, "error": "invalid_knee_mode", "message": f"Invalid knee_mode: {raw_km!r}"}
        km_norm = _HLG_KNEE_ALIASES.get(raw_km.strip().lower())
        if km_norm is None:
            return (
                False,
                {},
                {"ok": False, "error": "invalid_knee_mode", "message": f"Unsupported knee_mode: {raw_km!r}", "allowed": list(HLG_KNEE_MODES)},
            )
        updates["knee_mode"] = km_norm

    if "detail_level" in body and body["detail_level"] is not None:
        raw_dl = body["detail_level"]
        if isinstance(raw_dl, bool) or not isinstance(raw_dl, (int, float, str)):
            return False, {}, {"ok": False, "error": "invalid_detail_level", "message": f"Invalid detail_level: {raw_dl!r}"}
        try:
            f_dl = float(raw_dl)
        except ValueError:
            return False, {}, {"ok": False, "error": "invalid_detail_level", "message": f"Invalid detail_level: {raw_dl!r}"}
        if not math.isfinite(f_dl) or f_dl != float(int(f_dl)) or int(f_dl) < -7 or int(f_dl) > 7:
            return False, {}, {"ok": False, "error": "invalid_detail_level", "message": "detail_level must be integer in [-7, +7]"}
        updates["detail_level"] = int(f_dl)

    # 6. Gamma Display Assist mode
    if "display_assist_mode" in body and body["display_assist_mode"] is not None:
        raw_da = body["display_assist_mode"]
        if not isinstance(raw_da, str):
            return False, {}, {"ok": False, "error": "invalid_display_assist_mode", "message": f"Invalid display_assist_mode: {raw_da!r}"}
        da_norm = _DISPLAY_ASSIST_ALIASES.get(raw_da.strip().lower())
        if da_norm is None:
            return (
                False,
                {},
                {"ok": False, "error": "invalid_display_assist_mode", "message": f"Unsupported display_assist_mode: {raw_da!r}", "allowed": list(DISPLAY_ASSIST_MODES)},
            )
        updates["display_assist_mode"] = da_norm

    # 7. External HDMI RAW mode
    if "ext_raw_mode" in body and body["ext_raw_mode"] is not None:
        raw_em = body["ext_raw_mode"]
        if not isinstance(raw_em, str):
            return False, {}, {"ok": False, "error": "invalid_ext_raw_mode", "message": f"Invalid ext_raw_mode: {raw_em!r}"}
        em_norm = _EXT_RAW_ALIASES.get(raw_em.strip().lower())
        if em_norm is None:
            return (
                False,
                {},
                {"ok": False, "error": "invalid_ext_raw_mode", "message": f"Unsupported ext_raw_mode: {raw_em!r}", "allowed": list(EXT_RAW_OUTPUT_MODES)},
            )
        updates["ext_raw_mode"] = em_norm

    # 8. Focus Breathing Compensation mode
    if "breathing_comp_mode" in body and body["breathing_comp_mode"] is not None:
        raw_bm = body["breathing_comp_mode"]
        if isinstance(raw_bm, bool):
            bm_norm = "AUTO" if raw_bm else "OFF"
        elif isinstance(raw_bm, str):
            bm_norm = _FOCUS_BREATHING_ALIASES.get(raw_bm.strip().lower())
        else:
            bm_norm = None
        if bm_norm is None:
            return (
                False,
                {},
                {"ok": False, "error": "invalid_breathing_comp_mode", "message": f"Unsupported breathing_comp_mode: {raw_bm!r}", "allowed": list(FOCUS_BREATHING_MODES)},
            )
        updates["breathing_comp_mode"] = bm_norm

    return True, updates, None


# ---------------------------------------------------------------------------
# Phase 123: Live USB-C UVC 1.5 / UAC 2.0 Streaming, Wired P12-Safe SRT /
# RTMPS TLS 1.3 Streaming (AES-128/256, ARQ), & CRSDK PTP / PTP-IP (0x054C)
# Remote Control + Destructive Flash-Opcode Firewall ('UVCS' mb[60..63])
# ---------------------------------------------------------------------------

UVC_STREAM_MODES: tuple[str, ...] = (
    "OFF",
    "UVC_4K30P_MJPEG_5G",
    "UVC_1080P60P_YUY2_5G",
    "UVC_720P30P_MJPEG_USB2_FALLBACK",
)
_UVC_MODE_TO_IDX: dict[str, int] = {m: i for i, m in enumerate(UVC_STREAM_MODES)}
_UVC_MODE_ALIASES: dict[str, str] = {
    "off": "OFF",
    "none": "OFF",
    "uvc_4k30p_mjpeg_5g": "UVC_4K30P_MJPEG_5G",
    "4k30p": "UVC_4K30P_MJPEG_5G",
    "4k30": "UVC_4K30P_MJPEG_5G",
    "4k_mjpeg": "UVC_4K30P_MJPEG_5G",
    "uvc_1080p60p_yuy2_5g": "UVC_1080P60P_YUY2_5G",
    "1080p60": "UVC_1080P60P_YUY2_5G",
    "1080p60p": "UVC_1080P60P_YUY2_5G",
    "fhd60_yuy2": "UVC_1080P60P_YUY2_5G",
    "uvc_720p30p_mjpeg_usb2_fallback": "UVC_720P30P_MJPEG_USB2_FALLBACK",
    "720p30": "UVC_720P30P_MJPEG_USB2_FALLBACK",
    "usb2_fallback": "UVC_720P30P_MJPEG_USB2_FALLBACK",
}
UVC_MODE_SPECS: dict[str, dict[str, Any]] = {
    "OFF": {"resolution": "0x0", "fps": 0, "codec": "NONE", "bitrate_mbps": 0, "min_usb_speed": "USB2_480M"},
    "UVC_4K30P_MJPEG_5G": {"resolution": "3840x2160", "fps": 30, "codec": "MJPEG", "bitrate_mbps": 250, "min_usb_speed": "USB3_5G"},
    "UVC_1080P60P_YUY2_5G": {"resolution": "1920x1080", "fps": 60, "codec": "YUY2", "bitrate_mbps": 400, "min_usb_speed": "USB3_5G"},
    "UVC_720P30P_MJPEG_USB2_FALLBACK": {"resolution": "1280x720", "fps": 30, "codec": "MJPEG", "bitrate_mbps": 35, "min_usb_speed": "USB2_480M"},
}

USB_LINK_SPEEDS: tuple[str, ...] = ("USB3_5G", "USB2_480M")
_USB_LINK_ALIASES: dict[str, str] = {
    "usb3_5g": "USB3_5G",
    "usb3": "USB3_5G",
    "5g": "USB3_5G",
    "5gbps": "USB3_5G",
    "superspeed": "USB3_5G",
    "usb2_480m": "USB2_480M",
    "usb2": "USB2_480M",
    "480m": "USB2_480M",
    "480mbps": "USB2_480M",
    "highspeed": "USB2_480M",
    "non_superspeed": "USB2_480M",
}

SRT_MODES: tuple[str, ...] = ("OFF", "SRT_CALLER", "SRT_LISTENER")
_SRT_MODE_TO_IDX: dict[str, int] = {m: i for i, m in enumerate(SRT_MODES)}
_SRT_MODE_ALIASES: dict[str, str] = {
    "off": "OFF",
    "none": "OFF",
    "srt_caller": "SRT_CALLER",
    "caller": "SRT_CALLER",
    "srt_listener": "SRT_LISTENER",
    "listener": "SRT_LISTENER",
}

SRT_PBKEYLEN_MODES: tuple[str, ...] = ("NONE", "AES-128", "AES-256")
_SRT_PBKEY_TO_IDX: dict[str, int] = {m: i for i, m in enumerate(SRT_PBKEYLEN_MODES)}
_SRT_PBKEY_ALIASES: dict[str, str] = {
    "none": "NONE",
    "0": "NONE",
    "aes-128": "AES-128",
    "aes128": "AES-128",
    "16": "AES-128",
    "aes-256": "AES-256",
    "aes256": "AES-256",
    "32": "AES-256",
}
SRT_PBKEYLEN_BYTES: dict[str, int] = {"NONE": 0, "AES-128": 16, "AES-256": 32}
SRT_LATENCY_MIN_MS = 20
SRT_LATENCY_MAX_MS = 1000

RTMPS_MODES: tuple[str, ...] = ("OFF", "RTMPS_TLS13")
_RTMPS_ALIASES: dict[str, str] = {
    "off": "OFF",
    "none": "OFF",
    "rtmps_tls13": "RTMPS_TLS13",
    "rtmps": "RTMPS_TLS13",
    "tls13": "RTMPS_TLS13",
    "tls1.3": "RTMPS_TLS13",
}

CRSDK_PTP_MODES: tuple[str, ...] = ("OFF", "USB_PTP", "WIRED_PTPIP")
_CRSDK_PTP_TO_IDX: dict[str, int] = {m: i for i, m in enumerate(CRSDK_PTP_MODES)}
_CRSDK_PTP_ALIASES: dict[str, str] = {
    "off": "OFF",
    "none": "OFF",
    "usb_ptp": "USB_PTP",
    "usb": "USB_PTP",
    "ptp": "USB_PTP",
    "wired_ptpip": "WIRED_PTPIP",
    "ptpip": "WIRED_PTPIP",
    "ptp-ip": "WIRED_PTPIP",
}

CRSDK_USB_VID = "0x054C"
CRSDK_PTPIP_TCP_PORT = 15740
PTP_FLASH_OPCODE_MIN = 0x9280
PTP_FLASH_OPCODE_MAX = 0x92FF
CRSDK_SAFE_D2XX_OPCODES: dict[int, str] = {
    0xD20D: "ShutterSpeed_Angle",
    0xD210: "ExposureIndex_BaseISO",
    0xD21C: "WhiteBalance_ColorTemp",
    0xD220: "BaseLook_UserLut",
    0xD224: "ND_Filter_P4_Clamp",
    0xD2C1: "AF_TouchFocus_XY",
    0xD2C4: "RecTrigger_StartStop",
}

UVC_SRT_CRSDK_PTP_DEFAULTS: dict[str, Any] = {
    "uvc_mode": "OFF",
    "usb_link_speed": "USB3_5G",
    "uac_audio_enabled": True,
    "srt_mode": "OFF",
    "srt_pbkeylen": "AES-256",
    "srt_latency_ms": 120,
    "rtmps_mode": "OFF",
    "stream_bitrate_mbps": 12,
    "crsdk_ptp_mode": "OFF",
}

UVC_SRT_CRSDK_PTP_SPECS: dict[str, Any] = {
    "uvc_modes": list(UVC_STREAM_MODES),
    "uvc_mode_specs": UVC_MODE_SPECS,
    "usb_link_speeds": list(USB_LINK_SPEEDS),
    "uac_audio_spec": "48kHz_16bit_2ch_PCM",
    "uvc_clean_feed_enforced": True,
    "srt_modes": list(SRT_MODES),
    "srt_pbkeylen_modes": list(SRT_PBKEYLEN_MODES),
    "srt_latency_range_ms": [SRT_LATENCY_MIN_MS, SRT_LATENCY_MAX_MS],
    "rtmps_modes": list(RTMPS_MODES),
    "stream_bitrate_range_mbps": [1, 50],
    "stream_transport": "CDC_NCM_WIRED_ETHERNET",
    "p12_wlan_off_enforced": True,
    "crsdk_ptp_modes": list(CRSDK_PTP_MODES),
    "crsdk_usb_vid": CRSDK_USB_VID,
    "crsdk_ptpip_tcp_port": CRSDK_PTPIP_TCP_PORT,
    "crsdk_safe_d2xx_opcodes": {f"0x{k:04X}": v for k, v in CRSDK_SAFE_D2XX_OPCODES.items()},
    "ptp_flash_firewall_range": ["0x9280", "0x92FF"],
    "mailbox_magic": "0x55564353",
    "mailbox_slots": "mb[60..63]",
    "supported_langs": ["en", "zh-CN", "zh-TW", "ja"],
}


def _parse_ptp_opcode(raw_val: Any) -> int | None:
    if isinstance(raw_val, bool):
        return None
    if isinstance(raw_val, int):
        return raw_val if 0 <= raw_val <= 0xFFFF else None
    if isinstance(raw_val, str):
        s = raw_val.strip().lower()
        if not s:
            return None
        try:
            v = int(s, 16) if s.startswith("0x") else int(s, 10)
            return v if 0 <= v <= 0xFFFF else None
        except ValueError:
            return None
    return None


def compute_uvc_srt_crsdk_ptp_derived(
    state: dict[str, Any],
    *,
    cine_ei_base: str = "800",
    ei_index: int = 800,
    base_look: str = "S-Cinetone",
    nd_preset: str = "Clear [FX3 P4 Locked]",
    last_safe_opcode: int = 0xD210,
    safe_cmd_count: int = 0,
    flash_blocked_count: int = 0,
    last_blocked_opcode: str | None = None,
    p12_blocked_count: int = 0,
    uvc_osd_blocked_count: int = 0,
    crsdk_nd_clamp_count: int = 0,
    wf12_00342260_hits: int = 0,
) -> dict[str, Any]:
    """Compute Phase 123 UVC 1.5/UAC 2.0, Wired SRT/RTMPS, & CRSDK PTP Firewall derived state."""
    uvc_mode = str(state.get("uvc_mode", "OFF"))
    if uvc_mode not in UVC_STREAM_MODES:
        uvc_mode = "OFF"
    usb_link_speed = str(state.get("usb_link_speed", "USB3_5G"))
    if usb_link_speed not in USB_LINK_SPEEDS:
        usb_link_speed = "USB3_5G"
    uac_audio_enabled = bool(state.get("uac_audio_enabled", True))

    if usb_link_speed == "USB2_480M" and uvc_mode in ("UVC_4K30P_MJPEG_5G", "UVC_1080P60P_YUY2_5G"):
        effective_uvc_mode = "UVC_720P30P_MJPEG_USB2_FALLBACK"
        uvc_usb2_stepdown_active = True
        uvc_stepdown_reason = "NON_SUPERSPEED_USB2_480MBPS_STEPDOWN"
    else:
        effective_uvc_mode = uvc_mode
        uvc_usb2_stepdown_active = False
        uvc_stepdown_reason = "NONE"

    uvc_spec = UVC_MODE_SPECS[effective_uvc_mode]

    srt_mode = str(state.get("srt_mode", "OFF"))
    if srt_mode not in SRT_MODES:
        srt_mode = "OFF"
    srt_pbkeylen = str(state.get("srt_pbkeylen", "AES-256"))
    if srt_pbkeylen not in SRT_PBKEYLEN_MODES:
        srt_pbkeylen = "AES-256"
    srt_latency_ms = max(SRT_LATENCY_MIN_MS, min(SRT_LATENCY_MAX_MS, int(state.get("srt_latency_ms", 120))))
    rtmps_mode = str(state.get("rtmps_mode", "OFF"))
    if rtmps_mode not in RTMPS_MODES:
        rtmps_mode = "OFF"
    stream_bitrate_mbps = max(1, min(50, int(state.get("stream_bitrate_mbps", 12))))

    crsdk_ptp_mode = str(state.get("crsdk_ptp_mode", "OFF"))
    if crsdk_ptp_mode not in CRSDK_PTP_MODES:
        crsdk_ptp_mode = "OFF"

    safe_op_i = int(last_safe_opcode) if int(last_safe_opcode) in CRSDK_SAFE_D2XX_OPCODES else 0xD210

    return {
        "uvc_mode": uvc_mode,
        "effective_uvc_mode": effective_uvc_mode,
        "usb_link_speed": usb_link_speed,
        "uvc_usb2_stepdown_active": uvc_usb2_stepdown_active,
        "uvc_stepdown_reason": uvc_stepdown_reason,
        "uvc_resolution": uvc_spec["resolution"],
        "uvc_fps": int(uvc_spec["fps"]),
        "uvc_codec": uvc_spec["codec"],
        "uvc_bitrate_mbps": int(uvc_spec["bitrate_mbps"]),
        "uac_audio_enabled": uac_audio_enabled,
        "uac_audio_spec": "48kHz_16bit_2ch_PCM" if uac_audio_enabled else "OFF",
        "uac_sample_rate_hz": 48000 if uac_audio_enabled else 0,
        "uac_bit_depth": 16 if uac_audio_enabled else 0,
        "uac_channels": 2 if uac_audio_enabled else 0,
        "uvc_clean_feed_no_osd": True,
        "uvc_osd_burnin_px": 0,
        "uvc_osd_blocked_count": int(uvc_osd_blocked_count),
        "srt_mode": srt_mode,
        "srt_pbkeylen": srt_pbkeylen,
        "srt_pbkeylen_bytes": SRT_PBKEYLEN_BYTES[srt_pbkeylen],
        "srt_latency_ms": srt_latency_ms,
        "srt_arq_enabled": srt_mode != "OFF",
        "rtmps_mode": rtmps_mode,
        "rtmps_tls_version": "TLS_1_3" if rtmps_mode != "OFF" else "NONE",
        "stream_bitrate_mbps": stream_bitrate_mbps,
        "stream_transport": "CDC_NCM_WIRED_ETHERNET",
        "p12_wlan_off": True,
        "wf12_00342260_hits": int(wf12_00342260_hits),
        "p12_blocked_count": int(p12_blocked_count),
        "crsdk_ptp_mode": crsdk_ptp_mode,
        "crsdk_usb_vid": CRSDK_USB_VID,
        "crsdk_ptpip_tcp_port": CRSDK_PTPIP_TCP_PORT,
        "crsdk_last_safe_opcode": f"0x{safe_op_i:04X}",
        "crsdk_last_safe_prop": CRSDK_SAFE_D2XX_OPCODES[safe_op_i],
        "crsdk_safe_cmd_count": int(safe_cmd_count),
        "crsdk_cine_ei_base": str(cine_ei_base),
        "crsdk_ei_index": int(ei_index),
        "crsdk_base_look": str(base_look),
        "crsdk_nd_preset": str(nd_preset),
        "p4_nd_clear_enforced": True,
        "crsdk_nd_clamp_count": int(crsdk_nd_clamp_count),
        "ptp_flash_opcodes_blocked": True,
        "emmc_mutation_bytes": 0,
        "blocked_flash_opcode_count": int(flash_blocked_count),
        "last_blocked_flash_opcode": last_blocked_opcode,
        "persistent_emmc_writes_authorized": False,
    }


def format_uvc_srt_crsdk_ptp_command(state: dict[str, Any]) -> str:
    """Format deterministic Phase 123 UVCS host<->guest protocol telemetry line."""
    return (
        f"UVCS uvc={state['effective_uvc_mode']}({state['usb_link_speed']},step={int(state['uvc_usb2_stepdown_active'])},uac={state['uac_audio_spec']},cln=1) "
        f"srt={state['srt_mode']}({state['srt_pbkeylen']},arq={state['srt_latency_ms']}ms) "
        f"rtmps={state['rtmps_mode']}@{state['stream_bitrate_mbps']}M(p12_wlan_off=1,wf12={state['wf12_00342260_hits']}) "
        f"ptp={state['crsdk_ptp_mode']}({state['crsdk_usb_vid']},{state['crsdk_last_safe_opcode']},flash_blk=1,emmc=0,blk={state['blocked_flash_opcode_count']})"
    )


def validate_uvc_srt_crsdk_ptp_patch(
    body: Any,
    current_state: dict[str, Any] | None = None,
) -> tuple[bool, dict[str, Any], dict[str, Any] | None]:
    """Validate and normalize Phase 123 UVC/UAC, Wired SRT/RTMPS & CRSDK PTP Firewall updates fail-closed."""
    if not isinstance(body, dict):
        return False, {}, {"ok": False, "error": "invalid_uvc_srt_crsdk_ptp", "message": "Payload must be a JSON object"}

    updates: dict[str, Any] = {}
    if body.get("reset") is True:
        updates.update(UVC_SRT_CRSDK_PTP_DEFAULTS)

    # 1. Fail-closed P12 Wi-Fi/BT RF-OFF guard
    iface = str(body.get("stream_interface") or body.get("network_interface") or "").strip().lower()
    if (
        body.get("use_wifi") is True
        or body.get("enable_wlan") is True
        or body.get("enable_wifi") is True
        or body.get("enable_bt") is True
        or body.get("p12_wlan_off") is False
        or iface in ("wifi", "wlan", "wlan0", "bt", "bluetooth", "ap", "sta")
    ):
        return (
            False,
            {},
            {
                "ok": False,
                "error": "p12_wlan_off_enforced",
                "message": "P12 Airplane-Mode Shadow Lock enforced: Wi-Fi/BT disabled (wf12_00342260_hits=0); use wired CDC-NCM only",
                "p12_wlan_off": True,
                "wf12_00342260_hits": 0,
            },
        )

    # 2. Fail-closed UVC Clean Feed without OSD burn-in guard
    if (
        body.get("uvc_bake_osd") is True
        or body.get("bake_osd_into_uvc") is True
        or body.get("uvc_clean_feed_no_osd") is False
    ):
        return (
            False,
            {},
            {
                "ok": False,
                "error": "uvc_osd_burnin_blocked",
                "message": "UVC 1.5 output is locked to clean feed without OSD burn-in",
                "uvc_clean_feed_no_osd": True,
                "uvc_osd_burnin_px": 0,
            },
        )

    # 3. Fail-closed Destructive PTP Flash-Opcode Firewall (0x9280..0x92FF & firmware flash tokens)
    raw_op = body.get("ptp_opcode", body.get("crsdk_opcode"))
    parsed_op: int | None = None
    if raw_op is not None and str(raw_op).strip() != "":
        parsed_op = _parse_ptp_opcode(raw_op)
        if parsed_op is None:
            return False, {}, {"ok": False, "error": "invalid_ptp_opcode", "message": f"Invalid PTP opcode: {raw_op!r}"}
        if (PTP_FLASH_OPCODE_MIN <= parsed_op <= PTP_FLASH_OPCODE_MAX) or (0x9201 <= parsed_op <= 0x920F):
            return (
                False,
                {},
                {
                    "ok": False,
                    "error": "ptp_flash_opcode_blocked",
                    "blocked_opcode": f"0x{parsed_op:04X}",
                    "message": f"Destructive CRSDK PTP flash opcode 0x{parsed_op:04X} (0x9280..0x92FF) blocked by hardware firewall",
                    "ptp_flash_opcodes_blocked": True,
                    "emmc_mutation_bytes": 0,
                },
            )
        if parsed_op not in CRSDK_SAFE_D2XX_OPCODES:
            return (
                False,
                {},
                {
                    "ok": False,
                    "error": "unsupported_ptp_opcode",
                    "opcode": f"0x{parsed_op:04X}",
                    "message": f"PTP opcode 0x{parsed_op:04X} not in safe 0xD2xx allowlist",
                    "allowed_opcodes": [f"0x{k:04X}" for k in CRSDK_SAFE_D2XX_OPCODES],
                },
            )
        updates["crsdk_safe_opcode"] = parsed_op

    action_str = str(body.get("crsdk_action") or "").strip().lower()
    if (
        body.get("firmware_flash") is True
        or body.get("emmc_write") is True
        or body.get("nvram_tamper") is True
        or any(tok in action_str for tok in ("flash", "firmware", "ufu", "emmc", "nvram", "erase", "format_nand"))
    ):
        return (
            False,
            {},
            {
                "ok": False,
                "error": "ptp_flash_opcode_blocked",
                "blocked_opcode": "0x9280",
                "message": "Destructive firmware/eMMC flash operation blocked by CRSDK PTP firewall",
                "ptp_flash_opcodes_blocked": True,
                "emmc_mutation_bytes": 0,
            },
        )

    # 4. UVC 1.5 / USB Link Speed / UAC 2.0
    if "uvc_mode" in body and body["uvc_mode"] is not None:
        raw_uvc = body["uvc_mode"]
        if not isinstance(raw_uvc, str):
            return False, {}, {"ok": False, "error": "invalid_uvc_mode", "message": f"Invalid uvc_mode: {raw_uvc!r}"}
        uvc_norm = _UVC_MODE_ALIASES.get(raw_uvc.strip().lower())
        if uvc_norm is None:
            return (
                False,
                {},
                {"ok": False, "error": "invalid_uvc_mode", "message": f"Unsupported uvc_mode: {raw_uvc!r}", "allowed": list(UVC_STREAM_MODES)},
            )
        updates["uvc_mode"] = uvc_norm

    if "usb_link_speed" in body and body["usb_link_speed"] is not None:
        raw_usb = body["usb_link_speed"]
        if not isinstance(raw_usb, str):
            return False, {}, {"ok": False, "error": "invalid_usb_link_speed", "message": f"Invalid usb_link_speed: {raw_usb!r}"}
        usb_norm = _USB_LINK_ALIASES.get(raw_usb.strip().lower())
        if usb_norm is None:
            return (
                False,
                {},
                {"ok": False, "error": "invalid_usb_link_speed", "message": f"Unsupported usb_link_speed: {raw_usb!r}", "allowed": list(USB_LINK_SPEEDS)},
            )
        updates["usb_link_speed"] = usb_norm

    if "uac_audio_enabled" in body and body["uac_audio_enabled"] is not None:
        if not isinstance(body["uac_audio_enabled"], bool):
            return False, {}, {"ok": False, "error": "invalid_uac_audio_enabled", "message": "uac_audio_enabled must be bool"}
        updates["uac_audio_enabled"] = body["uac_audio_enabled"]

    # 5. Wired CDC-NCM SRT & RTMPS TLS 1.3
    if "srt_mode" in body and body["srt_mode"] is not None:
        raw_srt = body["srt_mode"]
        if not isinstance(raw_srt, str):
            return False, {}, {"ok": False, "error": "invalid_srt_mode", "message": f"Invalid srt_mode: {raw_srt!r}"}
        srt_norm = _SRT_MODE_ALIASES.get(raw_srt.strip().lower())
        if srt_norm is None:
            return (
                False,
                {},
                {"ok": False, "error": "invalid_srt_mode", "message": f"Unsupported srt_mode: {raw_srt!r}", "allowed": list(SRT_MODES)},
            )
        updates["srt_mode"] = srt_norm

    if "srt_pbkeylen" in body and body["srt_pbkeylen"] is not None:
        raw_pk = body["srt_pbkeylen"]
        if not isinstance(raw_pk, str):
            return False, {}, {"ok": False, "error": "invalid_srt_pbkeylen", "message": f"Invalid srt_pbkeylen: {raw_pk!r}"}
        pk_norm = _SRT_PBKEY_ALIASES.get(raw_pk.strip().lower())
        if pk_norm is None:
            return (
                False,
                {},
                {"ok": False, "error": "invalid_srt_pbkeylen", "message": f"Unsupported srt_pbkeylen: {raw_pk!r}", "allowed": list(SRT_PBKEYLEN_MODES)},
            )
        updates["srt_pbkeylen"] = pk_norm

    if "srt_latency_ms" in body and body["srt_latency_ms"] is not None:
        raw_lat = body["srt_latency_ms"]
        if isinstance(raw_lat, bool) or not isinstance(raw_lat, (int, float, str)):
            return False, {}, {"ok": False, "error": "invalid_srt_latency_ms", "message": f"Invalid srt_latency_ms: {raw_lat!r}"}
        try:
            f_lat = float(raw_lat)
        except ValueError:
            return False, {}, {"ok": False, "error": "invalid_srt_latency_ms", "message": f"Invalid srt_latency_ms: {raw_lat!r}"}
        if not math.isfinite(f_lat) or f_lat != float(int(f_lat)) or int(f_lat) < SRT_LATENCY_MIN_MS or int(f_lat) > SRT_LATENCY_MAX_MS:
            return False, {}, {"ok": False, "error": "invalid_srt_latency_ms", "message": "srt_latency_ms must be integer in [20, 1000]"}
        updates["srt_latency_ms"] = int(f_lat)

    if "rtmps_mode" in body and body["rtmps_mode"] is not None:
        raw_rtmps = body["rtmps_mode"]
        if not isinstance(raw_rtmps, str):
            return False, {}, {"ok": False, "error": "invalid_rtmps_mode", "message": f"Invalid rtmps_mode: {raw_rtmps!r}"}
        if raw_rtmps.strip().lower() in ("rtmp", "rtmp_plain", "rtmp://"):
            return False, {}, {"ok": False, "error": "rtmps_tls13_required", "message": "Plain RTMP rejected; RTMPS TLS 1.3 required"}
        rtmps_norm = _RTMPS_ALIASES.get(raw_rtmps.strip().lower())
        if rtmps_norm is None:
            return (
                False,
                {},
                {"ok": False, "error": "invalid_rtmps_mode", "message": f"Unsupported rtmps_mode: {raw_rtmps!r}", "allowed": list(RTMPS_MODES)},
            )
        if body.get("use_tls") is False and rtmps_norm != "OFF":
            return False, {}, {"ok": False, "error": "rtmps_tls13_required", "message": "RTMPS requires TLS 1.3"}
        updates["rtmps_mode"] = rtmps_norm

    if "stream_bitrate_mbps" in body and body["stream_bitrate_mbps"] is not None:
        raw_br = body["stream_bitrate_mbps"]
        if isinstance(raw_br, bool) or not isinstance(raw_br, (int, float, str)):
            return False, {}, {"ok": False, "error": "invalid_stream_bitrate_mbps", "message": f"Invalid stream_bitrate_mbps: {raw_br!r}"}
        try:
            f_br = float(raw_br)
        except ValueError:
            return False, {}, {"ok": False, "error": "invalid_stream_bitrate_mbps", "message": f"Invalid stream_bitrate_mbps: {raw_br!r}"}
        if not math.isfinite(f_br) or f_br != float(int(f_br)) or int(f_br) < 1 or int(f_br) > 50:
            return False, {}, {"ok": False, "error": "invalid_stream_bitrate_mbps", "message": "stream_bitrate_mbps must be integer in [1, 50]"}
        updates["stream_bitrate_mbps"] = int(f_br)

    # 6. CRSDK PTP / PTP-IP Mode + Safe 0xD2xx parameters
    if "crsdk_ptp_mode" in body and body["crsdk_ptp_mode"] is not None:
        raw_ptp = body["crsdk_ptp_mode"]
        if not isinstance(raw_ptp, str):
            return False, {}, {"ok": False, "error": "invalid_crsdk_ptp_mode", "message": f"Invalid crsdk_ptp_mode: {raw_ptp!r}"}
        ptp_norm = _CRSDK_PTP_ALIASES.get(raw_ptp.strip().lower())
        if ptp_norm is None:
            return (
                False,
                {},
                {"ok": False, "error": "invalid_crsdk_ptp_mode", "message": f"Unsupported crsdk_ptp_mode: {raw_ptp!r}", "allowed": list(CRSDK_PTP_MODES)},
            )
        updates["crsdk_ptp_mode"] = ptp_norm

    if "crsdk_cine_ei_base" in body and body["crsdk_cine_ei_base"] is not None:
        raw_base = str(body["crsdk_cine_ei_base"]).strip()
        if raw_base not in ("800", "12800"):
            return False, {}, {"ok": False, "error": "invalid_crsdk_cine_ei_base", "message": "crsdk_cine_ei_base must be '800' or '12800'"}
        updates["crsdk_cine_ei_base"] = raw_base
        updates.setdefault("crsdk_safe_opcode", 0xD210)

    if "crsdk_ei_index" in body and body["crsdk_ei_index"] is not None:
        raw_ei = body["crsdk_ei_index"]
        if isinstance(raw_ei, bool) or not isinstance(raw_ei, (int, float, str)):
            return False, {}, {"ok": False, "error": "invalid_crsdk_ei_index", "message": f"Invalid crsdk_ei_index: {raw_ei!r}"}
        try:
            ei_i = int(raw_ei)
        except ValueError:
            return False, {}, {"ok": False, "error": "invalid_crsdk_ei_index", "message": f"Invalid crsdk_ei_index: {raw_ei!r}"}
        if ei_i not in CINE_EI_STEPS["800"] and ei_i not in CINE_EI_STEPS["12800"]:
            return False, {}, {"ok": False, "error": "invalid_crsdk_ei_index", "message": f"Unsupported EI index: {ei_i}"}
        updates["crsdk_ei_index"] = ei_i
        updates.setdefault("crsdk_safe_opcode", 0xD210)

    if "crsdk_base_look" in body and body["crsdk_base_look"] is not None:
        raw_look = str(body["crsdk_base_look"]).strip()
        matched_look = next((k for k in BASE_LOOK_NLE_TAGS if k.lower() == raw_look.lower()), None)
        if matched_look is None:
            return False, {}, {"ok": False, "error": "invalid_crsdk_base_look", "message": f"Unsupported base_look: {raw_look!r}"}
        updates["crsdk_base_look"] = matched_look
        updates.setdefault("crsdk_safe_opcode", 0xD220)

    if "crsdk_nd_preset" in body and body["crsdk_nd_preset"] is not None:
        raw_nd = str(body["crsdk_nd_preset"]).strip()
        is_clear = raw_nd.lower() in ("clear", "clear [fx3 p4 locked]", "0", "none", "")
        updates["crsdk_nd_preset"] = "Clear [FX3 P4 Locked]"
        updates["crsdk_nd_clamped"] = not is_clear
        updates.setdefault("crsdk_safe_opcode", 0xD224)

    return True, updates, None


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


_BG_ROW = b"\x00" + b"\x0e\x10\x14\xff" * GPE0_W
_FAST_GPE_FN = None
_FAST_GPE_TRIED = False


def _get_fast_gpe0_fn():
    """Compile once into /private/tmp for sub-millisecond BGRA->PNG scanline packing, with stdlib fallback."""
    global _FAST_GPE_FN, _FAST_GPE_TRIED
    if _FAST_GPE_TRIED:
        return _FAST_GPE_FN
    _FAST_GPE_TRIED = True
    c_src = (
        "#include <stddef.h>\n"
        "#include <stdint.h>\n"
        "uint32_t fx6_pack_scanlines(const uint32_t *src, uint8_t *dst, uint32_t w, uint32_t h) {\n"
        "    uint32_t nz = 0, stride = 1u + w * 4u;\n"
        "    for (uint32_t y = 0; y < h; y++) {\n"
        "        uint8_t *row = dst + (size_t)y * stride;\n"
        "        row[0] = 0;\n"
        "        const uint32_t *s = src + (size_t)y * w;\n"
        "        uint8_t *p = row + 1;\n"
        "        for (uint32_t x = 0; x < w; x++, p += 4) {\n"
        "            uint32_t v = s[x];\n"
        "            if (v) { nz++; p[0] = (v >> 16) & 0xff; p[1] = (v >> 8) & 0xff; p[2] = v & 0xff; p[3] = 255; }\n"
        "            else   { p[0] = 14; p[1] = 16; p[2] = 20; p[3] = 255; }\n"
        "        }\n"
        "    }\n"
        "    return nz;\n"
        "}\n"
    )
    try:
        import ctypes
        import hashlib
        tag = hashlib.sha256(c_src.encode()).hexdigest()[:12]
        dylib = Path("/private/tmp") / f"fx6_gpe0_scanline_{tag}.dylib"
        if not dylib.is_file():
            src_file = Path("/private/tmp") / f"fx6_gpe0_scanline_{tag}.c"
            tmp_dylib = Path("/private/tmp") / f"fx6_gpe0_scanline_{tag}.{os.getpid()}.dylib"
            src_file.write_text(c_src)
            done = subprocess.run(
                ["/usr/bin/xcrun", "clang", "-O3", "-dynamiclib", str(src_file), "-o", str(tmp_dylib)],
                capture_output=True,
                timeout=10,
            )
            if done.returncode == 0:
                os.replace(tmp_dylib, dylib)
        if dylib.is_file():
            lib = ctypes.CDLL(str(dylib))
            fn = lib.fx6_pack_scanlines
            fn.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32]
            fn.restype = ctypes.c_uint32
            _FAST_GPE_FN = (ctypes, fn)
    except Exception:
        _FAST_GPE_FN = None
    return _FAST_GPE_FN


def gpe0_raw_to_png(raw: bytes) -> tuple[bytes, int]:
    """Convert raw 1024x540x4 gpe0 physical memory dump to PNG (sub-ms C fastpath + pure-stdlib fallback)."""
    if len(raw) < GPE0_BYTES:
        return b"", 0
    row_stride = 1 + GPE0_W * 4
    fast = _get_fast_gpe0_fn()
    if fast is not None:
        ctypes_mod, fn = fast
        scanlines = (ctypes_mod.c_uint8 * (row_stride * GPE0_H))()
        src_buf = (ctypes_mod.c_char * GPE0_BYTES).from_buffer_copy(raw, 0)
        nz = int(fn(ctypes_mod.addressof(src_buf), ctypes_mod.addressof(scanlines), GPE0_W, GPE0_H))
        if nz == 0:
            return b"", 0
        raw_scanlines = bytes(scanlines)
    else:
        u32_list = memoryview(raw)[:GPE0_BYTES].cast("I").tolist()
        nz = GPE0_W * GPE0_H - u32_list.count(0)
        if nz == 0:
            return b"", 0
        scanlines_ba = bytearray(_BG_ROW * GPE0_H)
        for idx, v in enumerate(u32_list):
            if v:
                y, x = divmod(idx, GPE0_W)
                o = y * row_stride + 1 + x * 4
                scanlines_ba[o] = (v >> 16) & 0xFF
                scanlines_ba[o + 1] = (v >> 8) & 0xFF
                scanlines_ba[o + 2] = v & 0xFF
        raw_scanlines = bytes(scanlines_ba)
    ihdr = struct.pack(">IIBBBBB", GPE0_W, GPE0_H, 8, 6, 0, 0, 0)
    compressed = zlib.compress(raw_scanlines, level=6)
    png = b"\x89PNG\r\n\x1a\n" + _png_chunk(b"IHDR", ihdr) + _png_chunk(b"IDAT", compressed) + _png_chunk(b"IEND", b"")
    return png, nz


def _relocate_migrated_path(raw_path: str) -> str:
    """Relocate historical /Volumes/KAFU2T/AI/Projects/Mac paths to internal AI-Workspace when present."""
    p = Path(raw_path)
    if p.exists():
        return raw_path
    prefixes = (
        "/Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/",
        "/Volumes/KAFU2T/AI/Projects/Mac/",
    )
    rel: str | None = None
    for pfx in prefixes:
        if raw_path.startswith(pfx):
            rel = raw_path[len(pfx):]
            break
    if rel is None:
        return raw_path
    roots = [
        REPO_ROOT,
        Path.home() / "AI-Workspace" / "AI" / "Projects" / "Mac" / "outputs" / "sony-fx3-fx6-lab",
        Path.home() / "AI-Workspace" / "AI" / "Projects" / "Mac",
    ]
    for root in roots:
        cand = root / rel
        if cand.exists():
            return str(cand)
    return raw_path


def _read_file_readonly(path: Path) -> bytes:
    """Open and read a donor/asset file strictly with os.O_RDONLY."""
    fd = os.open(str(path), os.O_RDONLY)
    with os.fdopen(fd, "rb") as fh:
        return fh.read()


def resolve_port_scoped_workdir(port: int, workdir: Path | None = None) -> Path:
    """Isolate runtime workdir by port whenever port != DEFAULT_PORT (8768)."""
    port = int(port)
    if workdir is None:
        return DEFAULT_WORKDIR if port == DEFAULT_PORT else Path(f"/private/tmp/fx6-live-gpe0-run-{port}")
    wd = Path(workdir)
    if port != DEFAULT_PORT and wd.resolve() == DEFAULT_WORKDIR.resolve():
        return Path(f"/private/tmp/fx6-live-gpe0-run-{port}")
    return wd


def _resolve_donor_app_dir() -> Path | None:
    """Locate Sony FX6 donor `share/app` directory strictly read-only if present locally."""
    env_dir = os.environ.get("FX6_DONOR_APP_DIR", "").strip()
    if env_dir:
        cand = Path(env_dir)
        if cand.is_dir():
            return cand
    env_uxc = os.environ.get("FX6_IMAGE_00_169_UXC", "").strip()
    if env_uxc and Path(env_uxc).is_file():
        return Path(env_uxc).parent
    if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM", "").strip().lower() in ("1", "true", "yes"):
        return None
    rel = Path("work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app")
    candidates = [
        REPO_ROOT / rel,
        Path.home() / "AI-Workspace" / "AI" / "Projects" / "Mac" / rel,
        Path.home() / "AI-Workspace" / "AI" / "Projects" / "Mac" / "outputs" / "sony-fx3-fx6-lab" / rel,
        Path("/Volumes/KAFU2T/AI/Projects/Mac") / rel,
    ]
    for cand in candidates:
        if cand.is_dir():
            return cand
    return None


def _resolve_donor_image_uxc() -> Path | None:
    """Locate Sony FX6 donor `image_00_169.uxc` strictly read-only if present locally."""
    env_uxc = os.environ.get("FX6_IMAGE_00_169_UXC", "").strip()
    if env_uxc and Path(env_uxc).is_file():
        return Path(env_uxc)
    app_dir = _resolve_donor_app_dir()
    if app_dir is not None:
        cand = app_dir / "image_00_169.uxc"
        if cand.is_file():
            return cand
    return None


DONOR_OVERLAY_FILENAMES = (
    "image_00_169.uxc",
    "string_simplifiedchinese_2.uxc",
    "MYingHeiC-GB18030-SJ_wIcon.ltt",
    "string_japanese_2.uxc",
)


def _resolve_donor_overlay_assets(donor_app_dir: Path | None = None) -> dict[str, Path]:
    """Return mapping `{cpio_rel_path: donor_path}` for available donor overlay files."""
    app_dir = donor_app_dir if donor_app_dir is not None else _resolve_donor_app_dir()
    assets: dict[str, Path] = {}
    if app_dir is not None and app_dir.is_dir():
        for fname in DONOR_OVERLAY_FILENAMES:
            cand = app_dir / fname
            if cand.is_file():
                assets[f"usr/share/app/{fname}"] = cand
    if "usr/share/app/image_00_169.uxc" not in assets and donor_app_dir is None:
        uxc = _resolve_donor_image_uxc()
        if uxc is not None:
            assets["usr/share/app/image_00_169.uxc"] = uxc
    return assets


def discover_available_lang_packs(donor_app_dir: Path | None = None) -> dict[str, dict[str, Any]]:
    """Inspect donor `.uxc` string packs & CJK font assets read-only and report availability."""
    app_dir = donor_app_dir if donor_app_dir is not None else _resolve_donor_app_dir()
    packs: dict[str, dict[str, Any]] = {}
    for code, spec in LANG_PACKS.items():
        req_files = tuple(spec["required_donor_files"])
        missing: list[str] = []
        staged_paths: dict[str, str] = {}
        if req_files:
            if app_dir is None or not app_dir.is_dir():
                missing = list(req_files)
            else:
                for fname in req_files:
                    cand = app_dir / fname
                    if cand.is_file():
                        staged_paths[fname] = str(cand)
                    else:
                        missing.append(fname)
        packs[code] = {
            "id": spec["id"],
            "code": code,
            "label": spec["label"],
            "short": spec["short"],
            "bank": spec["bank"],
            "font_ns": spec["font_ns"],
            "font_name": spec["font_name"],
            "uxc_files": list(spec["uxc_files"]),
            "required_donor_files": list(req_files),
            "staged_paths": staged_paths,
            "missing_files": missing,
            "available": len(missing) == 0,
        }
    return packs


def _pack_newc_entry(name: str, data: bytes, mode: int = 0o100644, ino: int = 0x9001) -> bytes:
    """Pack a single SVR4 newc (070701) CPIO record padded to 4-byte boundaries."""
    name_bytes = name.encode("utf-8") + b"\x00"
    namesize = len(name_bytes)
    filesize = len(data)
    hdr = (
        b"070701"
        + f"{ino:08x}{mode:08x}{0:08x}{0:08x}{1:08x}{0:08x}{filesize:08x}"
          f"{0:08x}{0:08x}{0:08x}{0:08x}{namesize:08x}{0:08x}".encode("ascii")
    )
    hdr_and_name = hdr + name_bytes
    name_pad = b"\x00" * ((-len(hdr_and_name)) % 4)
    data_pad = b"\x00" * ((-filesize) % 4)
    return hdr_and_name + name_pad + data + data_pad


_GDB_PKT_RE = re.compile(rb"\$([^#$]*)#[0-9a-fA-F]{2}")


class FX6LiveGpe0Session:
    def __init__(self, workdir: Path, port: int = DEFAULT_PORT) -> None:
        self.port = int(port)
        self.workdir = resolve_port_scoped_workdir(self.port, workdir)
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        self.gpe_lock = threading.Lock()
        self.cmd_lock = threading.Lock()
        self.gdb_lock = threading.Lock()
        self.proc: subprocess.Popen[bytes] | None = None
        self.serial_log = self.workdir / "serial.log"
        self.qemu_stderr = self.workdir / "qemu.stderr.log"
        self.qmp_sock = Path("/private/tmp") / f"fx6-live-qmp-{self.port}-{os.getpid()}.sock"
        self.gdb_sock = Path("/private/tmp") / f"fx6-live-gdb-{self.port}-{os.getpid()}.sock"
        self.qmp_conn: socket.socket | None = None
        self.gdb_conn: socket.socket | None = None
        self._gdb_rx = bytearray()
        self.gpe0_bin = self.workdir / "gpe0-live.bin"
        self.started_at: float | None = None

        # Shadow state matching guest 0x41e000e00 mailbox (mb[0..27])
        self.cmd_seq = 1
        self.ack_seq = 0
        self.page = 0
        self.sel_box = 4
        self.menu_cat = 2
        self.menu_item = 0
        self.menu_depth = 0
        self.cell_vals = [0, 0, 0, 0, 0, 0]
        self.ibis_idx = 0
        self.xlr_idx = 0
        self.p4_lock_attempts = 0
        self.p4_nd_reject_count = 0
        self.p12_bk4_airplane_mode_locked = True
        self.audio_ch_db: list[int] = [-12, -12, -18, -18]
        self.xlr_phantom_48v = True
        self.xlr_handle_attached = True
        self.rtmd_0xe304_ibis_lock = "ACTIVE_5AXIS"
        self.aspect_marker = "Off"
        self.zebra_mode = "Off"
        self.peaking_mode = "Off"
        self.desqueeze = "1.0x"
        self.cine_ei_base = "800"
        self.ei_index = 800
        self.shutter_mode = "angle"
        self.shutter_angle_deg = 180.0
        self.shutter_speed_denom = 48
        self.ecs_freq_hz = 60.0
        self.sq_enabled = False
        self.base_fps = 23.98
        self.sq_fps = 24
        self.rec_state = "STBY"
        self.tally_lamp_mode = "on"
        self.wired_io_mode = "off"
        self.rec_tc_frames = 0
        self.last_cine_exp_cmd = format_cine_exp_command({
            "cine_ei_base": self.cine_ei_base,
            "ei_index": self.ei_index,
            "shutter_mode": self.shutter_mode,
            "shutter_angle_deg": self.shutter_angle_deg,
            "shutter_speed_denom": self.shutter_speed_denom,
            "ecs_freq_hz": self.ecs_freq_hz,
            "sq_enabled": self.sq_enabled,
            "base_fps": self.base_fps,
            "sq_fps": self.sq_fps,
            "rec_state": self.rec_state,
            "tally_lamp_mode": self.tally_lamp_mode,
            "wired_io_mode": self.wired_io_mode,
            **compute_cine_ei_latitude(self.cine_ei_base, self.ei_index),
        })
        self.wb_mode = "preset_5600k"
        self.kelvin = 5600
        self.tint_gm = 0
        self.shockless_wb = "off"
        self.base_look = "S-Cinetone"
        self.cam_id = "A"
        self.reel_num = 1
        self.cam_pos = "C"
        self.clip_seq = 1
        self.dual_slot_mode = "simul"
        self.proxy_mode = "xavc_hs_1080p_16m"
        self.last_wb_media_cmd = format_wb_media_command(compute_color_and_media_derived({
            "wb_mode": self.wb_mode,
            "kelvin": self.kelvin,
            "tint_gm": self.tint_gm,
            "shockless_wb": self.shockless_wb,
            "base_look": self.base_look,
            "cam_id": self.cam_id,
            "reel_num": self.reel_num,
            "cam_pos": self.cam_pos,
            "clip_seq": self.clip_seq,
            "dual_slot_mode": self.dual_slot_mode,
            "proxy_mode": self.proxy_mode,
        }, sq_enabled=self.sq_enabled))
        self.touch_af_mode = "off"
        self.touch_x = 480
        self.touch_y = 270
        self.focus_mag = "1.0x"
        self.false_color_mode = "off"
        self.ciz_scale = 1.00
        self.ciz_res_mode = "4K"
        self.zoom_rocker_speed = 4
        self.last_letterbox_ignored = False
        self.last_touch_af_ciz_cmd = format_touch_focus_ciz_command(compute_touch_focus_ciz_derived({
            "touch_af_mode": self.touch_af_mode,
            "touch_x": self.touch_x,
            "touch_y": self.touch_y,
            "focus_mag": self.focus_mag,
            "false_color_mode": self.false_color_mode,
            "ciz_scale": self.ciz_scale,
            "ciz_res_mode": self.ciz_res_mode,
            "zoom_rocker_speed": self.zoom_rocker_speed,
        }))
        self.shotmarks: list[dict[str, Any]] = []
        self.iris_fstop = 2.8
        self.ae_shift_ev = 0.0
        self.metering_mode = "multi"
        self.ch34_safety_pad_db = 0
        self.user_bits_hex = "auto_camid_reel"
        self.push_auto_iris_active = False
        self.last_scene_ev = 12.0
        self.last_shotmark_iris_cmd = format_shotmark_iris_command(compute_shotmark_and_iris_derived({
            "shotmarks": self.shotmarks,
            "iris_fstop": self.iris_fstop,
            "ae_shift_ev": self.ae_shift_ev,
            "metering_mode": self.metering_mode,
            "ch34_safety_pad_db": self.ch34_safety_pad_db,
            "user_bits_hex": self.user_bits_hex,
            "push_auto_iris_active": self.push_auto_iris_active,
            "last_scene_ev": self.last_scene_ev,
        }))
        self.squeeze_factor = 1.0
        self.ibis_mode = "Standard"
        self.anamorphic_fallback_mode = "Anamorphic_Asymmetric"
        self.ref_tone_enabled = False
        self.color_bars_enabled = False
        self.limiter_enabled = False
        self.last_gyroflow_anamorphic_cmd = format_gyroflow_anamorphic_command(compute_gyroflow_anamorphic_derived({
            "squeeze_factor": self.squeeze_factor,
            "ibis_mode": self.ibis_mode,
            "anamorphic_fallback_mode": self.anamorphic_fallback_mode,
            "ref_tone_enabled": self.ref_tone_enabled,
            "color_bars_enabled": self.color_bars_enabled,
            "limiter_enabled": self.limiter_enabled,
        }))
        self.last_scope_stats: dict[str, Any] | None = None
        self.user_lut_slots: dict[str, dict[str, Any]] = self._default_user_lut_slots()
        self.cache_seconds = 0
        self.codec_profile = "auto"
        self.interval_rec_enabled = False
        self.interval_sec = 5
        self.target_shots = 120
        self.shots_taken = 0
        self.ae_tracking = "Mid"
        self.mechanical_curtain_actuations = 0
        self.ftps_mode = "Off"
        self.ftps_nic_driver = "CDC_NCM_RTL8153"
        self.ftps_tls_version = "FTPES_TLS13"
        self.ftps_queue: list[dict[str, Any]] = []
        self.ftps_completed: list[dict[str, Any]] = []
        self.ftps_blocked_traversal_count = 0
        self.ftps_last_blocked_path: str | None = None
        self.wf12_00342260_hits = 0
        self._user_lut_33_ram_tables: dict[str, list[tuple[float, float, float]]] = {}
        self.last_interval_cache_lut_ftp_cmd = format_interval_cache_lut_ftp_command(
            compute_interval_cache_lut_ftp_derived(
                {
                    "cache_seconds": self.cache_seconds,
                    "codec_profile": self.codec_profile,
                    "interval_rec_enabled": self.interval_rec_enabled,
                    "interval_sec": self.interval_sec,
                    "target_shots": self.target_shots,
                    "shots_taken": self.shots_taken,
                    "ae_tracking": self.ae_tracking,
                    "ftps_mode": self.ftps_mode,
                    "ftps_nic_driver": self.ftps_nic_driver,
                    "ftps_tls_version": self.ftps_tls_version,
                }
            )
        )
        self.fleet_role = "Solo"
        self.fleet_cams_online = 1
        self.fleet_nic_driver = "CDC_NCM_RTL8153"
        self.gang_rec_trigger = False
        self.sdi_bridge_converter = "BMD_Micro_Converter_12G"
        self.hdmi_rec_control_enabled = True
        self.hdmi_tc_output_enabled = True
        self.recorder_range_expectation = "AUTO_MATCH"
        self.mount_type = "Sony_EMount_12Pin_GM"
        self.lens_model = "SEL2470GM2 (FE 24-70mm F2.8 GM II)"
        self.lens_kg = 0.695
        self.focal_length_mm = 24
        self.rod_support_15mm_lws = False
        self.c2pa_blocked_attempts = 0
        self.c2pa_last_blocked_reason: str | None = None
        self.last_mc_fleet_sdi_c2pa_cmd = format_mc_fleet_sdi_c2pa_command(
            compute_mc_fleet_sdi_c2pa_derived(
                {
                    "fleet_role": self.fleet_role,
                    "fleet_cams_online": self.fleet_cams_online,
                    "fleet_nic_driver": self.fleet_nic_driver,
                    "gang_rec_trigger": self.gang_rec_trigger,
                    "sdi_bridge_converter": self.sdi_bridge_converter,
                    "hdmi_rec_control_enabled": self.hdmi_rec_control_enabled,
                    "hdmi_tc_output_enabled": self.hdmi_tc_output_enabled,
                    "recorder_range_expectation": self.recorder_range_expectation,
                    "mount_type": self.mount_type,
                    "lens_model": self.lens_model,
                    "lens_kg": self.lens_kg,
                    "focal_length_mm": self.focal_length_mm,
                    "rod_support_15mm_lws": self.rod_support_15mm_lws,
                }
            )
        )
        self.hlg_profile = "OFF"
        self.color_gamut = "BT.709"
        self.knee_mode = "Auto"
        self.detail_level = 0
        self.display_assist_mode = "OFF"
        self.ext_raw_mode = "OFF"
        self.breathing_comp_mode = "OFF"
        self.p116_assist_leak_blocked_count = 0
        self.p116_bt2020_blocked_count = 0
        self.last_hdr_hlg_raw_breathing_cmd = format_hdr_hlg_raw_breathing_command(
            compute_hdr_hlg_raw_breathing_derived(
                {
                    "hlg_profile": self.hlg_profile,
                    "color_gamut": self.color_gamut,
                    "knee_mode": self.knee_mode,
                    "detail_level": self.detail_level,
                    "display_assist_mode": self.display_assist_mode,
                    "ext_raw_mode": self.ext_raw_mode,
                    "breathing_comp_mode": self.breathing_comp_mode,
                }
            )
        )
        self.uvc_mode = "OFF"
        self.usb_link_speed = "USB3_5G"
        self.uac_audio_enabled = True
        self.srt_mode = "OFF"
        self.srt_pbkeylen = "AES-256"
        self.srt_latency_ms = 120
        self.rtmps_mode = "OFF"
        self.stream_bitrate_mbps = 12
        self.crsdk_ptp_mode = "OFF"
        self.p123_last_safe_opcode = 0xD210
        self.p123_safe_cmd_count = 0
        self.p123_flash_blocked_count = 0
        self.p123_last_blocked_opcode: str | None = None
        self.p123_p12_blocked_count = 0
        self.p123_uvc_osd_blocked_count = 0
        self.p123_crsdk_nd_clamp_count = 0
        self.last_uvc_srt_crsdk_ptp_cmd = format_uvc_srt_crsdk_ptp_command(
            compute_uvc_srt_crsdk_ptp_derived(
                {
                    "uvc_mode": self.uvc_mode,
                    "usb_link_speed": self.usb_link_speed,
                    "uac_audio_enabled": self.uac_audio_enabled,
                    "srt_mode": self.srt_mode,
                    "srt_pbkeylen": self.srt_pbkeylen,
                    "srt_latency_ms": self.srt_latency_ms,
                    "rtmps_mode": self.rtmps_mode,
                    "stream_bitrate_mbps": self.stream_bitrate_mbps,
                    "crsdk_ptp_mode": self.crsdk_ptp_mode,
                }
            )
        )
        self.last_toast = ""
        self.table_off = ALL_128_PAGES[0]["off"] if ALL_128_PAGES else 0x02E90FB0
        self.table_rows = ALL_128_PAGES[0]["rows"] if ALL_128_PAGES else 7
        self.table_off2 = 0
        self.table_rows2 = 0
        self.table_idx128 = 0
        self.rec_fmt_idx = 0
        self.lang_code = "en"
        self.lang_id = 0
        self.last_p10_hwcode = 0
        self.last_p10_telemetry: dict[str, Any] = {
            "button": None,
            "label": "Idle",
            "phy_code": "0x0000",
            "infra_code": "0x0000",
            "p10_code": "0x0000",
            "p10_symbol": "IDLE",
            "target_page": 0,
            "cmd_seq": 1,
        }
        self.last_nz = 0
        self.last_text_ok = 0
        self.last_fill_n = 0
        self.last_icon_n = 0
        self.last_png: bytes = FALLBACK_GPE0_PNG.read_bytes() if FALLBACK_GPE0_PNG.exists() else b""
        self.last_png_source = "real-gpe0-cached-677 (waiting for live VM boot)"
        self.last_raw_gpe0: bytes = b""
        self.socket_disconnect_count = 0
        self.last_multilang_diff: dict[str, Any] | None = None
        self._gpe0_test_capture_hook: Any = None
        self.live_ready = False
        self.crashed = False
        self.crash_reason = ""

    @staticmethod
    def _default_user_lut_slots() -> dict[str, dict[str, Any]]:
        slots: dict[str, dict[str, Any]] = {}
        for slot in USER_LUT_SLOTS:
            slots[slot] = {
                "slot": slot,
                "name": f"{slot} .cube",
                "title": f"{slot} .cube",
                "uploaded": False,
                "preset": None,
                "size": 33,
                "source_grid_size": 33,
                "target_grid_size": 33,
                "triplets": 33 ** 3,
                "resampled_33_triplets": 33 ** 3,
                "resampling_method": "tetrahedral",
                "sha256": None,
                "resampled_33_sha256": None,
                "contrast_signature": 1.0,
                "mid_gray_rgb": [0.5, 0.5, 0.5],
                "tint_rgb8": [128, 128, 128],
                "tint_hex": "#808080",
                "shadow_tint_rgb8": [128, 128, 128],
                "highlight_tint_rgb8": [128, 128, 128],
                "volatile_ram_only": True,
                "emmc_mutation_bytes": 0,
            }
        return slots

    def is_running(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def start_vm(self) -> dict[str, Any]:
        with self.lock:
            if self.is_running():
                return {"ok": True, "already_running": True, "pid": self.proc.pid}
            self._cleanup_sockets()
            manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
            argv = list(manifest["candidate_argv_before_observer_serial_retarget"])
            out_argv: list[str] = []
            i = 0
            while i < len(argv):
                if argv[i] == "-serial" and i + 1 < len(argv):
                    out_argv.extend(["-serial", f"file:{self.serial_log}"])
                    i += 2
                elif argv[i] == "-qmp" and i + 1 < len(argv):
                    out_argv.extend(["-qmp", f"unix:{self.qmp_sock},server=on,wait=off"])
                    i += 2
                elif argv[i] == "-chardev" and i + 1 < len(argv):
                    out_argv.extend([
                        "-chardev",
                        f"socket,path={self.gdb_sock},server=on,wait=off,id=keygate93",
                    ])
                    i += 2
                elif argv[i] == "-S":
                    i += 1
                elif argv[i] == "-device" and i + 1 < len(argv) and "file=" in argv[i + 1]:
                    dev_arg = argv[i + 1]
                    m_file = re.search(r"file=([^,]+)", dev_arg)
                    if m_file:
                        reloc = _relocate_migrated_path(m_file.group(1))
                        if reloc.endswith("guest-hybrid-fx6kernel-capid-grmreal-live700.cpio") and Path(reloc).is_file():
                            reloc = self._prepare_fresh_live700_cpio(Path(reloc))
                        dev_arg = dev_arg[:m_file.start(1)] + reloc + dev_arg[m_file.end(1):]
                    out_argv.extend(["-device", dev_arg])
                    i += 2
                else:
                    out_argv.append(_relocate_migrated_path(argv[i]) if argv[i].startswith("/") else argv[i])
                    i += 1

            env = os.environ.copy()
            for k, v in manifest.get("model_env", {}).items():
                env[str(k)] = str(v)

            self.serial_log.write_bytes(b"")
            stderr_f = self.qemu_stderr.open("wb")
            self.proc = subprocess.Popen(
                out_argv,
                cwd=str(self.workdir),
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=stderr_f,
            )
            self.started_at = time.time()
            self.live_ready = False
            self.crashed = False
            self.crash_reason = ""
            self.cmd_seq = 1
            self.ack_seq = 0
            self.page = 0
            self.sel_box = 4
            self.menu_cat = 2
            self.menu_item = 0
            self.menu_depth = 0
            self.cell_vals = [0, 0, 0, 0, 0, 0]
            self.ibis_idx = 0
            self.xlr_idx = 0
            self.p4_lock_attempts = 0
            self.p4_nd_reject_count = 0
            self.p12_bk4_airplane_mode_locked = True
            self.audio_ch_db = [-12, -12, -18, -18]
            self.xlr_phantom_48v = True
            self.xlr_handle_attached = True
            self.rtmd_0xe304_ibis_lock = "ACTIVE_5AXIS"
            self.aspect_marker = "Off"
            self.zebra_mode = "Off"
            self.peaking_mode = "Off"
            self.desqueeze = "1.0x"
            self.wb_mode = "preset_5600k"
            self.kelvin = 5600
            self.tint_gm = 0
            self.shockless_wb = "off"
            self.base_look = "S-Cinetone"
            self.cam_id = "A"
            self.reel_num = 1
            self.cam_pos = "C"
            self.clip_seq = 1
            self.dual_slot_mode = "simul"
            self.proxy_mode = "xavc_hs_1080p_16m"
            self.touch_af_mode = "off"
            self.touch_x = 480
            self.touch_y = 270
            self.focus_mag = "1.0x"
            self.false_color_mode = "off"
            self.ciz_scale = 1.00
            self.ciz_res_mode = "4K"
            self.zoom_rocker_speed = 4
            self.last_letterbox_ignored = False
            self.shotmarks = []
            self.iris_fstop = 2.8
            self.ae_shift_ev = 0.0
            self.metering_mode = "multi"
            self.ch34_safety_pad_db = 0
            self.user_bits_hex = "auto_camid_reel"
            self.push_auto_iris_active = False
            self.last_scene_ev = 12.0
            self.squeeze_factor = 1.0
            self.ibis_mode = "Standard"
            self.anamorphic_fallback_mode = "Anamorphic_Asymmetric"
            self.ref_tone_enabled = False
            self.color_bars_enabled = False
            self.limiter_enabled = False
            self.last_scope_stats = None
            self.user_lut_slots = self._default_user_lut_slots()
            self.last_toast = ""
            self.lang_code = "en"
            self.lang_id = 0
            self.last_p10_hwcode = 0
            self.last_p10_telemetry = {
                "button": None,
                "label": "Idle",
                "phy_code": "0x0000",
                "infra_code": "0x0000",
                "p10_code": "0x0000",
                "p10_symbol": "IDLE",
                "target_page": 0,
                "cmd_seq": 1,
            }
            return {"ok": True, "pid": self.proc.pid}

    def stop_vm(self) -> dict[str, Any]:
        with self.lock:
            self._close_connections()
            if self.proc is not None and self.proc.poll() is None:
                self.proc.terminate()
                try:
                    self.proc.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
            self.proc = None
            self.live_ready = False
            self._cleanup_sockets()
            return {"ok": True}

    def _close_connections(self) -> None:
        if self.qmp_conn is not None:
            try:
                self.qmp_conn.close()
            except Exception:
                pass
            self.qmp_conn = None
        with self.gdb_lock:
            if self.gdb_conn is not None:
                try:
                    self.gdb_conn.close()
                except Exception:
                    pass
                self.gdb_conn = None
            self._gdb_rx.clear()

    def _cleanup_sockets(self) -> None:
        self._close_connections()
        for p in (self.qmp_sock, self.gdb_sock):
            try:
                if p.exists():
                    p.unlink()
            except OSError:
                pass

    def _gdb_pop_packets(self, sock: socket.socket) -> list[bytes]:
        """Extract all complete `$...#xx` packets from `self._gdb_rx`, sending `+` ACK for each."""
        pkts: list[bytes] = []
        while True:
            m = _GDB_PKT_RE.search(self._gdb_rx)
            if not m:
                # Discard leading '+' / '-' ACK bytes when no complete packet starts at 0
                while self._gdb_rx and self._gdb_rx[0] in (0x2B, 0x2D):
                    del self._gdb_rx[0]
                break
            pkts.append(bytes(m.group(1)))
            del self._gdb_rx[:m.end()]
            sock.sendall(b"+")
        return pkts

    def _gdb_drain_async(self, sock: socket.socket, timeout: float = 0.05) -> list[bytes]:
        """Drain any pending async GDB packets/ACKs without blocking indefinitely."""
        pkts = self._gdb_pop_packets(sock)
        old_to = sock.gettimeout()
        try:
            sock.settimeout(timeout)
            deadline = time.time() + max(timeout, 0.02)
            while time.time() < deadline:
                try:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    self._gdb_rx.extend(chunk)
                    pkts.extend(self._gdb_pop_packets(sock))
                    sock.settimeout(0.01)
                except socket.timeout:
                    break
        finally:
            sock.settimeout(old_to)
        return pkts

    def _gdb_wait_stop_reply(self, sock: socket.socket, timeout: float = 0.45) -> list[bytes]:
        """Wait for stop-reply packet (`$T..#xx` / `$S..#xx` / `$W..#xx`) after sending 0x03."""
        pkts = self._gdb_pop_packets(sock)
        if any(p[:1] in (b"T", b"S", b"W", b"X") for p in pkts):
            pkts.extend(self._gdb_drain_async(sock, timeout=0.02))
            return pkts
        old_to = sock.gettimeout()
        deadline = time.time() + timeout
        try:
            while time.time() < deadline:
                rem = max(0.01, min(0.1, deadline - time.time()))
                sock.settimeout(rem)
                try:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    self._gdb_rx.extend(chunk)
                    got = self._gdb_pop_packets(sock)
                    pkts.extend(got)
                    if any(p[:1] in (b"T", b"S", b"W", b"X") for p in got):
                        pkts.extend(self._gdb_drain_async(sock, timeout=0.02))
                        break
                except socket.timeout:
                    if pkts:
                        break
        finally:
            sock.settimeout(old_to)
        return pkts

    def _gdb_send_packet(self, sock: socket.socket, payload: bytes, skip_stop_replies: bool = True) -> bytes:
        chk = sum(payload) & 0xFF
        pkt = b"$" + payload + b"#" + f"{chk:02x}".encode("ascii")
        sock.sendall(pkt)
        deadline = time.time() + 1.5
        while time.time() < deadline:
            pkts = self._gdb_pop_packets(sock)
            for p in pkts:
                if skip_stop_replies and p[:1] in (b"T", b"S"):
                    continue
                return p
            try:
                sock.settimeout(max(0.05, min(0.5, deadline - time.time())))
                chunk = sock.recv(4096)
                if not chunk:
                    break
                self._gdb_rx.extend(chunk)
                pkts = self._gdb_pop_packets(sock)
                for p in pkts:
                    if skip_stop_replies and p[:1] in (b"T", b"S"):
                        continue
                    return p
            except socket.timeout:
                break
        return b""

    def _ensure_gdb(self) -> socket.socket | None:
        if self.gdb_conn is not None:
            return self.gdb_conn
        if not self.is_running() or not self.gdb_sock.exists():
            return None
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(1.5)
        s.connect(str(self.gdb_sock))
        self._gdb_rx.clear()
        self._gdb_drain_async(s, timeout=0.04)
        self._gdb_send_packet(s, b"Qqemu.PhyMemMode:1")
        self.gdb_conn = s
        return s

    def _ensure_qmp(self) -> socket.socket | None:
        if self.qmp_conn is not None:
            return self.qmp_conn
        if not self.is_running() or not self.qmp_sock.exists():
            return None
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(2.5)
        s.connect(str(self.qmp_sock))
        s.recv(4096)
        s.sendall(b'{"execute":"qmp_capabilities"}\n')
        s.recv(4096)
        self.qmp_conn = s
        return s

    def _prepare_fresh_live700_cpio(self, donor_cpio: Path) -> str:
        """Build workdir/fx6-live700-rebuilt.cpio with latest memory-safe src/*.c shim and O_RDONLY donor overlay assets without mutating donor."""
        try:
            import mmap as _mmap
            import shutil
            import sys as _sys
            if str(TRIAL_DIR) not in _sys.path:
                _sys.path.insert(0, str(TRIAL_DIR))
            import build_live700 as b700
            self.workdir.mkdir(parents=True, exist_ok=True)
            tmp_so = self.workdir / "fx6-live700-shim.so"
            tmp_cpio = self.workdir / "fx6-live700-rebuilt.cpio"
            tmp_stamp = self.workdir / "fx6-live700-rebuilt.sha256"
            shim = b700.compile_shim(b700.DEFAULT_ZIG, tmp_so)
            overlay_assets = _resolve_donor_overlay_assets()
            asset_tag = "|".join(
                f"{k}={v}:{v.stat().st_size}" for k, v in sorted(overlay_assets.items())
            ) or "no-overlay"
            want_stamp = f"{donor_cpio}:{donor_cpio.stat().st_size}:{shim['sha256']}:{asset_tag}"
            if tmp_cpio.is_file() and tmp_stamp.is_file() and tmp_stamp.read_text().strip() == want_stamp:
                return str(tmp_cpio)
            shutil.copyfile(donor_cpio, tmp_cpio)
            b700.update_cpio_member(tmp_cpio, b700.MEMBER_NAME, tmp_so.read_bytes())
            if overlay_assets:
                with tmp_cpio.open("rb") as f, _mmap.mmap(f.fileno(), 0, access=_mmap.ACCESS_READ) as mm:
                    existing_names = {r["name"] for r in b700.scan_newc_cpio(mm)}
                missing = [(name, path) for name, path in sorted(overlay_assets.items()) if name not in existing_names]
                if missing:
                    chunks = []
                    for idx, (cpio_name, src_path) in enumerate(missing):
                        data = _read_file_readonly(src_path)
                        chunks.append(_pack_newc_entry(cpio_name, data, mode=0o100644, ino=0x9001 + idx))
                    chunks.append(_pack_newc_entry("TRAILER!!!", b"", mode=0, ino=0))
                    overlay = b"".join(chunks)
                    overlay += b"\x00" * ((-len(overlay)) % 512)
                    cur_sz = tmp_cpio.stat().st_size
                    pad_before = b"\x00" * ((-cur_sz) % 512)
                    with tmp_cpio.open("ab") as out:
                        if pad_before:
                            out.write(pad_before)
                        out.write(overlay)
            tmp_stamp.write_text(want_stamp)
            return str(tmp_cpio)
        except Exception as exc:
            print(f"[FX6-LIVE-GPE0] Warning: fallback to donor CPIO ({exc})")
            return str(donor_cpio)

    def _pack_mailbox_bytes(self) -> bytes:
        """Pack guest control mailbox mb[0..27] (112 bytes) matching fx6_live_guest.c."""
        mb_vals = (
            [self.table_off, self.table_rows, self.table_off2, self.table_rows2, 0, 0]
            if self.page == 24
            else list(self.cell_vals[:6])
        )
        if self.page != 24:
            mb_vals[3] = 0  # Stage-B P4 ND=Clear hardware lock
        stats_word = ((self.last_text_ok & 0xFF) << 24) | (self.last_nz & 0x00FFFFFF)
        words = [
            CTRL_MAGIC,
            self.cmd_seq,
            self.ack_seq,
            self.page,
            self.sel_box,
            self.menu_cat,
            self.menu_item,
            self.menu_depth,
            mb_vals[0],
            mb_vals[1],
            mb_vals[2],
            mb_vals[3],
            mb_vals[4],
            mb_vals[5],
            self.rec_fmt_idx,
            stats_word,
            self.lang_id,
            self.last_p10_hwcode & 0xFFFFFFFF,
        ]
        p11_state_word = ((self.xlr_idx & 0x0F) << 4) | (self.ibis_idx & 0x0F)
        active_lut_idx = self.cell_vals[4] % len(CINEMA_PARAM_SPECS["lut"]["presets"])
        if active_lut_idx >= 4:
            slot_num = active_lut_idx - 3
            slot_key = f"User{slot_num}"
            slot_info = self.user_lut_slots.get(slot_key, {})
            r8, g8, b8 = [max(0, min(255, int(v))) for v in slot_info.get("tint_rgb8", [128, 128, 128])]
            tint_valid = 1 if slot_info.get("uploaded") else 0
            lut_meta_word = ((slot_num & 0xF) << 28) | (tint_valid << 24) | (r8 << 16) | (g8 << 8) | b8
            raw_name = str(slot_info.get("name", slot_key)).encode("ascii", errors="replace")[:23]
        else:
            lut_meta_word = 0
            raw_name = b""
        lut_name_bytes = raw_name.ljust(24, b"\x00")
        name_words = struct.unpack("<6I", lut_name_bytes)
        ch_bytes = [max(-60, min(12, int(v))) + 60 for v in self.audio_ch_db[:4]]
        audio_packed_word = (
            (ch_bytes[0] & 0xFF)
            | ((ch_bytes[1] & 0xFF) << 8)
            | ((ch_bytes[2] & 0xFF) << 16)
            | ((ch_bytes[3] & 0xFF) << 24)
        )
        rtmd_idx = RTMD_0XE304_MODES.index(self.rtmd_0xe304_ibis_lock) if self.rtmd_0xe304_ibis_lock in RTMD_0XE304_MODES else 0
        aspect_choices = ASSIST_TOOLS_SPECS["aspect_marker"]["choices"]
        zebra_choices = ASSIST_TOOLS_SPECS["zebra_mode"]["choices"]
        peaking_choices = ASSIST_TOOLS_SPECS["peaking_mode"]["choices"]
        desqueeze_choices = ASSIST_TOOLS_SPECS["desqueeze"]["choices"]
        aspect_idx = aspect_choices.index(self.aspect_marker) if self.aspect_marker in aspect_choices else 0
        zebra_idx = zebra_choices.index(self.zebra_mode) if self.zebra_mode in zebra_choices else 0
        peaking_idx = peaking_choices.index(self.peaking_mode) if self.peaking_mode in peaking_choices else 0
        desqueeze_idx = desqueeze_choices.index(self.desqueeze) if self.desqueeze in desqueeze_choices else 0
        p56_valid = 1 if (aspect_idx or zebra_idx or peaking_idx or desqueeze_idx) else 0
        p40_flags_word = (
            (1 if self.xlr_handle_attached else 0)
            | ((1 if (self.xlr_handle_attached and self.xlr_phantom_48v) else 0) << 1)
            | ((rtmd_idx & 0x3) << 4)
            | (1 << 8)
            | (1 << 9)
            | ((aspect_idx & 0x7) << 12)
            | ((zebra_idx & 0x3) << 16)
            | ((peaking_idx & 0x3) << 18)
            | ((desqueeze_idx & 0x3) << 20)
            | (p56_valid << 24)
        )
        ext_raw = struct.pack("<I6III", lut_meta_word, *name_words, audio_packed_word, p40_flags_word)
        raw = struct.pack("<18I", *words) + struct.pack("<I", p11_state_word) + ext_raw
        return raw

    def _pack_phase64_mailbox_bytes(self) -> bytes:
        """Pack Phase 64 guest control mailbox mb[28..31] (16 bytes) matching fx6_live_guest.c."""
        base_high = 1 if self.cine_ei_base == "12800" else 0
        steps = CINE_EI_STEPS[self.cine_ei_base]
        ei_step = steps.index(self.ei_index) if self.ei_index in steps else 6
        shutter_mode_idx = SHUTTER_MODES.index(self.shutter_mode) if self.shutter_mode in SHUTTER_MODES else 0
        sq_flag = 1 if self.sq_enabled else 0
        base_fps_idx = next(
            (i for i, v in enumerate(SQ_BASE_FPS_VALUES) if abs(v - float(self.base_fps)) < 1e-3),
            0,
        )
        rec_flag = 1 if self.rec_state == "REC" else 0
        tally_idx = TALLY_LAMP_MODES.index(self.tally_lamp_mode) if self.tally_lamp_mode in TALLY_LAMP_MODES else 0
        wired_io_idx = WIRED_IO_MODES.index(self.wired_io_mode) if self.wired_io_mode in WIRED_IO_MODES else 0
        mb28 = (
            (base_high & 0x1)
            | ((ei_step & 0xF) << 1)
            | ((shutter_mode_idx & 0x3) << 5)
            | ((sq_flag & 0x1) << 7)
            | ((base_fps_idx & 0x7) << 8)
            | ((rec_flag & 0x1) << 11)
            | ((tally_idx & 0x3) << 12)
            | ((wired_io_idx & 0x3) << 14)
            | (1 << 16)   # P4 ND hardware absent
            | (1 << 17)   # P12 Wi-Fi/BT RF disabled
            | (1 << 31)   # phase64_valid
        )
        if self.shutter_mode == "speed":
            sh_val = int(self.shutter_speed_denom) & 0xFFFFF
        elif self.shutter_mode == "ecs":
            sh_val = int(round(float(self.ecs_freq_hz) * 100.0)) & 0xFFFFF
        else:
            sh_val = int(round(float(self.shutter_angle_deg) * 10.0)) & 0xFFFFF
        mb29 = sh_val | ((int(self.sq_fps) & 0xFF) << 20)
        mb30 = int(self.rec_tc_frames) & 0xFFFFFFFF
        mb31 = 0x43494E45  # 'CINE'
        return struct.pack("<4I", mb28, mb29, mb30, mb31)

    def _pack_full_mailbox_bytes(self) -> bytes:
        """Pack complete guest control mailbox mb[0..31] (128 bytes)."""
        return self._pack_mailbox_bytes() + self._pack_phase64_mailbox_bytes()

    def _pack_phase73_mailbox_bytes(self) -> bytes:
        """Pack Phase 73 guest control mailbox mb[32..35] (16 bytes) matching fx6_live_guest.c."""
        wb_mode_idx = WB_MODES.index(self.wb_mode) if self.wb_mode in WB_MODES else 2
        kelvin_val = WB_PRESET_KELVIN[self.wb_mode] if self.wb_mode in WB_PRESET_KELVIN else int(self.kelvin)
        kelvin_val = max(WB_KELVIN_MIN, min(WB_KELVIN_MAX, kelvin_val))
        tint_enc = (max(WB_TINT_MIN, min(WB_TINT_MAX, int(self.tint_gm))) + 99) & 0xFF
        shockless_idx = SHOCKLESS_WB_MODES.index(self.shockless_wb) if self.shockless_wb in SHOCKLESS_WB_MODES else 0
        look_idx = BASE_LOOK_NLE_TAGS.get(self.base_look, BASE_LOOK_NLE_TAGS["S-Cinetone"])["guest_idx"]
        mb32 = (
            (wb_mode_idx & 0x7)
            | ((kelvin_val & 0x3FFF) << 3)
            | ((tint_enc & 0xFF) << 17)
            | ((shockless_idx & 0x3) << 25)
            | ((look_idx & 0x7) << 27)
            | (1 << 30)   # wb_soft_mapped (FX3 physical B/A/PRST switch absent)
            | (1 << 31)   # phase73_valid
        )
        cam_id_idx = max(0, min(25, ord(str(self.cam_id or "A")[0].upper()) - ord("A")))
        reel_val = max(1, min(999, int(self.reel_num)))
        cam_pos_idx = CAM_POS_VALUES.index(self.cam_pos) if self.cam_pos in CAM_POS_VALUES else 0
        clip_seq_val = max(1, min(999, int(self.clip_seq)))
        dual_slot_idx = DUAL_SLOT_MODES.index(self.dual_slot_mode) if self.dual_slot_mode in DUAL_SLOT_MODES else 0
        proxy_map = {"off": 0, "xavc_hs_1080p_16m": 1, "xavc_hs_1080p_9m": 2, "xavc_s_720p_6m": 3}
        proxy_mode_idx = proxy_map.get(self.proxy_mode, 1)
        proxy_eff = 1 if (self.proxy_mode != "off" and not self.sq_enabled) else 0
        mb33 = (
            (cam_id_idx & 0x1F)
            | ((reel_val & 0x3FF) << 5)
            | ((cam_pos_idx & 0x3) << 15)
            | ((clip_seq_val & 0x3FF) << 17)
            | ((dual_slot_idx & 0x3) << 27)
            | ((proxy_mode_idx & 0x3) << 29)
            | ((proxy_eff & 0x1) << 31)
        )
        lut_cell_idx = self.cell_vals[4] % 8
        active_lut_slot_num = (lut_cell_idx - 3) if lut_cell_idx >= 4 else (1 if self.base_look == "User 3D LUT" else 0)
        mb34 = (1 if self.sq_enabled else 0) | ((active_lut_slot_num & 0x7) << 1)
        mb35 = 0x57424C4D  # 'WBLM'
        return struct.pack("<4I", mb32, mb33, mb34, mb35)

    def _pack_phase81_mailbox_bytes(self) -> bytes:
        """Pack Phase 81 guest control mailbox mb[36..39] (16 bytes) matching fx6_live_guest.c."""
        tfc = self.get_touch_focus_ciz()
        af_idx = TOUCH_AF_MODES.index(tfc["touch_af_mode"]) if tfc["touch_af_mode"] in TOUCH_AF_MODES else 0
        tx = max(0, min(959, int(tfc["touch_x"])))
        ty = max(0, min(539, int(tfc["touch_y"])))
        p_idx = max(0, min(626, int(tfc["pdaf_index"])))
        p_col = max(0, min(32, int(tfc["pdaf_col"])))
        p_row = max(0, min(18, int(tfc["pdaf_row"])))
        mag_idx = FOCUS_MAG_MODES.index(tfc["focus_mag"]) if tfc["focus_mag"] in FOCUS_MAG_MODES else 0
        fc_idx = FALSE_COLOR_MODES.index(tfc["false_color_mode"]) if tfc["false_color_mode"] in FALSE_COLOR_MODES else 0
        eff_ciz_x100 = max(100, min(200, int(round(float(tfc["effective_ciz_scale"]) * 100.0))))
        req_ciz_x100 = max(100, min(200, int(round(float(tfc["ciz_scale"]) * 100.0))))
        spd = max(1, min(8, int(tfc["zoom_rocker_speed"])))
        res_fhd = 1 if tfc["ciz_res_mode"] == "FHD" else 0
        excl_bit = 1 if tfc["ciz_clamped_by_exclusion"] else 0
        res_clamp_bit = 1 if tfc["ciz_clamped_by_res_limit"] else 0
        zeb_warn_bit = 1 if tfc["slog3_zebra100_clip_warning"] else 0
        lb_bit = 1 if tfc["letterbox_ignored"] else 0

        mb36 = (
            (af_idx & 0x3)
            | ((tx & 0x3FF) << 2)
            | ((ty & 0x3FF) << 12)
            | ((p_idx & 0x3FF) << 22)
        )
        mb37 = (
            (p_col & 0x3F)
            | ((p_row & 0x1F) << 6)
            | ((mag_idx & 0x3) << 11)
            | ((fc_idx & 0x3) << 13)
            | (1 << 15)  # clean_hdmi_unmagnified = True
            | ((eff_ciz_x100 & 0xFF) << 16)
            | ((req_ciz_x100 & 0xFF) << 24)
        )
        mb38 = (
            (spd & 0xF)
            | ((res_fhd & 0x1) << 4)
            | ((excl_bit & 0x1) << 5)
            | ((res_clamp_bit & 0x1) << 6)
            | ((zeb_warn_bit & 0x1) << 7)
            | ((lb_bit & 0x1) << 8)
            | (1 << 31)  # phase81_valid
        )
        mb39 = 0x54414643  # 'TAFC'
        return struct.pack("<4I", mb36, mb37, mb38, mb39)

    def _pack_phase88_mailbox_bytes(self) -> bytes:
        """Pack Phase 88 guest control mailbox mb[40..43] (16 bytes) matching fx6_live_guest.c."""
        smi = self.get_shotmark_and_iris()
        sm_total = max(0, min(64, int(smi["shotmark_count"])))
        sm1_cnt = max(0, min(64, int(smi["shotmark1_count"])))
        sm2_cnt = max(0, min(64, int(smi["shotmark2_count"])))
        latest = smi.get("latest_shotmark")
        if isinstance(latest, dict):
            last_type = 1 if latest.get("type") == "ShotMark1" else (2 if latest.get("type") == "ShotMark2" else 0)
            last_frame_low = int(latest.get("frame", 0)) & 0x1FF
        else:
            last_type = 0
            last_frame_low = 0

        mb40 = (
            (sm_total & 0x7F)
            | ((sm1_cnt & 0x7F) << 7)
            | ((sm2_cnt & 0x7F) << 14)
            | ((last_type & 0x3) << 21)
            | ((last_frame_low & 0x1FF) << 23)
        )
        iris_x100 = max(140, min(2200, int(round(float(smi["iris_fstop"]) * 100.0))))
        meter_idx = METERING_MODES.index(smi["metering_mode"]) if smi["metering_mode"] in METERING_MODES else 0
        ae_enc = max(0, min(32, int(round((float(smi["ae_shift_ev"]) + 2.0) * 8.0))))
        pad_bit = 1 if int(smi["ch34_safety_pad_db"]) == -20 else 0
        push_bit = 1 if smi["push_auto_iris_active"] else 0
        target_ire_int = max(1, min(109, int(round(float(smi["target_ire"])))))

        mb41 = (
            (iris_x100 & 0xFFF)
            | ((meter_idx & 0x3) << 12)
            | ((ae_enc & 0xFF) << 14)
            | ((pad_bit & 0x1) << 22)
            | ((push_bit & 0x1) << 23)
            | ((target_ire_int & 0x7F) << 24)
            | (1 << 31)  # phase88_valid
        )
        mb42 = user_bits_to_uint32(smi["user_bits_effective"])
        mb43 = 0x534D524B  # 'SMRK'
        return struct.pack("<4I", mb40, mb41, mb42, mb43)

    def _pack_phase95_mailbox_bytes(self) -> bytes:
        """Pack Phase 95 guest control mailbox mb[44..47] (16 bytes) matching fx6_live_guest.c."""
        ga = self.get_gyroflow_anamorphic()
        sq = float(ga["squeeze_factor"])
        try:
            sq_idx = ANAMORPHIC_SQUEEZE_FACTORS.index(sq)
        except ValueError:
            sq_idx = 0
        eff_ibis_idx = (
            IBIS_ARBITRATOR_MODES.index(ga["effective_ibis_mode"])
            if ga["effective_ibis_mode"] in IBIS_ARBITRATOR_MODES
            else 1
        )
        req_ibis_idx = (
            IBIS_ARBITRATOR_MODES.index(ga["ibis_mode"])
            if ga["ibis_mode"] in IBIS_ARBITRATOR_MODES
            else 1
        )
        arb_bit = 1 if ga["ibis_arbitrated"] else 0
        ctr_bit = 1 if ga["center_lock_0x0400"] else 0
        yaw_pct = max(0, min(100, int(round(float(ga["horizontal_yaw_gain"]) * 100.0))))
        tx = max(0, min(959, int(ga["touch_x"])))
        tx_sync_bit = 1 if ga["touch_af_desqueeze_synced"] else 0
        wobble_bit = 1 if ga["anamorphic_edge_wobble_prevented"] else 0

        mb44 = (
            (sq_idx & 0x7)
            | ((eff_ibis_idx & 0x7) << 3)
            | ((req_ibis_idx & 0x7) << 6)
            | ((arb_bit & 0x1) << 9)
            | ((ctr_bit & 0x1) << 10)
            | ((yaw_pct & 0xFF) << 11)
            | ((tx & 0x3FF) << 19)
            | ((tx_sync_bit & 0x1) << 29)
            | ((wobble_bit & 0x1) << 30)
            | (1 << 31)  # phase95_valid
        )

        imu_x10 = max(1, min(4095, int(round(float(ga["imu_samples_per_frame"]) * 10.0))))
        skew_x10 = max(1, min(255, int(round(float(ga["rolling_shutter_skew_ms"]) * 10.0))))
        rtmd_map = {"RTMD_READY": 0, "RTMD_CENTER_LOCKED": 1, "RTMD_SUSPENDED_BY_SQ": 2}
        rtmd_st_idx = rtmd_map.get(str(ga["rtmd_status"]), 0)
        susp_sq_bit = 1 if ga["rtmd_suspended_by_sq"] else 0
        gyro_ready_bit = 1 if ga["gyroflow_ready"] else 0
        fb_ctr_bit = 1 if ga["anamorphic_fallback_mode"] == "Center_Lock_Gyroflow" else 0
        sq_x50 = max(50, min(127, int(round(sq * 50.0))))

        mb45 = (
            (imu_x10 & 0xFFF)
            | ((skew_x10 & 0xFF) << 12)
            | ((rtmd_st_idx & 0x3) << 20)
            | ((susp_sq_bit & 0x1) << 22)
            | ((gyro_ready_bit & 0x1) << 23)
            | ((fb_ctr_bit & 0x1) << 24)
            | ((sq_x50 & 0x7F) << 25)
        )

        tone_req = 1 if ga["ref_tone_enabled"] else 0
        tone_eff = 1 if ga["ref_tone_effective_active"] else 0
        tone_inhib = 1 if ga["ref_tone_inhibited_by_rec"] else 0
        bars_eff = 1 if ga["color_bars_effective_active"] else 0
        lim_en = 1 if ga["limiter_enabled"] else 0
        lim_eng = 1 if ga["limiter_engaging"] else 0
        ch_mask = int(ga["ch_clamped_mask"]) & 0xF
        ceil_x10 = 30
        ref_lvl_abs = 20

        mb46 = (
            (tone_req & 0x1)
            | ((tone_eff & 0x1) << 1)
            | ((tone_inhib & 0x1) << 2)
            | ((bars_eff & 0x1) << 3)
            | ((lim_en & 0x1) << 4)
            | ((lim_eng & 0x1) << 5)
            | ((ch_mask & 0xF) << 6)
            | ((ceil_x10 & 0xFF) << 10)
            | ((ref_lvl_abs & 0xFF) << 18)
            | (1 << 31)  # phase95_tone_valid
        )
        mb47 = 0x4759524F  # 'GYRO'
        return struct.pack("<4I", mb44, mb45, mb46, mb47)

    def _pack_phase102_mailbox_bytes(self) -> bytes:
        """Pack Phase 102 guest control mailbox mb[48..51] (16 bytes) matching fx6_live_guest.c."""
        p102 = self.get_interval_cache_lut_ftp()
        eff_sec = max(0, min(16, int(p102["effective_cache_seconds"])))
        req_sec = max(0, min(16, int(p102["cache_seconds"])))
        ddr_mib = max(0, min(384, int(round(float(p102["allocated_ddr_mib"])))))
        cache_active = 1 if p102["picture_cache_active"] else 0
        cache_susp = 1 if p102["picture_cache_suspended"] else 0
        cache_clamped = 1 if p102["clamped_by_ddr_budget"] else 0
        intvl_en = 1 if p102["interval_rec_enabled"] else 0
        intvl_sec = max(1, min(60, int(p102["interval_sec"])))
        ae_map = {"High": 0, "Mid": 1, "Low": 2, "Lock": 3}
        ae_idx = ae_map.get(str(p102["ae_tracking"]), 1)

        mb48 = (
            (eff_sec & 0x1F)
            | ((req_sec & 0x1F) << 5)
            | ((ddr_mib & 0x1FF) << 10)
            | ((cache_active & 0x1) << 19)
            | ((cache_susp & 0x1) << 20)
            | ((cache_clamped & 0x1) << 21)
            | ((intvl_en & 0x1) << 22)
            | ((intvl_sec & 0x3F) << 23)
            | ((ae_idx & 0x3) << 29)
            | (1 << 31)  # phase102_cache_interval valid
        )

        shots_taken = max(0, min(9999, int(p102["shots_taken"])))
        target_shots = max(1, min(9999, int(p102["target_shots"])))
        ftps_map = {"Off": 0, "Proxy_Only": 1, "Original_And_Proxy": 2}
        ftps_idx = ftps_map.get(str(p102["ftps_mode"]), 0)
        ftps_p12_safe = 1 if p102["p12_rf_off_enforced"] else 0
        eshut_enforced = 1 if p102["electronic_shutter_enforced"] else 0

        mb49 = (
            (shots_taken & 0x3FFF)
            | ((target_shots & 0x3FFF) << 14)
            | ((ftps_idx & 0x3) << 28)
            | ((ftps_p12_safe & 0x1) << 30)
            | ((eshut_enforced & 0x1) << 31)
        )

        slot_map = {"User1": 1, "User2": 2, "User3": 3, "User4": 4}
        lut_slot = slot_map.get(str(p102.get("active_user_lut_slot") or ""), 0) if p102["active_user_lut_uploaded"] else 0
        lut_res33 = 1 if (p102["active_user_lut_uploaded"] and p102.get("active_user_lut_target_size") == 33) else 0
        src_map = {17: 1, 33: 2, 65: 3}
        lut_src_idx = src_map.get(int(p102.get("active_user_lut_source_size", 0)), 0) if p102["active_user_lut_uploaded"] else 0
        contrast_x100 = max(25, min(250, int(round(float(p102.get("active_user_lut_contrast_signature", 1.0)) * 100.0))))
        ftps_q_cnt = max(0, min(255, int(p102["ftps_queued_count"])))
        ftps_done_cnt = max(0, min(255, int(p102["ftps_completed_count"])))
        ftps_trav_blk = 1 if int(p102["ftps_blocked_traversal_count"]) > 0 else 0

        mb50 = (
            (lut_slot & 0x7)
            | ((lut_res33 & 0x1) << 3)
            | ((lut_src_idx & 0x3) << 4)
            | ((contrast_x100 & 0xFF) << 6)
            | ((ftps_q_cnt & 0xFF) << 14)
            | ((ftps_done_cnt & 0xFF) << 22)
            | ((ftps_trav_blk & 0x1) << 30)
            | (1 << 31)  # phase102_lut_ftps valid
        )
        mb51 = 0x49434C46  # 'ICLF'
        return struct.pack("<4I", mb48, mb49, mb50, mb51)

    def _pack_phase109_mailbox_bytes(self) -> bytes:
        """Pack Phase 109 guest control mailbox mb[52..55] (16 bytes) matching fx6_live_guest.c."""
        p109 = self.get_mc_fleet_sdi_c2pa()
        role_idx = _MC_FLEET_ROLE_TO_IDX.get(str(p109["fleet_role"]), 0)
        cams_online = max(1, min(4, int(p109["fleet_cams_online"])))
        gang_rec = 1 if p109["gang_rec_trigger"] else 0
        sdi_active = 1 if p109["sdi_bridge_active"] else 0
        sdi_idx = _SDI_BRIDGE_TO_IDX.get(str(p109["sdi_bridge_converter"]), 0)
        rp188_rec = 1 if int(p109["rp188_rec_trigger_bit"]) else 0
        avi_safe = 1 if p109["avi_checksum_valid"] and p109["shadow_crush_prevented"] else 0
        avi_quant_idx = 1 if "FULL" in str(p109["avi_quantization_range"]).upper() else 0
        avi_cs = int(p109["avi_checksum_byte"]) & 0xFF
        ptp_skew_div2 = max(0, min(63, int(round(float(p109["ptp_max_clock_skew_us"]) / 2.0))))
        p12_rf_off = 1 if p109["p12_rf_off_enforced"] else 0
        hdmi_tc = 1 if p109["hdmi_tc_output_enabled"] else 0

        mb52 = (
            (role_idx & 0x7)
            | ((cams_online & 0x7) << 3)
            | ((gang_rec & 0x1) << 6)
            | ((sdi_active & 0x1) << 7)
            | ((sdi_idx & 0x3) << 8)
            | ((rp188_rec & 0x1) << 10)
            | ((avi_safe & 0x1) << 11)
            | ((avi_quant_idx & 0x1) << 12)
            | ((avi_cs & 0xFF) << 13)
            | ((ptp_skew_div2 & 0x3F) << 21)
            | ((p12_rf_off & 0x1) << 27)
            | ((hdmi_tc & 0x1) << 28)
            | (1 << 31)
        )

        mount_pl = 1 if p109["mount_type"] == "Manual_PL_Adapter_Unchipped" else 0
        shd_ident = 1 if p109["shading_identity_reset"] else 0
        shd_gain_x100 = max(50, min(255, int(round(float(p109["vignetting_comp_gain"]) * 100.0))))
        lens_kg_x10 = max(1, min(63, int(round(float(p109["lens_kg"]) * 10.0))))
        g31_warn = 1 if p109["g31_15mm_lws_warning"] else 0
        rod_lws = 1 if p109["rod_support_15mm_lws"] else 0
        e_pins = 0 if mount_pl else max(0, min(15, int(p109["electronic_pins_active"])))
        focal_div2 = max(1, min(127, int(p109["focal_length_mm"]) // 2))

        mb53 = (
            (mount_pl & 0x1)
            | ((shd_ident & 0x1) << 1)
            | ((shd_gain_x100 & 0xFF) << 2)
            | ((lens_kg_x10 & 0x3F) << 10)
            | ((g31_warn & 0x1) << 16)
            | ((rod_lws & 0x1) << 17)
            | ((e_pins & 0xF) << 18)
            | ((focal_div2 & 0x7F) << 22)
            | (1 << 31)
        )

        blk_cnt = max(0, min(255, int(p109["c2pa_blocked_attempts"])))
        spoof_blk = 1 if blk_cnt > 0 else 0
        fleet_pkt_div10 = (int(self.cmd_seq) // 10) & 0xFF
        mb54 = (
            0  # vault_idx=0 (CNFLASHA_RDONLY_ZERO_TOUCH)
            | (1 << 2)  # clean_room_research=1
            | (0 << 3)  # hw_attest_claimed=0
            | (1 << 4)  # cnflasha_ro_zero_touch=1
            | ((spoof_blk & 0x1) << 5)
            | ((blk_cnt & 0xFF) << 6)
            | ((fleet_pkt_div10 & 0xFF) << 14)
            | (1 << 31)
        )
        mb55 = 0x4D43464C  # 'MCFL'
        return struct.pack("<4I", mb52, mb53, mb54, mb55)

    def _pack_phase116_mailbox_bytes(self) -> bytes:
        """Pack Phase 116 guest control mailbox mb[56..59] (16 bytes) matching fx6_live_guest.c."""
        p116 = self.get_hdr_hlg_raw_breathing()
        hlg_idx = _HLG_PROFILE_TO_IDX.get(str(p116["hlg_profile"]), 0)
        gamut_idx = _HLG_GAMUT_TO_IDX.get(str(p116["color_gamut"]), 0)
        detail_enc = max(0, min(14, int(p116["detail_level"]) + 7))
        knee_idx = _HLG_KNEE_TO_IDX.get(str(p116["knee_mode"]), 0)
        cta_eotf = int(p116["cta_eotf"]) & 0x3
        cta_ok = 1 if p116["cta_checksum_valid"] else 0
        cta_cs = int(p116["cta_checksum_byte"]) & 0xFF
        peak_nits_div10 = max(10, min(255, int(p116["peak_nits"]) // 10))
        bt2020_blk = 1 if int(p116["bt2020_in_bt709_blocked_count"]) > 0 else 0

        mb56 = (
            (hlg_idx & 0x7)
            | ((gamut_idx & 0x3) << 3)
            | ((detail_enc & 0xF) << 5)
            | ((knee_idx & 0x3) << 9)
            | ((cta_eotf & 0x3) << 11)
            | ((cta_ok & 0x1) << 13)
            | ((cta_cs & 0xFF) << 14)
            | ((peak_nits_div10 & 0xFF) << 22)
            | ((bt2020_blk & 0x1) << 30)
            | (1 << 31)
        )

        ast_req = _DISPLAY_ASSIST_TO_IDX.get(str(p116["display_assist_mode"]), 0)
        ast_res = _DISPLAY_ASSIST_TO_IDX.get(str(p116["resolved_assist_mode"]), 0)
        evf_ast_on = 1 if p116["evf_lcd_assist_active"] else 0
        clean_hdmi = 1 if p116["clean_hdmi_sdi_unassisted"] else 0
        xavc_unassist = 1 if p116["xavc_internal_unassisted"] else 0
        leak_cnt = max(0, min(127, int(p116["assist_leak_blocked_count"])))
        vf_nit_div10 = max(1, min(255, int(p116["vf_nit_ceiling"]) // 10))
        peak_ire = max(0, min(109, int(p116["waveform_peak_ire"])))

        mb57 = (
            (ast_req & 0x7)
            | ((ast_res & 0x7) << 3)
            | ((evf_ast_on & 0x1) << 6)
            | ((clean_hdmi & 0x1) << 7)
            | ((xavc_unassist & 0x1) << 8)
            | ((leak_cnt & 0x7F) << 9)
            | ((vf_nit_div10 & 0xFF) << 16)
            | ((peak_ire & 0x7F) << 24)
            | (1 << 31)
        )

        ext_raw_idx = _EXT_RAW_TO_IDX.get(str(p116["ext_raw_mode"]), 0)
        raw_b12800 = 1 if int(p116["raw_base_iso"]) >= 12800 else 0
        raw_kelvin_div100 = max(20, min(150, int(p116["raw_kelvin"]) // 100))
        lens_meta = 1 if p116["raw_lens_metadata"]["attached"] else 0
        tc_trig = 1 if (self.rec_state == "REC" and ext_raw_idx > 0) else 0
        breath_req = 1 if p116["breathing_comp_mode"] == "AUTO" else 0
        breath_eff = 1 if p116["breathing_effective_active"] else 0
        byp_pl = 1 if p116["breathing_bypassed_by_pl_mount"] else 0
        byp_raw = 1 if p116["breathing_bypassed_by_raw"] else 0
        crop_x100 = max(100, min(108, int(round(float(p116["breathing_crop_factor"]) * 100.0))))
        fps_list = [23.98, 24.0, 25.0, 29.97, 50.0, 59.94]
        raw_fps_idx = min(range(len(fps_list)), key=lambda i: abs(fps_list[i] - float(self.base_fps)))

        mb58 = (
            (ext_raw_idx & 0x3)
            | ((raw_b12800 & 0x1) << 2)
            | ((raw_kelvin_div100 & 0xFF) << 3)
            | ((lens_meta & 0x1) << 11)
            | ((tc_trig & 0x1) << 12)
            | ((breath_req & 0x1) << 13)
            | ((breath_eff & 0x1) << 14)
            | ((byp_pl & 0x1) << 15)
            | ((byp_raw & 0x1) << 16)
            | ((crop_x100 & 0xFF) << 17)
            | ((raw_fps_idx & 0x3F) << 25)
            | (1 << 31)
        )
        mb59 = 0x484C4741  # 'HLGA'
        return struct.pack("<4I", mb56, mb57, mb58, mb59)

    def _pack_phase123_mailbox_bytes(self) -> bytes:
        """Pack Phase 123 guest control mailbox mb[60..63] (16 bytes) matching fx6_live_guest.c."""
        p123 = self.get_uvc_srt_crsdk_ptp()
        uvc_req_idx = _UVC_MODE_TO_IDX.get(str(p123["uvc_mode"]), 0)
        uvc_eff_idx = _UVC_MODE_TO_IDX.get(str(p123["effective_uvc_mode"]), 0)
        usb2_non_ss = 1 if p123["usb_link_speed"] == "USB2_480M" else 0
        uvc_step = 1 if p123["uvc_usb2_stepdown_active"] else 0
        uac_en = 1 if p123["uac_audio_enabled"] else 0
        uvc_clean = 1 if p123["uvc_clean_feed_no_osd"] else 0
        uvc_fps = max(0, min(63, int(p123["uvc_fps"])))
        uvc_mbps = max(0, min(1023, int(p123["uvc_bitrate_mbps"])))
        uac_ch = max(0, min(15, int(p123["uac_channels"])))
        uvc_osd_blk = 1 if int(p123["uvc_osd_blocked_count"]) > 0 else 0

        mb60 = (
            (uvc_req_idx & 0x3)
            | ((uvc_eff_idx & 0x3) << 2)
            | ((usb2_non_ss & 0x1) << 4)
            | ((uvc_step & 0x1) << 5)
            | ((uac_en & 0x1) << 6)
            | ((uvc_clean & 0x1) << 7)
            | ((uvc_fps & 0x3F) << 8)
            | ((uvc_mbps & 0x3FF) << 14)
            | ((uac_ch & 0xF) << 24)
            | ((uvc_osd_blk & 0x1) << 28)
            | (1 << 31)
        )

        srt_idx = _SRT_MODE_TO_IDX.get(str(p123["srt_mode"]), 0)
        pk_idx = _SRT_PBKEY_TO_IDX.get(str(p123["srt_pbkeylen"]), 2)
        srt_lat = max(20, min(1000, int(p123["srt_latency_ms"])))
        rtmps_on = 1 if p123["rtmps_mode"] != "OFF" else 0
        stream_mbps = max(1, min(50, int(p123["stream_bitrate_mbps"])))
        p12_wlan_off = 1 if p123["p12_wlan_off"] else 0
        cdc_ncm_ok = 1
        p12_blk_cnt = max(0, min(127, int(p123["p12_blocked_count"])))
        arq_en = 1 if p123["srt_arq_enabled"] else 0

        mb61 = (
            (srt_idx & 0x3)
            | ((pk_idx & 0x3) << 2)
            | ((srt_lat & 0x3FF) << 4)
            | ((rtmps_on & 0x1) << 14)
            | ((stream_mbps & 0x3F) << 15)
            | ((p12_wlan_off & 0x1) << 21)
            | ((cdc_ncm_ok & 0x1) << 22)
            | ((p12_blk_cnt & 0x7F) << 23)
            | ((arq_en & 0x1) << 30)
            | (1 << 31)
        )

        ptp_idx = _CRSDK_PTP_TO_IDX.get(str(p123["crsdk_ptp_mode"]), 0)
        flash_blk = 1 if p123["ptp_flash_opcodes_blocked"] else 0
        emmc_zero = 1 if int(p123["emmc_mutation_bytes"]) == 0 else 0
        p12_ptp = 1 if p123["p12_wlan_off"] else 0
        p4_nd_clr = 1 if p123["p4_nd_clear_enforced"] else 0
        last_d2_low = int(self.p123_last_safe_opcode) & 0xFF
        blk_flash_cnt = max(0, min(127, int(p123["blocked_flash_opcode_count"])))
        safe_cmd_cnt = max(0, min(127, int(p123["crsdk_safe_cmd_count"])))
        action_kind = 5 if blk_flash_cnt > 0 else (4 if int(p123["crsdk_nd_clamp_count"]) > 0 else 0)

        mb62 = (
            (ptp_idx & 0x3)
            | ((flash_blk & 0x1) << 2)
            | ((emmc_zero & 0x1) << 3)
            | ((p12_ptp & 0x1) << 4)
            | ((p4_nd_clr & 0x1) << 5)
            | ((last_d2_low & 0xFF) << 6)
            | ((blk_flash_cnt & 0x7F) << 14)
            | ((safe_cmd_cnt & 0x7F) << 21)
            | ((action_kind & 0x7) << 28)
            | (1 << 31)
        )
        mb63 = 0x55564353  # 'UVCS'
        return struct.pack("<4I", mb60, mb61, mb62, mb63)

    def _write_ctrl_mailbox(self) -> bool:
        """Write mb[0..63] to guest physical 0x41e000e00 via serialized QEMU GDB stub and always resume VCPUs."""
        if not self.is_running() or not self.gdb_sock.exists() or not self.live_ready or self.crashed:
            return False
        raw = (
            self._pack_full_mailbox_bytes()
            + self._pack_phase73_mailbox_bytes()
            + self._pack_phase81_mailbox_bytes()
            + self._pack_phase88_mailbox_bytes()
            + self._pack_phase95_mailbox_bytes()
            + self._pack_phase102_mailbox_bytes()
            + self._pack_phase109_mailbox_bytes()
            + self._pack_phase116_mailbox_bytes()
            + self._pack_phase123_mailbox_bytes()
        )
        with self.gdb_lock:
            for _ in range(2):
                s: socket.socket | None = None
                interrupted = False
                try:
                    s = self._ensure_gdb()
                    if s is None:
                        return False
                    # Drain any stale async packets, interrupt running VCPUs cleanly, and ACK stop reply
                    self._gdb_drain_async(s, timeout=0.02)
                    s.sendall(b"\x03")
                    interrupted = True
                    self._gdb_wait_stop_reply(s, timeout=0.45)

                    s.settimeout(1.5)
                    self._gdb_send_packet(s, b"Qqemu.PhyMemMode:1")
                    # Write mb[3..18] first, then mb[0..2] so mb[1] (cmd_seq) commits last
                    body_hex = raw[12:].hex().encode("ascii")
                    r1 = self._gdb_send_packet(
                        s, f"M{CTRL_MB_PHYS + 12:x},{len(raw) - 12:x}:".encode("ascii") + body_hex
                    )
                    hdr_hex = raw[:12].hex().encode("ascii")
                    r2 = self._gdb_send_packet(
                        s, f"M{CTRL_MB_PHYS:x},c:".encode("ascii") + hdr_hex
                    )
                    if r1 == b"OK" and r2 == b"OK":
                        return True
                except Exception:
                    interrupted = False
                    if self.gdb_conn is not None:
                        try:
                            self.gdb_conn.close()
                        except Exception:
                            pass
                        self.gdb_conn = None
                    self._gdb_rx.clear()
                finally:
                    if interrupted and s is not None and self.gdb_conn is s:
                        try:
                            s.sendall(b"$c#63")
                            extra = self._gdb_drain_async(s, timeout=0.05)
                            if any(p[:1] in (b"T", b"S") for p in extra):
                                s.sendall(b"$c#63")
                                self._gdb_drain_async(s, timeout=0.03)
                            s.settimeout(1.5)
                        except Exception:
                            try:
                                s.close()
                            except Exception:
                                pass
                            self.gdb_conn = None
                            self._gdb_rx.clear()
        return False

    def _wait_for_frame_seq(self, target_seq: int, timeout: float = 3.2) -> bool:
        deadline = time.time() + timeout
        pat = re.compile(
            rf"FX6_LIVE_(?:READY|FRAME) seq={target_seq} page=(\d+) sel=(\d+) cat=(\d+) item=(\d+) depth=(\d+) nz=(\d+) text_ok=(\d+) fill=(\d+) icon=(\d+)(?: lang=(\d+))?"
        )
        while time.time() < deadline:
            if self.serial_log.exists():
                tail = self.serial_log.read_bytes()[-131072:].decode("latin1", errors="replace")
                if "APPFW_SEGV" in tail or "Entering exception monitor" in tail or "[Exception Syndrome]" in tail:
                    self.live_ready = False
                    self.crashed = True
                    for ln in reversed(tail.splitlines()):
                        if "APPFW_SEGV" in ln or "Abort (PC=" in ln or "Entering exception monitor" in ln:
                            self.crash_reason = ln.strip()
                            break
                    return False
                m = pat.search(tail)
                if m:
                    self.ack_seq = target_seq
                    self.last_nz = int(m.group(6))
                    self.last_text_ok = int(m.group(7))
                    self.last_fill_n = int(m.group(8))
                    self.last_icon_n = int(m.group(9))
                    self.live_ready = True
                    return True
            time.sleep(0.03)
        return False

    def _capture_live_gpe0_with_raw(self) -> tuple[bytes, bytes, int]:
        """Dump 0x41e001000 (0x21c000 bytes) via persistent QMP pmemsave and return (raw, png, nz)."""
        if not self.is_running() or not self.qmp_sock.exists():
            return self.last_raw_gpe0, self.last_png, self.last_nz
        with self.gpe_lock:
            for _ in range(2):
                try:
                    s = self._ensure_qmp()
                    if s is None:
                        break
                    try:
                        self.gpe0_bin.unlink()
                    except OSError:
                        pass
                    cmd = {
                        "execute": "pmemsave",
                        "arguments": {
                            "val": GPE0_PHYS,
                            "size": GPE0_BYTES,
                            "filename": str(self.gpe0_bin),
                        },
                    }
                    s.sendall((json.dumps(cmd) + "\n").encode("utf-8"))
                    s.recv(4096)
                    for _ in range(25):
                        if self.gpe0_bin.exists() and self.gpe0_bin.stat().st_size >= GPE0_BYTES:
                            break
                        time.sleep(0.02)
                    if self.gpe0_bin.exists() and self.gpe0_bin.stat().st_size >= GPE0_BYTES:
                        raw = self.gpe0_bin.read_bytes()
                        png, nz = gpe0_raw_to_png(raw)
                        if nz > 0 and png:
                            self.last_raw_gpe0 = raw[:GPE0_BYTES]
                            self.last_png = png
                            self.last_nz = nz
                            self.last_png_source = f"LIVE QEMU GPE0 @ 0x41e001000 (seq={self.ack_seq}, nz={nz})"
                            return self.last_raw_gpe0, png, nz
                    break
                except Exception:
                    if self.qmp_conn is not None:
                        try:
                            self.qmp_conn.close()
                        except Exception:
                            pass
                        self.qmp_conn = None
        return self.last_raw_gpe0, self.last_png, self.last_nz

    def capture_live_gpe0(self) -> tuple[bytes, int]:
        """Dump 0x41e001000 (0x21c000 bytes) via persistent QMP pmemsave and convert to PNG."""
        _, png, nz = self._capture_live_gpe0_with_raw()
        return png, nz

    @staticmethod
    def _normalize_lang(lang: Any) -> str | None:
        raw = str(lang or "").strip().lower()
        aliases = {
            "en": "en",
            "english": "en",
            "0": "en",
            "zh": "zh",
            "zh-cn": "zh",
            "zh_cn": "zh",
            "schinese": "zh",
            "simplifiedchinese": "zh",
            "cn": "zh",
            "1": "zh",
            "ja": "ja",
            "jp": "ja",
            "japanese": "ja",
            "2": "ja",
        }
        return aliases.get(raw)

    def set_lang(self, lang: Any) -> dict[str, Any]:
        with self.cmd_lock:
            code = self._normalize_lang(lang)
            packs = discover_available_lang_packs()
            if code is None or code not in packs:
                return {
                    "ok": False,
                    "error": f"Unsupported language: {lang!r}",
                    "available_langs": [k for k, v in packs.items() if v["available"]],
                }
            pack = packs[code]
            if not pack["available"]:
                return {
                    "ok": False,
                    "error": f"Language pack {code!r} missing donor assets",
                    "missing_files": pack["missing_files"],
                    "available_langs": [k for k, v in packs.items() if v["available"]],
                }
            self.lang_code = code
            self.lang_id = int(pack["id"])
            self.cmd_seq += 1
            wrote = self._write_ctrl_mailbox()
            synced = False
            if wrote:
                synced = self._wait_for_frame_seq(self.cmd_seq, timeout=3.2)
                self.capture_live_gpe0()
            return {
                "ok": True,
                "lang": self.lang_code,
                "lang_id": self.lang_id,
                "pack": pack,
                "wrote_mailbox": wrote,
                "guest_synced": synced,
                "status": self.get_status(),
            }

    @staticmethod
    def _normalize_bool(val: Any) -> bool | None:
        if isinstance(val, bool):
            return val
        if isinstance(val, int) and val in (0, 1):
            return bool(val)
        s = str(val or "").strip().lower()
        if s in ("1", "true", "yes", "on", "enable", "enabled", "attached"):
            return True
        if s in ("0", "false", "no", "off", "disable", "disabled", "detached"):
            return False
        return None

    @staticmethod
    def _normalize_rtmd_ibis(val: Any) -> str | None:
        raw = str(val or "").strip()
        if not raw:
            return None
        upper = raw.upper()
        if upper in RTMD_0XE304_MODES:
            return upper
        return RTMD_0XE304_ALIASES.get(raw.lower())

    @staticmethod
    def _normalize_lut_slot(slot: Any) -> str | None:
        s = str(slot or "User1").strip()
        low = s.lower().replace(" ", "")
        mapping = {
            "user1": "User1",
            "1": "User1",
            "user1(33³.cube)": "User1",
            "user2": "User2",
            "2": "User2",
            "user2(33³.cube)": "User2",
            "user3": "User3",
            "3": "User3",
            "user3(33³.cube)": "User3",
            "user4": "User4",
            "4": "User4",
            "user4(33³.cube)": "User4",
        }
        return mapping.get(low)

    def _effective_audio_route(self) -> tuple[str, str]:
        if not self.xlr_handle_attached:
            return ("INTERNAL_STEREO_FALLBACK", "Internal Stereo (P11 0x91db059b Fallback)")
        if self.xlr_idx == 2:
            return ("INTERNAL_STEREO", "Internal Stereo Mic")
        if self.xlr_phantom_48v or self.xlr_idx == 0:
            return ("XLR_H1_48V", "XLR-H1 Ch1/2 +48V (0x5d90)")
        return ("XLR_H1_LINE", "XLR-H1 Ch1/2 Line In (0x5d90)")

    def get_lut_slots(self) -> dict[str, Any]:
        lut_presets = CINEMA_PARAM_SPECS["lut"]["presets"]
        lut_idx = self.cell_vals[4] % len(lut_presets)
        active_slot = f"User{lut_idx - 3}" if lut_idx >= 4 else None
        return {
            "ok": True,
            "active_lut_index": lut_idx,
            "active_lut_preset": lut_presets[lut_idx],
            "active_user_slot": active_slot,
            "slots": {k: dict(v) for k, v in self.user_lut_slots.items()},
            "builtin_presets": list(BUILTIN_CUBE_PRESETS.values()),
        }

    def get_cinema_params(self) -> dict[str, Any]:
        ei_presets = CINEMA_PARAM_SPECS["ei"]["presets"]
        ei_idx = self.cell_vals[1] % len(ei_presets)
        base_iso = "12800" if ei_idx >= 3 else "800"
        ibis_presets = CINEMA_PARAM_SPECS["ibis"]["presets"]
        xlr_presets = CINEMA_PARAM_SPECS["xlr"]["presets"]
        effective_xlr_idx = 2 if not self.xlr_handle_attached else (self.xlr_idx % len(xlr_presets))
        indices = {
            "fps": self.cell_vals[0] % len(CINEMA_PARAM_SPECS["fps"]["presets"]),
            "ei": ei_idx,
            "shutter": self.cell_vals[2] % len(CINEMA_PARAM_SPECS["shutter"]["presets"]),
            "nd": 0,
            "lut": self.cell_vals[4] % len(CINEMA_PARAM_SPECS["lut"]["presets"]),
            "wb": self.cell_vals[5] % len(CINEMA_PARAM_SPECS["wb"]["presets"]),
            "ibis": self.ibis_idx % len(ibis_presets),
            "xlr": effective_xlr_idx,
        }
        values = {
            k: CINEMA_PARAM_SPECS[k]["presets"][idx]
            for k, idx in indices.items()
        }
        active_user_lut = None
        if indices["lut"] >= 4:
            slot_key = f"User{indices['lut'] - 3}"
            active_user_lut = dict(self.user_lut_slots[slot_key])
        audio_route, ch12_source = self._effective_audio_route()
        effective_48v = bool(self.xlr_handle_attached and self.xlr_phantom_48v and effective_xlr_idx != 2)
        return {
            "values": values,
            "indices": indices,
            "base_iso": base_iso,
            "nd_locked": True,
            "nd_lock_contract": "P4 set_nd_filter_mode_i -> Clear",
            "p4_lock_attempts": self.p4_lock_attempts,
            "p4_nd_reject_count": self.p4_nd_reject_count,
            "p12_bk4_airplane_mode_locked": True,
            "lut_source": "/dev/nflasha30 (0x0165/0x0166 33x33x33)",
            "active_user_lut": active_user_lut,
            "user_lut_slots": {k: dict(v) for k, v in self.user_lut_slots.items()},
            "ibis_status": values["ibis"],
            "rtmd_0xe304_ibis_lock": self.rtmd_0xe304_ibis_lock,
            "xlr_status": values["xlr"],
            "ch1_db": int(self.audio_ch_db[0]),
            "ch2_db": int(self.audio_ch_db[1]),
            "ch3_db": int(self.audio_ch_db[2]),
            "ch4_db": int(self.audio_ch_db[3]),
            "xlr_phantom_48v": effective_48v,
            "xlr_phantom_48v_setting": bool(self.xlr_phantom_48v),
            "xlr_handle_attached": bool(self.xlr_handle_attached),
            "audio_route": audio_route,
            "ch1_ch2_source": ch12_source,
            "ch3_ch4_active": bool(self.xlr_handle_attached),
            "p11_audio_fallback_contract": "0x91db059b",
            "specs": CINEMA_PARAM_SPECS,
        }

    def get_stage_b_telemetry(self) -> dict[str, Any]:
        cp = self.get_cinema_params()
        p10_btn = self.last_p10_telemetry.get("button")
        p10_detail = (
            f"{p10_btn}: {self.last_p10_telemetry.get('phy_code')}->{self.last_p10_telemetry.get('infra_code')}"
            if p10_btn
            else "FX3 Deck Ready (Fn/MENU/DISP/C1..C6)"
        )
        active_user = cp.get("active_user_lut")
        lut_detail = (
            f"/dev/nflasha30 -> {active_user['slot']}:{active_user['name']} ({active_user['tint_hex']})"
            if active_user and active_user.get("uploaded")
            else f"/dev/nflasha30 -> {cp['values']['lut']}"
        )
        return {
            "P1": {
                "id": "P1",
                "label": "P1 (/lut->p30)",
                "detail": lut_detail,
                "active": True,
                "active_user_lut": active_user,
                "user_lut_slots": cp["user_lut_slots"],
            },
            "P4": {
                "id": "P4",
                "label": "P4 (ND=Clear)",
                "detail": f"Clear [FX3 P4 Locked] (attempts={self.p4_lock_attempts}, rejects={self.p4_nd_reject_count})",
                "locked": True,
                "attempts": self.p4_lock_attempts,
                "p4_nd_reject_count": self.p4_nd_reject_count,
            },
            "P10": {
                "id": "P10",
                "label": "P10 (FX3 Keys)",
                "detail": p10_detail,
                "last_hwcode": f"0x{self.last_p10_hwcode:08x}",
            },
            "P11": {
                "id": "P11",
                "label": "P11 (Base ISO 800/12800 + 33³ LUT + XLR-H1 + IBIS Lock)",
                "detail": (
                    f"Base {cp['base_iso']} ({cp['values']['ei']}) | "
                    f"33³ LUT 0x0165/0x0166={cp['values']['lut']} | "
                    f"XLR-H1=0x5d90 ({cp['ch1_ch2_source']}, ch={self.audio_ch_db[0]}/{self.audio_ch_db[1]}/{self.audio_ch_db[2]}/{self.audio_ch_db[3]}dB) | "
                    f"RTMD 0xE304={self.rtmd_0xe304_ibis_lock}"
                ),
                "base_iso": cp["base_iso"],
                "xlr_handle": "0x5d90",
                "xlr_handle_attached": bool(self.xlr_handle_attached),
                "xlr_fallback_contract": "0x91db059b",
                "audio_route": cp["audio_route"],
                "ch1_ch2_source": cp["ch1_ch2_source"],
                "ch1_db": int(self.audio_ch_db[0]),
                "ch2_db": int(self.audio_ch_db[1]),
                "ch3_db": int(self.audio_ch_db[2]),
                "ch4_db": int(self.audio_ch_db[3]),
                "xlr_phantom_48v": cp["xlr_phantom_48v"],
                "ibis": cp["values"]["ibis"],
                "rtmd_0xe304_ibis_lock": self.rtmd_0xe304_ibis_lock,
                "lut_dma": "0x0165/0x0166",
            },
            "P12": {
                "id": "P12",
                "label": "P12 (WF-12 Safe)",
                "detail": "Direct O_RDONLY / LRU Pool / Bounded Write / BK4 Airplane Lock",
                "safe": True,
                "bk4_airplane_mode_locked": True,
            },
        }

    def _sync_mailbox_and_capture(self) -> tuple[bool, bool]:
        self.cmd_seq += 1
        wrote = self._write_ctrl_mailbox()
        synced = False
        if wrote:
            synced = self._wait_for_frame_seq(self.cmd_seq, timeout=3.2)
            self.capture_live_gpe0()
        return wrote, synced

    def _apply_flat_phase40_fields(self, body: dict[str, Any]) -> dict[str, Any]:
        """Validate & apply flat audio/RTMD fields (`ch1_db..ch4_db`, `xlr_phantom_48v`, `xlr_handle_attached`, `rtmd_0xe304_ibis_lock`)."""
        parsed_ch: dict[int, int] = {}
        for idx in range(4):
            k = f"ch{idx + 1}_db"
            if k in body and body[k] is not None:
                v = body[k]
                if isinstance(v, bool):
                    return {"ok": False, "error": "invalid_audio_db", "message": f"{k} cannot be bool"}
                try:
                    fv = float(v)
                except (TypeError, ValueError):
                    return {"ok": False, "error": "invalid_audio_db", "message": f"{k} must be numeric"}
                if not math.isfinite(fv):
                    return {"ok": False, "error": "invalid_audio_db", "message": f"{k} must be finite"}
                parsed_ch[idx] = max(-60, min(12, int(round(fv))))

        parsed_attached: bool | None = None
        if "xlr_handle_attached" in body and body["xlr_handle_attached"] is not None:
            parsed_attached = self._normalize_bool(body["xlr_handle_attached"])
            if parsed_attached is None:
                return {"ok": False, "error": "invalid_xlr_handle_attached", "message": "xlr_handle_attached must be boolean"}

        parsed_phantom: bool | None = None
        if "xlr_phantom_48v" in body and body["xlr_phantom_48v"] is not None:
            parsed_phantom = self._normalize_bool(body["xlr_phantom_48v"])
            if parsed_phantom is None:
                return {"ok": False, "error": "invalid_xlr_phantom_48v", "message": "xlr_phantom_48v must be boolean"}

        parsed_rtmd: str | None = None
        if "rtmd_0xe304_ibis_lock" in body and body["rtmd_0xe304_ibis_lock"] is not None:
            parsed_rtmd = self._normalize_rtmd_ibis(body["rtmd_0xe304_ibis_lock"])
            if parsed_rtmd is None:
                return {
                    "ok": False,
                    "error": "invalid_rtmd_0xe304_ibis_lock",
                    "message": f"Unsupported rtmd_0xe304_ibis_lock: {body['rtmd_0xe304_ibis_lock']!r}",
                    "allowed": list(RTMD_0XE304_MODES),
                }

        with self.cmd_lock:
            for idx, val in parsed_ch.items():
                self.audio_ch_db[idx] = val
            if parsed_phantom is not None:
                self.xlr_phantom_48v = parsed_phantom
                if self.xlr_handle_attached:
                    self.xlr_idx = 0 if parsed_phantom else 1
            if parsed_attached is not None:
                was_attached = self.xlr_handle_attached
                self.xlr_handle_attached = parsed_attached
                if not parsed_attached:
                    self.xlr_idx = 2  # P11 0x91db059b Internal Stereo fallback
                elif not was_attached and self.xlr_idx == 2:
                    self.xlr_idx = 0 if self.xlr_phantom_48v else 1
            if not self.xlr_handle_attached:
                self.xlr_idx = 2
            if parsed_rtmd is not None:
                self.rtmd_0xe304_ibis_lock = parsed_rtmd
                self.ibis_idx = RTMD_0XE304_MODES.index(parsed_rtmd)
                rtmd_to_p95 = {
                    "ACTIVE_5AXIS": "Active",
                    "OFF_CENTER_LOCKED": "Center_Lock_Gyroflow",
                    "STANDARD": "Standard",
                }
                self.ibis_mode = rtmd_to_p95.get(parsed_rtmd, self.ibis_mode)
            self.last_gyroflow_anamorphic_cmd = format_gyroflow_anamorphic_command(self.get_gyroflow_anamorphic())

            if not self.xlr_handle_attached:
                self.last_toast = "P11 0x91db059b: XLR-H1 detached -> CH1/2 auto-fallback to Internal Stereo Mic"
            else:
                self.last_toast = (
                    f"XLR-H1 CH1..4={self.audio_ch_db}dB (+48V={'ON' if self.xlr_phantom_48v else 'OFF'}) | "
                    f"RTMD 0xE304={self.rtmd_0xe304_ibis_lock}"
                )
            wrote, synced = self._sync_mailbox_and_capture()
            return {
                "ok": True,
                "param": "audio_rtmd",
                "toast": self.last_toast,
                "wrote_mailbox": wrote,
                "guest_synced": synced,
                "cinema_params": self.get_cinema_params(),
                "stage_b_telemetry": self.get_stage_b_telemetry(),
                "status": self.get_status(),
            }

    def set_cinema_param(
        self,
        param: Any = None,
        delta: Any = None,
        preset: Any = None,
        *,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if (param is None or str(param).strip() == "") and isinstance(payload, dict):
            if any(k in payload for k in AUDIO_PARAM_KEYS):
                return self._apply_flat_phase40_fields(payload)

        raw_param = str(param or "").strip().lower()
        # Support Phase 40 audio & RTMD params via set_cinema_param(param=..., delta=..., preset=...)
        phase40_alias = {
            "ch1_db": ("ch", 0),
            "ch2_db": ("ch", 1),
            "ch3_db": ("ch", 2),
            "ch4_db": ("ch", 3),
            "xlr_phantom_48v": ("phantom", None),
            "phantom_48v": ("phantom", None),
            "xlr_handle_attached": ("attached", None),
            "xlr_attached": ("attached", None),
            "rtmd_0xe304_ibis_lock": ("rtmd", None),
            "rtmd_ibis": ("rtmd", None),
            "ibis_lock": ("rtmd", None),
        }.get(raw_param)
        if phase40_alias is not None:
            kind, ch_idx = phase40_alias
            if kind == "ch" and ch_idx is not None:
                if preset is not None and str(preset).strip() != "":
                    if isinstance(preset, bool):
                        return {"ok": False, "error": "invalid_audio_db"}
                    try:
                        fv = float(preset)
                    except (TypeError, ValueError):
                        return {"ok": False, "error": f"Invalid dB value: {preset!r}"}
                    if not math.isfinite(fv):
                        return {"ok": False, "error": "Non-finite dB value"}
                    new_db = max(-60, min(12, int(round(fv))))
                else:
                    try:
                        step = int(delta) if delta is not None and str(delta).strip() != "" else 3
                    except Exception:
                        return {"ok": False, "error": f"Invalid delta {delta!r}"}
                    new_db = max(-60, min(12, self.audio_ch_db[ch_idx] + step))
                return self._apply_flat_phase40_fields({f"ch{ch_idx + 1}_db": new_db})
            if kind == "phantom":
                new_val = (not self.xlr_phantom_48v) if (preset is None or str(preset).strip() == "") else preset
                return self._apply_flat_phase40_fields({"xlr_phantom_48v": new_val})
            if kind == "attached":
                new_val = (not self.xlr_handle_attached) if (preset is None or str(preset).strip() == "") else preset
                return self._apply_flat_phase40_fields({"xlr_handle_attached": new_val})
            if kind == "rtmd":
                if preset is not None and str(preset).strip() != "":
                    return self._apply_flat_phase40_fields({"rtmd_0xe304_ibis_lock": preset})
                try:
                    step = int(delta) if delta is not None and str(delta).strip() != "" else 1
                except Exception:
                    return {"ok": False, "error": f"Invalid delta {delta!r}"}
                cur = RTMD_0XE304_MODES.index(self.rtmd_0xe304_ibis_lock) if self.rtmd_0xe304_ibis_lock in RTMD_0XE304_MODES else 0
                return self._apply_flat_phase40_fields({"rtmd_0xe304_ibis_lock": RTMD_0XE304_MODES[(cur + step) % len(RTMD_0XE304_MODES)]})

        key = CINEMA_PARAM_ALIASES.get(raw_param)
        if key is None or key not in CINEMA_PARAM_SPECS:
            return {
                "ok": False,
                "error": f"Unknown cinema param: {param!r}",
                "supported_params": list(CINEMA_PARAM_SPECS.keys()) + list(AUDIO_PARAM_KEYS),
            }
        spec = CINEMA_PARAM_SPECS[key]
        presets = list(spec["presets"])
        with self.cmd_lock:
            if key == "nd":
                self.cell_vals[3] = 0
                if self.page in (0, 3):
                    self.sel_box = 3
                self.p4_lock_attempts += 1
                self.last_toast = spec["lock_reason"]
                new_idx = 0
            else:
                cell_idx = spec["cell_idx"]
                if cell_idx is not None:
                    cur_idx = self.cell_vals[cell_idx] % len(presets)
                elif key == "ibis":
                    cur_idx = self.ibis_idx % len(presets)
                else:
                    cur_idx = self.xlr_idx % len(presets)

                if preset is not None and str(preset).strip() != "":
                    p_str = str(preset).strip()
                    p_low = p_str.lower()
                    matched_idx: int | None = None
                    for idx, cand in enumerate(presets):
                        if cand.lower() == p_low:
                            matched_idx = idx
                            break
                    if matched_idx is None:
                        for idx, cand in enumerate(presets):
                            c_low = cand.lower()
                            if c_low.startswith(p_low) or p_low in c_low:
                                matched_idx = idx
                                break
                    if matched_idx is None and isinstance(preset, int) and not isinstance(preset, bool):
                        if 0 <= preset < len(presets):
                            matched_idx = preset
                    if matched_idx is None and p_str.isdigit():
                        idx_num = int(p_str)
                        if 0 <= idx_num < len(presets):
                            matched_idx = idx_num
                    if matched_idx is None:
                        return {
                            "ok": False,
                            "error": f"Unknown preset {preset!r} for {key}",
                            "presets": presets,
                        }
                    new_idx = matched_idx
                else:
                    try:
                        step = int(delta) if delta is not None and str(delta).strip() != "" else 1
                    except Exception:
                        return {"ok": False, "error": f"Invalid delta {delta!r}"}
                    new_idx = (cur_idx + step) % len(presets)

                if cell_idx is not None:
                    self.cell_vals[cell_idx] = new_idx
                    if self.page in (0, 3):
                        self.sel_box = cell_idx
                    if key == "fps":
                        fps_map = [23.98, 24.0, 25.0, 29.97, 50.0, 59.94]
                        if new_idx == 6:
                            self.sq_enabled = True
                            self.sq_fps = 120
                            self.base_fps = 23.98
                            self.interval_rec_enabled = False
                        elif 0 <= new_idx < len(fps_map):
                            self.base_fps = fps_map[new_idx]
                            self.sq_enabled = False
                        self.last_cine_exp_cmd = format_cine_exp_command(self.get_cine_exposure())
                        self.last_touch_af_ciz_cmd = format_touch_focus_ciz_command(self.get_touch_focus_ciz())
                        self.last_gyroflow_anamorphic_cmd = format_gyroflow_anamorphic_command(self.get_gyroflow_anamorphic())
                        self.last_interval_cache_lut_ftp_cmd = format_interval_cache_lut_ftp_command(self.get_interval_cache_lut_ftp())
                        self.last_mc_fleet_sdi_c2pa_cmd = format_mc_fleet_sdi_c2pa_command(self.get_mc_fleet_sdi_c2pa())
                        self.last_hdr_hlg_raw_breathing_cmd = format_hdr_hlg_raw_breathing_command(self.get_hdr_hlg_raw_breathing())
                    elif key == "ei":
                        ei_map = [
                            ("800", 800),
                            ("800", 400),
                            ("800", 1600),
                            ("12800", 12800),
                            ("12800", 6400),
                            ("12800", 25600),
                        ]
                        if 0 <= new_idx < len(ei_map):
                            self.cine_ei_base, self.ei_index = ei_map[new_idx]
                            self.last_cine_exp_cmd = format_cine_exp_command(self.get_cine_exposure())
                            self.last_hdr_hlg_raw_breathing_cmd = format_hdr_hlg_raw_breathing_command(self.get_hdr_hlg_raw_breathing())
                            self.last_uvc_srt_crsdk_ptp_cmd = format_uvc_srt_crsdk_ptp_command(self.get_uvc_srt_crsdk_ptp())
                    elif key == "shutter":
                        shutter_map = [
                            ("angle", 180.0, None),
                            ("angle", 90.0, None),
                            ("angle", 45.0, None),
                            ("angle", 360.0, None),
                            ("speed", None, 48),
                            ("speed", None, 50),
                            ("speed", None, 100),
                        ]
                        if 0 <= new_idx < len(shutter_map):
                            sm, ang, den = shutter_map[new_idx]
                            self.shutter_mode = sm
                            if ang is not None:
                                self.shutter_angle_deg = ang
                            if den is not None:
                                self.shutter_speed_denom = den
                            self.last_cine_exp_cmd = format_cine_exp_command(self.get_cine_exposure())
                    elif key == "lut":
                        lut_look_map = [
                            "S-Cinetone",
                            "S-Log3 / S-Gamut3.Cine",
                            "ITU709",
                            "709(800%)",
                            "User 3D LUT",
                            "User 3D LUT",
                            "User 3D LUT",
                            "User 3D LUT",
                        ]
                        if 0 <= new_idx < len(lut_look_map):
                            self.base_look = lut_look_map[new_idx]
                            self.last_wb_media_cmd = format_wb_media_command(self.get_color_and_media())
                            self.last_touch_af_ciz_cmd = format_touch_focus_ciz_command(self.get_touch_focus_ciz())
                            self.last_interval_cache_lut_ftp_cmd = format_interval_cache_lut_ftp_command(self.get_interval_cache_lut_ftp())
                            self.last_mc_fleet_sdi_c2pa_cmd = format_mc_fleet_sdi_c2pa_command(self.get_mc_fleet_sdi_c2pa())
                            self.last_hdr_hlg_raw_breathing_cmd = format_hdr_hlg_raw_breathing_command(self.get_hdr_hlg_raw_breathing())
                            self.last_uvc_srt_crsdk_ptp_cmd = format_uvc_srt_crsdk_ptp_command(self.get_uvc_srt_crsdk_ptp())
                    elif key == "wb":
                        wb_cell_map = [
                            ("preset_5600k", 5600),
                            ("preset_4300k", 4300),
                            ("preset_3200k", 3200),
                            ("atw", None),
                            ("mem_a", None),
                            ("mem_b", None),
                        ]
                        if 0 <= new_idx < len(wb_cell_map):
                            self.wb_mode, preset_k = wb_cell_map[new_idx]
                            if preset_k is not None:
                                self.kelvin = preset_k
                            self.last_wb_media_cmd = format_wb_media_command(self.get_color_and_media())
                            self.last_hdr_hlg_raw_breathing_cmd = format_hdr_hlg_raw_breathing_command(self.get_hdr_hlg_raw_breathing())
                    self.last_toast = f"{spec['label']}: {presets[new_idx]} ({spec['contract']})"
                elif key == "ibis":
                    self.ibis_idx = new_idx
                    self.rtmd_0xe304_ibis_lock = RTMD_0XE304_MODES[new_idx % len(RTMD_0XE304_MODES)]
                    rtmd_to_p95 = {
                        "ACTIVE_5AXIS": "Active",
                        "OFF_CENTER_LOCKED": "Center_Lock_Gyroflow",
                        "STANDARD": "Standard",
                    }
                    self.ibis_mode = rtmd_to_p95.get(self.rtmd_0xe304_ibis_lock, self.ibis_mode)
                    self.last_gyroflow_anamorphic_cmd = format_gyroflow_anamorphic_command(self.get_gyroflow_anamorphic())
                    self.last_toast = f"{spec['label']}: {presets[new_idx]} (RTMD 0xE304={self.rtmd_0xe304_ibis_lock})"
                else:
                    if not self.xlr_handle_attached:
                        self.xlr_idx = 2
                        new_idx = 2
                        self.last_toast = "P11 0x91db059b: XLR-H1 detached -> CH1/2 auto-fallback to Internal Stereo Mic"
                    else:
                        self.xlr_idx = new_idx
                        self.xlr_phantom_48v = (new_idx == 0)
                        self.last_toast = f"{spec['label']}: {presets[new_idx]} ({spec['contract']})"

            wrote, synced = self._sync_mailbox_and_capture()
            return {
                "ok": True,
                "param": key,
                "index": new_idx,
                "value": presets[new_idx],
                "locked": bool(spec["locked"]),
                "toast": self.last_toast,
                "wrote_mailbox": wrote,
                "guest_synced": synced,
                "cinema_params": self.get_cinema_params(),
                "status": self.get_status(),
            }

    def upload_cube_lut(self, body: Any, *, allow_mini_grid: bool = False) -> dict[str, Any]:
        """Validate/sanitize `.cube` 3D LUT fail-closed, resample 17^3/33^3/65^3 -> 33^3 in volatile RAM, and sync guest GPE0."""
        if not isinstance(body, dict):
            return {"ok": False, "error": "invalid_request_body", "message": "Request body must be a JSON object"}

        slot = self._normalize_lut_slot(body.get("slot", "User1"))
        if slot is None:
            return {
                "ok": False,
                "error": "invalid_lut_slot",
                "message": f"Unsupported User LUT slot: {body.get('slot')!r} (expected User1..User4)",
            }

        preset_id = body.get("preset")
        cube_text = body.get("cube_text")
        req_name = str(body.get("name") or "").strip()

        if cube_text is None and preset_id is not None and str(preset_id).strip() != "":
            pid = str(preset_id).strip()
            if pid not in BUILTIN_CUBE_PRESETS:
                return {
                    "ok": False,
                    "error": "unknown_builtin_cube_preset",
                    "message": f"Unknown built-in .cube preset: {pid!r}",
                    "builtin_presets": list(BUILTIN_CUBE_PRESETS.keys()),
                }
            size_req = body.get("size", BUILTIN_CUBE_PRESETS[pid]["size"])
            try:
                size_int = int(size_req)
            except (TypeError, ValueError):
                return {"ok": False, "error": "invalid_lut_3d_size", "message": f"Invalid size {size_req!r}"}
            if size_int not in ({2, 17, 33, 65} if allow_mini_grid else {17, 33, 65}):
                return {
                    "ok": False,
                    "error": "unsupported_lut_3d_size",
                    "message": f"Unsupported built-in LUT size: {size_int}",
                }
            cube_text = generate_builtin_cube_lut(pid, size=size_int)
            if not req_name:
                req_name = BUILTIN_CUBE_PRESETS[pid]["name"]

        if cube_text is None:
            return {
                "ok": False,
                "error": "missing_cube_payload",
                "message": "Provide either 'cube_text' or built-in 'preset' (709_typeA, teal_orange, film_2383, slog3_bypass)",
            }

        sanitized = validate_and_sanitize_cube_lut(
            cube_text,
            name=req_name,
            allow_mini_grid=allow_mini_grid,
            include_33_table=True,
        )
        if not sanitized["ok"]:
            return sanitized

        table_33 = sanitized.pop("_table_33", [])
        slot_record = {
            "slot": slot,
            "name": sanitized["name"],
            "title": sanitized["title"],
            "uploaded": True,
            "preset": str(preset_id).strip() if preset_id else None,
            "size": sanitized["size"],
            "source_grid_size": sanitized["source_grid_size"],
            "target_grid_size": sanitized["target_grid_size"],
            "triplets": sanitized["triplets"],
            "resampled_33_triplets": sanitized["resampled_33_triplets"],
            "resampling_method": sanitized["resampling_method"],
            "clamped_components": sanitized["clamped_components"],
            "domain_min": sanitized["domain_min"],
            "domain_max": sanitized["domain_max"],
            "sha256": sanitized["sha256"],
            "resampled_33_sha256": sanitized["resampled_33_sha256"],
            "contrast_signature": sanitized["contrast_signature"],
            "mid_gray_rgb": sanitized["mid_gray_rgb"],
            "tint_rgb8": sanitized["tint_rgb8"],
            "tint_hex": sanitized["tint_hex"],
            "shadow_tint_rgb8": sanitized["shadow_tint_rgb8"],
            "highlight_tint_rgb8": sanitized["highlight_tint_rgb8"],
            "volatile_ram_only": True,
            "persistent_emmc_writes_authorized": False,
            "emmc_mutation_bytes": 0,
        }

        with self.cmd_lock:
            self.user_lut_slots[slot] = slot_record
            self._user_lut_33_ram_tables[slot] = list(table_33)
            cell_idx = USER_LUT_SLOT_TO_CELL_IDX[slot]
            self.cell_vals[4] = cell_idx
            self.base_look = "User 3D LUT"
            self.last_wb_media_cmd = format_wb_media_command(self.get_color_and_media())
            self.last_touch_af_ciz_cmd = format_touch_focus_ciz_command(self.get_touch_focus_ciz())
            p102 = self.get_interval_cache_lut_ftp()
            self.last_interval_cache_lut_ftp_cmd = format_interval_cache_lut_ftp_command(p102)
            self.last_mc_fleet_sdi_c2pa_cmd = format_mc_fleet_sdi_c2pa_command(self.get_mc_fleet_sdi_c2pa())
            self.last_hdr_hlg_raw_breathing_cmd = format_hdr_hlg_raw_breathing_command(self.get_hdr_hlg_raw_breathing())
            if self.page in (0, 3):
                self.sel_box = 4
            self.last_toast = (
                f"{slot} .cube Imported (RAM): {slot_record['title']} ({slot_record['source_grid_size']}³->33³ tetrahedral, "
                f"tint={slot_record['tint_hex']}, contrast={slot_record['contrast_signature']:.2f}, "
                f"sha33={slot_record['resampled_33_sha256'][:12]})"
            )
            wrote, synced = self._sync_mailbox_and_capture()
            return {
                "ok": True,
                "slot": slot,
                "lut_index": cell_idx,
                "lut": dict(slot_record),
                "resampled_33_sha256": slot_record["resampled_33_sha256"],
                "contrast_signature": slot_record["contrast_signature"],
                "volatile_ram_only": True,
                "persistent_emmc_writes_authorized": False,
                "emmc_mutation_bytes": 0,
                "interval_cache_lut_ftp": p102,
                "toast": self.last_toast,
                "wrote_mailbox": wrote,
                "guest_synced": synced,
                "cinema_params": self.get_cinema_params(),
                "status": self.get_status(),
            }

    def get_assist_tools(self) -> dict[str, str]:
        return {
            "aspect_marker": self.aspect_marker,
            "zebra_mode": self.zebra_mode,
            "peaking_mode": self.peaking_mode,
            "desqueeze": self.desqueeze,
        }

    def set_assist_tools(self, body: Any) -> dict[str, Any]:
        ok, updates, err = validate_assist_tools_patch(body)
        if not ok:
            return err or {"ok": False, "error": "invalid_assist_tools"}
        with self.cmd_lock:
            if "aspect_marker" in updates:
                self.aspect_marker = updates["aspect_marker"]
            if "zebra_mode" in updates:
                self.zebra_mode = updates["zebra_mode"]
            if "peaking_mode" in updates:
                self.peaking_mode = updates["peaking_mode"]
            if "desqueeze" in updates:
                self.desqueeze = updates["desqueeze"]
                self.squeeze_factor = _parse_desqueeze_factor_from_str(self.desqueeze)
            self.last_letterbox_ignored = False
            self.last_touch_af_ciz_cmd = format_touch_focus_ciz_command(self.get_touch_focus_ciz())
            self.last_gyroflow_anamorphic_cmd = format_gyroflow_anamorphic_command(self.get_gyroflow_anamorphic())
            self.last_toast = (
                f"Assist Tools: Marker={self.aspect_marker}, Zebra={self.zebra_mode}, "
                f"Peaking={self.peaking_mode}, Desqueeze={self.desqueeze}"
            )
            wrote, synced = self._sync_mailbox_and_capture()
            return {
                "ok": True,
                "assist_tools": self.get_assist_tools(),
                "toast": self.last_toast,
                "wrote_mailbox": wrote,
                "guest_synced": synced,
                "status": self.get_status(),
            }

    def get_cine_exposure(self) -> dict[str, Any]:
        lat = compute_cine_ei_latitude(self.cine_ei_base, self.ei_index)
        sq = compute_sq_motion_metrics(self.sq_enabled, self.base_fps, self.sq_fps)
        if self.shutter_mode == "speed":
            shutter_display = f"1/{self.shutter_speed_denom}"
        elif self.shutter_mode == "ecs":
            shutter_display = f"ECS {self.ecs_freq_hz:.2f}Hz"
        else:
            shutter_display = f"{self.shutter_angle_deg:.1f}\u00b0"
        f_rate = 25 if self.base_fps in (25.0, 50.0) else 24
        tc_total = int(self.rec_tc_frames)
        ff = tc_total % f_rate
        tot_s = tc_total // f_rate
        ss = tot_s % 60
        mm = (tot_s // 60) % 60
        hh = (tot_s // 3600) % 24
        rec_tc = f"{hh:02d}:{mm:02d}:{ss:02d}:{ff:02d}"
        rec_on = self.rec_state == "REC"
        tally_front_lit = rec_on and self.tally_lamp_mode in ("on", "front_only")
        tally_rear_lit = rec_on and self.tally_lamp_mode in ("on", "rear_only")
        state = {
            "cine_ei_base": self.cine_ei_base,
            "ei_index": int(self.ei_index),
            **lat,
            "shutter_mode": self.shutter_mode,
            "shutter_angle_deg": float(self.shutter_angle_deg),
            "shutter_speed_denom": int(self.shutter_speed_denom),
            "ecs_freq_hz": float(self.ecs_freq_hz),
            "shutter_display": shutter_display,
            "sq_enabled": bool(self.sq_enabled),
            "base_fps": float(self.base_fps),
            "sq_fps": int(self.sq_fps),
            **sq,
            "rec_state": self.rec_state,
            "tally_lamp_mode": self.tally_lamp_mode,
            "tally_front_lit": tally_front_lit,
            "tally_rear_lit": tally_rear_lit,
            "rec_tc_frames": tc_total,
            "rec_tc": rec_tc,
            "wired_io_mode": self.wired_io_mode,
            "wired_io_detail": build_wired_io_detail(self.wired_io_mode),
            "wifi_bt_rf_disabled": True,
            "p12_bk4_airplane_mode_locked": True,
            "nd_preset": "Clear",
            "p4_nd_hardware_absent": True,
        }
        state["cine_exp_cmd"] = format_cine_exp_command(state)
        return state

    def _apply_cine_exposure_updates_locked(self, updates: dict[str, Any]) -> None:
        if "cine_ei_base" in updates:
            self.cine_ei_base = str(updates["cine_ei_base"])
        if "ei_index" in updates:
            self.ei_index = int(updates["ei_index"])
        if "shutter_mode" in updates:
            self.shutter_mode = str(updates["shutter_mode"])
        if "shutter_angle_deg" in updates:
            self.shutter_angle_deg = float(updates["shutter_angle_deg"])
        if "shutter_speed_denom" in updates:
            self.shutter_speed_denom = int(updates["shutter_speed_denom"])
        if "ecs_freq_hz" in updates:
            self.ecs_freq_hz = float(updates["ecs_freq_hz"])
        if "sq_enabled" in updates:
            self.sq_enabled = bool(updates["sq_enabled"])
            if self.sq_enabled:
                self.interval_rec_enabled = False
        if "base_fps" in updates:
            self.base_fps = float(updates["base_fps"])
        if "sq_fps" in updates:
            self.sq_fps = int(updates["sq_fps"])
        if "rec_state" in updates:
            self.rec_state = str(updates["rec_state"])
            if self.rec_state == "STBY":
                self.gang_rec_trigger = False
            elif self.rec_state == "REC" and self.fleet_role != "Solo":
                self.gang_rec_trigger = True
        if "tally_lamp_mode" in updates:
            self.tally_lamp_mode = str(updates["tally_lamp_mode"])
        if "wired_io_mode" in updates:
            self.wired_io_mode = str(updates["wired_io_mode"])
        if "reset" in updates or (
            updates.get("rec_state") == "STBY" and self.rec_state == "STBY" and len(updates) == len(CINE_EXPOSURE_DEFAULTS)
        ):
            self.rec_tc_frames = 0
        elif self.rec_state == "REC":
            self.rec_tc_frames += 1

        # Keep Big-6 cells aligned when matching standard presets
        if self.sq_enabled and self.sq_fps >= 100:
            self.cell_vals[0] = 6  # 119.88p (S&Q)
        else:
            fps_map = {23.98: 0, 24.0: 1, 25.0: 2, 29.97: 3, 50.0: 4, 59.94: 5}
            self.cell_vals[0] = fps_map.get(round(self.base_fps, 2), 0)
        ei_map = {800: 0, 400: 1, 1600: 2, 12800: 3, 6400: 4, 25600: 5}
        if self.ei_index in ei_map:
            self.cell_vals[1] = ei_map[self.ei_index]
        elif self.cine_ei_base == "12800":
            self.cell_vals[1] = 3
        else:
            self.cell_vals[1] = 0
        self.cell_vals[3] = 0  # P4 ND=Clear Hardware Lock
        self.p12_bk4_airplane_mode_locked = True
        self.last_cine_exp_cmd = format_cine_exp_command(self.get_cine_exposure())
        self.last_wb_media_cmd = format_wb_media_command(self.get_color_and_media())
        self.last_touch_af_ciz_cmd = format_touch_focus_ciz_command(self.get_touch_focus_ciz())
        self.last_shotmark_iris_cmd = format_shotmark_iris_command(self.get_shotmark_and_iris())
        self.last_gyroflow_anamorphic_cmd = format_gyroflow_anamorphic_command(self.get_gyroflow_anamorphic())
        self.last_interval_cache_lut_ftp_cmd = format_interval_cache_lut_ftp_command(self.get_interval_cache_lut_ftp())
        self.last_mc_fleet_sdi_c2pa_cmd = format_mc_fleet_sdi_c2pa_command(self.get_mc_fleet_sdi_c2pa())
        if "wired_io_mode" in updates and str(updates["wired_io_mode"]).lower() != "hdmi_raw16":
            self.ext_raw_mode = "OFF"
        elif "wired_io_mode" in updates and str(updates["wired_io_mode"]).lower() == "hdmi_raw16" and self.ext_raw_mode == "OFF":
            self.ext_raw_mode = "Atomos_ProRes_RAW_16_12L"
        self.last_hdr_hlg_raw_breathing_cmd = format_hdr_hlg_raw_breathing_command(self.get_hdr_hlg_raw_breathing())
        self.last_uvc_srt_crsdk_ptp_cmd = format_uvc_srt_crsdk_ptp_command(self.get_uvc_srt_crsdk_ptp())

    def set_cine_exposure(self, body: Any) -> dict[str, Any]:
        with self.cmd_lock:
            cur = {
                "cine_ei_base": self.cine_ei_base,
                "ei_index": self.ei_index,
                "shutter_mode": self.shutter_mode,
                "shutter_angle_deg": self.shutter_angle_deg,
                "shutter_speed_denom": self.shutter_speed_denom,
                "ecs_freq_hz": self.ecs_freq_hz,
                "sq_enabled": self.sq_enabled,
                "base_fps": self.base_fps,
                "sq_fps": self.sq_fps,
                "rec_state": self.rec_state,
                "tally_lamp_mode": self.tally_lamp_mode,
                "wired_io_mode": self.wired_io_mode,
            }
            ok, updates, err = validate_cine_exposure_patch(body, current_state=cur)
            if not ok:
                if err and err.get("error") == "p4_nd_hardware_absent":
                    self.cell_vals[3] = 0
                    self.p4_lock_attempts += 1
                    self.p4_nd_reject_count += 1
                    self.last_toast = str(err.get("message", "Stage-B P4 ND=Clear Hardware Lock"))
                return err or {"ok": False, "error": "invalid_cine_exposure"}

            self._apply_cine_exposure_updates_locked(updates)
            ce = self.get_cine_exposure()
            self.last_toast = (
                f"CineExposure: {ce['rec_state']} | {ce['ei_index']}EI (B{ce['cine_ei_base']} {ce['latitude_label']}) | "
                f"{ce['shutter_display']} | "
                f"{('S&Q ' + str(ce['sq_fps']) + 'fps ' + ce['motion_label']) if ce['sq_enabled'] else str(ce['base_fps']) + 'p'} | "
                f"IO={ce['wired_io_mode']}"
            )
            wrote, synced = self._sync_mailbox_and_capture()
            return {
                "ok": True,
                "cine_exposure": ce,
                "cine_exp_cmd": ce["cine_exp_cmd"],
                "p4_nd_hardware_absent": True,
                "wifi_bt_rf_disabled": True,
                "toast": self.last_toast,
                "wrote_mailbox": wrote,
                "guest_synced": synced,
                "status": self.get_status(),
            }

    def _active_user_lut_for_color(self) -> dict[str, Any] | None:
        lut_idx = self.cell_vals[4] % len(CINEMA_PARAM_SPECS["lut"]["presets"])
        if lut_idx >= 4:
            slot_key = f"User{lut_idx - 3}"
            return dict(self.user_lut_slots[slot_key])
        if self.base_look == "User 3D LUT":
            for slot_key in USER_LUT_SLOTS:
                if self.user_lut_slots[slot_key].get("uploaded"):
                    return dict(self.user_lut_slots[slot_key])
            return dict(self.user_lut_slots["User1"])
        return None

    def get_color_and_media(self) -> dict[str, Any]:
        state = compute_color_and_media_derived(
            {
                "wb_mode": self.wb_mode,
                "kelvin": self.kelvin,
                "tint_gm": self.tint_gm,
                "shockless_wb": self.shockless_wb,
                "base_look": self.base_look,
                "cam_id": self.cam_id,
                "reel_num": self.reel_num,
                "cam_pos": self.cam_pos,
                "clip_seq": self.clip_seq,
                "dual_slot_mode": self.dual_slot_mode,
                "proxy_mode": self.proxy_mode,
            },
            sq_enabled=self.sq_enabled,
            active_user_lut=self._active_user_lut_for_color(),
        )
        state["wb_media_cmd"] = format_wb_media_command(state)
        return state

    def _apply_color_and_media_updates_locked(self, updates: dict[str, Any]) -> None:
        if "wb_mode" in updates:
            self.wb_mode = str(updates["wb_mode"])
        if "kelvin" in updates:
            self.kelvin = int(updates["kelvin"])
        if "tint_gm" in updates:
            self.tint_gm = int(updates["tint_gm"])
        if "shockless_wb" in updates:
            self.shockless_wb = str(updates["shockless_wb"])
        if "base_look" in updates:
            self.base_look = str(updates["base_look"])
        if "cam_id" in updates:
            self.cam_id = str(updates["cam_id"])
        if "reel_num" in updates:
            self.reel_num = int(updates["reel_num"])
        if "cam_pos" in updates:
            self.cam_pos = str(updates["cam_pos"])
        if "clip_seq" in updates:
            self.clip_seq = int(updates["clip_seq"])
        if "dual_slot_mode" in updates:
            self.dual_slot_mode = str(updates["dual_slot_mode"])
        if "proxy_mode" in updates:
            self.proxy_mode = str(updates["proxy_mode"])

        wb_to_cell = {
            "preset_5600k": 0,
            "preset_4300k": 1,
            "preset_3200k": 2,
            "atw": 3,
            "mem_a": 4,
            "mem_b": 5,
        }
        if self.wb_mode in wb_to_cell:
            self.cell_vals[5] = wb_to_cell[self.wb_mode]

        if "user_lut_slot" in updates and updates["user_lut_slot"] in USER_LUT_SLOT_TO_CELL_IDX:
            self.cell_vals[4] = USER_LUT_SLOT_TO_CELL_IDX[updates["user_lut_slot"]]
        elif "base_look" in updates:
            if self.base_look == "User 3D LUT":
                if (self.cell_vals[4] % 8) < 4:
                    self.cell_vals[4] = 4
            elif self.base_look in BASE_LOOK_NLE_TAGS:
                self.cell_vals[4] = int(BASE_LOOK_NLE_TAGS[self.base_look]["cell_lut_idx"])

        self.last_wb_media_cmd = format_wb_media_command(self.get_color_and_media())
        self.last_touch_af_ciz_cmd = format_touch_focus_ciz_command(self.get_touch_focus_ciz())
        self.last_shotmark_iris_cmd = format_shotmark_iris_command(self.get_shotmark_and_iris())
        self.last_mc_fleet_sdi_c2pa_cmd = format_mc_fleet_sdi_c2pa_command(self.get_mc_fleet_sdi_c2pa())
        self.last_hdr_hlg_raw_breathing_cmd = format_hdr_hlg_raw_breathing_command(self.get_hdr_hlg_raw_breathing())
        self.last_uvc_srt_crsdk_ptp_cmd = format_uvc_srt_crsdk_ptp_command(self.get_uvc_srt_crsdk_ptp())

    def set_color_and_media(self, body: Any) -> dict[str, Any]:
        with self.cmd_lock:
            cur = {
                "wb_mode": self.wb_mode,
                "kelvin": self.kelvin,
                "tint_gm": self.tint_gm,
                "shockless_wb": self.shockless_wb,
                "base_look": self.base_look,
                "cam_id": self.cam_id,
                "reel_num": self.reel_num,
                "cam_pos": self.cam_pos,
                "clip_seq": self.clip_seq,
                "dual_slot_mode": self.dual_slot_mode,
                "proxy_mode": self.proxy_mode,
            }
            ok, updates, err = validate_color_and_media_patch(body, current_state=cur)
            if not ok:
                return err or {"ok": False, "error": "invalid_color_and_media"}

            self._apply_color_and_media_updates_locked(updates)
            cm = self.get_color_and_media()
            prx_note = "PRX:OFF(S&Q)" if cm["proxy_auto_suspended_by_sq"] else (
                "PRX:ON" if cm["proxy_effective_active"] else "PRX:OFF"
            )
            self.last_toast = (
                f"ColorMedia: {cm['wb_display']} ({cm['wb_mode']}, SL={cm['shockless_wb']}) | "
                f"{cm['base_look']} ({cm['capture_gamma_equation']}/{cm['capture_color_primaries']}) | "
                f"{cm['main_clip_name']} [{cm['dual_slot_mode']}] {prx_note}"
            )
            wrote, synced = self._sync_mailbox_and_capture()
            return {
                "ok": True,
                "color_and_media": cm,
                "wb_media_cmd": cm["wb_media_cmd"],
                "fx3_wb_switch_soft_mapped": True,
                "toast": self.last_toast,
                "wrote_mailbox": wrote,
                "guest_synced": synced,
                "status": self.get_status(),
            }

    def get_xml_sidecar(self) -> dict[str, Any]:
        with self.cmd_lock:
            ce = self.get_cine_exposure()
            cm = self.get_color_and_media()
            smi = self.get_shotmark_and_iris()
            ga = self.get_gyroflow_anamorphic()
            ic = self.get_interval_cache_lut_ftp()
            p109 = self.get_mc_fleet_sdi_c2pa()
            p116 = self.get_hdr_hlg_raw_breathing()
            p123 = self.get_uvc_srt_crsdk_ptp()
            active_user = self._active_user_lut_for_color()
        xml_text = build_nrtm_xml_sidecar(
            ce,
            cm,
            active_user_lut=active_user,
            shotmark_and_iris=smi,
            gyroflow_anamorphic=ga,
            interval_cache_lut_ftp=ic,
            mc_fleet_sdi_c2pa=p109,
            hdr_hlg_raw_breathing=p116,
            uvc_srt_crsdk_ptp=p123,
        )
        return {
            "ok": True,
            "filename": cm["sidecar_xml_name"],
            "main_clip_name": cm["main_clip_name"],
            "proxy_clip_name": cm["proxy_active_clip_name"],
            "nrtm_namespace": NRTM_NAMESPACE_V220,
            "content_type": "application/xml; charset=utf-8",
            "c2pa_spoofed": False,
            "persistent_emmc_writes_authorized": False,
            "xml_sha256": hashlib.sha256(xml_text.encode("utf-8")).hexdigest(),
            "xml": xml_text,
            "color_and_media": cm,
            "cine_exposure": ce,
            "shotmark_and_iris": smi,
            "gyroflow_anamorphic": ga,
            "interval_cache_lut_ftp": ic,
            "mc_fleet_sdi_c2pa": p109,
            "hdr_hlg_raw_breathing": p116,
            "uvc_srt_crsdk_ptp": p123,
        }

    def get_mc_fleet_sdi_c2pa(self) -> dict[str, Any]:
        ce = self.get_cine_exposure()
        state = compute_mc_fleet_sdi_c2pa_derived(
            {
                "fleet_role": self.fleet_role,
                "fleet_cams_online": self.fleet_cams_online,
                "fleet_nic_driver": self.fleet_nic_driver,
                "gang_rec_trigger": self.gang_rec_trigger,
                "sdi_bridge_converter": self.sdi_bridge_converter,
                "hdmi_rec_control_enabled": self.hdmi_rec_control_enabled,
                "hdmi_tc_output_enabled": self.hdmi_tc_output_enabled,
                "recorder_range_expectation": self.recorder_range_expectation,
                "mount_type": self.mount_type,
                "lens_model": self.lens_model,
                "lens_kg": self.lens_kg,
                "focal_length_mm": self.focal_length_mm,
                "rod_support_15mm_lws": self.rod_support_15mm_lws,
            },
            rec_state=self.rec_state,
            rec_tc=ce["rec_tc"],
            base_fps=self.base_fps,
            base_look=self.base_look,
            wired_io_mode=self.wired_io_mode,
            c2pa_blocked_attempts=self.c2pa_blocked_attempts,
            c2pa_last_blocked_reason=self.c2pa_last_blocked_reason,
            wf12_00342260_hits=self.wf12_00342260_hits,
        )
        state["mc_fleet_sdi_c2pa_cmd"] = format_mc_fleet_sdi_c2pa_command(state)
        return state

    def _apply_mc_fleet_sdi_c2pa_updates_locked(
        self,
        updates: dict[str, Any],
        *,
        is_reset: bool = False,
        preserve_rec_state: bool = False,
    ) -> None:
        if is_reset:
            self.c2pa_blocked_attempts = 0
            self.c2pa_last_blocked_reason = None
        if "fleet_role" in updates:
            self.fleet_role = str(updates["fleet_role"])
        if "fleet_cams_online" in updates:
            self.fleet_cams_online = int(updates["fleet_cams_online"])
        if "fleet_nic_driver" in updates:
            self.fleet_nic_driver = str(updates["fleet_nic_driver"])
        if "gang_rec_trigger" in updates:
            self.gang_rec_trigger = bool(updates["gang_rec_trigger"])
            if self.gang_rec_trigger:
                self.rec_state = "REC"
                if not preserve_rec_state:
                    self.rec_tc_frames += 1
            elif not preserve_rec_state:
                self.rec_state = "STBY"
        if "sdi_bridge_converter" in updates:
            self.sdi_bridge_converter = str(updates["sdi_bridge_converter"])
        if "hdmi_rec_control_enabled" in updates:
            self.hdmi_rec_control_enabled = bool(updates["hdmi_rec_control_enabled"])
        if "hdmi_tc_output_enabled" in updates:
            self.hdmi_tc_output_enabled = bool(updates["hdmi_tc_output_enabled"])
        if "recorder_range_expectation" in updates:
            self.recorder_range_expectation = str(updates["recorder_range_expectation"])
        if "mount_type" in updates:
            self.mount_type = str(updates["mount_type"])
        if "lens_model" in updates:
            self.lens_model = str(updates["lens_model"])
        if "lens_kg" in updates:
            self.lens_kg = float(updates["lens_kg"])
        if "focal_length_mm" in updates:
            self.focal_length_mm = int(updates["focal_length_mm"])
        if "rod_support_15mm_lws" in updates:
            self.rod_support_15mm_lws = bool(updates["rod_support_15mm_lws"])

        self.wf12_00342260_hits = 0
        self.p12_bk4_airplane_mode_locked = True
        self.last_cine_exp_cmd = format_cine_exp_command(self.get_cine_exposure())
        self.last_wb_media_cmd = format_wb_media_command(self.get_color_and_media())
        self.last_touch_af_ciz_cmd = format_touch_focus_ciz_command(self.get_touch_focus_ciz())
        self.last_shotmark_iris_cmd = format_shotmark_iris_command(self.get_shotmark_and_iris())
        self.last_gyroflow_anamorphic_cmd = format_gyroflow_anamorphic_command(self.get_gyroflow_anamorphic())
        self.last_interval_cache_lut_ftp_cmd = format_interval_cache_lut_ftp_command(self.get_interval_cache_lut_ftp())
        self.last_mc_fleet_sdi_c2pa_cmd = format_mc_fleet_sdi_c2pa_command(self.get_mc_fleet_sdi_c2pa())
        self.last_hdr_hlg_raw_breathing_cmd = format_hdr_hlg_raw_breathing_command(self.get_hdr_hlg_raw_breathing())

    def set_mc_fleet_sdi_c2pa(self, body: Any) -> dict[str, Any]:
        with self.cmd_lock:
            cur = {
                "fleet_role": self.fleet_role,
                "fleet_cams_online": self.fleet_cams_online,
                "fleet_nic_driver": self.fleet_nic_driver,
                "gang_rec_trigger": self.gang_rec_trigger,
                "sdi_bridge_converter": self.sdi_bridge_converter,
                "hdmi_rec_control_enabled": self.hdmi_rec_control_enabled,
                "hdmi_tc_output_enabled": self.hdmi_tc_output_enabled,
                "recorder_range_expectation": self.recorder_range_expectation,
                "mount_type": self.mount_type,
                "lens_model": self.lens_model,
                "lens_kg": self.lens_kg,
                "focal_length_mm": self.focal_length_mm,
                "rod_support_15mm_lws": self.rod_support_15mm_lws,
            }
            ok, updates, err = validate_mc_fleet_sdi_c2pa_patch(
                body,
                current_state=cur,
                base_look=self.base_look,
                wired_io_mode=self.wired_io_mode,
            )
            if not ok:
                if err and err.get("error") == "c2pa_cnflasha_zero_touch_blocked":
                    self.c2pa_blocked_attempts += 1
                    self.c2pa_last_blocked_reason = str(err.get("message", "cnflasha zero-touch blocked"))
                    self.last_toast = self.c2pa_last_blocked_reason
                    self.last_mc_fleet_sdi_c2pa_cmd = format_mc_fleet_sdi_c2pa_command(self.get_mc_fleet_sdi_c2pa())
                    self._sync_mailbox_and_capture()
                    err["c2pa_blocked_attempts"] = self.c2pa_blocked_attempts
                    err["mc_fleet_sdi_c2pa"] = self.get_mc_fleet_sdi_c2pa()
                return err or {"ok": False, "error": "invalid_mc_fleet_sdi_c2pa"}

            is_reset = isinstance(body, dict) and body.get("reset") is True
            self._apply_mc_fleet_sdi_c2pa_updates_locked(updates, is_reset=is_reset)
            p109 = self.get_mc_fleet_sdi_c2pa()
            self.last_toast = (
                f"Phase109: {p109['fleet_role']}({p109['fleet_cams_online']}/4,GANG={'REC' if p109['gang_rec_trigger'] else 'STBY'}) | "
                f"SDI={p109['sdi_bridge_converter']}(RP188={p109['rp188_rec_trigger_bit']},CS={p109['avi_checksum_hex']}) | "
                f"Mount={p109['mount_type']}({p109['vignetting_comp_gain']:.2f}x) | C2PA={p109['c2pa_vault_status']}"
            )
            wrote, synced = self._sync_mailbox_and_capture()
            return {
                "ok": True,
                "mc_fleet_sdi_c2pa": p109,
                "mc_fleet_sdi_c2pa_cmd": p109["mc_fleet_sdi_c2pa_cmd"],
                "wf12_00342260_hits": 0,
                "c2pa_vault_status": p109["c2pa_vault_status"],
                "private_key_reads": 0,
                "cnflasha_writes": 0,
                "toast": self.last_toast,
                "wrote_mailbox": wrote,
                "guest_synced": synced,
                "status": self.get_status(),
            }

    def get_hdr_hlg_raw_breathing(self) -> dict[str, Any]:
        state = compute_hdr_hlg_raw_breathing_derived(
            {
                "hlg_profile": self.hlg_profile,
                "color_gamut": self.color_gamut,
                "knee_mode": self.knee_mode,
                "detail_level": self.detail_level,
                "display_assist_mode": self.display_assist_mode,
                "ext_raw_mode": self.ext_raw_mode,
                "breathing_comp_mode": self.breathing_comp_mode,
            },
            base_look=self.base_look,
            cine_ei_base=self.cine_ei_base,
            kelvin=self.kelvin,
            base_fps=self.base_fps,
            wired_io_mode=self.wired_io_mode,
            mount_type=self.mount_type,
            lens_model=self.lens_model,
            focal_length_mm=self.focal_length_mm,
            iris_fstop=self.iris_fstop,
            assist_leak_blocked_count=self.p116_assist_leak_blocked_count,
            bt2020_in_bt709_blocked_count=self.p116_bt2020_blocked_count,
        )
        state["hdr_hlg_raw_breathing_cmd"] = format_hdr_hlg_raw_breathing_command(state)
        return state

    def _apply_hdr_hlg_raw_breathing_updates_locked(
        self,
        updates: dict[str, Any],
        *,
        is_reset: bool = False,
        preserve_wired_io: bool = False,
    ) -> None:
        if is_reset:
            self.p116_assist_leak_blocked_count = 0
            self.p116_bt2020_blocked_count = 0
        if "hlg_profile" in updates:
            self.hlg_profile = str(updates["hlg_profile"])
        if "color_gamut" in updates:
            self.color_gamut = str(updates["color_gamut"])
        if "knee_mode" in updates:
            self.knee_mode = str(updates["knee_mode"])
        if "detail_level" in updates:
            self.detail_level = int(updates["detail_level"])
        if "display_assist_mode" in updates:
            self.display_assist_mode = str(updates["display_assist_mode"])
        if "ext_raw_mode" in updates:
            self.ext_raw_mode = str(updates["ext_raw_mode"])
            if not preserve_wired_io:
                if self.ext_raw_mode != "OFF":
                    self.wired_io_mode = "hdmi_raw16"
                elif self.wired_io_mode == "hdmi_raw16":
                    self.wired_io_mode = "off"
        if "breathing_comp_mode" in updates:
            self.breathing_comp_mode = str(updates["breathing_comp_mode"])

        self.last_cine_exp_cmd = format_cine_exp_command(self.get_cine_exposure())
        self.last_mc_fleet_sdi_c2pa_cmd = format_mc_fleet_sdi_c2pa_command(self.get_mc_fleet_sdi_c2pa())
        self.last_hdr_hlg_raw_breathing_cmd = format_hdr_hlg_raw_breathing_command(self.get_hdr_hlg_raw_breathing())

    def set_hdr_hlg_raw_breathing(self, body: Any) -> dict[str, Any]:
        with self.cmd_lock:
            cur = {
                "hlg_profile": self.hlg_profile,
                "color_gamut": self.color_gamut,
                "knee_mode": self.knee_mode,
                "detail_level": self.detail_level,
                "display_assist_mode": self.display_assist_mode,
                "ext_raw_mode": self.ext_raw_mode,
                "breathing_comp_mode": self.breathing_comp_mode,
            }
            ok, updates, err = validate_hdr_hlg_raw_breathing_patch(
                body,
                current_state=cur,
                mount_type=self.mount_type,
                wired_io_mode=self.wired_io_mode,
            )
            if not ok:
                err_code = (err or {}).get("error")
                if err_code == "display_assist_clean_feed_leak_blocked":
                    self.p116_assist_leak_blocked_count += 1
                    self.last_toast = str(err.get("message", "Display Assist clean-feed isolation enforced"))
                    self.last_hdr_hlg_raw_breathing_cmd = format_hdr_hlg_raw_breathing_command(self.get_hdr_hlg_raw_breathing())
                    self._sync_mailbox_and_capture()
                    err["assist_leak_blocked_count"] = self.p116_assist_leak_blocked_count
                    err["hdr_hlg_raw_breathing"] = self.get_hdr_hlg_raw_breathing()
                elif err_code == "bt2020_in_bt709_container_blocked":
                    self.p116_bt2020_blocked_count += 1
                    self.last_toast = str(err.get("message", "BT.2020-in-BT.709 container blocked"))
                    self.last_hdr_hlg_raw_breathing_cmd = format_hdr_hlg_raw_breathing_command(self.get_hdr_hlg_raw_breathing())
                    self._sync_mailbox_and_capture()
                    err["bt2020_in_bt709_blocked_count"] = self.p116_bt2020_blocked_count
                    err["hdr_hlg_raw_breathing"] = self.get_hdr_hlg_raw_breathing()
                return err or {"ok": False, "error": "invalid_hdr_hlg_raw_breathing"}

            is_reset = isinstance(body, dict) and body.get("reset") is True
            self._apply_hdr_hlg_raw_breathing_updates_locked(updates, is_reset=is_reset)
            p116 = self.get_hdr_hlg_raw_breathing()
            self.last_toast = (
                f"Phase116: HLG={p116['hlg_profile']}({p116['color_gamut']},{p116['peak_nits']}nit,87:CS={p116['cta_checksum_hex']}) | "
                f"Assist={p116['resolved_assist_mode']}(CleanHDMI=1) | "
                f"RAW={p116['ext_raw_mode']} | FBC={p116['breathing_crop_factor']:.2f}x"
            )
            wrote, synced = self._sync_mailbox_and_capture()
            return {
                "ok": True,
                "hdr_hlg_raw_breathing": p116,
                "hdr_hlg_raw_breathing_cmd": p116["hdr_hlg_raw_breathing_cmd"],
                "clean_hdmi_sdi_unassisted": True,
                "xavc_internal_unassisted": True,
                "external_output_assist_leak_px": 0,
                "toast": self.last_toast,
                "wrote_mailbox": wrote,
                "guest_synced": synced,
                "status": self.get_status(),
            }

    def get_uvc_srt_crsdk_ptp(self) -> dict[str, Any]:
        state = compute_uvc_srt_crsdk_ptp_derived(
            {
                "uvc_mode": self.uvc_mode,
                "usb_link_speed": self.usb_link_speed,
                "uac_audio_enabled": self.uac_audio_enabled,
                "srt_mode": self.srt_mode,
                "srt_pbkeylen": self.srt_pbkeylen,
                "srt_latency_ms": self.srt_latency_ms,
                "rtmps_mode": self.rtmps_mode,
                "stream_bitrate_mbps": self.stream_bitrate_mbps,
                "crsdk_ptp_mode": self.crsdk_ptp_mode,
            },
            cine_ei_base=self.cine_ei_base,
            ei_index=self.ei_index,
            base_look=self.base_look,
            nd_preset="Clear [FX3 P4 Locked]",
            last_safe_opcode=self.p123_last_safe_opcode,
            safe_cmd_count=self.p123_safe_cmd_count,
            flash_blocked_count=self.p123_flash_blocked_count,
            last_blocked_opcode=self.p123_last_blocked_opcode,
            p12_blocked_count=self.p123_p12_blocked_count,
            uvc_osd_blocked_count=self.p123_uvc_osd_blocked_count,
            crsdk_nd_clamp_count=self.p123_crsdk_nd_clamp_count,
            wf12_00342260_hits=self.wf12_00342260_hits,
        )
        state["uvc_srt_crsdk_ptp_cmd"] = format_uvc_srt_crsdk_ptp_command(state)
        return state

    def _apply_uvc_srt_crsdk_ptp_updates_locked(
        self,
        updates: dict[str, Any],
        *,
        is_reset: bool = False,
    ) -> None:
        if is_reset:
            self.p123_last_safe_opcode = 0xD210
            self.p123_safe_cmd_count = 0
            self.p123_flash_blocked_count = 0
            self.p123_last_blocked_opcode = None
            self.p123_p12_blocked_count = 0
            self.p123_uvc_osd_blocked_count = 0
            self.p123_crsdk_nd_clamp_count = 0
        if "uvc_mode" in updates:
            self.uvc_mode = str(updates["uvc_mode"])
        if "usb_link_speed" in updates:
            self.usb_link_speed = str(updates["usb_link_speed"])
        if "uac_audio_enabled" in updates:
            self.uac_audio_enabled = bool(updates["uac_audio_enabled"])
        if "srt_mode" in updates:
            self.srt_mode = str(updates["srt_mode"])
        if "srt_pbkeylen" in updates:
            self.srt_pbkeylen = str(updates["srt_pbkeylen"])
        if "srt_latency_ms" in updates:
            self.srt_latency_ms = int(updates["srt_latency_ms"])
        if "rtmps_mode" in updates:
            self.rtmps_mode = str(updates["rtmps_mode"])
        if "stream_bitrate_mbps" in updates:
            self.stream_bitrate_mbps = int(updates["stream_bitrate_mbps"])
        if "crsdk_ptp_mode" in updates:
            self.crsdk_ptp_mode = str(updates["crsdk_ptp_mode"])

        if "crsdk_cine_ei_base" in updates:
            self.cine_ei_base = str(updates["crsdk_cine_ei_base"])
            if "crsdk_ei_index" not in updates:
                self.ei_index = int(self.cine_ei_base)
        if "crsdk_ei_index" in updates:
            self.ei_index = int(updates["crsdk_ei_index"])
            if "crsdk_cine_ei_base" not in updates:
                self.cine_ei_base = "12800" if self.ei_index in CINE_EI_STEPS["12800"] and self.ei_index not in CINE_EI_STEPS["800"] else (
                    "12800" if self.ei_index >= 6400 and self.cine_ei_base == "12800" else ("12800" if self.ei_index >= 12800 else "800")
                )
        if "crsdk_cine_ei_base" in updates or "crsdk_ei_index" in updates:
            ei_cell_map = {
                ("800", 800): 0,
                ("800", 400): 1,
                ("800", 1600): 2,
                ("12800", 12800): 3,
                ("12800", 6400): 4,
                ("12800", 25600): 5,
            }
            if (self.cine_ei_base, self.ei_index) in ei_cell_map:
                self.cell_vals[1] = ei_cell_map[(self.cine_ei_base, self.ei_index)]
            elif self.cine_ei_base == "12800":
                self.cell_vals[1] = 3
            else:
                self.cell_vals[1] = 0

        if "crsdk_base_look" in updates:
            self.base_look = str(updates["crsdk_base_look"])
            if self.base_look == "User 3D LUT":
                if (self.cell_vals[4] % 8) < 4:
                    self.cell_vals[4] = 4
            elif self.base_look in BASE_LOOK_NLE_TAGS:
                self.cell_vals[4] = int(BASE_LOOK_NLE_TAGS[self.base_look]["cell_lut_idx"])

        if updates.get("crsdk_nd_clamped"):
            self.p123_crsdk_nd_clamp_count += 1
            self.p4_lock_attempts += 1
        self.cell_vals[3] = 0  # P4 ND=Clear Hardware Lock always enforced!

        if "crsdk_safe_opcode" in updates:
            self.p123_last_safe_opcode = int(updates["crsdk_safe_opcode"])
            self.p123_safe_cmd_count += 1

        self.wf12_00342260_hits = 0
        self.p12_bk4_airplane_mode_locked = True
        self.last_cine_exp_cmd = format_cine_exp_command(self.get_cine_exposure())
        self.last_wb_media_cmd = format_wb_media_command(self.get_color_and_media())
        self.last_mc_fleet_sdi_c2pa_cmd = format_mc_fleet_sdi_c2pa_command(self.get_mc_fleet_sdi_c2pa())
        self.last_hdr_hlg_raw_breathing_cmd = format_hdr_hlg_raw_breathing_command(self.get_hdr_hlg_raw_breathing())
        self.last_uvc_srt_crsdk_ptp_cmd = format_uvc_srt_crsdk_ptp_command(self.get_uvc_srt_crsdk_ptp())

    def set_uvc_srt_crsdk_ptp(self, body: Any) -> dict[str, Any]:
        with self.cmd_lock:
            cur = {
                "uvc_mode": self.uvc_mode,
                "usb_link_speed": self.usb_link_speed,
                "uac_audio_enabled": self.uac_audio_enabled,
                "srt_mode": self.srt_mode,
                "srt_pbkeylen": self.srt_pbkeylen,
                "srt_latency_ms": self.srt_latency_ms,
                "rtmps_mode": self.rtmps_mode,
                "stream_bitrate_mbps": self.stream_bitrate_mbps,
                "crsdk_ptp_mode": self.crsdk_ptp_mode,
            }
            ok, updates, err = validate_uvc_srt_crsdk_ptp_patch(body, current_state=cur)
            if not ok:
                err_code = (err or {}).get("error")
                if err_code == "ptp_flash_opcode_blocked":
                    self.p123_flash_blocked_count += 1
                    self.p123_last_blocked_opcode = str(err.get("blocked_opcode", "0x9280"))
                    self.last_toast = str(err.get("message", "Destructive PTP flash opcode blocked"))
                    self.last_uvc_srt_crsdk_ptp_cmd = format_uvc_srt_crsdk_ptp_command(self.get_uvc_srt_crsdk_ptp())
                    self._sync_mailbox_and_capture()
                    err["blocked_flash_opcode_count"] = self.p123_flash_blocked_count
                    err["last_blocked_flash_opcode"] = self.p123_last_blocked_opcode
                    err["ptp_flash_opcodes_blocked"] = True
                    err["emmc_mutation_bytes"] = 0
                    err["uvc_srt_crsdk_ptp"] = self.get_uvc_srt_crsdk_ptp()
                    err["status"] = self.get_status()
                elif err_code == "p12_wlan_off_enforced":
                    self.p123_p12_blocked_count += 1
                    self.last_toast = str(err.get("message", "P12 Airplane-Mode Wi-Fi-OFF enforced"))
                    self.last_uvc_srt_crsdk_ptp_cmd = format_uvc_srt_crsdk_ptp_command(self.get_uvc_srt_crsdk_ptp())
                    self._sync_mailbox_and_capture()
                    err["p12_blocked_count"] = self.p123_p12_blocked_count
                    err["p12_wlan_off"] = True
                    err["wf12_00342260_hits"] = 0
                    err["uvc_srt_crsdk_ptp"] = self.get_uvc_srt_crsdk_ptp()
                    err["status"] = self.get_status()
                elif err_code == "uvc_osd_burnin_blocked":
                    self.p123_uvc_osd_blocked_count += 1
                    self.last_toast = str(err.get("message", "UVC clean feed without OSD burn-in enforced"))
                    self.last_uvc_srt_crsdk_ptp_cmd = format_uvc_srt_crsdk_ptp_command(self.get_uvc_srt_crsdk_ptp())
                    self._sync_mailbox_and_capture()
                    err["uvc_osd_blocked_count"] = self.p123_uvc_osd_blocked_count
                    err["uvc_clean_feed_no_osd"] = True
                    err["uvc_osd_burnin_px"] = 0
                    err["uvc_srt_crsdk_ptp"] = self.get_uvc_srt_crsdk_ptp()
                    err["status"] = self.get_status()
                return err or {"ok": False, "error": "invalid_uvc_srt_crsdk_ptp"}

            is_reset = isinstance(body, dict) and body.get("reset") is True
            self._apply_uvc_srt_crsdk_ptp_updates_locked(updates, is_reset=is_reset)
            p123 = self.get_uvc_srt_crsdk_ptp()
            self.last_toast = (
                f"Phase123: UVC={p123['effective_uvc_mode']}({p123['usb_link_speed']},Clean=1) | "
                f"SRT={p123['srt_mode']}({p123['srt_pbkeylen']},{p123['srt_latency_ms']}ms) | "
                f"RTMPS={p123['rtmps_mode']}@{p123['stream_bitrate_mbps']}M(P12=1) | "
                f"CRSDK={p123['crsdk_ptp_mode']}({p123['crsdk_last_safe_opcode']},FlashBlk=1)"
            )
            wrote, synced = self._sync_mailbox_and_capture()
            return {
                "ok": True,
                "uvc_srt_crsdk_ptp": p123,
                "uvc_srt_crsdk_ptp_cmd": p123["uvc_srt_crsdk_ptp_cmd"],
                "p12_wlan_off": True,
                "wf12_00342260_hits": 0,
                "ptp_flash_opcodes_blocked": True,
                "emmc_mutation_bytes": 0,
                "uvc_clean_feed_no_osd": True,
                "uvc_osd_burnin_px": 0,
                "p4_nd_clear_enforced": True,
                "crsdk_nd_clamped": bool(updates.get("crsdk_nd_clamped", False)),
                "toast": self.last_toast,
                "wrote_mailbox": wrote,
                "guest_synced": synced,
                "status": self.get_status(),
            }

    def get_interval_cache_lut_ftp(self) -> dict[str, Any]:
        state = compute_interval_cache_lut_ftp_derived(
            {
                "cache_seconds": self.cache_seconds,
                "codec_profile": self.codec_profile,
                "interval_rec_enabled": self.interval_rec_enabled,
                "interval_sec": self.interval_sec,
                "target_shots": self.target_shots,
                "shots_taken": self.shots_taken,
                "ae_tracking": self.ae_tracking,
                "ftps_mode": self.ftps_mode,
                "ftps_nic_driver": self.ftps_nic_driver,
                "ftps_tls_version": self.ftps_tls_version,
            },
            base_fps=self.base_fps,
            rec_fmt_idx=self.rec_fmt_idx,
            sq_enabled=self.sq_enabled,
            wired_io_mode=self.wired_io_mode,
            active_user_lut=self._active_user_lut_for_color(),
            ftps_queue=self.ftps_queue,
            ftps_completed=self.ftps_completed,
            ftps_blocked_traversal_count=self.ftps_blocked_traversal_count,
            ftps_last_blocked_path=self.ftps_last_blocked_path,
            wf12_00342260_hits=self.wf12_00342260_hits,
            mechanical_curtain_actuations=self.mechanical_curtain_actuations,
        )
        state["interval_cache_lut_ftp_cmd"] = format_interval_cache_lut_ftp_command(state)
        return state

    def _enqueue_ftps_path_locked(self, norm_path: str, kind: str = "auto") -> dict[str, Any]:
        seq_id = len(self.ftps_queue) + len(self.ftps_completed) + 1
        eff_kind = kind
        if eff_kind == "auto":
            eff_kind = "proxy" if (self.ftps_mode == "Proxy_Only" or "/SUB/" in norm_path) else "original"
        job = {
            "job_id": f"ftps-{seq_id:04d}",
            "path": norm_path,
            "kind": eff_kind,
            "transport": f"USB_LAN_{self.ftps_nic_driver}",
            "nic_driver": self.ftps_nic_driver,
            "tls_version": self.ftps_tls_version,
            "data_mode": "PASV",
            "p12_rf_off_enforced": True,
            "wf12_00342260_hits": 0,
            "status": "QUEUED",
        }
        self.ftps_queue.append(job)
        if len(self.ftps_queue) > 64:
            self.ftps_queue = self.ftps_queue[-64:]
        return job

    def _apply_interval_cache_lut_ftp_updates_locked(
        self,
        updates: dict[str, Any],
        *,
        is_reset: bool = False,
        restored_shots_taken: int | None = None,
    ) -> None:
        if is_reset:
            self.ftps_queue.clear()
            self.ftps_completed.clear()
            self.ftps_blocked_traversal_count = 0
            self.ftps_last_blocked_path = None
            self.shots_taken = 0
        if "cache_seconds" in updates:
            self.cache_seconds = int(updates["cache_seconds"])
        if "codec_profile" in updates:
            self.codec_profile = str(updates["codec_profile"])
        if "interval_rec_enabled" in updates:
            self.interval_rec_enabled = bool(updates["interval_rec_enabled"])
            if self.interval_rec_enabled and self.sq_enabled:
                self.sq_enabled = False
                fps_map = {23.98: 0, 24.0: 1, 25.0: 2, 29.97: 3, 50.0: 4, 59.94: 5}
                self.cell_vals[0] = fps_map.get(round(self.base_fps, 2), 0)
                self.last_cine_exp_cmd = format_cine_exp_command(self.get_cine_exposure())
                self.last_wb_media_cmd = format_wb_media_command(self.get_color_and_media())
                self.last_touch_af_ciz_cmd = format_touch_focus_ciz_command(self.get_touch_focus_ciz())
                self.last_gyroflow_anamorphic_cmd = format_gyroflow_anamorphic_command(self.get_gyroflow_anamorphic())
        if "interval_sec" in updates:
            self.interval_sec = int(updates["interval_sec"])
        if "target_shots" in updates:
            self.target_shots = int(updates["target_shots"])
        if updates.get("reset_shots"):
            self.shots_taken = 0
        if restored_shots_taken is not None:
            self.shots_taken = max(0, min(self.target_shots, int(restored_shots_taken)))
        if "advance_shots" in updates:
            self.shots_taken = max(0, min(self.target_shots, self.shots_taken + int(updates["advance_shots"])))
        if "ae_tracking" in updates:
            self.ae_tracking = str(updates["ae_tracking"])
        if "ftps_mode" in updates:
            self.ftps_mode = str(updates["ftps_mode"])
        if "ftps_nic_driver" in updates:
            self.ftps_nic_driver = str(updates["ftps_nic_driver"])
        if updates.get("clear_queue"):
            self.ftps_queue.clear()
            self.ftps_completed.clear()
        if "enqueue_path" in updates:
            self._enqueue_ftps_path_locked(str(updates["enqueue_path"]))
        if updates.get("enqueue_current_clip"):
            cm = self.get_color_and_media()
            if self.ftps_mode == "Proxy_Only":
                ok_p, norm_p, _, _ = validate_ftps_media_path(f"/mnt/slot_a/PRIVATE/M4ROOT/SUB/{cm['proxy_clip_name']}")
                if ok_p:
                    self._enqueue_ftps_path_locked(norm_p, kind="proxy")
            else:
                ok_m, norm_m, _, _ = validate_ftps_media_path(f"/mnt/slot_a/PRIVATE/M4ROOT/CLIP/{cm['main_clip_name']}")
                if ok_m:
                    self._enqueue_ftps_path_locked(norm_m, kind="original")
                if self.ftps_mode == "Original_And_Proxy":
                    ok_s, norm_s, _, _ = validate_ftps_media_path(f"/mnt/slot_a/PRIVATE/M4ROOT/SUB/{cm['proxy_clip_name']}")
                    if ok_s:
                        self._enqueue_ftps_path_locked(norm_s, kind="proxy")
        if (updates.get("process_next_job") or updates.get("advance_queue")) and self.ftps_mode != "Off" and self.ftps_queue:
            job = dict(self.ftps_queue.pop(0))
            job["status"] = "COMPLETED"
            job["wf12_00342260_hits"] = 0
            job["p12_rf_off_enforced"] = True
            self.ftps_completed.append(job)
            if len(self.ftps_completed) > 64:
                self.ftps_completed = self.ftps_completed[-64:]

        self.shots_taken = max(0, min(self.target_shots, self.shots_taken))
        self.mechanical_curtain_actuations = 0
        self.wf12_00342260_hits = 0
        self.p12_bk4_airplane_mode_locked = True
        self.last_interval_cache_lut_ftp_cmd = format_interval_cache_lut_ftp_command(self.get_interval_cache_lut_ftp())

    def set_interval_cache_lut_ftp(self, body: Any) -> dict[str, Any]:
        with self.cmd_lock:
            cur = {
                "cache_seconds": self.cache_seconds,
                "codec_profile": self.codec_profile,
                "interval_rec_enabled": self.interval_rec_enabled,
                "interval_sec": self.interval_sec,
                "target_shots": self.target_shots,
                "shots_taken": self.shots_taken,
                "ae_tracking": self.ae_tracking,
                "ftps_mode": self.ftps_mode,
                "ftps_nic_driver": self.ftps_nic_driver,
            }
            ok, updates, err = validate_interval_cache_lut_ftp_patch(body, current_state=cur)
            if not ok:
                if err and err.get("error") == "emmc_path_traversal_blocked":
                    self.ftps_blocked_traversal_count += 1
                    self.ftps_last_blocked_path = str(err.get("blocked_path", ""))
                    self.last_toast = str(err.get("message", "Blocked eMMC p1..p15 traversal"))
                    self.last_interval_cache_lut_ftp_cmd = format_interval_cache_lut_ftp_command(
                        self.get_interval_cache_lut_ftp()
                    )
                    self._sync_mailbox_and_capture()
                    err["ftps_blocked_traversal_count"] = self.ftps_blocked_traversal_count
                return err or {"ok": False, "error": "invalid_interval_cache_lut_ftp"}

            is_reset = isinstance(body, dict) and body.get("reset") is True
            self._apply_interval_cache_lut_ftp_updates_locked(updates, is_reset=is_reset)
            p102 = self.get_interval_cache_lut_ftp()
            self.last_toast = (
                f"Phase102: Cache={p102['effective_cache_seconds']}s({p102['allocated_ddr_mib']:.1f}MiB) | "
                f"Intvl={'ON' if p102['interval_rec_enabled'] else 'OFF'}({p102['shots_taken']}/{p102['target_shots']} E-SH) | "
                f"FTPS={p102['ftps_mode']}(Q={p102['ftps_queued_count']}/D={p102['ftps_completed_count']} P12=OFF)"
            )
            wrote, synced = self._sync_mailbox_and_capture()
            return {
                "ok": True,
                "interval_cache_lut_ftp": p102,
                "interval_cache_lut_ftp_cmd": p102["interval_cache_lut_ftp_cmd"],
                "mechanical_curtain_actuations": 0,
                "wf12_00342260_hits": 0,
                "toast": self.last_toast,
                "wrote_mailbox": wrote,
                "guest_synced": synced,
                "status": self.get_status(),
            }

    def get_touch_focus_ciz(self) -> dict[str, Any]:
        state = compute_touch_focus_ciz_derived(
            {
                "touch_af_mode": self.touch_af_mode,
                "touch_x": self.touch_x,
                "touch_y": self.touch_y,
                "focus_mag": self.focus_mag,
                "false_color_mode": self.false_color_mode,
                "ciz_scale": self.ciz_scale,
                "ciz_res_mode": self.ciz_res_mode,
                "zoom_rocker_speed": self.zoom_rocker_speed,
            },
            aspect_marker=self.aspect_marker,
            desqueeze=self.desqueeze,
            squeeze_factor=self.squeeze_factor,
            zebra_mode=self.zebra_mode,
            base_look=self.base_look,
            wired_io_mode=self.wired_io_mode,
            sq_enabled=self.sq_enabled,
            sq_fps=self.sq_fps,
            letterbox_ignored=self.last_letterbox_ignored,
        )
        state["touch_af_ciz_cmd"] = format_touch_focus_ciz_command(state)
        return state

    def _apply_touch_focus_ciz_updates_locked(self, updates: dict[str, Any]) -> None:
        if "touch_af_mode" in updates:
            self.touch_af_mode = str(updates["touch_af_mode"])
        if "touch_x" in updates:
            self.touch_x = int(updates["touch_x"])
        if "touch_y" in updates:
            self.touch_y = int(updates["touch_y"])
        if "focus_mag" in updates:
            self.focus_mag = str(updates["focus_mag"])
        if "false_color_mode" in updates:
            self.false_color_mode = str(updates["false_color_mode"])
        if "ciz_scale" in updates:
            self.ciz_scale = float(updates["ciz_scale"])
        if "ciz_res_mode" in updates:
            self.ciz_res_mode = str(updates["ciz_res_mode"])
        if "zoom_rocker_speed" in updates:
            self.zoom_rocker_speed = int(updates["zoom_rocker_speed"])
        self.last_letterbox_ignored = bool(updates.get("_letterbox_ignored", False))
        self.last_touch_af_ciz_cmd = format_touch_focus_ciz_command(self.get_touch_focus_ciz())
        self.last_gyroflow_anamorphic_cmd = format_gyroflow_anamorphic_command(self.get_gyroflow_anamorphic())

    def set_touch_focus_ciz(self, body: Any) -> dict[str, Any]:
        with self.cmd_lock:
            cur = {
                "touch_af_mode": self.touch_af_mode,
                "touch_x": self.touch_x,
                "touch_y": self.touch_y,
                "focus_mag": self.focus_mag,
                "false_color_mode": self.false_color_mode,
                "ciz_scale": self.ciz_scale,
                "ciz_res_mode": self.ciz_res_mode,
                "zoom_rocker_speed": self.zoom_rocker_speed,
            }
            ok, updates, err = validate_touch_focus_ciz_patch(
                body,
                current_state=cur,
                aspect_marker=self.aspect_marker,
                desqueeze=self.desqueeze,
                squeeze_factor=self.squeeze_factor,
            )
            if not ok:
                return err or {"ok": False, "error": "invalid_touch_focus_ciz"}

            self._apply_touch_focus_ciz_updates_locked(updates)
            tfc = self.get_touch_focus_ciz()
            if tfc["letterbox_ignored"]:
                self.last_toast = (
                    f"Touch-AF Letterbox Ignored ({self.aspect_marker}/{self.desqueeze}): "
                    f"AF locked @ ({tfc['touch_x']},{tfc['touch_y']}) #{tfc['pdaf_index']}"
                )
            elif tfc["ciz_clamped_by_exclusion"]:
                self.last_toast = (
                    f"Touch-AF={tfc['touch_af_mode']}#{tfc['pdaf_index']} | Mag={tfc['focus_mag']} | "
                    f"FC={tfc['false_color_mode']} | CIZ Clamped->1.00x ({tfc['ciz_exclusion_reason']})"
                )
            elif tfc["slog3_zebra100_clip_warning"]:
                self.last_toast = (
                    f"Touch-AF={tfc['touch_af_mode']}#{tfc['pdaf_index']} | FC={tfc['false_color_mode']} | "
                    "WARN: S-Log3 clips@94% vs Zebra100%"
                )
            else:
                self.last_toast = (
                    f"Touch-AF={tfc['touch_af_mode']}@({tfc['touch_x']},{tfc['touch_y']}) "
                    f"PDAF#{tfc['pdaf_index']}({tfc['pdaf_col']},{tfc['pdaf_row']}) | "
                    f"Mag={tfc['focus_mag']} | FC={tfc['false_color_mode']} | "
                    f"CIZ={tfc['effective_ciz_scale']:.2f}x ({tfc['ciz_res_mode']})"
                )
            wrote, synced = self._sync_mailbox_and_capture()
            return {
                "ok": True,
                "touch_focus_ciz": tfc,
                "touch_af_ciz_cmd": tfc["touch_af_ciz_cmd"],
                "letterbox_ignored": tfc["letterbox_ignored"],
                "clean_hdmi_unmagnified": tfc["clean_hdmi_unmagnified"],
                "toast": self.last_toast,
                "wrote_mailbox": wrote,
                "guest_synced": synced,
                "status": self.get_status(),
            }

    def get_shotmark_and_iris(self) -> dict[str, Any]:
        eff_fps = float(self.sq_fps) if self.sq_enabled else float(self.base_fps)
        state = compute_shotmark_and_iris_derived(
            {
                "shotmarks": self.shotmarks,
                "iris_fstop": self.iris_fstop,
                "ae_shift_ev": self.ae_shift_ev,
                "metering_mode": self.metering_mode,
                "ch34_safety_pad_db": self.ch34_safety_pad_db,
                "user_bits_hex": self.user_bits_hex,
                "push_auto_iris_active": self.push_auto_iris_active,
                "last_scene_ev": self.last_scene_ev,
            },
            cam_id=self.cam_id,
            reel_num=self.reel_num,
            clip_seq=self.clip_seq,
            ei_index=self.ei_index,
            shutter_mode=self.shutter_mode,
            shutter_angle_deg=self.shutter_angle_deg,
            shutter_speed_denom=self.shutter_speed_denom,
            ecs_freq_hz=self.ecs_freq_hz,
            effective_fps=eff_fps,
            audio_ch_db=self.audio_ch_db,
        )
        state["shotmark_iris_cmd"] = format_shotmark_iris_command(state)
        return state

    def _apply_shotmark_and_iris_updates_locked(self, updates: dict[str, Any]) -> None:
        if "shotmarks" in updates:
            self.shotmarks = [dict(m) for m in updates["shotmarks"]]
        if "iris_fstop" in updates:
            self.iris_fstop = float(updates["iris_fstop"])
        if "ae_shift_ev" in updates:
            self.ae_shift_ev = float(updates["ae_shift_ev"])
        if "metering_mode" in updates:
            self.metering_mode = str(updates["metering_mode"])
        if "ch34_safety_pad_db" in updates:
            self.ch34_safety_pad_db = int(updates["ch34_safety_pad_db"])
        if "user_bits_hex" in updates:
            self.user_bits_hex = str(updates["user_bits_hex"])
        if "push_auto_iris_active" in updates:
            self.push_auto_iris_active = bool(updates["push_auto_iris_active"])
        if "last_scene_ev" in updates:
            self.last_scene_ev = float(updates["last_scene_ev"])
        self.last_shotmark_iris_cmd = format_shotmark_iris_command(self.get_shotmark_and_iris())
        self.last_hdr_hlg_raw_breathing_cmd = format_hdr_hlg_raw_breathing_command(self.get_hdr_hlg_raw_breathing())

    def set_shotmark_and_iris(self, body: Any) -> dict[str, Any]:
        with self.cmd_lock:
            eff_fps = float(self.sq_fps) if self.sq_enabled else float(self.base_fps)
            cur = {
                "shotmarks": self.shotmarks,
                "iris_fstop": self.iris_fstop,
                "ae_shift_ev": self.ae_shift_ev,
                "metering_mode": self.metering_mode,
                "ch34_safety_pad_db": self.ch34_safety_pad_db,
                "user_bits_hex": self.user_bits_hex,
                "push_auto_iris_active": self.push_auto_iris_active,
                "last_scene_ev": self.last_scene_ev,
            }
            ok, updates, err = validate_shotmark_and_iris_patch(
                body,
                current_state=cur,
                rec_tc_frames=self.rec_tc_frames,
                ei_index=self.ei_index,
                shutter_mode=self.shutter_mode,
                shutter_angle_deg=self.shutter_angle_deg,
                shutter_speed_denom=self.shutter_speed_denom,
                ecs_freq_hz=self.ecs_freq_hz,
                effective_fps=eff_fps,
                base_fps=self.base_fps,
            )
            if not ok:
                return err or {"ok": False, "error": "invalid_shotmark_and_iris"}

            self._apply_shotmark_and_iris_updates_locked(updates)
            smi = self.get_shotmark_and_iris()
            self.last_toast = (
                f"ShotMark&Iris: M1={smi['shotmark1_count']} M2={smi['shotmark2_count']} | "
                f"{smi['iris_display']} ({smi['metering_mode']}, AE={smi['ae_shift_ev']:+.2f}EV) | "
                f"41%IRE | CH3/4={smi['ch34_safety_pad_db']}dB | UB={smi['user_bits_effective']}"
            )
            wrote, synced = self._sync_mailbox_and_capture()
            return {
                "ok": True,
                "shotmark_and_iris": smi,
                "shotmark_iris_cmd": smi["shotmark_iris_cmd"],
                "p4_nd_motor_faults": 0,
                "toast": self.last_toast,
                "wrote_mailbox": wrote,
                "guest_synced": synced,
                "status": self.get_status(),
            }

    def get_gyroflow_anamorphic(self) -> dict[str, Any]:
        state = compute_gyroflow_anamorphic_derived(
            {
                "squeeze_factor": self.squeeze_factor,
                "ibis_mode": self.ibis_mode,
                "anamorphic_fallback_mode": self.anamorphic_fallback_mode,
                "ref_tone_enabled": self.ref_tone_enabled,
                "color_bars_enabled": self.color_bars_enabled,
                "limiter_enabled": self.limiter_enabled,
            },
            base_fps=self.base_fps,
            sq_enabled=self.sq_enabled,
            sq_fps=self.sq_fps,
            rec_state=self.rec_state,
            touch_x=self.touch_x,
            touch_y=self.touch_y,
            audio_ch_db=self.audio_ch_db,
        )
        state["gyroflow_anamorphic_cmd"] = format_gyroflow_anamorphic_command(state)
        return state

    def _apply_gyroflow_anamorphic_updates_locked(self, updates: dict[str, Any]) -> None:
        if "squeeze_factor" in updates:
            self.squeeze_factor = float(updates["squeeze_factor"])
            self.desqueeze = squeeze_factor_to_assist_desqueeze(self.squeeze_factor)
        if "ibis_mode" in updates:
            self.ibis_mode = str(updates["ibis_mode"])
        if "anamorphic_fallback_mode" in updates:
            self.anamorphic_fallback_mode = str(updates["anamorphic_fallback_mode"])
        if "ref_tone_enabled" in updates:
            self.ref_tone_enabled = bool(updates["ref_tone_enabled"])
        if "color_bars_enabled" in updates:
            self.color_bars_enabled = bool(updates["color_bars_enabled"])
        if "limiter_enabled" in updates:
            self.limiter_enabled = bool(updates["limiter_enabled"])

        ga = self.get_gyroflow_anamorphic()
        if any(k in updates for k in ("ibis_mode", "squeeze_factor", "anamorphic_fallback_mode", "reset")):
            eff_ibis = ga["effective_ibis_mode"]
            if eff_ibis in ("Off", "Center_Lock_Gyroflow"):
                self.rtmd_0xe304_ibis_lock = "OFF_CENTER_LOCKED"
                self.ibis_idx = RTMD_0XE304_MODES.index("OFF_CENTER_LOCKED")
            elif eff_ibis in ("Standard", "Anamorphic_Asymmetric"):
                self.rtmd_0xe304_ibis_lock = "STANDARD"
                self.ibis_idx = RTMD_0XE304_MODES.index("STANDARD")
            else:
                self.rtmd_0xe304_ibis_lock = "ACTIVE_5AXIS"
                self.ibis_idx = RTMD_0XE304_MODES.index("ACTIVE_5AXIS")

        self.last_touch_af_ciz_cmd = format_touch_focus_ciz_command(self.get_touch_focus_ciz())
        self.last_gyroflow_anamorphic_cmd = ga["gyroflow_anamorphic_cmd"]

    def set_gyroflow_anamorphic(self, body: Any) -> dict[str, Any]:
        with self.cmd_lock:
            cur = {
                "squeeze_factor": self.squeeze_factor,
                "ibis_mode": self.ibis_mode,
                "anamorphic_fallback_mode": self.anamorphic_fallback_mode,
                "ref_tone_enabled": self.ref_tone_enabled,
                "color_bars_enabled": self.color_bars_enabled,
                "limiter_enabled": self.limiter_enabled,
            }
            ok, updates, err = validate_gyroflow_anamorphic_patch(body, current_state=cur)
            if not ok:
                return err or {"ok": False, "error": "invalid_gyroflow_anamorphic"}

            # Optional synchronized Touch-AF coordinate update inside /api/gyroflow_anamorphic
            tfc_updates: dict[str, Any] = {}
            if isinstance(body, dict) and any(
                k in body and body[k] is not None for k in ("desqueezed_touch_x", "touch_x", "touch_y")
            ):
                next_sq = float(updates.get("squeeze_factor", self.squeeze_factor))
                next_dsq = squeeze_factor_to_assist_desqueeze(next_sq)
                tfc_payload = {
                    k: body[k]
                    for k in ("desqueezed_touch_x", "touch_x", "touch_y", "coordinate_space", "touch_af_mode")
                    if k in body and body[k] is not None
                }
                cur_tfc = {
                    "touch_af_mode": self.touch_af_mode,
                    "touch_x": self.touch_x,
                    "touch_y": self.touch_y,
                    "focus_mag": self.focus_mag,
                    "false_color_mode": self.false_color_mode,
                    "ciz_scale": self.ciz_scale,
                    "ciz_res_mode": self.ciz_res_mode,
                    "zoom_rocker_speed": self.zoom_rocker_speed,
                }
                ok_tfc, tfc_updates, err_tfc = validate_touch_focus_ciz_patch(
                    tfc_payload,
                    current_state=cur_tfc,
                    aspect_marker=self.aspect_marker,
                    desqueeze=next_dsq,
                    squeeze_factor=next_sq,
                )
                if not ok_tfc:
                    return err_tfc or {"ok": False, "error": "invalid_touch_focus_ciz"}

            self._apply_gyroflow_anamorphic_updates_locked(updates)
            if tfc_updates:
                self._apply_touch_focus_ciz_updates_locked(tfc_updates)
            ga = self.get_gyroflow_anamorphic()
            tone_tag = (
                "TONE:INHIB(REC)"
                if ga["ref_tone_inhibited_by_rec"]
                else ("TONE:1kHz@-20dB" if ga["ref_tone_effective_active"] else "TONE:OFF")
            )
            self.last_toast = (
                f"Phase95: DSQ {ga['squeeze_display']} | IBIS={ga['effective_ibis_mode']}"
                f"(yaw={ga['horizontal_yaw_gain']:.2f}) | GYRO={ga['imu_samples_per_frame']:.1f}/f "
                f"{ga['rolling_shutter_skew_ms']:.1f}ms [{ga['rtmd_status']}] | {tone_tag} | "
                f"LIM={'ON' if ga['limiter_enabled'] else 'OFF'}"
            )
            wrote, synced = self._sync_mailbox_and_capture()
            return {
                "ok": True,
                "gyroflow_anamorphic": ga,
                "gyroflow_anamorphic_cmd": ga["gyroflow_anamorphic_cmd"],
                "touch_focus_ciz": self.get_touch_focus_ciz(),
                "toast": self.last_toast,
                "wrote_mailbox": wrote,
                "guest_synced": synced,
                "status": self.get_status(),
            }

    def get_scope_stats(self, refresh: bool = False) -> dict[str, Any]:
        if self.is_running() and self.live_ready and not self.crashed and (refresh or len(self.last_raw_gpe0) < GPE0_BYTES):
            self._capture_live_gpe0_with_raw()
        if len(self.last_raw_gpe0) >= GPE0_BYTES:
            raw = self.last_raw_gpe0[:GPE0_BYTES]
            source = "live_gpe0"
        else:
            raw, source = _get_fallback_gpe0_raw(self.last_png)
        stats = compute_gpe0_scope_stats(raw)
        stats["source"] = source
        stats["ack_seq"] = self.ack_seq
        stats["page"] = self.page
        stats["assist_tools"] = self.get_assist_tools()
        active_lut = self._active_user_lut_for_color()
        lut_uploaded = bool(active_lut and active_lut.get("uploaded"))
        stats["lut_preview"] = {
            "active": lut_uploaded,
            "slot": active_lut.get("slot") if active_lut and lut_uploaded else None,
            "title": (active_lut.get("title") or active_lut.get("name")) if active_lut and lut_uploaded else None,
            "target_grid_size": 33 if lut_uploaded else 0,
            "resampling_method": "tetrahedral" if lut_uploaded else None,
            "resampled_33_sha256": active_lut.get("resampled_33_sha256") if active_lut and lut_uploaded else None,
            "contrast_signature": float(active_lut.get("contrast_signature", 1.0)) if active_lut and lut_uploaded else 1.0,
            "tint_rgb8": list(active_lut.get("tint_rgb8", [128, 128, 128])) if active_lut and lut_uploaded else [128, 128, 128],
            "tint_hex": active_lut.get("tint_hex", "#808080") if active_lut and lut_uploaded else "#808080",
            "shadow_tint_rgb8": list(active_lut.get("shadow_tint_rgb8", [128, 128, 128])) if active_lut and lut_uploaded else [128, 128, 128],
            "highlight_tint_rgb8": list(active_lut.get("highlight_tint_rgb8", [128, 128, 128])) if active_lut and lut_uploaded else [128, 128, 128],
            "volatile_ram_only": True,
        }
        self.last_scope_stats = stats
        return stats

    def export_camset_preset(self) -> dict[str, Any]:
        """Export deterministic `fx6_on_fx3_camset_v1` JSON snapshot with SHA-256."""
        cp = self.get_cinema_params()
        canonical_body = {
            "schema": "fx6_on_fx3_camset_v1",
            "lang": self.lang_code,
            "cinema_params": {
                "fps": cp["values"]["fps"],
                "ei": cp["values"]["ei"],
                "shutter": cp["values"]["shutter"],
                "nd": "Clear [FX3 P4 Locked]",
                "lut": cp["values"]["lut"],
                "wb": cp["values"]["wb"],
                "ibis": cp["values"]["ibis"],
                "xlr": cp["values"]["xlr"],
            },
            "audio": {
                "ch1_db": int(self.audio_ch_db[0]),
                "ch2_db": int(self.audio_ch_db[1]),
                "ch3_db": int(self.audio_ch_db[2]),
                "ch4_db": int(self.audio_ch_db[3]),
                "xlr_phantom_48v": bool(self.xlr_phantom_48v),
                "xlr_handle_attached": bool(self.xlr_handle_attached),
            },
            "assist_tools": self.get_assist_tools(),
            "cine_exposure": self.get_cine_exposure(),
            "color_and_media": self.get_color_and_media(),
            "touch_focus_ciz": self.get_touch_focus_ciz(),
            "shotmark_and_iris": self.get_shotmark_and_iris(),
            "gyroflow_anamorphic": self.get_gyroflow_anamorphic(),
            "interval_cache_lut_ftp": self.get_interval_cache_lut_ftp(),
            "mc_fleet_sdi_c2pa": self.get_mc_fleet_sdi_c2pa(),
            "hdr_hlg_raw_breathing": self.get_hdr_hlg_raw_breathing(),
            "uvc_srt_crsdk_ptp": self.get_uvc_srt_crsdk_ptp(),
            "rtmd_0xe304_ibis_lock": self.rtmd_0xe304_ibis_lock,
            "p12_bk4_airplane_mode_locked": True,
            "active_user_lut": cp.get("active_user_lut"),
            "user_lut_slots": {k: dict(v) for k, v in self.user_lut_slots.items()},
        }
        canonical_json = json.dumps(canonical_body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        preset_sha256 = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
        return {
            "ok": True,
            **canonical_body,
            "preset_sha256": preset_sha256,
        }

    def import_camset_preset(self, payload: Any) -> dict[str, Any]:
        """Validate & apply `fx6_on_fx3_camset_v1` (or sanitized A-Cam `ILME-FX6` fleet preset) while enforcing P4 & P12."""
        if not isinstance(payload, dict):
            return {"ok": False, "error": "invalid_camset_payload", "message": "CAMSET payload must be a JSON object"}

        is_fx6_fleet = detect_fx6_fleet_camset(payload)
        raw_schema = payload.get("schema")
        if is_fx6_fleet:
            if raw_schema is not None and raw_schema not in ("fx6_on_fx3_camset_v1", "ilme_fx6_camset_v1", "fx6_camset_v1"):
                return {
                    "ok": False,
                    "error": "invalid_camset_schema",
                    "message": f"Expected schema 'fx6_on_fx3_camset_v1' or 'ilme_fx6_camset_v1', got {raw_schema!r}",
                }
            payload, sanitized_fx6_fields, sanitized_fx6_details = sanitize_fx6_fleet_camset_payload(payload)
        else:
            if raw_schema != "fx6_on_fx3_camset_v1":
                return {
                    "ok": False,
                    "error": "invalid_camset_schema",
                    "message": f"Expected schema 'fx6_on_fx3_camset_v1', got {raw_schema!r}",
                }
            sanitized_fx6_fields = []
            sanitized_fx6_details = {}

        cparams = payload.get("cinema_params")
        if cparams is None:
            cparams = {}
        if not isinstance(cparams, dict):
            return {"ok": False, "error": "invalid_cinema_params", "message": "cinema_params must be a JSON object"}

        ce_raw = payload.get("cine_exposure")
        if ce_raw is not None and not isinstance(ce_raw, dict):
            return {"ok": False, "error": "invalid_cine_exposure", "message": "cine_exposure must be a JSON object"}

        # Detect any P4 ND tamper attempts across cinema_params, cine_exposure, or top-level keys
        nd_tamper_val = None
        ce_nd_val = ce_raw.get("nd_preset") if isinstance(ce_raw, dict) else None
        for cand_nd in (cparams.get("nd"), ce_nd_val, payload.get("nd"), payload.get("nd_filter"), payload.get("variable_nd")):
            if cand_nd is not None:
                s_nd = str(cand_nd).strip().lower()
                if s_nd not in ("", "clear [fx3 p4 locked]", "clear", "0", "false", "none", "off"):
                    nd_tamper_val = cand_nd
                    break
        if nd_tamper_val is None and payload.get("nd_enabled") is True:
            nd_tamper_val = True

        # Validate cinema param choices before mutating state
        new_cells: dict[int, int] = {}
        for pkey in ("fps", "ei", "shutter", "lut", "wb"):
            if pkey in cparams and cparams[pkey] is not None:
                spec = CINEMA_PARAM_SPECS[pkey]
                presets = list(spec["presets"])
                target = str(cparams[pkey]).strip()
                t_low = target.lower()
                matched = next((idx for idx, cand in enumerate(presets) if cand.lower() == t_low), None)
                if matched is None:
                    matched = next(
                        (idx for idx, cand in enumerate(presets) if cand.lower().startswith(t_low) or t_low in cand.lower()),
                        None,
                    )
                if matched is None:
                    return {"ok": False, "error": f"invalid_camset_{pkey}", "message": f"Unknown {pkey} preset: {target!r}"}
                new_cells[int(spec["cell_idx"])] = matched

        new_rtmd = None
        if "rtmd_0xe304_ibis_lock" in payload and payload["rtmd_0xe304_ibis_lock"] is not None:
            new_rtmd = self._normalize_rtmd_ibis(payload["rtmd_0xe304_ibis_lock"])
            if new_rtmd is None:
                return {"ok": False, "error": "invalid_rtmd_0xe304_ibis_lock", "message": f"Invalid rtmd_0xe304_ibis_lock: {payload['rtmd_0xe304_ibis_lock']!r}"}
        elif "ibis" in cparams and cparams["ibis"] is not None:
            ibis_presets = CINEMA_PARAM_SPECS["ibis"]["presets"]
            t_low = str(cparams["ibis"]).strip().lower()
            matched_ibis = next((idx for idx, cand in enumerate(ibis_presets) if cand.lower() == t_low), None)
            if matched_ibis is None:
                return {"ok": False, "error": "invalid_camset_ibis", "message": f"Unknown ibis preset: {cparams['ibis']!r}"}
            new_rtmd = RTMD_0XE304_MODES[matched_ibis % len(RTMD_0XE304_MODES)]

        audio_in = payload.get("audio")
        if audio_in is None:
            audio_in = {}
        if not isinstance(audio_in, dict):
            return {"ok": False, "error": "invalid_camset_audio", "message": "audio must be a JSON object"}

        new_ch_db: dict[int, int] = {}
        for idx in range(4):
            ak = f"ch{idx + 1}_db"
            if ak in audio_in and audio_in[ak] is not None:
                v = audio_in[ak]
                if isinstance(v, bool):
                    return {"ok": False, "error": "invalid_audio_db", "message": f"{ak} cannot be bool"}
                try:
                    fv = float(v)
                except (TypeError, ValueError):
                    return {"ok": False, "error": "invalid_audio_db", "message": f"{ak} must be numeric"}
                if not math.isfinite(fv):
                    return {"ok": False, "error": "invalid_audio_db", "message": f"{ak} must be finite"}
                new_ch_db[idx] = max(-60, min(12, int(round(fv))))

        new_attached: bool | None = None
        if "xlr_handle_attached" in audio_in and audio_in["xlr_handle_attached"] is not None:
            new_attached = self._normalize_bool(audio_in["xlr_handle_attached"])
            if new_attached is None:
                return {"ok": False, "error": "invalid_xlr_handle_attached"}

        new_phantom: bool | None = None
        if "xlr_phantom_48v" in audio_in and audio_in["xlr_phantom_48v"] is not None:
            new_phantom = self._normalize_bool(audio_in["xlr_phantom_48v"])
            if new_phantom is None:
                return {"ok": False, "error": "invalid_xlr_phantom_48v"}

        new_lang_code: str | None = None
        new_lang_id: int | None = None
        if "lang" in payload and payload["lang"] is not None:
            nc = self._normalize_lang(payload["lang"])
            packs = discover_available_lang_packs()
            if nc is not None and nc in packs and packs[nc]["available"]:
                new_lang_code = nc
                new_lang_id = int(packs[nc]["id"])

        new_slots: dict[str, dict[str, Any]] = {}
        new_slot_tables: dict[str, list[tuple[float, float, float]]] = {}
        raw_slots = payload.get("user_lut_slots")
        if isinstance(raw_slots, dict):
            for skey, sdata in raw_slots.items():
                norm_s = self._normalize_lut_slot(skey)
                if norm_s is None or not isinstance(sdata, dict):
                    continue
                if "cube_text" in sdata and isinstance(sdata["cube_text"], str):
                    san = validate_and_sanitize_cube_lut(
                        sdata["cube_text"],
                        name=str(sdata.get("name", norm_s)),
                        include_33_table=True,
                    )
                    if not san["ok"]:
                        return san
                    new_slot_tables[norm_s] = list(san.pop("_table_33", []))
                    new_slots[norm_s] = {
                        "slot": norm_s,
                        "name": san["name"],
                        "title": san["title"],
                        "uploaded": True,
                        "preset": sdata.get("preset"),
                        "size": san["size"],
                        "source_grid_size": san["source_grid_size"],
                        "target_grid_size": san["target_grid_size"],
                        "triplets": san["triplets"],
                        "resampled_33_triplets": san["resampled_33_triplets"],
                        "resampling_method": san["resampling_method"],
                        "clamped_components": san["clamped_components"],
                        "domain_min": san["domain_min"],
                        "domain_max": san["domain_max"],
                        "sha256": san["sha256"],
                        "resampled_33_sha256": san["resampled_33_sha256"],
                        "contrast_signature": san["contrast_signature"],
                        "mid_gray_rgb": san["mid_gray_rgb"],
                        "tint_rgb8": san["tint_rgb8"],
                        "tint_hex": san["tint_hex"],
                        "shadow_tint_rgb8": san["shadow_tint_rgb8"],
                        "highlight_tint_rgb8": san["highlight_tint_rgb8"],
                        "volatile_ram_only": True,
                        "persistent_emmc_writes_authorized": False,
                        "emmc_mutation_bytes": 0,
                    }
                else:
                    rgb8 = sdata.get("tint_rgb8", [128, 128, 128])
                    if not (isinstance(rgb8, list) and len(rgb8) == 3):
                        rgb8 = [128, 128, 128]
                    rgb8_clean = [max(0, min(255, int(x))) for x in rgb8]
                    safe_n = str(sdata.get("name", f"{norm_s} .cube"))[:23]
                    if _is_unsafe_lut_label(safe_n):
                        return {"ok": False, "error": "unsafe_lut_name", "message": "Unsafe LUT name in CAMSET"}
                    src_sz = int(sdata.get("source_grid_size", sdata.get("size", 33)))
                    if src_sz not in (2, 17, 33, 65):
                        src_sz = 33
                    new_slots[norm_s] = {
                        "slot": norm_s,
                        "name": safe_n,
                        "title": str(sdata.get("title") or safe_n)[:23],
                        "uploaded": bool(sdata.get("uploaded", False)),
                        "preset": sdata.get("preset"),
                        "size": int(sdata.get("size", src_sz)) if int(sdata.get("size", src_sz)) in (2, 17, 33, 65) else 33,
                        "source_grid_size": src_sz,
                        "target_grid_size": 33,
                        "triplets": int(sdata.get("triplets", src_sz ** 3)),
                        "resampled_33_triplets": 33 ** 3,
                        "resampling_method": "tetrahedral",
                        "sha256": sdata.get("sha256"),
                        "resampled_33_sha256": sdata.get("resampled_33_sha256") or sdata.get("sha256"),
                        "contrast_signature": float(sdata.get("contrast_signature", 1.0)),
                        "mid_gray_rgb": sdata.get("mid_gray_rgb", [0.5, 0.5, 0.5]),
                        "tint_rgb8": rgb8_clean,
                        "tint_hex": f"#{rgb8_clean[0]:02x}{rgb8_clean[1]:02x}{rgb8_clean[2]:02x}",
                        "shadow_tint_rgb8": sdata.get("shadow_tint_rgb8", rgb8_clean),
                        "highlight_tint_rgb8": sdata.get("highlight_tint_rgb8", rgb8_clean),
                        "volatile_ram_only": True,
                        "persistent_emmc_writes_authorized": False,
                        "emmc_mutation_bytes": 0,
                    }

        new_assist_updates: dict[str, str] = {}
        if "assist_tools" in payload and payload["assist_tools"] is not None:
            ok_a, new_assist_updates, err_a = validate_assist_tools_patch(payload["assist_tools"])
            if not ok_a:
                return err_a or {"ok": False, "error": "invalid_assist_tools"}

        new_cine_updates: dict[str, Any] = {}
        ce_tc_frames: int | None = None
        ce_p12_tamper = False
        if ce_raw is not None:
            ce_p12_tamper = (
                ce_raw.get("wifi_enabled") is True
                or ce_raw.get("bt_enabled") is True
                or ce_raw.get("wifi_bt_rf_disabled") is False
                or ce_raw.get("p12_bk4_airplane_mode_locked") is False
            )
            ce_clean = {
                k: v
                for k, v in ce_raw.items()
                if k not in ("nd_preset", "wifi_enabled", "bt_enabled", "wifi_bt_rf_disabled", "p12_bk4_airplane_mode_locked")
            }
            cur_ce = {
                "cine_ei_base": self.cine_ei_base,
                "ei_index": self.ei_index,
                "shutter_mode": self.shutter_mode,
                "shutter_angle_deg": self.shutter_angle_deg,
                "shutter_speed_denom": self.shutter_speed_denom,
                "ecs_freq_hz": self.ecs_freq_hz,
                "sq_enabled": self.sq_enabled,
                "base_fps": self.base_fps,
                "sq_fps": self.sq_fps,
                "rec_state": self.rec_state,
                "tally_lamp_mode": self.tally_lamp_mode,
                "wired_io_mode": self.wired_io_mode,
            }
            ok_ce, new_cine_updates, err_ce = validate_cine_exposure_patch(ce_clean, current_state=cur_ce)
            if not ok_ce:
                return err_ce or {"ok": False, "error": "invalid_cine_exposure"}
            if "rec_tc_frames" in ce_raw and ce_raw["rec_tc_frames"] is not None:
                raw_tcf = ce_raw["rec_tc_frames"]
                if isinstance(raw_tcf, bool) or not isinstance(raw_tcf, int) or raw_tcf < 0:
                    return {"ok": False, "error": "invalid_rec_tc_frames", "message": "rec_tc_frames must be non-negative int"}
                ce_tc_frames = raw_tcf

        cm_raw = payload.get("color_and_media")
        new_cm_updates: dict[str, Any] = {}
        if cm_raw is not None:
            cur_cm = {
                "wb_mode": self.wb_mode,
                "kelvin": self.kelvin,
                "tint_gm": self.tint_gm,
                "shockless_wb": self.shockless_wb,
                "base_look": self.base_look,
                "cam_id": self.cam_id,
                "reel_num": self.reel_num,
                "cam_pos": self.cam_pos,
                "clip_seq": self.clip_seq,
                "dual_slot_mode": self.dual_slot_mode,
                "proxy_mode": self.proxy_mode,
            }
            ok_cm, new_cm_updates, err_cm = validate_color_and_media_patch(cm_raw, current_state=cur_cm)
            if not ok_cm:
                return err_cm or {"ok": False, "error": "invalid_color_and_media"}

        ga_raw = payload.get("gyroflow_anamorphic")
        new_ga_updates: dict[str, Any] = {}
        if ga_raw is not None:
            cur_ga = {
                "squeeze_factor": self.squeeze_factor,
                "ibis_mode": self.ibis_mode,
                "anamorphic_fallback_mode": self.anamorphic_fallback_mode,
                "ref_tone_enabled": self.ref_tone_enabled,
                "color_bars_enabled": self.color_bars_enabled,
                "limiter_enabled": self.limiter_enabled,
            }
            ok_ga, new_ga_updates, err_ga = validate_gyroflow_anamorphic_patch(ga_raw, current_state=cur_ga)
            if not ok_ga:
                return err_ga or {"ok": False, "error": "invalid_gyroflow_anamorphic"}

        tfc_raw = payload.get("touch_focus_ciz")
        new_tfc_updates: dict[str, Any] = {}
        if tfc_raw is not None:
            eff_aspect = new_assist_updates.get("aspect_marker", self.aspect_marker)
            eff_desqueeze = new_assist_updates.get("desqueeze", self.desqueeze)
            eff_sq_f = new_ga_updates.get("squeeze_factor", self.squeeze_factor)
            cur_tfc = {
                "touch_af_mode": self.touch_af_mode,
                "touch_x": self.touch_x,
                "touch_y": self.touch_y,
                "focus_mag": self.focus_mag,
                "false_color_mode": self.false_color_mode,
                "ciz_scale": self.ciz_scale,
                "ciz_res_mode": self.ciz_res_mode,
                "zoom_rocker_speed": self.zoom_rocker_speed,
            }
            ok_tfc, new_tfc_updates, err_tfc = validate_touch_focus_ciz_patch(
                tfc_raw,
                current_state=cur_tfc,
                aspect_marker=eff_aspect,
                desqueeze=eff_desqueeze,
                squeeze_factor=eff_sq_f,
            )
            if not ok_tfc:
                return err_tfc or {"ok": False, "error": "invalid_touch_focus_ciz"}

        smi_raw = payload.get("shotmark_and_iris")
        new_smi_updates: dict[str, Any] = {}
        if smi_raw is not None:
            eff_ei = int(new_cine_updates.get("ei_index", self.ei_index))
            eff_sm = str(new_cine_updates.get("shutter_mode", self.shutter_mode))
            eff_ang = float(new_cine_updates.get("shutter_angle_deg", self.shutter_angle_deg))
            eff_den = int(new_cine_updates.get("shutter_speed_denom", self.shutter_speed_denom))
            eff_ecs = float(new_cine_updates.get("ecs_freq_hz", self.ecs_freq_hz))
            eff_sq = bool(new_cine_updates.get("sq_enabled", self.sq_enabled))
            eff_bfps = float(new_cine_updates.get("base_fps", self.base_fps))
            eff_sfps = int(new_cine_updates.get("sq_fps", self.sq_fps))
            cur_smi = {
                "shotmarks": self.shotmarks,
                "iris_fstop": self.iris_fstop,
                "ae_shift_ev": self.ae_shift_ev,
                "metering_mode": self.metering_mode,
                "ch34_safety_pad_db": self.ch34_safety_pad_db,
                "user_bits_hex": self.user_bits_hex,
                "push_auto_iris_active": self.push_auto_iris_active,
                "last_scene_ev": self.last_scene_ev,
            }
            ok_smi, new_smi_updates, err_smi = validate_shotmark_and_iris_patch(
                smi_raw,
                current_state=cur_smi,
                rec_tc_frames=ce_tc_frames if ce_tc_frames is not None else self.rec_tc_frames,
                ei_index=eff_ei,
                shutter_mode=eff_sm,
                shutter_angle_deg=eff_ang,
                shutter_speed_denom=eff_den,
                ecs_freq_hz=eff_ecs,
                effective_fps=float(eff_sfps) if eff_sq else eff_bfps,
                base_fps=eff_bfps,
            )
            if not ok_smi:
                return err_smi or {"ok": False, "error": "invalid_shotmark_and_iris"}

        ic_raw = payload.get("interval_cache_lut_ftp")
        new_ic_updates: dict[str, Any] = {}
        ic_restored_shots: int | None = None
        if ic_raw is not None:
            if not isinstance(ic_raw, dict):
                return {"ok": False, "error": "invalid_interval_cache_lut_ftp", "message": "interval_cache_lut_ftp must be a JSON object"}
            if ic_raw.get("mechanical_curtain_actuations") not in (None, 0):
                return {
                    "ok": False,
                    "error": "mechanical_shutter_forbidden_in_interval_rec",
                    "message": "mechanical_curtain_actuations must be 0 in CAMSET",
                }
            if ic_raw.get("wf12_00342260_hits") not in (None, 0):
                return {
                    "ok": False,
                    "error": "p12_rf_off_violation",
                    "message": "wf12_00342260_hits must be 0 under P12 BK4 RF-off",
                }
            cur_ic = {
                "cache_seconds": self.cache_seconds,
                "codec_profile": self.codec_profile,
                "interval_rec_enabled": self.interval_rec_enabled,
                "interval_sec": self.interval_sec,
                "target_shots": self.target_shots,
                "shots_taken": self.shots_taken,
                "ae_tracking": self.ae_tracking,
                "ftps_mode": self.ftps_mode,
                "ftps_nic_driver": self.ftps_nic_driver,
            }
            ok_ic, new_ic_updates, err_ic = validate_interval_cache_lut_ftp_patch(ic_raw, current_state=cur_ic)
            if not ok_ic:
                return err_ic or {"ok": False, "error": "invalid_interval_cache_lut_ftp"}
            if "shots_taken" in ic_raw and ic_raw["shots_taken"] is not None:
                st_raw = ic_raw["shots_taken"]
                if isinstance(st_raw, bool) or not isinstance(st_raw, int) or st_raw < 0 or st_raw > 9999:
                    return {"ok": False, "error": "invalid_shots_taken", "message": "shots_taken must be int in [0, 9999]"}
                ic_restored_shots = st_raw
            for q_key in ("ftps_queue", "ftps_completed"):
                q_list = ic_raw.get(q_key)
                if isinstance(q_list, list):
                    for q_item in q_list:
                        if isinstance(q_item, dict) and q_item.get("path") is not None:
                            ok_qp, _, err_qc, err_qm = validate_ftps_media_path(q_item["path"])
                            if not ok_qp:
                                return {
                                    "ok": False,
                                    "error": err_qc or "emmc_path_traversal_blocked",
                                    "message": err_qm or "eMMC path traversal blocked in CAMSET FTPS queue",
                                }

        p109_raw = payload.get("mc_fleet_sdi_c2pa")
        new_p109_updates: dict[str, Any] = {}
        if p109_raw is not None:
            if not isinstance(p109_raw, dict):
                return {"ok": False, "error": "invalid_mc_fleet_sdi_c2pa", "message": "mc_fleet_sdi_c2pa must be a JSON object"}
            if p109_raw.get("wf12_00342260_hits") not in (None, 0):
                return {
                    "ok": False,
                    "error": "p12_rf_off_violation",
                    "message": "wf12_00342260_hits must be 0 under P12 BK4 RF-off",
                }
            if (
                p109_raw.get("c2pa_vault_status") not in (None, C2PA_VAULT_STATUS_LOCKED)
                or p109_raw.get("c2pa_spoofed") is True
                or p109_raw.get("hardware_attestation_claimed") is True
                or p109_raw.get("private_key_reads") not in (None, 0)
                or p109_raw.get("cnflasha_writes") not in (None, 0)
            ):
                return {
                    "ok": False,
                    "error": "c2pa_cnflasha_zero_touch_blocked",
                    "message": "C2PA 2.1 cnflasha zero-touch violation in CAMSET import",
                }
            cur_p109 = {
                "fleet_role": self.fleet_role,
                "fleet_cams_online": self.fleet_cams_online,
                "fleet_nic_driver": self.fleet_nic_driver,
                "gang_rec_trigger": self.gang_rec_trigger,
                "sdi_bridge_converter": self.sdi_bridge_converter,
                "hdmi_rec_control_enabled": self.hdmi_rec_control_enabled,
                "hdmi_tc_output_enabled": self.hdmi_tc_output_enabled,
                "recorder_range_expectation": self.recorder_range_expectation,
                "mount_type": self.mount_type,
                "lens_model": self.lens_model,
                "lens_kg": self.lens_kg,
                "focal_length_mm": self.focal_length_mm,
                "rod_support_15mm_lws": self.rod_support_15mm_lws,
            }
            eff_look = str(new_cm_updates.get("base_look", self.base_look))
            eff_io = str(new_cine_updates.get("wired_io_mode", self.wired_io_mode))
            ok_p109, new_p109_updates, err_p109 = validate_mc_fleet_sdi_c2pa_patch(
                p109_raw,
                current_state=cur_p109,
                base_look=eff_look,
                wired_io_mode=eff_io,
            )
            if not ok_p109:
                return err_p109 or {"ok": False, "error": "invalid_mc_fleet_sdi_c2pa"}

        p116_raw = payload.get("hdr_hlg_raw_breathing")
        new_p116_updates: dict[str, Any] = {}
        if p116_raw is not None:
            if not isinstance(p116_raw, dict):
                return {"ok": False, "error": "invalid_hdr_hlg_raw_breathing", "message": "hdr_hlg_raw_breathing must be a JSON object"}
            if p116_raw.get("external_output_assist_leak_px") not in (None, 0):
                return {
                    "ok": False,
                    "error": "display_assist_clean_feed_leak_blocked",
                    "message": "Gamma Display Assist clean-feed leak forbidden in CAMSET import",
                }
            cur_p116 = {
                "hlg_profile": self.hlg_profile,
                "color_gamut": self.color_gamut,
                "knee_mode": self.knee_mode,
                "detail_level": self.detail_level,
                "display_assist_mode": self.display_assist_mode,
                "ext_raw_mode": self.ext_raw_mode,
                "breathing_comp_mode": self.breathing_comp_mode,
            }
            eff_mount = str(new_p109_updates.get("mount_type", self.mount_type))
            eff_io = str(new_cine_updates.get("wired_io_mode", self.wired_io_mode))
            ok_p116, new_p116_updates, err_p116 = validate_hdr_hlg_raw_breathing_patch(
                p116_raw,
                current_state=cur_p116,
                mount_type=eff_mount,
                wired_io_mode=eff_io,
            )
            if not ok_p116:
                return err_p116 or {"ok": False, "error": "invalid_hdr_hlg_raw_breathing"}

        p123_raw = payload.get("uvc_srt_crsdk_ptp")
        new_p123_updates: dict[str, Any] = {}
        if p123_raw is not None:
            if not isinstance(p123_raw, dict):
                return {"ok": False, "error": "invalid_uvc_srt_crsdk_ptp", "message": "uvc_srt_crsdk_ptp must be a JSON object"}
            if p123_raw.get("emmc_mutation_bytes") not in (None, 0) or p123_raw.get("persistent_emmc_writes_authorized") is True:
                return {
                    "ok": False,
                    "error": "ptp_flash_opcode_blocked",
                    "blocked_opcode": "0x9280",
                    "message": "Destructive eMMC/flash mutation forbidden in CAMSET import",
                    "ptp_flash_opcodes_blocked": True,
                    "emmc_mutation_bytes": 0,
                }
            if p123_raw.get("uvc_osd_burnin_px") not in (None, 0):
                return {
                    "ok": False,
                    "error": "uvc_osd_burnin_blocked",
                    "message": "UVC OSD burn-in forbidden in CAMSET import",
                    "uvc_clean_feed_no_osd": True,
                    "uvc_osd_burnin_px": 0,
                }
            cur_p123 = {
                "uvc_mode": self.uvc_mode,
                "usb_link_speed": self.usb_link_speed,
                "uac_audio_enabled": self.uac_audio_enabled,
                "srt_mode": self.srt_mode,
                "srt_pbkeylen": self.srt_pbkeylen,
                "srt_latency_ms": self.srt_latency_ms,
                "rtmps_mode": self.rtmps_mode,
                "stream_bitrate_mbps": self.stream_bitrate_mbps,
                "crsdk_ptp_mode": self.crsdk_ptp_mode,
            }
            ok_p123, new_p123_updates, err_p123 = validate_uvc_srt_crsdk_ptp_patch(
                p123_raw,
                current_state=cur_p123,
            )
            if not ok_p123:
                return err_p123 or {"ok": False, "error": "invalid_uvc_srt_crsdk_ptp"}

        p12_clamped = (
            (payload.get("p12_bk4_airplane_mode_locked") is False)
            or ce_p12_tamper
            or any(k in sanitized_fx6_fields for k in ("wifi_ap_enabled", "wifi_enabled", "bt_enabled", "wifi_bt_rf_disabled", "p12_bk4_airplane_mode_locked"))
        )

        with self.cmd_lock:
            if new_cine_updates:
                self._apply_cine_exposure_updates_locked(new_cine_updates)
                if ce_tc_frames is not None:
                    self.rec_tc_frames = ce_tc_frames
                    self.last_cine_exp_cmd = format_cine_exp_command(self.get_cine_exposure())

            if new_cm_updates:
                self._apply_color_and_media_updates_locked(new_cm_updates)

            wb_to_cell = {
                "preset_5600k": 0,
                "preset_4300k": 1,
                "preset_3200k": 2,
                "atw": 3,
                "mem_a": 4,
                "mem_b": 5,
            }
            wb_cell_map = [
                ("preset_5600k", 5600),
                ("preset_4300k", 4300),
                ("preset_3200k", 3200),
                ("atw", None),
                ("mem_a", None),
                ("mem_b", None),
            ]
            lut_look_map = [
                "S-Cinetone",
                "S-Log3 / S-Gamut3.Cine",
                "ITU709",
                "709(800%)",
                "User 3D LUT",
                "User 3D LUT",
                "User 3D LUT",
                "User 3D LUT",
            ]
            for c_idx, c_val in new_cells.items():
                self.cell_vals[c_idx] = c_val
                if c_idx == 4:
                    cur_look_cell = BASE_LOOK_NLE_TAGS.get(self.base_look, {}).get("cell_lut_idx")
                    matches_user = (self.base_look == "User 3D LUT" and 4 <= c_val <= 7)
                    if (not new_cm_updates) or (not matches_user and cur_look_cell != c_val):
                        if 0 <= c_val < len(lut_look_map):
                            self.base_look = lut_look_map[c_val]
                elif c_idx == 5:
                    cur_wb_cell = wb_to_cell.get(self.wb_mode)
                    if (not new_cm_updates) or (cur_wb_cell != c_val):
                        if 0 <= c_val < len(wb_cell_map):
                            self.wb_mode, preset_k = wb_cell_map[c_val]
                            if preset_k is not None:
                                self.kelvin = preset_k
            self.cell_vals[3] = 0  # P4 ND=Clear Hardware Lock always enforced!
            p4_rejected = nd_tamper_val is not None
            if p4_rejected:
                self.p4_nd_reject_count += 1
                self.p4_lock_attempts += 1

            for skey, srec in new_slots.items():
                self.user_lut_slots[skey] = srec
            for skey, tbl in new_slot_tables.items():
                self._user_lut_33_ram_tables[skey] = tbl

            if new_rtmd is not None:
                self.rtmd_0xe304_ibis_lock = new_rtmd
                self.ibis_idx = RTMD_0XE304_MODES.index(new_rtmd)

            if "aspect_marker" in new_assist_updates:
                self.aspect_marker = new_assist_updates["aspect_marker"]
            if "zebra_mode" in new_assist_updates:
                self.zebra_mode = new_assist_updates["zebra_mode"]
            if "peaking_mode" in new_assist_updates:
                self.peaking_mode = new_assist_updates["peaking_mode"]
            if "desqueeze" in new_assist_updates:
                self.desqueeze = new_assist_updates["desqueeze"]
                self.squeeze_factor = _parse_desqueeze_factor_from_str(self.desqueeze)

            for idx, val in new_ch_db.items():
                self.audio_ch_db[idx] = val
            if new_phantom is not None:
                self.xlr_phantom_48v = new_phantom
            if new_attached is not None:
                self.xlr_handle_attached = new_attached

            if not self.xlr_handle_attached:
                self.xlr_idx = 2
            elif "xlr" in cparams and cparams["xlr"] is not None:
                xlr_presets = CINEMA_PARAM_SPECS["xlr"]["presets"]
                x_low = str(cparams["xlr"]).strip().lower()
                x_idx = next((idx for idx, cand in enumerate(xlr_presets) if cand.lower() == x_low), None)
                if x_idx is not None:
                    self.xlr_idx = x_idx
            else:
                self.xlr_idx = 0 if self.xlr_phantom_48v else 1

            if new_lang_code is not None and new_lang_id is not None:
                self.lang_code = new_lang_code
                self.lang_id = new_lang_id

            self.p12_bk4_airplane_mode_locked = True  # P12 BK4 Airplane-Mode shadow lock always enforced!
            self.last_wb_media_cmd = format_wb_media_command(self.get_color_and_media())
            if new_ga_updates:
                self._apply_gyroflow_anamorphic_updates_locked(new_ga_updates)
            if new_tfc_updates:
                self._apply_touch_focus_ciz_updates_locked(new_tfc_updates)
            else:
                self.last_touch_af_ciz_cmd = format_touch_focus_ciz_command(self.get_touch_focus_ciz())
            if new_smi_updates:
                self._apply_shotmark_and_iris_updates_locked(new_smi_updates)
            else:
                self.last_shotmark_iris_cmd = format_shotmark_iris_command(self.get_shotmark_and_iris())
            self.last_gyroflow_anamorphic_cmd = format_gyroflow_anamorphic_command(self.get_gyroflow_anamorphic())
            if ic_raw is not None:
                if isinstance(ic_raw.get("ftps_queue"), list):
                    self.ftps_queue = [
                        {
                            "job_id": str(j.get("job_id", f"ftps-{idx+1:04d}")),
                            "path": str(j.get("path", "")),
                            "kind": str(j.get("kind", "original")),
                            "transport": f"USB_LAN_{self.ftps_nic_driver}",
                            "nic_driver": self.ftps_nic_driver,
                            "tls_version": self.ftps_tls_version,
                            "data_mode": "PASV",
                            "p12_rf_off_enforced": True,
                            "wf12_00342260_hits": 0,
                            "status": "QUEUED",
                        }
                        for idx, j in enumerate(ic_raw["ftps_queue"][-64:])
                        if isinstance(j, dict) and j.get("path")
                    ]
                if isinstance(ic_raw.get("ftps_completed"), list):
                    self.ftps_completed = [
                        {
                            "job_id": str(j.get("job_id", f"ftps-{idx+1:04d}")),
                            "path": str(j.get("path", "")),
                            "kind": str(j.get("kind", "original")),
                            "transport": f"USB_LAN_{self.ftps_nic_driver}",
                            "nic_driver": self.ftps_nic_driver,
                            "tls_version": self.ftps_tls_version,
                            "data_mode": "PASV",
                            "p12_rf_off_enforced": True,
                            "wf12_00342260_hits": 0,
                            "status": "COMPLETED",
                        }
                        for idx, j in enumerate(ic_raw["ftps_completed"][-64:])
                        if isinstance(j, dict) and j.get("path")
                    ]
                self._apply_interval_cache_lut_ftp_updates_locked(
                    new_ic_updates,
                    restored_shots_taken=ic_restored_shots,
                )
            else:
                self.last_interval_cache_lut_ftp_cmd = format_interval_cache_lut_ftp_command(
                    self.get_interval_cache_lut_ftp()
                )
            if p109_raw is not None:
                self._apply_mc_fleet_sdi_c2pa_updates_locked(
                    new_p109_updates,
                    is_reset=bool(p109_raw.get("reset") is True),
                    preserve_rec_state=("rec_state" in new_cine_updates),
                )
            else:
                self.last_mc_fleet_sdi_c2pa_cmd = format_mc_fleet_sdi_c2pa_command(
                    self.get_mc_fleet_sdi_c2pa()
                )
            if p116_raw is not None:
                self._apply_hdr_hlg_raw_breathing_updates_locked(
                    new_p116_updates,
                    is_reset=bool(p116_raw.get("reset") is True),
                    preserve_wired_io=("wired_io_mode" in new_cine_updates),
                )
            else:
                self.last_hdr_hlg_raw_breathing_cmd = format_hdr_hlg_raw_breathing_command(
                    self.get_hdr_hlg_raw_breathing()
                )
            if p123_raw is not None:
                if "crsdk_last_safe_opcode" in p123_raw and "ptp_opcode" not in p123_raw and "crsdk_opcode" not in p123_raw:
                    saved_op = _parse_ptp_opcode(p123_raw.get("crsdk_last_safe_opcode"))
                    if saved_op is not None and saved_op in CRSDK_SAFE_D2XX_OPCODES:
                        new_p123_updates["crsdk_safe_opcode"] = saved_op
                self._apply_uvc_srt_crsdk_ptp_updates_locked(
                    new_p123_updates,
                    is_reset=bool(p123_raw.get("reset") is True),
                )
            else:
                self.last_uvc_srt_crsdk_ptp_cmd = format_uvc_srt_crsdk_ptp_command(
                    self.get_uvc_srt_crsdk_ptp()
                )

            if p4_rejected:
                self.last_toast = (
                    f"P4 ND=Clear Lock Enforced: rejected ND={nd_tamper_val!r} in CAMSET "
                    f"(p4_nd_reject_count={self.p4_nd_reject_count})"
                )
            elif is_fx6_fleet:
                self.last_toast = (
                    f"FX6->FX3 Fleet CAMSET Sanitized ({len(sanitized_fx6_fields)} fields clamped: "
                    f"ND=Clear, SDI=CONTAINED_DISABLED, RF=OFF)"
                )
            elif p12_clamped:
                self.last_toast = "CAMSET Imported (P12 BK4 Airplane-Mode shadow lock preserved)"
            else:
                self.last_toast = "CAMSET fx6_on_fx3_camset_v1 Imported & Applied"

            wrote, synced = self._sync_mailbox_and_capture()
            return {
                "ok": True,
                "schema": "fx6_on_fx3_camset_v1",
                "fx6_fleet_sanitized": is_fx6_fleet,
                "sanitized_fx6_fields": sanitized_fx6_fields,
                "sanitized_fx6_details": sanitized_fx6_details,
                "nd_preset": "Clear",
                "sdi_out": "CONTAINED_DISABLED",
                "wifi_bt_rf_disabled": True,
                "p4_nd_motor_faults": 0,
                "p4_nd_rejected": p4_rejected,
                "p4_nd_clamped": p4_rejected,
                "p4_nd_hardware_absent": True,
                "p4_nd_reject_count": self.p4_nd_reject_count,
                "p4_lock_attempts": self.p4_lock_attempts,
                "p12_bk4_airplane_mode_locked": True,
                "p12_bk4_clamped": p12_clamped,
                "toast": self.last_toast,
                "wrote_mailbox": wrote,
                "guest_synced": synced,
                "assist_tools": self.get_assist_tools(),
                "cine_exposure": self.get_cine_exposure(),
                "color_and_media": self.get_color_and_media(),
                "touch_focus_ciz": self.get_touch_focus_ciz(),
                "shotmark_and_iris": self.get_shotmark_and_iris(),
                "gyroflow_anamorphic": self.get_gyroflow_anamorphic(),
                "interval_cache_lut_ftp": self.get_interval_cache_lut_ftp(),
                "mc_fleet_sdi_c2pa": self.get_mc_fleet_sdi_c2pa(),
                "hdr_hlg_raw_breathing": self.get_hdr_hlg_raw_breathing(),
                "uvc_srt_crsdk_ptp": self.get_uvc_srt_crsdk_ptp(),
                "cinema_params": self.get_cinema_params(),
                "stage_b_telemetry": self.get_stage_b_telemetry(),
                "status": self.get_status(),
            }

    def press_fx3_button(self, button: Any) -> dict[str, Any]:
        raw_btn = str(button or "").strip().upper()
        btn = FX3_BUTTON_ALIASES.get(raw_btn, raw_btn)
        if btn not in FX3_BUTTON_MAP:
            return {
                "ok": False,
                "error": f"Unknown FX3 button: {button!r}",
                "supported_buttons": list(FX3_BUTTON_MAP.keys()),
            }
        with self.cmd_lock:
            spec = FX3_BUTTON_MAP[btn]
            kind = spec["kind"]
            if kind == "home":
                self.page = 0
                self.sel_box = 4
                self.menu_depth = 0
                self.cmd_seq += 1
            elif kind == "disp_cycle":
                self.page = 6 if self.page == 16 else 16
                self.sel_box = 0
                self.menu_depth = 0
                self.cmd_seq += 1
            elif kind == "c1_baselook":
                if self.page == 1 and self.menu_cat == 4 and self.menu_depth >= 2:
                    self.menu_item = (self.menu_item + 1) % CELL_N_VALS[4]
                    self.cell_vals[4] = self.menu_item
                else:
                    self.page = 1
                    self.menu_cat = 4
                    self.menu_item = self.cell_vals[4] % CELL_N_VALS[4]
                    self.menu_depth = 2
                    self.sel_box = 0
                self.last_toast = f"Base Look / 3D LUT: {CINEMA_PARAM_SPECS['lut']['presets'][self.cell_vals[4]]}"
                self.cmd_seq += 1
            elif kind == "c2_wb":
                if self.page == 3 and (self.sel_box % 6) == 5:
                    self.cell_vals[5] = (self.cell_vals[5] + 1) % CELL_N_VALS[5]
                else:
                    self.page = 3
                    self.sel_box = 5
                    self.menu_depth = 0
                self.last_toast = f"White Balance: {CINEMA_PARAM_SPECS['wb']['presets'][self.cell_vals[5]]}"
                self.cmd_seq += 1
            elif kind == "page":
                self.page = int(spec["page"])
                self.sel_box = 0
                self.menu_depth = 0
                self.cmd_seq += 1
            elif kind == "key":
                self._step_local_state(KEY_CODES[spec["key"]])

            phy_val = int(spec["phy_code"], 16)
            infra_val = int(spec["infra_code"], 16)
            self.last_p10_hwcode = ((phy_val & 0xFFFF) << 16) | (infra_val & 0xFFFF)
            self.last_p10_telemetry = {
                "button": btn,
                "label": spec["label"],
                "phy_code": spec["phy_code"],
                "infra_code": spec["infra_code"],
                "p10_code": spec["p10_code"],
                "p10_symbol": spec["p10_symbol"],
                "target_page": self.page,
                "cmd_seq": self.cmd_seq,
            }

            wrote = self._write_ctrl_mailbox()
            synced = False
            if wrote:
                synced = self._wait_for_frame_seq(self.cmd_seq, timeout=3.2)
                self.capture_live_gpe0()

            return {
                "ok": True,
                "button": btn,
                "p10_telemetry": dict(self.last_p10_telemetry),
                "wrote_mailbox": wrote,
                "guest_synced": synced,
                "status": self.get_status(),
            }

    def apply_key_or_state(self, body: dict[str, Any]) -> dict[str, Any]:
        with self.cmd_lock:
            key = str(body.get("key", "")).upper().strip()
            lang_changed = False
            if "lang" in body:
                code = self._normalize_lang(body["lang"])
                packs = discover_available_lang_packs()
                if code is not None and code in packs and packs[code]["available"]:
                    self.lang_code = code
                    self.lang_id = int(packs[code]["id"])
                    lang_changed = True

            if "page" in body:
                p_val = body["page"]
                if isinstance(p_val, str) and p_val.lower() in LEGACY_PAGE_MAP:
                    self.page = LEGACY_PAGE_MAP[p_val.lower()]
                else:
                    self.page = int(p_val) % 25
                if "sel_box" not in body:
                    self.sel_box = 4 if self.page == 0 else 0
                if "menu_depth" not in body and self.page != 1:
                    self.menu_depth = 0
            if "table_off" in body and "table_rows" in body:
                self.page = 24
                self.table_off = int(body["table_off"])
                self.table_rows = int(body["table_rows"])
                self.table_off2 = int(body.get("table_off2", 0))
                self.table_rows2 = int(body.get("table_rows2", 0))
                if "sel_box" not in body:
                    self.sel_box = 0
                for idx, p in enumerate(ALL_128_PAGES):
                    if p["off"] == self.table_off:
                        self.table_idx128 = idx
                        break
            if "sel_box" in body:
                self.sel_box = int(body["sel_box"])
            if "menu_cat" in body:
                self.menu_cat = int(body["menu_cat"]) % 11
                self.menu_item = 0
            if "menu_item" in body:
                self.menu_item = int(body["menu_item"])
            if "menu_depth" in body:
                self.menu_depth = int(body["menu_depth"])

            if key in KEY_CODES:
                self._step_local_state(KEY_CODES[key])
            elif lang_changed or any(k in body for k in ("page", "sel_box", "menu_cat", "menu_item", "menu_depth", "table_off")):
                self.cmd_seq += 1

            wrote = self._write_ctrl_mailbox()
            synced = False
            if wrote:
                synced = self._wait_for_frame_seq(self.cmd_seq, timeout=3.2)
                self.capture_live_gpe0()

            return {
                "ok": True,
                "key": key,
                "wrote_mailbox": wrote,
                "guest_synced": synced,
                "status": self.get_status(),
            }

    def jump_to_page(self, body: Any) -> dict[str, Any]:
        """Jump directly to any flagship, 11-category, or 128-page catalog target."""
        if not isinstance(body, dict):
            return {"ok": False, "error": "invalid_request_body", "message": "Request body must be a JSON object"}

        catalog = build_menu_catalog()
        items = catalog["items"]
        by_id = {it["page_id"].lower(): it for it in items}
        entry: dict[str, Any] | None = None

        raw_pid = body.get("page_id") if body.get("page_id") is not None else body.get("id")
        if raw_pid is not None and str(raw_pid).strip() != "":
            pid_str = str(raw_pid).strip()
            pid_low = pid_str.lower()
            entry = by_id.get(pid_low)
            if entry is None and pid_low.startswith("page_") and pid_low[5:].isdigit():
                p_num = int(pid_low[5:])
                entry = next((it for it in items if it.get("kind") == "flagship" and it["macro"].get("page") == p_num), None)
            if entry is None and pid_str.isdigit():
                idx_num = int(pid_str)
                entry = by_id.get(f"p128_{idx_num:03d}")
            if entry is None:
                return {
                    "ok": False,
                    "error": "unknown_page_id",
                    "message": f"Unknown menu catalog page_id: {raw_pid!r}",
                }
        elif body.get("idx128") is not None and str(body.get("idx128")).strip() != "":
            if isinstance(body["idx128"], bool):
                return {"ok": False, "error": "invalid_idx128", "message": "idx128 cannot be bool"}
            try:
                idx_num = int(body["idx128"])
            except (TypeError, ValueError):
                return {"ok": False, "error": "invalid_idx128", "message": f"Invalid idx128: {body['idx128']!r}"}
            entry = by_id.get(f"p128_{idx_num:03d}")
            if entry is None:
                return {
                    "ok": False,
                    "error": "idx128_out_of_range",
                    "message": f"idx128={idx_num} not found in 128-page table (len={len(ALL_128_PAGES)})",
                }
        elif (body.get("query") is not None and str(body.get("query")).strip() != "") or (
            body.get("q") is not None and str(body.get("q")).strip() != ""
        ):
            q_val = str(body.get("query") if body.get("query") is not None else body.get("q")).strip()
            cat_val = str(body.get("category") or "").strip()
            res_search = search_menu_catalog(query=q_val, category=cat_val)
            if not res_search["items"]:
                return {
                    "ok": False,
                    "error": "menu_search_no_match",
                    "message": f"No FX6 menu catalog entry matched query={q_val!r}",
                    "query": q_val,
                }
            entry = res_search["items"][0]
        elif body.get("menu_cat") is not None and str(body.get("menu_cat")).strip() != "":
            try:
                c_idx = int(body["menu_cat"]) % 11
            except (TypeError, ValueError):
                return {"ok": False, "error": "invalid_menu_cat", "message": f"Invalid menu_cat: {body['menu_cat']!r}"}
            entry = next((it for it in items if it.get("kind") == "category" and it.get("cat_idx") == c_idx), None)
        elif body.get("page") is not None and str(body.get("page")).strip() != "":
            p_raw = body["page"]
            if isinstance(p_raw, str) and p_raw.lower() in LEGACY_PAGE_MAP:
                p_num = LEGACY_PAGE_MAP[p_raw.lower()]
            else:
                try:
                    p_num = int(p_raw) % 25
                except (TypeError, ValueError):
                    return {"ok": False, "error": "invalid_page", "message": f"Invalid page: {p_raw!r}"}
            entry = next((it for it in items if it.get("kind") == "flagship" and it["macro"].get("page") == p_num), None)
            if entry is None:
                entry = {
                    "page_id": f"page_{p_num}",
                    "id": f"page_{p_num}",
                    "kind": "page",
                    "zh_title": PAGE_NAMES.get(p_num, f"Page {p_num}"),
                    "en_title": PAGE_NAMES.get(p_num, f"Page {p_num}"),
                    "category": "Technical",
                    "category_zh": "系统",
                    "macro": {"page": p_num, "sel_box": 4 if p_num == 0 else 0, "menu_depth": 0},
                    "fx3_bridge_note": f"Direct FX6 page {p_num}",
                    "keywords": [],
                }
        else:
            return {
                "ok": False,
                "error": "missing_jump_target",
                "message": "Provide 'page_id', 'idx128', 'query', 'menu_cat', or 'page'",
            }

        assert entry is not None
        macro = dict(entry["macro"])
        with self.cmd_lock:
            target_page = int(macro.get("page", 0)) % 25
            self.page = target_page
            if "sel_box" in macro:
                self.sel_box = int(macro["sel_box"])
            else:
                self.sel_box = 4 if target_page == 0 else 0
            if "menu_cat" in macro:
                self.menu_cat = int(macro["menu_cat"]) % 11
            if "menu_item" in macro:
                self.menu_item = int(macro["menu_item"])
            elif "menu_cat" in macro:
                self.menu_item = 0
            if "menu_depth" in macro:
                self.menu_depth = int(macro["menu_depth"])
            elif target_page != 1:
                self.menu_depth = 0
            if target_page == 24 and "table_off" in macro and "table_rows" in macro:
                self.table_off = int(macro["table_off"])
                self.table_rows = int(macro["table_rows"])
                self.table_off2 = int(macro.get("table_off2", 0))
                self.table_rows2 = int(macro.get("table_rows2", 0))
                if "idx128" in macro:
                    self.table_idx128 = int(macro["idx128"])
                else:
                    for idx, p in enumerate(ALL_128_PAGES):
                        if p["off"] == self.table_off:
                            self.table_idx128 = idx
                            break

            self.last_toast = f"Jump -> {entry['en_title']} ({entry['fx3_bridge_note']})"
            self.cmd_seq += 1
            wrote = self._write_ctrl_mailbox()
            synced = False
            if wrote:
                synced = self._wait_for_frame_seq(self.cmd_seq, timeout=3.2)
                self.capture_live_gpe0()

            return {
                "ok": True,
                "page_id": entry["page_id"],
                "entry": dict(entry),
                "macro": macro,
                "toast": self.last_toast,
                "wrote_mailbox": wrote,
                "guest_synced": synced,
                "status": self.get_status(),
            }

    def verify_multilang_diff(self, page: int | None = None) -> dict[str, Any]:
        """Switch en -> zh -> ja in-guest, compute GPE0 SHA-256 & pixel deltas, then restore language."""
        packs = discover_available_lang_packs()
        missing = [lc for lc in ("en", "zh", "ja") if not packs.get(lc, {}).get("available")]
        if missing:
            return {
                "ok": False,
                "error": "missing_lang_packs",
                "message": f"Missing donor language packs for multilingual GPE0 diff: {missing}",
                "missing_langs": missing,
                "available_langs": [k for k, v in packs.items() if v["available"]],
            }

        test_hook = self._gpe0_test_capture_hook
        is_live = self.is_running() and self.live_ready and not self.crashed
        if not is_live and test_hook is None:
            return {
                "ok": False,
                "error": "vm_not_ready",
                "message": "QEMU guest is not LIVE_GPE0_READY; start VM before running in-guest EN/ZH/JA pixel-diff verification.",
                "stage": self.get_status()["stage"],
            }

        with self.cmd_lock:
            orig_lang = self.lang_code
            orig_lang_id = self.lang_id
            orig_page = self.page
            orig_sel = self.sel_box
            orig_cat = self.menu_cat
            orig_item = self.menu_item
            orig_depth = self.menu_depth
            start_ack = self.ack_seq

            if page is not None:
                self.page = int(page) % 25
                if self.page == 0:
                    self.sel_box = 4
                elif self.page == 1:
                    self.sel_box = 0

            captures: dict[str, dict[str, Any]] = {}
            raw_frames: dict[str, bytes] = {}
            ack_seqs: list[int] = []
            step_error: str | None = None

            try:
                for lc in ("en", "zh", "ja"):
                    pack = packs[lc]
                    self.lang_code = lc
                    self.lang_id = int(pack["id"])
                    self.cmd_seq += 1

                    if test_hook is not None:
                        raw = test_hook(lc, self.page, self.cmd_seq)
                        self.ack_seq = self.cmd_seq
                        png, nz = gpe0_raw_to_png(raw)
                        if nz > 0 and png:
                            self.last_raw_gpe0 = raw[:GPE0_BYTES]
                            self.last_png = png
                            self.last_nz = nz
                        wrote, synced = True, True
                    else:
                        wrote = self._write_ctrl_mailbox()
                        synced = self._wait_for_frame_seq(self.cmd_seq, timeout=3.2) if wrote else False
                        raw, png, nz = self._capture_live_gpe0_with_raw()

                    if not wrote or not synced or len(raw) < GPE0_BYTES or nz <= 0:
                        step_error = f"Capture failed for lang={lc} (wrote={wrote}, synced={synced}, raw_len={len(raw)}, nz={nz})"
                        break

                    frame_raw = raw[:GPE0_BYTES]
                    sha = hashlib.sha256(frame_raw).hexdigest()
                    captures[lc] = {
                        "lang": lc,
                        "lang_id": int(pack["id"]),
                        "cmd_seq": self.cmd_seq,
                        "ack_seq": self.ack_seq,
                        "sha256": sha,
                        "gpe0_bytes": GPE0_BYTES,
                        "nonzero_px": nz,
                    }
                    raw_frames[lc] = frame_raw
                    ack_seqs.append(self.ack_seq)
            finally:
                if not self.crashed:
                    self.lang_code = orig_lang
                    self.lang_id = orig_lang_id
                    if page is not None:
                        self.page = orig_page
                        self.sel_box = orig_sel
                        self.menu_cat = orig_cat
                        self.menu_item = orig_item
                        self.menu_depth = orig_depth
                    self.cmd_seq += 1
                    if test_hook is not None:
                        raw_rest = test_hook(self.lang_code, self.page, self.cmd_seq)
                        self.ack_seq = self.cmd_seq
                        png_r, nz_r = gpe0_raw_to_png(raw_rest)
                        if nz_r > 0 and png_r:
                            self.last_raw_gpe0 = raw_rest[:GPE0_BYTES]
                            self.last_png = png_r
                            self.last_nz = nz_r
                    elif self.is_running() and self.live_ready and not self.crashed:
                        if self._write_ctrl_mailbox():
                            self._wait_for_frame_seq(self.cmd_seq, timeout=3.2)
                            self._capture_live_gpe0_with_raw()

            if step_error is not None:
                return {
                    "ok": False,
                    "error": "multilang_capture_failed",
                    "message": step_error,
                    "restored_lang": self.lang_code,
                    "captures": captures,
                    "status": self.get_status(),
                }

            d_en_zh = compute_gpe0_frame_diff(raw_frames["en"], raw_frames["zh"])
            d_zh_ja = compute_gpe0_frame_diff(raw_frames["zh"], raw_frames["ja"])
            d_en_ja = compute_gpe0_frame_diff(raw_frames["en"], raw_frames["ja"])

            ack_monotonic = (
                len(ack_seqs) == 3
                and ack_seqs[0] > start_ack
                and ack_seqs[0] < ack_seqs[1] < ack_seqs[2]
                and self.ack_seq > ack_seqs[2]
            )
            distinct = (
                d_en_zh["diff_bytes"] > 0
                and d_zh_ja["diff_bytes"] > 0
                and d_en_ja["diff_bytes"] > 0
            )
            ok = bool(ack_monotonic and distinct)
            self.last_toast = (
                f"EN/ZH/JA GPE0 Diff: EN<>ZH={d_en_zh['diff_bytes']}B ({d_en_zh['diff_pixels']}px), "
                f"ZH<>JA={d_zh_ja['diff_bytes']}B ({d_zh_ja['diff_pixels']}px), restored={self.lang_code}"
            )
            receipt = {
                "ok": ok,
                "page": int(page) % 25 if page is not None else self.page,
                "restored_lang": self.lang_code,
                "sequence": ["en", "zh", "ja"],
                "ack_seq_start": start_ack,
                "ack_seqs": ack_seqs,
                "ack_seq_end": self.ack_seq,
                "ack_seq_monotonic": ack_monotonic,
                "captures": captures,
                "en_vs_zh_diff_bytes": d_en_zh["diff_bytes"],
                "en_vs_zh_diff_pixels": d_en_zh["diff_pixels"],
                "zh_vs_ja_diff_bytes": d_zh_ja["diff_bytes"],
                "zh_vs_ja_diff_pixels": d_zh_ja["diff_pixels"],
                "en_vs_ja_diff_bytes": d_en_ja["diff_bytes"],
                "en_vs_ja_diff_pixels": d_en_ja["diff_pixels"],
                "all_distinct": distinct,
                "toast": self.last_toast,
                "status": self.get_status(),
            }
            if not ok:
                receipt["error"] = "zero_pixel_diff_detected" if not distinct else "ack_seq_non_monotonic"
                receipt["message"] = "Multilingual GPE0 diff or monotonic ack_seq invariant failed"
            self.last_multilang_diff = {
                k: v for k, v in receipt.items() if k != "status"
            }
            return receipt

    def _step_local_state(self, kcode: int) -> None:
        cat_n_items = [6, 5, 7, 7, 7, 7, 7, 7, 7, 7, 7][self.menu_cat % 11]
        if self.menu_depth >= 2:
            cat_n_items = 5 if (self.menu_cat % 11) == 3 else 7

        if kcode == 1:  # UP
            if self.page in (0, 3):
                self.sel_box = (self.sel_box - 3) if self.sel_box >= 3 else (self.sel_box + 3)
            elif self.page == 1:
                if self.menu_depth == 0:
                    self.menu_cat = (self.menu_cat + 10) % 11
                    self.menu_item = 0
                else:
                    self.menu_item = (self.menu_item - 1) if self.menu_item > 0 else (cat_n_items - 1)
            else:
                self.sel_box = max(0, self.sel_box - 1)
        elif kcode == 2:  # DOWN
            if self.page in (0, 3):
                self.sel_box = (self.sel_box + 3) % 6
            elif self.page == 1:
                if self.menu_depth == 0:
                    self.menu_cat = (self.menu_cat + 1) % 11
                    self.menu_item = 0
                else:
                    self.menu_item = (self.menu_item + 1) % cat_n_items
            else:
                self.sel_box += 1
        elif kcode == 3:  # LEFT
            if self.page in (0, 3):
                self.sel_box = (self.sel_box + 5) % 6
            elif self.page == 1:
                if self.menu_depth > 0:
                    self.menu_depth -= 1
                    self.menu_item = 0
            else:
                self.sel_box = max(0, self.sel_box - 1)
        elif kcode == 4:  # RIGHT
            if self.page in (0, 3):
                self.sel_box = (self.sel_box + 1) % 6
            elif self.page == 1:
                if self.menu_depth == 0:
                    self.menu_depth = 1
                    self.menu_item = 0
                elif self.menu_depth == 1:
                    self.menu_depth = 2
                    self.menu_item = 0
            else:
                self.sel_box += 1
        elif kcode == 5:  # SET
            if self.page in (0, 3):
                c = self.sel_box % 6
                if c == 3:
                    self.cell_vals[3] = 0
                    self.p4_lock_attempts += 1
                    self.last_toast = CINEMA_PARAM_SPECS["nd"]["lock_reason"]
                else:
                    self.cell_vals[c] = (self.cell_vals[c] + 1) % CELL_N_VALS[c]
                    param_key = ["fps", "ei", "shutter", "nd", "lut", "wb"][c]
                    spec = CINEMA_PARAM_SPECS[param_key]
                    self.last_toast = f"{spec['label']}: {spec['presets'][self.cell_vals[c]]}"
            elif self.page == 2:
                self.cell_vals[4] = (self.cell_vals[4] + 1) % CELL_N_VALS[4]
                self.last_toast = f"Base Look / 3D LUT: {CINEMA_PARAM_SPECS['lut']['presets'][self.cell_vals[4]]}"
            elif self.page == 1:
                if self.menu_depth == 0:
                    self.menu_depth = 1
                    self.menu_item = 0
                elif self.menu_depth == 1:
                    if self.menu_cat == 3 and self.menu_item == 6:
                        self.page = 4
                        self.sel_box = 0
                    elif self.menu_cat == 4 and 1 <= self.menu_item <= 6:
                        self.cell_vals[4] = (self.menu_item - 1) % CELL_N_VALS[4]
                        self.last_toast = f"Base Look / 3D LUT: {CINEMA_PARAM_SPECS['lut']['presets'][self.cell_vals[4]]}"
                    else:
                        self.menu_depth = 2
                        self.menu_item = 0
                else:
                    if self.menu_cat == 3:
                        self.rec_fmt_idx = self.menu_item % 5
                    else:
                        self.cell_vals[4] = self.menu_item % CELL_N_VALS[4]
                        self.last_toast = f"Base Look / 3D LUT: {CINEMA_PARAM_SPECS['lut']['presets'][self.cell_vals[4]]}"
                    self.menu_depth = 1
            elif self.page == 24 and ALL_128_PAGES:
                self.table_idx128 = (self.table_idx128 + 1) % len(ALL_128_PAGES)
                p = ALL_128_PAGES[self.table_idx128]
                self.table_off = p["off"]
                self.table_rows = p["rows"]
                self.sel_box = 0
            else:
                self.menu_depth = (self.menu_depth + 1) % 3
                self.sel_box = 0
        elif kcode == 6:  # BACK
            if self.page == 1 and self.menu_depth > 0:
                self.menu_depth -= 1
                self.menu_item = 0
            elif self.page >= 5 and self.menu_depth > 0:
                self.menu_depth = 0
                self.sel_box = 0
            else:
                self.page = 0
                self.sel_box = 4
        elif kcode == 7:  # MENU
            if self.page == 1:
                self.page = 0
                self.sel_box = 4
            else:
                self.page = 1
                self.menu_depth = 0
        elif kcode == 8:  # HOME
            self.page = 0
            self.sel_box = 4
        elif kcode == 9:  # DISP
            self.page = (self.page + 1) % 24
            self.sel_box = 4 if self.page == 0 else 0
            self.menu_depth = 0

        self.cmd_seq += 1

    def get_status(self) -> dict[str, Any]:
        running = self.is_running()
        elapsed = round(time.time() - self.started_at, 1) if (running and self.started_at) else 0.0
        serial_tail = ""
        stage = "STOPPED"
        if self.serial_log.exists():
            raw = self.serial_log.read_bytes()
            serial_window = raw[-524288:].decode("latin1", errors="replace")
            if "APPFW_SEGV" in serial_window or "Entering exception monitor" in serial_window or "[Exception Syndrome]" in serial_window:
                self.live_ready = False
                self.crashed = True
                is_segv = "APPFW_SEGV" in serial_window
                for ln in reversed(serial_window.splitlines()):
                    if "APPFW_SEGV" in ln or "Abort (PC=" in ln or "Entering exception monitor" in ln:
                        self.crash_reason = ln.strip()
                        break
                stage = "CRASHED_APPFW_SEGV" if is_segv else "CRASHED_EXCEPTION_MONITOR"
            elif self.live_ready or "FX6_LIVE_READY" in serial_window or "FX6_LIVE_FRAME" in serial_window:
                if not self.live_ready:
                    self.live_ready = True
                    matches = re.findall(
                        r"FX6_LIVE_(?:READY|FRAME) seq=(\d+) page=(\d+) sel=(\d+) cat=(\d+) item=(\d+) depth=(\d+) nz=(\d+) text_ok=(\d+) fill=(\d+) icon=(\d+)(?: lang=(\d+))?",
                        serial_window,
                    )
                    if matches:
                        last = matches[-1]
                        self.ack_seq = int(last[0])
                        self.last_nz = int(last[6])
                        self.last_text_ok = int(last[7])
                        self.last_fill_n = int(last[8])
                        self.last_icon_n = int(last[9])
                    if self.cmd_seq > self.ack_seq and self._write_ctrl_mailbox():
                        self._wait_for_frame_seq(self.cmd_seq, timeout=3.2)
                    self.capture_live_gpe0()
                stage = "LIVE_GPE0_READY"
            elif "FX6_LIVE appfw=" in serial_window or "Application_System_Init" in serial_window:
                stage = "LOADING_APPFW_UI"
            elif "Linux version" in serial_window:
                stage = "BOOTING_KERNEL"
            elif running:
                stage = "STARTING_QEMU"
            clean_lines = [
                ln for ln in serial_window.splitlines()
                if "model_mutex.cpp" not in ln and "model::model_lock" not in ln
            ]
            serial_tail = "\n".join(clean_lines[-18:])

        if self.page == 24 and ALL_128_PAGES:
            p = ALL_128_PAGES[self.table_idx128 % len(ALL_128_PAGES)]
            page_name = f"128-Page #{p['idx']:03d} ({p['off_hex']}, {p['rows']} rows | {p['first_name']})"
        else:
            page_name = PAGE_NAMES.get(self.page, f"Page {self.page}")

        lang_packs = discover_available_lang_packs()
        cur_pack = LANG_PACKS.get(self.lang_code, LANG_PACKS["en"])

        return {
            "running": running,
            "pid": self.proc.pid if running and self.proc else None,
            "port": self.port,
            "workdir": str(self.workdir),
            "elapsed_sec": elapsed,
            "stage": stage,
            "live_ready": self.live_ready,
            "crashed": self.crashed,
            "crash_reason": self.crash_reason,
            "cmd_seq": self.cmd_seq,
            "ack_seq": self.ack_seq,
            "page": self.page,
            "page_name": page_name,
            "sel_box": self.sel_box,
            "sel_cell_name": CELL_NAMES[self.sel_box % 6],
            "menu_cat": self.menu_cat,
            "menu_cat_name": CAT_NAMES[self.menu_cat % 11],
            "menu_item": self.menu_item,
            "menu_depth": self.menu_depth,
            "cell_vals": self.cell_vals,
            "ibis_idx": self.ibis_idx,
            "xlr_idx": self.xlr_idx,
            "p4_lock_attempts": self.p4_lock_attempts,
            "p4_nd_reject_count": self.p4_nd_reject_count,
            "p12_bk4_airplane_mode_locked": True,
            "audio_ch_db": list(self.audio_ch_db),
            "xlr_phantom_48v": bool(self.xlr_handle_attached and self.xlr_phantom_48v and self.xlr_idx != 2),
            "xlr_handle_attached": bool(self.xlr_handle_attached),
            "rtmd_0xe304_ibis_lock": self.rtmd_0xe304_ibis_lock,
            "user_lut_slots": {k: dict(v) for k, v in self.user_lut_slots.items()},
            "last_toast": self.last_toast,
            "cinema_params": self.get_cinema_params(),
            "stage_b_telemetry": self.get_stage_b_telemetry(),
            "table_off": f"0x{self.table_off:08x}",
            "table_rows": self.table_rows,
            "table_idx128": self.table_idx128,
            "lang": self.lang_code,
            "lang_id": self.lang_id,
            "lang_label": cur_pack["label"],
            "available_langs": [k for k, v in lang_packs.items() if v["available"]],
            "lang_packs": lang_packs,
            "p10_telemetry": dict(self.last_p10_telemetry),
            "gpe0_nonzero_px": self.last_nz,
            "text_ok": self.last_text_ok,
            "fill_n": self.last_fill_n,
            "icon_n": self.last_icon_n,
            "png_source": self.last_png_source,
            "socket_disconnect_count": self.socket_disconnect_count,
            "last_multilang_diff": self.last_multilang_diff,
            "assist_tools": self.get_assist_tools(),
            "cine_exposure": self.get_cine_exposure(),
            "color_and_media": self.get_color_and_media(),
            "touch_focus_ciz": self.get_touch_focus_ciz(),
            "shotmark_and_iris": self.get_shotmark_and_iris(),
            "gyroflow_anamorphic": self.get_gyroflow_anamorphic(),
            "interval_cache_lut_ftp": self.get_interval_cache_lut_ftp(),
            "mc_fleet_sdi_c2pa": self.get_mc_fleet_sdi_c2pa(),
            "hdr_hlg_raw_breathing": self.get_hdr_hlg_raw_breathing(),
            "uvc_srt_crsdk_ptp": self.get_uvc_srt_crsdk_ptp(),
            "serial_tail": serial_tail,
        }


HTML_UI = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<title>Sony FX6 真实虚拟机 GPE0 菜单控制台 (0x41e001000)</title>
<style>
  :root {
    --bg: #0b0d11;
    --panel: #141820;
    --border: #283040;
    --accent: #f59e0b;
    --cyan: #22d3ee;
    --green: #10b981;
    --text: #e5e7eb;
    --muted: #9ca3af;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", sans-serif;
    padding: 16px 22px;
  }
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 1px solid var(--border);
    padding-bottom: 12px;
    margin-bottom: 16px;
  }
  .title-block h1 {
    margin: 0;
    font-size: 19px;
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .badge {
    background: #064e3b;
    color: #a7f3d0;
    padding: 3px 10px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 700;
  }
  .badge.booting {
    background: #78350f;
    color: #fde68a;
  }
  .main-grid {
    display: grid;
    grid-template-columns: 1fr 390px;
    gap: 18px;
    align-items: start;
  }
  .card {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 14px;
  }
  .screen-wrap {
    position: relative;
    background: #000;
    border: 2px solid #2e3646;
    border-radius: 8px;
    overflow: hidden;
    aspect-ratio: 1024 / 540;
    width: 100%;
    cursor: pointer;
  }
  .screen-wrap img {
    width: 100%;
    height: 100%;
    display: block;
    image-rendering: auto;
    user-select: none;
  }
  .boot-overlay {
    position: absolute;
    left: 12px;
    bottom: 12px;
    background: rgba(11, 13, 17, 0.88);
    border: 1px solid var(--accent);
    color: #fde68a;
    padding: 8px 12px;
    border-radius: 6px;
    font-size: 12px;
    font-family: "SF Mono", Menlo, monospace;
    display: none;
    pointer-events: none;
  }
  .render-toast {
    position: absolute;
    right: 12px;
    top: 12px;
    background: rgba(6, 78, 59, 0.92);
    border: 1px solid var(--cyan);
    color: #fff;
    padding: 6px 12px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 600;
    display: none;
    pointer-events: none;
  }
  .meta-bar {
    display: flex;
    flex-wrap: wrap;
    gap: 14px;
    margin-top: 10px;
    font-size: 12px;
    color: var(--muted);
    font-family: "SF Mono", Menlo, monospace;
  }
  .meta-bar b { color: var(--cyan); }
  h3 {
    margin: 0 0 10px 0;
    font-size: 13px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .page-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 6px;
    margin-bottom: 14px;
  }
  .cat-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 6px;
    margin-bottom: 14px;
  }
  button {
    background: #1f2633;
    color: var(--text);
    border: 1px solid #374151;
    border-radius: 7px;
    padding: 8px 10px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.12s;
  }
  button:hover {
    background: #2b3548;
    border-color: var(--cyan);
  }
  button.active {
    background: #164e63;
    border-color: var(--cyan);
    color: #fff;
  }
  .dpad-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    margin-bottom: 12px;
  }
  .dpad-grid button {
    padding: 12px 8px;
    font-size: 13px;
  }
  .btn-set {
    background: #92400e;
    border-color: var(--accent);
    color: #fff;
  }
  .telemetry-strip {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 14px;
    padding: 9px 12px;
    background: #0d131d;
    border: 1px solid #233044;
    border-radius: 9px;
    font-family: "SF Mono", Menlo, monospace;
    font-size: 11px;
  }
  .tel-pill {
    display: flex;
    flex-direction: column;
    gap: 2px;
    padding: 5px 9px;
    background: #131c2b;
    border: 1px solid #2b3a52;
    border-radius: 6px;
    flex: 1 1 160px;
  }
  .tel-pill.locked {
    border-color: #f59e0b;
    background: #1f1709;
  }
  .tel-pill b {
    color: var(--cyan);
    font-size: 11px;
  }
  .tel-pill.locked b {
    color: #fbbf24;
  }
  .tel-pill span {
    color: var(--muted);
    font-size: 10.5px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .param-toast {
    display: none;
    margin-bottom: 10px;
    padding: 8px 11px;
    border-radius: 7px;
    font-size: 12px;
    font-weight: 600;
    border: 1px solid var(--cyan);
    background: #0b2936;
    color: #cffafe;
  }
  .param-toast.warn {
    border-color: #f59e0b;
    background: #451a03;
    color: #fde68a;
  }
  .cinema-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
    margin-bottom: 10px;
  }
  .cparam-box {
    background: #0f1520;
    border: 1px solid #283548;
    border-radius: 7px;
    padding: 8px 10px;
  }
  .cparam-box.locked {
    border-color: #b45309;
    background: #1a1207;
  }
  .cparam-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 11px;
    color: var(--muted);
    margin-bottom: 5px;
  }
  .cparam-row {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .cparam-val {
    flex: 1;
    font-family: "SF Mono", Menlo, monospace;
    font-size: 12px;
    font-weight: 700;
    color: #f8fafc;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .pill-row {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }
  .pill-row button {
    padding: 5px 8px;
    font-size: 11px;
    background: #172030;
  }
  .search-jump-bar {
    background: #0f1520;
    border: 1px solid #283548;
    border-radius: 9px;
    padding: 10px 12px;
    margin-bottom: 14px;
  }
  .search-results-list {
    max-height: 170px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 5px;
    margin-top: 8px;
  }
  .search-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    padding: 6px 9px;
    background: #131c2b;
    border: 1px solid #263348;
    border-radius: 6px;
    font-size: 11.5px;
  }
  .search-item:hover {
    border-color: var(--cyan);
  }
  .multilang-diff-box {
    margin-bottom: 12px;
    padding: 8px 11px;
    border-radius: 7px;
    border: 1px solid #312e81;
    background: #111329;
    font-family: "SF Mono", Menlo, monospace;
    font-size: 11px;
    color: #c7d2fe;
    display: none;
  }
  .serial-box {
    background: #07090c;
    border: 1px solid #1f2937;
    border-radius: 6px;
    padding: 9px;
    font-family: "SF Mono", Menlo, monospace;
    font-size: 11px;
    color: #10b981;
    height: 175px;
    overflow-y: auto;
    white-space: pre-wrap;
  }
</style>
</head>
<body>
<header>
  <div class="title-block">
    <h1>
      <span>Sony FX6 真实虚拟机 GPE0 菜单系统</span>
      <span id="stage-badge" class="badge booting">BOOTING VM...</span>
    </h1>
    <div style="font-size:12px;color:var(--muted);margin-top:4px;">
      100% 虚拟机内部 ARM64 <code>appFw.so + libuxengine.so + TextRM</code> 渲染至物理显存 <code>0x41e001000 (gpe0)</code> · 支持直接点击屏幕或右侧按键
    </div>
  </div>
  <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
    <button id="lang-toggle-btn" onclick="toggleLang()" style="background:#0f2b46;border-color:#22d3ee;color:#cffafe;font-weight:600;">🌐 中文 / EN</button>
    <button id="lbtn-en" onclick="setLang('en')">EN</button>
    <button id="lbtn-zh" onclick="setLang('zh')">中文</button>
    <button id="lbtn-ja" onclick="setLang('ja')">日本語</button>
    <button id="btn-verify-multilang" onclick="verifyMultilangDiff()" style="background:#1e1b4b;border-color:#818cf8;color:#e0e7ff;">驗 / Verify EN-ZH-JA GPE0</button>
    <button onclick="refreshGpe0()">刷新 GPE0 显存帧</button>
    <button onclick="restartVm()" style="background:#7f1d1d;border-color:#ef4444;">重启 QEMU 虚拟机</button>
  </div>
</header>

<div class="telemetry-strip" id="stage-b-telemetry-strip">
  <div class="tel-pill" id="tel-p1"><b>P1 (/lut->p30)</b><span id="tel-p1-d">/dev/nflasha30 -> S-Cinetone</span></div>
  <div class="tel-pill locked" id="tel-p4"><b>P4 (ND=Clear)</b><span id="tel-p4-d">Clear [FX3 P4 Locked]</span></div>
  <div class="tel-pill" id="tel-p10"><b>P10 (FX3 Keys)</b><span id="tel-p10-d">FX3 Deck Ready</span></div>
  <div class="tel-pill" id="tel-p11"><b>P11 (Base ISO 800/12800 + 33³ LUT + XLR-H1 + IBIS Lock)</b><span id="tel-p11-d">Base 800 | 0x0165/0x0166 | 0x5d90 | IBIS Center Lock</span></div>
  <div class="tel-pill" id="tel-p12"><b>P12 (WF-12 Safe)</b><span id="tel-p12-d">Direct O_RDONLY / LRU Pool / Bounded Write Safe</span></div>
</div>

<div id="multilang-diff-readout" class="multilang-diff-box"></div>

<div class="search-jump-bar" id="menu-search-jump-bar">
  <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:8px;">
    <span style="font-size:12px;font-weight:700;color:var(--cyan);">🔍 搜索菜单 / Quick Jump (128 Pages)</span>
    <input id="menu-search-input" type="text" oninput="filterMenuCatalog()" placeholder="输入中文或英文关键词搜索 (如: Cine EI, LUT, XLR-H1, ND, CFexpress, Airplane, Page 110)..." style="flex:1;min-width:240px;background:#07090c;color:#f8fafc;border:1px solid #374151;border-radius:6px;padding:6px 10px;font-size:12px;" />
    <select id="menu-cat-filter" onchange="filterMenuCatalog()" style="background:#172030;color:#e5e7eb;border:1px solid #374151;border-radius:6px;padding:6px 8px;font-size:11.5px;">
      <option value="">All 11 Categories + 128 Pages</option>
    </select>
    <span id="menu-catalog-count" style="font-size:11px;color:var(--muted);font-family:'SF Mono',Menlo,monospace;">11 Categories · 128 Pages</span>
  </div>
  <div class="pill-row" id="quick-jump-pills"></div>
  <div class="search-results-list" id="menu-search-results"></div>
</div>

<div class="main-grid">
  <div>
    <div class="card">
      <div class="screen-wrap" id="screen-wrap" onclick="onScreenClick(event)">
        <img id="gpe0-img" src="/api/frame.png" alt="FX6 Real GPE0 Framebuffer" />
        <div id="p81-canvas-reticle" style="display:none;position:absolute;pointer-events:none;border:2px solid #22c55e;box-shadow:0 0 0 1px rgba(0,0,0,0.65);border-radius:3px;transform:translate(-50%,-50%);width:48px;height:36px;"></div>
        <div id="render-toast" class="render-toast">正在虚拟机内渲染 GPE0 帧...</div>
        <div id="boot-overlay" class="boot-overlay">
          正在等待 FX3 QEMU 虚拟机加载 FX6 内核与 appFw.so (约 42 秒)...
        </div>
      </div>
      <div class="meta-bar">
        <span>页面: <b id="st-page">-</b></span>
        <span>语言包: <b id="st-lang">-</b></span>
        <span>Stage-B P10: <b id="st-p10">-</b></span>
        <span>GPE0 非零像素: <b id="st-nz">-</b></span>
        <span>TextRM 文本贴图: <b id="st-text">-</b></span>
        <span>Fill/Icon: <b id="st-fill">-</b></span>
        <span>Mailbox 序号: <b id="st-seq">-</b></span>
        <span>来源: <b id="st-src">-</b></span>
      </div>
    </div>

    <div class="card" style="margin-top:14px;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;gap:8px;flex-wrap:wrap;">
        <h3 style="margin:0;">Phase 56 · Cinema Line 监看辅助 &amp; 📊 Waveform / IRE Scope (/api/assist_tools · /api/scope_stats)</h3>
        <div style="display:flex;gap:6px;align-items:center;">
          <button id="btn-desqueeze-preview" onclick="toggleDesqueezePreview()" style="padding:4px 9px;font-size:11px;background:#0f2b46;border-color:#22d3ee;">Anamorphic CSS Preview: ON</button>
          <button onclick="refreshScopeStats(true)" style="padding:4px 9px;font-size:11px;">刷新 Scope</button>
        </div>
      </div>
      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:10px;">
        <div class="cparam-box">
          <div class="cparam-head"><span>Aspect Marker</span><span>In-Guest GPE0</span></div>
          <select id="assist-aspect-select" onchange="setAssistTools({aspect_marker: this.value})" style="width:100%;background:#172030;color:#e5e7eb;border:1px solid #374151;border-radius:6px;padding:5px;font-size:11.5px;">
            <option value="Off">Off</option>
            <option value="2.39:1">2.39:1 (Scope)</option>
            <option value="1.85:1">1.85:1 (Flat)</option>
            <option value="17:9">17:9 (DCI 4K)</option>
            <option value="9:16">9:16 (Vertical)</option>
            <option value="CenterCross">CenterCross</option>
          </select>
        </div>
        <div class="cparam-box">
          <div class="cparam-head"><span>Zebra Overlay</span><span>IRE Threshold</span></div>
          <select id="assist-zebra-select" onchange="setAssistTools({zebra_mode: this.value})" style="width:100%;background:#172030;color:#e5e7eb;border:1px solid #374151;border-radius:6px;padding:5px;font-size:11.5px;">
            <option value="Off">Off</option>
            <option value="70%">70% (Skin)</option>
            <option value="94%_SLog3">94%_SLog3 (Clip)</option>
            <option value="100%">100% (Peak)</option>
          </select>
        </div>
        <div class="cparam-box">
          <div class="cparam-head"><span>Focus Peaking</span><span>Edge Gradient</span></div>
          <select id="assist-peaking-select" onchange="setAssistTools({peaking_mode: this.value})" style="width:100%;background:#172030;color:#e5e7eb;border:1px solid #374151;border-radius:6px;padding:5px;font-size:11.5px;">
            <option value="Off">Off</option>
            <option value="Red">Red</option>
            <option value="Yellow">Yellow</option>
            <option value="White">White</option>
          </select>
        </div>
        <div class="cparam-box">
          <div class="cparam-head"><span>Anamorphic Desqueeze</span><span>GPE0 + CSS</span></div>
          <select id="assist-desqueeze-select" onchange="setAssistTools({desqueeze: this.value})" style="width:100%;background:#172030;color:#e5e7eb;border:1px solid #374151;border-radius:6px;padding:5px;font-size:11.5px;">
            <option value="1.0x">1.0x (Spherical)</option>
            <option value="1.33x">1.33x (Anamorphic)</option>
            <option value="2.0x">2.0x (Anamorphic)</option>
          </select>
        </div>
      </div>
      <div class="pill-row" style="margin-bottom:10px;">
        <button onclick="setAssistTools({aspect_marker:'2.39:1',zebra_mode:'70%',peaking_mode:'Red',desqueeze:'2.0x'})" style="border-color:#22d3ee;">2.39:1 + Zebra 70% + Peak Red + 2.0x</button>
        <button onclick="setAssistTools({aspect_marker:'9:16',zebra_mode:'94%_SLog3',peaking_mode:'Yellow',desqueeze:'1.0x'})">9:16 + S-Log3 94% + Peak Yellow</button>
        <button onclick="setAssistTools({aspect_marker:'CenterCross',zebra_mode:'100%',peaking_mode:'White',desqueeze:'1.33x'})">CenterCross + 100% + 1.33x</button>
        <button onclick="setAssistTools({reset:true})">Reset Assist Off</button>
      </div>
      <div class="cparam-box" id="waveform-scope-panel">
        <div class="cparam-head">
          <span style="color:var(--cyan);font-weight:700;">📊 Waveform / IRE Scope (0..109% IRE · 32-Col Luma + 16-Bin RGB)</span>
          <span id="scope-stats-readout" style="font-family:'SF Mono',Menlo,monospace;color:#a7f3d0;">Waiting for /api/scope_stats...</span>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
          <canvas id="scope-waveform-canvas" width="384" height="120" style="width:100%;height:120px;background:#07090c;border:1px solid #1f2937;border-radius:6px;"></canvas>
          <canvas id="scope-hist-canvas" width="384" height="120" style="width:100%;height:120px;background:#07090c;border:1px solid #1f2937;border-radius:6px;"></canvas>
        </div>
      </div>
    </div>

    <div class="card" id="phase64-cine-exposure-card" style="margin-top:14px;border-color:#334155;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;gap:8px;flex-wrap:wrap;">
        <h3 style="margin:0;">Phase 64 · Cinema Line Cine EI / Shutter-ECS / S&amp;Q (1–240fps) / REC Tally &amp; Wired I/O (/api/cine_exposure)</h3>
        <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;">
          <span id="p64-bilingual-hint" style="font-size:10.5px;color:#94a3b8;">EN · 简体中文 · 繁體中文 · 日本語</span>
          <span id="p64-p4-badge" style="font-size:10.5px;padding:2px 7px;border-radius:999px;background:#451a03;color:#fde68a;border:1px solid #f59e0b;">P4 ND=Clear (HW Absent)</span>
          <span id="p64-p12-badge" style="font-size:10.5px;padding:2px 7px;border-radius:999px;background:#064e3b;color:#a7f3d0;border:1px solid #10b981;">P12 Wi-Fi/BT OFF</span>
        </div>
      </div>
      <div id="p64-error-banner" style="display:none;margin-bottom:8px;padding:6px 10px;border-radius:6px;background:#450a0a;border:1px solid #ef4444;color:#fecaca;font-size:11.5px;"></div>
      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:8px;">
        <div class="cparam-box">
          <div class="cparam-head"><span>REC / 录制 · 錄製 · 記録 &amp; Tally</span><span id="p64-tc-readout" style="color:#fca5a5;font-family:'SF Mono',Menlo,monospace;">00:00:00:00</span></div>
          <div style="display:flex;gap:6px;align-items:center;margin-bottom:6px;">
            <button id="p64-rec-btn" onclick="toggleCineRec()" style="flex:1;font-weight:700;background:#064e3b;border-color:#10b981;color:#ecfdf5;">● STBY -> REC</button>
            <span id="p64-tally-front" title="Front Tally" style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#374151;border:1px solid #6b7280;"></span>
            <span id="p64-tally-rear" title="Rear Tally" style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#374151;border:1px solid #6b7280;"></span>
          </div>
          <select id="p64-tally-select" onchange="setCineExposure({tally_lamp_mode: this.value})" style="width:100%;background:#172030;color:#e5e7eb;border:1px solid #374151;border-radius:6px;padding:4px;font-size:11px;">
            <option value="on">Tally: On (Front + Rear)</option>
            <option value="front_only">Tally: Front Only</option>
            <option value="rear_only">Tally: Rear Only</option>
            <option value="off">Tally: Off (Stealth 隱蔽/ステルス)</option>
          </select>
        </div>

        <div class="cparam-box">
          <div class="cparam-head"><span>Cine EI · 双原生ISO / 基準EI</span><span id="p64-lat-readout" style="color:#38bdf8;font-family:'SF Mono',Menlo,monospace;">+6 / -8</span></div>
          <div style="display:flex;gap:4px;margin-bottom:6px;">
            <select id="p64-ei-base-select" onchange="setCineExposure({cine_ei_base: this.value})" style="width:48%;background:#172030;color:#e5e7eb;border:1px solid #374151;border-radius:6px;padding:4px;font-size:11px;">
              <option value="800">Base 800</option>
              <option value="12800">Base 12800</option>
            </select>
            <select id="p64-ei-index-select" onchange="setCineExposure({ei_index: Number(this.value)})" style="width:52%;background:#172030;color:#e5e7eb;border:1px solid #374151;border-radius:6px;padding:4px;font-size:11px;">
              <option value="800">800 EI</option>
            </select>
          </div>
          <div style="height:8px;background:#1f2937;border-radius:4px;overflow:hidden;display:flex;" title="14-Stop Dynamic Latitude">
            <div id="p64-lat-over-bar" style="width:43%;background:#f59e0b;"></div>
            <div id="p64-lat-under-bar" style="width:57%;background:#0284c7;"></div>
          </div>
        </div>

        <div class="cparam-box">
          <div class="cparam-head"><span>Shutter · 快门角度 / ECS消閃</span><span id="p64-shutter-readout" style="color:#fde68a;font-family:'SF Mono',Menlo,monospace;">180.0°</span></div>
          <select id="p64-shutter-mode-select" onchange="setCineExposure({shutter_mode: this.value})" style="width:100%;background:#172030;color:#e5e7eb;border:1px solid #374151;border-radius:6px;padding:4px;font-size:11px;margin-bottom:6px;">
            <option value="angle">Angle (5.6°–360.0°)</option>
            <option value="speed">Speed (1/24–1/8000)</option>
            <option value="ecs">ECS Anti-Flicker (23.98–7900Hz)</option>
          </select>
          <div style="display:flex;gap:4px;">
            <input id="p64-shutter-val-input" type="number" step="0.1" value="180.0" style="flex:1;background:#07090c;color:#f8fafc;border:1px solid #374151;border-radius:6px;padding:4px;font-size:11px;" />
            <button onclick="applyPhase64ShutterVal()" style="padding:4px 8px;font-size:11px;">Apply</button>
          </div>
        </div>

        <div class="cparam-box">
          <div class="cparam-head"><span>S&amp;Q (1–240fps) &amp; Wired I/O</span><span id="p64-sq-mute-badge" style="color:#94a3b8;font-size:10px;">Audio Active</span></div>
          <div style="display:flex;gap:4px;margin-bottom:6px;align-items:center;">
            <button id="p64-sq-btn" onclick="toggleCineSq()" style="padding:4px 7px;font-size:11px;">S&amp;Q: OFF</button>
            <select id="p64-base-fps-select" onchange="setCineExposure({base_fps: Number(this.value)})" style="width:68px;background:#172030;color:#e5e7eb;border:1px solid #374151;border-radius:6px;padding:4px;font-size:10.5px;">
              <option value="23.98">23.98</option>
              <option value="24.0">24.00</option>
              <option value="25.0">25.00</option>
              <option value="29.97">29.97</option>
              <option value="50.0">50.00</option>
              <option value="59.94">59.94</option>
            </select>
            <input id="p64-sq-fps-input" type="number" min="1" max="240" value="24" style="width:52px;background:#07090c;color:#f8fafc;border:1px solid #374151;border-radius:6px;padding:4px;font-size:11px;" onchange="setCineExposure({sq_fps: Number(this.value)})" />
          </div>
          <select id="p64-wired-io-select" onchange="setCineExposure({wired_io_mode: this.value})" style="width:100%;background:#172030;color:#e5e7eb;border:1px solid #374151;border-radius:6px;padding:4px;font-size:11px;">
            <option value="off">Wired I/O: Off (P12 Safe)</option>
            <option value="usblan_ptpip">USB-LAN CDC-NCM + PTP-IP 15740</option>
            <option value="hdmi_raw16">HDMI 16-bit Linear RAW 4264x2408</option>
          </select>
        </div>
      </div>
      <div class="pill-row">
        <button onclick="setCineExposure({cine_ei_base:'800',ei_index:400})">400 EI (+5/-9)</button>
        <button onclick="setCineExposure({cine_ei_base:'800',ei_index:800})">800 EI (+6/-8)</button>
        <button onclick="setCineExposure({cine_ei_base:'800',ei_index:1600})">1600 EI (+7/-7)</button>
        <button onclick="setCineExposure({cine_ei_base:'12800',ei_index:12800})">12800 Base</button>
        <button onclick="setCineExposure({shutter_mode:'angle',shutter_angle_deg:172.8})">172.8°</button>
        <button onclick="setCineExposure({shutter_mode:'ecs',ecs_freq_hz:100.2})">ECS 100.2Hz</button>
        <button onclick="setCineExposure({sq_enabled:true,base_fps:23.98,sq_fps:120})" style="border-color:#f59e0b;">S&amp;Q 120fps (5.00x Slow)</button>
        <button onclick="setCineExposure({sq_enabled:true,base_fps:24.0,sq_fps:4})">S&amp;Q 4fps (0.17x Quick)</button>
        <button onclick="setCineExposure({rec_state:'REC',sq_enabled:true,base_fps:23.98,sq_fps:120,shutter_mode:'ecs',ecs_freq_hz:100.2,wired_io_mode:'hdmi_raw16'})" style="border-color:#ef4444;color:#fecaca;">REC + S&amp;Q120 + ECS100.2 + RAW16</button>
        <button onclick="setCineExposure({reset:true})">Reset CineExposure</button>
      </div>
      <div id="p64-cmd-readout" style="margin-top:6px;font-size:10.5px;color:#67e8f9;font-family:'SF Mono',Menlo,monospace;">CINE_EXP ...</div>
    </div>

    <div class="card" id="phase73-color-media-card" style="margin-top:14px;border-color:#0e7490;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;gap:8px;flex-wrap:wrap;">
        <h3 style="margin:0;">Phase 73 · 色彩白平衡 / 双卡槽场记命名 &amp; 达芬奇 M01.XML 导出 (Color/WB, Dual-Slot CamID &amp; Resolve XML)</h3>
        <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;">
          <span style="font-size:10.5px;padding:2px 7px;border-radius:999px;background:#0f2b46;color:#67e8f9;border:1px solid #0891b2;">FX3 B/A/PRST Soft-Mapped</span>
          <span id="p73-sq-proxy-badge" style="font-size:10.5px;padding:2px 7px;border-radius:999px;background:#064e3b;color:#a7f3d0;border:1px solid #10b981;">Proxy Active</span>
        </div>
      </div>
      <div id="p73-error-banner" style="display:none;margin-bottom:8px;padding:6px 10px;border-radius:6px;background:#450a0a;border:1px solid #ef4444;color:#fecaca;font-size:11.5px;"></div>
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:8px;">
        <div class="cparam-box">
          <div class="cparam-head"><span>White Balance · 白平衡 (Shockless)</span><span id="p73-wb-readout" style="color:#fde68a;font-family:'SF Mono',Menlo,monospace;">5600K+0</span></div>
          <select id="p73-wb-mode-select" onchange="setColorAndMedia({wb_mode: this.value})" style="width:100%;background:#172030;color:#e5e7eb;border:1px solid #374151;border-radius:6px;padding:4px;font-size:11px;margin-bottom:6px;">
            <option value="preset_5600k">Preset 5600K (Daylight)</option>
            <option value="preset_4300k">Preset 4300K</option>
            <option value="preset_3200k">Preset 3200K (Tungsten)</option>
            <option value="mem_a">Memory A (Custom K + Tint)</option>
            <option value="mem_b">Memory B (Custom K + Tint)</option>
            <option value="atw">ATW (Auto Tracing WB)</option>
          </select>
          <div style="display:flex;gap:4px;align-items:center;margin-bottom:6px;">
            <input id="p73-kelvin-input" type="number" min="2000" max="15000" step="50" value="5600" title="Kelvin [2000..15000]" style="width:74px;background:#07090c;color:#f8fafc;border:1px solid #374151;border-radius:6px;padding:4px;font-size:11px;" />
            <input id="p73-tint-input" type="number" min="-99" max="99" step="1" value="0" title="Tint MG/GR [-99..+99]" style="width:54px;background:#07090c;color:#f8fafc;border:1px solid #374151;border-radius:6px;padding:4px;font-size:11px;" />
            <select id="p73-shockless-select" title="Shockless WB Speed" onchange="setColorAndMedia({shockless_wb: this.value})" style="flex:1;background:#172030;color:#e5e7eb;border:1px solid #374151;border-radius:6px;padding:4px;font-size:11px;">
              <option value="off">SL: Off</option>
              <option value="1">SL: 1 (Fast 0.65s)</option>
              <option value="2">SL: 2 (Med 1.60s)</option>
              <option value="3">SL: 3 (Slow 3.20s)</option>
            </select>
          </div>
          <button onclick="applyPhase73WbKelvinTint()" style="width:100%;padding:4px 8px;font-size:11px;">Apply K / Tint · 应用色温偏移</button>
        </div>

        <div class="cparam-box">
          <div class="cparam-head"><span>Base Look · 色彩科学管线</span><span id="p73-nle-tags" style="color:#a78bfa;font-family:'SF Mono',Menlo,monospace;">s-cinetone / rec709</span></div>
          <select id="p73-base-look-select" onchange="setColorAndMedia({base_look: this.value})" style="width:100%;background:#172030;color:#e5e7eb;border:1px solid #374151;border-radius:6px;padding:4px;font-size:11px;margin-bottom:6px;">
            <option value="S-Cinetone">S-Cinetone (Cinema Portrait)</option>
            <option value="S-Log3 / S-Gamut3.Cine">S-Log3 / S-Gamut3.Cine</option>
            <option value="S-Log3 / S-Gamut3">S-Log3 / S-Gamut3</option>
            <option value="ITU709">ITU709 (s709)</option>
            <option value="709(800%)">709(800%) (R709)</option>
            <option value="HLG Live">HLG Live (BT.2100)</option>
            <option value="User 3D LUT">User 3D LUT (User1..User4 .cube)</option>
          </select>
          <div style="font-size:10.5px;color:#94a3b8;line-height:1.4;margin-bottom:6px;">
            Active LUT: <b id="p73-active-lut-readout" style="color:#67e8f9;">-</b>
          </div>
          <div class="pill-row">
            <button onclick="setColorAndMedia({wb_mode:'preset_3200k',tint_gm:-5,base_look:'S-Log3 / S-Gamut3.Cine'})">3200K S-Log3.Cine</button>
            <button onclick="setColorAndMedia({wb_mode:'atw',shockless_wb:'2',base_look:'S-Cinetone'})">ATW SL:2</button>
          </div>
        </div>

        <div class="cparam-box">
          <div class="cparam-head"><span>CamID/Reel &amp; Dual-Slot · 双卡槽场记</span><span id="p73-slot-readout" style="color:#34d399;font-family:'SF Mono',Menlo,monospace;">simul</span></div>
          <div style="display:grid;grid-template-columns:44px 58px 48px 58px;gap:4px;margin-bottom:6px;">
            <input id="p73-cam-id-input" type="text" maxlength="1" value="A" title="CamID A..Z" style="background:#07090c;color:#f8fafc;border:1px solid #374151;border-radius:6px;padding:4px;font-size:11px;text-align:center;" />
            <input id="p73-reel-input" type="number" min="1" max="999" value="1" title="Reel 1..999" style="background:#07090c;color:#f8fafc;border:1px solid #374151;border-radius:6px;padding:4px;font-size:11px;" />
            <select id="p73-pos-select" title="Camera Position" style="background:#172030;color:#e5e7eb;border:1px solid #374151;border-radius:6px;padding:4px;font-size:11px;">
              <option value="C">C</option>
              <option value="L">L</option>
              <option value="R">R</option>
            </select>
            <input id="p73-clip-seq-input" type="number" min="1" max="999" value="1" title="Clip Seq 1..999" style="background:#07090c;color:#f8fafc;border:1px solid #374151;border-radius:6px;padding:4px;font-size:11px;" />
          </div>
          <div style="display:flex;gap:4px;margin-bottom:6px;">
            <select id="p73-dualslot-select" onchange="setColorAndMedia({dual_slot_mode: this.value})" style="flex:1;background:#172030;color:#e5e7eb;border:1px solid #374151;border-radius:6px;padding:4px;font-size:10.5px;">
              <option value="simul">Simul (A+B 同录)</option>
              <option value="relay">Relay (A->B 接力)</option>
              <option value="sort_main_proxy">Sort Main/Proxy</option>
              <option value="single_slot_a">Single Slot A</option>
            </select>
            <select id="p73-proxy-select" onchange="setColorAndMedia({proxy_mode: this.value})" style="flex:1;background:#172030;color:#e5e7eb;border:1px solid #374151;border-radius:6px;padding:4px;font-size:10.5px;">
              <option value="xavc_hs_1080p_16m">Proxy HS 1080p 16M</option>
              <option value="xavc_hs_1080p_9m">Proxy HS 1080p 9M</option>
              <option value="xavc_s_720p_6m">Proxy S 720p 6M</option>
              <option value="off">Proxy Off</option>
            </select>
          </div>
          <button onclick="applyPhase73MediaNaming()" style="width:100%;padding:4px 8px;font-size:11px;">Apply Clip Naming · 应用场记号</button>
        </div>
      </div>

      <div class="cparam-box" style="margin-bottom:8px;">
        <div class="cparam-head">
          <span>Cinema Line Clip / Proxy Paths &amp; Resolve NonRealTimeMeta (M01.XML)</span>
          <span id="p73-clip-readout" style="color:#67e8f9;font-family:'SF Mono',Menlo,monospace;">A001C001_261114_FX3B.MP4</span>
        </div>
        <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin-bottom:6px;">
          <button onclick="downloadXmlSidecar()" style="background:#0f2b46;border-color:#22d3ee;color:#cffafe;">⬇ Download M01.XML (达芬奇 / Resolve Sidecar)</button>
          <button onclick="refreshXmlSidecarPreview()">Refresh XML Preview · 刷新预览</button>
          <button onclick="setColorAndMedia({cam_id:'B',reel_num:4,cam_pos:'C',clip_seq:12,dual_slot_mode:'relay',wb_mode:'preset_3200k',tint_gm:-5,base_look:'S-Log3 / S-Gamut3.Cine'})" style="border-color:#818cf8;">B004C012 Relay + S-Log3.Cine</button>
          <button onclick="setColorAndMedia({reset:true})">Reset Color/Media</button>
          <span id="p73-proxy-path-readout" style="font-size:10.5px;color:#94a3b8;font-family:'SF Mono',Menlo,monospace;">SUB: A001C001_261114_FX3BS03.MP4</span>
        </div>
        <pre id="p73-xml-preview" style="margin:0;max-height:130px;overflow:auto;background:#07090c;border:1px solid #1f2937;border-radius:6px;padding:7px;font-family:'SF Mono',Menlo,monospace;font-size:10px;color:#a7f3d0;">Click "Refresh XML Preview" or "Download M01.XML" to inspect Sony NonRealTimeMeta v2.20...</pre>
      </div>
      <div id="p73-cmd-readout" style="font-size:10.5px;color:#67e8f9;font-family:'SF Mono',Menlo,monospace;">WB_MEDIA ...</div>
    </div>

    <div class="card" id="phase81-touchaf-ciz-card" style="margin-top:14px;border-color:#16a34a;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;gap:8px;flex-wrap:wrap;">
        <h3 style="margin:0;">Phase 81 · 触控跟焦 627点 PDAF / S-Log3 伪色曝光 / 超解析变焦 CIZ (Touch-AF, S-Log3 False Color &amp; CIZ)</h3>
        <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;">
          <button id="p81-click-toggle-btn" onclick="toggleClickCanvasToFocus()" style="padding:4px 9px;font-size:11px;background:#0f2b46;border-color:#22d3ee;color:#cffafe;">🎯 点击画面触控对焦: OFF (Click-Canvas-to-Focus)</button>
          <span id="p81-pdaf-badge" style="font-size:10.5px;padding:2px 7px;border-radius:999px;background:#052e16;color:#86efac;border:1px solid #22c55e;">PDAF 33x19 #313 (16,9)</span>
          <span id="p81-clean-hdmi-badge" style="font-size:10.5px;padding:2px 7px;border-radius:999px;background:#064e3b;color:#a7f3d0;border:1px solid #10b981;">HDMI Clean: 1.0x</span>
        </div>
      </div>
      <div id="p81-error-banner" style="display:none;margin-bottom:8px;padding:6px 10px;border-radius:6px;background:#450a0a;border:1px solid #ef4444;color:#fecaca;font-size:11.5px;"></div>
      <div id="p81-zebra100-warn" style="display:none;margin-bottom:8px;padding:6px 10px;border-radius:6px;background:#451a03;border:1px solid #f59e0b;color:#fde68a;font-size:11px;"></div>
      <div id="p81-ciz-excl-warn" style="display:none;margin-bottom:8px;padding:6px 10px;border-radius:6px;background:#431407;border:1px solid #f97316;color:#fed7aa;font-size:11px;"></div>
      <div id="p81-letterbox-warn" style="display:none;margin-bottom:8px;padding:6px 10px;border-radius:6px;background:#3f2d06;border:1px solid #eab308;color:#fef08a;font-size:11px;"></div>
      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:8px;">
        <div class="cparam-box">
          <div class="cparam-head"><span>Touch AF · 触控跟焦 (627-pt)</span><span id="p81-af-readout" style="color:#4ade80;font-family:'SF Mono',Menlo,monospace;">off</span></div>
          <select id="p81-af-mode-select" onchange="setTouchFocusCiz({touch_af_mode: this.value})" style="width:100%;background:#172030;color:#e5e7eb;border:1px solid #374151;border-radius:6px;padding:4px;font-size:11px;margin-bottom:6px;">
            <option value="off">Off (关闭)</option>
            <option value="touch_focus">Touch Focus (单点触控对焦)</option>
            <option value="touch_tracking">Real-time Tracking AF (实时追踪跟焦)</option>
          </select>
          <div style="display:flex;gap:4px;align-items:center;margin-bottom:6px;">
            <input id="p81-touch-x-input" type="number" min="0" max="959" value="480" title="touch_x [0..959]" style="width:62px;background:#07090c;color:#f8fafc;border:1px solid #374151;border-radius:6px;padding:4px;font-size:11px;" />
            <input id="p81-touch-y-input" type="number" min="0" max="539" value="270" title="touch_y [0..539]" style="width:62px;background:#07090c;color:#f8fafc;border:1px solid #374151;border-radius:6px;padding:4px;font-size:11px;" />
            <button onclick="applyPhase81TouchCoords()" style="flex:1;padding:4px 6px;font-size:11px;">Set XY</button>
          </div>
          <div id="p81-pdaf-readout" style="font-size:10px;color:#94a3b8;font-family:'SF Mono',Menlo,monospace;">col=16, row=9, idx=313</div>
        </div>

        <div class="cparam-box">
          <div class="cparam-head"><span>Focus Magnifier · 对焦放大</span><span id="p81-mag-readout" style="color:#fbbf24;font-family:'SF Mono',Menlo,monospace;">1.0x</span></div>
          <select id="p81-mag-select" onchange="setTouchFocusCiz({focus_mag: this.value})" style="width:100%;background:#172030;color:#e5e7eb;border:1px solid #374151;border-radius:6px;padding:4px;font-size:11px;margin-bottom:6px;">
            <option value="1.0x">1.0x (Full Frame)</option>
            <option value="2.0x">2.0x (Preview Zoom)</option>
            <option value="4.0x">4.0x (Critical Focus)</option>
          </select>
          <div id="p81-mag-roi-readout" style="font-size:10px;color:#94a3b8;line-height:1.4;font-family:'SF Mono',Menlo,monospace;">ROI: 960x540 @ (480,270)<br/>HDMI Clean Feed: 1.0x Unmagnified</div>
        </div>

        <div class="cparam-box">
          <div class="cparam-head"><span>S-Log3 False Color / EL-Zone</span><span id="p81-fc-readout" style="color:#f472b6;font-family:'SF Mono',Menlo,monospace;">off</span></div>
          <select id="p81-fc-select" onchange="setTouchFocusCiz({false_color_mode: this.value})" style="width:100%;background:#172030;color:#e5e7eb;border:1px solid #374151;border-radius:6px;padding:4px;font-size:11px;margin-bottom:6px;">
            <option value="off">Off (关闭)</option>
            <option value="slog3_ire">S-Log3 IRE False Color (伪色)</option>
            <option value="el_zone">EL-Zone (EV Stops 色阶)</option>
          </select>
          <div style="display:flex;gap:4px;flex-wrap:wrap;font-size:9.5px;font-family:'SF Mono',Menlo,monospace;">
            <span style="padding:1px 5px;border-radius:4px;background:#7e22ce;color:#fff;">3.5% Clip</span>
            <span style="padding:1px 5px;border-radius:4px;background:#16a34a;color:#fff;">41% Grey</span>
            <span style="padding:1px 5px;border-radius:4px;background:#db2777;color:#fff;">52% Skin</span>
            <span style="padding:1px 5px;border-radius:4px;background:#dc2626;color:#fff;">94% Clip</span>
          </div>
        </div>

        <div class="cparam-box">
          <div class="cparam-head"><span>Clear Image Zoom (CIZ)</span><span id="p81-ciz-eff-readout" style="color:#38bdf8;font-family:'SF Mono',Menlo,monospace;">1.00x (4K)</span></div>
          <div style="display:flex;gap:4px;margin-bottom:6px;">
            <select id="p81-ciz-res-select" onchange="setTouchFocusCiz({ciz_res_mode: this.value})" style="width:48%;background:#172030;color:#e5e7eb;border:1px solid #374151;border-radius:6px;padding:4px;font-size:11px;">
              <option value="4K">4K (Max 1.50x)</option>
              <option value="FHD">FHD (Max 2.00x)</option>
            </select>
            <select id="p81-rocker-speed-select" onchange="setTouchFocusCiz({zoom_rocker_speed: Number(this.value)})" title="Zoom Rocker Speed 1..8" style="width:52%;background:#172030;color:#e5e7eb;border:1px solid #374151;border-radius:6px;padding:4px;font-size:11px;">
              <option value="1">Speed 1</option>
              <option value="2">Speed 2</option>
              <option value="3">Speed 3</option>
              <option value="4">Speed 4</option>
              <option value="5">Speed 5</option>
              <option value="6">Speed 6</option>
              <option value="7">Speed 7</option>
              <option value="8">Speed 8</option>
            </select>
          </div>
          <div style="display:flex;gap:4px;">
            <input id="p81-ciz-scale-input" type="number" min="1.00" max="2.00" step="0.05" value="1.00" style="flex:1;background:#07090c;color:#f8fafc;border:1px solid #374151;border-radius:6px;padding:4px;font-size:11px;" />
            <button onclick="applyPhase81CizScale()" style="padding:4px 8px;font-size:11px;">Apply</button>
          </div>
        </div>
      </div>
      <div class="pill-row">
        <button onclick="setTouchFocusCiz({touch_af_mode:'touch_tracking',touch_x:640,touch_y:260,focus_mag:'1.0x',false_color_mode:'slog3_ire',ciz_res_mode:'4K',ciz_scale:1.40,zoom_rocker_speed:5})" style="border-color:#22c55e;color:#bbf7d0;">Tracking (640,260) + S-Log3 FC + CIZ 1.40x</button>
        <button onclick="setTouchFocusCiz({touch_af_mode:'touch_focus',touch_x:480,touch_y:270,focus_mag:'4.0x',false_color_mode:'el_zone',ciz_res_mode:'FHD',ciz_scale:1.80})" style="border-color:#f59e0b;">EL-Zone + Focus Mag x4.0 + FHD CIZ 1.80x</button>
        <button onclick="setTouchFocusCiz({reset:true})">Reset Touch-AF / FC / CIZ</button>
      </div>
      <div id="p81-cmd-readout" style="margin-top:6px;font-size:10.5px;color:#86efac;font-family:'SF Mono',Menlo,monospace;">TOUCH_CIZ ...</div>
    </div>

    <div class="card" id="phase88-shotmark-iris-card" style="margin-top:14px;border-color:#f59e0b;">
      <h3>场记打点 ShotMark1/2 / 一键自动光圈 41%IRE / FX6->FX3 多机位配置克隆 (ShotMark, Push Auto Iris &amp; Fleet CAMSET)</h3>
      <div id="p88-error-banner" style="display:none;background:#450a0a;border:1px solid #ef4444;color:#fecaca;border-radius:6px;padding:6px 10px;font-size:11.5px;margin-bottom:8px;"></div>
      <div class="cinema-grid">
        <div class="cparam-box" style="border-color:#b45309;">
          <div class="cparam-head"><span>ShotMark1/2 · 场记打点</span><span id="p88-sm-count-readout" style="color:#fbbf24;font-family:'SF Mono',Menlo,monospace;">M1:0 / M2:0</span></div>
          <div style="display:flex;gap:4px;margin-bottom:6px;flex-wrap:wrap;">
            <button onclick="setShotmarkAndIris({action:'add_shotmark1'})" style="border-color:#fbbf24;color:#fde68a;padding:4px 8px;font-size:11px;">★ ShotMark1 (OK)</button>
            <button onclick="setShotmarkAndIris({action:'add_shotmark2'})" style="border-color:#38bdf8;color:#bae6fd;padding:4px 8px;font-size:11px;">★ ShotMark2 (KEEP)</button>
            <button onclick="setShotmarkAndIris({action:'clear_shotmarks'})" style="padding:4px 8px;font-size:11px;">Clear</button>
          </div>
          <div id="p88-sm-latest-readout" style="font-size:10px;color:#cbd5e1;font-family:'SF Mono',Menlo,monospace;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">EssenceMark: none (0/64)</div>
        </div>

        <div class="cparam-box" style="border-color:#15803d;">
          <div class="cparam-head"><span>Push Auto Iris · 1/8-Stop</span><span id="p88-iris-readout" style="color:#4ade80;font-family:'SF Mono',Menlo,monospace;">F2.8 · 41.0%IRE</span></div>
          <div style="display:flex;gap:4px;margin-bottom:6px;">
            <select id="p88-metering-select" onchange="setShotmarkAndIris({metering_mode:this.value})" style="flex:1;background:#172030;color:#e5e7eb;border:1px solid #374151;border-radius:6px;padding:4px;font-size:11px;">
              <option value="multi">Multi (41% Grey)</option>
              <option value="center">Center</option>
              <option value="spot">Spot</option>
              <option value="highlight">Highlight (&lt;94% IRE)</option>
            </select>
            <input id="p88-ev-input" type="number" min="0" max="18" step="0.5" value="12.0" title="Scene EV [0..18]" style="width:54px;background:#07090c;color:#f8fafc;border:1px solid #374151;border-radius:6px;padding:4px;font-size:11px;" />
            <button onclick="applyPhase88PushAutoIris()" style="border-color:#22c55e;color:#bbf7d0;padding:4px 7px;font-size:11px;">Push</button>
          </div>
          <div id="p88-ire-est-readout" style="font-size:10px;color:#94a3b8;font-family:'SF Mono',Menlo,monospace;">Est Grey: 41.0% | HL: 89.2% | ND Faults: 0</div>
        </div>

        <div class="cparam-box">
          <div class="cparam-head"><span>4-Ch 24-bit Pad &amp; SMPTE User-Bits</span><span id="p88-pad-readout" style="color:#22d3ee;font-family:'SF Mono',Menlo,monospace;">0 dB</span></div>
          <div style="display:flex;gap:4px;margin-bottom:6px;">
            <button onclick="setShotmarkAndIris({ch34_safety_pad_db:0})" style="padding:4px 7px;font-size:11px;">CH3/4 0dB</button>
            <button onclick="setShotmarkAndIris({ch34_safety_pad_db:-20})" style="border-color:#10b981;color:#a7f3d0;padding:4px 7px;font-size:11px;">CH3/4 -20dB SAFE</button>
          </div>
          <div style="display:flex;gap:4px;">
            <input id="p88-ub-input" type="text" value="auto_camid_reel" placeholder="auto_camid_reel or AA:BB:CC:DD" style="flex:1;background:#07090c;color:#f8fafc;border:1px solid #374151;border-radius:6px;padding:4px;font-size:11px;font-family:'SF Mono',Menlo,monospace;" />
            <button onclick="applyPhase88UserBits()" style="padding:4px 7px;font-size:11px;">UB</button>
          </div>
        </div>

        <div class="cparam-box" style="border-color:#0284c7;">
          <div class="cparam-head"><span>FX6->FX3 Fleet CAMSET &amp; XML</span><span id="p88-fleet-badge" style="color:#38bdf8;font-family:'SF Mono',Menlo,monospace;">Ready</span></div>
          <div style="display:flex;gap:4px;flex-wrap:wrap;margin-bottom:6px;">
            <button onclick="importFx6FleetCamsetPreset()" style="border-color:#38bdf8;color:#bae6fd;padding:4px 8px;font-size:11px;">FX6->FX3 Sanitize Clone</button>
            <a href="/api/xml_sidecar" target="_blank" style="display:inline-block;padding:4px 8px;font-size:11px;background:#172030;color:#e5e7eb;border:1px solid #374151;border-radius:6px;text-decoration:none;">Download M01.XML</a>
          </div>
          <div id="p88-ub-readout" style="font-size:10px;color:#94a3b8;font-family:'SF Mono',Menlo,monospace;">UB: A0:01:00:01 (auto_camid_reel)</div>
        </div>
      </div>
      <div id="p88-cmd-readout" style="margin-top:6px;font-size:10.5px;color:#fde68a;font-family:'SF Mono',Menlo,monospace;">SMRK_IRIS ...</div>
    </div>

    <div class="card" id="phase95-gyroflow-anamorphic-card" style="margin-top:14px;border-color:#06b6d4;">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:8px;">
        <h3 id="p95-card-title" style="margin:0;">Phase 95 · 变形镜头 IBIS 仲裁 / Gyroflow 2000Hz RTMD / 1kHz -20dBFS 基准音与 -3dB 限幅器</h3>
        <div style="display:flex;gap:4px;align-items:center;flex-wrap:wrap;">
          <button id="p95-lang-en" onclick="setP95Lang('en')" style="padding:3px 7px;font-size:10.5px;">EN</button>
          <button id="p95-lang-zh-CN" onclick="setP95Lang('zh-CN')" style="padding:3px 7px;font-size:10.5px;border-color:#22d3ee;">简体中文</button>
          <button id="p95-lang-zh-TW" onclick="setP95Lang('zh-TW')" style="padding:3px 7px;font-size:10.5px;">繁體中文</button>
          <button id="p95-lang-ja" onclick="setP95Lang('ja')" style="padding:3px 7px;font-size:10.5px;">日本語</button>
        </div>
      </div>
      <div id="p95-error-banner" style="display:none;background:#450a0a;border:1px solid #ef4444;color:#fecaca;border-radius:6px;padding:6px 10px;font-size:11.5px;margin-bottom:8px;"></div>
      <div id="p95-arbitration-banner" style="display:none;background:#083344;border:1px solid #22d3ee;color:#cffafe;border-radius:6px;padding:6px 10px;font-size:11px;margin-bottom:8px;"></div>
      <div id="p95-sq-warn-banner" style="display:none;background:#450a0a;border:1px solid #f87171;color:#fecaca;border-radius:6px;padding:6px 10px;font-size:11px;margin-bottom:8px;"></div>

      <div class="cinema-grid">
        <div class="cparam-box" style="border-color:#0891b2;">
          <div class="cparam-head"><span id="p95-lbl-anamorphic">Anamorphic &amp; IBIS Arbitrator</span><span id="p95-sq-readout" style="color:#22d3ee;font-family:'SF Mono',Menlo,monospace;">1.00x · Standard</span></div>
          <div style="display:flex;gap:4px;margin-bottom:6px;">
            <select id="p95-squeeze-select" onchange="setGyroflowAnamorphic({squeeze_factor: Number(this.value)})" style="width:36%;background:#172030;color:#e5e7eb;border:1px solid #374151;border-radius:6px;padding:4px;font-size:11px;">
              <option value="1.0">1.00x</option>
              <option value="1.3">1.30x</option>
              <option value="1.33">1.33x</option>
              <option value="1.5">1.50x</option>
              <option value="1.8">1.80x</option>
              <option value="2.0">2.00x</option>
            </select>
            <select id="p95-ibis-select" onchange="setGyroflowAnamorphic({ibis_mode: this.value})" style="width:64%;background:#172030;color:#e5e7eb;border:1px solid #374151;border-radius:6px;padding:4px;font-size:11px;">
              <option value="Off">Off</option>
              <option value="Standard">Standard (5-Axis)</option>
              <option value="Active">Active (Auto-Arbitrated &gt;1.0x)</option>
              <option value="Anamorphic_Asymmetric">Anamorphic Asymmetric (1/Sq Yaw)</option>
              <option value="Center_Lock_Gyroflow">Center-Lock 0x0400 (Gyroflow)</option>
            </select>
          </div>
          <div style="display:flex;gap:4px;align-items:center;margin-bottom:5px;">
            <span id="p95-lbl-fallback" style="font-size:10px;color:#94a3b8;">Fallback:</span>
            <select id="p95-fallback-select" onchange="setGyroflowAnamorphic({anamorphic_fallback_mode: this.value})" style="flex:1;background:#172030;color:#e5e7eb;border:1px solid #374151;border-radius:6px;padding:3px;font-size:10.5px;">
              <option value="Anamorphic_Asymmetric">Anamorphic_Asymmetric</option>
              <option value="Center_Lock_Gyroflow">Center_Lock_Gyroflow (0x0400)</option>
            </select>
          </div>
          <div id="p95-yaw-readout" style="font-size:10px;color:#a5f3fc;font-family:'SF Mono',Menlo,monospace;">Yaw Gain: 1.0000 | Pitch: 1.0000 | Center-Lock: OFF</div>
        </div>

        <div class="cparam-box" style="border-color:#0e7490;">
          <div class="cparam-head"><span id="p95-lbl-gyro">Gyroflow 2000Hz RTMD &amp; Skew</span><span id="p95-rtmd-badge" style="color:#10b981;font-family:'SF Mono',Menlo,monospace;">RTMD_READY</span></div>
          <div id="p95-imu-readout" style="font-size:10.5px;color:#e2e8f0;font-family:'SF Mono',Menlo,monospace;margin-bottom:4px;">2000 Hz · 83.4 samples/frame @ 23.98p</div>
          <div id="p95-skew-readout" style="font-size:10px;color:#94a3b8;font-family:'SF Mono',Menlo,monospace;margin-bottom:6px;">IMX510 Skew: 8.7ms | Wobble Safe: false</div>
          <div style="display:flex;gap:4px;align-items:center;">
            <input id="p95-dsq-touchx-input" type="number" min="0" max="1919" value="480" title="Desqueezed Touch X" style="width:74px;background:#07090c;color:#f8fafc;border:1px solid #374151;border-radius:6px;padding:3px 5px;font-size:10.5px;" />
            <button id="p95-btn-sync-af" onclick="applyPhase95DesqueezedTouch()" style="flex:1;padding:3px 6px;font-size:10.5px;border-color:#22d3ee;">Sync Touch-AF X</button>
          </div>
          <div id="p95-touchaf-sync-readout" style="margin-top:4px;font-size:9.5px;color:#67e8f9;font-family:'SF Mono',Menlo,monospace;">Touch-AF: sensor=480 (dsq=480, scale=1.0000)</div>
        </div>

        <div class="cparam-box" style="border-color:#6d28d9;">
          <div class="cparam-head"><span id="p95-lbl-tone">1kHz -20dBFS Tone &amp; SMPTE Bars</span><span id="p95-tone-badge" style="color:#94a3b8;font-family:'SF Mono',Menlo,monospace;">OFF</span></div>
          <div style="display:flex;gap:4px;flex-wrap:wrap;margin-bottom:6px;">
            <button id="p95-btn-tone-toggle" onclick="togglePhase95RefTone()" style="padding:4px 8px;font-size:11px;border-color:#a78bfa;color:#ddd6fe;">1kHz -20dBFS: OFF</button>
            <button id="p95-btn-bars-toggle" onclick="togglePhase95ColorBars()" style="padding:4px 8px;font-size:11px;border-color:#38bdf8;color:#bae6fd;">SMPTE Bars: OFF</button>
          </div>
          <div id="p95-tone-status-readout" style="font-size:10px;color:#cbd5e1;font-family:'SF Mono',Menlo,monospace;">STBY Ready · Auto-inhibited on REC tally</div>
        </div>

        <div class="cparam-box" style="border-color:#15803d;">
          <div class="cparam-head"><span id="p95-lbl-limiter">4-Ch 24-bit -3.0dBFS Peak Limiter</span><span id="p95-lim-badge" style="color:#94a3b8;font-family:'SF Mono',Menlo,monospace;">OFF</span></div>
          <div style="display:flex;gap:4px;flex-wrap:wrap;margin-bottom:6px;">
            <button id="p95-btn-lim-toggle" onclick="togglePhase95Limiter()" style="padding:4px 8px;font-size:11px;border-color:#10b981;color:#a7f3d0;">Limiter -3.0dBFS: OFF</button>
            <button id="p95-btn-reset" onclick="setGyroflowAnamorphic({reset:true})" style="padding:4px 8px;font-size:11px;">Reset P95</button>
          </div>
          <div id="p95-lim-ch-readout" style="font-size:10px;color:#94a3b8;font-family:'SF Mono',Menlo,monospace;">Eff Ch: -12/-12/-18/-18 dB | Clamped: 0/4</div>
        </div>
      </div>

      <div class="pill-row">
        <button id="p95-preset-2x-asym" onclick="setGyroflowAnamorphic({squeeze_factor:2.0,ibis_mode:'Active',anamorphic_fallback_mode:'Anamorphic_Asymmetric'})" style="border-color:#22d3ee;color:#a5f3fc;">2.0x Active -> Anamorphic_Asymmetric (50% Yaw)</button>
        <button id="p95-preset-18x-ctrlock" onclick="setGyroflowAnamorphic({squeeze_factor:1.8,ibis_mode:'Active',anamorphic_fallback_mode:'Center_Lock_Gyroflow'})" style="border-color:#f59e0b;color:#fde68a;">1.8x Active -> 0x0400 Center-Lock (Gyroflow)</button>
        <button id="p95-preset-tone-bars" onclick="setGyroflowAnamorphic({ref_tone_enabled:true,color_bars_enabled:true,limiter_enabled:true})" style="border-color:#a78bfa;color:#ddd6fe;">Calibrate: 1kHz -20dBFS + Bars + Limiter</button>
      </div>
      <div id="p95-cmd-readout" style="margin-top:6px;font-size:10.5px;color:#67e8f9;font-family:'SF Mono',Menlo,monospace;">GYRO_ANA ...</div>
    </div>

    <div class="card" id="phase123-uvc-srt-crsdk-ptp-card" style="margin-top:14px;border-color:#10b981;">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:8px;">
        <h3 id="p123-card-title" style="margin:0;">Phase 123 · USB-C UVC 1.5 / UAC 2.0 洁净推流 · P12 有线 SRT/RTMPS · CRSDK PTP 遥控与刷写防火墙</h3>
        <div style="display:flex;gap:4px;align-items:center;flex-wrap:wrap;">
          <button id="p123-lang-en" onclick="setP123Lang('en')" style="padding:3px 7px;font-size:10.5px;">EN</button>
          <button id="p123-lang-zh-CN" onclick="setP123Lang('zh-CN')" style="padding:3px 7px;font-size:10.5px;border-color:#10b981;">简体中文</button>
          <button id="p123-lang-zh-TW" onclick="setP123Lang('zh-TW')" style="padding:3px 7px;font-size:10.5px;">繁體中文</button>
          <button id="p123-lang-ja" onclick="setP123Lang('ja')" style="padding:3px 7px;font-size:10.5px;">日本語</button>
        </div>
      </div>
      <div id="p123-error-banner" style="display:none;background:#450a0a;border:1px solid #ef4444;color:#fecaca;border-radius:6px;padding:6px 10px;font-size:11.5px;margin-bottom:8px;"></div>
      <div id="p123-warn-banner" style="display:none;background:#78350f;border:1px solid #f59e0b;color:#fde68a;border-radius:6px;padding:6px 10px;font-size:11px;margin-bottom:8px;"></div>

      <div class="cinema-grid">
        <div class="cparam-box" style="border-color:#22d3ee;">
          <div class="cparam-head"><span id="p123-lbl-uvc">USB-C UVC 1.5 / UAC 2.0 Clean Feed</span><span id="p123-uvc-badge" style="color:#a5f3fc;font-family:'SF Mono',Menlo,monospace;">OFF · CLEAN=1</span></div>
          <div style="display:flex;gap:4px;margin-bottom:6px;flex-wrap:wrap;">
            <select id="p123-uvc-select" onchange="setPhase123State({uvc_mode: this.value})" style="flex:1;background:#172030;color:#e5e7eb;border:1px solid #374151;border-radius:6px;padding:4px;font-size:10.5px;">
              <option value="OFF">OFF</option>
              <option value="UVC_4K30P_MJPEG_5G">UVC 4K30p MJPEG (5Gbps)</option>
              <option value="UVC_1080P60P_YUY2_5G">UVC 1080p60 YUY2 (5Gbps)</option>
              <option value="UVC_720P30P_MJPEG_USB2_FALLBACK">UVC 720p30 MJPEG (USB2)</option>
            </select>
            <select id="p123-usb-speed-select" onchange="setPhase123State({usb_link_speed: this.value})" style="width:94px;background:#172030;color:#e5e7eb;border:1px solid #374151;border-radius:6px;padding:4px;font-size:10.5px;">
              <option value="USB3_5G">USB3 5G</option>
              <option value="USB2_480M">USB2 480M</option>
            </select>
            <button id="p123-btn-test-osd-leak" onclick="setPhase123State({uvc_bake_osd: true})" style="padding:4px 7px;font-size:10.5px;border-color:#ef4444;color:#fecaca;">Test OSD Block</button>
          </div>
          <div id="p123-uvc-readout" style="font-size:10px;color:#a5f3fc;font-family:'SF Mono',Menlo,monospace;">UAC 48kHz 16-bit 2ch PCM | CleanFeed=1 OSD=0px</div>
        </div>

        <div class="cparam-box" style="border-color:#10b981;">
          <div class="cparam-head"><span id="p123-lbl-srt">Wired CDC-NCM SRT / RTMPS TLS 1.3 (P12)</span><span id="p123-srt-badge" style="color:#6ee7b7;font-family:'SF Mono',Menlo,monospace;">OFF · P12 WLAN=OFF</span></div>
          <div style="display:flex;gap:4px;margin-bottom:6px;flex-wrap:wrap;">
            <select id="p123-srt-select" onchange="setPhase123State({srt_mode: this.value})" style="flex:1;background:#172030;color:#e5e7eb;border:1px solid #374151;border-radius:6px;padding:4px;font-size:10.5px;">
              <option value="OFF">SRT OFF</option>
              <option value="SRT_CALLER">SRT Caller (ARQ)</option>
              <option value="SRT_LISTENER">SRT Listener (ARQ)</option>
            </select>
            <select id="p123-pbkey-select" onchange="setPhase123State({srt_pbkeylen: this.value})" style="width:84px;background:#172030;color:#e5e7eb;border:1px solid #374151;border-radius:6px;padding:4px;font-size:10.5px;">
              <option value="AES-256">AES-256</option>
              <option value="AES-128">AES-128</option>
              <option value="NONE">NONE</option>
            </select>
            <input id="p123-latency-input" type="number" step="10" min="20" max="1000" value="120" title="SRT ARQ Latency (ms)" style="width:58px;background:#07090c;color:#f8fafc;border:1px solid #374151;border-radius:6px;padding:3px 5px;font-size:10.5px;" />
            <select id="p123-rtmps-select" onchange="setPhase123State({rtmps_mode: this.value})" style="width:98px;background:#172030;color:#e5e7eb;border:1px solid #374151;border-radius:6px;padding:4px;font-size:10.5px;">
              <option value="OFF">RTMPS OFF</option>
              <option value="RTMPS_TLS13">RTMPS TLS1.3</option>
            </select>
            <input id="p123-bitrate-input" type="number" step="1" min="1" max="50" value="12" title="Bitrate (Mbps)" style="width:48px;background:#07090c;color:#f8fafc;border:1px solid #374151;border-radius:6px;padding:3px 5px;font-size:10.5px;" />
            <button id="p123-btn-apply-srt" onclick="applyPhase123SrtParams()" style="padding:3px 7px;font-size:10.5px;border-color:#10b981;">Apply</button>
            <button id="p123-btn-test-wifi" onclick="setPhase123State({use_wifi: true})" style="padding:3px 7px;font-size:10.5px;border-color:#ef4444;color:#fecaca;">Test P12 Wi-Fi</button>
          </div>
          <div id="p123-srt-readout" style="font-size:10px;color:#a7f3d0;font-family:'SF Mono',Menlo,monospace;">CDC-NCM Wired | P12 WLAN=OFF wf12=0 | 12Mbps</div>
        </div>

        <div class="cparam-box" style="border-color:#3b82f6;">
          <div class="cparam-head"><span id="p123-lbl-ptp">CRSDK PTP / PTP-IP (0x054C) Remote</span><span id="p123-ptp-badge" style="color:#bfdbfe;font-family:'SF Mono',Menlo,monospace;">OFF · 0xD210</span></div>
          <div style="display:flex;gap:4px;margin-bottom:6px;flex-wrap:wrap;">
            <select id="p123-ptp-select" onchange="setPhase123State({crsdk_ptp_mode: this.value})" style="flex:1;background:#172030;color:#e5e7eb;border:1px solid #374151;border-radius:6px;padding:4px;font-size:10.5px;">
              <option value="OFF">OFF</option>
              <option value="USB_PTP">USB PTP (0x054C)</option>
              <option value="WIRED_PTPIP">Wired PTP-IP (15740)</option>
            </select>
            <select id="p123-d2xx-select" style="width:128px;background:#172030;color:#e5e7eb;border:1px solid #374151;border-radius:6px;padding:4px;font-size:10.5px;">
              <option value="0xD210">0xD210 Base/EI</option>
              <option value="0xD20D">0xD20D Shutter</option>
              <option value="0xD21C">0xD21C WB/K</option>
              <option value="0xD220">0xD220 Look/LUT</option>
              <option value="0xD224">0xD224 P4 ND-Clear</option>
              <option value="0xD2C1">0xD2C1 Touch AF</option>
              <option value="0xD2C4">0xD2C4 REC Trig</option>
            </select>
            <button id="p123-btn-send-d2xx" onclick="sendPhase123SafeOpcode()" style="padding:3px 7px;font-size:10.5px;border-color:#3b82f6;color:#bfdbfe;">Run 0xD2xx</button>
            <button id="p123-btn-test-nd-clamp" onclick="setPhase123State({ptp_opcode:'0xD224',crsdk_nd_preset:'1/16'})" style="padding:3px 7px;font-size:10.5px;border-color:#f59e0b;color:#fde68a;">Test P4 ND</button>
          </div>
          <div id="p123-ptp-readout" style="font-size:10px;color:#bfdbfe;font-family:'SF Mono',Menlo,monospace;">VID 0x054C | Base800 EI800 | Look=S-Cinetone | P4 ND=Clear</div>
        </div>

        <div class="cparam-box" style="border-color:#ef4444;">
          <div class="cparam-head"><span id="p123-lbl-fw">PTP Flash-Opcode Firewall (0x9280..)</span><span id="p123-fw-badge" style="color:#fca5a5;font-family:'SF Mono',Menlo,monospace;">ARMED · eMMC=0B</span></div>
          <div style="display:flex;gap:4px;margin-bottom:6px;flex-wrap:wrap;">
            <button id="p123-btn-test-flash-9280" onclick="setPhase123State({ptp_opcode:'0x9280'})" style="flex:1;padding:4px 7px;font-size:10.5px;border-color:#ef4444;color:#fecaca;">Block 0x9280 Flash</button>
            <button id="p123-btn-test-flash-9285" onclick="setPhase123State({ptp_opcode:'0x9285',crsdk_action:'firmware_flash'})" style="flex:1;padding:4px 7px;font-size:10.5px;border-color:#ef4444;color:#fecaca;">Block 0x9285 UFU</button>
          </div>
          <div id="p123-fw-readout" style="font-size:10px;color:#fecaca;font-family:'SF Mono',Menlo,monospace;">Firewall=ON | eMMC_Mutation=0B | Blocked=0</div>
        </div>
      </div>

      <div class="pill-row">
        <button id="p123-preset-uvc4k-srt-ptpip" onclick="setPhase123State({uvc_mode:'UVC_4K30P_MJPEG_5G',usb_link_speed:'USB3_5G',srt_mode:'SRT_CALLER',srt_pbkeylen:'AES-256',srt_latency_ms:120,crsdk_ptp_mode:'WIRED_PTPIP'})" style="border-color:#10b981;color:#a7f3d0;">UVC 4K30p + SRT Caller AES-256 + PTP-IP</button>
        <button id="p123-preset-usb2-fallback" onclick="setPhase123State({uvc_mode:'UVC_4K30P_MJPEG_5G',usb_link_speed:'USB2_480M',rtmps_mode:'RTMPS_TLS13',stream_bitrate_mbps:18})" style="border-color:#f59e0b;color:#fde68a;">USB2 480M Stepdown (720p30) + RTMPS TLS1.3</button>
        <button id="p123-preset-ptp-ei12800" onclick="setPhase123State({crsdk_ptp_mode:'USB_PTP',ptp_opcode:'0xD210',crsdk_cine_ei_base:'12800',crsdk_ei_index:12800,crsdk_base_look:'S-Log3 / S-Gamut3.Cine'})" style="border-color:#3b82f6;color:#bfdbfe;">CRSDK 0xD210 EI 12800 + S-Log3</button>
        <button id="p123-btn-reset" onclick="setPhase123State({reset:true})" style="padding:4px 8px;font-size:11px;">Reset P123</button>
      </div>
      <div id="p123-cmd-readout" style="margin-top:6px;font-size:10.5px;color:#6ee7b7;font-family:'SF Mono',Menlo,monospace;">UVCS ...</div>
    </div>

    <div class="card" id="phase116-hlg-raw-breathing-card" style="margin-top:14px;border-color:#f59e0b;">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:8px;">
        <h3 id="p116-card-title" style="margin:0;">Phase 116 · HLG1/HLG2/HLG3 BT.2100 &amp; CTA-861.3 (0x87) / Display Assist 洁净隔离 / ProRes RAW &amp; BRAW / 呼吸效应补偿</h3>
        <div style="display:flex;gap:4px;align-items:center;flex-wrap:wrap;">
          <button id="p116-lang-en" onclick="setP116Lang('en')" style="padding:3px 7px;font-size:10.5px;">EN</button>
          <button id="p116-lang-zh-CN" onclick="setP116Lang('zh-CN')" style="padding:3px 7px;font-size:10.5px;border-color:#f59e0b;">简体中文</button>
          <button id="p116-lang-zh-TW" onclick="setP116Lang('zh-TW')" style="padding:3px 7px;font-size:10.5px;">繁體中文</button>
          <button id="p116-lang-ja" onclick="setP116Lang('ja')" style="padding:3px 7px;font-size:10.5px;">日本語</button>
        </div>
      </div>
      <div id="p116-error-banner" style="display:none;background:#450a0a;border:1px solid #ef4444;color:#fecaca;border-radius:6px;padding:6px 10px;font-size:11.5px;margin-bottom:8px;"></div>
      <div id="p116-warn-banner" style="display:none;background:#78350f;border:1px solid #f59e0b;color:#fde68a;border-radius:6px;padding:6px 10px;font-size:11px;margin-bottom:8px;"></div>

      <div class="cinema-grid">
        <div class="cparam-box" style="border-color:#f59e0b;">
          <div class="cparam-head"><span id="p116-lbl-hlg">HLG BT.2100 &amp; CTA-861.3 (0x87)</span><span id="p116-hlg-badge" style="color:#fde68a;font-family:'SF Mono',Menlo,monospace;">OFF · 100nit · CS=0x69</span></div>
          <div style="display:flex;gap:4px;margin-bottom:6px;flex-wrap:wrap;">
            <select id="p116-hlg-select" onchange="setPhase116State({hlg_profile: this.value})" style="flex:1;background:#172030;color:#e5e7eb;border:1px solid #374151;border-radius:6px;padding:4px;font-size:10.5px;">
              <option value="OFF">OFF (SDR / Log)</option>
              <option value="HLG1">HLG1 (87% ~925nit Low-Noise)</option>
              <option value="HLG2">HLG2 (95% ~1000nit Balanced)</option>
              <option value="HLG3">HLG3 (100% ~1090nit Wide-DR)</option>
            </select>
            <select id="p116-gamut-select" onchange="setPhase116State({color_gamut: this.value})" style="width:90px;background:#172030;color:#e5e7eb;border:1px solid #374151;border-radius:6px;padding:4px;font-size:10.5px;">
              <option value="BT.2020">BT.2020</option>
              <option value="BT.709">BT.709</option>
            </select>
            <select id="p116-knee-select" onchange="setPhase116State({knee_mode: this.value})" style="width:74px;background:#172030;color:#e5e7eb;border:1px solid #374151;border-radius:6px;padding:4px;font-size:10.5px;">
              <option value="Auto">Auto</option>
              <option value="87%">87%</option>
              <option value="95%">95%</option>
              <option value="100%">100%</option>
            </select>
            <input id="p116-detail-input" type="number" step="1" min="-7" max="7" value="0" title="HLG Detail (-7..+7)" style="width:52px;background:#07090c;color:#f8fafc;border:1px solid #374151;border-radius:6px;padding:3px 5px;font-size:10.5px;" />
            <button id="p116-btn-apply-detail" onclick="applyPhase116Detail()" style="padding:3px 7px;font-size:10.5px;border-color:#f59e0b;">Apply</button>
          </div>
          <div id="p116-hlg-readout" style="font-size:10px;color:#fde68a;font-family:'SF Mono',Menlo,monospace;">CTA-861.3 0x87 EOTF=0 CS=0x69 (sum%256=0) | Peak=100nit</div>
        </div>

        <div class="cparam-box" style="border-color:#10b981;">
          <div class="cparam-head"><span id="p116-lbl-assist">Gamma Display Assist (Clean HDMI/SDI)</span><span id="p116-assist-badge" style="color:#6ee7b7;font-family:'SF Mono',Menlo,monospace;">OFF · CLEAN=1</span></div>
          <div style="display:flex;gap:4px;margin-bottom:6px;flex-wrap:wrap;">
            <select id="p116-assist-select" onchange="setPhase116State({display_assist_mode: this.value})" style="flex:1;background:#172030;color:#e5e7eb;border:1px solid #374151;border-radius:6px;padding:4px;font-size:10.5px;">
              <option value="OFF">OFF</option>
              <option value="AUTO">AUTO (Follow HLG / S-Log3)</option>
              <option value="S-Log3->709(800%)">S-Log3-&gt;709(800%)</option>
              <option value="HLG->709(BT.2020)">HLG-&gt;709(BT.2020)</option>
              <option value="HLG->709(709)">HLG-&gt;709(709)</option>
            </select>
            <button id="p116-btn-test-leak" onclick="setPhase116State({apply_assist_to_hdmi: true})" style="padding:4px 7px;font-size:10.5px;border-color:#ef4444;color:#fecaca;">Test Clean Leak Guard</button>
          </div>
          <div id="p116-assist-readout" style="font-size:10px;color:#a7f3d0;font-family:'SF Mono',Menlo,monospace;">EVF/LCD=OFF | Clean HDMI/SDI=1 XAVC=1 Leak=0px Blk=0</div>
        </div>

        <div class="cparam-box" style="border-color:#22d3ee;">
          <div class="cparam-head"><span id="p116-lbl-raw">External HDMI RAW (16-&gt;12-Bit Log)</span><span id="p116-raw-badge" style="color:#a5f3fc;font-family:'SF Mono',Menlo,monospace;">OFF · XAVC 10b</span></div>
          <div style="display:flex;gap:4px;margin-bottom:6px;flex-wrap:wrap;">
            <select id="p116-raw-select" onchange="setPhase116State({ext_raw_mode: this.value})" style="flex:1;background:#172030;color:#e5e7eb;border:1px solid #374151;border-radius:6px;padding:4px;font-size:10.5px;">
              <option value="OFF">OFF (Internal XAVC)</option>
              <option value="Atomos_ProRes_RAW_16_12L">Atomos ProRes RAW (16-&gt;12L)</option>
              <option value="Blackmagic_BRAW_16_12L">Blackmagic BRAW (16-&gt;12L)</option>
            </select>
            <button id="p116-btn-xml-sidecar" onclick="window.open('/api/xml_sidecar','_blank')" style="padding:4px 7px;font-size:10.5px;border-color:#22d3ee;color:#a5f3fc;">Inspect HDR XML</button>
          </div>
          <div id="p116-raw-readout" style="font-size:10px;color:#a5f3fc;font-family:'SF Mono',Menlo,monospace;">Internal XAVC | Base800 5600K 24mm F2.8</div>
        </div>

        <div class="cparam-box" style="border-color:#a78bfa;">
          <div class="cparam-head"><span id="p116-lbl-fbc">Focus Breathing Comp (E-Mount 12-Pin)</span><span id="p116-fbc-badge" style="color:#ddd6fe;font-family:'SF Mono',Menlo,monospace;">OFF · 1.00x</span></div>
          <div style="display:flex;gap:4px;margin-bottom:6px;flex-wrap:wrap;">
            <select id="p116-fbc-select" onchange="setPhase116State({breathing_comp_mode: this.value})" style="flex:1;background:#172030;color:#e5e7eb;border:1px solid #374151;border-radius:6px;padding:4px;font-size:10.5px;">
              <option value="OFF">OFF (1.00x)</option>
              <option value="AUTO">AUTO (E-Mount 1.02x..1.08x)</option>
            </select>
            <button id="p116-btn-test-fbc-pl" onclick="setPhase116State({force_breathing_on_pl: true})" style="padding:4px 7px;font-size:10.5px;border-color:#ef4444;color:#fecaca;">Test PL Bypass</button>
          </div>
          <div id="p116-fbc-readout" style="font-size:10px;color:#ddd6fe;font-family:'SF Mono',Menlo,monospace;">FBC=OFF (1.00x) | E-Mount 12-Pin Ready</div>
        </div>
      </div>

      <div class="pill-row">
        <button id="p116-preset-hlg3-assist" onclick="setPhase116State({hlg_profile:'HLG3',color_gamut:'BT.2020',display_assist_mode:'AUTO',ext_raw_mode:'OFF'})" style="border-color:#f59e0b;color:#fde68a;">HLG3 BT.2020 (1090nit) + Assist AUTO</button>
        <button id="p116-preset-prores-raw" onclick="setPhase116State({ext_raw_mode:'Atomos_ProRes_RAW_16_12L',breathing_comp_mode:'AUTO'})" style="border-color:#22d3ee;color:#a5f3fc;">Atomos ProRes RAW 16-&gt;12L (FBC 1.00x Bypass)</button>
        <button id="p116-preset-braw" onclick="setPhase116State({ext_raw_mode:'Blackmagic_BRAW_16_12L',breathing_comp_mode:'AUTO'})" style="border-color:#3b82f6;color:#bfdbfe;">Blackmagic BRAW 16-&gt;12L (FBC 1.00x Bypass)</button>
        <button id="p116-preset-fbc-emount" onclick="setPhase116State({ext_raw_mode:'OFF',breathing_comp_mode:'AUTO'})" style="border-color:#a78bfa;color:#ddd6fe;">E-Mount 12-Pin Breathing Comp AUTO</button>
        <button id="p116-btn-reset" onclick="setPhase116State({reset:true})" style="padding:4px 8px;font-size:11px;">Reset P116</button>
      </div>
      <div id="p116-cmd-readout" style="margin-top:6px;font-size:10.5px;color:#fbbf24;font-family:'SF Mono',Menlo,monospace;">HLGA ...</div>
    </div>

    <div class="card" id="phase109-mcfleet-sdi-c2pa-card" style="margin-top:14px;border-color:#06b6d4;">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:8px;">
        <h3 id="p109-card-title" style="margin:0;">Phase 109 · M&amp;C 4机位有线同步 / HDMI→12G-SDI RP188 / E-卡口与PL热插拔 / C2PA 零接触溯源</h3>
        <div style="display:flex;gap:4px;align-items:center;flex-wrap:wrap;">
          <button id="p109-lang-en" onclick="setP109Lang('en')" style="padding:3px 7px;font-size:10.5px;">EN</button>
          <button id="p109-lang-zh-CN" onclick="setP109Lang('zh-CN')" style="padding:3px 7px;font-size:10.5px;border-color:#06b6d4;">简体中文</button>
          <button id="p109-lang-zh-TW" onclick="setP109Lang('zh-TW')" style="padding:3px 7px;font-size:10.5px;">繁體中文</button>
          <button id="p109-lang-ja" onclick="setP109Lang('ja')" style="padding:3px 7px;font-size:10.5px;">日本語</button>
        </div>
      </div>
      <div id="p109-error-banner" style="display:none;background:#450a0a;border:1px solid #ef4444;color:#fecaca;border-radius:6px;padding:6px 10px;font-size:11.5px;margin-bottom:8px;"></div>
      <div id="p109-warn-banner" style="display:none;background:#78350f;border:1px solid #f59e0b;color:#fde68a;border-radius:6px;padding:6px 10px;font-size:11px;margin-bottom:8px;"></div>

      <div class="cinema-grid">
        <div class="cparam-box" style="border-color:#06b6d4;">
          <div class="cparam-head"><span id="p109-lbl-fleet">M&amp;C 4-Cam Wired Fleet (PTP-IP)</span><span id="p109-fleet-badge" style="color:#22d3ee;font-family:'SF Mono',Menlo,monospace;">Solo · 1/4 · P12 OFF</span></div>
          <div style="display:flex;gap:4px;margin-bottom:6px;flex-wrap:wrap;">
            <select id="p109-role-select" onchange="setPhase109State({fleet_role: this.value})" style="flex:1;background:#172030;color:#e5e7eb;border:1px solid #374151;border-radius:6px;padding:4px;font-size:10.5px;">
              <option value="Solo">Solo</option>
              <option value="A_Cam_Master">A_Cam_Master</option>
              <option value="B_Cam_Follower">B_Cam_Follower</option>
              <option value="C_Cam_Follower">C_Cam_Follower</option>
              <option value="D_Cam_Follower">D_Cam_Follower</option>
            </select>
            <select id="p109-cams-select" onchange="setPhase109State({fleet_cams_online: Number(this.value)})" style="width:68px;background:#172030;color:#e5e7eb;border:1px solid #374151;border-radius:6px;padding:4px;font-size:10.5px;">
              <option value="1">1 Cam</option>
              <option value="2">2 Cams</option>
              <option value="3">3 Cams</option>
              <option value="4">4 Cams</option>
            </select>
            <button id="p109-btn-gang-rec" onclick="togglePhase109GangRec()" style="padding:4px 8px;font-size:10.5px;border-color:#ef4444;color:#fecaca;">Gang REC: OFF</button>
          </div>
          <div id="p109-fleet-readout" style="font-size:10px;color:#a5f3fc;font-family:'SF Mono',Menlo,monospace;">USB_LAN_CDC_NCM_RTL8153 | PTP Skew=0.0us | wf12=0</div>
        </div>

        <div class="cparam-box" style="border-color:#3b82f6;">
          <div class="cparam-head"><span id="p109-lbl-sdi">HDMI→12G-SDI AVI &amp; RP 188 Bridge</span><span id="p109-sdi-badge" style="color:#93c5fd;font-family:'SF Mono',Menlo,monospace;">RP188=0 · CS=0x00</span></div>
          <div style="display:flex;gap:4px;margin-bottom:6px;flex-wrap:wrap;">
            <select id="p109-sdi-select" onchange="setPhase109State({sdi_bridge_converter: this.value})" style="flex:1;background:#172030;color:#e5e7eb;border:1px solid #374151;border-radius:6px;padding:4px;font-size:10.5px;">
              <option value="BMD_Micro_Converter_12G">BMD_Micro_Converter_12G</option>
              <option value="Teradek_Bolt_HDMI_SDI">Teradek_Bolt_HDMI_SDI</option>
              <option value="Atomos_Connect_12G">Atomos_Connect_12G</option>
              <option value="Off">Off</option>
            </select>
            <button id="p109-btn-hdmi-tc" onclick="togglePhase109HdmiTc()" style="padding:4px 7px;font-size:10.5px;border-color:#3b82f6;color:#bfdbfe;">TC+REC Ctrl: ON</button>
          </div>
          <div id="p109-sdi-readout" style="font-size:10px;color:#bfdbfe;font-family:'SF Mono',Menlo,monospace;">AVI CS=0x00 (sum%256=0) | LEGAL_64_940 | No BNC Faults</div>
        </div>

        <div class="cparam-box" style="border-color:#f59e0b;">
          <div class="cparam-head"><span id="p109-lbl-mount">E-Mount 12-Pin vs PL Hot-Swap Shading</span><span id="p109-mount-badge" style="color:#fde68a;font-family:'SF Mono',Menlo,monospace;">12-Pin · 1.32x</span></div>
          <div style="display:flex;gap:4px;margin-bottom:5px;flex-wrap:wrap;">
            <select id="p109-mount-select" onchange="setPhase109State({mount_type: this.value})" style="flex:1;background:#172030;color:#e5e7eb;border:1px solid #374151;border-radius:6px;padding:4px;font-size:10.5px;">
              <option value="Sony_EMount_12Pin_GM">Sony_EMount_12Pin_GM</option>
              <option value="Manual_PL_Adapter_Unchipped">Manual_PL_Adapter_Unchipped</option>
            </select>
            <input id="p109-lens-kg-input" type="number" step="0.1" min="0.1" max="10.0" value="0.7" title="Lens Weight (kg)" style="width:58px;background:#07090c;color:#f8fafc;border:1px solid #374151;border-radius:6px;padding:3px 5px;font-size:10.5px;" />
            <button id="p109-btn-apply-mount" onclick="applyPhase109MountParams()" style="padding:3px 7px;font-size:10.5px;border-color:#f59e0b;">Apply</button>
            <button id="p109-btn-lws" onclick="togglePhase109Lws()" style="padding:3px 7px;font-size:10.5px;border-color:#eab308;">LWS: OFF</button>
          </div>
          <div id="p109-mount-readout" style="font-size:10px;color:#fde68a;font-family:'SF Mono',Menlo,monospace;">Shading=1.32x | 0.70kg | G31 Flange OK</div>
        </div>

        <div class="cparam-box" style="border-color:#10b981;">
          <div class="cparam-head"><span id="p109-lbl-c2pa">C2PA 2.1 / cnflasha Zero-Touch Shield</span><span id="p109-c2pa-badge" style="color:#6ee7b7;font-family:'SF Mono',Menlo,monospace;">RDONLY · kr=0 cw=0</span></div>
          <div style="display:flex;gap:4px;margin-bottom:5px;flex-wrap:wrap;">
            <button id="p109-btn-c2pa-guard" onclick="setPhase109State({c2pa_operation:'READ_KEY'})" style="padding:4px 8px;font-size:10.5px;border-color:#ef4444;color:#fecaca;">Test Zero-Touch Guard</button>
            <button id="p109-btn-xml-prov" onclick="window.open('/api/xml_sidecar','_blank')" style="padding:4px 8px;font-size:10.5px;border-color:#10b981;color:#a7f3d0;">Inspect XML Provenance</button>
          </div>
          <div id="p109-c2pa-readout" style="font-size:10px;color:#a7f3d0;font-family:'SF Mono',Menlo,monospace;">CNFLASHA_RDONLY_ZERO_TOUCH | CLEAN_ROOM_RESEARCH_UNATTESTED | Blk=0</div>
        </div>
      </div>

      <div class="pill-row">
        <button id="p109-preset-fleet4" onclick="setPhase109State({fleet_role:'A_Cam_Master',fleet_cams_online:4,gang_rec_trigger:true,sdi_bridge_converter:'BMD_Micro_Converter_12G'})" style="border-color:#06b6d4;color:#a5f3fc;">4-Cam Wired Master + Gang REC + RP188</button>
        <button id="p109-preset-pl-cine" onclick="setPhase109State({mount_type:'Manual_PL_Adapter_Unchipped',lens_kg:1.8,rod_support_15mm_lws:false})" style="border-color:#f59e0b;color:#fde68a;">Hot-Swap Manual PL (1.8kg G31 Warn)</button>
        <button id="p109-preset-pl-lws" onclick="setPhase109State({mount_type:'Manual_PL_Adapter_Unchipped',lens_kg:1.8,rod_support_15mm_lws:true})" style="border-color:#10b981;color:#a7f3d0;">Engage 15mm LWS Support (PL 1.00x)</button>
        <button id="p109-btn-reset" onclick="setPhase109State({reset:true})" style="padding:4px 8px;font-size:11px;">Reset P109</button>
      </div>
      <div id="p109-cmd-readout" style="margin-top:6px;font-size:10.5px;color:#22d3ee;font-family:'SF Mono',Menlo,monospace;">MCFL ...</div>
    </div>

    <div class="card" id="phase102-cache-lut-ftp-card" style="margin-top:14px;border-color:#10b981;">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:8px;">
        <h3 id="p102-card-title" style="margin:0;">Phase 102 · 预录制 DDR 缓存 / 电子快门间隔摄影 / .cube 33³ 四面体上传 / USB-LAN FTPS 队列</h3>
        <div style="display:flex;gap:4px;align-items:center;flex-wrap:wrap;">
          <button id="p102-lang-en" onclick="setP102Lang('en')" style="padding:3px 7px;font-size:10.5px;">EN</button>
          <button id="p102-lang-zh-CN" onclick="setP102Lang('zh-CN')" style="padding:3px 7px;font-size:10.5px;border-color:#10b981;">简体中文</button>
          <button id="p102-lang-zh-TW" onclick="setP102Lang('zh-TW')" style="padding:3px 7px;font-size:10.5px;">繁體中文</button>
          <button id="p102-lang-ja" onclick="setP102Lang('ja')" style="padding:3px 7px;font-size:10.5px;">日本語</button>
        </div>
      </div>
      <div id="p102-error-banner" style="display:none;background:#450a0a;border:1px solid #ef4444;color:#fecaca;border-radius:6px;padding:6px 10px;font-size:11.5px;margin-bottom:8px;"></div>
      <div id="p102-susp-banner" style="display:none;background:#78350f;border:1px solid #f59e0b;color:#fde68a;border-radius:6px;padding:6px 10px;font-size:11px;margin-bottom:8px;"></div>

      <div class="cinema-grid">
        <div class="cparam-box" style="border-color:#10b981;">
          <div class="cparam-head"><span id="p102-lbl-cache">Picture Cache (Pre-Rec DDR)</span><span id="p102-cache-badge" style="color:#10b981;font-family:'SF Mono',Menlo,monospace;">0s / 384 MiB</span></div>
          <div style="display:flex;gap:4px;margin-bottom:6px;">
            <select id="p102-cache-sec-select" onchange="setPhase102State({cache_seconds: Number(this.value)})" style="width:40%;background:#172030;color:#e5e7eb;border:1px solid #374151;border-radius:6px;padding:4px;font-size:11px;">
              <option value="0">Off (0s)</option>
              <option value="2">2s</option>
              <option value="4">4s</option>
              <option value="8">8s</option>
              <option value="16">16s (Max)</option>
            </select>
            <select id="p102-codec-select" onchange="setPhase102State({codec_profile: this.value})" style="width:60%;background:#172030;color:#e5e7eb;border:1px solid #374151;border-radius:6px;padding:4px;font-size:11px;">
              <option value="auto">Auto (Active Format)</option>
              <option value="XAVC_I_4K60">XAVC-I 4K60 (600Mbps · 75 MiB/s)</option>
              <option value="XAVC_I_4K24">XAVC-I 4K24 (240Mbps · 30 MiB/s)</option>
              <option value="XAVC_L_4K60">XAVC-L 4K60 (200Mbps · 25 MiB/s)</option>
              <option value="XAVC_L_4K30">XAVC-L 4K30 (100Mbps · 12.5 MiB/s)</option>
              <option value="XAVC_HS_4K60">XAVC-HS 4K60 (150Mbps · 18.75 MiB/s)</option>
            </select>
          </div>
          <div id="p102-ddr-readout" style="font-size:10px;color:#a7f3d0;font-family:'SF Mono',Menlo,monospace;">DDR Ring: 0.0 / 384.0 MiB (2048 MiB DRAM)</div>
        </div>

        <div class="cparam-box" style="border-color:#8b5cf6;">
          <div class="cparam-head"><span id="p102-lbl-interval">Interval Rec (E-Shutter Only)</span><span id="p102-intvl-badge" style="color:#c4b5fd;font-family:'SF Mono',Menlo,monospace;">OFF · MECH=0</span></div>
          <div style="display:flex;gap:4px;align-items:center;margin-bottom:6px;">
            <button id="p102-btn-intvl-toggle" onclick="togglePhase102Interval()" style="padding:4px 8px;font-size:11px;border-color:#a78bfa;color:#ddd6fe;">Interval: OFF</button>
            <input id="p102-intvl-sec-input" type="number" min="1" max="60" value="5" title="Interval (1..60s)" style="width:52px;background:#07090c;color:#f8fafc;border:1px solid #374151;border-radius:6px;padding:3px 5px;font-size:10.5px;" />
            <input id="p102-target-shots-input" type="number" min="1" max="9999" value="120" title="Target Shots (1..9999)" style="width:62px;background:#07090c;color:#f8fafc;border:1px solid #374151;border-radius:6px;padding:3px 5px;font-size:10.5px;" />
            <select id="p102-ae-select" onchange="setPhase102State({ae_tracking: this.value})" style="flex:1;background:#172030;color:#e5e7eb;border:1px solid #374151;border-radius:6px;padding:3px;font-size:10.5px;">
              <option value="High">AE: High</option>
              <option value="Mid">AE: Mid</option>
              <option value="Low">AE: Low</option>
              <option value="Lock">AE: Lock</option>
            </select>
          </div>
          <div style="display:flex;gap:4px;align-items:center;margin-bottom:4px;">
            <button id="p102-btn-apply-intvl" onclick="applyPhase102IntervalParams()" style="padding:3px 7px;font-size:10.5px;border-color:#8b5cf6;">Apply Intvl</button>
            <button id="p102-btn-trigger-shot" onclick="setPhase102State({trigger_shot:true})" style="padding:3px 7px;font-size:10.5px;border-color:#a78bfa;">+1 E-Shot</button>
            <button id="p102-btn-reset-shots" onclick="setPhase102State({reset_shots:true})" style="padding:3px 7px;font-size:10.5px;">Reset Shots</button>
          </div>
          <div id="p102-intvl-readout" style="font-size:10px;color:#ddd6fe;font-family:'SF Mono',Menlo,monospace;">Shots: 0/120 @ 5s | Curtain Actuations: 0 (E-SH)</div>
        </div>

        <div class="cparam-box" style="border-color:#f59e0b;">
          <div class="cparam-head"><span id="p102-lbl-lut">User .cube 3D-LUT (17/33/65³ -> 33³ RAM)</span><span id="p102-lut-badge" style="color:#fde68a;font-family:'SF Mono',Menlo,monospace;">RAM 0B eMMC</span></div>
          <div style="display:flex;gap:4px;margin-bottom:5px;">
            <select id="p102-lut-slot-select" style="width:30%;background:#172030;color:#e5e7eb;border:1px solid #374151;border-radius:6px;padding:3px;font-size:10.5px;">
              <option value="User1">User1</option>
              <option value="User2">User2</option>
              <option value="User3">User3</option>
              <option value="User4">User4</option>
            </select>
            <input id="p102-lut-title-input" type="text" placeholder="LUT Title (optional)" style="flex:1;background:#07090c;color:#f8fafc;border:1px solid #374151;border-radius:6px;padding:3px 6px;font-size:10.5px;" />
            <button id="p102-btn-upload-lut" onclick="uploadPhase102CubeLut()" style="padding:3px 8px;font-size:10.5px;border-color:#f59e0b;color:#fde68a;">Upload .cube</button>
          </div>
          <textarea id="p102-cube-text" rows="2" placeholder="Paste Adobe .cube (17^3/33^3/65^3) or leave empty to test preset" style="width:100%;background:#07090c;color:#e2e8f0;border:1px solid #374151;border-radius:6px;padding:4px 6px;font-size:10px;font-family:'SF Mono',Menlo,monospace;resize:vertical;"></textarea>
          <div id="p102-lut-readout" style="margin-top:4px;font-size:10px;color:#fde68a;font-family:'SF Mono',Menlo,monospace;">LUT: None | 33³ SHA: none | Volatile RAM only</div>
        </div>

        <div class="cparam-box" style="border-color:#38bdf8;">
          <div class="cparam-head"><span id="p102-lbl-ftps">Wired USB-LAN FTPS (P12 RF-OFF)</span><span id="p102-ftps-badge" style="color:#38bdf8;font-family:'SF Mono',Menlo,monospace;">P12 SAFE · wf12=0</span></div>
          <div style="display:flex;gap:4px;margin-bottom:5px;">
            <select id="p102-ftps-mode-select" onchange="setPhase102State({ftps_mode: this.value})" style="width:46%;background:#172030;color:#e5e7eb;border:1px solid #374151;border-radius:6px;padding:3px;font-size:10.5px;">
              <option value="Off">Off</option>
              <option value="Proxy_Only">Proxy_Only (USB-LAN)</option>
              <option value="Original_And_Proxy">Original_And_Proxy</option>
            </select>
            <button id="p102-btn-ftp-enq" onclick="setPhase102State({enqueue_current_clip:true})" style="padding:3px 6px;font-size:10.5px;border-color:#38bdf8;">+Queue Clip</button>
            <button id="p102-btn-ftp-step" onclick="setPhase102State({process_next_job:true})" style="padding:3px 6px;font-size:10.5px;border-color:#10b981;">Send Next</button>
          </div>
          <div style="display:flex;gap:4px;margin-bottom:4px;">
            <input id="p102-ftp-path-input" type="text" value="/mnt/slot_a/PRIVATE/M4ROOT/CLIP/A001C001.MXF" style="flex:1;background:#07090c;color:#f8fafc;border:1px solid #374151;border-radius:6px;padding:3px 5px;font-size:10px;font-family:'SF Mono',Menlo,monospace;" />
            <button id="p102-btn-ftp-custom" onclick="enqueuePhase102CustomPath()" style="padding:3px 7px;font-size:10.5px;">Enqueue</button>
          </div>
          <div id="p102-ftps-readout" style="font-size:10px;color:#bae6fd;font-family:'SF Mono',Menlo,monospace;">USB_LAN_CDC_NCM_RTL8153 | Q=0 Done=0 BlkTrav=0 | wf12=0</div>
        </div>
      </div>

      <div class="pill-row">
        <button id="p102-preset-cache8" onclick="setPhase102State({cache_seconds:8,codec_profile:'XAVC_I_4K60'})" style="border-color:#10b981;color:#a7f3d0;">Cache 8s @ 4K60 (384 MiB Clamp)</button>
        <button id="p102-preset-intvl" onclick="setPhase102State({interval_rec_enabled:true,interval_sec:2,target_shots:240,ae_tracking:'Low'})" style="border-color:#a78bfa;color:#ddd6fe;">Interval 2s/240f (E-Shutter)</button>
        <button id="p102-preset-ftps" onclick="setPhase102State({ftps_mode:'Proxy_Only',enqueue_current_clip:true})" style="border-color:#38bdf8;color:#bae6fd;">USB-LAN FTPS Proxy Queue</button>
        <button id="p102-btn-reset" onclick="setPhase102State({reset:true})" style="padding:4px 8px;font-size:11px;">Reset P102</button>
      </div>
      <div id="p102-cmd-readout" style="margin-top:6px;font-size:10.5px;color:#34d399;font-family:'SF Mono',Menlo,monospace;">ICLF ...</div>
    </div>

    <div class="card" style="margin-top:14px;">
      <h3>Cinema Line 实时参数调节面板 (/api/cinema_param · Big-6 + HUD + P4/P11 硬件契约)</h3>
      <div id="param-toast" class="param-toast"></div>
      <div class="cinema-grid">
        <div class="cparam-box">
          <div class="cparam-head"><span>Cell 0 · FPS</span><span>S&amp;Q / Project</span></div>
          <div class="cparam-row">
            <button onclick="setCinemaParam('fps', -1)">◀</button>
            <span class="cparam-val" id="cp-fps">23.98p</span>
            <button onclick="setCinemaParam('fps', 1)">▶</button>
          </div>
        </div>
        <div class="cparam-box">
          <div class="cparam-head"><span>Cell 1 · EI / Base ISO</span><span id="cp-base-badge">800 Base</span></div>
          <div class="cparam-row">
            <button onclick="setCinemaParam('ei', -1)">◀</button>
            <span class="cparam-val" id="cp-ei">800 EI (800 Base)</span>
            <button onclick="setCinemaParam('ei', 1)">▶</button>
          </div>
        </div>
        <div class="cparam-box">
          <div class="cparam-head"><span>Cell 2 · Shutter</span><span>BK4 0x02cf1702/04</span></div>
          <div class="cparam-row">
            <button onclick="setCinemaParam('shutter', -1)">◀</button>
            <span class="cparam-val" id="cp-shutter">180.0°</span>
            <button onclick="setCinemaParam('shutter', 1)">▶</button>
          </div>
        </div>
        <div class="cparam-box locked">
          <div class="cparam-head"><span>Cell 3 · ND Filter</span><span style="color:#fbbf24;">P4 LOCKED</span></div>
          <div class="cparam-row">
            <button onclick="setCinemaParam('nd', -1)">◀</button>
            <span class="cparam-val" id="cp-nd" style="color:#fde68a;">Clear [FX3 P4 Locked]</span>
            <button onclick="setCinemaParam('nd', 1)">▶</button>
          </div>
        </div>
        <div class="cparam-box">
          <div class="cparam-head"><span>Cell 4 · Base Look / 3D LUT</span><span>P1 + P11 33³</span></div>
          <div class="cparam-row">
            <button onclick="setCinemaParam('lut', -1)">◀</button>
            <span class="cparam-val" id="cp-lut">S-Cinetone</span>
            <button onclick="setCinemaParam('lut', 1)">▶</button>
          </div>
        </div>
        <div class="cparam-box">
          <div class="cparam-head"><span>Cell 5 · White Balance</span><span>Preset / ATW</span></div>
          <div class="cparam-row">
            <button onclick="setCinemaParam('wb', -1)">◀</button>
            <span class="cparam-val" id="cp-wb">5600K</span>
            <button onclick="setCinemaParam('wb', 1)">▶</button>
          </div>
        </div>
        <div class="cparam-box">
          <div class="cparam-head"><span>P11 · 5-Axis IBIS</span><span>Center Lock</span></div>
          <div class="cparam-row">
            <button onclick="setCinemaParam('ibis', -1)">◀</button>
            <span class="cparam-val" id="cp-ibis">5-Axis Center Lock (P11)</span>
            <button onclick="setCinemaParam('ibis', 1)">▶</button>
          </div>
        </div>
        <div class="cparam-box">
          <div class="cparam-head"><span>P11 · XLR-H1 Audio</span><span>Handle 0x5d90</span></div>
          <div class="cparam-row">
            <button onclick="setCinemaParam('xlr', -1)">◀</button>
            <span class="cparam-val" id="cp-xlr">XLR-H1 Ch1/2 +48V (0x5d90)</span>
            <button onclick="setCinemaParam('xlr', 1)">▶</button>
          </div>
        </div>
      </div>
      <div class="pill-row">
        <button onclick="setCinemaPreset('fps', '23.98p')">23.98p</button>
        <button onclick="setCinemaPreset('fps', '59.94p')">59.94p</button>
        <button onclick="setCinemaPreset('fps', '119.88p (S&Q)')">119.88p S&amp;Q</button>
        <button onclick="setCinemaPreset('ei', '800 EI (800 Base)')">800 EI (Base 800)</button>
        <button onclick="setCinemaPreset('ei', '12800 EI (12800 Base)')">12800 EI (Base 12800)</button>
        <button onclick="setCinemaPreset('shutter', '180.0°')">180.0°</button>
        <button onclick="setCinemaPreset('shutter', '1/48')">1/48</button>
        <button onclick="setCinemaPreset('lut', 'S-Cinetone')">S-Cinetone</button>
        <button onclick="setCinemaPreset('lut', 'S-Log3.Cine / S-Gamut3.Cine')">S-Log3.Cine</button>
        <button onclick="setCinemaPreset('lut', 'User1 (33³ .cube)')">User1 33³</button>
        <button onclick="setCinemaPreset('wb', '5600K')">5600K</button>
        <button onclick="setCinemaPreset('wb', 'ATW')">ATW</button>
        <button onclick="setCinemaParam('nd', 1)" style="border-color:#f59e0b;color:#fde68a;">Test P4 ND Lock</button>
      </div>
    </div>

    <div class="card" style="margin-top:14px;">
      <h3>Phase 40 · 4-Ch XLR-H1 音频 VU 表 &amp; RTMD 0xE304 + .cube 3D LUT 导入 + CAMSET 场景预设</h3>
      <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-bottom:10px;">
        <div class="cparam-box">
          <div class="cparam-head">
            <span>4-Ch XLR-H1 Audio Trim / VU</span>
            <span id="xlr-route-badge" style="color:#22d3ee;">XLR-H1 0x5d90</span>
          </div>
          <div id="xlr-vu-rows" style="display:flex;flex-direction:column;gap:5px;font-family:'SF Mono',Menlo,monospace;font-size:11px;">
            <div style="display:flex;align-items:center;gap:6px;">
              <span style="width:32px;">CH1</span>
              <input id="audio-ch1" type="range" min="-60" max="12" value="-12" style="flex:1;" onchange="setAudioTrim()" />
              <span id="audio-ch1-db" style="width:42px;text-align:right;">-12dB</span>
              <div style="width:48px;height:8px;background:#1f2937;border-radius:3px;overflow:hidden;"><div id="audio-vu1" style="height:100%;width:66%;background:#10b981;"></div></div>
            </div>
            <div style="display:flex;align-items:center;gap:6px;">
              <span style="width:32px;">CH2</span>
              <input id="audio-ch2" type="range" min="-60" max="12" value="-12" style="flex:1;" onchange="setAudioTrim()" />
              <span id="audio-ch2-db" style="width:42px;text-align:right;">-12dB</span>
              <div style="width:48px;height:8px;background:#1f2937;border-radius:3px;overflow:hidden;"><div id="audio-vu2" style="height:100%;width:66%;background:#10b981;"></div></div>
            </div>
            <div style="display:flex;align-items:center;gap:6px;">
              <span style="width:32px;">CH3</span>
              <input id="audio-ch3" type="range" min="-60" max="12" value="-18" style="flex:1;" onchange="setAudioTrim()" />
              <span id="audio-ch3-db" style="width:42px;text-align:right;">-18dB</span>
              <div style="width:48px;height:8px;background:#1f2937;border-radius:3px;overflow:hidden;"><div id="audio-vu3" style="height:100%;width:58%;background:#10b981;"></div></div>
            </div>
            <div style="display:flex;align-items:center;gap:6px;">
              <span style="width:32px;">CH4</span>
              <input id="audio-ch4" type="range" min="-60" max="12" value="-18" style="flex:1;" onchange="setAudioTrim()" />
              <span id="audio-ch4-db" style="width:42px;text-align:right;">-18dB</span>
              <div style="width:48px;height:8px;background:#1f2937;border-radius:3px;overflow:hidden;"><div id="audio-vu4" style="height:100%;width:58%;background:#10b981;"></div></div>
            </div>
          </div>
          <div class="pill-row" style="margin-top:8px;">
            <button id="btn-xlr-attach" onclick="toggleXlrAttach()">XLR-H1: Attached</button>
            <button id="btn-xlr-48v" onclick="toggleXlr48v()">+48V: ON</button>
            <select id="rtmd-ibis-select" onchange="setRtmdIbis()" style="background:#172030;color:#e5e7eb;border:1px solid #374151;border-radius:6px;padding:4px 6px;font-size:11px;">
              <option value="ACTIVE_5AXIS">RTMD 0xE304: ACTIVE_5AXIS</option>
              <option value="OFF_CENTER_LOCKED">RTMD 0xE304: OFF_CENTER_LOCKED</option>
              <option value="STANDARD">RTMD 0xE304: STANDARD</option>
            </select>
          </div>
        </div>

        <div class="cparam-box">
          <div class="cparam-head">
            <span>.cube 3D LUT User1..User4 Uploader</span>
            <span style="display:inline-flex;align-items:center;gap:5px;">
              <span id="lut-swatch" style="display:inline-block;width:12px;height:12px;border-radius:3px;background:#808080;border:1px solid #e5e7eb;"></span>
              <span id="lut-tint-hex">#808080</span>
            </span>
          </div>
          <div style="display:flex;gap:6px;margin-bottom:6px;">
            <select id="lut-slot-select" style="background:#172030;color:#e5e7eb;border:1px solid #374151;border-radius:6px;padding:5px;font-size:11px;">
              <option value="User1">User1</option>
              <option value="User2">User2</option>
              <option value="User3">User3</option>
              <option value="User4">User4</option>
            </select>
            <input id="lut-name-input" type="text" placeholder="LUT Name (e.g. Kodak2383)" style="flex:1;background:#0a0f18;color:#e5e7eb;border:1px solid #374151;border-radius:6px;padding:5px 7px;font-size:11px;" />
            <input id="lut-file-input" type="file" accept=".cube,.txt" onchange="onCubeFilePick(event)" style="width:82px;font-size:10px;color:#9ca3af;" />
          </div>
          <div class="pill-row" style="margin-bottom:6px;">
            <button onclick="uploadBuiltinCube('709_typeA')">709 Type-A</button>
            <button onclick="uploadBuiltinCube('teal_orange')">Teal&amp;Orange</button>
            <button onclick="uploadBuiltinCube('film_2383')">Film 2383</button>
            <button onclick="uploadBuiltinCube('slog3_bypass')">SLog3 Bypass</button>
          </div>
          <textarea id="cube-text-input" rows="2" placeholder="Paste Adobe .cube text (LUT_3D_SIZE 17 or 33)..." style="width:100%;background:#07090c;color:#cbd5e1;border:1px solid #283548;border-radius:6px;padding:5px;font-family:'SF Mono',Menlo,monospace;font-size:10.5px;"></textarea>
          <div style="display:flex;gap:6px;margin-top:5px;align-items:center;">
            <button onclick="uploadCustomCube()" style="background:#0f2b46;border-color:#22d3ee;">Sanitize &amp; Load .cube</button>
            <span id="lut-upload-status" style="font-size:10.5px;color:#9ca3af;font-family:'SF Mono',Menlo,monospace;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">Ready (libmpr SetLutData Guard Active)</span>
          </div>
        </div>
      </div>

      <div class="cparam-box">
        <div class="cparam-head">
          <span>CAMSET Scene File Preset Save / Load (fx6_on_fx3_camset_v1 · P4 &amp; BK4 Enforced)</span>
          <span id="camset-sha-readout" style="color:#67e8f9;font-family:'SF Mono',Menlo,monospace;">sha256: -</span>
        </div>
        <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin-bottom:6px;">
          <button onclick="exportCamset()">Export CAMSET JSON</button>
          <button onclick="importCamset()">Import CAMSET JSON</button>
          <button onclick="testCamsetP4Tamper()" style="border-color:#f59e0b;color:#fde68a;">Test P4 ND Tamper Lock</button>
          <button onclick="importFx6FleetCamsetPreset()" style="border-color:#38bdf8;color:#bae6fd;">Import FX6 Fleet Preset</button>
          <span id="camset-lock-badge" style="font-size:11px;color:#fde68a;font-family:'SF Mono',Menlo,monospace;">P4 rejects=0 | BK4=LOCKED</span>
        </div>
        <textarea id="camset-json-box" rows="2" placeholder="Exported fx6_on_fx3_camset_v1 JSON appears here..." style="width:100%;background:#07090c;color:#a7f3d0;border:1px solid #283548;border-radius:6px;padding:5px;font-family:'SF Mono',Menlo,monospace;font-size:10.5px;"></textarea>
      </div>
    </div>

    <div class="card" style="margin-top:14px;">
      <h3>FX6 原生页面直达切换 (Guest 0x41e000e00 Mailbox -> appFw.so 实时重绘)</h3>
      <div class="page-grid" id="page-buttons">
        <button onclick="setPage(0)" id="pbtn-0">0. Big-6 主界面</button>
        <button onclick="setPage(1)" id="pbtn-1">1. 三层完整菜单</button>
        <button onclick="setPage(2)" id="pbtn-2">2. Setting Main</button>
        <button onclick="setPage(3)" id="pbtn-3">3. Setting Center</button>
        <button onclick="setPage(4)" id="pbtn-4">4. Assignable 30键</button>
        <button onclick="setPage(5)" id="pbtn-5">5. Network 状态/176</button>
        <button onclick="setPage(6)" id="pbtn-6">6. 寻像器 HUD 条</button>
        <button onclick="setPage(7)" id="pbtn-7">7. Clip / Playback</button>
        <button onclick="setPage(8)" id="pbtn-8">8. Status / Grid 69</button>
        <button onclick="setPage(9)" id="pbtn-9">9. Thumbnail 全屏页</button>
        <button onclick="setPage(10)" id="pbtn-10">10. Touch 触控浮层</button>
        <button onclick="setPage(11)" id="pbtn-11">11. Subpage + Gamma</button>
        <button onclick="setPage(12)" id="pbtn-12">12. Paint 键盘输入102</button>
        <button onclick="setPage(13)" id="pbtn-13">13. Media 状态页48</button>
        <button onclick="setPage(14)" id="pbtn-14">14. Clip 12宫格缩略图</button>
        <button onclick="setPage(15)" id="pbtn-15">15. StatusIcon/Date/Track</button>
        <button onclick="setPage(16)" id="pbtn-16">16. HUD 253行完整主界面</button>
        <button onclick="setPage(17)" id="pbtn-17">17. TC/电平表/6键状态页</button>
        <button onclick="setPage(18)" id="pbtn-18">18. 6行通知对话框 p81</button>
        <button onclick="setPage(19)" id="pbtn-19">19. Wi-Fi SSID 扫描页</button>
        <button onclick="setPage(20)" id="pbtn-20">20. 三列设置列表 p66/73</button>
        <button onclick="setPage(21)" id="pbtn-21">21. 确认/执行弹窗 p72/93</button>
        <button onclick="setPage(22)" id="pbtn-22">22. 双栏设置/横幅 p77/112</button>
        <button onclick="setPage(23)" id="pbtn-23">23. 15键/10键宫格 p64/57</button>
      </div>

      <h3>全量 128 个 FX6 原生页面描述符直达 (fx6_all_pages[0..127] · Universal Descriptor Table Mode)</h3>
      <div style="display:flex;gap:8px;margin-bottom:14px;align-items:center;">
        <button onclick="step128(-1)">◀ 上一页</button>
        <select id="all128-select" onchange="onSelect128()" style="flex:1;background:#1f2633;color:var(--text);border:1px solid #374151;border-radius:7px;padding:8px 10px;font-size:12px;font-family:'SF Mono',Menlo,monospace;">
          <option value="">-- 选择 fx6_all_pages[0..127] 任意原生页面描述符表 --</option>
        </select>
        <button onclick="step128(1)">下一页 ▶</button>
      </div>

      <h3>三层菜单 11 大分类直达 (TABLE 0x2ea02f8 + string_english_2.uxc)</h3>
      <div class="cat-grid" id="cat-buttons">
        <button onclick="setCat(0)" id="cbtn-0">1. User</button>
        <button onclick="setCat(1)" id="cbtn-1">2. Edit User Menu</button>
        <button onclick="setCat(2)" id="cbtn-2">3. Shooting</button>
        <button onclick="setCat(3)" id="cbtn-3">4. Project</button>
        <button onclick="setCat(4)" id="cbtn-4">5. Paint/Look</button>
        <button onclick="setCat(5)" id="cbtn-5">6. TC/Media</button>
        <button onclick="setCat(6)" id="cbtn-6">7. Monitoring</button>
        <button onclick="setCat(7)" id="cbtn-7">8. Audio</button>
        <button onclick="setCat(8)" id="cbtn-8">9. Thumbnail</button>
        <button onclick="setCat(9)" id="cbtn-9">10. Technical</button>
        <button onclick="setCat(10)" id="cbtn-10">11. Maintenance</button>
      </div>
    </div>
  </div>

  <div style="display:flex;flex-direction:column;gap:14px;">
    <div class="card">
      <h3>FX6 机身按键面板 (支持直接点击画面 / 键盘方向键 / Enter / M / H)</h3>
      <div class="dpad-grid">
        <button onclick="sendKey('HOME')">HOME</button>
        <button onclick="sendKey('UP')">▲ UP</button>
        <button onclick="sendKey('MENU')">MENU</button>

        <button onclick="sendKey('LEFT')">◀ LEFT</button>
        <button onclick="sendKey('SET')" class="btn-set">● SET</button>
        <button onclick="sendKey('RIGHT')">RIGHT ▶</button>

        <button onclick="sendKey('BACK')">BACK</button>
        <button onclick="sendKey('DOWN')">▼ DOWN</button>
        <button onclick="sendKey('DISP')">DISP</button>
      </div>
      <div style="font-size:12px;color:var(--muted);line-height:1.5;">
        • <b>直接点击画面</b>：点击画面左上角 <b>Menu</b> 区域即可进入/退出三层菜单；在 Big-6 主界面点击任意外围 6 格可选中或切换值；在三层菜单点击左侧分类或右侧条目可直接切换。<br/>
        • <b>机身按键/键盘</b>：方向键移动高亮框 (<code>0x0200c011</code>)，<b>SET (Enter)</b> 切换值，<b>MENU (M)</b> 打开三层菜单。
      </div>
    </div>

    <div class="card">
      <h3>ILME-FX3 物理机身控制面板 (Top / Rear Deck · Stage-B P10 映射)</h3>
      <div class="page-grid" style="margin-bottom:8px;">
        <button onclick="sendFx3Button('FN')" title="FX3 Fn (0x0013 -> 0x7095 / PF_K_HOME)">Fn → Big-6 主页</button>
        <button onclick="sendFx3Button('MENU')" title="FX3 MENU (0x0011 -> 0x01ab / UIBIZ_KEY_TACT_MENU)">MENU → 3层菜单</button>
        <button onclick="sendFx3Button('DISP')" title="FX3 DISP (0x0025 -> 0x70ec / PF_K_DISP_SEL)">DISP → HUD p16/p6</button>
        <button onclick="sendFx3Button('C1')" title="FX3 C1 (0x001d -> 0x0066 / PF_K_KURU_PON)">C1 → Base Look/LUT</button>
        <button onclick="sendFx3Button('C2')" title="FX3 C2 (0x0024 -> 0x70e7 / PF_K_MENU_CANCEL)">C2 → 白平衡/Setting</button>
        <button onclick="sendFx3Button('C3')" title="FX3 C3 (0x0025 -> 0x70ec / PF_K_DISP_SEL)">C3 → Audio/TC p17</button>
        <button onclick="sendFx3Button('C4')" title="FX3 C4 (0x0026 -> 0x70ed / PF_K_SLOT_SEL)">C4 → Media SSA/SSB p13</button>
        <button onclick="sendFx3Button('C5')" title="FX3 C5/DEL (0x000c -> 0x01f8 / PF_K_USER)">C5 → Assignable p4</button>
        <button onclick="sendFx3Button('C6')" title="FX3 C6/PLAY (0x000b -> 0x01f7 / PF_K_THUMBNAIL)">C6 → Clip 浏览器 p14</button>
        <button onclick="sendFx3Button('WHEEL_UP')" title="FX3 Rear Dial UP (0x0003 -> 0x7081 / PF_K_UP)">WHEEL ▲ UP</button>
        <button onclick="sendFx3Button('WHEEL_SET')" class="btn-set" title="FX3 Rear Dial SET (0x001c -> 0x01ac / PF_K_SET)">● WHEEL SET</button>
        <button onclick="sendFx3Button('WHEEL_DOWN')" title="FX3 Rear Dial DOWN (0x0030 -> 0x7082 / PF_K_DOWN)">WHEEL ▼ DOWN</button>
        <button onclick="sendFx3Button('BACK')" title="FX3 BACK/CANCEL (0x0024 -> 0x70e7 / PF_K_MENU_CANCEL)" style="grid-column:span 3;">BACK / CANCEL (返回/取消)</button>
      </div>
      <div id="p10-telemetry-readout" style="font-size:11px;color:#67e8f9;background:#0a0f18;border:1px solid #1e293b;border-radius:6px;padding:7px 9px;font-family:'SF Mono',Menlo,monospace;line-height:1.45;">
        Stage-B P10 遥测: IDLE (点击任意 FX3 物理按键发送 /api/fx3_button)
      </div>
    </div>

    <div class="card">
      <h3>QEMU 虚拟机串口实时日志 (FX6_LIVE_READY / FX6_LIVE_FRAME)</h3>
      <div id="serial-box" class="serial-box">正在连接虚拟机串口...</div>
    </div>
  </div>
</div>

<script>
let busy = false;
let currentStatus = null;
let pages128 = [];

async function loadPages128() {
  try {
    const r = await fetch('/api/pages128');
    pages128 = await r.json();
    const sel = document.getElementById('all128-select');
    if (sel && pages128.length) {
      pages128.forEach((p, idx) => {
        const opt = document.createElement('option');
        opt.value = String(idx);
        opt.textContent = `Page ${String(p.idx).padStart(3,'0')} | ${p.off_hex} (${String(p.rows).padStart(3,' ')} rows) | ${p.first_name}`;
        sel.appendChild(opt);
      });
    }
  } catch (e) {}
}

function onSelect128() {
  const sel = document.getElementById('all128-select');
  if (!sel || sel.value === '') return;
  const p = pages128[parseInt(sel.value, 10)];
  if (p) {
    sendPayload({table_off: p.off, table_rows: p.rows, table_off2: 0, table_rows2: 0});
  }
}

function step128(delta) {
  const sel = document.getElementById('all128-select');
  if (!sel || !pages128.length) return;
  let cur = sel.value === '' ? 0 : parseInt(sel.value, 10) + delta;
  if (cur < 0) cur = pages128.length - 1;
  if (cur >= pages128.length) cur = 0;
  sel.value = String(cur);
  onSelect128();
}

async function updateUI(st, forceImg) {
  if (!st) return;
  currentStatus = st;
  const badge = document.getElementById('stage-badge');
  const overlay = document.getElementById('boot-overlay');
  badge.textContent = st.stage + (st.running ? ` (${st.elapsed_sec}s)` : '');
  if (st.live_ready) {
    badge.className = 'badge';
    overlay.style.display = 'none';
  } else {
    badge.className = 'badge booting';
    overlay.style.display = 'block';
    overlay.textContent = `虚拟机正在启动 FX6 系统: ${st.stage} (已运行 ${st.elapsed_sec}s / 约需 42s 到达 FX6_LIVE_READY)...`;
  }

  document.getElementById('st-page').textContent = st.page_name;
  const langEl = document.getElementById('st-lang');
  if (langEl) langEl.textContent = `${st.lang_label || 'English'} (${(st.lang || 'en').toUpperCase()})`;
  const langBtn = document.getElementById('lang-toggle-btn');
  if (langBtn) {
    const isZh = st.lang === 'zh';
    langBtn.textContent = isZh ? '🌐 中文 / EN [当前: 简体中文]' : '🌐 中文 / EN [Current: EN]';
  }
  ['en', 'zh', 'ja'].forEach((lc) => {
    const lb = document.getElementById('lbtn-' + lc);
    if (lb) lb.className = (st.lang === lc) ? 'active' : '';
  });

  const cp = st.cinema_params || {};
  const vals = cp.values || {};
  ['fps', 'ei', 'shutter', 'nd', 'lut', 'wb', 'ibis', 'xlr'].forEach((k) => {
    const el = document.getElementById('cp-' + k);
    if (el && vals[k] !== undefined) el.textContent = vals[k];
  });
  const baseBadge = document.getElementById('cp-base-badge');
  if (baseBadge && cp.base_iso) baseBadge.textContent = `${cp.base_iso} Base`;

  const pToast = document.getElementById('param-toast');
  if (pToast) {
    if (st.last_toast) {
      pToast.style.display = 'block';
      pToast.textContent = st.last_toast;
      pToast.className = st.last_toast.includes('P4') ? 'param-toast warn' : 'param-toast';
    } else {
      pToast.style.display = 'none';
    }
  }

  const sbt = st.stage_b_telemetry || {};
  if (sbt.P1) document.getElementById('tel-p1-d').textContent = sbt.P1.detail;
  if (sbt.P4) document.getElementById('tel-p4-d').textContent = sbt.P4.detail;
  if (sbt.P10) document.getElementById('tel-p10-d').textContent = sbt.P10.detail;
  if (sbt.P11) document.getElementById('tel-p11-d').textContent = sbt.P11.detail;
  if (sbt.P12) document.getElementById('tel-p12-d').textContent = sbt.P12.detail;

  const p10 = st.p10_telemetry || {};
  const p10Text = p10.button
    ? `${p10.button}: ${p10.phy_code} -> ${p10.infra_code} (${p10.p10_symbol})`
    : 'IDLE';
  const p10El = document.getElementById('st-p10');
  if (p10El) p10El.textContent = p10Text;
  const p10Box = document.getElementById('p10-telemetry-readout');
  if (p10Box) {
    p10Box.textContent = p10.button
      ? `Stage-B P10 遥测: [${p10.button}] ${p10.label} | phy=${p10.phy_code} -> infra=${p10.infra_code} (${p10.p10_symbol}) | target_page=${p10.target_page} | seq=${p10.cmd_seq}`
      : 'Stage-B P10 遥测: IDLE (点击任意 FX3 物理按键发送 /api/fx3_button)';
  }

  // Phase 40: 4-Ch XLR-H1 Audio VU + RTMD 0xE304 + .cube LUT + CAMSET sync
  const chDb = st.audio_ch_db || [-12, -12, -18, -18];
  for (let c = 0; c < 4; c++) {
    const dbVal = (chDb[c] !== undefined) ? Number(chDb[c]) : -12;
    const rng = document.getElementById('audio-ch' + (c + 1));
    const lbl = document.getElementById('audio-ch' + (c + 1) + '-db');
    const vu = document.getElementById('audio-vu' + (c + 1));
    if (rng && document.activeElement !== rng) rng.value = String(dbVal);
    if (lbl) lbl.textContent = `${dbVal >= 0 ? '+' : ''}${dbVal}dB`;
    if (vu) {
      const pct = Math.max(4, Math.min(100, Math.round(((dbVal + 60) / 72) * 100)));
      vu.style.width = pct + '%';
      vu.style.background = (!st.xlr_handle_attached && c >= 2) ? '#4b5563' : (dbVal > -6 ? '#f59e0b' : '#10b981');
    }
  }
  const routeBadge = document.getElementById('xlr-route-badge');
  if (routeBadge) {
    routeBadge.textContent = st.xlr_handle_attached
      ? (st.xlr_phantom_48v ? 'XLR-H1 0x5d90 (+48V)' : 'XLR-H1 0x5d90 (LINE)')
      : 'Internal Stereo (P11 Fallback)';
    routeBadge.style.color = st.xlr_handle_attached ? '#22d3ee' : '#fbbf24';
  }
  const xlrAttachBtn = document.getElementById('btn-xlr-attach');
  if (xlrAttachBtn) xlrAttachBtn.textContent = st.xlr_handle_attached ? 'XLR-H1: Attached' : 'XLR-H1: Detached (Internal)';
  const xlr48Btn = document.getElementById('btn-xlr-48v');
  if (xlr48Btn) xlr48Btn.textContent = st.xlr_phantom_48v ? '+48V: ON' : '+48V: OFF';
  const rtmdSel = document.getElementById('rtmd-ibis-select');
  if (rtmdSel && st.rtmd_0xe304_ibis_lock && document.activeElement !== rtmdSel) {
    rtmdSel.value = st.rtmd_0xe304_ibis_lock;
  }

  const activeLut = cp.active_user_lut || null;
  const lutSlots = st.user_lut_slots || {};
  const slotSel = document.getElementById('lut-slot-select');
  const shownLut = activeLut || (slotSel && lutSlots[slotSel.value]) || lutSlots.User1;
  const swatchEl = document.getElementById('lut-swatch');
  const hexEl = document.getElementById('lut-tint-hex');
  if (shownLut && swatchEl && hexEl) {
    const tintHex = shownLut.tint_hex || '#808080';
    swatchEl.style.background = tintHex;
    hexEl.textContent = `${shownLut.slot || 'User1'}: ${tintHex}`;
  }
  const lockBadge = document.getElementById('camset-lock-badge');
  if (lockBadge) {
    const rej = st.p4_nd_reject_count || 0;
    const bk4 = st.p12_bk4_airplane_mode_locked !== false ? 'LOCKED' : 'OPEN';
    lockBadge.textContent = `P4 rejects=${rej} | BK4=${bk4}`;
  }

  document.getElementById('st-nz').textContent = st.gpe0_nonzero_px;
  document.getElementById('st-text').textContent = st.text_ok;
  document.getElementById('st-fill').textContent = `${st.fill_n} / ${st.icon_n}`;
  document.getElementById('st-seq').textContent = `${st.ack_seq} / ${st.cmd_seq}`;
  document.getElementById('st-src').textContent = st.png_source;
  document.getElementById('serial-box').textContent = st.serial_tail || '(等待串口输出...)';

  for (let i = 0; i < 24; i++) {
    const b = document.getElementById('pbtn-' + i);
    if (b) b.className = (st.page === i) ? 'active' : '';
  }
  const sel128 = document.getElementById('all128-select');
  if (sel128) {
    sel128.value = (st.page === 24 && st.table_idx128 !== undefined) ? String(st.table_idx128) : '';
  }
  for (let i = 0; i < 11; i++) {
    const b = document.getElementById('cbtn-' + i);
    if (b) b.className = (st.page === 1 && st.menu_cat === i) ? 'active' : '';
  }

  const at = st.assist_tools || {};
  const aspSel = document.getElementById('assist-aspect-select');
  if (aspSel && at.aspect_marker && document.activeElement !== aspSel) aspSel.value = at.aspect_marker;
  const zebSel = document.getElementById('assist-zebra-select');
  if (zebSel && at.zebra_mode && document.activeElement !== zebSel) zebSel.value = at.zebra_mode;
  const pkSel = document.getElementById('assist-peaking-select');
  if (pkSel && at.peaking_mode && document.activeElement !== pkSel) pkSel.value = at.peaking_mode;
  const dsqSel = document.getElementById('assist-desqueeze-select');
  if (dsqSel && at.desqueeze && document.activeElement !== dsqSel) dsqSel.value = at.desqueeze;
  const ga = st.gyroflow_anamorphic || null;
  const previewSq = (ga && ga.squeeze_display) || at.desqueeze || '1.0x';
  applyDesqueezePreview(previewSq);

  if (st.cine_exposure) {
    syncCineExposureUI(st.cine_exposure);
  }
  if (st.color_and_media) {
    syncColorAndMediaUI(st.color_and_media);
  }
  if (st.touch_focus_ciz) {
    syncTouchFocusCizUI(st.touch_focus_ciz);
  }
  if (st.shotmark_and_iris) {
    syncShotmarkIrisUI(st.shotmark_and_iris);
  }
  if (st.gyroflow_anamorphic) {
    syncGyroflowAnamorphicUI(st.gyroflow_anamorphic);
  }
  if (st.interval_cache_lut_ftp) {
    syncPhase102IntervalCacheLutFtpUI(st.interval_cache_lut_ftp);
  }
  if (st.mc_fleet_sdi_c2pa) {
    syncPhase109McFleetSdiC2paUI(st.mc_fleet_sdi_c2pa);
  }
  if (st.hdr_hlg_raw_breathing) {
    syncPhase116HlgRawBreathingUI(st.hdr_hlg_raw_breathing);
  }
  if (st.uvc_srt_crsdk_ptp) {
    syncPhase123UvcSrtCrsdkPtpUI(st.uvc_srt_crsdk_ptp);
  }

  if (forceImg || st.live_ready) {
    document.getElementById('gpe0-img').src = '/api/frame.png?t=' + Date.now();
  }
  if (forceImg || !scopeLoadedOnce) {
    refreshScopeStats(false);
  }
}

async function sendPayload(payload) {
  if (busy) return;
  busy = true;
  const toast = document.getElementById('render-toast');
  toast.style.display = 'block';
  try {
    const r = await fetch('/api/key', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload)
    });
    const data = await r.json();
    await updateUI(data.status, true);
  } finally {
    toast.style.display = 'none';
    busy = false;
  }
}

async function setCinemaParam(param, delta) {
  if (busy) return;
  busy = true;
  const toast = document.getElementById('render-toast');
  toast.style.display = 'block';
  try {
    const r = await fetch('/api/cinema_param', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({param: param, delta: delta})
    });
    const data = await r.json();
    if (data.status) await updateUI(data.status, true);
  } finally {
    toast.style.display = 'none';
    busy = false;
  }
}

async function setCinemaPreset(param, preset) {
  if (busy) return;
  busy = true;
  const toast = document.getElementById('render-toast');
  toast.style.display = 'block';
  try {
    const r = await fetch('/api/cinema_param', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({param: param, preset: preset})
    });
    const data = await r.json();
    if (data.status) await updateUI(data.status, true);
  } finally {
    toast.style.display = 'none';
    busy = false;
  }
}

async function postCinemaRaw(bodyObj) {
  if (busy) return;
  busy = true;
  const toast = document.getElementById('render-toast');
  toast.style.display = 'block';
  try {
    const r = await fetch('/api/cinema_param', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(bodyObj)
    });
    const data = await r.json();
    if (data.status) await updateUI(data.status, true);
    return data;
  } finally {
    toast.style.display = 'none';
    busy = false;
  }
}

function setAudioTrim() {
  const payload = {
    ch1_db: Number(document.getElementById('audio-ch1').value),
    ch2_db: Number(document.getElementById('audio-ch2').value),
    ch3_db: Number(document.getElementById('audio-ch3').value),
    ch4_db: Number(document.getElementById('audio-ch4').value)
  };
  postCinemaRaw(payload);
}

function toggleXlrAttach() {
  const cur = currentStatus ? !!currentStatus.xlr_handle_attached : true;
  postCinemaRaw({xlr_handle_attached: !cur});
}

function toggleXlr48v() {
  const cur = currentStatus ? !!currentStatus.xlr_phantom_48v : true;
  postCinemaRaw({xlr_phantom_48v: !cur});
}

function setRtmdIbis() {
  const sel = document.getElementById('rtmd-ibis-select');
  if (sel) postCinemaRaw({rtmd_0xe304_ibis_lock: sel.value});
}

function onCubeFilePick(e) {
  const f = e.target && e.target.files && e.target.files[0];
  if (!f) return;
  const nameIn = document.getElementById('lut-name-input');
  if (nameIn && !nameIn.value.trim()) {
    nameIn.value = f.name.replace(/\.cube$/i, '').slice(0, 23);
  }
  const reader = new FileReader();
  reader.onload = () => {
    const box = document.getElementById('cube-text-input');
    if (box) box.value = String(reader.result || '');
  };
  reader.readAsText(f);
}

async function uploadBuiltinCube(presetKey) {
  const slot = (document.getElementById('lut-slot-select') || {}).value || 'User1';
  const name = (document.getElementById('lut-name-input') || {}).value || '';
  await _postLutUpload({slot: slot, preset: presetKey, name: name || undefined});
}

async function uploadCustomCube() {
  const slot = (document.getElementById('lut-slot-select') || {}).value || 'User1';
  const name = (document.getElementById('lut-name-input') || {}).value || '';
  const cubeText = (document.getElementById('cube-text-input') || {}).value || '';
  await _postLutUpload({slot: slot, name: name, cube_text: cubeText});
}

async function _postLutUpload(payload) {
  if (busy) return;
  busy = true;
  const toast = document.getElementById('render-toast');
  const statusEl = document.getElementById('lut-upload-status');
  toast.style.display = 'block';
  try {
    const r = await fetch('/api/lut_upload', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload)
    });
    const data = await r.json();
    if (statusEl) {
      if (data.ok && data.lut) {
        statusEl.style.color = '#a7f3d0';
        statusEl.textContent = `OK ${data.lut.slot}: ${data.lut.name} (${data.lut.size}³ ${data.lut.tint_hex})`;
      } else {
        statusEl.style.color = '#fca5a5';
        statusEl.textContent = `Rejected (${data.error || 'err'}): ${data.message || ''}`;
      }
    }
    if (data.status) await updateUI(data.status, true);
  } finally {
    toast.style.display = 'none';
    busy = false;
  }
}

async function exportCamset() {
  const r = await fetch('/api/preset_export');
  const data = await r.json();
  const box = document.getElementById('camset-json-box');
  const sha = document.getElementById('camset-sha-readout');
  if (box) box.value = JSON.stringify(data, null, 2);
  if (sha && data.preset_sha256) sha.textContent = `sha256: ${data.preset_sha256.slice(0, 16)}...`;
}

async function importCamset() {
  const box = document.getElementById('camset-json-box');
  const sha = document.getElementById('camset-sha-readout');
  if (!box) return;
  let parsed;
  try {
    parsed = JSON.parse(box.value);
  } catch (e) {
    if (sha) sha.textContent = 'Invalid JSON in CAMSET box';
    return;
  }
  const r = await fetch('/api/preset_import', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(parsed)
  });
  const data = await r.json();
  if (data.status) await updateUI(data.status, true);
}

async function testCamsetP4Tamper() {
  const rExp = await fetch('/api/preset_export');
  const camset = await rExp.json();
  camset.cinema_params = camset.cinema_params || {};
  camset.cinema_params.nd = '1/16 ND';
  const box = document.getElementById('camset-json-box');
  if (box) box.value = JSON.stringify(camset, null, 2);
  const rImp = await fetch('/api/preset_import', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(camset)
  });
  const data = await rImp.json();
  if (data.status) await updateUI(data.status, true);
}

async function setLang(langCode) {
  if (busy) return;
  busy = true;
  const toast = document.getElementById('render-toast');
  toast.style.display = 'block';
  try {
    const r = await fetch('/api/lang', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({lang: langCode})
    });
    const data = await r.json();
    if (data.status) await updateUI(data.status, true);
  } finally {
    toast.style.display = 'none';
    busy = false;
  }
}

function toggleLang() {
  const cur = (currentStatus && currentStatus.lang) ? currentStatus.lang : 'en';
  setLang(cur === 'zh' ? 'en' : 'zh');
}

async function sendFx3Button(btn) {
  if (busy) return;
  busy = true;
  const toast = document.getElementById('render-toast');
  toast.style.display = 'block';
  try {
    const r = await fetch('/api/fx3_button', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({button: btn})
    });
    const data = await r.json();
    if (data.status) await updateUI(data.status, true);
  } finally {
    toast.style.display = 'none';
    busy = false;
  }
}

function sendKey(k) { sendPayload({key: k}); }
function setPage(p) { sendPayload({page: p}); }
function setCat(c)  { sendPayload({page: 1, menu_cat: c, menu_item: 0, menu_depth: 0}); }

let clickCanvasToFocusEnabled = false;

function onScreenClick(e) {
  const wrap = document.getElementById('screen-wrap');
  const rect = wrap.getBoundingClientRect();
  const x = ((e.clientX - rect.left) / rect.width) * 1024;
  const y = ((e.clientY - rect.top) / rect.height) * 540;

  if (clickCanvasToFocusEnabled) {
    const tx = Math.max(0, Math.min(959, Math.round(((e.clientX - rect.left) / rect.width) * 960)));
    const ty = Math.max(0, Math.min(539, Math.round(((e.clientY - rect.top) / rect.height) * 540)));
    const curAf = (currentStatus && currentStatus.touch_focus_ciz && currentStatus.touch_focus_ciz.touch_af_mode) || 'off';
    const nextAf = (curAf === 'off') ? 'touch_tracking' : curAf;
    setTouchFocusCiz({touch_af_mode: nextAf, touch_x: tx, touch_y: ty});
    return;
  }

  const page = currentStatus ? currentStatus.page : 0;

  // Top-left Menu button hotspot on FX6 screen
  if (x < 220 && y < 72) {
    sendKey('MENU');
    return;
  }

  if (page === 0 || page === 3) {
    // 6 outer cells on Big-6 Home / Setting Center
    let row = (y < 295) ? 0 : 1;
    let col = (x < 340) ? 0 : (x < 684 ? 1 : 2);
    let idx = row * 3 + col;
    if (currentStatus && currentStatus.sel_box === idx) {
      sendKey('SET');
    } else {
      sendPayload({sel_box: idx});
    }
    return;
  }

  if (page === 1) {
    // Three-Layer Menu: left column categories [62..556, 56..518], right column [568..950]
    if (x >= 50 && x < 556 && y >= 56 && y < 518) {
      const row = Math.floor((y - 56) / (462 / 9));
      const winStart = (currentStatus && currentStatus.menu_cat >= 9) ? 2 : 0;
      const cat = Math.min(10, Math.max(0, winStart + row));
      sendPayload({page: 1, menu_cat: cat, menu_item: 0, menu_depth: 0});
    } else if (x >= 568 && y >= 105 && y < 155) {
      sendKey('BACK');
    } else if (x >= 568 && y >= 156) {
      const item = Math.max(0, Math.min(6, Math.floor((y - 156) / 51)));
      if (currentStatus && currentStatus.menu_depth >= 1 && currentStatus.menu_item === item) {
        sendKey('SET');
      } else {
        sendPayload({page: 1, menu_item: item, menu_depth: Math.max(1, currentStatus ? currentStatus.menu_depth : 1)});
      }
    }
  }
}

async function refreshGpe0() {
  const r = await fetch('/api/refresh', {method: 'POST'});
  const data = await r.json();
  await updateUI(data.status, true);
}

async function restartVm() {
  await fetch('/api/stop', {method: 'POST'});
  const r = await fetch('/api/start', {method: 'POST'});
  await r.json();
  await pollStatus();
}

async function pollStatus() {
  try {
    const r = await fetch('/api/status');
    const st = await r.json();
    await updateUI(st, false);
  } catch (e) {}
}

window.addEventListener('keydown', (e) => {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') return;
  const map = {
    ArrowUp: 'UP',
    ArrowDown: 'DOWN',
    ArrowLeft: 'LEFT',
    ArrowRight: 'RIGHT',
    Enter: 'SET',
    Backspace: 'BACK',
    Escape: 'BACK',
    m: 'MENU',
    M: 'MENU',
    h: 'HOME',
    H: 'HOME',
    d: 'DISP',
    D: 'DISP',
    f: 'HOME',
    F: 'HOME',
    '1': 'SET',
    '2': 'BACK',
    '3': 'DISP',
  };
  if (e.key === 'p' || e.key === 'P') {
    e.preventDefault();
    setPage(14);
    return;
  }
  if (e.key === 'u' || e.key === 'U') {
    e.preventDefault();
    setCat(0);
    return;
  }
  if (map[e.key]) {
    e.preventDefault();
    sendKey(map[e.key]);
  }
});

let menuCatalogData = null;

async function loadMenuCatalog() {
  try {
    const r = await fetch('/api/menu_catalog');
    menuCatalogData = await r.json();
    const sel = document.getElementById('menu-cat-filter');
    if (sel && menuCatalogData.categories) {
      menuCatalogData.categories.forEach((c) => {
        const opt = document.createElement('option');
        opt.value = c.category;
        opt.textContent = `${c.cat_idx + 1}. ${c.category} (${c.category_zh})`;
        sel.appendChild(opt);
      });
    }
    const pillsEl = document.getElementById('quick-jump-pills');
    if (pillsEl && menuCatalogData.quick_jump_pills) {
      pillsEl.innerHTML = '';
      menuCatalogData.quick_jump_pills.forEach((p) => {
        const btn = document.createElement('button');
        btn.textContent = p.en_title.split('->')[0].trim();
        btn.title = `${p.zh_title} | ${p.fx3_bridge_note}`;
        btn.onclick = () => jumpToPageId(p.page_id);
        pillsEl.appendChild(btn);
      });
    }
    filterMenuCatalog();
  } catch (e) {}
}

function filterMenuCatalog() {
  if (!menuCatalogData || !menuCatalogData.items) return;
  const qEl = document.getElementById('menu-search-input');
  const cEl = document.getElementById('menu-cat-filter');
  const listEl = document.getElementById('menu-search-results');
  const cntEl = document.getElementById('menu-catalog-count');
  if (!listEl) return;
  const q = (qEl ? qEl.value : '').trim().toLowerCase();
  const cat = (cEl ? cEl.value : '').trim().toLowerCase();
  const tokens = q ? q.split(/\s+/).filter(Boolean) : [];
  const filtered = menuCatalogData.items.filter((it) => {
    if (cat && (it.category || '').toLowerCase() !== cat) return false;
    if (!tokens.length) return true;
    const hay = [
      it.page_id, it.zh_title, it.en_title, it.category, it.category_zh,
      it.fx3_bridge_note, it.first_name || '', it.off_hex || '',
      ...(it.keywords || [])
    ].join(' ').toLowerCase();
    return tokens.every((t) => hay.includes(t));
  });
  if (cntEl) {
    cntEl.textContent = `${filtered.length} / ${menuCatalogData.total_entries} matches (${menuCatalogData.total_categories} cats · ${menuCatalogData.total_pages_128} pages)`;
  }
  const shown = filtered.slice(0, q || cat ? 24 : 12);
  listEl.innerHTML = '';
  shown.forEach((it) => {
    const row = document.createElement('div');
    row.className = 'search-item';
    const info = document.createElement('div');
    info.style.cssText = 'flex:1;min-width:0;';
    const title = document.createElement('div');
    title.style.cssText = 'font-weight:600;color:#f8fafc;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;';
    title.textContent = `[${it.category}] ${it.zh_title} — ${it.en_title}`;
    const note = document.createElement('div');
    note.style.cssText = 'font-size:10.5px;color:#9ca3af;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;';
    note.textContent = `${it.page_id} · ${it.fx3_bridge_note}`;
    info.appendChild(title);
    info.appendChild(note);
    const btn = document.createElement('button');
    btn.textContent = 'Jump';
    btn.style.cssText = 'padding:4px 10px;font-size:11px;background:#0f2b46;border-color:#22d3ee;';
    btn.onclick = () => jumpToPageId(it.page_id);
    row.appendChild(info);
    row.appendChild(btn);
    listEl.appendChild(row);
  });
}

async function jumpToPageId(pageId) {
  if (busy) return;
  busy = true;
  const toast = document.getElementById('render-toast');
  toast.style.display = 'block';
  try {
    const r = await fetch('/api/jump_page', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({page_id: pageId})
    });
    const data = await r.json();
    if (data.status) await updateUI(data.status, true);
  } finally {
    toast.style.display = 'none';
    busy = false;
  }
}

async function verifyMultilangDiff() {
  if (busy) return;
  busy = true;
  const toast = document.getElementById('render-toast');
  const box = document.getElementById('multilang-diff-readout');
  toast.style.display = 'block';
  if (box) {
    box.style.display = 'block';
    box.textContent = 'Running in-guest EN -> ZH -> JA GPE0 diff verification...';
  }
  try {
    const r = await fetch('/api/verify_multilang_diff', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({})
    });
    const data = await r.json();
    if (box) {
      if (data.ok && data.captures) {
        box.style.borderColor = '#10b981';
        box.style.color = '#a7f3d0';
        box.textContent =
          `VERIFIED EN->ZH->JA (restored=${data.restored_lang}, ack_seq=${data.ack_seqs.join('->')}->${data.ack_seq_end}) | ` +
          `EN<>ZH=${data.en_vs_zh_diff_bytes}B (${data.en_vs_zh_diff_pixels}px) | ` +
          `ZH<>JA=${data.zh_vs_ja_diff_bytes}B (${data.zh_vs_ja_diff_pixels}px) | ` +
          `SHA[en=${data.captures.en.sha256.slice(0,10)}, zh=${data.captures.zh.sha256.slice(0,10)}, ja=${data.captures.ja.sha256.slice(0,10)}]`;
      } else {
        box.style.borderColor = '#f59e0b';
        box.style.color = '#fde68a';
        box.textContent = `Multilang Diff (${data.error || 'err'}): ${data.message || ''}`;
      }
    }
    if (data.status) await updateUI(data.status, true);
  } finally {
    toast.style.display = 'none';
    busy = false;
  }
}

let desqueezePreviewEnabled = true;
let scopeLoadedOnce = false;

function applyDesqueezePreview(desq) {
  const wrap = document.getElementById('screen-wrap');
  const img = document.getElementById('gpe0-img');
  const btn = document.getElementById('btn-desqueeze-preview');
  const label = desq || '1.0x';
  if (btn) {
    btn.textContent = desqueezePreviewEnabled
      ? `Anamorphic CSS Preview: ON (${label})`
      : `Anamorphic CSS Preview: OFF (${label})`;
  }
  if (!wrap || !img) return;
  const num = parseFloat(String(label).replace('x', '')) || 1.0;
  if (!desqueezePreviewEnabled || num <= 1.01) {
    wrap.style.aspectRatio = '1024 / 540';
    img.style.objectFit = 'fill';
  } else {
    const w = Math.round(1024 * num);
    wrap.style.aspectRatio = `${w} / 540`;
    img.style.objectFit = 'fill';
  }
}

function toggleDesqueezePreview() {
  desqueezePreviewEnabled = !desqueezePreviewEnabled;
  const cur =
    (currentStatus && currentStatus.gyroflow_anamorphic && currentStatus.gyroflow_anamorphic.squeeze_display) ||
    (currentStatus && currentStatus.assist_tools && currentStatus.assist_tools.desqueeze) ||
    '1.0x';
  applyDesqueezePreview(cur);
}

async function setAssistTools(patch) {
  if (busy) return;
  busy = true;
  const toast = document.getElementById('render-toast');
  toast.style.display = 'block';
  try {
    const r = await fetch('/api/assist_tools', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(patch)
    });
    const data = await r.json();
    if (data.status) await updateUI(data.status, true);
    await refreshScopeStats(false);
  } finally {
    toast.style.display = 'none';
    busy = false;
  }
}

const P64_EI_STEPS = {
  '800': [200, 250, 320, 400, 500, 640, 800, 1000, 1250, 1600, 2000, 2500, 3200],
  '12800': [3200, 4000, 5000, 6400, 8000, 10000, 12800, 16000, 20000, 25600, 32000, 40000, 51200]
};

function syncCineExposureUI(ce) {
  if (!ce) return;
  const recBtn = document.getElementById('p64-rec-btn');
  const isRec = ce.rec_state === 'REC';
  if (recBtn) {
    recBtn.textContent = isRec ? '■ REC -> STBY' : '● STBY -> REC';
    recBtn.style.background = isRec ? '#991b1b' : '#064e3b';
    recBtn.style.borderColor = isRec ? '#ef4444' : '#10b981';
  }
  const tcEl = document.getElementById('p64-tc-readout');
  if (tcEl) tcEl.textContent = ce.rec_tc || '00:00:00:00';
  const tf = document.getElementById('p64-tally-front');
  const tr = document.getElementById('p64-tally-rear');
  if (tf) tf.style.background = ce.tally_front_lit ? '#ef4444' : '#374151';
  if (tr) tr.style.background = ce.tally_rear_lit ? '#f97316' : '#374151';
  const tlSel = document.getElementById('p64-tally-select');
  if (tlSel && document.activeElement !== tlSel) tlSel.value = ce.tally_lamp_mode || 'on';

  const baseSel = document.getElementById('p64-ei-base-select');
  const baseStr = String(ce.cine_ei_base || '800');
  if (baseSel && document.activeElement !== baseSel) baseSel.value = baseStr;
  const eiSel = document.getElementById('p64-ei-index-select');
  if (eiSel && document.activeElement !== eiSel) {
    const steps = P64_EI_STEPS[baseStr] || P64_EI_STEPS['800'];
    const curEi = Number(ce.ei_index || 800);
    if (eiSel.options.length !== steps.length || Number(eiSel.options[0].value) !== steps[0]) {
      eiSel.innerHTML = '';
      steps.forEach((v) => {
        const opt = document.createElement('option');
        opt.value = String(v);
        opt.textContent = `${v} EI`;
        eiSel.appendChild(opt);
      });
    }
    eiSel.value = String(curEi);
  }
  const latEl = document.getElementById('p64-lat-readout');
  if (latEl) latEl.textContent = ce.latitude_label || '+6 / -8';
  const overBar = document.getElementById('p64-lat-over-bar');
  const underBar = document.getElementById('p64-lat-under-bar');
  if (overBar && underBar && ce.over_stops !== undefined) {
    const overPct = Math.round((Number(ce.over_stops) / 14.0) * 100);
    overBar.style.width = `${overPct}%`;
    underBar.style.width = `${100 - overPct}%`;
  }

  const shRo = document.getElementById('p64-shutter-readout');
  if (shRo) shRo.textContent = ce.shutter_display || '180.0°';
  const smSel = document.getElementById('p64-shutter-mode-select');
  if (smSel && document.activeElement !== smSel) smSel.value = ce.shutter_mode || 'angle';
  const svIn = document.getElementById('p64-shutter-val-input');
  if (svIn && document.activeElement !== svIn) {
    if (ce.shutter_mode === 'speed') svIn.value = String(ce.shutter_speed_denom || 48);
    else if (ce.shutter_mode === 'ecs') svIn.value = String(ce.ecs_freq_hz || 60.0);
    else svIn.value = String(ce.shutter_angle_deg || 180.0);
  }

  const sqBtn = document.getElementById('p64-sq-btn');
  if (sqBtn) {
    sqBtn.textContent = ce.sq_enabled ? `S&Q: ON (${ce.motion_label || ''})` : 'S&Q: OFF';
    sqBtn.style.background = ce.sq_enabled ? '#78350f' : '';
    sqBtn.style.borderColor = ce.sq_enabled ? '#f59e0b' : '';
  }
  const sqMute = document.getElementById('p64-sq-mute-badge');
  if (sqMute) {
    sqMute.textContent = ce.audio_rec_muted_by_sq ? '[CH1-4 MUTE by S&Q]' : 'Audio Active';
    sqMute.style.color = ce.audio_rec_muted_by_sq ? '#fbbf24' : '#94a3b8';
  }
  const bfSel = document.getElementById('p64-base-fps-select');
  if (bfSel && document.activeElement !== bfSel) bfSel.value = String(ce.base_fps || 23.98);
  const sfIn = document.getElementById('p64-sq-fps-input');
  if (sfIn && document.activeElement !== sfIn) sfIn.value = String(ce.sq_fps || 24);
  const ioSel = document.getElementById('p64-wired-io-select');
  if (ioSel && document.activeElement !== ioSel) ioSel.value = ce.wired_io_mode || 'off';
  const cmdEl = document.getElementById('p64-cmd-readout');
  if (cmdEl) cmdEl.textContent = ce.cine_exp_cmd || '';
}

async function setCineExposure(patch) {
  if (busy) return;
  busy = true;
  const toast = document.getElementById('render-toast');
  const errEl = document.getElementById('p64-error-banner');
  toast.style.display = 'block';
  try {
    const r = await fetch('/api/cine_exposure', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(patch)
    });
    const data = await r.json();
    if (!data.ok) {
      if (errEl) {
        errEl.style.display = 'block';
        errEl.textContent = data.message || data.error || 'Invalid cine_exposure parameter';
      }
    } else if (errEl) {
      errEl.style.display = 'none';
    }
    if (data.status) await updateUI(data.status, true);
  } finally {
    toast.style.display = 'none';
    busy = false;
  }
}

function toggleCineRec() {
  const cur = (currentStatus && currentStatus.cine_exposure && currentStatus.cine_exposure.rec_state) || 'STBY';
  setCineExposure({rec_state: cur === 'REC' ? 'STBY' : 'REC'});
}

function toggleCineSq() {
  const cur = !!(currentStatus && currentStatus.cine_exposure && currentStatus.cine_exposure.sq_enabled);
  setCineExposure({sq_enabled: !cur});
}

function applyPhase64ShutterVal() {
  const mode = (document.getElementById('p64-shutter-mode-select') || {}).value || 'angle';
  const val = Number((document.getElementById('p64-shutter-val-input') || {}).value);
  if (mode === 'speed') setCineExposure({shutter_mode: 'speed', shutter_speed_denom: val});
  else if (mode === 'ecs') setCineExposure({shutter_mode: 'ecs', ecs_freq_hz: val});
  else setCineExposure({shutter_mode: 'angle', shutter_angle_deg: val});
}

function syncColorAndMediaUI(cm) {
  if (!cm) return;
  const wbRead = document.getElementById('p73-wb-readout');
  if (wbRead) wbRead.textContent = (cm.wb_display || (cm.kelvin + 'K')) + ' [' + (cm.wb_mode || 'preset_5600k') + ']';
  const wbSel = document.getElementById('p73-wb-mode-select');
  if (wbSel && cm.wb_mode && document.activeElement !== wbSel) wbSel.value = cm.wb_mode;
  const kInp = document.getElementById('p73-kelvin-input');
  if (kInp && cm.kelvin !== undefined && document.activeElement !== kInp) {
    kInp.value = String(cm.kelvin);
    kInp.disabled = !!cm.kelvin_locked;
  }
  const tInp = document.getElementById('p73-tint-input');
  if (tInp && cm.tint_gm !== undefined && document.activeElement !== tInp) tInp.value = String(cm.tint_gm);
  const slSel = document.getElementById('p73-shockless-select');
  if (slSel && cm.shockless_wb && document.activeElement !== slSel) slSel.value = cm.shockless_wb;

  const lookSel = document.getElementById('p73-base-look-select');
  if (lookSel && cm.base_look && document.activeElement !== lookSel) lookSel.value = cm.base_look;
  const nleEl = document.getElementById('p73-nle-tags');
  if (nleEl) nleEl.textContent = (cm.capture_gamma_equation || '-') + ' / ' + (cm.capture_color_primaries || '-');
  const lutEl = document.getElementById('p73-active-lut-readout');
  if (lutEl) {
    const lutName = cm.active_user_lut && cm.active_user_lut.name;
    lutEl.textContent = lutName ? (cm.active_user_lut_slot + ': ' + lutName) : (cm.base_look || '-');
  }

  const slotRead = document.getElementById('p73-slot-readout');
  if (slotRead) slotRead.textContent = (cm.dual_slot_mode || 'simul');
  const camInp = document.getElementById('p73-cam-id-input');
  if (camInp && cm.cam_id && document.activeElement !== camInp) camInp.value = cm.cam_id;
  const reelInp = document.getElementById('p73-reel-input');
  if (reelInp && cm.reel_num !== undefined && document.activeElement !== reelInp) reelInp.value = String(cm.reel_num);
  const posSel = document.getElementById('p73-pos-select');
  if (posSel && cm.cam_pos && document.activeElement !== posSel) posSel.value = cm.cam_pos;
  const seqInp = document.getElementById('p73-clip-seq-input');
  if (seqInp && cm.clip_seq !== undefined && document.activeElement !== seqInp) seqInp.value = String(cm.clip_seq);
  const dsSel = document.getElementById('p73-dualslot-select');
  if (dsSel && cm.dual_slot_mode && document.activeElement !== dsSel) dsSel.value = cm.dual_slot_mode;
  const prxSel = document.getElementById('p73-proxy-select');
  if (prxSel && cm.proxy_mode && document.activeElement !== prxSel) prxSel.value = cm.proxy_mode;

  const prxBadge = document.getElementById('p73-sq-proxy-badge');
  if (prxBadge) {
    if (cm.proxy_auto_suspended_by_sq) {
      prxBadge.textContent = 'Proxy Auto-Suspended (S&Q Active)';
      prxBadge.style.background = '#78350f';
      prxBadge.style.borderColor = '#f59e0b';
      prxBadge.style.color = '#fde68a';
    } else if (cm.proxy_effective_active) {
      prxBadge.textContent = 'Proxy Active (' + (cm.proxy_mode || '') + ')';
      prxBadge.style.background = '#064e3b';
      prxBadge.style.borderColor = '#10b981';
      prxBadge.style.color = '#a7f3d0';
    } else {
      prxBadge.textContent = 'Proxy Off';
      prxBadge.style.background = '#1f2937';
      prxBadge.style.borderColor = '#4b5563';
      prxBadge.style.color = '#d1d5db';
    }
  }
  const clipRead = document.getElementById('p73-clip-readout');
  if (clipRead) clipRead.textContent = (cm.main_clip_name || '') + ' (' + (cm.sidecar_xml_name || '') + ')';
  const prxPathRead = document.getElementById('p73-proxy-path-readout');
  if (prxPathRead) {
    prxPathRead.textContent = cm.proxy_active_clip_name ? ('SUB: ' + cm.proxy_active_clip_name) : 'SUB: OFF';
  }
  const cmdEl = document.getElementById('p73-cmd-readout');
  if (cmdEl) cmdEl.textContent = cm.wb_media_cmd || 'WB_MEDIA ...';
}

async function setColorAndMedia(patch) {
  if (busy) return;
  busy = true;
  const toast = document.getElementById('render-toast');
  const errEl = document.getElementById('p73-error-banner');
  toast.style.display = 'block';
  try {
    const r = await fetch('/api/color_and_media', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(patch || {})
    });
    const data = await r.json();
    if (!data.ok) {
      if (errEl) {
        errEl.style.display = 'block';
        errEl.textContent = data.message || data.error || 'Invalid color_and_media parameter';
      }
    } else if (errEl) {
      errEl.style.display = 'none';
    }
    if (data.status) await updateUI(data.status, true);
  } finally {
    toast.style.display = 'none';
    busy = false;
  }
}

function applyPhase73WbKelvinTint() {
  const wbMode = (document.getElementById('p73-wb-mode-select') || {}).value || 'preset_5600k';
  const kInp = document.getElementById('p73-kelvin-input');
  const tInp = document.getElementById('p73-tint-input');
  const slSel = document.getElementById('p73-shockless-select');
  const patch = {
    tint_gm: Number((tInp || {}).value || 0),
    shockless_wb: (slSel || {}).value || 'off'
  };
  if (wbMode === 'mem_a' || wbMode === 'mem_b' || wbMode === 'atw') {
    patch.wb_mode = wbMode;
    patch.kelvin = Number((kInp || {}).value || 5600);
  } else {
    patch.wb_mode = wbMode;
  }
  setColorAndMedia(patch);
}

function applyPhase73MediaNaming() {
  const camId = String((document.getElementById('p73-cam-id-input') || {}).value || 'A').trim().toUpperCase();
  const reelNum = Number((document.getElementById('p73-reel-input') || {}).value || 1);
  const camPos = (document.getElementById('p73-pos-select') || {}).value || 'C';
  const clipSeq = Number((document.getElementById('p73-clip-seq-input') || {}).value || 1);
  const dualSlot = (document.getElementById('p73-dualslot-select') || {}).value || 'simul';
  const proxyMode = (document.getElementById('p73-proxy-select') || {}).value || 'xavc_hs_1080p_16m';
  setColorAndMedia({
    cam_id: camId,
    reel_num: reelNum,
    cam_pos: camPos,
    clip_seq: clipSeq,
    dual_slot_mode: dualSlot,
    proxy_mode: proxyMode
  });
}

async function refreshXmlSidecarPreview() {
  const pre = document.getElementById('p73-xml-preview');
  try {
    const r = await fetch('/api/xml_sidecar?format=json');
    const data = await r.json();
    if (pre && data && data.xml) {
      pre.textContent = data.xml;
    }
  } catch (e) {
    if (pre) pre.textContent = 'XML sidecar preview error: ' + String(e);
  }
}

async function downloadXmlSidecar() {
  await refreshXmlSidecarPreview();
  const r = await fetch('/api/xml_sidecar?format=json');
  const data = await r.json();
  const fname = (data && data.filename) ? data.filename : 'A001C001_261114_FX3BM01.XML';
  const a = document.createElement('a');
  a.href = '/api/xml_sidecar?t=' + Date.now();
  a.download = fname;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

function drawWaveformCanvas(scope) {
  const cvs = document.getElementById('scope-waveform-canvas');
  if (!cvs || !scope || !scope.waveform) return;
  const ctx = cvs.getContext('2d');
  const w = cvs.width, h = cvs.height;
  ctx.fillStyle = '#07090c';
  ctx.fillRect(0, 0, w, h);
  const graticules = [
    {ire: 109, label: '109', col: '#334155'},
    {ire: 94,  label: '94',  col: '#78350f'},
    {ire: 70,  label: '70',  col: '#1e3a5f'},
    {ire: 50,  label: '50',  col: '#1f2937'},
    {ire: 0,   label: '0',   col: '#334155'}
  ];
  ctx.font = '9px Menlo, monospace';
  graticules.forEach((g) => {
    const y = h - 6 - ((g.ire / 109.0) * (h - 14));
    ctx.strokeStyle = g.col;
    ctx.beginPath();
    ctx.moveTo(22, y);
    ctx.lineTo(w - 4, y);
    ctx.stroke();
    ctx.fillStyle = '#64748b';
    ctx.fillText(g.label, 2, y + 3);
  });
  const cols = scope.waveform;
  const cw = (w - 28) / Math.max(1, cols.length);
  cols.forEach((c, idx) => {
    const x = 24 + idx * cw;
    const yMin = h - 6 - ((c.min_ire / 109.0) * (h - 14));
    const yMax = h - 6 - ((c.max_ire / 109.0) * (h - 14));
    const yAvg = h - 6 - ((c.avg_ire / 109.0) * (h - 14));
    ctx.fillStyle = 'rgba(34, 211, 238, 0.35)';
    ctx.fillRect(x, yMax, Math.max(2, cw - 2), Math.max(2, yMin - yMax));
    ctx.fillStyle = c.max_ire >= 94 ? '#f59e0b' : '#22d3ee';
    ctx.fillRect(x, yMax - 1, Math.max(2, cw - 2), 2);
    ctx.fillStyle = '#10b981';
    ctx.fillRect(x, yAvg - 1, Math.max(2, cw - 2), 2);
  });
}

function drawHistogramCanvas(scope) {
  const cvs = document.getElementById('scope-hist-canvas');
  if (!cvs || !scope || !scope.histograms) return;
  const ctx = cvs.getContext('2d');
  const w = cvs.width, h = cvs.height;
  ctx.fillStyle = '#07090c';
  ctx.fillRect(0, 0, w, h);
  const channels = [
    {key: 'r',    col: 'rgba(239, 68, 68, 0.55)'},
    {key: 'g',    col: 'rgba(16, 185, 129, 0.50)'},
    {key: 'b',    col: 'rgba(59, 130, 246, 0.55)'},
    {key: 'luma', col: 'rgba(248, 250, 252, 0.70)'}
  ];
  let maxBin = 1;
  channels.forEach((ch) => {
    const arr = scope.histograms[ch.key] || [];
    for (let i = 1; i < arr.length; i++) {
      if (arr[i] > maxBin) maxBin = arr[i];
    }
  });
  const bw = (w - 16) / 16;
  channels.forEach((ch, cIdx) => {
    const arr = scope.histograms[ch.key] || [];
    ctx.fillStyle = ch.col;
    for (let i = 0; i < arr.length; i++) {
      const val = i === 0 ? Math.min(arr[i], maxBin) : arr[i];
      const bh = Math.max(1, (val / maxBin) * (h - 18));
      const x = 8 + i * bw + (cIdx * (bw * 0.18));
      ctx.fillRect(x, h - 6 - bh, Math.max(2, bw * 0.42), bh);
    }
  });
  ctx.fillStyle = '#94a3b8';
  ctx.font = '9px Menlo, monospace';
  ctx.fillText('16-Bin R/G/B/Luma Histogram', 8, 11);
}

async function refreshScopeStats(forceRefresh) {
  try {
    const url = forceRefresh ? '/api/scope_stats?refresh=1' : '/api/scope_stats';
    const r = await fetch(url);
    const scope = await r.json();
    if (!scope || !scope.ok) return;
    scopeLoadedOnce = true;
    drawWaveformCanvas(scope);
    drawHistogramCanvas(scope);
    const ro = document.getElementById('scope-stats-readout');
    if (ro) {
      const peakIre = Math.max(...(scope.waveform || []).map((c) => c.max_ire || 0), 0);
      ro.textContent =
        `NZ=${(scope.nonzero_ratio * 100).toFixed(1)}% | HI=${scope.highlight_pixels}px | ` +
        `AMB=${scope.amber_pixels}px | Peak=${peakIre.toFixed(1)} IRE | ${scope.source || 'gpe0'}`;
    }
  } catch (e) {}
}

function toggleClickCanvasToFocus() {
  clickCanvasToFocusEnabled = !clickCanvasToFocusEnabled;
  const btn = document.getElementById('p81-click-toggle-btn');
  const wrap = document.getElementById('screen-wrap');
  if (btn) {
    btn.textContent = clickCanvasToFocusEnabled
      ? '🎯 点击画面触控对焦: ON (Click-Canvas-to-Focus)'
      : '🎯 点击画面触控对焦: OFF (Click-Canvas-to-Focus)';
    btn.style.background = clickCanvasToFocusEnabled ? '#052e16' : '#0f2b46';
    btn.style.borderColor = clickCanvasToFocusEnabled ? '#22c55e' : '#22d3ee';
  }
  if (wrap) {
    wrap.style.cursor = clickCanvasToFocusEnabled ? 'crosshair' : 'pointer';
  }
}

function syncTouchFocusCizUI(tfc) {
  if (!tfc) return;
  const afEl = document.getElementById('p81-af-readout');
  if (afEl) afEl.textContent = tfc.touch_af_mode || 'off';
  const afSel = document.getElementById('p81-af-mode-select');
  if (afSel && tfc.touch_af_mode && document.activeElement !== afSel) afSel.value = tfc.touch_af_mode;
  const txIn = document.getElementById('p81-touch-x-input');
  if (txIn && tfc.touch_x !== undefined && document.activeElement !== txIn) txIn.value = String(tfc.touch_x);
  const tyIn = document.getElementById('p81-touch-y-input');
  if (tyIn && tfc.touch_y !== undefined && document.activeElement !== tyIn) tyIn.value = String(tfc.touch_y);

  const pdafBadge = document.getElementById('p81-pdaf-badge');
  if (pdafBadge) pdafBadge.textContent = `PDAF 33x19 #${tfc.pdaf_index} (${tfc.pdaf_col},${tfc.pdaf_row})`;
  const pdafRo = document.getElementById('p81-pdaf-readout');
  if (pdafRo) pdafRo.textContent = `col=${tfc.pdaf_col}, row=${tfc.pdaf_row}, idx=${tfc.pdaf_index}`;

  const magEl = document.getElementById('p81-mag-readout');
  if (magEl) magEl.textContent = tfc.focus_mag || '1.0x';
  const magSel = document.getElementById('p81-mag-select');
  if (magSel && tfc.focus_mag && document.activeElement !== magSel) magSel.value = tfc.focus_mag;
  const roi = tfc.focus_mag_roi || {w: 960, h: 540};
  const roiRo = document.getElementById('p81-mag-roi-readout');
  if (roiRo) {
    roiRo.innerHTML = `ROI: ${roi.w}x${roi.h} @ (${tfc.touch_x},${tfc.touch_y})<br/>HDMI Clean Feed: 1.0x Unmagnified`;
  }
  const hdmiBadge = document.getElementById('p81-clean-hdmi-badge');
  if (hdmiBadge) {
    hdmiBadge.textContent = tfc.focus_mag && tfc.focus_mag !== '1.0x'
      ? `Preview ${tfc.focus_mag} · HDMI Clean 1.0x`
      : 'HDMI Clean: 1.0x';
  }

  const fcEl = document.getElementById('p81-fc-readout');
  if (fcEl) fcEl.textContent = tfc.false_color_mode || 'off';
  const fcSel = document.getElementById('p81-fc-select');
  if (fcSel && tfc.false_color_mode && document.activeElement !== fcSel) fcSel.value = tfc.false_color_mode;

  const cizEff = Number(tfc.effective_ciz_scale || 1.0).toFixed(2);
  const cizEl = document.getElementById('p81-ciz-eff-readout');
  if (cizEl) cizEl.textContent = `${cizEff}x (${tfc.ciz_res_mode || '4K'})`;
  const resSel = document.getElementById('p81-ciz-res-select');
  if (resSel && tfc.ciz_res_mode && document.activeElement !== resSel) resSel.value = tfc.ciz_res_mode;
  const spdSel = document.getElementById('p81-rocker-speed-select');
  if (spdSel && tfc.zoom_rocker_speed !== undefined && document.activeElement !== spdSel) {
    spdSel.value = String(tfc.zoom_rocker_speed);
  }
  const cizIn = document.getElementById('p81-ciz-scale-input');
  if (cizIn && tfc.ciz_scale !== undefined && document.activeElement !== cizIn) {
    cizIn.value = Number(tfc.ciz_scale).toFixed(2);
  }

  const zebWarn = document.getElementById('p81-zebra100-warn');
  if (zebWarn) {
    if (tfc.slog3_zebra100_clip_warning) {
      zebWarn.style.display = 'block';
      zebWarn.textContent = tfc.slog3_zebra100_warning_message || 'Warning: S-Log3 clips at 94% IRE vs Zebra 100%';
    } else {
      zebWarn.style.display = 'none';
    }
  }
  const exclWarn = document.getElementById('p81-ciz-excl-warn');
  if (exclWarn) {
    if (tfc.ciz_clamped_by_exclusion) {
      exclWarn.style.display = 'block';
      exclWarn.textContent = 'CIZ Auto-Clamped to 1.00x: ' + (tfc.ciz_exclusion_reason || 'Mutual Exclusion');
    } else {
      exclWarn.style.display = 'none';
    }
  }
  const lbWarn = document.getElementById('p81-letterbox-warn');
  if (lbWarn) {
    if (tfc.letterbox_ignored) {
      lbWarn.style.display = 'block';
      lbWarn.textContent = 'Letterbox / Matte Bar Click Ignored: AF lock preserved inside active sensor area.';
    } else {
      lbWarn.style.display = 'none';
    }
  }

  const reticle = document.getElementById('p81-canvas-reticle');
  if (reticle) {
    if (tfc.touch_af_mode && tfc.touch_af_mode !== 'off') {
      reticle.style.display = 'block';
      reticle.style.left = `${(Number(tfc.touch_x) / 960.0) * 100.0}%`;
      reticle.style.top = `${(Number(tfc.touch_y) / 540.0) * 100.0}%`;
      reticle.style.borderColor = tfc.touch_af_mode === 'touch_tracking' ? '#22c55e' : '#f8fafc';
    } else {
      reticle.style.display = 'none';
    }
  }

  const cmdEl = document.getElementById('p81-cmd-readout');
  if (cmdEl) cmdEl.textContent = tfc.touch_af_ciz_cmd || 'TOUCH_CIZ ...';
}

async function setTouchFocusCiz(patch) {
  if (busy) return;
  busy = true;
  const toast = document.getElementById('render-toast');
  const errEl = document.getElementById('p81-error-banner');
  toast.style.display = 'block';
  try {
    const r = await fetch('/api/touch_focus_ciz', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(patch || {})
    });
    const data = await r.json();
    if (!data.ok) {
      if (errEl) {
        errEl.style.display = 'block';
        errEl.textContent = data.message || data.error || 'Invalid touch_focus_ciz parameter';
      }
    } else if (errEl) {
      errEl.style.display = 'none';
    }
    if (data.status) await updateUI(data.status, true);
  } finally {
    toast.style.display = 'none';
    busy = false;
  }
}

function applyPhase81TouchCoords() {
  const tx = Number((document.getElementById('p81-touch-x-input') || {}).value || 480);
  const ty = Number((document.getElementById('p81-touch-y-input') || {}).value || 270);
  const curAf = (document.getElementById('p81-af-mode-select') || {}).value || 'touch_tracking';
  setTouchFocusCiz({
    touch_af_mode: curAf === 'off' ? 'touch_tracking' : curAf,
    touch_x: tx,
    touch_y: ty
  });
}

function applyPhase81CizScale() {
  const sc = Number((document.getElementById('p81-ciz-scale-input') || {}).value || 1.00);
  const res = (document.getElementById('p81-ciz-res-select') || {}).value || '4K';
  const spd = Number((document.getElementById('p81-rocker-speed-select') || {}).value || 4);
  setTouchFocusCiz({ciz_scale: sc, ciz_res_mode: res, zoom_rocker_speed: spd});
}

function syncShotmarkIrisUI(smi) {
  if (!smi) return;
  const smCntEl = document.getElementById('p88-sm-count-readout');
  if (smCntEl) smCntEl.textContent = `M1:${smi.shotmark1_count || 0} / M2:${smi.shotmark2_count || 0}`;
  const smLatEl = document.getElementById('p88-sm-latest-readout');
  if (smLatEl) {
    if (smi.latest_shotmark) {
      const lm = smi.latest_shotmark;
      smLatEl.textContent = `EssenceMark: ${lm.type} (${lm.label}) @ f=${lm.frame} [${lm.tc}] (${smi.shotmark_count}/${smi.shotmark_max_per_clip})`;
    } else {
      smLatEl.textContent = `EssenceMark: none (0/${smi.shotmark_max_per_clip || 64})`;
    }
  }
  const irisEl = document.getElementById('p88-iris-readout');
  if (irisEl) {
    irisEl.textContent = `${smi.iris_display || 'F2.8'} · ${Number(smi.target_ire || 41.0).toFixed(1)}%IRE`;
  }
  const meterSel = document.getElementById('p88-metering-select');
  if (meterSel && smi.metering_mode && document.activeElement !== meterSel) {
    meterSel.value = smi.metering_mode;
  }
  const evIn = document.getElementById('p88-ev-input');
  if (evIn && smi.last_scene_ev !== undefined && document.activeElement !== evIn) {
    evIn.value = Number(smi.last_scene_ev).toFixed(1);
  }
  const ireEstEl = document.getElementById('p88-ire-est-readout');
  if (ireEstEl) {
    ireEstEl.textContent = `Est Grey: ${Number(smi.estimated_grey_ire || 41.0).toFixed(1)}% | HL: ${Number(smi.estimated_highlight_ire || 89.0).toFixed(1)}% | ND Faults: ${smi.p4_nd_motor_faults || 0}`;
  }
  const padEl = document.getElementById('p88-pad-readout');
  if (padEl) {
    padEl.textContent = smi.ch34_safety_pad_db === -20 ? '-20 dB SAFE' : '0 dB';
  }
  const ubIn = document.getElementById('p88-ub-input');
  if (ubIn && smi.user_bits_hex && document.activeElement !== ubIn) {
    ubIn.value = smi.user_bits_hex;
  }
  const ubReadEl = document.getElementById('p88-ub-readout');
  if (ubReadEl) {
    ubReadEl.textContent = `UB: ${smi.user_bits_effective || 'A0:01:00:01'} (${smi.user_bits_mode || 'auto_camid_reel'})`;
  }
  const cmdEl = document.getElementById('p88-cmd-readout');
  if (cmdEl) cmdEl.textContent = smi.shotmark_iris_cmd || 'SMRK_IRIS ...';
}

async function setShotmarkAndIris(patch) {
  if (busy) return;
  busy = true;
  const toast = document.getElementById('render-toast');
  const errEl = document.getElementById('p88-error-banner');
  toast.style.display = 'block';
  try {
    const r = await fetch('/api/shotmark_and_iris', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(patch || {})
    });
    const data = await r.json();
    if (!data.ok) {
      if (errEl) {
        errEl.style.display = 'block';
        errEl.textContent = data.message || data.error || 'Invalid shotmark_and_iris parameter';
      }
    } else if (errEl) {
      errEl.style.display = 'none';
    }
    if (data.status) await updateUI(data.status, true);
  } finally {
    toast.style.display = 'none';
    busy = false;
  }
}

function applyPhase88PushAutoIris() {
  const ev = Number((document.getElementById('p88-ev-input') || {}).value || 12.0);
  const meter = (document.getElementById('p88-metering-select') || {}).value || 'multi';
  setShotmarkAndIris({action: 'push_auto_iris', scene_ev: ev, metering_mode: meter});
}

function applyPhase88UserBits() {
  const ub = ((document.getElementById('p88-ub-input') || {}).value || 'auto_camid_reel').trim();
  setShotmarkAndIris({user_bits_hex: ub || 'auto_camid_reel'});
}

async function importFx6FleetCamsetPreset() {
  if (busy) return;
  busy = true;
  const toast = document.getElementById('render-toast');
  const badge = document.getElementById('p88-fleet-badge');
  toast.style.display = 'block';
  try {
    const box = document.getElementById('camset-json-box');
    let payload = null;
    if (box && box.value.trim()) {
      try {
        const parsed = JSON.parse(box.value);
        if (parsed && (parsed.source_model === 'ILME-FX6' || parsed.sanitize_fx6_fleet === true || 'fx6_nd_preset' in parsed || 'sdi_12g_out' in parsed)) {
          payload = parsed;
        }
      } catch (_e) {}
    }
    if (!payload) {
      payload = {
        schema: 'ilme_fx6_camset_v1',
        source_model: 'ILME-FX6',
        sanitize_fx6_fleet: true,
        fx6_nd_preset: '1/16',
        sdi_12g_out: 'On',
        wifi_ap_enabled: true,
        vf_peaking: 'On',
        cinema_params: { fps: '23.98p', ei: '800 EI (800 Base)', shutter: '180.0°', nd: '1/16', wb: '5600K' }
      };
      if (box) box.value = JSON.stringify(payload, null, 2);
    }
    const r = await fetch('/api/camset_import', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload)
    });
    const data = await r.json();
    if (badge) {
      badge.textContent = data.ok ? `Clamped ${(data.sanitized_fx6_fields || []).length} FX6 keys` : (data.error || 'Error');
    }
    if (data.status) await updateUI(data.status, true);
  } finally {
    toast.style.display = 'none';
    busy = false;
  }
}

let p95Lang = 'zh-CN';
const P95_I18N = {
  'en': {
    title: 'Phase 95 · Anamorphic IBIS Arbitrator / Gyroflow 2000Hz RTMD / 1kHz -20dBFS Tone & -3dB Limiter',
    anamorphic: 'Anamorphic & IBIS Arbitrator',
    fallback: 'Fallback:',
    gyro: 'Gyroflow 2000Hz RTMD & Skew',
    syncAf: 'Sync Touch-AF X',
    tone: '1kHz -20dBFS Tone & SMPTE Bars',
    limiter: '4-Ch 24-bit -3.0dBFS Peak Limiter',
    reset: 'Reset P95',
    preset2x: '2.0x Active -> Anamorphic_Asymmetric (50% Yaw)',
    preset18x: '1.8x Active -> 0x0400 Center-Lock (Gyroflow)',
    presetTone: 'Calibrate: 1kHz -20dBFS + Bars + Limiter'
  },
  'zh-CN': {
    title: 'Phase 95 · 变形镜头 IBIS 仲裁 / Gyroflow 2000Hz RTMD / 1kHz -20dBFS 基准音与 -3dB 限幅器',
    anamorphic: '变形反挤压 & IBIS 仲裁器',
    fallback: '仲裁回退:',
    gyro: 'Gyroflow 2000Hz 陀螺仪 & 卷帘果冻',
    syncAf: '反挤压触控对焦 X',
    tone: '1kHz -20dBFS 测试音与彩条',
    limiter: '4路 24-bit -3.0dBFS 软拐点限幅器',
    reset: '重置 P95',
    preset2x: '2.0x Active -> 变形非对称水平减半',
    preset18x: '1.8x Active -> 0x0400 居中锁定 (Gyroflow)',
    presetTone: '校准: 1kHz -20dBFS + SMPTE 彩条 + 限幅'
  },
  'zh-TW': {
    title: 'Phase 95 · 變形鏡頭 IBIS 仲裁 / Gyroflow 2000Hz RTMD / 1kHz -20dBFS 基準音與 -3dB 限幅器',
    anamorphic: '變形反擠壓 & IBIS 仲裁器',
    fallback: '仲裁回退:',
    gyro: 'Gyroflow 2000Hz 陀螺儀 & 捲簾果凍',
    syncAf: '反擠壓觸控對焦 X',
    tone: '1kHz -20dBFS 測試音與彩條',
    limiter: '4路 24-bit -3.0dBFS 軟拐點限幅器',
    reset: '重置 P95',
    preset2x: '2.0x Active -> 變形非對稱水平減半',
    preset18x: '1.8x Active -> 0x0400 置中鎖定 (Gyroflow)',
    presetTone: '校準: 1kHz -20dBFS + SMPTE 彩條 + 限幅'
  },
  'ja': {
    title: 'Phase 95 · アナモルフィック IBIS 調停 / Gyroflow 2000Hz RTMD / 1kHz -20dBFS 基準音・-3dB リミッター',
    anamorphic: 'アナモルフィック & IBIS 調停',
    fallback: '調停先:',
    gyro: 'Gyroflow 2000Hz IMU & ローリング歪み',
    syncAf: '逆スクイーズ Touch-AF X',
    tone: '1kHz -20dBFS テストトーン & カラーバー',
    limiter: '4ch 24-bit -3.0dBFS リミッター',
    reset: 'P95 リセット',
    preset2x: '2.0x Active -> 非対称水平ゲイン (50% Yaw)',
    preset18x: '1.8x Active -> 0x0400 センターロック (Gyroflow)',
    presetTone: '校正: 1kHz -20dBFS + カラーバー + リミッター'
  }
};

function setP95Lang(lang) {
  if (!P95_I18N[lang]) return;
  p95Lang = lang;
  const d = P95_I18N[lang];
  const map = {
    'p95-card-title': d.title,
    'p95-lbl-anamorphic': d.anamorphic,
    'p95-lbl-fallback': d.fallback,
    'p95-lbl-gyro': d.gyro,
    'p95-btn-sync-af': d.syncAf,
    'p95-lbl-tone': d.tone,
    'p95-lbl-limiter': d.limiter,
    'p95-btn-reset': d.reset,
    'p95-preset-2x-asym': d.preset2x,
    'p95-preset-18x-ctrlock': d.preset18x,
    'p95-preset-tone-bars': d.presetTone
  };
  Object.keys(map).forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.textContent = map[id];
  });
  ['en', 'zh-CN', 'zh-TW', 'ja'].forEach((code) => {
    const b = document.getElementById('p95-lang-' + code);
    if (b) b.style.borderColor = (code === lang) ? '#22d3ee' : '#374151';
  });
}

function syncGyroflowAnamorphicUI(ga) {
  if (!ga) return;
  const sqSel = document.getElementById('p95-squeeze-select');
  const sqVal = Number(ga.squeeze_factor || 1.0);
  const sqOpt = Math.abs(sqVal - 1.33) < 0.005 ? '1.33' : sqVal.toFixed(1);
  if (sqSel && document.activeElement !== sqSel) sqSel.value = sqOpt;

  const ibisSel = document.getElementById('p95-ibis-select');
  if (ibisSel && ga.ibis_mode && document.activeElement !== ibisSel) ibisSel.value = ga.ibis_mode;

  const fbSel = document.getElementById('p95-fallback-select');
  if (fbSel && ga.anamorphic_fallback_mode && document.activeElement !== fbSel) {
    fbSel.value = ga.anamorphic_fallback_mode;
  }

  const sqRo = document.getElementById('p95-sq-readout');
  if (sqRo) {
    sqRo.textContent = `${ga.squeeze_display || '1.00x'} · ${ga.effective_ibis_mode || 'Standard'}`;
  }
  const yawRo = document.getElementById('p95-yaw-readout');
  if (yawRo) {
    yawRo.textContent =
      `Yaw Gain: ${Number(ga.horizontal_yaw_gain || 1.0).toFixed(4)} | ` +
      `Pitch: ${Number(ga.vertical_pitch_gain || 1.0).toFixed(4)} | ` +
      `Center-Lock: ${ga.center_lock_0x0400 ? '0x0400 ON' : 'OFF'}`;
  }

  const arbBanner = document.getElementById('p95-arbitration-banner');
  if (arbBanner) {
    if (ga.ibis_arbitrated) {
      arbBanner.style.display = 'block';
      arbBanner.textContent =
        `[Anamorphic IBIS Arbitrator] ${ga.arbitration_reason || 'Active IBIS arbitrated to prevent edge wobble'} ` +
        `(yaw=${Number(ga.horizontal_yaw_gain || 1.0).toFixed(4)})`;
    } else {
      arbBanner.style.display = 'none';
    }
  }

  const sqWarn = document.getElementById('p95-sq-warn-banner');
  if (sqWarn) {
    if (ga.rtmd_suspended_by_sq || ga.ref_tone_inhibited_by_rec) {
      sqWarn.style.display = 'block';
      const parts = [];
      if (ga.rtmd_suspended_by_sq) parts.push('S&Q VFR active: RTMD_SUSPENDED_BY_SQ (Gyroflow metadata paused)');
      if (ga.ref_tone_inhibited_by_rec) parts.push('REC tally active: 1kHz -20dBFS Reference Tone auto-inhibited');
      sqWarn.textContent = parts.join(' | ');
    } else {
      sqWarn.style.display = 'none';
    }
  }

  const rtmdBadge = document.getElementById('p95-rtmd-badge');
  if (rtmdBadge) {
    rtmdBadge.textContent = ga.rtmd_status || 'RTMD_READY';
    rtmdBadge.style.color = ga.rtmd_suspended_by_sq ? '#f87171' : '#10b981';
  }
  const imuRo = document.getElementById('p95-imu-readout');
  if (imuRo) {
    imuRo.textContent =
      `${ga.imu_rate_hz || 2000} Hz · ${Number(ga.imu_samples_per_frame || 83.4).toFixed(1)} samples/frame @ ${Number(ga.effective_fps || 23.98).toFixed(2)}p`;
  }
  const skewRo = document.getElementById('p95-skew-readout');
  if (skewRo) {
    skewRo.textContent =
      `IMX510 Skew: ${Number(ga.rolling_shutter_skew_ms || 8.7).toFixed(1)}ms | ` +
      `Wobble Safe: ${ga.anamorphic_edge_wobble_prevented ? 'true' : 'false'}`;
  }
  const afRo = document.getElementById('p95-touchaf-sync-readout');
  if (afRo) {
    afRo.textContent =
      `Touch-AF: sensor=${ga.touch_x ?? 480} ` +
      `(dsq=${ga.desqueezed_touch_x ?? 480}, scale=${Number(ga.touch_af_inverse_desqueeze_scale || 1.0).toFixed(4)})`;
  }

  const toneBadge = document.getElementById('p95-tone-badge');
  if (toneBadge) {
    if (ga.ref_tone_inhibited_by_rec) {
      toneBadge.textContent = 'INHIBITED (REC)';
      toneBadge.style.color = '#f87171';
    } else if (ga.ref_tone_effective_active || ga.color_bars_effective_active) {
      toneBadge.textContent =
        `${ga.ref_tone_effective_active ? '1kHz -20dBFS' : 'TONE:OFF'}${ga.color_bars_effective_active ? ' + BARS' : ''}`;
      toneBadge.style.color = '#a78bfa';
    } else {
      toneBadge.textContent = 'OFF';
      toneBadge.style.color = '#94a3b8';
    }
  }
  const btnTone = document.getElementById('p95-btn-tone-toggle');
  if (btnTone) {
    btnTone.textContent = ga.ref_tone_inhibited_by_rec
      ? '1kHz -20dBFS: INHIBITED (REC)'
      : `1kHz -20dBFS: ${ga.ref_tone_enabled ? 'ON' : 'OFF'}`;
  }
  const btnBars = document.getElementById('p95-btn-bars-toggle');
  if (btnBars) {
    btnBars.textContent = `SMPTE Bars: ${ga.color_bars_enabled ? 'ON' : 'OFF'}`;
  }
  const toneRo = document.getElementById('p95-tone-status-readout');
  if (toneRo) {
    toneRo.textContent = ga.ref_tone_inhibited_by_rec
      ? 'REC Tally Active · Test tone suppressed to protect live take'
      : (ga.ref_tone_effective_active
          ? 'Active: 1000 Hz @ -20.0 dBFS injected on Ch1-4 (STBY)'
          : 'STBY Ready · Auto-inhibited on REC tally');
  }

  const limBadge = document.getElementById('p95-lim-badge');
  if (limBadge) {
    limBadge.textContent = ga.limiter_enabled ? (ga.limiter_engaging ? '-3.0dBFS CLAMP' : '-3.0dBFS ON') : 'OFF';
    limBadge.style.color = ga.limiter_engaging ? '#f59e0b' : (ga.limiter_enabled ? '#10b981' : '#94a3b8');
  }
  const btnLim = document.getElementById('p95-btn-lim-toggle');
  if (btnLim) {
    btnLim.textContent = `Limiter -3.0dBFS: ${ga.limiter_enabled ? 'ON' : 'OFF'}`;
  }
  const limRo = document.getElementById('p95-lim-ch-readout');
  if (limRo) {
    const chs = Array.isArray(ga.effective_ch_db) ? ga.effective_ch_db.join('/') : '-12/-12/-18/-18';
    const clampCnt = Array.isArray(ga.ch_clamped) ? ga.ch_clamped.filter(Boolean).length : 0;
    limRo.textContent = `Eff Ch: ${chs} dB | Clamped: ${clampCnt}/4`;
  }

  const cmdEl = document.getElementById('p95-cmd-readout');
  if (cmdEl) cmdEl.textContent = ga.gyroflow_anamorphic_cmd || 'GYRO_ANA ...';
}

async function setGyroflowAnamorphic(patch) {
  if (busy) return;
  busy = true;
  const toast = document.getElementById('render-toast');
  const errEl = document.getElementById('p95-error-banner');
  toast.style.display = 'block';
  try {
    const r = await fetch('/api/gyroflow_anamorphic', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(patch || {})
    });
    const data = await r.json();
    if (!data.ok) {
      if (errEl) {
        errEl.style.display = 'block';
        errEl.textContent = data.message || data.error || 'Invalid gyroflow_anamorphic parameter';
      }
    } else if (errEl) {
      errEl.style.display = 'none';
    }
    if (data.status) await updateUI(data.status, true);
  } finally {
    toast.style.display = 'none';
    busy = false;
  }
}

function applyPhase95DesqueezedTouch() {
  const dx = Number((document.getElementById('p95-dsq-touchx-input') || {}).value || 480);
  setGyroflowAnamorphic({desqueezed_touch_x: dx, coordinate_space: 'desqueezed', touch_af_mode: 'touch_tracking'});
}

function togglePhase95RefTone() {
  const cur = !!(currentStatus && currentStatus.gyroflow_anamorphic && currentStatus.gyroflow_anamorphic.ref_tone_enabled);
  setGyroflowAnamorphic({ref_tone_enabled: !cur});
}

function togglePhase95ColorBars() {
  const cur = !!(currentStatus && currentStatus.gyroflow_anamorphic && currentStatus.gyroflow_anamorphic.color_bars_enabled);
  setGyroflowAnamorphic({color_bars_enabled: !cur});
}

function togglePhase95Limiter() {
  const cur = !!(currentStatus && currentStatus.gyroflow_anamorphic && currentStatus.gyroflow_anamorphic.limiter_enabled);
  setGyroflowAnamorphic({limiter_enabled: !cur});
}

const P102_I18N = {
  'en': {
    title: 'Phase 102 · Picture Cache DDR Ring / Interval E-Shutter / .cube 33³ LUT / USB-LAN FTPS',
    cache: 'Picture Cache (Pre-Rec DDR)',
    interval: 'Interval Rec (E-Shutter Only)',
    lut: 'User .cube 3D-LUT (17/33/65³ -> 33³ RAM)',
    ftps: 'Wired USB-LAN FTPS (P12 RF-OFF)',
    applyIntvl: 'Apply Intvl',
    triggerShot: '+1 E-Shot',
    resetShots: 'Reset Shots',
    uploadLut: 'Upload .cube',
    enqClip: '+Queue Clip',
    sendNext: 'Send Next',
    enqCustom: 'Enqueue',
    presetCache8: 'Cache 8s @ 4K60 (384 MiB Clamp)',
    presetIntvl: 'Interval 2s/240f (E-Shutter)',
    presetFtps: 'USB-LAN FTPS Proxy Queue',
    reset: 'Reset P102'
  },
  'zh-CN': {
    title: 'Phase 102 · 预录制 DDR 环形缓存 / 电子快门间隔摄影 / .cube 33³ 四面体上传 / USB-LAN FTPS 队列',
    cache: '预录制 Picture Cache (DDR 环缓)',
    interval: '间隔摄影 Interval Rec (仅电子快门)',
    lut: '用户 .cube 3D-LUT (17/33/65³ -> 33³ 内存)',
    ftps: '有线 USB-LAN FTPS (P12 射频关闭)',
    applyIntvl: '应用间隔',
    triggerShot: '+1 电子张',
    resetShots: '清零计数',
    uploadLut: '上传 .cube',
    enqClip: '+当前素材入队',
    sendNext: '传输下一项',
    enqCustom: '路径入队',
    presetCache8: '8秒预录 @ 4K60 (384 MiB 上限)',
    presetIntvl: '间隔 2s/240张 (电子快门)',
    presetFtps: 'USB-LAN FTPS 代理队列',
    reset: '重置 P102'
  },
  'zh-TW': {
    title: 'Phase 102 · 預錄製 DDR 環形快取 / 電子快門間隔攝影 / .cube 33³ 四面體上傳 / USB-LAN FTPS 佇列',
    cache: '預錄製 Picture Cache (DDR 環緩)',
    interval: '間隔攝影 Interval Rec (僅電子快門)',
    lut: '使用者 .cube 3D-LUT (17/33/65³ -> 33³ 記憶體)',
    ftps: '有線 USB-LAN FTPS (P12 射頻關閉)',
    applyIntvl: '套用間隔',
    triggerShot: '+1 電子張',
    resetShots: '歸零計數',
    uploadLut: '上傳 .cube',
    enqClip: '+目前素材入佇列',
    sendNext: '傳送下一筆',
    enqCustom: '路徑入佇列',
    presetCache8: '8秒預錄 @ 4K60 (384 MiB 上限)',
    presetIntvl: '間隔 2s/240張 (電子快門)',
    presetFtps: 'USB-LAN FTPS 代理佇列',
    reset: '重設 P102'
  },
  'ja': {
    title: 'Phase 102 · ピクチャーキャッシュ DDR / 電子シャッターインターバル / .cube 33³ LUT / USB-LAN FTPS',
    cache: 'ピクチャーキャッシュ (Pre-Rec DDR)',
    interval: 'インターバル撮影 (電子シャッター専用)',
    lut: 'ユーザー .cube 3D-LUT (17/33/65³ -> 33³ RAM)',
    ftps: '有線 USB-LAN FTPS (P12 無線OFF)',
    applyIntvl: '間隔適用',
    triggerShot: '+1 電子撮影',
    resetShots: '枚数リセット',
    uploadLut: '.cube 転送',
    enqClip: '+クリップ登録',
    sendNext: '次を転送',
    enqCustom: 'パス追加',
    presetCache8: '8秒キャッシュ @ 4K60 (384 MiB上限)',
    presetIntvl: '間隔 2秒/240枚 (電子シャッター)',
    presetFtps: 'USB-LAN FTPS プロキシキュー',
    reset: 'P102 リセット'
  }
};

function setP102Lang(lang) {
  const d = P102_I18N[lang] || P102_I18N['en'];
  const map = {
    'p102-card-title': d.title,
    'p102-lbl-cache': d.cache,
    'p102-lbl-interval': d.interval,
    'p102-lbl-lut': d.lut,
    'p102-lbl-ftps': d.ftps,
    'p102-btn-apply-intvl': d.applyIntvl,
    'p102-btn-trigger-shot': d.triggerShot,
    'p102-btn-reset-shots': d.resetShots,
    'p102-btn-upload-lut': d.uploadLut,
    'p102-btn-ftp-enq': d.enqClip,
    'p102-btn-ftp-step': d.sendNext,
    'p102-btn-ftp-custom': d.enqCustom,
    'p102-preset-cache8': d.presetCache8,
    'p102-preset-intvl': d.presetIntvl,
    'p102-preset-ftps': d.presetFtps,
    'p102-btn-reset': d.reset
  };
  Object.keys(map).forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.textContent = map[id];
  });
  ['en', 'zh-CN', 'zh-TW', 'ja'].forEach((code) => {
    const b = document.getElementById('p102-lang-' + code);
    if (b) b.style.borderColor = (code === lang) ? '#10b981' : '#374151';
  });
}

function syncPhase102IntervalCacheLutFtpUI(p102) {
  if (!p102) return;
  const cacheSel = document.getElementById('p102-cache-sec-select');
  if (cacheSel && document.activeElement !== cacheSel) {
    cacheSel.value = String(p102.cache_seconds !== undefined ? p102.cache_seconds : 0);
  }
  const codecSel = document.getElementById('p102-codec-select');
  if (codecSel && p102.codec_profile && document.activeElement !== codecSel) {
    codecSel.value = p102.codec_profile;
  }
  const cacheBadge = document.getElementById('p102-cache-badge');
  if (cacheBadge) {
    if (p102.picture_cache_suspended) {
      cacheBadge.textContent = `SUSPENDED (${p102.picture_cache_suspension_reason || 'MUTEX'})`;
      cacheBadge.style.color = '#fbbf24';
    } else {
      cacheBadge.textContent = `${p102.effective_cache_seconds || 0}s / ${Number(p102.allocated_ddr_mib || 0).toFixed(1)} MiB`;
      cacheBadge.style.color = p102.clamped_by_ddr_budget ? '#f59e0b' : '#10b981';
    }
  }
  const ddrRo = document.getElementById('p102-ddr-readout');
  if (ddrRo) {
    ddrRo.textContent =
      `DDR Ring: ${Number(p102.allocated_ddr_mib || 0).toFixed(1)} / ${Number(p102.ddr_budget_mib || 384).toFixed(1)} MiB ` +
      `(${Number(p102.fx3_total_dram_mib || 2048).toFixed(0)} MiB DRAM) · ${p102.effective_codec_profile || 'XAVC_I_4K24'}` +
      `${p102.clamped_by_ddr_budget ? ' [CLAMPED<=384]' : ''}`;
  }

  const suspBanner = document.getElementById('p102-susp-banner');
  if (suspBanner) {
    const warns = [];
    if (p102.picture_cache_suspended) {
      warns.push(`Picture Cache auto-suspended (${p102.picture_cache_suspension_reason})`);
    }
    if (p102.interval_rec_enabled) {
      warns.push('Interval Rec active: Electronic Shutter enforced (mechanical_curtain_actuations=0) & S&Q excluded');
    }
    if (warns.length > 0) {
      suspBanner.style.display = 'block';
      suspBanner.textContent = warns.join(' | ');
    } else {
      suspBanner.style.display = 'none';
    }
  }

  const intvlBadge = document.getElementById('p102-intvl-badge');
  if (intvlBadge) {
    intvlBadge.textContent = `${p102.interval_rec_enabled ? 'ON' : 'OFF'} · MECH=${p102.mechanical_curtain_actuations ?? 0}`;
    intvlBadge.style.color = p102.interval_rec_enabled ? '#a78bfa' : '#94a3b8';
  }
  const btnIntvl = document.getElementById('p102-btn-intvl-toggle');
  if (btnIntvl) btnIntvl.textContent = `Interval: ${p102.interval_rec_enabled ? 'ON' : 'OFF'}`;
  const isecIn = document.getElementById('p102-intvl-sec-input');
  if (isecIn && document.activeElement !== isecIn && p102.interval_sec !== undefined) {
    isecIn.value = String(p102.interval_sec);
  }
  const tshotIn = document.getElementById('p102-target-shots-input');
  if (tshotIn && document.activeElement !== tshotIn && p102.target_shots !== undefined) {
    tshotIn.value = String(p102.target_shots);
  }
  const aeSel = document.getElementById('p102-ae-select');
  if (aeSel && p102.ae_tracking && document.activeElement !== aeSel) {
    aeSel.value = p102.ae_tracking;
  }
  const intvlRo = document.getElementById('p102-intvl-readout');
  if (intvlRo) {
    intvlRo.textContent =
      `Shots: ${p102.shots_taken ?? 0}/${p102.target_shots ?? 120} @ ${p102.interval_sec ?? 5}s | ` +
      `Curtain Actuations: ${p102.mechanical_curtain_actuations ?? 0} (E-SH, AE=${p102.ae_tracking || 'Mid'})`;
  }

  const lutBadge = document.getElementById('p102-lut-badge');
  if (lutBadge) {
    lutBadge.textContent = p102.active_user_lut_uploaded
      ? `${p102.active_user_lut_slot} (${p102.active_user_lut_source_size || 33}->33³ RAM)`
      : 'RAM 0B eMMC';
  }
  const lutRo = document.getElementById('p102-lut-readout');
  if (lutRo) {
    const shaShort = p102.active_user_lut_resampled_33_sha256
      ? String(p102.active_user_lut_resampled_33_sha256).slice(0, 12)
      : 'none';
    lutRo.textContent =
      `LUT: ${p102.active_user_lut_title || 'None'} | 33³ SHA: ${shaShort} | ` +
      `eMMC=${p102.emmc_mutation_bytes ?? 0}B (Volatile RAM only)`;
  }

  const ftpsModeSel = document.getElementById('p102-ftps-mode-select');
  if (ftpsModeSel && p102.ftps_mode && document.activeElement !== ftpsModeSel) {
    ftpsModeSel.value = p102.ftps_mode;
  }
  const ftpsBadge = document.getElementById('p102-ftps-badge');
  if (ftpsBadge) {
    ftpsBadge.textContent = `P12 SAFE · wf12=${p102.wf12_00342260_hits ?? 0}`;
  }
  const ftpsRo = document.getElementById('p102-ftps-readout');
  if (ftpsRo) {
    ftpsRo.textContent =
      `${p102.ftps_transport || 'USB_LAN_CDC_NCM_RTL8153'} | ` +
      `Q=${p102.ftps_queued_count ?? 0} Done=${p102.ftps_completed_count ?? 0} ` +
      `BlkTrav=${p102.ftps_blocked_traversal_count ?? 0} | wf12=${p102.wf12_00342260_hits ?? 0}`;
  }

  const cmdEl = document.getElementById('p102-cmd-readout');
  if (cmdEl) cmdEl.textContent = p102.interval_cache_lut_ftp_cmd || 'ICLF ...';
}

async function setPhase102State(patch) {
  if (busy) return;
  busy = true;
  const toast = document.getElementById('render-toast');
  const errEl = document.getElementById('p102-error-banner');
  toast.style.display = 'block';
  try {
    const r = await fetch('/api/interval_cache_lut_ftp', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(patch || {})
    });
    const data = await r.json();
    if (!data.ok) {
      if (errEl) {
        errEl.style.display = 'block';
        errEl.textContent = data.message || data.error || 'Invalid Phase 102 parameter';
      }
    } else if (errEl) {
      errEl.style.display = 'none';
    }
    if (data.status) await updateUI(data.status, true);
  } finally {
    toast.style.display = 'none';
    busy = false;
  }
}

function togglePhase102Interval() {
  const cur = !!(currentStatus && currentStatus.interval_cache_lut_ftp && currentStatus.interval_cache_lut_ftp.interval_rec_enabled);
  setPhase102State({interval_rec_enabled: !cur});
}

function applyPhase102IntervalParams() {
  const isec = Number((document.getElementById('p102-intvl-sec-input') || {}).value || 5);
  const tshots = Number((document.getElementById('p102-target-shots-input') || {}).value || 120);
  const ae = (document.getElementById('p102-ae-select') || {}).value || 'Mid';
  setPhase102State({interval_sec: isec, target_shots: tshots, ae_tracking: ae});
}

async function uploadPhase102CubeLut() {
  if (busy) return;
  busy = true;
  const toast = document.getElementById('render-toast');
  const errEl = document.getElementById('p102-error-banner');
  toast.style.display = 'block';
  try {
    const slot = (document.getElementById('p102-lut-slot-select') || {}).value || 'User1';
    const name = String((document.getElementById('p102-lut-title-input') || {}).value || '').trim();
    const cubeText = String((document.getElementById('p102-cube-text') || {}).value || '').trim();
    const payload = {slot};
    if (name) payload.name = name;
    if (cubeText) {
      payload.cube_text = cubeText;
    } else {
      payload.preset = 'teal_orange';
      payload.size = 17;
    }
    const r = await fetch('/api/upload_cube_lut', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload)
    });
    const data = await r.json();
    if (!data.ok) {
      if (errEl) {
        errEl.style.display = 'block';
        errEl.textContent = data.message || data.error || 'Failed to upload .cube LUT';
      }
    } else if (errEl) {
      errEl.style.display = 'none';
    }
    if (data.status) await updateUI(data.status, true);
    await refreshScopeStats(true);
  } finally {
    toast.style.display = 'none';
    busy = false;
  }
}

function enqueuePhase102CustomPath() {
  const p = String((document.getElementById('p102-ftp-path-input') || {}).value || '').trim();
  setPhase102State({enqueue_path: p});
}

const P109_I18N = {
  'en': {
    title: 'Phase 109 · M&C 4-Cam Wired Gang-REC / HDMI→12G-SDI AVI & RP188 / E-Mount-PL / C2PA Zero-Touch',
    fleet: 'M&C 4-Cam Wired Fleet (PTP-IP)',
    sdi: 'HDMI→12G-SDI AVI & RP 188 Bridge',
    mount: 'E-Mount 12-Pin vs PL Hot-Swap Shading',
    c2pa: 'C2PA 2.1 / cnflasha Zero-Touch Shield',
    applyMount: 'Apply',
    testC2pa: 'Test Zero-Touch Guard',
    xmlProv: 'Inspect XML Provenance',
    presetFleet4: '4-Cam Wired Master + Gang REC + RP188',
    presetPlCine: 'Hot-Swap Manual PL (1.8kg G31 Warn)',
    presetPlLws: 'Engage 15mm LWS Support (PL 1.00x)',
    reset: 'Reset P109'
  },
  'zh-CN': {
    title: 'Phase 109 · M&C 4机位有线同步 / HDMI→12G-SDI AVI & RP188 / E-卡口与PL热插拔 / C2PA 零接触溯源',
    fleet: 'M&C 4机位有线同步矩阵 (PTP-IP)',
    sdi: 'HDMI→12G-SDI AVI 量化与 RP 188 触发桥接',
    mount: 'E-卡口 12针 / 无触点 PL 热插拔暗角仲裁',
    c2pa: 'C2PA 2.1 / cnflasha 只读零接触防护盾',
    applyMount: '应用',
    testC2pa: '测试零接触防护',
    xmlProv: '查看 XML 溯源声明',
    presetFleet4: '4机位主机 + 联动录制 + RP188',
    presetPlCine: '热插拔手动 PL 镜头 (1.8kg G31 告警)',
    presetPlLws: '启用 15mm LWS 导管支撑 (PL 1.00x)',
    reset: '重置 P109'
  },
  'zh-TW': {
    title: 'Phase 109 · M&C 4機位有線同步 / HDMI→12G-SDI AVI & RP188 / E-接環與PL熱插拔 / C2PA 零接觸溯源',
    fleet: 'M&C 4機位有線同步矩陣 (PTP-IP)',
    sdi: 'HDMI→12G-SDI AVI 量化與 RP 188 觸發橋接',
    mount: 'E-接環 12針 / 無接點 PL 熱插拔暗角仲裁',
    c2pa: 'C2PA 2.1 / cnflasha 唯讀零接觸防護盾',
    applyMount: '套用',
    testC2pa: '測試零接觸防護',
    xmlProv: '檢視 XML 溯源聲明',
    presetFleet4: '4機位主機 + 連動錄製 + RP188',
    presetPlCine: '熱插拔手動 PL 鏡頭 (1.8kg G31 告警)',
    presetPlLws: '啟用 15mm LWS 導管支撐 (PL 1.00x)',
    reset: '重設 P109'
  },
  'ja': {
    title: 'Phase 109 · M&C 4台有線同期REC / HDMI→12G-SDI AVI & RP188 / Eマウント・PL / C2PA ゼロタッチ',
    fleet: 'M&C 4台有線 PTP-IP 同期マトリクス',
    sdi: 'HDMI→12G-SDI AVI量子化 & RP 188 変換',
    mount: 'Eマウント 12ピン / 無接点 PL 周辺減光補正',
    c2pa: 'C2PA 2.1 / cnflasha ゼロタッチ保護シールド',
    applyMount: '適用',
    testC2pa: 'ゼロタッチ防御テスト',
    xmlProv: 'XML 来歴メタデータ',
    presetFleet4: '4台有線マスター + 連動REC + RP188',
    presetPlCine: '手動 PL マウント交換 (1.8kg G31 警告)',
    presetPlLws: '15mm LWS ロッド装着 (PL 1.00x)',
    reset: 'P109 リセット'
  }
};

function setP109Lang(lang) {
  const d = P109_I18N[lang] || P109_I18N['en'];
  const map = {
    'p109-card-title': d.title,
    'p109-lbl-fleet': d.fleet,
    'p109-lbl-sdi': d.sdi,
    'p109-lbl-mount': d.mount,
    'p109-lbl-c2pa': d.c2pa,
    'p109-btn-apply-mount': d.applyMount,
    'p109-btn-c2pa-guard': d.testC2pa,
    'p109-btn-xml-prov': d.xmlProv,
    'p109-preset-fleet4': d.presetFleet4,
    'p109-preset-pl-cine': d.presetPlCine,
    'p109-preset-pl-lws': d.presetPlLws,
    'p109-btn-reset': d.reset
  };
  Object.keys(map).forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.textContent = map[id];
  });
  ['en', 'zh-CN', 'zh-TW', 'ja'].forEach((code) => {
    const b = document.getElementById('p109-lang-' + code);
    if (b) b.style.borderColor = (code === lang) ? '#06b6d4' : '#374151';
  });
}

function syncPhase109McFleetSdiC2paUI(p109) {
  if (!p109) return;
  const roleSel = document.getElementById('p109-role-select');
  if (roleSel && p109.fleet_role && document.activeElement !== roleSel) roleSel.value = p109.fleet_role;
  const camsSel = document.getElementById('p109-cams-select');
  if (camsSel && p109.fleet_cams_online && document.activeElement !== camsSel) camsSel.value = String(p109.fleet_cams_online);
  const btnGang = document.getElementById('p109-btn-gang-rec');
  if (btnGang) {
    btnGang.textContent = `Gang REC: ${p109.gang_rec_trigger ? 'ON (REC)' : 'OFF'}`;
    btnGang.style.background = p109.gang_rec_trigger ? '#7f1d1d' : '';
  }
  const fleetBadge = document.getElementById('p109-fleet-badge');
  if (fleetBadge) {
    fleetBadge.textContent = `${p109.fleet_role} · ${p109.fleet_cams_online}/4 · wf12=${p109.wf12_00342260_hits ?? 0}`;
  }
  const fleetRo = document.getElementById('p109-fleet-readout');
  if (fleetRo) {
    fleetRo.textContent =
      `${p109.fleet_transport || 'USB_LAN_CDC_NCM_RTL8153'} | ` +
      `Skew=${Number(p109.ptp_max_clock_skew_us || 0).toFixed(1)}us | ` +
      `Gang=${p109.gang_rec_trigger ? 'REC' : 'STBY'} | wf12=${p109.wf12_00342260_hits ?? 0}`;
  }

  const sdiSel = document.getElementById('p109-sdi-select');
  if (sdiSel && p109.sdi_bridge_converter && document.activeElement !== sdiSel) sdiSel.value = p109.sdi_bridge_converter;
  const btnTc = document.getElementById('p109-btn-hdmi-tc');
  if (btnTc) btnTc.textContent = `TC+REC Ctrl: ${p109.hdmi_tc_output_enabled ? 'ON' : 'OFF'}`;
  const sdiBadge = document.getElementById('p109-sdi-badge');
  if (sdiBadge) {
    sdiBadge.textContent = `RP188=${p109.rp188_rec_trigger_bit ?? 0} · CS=${p109.avi_checksum_hex || '0x00'}`;
    sdiBadge.style.color = p109.rp188_rec_trigger_bit ? '#f87171' : '#93c5fd';
  }
  const sdiRo = document.getElementById('p109-sdi-readout');
  if (sdiRo) {
    sdiRo.textContent =
      `AVI CS=${p109.avi_checksum_hex} (sum%256=${p109.avi_checksum_zero_mod256}) | ` +
      `${p109.avi_quantization_range} | RP188 ${p109.rp188_atc_did}/${p109.rp188_atc_sdid} Parity=${p109.rp188_parity_ok ? 'OK' : 'ERR'}`;
  }

  const mtSel = document.getElementById('p109-mount-select');
  if (mtSel && p109.mount_type && document.activeElement !== mtSel) mtSel.value = p109.mount_type;
  const kgIn = document.getElementById('p109-lens-kg-input');
  if (kgIn && p109.lens_kg !== undefined && document.activeElement !== kgIn) kgIn.value = String(p109.lens_kg);
  const btnLws = document.getElementById('p109-btn-lws');
  if (btnLws) btnLws.textContent = `LWS: ${p109.rod_support_15mm_lws ? 'ON' : 'OFF'}`;
  const mtBadge = document.getElementById('p109-mount-badge');
  if (mtBadge) {
    mtBadge.textContent = `${p109.electronic_pins_active || 0}-Pin · ${Number(p109.vignetting_comp_gain || 1.0).toFixed(2)}x`;
  }
  const mtRo = document.getElementById('p109-mount-readout');
  if (mtRo) {
    mtRo.textContent =
      `Shading=${Number(p109.vignetting_comp_gain || 1.0).toFixed(2)}x ` +
      `(reset=${Number(p109.reset_latency_ms || 0).toFixed(2)}ms <1f) | ${Number(p109.lens_kg || 0.7).toFixed(2)}kg | ${p109.g31_15mm_lws_message || ''}`;
  }

  const c2paBadge = document.getElementById('p109-c2pa-badge');
  if (c2paBadge) c2paBadge.textContent = `RDONLY · kr=${p109.private_key_reads ?? 0} cw=${p109.cnflasha_writes ?? 0}`;
  const c2paRo = document.getElementById('p109-c2pa-readout');
  if (c2paRo) {
    c2paRo.textContent =
      `${p109.c2pa_vault_status} | ${p109.c2pa_provenance_mode} | ` +
      `HWAttest=${p109.hardware_attestation_claimed ? 'TRUE' : 'FALSE'} Blk=${p109.c2pa_blocked_attempts ?? 0}`;
  }

  const warnEl = document.getElementById('p109-warn-banner');
  if (warnEl) {
    if (p109.g31_15mm_lws_warning) {
      warnEl.style.display = 'block';
      warnEl.textContent = p109.g31_15mm_lws_message || 'G31 WARNING: 15mm LWS rod support required for lens > 1.2kg';
    } else {
      warnEl.style.display = 'none';
    }
  }

  const cmdEl = document.getElementById('p109-cmd-readout');
  if (cmdEl) cmdEl.textContent = p109.mc_fleet_sdi_c2pa_cmd || 'MCFL ...';
}

async function setPhase109State(patch) {
  if (busy) return;
  busy = true;
  const toast = document.getElementById('render-toast');
  const errEl = document.getElementById('p109-error-banner');
  toast.style.display = 'block';
  try {
    const r = await fetch('/api/mc_fleet_sdi_c2pa', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(patch || {})
    });
    const data = await r.json();
    if (!data.ok) {
      if (errEl) {
        errEl.style.display = 'block';
        errEl.textContent = data.message || data.error || 'Blocked / Invalid Phase 109 parameter';
      }
      if (data.mc_fleet_sdi_c2pa) syncPhase109McFleetSdiC2paUI(data.mc_fleet_sdi_c2pa);
    } else if (errEl) {
      errEl.style.display = 'none';
    }
    if (data.status) await updateUI(data.status, true);
  } finally {
    toast.style.display = 'none';
    busy = false;
  }
}

function togglePhase109GangRec() {
  const cur = !!(currentStatus && currentStatus.mc_fleet_sdi_c2pa && currentStatus.mc_fleet_sdi_c2pa.gang_rec_trigger);
  setPhase109State({gang_rec_trigger: !cur});
}

function togglePhase109HdmiTc() {
  const cur = !!(currentStatus && currentStatus.mc_fleet_sdi_c2pa && currentStatus.mc_fleet_sdi_c2pa.hdmi_tc_output_enabled);
  setPhase109State({hdmi_tc_output_enabled: !cur, hdmi_rec_control_enabled: !cur});
}

function applyPhase109MountParams() {
  const mt = (document.getElementById('p109-mount-select') || {}).value || 'Sony_EMount_12Pin_GM';
  const kg = Number((document.getElementById('p109-lens-kg-input') || {}).value || 0.7);
  setPhase109State({mount_type: mt, lens_kg: kg});
}

function togglePhase109Lws() {
  const cur = !!(currentStatus && currentStatus.mc_fleet_sdi_c2pa && currentStatus.mc_fleet_sdi_c2pa.rod_support_15mm_lws);
  setPhase109State({rod_support_15mm_lws: !cur});
}

const P116_I18N = {
  en: {
    title: 'Phase 116 · HLG1/HLG2/HLG3 BT.2100 & CTA-861.3 (0x87) / Clean HDMI Display Assist / ProRes RAW & BRAW / Breathing Comp',
    hlg: 'HLG BT.2100 & CTA-861.3 (0x87)',
    assist: 'Gamma Display Assist (Clean HDMI/SDI)',
    raw: 'External HDMI RAW (16->12-Bit Log)',
    fbc: 'Focus Breathing Comp (E-Mount 12-Pin)',
    applyDetail: 'Apply',
    testLeak: 'Test Clean Leak Guard',
    xmlSidecar: 'Inspect HDR XML',
    testFbcPl: 'Test PL Bypass',
    presetHlg3: 'HLG3 BT.2020 (1090nit) + Assist AUTO',
    presetProRes: 'Atomos ProRes RAW 16->12L (FBC 1.00x Bypass)',
    presetBraw: 'Blackmagic BRAW 16->12L (FBC 1.00x Bypass)',
    presetFbcEmount: 'E-Mount 12-Pin Breathing Comp AUTO',
    reset: 'Reset P116'
  },
  'zh-CN': {
    title: 'Phase 116 · HLG1/HLG2/HLG3 BT.2100 & CTA-861.3 (0x87) / Display Assist 洁净隔离 / ProRes RAW & BRAW / 呼吸效应补偿',
    hlg: 'HLG BT.2100 & CTA-861.3 (0x87)',
    assist: '伽马显示辅助 (VF/LCD 隔离 · HDMI/SDI 洁净输出)',
    raw: '外录 HDMI RAW (16->12-Bit Log)',
    fbc: '呼吸效应补偿 (E卡口 12-Pin / PL 旁路)',
    applyDetail: '应用',
    testLeak: '测试洁净输出防泄漏',
    xmlSidecar: '查看 HDR XML 边车',
    testFbcPl: '测试 PL 卡口旁路',
    presetHlg3: 'HLG3 BT.2020 (1090nit) + 辅助 AUTO',
    presetProRes: 'Atomos ProRes RAW 16->12L (呼吸补偿 1.00x 旁路)',
    presetBraw: 'Blackmagic BRAW 16->12L (呼吸补偿 1.00x 旁路)',
    presetFbcEmount: 'E-卡口 12-Pin 呼吸效应补偿 AUTO',
    reset: '重置 P116'
  },
  'zh-TW': {
    title: 'Phase 116 · HLG1/HLG2/HLG3 BT.2100 & CTA-861.3 (0x87) / Display Assist 潔淨隔離 / ProRes RAW & BRAW / 呼吸效應補償',
    hlg: 'HLG BT.2100 & CTA-861.3 (0x87)',
    assist: 'Gamma 顯示輔助 (VF/LCD 隔離 · HDMI/SDI 潔淨輸出)',
    raw: '外錄 HDMI RAW (16->12-Bit Log)',
    fbc: '呼吸效應補償 (E接環 12-Pin / PL 旁路)',
    applyDetail: '套用',
    testLeak: '測試潔淨輸出防洩漏',
    xmlSidecar: '檢視 HDR XML Sidecar',
    testFbcPl: '測試 PL 接環旁路',
    presetHlg3: 'HLG3 BT.2020 (1090nit) + 輔助 AUTO',
    presetProRes: 'Atomos ProRes RAW 16->12L (呼吸補償 1.00x 旁路)',
    presetBraw: 'Blackmagic BRAW 16->12L (呼吸補償 1.00x 旁路)',
    presetFbcEmount: 'E-接環 12-Pin 呼吸效應補償 AUTO',
    reset: '重設 P116'
  },
  ja: {
    title: 'Phase 116 · HLG1/HLG2/HLG3 BT.2100 & CTA-861.3 (0x87) / ガンマ表示アシスト隔離 / ProRes RAW & BRAW / ブリージング補正',
    hlg: 'HLG BT.2100 & CTA-861.3 (0x87)',
    assist: 'ガンマ表示アシスト (EVF/LCD 専用 · クリーン HDMI/SDI)',
    raw: '外部 HDMI RAW (16->12-Bit Log)',
    fbc: 'ブリージング補正 (Eマウント 12ピン / PL バイパス)',
    applyDetail: '適用',
    testLeak: 'クリーン出力漏洩ガード',
    xmlSidecar: 'HDR XML サイドカー確認',
    testFbcPl: 'PL バイパステスト',
    presetHlg3: 'HLG3 BT.2020 (1090nit) + アシスト AUTO',
    presetProRes: 'Atomos ProRes RAW 16->12L (補正 1.00x バイパス)',
    presetBraw: 'Blackmagic BRAW 16->12L (補正 1.00x バイパス)',
    presetFbcEmount: 'Eマウント 12ピン ブリージング補正 AUTO',
    reset: 'P116 リセット'
  }
};

function setP116Lang(lang) {
  const d = P116_I18N[lang] || P116_I18N['en'];
  const map = {
    'p116-card-title': d.title,
    'p116-lbl-hlg': d.hlg,
    'p116-lbl-assist': d.assist,
    'p116-lbl-raw': d.raw,
    'p116-lbl-fbc': d.fbc,
    'p116-btn-apply-detail': d.applyDetail,
    'p116-btn-test-leak': d.testLeak,
    'p116-btn-xml-sidecar': d.xmlSidecar,
    'p116-btn-test-fbc-pl': d.testFbcPl,
    'p116-preset-hlg3-assist': d.presetHlg3,
    'p116-preset-prores-raw': d.presetProRes,
    'p116-preset-braw': d.presetBraw,
    'p116-preset-fbc-emount': d.presetFbcEmount,
    'p116-btn-reset': d.reset
  };
  Object.keys(map).forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.textContent = map[id];
  });
  ['en', 'zh-CN', 'zh-TW', 'ja'].forEach((code) => {
    const b = document.getElementById('p116-lang-' + code);
    if (b) b.style.borderColor = (code === lang) ? '#f59e0b' : '#374151';
  });
}

function syncPhase116HlgRawBreathingUI(p116) {
  if (!p116) return;
  const hlgSel = document.getElementById('p116-hlg-select');
  if (hlgSel && p116.hlg_profile && document.activeElement !== hlgSel) hlgSel.value = p116.hlg_profile;
  const gamSel = document.getElementById('p116-gamut-select');
  if (gamSel && p116.color_gamut && document.activeElement !== gamSel) gamSel.value = p116.color_gamut;
  const kneeSel = document.getElementById('p116-knee-select');
  if (kneeSel && p116.knee_mode && document.activeElement !== kneeSel) kneeSel.value = p116.knee_mode;
  const detIn = document.getElementById('p116-detail-input');
  if (detIn && p116.detail_level !== undefined && document.activeElement !== detIn) detIn.value = String(p116.detail_level);

  const hlgBadge = document.getElementById('p116-hlg-badge');
  if (hlgBadge) {
    hlgBadge.textContent = `${p116.hlg_profile} · ${p116.peak_nits ?? 100}nit · CS=${p116.cta_checksum_hex || '0x00'}`;
  }
  const hlgRo = document.getElementById('p116-hlg-readout');
  if (hlgRo) {
    hlgRo.textContent =
      `CTA-861.3 0x87 EOTF=${p116.cta_eotf ?? 0} CS=${p116.cta_checksum_hex} (sum%256=${p116.cta_checksum_zero_mod256}) | ` +
      `CICP ${p116.cicp_color_primaries}/${p116.cicp_transfer_characteristics}/${p116.cicp_matrix_coefficients} | Knee=${Number(p116.knee_pct || 0).toFixed(0)}% Det=${p116.detail_level ?? 0}`;
  }

  const assSel = document.getElementById('p116-assist-select');
  if (assSel && p116.display_assist_mode && document.activeElement !== assSel) assSel.value = p116.display_assist_mode;
  const assBadge = document.getElementById('p116-assist-badge');
  if (assBadge) {
    assBadge.textContent = `${p116.resolved_assist_mode || 'OFF'} · CLEAN=${p116.clean_hdmi_sdi_unassisted ? 1 : 0}`;
  }
  const assRo = document.getElementById('p116-assist-readout');
  if (assRo) {
    assRo.textContent =
      `EVF/LCD=${p116.resolved_assist_mode} (Ceil=${p116.vf_nit_ceiling ?? 100}nit) | Clean HDMI/SDI=${p116.clean_hdmi_sdi_unassisted ? 1 : 0} ` +
      `XAVC=${p116.xavc_internal_unassisted ? 1 : 0} Leak=${p116.external_output_assist_leak_px ?? 0}px Blk=${p116.assist_leak_blocked_count ?? 0}`;
  }

  const rawSel = document.getElementById('p116-raw-select');
  if (rawSel && p116.ext_raw_mode && document.activeElement !== rawSel) rawSel.value = p116.ext_raw_mode;
  const rawBadge = document.getElementById('p116-raw-badge');
  if (rawBadge) {
    rawBadge.textContent = p116.ext_raw_active ? `${p116.raw_bit_depth_in}->${p116.raw_bit_depth_packed}b Log` : 'OFF · XAVC 10b';
  }
  const rawRo = document.getElementById('p116-raw-readout');
  if (rawRo) {
    rawRo.textContent = p116.raw_hdmi_packet_summary || 'Internal XAVC (Ext RAW OFF)';
  }

  const fbcSel = document.getElementById('p116-fbc-select');
  if (fbcSel && p116.breathing_comp_mode && document.activeElement !== fbcSel) fbcSel.value = p116.breathing_comp_mode;
  const fbcBadge = document.getElementById('p116-fbc-badge');
  if (fbcBadge) {
    fbcBadge.textContent = `${p116.breathing_effective_active ? 'ON' : (p116.breathing_comp_mode === 'AUTO' ? 'BYPASS' : 'OFF')} · ${Number(p116.breathing_crop_factor || 1.0).toFixed(2)}x`;
  }
  const fbcRo = document.getElementById('p116-fbc-readout');
  if (fbcRo) {
    fbcRo.textContent = `FBC=${p116.breathing_comp_mode}->${p116.breathing_effective_active ? 'ACTIVE' : 'BYPASS'} (${Number(p116.breathing_crop_factor || 1.0).toFixed(2)}x) | ${p116.breathing_bypass_reason || ''}`;
  }

  const warnEl = document.getElementById('p116-warn-banner');
  if (warnEl) {
    if (p116.breathing_bypassed_by_pl_mount || p116.breathing_bypassed_by_raw) {
      warnEl.style.display = 'block';
      warnEl.textContent = `Focus Breathing Bypassed (1.00x): ${p116.breathing_bypass_reason}`;
    } else {
      warnEl.style.display = 'none';
    }
  }

  const cmdEl = document.getElementById('p116-cmd-readout');
  if (cmdEl) cmdEl.textContent = p116.hdr_hlg_raw_breathing_cmd || 'HLGA ...';
}

async function setPhase116State(patch) {
  if (busy) return;
  busy = true;
  const toast = document.getElementById('render-toast');
  const errEl = document.getElementById('p116-error-banner');
  toast.style.display = 'block';
  try {
    const r = await fetch('/api/hdr_hlg_raw_breathing', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(patch || {})
    });
    const data = await r.json();
    if (!data.ok) {
      if (errEl) {
        errEl.style.display = 'block';
        errEl.textContent = data.message || data.error || 'Blocked / Invalid Phase 116 parameter';
      }
      if (data.hdr_hlg_raw_breathing) syncPhase116HlgRawBreathingUI(data.hdr_hlg_raw_breathing);
    } else if (errEl) {
      errEl.style.display = 'none';
    }
    if (data.status) await updateUI(data.status, true);
  } finally {
    toast.style.display = 'none';
    busy = false;
  }
}

function applyPhase116Detail() {
  const det = Number((document.getElementById('p116-detail-input') || {}).value || 0);
  setPhase116State({detail_level: det});
}

const P123_I18N = {
  en: {
    title: 'Phase 123 · USB-C UVC 1.5 / UAC 2.0 Clean Stream · P12 Wired SRT/RTMPS · CRSDK PTP Remote & Flash Firewall',
    uvc: 'USB-C UVC 1.5 / UAC 2.0 Clean Feed',
    srt: 'Wired CDC-NCM SRT / RTMPS TLS 1.3 (P12)',
    ptp: 'CRSDK PTP / PTP-IP (0x054C) Remote',
    fw: 'PTP Flash-Opcode Firewall (0x9280..)',
    testOsd: 'Test OSD Block',
    applySrt: 'Apply',
    testWifi: 'Test P12 Wi-Fi',
    sendD2xx: 'Run 0xD2xx',
    testNd: 'Test P4 ND',
    test9280: 'Block 0x9280 Flash',
    test9285: 'Block 0x9285 UFU',
    presetUvc4k: 'UVC 4K30p + SRT Caller AES-256 + PTP-IP',
    presetUsb2: 'USB2 480M Stepdown (720p30) + RTMPS TLS1.3',
    presetPtpEi: 'CRSDK 0xD210 EI 12800 + S-Log3',
    reset: 'Reset P123'
  },
  'zh-CN': {
    title: 'Phase 123 · USB-C UVC 1.5 / UAC 2.0 洁净推流 · P12 有线 SRT/RTMPS · CRSDK PTP 遥控与刷写防火墙',
    uvc: 'USB-C UVC 1.5 / UAC 2.0 洁净输出',
    srt: '有线 CDC-NCM SRT / RTMPS TLS 1.3 (P12 关 Wi-Fi)',
    ptp: 'Sony CRSDK PTP / PTP-IP (0x054C) 遥控',
    fw: 'PTP 固件刷写销毁指令防火墙 (0x9280..)',
    testOsd: '测试 OSD 防烧录',
    applySrt: '应用',
    testWifi: '测试 P12 Wi-Fi 拦截',
    sendD2xx: '执行 0xD2xx',
    testNd: '测试 P4 ND 钳位',
    test9280: '拦截 0x9280 刷写',
    test9285: '拦截 0x9285 UFU',
    presetUvc4k: 'UVC 4K30p + SRT Caller AES-256 + PTP-IP',
    presetUsb2: 'USB2 480M 自动降档 (720p30) + RTMPS TLS1.3',
    presetPtpEi: 'CRSDK 0xD210 EI 12800 + S-Log3',
    reset: '重置 P123'
  },
  'zh-TW': {
    title: 'Phase 123 · USB-C UVC 1.5 / UAC 2.0 潔淨串流 · P12 有線 SRT/RTMPS · CRSDK PTP 遙控與刷寫防火牆',
    uvc: 'USB-C UVC 1.5 / UAC 2.0 潔淨輸出',
    srt: '有線 CDC-NCM SRT / RTMPS TLS 1.3 (P12 關 Wi-Fi)',
    ptp: 'Sony CRSDK PTP / PTP-IP (0x054C) 遙控',
    fw: 'PTP 韌體刷寫銷毀指令防火牆 (0x9280..)',
    testOsd: '測試 OSD 防燒錄',
    applySrt: '套用',
    testWifi: '測試 P12 Wi-Fi 攔截',
    sendD2xx: '執行 0xD2xx',
    testNd: '測試 P4 ND 鉗位',
    test9280: '攔截 0x9280 刷寫',
    test9285: '攔截 0x9285 UFU',
    presetUvc4k: 'UVC 4K30p + SRT Caller AES-256 + PTP-IP',
    presetUsb2: 'USB2 480M 自動降階 (720p30) + RTMPS TLS1.3',
    presetPtpEi: 'CRSDK 0xD210 EI 12800 + S-Log3',
    reset: '重設 P123'
  },
  ja: {
    title: 'Phase 123 · USB-C UVC 1.5 / UAC 2.0 クリーン配信 · P12 有線 SRT/RTMPS · CRSDK PTP 制御＆書換FW',
    uvc: 'USB-C UVC 1.5 / UAC 2.0 クリーン出力',
    srt: '有線 CDC-NCM SRT / RTMPS TLS 1.3 (P12 Wi-Fi OFF)',
    ptp: 'Sony CRSDK PTP / PTP-IP (0x054C) 遠隔制御',
    fw: 'PTP フラッシュ破壊命令ファイアウォール (0x9280..)',
    testOsd: 'OSD 焼込遮断テスト',
    applySrt: '適用',
    testWifi: 'P12 Wi-Fi 遮断テスト',
    sendD2xx: '0xD2xx 実行',
    testNd: 'P4 ND クランプ試験',
    test9280: '0x9280 書換を遮断',
    test9285: '0x9285 UFU を遮断',
    presetUvc4k: 'UVC 4K30p + SRT Caller AES-256 + PTP-IP',
    presetUsb2: 'USB2 480M 自動降格 (720p30) + RTMPS TLS1.3',
    presetPtpEi: 'CRSDK 0xD210 EI 12800 + S-Log3',
    reset: 'P123 リセット'
  }
};

function setP123Lang(lang) {
  const d = P123_I18N[lang] || P123_I18N['en'];
  const map = {
    'p123-card-title': d.title,
    'p123-lbl-uvc': d.uvc,
    'p123-lbl-srt': d.srt,
    'p123-lbl-ptp': d.ptp,
    'p123-lbl-fw': d.fw,
    'p123-btn-test-osd-leak': d.testOsd,
    'p123-btn-apply-srt': d.applySrt,
    'p123-btn-test-wifi': d.testWifi,
    'p123-btn-send-d2xx': d.sendD2xx,
    'p123-btn-test-nd-clamp': d.testNd,
    'p123-btn-test-flash-9280': d.test9280,
    'p123-btn-test-flash-9285': d.test9285,
    'p123-preset-uvc4k-srt-ptpip': d.presetUvc4k,
    'p123-preset-usb2-fallback': d.presetUsb2,
    'p123-preset-ptp-ei12800': d.presetPtpEi,
    'p123-btn-reset': d.reset
  };
  Object.keys(map).forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.textContent = map[id];
  });
  ['en', 'zh-CN', 'zh-TW', 'ja'].forEach((code) => {
    const b = document.getElementById('p123-lang-' + code);
    if (b) b.style.borderColor = (code === lang) ? '#10b981' : '#374151';
  });
}

function syncPhase123UvcSrtCrsdkPtpUI(p123) {
  if (!p123) return;
  const uvcSel = document.getElementById('p123-uvc-select');
  if (uvcSel && p123.uvc_mode && document.activeElement !== uvcSel) uvcSel.value = p123.uvc_mode;
  const spdSel = document.getElementById('p123-usb-speed-select');
  if (spdSel && p123.usb_link_speed && document.activeElement !== spdSel) spdSel.value = p123.usb_link_speed;
  const uvcBadge = document.getElementById('p123-uvc-badge');
  if (uvcBadge) {
    uvcBadge.textContent = `${p123.effective_uvc_mode || 'OFF'} · CLEAN=${p123.uvc_clean_feed_no_osd ? 1 : 0}`;
  }
  const uvcRo = document.getElementById('p123-uvc-readout');
  if (uvcRo) {
    uvcRo.textContent =
      `${p123.uvc_resolution || '0x0'}@${p123.uvc_fps ?? 0} ${p123.uvc_codec || 'NONE'} (${p123.usb_link_speed}) | ` +
      `UAC=${p123.uac_audio_spec} | Clean=${p123.uvc_clean_feed_no_osd ? 1 : 0} OSD=${p123.uvc_osd_burnin_px ?? 0}px Blk=${p123.uvc_osd_blocked_count ?? 0}`;
  }

  const srtSel = document.getElementById('p123-srt-select');
  if (srtSel && p123.srt_mode && document.activeElement !== srtSel) srtSel.value = p123.srt_mode;
  const pkSel = document.getElementById('p123-pbkey-select');
  if (pkSel && p123.srt_pbkeylen && document.activeElement !== pkSel) pkSel.value = p123.srt_pbkeylen;
  const latIn = document.getElementById('p123-latency-input');
  if (latIn && p123.srt_latency_ms !== undefined && document.activeElement !== latIn) latIn.value = String(p123.srt_latency_ms);
  const rtmpsSel = document.getElementById('p123-rtmps-select');
  if (rtmpsSel && p123.rtmps_mode && document.activeElement !== rtmpsSel) rtmpsSel.value = p123.rtmps_mode;
  const brIn = document.getElementById('p123-bitrate-input');
  if (brIn && p123.stream_bitrate_mbps !== undefined && document.activeElement !== brIn) brIn.value = String(p123.stream_bitrate_mbps);
  const srtBadge = document.getElementById('p123-srt-badge');
  if (srtBadge) {
    srtBadge.textContent = `${p123.srt_mode}/${p123.rtmps_mode} · P12=${p123.p12_wlan_off ? 1 : 0}`;
  }
  const srtRo = document.getElementById('p123-srt-readout');
  if (srtRo) {
    srtRo.textContent =
      `CDC-NCM Wired | ${p123.srt_pbkeylen} ARQ=${p123.srt_latency_ms}ms ${p123.stream_bitrate_mbps}Mbps | ` +
      `P12_WLAN_OFF=${p123.p12_wlan_off ? 1 : 0} wf12=${p123.wf12_00342260_hits ?? 0} Blk=${p123.p12_blocked_count ?? 0}`;
  }

  const ptpSel = document.getElementById('p123-ptp-select');
  if (ptpSel && p123.crsdk_ptp_mode && document.activeElement !== ptpSel) ptpSel.value = p123.crsdk_ptp_mode;
  const ptpBadge = document.getElementById('p123-ptp-badge');
  if (ptpBadge) {
    ptpBadge.textContent = `${p123.crsdk_ptp_mode} · ${p123.crsdk_last_safe_opcode || '0xD210'}`;
  }
  const ptpRo = document.getElementById('p123-ptp-readout');
  if (ptpRo) {
    ptpRo.textContent =
      `VID ${p123.crsdk_usb_vid} (${p123.crsdk_last_safe_prop}) | Base${p123.crsdk_cine_ei_base} EI${p123.crsdk_ei_index} | ` +
      `Look=${p123.crsdk_base_look} | ND=Clear (Clamp=${p123.crsdk_nd_clamp_count ?? 0})`;
  }

  const fwBadge = document.getElementById('p123-fw-badge');
  if (fwBadge) {
    fwBadge.textContent = `ARMED · eMMC=${p123.emmc_mutation_bytes ?? 0}B · Blk=${p123.blocked_flash_opcode_count ?? 0}`;
  }
  const fwRo = document.getElementById('p123-fw-readout');
  if (fwRo) {
    fwRo.textContent =
      `Firewall=${p123.ptp_flash_opcodes_blocked ? 'ON' : 'OFF'} | eMMC_Mutation=${p123.emmc_mutation_bytes ?? 0}B | ` +
      `Blocked=${p123.blocked_flash_opcode_count ?? 0} Last=${p123.last_blocked_flash_opcode || 'NONE'}`;
  }

  const warnEl = document.getElementById('p123-warn-banner');
  if (warnEl) {
    if (p123.uvc_usb2_stepdown_active) {
      warnEl.style.display = 'block';
      warnEl.textContent = `USB 2.0 (480 Mbps) non-SuperSpeed cable detected: auto-stepped down ${p123.uvc_mode} -> ${p123.effective_uvc_mode} (1280x720@30p MJPEG).`;
    } else {
      warnEl.style.display = 'none';
    }
  }

  const cmdEl = document.getElementById('p123-cmd-readout');
  if (cmdEl) cmdEl.textContent = p123.uvc_srt_crsdk_ptp_cmd || 'UVCS ...';
}

async function setPhase123State(patch) {
  if (busy) return;
  busy = true;
  const toast = document.getElementById('render-toast');
  const errEl = document.getElementById('p123-error-banner');
  toast.style.display = 'block';
  try {
    const r = await fetch('/api/uvc_srt_crsdk_ptp', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(patch || {})
    });
    const data = await r.json();
    if (!data.ok) {
      if (errEl) {
        errEl.style.display = 'block';
        errEl.textContent = data.message || data.error || 'Blocked / Invalid Phase 123 parameter';
      }
      if (data.uvc_srt_crsdk_ptp) syncPhase123UvcSrtCrsdkPtpUI(data.uvc_srt_crsdk_ptp);
    } else if (errEl) {
      errEl.style.display = 'none';
    }
    if (data.status) await updateUI(data.status, true);
  } finally {
    toast.style.display = 'none';
    busy = false;
  }
}

function applyPhase123SrtParams() {
  const lat = Number((document.getElementById('p123-latency-input') || {}).value || 120);
  const br = Number((document.getElementById('p123-bitrate-input') || {}).value || 12);
  setPhase123State({srt_latency_ms: lat, stream_bitrate_mbps: br});
}

function sendPhase123SafeOpcode() {
  const op = (document.getElementById('p123-d2xx-select') || {}).value || '0xD210';
  const curMode = (document.getElementById('p123-ptp-select') || {}).value || 'OFF';
  const patch = {ptp_opcode: op};
  if (curMode === 'OFF') patch.crsdk_ptp_mode = 'USB_PTP';
  setPhase123State(patch);
}

setP95Lang('zh-CN');
setP102Lang('zh-CN');
setP109Lang('zh-CN');
setP116Lang('zh-CN');
setP123Lang('zh-CN');
loadPages128();
loadMenuCatalog();
setInterval(pollStatus, 1500);
pollStatus();
refreshScopeStats(false);
</script>
</body>
</html>
"""


def make_handler(session: FX6LiveGpe0Session):
    class Handler(BaseHTTPRequestHandler):
        timeout = 15.0

        def log_message(self, fmt: str, *args: Any) -> None:
            pass

        def _record_disconnect(self) -> None:
            self.close_connection = True
            session.socket_disconnect_count += 1
            if hasattr(self.server, "client_disconnects"):
                self.server.client_disconnects += 1

        def handle_one_request(self) -> None:
            try:
                super().handle_one_request()
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, TimeoutError, socket.timeout, OSError) as exc:
                if _is_client_disconnect_exc(exc):
                    self._record_disconnect()
                    return
                raise

        def finish(self) -> None:
            try:
                super().finish()
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, TimeoutError, socket.timeout, OSError) as exc:
                if _is_client_disconnect_exc(exc):
                    self._record_disconnect()
                    return
                raise

        def _safe_send_error(self, code: int, message: str | None = None) -> None:
            try:
                self.send_error(code, message)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, TimeoutError, socket.timeout, OSError) as exc:
                if _is_client_disconnect_exc(exc):
                    self._record_disconnect()
                    return
                raise

        def _send_bytes(
            self,
            raw: bytes,
            content_type: str,
            status: int = 200,
            extra_headers: dict[str, str] | None = None,
        ) -> bool:
            try:
                self.send_response(int(status))
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(raw)))
                self.send_header("Cache-Control", "no-store")
                if extra_headers:
                    for hk, hv in extra_headers.items():
                        self.send_header(str(hk), str(hv))
                self.end_headers()
                if raw:
                    self.wfile.write(raw)
                self.wfile.flush()
                return True
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, TimeoutError, socket.timeout, OSError) as exc:
                if _is_client_disconnect_exc(exc):
                    self._record_disconnect()
                    return False
                raise

        def _send_json(self, obj: Any, status: int = 200) -> bool:
            raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            return self._send_bytes(raw, "application/json; charset=utf-8", status=int(status))

        def do_GET(self) -> None:
            try:
                parsed = urllib.parse.urlparse(self.path)
                path = parsed.path
                qs = urllib.parse.parse_qs(parsed.query)
                if path in ("/", "/index.html"):
                    self._send_bytes(HTML_UI.encode("utf-8"), "text/html; charset=utf-8", status=HTTPStatus.OK)
                    return
                if path == "/api/status":
                    self._send_json(session.get_status())
                    return
                if path == "/api/pages128":
                    self._send_json(ALL_128_PAGES)
                    return
                if path == "/api/menu_catalog":
                    q_val = qs.get("q", qs.get("query", [""]))[0]
                    cat_val = qs.get("category", [""])[0]
                    res = search_menu_catalog(query=q_val, category=cat_val) if (q_val or cat_val) else build_menu_catalog()
                    self._send_json(res)
                    return
                if path == "/api/verify_multilang_diff":
                    self._send_json({
                        "ok": session.last_multilang_diff is not None,
                        "receipt": session.last_multilang_diff,
                    })
                    return
                if path == "/api/lang":
                    self._send_json({
                        "current": session.lang_code,
                        "lang_id": session.lang_id,
                        "packs": discover_available_lang_packs(),
                    })
                    return
                if path == "/api/fx3_button":
                    self._send_json({
                        "last_p10_telemetry": dict(session.last_p10_telemetry),
                        "buttons": FX3_BUTTON_MAP,
                    })
                    return
                if path == "/api/cinema_param":
                    self._send_json({
                        "ok": True,
                        "cinema_params": session.get_cinema_params(),
                        "stage_b_telemetry": session.get_stage_b_telemetry(),
                        "last_toast": session.last_toast,
                    })
                    return
                if path in ("/api/lut_upload", "/api/upload_cube_lut"):
                    self._send_json(session.get_lut_slots())
                    return
                if path in ("/api/preset_export", "/api/camset_export"):
                    self._send_json(session.export_camset_preset())
                    return
                if path == "/api/cine_exposure":
                    self._send_json({
                        "ok": True,
                        "cine_exposure": session.get_cine_exposure(),
                        "specs": CINE_EXPOSURE_SPECS,
                        "last_toast": session.last_toast,
                    })
                    return
                if path == "/api/color_and_media":
                    self._send_json({
                        "ok": True,
                        "color_and_media": session.get_color_and_media(),
                        "specs": COLOR_AND_MEDIA_SPECS,
                        "last_toast": session.last_toast,
                    })
                    return
                if path == "/api/xml_sidecar":
                    res = session.get_xml_sidecar()
                    fmt = qs.get("format", [""])[0].strip().lower()
                    if fmt == "json":
                        self._send_json(res)
                    else:
                        xml_bytes = str(res["xml"]).encode("utf-8")
                        self._send_bytes(
                            xml_bytes,
                            "application/xml; charset=utf-8",
                            status=HTTPStatus.OK,
                            extra_headers={"Content-Disposition": f'attachment; filename="{res["filename"]}"'},
                        )
                    return
                if path == "/api/assist_tools":
                    self._send_json({
                        "ok": True,
                        "assist_tools": session.get_assist_tools(),
                        "specs": ASSIST_TOOLS_SPECS,
                        "last_toast": session.last_toast,
                    })
                    return
                if path == "/api/touch_focus_ciz":
                    self._send_json({
                        "ok": True,
                        "touch_focus_ciz": session.get_touch_focus_ciz(),
                        "specs": TOUCH_FOCUS_CIZ_SPECS,
                        "last_toast": session.last_toast,
                    })
                    return
                if path == "/api/shotmark_and_iris":
                    self._send_json({
                        "ok": True,
                        "shotmark_and_iris": session.get_shotmark_and_iris(),
                        "specs": SHOTMARK_IRIS_SPECS,
                        "last_toast": session.last_toast,
                    })
                    return
                if path == "/api/gyroflow_anamorphic":
                    self._send_json({
                        "ok": True,
                        "gyroflow_anamorphic": session.get_gyroflow_anamorphic(),
                        "specs": GYROFLOW_ANAMORPHIC_SPECS,
                        "last_toast": session.last_toast,
                    })
                    return
                if path == "/api/interval_cache_lut_ftp":
                    self._send_json({
                        "ok": True,
                        "interval_cache_lut_ftp": session.get_interval_cache_lut_ftp(),
                        "specs": INTERVAL_CACHE_LUT_FTP_SPECS,
                        "last_toast": session.last_toast,
                    })
                    return
                if path == "/api/mc_fleet_sdi_c2pa":
                    self._send_json({
                        "ok": True,
                        "mc_fleet_sdi_c2pa": session.get_mc_fleet_sdi_c2pa(),
                        "specs": MC_FLEET_SDI_C2PA_SPECS,
                        "last_toast": session.last_toast,
                    })
                    return
                if path == "/api/hdr_hlg_raw_breathing":
                    self._send_json({
                        "ok": True,
                        "hdr_hlg_raw_breathing": session.get_hdr_hlg_raw_breathing(),
                        "specs": HDR_HLG_RAW_BREATHING_SPECS,
                        "last_toast": session.last_toast,
                    })
                    return
                if path == "/api/uvc_srt_crsdk_ptp":
                    self._send_json({
                        "ok": True,
                        "uvc_srt_crsdk_ptp": session.get_uvc_srt_crsdk_ptp(),
                        "specs": UVC_SRT_CRSDK_PTP_SPECS,
                        "last_toast": session.last_toast,
                    })
                    return
                if path == "/api/scope_stats":
                    refresh = qs.get("refresh", ["0"])[0].strip().lower() in ("1", "true", "yes")
                    self._send_json(session.get_scope_stats(refresh=refresh))
                    return
                if path in ("/api/frame.png", "/api/gpe0.png", "/frame.png"):
                    png, _ = session.capture_live_gpe0() if session.live_ready else (session.last_png, session.last_nz)
                    self._send_bytes(png, "image/png", status=HTTPStatus.OK)
                    return
                self._safe_send_error(HTTPStatus.NOT_FOUND)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, TimeoutError, socket.timeout, OSError) as exc:
                if _is_client_disconnect_exc(exc):
                    self._record_disconnect()
                    return
                raise

        def do_POST(self) -> None:
            try:
                parsed = urllib.parse.urlparse(self.path)
                path = parsed.path
                qs = urllib.parse.parse_qs(parsed.query)

                try:
                    length = max(0, int(self.headers.get("Content-Length", "0")))
                except ValueError:
                    self._send_json(
                        {"ok": False, "error": "invalid_content_length", "message": "Invalid Content-Length header"},
                        status=HTTPStatus.BAD_REQUEST,
                    )
                    return
                raw_body = self.rfile.read(length) if length > 0 else b"{}"
                json_err = False
                try:
                    body = json.loads(raw_body.decode("utf-8")) if raw_body else {}
                except Exception:
                    body = {}
                    json_err = True

                if json_err and path in (
                    "/api/lut_upload",
                    "/api/upload_cube_lut",
                    "/api/preset_import",
                    "/api/camset_import",
                    "/api/cinema_param",
                    "/api/cine_exposure",
                    "/api/color_and_media",
                    "/api/jump_page",
                    "/api/verify_multilang_diff",
                    "/api/assist_tools",
                    "/api/touch_focus_ciz",
                    "/api/shotmark_and_iris",
                    "/api/gyroflow_anamorphic",
                    "/api/interval_cache_lut_ftp",
                    "/api/mc_fleet_sdi_c2pa",
                    "/api/hdr_hlg_raw_breathing",
                    "/api/uvc_srt_crsdk_ptp",
                ):
                    self._send_json(
                        {"ok": False, "error": "invalid_json", "message": "Malformed JSON request body"},
                        status=HTTPStatus.BAD_REQUEST,
                    )
                    return

                if not isinstance(body, dict):
                    self._send_json(
                        {"ok": False, "error": "invalid_json_object", "message": "JSON body must be an object"},
                        status=HTTPStatus.BAD_REQUEST,
                    )
                    return

                # Support legacy query parameters from older browser tabs
                if "name" in qs and "key" not in body:
                    body["key"] = qs["name"][0]
                if "key" in qs and "key" not in body:
                    body["key"] = qs["key"][0]
                if "page" in qs and "page" not in body:
                    body["page"] = qs["page"][0]
                if "idx" in qs and "sel_box" not in body:
                    body["sel_box"] = int(qs["idx"][0])
                if "lang" in qs and "lang" not in body:
                    body["lang"] = qs["lang"][0]
                if "button" in qs and "button" not in body:
                    body["button"] = qs["button"][0]
                if "param" in qs and "param" not in body:
                    body["param"] = qs["param"][0]
                if "delta" in qs and "delta" not in body:
                    body["delta"] = qs["delta"][0]
                if "preset" in qs and "preset" not in body:
                    body["preset"] = qs["preset"][0]
                if "page_id" in qs and "page_id" not in body:
                    body["page_id"] = qs["page_id"][0]
                if "idx128" in qs and "idx128" not in body:
                    body["idx128"] = qs["idx128"][0]
                if "q" in qs and "q" not in body and "query" not in body:
                    body["q"] = qs["q"][0]
                if "query" in qs and "query" not in body:
                    body["query"] = qs["query"][0]
                if "category" in qs and "category" not in body:
                    body["category"] = qs["category"][0]

                if path in ("/api/start", "/api/vm/start"):
                    res = session.start_vm()
                    self._send_json({"ok": True, "result": res, "status": session.get_status()})
                    return
                if path in ("/api/stop", "/api/vm/stop"):
                    res = session.stop_vm()
                    self._send_json({"ok": True, "result": res, "status": session.get_status()})
                    return
                if path == "/api/refresh":
                    session.capture_live_gpe0()
                    self._send_json({"ok": True, "status": session.get_status()})
                    return
                if path == "/api/lang":
                    res = session.set_lang(body.get("lang", ""))
                    self._send_json(res, status=HTTPStatus.OK if res.get("ok") else HTTPStatus.BAD_REQUEST)
                    return
                if path == "/api/fx3_button":
                    res = session.press_fx3_button(body.get("button", ""))
                    self._send_json(res, status=HTTPStatus.OK if res.get("ok") else HTTPStatus.BAD_REQUEST)
                    return
                if path == "/api/cinema_param":
                    res = session.set_cinema_param(
                        body.get("param", ""),
                        delta=body.get("delta"),
                        preset=body.get("preset"),
                        payload=body,
                    )
                    self._send_json(res, status=HTTPStatus.OK if res.get("ok") else HTTPStatus.BAD_REQUEST)
                    return
                if path == "/api/cine_exposure":
                    res = session.set_cine_exposure(body)
                    self._send_json(res, status=HTTPStatus.OK if res.get("ok") else HTTPStatus.BAD_REQUEST)
                    return
                if path == "/api/color_and_media":
                    res = session.set_color_and_media(body)
                    self._send_json(res, status=HTTPStatus.OK if res.get("ok") else HTTPStatus.BAD_REQUEST)
                    return
                if path in ("/api/lut_upload", "/api/upload_cube_lut"):
                    res = session.upload_cube_lut(body)
                    self._send_json(res, status=HTTPStatus.OK if res.get("ok") else HTTPStatus.BAD_REQUEST)
                    return
                if path in ("/api/preset_import", "/api/camset_import"):
                    res = session.import_camset_preset(body)
                    self._send_json(res, status=HTTPStatus.OK if res.get("ok") else HTTPStatus.BAD_REQUEST)
                    return
                if path == "/api/assist_tools":
                    res = session.set_assist_tools(body)
                    self._send_json(res, status=HTTPStatus.OK if res.get("ok") else HTTPStatus.BAD_REQUEST)
                    return
                if path == "/api/touch_focus_ciz":
                    res = session.set_touch_focus_ciz(body)
                    self._send_json(res, status=HTTPStatus.OK if res.get("ok") else HTTPStatus.BAD_REQUEST)
                    return
                if path == "/api/shotmark_and_iris":
                    res = session.set_shotmark_and_iris(body)
                    self._send_json(res, status=HTTPStatus.OK if res.get("ok") else HTTPStatus.BAD_REQUEST)
                    return
                if path == "/api/gyroflow_anamorphic":
                    res = session.set_gyroflow_anamorphic(body)
                    self._send_json(res, status=HTTPStatus.OK if res.get("ok") else HTTPStatus.BAD_REQUEST)
                    return
                if path == "/api/interval_cache_lut_ftp":
                    res = session.set_interval_cache_lut_ftp(body)
                    self._send_json(res, status=HTTPStatus.OK if res.get("ok") else HTTPStatus.BAD_REQUEST)
                    return
                if path == "/api/mc_fleet_sdi_c2pa":
                    res = session.set_mc_fleet_sdi_c2pa(body)
                    self._send_json(res, status=HTTPStatus.OK if res.get("ok") else HTTPStatus.BAD_REQUEST)
                    return
                if path == "/api/hdr_hlg_raw_breathing":
                    res = session.set_hdr_hlg_raw_breathing(body)
                    self._send_json(res, status=HTTPStatus.OK if res.get("ok") else HTTPStatus.BAD_REQUEST)
                    return
                if path == "/api/uvc_srt_crsdk_ptp":
                    res = session.set_uvc_srt_crsdk_ptp(body)
                    self._send_json(res, status=HTTPStatus.OK if res.get("ok") else HTTPStatus.BAD_REQUEST)
                    return
                if path == "/api/jump_page":
                    res = session.jump_to_page(body)
                    self._send_json(res, status=HTTPStatus.OK if res.get("ok") else HTTPStatus.BAD_REQUEST)
                    return
                if path == "/api/verify_multilang_diff":
                    raw_page = body.get("page")
                    page_arg: int | None = None
                    if isinstance(raw_page, bool):
                        self._send_json(
                            {"ok": False, "error": "invalid_page", "message": "page cannot be bool"},
                            status=HTTPStatus.BAD_REQUEST,
                        )
                        return
                    if raw_page is not None and str(raw_page).strip() != "":
                        try:
                            page_arg = int(raw_page)
                        except (TypeError, ValueError):
                            self._send_json(
                                {"ok": False, "error": "invalid_page", "message": f"Invalid page: {raw_page!r}"},
                                status=HTTPStatus.BAD_REQUEST,
                            )
                            return
                    res = session.verify_multilang_diff(page=page_arg)
                    if res.get("ok"):
                        st_code = HTTPStatus.OK
                    elif res.get("error") == "vm_not_ready":
                        st_code = HTTPStatus.CONFLICT
                    else:
                        st_code = HTTPStatus.BAD_REQUEST
                    self._send_json(res, status=st_code)
                    return
                if path in ("/api/key", "/api/page", "/api/box"):
                    res = session.apply_key_or_state(body)
                    self._send_json(res)
                    return
                self._safe_send_error(HTTPStatus.NOT_FOUND)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, TimeoutError, socket.timeout, OSError) as exc:
                if _is_client_disconnect_exc(exc):
                    self._record_disconnect()
                    return
                raise

    return Handler


def main() -> int:
    parser = argparse.ArgumentParser(description="Sony FX6 Authentic In-Guest GPE0 Menu Runner")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument(
        "--workdir",
        "--work-dir",
        dest="workdir",
        type=Path,
        default=None,
        help="Runtime workdir (defaults to port-scoped /private/tmp/fx6-live-gpe0-run[-<port>])",
    )
    parser.add_argument("--check", action="store_true", help="Verify manifest and payload paths without starting VM")
    args = parser.parse_args()

    if args.check:
        if not MANIFEST_PATH.exists():
            raise SystemExit(f"Missing manifest: {MANIFEST_PATH}")
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        resolved_paths: dict[str, str] = {}
        for key in ("kernel", "initrd", "dtb", "backup"):
            p = Path(_relocate_migrated_path(manifest[key]["path"]))
            if not p.exists():
                raise SystemExit(f"Missing {key}: {p}")
            resolved_paths[key] = str(p)
        print(json.dumps({"ok": True, "manifest": str(MANIFEST_PATH), "resolved": resolved_paths}, ensure_ascii=False))
        return 0

    workdir = resolve_port_scoped_workdir(args.port, args.workdir)
    session = FX6LiveGpe0Session(workdir, port=args.port)

    print(f"[FX6-LIVE-GPE0] Auto-starting FX3 QEMU VM with FX6 native UI controller (live700, port={args.port}, workdir={workdir})...")
    start_info = session.start_vm()
    print(f"[FX6-LIVE-GPE0] QEMU started: {start_info}")

    server = HardenedThreadingHTTPServer(("127.0.0.1", args.port), make_handler(session))
    url = f"http://127.0.0.1:{args.port}/"
    print(f"[FX6-LIVE-GPE0] Listening on {url}")

    def _on_sigterm(_signum: int, _frame: Any) -> None:
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, _on_sigterm)

    if not args.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        session.stop_vm()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
