"""Phase 113 Dual-Mode Fast Unit Tests (>=36 tests, <0.5s clean-room):

- Pillar 0: Safety redlines, package exports (preserving Phase 94 DonorArtifactDigest), & O_RDONLY / clean-room donor inspection
- Pillar 1: CXD90057 / CXD90058 Dual-Bank A/B AP+CP synchronized epoch & torn-bank detector
- Pillar 2: Official Sony >=51% preflight gate & 6-scenario interrupted BODYDATA.DAT / USB-OTA forensic triage + Stage-B U5 zero-brick proof
- Pillar 3: CLI `verify-ab-bank-triage` & `verify-all-recovery --with-phase94 --with-phase101 --with-phase106 --with-phase113` (>=11 pillars)
"""

from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import shutil
import sys
import time
import unittest
from unittest import mock

import fx3_recovery
from fx3_recovery import __main__ as fx3_cli
from fx3_recovery.ab_bank_and_interrupted_ota_verifier import (
    AB_BANK_OTA_SCHEMA,
    AB_BANK_OTA_VERSION,
    ACTION_NO_RECOVERY_NEEDED_HEALTHY,
    ACTION_PASSIVE_UART_AND_TIER0_NOR_DUMP,
    ACTION_REJECT_CROSS_REGION_RESTORE_STOCK,
    ACTION_SD_SENTINEL_INSTANT_BOOT_ZERO_BRICK,
    ACTION_SD_SLOT1_VERIFIED_BODYDATA_OR_CLEAR_FLAGS,
    ACTION_TIER0_READONLY_DUMP_AND_SD_BODYDATA,
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    AP_BANK_FILENAMES,
    BANK_A,
    BANK_B,
    BANK_STATE_ACTIVE_VERIFIED,
    BANK_STATE_PENDING_TRIAL,
    BANK_STATE_ROLLBACK_FENCED,
    BANK_STATE_TORN_PARTIAL_WRITE,
    BODYDATA_HEADER_READ_BYTES,
    BODYDATA_UFU_MAGIC,
    BODYDATA_UFU_MAGIC_HEX,
    CP_BANK_FILENAMES,
    CXD90057_AP_SOC,
    CXD90058_CP_SOC,
    DOMAIN_AP,
    DOMAIN_CP,
    DONOR_FX3_BODYDATA_RELPATH,
    DONOR_FX3_CPAPP_B_RELPATH,
    DONOR_FX3_P1_205_RELPATH,
    DONOR_FX3_UDTRBODY_RELPATH,
    DONOR_FX6_CPAPP_B_RELPATH,
    DUAL_BANK_STATES,
    ERR_AP_BANK_ROLLBACK_FENCED,
    ERR_AP_BANK_TORN_PARTIAL_WRITE,
    ERR_AP_CP_ACTIVE_BANK_DESYNC,
    ERR_AP_CP_IPC_EPOCH_DEADLOCK,
    ERR_CP_BANK_ROLLBACK_FENCED,
    ERR_CP_BANK_TORN_PARTIAL_WRITE,
    ERR_CROSS_SKU_BANK_MISMATCH,
    ERR_FALLBACK_BANK_ROLLBACK_FENCED,
    ERR_INVALID_BANK_ID,
    ERR_NO_INTACT_FALLBACK_BANK,
    ERR_OTA_BATTERY_BELOW_51_PCT,
    ERR_OTA_BODYDATA_CRC_OR_MAGIC,
    ERR_OTA_MODEL_MISMATCH,
    ERR_OTA_REGION_NTSC_PAL_MISMATCH,
    ERR_OTA_SPLIT_BANK_PRECHECK_FAILED,
    ERR_OTA_UNSTABLE_TRANSPORT,
    FX3_EPOCH_BY_VERSION,
    FX3_MODEL_ID,
    FX3_SKU_CODE,
    FX6_MODEL_ID,
    FX6_SKU_CODE,
    OTA_SCENARIO_IDS,
    OTA_SCENARIO_U1_BATTERY_PULLED_CP,
    OTA_SCENARIO_U2_SD_CRC_MID_UPDATA,
    OTA_SCENARIO_U3_USB_CABLE_YANKED,
    OTA_SCENARIO_U4_CROSS_REGION_MISMATCH,
    OTA_SCENARIO_U5_STAGE_B_ZERO_BRICK,
    OTA_SCENARIO_U6_INTACT_HEALTHY,
    OTP_FUSE_TOUCHES,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_DEVICE_WRITES,
    PINNED_FX3_BODYDATA_HEADER_SHA256,
    PINNED_FX3_BODYDATA_TOTAL_BYTES,
    PINNED_FX3_CPAPP_B_SHA256,
    PINNED_FX3_P1_205_SHA256,
    PINNED_FX3_UDTRBODY_SHA256,
    PINNED_FX6_CPAPP_B_SHA256,
    READ_ONLY_DONOR_ACCESS,
    RECOVERY_ACTION_CODES,
    SONY_FW_UPDATE_MIN_BATTERY_PCT,
    SONY_UPDATA_ERROR_UINCOMP,
    SONY_UPDATA_FLAG_FILES,
    STAGE_B_SENTINEL_FILENAME,
    STATUS_DUAL_BANK_CONSISTENT,
    STATUS_DUAL_BANK_TORN_REJECTED,
    STATUS_FAIL_AB_BANK_OTA_GATE,
    STATUS_OTA_PREFLIGHT_APPROVED,
    STATUS_OTA_PREFLIGHT_REJECTED,
    STATUS_OTA_TRIAGE_HEALTHY,
    STATUS_OTA_TRIAGE_RECOVERABLE,
    STATUS_VERIFIED_AB_BANK_OTA_GATE,
    VALID_BANK_IDS,
    VALID_CAMERA_REGIONS,
    AbBankAndInterruptedOtaSuiteReport,
    BankSlotDescriptor,
    OtaInterruptionEvidence,
    audit_dual_bank_ap_cp_consistency,
    audit_official_ota_preflight,
    build_synthetic_dual_bank_snapshot,
    build_synthetic_ota_interruption_evidence,
    classify_bank_slot_health,
    inspect_ab_bank_and_ota_donors_readonly,
    run_ab_bank_and_interrupted_ota_suite,
    run_interrupted_ota_6_scenario_triage,
    triage_interrupted_ota_brick,
)
from fx3_recovery.files import is_forced_clean_room, resolve_donor_path

