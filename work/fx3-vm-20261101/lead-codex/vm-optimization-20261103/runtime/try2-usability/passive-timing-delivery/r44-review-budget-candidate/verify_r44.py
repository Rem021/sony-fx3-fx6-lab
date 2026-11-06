#!/usr/bin/env python3
"""Top-level offline verification for the r44 60s whole-step candidate.

This never starts the runner, browser, HTTP server, QEMU, QMP, guest, camera or any
deployment path. It only re-hashes frozen inputs, runs the two Node fake-DOM tests
and the Python pure/static tests, and writes a bounded receipt.
"""
import hashlib
import json
import os
import plistlib
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPTS = ROOT / "receipts"
RECEIPTS.mkdir(exist_ok=True)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(name, value):
    path = RECEIPTS / name
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    return path


def run(name, argv, timeout=120):
    started = time.time_ns()
    proc = subprocess.run(
        argv,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    ended = time.time_ns()
    (RECEIPTS / (name + ".stdout.txt")).write_text(proc.stdout)
    (RECEIPTS / (name + ".stderr.txt")).write_text(proc.stderr)
    write(name + ".process.json", {
        "argv": argv,
        "returncode": proc.returncode,
        "started_ns": started,
        "ended_ns": ended,
        "stdout_sha256": hashlib.sha256(proc.stdout.encode()).hexdigest(),
        "stderr_sha256": hashlib.sha256(proc.stderr.encode()).hexdigest(),
        "target_runner_main_started": False,
        "browser_started": False,
        "server_started": False,
        "VM_started": False,
    })
    assert proc.returncode == 0, (name, proc.returncode, proc.stderr[-2000:])
    return proc.stdout


def main():
    volume = plistlib.loads(subprocess.check_output(
        ["diskutil", "info", "-plist", "/Volumes/KAFU2T"]))["VolumeUUID"]
    assert volume == "F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B", volume

    source = json.loads((ROOT / "SOURCE-FREEZE.json").read_text())
    core = json.loads((ROOT / "CORE-SOURCE-FREEZE.json").read_text())
    assert len(source) == 43, len(source)
    assert len(core) == 38, len(core)
    for name, expected in source.items():
        assert sha(ROOT / name) == expected, name
    for name, expected in core.items():
        assert sha(ROOT / name) == expected, name

    adapter = (ROOT / "return-tools/return_adapter.py").read_text()
    operate_sha = adapter.split("OPERATE_SHA='", 1)[1].split("'", 1)[0]
    core_sha = adapter.split("CORE_FREEZE_SHA='", 1)[1].split("'", 1)[0]
    assert operate_sha == sha(ROOT / "runtime-wrapper/operate.py")
    assert core_sha == sha(ROOT / "CORE-SOURCE-FREEZE.json")
    assert source["return-tools/return_adapter.py"] == sha(ROOT / "return-tools/return_adapter.py")

    before = json.loads((ROOT / "INPUTS-BEFORE.json").read_text())
    after = json.loads((ROOT / "INPUTS-AFTER.json").read_text())
    assert before["r42_source_freeze_sha256"] == "6f8d7e926ae6a1387c42cb43f8e4c95ca74e3c51572a8dac1bee783868a89652"
    assert before["r42_core_freeze_sha256"] == "0760035499c8362eef3ee24c819d3b8f6cbed3bf156bf4ee8b09adc187b1ba68"
    assert before["r42_candidate_sha256"] == "857c2b7aed207ca2351029a5089741989b8fbfd4aa6feeed424ab0a4e4a11806"
    assert before["r42_cpio_sha256"] == "59c5850a4a367ddf469aa2c9f774e0808e3fd6632b9c566323e1a07592a03c63"
    assert before["r42_source_files"] == after["r42_source_files"]
    assert before["r42_candidate_sha256"] == after["r42_candidate_sha256"]
    assert before["r42_cpio_sha256"] == after["r42_cpio_sha256"]
    assert after["input_unchanged"] is True

    selector = json.loads(run("selector", [
        sys.executable, "-B", "-c",
        "import importlib.util,json;from pathlib import Path;"
        "p=Path('r35_package_selection.py');s=importlib.util.spec_from_file_location('r44_selector',p);"
        "m=importlib.util.module_from_spec(s);s.loader.exec_module(m);"
        "print(json.dumps(m.verify_package(Path.cwd()/'run-inputs/preflight-r44-offline'),ensure_ascii=False))",
    ]))
    assert selector["profile"] == "r44-review-budget-60s"
    assert selector["label"] == "v44review-n64-r44"
    assert selector["candidate_sha256"] == "857c2b7aed207ca2351029a5089741989b8fbfd4aa6feeed424ab0a4e4a11806"
    assert selector["initrd_sha256"] == "59c5850a4a367ddf469aa2c9f774e0808e3fd6632b9c566323e1a07592a03c63"
    assert selector["initrd_bytes"] == 453213884

    python_out = run("python-pure", [sys.executable, "-B", str(ROOT / "tests/python_pure_tests.py")])
    python = json.loads(python_out)
    assert python["cases_failed"] == 0, python
    (RECEIPTS / "python-pure-tests.json").write_text(python_out)

    node_out = run("fake-clock", ["node", str(ROOT / "tests/fake_clock_deadline_test.cjs")])
    fake_clock = json.loads((ROOT / "receipts/fake-clock-deadline.json").read_text())
    assert fake_clock["cases_failed"] == 0, fake_clock
    assert fake_clock["cases_total"] == 14
    assert fake_clock["deadline_ms"] == 60000

    node_out = run("guard-behaviour", ["node", str(ROOT / "tests/guard_behavior_test.cjs")])
    guard = json.loads((ROOT / "receipts/guard-behaviour.json").read_text())
    assert guard["cases_failed"] == 0, guard
    assert guard["cases_total"] == 6

    forbidden = {"Start-once", "runtime.json", "deadline-install.json",
                 "runner-stdout.txt", "runner-stderr.txt", "trial-web-final-receipt.json"}
    found = [str(p.relative_to(ROOT)) for p in ROOT.rglob("*") if p.is_file() and p.name in forbidden]
    assert not found, found

    result = {
        "schema": "fx3-r44-verify-v1",
        "candidate": str(ROOT),
        "verified_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "volume_uuid": volume,
        "offline": True,
        "browser": False,
        "server": False,
        "network": False,
        "VM": False,
        "QMP": False,
        "guest": False,
        "camera_usb_sd": False,
        "deployment": False,
        "source43_sha256": sha(ROOT / "SOURCE-FREEZE.json"),
        "core38_sha256": sha(ROOT / "CORE-SOURCE-FREEZE.json"),
        "adapter_operate_sha256": operate_sha,
        "adapter_core_freeze_sha256": core_sha,
        "r42_candidate_sha256": before["r42_candidate_sha256"],
        "r42_cpio_sha256": before["r42_cpio_sha256"],
        "selector": selector,
        "tests": {
            "python_pure": {"total": python["cases_total"], "passed": python["cases_passed"], "failed": python["cases_failed"]},
            "fake_clock_deadline": {"total": fake_clock["cases_total"], "passed": fake_clock["cases_passed"], "failed": fake_clock["cases_failed"]},
            "guard_behaviour": {"total": guard["cases_total"], "passed": guard["cases_passed"], "failed": guard["cases_failed"]},
        },
        "forbidden_runtime_artifacts": found,
        "status": "passed_offline_only",
        "limitations": [
            "No VM, browser, HTTP server, QEMU, QMP or guest was started.",
            "The 60s candidate has not been activated; the frozen 20s entry points are untouched.",
            "Offline passing is not a VM menu pass and does not prove a speed-up.",
            "The fake-DOM guards exercise the whole-step budget gate, not the full firmware/UI path.",
        ],
    }
    write("VERIFY-RESULT.json", result)
    (ROOT / "VERIFY-RESULT.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "tests": result["tests"],
                      "source43_sha256": result["source43_sha256"],
                      "core38_sha256": result["core38_sha256"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
