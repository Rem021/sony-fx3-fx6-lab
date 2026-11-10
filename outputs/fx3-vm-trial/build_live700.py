#!/usr/bin/env python3
"""Deterministic pure-stdlib builder for libgrm-fbinit25-live700.so and live700 CPIO.

Compiles outputs/fx3-vm-trial/src/*.c into libgrm-fbinit25-live700.so using the
AArch64 Zig 0.17.0 cross-toolchain, surgically updates usr/lib/libgrm-fbinit9.so
inside guest-hybrid-fx6kernel-capid-grmreal-live700.cpio (preserving all other
CPIO members and trailers byte-for-byte), and synchronizes SHA-256 / byte counts
in vm-candidate-gpecap25-live700.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import mmap
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
SRC_DIR = HERE / "src"
DEFAULT_ZIG = Path(
    os.environ.get(
        "FX6_ZIG",
        "/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/runtime/toolchains/zig-aarch64-macos-0.17.0/zig",
    )
)
SO_OUT = HERE / "libgrm-fbinit25-live700.so"
CPIO_PATH = HERE / "guest-hybrid-fx6kernel-capid-grmreal-live700.cpio"
MANIFEST_PATH = HERE / "vm-candidate-gpecap25-live700.json"
MEMBER_NAME = "usr/lib/libgrm-fbinit9.so"

SOURCES = [
    "libgrm-fbinit25-542.c",
    "fx6_next_stage_assist_log.c",
    "fx6_post_stub_393.c",
    "fx6_uosal_inject_early.c",
    "fx6_live_guest.c",
]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(4 * 1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def scan_newc_cpio(buf: mmap.mmap | bytes) -> list[dict]:
    """Scan SVR4 newc/crc CPIO archive (including concatenated archives)."""
    rows: list[dict] = []
    pos = 0
    total = len(buf)
    while pos + 110 <= total:
        magic = bytes(buf[pos : pos + 6])
        if magic not in (b"070701", b"070702"):
            # Skip NUL padding between concatenated CPIO archives if present
            if buf[pos] == 0:
                pos += 1
                continue
            raise ValueError(f"unexpected CPIO header magic {magic!r} at offset {pos:#x}")
        filesize = int(bytes(buf[pos + 54 : pos + 62]).decode("ascii"), 16)
        namesize = int(bytes(buf[pos + 94 : pos + 102]).decode("ascii"), 16)
        name_start = pos + 110
        name_end = name_start + namesize
        if name_end > total or buf[name_end - 1] != 0:
            raise ValueError(f"corrupt CPIO entry name at {pos:#x}")
        name = bytes(buf[name_start : name_end - 1]).decode("utf-8", errors="surrogateescape")
        data_offset = (name_end + 3) & ~3
        data_end = data_offset + filesize
        record_end = (data_end + 3) & ~3
        if record_end > total:
            raise ValueError(f"truncated CPIO member {name!r} at {pos:#x}")
        rows.append(
            {
                "header": pos,
                "offset": data_offset,
                "bytes": filesize,
                "end": record_end,
                "name": name,
            }
        )
        pos = record_end
    return rows


def compile_shim(zig: Path, out_so: Path) -> dict:
    if not zig.is_file():
        raise FileNotFoundError(f"Zig toolchain not found at {zig}")
    cache_root = Path("/private/tmp/fx6-live700-zig-cache")
    (cache_root / "local").mkdir(parents=True, exist_ok=True)
    (cache_root / "global").mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["ZIG_LOCAL_CACHE_DIR"] = str(cache_root / "local")
    env["ZIG_GLOBAL_CACHE_DIR"] = str(cache_root / "global")

    src_paths = [str(SRC_DIR / s) for s in SOURCES]
    tmp_so = out_so.with_name(f".{out_so.name}.{os.getpid()}.tmp")
    cmd = [
        str(zig),
        "cc",
        "-target",
        "aarch64-linux-gnu",
        "-shared",
        "-fPIC",
        "-nostdlib",
        "-fno-sanitize=all",
        "-fno-stack-protector",
        "-O2",
        "-Wall",
        "-Wextra",
        "-Wno-unused-parameter",
        "-Wno-unused-function",
        "-Wl,-soname,libgrm-fbinit9.so",
        f"-I{SRC_DIR}",
        *src_paths,
        "-o",
        str(tmp_so),
    ]
    res = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if res.returncode != 0:
        tmp_so.unlink(missing_ok=True)
        raise RuntimeError(f"zig cc failed ({res.returncode}):\n{res.stderr}")
    os.replace(tmp_so, out_so)
    data = out_so.read_bytes()
    return {
        "path": str(out_so),
        "bytes": len(data),
        "sha256": sha256_bytes(data),
        "stderr": res.stderr.strip(),
    }


def update_cpio_member(cpio_path: Path, member_name: str, payload: bytes) -> dict:
    if not cpio_path.is_file():
        raise FileNotFoundError(f"BYOF guest CPIO not found: {cpio_path}")
    tmp_cpio = cpio_path.with_name(f".{cpio_path.name}.{os.getpid()}.tmp")
    with cpio_path.open("rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as raw:
        rows = scan_newc_cpio(raw)
        matches = [r for r in rows if r["name"] == member_name]
        if len(matches) != 1:
            raise ValueError(f"expected exactly 1 {member_name!r} in CPIO, found {len(matches)}")
        with tmp_cpio.open("wb") as out:
            cursor = 0
            for r in rows:
                out.write(raw[cursor : r["header"]])
                if r["name"] == member_name:
                    hdr = bytearray(raw[r["header"] : r["header"] + 110])
                    hdr[54:62] = f"{len(payload):08x}".encode("ascii")
                    out.write(hdr)
                    out.write(raw[r["header"] + 110 : r["offset"]])
                    out.write(payload)
                    out.write(b"\x00" * (-len(payload) % 4))
                else:
                    out.write(raw[r["header"] : r["end"]])
                cursor = r["end"]
            out.write(raw[cursor:])

    # Verify rewritten CPIO integrity before atomic replace
    with tmp_cpio.open("rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as verify_raw:
        after_rows = scan_newc_cpio(verify_raw)
        if [r["name"] for r in after_rows] != [r["name"] for r in rows]:
            tmp_cpio.unlink(missing_ok=True)
            raise RuntimeError("CPIO member list changed unexpectedly")
        target = next(r for r in after_rows if r["name"] == member_name)
        if bytes(verify_raw[target["offset"] : target["offset"] + target["bytes"]]) != payload:
            tmp_cpio.unlink(missing_ok=True)
            raise RuntimeError("CPIO member readback mismatch")

    os.replace(tmp_cpio, cpio_path)
    size = cpio_path.stat().st_size
    digest = sha256_file(cpio_path)
    return {"path": str(cpio_path), "bytes": size, "sha256": digest, "members": len(rows)}


def sync_manifest(manifest_path: Path, shim_sha: str, cpio_info: dict) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["initrd"]["path"] = cpio_info["path"]
    manifest["initrd"]["sha256"] = cpio_info["sha256"]
    manifest["initrd"]["bytes"] = cpio_info["bytes"]
    manifest["initrd"]["size_bytes"] = cpio_info["bytes"]
    for change in manifest.get("firmware_payload_changes", []):
        if change.get("role") == "guest CPIO CP helper member":
            change["to_path"] = cpio_info["path"]
            change["to_sha256"] = cpio_info["sha256"]
    if "grm_fbinit" in manifest:
        manifest["grm_fbinit"]["member"] = f"{MEMBER_NAME} (content=libgrm-fbinit25-live700.so)"
        manifest["grm_fbinit"]["sha256"] = shim_sha
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Build libgrm-fbinit25-live700.so and update live700 CPIO + manifest.")
    ap.add_argument("--zig", type=Path, default=DEFAULT_ZIG)
    ap.add_argument("--compile-only", action="store_true", help="Only compile .so without modifying CPIO/manifest")
    args = ap.parse_args()

    shim = compile_shim(args.zig, SO_OUT)
    result: dict = {"status": "COMPILED_ONLY", "shim": shim}
    if not args.compile_only:
        if CPIO_PATH.is_file():
            cpio_info = update_cpio_member(CPIO_PATH, MEMBER_NAME, SO_OUT.read_bytes())
            sync_manifest(MANIFEST_PATH, shim["sha256"], cpio_info)
            result["status"] = "BUILT_AND_SYNCED"
            result["initrd"] = cpio_info
            result["manifest"] = str(MANIFEST_PATH)
        else:
            result["status"] = "COMPILED_NO_BYOF_CPIO"
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
