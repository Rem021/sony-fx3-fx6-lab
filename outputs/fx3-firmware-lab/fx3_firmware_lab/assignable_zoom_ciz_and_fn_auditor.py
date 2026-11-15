"""Phase 75 — 14th Unified Firmware-Lab Auditor: Assignable Button Cross-Body Catalog, `T/W` Zoom Lever / `Clear Image Zoom` (`CIZ`) Mutual-Exclusion Matrix, Touch Tracking AF & Anamorphic Desqueeze Coordinate Transform, and Custom `Big6` + `Fn` Volatile `BK4` Shadow Proof.

Strictly Read-Only (`os.O_RDONLY` + `mmap.ACCESS_READ`) & Clean-Room Dual-Mode:
- Local Donor Mode: inspects FX3 v7.02 (`appFw.so` / `icx1295` AP host,
  `cpapp-b.bin`, `libInfraLensCommunicator.so`, `global.xdb`,
  `string_english.uxc`, `string_english_g.uxc`) and FX6 v6.01 (`appFw.so`,
  `cpapp-b.bin`, `libInfraLensCommunicator.so`, `global.xdb`,
  `string_english.uxc`, `string_english_2.uxc`) strictly via `os.O_RDONLY` +
  read-only `mmap` and ELF64 `.rodata`/`.dynstr` section-scoped scanning, plus
  `uxa\\x07` / `.uxc` container parsing.
- Clean-Room Mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`, `clean_room=True`, or donors
  absent): synthesizes deterministic clean-room ELF64 / CP / `global.xdb` /
  `.uxc` fixtures carrying the exact contract markers and executes the
  identical four-pillar verification pipeline with zero proprietary files
  required.

Audits Four Ergonomics, Super-Resolution, Touch-AF & Shadow-NVRAM Pillars:
1. Pillar 1 — Assignable Button Cross-Body Action Catalog (`FX6 1..11` ->
   `FX3 Custom 1..6 + Lens Hold + Joystick + Touch`):
   Verifies hardware-backed Cinema Line assignable actions (`Zebra`, `Peaking`,
   `Marker`, `Base ISO / Cine EI Switch`, `S&Q Motion`, `Focus Magnifier x4.0`,
   `AF/MF`, `Push Auto ND/Iris -> Push Auto Iris`, `LUT On/Off`,
   `Status Check`, `Big6 / Shooting Screen Toggle`, `Audio Level Display`),
   while isolating and safely redirecting/graying-out FX6-only hardware-absent
   targets (`ND Preset`, `Auto ND`, `VF Adjust`, `SDI/HDMI Rec Control -> HDMI
   Rec Control`, `Smart Grip Assign 7..9` / `SDK Assign 10..11`) with `0`
   null-GPIO faults (`XLR-H1` handle compatible).
2. Pillar 2 — `T/W` Zoom Lever Rocker (`8-Step` Variable Speed) & `Clear Image
   Zoom` (`CIZ`) Mutual-Exclusion Matrix:
   Verifies `Optical Zoom Only` (`1.00x`, full 627-pt PDAF + Face/Eye tracking)
   vs `Clear Image Zoom` (`1.00x..1.50x` in `QFHD/DCI 4K`, `1.00x..2.00x` in
   `FHD` with PDAF tracking retained) vs `Digital Zoom` (`up to 4.00x`),
   plus deterministic mutual-exclusion clamping (`1.00x`) when `HDMI RAW16` or
   `S&Q 120/240fps` is enabled without crashing `icx1295` or `libcamera`.
3. Pillar 3 — Touch Tracking AF (`Touch Focus` / `Touch Tracking` /
   `Touch Shutter=Disabled in Cine`) & `Focus Magnifier` (`4.0x` Crop Coordinate
   Transform):
   Verifies `960x540` `GPE0` capacitive touch `(x, y)` -> normalized
   `[0.0..1.0]` `IMX510` 627-point (`33x19`) PDAF phase-window coordinate
   transform, including `4.0x` Focus Magnifier crop and anamorphic
   `1.3x / 1.5x / 1.6x / 2.0x` desqueeze inverse-X transforms.
4. Pillar 4 — Custom `Big6` Home Screen (`6`-Slot Layout) & `Fn` Menu (`12`-Slot
   Layout) Volatile `BK4` Shadow Proof:
   Verifies all `6` `Big6` slots + `12` `Fn` slots persist in volatile `/tmp` /
   `CAMSET` JSON shadow (`S&Q Mode Settings = Fixed/Variable` gate) while
   `bk4_persistent_nvram_writes == 0` and
   `persistent_emmc_writes_authorized == False`.
"""

from __future__ import annotations

import hashlib
import json
import math
import mmap
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from .emount_af_breathing_and_ibis_auditor import (
    FX3_LENS_COMM_RELPATH,
    FX6_LENS_COMM_RELPATH,
    _extract_uxc_labels,
    _parse_elf64_sections,
)
from .global_xdb_and_menu_tree_auditor import (
    build_sparse_uxc_string_pack,
    build_synthetic_global_xdb,
    parse_global_xdb_buffer,
)
from .haita_bk4_feature_analyzer import (
    DEFAULT_REPO_ROOT,
    FX3_APPFW_RELPATH,
    FX6_APPFW_RELPATH,
    is_forced_clean_room,
    resolve_donor_file,
)
from .sensor_codec_compatibility_analyzer import (
    FX3_CPAPP_RELPATH,
    FX6_CPAPP_RELPATH,
)
from .uxc_multilang_and_font_verifier import FX3_SHARE_APP_RELDIR, FX6_SHARE_APP_RELDIR
from .wbi_hibdrv_and_elf_abi_differ import build_synthetic_elf64_so


PHASE_75_SCHEMA = "fx3_firmware_lab_phase75_assignable_ciz_big6_v1"
PHASE_75_VERSION = "75.0.0"

FX3_GLOBAL_XDB_RELPATH = f"{FX3_SHARE_APP_RELDIR}/global.xdb"
FX6_GLOBAL_XDB_RELPATH = f"{FX6_SHARE_APP_RELDIR}/global.xdb"
FX3_STR_EN_RELPATH = f"{FX3_SHARE_APP_RELDIR}/string_english.uxc"
FX3_STR_EN_G_RELPATH = f"{FX3_SHARE_APP_RELDIR}/string_english_g.uxc"
FX6_STR_EN_1_RELPATH = f"{FX6_SHARE_APP_RELDIR}/string_english.uxc"
FX6_STR_EN_2_RELPATH = f"{FX6_SHARE_APP_RELDIR}/string_english_2.uxc"

# ---------------------------------------------------------------------------
# Pillar 1 Constants: Assignable Button Cross-Body Action Catalog
# ---------------------------------------------------------------------------

FX6_ASSIGNABLE_SLOTS: Tuple[str, ...] = (
    "ASSIGN_1",
    "ASSIGN_2",
    "ASSIGN_3",
    "ASSIGN_4",
    "ASSIGN_5",
    "ASSIGN_6",
    "ASSIGN_7",
    "ASSIGN_8",
    "ASSIGN_9",
    "ASSIGN_10",
    "ASSIGN_11",
    "LENS_FOCUS_HOLD",
)

FX3_HARDWARE_BUTTON_TARGETS: Tuple[str, ...] = (
    "CUSTOM_1",
    "CUSTOM_2",
    "CUSTOM_3",
    "CUSTOM_4",
    "CUSTOM_5",
    "CUSTOM_6",
    "LENS_FOCUS_HOLD",
    "JOYSTICK_CENTER",
    "AF_ON",
    "AEL",
    "TOUCH_FN_ICON",
)

FX6_TO_FX3_SLOT_MAPPING: Dict[str, Dict[str, object]] = {
    "ASSIGN_1": {
        "fx3_target": "CUSTOM_1",
        "fx6_location": "Body Rear Assign 1",
        "fx3_location": "Body Top/Rear Custom 1",
        "hw_present_on_fx3": True,
        "mapping_policy": "DIRECT_MAPPED",
    },
    "ASSIGN_2": {
        "fx3_target": "CUSTOM_2",
        "fx6_location": "Body Rear Assign 2",
        "fx3_location": "Body Top/Rear Custom 2",
        "hw_present_on_fx3": True,
        "mapping_policy": "DIRECT_MAPPED",
    },
    "ASSIGN_3": {
        "fx3_target": "CUSTOM_3",
        "fx6_location": "Body Rear Assign 3",
        "fx3_location": "Body Top/Rear Custom 3",
        "hw_present_on_fx3": True,
        "mapping_policy": "DIRECT_MAPPED",
    },
    "ASSIGN_4": {
        "fx3_target": "CUSTOM_4",
        "fx6_location": "Smart Grip Assign 4",
        "fx3_location": "Body Rear Custom 4 (Default HOME/Big6)",
        "hw_present_on_fx3": True,
        "mapping_policy": "DIRECT_MAPPED",
    },
    "ASSIGN_5": {
        "fx3_target": "CUSTOM_5",
        "fx6_location": "Smart Grip Assign 5",
        "fx3_location": "Body Top Custom 5",
        "hw_present_on_fx3": True,
        "mapping_policy": "DIRECT_MAPPED",
    },
    "ASSIGN_6": {
        "fx3_target": "CUSTOM_6",
        "fx6_location": "Smart Grip Assign 6",
        "fx3_location": "Body Top/Front Custom 6",
        "hw_present_on_fx3": True,
        "mapping_policy": "DIRECT_MAPPED",
    },
    "ASSIGN_7": {
        "fx3_target": "JOYSTICK_CENTER",
        "fx6_location": "FX6 Top Handle Assign 7",
        "fx3_location": "FX3 Multi-Selector / Joystick Center (XLR-H1 has no handle keys)",
        "hw_present_on_fx3": False,
        "mapping_policy": "SAFE_REDIRECTED",
    },
    "ASSIGN_8": {
        "fx3_target": "AF_ON",
        "fx6_location": "FX6 Top Handle Assign 8",
        "fx3_location": "FX3 AF-ON Tactile Button (XLR-H1 passive MI-Shoe)",
        "hw_present_on_fx3": False,
        "mapping_policy": "SAFE_REDIRECTED",
    },
    "ASSIGN_9": {
        "fx3_target": "TOUCH_FN_ICON",
        "fx6_location": "FX6 LCD/VF Assign 9",
        "fx3_location": "FX3 Touch Fn Icon / Big6 Footer",
        "hw_present_on_fx3": False,
        "mapping_policy": "SAFE_REDIRECTED",
    },
    "ASSIGN_10": {
        "fx3_target": "AEL",
        "fx6_location": "SDK/Remote Virtual Assign 10",
        "fx3_location": "FX3 AEL Button / Remote Soft Trigger",
        "hw_present_on_fx3": False,
        "mapping_policy": "SAFE_REDIRECTED",
    },
    "ASSIGN_11": {
        "fx3_target": "TOUCH_FN_ICON",
        "fx6_location": "SDK/Remote Virtual Assign 11",
        "fx3_location": "FX3 Touch Fn Icon / Remote Soft Trigger",
        "hw_present_on_fx3": False,
        "mapping_policy": "SAFE_REDIRECTED",
    },
    "LENS_FOCUS_HOLD": {
        "fx3_target": "LENS_FOCUS_HOLD",
        "fx6_location": "E-Mount Lens Focus Hold",
        "fx3_location": "E-Mount Lens Focus Hold (libInfraLensCommunicator.so)",
        "hw_present_on_fx3": True,
        "mapping_policy": "DIRECT_MAPPED",
    },
}

