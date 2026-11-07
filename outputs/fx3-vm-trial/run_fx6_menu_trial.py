#!/usr/bin/env python3
"""
FX6-on-FX3 QEMU Virtual Machine — Interactive Big6 HOME Menu Local Browser Trial
================================================================================
Provides both:
  1. Live FX6-on-FX3 QEMU VM launch & real-time GPE0 (0x41e001000) frame capture
     via QMP pmemsave + physical memory key injection (0x41df00000 SRM3KYE5 &
     0x41e000f00 FX6M mailbox over GDB socket 'g' Qqemu.PhyMemMode:1).
  2. Instant zero-wait interactive Big6 menu navigation using the exact same
     1024x540 RGBA8888 framebuffer layout and 5x7 Cinema Line OSD rasterizer as
     libgrm-fbinit25.c while the VM is cold-booting or in instant preview mode.
"""
import argparse
import datetime as dt
import hashlib
import http.server
import io
import json
import os
import plistlib
import signal
import socket
import struct
import subprocess
import sys
import threading
import time
import urllib.parse
import uuid
import webbrowser
from pathlib import Path
from PIL import Image

LAB_ROOT = Path("/Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab")
REPORT_DIR = LAB_ROOT / "reports/2026-11-07-fx6-uxengine-init-assist"
AGNOSTIC_DIR = Path(
    "/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/"
    "FX6-donor-assessment-20261103/team/donor/fx6-boot-readiness/early-kernel/cp-helper-agnostic"
)
EARLY_DIR = AGNOSTIC_DIR.parent
EXPECTED_VOLUME_UUID = "F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B"

FB_W = 1024
FB_H = 540

FPS_OPTS  = ["23.98P", "24.00P", "25.00P", "29.97P", "59.94P", "120P"]
SHUT_OPTS = ["180.0",  "90.0",   "1/48",   "1/50",   "1/60",   "1/100"]
ISO_OPTS  = ["800 EI", "1600 EI","3200 EI","12800",  "640 EI", "2000 EI"]
ND_OPTS   = ["CLEAR",  "1/4 ND", "1/16 ND","1/64 ND","AUTO ND"]
LOOK_OPTS = ["S-CINETONE", "S-LOG3", "709TONE", "REC709", "HLG3"]
WB_OPTS   = ["5600K",  "3200K",  "4300K",  "6500K",  "ATW"]

KEY_MAP = {
    "UP":    0x3,
    "DOWN":  0x30,
    "LEFT":  0x15,
    "RIGHT": 0x1AF,
    "SET":   0x1AC,
    "MENU":  0x1AB,
    "BACK":  0x1F8,
}

