"""Phase 46 — `global.xdb` UX Database Inspector & 128-Page FX6-on-FX3 Multilingual Menu Tree Completeness Auditor.

Strictly Read-Only (`os.O_RDONLY`) & Clean-Room Dual-Mode:
- Local Donor Mode: opens FX6 v6.01 and FX3 v7.02 `global.xdb` (`uxa\\x07`),
  `lang.uxb` (`uxb\\x07`), `fontlist.dat`, `.uxc`/`.uxd` string & common packs,
  and FX6 `appFw.so` strictly via `os.O_RDONLY` (and `mmap(..., ACCESS_READ)` for
  large ELF64 descriptor tables). Any SQLite3 UX DB passed for inspection is
  opened exclusively via `file:<path>?mode=ro&immutable=1` (`uri=True`) so
  `-wal`/`-shm`/journal files are never created in donor directories.
- Clean-Room Mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`, `clean_room=True`, or donors
  absent): synthesizes deterministic `uxa\\x07` `global.xdb`, `uxb\\x07` `lang.uxb`,
  `fontlist.dat`, sparse-slot `.uxc` string/common packs across `EN`, `Simplified
  Chinese`, `Traditional Chinese`, and `Japanese`, and an ELF64 `appFw.so` image
  carrying all 128 descriptor tables (`2,224` rows) so the exact same parser and
  auditor pipeline executes end-to-end.

Audits three pillars:
1. `global.xdb` & UX Resource Config Table Integrity (`FX6 v6.01` & `FX3 v7.02`).
2. 11-Category / 128-Page Multilingual Menu Tree (`Big-6 Home`, `Page 110`
   Assignable Buttons, and all `128` descriptor tables) across `EN`, `ZH-CN`,
   `ZH-TW`, and `JA` (`0` missing/corrupt UTF-8 labels, `0` null prototypes).
3. FX3 Hardware-Predicate Safety (`P4` Variable ND -> `LOCKED_CLEAR`, `12G-SDI` ->
   `HDMI_FALLBACK`, `Smart Grip/Handle Zoom` detached -> `INTERNAL_MIC_FALLBACK`,
   `WLAN` `P12` Airplane-gated -> `AIRPLANE_ISOLATED`, and `P10` Assignable
   Buttons `Page 110`).
"""

from __future__ import annotations

import hashlib
import mmap
import os
import re
import sqlite3
import struct
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

from .haita_bk4_feature_analyzer import (
    DEFAULT_REPO_ROOT,
    FX6_APPFW_RELPATH,
    is_forced_clean_room,
    read_bytes_rdonly,
    resolve_donor_file,
)
from .uxc_ldec_inspector import (
    UXC_HEADER_STRUCT,
    UXC_MAGIC,
    UXD_MAGIC,
)
from .uxc_multilang_and_font_verifier import (
    FX3_SHARE_APP_RELDIR,
    FX6_SHARE_APP_RELDIR,
    PRIMARY_CJK_EN_LANGUAGES,
    parse_uxc_string_pack_slots,
)


PHASE_46_SCHEMA = "fx3_firmware_lab_phase46_global_xdb_menu_tree_v1"
PHASE_46_VERSION = "46.0.0"

UXA_MAGIC = b"uxa\x07"
UXB_MAGIC = b"uxb\x07"
SQLITE_MAGIC = b"SQLite format 3\x00"

ELF_MAGIC = b"\x7fELF"
ELF64_EHDR_STRUCT = struct.Struct("<16sHHIQQQIHHHHHH")
ELF64_PHDR_STRUCT = struct.Struct("<IIQQQQQQ")
PT_LOAD = 1
DESC_STRIDE = 0x48

TARGET_LANGUAGES: Tuple[str, ...] = PRIMARY_CJK_EN_LANGUAGES  # english, simplifiedchinese, traditionalchinese, japanese

FX6_LANGUAGE_SLUGS_29: Tuple[str, ...] = (
    "arabic",
    "brazilianportuguese",
    "czech",
    "danish",
    "dutch",
    "english",
    "finnish",
    "french",
    "german",
    "greek",
    "hindi",
    "hungarian",
    "indonesia",
    "italian",
    "japanese",
    "korean",
    "malay",
    "norwegian",
    "persian",
    "polish",
    "portuguese",
    "russian",
    "simplifiedchinese",
    "spanish",
    "swedish",
    "thai",
    "traditionalchinese",
    "turkish",
    "ukrainian",
)

# 11 Level-1 Menu Categories in FX6 Cinema Line Menu Tree
FX6_11_CATEGORIES: Tuple[Tuple[int, str, int, Tuple[int, ...], Dict[str, str]], ...] = (
    (0, "User", 0x02004208, (0x02004294, 0x02004D4A, 0x02004264, 0x02004286, 0x02004257, 0x020023C2),
     {"english": "User", "simplifiedchinese": "用户", "traditionalchinese": "用戶", "japanese": "User"}),
    (1, "Edit User Menu", 0x02004D4A, (0x02004D4B, 0x02004294, 0x02004D4A, 0x02004286, 0x02004264),
     {"english": "Edit User Menu", "simplifiedchinese": "编辑用户菜单", "traditionalchinese": "編輯用戶功能表", "japanese": "User Menu編集"}),
    (2, "Shooting", 0x02002227, (0x020023C2, 0x020023BD, 0x0200215D, 0x020050E8, 0x02005689, 0x020023AA, 0x020023B2),
     {"english": "Shooting", "simplifiedchinese": "拍摄", "traditionalchinese": "拍攝", "japanese": "Shooting"}),
    (3, "Project", 0x02002228, (0x020023F8, 0x0200425F, 0x02004261, 0x02004264, 0x0200425A, 0x02004257, 0x02004286),
     {"english": "Project", "simplifiedchinese": "项目", "traditionalchinese": "專案", "japanese": "Project"}),
    (4, "Paint/Look", 0x02002493, (0x020023F8, 0x02002464, 0x02002460, 0x020021A0, 0x0200219E, 0x020023F1, 0x020023F5),
     {"english": "Paint/Look", "simplifiedchinese": "绘图/风格", "traditionalchinese": "繪製/外觀", "japanese": "Paint/Look"}),
    (5, "TC/Media", 0x0200222B, (0x02004242, 0x02004243, 0x02004244, 0x02004245, 0x02002244, 0x02004253, 0x02004254),
     {"english": "TC/Media", "simplifiedchinese": "TC/媒体", "traditionalchinese": "TC/媒體", "japanese": "TC/Media"}),
    (6, "Monitoring", 0x02002229, (0x02004238, 0x02004236, 0x02004235, 0x02004234, 0x02004239, 0x0200423A, 0x02004241),
     {"english": "Monitoring", "simplifiedchinese": "监看", "traditionalchinese": "監控", "japanese": "Monitoring"}),
    (7, "Audio", 0x020041FB, (0x02004232, 0x02004233, 0x02004234, 0x02002192, 0x02002191, 0x02003132, 0x0200429F),
     {"english": "Audio", "simplifiedchinese": "音频", "traditionalchinese": "音訊", "japanese": "Audio"}),
    (8, "Thumbnail", 0x02004209, (0x02004209, 0x02004FF3, 0x0200410D, 0x020028E8, 0x020042C7, 0x02004FDD, 0x02004FF8),
     {"english": "Thumbnail", "simplifiedchinese": "缩略图", "traditionalchinese": "縮圖", "japanese": "Thumbnail"}),
    (9, "Technical", 0x0200222A, (0x0200420E, 0x020050E8, 0x02004285, 0x02004212, 0x02004211, 0x02005689, 0x02004229),
     {"english": "Technical", "simplifiedchinese": "技术", "traditionalchinese": "技術", "japanese": "Technical"}),
    (10, "Maintenance", 0x02004203, (0x0200426B, 0x0200426C, 0x0200426D, 0x0200426E, 0x0200426F, 0x02004270, 0x02004291),
     {"english": "Maintenance", "simplifiedchinese": "维护", "traditionalchinese": "維護", "japanese": "Maintenance"}),
)

BIG6_HOME_PAGE_INDEX = 21
BIG6_HOME_BASE_VA = 0x02E9E210
BIG6_HOME_ROW_COUNT = 98

BIG6_CELL_TITLES: Tuple[Tuple[int, str, int, Dict[str, str]], ...] = (
    (0, "FPS", 0x02005082, {"english": "FPS", "simplifiedchinese": "FPS", "traditionalchinese": "FPS", "japanese": "FPS"}),
    (1, "EI / Base ISO", 0x02004C32, {"english": "ISO/Gain", "simplifiedchinese": "ISO/增益", "traditionalchinese": "ISO/增益", "japanese": "ISO/Gain"}),
    (2, "Shutter", 0x020050E8, {"english": "Shutter", "simplifiedchinese": "快门", "traditionalchinese": "快門", "japanese": "シャッター"}),
    (3, "ND Filter", 0x02004288, {"english": "ND Filter", "simplifiedchinese": "ND滤镜", "traditionalchinese": "ND篩選器", "japanese": "NDフィルター"}),
    (4, "Base Look / 3D LUT", 0x020023F8, {"english": "Base Look", "simplifiedchinese": "基本风格", "traditionalchinese": "基本外觀", "japanese": "基本Look"}),
    (5, "White Balance", 0x02005689, {"english": "White Balance", "simplifiedchinese": "白平衡", "traditionalchinese": "白平衡", "japanese": "ホワイトバランス"}),
)

ASSIGNABLE_PAGE_110_INDEX = 110
ASSIGNABLE_PAGE_110_BASE_VA = 0x02EB75F0
ASSIGNABLE_PAGE_110_ROW_COUNT = 54
ASSIGNABLE_PAGE_110_TITLE_RESID = 0x0200211E
ASSIGNABLE_PAGE_110_POOL: Tuple[int, ...] = (
    0x020023C4, 0x020020D0, 0x02004288, 0x0200423D, 0x0200423F, 0x0200423E,
    0x020049F5, 0x0200290A, 0x02004246, 0x0200425F, 0x02004261, 0x02004242,
    0x02004253, 0x02004254, 0x0200425A, 0x02002E6D, 0x02004214, 0x02004217,
    0x02004218, 0x02004285, 0x02004212, 0x02004211, 0x02004210, 0x02004229,
    0x0200422A, 0x02004239, 0x0200423A, 0x02004241, 0x0200429F, 0x02004285,
)

