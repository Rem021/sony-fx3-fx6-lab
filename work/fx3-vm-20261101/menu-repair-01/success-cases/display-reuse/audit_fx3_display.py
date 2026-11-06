#!/usr/bin/env python3
"""Read-only original ELF audit; outputs only beside this script, never executes ELF."""
from pathlib import Path
from io import BytesIO
import datetime
import hashlib
import json
import plistlib
import re
import subprocess
from elftools.elf.elffile import ELFFile
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
MANIFEST = ROOT / "original-uipc/ap-projection/projection-manifest-v3.json"
SOURCE = ROOT / "success-cases/source"
COMMIT = "b3d7c1fed349f1d918acc4259f1d2b3a7c52a500"
UUID = "F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B"
assert plistlib.loads(subprocess.check_output(
    ["diskutil", "info", "-plist", "/Volumes/KAFU2T"]))["VolumeUUID"] == UUID
manifest = json.loads(MANIFEST.read_text())
cs = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
observer = (SOURCE / "runtime/analysis/menu-observe.c").read_text()
exact = set(re.findall(r'"(_Z[^"\n]+)"', observer))
keys = ("notifyDraw", "drawFramebuffer", "Bitmap", "bitmap", "FrameBuffer",
        "Framebuffer", "framebuffer", "Gperm", "mpgpe", "Lz77", "LZ77",
        "lz77", "GRM_", "grm_", "BMP_", "osal_", "OSD", "uxengine_",
        "DataflowInfraPin4Send", "SetEntry_OsdImageSize", "InfraInput",
        "GraphicsImage", "processEvent", "Application_System_Init")

def sha(data):
    return hashlib.sha256(data).hexdigest()

class Image:
    def __init__(self, guest):
        self.row = next(r for r in manifest["members"] if r["guest_path"] == guest)
        self.data = Path(self.row["local_file"]).read_bytes()
        assert sha(self.data) == self.row["sha256"]
        self.elf = ELFFile(BytesIO(self.data))
        self.symbols = list(self.elf.get_section_by_name(".dynsym").iter_symbols())
        self.exports = {s.name: s for s in self.symbols if s["st_shndx"] != "SHN_UNDEF"}
        self.plt = {}
        rela = self.elf.get_section_by_name(".rela.plt")
        if rela:
            sym = self.elf.get_section(rela["sh_link"])
            plt = self.elf.get_section_by_name(".plt")
            self.plt = {plt["sh_addr"] + 32 + n * 16:
                        sym.get_symbol(r["r_info_sym"]).name
                        for n, r in enumerate(rela.iter_relocations())}

    def read(self, address, length):
        for segment in self.elf.iter_segments():
            if (segment["p_type"] == "PT_LOAD" and
                segment["p_vaddr"] <= address and
                address + length <= segment["p_vaddr"] + segment["p_filesz"]):
                start = segment["p_offset"] + address - segment["p_vaddr"]
                return self.data[start:start + length]
        raise ValueError(hex(address))

    def dis(self, address, length):
        result = []
        for i in cs.disasm(self.read(address, length), address):
            row = {"va": hex(i.address), "bytes": bytes(i.bytes).hex(),
                   "instruction": i.mnemonic + " " + i.op_str}
            if i.mnemonic in ("bl", "b") and i.op_str.startswith("#"):
                target = int(i.op_str[1:], 0)
                row["target"] = hex(target)
                if target in self.plt:
                    row["plt_symbol"] = self.plt[target]
            result.append(row)
        return result

    def proof(self):
        sym = [{"name": s.name, "value": hex(s["st_value"]),
                "size": s["st_size"], "defined": s["st_shndx"] != "SHN_UNDEF",
                "type": s["st_info"]["type"], "bind": s["st_info"]["bind"]}
               for s in self.symbols if s.name in exact or any(k in s.name for k in keys)]
        relocations = []
        for section in self.elf.iter_sections():
            if section["sh_type"] != "SHT_RELA":
                continue
            syms = self.elf.get_section(section["sh_link"])
            for r in section.iter_relocations():
                name = syms.get_symbol(r["r_info_sym"]).name
                if name in exact or any(k in name for k in keys):
                    relocations.append({"section": section.name,
                                        "offset": hex(r["r_offset"]),
                                        "type": r["r_info_type"],
                                        "addend": r["r_addend"], "symbol": name})
        return {"guest_path": self.row["guest_path"],
                "local_file": self.row["local_file"], "bytes": len(self.data),
                "sha256": sha(self.data), "selected_dynsym": sym,
                "selected_relocations": relocations}

