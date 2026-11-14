"""Phase 39 tests for the Stage-B Master Hardware Readiness Packet v2 (`stage_b_readiness_packet_v2`)."""

from __future__ import annotations

import copy
import io
import json
import os
import re
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import fx6_closure
from fx6_closure import __main__ as cli_main
from fx6_closure.hardware_readiness_packet import populate_tier0_capture_bundle_fixture
from fx6_closure.patcher import read_donor_bytes_readonly
from fx6_closure.stage_b_lifecycle_verifier import (
    DISPOSITION_ALLOWED_DEGRADED,
    DISPOSITION_FAIL_CLOSED_ABORT,
    DISPOSITION_PASS,
    STAGE_B_AIRPLANE_SHADOW_KEYS,
    STAGE_B_LIFECYCLE_SCHEMA,
    STAGE_B_SCENARIO_IDS,
)
from fx6_closure.uipc_completion_verifier import UIPC_BB_TARGET_QUEUE
from fx6_closure.stage_b_master_readiness_packet import (
    EXPECTED_STAGE_B_PATCH_SITE_COUNT,
    EXPECTED_STAGE_B_PATCH_SPEC_COUNT,
    EXPECTED_STAGE_B_SCENARIO_DISPOSITIONS,
    PHASE_39_VERSION,
    STAGE_B_MATRIX_13_ITEMS,
    STAGE_B_READINESS_PACKET_SCHEMA,
    StageBMasterPacketVerifyResult,
    StageBMasterReadinessPacketReport,
    _compute_packet_sha256,
    build_stage_b_gate_ordered_hardware_checklist,
    build_stage_b_master_readiness_packet,
    verify_stage_b_master_readiness_packet,
)


def _with_recomputed_sha256(pkt_dict: dict) -> dict:
    """Return a deep copy with a valid recomputed `packet_sha256` to verify semantic fail-closed checks."""
    mutated = copy.deepcopy(pkt_dict)
    mutated["packet_sha256"] = _compute_packet_sha256(mutated)
    return mutated


