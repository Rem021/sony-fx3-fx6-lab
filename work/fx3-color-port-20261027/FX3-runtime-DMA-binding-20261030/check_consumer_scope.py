#!/usr/bin/env python3
"""Separate original kernel-module linkage from same-name userspace references."""
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
    assert not (BASE / "consumer-scope.json").exists()
    binding = json.loads((BASE / "original-binding.json").read_bytes())
    selected = json.loads((BASE / "selected-consumers.json").read_bytes())
    cs = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
    module_views = []
    for item in selected["modules"]:
        path = BASE / item["local_path"]
        data = path.read_bytes()
        assert sha(data) == item["sha256"]
        elf = ELFFile(io.BytesIO(data))
        if item["path"].endswith(".so"):
            dynamic = elf.get_section_by_name(".dynamic")
            module_views.append({"path": item["path"], "ELF_type": "ET_DYN", "needed": [entry.needed for entry in dynamic.iter_tags() if entry.entry.d_tag == "DT_NEEDED"],
                "kernel_binding_proved": False, "scope": "This is an unresolved userspace ELF reference; matching a kernel export name does not resolve its loader scope."})
            continue
        imported = next(row for row in binding["importing_ELFs"] if row["path"] == item["path"])
        text = elf.get_section_by_name(".text")
        windows = []
        intervals = [(0, text["sh_size"], "complete .text, local function names stripped")] if item["path"].endswith("cachecontrol.ko") else [(0x41C0, 0x4290, "bounded unnamed context for two noncache conversions")]
        for start, end, scope in intervals:
            assert 0 <= start < end <= text["sh_size"]
            raw = text.data()[start:end]
            decoded = []
            for instruction in cs.disasm(raw, start):
                row = {"offset": hex(instruction.address), "bytes": instruction.bytes.hex(), "instruction": instruction.mnemonic + " " + instruction.op_str}
                row["original_import_relocations"] = [{"symbol": rel["symbol"], "type": rel["type"]} for rel in imported["relocations"] if rel.get("target_section") == ".text" and int(rel["offset"], 0) == instruction.address]
                decoded.append(row)
            windows.append({"start": hex(start), "end_exclusive": hex(end), "raw_sha256": sha(raw), "scope": scope, "disassembly": decoded})
        module_views.append({"path": item["path"], "sha256": item["sha256"], "ELF_type": "ET_REL", "windows": windows,
            "kernel_imports_match_export_names": True, "actual_loaded_module_proved": False})
    helper = FSROOT / "read_filesystems.py"
    assert sha(helper.read_bytes()) == binding["filesystem_reader_sha256"]
    sys.path.insert(0, str(FSROOT))
    from read_filesystems import Ext2
    definitions = []
    image_counts = []
    targets = set(binding["target_symbols"])
    for record in binding["scanned_images"]:
        image = FSROOT / ("nflasha" + str(record["partition"]) + ".img")
        assert sha(image.read_bytes()) == record["image_sha256"]
        fs = Ext2(image)
        count = 0
        for entry in fs.walk():
            if entry["type"] != 0x8000:
                continue
            data = fs.data(entry["inode"])
            if data[:4] != b"\x7fELF":
                continue
            elf = ELFFile(io.BytesIO(data))
            if elf.header["e_machine"] != "EM_AARCH64":
                continue
            count += 1
            dynamic = elf.get_section_by_name(".dynsym")
            if dynamic is None:
                continue
            for symbol in dynamic.iter_symbols():
                if symbol.name not in targets or symbol["st_shndx"] == "SHN_UNDEF":
                    continue
                section = elf.get_section(symbol["st_shndx"]) if isinstance(symbol["st_shndx"], int) else None
                definitions.append({"partition": record["partition"], "path": entry["path"], "sha256": sha(data), "ELF_type": elf.header["e_type"],
                    "symbol": symbol.name, "value": hex(symbol["st_value"]), "type": symbol["st_info"]["type"], "binding": symbol["st_info"]["bind"],
                    "section": section.name if section else symbol["st_shndx"], "executable_section": bool(section and section["sh_flags"] & 4)})
        assert count == record["A64_ELF_files_scanned"]
        image_counts.append({"partition": record["partition"], "A64_ELFs": count})
    result = {"created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "module_views": module_views,
        "dynamic_definitions_for_same_names": definitions, "images_scanned": image_counts,
        "importing_kernel_modules": sum(row["ELF_type"] == "ET_REL" for row in binding["importing_ELFs"]),
        "unresolved_shared_library_references": sum(row["ELF_type"] == "ET_DYN" for row in binding["importing_ELFs"]),
        "DMM_log_scope": "Eleven arch_phys_to_cache relocations are in named dmm_log_CreateArea, not evidence of RAW pixel allocation. Two noncache calls have no preserved enclosing function symbol.",
        "scope": "Original static linkage and bounded contexts, no loader resolution or hardware execution.", "device_actions": 0, "goal_complete": False}
    (BASE / "consumer-scope.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"importing_kernel_modules": result["importing_kernel_modules"], "unresolved_shared_library_references": result["unresolved_shared_library_references"],
        "dynamic_definitions": definitions}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