# All 128 FX6 Menu Page Descriptor Tables (page_idx, cat_group, base_va, row_count, first_name)
FX6_128_PAGE_DIRECTORY: Tuple[Tuple[int, int, int, int, str], ...] = (
    (0, 0, 0x02E90FB0, 7, "No33_touch"),
    (1, 1, 0x02E911F0, 14, "No2011_audio_level_meter"),
    (2, 2, 0x02E91628, 5, "No6_picture_size"),
    (3, 3, 0x02E917D8, 71, "No2010_gamma_display_assist"),
    (4, 3, 0x02E92C18, 102, "No142_BLOCK_TOUCH"),
    (5, 4, 0x02E94C28, 40, "No133_homemenu_clip_area"),
    (6, 5, 0x02E957B0, 5, "No2045_video_signal_monitor"),
    (7, 6, 0x02E959A8, 7, "No1066_base_look"),
    (8, 7, 0x02E95CC0, 20, "No2094_tracking_cancel_button"),
    (9, 8, 0x02E962A8, 11, "No16_resolution"),
    (10, 9, 0x02E96608, 253, "No4_recstate_string_slot_1st"),
    (11, 9, 0x02E9AD78, 35, "No423_BLOCK_TOUCH"),
    (12, 9, 0x02E9B798, 39, "No44_yuv_cover"),
    (13, 9, 0x02E9C2D8, 6, "No3_BG_MENU"),
    (14, 9, 0x02E9C4D0, 4, "No2_BG"),
    (15, 9, 0x02E9C638, 4, "No2_BG"),
    (16, 9, 0x02E9C7A0, 3, "No1_BG"),
    (17, 9, 0x02E9C8C0, 20, "No1_TRANS_BG"),
    (18, 9, 0x02E9CEF0, 46, "No43_yuv_cover"),
    (19, 9, 0x02E9DC28, 8, "No8_BLOCK_TOUCH"),
    (20, 9, 0x02E9DEB0, 11, "No17_TOUCH_SCREEN"),
    (21, 9, 0x02E9E210, 98, "No463_BLOCK_TOUCH"),
    (22, 9, 0x02E9FDE8, 3, "No2_enlargeareadebugdisplay"),
    (23, 9, 0x02E9FF08, 13, "No16_TOUCH_SCREEN"),
    (24, 9, 0x02EA02F8, 35, "No1_WID_NINEPATCHIMAGE_STAGE1_BG"),
    (25, 9, 0x02EA0D18, 69, "No69_TOUCH_SCREEN"),
    (26, 9, 0x02EA20C8, 23, "No23_TOUCH_SCREEN"),
    (27, 9, 0x02EA2788, 23, "No33_TOUCH_SCREEN"),
    (28, 9, 0x02EA2E48, 16, "No20_TOUCH"),
    (29, 9, 0x02EA3310, 14, "No20_TOUCH"),
    (30, 9, 0x02EA3748, 1, "No1_BG"),
    (31, 9, 0x02EA37D8, 10, "No18_TOUCH_SCREEN"),
    (32, 9, 0x02EA3AF0, 3, "No2_BG"),
    (33, 9, 0x02EA3C10, 2, "No2_BG"),
    (34, 9, 0x02EA3CE8, 2, "No2_BG"),
    (35, 9, 0x02EA3DC0, 1, "No1_BG"),
    (36, 9, 0x02EA3E50, 10, "No107_BLOCK_TOUCH"),
    (37, 9, 0x02EA4168, 6, "No2_BG"),
    (38, 9, 0x02EA4360, 5, "No1_TRANS_BG"),
    (39, 9, 0x02EA4510, 3, "No2_BG"),
    (40, 9, 0x02EA4630, 11, "No11_touchscreen"),
    (41, 9, 0x02EA4990, 33, "No26_TOUCH_SCREEN"),
    (42, 9, 0x02EA5320, 7, "No2_BG"),
    (43, 9, 0x02EA5560, 11, "No19_TOUCH_SCREEN"),
    (44, 9, 0x02EA58C0, 4, "No4_BLOCK_TOUCH"),
    (45, 9, 0x02EA5A28, 5, "No5_BLOCK_TOUCH"),
    (46, 9, 0x02EA5BD8, 5, "No6_BLOCK_TOUCH"),
    (47, 9, 0x02EA5D88, 6, "No7_BLOCK_TOUCH"),
    (48, 9, 0x02EA5F80, 7, "No7_BLOCK_TOUCH"),
    (49, 9, 0x02EA61C0, 7, "No8_BLOCK_TOUCH"),
    (50, 9, 0x02EA6400, 11, "No19_TOUCH"),
    (51, 9, 0x02EA6760, 12, "No17_TOUCH"),
    (52, 9, 0x02EA6B08, 19, "No26_TOUCH"),
    (53, 9, 0x02EA70A8, 13, "No19_TOUCH"),
    (54, 9, 0x02EA7498, 1, "No1_BG"),
    (55, 9, 0x02EA7528, 3, "No3_touch_screen"),
    (56, 9, 0x02EA7648, 176, "No48_TOUCH_SCREEN"),
    (57, 9, 0x02EAA810, 18, "No18_TOUCH_SCREEN"),
    (58, 9, 0x02EAAD68, 48, "No59_TOUCH_SCREEN"),
    (59, 9, 0x02EABB30, 3, "No2_BG"),
    (60, 9, 0x02EABC50, 4, "No2_EXECUTING_MESSAGE_BG"),
    (61, 9, 0x02EABDB8, 7, "No4_BG_2LINE"),
    (62, 9, 0x02EABFF8, 1, "No1_BG"),
    (63, 9, 0x02EAC088, 6, "No6_TOUCH_SCREEN"),
    (64, 9, 0x02EAC280, 34, "No26_TOUCH_SCREEN"),
    (65, 9, 0x02EACC58, 4, "No1_BG"),
    (66, 9, 0x02EACDC0, 10, "No12_TOUCH_SCREEN"),
    (67, 9, 0x02EAD0D8, 26, "No25_TOUCH_SCREEN"),
    (68, 9, 0x02EAD870, 55, "No48_TOUCH_SCREEN"),
    (69, 9, 0x02EAE830, 34, "No26_TOUCH_SCREEN"),
    (70, 9, 0x02EAF208, 17, "No107_BLOCK_TOUCH"),
    (71, 9, 0x02EAF718, 1, "No1_BG"),
    (72, 9, 0x02EAF7A8, 10, "No8_BLOCK_TOUCH"),
    (73, 9, 0x02EAFAC0, 10, "No10_TOUCH_SCREEN"),
    (74, 9, 0x02EAFDD8, 49, "No49_TOUCH_SCREEN"),
    (75, 9, 0x02EB0BE8, 3, "No2_BG"),
    (76, 9, 0x02EB0D08, 28, "No25_TOUCH_SCREEN"),
    (77, 9, 0x02EB1530, 11, "No13_TOUCH_SCREEN"),
    (78, 9, 0x02EB1890, 54, "No45_TOUCH_SCREEN"),
    (79, 9, 0x02EB2808, 9, "No7_TOUCH_SCREEN"),
    (80, 9, 0x02EB2AD8, 8, "No32_BG"),
    (81, 9, 0x02EB2D60, 10, "No8_BG"),
    (82, 9, 0x02EB3078, 4, "No6_BLOCK_TOUCH"),
    (83, 9, 0x02EB31E0, 5, "No6_BLOCK_TOUCH"),
    (84, 9, 0x02EB3390, 4, "No5_BLOCK_TOUCH"),
    (85, 9, 0x02EB34F8, 5, "No6_BLOCK_TOUCH"),
    (86, 9, 0x02EB36A8, 17, "No20_BG"),
    (87, 9, 0x02EB3BB8, 8, "No18_TOUCH_SCREEN"),
    (88, 9, 0x02EB3E40, 3, "No4_BG"),
    (89, 9, 0x02EB3F60, 3, "No2_NINEPATCHIMAGE_0"),
    (90, 9, 0x02EB4080, 8, "No7_TOUCH_SCREEN"),
    (91, 9, 0x02EB4308, 5, "No5_SETTING_LIST_BACKGROUND"),
    (92, 9, 0x02EB44B8, 19, "No30_TOUCH_SCREEN"),
    (93, 9, 0x02EB4A58, 12, "No11_BLOCK_TOUCH"),
    (94, 9, 0x02EB4E00, 19, "No30_TOUCH"),
    (95, 9, 0x02EB53A0, 28, "No25_TOUCH_SCREEN"),
    (96, 9, 0x02EB5BC8, 6, "No6_BLOCK_TOUCH"),
    (97, 9, 0x02EB5DC0, 7, "No12_BLOCK_TOUCH"),
    (98, 9, 0x02EB6000, 4, "No5_TOUCH"),
    (99, 9, 0x02EB6168, 5, "No9_TOUCH"),
    (100, 9, 0x02EB6318, 6, "No6_TOUCH"),
    (101, 9, 0x02EB6510, 7, "No7_TOUCH"),
    (102, 9, 0x02EB6750, 10, "No9_TOUCH"),
    (103, 9, 0x02EB6A68, 4, "No6_BG"),
    (104, 9, 0x02EB6BD0, 4, "No1_BG"),
    (105, 9, 0x02EB6D38, 5, "No1_BG"),
    (106, 9, 0x02EB6EE8, 5, "No5_BLOCK_TOUCH"),
    (107, 9, 0x02EB7098, 5, "No6_BLOCK_TOUCH"),
    (108, 9, 0x02EB7248, 5, "No6_BLOCK_TOUCH"),
    (109, 9, 0x02EB73F8, 6, "No7_BLOCK_TOUCH"),
    (110, 9, 0x02EB75F0, 54, "No32_TOUCH_SCREEN"),
    (111, 9, 0x02EB8568, 6, "No7_TOUCH_SCREEN_FOR_RELEASE"),
    (112, 9, 0x02EB8760, 11, "No11_TOUCH_SCREEN"),
    (113, 9, 0x02EB8AC0, 7, "No11_TOUCH_SCREEN"),
    (114, 9, 0x02EB8D00, 3, "No1_BG"),
    (115, 9, 0x02EB8E20, 9, "No8_TOUCH_SCREEN_FOR_RELEASE"),
    (116, 9, 0x02EB90F0, 10, "No15_TOUCH_SCREEN"),
    (117, 9, 0x02EB9408, 6, "No7_BLOCK_TOUCH"),
    (118, 9, 0x02EB9600, 4, "No8_TOUCH"),
    (119, 9, 0x02EB9768, 5, "No6_TOUCH"),
    (120, 9, 0x02EB9918, 4, "No4_TOUCH"),
    (121, 9, 0x02EB9A80, 6, "No6_BLOCK_TOUCH"),
    (122, 9, 0x02EB9C78, 8, "No11_TOUCH_SCREEN"),
    (123, 9, 0x02EB9F00, 5, "No5_TOUCH"),
    (124, 9, 0x02EBA0B0, 5, "No5_TOUCH"),
    (125, 9, 0x02EBA260, 10, "No11_TOUCH_SCREEN"),
    (126, 9, 0x02EBA578, 7, "No1_BG"),
    (127, 9, 0x02EBA7B8, 6, "No1_BUTTON_01"),
)

