#!/usr/bin/env python3
"""Append an index record under a lock, then seal and independently reread this stage."""
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
    with path.open("x") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def main():
    volume = plistlib.loads(subprocess.check_output(["diskutil", "info", "-plist", "/Volumes/KAFU2T"]))
    assert volume["VolumeUUID"] == "F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B"
    assert not (BASE / "final-receipt.json").exists()
    audit = json.loads((BASE / "evidence-audit.json").read_bytes())
    goal = json.loads((BASE / "goal-status-verified.json").read_bytes())
    assert audit["status"] == "PASS_PUBLIC_CATALOG_EVIDENCE_NOT_FLASH_READINESS"
    assert goal["goal"]["status"] == "active"
    write_new(BASE / "implementation-review.json", {
        "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "review_scope": "Own collection and offline evidence audit code; no third-party execution or device backend.",
        "guards_reviewed": ["External volume UUID before new collection/output", "Refuse existing query output directory", "Metadata bounded to 4 MiB", "Only IDs 953 and 963 from actual positive responses", "Exact ModelList / firmwareInfoAPI / firmwareID / fwURL casing", "Declared synthetic input versions", "No credentials, ID enumeration, camera or updater code", "Prefix limited to 64 bytes with no full-identity claim", "Source archive bytes verified without running source", "Historical three-turn blocked count not reused"],
        "tests_not_replayed": "No old signature, emulation, hardware or download tests rerun; fresh network results were verified offline.",
        "full_goal_ready": False,
    })
    relative = BASE.relative_to(ROOT).as_posix()
    delta = ("\n- [2026-10-30 Sony公开固件目录与FX5供体查询](<" + relative + "/README.md>)：12次匿名元数据请求及正对照验证，FX3 7.02/953与α7 IV 6.02/963成功，FX5/FX5B仍为空版本/ID和0字节；取得原厂下载URL并仅核对FX3前64字节，未取得完整私有供体或修改包准入，未达可刷入门槛，无设备动作。\n").encode()
    index = ROOT / "README.md"
    with index.open("a+b") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        stream.seek(0)
        before = stream.read()
        assert relative.encode() not in before, "Index already contains this stage"
        stream.seek(0, os.SEEK_END)
        stream.write(delta)
        stream.flush()
        os.fsync(stream.fileno())
        stream.seek(0)
        after = stream.read()
        assert after == before + delta
        write_new(BASE / "index-update-receipt.json", {
            "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "path": str(index),
            "mode": "flock-protected append only", "before_bytes": len(before), "after_bytes": len(after),
            "before_sha256": sha(before), "after_sha256": sha(after), "delta_sha256": sha(delta),
            "prior_content_preserved": True,
        })
    assert not list(BASE.rglob("__pycache__"))
    items = []
    for path in sorted(BASE.rglob("*")):
        if path.is_file():
            assert not path.is_symlink()
            data = path.read_bytes()
            items.append({"path": path.relative_to(BASE).as_posix(), "bytes": len(data), "sha256": sha(data)})
    write_new(BASE / "final-receipt.json", {
        "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "stage": BASE.name,
        "files": items, "verification": {
            "status": "PASS_PUBLIC_CATALOG_EVIDENCE_NOT_FLASH_READINESS",
            "anonymous_metadata_requests": 12, "positive_control_results": 4, "empty_target_results": 6,
            "official_documents": 4, "source_members_verified": 19,
            "whole_remote_binary_identity_proved": False,
            "modified_or_flashable_firmware_produced": False, "device_actions": 0,
            "full_objective_preserved": True, "goal_complete": False, "native_goal_status": "active",
            "fresh_resume_blocking_audit_turn": 1, "historical_count_reused": False,
        },
    })
    readback = json.loads((BASE / "final-receipt.json").read_bytes())
    for item in readback["files"]:
        data = (BASE / item["path"]).read_bytes()
        assert len(data) == item["bytes"] and sha(data) == item["sha256"]
    print(json.dumps({"sealed_files_verified": len(items), "final_receipt_sha256": sha((BASE / "final-receipt.json").read_bytes()),
        "status": readback["verification"]["status"], "goal_status": goal["goal"]["status"], "goal_complete": False}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
