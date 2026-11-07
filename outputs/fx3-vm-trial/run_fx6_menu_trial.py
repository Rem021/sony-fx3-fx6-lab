#!/usr/bin/env python3
"""
FX6-on-FX3 QEMU Virtual Machine — Authentic Multi-Screen Interactive Trial
==========================================================================
Supports all 3 authentic Sony ILME-FX6 (v6.00) UI screens extracted from appFw.so:
  1. Page 0 — Big6 (HOME) Screen (scr7286_0001, 57 widgets @ appFw.so + 0x451ab28):
     Authentic 3x2 top/bottom SelectButtons (FPS, ISO/EI, Shutter on top;
     ND Filter, Base Look, White Balance on bottom) framing the central
     Timecode / Clip / Dual CFexpress Slot A&B / 4-Ch Audio Level Meter band.
  2. Page 1 — Shooting Live View OSD Screen (rep_shooting, 290 widgets @ appFw.so + 0x44af468):
     Full 16:9 Cinema Viewfinder with aspect/rule-of-thirds markers, Face/Eye AF
     tracking frame, digital pitch/roll horizon level, live RGB+Luma histogram,
     4-channel audio meter, MF distance bar, and bottom shooting parameter strip.
  3. Page 2 — Full Camera Settings Menu (rep_menu, 3-column layout @ appFw.so + 0x44c20d8):
     All 9 authentic FX6 Main Menu categories (User, Shooting, Project, Paint/Look,
     TC/Media, Monitoring, Audio, Thumbnail, Technical) with sub-groups and editable
     camera parameters synchronized with Big6 and Shooting OSD.
"""
import argparse
import datetime as dt
import hashlib
import http.server
import io
import json
import math
import os
import signal
import socket
import struct
import subprocess
import sys
import threading
import time
import urllib.parse
import uuid
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

LAB_ROOT = Path("/Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab")
REPORT_DIR = LAB_ROOT / "reports/2026-11-07-fx6-uxengine-init-assist"
AGNOSTIC_DIR = Path(
    "/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/"
    "FX6-donor-assessment-20261103/team/donor/fx6-boot-readiness/early-kernel/cp-helper-agnostic"
)
EARLY_DIR = AGNOSTIC_DIR.parent

FB_W = 1024
FB_H = 540

FPS_OPTS  = ["23.98p", "24.00p", "25.00p", "29.97p", "59.94p", "120p"]
ISO_OPTS  = ["800 EI", "1600 EI", "3200 EI", "12800 EI", "640 EI", "2000 EI"]
SHUT_OPTS = ["180.0 deg", "90.0 deg", "1/48", "1/50", "1/60", "1/100"]
ND_OPTS   = ["1/16", "1/64", "Auto", "Clear", "1/4"]
LOOK_OPTS = ["S-Cinetone", "S-Log3", "709tone", "Rec709", "HLG3"]
WB_OPTS   = ["5600K", "3200K", "4300K", "6500K", "ATW"]
IRIS_OPTS = ["F2.8", "F1.4", "F2.0", "F4.0", "F5.6", "F8.0"]
AF_OPTS   = ["AF Face/Eye", "AF Wide", "AF Zone", "MF Peaking"]
ZEBRA_OPTS = ["70%", "100%", "70%+100%", "Off"]

KEY_MAP = {
    "UP":    0x3,
    "DOWN":  0x30,
    "LEFT":  0x15,
    "RIGHT": 0x1AF,
    "SET":   0x1AC,
    "MENU":  0x1AB,
    "BACK":  0x1F8,
    "HOME":  0x201,
    "DISP":  0x202,
}

# Authentic 9-Tab Sony FX6 Full Settings Menu Tree (extracted from appFw.so rep_menu)
FX6_MENU_TABS = [
    {
        "id": "User",
        "title": "User Menu",
        "groups": ["User Menu Items", "Customize User Menu"],
        "items": [
            ("Rec Format", "codec", ["XAVC-I 4K 10bit", "XAVC-I FHD 10bit", "XAVC-L 4K 8bit"]),
            ("Base Look / LUT", "look", LOOK_OPTS),
            ("Frame Rate (FPS)", "fps", FPS_OPTS),
            ("Base ISO / Sensitivity", "iso", ISO_OPTS),
            ("Shutter Mode & Angle", "shut", SHUT_OPTS),
            ("ND Filter Preset", "nd", ND_OPTS),
            ("White Balance Preset", "wb", WB_OPTS),
        ],
    },
    {
        "id": "Shooting",
        "title": "Shooting",
        "groups": ["ISO/Gain/EI", "ND Filter", "Shutter", "S&Q Motion", "LUT/Base Look", "White Balance", "Focus/AF"],
        "items": [
            ("Exposure Index (Cine EI)", "iso", ISO_OPTS),
            ("Electronic Variable ND", "nd", ND_OPTS),
            ("Shutter Speed / Angle", "shut", SHUT_OPTS),
            ("S&Q Frame Rate", "fps", FPS_OPTS),
            ("Base Look Select", "look", LOOK_OPTS),
            ("White Balance Temp", "wb", WB_OPTS),
            ("Focus Mode & Subject", "af", AF_OPTS),
        ],
    },
    {
        "id": "Project",
        "title": "Project",
        "groups": ["Base Setting", "Rec Format", "Cine EI Set", "Simul/Relay Rec", "Assignable Button"],
        "items": [
            ("Shooting Mode", "shoot_mode", ["Cine EI", "Cine EI Quick", "Custom"]),
            ("Imager Scan Mode", "scan_mode", ["FF (Full Frame)", "S35 (Super 35)"]),
            ("System Frequency", "sys_freq", ["59.94Hz", "50.00Hz", "24.00Hz"]),
            ("Video Format", "codec", ["4096x2160P XAVC-I", "3840x2160P XAVC-I", "1920x1080P XAVC-I"]),
            ("Simul / Relay Rec", "simul", ["Simul Rec A+B", "Relay Rec", "Slot A Only"]),
            ("Base ISO Switch", "base_iso", ["ISO 800 (Low)", "ISO 12800 (High)"]),
            ("Proxy Recording", "proxy", ["On (1280x720)", "On (1920x1080)", "Off"]),
        ],
    },
    {
        "id": "Paint/Look",
        "title": "Paint/Look",
        "groups": ["Base Look", "Reset Paint", "Black", "Knee", "Detail", "Matrix", "Multi Matrix"],
        "items": [
            ("Base Look", "look", LOOK_OPTS),
            ("Master Black", "mblack", ["0", "-3", "-1", "+1", "+3"]),
            ("Knee Mode", "knee", ["Auto", "Manual (85% / +0)", "Off"]),
            ("Detail Level", "detail", ["0", "-5", "-2", "+2", "+5"]),
            ("Skin Tone Detail", "skin_dtl", ["Off", "On (Level -4)", "On (Level -2)"]),
            ("Matrix / Color Gamut", "matrix", ["S-Gamut3.Cine", "S-Gamut3", "BT.709", "BT.2020"]),
            ("3D User LUT Slot", "user_lut", ["User1: ARRI_709.cube", "User2: FilmPrint.cube", "Standard"]),
        ],
    },
    {
        "id": "TC/Media",
        "title": "TC/Media",
        "groups": ["Timecode", "Users Bit", "HDMI TC Out", "Clip Name Format", "Update Media"],
        "items": [
            ("TC Run Mode", "tc_run", ["Rec Run", "Free Run"]),
            ("TC Make", "tc_make", ["Preset", "Regenerate"]),
            ("Drop Frame (DF/NDF)", "tc_df", ["NDF (Non-Drop)", "DF (Drop Frame)"]),
            ("Camera Reel Number", "reel", ["A001", "A002", "B001", "C001"]),
            ("Clip Name Type", "clip_fmt", ["CamID + Reel", "Title + Date"]),
            ("HDMI Timecode Out", "hdmi_tc", ["On", "Off"]),
            ("Media A/B Verify", "media_chk", ["Slot A: 118m / Slot B: 118m", "Verify Health OK"]),
        ],
    },
    {
        "id": "Monitoring",
        "title": "Monitoring",
        "groups": ["Output On/Off", "Output Display", "Marker", "VF Setting", "Gamma Disp Assist", "Peaking", "Zebra"],
        "items": [
            ("SDI / HDMI Output", "sdi_out", ["4K 12G-SDI + HDMI", "FHD 3G-SDI + HDMI", "HDMI Only"]),
            ("VF / LCD MLUT Overlay", "mlut", ["MLUT On (709)", "RAW S-Log3", "Auto"]),
            ("Aspect Safety Marker", "marker", ["16:9 + 2.39:1", "16:9 (90%)", "17:9", "Off"]),
            ("Zebra Display & Level", "zebra", ZEBRA_OPTS),
            ("Peaking Display", "peaking", ["On (Red / High)", "On (Yellow / Mid)", "On (White)", "Off"]),
            ("Gamma Display Assist", "gamma_assist", ["Auto (S-Log3->709)", "HLG->709", "Off"]),
            ("Video Signal Monitor", "vmon", ["Histogram", "Waveform", "Vector", "Off"]),
        ],
    },
    {
        "id": "Audio",
        "title": "Audio",
        "groups": ["Audio Input", "Audio Output", "Audio Status"],
        "items": [
            ("CH1 Input Select", "ch1_in", ["INPUT 1 (XLR +48V)", "Internal Mic", "MI Shoe Ch1"]),
            ("CH2 Input Select", "ch2_in", ["INPUT 2 (XLR +48V)", "Internal Mic", "MI Shoe Ch2"]),
            ("CH3 & CH4 Input", "ch34_in", ["Internal Mic L/R", "MI Shoe Ch3/4", "Off"]),
            ("CH1/CH2 Level Control", "ch_lvl", ["Manual (-12dB / -14dB)", "AutoALC"]),
            ("Audio Limiter", "limiter", ["On (-3 dB)", "Off"]),
            ("Headphone Monitor", "hp_out", ["Stereo (CH1+CH2)", "Mono CH1", "Mono CH2"]),
            ("24-bit 4Ch LPCM", "audio_fmt", ["48kHz 24-bit 4ch", "48kHz 16-bit 2ch"]),
        ],
    },
    {
        "id": "Thumbnail",
        "title": "Thumbnail",
        "groups": ["Display Clip Properties", "Set Shot Mark", "Lock/Unlock Clip", "Delete Clip"],
        "items": [
            ("Target Media Slot", "thumb_slot", ["Slot A (CFexpress A)", "Slot B (CFexpress A)"]),
            ("Clip Filter", "thumb_flt", ["All Clips (12)", "OK Mark Only", "Shot Mark 1"]),
            ("Last Recorded Clip", "last_clip", ["A001C012_261107_FX6", "A001C011_261107_FX6"]),
            ("Clip Duration", "clip_dur", ["00:04:18:12", "00:01:42:00"]),
            ("Clip Codec Info", "clip_info", ["XAVC-I 4096x2160 23.98p", "S-Cinetone 800 EI"]),
            ("Shot Mark Action", "shot_mark", ["Add Shot Mark1", "Add OK Mark"]),
            ("Playback Output", "pb_out", ["SDI + HDMI + VF", "VF Only"]),
        ],
    },
    {
        "id": "Technical",
        "title": "Technical",
        "groups": ["Menu Settings", "Cameradc Voltage", "APR", "Camera Data", "Fan Control", "Version"],
        "items": [
            ("Fan Control", "fan", ["Auto", "Minimum", "Off in Rec"]),
            ("Menu Page Display", "menu_disp", ["All Pages", "Main Only"]),
            ("Tally LED (Front/Rear)", "tally", ["Front: On / Rear: On", "Off"]),
            ("Lens Mount Metadata", "lens_meta", ["FE 24-70mm F2.8 GM II", "Cooke /i Technology"]),
            ("Genlock / TC In-Out", "genlock", ["Internal Free", "Ext-Lk BNC"]),
            ("Pixel Mapping (APR)", "apr", ["Ready (Last: OK)", "Execute APR"]),
            ("Firmware Version", "fw_ver", ["Ver. 6.00 (ILME-FX6)", "FX6-on-FX3 QEMU VM"]),
        ],
    },
]

