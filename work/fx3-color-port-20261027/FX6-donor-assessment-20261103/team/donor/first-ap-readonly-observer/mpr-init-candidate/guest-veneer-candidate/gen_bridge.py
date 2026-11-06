"""Generate pinned C offsets, trap entries, and AP/MPR digest constants."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DONOR = HERE.parents[2]
MAP = DONOR / "capid-init-portability/callback-fields.json"
MAP_SHA = "aef19dda30c2120538ad4ed66b536b25f01eb94c8326239658b0f5953ff660a5"
MPR_SHA = "9aeef3b9edb3d011c0c90cd2387b3a47bd3b506ebfa57be39ad1a9729771b57c"
OBS = HERE.parent / "runs/mpr-ro-b22ccc48/mpr-observation.json"
OBS_SHA = "fa8e834e999aafb573118ee34de89b1d7b38111fc13ef1c7122ddef774ef31e2"


def main() -> None:
    if hashlib.sha256(MAP.read_bytes()).hexdigest() != MAP_SHA:
        raise ValueError("callback map drift")
    if hashlib.sha256(OBS.read_bytes()).hexdigest() != OBS_SHA:
        raise ValueError("historic snapshot receipt drift")
    patch = json.loads((HERE / "ap-patch.json").read_text())
    ap = HERE / "appFw-bridge.so"
    if hashlib.sha256(ap.read_bytes()).hexdigest() != patch["patched_sha256"]:
        raise ValueError("patched AP drift")
    rows = json.loads(MAP.read_text())["symbol_mapping"]
    common = sorted((r for r in rows if r["fx3_offset"] is not None),
                    key=lambda r: int(r["fx3_offset"],16))
    extra = sorted((r for r in rows if r["fx3_offset"] is None),
                   key=lambda r: int(r["fx6_offset"],16))
    if len(common) != 57 or len(extra) != 18 or \
       [int(r["fx3_offset"],16) for r in common] != list(range(8,0x1d0,8)):
        raise ValueError("callback ranges drift")
    offsets = ["#pragma once", "#include <stdint.h>",
               "static const uint16_t fx6diag_dst_offsets[57] = {" +
               ",".join(str(int(r["fx3_offset"],16)) for r in common) + "};",
               "static const uint16_t fx6diag_src_offsets[57] = {" +
               ",".join(str(int(r["fx6_offset"],16)) for r in common) + "};",
               "static const uint16_t fx6diag_extra_offsets[18] = {" +
               ",".join(str(int(r["fx6_offset"],16)) for r in extra) + "};"]
    (HERE / "callback_offsets.h").write_text("\n".join(offsets)+"\n")
    digest = lambda h: ",".join("0x"+h[i:i+2] for i in range(0,64,2))
    (HERE / "bridge_pins.h").write_text(
        "#pragma once\n#include <stdint.h>\n"+
        "static const uint8_t fx6diag_expected_ap_sha[32]={"+digest(patch["patched_sha256"])+"};\n"+
        "static const uint8_t fx6diag_expected_mpr_sha[32]={"+digest(MPR_SHA)+"};\n")
    asm = [".text", ".balign 4"]
    for i in range(57):
        name=f"fx6diag_slot_{i:02d}"
        asm += [f".global {name}", f".type {name},%function", f"{name}:",
                f"    brk #0x{0x600+i:x}", "    b .", f".size {name}, .-{name}"]
    for name, imm in (("fx6diag_mpr_enterrec",0x7f0),("fx6diag_failstop",0x7fe)):
        asm += [f".global {name}",f".type {name},%function",f"{name}:",
                f"    brk #0x{imm:x}","    b .",f".size {name}, .-{name}"]
    asm += [".global fx6diag_call_original", ".type fx6diag_call_original,%function",
            "fx6diag_call_original:", "    stp x29, x30, [sp, #-16]!", "    mov x29, sp",
            "    blr x1", "    ldp x29, x30, [sp], #16", "    ret",
            ".size fx6diag_call_original, .-fx6diag_call_original",
            ".section .data.rel.ro,\"aw\",%progbits", ".balign 8",
            ".global fx6diag_slot_table", ".type fx6diag_slot_table,%object",
            "fx6diag_slot_table:"]
    asm += [f"    .xword fx6diag_slot_{i:02d}" for i in range(57)]
    asm += [".size fx6diag_slot_table, .-fx6diag_slot_table"]
    (HERE / "bridge_stops.S").write_text("\n".join(asm)+"\n")
    calls=[r for r in json.loads(OBS.read_text())["records"] if r["kind"]=="call"]
    if len(calls)!=1:raise ValueError("expected one historic Init call")
    raw=bytes.fromhex(calls[0]["parameter_0x290_hex"])
    if len(raw)!=0x290 or hashlib.sha256(raw).hexdigest()!="585d8918da368cec6ef689aa3c14dc3306311ab6661c0bffc9a02e1685430cf1":
        raise ValueError("historic Init parameter drift")
    (HERE/"genuine-input.bin").write_bytes(raw)
    print("generated 57 BRK-first thunks, enterrec/fail stops, pinned offsets")


if __name__ == "__main__": main()
