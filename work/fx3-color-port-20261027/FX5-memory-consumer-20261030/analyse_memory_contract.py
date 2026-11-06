#!/usr/bin/env python3
"""Static source/interval evidence only. No Sony instruction, MMU or cache execution."""
import datetime
import hashlib
import json
import pathlib
import plistlib
import re
import subprocess

BASE = pathlib.Path(__file__).resolve().parent
OLD = BASE.parents[1] / "sony-firmware-20261024/stage133-FX5-source-availability-and-portability"
FX5 = BASE / "sources/drivers/soc/cxd"
FX3 = BASE / "fx3-reference-sources-expanded/drivers/udif/mach-cxd900xx"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def sealed(stage, pin):
    manifest = stage / "final-receipt.json"
    assert sha(manifest.read_bytes()) == pin
    metadata = load(manifest)
    for item in metadata["files"]:
        data = (stage / item["path"]).read_bytes()
        assert sha(data) == item["sha256"] and len(data) == item["bytes"]
    return {"path": str(manifest), "sha256": pin, "members_verified": len(metadata["files"])}


def literal(path, text):
    data = path.read_bytes()
    lines = data.decode().splitlines()
    matches = [index + 1 for index, line in enumerate(lines) if text in line]
    assert matches, (str(path), text)
    return {"path": str(path.relative_to(BASE)), "sha256": sha(data), "literal": text, "lines": matches}


def p32_fx3(value):
    if 0 <= value < 0xFE000000:
        return 0x400000000 | value
    if 0xFE000000 <= value < 0xFF000000:
        return value
    return 0


def p32_fx5(value):
    return 0x200000000 | value


def p64_fx3(value):
    if 0x400000000 <= value < 0x4FE000000 or 0xFE000000 <= value < 0xFF000000:
        return value & 0xFFFFFFFF
    return 0xFFFFFFFF


def p64_fx5(value):
    if 0x200000000 <= value < 0x300000000:
        return value & 0xFFFFFFFF
    return 0xFFFFFFFF


