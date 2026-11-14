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
    """Generate a deterministic, standard R-fastest Adobe .cube 3D LUT string."""
    key = str(preset_id or "").strip()
    if key not in BUILTIN_CUBE_PRESETS:
        raise ValueError(f"Unknown built-in .cube preset: {preset_id!r}")
    n = int(size)
    if n not in (2, 17, 33):
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
) -> dict[str, Any]:
    """Strictly validate and sanitize Adobe `.cube` 3D LUT text fail-closed before touching guest state."""
    if not isinstance(cube_text, str):
        return {"ok": False, "error": "invalid_cube_type", "message": "cube_text must be a UTF-8 string"}
    if not cube_text.strip():
        return {"ok": False, "error": "empty_cube_payload", "message": "Empty .cube payload"}
    if "\x00" in cube_text or any((ord(c) < 32 and c not in "\n\r\t") or ord(c) == 127 for c in cube_text):
        return {"ok": False, "error": "control_characters_forbidden", "message": "Control or NUL bytes in .cube payload"}
    raw_bytes = cube_text.encode("utf-8", errors="strict")
    if len(raw_bytes) > 2 * 1024 * 1024:
        return {"ok": False, "error": "cube_payload_too_large", "message": ".cube payload exceeds 2 MiB safety limit"}

    req_name = str(name or "").strip()
    if req_name and _is_unsafe_lut_label(req_name):
        return {"ok": False, "error": "unsafe_lut_name", "message": "LUT name contains forbidden path/control characters"}

    lines = cube_text.splitlines()
    if len(lines) > 40000:
        return {"ok": False, "error": "too_many_lines", "message": ".cube exceeds 40,000 lines safety limit"}

    allowed_sizes = {17, 33}
    if allow_mini_grid:
        allowed_sizes.add(2)

    lut_size: int | None = None
    domain_min: list[float] | None = None
    domain_max: list[float] | None = None
    title = ""
    triplets: list[tuple[float, float, float]] = []
    clamped_components = 0
    seen_data = False

    for line_no, raw_ln in enumerate(lines, start=1):
        ln = raw_ln.strip()
        if not ln or ln.startswith("#"):
            continue
        if "#" in ln:
            ln = ln.split("#", 1)[0].strip()
            if not ln:
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
        cr, cg, cb = _clamp01(r_v), _clamp01(g_v), _clamp01(b_v)
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

    canonical_lines = [
        f'TITLE "{safe_name}"',
        f"LUT_3D_SIZE {lut_size}",
        f"DOMAIN_MIN {dmin[0]:.6f} {dmin[1]:.6f} {dmin[2]:.6f}",
        f"DOMAIN_MAX {dmax[0]:.6f} {dmax[1]:.6f} {dmax[2]:.6f}",
    ]
    canonical_lines.extend(f"{r:.6f} {g:.6f} {b:.6f}" for (r, g, b) in triplets)
    canonical_text = "\n".join(canonical_lines) + "\n"
    sha256 = hashlib.sha256(canonical_text.encode("utf-8")).hexdigest()

    in_r = (0.5 - dmin[0]) / (dmax[0] - dmin[0])
    in_g = (0.5 - dmin[1]) / (dmax[1] - dmin[1])
    in_b = (0.5 - dmin[2]) / (dmax[2] - dmin[2])
    mr, mg, mb = _trilinear_cube_sample(triplets, lut_size, in_r, in_g, in_b)
    r8 = max(0, min(255, int(round(mr * 255.0))))
    g8 = max(0, min(255, int(round(mg * 255.0))))
    b8 = max(0, min(255, int(round(mb * 255.0))))

    return {
        "ok": True,
        "name": safe_name,
        "title": title or safe_name,
        "size": lut_size,
        "triplets": expected,
        "clamped_components": clamped_components,
        "domain_min": dmin,
        "domain_max": dmax,
        "sha256": sha256,
        "mid_gray_rgb": [round(mr, 6), round(mg, 6), round(mb, 6)],
        "tint_rgb8": [r8, g8, b8],
        "tint_hex": f"#{r8:02x}{g8:02x}{b8:02x}",
    }


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
        self.user_lut_slots: dict[str, dict[str, Any]] = self._default_user_lut_slots()
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
                "uploaded": False,
                "preset": None,
                "size": 33,
                "triplets": 33 ** 3,
                "sha256": None,
                "mid_gray_rgb": [0.5, 0.5, 0.5],
                "tint_rgb8": [128, 128, 128],
                "tint_hex": "#808080",
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
        p40_flags_word = (
            (1 if self.xlr_handle_attached else 0)
            | ((1 if (self.xlr_handle_attached and self.xlr_phantom_48v) else 0) << 1)
            | ((rtmd_idx & 0x3) << 4)
            | (1 << 8)
            | (1 << 9)
        )
        ext_raw = struct.pack("<I6III", lut_meta_word, *name_words, audio_packed_word, p40_flags_word)
        raw = struct.pack("<18I", *words) + struct.pack("<I", p11_state_word) + ext_raw
        return raw

    def _write_ctrl_mailbox(self) -> bool:
        """Write mb[0..27] to guest physical 0x41e000e00 via serialized QEMU GDB stub and always resume VCPUs."""
        if not self.is_running() or not self.gdb_sock.exists() or not self.live_ready or self.crashed:
            return False
        raw = self._pack_mailbox_bytes()
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
                    self.last_toast = f"{spec['label']}: {presets[new_idx]} ({spec['contract']})"
                elif key == "ibis":
                    self.ibis_idx = new_idx
                    self.rtmd_0xe304_ibis_lock = RTMD_0XE304_MODES[new_idx % len(RTMD_0XE304_MODES)]
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
        """Validate/sanitize `.cube` 3D LUT fail-closed, store into User1..User4, and sync guest GPE0."""
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
            if size_int not in ({2, 17, 33} if allow_mini_grid else {17, 33}):
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

        sanitized = validate_and_sanitize_cube_lut(cube_text, name=req_name, allow_mini_grid=allow_mini_grid)
        if not sanitized["ok"]:
            return sanitized

        slot_record = {
            "slot": slot,
            "name": sanitized["name"],
            "title": sanitized["title"],
            "uploaded": True,
            "preset": str(preset_id).strip() if preset_id else None,
            "size": sanitized["size"],
            "triplets": sanitized["triplets"],
            "clamped_components": sanitized["clamped_components"],
            "domain_min": sanitized["domain_min"],
            "domain_max": sanitized["domain_max"],
            "sha256": sanitized["sha256"],
            "mid_gray_rgb": sanitized["mid_gray_rgb"],
            "tint_rgb8": sanitized["tint_rgb8"],
            "tint_hex": sanitized["tint_hex"],
        }

        with self.cmd_lock:
            self.user_lut_slots[slot] = slot_record
            cell_idx = USER_LUT_SLOT_TO_CELL_IDX[slot]
            self.cell_vals[4] = cell_idx
            if self.page in (0, 3):
                self.sel_box = 4
            self.last_toast = (
                f"{slot} .cube Imported: {slot_record['name']} ({slot_record['size']}³, "
                f"tint={slot_record['tint_hex']}, sha={slot_record['sha256'][:12]})"
            )
            wrote, synced = self._sync_mailbox_and_capture()
            return {
                "ok": True,
                "slot": slot,
                "lut_index": cell_idx,
                "lut": dict(slot_record),
                "toast": self.last_toast,
                "wrote_mailbox": wrote,
                "guest_synced": synced,
                "cinema_params": self.get_cinema_params(),
                "status": self.get_status(),
            }

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
        """Validate & apply `fx6_on_fx3_camset_v1` while enforcing P4 ND=Clear & P12 BK4 Airplane-Mode locks."""
        if not isinstance(payload, dict):
            return {"ok": False, "error": "invalid_camset_payload", "message": "CAMSET payload must be a JSON object"}
        if payload.get("schema") != "fx6_on_fx3_camset_v1":
            return {
                "ok": False,
                "error": "invalid_camset_schema",
                "message": f"Expected schema 'fx6_on_fx3_camset_v1', got {payload.get('schema')!r}",
            }

        cparams = payload.get("cinema_params")
        if cparams is None:
            cparams = {}
        if not isinstance(cparams, dict):
            return {"ok": False, "error": "invalid_cinema_params", "message": "cinema_params must be a JSON object"}

        # Detect any P4 ND tamper attempts across cinema_params or top-level keys
        nd_tamper_val = None
        for cand_nd in (cparams.get("nd"), payload.get("nd"), payload.get("nd_filter"), payload.get("variable_nd")):
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
        raw_slots = payload.get("user_lut_slots")
        if isinstance(raw_slots, dict):
            for skey, sdata in raw_slots.items():
                norm_s = self._normalize_lut_slot(skey)
                if norm_s is None or not isinstance(sdata, dict):
                    continue
                if "cube_text" in sdata and isinstance(sdata["cube_text"], str):
                    san = validate_and_sanitize_cube_lut(sdata["cube_text"], name=str(sdata.get("name", norm_s)))
                    if not san["ok"]:
                        return san
                    new_slots[norm_s] = {
                        "slot": norm_s,
                        "name": san["name"],
                        "title": san["title"],
                        "uploaded": True,
                        "preset": sdata.get("preset"),
                        "size": san["size"],
                        "triplets": san["triplets"],
                        "clamped_components": san["clamped_components"],
                        "domain_min": san["domain_min"],
                        "domain_max": san["domain_max"],
                        "sha256": san["sha256"],
                        "mid_gray_rgb": san["mid_gray_rgb"],
                        "tint_rgb8": san["tint_rgb8"],
                        "tint_hex": san["tint_hex"],
                    }
                else:
                    rgb8 = sdata.get("tint_rgb8", [128, 128, 128])
                    if not (isinstance(rgb8, list) and len(rgb8) == 3):
                        rgb8 = [128, 128, 128]
                    rgb8_clean = [max(0, min(255, int(x))) for x in rgb8]
                    safe_n = str(sdata.get("name", f"{norm_s} .cube"))[:23]
                    if _is_unsafe_lut_label(safe_n):
                        return {"ok": False, "error": "unsafe_lut_name", "message": "Unsafe LUT name in CAMSET"}
                    new_slots[norm_s] = {
                        "slot": norm_s,
                        "name": safe_n,
                        "title": safe_n,
                        "uploaded": bool(sdata.get("uploaded", False)),
                        "preset": sdata.get("preset"),
                        "size": int(sdata.get("size", 33)) if int(sdata.get("size", 33)) in (2, 17, 33) else 33,
                        "triplets": int(sdata.get("triplets", 33 ** 3)),
                        "sha256": sdata.get("sha256"),
                        "mid_gray_rgb": sdata.get("mid_gray_rgb", [0.5, 0.5, 0.5]),
                        "tint_rgb8": rgb8_clean,
                        "tint_hex": f"#{rgb8_clean[0]:02x}{rgb8_clean[1]:02x}{rgb8_clean[2]:02x}",
                    }

        p12_clamped = payload.get("p12_bk4_airplane_mode_locked") is False

        with self.cmd_lock:
            for c_idx, c_val in new_cells.items():
                self.cell_vals[c_idx] = c_val
            self.cell_vals[3] = 0  # P4 ND=Clear Hardware Lock always enforced!
            p4_rejected = nd_tamper_val is not None
            if p4_rejected:
                self.p4_nd_reject_count += 1
                self.p4_lock_attempts += 1

            for skey, srec in new_slots.items():
                self.user_lut_slots[skey] = srec

            if new_rtmd is not None:
                self.rtmd_0xe304_ibis_lock = new_rtmd
                self.ibis_idx = RTMD_0XE304_MODES.index(new_rtmd)

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

            if p4_rejected:
                self.last_toast = (
                    f"P4 ND=Clear Lock Enforced: rejected ND={nd_tamper_val!r} in CAMSET "
                    f"(p4_nd_reject_count={self.p4_nd_reject_count})"
                )
            elif p12_clamped:
                self.last_toast = "CAMSET Imported (P12 BK4 Airplane-Mode shadow lock preserved)"
            else:
                self.last_toast = "CAMSET fx6_on_fx3_camset_v1 Imported & Applied"

            wrote, synced = self._sync_mailbox_and_capture()
            return {
                "ok": True,
                "schema": "fx6_on_fx3_camset_v1",
                "p4_nd_rejected": p4_rejected,
                "p4_nd_clamped": p4_rejected,
                "p4_nd_reject_count": self.p4_nd_reject_count,
                "p4_lock_attempts": self.p4_lock_attempts,
                "p12_bk4_airplane_mode_locked": True,
                "p12_bk4_clamped": p12_clamped,
                "toast": self.last_toast,
                "wrote_mailbox": wrote,
                "guest_synced": synced,
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

  if (forceImg || st.live_ready) {
    document.getElementById('gpe0-img').src = '/api/frame.png?t=' + Date.now();
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

function onScreenClick(e) {
  const wrap = document.getElementById('screen-wrap');
  const rect = wrap.getBoundingClientRect();
  const x = ((e.clientX - rect.left) / rect.width) * 1024;
  const y = ((e.clientY - rect.top) / rect.height) * 540;
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

loadPages128();
loadMenuCatalog();
setInterval(pollStatus, 1500);
pollStatus();
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

        def _send_bytes(self, raw: bytes, content_type: str, status: int = 200) -> bool:
            try:
                self.send_response(int(status))
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(raw)))
                self.send_header("Cache-Control", "no-store")
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
                if path == "/api/lut_upload":
                    self._send_json(session.get_lut_slots())
                    return
                if path == "/api/preset_export":
                    self._send_json(session.export_camset_preset())
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
                    "/api/preset_import",
                    "/api/cinema_param",
                    "/api/jump_page",
                    "/api/verify_multilang_diff",
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
                if path == "/api/lut_upload":
                    res = session.upload_cube_lut(body)
                    self._send_json(res, status=HTTPStatus.OK if res.get("ok") else HTTPStatus.BAD_REQUEST)
                    return
                if path == "/api/preset_import":
                    res = session.import_camset_preset(body)
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