CURATED_SAMPLE_PAGE_INDICES: Tuple[int, ...] = (
    0, 1, 10, 11, 12, 18, 21, 24, 36, 43, 56, 58, 68, 70, 81, 110, 127
)

# Hardware Predicate Contracts: FX6-only physical menu items -> deterministic FX3 safe states
HARDWARE_PREDICATE_SPECS: Tuple[Dict[str, object], ...] = (
    {
        "predicate_id": "VARIABLE_ND",
        "patch_gate": "P4",
        "fx6_feature": "Optical Variable ND Auto/Preset",
        "fx3_safe_state": "LOCKED_CLEAR",
        "resids": (0x020020D3, 0x02002603, 0x02002604, 0x02002787),
        "appfw_marker": "set_nd_filter_mode_i",
        "notes": "ILME-FX3 lacks internal electronic e-ND; P4 forces ND=Clear with 0 NVRAM mutation.",
    },
    {
        "predicate_id": "SDI_12G_OUTPUT",
        "patch_gate": "P2+P5",
        "fx6_feature": "12G-SDI Output",
        "fx3_safe_state": "HDMI_FALLBACK",
        "resids": (0x02002246, 0x02002247, 0x02002249),
        "appfw_marker": "PRM_FEATURE_MANAGER_sdi_output",
        "notes": "FX3 routes video output via full-size HDMI / HDMI 16-bit RAW without blocking SDI probes.",
    },
    {
        "predicate_id": "SMART_GRIP_HANDLE_ZOOM",
        "patch_gate": "P3+P10+P11",
        "fx6_feature": "Smart Grip/Handle Zoom (Detached)",
        "fx3_safe_state": "INTERNAL_MIC_FALLBACK",
        "resids": (0x0200210B, 0x0200210C, 0x020023C6, 0x02004232),
        "appfw_marker": "INFRA_HOTSHOE_UIPC_SHOEINFO_EVT",
        "notes": "Detached XLR-H1 / Smart Handle falls back to Internal Stereo Mic & FX3 body buttons cleanly.",
    },
    {
        "predicate_id": "WLAN_AIRPLANE_GATE",
        "patch_gate": "P12",
        "fx6_feature": "WLAN (P12 Airplane-Gated)",
        "fx3_safe_state": "AIRPLANE_ISOLATED",
        "resids": (0x020027A0, 0x02004270, 0x020042D3),
        "appfw_marker": "EXTERN_SETTING_AIRPLANE_MODE_ON",
        "notes": "P12 Airplane gate + handleFatalError non-blocking guard prevents WF-12 bootloop (00342260).",
    },
)

# Canonical Multilingual String Fixtures for Clean-Room Mode
_CLEAN_ROOM_STRINGS: Dict[int, Dict[str, str]] = {
    0x02004208: {"english": "User", "simplifiedchinese": "用户", "traditionalchinese": "用戶", "japanese": "User"},
    0x02004D4A: {"english": "Edit User Menu", "simplifiedchinese": "编辑用户菜单", "traditionalchinese": "編輯用戶功能表", "japanese": "User Menu編集"},
    0x02002227: {"english": "Shooting", "simplifiedchinese": "拍摄", "traditionalchinese": "拍攝", "japanese": "Shooting"},
    0x02002228: {"english": "Project", "simplifiedchinese": "项目", "traditionalchinese": "專案", "japanese": "Project"},
    0x02002493: {"english": "Paint/Look", "simplifiedchinese": "绘图/风格", "traditionalchinese": "繪製/外觀", "japanese": "Paint/Look"},
    0x0200222B: {"english": "TC/Media", "simplifiedchinese": "TC/媒体", "traditionalchinese": "TC/媒體", "japanese": "TC/Media"},
    0x02002229: {"english": "Monitoring", "simplifiedchinese": "监看", "traditionalchinese": "監控", "japanese": "Monitoring"},
    0x020041FB: {"english": "Audio", "simplifiedchinese": "音频", "traditionalchinese": "音訊", "japanese": "Audio"},
    0x02004209: {"english": "Thumbnail", "simplifiedchinese": "缩略图", "traditionalchinese": "縮圖", "japanese": "Thumbnail"},
    0x0200222A: {"english": "Technical", "simplifiedchinese": "技术", "traditionalchinese": "技術", "japanese": "Technical"},
    0x02004203: {"english": "Maintenance", "simplifiedchinese": "维护", "traditionalchinese": "維護", "japanese": "Maintenance"},
    0x02005082: {"english": "FPS", "simplifiedchinese": "FPS", "traditionalchinese": "FPS", "japanese": "FPS"},
    0x02004C32: {"english": "ISO/Gain", "simplifiedchinese": "ISO/增益", "traditionalchinese": "ISO/增益", "japanese": "ISO/Gain"},
    0x020050E8: {"english": "Shutter", "simplifiedchinese": "快门", "traditionalchinese": "快門", "japanese": "シャッター"},
    0x02004288: {"english": "ND Filter", "simplifiedchinese": "ND滤镜", "traditionalchinese": "ND篩選器", "japanese": "NDフィルター"},
    0x020023F8: {"english": "Base Look", "simplifiedchinese": "基本风格", "traditionalchinese": "基本外觀", "japanese": "基本Look"},
    0x02005689: {"english": "White Balance", "simplifiedchinese": "白平衡", "traditionalchinese": "白平衡", "japanese": "ホワイトバランス"},
    0x0200211E: {"english": "Assignable Button", "simplifiedchinese": "可指定按钮", "traditionalchinese": "可指派按鈕", "japanese": "アサイナブルボタン"},
    0x020020D3: {"english": "ND Filter", "simplifiedchinese": "ND滤镜", "traditionalchinese": "ND篩選器", "japanese": "NDフィルター"},
    0x02002603: {"english": "ND Filter Mode", "simplifiedchinese": "ND滤镜模式", "traditionalchinese": "ND篩選器模式", "japanese": "NDフィルターモード"},
    0x02002604: {"english": "ND Filter", "simplifiedchinese": "ND滤镜", "traditionalchinese": "ND篩選器", "japanese": "NDフィルター"},
    0x02002787: {"english": "ND PRESET/VARIABLE", "simplifiedchinese": "ND PRESET/VARIABLE", "traditionalchinese": "ND PRESET/VARIABLE", "japanese": "ND PRESET/VARIABLE"},
    0x02002246: {"english": "SDI1", "simplifiedchinese": "SDI1", "traditionalchinese": "SDI1", "japanese": "SDI1"},
    0x02002247: {"english": "SDI2, HDMI", "simplifiedchinese": "SDI2, HDMI", "traditionalchinese": "SDI2, HDMI", "japanese": "SDI2, HDMI"},
    0x02002249: {"english": "SDI2 Off", "simplifiedchinese": "SDI2 Off", "traditionalchinese": "SDI2 Off", "japanese": "SDI2 Off"},
    0x0200210B: {"english": "Grip Dial", "simplifiedchinese": "手柄/遥控拨盘", "traditionalchinese": "手把/遙控轉盤", "japanese": "グリップダイヤル"},
    0x0200210C: {"english": "Handle Dial", "simplifiedchinese": "手柄拨盘", "traditionalchinese": "手柄轉盤", "japanese": "ハンドルダイヤル"},
    0x020023C6: {"english": "Zoom", "simplifiedchinese": "变焦", "traditionalchinese": "變焦", "japanese": "ズーム"},
    0x02004232: {"english": "Audio Input", "simplifiedchinese": "音频输入", "traditionalchinese": "音訊輸入", "japanese": "音声入力"},
    0x020027A0: {"english": "Wireless LAN", "simplifiedchinese": "无线LAN", "traditionalchinese": "無線LAN", "japanese": "無線LAN"},
    0x02004270: {"english": "Wi-Fi", "simplifiedchinese": "Wi-Fi", "traditionalchinese": "Wi-Fi", "japanese": "Wi-Fi"},
    0x020042D3: {"english": "Airplane Mode", "simplifiedchinese": "飞行模式", "traditionalchinese": "飛航模式", "japanese": "機内モード"},
}


class GlobalXdbParseError(ValueError):
    """Raised when a `global.xdb`, `lang.uxb`, or `fontlist.dat` payload fails validation."""


@dataclass(frozen=True)
class GlobalXdbSlotSummary:
    slot_index: int
    sub_namespace: Optional[int]
    record_kind: str
    entry_count: int
    sample_entries: Tuple[str, ...]
    is_dummy: bool


@dataclass(frozen=True)
class GlobalXdbAuditResult:
    body: str
    source_mode: str
    container_format: str
    header_magic_hex: str
    file_bytes: int
    hdr_flag: int
    namespace_id: int
    top_slot_count: int
    active_slot_count: int
    dummy_slot_count: int
    total_resource_entries: int
    non_dummy_resource_entries: int
    referenced_files_present: int
    referenced_files_missing: Tuple[str, ...]
    companion_uxb_ok: bool
    companion_fontlist_ok: bool
    fontlist_entries: Tuple[str, ...]
    lang_uxb_magic_hex: str
    lang_uxb_namespace_id: int
    lang_uxb_entry_count: int
    sqlite_table_names: Tuple[str, ...]
    sha256: str
    valid: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class CategoryCompletenessEntry:
    category_index: int
    category_name: str
    title_resid_hex: str
    item_count: int
    item_resids_hex: Tuple[str, ...]
    resolved_titles: Dict[str, str]
    missing_by_language: Dict[str, int]
    corrupt_utf8_count: int
    valid: bool


@dataclass(frozen=True)
class MenuPageAuditSummary:
    page_index: int
    cat_group: int
    base_va_hex: str
    row_count: int
    first_name: str
    null_proto_count: int
    null_name_count: int
    distinct_widget_tags: int
    resids_checked: int
    missing_cmn_resids: int
    missing_string_resids_by_lang: Dict[str, int]
    corrupt_utf8_count: int
    valid: bool


@dataclass(frozen=True)
class MenuTreeCompletenessReport:
    source_mode: str
    categories_verified: int
    category_entries: Tuple[CategoryCompletenessEntry, ...]
    big6_home_verified: bool
    big6_home_row_count: int
    big6_cell_titles: Dict[str, Dict[str, str]]
    assignable_p10_page110_verified: bool
    assignable_p10_row_count: int
    assignable_p10_pool_count: int
    pages_audited: int
    total_descriptor_rows: int
    total_resids_verified: int
    unique_string_resids_128p: int
    missing_resids_total: int
    corrupt_utf8_total: int
    null_proto_hazards: int
    null_name_hazards: int
    language_coverage_summary: Dict[str, Dict[str, int]]
    sample_pages: Tuple[MenuPageAuditSummary, ...]
    valid: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class HardwarePredicateMapping:
    predicate_id: str
    patch_gate: str
    fx6_feature: str
    fx3_safe_state: str
    menu_resids_hex: Tuple[str, ...]
    multilang_labels_verified: bool
    english_labels: Tuple[str, ...]
    appfw_marker: str
    appfw_marker_found: bool
    null_pointer_hazard: bool
    missing_widget_hazard: bool
    nvram_flash_mutation_bytes: int
    valid: bool
    notes: str