class TestPhase39StageBMasterReadinessPacket(unittest.TestCase):
    """Fast (<6s) deterministic & fail-closed verification for Phase 39 `stage_b_readiness_packet_v2`."""

    @classmethod
    def setUpClass(cls) -> None:
        t0 = time.monotonic()
        cls.packet = build_stage_b_master_readiness_packet()
        cls.build_elapsed_s = time.monotonic() - t0
        cls.packet_dict = cls.packet.to_dict()
        cls.packet_json_str = cls.packet.to_deterministic_json()
        cls.packet_json_dict = json.loads(cls.packet_json_str)

    def test_01_public_exports_and_constants(self) -> None:
        expected_exports = {
            "STAGE_B_READINESS_PACKET_SCHEMA",
            "PHASE_39_VERSION",
            "STAGE_B_MATRIX_13_ITEMS",
            "EXPECTED_STAGE_B_PATCH_SPEC_COUNT",
            "EXPECTED_STAGE_B_PATCH_SITE_COUNT",
            "EXPECTED_STAGE_B_SCENARIO_DISPOSITIONS",
            "StageBMasterReadinessPacketReport",
            "StageBMasterPacketVerifyResult",
            "build_stage_b_gate_ordered_hardware_checklist",
            "build_stage_b_master_readiness_packet",
            "verify_stage_b_master_readiness_packet",
        }
        self.assertTrue(expected_exports.issubset(set(fx6_closure.__all__)))
        self.assertEqual(STAGE_B_READINESS_PACKET_SCHEMA, "stage_b_readiness_packet_v2")
        self.assertEqual(PHASE_39_VERSION, "39.0.0")
        self.assertEqual(len(STAGE_B_MATRIX_13_ITEMS), 13)
        self.assertEqual(EXPECTED_STAGE_B_PATCH_SPEC_COUNT, 8)
        self.assertEqual(EXPECTED_STAGE_B_PATCH_SITE_COUNT, 18)

    def test_02_fast_execution_and_offline_complete(self) -> None:
        self.assertLess(self.build_elapsed_s, 5.0)
        self.assertIsInstance(self.packet, StageBMasterReadinessPacketReport)
        self.assertTrue(self.packet.offline_engineering_complete)
        self.assertEqual(self.packet.errors, ())
        self.assertIn(
            self.packet.verification_mode,
            ("LOCAL_DONOR_AND_POSIX_SANDBOX_VERIFIED", "CLEAN_ROOM_SYNTHETIC_VERIFIED"),
        )

    def test_03_hard_locked_zero_write_and_hardware_release_redlines(self) -> None:
        self.assertFalse(self.packet.persistent_emmc_writes_authorized)
        self.assertFalse(self.packet.persistent_write_release)
        self.assertTrue(self.packet.p8_cp_mutation_forbidden)
        self.assertEqual(self.packet.cp_mutation_bytes, 0)
        self.assertTrue(self.packet.wbi_p5_write_and_hibernation_forbidden)
        self.assertEqual(self.packet.wbi_mutation_bytes, 0)
        self.assertEqual(self.packet.usb_or_camera_operations, 0)
        self.assertFalse(self.packet.real_tier0_hardware_backup_verified)
        self.assertFalse(self.packet.stage_b_ram_trial_hardware_go)
        self.assertIsNone(self.packet.tier0_bundle_audit)

    def test_04_self_authenticating_sha256_and_zero_raw_bytes_repr(self) -> None:
        self.assertEqual(len(self.packet.packet_sha256), 64)
        self.assertEqual(
            _compute_packet_sha256(self.packet_dict),
            _compute_packet_sha256(self.packet_json_dict),
        )
        self.assertEqual(self.packet.packet_sha256, _compute_packet_sha256(self.packet_json_dict))
        self.assertNotIn("b'", self.packet_json_str)
        self.assertIsNone(re.search(r'(?<![0-9A-Za-z_])b["\']', self.packet_json_str))

        v_dict = verify_stage_b_master_readiness_packet(self.packet_dict)
        v_json = verify_stage_b_master_readiness_packet(self.packet_json_dict)
        self.assertIsInstance(v_dict, StageBMasterPacketVerifyResult)
        self.assertTrue(v_dict.valid, msg=f"dict verify errors: {v_dict.errors}")
        self.assertTrue(v_json.valid, msg=f"json verify errors: {v_json.errors}")
        self.assertEqual(v_dict.errors, ())
        self.assertEqual(v_json.errors, ())

    def test_05_read_donor_bytes_readonly_strictly_o_rdonly(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            sample = Path(td) / "donor_ro.bin"
            sample.write_bytes(b"\x7fELF" + b"\x00" * 12)
            seen_flags = []
            real_open = os.open

            def _spy_open(path: str, flags: int, *args: object) -> int:
                seen_flags.append(flags)
                return real_open(path, flags, *args)

            with mock.patch("fx6_closure.patcher.os.open", side_effect=_spy_open):
                data = read_donor_bytes_readonly(sample)

            self.assertEqual(data.hex(), (b"\x7fELF" + b"\x00" * 12).hex())
            self.assertEqual(seen_flags, [os.O_RDONLY])

    def test_06_stage_b_p1_to_p12_and_fan_matrix_coverage(self) -> None:
        mat = self.packet.stage_b_p1_to_p12_and_fan_matrix
        self.assertTrue(mat["all_13_items_verified"])
        self.assertEqual(mat["matrix_item_count"], 13)
        self.assertEqual(list(mat["verified_matrix_items"]), list(STAGE_B_MATRIX_13_ITEMS))
        self.assertEqual(mat["patch_spec_count"], EXPECTED_STAGE_B_PATCH_SPEC_COUNT)
        self.assertEqual(mat["total_patch_sites"], EXPECTED_STAGE_B_PATCH_SITE_COUNT)
        self.assertTrue(mat["rollback_all_matched"])
        for receipt in mat["patch_receipts"]:
            self.assertTrue(receipt["rollback_verified"])
            self.assertTrue(receipt["non_overlapping"])

    def test_07_p2_vfat_p5_p6_uipc_and_p7_sync100(self) -> None:
        mat = self.packet.stage_b_p1_to_p12_and_fan_matrix
        self.assertTrue(mat["p2_opelog_vfat"]["valid"])
        self.assertEqual(mat["p2_opelog_vfat"]["total_bytes"], 8 * 1024 * 1024)
        self.assertTrue(mat["p5_p6_uipc_completion"]["verified"])
        self.assertEqual(mat["p5_p6_uipc_completion"]["queue_hex"], hex(UIPC_BB_TARGET_QUEUE))
        self.assertEqual(mat["p5_p6_uipc_completion"]["opcode_count"], 5)
        self.assertTrue(mat["p7_dual_kernel_sync100_verified"])

    def test_08_p10_keymap_and_p11_uipc_cp_smart_handle_xlr_h1(self) -> None:
        mat = self.packet.stage_b_p1_to_p12_and_fan_matrix
        p10 = mat["p10_keymap"]
        self.assertTrue(p10["verified"])
        self.assertTrue(p10["zero_byte_overlap"])
        self.assertTrue(p10["native_1to1_passed"])
        self.assertTrue(p10["remapped_passed"])
        self.assertEqual(p10["total_site_count"], 10)
        if self.packet.verification_mode == "LOCAL_DONOR_AND_POSIX_SANDBOX_VERIFIED":
            self.assertEqual(p10["appfw_stage_b_sha256"], p10["expected_production_sha256"])

        p11 = mat["p11_uipc_cp_shim"]
        self.assertTrue(p11["verified"])
        self.assertTrue(p11["p8_cp_mutation_forbidden"])
        self.assertEqual(p11["cp_mutation_bytes"], 0)
        self.assertTrue(p11["xlr_h1_preserved"])
        self.assertEqual(p11["smart_handle_queue_hex"], "0x91db059b")
        self.assertEqual(p11["rtc_queue_hex"], "0x92d2091c")
        self.assertEqual(p11["hotshoe_vma"], "0x5d90")
        self.assertEqual(set(p11["fx6_exclusive_blocking_queues"]), {"0x92d2091c", "0x91db059b"})

    def test_09_p12_wf12_bootloop_guard_and_bk4_airplane_shadow(self) -> None:
        p12 = self.packet.stage_b_p1_to_p12_and_fan_matrix["p12_wireless_guard"]
        self.assertTrue(p12["verified"])
        self.assertEqual(p12["guard_vma"], "0x70d4")
        self.assertEqual(p12["patched_rc"], 0)
        self.assertTrue(p12["rollback_verified"])
        self.assertTrue(p12["bk4_airplane_shadow_valid"])
        self.assertEqual(p12["airplane_shadow_keys"], STAGE_B_AIRPLANE_SHADOW_KEYS)
        self.assertEqual(p12["wbi_mutation_bytes"], 0)
        self.assertEqual(p12["cp_mutation_bytes"], 0)
        self.assertEqual(p12["nvram_persistent_writes"], 0)

    def test_10_phase35_lifecycle_10_scenarios_and_dispositions(self) -> None:
        p35 = self.packet.phase35_stage_b_lifecycle
        self.assertEqual(p35["schema"], STAGE_B_LIFECYCLE_SCHEMA)
        self.assertTrue(p35["all_checks_passed"])
        self.assertEqual(p35["scenario_count"], 10)
        self.assertEqual(p35["passed_scenario_count"], 10)
        self.assertTrue(p35["h2_zero_drift_verified"])
        self.assertEqual(p35["h2_persistent_bytes_mutated"], 0)
        self.assertTrue(p35["temp_dir_cleaned"])
        self.assertEqual(
            p35["serial_fault_detector_v2_dispositions"],
            {"pass": 1, "allowed_degraded": 3, "fail_closed_abort": 6},
        )
        observed_ids = tuple(sc["scenario_id"] for sc in p35["scenarios"])
        self.assertEqual(observed_ids, STAGE_B_SCENARIO_IDS)
        for sc in p35["scenarios"]:
            self.assertEqual(sc["serial_disposition"], EXPECTED_STAGE_B_SCENARIO_DISPOSITIONS[sc["scenario_id"]])
            self.assertTrue(sc["zero_cp_writes"])
            self.assertTrue(sc["zero_nvram_writes"])

    def test_11_phase28_h0_rehearsal_and_12_safety_gates(self) -> None:
        p28 = self.packet.phase28_h0_hardware_rehearsal
        self.assertTrue(p28["all_passed"])
        self.assertTrue(p28["ready_for_physical_h0_capture"])
        self.assertEqual(p28["stage_count"], 6)
        self.assertEqual(p28["passed_stage_count"], 6)
        self.assertFalse(p28["persistent_emmc_writes_authorized"])
        self.assertFalse(p28["persistent_write_release"])

        gates = self.packet.preflight_safety_gates
        self.assertTrue(gates["offline_dry_run_all_12_gates_verified"])
        self.assertEqual(gates["offline_dry_run_verified_gate_count"], 12)
        self.assertEqual(gates["offline_dry_run_blocked_gate_ids"], [])
        self.assertFalse(gates["live_hardware_persistent_write_release"])

    def test_12_phase38_multiport_mishoe_crsdk_spacc_guards(self) -> None:
        p38 = self.packet.phase38_crsdk_mishoe_ltc_spacc_guard
        self.assertTrue(p38["all_passed"])
        self.assertEqual(p38["status"], "VERIFIED_SAFE")
        self.assertFalse(p38["persistent_emmc_writes_authorized"])
        self.assertFalse(p38["persistent_write_release"])

        self.assertTrue(p38["ltc_guard"]["valid"])
        self.assertEqual(tuple(p38["ltc_guard"]["uart_boot_protected_pins"]), (7, 8, 9))
        self.assertTrue(p38["mishoe_guard"]["valid"])
        self.assertTrue(p38["mishoe_guard"]["xlr_h1_preserved"])
        self.assertTrue(p38["mishoe_guard"]["libinfrahotshoe_timeout_safe"])
        self.assertTrue(p38["crsdk_firewall"]["valid"])
        self.assertEqual(p38["crsdk_firewall"]["vendor_extension_id_hex"], "0x11")
        self.assertTrue(p38["crsdk_firewall"]["sdio_handshake_complete"])
        self.assertTrue(p38["spacc_guard"]["valid"])
        self.assertGreaterEqual(p38["spacc_guard"]["xts_partitions_count"], 1)
        self.assertGreaterEqual(p38["spacc_guard"]["plaintext_partitions_count"], 1)

    def test_13_phase25_runtime_antibrick_guards(self) -> None:
        p25 = self.packet.phase25_runtime_antibrick_guards
        self.assertTrue(p25["all_passed"])
        self.assertEqual(p25["status"], "VERIFIED_SAFE")
        self.assertFalse(p25["persistent_emmc_writes_authorized"])
        self.assertTrue(p25["ld_so_preload_ban"]["valid"])
        self.assertTrue(p25["ld_so_preload_ban"]["dynamic_busybox_deadlock_blocked"])
        self.assertTrue(p25["dd_truncation_ban_and_5step"]["valid"])
        self.assertTrue(p25["nflasha10_0x10000009_headroom"]["valid"])
        self.assertEqual(p25["nflasha10_0x10000009_headroom"]["error_code"], "0x10000009")
        self.assertTrue(p25["product_model_nvram_immutability"]["valid"])
        self.assertEqual(p25["product_model_nvram_immutability"]["nvram_persistent_writes"], 0)

    def test_14_byof_parity_and_gate_ordered_checklist(self) -> None:
        byof = self.packet.byof_manifest_parity
        self.assertTrue(byof["all_checks_passed"])
        self.assertEqual(byof["en_entry_count"], 57)
        self.assertEqual(byof["zh_entry_count"], 57)
        self.assertTrue(byof["en_zh_parity_ok"])
        self.assertTrue(byof["zero_stage_reference_ok"])

        chk = build_stage_b_gate_ordered_hardware_checklist()
        self.assertEqual(len(chk), 3)
        for step in chk:
            self.assertEqual(step.emmc_write_bytes_allowed, 0)
            self.assertEqual(step.nor_write_bytes_allowed, 0)
            self.assertEqual(step.wbi_p5_write_bytes_allowed, 0)
            self.assertEqual(step.cp_p8_write_bytes_allowed, 0)

    def test_15_default_skips_165s_full_dry_run_and_opt_in_is_supported(self) -> None:
        self.assertFalse(self.packet.full_candidate_dry_run["included"])
        mock_dry = mock.MagicMock(
            candidate_ready=True,
            all_12_gates_verified=True,
            verified_gate_count=12,
            blocked_gate_ids=(),
            stage_b_combined_appfw_verified=True,
            stage_b_appfw_sha256="a" * 64,
            stage_b_wlan_rsrc_sha256="b" * 64,
            stage_a_overlay_cpio_sha256="c" * 64,
            uipc_cp_shim_ok=True,
            wireless_fault_isolation_ok=True,
        )
        fake_scenarios = [
            mock.MagicMock(
                scenario_id=sid,
                passed=True,
                status="POST_TRIAL_DRIFT_DETECTED" if sid == "S10_POST_TRIAL_DRIFT_DETECTION" else "VERIFIED_PASS",
                phase_scope="H0_H1_H2",
                expected_disposition=EXPECTED_STAGE_B_SCENARIO_DISPOSITIONS[sid],
                observed_disposition=EXPECTED_STAGE_B_SCENARIO_DISPOSITIONS[sid],
                serial_disposition=EXPECTED_STAGE_B_SCENARIO_DISPOSITIONS[sid],
                watchdog_passed=True,
                clear_before_exec_ok=True,
                verify_before_mount_ok=True,
                lifo_teardown_ok=True,
                zero_emmc_writes=True,
                zero_wbi_writes=True,
                zero_cp_writes=True,
                zero_nvram_writes=True,
                persistent_bytes_mutated=1 if sid == "S10_POST_TRIAL_DRIFT_DETECTION" else 0,
                drifted_items=("p12_cert",) if sid == "S10_POST_TRIAL_DRIFT_DETECTION" else (),
                diag_code="OK",
            )
            for sid in STAGE_B_SCENARIO_IDS
        ]
        with mock.patch(
            "fx6_closure.stage_b_master_readiness_packet.run_stage_b_lifecycle_drill"
        ) as m_p35:
            m_p35.return_value = mock.MagicMock(
                schema=STAGE_B_LIFECYCLE_SCHEMA,
                phase_version="35.0.0",
                verification_mode="CLEAN_ROOM_SYNTHETIC_VERIFIED",
                all_checks_passed=True,
                persistent_emmc_writes_authorized=False,
                persistent_write_release=False,
                p8_cp_mutation_forbidden=True,
                wbi_p5_write_and_hibernation_forbidden=True,
                temp_dir_cleaned=True,
                h0_bundle_valid=True,
                h2_zero_drift_verified=True,
                h2_audited_item_count=13,
                h2_persistent_bytes_mutated=0,
                h2_receipt_sha256="e" * 64,
                report_sha256="f" * 64,
                scenario_count=10,
                passed_scenario_count=10,
                scenarios=fake_scenarios,
                errors=(),
            )
            pkt_opt = build_stage_b_master_readiness_packet(
                synthetic_clean_room=True,
                include_full_candidate_dry_run=True,
                precomputed_dry_run=mock_dry,
            )
        self.assertTrue(pkt_opt.full_candidate_dry_run["included"])
        self.assertTrue(pkt_opt.full_candidate_dry_run["candidate_ready"])
        self.assertTrue(verify_stage_b_master_readiness_packet(pkt_opt.to_dict()).valid)

    def test_16_tier0_real_bundle_unlocks_ram_trial_go_only_and_rejects_synthetic_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            real_dir = Path(td) / "real_tier0"
            populate_tier0_capture_bundle_fixture(real_dir, synthetic_flag=False)
            synth_dir = Path(td) / "synth_tier0"
            populate_tier0_capture_bundle_fixture(
                synth_dir,
                capture_origin="synthetic_fixture",
                synthetic_flag=True,
            )

            with mock.patch(
                "fx6_closure.stage_b_master_readiness_packet.run_stage_b_lifecycle_drill"
            ) as m_p35:
                fake_scenarios = [
                    mock.MagicMock(
                        scenario_id=sid,
                        passed=True,
                        status="POST_TRIAL_DRIFT_DETECTED" if sid == "S10_POST_TRIAL_DRIFT_DETECTION" else "VERIFIED_PASS",
                        phase_scope="H0_H1_H2",
                        expected_disposition=EXPECTED_STAGE_B_SCENARIO_DISPOSITIONS[sid],
                        observed_disposition=EXPECTED_STAGE_B_SCENARIO_DISPOSITIONS[sid],
                        serial_disposition=EXPECTED_STAGE_B_SCENARIO_DISPOSITIONS[sid],
                        watchdog_passed=True,
                        clear_before_exec_ok=True,
                        verify_before_mount_ok=True,
                        lifo_teardown_ok=True,
                        zero_emmc_writes=True,
                        zero_wbi_writes=True,
                        zero_cp_writes=True,
                        zero_nvram_writes=True,
                        persistent_bytes_mutated=1 if sid == "S10_POST_TRIAL_DRIFT_DETECTION" else 0,
                        drifted_items=("p12_cert",) if sid == "S10_POST_TRIAL_DRIFT_DETECTION" else (),
                        diag_code="OK",
                    )
                    for sid in STAGE_B_SCENARIO_IDS
                ]
                m_p35.return_value = mock.MagicMock(
                    schema=STAGE_B_LIFECYCLE_SCHEMA,
                    phase_version="35.0.0",
                    verification_mode="CLEAN_ROOM_SYNTHETIC_VERIFIED",
                    all_checks_passed=True,
                    persistent_emmc_writes_authorized=False,
                    persistent_write_release=False,
                    p8_cp_mutation_forbidden=True,
                    wbi_p5_write_and_hibernation_forbidden=True,
                    temp_dir_cleaned=True,
                    h0_bundle_valid=True,
                    h2_zero_drift_verified=True,
                    h2_audited_item_count=13,
                    h2_persistent_bytes_mutated=0,
                    h2_receipt_sha256="e" * 64,
                    report_sha256="f" * 64,
                    scenario_count=10,
                    passed_scenario_count=10,
                    scenarios=fake_scenarios,
                    errors=(),
                )
                pkt_real = build_stage_b_master_readiness_packet(
                    tier0_bundle_dir=real_dir,
                    synthetic_clean_room=True,
                )
                pkt_synth = build_stage_b_master_readiness_packet(
                    tier0_bundle_dir=synth_dir,
                    synthetic_clean_room=True,
                )

            self.assertTrue(pkt_real.real_tier0_hardware_backup_verified)
            self.assertTrue(pkt_real.stage_b_ram_trial_hardware_go)
            self.assertFalse(pkt_real.persistent_emmc_writes_authorized)
            self.assertFalse(pkt_real.persistent_write_release)
            self.assertTrue(verify_stage_b_master_readiness_packet(pkt_real.to_dict()).valid)

            self.assertFalse(pkt_synth.real_tier0_hardware_backup_verified)
            self.assertFalse(pkt_synth.stage_b_ram_trial_hardware_go)
            self.assertFalse(pkt_synth.offline_engineering_complete)
            self.assertGreater(len(pkt_synth.errors), 0)
            self.assertFalse(verify_stage_b_master_readiness_packet(pkt_synth.to_dict()).valid)

    def test_17_tamper_non_mapping_and_bad_sha256(self) -> None:
        bad_type = verify_stage_b_master_readiness_packet(["not-a-dict"])  # type: ignore[arg-type]
        self.assertFalse(bad_type.valid)

        tampered = copy.deepcopy(self.packet_json_dict)
        tampered["packet_sha256"] = "0" * 64
        res = verify_stage_b_master_readiness_packet(tampered)
        self.assertFalse(res.valid)
        self.assertFalse(res.sha256_matched)

    def test_18_tamper_persistent_emmc_and_write_release_even_with_recomputed_sha(self) -> None:
        for field in ("persistent_emmc_writes_authorized", "persistent_write_release"):
            tampered = copy.deepcopy(self.packet_json_dict)
            tampered[field] = True
            res = verify_stage_b_master_readiness_packet(_with_recomputed_sha256(tampered))
            self.assertFalse(res.valid, msg=field)
            self.assertFalse(res.safety_redlines_ok, msg=field)

    def test_19_tamper_cp_and_wbi_mutation_bytes_even_with_recomputed_sha(self) -> None:
        for field in ("cp_mutation_bytes", "wbi_mutation_bytes", "usb_or_camera_operations"):
            tampered = copy.deepcopy(self.packet_json_dict)
            tampered[field] = 4
            res = verify_stage_b_master_readiness_packet(_with_recomputed_sha256(tampered))
            self.assertFalse(res.valid, msg=field)
            self.assertFalse(res.safety_redlines_ok, msg=field)

    def test_20_tamper_p12_wireless_guard_or_bk4_shadow_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.packet_json_dict)
        tampered["stage_b_p1_to_p12_and_fan_matrix"]["p12_wireless_guard"]["patched_rc"] = -1
        res1 = verify_stage_b_master_readiness_packet(_with_recomputed_sha256(tampered))
        self.assertFalse(res1.valid)
        self.assertFalse(res1.stage_b_matrix_ok)

        tampered2 = copy.deepcopy(self.packet_json_dict)
        tampered2["stage_b_p1_to_p12_and_fan_matrix"]["p12_wireless_guard"]["bk4_airplane_shadow_valid"] = False
        res2 = verify_stage_b_master_readiness_packet(_with_recomputed_sha256(tampered2))
        self.assertFalse(res2.valid)
        self.assertFalse(res2.stage_b_matrix_ok)

    def test_21_tamper_p11_cp_shim_or_rollback_receipt_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.packet_json_dict)
        tampered["stage_b_p1_to_p12_and_fan_matrix"]["p11_uipc_cp_shim"]["xlr_h1_preserved"] = False
        res1 = verify_stage_b_master_readiness_packet(_with_recomputed_sha256(tampered))
        self.assertFalse(res1.valid)
        self.assertFalse(res1.stage_b_matrix_ok)

        tampered2 = copy.deepcopy(self.packet_json_dict)
        tampered2["stage_b_p1_to_p12_and_fan_matrix"]["patch_receipts"][0]["rollback_verified"] = False
        res2 = verify_stage_b_master_readiness_packet(_with_recomputed_sha256(tampered2))
        self.assertFalse(res2.valid)
        self.assertFalse(res2.stage_b_matrix_ok)

    def test_22_tamper_phase35_scenarios_s04_or_s10_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.packet_json_dict)
        # S04 is index 3 (must remain ALLOWED_DEGRADED with zero writes)
        tampered["phase35_stage_b_lifecycle"]["scenarios"][3]["serial_disposition"] = DISPOSITION_PASS
        res1 = verify_stage_b_master_readiness_packet(_with_recomputed_sha256(tampered))
        self.assertFalse(res1.valid)
        self.assertFalse(res1.phase35_lifecycle_ok)

        tampered2 = copy.deepcopy(self.packet_json_dict)
        # S10 is index 9 (must report POST_TRIAL_DRIFT_DETECTED and drifted_items)
        tampered2["phase35_stage_b_lifecycle"]["scenarios"][9]["drifted_items"] = []
        res2 = verify_stage_b_master_readiness_packet(_with_recomputed_sha256(tampered2))
        self.assertFalse(res2.valid)
        self.assertFalse(res2.phase35_lifecycle_ok)

    def test_23_tamper_phase28_h0_and_preflight_gates_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.packet_json_dict)
        tampered["preflight_safety_gates"]["live_hardware_persistent_write_release"] = True
        res1 = verify_stage_b_master_readiness_packet(_with_recomputed_sha256(tampered))
        self.assertFalse(res1.valid)
        self.assertFalse(res1.phase28_h0_ok)

        tampered2 = copy.deepcopy(self.packet_json_dict)
        tampered2["phase28_h0_hardware_rehearsal"]["passed_stage_count"] = 5
        res2 = verify_stage_b_master_readiness_packet(_with_recomputed_sha256(tampered2))
        self.assertFalse(res2.valid)
        self.assertFalse(res2.phase28_h0_ok)

    def test_24_tamper_phase38_multiport_mishoe_crsdk_spacc_fails_closed(self) -> None:
        for section in ("ltc_guard", "mishoe_guard", "crsdk_firewall", "spacc_guard"):
            tampered = copy.deepcopy(self.packet_json_dict)
            tampered["phase38_crsdk_mishoe_ltc_spacc_guard"][section]["valid"] = False
            res = verify_stage_b_master_readiness_packet(_with_recomputed_sha256(tampered))
            self.assertFalse(res.valid, msg=section)
            self.assertFalse(res.phase38_guards_ok, msg=section)

    def test_25_tamper_phase25_antibrick_and_byof_parity_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.packet_json_dict)
        tampered["phase25_runtime_antibrick_guards"]["ld_so_preload_ban"]["valid"] = False
        res1 = verify_stage_b_master_readiness_packet(_with_recomputed_sha256(tampered))
        self.assertFalse(res1.valid)
        self.assertFalse(res1.phase25_antibrick_ok)

        tampered2 = copy.deepcopy(self.packet_json_dict)
        tampered2["byof_manifest_parity"]["en_zh_parity_ok"] = False
        res2 = verify_stage_b_master_readiness_packet(_with_recomputed_sha256(tampered2))
        self.assertFalse(res2.valid)
        self.assertFalse(res2.byof_parity_ok)

    def test_26_tamper_checklist_write_budget_and_hardware_go_consistency(self) -> None:
        tampered = copy.deepcopy(self.packet_json_dict)
        tampered["gate_ordered_hardware_execution_checklist"][1]["emmc_write_bytes_allowed"] = 512
        res1 = verify_stage_b_master_readiness_packet(_with_recomputed_sha256(tampered))
        self.assertFalse(res1.valid)
        self.assertFalse(res1.checklist_zero_write_ok)

        tampered2 = copy.deepcopy(self.packet_json_dict)
        tampered2["stage_b_ram_trial_hardware_go"] = True
        res2 = verify_stage_b_master_readiness_packet(_with_recomputed_sha256(tampered2))
        self.assertFalse(res2.valid)
        self.assertFalse(res2.tier0_bundle_ok)

    def test_27_cli_build_stage_b_readiness_packet_json_and_output(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_path = Path(td) / "stage_b_master.json"
            buf = io.StringIO()
            with mock.patch(
                "fx6_closure.stage_b_master_readiness_packet.build_stage_b_master_readiness_packet",
                return_value=self.packet,
            ):
                with redirect_stdout(buf):
                    rc = cli_main.main(
                        ["build-stage-b-readiness-packet", "--clean-room", "--json", "--output", str(out_path)]
                    )
            self.assertEqual(rc, 0)
            self.assertTrue(out_path.is_file())
            written_text = out_path.read_text(encoding="utf-8")
            self.assertEqual(buf.getvalue(), written_text)
            parsed = json.loads(written_text)
            self.assertEqual(parsed["schema"], STAGE_B_READINESS_PACKET_SCHEMA)
            self.assertTrue(verify_stage_b_master_readiness_packet(parsed).valid)
            self.assertNotIn("b'", written_text)


if __name__ == "__main__":
    unittest.main()
