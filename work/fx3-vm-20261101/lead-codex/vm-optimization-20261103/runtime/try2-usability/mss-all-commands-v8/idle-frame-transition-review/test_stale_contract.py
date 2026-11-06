#!/usr/bin/env python3
"""Offline fixture test against the archived runner and no-write receipts."""
import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUN = HERE.parent.parent / "runs/try2mssallinternal-c017e6ed"
SOURCE = RUN / "observer-source/run_trial_v15_mss_all.py"


def read(name):
    return json.loads((RUN / name).read_text())


def main():
    # Compile the unchanged archived function alone; the full runner imports live VM tooling.
    tree = ast.parse(SOURCE.read_text())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                and n.name == "classify_internal_review")
    namespace = {"KEYS": {0x1ab: "MENU"}}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(SOURCE), "exec"), namespace)
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    request = read("internal-stale-01-f37ae114-request.json")
    observed = read("internal-observe-01.json")
    current = read("internal-stale-01-f37ae114-current.json")
    stale = read("internal-stale-01-f37ae114.json")
    status, reason = namespace["classify_internal_review"](
        request, observed, current, RUN.name, 1,
        digest(RUN / "internal-stale-01-f37ae114-current.png"),
        digest(RUN / "internal-observe-01.png"), set())
    receipt = read("receipt.json")
    assert (status, reason) == ("stale", "current_committed_frame_changed")
    assert stale["status"] == "stale_no_guest_write"
    assert stale["next_step_unchanged"] == 1 and stale["sent_steps_unchanged"] == 0
    assert stale["new_human_review_required"] and stale["old_request_never_auto_retried"]
    assert receipt["key_steps"] == 0
    assert not (RUN / "trial-input-events.jsonl").exists()
    print(json.dumps({"status": status, "reason": reason, "key_steps": receipt["key_steps"],
                      "new_human_review_required": True,
                      "note": "The later STOP_FOR_REVIEW file is a separate operator stop; this fixture does not exercise a live runner loop."},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