@dataclass(frozen=True)
class GlobalXdbAndMenuTreeReport:
    schema_version: str
    mode: str
    all_checks_passed: bool
    o_rdonly_enforced: bool
    sqlite_wal_shm_forbidden: bool
    fx6_global_xdb: GlobalXdbAuditResult
    fx3_global_xdb: GlobalXdbAuditResult
    menu_tree_audit: MenuTreeCompletenessReport
    hardware_predicates: Tuple[HardwarePredicateMapping, ...]
    all_hardware_predicates_safe: bool
    zero_null_pointer_hazards: bool
    report_sha256: str
    errors: Tuple[str, ...]


def _resid_ns(rid: int) -> int:
    return (rid >> 13) & 0x7FF


def _resid_idx(rid: int) -> int:
    return rid & 0x1FFF


def _encode_resid(ns_id: int, idx: int) -> int:
    return (1 << 25) | ((ns_id & 0x7FF) << 13) | (idx & 0x1FFF)


def _pad4(buf: bytearray) -> None:
    while len(buf) % 4 != 0:
        buf.append(0)


def inspect_sqlite_ux_db_rdonly(path: Path) -> Tuple[str, Tuple[str, ...]]:
    """Inspect an optional SQLite3 UX database strictly read-only (`mode=ro&immutable=1`).

    Reads the first 16 bytes via `os.O_RDONLY` to verify `SQLite format 3\\x00`
    before opening `sqlite3.connect(f"file:{...}?mode=ro&immutable=1", uri=True)`
    so `-wal`/`-shm`/journal sidecar files are never created.
    """
    fd = os.open(str(path), os.O_RDONLY)
    try:
        with os.fdopen(fd, "rb") as fh:
            head = fh.read(16)
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        raise
    if head != SQLITE_MAGIC:
        raise GlobalXdbParseError(
            f"Expected SQLite3 magic {SQLITE_MAGIC.hex()}, got {head.hex()}"
        )
    uri = f"file:{path.resolve().as_posix()}?mode=ro&immutable=1"
    conn = sqlite3.connect(uri, uri=True)
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table', 'view') ORDER BY name"
        ).fetchall()
    finally:
        conn.close()
    return head.hex(), tuple(str(r[0]) for r in rows)


def parse_lang_uxb_bytes(data: bytes) -> Tuple[str, int, int, Tuple[str, ...]]:
    """Parse a Sony `uxb\\x07` language metadata table (`lang.uxb`)."""
    errors: List[str] = []
    if len(data) < 16:
        return data.hex(), 0, 0, (f"Truncated lang.uxb ({len(data)} bytes)",)
    magic, _res, hdr_flag, ns_id, meta = UXC_HEADER_STRUCT.unpack_from(data, 0)
    magic_hex = magic.hex()
    if magic != UXB_MAGIC:
        errors.append(f"Expected lang.uxb magic {UXB_MAGIC.hex()}, got {magic_hex}")
    if hdr_flag != 9:
        errors.append(f"Unexpected lang.uxb hdr_flag={hdr_flag} (expected 9)")
    entry_count = meta & 0x1FFF
    base = 16 + entry_count * 4
    if base > len(data):
        errors.append(f"lang.uxb offset table {base:#x} exceeds length {len(data):#x}")
        return magic_hex, ns_id, entry_count, tuple(errors)
    offs = struct.unpack_from(f"<{entry_count}I", data, 16)
    for idx, off in enumerate(offs):
        if base + off + 4 > len(data):
            errors.append(f"lang.uxb entry[{idx}] out of bounds")
            break
    return magic_hex, ns_id, entry_count, tuple(errors)


def parse_fontlist_dat_bytes(data: bytes) -> Tuple[Dict[str, str], Tuple[str, ...]]:
    """Parse Sony `fontlist.dat` key-tab-path lines."""
    errors: List[str] = []
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        return {}, (f"Invalid UTF-8 in fontlist.dat: {exc}",)
    mapping: Dict[str, str] = {}
    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 2:
            errors.append(f"fontlist.dat line {line_no} malformed: {line!r}")
            continue
        mapping[parts[0]] = parts[1]
    if not mapping:
        errors.append("fontlist.dat contains zero font mappings")
    return mapping, tuple(errors)


def parse_global_xdb_buffer(
    data: bytes,
    *,
    body: str = "fx6_601",
    source_mode: str = "SYNTHETIC_CLEAN_ROOM",
    share_app_dir: Optional[Path] = None,
    check_disk_closure: bool = False,
    sqlite_table_names: Tuple[str, ...] = (),
) -> GlobalXdbAuditResult:
    """Parse a Sony `uxa\\x07` `global.xdb` resource database (or SQLite3 UX DB)."""
    sha = hashlib.sha256(data).hexdigest()
    errors: List[str] = []
    header_magic_hex = data[:4].hex() if len(data) >= 4 else data.hex()

    if len(data) >= 16 and data[:16] == SQLITE_MAGIC:
        return GlobalXdbAuditResult(
            body=body,
            source_mode=source_mode,
            container_format="SQLITE3_RDONLY",
            header_magic_hex=data[:16].hex(),
            file_bytes=len(data),
            hdr_flag=0,
            namespace_id=0,
            top_slot_count=len(sqlite_table_names),
            active_slot_count=len(sqlite_table_names),
            dummy_slot_count=0,
            total_resource_entries=len(sqlite_table_names),
            non_dummy_resource_entries=len(sqlite_table_names),
            referenced_files_present=0,
            referenced_files_missing=(),
            companion_uxb_ok=True,
            companion_fontlist_ok=True,
            fontlist_entries=(),
            lang_uxb_magic_hex="",
            lang_uxb_namespace_id=0,
            lang_uxb_entry_count=0,
            sqlite_table_names=sqlite_table_names,
            sha256=sha,
            valid=len(sqlite_table_names) > 0,
            errors=() if sqlite_table_names else ("SQLite3 UX DB has zero tables",),
        )

    if len(data) < 16:
        return GlobalXdbAuditResult(
            body=body,
            source_mode=source_mode,
            container_format="SONY_UXA7",
            header_magic_hex=header_magic_hex,
            file_bytes=len(data),
            hdr_flag=0,
            namespace_id=0,
            top_slot_count=0,
            active_slot_count=0,
            dummy_slot_count=0,
            total_resource_entries=0,
            non_dummy_resource_entries=0,
            referenced_files_present=0,
            referenced_files_missing=(),
            companion_uxb_ok=False,
            companion_fontlist_ok=False,
            fontlist_entries=(),
            lang_uxb_magic_hex="",
            lang_uxb_namespace_id=0,
            lang_uxb_entry_count=0,
            sqlite_table_names=(),
            sha256=sha,
            valid=False,
            errors=(f"Truncated global.xdb ({len(data)} bytes)",),
        )

    magic, _res, hdr_flag, ns_id, meta = UXC_HEADER_STRUCT.unpack_from(data, 0)
    if magic != UXA_MAGIC:
        errors.append(f"Invalid global.xdb magic {magic.hex()} (expected {UXA_MAGIC.hex()})")
    if hdr_flag != 9:
        errors.append(f"Unexpected global.xdb hdr_flag={hdr_flag} (expected 9)")

    top_slot_count = meta & 0x1FFF
    rec_base = 16 + top_slot_count * 4
    if rec_base > len(data):
        errors.append(f"Top slot table {rec_base:#x} exceeds file size {len(data):#x}")
        top_slot_count = 0
        offs: Tuple[int, ...] = ()
    else:
        offs = struct.unpack_from(f"<{top_slot_count}I", data, 16)

    slots: List[GlobalXdbSlotSummary] = []
    referenced_files: List[str] = []
    dummy_slots = 0
    total_entries = 0

    for idx, rel_off in enumerate(offs):
        pos = rec_base + rel_off
        if pos >= len(data):
            errors.append(f"Slot {idx} offset {pos:#x} out of bounds")
            continue
        if data[pos] == 0x80:
            nul = data.find(b"\x00", pos + 1)
            if nul == -1:
                errors.append(f"Slot {idx} unterminated direct string at {pos:#x}")
                continue
            try:
                val = data[pos + 1 : nul].decode("utf-8", errors="strict")
            except UnicodeDecodeError as exc:
                errors.append(f"Slot {idx} invalid UTF-8 string: {exc}")
                continue
            is_dummy = val.startswith("__Dummy_NS_ID__")
            if is_dummy:
                dummy_slots += 1
            else:
                referenced_files.append(val)
            total_entries += 1
            slots.append(
                GlobalXdbSlotSummary(
                    slot_index=idx,
                    sub_namespace=None,
                    record_kind="direct_entry",
                    entry_count=1,
                    sample_entries=(val,),
                    is_dummy=is_dummy,
                )
            )
        else:
            if pos + 8 > len(data):
                errors.append(f"Slot {idx} subtable header out of bounds at {pos:#x}")
                continue
            sub_tag, sub_ns, sub_meta = struct.unpack_from("<HHI", data, pos)
            if sub_tag != 9:
                errors.append(f"Slot {idx} unexpected subtable tag {sub_tag:#x} (expected 0x9)")
                continue
            sub_cnt = sub_meta & 0x1FFF
            sub_base = pos + 8 + sub_cnt * 4
            if sub_base > len(data):
                errors.append(f"Slot {idx} subtable offsets exceed file size")
                continue
            sub_offs = struct.unpack_from(f"<{sub_cnt}I", data, pos + 8)
            items: List[str] = []
            for j, so in enumerate(sub_offs):
                sp = sub_base + so
                if sp >= len(data) or data[sp] != 0x80:
                    errors.append(f"Slot {idx}[{j}] missing 0x80 entry marker at {sp:#x}")
                    continue
                nul = data.find(b"\x00", sp + 1)
                if nul == -1:
                    errors.append(f"Slot {idx}[{j}] unterminated string at {sp:#x}")
                    continue
                try:
                    val = data[sp + 1 : nul].decode("utf-8", errors="strict")
                except UnicodeDecodeError as exc:
                    errors.append(f"Slot {idx}[{j}] invalid UTF-8: {exc}")
                    continue
                items.append(val)
                if not val.startswith("__Dummy_NS_ID__"):
                    referenced_files.append(val)
            is_dummy = len(items) == 1 and items[0].startswith("__Dummy_NS_ID__")
            if is_dummy:
                dummy_slots += 1
            total_entries += len(items)
            slots.append(
                GlobalXdbSlotSummary(
                    slot_index=idx,
                    sub_namespace=sub_ns,
                    record_kind="subtable",
                    entry_count=len(items),
                    sample_entries=tuple(items[:3]),
                    is_dummy=is_dummy,
                )
            )

    active_slot_count = len(slots) - dummy_slots
    missing_files: List[str] = []
    present_files = 0
    companion_uxb_ok = True
    companion_fontlist_ok = True
    fontlist_entries: Tuple[str, ...] = ()
    lang_magic_hex = ""
    lang_ns_id = 0
    lang_count = 0

    if check_disk_closure and share_app_dir is not None:
        for ref in referenced_files:
            bn = Path(ref).name
            if (share_app_dir / bn).is_file():
                present_files += 1
            else:
                missing_files.append(bn)
        if missing_files:
            errors.append(f"{body} global.xdb missing {len(missing_files)} referenced files: {missing_files[:5]}")

        lang_path = share_app_dir / "lang.uxb"
        if lang_path.is_file():
            lang_magic_hex, lang_ns_id, lang_count, l_errs = parse_lang_uxb_bytes(read_bytes_rdonly(lang_path))
            if l_errs:
                companion_uxb_ok = False
                errors.extend(l_errs)
        else:
            companion_uxb_ok = False
            errors.append(f"{body} missing companion lang.uxb")

        fl_path = share_app_dir / "fontlist.dat"
        if fl_path.is_file():
            fl_map, fl_errs = parse_fontlist_dat_bytes(read_bytes_rdonly(fl_path))
            fontlist_entries = tuple(f"{k}={v}" for k, v in sorted(fl_map.items()))
            if fl_errs:
                companion_fontlist_ok = False
                errors.extend(fl_errs)
        else:
            companion_fontlist_ok = False
            errors.append(f"{body} missing companion fontlist.dat")
    else:
        present_files = len(referenced_files)

    valid = (
        len(errors) == 0
        and len(slots) > 0
        and len(referenced_files) > 0
        and len(missing_files) == 0
        and companion_uxb_ok
        and companion_fontlist_ok
    )
    return GlobalXdbAuditResult(
        body=body,
        source_mode=source_mode,
        container_format="SONY_UXA7",
        header_magic_hex=header_magic_hex,
        file_bytes=len(data),
        hdr_flag=hdr_flag,
        namespace_id=ns_id,
        top_slot_count=top_slot_count,
        active_slot_count=active_slot_count,
        dummy_slot_count=dummy_slots,
        total_resource_entries=total_entries,
        non_dummy_resource_entries=len(referenced_files),
        referenced_files_present=present_files,
        referenced_files_missing=tuple(missing_files),
        companion_uxb_ok=companion_uxb_ok,
        companion_fontlist_ok=companion_fontlist_ok,
        fontlist_entries=fontlist_entries,
        lang_uxb_magic_hex=lang_magic_hex,
        lang_uxb_namespace_id=lang_ns_id,
        lang_uxb_entry_count=lang_count,
        sqlite_table_names=(),
        sha256=sha,
        valid=valid,
        errors=tuple(errors),
    )


