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
import io
import json
import os
import re
import socket
import struct
import subprocess
import threading
import time
import urllib.parse
import webbrowser
import zlib
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

REPO_ROOT = Path("/Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab")
TRIAL_DIR = REPO_ROOT / "outputs" / "fx3-vm-trial"
MANIFEST_PATH = TRIAL_DIR / "vm-candidate-gpecap25-live700.json"
FALLBACK_GPE0_PNG = REPO_ROOT / "reports" / "2026-11-08-fx6-native-text-gpe0" / "menu-677-big6-framed.png"

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
}

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

CELL_NAMES = ["FPS", "Shutter", "ISO/Gain", "ND Filter", "White Bal.", "Base Look"]
CELL_N_VALS = [3, 3, 3, 3, 3, 7]


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


def gpe0_raw_to_png(raw: bytes) -> tuple[bytes, int]:
    """Convert raw 1024x540x4 gpe0 physical memory dump to PNG using pure stdlib."""
    if len(raw) < GPE0_BYTES:
        return b"", 0
    u32 = struct.unpack(f"<{GPE0_W * GPE0_H}I", raw[:GPE0_BYTES])
    nz = sum(1 for v in u32 if v != 0)
    if nz == 0:
        return b"", 0
    row_stride = 1 + GPE0_W * 4
    scanlines = bytearray(row_stride * GPE0_H)
    for y in range(GPE0_H):
        row_base = y * row_stride
        scanlines[row_base] = 0  # filter type 0 (None)
        u32_base = y * GPE0_W
        for x in range(GPE0_W):
            v = u32[u32_base + x]
            o = row_base + 1 + x * 4
            if v:
                scanlines[o] = (v >> 16) & 0xFF
                scanlines[o + 1] = (v >> 8) & 0xFF
                scanlines[o + 2] = v & 0xFF
                scanlines[o + 3] = 255
            else:
                scanlines[o] = 14
                scanlines[o + 1] = 16
                scanlines[o + 2] = 20
                scanlines[o + 3] = 255
    ihdr = struct.pack(">IIBBBBB", GPE0_W, GPE0_H, 8, 6, 0, 0, 0)
    compressed = zlib.compress(bytes(scanlines), level=3)
    png = b"\x89PNG\r\n\x1a\n" + _png_chunk(b"IHDR", ihdr) + _png_chunk(b"IDAT", compressed) + _png_chunk(b"IEND", b"")
    return png, nz


