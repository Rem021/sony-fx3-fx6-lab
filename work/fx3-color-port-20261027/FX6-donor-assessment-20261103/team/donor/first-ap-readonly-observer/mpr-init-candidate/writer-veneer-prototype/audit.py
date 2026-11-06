"""Recheck fixed original SHA, ELF VA/fileoff and writer temporal edges."""
from __future__ import annotations

import json
import re
import struct
import subprocess
from pathlib import Path

from gen_inputs import DONOR, HERE, MAP, OBS, PINS, sha

MAC = HERE.parents[7]
FX3 = MAC / "work/sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/libmpr.so"
FX6 = DONOR / "nflasha15-files/lib/libmpr.so"
AP = DONOR / "nflasha15-files/lib/appFw.so"
ELF_PINS = {
    FX3: "9aeef3b9edb3d011c0c90cd2387b3a47bd3b506ebfa57be39ad1a9729771b57c",
    FX6: "814dfff34cac6517d71f659fce8d1ead0bb7ee52b8a9ac1a4e25aa9f83ac2d4e",
    AP: "a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067",
}
POINTS = {
    "fx3_mpr": (FX3, {
        "init_ldrh": 0xb7080, "init_record_call": 0xb7094,
        "u16_uxth": 0xd603c, "first_writer_new": 0xd60a8,
        "second_writer_new": 0xd60c8, "first_param_store": 0xd60e4,
        "first_writer_initializer": 0xd60f8, "second_param_store": 0xd6110,
        "second_writer_initializer": 0xd6120,
        "init_log_u16_read": 0x119798, "init_log_u16_stack": 0x1197a8,
        "init_log_call": 0x1197c4, "log_osal_allocation": 0x115a70,
        "writer_param_read": 0x1197c8, "writer_member_store": 0x1197cc,
        "init_queue_new": 0xd6278, "init_queue_ctor": 0xd6284,
        "threshold_this_saved": 0x11d178,
        "threshold_precheck_notification": 0x11faac,
        "threshold_precheck_stream": 0x11fab4,
        "threshold_precheck_fps": 0x11fabc,
        "threshold_member_read": 0x11fac8,
        "enterrec_setinfo": 0xd7e98, "enterrec_enqueue_open": 0xd7e28,
    }),
    "fx6_mpr": (FX6, {
        "init_ldrh": 0x12bd30, "manager_u16_store": 0x155de4,
        "mode_field_read": 0x157960, "mode_compare_8": 0x157964,
        "mode_branch_to_xavcs": 0x157968, "mxf_new": 0x15796c,
        "mxf_ctor": 0x157978, "xavcs_new": 0x157808,
        "xavcs_ctor": 0x157814, "xavcs_effective_constant": 0x1b0f44,
        "xavcs_effective_store": 0x1b0f48, "mxf_param_read": 0x194124,
        "mxf_effective_store": 0x194128, "xavcs_threshold_read": 0x1b679c,
        "mxf_threshold_read": 0x199494,
        "movie_write_producer_size": 0x1450f8,
        "movie_write_size_argument": 0x14516c,
        "movie_write_submit_call": 0x145178,
        "auto_divided_producer_size": 0x1455c0,
        "auto_divided_size_argument": 0x145630,
        "auto_divided_submit_call": 0x14563c,
    }),
    "fx6_ap": (AP, {
        "init_source_1440": 0x212f498,
        "init_source_store": 0x212f49c,
        "init_plt_call": 0x212f7b8,
        "enterrec_plt_call": 0x214314c,
        "movie_write_unconditional_byte": 0x213caa0,
        "movie_write_unconditional_qword": 0x213caec,
        "auto_unconditional_byte": 0x212da18,
        "auto_unconditional_qword": 0x212da54,
    }),
}