ROOT = Path(__file__).resolve().parents[3]
RAW_BYTES_RE = r'(?<![0-9A-Za-z_/.-])b[\'"]'


def _make_slot(
    *,
    bank_id: str = BANK_B,
    domain: str = DOMAIN_AP,
    firmware_version: str = "7.02",
    epoch: int = 5,
    declared_crc32: int = 0xB2C3D4E5,
    computed_crc32: int = 0xB2C3D4E5,
    bytes_written: int = 31695872,
    expected_bytes: int = 31695872,
    trial_flag: bool = False,
    rollback_fenced: bool = False,
    is_active: bool = True,
    sku_code: str = FX3_SKU_CODE,
) -> BankSlotDescriptor:
    default_name = AP_BANK_FILENAMES.get(bank_id, "ap_slot_x") if domain == DOMAIN_AP else CP_BANK_FILENAMES.get(bank_id, "cpapp-x.bin")
    return BankSlotDescriptor(
        bank_id=bank_id,
        domain=domain,
        artifact_name=default_name,
        firmware_version=firmware_version,
        epoch=epoch,
        declared_crc32=declared_crc32,
        computed_crc32=computed_crc32,
        bytes_written=bytes_written,
        expected_bytes=expected_bytes,
        trial_flag=trial_flag,
        rollback_fenced=rollback_fenced,
        is_active=is_active,
        sku_code=sku_code,
    )