class FX6LiveGpe0Session:
    def __init__(self, workdir: Path) -> None:
        self.workdir = workdir
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        self.gpe_lock = threading.Lock()
        self.cmd_lock = threading.Lock()
        self.proc: subprocess.Popen[bytes] | None = None
        self.serial_log = self.workdir / "serial.log"
        self.qemu_stderr = self.workdir / "qemu.stderr.log"
        self.qmp_sock = Path("/private/tmp") / f"fx6-live-qmp-{os.getpid()}.sock"
        self.gdb_sock = Path("/private/tmp") / f"fx6-live-gdb-{os.getpid()}.sock"
        self.qmp_conn: socket.socket | None = None
        self.gdb_conn: socket.socket | None = None
        self.gpe0_bin = self.workdir / "gpe0-live.bin"
        self.started_at: float | None = None

        # Shadow state matching guest 0x41e000e00 mailbox (mb[0..15])
        self.cmd_seq = 1
        self.ack_seq = 0
        self.page = 0
        self.sel_box = 5
        self.menu_cat = 2
        self.menu_item = 0
        self.menu_depth = 0
        self.cell_vals = [0, 0, 0, 0, 0, 0]
        self.rec_fmt_idx = 0
        self.last_nz = 0
        self.last_text_ok = 0
        self.last_fill_n = 0
        self.last_icon_n = 0
        self.last_png: bytes = FALLBACK_GPE0_PNG.read_bytes() if FALLBACK_GPE0_PNG.exists() else b""
        self.last_png_source = "real-gpe0-cached-677 (waiting for live VM boot)"
        self.live_ready = False

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
                else:
                    out_argv.append(argv[i])
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
            self.cmd_seq = 1
            self.ack_seq = 0
            self.page = 0
            self.sel_box = 5
            self.menu_cat = 2
            self.menu_item = 0
            self.menu_depth = 0
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
        for attr in ("qmp_conn", "gdb_conn"):
            conn = getattr(self, attr, None)
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
                setattr(self, attr, None)

    def _cleanup_sockets(self) -> None:
        self._close_connections()
        for p in (self.qmp_sock, self.gdb_sock):
            try:
                if p.exists():
                    p.unlink()
            except OSError:
                pass

    def _gdb_send_packet(self, sock: socket.socket, payload: bytes) -> bytes:
        chk = sum(payload) & 0xFF
        pkt = b"$" + payload + b"#" + f"{chk:02x}".encode("ascii")
        sock.sendall(pkt)
        buf = b""
        deadline = time.time() + 1.5
        while time.time() < deadline:
            try:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                buf += chunk
                if b"#" in buf:
                    sock.sendall(b"+")
                    break
            except socket.timeout:
                break
        return buf

    def _ensure_gdb(self) -> socket.socket | None:
        if self.gdb_conn is not None:
            return self.gdb_conn
        if not self.is_running() or not self.gdb_sock.exists():
            return None
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(1.5)
        s.connect(str(self.gdb_sock))
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

    def _write_ctrl_mailbox(self) -> bool:
        """Write mb[0..14] to guest physical 0x41e000e00 via persistent QEMU GDB stub."""
        if not self.is_running() or not self.gdb_sock.exists():
            return False
        words = [
            CTRL_MAGIC,
            self.cmd_seq,
            self.ack_seq,
            self.page,
            self.sel_box,
            self.menu_cat,
            self.menu_item,
            self.menu_depth,
            self.cell_vals[0],
            self.cell_vals[1],
            self.cell_vals[2],
            self.cell_vals[3],
            self.cell_vals[4],
            self.cell_vals[5],
            self.rec_fmt_idx,
        ]
        raw = struct.pack("<15I", *words)
        for _ in range(2):
            try:
                s = self._ensure_gdb()
                if s is None:
                    return False
                # If the GDB stub was in running state from a previous '$c#63', interrupt it first with 0x03
                try:
                    s.settimeout(0.05)
                    s.sendall(b"\x03")
                    while True:
                        chunk = s.recv(4096)
                        if not chunk:
                            break
                        if b"#" in chunk:
                            s.sendall(b"+")
                            break
                except socket.timeout:
                    pass
                s.settimeout(1.5)
                self._gdb_send_packet(s, b"Qqemu.PhyMemMode:1")
                # Write mb[3..14] first, then mb[0..2] so mb[1] (cmd_seq) commits last
                body_hex = raw[12:].hex().encode("ascii")
                r1 = self._gdb_send_packet(
                    s, f"M{CTRL_MB_PHYS + 12:x},{len(raw) - 12:x}:".encode("ascii") + body_hex
                )
                hdr_hex = raw[:12].hex().encode("ascii")
                r2 = self._gdb_send_packet(
                    s, f"M{CTRL_MB_PHYS:x},c:".encode("ascii") + hdr_hex
                )
                # Resume guest execution
                s.sendall(b"$c#63")
                try:
                    s.settimeout(0.1)
                    s.recv(64)
                except socket.timeout:
                    pass
                s.settimeout(1.5)
                if b"OK" in r1 and b"OK" in r2:
                    return True
            except Exception:
                if self.gdb_conn is not None:
                    try:
                        self.gdb_conn.close()
                    except Exception:
                        pass
                    self.gdb_conn = None
        return False

    def _wait_for_frame_seq(self, target_seq: int, timeout: float = 3.2) -> bool:
        deadline = time.time() + timeout
        pat = re.compile(
            rf"FX6_LIVE_(?:READY|FRAME) seq={target_seq} page=(\d+) sel=(\d+) cat=(\d+) item=(\d+) depth=(\d+) nz=(\d+) text_ok=(\d+) fill=(\d+) icon=(\d+)"
        )
        while time.time() < deadline:
            if self.serial_log.exists():
                tail = self.serial_log.read_bytes()[-131072:].decode("latin1", errors="replace")
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

    def capture_live_gpe0(self) -> tuple[bytes, int]:
        """Dump 0x41e001000 (0x21c000 bytes) via persistent QMP pmemsave and convert to PNG."""
        if not self.is_running() or not self.qmp_sock.exists():
            return self.last_png, self.last_nz
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
                            self.last_png = png
                            self.last_nz = nz
                            self.last_png_source = f"LIVE QEMU GPE0 @ 0x41e001000 (seq={self.ack_seq}, nz={nz})"
                            return png, nz
                    break
                except Exception:
                    if self.qmp_conn is not None:
                        try:
                            self.qmp_conn.close()
                        except Exception:
                            pass
                        self.qmp_conn = None
        return self.last_png, self.last_nz

    def apply_key_or_state(self, body: dict[str, Any]) -> dict[str, Any]:
        with self.cmd_lock:
            key = str(body.get("key", "")).upper().strip()

            if "page" in body:
                p_val = body["page"]
                if isinstance(p_val, str) and p_val.lower() in LEGACY_PAGE_MAP:
                    self.page = LEGACY_PAGE_MAP[p_val.lower()]
                else:
                    self.page = int(p_val) % 24
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
            elif any(k in body for k in ("page", "sel_box", "menu_cat", "menu_item", "menu_depth")):
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
                self.cell_vals[c] = (self.cell_vals[c] + 1) % CELL_N_VALS[c]
            elif self.page == 1:
                if self.menu_depth == 0:
                    self.menu_depth = 1
                    self.menu_item = 0
                elif self.menu_depth == 1:
                    if self.menu_cat == 3 and self.menu_item == 6:
                        self.page = 4
                        self.sel_box = 0
                    elif self.menu_cat == 4 and 1 <= self.menu_item <= 6:
                        self.cell_vals[5] = self.menu_item - 1
                    else:
                        self.menu_depth = 2
                        self.menu_item = 0
                else:
                    if self.menu_cat == 3:
                        self.rec_fmt_idx = self.menu_item % 5
                    else:
                        self.cell_vals[5] = self.menu_item % 7
                    self.menu_depth = 1
        elif kcode == 6:  # BACK
            if self.page == 1 and self.menu_depth > 0:
                self.menu_depth -= 1
                self.menu_item = 0
            else:
                self.page = 0
        elif kcode == 7:  # MENU
            if self.page == 1:
                self.page = 0
            else:
                self.page = 1
                self.menu_depth = 0
        elif kcode == 8:  # HOME
            self.page = 0
        elif kcode == 9:  # DISP
            disp_cycle = [6, 1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 0]
            self.page = disp_cycle[self.page % 12]

        self.cmd_seq += 1

    def get_status(self) -> dict[str, Any]:
        running = self.is_running()
        elapsed = round(time.time() - self.started_at, 1) if (running and self.started_at) else 0.0
        serial_tail = ""
        stage = "STOPPED"
        if self.serial_log.exists():
            raw = self.serial_log.read_bytes()
            serial_window = raw[-524288:].decode("latin1", errors="replace")
            if self.live_ready or "FX6_LIVE_READY" in serial_window or "FX6_LIVE_FRAME" in serial_window:
                if not self.live_ready:
                    self.live_ready = True
                    matches = re.findall(
                        r"FX6_LIVE_(?:READY|FRAME) seq=(\d+) page=(\d+) sel=(\d+) cat=(\d+) item=(\d+) depth=(\d+) nz=(\d+) text_ok=(\d+) fill=(\d+) icon=(\d+)",
                        serial_window,
                    )
                    if matches:
                        last = matches[-1]
                        self.ack_seq = int(last[0])
                        self.last_nz = int(last[6])
                        self.last_text_ok = int(last[7])
                        self.last_fill_n = int(last[8])
                        self.last_icon_n = int(last[9])
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

        return {
            "running": running,
            "pid": self.proc.pid if running and self.proc else None,
            "elapsed_sec": elapsed,
            "stage": stage,
            "live_ready": self.live_ready,
            "cmd_seq": self.cmd_seq,
            "ack_seq": self.ack_seq,
            "page": self.page,
            "page_name": PAGE_NAMES.get(self.page, f"Page {self.page}"),
            "sel_box": self.sel_box,
            "sel_cell_name": CELL_NAMES[self.sel_box % 6],
            "menu_cat": self.menu_cat,
            "menu_cat_name": CAT_NAMES[self.menu_cat % 11],
            "menu_item": self.menu_item,
            "menu_depth": self.menu_depth,
            "cell_vals": self.cell_vals,
            "gpe0_nonzero_px": self.last_nz,
            "text_ok": self.last_text_ok,
            "fill_n": self.last_fill_n,
            "icon_n": self.last_icon_n,
            "png_source": self.last_png_source,
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
  <div style="display:flex;gap:8px;">
    <button onclick="refreshGpe0()">刷新 GPE0 显存帧</button>
    <button onclick="restartVm()" style="background:#7f1d1d;border-color:#ef4444;">重启 QEMU 虚拟机</button>
  </div>
</header>

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
        <span>GPE0 非零像素: <b id="st-nz">-</b></span>
        <span>TextRM 文本贴图: <b id="st-text">-</b></span>
        <span>Fill/Icon: <b id="st-fill">-</b></span>
        <span>Mailbox 序号: <b id="st-seq">-</b></span>
        <span>来源: <b id="st-src">-</b></span>
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
      <h3>QEMU 虚拟机串口实时日志 (FX6_LIVE_READY / FX6_LIVE_FRAME)</h3>
      <div id="serial-box" class="serial-box">正在连接虚拟机串口...</div>
    </div>
  </div>
</div>

<script>
let busy = false;
let currentStatus = null;

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
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
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
  };
  if (map[e.key]) {
    e.preventDefault();
    sendKey(map[e.key]);
  }
});