def offset(elf: bytes, va: int) -> int:
    if elf[:6] != b"\x7fELF\x02\x01":
        raise ValueError("ELF64 little endian required")
    phoff = struct.unpack_from("<Q", elf, 32)[0]
    entsz, n = struct.unpack_from("<HH", elf, 54)
    for i in range(n):
        p = phoff + i * entsz
        typ = struct.unpack_from("<I", elf, p)[0]
        if typ != 1:
            continue
        off, vaddr = struct.unpack_from("<QQ", elf, p+8)
        filesz = struct.unpack_from("<Q", elf, p+32)[0]
        if vaddr <= va < vaddr + filesz:
            return off + va - vaddr
    raise ValueError(f"0x{va:x} outside PT_LOAD file bytes")


def instruction(path: Path, elf: bytes, va: int) -> dict:
    off = offset(elf, va)
    dis = subprocess.run(["objdump", "-d", f"--start-address=0x{va:x}",
                          f"--stop-address=0x{va+4:x}", str(path)],
                         check=True, capture_output=True, text=True).stdout
    rows = [line for line in dis.splitlines() if re.match(rf"^\s*{va:x}:\s", line)]
    if len(rows) != 1:
        raise ValueError(f"objdump missing VA 0x{va:x}")
    word = elf[off:off+4].hex()
    if word != bytes.fromhex(rows[0].split(":",1)[1].split()[0])[::-1].hex():
        raise ValueError(f"word mismatch at {va:x}")
    return {"va": f"0x{va:x}", "fileoff": f"0x{off:x}",
            "bytes_le": word, "objdump": rows[0].strip()}


def main() -> None:
    for path, expected in {**PINS, **ELF_PINS}.items():
        if sha(path) != expected:
            raise ValueError(f"fixed SHA drift {path}")
    result = {"scope": "original ELF instruction static, prior real parameter snapshot, own host only",
              "input_sha256": {str(p): h for p,h in {**PINS, **ELF_PINS}.items()},
              "instructions": {}}
    for key, (path, points) in POINTS.items():
        elf = path.read_bytes()
        result["instructions"][key] = {name: instruction(path, elf, va)
                                        for name, va in points.items()}
    ap_relocs = subprocess.run(["objdump", "-R", str(AP)], check=True,
                               capture_output=True, text=True).stdout
    fx3_exports = subprocess.run(["objdump", "-T", str(FX3)], check=True,
                                 capture_output=True, text=True).stdout
    required = {
        "Init": ("0000000002ef1368", "_ZN3mpr4InitERKNS_11initInParamE"),
        "EnterRec": ("0000000002ef2670", "_ZN3mpr8EnterRecERKNS_15enterRecInParamE"),
    }
    result["ap_jump_slots_and_fx3_exports"] = {}
    for name, (got, symbol) in required.items():
        rel = [line for line in ap_relocs.splitlines()
               if got in line and "R_AARCH64_JUMP_SLOT" in line and symbol in line]
        exp = [line for line in fx3_exports.splitlines() if " g " in line and " DF " in line and symbol in line]
        if len(rel) != 1 or len(exp) != 1:
            raise ValueError(f"original AP relocation / FX3 export missing: {name}")
        result["ap_jump_slots_and_fx3_exports"][name] = {"ap_relocation": rel[0], "fx3_export": exp[0]}
    obs = json.loads(OBS.read_text())
    raw = bytes.fromhex(next(r for r in obs["records"] if r["kind"] == "call")["parameter_0x290_hex"])
    if raw != (HERE / "genuine-input.bin").read_bytes():
        raise ValueError("generated input drift")
    result["snapshot"] = {"sha256": sha(HERE / "genuine-input.bin"),
                          "count": struct.unpack_from("<I",raw,0x268)[0],
                          "slots": struct.unpack_from("<4I",raw,0x26c),
                          "u16": struct.unpack_from("<H",raw,0x28a)[0]}
    (HERE / "evidence.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print("audited", sum(len(p[1]) for p in POINTS.values()), "original instructions")


if __name__ == "__main__":
    main()
