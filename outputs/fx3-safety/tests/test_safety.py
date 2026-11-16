"""Unit tests for preflight.py Gate G12 Phase 28 upgrades & package exports."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

import fx3_safety
from fx3_safety.brick_classifier import generate_failsafe_init2_overlay_hook
from fx3_safety.preflight import TIER0_REQUIRED_BACKUPS, evaluate_12_safety_gates


REPO_ROOT = Path(__file__).resolve().parents[3]


def _make_valid_gate12_inputs():
    good_items = {
        k: {
            "bytes": spec.get("exact_bytes") or spec.get("min_bytes") or 4096,
            "pass1_sha256": "f" * 64,
            "pass2_sha256": "f" * 64,
        }
        for k, spec in TIER0_REQUIRED_BACKUPS.items()
    }
    manifest = {"camera_body_tag": "1" * 64, "model_id": "0x91030080", "items": good_items}
    trace = [{"nr": 35, "dirfd": -100, "path": "/tmp/jiritsu/libJit.so", "flags": 0, "ret": 0}]
    hook = generate_failsafe_init2_overlay_hook()
    return manifest, trace, hook


class SafetyPreflightGate12AndExportsTests(unittest.TestCase):
    def test_gate12_backward_compat_defaults_none_treated_as_allowed(self) -> None:
        manifest, trace, hook = _make_valid_gate12_inputs()
        rep = evaluate_12_safety_gates(
            REPO_ROOT,
            tier0_manifest=manifest,
            worker_syscall_trace=trace,
            init2_failsafe_hook=hook,
            candidate_bundle_verified=True,
            allow_dry_run_gate12=True,
        )
        self.assertEqual(rep["summary"]["verified_gates"], 12)
        self.assertTrue(rep["summary"]["all_12_gates_verified"])
        self.assertIsNone(rep["wireless_fault_isolation_ok"])
        self.assertIsNone(rep["runtime_antibrick_ok"])
        self.assertIsNone(rep["multiport_tier3_harness_ok"])
        self.assertFalse(rep["persistent_write_release"])

    def test_gate12_new_phase28_redlines_block_deterministically(self) -> None:
        manifest, trace, hook = _make_valid_gate12_inputs()
        cases = (
            (
                {
                    "wireless_fault_isolation_ok": False,
                    "runtime_antibrick_ok": True,
                    "multiport_tier3_harness_ok": True,
                },
                "BLOCKED_BY_WIRELESS_FAULT_ISOLATION_REDLINE",
            ),
            (
                {
                    "wireless_fault_isolation_ok": True,
                    "runtime_antibrick_ok": False,
                    "multiport_tier3_harness_ok": True,
                },
                "BLOCKED_BY_RUNTIME_ANTIBRICK_REDLINE",
            ),
            (
                {
                    "wireless_fault_isolation_ok": True,
                    "runtime_antibrick_ok": True,
                    "multiport_tier3_harness_ok": False,
                },
                "BLOCKED_BY_MULTIPORT_TIER3_HARNESS_REDLINE",
            ),
        )
        for flags, expected_status in cases:
            rep = evaluate_12_safety_gates(
                REPO_ROOT,
                tier0_manifest=manifest,
                worker_syscall_trace=trace,
                init2_failsafe_hook=hook,
                candidate_bundle_verified=True,
                allow_dry_run_gate12=True,
                **flags,
            )
            self.assertEqual(rep["summary"]["verified_gates"], 11)
            self.assertFalse(rep["summary"]["all_12_gates_verified"])
            self.assertFalse(rep["persistent_write_release"])
            g12 = [g for g in rep["gates"] if g["gate_id"] == "G12_persistent_flash_write_authorization"][0]
            self.assertEqual(g12["status"], expected_status)

    def test_fx3_safety_and_fx3_recovery_package_exports(self) -> None:
        for sym in (
            "run_h0_hardware_rehearsal",
            "H0RehearsalConfig",
            "H0RehearsalReport",
            "StageResult",
            "validate_rp2040_multiport_harness",
            "evaluate_runtime_antibrick_guards",
            "classify_brick_state",
            "evaluate_12_safety_gates",
        ):
            self.assertTrue(hasattr(fx3_safety, sym), f"Missing fx3_safety export: {sym}")

        recovery_root = REPO_ROOT / "outputs" / "fx3-recovery-adapter"
        if str(recovery_root) not in sys.path:
            sys.path.insert(0, str(recovery_root))
        import fx3_recovery

        for sym in (
            "MacOSUSBTransportSession",
            "SenserChallenge",
            "classify_senser_challenge",
            "audit_jiritsu_sequence",
            "autolocate_4_sites",
            "run_autolocated_p1_roundtrip",
            "build_synthetic_p1_elf64_libraries",
        ):
            self.assertTrue(hasattr(fx3_recovery, sym), f"Missing fx3_recovery export: {sym}")


if __name__ == "__main__":
    unittest.main()