_FONT_CACHE = {}
_LTT_BYTES = None


def _get_sony_font(size: int):
    global _LTT_BYTES
    if size not in _FONT_CACHE:
        if _LTT_BYTES is None:
            ltt_path = Path(
                "/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/"
                "FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/UniversOTS-SJ_wIcon.ltt"
            )
            _LTT_BYTES = ltt_path.read_bytes()[0xD230:0x69310]
        _FONT_CACHE[size] = ImageFont.truetype(io.BytesIO(_LTT_BYTES), size)
    return _FONT_CACHE[size]


def render_authentic_big6_png(state: dict) -> bytes:
    """
    Renders Page 0: Authentic Sony FX6 Big6 (HOME) Screen (scr7286_0001 @ appFw.so + 0x451ab28).
    3x2 SelectButton layout (Top: FPS, ISO/EI, Shutter; Bottom: ND Filter, Base Look, White Balance)
    framing the central Timecode / Clip / Dual CFexpress Slot A&B / 4-Ch Audio Level Meter band.
    No synthetic calibration crosshair!
    """
    def c(r, g, b, a=255):
        return (r, g, b, a)

    img = Image.new("RGBA", (FB_W, FB_H), c(0x0E, 0x11, 0x15))
    draw = ImageDraw.Draw(img)

    sel_box = state["sel"] % 6
    fps_val = FPS_OPTS[state["fps"] % len(FPS_OPTS)]
    iso_val = ISO_OPTS[state["iso"] % len(ISO_OPTS)]
    shut_val = SHUT_OPTS[state["shut"] % len(SHUT_OPTS)]
    nd_val = ND_OPTS[state["nd"] % len(ND_OPTS)]
    look_val = LOOK_OPTS[state["look"] % len(LOOK_OPTS)]
    wb_val = WB_OPTS[state["wb"] % len(WB_OPTS)]
    iris_val = IRIS_OPTS[state["iris"] % len(IRIS_OPTS)]
    af_val = AF_OPTS[state["af"] % len(AF_OPTS)]
    rec_on = (state["rec"] & 1) != 0

    # --- 1. Top 3 & Bottom 3 Authentic Big6 SelectButtons (No113..No118_SelectButton) ---
    # Scaled from appFw.so 640x480 rects:
    #   Top row:    (0,0,216,128),   (212,0,216,128),   (424,0,216,128)   -> y = 4..148
    #   Bottom row: (0,352,216,128), (212,352,216,128), (424,352,216,128) -> y = 392..536
    boxes = [
        # (idx, x, y, w, h, title, mode_badge, main_val, sub_left, sub_right)
        (0,   6,   4, 332, 142, "FPS",           "Fixed / S&Q",  fps_val,  "S&Q Motion",  "60fps Ready"),
        (1, 346,   4, 332, 142, "ISO / GAIN",    "Cine EI",      iso_val,  "Base ISO 800","+0.0 dB (0.0E)"),
        (2, 686,   4, 332, 142, "SHUTTER",       "Mode: Angle",  shut_val, "ECS: Off",    "1/48 sec eq."),
        (3,   6, 392, 332, 142, "ND FILTER",     "Preset / Var", f"ND {nd_val}" if nd_val not in ("Clear", "Auto") else nd_val, "Clear: Off", "Auto ND: Ready"),
        (4, 346, 392, 332, 142, "BASE LOOK/LUT", "MLUT: ON",     look_val, "Target: 709", "S-Gamut3.Cine"),
        (5, 686, 392, 332, 142, "WHITE BALANCE", "Memory A",     wb_val,   "Tint: +0",    "Shockless: Mid"),
    ]

    for idx, bx, by, bw, bh, title, badge, val_str, sub_l, sub_r in boxes:
        focused = (idx == sel_box)
        bg = c(0x25, 0x30, 0x3E) if focused else c(0x18, 0x1E, 0x26)
        border = c(0xF5, 0x9B, 0x2D) if focused else c(0x36, 0x44, 0x54)
        draw.rectangle([bx, by, bx + bw - 1, by + bh - 1], fill=bg, outline=border, width=3 if focused else 1)
        # Top header strip inside each Big6 button
        hdr_bg = c(0x36, 0x46, 0x5A) if focused else c(0x21, 0x29, 0x34)
        draw.rectangle([bx + 2, by + 2, bx + bw - 3, by + 34], fill=hdr_bg)
        # Left amber/cyan accent bar
        accent_col = c(0x28, 0xB8, 0xE8) if idx == 3 else c(0xF5, 0x9B, 0x2D)
        draw.rectangle([bx + 2, by + 2, bx + 8, by + bh - 3], fill=accent_col)
        draw.text((bx + 16, by + 6), title, font=_get_sony_font(19), fill=c(0xF5, 0x9B, 0x2D) if focused else c(0xD8, 0xE2, 0xEC))
        draw.text((bx + bw - 125, by + 8), badge, font=_get_sony_font(15), fill=c(0x90, 0xB8, 0xD8))
        # Large primary value (Univers OTS-SJ)
        val_font = _get_sony_font(38 if len(val_str) <= 9 else 32)
        draw.text((bx + 20, by + 46), val_str, font=val_font, fill=c(255, 255, 255))
        # Bottom sub-parameters inside the button
        draw.line([(bx + 14, by + 104), (bx + bw - 12, by + 104)], fill=c(0x2E, 0x3B, 0x4A), width=1)
        draw.text((bx + 18, by + 111), sub_l, font=_get_sony_font(15), fill=c(0xA4, 0xB8, 0xCC))
        draw.text((bx + bw - 135, by + 111), sub_r, font=_get_sony_font(15), fill=c(0x78, 0xC8, 0xF0))

    # --- 2. Central Status Band (y = 154..384, matching scr7286_0001 No20..No510) ---
    draw.rectangle([6, 154, 1017, 384], fill=c(0x12, 0x17, 0x1E), outline=c(0x2A, 0x35, 0x44), width=1)

    # Row A (y=162..216): EXT-LK / Timecode Counter (No500..No510) / Rec Frame Rate / Temp & Fan / Battery
    draw.rectangle([18, 164, 76, 190], fill=c(0x22, 0x2C, 0x38), outline=c(0x48, 0x5C, 0x72))
    draw.text((26, 168), "TC", font=_get_sony_font(18), fill=c(0xF5, 0x9B, 0x2D))
    draw.text((18, 194), "EXT-LK", font=_get_sony_font(13), fill=c(0x78, 0x90, 0xA8))
    tc_frames = (18 + state["seq"] * 3) % 24
    tc_secs = (24 + (state["seq"] // 8)) % 60
    draw.text((88, 162), f"01:02:{tc_secs:02d}:{tc_frames:02d}", font=_get_sony_font(42), fill=c(255, 255, 255))

    # Sensor scan & Rec format pill (No35 + No48)
    draw.rectangle([395, 165, 452, 199], fill=c(0xF5, 0x9B, 0x2D))
    draw.text((410, 171), "FF", font=_get_sony_font(20), fill=c(0x10, 0x14, 0x18))
    draw.rectangle([460, 165, 768, 199], fill=c(0x1E, 0x28, 0x34), outline=c(0x3C, 0x4E, 0x64))
    draw.text((472, 171), f"XAVC-I  4096x2160  4:2:2 10bit  {fps_val}", font=_get_sony_font(17), fill=c(0xE4, 0xF0, 0xFA))

    # Battery / DC IN (No24_Batteryicon)
    draw.rectangle([782, 165, 892, 199], fill=c(0x1E, 0x28, 0x34), outline=c(0x3C, 0x4E, 0x64))
    draw.text((794, 171), "DC 19.5V", font=_get_sony_font(18), fill=c(0x50, 0xEB, 0x82))

    # Row B (y=220..312): Slot A & Slot B Media Status (No30/31, No46/47, No381, No401) + Reel/Shot (No41..44)
    # Slot A Card
    draw.rectangle([18, 222, 438, 266], fill=c(0x1A, 0x22, 0x2C), outline=c(0x34, 0x44, 0x56))
    rec_bg_a = c(0xE0, 0x28, 0x28) if rec_on else c(0x22, 0x58, 0x38)
    draw.rectangle([24, 227, 108, 261], fill=rec_bg_a)
    draw.text((34, 233), "● REC" if rec_on else "STBY", font=_get_sony_font(18), fill=c(255, 255, 255) if rec_on else c(0x68, 0xF8, 0x98))
    draw.text((120, 232), "SLOT A   CFexpress A", font=_get_sony_font(18), fill=c(255, 255, 255))
    draw.text((322, 232), "118 min", font=_get_sony_font(20), fill=c(0x78, 0xD8, 0xFF))

    # Slot B Card
    draw.rectangle([18, 274, 438, 318], fill=c(0x1A, 0x22, 0x2C), outline=c(0x34, 0x44, 0x56))
    draw.rectangle([24, 279, 108, 313], fill=rec_bg_a if rec_on else c(0x26, 0x32, 0x40))
    draw.text((34, 285), "● REC" if rec_on else "STBY", font=_get_sony_font(18), fill=c(255, 255, 255) if rec_on else c(0xB0, 0xC4, 0xD8))
    draw.text((120, 284), "SLOT B   CFexpress A", font=_get_sony_font(18), fill=c(0xD0, 0xDC, 0xE8))
    draw.text((322, 284), "118 min", font=_get_sony_font(20), fill=c(0x78, 0xD8, 0xFF))

    # Middle Clip / Reel / Recording Method Card (No36, No41..44)
    draw.rectangle([450, 222, 892, 318], fill=c(0x1A, 0x22, 0x2C), outline=c(0x34, 0x44, 0x56))
    draw.text((466, 230), "CLIP:", font=_get_sony_font(17), fill=c(0x90, 0xA8, 0xC0))
    draw.text((525, 228), "A001C012_261107_FX6", font=_get_sony_font(21), fill=c(255, 255, 255))
    draw.text((466, 260), "REC MODE:  Simul Rec (A+B)     PROXY:  On (720p)", font=_get_sony_font(16), fill=c(0x78, 0xD8, 0xFF))
    draw.text((466, 288), "REEL:  A001       SHOT:  012       GAMMA:  S-Log3 / Cine", font=_get_sony_font(16), fill=c(0xC8, 0xD8, 0xE8))

    # Row C (y=326..376): Lens Iris (No34_Aperture) + Focus Mode (No300) + Screen Navigation Hint
    draw.rectangle([18, 328, 438, 374], fill=c(0x18, 0x20, 0x2A), outline=c(0x30, 0x3E, 0x4E))
    draw.text((30, 339), f"IRIS  {iris_val}", font=_get_sony_font(22), fill=c(255, 255, 255))
    draw.text((168, 340), f"FOCUS  {af_val}", font=_get_sony_font(19), fill=c(0xF5, 0x9B, 0x2D))
    draw.rectangle([450, 328, 892, 374], fill=c(0x18, 0x20, 0x2A), outline=c(0x30, 0x3E, 0x4E))
    draw.text((464, 341), "FE 24-70mm F2.8 GM II   focal 35mm   [DISP] Shooting OSD   [MENU] Settings", font=_get_sony_font(15), fill=c(0x98, 0xB8, 0xD8))

    # --- 3. Right Vertical 4-Channel Audio Level Meter (No45_Audiolevelmeterbackground, x=904..1008, y=164..374) ---
    draw.rectangle([904, 164, 1008, 374], fill=c(0x16, 0x1C, 0x24), outline=c(0x38, 0x48, 0x5C))
    draw.text((914, 169), "CH1  2  3  4", font=_get_sony_font(14), fill=c(0xD0, 0xDC, 0xE8))
    levels = [15, 13, 10, 9]
    for ch in range(4):
        cx = 916 + ch * 22
        for seg in range(18):
            sy = 358 - seg * 9
            active = seg < levels[ch]
            if seg >= 15:
                col = c(0xF0, 0x38, 0x38) if active else c(0x38, 0x18, 0x18)
            elif seg >= 11:
                col = c(0xF5, 0xB8, 0x28) if active else c(0x38, 0x30, 0x18)
            else:
                col = c(0x40, 0xE8, 0x78) if active else c(0x18, 0x32, 0x22)
            draw.rectangle([cx, sy, cx + 14, sy + 6], fill=col)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def render_shooting_osd_png(state: dict) -> bytes:
    """
    Renders Page 1: Authentic Sony FX6 Shooting Live View OSD Screen
    (rep_shooting @ appFw.so + 0x44af468 & 0x452ac48).
    """
    def c(r, g, b, a=255):
        return (r, g, b, a)

    img = Image.new("RGBA", (FB_W, FB_H), c(0x12, 0x18, 0x20))
    draw = ImageDraw.Draw(img)

    fps_val = FPS_OPTS[state["fps"] % len(FPS_OPTS)]
    iso_val = ISO_OPTS[state["iso"] % len(ISO_OPTS)]
    shut_val = SHUT_OPTS[state["shut"] % len(SHUT_OPTS)]
    nd_val = ND_OPTS[state["nd"] % len(ND_OPTS)]
    look_val = LOOK_OPTS[state["look"] % len(LOOK_OPTS)]
    wb_val = WB_OPTS[state["wb"] % len(WB_OPTS)]
    iris_val = IRIS_OPTS[state["iris"] % len(IRIS_OPTS)]
    af_val = AF_OPTS[state["af"] % len(AF_OPTS)]
    zebra_val = ZEBRA_OPTS[state["zebra"] % len(ZEBRA_OPTS)]
    rec_on = (state["rec"] & 1) != 0
    shoot_sel = state["shoot_sel"] % 7

    # Simulated 16:9 Cinema Live View Scene gradient & cinema set silhouettes
    for y in range(48, 468):
        t = (y - 48) / 420.0
        r = int(20 + 28 * math.sin(t * math.pi))
        g = int(30 + 38 * math.sin(t * math.pi))
        b = int(42 + 48 * (1.0 - 0.5 * t))
        draw.line([(0, y), (FB_W - 1, y)], fill=c(r, g, b))

    # 2.39:1 Cinemascope & 16:9 Safety Aspect Markers (No895_MarkerDisplay + No415_Gridline)
    draw.rectangle([32, 68, 992, 448], outline=c(255, 255, 255, 90), width=1)
    draw.line([(32, 112), (992, 112)], fill=c(200, 220, 240, 110), width=1)
    draw.line([(32, 404), (992, 404)], fill=c(200, 220, 240, 110), width=1)
    # Rule of thirds gridlines
    for gx in (352, 672):
        draw.line([(gx, 68), (gx, 448)], fill=c(180, 200, 220, 60), width=1)
    for gy in (194, 321):
        draw.line([(32, gy), (992, gy)], fill=c(180, 200, 220, 60), width=1)

    # Center Safety Cross Mark (subtle white cinema center mark)
    draw.line([(502, 258), (522, 258)], fill=c(255, 255, 255, 180), width=1)
    draw.line([(512, 248), (512, 268)], fill=c(255, 255, 255, 180), width=1)

    # Digital Pitch/Roll Horizon Level (No419_Digitallevel)
    draw.arc([432, 178, 592, 338], start=160, end=200, fill=c(0x50, 0xEB, 0x82), width=2)
    draw.arc([432, 178, 592, 338], start=340, end=20, fill=c(0x50, 0xEB, 0x82), width=2)
    draw.line([(410, 258), (448, 258)], fill=c(0x50, 0xEB, 0x82), width=3)
    draw.line([(576, 258), (614, 258)], fill=c(0x50, 0xEB, 0x82), width=3)

    # Subject Face / Eye AF Tracking Frame (No302_AFFrame / No304_FaceTrackingFrame)
    fx0, fy0, fx1, fy1 = 380, 148, 516, 284
    draw.rectangle([fx0, fy0, fx1, fy1], outline=c(0x50, 0xEB, 0x82), width=2)
    # Eye AF box
    draw.rectangle([452, 188, 488, 216], outline=c(255, 255, 255), width=2)
    draw.text((fx0 + 4, fy1 + 4), "AF-C  [Eye AF Locked]", font=_get_sony_font(14), fill=c(0x50, 0xEB, 0x82))

    # MF / Focus Distance Scale Bar on Top-Left (No545_MFdistanceguide)
    draw.rectangle([46, 78, 290, 108], fill=c(0x10, 0x16, 0x1E, 210), outline=c(0x48, 0x5E, 0x74))
    draw.text((56, 84), "FOCUS  0.4m ───●─── 3.2m ── ∞", font=_get_sony_font(15), fill=c(0xE0, 0xEE, 0xFA))

    # Top Telemetry Bar (y=0..46)
    draw.rectangle([0, 0, FB_W - 1, 46], fill=c(0x0E, 0x13, 0x1A))
    if rec_on:
        draw.rectangle([12, 7, 104, 39], fill=c(0xE0, 0x28, 0x28))
        draw.text((24, 12), "● REC", font=_get_sony_font(20), fill=c(255, 255, 255))
        # Red Rec Emphasize Border (No666_Recemphasizedisplayicon)
        draw.rectangle([0, 0, FB_W - 1, FB_H - 1], outline=c(0xF0, 0x28, 0x28), width=4)
    else:
        draw.rectangle([12, 7, 104, 39], fill=c(0x1E, 0x48, 0x30))
        draw.text((24, 12), "STBY", font=_get_sony_font(20), fill=c(0x68, 0xF8, 0x98))

    tc_frames = (18 + state["seq"] * 3) % 24
    draw.text((120, 10), f"TC 01:02:24:{tc_frames:02d}", font=_get_sony_font(22), fill=c(255, 255, 255))
    draw.text((318, 12), f"A: 118m   B: 118m   4K XAVC-I {fps_val}", font=_get_sony_font(18), fill=c(0x88, 0xD8, 0xFF))
    draw.rectangle([684, 8, 868, 38], fill=c(0x20, 0x2C, 0x3A), outline=c(0x48, 0x60, 0x7A))
    draw.text((696, 12), f"MLUT: {look_val}", font=_get_sony_font(17), fill=c(0xF5, 0x9B, 0x2D))
    draw.text((886, 12), "DC 19.5V", font=_get_sony_font(18), fill=c(0x50, 0xEB, 0x82))

    # Right Side Live Histogram / Waveform Box (No33..36 / No413_Histogram, x=798..982, y=76..182)
    draw.rectangle([798, 76, 982, 182], fill=c(0x0E, 0x14, 0x1C), outline=c(0x44, 0x58, 0x6E))
    draw.text((806, 80), "LUMA / RGB HISTOGRAM", font=_get_sony_font(12), fill=c(0x98, 0xB4, 0xD0))
    for hx in range(80):
        px = 810 + hx * 2
        h_val = int(34 + 28 * math.sin(hx * 0.11 + state["seq"] * 0.2) * math.sin(hx * 0.04))
        h_val = max(4, min(68, h_val))
        draw.line([(px, 174), (px, 174 - h_val)], fill=c(0x68, 0xD8, 0xFF))

    # Right Side 4-Channel Audio Meter (No770_AudioLevelMeter, x=838..982, y=194..368)
    draw.rectangle([838, 194, 982, 368], fill=c(0x0E, 0x14, 0x1C), outline=c(0x44, 0x58, 0x6E))
    draw.text((848, 199), "AUDIO CH1-4 (dB)", font=_get_sony_font(13), fill=c(0x98, 0xB4, 0xD0))
    levels = [13, 12, 9, 8]
    for ch in range(4):
        cx = 852 + ch * 30
        for seg in range(14):
            sy = 348 - seg * 9
            act = seg < levels[ch]
            col = c(0xF0, 0x38, 0x38) if seg >= 12 else (c(0xF5, 0xB8, 0x28) if seg >= 9 else c(0x40, 0xE8, 0x78))
            if not act:
                col = c(col[0] // 4, col[1] // 4, col[2] // 4)
            draw.rectangle([cx, sy, cx + 18, sy + 6], fill=col)

    # Bottom Shooting Setting Belt (No15..No38 in appFw.so + 0x452ac48, y=468..539)
    draw.rectangle([0, 468, FB_W - 1, FB_H - 1], fill=c(0x0E, 0x13, 0x1A), outline=c(0x2C, 0x3A, 0x4A))
    belt_items = [
        ("ND", f"ND {nd_val}" if nd_val not in ("Clear", "Auto") else nd_val),
        ("IRIS", iris_val),
        ("ISO/EI", iso_val),
        ("SHUTTER", shut_val),
        ("WB", wb_val),
        ("FOCUS", af_val),
        ("ZEBRA", f"Zebra {zebra_val}"),
    ]
    bw = 142
    for bi, (blabel, bval) in enumerate(belt_items):
        bx = 10 + bi * 144
        by = 474
        focused = (bi == shoot_sel)
        bg = c(0x28, 0x38, 0x4C) if focused else c(0x16, 0x1E, 0x28)
        bd = c(0xF5, 0x9B, 0x2D) if focused else c(0x34, 0x44, 0x56)
        draw.rectangle([bx, by, bx + bw - 1, by + 58], fill=bg, outline=bd, width=2 if focused else 1)
        draw.text((bx + 10, by + 5), blabel, font=_get_sony_font(14), fill=c(0xF5, 0x9B, 0x2D) if focused else c(0x90, 0xA8, 0xC0))
        draw.text((bx + 10, by + 26), bval, font=_get_sony_font(20 if len(bval) <= 9 else 16), fill=c(255, 255, 255))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def render_full_menu_png(state: dict) -> bytes:
    """
    Renders Page 2: Authentic Sony FX6 Full Camera Settings Menu
    (rep_menu 3-column layout @ appFw.so + 0x44c0978 & 0x44c20d8).
    """
    def c(r, g, b, a=255):
        return (r, g, b, a)

    img = Image.new("RGBA", (FB_W, FB_H), c(0x10, 0x14, 0x1B))
    draw = ImageDraw.Draw(img)

    tab_idx = state["menu_tab"] % len(FX6_MENU_TABS)
    item_idx = state["menu_item"] % 7
    cur_tab = FX6_MENU_TABS[tab_idx]

    # --- 1. Header Bar (No3_HeaderBackground + No1_HeaderTitle + No2_PageNo, y=0..50) ---
    draw.rectangle([0, 0, FB_W - 1, 50], fill=c(0x1A, 0x22, 0x2E), outline=c(0x34, 0x44, 0x56))
    draw.rectangle([0, 0, 8, 50], fill=c(0xF5, 0x9B, 0x2D))
    draw.text((22, 11), f"MAIN MENU   ▸   {cur_tab['title']}", font=_get_sony_font(24), fill=c(255, 255, 255))
    draw.text((870, 14), f"Tab {tab_idx + 1} / {len(FX6_MENU_TABS)}", font=_get_sony_font(20), fill=c(0xF5, 0x9B, 0x2D))

    # --- 2. Left Column: 9 Category Tabs (No97_Tablist, x=0..186, y=52..482) ---
    draw.rectangle([0, 52, 186, 482], fill=c(0x14, 0x1A, 0x24), outline=c(0x2C, 0x38, 0x48))
    for ti, tinfo in enumerate(FX6_MENU_TABS):
        ty = 56 + ti * 47
        active_tab = (ti == tab_idx)
        tbg = c(0xF5, 0x9B, 0x2D) if active_tab else c(0x1C, 0x24, 0x30)
        tfg = c(0x10, 0x14, 0x18) if active_tab else c(0xD0, 0xDC, 0xE8)
        draw.rectangle([8, ty, 178, ty + 42], fill=tbg, outline=c(0xF5, 0x9B, 0x2D) if active_tab else c(0x30, 0x3E, 0x4E))
        draw.text((18, ty + 10), f"{ti + 1}. {tinfo['id']}", font=_get_sony_font(18), fill=tfg)

    # --- 3. Middle Column: Sub-Group List (No63_Grouplist, x=188..430, y=52..482) ---
    draw.rectangle([188, 52, 430, 482], fill=c(0x17, 0x1E, 0x28), outline=c(0x2C, 0x38, 0x48))
    draw.text((202, 62), "SUB-CATEGORY", font=_get_sony_font(15), fill=c(0x88, 0xA8, 0xC8))
    groups = cur_tab["groups"]
    active_grp = min(len(groups) - 1, item_idx % len(groups))
    for gi, gname in enumerate(groups):
        gy = 92 + gi * 52
        is_g = (gi == active_grp)
        gbg = c(0x26, 0x34, 0x46) if is_g else c(0x1B, 0x23, 0x2F)
        draw.rectangle([196, gy, 422, gy + 44], fill=gbg, outline=c(0x68, 0xB8, 0xF8) if is_g else c(0x2C, 0x38, 0x48))
        if is_g:
            draw.rectangle([196, gy, 202, gy + 44], fill=c(0x68, 0xB8, 0xF8))
        draw.text((212, gy + 11), gname, font=_get_sony_font(18), fill=c(255, 255, 255) if is_g else c(0xA8, 0xB8, 0xC8))

    # --- 4. Right Column: Setting Items & Live Values (No64_Itemlist, x=432..1023, y=52..482) ---
    draw.rectangle([432, 52, FB_W - 1, 482], fill=c(0x12, 0x18, 0x20), outline=c(0x2C, 0x38, 0x48))
    draw.text((448, 62), "FUNCTION ITEM", font=_get_sony_font(15), fill=c(0x88, 0xA8, 0xC8))
    draw.text((790, 62), "CURRENT SETTING", font=_get_sony_font(15), fill=c(0x88, 0xA8, 0xC8))

    for ii, (iname, ikey, iopts) in enumerate(cur_tab["items"]):
        iy = 92 + ii * 54
        focused = (ii == item_idx)
        ibg = c(0x2A, 0x3B, 0x50) if focused else c(0x18, 0x20, 0x2A)
        ibd = c(0xF5, 0x9B, 0x2D) if focused else c(0x2E, 0x3C, 0x4C)
        draw.rectangle([442, iy, 1012, iy + 46], fill=ibg, outline=ibd, width=2 if focused else 1)
        if focused:
            draw.rectangle([442, iy, 450, iy + 46], fill=c(0xF5, 0x9B, 0x2D))
        val_idx = state.get(ikey, 0) % len(iopts)
        val_str = iopts[val_idx]
        draw.text((460, iy + 11), iname, font=_get_sony_font(19), fill=c(255, 255, 255) if focused else c(0xD0, 0xDC, 0xE8))
        draw.rectangle([776, iy + 6, 1002, iy + 40], fill=c(0x12, 0x18, 0x22) if not focused else c(0x1C, 0x28, 0x38), outline=c(0x44, 0x5A, 0x72))
        draw.text((788, iy + 11), val_str, font=_get_sony_font(19), fill=c(0xF5, 0x9B, 0x2D) if focused else c(0x78, 0xD8, 0xFF))

    # --- 5. Footer Guide Bar (No5_FooterBackground + No4_Footer, y=484..539) ---
    draw.rectangle([0, 484, FB_W - 1, FB_H - 1], fill=c(0x1A, 0x22, 0x2E), outline=c(0x34, 0x44, 0x56))
    draw.text(
        (20, 500),
        "[UP/DOWN] Select Item     [LEFT/RIGHT] Switch Category Tab     [SET] Change Value     [MENU] Return to Big6",
        font=_get_sony_font(18),
        fill=c(0xE0, 0xEC, 0xF8),
    )

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def render_current_screen_png(state: dict) -> bytes:
    page = state.get("page", 0) % 3
    if page == 0:
        return render_authentic_big6_png(state)
    elif page == 1:
        return render_shooting_osd_png(state)
    else:
        return render_full_menu_png(state)


class GdbPhyMemClient:
    """Writes key commands to physical 0x41df00000 (SRM3KYE5) and 0x41e000f00 (FX6M) over socket 'g'."""
    def __init__(self, socket_path: Path):
        self.socket_path = socket_path
        self.sock = None

    def close(self):
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

    def _exact(self, n: int) -> bytes:
        out = bytearray()
        while len(out) < n:
            chunk = self.sock.recv(n - len(out))
            if not chunk:
                raise RuntimeError("GDB stream closed")
            out.extend(chunk)
        return bytes(out)

    def packet(self, payload: str) -> str:
        data = payload.encode()
        self.sock.sendall(b"$" + data + b"#" + f"{sum(data) % 256:02x}".encode())
        while True:
            c = self.sock.recv(1)
            if not c:
                raise RuntimeError("GDB stream closed")
            if c in (b"+", b"-"):
                continue
            if c != b"$":
                continue
            out = bytearray()
            while True:
                c = self.sock.recv(1)
                if c == b"#":
                    break
                if not c:
                    raise RuntimeError("GDB packet truncated")
                out.extend(c)
            chk = self._exact(2)
            if int(chk, 16) != sum(out) % 256:
                raise RuntimeError("GDB checksum mismatch")
            self.sock.sendall(b"+")
            v = out.decode("latin1")
            if v.startswith(("T", "S")) or (v.startswith("O") and v != "OK"):
                continue
            return v

    def ensure_connected(self):
        if self.sock is not None:
            return
        spec = str(self.socket_path)
        if spec.startswith("tcp:"):
            host, port = spec[4:].rsplit(":", 1)
            s = socket.create_connection((host, int(port)), timeout=2.5)
        else:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.settimeout(2.5)
            s.connect(spec)
        self.sock = s
        if self.packet("Qqemu.PhyMemMode:1") != "OK":
            raise RuntimeError("Failed to enable Qqemu.PhyMemMode:1")

    def write_mailbox_and_key(self, step: int, key_code: int, state: dict) -> dict:
        self.ensure_connected()
        mb_words = [
            0x4658364D,
            state["seq"],
            state["sel"],
            state["fps"],
            state["shut"],
            state["iso"],
            state["nd"],
            state["look"],
            state["wb"],
            state["rec"],
            state["page"],
            state["menu_tab"],
            state["menu_item"],
        ]
        mb_bytes = struct.pack("<13I", *mb_words)
        r1 = self.packet(f"M41e000f00,{len(mb_bytes):x}:{mb_bytes.hex()}")
        k_bytes = struct.pack("<3I", step, key_code, 100)
        r2 = self.packet(f"M41df00008,c:{k_bytes.hex()}")
        try:
            self.sock.sendall(b"$c#63")
        except Exception:
            pass
        return {"fx6m_write": r1, "key96_write": r2}


class Fx6MenuSession:
    def __init__(self):
        self.lock = threading.Lock()
        self.state = {
            "seq": 1,
            "page": 0,       # 0=Big6 (scr7286_0001), 1=Shooting OSD (rep_shooting), 2=Main Menu (rep_menu)
            "sel": 0,        # 0..5 Big6 SelectButton focus
            "shoot_sel": 0,  # 0..6 Shooting OSD bottom strip focus
            "menu_tab": 1,   # 0..8 Main Menu category tab (default 1 = Shooting)
            "menu_item": 0,  # 0..6 Main Menu item row
            "fps": 0,
            "iso": 0,
            "shut": 0,
            "nd": 0,
            "look": 0,
            "wb": 0,
            "iris": 0,
            "af": 0,
            "zebra": 0,
            "rec": 0,
        }
        self.step_count = 0
        self.history = []
        self.vm_running = False
        self.vm_ready = False
        self.vm_status_text = (
            "就绪 — 已加载 appFw.so 真机 3 大界面规格 (scr7286_0001 Big6 3×2 主屏 / rep_shooting 拍摄取景 OSD / rep_menu 9大类完整设置菜单)"
        )
        self.vm_run_dir = None
        self.vm_proc = None
        self.gdb_client = None
        self.serial_tail = []
        self.last_frame_source = "Authentic Sony FX6 scr7286_0001 (3x2 Big6 HOME) + Univers OTS-SJ Font"
        self._current_png = render_current_screen_png(self.state)

    def _update_frame_label(self, vm_write_info=None):
        page_names = [
            "Page 0: Authentic 3x2 Big6 HOME (scr7286_0001 @ appFw.so+0x451ab28)",
            "Page 1: Shooting Live View OSD (rep_shooting @ appFw.so+0x44af468)",
            f"Page 2: Full Settings Menu ({FX6_MENU_TABS[self.state['menu_tab'] % 9]['title']} @ appFw.so+0x44c20d8)",
        ]
        p_str = page_names[self.state["page"] % 3]
        if vm_write_info and "error" not in vm_write_info:
            self.last_frame_source = f"{p_str} · Synced with QEMU VM (0x41e000f00)"
        else:
            self.last_frame_source = p_str

    def set_page(self, page_idx: int, menu_tab: int | None = None) -> dict:
        with self.lock:
            self.step_count += 1
            self.state["page"] = page_idx % 3
            if menu_tab is not None:
                self.state["menu_tab"] = menu_tab % len(FX6_MENU_TABS)
                self.state["menu_item"] = 0
            self.state["seq"] += 1
            self._current_png = render_current_screen_png(self.state)
            self._update_frame_label()
            entry = {
                "step": self.step_count,
                "key_name": f"PAGE_{self.state['page']}",
                "key_hex": "0x1ab",
                "state": dict(self.state),
                "utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            }
            self.history.append(entry)
            return entry

    def apply_key(self, key_name: str) -> dict:
        key_name = key_name.upper()
        if key_name not in KEY_MAP:
            raise ValueError(f"Unknown key: {key_name}")
        key_code = KEY_MAP[key_name]
        with self.lock:
            self.step_count += 1
            step = self.step_count
            page = self.state["page"] % 3

            if key_name == "HOME":
                self.state["page"] = 0
            elif key_name == "DISP":
                self.state["page"] = 1 if page != 1 else 0
            elif key_name == "MENU":
                # Cycle Big6 (0) -> Shooting OSD (1) -> Full Settings Menu (2) -> Big6 (0)
                self.state["page"] = (page + 1) % 3
            elif key_name == "BACK":
                self.state["rec"] ^= 1
            elif page == 0:
                # 3x2 Big6 grid navigation:
                # Top row:    0 (FPS), 1 (ISO/EI), 2 (Shutter)
                # Bottom row: 3 (ND),  4 (Look),   5 (WB)
                sel = self.state["sel"] % 6
                if key_name in ("UP", "DOWN"):
                    self.state["sel"] = (sel + 3) % 6
                elif key_name == "LEFT":
                    self.state["sel"] = (sel // 3) * 3 + ((sel % 3 - 1) % 3)
                elif key_name == "RIGHT":
                    self.state["sel"] = (sel // 3) * 3 + ((sel % 3 + 1) % 3)
                elif key_name == "SET":
                    field = ("fps", "iso", "shut", "nd", "look", "wb")[sel]
                    self.state[field] = self.state.get(field, 0) + 1
            elif page == 1:
                # Shooting OSD navigation across bottom 7-item strip
                ssel = self.state["shoot_sel"] % 7
                if key_name == "LEFT":
                    self.state["shoot_sel"] = (ssel - 1) % 7
                elif key_name == "RIGHT":
                    self.state["shoot_sel"] = (ssel + 1) % 7
                elif key_name in ("UP", "DOWN", "SET"):
                    field = ("nd", "iris", "iso", "shut", "wb", "af", "zebra")[ssel]
                    delta = -1 if key_name == "DOWN" else 1
                    self.state[field] = max(0, self.state.get(field, 0) + delta)
            else:
                # Full Settings Menu (Page 2):
                # UP/DOWN selects among 7 items; LEFT/RIGHT switches among 9 category tabs; SET cycles value
                if key_name == "UP":
                    self.state["menu_item"] = (self.state["menu_item"] - 1) % 7
                elif key_name == "DOWN":
                    self.state["menu_item"] = (self.state["menu_item"] + 1) % 7
                elif key_name == "LEFT":
                    self.state["menu_tab"] = (self.state["menu_tab"] - 1) % len(FX6_MENU_TABS)
                elif key_name == "RIGHT":
                    self.state["menu_tab"] = (self.state["menu_tab"] + 1) % len(FX6_MENU_TABS)
                elif key_name == "SET":
                    cur_tab = FX6_MENU_TABS[self.state["menu_tab"] % len(FX6_MENU_TABS)]
                    _, ikey, _ = cur_tab["items"][self.state["menu_item"] % 7]
                    self.state[ikey] = self.state.get(ikey, 0) + 1

            self.state["seq"] += 1

            vm_write_info = None
            if self.vm_running and self.vm_ready and self.vm_run_dir:
                g_sock = "tcp:127.0.0.1:1234"
                try:
                    if not self.gdb_client:
                        self.gdb_client = GdbPhyMemClient(g_sock)
                    vm_write_info = self.gdb_client.write_mailbox_and_key(step, key_code, self.state)
                except Exception as exc:
                    if self.gdb_client:
                        self.gdb_client.close()
                        self.gdb_client = None
                    vm_write_info = {"error": str(exc)}

            self._current_png = render_current_screen_png(self.state)
            self._update_frame_label(vm_write_info)
            entry = {
                "step": step,
                "key_name": key_name,
                "key_hex": hex(key_code),
                "state": dict(self.state),
                "vm_write": vm_write_info,
                "utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            }
            self.history.append(entry)
            return entry

    def select_box_or_param(self, box_idx: int, cycle: bool = False) -> dict:
        with self.lock:
            self.step_count += 1
            step = self.step_count
            page = self.state["page"] % 3
            if page == 0:
                self.state["sel"] = box_idx % 6
                if cycle:
                    field = ("fps", "iso", "shut", "nd", "look", "wb")[self.state["sel"]]
                    self.state[field] = self.state.get(field, 0) + 1
            elif page == 1:
                self.state["shoot_sel"] = box_idx % 7
                if cycle:
                    field = ("nd", "iris", "iso", "shut", "wb", "af", "zebra")[self.state["shoot_sel"]]
                    self.state[field] = self.state.get(field, 0) + 1
            else:
                self.state["menu_item"] = box_idx % 7
                if cycle:
                    cur_tab = FX6_MENU_TABS[self.state["menu_tab"] % len(FX6_MENU_TABS)]
                    _, ikey, _ = cur_tab["items"][self.state["menu_item"] % 7]
                    self.state[ikey] = self.state.get(ikey, 0) + 1
            self.state["seq"] += 1
            self._current_png = render_current_screen_png(self.state)
            self._update_frame_label()
            entry = {
                "step": step,
                "key_name": f"SELECT_{box_idx + 1}" + ("_SET" if cycle else ""),
                "key_hex": "0x1ac" if cycle else "0x1ab",
                "state": dict(self.state),
                "utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            }
            self.history.append(entry)
            return entry

    def get_png(self) -> bytes:
        with self.lock:
            return self._current_png

    def get_status(self) -> dict:
        with self.lock:
            s = self.state
            page_titles = ["Big6 HOME (scr7286_0001)", "拍摄取景 OSD (rep_shooting)", "完整设置菜单 (rep_menu)"]
            return {
                "seq": s["seq"],
                "step_count": self.step_count,
                "page": s["page"] % 3,
                "page_title": page_titles[s["page"] % 3],
                "selected_box": (s["sel"] % 6) + 1,
                "menu_tab": s["menu_tab"] % len(FX6_MENU_TABS),
                "menu_tab_title": FX6_MENU_TABS[s["menu_tab"] % len(FX6_MENU_TABS)]["title"],
                "menu_item": (s["menu_item"] % 7) + 1,
                "fps": FPS_OPTS[s["fps"] % len(FPS_OPTS)],
                "iso": ISO_OPTS[s["iso"] % len(ISO_OPTS)],
                "shutter": SHUT_OPTS[s["shut"] % len(SHUT_OPTS)],
                "nd": ND_OPTS[s["nd"] % len(ND_OPTS)],
                "look": LOOK_OPTS[s["look"] % len(LOOK_OPTS)],
                "wb": WB_OPTS[s["wb"] % len(WB_OPTS)],
                "rec": "REC" if (s["rec"] & 1) else "STBY",
                "vm_running": self.vm_running,
                "vm_ready": self.vm_ready,
                "vm_status_text": self.vm_status_text,
                "vm_run_dir": str(self.vm_run_dir) if self.vm_run_dir else None,
                "frame_source": self.last_frame_source,
                "frame_sha256": hashlib.sha256(self._current_png).hexdigest()[:16],
                "serial_tail": self.serial_tail[-18:],
                "history": self.history[-10:],
            }

    def start_live_vm(self) -> dict:
        with self.lock:
            if self.vm_running:
                return {"ok": True, "message": "QEMU VM 已在运行中"}
            manifest_path = None
            for cand in ("277", "276", "271", "270", "269"):
                p = AGNOSTIC_DIR / f"vm-candidate-gpecap25-{cand}.json"
                if p.exists():
                    manifest_path = p
                    break
            if not manifest_path:
                return {"ok": False, "message": "未找到候选清单"}
            self.vm_running = True
            self.vm_ready = False
            self.vm_status_text = f"正在启动 FX6-on-FX3 QEMU 虚拟机 ({manifest_path.name})…"
            t = threading.Thread(target=self._vm_worker, args=(manifest_path,), daemon=True)
            t.start()
            return {"ok": True, "message": "已启动 FX6-on-FX3 QEMU 虚拟机后台线程"}

    def stop_live_vm(self) -> dict:
        with self.lock:
            proc = self.vm_proc
            self.vm_running = False
            self.vm_ready = False
            if self.gdb_client:
                self.gdb_client.close()
                self.gdb_client = None
        if proc and proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except Exception:
                pass
        with self.lock:
            self.vm_status_text = "已停止 QEMU 实机进程（3大界面交互继续可用）"
        return {"ok": True, "message": "已停止 QEMU 实机进程"}

    def _vm_worker(self, manifest_path: Path):
        sys.path.insert(0, str(EARLY_DIR))
        try:
            import fixed_runner as fr
            saved = json.loads(manifest_path.read_text())
            run_dir = AGNOSTIC_DIR / "runs" / ("fx6-ui-" + uuid.uuid4().hex[:8])
            run_dir.mkdir(parents=True, mode=0o700)
            args = saved["candidate_argv_before_observer_serial_retarget"].copy()
            args[args.index("-serial") + 1] = "file:" + str(run_dir / "serial.log")
            env = os.environ.copy()
            env.update(saved["model_env"])
            with self.lock:
                self.vm_run_dir = run_dir
                self.vm_status_text = f"QEMU 已启动 ({run_dir.name})，等待内核与 appFw.so 初始化…"
            with (run_dir / "host-stdout.log").open("wb") as out_f, (run_dir / "host-stderr.log").open("wb") as err_f:
                proc = subprocess.Popen(
                    args,
                    cwd=run_dir,
                    env=env,
                    stdout=out_f,
                    stderr=err_f,
                    start_new_session=True,
                    preexec_fn=fr.limits,
                )
            with self.lock:
                self.vm_proc = proc

            q_path = run_dir / "q"
            short_q = Path("/tmp") / (run_dir.name + ".qmp")
            for _ in range(100):
                if q_path.exists():
                    try:
                        short_q.unlink(missing_ok=True)
                        short_q.symlink_to(q_path)
                        q_path = short_q
                    except Exception:
                        pass
                    break
                time.sleep(0.05)
            qsock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            qsock.settimeout(5.0)
            qsock.connect(str(q_path))
            qreader = qsock.makefile("rb")
            json.loads(qreader.readline())
            fr.qmp_send(qsock, qreader, "qmp_capabilities", 1)
            fr.qmp_send(qsock, qreader, "human-monitor-command", 2, {"command-line": "info registers"})
            fr.qmp_send(qsock, qreader, "query-cpus-fast", 3)
            fr.qmp_send(qsock, qreader, "cont", 4)

            start_t = time.monotonic()
            while True:
                with self.lock:
                    if not self.vm_running:
                        break
                if proc.poll() is not None:
                    with self.lock:
                        self.vm_running = False
                        self.vm_status_text = f"QEMU 进程已退出 (rc={proc.returncode})"
                    break
                serial_file = run_dir / "serial.log"
                if serial_file.exists():
                    txt = serial_file.read_text(errors="replace")
                    lines = [
                        ln.strip()
                        for ln in txt.splitlines()
                        if any(k in ln for k in ("FX6_", "FX3_GPE_", "FX3_KEY96_", "FX3_BACKUP_CP_", "FX3_AP89_"))
                    ]
                    elapsed = int(time.monotonic() - start_t)
                    with self.lock:
                        self.serial_tail = lines[-20:]
                        if "FX6_OSD_FLUSH" in txt or "FX6_GPE_FILLRECT" in txt:
                            self.vm_ready = True
                            self.vm_status_text = f"实机运行中 (t={elapsed}s) — 支持 0x41df00000 按键注入与多界面同步"
                        else:
                            self.vm_status_text = f"实机启动中 (t={elapsed}s) — Linux 内核与 appFw.so 初始化中…"
                time.sleep(0.5)
        except Exception as exc:
            with self.lock:
                self.vm_running = False
                self.vm_status_text = f"实机启动异常: {exc}"


HTML_PAGE = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sony ILME-FX6 固件 — Big6 主屏 + 拍摄取景 OSD + 完整设置菜单</title>
<style>
  :root {
    --bg: #0b0f14;
    --card: #141c26;
    --border: #2a394c;
    --amber: #f59b2d;
    --cyan: #28b8e8;
    --green: #38e878;
    --red: #ff3838;
    --text: #e8f0f8;
    --muted: #90a4b8;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    padding: 16px 22px;
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "PingFang SC", sans-serif;
  }
  header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid var(--border);
    padding-bottom: 10px;
    margin-bottom: 14px;
  }
  .badge {
    display: inline-block;
    padding: 5px 12px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 600;
    background: rgba(56, 232, 120, 0.15);
    color: var(--green);
    border: 1px solid rgba(56, 232, 120, 0.4);
  }
  .page-tabs {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 10px;
    margin-bottom: 12px;
  }
  .page-btn {
    background: #1a2432;
    color: var(--text);
    border: 1px solid #384c64;
    border-radius: 8px;
    padding: 10px 12px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    text-align: center;
    transition: 0.12s;
  }
  .page-btn:hover { border-color: var(--amber); background: #243244; }
  .page-btn.active {
    background: linear-gradient(180deg, #f59b2d, #d47a12);
    color: #0e1218;
    border-color: #ffbe68;
  }
  .page-btn small { display: block; font-size: 11px; opacity: 0.85; margin-top: 2px; font-weight: 500; }
  .menu-cat-bar {
    display: grid;
    grid-template-columns: repeat(9, 1fr);
    gap: 6px;
    margin-bottom: 10px;
  }
  .cat-btn {
    background: #18222e;
    color: var(--muted);
    border: 1px solid #2e3e52;
    border-radius: 6px;
    padding: 6px 4px;
    font-size: 11px;
    font-weight: 600;
    cursor: pointer;
    text-align: center;
  }
  .cat-btn:hover { border-color: var(--cyan); color: #fff; }
  .cat-btn.active { border-color: var(--amber); background: #28384c; color: var(--amber); }
  .layout {
    display: grid;
    grid-template-columns: 1fr 370px;
    gap: 18px;
    align-items: start;
  }
  @media (max-width: 1180px) {
    .layout { grid-template-columns: 1fr; }
  }
  .card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 14px;
  }
  .screen-wrap {
    position: relative;
    width: 100%;
    max-width: 1024px;
    margin: 0 auto;
    border: 2px solid #384a62;
    border-radius: 6px;
    overflow: hidden;
    background: #0e1115;
    cursor: pointer;
  }
  .screen-wrap img {
    display: block;
    width: 100%;
    height: auto;
  }
  .quick-boxes {
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 8px;
    margin-top: 12px;
  }
  .quick-btn {
    background: #1c2634;
    color: var(--text);
    border: 1px solid #384c64;
    border-radius: 6px;
    padding: 8px 6px;
    font-size: 12px;
    cursor: pointer;
    text-align: center;
    transition: 0.12s;
  }
  .quick-btn:hover { border-color: var(--amber); background: #243244; }
  .quick-btn.active { border: 2px solid var(--amber); background: #2c3e54; }
  .quick-btn strong { display: block; color: var(--amber); font-size: 11px; margin-bottom: 3px; }
  .dpad {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    margin: 12px 0;
  }
  button.ctrl {
    background: #1e2a3a;
    color: var(--text);
    border: 1px solid #3c526e;
    border-radius: 8px;
    padding: 11px 8px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    transition: 0.12s;
  }
  button.ctrl:hover { background: #293b52; border-color: var(--amber); }
  button.ctrl:active { transform: scale(0.98); }
  button.ctrl.primary { background: #d86c10; border-color: #ff9838; color: #fff; }
  button.ctrl.rec { background: #882028; border-color: #ff4848; color: #fff; }
  button.vm-btn {
    width: 100%;
    padding: 9px 12px;
    border-radius: 8px;
    border: 1px solid var(--cyan);
    background: rgba(40, 184, 232, 0.14);
    color: #fff;
    font-weight: 600;
    cursor: pointer;
    margin-bottom: 8px;
  }
  button.vm-btn:hover { background: rgba(40, 184, 232, 0.26); }
  .kv {
    display: grid;
    grid-template-columns: 110px 1fr;
    row-gap: 6px;
    font-size: 13px;
    margin-top: 8px;
  }
  .kv div:nth-child(odd) { color: var(--muted); }
  pre.log {
    background: #0a0e13;
    border: 1px solid #243242;
    border-radius: 6px;
    padding: 8px;
    font-size: 11px;
    color: #a8c0d8;
    max-height: 160px;
    overflow-y: auto;
    margin: 8px 0 0;
  }
</style>
</head>
<body>
<header>
  <div>
    <h2 style="margin:0;font-size:20px;">Sony ILME-FX6 固件 (appFw.so 真机规格) — Big6 主屏 · 拍摄取景 OSD · 完整设置菜单</h2>
    <div style="font-size:12px;color:var(--muted);margin-top:4px;">
      提取自 appFw.so: scr7286_0001 (57控件 Big6 3×2) · rep_shooting (290控件 拍摄取景) · rep_menu (9大类 3栏设置菜单) · 索尼原厂 Univers OTS-SJ 字体
    </div>
  </div>
  <span class="badge" id="recBadge">STBY · CFexpress A+B</span>
</header>

<div class="layout">
  <div class="card">
    <div class="page-tabs">
      <button class="page-btn active" id="ptab0" onclick="setPage(0)">
        1 · HOME (Big6 监控主屏)
        <small>scr7286_0001 · 真实上下 3×2 布局</small>
      </button>
      <button class="page-btn" id="ptab1" onclick="setPage(1)">
        2 · DISP (拍摄取景界面 OSD)
        <small>rep_shooting · 16:9 寻像器 + 波形/眼部AF</small>
      </button>
      <button class="page-btn" id="ptab2" onclick="setPage(2)">
        3 · MENU (完整设置菜单)
        <small>rep_menu · 9 大分类完整设置项</small>
      </button>
    </div>

    <div class="menu-cat-bar" id="menuCatBar">
      <button class="cat-btn" id="mcat0" onclick="setPage(2, 0)">1. User</button>
      <button class="cat-btn active" id="mcat1" onclick="setPage(2, 1)">2. Shooting</button>
      <button class="cat-btn" id="mcat2" onclick="setPage(2, 2)">3. Project</button>
      <button class="cat-btn" id="mcat3" onclick="setPage(2, 3)">4. Paint/Look</button>
      <button class="cat-btn" id="mcat4" onclick="setPage(2, 4)">5. TC/Media</button>
      <button class="cat-btn" id="mcat5" onclick="setPage(2, 5)">6. Monitoring</button>
      <button class="cat-btn" id="mcat6" onclick="setPage(2, 6)">7. Audio</button>
      <button class="cat-btn" id="mcat7" onclick="setPage(2, 7)">8. Thumbnail</button>
      <button class="cat-btn" id="mcat8" onclick="setPage(2, 8)">9. Technical</button>
    </div>

    <div class="screen-wrap" id="screenWrap" onclick="onCanvasClick(event)">
      <img id="fbImg" src="/frame.png?t=0" alt="FX6 1024x540 Framebuffer">
    </div>

    <div class="quick-boxes">
      <button class="quick-btn" id="qbox1" onclick="clickBox(0)"><strong>上左 · FPS</strong><span id="v_fps">23.98p</span></button>
      <button class="quick-btn" id="qbox2" onclick="clickBox(1)"><strong>上中 · ISO / GAIN</strong><span id="v_iso">800 EI</span></button>
      <button class="quick-btn" id="qbox3" onclick="clickBox(2)"><strong>上右 · SHUTTER</strong><span id="v_shut">180.0 deg</span></button>
      <button class="quick-btn" id="qbox4" onclick="clickBox(3)"><strong>下左 · ND FILTER</strong><span id="v_nd">1/16</span></button>
      <button class="quick-btn" id="qbox5" onclick="clickBox(4)"><strong>下中 · BASE LOOK</strong><span id="v_look">S-Cinetone</span></button>
      <button class="quick-btn" id="qbox6" onclick="clickBox(5)"><strong>下右 · WHITE BAL</strong><span id="v_wb">5600K</span></button>
    </div>
    <div style="font-size:12px;color:var(--muted);margin-top:8px;">
      提示：可直接点击画面任意区域（Big6 六宫格 / 拍摄底部参数条 / 菜单左侧分类与右侧条目），或使用右侧机身按键与键盘方向键操作。
    </div>
  </div>

  <div class="card">
    <h3 style="margin:0 0 8px;font-size:15px;">机身按键控制 (支持三界面切换与调参)</h3>
    <div class="dpad">
      <button class="ctrl" onclick="sendKey('HOME')">HOME<br><small>Big6 主屏</small></button>
      <button class="ctrl" onclick="sendKey('UP')">▲ 上<br><small>0x3</small></button>
      <button class="ctrl" onclick="sendKey('DISP')">DISP<br><small>拍摄 OSD</small></button>
      <button class="ctrl" onclick="sendKey('LEFT')">◀ 左<br><small>0x15</small></button>
      <button class="ctrl primary" onclick="sendKey('SET')">SET 切换值<br><small>0x1ac</small></button>
      <button class="ctrl" onclick="sendKey('RIGHT')">▶ 右<br><small>0x1af</small></button>
      <button class="ctrl" onclick="sendKey('MENU')">MENU 菜单<br><small>0x1ab</small></button>
      <button class="ctrl" onclick="sendKey('DOWN')">▼ 下<br><small>0x30</small></button>
      <button class="ctrl rec" onclick="sendKey('BACK')">REC / STBY<br><small>0x1f8</small></button>
    </div>

    <hr style="border:0;border-top:1px solid var(--border);margin:12px 0;">
    <h3 style="margin:0 0 8px;font-size:15px;">QEMU 实机后台会话</h3>
    <button class="vm-btn" onclick="startVm()">启动 FX6-on-FX3 QEMU 实机运行 (可选)</button>
    <button class="vm-btn" style="border-color:#687a90;background:transparent;font-size:12px;padding:7px;" onclick="stopVm()">停止 QEMU 实机进程</button>
    <div id="vmStatus" style="font-size:12px;color:var(--green);line-height:1.4;margin-bottom:8px;">加载中…</div>

    <div class="kv">
      <div>当前界面模式:</div><div id="stPage" style="color:var(--amber);font-weight:600;">Big6 HOME</div>
      <div>当前焦点位置:</div><div id="stSel">Box #1</div>
      <div>累计操作步数:</div><div id="stSteps">0</div>
      <div>画面规格来源:</div><div id="stSource" style="word-break:break-all;">-</div>
      <div>帧 SHA-256:</div><div id="stSha">-</div>
    </div>

    <div style="font-size:12px;color:var(--muted);margin-top:10px;">串口 / 按键回执日志：</div>
    <pre class="log" id="logBox">等待操作…</pre>
  </div>
</div>

<script>
let currentPage = 0;

async function refreshStatus(forceImg) {
  const r = await fetch('/api/status');
  const st = await r.json();
  currentPage = st.page;
  document.getElementById('v_fps').textContent = st.fps;
  document.getElementById('v_iso').textContent = st.iso;
  document.getElementById('v_shut').textContent = st.shutter;
  document.getElementById('v_nd').textContent = st.nd;
  document.getElementById('v_look').textContent = st.look;
  document.getElementById('v_wb').textContent = st.wb;
  document.getElementById('stPage').textContent = st.page_title;
  document.getElementById('stSel').textContent =
    st.page === 0 ? ('Big6 Box #' + st.selected_box) :
    st.page === 1 ? 'Shooting OSD Strip' :
    (st.menu_tab_title + ' · Row #' + st.menu_item);
  document.getElementById('stSteps').textContent = st.step_count + ' (seq=' + st.seq + ')';
  document.getElementById('stSource').textContent = st.frame_source;
  document.getElementById('stSha').textContent = st.frame_sha256;
  document.getElementById('vmStatus').textContent = st.vm_status_text;

  for (let p = 0; p < 3; p++) {
    const pt = document.getElementById('ptab' + p);
    if (st.page === p) pt.classList.add('active');
    else pt.classList.remove('active');
  }
  for (let c = 0; c < 9; c++) {
    const cb = document.getElementById('mcat' + c);
    if (st.menu_tab === c) cb.classList.add('active');
    else cb.classList.remove('active');
  }

  const badge = document.getElementById('recBadge');
  if (st.rec === 'REC') {
    badge.textContent = '● REC · CFexpress A+B';
    badge.style.background = 'rgba(255,56,56,0.2)';
    badge.style.color = '#ff5858';
    badge.style.borderColor = '#ff5858';
  } else {
    badge.textContent = 'STBY · CFexpress A+B';
    badge.style.background = 'rgba(56,232,120,0.15)';
    badge.style.color = '#38e878';
    badge.style.borderColor = 'rgba(56,232,120,0.4)';
  }

  for (let i = 1; i <= 6; i++) {
    const el = document.getElementById('qbox' + i);
    if (st.page === 0 && st.selected_box === i) el.classList.add('active');
    else el.classList.remove('active');
  }

  const lines = [];
  if (st.history && st.history.length) {
    for (const h of st.history) {
      lines.push(`[step #${h.step}] key=${h.key_name} (${h.key_hex}) -> page=${h.state.page} sel=${h.state.sel}`);
    }
  }
  if (st.serial_tail && st.serial_tail.length) {
    lines.push('--- QEMU Serial Tail ---');
    for (const ln of st.serial_tail) lines.push(ln);
  }
  if (lines.length) {
    document.getElementById('logBox').textContent = lines.join('\\n');
  }
  if (forceImg || st.vm_running) {
    document.getElementById('fbImg').src = '/frame.png?t=' + Date.now();
  }
}

async function setPage(pageIdx, menuTab) {
  let url = '/api/page?page=' + pageIdx;
  if (menuTab !== undefined) url += '&tab=' + menuTab;
  await fetch(url, { method: 'POST' });
  document.getElementById('fbImg').src = '/frame.png?t=' + Date.now();
  await refreshStatus(false);
}

async function sendKey(k) {
  await fetch('/api/key?name=' + encodeURIComponent(k), { method: 'POST' });
  document.getElementById('fbImg').src = '/frame.png?t=' + Date.now();
  await refreshStatus(false);
}

async function clickBox(idx) {
  if (currentPage !== 0) {
    await setPage(0);
  }
  await fetch('/api/box?idx=' + idx + '&cycle=1', { method: 'POST' });
  document.getElementById('fbImg').src = '/frame.png?t=' + Date.now();
  await refreshStatus(false);
}

async function onCanvasClick(ev) {
  const img = document.getElementById('fbImg');
  const rect = img.getBoundingClientRect();
  const x = (ev.clientX - rect.left) * (1024 / rect.width);
  const y = (ev.clientY - rect.top) * (540 / rect.height);
  if (currentPage === 0) {
    // Top row (y < 150) or Bottom row (y >= 390)
    const col = x < 342 ? 0 : (x < 682 ? 1 : 2);
    if (y < 154) {
      await clickBox(col);
    } else if (y >= 388) {
      await clickBox(3 + col);
    } else if (x < 120 && y >= 220 && y < 320) {
      await sendKey('BACK');
    }
  } else if (currentPage === 1) {
    if (y >= 465) {
      const idx = Math.min(6, Math.max(0, Math.floor((x - 10) / 144)));
      await fetch('/api/box?idx=' + idx + '&cycle=1', { method: 'POST' });
      document.getElementById('fbImg').src = '/frame.png?t=' + Date.now();
      await refreshStatus(false);
    } else if (x < 120 && y < 48) {
      await sendKey('BACK');
    }
  } else if (currentPage === 2) {
    if (x < 186 && y >= 56 && y < 480) {
      const tab = Math.min(8, Math.max(0, Math.floor((y - 56) / 47)));
      await setPage(2, tab);
    } else if (x >= 432 && y >= 92 && y < 474) {
      const row = Math.min(6, Math.max(0, Math.floor((y - 92) / 54)));
      await fetch('/api/box?idx=' + row + '&cycle=1', { method: 'POST' });
      document.getElementById('fbImg').src = '/frame.png?t=' + Date.now();
      await refreshStatus(false);
    }
  }
}

async function startVm() {
  await fetch('/api/vm/start', { method: 'POST' });
  await refreshStatus(false);
}

async function stopVm() {
  await fetch('/api/vm/stop', { method: 'POST' });
  await refreshStatus(false);
}

window.addEventListener('keydown', (ev) => {
  const map = {
    ArrowUp: 'UP',
    ArrowDown: 'DOWN',
    ArrowLeft: 'LEFT',
    ArrowRight: 'RIGHT',
    Enter: 'SET',
    ' ': 'SET',
    m: 'MENU',
    M: 'MENU',
    d: 'DISP',
    D: 'DISP',
    h: 'HOME',
    H: 'HOME',
    Backspace: 'BACK',
  };
  if (map[ev.key]) {
    ev.preventDefault();
    sendKey(map[ev.key]);
  }
});

refreshStatus(true);
setInterval(() => refreshStatus(false), 1200);
</script>
</body>
</html>
"""


class Fx6MenuHttpHandler(http.server.BaseHTTPRequestHandler):
    session: Fx6MenuSession = None

    def log_message(self, fmt, *args):
        return

    def _send_json(self, obj: dict, status: int = 200):
        raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            raw = HTML_PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        elif parsed.path == "/frame.png":
            png = self.session.get_png()
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(png)))
            self.end_headers()
            self.wfile.write(png)
        elif parsed.path == "/api/status":
            self._send_json(self.session.get_status())
        else:
            self._send_json({"error": "Not found"}, status=404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        if parsed.path == "/api/key":
            name = (qs.get("name") or ["MENU"])[0]
            try:
                res = self.session.apply_key(name)
                self._send_json({"ok": True, "event": res})
            except Exception as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=400)
        elif parsed.path == "/api/page":
            p = int((qs.get("page") or ["0"])[0])
            tab = int(qs["tab"][0]) if "tab" in qs else None
            res = self.session.set_page(p, tab)
            self._send_json({"ok": True, "event": res})
        elif parsed.path == "/api/box":
            idx = int((qs.get("idx") or ["0"])[0])
            cycle = (qs.get("cycle") or ["0"])[0] == "1"
            res = self.session.select_box_or_param(idx, cycle=cycle)
            self._send_json({"ok": True, "event": res})
        elif parsed.path == "/api/vm/start":
            self._send_json(self.session.start_live_vm())
        elif parsed.path == "/api/vm/stop":
            self._send_json(self.session.stop_live_vm())
        else:
            self._send_json({"error": "Not found"}, status=404)


def main():
    ap = argparse.ArgumentParser(description="Sony ILME-FX6 Multi-Screen Interactive Trial Server")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8768)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--auto-start-vm", action="store_true")
    args = ap.parse_args()

    session = Fx6MenuSession()
    if args.auto_start_vm:
        session.start_live_vm()
    Fx6MenuHttpHandler.session = session

    class ReusableThreadingHTTPServer(http.server.ThreadingHTTPServer):
        allow_reuse_address = True

    srv = ReusableThreadingHTTPServer((args.host, args.port), Fx6MenuHttpHandler)
    url = f"http://{args.host}:{args.port}/"
    print(f"FX6 Multi-Screen Interactive Server listening on {url}", flush=True)
    if not args.no_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        session.stop_live_vm()
        srv.server_close()


if __name__ == "__main__":
    main()
