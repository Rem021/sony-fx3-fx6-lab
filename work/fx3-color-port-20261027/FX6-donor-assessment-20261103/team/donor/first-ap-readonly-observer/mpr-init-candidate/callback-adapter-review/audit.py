"""固定 ELF/原 GDB 回执的只读 VA→fileoff/原字/汇编核对。"""
from __future__ import annotations

import hashlib
import json
import re
import struct
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[7]  # /Volumes/KAFU2T/AI/Projects/Mac
DONOR = HERE.parents[2]
SOURCES = {
    "fx3_mpr": (PROJECT / "work/sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/libmpr.so",
                "9aeef3b9edb3d011c0c90cd2387b3a47bd3b506ebfa57be39ad1a9729771b57c"),
    "fx6_mpr": (DONOR / "nflasha15-files/lib/libmpr.so",
                "814dfff34cac6517d71f659fce8d1ead0bb7ee52b8a9ac1a4e25aa9f83ac2d4e"),
    "fx6_ap": (DONOR / "nflasha15-files/lib/appFw.so",
               "a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067"),
}
RUN = HERE.parent / "runs/mpr-ro-b22ccc48"
RUN_SHA = {
    "receipt.json": "cc2dcc056fecb556193610e2716062d462b6cb5d88cad2775113287046ad9e19",
    "mpr-observation.json": "fa8e834e999aafb573118ee34de89b1d7b38111fc13ef1c7122ddef774ef31e2",
    "serial.log": "011ba0bb9fb048a84428d4a732adeec953e348a3cd5ec65b4e4a3be9a99febd2",
}
PRIOR_CONTRACTS = {
    "poweron": (DONOR / "capid-init-portability/poweron-contract/README.md",
                "22484628b889c6191306217c3455eea9dc7a6b9d45573f85470d48437e79f979"),
    "timer": (DONOR / "capid-init-portability/init-callback-entry-contract/README.md",
              "7b715aa5949d8958ec3d05a757309231ed57b71f98b30bab6d8ba732370ea823"),
    "u16": (DONOR / "capid-init-portability/init-u16-contract/README.md",
            "337b1dd21dc0606cf1af6ba82ae28a6eabb48297d40ac56948c1c2d17af63d28"),
}

# Only original instructions on the two relevant producer→queue→consumer paths.
POINTS = {
    "fx3_mpr": {
        "write_stack": [0xcb488, 0xcb490, 0xcb494, 0xcb49c, 0xcb4a4, 0xcb4a8, 0xcb4b0, 0xcb4b4, 0xcb4b8],
        "auto_stack": [0xcb920, 0xcb924, 0xcb928, 0xcb930, 0xcb938, 0xcb93c, 0xcb940, 0xcb944],
        "set_event_heap": [0xb4168, 0xb416c, 0xb3f70, 0xb3f7c, 0xb3f80, 0xb3f84, 0xb3f88, 0xb3f8c, 0xb3fc0, 0xb3fc4],
        "callback_and_free": [0xb4440, 0xb4654, 0xb4664, 0xb4668, 0xb4670, 0xb4674, 0xb46d8, 0xb46e8, 0xb46ec, 0xb46f4, 0xb46f8, 0xb4488, 0xb4494],
    },
    "fx6_mpr": {
        "write_stack": [0x1450f8, 0x145100, 0x145114, 0x145120, 0x145124, 0x14512c, 0x145130, 0x145144, 0x145150, 0x145154, 0x145168, 0x14516c, 0x145174, 0x145178],
        "auto_stack": [0x1455c0, 0x1455c8, 0x1455dc, 0x1455e8, 0x1455f8, 0x1455fc, 0x145618, 0x14561c, 0x145628, 0x14562c, 0x145638, 0x14563c],
        "set_event_heap": [0x128994, 0x128998, 0x12879c, 0x1287a8, 0x1287ac, 0x1287b0, 0x1287b4, 0x1287b8],
    },
    "fx6_ap": {
        "write_consumer": [0x213caa0, 0x213caac, 0x213caec, 0x213caf8, 0x213cabc, 0x213cb00, 0x213cb20, 0x213cb24, 0x213cb30],
        "auto_consumer": [0x212da18, 0x212da1c, 0x212da54, 0x212da5c, 0x212da60, 0x212da84, 0x212da88, 0x212da94],
    },
}
EXPECTED = {
    ("fx3_mpr", 0xcb4b4): "d2800402",  # 32B SetIssueEvent source length
    ("fx3_mpr", 0xcb93c): "d2800402",
    ("fx3_mpr", 0xb3f7c): "97ff3689",  # malloc(x3)
    ("fx3_mpr", 0xb3f8c): "97ff1e91",  # memcpy(p,source,x3)
    ("fx6_mpr", 0x1450f8): "d280f118",  # 0x788
    ("fx6_mpr", 0x1455c0): "d280f018",  # 0x780
    ("fx6_mpr", 0x1287a8): "97ff1f56",  # malloc(x3)
    ("fx6_ap", 0x213caa0): "395dc263",  # [x19+0x770] u8
    ("fx6_ap", 0x213caec): "f943be60",  # [x19+0x778] u64
    ("fx6_ap", 0x212da18): "395db003",  # [x0+0x76c] u8
    ("fx6_ap", 0x212da54): "f943ba82",  # [x20+0x770] u64
}
RELOCS = {
    "fx3_mpr": {"0x2f9980": "_ZN3mpr28gp_evtMovieWriteFinishedFuncE",
                 "0x2f9750": "_ZN3mpr29gp_evtMovieRecAutoDividedFuncE"},
    "fx6_mpr": {"0x108e460": "_ZN3mpr28gp_evtMovieWriteFinishedFuncE",
                 "0x108bfb8": "_ZN3mpr29gp_evtMovieRecAutoDividedFuncE"},
}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def file_offset(blob: bytes, va: int) -> int:
    if blob[:4] != b"\x7fELF" or blob[4] != 2 or blob[5] != 1 or struct.unpack_from("<H", blob, 18)[0] != 183:
        raise ValueError("expected original ELF64 LE AArch64")
    phoff = struct.unpack_from("<Q", blob, 32)[0]
    phentsize, phnum = struct.unpack_from("<HH", blob, 54)
    for i in range(phnum):
        off = phoff + i * phentsize
        typ, file_start, virtual, file_size = struct.unpack_from("<I4xQQ8xQ", blob, off)
        if typ == 1 and virtual <= va and va + 4 <= virtual + file_size:
            return file_start + va - virtual
    raise ValueError(f"VA 0x{va:x} absent from PT_LOAD filesz")


