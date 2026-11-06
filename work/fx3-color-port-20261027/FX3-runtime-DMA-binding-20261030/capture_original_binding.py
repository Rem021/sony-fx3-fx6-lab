#!/usr/bin/env python3
"""Read original package kernel/ELF linkage; no vendor execution or device operations."""
import sys
sys.dont_write_bytecode = True
import datetime
import hashlib
import io
import json
import pathlib
import plistlib
import re
import struct
import subprocess
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN
from elftools.elf.elffile import ELFFile
from elftools.elf.descriptions import describe_reloc_type

BASE = pathlib.Path(__file__).resolve().parent
ROOT = pathlib.Path("/Volumes/KAFU2T/AI/Projects/Mac")
FSROOT = ROOT / "work/sony-firmware-20261024/stage2/extraction"
CATALOG = ROOT / "work/sony-firmware-20261024/stage146-original-kernel-symbol-and-vendor-route/work/kernel-symbol-catalog.json"
KBASE = 0xFFFFFF8008080000
TARGETS = {"__udif_cache_ctrl", "udif_dma_map_sg", "udif_dma_unmap_sg", "__dma_map_area", "__dma_unmap_area", "__dma_inv_area", "__dma_clean_area",
    "arch_phys_to_va", "arch_va_to_phys", "arch_phys_to_noncache", "arch_phys_to_cache", "arch_phys_to_cachetype2", "arch_p64_to_p32", "arch_p32_to_p64"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def nul(data, offset):
    assert 0 <= offset < len(data)
    end = data.index(b"\0", offset, offset + 512)
    return data[offset:end].decode("ascii")


def main():
    volume = plistlib.loads(subprocess.check_output(["diskutil", "info", "-plist", "/Volumes/KAFU2T"]))
    assert volume["VolumeUUID"] == "F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B"
    assert not (BASE / "original-binding.json").exists()
    helper = FSROOT / "read_filesystems.py"
    assert sha(helper.read_bytes()) == "eecbe9b099f9fbc8f8e06759c5e8a2ce9910e0f365ae9891fe0887353edc31ad"
    sys.path.insert(0, str(FSROOT))
    from read_filesystems import Ext2, FAT16
    catalog_raw = CATALOG.read_bytes()
    assert sha(catalog_raw) == "b37c6b7d4315f65234cd6b64c3be4a3d7c6e0d2cca66204e27cb5c575000a51e"
    symbols = json.loads(catalog_raw)
    assert len(symbols) == 41269
    image = FSROOT / "nflasha3.img"
    assert sha(image.read_bytes()) == "ca5a8c80a1883c4a72c2f40018e3d40ab43e28ff0bf6a1d89f17d0680c607568"
    fat = FAT16(image)
    entry = next(item for item in fat.walk() if item["path"] == "/vmlinux.bin")
    kernel = fat.data(entry["cluster"], entry["size"])
    assert len(kernel) == 6610952 and sha(kernel) == "da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c"
    originals = BASE / "original-fragments"
    originals.mkdir(exist_ok=False)
    cs = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
    functions = []
    for name in sorted(TARGETS):
        selected = [item for item in symbols if item["name"] == name]
        assert len(selected) == 1
        item = selected[0]
        start = item["file_offset"]
        assert KBASE + start == item["address"]
        end = min(candidate["file_offset"] for candidate in symbols if candidate["file_offset"] > start)
        assert 0 < end - start < 4096
        data = kernel[start:end]
        path = originals / (name + ".bin")
        path.write_bytes(data)
        decoded = [{"VA": hex(instruction.address), "file_offset": hex(instruction.address - KBASE), "bytes": instruction.bytes.hex(),
            "instruction": instruction.mnemonic + " " + instruction.op_str} for instruction in cs.disasm(data, item["address"])]
        export = [candidate for candidate in symbols if candidate["name"] == "__ksymtab_" + name]
        export_record = None
        if export:
            assert len(export) == 1
            at = export[0]["file_offset"]
            value, name_pointer = struct.unpack_from("<QQ", kernel, at)
            decoded_name = nul(kernel, name_pointer - KBASE)
            assert value == item["address"] and decoded_name == name
            export_record = {"file_offset": hex(at), "raw16": kernel[at:at + 16].hex(), "value": hex(value), "name_pointer": hex(name_pointer), "name": decoded_name}
        functions.append({"name": name, "file_offset": hex(start), "VA": hex(item["address"]), "span_bytes": end - start,
            "boundary_scope": "Next distinct recovered symbol; may include padding/literals. Disassembly is an initial linear view, not a whole-function control-flow proof.",
            "fragment": path.relative_to(BASE).as_posix(), "fragment_sha256": sha(data), "initial_linear_disassembly": decoded,
            "decoded_bytes": sum(len(bytes.fromhex(instruction["bytes"])) for instruction in decoded), "independent_export_record": export_record})
    imports = []
    counts = []
    for partition, expected in [(15, "df0a2cf2ebb0d884605d041a6dcb701092bd36848956855b8d3d7a7164a3a1c5"), (7, "ceca23d253350e65df9c7c976f06e545ad41a2d8f272d28fc1e73fcc576ddba7")]:
        path = FSROOT / ("nflasha" + str(partition) + ".img")
        assert sha(path.read_bytes()) == expected
        fs = Ext2(path)
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
            undefined = set()
            for section in elf.iter_sections():
                if section["sh_type"] in ("SHT_SYMTAB", "SHT_DYNSYM"):
                    undefined.update(symbol.name for symbol in section.iter_symbols() if symbol["st_shndx"] == "SHN_UNDEF" and symbol.name in TARGETS)
            if not undefined:
                continue
            relocations = []
            for section in elf.iter_sections():
                if section["sh_type"] not in ("SHT_RELA", "SHT_REL"):
                    continue
                table = elf.get_section(section["sh_link"])
                for relocation in section.iter_relocations():
                    symbol = table.get_symbol(relocation["r_info_sym"])
                    if symbol.name not in undefined:
                        continue
                    row = {"section": section.name, "offset": hex(relocation["r_offset"]), "symbol": symbol.name,
                        "type": describe_reloc_type(relocation["r_info_type"], elf), "type_number": relocation["r_info_type"],
                        "addend": relocation.entry.get("r_addend")}
                    if elf.header["e_type"] == "ET_REL" and section["sh_info"]:
                        target = elf.get_section(section["sh_info"])
                        offset = relocation["r_offset"]
                        row["target_section"] = target.name
                        if 0 <= offset < target["sh_size"]:
                            start, end = max(0, offset - 24), min(target["sh_size"], offset + 16)
                            raw = target.data()[start:end]
                            row["context_offset"] = hex(start)
                            row["context_raw"] = raw.hex()
                            row["initial_context_disassembly"] = [{"offset": hex(ins.address), "bytes": ins.bytes.hex(), "instruction": ins.mnemonic + " " + ins.op_str} for ins in cs.disasm(raw, start)]
                            row["enclosing_functions"] = [candidate.name for candidate in table.iter_symbols() if candidate["st_info"]["type"] == "STT_FUNC" and candidate["st_shndx"] == section["sh_info"] and candidate["st_value"] <= offset < candidate["st_value"] + candidate["st_size"]]
                    relocations.append(row)
            modinfo = elf.get_section_by_name(".modinfo")
            vermagic = [value.decode("ascii", "replace") for value in modinfo.data().split(b"\0") if value.startswith(b"vermagic=")] if modinfo else []
            versions = elf.get_section_by_name("__versions")
            imports.append({"partition": partition, "path": entry["path"], "bytes": len(data), "sha256": sha(data), "ELF_type": elf.header["e_type"],
                "target_undefined_symbols": sorted(undefined), "relocations": relocations, "vermagic": vermagic,
                "module_versions_section_bytes": versions["sh_size"] if versions else None,
                "scope": "Packaged ELF imports and relocations only; does not prove module load or actual runtime symbol resolution."})
        counts.append({"partition": partition, "image_sha256": expected, "A64_ELF_files_scanned": count})
    result = {"created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "kernel": {"image": str(image), "path": "/vmlinux.bin", "bytes": len(kernel), "sha256": sha(kernel),
            "linux_version_matches": [match.group(0).decode("ascii", "replace") for match in re.finditer(rb"Linux version [0-9.]+", kernel)],
            "VA_base": hex(KBASE), "VA_scope": "Original link-time navigation, not observed runtime/KASLR state."},
        "symbol_catalog": {"path": str(CATALOG), "sha256": sha(catalog_raw), "symbols": len(symbols), "reused_read_only": True},
        "filesystem_reader_sha256": sha(helper.read_bytes()), "functions": functions, "scanned_images": counts,
        "importing_ELFs": imports, "target_symbols": sorted(TARGETS),
        "vendor_native_code_executed": False, "device_actions": 0, "cache_or_MMU_operations_executed": 0,
        "modified_or_flashable_package_produced": False, "goal_complete": False}
    (BASE / "original-binding.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"kernel_versions": result["kernel"]["linux_version_matches"], "original_functions": len(functions),
        "independent_exports": sum(bool(item["independent_export_record"]) for item in functions), "ELF_counts": counts,
        "importers": [{"path": item["path"], "targets": item["target_undefined_symbols"], "relocations": len(item["relocations"])} for item in imports]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
