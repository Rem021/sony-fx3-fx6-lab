#!/usr/bin/env python3
"""Seal the completed offline binding stage, preserving the shared index by append."""
import datetime
import fcntl
import hashlib
import json
import os
import pathlib
import plistlib
import subprocess

BASE = pathlib.Path(__file__).resolve().parent
ROOT = pathlib.Path("/Volumes/KAFU2T/AI/Projects/Mac")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_new(path, value):
    with path.open("x") as target:
        json.dump(value, target, ensure_ascii=False, indent=2)
        target.write("\n")


def main():
    volume = plistlib.loads(subprocess.check_output(["diskutil", "info", "-plist", "/Volumes/KAFU2T"]))
    assert volume["VolumeUUID"] == "F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B"
    assert not (BASE / "final-receipt.json").exists()
    verification = json.loads((BASE / "verification-receipt.json").read_bytes())
    goal = json.loads((BASE / "goal-status-verified.json").read_bytes())
    assert verification["status"] == "PASS_ORIGINAL_PACKAGE_LINKAGE_AND_BOUNDED_PROBES_NOT_RUNTIME_OR_FLASH"
    assert goal["goal"]["status"] == "active" and not verification["goal_complete"]
    write_new(BASE / "implementation-review.json", {
        "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "reviewed_boundaries": ["Source association advanced to original packaged binaries, not to running body identity", "Original export records checked separately from recovered symbol names", "22 ET_REL kernel modules separated from one unresolved ET_DYN userspace library", "DMM log area references do not prove RAW pixel allocation", "Only five pure conversion cases returned; four invalid cases stop before printk", "Three cache paths stop before DC and are incomplete prefixes", "W0 versus X0 return width is explicit", "Internal cachecontrol command/frame interpretation is static and not an external device procedure", "Original mapping, module and kernel files preserved; no native/device execution", "Earlier failed captures and guard stops retained without fabricating responses"],
        "reviewed_verification": verification["status"], "source_or_native_Sony_programs_executed": False,
        "goal_complete": False, "modified_or_flashable_firmware_produced": False,
        "goal_turn_classification": "progress: original target package linkage and integer/cache-dispatch evidence changed next investigation to descriptor producers and pixel consumers",
        "historical_blocked_counts_reused": False})
    relative = BASE.relative_to(ROOT).as_posix()
    delta = ("\n- [2026-10-30 FX3原包DMA与缓存接口绑定](<" + relative + "/README.md>)：15原内核范围/10独立导出，565 ELF中22模块及1未解析共享库的217重定位；12有界案例/158原指令，5转换返回、4诊断调用前停、3缓存DC前停。DMM日志不充RAW像素，未证机身加载/完整ISP/修改包准入，无设备或缓存操作。\n").encode()
    index = ROOT / "README.md"
    with index.open("a+b") as target:
        fcntl.flock(target.fileno(), fcntl.LOCK_EX)
        target.seek(0)
        before = target.read()
        assert relative.encode() not in before
        target.seek(0, os.SEEK_END)
        target.write(delta)
        target.flush()
        os.fsync(target.fileno())
        target.seek(0)
        after = target.read()
        assert after == before + delta
        write_new(BASE / "index-update-receipt.json", {"created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "path": str(index), "mode": "flock-protected append only", "before_bytes": len(before), "after_bytes": len(after),
            "before_sha256": sha(before), "after_sha256": sha(after), "delta_sha256": sha(delta), "prior_content_preserved": True})
    assert not list(BASE.rglob("__pycache__"))
    files = []
    for path in sorted(BASE.rglob("*")):
        if path.is_file():
            assert not path.is_symlink()
            data = path.read_bytes()
            files.append({"path": path.relative_to(BASE).as_posix(), "bytes": len(data), "sha256": sha(data)})
    write_new(BASE / "final-receipt.json", {"created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "stage": BASE.name,
        "files": files, "verification_status": verification["status"], "original_function_ranges": 15, "independent_export_records": 10,
        "importing_kernel_modules": 22, "unresolved_shared_library_references": 1, "import_relocations": 217,
        "bounded_original_cases": 12, "original_instructions": 158, "cache_or_system_instructions_executed": 0,
        "device_actions": 0, "native_Sony_programs_executed": 0, "full_objective_preserved": True,
        "modified_or_flashable_firmware_produced": False, "goal_complete": False, "native_goal_status": "active",
        "prior_goal_turn_classification": verification["prior_goal_turn_classification"],
        "current_goal_turn_classification": verification["current_goal_turn_classification"]})
    saved = json.loads((BASE / "final-receipt.json").read_bytes())
    for row in saved["files"]:
        data = (BASE / row["path"]).read_bytes()
        assert len(data) == row["bytes"] and sha(data) == row["sha256"]
    print(json.dumps({"sealed_files_verified": len(files), "final_receipt_sha256": sha((BASE / "final-receipt.json").read_bytes()),
        "verification_status": verification["status"], "goal_status": "active", "goal_complete": False}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