def audit_global_xdb_file_rdonly(
    path: Path,
    *,
    body: str = "fx6_601",
    share_app_dir: Optional[Path] = None,
    check_disk_closure: bool = True,
) -> GlobalXdbAuditResult:
    """Open and audit a `global.xdb` (Sony `uxa\\x07` or SQLite3) strictly `os.O_RDONLY`."""
    raw = read_bytes_rdonly(path)
    sqlite_tables: Tuple[str, ...] = ()
    if len(raw) >= 16 and raw[:16] == SQLITE_MAGIC:
        _hex, sqlite_tables = inspect_sqlite_ux_db_rdonly(path)
    return parse_global_xdb_buffer(
        raw,
        body=body,
        source_mode="LOCAL_DONOR_RDONLY",
        share_app_dir=share_app_dir if share_app_dir is not None else path.parent,
        check_disk_closure=check_disk_closure,
        sqlite_table_names=sqlite_tables,
    )


def _encode_uxa_subtable(sub_ns: int, strings: Sequence[str], *, sub_meta_flags: int = 0x2000) -> bytes:
    payload = bytearray()
    offs: List[int] = []
    for s in strings:
        offs.append(len(payload))
        payload.append(0x80)
        payload.extend(s.encode("utf-8"))
        payload.append(0)
        _pad4(payload)
    sub_cnt = len(strings)
    sub_meta = (sub_cnt & 0x1FFF) | (sub_meta_flags if sub_cnt == 1 else (sub_cnt << 13))
    hdr = struct.pack("<HHI", 9, sub_ns, sub_meta)
    off_tbl = struct.pack(f"<{sub_cnt}I", *offs)
    return hdr + off_tbl + bytes(payload)


def build_synthetic_global_xdb(variant: str = "fx6_601") -> bytes:
    """Build a deterministic byte-compliant Sony `uxa\\x07` `global.xdb` fixture."""
    slots: List[Tuple[str, bytes]] = []
    if variant == "fx6_601":
        ns1 = [f"string_{lang}.uxc" for lang in FX6_LANGUAGE_SLUGS_29]
        ns2 = [f"string_{lang}_2.uxc" for lang in FX6_LANGUAGE_SLUGS_29]
        slots.append(("sub", _encode_uxa_subtable(0, ["../../../usr/share/app/image_00_169.uxc"])))
        slots.append(("sub", _encode_uxa_subtable(1, ns1)))
        slots.append(("sub", _encode_uxa_subtable(2, ns2)))
        slots.append(("sub", _encode_uxa_subtable(3, ["style_cmn.uxc"])))
        direct = bytearray(b"\x80lang.uxb\x00")
        _pad4(direct)
        slots.append(("raw", bytes(direct)))
        slots.append(("sub", _encode_uxa_subtable(5, ["lang_cmn.uxc"])))
        slots.append(("sub", _encode_uxa_subtable(6, ["color_cmn.uxc"])))
    elif variant == "fx3_702":
        langs34 = list(FX6_LANGUAGE_SLUGS_29) + ["finnish2", "spanish_la", "french_ca", "chinese_hk", "vietnamese"]
        slots.append(("sub", _encode_uxa_subtable(0, [
            "../../../usr/share/app/image_00_43.uxc",
            "../../../usr/share/app/image_00_169.uxc",
            "../../../usr/share/app/image_00_32.uxc",
        ])))
        slots.append(("sub", _encode_uxa_subtable(1, [
            "../../../usr/share/app/image_01_43.uxc",
            "../../../usr/share/app/image_01_169.uxc",
            "../../../usr/share/app/image_01_32.uxc",
        ])))
        slots.append(("sub", _encode_uxa_subtable(2, [
            "../../../usr/share/app/image_02_43.uxc",
            "../../../usr/share/app/image_02_169.uxc",
            "../../../usr/share/app/image_02_32.uxc",
        ])))
        slots.append(("sub", _encode_uxa_subtable(3, [f"string_{l}_g.uxc" for l in langs34])))
        for i in range(4, 12):
            if i == 5:
                slots.append(("sub", _encode_uxa_subtable(5, ["lang_cmn.uxc"])))
            elif i == 6:
                slots.append(("sub", _encode_uxa_subtable(6, ["style_cmn.uxc"])))
            elif i == 7:
                slots.append(("sub", _encode_uxa_subtable(7, ["color_cmn.uxc"])))
            else:
                slots.append(("sub", _encode_uxa_subtable(i, [f"__Dummy_NS_ID__{i}"])))
    else:
        raise ValueError(f"Unknown synthetic global.xdb variant: {variant!r}")

    body = bytearray()
    offs: List[int] = []
    for _kind, chunk in slots:
        offs.append(len(body))
        body.extend(chunk)
    cnt = len(slots)
    meta = (cnt & 0x1FFF) | ((cnt & 0x1FFF) << 13)
    hdr = UXC_HEADER_STRUCT.pack(UXA_MAGIC, 0, 9, 0, meta)
    off_tbl = struct.pack(f"<{cnt}I", *offs)
    return hdr + off_tbl + bytes(body)


def build_synthetic_lang_uxb(namespace_id: int = 4, count: int = 36) -> bytes:
    """Build a deterministic byte-compliant Sony `uxb\\x07` (`lang.uxb`) fixture."""
    stride = 0x4C
    offs = [i * stride for i in range(count)]
    recs = bytearray()
    for i in range(count):
        rec = bytearray(stride)
        struct.pack_into("<HHII", rec, 0, 8, namespace_id, 0x4003, i)
        recs.extend(rec)
    meta = (count & 0x1FFF) | (0x040000)
    hdr = UXC_HEADER_STRUCT.pack(UXB_MAGIC, 0, 9, namespace_id, meta)
    off_tbl = struct.pack(f"<{count}I", *offs)
    return hdr + off_tbl + bytes(recs)


def build_synthetic_fontlist_dat(variant: str = "fx6_601") -> bytes:
    """Build deterministic clean-room `fontlist.dat` mapping."""
    lines = [
        "FONT_JAPANESE\t/usr/share/app/HeiseiKakuGothW5-SJ_wIcon.ltt",
        "FONT_UNIVERS\t/usr/share/app/UniversOTS-SJ_wIcon.ltt",
        "FONT_KOREAN\t/usr/share/app/MYingHeiC-KSX1001-SJ_wIcon.ltt",
        "FONT_S_CHINESE\t/usr/share/app/MYingHeiC-GB18030-SJ_wIcon.ltt",
        "FONT_T_CHINESE\t/usr/share/app/MYingHeiC-Big5HKSCS-SJ_wIcon.ltt",
    ]
    if variant == "fx3_702":
        lines.append("FONT_ICONS\t/usr/share/app/Sony_DI_Icons.ttf")
    return ("\n".join(lines) + "\n").encode("utf-8")


