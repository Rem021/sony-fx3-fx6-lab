#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
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
import types
import zlib
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
HOME_AI_MAC = pathlib.Path.home() / "AI-Workspace" / "AI" / "Projects" / "Mac"
HOME_AI_LAB = HOME_AI_MAC / "outputs" / "sony-fx3-fx6-lab"
LEGACY_MAC = pathlib.Path("/Volumes/KAFU2T/AI/Projects/Mac")


def _resolve_migrated_path(
    env_var: str,
    rel_subpath: str,
    legacy_abs: Optional[str] = None,
    *,
    prefer_repo: bool = False,
) -> pathlib.Path:
    override = os.environ.get(env_var, "").strip()
    if override:
        return pathlib.Path(override)
    candidates: List[pathlib.Path] = []
    if prefer_repo:
        candidates.append(REPO / rel_subpath)
    candidates.extend(
        [
            HOME_AI_MAC / rel_subpath,
            HOME_AI_LAB / rel_subpath,
        ]
    )
    if not prefer_repo:
        candidates.append(REPO / rel_subpath)
    if legacy_abs:
        candidates.append(pathlib.Path(legacy_abs))
    for cand in candidates:
        if cand.exists():
            return cand
    return candidates[0]


ZIG = _resolve_migrated_path(
    "FX6_ZIG",
    "work/fx3-vm-20261101/menu-repair-01/runtime/toolchains/zig-aarch64-macos-0.17.0/zig",
    "/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/runtime/toolchains/zig-aarch64-macos-0.17.0/zig",
)
QEMU_BIN = _resolve_migrated_path(
    "FX6_QEMU_BIN",
    "work/fx3-vm-20261101/menu-repair-01/runtime/qemu-display-build/bin/qemu-gpio5-bf4d46481998b8fb",
    "/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/runtime/qemu-display-build/bin/qemu-gpio5-bf4d46481998b8fb",
)
PARENT_CPIO = _resolve_migrated_path(
    "FX6_PARENT_CPIO",
    "work/fx6-worker-pool-restore-20261107/guest-worker-pool-restore295.cpio",
    "/Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/work/fx6-worker-pool-restore-20261107/guest-worker-pool-restore295.cpio",
    prefer_repo=True,
)
KERNEL_BIN = _resolve_migrated_path(
    "FX3_KERNEL_BIN",
    "work/sony-firmware-20261024/stage47-runtime-provider-binding/official-files/nflasha3/vmlinux.bin",
    "/Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage47-runtime-provider-binding/official-files/nflasha3/vmlinux.bin",
)
GUEST_DTB = _resolve_migrated_path(
    "FX3_GUEST_DTB",
    "work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/vmopt-20261103-try2-long-media-gap-v2/guest.dtb",
    "/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/vmopt-20261103-try2-long-media-gap-v2/guest.dtb",
)
DONOR_BK4_NTSC = _resolve_migrated_path(
    "FX6_DONOR_BK4_NTSC",
    "work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0110_backup/SYSIPSX-DSLR/CHAPLIN/CX95898_NTSC.bin",
    "/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0110_backup/SYSIPSX-DSLR/CHAPLIN/CX95898_NTSC.bin",
)
FX3_UPM_KO = _resolve_migrated_path(
    "FX3_UPM_KO",
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/original-modules/upm.ko",
    "/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/original-modules/upm.ko",
)
FX3_SEED_BK4 = _resolve_migrated_path(
    "FX3_SEED_BK4",
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin",
    "/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin",
)
DONOR_IMAGE_00_169_UXC = _resolve_migrated_path(
    "FX6_DONOR_IMAGE_00_169_UXC",
    "work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/image_00_169.uxc",
)
DONOR_STRING_SCHINESE_UXC = _resolve_migrated_path(
    "FX6_DONOR_STRING_SCHINESE_UXC",
    "work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_simplifiedchinese.uxc",
)
DONOR_STRING_SCHINESE_2_UXC = _resolve_migrated_path(
    "FX6_DONOR_STRING_SCHINESE_2_UXC",
    "work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_simplifiedchinese_2.uxc",
)
DONOR_FONT_SCHINESE_LTT = _resolve_migrated_path(
    "FX6_DONOR_FONT_SCHINESE_LTT",
    "work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/MYingHeiC-GB18030-SJ_wIcon.ltt",
)
DONOR_STRING_TCHINESE_UXC = _resolve_migrated_path(
    "FX6_DONOR_STRING_TCHINESE_UXC",
    "work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_traditionalchinese.uxc",
)
DONOR_STRING_TCHINESE_2_UXC = _resolve_migrated_path(
    "FX6_DONOR_STRING_TCHINESE_2_UXC",
    "work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_traditionalchinese_2.uxc",
)
DONOR_FONT_TCHINESE_LTT = _resolve_migrated_path(
    "FX6_DONOR_FONT_TCHINESE_LTT",
    "work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/MYingHeiC-Big5HKSCS-SJ_wIcon.ltt",
)
DONOR_STRING_JAPANESE_UXC = _resolve_migrated_path(
    "FX6_DONOR_STRING_JAPANESE_UXC",
    "work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_japanese.uxc",
)
DONOR_STRING_JAPANESE_2_UXC = _resolve_migrated_path(
    "FX6_DONOR_STRING_JAPANESE_2_UXC",
    "work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_japanese_2.uxc",
)
DONOR_FONT_JAPANESE_LTT = _resolve_migrated_path(
    "FX6_DONOR_FONT_JAPANESE_LTT",
    "work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/HeiseiKakuGothW5-SJ_wIcon.ltt",
)
DONOR_STRING_ENGLISH_UXC = _resolve_migrated_path(
    "FX6_DONOR_STRING_ENGLISH_UXC",
    "work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english.uxc",
)
DONOR_STRING_ENGLISH_2_UXC = _resolve_migrated_path(
    "FX6_DONOR_STRING_ENGLISH_2_UXC",
    "work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english_2.uxc",
)
DONOR_FONT_ENGLISH_LTT = _resolve_migrated_path(
    "FX6_DONOR_FONT_ENGLISH_LTT",
    "work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/UniversOTS-SJ_wIcon.ltt",
)
LANG_CODE_MAP: Dict[str, int] = {
    "en": 0,
    "english": 0,
    "japanese": 1,
    "tchinese": 2,
    "schinese": 3,
}
DEFAULT_ASSETS_DIR = REPO / "reports/2026-11-10-fx6-native-presenter-closure/assets"

