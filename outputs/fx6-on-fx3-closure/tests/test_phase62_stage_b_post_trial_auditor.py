"""Phase 62 tests for Stage-B `H0`-vs-`H2` Post-Trial Zero-Persistence Forensic Auditor."""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import copy
import inspect
import io
import json
import os
import re
import tempfile
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

import fx6_closure
from fx3_safety.exfat_media_integrity_guard import (
    EXFAT_FLAG_MEDIA_FAILURE,
    EXFAT_FLAG_VOLUME_DIRTY,
    build_synthetic_exfat_boot_region,
)
from fx3_safety.thermal_pwm_and_power_guard import USBPD_REQUIRED_POWER_MW
from fx6_closure import __main__ as cli_main
from fx6_closure.hardware_readiness_packet import is_forced_clean_room
from fx6_closure.stage_b_post_trial_auditor import (
    ANOMALY_0x100D_13S_PANIC,
    ANOMALY_BK4_PERSISTENT_NVRAM_LEAK,
    ANOMALY_C2PA_OR_CALIBRATION_DRIFT,
    ANOMALY_CP_BYTE_MUTATION,
    ANOMALY_EXFAT_UNFINALIZED_RSV_CLIP,
    ANOMALY_EXFAT_VOLUME_DIRTY,
    ANOMALY_P1_CAPSULE_OR_COUNTER_DRIFT,
    ANOMALY_PERSISTENT_EMMC_WRITE_POLICY,
    ANOMALY_RP2040_FIXTURE_HAZARD,
    ANOMALY_SAME_BODY_IDENTITY_MISMATCH,
    ANOMALY_SECTOR0_TAMPER,
    ANOMALY_SERIAL_WATCHDOG_OR_PANIC,
    ANOMALY_SYNTHETIC_OR_INVALID_BUNDLE,
    ANOMALY_THERMAL_RUNAWAY_TEARDOWN,
    ANOMALY_TIER0_PERSISTENT_DRIFT,
    ANOMALY_WBI2_HEADER_DRIFT,
    ANOMALY_WF12_00342260_HANG,
    CALIBRATION_MUTATION_BYTES,
    CLASS_CLEAN_ZERO_PERSISTENCE,
    CP_MUTATION_BYTES,
    DONOR_FX3_SEED_BK4_RELPATH,
    DONOR_P1_RELPATH,
    P8_CP_MUTATION_FORBIDDEN,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE_62_VERSION,
    STAGE_B_ANOMALY_CLASSIFICATION_CODES,
    STAGE_B_CALIBRATION_ITEM_IDS,
    STAGE_B_FORENSIC_PROBE_DEFAULTS,
    STAGE_B_POST_TRIAL_AUDIT_SCHEMA,
    STAGE_B_POST_TRIAL_RECEIPT_SCHEMA,
    STAGE_B_POST_TRIAL_SCENARIO_IDS,
    USB_OR_CAMERA_OPERATIONS,
    WBI_MUTATION_BYTES,
    WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN,
    StageBBk4NvramZeroDriftAudit,
    StageBC2paSpaccCalibrationAudit,
    StageBP1CapsuleAndExfatAudit,
    StageBPostTrialAuditReport,
    StageBPostTrialItemParity,
    StageBPostTrialReceipt,
    StageBPostTrialScenarioResult,
    StageBPostTrialVerifyResult,
    StageBRp2040AndSerialThermalPostMortem,
    _compute_canonical_sha256,
    _compute_report_sha256,
    build_persistent_stock_bk4_bytes,
    populate_stage_b_capture_bundle_fixture,
    run_stage_b_post_trial_forensic_audit,
    verify_stage_b_post_trial_report,
    verify_stage_b_post_trial_zero_persistence,
)

RAW_BYTES_REPR_REGEX = r"(?<![0-9A-Za-z_/.-])b['\"]"


def _with_recomputed_sha256(report_dict: dict) -> dict:
    """Return a deep copy with valid recomputed `report_sha256` to test fail-closed semantics."""
    mutated = copy.deepcopy(report_dict)
    mutated["report_sha256"] = _compute_report_sha256(mutated)
    return mutated