def main():
    volume = plistlib.loads(subprocess.check_output(["diskutil", "info", "-plist", "/Volumes/KAFU2T"]))
    assert volume["VolumeUUID"] == "F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B"
    assert not (BASE / "memory-contract-evidence.json").exists()
    source_files = []
    for filename in ["source-capture.json", "translation-source-capture.json", "fx3-source-capture-expanded.json"]:
        source_files += load(BASE / filename)["selected_sources"]
    for model in load(BASE / "cache-abi-source-capture.json")["models"]:
        source_files += model["selected_sources"]
    for item in source_files:
        data = (BASE / item["path"]).read_bytes()
        assert len(data) == item["bytes"] and sha(data) == item["sha256"]
    assert len(source_files) == 44
    old_sources = load(OLD / "gpl-source-selection-receipt.json")
    old_members = {item["path"]: item for archive in old_sources["archives"] for item in archive["selected_regular_sources"]}
    dts_root = OLD / "gpl-selection/linux-kernel/arch/arm64/boot/dts/cxd"
    published_maps = []
    for name in ["memmap-3G.dtsi", "memmap-4G.dtsi", "memmap-6G.dtsi", "memmap-8G.dtsi", "cxd90xxx.dtsi", "cxd90201_set.dts"]:
        path = dts_root / name
        data = path.read_bytes()
        metadata = old_members[path.relative_to(OLD).as_posix()]
        assert len(data) == metadata["bytes"] and sha(data) == metadata["sha256"]
        if not name.startswith("memmap-"):
            continue
        cells = re.search(r"reg\s*=\s*<([^>]+)>", data.decode()).group(1).split()
        assert len(cells) == 4
        a, b, c, d = [int(value, 0) for value in cells]
        start, size = (a << 32) | b, (c << 32) | d
        published_maps.append({"source": str(path), "sha256": sha(data), "start": hex(start), "size": hex(size), "end_exclusive": hex(start + size)})
    previous_stage = BASE.parent / "AP-staging-record-routing-20261030"
    prior = [sealed(previous_stage, "6bd744f39317d8a8761f74e7a86093a460a46397ac6e236d33670e21bf767ff7"),
        sealed(BASE.parent / "Creators-public-catalog-20261030", "1c888a0f6e88482614b4fec4d9478903018646a9fbd0eaa6a0033295af758464")]
    defaults = load(previous_stage / "default-span-roundtrip.json")
    spans = [("AP primary declared capacity", int(defaults["source"], 0), int(defaults["source"], 0) + int(defaults["AP_declared_capacity"], 0), "AP default property"),
        ("CP escape transfer target", int(defaults["destination"], 0), int(defaults["destination"], 0) + int(defaults["length"], 0), "CP default property")]
    for item in defaults["rows"]:
        spans.append((item["path"], int(item["projected_AP_start"], 0), int(item["projected_AP_end_exclusive"], 0), "AP projected slot"))
        spans.append((item["path"], int(item["CP_start"], 0), int(item["CP_end_exclusive"], 0), "CP default slot"))
    span_results = []
    for label, start, end, role in spans:
        assert start < end
        sample = {"label": label, "role": role, "start": hex(start), "end_exclusive": hex(end), "bytes": end - start,
            "FX3_public_AP_dma32_start": hex(p64_fx3(start)), "FX5_public_AP_dma32_start": hex(p64_fx5(start)),
            "contained_in_FX5_published_primary_memory_map": [item["source"].split("/")[-1] for item in published_maps if int(item["start"], 0) <= start and end <= int(item["end_exclusive"], 0)]}
        assert p64_fx5(start) == p64_fx5(end - 1) == 0xFFFFFFFF
        assert not sample["contained_in_FX5_published_primary_memory_map"]
        assert not (0x600000000 <= start and end <= 0x7FE000000)
        if role.startswith("AP"):
            assert p64_fx3(start) != 0xFFFFFFFF and p64_fx3(end - 1) != 0xFFFFFFFF
            assert p32_fx3(p64_fx3(start)) == start
            assert p32_fx5(p64_fx3(start)) != start
        else:
            assert p64_fx3(start) == p64_fx3(end - 1) == 0xFFFFFFFF
        span_results.append(sample)
    assert len(span_results) == 20
    boundary_values = [0, 0x12000000, 0x132D8E00, 0xFDFFFFFF, 0xFE000000, 0xFE001000, 0xFEFFFFFF, 0xFF000000, 0xFFFFFFFF]
    boundary_results = [{"p32": hex(value), "FX3_public_helper_p64": hex(p32_fx3(value)), "FX5_public_helper_p64": hex(p32_fx5(value))} for value in boundary_values]
    assert p32_fx3(0xFE001000) == 0xFE001000 and p32_fx5(0xFE001000) == 0x2FE001000
    assert p64_fx3(0x4132D8E00) == 0x132D8E00 and p64_fx5(0x4132D8E00) == 0xFFFFFFFF
    facts = []
    targets = [
        (FX5 / "export/mach/dma32.h", ["0x200000000UL", "0x300000000UL", "return (uint32_t)p64", "return DMA32_P64(p32)"]),
        (FX3 / "include/mach/dma32.h", ["0x0FE000000U", "0x0FF000000U", "0x400000000UL", "return PHYS64_ERR"]),
        (FX5 / "adrs_conv.c", ["asm volatile(\"at s1e1r", "read_sysreg(par_el1)", "attr < 0 || ptmp != pa", "attr < 0 || is_cache(attr)", "arch_phys_to_cachetype2", "ret2 = arch_phys_to_cachetype(pe)"]),
        (FX5 / "export/mach/platform.h", ["DDR0_BASE\t\tUL(0x200000000)", "DDR1_BASE\t\tUL(0x600000000)"]),
        (BASE / "sources/arch/arm64/mm/mmu.c", ["rmem_arm_add(rmem->base, rmem->size, memtype)", '"arm,rmem"', "rmem_map_memblock(pgdp, start, end", 'for_each_node_by_type(np, "iomap")']),
        (BASE / "sources/drivers/of/fdt.c", ['"linux,usable-memory"', "early_init_dt_add_memory_arch(base, size)", "fdt_init_reserved_mem()"]),
        (FX5 / "udif/cache.c", ["UDIF_CACHE_INVALIDATE == dir", "dcache_inval_poc", "dcache_clean_poc"]),
        (FX3 / "cache.c", ["__dma_map_area"]),
        (FX5 / "udif/dma-mapping.c", ["sg_dma_address(sg) = sg_phys(sg)", "__dma_map_area", "__dma_unmap_area"]),
        (FX5 / "mmap.c", ["if (!cxd90xxx_mmap_debug)", "return 1;", "case 1: /* warning only */", "case 2: /* warning and error */"]),
    ]
    for path, terms in targets:
        facts += [literal(path, term) for term in terms]
    cache_header_3 = BASE / "fx3-cache-abi-sources/include/linux/udif/cache.h"
    cache_header_5 = BASE / "fx5-cache-abi-sources/include/linux/udif/cache.h"
    assert cache_header_3.read_bytes() == cache_header_5.read_bytes()
    for model in ("fx3", "fx5"):
        path = BASE / (model + "-cache-abi-sources/include/linux/dma-direction.h")
        for term in ["DMA_TO_DEVICE = 1", "DMA_FROM_DEVICE = 2", "DMA_NONE = 3"]:
            facts.append(literal(path, term))
    old_asm = BASE / "fx3-cache-abi-sources/arch/arm64/mm/cache.S"
    new_asm = BASE / "fx5-cache-abi-sources/arch/arm64/mm/cache.S"
    facts.append(literal(old_asm, "b.eq\t__dma_inv_area"))
    facts.append(literal(new_asm, "b\t__dma_clean_area"))
    result = {"created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": "PASS_STATIC_SOURCE_CONTRACT_NOT_RUNTIME_OR_FLASH",
        "source_files_verified": 44, "verified_prior_stages": prior,
        "public_memory_map_examples": published_maps, "source_facts": facts,
        "original_FX3_default_span_results": span_results, "DMA32_boundary_arithmetic": boundary_results,
        "arithmetic_scope": "Python evaluation of explicitly read source interval formulae, not execution of the original C/assembly or a physical address probe.",
        "cache_contract": {"UDIF_cache_header_byte_identical": True,
            "flags": {"FLUSH": 1, "INVALIDATE": 2, "NONE": 3},
            "public_FLUSH_route": {"FX3": "UDIF -> __dma_map_area -> __dma_clean_area(start,size)", "FX5": "UDIF -> dcache_clean_poc(start,end)"},
            "public_INVALIDATE_route": {"FX3": "UDIF -> __dma_map_area -> __dma_inv_area(start,size)", "FX5": "UDIF -> dcache_inval_poc(start,end)"},
            "NONE_scope": "The inspected UDIF wrappers reject null address/zero size only; NONE reaches the non-invalidate clean branch. Do not infer a no-op from the enum name.",
            "scatter_gather_map_difference": "FX3 __dma_map_area branches on DMA_FROM_DEVICE; FX5 __dma_map_area always cleans before DMA, while both unmap functions invalidate for non-TO_DEVICE. Different timing is not itself proof of a defect.",
            "v2p_scope": "AT S1E1R/PAR_EL1 translation and cache attributes are runtime inputs; no such instructions were executed.",
            "phys_to_va_scope": "arch_phys_to_va uses arithmetic __p2v without the reverse-translation/cache check imposed by arch_phys_to_cache/noncache.",
            "cachetype2_scope": "Checks first and last byte attributes only; this is not a proof every intervening page has one attribute.",
            "mmap_guard_scope": "debug defaults to 0 and immediately permits; debug=1 warns only. It is not an always-on uniform-cache validator."},
        "next_action_changed_by_evidence": "Preserve address domains and use target-specific conversion/cache APIs; do not share raw DMA values or replace low-level cache symbols by name. Bind these source contracts to the actual FX3 7.02 runtime and donor before implementing an adapter.",
        "physical_RAM_chip_size_or_RAW_pool_proved": False, "FX5_selected_runtime_DTB_proved": False,
        "actual_FX3_702_runtime_helper_binding": False, "complete_private_donor_obtained": False,
        "modified_or_flashable_package_produced": False, "goal_complete": False,
        "previous_goal_turn_classification": "progress: new anonymous public route with positive controls changed the next source-acquisition action; readiness was unchanged",
        "current_goal_turn_classification": "progress: new paired source consumers, address-domain rejection and cache protocol constraints",
        "historical_blocked_count_reused": False, "native_goal_status": "active",
        "source_built_or_executed": False, "cache_or_TLB_operations_executed": 0, "device_actions": 0,
        "other_owner_files_written_or_tools_run": False,
    }
    (BASE / "memory-contract-evidence.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ["status", "source_files_verified", "next_action_changed_by_evidence", "actual_FX3_702_runtime_helper_binding", "modified_or_flashable_package_produced", "goal_complete"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
