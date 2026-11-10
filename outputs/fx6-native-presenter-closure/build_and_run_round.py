#!/usr/bin/env python3
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import mmap
import os
import pathlib
import re
import shutil
import signal
import socket
import struct
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent

ZIG = pathlib.Path(
    "/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/"
    "menu-repair-01/runtime/toolchains/zig-aarch64-macos-0.17.0/zig"
)
QEMU_BIN = pathlib.Path(
    "/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/"
    "menu-repair-01/runtime/qemu-display-build/bin/qemu-gpio5-bf4d46481998b8fb"
)
PARENT_CPIO = (
    REPO / "work/fx6-worker-pool-restore-20261107/guest-worker-pool-restore295.cpio"
)
KERNEL_BIN = pathlib.Path(
    "/Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/"
    "stage47-runtime-provider-binding/official-files/nflasha3/vmlinux.bin"
)
GUEST_DTB = pathlib.Path(
    "/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/"
    "vm-optimization-20261103/runtime/try2-usability/"
    "vmopt-20261103-try2-long-media-gap-v2/guest.dtb"
)
DONOR_BK4_NTSC = pathlib.Path(
    "/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/"
    "FX6-donor-assessment-20261103/team/donor/tree/0110_backup/"
    "SYSIPSX-DSLR/CHAPLIN/CX95898_NTSC.bin"
)

FB_W = 1024
FB_H = 540
FB_BYTES = FB_W * FB_H * 4
GPE0_PHYS = 0x41E001000


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def scan_cpio(buf: mmap.mmap) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    pos = 0
    nonzero = re.compile(b"[^\x00]")
    n_len = len(buf)
    while pos + 110 <= n_len:
        if buf[pos] == 0:
            m = nonzero.search(buf, pos)
            if not m:
                break
            pos = m.start()
        if buf[pos : pos + 6] != b"070701":
            raise ValueError(f"Invalid newc header at {pos}")
        fields = [int(buf[pos + 6 + i * 8 : pos + 14 + i * 8], 16) for i in range(13)]
        nsize = fields[11]
        fsize = fields[6]
        name_raw = buf[pos + 110 : pos + 110 + nsize]
        if len(name_raw) != nsize or name_raw[-1:] != b"\x00":
            raise ValueError(f"Bad entry name at {pos}")
        name = name_raw[:-1].decode("utf-8", errors="replace")
        start = (pos + 110 + nsize + 3) & ~3
        end = (start + fsize + 3) & ~3
        if end > n_len:
            raise ValueError(f"Truncated CPIO payload for {name}")
        rows.append(
            {
                "name": name,
                "header": pos,
                "offset": start,
                "bytes": fsize,
                "end": end,
                "fields": fields,
            }
        )
        pos = end
    return rows


def build_binaries(
    build_dir: pathlib.Path,
    fx6_round: int,
    restore_infra70: int,
    restore_all_early: int,
    reply_all_200d: int,
    initial_setting_done: int = 0,
) -> Tuple[bytes, bytes, Dict[str, Any]]:
    cache_dir = build_dir / "zig-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["ZIG_LOCAL_CACHE_DIR"] = str(cache_dir / "local")
    env["ZIG_GLOBAL_CACHE_DIR"] = str(cache_dir / "global")

    launcher_out = build_dir / "appfw-launch"
    launcher_cmd = [
        str(ZIG),
        "cc",
        "-target",
        "aarch64-linux-gnu.2.17",
        "-std=gnu11",
        "-no-pie",
        "-fno-sanitize=all",
        "-fno-stack-protector",
        "-O2",
        "-g",
        f"-DFX6_ROUND={fx6_round}",
        str(HERE / "appfw-launch.c"),
        "-o",
        str(launcher_out),
    ]
    r_launch = subprocess.run(launcher_cmd, env=env, capture_output=True, text=True)
    if r_launch.returncode != 0:
        raise RuntimeError(f"Launcher compile failed:\n{r_launch.stderr}")

    shim_out = build_dir / "libgrm-fbinit9.so"
    shim_cmd = [
        str(ZIG),
        "cc",
        "-target",
        "aarch64-linux-gnu",
        "-shared",
        "-fPIC",
        "-nostdlib",
        "-fno-sanitize=all",
        "-fno-stack-protector",
        "-O0",
        "-g",
        f"-DFX6_ROUND={fx6_round}",
        f"-DFX6_RESTORE_INFRA70={restore_infra70}",
        f"-DFX6_RESTORE_ALL_EARLY={restore_all_early}",
        f"-DFX6_REPLY_ALL_200D={reply_all_200d}",
        f"-DFX6_INITIAL_SETTING_DONE={initial_setting_done}",
        "-Wl,-soname,libgrm-fbinit9.so",
        str(HERE / "libgrm-fbinit9.c"),
        "-o",
        str(shim_out),
    ]
    r_shim = subprocess.run(shim_cmd, env=env, capture_output=True, text=True)
    if r_shim.returncode != 0:
        raise RuntimeError(f"Shim compile failed:\n{r_shim.stderr}")

    launcher_bytes = launcher_out.read_bytes()
    shim_bytes = shim_out.read_bytes()
    meta = {
        "launcher_bytes": len(launcher_bytes),
        "launcher_sha256": sha256_bytes(launcher_bytes),
        "launcher_cmd": launcher_cmd,
        "shim_bytes": len(shim_bytes),
        "shim_sha256": sha256_bytes(shim_bytes),
        "shim_cmd": shim_cmd,
    }
    return launcher_bytes, shim_bytes, meta