class TestAbBankAndInterruptedOtaVerifier(unittest.TestCase):
    suite_report: AbBankAndInterruptedOtaSuiteReport

    @classmethod
    def setUpClass(cls) -> None:
        cls.suite_report = run_ab_bank_and_interrupted_ota_suite()

    def setUp(self) -> None:
        self._sandbox = (
            ROOT / "outputs" / "fx3-recovery-adapter" / f".tmp-phase113-test-{os.getpid()}-{time.time_ns()}"
        )

    def tearDown(self) -> None:
        shutil.rmtree(self._sandbox, ignore_errors=True)

    # ------------------------------------------------------------------
    # Safety Redlines & Package Exports
    # ------------------------------------------------------------------

    def test_01_safety_redlines_hard_locked(self) -> None:
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(ALLOW_BOOT_PARTITION_TARGETING)
        self.assertFalse(ALLOW_DESTRUCTIVE_FASTBOOT)
        self.assertTrue(READ_ONLY_DONOR_ACCESS)
        self.assertEqual(OTP_FUSE_TOUCHES, 0)
        self.assertEqual(PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(CXD90057_AP_SOC, "CXD90057")
        self.assertEqual(CXD90058_CP_SOC, "CXD90058")
        self.assertEqual(SONY_FW_UPDATE_MIN_BATTERY_PCT, 51)
        self.assertEqual(SONY_UPDATA_ERROR_UINCOMP, 54)

    def test_02_package_exports_preserve_phase94_and_expose_phase113(self) -> None:
        self.assertIs(
            fx3_recovery.DonorArtifactDigest,
            fx3_recovery.gpt_rpmb_and_rescue_bundle_verifier.DonorArtifactDigest,
        )
        self.assertIs(
            fx3_recovery.AbBankDonorArtifactDigest,
            fx3_recovery.ab_bank_and_interrupted_ota_verifier.AbBankDonorArtifactDigest,
        )
        for name in (
            "ab_bank_and_interrupted_ota_verifier",
            "AB_BANK_OTA_SCHEMA",
            "AbBankAndInterruptedOtaSuiteReport",
            "AbBankDonorArtifactDigest",
            "BankSlotDescriptor",
            "BankSlotHealthResult",
            "DualBankConsistencyReport",
            "OtaInterruptionEvidence",
            "OtaBrickTriageResult",
            "OtaPreflightResult",
            "Ota6ScenarioSuiteResult",
            "classify_bank_slot_health",
            "audit_dual_bank_ap_cp_consistency",
            "audit_official_ota_preflight",
            "triage_interrupted_ota_brick",
            "run_interrupted_ota_6_scenario_triage",
            "inspect_ab_bank_and_ota_donors_readonly",
            "run_ab_bank_and_interrupted_ota_suite",
        ):
            self.assertTrue(hasattr(fx3_recovery, name), f"missing export {name}")
            self.assertIn(name, fx3_recovery.__all__)

    # ------------------------------------------------------------------
    # Dual-Mode Donor Inspection (O_RDONLY & Clean-Room Fallback)
    # ------------------------------------------------------------------

    def test_03_clean_room_donor_inspection_anchors(self) -> None:
        snap = inspect_ab_bank_and_ota_donors_readonly(force_clean_room=True)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.read_only_access)
        self.assertTrue(snap.cpapp_b_present)
        self.assertTrue(snap.cpapp_a_referenced_in_dual_bank_model)
        self.assertEqual(snap.sony_min_battery_pct_gate, 51)
        self.assertEqual(snap.bodydata_magic_hex, BODYDATA_UFU_MAGIC_HEX)
        self.assertEqual(snap.bodydata_total_bytes, PINNED_FX3_BODYDATA_TOTAL_BYTES)
        self.assertEqual(snap.fx3_cpapp_b_sha256, PINNED_FX3_CPAPP_B_SHA256)
        self.assertEqual(snap.fx6_cpapp_b_sha256, PINNED_FX6_CPAPP_B_SHA256)
        self.assertEqual(snap.fx3_p1_205_sha256, PINNED_FX3_P1_205_SHA256)
        self.assertEqual(snap.fx3_udtrbody_sha256, PINNED_FX3_UDTRBODY_SHA256)
        self.assertEqual(len(snap.artifacts), 5)
        self.assertEqual(len(snap.snapshot_sha256), 64)
        self.assertIn("/setting/updater/uincomp", snap.updata_flags_verified)

    def test_04_active_donor_mode_matches_pinned_digests_when_donors_present(self) -> None:
        donors_exist = all(
            resolve_donor_path(rel, require_file=True).is_file()
            for rel in (
                DONOR_FX3_P1_205_RELPATH,
                DONOR_FX3_UDTRBODY_RELPATH,
                DONOR_FX3_CPAPP_B_RELPATH,
                DONOR_FX6_CPAPP_B_RELPATH,
                DONOR_FX3_BODYDATA_RELPATH,
            )
        )
        snap = inspect_ab_bank_and_ota_donors_readonly()
        if is_forced_clean_room() or not donors_exist:
            self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        else:
            self.assertEqual(snap.verification_mode, "LOCAL_DONOR_O_RDONLY")
            self.assertEqual(snap.fx3_p1_205_sha256, PINNED_FX3_P1_205_SHA256)
            self.assertEqual(snap.fx3_udtrbody_sha256, PINNED_FX3_UDTRBODY_SHA256)
            self.assertEqual(snap.fx3_cpapp_b_sha256, PINNED_FX3_CPAPP_B_SHA256)
            self.assertEqual(snap.fx6_cpapp_b_sha256, PINNED_FX6_CPAPP_B_SHA256)
            bd_artifact = [a for a in snap.artifacts if a.label == "fx3_702_bodydata_header"][0]
            self.assertEqual(bd_artifact.sha256, PINNED_FX3_BODYDATA_HEADER_SHA256)
            self.assertEqual(bd_artifact.byte_length, PINNED_FX3_BODYDATA_TOTAL_BYTES)

    def test_05_env_force_clean_room_overrides_local_donors(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            snap = inspect_ab_bank_and_ota_donors_readonly()
            self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    # ------------------------------------------------------------------
    # Pillar 1: CXD90057 / CXD90058 Dual-Bank A/B Classifier & Auditor
    # ------------------------------------------------------------------

    def test_06_classify_active_verified_slot(self) -> None:
        res = classify_bank_slot_health(_make_slot(bank_id=BANK_B, domain=DOMAIN_CP, epoch=5), min_otp_epoch=4)
        self.assertEqual(res.classified_state, BANK_STATE_ACTIVE_VERIFIED)
        self.assertTrue(res.crc_valid)
        self.assertTrue(res.complete_write)
        self.assertTrue(res.bootable)
        self.assertEqual(res.error_codes, ())

    def test_07_classify_pending_trial_slot(self) -> None:
        res = classify_bank_slot_health(_make_slot(bank_id=BANK_B, domain=DOMAIN_AP, trial_flag=True), min_otp_epoch=4)
        self.assertEqual(res.classified_state, BANK_STATE_PENDING_TRIAL)
        self.assertTrue(res.bootable)
        self.assertEqual(res.error_codes, ())

    def test_08_classify_torn_partial_write_on_truncated_bytes(self) -> None:
        res = classify_bank_slot_health(
            _make_slot(bank_id=BANK_A, domain=DOMAIN_CP, bytes_written=9437184, expected_bytes=15980568),
            min_otp_epoch=1,
        )
        self.assertEqual(res.classified_state, BANK_STATE_TORN_PARTIAL_WRITE)
        self.assertFalse(res.complete_write)
        self.assertFalse(res.bootable)
        self.assertIn(ERR_CP_BANK_TORN_PARTIAL_WRITE, res.error_codes)

    def test_09_classify_torn_partial_write_on_crc_mismatch_or_zero_crc(self) -> None:
        res_ap = classify_bank_slot_health(
            _make_slot(bank_id=BANK_A, domain=DOMAIN_AP, declared_crc32=0x11112222, computed_crc32=0xDEADBEEF),
        )
        self.assertEqual(res_ap.classified_state, BANK_STATE_TORN_PARTIAL_WRITE)
        self.assertFalse(res_ap.crc_valid)
        self.assertFalse(res_ap.bootable)
        self.assertIn(ERR_AP_BANK_TORN_PARTIAL_WRITE, res_ap.error_codes)

        res_zero = classify_bank_slot_health(
            _make_slot(bank_id=BANK_B, domain=DOMAIN_CP, declared_crc32=0, computed_crc32=0),
        )
        self.assertEqual(res_zero.classified_state, BANK_STATE_TORN_PARTIAL_WRITE)
        self.assertFalse(res_zero.crc_valid)
        self.assertIn(ERR_CP_BANK_TORN_PARTIAL_WRITE, res_zero.error_codes)

    def test_10_classify_rollback_fenced_explicit_and_by_otp_epoch(self) -> None:
        res_flag = classify_bank_slot_health(
            _make_slot(bank_id=BANK_A, domain=DOMAIN_AP, firmware_version="2.05", epoch=1, rollback_fenced=True),
            min_otp_epoch=1,
        )
        self.assertEqual(res_flag.classified_state, BANK_STATE_ROLLBACK_FENCED)
        self.assertFalse(res_flag.bootable)
        self.assertIn(ERR_AP_BANK_ROLLBACK_FENCED, res_flag.error_codes)

        res_otp = classify_bank_slot_health(
            _make_slot(bank_id=BANK_A, domain=DOMAIN_CP, firmware_version="2.05", epoch=1),
            min_otp_epoch=4,
        )
        self.assertEqual(res_otp.classified_state, BANK_STATE_ROLLBACK_FENCED)
        self.assertFalse(res_otp.bootable)
        self.assertIn(ERR_CP_BANK_ROLLBACK_FENCED, res_otp.error_codes)

    def test_11_classify_rejects_invalid_bank_id_and_cross_sku_fx6(self) -> None:
        res_bad = classify_bank_slot_health(_make_slot(bank_id="BANK_C", domain=DOMAIN_AP))
        self.assertFalse(res_bad.bootable)
        self.assertIn(ERR_INVALID_BANK_ID, res_bad.error_codes)

        res_sku = classify_bank_slot_health(_make_slot(bank_id=BANK_B, domain=DOMAIN_CP, sku_code=FX6_SKU_CODE))
        self.assertFalse(res_sku.bootable)
        self.assertIn(ERR_CROSS_SKU_BANK_MISMATCH, res_sku.error_codes)

    def test_12_dual_bank_healthy_702_snapshot(self) -> None:
        rep = build_synthetic_dual_bank_snapshot("HEALTHY_702")
        self.assertTrue(rep.passed)
        self.assertEqual(rep.status, STATUS_DUAL_BANK_CONSISTENT)
        self.assertEqual(rep.ap_active_bank, BANK_B)
        self.assertEqual(rep.cp_active_bank, BANK_B)
        self.assertTrue(rep.ipc_protocol_compatible)
        self.assertFalse(rep.split_epoch_deadlock_detected)
        self.assertEqual(rep.fallback_bank_available, BANK_A)
        self.assertEqual(rep.recommended_action, ACTION_NO_RECOVERY_NEEDED_HEALTHY)
        self.assertTrue(rep.ram_only_classification)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_13_dual_bank_split_epoch_ap_b_702_vs_cp_a_205_torn_deadlock(self) -> None:
        rep = build_synthetic_dual_bank_snapshot("SPLIT_EPOCH_AP_B_702_CP_A_205_TORN")
        self.assertFalse(rep.passed)
        self.assertEqual(rep.status, STATUS_DUAL_BANK_TORN_REJECTED)
        self.assertTrue(rep.split_epoch_deadlock_detected)
        self.assertFalse(rep.ipc_protocol_compatible)
        self.assertIsNone(rep.fallback_bank_available)
        self.assertEqual(rep.ap_bank_b.classified_state, BANK_STATE_ACTIVE_VERIFIED)
        self.assertEqual(rep.cp_bank_a.classified_state, BANK_STATE_TORN_PARTIAL_WRITE)
        self.assertEqual(rep.cp_bank_b.classified_state, BANK_STATE_TORN_PARTIAL_WRITE)
        self.assertIn(ERR_AP_CP_IPC_EPOCH_DEADLOCK, rep.error_codes)
        self.assertIn(ERR_AP_CP_ACTIVE_BANK_DESYNC, rep.error_codes)
        self.assertIn(ERR_CP_BANK_TORN_PARTIAL_WRITE, rep.error_codes)
        self.assertEqual(rep.recommended_action, ACTION_PASSIVE_UART_AND_TIER0_NOR_DUMP)

    def test_14_dual_bank_pending_trial_with_intact_fallback_approved(self) -> None:
        rep = build_synthetic_dual_bank_snapshot("PENDING_TRIAL_702_WITH_INTACT_700_FALLBACK")
        self.assertTrue(rep.passed)
        self.assertEqual(rep.ap_bank_b.classified_state, BANK_STATE_PENDING_TRIAL)
        self.assertEqual(rep.cp_bank_b.classified_state, BANK_STATE_PENDING_TRIAL)
        self.assertEqual(rep.fallback_bank_available, BANK_A)
        self.assertTrue(rep.ipc_protocol_compatible)

    def test_15_dual_bank_pending_trial_without_fallback_rejected(self) -> None:
        ap_a = _make_slot(bank_id=BANK_A, domain=DOMAIN_AP, firmware_version="7.00", epoch=4, rollback_fenced=True, is_active=False)
        ap_b = _make_slot(bank_id=BANK_B, domain=DOMAIN_AP, firmware_version="7.02", epoch=5, trial_flag=True, is_active=True)
        cp_a = _make_slot(bank_id=BANK_A, domain=DOMAIN_CP, firmware_version="7.00", epoch=4, rollback_fenced=True, is_active=False)
        cp_b = _make_slot(bank_id=BANK_B, domain=DOMAIN_CP, firmware_version="7.02", epoch=5, trial_flag=True, is_active=True)
        rep = audit_dual_bank_ap_cp_consistency(
            ap_a, ap_b, cp_a, cp_b, ap_active_bank=BANK_B, cp_active_bank=BANK_B, min_otp_epoch=4,
        )
        self.assertFalse(rep.passed)
        self.assertIsNone(rep.fallback_bank_available)
        self.assertIn(ERR_NO_INTACT_FALLBACK_BANK, rep.error_codes)
        self.assertIn(ERR_FALLBACK_BANK_ROLLBACK_FENCED, rep.error_codes)

    def test_16_dual_bank_rollback_fenced_vs_torn_702_rejected(self) -> None:
        rep = build_synthetic_dual_bank_snapshot("ROLLBACK_FENCED_205_VS_TORN_702")
        self.assertFalse(rep.passed)
        self.assertEqual(rep.status, STATUS_DUAL_BANK_TORN_REJECTED)
        self.assertEqual(rep.ap_bank_a.classified_state, BANK_STATE_ROLLBACK_FENCED)
        self.assertEqual(rep.cp_bank_a.classified_state, BANK_STATE_ROLLBACK_FENCED)
        self.assertEqual(rep.ap_bank_b.classified_state, BANK_STATE_TORN_PARTIAL_WRITE)
        self.assertIn(ERR_FALLBACK_BANK_ROLLBACK_FENCED, rep.error_codes)
        self.assertIn(ERR_AP_BANK_TORN_PARTIAL_WRITE, rep.error_codes)

    def test_17_dual_bank_same_bank_epoch_mismatch_rejected(self) -> None:
        ap_a = _make_slot(bank_id=BANK_A, domain=DOMAIN_AP, firmware_version="7.00", epoch=4, is_active=False)
        ap_b = _make_slot(bank_id=BANK_B, domain=DOMAIN_AP, firmware_version="7.02", epoch=5, is_active=True)
        cp_a = _make_slot(bank_id=BANK_A, domain=DOMAIN_CP, firmware_version="7.00", epoch=4, is_active=False)
        cp_b = _make_slot(bank_id=BANK_B, domain=DOMAIN_CP, firmware_version="6.02", epoch=3, is_active=True)
        rep = audit_dual_bank_ap_cp_consistency(
            ap_a, ap_b, cp_a, cp_b, ap_active_bank=BANK_B, cp_active_bank=BANK_B, min_otp_epoch=1,
        )
        self.assertFalse(rep.passed)
        self.assertTrue(rep.split_epoch_deadlock_detected)
        self.assertFalse(rep.ipc_protocol_compatible)
        self.assertIn(ERR_AP_CP_IPC_EPOCH_DEADLOCK, rep.error_codes)

    def test_18_dual_bank_invalid_active_bank_id_and_unknown_scenario(self) -> None:
        ap_a = _make_slot(bank_id=BANK_A, domain=DOMAIN_AP, firmware_version="7.00", epoch=4, is_active=False)
        ap_b = _make_slot(bank_id=BANK_B, domain=DOMAIN_AP, firmware_version="7.02", epoch=5, is_active=True)
        cp_a = _make_slot(bank_id=BANK_A, domain=DOMAIN_CP, firmware_version="7.00", epoch=4, is_active=False)
        cp_b = _make_slot(bank_id=BANK_B, domain=DOMAIN_CP, firmware_version="7.02", epoch=5, is_active=True)
        rep = audit_dual_bank_ap_cp_consistency(
            ap_a, ap_b, cp_a, cp_b, ap_active_bank="BANK_Z", cp_active_bank=BANK_B,
        )
        self.assertFalse(rep.passed)
        self.assertIn(ERR_INVALID_BANK_ID, rep.error_codes)

        with self.assertRaises(ValueError):
            build_synthetic_dual_bank_snapshot("NONEXISTENT_SCENARIO")

    def test_19_dual_bank_epoch_table_and_all_4_states_covered(self) -> None:
        self.assertEqual(len(DUAL_BANK_STATES), 4)
        self.assertLess(FX3_EPOCH_BY_VERSION["2.05"], FX3_EPOCH_BY_VERSION["3.00"])
        self.assertLess(FX3_EPOCH_BY_VERSION["6.02"], FX3_EPOCH_BY_VERSION["7.00"])
        self.assertLess(FX3_EPOCH_BY_VERSION["7.01"], FX3_EPOCH_BY_VERSION["7.02"])
        self.assertEqual(VALID_BANK_IDS, (BANK_A, BANK_B))

    # ------------------------------------------------------------------
    # Pillar 2: Official OTA Pre-Flight Gate & 6-Scenario Forensic Triage
    # ------------------------------------------------------------------

    def test_20_ota_preflight_51_pct_boundary(self) -> None:
        ok_51 = audit_official_ota_preflight(battery_pct=51)
        self.assertTrue(ok_51.passed)
        self.assertEqual(ok_51.status, STATUS_OTA_PREFLIGHT_APPROVED)
        self.assertFalse(ok_51.persistent_emmc_writes_authorized)

        bad_50 = audit_official_ota_preflight(battery_pct=50)
        self.assertFalse(bad_50.passed)
        self.assertEqual(bad_50.status, STATUS_OTA_PREFLIGHT_REJECTED)
        self.assertIn(ERR_OTA_BATTERY_BELOW_51_PCT, bad_50.error_codes)

    def test_21_ota_preflight_rejects_fx6_model_cross_region_bad_ufu_and_unstable_media(self) -> None:
        bad_model = audit_official_ota_preflight(battery_pct=90, model_id=FX6_MODEL_ID)
        self.assertFalse(bad_model.passed)
        self.assertIn(ERR_OTA_MODEL_MISMATCH, bad_model.error_codes)

        bad_region = audit_official_ota_preflight(battery_pct=90, camera_region="NTSC", package_region="PAL")
        self.assertFalse(bad_region.passed)
        self.assertIn(ERR_OTA_REGION_NTSC_PAL_MISMATCH, bad_region.error_codes)

        bad_ufu = audit_official_ota_preflight(battery_pct=90, bodydata_header=b"NOT_UFU!")
        self.assertFalse(bad_ufu.passed)
        self.assertIn(ERR_OTA_BODYDATA_CRC_OR_MAGIC, bad_ufu.error_codes)

        bad_crc = audit_official_ota_preflight(battery_pct=90, bodydata_crc_ok=False)
        self.assertFalse(bad_crc.passed)
        self.assertIn(ERR_OTA_BODYDATA_CRC_OR_MAGIC, bad_crc.error_codes)

        bad_media = audit_official_ota_preflight(battery_pct=90, media_slot_stable=False)
        self.assertFalse(bad_media.passed)
        self.assertIn(ERR_OTA_UNSTABLE_TRANSPORT, bad_media.error_codes)

        bad_bank = audit_official_ota_preflight(battery_pct=90, dual_bank_precheck_ok=False)
        self.assertFalse(bad_bank.passed)
        self.assertIn(ERR_OTA_SPLIT_BANK_PRECHECK_FAILED, bad_bank.error_codes)

    def test_22_triage_u1_battery_pulled_during_cp_flash(self) -> None:
        ev = build_synthetic_ota_interruption_evidence(OTA_SCENARIO_U1_BATTERY_PULLED_CP)
        res = triage_interrupted_ota_brick(ev)
        self.assertTrue(res.passed)
        self.assertEqual(res.status, STATUS_OTA_TRIAGE_RECOVERABLE)
        self.assertTrue(res.flash_interruption_brick_surface)
        self.assertFalse(res.stage_b_zero_brick_proven)
        self.assertTrue(res.passive_uart_required)
        self.assertTrue(res.tier0_readonly_dump_required)
        self.assertFalse(res.sd_sentinel_instant_escape_available)
        self.assertEqual(res.recovery_action_code, ACTION_PASSIVE_UART_AND_TIER0_NOR_DUMP)
        self.assertIn(ERR_OTA_BATTERY_BELOW_51_PCT, res.error_codes)
        self.assertIn(ERR_CP_BANK_TORN_PARTIAL_WRITE, res.error_codes)
        self.assertEqual(res.physical_device_writes, 0)

    def test_23_triage_u2_sd_card_crc_mid_updata(self) -> None:
        ev = build_synthetic_ota_interruption_evidence(OTA_SCENARIO_U2_SD_CRC_MID_UPDATA)
        res = triage_interrupted_ota_brick(ev)
        self.assertTrue(res.passed)
        self.assertEqual(res.status, STATUS_OTA_TRIAGE_RECOVERABLE)
        self.assertTrue(res.flash_interruption_brick_surface)
        self.assertTrue(res.updata_flags_touched)
        self.assertFalse(res.passive_uart_required)
        self.assertEqual(res.recovery_action_code, ACTION_SD_SLOT1_VERIFIED_BODYDATA_OR_CLEAR_FLAGS)

    def test_24_triage_u3_usb_cable_yanked_legacy_updater(self) -> None:
        ev = build_synthetic_ota_interruption_evidence(OTA_SCENARIO_U3_USB_CABLE_YANKED)
        res = triage_interrupted_ota_brick(ev)
        self.assertTrue(res.passed)
        self.assertEqual(res.status, STATUS_OTA_TRIAGE_RECOVERABLE)
        self.assertTrue(res.flash_interruption_brick_surface)
        self.assertTrue(res.tier0_readonly_dump_required)
        self.assertTrue(res.passive_uart_required)
        self.assertEqual(res.recovery_action_code, ACTION_TIER0_READONLY_DUMP_AND_SD_BODYDATA)

    def test_25_triage_u4_cross_region_ntsc_pal_mismatch(self) -> None:
        ev = build_synthetic_ota_interruption_evidence(OTA_SCENARIO_U4_CROSS_REGION_MISMATCH)
        res = triage_interrupted_ota_brick(ev)
        self.assertTrue(res.passed)
        self.assertEqual(res.status, STATUS_OTA_TRIAGE_RECOVERABLE)
        self.assertIn(ERR_OTA_REGION_NTSC_PAL_MISMATCH, res.error_codes)
        self.assertEqual(res.recovery_action_code, ACTION_REJECT_CROSS_REGION_RESTORE_STOCK)
        self.assertFalse(res.passive_uart_required)

    def test_26_triage_u5_stage_b_clean_sd_eject_zero_brick_proof(self) -> None:
        ev = build_synthetic_ota_interruption_evidence(OTA_SCENARIO_U5_STAGE_B_ZERO_BRICK)
        res = triage_interrupted_ota_brick(ev)
        self.assertTrue(res.passed)
        self.assertEqual(res.status, STATUS_OTA_TRIAGE_HEALTHY)
        self.assertEqual(res.brick_severity, "ZERO_BRICK_SURFACE")
        self.assertFalse(res.flash_interruption_brick_surface)
        self.assertTrue(res.stage_b_zero_brick_proven)
        self.assertEqual(res.emmc_bank_transitions, 0)
        self.assertFalse(res.updata_flags_touched)
        self.assertFalse(res.passive_uart_required)
        self.assertFalse(res.tier0_readonly_dump_required)
        self.assertTrue(res.sd_sentinel_instant_escape_available)
        self.assertEqual(res.recovery_action_code, ACTION_SD_SENTINEL_INSTANT_BOOT_ZERO_BRICK)
        self.assertIn(STAGE_B_SENTINEL_FILENAME, " ".join(res.recovery_steps))

    def test_27_triage_u6_intact_dual_bank_healthy(self) -> None:
        ev = build_synthetic_ota_interruption_evidence(OTA_SCENARIO_U6_INTACT_HEALTHY)
        res = triage_interrupted_ota_brick(ev)
        self.assertTrue(res.passed)
        self.assertEqual(res.status, STATUS_OTA_TRIAGE_HEALTHY)
        self.assertEqual(res.brick_severity, "NONE")
        self.assertFalse(res.flash_interruption_brick_surface)
        self.assertEqual(res.emmc_bank_transitions, 0)
        self.assertFalse(res.updata_flags_touched)
        self.assertEqual(res.recovery_action_code, ACTION_NO_RECOVERY_NEEDED_HEALTHY)

    def test_28_u5_zero_brick_proof_does_not_fire_if_emmc_or_updata_touched(self) -> None:
        dirty_ev = OtaInterruptionEvidence(
            scenario_id="DIRTY_OVERLAY_TEST",
            battery_pct_at_event=15,
            interruption_phase="STAGE_B_TEST",
            transport_medium="SD_VOLATILE_RAM_OVERLAY",
            dual_bank_report=build_synthetic_dual_bank_snapshot("HEALTHY_702"),
            updata_uincomp_present=False,
            updata_mode_flags=("/setting/updater/mode5",),
            sd_crc_error_detected=False,
            usb_disconnect_mid_transfer=False,
            camera_region="NTSC",
            package_region="NTSC",
            stage_b_ram_overlay_active=True,
            emmc_bank_transitions=1,
            updata_flags_touched=True,
            led_pattern="test",
        )
        res = triage_interrupted_ota_brick(dirty_ev)
        self.assertFalse(res.stage_b_zero_brick_proven)
        self.assertTrue(res.flash_interruption_brick_surface)

    def test_29_ota_6_scenario_suite_and_unknown_scenario_error(self) -> None:
        res = run_interrupted_ota_6_scenario_triage()
        self.assertTrue(res.passed, res.errors)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertTrue(res.stage_b_u5_zero_brick_verified)
        self.assertEqual(len(res.suite_sha256), 64)
        self.assertEqual(len(RECOVERY_ACTION_CODES), 6)
        self.assertEqual(VALID_CAMERA_REGIONS, ("NTSC", "PAL"))

        with self.assertRaises(ValueError):
            build_synthetic_ota_interruption_evidence("UNKNOWN_U99")

    # ------------------------------------------------------------------
    # Pillar 3: Suite Determinism, Timing, CLI & >=11-Pillar Master Gate
    # ------------------------------------------------------------------

    def test_30_unified_suite_all_passed_and_invariants(self) -> None:
        rep = self.suite_report
        self.assertTrue(rep.all_passed, rep.errors)
        self.assertEqual(rep.schema, AB_BANK_OTA_SCHEMA)
        self.assertEqual(rep.version, AB_BANK_OTA_VERSION)
        self.assertEqual(rep.status, STATUS_VERIFIED_AB_BANK_OTA_GATE)
        self.assertTrue(rep.read_only_donor_access)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)
        self.assertFalse(rep.allow_boot_partition_targeting)
        self.assertFalse(rep.allow_destructive_fastboot)
        self.assertEqual(rep.otp_fuse_touches, 0)
        self.assertEqual(rep.passive_tx_bytes_emitted, 0)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertTrue(rep.dual_bank_healthy_report.passed)
        self.assertFalse(rep.dual_bank_split_deadlock_report.passed)
        self.assertTrue(rep.dual_bank_trial_pending_report.passed)
        self.assertFalse(rep.dual_bank_rollback_fenced_report.passed)
        self.assertTrue(rep.ota_preflight_valid.passed)
        self.assertFalse(rep.ota_preflight_low_battery_blocked.passed)
        self.assertTrue(rep.ota_6_scenario_suite.stage_b_u5_zero_brick_verified)

    def test_31_clean_room_suite_runtime_and_sha256_determinism(self) -> None:
        t0 = time.monotonic()
        r1 = run_ab_bank_and_interrupted_ota_suite(force_clean_room=True)
        elapsed = time.monotonic() - t0
        self.assertTrue(r1.all_passed, r1.errors)
        self.assertEqual(r1.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertLessEqual(elapsed, 0.5)
        r2 = run_ab_bank_and_interrupted_ota_suite(force_clean_room=True)
        self.assertEqual(r1.suite_sha256, r2.suite_sha256)
        self.assertEqual(r1.donor_snapshot.snapshot_sha256, r2.donor_snapshot.snapshot_sha256)

    def test_32_cli_verify_ab_bank_triage_json_out_text_and_fail_rc(self) -> None:
        self._sandbox.mkdir(parents=True, exist_ok=True)
        out_dir = self._sandbox / "cli_p113_out"

        buf_json = io.StringIO()
        with (
            mock.patch.object(
                sys,
                "argv",
                ["fx3_recovery", "verify-ab-bank-triage", "--clean-room", "--json", "--out", str(out_dir)],
            ),
            redirect_stdout(buf_json),
        ):
            rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        rendered = buf_json.getvalue()
        self.assertNotRegex(rendered, RAW_BYTES_RE)
        parsed = json.loads(rendered)
        self.assertEqual(parsed["schema"], AB_BANK_OTA_SCHEMA)
        self.assertTrue(parsed["all_passed"])
        self.assertTrue(parsed["ota_6_scenario_suite"]["stage_b_u5_zero_brick_verified"])
        self.assertTrue((out_dir / "ab-bank-ota-triage-report.json").is_file())

        buf_txt = io.StringIO()
        with mock.patch.object(sys, "argv", ["fx3_recovery", "verify-ab-bank-triage", "--clean-room"]), redirect_stdout(
            buf_txt
        ):
            rc_txt = fx3_cli.main()
        self.assertEqual(rc_txt, 0)
        self.assertIn(f"status={STATUS_VERIFIED_AB_BANK_OTA_GATE}", buf_txt.getvalue())
        self.assertIn("ota_scenarios=6/6", buf_txt.getvalue())
        self.assertIn("stage_b_u5_zero_brick_verified=True", buf_txt.getvalue())
        self.assertIn("split_deadlock_rejected=True", buf_txt.getvalue())

        failing = AbBankAndInterruptedOtaSuiteReport(
            **{**self.suite_report.__dict__, "all_passed": False, "status": STATUS_FAIL_AB_BANK_OTA_GATE}
        )
        with mock.patch("fx3_recovery.__main__.run_ab_bank_and_interrupted_ota_suite", return_value=failing):
            buf_fail = io.StringIO()
            with mock.patch.object(sys, "argv", ["fx3_recovery", "verify-ab-bank-triage", "--json"]), redirect_stdout(
                buf_fail
            ):
                rc_fail = fx3_cli.main()
            self.assertEqual(rc_fail, 2)

    def test_33_cli_verify_all_recovery_11_pillar_clean_room_json_and_text(self) -> None:
        buf = io.StringIO()
        with (
            mock.patch.object(
                sys,
                "argv",
                [
                    "fx3_recovery",
                    "verify-all-recovery",
                    "--clean-room",
                    "--with-phase94",
                    "--with-phase101",
                    "--with-phase106",
                    "--with-phase113",
                    "--json",
                ],
            ),
            redirect_stdout(buf),
        ):
            rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        rendered = buf.getvalue()
        self.assertNotRegex(rendered, RAW_BYTES_RE)
        parsed = json.loads(rendered)
        self.assertTrue(parsed["all_passed"])
        self.assertGreaterEqual(parsed["pillar_count"], 11)
        self.assertEqual(parsed["pillars_passed"], parsed["pillar_count"])
        self.assertIn("phase94_pillar8_gpt_rpmb_rescue", parsed)
        self.assertIn("phase101_pillar9_ramdisk_emmc_health", parsed)
        self.assertIn("phase106_pillar10_fdt_bootargs_kernel", parsed)
        self.assertIn("phase113_pillar11_ab_bank_interrupted_ota", parsed)
        self.assertTrue(parsed["phase113_pillar11_ab_bank_interrupted_ota"]["all_passed"])

        buf_txt = io.StringIO()
        with (
            mock.patch.object(
                sys,
                "argv",
                [
                    "fx3_recovery",
                    "verify-all-recovery",
                    "--clean-room",
                    "--with-phase94",
                    "--with-phase101",
                    "--with-phase106",
                    "--with-phase113",
                ],
            ),
            redirect_stdout(buf_txt),
        ):
            rc_txt = fx3_cli.main()
        self.assertEqual(rc_txt, 0)
        self.assertRegex(buf_txt.getvalue(), r"pillars=(\d+)/\1\b")

    def test_34_cli_verify_all_recovery_11_pillar_active_mode_and_fail_propagation(self) -> None:
        buf = io.StringIO()
        with (
            mock.patch.object(
                sys,
                "argv",
                [
                    "fx3_recovery",
                    "verify-all-recovery",
                    "--with-phase94",
                    "--with-phase101",
                    "--with-phase106",
                    "--with-phase113",
                    "--json",
                ],
            ),
            redirect_stdout(buf),
        ):
            rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        rendered = buf.getvalue()
        self.assertNotRegex(rendered, RAW_BYTES_RE)
        parsed = json.loads(rendered)
        self.assertTrue(parsed["all_passed"])
        self.assertGreaterEqual(parsed["pillar_count"], 11)
        self.assertEqual(parsed["pillars_passed"], parsed["pillar_count"])

        failing = AbBankAndInterruptedOtaSuiteReport(
            **{**self.suite_report.__dict__, "all_passed": False, "status": STATUS_FAIL_AB_BANK_OTA_GATE}
        )
        with mock.patch("fx3_recovery.__main__.run_ab_bank_and_interrupted_ota_suite", return_value=failing):
            buf_fail = io.StringIO()
            with (
                mock.patch.object(
                    sys,
                    "argv",
                    [
                        "fx3_recovery",
                        "verify-all-recovery",
                        "--clean-room",
                        "--with-phase94",
                        "--with-phase101",
                        "--with-phase106",
                        "--with-phase113",
                        "--json",
                    ],
                ),
                redirect_stdout(buf_fail),
            ):
                rc_fail = fx3_cli.main()
            self.assertEqual(rc_fail, 2)
            parsed_fail = json.loads(buf_fail.getvalue())
            self.assertFalse(parsed_fail["all_passed"])
            self.assertGreaterEqual(parsed_fail["pillar_count"], 11)
            self.assertEqual(parsed_fail["pillars_passed"], parsed_fail["pillar_count"] - 1)

    def test_35_cli_verify_all_recovery_default_7_pillar_compatibility_preserved(self) -> None:
        buf = io.StringIO()
        with (
            mock.patch.object(
                sys,
                "argv",
                ["fx3_recovery", "verify-all-recovery", "--clean-room", "--json"],
            ),
            redirect_stdout(buf),
        ):
            rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertEqual(parsed["pillar_count"], 7)
        self.assertEqual(parsed["pillars_passed"], 7)
        self.assertNotIn("phase113_pillar11_ab_bank_interrupted_ota", parsed)

    def test_36_json_serialization_no_raw_bytes_and_no_nan(self) -> None:
        rendered = json.dumps(self.suite_report.to_dict(), ensure_ascii=False, sort_keys=True, allow_nan=False)
        self.assertNotRegex(rendered, RAW_BYTES_RE)
        decoded = json.loads(rendered)
        self.assertEqual(decoded["suite_sha256"], self.suite_report.suite_sha256)
        self.assertEqual(decoded["otp_fuse_touches"], 0)
        self.assertEqual(decoded["passive_tx_bytes_emitted"], 0)
        self.assertEqual(decoded["physical_device_writes"], 0)
        self.assertFalse(decoded["persistent_emmc_writes_authorized"])
        self.assertFalse(decoded["persistent_write_release"])

    def test_37_bounded_header_size_constant_and_updata_flag_inventory(self) -> None:
        self.assertEqual(BODYDATA_HEADER_READ_BYTES, 4096)
        self.assertEqual(BODYDATA_UFU_MAGIC, b"\x89UFU\r\n\x1a\n")
        self.assertEqual(len(SONY_UPDATA_FLAG_FILES), 9)
        self.assertIn("/setting/updater/uincomp", SONY_UPDATA_FLAG_FILES)
        self.assertIn("/setting/updater/mode", SONY_UPDATA_FLAG_FILES)

    def test_38_cli_verify_ab_bank_triage_active_mode(self) -> None:
        buf = io.StringIO()
        with (
            mock.patch.object(
                sys,
                "argv",
                ["fx3_recovery", "verify-ab-bank-triage", "--json"],
            ),
            redirect_stdout(buf),
        ):
            rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        rendered = buf.getvalue()
        self.assertNotRegex(rendered, RAW_BYTES_RE)
        parsed = json.loads(rendered)
        self.assertTrue(parsed["all_passed"])
        self.assertIn(parsed["verification_mode"], ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))


if __name__ == "__main__":
    unittest.main()
