"""Pin existing evidence and generate only small host build inputs."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DONOR = HERE.parents[2]
MAP = DONOR / "capid-init-portability/callback-fields.json"
OBS = HERE.parent / "runs/mpr-ro-b22ccc48/mpr-observation.json"
PINS = {
    MAP: "aef19dda30c2120538ad4ed66b536b25f01eb94c8326239658b0f5953ff660a5",
    OBS: "fa8e834e999aafb573118ee34de89b1d7b38111fc13ef1c7122ddef774ef31e2",
}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    for path, expected in PINS.items():
        if sha(path) != expected:
            raise ValueError(f"fixed source SHA drift: {path}")
    rows = json.loads(MAP.read_text())["symbol_mapping"]
    common = sorted((r for r in rows if r["fx3_offset"] is not None),
                    key=lambda r: int(r["fx3_offset"], 16))
    extra = sorted((r for r in rows if r["fx3_offset"] is None),
                   key=lambda r: int(r["fx6_offset"], 16))
    if len(common) != 57 or len(extra) != 18:
        raise ValueError("unexpected 57/18 callback mapping")
    if [int(r["fx3_offset"], 16) for r in common] != list(range(8, 0x1d0, 8)):
        raise ValueError("FX3 offsets incomplete")
    lines = ["// Generated from pinned original callback-fields.json; no callback ABI claim.",
             "#pragma once", "#include <array>", "#include <cstdint>",
             "struct SlotMap { uint16_t dst; uint16_t src; const char* symbol; };",
             "inline constexpr std::array<SlotMap,57> kCommon = {{"]
    lines += [f'  SlotMap{{{int(r["fx3_offset"],16)}, {int(r["fx6_offset"],16)}, "{r["symbol"]}"}},'
              for r in common]
    lines += ["}};", "inline constexpr std::array<uint16_t,18> kExtra = {{"]
    lines += ["  " + ", ".join(str(int(r["fx6_offset"], 16)) for r in extra) + ",", "}};"]
    (HERE / "callback_map.hpp").write_text("\n".join(lines) + "\n")
    records = json.loads(OBS.read_text())["records"]
    calls = [r for r in records if r["kind"] == "call"]
    if len(calls) != 1:
        raise ValueError("expected one genuine MPR call")
    raw = bytes.fromhex(calls[0]["parameter_0x290_hex"])
    if len(raw) != 0x290 or hashlib.sha256(raw).hexdigest() != "585d8918da368cec6ef689aa3c14dc3306311ab6661c0bffc9a02e1685430cf1":
        raise ValueError("genuine input SHA drift")
    (HERE / "genuine-input.bin").write_bytes(raw)
    print(f"generated 57/18 map and {len(raw)}-byte genuine input")


if __name__ == "__main__":
    main()