def make_cpio_member(name: str, payload: bytes, ino: int = 0x999900) -> bytes:
    name_b = name.encode("utf-8") + b"\x00"
    hdr = (
        "070701"
        f"{ino:08x}"
        f"{0o100644:08x}"
        f"{0:08x}{0:08x}{1:08x}{0:08x}"
        f"{len(payload):08x}"
        f"{0:08x}{0:08x}{0:08x}{0:08x}"
        f"{len(name_b):08x}"
        f"{0:08x}"
    ).encode("ascii")
    out = bytearray(hdr) + name_b
    if len(out) % 4:
        out += b"\x00" * (4 - (len(out) % 4))
    out += payload
    if len(out) % 4:
        out += b"\x00" * (4 - (len(out) % 4))
    return bytes(out)


def patch_cpio(
    parent_cpio: pathlib.Path,
    out_cpio: pathlib.Path,
    replacements: Dict[str, bytes],
    additions: Optional[Dict[str, bytes]] = None,
) -> Dict[str, Any]:
    replaced_seen: List[str] = []
    added_seen: List[str] = []
    with parent_cpio.open("rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as raw:
        rows = scan_cpio(raw)
        with out_cpio.open("wb") as fo:
            cursor = 0
            for r in rows:
                fo.write(raw[cursor : r["header"]])
                name = r["name"]
                if name == "TRAILER!!!" and additions and not added_seen:
                    for idx, (add_name, add_payload) in enumerate(additions.items()):
                        fo.write(make_cpio_member(add_name, add_payload, 0x999900 + idx))
                        added_seen.append(add_name)
                if name in replacements:
                    payload = replacements[name]
                    header = bytearray(raw[r["header"] : r["header"] + 110])
                    header[54:62] = f"{len(payload):08x}".encode("ascii")
                    fo.write(header)
                    fo.write(raw[r["header"] + 110 : r["offset"]])
                    fo.write(payload)
                    pad = (-len(payload)) % 4
                    if pad:
                        fo.write(b"\x00" * pad)
                    replaced_seen.append(name)
                else:
                    fo.write(raw[r["header"] : r["end"]])
                cursor = r["end"]
            fo.write(raw[cursor:])
    return {
        "parent_cpio": str(parent_cpio),
        "out_cpio_bytes": out_cpio.stat().st_size,
        "replaced_members": replaced_seen,
        "added_members": added_seen,
    }


class QmpClient:
    def __init__(self, sock_path: pathlib.Path) -> None:
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(5.0)
        self.sock.connect(str(sock_path))
        self.buf = b""
        self._recv_json()  # banner
        self.cmd("qmp_capabilities")

    def _recv_json(self) -> Dict[str, Any]:
        while True:
            nl = self.buf.find(b"\n")
            if nl >= 0:
                line = self.buf[:nl].strip()
                self.buf = self.buf[nl + 1 :]
                if line:
                    obj = json.loads(line.decode("utf-8", errors="replace"))
                    if "event" in obj:
                        continue
                    return obj
            chunk = self.sock.recv(65536)
            if not chunk:
                raise EOFError("QMP connection closed")
            self.buf += chunk

    def cmd(self, execute: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        req: Dict[str, Any] = {"execute": execute}
        if arguments is not None:
            req["arguments"] = arguments
        self.sock.sendall((json.dumps(req) + "\n").encode("utf-8"))
        return self._recv_json()

    def close(self) -> None:
        try:
            self.sock.close()
        except Exception:
            pass


def analyze_gpe0_raw(raw_path: pathlib.Path) -> Dict[str, Any]:
    if not raw_path.exists():
        return {"present": False}
    data = raw_path.read_bytes()
    total_px = len(data) // 4
    nz_px = 0
    counter: collections.Counter[int] = collections.Counter()
    for (px,) in struct.iter_unpack("<I", data[: total_px * 4]):
        if px != 0:
            nz_px += 1
        counter[px] += 1
    top_colors = [
        {"argb": f"0x{c:08x}", "pixels": cnt}
        for c, cnt in counter.most_common(12)
    ]
    return {
        "present": True,
        "bytes": len(data),
        "total_pixels": total_px,
        "nonzero_pixels": nz_px,
        "unique_colors": len(counter),
        "sha256": sha256_bytes(data),
        "top_colors": top_colors,
    }


def extract_milestones(serial_text: str) -> Dict[str, Any]:
    important_prefixes = (
        "FX6_NATIVE_FAITHFUL_SHIM_LOADED",
        "FX6_MWF_",
        "FX6_IMCFG_",
        "FX6_INFRA_INPUT_",
        "FX6_BK4_",
        "FX6_BACKUP_READ8",
        "FX6_BACKUP_MEDIA",
        "FX6_BACKUP_NREAD_MULTI",
        "FX6_BACKUP_QUERY",
        "FX6_PATCH_",
        "FX6_APP_CONFIG_",
        "FX6_QUEUE_OBS_LIBRARY",
        "FX6_QUEUE_OBS_GOT",
        "FX6_QUEUE_OBS_ENTER",
        "FX6_QUEUE_OBS_EXIT",
        "FX6_UIPC_SND",
        "FX6_UIPC_SYNC_",
        "FX6_UIPC_COMPLETION_",
        "FX6_MILESTONE_",
        "FX6_SCREEN_MGR_STATE",
        "FX6_APPFW_MEDIA_SLOTS",
        "FX6_PRESENTER_SLOT",
        "FX6_TRIGGER_PUMP_",
        "FX6_UX_SCREEN_AREA",
        "FX6_UX_SCREEN_TREE",
        "FX6_GRM_",
        "FX6_BMP_",
        "FX6_FONT_",
        "FX6_GPE_",
        "FX6_OSD_FLUSH",
        "FX6_ABORT_",
        "APPFW_SEGV",
        "APPFW_PC_",
        "APPFW_LR_",
        "APPFW_FP_BT_",
        "APPFW_X",
        "FX6_WAIT_SNAPSHOT",
        "terminate called",
        "Assertion",
    )
    matched: List[str] = []
    counts: Dict[str, int] = collections.Counter()
    for raw_line in serial_text.splitlines():
        line = raw_line.strip("\r")
        for pfx in important_prefixes:
            if pfx in line:
                matched.append(line)
                counts[pfx] += 1
                break

    # Also summarize last seen thread snapshot from init's 3s loop
    tid_blocks = re.findall(
        r"FX6_QUEUE_OBS_TASK pid=(\d+) tid=(\d+)\n([^\n]+)\nFX6_QUEUE_OBS_COMM\n([^\n]*)\n"
        r"FX6_QUEUE_OBS_STATUS\n(.*?)FX6_QUEUE_OBS_WCHAN\n([^\n]*)",
        serial_text,
        flags=re.DOTALL,
    )
    latest_by_tid: Dict[str, Dict[str, str]] = {}
    for pid, tid, up, comm, status, wchan in tid_blocks:
        state_m = re.search(r"State:\s*([^\n]+)", status)
        latest_by_tid[tid] = {
            "tid": tid,
            "uptime": up.strip(),
            "comm": comm.strip(),
            "state": state_m.group(1).strip() if state_m else "",
            "wchan": wchan.strip(),
        }

    return {
        "prefix_counts": dict(counts),
        "total_threads_seen": len(latest_by_tid),
        "sample_threads": list(latest_by_tid.values())[:25],
        "matched_lines": matched,
    }


def run_once(args: argparse.Namespace) -> int:
    duration = min(max(int(args.duration), 15), 105)
    run_id = args.run_id
    run_dir = HERE / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    serial_log = run_dir / "serial.log"
    if serial_log.exists():
        serial_log.unlink()

    owner_pid = os.getpid()
    tmp_build = pathlib.Path(f"/private/tmp/fx6-native-closure-build-{owner_pid}-{run_id}")
    tmp_cpio = pathlib.Path(f"/private/tmp/fx6-native-closure-{owner_pid}-{run_id}.cpio")
    qmp_sock = pathlib.Path(f"/private/tmp/fx6-native-{owner_pid}-{run_id}-qmp.sock")
    gdb_sock = pathlib.Path(f"/private/tmp/fx6-native-{owner_pid}-{run_id}-gdb.sock")
    gpe_raw = pathlib.Path(f"/private/tmp/fx6-native-{owner_pid}-{run_id}-gpe0.raw")

    proc: Optional[subprocess.Popen[bytes]] = None
    qmp: Optional[QmpClient] = None
    t0 = time.monotonic()

    try:
        print(f"[{run_id}] Compiling launcher & shim (round={args.round})...", flush=True)
        launcher_bytes, shim_bytes, build_meta = build_binaries(
            tmp_build,
            fx6_round=args.round,
            restore_infra70=args.restore_infra70,
            restore_all_early=args.restore_all_early,
            reply_all_200d=args.reply_all_200d,
            initial_setting_done=args.initial_setting_done,
        )
        print(f"[{run_id}] Patching temporary CPIO -> {tmp_cpio}...", flush=True)
        additions: Optional[Dict[str, bytes]] = None
        if args.round >= 4 and DONOR_BK4_NTSC.exists():
            additions = {"etc/fx6_chaplin_ntsc.bk4": DONOR_BK4_NTSC.read_bytes()}
        cpio_meta = patch_cpio(
            PARENT_CPIO,
            tmp_cpio,
            {
                "usr/bin/appfw-launch": launcher_bytes,
                "usr/lib/libgrm-fbinit9.so": shim_bytes,
            },
            additions=additions,
        )

        qemu_env = os.environ.copy()
        qemu_env.update(
            {
                "FX3_VM_ESRAM_RAM": "1",
                "FX3_VM_HIGH_DDR": "1",
                "FX3_VM_SONY_TIMER": "1",
                "FX3_VM_SCU_REQUEST": "1",
                "FX3_VM_GPIO_BANK5": "1",
            }
        )
        qemu_argv = [
            str(QEMU_BIN),
            "-machine",
            "virt,gic-version=2,secure=off",
            "-accel",
            "tcg,thread=multi",
            "-cpu",
            "cortex-a35",
            "-smp",
            "4",
            "-m",
            "5120",
            "-display",
            "none",
            "-nodefaults",
            "-nic",
            "none",
            "-no-reboot",
            "-monitor",
            "none",
            "-serial",
            f"file:{serial_log}",
            "-qmp",
            f"unix:{qmp_sock},server=on,wait=off",
            "-chardev",
            f"socket,path={gdb_sock},server=on,wait=off,id=keygate93",
            "-gdb",
            "chardev:keygate93",
            "-S",
            "-kernel",
            str(KERNEL_BIN),
            "-device",
            f"loader,file={tmp_cpio},addr=0x440000000,force-raw=on",
            "-device",
            f"loader,file={GUEST_DTB},addr=0x400002000,force-raw=on",
        ]

        print(f"[{run_id}] Spawning isolated QEMU (budget={duration}s <= 120s)...", flush=True)
        proc = subprocess.Popen(
            qemu_argv,
            env=qemu_env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        print(f"[{run_id}] QEMU child pid={proc.pid}", flush=True)

        # Wait for QMP socket
        deadline_qmp = time.monotonic() + 15.0
        while time.monotonic() < deadline_qmp:
            if proc.poll() is not None:
                _, err_b = proc.communicate(timeout=2)
                raise RuntimeError(
                    f"QEMU exited early (rc={proc.returncode}): "
                    f"{err_b.decode('utf-8', 'replace')}"
                )
            if qmp_sock.exists():
                try:
                    qmp = QmpClient(qmp_sock)
                    break
                except Exception:
                    pass
            time.sleep(0.1)
        if qmp is None:
            raise RuntimeError("Timed out waiting for QMP socket")

        qmp.cmd("cont")
        vm_start = time.monotonic()

        while (time.monotonic() - vm_start) < duration:
            if proc.poll() is not None:
                print(f"[{run_id}] QEMU exited with code {proc.returncode}", flush=True)
                break
            if serial_log.exists():
                txt = serial_log.read_text(encoding="utf-8", errors="replace")
                if "APPFW_SEGV" in txt or "FX6_ABORT_BT" in txt:
                    # Wait 2s to flush remaining diagnostic output then stop early
                    time.sleep(2.0)
                    print(f"[{run_id}] Detected crash/abort signature; stopping early.", flush=True)
                    break
            time.sleep(1.0)

        gpe_stats: Dict[str, Any] = {"present": False}
        if qmp is not None and proc.poll() is None:
            try:
                qmp.cmd(
                    "pmemsave",
                    {
                        "val": GPE0_PHYS,
                        "size": FB_BYTES,
                        "filename": str(gpe_raw),
                    },
                )
                time.sleep(0.3)
                gpe_stats = analyze_gpe0_raw(gpe_raw)
            except Exception as exc:
                gpe_stats = {"present": False, "error": str(exc)}

        elapsed = round(time.monotonic() - t0, 2)
        serial_text = (
            serial_log.read_text(encoding="utf-8", errors="replace")
            if serial_log.exists()
            else ""
        )
        milestones = extract_milestones(serial_text)
        milestones_path = run_dir / "milestones.log"
        milestones_path.write_text(
            "\n".join(milestones["matched_lines"]) + "\n", encoding="utf-8"
        )

        summary = {
            "run_id": run_id,
            "round": args.round,
            "restore_infra70": args.restore_infra70,
            "restore_all_early": args.restore_all_early,
            "reply_all_200d": args.reply_all_200d,
            "initial_setting_done": args.initial_setting_done,
            "duration_budget_sec": duration,
            "wall_elapsed_sec": elapsed,
            "qemu_pid": proc.pid,
            "build": build_meta,
            "cpio": cpio_meta,
            "serial_bytes": len(serial_text.encode("utf-8", errors="replace")),
            "gpe0_readback": gpe_stats,
            "prefix_counts": milestones["prefix_counts"],
            "total_threads_seen": milestones["total_threads_seen"],
            "sample_threads": milestones["sample_threads"],
        }
        (run_dir / "summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
        )
        print(
            f"[{run_id}] Done in {elapsed}s | threads={milestones['total_threads_seen']} "
            f"| gpe0_nz={gpe_stats.get('nonzero_pixels')} unique_colors={gpe_stats.get('unique_colors')} "
            f"| counts={milestones['prefix_counts']}",
            flush=True,
        )
        return 0
    finally:
        if qmp is not None:
            try:
                qmp.cmd("quit")
            except Exception:
                pass
            qmp.close()
        if proc is not None and proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
                proc.wait(timeout=4.0)
            except Exception:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait(timeout=2.0)
                except Exception:
                    pass
        for p in (qmp_sock, gdb_sock, gpe_raw, tmp_cpio):
            try:
                if p.exists():
                    p.unlink()
            except Exception:
                pass
        if tmp_build.exists():
            shutil.rmtree(tmp_build, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--round", type=int, choices=[1, 2, 3, 4], required=True)
    ap.add_argument("--duration", type=int, default=55)
    ap.add_argument("--restore-infra70", type=int, choices=[0, 1], default=0)
    ap.add_argument("--restore-all-early", type=int, choices=[0, 1], default=0)
    ap.add_argument("--reply-all-200d", type=int, choices=[0, 1], default=0)
    ap.add_argument("--initial-setting-done", type=int, choices=[0, 1], default=0)
    args = ap.parse_args()
    return run_once(args)


if __name__ == "__main__":
    sys.exit(main())
