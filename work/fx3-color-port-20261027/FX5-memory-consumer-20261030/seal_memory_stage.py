#!/usr/bin/env python3
"""Seal static evidence after a locked append to the existing project index."""
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


def write_new(path, data):
    with path.open("x") as target:
        json.dump(data, target, ensure_ascii=False, indent=2)
        target.write("\n")


def main():
    volume = plistlib.loads(subprocess.check_output(["diskutil", "info", "-plist", "/Volumes/KAFU2T"]))
    assert volume["VolumeUUID"] == "F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B"
    assert not (BASE / "final-receipt.json").exists()
    evidence = json.loads((BASE / "memory-contract-evidence.json").read_bytes())
    goal = json.loads((BASE / "goal-status-verified.json").read_bytes())
    assert evidence["status"] == "PASS_STATIC_SOURCE_CONTRACT_NOT_RUNTIME_OR_FLASH"
    assert goal["goal"]["status"] == "active"
    review = {
        "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "reviewed_scope": "Public source consumers and interval arithmetic, with explicitly separate AP/CP domains and source/runtime evidence.",
        "reviewed_findings": ["Identical public UDIF header is partial source compatibility only", "FX3 and FX5 DMA32 ESRAM/DDR rules differ", "Twenty original default spans are not twenty measured buffers", "Cache helpers require actual MMU translation; no privileged instructions executed", "Source cachetype2 checks endpoints only", "mmap cache guard is disabled by default", "SG map timing differs; not itself a defect claim", "Device-tree sample size does not identify real RAM or RAW pool", "FX3 7.00 public sources do not establish actual 7.02 binary binding"],
        "initial_source_layout_probe": "Zero matches for mach-cxd90057 was retained; exact namespace from archive index then yielded eight sources.",
        "source_collector_edits_after_capture": "Reduced metadata printing and moved namespace selection before the read loop; captured vendor files and formulae unchanged.",
        "verification": {"source_files": 44, "source_literal_locations": len(evidence["source_facts"]),
            "original_default_spans": len(evidence["original_FX3_default_span_results"]),
            "boundary_inputs": len(evidence["DMA32_boundary_arithmetic"]),
            "prior_sealed_files_verified": sum(item["members_verified"] for item in evidence["verified_prior_stages"])},
        "execution_scope": "Only own Python/static analysis and volume metadata; no compiler, vendor source execution, device, cache/TLB, native Sony updater or private signing-key work.",
        "goal_complete": False, "modified_or_flashable_firmware_produced": False,
    }
    assert review["verification"] == {"source_files": 44, "source_literal_locations": 42, "original_default_spans": 20, "boundary_inputs": 9, "prior_sealed_files_verified": 109}
    write_new(BASE / "implementation-review.json", review)
    relative = BASE.relative_to(ROOT).as_posix()
    delta = ("\n- [2026-10-30 FX5与FX3的DMA地址及缓存协议](<" + relative + "/README.md>)：成对核对44份公开源码、20个原默认AP/CP范围和9个边界输入；UDIF参数头相同，但DMA32的DDR/ESRAM规则与SG缓存交接时序不同。未绑定实际7.02模块、未取得私有ISP或可刷包，无设备/cache/TLB操作。\n").encode()
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
    write_new(BASE / "final-receipt.json", {"created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "stage": BASE.name, "files": files, "verification": review["verification"],
        "status": evidence["status"], "native_goal_status": "active", "goal_complete": False,
        "previous_goal_turn_classification": evidence["previous_goal_turn_classification"],
        "current_goal_turn_classification": evidence["current_goal_turn_classification"],
        "device_actions": 0, "source_built_or_executed": False, "cache_or_TLB_operations_executed": 0,
        "modified_or_flashable_firmware_produced": False})
    reread = json.loads((BASE / "final-receipt.json").read_bytes())
    for item in reread["files"]:
        data = (BASE / item["path"]).read_bytes()
        assert len(data) == item["bytes"] and sha(data) == item["sha256"]
    print(json.dumps({"sealed_files_verified": len(files), "final_receipt_sha256": sha((BASE / "final-receipt.json").read_bytes()),
        "status": evidence["status"], "goal_complete": False}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
