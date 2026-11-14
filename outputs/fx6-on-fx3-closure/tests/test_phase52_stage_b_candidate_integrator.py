"""Phase 52 tests for Unified Stage-B End-to-End Candidate Integrator (`stage_b_integrated_dossier_v1`)."""

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
from fx3_recovery.emmc_dump_forensic_verifier import (
    FORENSIC_VERIFIER_SCHEMA,
    WBI2_HEADER_SIZE,
    WBI2_MAGIC,
    build_synthetic_p5_wbi2_image,
    verify_emmc_dump_bytes,
)
from fx3_recovery.unbrick_ladder_and_capsule_verifier import UNBRICK_LADDER_SCHEMA
from fx3_safety.master_16gate_preflight import MASTER_16GATE_PREFLIGHT_SCHEMA
from fx6_closure import __main__ as cli_main
from fx6_closure.patcher import read_donor_bytes_readonly
from fx6_closure.stage_b_candidate_integrator import (
    CALIBRATION_MUTATION_BYTES,
    CP_MUTATION_BYTES,
    DONOR_FORENSIC_DUMP_SPECS,
    DONOR_P5_WBI2_RELPATH,
    FORENSIC_REQUIRED_ROLES,
    P8_CP_MUTATION_FORBIDDEN,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE_52_VERSION,
    STAGE_B_CANDIDATE_DOSSIER_SCHEMA,
    STAGE_B_CANDIDATE_PILLARS,
    USB_OR_CAMERA_OPERATIONS,
    WBI_MUTATION_BYTES,
    WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN,
    StageBCandidateVerifyResult,
    StageBIntegratedDossierReport,
    _compute_dossier_sha256,
    build_stage_b_integrated_dossier,
    verify_stage_b_integrated_dossier,
)
from fx6_closure.stage_b_master_readiness_packet import STAGE_B_READINESS_PACKET_SCHEMA
from fx6_closure.stage_b_ram_overlay_packager import (
    PHASE_48_SCHEMA,
    STAGE_B_BK_LANG_SPECS,
    STAGE_B_SUPPORTED_LANGS,
    STAGE_B_TMPFS_BUDGET_LIMIT_MIB,
)


RAW_BYTES_REPR_REGEX = r'(?<![0-9A-Za-z_/.-])b[\'"]'


def _with_recomputed_dossier_sha256(dossier_dict: dict) -> dict:
    """Return a deep copy with valid recomputed `dossier_sha256` to test fail-closed semantics."""
    mutated = copy.deepcopy(dossier_dict)
    mutated["dossier_sha256"] = _compute_dossier_sha256(mutated)
    return mutated