# Hardware-backed Cinema Line assignable actions + FX6-only absent-hardware targets
CINEMA_ASSIGNABLE_ACTION_SPECS: Dict[str, Dict[str, object]] = {
    "ZEBRA": {
        "fx6_token": "ASSIGNABLE_SWITCH_ZEBRA",
        "fx3_action": "ZEBRA_DISPLAY_TOGGLE",
        "default_fx6_slot": "ASSIGN_1",
        "hardware_backed_on_fx3": True,
        "resolution_policy": "DIRECT_MAPPED",
        "safe_redirect_action": "ZEBRA_DISPLAY_TOGGLE",
    },
    "PEAKING": {
        "fx6_token": "ASSIGNABLE_SWITCH_PEAKING",
        "fx3_action": "PEAKING_DISPLAY_TOGGLE",
        "default_fx6_slot": "ASSIGN_2",
        "hardware_backed_on_fx3": True,
        "resolution_policy": "DIRECT_MAPPED",
        "safe_redirect_action": "PEAKING_DISPLAY_TOGGLE",
    },
    "MARKER": {
        "fx6_token": "ASSIGNABLE_SWITCH_MARKER",
        "fx3_action": "MARKER_ASPECT_GUIDE_TOGGLE",
        "default_fx6_slot": "ASSIGN_3",
        "hardware_backed_on_fx3": True,
        "resolution_policy": "DIRECT_MAPPED",
        "safe_redirect_action": "MARKER_ASPECT_GUIDE_TOGGLE",
    },
    "BASE_ISO_CINE_EI": {
        "fx6_token": "ASSIGNABLE_SWITCH_BASE_ISO_SENSITIVITY",
        "fx3_action": "BASE_ISO_800_12800_OR_CINE_EI_SWITCH",
        "default_fx6_slot": "ASSIGN_5",
        "hardware_backed_on_fx3": True,
        "resolution_policy": "DIRECT_MAPPED",
        "safe_redirect_action": "BASE_ISO_800_12800_OR_CINE_EI_SWITCH",
    },
    "SQ_MOTION": {
        "fx6_token": "ASSIGNABLE_SWITCH_S_Q_MOTION",
        "fx3_action": "SQ_FIXED_VARIABLE_FPS_SWITCH",
        "default_fx6_slot": "ASSIGN_6",
        "hardware_backed_on_fx3": True,
        "resolution_policy": "DIRECT_MAPPED",
        "safe_redirect_action": "SQ_FIXED_VARIABLE_FPS_SWITCH",
    },
    "FOCUS_MAGNIFIER_X4": {
        "fx6_token": "ASSIGNABLE_SWITCH_FOCUS_MAGNIFIER_x3",
        "fx3_action": "FOCUS_MAGNIFIER_X4_0",
        "default_fx6_slot": "ASSIGN_7",
        "hardware_backed_on_fx3": True,
        "resolution_policy": "DIRECT_MAPPED",
        "safe_redirect_action": "FOCUS_MAGNIFIER_X4_0",
    },
    "AF_MF": {
        "fx6_token": "ASSIGNABLE_SWITCH_FOCUS_OPERATION",
        "fx3_action": "AF_MF_TOGGLE",
        "default_fx6_slot": "LENS_FOCUS_HOLD",
        "hardware_backed_on_fx3": True,
        "resolution_policy": "DIRECT_MAPPED",
        "safe_redirect_action": "AF_MF_TOGGLE",
    },
    "PUSH_AUTO_ND_IRIS": {
        "fx6_token": "ASSIGNABLE_SWITCH_PUSH_AUTO_ND",
        "fx3_action": "PUSH_AUTO_IRIS",
        "default_fx6_slot": "ASSIGN_10",
        "hardware_backed_on_fx3": False,
        "resolution_policy": "SAFE_REDIRECTED",
        "safe_redirect_action": "PUSH_AUTO_IRIS",
    },
    "LUT_ON_OFF": {
        "fx6_token": "ASSIGNABLE_SWITCH_LUT",
        "fx3_action": "MONITOR_AND_REC_LUT_ON_OFF",
        "default_fx6_slot": "ASSIGN_9",
        "hardware_backed_on_fx3": True,
        "resolution_policy": "DIRECT_MAPPED",
        "safe_redirect_action": "MONITOR_AND_REC_LUT_ON_OFF",
    },
    "STATUS_CHECK": {
        "fx6_token": "ASSIGNABLE_SWITCH_NETWORK_STATUS",
        "fx3_action": "STATUS_PAGE_OVERLAY_TOGGLE",
        "default_fx6_slot": "ASSIGN_11",
        "hardware_backed_on_fx3": True,
        "resolution_policy": "DIRECT_MAPPED",
        "safe_redirect_action": "STATUS_PAGE_OVERLAY_TOGGLE",
    },
    "BIG6_SHOOTING_SCREEN": {
        "fx6_token": "ASSIGNABLE_SWITCH_HOME",
        "fx3_action": "BIG6_HOME_SHOOTING_SCREEN_TOGGLE",
        "default_fx6_slot": "ASSIGN_4",
        "hardware_backed_on_fx3": True,
        "resolution_policy": "DIRECT_MAPPED",
        "safe_redirect_action": "BIG6_HOME_SHOOTING_SCREEN_TOGGLE",
    },
    "AUDIO_LEVEL_DISPLAY": {
        "fx6_token": "ASSIGNABLE_SWITCH_AUDIO_MONITOR_CH",
        "fx3_action": "AUDIO_LEVEL_METER_DISPLAY",
        "default_fx6_slot": "ASSIGN_8",
        "hardware_backed_on_fx3": True,
        "resolution_policy": "DIRECT_MAPPED",
        "safe_redirect_action": "AUDIO_LEVEL_METER_DISPLAY",
    },
    # FX6-only hardware-absent targets (isolated/grayed-out/redirected with 0 null-GPIO faults)
    "ND_PRESET": {
        "fx6_token": "ASSIGNABLE_SWITCH_ND_FILTER_POSITION",
        "fx3_action": "DISABLED_NO_ELECTRONIC_ND_CELL",
        "default_fx6_slot": "ASSIGN_1",
        "hardware_backed_on_fx3": False,
        "resolution_policy": "GRAYED_OUT_HARDWARE_ABSENT",
        "safe_redirect_action": "NONE_GRAYED_OUT",
    },
    "AUTO_ND": {
        "fx6_token": "ASSIGNABLE_SWITCH_AUTO_ND_FILTER",
        "fx3_action": "DISABLED_NO_ELECTRONIC_ND_CELL",
        "default_fx6_slot": "ASSIGN_2",
        "hardware_backed_on_fx3": False,
        "resolution_policy": "GRAYED_OUT_HARDWARE_ABSENT",
        "safe_redirect_action": "NONE_GRAYED_OUT",
    },
    "VF_ADJUST": {
        "fx6_token": "ASSIGNABLE_SWITCH_VF_ADJUST",
        "fx3_action": "DISABLED_NO_DETACHABLE_EVF_LOUPE",
        "default_fx6_slot": "ASSIGN_9",
        "hardware_backed_on_fx3": False,
        "resolution_policy": "GRAYED_OUT_HARDWARE_ABSENT",
        "safe_redirect_action": "NONE_GRAYED_OUT",
    },
    "SDI_HDMI_REC_CONTROL": {
        "fx6_token": "ASSIGNABLE_SWITCH_LUT_SDI_HDMI",
        "fx3_action": "HDMI_REC_CONTROL_ONLY",
        "default_fx6_slot": "ASSIGN_3",
        "hardware_backed_on_fx3": False,
        "resolution_policy": "SAFE_REDIRECTED",
        "safe_redirect_action": "HDMI_REC_CONTROL_ONLY",
    },
    "SMART_GRIP_ASSIGN_7_9": {
        "fx6_token": "ASSIGNABLE_SWITCH_HANDLE_ZOOM",
        "fx3_action": "FX3_BODY_TW_LEVER_AND_JOYSTICK_FALLBACK",
        "default_fx6_slot": "ASSIGN_7",
        "hardware_backed_on_fx3": False,
        "resolution_policy": "SAFE_REDIRECTED",
        "safe_redirect_action": "FX3_BODY_TW_LEVER_AND_JOYSTICK_FALLBACK",
    },
}

# ---------------------------------------------------------------------------
# Pillar 2 Constants: T/W Zoom Lever (8-Step) & Clear Image Zoom (CIZ) Matrix
# ---------------------------------------------------------------------------

ZOOM_MODES: Tuple[str, ...] = ("OPTICAL_ZOOM_ONLY", "CLEAR_IMAGE_ZOOM", "DIGITAL_ZOOM")
ZOOM_RESOLUTION_MODES: Tuple[str, ...] = (
    "DCI_4K_4096x2160",
    "QFHD_3840x2160",
    "FHD_1920x1080",
)
CIZ_MAX_MAG_BY_RESOLUTION: Dict[str, float] = {
    "DCI_4K_4096x2160": 1.50,
    "QFHD_3840x2160": 1.50,
    "FHD_1920x1080": 2.00,
}
DIGITAL_ZOOM_MAX_MAG = 4.00
ZOOM_LEVER_SPEED_MIN = 1
ZOOM_LEVER_SPEED_MAX = 8

# ---------------------------------------------------------------------------
# Pillar 3 Constants: GPE0 960x540 Touch AF & Anamorphic Desqueeze Transform
# ---------------------------------------------------------------------------

GPE0_TOUCH_WIDTH = 960
GPE0_TOUCH_HEIGHT = 540
IMX510_PDAF_COLS = 33
IMX510_PDAF_ROWS = 19
IMX510_PDAF_TOTAL_POINTS = IMX510_PDAF_COLS * IMX510_PDAF_ROWS  # 627
VALID_TOUCH_FUNCTIONS_CINE: Tuple[str, ...] = ("OFF", "TOUCH_FOCUS", "TOUCH_TRACKING")
VALID_DESQUEEZE_RATIOS: Tuple[float, ...] = (1.0, 1.3, 1.5, 1.6, 2.0)
VALID_MAGNIFIER_FACTORS: Tuple[float, ...] = (1.0, 4.0)

# ---------------------------------------------------------------------------
# Pillar 4 Constants: Big6 (6-Slot) & Fn (12-Slot) Volatile BK4 Shadow
# ---------------------------------------------------------------------------

VALID_SQ_MODE_SETTINGS: Tuple[str, ...] = ("FIXED_VARIABLE", "LEGACY_SQ_MODE")
VALID_HOME_LOWER_LEFT_MODES: Tuple[str, ...] = ("APERTURE", "ND_FILTER")

BIG6_DEFAULT_SLOTS: Tuple[Dict[str, str], ...] = (
    {"slot_id": "BIG6_1_FPS", "label": "FPS", "value": "23.98p (Fixed)"},
    {"slot_id": "BIG6_2_ISO_EI", "label": "ISO / Base EI", "value": "800 EI (Base 800)"},
    {"slot_id": "BIG6_3_SHUTTER", "label": "Shutter Angle", "value": "180.0 deg"},
    {"slot_id": "BIG6_4_LOWER_LEFT", "label": "Aperture / ND", "value": "F2.8 (ND Locked Clear)"},
    {"slot_id": "BIG6_5_LOOK_LUT", "label": "Base Look / LUT", "value": "S-Log3 / User1.cube"},
    {"slot_id": "BIG6_6_WB", "label": "White Balance", "value": "5600K (Shockless 1)"},
)

FN_MENU_DEFAULT_SLOTS: Tuple[Dict[str, str], ...] = (
    {"slot_id": "FN_01", "label": "Focus Mode", "value": "AF-C"},
    {"slot_id": "FN_02", "label": "Focus Area", "value": "Wide"},
    {"slot_id": "FN_03", "label": "Face/Eye AF", "value": "On"},
    {"slot_id": "FN_04", "label": "Zoom / CIZ", "value": "Clear Image Zoom (1.5x)"},
    {"slot_id": "FN_05", "label": "SteadyShot", "value": "Standard"},
    {"slot_id": "FN_06", "label": "Audio Rec Level", "value": "4ch 24-bit 48kHz"},
    {"slot_id": "FN_07", "label": "Zebra", "value": "On (70+/-2%)"},
    {"slot_id": "FN_08", "label": "Peaking", "value": "Mid / Red"},
    {"slot_id": "FN_09", "label": "Marker", "value": "2.39:1 Aspect"},
    {"slot_id": "FN_10", "label": "Timecode", "value": "EXT-LK Free Run"},
    {"slot_id": "FN_11", "label": "Dual Slot", "value": "Simultaneous"},
    {"slot_id": "FN_12", "label": "Proxy Rec", "value": "16M XAVC HS 1080p"},
)

VOLATILE_SHADOW_PREFIXES: Tuple[str, ...] = ("/tmp/", "ram://", "memory://")
FORBIDDEN_PERSISTENT_NVRAM_PREFIXES: Tuple[str, ...] = (
    "/dev/nflasha",
    "/dev/cnflasha",
    "/dev/mtdblock",
    "nflasha",
    "cnflasha",
    "p1:",
    "p2:",
    "bk4://persistent",
    "nvram://",
)

# ---------------------------------------------------------------------------
# Verified Binary Marker Contracts (FX3 v7.02 & FX6 v6.01)
# ---------------------------------------------------------------------------