setInterval(pollStatus, 1500);
pollStatus();
</script>
</body>
</html>
"""


def make_handler(session: FX6LiveGpe0Session):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:
            pass

        def _send_json(self, obj: Any, status: int = 200) -> None:
            raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self) -> None:
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            if path in ("/", "/index.html"):
                raw = HTML_UI.encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(raw)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(raw)
                return
            if path == "/api/status":
                self._send_json(session.get_status())
                return
            if path in ("/api/frame.png", "/api/gpe0.png", "/frame.png"):
                png, _ = session.capture_live_gpe0() if session.live_ready else (session.last_png, session.last_nz)
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(png)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(png)
                return
            self.send_error(HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            qs = urllib.parse.parse_qs(parsed.query)

            length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(length) if length > 0 else b"{}"
            try:
                body = json.loads(raw_body.decode("utf-8")) if raw_body else {}
            except Exception:
                body = {}

            # Support legacy query parameters from older browser tabs
            if "name" in qs and "key" not in body:
                body["key"] = qs["name"][0]
            if "key" in qs and "key" not in body:
                body["key"] = qs["key"][0]
            if "page" in qs and "page" not in body:
                body["page"] = qs["page"][0]
            if "idx" in qs and "sel_box" not in body:
                body["sel_box"] = int(qs["idx"][0])

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
            if path in ("/api/key", "/api/page", "/api/box"):
                res = session.apply_key_or_state(body)
                self._send_json(res)
                return
            self.send_error(HTTPStatus.NOT_FOUND)

    return Handler


def main() -> int:
    parser = argparse.ArgumentParser(description="Sony FX6 Authentic In-Guest GPE0 Menu Runner")
    parser.add_argument("--port", type=int, default=8768)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--check", action="store_true", help="Verify manifest and payload paths without starting VM")
    args = parser.parse_args()

    if args.check:
        if not MANIFEST_PATH.exists():
            raise SystemExit(f"Missing manifest: {MANIFEST_PATH}")
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        for key in ("kernel", "initrd", "dtb", "backup"):
            p = Path(manifest[key]["path"])
            if not p.exists():
                raise SystemExit(f"Missing {key}: {p}")
        print(json.dumps({"ok": True, "manifest": str(MANIFEST_PATH), "initrd": manifest["initrd"]["path"]}, ensure_ascii=False))
        return 0

    workdir = TRIAL_DIR / "live-gpe0-run"
    session = FX6LiveGpe0Session(workdir)

    print("[FX6-LIVE-GPE0] Auto-starting FX3 QEMU VM with FX6 native UI controller (live700)...")
    start_info = session.start_vm()
    print(f"[FX6-LIVE-GPE0] QEMU started: {start_info}")

    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(session))
    url = f"http://127.0.0.1:{args.port}/"
    print(f"[FX6-LIVE-GPE0] Listening on {url}")

    if not args.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        session.stop_vm()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
