#!/usr/bin/env python3
"""Bounded original instructions: integer conversions and cache dispatch only."""
import sys
sys.dont_write_bytecode = True
import datetime
import hashlib
import json
import pathlib
import plistlib
import subprocess
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE, UC_HOOK_MEM_INVALID
from unicorn import UC_MEM_READ, UC_PROT_READ, UC_PROT_EXEC
from unicorn import arm64_const as reg

BASE = pathlib.Path(__file__).resolve().parent
FSROOT = BASE.parents[1] / "sony-firmware-20261024/stage2/extraction"
KBASE = 0xFFFFFF8008080000
STACK = 0x10000000
STOP = 0x10010000


def sha(data):
    return hashlib.sha256(data).hexdigest()


def run_case(kernel, binding, symbols, label, name, args, expected, validate=True):
    entries = {item["name"]: item for item in binding["functions"]}
    allowed_names = [name]
    if name == "__udif_cache_ctrl":
        allowed_names += ["__dma_map_area", "__dma_inv_area", "__inval_cache_range", "__dma_clean_area"]
    windows = [(int(entries[target]["VA"], 0), int(entries[target]["VA"], 0) + entries[target]["span_bytes"]) for target in allowed_names]
    uc = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
    uc.mem_map(KBASE, (len(kernel) + 4095) & ~4095)
    uc.mem_write(KBASE, kernel)
    uc.mem_protect(KBASE, (len(kernel) + 4095) & ~4095, UC_PROT_READ | UC_PROT_EXEC)
    uc.mem_map(STACK, 0x11000)
    uc.mem_write(STOP, b"\0\0\0\0")
    initial_sp = STACK + 0xF000
    uc.reg_write(reg.UC_ARM64_REG_SP, initial_sp)
    uc.reg_write(reg.UC_ARM64_REG_X30, STOP)
    callee = {number: 0x55AA000000000000 + number for number in range(19, 30)}
    for number, value in callee.items():
        uc.reg_write(getattr(reg, "UC_ARM64_REG_X" + str(number)), value)
    for number, value in enumerate(args):
        uc.reg_write(getattr(reg, "UC_ARM64_REG_X" + str(number)), value)
    cs = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
    record = {"label": label, "entry": name, "args": [hex(value) for value in args], "trace": [], "instruction_count": 0,
        "cache_or_system_instructions_executed": 0, "helper_replies_supplied": 0, "hardware_replies_supplied": 0}

    def stop(kind, **extra):
        if "stop" not in record:
            record["stop"] = {"kind": kind, **extra}
        uc.emu_stop()

    def code(machine, address, size, user):
        if address == STOP:
            stop("return")
            return
        if not any(start <= address < end for start, end in windows):
            stop("unexecuted_outside_call", VA=hex(address), symbols=[item["name"] for item in symbols if item["address"] == address])
            return
        raw = bytes(machine.mem_read(address, 4))
        decoded = list(cs.disasm(raw, address, count=1))
        if len(decoded) != 1:
            stop("unknown_instruction", VA=hex(address), bytes=raw.hex())
            return
        instruction = decoded[0]
        row = {"VA": hex(address), "file_offset": hex(address - KBASE), "bytes": raw.hex(), "instruction": instruction.mnemonic + " " + instruction.op_str}
        if instruction.mnemonic in {"mrs", "msr", "sys", "sysl", "at", "dc", "ic", "tlbi", "dsb", "dmb", "isb", "svc", "hvc", "smc"}:
            stop("unexecuted_system_or_cache_boundary", **row)
            return
        record["trace"].append(row)
        record["instruction_count"] += 1
        if record["instruction_count"] > 256:
            stop("instruction_limit")

    def memory(machine, access, address, size, value, user):
        if STACK <= address and address + size <= STOP:
            return
        if access == UC_MEM_READ and any(start <= address and address + size <= end for start, end in windows):
            return
        stop("unknown_or_runtime_memory", address=hex(address), size=size, access=access)

    def invalid(machine, access, address, size, value, user):
        stop("unmapped_memory", address=hex(address), size=size, access=access)
        return False

    uc.hook_add(UC_HOOK_CODE, code)
    uc.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE, memory)
    uc.hook_add(UC_HOOK_MEM_INVALID, invalid)
    try:
        uc.emu_start(int(entries[name]["VA"], 0), STOP + 4, count=300)
    except Exception as error:
        record["emulator_exception"] = {"type": type(error).__name__, "message": str(error)}
    record["x0_at_stop"] = hex(uc.reg_read(reg.UC_ARM64_REG_X0))
    record["w0_at_stop"] = hex(uc.reg_read(reg.UC_ARM64_REG_X0) & 0xFFFFFFFF)
    record["sp_at_stop"] = hex(uc.reg_read(reg.UC_ARM64_REG_SP))
    record["callee_saved_restored"] = all(uc.reg_read(getattr(reg, "UC_ARM64_REG_X" + str(number))) == value for number, value in callee.items())
    if not validate:
        record["validation_skipped_for_boundary_diagnosis"] = True
        return record
    if expected[0] == "return32":
        assert record["stop"]["kind"] == "return" and int(record["w0_at_stop"], 0) == expected[1]
    elif expected[0] == "return64":
        assert record["stop"]["kind"] == "return" and int(record["x0_at_stop"], 0) == expected[1]
    elif expected[0] == "logger_boundary":
        assert record["stop"]["kind"] == "unexecuted_outside_call" and "printk" in record["stop"]["symbols"]
    elif expected[0] == "cache_boundary":
        assert record["stop"]["kind"] == "unexecuted_system_or_cache_boundary"
        assert any(int(item["VA"], 0) == int(entries[expected[1]]["VA"], 0) for item in record["trace"]) or int(record["stop"]["VA"], 0) == int(entries[expected[1]]["VA"], 0)
    else:
        raise AssertionError(expected)
    if record["stop"]["kind"] == "return":
        assert record["callee_saved_restored"] and uc.reg_read(reg.UC_ARM64_REG_SP) == initial_sp
    record["expectation"] = [expected[0], hex(expected[1]) if isinstance(expected[1], int) else expected[1]]
    return record


