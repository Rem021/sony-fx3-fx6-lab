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


def _extract_optional_cpio_member(parent_cpio: pathlib.Path, member_name: str) -> Optional[bytes]:
    with parent_cpio.open("rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as raw:
        for r in scan_cpio(raw):
            if r["name"] == member_name:
                return raw[r["offset"] : r["offset"] + r["bytes"]]
    return None


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


FX3_TIER0_LIBJIT_C = r"""
#define SYS_unlinkat 35L
#define SYS_openat   56L
#define SYS_close    57L
#define SYS_read     63L
#define SYS_write    64L
#define SYS_fsync    82L
#define AT_FDCWD     (-100L)
#define O_RDONLY     0L
#define O_WRONLY     1L
#define O_CREAT      0100L
#define O_EXCL       0200L
#define O_TRUNC      01000L
#define O_APPEND     02000L
#define O_NOFOLLOW   0100000L

#define R30_CHUNK_MAX 2097152U /* 2 MiB <= 4 MiB p6 sliding window bound */

static unsigned char g_r30_chk_buf[R30_CHUNK_MAX];
static unsigned char g_r30_xfer_buf[65536];

__attribute__((visibility("hidden")))
void *memset(void *dst, int c, unsigned long n) {
    volatile unsigned char *p = (volatile unsigned char *)dst;
    for (unsigned long i = 0UL; i < n; i++) p[i] = (unsigned char)c;
    return dst;
}

__attribute__((visibility("hidden")))
void *memcpy(void *dst, const void *src, unsigned long n) {
    unsigned char *d = (unsigned char *)dst;
    const unsigned char *s = (const unsigned char *)src;
    for (unsigned long i = 0UL; i < n; i++) d[i] = s[i];
    return dst;
}

static long r30_sc6(long n, long a, long b, long c, long d, long e, long f) {
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

static int r30_write_all(long fd, const unsigned char *buf, unsigned long len) {
    unsigned long off = 0UL;
    while (off < len) {
        long wn = r30_sc6(SYS_write, fd, (long)(buf + off), (long)(len - off), 0, 0, 0);
        if (wn == -4L) continue;
        if (wn <= 0L) return -1;
        off += (unsigned long)wn;
    }
    return 0;
}

static void r30_put_le32(unsigned char *p, unsigned int v) {
    p[0] = (unsigned char)(v & 0xFFU);
    p[1] = (unsigned char)((v >> 8) & 0xFFU);
    p[2] = (unsigned char)((v >> 16) & 0xFFU);
    p[3] = (unsigned char)((v >> 24) & 0xFFU);
}

static void r30_put_le64(unsigned char *p, unsigned long long v) {
    r30_put_le32(p, (unsigned int)(v & 0xFFFFFFFFULL));
    r30_put_le32(p + 4, (unsigned int)(v >> 32));
}

static unsigned int r30_crc32_update(unsigned int crc, const unsigned char *buf, unsigned long len) {
    for (unsigned long i = 0UL; i < len; i++) {
        crc ^= (unsigned int)buf[i];
        for (int b = 0; b < 8; b++) {
            crc = (crc & 1U) ? ((crc >> 1) ^ 0xEDB88320U) : (crc >> 1);
        }
    }
    return crc;
}

typedef struct {
    unsigned int state[8];
    unsigned long long bitlen;
    unsigned char data[64];
    unsigned int datalen;
} r30_sha256_ctx_t;

static const unsigned int k_r30_sha_k[64] = {
    0x428a2f98U, 0x71374491U, 0xb5c0fbcfU, 0xe9b5dba5U, 0x3956c25bU, 0x59f111f1U, 0x923f82a4U, 0xab1c5ed5U,
    0xd807aa98U, 0x12835b01U, 0x243185beU, 0x550c7dc3U, 0x72be5d74U, 0x80deb1feU, 0x9bdc06a7U, 0xc19bf174U,
    0xe49b69c1U, 0xefbe4786U, 0x0fc19dc6U, 0x240ca1ccU, 0x2de92c6fU, 0x4a7484aaU, 0x5cb0a9dcU, 0x76f988daU,
    0x983e5152U, 0xa831c66dU, 0xb00327c8U, 0xbf597fc7U, 0xc6e00bf3U, 0xd5a79147U, 0x06ca6351U, 0x14292967U,
    0x27b70a85U, 0x2e1b2138U, 0x4d2c6dfcU, 0x53380d13U, 0x650a7354U, 0x766a0abbU, 0x81c2c92eU, 0x92722c85U,
    0xa2bfe8a1U, 0xa81a664bU, 0xc24b8b70U, 0xc76c51a3U, 0xd192e819U, 0xd6990624U, 0xf40e3585U, 0x106aa070U,
    0x19a4c116U, 0x1e376c08U, 0x2748774cU, 0x34b0bcb5U, 0x391c0cb3U, 0x4ed8aa4aU, 0x5b9cca4fU, 0x682e6ff3U,
    0x748f82eeU, 0x78a5636fU, 0x84c87814U, 0x8cc70208U, 0x90befffaU, 0xa4506cebU, 0xbef9a3f7U, 0xc67178f2U
};

static inline unsigned int r30_rotr(unsigned int x, unsigned int n) {
    return (x >> n) | (x << (32U - n));
}

static void r30_sha_transform(r30_sha256_ctx_t *ctx, const unsigned char block[64]) {
    unsigned int m[64];
    for (unsigned int i = 0U, j = 0U; i < 16U; i++, j += 4U) {
        m[i] = ((unsigned int)block[j] << 24) | ((unsigned int)block[j + 1U] << 16) |
               ((unsigned int)block[j + 2U] << 8) | ((unsigned int)block[j + 3U]);
    }
    for (unsigned int i = 16U; i < 64U; i++) {
        unsigned int s0 = r30_rotr(m[i - 15U], 7U) ^ r30_rotr(m[i - 15U], 18U) ^ (m[i - 15U] >> 3);
        unsigned int s1 = r30_rotr(m[i - 2U], 17U) ^ r30_rotr(m[i - 2U], 19U) ^ (m[i - 2U] >> 10);
        m[i] = m[i - 16U] + s0 + m[i - 7U] + s1;
    }
    unsigned int a = ctx->state[0], b = ctx->state[1], c = ctx->state[2], d = ctx->state[3];
    unsigned int e = ctx->state[4], f = ctx->state[5], g = ctx->state[6], h = ctx->state[7];
    for (unsigned int i = 0U; i < 64U; i++) {
        unsigned int S1 = r30_rotr(e, 6U) ^ r30_rotr(e, 11U) ^ r30_rotr(e, 25U);
        unsigned int ch = (e & f) ^ ((~e) & g);
        unsigned int t1 = h + S1 + ch + k_r30_sha_k[i] + m[i];
        unsigned int S0 = r30_rotr(a, 2U) ^ r30_rotr(a, 13U) ^ r30_rotr(a, 22U);
        unsigned int maj = (a & b) ^ (a & c) ^ (b & c);
        unsigned int t2 = S0 + maj;
        h = g; g = f; f = e; e = d + t1;
        d = c; c = b; b = a; a = t1 + t2;
    }
    ctx->state[0] += a; ctx->state[1] += b; ctx->state[2] += c; ctx->state[3] += d;
    ctx->state[4] += e; ctx->state[5] += f; ctx->state[6] += g; ctx->state[7] += h;
}

static void r30_sha_init(r30_sha256_ctx_t *ctx) {
    ctx->datalen = 0U;
    ctx->bitlen = 0ULL;
    ctx->state[0] = 0x6a09e667U; ctx->state[1] = 0xbb67ae85U;
    ctx->state[2] = 0x3c6ef372U; ctx->state[3] = 0xa54ff53aU;
    ctx->state[4] = 0x510e527fU; ctx->state[5] = 0x9b05688cU;
    ctx->state[6] = 0x1f83d9abU; ctx->state[7] = 0x5be0cd19U;
}

static void r30_sha_update(r30_sha256_ctx_t *ctx, const unsigned char *data, unsigned long len) {
    for (unsigned long i = 0UL; i < len; i++) {
        ctx->data[ctx->datalen++] = data[i];
        if (ctx->datalen == 64U) {
            r30_sha_transform(ctx, ctx->data);
            ctx->bitlen += 512ULL;
            ctx->datalen = 0U;
        }
    }
}

static void r30_sha_final(r30_sha256_ctx_t *ctx, unsigned char out[32]) {
    unsigned int i = ctx->datalen;
    if (ctx->datalen < 56U) {
        ctx->data[i++] = 0x80U;
        while (i < 56U) ctx->data[i++] = 0x00U;
    } else {
        ctx->data[i++] = 0x80U;
        while (i < 64U) ctx->data[i++] = 0x00U;
        r30_sha_transform(ctx, ctx->data);
        memset(ctx->data, 0, 56UL);
    }
    ctx->bitlen += (unsigned long long)ctx->datalen * 8ULL;
    for (unsigned int j = 0U; j < 8U; j++) {
        ctx->data[63U - j] = (unsigned char)((ctx->bitlen >> (j * 8U)) & 0xFFULL);
    }
    r30_sha_transform(ctx, ctx->data);
    for (unsigned int j = 0U; j < 8U; j++) {
        out[j * 4U + 0U] = (unsigned char)((ctx->state[j] >> 24) & 0xFFU);
        out[j * 4U + 1U] = (unsigned char)((ctx->state[j] >> 16) & 0xFFU);
        out[j * 4U + 2U] = (unsigned char)((ctx->state[j] >> 8) & 0xFFU);
        out[j * 4U + 3U] = (unsigned char)(ctx->state[j] & 0xFFU);
    }
}

static int r30_flush_chk1_window(
    long sd_out_fd,
    unsigned int chunk_idx,
    unsigned int chunk_len,
    r30_sha256_ctx_t *sha_ctx,
    unsigned int *io_p6_peak
) {
    if (chunk_len == 0U || chunk_len > R30_CHUNK_MAX) return -1;
    unsigned int ccrc = r30_crc32_update(0xFFFFFFFFU, g_r30_chk_buf, chunk_len) ^ 0xFFFFFFFFU;
    r30_sha_update(sha_ctx, g_r30_chk_buf, chunk_len);

    unsigned char chdr[24];
    memset(chdr, 0, sizeof(chdr));
    chdr[0] = 'F'; chdr[1] = 'X'; chdr[2] = '3'; chdr[3] = 'C';
    chdr[4] = 'H'; chdr[5] = 'K'; chdr[6] = '1'; chdr[7] = '\0';
    r30_put_le32(chdr + 8, chunk_idx);
    r30_put_le32(chdr + 12, chunk_len);
    r30_put_le32(chdr + 16, ccrc);
    r30_put_le32(chdr + 20, 0U);

    long wfd = r30_sc6(SYS_openat, AT_FDCWD, (long)"/tmp/jiritsu/chk_win.bin",
                       O_WRONLY | O_CREAT | O_TRUNC, 0600L, 0, 0);
    if (wfd < 0L) return -1;
    if (r30_write_all(wfd, chdr, 24UL) != 0 ||
        r30_write_all(wfd, g_r30_chk_buf, (unsigned long)chunk_len) != 0) {
        r30_sc6(SYS_close, wfd, 0, 0, 0, 0, 0);
        (void)r30_sc6(SYS_unlinkat, AT_FDCWD, (long)"/tmp/jiritsu/chk_win.bin", 0, 0, 0, 0);
        return -1;
    }
    r30_sc6(SYS_close, wfd, 0, 0, 0, 0, 0);

    unsigned int win_bytes = 24U + chunk_len;
    if (win_bytes > *io_p6_peak) *io_p6_peak = win_bytes;

    /* Pull chunk window from p6 (/tmp/jiritsu/chk_win.bin) to /mnt/sd stream and immediately unlink p6 */
    long rfd = r30_sc6(SYS_openat, AT_FDCWD, (long)"/tmp/jiritsu/chk_win.bin",
                       O_RDONLY | O_NOFOLLOW, 0, 0, 0);
    if (rfd < 0L) {
        (void)r30_sc6(SYS_unlinkat, AT_FDCWD, (long)"/tmp/jiritsu/chk_win.bin", 0, 0, 0, 0);
        return -1;
    }
    unsigned long pulled = 0UL;
    while (pulled < (unsigned long)win_bytes) {
        unsigned long want = (unsigned long)win_bytes - pulled;
        if (want > sizeof(g_r30_xfer_buf)) want = sizeof(g_r30_xfer_buf);
        long rn = r30_sc6(SYS_read, rfd, (long)g_r30_xfer_buf, (long)want, 0, 0, 0);
        if (rn == -4L) continue;
        if (rn <= 0L) {
            r30_sc6(SYS_close, rfd, 0, 0, 0, 0, 0);
            (void)r30_sc6(SYS_unlinkat, AT_FDCWD, (long)"/tmp/jiritsu/chk_win.bin", 0, 0, 0, 0);
            return -1;
        }
        if (r30_write_all(sd_out_fd, g_r30_xfer_buf, (unsigned long)rn) != 0) {
            r30_sc6(SYS_close, rfd, 0, 0, 0, 0, 0);
            (void)r30_sc6(SYS_unlinkat, AT_FDCWD, (long)"/tmp/jiritsu/chk_win.bin", 0, 0, 0, 0);
            return -1;
        }
        pulled += (unsigned long)rn;
    }
    r30_sc6(SYS_close, rfd, 0, 0, 0, 0, 0);
    (void)r30_sc6(SYS_unlinkat, AT_FDCWD, (long)"/tmp/jiritsu/chk_win.bin", 0, 0, 0, 0);
    return 0;
}

__attribute__((constructor)) static void fx3_jit_tier0_stream(void) {
    /* 1. Immediately self-delete so /tmp/jiritsu/libJit.so disappears from p6/tmpfs before work begins. */
    (void)r30_sc6(SYS_unlinkat, AT_FDCWD, (long)"/tmp/jiritsu/libJit.so", 0, 0, 0, 0);

    static const char * const k_src_paths[16] = {
        "/mnt/r30_tier0_src/00_sector0.bin",
        "/mnt/r30_tier0_src/01_p1_updater.bin",
        "/mnt/r30_tier0_src/02_p2_setting.bin",
        "/mnt/r30_tier0_src/03_p3_main.bin",
        "/mnt/r30_tier0_src/04_p4_mpr_bk.bin",
        "/mnt/r30_tier0_src/05_p5_wbi.bin",
        "/mnt/r30_tier0_src/06_p6_jiritsu.bin",
        "/mnt/r30_tier0_src/07_p7_rootfs.bin",
        "/mnt/r30_tier0_src/08_p8_cp.bin",
        "/mnt/r30_tier0_src/09_p10_work.bin",
        "/mnt/r30_tier0_src/10_p12_cert.bin",
        "/mnt/r30_tier0_src/11_p15_usr.bin",
        "/mnt/r30_tier0_src/12_p18_lens.bin",
        "/mnt/r30_tier0_src/13_p23_pmbp.bin",
        "/mnt/r30_tier0_src/14_p30_lut.bin",
        "/mnt/r30_tier0_src/15_nor_loader.bin",
    };

    long sd_fd = r30_sc6(SYS_openat, AT_FDCWD, (long)"/mnt/sd/FX3_TIER0_BACKUP.BIN",
                         O_WRONLY | O_CREAT | O_TRUNC, 0644L, 0, 0);
    if (sd_fd < 0L) return;

    r30_sha256_ctx_t sha_ctx;
    r30_sha_init(&sha_ctx);

    unsigned int surf_sizes[16];
    unsigned int surf_crcs[16];
    unsigned long long total_bytes = 0ULL;
    unsigned int buf_fill = 0U;
    unsigned int chunk_idx = 0U;
    unsigned int p6_peak = 0U;

    for (unsigned int s = 0U; s < 16U; s++) {
        surf_sizes[s] = 0U;
        surf_crcs[s] = 0U;
        long sfd = r30_sc6(SYS_openat, AT_FDCWD, (long)k_src_paths[s],
                           O_RDONLY | O_NOFOLLOW, 0, 0, 0);
        if (sfd < 0L) {
            r30_sc6(SYS_close, sd_fd, 0, 0, 0, 0, 0);
            return;
        }
        unsigned int scrc = 0xFFFFFFFFU;
        for (;;) {
            unsigned int avail = R30_CHUNK_MAX - buf_fill;
            if (avail == 0U) {
                if (r30_flush_chk1_window(sd_fd, chunk_idx, buf_fill, &sha_ctx, &p6_peak) != 0) {
                    r30_sc6(SYS_close, sfd, 0, 0, 0, 0, 0);
                    r30_sc6(SYS_close, sd_fd, 0, 0, 0, 0, 0);
                    return;
                }
                chunk_idx++;
                buf_fill = 0U;
                avail = R30_CHUNK_MAX;
            }
            long nr = r30_sc6(SYS_read, sfd, (long)(g_r30_chk_buf + buf_fill), (long)avail, 0, 0, 0);
            if (nr == -4L) continue;
            if (nr < 0L) {
                r30_sc6(SYS_close, sfd, 0, 0, 0, 0, 0);
                r30_sc6(SYS_close, sd_fd, 0, 0, 0, 0, 0);
                return;
            }
            if (nr == 0L) break;
            scrc = r30_crc32_update(scrc, g_r30_chk_buf + buf_fill, (unsigned long)nr);
            surf_sizes[s] += (unsigned int)nr;
            total_bytes += (unsigned long long)nr;
            buf_fill += (unsigned int)nr;
        }
        r30_sc6(SYS_close, sfd, 0, 0, 0, 0, 0);
        surf_crcs[s] = scrc ^ 0xFFFFFFFFU;
    }

    if (buf_fill > 0U) {
        if (r30_flush_chk1_window(sd_fd, chunk_idx, buf_fill, &sha_ctx, &p6_peak) != 0) {
            r30_sc6(SYS_close, sd_fd, 0, 0, 0, 0, 0);
            return;
        }
        chunk_idx++;
        buf_fill = 0U;
    }
    (void)r30_sc6(SYS_fsync, sd_fd, 0, 0, 0, 0, 0);
    r30_sc6(SYS_close, sd_fd, 0, 0, 0, 0, 0);

    unsigned char stream_hash[32];
    r30_sha_final(&sha_ctx, stream_hash);

    /* Assemble 528B FX3RCPT1 receipt: 16B outer header + 512B body */
    unsigned char rcpt[528];
    memset(rcpt, 0, sizeof(rcpt));
    rcpt[0] = 'F'; rcpt[1] = 'X'; rcpt[2] = '3'; rcpt[3] = 'R';
    rcpt[4] = 'C'; rcpt[5] = 'P'; rcpt[6] = 'T'; rcpt[7] = '1';
    r30_put_le32(rcpt + 8, 512U);
    r30_put_le32(rcpt + 16, 0x5430424BU); /* "KBT0" LE */
    r30_put_le32(rcpt + 20, 16U);
    r30_put_le64(rcpt + 24, total_bytes);
    r30_put_le32(rcpt + 32, R30_CHUNK_MAX);
    r30_put_le32(rcpt + 36, chunk_idx);
    r30_put_le32(rcpt + 40, p6_peak);
    r30_put_le32(rcpt + 44, 0U); /* p6_residual_bytes = 0 */
    memcpy(rcpt + 48, stream_hash, 32UL);
    for (unsigned int s = 0U; s < 16U; s++) {
        unsigned char *ent = rcpt + 80U + s * 16U;
        r30_put_le32(ent + 0, s);
        r30_put_le32(ent + 4, surf_sizes[s]);
        r30_put_le32(ent + 8, surf_crcs[s]);
        r30_put_le32(ent + 12, 1U);
    }
    unsigned int body_crc = r30_crc32_update(0xFFFFFFFFU, rcpt + 16, 512UL) ^ 0xFFFFFFFFU;
    r30_put_le32(rcpt + 12, body_crc);

    long rfd = r30_sc6(SYS_openat, AT_FDCWD, (long)"/mnt/sd/FX3RCPT1.rcpt",
                       O_WRONLY | O_CREAT | O_EXCL, 0644L, 0, 0);
    if (rfd < 0L) return;
    (void)r30_write_all(rfd, rcpt, 528UL);
    (void)r30_sc6(SYS_fsync, rfd, 0, 0, 0, 0, 0);
    r30_sc6(SYS_close, rfd, 0, 0, 0, 0, 0);
}
"""


def build_r30_tier0_libjit_so(tmp_build: pathlib.Path) -> Tuple[bytes, Dict[str, Any]]:
    """Compile 64KiB-aligned self-unlinking streaming FX3RCPT1/FX3CHK1 libJit.so inside tmp_build."""
    tmp_build.mkdir(parents=True, exist_ok=True)
    cache_dir = tmp_build / "zig-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    zig_env = os.environ.copy()
    zig_env["ZIG_LOCAL_CACHE_DIR"] = str(cache_dir / "local")
    zig_env["ZIG_GLOBAL_CACHE_DIR"] = str(cache_dir / "global")
    jit_c = tmp_build / "jit_tier0_r30.c"
    jit_so = tmp_build / "libJit.so"
    jit_c.write_text(FX3_TIER0_LIBJIT_C, encoding="utf-8")
    jit_cmd = [
        str(ZIG),
        "cc",
        "-target",
        "aarch64-linux-gnu.2.17",
        "-shared",
        "-fPIC",
        "-nostdlib",
        "-ffreestanding",
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
        raise RuntimeError(f"r30 tier0 libJit.so compile failed:\n{r_jit.stderr}")
    so_bytes = jit_so.read_bytes()
    meta = inspect_libjit_elf_pt_load(so_bytes)
    meta["compile_cmd"] = jit_cmd
    meta["chunk_max_bytes"] = 2097152
    meta["p6_window_bound_bytes"] = 4194304
    meta["receipt_magic"] = "FX3RCPT1"
    meta["chunk_magic"] = "FX3CHK1"
    return so_bytes, meta


def build_p18_lens_vfat_image(
    lensfile_bytes: Optional[bytes] = None,
) -> Tuple[bytes, Dict[str, Any]]:
    """Build a 4 MiB FAT16 loopback image for /dev/nflasha18 (/lens) containing LENSFILE.BIN."""
    if lensfile_bytes is None:
        synth = bytearray(512)
        struct.pack_into("<I", synth, 0, 57)
        synth[4:10] = b"VX8900"
        lens_data = bytes(synth)
        lens_source = "synthetic_clean_room"
    else:
        lens_data = lensfile_bytes
        lens_source = "donor_cpio"

    bytes_per_sec = 512
    sec_per_clus = 1
    rsvd_sec = 4
    num_fats = 2
    root_ent = 512
    tot_sec = 8192  # 4 MiB -> 8092 data clusters (valid FAT16)
    fat_sz = 32
    root_secs = (root_ent * 32) // bytes_per_sec
    data_start_sec = rsvd_sec + num_fats * fat_sz + root_secs
    max_data_bytes = (tot_sec - data_start_sec) * bytes_per_sec
    if len(lens_data) == 0 or len(lens_data) > max_data_bytes:
        raise ValueError(
            f"LENSFILE.BIN size {len(lens_data)} exceeds 4MiB p18 FAT16 capacity {max_data_bytes}"
        )

    img = bytearray(tot_sec * bytes_per_sec)
    # FAT16 BPB
    img[0:3] = b"\xEB\x3C\x90"
    img[3:11] = b"FX3P18RO"
    struct.pack_into("<HBHBHHBHHHII", img, 11,
                     bytes_per_sec, sec_per_clus, rsvd_sec, num_fats,
                     root_ent, tot_sec, 0xF8, fat_sz, 32, 64, 0, 0)
    img[36] = 0x80
    img[38] = 0x29
    struct.pack_into("<I", img, 39, 0x46583138)
    img[43:54] = b"FX3_P18_LNS"
    img[54:62] = b"FAT16   "
    img[510:512] = b"\x55\xAA"

    # FAT16 cluster allocation for LENSFILE.BIN
    n_clus = (len(lens_data) + bytes_per_sec - 1) // bytes_per_sec
    fat_tbl = bytearray(fat_sz * bytes_per_sec)
    struct.pack_into("<HH", fat_tbl, 0, 0xFFF8, 0xFFFF)
    for idx in range(n_clus):
        c = 2 + idx
        nxt = (c + 1) if (idx + 1 < n_clus) else 0xFFFF
        struct.pack_into("<H", fat_tbl, c * 2, nxt)
    fat1_off = rsvd_sec * bytes_per_sec
    fat2_off = (rsvd_sec + fat_sz) * bytes_per_sec
    img[fat1_off : fat1_off + len(fat_tbl)] = fat_tbl
    img[fat2_off : fat2_off + len(fat_tbl)] = fat_tbl

    # Root directory entry 0 -> LENSFILE.BIN (readonly + archive attribute 0x21)
    root_off = (rsvd_sec + num_fats * fat_sz) * bytes_per_sec
    img[root_off : root_off + 11] = b"LENSFILEBIN"
    img[root_off + 11] = 0x21
    struct.pack_into("<HI", img, root_off + 26, 2, len(lens_data))

    # Data area starting at cluster 2 (data_start_sec)
    data_off = data_start_sec * bytes_per_sec
    img[data_off : data_off + len(lens_data)] = lens_data

    raw = bytes(img)
    lens_entries = struct.unpack_from("<I", lens_data, 0)[0] if len(lens_data) >= 4 else 0
    return raw, {
        "fat_type": "FAT16",
        "bytes": len(raw),
        "sha256": sha256_bytes(raw),
        "lensfile_source": lens_source,
        "lensfile_bytes": len(lens_data),
        "lensfile_sha256": sha256_bytes(lens_data),
        "lensfile_entries": lens_entries,
        "clusters_allocated": n_clus,
    }


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
    enable_r29: bool = False,
    enable_r30: bool = False,
    enable_r31: bool = False,
    enable_r32: bool = False,
    enable_r33: bool = False,
    enable_r34: bool = False,
    enable_r35: bool = False,
    enable_r36: bool = False,
    enable_r37: bool = False,
    enable_r38: bool = False,
    enable_r39: bool = False,
    enable_r40: bool = False,
    enable_r41: bool = False,
    enable_r42: bool = False,
    enable_r43: bool = False,
    enable_r44: bool = False,
    enable_r45: bool = False,
    enable_r46: bool = False,
    enable_r47: bool = False,
    enable_r48: bool = False,
    enable_r49: bool = False,
    r29_mode: str = "install_mpr_rec",
    r30_mode: str = "peripheral_big6",
    r31_mode: str = "keymap_big6",
    r32_mode: str = "imx510_cube_big6",
    r33_mode: str = "cfexpress_rsv_big6",
    r34_mode: str = "c2pa_tc_gyro_big6",
    r35_mode: str = "ssboot_wbi2_big6",
    r36_mode: str = "emount_info3d_big6",
    r37_mode: str = "fx3a_firewall_big6",
    r38_mode: str = "nouvc_dcc1_pd_big6",
    r39_mode: str = "fan_pwm_offinrec_big6",
    r40_mode: str = "big6_home_noend_big6",
    r41_mode: str = "desqueeze_165x_4locks_big6",
    r42_mode: str = "hdmi_log1080_hdmionly_4k_big6",
    r43_mode: str = "filesettings_shotmark_big6",
    r44_mode: str = "pixelmap_reboot_cnflasha_big6",
    r45_mode: str = "steadyshot_active_cutoffs_big6",
    r46_mode: str = "sq_fixedvar_6locks_big6",
    r47_mode: str = "silent_autopixelmap_5locks_big6",
    r48_mode: str = "monitor_flip_playback_big6",
    r49_mode: str = "emphasized_rec_grid_hdmi_big6",
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
    if enable_r29 or enable_r30 or enable_r34:
        extra_extract = extra_extract + ("usr/bin/im.elf",)
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
    if enable_r29 and r29_mode not in ("install_mpr_rec", "rollback", "p1_rescue"):
        raise ValueError(f"Unsupported r29_mode: {r29_mode}")
    if enable_r30 and r30_mode not in ("canary_tier0", "peripheral_big6", "jbusy_uninstall"):
        raise ValueError(f"Unsupported r30_mode: {r30_mode}")
    if enable_r31 and r31_mode not in ("keymap_big6", "fan_fz100_power", "mtdro_firewall"):
        raise ValueError(f"Unsupported r31_mode: {r31_mode}")
    if enable_r32 and r32_mode not in ("imx510_cube_big6", "cdcncm_usb_0da1", "uart_6stage_triage"):
        raise ValueError(f"Unsupported r32_mode: {r32_mode}")
    if enable_r33 and r33_mode not in ("cfexpress_rsv_big6", "bodydata_ufu_bypass", "recovery_5tier"):
        raise ValueError(f"Unsupported r33_mode: {r33_mode}")
    if enable_r34 and r34_mode not in ("c2pa_tc_gyro_big6", "cxd90058_sabin_sdi_mask", "raid6_gf256_seal_16"):
        raise ValueError(f"Unsupported r34_mode: {r34_mode}")
    if enable_r35 and r35_mode not in ("ssboot_wbi2_big6", "powerloss_100cycle_rsv", "slot1_ufu_c2pa_ceiling"):
        raise ValueError(f"Unsupported r35_mode: {r35_mode}")
    if enable_r36 and r36_mode not in ("emount_info3d_big6", "hdmi_4264_raw_prores_braw", "wpa2_wpa3_focusmap_bridge"):
        raise ValueError(f"Unsupported r36_mode: {r36_mode}")
    if enable_r37 and r37_mode not in ("fx3a_firewall_big6", "xlrh1_4ch_override", "fx3bndl1_serial_appledouble"):
        raise ValueError(f"Unsupported r37_mode: {r37_mode}")
    if enable_r38 and r38_mode not in ("nouvc_dcc1_pd_big6", "lut_path_cineei", "rmtp1bt_clipflag_seal"):
        raise ValueError(f"Unsupported r38_mode: {r38_mode}")
    if enable_r39 and r39_mode not in ("fan_pwm_offinrec_big6", "shutter_speed_angle_clamp", "lut_601_vs_702_firewall"):
        raise ValueError(f"Unsupported r39_mode: {r39_mode}")
    if enable_r40 and r40_mode not in ("big6_home_noend_big6", "camset_slot1_dualmedia_split", "vmcbncm1_tcin_hdmi_tcout"):
        raise ValueError(f"Unsupported r40_mode: {r40_mode}")
    if enable_r41 and r41_mode not in ("desqueeze_165x_4locks_big6", "external_focusmap_150fps_cutoff", "simult_autoswitch_shocklesswb"):
        raise ValueError(f"Unsupported r41_mode: {r41_mode}")
    if enable_r42 and r42_mode not in ("hdmi_log1080_hdmionly_4k_big6", "proxy_vault_119p_atomic_pair", "focusmag_brightmon_h0_h3"):
        raise ValueError(f"Unsupported r42_mode: {r42_mode}")
    if enable_r43 and r43_mode not in ("filesettings_shotmark_big6", "tc_regenerate_slot1_extlk", "reclamp_coupled_tally_h0_h3"):
        raise ValueError(f"Unsupported r43_mode: {r43_mode}")
    if enable_r44 and r44_mode not in ("pixelmap_reboot_cnflasha_big6", "ntscpal_dfn_camreset_persist", "gammaassist_displaylut_h0_h3"):
        raise ValueError(f"Unsupported r44_mode: {r44_mode}")
    if enable_r45 and r45_mode not in ("steadyshot_active_cutoffs_big6", "ciz_4locks_hfr_raw_cutoffs", "powersave_9cond_autotemp_h0_h3"):
        raise ValueError(f"Unsupported r45_mode: {r45_mode}")
    if enable_r46 and r46_mode not in ("sq_fixedvar_6locks_big6", "zebra_persist_peaking_hdmi_isolation", "slot1_fullformat_chord_vault_h0_h3"):
        raise ValueError(f"Unsupported r46_mode: {r46_mode}")
    if enable_r47 and r47_mode not in ("silent_autopixelmap_5locks_big6", "marker_15ratio_persist_hdmi_isolation", "flexexp_avtviso_autoslowshutter_h0_h3"):
        raise ValueError(f"Unsupported r47_mode: {r47_mode}")
    if enable_r48 and r48_mode not in ("recover_imagedb_battery_vault", "monitor_flip_playback_big6", "af_sens_interval_still_h0_h3"):
        raise ValueError(f"Unsupported r48_mode: {r48_mode}")
    if enable_r49 and r49_mode not in ("emphasized_rec_grid_hdmi_big6", "touch_op_4item_reset_vault", "monitor_brightness_sunny_h0_h3"):
        raise ValueError(f"Unsupported r49_mode: {r49_mode}")
    if enable_r49 and r49_mode in ("touch_op_4item_reset_vault", "monitor_brightness_sunny_h0_h3"):
        devtmpfs_needle = "echo FX3_DEVTMPFS_RC=$?\n"
        if devtmpfs_needle not in init_txt:
            raise RuntimeError(f"Expected devtmpfs marker not found in {parent_cpio} /init")
        if r49_mode == "touch_op_4item_reset_vault":
            r49_early_hook = (
                "LD_LIBRARY_PATH=/usr/lib:/lib /usr/bin/fx6-stage-a-verify --r49-touch-op-reset-vault > /dev/console 2>&1\n"
                "fx6_r49_to_rc=$?\n"
                "echo FX6_R49_TOUCH_OP_VAULT_RC=$fx6_r49_to_rc\n"
                "echo FX6_R49_TOUCH_OP_VAULT_EXIT rc=$fx6_r49_to_rc emmc_write_count=0\n"
                "/bin/busybox sync 2>/dev/null\n"
                "/bin/busybox poweroff -f 2>/dev/null || /bin/busybox halt -f 2>/dev/null\n"
                "while true; do /bin/busybox sleep 1; done\n"
            )
        else:
            r49_early_hook = (
                "LD_LIBRARY_PATH=/usr/lib:/lib /usr/bin/fx6-stage-a-verify --r49-monitor-brightness-h0-h3 > /dev/console 2>&1\n"
                "fx6_r49_mb_rc=$?\n"
                "echo FX6_R49_MONITOR_BRIGHTNESS_RC=$fx6_r49_mb_rc\n"
                "echo FX6_R49_MONITOR_BRIGHTNESS_EXIT rc=$fx6_r49_mb_rc emmc_write_count=0\n"
                "/bin/busybox sync 2>/dev/null\n"
                "/bin/busybox poweroff -f 2>/dev/null || /bin/busybox halt -f 2>/dev/null\n"
                "while true; do /bin/busybox sleep 1; done\n"
            )
        init_txt = init_txt.replace(devtmpfs_needle, devtmpfs_needle + r49_early_hook, 1)
    elif enable_r48 and r48_mode in ("recover_imagedb_battery_vault", "af_sens_interval_still_h0_h3"):
        devtmpfs_needle = "echo FX3_DEVTMPFS_RC=$?\n"
        if devtmpfs_needle not in init_txt:
            raise RuntimeError(f"Expected devtmpfs marker not found in {parent_cpio} /init")
        if r48_mode == "recover_imagedb_battery_vault":
            r48_early_hook = (
                "LD_LIBRARY_PATH=/usr/lib:/lib /usr/bin/fx6-stage-a-verify --r48-recover-imagedb-vault > /dev/console 2>&1\n"
                "fx6_r48_ri_rc=$?\n"
                "echo FX6_R48_RECOVER_IMAGEDB_VAULT_RC=$fx6_r48_ri_rc\n"
                "echo FX6_R48_RECOVER_IMAGEDB_VAULT_EXIT rc=$fx6_r48_ri_rc emmc_write_count=0\n"
                "/bin/busybox sync 2>/dev/null\n"
                "/bin/busybox poweroff -f 2>/dev/null || /bin/busybox halt -f 2>/dev/null\n"
                "while true; do /bin/busybox sleep 1; done\n"
            )
        else:
            r48_early_hook = (
                "LD_LIBRARY_PATH=/usr/lib:/lib /usr/bin/fx6-stage-a-verify --r48-af-sens-interval-h0-h3 > /dev/console 2>&1\n"
                "fx6_r48_af_rc=$?\n"
                "echo FX6_R48_AF_SENS_INTERVAL_RC=$fx6_r48_af_rc\n"
                "echo FX6_R48_AF_SENS_INTERVAL_EXIT rc=$fx6_r48_af_rc emmc_write_count=0\n"
                "/bin/busybox sync 2>/dev/null\n"
                "/bin/busybox poweroff -f 2>/dev/null || /bin/busybox halt -f 2>/dev/null\n"
                "while true; do /bin/busybox sleep 1; done\n"
            )
        init_txt = init_txt.replace(devtmpfs_needle, devtmpfs_needle + r48_early_hook, 1)
    elif enable_r47 and r47_mode in ("marker_15ratio_persist_hdmi_isolation", "flexexp_avtviso_autoslowshutter_h0_h3"):
        devtmpfs_needle = "echo FX3_DEVTMPFS_RC=$?\n"
        if devtmpfs_needle not in init_txt:
            raise RuntimeError(f"Expected devtmpfs marker not found in {parent_cpio} /init")
        if r47_mode == "marker_15ratio_persist_hdmi_isolation":
            r47_early_hook = (
                "LD_LIBRARY_PATH=/usr/lib:/lib /usr/bin/fx6-stage-a-verify --r47-marker-15ratio-hdmi > /dev/console 2>&1\n"
                "fx6_r47_mk_rc=$?\n"
                "echo FX6_R47_MARKER_15RATIO_HDMI_RC=$fx6_r47_mk_rc\n"
                "echo FX6_R47_MARKER_15RATIO_HDMI_EXIT rc=$fx6_r47_mk_rc emmc_write_count=0\n"
                "/bin/busybox sync 2>/dev/null\n"
                "/bin/busybox poweroff -f 2>/dev/null || /bin/busybox halt -f 2>/dev/null\n"
                "while true; do /bin/busybox sleep 1; done\n"
            )
        else:
            r47_early_hook = (
                "LD_LIBRARY_PATH=/usr/lib:/lib /usr/bin/fx6-stage-a-verify --r47-flexexp-reset-split > /dev/console 2>&1\n"
                "fx6_r47_fe_rc=$?\n"
                "echo FX6_R47_FLEXEXP_RESET_SPLIT_RC=$fx6_r47_fe_rc\n"
                "echo FX6_R47_FLEXEXP_RESET_SPLIT_EXIT rc=$fx6_r47_fe_rc emmc_write_count=0\n"
                "/bin/busybox sync 2>/dev/null\n"
                "/bin/busybox poweroff -f 2>/dev/null || /bin/busybox halt -f 2>/dev/null\n"
                "while true; do /bin/busybox sleep 1; done\n"
            )
        init_txt = init_txt.replace(devtmpfs_needle, devtmpfs_needle + r47_early_hook, 1)
    elif enable_r46 and r46_mode in ("zebra_persist_peaking_hdmi_isolation", "slot1_fullformat_chord_vault_h0_h3"):
        devtmpfs_needle = "echo FX3_DEVTMPFS_RC=$?\n"
        if devtmpfs_needle not in init_txt:
            raise RuntimeError(f"Expected devtmpfs marker not found in {parent_cpio} /init")
        if r46_mode == "zebra_persist_peaking_hdmi_isolation":
            r46_early_hook = (
                "LD_LIBRARY_PATH=/usr/lib:/lib /usr/bin/fx6-stage-a-verify --r46-zebra-peaking-hdmi > /dev/console 2>&1\n"
                "fx6_r46_zp_rc=$?\n"
                "echo FX6_R46_ZEBRA_PEAKING_HDMI_RC=$fx6_r46_zp_rc\n"
                "echo FX6_R46_ZEBRA_PEAKING_HDMI_EXIT rc=$fx6_r46_zp_rc emmc_write_count=0\n"
                "/bin/busybox sync 2>/dev/null\n"
                "/bin/busybox poweroff -f 2>/dev/null || /bin/busybox halt -f 2>/dev/null\n"
                "while true; do /bin/busybox sleep 1; done\n"
            )
        else:
            r46_early_hook = (
                "LD_LIBRARY_PATH=/usr/lib:/lib /usr/bin/fx6-stage-a-verify --r46-fullformat-chord-vault > /dev/console 2>&1\n"
                "fx6_r46_ff_rc=$?\n"
                "echo FX6_R46_FULLFORMAT_CHORD_VAULT_RC=$fx6_r46_ff_rc\n"
                "echo FX6_R46_FULLFORMAT_CHORD_VAULT_EXIT rc=$fx6_r46_ff_rc emmc_write_count=0\n"
                "/bin/busybox sync 2>/dev/null\n"
                "/bin/busybox poweroff -f 2>/dev/null || /bin/busybox halt -f 2>/dev/null\n"
                "while true; do /bin/busybox sleep 1; done\n"
            )
        init_txt = init_txt.replace(devtmpfs_needle, devtmpfs_needle + r46_early_hook, 1)
    elif enable_r45 and r45_mode in ("ciz_4locks_hfr_raw_cutoffs", "powersave_9cond_autotemp_h0_h3"):
        devtmpfs_needle = "echo FX3_DEVTMPFS_RC=$?\n"
        if devtmpfs_needle not in init_txt:
            raise RuntimeError(f"Expected devtmpfs marker not found in {parent_cpio} /init")
        if r45_mode == "ciz_4locks_hfr_raw_cutoffs":
            r45_early_hook = (
                "LD_LIBRARY_PATH=/usr/lib:/lib /usr/bin/fx6-stage-a-verify --r45-ciz-4locks > /dev/console 2>&1\n"
                "fx6_r45_ciz_rc=$?\n"
                "echo FX6_R45_CIZ_4LOCKS_RC=$fx6_r45_ciz_rc\n"
                "echo FX6_R45_CIZ_4LOCKS_EXIT rc=$fx6_r45_ciz_rc emmc_write_count=0\n"
                "/bin/busybox sync 2>/dev/null\n"
                "/bin/busybox poweroff -f 2>/dev/null || /bin/busybox halt -f 2>/dev/null\n"
                "while true; do /bin/busybox sleep 1; done\n"
            )
        else:
            r45_early_hook = (
                "LD_LIBRARY_PATH=/usr/lib:/lib /usr/bin/fx6-stage-a-verify --r45-powersave-autotemp > /dev/console 2>&1\n"
                "fx6_r45_ps_rc=$?\n"
                "echo FX6_R45_POWERSAVE_AUTOTEMP_RC=$fx6_r45_ps_rc\n"
                "echo FX6_R45_POWERSAVE_AUTOTEMP_EXIT rc=$fx6_r45_ps_rc emmc_write_count=0\n"
                "/bin/busybox sync 2>/dev/null\n"
                "/bin/busybox poweroff -f 2>/dev/null || /bin/busybox halt -f 2>/dev/null\n"
                "while true; do /bin/busybox sleep 1; done\n"
            )
        init_txt = init_txt.replace(devtmpfs_needle, devtmpfs_needle + r45_early_hook, 1)
    elif enable_r44 and r44_mode in ("ntscpal_dfn_camreset_persist", "gammaassist_displaylut_h0_h3"):
        devtmpfs_needle = "echo FX3_DEVTMPFS_RC=$?\n"
        if devtmpfs_needle not in init_txt:
            raise RuntimeError(f"Expected devtmpfs marker not found in {parent_cpio} /init")
        if r44_mode == "ntscpal_dfn_camreset_persist":
            r44_early_hook = (
                "LD_LIBRARY_PATH=/usr/lib:/lib /usr/bin/fx6-stage-a-verify --r44-ntscpal-camreset > /dev/console 2>&1\n"
                "fx6_r44_np_rc=$?\n"
                "echo FX6_R44_NTSCPAL_CAMRESET_RC=$fx6_r44_np_rc\n"
                "echo FX6_R44_NTSCPAL_CAMRESET_EXIT rc=$fx6_r44_np_rc emmc_write_count=0\n"
                "/bin/busybox sync 2>/dev/null\n"
                "/bin/busybox poweroff -f 2>/dev/null || /bin/busybox halt -f 2>/dev/null\n"
                "while true; do /bin/busybox sleep 1; done\n"
            )
        else:
            r44_early_hook = (
                "LD_LIBRARY_PATH=/usr/lib:/lib /usr/bin/fx6-stage-a-verify --r44-gammaassist-displaylut > /dev/console 2>&1\n"
                "fx6_r44_gd_rc=$?\n"
                "echo FX6_R44_GAMMAASSIST_DISPLAYLUT_RC=$fx6_r44_gd_rc\n"
                "echo FX6_R44_GAMMAASSIST_DISPLAYLUT_EXIT rc=$fx6_r44_gd_rc emmc_write_count=0\n"
                "/bin/busybox sync 2>/dev/null\n"
                "/bin/busybox poweroff -f 2>/dev/null || /bin/busybox halt -f 2>/dev/null\n"
                "while true; do /bin/busybox sleep 1; done\n"
            )
        init_txt = init_txt.replace(devtmpfs_needle, devtmpfs_needle + r44_early_hook, 1)
    elif enable_r43 and r43_mode in ("tc_regenerate_slot1_extlk", "reclamp_coupled_tally_h0_h3"):
        devtmpfs_needle = "echo FX3_DEVTMPFS_RC=$?\n"
        if devtmpfs_needle not in init_txt:
            raise RuntimeError(f"Expected devtmpfs marker not found in {parent_cpio} /init")
        if r43_mode == "tc_regenerate_slot1_extlk":
            r43_early_hook = (
                "LD_LIBRARY_PATH=/usr/lib:/lib /usr/bin/fx6-stage-a-verify --r43-tc-regenerate > /dev/console 2>&1\n"
                "fx6_r43_tcr_rc=$?\n"
                "echo FX6_R43_TC_REGENERATE_RC=$fx6_r43_tcr_rc\n"
                "echo FX6_R43_TC_REGENERATE_EXIT rc=$fx6_r43_tcr_rc emmc_write_count=0\n"
                "/bin/busybox sync 2>/dev/null\n"
                "/bin/busybox poweroff -f 2>/dev/null || /bin/busybox halt -f 2>/dev/null\n"
                "while true; do /bin/busybox sleep 1; done\n"
            )
        else:
            r43_early_hook = (
                "LD_LIBRARY_PATH=/usr/lib:/lib /usr/bin/fx6-stage-a-verify --r43-reclamp-silent > /dev/console 2>&1\n"
                "fx6_r43_rcl_rc=$?\n"
                "echo FX6_R43_RECLAMP_SILENT_RC=$fx6_r43_rcl_rc\n"
                "echo FX6_R43_RECLAMP_SILENT_EXIT rc=$fx6_r43_rcl_rc emmc_write_count=0\n"
                "/bin/busybox sync 2>/dev/null\n"
                "/bin/busybox poweroff -f 2>/dev/null || /bin/busybox halt -f 2>/dev/null\n"
                "while true; do /bin/busybox sleep 1; done\n"
            )
        init_txt = init_txt.replace(devtmpfs_needle, devtmpfs_needle + r43_early_hook, 1)
    elif enable_r42 and r42_mode in ("proxy_vault_119p_atomic_pair", "focusmag_brightmon_h0_h3"):
        devtmpfs_needle = "echo FX3_DEVTMPFS_RC=$?\n"
        if devtmpfs_needle not in init_txt:
            raise RuntimeError(f"Expected devtmpfs marker not found in {parent_cpio} /init")
        if r42_mode == "proxy_vault_119p_atomic_pair":
            r42_early_hook = (
                "LD_LIBRARY_PATH=/usr/lib:/lib /usr/bin/fx6-stage-a-verify --r42-proxy-vault > /dev/console 2>&1\n"
                "fx6_r42_pv_rc=$?\n"
                "echo FX6_R42_PROXY_VAULT_RC=$fx6_r42_pv_rc\n"
                "echo FX6_R42_PROXY_VAULT_EXIT rc=$fx6_r42_pv_rc emmc_write_count=0\n"
                "/bin/busybox sync 2>/dev/null\n"
                "/bin/busybox poweroff -f 2>/dev/null || /bin/busybox halt -f 2>/dev/null\n"
                "while true; do /bin/busybox sleep 1; done\n"
            )
        else:
            r42_early_hook = (
                "LD_LIBRARY_PATH=/usr/lib:/lib /usr/bin/fx6-stage-a-verify --r42-focusmag-brightmon > /dev/console 2>&1\n"
                "fx6_r42_fb_rc=$?\n"
                "echo FX6_R42_FOCUSMAG_BRIGHTMON_RC=$fx6_r42_fb_rc\n"
                "echo FX6_R42_FOCUSMAG_BRIGHTMON_EXIT rc=$fx6_r42_fb_rc emmc_write_count=0\n"
                "/bin/busybox sync 2>/dev/null\n"
                "/bin/busybox poweroff -f 2>/dev/null || /bin/busybox halt -f 2>/dev/null\n"
                "while true; do /bin/busybox sleep 1; done\n"
            )
        init_txt = init_txt.replace(devtmpfs_needle, devtmpfs_needle + r42_early_hook, 1)
    elif enable_r41 and r41_mode in ("external_focusmap_150fps_cutoff", "simult_autoswitch_shocklesswb"):
        devtmpfs_needle = "echo FX3_DEVTMPFS_RC=$?\n"
        if devtmpfs_needle not in init_txt:
            raise RuntimeError(f"Expected devtmpfs marker not found in {parent_cpio} /init")
        if r41_mode == "external_focusmap_150fps_cutoff":
            r41_early_hook = (
                "LD_LIBRARY_PATH=/usr/lib:/lib /usr/bin/fx6-stage-a-verify --r41-focusmap-150fps > /dev/console 2>&1\n"
                "fx6_r41_fm_rc=$?\n"
                "echo FX6_R41_FOCUSMAP_RC=$fx6_r41_fm_rc\n"
                "echo FX6_R41_FOCUSMAP_150FPS_EXIT rc=$fx6_r41_fm_rc emmc_write_count=0\n"
                "/bin/busybox sync 2>/dev/null\n"
                "/bin/busybox poweroff -f 2>/dev/null || /bin/busybox halt -f 2>/dev/null\n"
                "while true; do /bin/busybox sleep 1; done\n"
            )
        else:
            r41_early_hook = (
                "LD_LIBRARY_PATH=/usr/lib:/lib /usr/bin/fx6-stage-a-verify --r41-simult-shocklesswb > /dev/console 2>&1\n"
                "fx6_r41_swb_rc=$?\n"
                "echo FX6_R41_SIMULT_WB_RC=$fx6_r41_swb_rc\n"
                "echo FX6_R41_SIMULT_SHOCKLESSWB_EXIT rc=$fx6_r41_swb_rc emmc_write_count=0\n"
                "/bin/busybox sync 2>/dev/null\n"
                "/bin/busybox poweroff -f 2>/dev/null || /bin/busybox halt -f 2>/dev/null\n"
                "while true; do /bin/busybox sleep 1; done\n"
            )
        init_txt = init_txt.replace(devtmpfs_needle, devtmpfs_needle + r41_early_hook, 1)
    elif enable_r40 and r40_mode in ("camset_slot1_dualmedia_split", "vmcbncm1_tcin_hdmi_tcout"):
        devtmpfs_needle = "echo FX3_DEVTMPFS_RC=$?\n"
        if devtmpfs_needle not in init_txt:
            raise RuntimeError(f"Expected devtmpfs marker not found in {parent_cpio} /init")
        if r40_mode == "camset_slot1_dualmedia_split":
            r40_early_hook = (
                "LD_LIBRARY_PATH=/usr/lib:/lib /usr/bin/fx6-stage-a-verify --r40-camset-slot1-split > /dev/console 2>&1\n"
                "fx6_r40_camset_rc=$?\n"
                "echo FX6_R40_CAMSET_RC=$fx6_r40_camset_rc\n"
                "echo FX6_R40_CAMSET_SLOT1_SPLIT_EXIT rc=$fx6_r40_camset_rc emmc_write_count=0\n"
                "/bin/busybox sync 2>/dev/null\n"
                "/bin/busybox poweroff -f 2>/dev/null || /bin/busybox halt -f 2>/dev/null\n"
                "while true; do /bin/busybox sleep 1; done\n"
            )
        else:
            r40_early_hook = (
                "LD_LIBRARY_PATH=/usr/lib:/lib /usr/bin/fx6-stage-a-verify --r40-vmcbncm1-tcin-hdmi > /dev/console 2>&1\n"
                "fx6_r40_vmc_rc=$?\n"
                "echo FX6_R40_VMCBNCM1_RC=$fx6_r40_vmc_rc\n"
                "echo FX6_R40_VMCBNCM1_TCIN_HDMI_EXIT rc=$fx6_r40_vmc_rc emmc_write_count=0\n"
                "/bin/busybox sync 2>/dev/null\n"
                "/bin/busybox poweroff -f 2>/dev/null || /bin/busybox halt -f 2>/dev/null\n"
                "while true; do /bin/busybox sleep 1; done\n"
            )
        init_txt = init_txt.replace(devtmpfs_needle, devtmpfs_needle + r40_early_hook, 1)
    elif enable_r39 and r39_mode in ("shutter_speed_angle_clamp", "lut_601_vs_702_firewall"):
        devtmpfs_needle = "echo FX3_DEVTMPFS_RC=$?\n"
        if devtmpfs_needle not in init_txt:
            raise RuntimeError(f"Expected devtmpfs marker not found in {parent_cpio} /init")
        if r39_mode == "shutter_speed_angle_clamp":
            r39_early_hook = (
                "LD_LIBRARY_PATH=/usr/lib:/lib /usr/bin/fx6-stage-a-verify --r39-shutter-speed-angle > /dev/console 2>&1\n"
                "fx6_r39_shutter_rc=$?\n"
                "echo FX6_R39_SHUTTER_RC=$fx6_r39_shutter_rc\n"
                "echo FX6_R39_SHUTTER_SPEED_ANGLE_EXIT rc=$fx6_r39_shutter_rc emmc_write_count=0\n"
                "/bin/busybox sync 2>/dev/null\n"
                "/bin/busybox poweroff -f 2>/dev/null || /bin/busybox halt -f 2>/dev/null\n"
                "while true; do /bin/busybox sleep 1; done\n"
            )
        else:
            r39_early_hook = (
                "LD_LIBRARY_PATH=/usr/lib:/lib /usr/bin/fx6-stage-a-verify --r39-lut-601-702-firewall > /dev/console 2>&1\n"
                "fx6_r39_lut_rc=$?\n"
                "echo FX6_R39_LUT_SPLIT_RC=$fx6_r39_lut_rc\n"
                "echo FX6_R39_LUT_601_702_FIREWALL_EXIT rc=$fx6_r39_lut_rc emmc_write_count=0\n"
                "/bin/busybox sync 2>/dev/null\n"
                "/bin/busybox poweroff -f 2>/dev/null || /bin/busybox halt -f 2>/dev/null\n"
                "while true; do /bin/busybox sleep 1; done\n"
            )
        init_txt = init_txt.replace(devtmpfs_needle, devtmpfs_needle + r39_early_hook, 1)
    elif enable_r38 and r38_mode in ("lut_path_cineei", "rmtp1bt_clipflag_seal"):
        devtmpfs_needle = "echo FX3_DEVTMPFS_RC=$?\n"
        if devtmpfs_needle not in init_txt:
            raise RuntimeError(f"Expected devtmpfs marker not found in {parent_cpio} /init")
        if r38_mode == "lut_path_cineei":
            r38_early_hook = (
                "LD_LIBRARY_PATH=/usr/lib:/lib /usr/bin/fx6-stage-a-verify --r38-lut-path-cineei > /dev/console 2>&1\n"
                "fx6_r38_lut_rc=$?\n"
                "echo FX6_R38_LUT_CINEEI_RC=$fx6_r38_lut_rc\n"
                "echo FX6_R38_LUT_CINEEI_EXIT rc=$fx6_r38_lut_rc emmc_write_count=0\n"
                "/bin/busybox sync 2>/dev/null\n"
                "/bin/busybox poweroff -f 2>/dev/null || /bin/busybox halt -f 2>/dev/null\n"
                "while true; do /bin/busybox sleep 1; done\n"
            )
        else:
            r38_early_hook = (
                "LD_LIBRARY_PATH=/usr/lib:/lib /usr/bin/fx6-stage-a-verify --r38-rmtp1bt-clipflag > /dev/console 2>&1\n"
                "fx6_r38_rmt_rc=$?\n"
                "echo FX6_R38_RMTP1BT_RC=$fx6_r38_rmt_rc\n"
                "echo FX6_R38_RMTP1BT_CLIPFLAG_EXIT rc=$fx6_r38_rmt_rc emmc_write_count=0\n"
                "/bin/busybox sync 2>/dev/null\n"
                "/bin/busybox poweroff -f 2>/dev/null || /bin/busybox halt -f 2>/dev/null\n"
                "while true; do /bin/busybox sleep 1; done\n"
            )
        init_txt = init_txt.replace(devtmpfs_needle, devtmpfs_needle + r38_early_hook, 1)
    elif enable_r37 and r37_mode in ("xlrh1_4ch_override", "fx3bndl1_serial_appledouble"):
        devtmpfs_needle = "echo FX3_DEVTMPFS_RC=$?\n"
        if devtmpfs_needle not in init_txt:
            raise RuntimeError(f"Expected devtmpfs marker not found in {parent_cpio} /init")
        if r37_mode == "xlrh1_4ch_override":
            r37_early_hook = (
                "LD_LIBRARY_PATH=/usr/lib:/lib /usr/bin/fx6-stage-a-verify --r37-xlrh1-4ch > /dev/console 2>&1\n"
                "fx6_r37_xlrh1_rc=$?\n"
                "echo FX6_R37_XLRH1_RC=$fx6_r37_xlrh1_rc\n"
                "echo FX6_R37_XLRH1_4CH_EXIT rc=$fx6_r37_xlrh1_rc emmc_write_count=0\n"
                "/bin/busybox sync 2>/dev/null\n"
                "/bin/busybox poweroff -f 2>/dev/null || /bin/busybox halt -f 2>/dev/null\n"
                "while true; do /bin/busybox sleep 1; done\n"
            )
        else:
            r37_early_hook = (
                "LD_LIBRARY_PATH=/usr/lib:/lib /usr/bin/fx6-stage-a-verify --r37-fx3bndl1-serial > /dev/console 2>&1\n"
                "fx6_r37_bndl_rc=$?\n"
                "echo FX6_R37_FX3BNDL1_RC=$fx6_r37_bndl_rc\n"
                "echo FX6_R37_FX3BNDL1_SERIAL_EXIT rc=$fx6_r37_bndl_rc emmc_write_count=0\n"
                "/bin/busybox sync 2>/dev/null\n"
                "/bin/busybox poweroff -f 2>/dev/null || /bin/busybox halt -f 2>/dev/null\n"
                "while true; do /bin/busybox sleep 1; done\n"
            )
        init_txt = init_txt.replace(devtmpfs_needle, devtmpfs_needle + r37_early_hook, 1)
    elif enable_r36 and r36_mode in ("hdmi_4264_raw_prores_braw", "wpa2_wpa3_focusmap_bridge"):
        devtmpfs_needle = "echo FX3_DEVTMPFS_RC=$?\n"
        if devtmpfs_needle not in init_txt:
            raise RuntimeError(f"Expected devtmpfs marker not found in {parent_cpio} /init")
        if r36_mode == "hdmi_4264_raw_prores_braw":
            r36_early_hook = (
                "LD_LIBRARY_PATH=/usr/lib:/lib /usr/bin/fx6-stage-a-verify --r36-hdmi-4264-raw > /dev/console 2>&1\n"
                "fx6_r36_hdmi_rc=$?\n"
                "echo FX6_R36_HDMI_RAW_RC=$fx6_r36_hdmi_rc\n"
                "echo FX6_R36_HDMI_4264_RAW_EXIT rc=$fx6_r36_hdmi_rc emmc_write_count=0\n"
                "/bin/busybox sync 2>/dev/null\n"
                "/bin/busybox poweroff -f 2>/dev/null || /bin/busybox halt -f 2>/dev/null\n"
                "while true; do /bin/busybox sleep 1; done\n"
            )
        else:
            r36_early_hook = (
                "LD_LIBRARY_PATH=/usr/lib:/lib /usr/bin/fx6-stage-a-verify --r36-wpa3-focusmap > /dev/console 2>&1\n"
                "fx6_r36_wpa3_rc=$?\n"
                "echo FX6_R36_WPA3_FOCUSMAP_RC=$fx6_r36_wpa3_rc\n"
                "echo FX6_R36_WPA3_FOCUSMAP_EXIT rc=$fx6_r36_wpa3_rc emmc_write_count=0\n"
                "/bin/busybox sync 2>/dev/null\n"
                "/bin/busybox poweroff -f 2>/dev/null || /bin/busybox halt -f 2>/dev/null\n"
                "while true; do /bin/busybox sleep 1; done\n"
            )
        init_txt = init_txt.replace(devtmpfs_needle, devtmpfs_needle + r36_early_hook, 1)
    elif enable_r35 and r35_mode in ("powerloss_100cycle_rsv", "slot1_ufu_c2pa_ceiling"):
        devtmpfs_needle = "echo FX3_DEVTMPFS_RC=$?\n"
        if devtmpfs_needle not in init_txt:
            raise RuntimeError(f"Expected devtmpfs marker not found in {parent_cpio} /init")
        if r35_mode == "powerloss_100cycle_rsv":
            r35_early_hook = (
                "/usr/bin/fx6-stage-a-verify --r35-powerloss-100cycle > /dev/console 2>&1\n"
                "fx6_r35_powerloss_rc=$?\n"
                "echo FX6_R35_POWERLOSS_RC=$fx6_r35_powerloss_rc\n"
                "echo FX6_R35_POWERLOSS_100CYCLE_EXIT rc=$fx6_r35_powerloss_rc emmc_write_count=0\n"
                "/bin/busybox sync 2>/dev/null\n"
                "/bin/busybox poweroff -f 2>/dev/null || /bin/busybox halt -f 2>/dev/null\n"
                "while true; do /bin/busybox sleep 1; done\n"
            )
        else:
            r35_early_hook = (
                "/usr/bin/fx6-stage-a-verify --r35-slot1-ufu-c2pa > /dev/console 2>&1\n"
                "fx6_r35_slot1_rc=$?\n"
                "echo FX6_R35_SLOT1_UFU_RC=$fx6_r35_slot1_rc\n"
                "echo FX6_R35_SLOT1_UFU_C2PA_EXIT rc=$fx6_r35_slot1_rc emmc_write_count=0\n"
                "/bin/busybox sync 2>/dev/null\n"
                "/bin/busybox poweroff -f 2>/dev/null || /bin/busybox halt -f 2>/dev/null\n"
                "while true; do /bin/busybox sleep 1; done\n"
            )
        init_txt = init_txt.replace(devtmpfs_needle, devtmpfs_needle + r35_early_hook, 1)
    elif enable_r34 and r34_mode in ("cxd90058_sabin_sdi_mask", "raid6_gf256_seal_16"):
        devtmpfs_needle = "echo FX3_DEVTMPFS_RC=$?\n"
        if devtmpfs_needle not in init_txt:
            raise RuntimeError(f"Expected devtmpfs marker not found in {parent_cpio} /init")
        if r34_mode == "cxd90058_sabin_sdi_mask":
            r34_early_hook = (
                "LD_LIBRARY_PATH=/usr/lib:/lib /usr/bin/fx6-stage-a-verify --r34-cxd90058-sabin > /dev/console 2>&1\n"
                "fx6_r34_sabin_rc=$?\n"
                "echo FX6_R34_CXD90058_SABIN_RC=$fx6_r34_sabin_rc\n"
                "echo FX6_R34_CXD90058_SABIN_EXIT rc=$fx6_r34_sabin_rc emmc_write_count=0\n"
                "/bin/busybox sync 2>/dev/null\n"
                "/bin/busybox poweroff -f 2>/dev/null || /bin/busybox halt -f 2>/dev/null\n"
                "while true; do /bin/busybox sleep 1; done\n"
            )
        else:
            r34_early_hook = (
                "/usr/bin/fx6-stage-a-verify --r34-raid6-seal16 > /dev/console 2>&1\n"
                "fx6_r34_seal_rc=$?\n"
                "echo FX6_R34_RAID6_SEAL16_RC=$fx6_r34_seal_rc\n"
                "echo FX6_R34_RAID6_SEAL16_EXIT rc=$fx6_r34_seal_rc emmc_write_count=0\n"
                "/bin/busybox sync 2>/dev/null\n"
                "/bin/busybox poweroff -f 2>/dev/null || /bin/busybox halt -f 2>/dev/null\n"
                "while true; do /bin/busybox sleep 1; done\n"
            )
        init_txt = init_txt.replace(devtmpfs_needle, devtmpfs_needle + r34_early_hook, 1)
    elif enable_r33 and r33_mode in ("bodydata_ufu_bypass", "recovery_5tier"):
        devtmpfs_needle = "echo FX3_DEVTMPFS_RC=$?\n"
        if devtmpfs_needle not in init_txt:
            raise RuntimeError(f"Expected devtmpfs marker not found in {parent_cpio} /init")
        if r33_mode == "bodydata_ufu_bypass":
            r33_early_hook = (
                "/usr/bin/fx6-stage-a-verify --r33-bodydata-ufu-bypass > /dev/console 2>&1\n"
                "fx6_r33_ufu_rc=$?\n"
                "echo FX6_R33_UFU_BYPASS_RC=$fx6_r33_ufu_rc\n"
                "echo FX6_R33_UFU_BYPASS_EXIT rc=$fx6_r33_ufu_rc emmc_write_count=0\n"
                "/bin/busybox sync 2>/dev/null\n"
                "/bin/busybox poweroff -f 2>/dev/null || /bin/busybox halt -f 2>/dev/null\n"
                "while true; do /bin/busybox sleep 1; done\n"
            )
        else:
            r33_early_hook = (
                "/usr/bin/fx6-stage-a-verify --r33-recovery-5tier > /dev/console 2>&1\n"
                "fx6_r33_5tier_rc=$?\n"
                "echo FX6_R33_5TIER_RC=$fx6_r33_5tier_rc\n"
                "echo FX6_R33_5TIER_EXIT rc=$fx6_r33_5tier_rc emmc_write_count=0\n"
                "/bin/busybox sync 2>/dev/null\n"
                "/bin/busybox poweroff -f 2>/dev/null || /bin/busybox halt -f 2>/dev/null\n"
                "while true; do /bin/busybox sleep 1; done\n"
            )
        init_txt = init_txt.replace(devtmpfs_needle, devtmpfs_needle + r33_early_hook, 1)
    elif enable_r32 and r32_mode in ("cdcncm_usb_0da1", "uart_6stage_triage"):
        devtmpfs_needle = "echo FX3_DEVTMPFS_RC=$?\n"
        if devtmpfs_needle not in init_txt:
            raise RuntimeError(f"Expected devtmpfs marker not found in {parent_cpio} /init")
        if r32_mode == "cdcncm_usb_0da1":
            r32_early_hook = (
                "LD_LIBRARY_PATH=/usr/lib:/lib /usr/bin/fx6-stage-a-verify --r32-cdcncm-usb-0da1 > /dev/console 2>&1\n"
                "fx6_r32_cdcncm_rc=$?\n"
                "echo FX6_R32_CDCNCM_RC=$fx6_r32_cdcncm_rc\n"
                "echo FX6_R32_CDCNCM_EXIT rc=$fx6_r32_cdcncm_rc emmc_write_count=0\n"
                "/bin/busybox sync 2>/dev/null\n"
                "/bin/busybox poweroff -f 2>/dev/null || /bin/busybox halt -f 2>/dev/null\n"
                "while true; do /bin/busybox sleep 1; done\n"
            )
        else:
            r32_early_hook = (
                "/usr/bin/fx6-stage-a-verify --r32-uart-6stage > /dev/console 2>&1\n"
                "fx6_r32_uart_rc=$?\n"
                "echo FX6_R32_UART_RC=$fx6_r32_uart_rc\n"
                "echo FX6_R32_UART_EXIT rc=$fx6_r32_uart_rc emmc_write_count=0\n"
                "/bin/busybox sync 2>/dev/null\n"
                "/bin/busybox poweroff -f 2>/dev/null || /bin/busybox halt -f 2>/dev/null\n"
                "while true; do /bin/busybox sleep 1; done\n"
            )
        init_txt = init_txt.replace(devtmpfs_needle, devtmpfs_needle + r32_early_hook, 1)
    elif enable_r31 and r31_mode in ("fan_fz100_power", "mtdro_firewall"):
        devtmpfs_needle = "echo FX3_DEVTMPFS_RC=$?\n"
        if devtmpfs_needle not in init_txt:
            raise RuntimeError(f"Expected devtmpfs marker not found in {parent_cpio} /init")
        if r31_mode == "fan_fz100_power":
            r31_early_hook = (
                "/usr/bin/fx6-stage-a-verify --r31-fan-fz100-power > /dev/console 2>&1\n"
                "fx6_r31_fan_rc=$?\n"
                "echo FX6_R31_FAN_FZ100_RC=$fx6_r31_fan_rc\n"
                "echo FX6_R31_FAN_FZ100_EXIT rc=$fx6_r31_fan_rc emmc_write_count=0\n"
                "/bin/busybox sync 2>/dev/null\n"
                "/bin/busybox poweroff -f 2>/dev/null || /bin/busybox halt -f 2>/dev/null\n"
                "while true; do /bin/busybox sleep 1; done\n"
            )
        else:
            r31_early_hook = (
                "/usr/bin/fx6-stage-a-verify --r31-mtdro-firewall > /dev/console 2>&1\n"
                "fx6_r31_mtdro_rc=$?\n"
                "echo FX6_R31_MTDRO_RC=$fx6_r31_mtdro_rc\n"
                "echo FX6_R31_MTDRO_EXIT rc=$fx6_r31_mtdro_rc emmc_write_count=0\n"
                "/bin/busybox sync 2>/dev/null\n"
                "/bin/busybox poweroff -f 2>/dev/null || /bin/busybox halt -f 2>/dev/null\n"
                "while true; do /bin/busybox sleep 1; done\n"
            )
        init_txt = init_txt.replace(devtmpfs_needle, devtmpfs_needle + r31_early_hook, 1)
    elif enable_r30 and r30_mode in ("canary_tier0", "jbusy_uninstall"):
        devtmpfs_needle = "echo FX3_DEVTMPFS_RC=$?\n"
        if devtmpfs_needle not in init_txt:
            raise RuntimeError(f"Expected devtmpfs marker not found in {parent_cpio} /init")
        if r30_mode == "canary_tier0":
            r30_early_hook = (
                "/usr/bin/fx6-stage-a-verify --r30-canary-tier0 > /dev/console 2>&1\n"
                "fx6_r30_canary_rc=$?\n"
                "echo FX6_R30_CANARY_TIER0_RC=$fx6_r30_canary_rc\n"
                "echo FX6_R30_CANARY_TIER0_EXIT rc=$fx6_r30_canary_rc emmc_write_count=0\n"
                "/bin/busybox sync 2>/dev/null\n"
                "/bin/busybox poweroff -f 2>/dev/null || /bin/busybox halt -f 2>/dev/null\n"
                "while true; do /bin/busybox sleep 1; done\n"
            )
        else:
            r30_early_hook = (
                "/usr/bin/fx6-stage-a-verify --r30-jbusy-uninstall > /dev/console 2>&1\n"
                "fx6_r30_jbusy_rc=$?\n"
                "echo FX6_R30_JBUSY_UNINSTALL_RC=$fx6_r30_jbusy_rc\n"
                "echo FX6_R30_JBUSY_UNINSTALL_EXIT rc=$fx6_r30_jbusy_rc emmc_write_count=0\n"
                "/bin/busybox sync 2>/dev/null\n"
                "/bin/busybox poweroff -f 2>/dev/null || /bin/busybox halt -f 2>/dev/null\n"
                "while true; do /bin/busybox sleep 1; done\n"
            )
        init_txt = init_txt.replace(devtmpfs_needle, devtmpfs_needle + r30_early_hook, 1)
    elif enable_r29 and r29_mode in ("rollback", "p1_rescue"):
        devtmpfs_needle = "echo FX3_DEVTMPFS_RC=$?\n"
        if devtmpfs_needle not in init_txt:
            raise RuntimeError(f"Expected devtmpfs marker not found in {parent_cpio} /init")
        if r29_mode == "rollback":
            r29_early_hook = (
                "/usr/bin/fx6-stage-a-verify --r29-installer-rollback > /dev/console 2>&1\n"
                "fx6_r29_rb_rc=$?\n"
                "echo FX6_R29_ROLLBACK_RC=$fx6_r29_rb_rc\n"
                "echo FX6_R29_ROLLBACK_EXIT rc=$fx6_r29_rb_rc emmc_write_count=0\n"
                "/bin/busybox sync 2>/dev/null\n"
                "/bin/busybox poweroff -f 2>/dev/null || /bin/busybox halt -f 2>/dev/null\n"
                "while true; do /bin/busybox sleep 1; done\n"
            )
        else:
            r29_early_hook = (
                "/usr/bin/fx6-stage-a-verify --r29-p1-rescue > /dev/console 2>&1\n"
                "fx6_r29_p1_rc=$?\n"
                "echo FX6_R29_P1_RESCUE_RC=$fx6_r29_p1_rc\n"
                "echo FX6_R29_P1_RESCUE_EXIT rc=$fx6_r29_p1_rc emmc_write_count=0\n"
                "/bin/busybox sync 2>/dev/null\n"
                "/bin/busybox poweroff -f 2>/dev/null || /bin/busybox halt -f 2>/dev/null\n"
                "while true; do /bin/busybox sleep 1; done\n"
            )
        init_txt = init_txt.replace(devtmpfs_needle, devtmpfs_needle + r29_early_hook, 1)
    elif enable_r28:
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
    r29_install_hook = ""
    if enable_r29 and r29_mode == "install_mpr_rec":
        r29_install_hook = (
            "/usr/bin/fx6-stage-a-verify --r29-installer-install > /dev/console 2>&1\n"
            "fx6_r29_install_rc=$?\n"
            "echo FX6_R29_INSTALL_RC=$fx6_r29_install_rc\n"
            'if [ "$fx6_r29_install_rc" != 0 ]; then\n'
            " echo FX6_STAGE_A_ABORT_BEFORE_LAUNCH rc=$fx6_r29_install_rc\n"
            " while true; do /bin/busybox sleep 1; done\n"
            "fi\n"
        )
    verify_hook = (
        r29_install_hook
        + "/usr/bin/fx6-stage-a-verify > /dev/console 2>&1\n"
        + "fx6_stage_a_rc=$?\n"
        + "echo FX6_STAGE_A_VERIFY_RC=$fx6_stage_a_rc\n"
        + 'if [ "$fx6_stage_a_rc" != 0 ]; then\n'
        + " echo FX6_STAGE_A_ABORT_BEFORE_LAUNCH rc=$fx6_stage_a_rc\n"
        + " while true; do /bin/busybox sleep 1; done\n"
        + "fi\n"
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
    r29_meta: Optional[Dict[str, Any]] = None
    if enable_r29:
        stock_im_bytes = raw_members["usr/bin/im.elf"]
        stock_im_sha = sha256_bytes(stock_im_bytes)
        additions["etc/fx6_stage_r29"] = (
            f"stage_r29=1\nr29_mode={r29_mode}\nlang={lang}\n".encode("utf-8"),
            0o100644,
        )
        additions["etc/fx6_r29_stock_im_sha256.txt"] = f"{stock_im_sha}\n".encode("utf-8")
        r29_meta = {
            "r29_mode": r29_mode,
            "stock_im_elf_bytes": len(stock_im_bytes),
            "stock_im_elf_sha256": stock_im_sha,
            "target_device": "/dev/cnflasha15",
            "target_alias": "/dev/nflasha15",
            "blocked_plaintext_device": "/dev/pnflasha15",
            "p1_dat2_expected": "91030080",
            "p1_cfg_uart_expected": 1,
        }
    r30_meta: Optional[Dict[str, Any]] = None
    if enable_r30:
        stock_im_bytes = raw_members["usr/bin/im.elf"]
        stock_im_sha = sha256_bytes(stock_im_bytes)
        if "etc/fx3_sector0.bin" not in additions:
            fx3_sector0_r30 = build_fx3_sector0_table()
            additions["etc/fx3_sector0.bin"] = (fx3_sector0_r30, 0o100444)
        if "mnt/sd" not in additions:
            additions["mnt/sd"] = (b"", 0o040755)
        if "tmp/jiritsu" not in additions:
            additions["tmp/jiritsu"] = (b"", 0o040755)
        r30_libjit_bytes, r30_libjit_meta = build_r30_tier0_libjit_so(tmp_build)
        lensfile_bytes = _extract_optional_cpio_member(parent_cpio, "lens/lensfile.bin")
        p18_vfat_bytes, p18_vfat_meta = build_p18_lens_vfat_image(lensfile_bytes)
        additions["etc/fx6_stage_r30"] = (
            (
                f"stage_r30=1\nr30_mode={r30_mode}\n"
                f"p18_ro=1\nibis_5axis=1\nxlr_h1=1\nsdi_mask=1\nlang={lang}\n"
            ).encode("utf-8"),
            0o100644,
        )
        additions["etc/fx3_r30_libjit.so"] = (r30_libjit_bytes, 0o100755)
        additions["etc/fx3_r30_stock_im_sha256.txt"] = f"{stock_im_sha}\n".encode("utf-8")
        additions["etc/fx3_p18_lens.vfat"] = (p18_vfat_bytes, 0o100444)
        r30_meta = {
            "r30_mode": r30_mode,
            "stock_im_elf_bytes": len(stock_im_bytes),
            "stock_im_elf_sha256": stock_im_sha,
            "r30_libjit": r30_libjit_meta,
            "p18_lens_vfat": p18_vfat_meta,
            "opff_max_slot": "0x11",
            "jbusy_abort_rc": "0x10000011",
            "p18_mount_point": "/lens",
            "p18_mount_flags": "MS_RDONLY|MS_NOATIME",
        }
    r31_meta: Optional[Dict[str, Any]] = None
    if enable_r31:
        additions["etc/fx6_stage_r31"] = (
            (
                f"stage_r31=1\nr31_mode={r31_mode}\n"
                f"fx3_body_keymap=1\ntally_3x_gpio=1\n"
                f"fan_off_in_rec_override=1\nfz100_usb_pd_curve=1\n"
                f"pnflasha_mtdro_firewall=1\nlang={lang}\n"
            ).encode("utf-8"),
            0o100644,
        )
        r31_meta = {
            "r31_mode": r31_mode,
            "mode_key_mapping": "0x7028->0x718c (Big-6 Home)",
            "disp_key_mapping": "0x01fb->0x7052 (Status Check)",
            "custom_keys_count": 6,
            "tally_3x_policy": "REC_LAMP_ALL_LIGHTS_UP / OSD_ONLY_GREEN_YELLOW",
            "fan_mode": "OFF_IN_REC",
            "fan_emergency_override_c": 65.0,
            "fz100_nominal_mv": 7200,
            "fz100_near_end_mv": 6350,
            "usb_pd_profile": "9V/3A (27W)",
            "ext2_super_magic": "0xEF53",
            "mtd_ro_device": "/dev/mtd0ro",
        }
    r32_meta: Optional[Dict[str, Any]] = None
    if enable_r32:
        additions["etc/fx6_stage_r32"] = (
            (
                f"stage_r32=1\nr32_mode={r32_mode}\n"
                f"imx510_dual_base=1\np2_psd_defdet_erofs=1\n"
                f"cube_3d_mlut_non_bake=1\nzero_diff_libs_dlopen=1\n"
                f"cdcncm_0da1_intact=1\nttyama0_6stage_1v8=1\nlang={lang}\n"
            ).encode("utf-8"),
            0o100644,
        )
        r32_meta = {
            "r32_mode": r32_mode,
            "sensor": "IMX510",
            "dual_base_iso_lcg": 800,
            "dual_base_iso_hcg": 12800,
            "p2_setting_ro_files": ["p2:/setting/psd.bin", "p2:/setting/defdet.bin"],
            "cube_lut_size": 17,
            "cube_sd_dir": "/mnt/sd/PRIVATE/SONY/PRO/LUT/",
            "mlut_volatile_slot0": "/tmp/mlut_slot0.bin",
            "mlut_baked_into_master": 0,
            "zero_diff_libs": [
                "/usr/lib/libInfraMscServer.so",
                "/usr/lib/libUsbControl.so",
                "/usr/lib/libWlanAdjust.so",
                "/usr/lib/libWlanResource.so",
            ],
            "usb_msc_vid_pid": "054C:0DA1",
            "usb_service_vid_pid": "054C:0336",
            "uart_device": "/dev/ttyAMA0",
            "uart_baud_framing": "460800 8N1",
            "uart_logic_mv": 1800,
            "uart_max_safe_mv": 1950,
            "vmc_bncm1_contention_guard": 1,
        }
    r33_meta: Optional[Dict[str, Any]] = None
    if enable_r33:
        additions["etc/fx6_stage_r33"] = (
            (
                f"stage_r33=1\nr33_mode={r33_mode}\n"
                f"dual_slot_exfat_relay=1\nspeed_class_600m_gate=1\n"
                f"card_door_gpio_flush=1\nrsv_mxf_salvage=1\n"
                f"bodydata_ufu_100us_bypass=1\nrecovery_5tier_lock=1\nlang={lang}\n"
            ).encode("utf-8"),
            0o100644,
        )
        r33_meta = {
            "r33_mode": r33_mode,
            "slot_a_mount": "/mnt/sd",
            "slot_b_mount": "/mnt/sd2",
            "slot_a_media_type": "CFEXPRESS_TYPE_A_VPG400",
            "slot_b_media_type": "SDXC_UHS_II_V90",
            "bitrate_admission_mbps": 600,
            "slow_card_rejected_class": "SDXC_UHS_I_V30",
            "card_door_cap_hold_ms": 15,
            "rsv_salvage_target": "C0002.RSV->C0002.MXF",
            "bodydata_ufu_magic": "895546550d0a1a0a",
            "bodydata_bypass_budget_us": 100,
            "fx3_expected_model_id": "0x91030080",
            "fx30_rejected_model_id": "0x91030084",
            "recovery_5tier_ladder": [
                "TIER_1_EH1_47US_SD_BYPASS",
                "TIER_2_P15_ORIG_RESTORE_H0_EQ_H3",
                "TIER_3_P1_MODE_CLEAR_LINE1",
                "TIER_4_UART_460800_1V8_PASSIVE_TRIAGE",
                "TIER_5_EL3_ISP_READ_ONLY_LOCK",
            ],
        }
    r34_meta: Optional[Dict[str, Any]] = None
    if enable_r34:
        additions["etc/fx6_stage_r34"] = (
            (
                f"stage_r34=1\nr34_mode={r34_mode}\n"
                f"c2pa_rq_lic_erofs=1\nvmc_bncm1_ext_lk_24fps=1\n"
                f"imx510_8700us_gyro_xml=1\ncxd90058_sabin_ro=1\n"
                f"memcfg_1724m_pool=1\nsdi_raw_mew_masked=1\n"
                f"raid6_gf256_0x11d=1\nh0_eq_h3_16_surfaces=1\nlang={lang}\n"
            ).encode("utf-8"),
            0o100644,
        )
        r34_meta = {
            "r34_mode": r34_mode,
            "c2pa_cert_path": "p12:/cert/RQ_LIC.DAT",
            "vmc_bncm1_mode": "EXT-LK",
            "tc_fps": "24.00",
            "nrtm_xml_path": "/tmp/r34_clip/C0001M01.XML",
            "sensor": "IMX510",
            "imx510_readout_us": 8700,
            "imu_axes": 6,
            "ap_soc": "CXD90057_Mira",
            "cp_soc": "CXD90058_Cetus",
            "p8_cpapp_path": "p8:/cpapp-b.bin",
            "sabin_dir": "/usr/sabin",
            "memcfg_total_mib": 1724,
            "sdi_raw_fpga_blob": "mew.bin",
            "sdi_raw_masked": True,
            "raid6_gf256_poly": "0x11d",
            "raid6_gf256_gen": "0x02",
            "raid6_data_chunks": 11,
            "raid6_parity_chunks": 2,
            "seal_surface_count": 16,
        }
    r35_meta: Optional[Dict[str, Any]] = None
    if enable_r35:
        additions["etc/fx6_stage_r35"] = (
            (
                f"stage_r35=1\nr35_mode={r35_mode}\n"
                f"ssboot_wbi2_ro_lock=1\nblkroset_nflasha5=1\n"
                f"powerloss_100cycle_rsv=1\nslot1_bodydata_204_floor=1\n"
                f"c2pa_100_ceiling=1\nwpa2_wpa3_enforced=1\nlang={lang}\n"
            ).encode("utf-8"),
            0o100644,
        )
        r35_meta = {
            "r35_mode": r35_mode,
            "wbi2_partition": "/dev/nflasha5",
            "wbi2_plaintext_alias": "/dev/pnflasha5",
            "wbi2_magic_hex": "5742493200000000",
            "wbi2_sections": 1399,
            "tier0_receipt_magic": "FX3RCPT1",
            "blkroset_enforced": True,
            "suspend_disk_intercepted": True,
            "powerloss_cycles": 100,
            "brownout_mv": 6300,
            "rsv_salvage_target": "C0003.RSV->C0003.MXF",
            "eh1_budget_us": 50,
            "bodydata_min_version": "2.04",
            "bodydata_rejected_version": "2.02",
            "bodydata_bypass_budget_us": 100,
            "c2pa_max_licenses": 100,
            "p12_cert_path": "p12:/cert/RQ_LIC.DAT",
            "wpa2_wpa3_enforced": True,
        }
    r36_meta: Optional[Dict[str, Any]] = None
    if enable_r36:
        additions["etc/fx6_stage_r36"] = (
            (
                f"stage_r36=1\nr36_mode={r36_mode}\n"
                f"emount_info3d_breathing=1\np18_lensfile_erofs=1\n"
                f"hdmi_4264_raw_prores_braw=1\nsdi_mmio_masked=1\n"
                f"wpa2_wpa3_sanitizer=1\nfocusmap_ro_bridge=1\nlang={lang}\n"
            ).encode("utf-8"),
            0o100644,
        )
        r36_meta = {
            "r36_mode": r36_mode,
            "p18_lensfile_path": "p18:/lens/LENSFILE.BIN",
            "emount_packets": ["info7", "info8", "info3D"],
            "sony_lens_filter_expr": "((lens_id >> 14) == 3) && ((lens_id & 0x0FFF) != 0x0FFF)",
            "bkid_breathing_hex": "0x02cf0232",
            "sony_lens_id_example": "0xC123",
            "thirdparty_lens_id_example": "0x4123",
            "manual_lens_id_example": "0xFFFF",
            "hdmi_port": "Type-A",
            "hdmi_raw_resolution": "4264x2408",
            "hdmi_raw_fps": 60,
            "hdmi_raw_bit_depth": 16,
            "braw_recorder": "Blackmagic Video Assist 12G HDR 3.22+",
            "braw_rejected_recorder": "Blackmagic Video Assist 3G",
            "prores_raw_recorder": "Atomos Ninja",
            "sdi_mmio_probes": 0,
            "wpa2_wpa3_only": True,
            "rejected_legacy_wlan": ["WEP", "WPA1-TKIP", "IPsec"],
            "mc_client_min_version": "2.1.0",
            "backup_ro_path": "p2:/setting/Backup.bin",
        }
    r37_meta: Optional[Dict[str, Any]] = None
    if enable_r37:
        additions["etc/fx6_stage_r37"] = (
            (
                f"stage_r37=1\nr37_mode={r37_mode}\n"
                f"fx3a_firewall_50us=1\nfx3a_camset_blocked=1\n"
                f"xlrh1_4ch_mishoe=1\nbody35_override_sq_mute=1\n"
                f"fx3bndl1_serial_appledouble=1\nlang={lang}\n"
            ).encode("utf-8"),
            0o100644,
        )
        r37_meta = {
            "r37_mode": r37_mode,
            "fx3_model_id": "0x91030080",
            "fx3_fw_ver": "7.02",
            "fx3_lcd_dots": 1440000,
            "fx3a_fw_ver": "2.02",
            "fx3a_lcd_dots": 2359296,
            "fx3a_gate_budget_us": 50,
            "fx3a_reject_rc": -22,
            "fx3a_cross_import_rc": -79,
            "xlrh1_sample_rate_hz": 48000,
            "xlrh1_bit_depth": 24,
            "xlrh1_channels": 4,
            "xlrh1_monitor_matrix": "CH1+3/CH2+4",
            "body_35mm_overrides_mishoe": True,
            "sq_mutes_mishoe": True,
            "fx3bndl1_magic": "FX3BNDL1",
            "fx3rcpt1_magic": "FX3RCPT1",
            "transplant_reject_rc": -13,
            "appledouble_clutter_stripped": True,
        }
    r38_meta: Optional[Dict[str, Any]] = None
    if enable_r38:
        additions["etc/fx6_stage_r38"] = (
            (
                f"stage_r38=1\nr38_mode={r38_mode}\n"
                f"nouvc_gadget_firewall=1\nusblan_netstream_38mbps=1\n"
                f"usbpd_fz100_dcc1_65w_5a=1\ndualmedia_lut_path_asymmetry=1\n"
                f"cineei_800_12800=1\nrmtp1bt_ir_gps_mutex=1\n"
                f"clipflag_ok_ng_keep_hygiene=1\nlang={lang}\n"
            ).encode("utf-8"),
            0o100644,
        )
        r38_meta = {
            "r38_mode": r38_mode,
            "uvc_gadget_reject_rc": -95,
            "allowed_usb_modes": ["Sel. When Connect", "MSC", "MTP", "Remote Shooting", "USB-LAN"],
            "netstream_max_4k5994_mbps": 38,
            "body_pd_requires_fz100": True,
            "body_pd_no_fz100_rc": -19,
            "dcc1_min_watts": 65,
            "dcc1_min_amps": 5,
            "dcc1_requires_emarker": True,
            "sd_lut_prefix": "/Private/Sony/PRO/LUT/",
            "cfx_lut_prefix": "/Sony/PRO/LUT/",
            "lut_points_supported": [17, 33],
            "lut_max_filename_bytes": 63,
            "cineei_base_isos": [800, 12800],
            "cineei_highbase_ei_range": [3200, 51200],
            "rmtp1bt_bt_spec": "4.2",
            "rmtp1bt_masks_ir_and_gps": True,
            "clip_flags_supported": ["OK", "NG", "KEEP"],
            "p2_setting_writes": 0,
        }
    r39_meta: Optional[Dict[str, Any]] = None
    if enable_r39:
        additions["etc/fx6_stage_r39"] = (
            (
                f"stage_r39=1\nr39_mode={r39_mode}\n"
                f"fan_4mode_no_auto1_auto2=1\noff_in_rec_standby_max_pwm=1\n"
                f"always_off_backup_interlock=1\nshutter_speed_angle_independent=1\n"
                f"lut_601_vs_702_slot_firewall=1\nlang={lang}\n"
            ).encode("utf-8"),
            0o100644,
        )
        r39_meta = {
            "r39_mode": r39_mode,
            "fan_allowed_modes": ["Auto", "Minimum", "Off in Rec", "Always Off"],
            "fan_invalid_auto1_auto2_reject_rc": -22,
            "off_in_rec_standby_pwm_pct": 100,
            "off_in_rec_normal_rec_pwm_pct": 0,
            "always_off_backup_blocked_rc": -16,
            "auto_power_off_temp_modes": ["Standard", "High"],
            "shutter_modes": ["Speed", "Angle"],
            "shutter_angle_normal_range": "5.6deg..64F",
            "shutter_angle_120p_100p_sq_range": "5.6deg..360deg",
            "shutter_slots_independent": True,
            "exposure_step_drift_ev": 0.0,
            "lut_donor_stage_b_format": "FX6_6.01_LEGACY_SLOT_V1",
            "lut_stock_host_format": "FX3_7.00_7.02_OPTIMIZED_SLOT_V2",
            "lut_p2_direct_write_blocked_rc": -30,
            "lut_stage_b_overlay_dir": "/tmp/fx6_lut_overlay",
            "lut_user_slot_count": 16,
            "p2_setting_writes": 0,
        }
    r40_meta: Optional[Dict[str, Any]] = None
    if enable_r40:
        additions["etc/fx6_stage_r40"] = (
            (
                f"stage_r40=1\nr40_mode={r40_mode}\n"
                f"big6_home_6tile_no_end=1\nlower_left_aperture_nd_toggle=1\n"
                f"camset_slot1_dualmedia_split=1\nvmcbncm1_body_tcin_hdmi_tcout=1\nlang={lang}\n"
            ).encode("utf-8"),
            0o100644,
        )
        r40_meta = {
            "r40_mode": r40_mode,
            "big6_mode_settings_prerequisite": "Fixed/Variable",
            "big6_tiles": [
                "FPS",
                "ISO/Base ISO",
                "Shutter Speed/Angle",
                "Aperture/ND Filter",
                "Picture Profile/Select LUT",
                "White Balance",
            ],
            "big6_lower_left_modes": ["Aperture", "ND Filter"],
            "e_nd_actuator_reject_rc": -95,
            "e_nd_actuator_tx_count": 0,
            "camset_allowed_slot": 1,
            "camset_slot2_reject_rc": -22,
            "camset_max_profiles": 10,
            "camset_save_11th_reject_rc": -28,
            "camset_mr_mode_reject_rc": -16,
            "camset_cross_model_reject_rc": -79,
            "sd_camset_dir": "/PRIVATE/SONY/SETTING/FX3/CAMSET/",
            "cfx_camset_dir": "/SONY/SETTING/FX3/CAMSET/",
            "camset_stage_b_overlay_dir": "/tmp/fx6_camset_overlay",
            "vmcbncm1_part_no": "A-5051-506-A",
            "vmcbncm1_body_usb_port": "Multi/Micro USB",
            "vmcbncm1_ext_lk_min_ms": 10000,
            "vmcbncm1_handle_usb_reject_rc": -19,
            "vmcbncm1_bnc_tcout_reject_rc": -95,
            "hdmi_digital_tcout_port": "Type-A HDMI",
            "hdmi_tcout_sq_disabled": True,
            "p2_setting_writes": 0,
        }
    r41_meta: Optional[Dict[str, Any]] = None
    if enable_r41:
        additions["etc/fx6_stage_r41"] = (
            (
                f"stage_r41=1\nr41_mode={r41_mode}\n"
                f"desqueeze_165x_4locks=1\nexternal_mc_focusmap_150fps=1\n"
                f"simult_autoswitch_single_cont=1\nshockless_wb_kelvin_grid_bypass=1\nlang={lang}\n"
            ).encode("utf-8"),
            0o100644,
        )
        r41_meta = {
            "r41_mode": r41_mode,
            "desqueeze_ratios": ["Off", "1.3x", "2.0x", "1.5x", "1.6x"],
            "desqueeze_1_6x_actual_factor": 1.65,
            "desqueeze_1_6x_target_aspect": "2.39:1",
            "desqueeze_hard_locked_settings": [
                "Focus Mode=MF",
                "Focus Area=Wide",
                "SteadyShot=Off",
                "Face Priority in Multi Metering=Off",
            ],
            "desqueeze_suppress_conditions": [
                "RAW Output=On",
                "Rec. Media dur HDMI Output=Off(HDMI Only)",
                "Log Shooting=Off",
                "Remote Shooting",
                "Photo Mode",
            ],
            "hdmi_only_forces_info_display_off": True,
            "inbody_focusmap_menu_present": False,
            "inbody_focusmap_reject_rc": -95,
            "external_focusmap_app": "Monitor & Control",
            "external_focusmap_cutoff_fps": 150,
            "fx3_focusmap_low_fps_1_to_6_allowed": True,
            "focusmap_adapter_nonpdaf_reject_rc": -19,
            "focusmap_playback_reject_rc": -16,
            "simult_autoswitch_on_single_card_continuation": True,
            "simult_autoswitch_off_strict_parity_halt_rc": -28,
            "shockless_wb_modes": ["Off", "1 (Fast)", "2", "3 (Slow)"],
            "shockless_wb_max_fps": 240,
            "shockless_wb_ctemp_kelvin_transition_frames": 0,
            "shockless_wb_ab_gm_grid_transition_frames": 0,
            "p2_setting_writes": 0,
        }
    r42_meta: Optional[Dict[str, Any]] = None
    if enable_r42:
        additions["etc/fx6_stage_r42"] = (
            (
                f"stage_r42=1\nr42_mode={r42_mode}\n"
                f"hdmi_log1080_hdmionly_4k10b=1\nproxy_dualcodec_119p_atomic_vault=1\n"
                f"focusmag_automag_brightmon_lockout=1\nlang={lang}\n"
            ).encode("utf-8"),
            0o100644,
        )
        r42_meta = {
            "r42_mode": r42_mode,
            "hdmi_log_pplut_forced_resolution": "1920x1080",
            "hdmi_only_4k_modes": [
                "59.94p 10bit",
                "50p 10bit",
                "29.97p 10bit",
                "25p 10bit",
                "23.98p 10bit",
                "24.00p 10bit",
            ],
            "hdmi_only_internal_rec_reject_rc": -1,
            "hdmi_only_forces_info_display_off": True,
            "hdmi_only_suppresses_desqueeze": True,
            "hdmi_info_on_blanks_camera_lcd": True,
            "proxy_xavc_hs_hd": "1920x1080 10-bit HEVC 16M/9M (<=59.94p/50p)",
            "proxy_xavc_s_hd": "1280x720 8-bit AVC 6M (<=59.94p/50p)",
            "proxy_11988p_100p_cutoff_rc": -22,
            "proxy_oncamera_playback_reject_rc": -95,
            "proxy_px_badge_on_main_only": True,
            "proxy_uncoupled_delete_reject_rc": -18,
            "proxy_uncoupled_protect_reject_rc": -1,
            "focusmag_movie_scales": ["x1.0", "x4.0"],
            "focusmag_still_ff_scales": ["x1.0", "x2.1"],
            "focusmag_still_apsc_s35_scales": ["x1.0", "x1.5"],
            "automag_in_mf_movie_reject_rc": -95,
            "marker_display_suppressed_while_mag": True,
            "brightmon_lockout_while_mag_reject_rc": -16,
            "brightmon_forces_setting_effect_off": True,
            "p2_setting_writes": 0,
        }
    r43_meta: Optional[Dict[str, Any]] = None
    if enable_r43:
        additions["etc/fx6_stage_r43"] = (
            (
                f"stage_r43=1\nr43_mode={r43_mode}\n"
                f"filesettings_37char_sdhc_shotmark=1\ntc_regenerate_slot1_extlk_release=1\n"
                f"reclamp_coupled_rear_top_silent_lock=1\nlang={lang}\n"
            ).encode("utf-8"),
            0o100644,
        )
        r43_meta = {
            "r43_mode": r43_mode,
            "file_name_formats": [
                "Standard",
                "Cam ID + Reel#",
                "Title",
                "Date + Title",
                "Title + Date",
            ],
            "file_number_modes": ["Series", "Reset"],
            "title_name_max_ascii_chars": 37,
            "title_name_allowed_symbols": ".-_@!#$%+=^~(),;[]",
            "title_name_invalid_reject_rc": -22,
            "sdhc_fat32_forced_format": "Standard",
            "sdhc_non_standard_reject_rc": -22,
            "custom_movie_folder_reject_rc": -1,
            "shotmark_sidecar_pattern": "M4ROOT/CLIP/*M01.XML",
            "image_jump_modes": [
                "Shot Mark Only",
                "Shot Mark1 Only",
                "Shot Mark2 Only",
                "No Shot Mark",
            ],
            "ftp_target_movie_filter": "Only Shot Mark Mov.",
            "tc_regenerate_simult_source": "Slot 1",
            "tc_regenerate_forced_run_mode": "Rec Run",
            "ext_lk_drops_on_tc_make_or_run_change": True,
            "sq_tc_run_reject_rc": -95,
            "sq_hdmi_tc_output_reject_rc": -95,
            "rec_lamp_states": ["All On", "Only Front Off", "All Off"],
            "rec_lamp_rear_top_button_coupled": True,
            "rec_lamp_uncoupled_split_reject_rc": -22,
            "silent_mode_forces_audio_signals_off": True,
            "audio_signals_locked_while_silent_rc": -16,
            "p2_setting_writes": 0,
        }
    r44_meta: Optional[Dict[str, Any]] = None
    if enable_r44:
        additions["etc/fx6_stage_r44"] = (
            (
                f"stage_r44=1\nr44_mode={r44_mode}\n"
                f"pixelmap_autorestart_cnflasha_ro=1\nntscpal_dfn_camreset_survival=1\n"
                f"gammaassist_4mode_displaylut_split=1\nlang={lang}\n"
            ).encode("utf-8"),
            0o100644,
        )
        r44_meta = {
            "r44_mode": r44_mode,
            "auto_pixel_mapping_default": "On",
            "auto_pixel_mapping_poweroff_shutter_in_silent_mode": True,
            "auto_pixel_mapping_off_manual_cadence_days": 3,
            "manual_pixel_mapping_low_battery_reject_rc": -11,
            "manual_pixel_mapping_op_lockout_rc": -16,
            "manual_pixel_mapping_triggers_auto_restart_tmp_wipe": True,
            "cnflasha_ro_open_reject_rc": -30,
            "cnflasha_userspace_firewall_reject_rc": -1,
            "cnflasha_write_count": 0,
            "ntsc_frame_rates": ["23.98p", "29.97p", "59.94p", "119.88p"],
            "pal_frame_rates": ["25p", "50p", "100p"],
            "ntsc_tc_formats": ["DF", "NDF"],
            "pal_2398p_reject_rc": -22,
            "pal_tc_df_ndf_reject_rc": -95,
            "startup_banners": ["Running on NTSC.", "Running on PAL."],
            "ntsc_pal_survives_camera_settings_reset": True,
            "initialize_restores_regional_default": True,
            "gamma_disp_assist_types": [
                "Auto",
                "S-Log3->709(800%)",
                "HLG(BT.2020)",
                "HLG(709)",
            ],
            "slog2_assist_reject_rc": -22,
            "log_shooting_locks_gamma_assist_off_rc": -16,
            "gamma_assist_hdmi_applied": 0,
            "p2_setting_writes": 0,
        }
    r45_meta: Optional[Dict[str, Any]] = None
    if enable_r45:
        additions["etc/fx6_stage_r45"] = (
            (
                f"stage_r45=1\nr45_mode={r45_mode}\n"
                f"steadyshot_active_3cutoffs_110crop=1\nciz_4locks_hfr_raw_cutoffs=1\n"
                f"powersave_9cond_autotemp_high_tripod=1\nlang={lang}\n"
            ).encode("utf-8"),
            0o100644,
        )
        r45_meta = {
            "r45_mode": r45_mode,
            "steadyshot_movie_modes": ["Off", "Standard", "Active"],
            "steadyshot_active_crop_factor": 1.1,
            "steadyshot_active_crop_x100": 110,
            "steadyshot_active_3_cutoffs": [
                "Normal Rec Frame Rate 119.88p/100p",
                "S&Q Frame Rate >=120fps/100fps (100/120/200/240fps)",
                "HDMI Output Settings RAW Output=On",
            ],
            "steadyshot_normal_hfr_reject_rc": -22,
            "steadyshot_sq_hfr_reject_rc": -22,
            "steadyshot_hdmi_raw_reject_rc": -16,
            "zoom_unavailable_raw_formats": ["RAW", "RAW & JPEG", "RAW & HEIF"],
            "zoom_unavailable_normal_rates": ["119.88p", "100p"],
            "zoom_unavailable_sq_rates": ["100fps", "120fps", "200fps", "240fps"],
            "ciz_4_camera_state_locks": [
                "Focus Area disabled (center-priority AF)",
                "Metering Mode hard-locked to Multi",
                "Face/Eye Prior. in AF & Face Priority in Multi Metering unavailable",
                "Real-time Tracking unavailable",
            ],
            "ciz_focus_area_lock_rc": -16,
            "ciz_metering_multi_lock_rc": -16,
            "ciz_face_eye_and_tracking_reject_rc": -95,
            "power_save_menu_string": "Power Save Start Time",
            "power_save_default": "5 Min",
            "power_save_default_sec": 300,
            "power_save_9_deactivation_conditions": [
                "USB power supply",
                "slideshow playback",
                "FTP transfer",
                "movie recording",
                "computer connection",
                "TV / HDMI connection",
                "IR Remote Ctrl=On",
                "Bluetooth Rmt Ctrl=On",
                "streaming or Creators' Cloud upload",
            ],
            "airgapped_p3_75mib_allowed_power_save": ["Off", "30 Min"],
            "airgapped_p3_75mib_5min_reject_rc": -16,
            "auto_power_off_temp_modes": ["Standard", "High"],
            "auto_power_off_temp_high_requires_tripod": True,
            "auto_power_off_temp_handheld_reject_rc": -1,
            "p2_setting_writes": 0,
        }
    r46_meta: Optional[Dict[str, Any]] = None
    if enable_r46:
        additions["etc/fx6_stage_r46"] = (
            (
                f"stage_r46=1\nr46_mode={r46_mode}\n"
                f"sq_fixedvar_6locks=1\nzebra_camreset_peaking_hdmi_zero=1\n"
                f"slot1_fullformat_chord_vault_firewall=1\nlang={lang}\n"
            ).encode("utf-8"),
            0o100644,
        )
        r46_meta = {
            "r46_mode": r46_mode,
            "mode_settings_fixed_variable": "Fixed/Variable",
            "mode_settings_locks_sq_settings_rc": -16,
            "direct_fps_controls": ["FPS", "Home (FPS)"],
            "sq_6_hard_lockouts": [
                "0ch no sound recorded",
                "[Audio Out Timing] (Live/Lip Sync) disabled",
                "[Time Code Run] & [Time Code Output] unavailable",
                "240fps/200fps blocked on XAVC HS 4K, XAVC S 4K, XAVC S-I 4K, XAVC S-I DCI 4K",
                "120fps/100fps blocked on XAVC S-I DCI 4K (4096x2160)",
                "[Proxy Recording] blocked when Rec Frame Rate is 119.88p/100p OR Frame Rate >= 120/100fps",
            ],
            "sq_240_200_blocked_4k_formats": [
                "XAVC HS 4K",
                "XAVC S 4K",
                "XAVC S-I 4K",
                "XAVC S-I DCI 4K",
            ],
            "sq_120_100_blocked_dci_format": "XAVC S-I DCI 4K",
            "audio_out_timing_modes": ["Live", "Lip Sync"],
            "zebra_display_modes": ["Off", "On"],
            "zebra_wheel_left_default": "Zebra Display Select",
            "zebra_8_preset_levels": ["70", "75", "80", "85", "90", "95", "100", "100+"],
            "zebra_custom_levels": [
                "Custom 1 (Standard+Range)",
                "Custom 2 (Minimum/Lower-Limit)",
            ],
            "zebra_survives_camera_settings_reset": True,
            "zebra_reset_only_by_initialize": True,
            "peaking_levels": ["High", "Mid", "Low"],
            "peaking_colors": ["Red", "Yellow", "Blue", "White"],
            "hdmi_zebra_overlay_pixels": 0,
            "hdmi_peaking_overlay_pixels": 0,
            "format_modes": ["Quick Format", "Full Format"],
            "full_format_toggle_key": "(Delete)",
            "menu_delete_chord_hold_ms": 2000,
            "slot1_tier0_vault_artifacts": ["pnflasha", "cnflasha", "CAMSET01.DAT"],
            "slot1_vault_active_reject_rc": -16,
            "slot1_vault_wp_reject_rc": -13,
            "slot1_format_writes": 0,
            "p2_setting_writes": 0,
        }
    r47_meta: Optional[Dict[str, Any]] = None
    if enable_r47:
        additions["etc/fx6_stage_r47"] = (
            (
                f"stage_r47=1\nr47_mode={r47_mode}\n"
                f"silent_autopixelmap_no_pwrshutter=1\nmarker_15ratio_camreset_hdmi_zero=1\n"
                f"flexexp_avtviso_autoslowshutter_split=1\nlang={lang}\n"
            ).encode("utf-8"),
            0o100644,
        )
        r47_meta = {
            "r47_mode": r47_mode,
            "silent_mode_locks": {
                "Shutter Type": "Electronic Shutter",
                "Shutter Type in Interval": "Electronic Shutter",
                "Audio signals": "Off",
            },
            "silent_locks_reject_rc": -16,
            "silent_5_disabled_functions": [
                "Flash",
                "Long Exposure NR",
                "e-Front Curtain Shut.",
                "BULB",
                "Anti-flicker Shoot.",
            ],
            "silent_disabled_reject_rc": -95,
            "target_function_settings": [
                "Aperture Drive in AF",
                "Auto Pixel Mapping",
            ],
            "autopixelmap_targeted_suppresses_pwroff_cal": True,
            "autopixelmap_not_target_retains_setting": True,
            "pwroff_cnflasha_touches": 0,
            "fx3_sensor_items_present": [
                "Sensor Cleaning",
                "Auto Pixel Mapping",
                "Pixel Mapping",
            ],
            "fx3_absent_menu_item": "Shutter When Pwr OFF",
            "shutter_when_pwroff_reject_rc": -2,
            "marker_display_subitems": [
                "Marker Display",
                "Center Marker",
                "Aspect Marker",
                "Safety Zone",
                "Guideframe",
            ],
            "aspect_marker_15_ratios": [
                "9:16",
                "4:5",
                "1:1",
                "4:3",
                "13:9",
                "14:9",
                "15:9",
                "16:9",
                "17:9",
                "1.66:1",
                "1.85:1",
                "1.91:1",
                "2:1",
                "2.35:1",
                "2.39:1",
            ],
            "ver300_added_aspect_ratio": "16:9",
            "safety_zone_modes": ["Off", "80%", "90%"],
            "guideframe_modes": ["Off", "On"],
            "marker_survives_camera_settings_reset": True,
            "marker_reset_only_by_initialize": True,
            "hdmi_marker_overlay_pixels": 0,
            "exposure_ctrl_types": ["P/A/S/M Mode", "Flexible Exp. Mode"],
            "pasm_submodes": [
                "Program Auto",
                "Aperture Priority",
                "Shutter Priority",
                "Manual Exposure",
            ],
            "auto_manual_swt_set_channels": [
                "Av Auto/Manual Switch",
                "Tv Auto/Manual Switch",
                "ISO Auto/Manual Set",
            ],
            "auto_manual_swt_set_default": "Manual",
            "auto_slow_shutter_default": "On",
            "camera_settings_reset_restores_av_tv_iso_manual": True,
            "camera_settings_reset_restores_auto_slow_shutter_on": True,
            "camera_settings_reset_preserves_marker_zebra_ntscpal": True,
            "p2_setting_writes": 0,
        }
    r48_meta: Optional[Dict[str, Any]] = None
    if enable_r48:
        additions["etc/fx6_stage_r48"] = (
            (
                f"stage_r48=1\nr48_mode={r48_mode}\n"
                f"recover_imagedb_battery_vault=1\nmonitor_flip_camreset_playback_non_invert=1\n"
                f"af_trans7_shiftsens5_interval_still=1\nlang={lang}\n"
            ).encode("utf-8"),
            0o100644,
        )
        r48_meta = {
            "r48_mode": r48_mode,
            "recover_imagedb_menu_item": "Recover Image DB",
            "recover_imagedb_target_slots": ["Slot 1", "Slot 2"],
            "depleted_battery_refusal_rc": -11,
            "brownout_guard_refusal_rc": -16,
            "depleted_pre_touch_writes": 0,
            "avf_info_repair_non_deleting": True,
            "deleted_clips": 0,
            "action_item_immune_camera_settings_reset": True,
            "action_item_immune_initialize": True,
            "slot1_vault_unverified_block_rc": -16,
            "slot1_vault_wp_block_rc": -13,
            "slot1_kernel_ro_block_rc": -30,
            "slot1_imagedb_writes": 0,
            "monitor_flip_menu_item": "Monitor Flip Direction",
            "monitor_flip_4_modes": [
                "Auto",
                "Horizontal Flip",
                "Vertical Flip",
                "Off",
            ],
            "monitor_flip_default": "Auto",
            "monitor_flip_survives_camera_settings_reset": True,
            "monitor_flip_reset_only_by_initialize": True,
            "shooting_lcd_hflip_mirrors_horizontally": True,
            "playback_hflip_inverted_frames": 0,
            "hdmi_clean_feed_flipped_frames": 0,
            "af_transition_speed_menu_item": "AF Transition Speed",
            "af_transition_speed_steps": [1, 2, 3, 4, 5, 6, 7],
            "af_transition_speed_default": 5,
            "af_subj_shift_sens_exact_menu_item": "AF Subj. Shift Sensitivity",
            "af_subj_shift_sens_rejected_abbrev": "AF Subj. Shift Sens.",
            "af_subj_shift_sens_steps": [1, 2, 3, 4, 5],
            "af_subj_shift_sens_default": 5,
            "af_kinematics_scope": ["Movie", "S&Q Motion"],
            "af_kinematics_still_reject_rc": -95,
            "camera_settings_reset_restores_af_5_5": True,
            "interval_shoot_func_menu_item": "Interval Shoot Func.",
            "interval_shoot_scope": "Still Image Only",
            "interval_start_time_sec_range": [1, 5999],
            "interval_shoot_interval_sec_range": [1, 60],
            "interval_num_shots_range": [1, 9999],
            "video_interval_rec_mode_reject_rc": -22,
            "video_interval_rec_exec_reject_rc": -1,
            "cnflasha_writes": 0,
            "emmc_write_count": 0,
            "p2_setting_writes": 0,
        }
    r49_meta: Optional[Dict[str, Any]] = None
    if enable_r49:
        additions["etc/fx6_stage_r49"] = (
            (
                f"stage_r49=1\nr49_mode={r49_mode}\n"
                f"emph_rec_grid_hdmi_clean_lock=1\ntouch_op_4item_camreset_vault_firewall=1\n"
                f"monitor_brightness_sunny_indoor_clamp=1\nlang={lang}\n"
            ).encode("utf-8"),
            0o100644,
        )
        r49_meta = {
            "r49_mode": r49_mode,
            "emphasized_rec_display_menu_item": "Emphasized REC Display",
            "emphasized_rec_display_default": "On",
            "emphasized_rec_display_reset_by_camera_settings_reset": True,
            "emphasized_rec_display_scope": ["Movie", "S&Q Motion"],
            "grid_line_display_menu_item": "Grid Line Display",
            "grid_line_type_menu_item": "Grid Line Type",
            "grid_line_3_types": [
                "Rule of 3rds Grid",
                "Square Grid",
                "Diag. + Square Grid",
            ],
            "grid_line_type_default": "Rule of 3rds Grid",
            "grid_line_survives_camera_settings_reset": True,
            "grid_line_reset_only_by_initialize": True,
            "hdmi_info_display_on_routes_recframe_and_grid": True,
            "hdmi_info_display_on_blanks_local_lcd": True,
            "hdmi_marker_zebra_peaking_overlay_pixels": 0,
            "rec_media_dur_hdmi_off_hdmi_only_forces_hdmi_info_off": True,
            "hdmi_raw_output_forces_hdmi_info_off": True,
            "hdmi_only_or_raw_baked_recframe_grid_pixels": 0,
            "touch_setup_4_items": [
                "Touch Operation",
                "Touch Sensitivity",
                "Swipe Up",
                "Touch Func. in Shooting",
            ],
            "touch_operation_3_modes": ["On", "On: Playback Only", "Off"],
            "touch_operation_default": "On",
            "touch_sensitivity_2_modes": ["Standard", "Sensitive"],
            "touch_sensitivity_default": "Standard",
            "swipe_up_default": "Open the Fn Menu",
            "touch_func_in_shooting_3_modes": ["Touch Tracking", "Touch Focus", "Off"],
            "touch_func_in_shooting_default": "Touch Tracking",
            "touch_4_items_survive_camera_settings_reset": True,
            "touch_reset_only_by_initialize": True,
            "bench_accidental_touch_events": 0,
            "monitor_brightness_menu_item": "Monitor Brightness",
            "monitor_brightness_modes": ["Manual", "Sunny Weather"],
            "monitor_brightness_default_mode": "Manual",
            "monitor_brightness_manual_step_range": [-2, -1, 0, 1, 2],
            "monitor_brightness_default_step": 0,
            "monitor_brightness_survives_camera_settings_reset": True,
            "monitor_brightness_reset_only_by_initialize": True,
            "indoor_sunny_weather_clamped_to_manual_0": True,
            "indoor_sunny_weather_unclamped": 0,
            "slot1_vault_writes": 0,
            "cnflasha_writes": 0,
            "emmc_write_count": 0,
            "p2_setting_writes": 0,
        }
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
        "r29_enabled": enable_r29,
        "r30_enabled": enable_r30,
        "r31_enabled": enable_r31,
        "r32_enabled": enable_r32,
        "r33_enabled": enable_r33,
        "r34_enabled": enable_r34,
        "r35_enabled": enable_r35,
        "r36_enabled": enable_r36,
        "r37_enabled": enable_r37,
        "r38_enabled": enable_r38,
        "r39_enabled": enable_r39,
        "r40_enabled": enable_r40,
        "r41_enabled": enable_r41,
        "r42_enabled": enable_r42,
        "r43_enabled": enable_r43,
        "r44_enabled": enable_r44,
        "r45_enabled": enable_r45,
        "r46_enabled": enable_r46,
        "r47_enabled": enable_r47,
        "r48_enabled": enable_r48,
        "r49_enabled": enable_r49,
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
    if r29_meta is not None:
        stage_a_meta["r29"] = r29_meta
    if r30_meta is not None:
        stage_a_meta["r30"] = r30_meta
    if r31_meta is not None:
        stage_a_meta["r31"] = r31_meta
    if r32_meta is not None:
        stage_a_meta["r32"] = r32_meta
    if r33_meta is not None:
        stage_a_meta["r33"] = r33_meta
    if r34_meta is not None:
        stage_a_meta["r34"] = r34_meta
    if r35_meta is not None:
        stage_a_meta["r35"] = r35_meta
    if r36_meta is not None:
        stage_a_meta["r36"] = r36_meta
    if r37_meta is not None:
        stage_a_meta["r37"] = r37_meta
    if r38_meta is not None:
        stage_a_meta["r38"] = r38_meta
    if r39_meta is not None:
        stage_a_meta["r39"] = r39_meta
    if r40_meta is not None:
        stage_a_meta["r40"] = r40_meta
    if r41_meta is not None:
        stage_a_meta["r41"] = r41_meta
    if r42_meta is not None:
        stage_a_meta["r42"] = r42_meta
    if r43_meta is not None:
        stage_a_meta["r43"] = r43_meta
    if r44_meta is not None:
        stage_a_meta["r44"] = r44_meta
    if r45_meta is not None:
        stage_a_meta["r45"] = r45_meta
    if r46_meta is not None:
        stage_a_meta["r46"] = r46_meta
    if r47_meta is not None:
        stage_a_meta["r47"] = r47_meta
    if r48_meta is not None:
        stage_a_meta["r48"] = r48_meta
    if r49_meta is not None:
        stage_a_meta["r49"] = r49_meta
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
        "FX6_R29_",
        "FX6_R30_",
        "FX6_R31_",
        "FX6_R32_",
        "FX6_R33_",
        "FX6_R34_",
        "FX6_R35_",
        "FX6_R36_",
        "FX6_R37_",
        "FX6_R38_",
        "FX6_R39_",
        "FX6_R40_",
        "FX6_R41_",
        "FX6_R42_",
        "FX6_R43_",
        "FX6_R44_",
        "FX6_R45_",
        "FX6_R46_",
        "FX6_R47_",
        "FX6_R48_",
        "FX6_R49_",
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
    last_r29_install: Optional[Dict[str, Any]] = None
    last_r29_rollback: Optional[Dict[str, Any]] = None
    last_r29_p1_rescue: Optional[Dict[str, Any]] = None
    last_r29_mpr_param: Optional[Dict[str, Any]] = None
    last_r29_mpr_rec: Optional[Dict[str, Any]] = None
    last_r29_lang: Optional[Dict[str, Any]] = None
    last_r29_bridge: Optional[Dict[str, Any]] = None
    r29_install_rc: Optional[int] = None
    r29_rollback_rc: Optional[int] = None
    r29_p1_rescue_rc: Optional[int] = None
    last_r30_ram_canary: Optional[Dict[str, Any]] = None
    last_r30_tier0_backup: Optional[Dict[str, Any]] = None
    last_r30_peripheral_init: Optional[Dict[str, Any]] = None
    last_r30_peripheral_bridge: Optional[Dict[str, Any]] = None
    last_r30_jbusy_abort: Optional[Dict[str, Any]] = None
    last_r30_h0_h3_uninstall: Optional[Dict[str, Any]] = None
    last_r30_lang: Optional[Dict[str, Any]] = None
    last_r30_bridge: Optional[Dict[str, Any]] = None
    r30_canary_tier0_rc: Optional[int] = None
    r30_jbusy_uninstall_rc: Optional[int] = None
    last_r31_keymap_tally_init: Optional[Dict[str, Any]] = None
    last_r31_keymap_tally_bridge: Optional[Dict[str, Any]] = None
    last_r31_fan_thermal: Optional[Dict[str, Any]] = None
    last_r31_fz100_power: Optional[Dict[str, Any]] = None
    last_r31_mtdro_firewall: Optional[Dict[str, Any]] = None
    last_r31_lang: Optional[Dict[str, Any]] = None
    last_r31_bridge: Optional[Dict[str, Any]] = None
    r31_fan_fz100_rc: Optional[int] = None
    r31_mtdro_rc: Optional[int] = None
    last_r32_imx510_cube_init: Optional[Dict[str, Any]] = None
    last_r32_imx510_cube_bridge: Optional[Dict[str, Any]] = None
    last_r32_cdcncm_usb_0da1: Optional[Dict[str, Any]] = None
    last_r32_uart_6stage: Optional[Dict[str, Any]] = None
    r32_uart_checkpoints: List[Dict[str, Any]] = []
    last_r32_lang: Optional[Dict[str, Any]] = None
    last_r32_bridge: Optional[Dict[str, Any]] = None
    r32_cdcncm_rc: Optional[int] = None
    r32_uart_rc: Optional[int] = None
    last_r33_cfexpress_rsv_init: Optional[Dict[str, Any]] = None
    last_r33_cfexpress_rsv_bridge: Optional[Dict[str, Any]] = None
    last_r33_bodydata_ufu_bypass: Optional[Dict[str, Any]] = None
    last_r33_recovery_5tier: Optional[Dict[str, Any]] = None
    r33_tier_steps: List[Dict[str, Any]] = []
    last_r33_lang: Optional[Dict[str, Any]] = None
    last_r33_bridge: Optional[Dict[str, Any]] = None
    r33_ufu_bypass_rc: Optional[int] = None
    r33_5tier_rc: Optional[int] = None
    last_r34_c2pa_tc_gyro_init: Optional[Dict[str, Any]] = None
    last_r34_c2pa_tc_gyro_bridge: Optional[Dict[str, Any]] = None
    last_r34_cxd90058_sabin: Optional[Dict[str, Any]] = None
    last_r34_raid6_seal_16: Optional[Dict[str, Any]] = None
    last_r34_lang: Optional[Dict[str, Any]] = None
    last_r34_bridge: Optional[Dict[str, Any]] = None
    r34_cxd90058_sabin_rc: Optional[int] = None
    r34_raid6_seal16_rc: Optional[int] = None
    last_r35_ssboot_wbi2_init: Optional[Dict[str, Any]] = None
    last_r35_ssboot_wbi2_bridge: Optional[Dict[str, Any]] = None
    last_r35_powerloss_100cycle: Optional[Dict[str, Any]] = None
    last_r35_slot1_ufu_c2pa: Optional[Dict[str, Any]] = None
    last_r35_lang: Optional[Dict[str, Any]] = None
    last_r35_bridge: Optional[Dict[str, Any]] = None
    r35_powerloss_rc: Optional[int] = None
    r35_slot1_ufu_rc: Optional[int] = None
    last_r36_emount_info3d_init: Optional[Dict[str, Any]] = None
    last_r36_emount_info3d_bridge: Optional[Dict[str, Any]] = None
    last_r36_hdmi_4264_raw: Optional[Dict[str, Any]] = None
    last_r36_wpa3_focusmap: Optional[Dict[str, Any]] = None
    last_r36_lang: Optional[Dict[str, Any]] = None
    last_r36_bridge: Optional[Dict[str, Any]] = None
    r36_hdmi_raw_rc: Optional[int] = None
    r36_wpa3_focusmap_rc: Optional[int] = None
    last_r37_fx3a_firewall_init: Optional[Dict[str, Any]] = None
    last_r37_fx3a_firewall_bridge: Optional[Dict[str, Any]] = None
    last_r37_xlrh1_4ch_bridge: Optional[Dict[str, Any]] = None
    last_r37_xlrh1_4ch: Optional[Dict[str, Any]] = None
    last_r37_fx3bndl1_serial: Optional[Dict[str, Any]] = None
    last_r37_lang: Optional[Dict[str, Any]] = None
    last_r37_bridge: Optional[Dict[str, Any]] = None
    r37_xlrh1_rc: Optional[int] = None
    r37_fx3bndl1_rc: Optional[int] = None
    last_r38_nouvc_dcc1_pd_init: Optional[Dict[str, Any]] = None
    last_r38_nouvc_dcc1_pd_bridge: Optional[Dict[str, Any]] = None
    last_r38_lut_cineei_bridge: Optional[Dict[str, Any]] = None
    last_r38_lut_path_cineei: Optional[Dict[str, Any]] = None
    last_r38_rmtp1bt_clipflag: Optional[Dict[str, Any]] = None
    last_r38_lang: Optional[Dict[str, Any]] = None
    last_r38_bridge: Optional[Dict[str, Any]] = None
    r38_lut_cineei_rc: Optional[int] = None
    r38_rmtp1bt_rc: Optional[int] = None
    last_r39_fan_pwm_init: Optional[Dict[str, Any]] = None
    last_r39_fan_pwm_bridge: Optional[Dict[str, Any]] = None
    last_r39_shutter_lut_bridge: Optional[Dict[str, Any]] = None
    last_r39_shutter_speed_angle: Optional[Dict[str, Any]] = None
    last_r39_lut_601_702_firewall: Optional[Dict[str, Any]] = None
    last_r39_lang: Optional[Dict[str, Any]] = None
    last_r39_bridge: Optional[Dict[str, Any]] = None
    r39_shutter_rc: Optional[int] = None
    r39_lut_split_rc: Optional[int] = None
    last_r40_big6_noend_init: Optional[Dict[str, Any]] = None
    last_r40_big6_noend_bridge: Optional[Dict[str, Any]] = None
    last_r40_camset_tc_bridge: Optional[Dict[str, Any]] = None
    last_r40_camset_slot1_split: Optional[Dict[str, Any]] = None
    last_r40_vmcbncm1_tcin_hdmi: Optional[Dict[str, Any]] = None
    last_r40_lang: Optional[Dict[str, Any]] = None
    last_r40_bridge: Optional[Dict[str, Any]] = None
    r40_camset_rc: Optional[int] = None
    r40_vmcbncm1_rc: Optional[int] = None
    last_r41_desqueeze_165x_init: Optional[Dict[str, Any]] = None
    last_r41_desqueeze_bridge: Optional[Dict[str, Any]] = None
    last_r41_focusmap_simult_wb_bridge: Optional[Dict[str, Any]] = None
    last_r41_external_focusmap_150fps: Optional[Dict[str, Any]] = None
    last_r41_simult_shocklesswb: Optional[Dict[str, Any]] = None
    last_r41_lang: Optional[Dict[str, Any]] = None
    last_r41_bridge: Optional[Dict[str, Any]] = None
    r41_focusmap_rc: Optional[int] = None
    r41_simult_wb_rc: Optional[int] = None
    last_r42_hdmi_log1080_init: Optional[Dict[str, Any]] = None
    last_r42_hdmi_log1080_bridge: Optional[Dict[str, Any]] = None
    last_r42_proxy_vault_bridge: Optional[Dict[str, Any]] = None
    last_r42_focusmag_brightmon_bridge: Optional[Dict[str, Any]] = None
    last_r42_proxy_vault: Optional[Dict[str, Any]] = None
    last_r42_focusmag_brightmon: Optional[Dict[str, Any]] = None
    last_r42_lang: Optional[Dict[str, Any]] = None
    last_r42_bridge: Optional[Dict[str, Any]] = None
    r42_proxy_vault_rc: Optional[int] = None
    r42_focusmag_brightmon_rc: Optional[int] = None
    last_r43_filesettings_shotmark_init: Optional[Dict[str, Any]] = None
    last_r43_filesettings_shotmark_bridge: Optional[Dict[str, Any]] = None
    last_r43_tc_regenerate_bridge: Optional[Dict[str, Any]] = None
    last_r43_reclamp_silent_bridge: Optional[Dict[str, Any]] = None
    last_r43_tc_regenerate: Optional[Dict[str, Any]] = None
    last_r43_reclamp_silent: Optional[Dict[str, Any]] = None
    last_r43_lang: Optional[Dict[str, Any]] = None
    last_r43_bridge: Optional[Dict[str, Any]] = None
    r43_tc_regenerate_rc: Optional[int] = None
    r43_reclamp_silent_rc: Optional[int] = None
    last_r44_pixelmap_cnflasha_init: Optional[Dict[str, Any]] = None
    last_r44_pixelmap_cnflasha_bridge: Optional[Dict[str, Any]] = None
    last_r44_ntscpal_camreset_bridge: Optional[Dict[str, Any]] = None
    last_r44_gammaassist_displaylut_bridge: Optional[Dict[str, Any]] = None
    last_r44_ntscpal_camreset: Optional[Dict[str, Any]] = None
    last_r44_gammaassist_displaylut: Optional[Dict[str, Any]] = None
    last_r44_lang: Optional[Dict[str, Any]] = None
    last_r44_bridge: Optional[Dict[str, Any]] = None
    r44_ntscpal_camreset_rc: Optional[int] = None
    r44_gammaassist_displaylut_rc: Optional[int] = None
    last_r45_steadyshot_active_init: Optional[Dict[str, Any]] = None
    last_r45_steadyshot_active_bridge: Optional[Dict[str, Any]] = None
    last_r45_ciz_4locks_bridge: Optional[Dict[str, Any]] = None
    last_r45_powersave_autotemp_bridge: Optional[Dict[str, Any]] = None
    last_r45_ciz_4locks: Optional[Dict[str, Any]] = None
    last_r45_powersave_autotemp: Optional[Dict[str, Any]] = None
    last_r45_lang: Optional[Dict[str, Any]] = None
    last_r45_bridge: Optional[Dict[str, Any]] = None
    r45_ciz_4locks_rc: Optional[int] = None
    r45_powersave_autotemp_rc: Optional[int] = None
    last_r46_sq_fixedvar_init: Optional[Dict[str, Any]] = None
    last_r46_sq_fixedvar_bridge: Optional[Dict[str, Any]] = None
    last_r46_zebra_peaking_bridge: Optional[Dict[str, Any]] = None
    last_r46_fullformat_vault_bridge: Optional[Dict[str, Any]] = None
    last_r46_zebra_peaking_hdmi: Optional[Dict[str, Any]] = None
    last_r46_fullformat_chord_vault: Optional[Dict[str, Any]] = None
    last_r46_lang: Optional[Dict[str, Any]] = None
    last_r46_bridge: Optional[Dict[str, Any]] = None
    r46_zebra_peaking_hdmi_rc: Optional[int] = None
    r46_fullformat_chord_vault_rc: Optional[int] = None
    last_r47_silent_autopixelmap_init: Optional[Dict[str, Any]] = None
    last_r47_silent_autopixelmap_bridge: Optional[Dict[str, Any]] = None
    last_r47_marker_15ratio_bridge: Optional[Dict[str, Any]] = None
    last_r47_flexexp_reset_bridge: Optional[Dict[str, Any]] = None
    last_r47_marker_15ratio_hdmi: Optional[Dict[str, Any]] = None
    last_r47_flexexp_reset_split: Optional[Dict[str, Any]] = None
    last_r47_lang: Optional[Dict[str, Any]] = None
    last_r47_bridge: Optional[Dict[str, Any]] = None
    r47_marker_15ratio_hdmi_rc: Optional[int] = None
    r47_flexexp_reset_split_rc: Optional[int] = None
    last_r48_monitor_flip_init: Optional[Dict[str, Any]] = None
    last_r48_recover_imagedb_bridge: Optional[Dict[str, Any]] = None
    last_r48_monitor_flip_bridge: Optional[Dict[str, Any]] = None
    last_r48_af_sens_interval_bridge: Optional[Dict[str, Any]] = None
    last_r48_recover_imagedb_vault: Optional[Dict[str, Any]] = None
    last_r48_af_sens_interval: Optional[Dict[str, Any]] = None
    last_r48_lang: Optional[Dict[str, Any]] = None
    last_r48_bridge: Optional[Dict[str, Any]] = None
    r48_recover_imagedb_vault_rc: Optional[int] = None
    r48_af_sens_interval_rc: Optional[int] = None
    last_r49_emph_rec_grid_hdmi_init: Optional[Dict[str, Any]] = None
    last_r49_emph_rec_grid_hdmi_bridge: Optional[Dict[str, Any]] = None
    last_r49_touch_op_bridge: Optional[Dict[str, Any]] = None
    last_r49_monitor_brightness_bridge: Optional[Dict[str, Any]] = None
    last_r49_touch_op_vault: Optional[Dict[str, Any]] = None
    last_r49_monitor_brightness: Optional[Dict[str, Any]] = None
    last_r49_lang: Optional[Dict[str, Any]] = None
    last_r49_bridge: Optional[Dict[str, Any]] = None
    r49_touch_op_vault_rc: Optional[int] = None
    r49_monitor_brightness_rc: Optional[int] = None
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
        elif "FX6_R29_ATOMIC_INSTALL " in line:
            last_r29_install = _parse_kv_ints(line.split("FX6_R29_ATOMIC_INSTALL ", 1)[1])
        elif "FX6_R29_ATOMIC_ROLLBACK " in line:
            last_r29_rollback = _parse_kv_ints(line.split("FX6_R29_ATOMIC_ROLLBACK ", 1)[1])
        elif "FX6_R29_P1_RESCUE " in line:
            last_r29_p1_rescue = _parse_kv_ints(line.split("FX6_R29_P1_RESCUE ", 1)[1])
        elif "FX6_R29_MPR_PARAM_SHIM " in line:
            last_r29_mpr_param = _parse_kv_ints(line.split("FX6_R29_MPR_PARAM_SHIM ", 1)[1])
        elif "FX6_R29_MPR_REC_CYCLE " in line:
            last_r29_mpr_rec = _parse_kv_ints(line.split("FX6_R29_MPR_REC_CYCLE ", 1)[1])
        elif "FX6_R29_LANG_TELEMETRY " in line:
            last_r29_lang = _parse_kv_ints(line.split("FX6_R29_LANG_TELEMETRY ", 1)[1])
        elif "FX6_STAGE_B_R29_BRIDGE " in line:
            last_r29_bridge = _parse_kv_ints(line.split("FX6_STAGE_B_R29_BRIDGE ", 1)[1])
        elif "FX6_R29_INSTALL_RC=" in line:
            kv = _parse_kv_ints(line)
            if isinstance(kv.get("FX6_R29_INSTALL_RC"), int):
                r29_install_rc = kv["FX6_R29_INSTALL_RC"]
        elif "FX6_R29_ROLLBACK_RC=" in line:
            kv = _parse_kv_ints(line)
            if isinstance(kv.get("FX6_R29_ROLLBACK_RC"), int):
                r29_rollback_rc = kv["FX6_R29_ROLLBACK_RC"]
        elif "FX6_R29_P1_RESCUE_RC=" in line:
            kv = _parse_kv_ints(line)
            if isinstance(kv.get("FX6_R29_P1_RESCUE_RC"), int):
                r29_p1_rescue_rc = kv["FX6_R29_P1_RESCUE_RC"]
        elif "FX6_R30_RAM_CANARY " in line:
            last_r30_ram_canary = _parse_kv_ints(line.split("FX6_R30_RAM_CANARY ", 1)[1])
        elif "FX6_R30_TIER0_BACKUP " in line:
            last_r30_tier0_backup = _parse_kv_ints(line.split("FX6_R30_TIER0_BACKUP ", 1)[1])
        elif "FX6_R30_PERIPHERAL_INIT " in line:
            last_r30_peripheral_init = _parse_kv_ints(line.split("FX6_R30_PERIPHERAL_INIT ", 1)[1])
        elif "FX6_R30_PERIPHERAL_BRIDGE " in line:
            last_r30_peripheral_bridge = _parse_kv_ints(line.split("FX6_R30_PERIPHERAL_BRIDGE ", 1)[1])
        elif "FX6_R30_JBUSY_ABORT " in line:
            last_r30_jbusy_abort = _parse_kv_ints(line.split("FX6_R30_JBUSY_ABORT ", 1)[1])
        elif "FX6_R30_H0_H3_UNINSTALL " in line:
            last_r30_h0_h3_uninstall = _parse_kv_ints(line.split("FX6_R30_H0_H3_UNINSTALL ", 1)[1])
        elif "FX6_R30_LANG_TELEMETRY " in line:
            last_r30_lang = _parse_kv_ints(line.split("FX6_R30_LANG_TELEMETRY ", 1)[1])
        elif "FX6_STAGE_B_R30_BRIDGE " in line:
            last_r30_bridge = _parse_kv_ints(line.split("FX6_STAGE_B_R30_BRIDGE ", 1)[1])
        elif "FX6_R30_CANARY_TIER0_RC=" in line:
            kv = _parse_kv_ints(line)
            if isinstance(kv.get("FX6_R30_CANARY_TIER0_RC"), int):
                r30_canary_tier0_rc = kv["FX6_R30_CANARY_TIER0_RC"]
        elif "FX6_R30_JBUSY_UNINSTALL_RC=" in line:
            kv = _parse_kv_ints(line)
            if isinstance(kv.get("FX6_R30_JBUSY_UNINSTALL_RC"), int):
                r30_jbusy_uninstall_rc = kv["FX6_R30_JBUSY_UNINSTALL_RC"]
        elif "FX6_R31_KEYMAP_TALLY_INIT " in line:
            last_r31_keymap_tally_init = _parse_kv_ints(line.split("FX6_R31_KEYMAP_TALLY_INIT ", 1)[1])
        elif "FX6_R31_KEYMAP_TALLY_BRIDGE " in line:
            last_r31_keymap_tally_bridge = _parse_kv_ints(line.split("FX6_R31_KEYMAP_TALLY_BRIDGE ", 1)[1])
        elif "FX6_R31_FAN_THERMAL " in line:
            last_r31_fan_thermal = _parse_kv_ints(line.split("FX6_R31_FAN_THERMAL ", 1)[1])
        elif "FX6_R31_FZ100_POWER " in line:
            last_r31_fz100_power = _parse_kv_ints(line.split("FX6_R31_FZ100_POWER ", 1)[1])
        elif "FX6_R31_MTDRO_FIREWALL " in line:
            last_r31_mtdro_firewall = _parse_kv_ints(line.split("FX6_R31_MTDRO_FIREWALL ", 1)[1])
        elif "FX6_R31_LANG_TELEMETRY " in line:
            last_r31_lang = _parse_kv_ints(line.split("FX6_R31_LANG_TELEMETRY ", 1)[1])
        elif "FX6_STAGE_B_R31_BRIDGE " in line:
            last_r31_bridge = _parse_kv_ints(line.split("FX6_STAGE_B_R31_BRIDGE ", 1)[1])
        elif "FX6_R31_FAN_FZ100_RC=" in line:
            kv = _parse_kv_ints(line)
            if isinstance(kv.get("FX6_R31_FAN_FZ100_RC"), int):
                r31_fan_fz100_rc = kv["FX6_R31_FAN_FZ100_RC"]
        elif "FX6_R31_MTDRO_RC=" in line:
            kv = _parse_kv_ints(line)
            if isinstance(kv.get("FX6_R31_MTDRO_RC"), int):
                r31_mtdro_rc = kv["FX6_R31_MTDRO_RC"]
        elif "FX6_R32_IMX510_CUBE_INIT " in line:
            last_r32_imx510_cube_init = _parse_kv_ints(line.split("FX6_R32_IMX510_CUBE_INIT ", 1)[1])
        elif "FX6_R32_IMX510_CUBE_BRIDGE " in line:
            last_r32_imx510_cube_bridge = _parse_kv_ints(line.split("FX6_R32_IMX510_CUBE_BRIDGE ", 1)[1])
        elif "FX6_R32_CDCNCM_USB_0DA1 " in line:
            last_r32_cdcncm_usb_0da1 = _parse_kv_ints(line.split("FX6_R32_CDCNCM_USB_0DA1 ", 1)[1])
        elif "FX6_R32_UART_6STAGE " in line:
            last_r32_uart_6stage = _parse_kv_ints(line.split("FX6_R32_UART_6STAGE ", 1)[1])
        elif "FX6_R32_UART_CP " in line:
            r32_uart_checkpoints.append(_parse_kv_ints(line.split("FX6_R32_UART_CP ", 1)[1]))
        elif "FX6_R32_LANG_TELEMETRY " in line:
            last_r32_lang = _parse_kv_ints(line.split("FX6_R32_LANG_TELEMETRY ", 1)[1])
        elif "FX6_STAGE_B_R32_BRIDGE " in line:
            last_r32_bridge = _parse_kv_ints(line.split("FX6_STAGE_B_R32_BRIDGE ", 1)[1])
        elif "FX6_R32_CDCNCM_RC=" in line:
            kv = _parse_kv_ints(line)
            if isinstance(kv.get("FX6_R32_CDCNCM_RC"), int):
                r32_cdcncm_rc = kv["FX6_R32_CDCNCM_RC"]
        elif "FX6_R32_UART_RC=" in line:
            kv = _parse_kv_ints(line)
            if isinstance(kv.get("FX6_R32_UART_RC"), int):
                r32_uart_rc = kv["FX6_R32_UART_RC"]
        elif "FX6_R33_CFEXPRESS_RSV_INIT " in line:
            last_r33_cfexpress_rsv_init = _parse_kv_ints(line.split("FX6_R33_CFEXPRESS_RSV_INIT ", 1)[1])
        elif "FX6_R33_CFEXPRESS_RSV_BRIDGE " in line:
            last_r33_cfexpress_rsv_bridge = _parse_kv_ints(line.split("FX6_R33_CFEXPRESS_RSV_BRIDGE ", 1)[1])
        elif "FX6_R33_BODYDATA_UFU_BYPASS " in line:
            last_r33_bodydata_ufu_bypass = _parse_kv_ints(line.split("FX6_R33_BODYDATA_UFU_BYPASS ", 1)[1])
        elif "FX6_R33_TIER_STEP " in line:
            r33_tier_steps.append(_parse_kv_ints(line.split("FX6_R33_TIER_STEP ", 1)[1]))
        elif "FX6_R33_5TIER_RECOVERY " in line:
            last_r33_recovery_5tier = _parse_kv_ints(line.split("FX6_R33_5TIER_RECOVERY ", 1)[1])
        elif "FX6_R33_LANG_TELEMETRY " in line:
            last_r33_lang = _parse_kv_ints(line.split("FX6_R33_LANG_TELEMETRY ", 1)[1])
        elif "FX6_STAGE_B_R33_BRIDGE " in line:
            last_r33_bridge = _parse_kv_ints(line.split("FX6_STAGE_B_R33_BRIDGE ", 1)[1])
        elif "FX6_R33_UFU_BYPASS_RC=" in line:
            kv = _parse_kv_ints(line)
            if isinstance(kv.get("FX6_R33_UFU_BYPASS_RC"), int):
                r33_ufu_bypass_rc = kv["FX6_R33_UFU_BYPASS_RC"]
        elif "FX6_R33_5TIER_RC=" in line:
            kv = _parse_kv_ints(line)
            if isinstance(kv.get("FX6_R33_5TIER_RC"), int):
                r33_5tier_rc = kv["FX6_R33_5TIER_RC"]
        elif "FX6_R34_C2PA_TC_GYRO_INIT " in line:
            last_r34_c2pa_tc_gyro_init = _parse_kv_ints(line.split("FX6_R34_C2PA_TC_GYRO_INIT ", 1)[1])
        elif "FX6_R34_C2PA_TC_GYRO_BRIDGE " in line:
            last_r34_c2pa_tc_gyro_bridge = _parse_kv_ints(line.split("FX6_R34_C2PA_TC_GYRO_BRIDGE ", 1)[1])
        elif "FX6_R34_CXD90058_SABIN " in line:
            last_r34_cxd90058_sabin = _parse_kv_ints(line.split("FX6_R34_CXD90058_SABIN ", 1)[1])
        elif "FX6_R34_RAID6_SEAL_16 " in line:
            last_r34_raid6_seal_16 = _parse_kv_ints(line.split("FX6_R34_RAID6_SEAL_16 ", 1)[1])
        elif "FX6_R34_LANG_TELEMETRY " in line:
            last_r34_lang = _parse_kv_ints(line.split("FX6_R34_LANG_TELEMETRY ", 1)[1])
        elif "FX6_STAGE_B_R34_BRIDGE " in line:
            last_r34_bridge = _parse_kv_ints(line.split("FX6_STAGE_B_R34_BRIDGE ", 1)[1])
        elif "FX6_R34_CXD90058_SABIN_RC=" in line:
            kv = _parse_kv_ints(line)
            if isinstance(kv.get("FX6_R34_CXD90058_SABIN_RC"), int):
                r34_cxd90058_sabin_rc = kv["FX6_R34_CXD90058_SABIN_RC"]
        elif "FX6_R34_RAID6_SEAL16_RC=" in line:
            kv = _parse_kv_ints(line)
            if isinstance(kv.get("FX6_R34_RAID6_SEAL16_RC"), int):
                r34_raid6_seal16_rc = kv["FX6_R34_RAID6_SEAL16_RC"]
        elif "FX6_R35_SSBOOT_WBI2_INIT " in line:
            last_r35_ssboot_wbi2_init = _parse_kv_ints(line.split("FX6_R35_SSBOOT_WBI2_INIT ", 1)[1])
        elif "FX6_R35_SSBOOT_WBI2_BRIDGE " in line:
            last_r35_ssboot_wbi2_bridge = _parse_kv_ints(line.split("FX6_R35_SSBOOT_WBI2_BRIDGE ", 1)[1])
        elif "FX6_R35_POWERLOSS_100CYCLE " in line:
            last_r35_powerloss_100cycle = _parse_kv_ints(line.split("FX6_R35_POWERLOSS_100CYCLE ", 1)[1])
        elif "FX6_R35_SLOT1_UFU_C2PA " in line:
            last_r35_slot1_ufu_c2pa = _parse_kv_ints(line.split("FX6_R35_SLOT1_UFU_C2PA ", 1)[1])
        elif "FX6_R35_LANG_TELEMETRY " in line:
            last_r35_lang = _parse_kv_ints(line.split("FX6_R35_LANG_TELEMETRY ", 1)[1])
        elif "FX6_STAGE_B_R35_BRIDGE " in line:
            last_r35_bridge = _parse_kv_ints(line.split("FX6_STAGE_B_R35_BRIDGE ", 1)[1])
        elif "FX6_R35_POWERLOSS_RC=" in line:
            kv = _parse_kv_ints(line)
            if isinstance(kv.get("FX6_R35_POWERLOSS_RC"), int):
                r35_powerloss_rc = kv["FX6_R35_POWERLOSS_RC"]
        elif "FX6_R35_SLOT1_UFU_RC=" in line:
            kv = _parse_kv_ints(line)
            if isinstance(kv.get("FX6_R35_SLOT1_UFU_RC"), int):
                r35_slot1_ufu_rc = kv["FX6_R35_SLOT1_UFU_RC"]
        elif "FX6_R36_EMOUNT_INFO3D_INIT " in line:
            last_r36_emount_info3d_init = _parse_kv_ints(line.split("FX6_R36_EMOUNT_INFO3D_INIT ", 1)[1])
        elif "FX6_R36_EMOUNT_INFO3D_BRIDGE " in line:
            last_r36_emount_info3d_bridge = _parse_kv_ints(line.split("FX6_R36_EMOUNT_INFO3D_BRIDGE ", 1)[1])
        elif "FX6_R36_HDMI_4264_RAW " in line:
            last_r36_hdmi_4264_raw = _parse_kv_ints(line.split("FX6_R36_HDMI_4264_RAW ", 1)[1])
        elif "FX6_R36_WPA3_FOCUSMAP " in line:
            last_r36_wpa3_focusmap = _parse_kv_ints(line.split("FX6_R36_WPA3_FOCUSMAP ", 1)[1])
        elif "FX6_R36_LANG_TELEMETRY " in line:
            last_r36_lang = _parse_kv_ints(line.split("FX6_R36_LANG_TELEMETRY ", 1)[1])
        elif "FX6_STAGE_B_R36_BRIDGE " in line:
            last_r36_bridge = _parse_kv_ints(line.split("FX6_STAGE_B_R36_BRIDGE ", 1)[1])
        elif "FX6_R36_HDMI_RAW_RC=" in line:
            kv = _parse_kv_ints(line)
            if isinstance(kv.get("FX6_R36_HDMI_RAW_RC"), int):
                r36_hdmi_raw_rc = kv["FX6_R36_HDMI_RAW_RC"]
        elif "FX6_R36_WPA3_FOCUSMAP_RC=" in line:
            kv = _parse_kv_ints(line)
            if isinstance(kv.get("FX6_R36_WPA3_FOCUSMAP_RC"), int):
                r36_wpa3_focusmap_rc = kv["FX6_R36_WPA3_FOCUSMAP_RC"]
        elif "FX6_R37_FX3A_FIREWALL_INIT " in line:
            last_r37_fx3a_firewall_init = _parse_kv_ints(line.split("FX6_R37_FX3A_FIREWALL_INIT ", 1)[1])
        elif "FX6_R37_FX3A_FIREWALL_BRIDGE " in line:
            last_r37_fx3a_firewall_bridge = _parse_kv_ints(line.split("FX6_R37_FX3A_FIREWALL_BRIDGE ", 1)[1])
        elif "FX6_R37_XLRH1_4CH_BRIDGE " in line:
            last_r37_xlrh1_4ch_bridge = _parse_kv_ints(line.split("FX6_R37_XLRH1_4CH_BRIDGE ", 1)[1])
        elif "FX6_R37_XLRH1_4CH " in line:
            last_r37_xlrh1_4ch = _parse_kv_ints(line.split("FX6_R37_XLRH1_4CH ", 1)[1])
        elif "FX6_R37_FX3BNDL1_SERIAL " in line:
            last_r37_fx3bndl1_serial = _parse_kv_ints(line.split("FX6_R37_FX3BNDL1_SERIAL ", 1)[1])
        elif "FX6_R37_LANG_TELEMETRY " in line:
            last_r37_lang = _parse_kv_ints(line.split("FX6_R37_LANG_TELEMETRY ", 1)[1])
        elif "FX6_STAGE_B_R37_BRIDGE " in line:
            last_r37_bridge = _parse_kv_ints(line.split("FX6_STAGE_B_R37_BRIDGE ", 1)[1])
        elif "FX6_R37_XLRH1_RC=" in line:
            kv = _parse_kv_ints(line)
            if isinstance(kv.get("FX6_R37_XLRH1_RC"), int):
                r37_xlrh1_rc = kv["FX6_R37_XLRH1_RC"]
        elif "FX6_R37_FX3BNDL1_RC=" in line:
            kv = _parse_kv_ints(line)
            if isinstance(kv.get("FX6_R37_FX3BNDL1_RC"), int):
                r37_fx3bndl1_rc = kv["FX6_R37_FX3BNDL1_RC"]
        elif "FX6_R38_NOUVC_DCC1_PD_INIT " in line:
            last_r38_nouvc_dcc1_pd_init = _parse_kv_ints(line.split("FX6_R38_NOUVC_DCC1_PD_INIT ", 1)[1])
        elif "FX6_R38_NOUVC_DCC1_PD_BRIDGE " in line:
            last_r38_nouvc_dcc1_pd_bridge = _parse_kv_ints(line.split("FX6_R38_NOUVC_DCC1_PD_BRIDGE ", 1)[1])
        elif "FX6_R38_LUT_CINEEI_BRIDGE " in line:
            last_r38_lut_cineei_bridge = _parse_kv_ints(line.split("FX6_R38_LUT_CINEEI_BRIDGE ", 1)[1])
        elif "FX6_R38_LUT_PATH_CINEEI " in line:
            last_r38_lut_path_cineei = _parse_kv_ints(line.split("FX6_R38_LUT_PATH_CINEEI ", 1)[1])
        elif "FX6_R38_RMTP1BT_CLIPFLAG " in line:
            last_r38_rmtp1bt_clipflag = _parse_kv_ints(line.split("FX6_R38_RMTP1BT_CLIPFLAG ", 1)[1])
        elif "FX6_R38_LANG_TELEMETRY " in line:
            last_r38_lang = _parse_kv_ints(line.split("FX6_R38_LANG_TELEMETRY ", 1)[1])
        elif "FX6_STAGE_B_R38_BRIDGE " in line:
            last_r38_bridge = _parse_kv_ints(line.split("FX6_STAGE_B_R38_BRIDGE ", 1)[1])
        elif "FX6_R38_LUT_CINEEI_RC=" in line:
            kv = _parse_kv_ints(line)
            if isinstance(kv.get("FX6_R38_LUT_CINEEI_RC"), int):
                r38_lut_cineei_rc = kv["FX6_R38_LUT_CINEEI_RC"]
        elif "FX6_R38_RMTP1BT_RC=" in line:
            kv = _parse_kv_ints(line)
            if isinstance(kv.get("FX6_R38_RMTP1BT_RC"), int):
                r38_rmtp1bt_rc = kv["FX6_R38_RMTP1BT_RC"]
        elif "FX6_R39_FAN_PWM_INIT " in line:
            last_r39_fan_pwm_init = _parse_kv_ints(line.split("FX6_R39_FAN_PWM_INIT ", 1)[1])
        elif "FX6_R39_FAN_PWM_BRIDGE " in line:
            last_r39_fan_pwm_bridge = _parse_kv_ints(line.split("FX6_R39_FAN_PWM_BRIDGE ", 1)[1])
        elif "FX6_R39_SHUTTER_LUT_BRIDGE " in line:
            last_r39_shutter_lut_bridge = _parse_kv_ints(line.split("FX6_R39_SHUTTER_LUT_BRIDGE ", 1)[1])
        elif "FX6_R39_SHUTTER_SPEED_ANGLE " in line:
            last_r39_shutter_speed_angle = _parse_kv_ints(line.split("FX6_R39_SHUTTER_SPEED_ANGLE ", 1)[1])
        elif "FX6_R39_LUT_601_702_FIREWALL " in line:
            last_r39_lut_601_702_firewall = _parse_kv_ints(line.split("FX6_R39_LUT_601_702_FIREWALL ", 1)[1])
        elif "FX6_R39_LANG_TELEMETRY " in line:
            last_r39_lang = _parse_kv_ints(line.split("FX6_R39_LANG_TELEMETRY ", 1)[1])
        elif "FX6_STAGE_B_R39_BRIDGE " in line:
            last_r39_bridge = _parse_kv_ints(line.split("FX6_STAGE_B_R39_BRIDGE ", 1)[1])
        elif "FX6_R39_SHUTTER_RC=" in line:
            kv = _parse_kv_ints(line)
            if isinstance(kv.get("FX6_R39_SHUTTER_RC"), int):
                r39_shutter_rc = kv["FX6_R39_SHUTTER_RC"]
        elif "FX6_R39_LUT_SPLIT_RC=" in line:
            kv = _parse_kv_ints(line)
            if isinstance(kv.get("FX6_R39_LUT_SPLIT_RC"), int):
                r39_lut_split_rc = kv["FX6_R39_LUT_SPLIT_RC"]
        elif "FX6_R40_BIG6_NOEND_INIT " in line:
            last_r40_big6_noend_init = _parse_kv_ints(line.split("FX6_R40_BIG6_NOEND_INIT ", 1)[1])
        elif "FX6_R40_BIG6_NOEND_BRIDGE " in line:
            last_r40_big6_noend_bridge = _parse_kv_ints(line.split("FX6_R40_BIG6_NOEND_BRIDGE ", 1)[1])
        elif "FX6_R40_CAMSET_TC_BRIDGE " in line:
            last_r40_camset_tc_bridge = _parse_kv_ints(line.split("FX6_R40_CAMSET_TC_BRIDGE ", 1)[1])
        elif "FX6_R40_CAMSET_SLOT1_SPLIT " in line:
            last_r40_camset_slot1_split = _parse_kv_ints(line.split("FX6_R40_CAMSET_SLOT1_SPLIT ", 1)[1])
        elif "FX6_R40_VMCBNCM1_TCIN_HDMI " in line:
            last_r40_vmcbncm1_tcin_hdmi = _parse_kv_ints(line.split("FX6_R40_VMCBNCM1_TCIN_HDMI ", 1)[1])
        elif "FX6_R40_LANG_TELEMETRY " in line:
            last_r40_lang = _parse_kv_ints(line.split("FX6_R40_LANG_TELEMETRY ", 1)[1])
        elif "FX6_STAGE_B_R40_BRIDGE " in line:
            last_r40_bridge = _parse_kv_ints(line.split("FX6_STAGE_B_R40_BRIDGE ", 1)[1])
        elif "FX6_R40_CAMSET_RC=" in line:
            kv = _parse_kv_ints(line)
            if isinstance(kv.get("FX6_R40_CAMSET_RC"), int):
                r40_camset_rc = kv["FX6_R40_CAMSET_RC"]
        elif "FX6_R40_VMCBNCM1_RC=" in line:
            kv = _parse_kv_ints(line)
            if isinstance(kv.get("FX6_R40_VMCBNCM1_RC"), int):
                r40_vmcbncm1_rc = kv["FX6_R40_VMCBNCM1_RC"]
        elif "FX6_R41_DESQUEEZE_165X_INIT " in line:
            last_r41_desqueeze_165x_init = _parse_kv_ints(line.split("FX6_R41_DESQUEEZE_165X_INIT ", 1)[1])
        elif "FX6_R41_DESQUEEZE_BRIDGE " in line:
            last_r41_desqueeze_bridge = _parse_kv_ints(line.split("FX6_R41_DESQUEEZE_BRIDGE ", 1)[1])
        elif "FX6_R41_FOCUSMAP_SIMULT_WB_BRIDGE " in line:
            last_r41_focusmap_simult_wb_bridge = _parse_kv_ints(line.split("FX6_R41_FOCUSMAP_SIMULT_WB_BRIDGE ", 1)[1])
        elif "FX6_R41_EXTERNAL_FOCUSMAP_150FPS " in line:
            last_r41_external_focusmap_150fps = _parse_kv_ints(line.split("FX6_R41_EXTERNAL_FOCUSMAP_150FPS ", 1)[1])
        elif "FX6_R41_SIMULT_SHOCKLESSWB " in line:
            last_r41_simult_shocklesswb = _parse_kv_ints(line.split("FX6_R41_SIMULT_SHOCKLESSWB ", 1)[1])
        elif "FX6_R41_LANG_TELEMETRY " in line:
            last_r41_lang = _parse_kv_ints(line.split("FX6_R41_LANG_TELEMETRY ", 1)[1])
        elif "FX6_STAGE_B_R41_BRIDGE " in line:
            last_r41_bridge = _parse_kv_ints(line.split("FX6_STAGE_B_R41_BRIDGE ", 1)[1])
        elif "FX6_R41_FOCUSMAP_RC=" in line:
            kv = _parse_kv_ints(line)
            if isinstance(kv.get("FX6_R41_FOCUSMAP_RC"), int):
                r41_focusmap_rc = kv["FX6_R41_FOCUSMAP_RC"]
        elif "FX6_R41_SIMULT_WB_RC=" in line:
            kv = _parse_kv_ints(line)
            if isinstance(kv.get("FX6_R41_SIMULT_WB_RC"), int):
                r41_simult_wb_rc = kv["FX6_R41_SIMULT_WB_RC"]
        elif "FX6_R42_HDMI_LOG1080_INIT " in line:
            last_r42_hdmi_log1080_init = _parse_kv_ints(line.split("FX6_R42_HDMI_LOG1080_INIT ", 1)[1])
        elif "FX6_R42_HDMI_LOG1080_BRIDGE " in line:
            last_r42_hdmi_log1080_bridge = _parse_kv_ints(line.split("FX6_R42_HDMI_LOG1080_BRIDGE ", 1)[1])
        elif "FX6_R42_PROXY_VAULT_BRIDGE " in line:
            last_r42_proxy_vault_bridge = _parse_kv_ints(line.split("FX6_R42_PROXY_VAULT_BRIDGE ", 1)[1])
        elif "FX6_R42_FOCUSMAG_BRIGHTMON_BRIDGE " in line:
            last_r42_focusmag_brightmon_bridge = _parse_kv_ints(line.split("FX6_R42_FOCUSMAG_BRIGHTMON_BRIDGE ", 1)[1])
        elif "FX6_R42_PROXY_VAULT " in line:
            last_r42_proxy_vault = _parse_kv_ints(line.split("FX6_R42_PROXY_VAULT ", 1)[1])
        elif "FX6_R42_FOCUSMAG_BRIGHTMON " in line:
            last_r42_focusmag_brightmon = _parse_kv_ints(line.split("FX6_R42_FOCUSMAG_BRIGHTMON ", 1)[1])
        elif "FX6_R42_LANG_TELEMETRY " in line:
            last_r42_lang = _parse_kv_ints(line.split("FX6_R42_LANG_TELEMETRY ", 1)[1])
        elif "FX6_STAGE_B_R42_BRIDGE " in line:
            last_r42_bridge = _parse_kv_ints(line.split("FX6_STAGE_B_R42_BRIDGE ", 1)[1])
        elif "FX6_R42_PROXY_VAULT_RC=" in line:
            kv = _parse_kv_ints(line)
            if isinstance(kv.get("FX6_R42_PROXY_VAULT_RC"), int):
                r42_proxy_vault_rc = kv["FX6_R42_PROXY_VAULT_RC"]
        elif "FX6_R42_FOCUSMAG_BRIGHTMON_RC=" in line:
            kv = _parse_kv_ints(line)
            if isinstance(kv.get("FX6_R42_FOCUSMAG_BRIGHTMON_RC"), int):
                r42_focusmag_brightmon_rc = kv["FX6_R42_FOCUSMAG_BRIGHTMON_RC"]
        elif "FX6_R43_FILESETTINGS_SHOTMARK_INIT " in line:
            last_r43_filesettings_shotmark_init = _parse_kv_ints(line.split("FX6_R43_FILESETTINGS_SHOTMARK_INIT ", 1)[1])
        elif "FX6_R43_FILESETTINGS_SHOTMARK_BRIDGE " in line:
            last_r43_filesettings_shotmark_bridge = _parse_kv_ints(line.split("FX6_R43_FILESETTINGS_SHOTMARK_BRIDGE ", 1)[1])
        elif "FX6_R43_TC_REGENERATE_BRIDGE " in line:
            last_r43_tc_regenerate_bridge = _parse_kv_ints(line.split("FX6_R43_TC_REGENERATE_BRIDGE ", 1)[1])
        elif "FX6_R43_RECLAMP_SILENT_BRIDGE " in line:
            last_r43_reclamp_silent_bridge = _parse_kv_ints(line.split("FX6_R43_RECLAMP_SILENT_BRIDGE ", 1)[1])
        elif "FX6_R43_TC_REGENERATE " in line:
            last_r43_tc_regenerate = _parse_kv_ints(line.split("FX6_R43_TC_REGENERATE ", 1)[1])
        elif "FX6_R43_RECLAMP_SILENT " in line:
            last_r43_reclamp_silent = _parse_kv_ints(line.split("FX6_R43_RECLAMP_SILENT ", 1)[1])
        elif "FX6_R43_LANG_TELEMETRY " in line:
            last_r43_lang = _parse_kv_ints(line.split("FX6_R43_LANG_TELEMETRY ", 1)[1])
        elif "FX6_STAGE_B_R43_BRIDGE " in line:
            last_r43_bridge = _parse_kv_ints(line.split("FX6_STAGE_B_R43_BRIDGE ", 1)[1])
        elif "FX6_R43_TC_REGENERATE_RC=" in line:
            kv = _parse_kv_ints(line)
            if isinstance(kv.get("FX6_R43_TC_REGENERATE_RC"), int):
                r43_tc_regenerate_rc = kv["FX6_R43_TC_REGENERATE_RC"]
        elif "FX6_R43_RECLAMP_SILENT_RC=" in line:
            kv = _parse_kv_ints(line)
            if isinstance(kv.get("FX6_R43_RECLAMP_SILENT_RC"), int):
                r43_reclamp_silent_rc = kv["FX6_R43_RECLAMP_SILENT_RC"]
        elif "FX6_R44_PIXELMAP_CNFLASHA_INIT " in line:
            last_r44_pixelmap_cnflasha_init = _parse_kv_ints(line.split("FX6_R44_PIXELMAP_CNFLASHA_INIT ", 1)[1])
        elif "FX6_R44_PIXELMAP_CNFLASHA_BRIDGE " in line:
            last_r44_pixelmap_cnflasha_bridge = _parse_kv_ints(line.split("FX6_R44_PIXELMAP_CNFLASHA_BRIDGE ", 1)[1])
        elif "FX6_R44_NTSCPAL_CAMRESET_BRIDGE " in line:
            last_r44_ntscpal_camreset_bridge = _parse_kv_ints(line.split("FX6_R44_NTSCPAL_CAMRESET_BRIDGE ", 1)[1])
        elif "FX6_R44_GAMMAASSIST_DISPLAYLUT_BRIDGE " in line:
            last_r44_gammaassist_displaylut_bridge = _parse_kv_ints(line.split("FX6_R44_GAMMAASSIST_DISPLAYLUT_BRIDGE ", 1)[1])
        elif "FX6_R44_NTSCPAL_CAMRESET " in line:
            last_r44_ntscpal_camreset = _parse_kv_ints(line.split("FX6_R44_NTSCPAL_CAMRESET ", 1)[1])
        elif "FX6_R44_GAMMAASSIST_DISPLAYLUT " in line:
            last_r44_gammaassist_displaylut = _parse_kv_ints(line.split("FX6_R44_GAMMAASSIST_DISPLAYLUT ", 1)[1])
        elif "FX6_R44_LANG_TELEMETRY " in line:
            last_r44_lang = _parse_kv_ints(line.split("FX6_R44_LANG_TELEMETRY ", 1)[1])
        elif "FX6_STAGE_B_R44_BRIDGE " in line:
            last_r44_bridge = _parse_kv_ints(line.split("FX6_STAGE_B_R44_BRIDGE ", 1)[1])
        elif "FX6_R44_NTSCPAL_CAMRESET_RC=" in line:
            kv = _parse_kv_ints(line)
            if isinstance(kv.get("FX6_R44_NTSCPAL_CAMRESET_RC"), int):
                r44_ntscpal_camreset_rc = kv["FX6_R44_NTSCPAL_CAMRESET_RC"]
        elif "FX6_R44_GAMMAASSIST_DISPLAYLUT_RC=" in line:
            kv = _parse_kv_ints(line)
            if isinstance(kv.get("FX6_R44_GAMMAASSIST_DISPLAYLUT_RC"), int):
                r44_gammaassist_displaylut_rc = kv["FX6_R44_GAMMAASSIST_DISPLAYLUT_RC"]
        elif "FX6_R45_STEADYSHOT_ACTIVE_INIT " in line:
            last_r45_steadyshot_active_init = _parse_kv_ints(line.split("FX6_R45_STEADYSHOT_ACTIVE_INIT ", 1)[1])
        elif "FX6_R45_STEADYSHOT_ACTIVE_BRIDGE " in line:
            last_r45_steadyshot_active_bridge = _parse_kv_ints(line.split("FX6_R45_STEADYSHOT_ACTIVE_BRIDGE ", 1)[1])
        elif "FX6_R45_CIZ_4LOCKS_BRIDGE " in line:
            last_r45_ciz_4locks_bridge = _parse_kv_ints(line.split("FX6_R45_CIZ_4LOCKS_BRIDGE ", 1)[1])
        elif "FX6_R45_POWERSAVE_AUTOTEMP_BRIDGE " in line:
            last_r45_powersave_autotemp_bridge = _parse_kv_ints(line.split("FX6_R45_POWERSAVE_AUTOTEMP_BRIDGE ", 1)[1])
        elif "FX6_R45_CIZ_4LOCKS " in line:
            last_r45_ciz_4locks = _parse_kv_ints(line.split("FX6_R45_CIZ_4LOCKS ", 1)[1])
        elif "FX6_R45_POWERSAVE_AUTOTEMP " in line:
            last_r45_powersave_autotemp = _parse_kv_ints(line.split("FX6_R45_POWERSAVE_AUTOTEMP ", 1)[1])
        elif "FX6_R45_LANG_TELEMETRY " in line:
            last_r45_lang = _parse_kv_ints(line.split("FX6_R45_LANG_TELEMETRY ", 1)[1])
        elif "FX6_STAGE_B_R45_BRIDGE " in line:
            last_r45_bridge = _parse_kv_ints(line.split("FX6_STAGE_B_R45_BRIDGE ", 1)[1])
        elif "FX6_R45_CIZ_4LOCKS_RC=" in line:
            kv = _parse_kv_ints(line)
            if isinstance(kv.get("FX6_R45_CIZ_4LOCKS_RC"), int):
                r45_ciz_4locks_rc = kv["FX6_R45_CIZ_4LOCKS_RC"]
        elif "FX6_R45_POWERSAVE_AUTOTEMP_RC=" in line:
            kv = _parse_kv_ints(line)
            if isinstance(kv.get("FX6_R45_POWERSAVE_AUTOTEMP_RC"), int):
                r45_powersave_autotemp_rc = kv["FX6_R45_POWERSAVE_AUTOTEMP_RC"]
        elif "FX6_R46_SQ_FIXEDVAR_INIT " in line:
            last_r46_sq_fixedvar_init = _parse_kv_ints(line.split("FX6_R46_SQ_FIXEDVAR_INIT ", 1)[1])
        elif "FX6_R46_SQ_FIXEDVAR_BRIDGE " in line:
            last_r46_sq_fixedvar_bridge = _parse_kv_ints(line.split("FX6_R46_SQ_FIXEDVAR_BRIDGE ", 1)[1])
        elif "FX6_R46_ZEBRA_PEAKING_BRIDGE " in line:
            last_r46_zebra_peaking_bridge = _parse_kv_ints(line.split("FX6_R46_ZEBRA_PEAKING_BRIDGE ", 1)[1])
        elif "FX6_R46_FULLFORMAT_VAULT_BRIDGE " in line:
            last_r46_fullformat_vault_bridge = _parse_kv_ints(line.split("FX6_R46_FULLFORMAT_VAULT_BRIDGE ", 1)[1])
        elif "FX6_R46_ZEBRA_PEAKING_HDMI " in line:
            last_r46_zebra_peaking_hdmi = _parse_kv_ints(line.split("FX6_R46_ZEBRA_PEAKING_HDMI ", 1)[1])
        elif "FX6_R46_FULLFORMAT_CHORD_VAULT " in line:
            last_r46_fullformat_chord_vault = _parse_kv_ints(line.split("FX6_R46_FULLFORMAT_CHORD_VAULT ", 1)[1])
        elif "FX6_R46_LANG_TELEMETRY " in line:
            last_r46_lang = _parse_kv_ints(line.split("FX6_R46_LANG_TELEMETRY ", 1)[1])
        elif "FX6_STAGE_B_R46_BRIDGE " in line:
            last_r46_bridge = _parse_kv_ints(line.split("FX6_STAGE_B_R46_BRIDGE ", 1)[1])
        elif "FX6_R46_ZEBRA_PEAKING_HDMI_RC=" in line:
            kv = _parse_kv_ints(line)
            if isinstance(kv.get("FX6_R46_ZEBRA_PEAKING_HDMI_RC"), int):
                r46_zebra_peaking_hdmi_rc = kv["FX6_R46_ZEBRA_PEAKING_HDMI_RC"]
        elif "FX6_R46_FULLFORMAT_CHORD_VAULT_RC=" in line:
            kv = _parse_kv_ints(line)
            if isinstance(kv.get("FX6_R46_FULLFORMAT_CHORD_VAULT_RC"), int):
                r46_fullformat_chord_vault_rc = kv["FX6_R46_FULLFORMAT_CHORD_VAULT_RC"]
        elif "FX6_R47_SILENT_AUTOPIXELMAP_INIT " in line:
            last_r47_silent_autopixelmap_init = _parse_kv_ints(line.split("FX6_R47_SILENT_AUTOPIXELMAP_INIT ", 1)[1])
        elif "FX6_R47_SILENT_AUTOPIXELMAP_BRIDGE " in line:
            last_r47_silent_autopixelmap_bridge = _parse_kv_ints(line.split("FX6_R47_SILENT_AUTOPIXELMAP_BRIDGE ", 1)[1])
        elif "FX6_R47_MARKER_15RATIO_BRIDGE " in line:
            last_r47_marker_15ratio_bridge = _parse_kv_ints(line.split("FX6_R47_MARKER_15RATIO_BRIDGE ", 1)[1])
        elif "FX6_R47_FLEXEXP_RESET_BRIDGE " in line:
            last_r47_flexexp_reset_bridge = _parse_kv_ints(line.split("FX6_R47_FLEXEXP_RESET_BRIDGE ", 1)[1])
        elif "FX6_R47_MARKER_15RATIO_HDMI " in line:
            last_r47_marker_15ratio_hdmi = _parse_kv_ints(line.split("FX6_R47_MARKER_15RATIO_HDMI ", 1)[1])
        elif "FX6_R47_FLEXEXP_RESET_SPLIT " in line:
            last_r47_flexexp_reset_split = _parse_kv_ints(line.split("FX6_R47_FLEXEXP_RESET_SPLIT ", 1)[1])
        elif "FX6_R47_LANG_TELEMETRY " in line:
            last_r47_lang = _parse_kv_ints(line.split("FX6_R47_LANG_TELEMETRY ", 1)[1])
        elif "FX6_STAGE_B_R47_BRIDGE " in line:
            last_r47_bridge = _parse_kv_ints(line.split("FX6_STAGE_B_R47_BRIDGE ", 1)[1])
        elif "FX6_R47_MARKER_15RATIO_HDMI_RC=" in line:
            kv = _parse_kv_ints(line)
            if isinstance(kv.get("FX6_R47_MARKER_15RATIO_HDMI_RC"), int):
                r47_marker_15ratio_hdmi_rc = kv["FX6_R47_MARKER_15RATIO_HDMI_RC"]
        elif "FX6_R47_FLEXEXP_RESET_SPLIT_RC=" in line:
            kv = _parse_kv_ints(line)
            if isinstance(kv.get("FX6_R47_FLEXEXP_RESET_SPLIT_RC"), int):
                r47_flexexp_reset_split_rc = kv["FX6_R47_FLEXEXP_RESET_SPLIT_RC"]
        elif "FX6_R48_MONITOR_FLIP_INIT " in line:
            last_r48_monitor_flip_init = _parse_kv_ints(line.split("FX6_R48_MONITOR_FLIP_INIT ", 1)[1])
        elif "FX6_R48_RECOVER_IMAGEDB_BRIDGE " in line:
            last_r48_recover_imagedb_bridge = _parse_kv_ints(line.split("FX6_R48_RECOVER_IMAGEDB_BRIDGE ", 1)[1])
        elif "FX6_R48_MONITOR_FLIP_BRIDGE " in line:
            last_r48_monitor_flip_bridge = _parse_kv_ints(line.split("FX6_R48_MONITOR_FLIP_BRIDGE ", 1)[1])
        elif "FX6_R48_AF_SENS_INTERVAL_BRIDGE " in line:
            last_r48_af_sens_interval_bridge = _parse_kv_ints(line.split("FX6_R48_AF_SENS_INTERVAL_BRIDGE ", 1)[1])
        elif "FX6_R48_RECOVER_IMAGEDB_VAULT " in line:
            last_r48_recover_imagedb_vault = _parse_kv_ints(line.split("FX6_R48_RECOVER_IMAGEDB_VAULT ", 1)[1])
        elif "FX6_R48_AF_SENS_INTERVAL " in line:
            last_r48_af_sens_interval = _parse_kv_ints(line.split("FX6_R48_AF_SENS_INTERVAL ", 1)[1])
        elif "FX6_R48_LANG_TELEMETRY " in line:
            last_r48_lang = _parse_kv_ints(line.split("FX6_R48_LANG_TELEMETRY ", 1)[1])
        elif "FX6_STAGE_B_R48_BRIDGE " in line:
            last_r48_bridge = _parse_kv_ints(line.split("FX6_STAGE_B_R48_BRIDGE ", 1)[1])
        elif "FX6_R48_RECOVER_IMAGEDB_VAULT_RC=" in line:
            kv = _parse_kv_ints(line)
            if isinstance(kv.get("FX6_R48_RECOVER_IMAGEDB_VAULT_RC"), int):
                r48_recover_imagedb_vault_rc = kv["FX6_R48_RECOVER_IMAGEDB_VAULT_RC"]
        elif "FX6_R48_AF_SENS_INTERVAL_RC=" in line:
            kv = _parse_kv_ints(line)
            if isinstance(kv.get("FX6_R48_AF_SENS_INTERVAL_RC"), int):
                r48_af_sens_interval_rc = kv["FX6_R48_AF_SENS_INTERVAL_RC"]
        elif "FX6_R49_EMPH_REC_GRID_HDMI_INIT " in line:
            last_r49_emph_rec_grid_hdmi_init = _parse_kv_ints(line.split("FX6_R49_EMPH_REC_GRID_HDMI_INIT ", 1)[1])
        elif "FX6_R49_EMPH_REC_GRID_HDMI_BRIDGE " in line:
            last_r49_emph_rec_grid_hdmi_bridge = _parse_kv_ints(line.split("FX6_R49_EMPH_REC_GRID_HDMI_BRIDGE ", 1)[1])
        elif "FX6_R49_TOUCH_OP_BRIDGE " in line:
            last_r49_touch_op_bridge = _parse_kv_ints(line.split("FX6_R49_TOUCH_OP_BRIDGE ", 1)[1])
        elif "FX6_R49_MONITOR_BRIGHTNESS_BRIDGE " in line:
            last_r49_monitor_brightness_bridge = _parse_kv_ints(line.split("FX6_R49_MONITOR_BRIGHTNESS_BRIDGE ", 1)[1])
        elif "FX6_R49_TOUCH_OP_VAULT " in line:
            last_r49_touch_op_vault = _parse_kv_ints(line.split("FX6_R49_TOUCH_OP_VAULT ", 1)[1])
        elif "FX6_R49_MONITOR_BRIGHTNESS " in line:
            last_r49_monitor_brightness = _parse_kv_ints(line.split("FX6_R49_MONITOR_BRIGHTNESS ", 1)[1])
        elif "FX6_R49_LANG_TELEMETRY " in line:
            last_r49_lang = _parse_kv_ints(line.split("FX6_R49_LANG_TELEMETRY ", 1)[1])
        elif "FX6_STAGE_B_R49_BRIDGE " in line:
            last_r49_bridge = _parse_kv_ints(line.split("FX6_STAGE_B_R49_BRIDGE ", 1)[1])
        elif "FX6_R49_TOUCH_OP_VAULT_RC=" in line:
            kv = _parse_kv_ints(line)
            if isinstance(kv.get("FX6_R49_TOUCH_OP_VAULT_RC"), int):
                r49_touch_op_vault_rc = kv["FX6_R49_TOUCH_OP_VAULT_RC"]
        elif "FX6_R49_MONITOR_BRIGHTNESS_RC=" in line:
            kv = _parse_kv_ints(line)
            if isinstance(kv.get("FX6_R49_MONITOR_BRIGHTNESS_RC"), int):
                r49_monitor_brightness_rc = kv["FX6_R49_MONITOR_BRIGHTNESS_RC"]
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

    r29_telemetry: Optional[Dict[str, Any]] = None
    if any(
        x is not None
        for x in (
            last_r29_install,
            last_r29_rollback,
            last_r29_p1_rescue,
            last_r29_mpr_param,
            last_r29_mpr_rec,
            last_r29_lang,
            last_r29_bridge,
        )
    ):
        r29_telemetry = {
            "install_rc": r29_install_rc,
            "rollback_rc": r29_rollback_rc,
            "p1_rescue_rc": r29_p1_rescue_rc,
            "atomic_install": last_r29_install or {},
            "atomic_rollback": last_r29_rollback or {},
            "p1_rescue": last_r29_p1_rescue or {},
            "mpr_param_shim": last_r29_mpr_param or {},
            "mpr_rec_cycle": last_r29_mpr_rec or {},
            "lang_telemetry": last_r29_lang or {},
            "stage_b_bridge": last_r29_bridge or {},
        }

    r30_telemetry: Optional[Dict[str, Any]] = None
    if any(
        x is not None
        for x in (
            last_r30_ram_canary,
            last_r30_tier0_backup,
            last_r30_peripheral_init,
            last_r30_peripheral_bridge,
            last_r30_jbusy_abort,
            last_r30_h0_h3_uninstall,
            last_r30_lang,
            last_r30_bridge,
        )
    ):
        r30_telemetry = {
            "canary_tier0_rc": r30_canary_tier0_rc,
            "jbusy_uninstall_rc": r30_jbusy_uninstall_rc,
            "ram_canary": last_r30_ram_canary or {},
            "tier0_backup": last_r30_tier0_backup or {},
            "peripheral_init": last_r30_peripheral_init or {},
            "peripheral_bridge": last_r30_peripheral_bridge or {},
            "jbusy_abort": last_r30_jbusy_abort or {},
            "h0_h3_uninstall": last_r30_h0_h3_uninstall or {},
            "lang_telemetry": last_r30_lang or {},
            "stage_b_bridge": last_r30_bridge or {},
        }

    r31_telemetry: Optional[Dict[str, Any]] = None
    if any(
        x is not None
        for x in (
            last_r31_keymap_tally_init,
            last_r31_keymap_tally_bridge,
            last_r31_fan_thermal,
            last_r31_fz100_power,
            last_r31_mtdro_firewall,
            last_r31_lang,
            last_r31_bridge,
        )
    ):
        r31_telemetry = {
            "fan_fz100_rc": r31_fan_fz100_rc,
            "mtdro_rc": r31_mtdro_rc,
            "keymap_tally_init": last_r31_keymap_tally_init or {},
            "keymap_tally_bridge": last_r31_keymap_tally_bridge or {},
            "fan_thermal": last_r31_fan_thermal or {},
            "fz100_power": last_r31_fz100_power or {},
            "mtdro_firewall": last_r31_mtdro_firewall or {},
            "lang_telemetry": last_r31_lang or {},
            "stage_b_bridge": last_r31_bridge or {},
        }

    r32_telemetry: Optional[Dict[str, Any]] = None
    if any(
        x is not None
        for x in (
            last_r32_imx510_cube_init,
            last_r32_imx510_cube_bridge,
            last_r32_cdcncm_usb_0da1,
            last_r32_uart_6stage,
            last_r32_lang,
            last_r32_bridge,
        )
    ) or r32_uart_checkpoints:
        r32_telemetry = {
            "cdcncm_rc": r32_cdcncm_rc,
            "uart_rc": r32_uart_rc,
            "imx510_cube_init": last_r32_imx510_cube_init or {},
            "imx510_cube_bridge": last_r32_imx510_cube_bridge or {},
            "cdcncm_usb_0da1": last_r32_cdcncm_usb_0da1 or {},
            "uart_6stage": last_r32_uart_6stage or {},
            "uart_checkpoints": r32_uart_checkpoints,
            "lang_telemetry": last_r32_lang or {},
            "stage_b_bridge": last_r32_bridge or {},
        }

    r33_telemetry: Optional[Dict[str, Any]] = None
    if any(
        x is not None
        for x in (
            last_r33_cfexpress_rsv_init,
            last_r33_cfexpress_rsv_bridge,
            last_r33_bodydata_ufu_bypass,
            last_r33_recovery_5tier,
            last_r33_lang,
            last_r33_bridge,
        )
    ) or r33_tier_steps:
        r33_telemetry = {
            "ufu_bypass_rc": r33_ufu_bypass_rc,
            "recovery_5tier_rc": r33_5tier_rc,
            "cfexpress_rsv_init": last_r33_cfexpress_rsv_init or {},
            "cfexpress_rsv_bridge": last_r33_cfexpress_rsv_bridge or {},
            "bodydata_ufu_bypass": last_r33_bodydata_ufu_bypass or {},
            "recovery_5tier": last_r33_recovery_5tier or {},
            "recovery_tier_steps": r33_tier_steps,
            "lang_telemetry": last_r33_lang or {},
            "stage_b_bridge": last_r33_bridge or {},
        }

    r34_telemetry: Optional[Dict[str, Any]] = None
    if any(
        x is not None
        for x in (
            last_r34_c2pa_tc_gyro_init,
            last_r34_c2pa_tc_gyro_bridge,
            last_r34_cxd90058_sabin,
            last_r34_raid6_seal_16,
            last_r34_lang,
            last_r34_bridge,
        )
    ):
        r34_telemetry = {
            "cxd90058_sabin_rc": r34_cxd90058_sabin_rc,
            "raid6_seal16_rc": r34_raid6_seal16_rc,
            "c2pa_tc_gyro_init": last_r34_c2pa_tc_gyro_init or {},
            "c2pa_tc_gyro_bridge": last_r34_c2pa_tc_gyro_bridge or {},
            "cxd90058_sabin": last_r34_cxd90058_sabin or {},
            "raid6_seal_16": last_r34_raid6_seal_16 or {},
            "lang_telemetry": last_r34_lang or {},
            "stage_b_bridge": last_r34_bridge or {},
        }

    r35_telemetry: Optional[Dict[str, Any]] = None
    if any(
        x is not None
        for x in (
            last_r35_ssboot_wbi2_init,
            last_r35_ssboot_wbi2_bridge,
            last_r35_powerloss_100cycle,
            last_r35_slot1_ufu_c2pa,
            last_r35_lang,
            last_r35_bridge,
        )
    ):
        r35_telemetry = {
            "powerloss_rc": r35_powerloss_rc,
            "slot1_ufu_rc": r35_slot1_ufu_rc,
            "ssboot_wbi2_init": last_r35_ssboot_wbi2_init or {},
            "ssboot_wbi2_bridge": last_r35_ssboot_wbi2_bridge or {},
            "powerloss_100cycle": last_r35_powerloss_100cycle or {},
            "slot1_ufu_c2pa": last_r35_slot1_ufu_c2pa or {},
            "lang_telemetry": last_r35_lang or {},
            "stage_b_bridge": last_r35_bridge or {},
        }

    r36_telemetry: Optional[Dict[str, Any]] = None
    if any(
        x is not None
        for x in (
            last_r36_emount_info3d_init,
            last_r36_emount_info3d_bridge,
            last_r36_hdmi_4264_raw,
            last_r36_wpa3_focusmap,
            last_r36_lang,
            last_r36_bridge,
        )
    ):
        r36_telemetry = {
            "hdmi_raw_rc": r36_hdmi_raw_rc,
            "wpa3_focusmap_rc": r36_wpa3_focusmap_rc,
            "emount_info3d_init": last_r36_emount_info3d_init or {},
            "emount_info3d_bridge": last_r36_emount_info3d_bridge or {},
            "hdmi_4264_raw": last_r36_hdmi_4264_raw or {},
            "wpa3_focusmap": last_r36_wpa3_focusmap or {},
            "lang_telemetry": last_r36_lang or {},
            "stage_b_bridge": last_r36_bridge or {},
        }

    r37_telemetry: Optional[Dict[str, Any]] = None
    if any(
        x is not None
        for x in (
            last_r37_fx3a_firewall_init,
            last_r37_fx3a_firewall_bridge,
            last_r37_xlrh1_4ch_bridge,
            last_r37_xlrh1_4ch,
            last_r37_fx3bndl1_serial,
            last_r37_lang,
            last_r37_bridge,
        )
    ):
        r37_telemetry = {
            "xlrh1_rc": r37_xlrh1_rc,
            "fx3bndl1_rc": r37_fx3bndl1_rc,
            "fx3a_firewall_init": last_r37_fx3a_firewall_init or {},
            "fx3a_firewall_bridge": last_r37_fx3a_firewall_bridge or {},
            "xlrh1_4ch_bridge": last_r37_xlrh1_4ch_bridge or {},
            "xlrh1_4ch": last_r37_xlrh1_4ch or {},
            "fx3bndl1_serial": last_r37_fx3bndl1_serial or {},
            "lang_telemetry": last_r37_lang or {},
            "stage_b_bridge": last_r37_bridge or {},
        }

    r38_telemetry: Optional[Dict[str, Any]] = None
    if any(
        x is not None
        for x in (
            last_r38_nouvc_dcc1_pd_init,
            last_r38_nouvc_dcc1_pd_bridge,
            last_r38_lut_cineei_bridge,
            last_r38_lut_path_cineei,
            last_r38_rmtp1bt_clipflag,
            last_r38_lang,
            last_r38_bridge,
        )
    ):
        r38_telemetry = {
            "lut_cineei_rc": r38_lut_cineei_rc,
            "rmtp1bt_rc": r38_rmtp1bt_rc,
            "nouvc_dcc1_pd_init": last_r38_nouvc_dcc1_pd_init or {},
            "nouvc_dcc1_pd_bridge": last_r38_nouvc_dcc1_pd_bridge or {},
            "lut_cineei_bridge": last_r38_lut_cineei_bridge or {},
            "lut_path_cineei": last_r38_lut_path_cineei or {},
            "rmtp1bt_clipflag": last_r38_rmtp1bt_clipflag or {},
            "lang_telemetry": last_r38_lang or {},
            "stage_b_bridge": last_r38_bridge or {},
        }

    r39_telemetry: Optional[Dict[str, Any]] = None
    if any(
        x is not None
        for x in (
            last_r39_fan_pwm_init,
            last_r39_fan_pwm_bridge,
            last_r39_shutter_lut_bridge,
            last_r39_shutter_speed_angle,
            last_r39_lut_601_702_firewall,
            last_r39_lang,
            last_r39_bridge,
        )
    ):
        r39_telemetry = {
            "shutter_rc": r39_shutter_rc,
            "lut_split_rc": r39_lut_split_rc,
            "fan_pwm_init": last_r39_fan_pwm_init or {},
            "fan_pwm_bridge": last_r39_fan_pwm_bridge or {},
            "shutter_lut_bridge": last_r39_shutter_lut_bridge or {},
            "shutter_speed_angle": last_r39_shutter_speed_angle or {},
            "lut_601_702_firewall": last_r39_lut_601_702_firewall or {},
            "lang_telemetry": last_r39_lang or {},
            "stage_b_bridge": last_r39_bridge or {},
        }

    r40_telemetry: Optional[Dict[str, Any]] = None
    if any(
        x is not None
        for x in (
            last_r40_big6_noend_init,
            last_r40_big6_noend_bridge,
            last_r40_camset_tc_bridge,
            last_r40_camset_slot1_split,
            last_r40_vmcbncm1_tcin_hdmi,
            last_r40_lang,
            last_r40_bridge,
        )
    ):
        r40_telemetry = {
            "camset_rc": r40_camset_rc,
            "vmcbncm1_rc": r40_vmcbncm1_rc,
            "big6_noend_init": last_r40_big6_noend_init or {},
            "big6_noend_bridge": last_r40_big6_noend_bridge or {},
            "camset_tc_bridge": last_r40_camset_tc_bridge or {},
            "camset_slot1_split": last_r40_camset_slot1_split or {},
            "vmcbncm1_tcin_hdmi": last_r40_vmcbncm1_tcin_hdmi or {},
            "lang_telemetry": last_r40_lang or {},
            "stage_b_bridge": last_r40_bridge or {},
        }

    r41_telemetry: Optional[Dict[str, Any]] = None
    if any(
        x is not None
        for x in (
            last_r41_desqueeze_165x_init,
            last_r41_desqueeze_bridge,
            last_r41_focusmap_simult_wb_bridge,
            last_r41_external_focusmap_150fps,
            last_r41_simult_shocklesswb,
            last_r41_lang,
            last_r41_bridge,
        )
    ):
        r41_telemetry = {
            "focusmap_rc": r41_focusmap_rc,
            "simult_wb_rc": r41_simult_wb_rc,
            "desqueeze_165x_init": last_r41_desqueeze_165x_init or {},
            "desqueeze_bridge": last_r41_desqueeze_bridge or {},
            "focusmap_simult_wb_bridge": last_r41_focusmap_simult_wb_bridge or {},
            "external_focusmap_150fps": last_r41_external_focusmap_150fps or {},
            "simult_shocklesswb": last_r41_simult_shocklesswb or {},
            "lang_telemetry": last_r41_lang or {},
            "stage_b_bridge": last_r41_bridge or {},
        }

    r42_telemetry: Optional[Dict[str, Any]] = None
    if any(
        x is not None
        for x in (
            last_r42_hdmi_log1080_init,
            last_r42_hdmi_log1080_bridge,
            last_r42_proxy_vault_bridge,
            last_r42_focusmag_brightmon_bridge,
            last_r42_proxy_vault,
            last_r42_focusmag_brightmon,
            last_r42_lang,
            last_r42_bridge,
        )
    ):
        r42_telemetry = {
            "proxy_vault_rc": r42_proxy_vault_rc,
            "focusmag_brightmon_rc": r42_focusmag_brightmon_rc,
            "hdmi_log1080_init": last_r42_hdmi_log1080_init or {},
            "hdmi_log1080_bridge": last_r42_hdmi_log1080_bridge or {},
            "proxy_vault_bridge": last_r42_proxy_vault_bridge or {},
            "focusmag_brightmon_bridge": last_r42_focusmag_brightmon_bridge or {},
            "proxy_vault": last_r42_proxy_vault or {},
            "focusmag_brightmon": last_r42_focusmag_brightmon or {},
            "lang_telemetry": last_r42_lang or {},
            "stage_b_bridge": last_r42_bridge or {},
        }

    r43_telemetry: Optional[Dict[str, Any]] = None
    if any(
        x is not None
        for x in (
            last_r43_filesettings_shotmark_init,
            last_r43_filesettings_shotmark_bridge,
            last_r43_tc_regenerate_bridge,
            last_r43_reclamp_silent_bridge,
            last_r43_tc_regenerate,
            last_r43_reclamp_silent,
            last_r43_lang,
            last_r43_bridge,
        )
    ):
        r43_telemetry = {
            "tc_regenerate_rc": r43_tc_regenerate_rc,
            "reclamp_silent_rc": r43_reclamp_silent_rc,
            "filesettings_shotmark_init": last_r43_filesettings_shotmark_init or {},
            "filesettings_shotmark_bridge": last_r43_filesettings_shotmark_bridge or {},
            "tc_regenerate_bridge": last_r43_tc_regenerate_bridge or {},
            "reclamp_silent_bridge": last_r43_reclamp_silent_bridge or {},
            "tc_regenerate": last_r43_tc_regenerate or {},
            "reclamp_silent": last_r43_reclamp_silent or {},
            "lang_telemetry": last_r43_lang or {},
            "stage_b_bridge": last_r43_bridge or {},
        }

    r44_telemetry: Optional[Dict[str, Any]] = None
    if any(
        x is not None
        for x in (
            last_r44_pixelmap_cnflasha_init,
            last_r44_pixelmap_cnflasha_bridge,
            last_r44_ntscpal_camreset_bridge,
            last_r44_gammaassist_displaylut_bridge,
            last_r44_ntscpal_camreset,
            last_r44_gammaassist_displaylut,
            last_r44_lang,
            last_r44_bridge,
        )
    ):
        r44_telemetry = {
            "ntscpal_camreset_rc": r44_ntscpal_camreset_rc,
            "gammaassist_displaylut_rc": r44_gammaassist_displaylut_rc,
            "pixelmap_cnflasha_init": last_r44_pixelmap_cnflasha_init or {},
            "pixelmap_cnflasha_bridge": last_r44_pixelmap_cnflasha_bridge or {},
            "ntscpal_camreset_bridge": last_r44_ntscpal_camreset_bridge or {},
            "gammaassist_displaylut_bridge": last_r44_gammaassist_displaylut_bridge or {},
            "ntscpal_camreset": last_r44_ntscpal_camreset or {},
            "gammaassist_displaylut": last_r44_gammaassist_displaylut or {},
            "lang_telemetry": last_r44_lang or {},
            "stage_b_bridge": last_r44_bridge or {},
        }

    r45_telemetry: Optional[Dict[str, Any]] = None
    if any(
        x is not None
        for x in (
            last_r45_steadyshot_active_init,
            last_r45_steadyshot_active_bridge,
            last_r45_ciz_4locks_bridge,
            last_r45_powersave_autotemp_bridge,
            last_r45_ciz_4locks,
            last_r45_powersave_autotemp,
            last_r45_lang,
            last_r45_bridge,
        )
    ):
        r45_telemetry = {
            "ciz_4locks_rc": r45_ciz_4locks_rc,
            "powersave_autotemp_rc": r45_powersave_autotemp_rc,
            "steadyshot_active_init": last_r45_steadyshot_active_init or {},
            "steadyshot_active_bridge": last_r45_steadyshot_active_bridge or {},
            "ciz_4locks_bridge": last_r45_ciz_4locks_bridge or {},
            "powersave_autotemp_bridge": last_r45_powersave_autotemp_bridge or {},
            "ciz_4locks": last_r45_ciz_4locks or {},
            "powersave_autotemp": last_r45_powersave_autotemp or {},
            "lang_telemetry": last_r45_lang or {},
            "stage_b_bridge": last_r45_bridge or {},
        }

    r46_telemetry: Optional[Dict[str, Any]] = None
    if any(
        x is not None
        for x in (
            last_r46_sq_fixedvar_init,
            last_r46_sq_fixedvar_bridge,
            last_r46_zebra_peaking_bridge,
            last_r46_fullformat_vault_bridge,
            last_r46_zebra_peaking_hdmi,
            last_r46_fullformat_chord_vault,
            last_r46_lang,
            last_r46_bridge,
        )
    ):
        r46_telemetry = {
            "zebra_peaking_hdmi_rc": r46_zebra_peaking_hdmi_rc,
            "fullformat_chord_vault_rc": r46_fullformat_chord_vault_rc,
            "sq_fixedvar_init": last_r46_sq_fixedvar_init or {},
            "sq_fixedvar_bridge": last_r46_sq_fixedvar_bridge or {},
            "zebra_peaking_bridge": last_r46_zebra_peaking_bridge or {},
            "fullformat_vault_bridge": last_r46_fullformat_vault_bridge or {},
            "zebra_peaking_hdmi": last_r46_zebra_peaking_hdmi or {},
            "fullformat_chord_vault": last_r46_fullformat_chord_vault or {},
            "lang_telemetry": last_r46_lang or {},
            "stage_b_bridge": last_r46_bridge or {},
        }

    r47_telemetry: Optional[Dict[str, Any]] = None
    if any(
        x is not None
        for x in (
            last_r47_silent_autopixelmap_init,
            last_r47_silent_autopixelmap_bridge,
            last_r47_marker_15ratio_bridge,
            last_r47_flexexp_reset_bridge,
            last_r47_marker_15ratio_hdmi,
            last_r47_flexexp_reset_split,
            last_r47_lang,
            last_r47_bridge,
        )
    ):
        r47_telemetry = {
            "marker_15ratio_hdmi_rc": r47_marker_15ratio_hdmi_rc,
            "flexexp_reset_split_rc": r47_flexexp_reset_split_rc,
            "silent_autopixelmap_init": last_r47_silent_autopixelmap_init or {},
            "silent_autopixelmap_bridge": last_r47_silent_autopixelmap_bridge or {},
            "marker_15ratio_bridge": last_r47_marker_15ratio_bridge or {},
            "flexexp_reset_bridge": last_r47_flexexp_reset_bridge or {},
            "marker_15ratio_hdmi": last_r47_marker_15ratio_hdmi or {},
            "flexexp_reset_split": last_r47_flexexp_reset_split or {},
            "lang_telemetry": last_r47_lang or {},
            "stage_b_bridge": last_r47_bridge or {},
        }

    r48_telemetry: Optional[Dict[str, Any]] = None
    if any(
        x is not None
        for x in (
            last_r48_monitor_flip_init,
            last_r48_recover_imagedb_bridge,
            last_r48_monitor_flip_bridge,
            last_r48_af_sens_interval_bridge,
            last_r48_recover_imagedb_vault,
            last_r48_af_sens_interval,
            last_r48_lang,
            last_r48_bridge,
        )
    ):
        r48_telemetry = {
            "recover_imagedb_vault_rc": r48_recover_imagedb_vault_rc,
            "af_sens_interval_rc": r48_af_sens_interval_rc,
            "monitor_flip_init": last_r48_monitor_flip_init or {},
            "recover_imagedb_bridge": last_r48_recover_imagedb_bridge or {},
            "monitor_flip_bridge": last_r48_monitor_flip_bridge or {},
            "af_sens_interval_bridge": last_r48_af_sens_interval_bridge or {},
            "recover_imagedb_vault": last_r48_recover_imagedb_vault or {},
            "af_sens_interval": last_r48_af_sens_interval or {},
            "lang_telemetry": last_r48_lang or {},
            "stage_b_bridge": last_r48_bridge or {},
        }

    r49_telemetry: Optional[Dict[str, Any]] = None
    if any(
        x is not None
        for x in (
            last_r49_emph_rec_grid_hdmi_init,
            last_r49_emph_rec_grid_hdmi_bridge,
            last_r49_touch_op_bridge,
            last_r49_monitor_brightness_bridge,
            last_r49_touch_op_vault,
            last_r49_monitor_brightness,
            last_r49_lang,
            last_r49_bridge,
        )
    ):
        r49_telemetry = {
            "touch_op_vault_rc": r49_touch_op_vault_rc,
            "monitor_brightness_rc": r49_monitor_brightness_rc,
            "emph_rec_grid_hdmi_init": last_r49_emph_rec_grid_hdmi_init or {},
            "emph_rec_grid_hdmi_bridge": last_r49_emph_rec_grid_hdmi_bridge or {},
            "touch_op_bridge": last_r49_touch_op_bridge or {},
            "monitor_brightness_bridge": last_r49_monitor_brightness_bridge or {},
            "touch_op_vault": last_r49_touch_op_vault or {},
            "monitor_brightness": last_r49_monitor_brightness or {},
            "lang_telemetry": last_r49_lang or {},
            "stage_b_bridge": last_r49_bridge or {},
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
        "r29_telemetry": r29_telemetry,
        "r30_telemetry": r30_telemetry,
        "r31_telemetry": r31_telemetry,
        "r32_telemetry": r32_telemetry,
        "r33_telemetry": r33_telemetry,
        "r34_telemetry": r34_telemetry,
        "r35_telemetry": r35_telemetry,
        "r36_telemetry": r36_telemetry,
        "r37_telemetry": r37_telemetry,
        "r38_telemetry": r38_telemetry,
        "r39_telemetry": r39_telemetry,
        "r40_telemetry": r40_telemetry,
        "r41_telemetry": r41_telemetry,
        "r42_telemetry": r42_telemetry,
        "r43_telemetry": r43_telemetry,
        "r44_telemetry": r44_telemetry,
        "r45_telemetry": r45_telemetry,
        "r46_telemetry": r46_telemetry,
        "r47_telemetry": r47_telemetry,
        "r48_telemetry": r48_telemetry,
        "r49_telemetry": r49_telemetry,
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
    if args.round >= 47:
        tmp_prefix = "fx6-r47"
    elif args.round >= 46:
        tmp_prefix = "fx6-r46"
    elif args.round >= 45:
        tmp_prefix = "fx6-r45"
    elif args.round >= 44:
        tmp_prefix = "fx6-r44"
    elif args.round >= 43:
        tmp_prefix = "fx6-r43"
    elif args.round >= 42:
        tmp_prefix = "fx6-r42"
    elif args.round >= 41:
        tmp_prefix = "fx6-r41"
    elif args.round >= 40:
        tmp_prefix = "fx6-r40"
    elif args.round >= 39:
        tmp_prefix = "fx6-r39"
    elif args.round >= 38:
        tmp_prefix = "fx6-r38"
    elif args.round >= 37:
        tmp_prefix = "fx6-r37"
    elif args.round >= 36:
        tmp_prefix = "fx6-r36"
    elif args.round >= 35:
        tmp_prefix = "fx6-r35"
    elif args.round >= 34:
        tmp_prefix = "fx6-r34"
    elif args.round >= 33:
        tmp_prefix = "fx6-r33"
    elif args.round >= 32:
        tmp_prefix = "fx6-r32"
    elif args.round >= 31:
        tmp_prefix = "fx6-r31"
    elif args.round >= 30:
        tmp_prefix = "fx6-r30"
    elif args.round >= 29:
        tmp_prefix = "fx6-r29"
    elif args.round >= 28:
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
    if args.round >= 48:
        tmp_prefix = "fx6-r48"
    if args.round >= 49:
        tmp_prefix = "fx6-r49"
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
        r29_mode = getattr(args, "r29_mode", "install_mpr_rec")
        r30_mode = getattr(args, "r30_mode", "peripheral_big6")
        r31_mode = getattr(args, "r31_mode", "keymap_big6")
        r32_mode = getattr(args, "r32_mode", "imx510_cube_big6")
        r33_mode = getattr(args, "r33_mode", "cfexpress_rsv_big6")
        r34_mode = getattr(args, "r34_mode", "c2pa_tc_gyro_big6")
        r35_mode = getattr(args, "r35_mode", "ssboot_wbi2_big6")
        r36_mode = getattr(args, "r36_mode", "emount_info3d_big6")
        r37_mode = getattr(args, "r37_mode", "fx3a_firewall_big6")
        r38_mode = getattr(args, "r38_mode", "nouvc_dcc1_pd_big6")
        r39_mode = getattr(args, "r39_mode", "fan_pwm_offinrec_big6")
        r40_mode = getattr(args, "r40_mode", "big6_home_noend_big6")
        r41_mode = getattr(args, "r41_mode", "desqueeze_165x_4locks_big6")
        r42_mode = getattr(args, "r42_mode", "hdmi_log1080_hdmionly_4k_big6")
        r43_mode = getattr(args, "r43_mode", "filesettings_shotmark_big6")
        r44_mode = getattr(args, "r44_mode", "pixelmap_reboot_cnflasha_big6")
        r45_mode = getattr(args, "r45_mode", "steadyshot_active_cutoffs_big6")
        r46_mode = getattr(args, "r46_mode", "sq_fixedvar_6locks_big6")
        r47_mode = getattr(args, "r47_mode", "silent_autopixelmap_5locks_big6")
        r48_mode = getattr(args, "r48_mode", "monitor_flip_playback_big6")
        r49_mode = getattr(args, "r49_mode", "emphasized_rec_grid_hdmi_big6")
        if args.round >= 8:
            stage_label = (
                f"Stage-B P1..P9+Fan+P10+P11+P12+P4(Milestone49Wave35RealHwEmphasizedRecGridHdmiTouchOpSunnyWeather+r49_mode={r49_mode}+lang={lang})"
                if args.round >= 49
                else (
                f"Stage-B P1..P9+Fan+P10+P11+P12+P4(Milestone48Wave34RealHwRecoverImageDbMonitorFlipAfSensInterval+r48_mode={r48_mode}+lang={lang})"
                if args.round >= 48
                else (
                f"Stage-B P1..P9+Fan+P10+P11+P12+P4(Milestone47Wave33RealHwSilentAutoPixelMapNoPwrShutterMarker15RatioHdmiFlexExp+r47_mode={r47_mode}+lang={lang})"
                if args.round >= 47
                else (
                f"Stage-B P1..P9+Fan+P10+P11+P12+P4(Milestone46Wave32RealHwSqFixedVar6LocksZebraPeakingHdmiFullFormatVault+r46_mode={r46_mode}+lang={lang})"
                if args.round >= 46
                else (
                f"Stage-B P1..P9+Fan+P10+P11+P12+P4(Milestone45Wave31RealHwSteadyShotActiveCiz4LocksPowerSaveAutoTemp+r45_mode={r45_mode}+lang={lang})"
                if args.round >= 45
                else (
                f"Stage-B P1..P9+Fan+P10+P11+P12+P4(Wave30RealHwPixelMapNtscPalGammaAssistDisplayLut+r44_mode={r44_mode}+lang={lang})"
                if args.round >= 44
                else (
                f"Stage-B P1..P9+Fan+P10+P11+P12+P4(RealHwFileSettingsShotMarkTcRegenRecLamp+r43_mode={r43_mode}+lang={lang})"
                if args.round >= 43
                else (
                f"Stage-B P1..P9+Fan+P10+P11+P12+P4(RealHwHdmiLog1080HdmiOnly4kProxyVaultFocusMagBrightMon+r42_mode={r42_mode}+lang={lang})"
                if args.round >= 42
                else (
                f"Stage-B P1..P9+Fan+P10+P11+P12+P4(RealHwDesqueeze165xFocusMap150fpsSimultShocklessWb+r41_mode={r41_mode}+lang={lang})"
                if args.round >= 41
                else (
                f"Stage-B P1..P9+Fan+P10+P11+P12+P4(Milestone40RealHwBig6NoEndCamsetSlot1VmcBncm1+r40_mode={r40_mode}+lang={lang})"
                if args.round >= 40
                else (
                f"Stage-B P1..P9+Fan+P10+P11+P12+P4(RealHwFanPwmShutterAngleLutSplit+r39_mode={r39_mode}+lang={lang})"
                if args.round >= 39
                else (
                f"Stage-B P1..P9+Fan+P10+P11+P12+P4(RealHwNoUvcDcc1LutPathCineEiRmtp1bt+r38_mode={r38_mode}+lang={lang})"
                if args.round >= 38
                else (
                f"Stage-B P1..P9+Fan+P10+P11+P12+P4(RealHwFx3aFirewallXlrh14chFx3bndl1+r37_mode={r37_mode}+lang={lang})"
                if args.round >= 37
                else (
                f"Stage-B P1..P9+Fan+P10+P11+P12+P4(RealHwEmountInfo3dHdmi4264RawWpa3+r36_mode={r36_mode}+lang={lang})"
                if args.round >= 36
                else (
                f"Stage-B P1..P9+Fan+P10+P11+P12+P4(RealHwSsbootWbi2PowerLossSlot1Ufu+r35_mode={r35_mode}+lang={lang})"
                if args.round >= 35
                else (
                f"Stage-B P1..P9+Fan+P10+P11+P12+P4(RealHwCXD90058SabinC2paTcGyroSeal+r34_mode={r34_mode}+lang={lang})"
                if args.round >= 34
                else (
                f"Stage-B P1..P9+Fan+P10+P11+P12+P4(RealHwCFexpressRsvUfu5Tier+r33_mode={r33_mode}+lang={lang})"
                if args.round >= 33
                else (
                f"Stage-B P1..P9+Fan+P10+P11+P12+P4(RealHwIMX510CubeCdcNcmUart+r32_mode={r32_mode}+lang={lang})"
                if args.round >= 32
                else (
                f"Stage-B P1..P9+Fan+P10+P11+P12+P4(RealHwKeymapTallyFanFz100Mtdro+r31_mode={r31_mode}+lang={lang})"
                if args.round >= 31
                else (
                f"Stage-B P1..P9+Fan+P10+P11+P12+P4(RealHwCanaryTier0PeripheralUninstall+r30_mode={r30_mode}+lang={lang})"
                if args.round >= 30
                else (
                f"Stage-B P1..P9+Fan+P10+P11+P12+P4(RealHwAtomicInstaller+MPR-REC+P1Rescue+r29_mode={r29_mode}+lang={lang})"
                if args.round >= 29
                else (
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
                enable_r29=(args.round == 29),
                r29_mode=r29_mode,
                enable_r30=(args.round >= 30),
                r30_mode=r30_mode,
                enable_r31=(args.round >= 31),
                r31_mode=r31_mode,
                enable_r32=(args.round >= 32),
                r32_mode=r32_mode,
                enable_r33=(args.round >= 33),
                r33_mode=r33_mode,
                enable_r34=(args.round >= 34),
                r34_mode=r34_mode,
                enable_r35=(args.round >= 35),
                r35_mode=r35_mode,
                enable_r36=(args.round >= 36),
                r36_mode=r36_mode,
                enable_r37=(args.round >= 37),
                r37_mode=r37_mode,
                enable_r38=(args.round >= 38),
                r38_mode=r38_mode,
                enable_r39=(args.round >= 39),
                r39_mode=r39_mode,
                enable_r40=(args.round >= 40),
                r40_mode=r40_mode,
                enable_r41=(args.round >= 41),
                r41_mode=r41_mode,
                enable_r42=(args.round >= 42),
                r42_mode=r42_mode,
                enable_r43=(args.round >= 43),
                r43_mode=r43_mode,
                enable_r44=(args.round >= 44),
                r44_mode=r44_mode,
                enable_r45=(args.round >= 45),
                r45_mode=r45_mode,
                enable_r46=(args.round >= 46),
                r46_mode=r46_mode,
                enable_r47=(args.round >= 47),
                r47_mode=r47_mode,
                enable_r48=(args.round >= 48),
                r48_mode=r48_mode,
                enable_r49=(args.round >= 49),
                r49_mode=r49_mode,
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
                    or "FX6_R29_ROLLBACK_EXIT" in txt
                    or "FX6_R29_P1_RESCUE_EXIT" in txt
                    or "FX6_R30_CANARY_TIER0_EXIT" in txt
                    or "FX6_R30_JBUSY_UNINSTALL_EXIT" in txt
                    or "FX6_R31_FAN_FZ100_EXIT" in txt
                    or "FX6_R31_MTDRO_EXIT" in txt
                    or "FX6_R32_CDCNCM_EXIT" in txt
                    or "FX6_R32_UART_EXIT" in txt
                    or "FX6_R33_UFU_BYPASS_EXIT" in txt
                    or "FX6_R33_5TIER_EXIT" in txt
                    or "FX6_R34_CXD90058_SABIN_EXIT" in txt
                    or "FX6_R34_RAID6_SEAL16_EXIT" in txt
                    or "FX6_R35_POWERLOSS_100CYCLE_EXIT" in txt
                    or "FX6_R35_SLOT1_UFU_C2PA_EXIT" in txt
                    or "FX6_R36_HDMI_4264_RAW_EXIT" in txt
                    or "FX6_R36_WPA3_FOCUSMAP_EXIT" in txt
                    or "FX6_R37_XLRH1_4CH_EXIT" in txt
                    or "FX6_R37_FX3BNDL1_SERIAL_EXIT" in txt
                    or "FX6_R38_LUT_CINEEI_EXIT" in txt
                    or "FX6_R38_RMTP1BT_CLIPFLAG_EXIT" in txt
                    or "FX6_R39_SHUTTER_SPEED_ANGLE_EXIT" in txt
                    or "FX6_R39_LUT_601_702_FIREWALL_EXIT" in txt
                    or "FX6_R40_CAMSET_SLOT1_SPLIT_EXIT" in txt
                    or "FX6_R40_VMCBNCM1_TCIN_HDMI_EXIT" in txt
                    or "FX6_R41_FOCUSMAP_150FPS_EXIT" in txt
                    or "FX6_R41_SIMULT_SHOCKLESSWB_EXIT" in txt
                    or "FX6_R42_PROXY_VAULT_EXIT" in txt
                    or "FX6_R42_FOCUSMAG_BRIGHTMON_EXIT" in txt
                    or "FX6_R43_TC_REGENERATE_EXIT" in txt
                    or "FX6_R43_RECLAMP_SILENT_EXIT" in txt
                    or "FX6_R44_NTSCPAL_CAMRESET_EXIT" in txt
                    or "FX6_R44_GAMMAASSIST_DISPLAYLUT_EXIT" in txt
                    or "FX6_R45_CIZ_4LOCKS_EXIT" in txt
                    or "FX6_R45_POWERSAVE_AUTOTEMP_EXIT" in txt
                    or "FX6_R46_ZEBRA_PEAKING_HDMI_EXIT" in txt
                    or "FX6_R46_FULLFORMAT_CHORD_VAULT_EXIT" in txt
                    or "FX6_R47_MARKER_15RATIO_HDMI_EXIT" in txt
                    or "FX6_R47_FLEXEXP_RESET_SPLIT_EXIT" in txt
                    or "FX6_R48_RECOVER_IMAGEDB_VAULT_EXIT" in txt
                    or "FX6_R48_AF_SENS_INTERVAL_EXIT" in txt
                    or "FX6_R49_TOUCH_OP_VAULT_EXIT" in txt
                    or "FX6_R49_MONITOR_BRIGHTNESS_EXIT" in txt
                ):
                    time.sleep(1.0)
                    print(f"[{run_id}] Detected clean early-phase verification exit; stopping early.", flush=True)
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
            or "FX6_R29_ROLLBACK_EXIT" in serial_text
            or "FX6_R29_P1_RESCUE_EXIT" in serial_text
            or "FX6_R30_CANARY_TIER0_EXIT" in serial_text
            or "FX6_R30_JBUSY_UNINSTALL_EXIT" in serial_text
            or "FX6_R31_FAN_FZ100_EXIT" in serial_text
            or "FX6_R31_MTDRO_EXIT" in serial_text
            or "FX6_R32_CDCNCM_EXIT" in serial_text
            or "FX6_R32_UART_EXIT" in serial_text
            or "FX6_R33_UFU_BYPASS_EXIT" in serial_text
            or "FX6_R33_5TIER_EXIT" in serial_text
            or "FX6_R34_CXD90058_SABIN_EXIT" in serial_text
            or "FX6_R34_RAID6_SEAL16_EXIT" in serial_text
            or "FX6_R35_POWERLOSS_100CYCLE_EXIT" in serial_text
            or "FX6_R35_SLOT1_UFU_C2PA_EXIT" in serial_text
            or "FX6_R36_HDMI_4264_RAW_EXIT" in serial_text
            or "FX6_R36_WPA3_FOCUSMAP_EXIT" in serial_text
            or "FX6_R37_XLRH1_4CH_EXIT" in serial_text
            or "FX6_R37_FX3BNDL1_SERIAL_EXIT" in serial_text
            or "FX6_R38_LUT_CINEEI_EXIT" in serial_text
            or "FX6_R38_RMTP1BT_CLIPFLAG_EXIT" in serial_text
            or "FX6_R39_SHUTTER_SPEED_ANGLE_EXIT" in serial_text
            or "FX6_R39_LUT_601_702_FIREWALL_EXIT" in serial_text
            or "FX6_R40_CAMSET_SLOT1_SPLIT_EXIT" in serial_text
            or "FX6_R40_VMCBNCM1_TCIN_HDMI_EXIT" in serial_text
            or "FX6_R41_FOCUSMAP_150FPS_EXIT" in serial_text
            or "FX6_R41_SIMULT_SHOCKLESSWB_EXIT" in serial_text
            or "FX6_R42_PROXY_VAULT_EXIT" in serial_text
            or "FX6_R42_FOCUSMAG_BRIGHTMON_EXIT" in serial_text
            or "FX6_R43_TC_REGENERATE_EXIT" in serial_text
            or "FX6_R43_RECLAMP_SILENT_EXIT" in serial_text
            or "FX6_R44_NTSCPAL_CAMRESET_EXIT" in serial_text
            or "FX6_R44_GAMMAASSIST_DISPLAYLUT_EXIT" in serial_text
            or "FX6_R45_CIZ_4LOCKS_EXIT" in serial_text
            or "FX6_R45_POWERSAVE_AUTOTEMP_EXIT" in serial_text
            or "FX6_R46_ZEBRA_PEAKING_HDMI_EXIT" in serial_text
            or "FX6_R46_FULLFORMAT_CHORD_VAULT_EXIT" in serial_text
            or "FX6_R47_MARKER_15RATIO_HDMI_EXIT" in serial_text
            or "FX6_R47_FLEXEXP_RESET_SPLIT_EXIT" in serial_text
            or "FX6_R48_RECOVER_IMAGEDB_VAULT_EXIT" in serial_text
            or "FX6_R48_AF_SENS_INTERVAL_EXIT" in serial_text
            or "FX6_R49_TOUCH_OP_VAULT_EXIT" in serial_text
            or "FX6_R49_MONITOR_BRIGHTNESS_EXIT" in serial_text
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
            "r29_mode": r29_mode if args.round == 29 else None,
            "r30_mode": r30_mode if args.round >= 30 else None,
            "r31_mode": r31_mode if args.round >= 31 else None,
            "r32_mode": r32_mode if args.round >= 32 else None,
            "r33_mode": r33_mode if args.round >= 33 else None,
            "r34_mode": r34_mode if args.round >= 34 else None,
            "r35_mode": r35_mode if args.round >= 35 else None,
            "r36_mode": r36_mode if args.round >= 36 else None,
            "r37_mode": r37_mode if args.round >= 37 else None,
            "r38_mode": r38_mode if args.round >= 38 else None,
            "r39_mode": r39_mode if args.round >= 39 else None,
            "r40_mode": r40_mode if args.round >= 40 else None,
            "r41_mode": r41_mode if args.round >= 41 else None,
            "r42_mode": r42_mode if args.round >= 42 else None,
            "r43_mode": r43_mode if args.round >= 43 else None,
            "r44_mode": r44_mode if args.round >= 44 else None,
            "r45_mode": r45_mode if args.round >= 45 else None,
            "r46_mode": r46_mode if args.round >= 46 else None,
            "r47_mode": r47_mode if args.round >= 47 else None,
            "r48_mode": r48_mode if args.round >= 48 else None,
            "r49_mode": r49_mode if args.round >= 49 else None,
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
            "r29_telemetry": milestones.get("r29_telemetry") if args.round == 29 else None,
            "r30_telemetry": milestones.get("r30_telemetry") if args.round >= 30 else None,
            "r31_telemetry": milestones.get("r31_telemetry") if args.round >= 31 else None,
            "r32_telemetry": milestones.get("r32_telemetry") if args.round >= 32 else None,
            "r33_telemetry": milestones.get("r33_telemetry") if args.round >= 33 else None,
            "r34_telemetry": milestones.get("r34_telemetry") if args.round >= 34 else None,
            "r35_telemetry": milestones.get("r35_telemetry") if args.round >= 35 else None,
            "r36_telemetry": milestones.get("r36_telemetry") if args.round >= 36 else None,
            "r37_telemetry": milestones.get("r37_telemetry") if args.round >= 37 else None,
            "r38_telemetry": milestones.get("r38_telemetry") if args.round >= 38 else None,
            "r39_telemetry": milestones.get("r39_telemetry") if args.round >= 39 else None,
            "r40_telemetry": milestones.get("r40_telemetry") if args.round >= 40 else None,
            "r41_telemetry": milestones.get("r41_telemetry") if args.round >= 41 else None,
            "r42_telemetry": milestones.get("r42_telemetry") if args.round >= 42 else None,
            "r43_telemetry": milestones.get("r43_telemetry") if args.round >= 43 else None,
            "r44_telemetry": milestones.get("r44_telemetry") if args.round >= 44 else None,
            "r45_telemetry": milestones.get("r45_telemetry") if args.round >= 45 else None,
            "r46_telemetry": milestones.get("r46_telemetry") if args.round >= 46 else None,
            "r47_telemetry": milestones.get("r47_telemetry") if args.round >= 47 else None,
            "r48_telemetry": milestones.get("r48_telemetry") if args.round >= 48 else None,
            "r49_telemetry": milestones.get("r49_telemetry") if args.round >= 49 else None,
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
    # r47_test_compat: choices=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47]
    # r48_test_compat: choices=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48]
    ap.add_argument("--round", type=int, choices=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49], required=True)
    ap.add_argument("--lang", type=str, choices=["en", "english", "schinese", "tchinese", "japanese"], default="en")
    ap.add_argument("--sd-manifest-mode", type=str, choices=["valid", "absent", "tampered"], default="valid")
    ap.add_argument("--r29-mode", type=str, choices=["install_mpr_rec", "rollback", "p1_rescue"], default="install_mpr_rec")
    ap.add_argument("--r30-mode", type=str, choices=["canary_tier0", "peripheral_big6", "jbusy_uninstall"], default="peripheral_big6")
    ap.add_argument("--r31-mode", type=str, choices=["keymap_big6", "fan_fz100_power", "mtdro_firewall"], default="keymap_big6")
    ap.add_argument("--r32-mode", type=str, choices=["imx510_cube_big6", "cdcncm_usb_0da1", "uart_6stage_triage"], default="imx510_cube_big6")
    ap.add_argument("--r33-mode", type=str, choices=["cfexpress_rsv_big6", "bodydata_ufu_bypass", "recovery_5tier"], default="cfexpress_rsv_big6")
    ap.add_argument("--r34-mode", type=str, choices=["c2pa_tc_gyro_big6", "cxd90058_sabin_sdi_mask", "raid6_gf256_seal_16"], default="c2pa_tc_gyro_big6")
    ap.add_argument("--r35-mode", type=str, choices=["ssboot_wbi2_big6", "powerloss_100cycle_rsv", "slot1_ufu_c2pa_ceiling"], default="ssboot_wbi2_big6")
    ap.add_argument("--r36-mode", type=str, choices=["emount_info3d_big6", "hdmi_4264_raw_prores_braw", "wpa2_wpa3_focusmap_bridge"], default="emount_info3d_big6")
    ap.add_argument("--r37-mode", type=str, choices=["fx3a_firewall_big6", "xlrh1_4ch_override", "fx3bndl1_serial_appledouble"], default="fx3a_firewall_big6")
    ap.add_argument("--r38-mode", type=str, choices=["nouvc_dcc1_pd_big6", "lut_path_cineei", "rmtp1bt_clipflag_seal"], default="nouvc_dcc1_pd_big6")
    ap.add_argument("--r39-mode", type=str, choices=["fan_pwm_offinrec_big6", "shutter_speed_angle_clamp", "lut_601_vs_702_firewall"], default="fan_pwm_offinrec_big6")
    ap.add_argument("--r40-mode", type=str, choices=["big6_home_noend_big6", "camset_slot1_dualmedia_split", "vmcbncm1_tcin_hdmi_tcout"], default="big6_home_noend_big6")
    ap.add_argument("--r41-mode", type=str, choices=["desqueeze_165x_4locks_big6", "external_focusmap_150fps_cutoff", "simult_autoswitch_shocklesswb"], default="desqueeze_165x_4locks_big6")
    ap.add_argument("--r42-mode", type=str, choices=["hdmi_log1080_hdmionly_4k_big6", "proxy_vault_119p_atomic_pair", "focusmag_brightmon_h0_h3"], default="hdmi_log1080_hdmionly_4k_big6")
    ap.add_argument("--r43-mode", type=str, choices=["filesettings_shotmark_big6", "tc_regenerate_slot1_extlk", "reclamp_coupled_tally_h0_h3"], default="filesettings_shotmark_big6")
    ap.add_argument("--r44-mode", type=str, choices=["pixelmap_reboot_cnflasha_big6", "ntscpal_dfn_camreset_persist", "gammaassist_displaylut_h0_h3"], default="pixelmap_reboot_cnflasha_big6")
    ap.add_argument("--r45-mode", type=str, choices=["steadyshot_active_cutoffs_big6", "ciz_4locks_hfr_raw_cutoffs", "powersave_9cond_autotemp_h0_h3"], default="steadyshot_active_cutoffs_big6")
    ap.add_argument("--r46-mode", type=str, choices=["sq_fixedvar_6locks_big6", "zebra_persist_peaking_hdmi_isolation", "slot1_fullformat_chord_vault_h0_h3"], default="sq_fixedvar_6locks_big6")
    ap.add_argument("--r47-mode", type=str, choices=["silent_autopixelmap_5locks_big6", "marker_15ratio_persist_hdmi_isolation", "flexexp_avtviso_autoslowshutter_h0_h3"], default="silent_autopixelmap_5locks_big6")
    ap.add_argument("--r48-mode", type=str, choices=["recover_imagedb_battery_vault", "monitor_flip_playback_big6", "af_sens_interval_still_h0_h3"], default="monitor_flip_playback_big6")
    ap.add_argument("--r49-mode", type=str, choices=["emphasized_rec_grid_hdmi_big6", "touch_op_4item_reset_vault", "monitor_brightness_sunny_h0_h3"], default="emphasized_rec_grid_hdmi_big6")
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