images = {g: Image(g) for g in ("/usr/lib/libObj.so", "/usr/lib/libgpe.so",
                               "/usr/lib/appFw.so", "/usr/lib/libosal_uipc.so")}
obj = images["/usr/lib/libObj.so"]
functions = {}
for name, symbol in obj.exports.items():
    if name.startswith(("GRM_", "BMP_")) or any(
        k in name for k in ("notifyDraw", "drawFramebuffer", "sys_getInstance",
                            "FramebufferWidth", "FramebufferHeight")):
        address, length = symbol["st_value"], symbol["st_size"]
        if 0 < length <= 1200:
            functions[name] = obj.dis(address, length)

# These are FX3 branch targets recovered from its own exported wrappers, not
# copied A7C2 ABI addresses. They are disassembly evidence, not runtime hooks.
internal_blocks = {
    "framebuffer_manager_getter": (0xf2ab8, 0x40),
    "current_bitmap_getter": (0xf2d58, 8),
    "manager_lock_swap": (0xf2e34, 8),
    "manager_unlock_swap": (0xf2e64, 12),
    "framebuffer_current_bitmap": (0xf3368, 24),
    "framebuffer_lock_swap": (0xf3380, 40),
    "framebuffer_unlock_swap": (0xf33a8, 40),
    "framebuffer_swap": (0xf33d0, 52),
    "semaphore_lock_infinite": (0xfd344, 64),
    "semaphore_unlock": (0xfd384, 60),
    "bitmap_size_wrapper": (0xeec14, 92),
    "bitmap_physical_wrapper": (0xeecf8, 68),
    "bitmap_read_lock_wrapper": (0xeed80, 56),
    "bitmap_read_unlock_wrapper": (0xeedb8, 68),
    "bitmap_addref_candidate_wrapper": (0xeee78, 68),
    "bitmap_release_wrapper": (0xeeebc, 92),
    "grm_status_translation": (0xfb16c, 8),
    "ap_meta_message_allocate_and_tag": (0xf1d04, 0x8c),
    "ap_control_message_allocate_and_tag": (0xf1d90, 0x8c),
    "ap_pixels_message_allocate_and_tag": (0xf1e1c, 0x8c),
    "ap_osd_completion_receiver_candidate": (0xf29c0, 0xf8),
    "lz77_decoder_decodeImpl": (0x154c40, 0x2d8),
    "graphicsimage_write_lock_adapter": (0x12b414, 0x24),
}

# Derive the hidden Lz77Decoder vtable through its original RTTI string and
# relocation graph. This does not rely on the A7C2 decoder address/slot.
relatives = [r for section in obj.elf.iter_sections()
             if section["sh_type"] == "SHT_RELA"
             for r in section.iter_relocations() if r["r_info_type"] == 1027]
lz_name_offset = obj.data.index(b"N2ux4core11Lz77DecoderE\0")
lz_name_va = next(s["p_vaddr"] + lz_name_offset - s["p_offset"]
                  for s in obj.elf.iter_segments() if s["p_type"] == "PT_LOAD"
                  and s["p_offset"] <= lz_name_offset < s["p_offset"] + s["p_filesz"])
lz_rtti_graph = []
for name_relocation in relatives:
    if name_relocation["r_addend"] != lz_name_va:
        continue
    typeinfo = name_relocation["r_offset"] - 8
    for table_relocation in relatives:
        if table_relocation["r_addend"] != typeinfo:
            continue
        address_point = table_relocation["r_offset"] + 8
        slots = [{"slot_va": hex(r["r_offset"]), "target_va": hex(r["r_addend"])}
                 for r in relatives if address_point <= r["r_offset"] < address_point + 32]
        lz_rtti_graph.append({"typename": "N2ux4core11Lz77DecoderE",
                              "typename_va": hex(lz_name_va), "typeinfo_va": hex(typeinfo),
                              "vtable_address_point_va": hex(address_point), "first_four_slots": slots})

# Exact literals and short MOV/MOVK chains are locations, not service-role proof.
wanted = {0x8280074d, 0x8280084d, 0x8280084e, 0x8288076c,
          0x9088076b, 0x02886047, 0x02886044, 0x005503e0,
          0x807a0020, 0x92840747}
