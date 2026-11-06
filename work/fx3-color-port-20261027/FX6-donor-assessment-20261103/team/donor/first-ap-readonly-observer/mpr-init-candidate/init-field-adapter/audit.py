"""只读核对固定 ELF、回调 load、Init 字段读和真实参数快照。"""
from __future__ import annotations

import hashlib
import json
import re
import struct
import subprocess
from pathlib import Path

from init_adapter import CALLBACK_INDEX, CALLBACK_INDEX_SHA, DONOR, project

ROOT = Path(__file__).resolve().parent
MAC = ROOT.parents[7]
FX3 = MAC / "work/sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/libmpr.so"
FX6_MPR = DONOR / "nflasha15-files/lib/libmpr.so"
FX6_AP = DONOR / "nflasha15-files/lib/appFw.so"
OBS = ROOT.parent / "runs/mpr-ro-b22ccc48/mpr-observation.json"
PINS = {
    FX3: "9aeef3b9edb3d011c0c90cd2387b3a47bd3b506ebfa57be39ad1a9729771b57c",
    FX6_MPR: "814dfff34cac6517d71f659fce8d1ead0bb7ee52b8a9ac1a4e25aa9f83ac2d4e",
    FX6_AP: "a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067",
    CALLBACK_INDEX: CALLBACK_INDEX_SHA,
    OBS: "fa8e834e999aafb573118ee34de89b1d7b38111fc13ef1c7122ddef774ef31e2",
}


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def fileoff(elf: bytes, va: int) -> int:
    if elf[:4] != b"\x7fELF" or elf[4:6] != b"\x02\x01":
        raise ValueError("not ELF64 little-endian")
    phoff = struct.unpack_from("<Q", elf, 32)[0]
    entsz, n = struct.unpack_from("<HH", elf, 54)
    for i in range(n):
        p = phoff + i * entsz
        typ = struct.unpack_from("<I", elf, p)[0]
        if typ != 1:
            continue
        off, vaddr = struct.unpack_from("<QQ", elf, p + 8)
        filesz = struct.unpack_from("<Q", elf, p + 32)[0]
        if vaddr <= va < vaddr + filesz:
            return off + va - vaddr
    raise ValueError(f"VA 0x{va:x} outside PT_LOAD filesz")


def executable(elf: bytes, va: int) -> bool:
    phoff = struct.unpack_from("<Q", elf, 32)[0]
    entsz, n = struct.unpack_from("<HH", elf, 54)
    for i in range(n):
        p = phoff + i * entsz
        typ, flags = struct.unpack_from("<II", elf, p)
        if typ != 1:
            continue
        vaddr = struct.unpack_from("<Q", elf, p + 16)[0]
        filesz = struct.unpack_from("<Q", elf, p + 32)[0]
        if vaddr <= va < vaddr + filesz:
            return bool(flags & 1)
    return False


def word(elf: bytes, va: int) -> dict:
    off = fileoff(elf, va)
    return {"va": f"0x{va:x}", "fileoff": f"0x{off:x}", "word_le": elf[off:off+4].hex()}


