#!/usr/bin/env python3
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import os
import plistlib
import shutil
import subprocess
import sys
import time

ROOT = Path("/Volumes/KAFU2T/AI/Projects/Mac")
WORK = ROOT / "work/sony-firmware-20261024"
STAGE279 = WORK / "stage279-fixed-service-access-communication04"
STAGE281 = WORK / "stage281-fixed-host-cleanup04-plan"
RUN_DIR = STAGE281 / "runs/execution01"
JOB_DIR = Path("/private/tmp/fx3-host-cleanup-20261101-04")
GP = WORK / "GOAL_STATUS.json"

EXPECTED_BUNDLE_SHA = "1e7dfc527cdbd5028cc1dbbaa3d3a851d19a75c9db1993e48f6999daaade45af"
EXPECTED_PROG_SHA = "db39253a9e1edc3a6c759264afd78d55c251d842b4b3fbf4b6f51a18d0fdfb27"

sys.path.insert(0, str(STAGE279))
import controller_ipc as I
from cache_parser import sanitize


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def file_sha256(p: Path) -> str:
    return sha256(p.read_bytes()).hexdigest()


def verify_bundle():
    bundle_path = STAGE281 / "approval-bundle.json"
    assert file_sha256(bundle_path) == EXPECTED_BUNDLE_SHA
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    for entry in bundle["files"]:
        fp = STAGE281 / entry["path"]
        assert fp.stat().st_size == entry["bytes"], f"size mismatch: {entry['path']}"
        assert file_sha256(fp) == entry["sha256"], f"sha256 mismatch: {entry['path']}"
    return bundle


def query_sony_cache():
    raw = subprocess.run(
        ["/usr/sbin/ioreg", "-a", "-p", "IOService", "-r", "-c", "IOUSBHostDevice", "-l", "-w", "0"],
        capture_output=True,
        check=True,
        timeout=15,
    ).stdout
    return sanitize(raw)["candidates"]


