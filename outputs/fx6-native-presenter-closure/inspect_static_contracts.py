#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib
import struct
import subprocess
import sys
from typing import Any, Dict, List

DONOR_ROOT = pathlib.Path(
    "/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/"
    "FX6-donor-assessment-20261103/team/donor/nflasha15-files"
)

TARGET_BINARIES = [
    "bin/im.elf",
    "lib/libIMDB.so",
    "lib/libMWF.so",
    "lib/libgrm.so",
    "lib/libosal_uipc.so",
    "lib/appFw.so",
]


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def disasm_range(path: pathlib.Path, start: int, stop: int) -> str:
    return subprocess.check_output(
        [
            "/usr/bin/objdump",
            "-d",
            f"--start-address={hex(start)}",
            f"--stop-address={hex(stop)}",
            str(path),
        ],
        text=True,
    )


def parse_imdb_entries(libimdb_path: pathlib.Path) -> List[Dict[str, Any]]:
    data = libimdb_path.read_bytes()
    # In FX6 6.01 libIMDB.so, .data is at file offset 0xdf30 with VMA 0x1df30;
    # imdb_raw starts at VMA 0x1e870 (file offset 0xe870), entries at +0x100 (VMA 0x1e970).
    table_vma = 0x1E970
    vma_to_file = 0x10000
    table_off = table_vma - vma_to_file

    def read_cstr(ptr: int) -> str:
        if ptr == 0:
            return ""
        off = ptr - vma_to_file
        if off < 0 or off >= len(data):
            return f"<va:{hex(ptr)}>"
        end = data.find(b"\x00", off)
        if end < 0:
            return ""
        return data[off:end].decode("ascii", errors="replace")

    entries: List[Dict[str, Any]] = []
    for idx in range(180):
        off = table_off + idx * 72
        if off + 72 > len(data):
            break
        kind, flags, mask = struct.unpack_from("<III", data, off)
        mod_id, sel = struct.unpack_from("<II", data, off + 0x18)
        lib_p, sym_p, arg0_p, arg1_p = struct.unpack_from("<QQQQ", data, off + 0x28)
        entry = {
            "index": idx,
            "vma": hex(table_vma + idx * 72),
            "kind": hex(kind),
            "flags": hex(flags),
            "target_mask": hex(mask),
            "module_id": mod_id,
            "sel": sel,
            "lib": read_cstr(lib_p),
            "init": read_cstr(sym_p),
            "arg0": read_cstr(arg0_p),
            "arg1": read_cstr(arg1_p),
        }
        entries.append(entry)
        if kind == 0x08000009:
            break
    return entries


def collect_contracts() -> Dict[str, Any]:
    digests: Dict[str, Dict[str, Any]] = {}
    for rel in TARGET_BINARIES:
        p = DONOR_ROOT / rel
        digests[rel] = {
            "size_bytes": p.stat().st_size,
            "sha256": sha256_file(p),
        }

    imdb_entries = parse_imdb_entries(DONOR_ROOT / "lib/libIMDB.so")
    interesting_imdb = [
        e
        for e in imdb_entries
        if e["kind"].startswith("0x800000")
        or e["lib"] in ("libMWF.so", "libkiki.so", "appFw.so", "libgrm.so")
        or e["init"] in ("MWF_Init", "Application_System_Init", "BIZ_Init")
    ]

    snippets = {
        "im_elf_main_phases": disasm_range(DONOR_ROOT / "bin/im.elf", 0x402490, 0x402750),
        "im_elf_kind_dispatch": disasm_range(DONOR_ROOT / "bin/im.elf", 0x405E24, 0x4062A0),
        "mwf_init_thunk": disasm_range(DONOR_ROOT / "lib/libMWF.so", 0x27D68, 0x27E78),
        "mwf_rsrc_dp_init": disasm_range(DONOR_ROOT / "lib/libMWF.so", 0x38CB0, 0x38DF4),
        "mwf_rsrc_relation_init": disasm_range(DONOR_ROOT / "lib/libMWF.so", 0x3A57C, 0x3A658),
        "mwf_objshlock_ctor_and_lock": disasm_range(DONOR_ROOT / "lib/libMWF.so", 0x3B300, 0x3B498),
        "grm_register_trigger_cb": disasm_range(DONOR_ROOT / "lib/libgrm.so", 0x22C78, 0x22D20),
        "grm_c_api_trigger_cb": disasm_range(DONOR_ROOT / "lib/libgrm.so", 0x236A8, 0x236D0),
        "appfw_app_initialize": disasm_range(DONOR_ROOT / "lib/appFw.so", 0xC09DA0, 0xC09E88),
        "appfw_trigger_cb_body": disasm_range(DONOR_ROOT / "lib/appFw.so", 0xC091D0, 0xC091EC),
        "appfw_frame_gate_helpers": disasm_range(DONOR_ROOT / "lib/appFw.so", 0xDE4240, 0xDE42AC),
        "appfw_start_utimer": disasm_range(DONOR_ROOT / "lib/appFw.so", 0xC09C14, 0xC09D9C),
        "appfw_cold_boot_tail": disasm_range(DONOR_ROOT / "lib/appFw.so", 0x1CD8604, 0x1CD86B4),
        "appfw_init_hdmi": disasm_range(DONOR_ROOT / "lib/appFw.so", 0x1CD80DC, 0x1CD81C4),
    }

    return {
        "donor_root": str(DONOR_ROOT),
        "digests": digests,
        "imdb_highlights": interesting_imdb,
        "snippet_line_counts": {k: len(v.splitlines()) for k, v in snippets.items()},
    }


def main() -> int:
    summary = collect_contracts()
    out_path = pathlib.Path(__file__).resolve().parent / "static-contracts-summary.json"
    out_path.write_text(json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(f"Wrote {out_path} ({out_path.stat().st_size} bytes)")
    for rel, info in summary["digests"].items():
        print(f"  {rel}: {info['size_bytes']} B  sha256={info['sha256']}")
    print(f"  imdb_highlights: {len(summary['imdb_highlights'])} entries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