FB_W = 1024
FB_H = 540
FB_BYTES = FB_W * FB_H * 4
GPE0_PHYS = 0x41E001000


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_bytes_readonly(path: pathlib.Path) -> bytes:
    """Read a donor/input file strictly with os.O_RDONLY."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        st = os.fstat(fd)
        chunks: List[bytes] = []
        remaining = st.st_size
        while remaining > 0:
            chunk = os.read(fd, min(remaining, 4 * 1024 * 1024))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)
    finally:
        os.close(fd)


def parse_key_seq(spec: str) -> List[Tuple[int, int, int]]:
    out: List[Tuple[int, int, int]] = []
    if not spec or not spec.strip():
        return out
    for raw_item in spec.split(","):
        item = raw_item.strip()
        if not item:
            continue
        parts = item.split(":")
        if len(parts) != 3:
            raise ValueError(f"Invalid key-seq step '{item}'; expected key:hold_ms:gap_ms")
        key_id = int(parts[0], 0)
        hold_ms = max(int(parts[1], 0), 20)
        gap_ms = max(int(parts[2], 0), 20)
        out.append((key_id, hold_ms, gap_ms))
    return out


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
    shooting_mode_cine_ei: int = 0,
    key_seq: str = "",
    key_settle_ms: int = 1500,
    lang: str = "en",
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
        "-DFX6_NATIVE_FAITHFUL=1",
        f"-DFX6_ROUND={fx6_round}",
        str(HERE / "appfw-launch.c"),
        "-o",
        str(launcher_out),
    ]
    r_launch = subprocess.run(launcher_cmd, env=env, capture_output=True, text=True)
    if r_launch.returncode != 0:
        raise RuntimeError(f"Launcher compile failed:\n{r_launch.stderr}")

    steps = parse_key_seq(key_seq)
    key_flags: List[str] = [f"-DFX6_KEY_SETTLE_MS={max(int(key_settle_ms), 100)}U"]
    if steps:
        ids_c = "{" + ",".join(f"0x{k:x}U" for k, _, _ in steps) + "}"
        holds_c = "{" + ",".join(f"{h}U" for _, h, _ in steps) + "}"
        gaps_c = "{" + ",".join(f"{g}U" for _, _, g in steps) + "}"
        key_flags.extend(
            [
                f"-DFX6_KEY_COUNT={len(steps)}",
                f"-DFX6_KEY_IDS={ids_c}",
                f"-DFX6_KEY_HOLDS={holds_c}",
                f"-DFX6_KEY_GAPS={gaps_c}",
            ]
        )

    lang_schinese = 1 if lang == "schinese" else 0
    lang_code = LANG_CODE_MAP.get(lang, 0)
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
        "-DFX6_NATIVE_FAITHFUL=1",
        f"-DFX6_ROUND={fx6_round}",
        f"-DFX6_RESTORE_INFRA70={restore_infra70}",
        f"-DFX6_RESTORE_ALL_EARLY={restore_all_early}",
        f"-DFX6_REPLY_ALL_200D={reply_all_200d}",
        f"-DFX6_INITIAL_SETTING_DONE={initial_setting_done}",
        f"-DFX6_SHOOTING_MODE_CINE_EI={shooting_mode_cine_ei}",
        f"-DFX6_LANG_SCHINESE={lang_schinese}",
        f"-DFX6_LANG_CODE={lang_code}",
        *key_flags,
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
        "lang": lang,
        "lang_code": lang_code,
        "launcher_bytes": len(launcher_bytes),
        "launcher_sha256": sha256_bytes(launcher_bytes),
        "launcher_cmd": launcher_cmd,
        "shim_bytes": len(shim_bytes),
        "shim_sha256": sha256_bytes(shim_bytes),
        "shim_cmd": shim_cmd,
        "key_steps": [
            {"key": f"0x{k:04x}", "hold_ms": h, "gap_ms": g} for k, h, g in steps
        ],
    }
    return launcher_bytes, shim_bytes, meta


def make_cpio_member(
    name: str,
    payload: bytes,
    ino: int = 0x999900,
    mode: int = 0o100644,
) -> bytes:
    name_b = name.encode("utf-8") + b"\x00"
    hdr = (
        "070701"
        f"{ino:08x}"
        f"{mode:08x}"
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
    additions: Optional[Dict[str, Union[bytes, Tuple[bytes, int]]]] = None,
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
                    for idx, (add_name, add_val) in enumerate(additions.items()):
                        if isinstance(add_val, tuple):
                            add_payload, add_mode = add_val
                        else:
                            add_payload, add_mode = add_val, 0o100644
                        fo.write(
                            make_cpio_member(
                                add_name,
                                add_payload,
                                0x999900 + idx,
                                mode=add_mode,
                            )
                        )
                        added_seen.append(add_name)
                if name in replacements:
                    payload = replacements[name]
                    header = bytearray(raw[r["header"] : r["header"] + 110])
                    if int(header[14:22].decode("ascii"), 16) == 0:
                        header[14:22] = f"{0o100755:08x}".encode("ascii")
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


def _import_stage_a_modules() -> Tuple[Any, Any, Any]:
    """Read-only import of pure-stdlib Stage-A builders without triggering unicorn."""
    fx3_safety_dir = str(REPO / "outputs" / "fx3-safety")
    if fx3_safety_dir not in sys.path:
        sys.path.insert(0, fx3_safety_dir)
    closure_pkg_dir = REPO / "outputs" / "fx6-on-fx3-closure" / "fx6_closure"
    if "fx6_closure" not in sys.modules:
        pkg = types.ModuleType("fx6_closure")
        pkg.__path__ = [str(closure_pkg_dir)]
        sys.modules["fx6_closure"] = pkg
    from fx6_closure import backup_mount_tolerance_verifier, patcher, vfat_builder

    return patcher, vfat_builder, backup_mount_tolerance_verifier


def _extract_cpio_members(parent_cpio: pathlib.Path, names: Tuple[str, ...]) -> Dict[str, bytes]:
    wanted = set(names)
    found: Dict[str, bytes] = {}
    with parent_cpio.open("rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as raw:
        for r in scan_cpio(raw):
            nm = r["name"]
            if nm in wanted:
                found[nm] = raw[r["offset"] : r["offset"] + r["bytes"]]
    missing = sorted(wanted - set(found.keys()))
    if missing:
        raise FileNotFoundError(f"Missing members in {parent_cpio}: {missing}")
    return found


def _load_p10_keymap_spec(patcher_mod: Any) -> Any:
    """Read-only load of P10_APPFW_KEYMAP_SPEC without importing unicorn."""
    verifier_path = (
        REPO
        / "outputs"
        / "fx6-on-fx3-closure"
        / "fx6_closure"
        / "peripheral_ux_compatibility_verifier.py"
    )
    src = verifier_path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(verifier_path))
    rhs_node: Optional[ast.expr] = None
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign):
            for tgt in stmt.targets:
                if isinstance(tgt, ast.Name) and tgt.id == "P10_APPFW_KEYMAP_SPEC":
                    rhs_node = stmt.value
                    break
        elif isinstance(stmt, ast.AnnAssign):
            if (
                isinstance(stmt.target, ast.Name)
                and stmt.target.id == "P10_APPFW_KEYMAP_SPEC"
                and stmt.value is not None
            ):
                rhs_node = stmt.value
        if rhs_node is not None:
            break
    if rhs_node is None:
        raise RuntimeError(f"P10_APPFW_KEYMAP_SPEC not found in {verifier_path}")
    expr = ast.Expression(rhs_node)
    ast.fix_missing_locations(expr)
    spec = eval(
        compile(expr, str(verifier_path), "eval"),
        {"__builtins__": {}},
        {
            "LibraryPatchSpec": patcher_mod.LibraryPatchSpec,
            "PatchSiteSpec": patcher_mod.PatchSiteSpec,
            "PF_R": patcher_mod.PF_R,
            "struct": struct,
            "bytes": bytes,
        },
    )
    if spec.spec_id != "P10_FX3_TO_FX6_KEYMAP_ADAPTER" or len(spec.sites) != 6:
        raise RuntimeError(f"Unexpected P10_APPFW_KEYMAP_SPEC: {spec.spec_id} sites={len(spec.sites)}")
    return spec


def _load_p12_wlan_spec(patcher_mod: Any) -> Any:
    """Read-only AST load of P12_WLAN_FATAL_GUARD_SPEC without importing unicorn."""
    verifier_path = (
        REPO
        / "outputs"
        / "fx6-on-fx3-closure"
        / "fx6_closure"
        / "wireless_fault_isolation_verifier.py"
    )
    src = verifier_path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(verifier_path))
    consts: Dict[str, Any] = {}
    rhs_node: Optional[ast.expr] = None
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
            tgt = stmt.targets[0]
            if isinstance(tgt, ast.Name):
                if tgt.id in ("FX6_WLAN_RSRC_SHA256", "FX6_WLAN_RSRC_HANDLE_FATAL_VMA"):
                    consts[tgt.id] = ast.literal_eval(stmt.value)
                elif tgt.id == "P12_WLAN_FATAL_GUARD_SPEC":
                    rhs_node = stmt.value
                    break
        elif isinstance(stmt, ast.AnnAssign):
            if (
                isinstance(stmt.target, ast.Name)
                and stmt.target.id == "P12_WLAN_FATAL_GUARD_SPEC"
                and stmt.value is not None
            ):
                rhs_node = stmt.value
                break
    if rhs_node is None:
        raise RuntimeError(f"P12_WLAN_FATAL_GUARD_SPEC not found in {verifier_path}")
    expr = ast.Expression(rhs_node)
    ast.fix_missing_locations(expr)
    spec = eval(
        compile(expr, str(verifier_path), "eval"),
        {"__builtins__": {}},
        {
            "LibraryPatchSpec": patcher_mod.LibraryPatchSpec,
            "PatchSiteSpec": patcher_mod.PatchSiteSpec,
            "PF_R": getattr(patcher_mod, "PF_R", 4),
            "PF_X": getattr(patcher_mod, "PF_X", 1),
            "_pack_insns": lambda *words: b"".join(struct.pack("<I", w) for w in words),
            "struct": struct,
            "bytes": bytes,
            **consts,
        },
    )
    if spec.spec_id != "P12_libWlanResource_fatal_guard" or len(spec.sites) != 1:
        raise RuntimeError(f"Unexpected P12_WLAN_FATAL_GUARD_SPEC: {spec.spec_id} sites={len(spec.sites)}")
    return spec


FX3_SECTOR0_PARTITIONS: Tuple[Tuple[int, int, int, int], ...] = (
    (0x00000080, 0x0000BF80, 0x00000005, 0xFFFFFFFF),  # p1: SYSTEM (Updater)
    (0x0000C000, 0x0000A000, 0x00000005, 0xFFFFFFFF),  # p2: SYSTEM (Setting)
    (0x00016000, 0x00025800, 0x00000005, 0xFFFFFFFF),  # p3: SYSTEM (Main)
    (0x0003B800, 0x00006000, 0x00000004, 0xFFFFFFFF),  # p4: MPR Flash Backup
    (0x00041800, 0x00096000, 0x00000006, 0xFFFFFFFF),  # p5: Warm Boot Image
    (0x000D7800, 0x0000C800, 0x00000005, 0xFFFFFFFF),  # p6: Jiritsu
    (0x000E4000, 0x00008000, 0x00000004, 0xFFFFFFFF),  # p7: Rootfs
    (0x000EC000, 0x00020000, 0x00000005, 0xFFFFFFFF),  # p8: CP Data
    (0x0010C000, 0x00000000, 0x00000004, 0x00000000),  # p9: reserved
    (0x0010C000, 0x00006000, 0x00000005, 0xFFFFFFFF),  # p10: Work
    (0x00112000, 0x000FA000, 0x00000005, 0xFFFFFFFF),  # p11: Log
    (0x0020C000, 0x00014000, 0x00000005, 0xFFFFFFFF),  # p12: Network
    (0x00220000, 0x00002000, 0x00000005, 0xFFFFFFFF),  # p13: UpdaterWork
    (0x00222000, 0x00000000, 0x00000004, 0x00000000),  # p14: reserved
    (0x00222000, 0x000FA000, 0x00000004, 0xFFFFFFFF),  # p15: usr
    (0x0031C000, 0x00000000, 0x00000004, 0x00000000),  # p16: reserved
    (0x0031C000, 0x00000000, 0x00000004, 0x00000000),  # p17: reserved
    (0x0031C000, 0x0000A000, 0x00000005, 0xFFFFFFFF),  # p18: LensData
    (0x00326000, 0x00000000, 0x00000004, 0x00000000),  # p19: reserved
    (0x00326000, 0x00000000, 0x00000004, 0x00000000),  # p20: reserved (FX3=0)
    (0x00326000, 0x00000000, 0x00000004, 0x00000000),  # p21: reserved (FX3=0)
    (0x00326000, 0x00000000, 0x00000004, 0x00000000),  # p22: reserved
    (0x00326000, 0x00020000, 0x00000005, 0xFFFFFFFF),  # p23: PMBP
    (0x00346000, 0x00000000, 0x00000004, 0x00000000),  # p24: Storage
    (0x00346000, 0x00000000, 0x00000004, 0x00000000),  # p25: BGM(MP3)
    (0x00346000, 0x00000000, 0x00000004, 0x00000000),  # p26: BGM(AC3)
    (0x00346000, 0x00000000, 0x00000004, 0x00000000),  # p27: reserved
    (0x00346000, 0x00000000, 0x00000004, 0x00000000),  # p28: reserved
    (0x00346000, 0x00000000, 0x00000004, 0x00000000),  # p29: reserved
    (0x00346000, 0x00018000, 0x00000005, 0xFFFFFFFF),  # p30: LutData (48 MiB)
)


def build_fx3_sector0_table() -> bytes:
    """Assemble the canonical 512-byte Sony FX3 7.02 Sector-0 partition table ('8246'/'2.00', n=30)."""
    out = bytearray(512)
    out[0:4] = b"8246"
    out[4:8] = b"2.00"
    struct.pack_into("<I", out, 8, len(FX3_SECTOR0_PARTITIONS))
    for idx, (start_sec, size_sec, ptype, flag) in enumerate(FX3_SECTOR0_PARTITIONS):
        struct.pack_into("<IIII", out, 0x20 + idx * 16, start_sec, size_sec, ptype, flag)
    return bytes(out)


FX3_HARDENED_LIBJIT_C = r"""
#define SYS_unlinkat 35L
#define SYS_openat   56L
#define SYS_close    57L
#define SYS_read     63L
#define SYS_write    64L
#define AT_FDCWD     (-100L)
#define O_RDONLY     0L
#define O_WRONLY     1L
#define O_CREAT      0100L
#define O_EXCL       0200L
#define O_NOFOLLOW   0100000L

static long sc6(long n, long a, long b, long c, long d, long e, long f) {
    register long x8 asm("x8") = n;
    register long x0 asm("x0") = a;
    register long x1 asm("x1") = b;
    register long x2 asm("x2") = c;
    register long x3 asm("x3") = d;
    register long x4 asm("x4") = e;
    register long x5 asm("x5") = f;
    asm volatile("svc #0"
                 : "+r"(x0)
                 : "r"(x8), "r"(x1), "r"(x2), "r"(x3), "r"(x4), "r"(x5)
                 : "memory");
    return x0;
}