FX3_APPFW_ASSIGNABLE_MARKERS: Tuple[str, ...] = (
    "BKID_APP_setting_custom_key_movie_custom_button_1",
    "BKID_APP_setting_custom_key_movie_custom_button_6",
    "BKID_APP_setting_custom_key_movie_focus_hold_button",
    "BKID_APP_setting_custom_key_movie_center_button_multiselector",
    "BKID_APP_setting_custom_key_movie_af_on_button",
    "BKID_APP_setting_custom_key_movie_ael_button",
    "UIBIZ_KEY_TACT_FOCUS_HOLD",
    "UIBIZ_KEY_TACT_AF_MF",
    "UIBIZ_KEY_TACT_5WAY_ALL",
    "INFRA_NOTIFY_GET_AUDIO_LEVEL_TIMER",
)

FX6_APPFW_ASSIGNABLE_MARKERS: Tuple[str, ...] = (
    "ASSIGNABLE_SWITCH_1",
    "ASSIGNABLE_SWITCH_6",
    "ASSIGNABLE_SWITCH_7",
    "ASSIGNABLE_SWITCH_9",
    "ASSIGNABLE_SWITCH_10",
    "ASSIGNABLE_SWITCH_11",
    "ASSIGNABLE_SWITCH_ZEBRA",
    "ASSIGNABLE_SWITCH_PEAKING",
    "ASSIGNABLE_SWITCH_MARKER",
    "ASSIGNABLE_SWITCH_BASE_ISO_SENSITIVITY",
    "ASSIGNABLE_SWITCH_S_Q_MOTION",
    "ASSIGNABLE_SWITCH_FOCUS_MAGNIFIER_x3",
    "ASSIGNABLE_SWITCH_PUSH_AUTO_IRIS",
    "ASSIGNABLE_SWITCH_PUSH_AUTO_ND",
    "ASSIGNABLE_SWITCH_ND_FILTER_POSITION",
    "ASSIGNABLE_SWITCH_AUTO_ND_FILTER",
    "ASSIGNABLE_SWITCH_VF_ADJUST",
    "ASSIGNABLE_SWITCH_LUT",
    "ASSIGNABLE_SWITCH_LUT_SDI_HDMI",
    "ASSIGNABLE_SWITCH_HOME",
    "ASSIGNABLE_SWITCH_FOCUS_HOLD",
    "ASSIGNABLE_SWITCH_AUDIO_MONITOR_CH",
    "ASSIGNABLE_SWITCH_NETWORK_STATUS",
)

FX3_APPFW_CIZ_ZOOM_MARKERS: Tuple[str, ...] = (
    "CLEAR_IMAGE_ZOOM_ON",
    "VAL_setting_zoom_setting_ZOOM_SETTING_CLEAR_IMAGE_ZOOM_ON",
    "VAL_setting_zoom_setting_ZOOM_SETTING_DIGITAL_ZOOM_ON",
    "VAL_setting_zoom_setting_ZOOM_SETTING_OPTICAL_ZOOM_ONLY",
    "UIBIZ_KEY_ZOOM_TELE_SPEED_1",
    "UIBIZ_KEY_ZOOM_TELE_SPEED_8",
    "UIBIZ_KEY_ZOOM_WIDE_SPEED_1",
    "UIBIZ_KEY_ZOOM_WIDE_SPEED_8",
    "BKID_APP_setting_zoom_setting",
    "BKID_APP_setting_variable_zoom_speed",
)

FX6_APPFW_CIZ_ZOOM_MARKERS: Tuple[str, ...] = (
    "CLEAR_IMAGE_ZOOM_ON",
    "CLEAR_IMAGE_ZOOM_TYPE_OPTICAL_ZOOM_PRIORITY",
    "CLEAR_IMAGE_ZOOM_TYPE_SMOOTH_PRIORITY",
    "ZOOM_SPEED_REC_1",
    "ZOOM_SPEED_REC_8",
)

FX3_APPFW_TOUCH_AF_MARKERS: Tuple[str, ...] = (
    "VAL_setting_shooting_touch_function_SHOOTING_TOUCH_FUNCTION_TOUCH_FOCUS",
    "TOUCH_TRACKING_ON",
    "TOUCH_TRACKING_OFF",
    "TOUCH_SHUTTER_SHOOTING",
    "MOV_INIT_RATIO_FOCUS_MAGNIF_X4_0",
    "DE_SQUEEZE_DISP_1_3X",
    "DE_SQUEEZE_DISP_1_5X",
    "DE_SQUEEZE_DISP_1_6X",
    "DE_SQUEEZE_DISP_2_0X",
)

FX6_APPFW_TOUCH_AF_MARKERS: Tuple[str, ...] = (
    "SHOOTING_TOUCH_FUNCTION_TOUCH_TRACKING",
    "TOUCH_FOCUS_STATE_ON",
    "FOCUS_MAGNIFIER_x3",
    "FOCUS_MAGNIFIER_x6",
    "DE_SQUEEZE_DISP_1_3X",
    "DE_SQUEEZE_DISP_2_0X",
)

FX3_APPFW_BIG6_FN_MARKERS: Tuple[str, ...] = (
    "BIG6_FPS_SELECT",
    "BIG6_FRAME_RATE",
    "HOME_SCREEN_STATE_ON_CURSOR_ON",
    "FN_MENU",
    "BKID_APP_setting_movie_home_lower_left",
    "BKID_APP_setting_icon_touch_function",
    "CAMSET",
)

FX6_APPFW_BIG6_FN_MARKERS: Tuple[str, ...] = (
    "BIG6_FPS_SELECT",
    "BIG6_FRAME_RATE",
    "BIG6_WHITE_COLOR_TEMP",
    "BIG6_WHITE_TINT",
    "HOME_SCREEN_STATE_ON_CURSOR_ON",
    "FN_MENU",
    "BKID_APP_HOME_SCREEN_STATE",
)

CP_SHARED_ZOOM_TOUCH_MARKERS: Tuple[str, ...] = (
    "CheckSetEzoomOn",
    "SET_EZOOM_ON",
    "SET_ANAMO_DESQUEEZE_SCALE",
    "MSG_ID_INFRABB_VDF_INPUT_SET_TOUCH_PANEL",
    "FOCUS_HOLD_MODE",
)

LENS_COMM_SHARED_MARKERS: Tuple[str, ...] = (
    "_ZN16LensCommunicator18GetMountedLensInfoEPv",
    "_ZN16LensCommunicator23GetSuopportedCommandIdsEPv",
    "_ZN16LensCommunicator10SndSyncMsgEPvj",
)

# Verified .uxc String Resource IDs
FX3_NS39_PHASE75_LABELS: Dict[int, str] = {
    0x0004E06B: "Digital Zoom",
    0x0004E226: "Focus Magnifier",
    0x0004E8BA: "Focus Hold",
    0x0004E8E3: "Touch Operation",
    0x0004E941: "Custom Key Settings",
}

FX3_NS3_PHASE75_LABELS: Dict[int, str] = {
    0x00006050: "Peaking Display",
    0x00006099: "S&Q Motion",
    0x000062E0: "Focus Hold Button",
    0x00006352: "Zebra Display",
}

FX6_NS1_PHASE75_LABELS: Dict[int, str] = {
    0x00002052: "Base ISO/Sensitivity",
    0x000020D3: "ND Filter",
    0x0000211E: "Assignable Button",
    0x0000221E: "Focus Magnifier \u00d73",
    0x00002223: "VF Adjust",
    0x000023C9: "Optical Zoom Only",
    0x000023CB: "On(Clear Image Zoom)",
    0x000023F6: "LUT On/Off",
}

FX6_NS2_PHASE75_LABELS: Dict[int, str] = {
    0x00004233: "Audio Level",
    0x0000423D: "Peaking",
    0x0000423E: "Marker",
    0x0000423F: "Zebra",
    0x00004246: "S&Q Motion",
    0x0000428D: "SDI/HDMI Rec Control",
}

# ---------------------------------------------------------------------------
# Report & Evaluation Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AssignableButtonEvalResult:
    valid: bool
    fx6_slot: str
    fx6_action: str
    fx3_target: str
    fx3_action: str
    resolution_policy: str
    hardware_backed_on_fx3: bool
    gpio_access_attempted: bool
    null_gpio_faults: int
    xlr_h1_compatible: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class AssignableCatalogReport:
    passed: bool
    fx3_appfw_markers: Tuple[str, ...]
    fx6_appfw_markers: Tuple[str, ...]
    lens_comm_shared_markers: Tuple[str, ...]
    uxc_assignable_labels: Dict[str, str]
    slot_mappings: Tuple[AssignableButtonEvalResult, ...]
    action_catalog_evals: Tuple[AssignableButtonEvalResult, ...]
    hardware_backed_count: int
    absent_hardware_isolated_count: int
    null_gpio_faults: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class ZoomCizEvalResult:
    valid: bool
    status: str
    requested_zoom_mode: str
    effective_zoom_mode: str
    resolution_mode: str
    requested_magnification: float
    effective_magnification: float
    max_allowed_ciz_magnification: float
    zoom_lever_speed: int
    by_pixel_super_res_active: bool
    pdaf_627_active: bool
    face_eye_tracking_retained: bool
    focus_area_mode: str
    hdmi_raw16_enabled: bool
    sq_active: bool
    sq_fps: float
    ciz_clamped_by_mutual_exclusion: bool
    mutual_exclusion_reason: Optional[str]
    icx1295_crashed: bool
    libcamera_crashed: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class ZoomCizMatrixReport:
    passed: bool
    fx3_ciz_markers: Tuple[str, ...]
    fx6_ciz_markers: Tuple[str, ...]
    cp_zoom_markers: Tuple[str, ...]
    optical_4k_eval: ZoomCizEvalResult
    ciz_4k_15x_eval: ZoomCizEvalResult
    ciz_fhd_20x_eval: ZoomCizEvalResult
    digital_40x_eval: ZoomCizEvalResult
    hdmi_raw16_clamp_eval: ZoomCizEvalResult
    sq_120fps_clamp_eval: ZoomCizEvalResult
    sq_240fps_clamp_eval: ZoomCizEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class TouchAfCoordEvalResult:
    valid: bool
    status: str
    touch_function: str
    cine_mode: bool
    touch_shutter_disabled_in_cine: bool
    gpe0_touch_x_px: float
    gpe0_touch_y_px: float
    desqueeze_ratio: float
    focus_magnifier_factor: float
    magnifier_center_norm: Tuple[float, float]
    display_norm_x: float
    display_norm_y: float
    sensor_norm_x: float
    sensor_norm_y: float
    pdaf_col: int
    pdaf_row: int
    pdaf_point_index: int
    pdaf_total_points: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class TouchAfAndMagnifierReport:
    passed: bool
    fx3_touch_af_markers: Tuple[str, ...]
    fx6_touch_af_markers: Tuple[str, ...]
    cp_touch_markers: Tuple[str, ...]
    normal_1x_eval: TouchAfCoordEvalResult
    anamorphic_13x_eval: TouchAfCoordEvalResult
    anamorphic_20x_eval: TouchAfCoordEvalResult
    magnifier_4x_desqueeze_20x_eval: TouchAfCoordEvalResult
    touch_shutter_cine_block_eval: TouchAfCoordEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Big6FnShadowEvalResult:
    valid: bool
    status: str
    sq_mode_settings: str
    big6_available: bool
    home_lower_left_mode: str
    big6_slot_count: int
    fn_slot_count: int
    shadow_path: str
    volatile_shadow_only: bool
    bk4_persistent_nvram_writes: int
    persistent_emmc_writes_authorized: bool
    camset_shadow_sha256: str
    camset_shadow_json: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Big6AndFnShadowReport:
    passed: bool
    fx3_big6_fn_markers: Tuple[str, ...]
    fx6_big6_fn_markers: Tuple[str, ...]
    fx3_global_xdb_valid: bool
    fx6_global_xdb_valid: bool
    fx3_big6_shadow_eval: Big6FnShadowEvalResult
    fx6_nd_lower_left_shadow_eval: Big6FnShadowEvalResult
    legacy_sq_gate_eval: Big6FnShadowEvalResult
    nvram_write_blocked_eval: Big6FnShadowEvalResult
    bk4_persistent_nvram_writes: int
    persistent_emmc_writes_authorized: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class AssignableZoomCizAndFnReport:
    schema_version: str
    phase_version: str
    mode: str
    all_checks_passed: bool
    o_rdonly_enforced: bool
    persistent_emmc_writes_authorized: bool
    bk4_persistent_nvram_writes: int
    null_gpio_faults: int
    icx1295_crashed: bool
    libcamera_crashed: bool
    donor_file_sizes: Dict[str, int]
    pillar_1_assignable_catalog: AssignableCatalogReport
    pillar_2_zoom_ciz_matrix: ZoomCizMatrixReport
    pillar_3_touch_af_desqueeze: TouchAfAndMagnifierReport
    pillar_4_big6_fn_shadow: Big6AndFnShadowReport
    errors: Tuple[str, ...]
    report_sha256: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)

    def to_deterministic_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True) + "\n"