def instruction(path: Path, blob: bytes, va: int) -> dict:
    off = file_offset(blob, va)
    word = f"{int.from_bytes(blob[off:off + 4], 'little'):08x}"
    lines = subprocess.check_output(["objdump", "-d", f"--start-address=0x{va:x}",
                                     f"--stop-address=0x{va+4:x}", str(path)], text=True).splitlines()
    found = [m for line in lines if (m := re.match(r"\s*([0-9a-f]+):\s+([0-9a-f]{8})\s+(.+)", line))]
    if len(found) != 1 or int(found[0].group(1), 16) != va or found[0].group(2) != word:
        raise ValueError(f"objdump/raw mismatch at 0x{va:x}")
    return {"va": f"0x{va:x}", "fileoff": f"0x{off:x}", "word_le": word,
            "disassembly": found[0].group(3).strip()}


def main():
    out = {"scope": "host_static_original_bytes_plus_prior_vm_receipt", "inputs": {}, "prior_contracts": {}, "edges": {}, "run": {}}
    for name, (path, expected) in PRIOR_CONTRACTS.items():
        actual = digest(path)
        if actual != expected:
            raise ValueError(f"prior contract {name} SHA drift")
        out["prior_contracts"][name] = {"path": str(path), "sha256": actual}
    for name, (path, expected) in SOURCES.items():
        sha = digest(path)
        if sha != expected:
            raise ValueError(f"{name} SHA drift: {sha}")
        out["inputs"][name] = {"path": str(path), "sha256": sha, "size": path.stat().st_size}
        blob = path.read_bytes()
        out["edges"][name] = {}
        for edge, vas in POINTS[name].items():
            rows = [instruction(path, blob, va) for va in vas]
            for row in rows:
                expected_word = EXPECTED.get((name, int(row["va"], 16)))
                if expected_word and row["word_le"] != expected_word:
                    raise ValueError(f"original word drift {name} {row['va']}")
            out["edges"][name][edge] = rows
        if name in RELOCS:
            reloc_text = subprocess.check_output(["objdump", "-R", str(path)], text=True)
            out["edges"][name]["callback_relocations"] = {}
            for addr, symbol in RELOCS[name].items():
                pattern = rf"(?m)^0*{int(addr,16):x}\s+R_AARCH64_GLOB_DAT\s+{re.escape(symbol)}\s*$"
                match = re.search(pattern, reloc_text)
                if not match:
                    raise ValueError(f"missing original callback relocation {name} {addr}")
                out["edges"][name]["callback_relocations"][addr] = symbol
    for name, expected in RUN_SHA.items():
        actual = digest(RUN / name)
        if actual != expected:
            raise ValueError(f"run {name} SHA drift")
        out["run"][name] = actual
    receipt = json.loads((RUN / "receipt.json").read_text())
    obs = json.loads((RUN / "mpr-observation.json").read_text())
    call, ret = [r for r in obs["records"] if r["kind"] in ("call", "return")]
    assert receipt["stop"] == "mpr_same_call_return_captured" and receipt["qemu_reaped"]
    assert receipt["cleanup"]["API16_restored"] and receipt["breakpoint_cleanup"]["all_removed"]
    assert receipt["inputs_unchanged"] and all(lock["free"] for lock in receipt["locks"])
    assert call["tls"] == ret["tls"] and call["fp"] == ret["fp"]
    assert call["parameter_0x290_sha256"] == hashlib.sha256(bytes.fromhex(call["parameter_0x290_hex"])).hexdigest()
    assert ret["return_w0_signed32"] == 3 and ret["mpr_identity_after"]
    out["run"]["observed"] = {"call_pc": call["pc"], "return_pc": ret["pc"],
                               "call_record_sha256": call["parameter_0x290_sha256"],
                               "got_before": call["got_before"], "got_after": ret["got_after"],
                               "mpr_bias": ret["mpr_identity_after"]["identity"]["bias"],
                               "w0": ret["return_w0_signed32"],
                               "mpr_entry_observed": ret["mpr_entry_observed"],
                               "capid_breakpoint_armed": ret["capid_breakpoint_armed"]}
    (HERE / "evidence.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print("PASS_PINNED_HOST_STATIC", sum(len(v) for d in POINTS.values() for v in d.values()), "original instructions")


if __name__ == "__main__":
    main()
