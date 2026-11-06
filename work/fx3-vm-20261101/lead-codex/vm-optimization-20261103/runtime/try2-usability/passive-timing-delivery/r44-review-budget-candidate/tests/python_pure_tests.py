#!/usr/bin/env python3
"""Offline pure-function and static-boundary checks for the r44 60s candidate.

No browser, server, network, VM, QMP, guest, runner, package launch or deployment.
The only imports are side-effect-free stdlib modules and the candidate's pure selector
and observation modules. cleanup.py is not imported; its one pure classifier is
extracted from the actual source AST.
"""
import ast
import hashlib
import importlib.util
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEL = ROOT.parent
R42 = DEL / "r42-command-timing-runner"
RESULTS = []


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check(name, fn):
    try:
        detail = fn()
        RESULTS.append({"name": name, "passed": True, "detail": detail})
    except BaseException as exc:  # noqa: BLE001 - receipt must retain every failure
        RESULTS.append({"name": name, "passed": False, "error": type(exc).__name__ + ": " + str(exc)})


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source_state(budget, mode="armed"):
    binding = {
        "attempt_id": "a" * 36,
        "nonce": "b" * 36,
        "launch_request_id": "c" * 36,
        "document_time_origin": 100.0,
        "base_step": 0,
    }
    armed = 1000.0
    due = armed + budget
    cancelled = armed + 30000.0 if mode == "cancelled" else None
    state = {
        "qualified": True,
        "mode": mode,
        "attempt_binding": binding,
        "attempt_id": binding["attempt_id"],
        "nonce": binding["nonce"],
        "launch_id": binding["launch_request_id"],
        "document_time_origin": binding["document_time_origin"],
        "document_id": "d" * 36,
        "step": 0,
        "alarm_state": mode,
        "alarm_budget_ms": budget,
        "alarm_due_exact_in_browser": True,
        "alarm_due_ms": due,
        "alarm_armed_ms": armed,
        "alarm_cancelled_ms": cancelled,
        "phase": "ready",
        "ready": True,
        "busy": False,
        "review_required": False,
        "error": None,
        "delivery_unknown": False,
        "review_unknown": False,
        "protocol_unknown": False,
        "ending": False,
        "finished": False,
        "attempt_outcome": "not_posted",
        "mutation_called": False,
        "fresh_server_lifecycle": {
            "phase": "ready",
            "ready": True,
            "busy": False,
            "review_required": False,
            "error": None,
            "steps": 0,
            "launch_id": binding["launch_request_id"],
            "render_valid": True,
            "protocol_unknown": False,
        },
        "performance_ms": 2000.0 if mode == "armed" else 31000.0,
        "sequence": 1,
    }
    return state, binding


def alarm_value(budget=60000, state="cancelled", due_delta=None):
    url = "http://127.0.0.1:60752/"
    launch = "1" * 36
    current = {
        "nonce": "22222222-2222-4222-8222-222222222222",
        "armed_ms": 1000.0,
        "due_ms": 1000.0 + (budget if due_delta is None else due_delta),
        "deadline_ms": budget,
        "state": state,
    }
    return {
        "version": 1,
        "deadline_ms": budget,
        "expectedURL": url,
        "expectedLaunchId": launch,
        "sealed": False,
        "documentTimeOrigin": 100.0,
        "events": [{"event": "armed", "nonce": current["nonce"], "due_ms": current["due_ms"]}],
        "current": current,
    }


