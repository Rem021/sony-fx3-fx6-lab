#!/usr/bin/env python3
"""Append a protected index entry and seal the scoped catalogue evidence."""
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
    with path.open("x") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def main():
    volume = plistlib.loads(subprocess.check_output(["diskutil", "info", "-plist", "/Volumes/KAFU2T"]))
    assert volume["VolumeUUID"] == "F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B"
    assert not (BASE / "final-receipt.json").exists()
    verification = json.loads((BASE / "verification-receipt.json").read_bytes())
    goal = json.loads((BASE / "goal-status-verified.json").read_bytes())
    assert verification["status"] == "PASS_SCOPED_CATALOG_AND_PREFIX_EVIDENCE_NOT_FLASH_READINESS"
    assert goal["goal"]["status"] == "active" and not verification["goal_complete"]
    write_new(BASE / "implementation-review.json", {
        "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "checks": ["Positive metadata controls include real payload links and an instructions-only FX3 item remains separate", "FX5 model registration is independently returned, rather than inferred from an empty search", "Both names and returned paths used for target negatives", "403 captures are retained as access gaps", "Different ETags and412 responses do not become whole archive identity proof", "AXS-R7 prefix is only3996 bytes, not an extracted full loader", "Pinned Msfirm condition is false before crypto lookup; no source import, key trial or code execution", "All nine whole-goal requirements retained", "No native/device actions or other-owner mutations"],
        "restart_recovery": "Four existing capture receipts and12 source objects were reverified before work resumed; no listed own Python source-collection process was observed in the scoped process snapshot. Completed network captures were not restarted.",
        "goal_complete": False, "modified_or_flashable_firmware_produced": False,
        "goal_turn_classification": verification["current_goal_turn_classification"], "historical_blocked_counts_reused": False})
    relative = BASE.relative_to(ROOT).as_posix()
    delta = ("\n- [2026-10-30 Sony专业目录与FX5注册路径复查](<" + relative + "/README.md>)：12个匿名JSON请求验证中国目录，FX5/FX5B已登记但四次固件查询为空；FX6 6.01/FX3 7.02/VENICE2 5.00正对照成功。旧组合包仅目录及AXS头片段，ETag/412保留，已核解析器头条件不匹配；无完整私有供体或可刷包，无设备动作。\n").encode()
    with (ROOT / "README.md").open("a+b") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        stream.seek(0)
        before = stream.read()
        assert relative.encode() not in before
        stream.seek(0, os.SEEK_END)
        stream.write(delta)
        stream.flush()
        os.fsync(stream.fileno())
        stream.seek(0)
        after = stream.read()
        assert after == before + delta
        write_new(BASE / "index-update-receipt.json", {"path": str(ROOT / "README.md"), "mode": "flock-protected append only",
            "before_bytes": len(before), "after_bytes": len(after), "before_sha256": sha(before), "after_sha256": sha(after),
            "delta_sha256": sha(delta), "prior_content_preserved": True})
    assert not list(BASE.rglob("__pycache__"))
    files = []
    for path in sorted(BASE.rglob("*")):
        if path.is_file():
            assert not path.is_symlink()
            data = path.read_bytes()
            files.append({"path": path.relative_to(BASE).as_posix(), "bytes": len(data), "sha256": sha(data)})
    write_new(BASE / "final-receipt.json", {"created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "stage": BASE.name,
        "files": files, "verification_status": verification["status"], "catalogue_API_JSON_requests_verified": 12,
        "registered_FX5_family_models": 2, "FX5_family_empty_queries": 4, "AXSR7_prefix_bytes": 3996,
        "complete_private_donor_obtained": False, "modified_or_flashable_firmware_produced": False, "full_objective_preserved": True,
        "goal_complete": False, "native_goal_status": "active", "device_actions": 0,
        "Sony_native_programs_or_downloaded_source_executed": False, "signing_key_work": False,
        "previous_goal_turn_classification": verification["previous_goal_turn_classification"],
        "current_goal_turn_classification": verification["current_goal_turn_classification"]})
    for row in json.loads((BASE / "final-receipt.json").read_bytes())["files"]:
        data = (BASE / row["path"]).read_bytes()
        assert len(data) == row["bytes"] and sha(data) == row["sha256"]
    print(json.dumps({"sealed_files_verified": len(files), "final_receipt_sha256": sha((BASE / "final-receipt.json").read_bytes()),
        "verification_status": verification["status"], "goal_complete": False, "goal_status": "active"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