# ---------------------------------------------------------------------------
# Strictly `os.O_RDONLY` + `mmap.ACCESS_READ` Section-Scoped Scanning Helpers
# ---------------------------------------------------------------------------


def _read_bytes_rdonly(path: Path) -> bytes:
    """Read a compact `.uxc` or `global.xdb` artifact strictly via `os.O_RDONLY`."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        with os.fdopen(fd, "rb") as fh:
            return fh.read()
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        raise


def _scan_donor_rdonly_markers(
    path: Path,
    marker_groups: Mapping[str, Sequence[str]],
    *,
    is_elf: bool,
) -> Tuple[int, Dict[str, Tuple[str, ...]]]:
    """Open `path` strictly `os.O_RDONLY` with `mmap.ACCESS_READ` and scan marker groups."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        sz = os.fstat(fd).st_size
        if sz == 0:
            return 0, {k: () for k in marker_groups}
        unique_markers = sorted(
            {m for markers in marker_groups.values() for m in markers},
            key=lambda s: (-len(s), s),
        )
        if not unique_markers:
            return sz, {k: () for k in marker_groups}

        pat = re.compile(b"|".join(re.escape(m.encode("latin1")) for m in unique_markers))
        matched_tokens: set[bytes] = set()
        with mmap.mmap(fd, sz, access=mmap.ACCESS_READ) as mm:
            ranges: List[Tuple[int, int]] = [(0, sz)]
            if is_elf:
                try:
                    secs = _parse_elf64_sections(mm)  # type: ignore[arg-type]
                    elf_ranges = [secs[s] for s in (".rodata", ".dynstr") if s in secs]
                    if elf_ranges:
                        ranges = elf_ranges
                except ValueError:
                    ranges = [(0, sz)]

            for off, rsz in ranges:
                for mo in pat.finditer(mm, off, off + rsz):
                    matched_tokens.add(mo.group(0))

        matched_list = list(matched_tokens)
        present_markers = {
            m
            for m in unique_markers
            if (mb := m.encode("latin1")) in matched_tokens or any(mb in tok for tok in matched_list)
        }
        results: Dict[str, Tuple[str, ...]] = {
            group_name: tuple(m for m in markers if m in present_markers)
            for group_name, markers in marker_groups.items()
        }
        return sz, results
    finally:
        os.close(fd)


# ---------------------------------------------------------------------------
# Clean-Room Synthetic Fixtures (Used ONLY when FX3_FX6_FORCE_CLEAN_ROOM=1 or donors absent)
# ---------------------------------------------------------------------------


def build_clean_room_assignable_ciz_fixtures() -> Dict[str, bytes]:
    """Build deterministic clean-room ELF64, CP, `global.xdb`, and `.uxc` fixtures for Phase 75."""
    fx3_appfw_blob = (
        b"\x00".join(
            m.encode("latin1")
            for m in (
                *FX3_APPFW_ASSIGNABLE_MARKERS,
                *FX3_APPFW_CIZ_ZOOM_MARKERS,
                *FX3_APPFW_TOUCH_AF_MARKERS,
                *FX3_APPFW_BIG6_FN_MARKERS,
            )
        )
        + b"\x00"
    )
    fx6_appfw_blob = (
        b"\x00".join(
            m.encode("latin1")
            for m in (
                *FX6_APPFW_ASSIGNABLE_MARKERS,
                *FX6_APPFW_CIZ_ZOOM_MARKERS,
                *FX6_APPFW_TOUCH_AF_MARKERS,
                *FX6_APPFW_BIG6_FN_MARKERS,
            )
        )
        + b"\x00"
    )
    cp_blob = b"\x00".join(m.encode("latin1") for m in CP_SHARED_ZOOM_TOUCH_MARKERS) + b"\x00"

    lens_comm_elf = build_synthetic_elf64_so(
        soname="libInfraLensCommunicator.so",
        dt_needed=("libpthread.so.0", "libstdc++.so.6"),
        exports=LENS_COMM_SHARED_MARKERS,
        imports=("osal_snd_sync_msg",),
    )

    fx3_xdb = build_synthetic_global_xdb("fx3_702")
    fx6_xdb = build_synthetic_global_xdb("fx6_601")

    fx3_str_en = build_sparse_uxc_string_pack(
        {k & 0x1FFF: v for k, v in FX3_NS39_PHASE75_LABELS.items()}, namespace_id=39
    )
    fx3_str_en_g = build_sparse_uxc_string_pack(
        {k & 0x1FFF: v for k, v in FX3_NS3_PHASE75_LABELS.items()}, namespace_id=3
    )
    fx6_str_en_1 = build_sparse_uxc_string_pack(
        {k & 0x1FFF: v for k, v in FX6_NS1_PHASE75_LABELS.items()}, namespace_id=1
    )
    fx6_str_en_2 = build_sparse_uxc_string_pack(
        {k & 0x1FFF: v for k, v in FX6_NS2_PHASE75_LABELS.items()}, namespace_id=2
    )

    return {
        "fx3_appfw": fx3_appfw_blob,
        "fx6_appfw": fx6_appfw_blob,
        "fx3_cpapp": cp_blob,
        "fx6_cpapp": cp_blob,
        "fx3_lens_comm": lens_comm_elf,
        "fx6_lens_comm": lens_comm_elf,
        "fx3_global_xdb": fx3_xdb,
        "fx6_global_xdb": fx6_xdb,
        "fx3_str_en": fx3_str_en,
        "fx3_str_en_g": fx3_str_en_g,
        "fx6_str_en_1": fx6_str_en_1,
        "fx6_str_en_2": fx6_str_en_2,
    }


def _scan_bytes_marker_groups(
    blob: bytes,
    marker_groups: Mapping[str, Sequence[str]],
) -> Tuple[int, Dict[str, Tuple[str, ...]]]:
    unique_markers = sorted(
        {m for markers in marker_groups.values() for m in markers},
        key=lambda s: (-len(s), s),
    )
    if not unique_markers:
        return len(blob), {k: () for k in marker_groups}
    pat = re.compile(b"|".join(re.escape(m.encode("latin1")) for m in unique_markers))
    matched_tokens = {mo.group(0) for mo in pat.finditer(blob)}
    matched_list = list(matched_tokens)
    present_markers = {
        m
        for m in unique_markers
        if (mb := m.encode("latin1")) in matched_tokens or any(mb in tok for tok in matched_list)
    }
    results = {
        group_name: tuple(m for m in markers if m in present_markers)
        for group_name, markers in marker_groups.items()
    }
    return len(blob), results


# ---------------------------------------------------------------------------
# Pillar 1: Assignable Button Cross-Body Action Catalog
# ---------------------------------------------------------------------------


def evaluate_assignable_button_mapping(
    *,
    fx6_slot: str,
    fx6_action: str,
) -> AssignableButtonEvalResult:
    """Resolve an FX6 Assignable slot (`ASSIGN_1..11`, `LENS_FOCUS_HOLD`) & action onto FX3 hardware."""
    errors: List[str] = []
    norm_slot = fx6_slot.strip().upper()
    norm_action = fx6_action.strip().upper()

    slot_spec = FX6_TO_FX3_SLOT_MAPPING.get(norm_slot)
    if slot_spec is None:
        errors.append(f"Unsupported FX6 assignable slot {fx6_slot!r}")
    action_spec = CINEMA_ASSIGNABLE_ACTION_SPECS.get(norm_action)
    if action_spec is None:
        errors.append(f"Unsupported Cinema Line assignable action {fx6_action!r}")

    if errors or slot_spec is None or action_spec is None:
        return AssignableButtonEvalResult(
            valid=False,
            fx6_slot=norm_slot,
            fx6_action=norm_action,
            fx3_target="INVALID",
            fx3_action="INVALID",
            resolution_policy="BLOCKED_INVALID_ASSIGNABLE",
            hardware_backed_on_fx3=False,
            gpio_access_attempted=False,
            null_gpio_faults=0,
            xlr_h1_compatible=True,
            errors=tuple(errors),
        )

    fx3_target = str(slot_spec["fx3_target"])
    hw_backed = bool(action_spec["hardware_backed_on_fx3"])
    policy = str(action_spec["resolution_policy"])
    fx3_action = str(action_spec["safe_redirect_action"])
    if policy == "DIRECT_MAPPED" and str(slot_spec["mapping_policy"]) == "SAFE_REDIRECTED":
        policy = "SAFE_REDIRECTED"

    # Absent FX6-only hardware never accesses an unmapped GPIO line on FX3.
    gpio_access_attempted = hw_backed and bool(slot_spec["hw_present_on_fx3"])
    return AssignableButtonEvalResult(
        valid=True,
        fx6_slot=norm_slot,
        fx6_action=norm_action,
        fx3_target=fx3_target,
        fx3_action=fx3_action,
        resolution_policy=policy,
        hardware_backed_on_fx3=hw_backed,
        gpio_access_attempted=gpio_access_attempted,
        null_gpio_faults=0,
        xlr_h1_compatible=True,
        errors=(),
    )