def main():
    def t_source_freeze():
        source = json.loads((ROOT / "SOURCE-FREEZE.json").read_text())
        core = json.loads((ROOT / "CORE-SOURCE-FREEZE.json").read_text())
        assert len(source) == 43, len(source)
        assert len(core) == 38, len(core)
        for name, expected in source.items():
            assert sha(ROOT / name) == expected, name
        for name, expected in core.items():
            assert sha(ROOT / name) == expected, name
        assert source["CORE-SOURCE-FREEZE.json"] == sha(ROOT / "CORE-SOURCE-FREEZE.json")
        return {"source_count": 43, "core_count": 38,
                "source_sha256": sha(ROOT / "SOURCE-FREEZE.json"),
                "core_sha256": sha(ROOT / "CORE-SOURCE-FREEZE.json")}

    def t_adapter_pins():
        text = (ROOT / "return-tools/return_adapter.py").read_text()
        operate = re.search(r"OPERATE_SHA='([0-9a-f]{64})'", text).group(1)
        core = re.search(r"CORE_FREEZE_SHA='([0-9a-f]{64})'", text).group(1)
        assert operate == sha(ROOT / "runtime-wrapper/operate.py")
        assert core == sha(ROOT / "CORE-SOURCE-FREEZE.json")
        source = json.loads((ROOT / "SOURCE-FREEZE.json").read_text())
        assert source["return-tools/return_adapter.py"] == sha(ROOT / "return-tools/return_adapter.py")
        return {"operate_sha256": operate, "core_sha256": core}

    def t_budget_matrix():
        expected = {
            "operator-helpers/deadline.js": (1, 0),
            "operator-helpers/snapshot_read.js": (1, 0),
            "operator-helpers/planned_navigation_click.js": (1, 0),
            "operator-helpers/recovery_cancel.js": (3, 0),
            "operator-helpers/recovery_readonly.js": (5, 0),
            "operator-helpers/snapshot_confirm.js": (1, 0),
            "operator-helpers/postkey_read.js": (3, 0),
            "operator-helpers/recovery_observation.py": (1, 0),
            "runtime-wrapper/cleanup.py": (3, 0),
            "runtime-wrapper/operate.py": (1, 0),
        }
        rows = []
        for name, (new_count, old_count) in expected.items():
            text = (ROOT / name).read_text()
            actual_new = text.count("60_000") if name.endswith("deadline.js") else text.count("60000")
            assert actual_new == new_count, (name, actual_new, new_count)
            assert text.count("20000") == old_count, (name, "20000", text.count("20000"))
            assert text.count("20_000") == 0, (name, "20_000")
            rows.append({"path": name, "new_budget_literals": actual_new,
                         "old_budget_literals": 0})
        deadline = (ROOT / "operator-helpers/deadline.js").read_text()
        assert "const DEADLINE_MS = 60_000;" in deadline
        assert "const SCRIPT_SHA = '852c83d673478a8f3db8a4d71989259c476a2325f2655a8dd3c8f8e46acfa55b';" in deadline
        planned = (ROOT / "operator-helpers/planned_navigation_click.js").read_text()
        assert "candidate whole-step budget is 60 seconds" in planned
        assert "alarm_60s_browser_identity" in (ROOT / "operator-helpers/recovery_observation.py").read_text()
        return {"rows": rows, "page_fingerprint": "852c83d673478a8f3db8a4d71989259c476a2325f2655a8dd3c8f8e46acfa55b"}

    def t_preserved_boundaries():
        exact_equal = [
            "run_trial_r24_review_snapshot.py",
            "trial_web_r24_review_snapshot.py",
            "review_page_r24.js",
            "confirm_page_r24.js",
            "startup_observation.py",
            "trial_ring_cached.py",
            "trial_log_v4_mss.py",
            "runtime-wrapper/start_and_wait.py",
            "runtime-wrapper/postkey_flow.py",
            "runtime-wrapper/recovery_guard.py",
            "operator-helpers/planned_prerequisite.py",
            "operator-helpers/postkey_observation.py",
            "operator-helpers/recovery_tools.py",
            "operator-helpers/review_snapshot_cli.py",
            "operator-helpers/deadline_cli.py",
            "return-tools/short_tool.mjs",
            "return-tools/show_result.mjs",
            "return-tools/tool_call.mjs",
        ]
        for name in exact_equal:
            assert (ROOT / name).read_bytes() == (R42 / name).read_bytes(), name
        trial_web = (ROOT / "trial_web_r24_review_snapshot.py").read_text()
        assert "SNAPSHOT_TTL=20.0" in trial_web
        runner = (ROOT / "run_trial_r24_review_snapshot.py").read_text()
        assert "now-command['sent_monotonic'] <= 12" in runner
        start = (ROOT / "runtime-wrapper/start_and_wait.py").read_text()
        assert "deadline=start_monotonic+180" in start
        postkey = (ROOT / "operator-helpers/postkey_read.js").read_text()
        assert "wait.not_before_ms=wait.arm_ms+5000" in postkey
        prepare = (ROOT / "prepare_run.py").read_text()
        assert "candidate whole-step operator deadline 60s" in prepare
        assert "候选60s不重置" in prepare
        assert "原20s" not in prepare
        launch = (ROOT / "runtime-wrapper/launch_prepare.py").read_text()
        assert "'--max-minutes','8'" in launch
        assert "'--max-steps','32'" in launch
        assert "'--snapshot-tail'" in launch
        assert "'--preflight'" not in launch  # no accidental new action
        return {"exact_equal_files": len(exact_equal), "native_ack_seconds": 12,
                "snapshot_ttl_seconds": 20.0, "startup_seconds": 180,
                "first_observation_not_before_arm_ms": 5000,
                "run_minutes": 8, "max_steps": 32}

    def t_selector():
        m = load_module("r44_selector", ROOT / "r35_package_selection.py")
        assert m.PROFILE == "r44-review-budget-60s"
        assert m.LABEL == "v44review-n64-r44"
        assert m.APPROVED_HOST == ROOT
        assert m.PACKAGE == ROOT.parent / "r42-command-timing-package"
        assert m.CANDIDATE_SHA == "857c2b7aed207ca2351029a5089741989b8fbfd4aa6feeed424ab0a4e4a11806"
        assert m.CPIO_SHA == "59c5850a4a367ddf469aa2c9f774e0808e3fd6632b9c566323e1a07592a03c63"
        run_dir = ROOT / "run-inputs/preflight-r44-offline"
        receipt = m.verify_package(run_dir)
        assert receipt["profile"] == m.PROFILE
        assert receipt["label"] == m.LABEL
        assert receipt["candidate_sha256"] == m.CANDIDATE_SHA
        assert receipt["initrd_sha256"] == m.CPIO_SHA
        assert receipt["initrd_bytes"] == 453213884
        return {"profile": receipt["profile"], "label": receipt["label"],
                "package_root": receipt["package_root"],
                "candidate_sha256": receipt["candidate_sha256"],
                "cpio_sha256": receipt["initrd_sha256"]}

    def t_observation_budget():
        m = load_module("r44_observation", ROOT / "operator-helpers/recovery_observation.py")
        state, binding = source_state(60000)
        after = {**state, "performance_ms": 2100.0, "sequence": 2}
        m.valid_states(state, after, binding, "armed")
        bad, bad_binding = source_state(20000)
        try:
            m.valid_states(bad, {**bad, "performance_ms": 2100.0, "sequence": 2}, bad_binding, "armed")
            raise AssertionError("old 20s observation accepted")
        except ValueError as exc:
            assert "alarm_60s_browser_identity" in str(exc), str(exc)
        cancelled, cb = source_state(60000, "cancelled")
        m.valid_states(cancelled, {**cancelled, "sequence": 2}, cb, "cancelled")
        exact = {**cancelled, "alarm_due_exact_in_browser": False}
        try:
            m.valid_states(exact, {**exact, "sequence": 2}, cb, "cancelled")
            raise AssertionError("non-exact due accepted")
        except ValueError as exc:
            assert "alarm_60s_browser_identity" in str(exc), str(exc)
        expired = {**state, "performance_ms": 61000.0}
        try:
            m.valid_states(expired, {**expired, "sequence": 2}, binding, "armed")
            raise AssertionError("expired armed accepted")
        except ValueError as exc:
            assert "expired_alarm" in str(exc), str(exc)
        return {"new_budget_armed": "qualified", "old_budget": "alarm_60s_browser_identity",
                "cancelled": "qualified", "expired_armed": "rejected"}

    def t_cleanup_classifier():
        source = (ROOT / "runtime-wrapper/cleanup.py").read_text()
        tree = ast.parse(source)
        fn = next(node for node in tree.body
                  if isinstance(node, ast.FunctionDef) and node.name == "alarm_disposition")
        module = ast.Module(body=[fn], type_ignores=[])
        namespace = {"re": re, "math": math}
        exec(compile(module, "cleanup.py", "exec"), namespace)
        classify = namespace["alarm_disposition"]
        c = {"url": "http://127.0.0.1:60752/", "launch_id": "1" * 36}
        assert classify(alarm_value(), c) == "valid_nonarmed"
        assert classify(alarm_value(state="armed"), c) == "valid_armed_do_not_cancel_or_dispose"
        null = alarm_value()
        null["current"] = None
        null["events"] = []
        assert classify(null, c) == "valid_null_never_armed"
        assert classify(alarm_value(20000), c) == "unknown_malformed"
        assert classify(alarm_value(60000, due_delta=20000), c) == "unknown_malformed"
        bad = alarm_value()
        bad["expectedURL"] = "http://127.0.0.1:9/"
        assert classify(bad, c) == "unknown_malformed"
        bad_nonce = alarm_value()
        bad_nonce["current"]["nonce"] = "not-a-uuid"
        assert classify(bad_nonce, c) == "unknown_malformed"
        return {"new_budget": "valid_nonarmed", "old_budget": "unknown_malformed",
                "due_delta_old": "unknown_malformed", "foreign_url": "unknown_malformed"}

    def t_operate_assert():
        source = (ROOT / "runtime-wrapper/operate.py").read_text()
        tree = ast.parse(source)
        nodes = [node for node in ast.walk(tree)
                 if isinstance(node, ast.Assert) and "deadline_ms" in ast.unparse(node.test)]
        assert len(nodes) == 1, len(nodes)
        expression = compile(ast.Expression(nodes[0].test), "operate.py", "eval")
        arm = {"deadline_ms": 60000, "current": {"state": "armed", "nonce": "n"}}
        assert eval(expression, {"arm": arm, "nonce": "n"}) is True
        arm["deadline_ms"] = 20000
        assert eval(expression, {"arm": arm, "nonce": "n"}) is False
        return {"new_budget": "accepted", "old_budget": "rejected"}

    def t_delta():
        delta = json.loads((ROOT / "CANDIDATE-DELTA.json").read_text())
        assert delta["source_entries"] == 43 and delta["core_entries"] == 38
        assert delta["candidate_source43_sha256"] == sha(ROOT / "SOURCE-FREEZE.json")
        assert delta["candidate_core38_sha256"] == sha(ROOT / "CORE-SOURCE-FREEZE.json")
        assert any(row["path"] == "return-tools/return_adapter.py" for row in delta["changed"])
        return {"changed": len(delta["changed"]), "unchanged": delta["unchanged_count"]}

    def t_inputs():
        before = json.loads((ROOT / "INPUTS-BEFORE.json").read_text())
        after = json.loads((ROOT / "INPUTS-AFTER.json").read_text())
        assert before["r42_source_freeze_sha256"] == after["r42_source_freeze_sha256"]
        assert before["r42_core_freeze_sha256"] == after["r42_core_freeze_sha256"]
        assert before["r42_candidate_sha256"] == after["r42_candidate_sha256"]
        assert before["r42_cpio_sha256"] == after["r42_cpio_sha256"]
        assert before["r42_source_files"] == after["r42_source_files"]
        assert after["input_unchanged"] is True
        return {"r42_source_freeze_sha256": before["r42_source_freeze_sha256"],
                "r42_core_freeze_sha256": before["r42_core_freeze_sha256"],
                "r42_candidate_sha256": before["r42_candidate_sha256"],
                "r42_cpio_sha256": before["r42_cpio_sha256"]}

    def t_page_fixture():
        page = (ROOT / "tests/fixtures/PAGE-script.txt").read_bytes()
        digest = hashlib.sha256(page).hexdigest()
        assert digest == "852c83d673478a8f3db8a4d71989259c476a2325f2655a8dd3c8f8e46acfa55b"
        assert "const token=__TOKEN__;" in page.decode()
        return {"fixture_sha256": digest, "bytes": len(page)}

    def t_no_runtime_artifacts():
        forbidden_names = {"Start-once", "runtime.json", "deadline-install.json",
                           "runner-stdout.txt", "runner-stderr.txt", "trial-web-final-receipt.json"}
        found = []
        for path in ROOT.rglob("*"):
            if path.is_file() and path.name in forbidden_names:
                found.append(str(path.relative_to(ROOT)))
        assert not found, found
        return {"forbidden_runtime_artifacts": found, "no_qemu_or_browser_state": True}

    for name, fn in [
        ("source_freezes", t_source_freeze),
        ("adapter_pins", t_adapter_pins),
        ("budget_matrix", t_budget_matrix),
        ("preserved_boundaries", t_preserved_boundaries),
        ("selector_identity_and_package", t_selector),
        ("recovery_observation_budget", t_observation_budget),
        ("cleanup_alarm_classifier", t_cleanup_classifier),
        ("operate_budget_assert", t_operate_assert),
        ("candidate_delta", t_delta),
        ("input_before_after", t_inputs),
        ("page_fixture", t_page_fixture),
        ("no_runtime_artifacts", t_no_runtime_artifacts),
    ]:
        check(name, fn)

    passed = sum(1 for row in RESULTS if row["passed"])
    receipt = {
        "schema": "fx3-r44-python-pure-tests-v1",
        "candidate": str(ROOT),
        "offline": True,
        "browser": False,
        "server": False,
        "network": False,
        "VM": False,
        "QMP": False,
        "guest": False,
        "cases_total": len(RESULTS),
        "cases_passed": passed,
        "cases_failed": len(RESULTS) - passed,
        "results": RESULTS,
    }
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0 if passed == len(RESULTS) else 2


if __name__ == "__main__":
    raise SystemExit(main())