constant_sites = []
for guest, img in images.items():
    for value in sorted(wanted):
        raw = value.to_bytes(4, "little")
        start = 0
        while (start := img.data.find(raw, start)) >= 0:
            constant_sites.append({"guest_path": guest, "kind": "literal_bytes",
                                   "file_offset": hex(start), "value": hex(value)})
            start += 1
    if guest not in ("/usr/lib/libObj.so", "/usr/lib/libgpe.so"):
        continue
    text = img.elf.get_section_by_name(".text")
    recent = []
    for ins in cs.disasm(text.data(), text["sh_addr"]):
        recent = [r for r in recent if ins.address - r[0] <= 20]
        match = re.fullmatch(r"([wx]\d+), #(-?0x[0-9a-f]+|-?\d+)", ins.op_str)
        if ins.mnemonic == "mov" and match:
            recent.append((ins.address, match[1], int(match[2], 0)))
        match = re.fullmatch(r"([wx]\d+), #(0x[0-9a-f]+|\d+), lsl #(16|32|48)", ins.op_str)
        if ins.mnemonic == "movk" and match:
            register, part, shift = match[1], int(match[2], 0), int(match[3])
            for origin, reg, old in reversed(recent):
                if reg != register:
                    continue
                width = 32 if reg.startswith("w") else 64
                value = ((old & ~(0xffff << shift)) | (part << shift)) & ((1 << width) - 1)
                if value in wanted:
                    constant_sites.append({"guest_path": guest, "kind": "short_mov_chain_candidate",
                                           "origin_va": hex(origin), "va": hex(ins.address),
                                           "register": reg, "value": hex(value),
                                           "instructions": img.dis(origin, ins.address - origin + 4),
                                           "limit": "No data-flow or receiver role assertion"})
                break

plain_strings = []
for match in re.finditer(rb"[\x20-\x7e]{5,}\x00", obj.data):
    text = match.group()[:-1].decode("ascii")
    if any(k.lower() in text.lower() for k in ("Lz77Decoder", "Bitmap", "Framebuffer", "GRM_fbrm")):
        plain_strings.append({"file_offset": hex(match.start()), "text": text})

case_paths = ("docs/tech/05-display.md", "docs/tech/06-input.md",
              "runtime/analysis/menu-observe.c", "runtime/analysis/headless-osd.c",
              "runtime/analysis/headless-osd-export.c", "runtime/analysis/ramfb-viewer.c",
              "runtime/analysis/inject-key.c", "runtime/analysis/gpe-raster.c",
              "runtime/analysis/gpe-sprite.c", "runtime/analysis/sony-lz77.c")
result = {
    "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "status": "STATIC_ORIGINAL_FX3_INTERFACES_ONLY_NOT_RUNTIME_ACCEPTANCE",
    "volume_uuid": UUID,
    "source_manifest": str(MANIFEST), "source_manifest_sha256": sha(MANIFEST.read_bytes()),
    "successful_case": {"repository": "https://github.com/chocotan/a7c2-qemu",
                        "commit": COMMIT,
                        "files": [{"path": p, "sha256": sha((SOURCE / p).read_bytes()),
                                   "canonical_url": f"https://github.com/chocotan/a7c2-qemu/blob/{COMMIT}/{p}"}
                                  for p in case_paths]},
    "original_files": [img.proof() for img in images.values()],
    "original_exported_functions": functions,
    "original_internal_branch_target_evidence": {
        name: obj.dis(address, length) for name, (address, length) in internal_blocks.items()},
    "lz77_original_rtti_relocation_graph": lz_rtti_graph,
    "gpe_exported_function_evidence": {
        name: images["/usr/lib/libgpe.so"].dis(s["st_value"], s["st_size"])
        for name, s in images["/usr/lib/libgpe.so"].exports.items()
        if name in exact and 0 < s["st_size"] <= 1200},
    "searched_case_constant_values": [hex(v) for v in sorted(wanted)],
    "constant_sites_not_role_proof": constant_sites,
    "libObj_selected_plain_strings": plain_strings,
    "limits": ["No original Sony ELF, QEMU, guest, or updater executed by this audit.",
               "Matching symbol names do not establish parameter-block, pixel-format or queue semantics.",
               "Public GRM wrappers may block indefinitely or assert; none invoked here.",
               "A7C2 private addresses, framebuffer fields, LZ decoder vtable and key table cannot be copied."]}
(OUT / "fx3-display-static-proof.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"files": len(images), "function_blocks": len(functions),
                  "private_evidence_blocks": len(internal_blocks),
                  "case_constant_sites_not_role_proof": len(constant_sites),
                  "selected_strings": len(plain_strings), "output": str(OUT / "fx3-display-static-proof.json")}))