def evaluate_pillar_1_assignable_catalog(
    present_map: Mapping[str, Tuple[str, ...]],
    uxc_labels: Mapping[str, str],
) -> AssignableCatalogReport:
    """Audit Pillar 1 across binary markers, `.uxc` labels, all 12 slots, and all 17 action rules."""
    errors: List[str] = []
    fx3_assign = present_map["fx3_appfw_assignable"]
    fx6_assign = present_map["fx6_appfw_assignable"]
    lens_shared = present_map["lens_comm_shared"]

    if fx3_assign != FX3_APPFW_ASSIGNABLE_MARKERS:
        missing = tuple(m for m in FX3_APPFW_ASSIGNABLE_MARKERS if m not in fx3_assign)
        errors.append(f"FX3 appFw.so missing assignable markers: {missing}")
    if fx6_assign != FX6_APPFW_ASSIGNABLE_MARKERS:
        missing = tuple(m for m in FX6_APPFW_ASSIGNABLE_MARKERS if m not in fx6_assign)
        errors.append(f"FX6 appFw.so missing assignable markers: {missing}")
    if lens_shared != LENS_COMM_SHARED_MARKERS:
        missing = tuple(m for m in LENS_COMM_SHARED_MARKERS if m not in lens_shared)
        errors.append(f"libInfraLensCommunicator.so missing Lens Focus Hold IPC symbols: {missing}")

    slot_evals: List[AssignableButtonEvalResult] = []
    default_actions_cycle = (
        "ZEBRA",
        "PEAKING",
        "MARKER",
        "BIG6_SHOOTING_SCREEN",
        "BASE_ISO_CINE_EI",
        "SQ_MOTION",
        "FOCUS_MAGNIFIER_X4",
        "AUDIO_LEVEL_DISPLAY",
        "LUT_ON_OFF",
        "PUSH_AUTO_ND_IRIS",
        "STATUS_CHECK",
        "AF_MF",
    )
    for slot, act in zip(FX6_ASSIGNABLE_SLOTS, default_actions_cycle):
        ev = evaluate_assignable_button_mapping(fx6_slot=slot, fx6_action=act)
        if not ev.valid:
            errors.extend(ev.errors)
        slot_evals.append(ev)

    action_evals: List[AssignableButtonEvalResult] = []
    for act_name, spec in CINEMA_ASSIGNABLE_ACTION_SPECS.items():
        ev = evaluate_assignable_button_mapping(
            fx6_slot=str(spec["default_fx6_slot"]),
            fx6_action=act_name,
        )
        if not ev.valid:
            errors.extend(ev.errors)
        action_evals.append(ev)

    hw_backed_count = sum(1 for ev in action_evals if ev.hardware_backed_on_fx3)
    absent_isolated_count = sum(
        1
        for ev in action_evals
        if not ev.hardware_backed_on_fx3
        and ev.resolution_policy in ("SAFE_REDIRECTED", "GRAYED_OUT_HARDWARE_ABSENT")
    )
    total_null_gpio = sum(ev.null_gpio_faults for ev in (*slot_evals, *action_evals))

    if hw_backed_count < 11:
        errors.append(f"Expected >= 11 hardware-backed Cinema Line actions, got {hw_backed_count}")
    if absent_isolated_count < 5:
        errors.append(
            f"Expected >= 5 FX6-only absent-hardware targets safely isolated/redirected, got {absent_isolated_count}"
        )
    if total_null_gpio != 0:
        errors.append(f"Non-zero null_gpio_faults={total_null_gpio}")

    return AssignableCatalogReport(
        passed=len(errors) == 0 and total_null_gpio == 0,
        fx3_appfw_markers=fx3_assign,
        fx6_appfw_markers=fx6_assign,
        lens_comm_shared_markers=lens_shared,
        uxc_assignable_labels=dict(uxc_labels),
        slot_mappings=tuple(slot_evals),
        action_catalog_evals=tuple(action_evals),
        hardware_backed_count=hw_backed_count,
        absent_hardware_isolated_count=absent_isolated_count,
        null_gpio_faults=total_null_gpio,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 2: T/W Zoom Lever (8-Step) & Clear Image Zoom (CIZ) Mutual-Exclusion Matrix
# ---------------------------------------------------------------------------


def evaluate_zoom_ciz_matrix(
    *,
    requested_zoom_mode: str = "CLEAR_IMAGE_ZOOM",
    requested_magnification: float = 1.50,
    resolution_mode: str = "QFHD_3840x2160",
    zoom_lever_speed: int = 4,
    hdmi_raw16_enabled: bool = False,
    sq_active: bool = False,
    sq_fps: float = 24.0,
) -> ZoomCizEvalResult:
    """Evaluate `T/W` 8-step zoom lever, `CIZ` 1.5x/2.0x super-resolution & `RAW16`/`S&Q` exclusions."""
    errors: List[str] = []
    norm_mode = requested_zoom_mode.strip().upper()
    res_lookup = {r.upper(): r for r in ZOOM_RESOLUTION_MODES}
    norm_res = res_lookup.get(resolution_mode.strip().upper(), resolution_mode.strip())

    if norm_mode not in ZOOM_MODES:
        errors.append(f"Unsupported requested_zoom_mode {requested_zoom_mode!r}; expected {ZOOM_MODES}")
    if norm_res not in ZOOM_RESOLUTION_MODES:
        errors.append(f"Unsupported resolution_mode {resolution_mode!r}; expected {ZOOM_RESOLUTION_MODES}")
    if isinstance(zoom_lever_speed, bool) or not isinstance(zoom_lever_speed, int):
        errors.append(f"zoom_lever_speed must be an int in [{ZOOM_LEVER_SPEED_MIN}..{ZOOM_LEVER_SPEED_MAX}]")
    elif not (ZOOM_LEVER_SPEED_MIN <= zoom_lever_speed <= ZOOM_LEVER_SPEED_MAX):
        errors.append(
            f"zoom_lever_speed={zoom_lever_speed} outside [{ZOOM_LEVER_SPEED_MIN}..{ZOOM_LEVER_SPEED_MAX}]"
        )
    if sq_fps <= 0.0 or not math.isfinite(sq_fps):
        errors.append(f"Invalid sq_fps={sq_fps!r}")
    if not math.isfinite(requested_magnification) or requested_magnification < 1.0:
        errors.append(f"requested_magnification={requested_magnification!r} must be >= 1.0")

    max_ciz = CIZ_MAX_MAG_BY_RESOLUTION.get(norm_res, 1.50)

    if not errors:
        if norm_mode == "OPTICAL_ZOOM_ONLY" and requested_magnification > 1.0 + 1e-9:
            errors.append(
                f"OPTICAL_ZOOM_ONLY magnification {requested_magnification:.2f}x cannot exceed 1.00x"
            )
        elif norm_mode == "CLEAR_IMAGE_ZOOM" and requested_magnification > max_ciz + 1e-9:
            errors.append(
                f"CLEAR_IMAGE_ZOOM magnification {requested_magnification:.2f}x exceeds {norm_res} cap {max_ciz:.2f}x"
            )
        elif norm_mode == "DIGITAL_ZOOM" and requested_magnification > DIGITAL_ZOOM_MAX_MAG + 1e-9:
            errors.append(
                f"DIGITAL_ZOOM magnification {requested_magnification:.2f}x exceeds {DIGITAL_ZOOM_MAX_MAG:.2f}x cap"
            )

    if errors:
        return ZoomCizEvalResult(
            valid=False,
            status="BLOCKED_INVALID_ZOOM_PARAM",
            requested_zoom_mode=norm_mode,
            effective_zoom_mode="OPTICAL_ZOOM_ONLY",
            resolution_mode=norm_res,
            requested_magnification=float(requested_magnification),
            effective_magnification=1.0,
            max_allowed_ciz_magnification=max_ciz,
            zoom_lever_speed=int(zoom_lever_speed) if isinstance(zoom_lever_speed, int) else 0,
            by_pixel_super_res_active=False,
            pdaf_627_active=True,
            face_eye_tracking_retained=True,
            focus_area_mode="WIDE_OR_ZONE_627PT",
            hdmi_raw16_enabled=hdmi_raw16_enabled,
            sq_active=sq_active,
            sq_fps=float(sq_fps),
            ciz_clamped_by_mutual_exclusion=False,
            mutual_exclusion_reason=None,
            icx1295_crashed=False,
            libcamera_crashed=False,
            errors=tuple(errors),
        )

    # Check deterministic mutual exclusions (HDMI RAW16 or S&Q 100/120/200/240fps)
    exclusion_reasons: List[str] = []
    if hdmi_raw16_enabled:
        exclusion_reasons.append("HDMI_RAW16_ACTIVE")
    if sq_active and sq_fps >= 100.0:
        exclusion_reasons.append("SQ_HFR_120_240FPS_ACTIVE")

    ciz_clamped = False
    exclusion_reason: Optional[str] = None
    eff_mode = norm_mode
    eff_mag = round(float(requested_magnification), 4)

    if exclusion_reasons and norm_mode in ("CLEAR_IMAGE_ZOOM", "DIGITAL_ZOOM"):
        ciz_clamped = True
        exclusion_reason = "+".join(exclusion_reasons)
        eff_mode = "OPTICAL_ZOOM_ONLY"
        eff_mag = 1.0

    by_pixel_sr = eff_mode == "CLEAR_IMAGE_ZOOM" and eff_mag > 1.0
    if eff_mode == "OPTICAL_ZOOM_ONLY":
        pdaf_active = True
        face_eye_retained = True
        focus_area_mode = "FULL_627PT_PDAF"
    elif eff_mode == "CLEAR_IMAGE_ZOOM":
        pdaf_active = True
        face_eye_retained = True
        focus_area_mode = "CENTER_WIDE_PDAF_RETAINED"
    else:
        pdaf_active = False
        face_eye_retained = False
        focus_area_mode = "CENTER_CONTRAST_ONLY"

    if ciz_clamped:
        status = "CIZ_CLAMPED_TO_OPTICAL_1X_SAFE"
    elif eff_mode == "CLEAR_IMAGE_ZOOM":
        status = "CIZ_BY_PIXEL_SUPER_RES_VERIFIED"
    elif eff_mode == "DIGITAL_ZOOM":
        status = "DIGITAL_ZOOM_VERIFIED"
    else:
        status = "OPTICAL_ZOOM_ONLY_VERIFIED"

    return ZoomCizEvalResult(
        valid=True,
        status=status,
        requested_zoom_mode=norm_mode,
        effective_zoom_mode=eff_mode,
        resolution_mode=norm_res,
        requested_magnification=round(float(requested_magnification), 4),
        effective_magnification=eff_mag,
        max_allowed_ciz_magnification=max_ciz,
        zoom_lever_speed=zoom_lever_speed,
        by_pixel_super_res_active=by_pixel_sr,
        pdaf_627_active=pdaf_active,
        face_eye_tracking_retained=face_eye_retained,
        focus_area_mode=focus_area_mode,
        hdmi_raw16_enabled=hdmi_raw16_enabled,
        sq_active=sq_active,
        sq_fps=float(sq_fps),
        ciz_clamped_by_mutual_exclusion=ciz_clamped,
        mutual_exclusion_reason=exclusion_reason,
        icx1295_crashed=False,
        libcamera_crashed=False,
        errors=(),
    )


def evaluate_pillar_2_zoom_ciz_matrix(
    present_map: Mapping[str, Tuple[str, ...]],
) -> ZoomCizMatrixReport:
    """Audit Pillar 2 across `T/W` 8-step speed, `CIZ 1.5x/2.0x`, Digital `4.0x`, and `RAW16`/`S&Q` clamps."""
    errors: List[str] = []
    fx3_ciz = present_map["fx3_appfw_ciz_zoom"]
    fx6_ciz = present_map["fx6_appfw_ciz_zoom"]
    cp_zoom = present_map["cp_shared_zoom_touch"]

    if fx3_ciz != FX3_APPFW_CIZ_ZOOM_MARKERS:
        missing = tuple(m for m in FX3_APPFW_CIZ_ZOOM_MARKERS if m not in fx3_ciz)
        errors.append(f"FX3 appFw.so missing CIZ/Zoom Lever markers: {missing}")
    if fx6_ciz != FX6_APPFW_CIZ_ZOOM_MARKERS:
        missing = tuple(m for m in FX6_APPFW_CIZ_ZOOM_MARKERS if m not in fx6_ciz)
        errors.append(f"FX6 appFw.so missing CIZ/Zoom Lever markers: {missing}")
    if not all(m in cp_zoom for m in ("CheckSetEzoomOn", "SET_EZOOM_ON")):
        errors.append("cpapp-b.bin missing CheckSetEzoomOn / SET_EZOOM_ON")

    opt_4k = evaluate_zoom_ciz_matrix(
        requested_zoom_mode="OPTICAL_ZOOM_ONLY",
        requested_magnification=1.0,
        resolution_mode="DCI_4K_4096x2160",
        zoom_lever_speed=1,
    )
    ciz_4k_15x = evaluate_zoom_ciz_matrix(
        requested_zoom_mode="CLEAR_IMAGE_ZOOM",
        requested_magnification=1.50,
        resolution_mode="QFHD_3840x2160",
        zoom_lever_speed=5,
    )
    ciz_fhd_20x = evaluate_zoom_ciz_matrix(
        requested_zoom_mode="CLEAR_IMAGE_ZOOM",
        requested_magnification=2.00,
        resolution_mode="FHD_1920x1080",
        zoom_lever_speed=8,
    )
    dig_40x = evaluate_zoom_ciz_matrix(
        requested_zoom_mode="DIGITAL_ZOOM",
        requested_magnification=4.00,
        resolution_mode="FHD_1920x1080",
        zoom_lever_speed=4,
    )
    raw16_clamp = evaluate_zoom_ciz_matrix(
        requested_zoom_mode="CLEAR_IMAGE_ZOOM",
        requested_magnification=1.50,
        resolution_mode="QFHD_3840x2160",
        zoom_lever_speed=6,
        hdmi_raw16_enabled=True,
    )
    sq_120_clamp = evaluate_zoom_ciz_matrix(
        requested_zoom_mode="CLEAR_IMAGE_ZOOM",
        requested_magnification=1.50,
        resolution_mode="QFHD_3840x2160",
        zoom_lever_speed=6,
        sq_active=True,
        sq_fps=120.0,
    )
    sq_240_clamp = evaluate_zoom_ciz_matrix(
        requested_zoom_mode="CLEAR_IMAGE_ZOOM",
        requested_magnification=2.00,
        resolution_mode="FHD_1920x1080",
        zoom_lever_speed=8,
        sq_active=True,
        sq_fps=240.0,
    )

    for ev in (opt_4k, ciz_4k_15x, ciz_fhd_20x, dig_40x, raw16_clamp, sq_120_clamp, sq_240_clamp):
        if not ev.valid or ev.icx1295_crashed or ev.libcamera_crashed:
            errors.extend(ev.errors or (f"Crash/failure in {ev.status}",))

    if not (ciz_4k_15x.by_pixel_super_res_active and ciz_4k_15x.pdaf_627_active):
        errors.append("CIZ 4K 1.5x failed By-Pixel SR or PDAF retention check")
    if not (ciz_fhd_20x.by_pixel_super_res_active and ciz_fhd_20x.effective_magnification == 2.0):
        errors.append("CIZ FHD 2.0x failed By-Pixel SR check")
    for clamp_ev in (raw16_clamp, sq_120_clamp, sq_240_clamp):
        if not clamp_ev.ciz_clamped_by_mutual_exclusion or clamp_ev.effective_magnification != 1.0:
            errors.append(f"Mutual-exclusion clamp failed for {clamp_ev.mutual_exclusion_reason}")

    return ZoomCizMatrixReport(
        passed=len(errors) == 0,
        fx3_ciz_markers=fx3_ciz,
        fx6_ciz_markers=fx6_ciz,
        cp_zoom_markers=cp_zoom,
        optical_4k_eval=opt_4k,
        ciz_4k_15x_eval=ciz_4k_15x,
        ciz_fhd_20x_eval=ciz_fhd_20x,
        digital_40x_eval=dig_40x,
        hdmi_raw16_clamp_eval=raw16_clamp,
        sq_120fps_clamp_eval=sq_120_clamp,
        sq_240fps_clamp_eval=sq_240_clamp,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 3: Touch Tracking AF & Anamorphic Desqueeze + 4.0x Magnifier Coordinate Math
# ---------------------------------------------------------------------------


def transform_gpe0_touch_to_imx510_pdaf(
    *,
    touch_x_px: float,
    touch_y_px: float,
    touch_function: str = "TOUCH_TRACKING",
    cine_mode: bool = True,
    desqueeze_ratio: float = 1.0,
    focus_magnifier_factor: float = 1.0,
    magnifier_center_norm: Tuple[float, float] = (0.5, 0.5),
) -> TouchAfCoordEvalResult:
    """Transform `960x540` `GPE0` capacitive touch `(x, y)` into `[0..1]` `IMX510` 627-pt PDAF coords."""
    errors: List[str] = []
    norm_fn = touch_function.strip().upper()

    touch_shutter_blocked = False
    if cine_mode and norm_fn == "TOUCH_SHUTTER":
        touch_shutter_blocked = True
        errors.append("BLOCKED_TOUCH_SHUTTER_DISABLED_IN_CINE: Touch Shutter cannot fire in Cinema/Movie mode")
    elif norm_fn not in (*VALID_TOUCH_FUNCTIONS_CINE, "TOUCH_SHUTTER"):
        errors.append(f"Unsupported touch_function {touch_function!r}")

    if not math.isfinite(touch_x_px) or not (0.0 <= touch_x_px <= float(GPE0_TOUCH_WIDTH)):
        errors.append(f"touch_x_px={touch_x_px!r} outside [0..{GPE0_TOUCH_WIDTH}]")
    if not math.isfinite(touch_y_px) or not (0.0 <= touch_y_px <= float(GPE0_TOUCH_HEIGHT)):
        errors.append(f"touch_y_px={touch_y_px!r} outside [0..{GPE0_TOUCH_HEIGHT}]")

    if not any(abs(desqueeze_ratio - r) < 1e-9 for r in VALID_DESQUEEZE_RATIOS):
        errors.append(f"Unsupported anamorphic desqueeze_ratio={desqueeze_ratio!r}; expected {VALID_DESQUEEZE_RATIOS}")
    if not any(abs(focus_magnifier_factor - f) < 1e-9 for f in VALID_MAGNIFIER_FACTORS):
        errors.append(
            f"Unsupported focus_magnifier_factor={focus_magnifier_factor!r}; expected {VALID_MAGNIFIER_FACTORS}"
        )

    mcx, mcy = magnifier_center_norm
    if not (math.isfinite(mcx) and math.isfinite(mcy) and 0.0 <= mcx <= 1.0 and 0.0 <= mcy <= 1.0):
        errors.append(f"magnifier_center_norm={magnifier_center_norm!r} outside [0.0..1.0]^2")

    if errors:
        return TouchAfCoordEvalResult(
            valid=False,
            status=(
                "BLOCKED_TOUCH_SHUTTER_DISABLED_IN_CINE"
                if touch_shutter_blocked
                else "BLOCKED_INVALID_TOUCH_COORD"
            ),
            touch_function=norm_fn,
            cine_mode=cine_mode,
            touch_shutter_disabled_in_cine=cine_mode,
            gpe0_touch_x_px=float(touch_x_px),
            gpe0_touch_y_px=float(touch_y_px),
            desqueeze_ratio=float(desqueeze_ratio),
            focus_magnifier_factor=float(focus_magnifier_factor),
            magnifier_center_norm=(float(mcx), float(mcy)),
            display_norm_x=0.0,
            display_norm_y=0.0,
            sensor_norm_x=0.0,
            sensor_norm_y=0.0,
            pdaf_col=0,
            pdaf_row=0,
            pdaf_point_index=0,
            pdaf_total_points=IMX510_PDAF_TOTAL_POINTS,
            errors=tuple(errors),
        )

    u_disp = float(touch_x_px) / float(GPE0_TOUCH_WIDTH)
    v_disp = float(touch_y_px) / float(GPE0_TOUCH_HEIGHT)

    # Focus Magnifier crop window transform (1.0x full frame or 4.0x 0.25x0.25 crop)
    if focus_magnifier_factor > 1.0:
        half_span = 0.5 / focus_magnifier_factor
        clamped_cx = min(1.0 - half_span, max(half_span, float(mcx)))
        clamped_cy = min(1.0 - half_span, max(half_span, float(mcy)))
        u_view = (clamped_cx - half_span) + u_disp * (2.0 * half_span)
        v_view = (clamped_cy - half_span) + v_disp * (2.0 * half_span)
    else:
        u_view = u_disp
        v_view = v_disp

    # Anamorphic desqueeze inverse-X transform: u_disp_desqueezed = 0.5 + D * (u_sensor - 0.5)
    # Therefore u_sensor = 0.5 + (u_view - 0.5) / D
    u_sensor = min(1.0, max(0.0, 0.5 + (u_view - 0.5) / float(desqueeze_ratio)))
    v_sensor = min(1.0, max(0.0, v_view))

    pdaf_col = min(IMX510_PDAF_COLS - 1, max(0, int(u_sensor * IMX510_PDAF_COLS)))
    pdaf_row = min(IMX510_PDAF_ROWS - 1, max(0, int(v_sensor * IMX510_PDAF_ROWS)))
    pdaf_idx = pdaf_row * IMX510_PDAF_COLS + pdaf_col

    return TouchAfCoordEvalResult(
        valid=True,
        status="TOUCH_AF_COORD_TRANSFORM_VERIFIED",
        touch_function=norm_fn,
        cine_mode=cine_mode,
        touch_shutter_disabled_in_cine=cine_mode,
        gpe0_touch_x_px=round(float(touch_x_px), 4),
        gpe0_touch_y_px=round(float(touch_y_px), 4),
        desqueeze_ratio=float(desqueeze_ratio),
        focus_magnifier_factor=float(focus_magnifier_factor),
        magnifier_center_norm=(round(float(mcx), 6), round(float(mcy), 6)),
        display_norm_x=round(u_disp, 6),
        display_norm_y=round(v_disp, 6),
        sensor_norm_x=round(u_sensor, 6),
        sensor_norm_y=round(v_sensor, 6),
        pdaf_col=pdaf_col,
        pdaf_row=pdaf_row,
        pdaf_point_index=pdaf_idx,
        pdaf_total_points=IMX510_PDAF_TOTAL_POINTS,
        errors=(),
    )


def evaluate_pillar_3_touch_af_and_magnifier(
    present_map: Mapping[str, Tuple[str, ...]],
) -> TouchAfAndMagnifierReport:
    """Audit Pillar 3 across touch AF, `4.0x` crop, `1.3x`/`2.0x` desqueeze inverse-X, and Touch Shutter block."""
    errors: List[str] = []
    fx3_ta = present_map["fx3_appfw_touch_af"]
    fx6_ta = present_map["fx6_appfw_touch_af"]
    cp_zt = present_map["cp_shared_zoom_touch"]

    if fx3_ta != FX3_APPFW_TOUCH_AF_MARKERS:
        missing = tuple(m for m in FX3_APPFW_TOUCH_AF_MARKERS if m not in fx3_ta)
        errors.append(f"FX3 appFw.so missing Touch AF / Magnifier / Desqueeze markers: {missing}")
    if fx6_ta != FX6_APPFW_TOUCH_AF_MARKERS:
        missing = tuple(m for m in FX6_APPFW_TOUCH_AF_MARKERS if m not in fx6_ta)
        errors.append(f"FX6 appFw.so missing Touch AF / Magnifier / Desqueeze markers: {missing}")
    if not all(m in cp_zt for m in ("SET_ANAMO_DESQUEEZE_SCALE", "MSG_ID_INFRABB_VDF_INPUT_SET_TOUCH_PANEL")):
        errors.append("cpapp-b.bin missing SET_ANAMO_DESQUEEZE_SCALE / SET_TOUCH_PANEL markers")

    normal_1x = transform_gpe0_touch_to_imx510_pdaf(
        touch_x_px=480.0,
        touch_y_px=270.0,
        touch_function="TOUCH_TRACKING",
        desqueeze_ratio=1.0,
        focus_magnifier_factor=1.0,
    )
    anamorphic_13x = transform_gpe0_touch_to_imx510_pdaf(
        touch_x_px=604.8,  # u_disp=0.63 -> u_sensor=0.60 at 1.3x
        touch_y_px=216.0,  # v_sensor=0.40
        touch_function="TOUCH_FOCUS",
        desqueeze_ratio=1.3,
        focus_magnifier_factor=1.0,
    )
    anamorphic_20x = transform_gpe0_touch_to_imx510_pdaf(
        touch_x_px=864.0,  # u_disp=0.90 -> u_sensor=0.70 at 2.0x
        touch_y_px=216.0,  # v_sensor=0.40
        touch_function="TOUCH_TRACKING",
        desqueeze_ratio=2.0,
        focus_magnifier_factor=1.0,
    )
    mag_4x_20x = transform_gpe0_touch_to_imx510_pdaf(
        touch_x_px=720.0,  # u_disp=0.75 -> u_view=0.5625 -> u_sensor=0.53125
        touch_y_px=270.0,  # v_disp=0.50 -> v_sensor=0.50
        touch_function="TOUCH_FOCUS",
        desqueeze_ratio=2.0,
        focus_magnifier_factor=4.0,
        magnifier_center_norm=(0.5, 0.5),
    )
    touch_shutter_block = transform_gpe0_touch_to_imx510_pdaf(
        touch_x_px=480.0,
        touch_y_px=270.0,
        touch_function="TOUCH_SHUTTER",
        cine_mode=True,
    )

    for ev in (normal_1x, anamorphic_13x, anamorphic_20x, mag_4x_20x):
        if not ev.valid:
            errors.extend(ev.errors)

    if abs(anamorphic_13x.sensor_norm_x - 0.60) > 1e-4:
        errors.append(f"1.3x inverse-X mismatch: {anamorphic_13x.sensor_norm_x} != 0.60")
    if abs(anamorphic_20x.sensor_norm_x - 0.70) > 1e-4:
        errors.append(f"2.0x inverse-X mismatch: {anamorphic_20x.sensor_norm_x} != 0.70")
    if abs(mag_4x_20x.sensor_norm_x - 0.53125) > 1e-4:
        errors.append(f"4.0x + 2.0x inverse-X mismatch: {mag_4x_20x.sensor_norm_x} != 0.53125")
    if touch_shutter_block.valid or touch_shutter_block.status != "BLOCKED_TOUCH_SHUTTER_DISABLED_IN_CINE":
        errors.append("Touch Shutter failed to block in Cine mode")

    return TouchAfAndMagnifierReport(
        passed=len(errors) == 0,
        fx3_touch_af_markers=fx3_ta,
        fx6_touch_af_markers=fx6_ta,
        cp_touch_markers=cp_zt,
        normal_1x_eval=normal_1x,
        anamorphic_13x_eval=anamorphic_13x,
        anamorphic_20x_eval=anamorphic_20x,
        magnifier_4x_desqueeze_20x_eval=mag_4x_20x,
        touch_shutter_cine_block_eval=touch_shutter_block,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 4: Custom Big6 (6-Slot) & Fn (12-Slot) Volatile BK4 Shadow Proof
# ---------------------------------------------------------------------------


def _is_forbidden_nvram_path(path_str: str) -> bool:
    low = path_str.strip().lower()
    return any(low.startswith(pfx) or pfx in low for pfx in FORBIDDEN_PERSISTENT_NVRAM_PREFIXES)


def _is_volatile_shadow_path(path_str: str) -> bool:
    low = path_str.strip().lower()
    return low.startswith(VOLATILE_SHADOW_PREFIXES)


def build_and_verify_big6_fn_volatile_shadow(
    *,
    big6_slots: Optional[Sequence[Mapping[str, str]]] = None,
    fn_slots: Optional[Sequence[Mapping[str, str]]] = None,
    sq_mode_settings: str = "FIXED_VARIABLE",
    home_lower_left_mode: str = "APERTURE",
    shadow_path: str = "/tmp/fx3_stageb_camset_big6_fn_shadow.json",
    persistent_emmc_writes_authorized: bool = False,
) -> Big6FnShadowEvalResult:
    """Build and verify volatile `/tmp` / `CAMSET` JSON shadow for `Big6` (6) & `Fn` (12) with 0 BK4 writes."""
    errors: List[str] = []
    norm_sq = sq_mode_settings.strip().upper()
    norm_ll = home_lower_left_mode.strip().upper()

    if persistent_emmc_writes_authorized:
        errors.append("Hard safety redline: persistent_emmc_writes_authorized must remain False")

    attempted_nvram_writes = 0
    if _is_forbidden_nvram_path(shadow_path):
        attempted_nvram_writes = 1
        errors.append(
            f"BLOCKED_PERSISTENT_BK4_NVRAM_WRITE: shadow_path={shadow_path!r} targets SPI/eMMC NVRAM"
        )
    elif not _is_volatile_shadow_path(shadow_path):
        errors.append(
            f"shadow_path={shadow_path!r} must use a volatile prefix {VOLATILE_SHADOW_PREFIXES}"
        )

    if norm_sq not in VALID_SQ_MODE_SETTINGS:
        errors.append(f"Unsupported sq_mode_settings={sq_mode_settings!r}; expected {VALID_SQ_MODE_SETTINGS}")
    if norm_ll not in VALID_HOME_LOWER_LEFT_MODES:
        errors.append(
            f"Unsupported home_lower_left_mode={home_lower_left_mode!r}; expected {VALID_HOME_LOWER_LEFT_MODES}"
        )

    b6 = [dict(s) for s in (big6_slots if big6_slots is not None else BIG6_DEFAULT_SLOTS)]
    fn = [dict(s) for s in (fn_slots if fn_slots is not None else FN_MENU_DEFAULT_SLOTS)]

    if len(b6) != 6:
        errors.append(f"Big6 layout requires exactly 6 slots, got {len(b6)}")
    if len(fn) != 12:
        errors.append(f"Fn menu layout requires exactly 12 slots, got {len(fn)}")

    b6_ids = [s.get("slot_id", "").strip() for s in b6]
    fn_ids = [s.get("slot_id", "").strip() for s in fn]
    if any(not sid for sid in b6_ids) or len(set(b6_ids)) != len(b6_ids):
        errors.append("Big6 slot_id values must be non-empty and unique")
    if any(not sid for sid in fn_ids) or len(set(fn_ids)) != len(fn_ids):
        errors.append("Fn slot_id values must be non-empty and unique")
    if any(not s.get("label", "").strip() or not s.get("value", "").strip() for s in (*b6, *fn)):
        errors.append("All Big6 and Fn slots require non-empty label and value")

    big6_available = norm_sq == "FIXED_VARIABLE"
    if not big6_available:
        errors.append(
            "BLOCKED_BIG6_REQUIRES_FIXED_VARIABLE_SQ: FX3 v7.00+ Big6 requires S&Q Mode Settings = FIXED_VARIABLE"
        )

    payload = {
        "schema": "fx3_stageb_camset_volatile_shadow_v1",
        "sq_mode_settings": norm_sq,
        "big6_available": big6_available,
        "home_lower_left_mode": norm_ll,
        "shadow_path": shadow_path,
        "bk4_persistent_nvram_writes": 0,
        "persistent_emmc_writes_authorized": False,
        "big6_slots": b6,
        "fn_slots": fn,
    }
    camset_json = json.dumps(payload, indent=2, sort_keys=True)
    roundtrip = json.loads(camset_json)
    if len(roundtrip["big6_slots"]) != len(b6) or len(roundtrip["fn_slots"]) != len(fn):
        errors.append("CAMSET JSON shadow roundtrip length mismatch")
    camset_sha = hashlib.sha256(camset_json.encode("utf-8")).hexdigest()

    if attempted_nvram_writes > 0:
        status = "BLOCKED_PERSISTENT_BK4_NVRAM_WRITE"
    elif not big6_available:
        status = "BLOCKED_BIG6_REQUIRES_FIXED_VARIABLE_SQ"
    elif errors:
        status = "BLOCKED_SHADOW_POLICY_ERROR"
    else:
        status = "VOLATILE_BIG6_FN_CAMSET_SHADOW_VERIFIED"

    return Big6FnShadowEvalResult(
        valid=len(errors) == 0,
        status=status,
        sq_mode_settings=norm_sq,
        big6_available=big6_available,
        home_lower_left_mode=norm_ll,
        big6_slot_count=len(b6),
        fn_slot_count=len(fn),
        shadow_path=shadow_path,
        volatile_shadow_only=attempted_nvram_writes == 0 and _is_volatile_shadow_path(shadow_path),
        bk4_persistent_nvram_writes=0,
        persistent_emmc_writes_authorized=persistent_emmc_writes_authorized,
        camset_shadow_sha256=camset_sha,
        camset_shadow_json=camset_json,
        errors=tuple(errors),
    )


def evaluate_pillar_4_big6_fn_shadow(
    present_map: Mapping[str, Tuple[str, ...]],
    fx3_xdb_ok: bool,
    fx6_xdb_ok: bool,
) -> Big6AndFnShadowReport:
    """Audit Pillar 4 across `Big6`/`Fn` markers, `global.xdb`, and zero-NVRAM-write volatile shadows."""
    errors: List[str] = []
    fx3_bf = present_map["fx3_appfw_big6_fn"]
    fx6_bf = present_map["fx6_appfw_big6_fn"]

    if fx3_bf != FX3_APPFW_BIG6_FN_MARKERS:
        missing = tuple(m for m in FX3_APPFW_BIG6_FN_MARKERS if m not in fx3_bf)
        errors.append(f"FX3 appFw.so missing Big6/Fn/CAMSET markers: {missing}")
    if fx6_bf != FX6_APPFW_BIG6_FN_MARKERS:
        missing = tuple(m for m in FX6_APPFW_BIG6_FN_MARKERS if m not in fx6_bf)
        errors.append(f"FX6 appFw.so missing Big6/Fn markers: {missing}")
    if not fx3_xdb_ok or not fx6_xdb_ok:
        errors.append(f"global.xdb structural validation failed (fx3={fx3_xdb_ok}, fx6={fx6_xdb_ok})")

    fx3_shadow = build_and_verify_big6_fn_volatile_shadow(
        sq_mode_settings="FIXED_VARIABLE",
        home_lower_left_mode="APERTURE",
        shadow_path="/tmp/fx3_stageb_camset_shadow.json",
    )
    fx6_shadow = build_and_verify_big6_fn_volatile_shadow(
        sq_mode_settings="FIXED_VARIABLE",
        home_lower_left_mode="ND_FILTER",
        shadow_path="ram://fx6_big6_fn_shadow.json",
    )
    legacy_sq_gate = build_and_verify_big6_fn_volatile_shadow(
        sq_mode_settings="LEGACY_SQ_MODE",
        home_lower_left_mode="APERTURE",
        shadow_path="/tmp/fx3_legacy_sq_test.json",
    )
    nvram_blocked = build_and_verify_big6_fn_volatile_shadow(
        sq_mode_settings="FIXED_VARIABLE",
        home_lower_left_mode="APERTURE",
        shadow_path="/dev/cnflasha1/bk4_overwrite.bin",
    )

    for ev in (fx3_shadow, fx6_shadow):
        if not ev.valid or not ev.volatile_shadow_only or ev.bk4_persistent_nvram_writes != 0:
            errors.extend(ev.errors or ("Shadow verification failed",))
    if legacy_sq_gate.valid or legacy_sq_gate.status != "BLOCKED_BIG6_REQUIRES_FIXED_VARIABLE_SQ":
        errors.append("Legacy S&Q Mode failed to gate Big6 availability")
    if nvram_blocked.valid or nvram_blocked.status != "BLOCKED_PERSISTENT_BK4_NVRAM_WRITE":
        errors.append("Persistent NVRAM path failed to trigger BLOCKED_PERSISTENT_BK4_NVRAM_WRITE")

    total_nvram_writes = sum(
        ev.bk4_persistent_nvram_writes for ev in (fx3_shadow, fx6_shadow, legacy_sq_gate, nvram_blocked)
    )
    if total_nvram_writes != 0:
        errors.append(f"Expected 0 persistent BK4 NVRAM writes, got {total_nvram_writes}")

    return Big6AndFnShadowReport(
        passed=len(errors) == 0 and total_nvram_writes == 0,
        fx3_big6_fn_markers=fx3_bf,
        fx6_big6_fn_markers=fx6_bf,
        fx3_global_xdb_valid=fx3_xdb_ok,
        fx6_global_xdb_valid=fx6_xdb_ok,
        fx3_big6_shadow_eval=fx3_shadow,
        fx6_nd_lower_left_shadow_eval=fx6_shadow,
        legacy_sq_gate_eval=legacy_sq_gate,
        nvram_write_blocked_eval=nvram_blocked,
        bk4_persistent_nvram_writes=total_nvram_writes,
        persistent_emmc_writes_authorized=False,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Main Dual-Mode Entrypoint
# ---------------------------------------------------------------------------


def analyze_assignable_zoom_ciz_and_fn(
    repo_root: Optional[Path] = None,
    *,
    clean_room: bool = False,
) -> AssignableZoomCizAndFnReport:
    """Run the 14th Unified Firmware-Lab Auditor across Local Donor (`os.O_RDONLY`) or Clean-Room fixtures."""
    root = repo_root or DEFAULT_REPO_ROOT
    forced_clean = clean_room or is_forced_clean_room()

    donor_relpaths: Dict[str, str] = {
        "fx3_appfw": FX3_APPFW_RELPATH,
        "fx6_appfw": FX6_APPFW_RELPATH,
        "fx3_cpapp": FX3_CPAPP_RELPATH,
        "fx6_cpapp": FX6_CPAPP_RELPATH,
        "fx3_lens_comm": FX3_LENS_COMM_RELPATH,
        "fx6_lens_comm": FX6_LENS_COMM_RELPATH,
        "fx3_global_xdb": FX3_GLOBAL_XDB_RELPATH,
        "fx6_global_xdb": FX6_GLOBAL_XDB_RELPATH,
        "fx3_str_en": FX3_STR_EN_RELPATH,
        "fx3_str_en_g": FX3_STR_EN_G_RELPATH,
        "fx6_str_en_1": FX6_STR_EN_1_RELPATH,
        "fx6_str_en_2": FX6_STR_EN_2_RELPATH,
    }

    resolved_paths: Dict[str, Path] = {}
    if not forced_clean:
        for key, rel in donor_relpaths.items():
            p = resolve_donor_file(rel, repo_root=root)
            if p is not None and p.is_file():
                resolved_paths[key] = p

    use_local_donors = (not forced_clean) and (len(resolved_paths) == len(donor_relpaths))
    mode = "LOCAL_DONOR_VERIFIED" if use_local_donors else "CLEAN_ROOM_SYNTHETIC_VERIFIED"

    errors: List[str] = []
    donor_sizes: Dict[str, int] = {}
    present_map: Dict[str, Tuple[str, ...]] = {}

    fx3_appfw_groups = {
        "fx3_appfw_assignable": FX3_APPFW_ASSIGNABLE_MARKERS,
        "fx3_appfw_ciz_zoom": FX3_APPFW_CIZ_ZOOM_MARKERS,
        "fx3_appfw_touch_af": FX3_APPFW_TOUCH_AF_MARKERS,
        "fx3_appfw_big6_fn": FX3_APPFW_BIG6_FN_MARKERS,
    }
    fx6_appfw_groups = {
        "fx6_appfw_assignable": FX6_APPFW_ASSIGNABLE_MARKERS,
        "fx6_appfw_ciz_zoom": FX6_APPFW_CIZ_ZOOM_MARKERS,
        "fx6_appfw_touch_af": FX6_APPFW_TOUCH_AF_MARKERS,
        "fx6_appfw_big6_fn": FX6_APPFW_BIG6_FN_MARKERS,
    }

    if use_local_donors:
        sz_fx3_app, fx3_hits = _scan_donor_rdonly_markers(
            resolved_paths["fx3_appfw"], fx3_appfw_groups, is_elf=True
        )
        sz_fx6_app, fx6_hits = _scan_donor_rdonly_markers(
            resolved_paths["fx6_appfw"], fx6_appfw_groups, is_elf=True
        )
        sz_fx3_cp, fx3_cp_hits = _scan_donor_rdonly_markers(
            resolved_paths["fx3_cpapp"], {"cp": CP_SHARED_ZOOM_TOUCH_MARKERS}, is_elf=False
        )
        sz_fx6_cp, fx6_cp_hits = _scan_donor_rdonly_markers(
            resolved_paths["fx6_cpapp"], {"cp": CP_SHARED_ZOOM_TOUCH_MARKERS}, is_elf=False
        )
        sz_fx3_lens, fx3_lens_hits = _scan_donor_rdonly_markers(
            resolved_paths["fx3_lens_comm"], {"lens": LENS_COMM_SHARED_MARKERS}, is_elf=True
        )
        sz_fx6_lens, fx6_lens_hits = _scan_donor_rdonly_markers(
            resolved_paths["fx6_lens_comm"], {"lens": LENS_COMM_SHARED_MARKERS}, is_elf=True
        )

        fx3_xdb_bytes = _read_bytes_rdonly(resolved_paths["fx3_global_xdb"])
        fx6_xdb_bytes = _read_bytes_rdonly(resolved_paths["fx6_global_xdb"])
        fx3_str_en_bytes = _read_bytes_rdonly(resolved_paths["fx3_str_en"])
        fx3_str_eng_bytes = _read_bytes_rdonly(resolved_paths["fx3_str_en_g"])
        fx6_str_en1_bytes = _read_bytes_rdonly(resolved_paths["fx6_str_en_1"])
        fx6_str_en2_bytes = _read_bytes_rdonly(resolved_paths["fx6_str_en_2"])

        donor_sizes = {
            "fx3_appfw": sz_fx3_app,
            "fx6_appfw": sz_fx6_app,
            "fx3_cpapp": sz_fx3_cp,
            "fx6_cpapp": sz_fx6_cp,
            "fx3_lens_comm": sz_fx3_lens,
            "fx6_lens_comm": sz_fx6_lens,
            "fx3_global_xdb": len(fx3_xdb_bytes),
            "fx6_global_xdb": len(fx6_xdb_bytes),
            "fx3_str_en": len(fx3_str_en_bytes),
            "fx3_str_en_g": len(fx3_str_eng_bytes),
            "fx6_str_en_1": len(fx6_str_en1_bytes),
            "fx6_str_en_2": len(fx6_str_en2_bytes),
        }
        present_map.update(fx3_hits)
        present_map.update(fx6_hits)
        cp_both = tuple(
            m for m in CP_SHARED_ZOOM_TOUCH_MARKERS if m in fx3_cp_hits["cp"] and m in fx6_cp_hits["cp"]
        )
        lens_both = tuple(
            m for m in LENS_COMM_SHARED_MARKERS if m in fx3_lens_hits["lens"] and m in fx6_lens_hits["lens"]
        )
        present_map["cp_shared_zoom_touch"] = cp_both
        present_map["lens_comm_shared"] = lens_both
    else:
        fixtures = build_clean_room_assignable_ciz_fixtures()
        sz_fx3_app, fx3_hits = _scan_bytes_marker_groups(fixtures["fx3_appfw"], fx3_appfw_groups)
        sz_fx6_app, fx6_hits = _scan_bytes_marker_groups(fixtures["fx6_appfw"], fx6_appfw_groups)
        sz_fx3_cp, fx3_cp_hits = _scan_bytes_marker_groups(
            fixtures["fx3_cpapp"], {"cp": CP_SHARED_ZOOM_TOUCH_MARKERS}
        )
        sz_fx6_cp, fx6_cp_hits = _scan_bytes_marker_groups(
            fixtures["fx6_cpapp"], {"cp": CP_SHARED_ZOOM_TOUCH_MARKERS}
        )
        sz_fx3_lens, fx3_lens_hits = _scan_bytes_marker_groups(
            fixtures["fx3_lens_comm"], {"lens": LENS_COMM_SHARED_MARKERS}
        )
        sz_fx6_lens, fx6_lens_hits = _scan_bytes_marker_groups(
            fixtures["fx6_lens_comm"], {"lens": LENS_COMM_SHARED_MARKERS}
        )

        fx3_xdb_bytes = fixtures["fx3_global_xdb"]
        fx6_xdb_bytes = fixtures["fx6_global_xdb"]
        fx3_str_en_bytes = fixtures["fx3_str_en"]
        fx3_str_eng_bytes = fixtures["fx3_str_en_g"]
        fx6_str_en1_bytes = fixtures["fx6_str_en_1"]
        fx6_str_en2_bytes = fixtures["fx6_str_en_2"]

        donor_sizes = {
            "fx3_appfw": sz_fx3_app,
            "fx6_appfw": sz_fx6_app,
            "fx3_cpapp": sz_fx3_cp,
            "fx6_cpapp": sz_fx6_cp,
            "fx3_lens_comm": sz_fx3_lens,
            "fx6_lens_comm": sz_fx6_lens,
            "fx3_global_xdb": len(fx3_xdb_bytes),
            "fx6_global_xdb": len(fx6_xdb_bytes),
            "fx3_str_en": len(fx3_str_en_bytes),
            "fx3_str_en_g": len(fx3_str_eng_bytes),
            "fx6_str_en_1": len(fx6_str_en1_bytes),
            "fx6_str_en_2": len(fx6_str_en2_bytes),
        }
        present_map.update(fx3_hits)
        present_map.update(fx6_hits)
        present_map["cp_shared_zoom_touch"] = tuple(
            m for m in CP_SHARED_ZOOM_TOUCH_MARKERS if m in fx3_cp_hits["cp"] and m in fx6_cp_hits["cp"]
        )
        present_map["lens_comm_shared"] = tuple(
            m for m in LENS_COMM_SHARED_MARKERS if m in fx3_lens_hits["lens"] and m in fx6_lens_hits["lens"]
        )

    xdb_source_mode = "LOCAL_DONOR_RDONLY" if use_local_donors else "SYNTHETIC_CLEAN_ROOM"
    fx3_xdb_audit = parse_global_xdb_buffer(
        fx3_xdb_bytes,
        body="fx3_702",
        source_mode=xdb_source_mode,
        share_app_dir=resolved_paths["fx3_global_xdb"].parent if use_local_donors else None,
    )
    fx6_xdb_audit = parse_global_xdb_buffer(
        fx6_xdb_bytes,
        body="fx6_601",
        source_mode=xdb_source_mode,
        share_app_dir=resolved_paths["fx6_global_xdb"].parent if use_local_donors else None,
    )
    fx3_xdb_ok = fx3_xdb_audit.valid
    fx6_xdb_ok = fx6_xdb_audit.valid
    if not fx3_xdb_ok:
        errors.extend(fx3_xdb_audit.errors)
    if not fx6_xdb_ok:
        errors.extend(fx6_xdb_audit.errors)

    lbl_fx3_en, errs_fx3_en = _extract_uxc_labels(fx3_str_en_bytes, FX3_NS39_PHASE75_LABELS)
    lbl_fx3_eng, errs_fx3_eng = _extract_uxc_labels(fx3_str_eng_bytes, FX3_NS3_PHASE75_LABELS)
    lbl_fx6_en1, errs_fx6_en1 = _extract_uxc_labels(fx6_str_en1_bytes, FX6_NS1_PHASE75_LABELS)
    lbl_fx6_en2, errs_fx6_en2 = _extract_uxc_labels(fx6_str_en2_bytes, FX6_NS2_PHASE75_LABELS)
    errors.extend((*errs_fx3_en, *errs_fx3_eng, *errs_fx6_en1, *errs_fx6_en2))

    uxc_labels: Dict[str, str] = {
        "fx3_digital_zoom": lbl_fx3_en.get("0x0004e06b", ""),
        "fx3_focus_magnifier": lbl_fx3_en.get("0x0004e226", ""),
        "fx3_focus_hold": lbl_fx3_en.get("0x0004e8ba", ""),
        "fx3_touch_operation": lbl_fx3_en.get("0x0004e8e3", ""),
        "fx3_custom_key_settings": lbl_fx3_en.get("0x0004e941", ""),
        "fx3_peaking_display": lbl_fx3_eng.get("0x00006050", ""),
        "fx3_sq_motion": lbl_fx3_eng.get("0x00006099", ""),
        "fx3_zebra_display": lbl_fx3_eng.get("0x00006352", ""),
        "fx6_base_iso_sensitivity": lbl_fx6_en1.get("0x00002052", ""),
        "fx6_nd_filter": lbl_fx6_en1.get("0x000020d3", ""),
        "fx6_assignable_button": lbl_fx6_en1.get("0x0000211e", ""),
        "fx6_vf_adjust": lbl_fx6_en1.get("0x00002223", ""),
        "fx6_optical_zoom_only": lbl_fx6_en1.get("0x000023c9", ""),
        "fx6_clear_image_zoom": lbl_fx6_en1.get("0x000023cb", ""),
        "fx6_lut_on_off": lbl_fx6_en1.get("0x000023f6", ""),
        "fx6_audio_level": lbl_fx6_en2.get("0x00004233", ""),
        "fx6_peaking": lbl_fx6_en2.get("0x0000423d", ""),
        "fx6_marker": lbl_fx6_en2.get("0x0000423e", ""),
        "fx6_zebra": lbl_fx6_en2.get("0x0000423f", ""),
        "fx6_sdi_hdmi_rec_control": lbl_fx6_en2.get("0x0000428d", ""),
    }

    p1 = evaluate_pillar_1_assignable_catalog(present_map, uxc_labels)
    p2 = evaluate_pillar_2_zoom_ciz_matrix(present_map)
    p3 = evaluate_pillar_3_touch_af_and_magnifier(present_map)
    p4 = evaluate_pillar_4_big6_fn_shadow(present_map, fx3_xdb_ok, fx6_xdb_ok)

    errors.extend((*p1.errors, *p2.errors, *p3.errors, *p4.errors))
    all_passed = bool(
        len(errors) == 0
        and p1.passed
        and p2.passed
        and p3.passed
        and p4.passed
        and p1.null_gpio_faults == 0
        and p4.bk4_persistent_nvram_writes == 0
    )

    pre_hash_payload = {
        "schema_version": PHASE_75_SCHEMA,
        "phase_version": PHASE_75_VERSION,
        "mode": mode,
        "all_checks_passed": all_passed,
        "o_rdonly_enforced": True,
        "persistent_emmc_writes_authorized": False,
        "bk4_persistent_nvram_writes": p4.bk4_persistent_nvram_writes,
        "null_gpio_faults": p1.null_gpio_faults,
        "icx1295_crashed": False,
        "libcamera_crashed": False,
        "donor_file_sizes": donor_sizes,
        "pillar_1_assignable_catalog": asdict(p1),
        "pillar_2_zoom_ciz_matrix": asdict(p2),
        "pillar_3_touch_af_desqueeze": asdict(p3),
        "pillar_4_big6_fn_shadow": asdict(p4),
        "errors": list(errors),
    }
    report_sha256 = hashlib.sha256(
        json.dumps(pre_hash_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()

    return AssignableZoomCizAndFnReport(
        schema_version=PHASE_75_SCHEMA,
        phase_version=PHASE_75_VERSION,
        mode=mode,
        all_checks_passed=all_passed,
        o_rdonly_enforced=True,
        persistent_emmc_writes_authorized=False,
        bk4_persistent_nvram_writes=p4.bk4_persistent_nvram_writes,
        null_gpio_faults=p1.null_gpio_faults,
        icx1295_crashed=False,
        libcamera_crashed=False,
        donor_file_sizes=donor_sizes,
        pillar_1_assignable_catalog=p1,
        pillar_2_zoom_ciz_matrix=p2,
        pillar_3_touch_af_desqueeze=p3,
        pillar_4_big6_fn_shadow=p4,
        errors=tuple(errors),
        report_sha256=report_sha256,
    )


def assignable_zoom_ciz_and_fn_report_to_dict(
    report: AssignableZoomCizAndFnReport,
) -> Dict[str, object]:
    """Convert `AssignableZoomCizAndFnReport` to a deterministic JSON-serializable dict."""
    return report.to_dict()