def build_sparse_uxc_string_pack(
    slot_texts: Mapping[int, str],
    *,
    namespace_id: int,
) -> bytes:
    """Build a sparse-slot `uxc\\x07` string container indexed by exact `STRID & 0x1fff`."""
    max_slot = max(slot_texts.keys(), default=0)
    entry_slots = max_slot + 1
    padded_slots = (entry_slots + 1) & ~1
    w_offs: List[int] = []
    payload = bytearray()
    for idx in range(entry_slots):
        if idx not in slot_texts:
            w_offs.append(0xFFFF)
            continue
        assert len(payload) % 4 == 0
        w_offs.append(len(payload) // 4)
        resid16 = ((namespace_id & 0x7) << 13) | (idx & 0x1FFF)
        payload.extend(struct.pack("<HH", resid16, 0x1E00))
        payload.extend(slot_texts[idx].encode("utf-8"))
        payload.append(0)
        _pad4(payload)

    meta = (entry_slots & 0x1FFF) | 0x2000
    hdr = UXC_HEADER_STRUCT.pack(UXC_MAGIC, 0, 8, namespace_id, meta)
    off_tbl = struct.pack(f"<{entry_slots}H", *w_offs)
    if entry_slots < padded_slots:
        off_tbl += b"\xFF\xFF"
    return hdr + off_tbl + bytes(payload)


def _build_sparse_cmn_uxc(indices: Iterable[int], *, namespace_id: int, magic: bytes = UXC_MAGIC) -> bytes:
    idx_set = sorted(set(indices))
    entry_slots = max(idx_set, default=0) + 1
    padded_slots = (entry_slots + 1) & ~1
    w_offs: List[int] = []
    payload = bytearray()
    idx_lookup = set(idx_set)
    for idx in range(entry_slots):
        if idx not in idx_lookup:
            w_offs.append(0xFFFF)
            continue
        w_offs.append(len(payload) // 4)
        resid16 = ((namespace_id & 0x7) << 13) | (idx & 0x1FFF)
        if magic == UXD_MAGIC:
            payload.extend(struct.pack("<HHHHII", resid16, 0x2100, 16, 16, 4, 0))
        else:
            payload.extend(struct.pack("<HH", resid16, 0x1E00))
            payload.extend(f"cmn_{namespace_id}_{idx}".encode("ascii") + b"\x00")
            _pad4(payload)
    meta = (entry_slots & 0x1FFF) | 0x2000
    hdr = UXC_HEADER_STRUCT.pack(magic, 0, 8, namespace_id, meta)
    off_tbl = struct.pack(f"<{entry_slots}H", *w_offs)
    if entry_slots < padded_slots:
        off_tbl += b"\xFF\xFF"
    return hdr + off_tbl + bytes(payload)


def _collect_all_curated_resids() -> Set[int]:
    rids: Set[int] = set(_CLEAN_ROOM_STRINGS.keys())
    for _ci, _cname, title_rid, items, _titles in FX6_11_CATEGORIES:
        rids.add(title_rid)
        rids.update(items)
    for _ci, _cname, title_rid, _titles in BIG6_CELL_TITLES:
        rids.add(title_rid)
    rids.add(ASSIGNABLE_PAGE_110_TITLE_RESID)
    rids.update(ASSIGNABLE_PAGE_110_POOL)
    for spec in HARDWARE_PREDICATE_SPECS:
        rids.update(int(r) for r in spec["resids"])  # type: ignore[arg-type]
    return rids


def build_clean_room_menu_fixtures() -> Dict[str, object]:
    """Synthesize ELF64 `appFw.so` (128 descriptor tables) + multilingual `.uxc` packs."""
    all_rids = sorted(_collect_all_curated_resids())
    ns1_rids = [r for r in all_rids if _resid_ns(r) == 1]
    ns2_rids = [r for r in all_rids if _resid_ns(r) == 2]

    # Build sparse .uxc packs for all 4 languages
    uxc_packs: Dict[str, bytes] = {}
    for lang in TARGET_LANGUAGES:
        m1: Dict[int, str] = {}
        m2: Dict[int, str] = {}
        for rid in ns1_rids:
            idx = _resid_idx(rid)
            if rid in _CLEAN_ROOM_STRINGS:
                m1[idx] = _CLEAN_ROOM_STRINGS[rid][lang]
            else:
                m1[idx] = f"[{lang}] Item_{rid:08x}"
        for rid in ns2_rids:
            idx = _resid_idx(rid)
            if rid in _CLEAN_ROOM_STRINGS:
                m2[idx] = _CLEAN_ROOM_STRINGS[rid][lang]
            else:
                m2[idx] = f"[{lang}] Item2_{rid:08x}"
        uxc_packs[f"string_{lang}.uxc"] = build_sparse_uxc_string_pack(m1, namespace_id=1)
        uxc_packs[f"string_{lang}_2.uxc"] = build_sparse_uxc_string_pack(m2, namespace_id=2)

    uxc_packs["image_00_169.uxc"] = _build_sparse_cmn_uxc((0x0154, 0x043D), namespace_id=0, magic=UXD_MAGIC)
    uxc_packs["style_cmn.uxc"] = _build_sparse_cmn_uxc((0x000B, 0x000F, 0x002B), namespace_id=3)
    uxc_packs["lang_cmn.uxc"] = _build_sparse_cmn_uxc((0x0005, 0x0029), namespace_id=5)
    uxc_packs["color_cmn.uxc"] = _build_sparse_cmn_uxc((0x0001, 0x0003, 0x0008, 0x0014), namespace_id=6)

    # Synthesize ELF64 appFw.so with 1 PT_LOAD mapping [0x02e90000 .. 0x02ec2000)
    load_vaddr = 0x02E90000
    load_file_off = 0x1000
    max_table_end = max(va + rows * DESC_STRIDE for _i, _cg, va, rows, _n in FX6_128_PAGE_DIRECTORY)
    str_pool_va = max_table_end + 0x100
    str_pool = bytearray()
    name_va_cache: Dict[str, int] = {}

    def _intern_name(name: str) -> int:
        if name not in name_va_cache:
            name_va_cache[name] = str_pool_va + len(str_pool)
            str_pool.extend(name.encode("ascii") + b"\x00")
        return name_va_cache[name]

    # Pre-populate marker strings used by FX3 hardware predicate checks
    for spec in HARDWARE_PREDICATE_SPECS:
        _intern_name(str(spec["appfw_marker"]))
    _intern_name("global.xdb")

    # Populate all 128 descriptor tables
    load_size = (str_pool_va - load_vaddr) + len(str_pool) + 0x400
    # Re-calculate after interning page names
    for _pidx, _cg, _va, _rows, first_name in FX6_128_PAGE_DIRECTORY:
        _intern_name(first_name)
    load_size = (str_pool_va - load_vaddr) + len(str_pool) + 0x100

    buf = bytearray(load_file_off + load_size)
    ehdr = ELF64_EHDR_STRUCT.pack(
        b"\x7fELF\x02\x01\x01" + bytes(9),
        3,    # ET_DYN
        183,  # EM_AARCH64
        1,
        0,
        64,
        0,
        0,
        64,
        56,
        1,
        64,
        0,
        0,
    )
    phdr = ELF64_PHDR_STRUCT.pack(PT_LOAD, 4, load_file_off, load_vaddr, load_vaddr, load_size, load_size, 0x1000)
    buf[0:64] = ehdr
    buf[64:120] = phdr

    str_off_in_file = load_file_off + (str_pool_va - load_vaddr)
    buf[str_off_in_file : str_off_in_file + len(str_pool)] = str_pool

    # Cycle curated ResIDs across pages so every page has valid string/style/lang/color/icon ResIDs
    cycle_str_rids = ns1_rids + ns2_rids
    s_cursor = 0
    for pidx, _cg, va, rows, first_name in FX6_128_PAGE_DIRECTORY:
        base_off = load_file_off + (va - load_vaddr)
        nva = name_va_cache[first_name]
        for r in range(rows):
            ro = base_off + r * DESC_STRIDE
            if pidx == ASSIGNABLE_PAGE_110_INDEX and r < len(ASSIGNABLE_PAGE_110_POOL):
                d18 = ASSIGNABLE_PAGE_110_POOL[r]
                proto = 0x42D58D0
            elif r % 4 == 0:
                d18 = 0x0200C003
                proto = 0x42D5A40
            elif r % 4 == 1:
                d18 = 0x02000154
                proto = 0x42D5A50
            else:
                d18 = cycle_str_rids[s_cursor % len(cycle_str_rids)]
                s_cursor += 1
                proto = 0x42D57F0
            struct.pack_into("<QQ", buf, ro, proto, nva)
            struct.pack_into("<5I", buf, ro + 0x18, d18, 0x0200A029, 1, 0x0200600F, 0x0200600B)
            struct.pack_into("<5H", buf, ro + 0x3A, r, 60, 50, 200, 40)

    return {
        "appfw_bytes": bytes(buf),
        "uxc_packs": uxc_packs,
        "fx6_global_xdb": build_synthetic_global_xdb("fx6_601"),
        "fx3_global_xdb": build_synthetic_global_xdb("fx3_702"),
        "fx6_lang_uxb": build_synthetic_lang_uxb(namespace_id=4, count=36),
        "fx3_lang_uxb": build_synthetic_lang_uxb(namespace_id=59, count=36),
        "fx6_fontlist": build_synthetic_fontlist_dat("fx6_601"),
        "fx3_fontlist": build_synthetic_fontlist_dat("fx3_702"),
    }


def _parse_elf_pt_loads(mm: UnionBuffer) -> List[Tuple[int, int, int]]:
    if len(mm) < 64 or mm[:4] != ELF_MAGIC:
        raise GlobalXdbParseError("Invalid ELF64 header in appFw.so")
    e_phoff = struct.unpack_from("<Q", mm, 32)[0]
    e_phentsize, e_phnum = struct.unpack_from("<HH", mm, 54)
    loads: List[Tuple[int, int, int]] = []
    for i in range(e_phnum):
        pt, _pf, off, va, _pa, fsz, _msz, _align = ELF64_PHDR_STRUCT.unpack_from(
            mm, e_phoff + i * e_phentsize
        )
        if pt == PT_LOAD:
            loads.append((va, off, fsz))
    return loads


UnionBuffer = object  # typing alias kept lightweight for bytes | mmap.mmap


def _vaddr_to_offset(loads: Sequence[Tuple[int, int, int]], vaddr: int) -> Optional[int]:
    for sva, off, fsz in loads:
        if sva <= vaddr < sva + fsz:
            return off + (vaddr - sva)
    return None


def _load_cmn_slot_set(data: bytes) -> Tuple[int, Set[int]]:
    if len(data) < UXC_HEADER_STRUCT.size:
        raise GlobalXdbParseError("Truncated common .uxc header")
    magic, _res, _hdr_flag, ns_id, u32_0c = UXC_HEADER_STRUCT.unpack_from(data, 0)
    if magic not in (UXC_MAGIC, UXD_MAGIC):
        raise GlobalXdbParseError(f"Unexpected common pack magic {magic.hex()}")
    slots = u32_0c & 0x1FFF
    vals = struct.unpack_from(f"<{slots}H", data, 16)
    return ns_id, {idx for idx, w in enumerate(vals) if w != 0xFFFF}


def audit_128_page_multilingual_menu_tree(
    appfw_buf: bytes | mmap.mmap,
    lang_maps: Mapping[str, Mapping[int, Mapping[int, Tuple[int, str]]]],
    cmn_slot_sets: Mapping[int, Set[int]],
    *,
    source_mode: str,
    lang_corrupt_counts: Optional[Mapping[str, int]] = None,
) -> MenuTreeCompletenessReport:
    """Audit 11 categories, Big-6 Home, Page 110, and all 128 descriptor pages across 4 languages."""
    errors: List[str] = []
    loads = _parse_elf_pt_loads(appfw_buf)
    corrupt_map = dict(lang_corrupt_counts or {})

    # 1. Audit 11 Level-1 Categories + their menu items across all 4 languages
    cat_entries: List[CategoryCompletenessEntry] = []
    for cat_idx, cat_name, title_rid, item_rids, _expected in FX6_11_CATEGORIES:
        check_rids = (title_rid, *item_rids)
        resolved_titles: Dict[str, str] = {}
        missing_by_lang: Dict[str, int] = {lang: 0 for lang in TARGET_LANGUAGES}
        for lang in TARGET_LANGUAGES:
            ns_t = _resid_ns(title_rid)
            idx_t = _resid_idx(title_rid)
            entry = lang_maps.get(lang, {}).get(ns_t, {}).get(idx_t)
            if entry is None or not entry[1].strip():
                resolved_titles[lang] = ""
            else:
                resolved_titles[lang] = entry[1]
            for rid in check_rids:
                ns = _resid_ns(rid)
                idx = _resid_idx(rid)
                val = lang_maps.get(lang, {}).get(ns, {}).get(idx)
                if val is None or not val[1]:
                    missing_by_lang[lang] += 1
        corrupt_cnt = sum(corrupt_map.get(lang, 0) for lang in TARGET_LANGUAGES)
        cat_ok = all(v == 0 for v in missing_by_lang.values()) and all(
            bool(resolved_titles.get(l)) for l in TARGET_LANGUAGES
        ) and corrupt_cnt == 0
        if not cat_ok:
            errors.append(f"Category {cat_idx} ({cat_name}) incomplete: missing={missing_by_lang}")
        cat_entries.append(
            CategoryCompletenessEntry(
                category_index=cat_idx,
                category_name=cat_name,
                title_resid_hex=hex(title_rid),
                item_count=len(item_rids),
                item_resids_hex=tuple(hex(r) for r in item_rids),
                resolved_titles=resolved_titles,
                missing_by_language=missing_by_lang,
                corrupt_utf8_count=corrupt_cnt,
                valid=cat_ok,
            )
        )

    # 2. Big-6 Home cell titles across 4 languages
    big6_cell_titles: Dict[str, Dict[str, str]] = {}
    big6_ok = True
    for _cidx, cname, rid, _exp in BIG6_CELL_TITLES:
        ns, idx = _resid_ns(rid), _resid_idx(rid)
        per_lang: Dict[str, str] = {}
        for lang in TARGET_LANGUAGES:
            val = lang_maps.get(lang, {}).get(ns, {}).get(idx)
            if val is None or not val[1]:
                big6_ok = False
                errors.append(f"Big-6 cell {cname} missing {lang} label for {rid:#010x}")
                per_lang[lang] = ""
            else:
                per_lang[lang] = val[1]
        big6_cell_titles[cname] = per_lang

    # 3. Assignable Buttons Page 110 pool across 4 languages
    p10_ok = True
    for rid in (ASSIGNABLE_PAGE_110_TITLE_RESID, *ASSIGNABLE_PAGE_110_POOL):
        ns, idx = _resid_ns(rid), _resid_idx(rid)
        for lang in TARGET_LANGUAGES:
            val = lang_maps.get(lang, {}).get(ns, {}).get(idx)
            if val is None or not val[1]:
                p10_ok = False
                errors.append(f"Assignable Page 110 ResID {rid:#010x} missing in {lang}")

    # 4. Full 128-Page Descriptor Table Audit in appFw.so
    total_rows = 0
    total_resids_verified = 0
    missing_resids_total = 0
    null_proto_hazards = 0
    null_name_hazards = 0
    unique_str_rids: Set[Tuple[int, int]] = set()
    lang_missing_128: Dict[str, int] = {lang: 0 for lang in TARGET_LANGUAGES}
    sample_pages: List[MenuPageAuditSummary] = []

    for pidx, cat_group, va, rows, first_name in FX6_128_PAGE_DIRECTORY:
        fo = _vaddr_to_offset(loads, va)
        if fo is None or fo + rows * DESC_STRIDE > len(appfw_buf):
            errors.append(f"Page {pidx} VA {va:#x} ({rows} rows) unmapped in appFw.so")
            null_proto_hazards += rows
            continue

        total_rows += rows
        p_null_proto = 0
        p_null_name = 0
        p_tags: Set[int] = set()
        p_resids = 0
        p_missing_cmn = 0
        p_missing_str = {lang: 0 for lang in TARGET_LANGUAGES}

        for r in range(rows):
            ro = fo + r * DESC_STRIDE
            proto, name_va = struct.unpack_from("<QQ", appfw_buf, ro)
            if proto == 0:
                p_null_proto += 1
            else:
                p_tags.add(proto)
            if name_va == 0 or _vaddr_to_offset(loads, name_va) is None:
                p_null_name += 1

            d18, d1c, _flag, d24, d28 = struct.unpack_from("<5I", appfw_buf, ro + 0x18)
            for rid in (d18, d1c, d24, d28):
                if rid in (0, 0xFFFFFFFF):
                    continue
                p_resids += 1
                total_resids_verified += 1
                ns, idx = _resid_ns(rid), _resid_idx(rid)
                if ns in (1, 2):
                    unique_str_rids.add((ns, idx))
                    for lang in TARGET_LANGUAGES:
                        if idx not in lang_maps.get(lang, {}).get(ns, {}):
                            p_missing_str[lang] += 1
                            lang_missing_128[lang] += 1
                else:
                    if idx not in cmn_slot_sets.get(ns, set()):
                        p_missing_cmn += 1
                        missing_resids_total += 1

        null_proto_hazards += p_null_proto
        null_name_hazards += p_null_name
        missing_resids_total += sum(p_missing_str.values())

        page_ok = (
            p_null_proto == 0
            and p_null_name == 0
            and p_missing_cmn == 0
            and all(v == 0 for v in p_missing_str.values())
        )
        if not page_ok:
            errors.append(
                f"Page {pidx} ({first_name}) failed: null_proto={p_null_proto}, "
                f"null_name={p_null_name}, missing_cmn={p_missing_cmn}, missing_str={p_missing_str}"
            )
        if pidx in CURATED_SAMPLE_PAGE_INDICES:
            sample_pages.append(
                MenuPageAuditSummary(
                    page_index=pidx,
                    cat_group=cat_group,
                    base_va_hex=hex(va),
                    row_count=rows,
                    first_name=first_name,
                    null_proto_count=p_null_proto,
                    null_name_count=p_null_name,
                    distinct_widget_tags=len(p_tags),
                    resids_checked=p_resids,
                    missing_cmn_resids=p_missing_cmn,
                    missing_string_resids_by_lang=p_missing_str,
                    corrupt_utf8_count=0,
                    valid=page_ok,
                )
            )

    corrupt_utf8_total = sum(corrupt_map.get(lang, 0) for lang in TARGET_LANGUAGES)
    lang_cov_summary: Dict[str, Dict[str, int]] = {}
    for lang in TARGET_LANGUAGES:
        ns1_total = len(lang_maps.get(lang, {}).get(1, {}))
        ns2_total = len(lang_maps.get(lang, {}).get(2, {}))
        lang_cov_summary[lang] = {
            "ns1_strings": ns1_total,
            "ns2_strings": ns2_total,
            "missing_in_128_pages": lang_missing_128[lang],
            "corrupt_utf8": corrupt_map.get(lang, 0),
        }

    if null_proto_hazards > 0:
        errors.append(f"Detected {null_proto_hazards} null descriptor prototype pointers")
    if null_name_hazards > 0:
        errors.append(f"Detected {null_name_hazards} null descriptor debug names")

    valid = (
        len(errors) == 0
        and len(cat_entries) == 11
        and all(c.valid for c in cat_entries)
        and big6_ok
        and p10_ok
        and len(FX6_128_PAGE_DIRECTORY) == 128
        and total_rows == 2224
        and missing_resids_total == 0
        and corrupt_utf8_total == 0
        and null_proto_hazards == 0
        and null_name_hazards == 0
    )

    return MenuTreeCompletenessReport(
        source_mode=source_mode,
        categories_verified=len(cat_entries),
        category_entries=tuple(cat_entries),
        big6_home_verified=big6_ok,
        big6_home_row_count=BIG6_HOME_ROW_COUNT,
        big6_cell_titles=big6_cell_titles,
        assignable_p10_page110_verified=p10_ok,
        assignable_p10_row_count=ASSIGNABLE_PAGE_110_ROW_COUNT,
        assignable_p10_pool_count=len(ASSIGNABLE_PAGE_110_POOL),
        pages_audited=len(FX6_128_PAGE_DIRECTORY),
        total_descriptor_rows=total_rows,
        total_resids_verified=total_resids_verified,
        unique_string_resids_128p=len(unique_str_rids),
        missing_resids_total=missing_resids_total,
        corrupt_utf8_total=corrupt_utf8_total,
        null_proto_hazards=null_proto_hazards,
        null_name_hazards=null_name_hazards,
        language_coverage_summary=lang_cov_summary,
        sample_pages=tuple(sample_pages),
        valid=valid,
        errors=tuple(errors),
    )


def evaluate_fx3_hardware_predicates(
    appfw_buf: bytes | mmap.mmap,
    lang_maps: Mapping[str, Mapping[int, Mapping[int, Tuple[int, str]]]],
    menu_report: MenuTreeCompletenessReport,
) -> Tuple[HardwarePredicateMapping, ...]:
    """Verify FX6-only physical hardware menu items map cleanly to FX3 safe states."""
    results: List[HardwarePredicateMapping] = []
    no_widget_hazard = (menu_report.null_proto_hazards == 0 and menu_report.null_name_hazards == 0)

    for spec in HARDWARE_PREDICATE_SPECS:
        pred_id = str(spec["predicate_id"])
        patch_gate = str(spec["patch_gate"])
        fx6_feature = str(spec["fx6_feature"])
        fx3_safe_state = str(spec["fx3_safe_state"])
        resids = tuple(int(r) for r in spec["resids"])  # type: ignore[arg-type]
        marker = str(spec["appfw_marker"])
        notes = str(spec["notes"])

        marker_found = appfw_buf.find(marker.encode("ascii")) != -1
        en_labels: List[str] = []
        multilang_ok = True
        for rid in resids:
            ns, idx = _resid_ns(rid), _resid_idx(rid)
            for lang in TARGET_LANGUAGES:
                val = lang_maps.get(lang, {}).get(ns, {}).get(idx)
                if val is None or not val[1]:
                    multilang_ok = False
                elif lang == "english":
                    en_labels.append(val[1])

        null_ptr_hazard = not no_widget_hazard
        missing_widget_hazard = not (multilang_ok and marker_found and no_widget_hazard)
        valid = multilang_ok and marker_found and not null_ptr_hazard and not missing_widget_hazard

        results.append(
            HardwarePredicateMapping(
                predicate_id=pred_id,
                patch_gate=patch_gate,
                fx6_feature=fx6_feature,
                fx3_safe_state=fx3_safe_state,
                menu_resids_hex=tuple(hex(r) for r in resids),
                multilang_labels_verified=multilang_ok,
                english_labels=tuple(en_labels),
                appfw_marker=marker,
                appfw_marker_found=marker_found,
                null_pointer_hazard=null_ptr_hazard,
                missing_widget_hazard=missing_widget_hazard,
                nvram_flash_mutation_bytes=0,
                valid=valid,
                notes=notes,
            )
        )
    return tuple(results)


def analyze_global_xdb_and_menu_tree(
    *,
    clean_room: bool = False,
    repo_root: Path = DEFAULT_REPO_ROOT,
    env: Optional[Mapping[str, str]] = None,
) -> GlobalXdbAndMenuTreeReport:
    """Run the complete Phase 46 `global.xdb` + 128-page multilingual menu & predicate audit."""
    errors: List[str] = []

    fx6_xdb_path = resolve_donor_file(
        f"{FX6_SHARE_APP_RELDIR}/global.xdb",
        repo_root=repo_root,
        env=env,
        clean_room=clean_room,
    )
    fx3_xdb_path = resolve_donor_file(
        f"{FX3_SHARE_APP_RELDIR}/global.xdb",
        repo_root=repo_root,
        env=env,
        clean_room=clean_room,
    )
    fx6_appfw_path = resolve_donor_file(
        FX6_APPFW_RELPATH,
        repo_root=repo_root,
        env=env,
        clean_room=clean_room,
    )

    use_local = (
        not clean_room
        and not is_forced_clean_room(env)
        and fx6_xdb_path is not None
        and fx3_xdb_path is not None
        and fx6_appfw_path is not None
    )

    if use_local:
        assert fx6_xdb_path is not None and fx3_xdb_path is not None and fx6_appfw_path is not None
        mode = "LOCAL_DONOR_VERIFIED"
        src_mode = "LOCAL_DONOR_RDONLY"
        fx6_dir = fx6_xdb_path.parent
        fx3_dir = fx3_xdb_path.parent

        fx6_xdb_audit = audit_global_xdb_file_rdonly(fx6_xdb_path, body="fx6_601", share_app_dir=fx6_dir)
        fx3_xdb_audit = audit_global_xdb_file_rdonly(fx3_xdb_path, body="fx3_702", share_app_dir=fx3_dir)

        lang_maps: Dict[str, Dict[int, Dict[int, Tuple[int, str]]]] = {}
        lang_corrupt: Dict[str, int] = {}
        for lang in TARGET_LANGUAGES:
            ns1_raw = read_bytes_rdonly(fx6_dir / f"string_{lang}.uxc")
            ns2_raw = read_bytes_rdonly(fx6_dir / f"string_{lang}_2.uxc")
            _ns1, _s1, m1, _e1, c1, err1 = parse_uxc_string_pack_slots(ns1_raw)
            _ns2, _s2, m2, _e2, c2, err2 = parse_uxc_string_pack_slots(ns2_raw)
            lang_maps[lang] = {1: m1, 2: m2}
            lang_corrupt[lang] = c1 + c2
            errors.extend(err1)
            errors.extend(err2)

        cmn_sets: Dict[int, Set[int]] = {}
        for fn in ("image_00_169.uxc", "style_cmn.uxc", "lang_cmn.uxc", "color_cmn.uxc"):
            ns_id, sset = _load_cmn_slot_set(read_bytes_rdonly(fx6_dir / fn))
            cmn_sets[ns_id] = sset

        fd = os.open(str(fx6_appfw_path), os.O_RDONLY)
        try:
            with os.fdopen(fd, "rb") as fh:
                with mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                    menu_report = audit_128_page_multilingual_menu_tree(
                        mm,
                        lang_maps,
                        cmn_sets,
                        source_mode=src_mode,
                        lang_corrupt_counts=lang_corrupt,
                    )
                    hw_predicates = evaluate_fx3_hardware_predicates(mm, lang_maps, menu_report)
        except Exception:
            raise
    else:
        mode = "CLEAN_ROOM_SYNTHETIC_VERIFIED"
        src_mode = "SYNTHETIC_CLEAN_ROOM"
        fixtures = build_clean_room_menu_fixtures()

        fx6_xdb_audit = parse_global_xdb_buffer(
            fixtures["fx6_global_xdb"],  # type: ignore[arg-type]
            body="fx6_601",
            source_mode=src_mode,
        )
        # Verify synthetic lang.uxb and fontlist.dat too
        fl6_map, fl6_errs = parse_fontlist_dat_bytes(fixtures["fx6_fontlist"])  # type: ignore[arg-type]
        l6_magic, l6_ns, l6_cnt, l6_errs = parse_lang_uxb_bytes(fixtures["fx6_lang_uxb"])  # type: ignore[arg-type]
        if fl6_errs or l6_errs:
            errors.extend(fl6_errs)
            errors.extend(l6_errs)
        fx6_xdb_audit = GlobalXdbAuditResult(
            **{
                **asdict(fx6_xdb_audit),
                "fontlist_entries": tuple(f"{k}={v}" for k, v in sorted(fl6_map.items())),
                "lang_uxb_magic_hex": l6_magic,
                "lang_uxb_namespace_id": l6_ns,
                "lang_uxb_entry_count": l6_cnt,
            }
        )

        fx3_xdb_audit = parse_global_xdb_buffer(
            fixtures["fx3_global_xdb"],  # type: ignore[arg-type]
            body="fx3_702",
            source_mode=src_mode,
        )
        fl3_map, fl3_errs = parse_fontlist_dat_bytes(fixtures["fx3_fontlist"])  # type: ignore[arg-type]
        l3_magic, l3_ns, l3_cnt, l3_errs = parse_lang_uxb_bytes(fixtures["fx3_lang_uxb"])  # type: ignore[arg-type]
        if fl3_errs or l3_errs:
            errors.extend(fl3_errs)
            errors.extend(l3_errs)
        fx3_xdb_audit = GlobalXdbAuditResult(
            **{
                **asdict(fx3_xdb_audit),
                "fontlist_entries": tuple(f"{k}={v}" for k, v in sorted(fl3_map.items())),
                "lang_uxb_magic_hex": l3_magic,
                "lang_uxb_namespace_id": l3_ns,
                "lang_uxb_entry_count": l3_cnt,
            }
        )

        uxc_packs: Dict[str, bytes] = fixtures["uxc_packs"]  # type: ignore[assignment]
        lang_maps = {}
        lang_corrupt = {}
        for lang in TARGET_LANGUAGES:
            _ns1, _s1, m1, _e1, c1, err1 = parse_uxc_string_pack_slots(uxc_packs[f"string_{lang}.uxc"])
            _ns2, _s2, m2, _e2, c2, err2 = parse_uxc_string_pack_slots(uxc_packs[f"string_{lang}_2.uxc"])
            lang_maps[lang] = {1: m1, 2: m2}
            lang_corrupt[lang] = c1 + c2
            errors.extend(err1)
            errors.extend(err2)

        cmn_sets = {}
        for fn in ("image_00_169.uxc", "style_cmn.uxc", "lang_cmn.uxc", "color_cmn.uxc"):
            ns_id, sset = _load_cmn_slot_set(uxc_packs[fn])
            cmn_sets[ns_id] = sset

        appfw_bytes: bytes = fixtures["appfw_bytes"]  # type: ignore[assignment]
        menu_report = audit_128_page_multilingual_menu_tree(
            appfw_bytes,
            lang_maps,
            cmn_sets,
            source_mode=src_mode,
            lang_corrupt_counts=lang_corrupt,
        )
        hw_predicates = evaluate_fx3_hardware_predicates(appfw_bytes, lang_maps, menu_report)

    if not fx6_xdb_audit.valid:
        errors.extend(fx6_xdb_audit.errors)
    if not fx3_xdb_audit.valid:
        errors.extend(fx3_xdb_audit.errors)
    if not menu_report.valid:
        errors.extend(menu_report.errors)

    all_hw_safe = all(p.valid and not p.null_pointer_hazard and not p.missing_widget_hazard for p in hw_predicates)
    zero_null_hazards = menu_report.null_proto_hazards == 0 and menu_report.null_name_hazards == 0 and all(
        not p.null_pointer_hazard for p in hw_predicates
    )
    if not all_hw_safe:
        errors.append("One or more FX3 hardware predicates failed safe-state verification")

    all_passed = (
        len(errors) == 0
        and fx6_xdb_audit.valid
        and fx3_xdb_audit.valid
        and menu_report.valid
        and all_hw_safe
        and zero_null_hazards
    )

    core_digest_payload = {
        "schema_version": PHASE_46_SCHEMA,
        "mode": mode,
        "fx6_xdb_sha256": fx6_xdb_audit.sha256,
        "fx3_xdb_sha256": fx3_xdb_audit.sha256,
        "pages_audited": menu_report.pages_audited,
        "total_descriptor_rows": menu_report.total_descriptor_rows,
        "total_resids_verified": menu_report.total_resids_verified,
        "hw_predicates": [p.fx3_safe_state for p in hw_predicates],
    }
    import json

    report_sha256 = hashlib.sha256(
        json.dumps(core_digest_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()

    return GlobalXdbAndMenuTreeReport(
        schema_version=PHASE_46_SCHEMA,
        mode=mode,
        all_checks_passed=all_passed,
        o_rdonly_enforced=True,
        sqlite_wal_shm_forbidden=True,
        fx6_global_xdb=fx6_xdb_audit,
        fx3_global_xdb=fx3_xdb_audit,
        menu_tree_audit=menu_report,
        hardware_predicates=hw_predicates,
        all_hardware_predicates_safe=all_hw_safe,
        zero_null_pointer_hazards=zero_null_hazards,
        report_sha256=report_sha256,
        errors=tuple(errors),
    )


def global_xdb_and_menu_tree_report_to_dict(report: GlobalXdbAndMenuTreeReport) -> Dict[str, object]:
    """Convert `GlobalXdbAndMenuTreeReport` to a deterministic JSON-serializable dict."""
    return asdict(report)