def main():
    volume = plistlib.loads(subprocess.check_output(["diskutil", "info", "-plist", "/Volumes/KAFU2T"]))
    assert volume["VolumeUUID"] == "F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B"
    assert not (BASE / "original-instruction-probes.json").exists()
    binding = json.loads((BASE / "original-binding.json").read_bytes())
    helper = FSROOT / "read_filesystems.py"
    assert sha(helper.read_bytes()) == binding["filesystem_reader_sha256"]
    sys.path.insert(0, str(FSROOT))
    from read_filesystems import FAT16
    image = FSROOT / "nflasha3.img"
    assert sha(image.read_bytes()) == "ca5a8c80a1883c4a72c2f40018e3d40ab43e28ff0bf6a1d89f17d0680c607568"
    fs = FAT16(image)
    entry = next(item for item in fs.walk() if item["path"] == "/vmlinux.bin")
    kernel = fs.data(entry["cluster"], entry["size"])
    assert sha(kernel) == binding["kernel"]["sha256"]
    extension = json.loads((BASE / "selected-consumers.json").read_bytes())["cache_fallthrough"]
    fragment = (BASE / extension["fragment"]).read_bytes()
    assert sha(fragment) == extension["fragment_sha256"]
    offset = int(extension["file_offset"], 0)
    assert kernel[offset:offset + len(fragment)] == fragment
    binding["functions"].append(extension)
    catalog = pathlib.Path(binding["symbol_catalog"]["path"])
    assert sha(catalog.read_bytes()) == binding["symbol_catalog"]["sha256"]
    symbols = json.loads(catalog.read_bytes())
    cases = [
        ("AP-primary", "arch_p64_to_p32", [0x412000000], ("return32", 0x12000000)),
        ("DmmCfg-AP", "arch_p64_to_p32", [0x4132D8E00], ("return32", 0x132D8E00)),
        ("ESRAM-to32", "arch_p64_to_p32", [0xFE001000], ("return32", 0xFE001000)),
        ("FX5-domain-rejected", "arch_p64_to_p32", [0x200000000], ("logger_boundary", "printk")),
        ("CP-domain-rejected", "arch_p64_to_p32", [0x808730000], ("logger_boundary", "printk")),
        ("DDR-upper-exclusive", "arch_p64_to_p32", [0x4FE000000], ("logger_boundary", "printk")),
        ("DmmCfg-from32", "arch_p32_to_p64", [0x132D8E00], ("return64", 0x4132D8E00)),
        ("ESRAM-from32", "arch_p32_to_p64", [0xFE001000], ("return64", 0xFE001000)),
        ("from32-upper-exclusive", "arch_p32_to_p64", [0xFF000000], ("logger_boundary", "printk")),
        ("UDIF-FLUSH", "__udif_cache_ctrl", [STACK + 0x8000, 128, 1], ("cache_boundary", "__dma_clean_area")),
        ("UDIF-INVALIDATE", "__udif_cache_ctrl", [STACK + 0x8000, 128, 2], ("cache_boundary", "__dma_inv_area")),
        ("UDIF-NONE-name", "__udif_cache_ctrl", [STACK + 0x8000, 128, 3], ("cache_boundary", "__dma_clean_area")),
    ]
    results = [run_case(kernel, binding, symbols, *case) for case in cases]
    record = {"created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "kernel_sha256": sha(kernel), "cases": results,
        "scope": "Independent bounded RAM executions, not kernel boot, actual driver invocation, memory allocation, cache completion or runtime mapping measurement.",
        "return_width_note": "arch_p64_to_p32 returns uint32_t: validate W0. The original valid branch can leave the input high bits in X0.",
        "cache_or_system_instructions_executed": 0, "helper_or_hardware_replies_supplied": 0, "device_actions": 0,
        "modified_or_flashable_package_produced": False, "goal_complete": False}
    (BASE / "original-instruction-probes.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"cases": len(results), "executed_original_instructions": sum(item["instruction_count"] for item in results),
        "stops": [{"label": item["label"], "stop": item["stop"]} for item in results], "cache_or_system_instructions_executed": 0}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
