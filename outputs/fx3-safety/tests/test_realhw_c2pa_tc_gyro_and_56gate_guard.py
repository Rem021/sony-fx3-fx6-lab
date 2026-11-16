"""Fast dual-mode unit tests for Phase 170 — Real-Hardware Main Track Part 15:
Gate G55 (`p12:/cert/RQ_LIC.DAT` C2PA Authenticity License Read-Only Lock &
Cross-Body/Cross-Model Signing Firewall),
Gate G56 (`VMC-BNCM1` `EXT-LK` SMPTE-12M LTC `0.5V-4.5V p-p` Electrical Bounds,
Multi-USB `1.8V UART` Mutual Exclusion, FX6-Only `TC-OUT` BNC Mask & `IMX510`
`8.7 ms` Rolling-Shutter + 6-Axis IMU Gyro `NonRealTimeMeta.xml` Guard), and
Unified 56-Gate Master Safety Preflight (`G01..G56` / `verify-56-gates`).
"""

from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import fx3_safety
from fx3_safety.__main__ import main as package_cli_main
from fx3_safety.master_16gate_preflight import DEFAULT_REPO_ROOT
from fx3_safety.realhw_c2pa_tc_gyro_and_56gate_guard import (
    C2PA_ALLOWED_SIGNING_MODES,
    C2PA_FX3_MAX_LICENSES_PER_RQ_LIC,
    DEFAULT_SYNTHETIC_RQ_LIC_SHA256,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    FX3_MODEL_ID_HEX,
    FX3_MODEL_ID_INT,
    FX3_MODEL_NAME,
    G55_GATE_CODE,
    G55_GATE_ID,
    G56_GATE_CODE,
    G56_GATE_ID,
    IMX510_IMU_AXES,
    IMX510_IMU_SAMPLE_RATE_HZ,
    IMX510_ROLLING_SHUTTER_MS,
    IMX510_ROLLING_SHUTTER_TOLERANCE_MS,
    IMX510_SENSOR_NAME,
    NRTM_NAMESPACE_V220,
    NRTM_VALID_CONTAINERS,
    NRTM_XML_FILENAME,
    P12_CERT_DEVICE_NODE,
    P12_CERT_MOUNT_POINT,
    P12_CERT_REQUIRED_MOUNT_FLAG,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PINNED_PHASE170_DONOR_SPECS,
    REALHW_C2PA_TC_GYRO_56GATE_SCHEMA,
    REALHW_C2PA_TC_GYRO_56GATE_VERSION,
    RQ_LIC_FILENAME,
    RQ_LIC_PARTITION_PATH,
    SMPTE_12M_STANDARD_NAME,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_BLOCKED_G55_CROSS_MODEL_SIGNING_KEY,
    STATUS_BLOCKED_G55_P12_CERT_NON_RO_OR_MUTATION,
    STATUS_BLOCKED_G55_RQ_LIC_SHA256_DRIFT,
    STATUS_BLOCKED_G55_TELEMETRY_INVALID,
    STATUS_BLOCKED_G56_FX6_TC_OUT_BNC_UNMASKED,
    STATUS_BLOCKED_G56_IMX510_GYRO_NRTM_CORRUPT,
    STATUS_BLOCKED_G56_LTC_VOLTAGE_OR_UART_MUX_CLASH,
    STATUS_BLOCKED_G56_TELEMETRY_INVALID,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_PHASE170_DONOR_INTEGRITY,
    STATUS_SAFE,
    STATUS_VERIFIED_G55,
    STATUS_VERIFIED_G56,
    STATUS_VERIFIED_SAFE,
    SUPPORTED_SMPTE_LTC_FPS,
    VMC_BNCM1_ADAPTER_NAME,
    VMC_BNCM1_ID_RESISTOR_MAX_OHM,
    VMC_BNCM1_ID_RESISTOR_MIN_OHM,
    VMC_BNCM1_ID_RESISTOR_OHM,
    VMC_BNCM1_LTC_HARD_CEILING_MV,
    VMC_BNCM1_LTC_MAX_MV,
    VMC_BNCM1_LTC_MIN_MV,
    VMC_BNCM1_LTC_SYNC_MODES,
    audit_phase170_donor_contracts,
    build_synthetic_nrtm_gyro_xml,
    default_verified_rq_lic_h0_to_h3_hashes,
    evaluate_56_master_safety_gates,
    evaluate_56gate_preflight,
    evaluate_g55_c2pa_cert,
    evaluate_g56_tc_gyro_meta,
    main as module_cli_main,
    validate_c2pa_cross_model_signing_firewall,
    validate_fx6_tc_out_bnc_mask,
    validate_imx510_gyro_nrtm_integrity,
    validate_p12_cert_ms_rdonly_lock,
    validate_rq_lic_h0_to_h3_preservation,
    validate_vmc_bncm1_ltc_and_uart_mux,
    verify_c2pa_rq_lic_and_cross_model_signing_guard,
    verify_vmc_bncm1_ltc_and_imx510_gyro_nrtm_guard,
)
from fx3_safety.realhw_cxd90058_sabin_seal_and_54gate_guard import (
    REALHW_CXD90058_SABIN_SEAL_54GATE_SCHEMA,
    STATUS_BLOCKED_G53_FX6_SDI_RAW_MEW_UNMASKED,
    STATUS_BLOCKED_G54_RESIDUAL_ARTIFACT_PRESENT,
    evaluate_54gate_preflight,
)
from fx3_safety.rig_groundloop_lensrail_and_20gate_guard import (
    STATUS_FAIL_OFFLINE_HARDWARE_NOT_ATTACHED,
)