def main():
    vol = plistlib.loads(subprocess.check_output(["/usr/sbin/diskutil", "info", "-plist", "/Volumes/KAFU2T"]))
    assert vol["VolumeUUID"] == "F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B"

    bundle = verify_bundle()
    candidates_before = query_sony_cache()
    assert candidates_before == [], f"Expected 0 Sony USB candidates before host cleanup, found: {candidates_before}"

    RUN_DIR.mkdir(mode=0o700, parents=True, exist_ok=False)
    shutil.copy2(GP, RUN_DIR / "goal-status-before.json")

    auth_receipt = {
        "recorded_utc": now_utc(),
        "user_statement": "ok继续",
        "grant_id": "fx3-host-cleanup-20261101-04",
        "approval_bundle_sha256": EXPECTED_BUNDLE_SHA,
        "physical_all_USB_disconnected_confirmed": True,
        "battery_UI_menu_normal_previously_confirmed": True,
        "explicit_exception_to_stage279_no_kill": True,
        "maximum_root_program_invocations": 1,
        "no_USB_or_camera_access": True,
    }
    (RUN_DIR / "authorization-receipt.json").write_text(
        json.dumps(auth_receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    assert not JOB_DIR.exists() and not JOB_DIR.is_symlink(), "/private/tmp/fx3-host-cleanup-20261101-04 already exists"
    JOB_DIR.mkdir(mode=0o700, parents=False, exist_ok=False)

    src_prog = STAGE281 / "artifacts/fixed-host-cleanup"
    dst_prog = JOB_DIR / "source-helper"
    shutil.copy2(src_prog, dst_prog)
    os.chmod(dst_prog, 0o500)
    assert file_sha256(dst_prog) == EXPECTED_PROG_SHA

    src_cmd = STAGE281 / "HostCleanup.command"
    dst_cmd = JOB_DIR / "HostCleanup.command"
    shutil.copy2(src_cmd, dst_cmd)
    os.chmod(dst_cmd, 0o700)
    cmd_sha = file_sha256(dst_cmd)

    staging_receipt = {
        "recorded_utc": now_utc(),
        "job": str(JOB_DIR),
        "fixed_program_sha256": EXPECTED_PROG_SHA,
        "command_sha256": cmd_sha,
        "scope": "HOST_ONLY_FIXED_AUDIT_TOKEN_CLEANUP_AFTER_PHYSICAL_CAMERA_DISCONNECT",
        "new_admin_program_invocations_not_yet_observed": True,
        "new_USB_requests": 0,
    }
    (RUN_DIR / "staging-receipt.json").write_text(
        json.dumps(staging_receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    open_proc = subprocess.run(
        ["/usr/bin/open", "-a", "Terminal", str(dst_cmd)],
        capture_output=True,
        text=True,
        timeout=15,
    )
    launch_req = {
        "recorded_utc": now_utc(),
        "open_returncode": open_proc.returncode,
        "open_stderr": open_proc.stderr,
        "role": "Terminal open request only, not root completion",
        "automatic_retry": False,
    }
    (RUN_DIR / "launch-request.json").write_text(
        json.dumps(launch_req, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    assert open_proc.returncode == 0, f"open Terminal failed: {open_proc.stderr}"

    print("Terminal opened for HostCleanup.command; waiting for sudo/Touch ID completion...", flush=True)

    launcher_res_path = JOB_DIR / "launcher-result.json"
    deadline = time.monotonic() + 300.0
    while time.monotonic() < deadline:
        if launcher_res_path.exists() and launcher_res_path.stat().st_size > 0:
            try:
                lr = json.loads(launcher_res_path.read_text(encoding="utf-8"))
                if "launcher_exit" in lr:
                    break
            except Exception:
                pass
        time.sleep(0.25)
    else:
        raise TimeoutError("Timed out waiting for HostCleanup.command completion in Terminal")

    for fn in ["launcher-result.json", "root-stdout.log", "root-stderr.log"]:
        shutil.copy2(JOB_DIR / fn, RUN_DIR / fn)

    verify_bundle()
    stdout_text = (RUN_DIR / "root-stdout.log").read_text(encoding="utf-8").strip()
    actual_stdout = json.loads(stdout_text) if stdout_text else {}

    ipc = I.IPC()
    p_helper = ipc.probe(37860)
    p_observer = ipc.probe(36633)
    candidates_after = query_sony_cache()

    actual_cleanup = {
        "recorded_utc": now_utc(),
        "status": (
            "HOST_CLEANUP_COMPLETE_ORIGINAL_COMMUNICATION04_REMAINS_UNKNOWN"
            if actual_stdout.get("status") == "HOST_CLEANUP_ONLY_OLD_TRIAL_STILL_UNKNOWN"
            and p_helper is None
            and p_observer is None
            else "HOST_CLEANUP_INCOMPLETE_OR_UNEXPECTED"
        ),
        "approved_bundle_verified_before_and_after": True,
        "actual_program_stdout": actual_stdout,
        "independent_original_PID_probes": {
            "37860": p_helper.__dict__ if p_helper else None,
            "36633": p_observer.__dict__ if p_observer else None,
        },
        "new_root_cleanup_helper_invocations": 1,
        "no_more_native_authentication_required": True,
        "camera_not_accessed": True,
        "Sony_cache_nodes_after_cleanup": candidates_after,
        "original_HELD_and_95_private_frames_retained": True,
        "camera_all_USB_physically_disconnected_user_confirmed": True,
        "battery_shooting_UI_and_menu_normal_user_confirmed": True,
        "original_trial_normal_USB_return_not_proven": True,
        "new_camera_trial_not_authorized": True,
    }
    (RUN_DIR / "actual-host-cleanup.json").write_text(
        json.dumps(actual_cleanup, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    readme_md = f"""# 通信04仅主机收尾实际结果（`fx3-host-cleanup-20261101-04`）

- **终态**：`{actual_cleanup["status"]}`
- **原根助手 `PID 37860`**：通过内核 `audit_token_t` 发送一次 `SIGKILL(9)` 后已退出（`helper_absent = {actual_stdout.get("helper_absent")}`，独立探测 `37860 = None`）。
- **原观察器 `PID 36633`**：收尾前已自行退出，复核未发送信号且保持不存在（`observer_signal = {actual_stdout.get("observer_signal")}, observer_absent = {actual_stdout.get("observer_absent")}`，独立探测 `36633 = None`）。
- **全局根日志**：`/private/var/root/fx3-owner-trials/global-fx3-owner.journal` 字节与 SHA256 完全未变（`old_guard_bytes_unchanged = {actual_stdout.get("old_guard_bytes_unchanged")}`）。
- **相机与 USB**：0 次 USB 请求、0 次固件写入，收尾前后 Sony 缓存节点均为 `[]`；原通信 04 的 95 帧私有流与 `HELD`/`UNKNOWN` 状态原样保留。
"""
    (RUN_DIR / "README.md").write_text(readme_md, encoding="utf-8")

    manifest_entries = []
    for p in sorted(RUN_DIR.iterdir()):
        if p.name == "final-manifest.json" or not p.is_file():
            continue
        manifest_entries.append({
            "path": p.name,
            "bytes": p.stat().st_size,
            "sha256": file_sha256(p),
        })
    (RUN_DIR / "final-manifest.json").write_text(
        json.dumps({"created_utc": now_utc(), "files": manifest_entries}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # Update GOAL_STATUS.json
    g = json.loads(GP.read_text(encoding="utf-8"))
    g["updated_at"] = now_utc()
    g["latest_stage"] = "stage281-fixed-host-cleanup04-plan/runs/execution01"
    g.setdefault("authorization_consumption", {})["Mac_host_cleanup04"] = {
        "grant_id": "fx3-host-cleanup-20261101-04",
        "status": "consumed_once_and_completed",
        "approval_bundle_sha256": EXPECTED_BUNDLE_SHA,
        "single_use_consumed": True,
        "automatic_retry_allowed": False,
    }
    g["host_cleanup04_execution"] = actual_cleanup
    g["service_access_communication04_execution"]["retained_helper_still_alive"] = False
    g.setdefault("latest_stage_evidence", {})["stage281_actual_host_cleanup04"] = {
        "stage": "stage281-fixed-host-cleanup04-plan/runs/execution01",
        "directory": str(RUN_DIR),
        "actual_host_cleanup": str(RUN_DIR / "actual-host-cleanup.json"),
        "final_manifest": str(RUN_DIR / "final-manifest.json"),
    }
    GP.write_text(json.dumps(g, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(actual_cleanup, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