__attribute__((constructor)) static void fx3_jit_sector0_probe(void) {
    /* 1. Immediately self-delete so /tmp/jiritsu/libJit.so never lingers on p6/tmpfs. */
    (void)sc6(SYS_unlinkat, AT_FDCWD, (long)"/tmp/jiritsu/libJit.so", 0, 0, 0, 0);

    /* 2. Open /dev/pnflasha0 strictly read-only without following symlinks. */
    long fd = sc6(SYS_openat, AT_FDCWD, (long)"/dev/pnflasha0", O_RDONLY | O_NOFOLLOW, 0, 0, 0);
    if (fd < 0) return;

    unsigned char sec0[512];
    long total = 0;
    while (total < 512) {
        long n = sc6(SYS_read, fd, (long)(sec0 + total), 512 - total, 0, 0, 0);
        if (n == -4L) continue; /* EINTR */
        if (n <= 0) break;
        total += n;
    }
    sc6(SYS_close, fd, 0, 0, 0, 0, 0);

    /* 3. Verify exact 512B read and Sony PTBL header without truncating on error. */
    if (total != 512) return;
    if (sec0[0] != '8' || sec0[1] != '2' || sec0[2] != '4' || sec0[3] != '6') return;
    if (sec0[4] != '2' || sec0[5] != '.' || sec0[6] != '0' || sec0[7] != '0') return;
    unsigned int nparts = (unsigned int)sec0[8] |
                          ((unsigned int)sec0[9] << 8) |
                          ((unsigned int)sec0[10] << 16) |
                          ((unsigned int)sec0[11] << 24);
    if (nparts != 30U) return;

    /* 4. IEEE CRC32 over the 512B Sector-0 table. */
    unsigned int crc = 0xFFFFFFFFU;
    for (int i = 0; i < 512; i++) {
        crc ^= (unsigned int)sec0[i];
        for (int b = 0; b < 8; b++) {
            crc = (crc & 1U) ? ((crc >> 1) ^ 0xEDB88320U) : (crc >> 1);
        }
    }
    crc ^= 0xFFFFFFFFU;

    /* 5. Assemble 528B packet: [8B "FX3S0OK\0" + u32 len=512 + u32 crc32 + 512B sector0]. */
    unsigned char pkt[528];
    pkt[0] = 'F'; pkt[1] = 'X'; pkt[2] = '3'; pkt[3] = 'S';
    pkt[4] = '0'; pkt[5] = 'O'; pkt[6] = 'K'; pkt[7] = '\0';
    pkt[8] = 0x00; pkt[9] = 0x02; pkt[10] = 0x00; pkt[11] = 0x00;
    pkt[12] = (unsigned char)(crc & 0xFFU);
    pkt[13] = (unsigned char)((crc >> 8) & 0xFFU);
    pkt[14] = (unsigned char)((crc >> 16) & 0xFFU);
    pkt[15] = (unsigned char)((crc >> 24) & 0xFFU);
    for (int i = 0; i < 512; i++) pkt[16 + i] = sec0[i];

    /* 6. Write via O_CREAT|O_EXCL only after all validations pass (no truncation on error). */
    long out = sc6(SYS_openat, AT_FDCWD, (long)"/tmp/jiritsu/sector0.pkt",
                   O_WRONLY | O_CREAT | O_EXCL, 0644, 0, 0);
    if (out < 0) return;
    long wtot = 0;
    while (wtot < 528) {
        long wn = sc6(SYS_write, out, (long)(pkt + wtot), 528 - wtot, 0, 0, 0);
        if (wn == -4L) continue;
        if (wn <= 0) break;
        wtot += wn;
    }
    sc6(SYS_close, out, 0, 0, 0, 0, 0);
}
"""


def inspect_libjit_elf_pt_load(so_bytes: bytes) -> Dict[str, Any]:
    """Validate ELF64 AArch64 ET_DYN headers and 64KiB-safe PT_LOAD alignment."""
    if len(so_bytes) < 64 or so_bytes[:4] != b"\x7fELF":
        raise ValueError("libJit.so is not a valid ELF")
    ei_class, ei_data = so_bytes[4], so_bytes[5]
    e_type, e_machine = struct.unpack_from("<HH", so_bytes, 0x10)
    e_phoff = struct.unpack_from("<Q", so_bytes, 0x20)[0]
    e_phentsize, e_phnum = struct.unpack_from("<HH", so_bytes, 0x36)
    if ei_class != 2 or ei_data != 1 or e_type != 3 or e_machine != 183:
        raise ValueError(
            f"Unexpected libJit.so ELF header class={ei_class} data={ei_data} type={e_type} mach={e_machine}"
        )
    pt_load_aligns: List[int] = []
    has_dynamic = False
    for i in range(e_phnum):
        p_type, _p_flags, _p_off, _p_va, _p_pa, _p_fsz, _p_msz, p_align = struct.unpack_from(
            "<IIQQQQQQ", so_bytes, e_phoff + i * e_phentsize
        )
        if p_type == 1:
            pt_load_aligns.append(p_align)
        elif p_type == 2:
            has_dynamic = True
    if not pt_load_aligns or any(a != 0x10000 for a in pt_load_aligns) or not has_dynamic:
        raise ValueError(
            f"libJit.so PT_LOAD/DYNAMIC validation failed: aligns={pt_load_aligns} dynamic={has_dynamic}"
        )
    return {
        "bytes": len(so_bytes),
        "sha256": sha256_bytes(so_bytes),
        "e_type": e_type,
        "e_machine": e_machine,
        "pt_load_count": len(pt_load_aligns),
        "pt_load_align": "0x10000",
        "has_pt_dynamic": has_dynamic,
    }


def build_hardened_libjit_so(tmp_build: pathlib.Path) -> Tuple[bytes, Dict[str, Any]]:
    """Compile hardened 64KiB-aligned self-unlinking ARM64 libJit.so strictly inside tmp_build."""
    tmp_build.mkdir(parents=True, exist_ok=True)
    cache_dir = tmp_build / "zig-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    zig_env = os.environ.copy()
    zig_env["ZIG_LOCAL_CACHE_DIR"] = str(cache_dir / "local")
    zig_env["ZIG_GLOBAL_CACHE_DIR"] = str(cache_dir / "global")
    jit_c = tmp_build / "jit_payload.c"
    jit_so = tmp_build / "libJit.so"
    jit_c.write_text(FX3_HARDENED_LIBJIT_C, encoding="utf-8")
    jit_cmd = [
        str(ZIG),
        "cc",
        "-target",
        "aarch64-linux-gnu.2.17",
        "-shared",
        "-fPIC",
        "-nostdlib",
        "-fno-sanitize=all",
        "-fno-stack-protector",
        "-O2",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-Wl,-z,max-page-size=0x10000",
        "-Wl,-z,common-page-size=0x10000",
        "-Wl,--hash-style=sysv",
        "-Wl,-soname,libJit.so",
        str(jit_c),
        "-o",
        str(jit_so),
    ]
    r_jit = subprocess.run(jit_cmd, env=zig_env, capture_output=True, text=True)
    if r_jit.returncode != 0:
        raise RuntimeError(f"libJit.so compile failed:\n{r_jit.stderr}")
    so_bytes = jit_so.read_bytes()
    meta = inspect_libjit_elf_pt_load(so_bytes)
    meta["compile_cmd"] = jit_cmd
    return so_bytes, meta


def build_sd_trigger_manifest(
    items: Sequence[Tuple[bytes, str]],
    mode: str,
) -> Tuple[bytes, Dict[str, Any]]:
    """Build /mnt/sd/FX6_STAGEB_BOOT.MANIFEST (valid or deterministic 1-byte tampered)."""
    lines = [f"{sha256_bytes(blob)} {gpath}\n" for blob, gpath in items]
    raw = "".join(lines).encode("utf-8")
    meta: Dict[str, Any] = {
        "mode": mode,
        "item_count": len(items),
        "items": [{"guest_path": gp, "sha256": sha256_bytes(b), "bytes": len(b)} for b, gp in items],
        "valid_sha256": sha256_bytes(raw),
    }
    if mode == "tampered":
        corrupted = bytearray(raw)
        orig_byte = chr(corrupted[0])
        new_char = "1" if orig_byte != "1" else "0"
        corrupted[0] = ord(new_char)
        raw = bytes(corrupted)
        meta["tamper_offset"] = 0
        meta["tamper_bytes_flipped"] = 1
        meta["orig_char"] = orig_byte
        meta["corrupted_char"] = new_char
    meta["manifest_bytes"] = len(raw)
    meta["manifest_sha256"] = sha256_bytes(raw)
    return raw, meta


def build_stage_a_overlay(
    tmp_build: pathlib.Path,
    parent_cpio: pathlib.Path,
    bk4_ntsc_bytes: Optional[bytes],
    *,
    enable_p10: bool = False,
    enable_r10: bool = False,
    enable_p12: bool = False,
    enable_r12: bool = False,
    enable_r13: bool = False,
    enable_r14: bool = False,
    enable_r15: bool = False,
    enable_r16: bool = False,
    enable_r17: bool = False,
    enable_r18: bool = False,
    enable_r19: bool = False,
    enable_r20: bool = False,
    enable_r21: bool = False,
    enable_r22: bool = False,
    enable_r23: bool = False,
    enable_r24: bool = False,
    enable_r25: bool = False,
    enable_r26: bool = False,
    enable_r27: bool = False,
    enable_r28: bool = False,
    sd_manifest_mode: str = "valid",
    lang: str = "en",
    shim_bytes: Optional[bytes] = None,
) -> Tuple[Dict[str, bytes], Dict[str, Tuple[bytes, int]], Dict[str, Any]]:
    """Build Stage-A/B P1..P9+Fan(+P10/P11/P12) + 8MiB VFAT + RAM-Shadow BK4 + image_00_169.uxc (+ Multi-CJK UXC/LTT) + Verify-Before-Mount overlay."""
    patcher, vfat_builder, bmtv = _import_stage_a_modules()

    p10_spec = _load_p10_keymap_spec(patcher) if enable_p10 else None
    p12_spec = _load_p12_wlan_spec(patcher) if enable_p12 else None
    appfw_spec = patcher.P1_P4_P8_APPFW_COMBINED_SPEC
    if p10_spec is not None:
        appfw_spec = patcher.LibraryPatchSpec(
            spec_id="P1_P4_P8_P10_appFw_combined",
            library_name=patcher.P1_P4_P8_APPFW_COMBINED_SPEC.library_name,
            expected_size=patcher.P1_P4_P8_APPFW_COMBINED_SPEC.expected_size,
            donor_sha256=patcher.P1_P4_P8_APPFW_COMBINED_SPEC.donor_sha256,
            sites=patcher.P1_P4_P8_APPFW_COMBINED_SPEC.sites + p10_spec.sites,
            elf_kind=patcher.P1_P4_P8_APPFW_COMBINED_SPEC.elf_kind,
            source_domain=patcher.P1_P4_P8_APPFW_COMBINED_SPEC.source_domain,
        )

    member_specs = (
        ("usr/lib/libInfraSetupFile.so", patcher.P1_LIB_INFRA_SETUP_FILE_SPEC),
        ("usr/lib/libInfraMediaCommon.so", patcher.P1_LIB_INFRA_MEDIA_COMMON_SPEC),
        ("usr/lib/libInfraMediaConfig.so", patcher.P1_LIB_INFRA_MEDIA_CONFIG_SPEC),
        ("usr/lib/libInfraAppRemoteBoard.so", patcher.P3_LIB_INFRA_APP_REMOTE_BOARD_SPEC),
        ("usr/lib/libfan.so", patcher.FAN_LIBFAN_SPEC),
        ("usr/lib/appFw.so", appfw_spec),
    )
    lang_asset_specs = {
        "schinese": (
            (
                ("string_simplifiedchinese", "usr/share/app/string_simplifiedchinese.uxc", DONOR_STRING_SCHINESE_UXC, b"uxc\x07", "uxc_07"),
                ("string_simplifiedchinese_2", "usr/share/app/string_simplifiedchinese_2.uxc", DONOR_STRING_SCHINESE_2_UXC, b"uxc\x07", "uxc_07"),
                ("font_gb18030_ltt", "usr/share/app/MYingHeiC-GB18030-SJ_wIcon.ltt", DONOR_FONT_SCHINESE_LTT, b"LTT\n", "LTT"),
            ),
            "FONT_S_CHINESE",
            "MYingHeiC-GB18030-SJ_wIcon.ltt",
        ),
        "tchinese": (
            (
                ("string_traditionalchinese", "usr/share/app/string_traditionalchinese.uxc", DONOR_STRING_TCHINESE_UXC, b"uxc\x07", "uxc_07"),
                ("string_traditionalchinese_2", "usr/share/app/string_traditionalchinese_2.uxc", DONOR_STRING_TCHINESE_2_UXC, b"uxc\x07", "uxc_07"),
                ("font_big5hkscs_ltt", "usr/share/app/MYingHeiC-Big5HKSCS-SJ_wIcon.ltt", DONOR_FONT_TCHINESE_LTT, b"LTT\n", "LTT"),
            ),
            "FONT_T_CHINESE",
            "MYingHeiC-Big5HKSCS-SJ_wIcon.ltt",
        ),
        "japanese": (
            (
                ("string_japanese", "usr/share/app/string_japanese.uxc", DONOR_STRING_JAPANESE_UXC, b"uxc\x07", "uxc_07"),
                ("string_japanese_2", "usr/share/app/string_japanese_2.uxc", DONOR_STRING_JAPANESE_2_UXC, b"uxc\x07", "uxc_07"),
                ("font_japanese_ltt", "usr/share/app/HeiseiKakuGothW5-SJ_wIcon.ltt", DONOR_FONT_JAPANESE_LTT, b"LTT\n", "LTT"),
            ),
            "FONT_JAPANESE",
            "HeiseiKakuGothW5-SJ_wIcon.ltt",
        ),
        "english": (
            (
                ("string_english", "usr/share/app/string_english.uxc", DONOR_STRING_ENGLISH_UXC, b"uxc\x07", "uxc_07"),
                ("string_english_2", "usr/share/app/string_english_2.uxc", DONOR_STRING_ENGLISH_2_UXC, b"uxc\x07", "uxc_07"),
                ("font_univers_ltt", "usr/share/app/UniversOTS-SJ_wIcon.ltt", DONOR_FONT_ENGLISH_LTT, b"LTT\n", "LTT"),
            ),
            "FONT_UNIVERS",
            "UniversOTS-SJ_wIcon.ltt",
        ),
    }
    extra_extract: Tuple[str, ...] = ("init", "usr/kmod/upm.ko")
    if enable_r10:
        extra_extract = extra_extract + ("usr/share/app/image_00_169.uxc",)
    if enable_p12:
        extra_extract = extra_extract + ("usr/lib/libWlanResource.so",)
    if lang in lang_asset_specs:
        lang_items, _, _ = lang_asset_specs[lang]
        extra_extract = extra_extract + tuple(item[1] for item in lang_items) + ("usr/share/app/fontlist.dat",)
    cpio_extract_names = tuple(m for m, _ in member_specs) + extra_extract
    raw_members = _extract_cpio_members(parent_cpio, cpio_extract_names)

    replacements: Dict[str, bytes] = {}
    patch_receipts: Dict[str, Any] = {}
    manifest_rows: List[Tuple[str, str]] = []

    for cpio_name, spec in member_specs:
        patched_bytes, receipt = patcher.apply_patch_spec(
            raw_members[cpio_name], spec, verify_donor_sha256=True
        )
        replacements[cpio_name] = patched_bytes
        patch_receipts[spec.spec_id] = {
            "library": spec.library_name,
            "before_sha256": receipt.before_sha256,
            "after_sha256": receipt.after_sha256,
            "changed_bytes": receipt.changed_byte_count,
            "sites": [s.site_id for s in receipt.resolutions],
        }
        manifest_rows.append((receipt.after_sha256, f"/{cpio_name}"))

    if p10_spec is not None:
        patch_receipts[p10_spec.spec_id] = {
            "library": p10_spec.library_name,
            "changed_bytes": sum(s.size for s in p10_spec.sites),
            "sites": [s.site_id for s in p10_spec.sites],
            "combined_appfw_after_sha256": patch_receipts[appfw_spec.spec_id]["after_sha256"],
        }

    # P9 upm.ko: patch FX3 donor upm.ko in-memory via O_RDONLY when present, else verify CPIO's already-patched upm.ko
    if FX3_UPM_KO.exists():
        upm_patched, upm_receipt = patcher.apply_patch_spec(
            read_bytes_readonly(FX3_UPM_KO), patcher.P9_UPM_KO_SPEC, verify_donor_sha256=True
        )
        replacements["usr/kmod/upm.ko"] = upm_patched
        upm_sha = upm_receipt.after_sha256
        patch_receipts[patcher.P9_UPM_KO_SPEC.spec_id] = {
            "library": patcher.P9_UPM_KO_SPEC.library_name,
            "source": str(FX3_UPM_KO),
            "before_sha256": upm_receipt.before_sha256,
            "after_sha256": upm_sha,
            "changed_bytes": upm_receipt.changed_byte_count,
            "sites": [s.site_id for s in upm_receipt.resolutions],
        }
    else:
        upm_bytes = raw_members["usr/kmod/upm.ko"]
        upm_res = patcher.resolve_and_verify_sites(
            upm_bytes, patcher.P9_UPM_KO_SPEC, expect_patched_state=True
        )
        upm_sha = sha256_bytes(upm_bytes)
        patch_receipts[patcher.P9_UPM_KO_SPEC.spec_id] = {
            "library": patcher.P9_UPM_KO_SPEC.library_name,
            "source": "cpio_prepatched",
            "after_sha256": upm_sha,
            "sites": [s.site_id for s in upm_res],
        }
    manifest_rows.append((upm_sha, "/usr/kmod/upm.ko"))

    # P2: 8 MiB RAM opelog.vfat
    vfat_bytes, vfat_receipt = vfat_builder.build_opelog_vfat_image("8m_ram")
    vfat_audit = vfat_builder.verify_vfat_image(vfat_bytes)
    if not vfat_audit.valid:
        raise RuntimeError(f"Invalid P2 VFAT image: {vfat_audit.errors}")
    manifest_rows.append((vfat_receipt.sha256, "/tmp/opelog.vfat"))

    # RAM-Shadow BK4\0 container
    fa0080_tbl = bmtv.build_canonical_fa0080_normal_boot_table(
        donor_seed_bk4_path=FX3_SEED_BK4 if FX3_SEED_BK4.exists() else None
    )
    bk4_bundle = bmtv.synthesize_ram_shadow_bk4(
        flash_write_allowed=False,
        active_byte8=0x00,
        fa0080_table=fa0080_tbl,
    )
    manifest_rows.append((bk4_bundle.sha256, "/etc/fx6_ram_shadow_bk4.bin"))

    if bk4_ntsc_bytes is not None:
        manifest_rows.append((sha256_bytes(bk4_ntsc_bytes), "/etc/fx6_chaplin_ntsc.bk4"))

    if enable_p10 and shim_bytes is not None:
        manifest_rows.append((sha256_bytes(shim_bytes), "/usr/lib/libgrm-fbinit9.so"))

    clean_room = os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM", "").strip() == "1"
    uxc_meta: Optional[Dict[str, Any]] = None
    if enable_r10:
        if not clean_room and DONOR_IMAGE_00_169_UXC.is_file():
            uxc_bytes = read_bytes_readonly(DONOR_IMAGE_00_169_UXC)
            uxc_source = "donor_o_rdonly"
        else:
            uxc_bytes = raw_members["usr/share/app/image_00_169.uxc"]
            uxc_source = "cpio_preloaded"
        if len(uxc_bytes) < 16 or uxc_bytes[:4] != b"uxd\x07":
            raise RuntimeError(f"Invalid image_00_169.uxc magic: {uxc_bytes[:4].hex()}")
        replacements["usr/share/app/image_00_169.uxc"] = uxc_bytes
        uxc_sha = sha256_bytes(uxc_bytes)
        manifest_rows.append((uxc_sha, "/usr/share/app/image_00_169.uxc"))
        uxc_meta = {
            "guest_path": "/usr/share/app/image_00_169.uxc",
            "source": uxc_source,
            "bytes": len(uxc_bytes),
            "sha256": uxc_sha,
            "magic": "uxd_07",
        }

    if p12_spec is not None:
        wlan_patched, wlan_receipt = patcher.apply_patch_spec(
            raw_members["usr/lib/libWlanResource.so"], p12_spec, verify_donor_sha256=True
        )
        replacements["usr/lib/libWlanResource.so"] = wlan_patched
        patch_receipts[p12_spec.spec_id] = {
            "library": p12_spec.library_name,
            "before_sha256": wlan_receipt.before_sha256,
            "after_sha256": wlan_receipt.after_sha256,
            "changed_bytes": wlan_receipt.changed_byte_count,
            "sites": [s.site_id for s in wlan_receipt.resolutions],
        }
        manifest_rows.append((wlan_receipt.after_sha256, "/usr/lib/libWlanResource.so"))

    lang_assets_meta: Optional[Dict[str, Any]] = None
    schinese_assets_meta: Optional[Dict[str, Any]] = None
    if lang in lang_asset_specs:
        lang_specs, fontlist_key, fontlist_ltt = lang_asset_specs[lang]
        lang_assets_meta = {}
        for key, cpio_name, donor_path, expected_magic, magic_label in lang_specs:
            if not clean_room and donor_path.is_file():
                asset_bytes = read_bytes_readonly(donor_path)
                asset_source = "donor_o_rdonly"
            else:
                asset_bytes = raw_members[cpio_name]
                asset_source = "cpio_preloaded"
            if len(asset_bytes) < 16 or asset_bytes[:4] != expected_magic:
                raise RuntimeError(
                    f"Invalid {cpio_name} magic: {asset_bytes[:4].hex()} (expected {expected_magic.hex()})"
                )
            replacements[cpio_name] = asset_bytes
            lang_assets_meta[key] = {
                "guest_path": f"/{cpio_name}",
                "source": asset_source,
                "bytes": len(asset_bytes),
                "sha256": sha256_bytes(asset_bytes),
                "magic": magic_label,
            }
        fontlist_bytes = raw_members["usr/share/app/fontlist.dat"]
        if (
            fontlist_key.encode("ascii") not in fontlist_bytes
            or fontlist_ltt.encode("ascii") not in fontlist_bytes
        ):
            raise RuntimeError(f"fontlist.dat missing {fontlist_key} -> {fontlist_ltt} mapping")
        lang_assets_meta["fontlist_dat"] = {
            "guest_path": "/usr/share/app/fontlist.dat",
            "source": "cpio_preloaded",
            "bytes": len(fontlist_bytes),
            "sha256": sha256_bytes(fontlist_bytes),
            "fontlist_key": fontlist_key,
            "has_font_s_chinese": (lang == "schinese"),
        }
        if lang == "schinese":
            schinese_assets_meta = lang_assets_meta

    # Compile fx6-stage-a-verify C guest tool in /private/tmp
    cache_dir = tmp_build / "zig-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    zig_env = os.environ.copy()
    zig_env["ZIG_LOCAL_CACHE_DIR"] = str(cache_dir / "local")
    zig_env["ZIG_GLOBAL_CACHE_DIR"] = str(cache_dir / "global")
    verify_out = tmp_build / "fx6-stage-a-verify"
    verify_cmd = [
        str(ZIG),
        "cc",
        "-target",
        "aarch64-linux-gnu.2.17",
        "-std=gnu11",
        "-no-pie",
        "-fno-sanitize=all",
        "-fno-stack-protector",
        "-O2",
        "-Wall",
        "-Wextra",
        "-Werror",
        str(HERE / "fx6-stage-a-verify.c"),
        "-ldl",
        "-o",
        str(verify_out),
    ]
    r_ver = subprocess.run(verify_cmd, env=zig_env, capture_output=True, text=True)
    if r_ver.returncode != 0:
        raise RuntimeError(f"fx6-stage-a-verify compile failed:\n{r_ver.stderr}")
    verify_bytes = verify_out.read_bytes()

    # Rewrite guest /init in-memory to execute Stage-A/B Verify-Before-Mount right before appfw-launch
    init_txt = raw_members["init"].decode("utf-8", errors="replace")
    launch_needle = 'LD_PRELOAD="$FX6_PRELOAD" /usr/bin/appfw-launch'
    if launch_needle not in init_txt:
        raise RuntimeError(f"Expected launch line not found in {parent_cpio} /init")
    if enable_r28:
        devtmpfs_needle = "echo FX3_DEVTMPFS_RC=$?\n"
        if devtmpfs_needle not in init_txt:
            raise RuntimeError(f"Expected devtmpfs marker not found in {parent_cpio} /init")
        sd_gate_hook = (
            "/usr/bin/fx6-stage-a-verify --sd-gate > /dev/console 2>&1\n"
            "fx6_sd_gate_rc=$?\n"
            "echo FX6_R28_SD_GATE_RC=$fx6_sd_gate_rc\n"
            'if [ "$fx6_sd_gate_rc" != 0 ]; then\n'
            ' if [ "$fx6_sd_gate_rc" = 10 ]; then\n'
            "  echo FX6_R28_STOCK_FX3_BYPASS_EXIT mode=STOCK_FX3_BYPASS stageb_loaded=0 emmc_write_count=0\n"
            " else\n"
            "  echo FX6_R28_FAIL_CLOSED_FALLBACK_EXIT mode=FAIL_CLOSED_STOCK_FX3_FALLBACK stageb_loaded=0 emmc_write_count=0\n"
            " fi\n"
            " /bin/busybox sync 2>/dev/null\n"
            " /bin/busybox poweroff -f 2>/dev/null || /bin/busybox halt -f 2>/dev/null\n"
            " while true; do /bin/busybox sleep 1; done\n"
            "fi\n"
        )
        init_txt = init_txt.replace(devtmpfs_needle, devtmpfs_needle + sd_gate_hook, 1)
    verify_hook = (
        "/usr/bin/fx6-stage-a-verify > /dev/console 2>&1\n"
        "fx6_stage_a_rc=$?\n"
        "echo FX6_STAGE_A_VERIFY_RC=$fx6_stage_a_rc\n"
        'if [ "$fx6_stage_a_rc" != 0 ]; then\n'
        " echo FX6_STAGE_A_ABORT_BEFORE_LAUNCH rc=$fx6_stage_a_rc\n"
        " while true; do /bin/busybox sleep 1; done\n"
        "fi\n"
    )
    replacements["init"] = init_txt.replace(launch_needle, verify_hook + launch_needle, 1).encode("utf-8")

    manifest_text = "".join(f"{digest} {gpath}\n" for digest, gpath in manifest_rows).encode("utf-8")
    additions: Dict[str, Tuple[bytes, int]] = {
        "usr/bin/fx6-stage-a-verify": (verify_bytes, 0o100755),
        "etc/fx6_stage_a_manifest.txt": (manifest_text, 0o100644),
        "tmp/opelog.vfat": (vfat_bytes, 0o100644),
        "etc/fx6_ram_shadow_bk4.bin": (bk4_bundle.bk4_bytes, 0o100644),
    }
    if enable_p10:
        additions["etc/fx6_stage_b"] = (b"stage_b=1\np10_keymap=1\n", 0o100644)
    if enable_r10:
        additions["etc/fx6_stage_r10"] = (b"stage_r10=1\np11_uipc=1\nuxc=1\n", 0o100644)
    if enable_p12:
        additions["etc/fx6_stage_r11"] = (
            f"stage_r11=1\np12_wlan=1\nairplane_mode=1\nlang={lang}\n".encode("utf-8"),
            0o100644,
        )
    if enable_r12:
        additions["etc/fx6_stage_r12"] = (
            f"stage_r12=1\np10_keymap=1\np11_uipc=1\np12_wlan=1\np4_nd_clear=1\nuxc=1\nlang={lang}\n".encode("utf-8"),
            0o100644,
        )
    if enable_r13:
        additions["etc/fx6_stage_r13"] = (
            f"stage_r13=1\np10_keymap=1\np11_uipc=1\np12_wlan=1\np4_nd_clear=1\nuxc=1\n4lang_matrix=1\nlang={lang}\n".encode("utf-8"),
            0o100644,
        )
    if enable_r14:
        additions["etc/fx6_stage_r14"] = (
            f"stage_r14=1\np10_keymap=1\np11_uipc=1\np12_wlan=1\np4_nd_clear=1\nuxc=1\n4lang_matrix=1\nstatuscheck_4lang=1\nlang={lang}\n".encode("utf-8"),
            0o100644,
        )
    if enable_r15:
        additions["etc/fx6_stage_r15"] = (
            f"stage_r15=1\np10_keymap=1\np11_uipc=1\np12_wlan=1\np4_nd_clear=1\nuxc=1\n4lang_matrix=1\nstatuscheck_multitab=1\nmonitoring_3layer=1\nlang={lang}\n".encode("utf-8"),
            0o100644,
        )
    if enable_r16:
        additions["etc/fx6_stage_r16"] = (
            f"stage_r16=1\np10_keymap=1\np11_uipc=1\np12_wlan=1\np4_nd_clear=1\nuxc=1\n4lang_matrix=1\nstatuscheck_tabs45=1\ntcmedia_3layer=1\nlang={lang}\n".encode("utf-8"),
            0o100644,
        )
    if enable_r17:
        additions["etc/fx6_stage_r17"] = (
            f"stage_r17=1\np10_keymap=1\np11_uipc=1\np12_wlan=1\np4_nd_clear=1\nuxc=1\n4lang_matrix=1\nstatuscheck_fullsweep=1\naudio_3layer=1\nlang={lang}\n".encode("utf-8"),
            0o100644,
        )
    if enable_r18:
        additions["etc/fx6_stage_r18"] = (
            f"stage_r18=1\np10_keymap=1\np11_uipc=1\np12_wlan=1\np4_nd_clear=1\nuxc=1\n4lang_matrix=1\nmenu_8cat_closure=1\nlang={lang}\n".encode("utf-8"),
            0o100644,
        )
    if enable_r19:
        additions["etc/fx6_stage_r19"] = (
            f"stage_r19=1\np10_keymap=1\np11_uipc=1\np12_wlan=1\np4_nd_clear=1\nuxc=1\n4lang_matrix=1\nmenu_11cat_fullsweep=1\nlang={lang}\n".encode("utf-8"),
            0o100644,
        )
    if enable_r20:
        additions["etc/fx6_stage_r20"] = (
            f"stage_r20=1\np10_keymap=1\np11_uipc=1\np12_wlan=1\np4_nd_clear=1\nuxc=1\n4lang_matrix=1\nnetwork_4lang_wf12_closure=1\nlang={lang}\n".encode("utf-8"),
            0o100644,
        )
    if enable_r21:
        additions["etc/fx6_stage_r21"] = (
            f"stage_r21=1\np10_keymap=1\np11_uipc=1\np12_wlan=1\np4_nd_clear=1\nuxc=1\n4lang_matrix=1\naudio_4lang_dualsurface=1\nlang={lang}\n".encode("utf-8"),
            0o100644,
        )
    if enable_r22:
        additions["etc/fx6_stage_r22"] = (
            f"stage_r22=1\np10_keymap=1\np11_uipc=1\np12_wlan=1\np4_nd_clear=1\nuxc=1\n4lang_matrix=1\npaintlook_camtab2_4lang_dualsurface=1\nlang={lang}\n".encode("utf-8"),
            0o100644,
        )
    if enable_r23:
        additions["etc/fx6_stage_r23"] = (
            f"stage_r23=1\np10_keymap=1\np11_uipc=1\np12_wlan=1\np4_nd_clear=1\nuxc=1\n4lang_matrix=1\nmonitoring_tab5_4lang_dualsurface=1\nlang={lang}\n".encode("utf-8"),
            0o100644,
        )
    if enable_r24:
        additions["etc/fx6_stage_r24"] = (
            f"stage_r24=1\np10_keymap=1\np11_uipc=1\np12_wlan=1\np4_nd_clear=1\nuxc=1\n4lang_matrix=1\nproject_tab4_4lang_dualsurface=1\nlang={lang}\n".encode("utf-8"),
            0o100644,
        )
    if enable_r25:
        additions["etc/fx6_stage_r25"] = (
            f"stage_r25=1\np10_keymap=1\np11_uipc=1\np12_wlan=1\np4_nd_clear=1\nuxc=1\n4lang_matrix=1\ntcmedia_tab8_4lang_dualsurface=1\nlang={lang}\n".encode("utf-8"),
            0o100644,
        )
    if enable_r26:
        additions["etc/fx6_stage_r26"] = (
            f"stage_r26=1\np10_keymap=1\np11_uipc=1\np12_wlan=1\np4_nd_clear=1\nuxc=1\n4lang_matrix=1\ntechnical_tab6_4lang_dualsurface=1\nlang={lang}\n".encode("utf-8"),
            0o100644,
        )
    if enable_r27:
        additions["etc/fx6_stage_r27"] = (
            f"stage_r27=1\np10_keymap=1\np11_uipc=1\np12_wlan=1\np4_nd_clear=1\nuxc=1\n4lang_matrix=1\nmaintenance_tab7_4lang_dualsurface=1\nlang={lang}\n".encode("utf-8"),
            0o100644,
        )
    r28_meta: Optional[Dict[str, Any]] = None
    if enable_r28:
        if sd_manifest_mode not in ("valid", "absent", "tampered"):
            raise ValueError(f"Unsupported sd_manifest_mode: {sd_manifest_mode}")
        additions["etc/fx6_stage_r28"] = (
            f"stage_r28=1\nsd_manifest_mode={sd_manifest_mode}\nstrategy_a=1\nlang={lang}\n".encode("utf-8"),
            0o100644,
        )
        additions["mnt/sd"] = (b"", 0o040755)
        additions["tmp/jiritsu"] = (b"", 0o040755)
        r28_meta = {
            "sd_manifest_mode": sd_manifest_mode,
            "strategy_a_nflasha20_target": "/dev/nflasha30",
            "strategy_a_opelog_fstype": "tmpfs",
        }
        if sd_manifest_mode in ("valid", "tampered"):
            fx3_sector0_bytes = build_fx3_sector0_table()
            libjit_bytes, libjit_meta = build_hardened_libjit_so(tmp_build)
            sd_cfg_bytes = (
                f"mode=fx6_stageb_dualboot\nlang={lang}\nstrategy_a=1\n"
                f"sector0_crc32=0x{zlib.crc32(fx3_sector0_bytes) & 0xFFFFFFFF:08x}\n"
            ).encode("utf-8")
            sd_manifest_bytes, sd_manifest_meta = build_sd_trigger_manifest(
                [
                    (sd_cfg_bytes, "/mnt/sd/FX6_STAGEB_BOOT.CFG"),
                    (fx3_sector0_bytes, "/etc/fx3_sector0.bin"),
                    (libjit_bytes, "/tmp/jiritsu/libJit.so"),
                    (bk4_bundle.bk4_bytes, "/etc/fx6_ram_shadow_bk4.bin"),
                    (manifest_text, "/etc/fx6_stage_a_manifest.txt"),
                ],
                mode=sd_manifest_mode,
            )
            additions["etc/fx3_sector0.bin"] = (fx3_sector0_bytes, 0o100444)
            additions["tmp/jiritsu/libJit.so"] = (libjit_bytes, 0o100755)
            additions["mnt/sd/FX6_STAGEB_BOOT.CFG"] = (sd_cfg_bytes, 0o100644)
            additions["mnt/sd/FX6_STAGEB_BOOT.MANIFEST"] = (sd_manifest_bytes, 0o100644)
            r28_meta["fx3_sector0"] = {
                "bytes": len(fx3_sector0_bytes),
                "sha256": sha256_bytes(fx3_sector0_bytes),
                "crc32": f"0x{zlib.crc32(fx3_sector0_bytes) & 0xFFFFFFFF:08x}",
                "magic": "8246",
                "ver": "2.00",
                "n_partition": len(FX3_SECTOR0_PARTITIONS),
            }
            r28_meta["libjit"] = libjit_meta
            r28_meta["sd_manifest"] = sd_manifest_meta
        else:
            r28_meta["sd_manifest"] = {"mode": "absent", "manifest_present": False}
    stage_a_meta: Dict[str, Any] = {
        "stage": "B" if enable_p10 else "A",
        "r10_enabled": enable_r10,
        "p12_enabled": enable_p12,
        "r12_enabled": enable_r12,
        "r13_enabled": enable_r13,
        "r14_enabled": enable_r14,
        "r15_enabled": enable_r15,
        "r16_enabled": enable_r16,
        "r17_enabled": enable_r17,
        "r18_enabled": enable_r18,
        "r19_enabled": enable_r19,
        "r20_enabled": enable_r20,
        "r21_enabled": enable_r21,
        "r22_enabled": enable_r22,
        "r23_enabled": enable_r23,
        "r24_enabled": enable_r24,
        "r25_enabled": enable_r25,
        "r26_enabled": enable_r26,
        "r27_enabled": enable_r27,
        "r28_enabled": enable_r28,
        "lang": lang,
        "verify_bin_bytes": len(verify_bytes),
        "verify_bin_sha256": sha256_bytes(verify_bytes),
        "manifest_count": len(manifest_rows),
        "manifest_items": [
            {"guest_path": gpath, "sha256": digest} for digest, gpath in manifest_rows
        ],
        "patches": patch_receipts,
        "p2_vfat": {
            "mode": vfat_receipt.mode,
            "fat_type": vfat_receipt.fat_type,
            "bytes": vfat_receipt.total_bytes,
            "sha256": vfat_receipt.sha256,
            "precreated_dirs": list(vfat_receipt.precreated_dirs),
        },
        "ram_shadow_bk4": {
            "bytes": bk4_bundle.total_bytes,
            "sha256": bk4_bundle.sha256,
            "flash_write_allowed": bk4_bundle.flash_write_allowed,
            "active_byte8_selector": bk4_bundle.active_byte8_selector,
            "synthesized_key_count": bk4_bundle.synthesized_key_count,
        },
    }
    if uxc_meta is not None:
        stage_a_meta["image_00_169_uxc"] = uxc_meta
    if schinese_assets_meta is not None:
        stage_a_meta["schinese_assets"] = schinese_assets_meta
    if lang_assets_meta is not None:
        stage_a_meta["lang_assets"] = lang_assets_meta
    if r28_meta is not None:
        stage_a_meta["r28"] = r28_meta
    return replacements, additions, stage_a_meta


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


def _png_chunk(chunk_type: bytes, payload: bytes) -> bytes:
    crc = zlib.crc32(chunk_type + payload) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + chunk_type + payload + struct.pack(">I", crc)


def write_rgba_png(out_path: pathlib.Path, width: int, height: int, rgba: bytes) -> Dict[str, Any]:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    stride = width * 4
    scanlines = bytearray((stride + 1) * height)
    pos = 0
    for y in range(height):
        scanlines[pos] = 0  # Filter type 0 (None)
        row_start = y * stride
        scanlines[pos + 1 : pos + 1 + stride] = rgba[row_start : row_start + stride]
        pos += stride + 1
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    idat = zlib.compress(bytes(scanlines), level=9)
    png_bytes = (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", idat)
        + _png_chunk(b"IEND", b"")
    )
    out_path.write_bytes(png_bytes)
    return {
        "path": str(out_path),
        "bytes": len(png_bytes),
        "sha256": sha256_bytes(png_bytes),
    }


def unpack_rgba4444_pixel(p16: int) -> Tuple[int, int, int, int]:
    """Unpack BMP_PixelFormat==1 (stella_fmt==7, 16-bit LE RGBA4444) -> (R, G, B, A) 8-bit."""
    p16 &= 0xFFFF
    r = ((p16 >> 12) & 0xF) * 17
    g = ((p16 >> 8) & 0xF) * 17
    b = ((p16 >> 4) & 0xF) * 17
    a = (p16 & 0xF) * 17
    return (r, g, b, a)


def unpack_rgba4444_buffer(raw_le16: bytes) -> bytes:
    """Unpack packed little-endian RGBA4444 pixels into [R, G, B, A] 8-bit bytes."""
    if len(raw_le16) % 2 != 0:
        raise ValueError(f"RGBA4444 byte length must be even, got {len(raw_le16)}")
    out = bytearray((len(raw_le16) // 2) * 4)
    pos = 0
    for (p16,) in struct.iter_unpack("<H", raw_le16):
        out[pos] = ((p16 >> 12) & 0xF) * 17
        out[pos + 1] = ((p16 >> 8) & 0xF) * 17
        out[pos + 2] = ((p16 >> 4) & 0xF) * 17
        out[pos + 3] = (p16 & 0xF) * 17
        pos += 4
    return bytes(out)


def unpack_rgba8888_pixel(px4: bytes) -> Tuple[int, int, int, int]:
    """Unpack BMP_PixelFormat==2 (stella_fmt==1, 4-byte [R, G, B, A]) -> (R, G, B, A) 8-bit."""
    if len(px4) != 4:
        raise ValueError(f"RGBA8888 pixel must be 4 bytes, got {len(px4)}")
    return (px4[0], px4[1], px4[2], px4[3])


def unpack_rgba8888_buffer(raw_rgba: bytes) -> bytes:
    """Convert stella RGBA8888 [R, G, B, A] bytes into GPE0 little-endian 0xAARRGGBB ([B, G, R, A])."""
    if len(raw_rgba) % 4 != 0:
        raise ValueError(f"RGBA8888 buffer length must be divisible by 4, got {len(raw_rgba)}")
    out = bytearray(len(raw_rgba))
    out[0::4] = raw_rgba[2::4]  # B
    out[1::4] = raw_rgba[1::4]  # G
    out[2::4] = raw_rgba[0::4]  # R
    out[3::4] = raw_rgba[3::4]  # A
    return bytes(out)


def export_gpe0_pngs(
    raw_path: pathlib.Path,
    out_dir: pathlib.Path,
    stem: str,
    bg_rgb: Tuple[int, int, int] = (0x16, 0x1A, 0x20),
) -> Dict[str, Any]:
    data = raw_path.read_bytes()[:FB_BYTES]
    if len(data) < FB_BYTES:
        raise ValueError(f"Short GPE0 readback ({len(data)} < {FB_BYTES})")

    # GPE0 stores 0xAARRGGBB in little-endian uint32 -> [B, G, R, A] bytes
    rgba_alpha = bytearray(FB_BYTES)
    rgba_alpha[0::4] = data[2::4]  # R
    rgba_alpha[1::4] = data[1::4]  # G
    rgba_alpha[2::4] = data[0::4]  # B
    rgba_alpha[3::4] = data[3::4]  # A

    bg_r, bg_g, bg_b = bg_rgb
    rgba_comp = bytearray(FB_BYTES)
    transparent_px = 0
    for idx in range(0, FB_BYTES, 4):
        r = rgba_alpha[idx]
        g = rgba_alpha[idx + 1]
        b = rgba_alpha[idx + 2]
        a = rgba_alpha[idx + 3]
        if a < 255:
            transparent_px += 1
        if a == 255:
            rgba_comp[idx] = r
            rgba_comp[idx + 1] = g
            rgba_comp[idx + 2] = b
        elif a == 0:
            rgba_comp[idx] = bg_r
            rgba_comp[idx + 1] = bg_g
            rgba_comp[idx + 2] = bg_b
        else:
            inv = 255 - a
            rgba_comp[idx] = (r * a + bg_r * inv) // 255
            rgba_comp[idx + 1] = (g * a + bg_g * inv) // 255
            rgba_comp[idx + 2] = (b * a + bg_b * inv) // 255
        rgba_comp[idx + 3] = 255

    alpha_meta = write_rgba_png(out_dir / f"{stem}-alpha.png", FB_W, FB_H, bytes(rgba_alpha))
    comp_meta = write_rgba_png(out_dir / f"{stem}-composited.png", FB_W, FB_H, bytes(rgba_comp))
    return {
        "stem": stem,
        "backdrop_rgb": f"#{bg_r:02x}{bg_g:02x}{bg_b:02x}",
        "transparent_pixels": transparent_px,
        "alpha_png": alpha_meta,
        "composited_png": comp_meta,
    }


def decode_png_rgba_rows(png_bytes: bytes) -> Tuple[int, int, List[bytes]]:
    """Decode an RGBA8 PNG (filter=0) using pure stdlib zlib/struct."""
    if len(png_bytes) < 24 or png_bytes[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Invalid PNG signature")
    pos = 8
    width = 0
    height = 0
    idat_parts: List[bytes] = []
    while pos + 8 <= len(png_bytes):
        length = struct.unpack(">I", png_bytes[pos : pos + 4])[0]
        ctype = png_bytes[pos + 4 : pos + 8]
        payload = png_bytes[pos + 8 : pos + 8 + length]
        pos += 12 + length
        if ctype == b"IHDR":
            width, height, bit_depth, color_type = struct.unpack(">IIBB", payload[:10])
            if bit_depth != 8 or color_type != 6:
                raise ValueError(f"Unsupported PNG format bit_depth={bit_depth} color_type={color_type}")
        elif ctype == b"IDAT":
            idat_parts.append(payload)
        elif ctype == b"IEND":
            break
    raw = zlib.decompress(b"".join(idat_parts))
    stride = width * 4
    rows: List[bytes] = []
    idx = 0
    for _ in range(height):
        if raw[idx] != 0:
            raise ValueError(f"Unsupported PNG row filter {raw[idx]}")
        rows.append(raw[idx + 1 : idx + 1 + stride])
        idx += 1 + stride
    return width, height, rows


def compute_png_pixel_diff(path_a: pathlib.Path, path_b: pathlib.Path) -> int:
    """Count differing RGBA pixels between two identically sized RGBA8 PNG files."""
    wa, ha, rows_a = decode_png_rgba_rows(path_a.read_bytes())
    wb, hb, rows_b = decode_png_rgba_rows(path_b.read_bytes())
    if (wa, ha) != (wb, hb):
        raise ValueError(f"PNG dimension mismatch: {(wa, ha)} vs {(wb, hb)}")
    stride = wa * 4
    return sum(
        1
        for y in range(ha)
        if rows_a[y] != rows_b[y]
        for x in range(0, stride, 4)
        if rows_a[y][x : x + 4] != rows_b[y][x : x + 4]
    )


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
        for c, cnt in counter.most_common(16)
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


def _parse_kv_ints(line: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for tok in line.split():
        if "=" not in tok:
            continue
        k, v = tok.split("=", 1)
        if re.fullmatch(r"-?\d+", v):
            out[k] = int(v)
        else:
            out[k] = v
    return out


def extract_milestones(serial_text: str) -> Dict[str, Any]:
    important_prefixes = (
        "Linux version ",
        "FX6_STAGE_A_",
        "FX6_STAGE_B_",
        "FX6_HYBRID_",
        "FX6_NATIVE_FAITHFUL_SHIM_LOADED",
        "FX6_MWF_",
        "FX6_IMCFG_",
        "FX6_INFRA_INPUT_",
        "FX3_PHY_KEY_MAP",
        "FX3_SRM3KYE5_KEY",
        "FX6_KEY_INJECT",
        "FX6_BK4_",
        "FX6_BACKUP_READ8",
        "FX6_BACKUP_MEDIA",
        "FX6_BACKUP_NREAD_MULTI",
        "FX6_BACKUP_QUERY",
        "FX6_BACKUP_WRITE",
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
        "FX6_R10_",
        "FX6_P11_",
        "FX6_R11_",
        "FX6_R12_",
        "FX6_R13_",
        "FX6_R14_",
        "FX6_R15_",
        "FX6_R16_",
        "FX6_R17_",
        "FX6_R18_",
        "FX6_R19_",
        "FX6_R20_",
        "FX6_R21_",
        "FX6_R22_",
        "FX6_R23_",
        "FX6_R24_",
        "FX6_R25_",
        "FX6_R26_",
        "FX6_R27_",
        "FX6_R28_",
        "FX6_BK4_R11_",
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
    kernel_version = ""
    last_r10_icon: Optional[Dict[str, Any]] = None
    last_p11_uipc: Optional[Dict[str, Any]] = None
    last_r11_lang: Optional[Dict[str, Any]] = None
    last_r12_lang: Optional[Dict[str, Any]] = None
    last_r13_lang: Optional[Dict[str, Any]] = None
    last_r14_lang: Optional[Dict[str, Any]] = None
    last_r15_lang: Optional[Dict[str, Any]] = None
    last_r16_lang: Optional[Dict[str, Any]] = None
    last_r17_lang: Optional[Dict[str, Any]] = None
    last_r18_lang: Optional[Dict[str, Any]] = None
    last_r19_lang: Optional[Dict[str, Any]] = None
    last_r20_lang: Optional[Dict[str, Any]] = None
    last_r21_lang: Optional[Dict[str, Any]] = None
    last_r22_lang: Optional[Dict[str, Any]] = None
    last_r23_lang: Optional[Dict[str, Any]] = None
    last_r24_lang: Optional[Dict[str, Any]] = None
    last_r25_lang: Optional[Dict[str, Any]] = None
    last_r26_lang: Optional[Dict[str, Any]] = None
    last_r27_lang: Optional[Dict[str, Any]] = None
    last_r28_lang: Optional[Dict[str, Any]] = None
    last_r28_sd: Optional[Dict[str, Any]] = None
    last_r28_jit: Optional[Dict[str, Any]] = None
    last_r28_bridge: Optional[Dict[str, Any]] = None
    r28_sd_gate_rc: Optional[int] = None
    for raw_line in serial_text.splitlines():
        line = raw_line.strip("\r")
        if not kernel_version and "Linux version " in line:
            kv_idx = line.find("Linux version ")
            kernel_version = line[kv_idx:].strip()
        if "FX6_R10_ICON_TELEMETRY " in line:
            last_r10_icon = _parse_kv_ints(line.split("FX6_R10_ICON_TELEMETRY ", 1)[1])
        elif "FX6_P11_UIPC_TELEMETRY " in line:
            last_p11_uipc = _parse_kv_ints(line.split("FX6_P11_UIPC_TELEMETRY ", 1)[1])
        elif "FX6_R11_LANG_TELEMETRY " in line:
            last_r11_lang = _parse_kv_ints(line.split("FX6_R11_LANG_TELEMETRY ", 1)[1])
        elif "FX6_R12_LANG_TELEMETRY " in line:
            last_r12_lang = _parse_kv_ints(line.split("FX6_R12_LANG_TELEMETRY ", 1)[1])
        elif "FX6_R13_LANG_TELEMETRY " in line:
            last_r13_lang = _parse_kv_ints(line.split("FX6_R13_LANG_TELEMETRY ", 1)[1])
        elif "FX6_R14_LANG_TELEMETRY " in line:
            last_r14_lang = _parse_kv_ints(line.split("FX6_R14_LANG_TELEMETRY ", 1)[1])
        elif "FX6_R15_LANG_TELEMETRY " in line:
            last_r15_lang = _parse_kv_ints(line.split("FX6_R15_LANG_TELEMETRY ", 1)[1])
        elif "FX6_R16_LANG_TELEMETRY " in line:
            last_r16_lang = _parse_kv_ints(line.split("FX6_R16_LANG_TELEMETRY ", 1)[1])
        elif "FX6_R17_LANG_TELEMETRY " in line:
            last_r17_lang = _parse_kv_ints(line.split("FX6_R17_LANG_TELEMETRY ", 1)[1])
        elif "FX6_R18_LANG_TELEMETRY " in line:
            last_r18_lang = _parse_kv_ints(line.split("FX6_R18_LANG_TELEMETRY ", 1)[1])
        elif "FX6_R19_LANG_TELEMETRY " in line:
            last_r19_lang = _parse_kv_ints(line.split("FX6_R19_LANG_TELEMETRY ", 1)[1])
        elif "FX6_R20_LANG_TELEMETRY " in line:
            last_r20_lang = _parse_kv_ints(line.split("FX6_R20_LANG_TELEMETRY ", 1)[1])
        elif "FX6_R21_LANG_TELEMETRY " in line:
            last_r21_lang = _parse_kv_ints(line.split("FX6_R21_LANG_TELEMETRY ", 1)[1])
        elif "FX6_R22_LANG_TELEMETRY " in line:
            last_r22_lang = _parse_kv_ints(line.split("FX6_R22_LANG_TELEMETRY ", 1)[1])
        elif "FX6_R23_LANG_TELEMETRY " in line:
            last_r23_lang = _parse_kv_ints(line.split("FX6_R23_LANG_TELEMETRY ", 1)[1])
        elif "FX6_R24_LANG_TELEMETRY " in line:
            last_r24_lang = _parse_kv_ints(line.split("FX6_R24_LANG_TELEMETRY ", 1)[1])
        elif "FX6_R25_LANG_TELEMETRY " in line:
            last_r25_lang = _parse_kv_ints(line.split("FX6_R25_LANG_TELEMETRY ", 1)[1])
        elif "FX6_R26_LANG_TELEMETRY " in line:
            last_r26_lang = _parse_kv_ints(line.split("FX6_R26_LANG_TELEMETRY ", 1)[1])
        elif "FX6_R27_LANG_TELEMETRY " in line:
            last_r27_lang = _parse_kv_ints(line.split("FX6_R27_LANG_TELEMETRY ", 1)[1])
        elif "FX6_R28_LANG_TELEMETRY " in line:
            last_r28_lang = _parse_kv_ints(line.split("FX6_R28_LANG_TELEMETRY ", 1)[1])
        elif "FX6_R28_SD_DUALBOOT " in line:
            last_r28_sd = _parse_kv_ints(line.split("FX6_R28_SD_DUALBOOT ", 1)[1])
        elif "FX6_R28_JIRITSU_PROBE " in line:
            last_r28_jit = _parse_kv_ints(line.split("FX6_R28_JIRITSU_PROBE ", 1)[1])
        elif "FX6_R28_STRATEGY_A_BRIDGE " in line:
            last_r28_bridge = _parse_kv_ints(line.split("FX6_R28_STRATEGY_A_BRIDGE ", 1)[1])
        elif "FX6_R28_SD_GATE_RC=" in line:
            kv = _parse_kv_ints(line)
            if isinstance(kv.get("FX6_R28_SD_GATE_RC"), int):
                r28_sd_gate_rc = kv["FX6_R28_SD_GATE_RC"]
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

    r10_telemetry: Optional[Dict[str, Any]] = None
    if last_r10_icon is not None or last_p11_uipc is not None:
        r10_telemetry = {
            "icon_blitter": last_r10_icon or {},
            "p11_uipc": last_p11_uipc or {},
        }

    r28_telemetry: Optional[Dict[str, Any]] = None
    if (
        last_r28_sd is not None
        or last_r28_jit is not None
        or last_r28_bridge is not None
        or last_r28_lang is not None
    ):
        r28_telemetry = {
            "sd_gate_rc": r28_sd_gate_rc,
            "sd_dualboot": last_r28_sd or {},
            "jiritsu_probe": last_r28_jit or {},
            "strategy_a_bridge": last_r28_bridge or {},
            "lang_telemetry": last_r28_lang or {},
        }

    return {
        "kernel_version": kernel_version,
        "prefix_counts": dict(counts),
        "total_threads_seen": len(latest_by_tid),
        "sample_threads": list(latest_by_tid.values())[:25],
        "matched_lines": matched,
        "r10_telemetry": r10_telemetry,
        "r11_telemetry": last_r11_lang,
        "r12_telemetry": last_r12_lang,
        "r13_telemetry": last_r13_lang,
        "r14_telemetry": last_r14_lang,
        "r15_telemetry": last_r15_lang,
        "r16_telemetry": last_r16_lang,
        "r17_telemetry": last_r17_lang,
        "r18_telemetry": last_r18_lang,
        "r19_telemetry": last_r19_lang,
        "r20_telemetry": last_r20_lang,
        "r21_telemetry": last_r21_lang,
        "r22_telemetry": last_r22_lang,
        "r23_telemetry": last_r23_lang,
        "r24_telemetry": last_r24_lang,
        "r25_telemetry": last_r25_lang,
        "r26_telemetry": last_r26_lang,
        "r27_telemetry": last_r27_lang,
        "r28_telemetry": r28_telemetry,
    }


def run_once(args: argparse.Namespace) -> int:
    duration = min(max(int(args.duration), 15), 105)
    run_id = args.run_id
    lang = getattr(args, "lang", "en")
    run_dir = (
        pathlib.Path(args.run_dir)
        if getattr(args, "run_dir", "")
        else (HERE / "runs" / run_id)
    )
    run_dir.mkdir(parents=True, exist_ok=True)
    serial_log = run_dir / "serial.log"
    if serial_log.exists():
        serial_log.unlink()

    owner_pid = os.getpid()
    tmp_prefix = (
        "fx6-r11"
        if args.round >= 11
        else ("fx6-r10" if args.round >= 10 else ("fx6-r9" if args.round >= 9 else ("fx6-hybrid" if args.round >= 8 else "fx6-native")))
    )
    if args.round >= 28:
        tmp_prefix = "fx6-r28"
    elif args.round >= 27:
        tmp_prefix = "fx6-r27"
    elif args.round >= 26:
        tmp_prefix = "fx6-r26"
    elif args.round >= 25:
        tmp_prefix = "fx6-r25"
    elif args.round >= 24:
        tmp_prefix = "fx6-r24"
    elif args.round >= 23:
        tmp_prefix = "fx6-r23"
    elif args.round >= 22:
        tmp_prefix = "fx6-r22"
    elif args.round >= 21:
        tmp_prefix = "fx6-r21"
    elif args.round >= 20:
        tmp_prefix = "fx6-r20"
    elif args.round >= 19:
        tmp_prefix = "fx6-r19"
    elif args.round >= 18:
        tmp_prefix = "fx6-r18"
    elif args.round >= 17:
        tmp_prefix = "fx6-r17"
    elif args.round >= 16:
        tmp_prefix = "fx6-r16"
    elif args.round >= 15:
        tmp_prefix = "fx6-r15"
    elif args.round >= 14:
        tmp_prefix = "fx6-r14"
    elif args.round >= 13:
        tmp_prefix = "fx6-r13"
    elif args.round >= 12:
        tmp_prefix = "fx6-r12"
    tmp_build = pathlib.Path(f"/private/tmp/{tmp_prefix}-build-{owner_pid}-{run_id}")
    tmp_cpio = pathlib.Path(f"/private/tmp/{tmp_prefix}-{owner_pid}-{run_id}.cpio")
    qmp_sock = pathlib.Path(f"/private/tmp/{tmp_prefix}-{owner_pid}-{run_id}-qmp.sock")
    gdb_sock = pathlib.Path(f"/private/tmp/{tmp_prefix}-{owner_pid}-{run_id}-gdb.sock")
    gpe_raw = pathlib.Path(f"/private/tmp/{tmp_prefix}-{owner_pid}-{run_id}-gpe0.raw")

    proc: Optional[subprocess.Popen[bytes]] = None
    qmp: Optional[QmpClient] = None
    t0 = time.monotonic()

    try:
        print(f"[{run_id}] Compiling launcher & shim (round={args.round} lang={lang})...", flush=True)
        launcher_bytes, shim_bytes, build_meta = build_binaries(
            tmp_build,
            fx6_round=args.round,
            restore_infra70=args.restore_infra70,
            restore_all_early=args.restore_all_early,
            reply_all_200d=args.reply_all_200d,
            initial_setting_done=args.initial_setting_done,
            shooting_mode_cine_ei=args.shooting_mode_cine_ei,
            key_seq=args.key_seq,
            key_settle_ms=args.key_settle_ms,
            lang=lang,
        )
        replacements: Dict[str, bytes] = {
            "usr/bin/appfw-launch": launcher_bytes,
            "usr/lib/libgrm-fbinit9.so": shim_bytes,
        }
        additions: Dict[str, Union[bytes, Tuple[bytes, int]]] = {}
        bk4_bytes: Optional[bytes] = None
        if args.round >= 4 and DONOR_BK4_NTSC.exists():
            bk4_bytes = read_bytes_readonly(DONOR_BK4_NTSC)
            additions["etc/fx6_chaplin_ntsc.bk4"] = (bk4_bytes, 0o100644)

        stage_a_meta: Optional[Dict[str, Any]] = None
        sd_manifest_mode = getattr(args, "sd_manifest_mode", "valid")
        if args.round >= 8:
            stage_label = (
                f"Stage-B P1..P9+Fan+P10+P11+P12+P4(RealHwSDDualBoot+libJit+StrategyA+mode={sd_manifest_mode}+lang={lang})"
                if args.round >= 28
                else (
                    f"Stage-B P1..P9+Fan+P10+P11+P12+P4(MaintenanceTab7-4LangDualSurface+UXC+Wlan+lang={lang})"
                    if args.round >= 27
                    else (
                    f"Stage-B P1..P9+Fan+P10+P11+P12+P4(TechnicalTab6-4LangDualSurface+UXC+Wlan+lang={lang})"
                    if args.round >= 26
                    else (
                        f"Stage-B P1..P9+Fan+P10+P11+P12+P4(TCMediaTab8-4LangDualSurface+UXC+Wlan+lang={lang})"
                        if args.round >= 25
                        else (
                            f"Stage-B P1..P9+Fan+P10+P11+P12+P4(ProjectTab4-4LangDualSurface+UXC+Wlan+lang={lang})"
                            if args.round >= 24
                            else (
                                f"Stage-B P1..P9+Fan+P10+P11+P12+P4(MonitoringTab5-4LangDualSurface+UXC+Wlan+lang={lang})"
                                if args.round >= 23
                                else (
                                    f"Stage-B P1..P9+Fan+P10+P11+P12+P4(PaintLookCamTab2-4LangDualSurface+UXC+Wlan+lang={lang})"
                                    if args.round >= 22
                                    else (
                                        f"Stage-B P1..P9+Fan+P10+P11+P12+P4(Audio4LangDualSurface+UXC+Wlan+lang={lang})"
                                        if args.round >= 21
                                        else (
                                            f"Stage-B P1..P9+Fan+P10+P11+P12+P4(Network4LangWF12Closure+UXC+Wlan+lang={lang})"
                                            if args.round >= 20
                                            else (
                                                f"Stage-B P1..P9+Fan+P10+P11+P12+P4(Menu11CatFullSweep+UXC+Wlan+lang={lang})"
                                                if args.round >= 19
                                                else (
                                                    f"Stage-B P1..P9+Fan+P10+P11+P12+P4(Menu8CatClosure+UXC+Wlan+lang={lang})"
                                                    if args.round >= 18
                                                    else (
                                                        f"Stage-B P1..P9+Fan+P10+P11+P12+P4(StatusFullSweep-Audio3Layer+UXC+Wlan+lang={lang})"
                                                        if args.round >= 17
                                                        else (
                                                            f"Stage-B P1..P9+Fan+P10+P11+P12+P4(StatusTabs45-TCMedia+UXC+Wlan+lang={lang})"
                                                            if args.round >= 16
                                                            else (
                                                                f"Stage-B P1..P9+Fan+P10+P11+P12+P4(MultiTab-StatusCheck-Monitoring+UXC+Wlan+lang={lang})"
                                                                if args.round >= 15
                                                                else (
                                                                    f"Stage-B P1..P9+Fan+P10+P11+P12+P4(StatusCheck-4Lang-Matrix+UXC+Wlan+lang={lang})"
                                                                    if args.round >= 14
                                                                    else (
                                                                        f"Stage-B P1..P9+Fan+P10+P11+P12+P4(4Lang-Matrix+UXC+Wlan+lang={lang})"
                                                                        if args.round >= 13
                                                                        else (
                                                                            f"Stage-B P1..P9+Fan+P10+P11+P12+P4(UXC+Wlan+lang={lang})"
                                                                            if args.round >= 12
                                                                            else (
                                                                                f"Stage-B P1..P9+Fan+P10+P11+P12(UXC+Wlan+lang={lang})"
                                                                                if args.round >= 11
                                                                                else (
                                                                                    "Stage-B P1..P9+Fan+P10+R10(UXC+P11)"
                                                                                    if args.round >= 10
                                                                                    else ("Stage-B P1..P9+Fan+P10" if args.round >= 9 else "Stage-A P1..P9+Fan")
                                                                                )
                                                                            )
                                                                        )
                                                                    )
                                                                )
                                                            )
                                                        )
                                                    )
                                                )
                                            )
                                        )
                                    )
                                )
                            )
                        )
                    )
                    )
                )
            )
            print(f"[{run_id}] Building {stage_label} + VFAT + BK4-Shadow overlay...", flush=True)
            sa_rep, sa_add, stage_a_meta = build_stage_a_overlay(
                tmp_build,
                PARENT_CPIO,
                bk4_bytes,
                enable_p10=(args.round >= 9),
                enable_r10=(args.round >= 10),
                enable_p12=(args.round >= 11),
                enable_r12=(args.round >= 12),
                enable_r13=(args.round >= 13),
                enable_r14=(args.round >= 14),
                enable_r15=(args.round >= 15),
                enable_r16=(args.round >= 16),
                enable_r17=(args.round >= 17),
                enable_r18=(args.round >= 18),
                enable_r19=(args.round >= 19),
                enable_r20=(args.round >= 20),
                enable_r21=(args.round >= 21),
                enable_r22=(args.round >= 22),
                enable_r23=(args.round >= 23),
                enable_r24=(args.round >= 24),
                enable_r25=(args.round >= 25),
                enable_r26=(args.round >= 26),
                enable_r27=(args.round >= 27),
                enable_r28=(args.round >= 28),
                sd_manifest_mode=sd_manifest_mode,
                lang=lang,
                shim_bytes=shim_bytes if args.round >= 9 else None,
            )
            replacements.update(sa_rep)
            additions.update(sa_add)

        print(f"[{run_id}] Patching temporary CPIO -> {tmp_cpio}...", flush=True)
        cpio_meta = patch_cpio(
            PARENT_CPIO,
            tmp_cpio,
            replacements,
            additions=additions or None,
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
                if (
                    "APPFW_SEGV" in txt
                    or "FX6_ABORT_BT" in txt
                    or "FX6_STAGE_A_ABORT_BEFORE_LAUNCH" in txt
                ):
                    # Wait 2s to flush remaining diagnostic output then stop early
                    time.sleep(2.0)
                    print(f"[{run_id}] Detected crash/abort signature; stopping early.", flush=True)
                    break
                if (
                    "FX6_R28_STOCK_FX3_BYPASS_EXIT" in txt
                    or "FX6_R28_FAIL_CLOSED_FALLBACK_EXIT" in txt
                ):
                    time.sleep(1.0)
                    print(f"[{run_id}] Detected clean Round 28 stock-FX3 escape-hatch exit; stopping early.", flush=True)
                    break
            time.sleep(1.0)

        serial_text = (
            serial_log.read_text(encoding="utf-8", errors="replace")
            if serial_log.exists()
            else ""
        )
        stock_fx3_exit = (
            "FX6_R28_STOCK_FX3_BYPASS_EXIT" in serial_text
            or "FX6_R28_FAIL_CLOSED_FALLBACK_EXIT" in serial_text
        )
        gpe_stats: Dict[str, Any] = (
            {"present": False, "skipped_stock_fx3_mode": True}
            if stock_fx3_exit
            else {"present": False}
        )
        png_exports: Optional[Dict[str, Any]] = None
        if not stock_fx3_exit and qmp is not None and proc.poll() is None:
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
                if args.export_png_stem and gpe_raw.exists():
                    out_dir = (
                        pathlib.Path(args.export_png_dir)
                        if args.export_png_dir
                        else DEFAULT_ASSETS_DIR
                    )
                    png_exports = export_gpe0_pngs(gpe_raw, out_dir, args.export_png_stem)
                    print(
                        f"[{run_id}] Exported PNGs -> {png_exports['alpha_png']['path']} & "
                        f"{png_exports['composited_png']['path']}",
                        flush=True,
                    )
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
            "lang": lang,
            "sd_manifest_mode": sd_manifest_mode if args.round >= 28 else None,
            "kernel_bin": str(KERNEL_BIN),
            "kernel_version": milestones["kernel_version"],
            "dtb_bin": str(GUEST_DTB),
            "restore_infra70": args.restore_infra70,
            "restore_all_early": args.restore_all_early,
            "reply_all_200d": args.reply_all_200d,
            "initial_setting_done": args.initial_setting_done,
            "shooting_mode_cine_ei": args.shooting_mode_cine_ei,
            "key_seq": args.key_seq,
            "key_settle_ms": args.key_settle_ms,
            "duration_budget_sec": duration,
            "wall_elapsed_sec": elapsed,
            "qemu_pid": proc.pid,
            "build": build_meta,
            "stage_a": stage_a_meta,
            "stage_b": stage_a_meta if args.round >= 9 else None,
            "r10_telemetry": milestones.get("r10_telemetry") if args.round >= 10 else None,
            "r11_telemetry": milestones.get("r11_telemetry") if args.round >= 11 else None,
            "r12_telemetry": milestones.get("r12_telemetry") if args.round >= 12 else None,
            "r13_telemetry": milestones.get("r13_telemetry") if args.round >= 13 else None,
            "r14_telemetry": milestones.get("r14_telemetry") if args.round >= 14 else None,
            "r15_telemetry": milestones.get("r15_telemetry") if args.round >= 15 else None,
            "r16_telemetry": milestones.get("r16_telemetry") if args.round >= 16 else None,
            "r17_telemetry": milestones.get("r17_telemetry") if args.round >= 17 else None,
            "r18_telemetry": milestones.get("r18_telemetry") if args.round >= 18 else None,
            "r19_telemetry": milestones.get("r19_telemetry") if args.round >= 19 else None,
            "r20_telemetry": milestones.get("r20_telemetry") if args.round >= 20 else None,
            "r21_telemetry": milestones.get("r21_telemetry") if args.round >= 21 else None,
            "r22_telemetry": milestones.get("r22_telemetry") if args.round >= 22 else None,
            "r23_telemetry": milestones.get("r23_telemetry") if args.round >= 23 else None,
            "r24_telemetry": milestones.get("r24_telemetry") if args.round >= 24 else None,
            "r25_telemetry": milestones.get("r25_telemetry") if args.round >= 25 else None,
            "r26_telemetry": milestones.get("r26_telemetry") if args.round >= 26 else None,
            "r27_telemetry": milestones.get("r27_telemetry") if args.round >= 27 else None,
            "r28_telemetry": milestones.get("r28_telemetry") if args.round >= 28 else None,
            "cpio": cpio_meta,
            "serial_bytes": len(serial_text.encode("utf-8", errors="replace")),
            "gpe0_readback": gpe_stats,
            "png_exports": png_exports,
            "prefix_counts": milestones["prefix_counts"],
            "total_threads_seen": milestones["total_threads_seen"],
            "sample_threads": milestones["sample_threads"],
        }
        (run_dir / "summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
        )
        print(
            f"[{run_id}] Done in {elapsed}s | kernel={milestones['kernel_version']!r} "
            f"| threads={milestones['total_threads_seen']} "
            f"| gpe0_nz={gpe0_nz if (gpe0_nz := gpe_stats.get('nonzero_pixels')) is not None else None} unique_colors={gpe_stats.get('unique_colors')} "
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
                proc.terminate()
                proc.wait(timeout=4.0)
            except Exception:
                try:
                    proc.kill()
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
    ap.add_argument("--round", type=int, choices=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28], required=True)
    ap.add_argument("--lang", type=str, choices=["en", "english", "schinese", "tchinese", "japanese"], default="en")
    ap.add_argument("--sd-manifest-mode", type=str, choices=["valid", "absent", "tampered"], default="valid")
    ap.add_argument("--duration", type=int, default=55)
    ap.add_argument("--restore-infra70", type=int, choices=[0, 1], default=None)
    ap.add_argument("--restore-all-early", type=int, choices=[0, 1], default=None)
    ap.add_argument("--reply-all-200d", type=int, choices=[0, 1], default=None)
    ap.add_argument("--initial-setting-done", type=int, choices=[0, 1], default=0)
    ap.add_argument("--shooting-mode-cine-ei", type=int, choices=[0, 1], default=0)
    ap.add_argument("--key-seq", type=str, default="")
    ap.add_argument("--key-settle-ms", type=int, default=1500)
    ap.add_argument("--export-png-stem", type=str, default="")
    ap.add_argument("--export-png-dir", type=str, default="")
    ap.add_argument("--run-dir", type=str, default="")
    args = ap.parse_args()
    r5_default = 1 if args.round >= 5 else 0
    if args.restore_infra70 is None:
        args.restore_infra70 = r5_default
    if args.restore_all_early is None:
        args.restore_all_early = r5_default
    if args.reply_all_200d is None:
        args.reply_all_200d = r5_default
    return run_once(args)


if __name__ == "__main__":
    sys.exit(main())