class RealHwC2paTcGyroAnd56GateGuardTests(unittest.TestCase):
    # --- 1. Hard Redlines, Package Exports & O_RDONLY Donor Audit ---

    def test_01_hard_locked_redlines_and_package_exports(self) -> None:
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertEqual(
            REALHW_C2PA_TC_GYRO_56GATE_SCHEMA,
            "fx3-realhw-c2pa-tc-gyro-56gate-preflight-v1",
        )
        self.assertEqual(REALHW_C2PA_TC_GYRO_56GATE_VERSION, "1.0.0")
        self.assertEqual(FX3_MODEL_ID_INT, 0x91030080)
        self.assertEqual(FX3_MODEL_ID_HEX, "0x91030080")
        self.assertEqual(FX3_MODEL_NAME, "ILME-FX3")
        self.assertEqual(P12_CERT_MOUNT_POINT, "p12:/cert")
        self.assertEqual(RQ_LIC_FILENAME, "RQ_LIC.DAT")
        self.assertEqual(VMC_BNCM1_LTC_MIN_MV, 500)
        self.assertEqual(VMC_BNCM1_LTC_MAX_MV, 4500)
        self.assertEqual(VMC_BNCM1_LTC_HARD_CEILING_MV, 5000)
        self.assertEqual(IMX510_ROLLING_SHUTTER_MS, 8.7)
        self.assertEqual(IMX510_IMU_AXES, 6)
        self.assertEqual(NRTM_XML_FILENAME, "NonRealTimeMeta.xml")

        for sym in (
            "C2PA_ALLOWED_SIGNING_MODES",
            "C2PA_FX3_MAX_LICENSES_PER_RQ_LIC",
            "DEFAULT_SYNTHETIC_RQ_LIC_SHA256",
            "G55_GATE_CODE",
            "G55_GATE_ID",
            "G56_GATE_CODE",
            "G56_GATE_ID",
            "IMX510_IMU_AXES",
            "IMX510_IMU_SAMPLE_RATE_HZ",
            "IMX510_ROLLING_SHUTTER_MS",
            "IMX510_ROLLING_SHUTTER_TOLERANCE_MS",
            "IMX510_SENSOR_NAME",
            "NRTM_NAMESPACE_V220",
            "NRTM_VALID_CONTAINERS",
            "NRTM_XML_FILENAME",
            "P12_CERT_DEVICE_NODE",
            "P12_CERT_MOUNT_POINT",
            "P12_CERT_REQUIRED_MOUNT_FLAG",
            "PINNED_PHASE170_DONOR_SPECS",
            "REALHW_C2PA_TC_GYRO_56GATE_SCHEMA",
            "REALHW_C2PA_TC_GYRO_56GATE_VERSION",
            "RQ_LIC_FILENAME",
            "RQ_LIC_PARTITION_PATH",
            "SMPTE_12M_STANDARD_NAME",
            "STATUS_BLOCKED_G55_CROSS_MODEL_SIGNING_KEY",
            "STATUS_BLOCKED_G55_P12_CERT_NON_RO_OR_MUTATION",
            "STATUS_BLOCKED_G55_RQ_LIC_SHA256_DRIFT",
            "STATUS_BLOCKED_G55_TELEMETRY_INVALID",
            "STATUS_BLOCKED_G56_FX6_TC_OUT_BNC_UNMASKED",
            "STATUS_BLOCKED_G56_IMX510_GYRO_NRTM_CORRUPT",
            "STATUS_BLOCKED_G56_LTC_VOLTAGE_OR_UART_MUX_CLASH",
            "STATUS_BLOCKED_G56_TELEMETRY_INVALID",
            "STATUS_BLOCKED_PHASE170_DONOR_INTEGRITY",
            "STATUS_VERIFIED_G55",
            "STATUS_VERIFIED_G56",
            "SUPPORTED_SMPTE_LTC_FPS",
            "VMC_BNCM1_ADAPTER_NAME",
            "VMC_BNCM1_ID_RESISTOR_MAX_OHM",
            "VMC_BNCM1_ID_RESISTOR_MIN_OHM",
            "VMC_BNCM1_LTC_HARD_CEILING_MV",
            "VMC_BNCM1_LTC_MAX_MV",
            "VMC_BNCM1_LTC_MIN_MV",
            "VMC_BNCM1_LTC_SYNC_MODES",
            "C2paRqLicSigningGuardResult",
            "G55C2paCertResult",
            "G56TcGyroMetaResult",
            "Master56GateReport",
            "Phase170DonorAuditResult",
            "VmcBncm1LtcGyroNrtmGuardResult",
            "audit_phase170_donor_contracts",
            "build_synthetic_nrtm_gyro_xml",
            "default_verified_rq_lic_h0_to_h3_hashes",
            "evaluate_56_master_safety_gates",
            "evaluate_56gate_preflight",
            "evaluate_g55_c2pa_cert",
            "evaluate_g56_tc_gyro_meta",
            "realhw_c2pa_tc_gyro_and_56gate_guard",
            "validate_c2pa_cross_model_signing_firewall",
            "validate_fx6_tc_out_bnc_mask",
            "validate_imx510_gyro_nrtm_integrity",
            "validate_p12_cert_ms_rdonly_lock",
            "validate_rq_lic_h0_to_h3_preservation",
            "validate_vmc_bncm1_ltc_and_uart_mux",
            "verify_c2pa_rq_lic_and_cross_model_signing_guard",
            "verify_vmc_bncm1_ltc_and_imx510_gyro_nrtm_guard",
        ):
            self.assertTrue(hasattr(fx3_safety, sym), f"Missing package export: {sym}")

        # Prior colliding constants must remain untouched
        self.assertEqual(
            fx3_safety.STATUS_BLOCKED_DONOR_INTEGRITY,
            "BLOCKED_USBLAN_PTPIP_DONOR_INTEGRITY_MISMATCH",
        )
        self.assertEqual(fx3_safety.MEDIA_TYPE_CFEXPRESS_A, "CFEXPRESS_TYPE_A")

    def test_02_donor_audit_o_rdonly_and_clean_room_fallback(self) -> None:
        clean_res = audit_phase170_donor_contracts(force_clean_room=True)
        self.assertTrue(clean_res.valid)
        self.assertEqual(clean_res.status, STATUS_VERIFIED_SAFE)
        self.assertEqual(clean_res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(clean_res.access_mode, "O_RDONLY")
        self.assertEqual(clean_res.files_inspected, 0)
        self.assertEqual(
            len(clean_res.checked_markers), len(PINNED_PHASE170_DONOR_SPECS)
        )
        self.assertEqual(clean_res.missing_markers, ())
        self.assertTrue(clean_res.fx3_contracts_verified)

        with tempfile.TemporaryDirectory() as tmpdir:
            missing_res = audit_phase170_donor_contracts(
                work_root=Path(tmpdir), force_clean_room=False
            )
            self.assertTrue(missing_res.valid)
            self.assertEqual(missing_res.verification_mode, "CLEAN_ROOM_SYNTHETIC")

        orig_open = os.open
        seen_flags: list[int] = []

        def spy_open(path: str, flags: int, *args: object, **kwargs: object) -> int:
            seen_flags.append(flags)
            return orig_open(path, flags, *args, **kwargs)  # type: ignore[arg-type]

        with patch(
            "fx3_safety.realhw_c2pa_tc_gyro_and_56gate_guard.os.open",
            side_effect=spy_open,
        ):
            auto_res = audit_phase170_donor_contracts(repo_root=DEFAULT_REPO_ROOT)

        self.assertTrue(auto_res.valid)
        self.assertEqual(auto_res.access_mode, "O_RDONLY")
        if auto_res.verification_mode == "LOCAL_DONOR_O_RDONLY":
            self.assertEqual(
                auto_res.files_inspected, len(PINNED_PHASE170_DONOR_SPECS)
            )
            self.assertEqual(len(seen_flags), len(PINNED_PHASE170_DONOR_SPECS))
            for fl in seen_flags:
                self.assertEqual(fl & 3, os.O_RDONLY)

        dumped = json.dumps(auto_res.to_dict(), ensure_ascii=False)
        self.assertNotIn("b'\\x7fELF", dumped)
        self.assertNotIn('b"\\x7fELF', dumped)
        self.assertNotIn("b'BK4", dumped)

    def test_03_donor_audit_fails_closed_on_tampered_sha_or_missing_marker(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            work = Path(tmpdir)
            for _k, (_body, rel, size, _sha, toks, _lbl) in (
                PINNED_PHASE170_DONOR_SPECS.items()
            ):
                p = work / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                payload = b"".join(t + b"\x00" for t in toks)
                if len(payload) < size:
                    payload = payload + b"\x00" * (size - len(payload))
                p.write_bytes(payload[:size])

            bad_res = audit_phase170_donor_contracts(
                work_root=work, force_clean_room=False
            )
            self.assertFalse(bad_res.valid)
            self.assertEqual(bad_res.status, STATUS_BLOCKED_PHASE170_DONOR_INTEGRITY)
            self.assertFalse(bad_res.fx3_contracts_verified)
            self.assertGreater(len(bad_res.errors), 0)

    def test_04_donor_audit_fails_when_marker_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            work = Path(tmpdir)
            for _k, (_body, rel, size, _sha, _toks, _lbl) in (
                PINNED_PHASE170_DONOR_SPECS.items()
            ):
                p = work / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b"\x00" * min(size, 64))

            bad_res = audit_phase170_donor_contracts(
                work_root=work, force_clean_room=False
            )
            self.assertFalse(bad_res.valid)
            self.assertEqual(bad_res.status, STATUS_BLOCKED_PHASE170_DONOR_INTEGRITY)
            self.assertEqual(
                len(bad_res.missing_markers), len(PINNED_PHASE170_DONOR_SPECS)
            )

    # --- 2. Pure Helper Function Tests (G55 & G56) ---

    def test_05_default_rq_lic_hashes_and_invalid_seed_fallback(self) -> None:
        h0, h1, h2, h3 = default_verified_rq_lic_h0_to_h3_hashes()
        self.assertEqual(h0, DEFAULT_SYNTHETIC_RQ_LIC_SHA256)
        self.assertEqual(len({h0, h1, h2, h3}), 1)
        self.assertEqual(len(h0), 64)

        b0, b1, b2, b3 = default_verified_rq_lic_h0_to_h3_hashes("not-a-sha")
        self.assertEqual(b0, DEFAULT_SYNTHETIC_RQ_LIC_SHA256)
        self.assertEqual((b0, b1, b2, b3), (h0, h1, h2, h3))

    def test_06_validate_p12_cert_ms_rdonly_lock(self) -> None:
        self.assertTrue(validate_p12_cert_ms_rdonly_lock())
        self.assertTrue(validate_p12_cert_ms_rdonly_lock(p12_cert_mount_flags="ro"))
        self.assertFalse(
            validate_p12_cert_ms_rdonly_lock(p12_cert_mount_flags="MS_RDWR")
        )
        self.assertFalse(
            validate_p12_cert_ms_rdonly_lock(p12_cert_mount_flags="rw,relatime")
        )
        self.assertFalse(
            validate_p12_cert_ms_rdonly_lock(p12_cert_mount_flags="remount,ro")
        )
        self.assertFalse(validate_p12_cert_ms_rdonly_lock(p12_cert_ro_locked=False))
        self.assertFalse(validate_p12_cert_ms_rdonly_lock(c2pa_cert_mutation_bytes=1))
        self.assertFalse(
            validate_p12_cert_ms_rdonly_lock(c2pa_cert_write_requested=True)
        )
        self.assertFalse(
            validate_p12_cert_ms_rdonly_lock(p12_cert_mount_point="/tmp/cert")
        )
        self.assertFalse(
            validate_p12_cert_ms_rdonly_lock(p12_cert_device_node="/dev/nflasha15")
        )

    def test_07_validate_rq_lic_h0_to_h3_preservation(self) -> None:
        self.assertTrue(validate_rq_lic_h0_to_h3_preservation())
        self.assertTrue(
            validate_rq_lic_h0_to_h3_preservation(
                c2pa_license_count=C2PA_FX3_MAX_LICENSES_PER_RQ_LIC
            )
        )
        self.assertFalse(
            validate_rq_lic_h0_to_h3_preservation(rq_lic_h2_sha256="b" * 64)
        )
        self.assertFalse(
            validate_rq_lic_h0_to_h3_preservation(rq_lic_h3_sha256="badhex")
        )
        self.assertFalse(validate_rq_lic_h0_to_h3_preservation(c2pa_license_count=0))
        self.assertFalse(
            validate_rq_lic_h0_to_h3_preservation(
                c2pa_license_count=C2PA_FX3_MAX_LICENSES_PER_RQ_LIC + 1
            )
        )
        self.assertFalse(
            validate_rq_lic_h0_to_h3_preservation(rq_lic_path="/tmp/RQ_LIC.DAT")
        )

    def test_08_validate_c2pa_cross_model_signing_firewall(self) -> None:
        self.assertTrue(validate_c2pa_cross_model_signing_firewall())
        self.assertTrue(
            validate_c2pa_cross_model_signing_firewall(
                signing_mode="UNSIGNED_STAGE_B_RESEARCH_OVERLAY"
            )
        )
        self.assertFalse(
            validate_c2pa_cross_model_signing_firewall(
                signing_model_id=0x91020080, signing_model_name="ILME-FX6"
            )
        )
        self.assertFalse(
            validate_c2pa_cross_model_signing_firewall(signing_model_name="ILME-FX30")
        )
        self.assertFalse(
            validate_c2pa_cross_model_signing_firewall(signing_key_body_match=False)
        )
        self.assertFalse(
            validate_c2pa_cross_model_signing_firewall(cross_body_signing_attempted=True)
        )
        self.assertFalse(
            validate_c2pa_cross_model_signing_firewall(cross_model_signing_attempted=True)
        )
        self.assertFalse(
            validate_c2pa_cross_model_signing_firewall(sigcert_extract_requested=True)
        )
        self.assertFalse(
            validate_c2pa_cross_model_signing_firewall(
                c2pa_cross_model_signing_blocked=False
            )
        )

    def test_09_validate_vmc_bncm1_ltc_and_uart_mux(self) -> None:
        self.assertTrue(validate_vmc_bncm1_ltc_and_uart_mux())
        self.assertTrue(validate_vmc_bncm1_ltc_and_uart_mux(ltc_peak_to_peak_mv=500))
        self.assertTrue(validate_vmc_bncm1_ltc_and_uart_mux(ltc_peak_to_peak_mv=4500))
        # Over-voltage > 5000 mV and out-of-bounds (< 500 or > 4500 mV)
        self.assertFalse(validate_vmc_bncm1_ltc_and_uart_mux(ltc_peak_to_peak_mv=5500))
        self.assertFalse(validate_vmc_bncm1_ltc_and_uart_mux(ltc_peak_to_peak_mv=4700))
        self.assertFalse(validate_vmc_bncm1_ltc_and_uart_mux(ltc_peak_to_peak_mv=350))
        self.assertFalse(validate_vmc_bncm1_ltc_and_uart_mux(ltc_ac_coupled=False))
        # Mutual exclusion with Multi-USB 1.8V UART
        self.assertFalse(
            validate_vmc_bncm1_ltc_and_uart_mux(
                vmc_bncm1_ltc_active=True, multi_usb_uart_1v8_active=True
            )
        )
        self.assertFalse(validate_vmc_bncm1_ltc_and_uart_mux(uart_mux_conflict=True))
        # Wrong ID resistor (100 kOhm LANC instead of 680 kOhm VMC-BNCM1)
        self.assertFalse(
            validate_vmc_bncm1_ltc_and_uart_mux(vmc_bncm1_id_resistor_ohm=100_000)
        )
        self.assertFalse(validate_vmc_bncm1_ltc_and_uart_mux(tc_sync_mode="FREE-RUN"))

    def test_10_validate_fx6_tc_out_bnc_mask(self) -> None:
        self.assertTrue(validate_fx6_tc_out_bnc_mask())
        self.assertFalse(validate_fx6_tc_out_bnc_mask(tc_direction="OUT"))
        self.assertFalse(validate_fx6_tc_out_bnc_mask(tc_direction="IN_OUT"))
        self.assertFalse(validate_fx6_tc_out_bnc_mask(fx6_tc_out_bnc_masked=False))
        self.assertFalse(validate_fx6_tc_out_bnc_mask(tc_out_bnc_drive_requested=True))

    def test_11_validate_imx510_gyro_nrtm_integrity_mxf_and_mp4(self) -> None:
        for container in NRTM_VALID_CONTAINERS:
            ok, xml_ok = validate_imx510_gyro_nrtm_integrity(
                recording_container=container
            )
            self.assertTrue(ok)
            self.assertTrue(xml_ok)

        custom_xml = build_synthetic_nrtm_gyro_xml(recording_container="MP4")
        self.assertIn(NRTM_NAMESPACE_V220, custom_xml)
        ok_c, xml_ok_c = validate_imx510_gyro_nrtm_integrity(
            recording_container="MP4", nrtm_xml_text=custom_xml
        )
        self.assertTrue(ok_c)
        self.assertTrue(xml_ok_c)

        # Bad rolling shutter (13.2 ms != 8.7 ms)
        ok_rs, _ = validate_imx510_gyro_nrtm_integrity(imx510_rolling_shutter_ms=13.2)
        self.assertFalse(ok_rs)
        # Wrong IMU axes
        ok_ax, _ = validate_imx510_gyro_nrtm_integrity(imu_axes=3)
        self.assertFalse(ok_ax)
        # Corrupted XML
        ok_bad_xml, xml_ok_bad = validate_imx510_gyro_nrtm_integrity(
            nrtm_xml_text="<NonRealTimeMeta><broken"
        )
        self.assertFalse(ok_bad_xml)
        self.assertFalse(xml_ok_bad)

    # --- 3. Gate G55 Core Guard & Evaluator Tests ---

    def test_12_g55_guard_default_passes_and_locks_writes(self) -> None:
        res = verify_c2pa_rq_lic_and_cross_model_signing_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G55)
        self.assertEqual(res.violation_codes, ())
        self.assertTrue(res.p12_cert_ro_safe)
        self.assertTrue(res.rq_lic_preservation_safe)
        self.assertTrue(res.cross_model_signing_safe)
        self.assertTrue(res.c2pa_cross_model_signing_blocked)
        self.assertEqual(res.c2pa_cert_mutation_bytes, 0)
        self.assertFalse(res.persistent_emmc_writes_authorized)
        self.assertFalse(res.persistent_write_release)

    def test_13_g55_blocks_p12_cert_non_ro_or_mutation(self) -> None:
        r_rw = verify_c2pa_rq_lic_and_cross_model_signing_guard(
            p12_cert_mount_flags="MS_RDWR", p12_cert_ro_locked=False
        )
        self.assertFalse(r_rw.valid)
        self.assertEqual(r_rw.status, STATUS_BLOCKED_G55_P12_CERT_NON_RO_OR_MUTATION)
        self.assertFalse(r_rw.p12_cert_ro_safe)

        r_mut = verify_c2pa_rq_lic_and_cross_model_signing_guard(
            c2pa_cert_mutation_bytes=64
        )
        self.assertFalse(r_mut.valid)
        self.assertIn(
            STATUS_BLOCKED_G55_P12_CERT_NON_RO_OR_MUTATION, r_mut.violation_codes
        )

        r_wr = verify_c2pa_rq_lic_and_cross_model_signing_guard(
            c2pa_cert_write_requested=True
        )
        self.assertFalse(r_wr.valid)
        self.assertIn(
            STATUS_BLOCKED_G55_P12_CERT_NON_RO_OR_MUTATION, r_wr.violation_codes
        )

    def test_14_g55_blocks_rq_lic_sha256_drift_across_h0_h3(self) -> None:
        h0, h1, h2, _h3 = default_verified_rq_lic_h0_to_h3_hashes()
        r_drift = verify_c2pa_rq_lic_and_cross_model_signing_guard(
            rq_lic_h0_sha256=h0,
            rq_lic_h1_sha256=h1,
            rq_lic_h2_sha256=h2,
            rq_lic_h3_sha256="f" * 64,
        )
        self.assertFalse(r_drift.valid)
        self.assertEqual(r_drift.status, STATUS_BLOCKED_G55_RQ_LIC_SHA256_DRIFT)
        self.assertFalse(r_drift.rq_lic_h0_to_h3_preserved)
        self.assertFalse(r_drift.rq_lic_preservation_safe)

    def test_15_g55_blocks_cross_body_and_cross_model_c2pa_signing(self) -> None:
        r_fx6 = verify_c2pa_rq_lic_and_cross_model_signing_guard(
            signing_model_id=0x91020080,
            signing_model_name="ILME-FX6",
            cross_model_signing_attempted=True,
        )
        self.assertFalse(r_fx6.valid)
        self.assertEqual(r_fx6.status, STATUS_BLOCKED_G55_CROSS_MODEL_SIGNING_KEY)
        self.assertFalse(r_fx6.cross_model_signing_safe)

        r_body = verify_c2pa_rq_lic_and_cross_model_signing_guard(
            signing_key_body_match=False,
            cross_body_signing_attempted=True,
        )
        self.assertFalse(r_body.valid)
        self.assertIn(STATUS_BLOCKED_G55_CROSS_MODEL_SIGNING_KEY, r_body.violation_codes)

        r_extract = verify_c2pa_rq_lic_and_cross_model_signing_guard(
            sigcert_extract_requested=True
        )
        self.assertFalse(r_extract.valid)
        self.assertIn(
            STATUS_BLOCKED_G55_CROSS_MODEL_SIGNING_KEY, r_extract.violation_codes
        )

    def test_16_g55_rejects_invalid_and_boolean_spoofed_telemetry(self) -> None:
        r_bool = verify_c2pa_rq_lic_and_cross_model_signing_guard(
            c2pa_cert_mutation_bytes=True  # type: ignore[arg-type]
        )
        self.assertFalse(r_bool.valid)
        self.assertEqual(r_bool.status, STATUS_BLOCKED_G55_TELEMETRY_INVALID)

        r_bad_hex = verify_c2pa_rq_lic_and_cross_model_signing_guard(
            rq_lic_h0_sha256="zzzz"
        )
        self.assertFalse(r_bad_hex.valid)
        self.assertEqual(r_bad_hex.status, STATUS_BLOCKED_G55_TELEMETRY_INVALID)

    def test_17_evaluate_g55_propagates_donor_failure_and_blocks_emmc_write(
        self,
    ) -> None:
        bad_audit = audit_phase170_donor_contracts(force_clean_room=True)
        tampered = type(bad_audit)(
            valid=False,
            status=STATUS_BLOCKED_PHASE170_DONOR_INTEGRITY,
            verification_mode="LOCAL_DONOR_O_RDONLY",
            access_mode="O_RDONLY",
            files_inspected=5,
            checked_markers=(),
            missing_markers=("fx3/libmpr.so",),
            fx3_contracts_verified=False,
            sha256_by_artifact={},
            bytes_by_artifact={},
            errors=("tampered donor",),
            warnings=(),
        )
        v, r = evaluate_g55_c2pa_cert(donor_audit=tampered)
        self.assertFalse(v.passed)
        self.assertFalse(r.valid)
        self.assertIn(STATUS_BLOCKED_PHASE170_DONOR_INTEGRITY, v.violation_codes)

        v_blk, r_blk = evaluate_g55_c2pa_cert(
            force_clean_room=True, request_persistent_emmc_writes=True
        )
        self.assertFalse(v_blk.passed)
        self.assertFalse(r_blk.valid)
        self.assertIn(STATUS_BLOCKED_PERSISTENT_EMMC_WRITE, v_blk.violation_codes)
        self.assertFalse(r_blk.persistent_emmc_writes_authorized)

    # --- 4. Gate G56 Core Guard & Evaluator Tests ---

    def test_18_g56_guard_default_passes_and_locks_writes(self) -> None:
        res = verify_vmc_bncm1_ltc_and_imx510_gyro_nrtm_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G56)
        self.assertEqual(res.violation_codes, ())
        self.assertTrue(res.ltc_voltage_and_mux_safe)
        self.assertTrue(res.fx6_tc_out_mask_safe)
        self.assertTrue(res.imx510_gyro_nrtm_safe)
        self.assertTrue(res.nrtm_xml_validated)
        self.assertEqual(res.imx510_rolling_shutter_ms, 8.7)
        self.assertEqual(res.imu_axes, 6)
        self.assertFalse(res.persistent_emmc_writes_authorized)
        self.assertFalse(res.persistent_write_release)

    def test_19_g56_blocks_ltc_overvoltage_and_uart_1v8_mux_clash(self) -> None:
        r_ov = verify_vmc_bncm1_ltc_and_imx510_gyro_nrtm_guard(
            ltc_peak_to_peak_mv=5500
        )
        self.assertFalse(r_ov.valid)
        self.assertEqual(r_ov.status, STATUS_BLOCKED_G56_LTC_VOLTAGE_OR_UART_MUX_CLASH)
        self.assertFalse(r_ov.ltc_voltage_and_mux_safe)

        r_uv = verify_vmc_bncm1_ltc_and_imx510_gyro_nrtm_guard(
            ltc_peak_to_peak_mv=200
        )
        self.assertFalse(r_uv.valid)
        self.assertIn(
            STATUS_BLOCKED_G56_LTC_VOLTAGE_OR_UART_MUX_CLASH, r_uv.violation_codes
        )

        r_uart = verify_vmc_bncm1_ltc_and_imx510_gyro_nrtm_guard(
            vmc_bncm1_ltc_active=True,
            multi_usb_uart_1v8_active=True,
        )
        self.assertFalse(r_uart.valid)
        self.assertIn(
            STATUS_BLOCKED_G56_LTC_VOLTAGE_OR_UART_MUX_CLASH, r_uart.violation_codes
        )

        r_mux = verify_vmc_bncm1_ltc_and_imx510_gyro_nrtm_guard(
            uart_mux_conflict=True
        )
        self.assertFalse(r_mux.valid)
        self.assertIn(
            STATUS_BLOCKED_G56_LTC_VOLTAGE_OR_UART_MUX_CLASH, r_mux.violation_codes
        )

    def test_20_g56_blocks_fx6_tc_out_bnc_drive_unmasked(self) -> None:
        r_out = verify_vmc_bncm1_ltc_and_imx510_gyro_nrtm_guard(
            tc_direction="OUT"
        )
        self.assertFalse(r_out.valid)
        self.assertEqual(r_out.status, STATUS_BLOCKED_G56_FX6_TC_OUT_BNC_UNMASKED)
        self.assertFalse(r_out.fx6_tc_out_mask_safe)

        r_req = verify_vmc_bncm1_ltc_and_imx510_gyro_nrtm_guard(
            tc_out_bnc_drive_requested=True
        )
        self.assertFalse(r_req.valid)
        self.assertIn(STATUS_BLOCKED_G56_FX6_TC_OUT_BNC_UNMASKED, r_req.violation_codes)

        r_unmask = verify_vmc_bncm1_ltc_and_imx510_gyro_nrtm_guard(
            fx6_tc_out_bnc_masked=False
        )
        self.assertFalse(r_unmask.valid)
        self.assertIn(
            STATUS_BLOCKED_G56_FX6_TC_OUT_BNC_UNMASKED, r_unmask.violation_codes
        )

    def test_21_g56_blocks_imx510_gyro_or_nrtm_corruption(self) -> None:
        r_rs = verify_vmc_bncm1_ltc_and_imx510_gyro_nrtm_guard(
            imx510_rolling_shutter_ms=13.2
        )
        self.assertFalse(r_rs.valid)
        self.assertEqual(r_rs.status, STATUS_BLOCKED_G56_IMX510_GYRO_NRTM_CORRUPT)
        self.assertFalse(r_rs.imx510_gyro_nrtm_safe)

        r_crc = verify_vmc_bncm1_ltc_and_imx510_gyro_nrtm_guard(
            gyro_packet_crc_valid=False
        )
        self.assertFalse(r_crc.valid)
        self.assertIn(STATUS_BLOCKED_G56_IMX510_GYRO_NRTM_CORRUPT, r_crc.violation_codes)

        r_ts = verify_vmc_bncm1_ltc_and_imx510_gyro_nrtm_guard(
            gyro_monotonic_timestamps=False
        )
        self.assertFalse(r_ts.valid)
        self.assertIn(STATUS_BLOCKED_G56_IMX510_GYRO_NRTM_CORRUPT, r_ts.violation_codes)

        r_nrtm = verify_vmc_bncm1_ltc_and_imx510_gyro_nrtm_guard(
            nrtm_xml_present=False
        )
        self.assertFalse(r_nrtm.valid)
        self.assertIn(
            STATUS_BLOCKED_G56_IMX510_GYRO_NRTM_CORRUPT, r_nrtm.violation_codes
        )

        r_nle = verify_vmc_bncm1_ltc_and_imx510_gyro_nrtm_guard(
            davinci_resolve_compatible=False
        )
        self.assertFalse(r_nle.valid)
        self.assertIn(STATUS_BLOCKED_G56_IMX510_GYRO_NRTM_CORRUPT, r_nle.violation_codes)

    def test_22_g56_rejects_nan_inf_and_boolean_spoofed_telemetry(self) -> None:
        r_nan = verify_vmc_bncm1_ltc_and_imx510_gyro_nrtm_guard(
            imx510_rolling_shutter_ms=float("nan")
        )
        self.assertFalse(r_nan.valid)
        self.assertEqual(r_nan.status, STATUS_BLOCKED_G56_TELEMETRY_INVALID)

        r_inf = verify_vmc_bncm1_ltc_and_imx510_gyro_nrtm_guard(
            tc_fps=float("inf")
        )
        self.assertFalse(r_inf.valid)
        self.assertEqual(r_inf.status, STATUS_BLOCKED_G56_TELEMETRY_INVALID)

        r_bool = verify_vmc_bncm1_ltc_and_imx510_gyro_nrtm_guard(
            ltc_peak_to_peak_mv=True  # type: ignore[arg-type]
        )
        self.assertFalse(r_bool.valid)
        self.assertEqual(r_bool.status, STATUS_BLOCKED_G56_TELEMETRY_INVALID)

    def test_23_evaluate_g56_propagates_donor_failure_and_blocks_emmc_write(
        self,
    ) -> None:
        clean_audit = audit_phase170_donor_contracts(force_clean_room=True)
        tampered = type(clean_audit)(
            valid=False,
            status=STATUS_BLOCKED_PHASE170_DONOR_INTEGRITY,
            verification_mode="LOCAL_DONOR_O_RDONLY",
            access_mode="O_RDONLY",
            files_inspected=5,
            checked_markers=(),
            missing_markers=("fx3/cpapp-b.bin",),
            fx3_contracts_verified=False,
            sha256_by_artifact={},
            bytes_by_artifact={},
            errors=("tampered donor",),
            warnings=(),
        )
        v, r = evaluate_g56_tc_gyro_meta(donor_audit=tampered)
        self.assertFalse(v.passed)
        self.assertFalse(r.valid)
        self.assertIn(STATUS_BLOCKED_PHASE170_DONOR_INTEGRITY, v.violation_codes)

        v_blk, r_blk = evaluate_g56_tc_gyro_meta(
            force_clean_room=True, request_persistent_emmc_writes=True
        )
        self.assertFalse(v_blk.passed)
        self.assertFalse(r_blk.valid)
        self.assertIn(STATUS_BLOCKED_PERSISTENT_EMMC_WRITE, v_blk.violation_codes)
        self.assertFalse(r_blk.persistent_emmc_writes_authorized)

    def test_24_g55_and_g56_constants_sanity(self) -> None:
        self.assertIn("SAME_BODY_STOCK_C2PA", C2PA_ALLOWED_SIGNING_MODES)
        self.assertIn("UNSIGNED_STAGE_B_RESEARCH_OVERLAY", C2PA_ALLOWED_SIGNING_MODES)
        self.assertEqual(P12_CERT_DEVICE_NODE, "/dev/nflasha12")
        self.assertEqual(P12_CERT_REQUIRED_MOUNT_FLAG, "MS_RDONLY")
        self.assertEqual(RQ_LIC_PARTITION_PATH, "p12:/cert/RQ_LIC.DAT")
        self.assertEqual(VMC_BNCM1_ADAPTER_NAME, "VMC-BNCM1")
        self.assertEqual(VMC_BNCM1_ID_RESISTOR_OHM, 680_000)
        self.assertEqual(VMC_BNCM1_ID_RESISTOR_MIN_OHM, 612_000)
        self.assertEqual(VMC_BNCM1_ID_RESISTOR_MAX_OHM, 748_000)
        self.assertIn("EXT-LK", VMC_BNCM1_LTC_SYNC_MODES)
        self.assertEqual(SMPTE_12M_STANDARD_NAME, "SMPTE-12M")
        self.assertIn(23.976, SUPPORTED_SMPTE_LTC_FPS)
        self.assertEqual(IMX510_SENSOR_NAME, "IMX510")
        self.assertEqual(IMX510_ROLLING_SHUTTER_TOLERANCE_MS, 0.05)
        self.assertEqual(IMX510_IMU_SAMPLE_RATE_HZ, 2000)

    # --- 5. Unified 56-Gate Master Safety Preflight Tests ---

    def test_25_56gate_offline_default_reports_53_of_56_and_locks_writes(self) -> None:
        report = evaluate_56gate_preflight(DEFAULT_REPO_ROOT)
        self.assertEqual(report.schema, REALHW_C2PA_TC_GYRO_56GATE_SCHEMA)
        self.assertEqual(report.version, REALHW_C2PA_TC_GYRO_56GATE_VERSION)
        self.assertEqual(len(report.gates), 56)
        self.assertEqual(report.summary["total_gates"], 56)
        self.assertEqual(report.summary["verified_gates"], 53)
        self.assertEqual(report.summary["blocked_or_pending_gates"], 3)
        self.assertEqual(report.summary["g01_to_g12_verified"], 9)
        self.assertEqual(report.summary["g13_to_g54_verified"], 42)
        self.assertEqual(report.summary["g55_to_g56_verified"], 2)
        self.assertTrue(report.offline_53_gates_verified)
        self.assertFalse(report.all_56_gates_verified)
        self.assertTrue(report.g13_to_g56_all_passed)
        self.assertTrue(report.g55_to_g56_all_passed)
        self.assertFalse(report.dry_run_rehearsal_only)
        self.assertFalse(report.overall_ready_for_hardware_attach)
        self.assertFalse(report.el3_payload_transmit_authorized)
        self.assertFalse(report.spi_nor_write_authorized)
        self.assertFalse(report.persistent_emmc_writes_authorized)
        self.assertFalse(report.persistent_write_release)
        self.assertEqual(report.status, "VERIFIED_53_OF_56_AWAITING_PHYSICAL_TIER0")
        for idx in (9, 10, 11):
            self.assertFalse(report.gates[idx]["passed"])
            self.assertEqual(
                report.gates[idx]["status"], STATUS_FAIL_OFFLINE_HARDWARE_NOT_ATTACHED
            )

    def test_26_56gate_dry_run_simulated_backup_56_of_56_keeps_redlines_locked(
        self,
    ) -> None:
        report = evaluate_56gate_preflight(
            DEFAULT_REPO_ROOT, dry_run_simulated_backup=True
        )
        self.assertEqual(len(report.gates), 56)
        self.assertEqual(report.summary["verified_gates"], 56)
        self.assertEqual(report.summary["blocked_or_pending_gates"], 0)
        self.assertTrue(report.all_56_gates_verified)
        self.assertTrue(report.offline_53_gates_verified)
        self.assertTrue(report.g13_to_g56_all_passed)
        self.assertTrue(report.g55_to_g56_all_passed)
        self.assertTrue(report.dry_run_rehearsal_only)
        self.assertEqual(
            report.status, "VERIFIED_ALL_56_GATES_DRY_RUN_SIMULATED_BACKUP"
        )
        # Hard-locked even in dry-run green
        self.assertFalse(report.overall_ready_for_hardware_attach)
        self.assertFalse(report.el3_payload_transmit_authorized)
        self.assertFalse(report.spi_nor_write_authorized)
        self.assertFalse(report.persistent_emmc_writes_authorized)
        self.assertFalse(report.persistent_write_release)

    def test_27_56gate_clean_room_and_alias_parity(self) -> None:
        r1 = evaluate_56gate_preflight(
            DEFAULT_REPO_ROOT, force_clean_room=True, dry_run_simulated_backup=True
        )
        r2 = evaluate_56_master_safety_gates(
            DEFAULT_REPO_ROOT, force_clean_room=True, dry_run_simulated_backup=True
        )
        self.assertEqual(r1.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(r1.clean_room_forced)
        self.assertTrue(r1.all_56_gates_verified)
        self.assertEqual(r1.summary, r2.summary)
        self.assertEqual(r1.status, r2.status)
        self.assertEqual(
            r1.master_54_report["schema"], REALHW_CXD90058_SABIN_SEAL_54GATE_SCHEMA
        )

    def test_28_56gate_propagates_g55_and_g56_failures_and_blocks_h0_h1(self) -> None:
        fail_g55 = evaluate_56gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            c2pa_cert_kwargs={"c2pa_cert_mutation_bytes": 128},
        )
        self.assertFalse(fail_g55.all_56_gates_verified)
        self.assertFalse(fail_g55.offline_53_gates_verified)
        self.assertFalse(fail_g55.g55_to_g56_all_passed)
        self.assertFalse(fail_g55.h0_h1_trial_entry_allowed)
        self.assertEqual(
            fail_g55.status, STATUS_BLOCKED_G55_P12_CERT_NON_RO_OR_MUTATION
        )

        fail_cross = evaluate_56gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            c2pa_cert_kwargs={
                "signing_model_id": 0x91020080,
                "signing_model_name": "ILME-FX6",
            },
        )
        self.assertFalse(fail_cross.all_56_gates_verified)
        self.assertEqual(
            fail_cross.status, STATUS_BLOCKED_G55_CROSS_MODEL_SIGNING_KEY
        )

        fail_g56_ltc = evaluate_56gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            tc_gyro_meta_kwargs={"ltc_peak_to_peak_mv": 6000},
        )
        self.assertFalse(fail_g56_ltc.all_56_gates_verified)
        self.assertFalse(fail_g56_ltc.offline_53_gates_verified)
        self.assertFalse(fail_g56_ltc.g55_to_g56_all_passed)
        self.assertFalse(fail_g56_ltc.h0_h1_trial_entry_allowed)
        self.assertEqual(
            fail_g56_ltc.status, STATUS_BLOCKED_G56_LTC_VOLTAGE_OR_UART_MUX_CLASH
        )

        fail_g56_gyro = evaluate_56gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            tc_gyro_meta_kwargs={"gyro_packet_crc_valid": False},
        )
        self.assertFalse(fail_g56_gyro.all_56_gates_verified)
        self.assertEqual(
            fail_g56_gyro.status, STATUS_BLOCKED_G56_IMX510_GYRO_NRTM_CORRUPT
        )

    def test_29_56gate_propagates_g53_g54_failures_and_persistent_write_redline(
        self,
    ) -> None:
        fail_g53 = evaluate_56gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            cxd90058_sabin_kwargs={"sdi_raw_16bit_requested": True},
        )
        self.assertFalse(fail_g53.all_56_gates_verified)
        self.assertEqual(fail_g53.status, STATUS_BLOCKED_G53_FX6_SDI_RAW_MEW_UNMASKED)

        fail_g54 = evaluate_56gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            factory_seal_kwargs={"tmp_jiritsu_file_count": 2},
        )
        self.assertFalse(fail_g54.all_56_gates_verified)
        self.assertEqual(fail_g54.status, STATUS_BLOCKED_G54_RESIDUAL_ARTIFACT_PRESENT)

        fail_emmc = evaluate_56gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(fail_emmc.all_56_gates_verified)
        self.assertEqual(fail_emmc.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(fail_emmc.persistent_emmc_writes_authorized)

    def test_30_56gate_unique_gate_ids_and_54gate_unchanged(self) -> None:
        m54 = evaluate_54gate_preflight(
            DEFAULT_REPO_ROOT, force_clean_room=True, dry_run_simulated_backup=True
        )
        m56 = evaluate_56gate_preflight(
            DEFAULT_REPO_ROOT, force_clean_room=True, dry_run_simulated_backup=True
        )
        self.assertEqual(len(m54.gates), 54)
        self.assertEqual(len(m56.gates), 56)
        gate_ids = [g["gate_id"] for g in m56.gates]
        self.assertEqual(len(set(gate_ids)), 56)
        self.assertEqual(gate_ids[54], G55_GATE_ID)
        self.assertEqual(gate_ids[55], G56_GATE_ID)

    def test_31_json_serializable_without_raw_binary_leakage(self) -> None:
        report = evaluate_56gate_preflight(
            DEFAULT_REPO_ROOT, dry_run_simulated_backup=True
        )
        dumped = json.dumps(report.to_dict(), ensure_ascii=False)
        parsed = json.loads(dumped)
        self.assertEqual(parsed["summary"]["verified_gates"], 56)
        self.assertNotIn("b'\\x7fELF", dumped)
        self.assertNotIn("b'\\x89UFU", dumped)
        self.assertNotIn("b'BK4", dumped)

    # --- 6. CLI Tests (fx3_safety.__main__ & module main) ---

    def test_32_cli_verify_g55_c2pa_cert_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = package_cli_main(["verify-g55-c2pa-cert", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertTrue(data["valid"])
        self.assertEqual(data["status"], STATUS_VERIFIED_G55)
        self.assertTrue(data["c2pa_rq_lic_guard"]["c2pa_cross_model_signing_blocked"])
        self.assertFalse(data["persistent_emmc_writes_authorized"])
        self.assertFalse(data["persistent_write_release"])

    def test_33_cli_verify_g56_tc_gyro_meta_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = package_cli_main(["verify-g56-tc-gyro-meta", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertTrue(data["valid"])
        self.assertEqual(data["status"], STATUS_VERIFIED_G56)
        self.assertTrue(data["tc_gyro_meta_guard"]["fx6_tc_out_bnc_masked"])
        self.assertTrue(data["tc_gyro_meta_guard"]["nrtm_xml_validated"])
        self.assertFalse(data["persistent_emmc_writes_authorized"])

    def test_34_cli_verify_56_gates_offline_and_dry_run(self) -> None:
        buf_off = io.StringIO()
        with contextlib.redirect_stdout(buf_off):
            rc_off = package_cli_main(["verify-56-gates", "--clean-room"])
        self.assertEqual(rc_off, 0)
        self.assertIn("verified=53/56", buf_off.getvalue())
        self.assertIn("overall_ready_for_hardware_attach=False", buf_off.getvalue())
        self.assertIn("el3_payload_transmit_authorized=False", buf_off.getvalue())
        self.assertIn("spi_nor_write_authorized=False", buf_off.getvalue())
        self.assertIn("persistent_emmc_writes_authorized=False", buf_off.getvalue())

        buf_dry = io.StringIO()
        with contextlib.redirect_stdout(buf_dry):
            rc_dry = package_cli_main(
                ["verify-56-gates", "--clean-room", "--dry-run-simulated-backup", "--json"]
            )
        self.assertEqual(rc_dry, 0)
        data = json.loads(buf_dry.getvalue())
        self.assertTrue(data["all_56_gates_verified"])
        self.assertEqual(data["summary"]["verified_gates"], 56)
        self.assertFalse(data["overall_ready_for_hardware_attach"])
        self.assertFalse(data["el3_payload_transmit_authorized"])
        self.assertFalse(data["spi_nor_write_authorized"])
        self.assertFalse(data["persistent_emmc_writes_authorized"])
        self.assertFalse(data["persistent_write_release"])

    def test_35_module_cli_main_text_and_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = module_cli_main(["--clean-room", "--dry-run-simulated-backup"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("verified=56/56", out)
        self.assertIn("el3_payload_transmit_authorized=False", out)
        self.assertIn("spi_nor_write_authorized=False", out)
        self.assertIn("persistent_emmc_writes_authorized=False", out)

        buf_j = io.StringIO()
        with contextlib.redirect_stdout(buf_j):
            rc_j = module_cli_main(
                ["--clean-room", "--dry-run-simulated-backup", "--json"]
            )
        self.assertEqual(rc_j, 0)
        parsed = json.loads(buf_j.getvalue())
        self.assertTrue(parsed["all_56_gates_verified"])

    # --- 7. Additional Boundary & Edge-Case Coverage Tests (48 Total) ---

    def test_36_g55_allows_string_hex_target_and_signing_model_id(self) -> None:
        res = verify_c2pa_rq_lic_and_cross_model_signing_guard(
            target_model_id="0x91030080",
            signing_model_id="0x91030080",
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.target_model_id_hex, "0x91030080")
        self.assertEqual(res.signing_model_id_hex, "0x91030080")

    def test_37_g55_blocks_unsigned_overlay_if_cross_model_attempted(self) -> None:
        res = verify_c2pa_rq_lic_and_cross_model_signing_guard(
            signing_mode="UNSIGNED_STAGE_B_RESEARCH_OVERLAY",
            cross_model_signing_attempted=True,
        )
        self.assertFalse(res.valid)
        self.assertIn(STATUS_BLOCKED_G55_CROSS_MODEL_SIGNING_KEY, res.violation_codes)

    def test_38_g55_blocks_unknown_signing_mode(self) -> None:
        res = verify_c2pa_rq_lic_and_cross_model_signing_guard(
            signing_mode="FORGED_C2PA_KEY_REUSE"
        )
        self.assertFalse(res.valid)
        self.assertIn(STATUS_BLOCKED_G55_CROSS_MODEL_SIGNING_KEY, res.violation_codes)

    def test_39_g55_blocks_zero_or_excess_rq_lic_licenses(self) -> None:
        r0 = verify_c2pa_rq_lic_and_cross_model_signing_guard(c2pa_license_count=0)
        self.assertFalse(r0.valid)
        self.assertIn(STATUS_BLOCKED_G55_RQ_LIC_SHA256_DRIFT, r0.violation_codes)

        r101 = verify_c2pa_rq_lic_and_cross_model_signing_guard(c2pa_license_count=101)
        self.assertFalse(r101.valid)
        self.assertIn(STATUS_BLOCKED_G55_RQ_LIC_SHA256_DRIFT, r101.violation_codes)

    def test_40_g56_accepts_all_supported_smpte_ltc_frame_rates(self) -> None:
        for fps in SUPPORTED_SMPTE_LTC_FPS:
            res = verify_vmc_bncm1_ltc_and_imx510_gyro_nrtm_guard(tc_fps=fps)
            self.assertTrue(res.valid, f"Expected valid for fps={fps}")

    def test_41_g56_allows_uart_1v8_when_vmc_bncm1_detached(self) -> None:
        res = verify_vmc_bncm1_ltc_and_imx510_gyro_nrtm_guard(
            vmc_bncm1_ltc_active=False,
            multi_usb_uart_1v8_active=True,
            uart_mux_conflict=False,
        )
        self.assertTrue(res.valid)

    def test_42_g56_blocks_4501mv_to_5000mv_band_and_above_5000mv(self) -> None:
        for bad_mv in (4501, 5000, 5001, 12000):
            res = verify_vmc_bncm1_ltc_and_imx510_gyro_nrtm_guard(
                ltc_peak_to_peak_mv=bad_mv
            )
            self.assertFalse(res.valid)
            self.assertIn(
                STATUS_BLOCKED_G56_LTC_VOLTAGE_OR_UART_MUX_CLASH,
                res.violation_codes,
            )

    def test_43_g56_blocks_id_resistor_outside_680k_tolerance(self) -> None:
        for bad_ohm in (
            VMC_BNCM1_ID_RESISTOR_MIN_OHM - 1,
            VMC_BNCM1_ID_RESISTOR_MAX_OHM + 1,
        ):
            res = verify_vmc_bncm1_ltc_and_imx510_gyro_nrtm_guard(
                vmc_bncm1_id_resistor_ohm=bad_ohm
            )
            self.assertFalse(res.valid)
            self.assertIn(
                STATUS_BLOCKED_G56_LTC_VOLTAGE_OR_UART_MUX_CLASH,
                res.violation_codes,
            )

    def test_44_g56_blocks_xml_with_corrupted_rolling_shutter_or_missing_gyro(
        self,
    ) -> None:
        bad_rs_xml = build_synthetic_nrtm_gyro_xml(imx510_rolling_shutter_ms=14.0)
        res = verify_vmc_bncm1_ltc_and_imx510_gyro_nrtm_guard(
            nrtm_xml_text=bad_rs_xml
        )
        self.assertFalse(res.valid)
        self.assertIn(STATUS_BLOCKED_G56_IMX510_GYRO_NRTM_CORRUPT, res.violation_codes)

        no_gyro_xml = (
            f'<NonRealTimeMeta xmlns="{NRTM_NAMESPACE_V220}">'
            '<VideoFormat><SensorRollingShutter unit="ms">8.70</SensorRollingShutter></VideoFormat>'
            "</NonRealTimeMeta>"
        )
        res2 = verify_vmc_bncm1_ltc_and_imx510_gyro_nrtm_guard(
            nrtm_xml_text=no_gyro_xml
        )
        self.assertFalse(res2.valid)
        self.assertIn(
            STATUS_BLOCKED_G56_IMX510_GYRO_NRTM_CORRUPT, res2.violation_codes
        )

    def test_45_g56_blocks_non_220_nrtm_schema_or_unsupported_container(self) -> None:
        r_ver = verify_vmc_bncm1_ltc_and_imx510_gyro_nrtm_guard(
            nrtm_schema_version="1.00"
        )
        self.assertFalse(r_ver.valid)
        self.assertIn(
            STATUS_BLOCKED_G56_IMX510_GYRO_NRTM_CORRUPT, r_ver.violation_codes
        )

        r_cont = verify_vmc_bncm1_ltc_and_imx510_gyro_nrtm_guard(
            recording_container="AVI"
        )
        self.assertFalse(r_cont.valid)
        self.assertIn(
            STATUS_BLOCKED_G56_IMX510_GYRO_NRTM_CORRUPT, r_cont.violation_codes
        )

    def test_46_clean_room_env_var_overrides_local_donors(self) -> None:
        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            report = evaluate_56gate_preflight(
                DEFAULT_REPO_ROOT, dry_run_simulated_backup=True
            )
            self.assertEqual(report.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(report.clean_room_forced)
            self.assertTrue(report.all_56_gates_verified)
            self.assertEqual(report.summary["verified_gates"], 56)
            self.assertFalse(report.overall_ready_for_hardware_attach)
            self.assertFalse(report.el3_payload_transmit_authorized)
            self.assertFalse(report.spi_nor_write_authorized)
            self.assertFalse(report.persistent_emmc_writes_authorized)
            self.assertFalse(report.persistent_write_release)

    def test_47_text_cli_output_for_g55_and_g56(self) -> None:
        buf1 = io.StringIO()
        with contextlib.redirect_stdout(buf1):
            rc1 = package_cli_main(["verify-g55-c2pa-cert", "--clean-room"])
        self.assertEqual(rc1, 0)
        self.assertIn(STATUS_VERIFIED_G55, buf1.getvalue())
        self.assertIn("cross_model_blocked=True", buf1.getvalue())
        self.assertIn("persistent_emmc_writes_authorized=False", buf1.getvalue())

        buf2 = io.StringIO()
        with contextlib.redirect_stdout(buf2):
            rc2 = package_cli_main(["verify-g56-tc-gyro-meta", "--clean-room"])
        self.assertEqual(rc2, 0)
        self.assertIn(STATUS_VERIFIED_G56, buf2.getvalue())
        self.assertIn("tc_out_masked=True", buf2.getvalue())
        self.assertIn("nrtm_ok=True", buf2.getvalue())
        self.assertIn("persistent_emmc_writes_authorized=False", buf2.getvalue())

    def test_48_g55_and_g56_gate_verdicts_include_expected_ids_and_codes(self) -> None:
        v55, _r55 = evaluate_g55_c2pa_cert(force_clean_room=True)
        self.assertEqual(v55.gate_id, G55_GATE_ID)
        self.assertEqual(v55.gate_code, G55_GATE_CODE)
        self.assertTrue(v55.passed)
        self.assertEqual(v55.status, STATUS_VERIFIED_G55)

        v56, _r56 = evaluate_g56_tc_gyro_meta(force_clean_room=True)
        self.assertEqual(v56.gate_id, G56_GATE_ID)
        self.assertEqual(v56.gate_code, G56_GATE_CODE)
        self.assertTrue(v56.passed)
        self.assertEqual(v56.status, STATUS_VERIFIED_G56)


if __name__ == "__main__":
    unittest.main()