def main() -> None:
    for path, expected in PINS.items():
        actual = sha(path)
        if actual != expected:
            raise ValueError(f"SHA drift {path}: {actual}")
    fx3, fx6, ap = (p.read_bytes() for p in (FX3, FX6_MPR, FX6_AP))
    mapping = json.loads(CALLBACK_INDEX.read_text())
    verified_loads = {}
    for key, elf in (("fx3_mpr", fx3), ("fx6_mpr", fx6)):
        verified_loads[key] = []
        for row in mapping["loads"][key]:
            for name in ("load", "got_load"):
                entry = row[name]
                va = int(entry["va"], 16)
                w = word(elf, va)
                if w["fileoff"] != entry["fileoff"] or w["word_le"] != entry["bytes_le"]:
                    raise ValueError(f"callback {name} mismatch {key} {va:x}")
            verified_loads[key].append(row["offset"])
    if set(verified_loads["fx3_mpr"]) != set(range(8, 0x1d0, 8)):
        raise ValueError("FX3 callback field range incomplete")
    dis = subprocess.run(["objdump", "-d", "--start-address=0xb6844",
                          "--stop-address=0xb70b0", str(FX3)],
                         check=True, capture_output=True, text=True).stdout
    direct = []
    for line in dis.splitlines():
        m = re.search(r"^\s*([0-9a-f]+):\s+([0-9a-f]{8})\s+(.+)$", line)
        if not m:
            continue
        asm = m.group(3)
        op = re.search(r"\[x19, #0x([0-9a-f]+)\]", asm)
        if op and re.search(r"\b(?:ldr|ldrh|ldrb|ldrsw|ldp)\b", asm):
            direct.append({**word(fx3, int(m.group(1), 16)), "offset": int(op.group(1), 16), "asm": asm})
    found = {r["offset"] for r in direct}
    expected = set(range(8, 0x1d0, 8)) | {0x1d0, 0x1e4, 0x1e8, 0x1f2}
    if found != expected:
        raise ValueError(f"unaccounted direct x19 reads: missing={expected-found} extra={found-expected}")
    keys = {
        "fx3_count_guard": (fx3, [0xb6848, 0xb6870, 0xb6874, 0xb6878]),
        "fx3_slot_loop": (fx3, [0xb68ec, 0xb6ccc, 0xb6d10, 0xb7074, 0xb7094]),
        "fx3_control": (fx3, [0xb6f94, 0xb7080, 0xb7014, 0xb70a4]),
        "fx3_null_guard": (fx3, [0xb4b74, 0xb4b78, 0xb4b90, 0xb4ad4, 0xb4ad8, 0xb4ae0,
                                0xb4658, 0xb465c, 0xb4674, 0xb46dc, 0xb46e0, 0xb46f8]),
        "fx3_status": (fx3, [0xf42bc, 0xf4358, 0xf4394]),
        "fx3_dbgprint": (fx3, [0xa7600]),
        "fx6_producer": (ap, [0x212f478, 0x212f494, 0x212f498, 0x212f49c,
                              0x212f74c, 0x212f750, 0x212f798, 0x212f7b8]),
        "fx6_status": (fx6, [0x16e210, 0x16e270, 0x16e2ac, 0x16e2e8]),
    }
    original_words = {name: [word(elf, va) for va in vas] for name, (elf, vas) in keys.items()}
    observed = json.loads(OBS.read_text())
    calls = [r for r in observed["records"] if r["kind"] == "call"]
    if len(calls) != 1:
        raise ValueError("expected one observed call")
    call = calls[0]
    raw = bytes.fromhex(call["parameter_0x290_hex"])
    if sha(FX6_AP) != PINS[FX6_AP] or hashlib.sha256(raw).hexdigest() != call["parameter_0x290_sha256"]:
        raise ValueError("snapshot drift")
    if len(raw) != 0x290 or call["parameter_0x290_sha256"] != "585d8918da368cec6ef689aa3c14dc3306311ab6661c0bffc9a02e1685430cf1":
        raise ValueError("unexpected snapshot")
    if call["word_le"] != word(ap, int(call["va"], 16))["word_le"]:
        raise ValueError("AP call original word mismatch")
    projection = project(raw)
    bias = int(call["current_ap_identity"]["bias"], 16)
    for row in (*projection.callback_rows, *projection.fx6_extra_nonnull):
        if row.get("source_null", False):
            continue
        if not executable(ap, int(row["source_pointer"], 16) - bias):
            raise ValueError(f"snapshot callback not AP executable: {row['symbol']}")
    report = {
        "evidence_level": "original ELF static plus prior real VM parameter snapshot; host projection only",
        "pins": {str(p): h for p, h in PINS.items()},
        "observed_call": {"va": call["va"], "pc": call["pc"], "word_le": call["word_le"],
                          "parameter_sha256": call["parameter_0x290_sha256"]},
        "verified_callback_loads": {k: len(v) for k, v in verified_loads.items()},
        "fx3_init_direct_x19_loads": direct,
        "indirect_reads": ["x23=x19+0x1d4, four slot u32 reads with count loop",
                           "x20=x19+0x1ec, six node bytes forwarded"],
        "original_words": original_words,
        "actual_count": projection.count,
        "actual_slots": projection.slots,
        "status_active_all_four": projection.status_active,
        "msidconv_values": projection.msidconv_values,
        "actual_scalar_fields": projection.scalar_fields,
        "callback_nonnull_common": sum(not r["source_null"] for r in projection.callback_rows),
        "callback_nonnull_extra": len(projection.fx6_extra_nonnull),
        "nonnull_callback_pointers_in_original_ap_executable_pt_load": True,
    }
    (ROOT / "audit.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({k: report[k] for k in ("verified_callback_loads", "actual_count", "actual_slots", "callback_nonnull_common", "callback_nonnull_extra")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
