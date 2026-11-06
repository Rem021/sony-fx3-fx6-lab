#!/usr/bin/env python3
"""Capture explicit cache fallthrough and selected original module consumers."""
import sys
sys.dont_write_bytecode = True
import datetime
import hashlib
import io
import json
import pathlib
import plistlib
import subprocess
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN
from elftools.elf.elffile import ELFFile

BASE = pathlib.Path(__file__).resolve().parent
FSROOT = BASE.parents[1] / "sony-firmware-20261024/stage2/extraction"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    volume = plistlib.loads(subprocess.check_output(["diskutil", "info", "-plist", "/Volumes/KAFU2T"]))
    assert volume["VolumeUUID"] == "F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B"
    assert not (BASE / "selected-consumers.json").exists()
    binding = json.loads((BASE / "original-binding.json").read_bytes())
    helper = FSROOT / "read_filesystems.py"
    assert sha(helper.read_bytes()) == binding["filesystem_reader_sha256"]
    sys.path.insert(0, str(FSROOT))
    from read_filesystems import Ext2, FAT16
    image = FSROOT / "nflasha3.img"
    assert sha(image.read_bytes()) == "ca5a8c80a1883c4a72c2f40018e3d40ab43e28ff0bf6a1d89f17d0680c607568"
    fat = FAT16(image)
    item = next(row for row in fat.walk() if row["path"] == "/vmlinux.bin")
    kernel = fat.data(item["cluster"], item["size"])
    assert sha(kernel) == binding["kernel"]["sha256"]
    path = pathlib.Path(binding["symbol_catalog"]["path"])
    assert sha(path.read_bytes()) == binding["symbol_catalog"]["sha256"]
    symbols = json.loads(path.read_bytes())
    target = next(row for row in symbols if row["name"] == "__inval_cache_range")
    start = target["file_offset"]
    end = min(row["file_offset"] for row in symbols if row["file_offset"] > start)
    data = kernel[start:end]
    output = BASE / "original-fragments/__inval_cache_range.bin"
    if output.exists():
        assert output.read_bytes() == data
    else:
        output.write_bytes(data)
    cs = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
    extension = {"name": "__inval_cache_range", "VA": hex(target["address"]), "file_offset": hex(start), "span_bytes": len(data),
        "fragment": output.relative_to(BASE).as_posix(), "fragment_sha256": sha(data),
        "original_disassembly": [{"VA": hex(ins.address), "file_offset": hex(ins.address - target["address"] + start), "bytes": ins.bytes.hex(), "instruction": ins.mnemonic + " " + ins.op_str} for ins in cs.disasm(data, target["address"])],
        "reason": "Original __dma_inv_area falls through to this separately named symbol; initial guard stopped before it, not a helper failure or cache completion."}
    image = FSROOT / "nflasha15.img"
    assert sha(image.read_bytes()) == "df0a2cf2ebb0d884605d041a6dcb701092bd36848956855b8d3d7a7164a3a1c5"
    fs = Ext2(image)
    expected = {row["path"]: row for row in binding["importing_ELFs"] if row["path"] in {"/kmod/dmm.ko", "/kmod/cachecontrol.ko", "/lib/dataflowInfraFramework.so"}}
    output = BASE / "original-modules"
    output.mkdir(exist_ok=True)
    modules = []
    for entry in fs.walk():
        if entry["path"] not in expected:
            continue
        data = fs.data(entry["inode"])
        assert sha(data) == expected[entry["path"]]["sha256"]
        local = output / pathlib.PurePosixPath(entry["path"]).name
        if local.exists():
            assert local.read_bytes() == data
        else:
            local.write_bytes(data)
        elf = ELFFile(io.BytesIO(data))
        tables = [section for section in elf.iter_sections() if section["sh_type"] in ("SHT_SYMTAB", "SHT_DYNSYM")]
        named = []
        for table in tables:
            for symbol in table.iter_symbols():
                index = symbol["st_shndx"]
                if not isinstance(index, int) or not index or not symbol.name or symbol.name.startswith("$"):
                    continue
                section = elf.get_section(index)
                if not section["sh_flags"] & 4:
                    continue
                row = {"name": symbol.name, "section": section.name, "offset": hex(symbol["st_value"]),
                    "size": symbol["st_size"], "type": symbol["st_info"]["type"]}
                if row not in named:
                    named.append(row)
        modules.append({"path": entry["path"], "local_path": local.relative_to(BASE).as_posix(), "sha256": sha(data), "bytes": len(data),
            "ELF_type": elf.header["e_type"], "code_symbols": named,
            "symbol_table_names": [table.name for table in tables],
            "code_sections": [{"name": section.name, "bytes": section["sh_size"], "file_offset": hex(section["sh_offset"])} for section in elf.iter_sections() if section["sh_flags"] & 4],
            "modinfo": expected[entry["path"]]["vermagic"]})
    assert len(modules) == 3
    result = {"created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "cache_fallthrough": extension, "modules": modules,
        "native_source_or_binary_execution": False, "device_actions": 0}
    (BASE / "selected-consumers.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"fallthrough_bytes": len(bytes.fromhex(''.join(row['bytes'] for row in extension['original_disassembly']))),
        "modules": [{"path": row["path"], "bytes": row["bytes"], "ELF_type": row["ELF_type"], "code_symbols": len(row["code_symbols"])} for row in modules]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