class TestPhase52StageBCandidateIntegrator(unittest.TestCase):
    """Fast (<6s) dual-mode & fail-closed verification for `stage_b_integrated_dossier_v1`."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.recorded_opens: list[tuple[str, int]] = []
        real_open = os.open

        def _spy_open(path: object, flags: int, *args: object, **kwargs: object) -> int:
            cls.recorded_opens.append((str(path), flags))
            return real_open(path, flags, *args, **kwargs)  # type: ignore[arg-type]

        t0 = time.monotonic()
        with (
            mock.patch("fx6_closure.stage_b_candidate_integrator.os.open", side_effect=_spy_open),
            mock.patch("fx3_recovery.emmc_dump_forensic_verifier.os.open", side_effect=_spy_open),
            mock.patch("fx6_closure.patcher.os.open", side_effect=_spy_open),
        ):
            cls.dossier = build_stage_b_integrated_dossier()
        cls.build_elapsed_s = time.monotonic() - t0
        cls.dossier_dict = cls.dossier.to_dict()
        cls.dossier_json_str = cls.dossier.to_deterministic_json()
        cls.dossier_json_dict = json.loads(cls.dossier_json_str)

    def test_01_public_exports_and_constants(self) -> None:
        expected_exports = {
            "CALIBRATION_MUTATION_BYTES",
            "CP_MUTATION_BYTES",
            "DONOR_FORENSIC_DUMP_SPECS",
            "DONOR_P5_WBI2_RELPATH",
            "FORENSIC_REQUIRED_ROLES",
            "P8_CP_MUTATION_FORBIDDEN",
            "PERSISTENT_EMMC_WRITES_AUTHORIZED",
            "PERSISTENT_WRITE_RELEASE",
            "PHASE_52_VERSION",
            "STAGE_B_CANDIDATE_DOSSIER_SCHEMA",
            "STAGE_B_CANDIDATE_PILLARS",
            "USB_OR_CAMERA_OPERATIONS",
            "WBI_MUTATION_BYTES",
            "WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN",
            "StageBCandidateVerifyResult",
            "StageBIntegratedDossierReport",
            "build_stage_b_integrated_dossier",
            "verify_stage_b_integrated_dossier",
        }
        self.assertTrue(expected_exports.issubset(set(fx6_closure.__all__)))
        self.assertEqual(STAGE_B_CANDIDATE_DOSSIER_SCHEMA, "stage_b_integrated_dossier_v1")
        self.assertEqual(PHASE_52_VERSION, "52.0.0")
        self.assertEqual(len(STAGE_B_CANDIDATE_PILLARS), 5)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertTrue(P8_CP_MUTATION_FORBIDDEN)
        self.assertTrue(WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN)
        self.assertEqual(CP_MUTATION_BYTES, 0)
        self.assertEqual(WBI_MUTATION_BYTES, 0)
        self.assertEqual(CALIBRATION_MUTATION_BYTES, 0)
        self.assertEqual(USB_OR_CAMERA_OPERATIONS, 0)

    def test_02_fast_execution_and_candidate_ready(self) -> None:
        self.assertLess(self.build_elapsed_s, 5.0)
        self.assertIsInstance(self.dossier, StageBIntegratedDossierReport)
        self.assertEqual(self.dossier.schema, STAGE_B_CANDIDATE_DOSSIER_SCHEMA)
        self.assertEqual(self.dossier.phase_version, PHASE_52_VERSION)
        self.assertEqual(self.dossier.selected_lang, "en")
        self.assertTrue(self.dossier.all_5_pillars_passed)
        self.assertTrue(self.dossier.candidate_ready)
        self.assertEqual(self.dossier.pillar_count, 5)
        self.assertEqual(self.dossier.passed_pillar_count, 5)
        self.assertEqual(self.dossier.status, "VERIFIED_STAGE_B_CANDIDATE_OFFLINE_READY")
        self.assertEqual(self.dossier.errors, ())
        self.assertIn(self.dossier.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))

    def test_03_hard_locked_zero_write_and_immutability_redlines(self) -> None:
        self.assertFalse(self.dossier.persistent_emmc_writes_authorized)
        self.assertFalse(self.dossier.persistent_write_release)
        self.assertTrue(self.dossier.p8_cp_mutation_forbidden)
        self.assertEqual(self.dossier.cp_mutation_bytes, 0)
        self.assertTrue(self.dossier.wbi_p5_write_and_hibernation_forbidden)
        self.assertEqual(self.dossier.wbi_mutation_bytes, 0)
        self.assertEqual(self.dossier.calibration_mutation_bytes, 0)
        self.assertEqual(self.dossier.usb_or_camera_operations, 0)

    def test_04_self_authenticating_dossier_sha256_and_zero_raw_bytes_repr(self) -> None:
        self.assertIsNotNone(re.fullmatch(r"[0-9a-f]{64}", self.dossier.dossier_sha256))
        self.assertEqual(
            _compute_dossier_sha256(self.dossier_dict),
            _compute_dossier_sha256(self.dossier_json_dict),
        )
        self.assertEqual(self.dossier.dossier_sha256, _compute_dossier_sha256(self.dossier_json_dict))
        self.assertNotRegex(self.dossier_json_str, RAW_BYTES_REPR_REGEX)

        v_dict = verify_stage_b_integrated_dossier(self.dossier_dict)
        v_json = verify_stage_b_integrated_dossier(self.dossier_json_dict)
        self.assertIsInstance(v_dict, StageBCandidateVerifyResult)
        self.assertTrue(v_dict.valid, msg=f"dict verify errors: {v_dict.errors}")
        self.assertTrue(v_json.valid, msg=f"json verify errors: {v_json.errors}")
        self.assertTrue(v_dict.sha256_matched)
        self.assertTrue(v_dict.safety_redlines_ok)
        self.assertTrue(v_dict.phase50_16gate_ok)
        self.assertTrue(v_dict.phase48_ram_overlay_ok)
        self.assertTrue(v_dict.phase47_unbrick_capsule_ok)
        self.assertTrue(v_dict.phase42_forensic_gate_ok)
        self.assertTrue(v_dict.phase39_readiness_ok)
        self.assertEqual(v_dict.errors, ())

    def test_05_pillar1_phase50_master_16gate_g01_to_g16(self) -> None:
        p1 = self.dossier.phase50_master_16gate_preflight
        self.assertEqual(p1["schema"], MASTER_16GATE_PREFLIGHT_SCHEMA)
        self.assertTrue(p1["all_16_gates_verified"])
        self.assertTrue(p1["offline_13_gates_verified"])
        self.assertTrue(p1["g13_to_g16_all_passed"])
        self.assertEqual(len(p1["gates_g01_to_g16"]), 16)
        self.assertEqual(
            [g["gate_id"][:3] for g in p1["gates_g01_to_g16"]],
            [f"G{i:02d}" for i in range(1, 17)],
        )
        self.assertTrue(all(str(g["status"]).startswith("VERIFIED") for g in p1["gates_g01_to_g16"]))

        g13 = p1["g13_ltc_mishoe_crsdk_spacc"]
        g14 = p1["g14_thermal_npfz100_usbpd"]
        g15 = p1["g15_c2pa_and_factory_calibration"]
        g16 = p1["g16_p12_wf12_and_wbi2_lock"]
        self.assertTrue(g13["passed"])
        self.assertTrue(g13["xlr_h1_preserved"])
        self.assertTrue(g14["passed"])
        self.assertGreaterEqual(g14["npfz100_soc_pct"], 80)
        self.assertGreaterEqual(g14["usbpd_contract_mw"], 27000)
        self.assertTrue(g15["valid"])
        self.assertEqual(g15["calibration_mutation_bytes"], 0)
        self.assertTrue(g15["cnflasha_protected"])
        self.assertTrue(g15["rpmb_protected"])
        self.assertTrue(g15["trustzone_c2pa_keystore_protected"])
        self.assertTrue(g15["factory_sensor_ibis_protected"])
        self.assertTrue(g15["exfat_media_hygiene_ok"])
        self.assertTrue(g16["valid"])
        self.assertTrue(g16["p12_guard_verified"])
        self.assertEqual(g16["p12_patched_rc"], 0)
        self.assertTrue(g16["bk4_airplane_shadow_verified"])
        self.assertTrue(g16["wf12_bootloop_immune"])
        self.assertEqual(g16["wbi_mutation_bytes"], 0)
        self.assertEqual(g16["cp_mutation_bytes"], 0)

    def test_06_pillar2_phase48_ram_overlay_4_langs_13_locks_tmpfs_init2(self) -> None:
        p2 = self.dossier.phase48_stage_b_ram_overlay_v2
        self.assertEqual(p2["schema"], PHASE_48_SCHEMA)
        self.assertTrue(p2["all_checks_passed"])
        self.assertEqual(p2["lock_table_count"], 13)
        self.assertTrue(p2["rollback_all_matched"])
        self.assertTrue(p2["cpio_deterministic_metadata_ok"])
        self.assertTrue(p2["init2_failsafe_audit_valid"])
        self.assertTrue(p2["init2_ld_preload_audit_valid"])
        self.assertTrue(p2["tmpfs_budget_audit"]["within_budget"])
        self.assertLess(
            p2["tmpfs_budget_audit"]["volatile_tmpfs_overlay_mib"],
            float(STAGE_B_TMPFS_BUDGET_LIMIT_MIB),
        )
        self.assertTrue(p2["sandbox_drill"]["all_scenarios_passed"])
        self.assertEqual(p2["sandbox_drill"]["scenario_count"], 9)
        self.assertEqual(p2["sandbox_drill"]["passed_count"], 9)
        self.assertEqual(p2["sandbox_drill"]["total_emmc_mutation_bytes"], 0)
        self.assertEqual(p2["sandbox_drill"]["total_cp_mutation_bytes"], 0)
        self.assertEqual(p2["sandbox_drill"]["total_wbi_mutation_bytes"], 0)
        self.assertTrue(p2["sandbox_drill"]["temp_dir_cleaned"])

    def test_07_pillar3_phase47_unbrick_12_scenarios_and_p1_vfat_capsules(self) -> None:
        p3 = self.dossier.phase47_unbrick_ladder_and_capsule
        self.assertEqual(p3["schema"], UNBRICK_LADDER_SCHEMA)
        self.assertTrue(p3["all_passed"])
        self.assertEqual(p3["scenario_count"], 12)
        self.assertEqual(p3["scenarios_passed"], 12)
        self.assertFalse(p3["persistent_emmc_writes_authorized"])
        self.assertFalse(p3["allow_boot_partition_targeting"])
        self.assertFalse(p3["allow_destructive_fastboot"])
        self.assertFalse(p3["allow_persistent_jiritsu_writes"])
        self.assertEqual(p3["wbi_mutation_bytes"], 0)
        self.assertEqual(p3["emmc_write_bytes"], 0)
        for cap_name in ("fat12_armed", "fat12_tripped", "fat16_tripped"):
            cap = p3["capsules"][cap_name]
            self.assertTrue(cap["valid"])
            self.assertIsNotNone(re.fullmatch(r"[0-9a-f]{64}", cap["capsule_sha256"]))

    def test_08_pillar4_phase42_emmc_forensic_gate(self) -> None:
        p4 = self.dossier.phase42_emmc_dump_forensic_gate
        self.assertEqual(p4["schema"], FORENSIC_VERIFIER_SCHEMA)
        self.assertTrue(p4["all_passed"])
        self.assertEqual(p4["status"], "VERIFIED_READONLY")
        self.assertFalse(p4["persistent_emmc_writes_authorized"])
        self.assertFalse(p4["allow_boot_partition_targeting"])
        self.assertTrue(p4["read_only_donor_access"])
        for role in FORENSIC_REQUIRED_ROLES:
            self.assertTrue(p4["clean_room_roles_verified"][role]["passed"])
        neg = p4["pre_session_negative_gates"]
        self.assertTrue(neg["stuck_bus_rejected"])
        self.assertTrue(neg["truncation_rejected"])
        self.assertTrue(neg["invalidated_wbi2_rejected"])
        self.assertTrue(neg["boot_chain_firewall_blocks_boot0_flash"])
        if self.dossier.verification_mode == "LOCAL_DONOR_O_RDONLY":
            self.assertEqual(p4["verification_mode"], "LOCAL_DONOR_O_RDONLY")
            local_dumps = p4["local_donor_dumps_verified"]
            self.assertIn("p1", local_dumps)
            self.assertIn("p5", local_dumps)
            self.assertIn("p8", local_dumps)
            for k in ("p1", "p5", "p8"):
                self.assertTrue(local_dumps[k]["passed"])
                self.assertTrue(local_dumps[k]["two_pass_stable"])
                self.assertTrue(local_dumps[k]["magic_ok"])

    def test_09_pillar5_phase39_readiness_and_phase35_lifecycle(self) -> None:
        p5 = self.dossier.phase39_stage_b_master_readiness
        self.assertEqual(p5["schema"], STAGE_B_READINESS_PACKET_SCHEMA)
        self.assertTrue(p5["offline_engineering_complete"])
        self.assertTrue(p5["self_verify_valid"])
        self.assertTrue(p5["packet_sha256_verified"])
        self.assertFalse(p5["persistent_emmc_writes_authorized"])
        self.assertFalse(p5["persistent_write_release"])
        self.assertEqual(p5["cp_mutation_bytes"], 0)
        self.assertEqual(p5["wbi_mutation_bytes"], 0)
        self.assertEqual(p5["stage_b_matrix_item_count"], 13)
        self.assertTrue(p5["all_13_items_verified"])
        self.assertTrue(p5["rollback_all_matched"])
        self.assertIsNotNone(re.fullmatch(r"[0-9a-f]{64}", p5["stage_b_appfw_sha256"]))
        self.assertIsNotNone(re.fullmatch(r"[0-9a-f]{64}", p5["stage_b_wlan_rsrc_sha256"]))
        p2 = self.dossier.phase48_stage_b_ram_overlay_v2
        self.assertEqual(p5["stage_b_appfw_sha256"], p2["stage_b_appfw_sha256"])
        self.assertEqual(p5["stage_b_wlan_rsrc_sha256"], p2["stage_b_wlan_rsrc_sha256"])

        p35 = p5["phase35_lifecycle"]
        self.assertTrue(p35["all_checks_passed"])
        self.assertEqual(p35["scenario_count"], 10)
        self.assertEqual(p35["passed_scenario_count"], 10)
        self.assertTrue(p35["h2_zero_drift_verified"])
        self.assertEqual(p35["h2_persistent_bytes_mutated"], 0)
        self.assertTrue(p35["h2_receipt_sha256_verified"])
        self.assertIsNotNone(re.fullmatch(r"[0-9a-f]{64}", p35["report_sha256"]))

        byof = p5["byof_manifest_parity"]
        self.assertTrue(byof["all_checks_passed"])
        self.assertTrue(byof["en_zh_parity_ok"])
        self.assertEqual(byof["en_entry_count"], 57)
        self.assertEqual(byof["zh_entry_count"], 57)

    def test_10_invalid_lang_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            build_stage_b_integrated_dossier(lang="invalid_lang")

    def test_11_non_mapping_and_bad_dossier_sha256_fail_closed(self) -> None:
        bad_type = verify_stage_b_integrated_dossier(["not", "a", "dict"])  # type: ignore[arg-type]
        self.assertFalse(bad_type.valid)
        self.assertFalse(bad_type.schema_ok)
        self.assertFalse(bad_type.sha256_matched)

        tampered = copy.deepcopy(self.dossier_dict)
        first = tampered["dossier_sha256"][0]
        tampered["dossier_sha256"] = ("0" if first != "0" else "1") + tampered["dossier_sha256"][1:]
        res = verify_stage_b_integrated_dossier(tampered)
        self.assertFalse(res.valid)
        self.assertFalse(res.sha256_matched)

    def test_12_tamper_raw_bytes_repr_rejected(self) -> None:
        tampered = copy.deepcopy(self.dossier_dict)
        tampered["errors"] = ["raw=b'\\x89PNG'"]
        tampered = _with_recomputed_dossier_sha256(tampered)
        res = verify_stage_b_integrated_dossier(tampered)
        self.assertFalse(res.valid)
        self.assertTrue(any("Raw binary bytes repr" in err for err in res.errors))

    def test_13_tamper_schema_version_lang_or_mode_rejected(self) -> None:
        for field, bad_val in (
            ("schema", "stage_b_integrated_dossier_v0"),
            ("phase_version", "51.0.0"),
            ("selected_lang", "fr"),
            ("verification_mode", "LIVE_HARDWARE_WRITE"),
        ):
            tampered = copy.deepcopy(self.dossier_dict)
            tampered[field] = bad_val
            tampered = _with_recomputed_dossier_sha256(tampered)
            res = verify_stage_b_integrated_dossier(tampered)
            self.assertFalse(res.valid, msg=f"{field}={bad_val!r} should fail")
            self.assertFalse(res.schema_ok)

    def test_14_tamper_persistent_emmc_writes_authorized_rejected(self) -> None:
        tampered = copy.deepcopy(self.dossier_dict)
        tampered["persistent_emmc_writes_authorized"] = True
        tampered = _with_recomputed_dossier_sha256(tampered)
        res = verify_stage_b_integrated_dossier(tampered)
        self.assertFalse(res.valid)
        self.assertTrue(res.sha256_matched)
        self.assertFalse(res.safety_redlines_ok)

    def test_15_tamper_persistent_write_release_or_usb_ops_rejected(self) -> None:
        for field, val in (("persistent_write_release", True), ("usb_or_camera_operations", 1)):
            tampered = copy.deepcopy(self.dossier_dict)
            tampered[field] = val
            tampered = _with_recomputed_dossier_sha256(tampered)
            res = verify_stage_b_integrated_dossier(tampered)
            self.assertFalse(res.valid)
            self.assertFalse(res.safety_redlines_ok)

    def test_16_tamper_cp_wbi_calibration_mutation_bytes_rejected(self) -> None:
        for field in ("cp_mutation_bytes", "wbi_mutation_bytes", "calibration_mutation_bytes"):
            tampered = copy.deepcopy(self.dossier_dict)
            tampered[field] = 4
            tampered = _with_recomputed_dossier_sha256(tampered)
            res = verify_stage_b_integrated_dossier(tampered)
            self.assertFalse(res.valid, msg=f"{field}=4 should fail")
            self.assertFalse(res.safety_redlines_ok)

    def test_17_tamper_pillar_count_status_or_errors_rejected(self) -> None:
        for field, bad_val in (
            ("passed_pillar_count", 4),
            ("candidate_ready", False),
            ("status", "BLOCKED"),
            ("errors", ["synthetic-failure"]),
        ):
            tampered = copy.deepcopy(self.dossier_dict)
            tampered[field] = bad_val
            tampered = _with_recomputed_dossier_sha256(tampered)
            res = verify_stage_b_integrated_dossier(tampered)
            self.assertFalse(res.valid)
            self.assertFalse(res.safety_redlines_ok)

    def test_18_tamper_pillar1_g14_npfz100_or_usbpd_rejected(self) -> None:
        t1 = copy.deepcopy(self.dossier_dict)
        t1["phase50_master_16gate_preflight"]["g14_thermal_npfz100_usbpd"]["npfz100_soc_pct"] = 79
        res1 = verify_stage_b_integrated_dossier(_with_recomputed_dossier_sha256(t1))
        self.assertFalse(res1.valid)
        self.assertFalse(res1.phase50_16gate_ok)

        t2 = copy.deepcopy(self.dossier_dict)
        t2["phase50_master_16gate_preflight"]["g14_thermal_npfz100_usbpd"]["usbpd_contract_mw"] = 15000
        res2 = verify_stage_b_integrated_dossier(_with_recomputed_dossier_sha256(t2))
        self.assertFalse(res2.valid)
        self.assertFalse(res2.phase50_16gate_ok)

    def test_19_tamper_pillar1_g15_c2pa_or_g16_wf12_rejected(self) -> None:
        t1 = copy.deepcopy(self.dossier_dict)
        t1["phase50_master_16gate_preflight"]["g15_c2pa_and_factory_calibration"]["calibration_mutation_bytes"] = 8
        res1 = verify_stage_b_integrated_dossier(_with_recomputed_dossier_sha256(t1))
        self.assertFalse(res1.valid)
        self.assertFalse(res1.phase50_16gate_ok)

        t2 = copy.deepcopy(self.dossier_dict)
        t2["phase50_master_16gate_preflight"]["g16_p12_wf12_and_wbi2_lock"]["wf12_bootloop_immune"] = False
        res2 = verify_stage_b_integrated_dossier(_with_recomputed_dossier_sha256(t2))
        self.assertFalse(res2.valid)
        self.assertFalse(res2.phase50_16gate_ok)

    def test_20_tamper_pillar2_missing_lang_or_tmpfs_over_48mib_rejected(self) -> None:
        t1 = copy.deepcopy(self.dossier_dict)
        del t1["phase48_stage_b_ram_overlay_v2"]["lang_profiles"]["japanese"]
        res1 = verify_stage_b_integrated_dossier(_with_recomputed_dossier_sha256(t1))
        self.assertFalse(res1.valid)
        self.assertFalse(res1.phase48_ram_overlay_ok)

        t2 = copy.deepcopy(self.dossier_dict)
        t2["phase48_stage_b_ram_overlay_v2"]["tmpfs_budget_audit"]["volatile_tmpfs_overlay_mib"] = 48.01
        res2 = verify_stage_b_integrated_dossier(_with_recomputed_dossier_sha256(t2))
        self.assertFalse(res2.valid)
        self.assertFalse(res2.phase48_ram_overlay_ok)

    def test_21_tamper_pillar2_sandbox_drill_or_lock_table_rejected(self) -> None:
        t1 = copy.deepcopy(self.dossier_dict)
        t1["phase48_stage_b_ram_overlay_v2"]["sandbox_drill"]["passed_count"] = 8
        res1 = verify_stage_b_integrated_dossier(_with_recomputed_dossier_sha256(t1))
        self.assertFalse(res1.valid)
        self.assertFalse(res1.phase48_ram_overlay_ok)

        t2 = copy.deepcopy(self.dossier_dict)
        t2["phase48_stage_b_ram_overlay_v2"]["lock_table_count"] = 12
        res2 = verify_stage_b_integrated_dossier(_with_recomputed_dossier_sha256(t2))
        self.assertFalse(res2.valid)
        self.assertFalse(res2.phase48_ram_overlay_ok)

    def test_22_tamper_pillar3_unbrick_scenarios_or_capsule_rejected(self) -> None:
        t1 = copy.deepcopy(self.dossier_dict)
        t1["phase47_unbrick_ladder_and_capsule"]["scenarios_passed"] = 11
        res1 = verify_stage_b_integrated_dossier(_with_recomputed_dossier_sha256(t1))
        self.assertFalse(res1.valid)
        self.assertFalse(res1.phase47_unbrick_capsule_ok)

        t2 = copy.deepcopy(self.dossier_dict)
        t2["phase47_unbrick_ladder_and_capsule"]["capsules"]["fat16_tripped"]["valid"] = False
        res2 = verify_stage_b_integrated_dossier(_with_recomputed_dossier_sha256(t2))
        self.assertFalse(res2.valid)
        self.assertFalse(res2.phase47_unbrick_capsule_ok)

    def test_23_tamper_pillar3_boot_targeting_or_emmc_writes_rejected(self) -> None:
        t1 = copy.deepcopy(self.dossier_dict)
        t1["phase47_unbrick_ladder_and_capsule"]["allow_boot_partition_targeting"] = True
        res1 = verify_stage_b_integrated_dossier(_with_recomputed_dossier_sha256(t1))
        self.assertFalse(res1.valid)
        self.assertFalse(res1.phase47_unbrick_capsule_ok)

        t2 = copy.deepcopy(self.dossier_dict)
        t2["phase47_unbrick_ladder_and_capsule"]["emmc_write_bytes"] = 512
        res2 = verify_stage_b_integrated_dossier(_with_recomputed_dossier_sha256(t2))
        self.assertFalse(res2.valid)
        self.assertFalse(res2.phase47_unbrick_capsule_ok)

    def test_24_tamper_pillar4_forensic_negative_gate_or_role_rejected(self) -> None:
        t1 = copy.deepcopy(self.dossier_dict)
        t1["phase42_emmc_dump_forensic_gate"]["pre_session_negative_gates"]["stuck_bus_rejected"] = False
        res1 = verify_stage_b_integrated_dossier(_with_recomputed_dossier_sha256(t1))
        self.assertFalse(res1.valid)
        self.assertFalse(res1.phase42_forensic_gate_ok)

        t2 = copy.deepcopy(self.dossier_dict)
        t2["phase42_emmc_dump_forensic_gate"]["clean_room_roles_verified"]["p5"]["passed"] = False
        res2 = verify_stage_b_integrated_dossier(_with_recomputed_dossier_sha256(t2))
        self.assertFalse(res2.valid)
        self.assertFalse(res2.phase42_forensic_gate_ok)

    def test_25_tamper_pillar5_phase35_lifecycle_or_byof_rejected(self) -> None:
        t1 = copy.deepcopy(self.dossier_dict)
        t1["phase39_stage_b_master_readiness"]["phase35_lifecycle"]["passed_scenario_count"] = 9
        res1 = verify_stage_b_integrated_dossier(_with_recomputed_dossier_sha256(t1))
        self.assertFalse(res1.valid)
        self.assertFalse(res1.phase39_readiness_ok)

        t2 = copy.deepcopy(self.dossier_dict)
        t2["phase39_stage_b_master_readiness"]["byof_manifest_parity"]["en_zh_parity_ok"] = False
        res2 = verify_stage_b_integrated_dossier(_with_recomputed_dossier_sha256(t2))
        self.assertFalse(res2.valid)
        self.assertFalse(res2.phase39_readiness_ok)

    def test_26_strictly_o_rdonly_donor_and_wbi2_file_access(self) -> None:
        donor_opens = [
            (p, fl)
            for p, fl in self.recorded_opens
            if any(tok in p for tok in ("nflasha", "appFw.so", "libWlanResource.so", "upm.ko", ".so", ".img"))
        ]
        if self.dossier.verification_mode == "LOCAL_DONOR_O_RDONLY":
            self.assertGreater(len(donor_opens), 0)
        for path_str, fl in donor_opens:
            self.assertEqual(fl & os.O_ACCMODE, os.O_RDONLY, msg=f"Non-O_RDONLY open on {path_str}")

        with tempfile.TemporaryDirectory() as td:
            wbi2_path = Path(td) / "synthetic_nflasha5.img"
            wbi2_path.write_bytes(build_synthetic_p5_wbi2_image(magic=WBI2_MAGIC))
            seen: list[tuple[str, int]] = []
            real_open = os.open

            def _spy(path: object, flags: int, *args: object, **kwargs: object) -> int:
                seen.append((str(path), flags))
                return real_open(path, flags, *args, **kwargs)  # type: ignore[arg-type]

            with mock.patch("fx6_closure.patcher.os.open", side_effect=_spy):
                raw_wbi2 = read_donor_bytes_readonly(wbi2_path)
            rep = verify_emmc_dump_bytes(raw_wbi2, role="p5")
            raw_hdr = raw_wbi2[:WBI2_HEADER_SIZE]

            wbi2_opens = [fl for p, fl in seen if str(wbi2_path) in p]
            self.assertTrue(rep.passed)
            self.assertEqual(raw_hdr[:4].hex(), WBI2_MAGIC.hex())
            self.assertEqual(len(wbi2_opens), 1)
            self.assertTrue(all((f & os.O_ACCMODE) == os.O_RDONLY for f in wbi2_opens))

    def test_27_deterministic_json_roundtrip_and_zero_raw_bytes(self) -> None:
        roundtrip_text = self.dossier.to_deterministic_json(indent=2)
        self.assertNotRegex(roundtrip_text, RAW_BYTES_REPR_REGEX)
        parsed = json.loads(roundtrip_text)
        self.assertEqual(parsed["dossier_sha256"], self.dossier.dossier_sha256)
        self.assertTrue(verify_stage_b_integrated_dossier(parsed).valid)

    def test_28_cli_verify_stage_b_candidate_json_summary_and_output(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_path = Path(td) / "dossier.json"
            buf_json = io.StringIO()
            buf_summary = io.StringIO()

            with (
                mock.patch(
                    "fx6_closure.stage_b_candidate_integrator.build_stage_b_integrated_dossier",
                    return_value=self.dossier,
                ) as m_build,
                redirect_stdout(buf_json),
            ):
                rc_json = cli_main.main(
                    [
                        "verify-stage-b-candidate",
                        "--clean-room",
                        "--lang",
                        "schinese",
                        "--json",
                        "--output",
                        str(out_path),
                    ]
                )

            self.assertEqual(rc_json, 0)
            m_build.assert_called_once()
            self.assertTrue(m_build.call_args.kwargs["synthetic_clean_room"])
            self.assertEqual(m_build.call_args.kwargs["lang"], "schinese")
            self.assertTrue(out_path.is_file())
            stdout_json = buf_json.getvalue()
            self.assertEqual(out_path.read_text(encoding="utf-8"), stdout_json)
            self.assertNotRegex(stdout_json, RAW_BYTES_REPR_REGEX)

            with (
                mock.patch(
                    "fx6_closure.stage_b_candidate_integrator.build_stage_b_integrated_dossier",
                    return_value=self.dossier,
                ),
                redirect_stdout(buf_summary),
            ):
                rc_sum = cli_main.main(["verify-stage-b-candidate"])

            self.assertEqual(rc_sum, 0)
            summary_line = buf_summary.getvalue()
            self.assertIn("status=OK", summary_line)
            self.assertIn("pillars=5/5", summary_line)
            self.assertIn("16gate=PASS", summary_line)
            self.assertIn("unbrick=12/12", summary_line)
            self.assertIn("lifecycle=10/10", summary_line)
            self.assertNotRegex(summary_line, RAW_BYTES_REPR_REGEX)

    def test_29_cli_verify_stage_b_candidate_fails_closed_nonzero(self) -> None:
        bad_dict = copy.deepcopy(self.dossier_dict)
        bad_dict["persistent_emmc_writes_authorized"] = True
        bad_dict["errors"] = tuple(bad_dict["errors"])
        bad_dossier = StageBIntegratedDossierReport(**bad_dict)

        buf = io.StringIO()
        with (
            mock.patch(
                "fx6_closure.stage_b_candidate_integrator.build_stage_b_integrated_dossier",
                return_value=bad_dossier,
            ),
            redirect_stdout(buf),
        ):
            rc = cli_main.main(["verify-stage-b-candidate"])

        self.assertEqual(rc, 1)
        self.assertIn("status=FAILED", buf.getvalue())

    def test_30_all_4_bk_lang_profiles_distinct_and_reproducible(self) -> None:
        profiles = self.dossier.phase48_stage_b_ram_overlay_v2["lang_profiles"]
        self.assertEqual(tuple(profiles.keys()), STAGE_B_SUPPORTED_LANGS)
        bk_values = {profiles[code]["bk_lang_value"] for code in STAGE_B_SUPPORTED_LANGS}
        bk4_shas = {profiles[code]["bk4_shadow_sha256"] for code in STAGE_B_SUPPORTED_LANGS}
        cpio_shas = {profiles[code]["cpio_sha256"] for code in STAGE_B_SUPPORTED_LANGS}
        self.assertEqual(len(bk_values), 4)
        self.assertEqual(len(bk4_shas), 4)
        self.assertEqual(len(cpio_shas), 4)
        for code in STAGE_B_SUPPORTED_LANGS:
            prof = profiles[code]
            self.assertEqual(prof["bk_lang_value"], STAGE_B_BK_LANG_SPECS[code].bk_lang_value)
            self.assertEqual(prof["lock_table_count"], 13)
            self.assertTrue(prof["rollback_all_matched"])
            self.assertTrue(prof["tmpfs_within_budget"])
            self.assertLess(prof["volatile_tmpfs_overlay_mib"], float(STAGE_B_TMPFS_BUDGET_LIMIT_MIB))
            self.assertTrue(prof["cpio_deterministic_metadata_ok"])
            self.assertTrue(prof["init2_failsafe_audit_valid"])
            self.assertTrue(prof["init2_ld_preload_audit_valid"])
            self.assertIsNotNone(re.fullmatch(r"[0-9a-f]{64}", prof["cpio_sha256"]))
            self.assertIsNotNone(re.fullmatch(r"[0-9a-f]{64}", prof["bk4_shadow_sha256"]))


if __name__ == "__main__":
    unittest.main()