class TestPhase62StageBPostTrialAuditor(unittest.TestCase):
    """Fast (<3s) dual-mode & fail-closed tests for `stage_b_post_trial_auditor`."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.recorded_opens: list[tuple[str, int, str]] = []
        real_open = os.open

        def _spy_open(path: object, flags: int, *args: object, **kwargs: object) -> int:
            caller = ""
            depth = 1
            while True:
                try:
                    frame = sys._getframe(depth)
                except ValueError:
                    break
                fn = frame.f_code.co_filename
                if "unittest" not in fn and not fn.endswith("mock.py"):
                    caller = fn
                    break
                depth += 1
            cls.recorded_opens.append((str(path), flags, caller))
            return real_open(path, flags, *args, **kwargs)  # type: ignore[arg-type]

        t0 = time.monotonic()
        with mock.patch("fx6_closure.stage_b_post_trial_auditor.os.open", side_effect=_spy_open):
            cls.report = run_stage_b_post_trial_forensic_audit()
        cls.audit_elapsed_s = time.monotonic() - t0

        cls.report_dict = cls.report.to_dict()
        cls.report_json_str = cls.report.to_deterministic_json()
        cls.report_json_dict = json.loads(cls.report_json_str)

        cls._bundle_ctx = tempfile.TemporaryDirectory(prefix="fx6_phase62_unit_")
        cls.bundle_root = Path(cls._bundle_ctx.name)
        cls.h0_dir = cls.bundle_root / "h0_clean"
        cls.h2_dir = cls.bundle_root / "h2_clean"
        populate_stage_b_capture_bundle_fixture(cls.h0_dir)
        populate_stage_b_capture_bundle_fixture(cls.h2_dir)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._bundle_ctx.cleanup()

    def test_01_public_exports_and_constants(self) -> None:
        expected_exports = {
            "ANOMALY_0x100D_13S_PANIC",
            "ANOMALY_BK4_PERSISTENT_NVRAM_LEAK",
            "ANOMALY_C2PA_OR_CALIBRATION_DRIFT",
            "ANOMALY_CP_BYTE_MUTATION",
            "ANOMALY_EXFAT_UNFINALIZED_RSV_CLIP",
            "ANOMALY_EXFAT_VOLUME_DIRTY",
            "ANOMALY_P1_CAPSULE_OR_COUNTER_DRIFT",
            "ANOMALY_PERSISTENT_EMMC_WRITE_POLICY",
            "ANOMALY_RP2040_FIXTURE_HAZARD",
            "ANOMALY_SAME_BODY_IDENTITY_MISMATCH",
            "ANOMALY_SECTOR0_TAMPER",
            "ANOMALY_SERIAL_WATCHDOG_OR_PANIC",
            "ANOMALY_SYNTHETIC_OR_INVALID_BUNDLE",
            "ANOMALY_THERMAL_RUNAWAY_TEARDOWN",
            "ANOMALY_TIER0_PERSISTENT_DRIFT",
            "ANOMALY_WBI2_HEADER_DRIFT",
            "ANOMALY_WF12_00342260_HANG",
            "CLASS_CLEAN_ZERO_PERSISTENCE",
            "DONOR_FX3_SEED_BK4_RELPATH",
            "DONOR_P1_RELPATH",
            "PHASE_62_VERSION",
            "STAGE_B_ANOMALY_CLASSIFICATION_CODES",
            "STAGE_B_CALIBRATION_ITEM_IDS",
            "STAGE_B_FORENSIC_PROBE_DEFAULTS",
            "STAGE_B_POST_TRIAL_AUDIT_SCHEMA",
            "STAGE_B_POST_TRIAL_RECEIPT_SCHEMA",
            "STAGE_B_POST_TRIAL_SCENARIO_IDS",
            "StageBBk4NvramZeroDriftAudit",
            "StageBC2paSpaccCalibrationAudit",
            "StageBP1CapsuleAndExfatAudit",
            "StageBPostTrialAuditReport",
            "StageBPostTrialItemParity",
            "StageBPostTrialReceipt",
            "StageBPostTrialScenarioResult",
            "StageBPostTrialVerifyResult",
            "StageBRp2040AndSerialThermalPostMortem",
            "build_persistent_stock_bk4_bytes",
            "populate_stage_b_capture_bundle_fixture",
            "run_stage_b_post_trial_forensic_audit",
            "verify_stage_b_post_trial_report",
            "verify_stage_b_post_trial_zero_persistence",
        }
        self.assertTrue(expected_exports.issubset(set(fx6_closure.__all__)))
        self.assertEqual(STAGE_B_POST_TRIAL_RECEIPT_SCHEMA, "stage_b_post_trial_receipt_v1")
        self.assertEqual(STAGE_B_POST_TRIAL_AUDIT_SCHEMA, "stage_b_post_trial_forensic_audit_v1")
        self.assertEqual(PHASE_62_VERSION, "62.0.0")
        self.assertEqual(len(STAGE_B_POST_TRIAL_SCENARIO_IDS), 10)
        self.assertEqual(len(STAGE_B_ANOMALY_CLASSIFICATION_CODES), 10)
        self.assertEqual(len(STAGE_B_CALIBRATION_ITEM_IDS), 9)
        self.assertEqual(len(STAGE_B_FORENSIC_PROBE_DEFAULTS), 3)
        self.assertTrue(DONOR_P1_RELPATH.endswith("nflasha1"))
        self.assertTrue(DONOR_FX3_SEED_BK4_RELPATH.endswith("FX3-CX95900_ALLLANG-Backup.bin"))

    def test_02_hard_locked_zero_write_and_immutability_redlines(self) -> None:
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertTrue(P8_CP_MUTATION_FORBIDDEN)
        self.assertTrue(WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN)
        self.assertEqual(CP_MUTATION_BYTES, 0)
        self.assertEqual(WBI_MUTATION_BYTES, 0)
        self.assertEqual(CALIBRATION_MUTATION_BYTES, 0)
        self.assertEqual(USB_OR_CAMERA_OPERATIONS, 0)

        self.assertFalse(self.report.persistent_emmc_writes_authorized)
        self.assertFalse(self.report.persistent_write_release)
        self.assertTrue(self.report.p8_cp_mutation_forbidden)
        self.assertTrue(self.report.wbi_p5_write_and_hibernation_forbidden)
        self.assertEqual(self.report.cp_mutation_bytes, 0)
        self.assertEqual(self.report.wbi_mutation_bytes, 0)
        self.assertEqual(self.report.calibration_mutation_bytes, 0)
        self.assertEqual(self.report.usb_or_camera_operations, 0)

    def test_03_fast_execution_and_overall_report_status(self) -> None:
        self.assertLess(self.audit_elapsed_s, 3.0)
        self.assertIsInstance(self.report, StageBPostTrialAuditReport)
        self.assertEqual(self.report.schema, STAGE_B_POST_TRIAL_AUDIT_SCHEMA)
        self.assertEqual(self.report.phase_version, PHASE_62_VERSION)
        self.assertTrue(self.report.all_checks_passed, msg=f"errors={self.report.errors}")
        self.assertEqual(self.report.status, "VERIFIED_STAGE_B_POST_TRIAL_ZERO_PERSISTENCE")
        self.assertTrue(self.report.all_10_scenarios_passed)
        self.assertEqual(self.report.scenario_count, 10)
        self.assertEqual(self.report.passed_scenario_count, 10)
        self.assertTrue(self.report.temp_dir_cleaned)
        self.assertEqual(self.report.errors, ())
        expected_mode = "CLEAN_ROOM_SYNTHETIC" if is_forced_clean_room() else "LOCAL_DONOR_O_RDONLY"
        self.assertEqual(self.report.verification_mode, expected_mode)

    def test_04_self_authenticating_sha256_and_zero_raw_bytes_repr(self) -> None:
        self.assertRegex(self.report.report_sha256, r"^[0-9a-f]{64}$")
        self.assertRegex(self.report.nominal_receipt.receipt_sha256, r"^[0-9a-f]{64}$")
        self.assertEqual(
            _compute_report_sha256(self.report_dict),
            _compute_report_sha256(self.report_json_dict),
        )
        self.assertEqual(self.report.report_sha256, _compute_report_sha256(self.report_json_dict))
        self.assertNotRegex(self.report_json_str, RAW_BYTES_REPR_REGEX)

        v_obj = verify_stage_b_post_trial_report(self.report)
        v_dict = verify_stage_b_post_trial_report(self.report_dict)
        v_json = verify_stage_b_post_trial_report(self.report_json_dict)
        for v in (v_obj, v_dict, v_json):
            self.assertIsInstance(v, StageBPostTrialVerifyResult)
            self.assertTrue(v.valid, msg=f"verify errors: {v.errors}")
            self.assertTrue(v.schema_ok)
            self.assertTrue(v.sha256_matched)
            self.assertTrue(v.safety_redlines_ok)
            self.assertTrue(v.nominal_receipt_ok)
            self.assertTrue(v.all_10_scenarios_ok)
            self.assertEqual(v.errors, ())

    def test_05_strict_os_open_o_rdonly_hygiene(self) -> None:
        auditor_opens = [
            (p, f)
            for p, f, caller in self.recorded_opens
            if caller.endswith("stage_b_post_trial_auditor.py")
        ]
        self.assertGreater(len(auditor_opens), 0)
        write_flags = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
        for opened_path, flags in auditor_opens:
            self.assertEqual(
                flags & 0x3,
                os.O_RDONLY,
                msg=f"File {opened_path} opened without O_RDONLY (flags={flags:#x})",
            )
            self.assertEqual(
                flags & write_flags,
                0,
                msg=f"File {opened_path} opened with write flag (flags={flags:#x})",
            )

    def test_06_deterministic_receipt_and_json_reproducibility(self) -> None:
        rec1 = verify_stage_b_post_trial_zero_persistence(self.h0_dir, self.h2_dir)
        self.assertTrue(rec1.all_checks_passed)
        self.assertEqual(
            rec1.receipt_sha256,
            _compute_canonical_sha256(rec1.to_dict(), "receipt_sha256"),
        )
        self.assertEqual(rec1.to_deterministic_json(), rec1.to_deterministic_json())
        self.assertEqual(
            self.report.to_deterministic_json(),
            json.dumps(self.report_dict, indent=2, sort_keys=False) + "\n",
        )

    def test_07_nominal_16_surface_parity_and_donor_probes(self) -> None:
        nom = self.report.nominal_receipt
        self.assertIsInstance(nom, StageBPostTrialReceipt)
        self.assertEqual(nom.schema, STAGE_B_POST_TRIAL_RECEIPT_SCHEMA)
        self.assertEqual(nom.classification, CLASS_CLEAN_ZERO_PERSISTENCE)
        self.assertEqual(nom.audited_item_count, 16)
        self.assertEqual(nom.matched_item_count, 16)
        self.assertEqual(nom.persistent_bytes_mutated, 0)
        self.assertEqual(nom.sector0_mutation_bytes, 0)
        self.assertEqual(nom.wbi_mutation_bytes, 0)
        self.assertEqual(nom.cp_mutation_bytes, 0)
        self.assertEqual(nom.calibration_mutation_bytes, 0)
        self.assertEqual(nom.drifted_items, ())
        self.assertEqual(len(nom.item_comparisons), 16)
        self.assertTrue(all(isinstance(c, StageBPostTrialItemParity) and c.bit_exact_match for c in nom.item_comparisons))

        probes = self.report.donor_o_rdonly_probes
        self.assertTrue(probes["p1_vbr_checked"])
        self.assertTrue(probes["p5_wbi2_header_checked"])
        self.assertTrue(probes["p8_cp_fat_checked"])
        self.assertTrue(probes["bk4_seed_checked"])

    def test_08_nominal_bk4_nvram_zero_drift_and_ram_shadow_only(self) -> None:
        bk4 = self.report.nominal_receipt.bk4_nvram_audit
        self.assertIsInstance(bk4, StageBBk4NvramZeroDriftAudit)
        self.assertTrue(bk4.valid)
        self.assertTrue(bk4.bk4_bit_exact_match)
        self.assertEqual(bk4.bk4_mutated_bytes, 0)
        self.assertTrue(bk4.u5_boot_img_byte8_zero_ok)
        self.assertEqual(bk4.h2_bk4_byte8, 0)
        self.assertTrue(bk4.u5_zero_updater_mode_residue_ok)
        self.assertEqual(bk4.sticky_updater_residue, ())
        self.assertTrue(bk4.persistent_airplane_keys_unchanged)
        self.assertTrue(bk4.persistent_bk_lang_unchanged)
        self.assertTrue(bk4.ram_shadow_bk4_only)
        self.assertEqual(bk4.ram_shadow_bk_lang, "schinese")
        self.assertEqual(
            bk4.ram_shadow_airplane_keys,
            {"0x019e0012": "00", "0x0051000f": "00", "0x01a20002": "00"},
        )

    def test_09_nominal_c2pa_spacc_and_factory_calibration_zero_drift(self) -> None:
        cal = self.report.nominal_receipt.c2pa_calibration_audit
        self.assertIsInstance(cal, StageBC2paSpaccCalibrationAudit)
        self.assertTrue(cal.valid)
        self.assertEqual(cal.calibration_mutation_bytes, 0)
        self.assertTrue(cal.c2pa_keystore_untouched)
        self.assertTrue(cal.spacc_cnflasha_untouched)
        self.assertEqual(cal.c2pa_rq_lic_h0_sha256, cal.c2pa_rq_lic_h2_sha256)
        self.assertEqual(cal.spacc_cnflasha_h0_sha256, cal.spacc_cnflasha_h2_sha256)
        self.assertEqual(cal.audited_calibration_items, STAGE_B_CALIBRATION_ITEM_IDS)
        self.assertEqual(cal.drifted_calibration_items, ())

    def test_10_nominal_p1_capsule_and_exfat_media_cleanliness(self) -> None:
        px = self.report.nominal_receipt.p1_exfat_audit
        self.assertIsInstance(px, StageBP1CapsuleAndExfatAudit)
        self.assertTrue(px.valid)
        self.assertTrue(px.p1_vfat_valid)
        self.assertTrue(px.p1_oneshot_boot_counter_clean)
        self.assertEqual(px.p1_boot_attempts_observed, 0)
        self.assertTrue(px.p1_capsule_fsync_order_ok)
        self.assertTrue(px.exfat_vbr_valid)
        self.assertTrue(px.exfat_boot_checksum_ok)
        self.assertFalse(px.exfat_volume_dirty)
        self.assertFalse(px.exfat_media_failure)
        self.assertEqual(px.exfat_rsv_files, ())
        self.assertEqual(px.exfat_chk_files, ())
        self.assertTrue(px.exfat_media_clean)

    def test_11_nominal_rp2040_and_serial_thermal_post_mortem(self) -> None:
        st = self.report.nominal_receipt.serial_thermal_post_mortem
        self.assertIsInstance(st, StageBRp2040AndSerialThermalPostMortem)
        self.assertTrue(st.valid)
        self.assertTrue(st.rp2040_fixture_safe)
        self.assertTrue(st.rp2040_open_drain_enforced)
        self.assertAlmostEqual(st.rp2040_io_voltage_v, 1.8)
        self.assertEqual(st.rp2040_baud_rate, 48000)
        self.assertTrue(st.serial_detector_v2_passed)
        self.assertEqual(st.serial_detector_disposition, "PASS")
        self.assertTrue(st.watchdog_budget_passed)
        self.assertFalse(st.wf12_00342260_hang_detected)
        self.assertFalse(st.panic_0x100d_13s_detected)
        self.assertLess(st.peak_soc_c, 90.0)
        self.assertTrue(st.thermal_under_90c_ok)
        self.assertFalse(st.thermal_emergency_teardown_triggered)
        self.assertGreaterEqual(st.npfz100_soc_pct, 80)
        self.assertGreaterEqual(st.usbpd_contract_mw, USBPD_REQUIRED_POWER_MW)

    def test_12_scenario_s01_clean_session(self) -> None:
        sc = self.report.scenarios[0]
        self.assertIsInstance(sc, StageBPostTrialScenarioResult)
        self.assertEqual(sc.scenario_id, "S01_CLEAN_H0_EQ_H2_STAGE_B_SESSION")
        self.assertTrue(sc.expected_pass)
        self.assertTrue(sc.observed_pass)
        self.assertTrue(sc.passed)
        self.assertEqual(sc.observed_classification, CLASS_CLEAN_ZERO_PERSISTENCE)
        self.assertEqual(sc.persistent_bytes_mutated, 0)
        self.assertTrue(sc.c2pa_keystore_untouched)
        self.assertTrue(sc.exfat_media_clean)

    def test_13_scenario_s02_bk4_persistent_airplane_leak(self) -> None:
        sc = self.report.scenarios[1]
        self.assertEqual(sc.scenario_id, "S02_BK4_PERSISTENT_AIRPLANE_LEAK")
        self.assertFalse(sc.observed_pass)
        self.assertTrue(sc.passed)
        self.assertEqual(sc.observed_classification, ANOMALY_BK4_PERSISTENT_NVRAM_LEAK)
        self.assertGreater(sc.persistent_bytes_mutated, 0)
        self.assertIn("p2_backup_bin", sc.drifted_items)

    def test_14_scenario_s03_wbi2_header_drift(self) -> None:
        sc = self.report.scenarios[2]
        self.assertEqual(sc.scenario_id, "S03_WBI2_HEADER_DRIFT")
        self.assertFalse(sc.observed_pass)
        self.assertTrue(sc.passed)
        self.assertEqual(sc.observed_classification, ANOMALY_WBI2_HEADER_DRIFT)
        self.assertEqual(sc.wbi_mutation_bytes, 1)
        self.assertIn("p5_wbi_header", sc.drifted_items)

    def test_15_scenario_s04_cp_byte_mutation(self) -> None:
        sc = self.report.scenarios[3]
        self.assertEqual(sc.scenario_id, "S04_CP_BYTE_MUTATION")
        self.assertFalse(sc.observed_pass)
        self.assertTrue(sc.passed)
        self.assertEqual(sc.observed_classification, ANOMALY_CP_BYTE_MUTATION)
        self.assertEqual(sc.cp_mutation_bytes, 1)
        self.assertIn("p8_cp_image", sc.drifted_items)

    def test_16_scenario_s05_c2pa_calibration_digest_drift(self) -> None:
        sc = self.report.scenarios[4]
        self.assertEqual(sc.scenario_id, "S05_C2PA_CALIBRATION_DIGEST_DRIFT")
        self.assertFalse(sc.observed_pass)
        self.assertTrue(sc.passed)
        self.assertEqual(sc.observed_classification, ANOMALY_C2PA_OR_CALIBRATION_DRIFT)
        self.assertEqual(sc.calibration_mutation_bytes, 1)
        self.assertFalse(sc.c2pa_keystore_untouched)

    def test_17_scenario_s06_exfat_volume_dirty(self) -> None:
        sc = self.report.scenarios[5]
        self.assertEqual(sc.scenario_id, "S06_EXFAT_VOLUME_DIRTY_SET")
        self.assertFalse(sc.observed_pass)
        self.assertTrue(sc.passed)
        self.assertEqual(sc.observed_classification, ANOMALY_EXFAT_VOLUME_DIRTY)
        self.assertFalse(sc.exfat_media_clean)

    def test_18_scenario_s07_exfat_rsv_clip_left_behind(self) -> None:
        sc = self.report.scenarios[6]
        self.assertEqual(sc.scenario_id, "S07_EXFAT_RSV_CLIP_LEFT_BEHIND")
        self.assertFalse(sc.observed_pass)
        self.assertTrue(sc.passed)
        self.assertEqual(sc.observed_classification, ANOMALY_EXFAT_UNFINALIZED_RSV_CLIP)
        self.assertFalse(sc.exfat_media_clean)

    def test_19_scenario_s08_wf12_00342260_log_signature(self) -> None:
        sc = self.report.scenarios[7]
        self.assertEqual(sc.scenario_id, "S08_WF12_00342260_LOG_SIGNATURE")
        self.assertFalse(sc.observed_pass)
        self.assertTrue(sc.passed)
        self.assertEqual(sc.observed_classification, ANOMALY_WF12_00342260_HANG)

    def test_20_scenario_s09_thermal_90c_emergency_teardown(self) -> None:
        sc = self.report.scenarios[8]
        self.assertEqual(sc.scenario_id, "S09_THERMAL_90C_EMERGENCY_TEARDOWN")
        self.assertFalse(sc.observed_pass)
        self.assertTrue(sc.passed)
        self.assertEqual(sc.observed_classification, ANOMALY_THERMAL_RUNAWAY_TEARDOWN)

    def test_21_scenario_s10_sector0_tamper(self) -> None:
        sc = self.report.scenarios[9]
        self.assertEqual(sc.scenario_id, "S10_SECTOR0_TAMPER")
        self.assertFalse(sc.observed_pass)
        self.assertTrue(sc.passed)
        self.assertEqual(sc.observed_classification, ANOMALY_SECTOR0_TAMPER)
        self.assertEqual(sc.sector0_mutation_bytes, 1)
        self.assertIn("sector0", sc.drifted_items)

    def test_22_negative_identical_h0_h2_dirs_and_serial_mismatch(self) -> None:
        same_dir = verify_stage_b_post_trial_zero_persistence(self.h0_dir, self.h0_dir)
        self.assertFalse(same_dir.all_checks_passed)
        self.assertFalse(same_dir.distinct_capture_dirs_ok)
        self.assertIn(ANOMALY_SYNTHETIC_OR_INVALID_BUNDLE, same_dir.anomaly_codes)

        with tempfile.TemporaryDirectory(prefix="fx6_p62_mismatch_") as td:
            alt_h2 = Path(td) / "h2_other_body"
            populate_stage_b_capture_bundle_fixture(
                alt_h2,
                body_serial="C4020999",
                emmc_cid="15010030303847333201deadbeef9981",
            )
            mm = verify_stage_b_post_trial_zero_persistence(self.h0_dir, alt_h2)
            self.assertFalse(mm.all_checks_passed)
            self.assertFalse(mm.same_body_identity_verified)
            self.assertEqual(mm.classification, ANOMALY_SAME_BODY_IDENTITY_MISMATCH)

    def test_23_negative_spacc_cnflasha_and_c2pa_write_attempt_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p62_spacc_") as td:
            sp_h2 = Path(td) / "h2_spacc"
            populate_stage_b_capture_bundle_fixture(sp_h2)
            sp_file = sp_h2 / STAGE_B_FORENSIC_PROBE_DEFAULTS["spacc_cnflasha"]
            buf = bytearray(sp_file.read_bytes())
            buf[256] ^= 0x55
            sp_file.write_bytes(bytes(buf))
            mf_path = sp_h2 / "backup-manifest.json"
            mf = json.loads(mf_path.read_text(encoding="utf-8"))
            import hashlib
            s_new = hashlib.sha256(bytes(buf)).hexdigest()
            mf["stage_b_forensic_probes"]["spacc_cnflasha"]["pass1_sha256"] = s_new
            mf["stage_b_forensic_probes"]["spacc_cnflasha"]["pass2_sha256"] = s_new
            mf_path.write_text(json.dumps(mf, indent=2) + "\n", encoding="utf-8")

            rec = verify_stage_b_post_trial_zero_persistence(self.h0_dir, sp_h2)
            self.assertFalse(rec.all_checks_passed)
            self.assertEqual(rec.classification, ANOMALY_C2PA_OR_CALIBRATION_DRIFT)
            self.assertFalse(rec.spacc_cnflasha_untouched)
            self.assertEqual(rec.calibration_mutation_bytes, 1)

        rec_attempt = verify_stage_b_post_trial_zero_persistence(
            self.h0_dir, self.h2_dir, c2pa_keystore_writes_attempted=True
        )
        self.assertFalse(rec_attempt.all_checks_passed)
        self.assertEqual(rec_attempt.classification, ANOMALY_C2PA_OR_CALIBRATION_DRIFT)
        self.assertFalse(rec_attempt.c2pa_keystore_untouched)

    def test_24_negative_0x100d_panic_and_rp2040_push_pull_hazard(self) -> None:
        rec_panic = verify_stage_b_post_trial_zero_persistence(
            self.h0_dir,
            self.h2_dir,
            serial_log_text="[    3.200000] SYS_PANIC code=0x100D 13S fatal hardware blink\n",
        )
        self.assertFalse(rec_panic.all_checks_passed)
        self.assertIn(ANOMALY_0x100D_13S_PANIC, rec_panic.anomaly_codes)
        self.assertTrue(rec_panic.serial_thermal_post_mortem.panic_0x100d_13s_detected)

        rec_rp = verify_stage_b_post_trial_zero_persistence(
            self.h0_dir,
            self.h2_dir,
            rp2040_fixture_config={
                "board": "waveshare_rp2040_zero",
                "open_drain": False,
                "gpio_drive_mode": "push_pull",
                "io_voltage_v": 3.3,
                "baud_rate": 48000,
                "gnd_connected": True,
            },
        )
        self.assertFalse(rec_rp.all_checks_passed)
        self.assertIn(ANOMALY_RP2040_FIXTURE_HAZARD, rec_rp.anomaly_codes)
        self.assertFalse(rec_rp.serial_thermal_post_mortem.rp2040_fixture_safe)

    def test_25_negative_p1_boot_counter_exfat_media_failure_and_u5_sticky_residue(self) -> None:
        rec_p1 = verify_stage_b_post_trial_zero_persistence(
            self.h0_dir,
            self.h2_dir,
            p1_capsule_info={
                "boot_attempts": 1,
                "mod_arm_once_present": True,
                "capsule_sha256": "a" * 64,
                "expected_capsule_sha256": "a" * 64,
                "fsync_order": ["bad_order"],
                "allow_boot_partition_targeting": False,
                "emmc_write_bytes": 0,
            },
        )
        self.assertFalse(rec_p1.all_checks_passed)
        self.assertEqual(rec_p1.classification, ANOMALY_P1_CAPSULE_OR_COUNTER_DRIFT)

        mf_exfat = build_synthetic_exfat_boot_region(volume_flags=EXFAT_FLAG_MEDIA_FAILURE)
        rec_exfat = verify_stage_b_post_trial_zero_persistence(
            self.h0_dir, self.h2_dir, exfat_boot_bytes=mf_exfat
        )
        self.assertFalse(rec_exfat.all_checks_passed)
        self.assertEqual(rec_exfat.classification, ANOMALY_EXFAT_VOLUME_DIRTY)
        self.assertTrue(rec_exfat.p1_exfat_audit.exfat_media_failure)

        with tempfile.TemporaryDirectory(prefix="fx6_p62_u5_") as td:
            u5_h2 = Path(td) / "h2_u5"
            sticky_bk4 = build_persistent_stock_bk4_bytes(active_byte8=0x01)
            populate_stage_b_capture_bundle_fixture(
                u5_h2,
                bk4_bytes=sticky_bk4,
            )
            mode_dir = u5_h2 / "setting" / "updater"
            mode_dir.mkdir(parents=True, exist_ok=True)
            (mode_dir / "mode5").write_bytes(b"mode5")
            rec_u5 = verify_stage_b_post_trial_zero_persistence(self.h0_dir, u5_h2)
            self.assertFalse(rec_u5.all_checks_passed)
            self.assertEqual(rec_u5.classification, ANOMALY_BK4_PERSISTENT_NVRAM_LEAK)
            self.assertFalse(rec_u5.bk4_nvram_audit.u5_boot_img_byte8_zero_ok)
            self.assertFalse(rec_u5.bk4_nvram_audit.u5_zero_updater_mode_residue_ok)

    def test_26_fail_closed_tampered_sha_and_non_mapping(self) -> None:
        self.assertFalse(verify_stage_b_post_trial_report("not-a-mapping").valid)
        bad_sha = copy.deepcopy(self.report_dict)
        bad_sha["report_sha256"] = "0" * 64
        res = verify_stage_b_post_trial_report(bad_sha)
        self.assertFalse(res.valid)
        self.assertFalse(res.sha256_matched)

    def test_27_fail_closed_raw_bytes_repr_and_redline_flips(self) -> None:
        raw_repr = copy.deepcopy(self.report_dict)
        raw_repr["errors"] = ("b'bad'",)
        raw_repr = _with_recomputed_sha256(raw_repr)
        self.assertFalse(verify_stage_b_post_trial_report(raw_repr).valid)

        for key, val in (
            ("persistent_emmc_writes_authorized", True),
            ("persistent_write_release", True),
            ("p8_cp_mutation_forbidden", False),
            ("wbi_p5_write_and_hibernation_forbidden", False),
            ("cp_mutation_bytes", 1),
            ("wbi_mutation_bytes", 1),
            ("calibration_mutation_bytes", 1),
            ("usb_or_camera_operations", 1),
            ("temp_dir_cleaned", False),
        ):
            mut = copy.deepcopy(self.report_dict)
            mut[key] = val
            mut = _with_recomputed_sha256(mut)
            v = verify_stage_b_post_trial_report(mut)
            self.assertFalse(v.valid, msg=f"Redline flip {key}={val!r} should fail closed")
            self.assertFalse(v.safety_redlines_ok)

    def test_28_fail_closed_nominal_c2pa_exfat_thermal_or_scenario_tamper(self) -> None:
        mut_cal = copy.deepcopy(self.report_json_dict)
        mut_cal["nominal_receipt"]["c2pa_keystore_untouched"] = False
        mut_cal["nominal_receipt"]["receipt_sha256"] = _compute_canonical_sha256(
            mut_cal["nominal_receipt"], "receipt_sha256"
        )
        mut_cal = _with_recomputed_sha256(mut_cal)
        self.assertFalse(verify_stage_b_post_trial_report(mut_cal).valid)

        mut_ex = copy.deepcopy(self.report_json_dict)
        mut_ex["nominal_receipt"]["p1_exfat_audit"]["exfat_media_clean"] = False
        mut_ex["nominal_receipt"]["receipt_sha256"] = _compute_canonical_sha256(
            mut_ex["nominal_receipt"], "receipt_sha256"
        )
        mut_ex = _with_recomputed_sha256(mut_ex)
        self.assertFalse(verify_stage_b_post_trial_report(mut_ex).valid)

        mut_th = copy.deepcopy(self.report_json_dict)
        mut_th["nominal_receipt"]["serial_thermal_post_mortem"]["peak_soc_c"] = 90.0
        mut_th["nominal_receipt"]["receipt_sha256"] = _compute_canonical_sha256(
            mut_th["nominal_receipt"], "receipt_sha256"
        )
        mut_th = _with_recomputed_sha256(mut_th)
        self.assertFalse(verify_stage_b_post_trial_report(mut_th).valid)

        mut_sc = copy.deepcopy(self.report_json_dict)
        mut_sc["scenarios"][0]["passed"] = False
        mut_sc = _with_recomputed_sha256(mut_sc)
        v_sc = verify_stage_b_post_trial_report(mut_sc)
        self.assertFalse(v_sc.valid)
        self.assertFalse(v_sc.all_10_scenarios_ok)

    def test_29_cli_audit_stage_b_post_trial_clean_room_json_and_output(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p62_cli_") as td:
            out_path = Path(td) / "stage_b_post_trial_report.json"
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = cli_main.main(
                    [
                        "audit-stage-b-post-trial",
                        "--clean-room",
                        "--json",
                        "--output",
                        str(out_path),
                    ]
                )
            self.assertEqual(rc, 0)
            rendered = buf.getvalue()
            self.assertNotRegex(rendered, RAW_BYTES_REPR_REGEX)
            self.assertTrue(out_path.is_file())
            self.assertEqual(out_path.read_text(encoding="utf-8"), rendered)
            parsed = json.loads(rendered)
            self.assertEqual(parsed["schema"], STAGE_B_POST_TRIAL_AUDIT_SCHEMA)
            self.assertEqual(parsed["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(parsed["all_checks_passed"])
            self.assertTrue(parsed["all_10_scenarios_passed"])
            self.assertTrue(verify_stage_b_post_trial_report(parsed).valid)

    def test_30_cli_audit_stage_b_post_trial_direct_bundles_and_summary(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main.main(
                [
                    "audit-stage-b-post-trial",
                    "--h0-bundle-dir",
                    str(self.h0_dir),
                    "--h2-bundle-dir",
                    str(self.h2_dir),
                ]
            )
        self.assertEqual(rc, 0)
        summary = buf.getvalue()
        self.assertIn("status=OK", summary)
        self.assertIn("schema=stage_b_post_trial_receipt_v1", summary)
        self.assertIn("matched=16/16", summary)
        self.assertIn("c2pa_untouched=True", summary)
        self.assertIn("exfat_clean=True", summary)
        self.assertNotRegex(summary, RAW_BYTES_REPR_REGEX)

        err_buf = io.StringIO()
        with redirect_stderr(err_buf):
            rc_bad = cli_main.main(
                [
                    "audit-stage-b-post-trial",
                    "--h0-bundle-dir",
                    str(self.h0_dir),
                ]
            )
        self.assertEqual(rc_bad, 2)
        self.assertIn("must be specified together", err_buf.getvalue())


if __name__ == "__main__":
    unittest.main()