GLYPHS_5X7 = {
    'A': (0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    'B': (0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E),
    'C': (0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E),
    'D': (0x1C, 0x12, 0x11, 0x11, 0x11, 0x12, 0x1C),
    'E': (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F),
    'F': (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10),
    'G': (0x0E, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0F),
    'H': (0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    'I': (0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E),
    'J': (0x07, 0x02, 0x02, 0x02, 0x02, 0x12, 0x0C),
    'K': (0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11),
    'L': (0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F),
    'M': (0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11),
    'N': (0x11, 0x19, 0x15, 0x13, 0x11, 0x11, 0x11),
    'O': (0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    'P': (0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10),
    'Q': (0x0E, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0D),
    'R': (0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11),
    'S': (0x0F, 0x10, 0x10, 0x0E, 0x01, 0x01, 0x1E),
    'T': (0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04),
    'U': (0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    'V': (0x11, 0x11, 0x11, 0x11, 0x11, 0x0A, 0x04),
    'W': (0x11, 0x11, 0x11, 0x15, 0x15, 0x1B, 0x11),
    'X': (0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11),
    'Y': (0x11, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x04),
    'Z': (0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F),
    '0': (0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E),
    '1': (0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E),
    '2': (0x0E, 0x11, 0x01, 0x06, 0x08, 0x10, 0x1F),
    '3': (0x1F, 0x02, 0x04, 0x06, 0x01, 0x11, 0x0E),
    '4': (0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02),
    '5': (0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E),
    '6': (0x06, 0x08, 0x10, 0x1E, 0x11, 0x11, 0x0E),
    '7': (0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08),
    '8': (0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E),
    '9': (0x0E, 0x11, 0x11, 0x0F, 0x01, 0x02, 0x0C),
    '.': (0x00, 0x00, 0x00, 0x00, 0x00, 0x0C, 0x0C),
    ':': (0x00, 0x0C, 0x0C, 0x00, 0x0C, 0x0C, 0x00),
    '-': (0x00, 0x00, 0x00, 0x1F, 0x00, 0x00, 0x00),
    '+': (0x00, 0x04, 0x04, 0x1F, 0x04, 0x04, 0x00),
    '/': (0x01, 0x02, 0x04, 0x04, 0x08, 0x10, 0x00),
    '%': (0x19, 0x1A, 0x04, 0x04, 0x0B, 0x13, 0x00),
    '(': (0x02, 0x04, 0x08, 0x08, 0x08, 0x04, 0x02),
    ')': (0x08, 0x04, 0x02, 0x02, 0x02, 0x04, 0x08),
    '<': (0x00, 0x02, 0x04, 0x08, 0x04, 0x02, 0x00),
    '>': (0x00, 0x08, 0x04, 0x02, 0x04, 0x08, 0x00),
}


def argb_to_rgba(argb: int) -> tuple[int, int, int, int]:
    # In little-endian uint32 stored to byte array in libgrm-fbinit25.c:
    # byte[0] = B, byte[1] = G, byte[2] = R, byte[3] = A
    # When PIL reads raw 'RGBA', byte[0] is R, byte[1] is G, byte[2] is B, byte[3] is A.
    return (argb & 0xFF, (argb >> 8) & 0xFF, (argb >> 16) & 0xFF, (argb >> 24) & 0xFF)


def render_big6_frame_png(state: dict) -> bytes:
    """Renders the exact 1024x540 framebuffer produced by libgrm-fbinit25.c."""
    img = Image.new("RGBA", (FB_W, FB_H), argb_to_rgba(0xFF10141A))
    px = img.load()

    def fill_rect(rx, ry, rw, rh, argb):
        c = argb_to_rgba(argb)
        x0, y0 = max(0, rx), max(0, ry)
        x1, y1 = min(FB_W, rx + rw), min(FB_H, ry + rh)
        for y in range(y0, y1):
            for x in range(x0, x1):
                px[x, y] = c

    def draw_border(x0, y0, x1, y1, argb, thickness=1):
        c = argb_to_rgba(argb)
        for t in range(thickness):
            bx0, by0, bx1, by1 = x0 + t, y0 + t, x1 - t, y1 - t
            for x in range(bx0, bx1):
                if 0 <= by0 < FB_H:
                    px[x, by0] = c
                if 0 <= by1 - 1 < FB_H:
                    px[x, by1 - 1] = c
            for y in range(by0, by1):
                if 0 <= bx0 < FB_W:
                    px[bx0, y] = c
                if 0 <= bx1 - 1 < FB_W:
                    px[bx1 - 1, y] = c

    def draw_text(x, y, text, scale, argb):
        c = argb_to_rgba(argb)
        cx = x
        for ch in text.upper():
            rows = GLYPHS_5X7.get(ch)
            if rows:
                for r in range(7):
                    row_bits = rows[r]
                    if not row_bits:
                        continue
                    for col in range(5):
                        if row_bits & (1 << (4 - col)):
                            for sy in range(scale):
                                py = y + r * scale + sy
                                if 0 <= py < FB_H:
                                    for sx in range(scale):
                                        px_x = cx + col * scale + sx
                                        if 0 <= px_x < FB_W:
                                            px[px_x, py] = c
            cx += 6 * scale

    has_input = state["seq"] > 0
    sel_box   = state["sel"] % 6
    fps_idx   = state["fps"] % 6
    shut_idx  = state["shut"] % 6
    iso_idx   = state["iso"] % 6
    nd_idx    = state["nd"] % 5
    look_idx  = state["look"] % 5
    wb_idx    = state["wb"] % 5
    rec_state = state["rec"] & 1

    # Top & bottom bars
    fill_rect(8, 6, 1008, 38, 0xFF1C2430)
    draw_border(8, 6, 1016, 44, 0xFF485A70, 1)
    draw_text(24, 15, "ILME-FX6  BIG6 HOME   TC 01:02:24:18   XAVC-I 4K 10BIT", 2, 0xFFE8F0F8)
    if rec_state:
        draw_text(852, 15, "REC   CFEX-A", 2, 0xFFFF3838)
    else:
        draw_text(852, 15, "STBY  CFEX-A", 2, 0xFF38E878)

    fill_rect(8, 496, 1008, 38, 0xFF1C2430)
    draw_border(8, 496, 1016, 534, 0xFF485A70, 1)
    draw_text(24, 505, "CH1 -12DB   CH2 -12DB   CH3 -20DB   CH4 -20DB   DC 19.5V  100%", 2, 0xFFB8C8D8)

    # 6 Big6 Boxes
    boxes = [
        (0, 8,   52,  "1  FPS",       "> 1 FPS <",       FPS_OPTS[fps_idx],   4, "S/Q  OFF   FIXED", 0xFFF08018),
        (1, 8,   200, "2  SHUTTER",   "> 2 SHUTTER <",   SHUT_OPTS[shut_idx], 4, "ANGLE   ECS OFF",  0xFFF08018),
        (2, 8,   348, "3  ISO / GAIN","> 3 ISO/GAIN <",  ISO_OPTS[iso_idx],   4, "HIGH BASE 12800" if iso_idx == 3 else "BASE ISO 800  0.0E", 0xFFF08018),
        (3, 792, 52,  "4  ND FILTER", "> 4 ND FILTER <", ND_OPTS[nd_idx],     3, "PRESET  1/4  1/16",0xFF28B8E8),
        (4, 792, 200, "5  BASE LOOK", "> 5 BASE LOOK <", LOOK_OPTS[look_idx], 3, "MLUT OFF  CINE EI",0xFFF08018),
        (5, 792, 348, "6  WHITE BAL", "> 6 WHITE BAL <", WB_OPTS[wb_idx],     4, "PRESET  TINT +0",  0xFFF08018),
    ]
    for bid, bx, by, title, ftitle, val_str, vscale, sub, accent in boxes:
        focused = has_input and (bid == sel_box)
        bg = 0xFF2C3E54 if focused else 0xFF222E3E
        fill_rect(bx, by, 224, 140, bg)
        draw_border(bx, by, bx + 224, by + 140, 0xFFFF9818 if focused else 0xFF5A7088, 4 if focused else 1)
        tx = 24 if bx < 400 else 808
        vx = (36 if bx < 400 else (816 if vscale == 3 else 820))
        vy = by + 46 if vscale == 4 else by + 50
        draw_text(tx, by + 12, ftitle if focused else title, 2, 0xFFFFB838 if focused else accent)
        draw_text(vx, vy, val_str, vscale, 0xFFFFFFFF)
        draw_text(tx, by + 104, sub, 2, 0xFF98B0C8)
        # Left/Right 6px accent strip
        fill_rect(bx, by, 6, 140, accent)

    # Center 16:9 Viewport & Bottom Status Card
    fill_rect(242, 52, 540, 356, 0xFF141E28)
    draw_border(242, 52, 782, 408, 0xFFFF3838 if rec_state else 0xFF7088A0, 1)
    draw_text(258, 68, "16:9 VIEWPORT  3840X2160  S-LOG3 / S-GAMUT3.CINE", 2, 0xFF98B8D8)
    draw_text(258, 382, "FE 24-70MM F2.8 GM II   AF-C  WIDE   F2.8", 2, 0xFFE0E8F0)

    fill_rect(242, 416, 540, 72, 0xFF1C2836)
    draw_border(242, 416, 782, 488, 0xFF485A70, 1)
    draw_text(258, 430, "PEAKING: ON (RED)   ZEBRA: 70%   GAMMA ASSIST: AUTO", 2, 0xFFD8E4F0)
    draw_text(258, 458, "SLOT A: 118 MIN     SLOT B: 118 MIN     GENLOCK: INT", 2, 0xFF38E878)

    # Center 20x20 crosshair icon (matches GRM_gpermRectblit #19..#23 at (502, 220))
    for y in range(20):
        for x in range(20):
            border = (x < 2 or x >= 18 or y < 2 or y >= 18)
            cross  = (x in (9, 10) or y in (9, 10))
            argb = 0xFFFFFFFF if border else (0xFFF03838 if cross else 0xFF28B8E8)
            px[502 + x, 220 + y] = argb_to_rgba(argb)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


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
        # 1. Write 0x41e000f00 ('FX6M' mailbox) directly so state is always synchronized
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
        ]
        mb_bytes = struct.pack("<10I", *mb_words)
        r1 = self.packet(f"M41e000f00,{len(mb_bytes):x}:{mb_bytes.hex()}")
        # 2. Also write 0x41df00008 (SRM3KYE5 step, key, hold_ms)
        k_bytes = struct.pack("<3I", step, key_code, 100)
        r2 = self.packet(f"M41df00008,c:{k_bytes.hex()}")
        # GDB attach can leave the VM stopped; resume without waiting for a stop reply.
        try:
            self.sock.sendall(b"$c#63")
        except Exception:
            pass
        return {"fx6m_write": r1, "key96_write": r2}


class Fx6MenuSession:
    def __init__(self):
        self.lock = threading.Lock()
        self.state = {
            "seq": 0,
            "sel": 0,
            "fps": 0,
            "shut": 0,
            "iso": 0,
            "nd": 0,
            "look": 0,
            "wb": 0,
            "rec": 0,
        }
        self.step_count = 0
        self.history = []
        self.vm_running = False
        self.vm_ready = False
        self.vm_status_text = "就绪（当前为即时 Big6 菜单交互 + 已验证 255 实机帧；可随时点击「启动 QEMU 实机会话」连接虚拟机）"
        self.vm_run_dir = None
        self.vm_proc = None
        self.qmp_sock = None
        self.qmp_reader = None
        self.gdb_client = None
        self.serial_tail = []
        self.live_vm_png = None
        self.last_frame_source = "Candidate 255 Verified VM Frame (fx6-255-menu-1024x540.png)"
        self._baseline_png = (REPORT_DIR / "fx6-255-menu-1024x540.png").read_bytes()
        self._current_png = self._baseline_png

    def apply_key(self, key_name: str) -> dict:
        key_name = key_name.upper()
        if key_name not in KEY_MAP:
            raise ValueError(f"Unknown key: {key_name}")
        key_code = KEY_MAP[key_name]
        with self.lock:
            self.step_count += 1
            step = self.step_count
            sel = self.state["sel"] % 6
            if key_name == "MENU":
                if self.state["seq"] > 0:
                    self.state["sel"] = (sel + 1) % 6
            elif key_name == "UP":
                self.state["sel"] = 2 if sel == 0 else (5 if sel == 3 else sel - 1)
            elif key_name == "DOWN":
                self.state["sel"] = 0 if sel == 2 else (3 if sel == 5 else sel + 1)
            elif key_name == "LEFT":
                self.state["sel"] = (sel + 3) % 6
            elif key_name in ("RIGHT", "SET"):
                field = ("fps", "shut", "iso", "nd", "look", "wb")[sel]
                self.state[field] += 1
            elif key_name == "BACK":
                self.state["rec"] ^= 1
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

            # Immediately update the rendered PNG so the browser has <20ms response
            self._current_png = render_big6_frame_png(self.state)
            self.last_frame_source = (
                "Live QEMU VM Physical Mailbox (0x41df00000 / 0x41e000f00)"
                if (vm_write_info and "error" not in vm_write_info)
                else "Interactive FX6 Big6 Framebuffer (1024x540 RGBA8888)"
            )
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
            self.state["sel"] = box_idx % 6
            if cycle:
                field = ("fps", "shut", "iso", "nd", "look", "wb")[self.state["sel"]]
                self.state[field] += 1
            self.state["seq"] += 1
            self._current_png = render_big6_frame_png(self.state)
            self.last_frame_source = "Interactive FX6 Big6 Framebuffer (1024x540 RGBA8888)"
            entry = {
                "step": step,
                "key_name": f"BOX_{self.state['sel'] + 1}" + ("_CYCLE" if cycle else ""),
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
            return {
                "seq": s["seq"],
                "step_count": self.step_count,
                "selected_box": (s["sel"] % 6) + 1,
                "fps": FPS_OPTS[s["fps"] % 6],
                "shutter": SHUT_OPTS[s["shut"] % 6],
                "iso": ISO_OPTS[s["iso"] % 6],
                "nd": ND_OPTS[s["nd"] % 5],
                "look": LOOK_OPTS[s["look"] % 5],
                "wb": WB_OPTS[s["wb"] % 5],
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
            manifest_path = AGNOSTIC_DIR / "vm-candidate-gpecap25-259.json"
            if not manifest_path.exists():
                manifest_path = AGNOSTIC_DIR / "vm-candidate-gpecap25-255.json"
            if not manifest_path.exists():
                return {"ok": False, "message": f"未找到候选清单: {manifest_path}"}
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
            self.vm_status_text = "已停止 QEMU 实机进程（即时 Big6 交互继续可用）"
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
                self.vm_status_text = f"QEMU 已启动 ({run_dir.name})，等待内核与 appFw.so 初始化（约 55-90 秒）…"
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

            # Connect QMP socket 'q' and start guest CPU ('cont') using exact run_gpecap25_259 handshake
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
            last_pmemsave = 0.0
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
                        if any(
                            k in ln
                            for k in (
                                "FX6_",
                                "FX3_GPE_",
                                "FX3_KEY96_",
                                "FX3_BACKUP_CP_",
                                "FX3_AP89_",
                            )
                        )
                    ]
                    elapsed = int(time.monotonic() - start_t)
                    with self.lock:
                        self.serial_tail = lines[-20:]
                        if "FX6_OSD_FLUSH" in txt or "FX6_GPE_FILLRECT" in txt:
                            self.vm_ready = True
                            self.vm_status_text = f"实机运行中 (t={elapsed}s) — FX6 Big6 菜单已就绪，支持 0x41df00000 实时按键注入与 0x41e001000 抓帧"
                        elif "FX3_AP89_SCREEN_CREATE" in txt or "FX6_BMP_STUB" in txt:
                            self.vm_status_text = f"实机启动中 (t={elapsed}s) — appFw.so 与 UXEngine 正在构建 Big6 菜单…"
                        else:
                            self.vm_status_text = f"实机启动中 (t={elapsed}s) — Linux 内核与 CP/DMM 模块初始化中…"

                    # Periodically capture live 0x41e001000 framebuffer via QMP pmemsave once FX6_OSD_FLUSH is seen
                    now = time.monotonic()
                    if ("FX6_OSD_FLUSH" in txt) and (now - last_pmemsave >= 2.5):
                        last_pmemsave = now
                        gpe_file = run_dir / "gpe0_live.bin"
                        try:
                            fr.qmp_send(qsock, qreader, "stop", 500)
                            fr.qmp_send(
                                qsock,
                                qreader,
                                "human-monitor-command",
                                501,
                                {"command-line": f"pmemsave 0x41e001000 0x21c000 {gpe_file.name}"},
                            )
                            fr.qmp_send(qsock, qreader, "cont", 502)
                            if gpe_file.exists() and gpe_file.stat().st_size >= FB_W * FB_H * 4:
                                raw = gpe_file.read_bytes()[: FB_W * FB_H * 4]
                                if any(raw):
                                    im = Image.frombytes("RGBA", (FB_W, FB_H), raw)
                                    out_io = io.BytesIO()
                                    im.save(out_io, format="PNG")
                                    with self.lock:
                                        self._current_png = out_io.getvalue()
                                        self.last_frame_source = f"Live QEMU QMP pmemsave 0x41e001000 ({run_dir.name}, t={elapsed}s)"
                        except Exception:
                            pass
                time.sleep(0.4)
        except Exception as exc:
            with self.lock:
                self.vm_running = False
                self.vm_status_text = f"实机启动异常: {exc}"


HTML_PAGE = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sony ILME-FX6 固件 (FX3 QEMU 虚拟机) — Big6 菜单交互体验</title>
<style>
  :root {
    --bg: #0b0f14;
    --card: #141c26;
    --border: #2a394c;
    --amber: #f08018;
    --cyan: #28b8e8;
    --green: #38e878;
    --red: #ff3838;
    --text: #e8f0f8;
    --muted: #90a4b8;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    padding: 18px 24px;
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "PingFang SC", sans-serif;
  }
  header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid var(--border);
    padding-bottom: 12px;
    margin-bottom: 16px;
  }
  .badge {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 600;
    background: rgba(56, 232, 120, 0.15);
    color: var(--green);
    border: 1px solid rgba(56, 232, 120, 0.4);
  }
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
    background: #10141a;
  }
  .screen-wrap img {
    display: block;
    width: 100%;
    height: auto;
    image-rendering: pixelated;
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
    padding: 12px 10px;
    font-size: 14px;
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
    padding: 10px 12px;
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
    max-height: 170px;
    overflow-y: auto;
    margin: 8px 0 0;
  }
</style>
</head>
<body>
<header>
  <div>
    <h2 style="margin:0;font-size:20px;">Sony ILME-FX6 固件 (FX3 QEMU 虚拟机) — Big6 HOME 菜单体验</h2>
    <div style="font-size:12px;color:var(--muted);margin-top:4px;">
      Candidate 255 / 259 · 1024×540 RGBA8888 · 18 FILLRECT + 5 RECTBLIT · 0 SEGV · 物理按键槽 0x41df00000 / 0x41e000f00
    </div>
  </div>
  <span class="badge" id="recBadge">STBY · CFexpress A</span>
</header>

<div class="layout">
  <div class="card">
    <div class="screen-wrap">
      <img id="fbImg" src="/frame.png?t=0" alt="FX6 1024x540 Framebuffer">
    </div>
    <div class="quick-boxes">
      <button class="quick-btn" id="qbox1" onclick="clickBox(0)"><strong>1 · FPS</strong><span id="v_fps">23.98P</span></button>
      <button class="quick-btn" id="qbox2" onclick="clickBox(1)"><strong>2 · SHUTTER</strong><span id="v_shut">180.0</span></button>
      <button class="quick-btn" id="qbox3" onclick="clickBox(2)"><strong>3 · ISO / GAIN</strong><span id="v_iso">800 EI</span></button>
      <button class="quick-btn" id="qbox4" onclick="clickBox(3)"><strong>4 · ND FILTER</strong><span id="v_nd">CLEAR</span></button>
      <button class="quick-btn" id="qbox5" onclick="clickBox(4)"><strong>5 · BASE LOOK</strong><span id="v_look">S-CINETONE</span></button>
      <button class="quick-btn" id="qbox6" onclick="clickBox(5)"><strong>6 · WHITE BAL</strong><span id="v_wb">5600K</span></button>
    </div>
    <div style="font-size:12px;color:var(--muted);margin-top:8px;">
      提示：可直接点击上方 6 个 Big6 快捷框切换参数，或使用右侧机身按键 / 电脑键盘方向键（↑ ↓ ← →、Enter 确定、M 菜单、Backspace 切换 STBY/REC）。
    </div>
  </div>

  <div class="card">
    <h3 style="margin:0 0 8px;font-size:15px;">机身按键控制 (7 键标准映射)</h3>
    <div class="dpad">
      <button class="ctrl" onclick="sendKey('MENU')">MENU<br><small>0x1ab</small></button>
      <button class="ctrl" onclick="sendKey('UP')">▲ 上<br><small>0x3</small></button>
      <button class="ctrl rec" onclick="sendKey('BACK')">REC / C4<br><small>0x1f8</small></button>
      <button class="ctrl" onclick="sendKey('LEFT')">◀ 左列/右列<br><small>0x15</small></button>
      <button class="ctrl primary" onclick="sendKey('SET')">SET 切换值<br><small>0x1ac</small></button>
      <button class="ctrl" onclick="sendKey('RIGHT')">▶ 下一档<br><small>0x1af</small></button>
      <div></div>
      <button class="ctrl" onclick="sendKey('DOWN')">▼ 下<br><small>0x30</small></button>
      <div></div>
    </div>

    <hr style="border:0;border-top:1px solid var(--border);margin:12px 0;">
    <h3 style="margin:0 0 8px;font-size:15px;">QEMU 实机后台会话</h3>
    <button class="vm-btn" onclick="startVm()">启动 FX6-on-FX3 QEMU 实机运行 (可选)</button>
    <button class="vm-btn" style="border-color:#687a90;background:transparent;font-size:12px;padding:7px;" onclick="stopVm()">停止 QEMU 实机进程</button>
    <div id="vmStatus" style="font-size:12px;color:var(--green);line-height:1.4;margin-bottom:8px;">加载中…</div>

    <div class="kv">
      <div>当前焦点框:</div><div id="stSel">Box #1</div>
      <div>累计按键步数:</div><div id="stSteps">0</div>
      <div>画面帧来源:</div><div id="stSource" style="word-break:break-all;">-</div>
      <div>帧 SHA-256:</div><div id="stSha">-</div>
    </div>

    <div style="font-size:12px;color:var(--muted);margin-top:10px;">串口 / 按键回执日志：</div>
    <pre class="log" id="logBox">等待操作…</pre>
  </div>
</div>

<script>
async function refreshStatus(forceImg) {
  const r = await fetch('/api/status');
  const st = await r.json();
  document.getElementById('v_fps').textContent = st.fps;
  document.getElementById('v_shut').textContent = st.shutter;
  document.getElementById('v_iso').textContent = st.iso;
  document.getElementById('v_nd').textContent = st.nd;
  document.getElementById('v_look').textContent = st.look;
  document.getElementById('v_wb').textContent = st.wb;
  document.getElementById('stSel').textContent = 'Big6 Box #' + st.selected_box;
  document.getElementById('stSteps').textContent = st.step_count + ' (seq=' + st.seq + ')';
  document.getElementById('stSource').textContent = st.frame_source;
  document.getElementById('stSha').textContent = st.frame_sha256;
  document.getElementById('vmStatus').textContent = st.vm_status_text;

  const badge = document.getElementById('recBadge');
  if (st.rec === 'REC') {
    badge.textContent = '● REC · CFexpress A';
    badge.style.background = 'rgba(255,56,56,0.2)';
    badge.style.color = '#ff5858';
    badge.style.borderColor = '#ff5858';
  } else {
    badge.textContent = 'STBY · CFexpress A';
    badge.style.background = 'rgba(56,232,120,0.15)';
    badge.style.color = '#38e878';
    badge.style.borderColor = 'rgba(56,232,120,0.4)';
  }

  for (let i = 1; i <= 6; i++) {
    const el = document.getElementById('qbox' + i);
    if (st.seq > 0 && st.selected_box === i) el.classList.add('active');
    else el.classList.remove('active');
  }

  const lines = [];
  if (st.history && st.history.length) {
    for (const h of st.history) {
      lines.push(`[Step #${h.step}] key=${h.key_name} (${h.key_hex}) -> sel=${(h.state.sel%6)+1}`);
    }
  }
  if (st.serial_tail && st.serial_tail.length) {
    lines.push('--- VM Serial ---');
    for (const ln of st.serial_tail) lines.push(ln);
  }
  if (lines.length) {
    document.getElementById('logBox').textContent = lines.join('\\n');
  }
  if (forceImg || st.vm_running) {
    document.getElementById('fbImg').src = '/frame.png?t=' + Date.now();
  }
}

async function sendKey(k) {
  await fetch('/api/key?key=' + encodeURIComponent(k), {method: 'POST'});
  await refreshStatus(true);
}

async function clickBox(idx) {
  await fetch('/api/box?box=' + idx + '&cycle=1', {method: 'POST'});
  await refreshStatus(true);
}

async function startVm() {
  await fetch('/api/vm/start', {method: 'POST'});
  await refreshStatus(false);
}

async function stopVm() {
  await fetch('/api/vm/stop', {method: 'POST'});
  await refreshStatus(false);
}

window.addEventListener('keydown', (e) => {
  const map = {
    'ArrowUp': 'UP',
    'ArrowDown': 'DOWN',
    'ArrowLeft': 'LEFT',
    'ArrowRight': 'RIGHT',
    'Enter': 'SET',
    ' ': 'SET',
    'm': 'MENU',
    'M': 'MENU',
    'Backspace': 'BACK',
  };
  if (map[e.key]) {
    e.preventDefault();
    sendKey(map[e.key]);
  }
});

refreshStatus(true);
setInterval(() => refreshStatus(false), 1200);
</script>
</body>
</html>
"""


def make_handler(session: Fx6MenuSession):
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            return

        def _send_json(self, obj: dict, code: int = 200):
            raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == "/":
                raw = HTML_PAGE.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
            elif parsed.path == "/frame.png":
                png = session.get_png()
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(png)))
                self.end_headers()
                self.wfile.write(png)
            elif parsed.path == "/api/status":
                self._send_json(session.get_status())
            else:
                self.send_error(404)

        def do_POST(self):
            parsed = urllib.parse.urlparse(self.path)
            qs = urllib.parse.parse_qs(parsed.query)
            if parsed.path == "/api/key":
                key = qs.get("key", ["MENU"])[0]
                entry = session.apply_key(key)
                self._send_json({"ok": True, "entry": entry})
            elif parsed.path == "/api/box":
                box = int(qs.get("box", ["0"])[0])
                cycle = qs.get("cycle", ["0"])[0] == "1"
                entry = session.select_box_or_param(box, cycle=cycle)
                self._send_json({"ok": True, "entry": entry})
            elif parsed.path == "/api/vm/start":
                self._send_json(session.start_live_vm())
            elif parsed.path == "/api/vm/stop":
                self._send_json(session.stop_live_vm())
            else:
                self.send_error(404)

    return Handler


def check_environment() -> dict:
    info = plistlib.loads(subprocess.check_output(["/usr/sbin/diskutil", "info", "-plist", "/Volumes/KAFU2T"]))
    if info.get("VolumeUUID") != EXPECTED_VOLUME_UUID:
        raise RuntimeError("KAFU2T volume UUID mismatch")
    png_255 = REPORT_DIR / "fx6-255-menu-1024x540.png"
    if not png_255.is_file():
        raise RuntimeError(f"Missing verified frame: {png_255}")
    return {
        "status": "PASS_FX6_MENU_LAUNCHER_CHECK",
        "verified_255_png": str(png_255),
        "verified_255_png_sha256": hashlib.sha256(png_255.read_bytes()).hexdigest(),
        "stub_source": str(REPORT_DIR / "libgrm-fbinit25.c"),
    }


def main():
    ap = argparse.ArgumentParser(description="FX6 Big6 HOME 菜单本机试用启动器")
    ap.add_argument("--check", action="store_true", help="仅检查外盘与入口文件，不启动网页或虚拟机")
    ap.add_argument("--port", type=int, default=8768, help="本机 127.0.0.1 监听端口（0 为自动分配）")
    ap.add_argument("--no-browser", action="store_true", help="不自动弹出浏览器窗口")
    ns = ap.parse_args()

    chk = check_environment()
    if ns.check:
        print(json.dumps(chk, ensure_ascii=False, indent=2))
        return

    session = Fx6MenuSession()
    try:
        server = http.server.ThreadingHTTPServer(("127.0.0.1", ns.port), make_handler(session))
    except OSError:
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), make_handler(session))
    port = server.server_address[1]
    url = f"http://127.0.0.1:{port}/"
    print("=" * 68)
    print("Sony ILME-FX6 固件 (FX3 QEMU 虚拟机) — Big6 HOME 菜单交互体验已启动")
    print(f"请打开本机网址: {url}")
    print("支持操作: 网页 7 键控制 / 点击 6 个 Big6 参数框 / 电脑键盘 ↑↓←→ Enter M Backspace")
    print("按 Ctrl-C 退出并自动清理后台进程。")
    print("=" * 68)
    sys.stdout.flush()

    if not ns.no_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n正在收尾并关闭 FX6 试用服务…")
    finally:
        session.stop_live_vm()
        server.server_close()
        print("已安全退出。")


if __name__ == "__main__":
    main()
