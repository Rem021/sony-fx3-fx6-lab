#!/usr/bin/env python3
"""Independent byte/linkage audit; does not replay guest or device operations."""
import sys
sys.dont_write_bytecode = True
import datetime
import hashlib
import json
import pathlib
import plistlib
import struct
import subprocess

BASE = pathlib.Path(__file__).resolve().parent
FSROOT = BASE.parents[1] / "sony-firmware-20261024/stage2/extraction"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def main():
    volume = plistlib.loads(subprocess.check_output(["diskutil", "info", "-plist", "/Volumes/KAFU2T"]))
    assert volume["VolumeUUID"] == "F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B"
    assert not (BASE / "verification-receipt.json").exists()
    binding = read(BASE / "original-binding.json")
    selected = read(BASE / "selected-consumers.json")
    probes = read(BASE / "original-instruction-probes.json")
    scope = read(BASE / "consumer-scope.json")
    assert sha((FSROOT / "read_filesystems.py").read_bytes()) == binding["filesystem_reader_sha256"]
    sys.path.insert(0, str(FSROOT))
    from read_filesystems import FAT16
    image = FSROOT / "nflasha3.img"
    assert sha(image.read_bytes()) == "ca5a8c80a1883c4a72c2f40018e3d40ab43e28ff0bf6a1d89f17d0680c607568"
    fs = FAT16(image)
    item = next(row for row in fs.walk() if row["path"] == "/vmlinux.bin")
    kernel = fs.data(item["cluster"], item["size"])
    assert sha(kernel) == binding["kernel"]["sha256"] == probes["kernel_sha256"]
    base = int(binding["kernel"]["VA_base"], 0)
    functions = binding["functions"] + [selected["cache_fallthrough"]]
    exports = 0
    for row in functions:
        data = (BASE / row["fragment"]).read_bytes()
        start = int(row["file_offset"], 0)
        assert kernel[start:start + row["span_bytes"]] == data and sha(data) == row["fragment_sha256"]
        export = row.get("independent_export_record")
        if not export:
            continue
        offset = int(export["file_offset"], 0)
        raw = kernel[offset:offset + 16]
        assert raw.hex() == export["raw16"]
        value, pointer = struct.unpack("<QQ", raw)
        end = kernel.index(b"\0", pointer - base)
        assert value == int(row["VA"], 0) and kernel[pointer - base:end].decode() == row["name"]
        exports += 1
    assert len(functions) == 15 and exports == 10
    for case in probes["cases"]:
        assert not case.get("emulator_exception")
        assert case["helper_replies_supplied"] == case["hardware_replies_supplied"] == 0
        for instruction in case["trace"]:
            offset = int(instruction["file_offset"], 0)
            assert kernel[offset:offset + 4].hex() == instruction["bytes"]
            assert instruction["instruction"].split()[0] not in {"mrs", "msr", "sys", "sysl", "at", "dc", "ic", "tlbi", "dsb", "dmb", "isb", "svc", "hvc", "smc"}
        stop = case["stop"]
        if stop["kind"] == "return":
            assert case["callee_saved_restored"]
        if stop["kind"] == "unexecuted_system_or_cache_boundary":
            offset = int(stop["file_offset"], 0)
            assert kernel[offset:offset + 4].hex() == stop["bytes"] and stop["instruction"].startswith("dc ")
    stops = {kind: sum(row["stop"]["kind"] == kind for row in probes["cases"]) for kind in {row["stop"]["kind"] for row in probes["cases"]}}
    assert stops == {"return": 5, "unexecuted_outside_call": 4, "unexecuted_system_or_cache_boundary": 3}
    assert sum(row["instruction_count"] for row in probes["cases"]) == 158
    assert sum(row["A64_ELF_files_scanned"] for row in binding["scanned_images"]) == 565
    assert len(binding["importing_ELFs"]) == 23 and sum(len(row["relocations"]) for row in binding["importing_ELFs"]) == 217
    assert scope["importing_kernel_modules"] == 22 and scope["unresolved_shared_library_references"] == 1
    assert scope["dynamic_definitions_for_same_names"] == []
    for module in selected["modules"]:
        assert sha((BASE / module["local_path"]).read_bytes()) == module["sha256"]
    previous = BASE.parent / "FX5-memory-consumer-20261030"
    manifest = previous / "final-receipt.json"
    assert sha(manifest.read_bytes()) == "bb7805678abebba38bd05086292e73aeff82fc114a12c685eed1cdb6ccde8e55"
    old = read(manifest)
    for row in old["files"]:
        data = (previous / row["path"]).read_bytes()
        assert len(data) == row["bytes"] and sha(data) == row["sha256"]
    result = {"created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": "PASS_ORIGINAL_PACKAGE_LINKAGE_AND_BOUNDED_PROBES_NOT_RUNTIME_OR_FLASH",
        "original_kernel_sha256": sha(kernel), "original_function_spans_verified": 15, "independent_exports_verified": 10,
        "A64_ELFs_scanned": 565, "importing_kernel_modules": 22, "unresolved_shared_library_references": 1, "recorded_import_relocations": 217,
        "guest_cases": 12, "executed_original_instructions": 158, "guest_stop_counts": stops,
        "return_ABI_note": "p64_to_p32 returns a uint32_t in W0. Successful original paths can retain input high bits in X0; do not read it as a full 64-bit converted address.",
        "cachecontrol_static_command_review": {"scope": "Original module-relative .text offsets; internal callback commands, not a verified external ioctl/device procedure.",
            "command_dispatch": {"0x3000": "Prepare aligned fields from frame+0x10 and length frame+0x28; then query cache type", "0x3001": "Require cache type 0x11, pass flag1 to helper at .text+8", "0x3002": "Require cache type 0x11, pass flag2 to helper at .text+8"},
            "inferred_frame_minimum_bytes": 48, "fields": {"0x00": "command", "0x04": "status", "0x08": "aligned start produced by command0x3000", "0x10": "original start used by producer", "0x18": "original inclusive end produced by command0x3000", "0x20": "aligned inclusive end produced by command0x3000", "0x28": "length"},
            "alignment": "The original code uses a 0x3f mask; this is an observed compiled 64-byte alignment rule, not a measurement of every hardware cache.",
            "status_zero_limit": "Helper .text+0xe8 sets status0 and skips __udif_cache_ctrl when the mapped address or length condition at0xa4..0xb4 is zero; static path only, not a reproduced mapping failure or proof of completed cache maintenance.",
            "producer_runtime_binding": False},
        "previous_stage_files_verified": len(old["files"]),
        "prior_goal_turn_classification": "progress: paired source cache/DMA contracts changed target binding investigation",
        "current_goal_turn_classification": "progress: original 7.02 kernel exports, module call relocations and bounded original conversion/dispatch paths",
        "full_objective_preserved": True, "complete_private_donor_obtained": False,
        "actual_running_body_kernel_or_module_state_verified": False, "physical_RAW_samples_or_full_ISP_proved": False,
        "modified_or_flashable_firmware_produced": False, "goal_complete": False, "native_goal_status": "active",
        "device_actions": 0, "native_Sony_programs_executed": 0, "cache_or_system_instructions_executed": 0,
        "hardware_or_helper_replies_fabricated": False, "other_owner_files_written_or_tools_operated": False}
    (BASE / "verification-receipt.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ["status", "original_function_spans_verified", "independent_exports_verified", "importing_kernel_modules", "guest_cases", "executed_original_instructions", "goal_complete"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
